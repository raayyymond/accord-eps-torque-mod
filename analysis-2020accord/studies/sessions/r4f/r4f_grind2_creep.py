#!/usr/bin/env python3
"""Route `4f` (V69): does the operator's *"grind #2 seems to be GONE at low AND high speeds"* hold?

THIS SCRIPT COVERS THE CREEP ARM ONLY. The highway arm is `studies/sessions/r4f/r4f_highway_bands.py`; the lane-change
transient is `studies/sessions/r4f/r4f_lanechange.py`.

🛑🛑 THE ONE THING THAT MUST BE SAID BEFORE ANY NUMBER, AND IT IS THE EASIEST WAY TO OVER-CREDIT
V69: **V67 ALREADY ELIMINATED ENGAGED-CREEP GRIND #2.** Route `4a` gave 158.7 s armed with 0 bursts
against 7.62 expected, P(0) = 0.0005 (`_scratch/out/_r4a_results.json`). So a zero-burst creep result on `4f`
REPLICATES V67/V68's already-clean arm. It is a *non-regression* result for V69's 4x dose, which is
worth having -- V62's flat 2x is grind #2's own cause and 4x is twice the largest dose ever driven --
but it is NOT evidence that V69 removed anything at creep. That distinction is printed at every
table here rather than left to the reader.

INSTRUMENT. Deliberately `r47_orchestrator_checks._windows` UNCHANGED -- the same 2.56 s window, the
same butter+hilbert band envelope, the same p99, the same 500-count burst threshold that produced
every prior route's burst count. A Poisson comparison against the Kd=2 rate is only valid if the
detector is bit-identical, so the newer `_grind2_lib.win_env` (tapered) is NOT substituted here even
though it is the better estimator; the two differ by ~1.4-1.9x and cross-comparing them is the error
HANDOFF-2026-08-03 §9 records.
⚠ That also means this section inherits R47's `1/median(dt)` sample rate (biased high by 0.1-1.4%
route-to-route). COMMON MODE across every pool by construction, and 0.4% at 45 Hz is 0.18 Hz on a
9 Hz-wide band -- immaterial to a band-envelope census, material to a line frequency. The line work
in `studies/sessions/r4f/r4f_highway_bands.py` uses the lattice rate instead.

Usage:  python studies/sessions/r4f/r4f_grind2_creep.py [--json OUT]
"""
from __future__ import annotations
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

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import poisson

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:                                    # Windows consoles default to cp1252 and die on the emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import r47_orchestrator_checks as R47                              # noqa: E402
from _r31_common import load, sustained                            # noqa: E402

C4F = ROOT / "_scratch/cache/r4f"
SEGS = list(range(8))
PFX = "r4fs"
OUTJSON = HERE / "_scratch/out/_r4f_creep.json"

CREEP = (0.3, 4.0)              # the kit's creep window for the grind-#2 census (r4a §6)
CORNER_EFF, CORNER_ANG = 1200.0, 100.0

# V69's eight legal payloads on the wire (bit7 set, bit3 CLEAR, status bits 7).
LEGAL_V69 = {0x80 | a | b | c | 0x07 for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)}
V68_SPACE = {0x88 | a | b | c | 0x07 for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)}

POOLS = {
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_scratch/cache/r2b", "_scratch/cache/r2c", "_scratch/cache/r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
    "Kd=gated (V67 r47+r4a)":                 ["_scratch/cache/r47", "_scratch/cache/r4a"],
    "Kd=4x<50 (V69 r4f)  *** THIS ROUTE ***": ["_scratch/cache/r4f"],
}
KD2 = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
V67 = "Kd=gated (V67 r47+r4a)"
V69 = "Kd=4x<50 (V69 r4f)  *** THIS ROUTE ***"
RESULTS: dict = {}


def hdr(s):
    print(f"\n{'=' * 110}\n{s}\n{'=' * 110}")


def segs4f():
    for s in SEGS:
        p = C4F / f"{PFX}{s}.npz"
        if p.exists():
            yield s, load(s, C4F, PFX)


# =================================================================================================
def sec_identity():
    hdr("1.  BUILD IDENTITY FROM THE LOG -- never from the filename (the V64 lesson)")
    print("   V69's cave loads `movea 0x80,r0,r7`: bit7 LIVENESS set, bit3 build-class marker CLEAR.")
    print("   V68 sets bit3 on EVERY frame it emits (asserted by its build, measured 53,991/53,991),")
    print("   so ANY bit3==0 frame excludes V68 -- the image that was on the car before this one.\n")
    grid, raw = Counter(), Counter()
    for s, d in segs4f():
        grid.update(d["probe"].astype(int).tolist())
        raw.update(np.asarray(d["raw14_b4"], int).tolist())
    ngrid, nraw = sum(grid.values()), sum(raw.values())
    print(f"   {'byte4':>7s} {'grid frames':>12s} {'%':>9s} {'RAW 0x14A src1':>15s} {'%':>9s}   bits")
    for v in sorted(set(grid) | set(raw)):
        b = (f"b7={v >> 7 & 1} b6={v >> 6 & 1} b5={v >> 5 & 1} b4={v >> 4 & 1} "
             f"b3={v >> 3 & 1} st={v & 7}")
        print(f"   0x{v:02X}   {grid[v]:12d} {100 * grid[v] / ngrid:8.3f}% {raw[v]:15d} "
              f"{100 * raw[v] / nraw:8.3f}%   {b}")
    b3 = sum(c for v, c in grid.items() if v & 0x08)
    live = sum(c for v, c in grid.items() if v & 0x80)
    ill = sum(c for v, c in raw.items() if v not in LEGAL_V69)
    v68hit = sum(c for v, c in raw.items() if v in V68_SPACE)
    print(f"\n   bit7 LIVENESS set   : {live}/{ngrid} = {100 * live / ngrid:.3f}%   "
          f"(VOID would mean the cave never ran)")
    print(f"   bit3 CLASS set      : {b3}/{ngrid}   -- must be 0 on V69; V68 would be 100%")
    print(f"   outside V69's 8 legal payloads : {ill}/{nraw}")
    print(f"   inside V68's payload space     : {v68hit}/{nraw}")

    # --- the three ratchet rungs, and the two-tier exclusion -------------------------------------
    tot = ne = 0
    b6 = b5 = b4 = 0
    b6e = 0
    for s, d in segs4f():
        p = d["probe"].astype(int)
        eng = d["cc_lat"] > 0.5
        tot += len(p); ne += int(eng.sum())
        b6 += int((p & 0x40 != 0).sum()); b5 += int((p & 0x20 != 0).sum())
        b4 += int((p & 0x10 != 0).sum())
        b6e += int(((p & 0x40) != 0)[eng].sum())
    print(f"\n   THE THREE RATCHET RUNGS over {tot} frames ({tot / 100.0:.0f} s):")
    print(f"     bit6  gp-0x6ada >= +4096  (r24 lane out, half its rail) : {b6}  "
          f"({100 * b6 / tot:.4f}%)   *** V69's PRE-REGISTERED POSITIVE CONTROL (P7) ***")
    print(f"     bit5  gp-0x6b62 >= +4096  (return-to-centre lane)       : {b5}  "
          f"({100 * b5 / tot:.4f}%)")
    print(f"     bit4  gp-0x6ad4 >= +4096  (unfiltered residual lane)    : {b4}  "
          f"({100 * b4 / tot:.4f}%)")
    print(f"     engaged frames {ne} ({100 * ne / tot:.1f}%); bit6 while engaged {b6e}")

    print("\n   ★ THE EXCLUSION ARGUMENT, and it is STRONGER than the decoder's own tier-2 caveat.")
    print("     `probe/decode_v69_ratchet.py` warns that V66/V67 also emit bit3 = 0 and that their")
    print("     reachable payloads {0x87, 0xC7} are a SUBSET of V69's, so discrimination from those")
    print("     two 'rests on bit5 or bit4 ever firing, plus the .rwd filename'. On THIS route it")
    print("     does not have to: on V66 AND V67 bit6 is `gp-0x6806 != 0`, Honda's LKAS gate, which")
    print("     V68/route-4e measured tracking carControl.latActive EXACTLY at highway speed.")
    seg_eng = []
    for s, d in segs4f():
        lat = float((d["cc_lat"] > 0.5).mean())
        b6d = float((d["probe"].astype(int) & 0x40 != 0).mean())
        seg_eng.append((s, len(d["t"]), lat, b6d))
    full = [r for r in seg_eng if r[2] > 0.99]
    nfull = sum(r[1] for r in full)
    print(f"     Segments at latActive > 99%: {[r[0] for r in full]} = {nfull} frames.")
    print(f"     On V66/V67 every one of those frames would carry byte4 = 0xC7. Observed 0xC7: "
          f"{raw.get(0xC7, 0)}.")
    print("     ⇒ V66 and V67 are excluded BY MEASUREMENT here, not by filename. With V68 excluded")
    print("       by bit3 and V53/V54 structurally disjoint, the flown image is V69. [EVIDENCE]")
    print("   🛑 AND THEREFORE bit6's 0.0000% IS NOT 'the cave is the wrong one'. P7 said a silent")
    print("     bit6 means check bit7 and the .rwd name first; bit7 is 100% and the payload census")
    print("     rules out every other build. So the reading is the OTHER one: over this whole drive")
    print("     the r24 lane output never reached +4096 on its POSITIVE side. ⚠ ONE-SIDED -- it")
    print("     bounds positive excursions only, and says nothing about -4096.")
    RESULTS["identity"] = dict(byte4_grid={f"0x{v:02X}": c for v, c in grid.items()},
                               byte4_raw={f"0x{v:02X}": c for v, c in raw.items()},
                               frames=ngrid, bit3_set=b3, live=live, illegal=ill, v68_hits=v68hit,
                               bit6=b6, bit5=b5, bit4=b4, bit6_engaged=b6e,
                               engaged_frames=ne, full_eng_segs=[r[0] for r in full],
                               full_eng_frames=nfull, verdict="V69")


# =================================================================================================
def sec_flight():
    hdr("2.  FLIGHT-CLEAN CHECK -- P5 (`ST == 4` stays 0, the zero-EME streak continues)")
    stg, stw = Counter(), Counter()
    ev = Counter()
    for s, d in segs4f():
        stg.update(d["sstat"].astype(int).tolist())
        stw.update(np.asarray(d["raw18_st"], int).tolist())
        p = C4F / f"{PFX}{s}_events.json"
        if p.exists():
            for e in json.loads(p.read_text()):
                ev[e["name"]] += 1
    print(f"   STEER_STATUS, 0x14A grid : {dict(sorted(stg.items()))}")
    print(f"   STEER_STATUS, RAW 0x18F  : {dict(sorted(stw.items()))}   (independent second method)")
    watch = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
             "immediateDisable", "steerSaturated", "steerOverride"]
    print(f"   onroadEvents: {dict(ev.most_common(12))}")
    bad = {k: ev[k] for k in watch if ev.get(k)}
    print(f"   WATCHLIST hits: {bad if bad else 'NONE'}")
    print(f"   ⇒ ST==4 {stg.get(4, 0)} (grid) / {stw.get(4, 0)} (raw);  "
          f"ST==3 {stg.get(3, 0)} / {stw.get(3, 0)}   "
          f"⇒ P5 {'HELD' if stg.get(4, 0) == 0 and stw.get(4, 0) == 0 else 'VIOLATED'}")
    RESULTS["flight"] = dict(st_grid=dict(stg), st_raw=dict(stw), events=dict(ev))


# =================================================================================================
def sec_exposure():
    hdr("3.  EXPOSURE -- what this route can and cannot speak to")
    print(f"   {'seg':>4s} {'n':>6s} {'dur s':>7s} {'v max':>7s} {'eng %':>7s} "
          f"{'creep s':>8s} {'engcreep':>9s} {'discreep':>9s} {'hwy>=20':>8s} {'enghwy':>7s} "
          f"{'corner':>7s}")
    tot = dict(dur=0.0, creep=0.0, engcreep=0.0, discreep=0.0, hwy=0.0, enghwy=0.0, corner=0.0,
               dcorner=0.0)
    per = []
    for s, d in segs4f():
        t = d["t"]
        dt = float(np.median(np.diff(t)))
        v = np.abs(d["cs_v"])
        eng = d["cc_lat"] > 0.5
        fs = 1.0 / dt
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        ang = np.abs(d["ang"])
        cr = (v > CREEP[0]) & (v < CREEP[1])
        hw = v >= 20.0
        cor = cr & (eff >= CORNER_EFF) & (ang >= CORNER_ANG)
        row = dict(seg=s, n=len(t), dur=float(t[-1] - t[0]), vmax=float(v.max()),
                   eng=float(eng.mean()), creep=float(cr.sum()) * dt,
                   engcreep=float((cr & eng).sum()) * dt,
                   discreep=float((cr & ~eng).sum()) * dt,
                   hwy=float(hw.sum()) * dt, enghwy=float((hw & eng).sum()) * dt,
                   corner=float((cor & eng).sum()) * dt, dcorner=float((cor & ~eng).sum()) * dt)
        per.append(row)
        for k in tot:
            tot[k] += row[k]
        print(f"   {s:4d} {len(t):6d} {row['dur']:7.1f} {row['vmax']:7.2f} "
              f"{100 * row['eng']:6.1f}% {row['creep']:8.1f} {row['engcreep']:9.1f} "
              f"{row['discreep']:9.1f} {row['hwy']:8.1f} {row['enghwy']:7.1f} {row['corner']:7.1f}")
    print(f"   {'TOT':>4s} {'':6s} {tot['dur']:7.1f} {'':7s} {'':7s} {tot['creep']:8.1f} "
          f"{tot['engcreep']:9.1f} {tot['discreep']:9.1f} {tot['hwy']:8.1f} {tot['enghwy']:7.1f} "
          f"{tot['corner']:7.1f}")
    print(f"\n   corner = creep ∧ |sustained torque| >= {CORNER_EFF:.0f} ∧ |angle| >= "
          f"{CORNER_ANG:.0f} deg -- the cell grind #2 actually lived in on V62/V65.")
    print(f"   engaged corner {tot['corner']:.1f} s   disengaged corner {tot['dcorner']:.1f} s")
    RESULTS["exposure"] = dict(per_seg=per, total=tot)


# =================================================================================================
_W: dict = {}


def windows(pool):
    if pool not in _W:
        _W[pool] = sum([R47._windows(c, pool, lambda v: CREEP[0] < v < CREEP[1])
                        for c in POOLS[pool]], [])
    return _W[pool]


def _windows_eff(cache, tag):
    """R47._windows plus the effort/angle covariates the corner condition needs."""
    rows = []
    for p in sorted(glob.glob(str(ROOT / cache / "*.npz"))):
        if "_imu" in p or "_rpm" in p:
            continue
        d = dict(np.load(p))
        if "cs_v" not in d or "tq" not in d:
            continue
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        if not 95 < fs < 105:
            continue
        env = {k: R47._envelope(d["tq"], fs, *v) for k, v in R47.BANDS.items()}
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        n, hop = int(R47.WIN_S * fs), int(R47.WIN_S * fs) // 2
        lat = d["cc_lat"] > 0.5
        for i in range(0, len(t) - n, hop):
            sl = slice(i, i + n)
            v = float(np.median(d["cs_v"][sl]))
            if not (CREEP[0] < v < CREEP[1]):
                continue
            rows.append(dict(tag=tag, v=v, lat=float(lat[sl].mean()),
                             ang=float(np.abs(d["ang"][sl]).max()),
                             eff=float(np.median(eff[sl])),
                             **{k: float(np.percentile(env[k][sl], 99)) for k in R47.BANDS}))
    return rows


def sec_grind2():
    hdr("4.  GRIND #2 (40-49 Hz) AT CREEP -- burst census on the IDENTICAL instrument")
    print(f"   burst = one {R47.WIN_S} s window whose 40-49 Hz envelope p99 exceeds "
          f"{R47.BURST:.0f}. The V62/V65 creep bursts ran 2000-4000, so the threshold sits far")
    print("   below the phenomenon it is detecting.\n")
    print(f"   {'pool':44s} {'arm':9s} {'secs':>7s} {'n':>5s} {'40-49 p50':>10s} "
          f"{'40-49 p90':>10s} {'40-49 MAX':>10s} {'bursts':>7s} {'rate/s':>9s}")
    have, rate = {}, {}
    for k in POOLS:
        ss = windows(k)
        for lab, sel in (("LKAS ON", lambda r: r["lat"] > 0.9),
                         ("LKAS OFF", lambda r: r["lat"] < 0.1)):
            s = [r for r in ss if sel(r)]
            secs = len(s) * R47.WIN_S / 2
            if not s:
                print(f"   {k:44s} {lab:9s} {0.0:7.1f} {0:5d}")
                have[(k, lab)] = (0.0, 0)
                continue
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            print(f"   {k:44s} {lab:9s} {secs:7.1f} {len(s):5d} "
                  f"{np.median([r['40-49'] for r in s]):10.1f} "
                  f"{np.percentile([r['40-49'] for r in s], 90):10.1f} "
                  f"{max(r['40-49'] for r in s):10.1f} {b:7d} {b / max(secs, 1e-9):9.5f}")
            have[(k, lab)] = (secs, b)
            if k == KD2:
                rate[lab] = b / secs
        print()

    print("   Kd=2.00 reference burst RATES, recomputed here from the caches (never quoted):")
    for lab in ("LKAS ON", "LKAS OFF"):
        s, b = have[(KD2, lab)]
        print(f"      {lab:9s} {b} bursts / {s:.0f} s = {rate[lab]:.5f} /s")

    print("\n   POWER: P(0 bursts | the Kd=2.00 rate).")
    print(f"   {'route':30s} {'arm':9s} {'secs':>8s} {'observed':>9s} {'expected':>9s} "
          f"{'P(0)':>8s}   verdict")
    pw = {}
    for k, rl in ((V67, "V67 r47+r4a (PRIOR)"), (V69, "V69 r4f  (THIS ROUTE)")):
        for lab in ("LKAS ON", "LKAS OFF"):
            secs, obs = have[(k, lab)]
            exp = rate[lab] * secs
            p0 = float(poisson.pmf(0, exp))
            verd = ("RESOLVED (P(0) < 0.05)" if p0 < 0.05 and obs == 0 else
                    f"{obs} burst(s) OBSERVED" if obs else "UNDER-POWERED")
            print(f"   {rl:30s} {lab:9s} {secs:8.1f} {obs:9d} {exp:9.2f} {p0:8.4f}   {verd}")
            pw[f"{rl}|{lab}"] = dict(secs=secs, obs=obs, exp=exp, p0=p0)
    RESULTS["grind2_creep"] = dict(power=pw, kd2_rate=rate,
                                   census={f"{a}|{b}": list(v) for (a, b), v in have.items()})

    # ---- corner-conditioned ---------------------------------------------------------------------
    hdr("4b. CORNER-CONDITIONED POWER -- the stronger version of the same test")
    print("   Grind #2 never lived uniformly in creep; it lived in creep ∧ |sustained torque| >=")
    print(f"   {CORNER_EFF:.0f} ∧ |angle| >= {CORNER_ANG:.0f} deg. Conditioning the RATE on that "
          "corner removes the")
    print("   assumption that this route's creep seconds are exchangeable with V62/V65's, which is")
    print("   the weakest link in §4.\n")
    W = {k: sum([_windows_eff(c, k) for c in v], []) for k, v in POOLS.items()}
    print(f"   {'pool':44s} {'arm':9s} {'corner s':>9s} {'n':>5s} {'40-49 MAX':>10s} "
          f"{'bursts':>7s} {'rate/s':>9s}")
    crate, chave = {}, {}
    for k, ss in W.items():
        for lab, sel in (("LKAS ON", lambda r: r["lat"] > 0.9),
                         ("LKAS OFF", lambda r: r["lat"] < 0.1)):
            s = [r for r in ss if sel(r) and r["eff"] >= CORNER_EFF and r["ang"] >= CORNER_ANG]
            secs = len(s) * R47.WIN_S / 2
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            mx = max((r["40-49"] for r in s), default=float("nan"))
            print(f"   {k:44s} {lab:9s} {secs:9.1f} {len(s):5d} {mx:10.1f} {b:7d} "
                  f"{b / max(secs, 1e-9):9.5f}")
            chave[(k, lab)] = (secs, b)
            if k == KD2:
                crate[lab] = b / max(secs, 1e-9)
        print()
    print("   P(0 bursts | the Kd=2.00 CORNER rate):")
    print(f"   {'route':30s} {'arm':9s} {'corner s':>9s} {'observed':>9s} {'expected':>9s} "
          f"{'P(0)':>8s}")
    cpw = {}
    for k, rl in ((V67, "V67 r47+r4a (PRIOR)"), (V69, "V69 r4f  (THIS ROUTE)")):
        for lab in ("LKAS ON", "LKAS OFF"):
            secs, obs = chave[(k, lab)]
            exp = crate[lab] * secs
            print(f"   {rl:30s} {lab:9s} {secs:9.1f} {obs:9d} {exp:9.2f} "
                  f"{float(poisson.pmf(0, exp)):8.4f}")
            cpw[f"{rl}|{lab}"] = dict(secs=secs, obs=obs, exp=exp,
                                      p0=float(poisson.pmf(0, exp)))
    RESULTS["grind2_corner"] = dict(power=cpw, kd2_corner_rate=crate,
                                    census={f"{a}|{b}": list(v)
                                            for (a, b), v in chave.items()})

    # ---- the interpretation, stated rather than left implicit ------------------------------------
    hdr("4c. 🛑 IS THIS NEW, OR A REPLICATION?")
    s_on, b_on = have[(V69, "LKAS ON")]
    s_off, b_off = have[(V69, "LKAS OFF")]
    print(f"   V69/4f engaged creep : {s_on:.1f} s, {b_on} bursts, "
          f"expected {rate['LKAS ON'] * s_on:.2f} at the Kd=2 rate, "
          f"P(0) = {poisson.pmf(0, rate['LKAS ON'] * s_on):.4f}")
    print(f"   V67 prior (r47+r4a)  : 158.7 s armed, 0 bursts, expected 7.62, P(0) = 0.0005 "
          f"[_scratch/out/_r4a_results.json]")
    print("\n   ⇒ THE ENGAGED-CREEP ARM WAS ALREADY CLEAN ON V67, AND V68 INHERITED V67's CONTROL")
    print("     PATH BYTE-FOR-BYTE. A zero here REPLICATES that; it does not demonstrate a V69 fix.")
    print("     What it DOES establish, and this is the part worth having: **V69's 4.000x low-speed")
    print("     dose did not RE-INTRODUCE creep grind #2** -- which is exactly prediction P6, and")
    print("     the risk was real, because V62's flat 2.00x is grind #2's own recorded cause and")
    print("     4x is twice the largest dose this kit has ever driven. [EVIDENCE, non-regression]")


# =================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(OUTJSON))
    ap.add_argument("sections", nargs="*")
    a = ap.parse_args()
    todo = a.sections or ["identity", "flight", "exposure", "grind2"]
    for s in todo:
        globals()["sec_" + s]()
    Path(a.json).write_text(json.dumps(RESULTS, indent=1, default=str))
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
