#!/usr/bin/env python3
"""Shared conventions for the V61 route-`31` analysis. Import this; do not re-implement.

Every convention here is from docs/STATE.md "METHODOLOGY" and was established the hard way on the
V57/V58/V59 drives. Re-deriving them by hand is how earlier passes produced wrong answers.

  1. ENGAGEMENT is LATERAL -- carControl.latActive, corroborated by 0x18F byte4 bit3 (sca).
     NEVER carState.cruiseState.enabled (longitudinal+lateral; reads 0.00% on parking-lot routes).
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200. The
     oscillation is +/-1400 counts on the torsion-bar channel itself, so a raw test selects
     AGAINST the phenomenon.
  3. PROMINENCE and p99 ENVELOPE, never mean Welch power -- the mode is bursty.
  4. STRICT 18-26 Hz. A wider band catches the ratchet's 2nd harmonic (2x8.0-8.9 = 16-17.8 Hz)
     and manufactures a fake frequency-vs-speed slope.
  5. Never splice disjoint runs into one FFT. Average periodograms across DISJOINT runs.
  6. STEER_STATUS is 0x18F byte4 bits 7:4 (`sstat`), not bits 2:0 (`slow3`, spare, always 0).

Cache schema: see extract_r31_cache.py. Key additions over route 2c: cs_gear (car.capnp
GearShifter ORDINAL, 4 == reverse, held-last) and cs_std (standstill).
"""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "_cache_r31"
CACHE_2C = ROOT / "_cache_r2c"
CACHE_2B = ROOT / "_cache_r2b"   # relocated into the repo 2026-07-31; it previously hard-coded a
                                 # per-session scratchpad path, which does not survive the session.

SEGS_31 = [0, 1, 2, 3]
SEGS_2C = [0, 1, 3, 4, 8, 9, 10, 11, 12]
SEGS_2B = [0, 1, 2, 11, 12, 13]

BAND = (18.0, 26.0)     # The strict grinding band -- correct for V58/V59.
# 🛑 NOT VALID FOR V61+. V61 moved the mode to ~18.3 Hz engaged / ~17.1 Hz manual, so a strict-band
# argmax PINS TO THE 18.0 EDGE (sd 0.00) and silently reports the boundary as the peak. A strict band
# PRESENCE-TESTS a mode whose frequency you already know; it cannot LOCATE one that has shifted.
# Locate with a free 12-30 Hz argmax, then presence-test in a tracking band (that build's f0 +/- 1.5 Hz).
RATCHET = (6.0, 9.0)    # the strict ratchet band
NFFT = 256              # 2.56 s @ ~100 Hz, 0.3915 Hz bins -- the kit's standard
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
REVERSE, DRIVE, PARK = 4.0, 2.0, 1.0


def load(seg, cache=CACHE, pfx="r31s"):
    return {k: v for k, v in np.load(cache / f"{pfx}{seg}.npz").items()}


def fs_of(d):
    return 1.0 / np.median(np.diff(d["t"]))


def sustained(x, fs, fc=3.0):
    """The driver's actual push with the oscillation removed. Compute over the SUBSET analysed.

    NaN-fragile by construction (one NaN in, all NaN out) -- the input is guarded here.
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


def band_envelope(x, fs, lo=BAND[0], hi=BAND[1]):
    """Analytic-signal magnitude restricted to [lo,hi] Hz -- the burst envelope.

    This is the AMPLITUDE A of the band-limited component, so peak-to-peak is 2*A.
    """
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(x)))


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


def periodogram(seg, fs, nfft=NFFT, detrend=True):
    """Hann-windowed power for one nfft block. Detrend removes the DC + drift of a manoeuvre."""
    seg = np.asarray(seg, float)
    if len(seg) != nfft or not np.all(np.isfinite(seg)):
        return None
    if detrend:
        r = np.arange(nfft)
        c = np.polyfit(r, seg, 1)
        seg = seg - (c[0] * r + c[1])
    else:
        seg = seg - seg.mean()
    return np.abs(np.fft.rfft(seg * np.hanning(nfft))) ** 2


def peak_prom(f, P, lo=BAND[0], hi=BAND[1], halfwin=6.0, exclude=1.5):
    """(f0, prominence) for the strongest bin in [lo,hi].

    floor(f0) = median of P over |f-f0| <= halfwin excluding |f-f0| <= exclude -- a LOCAL floor,
    which is what separates a mode from broadband. Sub-bin refined parabolically in log power.
    Returns (nan, nan) if the band has no interior local maximum.
    """
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan
    j = int(np.argmax(np.where(m, P, -np.inf)))
    if j <= 0 or j >= len(P) - 1:
        return float(f[j]), np.nan
    near = (np.abs(f - f[j]) <= halfwin) & (np.abs(f - f[j]) > exclude) & (f > 0.3)
    if near.sum() < 5:
        return float(f[j]), np.nan
    floor = float(np.median(P[near]))
    prom = P[j] / floor if floor > 0 else np.inf
    y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
    den = y0 - 2 * y1 + y2
    delta = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    f0 = f[j] + np.clip(delta, -0.5, 0.5) * (f[1] - f[0])
    return float(f0), float(prom)


def q_of(f, P, j_f0, lo=BAND[0], hi=BAND[1]):
    """-3 dB Q of the peak nearest j_f0. Hann main lobe caps measurable Q at f0/(1.44*fs/nfft)."""
    j = int(np.argmin(np.abs(f - j_f0)))
    half = P[j] / 2.0
    a = j
    while a > 1 and P[a] > half and P[a - 1] < P[a]:
        a -= 1
    b = j
    while b < len(P) - 2 and P[b] > half and P[b + 1] < P[b]:
        b += 1
    bw = max(f[b] - f[a], f[1] - f[0])
    return float(f[j] / bw)


def windows(d, mask, nfft=NFFT, chan="tq", band=BAND, detrend=True):
    """Per-window (f0, prominence, envelope p99, mean |v|, mean |ang|, effort, t0) records.

    Windows are taken ONLY inside contiguous runs of `mask` (convention 5: no splicing).
    """
    fs = fs_of(d)
    out = []
    for a, b in runs_of(mask, d["t"], nfft):
        x = d[chan][a:b]
        env = band_envelope(x, fs, *band)
        for i in range(0, len(x) - nfft + 1, nfft):
            P = periodogram(x[i:i + nfft], fs, nfft, detrend)
            if P is None:
                continue
            f = np.fft.rfftfreq(nfft, 1 / fs)
            f0, pr = peak_prom(f, P, *band)
            sl = slice(a + i, a + i + nfft)
            out.append(dict(f0=f0, prom=pr, Q=q_of(f, P, f0) if np.isfinite(f0) else np.nan,
                            envp99=float(np.percentile(env[i:i + nfft], 99)),
                            envmed=float(np.median(env[i:i + nfft])),
                            v=float(np.mean(np.abs(d["cs_v"][sl]))),
                            ang=float(np.mean(np.abs(d["ang"][sl]))),
                            eff=float(np.mean(np.abs(sustained(d["tq"][sl], fs)))),
                            e4=float(np.mean(np.abs(d["e4tq"][sl]))),
                            t0=float(d["t"][a + i]), run=(a, b)))
    return out


def avg_spectrum(d, mask, nfft=NFFT, chan="tq", detrend=True):
    """(f, mean P, K, nruns) averaged over DISJOINT runs -- never a concatenation."""
    fs = fs_of(d)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    acc, K, nr = np.zeros(len(f)), 0, 0
    for a, b in runs_of(mask, d["t"], nfft):
        nr += 1
        x = d[chan][a:b]
        for i in range(0, len(x) - nfft + 1, nfft):
            P = periodogram(x[i:i + nfft], fs, nfft, detrend)
            if P is not None:
                acc += P
                K += 1
    return (f, acc / K, K, nr) if K else (f, None, 0, nr)


def stat(vals, name="", pcts=(50, 90, 99)):
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    if not len(v):
        return f"{name} n=0"
    ps = "  ".join(f"p{p}={np.percentile(v, p):.4g}" for p in pcts)
    return f"{name} n={len(v)}  {ps}  max={v.max():.4g}  sd={v.std(ddof=1) if len(v) > 1 else 0:.4g}"
