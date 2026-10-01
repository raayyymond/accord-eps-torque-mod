# -*- coding: utf-8 -*-
"""nl_realref_diag.py -- attribution of the realistic-path tracking deficit: band slope vs reference scale (1.0 / 0.3 /
0.1: a linear loop is scale-invariant) and with the I clamp lifted (ICL 4096 -> 16383, a DIAGNOSTIC only, not a
proposal), P2 and F2, nominal and nominal_nf.  ANALYSIS ONLY."""
import sys
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_realref as RR  # noqa: E402
import nl_sim as S  # noqa: E402
sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
R = RR.runs()
lines = []
for band in ("8-15", "15-22", ">22"):
    rr = R[band]
    for icl in (4096, 16383):
        S.ICL = icl
        cols, refs, tags = [], [], []
        for (tr, sa, vm) in rr:
            for sc in (1.0, 0.3, 0.1):
                for im in ("P2", "F2"):
                    for mem in ("nominal", "nominal_nf"):
                        cols.append(dict(impl=im, member=mem, v=vm, age=0)); refs.append((tr, sa * sc)); tags.append((sc, im, mem))
        dur = max(tr[-1] for tr, _ in refs) + 0.5
        fr = np.arange(0, dur, 0.01)
        REF = np.stack([np.interp(fr, tr, sa, right=sa[-1]) for tr, sa in refs], 1)
        r = S.run(cols, S.Scn(dur=dur, ref=lambda t: REF[min(int(round(t * 100)), REF.shape[0] - 1)], th0=REF[0].copy()))
        th = r["th"][::10].astype(float)
        for key in sorted(set(tags)):
            X, Y = [], []
            for j, tg in enumerate(tags):
                if tg != key:
                    continue
                n = int(refs[j][0][-1] * 100)
                X.append(signal.sosfiltfilt(sos, REF[:n, j])[400:]); Y.append(signal.sosfiltfilt(sos, th[:n, j])[400:])
            X, Y = np.concatenate(X), np.concatenate(Y)
            b = np.linalg.lstsq(np.vstack([X, np.ones_like(X)]).T, Y, rcond=None)[0][0]
            lines.append(f"band {band:>5s} ICL {icl:5d} scale {key[0]:.1f} {key[1]} {key[2]:11s} slope {b:.3f}")
            print(lines[-1], flush=True)
S.ICL = 4096
(RR.OUT / "realref_diag.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
