#!/usr/bin/env python3
r"""studies/v95-override/v95_427_aliasing_and_cadence.py -- two instrument questions about the CAN 427 telemetry field.

JOB 1 -- TASK-5 CADENCE, checked against the flown lane instead of the task table.
    `gp-0x6bbe`'s outer EMA has alpha = 205/1024 = 0.2002, so the pole is z = 1 - alpha = 0.7998 and
        f_task = 1000 Hz  ->  tau =  4.5 ms,  -3 dB corner 31.9 Hz
        f_task =  100 Hz  ->  tau = 44.8 ms,  -3 dB corner  3.2 Hz
    A 10x difference, and the corner lands inside the band 427 can see.  `gp-0x6bbe` is already on
    the wire on every V92 flight, so route 79's cache answers it with no drive.
    RESULT 2026-08-12: the measured `gp-0x6bbe <- wheel rate` transfer is -1.2 dB at 7-9 Hz relative
    to 1.5-3 Hz, against -8.4 dB predicted for 100 Hz and -0.3 dB for 1 kHz; and the step profile
    moves 138 % of its final value in one 20 ms sample, against a 36 % cap for tau = 44.8 ms.
    ⇒ the -5.8 / -7.5 / -8.6 dB attenuation figures derived from a 100 Hz task 5 are NOT observable
      in the flown lane.  DO NOT SIZE A BUILD ON THEM.
    🛑 Honest limits, both stated in the output: the visible transfer is `w -> bbe`, which contains
      an unknown upstream path (a differentiator followed by a 3.2 Hz pole would also look flat --
      the PHASE is what separates them, and it RISES where a pole would make it fall); and the step
      selection picks the largest one-sample jumps, though the 36 % cap is a property of the
      transfer rather than of the population.

JOB 2 -- ALIASING.  427 is a naive 50 Hz point-sample with no anti-alias filtering anywhere ahead
    of it.  TWO corrections to the obvious analysis:
      (a) the fold law is `f_alias = |f - 50*round(f/50)|`, NOT `f mod 25`.  26 -> 24, 29 -> 21,
          31 -> 19 Hz.
      (b) 🛑 MORE IMPORTANT: 427 transmits |x|, NOT x.  Rectification maps a line at f to DC AND 2f,
          and the 50 Hz sample folds THAT.  The law for the magnitude field is
          `|2f - 50*round(2f/50)|`:  26 -> 2 Hz,  29 -> 8 Hz,  31 -> 12 Hz.
          ⇒ the car's 26-31 Hz content folds into 2-12 Hz on the magnitude channel -- the band under
            test -- not into 19-24 Hz.
    The test is a coherence, not a spectral eyeball: does the 427 channel's 6-9 Hz content track the
    COLUMN's 26-31 Hz ENVELOPE (the thing that would fold there)?
    RESULT: NEGLIGIBLE for the signed reconstructions (coh^2 0.001-0.003) -- multiplying by the
    100 Hz sign bit re-modulates the folded energy out of the band -- and MATERIAL BUT BOUNDED for
    the raw |427| magnitude channel (coh^2 0.104 at 6-9 Hz on r77's |gp-0x6b26|).
    ⇒ no existing 19-24 Hz claim is invalidated; the exposed statistics are any computed on |427|
      directly rather than on the signed reconstruction.
    ⇒ FOR PROBE DESIGN: on a RECTIFIED field, halving to 25 Hz lands 26/29/31 Hz in the same 2-12 Hz
      zone, so the rate is not what protects you -- the SIGN BIT is.  Ship signed.

Usage:  python studies/v95-override/v95_427_aliasing_and_cadence.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v95_lane_decomposition import rebuild  # noqa: E402
from v95_rez_lib import (BUILD, HOP50, NW50, base, epwins, hdr, load, transfer)  # noqa: E402

RNG = np.random.default_rng(950822)
ALPHA = 205 / 1024
LOW = [("0.3-0.8", .3, .8), ("0.8-1.5", .8, 1.5), ("1.5-3", 1.5, 3), ("3-5", 3, 5), ("5-7", 5, 7),
       ("7-9", 7, 9), ("9-12", 9, 12), ("12-16", 12, 16), ("16-20", 16, 20), ("20-24", 20, 24)]


def job1():
    hdr("JOB 1 -- TASK-5 CADENCE FROM THE FLOWN gp-0x6bbe LANE (route 79, V92)")
    for ft in (1000.0, 100.0):
        tau = -1.0 / (ft * np.log(1 - ALPHA))
        fc = ft * ALPHA / (2 * np.pi)
        print(f"    predicted, task 5 @ {ft:6.0f} Hz: tau = {1000*tau:5.1f} ms, corner {fc:5.1f} Hz,"
              f" attenuation at 6 / 7.79 / 9 Hz = " +
              " / ".join(f"{20*np.log10(1/np.sqrt(1+(f/fc)**2)):+5.1f}" for f in (6, 7.79, 9))
              + " dB")
    S = rebuild("r79")
    W = epwins(S["mask"], S["t"], (S["w"], S["signed"]), nw=NW50, hop=HOP50, max_gap=0.10)
    r = transfer(W, S["fs"], LOW, NW50, RNG)
    ref = r["1.5-3"]["gain"]
    print(f"\n    MEASURED gp-0x6bbe <- wheel rate, {len(W)} windows / "
          f"{len({w[0] for w in W})} episodes, engaged hands-off:")
    print(f"      {'band':9s} {'|H| ct/(rad/s)':>15s} {'dB re 1.5-3 Hz':>15s} {'phase':>8s} "
          f"{'coh2':>6s}")
    for nm, _, _ in LOW:
        d = r[nm]
        print(f"      {nm:9s} {d['gain']:15.1f} {20*np.log10(d['gain']/ref):15.2f} "
              f"{d['phase_deg']:+7.0f}° {d['coh2']:6.3f}"
              f"{'' if d['trust'] else '  (no trust)'}")
    print("      🛑 the PHASE is the discriminator: a pole makes phase FALL.  If it RISES across")
    print("         3-20 Hz, a 3.2 Hz pole would need the upstream path to supply the difference,")
    print("         and between 4 and 8 Hz that is more than one differentiator can give.")

    print("\n    STEP RESPONSE of |gp-0x6bbe| (50 Hz => 20 ms resolution):")
    mag, msk = S["mag"], S["mask"]
    d = np.diff(mag)
    thr = np.percentile(np.abs(d[np.abs(d) > 0]), 99.5)
    idx = np.flatnonzero((np.abs(d) > thr) & msk[:-1])
    idx = idx[(idx > 5) & (idx < len(mag) - 20)]
    prof = []
    for i in idx:
        pre = mag[i - 3:i + 1].mean()
        post = mag[i + 6:i + 16]
        if len(post) < 10 or abs(post.mean() - pre) < thr / 2:
            continue
        prof.append((mag[i:i + 12] - pre) / (post.mean() - pre))
    if len(prof) < 20:
        print(f"      only {len(prof)} usable steps -- NOT SCOREABLE")
        return
    Pm = np.median(np.array(prof), axis=0)
    print(f"      {len(prof)} steps (|delta| > {thr:.0f} ct, 99.5th pct).  Median normalised "
          f"profile, samples 20 ms apart:")
    print("      " + "  ".join(f"{k*20:3d}ms:{v:+5.2f}" for k, v in enumerate(Pm[:8])))
    cap = 1 - np.exp(-20.0 / (-1000.0 / (100.0 * np.log(1 - ALPHA))))
    print(f"      🛑 a first-order system with tau = 44.8 ms can move at most {100*cap:.0f} % of its"
          f" final value in one 20 ms sample.  Measured at 20 ms: {100*Pm[1]:.0f} %.")
    print("      ⚠ the step selection picks the largest one-sample jumps, which favours fast events;"
          " the cap above is a property of the TRANSFER, not of the population, so it survives that.")


def job2():
    hdr("JOB 2 -- 427 ALIASING.  427 carries |x|, so the fold law runs on 2f, not f.")
    for f in (26, 29, 31, 20, 15, 7.8):
        print(f"    column {f:5.1f} Hz -> rectified {2*f:5.1f} Hz -> 427 magnitude bin "
              f"{abs(2*f - 50*round(2*f/50)):5.1f} Hz    "
              f"(un-rectified it would be {abs(f - 50*round(f/50)):4.1f} Hz)")
    print("\n    TEST: coherence of the 427 channel against the COLUMN's 26-31 Hz ENVELOPE -- the")
    print("    signal that would fold into 2-12 Hz.  Run on the SIGNED reconstruction and on the")
    print("    RAW MAGNITUDE separately, because only the raw magnitude is exposed.")
    print(f"\n    {'route':6s} {'channel':22s} " +
          "  ".join(f"{k:>18s}" for k in ("2-4", "6-9", "9-12")))
    for route in ("r79", "r77", "r78"):
        z = load(route)
        B = base(z)
        S = rebuild(route)
        x = B["tq"] - B["tq"].mean()
        F = np.fft.rfft(x)
        fr = np.fft.rfftfreq(len(x), 1 / B["fs"])
        F[(fr < 26) | (fr > 31)] = 0
        env = np.interp(S["t"], B["t"], np.abs(np.fft.irfft(F, len(x))))
        W = epwins(S["mask"], S["t"], (env, S["signed"], S["mag"]),
                   nw=NW50, hop=HOP50, max_gap=0.10)
        if len(W) < 8:
            print(f"    {route:6s} too few windows")
            continue
        bands = [("2-4", 2, 4), ("6-9", 6, 9), ("9-12", 9, 12)]
        for lbl, yi in (("signed reconstruction", 1), ("raw |427| magnitude", 2)):
            r = transfer(W, S["fs"], bands, NW50, np.random.default_rng(5), xi=0, yi=yi)
            print(f"    {route:6s} {lbl:22s} " + "  ".join(
                f"coh2 {r[k]['coh2']:.3f} (shuf {r[k]['coh2_shuf']:.3f})" for k, _, _ in bands))
    print("\n    READ: coh2 << 0.05 => the fold is negligible for that channel.  A material coh2 on")
    print("    the RAW magnitude with a clean SIGNED reconstruction is the expected pattern: the")
    print("    100 Hz sign bit re-modulates the folded energy out of the band.")


if __name__ == "__main__":
    job1()
    job2()
