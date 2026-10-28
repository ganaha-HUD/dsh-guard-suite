# API experiment runner (DeepSeek deepseek-flash, thinking + tools).
# usage:
#   python run_api_experiment.py --cells A-ni --turns 20 --tag smoke
#   python run_api_experiment.py --cells "A-shun,A-ni,B-shun,B-ni" --sessions 2 --turns 60 --stage-turns 2 --seed 1234 --tag formal
#   python run_api_experiment.py ... --sessions 8 --resume          # fills the rest, skips complete files
#
# workorder: deliverables\conv-20261026-f342510a\formal-experiment-workorder.md
# changes vs the pilot2 script (workorder section 3):
#   3.1 --sessions N; messages and rng are re-created INSIDE the session loop
#   3.2 --resume: a file counts as complete only if its LAST record has turn == --turns
#   3.3 outputs go to api2\<cell>\<tag>-sNN.jsonl/.log (api\ is never touched)
#   3.4 grand_cny accumulates across sessions; --max-cny (default 20) stops the run
#   3.5 one [session] line per session
# plus workorder section 7: 429/5xx/NET -> exponential backoff, at most 3 retries,
# then the session is marked failed and skipped.
import argparse, json, os, random, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROVIDERS = {
    "deepseek": {"base": "https://api.deepseek.com/chat/completions", "model": "deepseek-flash",
                 "env": "DEEPSEEK_API_KEY", "max_tokens_key": "max_tokens", "min_interval": 0.0},
    "mimo":     {"base": "https://api.xiaomimimo.com/v1/chat/completions", "model": "mimo-v2.6-pro",
                 "env": "MIMO_API_KEY", "max_tokens_key": "max_completion_tokens", "min_interval": 1.0},
    "mimo-flash": {"base": "https://api.xiaomimimo.com/v1/chat/completions", "model": "mimo-v2.6-flash",
                 "env": "MIMO_API_KEY", "max_tokens_key": "max_completion_tokens", "min_interval": 1.0},
    "kimi":     {"base": "https://api.moonshot.cn/v1/chat/completions", "model": "kimi-k3",
                 "env": "KIMI_API_KEY", "max_tokens_key": "max_tokens", "min_interval": 21.0},
}
PROV = "deepseek"
BASE = PROVIDERS[PROV]["base"]
MODEL = PROVIDERS[PROV]["model"]
EX = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\examples"
# workorder 3.3: formal runs live under api2; api\ holds pilot1/pilot2 for comparison.
OUT_ROOT2 = r"E:\Deepseek_kolp\data\conv-20261026-f342510a\api2"

# Prices per 1M tokens, in the unit shown. Verified 2026-10-27 from official pricing pages.
#   deepseek: USD off-peak  https://api-docs.deepseek.com/quick_start/pricing
#   mimo:     CNY           https://mimo.mi.com/docs/zh-CN/price/pay-as-you-go
#   kimi:     not published in a machine-readable form here -> cost reported as NaN
PRICES = {
    "deepseek":   {"hit": 0.003, "miss": 0.15, "out": 0.60, "usd": True},
    "mimo":       {"hit": 0.025, "miss": 3.00, "out": 6.00, "usd": False},
    "mimo-flash": {"hit": 0.02,  "miss": 1.00, "out": 2.00, "usd": False},
    "kimi":       {"hit": None,  "miss": None, "out": None, "usd": False},
}
USD_TO_CNY = 7.1

TOOL_DEFS = [
    {"type": "function", "function": {"name": "read_log", "description": "读取设备日志文件。",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "reset_board", "description": "重置传感器板子。",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "check_sensor", "description": "读取 SPS30 的 PM2.5 / PM10 数值。",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "write_script", "description": "把脚本写入磁盘。",
     "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "run_test", "description": "运行一次快速自检。",
     "parameters": {"type": "object", "properties": {}}}},
]

_last_call = [0.0]


def call(key, body):
    wait = PROVIDERS[PROV]["min_interval"] - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    req = urllib.request.Request(BASE, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, (e.code, e.read().decode("utf-8", "replace")[:400])
    except Exception as e:
        return None, ("NET", repr(e)[:300])

def call_retry(key, body):
    """workorder section 7: 429 / 5xx / NET -> exponential backoff, at most 3 retries."""
    resp, err = call(key, body)
    delay = 1.0
    attempt = 0
    while err and attempt < 3:
        code = err[0]
        retriable = (code == 429) or (code == "NET") or (isinstance(code, int) and code >= 500)
        if not retriable:
            break
        attempt += 1
        time.sleep(delay)
        delay *= 2
        resp, err = call(key, body)
    return resp, err

def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def read_tasks(p):
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line)["user"])
            except Exception:
                out.append(line)
    return out

def is_complete(path, turns):
    """workorder 3.2: complete means the LAST record has turn == turns (not row count)."""
    if not os.path.exists(path):
        return False
    last = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                last = line
    if not last:
        return False
    try:
        return int(json.loads(last).get("turn", 0)) == turns
    except Exception:
        return False

def system_text_for(use_persona, persona, lang_lock):
    # workorder section 10: A = persona + separator + lang lock; B = lang lock only.
    return (persona + "\n\n---\n" + lang_lock) if use_persona else lang_lock

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="A-ni")
    ap.add_argument("--sessions", type=int, default=1)
    ap.add_argument("--turns", type=int, default=60)
    ap.add_argument("--stage-turns", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--tag", default="smoke")
    ap.add_argument("--max-cny", type=float, default=20.0)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--provider", default="deepseek", choices=list(PROVIDERS.keys()))
    ap.add_argument("--model", default=None, help="override the provider default model")
    ap.add_argument("--out-root", default=None, help="override the output root (default: api2)")
    a = ap.parse_args()

    global BASE, MODEL, PROV
    PROV = a.provider
    profile = PROVIDERS[PROV]
    BASE = profile["base"]
    MODEL = a.model or profile["model"]
    key = os.environ.get(profile["env"], "").strip()
    if not key:
        print("FAIL: " + profile["env"] + " not set"); return 2
    min_interval = float(profile["min_interval"])

    persona = open(os.path.join(EX, "persona-V1-T86.txt"), encoding="utf-8").read().strip()
    lang_lock = open(os.path.join(EX, "lang-lock-cn.txt"), encoding="utf-8").read().strip()
    tasks = read_tasks(os.path.join(EX, "tasks-staged-cn.jsonl"))
    cell_conf = {
        "A-shun": (True,  "tools-normal.json"),
        "A-ni":   (True,  "tools-adverse.json"),
        "B-shun": (False, "tools-normal.json"),
        "B-ni":   (False, "tools-adverse.json"),
    }

    global OUT_ROOT2
    if a.out_root:
        OUT_ROOT2 = os.path.abspath(a.out_root)
    os.makedirs(OUT_ROOT2, exist_ok=True)
    grand = {"calls": 0, "prompt": 0, "hit": 0, "miss": 0, "completion": 0, "cny": 0.0}
    stopped = False
    skipped = 0

    for cell in [c.strip() for c in a.cells.split(",") if c.strip()]:
        if stopped:
            break
        if cell not in cell_conf:
            print("unknown cell:", cell); continue
        use_persona, tools_file = cell_conf[cell]
        spec = load_json(os.path.join(EX, tools_file))
        error_rate = float(spec.get("error_rate", 0.0))
        ok_texts = spec.get("tools", {})

        out_dir = os.path.join(OUT_ROOT2, cell)
        os.makedirs(out_dir, exist_ok=True)

        for n in range(1, a.sessions + 1):
            if stopped:
                break
            out_path = os.path.join(out_dir, f"{a.tag}-s{n:02d}.jsonl")
            log_path = os.path.join(out_dir, f"{a.tag}-s{n:02d}.log")
            if a.resume and is_complete(out_path, a.turns):
                skipped += 1
                print(f"[skip] cell={cell} s{n:02d} last_turn={a.turns}")
                continue

            # workorder 3.1: both lines must be INSIDE the session loop.
            messages = []
            rng = random.Random(a.seed)
            messages.append({"role": "system", "content": system_text_for(use_persona, persona, lang_lock)})

            stats = {"calls": 0, "prompt": 0, "hit": 0, "miss": 0, "completion": 0, "cny": 0.0,
                     "tool_calls": 0, "zero_tool_rows": 0, "rows": 0, "errors": 0}
            t0 = time.time()
            prev = None          # (tool_names, results, user_text) of the last sub-turn
            api_failed = False
            over_budget = False
            last_turn = 0

            with open(out_path, "w", encoding="utf-8", newline="\n") as out, \
                 open(log_path, "w", encoding="utf-8", newline="\n") as log:
                log.write(f"[run] cell={cell} session=s{n:02d} turns={a.turns} "
                          f"stage_turns={a.stage_turns} seed={a.seed}\n")
                log.write(f"[policy] persona={use_persona} tools={tools_file} error_rate={error_rate}\n")
                log.flush()

                for turn in range(1, a.turns + 1):
                    last_turn = turn
                    stage = min((turn - 1) // a.stage_turns, len(tasks) - 1)
                    # tool results are already role=tool; do NOT restate them in a user message
                    if (turn - 1) % a.stage_turns == 0 or prev is None:
                        user_text = tasks[stage]
                    else:
                        user_text = "请继续。"
                    messages.append({"role": "user", "content": user_text})

                    step = 0
                    while step < 5:
                        step += 1
                        body = {"model": MODEL, "messages": messages, "tools": TOOL_DEFS}
                        body[PROVIDERS[PROV]["max_tokens_key"]] = 1200
                        if PROV == "deepseek":
                            body["reasoning_effort"] = "high"
                            body["thinking"] = {"type": "enabled"}
                        resp, err = call_retry(key, body)
                        if err:
                            log.write(f"[turn {turn}.{step}] API ERROR {err[0]}: {str(err[1])[:200]}\n")
                            log.flush()
                            stats["errors"] += 1
                            api_failed = True
                            break

                        m = resp["choices"][0]["message"]
                        messages.append(m)  # full message, reasoning_content included
                        tcs = m.get("tool_calls") or []
                        rc = m.get("reasoning_content") or ""
                        content = m.get("content") or ""
                        u = resp.get("usage", {}) or {}
                        hit = int(u.get("prompt_cache_hit_tokens", 0))
                        miss = int(u.get("prompt_cache_miss_tokens", 0))
                        if hit + miss == 0:
                            det = u.get("prompt_tokens_details") or {}
                            cached = int(det.get("cached_tokens", 0))
                            total_prompt = int(u.get("prompt_tokens", 0))
                            if cached:
                                hit, miss = cached, max(0, total_prompt - cached)
                            else:
                                miss = total_prompt
                        comp = int(u.get("completion_tokens", 0))
                        pr = PRICES[PROV]
                        if pr["miss"] is None:
                            cny = float("nan")
                        else:
                            cny = (hit * pr["hit"] + miss * pr["miss"] + comp * pr["out"]) / 1e6
                            if pr["usd"]:
                                cny *= USD_TO_CNY
                        stats["calls"] += 1
                        stats["prompt"] += hit + miss
                        stats["hit"] += hit; stats["miss"] += miss; stats["completion"] += comp
                        if cny == cny:   # skip NaN when pricing is unknown
                            stats["cny"] += cny
                        stats["tool_calls"] += len(tcs)

                        results = []
                        for tc in tcs:
                            name = tc["function"]["name"]
                            if rng.random() < error_rate:
                                results.append("error: timeout")
                            else:
                                results.append(ok_texts.get(name, "OK"))
                        row = {"turn": turn, "step": step,
                               "reasoning": rc, "text": content,
                               "tool_calls": len(tcs),
                               "raw": {"tools": [t["function"]["name"] for t in tcs], "results": results,
                                       "usage": {"prompt": hit + miss, "cache_hit": hit, "completion": comp}},
                               "meta": {"model": MODEL, "cell": cell, "stage": stage, "tag": a.tag}}
                        out.write(json.dumps(row, ensure_ascii=False) + "\n")
                        out.flush()
                        stats["rows"] += 1
                        if not tcs:
                            stats["zero_tool_rows"] += 1

                        # workorder 3.4: budget is checked across sessions.
                        if grand["cny"] + stats["cny"] > a.max_cny:
                            over_budget = True
                            break

                        if not tcs:
                            break
                        for tc, res in zip(tcs, results):
                            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": res})
                        prev = ([t["function"]["name"] for t in tcs], results, user_text)

                    if api_failed or over_budget:
                        break

                wall = time.time() - t0
                if api_failed:
                    log.write(f"[failed] cell={cell} session=s{n:02d} at_turn={last_turn} "
                              f"errors={stats['errors']}\n")
                line = (f"[session] cell={cell} s{n:02d} turns={a.turns} rows={stats['rows']} "
                        f"calls={stats['calls']} cny={stats['cny']:.2f} wall={wall:.0f}s "
                        f"errors={stats['errors']}")
                log.write(line + "\n")
                log.flush()
                print(line)

            for k in grand:
                if k == "cny":
                    grand[k] += stats["cny"]
                elif k in stats:
                    grand[k] += stats[k]

            if over_budget:
                print(f"[stop] 已停止于 {cell} s{n:02d}: grand_cny={grand['cny']:.2f} > max_cny={a.max_cny}")
                stopped = True
                break

    print(f"[total] sessions_skipped={skipped} calls={grand['calls']} prompt={grand['prompt']} "
          f"completion={grand['completion']} cny={grand['cny']:.2f}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
