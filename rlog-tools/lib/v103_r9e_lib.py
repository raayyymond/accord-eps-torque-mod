#!/usr/bin/env python3
r"""lib/v103_r9e_lib.py -- shared loader + window machinery for route `9e` (V103).

Registers route `9e` with `v102_xb_lib` so every existing harness finds it, and adds the ONE thing
the brief demands that the existing chain does not do: **BLOCK BOOTSTRAP OVER EPISODES**, not over
windows.  Window bootstraps manufacture significance (memory `feedback-episodes-not-windows`).

🛑 CONVENTIONS THAT MUST NOT BE BROKEN (each has cost this kit a wrong answer):
  * `carState.yawRate` is IDENTICALLY ZERO on this car -> use `lp_yaw` (livePose z, z-DOWN).
  * `vEgo` is +7.9 % fast at 250-400 deg of angle -> speed reference is `v_rear = (ws_rl+ws_rr)/2`.
  * `raw14` off-by-one: `t` == `raw14_t[1:]`, `probe` == `raw14_b4[1:]`.  Only (t,probe) or
    (raw14_t,raw14_b4) may be paired.  This module only ever uses (t, probe).
  * `band_envelope` in `_r31_common`/`_r2b_common` is RECTIFIED, not analytic -> use
    `scipy.signal.hilbert` for any envelope statistic.
  * Engagement is `latActive` / `0x18F` b4 bit3 / `0x0E4` byte2 bit7 -- NEVER `cruiseState`.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L          # noqa: E402
import decode_v90_probe as P     # noqa: E402

# ---- register the new arms on the shared lib -------------------------------------------------
L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0, bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")
L.ROUTES["9e"] = L._mk("9e", "V103", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v103")
if "20-28" not in L.BANDS:
    L.BANDS["20-28"] = (20.0, 28.0)          # SPEC-2026-08-20 primary for band-RMS
if "21.5-25.5" not in L.BANDS:
    L.BANDS["21.5-25.5"] = (21.5, 25.5)      # legacy, retained for comparability
if "2.5-4.5" not in L.BANDS:
    L.BANDS["2.5-4.5"] = (2.5, 4.5)          # shape denominator / control
if "31-35" not in L.BANDS:
    L.BANDS["31-35"] = (31.0, 35.0)          # PRE-DECLARED negative control (handoff 3.4)

DEG2RAD = np.pi / 180.0
NW_Z, HOP_Z = P.NW_Z, P.HOP_Z                # 512 / 256 == 5.12 s at 100 Hz, the FROZEN estimator
VLO, VHI = 8.0, 24.0                         # m/s == 29-86 km/h, the f0 conditioning window
FIT = np.arange(19.0, 30.0, 1.0)             # 2 Hz bands; brackets every arm's crossing


def load(route="9e"):
    R = L.ROUTES[route]
    z = np.load(R["cache"] / ("r" + route + ".npz"), allow_pickle=True)
    return {k: np.asarray(z[k]) for k in z.files}


def masks(z):
    """The kit's standing masks.  Speed in m/s from `cs_v` (the estimator's own reference, kept for
    comparability) AND `v_rear` in km/h (the correct one at angle)."""
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    return dict(eng=lat, press=press, v=v,
                v_rear=np.asarray(z["v_rear"], float),
                rate=np.abs(np.asarray(z["rate_f"], float)),
                moving=v > 0.5)


def episodes(mask, t, min_len=NW_Z, max_gap=0.05):
    """Contiguous runs of `mask` at least `min_len` samples long -- the BOOTSTRAP BLOCK UNIT."""
    import _r31_common as C31
    return list(C31.runs_of(mask, t, min_len, max_gap=max_gap))


def wins_by_episode(z, mask, arrays, nw=NW_Z, hop=HOP_Z, vlo=None, vhi=None):
    """Windows grouped by their parent episode.  Returns [[w,...], ...], one list per episode.
    `arrays` is a tuple of same-length columns; each window is a tuple of slices.
    If vlo/vhi given, windows are filtered on the MEDIAN of arrays[-1] (which must be speed)."""
    t = np.asarray(z["t"], float)
    out = []
    for a, b in episodes(mask, t, nw):
        ep = []
        for i in range(0, (b - a) - nw + 1, hop):
            sl = slice(a + i, a + i + nw)
            w = tuple(A[sl] for A in arrays)
            if vlo is not None:
                m = float(np.median(w[-1]))
                if not (vlo <= m < vhi):
                    continue
            ep.append(w)
        if ep:
            out.append(ep)
    return out


def rez_pairs(z, extra_mask=None, hop=HOP_Z, vlo=VLO, vhi=VHI):
    """The frozen Re(Z) conditioning: engaged, hands-OFF, moving, speed-windowed.
    Returns (episode_groups, fs) where each group is a list of (rate_rad, tq) pairs."""
    M = masks(z)
    m = M["eng"] & (~M["press"]) & M["moving"]
    if extra_mask is not None:
        m = m & extra_mask
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    G = wins_by_episode(z, m, (np.asarray(z["rate_f"], float) * DEG2RAD,
                               np.asarray(z["tq"], float), M["v"]),
                        hop=hop, vlo=vlo, vhi=vhi)
    return [[(w[0], w[1]) for w in ep] for ep in G], fs


def f0_of(pairs, fs, fit=FIT):
    """Zero-crossing frequency of Re(Z) -- VERBATIM `rez_crossover.f0_of`, no re-implementation."""
    f, y = [], []
    for lo in fit:
        r = P._band_transfer(pairs, fs, NW_Z, [("b", lo, lo + 2.0)])["b"]
        f.append(lo + 1.0)
        y.append(r["re_over_sxx"])
    f, y = np.array(f), np.array(y)
    if not (np.any(y < 0) and np.any(y > 0)):
        return np.nan
    c = np.polyfit(f, y, 1)
    return float(-c[1] / c[0]) if c[0] != 0 else np.nan


def boot_episode(groups, fs, stat, nboot=400, rng=None):
    """BLOCK BOOTSTRAP OVER EPISODES.  Resample whole episodes with replacement, pool their
    windows, evaluate `stat(pooled_pairs, fs)`.  This is the pre-registered resampling unit."""
    rng = rng or np.random.default_rng(1030_2026)
    ne = len(groups)
    if ne == 0:
        return np.array([])
    out = []
    for _ in range(nboot):
        idx = rng.integers(0, ne, ne)
        pool = [w for k in idx for w in groups[k]]
        if len(pool) < 4:
            continue
        v = stat(pool, fs)
        if np.isfinite(v):
            out.append(v)
    return np.array(out)


def boot_window(pairs, fs, stat, nboot=400, rng=None):
    """Window bootstrap -- reported ONLY as the comparability number against the existing record
    (`studies/impedance/rez_crossover.py` used it).  It UNDERSTATES the CI; the episode bootstrap is primary."""
    rng = rng or np.random.default_rng(1030_2026)
    out = []
    for _ in range(nboot):
        v = stat([pairs[k] for k in rng.integers(0, len(pairs), len(pairs))], fs)
        if np.isfinite(v):
            out.append(v)
    return np.array(out)


def band_rms(x, fs, lo, hi, nw=256, hop=128):
    """Per-window band RMS via Welch-style rfft on a Hann taper.  Returns one value per window."""
    w = np.hanning(nw)
    out = []
    f = np.fft.rfftfreq(nw, 1.0 / fs)
    m = (f >= lo) & (f <= hi)
    scale = 1.0 / (np.sum(w ** 2) * fs)
    for i in range(0, len(x) - nw + 1, hop):
        seg = x[i:i + nw]
        X = np.fft.rfft((seg - seg.mean()) * w)
        psd = (np.abs(X) ** 2) * scale
        psd[1:-1] *= 2.0
        out.append(float(np.sqrt(np.sum(psd[m]) * (f[1] - f[0]))))
    return np.array(out)


def ci(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if len(a) < 3:
        return (np.nan, np.nan)
    return tuple(float(x) for x in np.percentile(a, [lo, hi]))
