# -*- coding: utf-8 -*-
r"""drive_read_fastpresence.py -- v293_flight_read.presence (the record's 18-22 Hz ring-presence predicate), EXACT,
without the per-window 2049 x 2049 nanmedian.

ANALYSIS ONLY.  The predicate is UNCHANGED: 2 s windows on a 0.5 s grid inside runs of the mask; PRESENT = 15-26 Hz
line prominence >= 8 on the driver-torque bar AND 18-22 Hz bar amplitude >= 40; the same aggregates.

WHAT IS DIFFERENT (and why the numbers cannot move):
  * the prominence floor (_grind2_lib.prom_spectrum) is a per-bin MEDIAN of the periodogram over the bin's
    neighbourhood mask M (the library's own _nearmask, used here unchanged).  _grind2_lib.locate reads R only on
    the 15-26 Hz bins (argmax of R where lo <= f <= hi and R finite, then R[j] and P around j), so only those rows
    are computed; every other bin is NaN, which locate never reads.  The median is np.median's own definition --
    the middle order statistic, or (lower + upper) / 2 for an even count -- taken with np.partition on the gathered
    neighbourhood values, row by row identical to nanmedian of where(M, P, nan) (P has no NaN).
  * the periodogram, x - x.mean(), locate, and the band amplitude are the library's own calls per window (the band
    filter is designed once instead of per call -- butter() is deterministic, the same sos array).
  * the 18-22 Hz bar amplitude is evaluated only where prom >= 8 (the predicate is `prom >= 8 and amp >= 40`).
  * a window shared by two calls is computed once; the windows are computed on 8 threads (FFT and partition
    release the GIL; each window's arithmetic is the single-window call's).
check_against_library() re-runs the library's line_of on sampled windows and asserts equality of (f0, prom).
"""
from __future__ import annotations

import numpy as np
from scipy import signal

VERSION = "fastpresence-1"
_SOS = {}
_ROWS = {}


def _sos(lo, hi, fs):
    k = (lo, hi, fs)
    if k not in _SOS:
        _SOS[k] = signal.butter(4, (lo, min(hi, 0.98 * fs / 2)), btype="bandpass", fs=fs, output="sos")
    return _SOS[k]


def bamp(x, lo, hi, fs):
    """creep20_loop_id.bamp with the filter designed once."""
    if len(x) < 32:
        return np.nan
    y = signal.sosfiltfilt(_sos(lo, hi, fs), x - np.mean(x))
    return float(np.sqrt(2) * y.std())


def _band_rows(G2, f, lo, hi, halfwin, exclude):
    """the rows locate can read (lo <= f <= hi), grouped by neighbourhood count, with their gather indices."""
    key = (len(f), float(f[1]), lo, hi, halfwin, exclude)
    if key not in _ROWS:
        M = G2._nearmask(np.asarray(f, float), halfwin, exclude)
        rows = np.flatnonzero((f >= lo) & (f <= hi))
        rows = rows[(rows > 0) & (rows < len(f) - 1)]          # R[0] = R[-1] = NaN in the library
        groups = {}
        for r in rows:
            idx = np.flatnonzero(M[r])
            groups.setdefault(len(idx), []).append((r, idx))
        G = []
        for c, lst in groups.items():
            rr = np.array([r for r, _ in lst], np.int64)
            II = np.array([i for _, i in lst], np.int64).reshape(len(lst), c) if c else np.zeros((len(lst), 0), np.int64)
            G.append((c, rr, II))
        _ROWS[key] = G
    return _ROWS[key]


def prom_rows(G2, f, P, lo, hi, halfwin=6.0, exclude=1.5):
    """_grind2_lib.prom_spectrum's R on the rows locate reads (NaN elsewhere)."""
    R = np.full(len(P), np.nan)
    for c, rr, II in _band_rows(G2, f, lo, hi, halfwin, exclude):
        if c == 0:
            continue                                            # nanmedian of an all-NaN row -> NaN -> R NaN
        V = P[II]
        if c % 2:
            k = c // 2
            fl = np.partition(V, k, axis=1)[:, k]
        else:
            k = c // 2
            Vp = np.partition(V, (k - 1, k), axis=1)
            fl = (Vp[:, k - 1] + Vp[:, k]) / 2.0
        R[rr] = np.where(fl > 0, P[rr] / np.where(fl > 0, fl, 1.0), np.nan)
    return R


def line_of(G2, x, fs, lo=15.0, hi=26.0, nfft=4096):
    """grind_incident_r35.line_of -> (f0, prom), exact."""
    x = np.asarray(x, float)
    if len(x) < 32:
        return np.nan, np.nan
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    Rp = prom_rows(G2, f, P, lo, hi)
    return G2.locate(f, P, lo, hi, R=Rp)


class Presence:
    """v293_flight_read.presence(g, mask, W, STEP) with a per-window memo shared across calls on one route."""

    def __init__(self, FR):
        self.FR = FR
        self.G2 = FR.GI.G2
        self.memo = {}

    def _win(self, bar, s, W):
        k = (s, W)
        if k not in self.memo:
            f0, prom = line_of(self.G2, bar[s:s + W], self.FR.FS)
            self.memo[k] = [f0, prom, None]
        return self.memo[k]

    def _fill(self, bar, starts, W, threads=8):
        """(f0, prom) of every window start not yet in the memo.  Threads, not processes: the periodogram FFT and
        np.partition release the GIL, each window is computed exactly as alone, and map() keeps the order."""
        todo = [s for s in dict.fromkeys(starts) if (s, W) not in self.memo]
        if not todo:
            return
        self._win(bar, todo[0], W)                          # builds the row/gather tables once, in this thread
        todo = todo[1:]
        fs, G2 = self.FR.FS, self.G2
        if len(todo) < 64 or threads <= 1:
            res = [line_of(G2, bar[s:s + W], fs) for s in todo]
        else:
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=threads) as ex:
                res = list(ex.map(lambda s: line_of(G2, bar[s:s + W], fs), todo, chunksize=16))
        for s, (f0, prom) in zip(todo, res):
            self.memo[(s, W)] = [f0, prom, None]

    def __call__(self, g, mask, W=200, STEP=50, label=""):
        FR = self.FR
        ra, npres, n, f0s = [], 0, 0, []
        bar, wire = g["bar"], g["wire"]
        self._fill(bar, [s for a, b in FR.C20.runs(mask, W) for s in range(a, b - W + 1, STEP)], W)
        for a, b in FR.C20.runs(mask, W):
            for s in range(a, b - W + 1, STEP):
                e = s + W
                rec = self._win(bar, s, W)
                f0, prom = rec[0], rec[1]
                n += 1
                if prom >= 8:
                    if rec[2] is None:
                        rec[2] = bamp(bar[s:e], 18, 22, FR.FS)              # CEN.band(bar, 18, 22)
                    if rec[2] >= 40:
                        npres += 1
                        ra.append(bamp(wire[s:e], 18, 22, FR.FS) / FR.CPD)  # CEN.band(wire, 18, 22) / CPD
                        f0s.append(f0)
        ra = np.asarray(ra, float)
        return dict(n_win=n, n_pres=npres, pres_pct=(100.0 * npres / n if n else float("nan")),
                    amp_p50=(float(np.median(ra)) if len(ra) else float("nan")),
                    amp_p90=(float(np.percentile(ra, 90)) if len(ra) else float("nan")),
                    f0_p50=(float(np.median(f0s)) if f0s else float("nan")))


# DRIFT GUARD: the library functions this module mirrors or replaces, hashed when the equality was proved
SOURCE_SHA = {
    "v293_flight_read.presence": "92c62cc377eeab12", "grind_incident_r35.line_of": "3cd6a1b6a38b24bb",
    "grind1_census_v282.line_of": "ce97c58109438ae0", "grind1_census_v282.band": "5d59a6f907d01c5b",
    "grind_incident_r35.band": "ff0a466c49486a26", "creep20_loop_id.bamp": "1d0546fa23f668de",
    "creep20_loop_id.runs": "ae2d6f7ba6005cc1", "_grind2_lib.prom_spectrum": "8b11c320364d4899",
    "_grind2_lib._nearmask": "bed3537a20abbc89",
}


def drift(FR):
    """[] when every mirrored library function is unchanged; else the names that moved (-> use FR.presence)."""
    import hashlib
    import inspect
    objs = {"v293_flight_read.presence": FR.presence, "grind_incident_r35.line_of": FR.GI.line_of,
            "grind1_census_v282.line_of": FR.CEN.line_of, "grind1_census_v282.band": FR.CEN.band,
            "grind_incident_r35.band": FR.GI.band, "creep20_loop_id.bamp": FR.C20.bamp,
            "creep20_loop_id.runs": FR.C20.runs, "_grind2_lib.prom_spectrum": FR.GI.G2.prom_spectrum,
            "_grind2_lib._nearmask": FR.GI.G2._nearmask}
    bad = []
    for k, o in objs.items():
        try:
            h = hashlib.sha256(inspect.getsource(o).replace("\r\n", "\n").encode()).hexdigest()[:16]
            if h != SOURCE_SHA[k]:
                bad.append(k)
        except (OSError, TypeError):
            bad.append(k)
    return bad


def check_against_library(FR, bar, starts, W=200):
    """(f0, prom) from the library's own CEN.line_of vs this module's, on the given window starts -> n mismatches."""
    bad = 0
    G2 = FR.GI.G2
    for s in starts:
        a = FR.CEN.line_of(bar[s:s + W], FR.FS)
        b = line_of(G2, bar[s:s + W], FR.FS)
        same = all((x == y) or (np.isnan(x) and np.isnan(y)) for x, y in zip(a, b))
        bad += 0 if same else 1
    return bad
