# -*- coding: utf-8 -*-
"""c1r2_time_summary.py -- one compact table per time-suite JSON: per candidate and speed, dwell-then-jump events
(the five tracking scenarios), hold hunt p2p, tg0.2, hold ratio, latch overshoot, sentinel excursion.
usage: python c1r2_time_summary.py <suite>   -> c1/time_r2_<suite>_summary.txt"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1r2_time as T  # noqa: E402
import c1_lib as C  # noqa: E402

suite = sys.argv[1]
d = json.loads((C.OUT / f"time_r2_{suite}.json").read_text())
rw, res = d["rows"], d["results"]
by = {}
for r in res:
    by.setdefault(r["member"], []).append(r)
out = []
for mem, rr in by.items():
    Tb = T.HT.table(rr, rw)
    out.append(f"\n== member {mem} (suite {suite}) ==  cell: dj events | hold hunt p2p deg | tg0.2 | hold ratio"
               + (" | latch ov deg | sentinel exc deg" if ("ov_latch", T.SPEEDS[0]) in Tb else ""))
    out.append("  m/s  " + " || ".join(f"{r['label'][:24]:^34s}" for r in rw))
    tot = [0] * len(rw)
    for v in T.SPEEDS:
        if ("rh", v) not in Tb:
            continue
        rh, st, s02, s05, ssm = (Tb[(n, v)] for n in ("rh", "st", "s02", "s05", "ssm"))
        cells = []
        for i in range(len(rw)):
            dj = s02["dj_events"][i] + s05["dj_events"][i] + ssm["dj_events"][i] + rh["hold_slips"][i] + st["hold_slips"][i]
            tot[i] += dj
            c = f"{dj:3.0f} {max(rh['hunt_p2p'][i], st['hunt_p2p'][i]):5.2f} {s02['track_gain'][i]:5.3f} {rh['hold_ratio'][i]:5.3f}"
            if ("ov_latch", v) in Tb:
                c += f" {Tb[('ov_latch', v)]['lurch_overshoot'][i]:5.2f} {Tb[('sen_L16', v)]['sen_excursion'][i]:4.1f}"
            cells.append(f"{c:34s}")
        out.append(f"  {v:4g}  " + " || ".join(cells))
    out.append("  total dj events: " + "  ".join(f"{r['label'][:24]}={t:.0f}" for r, t in zip(rw, tot)))
txt = "\n".join(out)
(HERE / f"time_r2_{suite}_summary.txt").write_text(txt, encoding="utf-8")
print(txt)
