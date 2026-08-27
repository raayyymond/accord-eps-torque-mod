#!/usr/bin/env python3
r"""Shared loader + spectral/bootstrap machinery for the V100(r85, 4x) vs V101(r95, 8x) contrast.

NO DECODER IS REIMPLEMENTED.  Both caches were written by the SAME extractor chain
(`extract_r7d.extract_route` via `decode/extract_r85.py` / `decode/extract_r95.py`), so field names, ZOH
convention and the `row2raw14` off-by-one fix are bit-for-bit identical between the two arms.

TRAPS HONOURED
  * `t` is EVENT-DRIVEN, not uniform (median dt 9.9 ms, p99 19.6 ms, zeros present, and r95s0
    carries a 1.32 s hole).  Every spectral estimate resamples onto a UNIFORM 100 Hz grid and
    SPLITS at any gap > 50 ms.  A raw FFT of the native grid is wrong.
  * The r85 whole-route `t` has a ~60 s HOLE (segment 17 absent).  Per-segment files only.
  * Engagement is `cc_lat > 0.5` (latActive).  `cs_eng` is identically 0 on r95 -- NEVER use it.
  * `v_rear` is METRES PER SECOND despite the extractor docstring saying km/h (checked against
    census `speed_all.max_kmh`: 29.136 m/s * 3.6 = 104.9 vs census 104.53).
  * Safe pairs are (t, probe) / (raw14_t, raw14_b4).  Every v100_b*/v101_b* column lives on the
    `t` row grid already.
"""
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"

FS = 100.0                      # the uniform analysis grid
GAP_S = 0.050                   # split a segment at any dt above this
KMH = 3.6

def _cache_dir(route):
    """Caches live under TWO roots -- `analysis-2020accord/_cache_r*` for r77+ and the REPO ROOT
    for the older ones (r71, r75, r76).  `_scratch/cache/r71` DOES exist, at the repo root, in the modern
    per-segment ~100 Hz schema; only `_scratch/cache/ratio/00000071.npz` (14.6 Hz) is the useless one."""
    for base in (AN, ROOT):
        p = base / ("_cache_r" + route)
        if p.exists():
            return p
    return AN / ("_cache_r" + route)


def _segs(route):
    p = _cache_dir(route)
    pre = "r" + route + "s"
    return tuple(sorted(int(f.stem[len(pre):]) for f in p.glob(pre + "*.npz")))


def _mk(route, build, **kw):
    return dict(build=build, cache=_cache_dir(route), pfx="r" + route + "s",
                segs=_segs(route), **kw)


ROUTES = {
    # gain = cal 0xC6CD0 ; leverB = 0x3AA96/0xC6446 armed (FB/5244) or reverted (C5/512)
    "85": _mk("85", "V100", gain=3564, clamp=2048, leverB=True, idcode=2, bits="v100"),
    "95": _mk("95", "V101", gain=7128, clamp=4096, leverB=False, idcode=3, bits="v101"),
    "71": _mk("71", "V87", gain=3564, clamp=2048, leverB=False, idcode=0, bits="v87"),
    "75": _mk("75", "V89", gain=3564, clamp=2048, leverB=True, idcode=0, bits="v89"),
    "76": _mk("76", "V89", gain=3564, clamp=2048, leverB=True, idcode=0, bits="v89"),
    "77": _mk("77", "V90", gain=3564, clamp=2048, leverB=True, idcode=0, bits="v90"),
    "73": _mk("73", "V88", gain=3564, clamp=2048, leverB=True, idcode=0, bits="v88"),
    "78": _mk("78", "V91", gain=3564, clamp=2048, leverB=True, idcode=0, bits="v91"),
}

# The kit's standing band vocabulary (compare_v75_v76_v80_grind.BAND4 + NEGCTRL).
BANDS = {
    "3-5":   (3.0, 5.0),         # LKAS command band (the low-pass passband)
    "6-9":   (6.0, 9.0),         # micro-ratchet ~7.8 Hz
    "10-15": (10.0, 15.0),
    "15-22": (15.0, 22.0),       # V88's grinding band
    "18-22": (18.0, 22.0),       # GRIND #1
    "22-26": (22.0, 26.0),       # *** the V101 line found by v102_xb_spectra #3b ***
    "26-31": (26.0, 31.0),       # lane-change ~28 Hz
    "32-38": (32.0, 38.0),       # PRE-DECLARED NEGATIVE CONTROL
    "40-49": (40.0, 49.0),       # GRIND #2
}
NEGCTRL = "32-38"

CH = ("tq", "rate_c", "cs_ang", "imu_lat", "imu_vert", "x6b94", "e4tq")
CH_NYQ = {"x6b94": 20.0}         # 427 is a 41.7 Hz stream ZOH'd up -> only trust below its Nyquist


def load_seg(route, seg):
    R = ROUTES[route]
    z = np.load(R["cache"] / (R["pfx"] + str(seg) + ".npz"))
    d = {k: np.asarray(z[k], float) for k in z.keys() if k != "probe_build"}
    if "v_rear" not in d:
        # caches before `decode/extract_r85.py` do not carry the rear-wheel speed; fall back to the rear
        # wheel-speed pair when present, else carState vEgo.  Units: METRES PER SECOND either way.
        if "ws_rl" in d and "ws_rr" in d:
            # EXACTLY `extract_r95.derive()`'s formula -- 0.5*(rl+rr), NO unit conversion.  An
            # earlier version divided by 3.6 here and put route 71's engaged median at 2.7 km/h
            # instead of 9.7, which emptied every matched cell.
            d["v_rear"] = 0.5 * (d["ws_rl"] + d["ws_rr"])
        else:
            d["v_rear"] = d["cs_v"]
    d["_route"], d["_seg"] = route, seg
    return d


def blocks(d):
    """Split one segment into gap-free blocks, resampled onto the uniform FS grid."""
    t = d["t"]
    brk = np.nonzero(np.diff(t) > GAP_S)[0]
    edges = [0] + [int(b) + 1 for b in brk] + [len(t)]
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a < 4 or t[b - 1] - t[a] < 2.0:
            continue
        tt = np.arange(t[a], t[b - 1], 1.0 / FS)
        blk = {"t": tt, "_route": d["_route"], "_seg": d["_seg"]}
        for k, v in d.items():
            if k.startswith("_") or k == "t" or np.shape(v) != np.shape(t):
                continue
            blk[k] = np.interp(tt, t[a:b], v[a:b])
        out.append(blk)
    return out


def all_blocks(route):
    out = []
    for s in ROUTES[route]["segs"]:
        out += blocks(load_seg(route, s))
    return out


def bandrms(x, fs, lo, hi, win):
    """RMS in [lo,hi) of a linearly-detrended, Hann-tapered window.  Parseval-normalised."""
    x = np.asarray(x, float)
    n = len(x)
    r = np.arange(n, dtype=float)
    c = np.polyfit(r, x, 1)
    y = (x - (c[0] * r + c[1])) * win
    scale = np.sqrt(np.mean(win ** 2))
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    m = (f >= lo) & (f < hi)
    p = (np.abs(X) ** 2) * 2.0 / (n ** 2)
    p[0] /= 2.0
    if n % 2 == 0:
        p[-1] /= 2.0
    return float(np.sqrt(p[m].sum())) / scale


def psd(x, fs, win):
    n = len(x)
    r = np.arange(n, dtype=float)
    c = np.polyfit(r, x, 1)
    y = (x - (c[0] * r + c[1])) * win
    scale = np.mean(win ** 2)
    X = np.fft.rfft(y)
    p = (np.abs(X) ** 2) * 2.0 / (n ** 2) / scale
    p[0] /= 2.0
    if n % 2 == 0:
        p[-1] /= 2.0
    return np.fft.rfftfreq(n, 1.0 / fs), p


def windows(route, nfft=256, hop=128, engaged=True, purity=0.98, vspread_kmh=8.0,
            keep_raw=False):
    """Uniform-grid analysis windows tagged with route, EPISODE id, speed and wheel rate.

    An EPISODE = a maximal contiguous run of the requested engagement state inside ONE block
    (hence inside one segment).  Episodes are the bootstrap unit; windows are never the unit.
    """
    win = np.hanning(nfft)
    recs, epi = [], 0
    for blk in all_blocks(route):
        eng = blk["cc_lat"] > 0.5
        want = eng if engaged else ~eng
        idx = np.nonzero(np.diff(want.astype(int)) != 0)[0] + 1
        bounds = [0] + list(idx) + [len(want)]
        for a, b in zip(bounds[:-1], bounds[1:]):
            if not want[a] or (b - a) < nfft:
                continue
            epi += 1
            for s in range(a, b - nfft + 1, hop):
                sl = slice(s, s + nfft)
                if want[sl].mean() < purity:
                    continue
                v = blk["v_rear"][sl] * KMH
                if v.max() - v.min() > vspread_kmh:
                    continue
                rec = dict(route=route, seg=blk["_seg"], epi=epi, i0=s,
                           t0=float(blk["t"][s]),
                           v=float(np.median(v)), vmin=float(v.min()), vmax=float(v.max()),
                           rate=float(np.median(np.abs(blk["rate_c"][sl]))),
                           tqmed=float(np.median(np.abs(blk["cs_tq"][sl]))),
                           e4=float(np.median(np.abs(blk["e4tq"][sl]))),
                           e4max=float(np.max(np.abs(blk["e4tq"][sl]))))
                for ch in CH:
                    if ch not in blk:
                        continue
                    x = blk[ch][sl]
                    for bn, (lo, hi) in BANDS.items():
                        if hi > CH_NYQ.get(ch, FS / 2):
                            continue
                        rec[ch + "|" + bn] = bandrms(x, FS, lo, hi, win)
                if keep_raw:
                    rec["_blk"] = blk
                    rec["_sl"] = sl
                recs.append(rec)
    return recs


def boot_ratio(recs_a, recs_b, key, nboot=4000, seed=0, stat=np.median):
    """Ratio of pooled band RMS, BLOCK-BOOTSTRAPPED OVER EPISODES (never windows)."""
    rng = np.random.default_rng(seed)

    def by_epi(recs):
        d = {}
        for r in recs:
            if key in r and np.isfinite(r[key]):
                d.setdefault((r["route"], r["seg"], r["epi"]), []).append(r[key])
        return [np.asarray(v, float) for v in d.values()]

    A, B = by_epi(recs_a), by_epi(recs_b)
    if not A or not B:
        return dict(ratio=np.nan, lo=np.nan, hi=np.nan, nA=len(A), nB=len(B), wA=0, wB=0)
    pt = stat(np.concatenate(A)) / stat(np.concatenate(B))
    out = np.empty(nboot)
    for i in range(nboot):
        a = np.concatenate([A[j] for j in rng.integers(0, len(A), len(A))])
        b = np.concatenate([B[j] for j in rng.integers(0, len(B), len(B))])
        out[i] = stat(a) / stat(b)
    good = out[np.isfinite(out)]
    lo, hi = np.percentile(good, [2.5, 97.5]) if len(good) else (np.nan, np.nan)
    return dict(ratio=float(pt), lo=float(lo), hi=float(hi),
                nA=len(A), nB=len(B),
                wA=int(sum(len(x) for x in A)), wB=int(sum(len(x) for x in B)))


def sel(recs, vlo=None, vhi=None, rlo=None, rhi=None):
    out = recs
    if vlo is not None:
        out = [r for r in out if r["v"] >= vlo]
    if vhi is not None:
        out = [r for r in out if r["v"] < vhi]
    if rlo is not None:
        out = [r for r in out if r["rate"] >= rlo]
    if rhi is not None:
        out = [r for r in out if r["rate"] < rhi]
    return out


def nepi(recs):
    return len({(r["route"], r["seg"], r["epi"]) for r in recs})
