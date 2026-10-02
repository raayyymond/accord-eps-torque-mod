# -*- coding: utf-8 -*-
r"""s2_report.py -- tabulate s2_results.json identically for every candidate (markdown to stdout + s2_tables.md).
Cells: plant member r79F, MEDIAN over residual-noise seeds 1-3 ('med'); [worst over members r79F, b_lo*J_hi and seeds
1-3] where shown.  TI also reports seed 0 (the deterministic twist, no residual).  < 1 s."""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
T0 = time.perf_counter()
D = json.loads((HERE.parents[5] / "_scratch" / "v299_S2" / "s2_results.json").read_text())
CIDS = ("V298", "D1c", "D1a", "D1c+G0", "D2a", "D2b", "D3a", "D3b", "D4b", "D4a", "D4b+S13", "D5b", "D5a",
        "G:D1c+D3fork", "G:D1c+D5fork", "G:D1c+D2bfork")
BETTER = {}


def sel(g, cid, v=None, x=None, member="r79F", seeds=(1, 2, 3)):
    return [r for r in D["rows"][g] if r["cid"] == cid and (v is None or r["v"] == v) and (x is None or r["x"] == x)
            and (member is None or r["member"] == member) and r["s"] in seeds]


def med(g, cid, k, v=None, x=None, member="r79F", seeds=(1, 2, 3)):
    xs = [r[k] for r in sel(g, cid, v, x, member, seeds)]
    xs = [np.inf if q is None else q for q in xs]
    return float(np.median(xs)) if xs else np.nan


def worst(g, cid, k, v=None, x=None, hi_bad=True, seeds=(1, 2, 3)):
    xs = [r[k] for r in sel(g, cid, v, x, None, seeds)]
    xs = [(np.inf if hi_bad else -np.inf) if q is None else q for q in xs]
    return float(max(xs) if hi_bad else min(xs)) if xs else np.nan


def f(x, p=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    if np.isinf(x):
        return "never"
    return f"{x:.{p}f}"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


L = []
# ---------------------------------------------------------------------------------------------------- SUMMARY
head = ["cand", "TI t90 s 3/8", "TI cov(sent sp) 3/8", "TI ω pk 3/8", "TI ovs ° [worst]", "TI settle s [worst]",
        "tap pk %rail [worst]", "hand-frz tog/s 3/8", "I kept 3/8", "stall-surge (TI 2 spd)", "O1 twist trips (TI)",
        "C2 fast g@0.5s 15/25", "C2 slow e_rms 15/25", "LH lurch ° worst", "OV O1 ms 5/15", "OV T_res/T_pre 5/15"]
rows = []
for c in CIDS:
    rows.append([
        c,
        f(med("TI", c, "t90", 3.0)) + "/" + f(med("TI", c, "t90", 8.0)),
        f(med("TI", c, "cov_sp", 3.0)) + "/" + f(med("TI", c, "cov_sp", 8.0)),
        f(med("TI", c, "wpk", 3.0), 0) + "/" + f(med("TI", c, "wpk", 8.0), 0),
        f(max(med("TI", c, "ovs", 3.0), med("TI", c, "ovs", 8.0)), 1) + f" [{f(worst('TI', c, 'ovs'), 1)}]",
        f(max(med("TI", c, "settle", 3.0), med("TI", c, "settle", 8.0))) + f" [{f(worst('TI', c, 'settle'))}]",
        f(100 * max(med("TI", c, "tap_pk", 3.0), med("TI", c, "tap_pk", 8.0)), 0)
        + f" [{f(100 * max(worst(g, c, 'tap_pk') for g in ('TI', 'C2', 'LH', 'OV')), 0)}]",
        f(med("TI", c, "hand_tog_s", 3.0), 1) + "/" + f(med("TI", c, "hand_tog_s", 8.0), 1),
        f(med("TI", c, "kept", 3.0)) + "/" + f(med("TI", c, "kept", 8.0)),
        f(med("TI", c, "ss", 3.0) + med("TI", c, "ss", 8.0), 0),
        f(med("TI", c, "o1_eps", 3.0) + med("TI", c, "o1_eps", 8.0), 0),
        f(med("C2", c, "g05", 15.0, "fast")) + "/" + f(med("C2", c, "g05", 25.0, "fast")),
        f(med("C2", c, "erms", 15.0, "slow")) + "/" + f(med("C2", c, "erms", 25.0, "slow")),
        f(max(worst("LH", c, "lurch", v) for v in (5.0, 15.0)), 1),
        f(med("OV", c, "t_o1_ms", 5.0), 0) + "/" + f(med("OV", c, "t_o1_ms", 15.0), 0),
        f(med("OV", c, "Tres", 5.0) / med("OV", c, "Tpre", 5.0)) + "/"
        + f(med("OV", c, "Tres", 15.0) / med("OV", c, "Tpre", 15.0)),
    ])
L.append("### S0 summary (r79F, median of seeds 1-3; [worst over members x seeds])\n")
L.append(table(head, rows))

# ---------------------------------------------------------------------------------------------------- TI detail
for v in (3.0, 8.0):
    head = ["cand", "cov@0.5s", "cov(sent)", "t_sent s", "t90 s", "ω pk", "ovs °", "settle s", "max lag °", "unwind t90 s",
            "under °", "tap %rail", "I kept", "hand-lost", "frz tog/s", "O1 eps", "O1 frac", "stall-surge", "DJ",
            "r48 °/s", "r1.6-3 °/s", "seed0 t90", "seed0 tog/s", "heavy t90 [worst]"]
    rows = []
    for c in CIDS:
        g = lambda k, p=2: f(med("TI", c, k, v), p)  # noqa: E731
        rows.append([c, g("cover05"), g("cov_sp"), g("t_spa"), g("t90"), g("wpk", 0), g("ovs", 1), g("settle"),
                     g("maxlag", 1), g("t90_out"), g("under", 1), f(100 * med("TI", c, "tap_pk", v), 0), g("kept"),
                     g("hand_lost"), g("hand_tog_s", 1), g("o1_eps", 0), g("o1_frac"), g("ss", 0), g("dj", 0),
                     g("r48", 1), g("r163", 1), f(med("TI", c, "t90", v, seeds=(0,))),
                     f(med("TI", c, "hand_tog_s", v, seeds=(0,)), 1),
                     f(med("TI", c, "t90", v, member="b_lo*J_hi")) + f" [{f(worst('TI', c, 't90', v))}]"])
    L.append(f"\n### TI 60° turn-in at {v:.0f} m/s (plan {320 if v < 5 else 216} deg/s)\n")
    L.append(table(head, rows))

# ---------------------------------------------------------------------------------------------------- C2 detail
head = ["cand"] + [f"{x} {v:.0f}: {k}" for v in (15.0, 25.0) for x, k in
                   (("fast", "t90"), ("fast", "g@0.5"), ("fast", "ovs"), ("slow", "e_rms"), ("slow", "max|e|"),
                    ("slow", "DJ"), ("slow", "dwell"))]
rows = []
for c in CIDS:
    r = [c]
    for v in (15.0, 25.0):
        r += [f(med("C2", c, "t90", v, "fast")), f(med("C2", c, "g05", v, "fast")), f(med("C2", c, "ovs", v, "fast")),
              f(med("C2", c, "erms", v, "slow")), f(med("C2", c, "maxlag", v, "slow")),
              f(med("C2", c, "dj", v, "slow"), 0), f(med("C2", c, "dwell", v, "slow"), 0)]
    rows.append(r)
L.append("\n### C2 2° correction (fast 0.25 s ramp; slow 1.33 deg/s drift)\n")
L.append(table(head, rows))

# ---------------------------------------------------------------------------------------------------- LH detail
head = ["cand"] + [f"{x}{v:.0f}: {k}" for v in (5.0, 15.0) for x in ("c", "o") for k in ("lurch", "ΔI T", "frz", "tap")] \
    + ["worst lurch (all)", "O1 eps (med, all)"]
rows = []
for c in CIDS:
    r = [c]
    for v in (5.0, 15.0):
        for x in ("c", "o"):
            r += [f(med("LH", c, "lurch", v, x), 1), f(med("LH", c, "dI_T", v, x), 0), f(med("LH", c, "frz_hold", v, x)),
                  f(100 * med("LH", c, "tap_hold", v, x), 0)]
    r += [f(worst("LH", c, "lurch"), 1),
          f(sum(med("LH", c, "o1_eps", v, x) for v in (5.0, 15.0) for x in ("c", "o")), 0)]
    rows.append(r)
L.append("\n### LH hold under a 400-count light hand (c = held 30 % toward centre, o = 30 % outward), release\n")
L.append(table(head, rows))

# ---------------------------------------------------------------------------------------------------- OV detail
head = ["cand"] + [f"{v:.0f}: {k}" for v in (5.0, 15.0) for k in
                   ("t_O1 ms", "t |T|<½ ms", "T_res T", "T_pre T", "tap pk under hand %", "hand T", "rel t90 s",
                    "rel ovs °")]
rows = []
for c in CIDS:
    r = [c]
    for v in (5.0, 15.0):
        r += [f(med("OV", c, "t_o1_ms", v), 0), f(med("OV", c, "t_yield_ms", v), 0), f(med("OV", c, "Tres", v), 0),
              f(med("OV", c, "Tpre", v), 0), f(100 * med("OV", c, "ov_tap", v), 0), f(med("OV", c, "hf_hold", v), 0),
              f(med("OV", c, "rel_t90", v)), f(med("OV", c, "rel_ovs", v), 1)]
    rows.append(r)
L.append("\n### OV hand override (word 1500, hand drags the wheel to centre, 1.5 s), release\n")
L.append(table(head, rows))

# ---------------------------------------------------------------------------------------------------- RD detail
head = ["cand"] + [f"{v:.0f}: {k}" for v in (3.0, 8.0) for k in ("T_pre", "T +50 ms", "T +150 ms", "ω pk", "Δθ 1 s")]
rows = []
for c in CIDS:
    r = [c]
    for v in (3.0, 8.0):
        r += [f(med("RD", c, "Tpre", v, seeds=(1,)), 0), f(med("RD", c, "T50", v, seeds=(1,)), 0),
              f(med("RD", c, "T150", v, seeds=(1,)), 0), f(med("RD", c, "wpk", v, seeds=(1,)), 1),
              f(med("RD", c, "dth1", v, seeds=(1,)), 1)]
    rows.append(r)
L.append("\n### RD request drop mid-turn (hold at A/2)\n")
L.append(table(head, rows))
L.append("\nwalls (s): " + ", ".join(f"{k} {v:.1f}" for k, v in D["walls"].items()) + f"; report {time.perf_counter() - T0:.2f} s")
txt = "\n".join(L)
(HERE / "s2_tables.md").write_text(txt + "\n", encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print(txt)
