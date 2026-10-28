# -*- coding: utf-8 -*-
"""Markdown -> HTML (formulas rendered to PNG at fixed physical size) -> PDF via headless Edge."""
import argparse, html, os, re, subprocess, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

# Formulas must be typeset in a serif face that matches the body text (Times).
# With the default (dejavusans) every \text{...} token renders in a sans/monospace
# face, which made identifiers like tool_calls look like code.
matplotlib.rcParams["mathtext.fontset"] = "stix"
matplotlib.rcParams["mathtext.default"] = "regular"
matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.serif"] = ["STIXGeneral", "DejaVu Serif"]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--outdir", required=True)
ap.add_argument("--lang", default="en")
a = ap.parse_args()

SRC, OUTDIR = a.src, a.outdir
MEDIA = os.path.join(OUTDIR, "media_" + a.lang)
os.makedirs(MEDIA, exist_ok=True)
FIGSRC = os.path.dirname(SRC)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DPI = 300
FS_DISPLAY, FS_INLINE = 12, 10

def tex_fix(s):
    s = s.replace("\\mathbb{E}", "\\mathrm{E}")
    return re.sub(r"\s+", " ", s.replace("\n", " ")).strip()

store = {}
def stash(tex, kind):
    key = f"@@{kind}{len(store)}@@"
    path = os.path.join(MEDIA, f"{kind.lower()}{len(store)}.png")
    fs = FS_DISPLAY if kind == "D" else FS_INLINE
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, "$" + tex_fix(tex) + "$", fontsize=fs, color="black")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", transparent=True, pad_inches=0.02)
    plt.close(fig)
    w, h = Image.open(path).size
    store[key] = (path, w / DPI * 25.4, h / DPI * 25.4)   # px -> mm at the render DPI
    return key

t = open(SRC, encoding="utf-8").read()
t = re.sub(r"\$\$(.+?)\$\$", lambda m: stash(m.group(1), "D"), t, flags=re.S)
t = re.sub(r"(?<!\$)\$(?!\$)([^$\n]{1,120}?)\$(?!\$)", lambda m: stash(m.group(1), "I"), t)
def _img(m):
    alt, rel = m.group(1), m.group(2)
    src = "file:///" + os.path.join(FIGSRC, rel).replace(os.sep, "/")
    # alt="Figure 1" already has a real caption in the markdown body; do not repeat it
    cap = "" if re.fullmatch(r"Figure \d+", alt.strip()) else "<figcaption>" + html.escape(alt) + "</figcaption>"
    return '<figure><img src="' + src + '">' + cap + '</figure>'

t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _img, t)

def table_block(block):
    lines = [l for l in block.strip().split("\n") if l.strip()]
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    if len(rows) < 2: return block
    head = rows[0]
    body = rows[2:] if set("".join(rows[1])) <= set("-: ") else rows[1:]
    out = ["<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr></thead><tbody>"]
    for r in body:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)

t = re.sub(r"(?:^\|.*\|[ \t]*\n?)+", lambda m: table_block(m.group(0)), t, flags=re.M)
t = re.sub(r"^### (.+)$", r"<h3>\1</h3>", t, flags=re.M)
t = re.sub(r"^## (.+)$", r"<h2>\1</h2>", t, flags=re.M)
t = re.sub(r"^# (.+)$", r"<h1>\1</h1>", t, flags=re.M)
t = re.sub(r"^---\s*$", "<hr>", t, flags=re.M)
t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
t = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", t)
t = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", t)

blocks = re.split(r"\n\s*\n", t)
out = []
for b in blocks:
    b = b.strip()
    if not b: continue
    if re.match(r"^<(h1|h2|h3|table|figure|hr|ul|ol|pre)", b): out.append(b)
    else: out.append("<p>" + b.replace("\n", " ") + "</p>")
body = "\n".join(out)

for key, (path, wmm, hmm) in store.items():
    src = "file:///" + path.replace(os.sep, "/")
    if key.startswith("@@D"):
        body = body.replace(key, f'<img class="formula-d" style="width:{wmm:.1f}mm" src="{src}">')
    else:
        body = body.replace(key, f'<img class="formula-i" style="height:{hmm:.2f}mm" src="{src}">')

FONT = '"Times New Roman", "SimSun", serif' if a.lang == "en" else '"SimSun", "Microsoft YaHei", serif'
CSS = f"""
@page {{ size: A4; margin: 22mm 20mm 20mm 20mm; }}
body {{ font-family: {FONT}; font-size: 10.5pt; line-height: 1.62; color: #111; text-align: justify; }}
h1 {{ font-size: 17pt; line-height: 1.3; margin: 0 0 6pt 0; text-align: left; }}
h2 {{ font-size: 12.5pt; margin: 15pt 0 5pt 0; border-bottom: 0.5pt solid #999; padding-bottom: 2pt; text-align: left; }}
h3 {{ font-size: 11pt; margin: 11pt 0 4pt 0; text-align: left; }}
p {{ margin: 0 0 6pt 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 8pt 0 10pt 0; font-size: 8.6pt; page-break-inside: avoid; }}
th, td {{ border: 0.4pt solid #888; padding: 2.6pt 4pt; text-align: left; vertical-align: top; }}
th {{ background: #f0f0f0; font-weight: bold; }}
figure {{ margin: 10pt 0; text-align: center; page-break-inside: avoid; }}
figure img {{ max-width: 100%; }}
figcaption {{ font-size: 8.8pt; color: #333; margin-top: 3pt; text-align: left; }}
img.formula-d {{ display: block; margin: 7pt auto; }}
img.formula-i {{ vertical-align: -0.30em; }}
hr {{ border: none; border-top: 0.4pt solid #bbb; margin: 10pt 0; }}
code {{ font-family: Consolas, monospace; font-size: 9pt; background: #f4f4f4; padding: 0 2pt; }}
"""
base = os.path.splitext(os.path.basename(SRC))[0]
html_path = os.path.join(OUTDIR, base + ".html")
pdf_path = os.path.join(OUTDIR, base + ".pdf")
open(html_path, "w", encoding="utf-8").write(
    f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>')
subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                "--print-to-pdf=" + pdf_path, "file:///" + html_path.replace(os.sep, "/")],
               check=False, timeout=180, capture_output=True)
print(f"{a.lang}: formulas={len(store)}  max_display_width_mm={max((v[1] for k,v in store.items() if k.startswith('@@D')), default=0):.1f}")
print("pdf:", os.path.getsize(pdf_path) if os.path.exists(pdf_path) else "MISSING")