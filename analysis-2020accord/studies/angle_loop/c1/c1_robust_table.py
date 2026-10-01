# -*- coding: utf-8 -*-
"""c1_robust_table.py -- compact per-member table of the time-harness robust suite for C1 and C0 (from time_robust.json
and time_nominal.json): tg0.2 / tg0.5 / dwell-then-jump+slip events / hold ratio / max T_hf in the holds, at >= 8 m/s,
plus the event totals at 3-7 m/s.  ANALYSIS ONLY."""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C
HT = C.HT
out = []
for suite in ("nominal", "robust"):
    d = json.loads((C.OUT / f"time_{suite}.json").read_text())
    rows = d["rows"]
    by = {}
    for r in d["results"]:
        by.setdefault(r["member"], []).append(r)
    for mem, rr in by.items():
        T = HT.table(rr, rows)
        for i in (0, 5):        # C1, C0 as listed
            lab = "C1" if i == 0 else "C0"
            cells, low = [], 0
            for v in (3.0, 5.0, 5.5, 6.0, 7.0):
                if ("rh", v) in T:
                    low += sum(T[(n, v)][k][i] for n, k in (("s02", "dj_events"), ("s05", "dj_events"), ("ssm", "dj_events"), ("rh", "hold_slips"), ("st", "hold_slips")))
            for v in (8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0):
                rh, st, s02, s05, ssm = (T[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm"))
                dj = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
                cells.append(f"{s02['track_gain'][i]:.2f}/{s05['track_gain'][i]:.2f} {int(dj)} {rh['hold_ratio'][i]:.2f}")
            out.append(f"| {mem} | {lab} | {int(low)} | " + " | ".join(cells) + " |")
hdr = "| member | build | events 3-7 m/s | " + " | ".join(f"{v:g}" for v in (8, 10, 11.9, 12.5, 15, 17, 19, 22, 26, 30)) + " |"
txt = "cell = tg0.2/tg0.5 events hold\n" + hdr + "\n|" + "---|" * 13 + "\n" + "\n".join(out)
(HERE / "robust_table.txt").write_text(txt, encoding="utf-8")
print(txt)
