"""Why the >=8 m/s fits are not evidence: in-band signal size vs the rate LSB, and how much of the command is
feedback of past measurement.

Per route and speed bin (hands-off engaged only), over the fit band 2-8 Hz:
  rms_sr_bp   rms of band-passed steeringRateDeg   [deg/s]   -- compare with the 1.0 deg/s LSB
  rms_sa_bp   rms of band-passed steeringAngleDeg  [deg]     -- compare with the 0.1 deg LSB
  rms_u_bp    rms of band-passed command u                   [torque units]
  Hmag        |S_uy/S_uu| at 4 Hz, and 1/Hmag = implied torque per deg/s
  R2_fb       R^2 of band-passed u regressed on lags 1..40 of band-passed (angle, rate)   -- feedback share
  R2_fb_ar    same, adding lags of u itself (total predictability)

usage: python diag_band.py route [route ...]
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
import common as C, estimate as E

OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
SOS = signal.butter(4, [2.0, 8.0], btype="band", fs=C.FS, output="sos")


def bp(x):
    return signal.sosfiltfilt(SOS, x)


def r2(y, Xs):
    X = np.column_stack(Xs + [np.ones_like(y)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    return 1.0 - np.var(res) / max(np.var(y), 1e-30)


if __name__ == "__main__":
    res = {}
    for route in sys.argv[1:]:
        R = C.load_route(route); mask = C.handsoff_mask(R)
        ub = bp(R["u"]); ab = bp(R["sa"]); rb = bp(R["sr"])
        # H at ~4 Hz from the stored chunk spectra
        f, rows = E.chunk_stack(R, mask, zkey="sp")
        for lo, hi in C.SPEED_BINS:
            m = mask & (R["v"] >= lo) & (R["v"] < hi)
            if m.sum() < 500:
                continue
            rr = [q for q in rows if lo <= q["v"] < hi]
            Hm = None
            if rr:
                S = E.combine(rr); H, coh = E.H_of(S, "direct", "rate")
                i4 = int(np.argmin(np.abs(f - 4.0)))
                Hm = float(np.abs(H[i4])); ch4 = float(coh[i4])
            idx = np.where(m)[0]
            idx = idx[idx > 45]
            nl = 40
            lags_m = [ab[idx - L] for L in range(1, nl + 1)] + [rb[idx - L] for L in range(1, nl + 1)]
            k = f"v{lo:.0f}-{hi:.0f}"
            row = dict(n_s=float(m.sum() / C.FS),
                       rms_sr_bp=float(np.std(rb[m])), rms_sa_bp=float(np.std(ab[m])), rms_u_bp=float(np.std(ub[m])),
                       p95_absrate_raw=float(np.percentile(np.abs(R["sr"][m]), 95)),
                       frac_rate_within_1lsb=float(np.mean(np.abs(R["sr"][m]) <= 1.0)),
                       n_distinct_rate=int(len(np.unique(np.round(R["sr"][m])))),
                       H4=Hm, coh4=(ch4 if Hm else None), inv_H4=(1.0 / Hm if Hm else None),
                       R2_fb=float(r2(ub[idx], lags_m)),
                       R2_fb_u=float(r2(ub[idx], lags_m + [ub[idx - L] for L in range(1, nl + 1)])))
            res[f"{route}|{k}"] = row
            print(f"{route} {k:7s} {row['n_s']:6.0f}s  sr_bp {row['rms_sr_bp']:6.2f} deg/s  sa_bp {row['rms_sa_bp']:6.3f} deg  "
                  f"u_bp {row['rms_u_bp']:7.4f}  p95|rate| {row['p95_absrate_raw']:5.1f}  <=1LSB {row['frac_rate_within_1lsb']:.2f}  "
                  f"nlvl {row['n_distinct_rate']:3d}  |H|4Hz {row['H4'] if row['H4'] is None else round(row['H4'])}"
                  f"  1/|H| {row['inv_H4'] if row['inv_H4'] is None else round(row['inv_H4'],5)}  coh4 {row['coh4'] if row['coh4'] is None else round(row['coh4'],2)}"
                  f"  R2_fb {row['R2_fb']:.3f}  R2_fb+u {row['R2_fb_u']:.3f}", flush=True)
        del R, rows, ub, ab, rb
    (OUT / "diag_band.json").write_text(json.dumps(res, indent=1, default=float))
