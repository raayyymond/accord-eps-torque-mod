#!/usr/bin/env python3
"""V61 route `31` -- BAND-EDGE DIAGNOSTIC: where are the peaks actually?

studies/sessions/r31/analyze_r31_grinding.py returns f0 pinned at the 18 Hz band edge in EVERY arm on route 31, with
the sub-bin refinement pushing several windows to 17.9x. That is the signature of a peak that has
moved BELOW the strict band, and a strict-band argmax cannot see it.

🛑 This script deliberately widens the search to 3-46 Hz. That is a DIAGNOSTIC ONLY -- docs/STATE.md
convention 4 (strict 18-26 Hz + presence test) exists because a wide argmax catches the ratchet's
2nd harmonic and manufactures a frequency-vs-speed law. Nothing here is a frequency law; it is a
"where did the line go" check, and every peak is reported with its own prominence and Q so the
reader can see which are modes and which are floor.

Usage:  python studies/sessions/r31/analyze_r31_spectra.py
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

sys.path.insert(0, str(Path(__file__).parents[3]))
from _r31_common import (CACHE_2B, CACHE_2C, NFFT, SEGS_2B, SEGS_2C, SEGS_31,  # noqa: E402
                         avg_spectrum, fs_of, load, q_of, runs_of, periodogram, sustained)

WIDE = (3.0, 46.0)


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def arm_mask(d, arm, vmax=5.0, vmin=0.3, hands=None):
    v = np.abs(d["cs_v"])
    m = (v <= vmax) & (v >= vmin)
    lat = d["cc_lat"] > 0.5
    gear = d.get("cs_gear")
    if arm == "eng_fwd":
        m &= lat & ((gear == 2) if gear is not None else True)
    elif arm == "man_fwd":
        m &= ~lat & ((gear == 2) if gear is not None else True)
    elif arm == "man_rev":
        m &= (gear == 4)
    elif arm == "any_eng":
        m &= lat
    elif arm == "any_man":
        m &= ~lat
    if hands is not None:
        fs = fs_of(d)
        sus = np.full(len(d["t"]), np.inf)
        if m.any():
            sus[m] = sustained(d["tq"][m], fs)
        m &= (sus <= 200) if hands else (sus > 200)
    return m


def pooled(segs, arm, cache=None, pfx="r31s", chan="tq", **kw):
    acc, K, nr, f = None, 0, 0, None
    for s in segs:
        d = load(s, cache, pfx) if cache is not None else load(s)
        m = arm_mask(d, arm, **kw)
        if not m.any():
            continue
        ff, P, k, n = avg_spectrum(d, m, chan=chan)
        if P is None:
            continue
        f = ff
        acc = P * k if acc is None else acc + P * k
        K += k
        nr += n
    return (f, acc / K, K, nr) if K else (None, None, 0, 0)


def peaks(f, P, fmin=WIDE[0], fmax=WIDE[1], halfwin=6.0, exclude=1.5, min_prom=3.0):
    out = []
    df = f[1] - f[0]
    for j in range(1, len(P) - 1):
        if not (fmin <= f[j] <= fmax):
            continue
        if not (P[j] > P[j - 1] and P[j] >= P[j + 1]):
            continue
        near = (np.abs(f - f[j]) <= halfwin) & (np.abs(f - f[j]) > exclude) & (f > 0.3)
        if near.sum() < 5:
            continue
        floor = float(np.median(P[near]))
        prom = P[j] / floor if floor > 0 else np.inf
        if prom < min_prom:
            continue
        y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
        den = y0 - 2 * y1 + y2
        dl = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        out.append((f[j] + np.clip(dl, -.5, .5) * df, prom, q_of(f, P, f[j]), P[j]))
    out.sort(key=lambda r: -r[1])
    return out


def show(tag, f, P, K, nr):
    if P is None:
        print(f"   {tag:38s}  no windows")
        return
    pk = peaks(f, P)
    print(f"   {tag:38s}  K={K:3d} runs={nr:2d}")
    for f0, pr, q, pw in pk[:6]:
        print(f"        {f0:6.2f} Hz   prom {pr:9.1f}x   Q {q:5.1f}   P {pw:.3e}")
    if not pk:
        print("        (no peak above 3x prominence anywhere in 3-46 Hz -- broadband floor)")


def main():
    hdr("S1. WIDE-BAND (3-46 Hz) POOLED SPECTRUM, engaged creep -- V61 vs V59 vs V58")
    print("   The strict 18-26 Hz argmax pins at the 18.0 Hz edge on EVERY route-31 arm. If the")
    print("   line moved below 18 Hz, only a wide search can see it. Diagnostic only.\n")
    for cache, pfx, segs, name in [(None, "r31s", SEGS_31, "V61 r31"),
                                   (CACHE_2C, "r2cs", SEGS_2C, "V59 r2c"),
                                   (CACHE_2B, "r2bs", SEGS_2B, "V58 r2b")]:
        for arm, lbl in [("any_eng", "engaged, |v| 0.3-5"),
                         ("any_man", "manual,  |v| 0.3-5")]:
            f, P, K, nr = pooled(segs, arm, cache=cache, pfx=pfx)
            show(f"{name}  {lbl}", f, P, K, nr)
        print()

    hdr("S2. ROUTE 31 BY ARM, wide band -- forward/reverse/engaged")
    for arm, lbl in [("eng_fwd", "engaged FORWARD"), ("man_fwd", "manual FORWARD"),
                     ("man_rev", "manual REVERSE")]:
        f, P, K, nr = pooled(SEGS_31, arm)
        show(lbl, f, P, K, nr)
    print()
    for arm, lbl in [("eng_fwd", "engaged FORWARD hands-off"),
                     ("man_fwd", "manual FORWARD hands-off"),
                     ("man_rev", "manual REVERSE hands-off")]:
        f, P, K, nr = pooled(SEGS_31, arm, hands=True)
        show(lbl, f, P, K, nr)

    hdr("S3. THE SAME QUESTION AT HIGHER RESOLUTION (nfft=512, 0.196 Hz bins)")
    print("   Confirms the peak frequency is not a 0.39 Hz binning artifact of the 18 Hz edge.\n")
    for arm, lbl in [("eng_fwd", "V61 engaged FORWARD"), ("man_rev", "V61 manual REVERSE"),
                     ("man_fwd", "V61 manual FORWARD")]:
        acc, K, nr, f = None, 0, 0, None
        for s in SEGS_31:
            d = load(s)
            m = arm_mask(d, arm)
            if not m.any():
                continue
            ff, P, k, n = avg_spectrum(d, m, nfft=512)
            if P is None:
                continue
            f, K, nr = ff, K + k, nr + n
            acc = P * k if acc is None else acc + P * k
        show(lbl + " (nfft=512)", f, acc / K if K else None, K, nr)
    for cache, pfx, segs, name in [(CACHE_2C, "r2cs", SEGS_2C, "V59 r2c engaged")]:
        acc, K, nr, f = None, 0, 0, None
        for s in segs:
            d = load(s, cache, pfx)
            m = arm_mask(d, "any_eng")
            if not m.any():
                continue
            ff, P, k, n = avg_spectrum(d, m, nfft=512)
            if P is None:
                continue
            f, K, nr = ff, K + k, nr + n
            acc = P * k if acc is None else acc + P * k
        show(name + " (nfft=512)", f, acc / K if K else None, K, nr)

    hdr("S4. PER-WINDOW ARGMAX over 12-30 Hz -- is the V61 line COHERENT, and where?")
    print("   Per-window (not pooled) so the scatter is meaningful. A mode holds frequency;")
    print("   the argmax of a floor wanders. Reported at prominence cuts.\n")
    for cache, pfx, segs, name in [(None, "r31s", SEGS_31, "V61 r31"),
                                   (CACHE_2C, "r2cs", SEGS_2C, "V59 r2c"),
                                   (CACHE_2B, "r2bs", SEGS_2B, "V58 r2b")]:
        for arm, lbl in [("any_eng", "engaged"), ("any_man", "manual "),
                         ("man_rev", "man REV")]:
            f0s, prs = [], []
            for s in segs:
                d = load(s, cache, pfx) if cache is not None else load(s)
                if arm == "man_rev" and "cs_gear" not in d:
                    continue
                m = arm_mask(d, arm)
                if not m.any():
                    continue
                fs = fs_of(d)
                ff = np.fft.rfftfreq(NFFT, 1 / fs)
                for a, b in runs_of(m, d["t"], NFFT):
                    x = d["tq"][a:b]
                    for i in range(0, len(x) - NFFT + 1, NFFT):
                        P = periodogram(x[i:i + NFFT], fs)
                        if P is None:
                            continue
                        pk = peaks(ff, P, 12.0, 30.0, min_prom=0.0)
                        if pk:
                            f0s.append(pk[0][0]); prs.append(pk[0][1])
            if not f0s:
                continue
            f0s, prs = np.array(f0s), np.array(prs)
            row = f"   {name} {lbl:8s} n={len(f0s):3d}"
            for cut in (5, 10, 50):
                m = prs >= cut
                row += (f" | >{cut}x: n={int(m.sum()):3d} f0 {np.median(f0s[m]):5.2f}"
                        f" sd {f0s[m].std(ddof=1):4.2f}" if m.sum() > 1 else
                        f" | >{cut}x: n={int(m.sum())}")
            print(row)


if __name__ == "__main__":
    main()
