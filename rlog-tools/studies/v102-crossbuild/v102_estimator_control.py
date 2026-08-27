#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_estimator_control.py -- settle Hann-vs-long-FFT with a SYNTHETIC signal of KNOWN band power.

`route-stock` gets Hann/true = 0.912 for STOCK where I got 0.551, and correctly notes that number
was aimed at its headline.  Rather than argue about constructions, both estimators are first run
against signals whose band power is known by construction.  Whichever disagrees with the truth is
the broken one.  THEN the real data is re-run per-run, so no averaging can hide a single bad run.

PART 1  SYNTHETIC.  Four cases at 100 Hz, band 21.5-25.5 Hz, true band power computed analytically:
          A  white noise                       -- broadband, the easy case
          B  white noise + a strong 23.0 Hz line (mid-band)
          C  white noise + a strong 24.7 Hz line (0.8 Hz from the 25.5 edge -- V102's case)
          D  steep 1/f^3 noise, no line        -- STOCK's case: a spectrum falling hard
                                                  through the band, almost no content in it
PART 2  REAL DATA, PER RUN.  No pooling -- the per-run ratios are printed so a single unusual run
        cannot masquerade as a bias.
PART 3  MY OWN CONSTRUCTION, AUDITED.  Re-runs PART 2 with the >=40 s run filter I used vs the
        >=20 s filter route-stock used, and with mean-removal vs linear detrend on the long FFT.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import score_v102_full as F  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LO, HI = 21.5, 25.5
ARMS = [("97", "STOCK 1x"), ("85", "V100 4x"), ("96", "V102 6x"), ("95", "V101 8x")]


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def band_long(x, fs, detrend="mean"):
    """Band power from ONE long FFT over the whole run.  Returns MEAN power in the band."""
    n = len(x)
    if detrend == "linear":
        r = np.arange(n, dtype=float)
        c = np.polyfit(r, x, 1)
        y = x - (c[0] * r + c[1])
    else:
        y = x - x.mean()
    f = np.fft.rfftfreq(n, 1.0 / fs)
    p = (np.abs(np.fft.rfft(y)) ** 2) * 2.0 / (n ** 2)
    return float(p[(f >= LO) & (f < HI)].sum())


def band_hann(x, fs, nw=100):
    """MEAN over 1 s Hann windows of the Parseval-normalised band power."""
    win = np.hanning(nw)
    scale = np.mean(win ** 2)
    ff = np.fft.rfftfreq(nw, 1.0 / fs)
    m = (ff >= LO) & (ff < HI)
    out = []
    for i in range(0, len(x) - nw + 1, nw):
        s = x[i:i + nw]
        r = np.arange(len(s), dtype=float)
        c = np.polyfit(r, s, 1)
        y = (s - (c[0] * r + c[1])) * win
        p = (np.abs(np.fft.rfft(y)) ** 2) * 2.0 / (nw ** 2) / scale
        out.append(float(p[m].sum()))
    return float(np.mean(out)) if out else np.nan


def band_boxcar(x, fs, nw=100):
    """MEAN over 1 s RECTANGULAR windows -- route-stock's 'boxcar long' analogue."""
    ff = np.fft.rfftfreq(nw, 1.0 / fs)
    m = (ff >= LO) & (ff < HI)
    out = []
    for i in range(0, len(x) - nw + 1, nw):
        s = x[i:i + nw]
        y = s - s.mean()
        p = (np.abs(np.fft.rfft(y)) ** 2) * 2.0 / (nw ** 2)
        out.append(float(p[m].sum()))
    return float(np.mean(out)) if out else np.nan


if __name__ == "__main__":
    # ------------------------------------------------------------------ PART 1
    hdr("PART 1 -- SYNTHETIC, band power KNOWN BY CONSTRUCTION.  Which estimator is right?")
    rng = np.random.default_rng(3)
    fs, N = 100.0, 300 * 100
    t = np.arange(N) / fs
    cases = {}
    w = rng.standard_normal(N)
    cases["A white noise"] = (w, (HI - LO) / (fs / 2))          # var 1 spread over 0..50 Hz
    for nm, f0 in (("B line 23.0 Hz (mid-band)", 23.0), ("C line 24.7 Hz (0.8 Hz from edge)", 24.7)):
        amp = 3.0
        x = w + amp * np.sin(2 * np.pi * f0 * t)
        cases[nm] = (x, (HI - LO) / (fs / 2) + amp ** 2 / 2.0)
    # steep 1/f^3, analytic truth by construction in the frequency domain
    fgrid = np.fft.rfftfreq(N, 1.0 / fs)
    shape = 1.0 / np.maximum(fgrid, 0.5) ** 3
    ph = rng.uniform(0, 2 * np.pi, len(fgrid))
    X = shape * np.exp(1j * ph) * N
    X[0] = 0
    d = np.fft.irfft(X, n=N)
    p_true = (np.abs(np.fft.rfft(d - d.mean())) ** 2) * 2.0 / (N ** 2)
    cases["D steep 1/f^3, no line"] = (d, float(p_true[(fgrid >= LO) & (fgrid < HI)].sum()))

    print("  %-34s %12s %12s %10s %12s %10s"
          % ("case", "TRUE", "long FFT", "ratio", "Hann 1 s", "ratio"))
    for nm, (x, truth) in cases.items():
        bl, bh = band_long(x, fs), band_hann(x, fs)
        print("  %-34s %12.5g %12.5g %10.3f %12.5g %10.3f"
              % (nm, truth, bl, bl / truth, bh, bh / truth))
    print("""
  READING: the long FFT is the reference only if its own ratio is ~1.  If BOTH estimators track
  the truth on every synthetic case, then any disagreement on real data is about the DATA
  (run selection, splicing), not about the estimators.""")

    # ------------------------------------------------------------------ PART 2
    hdr("PART 2 -- REAL DATA, PER RUN.  Contiguous engaged runs only; nothing concatenated.")
    for rt, lab in ARMS:
        z = dict(np.load(ROOT / "analysis-2020accord" / F.NPZ[rt], allow_pickle=True))
        tt = np.asarray(z["t"], float)
        fs_ = 1.0 / np.median(np.diff(tt))
        lat = np.asarray(z["cc_lat"], float) > 0.5
        WL = int(round(fs_))
        tq = np.asarray(z["tq"], float)
        print("\n  %s   (FS %.2f Hz)" % (lab, fs_))
        print("      %-8s %8s %12s %12s %10s %12s %10s"
              % ("run", "sec", "long FFT", "Hann 1 s", "H/long", "boxcar 1 s", "H/box"))
        rows = []
        for k, (a, b) in enumerate(F.runs_break(lat, tt, WL)):
            x = tq[a:b]
            if len(x) < 20 * fs_:
                continue
            bl, bh, bb = band_long(x, fs_), band_hann(x, fs_), band_boxcar(x, fs_)
            rows.append((len(x) / fs_, bl, bh, bb))
            print("      %-8d %8.1f %12.5g %12.5g %10.3f %12.5g %10.3f"
                  % (k, len(x) / fs_, bl, bh, bh / bl, bb, bh / bb))
        if rows:
            w_ = np.array([r[0] for r in rows])
            L_ = np.array([r[1] for r in rows])
            H_ = np.array([r[2] for r in rows])
            print("      %-8s %8.1f %12.5g %12.5g %10.3f"
                  % ("POOLED", w_.sum(), np.sum(L_ * w_) / w_.sum(),
                     np.sum(H_ * w_) / w_.sum(),
                     np.sum(H_ * w_) / np.sum(L_ * w_)))

    # ------------------------------------------------------------------ PART 3
    hdr("PART 3 -- AUDIT OF MY OWN CONSTRUCTION.  Does the >=40 s filter or the detrend explain it?")
    print("  %-11s %14s %14s %14s %14s"
          % ("arm", ">=20 s, mean", ">=40 s, mean", ">=20 s, linear", ">=40 s, linear"))
    for rt, lab in ARMS:
        z = dict(np.load(ROOT / "analysis-2020accord" / F.NPZ[rt], allow_pickle=True))
        tt = np.asarray(z["t"], float)
        fs_ = 1.0 / np.median(np.diff(tt))
        lat = np.asarray(z["cc_lat"], float) > 0.5
        WL = int(round(fs_))
        tq = np.asarray(z["tq"], float)
        out = []
        for minlen in (20, 40):
            for det in ("mean", "linear"):
                Lt = Ht = 0.0
                for a, b in F.runs_break(lat, tt, WL):
                    x = tq[a:b]
                    if len(x) < minlen * fs_:
                        continue
                    nw = int(len(x) // fs_)
                    Lt += band_long(x, fs_, det) * nw
                    h = band_hann(x, fs_)
                    if np.isfinite(h):
                        Ht += h * nw
                out.append(Ht / Lt if Lt else np.nan)
        print("  %-11s %14.3f %14.3f %14.3f %14.3f"
              % (lab, out[0], out[2], out[1], out[3]))
