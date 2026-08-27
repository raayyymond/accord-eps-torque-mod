"""GATE-2 boost-direction library.  Episode-bootstrapped band transfers + biquad math.

Frozen method (matches docs/review/GATE2-2026-08-20-notch-sign.md sec 2):
  4 s Hann windows, 50 % overlap, linear detrend, Welch-summed INSIDE engaged
  episodes only (cc_lat); band estimate H = sum_band S_xy / sum_band S_xx;
  CI = bootstrap over EPISODES (never windows).
"""
import numpy as np, json, os

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FS = 101.14792783296437
DEG2RAD = np.pi / 180.0


def load(tag):
    return np.load(os.path.join(CACHE, f"_cache_{tag}", f"{tag}.npz"), allow_pickle=True)


def episodes(mask, fs=FS, min_s=2.5):
    m = np.asarray(mask).astype(bool)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    out = []
    for i in range(len(b) - 1):
        if m[b[i]] and (b[i + 1] - b[i]) / fs >= min_s:
            out.append((int(b[i]), int(b[i + 1])))
    return out


def _win_spec(x, y, nper, fs):
    """Return per-window (Sxx, Syy, Sxy) arrays over the rfft grid, Hann, detrended."""
    step = nper // 2
    w = np.hanning(nper + 1)[:nper]
    U = (w ** 2).sum()
    XS, YS, XY = [], [], []
    n = len(x)
    for s in range(0, n - nper + 1, step):
        xs = x[s:s + nper]; ys = y[s:s + nper]
        if not (np.all(np.isfinite(xs)) and np.all(np.isfinite(ys))):
            continue
        # linear detrend
        tt = np.arange(nper)
        A = np.vstack([tt, np.ones(nper)]).T
        xs = xs - A @ np.linalg.lstsq(A, xs, rcond=None)[0]
        ys = ys - A @ np.linalg.lstsq(A, ys, rcond=None)[0]
        X = np.fft.rfft(xs * w); Y = np.fft.rfft(ys * w)
        XS.append((X.conj() * X).real / (fs * U))
        YS.append((Y.conj() * Y).real / (fs * U))
        XY.append((X.conj() * Y) / (fs * U))
    if not XS:
        return None
    return np.array(XS), np.array(YS), np.array(XY)


def episode_specs(x, y, eps, nper, fs=FS):
    """Per-episode SUMMED spectra (list of (Sxx,Syy,Sxy,nwin))."""
    out = []
    for a, b in eps:
        r = _win_spec(x[a:b], y[a:b], nper, fs)
        if r is None:
            continue
        XS, YS, XY = r
        out.append((XS.sum(0), YS.sum(0), XY.sum(0), len(XS)))
    return out


def band_H(specs, f, lo, hi):
    """Pooled band transfer H = sum Sxy / sum Sxx, plus coh^2, over a list of episode specs."""
    sel = (f >= lo) & (f < hi)
    Sxx = sum(s[0] for s in specs)
    Syy = sum(s[1] for s in specs)
    Sxy = sum(s[2] for s in specs)
    H = Sxy[sel].sum() / Sxx[sel].sum()
    coh = np.abs(Sxy[sel].sum()) ** 2 / (Sxx[sel].sum() * Syy[sel].sum())
    return H, float(coh.real)


def boot_H(specs, f, lo, hi, nboot=4000, seed=0):
    """Episode bootstrap of band_H.  Returns (H_point, coh, arr_complex)."""
    rng = np.random.default_rng(seed)
    Hp, coh = band_H(specs, f, lo, hi)
    n = len(specs)
    arr = np.empty(nboot, complex)
    for i in range(nboot):
        pick = rng.integers(0, n, n)
        arr[i] = band_H([specs[j] for j in pick], f, lo, hi)[0]
    return Hp, coh, arr


def ci(arr, q=(2.5, 97.5)):
    return np.percentile(arr, q)


def phase_ci(arr, centre):
    """CI on the phase, unwrapped about the point estimate."""
    ph = np.angle(arr, deg=True)
    ph = centre + (ph - centre + 180) % 360 - 180
    return np.percentile(ph, [2.5, 97.5])


# ------------------------------------------------------------------ biquad
def H_biquad(c1, c2, c3, c4, f, fs=1000.0):
    z = np.exp(-2j * np.pi * np.asarray(f, float) / fs)
    return c4 * (1 + c3 * z + z * z) / (1 + c1 * z + c2 * z * z)


HONDA = (-1.5372, 0.63462, -1.8808, 0.81731)


def honda_exact():
    """Read the four stock float32 from the recorded LE bytes."""
    b = bytes.fromhex('f8c2c4bf' + '7576223f' + '0ebef0bf' + '3a3b513f')
    return tuple(float(v) for v in np.frombuffer(b, '<f4'))


def design_boost(f0, r, fzero, fs=1000.0, dc=1.0):
    """Poles at f0 with radius r; numerator (1, b1, 1) with unit-circle zeros at fzero.
    g solved so |H(0)| = dc."""
    w0 = 2 * np.pi * f0 / fs
    a1 = -2 * r * np.cos(w0)
    a2 = r * r
    wz = 2 * np.pi * fzero / fs
    b1 = -2 * np.cos(wz)
    g = dc * (1 + a1 + a2) / (1 + b1 + 1)
    return a1, a2, b1, g


def f32(x):
    return float(np.float32(x))


def le_bytes(x):
    return np.float32(x).tobytes().hex()
