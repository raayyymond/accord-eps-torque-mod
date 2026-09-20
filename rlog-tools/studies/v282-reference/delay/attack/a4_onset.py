"""ADVERSARY a4: MY OWN plant-path D_act estimator + the brief's mandated synthetic control.

Idea, different from all four inherited estimators. Fit a TWO-SIDED nonparametric FIR of the measured
steering rate on the command, tau from -80 to +200 ms. Two things then fall out:
  * the causal plant response lives at tau >= D_act; its STEP response s(tau) = cumsum(h) is, for
    J*acc + b*rate + k*angle = u(t-D), equal to (tau - D)/J for small tau - D. So a straight line through
    the leading edge gives D as its ROOT and 1/J as its SLOPE -- no plant model, no band choice, no xcorr.
  * the CLOSED-LOOP contamination (u responding to y) lives at tau < 0 and is absorbed there instead of
    biasing the onset. That is the failure mode that voided e1/e2/e3.
Positive control: J*acc = u(t-D) - b*rate - k(v)*angle - F*sign(rate), Karnopp stick-slip, driven by the
ACTUAL logged 0xE4 (ZOH at the real send stamps), sampled at the REAL carState stamps, angle quantised
0.1 deg and rate 1 deg/s. Open loop, closed loop, and closed loop + unmeasured road torque.
"""
import sys
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent / "out"
GRID = 0.001
DT = 0.005
TAUS = np.arange(-0.08, 0.2001, DT)
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]


def cmd_grid(t_e4, e4, t0, t1):
    tg = np.arange(t0, t1, GRID)
    k = np.clip(np.searchsorted(t_e4, tg, side="right") - 1, 0, len(e4) - 1)
    u = e4[k] / -4089.0                                  # openpilot output-torque units, +left
    u[tg < t_e4[0]] = 0.0
    return tg, u


def sim(tg, u, tsamp, vsamp, D_ms, J=8e-5, b=6e-4, F=0.02, ks=1.0, fb=0.0, dist=0.0, seed=1):
    """1 kHz plant, Karnopp stick-slip; optional rate feedback (gain fb, one 10 ms frame old, RC 0.01)
    and an unmeasured band-limited road torque (std dist)."""
    n = len(tg)
    sh = int(round(D_ms / 1e3 / GRID))
    k_of = np.interp(np.interp(tg, tsamp, vsamp), HOLD_V_BP, HOLD_K_V) * ks
    rng = np.random.default_rng(seed)
    d = np.zeros(n)
    if dist > 0:
        w = rng.standard_normal(n)
        a = np.exp(-2 * np.pi * 4.0 * GRID)
        s = 0.0
        for i in range(n):
            s = a * s + (1 - a) * w[i]
            d[i] = s
        d *= dist / max(d.std(), 1e-9)
    ang = np.zeros(n); rate = np.zeros(n)
    x = 0.0; r = 0.0; rf = 0.0; arc = np.exp(-2 * np.pi / (2 * np.pi * 0.01) * GRID)
    arc = np.exp(-GRID / 0.01)
    ub = np.concatenate([np.zeros(sh), u[:n - sh]])
    for i in range(1, n):
        ui = ub[i] + d[i]
        if fb:
            ui += -fb * rf                                # rate feedback on the filtered measured rate
        net = ui - b * r - k_of[i] * x
        if abs(r) < 1e-3 and abs(net) <= F:
            r = 0.0
        else:
            r += GRID * (net - F * np.sign(r if abs(r) > 1e-9 else net)) / J
        x += GRID * r
        ang[i] = x; rate[i] = r
        if i % 10 == 0:                                   # 100 Hz measurement into the feedback
            rf = arc * rf + (1 - arc) * (np.round(r))
    ka = np.clip(np.round((tsamp - tg[0]) / GRID).astype(np.int64), 0, n - 1)
    return np.round(ang[ka] * 10) / 10, np.round(rate[ka])


def fir(tg, u, tsamp, y, mask, lam=1e-3):
    idx = np.where(mask)[0]
    X = np.empty((len(idx), len(TAUS)))
    for j, tau in enumerate(TAUS):
        a = np.clip(np.round((tsamp[idx] - tau - tg[0]) / GRID).astype(np.int64), 0, len(u) - 1)
        X[:, j] = u[a]
    X = X - X.mean(0)
    yy = y[idx] - y[idx].mean()
    NT = len(TAUS)
    P = np.zeros((NT + 2, NT))
    for j in range(NT):
        P[j, j] = 1.0
        if j + 1 < NT:
            P[j, j + 1] = -2.0
        if j + 2 < NT:
            P[j, j + 2] = 1.0
    XtX = X.T @ X
    s = np.trace(XtX) / NT
    h = np.linalg.solve(XtX + lam * s * P.T @ P, X.T @ yy)
    r2 = 1 - np.var(yy - X @ h) / np.var(yy)
    return h, r2


def onset(h, lo_ms=0.0, win=0.06):
    """straight line through the leading edge of the step response: root = D, slope = 1/J"""
    s = np.cumsum(h)
    D = lo_ms / 1e3
    for _ in range(6):
        m = (TAUS >= D) & (TAUS <= D + win)
        if m.sum() < 4:
            return np.nan, np.nan
        A = np.polyfit(TAUS[m], s[m], 1)
        if A[0] <= 0:
            return np.nan, np.nan
        Dn = -A[1] / A[0]
        if abs(Dn - D) < 1e-4:
            D = Dn; break
        D = np.clip(Dn, TAUS[0], TAUS[-1] - win)
    return D * 1e3, 1.0 / A[0]


def run(route, D_ms=None, **kw):
    D = np.load(OUT / f"raw_{route}.npz")
    t_cst, sa, sr, v, sp = D["t_cst"], D["sa"], D["sr"], D["v"], D["spress"]
    t_e4, e4 = D["t_e4"], D["e4"]
    tg, u = cmd_grid(t_e4, e4, t_cst[0] - 0.3, t_cst[-1] + 0.1)
    if D_ms is not None:
        sa, sr = sim(tg, u, t_cst, v, D_ms, **kw)
    ie = np.clip(np.searchsorted(t_e4, t_cst) - 1, 0, len(e4) - 1)
    mask = (sp < 0.5) & (np.abs(e4[ie]) > 0.5) & (np.abs(TAUS[0]) < 1)
    mask = (sp < 0.5) & (np.abs(e4[ie]) > 0.5)
    mask[:250] = False; mask[-250:] = False
    out = {}
    for nm, y in (("rate", sr.astype(float)),):
        h, r2 = fir(tg, u, t_cst, y, mask)
        Dh, Jh = onset(h)
        neg = np.abs(h[TAUS < -0.005]).sum() / max(np.abs(h).sum(), 1e-12)
        tag = f"{route[:8]} {'synth D=%.0f' % D_ms if D_ms is not None else 'REAL'}" \
              + (f" fb{kw.get('fb',0):g} dist{kw.get('dist',0):g} J{kw.get('J',8e-5):g}" if D_ms is not None else "")
        print(f"  {tag:46s} onset D {Dh:7.2f} ms  J_fit {Jh:9.2e}  R2 {r2:.3f}  |h(tau<0)|share {neg:.3f}")
        out[nm] = (Dh, Jh, r2)
    return out


if __name__ == "__main__":
    r = sys.argv[1]
    print("=== OPEN LOOP controls (mandated: recover 30 and 60 ms within 5 ms) ===")
    for Dt in (0, 30, 60):
        run(r, D_ms=Dt)
    print("=== sensitivity to the disputed J and b ===")
    run(r, D_ms=30, J=1e-3, b=3e-3); run(r, D_ms=60, J=1e-3, b=3e-3)
    run(r, D_ms=30, J=3e-4); run(r, D_ms=30, F=0.0); run(r, D_ms=30, ks=3.0)
    print("=== CLOSED LOOP, then closed loop + unmeasured road torque (the real situation) ===")
    run(r, D_ms=30, fb=6e-4); run(r, D_ms=60, fb=6e-4)
    run(r, D_ms=30, fb=6e-4, dist=0.015); run(r, D_ms=60, fb=6e-4, dist=0.015)
    run(r, D_ms=30, fb=3e-3, dist=0.015)
    print("=== REAL ===")
    run(r)
