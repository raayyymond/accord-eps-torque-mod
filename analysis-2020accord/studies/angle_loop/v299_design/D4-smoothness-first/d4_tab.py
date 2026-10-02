# -*- coding: utf-8 -*-
"""d4_tab.py -- tabulate the D4 sim grid (_scratch/v299_D4/sim_raw_*.json) per scenario x candidate x speed.
Prints per (scenario, metric) a candidate x speed table; each cell = 'nominal / F_hi / r79bk'.  < 2 s."""
import json
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
OUT = Path(__file__).resolve().parents[5] / "_scratch" / "v299_D4"
R = []
for f in sorted(OUT.glob("sim_raw_*.json")):
    R += json.load(open(f))
MEM = ("nominal", "F_hi", "r79bk")
SHOW = {
    "slew": ("stalls", "tog_per_s", "frz_duty", "lag_p50", "hard16", "T_hf", "peakT", "I_end"),
    "slew_nt": ("stalls", "lag_p50", "hard16", "peakT"),
    "creep": ("dj", "dj_max", "stick_pct", "lag_max", "slips", "T_hf", "tog_per_s"),
    "creep_nt": ("dj", "dj_max", "stick_pct", "lag_max", "slips", "T_hf"),
    "jit": ("T_hf", "T_jit", "hunt_rev", "hunt_p2p", "slips"),
    "s03_05": ("fit_gain", "phase", "dj", "stick_pct", "T_hf"),
    "rn": ("e_rms", "hunt_rev", "hunt_p2p", "T_hf", "om_hf"),
    "ov_lt400": ("lurch", "droop", "I_rel"), "ov_lt511": ("lurch", "droop", "I_rel"),
    "ov3_lt511": ("lurch", "droop", "I_rel"), "ov_fm2400": ("lurch", "droop", "I_rel"),
    "cs": ("lurch", "droop", "push_ovs"),
    "out400": ("lurch_in", "settle_err", "I_rel", "T_rel"), "out511": ("lurch_in", "settle_err", "I_rel", "T_rel"),
    "out1000": ("lurch_in", "settle_err", "I_rel", "T_rel"),
}
lines = []


def P(s=""):
    print(s)
    lines.append(s)


only = sys.argv[1:] or list(SHOW)
for scn in only:
    rows = [r for r in R if r["scn"] == scn]
    if not rows:
        continue
    keys = rows[0]["keys"]
    ids = list(dict.fromkeys(k["id"] for k in keys))
    vs = sorted(set(k["v"] for k in keys))
    bym = {r["member"]: r for r in rows}
    for met in SHOW[scn]:
        if met not in rows[0]["m"]:
            continue
        P("\n[%s] %s   (cell = nominal / F_hi / r79bk)" % (scn, met))
        P("  %-12s | " % "cand" + " | ".join("%7.1f m/s       " % v for v in vs))
        for cid in ids:
            cells = []
            for v in vs:
                q = []
                for mb in MEM:
                    if mb not in bym:
                        q.append("  -  ")
                        continue
                    ks = bym[mb]["keys"]
                    idx = [i for i, k in enumerate(ks) if k["id"] == cid and k["v"] == v]
                    x = np.array(bym[mb]["m"][met])[idx]
                    q.append("%5.2f" % np.nanmax(x) if len(x) else "  -  ")
                cells.append("/".join(q))
            P("  %-12s | " % cid + " | ".join(cells))
(OUT / "sim_tables.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nwall %.1f s" % (time.time() - T0))
