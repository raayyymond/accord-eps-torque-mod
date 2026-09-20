"""STEP 3 -- characterise one episode: time traces, envelope, cycle-by-cycle frequency.

python s3_event.py <route_key> <t_centre_s> [half_width_s]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, FS


def zero_cross_freq(x, t):
    """Cycle-by-cycle frequency from upward zero crossings of the band-passed signal."""
    s = np.sign(x)
    idx = np.flatnonzero((s[:-1] <= 0) & (s[1:] > 0))
    if len(idx) < 3:
        return np.array([]), np.array([])
    # linear-interpolated crossing times
    tc = t[idx] + (t[idx + 1] - t[idx]) * (-x[idx]) / (x[idx + 1] - x[idx])
    per = np.diff(tc)
    return tc[:-1], 1.0 / per


def main(key, tc, hw):
    D = load(key)
    t = D["t"]
    m = (t >= tc - hw) & (t <= tc + hw)
    print(f"{key} {D['route']} window {tc-hw:.0f}-{tc+hw:.0f}s  n={m.sum()}")
    eng = engaged_mask(D)
    print(f"  engaged hands-off fraction in window: {eng[m].mean():.2f}"
          f"   lat_active {D['lat_active'][m].mean():.2f}  spress {D['spress'][m].mean():.2f}")
    print(f"  vego {D['vego'][m].min():.1f}-{D['vego'][m].max():.1f} m/s "
          f"(mean {D['vego'][m].mean():.1f})")
    print(f"  angle {D['angle'][m].min():.1f}..{D['angle'][m].max():.1f} deg   "
          f"rate |max| {np.abs(D['rate'][m]).max():.0f} deg/s   "
          f"cmd |max| {np.abs(D['cmd'][m]).max():.0f}   "
          f"out |max| {np.abs(D['out'][m]).max():.3f}   sat {D['sat'][m].mean():.2f}")
    print(f"  la_des {D['la_des'][m].min():.2f}..{D['la_des'][m].max():.2f}  "
          f"la_act {D['la_act'][m].min():.2f}..{D['la_act'][m].max():.2f}  "
          f"dtq {D['dtq'][m].min():.0f}..{D['dtq'][m].max():.0f}")
    # narrow PSD on the window
    x = sig.detrend(D["rate"][m], type="linear")
    f, P = sig.welch(x, fs=FS, nperseg=min(len(x), 1024), noverlap=min(len(x), 1024) // 2)
    j = np.argmax(P[(f > 1.0) & (f < 8)])
    ff = f[(f > 1.0) & (f < 8)]
    print(f"  window PSD rate peak {ff[j]:.2f} Hz")
    # cycle-by-cycle on band-passed rate
    f0 = ff[j]
    b, a = sig.butter(2, [max(0.5, f0 - 1.2) / (FS / 2), (f0 + 1.2) / (FS / 2)], btype="band")
    for ch in ("rate", "angle", "cmd", "err", "dtq", "out"):
        y = sig.filtfilt(b, a, sig.detrend(D[ch][m], type="linear"))
        tt, ff2 = zero_cross_freq(y, t[m])
        env = np.abs(sig.hilbert(y))
        if len(ff2):
            print(f"  {ch:6s} cyc-f n={len(ff2):3d} med={np.median(ff2):.3f} "
                  f"iqr=[{np.percentile(ff2,25):.3f},{np.percentile(ff2,75):.3f}] "
                  f"| env max {env.max():.3g} at t={t[m][np.argmax(env)]:.1f}")
    # print a coarse trace
    print("\n   t      v   angle    rate    cmd    err    out   la_des la_act   dtq  eng")
    ii = np.flatnonzero(m)[::10]
    for i in ii:
        print(f"  {t[i]:7.2f} {D['vego'][i]:5.1f} {D['angle'][i]:7.2f} {D['rate'][i]:7.1f} "
              f"{D['cmd'][i]:7.0f} {D['err'][i]:6.2f} {D['out'][i]:6.3f} {D['la_des'][i]:6.2f} "
              f"{D['la_act'][i]:6.2f} {D['dtq'][i]:6.0f} {int(eng[i])}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 6.0)
