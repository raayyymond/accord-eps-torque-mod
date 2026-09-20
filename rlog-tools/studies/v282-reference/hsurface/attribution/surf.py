"""BLOCK EXTRACTOR for the |H| surface: model-desired lateral accel -> ACHIEVED lateral accel,
resolved on speed x demand AMPLITUDE x frequency, one route at a time (RAM).

MEASUREMENT, not a model: x = cs_des_curv*v^2 (the MODEL's desired lateral accel, the goal's own
reference), y = livePose yaw * v (independent of the controller's own estimate; carState.yawRate is
identically 0 on every route -- REPORT.md instrument facts).

Per block we store the raw one-window spectra (Pxx, Pyy, Pxy complex) up to 5 Hz plus the covariates
each mechanism's signature needs:
  rail duty (|output| >= 0.995)  ->  mechanism (b) actuator saturation
  |i|/LAF, |f|/LAF, |p|/LAF      ->  mechanism (c) the standing hold-FF deficit carried by an integrator
  |angle| median/max             ->  the regime where (b) was measured (98-100% of episodes >30 deg)
  in-band demand RMS             ->  the AMPLITUDE axis

Two instruments, because one block length cannot resolve 0.1 Hz and hold an amplitude bin at 3 Hz:
  A  nperseg 2048 = 20.48 s, df 0.0488 Hz   bands 0.10-0.25, 0.25-0.50
  B  nperseg  512 =  5.12 s, df 0.1953 Hz   bands 0.50-1.0, 1.0-2.0, 2.0-4.0
One Hann window per block; coherence comes from the cross-BLOCK sum inside a cell (bias ~ 1/n_blocks,
reported), never from a single window (where it is identically 1).
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
FMAX = 5.0
INSTR = {"A": 2048, "B": 512}
BANDS = {"A": [(0.10, 0.25), (0.25, 0.50)],
         "B": [(0.50, 1.00), (1.00, 2.00), (1.50, 3.50), (2.00, 4.00)]}
SPD = [(0, 8), (8, 15), (15, 22), (22, 40)]


def _spec(x, y, n):
    """One Hann window, mean removed. scipy-consistent one-sided density scaling."""
    w = signal.get_window("hann", n)
    s = 1.0 / (V.FS * (w ** 2).sum())
    X = np.fft.rfft((x - x.mean()) * w)
    Y = np.fft.rfft((y - y.mean()) * w)
    f = np.fft.rfftfreq(n, 1.0 / V.FS)
    sc = np.full(len(f), 2.0 * s); sc[0] = s
    if n % 2 == 0:
        sc[-1] = s
    return f, (np.abs(X) ** 2) * sc, (np.abs(Y) ** 2) * sc, (np.conj(X) * Y) * sc


def route_blocks(rk, verbose=True):
    S = V.load(rk)
    g = S["meta"].get("group", "?")
    x = np.nan_to_num(S["model"])
    ya = np.nan_to_num(S["la_pose"])
    ok = np.isfinite(S["la_pose"]) & np.isfinite(S["la_act"])
    sgn = 1.0
    if ok.sum() > 1000:
        c = float(np.corrcoef(np.nan_to_num(S["la_pose"][ok]), np.nan_to_num(S["la_act"][ok]))[0, 1])
        sgn = 1.0 if c >= 0 else -1.0
    y = sgn * ya
    out = np.nan_to_num(S["out"])
    # LAF read FROM THE WIRE: out == -clip(p+i+f, +-LAF)/LAF, so LAF = -(p+i+f)/out on unrailed frames.
    pif = np.nan_to_num(S["p"]) + np.nan_to_num(S["i"]) + np.nan_to_num(S["f"])
    m0 = V.usable(S) & (np.abs(out) > 0.02) & (np.abs(out) < 0.95)
    LAF = float(np.median(-pif[m0] / out[m0])) if m0.sum() > 200 else np.nan
    res = float(np.max(np.abs(out[m0] + np.clip(pif[m0], -LAF, LAF) / LAF))) if np.isfinite(LAF) else np.nan
    u = V.usable(S)
    recs = []
    for key, n in INSTR.items():
        for a, b in V.runs(u, S["t"], min_s=n / V.FS):
            for k in range(a, b - n + 1, n):
                sl = slice(k, k + n)
                f, pxx, pyy, pxy = _spec(x[sl], y[sl], n)
                keep = f <= FMAX + 1e-9
                ang = np.abs(np.nan_to_num(S["sa"][sl]))
                recs.append(dict(
                    instr=key, f=f[keep], pxx=pxx[keep], pyy=pyy[keep], pxy=pxy[keep],
                    v=float(np.median(S["v"][sl])), vmin=float(np.min(S["v"][sl])), vmax=float(np.max(S["v"][sl])),
                    ang_med=float(np.median(ang)), ang_max=float(np.max(ang)),
                    rail=float(np.mean(np.abs(out[sl]) >= 0.995)),
                    out_p99=float(np.percentile(np.abs(out[sl]), 99)),
                    i_abs=float(np.median(np.abs(np.nan_to_num(S["i"][sl])))) / LAF if LAF else np.nan,
                    f_abs=float(np.median(np.abs(np.nan_to_num(S["f"][sl])))) / LAF if LAF else np.nan,
                    p_abs=float(np.median(np.abs(np.nan_to_num(S["p"][sl])))) / LAF if LAF else np.nan,
                    cmd_abs=float(np.median(np.abs(out[sl]))),
                    x_rms=float(np.sqrt(np.mean((x[sl] - x[sl].mean()) ** 2))),
                ))
    if verbose:
        na = sum(1 for r in recs if r["instr"] == "A"); nb = len(recs) - na
        print(f"  {rk} {g:8s} LAF {LAF:6.3f} (identity residual {res:.2e}, pose sign {sgn:+.0f})  "
              f"blocks A {na:4d} B {nb:5d}")
    del S
    return g, recs, LAF, sgn, res


def pack(rk):
    g, recs, LAF, sgn, res = route_blocks(rk)
    d = {}
    for key in INSTR:
        rs = [r for r in recs if r["instr"] == key]
        if not rs:
            continue
        d[f"{key}_f"] = rs[0]["f"]
        for fld in ("pxx", "pyy"):
            d[f"{key}_{fld}"] = np.array([r[fld] for r in rs])
        d[f"{key}_pxy"] = np.array([r["pxy"] for r in rs])
        for fld in ("v", "vmin", "vmax", "ang_med", "ang_max", "rail", "out_p99",
                    "i_abs", "f_abs", "p_abs", "cmd_abs", "x_rms"):
            d[f"{key}_{fld}"] = np.array([r[fld] for r in rs], float)
    d["meta"] = np.array([LAF, sgn, res])
    np.savez_compressed(OUT / f"blocks_{rk}.npz", group=np.array([g]), **d)


def _self_test():
    """Positive controls on synthetic data with KNOWN answers, through the same _spec/cell math."""
    rng = np.random.default_rng(3)
    n = 2048
    t = np.arange(4 * n) / V.FS
    x = V.lowpass(rng.standard_normal(len(t)), 1.5) * 2.0
    lagN, gain = 7, 0.72                       # 70 ms, gain 0.72
    y = gain * np.concatenate([np.zeros(lagN), x[:-lagN]])
    Pxx = Pyy = Pxy = None
    for k in range(0, len(t) - n + 1, n):
        f, pxx, pyy, pxy = _spec(x[k:k + n], y[k:k + n], n)
        Pxx = pxx if Pxx is None else Pxx + pxx
        Pyy = pyy if Pyy is None else Pyy + pyy
        Pxy = pxy if Pxy is None else Pxy + pxy
    s = (f >= 0.25) & (f < 0.50)
    H = np.average(np.abs(Pxy[s]) / Pxx[s], weights=Pxx[s])
    coh = np.average(np.abs(Pxy[s]) ** 2 / (Pxx[s] * Pyy[s]), weights=Pxx[s])
    ph = np.degrees(np.angle(Pxy[s]))
    lag_rec = float(np.average(-ph / (360.0 * f[s]), weights=Pxx[s]))
    assert abs(H - gain) < 0.02, H
    assert coh > 0.98, coh
    assert abs(lag_rec - lagN / V.FS) < 0.004, lag_rec
    # hard clip: describing-function gain of a symmetric clip must be < 1 and fall with amplitude
    Hs = []
    for amp in (0.5, 2.0, 6.0):
        xa = x * amp
        ya = np.clip(xa, -1.0, 1.0)
        Pxx = Pxy = None
        for k in range(0, len(t) - n + 1, n):
            f, pxx, _, pxy = _spec(xa[k:k + n], ya[k:k + n], n)
            Pxx = pxx if Pxx is None else Pxx + pxx
            Pxy = pxy if Pxy is None else Pxy + pxy
        s = (f >= 0.25) & (f < 0.50)
        Hs.append(float(np.average(np.abs(Pxy[s]) / Pxx[s], weights=Pxx[s])))
    assert Hs[0] > Hs[1] > Hs[2] and Hs[2] < 0.45, Hs
    return (f"self-test OK: |H| {H:.3f} (true {gain}), coh {coh:.3f}, lag {lag_rec*1000:.0f} ms "
            f"(true {lagN*10} ms); clip DF gain falls {Hs[0]:.2f}->{Hs[1]:.2f}->{Hs[2]:.2f} with amplitude")


if __name__ == "__main__":
    print(_self_test())
    print(V._self_test())
    print("\nblocks per route:")
    for rk in V.ROUTES:
        pack(rk)
