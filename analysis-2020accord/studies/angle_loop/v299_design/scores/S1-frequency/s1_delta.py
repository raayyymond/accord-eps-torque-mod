# -*- coding: utf-8 -*-
r"""s1_delta.py -- every candidate loop vs V298 at IDENTICAL points (member, speed, frame, e, PID/PD, op-point, friction,
fade) from s1_freq.py's cached rows: min dPM (at), count of NEW sub-30 / sub-bar points (V298 passes, candidate does not),
and points the candidate RESCUES.  Analysis only.  ~1 s."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402

R = np.load(S.SCR / "s1_rows.npz")["R"]
C = {k: i for i, k in enumerate(S.COLS)}
KEY = ["mem", "v", "fr", "e", "noI", "aop", "fric", "fade"]
base = R[R[:, C["loop"]] == 0]
out, J = [], {}
out.append("| loop | block | n | min dPM vs V298 (at) | max dPM | new PM<30 | new PM<bar | rescued PM<30 | new GM<6 |")
out.append("|---|---|---|---|---|---|---|---|---|")
blocks = {"core-gate": lambda A: (A[:, C["aop"]] == 0) & (A[:, C["fric"]] == 0) & np.isin(A[:, C["fr"]], S.GATE_FR) & (A[:, C["fade"]] == 1),
          "core-R79": lambda A: (A[:, C["aop"]] == 0) & (A[:, C["fric"]] == 0) & np.isin(A[:, C["fr"]], (5, 6)),
          "op-points": lambda A: A[:, C["aop"]] > 0,
          "friction": lambda A: A[:, C["fric"]] > 0,
          "hands-on x0.30": lambda A: A[:, C["fade"]] != 1}
for li in range(1, len(S.LOOPS)):
    X = R[R[:, C["loop"]] == li]
    assert X.shape == base.shape and np.array_equal(X[:, [C[k] for k in KEY]], base[:, [C[k] for k in KEY]])
    for bn, f in blocks.items():
        m = f(base)
        A, B = X[m], base[m]
        d = A[:, C["PM"]] - B[:, C["PM"]]
        d = np.where(np.isfinite(d), d, 0.0)
        k = int(np.argmin(d))
        at = "%s @%.2f %s e%d %s" % (S.MEMBERS[int(A[k, C["mem"]])], S.SPEEDS[int(A[k, C["v"]])],
                                    S.FRAMES[int(A[k, C["fr"]])][0], int(A[k, C["e"]]), "PD" if A[k, C["noI"]] else "PID")
        n30 = int(((A[:, C["PM"]] < 30) & (B[:, C["PM"]] >= 30)).sum())
        nbar = int(((A[:, C["PM"]] < A[:, C["bar"]]) & (B[:, C["PM"]] >= B[:, C["bar"]])).sum())
        r30 = int(((A[:, C["PM"]] >= 30) & (B[:, C["PM"]] < 30)).sum())
        ngm = int(((A[:, C["GMu"]] < 6) & (B[:, C["GMu"]] >= 6)).sum())
        J["%s|%s" % (S.LOOPS[li].name, bn)] = dict(n=int(m.sum()), min_dPM=float(d[k]), at=at, max_dPM=float(d.max()),
                                                   new30=n30, newbar=nbar, rescued30=r30, newGM6=ngm)
        out.append("| %s | %s | %d | %+.1f (%s) | %+.1f | %d | %d | %d | %d |" % (S.LOOPS[li].name, bn, m.sum(), d[k], at,
                                                                          d.max(), n30, nbar, r30, ngm))
(HERE / "out" / "s1_delta.md").write_text("\n".join(out) + "\n", encoding="utf-8")
json.dump(J, open(HERE / "out" / "s1_delta.json", "w"), indent=1)
print("\n".join(out))
