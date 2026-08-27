#!/usr/bin/env python3
"""D5 ss3-5 -- ONE mode or TWO?  High-resolution spectra, harmonic TRACKING, and the AM test.

The operator says grind #1 and the micro ratchet "feel like the same vibration frequency", differing
only in audibility. This kit records 18-22 Hz vs 7.79 Hz. Three ways that can both be true:

  (a) TWO modes, and the felt frequency is dominated by whichever is larger  -> kit's account.
  (b) ONE mode, and 7.79 Hz is a SUBHARMONIC of it                          -> needs 20.9/7.79 to be
      an integer ratio (it is 2.68) or the ratchet's true line to be ~10.4 Hz (f/2).
  (c) ONE CARRIER at ~20 Hz AMPLITUDE-MODULATED at ~7.8 Hz. The ear hears the 20 Hz carrier ("grind"),
      the hand feels the 7.8 Hz envelope ("ratchet"). This reconciles BOTH accounts with one mode.

  ss3  averaged periodogram at NFFT 512 (0.195 Hz) and 1024 (0.098 Hz), engaged, by speed bin.
  ss4  per-EPISODE peak pairing: does f(6-9) TRACK f(18-22)?  Theil-Sen slope + shuffled-pairing null.
       🛑 A RATIO IS NOT A TRACKING TEST. This kit has retracted a harmonic claim built on marginals.
  ss5  AM test: envelope of the 12-28 Hz carrier, spectrum it, look at 6-9 Hz -- against a
       PHASE-RANDOMISED surrogate that preserves the carrier's power spectrum exactly and destroys
       only the amplitude structure. Plus the sideband check f0 +/- f_r in the high-res spectrum.
  ss6  channel check: which recorded channel is the driver torsion-bar sensor, and are both lines
       in it (not only in derived channels)?

Instrument is `_grind2_lib` / `_r31_common` unchanged; `fs_lattice` via `_r4f_lib.install_fs()`.
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
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r59_lib as L  # noqa: E402

OUT = ROOT / "_scratch/out/_d5_modes.json"
RNG = np.random.default_rng(8052026)

BUILDS = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V70/r50", "V62/r37", "V65/r3a",
          "V65/r3b", "V67/r47", "V68/r4e", "V71B/r54", "V71C/r58", "V72/r59"]
VB = [(0.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 1e9)]
VN = ["0-2", "2-4", "4-8", "8-15", "15-25", "25+"]
LOW = (5.0, 12.0)          # FREE locate band for the ratchet -- wider than the strict 6-9
HIGH = (15.0, 26.0)        # FREE locate band for grind #1  -- wider than the strict 18-22
CARRIER = (12.0, 28.0)     # AM carrier band: contains 18-22 and its +/-8 Hz sidebands, EXCLUDES 6-9


def segs_of(build):
    B = G.BUILDS[build]
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if p.exists():
            yield s, C.load(s, B["cache"], B["pfx"])


def vbin(v):
    for i, (lo, hi) in enumerate(VB):
        if lo <= v < hi:
            return i
    return len(VB) - 1


# ------------------------------------------------------------------ ss3 high-res spectra --------
def avg_spec(nfft, chan="tq", drop_parked=True):
    """{vbin: (f, meanP, K)} over ENGAGED windows, averaged over disjoint runs, all builds pooled.

    Windows are cut inside contiguous runs of latActive only, never across a transition; the speed
    selection is applied PER WINDOW after cutting (creep-script convention).
    """
    acc = {i: None for i in range(len(VB))}
    K = {i: 0 for i in range(len(VB))}
    fref = None
    hop = nfft // 2
    for b in BUILDS:
        bad = L.PARKED.get(b, []) if drop_parked else []
        for s, d in segs_of(b):
            if s in bad or chan not in d:
                continue
            fs = G.fs_of(d)
            f = np.fft.rfftfreq(nfft, 1 / fs)
            if fref is None:
                fref = f
            x = np.asarray(d[chan], float)
            v = np.abs(np.asarray(d["cs_v"], float))
            m = np.asarray(d["cc_lat"], float) > 0.5
            for a, bnd in C.runs_of(m, d["t"], nfft):
                for i in range(a, bnd - nfft + 1, hop):
                    P = C.periodogram(x[i:i + nfft], fs, nfft, True)
                    if P is None:
                        continue
                    j = vbin(float(np.mean(v[i:i + nfft])))
                    acc[j] = P.copy() if acc[j] is None else acc[j] + P
                    K[j] += 1
    return {i: (fref, (acc[i] / K[i] if K[i] else None), K[i]) for i in range(len(VB))}


def report_spec(name, spec):
    L.hdr(f"ss3  {name} -- averaged engaged periodogram of `tq`, peak of the PROMINENCE spectrum")
    print(f"  {'v (m/s)':<9}{'K':>7}   {'ratchet 5-12 Hz':>26}   {'grind 15-26 Hz':>26}"
          f"   {'ratio hi/lo':>12}")
    rows = {}
    for i, nm in enumerate(VN):
        f, P, K = spec[i]
        if P is None or K < 8:
            print(f"  {nm:<9}{K:>7}   {'-- UNPOWERED --':>26}")
            rows[nm] = None
            continue
        R = G.prom_spectrum(f, P)
        f1, p1 = G.locate(f, P, *LOW, R=R)
        f2, p2 = G.locate(f, P, *HIGH, R=R)
        rows[nm] = dict(K=K, f_low=f1, p_low=p1, f_high=f2, p_high=p2, ratio=f2 / f1)
        print(f"  {nm:<9}{K:>7}   {f1:>10.3f} Hz prom {p1:>6.2f}   {f2:>10.3f} Hz prom {p2:>6.2f}"
              f"   {f2/f1:>12.3f}")
    return rows


# ------------------------------------------------------------------ ss4 tracking test ------------
def per_window_pairs(nfft=512, vlo=0.0, vhi=1e9, min_prom=2.5):
    """[(build, seg, run, t0, v, f_low, p_low, f_high, p_high)] for engaged windows.

    `run` identifies the contiguous engagement run -- the EPISODE, the resampling unit.
    """
    out = []
    hop = nfft // 2
    for b in BUILDS:
        bad = L.PARKED.get(b, [])
        for s, d in segs_of(b):
            if s in bad:
                continue
            fs = G.fs_of(d)
            f = np.fft.rfftfreq(nfft, 1 / fs)
            x = np.asarray(d["tq"], float)
            v = np.abs(np.asarray(d["cs_v"], float))
            m = np.asarray(d["cc_lat"], float) > 0.5
            for a, bnd in C.runs_of(m, d["t"], nfft):
                for i in range(a, bnd - nfft + 1, hop):
                    vm = float(np.mean(v[i:i + nfft]))
                    if not (vlo <= vm < vhi):
                        continue
                    P = C.periodogram(x[i:i + nfft], fs, nfft, True)
                    if P is None:
                        continue
                    R = G.prom_spectrum(f, P)
                    f1, p1 = G.locate(f, P, *LOW, R=R)
                    f2, p2 = G.locate(f, P, *HIGH, R=R)
                    if not (np.isfinite(f1) and np.isfinite(f2)):
                        continue
                    if p1 < min_prom or p2 < min_prom:
                        continue
                    out.append(dict(build=b, seg=int(s), run=(b, int(s), int(a)),
                                    t0=float(d["t"][i]), v=vm, f_low=f1, p_low=p1,
                                    f_high=f2, p_high=p2))
    return out


def theil_sen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    i, j = np.triu_indices(n, 1)
    dx = x[j] - x[i]
    ok = np.abs(dx) > 1e-9
    sl = (y[j] - y[i])[ok] / dx[ok]
    if not len(sl):
        return np.nan, np.nan
    m = float(np.median(sl))
    return m, float(np.median(y - m * x))


def tracking_test(pairs, nboot=2000):
    """Theil-Sen slope of f_high on f_low, EPISODE-bootstrapped, against a shuffled-pairing null.

    The null re-pairs each window's f_high with a f_low drawn from a DIFFERENT episode, which
    destroys any within-window coupling while preserving both marginals exactly -- the specific
    failure mode ("a ratio computed on marginals") that this kit has already retracted once.
    """
    eps = {}
    for p in pairs:
        eps.setdefault(p["run"], []).append(p)
    eps = list(eps.values())
    if len(eps) < 4:
        return None
    x = np.array([p["f_low"] for p in pairs])
    y = np.array([p["f_high"] for p in pairs])
    slope, inter = theil_sen(x, y)
    draws = np.full(nboot, np.nan)
    for k in range(nboot):
        ii = RNG.integers(0, len(eps), len(eps))
        sub = [p for i in ii for p in eps[i]]
        draws[k] = theil_sen([p["f_low"] for p in sub], [p["f_high"] for p in sub])[0]
    null = np.full(nboot, np.nan)
    for k in range(nboot):
        perm = RNG.permutation(len(eps))
        xs, ys = [], []
        for a, b in zip(range(len(eps)), perm):
            n = min(len(eps[a]), len(eps[b]))
            xs += [p["f_low"] for p in eps[b][:n]]
            ys += [p["f_high"] for p in eps[a][:n]]
        null[k] = theil_sen(xs, ys)[0]
    r = float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else np.nan
    return dict(n=len(pairs), nep=len(eps), slope=slope, inter=inter,
                lo=float(np.nanpercentile(draws, 2.5)), hi=float(np.nanpercentile(draws, 97.5)),
                null_lo=float(np.nanpercentile(null, 2.5)),
                null_hi=float(np.nanpercentile(null, 97.5)),
                null_med=float(np.nanmedian(null)), pearson=r,
                med_low=float(np.median(x)), med_high=float(np.median(y)),
                med_ratio=float(np.median(y / x)))


# ------------------------------------------------------------------ ss5 the AM test --------------
def band_analytic(x, fs, lo, hi):
    """Analytic signal restricted to [lo,hi]; returns the complex band-limited signal."""
    x = np.asarray(x, float)
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    x = x - (c[0] * r + c[1])
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.fft.irfft(H, n=len(x)), m, X


def phase_surrogate(x, fs, lo, hi, rng):
    """Randomise the PHASES inside [lo,hi], keeping every magnitude. Same power spectrum, no AM."""
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    y = np.asarray(x, float) - (c[0] * r + c[1])
    X = np.fft.rfft(y)
    f = np.fft.rfftfreq(len(y), 1 / fs)
    m = (f >= lo) & (f <= hi)
    ph = rng.uniform(0, 2 * np.pi, int(m.sum()))
    H = np.zeros(len(f), complex)
    H[m] = 2 * np.abs(X[m]) * np.exp(1j * ph)
    return np.fft.irfft(H, n=len(y))


def env_spectrum(z, fs, nfft):
    """Prominence spectrum of the ENVELOPE |z|, mean removed, Hann-tapered."""
    e = np.abs(z)
    e = e - e.mean()
    P = C.periodogram(e, fs, nfft, True)
    if P is None:
        return None, None
    f = np.fft.rfftfreq(nfft, 1 / fs)
    return f, P


def am_test(nfft=512, vlo=0.0, vhi=4.0, nsur=40, min_e=300.0, max_win=900):
    """For high-amplitude engaged creep windows: is the 12-28 Hz envelope modulated at 6-9 Hz?

    Reported as the envelope-spectrum PROMINENCE in 6-9 Hz, paired per window against `nsur`
    phase-randomised surrogates of the SAME window. A surrogate keeps the carrier's power spectrum
    bit-for-bit and destroys only the phase relations that create amplitude modulation, so it is the
    correct null: any envelope structure a plain band-limited noise burst produces is in it too.
    """
    taper = np.hanning(nfft) + 1e-3
    cw = slice(int(0.2 * nfft), int(0.8 * nfft))
    obs, sur, meta = [], [], []
    hop = nfft // 2
    for b in BUILDS:
        bad = L.PARKED.get(b, [])
        for s, d in segs_of(b):
            if s in bad:
                continue
            fs = G.fs_of(d)
            x = np.asarray(d["tq"], float)
            v = np.abs(np.asarray(d["cs_v"], float))
            m = np.asarray(d["cc_lat"], float) > 0.5
            for a, bnd in C.runs_of(m, d["t"], nfft):
                for i in range(a, bnd - nfft + 1, hop):
                    vm = float(np.mean(v[i:i + nfft]))
                    if not (vlo <= vm < vhi):
                        continue
                    xw = x[i:i + nfft]
                    if not np.all(np.isfinite(xw)):
                        continue
                    if G.win_env(xw, fs, 18.0, 22.0, taper, cw) < min_e:
                        continue
                    z, _, _ = band_analytic(xw, fs, *CARRIER)
                    za = _hilbert(z)
                    f, P = env_spectrum(za, fs, nfft)
                    if P is None:
                        continue
                    R = G.prom_spectrum(f, P, halfwin=4.0, exclude=1.0)
                    f1, p1 = G.locate(f, P, 6.0, 9.0, R=R)
                    ss = []
                    for k in range(nsur):
                        ys = phase_surrogate(xw, fs, *CARRIER, rng=RNG)
                        zs = _hilbert(ys)
                        fs2, Ps = env_spectrum(zs, fs, nfft)
                        if Ps is None:
                            continue
                        Rs = G.prom_spectrum(fs2, Ps, halfwin=4.0, exclude=1.0)
                        ss.append(G.locate(fs2, Ps, 6.0, 9.0, R=Rs)[1])
                    if not ss:
                        continue
                    obs.append(p1)
                    sur.append(float(np.median(ss)))
                    meta.append(dict(build=b, seg=int(s), v=vm, f_env=f1,
                                     run=(b, int(s), int(a))))
                    if len(obs) >= max_win:
                        return np.array(obs), np.array(sur), meta
    return np.array(obs), np.array(sur), meta


def _hilbert(xr):
    """Analytic signal of a real band-limited series (no scipy dependency)."""
    n = len(xr)
    X = np.fft.fft(xr)
    h = np.zeros(n)
    if n % 2 == 0:
        h[0] = h[n // 2] = 1
        h[1:n // 2] = 2
    else:
        h[0] = 1
        h[1:(n + 1) // 2] = 2
    return np.fft.ifft(X * h)


def main():
    L.install_fs()
    res = {}

    for nfft in (512, 1024):
        sp = avg_spec(nfft)
        res[f"spec{nfft}"] = report_spec(f"NFFT {nfft} ({nfft/100:.2f} s, "
                                         f"{100/nfft:.3f} Hz bins)", sp)
        # keep the creep and highway mean spectra for the sideband inspection
        for i, nm in enumerate(VN):
            f, P, K = sp[i]
            if P is None:
                continue
            res.setdefault("curves", {})[f"{nfft}|{nm}"] = dict(
                K=K, f=[float(z) for z in f[(f >= 2) & (f <= 46)]],
                P=[float(z) for z in P[(f >= 2) & (f <= 46)]])

    # ---------------------------------------------------------------- ss4 tracking --------------
    L.hdr("ss4  DOES THE RATCHET LINE TRACK THE GRIND LINE?  per-window peaks, EPISODE bootstrap")
    for label, (vlo, vhi) in (("creep 0-4 m/s", (0.0, 4.0)), ("mid 4-15 m/s", (4.0, 15.0)),
                              ("all speeds", (0.0, 1e9))):
        pr = per_window_pairs(512, vlo, vhi)
        t = tracking_test(pr) if pr else None
        res.setdefault("tracking", {})[label] = t
        if not t:
            print(f"  {label:<16} -- underpowered (n={len(pr)})")
            continue
        print(f"  {label:<16} n={t['n']:<5d} eps={t['nep']:<4d}  "
              f"median f_low {t['med_low']:.2f} Hz   f_high {t['med_high']:.2f} Hz   "
              f"median ratio {t['med_ratio']:.3f}")
        print(f"  {'':<16} Theil-Sen slope f_high~f_low = {t['slope']:+.3f} "
              f"[{t['lo']:+.3f}, {t['hi']:+.3f}]   pearson r = {t['pearson']:+.3f}")
        print(f"  {'':<16} shuffled-pairing NULL slope = {t['null_med']:+.3f} "
              f"[{t['null_lo']:+.3f}, {t['null_hi']:+.3f}]")

    # ---------------------------------------------------------------- ss5 AM --------------------
    L.hdr("ss5  AM TEST -- is the 12-28 Hz carrier's ENVELOPE modulated at 6-9 Hz? (creep, engaged)")
    obs, sur, meta = am_test()
    if len(obs) < 20:
        print(f"  -- underpowered, n={len(obs)}")
        res["am"] = dict(n=int(len(obs)))
    else:
        eps = {}
        for i, m in enumerate(meta):
            eps.setdefault(m["run"], []).append(i)
        keys = list(eps)
        d = obs - sur
        draws = np.full(4000, np.nan)
        for k in range(4000):
            ii = RNG.integers(0, len(keys), len(keys))
            idx = [j for i in ii for j in eps[keys[i]]]
            draws[k] = np.median(d[idx])
        lo, hi = np.nanpercentile(draws, [2.5, 97.5])
        rat = float(np.median(obs) / np.median(sur))
        print(f"  n windows = {len(obs)}   episodes = {len(keys)}   "
              f"median envelope-6-9 prominence  OBSERVED {np.median(obs):.3f}  "
              f"SURROGATE {np.median(sur):.3f}")
        print(f"  paired difference (obs - phase-randomised surrogate) = {np.median(d):+.4f} "
              f"[{lo:+.4f}, {hi:+.4f}]   ratio {rat:.3f}")
        print(f"  median envelope peak frequency = {np.median([m['f_env'] for m in meta]):.3f} Hz")
        res["am"] = dict(n=int(len(obs)), nep=len(keys), obs=float(np.median(obs)),
                         sur=float(np.median(sur)), diff=float(np.median(d)),
                         lo=float(lo), hi=float(hi), ratio=rat,
                         f_env=float(np.median([m["f_env"] for m in meta])))

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
