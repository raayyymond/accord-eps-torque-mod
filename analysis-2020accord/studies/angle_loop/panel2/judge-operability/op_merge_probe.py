# -*- coding: utf-8 -*-
r"""op_merge_probe.py -- JUDGE OPERABILITY: the op_probe.py scenarios (cross-centre override, crown, camera step) on the
merged columns of op_merge.py.  ANALYSIS ONLY.  Same engine; the merged Cand rows are defined in op_merge.py (imported
here; its Pool code does not run on import).  Positive control: P2 / E2-A3 / G-P48d must reproduce op_probe.json.

usage: python op_merge_probe.py -> prints the tables quoted in JUDGE-operability §5
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import op_probe as OP  # noqa: E402
ST = OP.ST
import op_merge as OM  # noqa: E402  (registers the merged Cand rows in ITS copy of the scorer module)

for c in OM.MERGED:                     # op_merge loaded the scorer under the same module name; make sure both see them
    ST.CBYID[c.id] = c
CANDS = ["P2", "E2-A3", "G-P48d", "M-P48d-A3", "M-P48-A3", "M-P44d-A3", "M-F24-A3"]
OP.CANDS = CANDS

if __name__ == "__main__":
    res = OP.main(["ctl_lt400", "xc_lt400", "xc_fm2400", "xc3_lt400", "crown_300", "crown_450", "cam30"],
                  tag="op_merge_probe")
    for scn, key in (("ctl_lt400", "lurch"), ("xc_lt400", "lurch"), ("xc_fm2400", "lurch"), ("xc3_lt400", "lurch"),
                     ("crown_300", "err"), ("crown_450", "err"), ("cam30", "th050"), ("cam30", "th100")):
        print(f"\n## {scn}.{key}: worst over the members run; bands <8 | 8-12.5 | 12.5-22 | >22")
        for c in CANDS:
            cells = []
            for lo, hi in ((0, 7.99), (8, 12.5), (12.51, 22), (22.01, 99)):
                v = [r[key] for r in res[scn] if r["cid"] == c and lo <= r["v"] <= hi]
                cells.append(f"{max(v):.2f}" if v else "-")
            print(f"| {c} | " + " | ".join(cells) + " |")
