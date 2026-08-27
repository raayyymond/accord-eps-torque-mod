#!/usr/bin/env python3
"""V61 route `31` -- THE DECISIVE CONTROL for the "new manual grinding" claim.

M5 showed the loudest MANUAL windows on route 31 are at |v| ~ 0.0-0.6 m/s with the wheel cranked
hard (effort 2200-2700 counts) -- i.e. the >= 0.3 m/s "moving" gate was hiding them. That raises
the one question that decides whether V61 caused anything:

    *** Do the V58/V59 routes ALSO show an 16-19 Hz line when the car is near-stationary and the
    driver is cranking the wheel manually? If they do, the "new manual grinding" is the operating
    point, not the build.

Both predecessor routes contain that condition (route 2b seg 0 is 61 s parked; route 2c segs 0/12
have parked manual sections), so the control is available and is run here at MATCHED effort.

Gear is only available on the route-31 cache, so the predecessor arms are defined by speed +
!latActive, which is the same physical condition (stationary, manual, wheel being worked).

Usage:  python studies/sessions/r31/analyze_r31_standstill.py
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
                         band_envelope, fs_of, load, periodogram, runs_of, sustained)
from analyze_r31_spectra import peaks

VSTILL = 0.6            # "near-stationary": below this the wheel is being worked against a stop


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def cut(segs, mask_fn, cache=None, pfx="r31s", nfft=NFFT):
    """Per-window records over any mask, with a free 12-30 Hz argmax and the raw-waveform stats
    needed to rule out a step/spike faking a peak."""
    out = []
    for s in segs:
        d = load(s, cache, pfx) if cache is not None else load(s)
        fs = fs_of(d)
        m = mask_fn(d)
        if not m.any():
            continue
        f = np.fft.rfftfreq(nfft, 1 / fs)
        for a, b in runs_of(m, d["t"], nfft):
            x = d["tq"][a:b]
            env = band_envelope(x, fs, 14.0, 22.0)
            for i in range(0, len(x) - nfft + 1, nfft):
                seg = x[i:i + nfft]
                P = periodogram(seg, fs, nfft)
                if P is None:
                    continue
                pk = peaks(f, P, 12.0, 30.0, min_prom=0.0)
                sl = slice(a + i, a + i + nfft)
                dif = np.abs(np.diff(seg))
                out.append(dict(
                    f0=pk[0][0] if pk else np.nan, prom=pk[0][1] if pk else np.nan,
                    Q=pk[0][2] if pk else np.nan,
                    env=float(np.percentile(env[i:i + nfft], 99)),
                    v=float(np.mean(np.abs(d["cs_v"][sl]))),
                    ang=float(np.mean(np.abs(d["ang"][sl]))),
                    eff=float(np.mean(np.abs(sustained(d["tq"][sl], fs)))),
                    rng=float(seg.max() - seg.min()), maxstep=float(dif.max()),
                    sd=float(seg.std()), seg=s, t0=float(d["t"][a + i])))
    return out


def summ(tag, r, cuts=(10, 50, 200)):
    if not r:
        print(f"   {tag:44s} n=0")
        return
    pr = np.array([x["prom"] for x in r], float)
    f0 = np.array([x["f0"] for x in r], float)
    ev = np.array([x["env"] for x in r], float)
    ok = np.isfinite(pr)
    pr, f0, ev = pr[ok], f0[ok], ev[ok]
    t = f0[pr >= 10]
    print(f"   {tag:44s} n={len(pr):3d}  prom med {np.median(pr):8.1f} p90 "
          f"{np.percentile(pr,90):9.1f} max {pr.max():9.1f}  "
          f"envp99 med {np.median(ev):7.1f} max {ev.max():7.1f}  "
          f"f0 med {np.median(f0):5.2f}  [prom>=10x: n={len(t):2d} f0 "
          f"{np.median(t) if len(t) else np.nan:5.2f} sd {t.std(ddof=1) if len(t)>1 else 0:4.2f}]  "
          + " ".join(f">{c}x:{int((pr>=c).sum())}" for c in cuts))


def main():
    hdr("N1. NEAR-STATIONARY MANUAL (|v| <= 0.6 m/s, !latActive) -- V61 vs V59 vs V58")
    print("   The condition where route 31's loudest manual windows live. If the predecessors show")
    print("   the same line here, V61 changed nothing about manual driving.\n")
    still_man = lambda d: (np.abs(d["cs_v"]) <= VSTILL) & (d["cc_lat"] <= 0.5)  # noqa: E731
    r31 = cut(SEGS_31, still_man)
    r2c = cut(SEGS_2C, still_man, CACHE_2C, "r2cs")
    r2b = cut(SEGS_2B, still_man, CACHE_2B, "r2bs")
    summ("V61 r31  stationary manual (all gears)", r31)
    summ("V59 r2c  stationary manual", r2c)
    summ("V58 r2b  stationary manual", r2b)

    print("\n   -- EFFORT-MATCHED: only windows with sustained effort >= 1000 counts --")
    print("      (a stationary driver not touching the wheel excites nothing; the operator's")
    print("       report is specifically about turning it)")
    for tag, r in [("V61 r31", r31), ("V59 r2c", r2c), ("V58 r2b", r2b)]:
        summ(f"{tag}  stationary manual, eff >= 1000", [x for x in r if x["eff"] >= 1000])
    print("\n   -- and eff >= 2000 --")
    for tag, r in [("V61 r31", r31), ("V59 r2c", r2c), ("V58 r2b", r2b)]:
        summ(f"{tag}  stationary manual, eff >= 2000", [x for x in r if x["eff"] >= 2000])

    hdr("N2. ROUTE 31 BY GEAR at near-stationary, manual")
    for g, lbl in [(1.0, "PARK"), (2.0, "DRIVE (forward)"), (4.0, "REVERSE")]:
        r = cut(SEGS_31, lambda d, g=g: (np.abs(d["cs_v"]) <= VSTILL) & (d["cc_lat"] <= 0.5)
                & (d["cs_gear"] == g))
        summ(f"V61 r31  {lbl}", r)
        if r:
            hi = [x for x in r if x["eff"] >= 1000]
            summ(f"V61 r31  {lbl}, eff >= 1000", hi)
    print("\n   *** PARK is the control that separates 'gear' from 'stationary + cranking'.")

    hdr("N3. THE LOUDEST MANUAL WINDOWS ON ROUTE 31 -- waveform sanity check")
    print("   A single step or dropout can fake a high-prominence peak. rng = peak-to-peak of the")
    print("   raw window; maxstep = largest sample-to-sample jump. A real ~18 Hz oscillation at")
    print("   100 Hz sampling has maxstep well below rng (roughly rng*sin(2*pi*18/100) ~ 0.85*rng")
    print("   for a pure sinusoid), and rng >> the band envelope only if there is also a DC ramp.\n")
    allman = cut(SEGS_31, still_man) + cut(
        SEGS_31, lambda d: (np.abs(d["cs_v"]) > VSTILL) & (d["cs_v"] <= 5) & (d["cc_lat"] <= 0.5))
    allman.sort(key=lambda x: -(x["prom"] if np.isfinite(x["prom"]) else 0))
    print(f"   {'seg':>4s} {'t0':>7s} {'gear':>7s} {'|v|':>6s} {'|ang|':>7s} {'eff':>6s} "
          f"{'f0':>6s} {'prom':>9s} {'Q':>6s} {'envp99':>8s} {'rng':>7s} {'maxstep':>8s}")
    gearmap = {}
    for s in SEGS_31:
        d = load(s)
        gearmap[s] = (d["t"], d["cs_gear"])
    for x in allman[:14]:
        tt, gg = gearmap[x["seg"]]
        g = int(gg[np.searchsorted(tt, x["t0"] + 1.28)])
        print(f"   {x['seg']:4d} {x['t0']:7.2f} {['unk','P','D','N','R'][g] if g < 5 else g:>7} "
              f"{x['v']:6.2f} {x['ang']:7.1f} {x['eff']:6.0f} {x['f0']:6.2f} {x['prom']:9.1f} "
              f"{x['Q']:6.1f} {x['env']:8.1f} {x['rng']:7.0f} {x['maxstep']:8.0f}")

    hdr("N4. ENGAGED reference on the same statistic, for scale")
    eng = cut(SEGS_31, lambda d: (np.abs(d["cs_v"]) <= 5.0) & (d["cc_lat"] > 0.5))
    summ("V61 r31  engaged (|v| <= 5)", eng)
    e2c = cut(SEGS_2C, lambda d: (np.abs(d["cs_v"]) <= 5.0) & (d["cc_lat"] > 0.5), CACHE_2C, "r2cs")
    e2b = cut(SEGS_2B, lambda d: (np.abs(d["cs_v"]) <= 5.0) & (d["cc_lat"] > 0.5), CACHE_2B, "r2bs")
    summ("V59 r2c  engaged (|v| <= 5)", e2c)
    summ("V58 r2b  engaged (|v| <= 5)", e2b)


if __name__ == "__main__":
    main()
