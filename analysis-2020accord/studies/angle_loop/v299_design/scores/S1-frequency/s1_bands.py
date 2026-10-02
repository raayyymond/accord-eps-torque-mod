# -*- coding: utf-8 -*-
r"""s1_bands.py -- slices of s1_freq.py's cached rows: band loop gains per speed vs V295 / V298, the R2 gate box with and
without the ms_free products, the R79-frame fails, and the cave-hex table cross-checks.  Analysis only.  ~1 s."""
import json
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s1_freq as S  # noqa: E402

M = S.M
Z = np.load(S.SCR / "s1_rows.npz")
R = Z["R"]
C = {k: i for i, k in enumerate(S.COLS)}
c = lambda A, n: A[:, C[n]]  # noqa: E731
out = []
pr = out.append
# (1) cave-hex cross-checks: the designers' published caves carry the image table byte for byte
for nm, p in (("D1c flight", HERE.parents[1] / "D1-firmware-minimal" / "out" / "d1c_flight.hex"),
              ("D4b cave", S.KIT / "_scratch" / "v299_D4" / "d4b_cave.hex")):
    try:
        d = M.decode_cave(p)
        pr("- %s: table at 0x%X, %d B, rows == V298 image GB-P: %s" % (nm, d["tbl"], d["n"], tuple(d["rows"]) == S.GBP))
    except Exception as ex:                                        # pragma: no cover
        pr("- %s: decode failed (%r)" % (nm, ex))
pr("")
core = (c(R, "aop") == 0) & (c(R, "fric") == 0) & (c(R, "fade") == 1.0)
gate = core & np.isin(c(R, "fr"), S.GATE_FR)
msf = np.array(["ms_free" in S.MEMBERS[int(i)] for i in c(R, "mem")])
pr("| loop | R2 box fails (gate frames, PID+PD) | worst PM (at) | same, ms_free family excluded: fails / worst PM (at) |")
pr("|---|---|---|---|")
for li, l in enumerate(S.LOOPS):
    res = []
    for m in (gate & (c(R, "loop") == li), gate & (c(R, "loop") == li) & ~msf):
        A = R[m]
        fail = (c(A, "PM") < c(A, "bar")) | (c(A, "GMu") < 6) | (c(A, "Tc530") > 3)
        k = int(np.argmin(c(A, "PM") - c(A, "bar")))
        res.append("%d | %.1f (%s @%.2f %s e%d)" % (fail.sum(), c(A, "PM")[k], S.MEMBERS[int(A[k, C["mem"]])],
                                                  S.SPEEDS[int(A[k, C["v"]])], S.FRAMES[int(A[k, C["fr"]])][0],
                                                  int(A[k, C["e"]])))
    pr("| %s | %s | %s |" % (l.name, res[0], res[1].replace(" | ", " / ")))
pr("")
pr("R79-frame fails (core, PID): member @ v frame e PM bar")
for li, l in enumerate(S.LOOPS):
    m = core & (c(R, "loop") == li) & np.isin(c(R, "fr"), (5, 6)) & ((c(R, "PM") < c(R, "bar")) | (c(R, "GMu") < 6))
    A = R[m]
    s = sorted(set("%s@%.2f %s e%d PM %.1f" % (S.MEMBERS[int(a[C["mem"]])], S.SPEEDS[int(a[C["v"]])],
                                                S.FRAMES[int(a[C["fr"]])][0], int(a[C["e"]]), a[C["PM"]]) for a in A))
    pr("- %s: %d -> %s" % (l.name, len(A), "; ".join(s[:8]) + (" ..." if len(s) > 8 else "")))
pr("")
# (2) band gains per speed, core gate frames, PID: max over members/frames/e of |L|band / V295 and / V298 (same point)
pr("| v | " + " | ".join("%s 13-17/V295 | 18-22/V295 | 5-30/V298" % l.name for l in S.LOOPS[:5]) + " |")
pr("|---|" + "---|" * 15)
B = {}
for iv, v in enumerate(S.SPEEDS):
    cells = []
    for li, l in enumerate(S.LOOPS[:5]):
        A = R[gate & (c(R, "loop") == li) & (c(R, "v") == iv)]
        a1 = (c(A, "L1517") / c(A, "V295_1517")).max()
        a2 = (c(A, "L1822") / c(A, "V295_1822")).max()
        a3 = c(A, "r530").max()
        B["%s|%.2f" % (l.name, v)] = (a1, a2, a3)
        cells.append("%.3f | %.3f | %.3f" % (a1, a2, a3))
    pr("| %.2f | %s |" % (v, " | ".join(cells)))
pr("")
pr("bands wall %.1f s" % (time.time() - T0))
(HERE / "out" / "s1_bands.md").write_text("\n".join(out) + "\n", encoding="utf-8")
json.dump(B, open(HERE / "out" / "s1_bands.json", "w"), indent=0)
print("\n".join(out))
