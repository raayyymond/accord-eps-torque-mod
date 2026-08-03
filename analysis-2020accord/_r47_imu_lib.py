#!/usr/bin/env python3
"""Shared instruments for the route-47 (V67) IMU analysis.

The comma's LSM6DS3TR-C shares no signal path with the EPS, so it is the kit's only independent
witness. Everything here keeps the IMU on its OWN hardware-timestamp lattice; the CAN channels are
mapped ONTO the IMU by zero-order hold of the categorical masks, never the other way round.

🛑 THE ROUTE-47 CONFOUND, STATED ONCE SO EVERY TABLE INHERITS IT.
   `g6806` == `cc_lat` in 150,302 / 150,327 frames (99.983%). V67 gates Kd on the firmware's own
   LKAS gate, and that gate is LKAS engagement. So a within-route `g6806` split is EXACTLY an
   engagement split, and a raw r47 arm ratio measures (Kd effect x engagement effect), not Kd.
   The Kd term is recoverable only by DIFFERENCE-IN-DIFFERENCES against a build where the same
   engagement split exists at CONSTANT Kd -- V65 (r3a/r3b), Kd=2 in both arms.

🛑 THE ALIAS. The accelerometer's dt MEDIAN is 9.897-9.901 ms (=> a ~101.03 Hz hardware lattice),
   while its dt MEAN is ~10.000 ms because ~1% of samples are DROPPED, not jittered. Nyquist on the
   lattice is ~50.5 Hz, so a "45 Hz" line is indistinguishable from ~56 Hz, ~146 Hz, ... The IMU
   lattice differs from the CAN grid by only ~1.03 Hz per alias order, which is the quantity
   `alias_power()` measures rather than assumes.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

AXES = ["ax", "ay", "az", "gx", "gy", "gz"]
ACC = ["ax", "ay", "az"]
GYR = ["gx", "gy", "gz"]

# Bands. 30-40 / 40-49 are grind #2; 18-22 is grind #1; 24-28 is the pre-declared NEGATIVE control;
# 1-4 Hz is the exposure-matching validity check (driver/road input -- must NOT differ once matched).
BANDS = {"1-4": (1.0, 4.0), "6-9": (6.0, 9.0), "10-16": (10.0, 16.0), "18-22": (18.0, 22.0),
         "24-28": (24.0, 28.0), "30-40": (30.0, 40.0), "40-49": (40.0, 49.0), "30-49": (30.0, 49.0)}
BORDER = ["1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49", "30-49"]

SEGS = {"r3a": list(range(7)), "r3b": list(range(14)), "r47": list(range(26)),
        "r2c": [0, 1, 3, 4, 8, 9, 10, 11, 12], "r2b": list(range(14)),
        "r37": list(range(15))}
PFX = {"r3a": "r3as", "r3b": "r3bs", "r47": "r47s", "r2c": "r2cs", "r2b": "r2bs", "r37": "r37s"}

# Kd DOSE at HIGHWAY speed. 🛑 These are NOT the creep doses. V62/V65 apply a flat x2 via `sar 0x9`,
# but V67 replaces a speed-RISING LERP with the SCALAR cal 0xC6446 = 5244, so its multiplier climbs
# with speed: 1.94x at 7.2 km/h, 2.28x at 50, 2.44x at 100-110. Recomputed from
# v66_v67_explained.r24_gain_q10, not quoted. V58/V59 are stock (1.00x).
DOSE_HW = {"r2b": 1.00, "r2c": 1.00, "r37": 2.00, "r3a": 2.00, "r3b": 2.00, "r47": 2.44}
BUILD = {"r2b": "V58", "r2c": "V59", "r37": "V62", "r3a": "V65", "r3b": "V65", "r47": "V67"}

WHEEL_CIRC = 2.08          # m; the kit's established 2.073-2.088 m band. order 1 = v / 2.08 Hz


# ------------------------------------------------------------------ loading ----------------------
def load_imu(tag, s):
    p = ROOT / f"_cache_{tag}" / f"{PFX[tag]}{s}_imu.npz"
    return dict(np.load(p)) if p.exists() else None


def load_can(tag, s):
    p = ROOT / f"_cache_{tag}" / f"{PFX[tag]}{s}.npz"
    return dict(np.load(p)) if p.exists() else None


def have(tag, s):
    return (ROOT / f"_cache_{tag}" / f"{PFX[tag]}{s}_imu.npz").exists()


def load_snd(tag, s):
    """The microphone level cache -- the ONLY channel here without a ~50 Hz Nyquist ceiling."""
    p = ROOT / f"_cache_{tag}" / f"{PFX[tag]}{s}_snd.npz"
    return dict(np.load(p)) if p.exists() else None


# ------------------------------------------------------------------ the lattice ------------------
def lattice(t, odr0=None):
    """Snap irregular hardware timestamps to the sensor's OWN ODR lattice.

    Returns (index, refined_odr, resid_rms_s, resid_max_s).

    🛑 SEED FROM THIS SEGMENT'S OWN MEDIAN dt, never from a route-wide constant. A 0.015 Hz seed
    error accumulates to a full sample over a 60 s segment, the initial round() CYCLE-SLIPS near the
    end, and the least-squares refit is then dragged onto a wrong slope -- which showed up as a
    2.5 ms residual rms (25% of a period) on segments 12-24 and a fabricated ODR "drift" along the
    route. The median dt is drop-immune because drops are ~1% and land in the tail.

    Robustness: the fit is CUMULATIVE-MEDIAN based, not least-squares, so the ~1% of intervals that
    are 2x or 4x the period cannot lever the slope.
    """
    t = np.asarray(t, float)
    if odr0 is None:
        odr0 = 1.0 / float(np.median(np.diff(t)))
    slope, icpt = 1.0 / odr0, t[0]
    n = np.round((t - icpt) * odr0).astype(np.int64)
    for _ in range(6):
        A = np.vstack([n.astype(float), np.ones(len(n))]).T
        slope, icpt = np.linalg.lstsq(A, t, rcond=None)[0]
        n2 = np.round((t - icpt) / slope).astype(np.int64)
        if np.array_equal(n2, n):
            n = n2
            break
        n = n2
    resid = t - (icpt + n * slope)
    return n, 1.0 / slope, float(np.sqrt(np.mean(resid ** 2))), float(np.abs(resid).max())


def uniform(t, v, odr0=None):
    """Lattice-snapped uniform series, gaps interpolated. Returns (series, odr, fill_frac, t_uni).

    `t_uni` is the lattice's own time axis on the CAN time base, so an episode expressed in CAN
    seconds can be sliced out of the uniform series without re-deriving the mapping.
    """
    n, odr, _, _ = lattice(t, odr0)
    n = n - n[0]
    out = np.full(int(n[-1]) + 1, np.nan)
    out[n] = np.asarray(v, float)
    bad = ~np.isfinite(out)
    if bad.any():
        out[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), out[~bad])
    t_uni = t[0] + np.arange(len(out)) / odr
    return out, odr, float(1.0 - bad.mean()), t_uni


# ------------------------------------------------------------------ envelopes --------------------
def band_env(x, fs, lo, hi, taper=None):
    """|analytic signal| restricted to [lo,hi]. Linear-detrended and Hann-tapered, taper divided
    back out -- an undetrended rectangular window leaks the driver's own 1/f ramp into 30-49 Hz in
    proportion to effort, which is the covariate that separates the arms."""
    x = np.asarray(x, float)
    n = len(x)
    r = np.arange(n, dtype=float)
    c = np.polyfit(r, x, 1)
    w = np.hanning(n) + 1e-3 if taper is None else taper
    y = (x - (c[0] * r + c[1])) * w
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(n, 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=n)) / w


def env_full(x, fs, lo, hi):
    """Whole-series band envelope (no taper) -- for long records where edge leakage is negligible
    relative to the record length. Used only when the window is >= 20 s."""
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(x)))


# ------------------------------------------------------------------ spectra ----------------------
def periodogram(x, fs, nfft, detrend=True):
    x = np.asarray(x, float)
    if len(x) != nfft or not np.all(np.isfinite(x)):
        return None
    if detrend:
        r = np.arange(nfft, dtype=float)
        c = np.polyfit(r, x, 1)
        x = x - (c[0] * r + c[1])
    else:
        x = x - x.mean()
    return np.abs(np.fft.rfft(x * np.hanning(nfft))) ** 2


_MASK = {}


def prom_spectrum(f, P, halfwin=6.0, exclude=1.5):
    """P / its own local median floor, per bin -- so broadband driver input cannot pass as a mode."""
    key = (len(f), float(f[1]), halfwin, exclude)
    M = _MASK.get(key)
    if M is None:
        D = np.abs(f[:, None] - f[None, :])
        M = (D <= halfwin) & (D > exclude) & (f[None, :] > 0.3)
        M[M.sum(1) < 5] = False
        _MASK[key] = M
    A = np.where(M, P[None, :], np.nan)
    with np.errstate(all="ignore"):
        fl = np.nanmedian(A, axis=1)
    R = np.where(fl > 0, P / np.where(fl > 0, fl, 1.0), np.nan)
    R[~np.isfinite(fl)] = np.nan
    R[0] = R[-1] = np.nan
    return R


def locate(f, P, lo, hi, R=None):
    """(f0, prominence) of the most PROMINENT line in [lo,hi], sub-bin refined in log power."""
    if R is None:
        R = prom_spectrum(f, P)
    m = (f >= lo) & (f <= hi) & np.isfinite(R)
    if not m.any():
        return np.nan, np.nan
    j = int(np.argmax(np.where(m, R, -np.inf)))
    if j <= 0 or j >= len(P) - 1:
        return float(f[j]), float(R[j])
    y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
    den = y0 - 2 * y1 + y2
    dl = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return float(f[j] + np.clip(dl, -0.5, 0.5) * (f[1] - f[0])), float(R[j])


def q_of(f, P, f0):
    """-3 dB Q of the peak nearest f0. The Hann main lobe caps measurable Q at f0/(1.44*fs/nfft)."""
    if not np.isfinite(f0):
        return np.nan
    j = int(np.argmin(np.abs(f - f0)))
    half = P[j] / 2.0
    a = j
    while a > 1 and P[a] > half and P[a - 1] < P[a]:
        a -= 1
    b = j
    while b < len(P) - 2 and P[b] > half and P[b + 1] < P[b]:
        b += 1
    bw = max(f[b] - f[a], f[1] - f[0])
    return float(f[j] / bw)


# ------------------------------------------------------------------ CAN -> IMU grid --------------
def hold(t_out, t_in, v_in, fill=0.0):
    """Zero-order hold of a CATEGORICAL CAN channel onto the IMU's native times.

    🛑 The masks (g6806, cc_lat, gear) are categorical: np.interp would fabricate 0.5 codes at every
    transition. Continuous covariates (vEgo, effort) DO use np.interp -- see `lerp`.
    """
    t_in = np.asarray(t_in, float)
    if not len(t_in):
        return np.full(len(t_out), fill, float)
    i = np.searchsorted(t_in, t_out, side="right") - 1
    return np.where(i < 0, fill, np.asarray(v_in, float)[np.clip(i, 0, None)]).astype(float)


def lerp(t_out, t_in, v_in):
    return np.interp(t_out, np.asarray(t_in, float), np.asarray(v_in, float))


def sustained(x, fs, fc=3.0):
    """Driver's actual push with the oscillation removed -- |lowpass(tq, 3 Hz)|, never raw |tq|."""
    x = np.asarray(x, float)
    bad = ~np.isfinite(x)
    if bad.all():
        return np.full_like(x, np.inf)
    if bad.any():
        x = x.copy()
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), x[~bad])
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    return np.abs(np.fft.irfft(X, n=len(x)) + x.mean())


def runs_of(mask, t, min_n, max_gap=0.05):
    """Contiguous runs of `mask` with no sample gap > max_gap, at least min_n long."""
    idx = np.flatnonzero(np.asarray(mask, bool))
    if not len(idx):
        return
    s = prev = idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > max_gap:
            if prev - s + 1 >= min_n:
                yield s, prev + 1
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        yield s, prev + 1


# ------------------------------------------------------------------ episode statistics -----------
def episodes(rs, key="blk"):
    ep = {}
    for r in rs:
        ep.setdefault(r[key], []).append(r)
    return list(ep.values())


def boot_stat(rs, field, rng, agg=np.median, nboot=2000, epkey="blk"):
    """(point, lo, hi, n, nep) resampling EPISODES with replacement, never windows.

    A window bootstrap shrinks the CI by ~sqrt(windows/episode) and manufactures significance --
    this kit has retracted three claims to that error.
    """
    eps = episodes([r for r in rs if np.isfinite(r.get(field, np.nan))], epkey)
    if not eps:
        return np.nan, np.nan, np.nan, 0, 0
    per = [np.array([r[field] for r in e], float) for e in eps]
    allv = np.concatenate(per)
    dr = np.full(nboot, np.nan)
    for b in range(nboot):
        i = rng.integers(0, len(per), len(per))
        dr[b] = agg(np.concatenate([per[j] for j in i]))
    return (float(agg(allv)), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)),
            len(allv), len(eps))


def cellwise(rsA, rsB, field, rng, nboot=2000, agg=np.median, min_ep=2, min_win=5, epkey="blk"):
    """STRATIFIED log-ratio A/B over covariate cells occupied by BOTH sides, episode-resampled.

    Weight w_c = 1/(1/nepA_c + 1/nepB_c) -- a cell contributes in proportion to the SMALLER episode
    count, so a cell one arm barely visited cannot dominate the ratio.
    Returns (ratio, lo, hi, ncells, nepA, nepB, table).
    """
    epA, epB = episodes(rsA, epkey), episodes(rsB, epkey)

    def strat(eA, eB, want=False):
        A, B = {}, {}
        for e in eA:
            for r in e:
                if np.isfinite(r.get(field, np.nan)):
                    A.setdefault(r["cell"], []).append(r)
        for e in eB:
            for r in e:
                if np.isfinite(r.get(field, np.nan)):
                    B.setdefault(r["cell"], []).append(r)
        num = den = 0.0
        tab = []
        for c in sorted(set(A) & set(B)):
            ra, rb = A[c], B[c]
            nea, neb = len({r[epkey] for r in ra}), len({r[epkey] for r in rb})
            if nea < min_ep or neb < min_ep or len(ra) < min_win or len(rb) < min_win:
                continue
            sa = float(agg([r[field] for r in ra]))
            sb = float(agg([r[field] for r in rb]))
            if not (np.isfinite(sa) and np.isfinite(sb)) or sa <= 0 or sb <= 0:
                continue
            w = 1.0 / (1.0 / nea + 1.0 / neb)
            num += w * np.log(sa / sb)
            den += w
            if want:
                tab.append((c, len(ra), len(rb), nea, neb, sa, sb, sa / sb, w))
        return (num / den if den else np.nan), tab

    point, tab = strat(epA, epB, True)
    if nboot <= 0 or not np.isfinite(point):
        return (float(np.exp(point)) if np.isfinite(point) else np.nan,
                np.nan, np.nan, len(tab), len(epA), len(epB), tab)
    dr = np.full(nboot, np.nan)
    for k in range(nboot):
        ia = rng.integers(0, len(epA), len(epA))
        ib = rng.integers(0, len(epB), len(epB))
        dr[k] = strat([epA[i] for i in ia], [epB[i] for i in ib])[0]
    if not np.isfinite(dr).any():
        return float(np.exp(point)), np.nan, np.nan, len(tab), len(epA), len(epB), tab
    return (float(np.exp(point)), float(np.exp(np.nanpercentile(dr, 2.5))),
            float(np.exp(np.nanpercentile(dr, 97.5))), len(tab), len(epA), len(epB), tab)


def split_half_null(rs, field, rng, nrep=300, epkey="blk", **kw):
    """The pool's OWN noise floor: randomly halve ITS OWN episodes, run the identical estimator.

    Any ratio inside this interval is not distinguishable from route/exposure noise. On this data
    the floor has been ~2.2x -- large enough to have retracted real-looking claims.
    """
    eps = episodes(rs, epkey)
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(eps))
        h = len(eps) // 2
        ra = [r for i in idx[:h] for r in eps[i]]
        rb = [r for i in idx[h:] for r in eps[i]]
        v = cellwise(ra, rb, field, rng, nboot=0, epkey=epkey, **kw)[0]
        if np.isfinite(v) and v > 0:
            out.append(v)
    if not out:
        return np.nan, np.nan, np.nan, 0
    o = np.array(out, float)
    return (float(np.exp(np.median(np.log(o)))), float(np.percentile(o, 2.5)),
            float(np.percentile(o, 97.5)), len(o))


def perm_p(rsA, rsB, field, rng, nperm=1000, epkey="blk", **kw):
    """Two-sided permutation p: shuffle EPISODE labels between arms and re-estimate."""
    epA, epB = episodes(rsA, epkey), episodes(rsB, epkey)
    obs = cellwise(rsA, rsB, field, rng, nboot=0, epkey=epkey, **kw)[0]
    if not np.isfinite(obs) or obs <= 0:
        return np.nan, np.nan
    pool, nA = epA + epB, len(epA)
    hits = tot = 0
    for _ in range(nperm):
        idx = rng.permutation(len(pool))
        ra = [r for i in idx[:nA] for r in pool[i]]
        rb = [r for i in idx[nA:] for r in pool[i]]
        v = cellwise(ra, rb, field, rng, nboot=0, epkey=epkey, **kw)[0]
        if np.isfinite(v) and v > 0:
            tot += 1
            hits += abs(np.log(v)) >= abs(np.log(obs))
    return float(obs), (float((hits + 1) / (tot + 1)) if tot else np.nan)


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")


# ------------------------------------------------------------------ episode records --------------
def lowpass(x, fs, fc):
    X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    return np.fft.irfft(X, n=len(x)) + np.mean(x)


def dilate(m, fs, sec):
    k = max(1, int(sec * fs))
    return np.convolve(np.asarray(m, float), np.ones(2 * k + 1), "same") > 0


def imu_envelopes(tag, s, bands=None, axes=None):
    """Per-(axis, band) analytic envelope over the WHOLE segment, on the IMU's own lattice.

    🛑 ONE envelope per segment, sliced by episode afterwards -- NOT a per-episode FFT. A per-episode
    FFT would give a 0.9 s cruise control a 1.1 Hz resolution and a 20 s maneuver 0.05 Hz, so the two
    arms would be measured with different instruments and the ratio would be an artefact of episode
    length. The envelope is the identical estimator for every episode on the segment.
    """
    bands = bands or BANDS
    axes = axes or AXES
    d = load_imu(tag, s)
    if d is None or len(d["at"]) < 500:
        return None
    out = {"odr": None}
    for ax in axes:
        t = d["at"] if ax[0] == "a" else d["gt"]
        u, odr, fill, tu = uniform(t, d[ax])
        out["odr"] = odr
        out.setdefault("t", {})[ax[0]] = tu
        out.setdefault("fill", {})[ax[0]] = fill
        for k, (lo, hi) in bands.items():
            out[(ax, k)] = env_full(u, odr, lo, hi)
    return out


def can_on(t_uni, dc, fs):
    """The CAN covariates a record needs, evaluated on the IMU's own times.

    Categorical (gate, latActive, gear) -> zero-order HOLD. Continuous (speed, effort, angle,
    rate) -> linear interpolation. Mixing the two up fabricates half-engaged frames.
    """
    eff = sustained(dc["tq"], fs)
    return dict(
        v=lerp(t_uni, dc["t"], dc["cs_v"]),
        eff=lerp(t_uni, dc["t"], eff),
        ang=lerp(t_uni, dc["t"], np.abs(dc["ang"])),
        rate=lerp(t_uni, dc["t"], np.abs(dc["rate_c"])),
        tq=lerp(t_uni, dc["t"], dc["tq"]),
        gate=hold(t_uni, dc["t"], dc.get("g6806", dc["cc_lat"])),
        lat=hold(t_uni, dc["t"], dc["cc_lat"] > 0.5),
        gear=hold(t_uni, dc["t"], dc.get("cs_gear", np.zeros(len(dc["t"])))),
    )


V_BINS = [(0.0, 0.5), (0.5, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 14.0), (14.0, 22.0),
          (22.0, 27.0), (27.0, 30.0), (30.0, 99.0)]
E_BINS = [(0.0, 200.0), (200.0, 800.0), (800.0, 2000.0), (2000.0, 1e9)]


def binof(x, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= x < hi:
            return i
    return len(bins) - 1 if x >= bins[-1][0] else 0
