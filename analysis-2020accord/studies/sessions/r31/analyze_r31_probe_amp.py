#!/usr/bin/env python3
"""V61 route `31` -- QUESTION F (the V59 boost-index probe) and QUESTION G (bar amplitude),
plus the strict ratchet-band check for QUESTION E.

F. V61 carries V59's probe unchanged. It reads gp-0x6ba6, UPSTREAM of V61's edit, so the edit
   cannot move it directly -- but a louder torsion bar drives the index harder, so it is a
   SECONDARY READOUT. Compared against route 2c (V59) with the SAME decode, and effort-matched,
   because route 2c's disengaged sections were quiet parking-lot cruising while route 31's are a
   driver cranking a wheel: an unmatched disengaged comparison measures the driver, not the build.

G. The 18-26 Hz band is the wrong window for V61: its line is at 18.26 Hz, ON the band edge, so
   a strict-band envelope loses part of the peak. Amplitude is therefore also reported in a
   16.8-19.8 Hz mode-tracking band. Peak-to-peak = 2 * analytic envelope amplitude.

E. Ratchet: a strict 6-9 Hz band clips too, because V61's ratchet peak sits at 6.4-6.6 Hz. A free
   5-11 Hz argmax with a presence test is used to see whether it MOVED, reported alongside.

Usage:  python studies/sessions/r31/analyze_r31_probe_amp.py
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
from _r31_common import (CACHE_2C, NFFT, SEGS_2C, SEGS_31, band_envelope, fs_of,  # noqa: E402
                         load, periodogram, runs_of, sustained)
from analyze_r31_spectra import peaks  # noqa: E402

TRACK_31 = (16.76, 19.76)      # 18.26 +/- 1.5
TRACK_2C = (19.43, 22.43)      # 20.93 +/- 1.5


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def masks(d):
    v = np.abs(d["cs_v"])
    fs = fs_of(d)
    sus = sustained(d["tq"], fs)
    return dict(v=v, lat=d["cc_lat"] > 0.5, sus=sus, fs=fs)


def depth_row(tag, d, sel):
    if sel.sum() == 0:
        print(f"   {tag:46s} n=0")
        return
    lvl = d["lvl"][sel]
    print(f"   {tag:46s} n={int(sel.sum()):6d}  "
          f"<512 {100*(lvl==0).mean():6.2f}%  512-1k {100*(lvl==1).mean():6.2f}%  "
          f"1k-2k {100*(lvl==2).mean():6.2f}%  >=2048 {100*(lvl==3).mean():6.2f}%   "
          f"mean lvl {lvl.mean():.3f}")


def pooled_depth(segs, selfn, cache=None, pfx="r31s", tag=""):
    lv, tg, tt = [], [], []
    for s in segs:
        d = load(s, cache, pfx) if cache is not None else load(s)
        m = masks(d)
        sel = selfn(d, m)
        if not sel.any():
            continue
        lv.append(d["lvl"][sel])
        # toggle rate of bit5 (index crossing 512) over contiguous runs only
        for a, b in runs_of(sel, d["t"], 25):
            x = d["lt512"][a:b]
            tg.append(int(np.abs(np.diff(x)).sum()))
            tt.append((b - a) / m["fs"])
    if not lv:
        print(f"   {tag:46s} n=0")
        return
    lvl = np.concatenate(lv)
    rate = sum(tg) / sum(tt) if sum(tt) > 0 else np.nan
    print(f"   {tag:46s} n={len(lvl):6d}  "
          f"<512 {100*(lvl==0).mean():6.2f}%  512-1k {100*(lvl==1).mean():6.2f}%  "
          f"1k-2k {100*(lvl==2).mean():6.2f}%  >=2048 {100*(lvl==3).mean():6.2f}%   "
          f"bit5 toggles {rate:6.2f}/s over {sum(tt):5.1f}s")


def main():
    hdr("F. THE V59 BOOST-INDEX PROBE on V61 -- health, then depth, matched against route 2c")
    print("   Health was verified by rlog-tools/probe/decode_v59_boostindex.py on the raw rlogs:")
    print("   field==0 in 0/22,055 frames, bit7 set in 22,055/22,055, non-monotonic 0/22,055")
    print("   (0.000%), fault sentinel bit6 0/22,055 (0.000%), stock low bits &0x07 == 0b111 in")
    print("   100.00% of frames in every segment. The probe is fully healthy.\n")

    print("   -- depth, the conditions the V59 record quotes --")
    for segs, cache, pfx, name in [(SEGS_31, None, "r31s", "V61 r31"),
                                   (SEGS_2C, CACHE_2C, "r2cs", "V59 r2c")]:
        pooled_depth(segs, lambda d, m: m["lat"] & (m["v"] <= 5) & (m["sus"] <= 200),
                     cache, pfx, f"{name}  engaged + creep + HANDS-OFF")
        pooled_depth(segs, lambda d, m: m["lat"] & (m["v"] <= 5) & (m["sus"] > 200),
                     cache, pfx, f"{name}  engaged + creep + hands-ON")
        pooled_depth(segs, lambda d, m: ~m["lat"] & (m["v"] <= 5),
                     cache, pfx, f"{name}  DISENGAGED + creep (all effort)")
        print()

    print("   -- EFFORT-MATCHED disengaged: this is the fair comparison --")
    print("      route 2c's disengaged time is quiet cruising; route 31's is a driver cranking a")
    print("      wheel in a parking lot. Unmatched, the contrast measures the driver.")
    for lo, hi in [(0, 500), (500, 1000), (1000, 2000), (2000, 9999)]:
        for segs, cache, pfx, name in [(SEGS_31, None, "r31s", "V61 r31"),
                                       (SEGS_2C, CACHE_2C, "r2cs", "V59 r2c")]:
            pooled_depth(segs,
                         lambda d, m, lo=lo, hi=hi: (~m["lat"] & (m["v"] <= 5)
                                                     & (m["sus"] >= lo) & (m["sus"] < hi)),
                         cache, pfx, f"{name}  disengaged, effort {lo}-{hi}")
        print()

    hdr("G. TORSION-BAR OSCILLATION AMPLITUDE -- peak-to-peak counts of the mode component")
    print("   A = analytic envelope amplitude of the band-limited signal; peak-to-peak = 2A.")
    print("   Reported in BOTH the strict 18-26 Hz band and each build's mode-tracking band,")
    print("   because V61's 18.26 Hz line sits on the strict band's lower edge.\n")
    print(f"   {'arm':44s} {'n':>7s} {'A med':>8s} {'A p90':>8s} {'A p99':>8s} "
          f"{'pp med':>8s} {'pp p90':>8s} {'pp p99':>8s} {'pp max':>8s}")
    rows = [
        ("V61 r31 engaged creep, any hands", SEGS_31, None, "r31s", TRACK_31,
         lambda d, m: m["lat"] & (m["v"] <= 5)),
        ("V61 r31 engaged creep, HANDS-OFF", SEGS_31, None, "r31s", TRACK_31,
         lambda d, m: m["lat"] & (m["v"] <= 5) & (m["sus"] <= 200)),
        ("V61 r31 manual, stationary, eff>=1000", SEGS_31, None, "r31s", TRACK_31,
         lambda d, m: ~m["lat"] & (m["v"] <= 0.6) & (m["sus"] >= 1000)),
        ("V61 r31 manual REVERSE (all speeds)", SEGS_31, None, "r31s", TRACK_31,
         lambda d, m: (d["cs_gear"] == 4)),
        ("V59 r2c engaged creep, any hands", SEGS_2C, CACHE_2C, "r2cs", TRACK_2C,
         lambda d, m: m["lat"] & (m["v"] <= 5)),
        ("V59 r2c engaged creep, HANDS-OFF", SEGS_2C, CACHE_2C, "r2cs", TRACK_2C,
         lambda d, m: m["lat"] & (m["v"] <= 5) & (m["sus"] <= 200)),
    ]
    for lbl, segs, cache, pfx, track, selfn in rows:
        for band, bl in [((18.0, 26.0), "strict"), (track, "track ")]:
            env = []
            for s in segs:
                d = load(s, cache, pfx) if cache is not None else load(s)
                m = masks(d)
                sel = selfn(d, m)
                for a, b in runs_of(sel, d["t"], NFFT):
                    env.append(band_envelope(d["tq"][a:b], m["fs"], *band))
            if not env:
                print(f"   {lbl + ' [' + bl + ']':44s} n=0")
                continue
            e = np.concatenate(env)
            print(f"   {lbl + ' [' + bl + ']':44s} {len(e):7d} "
                  f"{np.median(e):8.1f} {np.percentile(e,90):8.1f} {np.percentile(e,99):8.1f} "
                  f"{2*np.median(e):8.1f} {2*np.percentile(e,90):8.1f} "
                  f"{2*np.percentile(e,99):8.1f} {2*e.max():8.1f}")
        print()

    hdr("E-ratchet. FREE 5-11 Hz ARGMAX with a presence test -- did the ratchet move?")
    print("   A strict 6-9 Hz band clips V61's peak the same way 18-26 Hz clips the grinding.\n")
    print(f"   {'arm':40s} {'n':>4s} {'prom med':>9s} {'max':>9s} {'f0 med':>7s} "
          f"{'sd(prom>=10)':>13s} {'n>=10x':>7s}")
    ratchet_rows = [
        ("V61 r31 engaged creep", SEGS_31, None, "r31s", lambda d, m: m["lat"] & (m["v"] <= 5)),
        ("V61 r31 manual creep", SEGS_31, None, "r31s",
         lambda d, m: ~m["lat"] & (m["v"] <= 5) & (m["v"] >= 0.3)),
        ("V61 r31 manual REVERSE", SEGS_31, None, "r31s", lambda d, m: d["cs_gear"] == 4),
        ("V59 r2c engaged creep", SEGS_2C, CACHE_2C, "r2cs", lambda d, m: m["lat"] & (m["v"] <= 5)),
        ("V59 r2c manual creep", SEGS_2C, CACHE_2C, "r2cs",
         lambda d, m: ~m["lat"] & (m["v"] <= 5) & (m["v"] >= 0.3)),
    ]
    for lbl, segs, cache, pfx, selfn in ratchet_rows:
        f0s, prs = [], []
        for s in segs:
            d = load(s, cache, pfx) if cache is not None else load(s)
            m = masks(d)
            sel = selfn(d, m)
            f = np.fft.rfftfreq(NFFT, 1 / m["fs"])
            for a, b in runs_of(sel, d["t"], NFFT):
                x = d["tq"][a:b]
                for i in range(0, len(x) - NFFT + 1, NFFT):
                    P = periodogram(x[i:i + NFFT], m["fs"])
                    if P is None:
                        continue
                    pk = peaks(f, P, 5.0, 11.0, min_prom=0.0)
                    if pk:
                        f0s.append(pk[0][0]); prs.append(pk[0][1])
        if not f0s:
            print(f"   {lbl:40s} n=0")
            continue
        f0s, prs = np.array(f0s), np.array(prs)
        t = f0s[prs >= 10]
        print(f"   {lbl:40s} {len(f0s):4d} {np.median(prs):9.1f} {prs.max():9.1f} "
              f"{np.median(f0s):7.2f} {t.std(ddof=1) if len(t)>1 else 0:13.2f} {len(t):7d}"
              + (f"   f0(prom>=10x) = {np.median(t):.2f} Hz" if len(t) else ""))


if __name__ == "__main__":
    main()
