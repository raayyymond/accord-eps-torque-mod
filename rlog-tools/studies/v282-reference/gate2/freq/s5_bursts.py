"""STEP 5 -- burst census. Bandpass -> analytic envelope -> list every episode, per route.

Reported per episode: peak envelope in physical units, duration, mean speed, |angle|,
whether engaged hands-off held, and the in-band fraction of broadband power. The last one is
the route-comparable number: absolute amplitudes differ because the driving differs.

python s5_bursts.py <band_lo> <band_hi> [route ...]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import ROUTES, load, engaged_mask, runs, FS, HERE

ORDER = ["r71", "r72", "r73", "r75", "v282a", "v282b", "v282c", "r74"]


def env_of(x, flo, fhi):
    b, a = sig.butter(3, [flo / (FS / 2), fhi / (FS / 2)], btype="band")
    y = sig.filtfilt(b, a, sig.detrend(x, type="constant"))
    return y, np.abs(sig.hilbert(y))


def census(key, flo, fhi, ch="rate", mult=6.0, min_s=0.8, vmin=0.0):
    D = load(key)
    m = engaged_mask(D, vmin=vmin)
    t = D["t"]
    y, env = env_of(D[ch], flo, fhi)
    _, envb = env_of(D[ch], 0.5, 15.0)
    med = np.median(env[m]) if m.any() else np.nan
    hot = m & (env > mult * med)
    eps = []
    for a, b in runs(hot, min_s=min_s):
        sl = slice(a, b)
        eps.append(dict(t0=t[a], t1=t[b - 1], dur=(b - a) / FS,
                        pk=float(env[sl].max()), pk_t=float(t[a + int(np.argmax(env[sl]))]),
                        v=float(D["vego"][sl].mean()),
                        ang=float(np.abs(D["angle"][sl]).max()),
                        la=float(np.abs(D["la_act"][sl]).max()),
                        frac=float((env[sl] ** 2).mean() / max((envb[sl] ** 2).mean(), 1e-12))))
    frac_all = float((env[m] ** 2).mean() / max((envb[m] ** 2).mean(), 1e-12)) if m.any() else np.nan
    rms_all = float(np.sqrt((env[m] ** 2).mean() / 2)) if m.any() else np.nan
    return D, m, eps, med, frac_all, rms_all


if __name__ == "__main__":
    flo, fhi = float(sys.argv[1]), float(sys.argv[2])
    vmin = float(sys.argv[3])
    keys = sys.argv[4:] or ORDER
    ch = "rate"
    print(f"BAND {flo}-{fhi} Hz on steeringRateDeg, engaged hands-off v>={vmin}, "
          f"burst = envelope > 6x route median for >= 0.8 s\n")
    print(f"{'route':7s} {'eng_s':>6s} {'med_env':>8s} {'rms_band':>8s} {'inband_frac':>11s} "
          f"{'nburst':>6s} {'burst_s':>8s}   top episodes")
    for k in keys:
        D, m, eps, med, frac, rms = census(k, flo, fhi, ch=ch, vmin=vmin)
        eps.sort(key=lambda e: -e["pk"])
        tot = sum(e["dur"] for e in eps)
        s = "  ".join(f"[t={e['t0']:.0f}-{e['t1']:.0f} pk={e['pk']:.0f} v={e['v']:.0f} "
                      f"ang={e['ang']:.0f} f={e['frac']:.2f}]" for e in eps[:3])
        print(f"{k:7s} {m.sum()/FS:6.0f} {med:8.3f} {rms:8.3f} {frac:11.4f} "
              f"{len(eps):6d} {tot:8.1f}   {s}")
        del D
