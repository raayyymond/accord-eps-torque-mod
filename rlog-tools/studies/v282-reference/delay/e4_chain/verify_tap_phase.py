"""INDEPENDENT verification of the B link (0xE4 on-bus -> 427 tap) by CROSS-SPECTRAL PHASE.

Different estimator from chain_timing.tap_fit (which is a time-domain lstsq on a 1 kHz grid):
  resample both the ZOH on-bus command and the 427 tap onto the tap's own 50 Hz instants (uniform 20 ms grid
  per engaged hands-off run), Welch/CSD, then fit  phase(f) = -2*pi*f*dd - atan(f/fc)  over 0.5-20 Hz by
  2-parameter least squares weighted by coherence.  Positive control: synthesise the tap from the route's own
  command with KNOWN (fc, dd) and check both are recovered.
Usage: python verify_tap_phase.py <counter--hash>
"""
import sys, json, math
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.optimize import least_squares
from scipy.signal import lfilter
HERE = Path(__file__).resolve().parent
FS = 50.0


def lpf(u, fc, dt):
    if not np.isfinite(fc):
        return u.copy()
    a = math.exp(-2 * math.pi * fc * dt)
    return lfilter([1 - a], [1, -a], u)


def build(route):
    D = dict(np.load(HERE / "cache" / f"{route}.npz"))
    CH = dict(np.load(HERE / "cache" / f"{route}_chain.npz"))
    CL = dict(np.load(HERE / "cache" / f"{route}_clock.npz"))
    lam = float(CL["lam_mean"]) * 1e-3
    tx = D["sc_t"] + lam
    cmd = D["sc_cmd"].astype(float)
    m = CH["mask"].astype(bool)
    eab = CL["eab"]; tap = D["tap"].astype(float)
    ok = np.isfinite(eab) & (np.abs(tap) < 2100)
    # engaged hands-off stretches of sends, >= 10 s, no gap
    runs, i, n = [], 0, len(tx)
    while i < n:
        if not m[i]:
            i += 1; continue
        j = i
        while j + 1 < n and m[j + 1] and tx[j + 1] - tx[j] < 0.03:
            j += 1
        if tx[j] - tx[i] > 10.0:
            runs.append((tx[i], tx[j]))
        i = j + 1
    return tx, cmd, eab, tap, ok, runs, D["v"] if "v" in D else CH["v"], CH["v"]


def xspec(tx, cmd, tab, tapv, runs, vmask=None, nper=512):
    """Uniform 20 ms grid per run; command ZOH at grid times; tap linearly interpolated from its own instants."""
    Sxy = Sxx = Syy = None; sec = 0.0; nr = 0
    for (t0, t1) in runs:
        if vmask is not None and not vmask(t0, t1):
            continue
        g = np.arange(t0 + 0.5, t1 - 0.05, 1.0 / FS)
        if len(g) < nper + 8:
            continue
        iu = np.searchsorted(tx, g, side="right") - 1
        if iu[0] < 0:
            continue
        u = cmd[iu]
        sel = (tab > t0) & (tab < t1)
        if sel.sum() < 100:
            continue
        y = np.interp(g, tab[sel], tapv[sel])
        f, pxy = signal.csd(u, y, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pxx = signal.welch(u, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pyy = signal.welch(y, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        Sxy = pxy if Sxy is None else Sxy + pxy
        Sxx = pxx if Sxx is None else Sxx + pxx
        Syy = pyy if Syy is None else Syy + pyy
        sec += len(g) / FS; nr += 1
    return f, Sxy, Sxx, Syy, sec, nr


def fit_pole_delay(f, Sxy, Sxx, Syy, f1=0.5, f2=20.0):
    s = (f >= f1) & (f <= f2)
    ph = np.unwrap(np.angle(Sxy[s]))
    coh = np.abs(Sxy[s]) ** 2 / np.maximum(Sxx[s] * Syy[s], 1e-30)
    w = np.sqrt(np.clip(coh, 0, 0.999) / np.maximum(1 - np.clip(coh, 0, 0.999), 1e-3))
    ff = f[s]
    def res(p):
        dd, fc = p[0], abs(p[1])
        model = -2 * math.pi * ff * dd - np.arctan(ff / fc)
        return (ph - model) * w
    best = None
    for dd0 in (0.0, 0.005, 0.02, 0.05):
        for fc0 in (3.0, 5.0, 10.0, 50.0):
            r = least_squares(res, [dd0, fc0])
            if best is None or r.cost < best.cost:
                best = r
    dd, fc = best.x[0], abs(best.x[1])
    # pure-delay-only alternative
    def res2(p):
        return (ph - (-2 * math.pi * ff * p[0])) * w
    r2 = least_squares(res2, [0.02])
    sst = float(np.sum((w * (ph - np.average(ph, weights=w))) ** 2))
    gain = float(np.average(np.abs(Sxy[s]) / np.maximum(Sxx[s], 1e-30), weights=coh))
    return dict(dd_ms=round(dd * 1e3, 2), fc_hz=round(fc, 3),
                r2_phase=round(1 - 2 * best.cost / max(sst, 1e-30), 4),
                pure_delay_only_ms=round(r2.x[0] * 1e3, 2),
                r2_phase_pure=round(1 - 2 * r2.cost / max(sst, 1e-30), 4),
                coh_mean=round(float(coh.mean()), 3), gain=round(gain, 4),
                pole_phase_delay_ms={ff_: round(math.atan(ff_ / fc) / (2 * math.pi * ff_) * 1e3, 2) for ff_ in (1.0, 2.0, 2.5, 3.5)})


def main(route):
    tx, cmd, eab, tap, ok, runs, _, vch = build(route)
    tab = np.where(ok, eab, np.nan); tapv = np.where(ok, tap, np.nan)
    good = np.isfinite(tab)
    out = {"route": route, "n_runs": len(runs)}
    f, Sxy, Sxx, Syy, sec, nr = xspec(tx, cmd, tab[good], tapv[good], runs)
    out["real"] = fit_pole_delay(f, Sxy, Sxx, Syy); out["real"]["sec"] = round(sec, 1); out["real"]["n_runs_used"] = nr
    print("REAL", json.dumps(out["real"]), flush=True)
    # POSITIVE CONTROL: synthesise the tap from this route's own command with known (fc, dd)
    out["control"] = {}
    for fc_t, dd_t in ((5.0, 4.0), (np.inf, 30.0), (np.inf, 60.0), (3.0, 20.0), (5.0, 30.0)):
        T = np.full(len(eab), np.nan)
        for (t0, t1) in runs:
            grid = np.arange(t0, t1, 0.001)
            u = cmd[np.clip(np.searchsorted(tx, grid, side="right") - 1, 0, None)]
            y = lpf(u, fc_t, 0.001) * 0.63
            sel = good & (eab > t0 + 0.2) & (eab < t1)
            gi = np.clip(np.round((eab[sel] - dd_t * 1e-3 - t0) / 0.001).astype(int), 0, len(y) - 1)
            T[sel] = y[gi]
        Tq = np.clip(np.sign(T) * np.floor(np.abs(np.nan_to_num(T)) / 8.0) * 8.0, -2461, 2461)
        gg = np.isfinite(T)
        f, Sxy, Sxx, Syy, sec, nr = xspec(tx, cmd, eab[gg], Tq[gg], runs)
        r = fit_pole_delay(f, Sxy, Sxx, Syy)
        r["true_fc"] = fc_t if np.isfinite(fc_t) else "inf"; r["true_dd_ms"] = dd_t
        r["dd_err_ms"] = round(r["dd_ms"] - dd_t, 2)
        out["control"][f"fc={fc_t} dd={dd_t}"] = r
        print("CTRL", f"fc={fc_t} dd={dd_t}", json.dumps({k: r[k] for k in ("dd_ms", "fc_hz", "dd_err_ms", "r2_phase", "pure_delay_only_ms", "coh_mean")}), flush=True)
    json.dump(out, open(HERE / "out" / f"verify_tapphase_{route}.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1])
