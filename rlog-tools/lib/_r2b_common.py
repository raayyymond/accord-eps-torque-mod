#!/usr/bin/env python3
"""Shared conventions for the V58 route-`2b` analysis. Import this; do not re-implement.

All three conventions below were established the hard way on the V57 drive (see docs/STATE.md
"METHODOLOGY"). Re-deriving them by hand is how earlier passes produced wrong answers.

CACHE SCHEMA (npz per segment, key `r2bs<N>`), sampled on 0x14A src1 arrivals at ~100 Hz:
    t        s, segment-relative      ang      STEER_ANGLE deg (0x14A b0:2 * -0.1)
    tq       torsion bar counts       rate_c   coarse rate deg/s (0x14A b2:4 * -1.0)
    rate_f   fine rate deg/s          wang     wheel angle deg
    probe    0x14A byte4 = V58 field  sca      STEER_CONTROL_ACTIVE (0x18F b4 bit3)
    sstat    STEER_STATUS (b4 7:4)    slow3    0x18F b4 bits 2:0 (SPARE, always 0)
    e4tq     openpilot LKAS command   e4req    STEER_TORQUE_REQUEST
    cs_v     vEgo m/s                 cs_ang cs_tq cs_press cs_eng (cruiseState: WRONG proxy)
    cc_lat   carControl.latActive     cc_en cc_req

V58 PROBE BITS in `probe`:
    0x80 liveness (must be 1) | 0x40 gp-0x6bbe < 0 | 0x20 gp-0x6bbe == +512
    0x10 gp-0x6b9a < 0        | 0x08 gp-0x6b9a == 0 | bits 2:0 stock, always 0b111
    field = (probe >> 3) & 0x1F;  field == 0 => cave did not fire => VOID, not "all false".
"""
from pathlib import Path

import numpy as np

CACHE = Path(r"C:\Users\dudei\AppData\Local\Temp\claude"
             r"\C--Users-dudei-Desktop-Projects-accord-eps-torque-mod"
             r"\fbc99f2a-ffd4-4e1a-bd09-899edf1b96ed\scratchpad")

BIT_LIVE, BIT_SIGN, BIT_RAIL, BIT_GSIGN, BIT_GZERO = 0x80, 0x40, 0x20, 0x10, 0x08

# Windows located by 0.5 s band-envelope scan over 18-26 Hz on the torsion bar.
# The route's engagement structure: seg0 parked; seg1 t<13 manual pull-out; LKAS engages
# seg1 t~15 and holds through seg12 t~50; seg12 t>51 and all of seg13 are manual parking.
CREEP_ENGAGED = [(1, 15.0, 34.0), (2, 0.0, 5.0), (11, 23.0, 34.0), (12, 41.0, 50.0)]
CREEP_MANUAL = [(1, 6.0, 13.5), (12, 51.0, 60.0), (13, 0.0, 60.0)]
ROAD_ENGAGED = [(11, 39.0, 58.0), (12, 19.0, 34.0)]
PARKED = [(0, 0.0, 61.0)]


def load(seg):
    return {k: v for k, v in np.load(CACHE / f"r2bs{seg}.npz").items()}


def fs_of(d):
    return 1.0 / np.median(np.diff(d["t"]))


def sustained(x, fs, fc=3.0):
    """Driver's actual push with the oscillation removed. NaN-fragile: guard the input.

    Compute over the SUBSET you intend to analyse -- the filter is global, so a route-wide
    call folds parking manoeuvres into a burst's baseline.
    """
    x = np.asarray(x, float)
    bad = ~np.isfinite(x)
    if bad.all():
        return np.full_like(x, np.inf)
    if bad.any():
        good = ~bad
        x = x.copy()
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(good), x[good])
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    return np.abs(np.fft.irfft(X, n=len(x)) + x.mean())


def band_envelope(x, fs, lo, hi):
    """Analytic-signal magnitude restricted to [lo,hi] Hz -- the burst envelope.

    Use p99/max of this, NOT mean Welch power: the mode is bursty, and the median is dominated
    by quiet time between bursts (that is exactly how V57's "halving" artifact was manufactured).
    """
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(x)))


def csd(x, y, fs, nfft=256):
    """Non-overlapping Hann segments so the returned K is the TRUE dof."""
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    Pxy = np.zeros(len(f), complex); Pxx = np.zeros(len(f)); Pyy = np.zeros(len(f)); K = 0
    for i in range(0, len(x) - nfft + 1, nfft):
        X = np.fft.rfft((x[i:i + nfft] - x[i:i + nfft].mean()) * win)
        Y = np.fft.rfft((y[i:i + nfft] - y[i:i + nfft].mean()) * win)
        Pxy += X * np.conj(Y); Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; K += 1
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
    return f, coh, np.degrees(np.angle(Pxy)), K


def runs_of(mask, t, min_n):
    """Contiguous runs of `mask` with no sample gap > 50 ms, at least min_n long."""
    idx = np.where(mask)[0]
    if not len(idx):
        return
    s = prev = idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                yield s, prev + 1
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        yield s, prev + 1


def gather(windows, vmin=None, vmax=None, hands_off=None, engaged=None):
    """Concatenate windows into one dict of channels, applying the standard masks per segment.

    engaged: True -> sca==1, False -> sca!=1, None -> no filter.
    hands_off: True -> sustained(tq) <= 200 (computed PER WINDOW, per convention 2).
    Returns dict of arrays plus 'seg' and 'win' provenance, and 'edges' listing run boundaries
    so callers can avoid splicing artifacts across joins.
    """
    out, edges, n = {}, [], 0
    keys = ["t", "ang", "rate_c", "rate_f", "wang", "probe", "tq", "sca", "sstat",
            "e4tq", "e4req", "cs_v", "cs_ang", "cs_tq", "cs_press", "cc_lat", "cc_req"]
    acc = {k: [] for k in keys}
    acc["seg"] = []; acc["win"] = []
    for wi, (seg, t0, t1) in enumerate(windows):
        d = load(seg)
        fs = fs_of(d)
        m = (d["t"] >= t0) & (d["t"] < t1)
        if vmin is not None:
            m &= d["cs_v"] >= vmin
        if vmax is not None:
            m &= d["cs_v"] <= vmax
        if engaged is not None:
            m &= (d["sca"] == 1) if engaged else (d["sca"] != 1)
        if hands_off is not None:
            sel = (d["t"] >= t0) & (d["t"] < t1)
            sus = np.full(len(d["t"]), np.inf)
            sus[sel] = sustained(d["tq"][sel], fs)
            m &= (sus <= 200) if hands_off else (sus > 200)
        if not m.any():
            continue
        for k in keys:
            acc[k].append(d[k][m])
        acc["seg"].append(np.full(m.sum(), seg))
        acc["win"].append(np.full(m.sum(), wi))
        edges.append((n, n + m.sum()))
        n += m.sum()
    if n == 0:
        return None
    for k in acc:
        out[k] = np.concatenate(acc[k])
    out["edges"] = edges
    out["n"] = n
    return out
