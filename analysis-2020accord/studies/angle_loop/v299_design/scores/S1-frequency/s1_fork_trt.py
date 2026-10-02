# -*- coding: utf-8 -*-
"""s1_fork_trt.py -- fork-coupled loop margins per round-trip delay from s1_freq.py's cached rows (all 19 members,
frames nom / FA.83 / FB1.155, e 0/10, fade 1): min PM (at) and min GM per (kind, loop, PID/PD, Trt).  ~0.5 s."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402
FR = np.load(S.SCR / "s1_rows.npz")["FR"]
C = {k: i for i, k in enumerate(S.FCOLS)}
out = ["| kind | loop | state | Trt 30: PM / GM | Trt 60: PM / GM | Trt 90: PM / GM | worst point at Trt 60 |", "|---|---|---|---|---|---|---|"]
for ki, kind in enumerate(S.KINDS):
    for li, l in enumerate(S.LOOPS):
        for noI in (0, 1):
            cells, at = [], ""
            for trt in S.TRT:
                m = (FR[:, C["kind"]] == ki) & (FR[:, C["loop"]] == li) & (FR[:, C["noI"]] == noI) & \
                    np.isclose(FR[:, C["trt"]], trt) & (FR[:, C["fade"]] == 1.0)
                A = FR[m]
                if not len(A):
                    break
                k = int(np.argmin(A[:, C["PM"]]))
                cells.append("%.1f / %.1f" % (A[k, C["PM"]], A[:, C["GMu"]].min()))
                if trt == 0.06:
                    at = "%s @%.2f %s e%d (fc %.2f Hz)" % (S.MEMBERS[int(A[k, C["mem"]])], S.SPEEDS[int(A[k, C["v"]])],
                                                         S.FRAMES[int(A[k, C["fr"]])][0], int(A[k, C["e"]]), A[k, C["fc"]])
            if cells:
                out.append("| %s | %s | %s | %s | %s |" % (kind, l.name, "PD" if noI else "PID", " | ".join(cells), at))
(HERE / "out" / "s1_fork_trt.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
