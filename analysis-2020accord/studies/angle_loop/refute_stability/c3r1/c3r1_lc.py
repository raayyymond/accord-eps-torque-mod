# -*- coding: utf-8 -*-
"""c3r1_lc.py -- limit-cycle diagnostic on the integer lane: long runs (default 24 s) after a step, the theta / T
peak-to-peak and dominant frequency in successive windows.  A sustained (non-decaying) window sequence = limit cycle.
python c3r1_lc.py -> _scratch/.../lc_out.txt"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_intlane as IL  # noqa: E402

D = M.designs()
S_C = 1.155
FR = {"nom": (1.0, 1.0), "FA.83": (0.83, 1.0), "FB.83": (0.83, 1 / S_C), "FA1.155": (1.155, 1.0), "FB1.155": (1.155, 1 / S_C)}
out = []
P = lambda *a: (out.append(" ".join(str(x) for x in a)), print(out[-1], flush=True))  # noqa: E731


def win(x, a, b):
    y = x[a:b]
    yy = (y - y.mean()) * np.hanning(len(y))
    Y = np.abs(np.fft.rfft(yy))
    f = np.fft.rfftfreq(len(y), 1e-3)
    j = int(np.argmax(Y[1:]) + 1)
    return float(np.ptp(y)), float(f[j])


def run(dn, mem, v, e, fr, A, secs=24, fric=0.0, noise=0.0, rf_sub=0):
    kap, jb = FR[fr]
    pl = M.member(mem, v)
    n = secs * 1000
    r = IL.simulate(D[dn], pl, v, n, lambda k: np.full(1, A if k >= 200 else 0.0), e=e, kappa=kap, jb=jb, fric=fric,
                    rate_noise=noise, rf_sub=rf_sub, record=("th", "T", "I", "D", "P", "frozen"))
    th, T = r["th"][0], r["T"][0]
    ws = [(4000, 8000), (8000, 12000), (12000, 16000), (16000, 20000), (20000, 24000)]
    s = "; ".join(f"[{a // 1000}-{b // 1000}s] th {win(th, a, b)[0]:.4f} ({win(th, a, b)[1]:.2f} Hz) T {win(T, a, b)[0]:.0f}"
                  for a, b in ws if b <= n)
    P(f"  {dn} {mem}@{v} e{e} {fr} step {A} fric {fric} noise {noise}: {s}")
    return r


if __name__ == "__main__":
    P("LIMIT-CYCLE DIAGNOSTIC (integer lane, frictionless unless stated)")
    for dn, mem, v, e, fr in (("C3-P", "b_q*ms_free", 15.75, 10, "FA.83"), ("C3-P", "b_q*ms_free", 15.75, 0, "nom"),
                              ("C3-P", "J_hi", 1.0, 0, "FA.83"), ("C3-P", "nominal", 1.0, 0, "nom"),
                              ("C3-P", "nominal", 3.1, 0, "nom"), ("C3-P", "nominal", 15.75, 0, "nom"),
                              ("C3-F", "b_q*ms_free", 15.75, 10, "FB.83"), ("C3-F", "J_hi", 1.0, 0, "FA.83")):
        for A in (0.3, 2.0):
            run(dn, mem, v, e, fr, A)
    (Path(M.OUT) / "lc_out.txt").write_text("\n".join(out), encoding="utf-8")
