"""STEP 11 -- pin an object's frequency with a defensible CI, from named episodes.

Two independent estimators, each with its own resampling CI:

  A. CYCLE estimator. Band-pass around the object (generous +-60 %), interpolate upward zero
     crossings, one frequency per cycle. Pooled over all episodes of the object; CI is a
     bootstrap over CYCLES (the natural unit -- 2000 draws, percentile).
  B. SPECTRAL estimator. 2 s sub-blocks, hop 0.5 s, FFT peak in 1.5-9 Hz refined
     parabolically in log power; each block weighted by its own in-band amplitude^2. Reported
     as the weighted mean; CI is a weighted bootstrap over BLOCKS.

Disagreement between A and B is reported, not hidden: for a clean sinusoid they agree to
better than 1 %; for a two-component object they do not, and that is the diagnosis.

python s11_pin.py <route> <label> t0:t1 [t0:t1 ...]
"""
import sys
import numpy as np
from scipy import signal as sig
from freq_lib import load, engaged_mask, FS

RNG = np.random.default_rng(73071)


def cycles(y, t):
    s = np.sign(y)
    k = np.flatnonzero((s[:-1] <= 0) & (s[1:] > 0))
    if len(k) < 3:
        return np.array([])
    tc = t[k] + (t[k + 1] - t[k]) * (-y[k]) / (y[k + 1] - y[k])
    return 1.0 / np.diff(tc)


def blocks(x, t, blk_s=2.0, hop_s=0.5):
    n, h = int(blk_s * FS), int(hop_s * FS)
    w = np.hanning(n)
    f = np.fft.rfftfreq(n, 1 / FS)
    sel = np.flatnonzero((f >= 1.5) & (f <= 9.0))
    out = []
    for i in range(0, len(x) - n + 1, h):
        P = np.abs(np.fft.rfft(sig.detrend(x[i:i + n]) * w)) ** 2
        j = sel[np.argmax(P[sel])]
        y0, y1, y2 = np.log(P[j - 1]), np.log(P[j]), np.log(P[j + 1])
        den = y0 - 2 * y1 + y2
        d = float(np.clip(0.5 * (y0 - y2) / den, -1, 1)) if den < 0 else 0.0
        fp = f[j] + d * (f[1] - f[0])
        bm = (f > fp * 0.85) & (f < fp * 1.15)
        a2 = float(np.trapezoid(P[bm], f[bm]))
        out.append((fp, a2))
    return np.array(out) if out else np.zeros((0, 2))


def wboot(v, w, n=4000):
    v, w = np.asarray(v), np.asarray(w)
    if len(v) < 3:
        return np.nan, np.nan
    r = np.empty(n)
    for k in range(n):
        i = RNG.integers(0, len(v), len(v))
        r[k] = np.average(v[i], weights=w[i]) if w[i].sum() > 0 else np.nan
    return float(np.nanpercentile(r, 2.5)), float(np.nanpercentile(r, 97.5))


def boot(v, n=4000):
    v = np.asarray(v)
    if len(v) < 3:
        return np.nan, np.nan
    r = np.array([np.median(v[RNG.integers(0, len(v), len(v))]) for _ in range(n)])
    return float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def main(key, label, wins, ch="rate"):
    D = load(key)
    t = D["t"]
    eng = engaged_mask(D)
    # coarse frequency from the pooled windows to set the band
    segs = [(t >= a) & (t <= b) for a, b in wins]
    fs_guess = []
    for m in segs:
        x = sig.detrend(D[ch][m])
        n = len(x); w = np.hanning(n)
        P = np.abs(np.fft.rfft(x * w)) ** 2
        f = np.fft.rfftfreq(n, 1 / FS)
        s = np.flatnonzero((f >= 1.5) & (f <= 9.0))
        fs_guess.append(f[s[np.argmax(P[s])]])
    f0 = float(np.median(fs_guess))
    flo, fhi = max(0.8, f0 * 0.40), f0 * 1.60
    b, a = sig.butter(3, [flo / (FS / 2), fhi / (FS / 2)], btype="band")
    yfull = sig.filtfilt(b, a, sig.detrend(D[ch], type="constant"))
    print(f"== {key} [{label}] {len(wins)} episode(s); coarse {f0:.2f} Hz, band {flo:.2f}-{fhi:.2f} Hz")
    allc, allb = [], []
    for (a0, b0), m in zip(wins, segs):
        c = cycles(yfull[m], t[m])
        bl = blocks(D[ch][m], t[m])
        allc.append(c); allb.append(bl)
        sp = D["spress"][m].mean(); en = eng[m].mean()
        print(f"   {a0:7.1f}-{b0:7.1f}s  n_cyc={len(c):3d} med {np.median(c) if len(c) else np.nan:5.2f}  "
              f"blocks={len(bl):3d}  v {D['vego'][m].mean():5.1f}  |ang| {np.abs(D['angle'][m]).max():5.1f}  "
              f"pressed {sp*100:3.0f}%  eng-handsoff {en*100:3.0f}%  "
              f"pkrate {np.abs(yfull[m]).max():6.1f} deg/s")
    C = np.concatenate([c for c in allc if len(c)])
    B = np.vstack([b_ for b_ in allb if len(b_)])
    c_lo, c_hi = boot(C)
    w_mean = float(np.average(B[:, 0], weights=B[:, 1]))
    b_lo, b_hi = wboot(B[:, 0], B[:, 1])
    # amplitude-weighted quartiles of the block peaks
    o = np.argsort(B[:, 0]); cw = np.cumsum(B[o, 1]) / B[:, 1].sum()
    q = [float(np.interp(p, cw, B[o, 0])) for p in (0.10, 0.25, 0.50, 0.75, 0.90)]
    print(f"   A CYCLE    median {np.median(C):.3f} Hz  95% CI [{c_lo:.3f}, {c_hi:.3f}]  "
          f"n={len(C)} cycles  IQR [{np.percentile(C,25):.2f},{np.percentile(C,75):.2f}]")
    print(f"   B SPECTRAL amp-weighted mean {w_mean:.3f} Hz  95% CI [{b_lo:.3f}, {b_hi:.3f}]  "
          f"n={len(B)} blocks")
    print(f"     amp-weighted deciles f10/f25/f50/f75/f90 = "
          f"{q[0]:.2f}/{q[1]:.2f}/{q[2]:.2f}/{q[3]:.2f}/{q[4]:.2f} Hz")
    return dict(cyc=float(np.median(C)), cyc_ci=(c_lo, c_hi), spec=w_mean, spec_ci=(b_lo, b_hi))


if __name__ == "__main__":
    key, label = sys.argv[1], sys.argv[2]
    wins = [tuple(float(v) for v in s.split(":")) for s in sys.argv[3:]]
    main(key, label, wins)
