"""
E4 (openpilot LKAS command) -> gp-0x6b98 (delivered EPS motor command) TRANSFER.

QUESTION: how much openpilot-commanded energy survives to the delivered motor
command in the 6-9 Hz band, and is openpilot-side excitation therefore viable?

427 (0x1AB) MOTOR_TORQUE carries |source| >> shift, 10-bit unsigned.  The SOURCE
changes by build; read from the plain images at 0x55DF2 / 0x55E10:

    V87,V88,V89 -> gp-0x6B98, sar 3   (8.0 counts / LSB)     routes 71,73,75,76
    V90,V91,V93 -> gp-0x6B26, sar 3
    V92         -> gp-0x6BBE, sar 4
    V94         -> gp-0x6B26, sar 1
    V96..V99    -> gp-0x6B70, sar 6
    V100,V101   -> gp-0x6B94, sar 6
    V102,V103   -> gp-0x6B4C, sar 6
    V104        -> gp-0x6B86, sar 4

Only routes 71/73/75/76 carry gp-0x6b98 and therefore answer the question directly.
Route 73 (V88) ALSO has the cave probe reading the SAME cell, so byte4 bit7 is the
SIGN of gp-0x6b98 at 100 Hz -> route 73 is the only SIGNED arm.  V89 repointed the
cave to gp-0x6ae2, so routes 75/76 have magnitude only.

TRAPS HONOURED
  * `t` pairs with `probe`; `raw14_t` pairs with `raw14_b4`.  Never crossed.
  * 427 is 49.8 Hz -> Nyquist 24.9 Hz.  Control band is 20-24 Hz, NOT 30-49.
  * Interpolating 427 to the 100 Hz grid is an LTI operation, so COHERENCE is
    unaffected; |H| is corrected by the linear-interpolation response sinc^2(f*T).
  * Windows are bootstrapped over EPISODES, never over windows.
"""
import json, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIT  = os.path.dirname(ROOT)

FS      = 100.0          # cache row grid
T427    = 1.0 / 49.82    # 427 frame period
NPERSEG = 512            # 5.12 s, df = 0.1953 Hz
BAND_LO = (0.5, 3.0)
BAND_HI = (6.0, 9.0)
BAND_CT = (20.0, 24.0)   # negative control, inside 427's Nyquist

ROUTES = {   # route -> (cache dir, build, 427 source, counts/LSB, signed?)
    "71": ("_scratch/cache/r71", "V87", "gp-0x6b98", 8.0, False),
    "73": ("_scratch/cache/r73", "V88", "gp-0x6b98", 8.0, True),
    "75": ("_scratch/cache/r75", "V89", "gp-0x6b98", 8.0, False),
    "76": ("_scratch/cache/r76", "V89", "gp-0x6b98", 8.0, False),
}


def load(route):
    cdir, build, src, lsb, signed = ROUTES[route]
    z = dict(np.load(os.path.join(KIT, cdir, "r%s.npz" % route), allow_pickle=True))
    t   = np.asarray(z["t"], float)
    e4  = np.asarray(z["e4tq"], float)
    req = np.asarray(z["e4req"], float)
    pr  = np.asarray(z["probe"], int) & 0xFF        # SAFE partner of t
    abt = np.asarray(z["ab_t1ab"], float)
    mt  = np.asarray(z["ab_mt"], float)
    o   = np.argsort(abt); abt, mt = abt[o], mt[o]

    # ---- 427 -> counts.  Sign (if available) applied AT THE 427 FRAME TIMES, then
    #      interpolated -- never magnitude-interp-then-sign, which fabricates edges.
    if signed:
        k = np.clip(np.searchsorted(t, abt), 0, len(t) - 1)
        sgn = np.where((pr[k] & 0x80) != 0, -1.0, 1.0)
    else:
        sgn = np.ones_like(mt)
    x427 = sgn * mt * lsb
    y = np.interp(t, abt, x427)
    sat = np.interp(t, abt, (mt >= 1023).astype(float)) > 0.0

    m = {
        "eng":   req > 0.5,
        "press": np.asarray(z["cs_press"], float) > 0.5,
        "v":     np.asarray(z["cs_v"], float),
        "sat":   sat,
    }
    if "cc_lat" in z:
        m["lat"] = np.asarray(z["cc_lat"], float) > 0.5
    return t, e4, y, m, (build, src, lsb, signed)


def episodes(mask, t, min_s=3.0):
    d = np.diff(np.concatenate(([0], mask.astype(int), [0])))
    lo, hi = np.where(d == 1)[0], np.where(d == -1)[0]
    return [(a, b) for a, b in zip(lo, hi) if (t[b - 1] - t[a]) >= min_s]


def windows(t, x, y, eps, nperseg=NPERSEG, hop=None):
    """Return per-window rFFTs of detrended, Hann-tapered segments, tagged by episode."""
    hop = hop or nperseg // 2
    w = np.hanning(nperseg)
    X, Y, ep = [], [], []
    for i, (a, b) in enumerate(eps):
        for s in range(a, b - nperseg + 1, hop):
            xs, ys = x[s:s + nperseg], y[s:s + nperseg]
            xs = xs - xs.mean(); ys = ys - ys.mean()
            X.append(np.fft.rfft(xs * w)); Y.append(np.fft.rfft(ys * w)); ep.append(i)
    if not X:
        return None
    f = np.fft.rfftfreq(nperseg, 1.0 / FS)
    return f, np.array(X), np.array(Y), np.array(ep)


def coh_and_H(X, Y, idx):
    """Pooled coherence and H1 = Sxy/Sxx over the window set `idx`."""
    Sxx = (np.abs(X[idx]) ** 2).mean(0)
    Syy = (np.abs(Y[idx]) ** 2).mean(0)
    Sxy = (np.conj(X[idx]) * Y[idx]).mean(0)
    g2  = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    H   = Sxy / np.maximum(Sxx, 1e-30)
    return Sxx, Syy, Sxy, g2, H


def band(f, lo, hi):
    return (f >= lo) & (f <= hi)


def interp_corr(f):
    """Linear-interpolation-to-100 Hz magnitude response, sinc^2(f*T427)."""
    return np.sinc(f * T427) ** 2


def band_stats(f, Sxx, Syy, Sxy, bnd):
    """Band-pooled coherence and |H|, with the interpolation correction on |H|."""
    sxx, syy = Sxx[bnd].sum(), Syy[bnd].sum()
    sxy = Sxy[bnd].sum()
    g2  = abs(sxy) ** 2 / max(sxx * syy, 1e-30)
    # |H| as an energy ratio corrected for the interpolation roll-off in-band
    c   = interp_corr(f[bnd]).mean()
    Hmag = np.sqrt(syy / max(sxx, 1e-30)) / np.sqrt(c)     # gain-like (includes noise)
    H1   = abs(sxy) / max(sxx, 1e-30) / np.sqrt(c)         # H1, noise-immune on Y
    return dict(g2=float(g2), H1=float(H1), Hgain=float(Hmag),
                Sxx=float(sxx), Syy=float(syy))
