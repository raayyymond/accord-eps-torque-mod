"""ADVERSARY a5: second attempt at a plant-path D_act (a4's FIR failed its control because a lightly
damped 1.5 Hz mode rings far longer than the FIR window). ARX: own lags of the measured rate absorb the
ringing compactly, the command enters at tau = 0..200 ms in 5 ms steps, and the DELAY is read as the onset
of the b coefficients (b_j must be 0 for tau_j < D_act). Same mandated synthetic controls as a4.
"""
import sys
from pathlib import Path
import numpy as np
import a4_onset as A4

OUT = Path(__file__).resolve().parent / "out"
TAUS = np.arange(0.0, 0.2001, 0.005)
NA = 6


def arx(tg, u, tsamp, y, mask):
    n = len(y)
    rows = np.where(mask)[0]
    rows = rows[rows > NA + 2]
    Y = y[rows]
    cols = [y[rows - i] for i in range(1, NA + 1)]
    for tau in TAUS:
        a = np.clip(np.round((tsamp[rows] - tau - tg[0]) / 0.001).astype(np.int64), 0, len(u) - 1)
        cols.append(u[a])
    X = np.column_stack(cols + [np.ones(len(rows))])
    th, *_ = np.linalg.lstsq(X, Y, rcond=None)
    r2 = 1 - np.var(Y - X @ th) / np.var(Y)
    return th[:NA], th[NA:NA + len(TAUS)], r2


def onset_b(b, frac=0.15):
    s = np.cumsum(b)
    pk = np.max(np.abs(s))
    if pk <= 0:
        return np.nan
    sgn = np.sign(s[np.argmax(np.abs(s))])
    z = sgn * s / pk
    i = np.argmax(z > frac)
    if i == 0:
        return np.nan
    # linear interpolation of the rise to the frac level, then extrapolate the local slope to zero
    j0, j1 = max(i - 1, 0), min(i + 2, len(z) - 1)
    A = np.polyfit(TAUS[j0:j1 + 1], z[j0:j1 + 1], 1)
    return (-A[1] / A[0]) * 1e3 if A[0] > 0 else np.nan


def run(route, D_ms=None, **kw):
    D = np.load(OUT / f"raw_{route}.npz")
    t_cst, sa, sr, v, sp = D["t_cst"], D["sa"], D["sr"], D["v"], D["spress"]
    t_e4, e4 = D["t_e4"], D["e4"]
    tg, u = A4.cmd_grid(t_e4, e4, t_cst[0] - 0.3, t_cst[-1] + 0.1)
    if D_ms is not None:
        sa, sr = A4.sim(tg, u, t_cst, v, D_ms, **kw)
    ie = np.clip(np.searchsorted(t_e4, t_cst) - 1, 0, len(e4) - 1)
    mask = (sp < 0.5) & (np.abs(e4[ie]) > 0.5)
    mask[:300] = False; mask[-300:] = False
    a, b, r2 = arx(tg, u, t_cst, sr.astype(float), mask)
    Dh = onset_b(b)
    tag = f"{route[:8]} {'synth D=%.0f' % D_ms if D_ms is not None else 'REAL'}" + \
          (f" fb{kw.get('fb',0):g} dist{kw.get('dist',0):g} J{kw.get('J',8e-5):g} b{kw.get('b',6e-4):g}"
           if D_ms is not None else "")
    print(f"  {tag:52s} onset {Dh:7.2f} ms  R2 {r2:.4f}  sum(b) {b.sum():+.3f}  a1 {a[0]:+.3f}")
    return Dh


if __name__ == "__main__":
    r = sys.argv[1]
    print("=== OPEN LOOP (mandated: 30 and 60 ms within 5 ms) ===")
    for Dt in (0, 15, 30, 60, 90):
        run(r, D_ms=Dt)
    print("=== disputed J / b / F / k ===")
    run(r, D_ms=30, J=1e-3, b=3e-3); run(r, D_ms=60, J=1e-3, b=3e-3)
    run(r, D_ms=30, J=3e-4); run(r, D_ms=30, F=0.0); run(r, D_ms=30, ks=3.0)
    print("=== CLOSED LOOP + unmeasured road torque (the real situation) ===")
    run(r, D_ms=30, fb=6e-4); run(r, D_ms=60, fb=6e-4)
    run(r, D_ms=30, fb=6e-4, dist=0.015); run(r, D_ms=60, fb=6e-4, dist=0.015)
    print("=== REAL ===")
    run(r)
