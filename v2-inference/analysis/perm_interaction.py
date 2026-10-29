# DEPRECATED (2026-10-29): this permutation shuffles persona labels, which
# destroys the persona main effect together with the interaction, and it keeps
# a fixed coefficient of 16 after shuffling even though cell sizes change.
# Its p = .094 / .176 values are retracted. Use perm_resid.py instead.
# -*- coding: utf-8 -*-
"""Permutation tests for the two-way and three-way terms, balanced 2x2x2."""
import os, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
rng = np.random.default_rng(20261029)
BASE = r"E:\Deepseek_kolp\data\conv-20261026-f342510a"
d = pd.read_csv(os.path.join(BASE, "anova3-records.csv"))


def ss(y, p, a, m, term):
    df = pd.DataFrame({"y": y, "p": p, "a": a, "m": m})
    g = y.mean()
    pm = df.groupby("p").y.mean(); am = df.groupby("a").y.mean(); mm = df.groupby("m").y.mean()
    pam = df.groupby(["p", "a"]).y.mean(); pmm = df.groupby(["p", "m"]).y.mean(); amm = df.groupby(["a", "m"]).y.mean()
    cam = df.groupby(["p", "a", "m"]).y.mean()
    if term == "pa":
        s = sum((v - pm[k[0]] - am[k[1]] + g) ** 2 for k, v in pam.items())
        return 16 * float(s)
    if term == "pam":
        s = 0.0
        for k, v in cam.items():
            pp, aa, mm_ = k
            s += (v - pam[(pp, aa)] - pmm[(pp, mm_)] - amm[(aa, mm_)]
                  + pm[pp] + am[aa] + mm[mm_] - g) ** 2
        return 8 * float(s)
    raise ValueError(term)


def perm(y, p, a, m, term, which, n=4000):
    obs = ss(y, p, a, m, term)
    null = np.empty(n)
    df = pd.DataFrame({"p": p, "a": a, "m": m})
    for b in range(n):
        d2 = df.copy()
        if which == "p":       # shuffle persona within model
            d2["p"] = d2.groupby("m")["p"].transform(lambda s: rng.permutation(s.values))
        else:                  # shuffle regime within model x persona
            d2["a"] = d2.groupby(["m", "p"])["a"].transform(lambda s: rng.permutation(s.values))
        null[b] = ss(y, d2.p.values, d2.a.values, d2.m.values, term)
    return obs, (np.sum(null >= obs) + 1) / (n + 1), np.median(null)


print("=== permutation null for interaction terms (4000 shuffles) ===")
print("%-13s %-6s %-4s %12s %10s %12s" % ("metric", "term", "shuf", "SS_obs", "p_perm", "SSnull_med"))
for metric in ["L1", "zero_ratio", "calls"]:
    y = d[metric].values.astype(float)
    for term in ["pa", "pam"]:
        for which in (["p"] if term == "pa" else ["p", "a"]):
            obs, pv, med = perm(y, d.persona.values, d.adversity.values, d.model.values, term, which)
            print("%-13s %-6s %-4s %12.4f %10.4f %12.4f" % (metric, term, which, obs, pv, med))
    print()