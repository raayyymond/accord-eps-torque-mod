"""STEP 10 -- BLIND EPISODE CENSUS. The decisive step: no band is assumed anywhere.

Detection: broadband 1.5-9 Hz analytic envelope of steeringRateDeg. An EPISODE is a maximal
run where that envelope exceeds ENV_ABS deg/s (an absolute physical threshold, identical for
every route, so no route's own statistics set its own bar) for at least MIN_S seconds, with
the engaged / hands-off mask holding over at least MASK_MIN of it.

Measurement: each episode is then measured on its own -- dominant frequency (whitened peak of
the rate spectrum over the episode +-1 s), in-band fraction, peak amplitude, speed, |angle|,
|lat accel|, growth rate of the envelope. The dominant frequency is read from the data, never
imposed.

python s10_episodes.py [env_abs] [vmin]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, runs, FS, HERE

ENV_ABS = 12.0       # deg/s -- roughly 20x the routine masked median (0.5-0.8 deg/s)
MIN_S = 0.6
MASK_MIN = 0.75
ORDER = ["r71", "r73", "r72", "r75", "v282a", "v282b", "v282c"]


def whitened_peak(x, lo=1.5, hi=9.0, logw=0.35):
    x = sig.detrend(np.asarray(x), type="linear")
    n = len(x); w = np.hanning(n)
    P = np.abs(np.fft.rfft(x * w)) ** 2 / (FS * (w ** 2).sum()); P[1:-1] *= 2
    f = np.fft.rfftfreq(n, 1 / FS)
    m = (f >= 0.6) & (f <= 20.0)
    lf, lg = np.log10(f[m]), np.log(P[m] + 1e-300)
    base = np.array([np.median(lg[np.abs(lf - x0) <= logw]) for x0 in lf])
    wh = lg - base
    fm, Pm = f[m], P[m]
    sel = (fm >= lo) & (fm <= hi)
    j = np.flatnonzero(sel)[np.argmax(wh[sel])]
    fpk = fm[j]
    bm = (fm > fpk * 0.85) & (fm < fpk * 1.15)
    amp = float(np.sqrt(2 * np.trapezoid(Pm[bm], fm[bm])))
    tot = float(np.trapezoid(Pm[(fm >= 0.6) & (fm <= 15)], fm[(fm >= 0.6) & (fm <= 15)]))
    return float(fpk), float(np.exp(wh[j])), amp, amp ** 2 / 2 / max(tot, 1e-30)


def episodes(key, env_abs=ENV_ABS, vmin=0.0, hands_off=True):
    D = load(key)
    t = D["t"]
    m = engaged_mask(D, vmin=vmin, hands_off=hands_off)
    b, a = sig.butter(3, [1.5 / (FS / 2), 9.0 / (FS / 2)], btype="band")
    e = np.abs(sig.hilbert(sig.filtfilt(b, a, sig.detrend(D["rate"], type="constant"))))
    hot = e > env_abs
    out = []
    for i0, i1 in runs(hot, min_s=MIN_S):
        if m[i0:i1].mean() < MASK_MIN:
            continue
        p0, p1 = max(0, i0 - 100), min(len(t), i1 + 100)
        fpk, prom, amp, frac = whitened_peak(D["rate"][p0:p1])
        sl = slice(i0, i1)
        ln = np.log(e[sl])
        g = np.polyfit(t[sl], ln, 1)[0] if (i1 - i0) > 30 else np.nan
        out.append(dict(t0=float(t[i0]), t1=float(t[i1 - 1]), dur=(i1 - i0) / FS,
                        pk=float(e[sl].max()), f=fpk, prom=prom, amp=amp, frac=frac,
                        v=float(D["vego"][sl].mean()), vmn=float(D["vego"][sl].min()),
                        ang=float(np.abs(D["angle"][sl]).max()),
                        la=float(np.abs(D["la_act"][sl]).max()),
                        cmd=float(np.abs(sig.detrend(D["cmd"][sl], type="constant")).max()),
                        dtq=float(np.abs(sig.detrend(D["dtq"][sl], type="constant")).max()),
                        sp=float(D["spress"][sl].mean()),
                        g=float(g), mk=float(m[i0:i1].mean())))
    secs = float(m.sum() / FS)
    del D
    return out, secs


if __name__ == "__main__":
    env_abs = float(sys.argv[1]) if len(sys.argv) > 1 else ENV_ABS
    vmin = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    hands_off = (len(sys.argv) < 4) or sys.argv[3] != "any"
    print(f"BLIND EPISODE CENSUS -- rate envelope 1.5-9 Hz > {env_abs} deg/s for >= {MIN_S}s, "
          f"engaged hands-off >= {MASK_MIN*100:.0f}% of episode, v>={vmin}\n")
    ALL = {}
    for k in ORDER:
        eps, secs = episodes(k, env_abs, vmin, hands_off)
        ALL[k] = eps
        eps.sort(key=lambda e: -e["pk"])
        print(f"== {k}  masked {secs:.0f}s  {len(eps)} episodes  "
              f"({len(eps)/max(secs/600,1e-9):.1f} per 10 min)")
        print(f"   {'t0':>8s} {'dur':>5s} {'f_Hz':>5s} {'prom':>6s} {'pk deg/s':>8s} "
              f"{'amp':>7s} {'inband':>6s} {'v':>5s} {'|ang|':>6s} {'|la|':>5s} {'dlnE/dt':>7s} {'|dtq|':>6s} {'sp':>4s}")
        for e in eps[:10]:
            print(f"   {e['t0']:8.1f} {e['dur']:5.1f} {e['f']:5.2f} {e['prom']:6.0f} "
                  f"{e['pk']:8.1f} {e['amp']:7.1f} {e['frac']:6.2f} {e['v']:5.1f} "
                  f"{e['ang']:6.1f} {e['la']:5.2f} {e['g']:+7.2f} {e['dtq']:6.0f} {e['sp']:4.2f}")
        if eps:
            fs = np.array([e["f"] for e in eps]); ws = np.array([e["pk"] for e in eps]) ** 2
            for lo, hi in ((1.5, 2.0), (2.0, 2.6), (2.6, 3.2), (3.2, 4.0), (4.0, 5.5), (5.5, 9.0)):
                s = ((fs >= lo) & (fs < hi))
                print(f"      {lo}-{hi} Hz: {s.sum():3d} episodes, {100*ws[s].sum()/ws.sum():5.1f}% "
                      f"of episode peak^2", end="\n")
        print()
