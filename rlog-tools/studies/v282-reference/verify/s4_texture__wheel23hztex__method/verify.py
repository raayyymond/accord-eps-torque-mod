"""Independent re-derivation of the s4_texture 'wheel 2-3 Hz texture' finding, from raw caches, WITHOUT
reusing s4_extract/s4_compare/s4_spectra. Purpose: does the magnitude survive a completely separate,
simpler pipeline? One route at a time; del the big dict before loading the next.

Method here (deliberately different from s4_texture's):
  - direct Welch PSD of the FULL usable, run-respecting signal (no 512-frame blocking), band-limited
    power ratio and bandpassed-rms ratio in 1.8-3.0 Hz, computed on RUNS (never across a gap).
  - crude matching: restrict to one speed x angle cell instead of the full cell-weighted scheme, so any
    agreement with the original numbers cannot be an artifact of the matching machinery.
  - cross-check the rate SENSOR (sr_deg) against the ANGLE-DERIVED rate (deriv(sa_deg)) independently.
  - check filter length: with order=4 butterworth bandpass at 1.8-3.0 Hz and FS=100, does sosfiltfilt on
    a short run introduce artifacts? Report min run length used.
"""
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

FS = V.FS


def bp(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos')
    return signal.sosfiltfilt(sos, x)


def band_power_welch(x, f1, f2, nperseg=1024):
    if len(x) < nperseg:
        nperseg = int(2 ** np.floor(np.log2(len(x))))
    if nperseg < 32:
        return np.nan, 0
    f, p = signal.welch(x - x.mean(), FS, nperseg=nperseg, noverlap=nperseg // 2)
    s = (f >= f1) & (f < f2)
    trapz = getattr(np, 'trapezoid', None) or np.trapz
    return float(trapz(p[s], f[s])), len(x)


def collect(rk, vmin, vmax, ang_max, min_run_s=5.0):
    """Return concatenated-by-run (never across gap) rate and angle-derived-rate samples in the speed/angle cell,
    plus per-run bandpassed rms lists for a route-level median (robust to one long run dominating)."""
    S = V.load(rk)
    u = V.usable(S, vmin, vmax)
    sa = np.nan_to_num(S['sa'])
    ang_ok = np.abs(sa) <= ang_max
    m = u & ang_ok
    t = S['t']
    sr = np.nan_to_num(S['sr'])
    sr_from_ang = V.deriv(np.nan_to_num(S['sa']))  # angle-derived rate, independent of the rate sensor
    runs = V.runs(m, t, min_s=min_run_s)
    rate_segs, ang_segs = [], []
    rms_hi_list, rms_hi_ang_list = [], []
    pow_hi_list, pow_lo_list = [], []
    min_len = None
    for a, b in runs:
        seg = sr[a:b]
        seg_a = sr_from_ang[a:b]
        if len(seg) < 64:
            continue
        min_len = len(seg) if min_len is None else min(min_len, len(seg))
        hi = bp(seg, 1.8, 3.0)
        hi_a = bp(seg_a, 1.8, 3.0)
        rms_hi_list.append(float(np.sqrt(np.mean(hi ** 2))))
        rms_hi_ang_list.append(float(np.sqrt(np.mean(hi_a ** 2))))
        ph, n = band_power_welch(seg, 1.8, 3.0)
        pl, _ = band_power_welch(seg, 0.3, 1.0)
        if np.isfinite(ph):
            pow_hi_list.append(ph)
        rate_segs.append(seg)
        ang_segs.append(seg_a)
    del S
    return dict(rk=rk, n_runs=len(runs), min_len=min_len,
                rms_hi=rms_hi_list, rms_hi_ang=rms_hi_ang_list, pow_hi=pow_hi_list,
                total_s=sum(len(x) for x in rate_segs) / FS)


def route_summary(rk, vmin, vmax, ang_max):
    d = collect(rk, vmin, vmax, ang_max)
    if d['total_s'] < 5 or len(d['rms_hi']) == 0:
        return None
    # route-level median-of-runs (robust point estimate), weight-independent of s4_texture's block scheme
    return dict(rk=d['rk'], sec=d['total_s'], n_runs=d['n_runs'], min_len=d['min_len'],
                med_rms_hi=float(np.median(d['rms_hi'])),
                med_rms_hi_ang=float(np.median(d['rms_hi_ang'])),
                med_pow_hi=float(np.median(d['pow_hi'])) if d['pow_hi'] else np.nan)


def main():
    print("=== INDEPENDENT re-derivation (own pipeline, not s4_texture's) ===")
    print("Cell: v in [15,25) m/s, |angle| <= 5 deg  (a 'ge15 straight'-like cell, chosen a priori, not tuned)")
    print()
    groups = {}
    for rk, meta in V.ROUTES.items():
        r = route_summary(rk, 15, 25, 5.0)
        if r is None:
            print(f"  {rk:24s} {meta['group']:8s}  -- insufficient data in this cell")
            continue
        groups.setdefault(meta['group'], []).append(r)
        print(f"  {rk:24s} {meta['group']:8s} sec={r['sec']:6.0f} n_runs={r['n_runs']:3d} min_len={r['min_len']:4d} "
              f"rms_hi(sr)={r['med_rms_hi']:.3f} rms_hi(ang-deriv)={r['med_rms_hi_ang']:.3f} "
              f"welch_pow_hi={r['med_pow_hi']:.4f}")
    print()
    if 'V282' not in groups:
        print("No V282 data in this cell -- cannot compute ratio.")
        return
    ref_rms = np.median([r['med_rms_hi'] for r in groups['V282']])
    ref_rms_ang = np.median([r['med_rms_hi_ang'] for r in groups['V282']])
    ref_pow = np.median([r['med_pow_hi'] for r in groups['V282']])
    print(f"V282 reference (median of route medians): rms_hi(sr)={ref_rms:.3f} rms_hi(ang)={ref_rms_ang:.3f} pow_hi={ref_pow:.4f}")
    print()
    for g, rs in groups.items():
        if g == 'V282':
            continue
        rms = np.median([r['med_rms_hi'] for r in rs])
        rms_ang = np.median([r['med_rms_hi_ang'] for r in rs])
        pw = np.median([r['med_pow_hi'] for r in rs])
        print(f"{g:8s} n_routes={len(rs)}  rms ratio(sr)={rms/ref_rms:.2f}  rms ratio(ang)={rms_ang/ref_rms_ang:.2f}  "
              f"welch power ratio={pw/ref_pow:.2f}")


if __name__ == '__main__':
    main()
