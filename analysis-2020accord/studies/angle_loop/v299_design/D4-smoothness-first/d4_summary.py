# -*- coding: utf-8 -*-
"""d4_summary.py -- the compact per-candidate rows the design page quotes, from _scratch/v299_D4/sim_raw_*.json.
Each number names its reduction (max or mean over the members nominal / F_hi / r79bk, at the stated speed).  < 2 s."""
import json
import time
from pathlib import Path

import numpy as np

T0 = time.time()
OUT = Path(__file__).resolve().parents[5] / "_scratch" / "v299_D4"
R = []
for f in sorted(OUT.glob("sim_raw_*.json")):
    R += json.load(open(f))


def get(scn, met, cid, v=None, member=None, red=np.max):
    xs = []
    for r in R:
        if r["scn"] != scn or (member and r["member"] != member) or met not in r["m"]:
            continue
        for i, k in enumerate(r["keys"]):
            if k["id"] == cid and (v is None or k["v"] == v):
                xs.append(r["m"][met][i])
    return float(red(xs)) if xs else float("nan")


ids = []
for r in R:
    if r["scn"] == "slew":
        ids = list(dict.fromkeys(k["id"] for k in r["keys"]))
        break
L = []


def P(s=""):
    print(s)
    L.append(s)


P("SLEW with the hands-off twist word (fork-capped 120 deg/s ramp to A(v), hold, return): max over members")
P("  cand        | hand-freeze toggles/s 3/8/12.5/19 | lag p50 deg 3 / 8 / 12.5 / 19 | 1.6-3 Hz rate 3/5/8 | peak T 3/8")
for c in ids:
    P("  %-11s | %4.1f %4.1f %4.1f %4.1f | %4.2f %4.2f %4.2f %4.2f | %5.2f %5.2f %5.2f | %4.0f %4.0f" % (
        c, *[get("slew", "tog_per_s", c, v) for v in (3.0, 8.0, 12.5, 19.0)],
        *[get("slew", "lag_p50", c, v) for v in (3.0, 8.0, 12.5, 19.0)],
        *[get("slew", "hard16", c, v) for v in (3.0, 5.0, 8.0)], get("slew", "peakT", c, 3.0), get("slew", "peakT", c, 8.0)))
P("  (no-twist reference, V298: lag p50 %.2f / %.2f / %.2f / %.2f)" % tuple(get("slew_nt", "lag_p50", "V298", v)
                                                                       for v in (3.0, 8.0, 12.5, 19.0)))
P("\nCREEP 1.5 deg/s drift + reversal (twist x0.5), r79bk member (route-79 breakaway friction)")
P("  cand        | stuck % 3 / 5 / 8 / 12.5 / 19 | dwell-jumps (sum 3-26) | lag max 12.5 / 19 | T 5-30 Hz rms mean")
for c in ids:
    P("  %-11s | %4.1f %4.1f %4.1f %4.1f %4.1f | %3.0f | %4.2f %4.2f | %4.2f" % (
        c, *[get("creep", "stick_pct", c, v, "r79bk") for v in (3.0, 5.0, 8.0, 12.5, 19.0)],
        get("creep", "dj", c, None, "r79bk", np.sum), get("creep", "lag_max", c, 12.5, "r79bk"),
        get("creep", "lag_max", c, 19.0, "r79bk"), get("creep", "T_hf", c, None, None, np.mean)))
P("\nHOLD with the measured one-quantum setpoint jitter / HOLD with road noise / small sine 0.3 deg 0.5 Hz")
P("  cand        | jit T 2-30 Hz rms max | jit reversals max | rn hunt p2p max | sine gain 19 / 26 nominal")
for c in ids:
    P("  %-11s | %5.2f | %3.0f | %4.2f | %4.2f %4.2f" % (
        c, get("jit", "T_jit", c), get("jit", "hunt_rev", c), get("rn", "hunt_p2p", c),
        get("s03_05", "fit_gain", c, 19.0, "nominal"), get("s03_05", "fit_gain", c, 26.0, "nominal")))
P("\nN1 HAND SCENARIOS: release lurch (deg), max over members, and the WORST change vs V298 over speeds x members")
bids = [c for c in ids if any(r["scn"] == "ov_lt400" and any(k["id"] == c for k in r["keys"]) for r in R)]
for scn, met in (("ov_lt400", "lurch"), ("ov_lt511", "lurch"), ("ov3_lt511", "lurch"), ("ov_fm2400", "lurch"),
                 ("cs", "droop"), ("out400", "lurch_in"), ("out511", "lurch_in"), ("out1000", "lurch_in")):
    row = []
    for c in bids:
        worst = get(scn, met, c)
        d = []
        for v in (3.0, 5.0, 8.0, 12.5, 19.0, 26.0):
            for mb in ("nominal", "F_hi", "r79bk"):
                d.append(get(scn, met, c, v, mb) - get(scn, met, "V298", v, mb))
        row.append("%s %.2f (%+.2f)" % (c, worst, max(d)))
    P("  %-9s %-8s | " % (scn, met) + " | ".join(row))
P("\nwall %.1f s" % (time.time() - T0))
(OUT / "sim_summary.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
