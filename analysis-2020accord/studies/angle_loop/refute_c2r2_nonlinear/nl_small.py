# -*- coding: utf-8 -*-
"""nl_small.py -- small-correction tracking at >= 8 m/s: per-speed detail (wire gain, fit gain, dwell-then-jump events
and largest jump, stuck %) with each member's friction-free twin as the linear control.  ANALYSIS ONLY."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_lens as L  # noqa
import nl_sim as S  # noqa
SP = (8.0, 9.0, 10.0, 11.0, 11.75, 12.25, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 21.75, 24.0, 26.9)
MEM = ("nominal", "nominal_nf", "bc", "bc_nf", "F_hi", "b_lo*J_hi", "b_lo*J_hi_nf")
out = []
for scn_name in ("mic03", "mic05", "mic10", "s05"):
    cols = [dict(impl=i, member=m, v=v, age=0) for m in MEM for v in SP for i in ("P2", "F2")]
    scn, meta = L.scenario(scn_name, cols)
    r = S.run(cols, scn)
    m = L.metrics(scn_name, meta, r, cols)
    out.append(f"\n## {scn_name} (amp {'0.3*A' if scn_name == 's05' else meta.get('amp')}, f {meta['f']} Hz): per column  gain / fit / dj (max jump deg) / stuck%")
    for mem in MEM:
        for im in ("P2", "F2"):
            cells = []
            for v in SP:
                j = [k for k, c in enumerate(cols) if c["member"] == mem and c["impl"] == im and c["v"] == v][0]
                cells.append(f"{v:g}:{m['gain'][j]:.2f}/{m['fit_gain'][j]:.2f}/{int(m['dj'][j])}({m['dj_max'][j]:.2f})/{m['stick_pct'][j]:.0f}")
            out.append(f"{im} {mem:13s} " + "  ".join(cells))
    print("\n".join(out[-15:]), flush=True)
(L.OUT / "small.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
