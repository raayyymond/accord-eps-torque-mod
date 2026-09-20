"""STEP 4 -- pin one oscillation object: frequency + CI, envelope, growth, channel order.

Frequency is estimated three independent ways so the CI is not an artefact of one estimator:
  (1) cycle-by-cycle from interpolated upward zero crossings of the band-passed signal,
      CI = bootstrap over cycles (percentile, 2000 draws);
  (2) the FFT peak of the whole episode, parabolically refined, CI = spread over 4 s
      sub-windows stepped 1 s;
  (3) the instantaneous frequency d(phase)/dt from the analytic signal, weighted by envelope,
      CI = weighted percentile.

python s4_object.py <route> <t0> <t1> [f_lo f_hi]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, FS

RNG = np.random.default_rng(20260920)


def boot_ci(x, w=None, n=2000, lo=2.5, hi=97.5):
    x = np.asarray(x)
    if len(x) < 3:
        return np.nan, np.nan
    med = []
    for _ in range(n):
        idx = RNG.integers(0, len(x), len(x))
        med.append(np.median(x[idx]))
    return float(np.percentile(med, lo)), float(np.percentile(med, hi))


def est_cycles(y, t):
    s = np.sign(y)
    k = np.flatnonzero((s[:-1] <= 0) & (s[1:] > 0))
    if len(k) < 3:
        return np.array([]), np.array([])
    tc = t[k] + (t[k + 1] - t[k]) * (-y[k]) / (y[k + 1] - y[k])
    return tc[:-1], 1.0 / np.diff(tc)


def est_fft(x, t, flo, fhi, sub_s=4.0, step_s=1.0):
    def pk(seg):
        n = len(seg)
        w = np.hanning(n)
        P = np.abs(np.fft.rfft(sig.detrend(seg) * w)) ** 2
        f = np.fft.rfftfreq(n, 1 / FS)
        m = (f >= flo) & (f <= fhi)
        idx = np.flatnonzero(m)
        j = idx[np.argmax(P[idx])]
        y0, y1, y2 = np.log(P[j - 1]), np.log(P[j]), np.log(P[j + 1])
        den = y0 - 2 * y1 + y2
        d = float(np.clip(0.5 * (y0 - y2) / den, -1, 1)) if den < 0 else 0.0
        return f[j] + d * (f[1] - f[0])
    full = pk(x)
    n = int(sub_s * FS); st = int(step_s * FS)
    subs = [pk(x[i:i + n]) for i in range(0, len(x) - n + 1, st)]
    return full, np.array(subs)


def main(key, t0, t1, flo=None, fhi=None):
    D = load(key)
    t = D["t"]
    m = (t >= t0) & (t <= t1)
    eng = engaged_mask(D)
    x = sig.detrend(D["rate"][m], type="linear")
    # coarse peak to set the band if not given
    n = len(x); w = np.hanning(n)
    P = np.abs(np.fft.rfft(x * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / FS)
    sel = (f >= 1.0) & (f <= 9.0)
    f0 = f[np.flatnonzero(sel)[np.argmax(P[np.flatnonzero(sel)])]]
    if flo is None:
        flo, fhi = max(0.5, f0 * 0.6), f0 * 1.6
    print(f"== {key} {D['route']}  t {t0:.0f}-{t1:.0f}s  coarse peak {f0:.2f} Hz, band {flo:.2f}-{fhi:.2f}")
    print(f"   engaged hands-off {eng[m].mean()*100:.0f}%  v {D['vego'][m].mean():.1f} "
          f"({D['vego'][m].min():.1f}-{D['vego'][m].max():.1f}) m/s  "
          f"|angle| max {np.abs(D['angle'][m]).max():.1f} deg  "
          f"|la_act| max {np.abs(D['la_act'][m]).max():.2f} m/s2  sat {D['sat'][m].mean():.2f}")
    b, a = sig.butter(3, [flo / (FS / 2), fhi / (FS / 2)], btype="band")
    print(f"\n   {'ch':7s} {'cyc med':>8s} {'cyc CI':>16s} {'fft':>6s} {'fft CI':>14s} "
          f"{'inst':>6s} {'inst CI':>14s} {'amp':>9s} {'band/tot':>8s}")
    rows = {}
    for ch in ("rate", "angle", "cmd", "err", "out", "la_act", "dtq", "yaw"):
        if ch not in D:
            continue
        xx = sig.detrend(D[ch][m], type="linear")
        y = sig.filtfilt(b, a, xx)
        tc, fc = est_cycles(y, t[m])
        c_lo, c_hi = boot_ci(fc)
        ffull, fsub = est_fft(xx, t[m], flo, fhi)
        s_lo, s_hi = (np.percentile(fsub, 2.5), np.percentile(fsub, 97.5)) if len(fsub) > 3 else (np.nan, np.nan)
        z = sig.hilbert(y)
        env = np.abs(z)
        ph = np.unwrap(np.angle(z))
        inst = np.diff(ph) / (2 * np.pi) * FS
        ww = env[:-1]
        good = (inst > flo) & (inst < fhi)
        iw = inst[good]; wg = ww[good]
        order = np.argsort(iw)
        cw = np.cumsum(wg[order]) / wg.sum()
        i_med = float(np.interp(0.5, cw, iw[order]))
        i_lo = float(np.interp(0.16, cw, iw[order])); i_hi = float(np.interp(0.84, cw, iw[order]))
        amp = env.max()
        rows[ch] = dict(cyc=float(np.median(fc)) if len(fc) else np.nan, cyc_ci=(c_lo, c_hi),
                        fft=ffull, fft_ci=(s_lo, s_hi), inst=i_med, inst_ci=(i_lo, i_hi),
                        amp=float(amp), env=env, t=t[m])
        print(f"   {ch:7s} {rows[ch]['cyc']:8.3f} [{c_lo:6.3f},{c_hi:6.3f}] {ffull:6.3f} "
              f"[{s_lo:6.3f},{s_hi:6.3f}] {i_med:6.3f} [{i_lo:6.3f},{i_hi:6.3f}] "
              f"{amp:9.4g} {y.std()/max(xx.std(),1e-12):8.2f}")
    # envelope of rate: onset / duration / growth
    env = rows["rate"]["env"]; tt = rows["rate"]["t"]
    pk = env.max(); ipk = int(np.argmax(env))
    thr = 0.3 * pk
    above = env > thr
    k = np.flatnonzero(above)
    print(f"\n   rate envelope: peak {pk:.1f} deg/s at t={tt[ipk]:.2f}s; "
          f">30% of peak from {tt[k[0]]:.2f} to {tt[k[-1]]:.2f} s ({(tt[k[-1]]-tt[k[0]]):.2f} s, "
          f"{(tt[k[-1]]-tt[k[0]])*rows['rate']['cyc']:.1f} cycles)")
    # growth/decay: fit log-envelope slope over rise and fall
    for lbl, sl in (("rise", slice(k[0], ipk + 1)), ("fall", slice(ipk, k[-1] + 1))):
        if sl.stop - sl.start > 20:
            p = np.polyfit(tt[sl], np.log(env[sl]), 1)
            zeta = -p[0] / (2 * np.pi * rows["rate"]["cyc"])
            print(f"      {lbl}: d(ln env)/dt = {p[0]:+.3f} /s  -> equivalent zeta {zeta:+.4f}")
    # envelope trace
    print("\n   t        env_rate  env_angle  env_cmd   env_err  v")
    for i in range(0, len(tt), 25):
        print(f"   {tt[i]:8.2f} {rows['rate']['env'][i]:9.2f} {rows['angle']['env'][i]:9.3f} "
              f"{rows['cmd']['env'][i]:9.1f} {rows['err']['env'][i]:9.4f} {D['vego'][m][i]:5.1f}")


if __name__ == "__main__":
    a = sys.argv
    main(a[1], float(a[2]), float(a[3]),
         float(a[4]) if len(a) > 4 else None, float(a[5]) if len(a) > 5 else None)
