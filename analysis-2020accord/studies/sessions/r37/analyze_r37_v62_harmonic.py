#!/usr/bin/env python3
"""V62 route `37` -- is the residual ~21.6 Hz line the GRINDING MODE, or the ratchet's 3rd harmonic?

The supplement (studies/sessions/r37/analyze_r37_v62_ratchet.py R3) turned up a pattern that changes the reading of the
headline. In route 37's loudest engaged-creep windows the 12-30 Hz argmax sits at almost exactly
3x the 6-9 Hz argmax:

    seg13 t=25.60   7.17 Hz -> 21.53 Hz   (3.003x)      seg1  t=30.05   7.16 -> 21.52  (3.006x)
    seg13 t=15.36   7.28 Hz -> 21.76 Hz   (2.989x)      seg12 t=52.94   7.37 -> 21.96  (2.980x)
    seg13 t=30.72   7.03 Hz -> 20.92 Hz   (2.976x)      seg13 t=0.00    7.23 -> 14.50  (2.005x)

and the 6-9 Hz fundamental is 20-40x STRONGER than the 12-30 Hz peak in those windows -- the right
way round for a harmonic (the kit's standing trap is the opposite case: a "harmonic" stronger than
its own fundamental is not a harmonic).

If the residual 21.6 Hz energy on V62 is harmonic distortion of a large 7.2 Hz ratchet, then the
21 Hz grinding MODE is not merely quieter on V62 -- it is absent, and the headline's tracking-band
numbers OVERSTATE what is left of it.

FOUR TESTS, each of which the grinding-mode hypothesis and the harmonic hypothesis answer differently:

  H1  ratio f(12-30)/f(6-9) per window. Harmonic => tight cluster at 2.00 or 3.00. Independent
      modes => a broad ratio distribution that tracks whatever the two frequencies happen to be.
  H2  RATCHET-QUIET windows only (6-9 Hz prominence < 10x). A real independent mode survives the
      split; a harmonic cannot exist without its fundamental. This is the decisive one.
  H3  harmonic-NOTCHED search: blank +/-0.75 Hz around 2*f_r and 3*f_r, then re-locate in 12-30 Hz.
  H4  speed-matched ratchet, since route 37 spends far more of its engaged time at 1-2 m/s than
      route 2c does, and the ratchet is a low-speed phenomenon.

V59 route 2c is the control throughout: its 21 Hz line is a measured Q~13.6 resonance, so it MUST
pass H2. If it does not, the test is broken rather than the finding.
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import peak_prom  # noqa: E402
from analyze_r37_v62_creep import (GRIND, HALF, ORDER, PRESENCE, RATCH,  # noqa: E402
                                   bandpower, col, hdr, msd, nrun, pooled_f0, track_prom, wrecs)
from analyze_r37_v62_ratchet import LOT_37, ROAD_37  # noqa: E402

BINS = [(1.0, 2.0), (2.0, 3.0), (3.0, 4.0)]


def notched_peak(rec, halfwidth=0.75, harmonics=(2, 3)):
    """Strongest 12-30 Hz bin after blanking +/-halfwidth Hz around each harmonic of f_r."""
    f, P = rec["f"], rec["P"].copy()
    fr = rec["fr"]
    if np.isfinite(fr):
        for h in harmonics:
            P[np.abs(f - h * fr) <= halfwidth] = np.nan
    good = np.isfinite(P)
    if not good.all():
        # fill the notch with the local floor so peak_prom's median floor is not disturbed
        near = (f >= GRIND[0] - 6) & (f <= GRIND[1] + 6) & good
        P[~good] = np.median(P[near]) if near.any() else 0.0
        P = np.where(np.isfinite(P), P, 0.0)
        # mask the notched bins out of the argmax by construction: they now sit at the floor
    return peak_prom(f, P, *GRIND)


def h1_ratio():
    hdr("H1.  RATIO f(12-30 Hz) / f(6-9 Hz), per window -- harmonic locking vs two free modes")
    print("   Restricted to windows where BOTH bands have a peak of prominence >= 10x, so the ratio")
    print("   is between two real lines rather than two argmaxes of a floor.\n")
    print(f"   {'build':14s} {'win':>4s} {'ratio med':>10s} {'sd':>6s} {'p10':>7s} {'p90':>7s} "
          f"{'|r-3| < 0.05':>13s} {'|r-2| < 0.05':>13s}")
    for lbl, r in pools().items():
        pg, pr = col(r, "prom"), col(r, "promr")
        ok = np.isfinite(pg) & np.isfinite(pr) & (pg >= PRESENCE) & (pr >= PRESENCE)
        if ok.sum() < 2:
            print(f"   {lbl:14s} {int(ok.sum()):4d}  -- too few")
            continue
        rt = col(r, "f0")[ok] / col(r, "fr")[ok]
        print(f"   {lbl:14s} {len(rt):4d} {np.median(rt):10.3f} {rt.std(ddof=1):6.3f} "
              f"{np.percentile(rt, 10):7.3f} {np.percentile(rt, 90):7.3f} "
              f"{100 * np.mean(np.abs(rt - 3) < 0.05):12.0f}% "
              f"{100 * np.mean(np.abs(rt - 2) < 0.05):12.0f}%")
    print("\n   (a 3.000 +/- 0.03 cluster is harmonic locking; two independent modes have no reason")
    print("    to land on an integer, and V59's own pooled peaks give 21.27 / 7.48 = 2.84)")


def h2_quiet():
    hdr("H2.  RATCHET-QUIET WINDOWS ONLY -- the decisive test. A mode survives; a harmonic cannot.")
    print("   Split each build's engaged-creep windows on their OWN 6-9 Hz prominence and re-report")
    print("   the 12-30 Hz line in each half. V59's 21 Hz line is a measured Q~13.6 resonance and")
    print("   MUST survive the quiet half; if it does not, the test is broken, not the finding.\n")
    f0b = {b: pooled_f0(wrecs(b))[0] for b in ORDER}
    f0b["V62 commute"] = f0b["V62 r37"]
    f0b["V62 lot"] = f0b["V62 r37"]
    print(f"   {'build':14s} {'half':16s} {'win':>4s} {'f0 med':>7s} {'sd':>5s} {'promFREE':>9s} "
          f"{'promTRK':>8s} {'pres%':>6s} {'P(trk)':>10s} {'P(18-26)':>10s} {'P(6-9)':>10s}")
    for lbl, r in pools().items():
        pr = col(r, "promr")
        for hname, sel in (("ratchet LOUD >=100x", np.isfinite(pr) & (pr >= 100)),
                           ("ratchet mid 10-100x", np.isfinite(pr) & (pr >= 10) & (pr < 100)),
                           ("ratchet QUIET <10x", ~(np.isfinite(pr) & (pr >= 10)))):
            s = [x for x, k in zip(r, sel) if k]
            if not s:
                print(f"   {lbl:14s} {hname:16s}    0")
                continue
            f0 = f0b[lbl]
            f0m, f0s = msd(col(s, "f0"))
            pf, pt = col(s, "prom"), track_prom(s, f0)
            ok = np.isfinite(pt)
            print(f"   {lbl:14s} {hname:16s} {len(s):4d} {f0m:7.2f} {f0s:5.2f} "
                  f"{np.nanmedian(pf):9.1f} {np.nanmedian(pt):8.1f} "
                  f"{100 * np.mean(pt[ok] >= PRESENCE) if ok.any() else float('nan'):6.1f} "
                  f"{np.median(bandpower(s, f0 - HALF, f0 + HALF)):10.3g} "
                  f"{np.median(bandpower(s, 18, 26)):10.3g} {np.median(bandpower(s, *RATCH)):10.3g}")
        print()


def h3_notched():
    hdr("H3.  HARMONIC-NOTCHED SEARCH -- blank +/-0.75 Hz at 2*f_r and 3*f_r, then re-locate")
    print(f"   {'build':14s} {'win':>4s} {'raw f0':>7s} {'raw prom':>9s} | {'notched f0':>11s} "
          f"{'sd':>5s} {'notched prom':>13s} {'p90':>9s} {'pres%':>6s}")
    for lbl, r in pools().items():
        nf = [notched_peak(x) for x in r]
        f0n = np.array([a for a, _ in nf], float)
        prn = np.array([b for _, b in nf], float)
        ok = np.isfinite(prn)
        print(f"   {lbl:14s} {len(r):4d} {np.nanmedian(col(r, 'f0')):7.2f} "
              f"{np.nanmedian(col(r, 'prom')):9.1f} | {np.nanmedian(f0n):11.2f} "
              f"{np.nanstd(f0n, ddof=1):5.2f} {np.nanmedian(prn):13.1f} "
              f"{np.nanpercentile(prn, 90):9.1f} {100 * np.mean(prn[ok] >= PRESENCE):6.1f}")
    print("\n   (if the 12-30 Hz line IS the harmonic, notching collapses its prominence; if it is an")
    print("    independent mode, notching leaves it where it was)")

    print("\n   -- same, ALSO notching the 4th harmonic. The 2f/3f pass pushed V62's lot peak to")
    print("      28.25 Hz, which is 4 x 7.06 -- so the ladder itself has to be excluded. --")
    print(f"   {'build':14s} {'win':>4s} {'notched f0':>11s} {'sd':>5s} {'prom':>9s} {'p90':>9s} "
          f"{'pres%':>6s}")
    for lbl, r in pools().items():
        nf = [notched_peak(x, harmonics=(2, 3, 4)) for x in r]
        f0n = np.array([a for a, _ in nf], float)
        prn = np.array([b for _, b in nf], float)
        ok = np.isfinite(prn)
        print(f"   {lbl:14s} {len(r):4d} {np.nanmedian(f0n):11.2f} {np.nanstd(f0n, ddof=1):5.2f} "
              f"{np.nanmedian(prn):9.1f} {np.nanpercentile(prn, 90):9.1f} "
              f"{100 * np.mean(prn[ok] >= PRESENCE):6.1f}")


def h5_handsoff():
    hdr("H5.  THE HANDS-OFF ARM -- V62's only arm that still shows a 21 Hz line. Is it a mode?")
    print("   Hands-off = sustained |lowpass(tq,3Hz)| <= 200. n is TINY on every build; every")
    print("   window is printed rather than summarised.\n")
    f0b = {b: pooled_f0(wrecs(b))[0] for b in ORDER}
    for b in ORDER:
        r = wrecs(b, hands=True, band=(f0b[b] - HALF, f0b[b] + HALF))
        print(f"   [{b}]  {len(r)} windows / {nrun(r)} episodes")
        print(f"     {'seg':>4s} {'t0':>7s} {'|v|':>5s} {'eff':>5s} {'f 6-9':>6s} {'promR':>9s} "
              f"{'f12-30':>7s} {'prom':>8s} {'ratio':>6s} {'notch f0':>9s} {'notch prom':>11s} "
              f"{'env99':>7s}")
        for x in r:
            nf, npr = notched_peak(x, harmonics=(2, 3, 4))
            rt = x["f0"] / x["fr"] if np.isfinite(x["fr"]) and x["fr"] > 0 else np.nan
            print(f"     {x['seg']:4d} {x['t0']:7.2f} {x['v']:5.2f} {x['eff']:5.0f} {x['fr']:6.2f} "
                  f"{x['promr']:9.1f} {x['f0']:7.2f} {x['prom']:8.1f} {rt:6.3f} {nf:9.2f} "
                  f"{npr:11.1f} {x['env']:7.1f}")
        print()


def h6_shift():
    hdr("H6.  THE STRUCTURAL SHIFT, SPEED-MATCHED and PROMINENCE-GATED")
    print("   The section-4 headline ratio used every window. Here both modes are located only in")
    print("   windows where that mode is solidly present (prominence >= 100x), inside one speed bin,")
    print("   so neither number is the argmax of a floor. 🛑 On V62 the 12-30 Hz column is KNOWN to")
    print("   be contaminated by the ratchet's 3rd harmonic -- it is printed for completeness, and")
    print("   the notched column beside it is the one that would carry a claim.\n")
    P = pools()
    for lo, hi in BINS:
        print(f"   |v| {lo}-{hi} m/s")
        print(f"     {'build':14s} {'n_r':>4s} {'ratchet f0':>11s} {'sd':>5s} | {'n_g':>4s} "
              f"{'grind f0':>9s} {'sd':>5s} | {'n_n':>4s} {'notched f0':>11s} {'sd':>5s}")
        for lbl, r in P.items():
            s = [x for x in r if lo <= x["v"] < hi]
            if not s:
                continue
            pr, pg = col(s, "promr"), col(s, "prom")
            fr = col(s, "fr")[np.isfinite(pr) & (pr >= 100)]
            fg = col(s, "f0")[np.isfinite(pg) & (pg >= 100)]
            nf = [notched_peak(x, harmonics=(2, 3, 4)) for x in s]
            fn = np.array([a for a, b in nf if np.isfinite(b) and b >= 100], float)
            def c(v):
                return (f"{np.median(v):11.2f} {v.std(ddof=1) if len(v) > 1 else 0:5.2f}"
                        if len(v) else f"{'--':>11s} {'--':>5s}")
            print(f"     {lbl:14s} {len(fr):4d} {c(fr)} | {len(fg):4d} "
                  f"{c(fg).replace('        ', '      ', 1)} | {len(fn):4d} {c(fn)}")
        print()


def h4_speed_ratchet():
    hdr("H4.  SPEED-MATCHED RATCHET -- route 37 spends much more engaged time at 1-2 m/s")
    print(f"   {'bin':>9s} {'build':14s} {'ep':>3s} {'win':>4s} {'f0':>6s} {'sd':>5s} "
          f"{'prom med':>9s} {'p90':>10s} {'max':>10s} {'P(6-9)':>10s} {'pres%':>6s}")
    P = pools()
    for lo, hi in BINS + [(0.3, 5.35)]:
        for lbl, r in P.items():
            s = [x for x in r if lo <= x["v"] < hi]
            if not s:
                print(f"   {lo:4.1f}-{hi:<4.1f} {lbl:14s}   -- n=0")
                continue
            pr = col(s, "promr")
            ok = np.isfinite(pr)
            f0m, f0s = msd(col(s, "fr"))
            print(f"   {lo:4.1f}-{hi:<4.1f} {lbl:14s} {nrun(s):3d} {len(s):4d} {f0m:6.2f} {f0s:5.2f} "
                  f"{np.nanmedian(pr):9.1f} {np.nanpercentile(pr, 90):10.1f} "
                  f"{np.nanmax(pr):10.1f} {np.median(bandpower(s, *RATCH)):10.3g} "
                  f"{100 * np.mean(pr[ok] >= PRESENCE):6.1f}")
        print()

    print("   -- engaged-creep speed composition (how many windows each build has per bin) --")
    for lbl, r in P.items():
        v = col(r, "v")
        print(f"     {lbl:14s} n={len(v):3d}  " + "  ".join(
            f"{lo}-{hi}: {int(((v >= lo) & (v < hi)).sum()):3d}" for lo, hi in
            [(0.3, 1), (1, 2), (2, 3), (3, 4), (4, 5.35)]))


_POOLS = {}


def pools():
    if not _POOLS:
        f0b = {b: pooled_f0(wrecs(b))[0] for b in ORDER}
        for b in ORDER:
            _POOLS[b] = wrecs(b, band=(f0b[b] - HALF, f0b[b] + HALF))
        _POOLS["V62 commute"] = wrecs("V62 r37", band=(f0b["V62 r37"] - HALF, f0b["V62 r37"] + HALF),
                                      segs=ROAD_37)
        _POOLS["V62 lot"] = wrecs("V62 r37", band=(f0b["V62 r37"] - HALF, f0b["V62 r37"] + HALF),
                                  segs=LOT_37)
    return _POOLS


def h7_final():
    hdr("H7.  THE DECISIVE FIGURE -- harmonic-excluded grinding presence, per speed bin")
    print("   Every 12-30 Hz peak within +/-0.75 Hz of 2/3/4 x the window's own ratchet frequency is")
    print("   blanked before the search. What is left is a line that cannot be ratchet distortion.")
    print("   The operator's '2-5 mph' is 0.89-2.24 m/s, i.e. essentially the 1-2 m/s bin.\n")
    print(f"   {'bin':>9s} {'build':14s} {'win':>4s} {'notch f0':>9s} {'sd':>5s} {'prom med':>9s} "
          f"{'p90':>9s} {'pres>=10x':>10s} {'pres>=100x':>11s}")
    P = pools()
    for lo, hi in BINS + [(0.3, 5.35)]:
        for lbl, r in P.items():
            s = [x for x in r if lo <= x["v"] < hi]
            if not s:
                continue
            nf = [notched_peak(x, harmonics=(2, 3, 4)) for x in s]
            f0n = np.array([a for a, _ in nf], float)
            prn = np.array([b for _, b in nf], float)
            ok = np.isfinite(prn)
            print(f"   {lo:4.1f}-{hi:<4.1f} {lbl:14s} {len(s):4d} {np.nanmedian(f0n):9.2f} "
                  f"{np.nanstd(f0n, ddof=1):5.2f} {np.nanmedian(prn):9.1f} "
                  f"{np.nanpercentile(prn, 90):9.1f} {100 * np.mean(prn[ok] >= 10):9.1f}% "
                  f"{100 * np.mean(prn[ok] >= 100):10.1f}%")
        print()

    hdr("H8.  RATCHET FREQUENCY SHIFT vs its own NULL CONTROL")
    print("   V64 is spectrally identical to V59 (its cal edits never applied), so V64/V59 measures")
    print("   the route-to-route floor of this statistic. Any V62/V59 shift must clear that floor.")
    print("   rate_lane_damping_model predicts V62 = +11.9% if V61's x0.865 extrapolates linearly.\n")
    print(f"   {'bin':>9s} {'V59':>7s} {'V64':>7s} {'V61':>7s} {'V62':>7s} | "
          f"{'V64/V59':>8s} {'V61/V59':>8s} {'V62/V59':>8s}")
    ref = {}
    for lo, hi in BINS:
        vals = {}
        for lbl in ("V59 r2c", "V64 r35", "V61 r31", "V62 r37"):
            s = [x for x in P[lbl] if lo <= x["v"] < hi]
            fr = col(s, "fr") if s else np.array([])
            pr = col(s, "promr") if s else np.array([])
            m = np.isfinite(fr) & np.isfinite(pr) & (pr >= PRESENCE)
            vals[lbl] = (np.median(fr[m]), int(m.sum())) if m.sum() else (np.nan, 0)
        ref[(lo, hi)] = vals
        f = lambda k: vals[k][0]  # noqa: E731
        print(f"   {lo:4.1f}-{hi:<4.1f} " + " ".join(
            f"{f(k):7.2f}" if np.isfinite(f(k)) else f"{'--':>7s}"
            for k in ("V59 r2c", "V64 r35", "V61 r31", "V62 r37")) + " | " + " ".join(
            f"{f(k) / f('V59 r2c'):8.3f}" if np.isfinite(f(k)) and np.isfinite(f("V59 r2c"))
            else f"{'--':>8s}" for k in ("V64 r35", "V61 r31", "V62 r37")))
        print(f"   {'':9s} " + " ".join(f"n={vals[k][1]:<5d}" for k in
                                        ("V59 r2c", "V64 r35", "V61 r31", "V62 r37")))


def main():
    h1_ratio()
    h2_quiet()
    h3_notched()
    h4_speed_ratchet()
    h5_handsoff()
    h6_shift()
    h7_final()


if __name__ == "__main__":
    main()
