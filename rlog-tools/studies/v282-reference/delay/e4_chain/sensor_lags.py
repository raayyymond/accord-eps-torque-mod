"""Relative lags between the EPS's steering signals, all on the fitted EPS arrival clock:
   rate14 (0x14A, 1 deg/s LSB -- what carState.steeringRateDeg and the fork's rate loop use)
   rate18 (0x18F, fine LSB)
   gradient of angle14 (0x14A angle, 0.1 deg LSB)
Method: cross-spectral phase slope over bands, plus the gain; engaged hands-off runs.  Frame times differ by the
EPS's own transmit schedule (0x18F ~1 ms after 0x14A), which is included (both stamped by fitted arrival).
Usage: python sensor_lags.py <counter--hash>
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plant_delay as P


def xspec(runs, t, x, y_t, y, nper=256):
    Sxy = Sxx = Syy = None
    for a, b in runs:
        tt = t[a:b]
        if len(tt) < nper + 4:
            continue
        yi = np.interp(tt, y_t, y)   # y resampled to x's instants (linear; small, 1 ms offsets)
        xx = x[a:b]
        f, pxy = signal.csd(xx, yi, fs=100, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pxx = signal.welch(xx, fs=100, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pyy = signal.welch(yi, fs=100, nperseg=nper, noverlap=nper // 2, detrend="linear")
        Sxy = pxy if Sxy is None else Sxy + pxy
        Sxx = pxx if Sxx is None else Sxx + pxx
        Syy = pyy if Syy is None else Syy + pyy
    return f, Sxy, Sxx, Syy


def slope(f, Sxy, Sxx, Syy, f1, f2):
    s = (f >= f1) & (f <= f2)
    coh = np.abs(Sxy[s]) ** 2 / (Sxx[s] * Syy[s])
    ph = np.unwrap(np.angle(Sxy[s]))
    w = np.sqrt(coh / np.maximum(1 - coh, 1e-3))
    A = np.stack([2 * np.pi * f[s], np.ones(s.sum())], 1)
    beta, *_ = np.linalg.lstsq(A * w[:, None], ph * w, rcond=None)
    gain = float(np.average(np.abs(Sxy[s]) / Sxx[s], weights=coh))
    return dict(lag_ms=float(beta[0] * 1e3), icpt_deg=float(np.degrees(beta[1])), coh=float(coh.mean()), gain=gain)


def main(route):
    R = P.load_route(route, "14A")
    D = dict(np.load(HERE / "cache" / f"{route}.npz"))
    CL = dict(np.load(HERE / "cache" / f"{route}_clock.npz"))
    runs = P.runs_of(R["mask"], R["ty"])
    t14 = R["ty"]
    e18 = CL["e18"]; ok18 = np.isfinite(e18)
    out = {"route": route}
    grad_ang = np.full(len(t14), np.nan)
    for a, b in runs:
        grad_ang[a:b] = np.gradient(R["ang"][a:b], t14[a:b])
    ga = np.nan_to_num(grad_ang)
    # lag of y relative to x (positive = y later)
    for nm, (x, yt, y) in {"rate14 -> rate18": (R["rate"], e18[ok18], D["rate18"][ok18]),
                           "grad(angle14) -> rate14": (ga, t14[np.isfinite(t14)], R["rate"][np.isfinite(t14)]),
                           "grad(angle14) -> rate18": (ga, e18[ok18], D["rate18"][ok18])}.items():
        f, Sxy, Sxx, Syy = xspec(runs, t14, x, yt, y)
        out[nm] = {f"{f1}-{f2}Hz": slope(f, Sxy, Sxx, Syy, f1, f2) for f1, f2 in ((1, 4), (2, 8), (4, 15), (8, 25))}
    json.dump(out, open(HERE / "out" / f"sensor_lags_{route}.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
