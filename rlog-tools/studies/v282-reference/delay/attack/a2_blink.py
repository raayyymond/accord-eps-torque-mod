"""ADVERSARY a2: the B link (0xE4 on the wire -> the firmware's delivered-lane-torque tap on 0x1AB/427),
which carries ~30 of the adjudicated 43 ms of D_act. Re-measured with a NONPARAMETRIC REGULARISED FIR:
no pole assumed, no pure delay assumed. The FIR's own DTFT then gives the phase delay at 1.8/2.5/3.5 Hz,
which is the quantity the phase arithmetic actually needs.

Why this link is identifiable at all: in V293 torque mode the EPS feedback clamp is 0, so the delivered
lane torque is a function of the COMMAND only -- this leg is OPEN LOOP, unlike everything downstream.

Model:   tap(t_k) = sum_j h_j * cmd(t_k - tau_j) + c,  tau_j = j*DT, j = 0..NT-1
Fitted on FIRST DIFFERENCES of consecutive 50 Hz tap frames (kills c and any slow common mode).
Regularised by a second-difference (smoothness) penalty; lambda chosen by GCV over a grid.
Readouts: DC gain, DC group delay (first moment), and phase delay / |H| at 1.8-6 Hz from the DTFT.

usage: python a2_blink.py <route> [--synth LAW] [--amp lo|hi] [--lam L]
"""
import sys
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent / "out"
DT = 0.004          # FIR tap spacing, s
NT = 26             # 0 .. 100 ms
GRID = 0.001        # command ZOH grid


def load(route):
    D = np.load(OUT / f"raw_{route}.npz")
    cb, addr, src, bi = D["cb"], D["cf_addr"], D["cf_src"], D["cf_bi"]
    s = (addr == 0x1AB) & (src == 1)
    t1 = cb[bi[s]]
    raw = D["cf_b0"][s].astype(np.int64) & 0x3FF
    mag = (raw & 511) * 8.0
    sgn = np.where((raw >> 9) & 1, -1.0, 1.0)
    return D, t1, mag * sgn, mag


def cmd_grid(t_e4, e4, t0, t1):
    """on-bus command as a ZOH on a 1 ms grid (stamped at sendcan time; lambda' is NOT added,
    so every lag reported here is measured from the sendcan stamp)."""
    tg = np.arange(t0, t1, GRID)
    k = np.clip(np.searchsorted(t_e4, tg, side="right") - 1, 0, len(e4) - 1)
    u = e4[k].astype(np.float64)
    u[tg < t_e4[0]] = 0.0
    return tg, u


def build(tg, u, ttap, ytap, mask):
    """design matrix of the differenced fit"""
    n = len(ttap)
    idx = np.arange(1, n)
    ok = mask[idx] & mask[idx - 1] & (np.diff(ttap) > 0.016) & (np.diff(ttap) < 0.026)
    idx = idx[ok]
    X = np.empty((len(idx), NT))
    for j in range(NT):
        a = np.clip(np.round((ttap[idx] - j * DT - tg[0]) / GRID).astype(np.int64), 0, len(u) - 1)
        b = np.clip(np.round((ttap[idx - 1] - j * DT - tg[0]) / GRID).astype(np.int64), 0, len(u) - 1)
        X[:, j] = u[a] - u[b]
    y = ytap[idx] - ytap[idx - 1]
    return X, y


def fit(X, y, lam=None):
    P = np.zeros((NT + 2, NT))                     # second-difference smoothness penalty
    for j in range(NT):
        P[j, j] = 1.0
        if j + 1 < NT:
            P[j, j + 1] = -2.0
        if j + 2 < NT:
            P[j, j + 2] = 1.0
    XtX, Xty = X.T @ X, X.T @ y
    PtP = P.T @ P
    s = np.trace(XtX) / NT
    best = None
    lams = [lam * s] if lam is not None else list(10.0 ** np.arange(-4, 2.01, 0.5) * s)
    for L in lams:
        h = np.linalg.solve(XtX + L * PtP + 1e-9 * s * np.eye(NT), Xty)
        r = y - X @ h
        dof = np.trace(np.linalg.solve(XtX + L * PtP + 1e-9 * s * np.eye(NT), XtX))
        gcv = np.mean(r ** 2) / (1 - dof / len(y)) ** 2
        if best is None or gcv < best[0]:
            best = (gcv, L, h, r, dof)
    return best


def readout(h, tag, r2=None, n=None):
    tau = np.arange(NT) * DT
    G = h.sum()
    gd = float((tau * h).sum() / G)
    out = dict(tag=tag, G=float(G), gd_ms=gd * 1e3, n=n, r2=r2)
    lines = [f"  {tag:22s} DCgain {G:7.4f}  DC group delay {gd*1e3:6.2f} ms" + (f"  R2 {r2:.3f}" if r2 is not None else "")]
    pd = []
    for f in (1.0, 1.8, 2.5, 3.5, 5.0, 6.0):
        Hf = np.sum(h * np.exp(-2j * np.pi * f * tau))
        ph = np.angle(Hf)
        pdl = -ph / (2 * np.pi * f) * 1e3
        pd.append(pdl)
        out[f"pd_{f}"] = float(pdl); out[f"mag_{f}"] = float(abs(Hf) / abs(G))
    lines.append("      phase delay ms @1/1.8/2.5/3.5/5/6 Hz: " + " ".join(f"{x:6.2f}" for x in pd))
    lines.append("      |H|/DC       @1/1.8/2.5/3.5/5/6 Hz: " +
                 " ".join(f"{out[f'mag_{f}']:6.3f}" for f in (1.0, 1.8, 2.5, 3.5, 5.0, 6.0)))
    print("\n".join(lines))
    return out


def synth_tap(tg, u, ttap, law):
    """generate a synthetic tap from the real command with a KNOWN law, sampled at the real tap instants"""
    kind, *p = law.split(":")
    y = u.copy()
    if kind == "pd":                                    # pure delay, ms
        d = float(p[0])
        sh = int(round(d / 1e3 / GRID))
        y = np.concatenate([np.zeros(sh), u[:len(u) - sh]])
    elif kind == "pole":                                # first-order pole fc Hz + delay ms
        fc, d = float(p[0]), float(p[1])
        a = np.exp(-2 * np.pi * fc * GRID)
        sh = int(round(d / 1e3 / GRID))
        z = np.concatenate([np.zeros(sh), u[:len(u) - sh]])
        yy = np.empty_like(z); s = 0.0
        for i in range(len(z)):
            s = a * s + (1 - a) * z[i]; yy[i] = s
        y = yy
    elif kind == "slew":                                # rate limit counts per ms + delay ms
        rl, d = float(p[0]), float(p[1])
        sh = int(round(d / 1e3 / GRID))
        z = np.concatenate([np.zeros(sh), u[:len(u) - sh]])
        yy = np.empty_like(z); s = 0.0
        for i in range(len(z)):
            s += np.clip(z[i] - s, -rl, rl); yy[i] = s
        y = yy
    g = 0.63
    k = np.clip(np.round((ttap - tg[0]) / GRID).astype(np.int64), 0, len(y) - 1)
    v = g * y[k]
    v = np.clip(np.round(v / 8.0) * 8.0, -2461, 2461)   # the tap's own quantisation and rail
    return v


def run(route, synth=None, amp=None, lam=None):
    D, ttap, ytap, mag = load(route)
    t_e4, e4 = D["t_e4"], D["e4"]
    t_cst, v, sp = D["t_cst"], D["v"], D["spress"]
    tg, u = cmd_grid(t_e4, e4, ttap[0] - 0.2, ttap[-1] + 0.1)
    if synth:
        ytap = synth_tap(tg, u, ttap, synth)
    # engaged hands-off mask on the tap clock
    kk = np.clip(np.searchsorted(t_cst, ttap) - 1, 0, len(v) - 1)
    ie4 = np.clip(np.searchsorted(t_e4, ttap) - 1, 0, len(e4) - 1)
    mask = (sp[kk] < 0.5) & (np.abs(e4[ie4]) > 0.5) & (np.abs(ytap) < 2400)
    tag = f"{route[:8]} {synth or 'REAL'}"
    if amp:
        # command slew rate in counts/ms, from consecutive sends, smoothed over 40 ms, on the tap clock
        sl = np.abs(np.diff(e4, prepend=e4[0])) / np.maximum(np.diff(t_e4, prepend=t_e4[0] - 0.01) * 1e3, 1.0)
        sl = np.convolve(sl, np.ones(4) / 4, mode="same")
        du = np.interp(ttap, t_e4, sl)
        thr = np.median(du[mask])
        print(f"      amp split threshold |dcmd/dt| = {thr:.2f} counts/ms")
        mask = mask & ((du < thr) if amp == "lo" else (du >= thr))
        tag += f" amp:{amp}"
    X, y = build(tg, u, ttap, ytap, mask)
    gcv, L, h, r, dof = fit(X, y, lam)
    r2 = 1 - np.var(r) / np.var(y)
    o = readout(h, tag, r2, len(y))
    o["lam_over_s"] = float(L / (np.trace(X.T @ X) / NT)); o["dof"] = float(dof)
    print(f"      lam/scale {o['lam_over_s']:.2e} dof {dof:.1f} n {len(y)}  h = "
          + " ".join(f"{x:+.3f}" for x in h))
    return o


if __name__ == "__main__":
    a = sys.argv[1:]
    route = a[0]
    kw = {}
    for i, x in enumerate(a):
        if x == "--synth":
            kw["synth"] = a[i + 1]
        if x == "--amp":
            kw["amp"] = a[i + 1]
        if x == "--lam":
            kw["lam"] = float(a[i + 1])
    run(route, **kw)
