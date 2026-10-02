# -*- coding: utf-8 -*-
"""rev_summary.py -- tables for the rev-2 spec from the cached runs (rev_cap_size_{S2,RSN}.json): the F4 grid for the
build (A-TL6144 = rev 2) against V298, rev 1 and the rejected 4-byte edit (A-S6144 = alt4), per amplitude, max over 2
members x 2 seeds in each engine; hold error at 4 s; unwind past centre PER MEMBER (the refuter's D6).  ANALYSIS ONLY."""
import collections
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC  # noqa: E402

T0 = time.perf_counter()
SYS = (("V298", "V298"), ("A-rev1", "rev1"), ("A-S6144", "alt4 (4 B)"), ("A-S5120", "single 5120"), ("A-TL6144", "REV 2"))
L = []
for eng in ("S2", "RSN"):
    R = json.loads((RC.OUT / f"rev_cap_size_{eng}.json").read_text())
    g = collections.defaultdict(list)
    for d in R:
        g[(d["sys"], d["v"], d["An"])].append(d)
    for amp in (45.0, 60.0, 90.0):
        L.append(f"\n#### {eng} engine, {int(amp)} deg hands-off turn-in: overshoot max deg [F4 columns of 4] / |hold err| @4 s max")
        L.append("| system | " + " | ".join(f"{v:g}" for v in (3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0, 10.0, 11.75, 12.5)) + " |")
        L.append("|---|" + "---|" * 10)
        for s, lab in SYS:
            cells = []
            for v in (3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0, 10.0, 11.75, 12.5):
                X = g[(s, v, amp)]
                o = max(x["ovs"] for x in X)
                f4 = sum(x["F4"] for x in X)
                e = max(abs(x["err"]) for x in X)
                cells.append(f"{o:.1f} [{f4}] / {e:.1f}" if v <= 10 else f"{o:.1f} / {e:.1f}")
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
    L.append(f"\n#### {eng}: unwind past centre after a 60-deg turn (deg), median [max] PER MEMBER")
    L.append("| system | member | 3 | 5 | 8 | 10 | 12.5 |")
    L.append("|---|---|---|---|---|---|---|")
    for s, lab in SYS:
        for m in ("r79F", "b_lo*J_hi"):
            cells = []
            for v in (3.0, 5.0, 8.0, 10.0, 12.5):
                X = [x["und"] for x in g[(s, v, 60.0)] if x["member"] == m]
                cells.append(f"{np.median(X):.1f} [{max(X):.1f}]")
            L.append(f"| {lab} | {m} | " + " | ".join(cells) + " |")
L.append(f"\nwall {time.perf_counter() - T0:.2f} s")
txt = "\n".join(L)
print(txt)
(RC.OUT / "rev_summary.md").write_text(txt, encoding="utf-8")
