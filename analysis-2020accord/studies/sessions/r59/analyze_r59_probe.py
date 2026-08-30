#!/usr/bin/env python3
"""studies/sessions/r59/analyze_r59_probe.py -- route 59 (V72): read the probe, and census the exposure.

Two jobs, kept apart on purpose:
  1. THE PROBE. bit6/bit5 = `a` (gp-0x69a4), bit4 = is Lever B's base damper in force, bit3 = the
     pre-registered rate-axis positive control. Plus liveness and the `bit5 => bit6` invariant.
  2. THE EXPOSURE CENSUS. Which regimes this drive actually visited, in seconds. 🛑 "EMPTY" IS NOT
     "NULL" and the distinction has bitten this kit repeatedly -- a regime with zero frames must be
     reported as unpowered, never as a negative result.

Usage:  python studies/sessions/r59/analyze_r59_probe.py
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from _r4f_lib import fs_lattice        # noqa: E402  -- never 1/median(dt)

CACHE = ROOT / "_scratch/cache/r59"
PFX = "r59s"
SEGS = list(range(15))

BIT_LIVE, BIT_A512, BIT_A1024, BIT_DAMP, BIT_RATE = 0x80, 0x40, 0x20, 0x10, 0x08
PROBE_MASK = 0xF8
LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_A512, BIT_A512 | BIT_A1024)
         for b in (0, BIT_DAMP) for c in (0, BIT_RATE)}

RATE_SCALE = 4.7121                       # counts per deg/s, settled three independent ways
RATE_DEGS = 512 / RATE_SCALE              # 108.66 deg/s
PREREG_BIT3 = 2.750                       # 📋 percent engaged, 9,497 / 345,396 prior frames
FACTORC_ONSET_KMH = 35.0
CREEP_MS = 4.0
HIGHWAY_MS = 13.9


def load_all():
    segs, tot_t = [], 0.0
    for s in SEGS:
        f = CACHE / f"{PFX}{s}.npz"
        if not f.exists():
            print(f"  ⚠ missing {f}")
            continue
        d = {k: v for k, v in np.load(f, allow_pickle=True).items()}
        d["_seg"] = s
        d["_fs"] = fs_lattice(d)
        d["_dt"] = 1.0 / d["_fs"]
        segs.append(d)
        tot_t += len(d["t"]) * d["_dt"]
    return segs, tot_t


def cat(segs, key):
    return np.concatenate([np.asarray(d[key], float) for d in segs])


def hdr(s):
    print("\n" + "=" * 98 + f"\n  {s}\n" + "=" * 98)


def duty(mask, sel):
    """(percent, n_fire, n_sel). Returns NaN percent on an EMPTY selector -- empty is not null."""
    n = int(sel.sum())
    if n == 0:
        return float("nan"), 0, 0
    k = int((mask & sel).sum())
    return 100.0 * k / n, k, n


def main():
    segs, _ = load_all()
    if not segs:
        print("no cache")
        return 2
    dt = np.concatenate([np.full(len(d["t"]), d["_dt"]) for d in segs])
    b4 = np.concatenate([np.asarray(d["probe"], int) for d in segs]).astype(np.uint8)
    v = cat(segs, "cs_v")
    kmh = v * 3.6
    eng = cat(segs, "cc_lat") > 0.5
    sca = cat(segs, "sca") == 1
    ang = np.abs(cat(segs, "cs_ang"))
    bang = np.abs(cat(segs, "ang"))
    tq = np.abs(cat(segs, "cs_tq"))
    rate_c = np.abs(cat(segs, "rate_c"))
    gear = cat(segs, "cs_gear")
    req = np.abs(np.nan_to_num(cat(segs, "cc_req")))   # openpilot's own commanded torque, |.|
    n = len(b4)

    a512 = (b4 & BIT_A512) != 0
    a1024 = (b4 & BIT_A1024) != 0
    damp = (b4 & BIT_DAMP) != 0
    rate = (b4 & BIT_RATE) != 0
    live = (b4 & BIT_LIVE) != 0

    # ---------------------------------------------------------------- 0. liveness / invariant ----
    hdr("§0  LIVENESS AND THE MONOTONE INVARIANT -- read this before anything else")
    void = int(((b4 & PROBE_MASK) == 0).sum())
    illegal = int(np.count_nonzero([(int(x) & PROBE_MASK) not in LEGAL for x in np.unique(b4)]))
    viol = int((a1024 & ~a512).sum())
    vals, cnts = np.unique(b4, return_counts=True)
    print(f"  frames           : {n}   ({dt.sum():.1f} s of 0x14A at ~100 Hz)")
    print(f"  distinct byte4   : {[hex(int(x)) for x in vals]}  counts {[int(c) for c in cnts]}")
    print(f"  VOID (field == 0): {void} / {n}   -- the cave did not fire")
    print(f"  illegal payloads : {illegal} distinct values outside the 12 legal")
    print(f"  bit5 => bit6 VIOLATIONS (must be 0): {viol} / {n}")
    ok = (void == 0 and illegal == 0 and viol == 0)
    print(f"  ⇒ {'✅ the probe is LIVE and every frame is V72-legal' if ok else '🛑 HARD FAIL'}")
    print("  ⚠ ONE-WAY: a violation would falsify V72; holding does not PROVE it. The .rwd filename")
    print("     remains the pre-drive discriminator.")

    # ---------------------------------------------------------------- 1. `a` ---------------------
    hdr("§1  ★★★★ bit6 / bit5 -- `a` = gp-0x69a4, THE UNMEASURED WEIGHT (2-step thermometer)")
    for lab, m in (("ALL      ", np.ones(n, bool)), ("engaged  ", eng), ("manual   ", ~eng)):
        p6, k6, n6 = duty(a512, m)
        p5, k5, _ = duty(a1024, m)
        print(f"  {lab}: a>=512 {p6:8.4f}% ({k6}/{n6})   a>=1024 {p5:8.4f}% ({k5}/{n6})")
    print("\n  BY SPEED BIN (m/s):")
    bins = [(-1, 1, "standstill  <1"), (1, CREEP_MS, "creep    1-4"), (CREEP_MS, 11, "mid      4-11"),
            (11, HIGHWAY_MS, "  11-13.9"), (HIGHWAY_MS, 99, "highway >13.9")]
    print(f"  {'bin':>16s} {'frames':>8s} {'sec':>8s} {'a>=512':>10s} {'a>=1024':>10s} "
          f"{'eng a>=512':>12s}")
    for lo, hi, lab in bins:
        m = (v >= lo) & (v < hi)
        p6, k6, n6 = duty(a512, m)
        p5, _, _ = duty(a1024, m)
        pe, _, ne = duty(a512, m & eng)
        print(f"  {lab:>16s} {n6:8d} {dt[m].sum():8.1f} {p6:9.4f}% {p5:9.4f}% "
              f"{pe:11.4f}% (n={ne})")
    lo6 = int(a512.sum()); hi5 = int(a1024.sum())
    print(f"\n  ⇒ BRACKET, WHOLE ROUTE: `a` < 512 in {100.0 * (n - lo6) / n:.3f}% of frames, "
          f"in [512, 1024) in {100.0 * (lo6 - hi5) / n:.3f}%, >= 1024 in {100.0 * hi5 / n:.3f}%.")
    creep = (v < CREEP_MS)
    c6, kc, nc = duty(a512, creep)
    c5, kc5, _ = duty(a1024, creep)
    print(f"  ⇒ BRACKET AT CREEP (v < {CREEP_MS} m/s, n={nc}): `a` < 512 in {100 - c6:.3f}%, "
          f"[512,1024) in {c6 - c5:.3f}%, >= 1024 in {c5:.3f}%")
    ec6, _, enc = duty(a512, creep & eng)
    print(f"  ⇒ BRACKET AT ENGAGED CREEP (n={enc}): `a` >= 512 in {ec6:.4f}%")
    print("  ⚠ Two ONE-BIT comparators, not a measurement of `a`. Quote the BRACKET, not a value.")

    # where does bit6 fire at all?
    if lo6:
        segid = np.concatenate([np.full(len(d["t"]), d["_seg"]) for d in segs])
        u, c = np.unique(segid[a512], return_counts=True)
        print(f"  bit6 fires in segments: {dict(zip(u.astype(int).tolist(), c.tolist()))}")
        print(f"     speed there  : {v[a512].min():.2f}..{v[a512].max():.2f} m/s "
              f"({kmh[a512].min():.0f}..{kmh[a512].max():.0f} km/h)")
        print(f"     |cs_ang|     : {ang[a512].min():.1f}..{ang[a512].max():.1f} deg   "
              f"|tq| {tq[a512].min():.0f}..{tq[a512].max():.0f}")
        print(f"     engaged      : {100.0 * eng[a512].mean():.1f}%")
        # ★ WHAT SELECTS THE FIRING FRAMES? A one-bit thermometer cannot measure `a`, but it CAN
        # say which operating point pushes it over 0.5 -- and that names the producer's index.
        e = np.flatnonzero(np.diff(a512.astype(int)) != 0) + 1
        runs = np.split(np.flatnonzero(a512), np.searchsorted(np.flatnonzero(a512), e))
        runs = [r for r in runs if len(r)]
        print(f"     EPISODES     : {len(runs)} contiguous run(s), lengths "
              f"{[len(r) for r in runs][:12]} frames ({[round(len(r) / 100, 2) for r in runs][:12]} s)")
        for lab, x, unit in (("|cs_tq|", tq, "counts"), ("|rate_c|", rate_c, "deg/s"),
                             ("|cs_ang|", ang, "deg"), ("v", v, "m/s")):
            hiq = np.percentile(x[a512], [5, 50, 95])
            allq = np.percentile(x[eng & (v > HIGHWAY_MS)], [5, 50, 95])
            print(f"     {lab:>9s} at bit6=1: {hiq[0]:7.1f}/{hiq[1]:7.1f}/{hiq[2]:7.1f}  vs "
                  f"engaged-highway p5/50/95 {allq[0]:7.1f}/{allq[1]:7.1f}/{allq[2]:7.1f} {unit}")
        thr = np.percentile(tq[eng & (v > HIGHWAY_MS)], 99)
        print(f"     ⇒ every bit6=1 frame has |cs_tq| >= {tq[a512].min():.0f}; the engaged-highway "
              f"p99 of |cs_tq| is {thr:.0f} ⇒ `a` crosses 0.5 only under EXTREME sustained effort.")

    # ---------------------------------------------------------------- 1b. `a` vs ITS INDEX -------
    # ★★ F4-surface-lever traced `a`'s producer (the 10-segment LERP at 0x355C6 in FUN_000352b4) to
    #    index = abs( clamp(gp-0x4f60, +-cal 0xC6200) + gp-0x6b4a )   clamped +-0x6400
    # gp-0x4f60 = DRIVER column torque (Sensor B, raw); gp-0x6b4a = the type-8 MIXER output torque.
    # ⇒ the bus proxy for the index is |driver torque + commanded torque|, and near a centred wheel
    # with light hands BOTH terms are small. This block prices `a` against each term separately and
    # against the sum, because that is the operator's exact conditional (near centre, engaged,
    # while commanding).
    hdr("§1b  `a` CONDITIONED ON WHAT INDEXES IT -- |driver torque|, |command|, |angle|")
    # the operator reports a ~+/-4 deg sensor offset; estimate it from straight highway cruising
    off = float(np.median(cat(segs, "cs_ang")[(v > HIGHWAY_MS) & (np.abs(cat(segs, "rate_c")) < 5)]))
    angc = np.abs(cat(segs, "cs_ang") - off)
    print(f"  angle offset from straight-highway median cs_ang: {off:+.2f} deg  "
          f"(operator reports ~+/-4 deg); `angc` below is offset-corrected")
    e4 = np.abs(cat(segs, "e4tq"))          # 0x0E4 bytes 0:1 -- openpilot's COMMANDED torque
    both = np.abs(cat(segs, "tq") + cat(segs, "e4tq"))
    diff = np.abs(cat(segs, "tq") - cat(segs, "e4tq"))
    for lab, x, edges in (("|cs_tq| driver torque", tq, (0, 500, 1000, 1500, 2000, 2500, 3000, 1e9)),
                          ("|e4tq|  LKAS command ", e4, (0, 100, 300, 600, 1000, 2000, 1e9)),
                          ("|angc|  angle (corr) ", angc, (0, 4, 10, 30, 100, 1e9)),
                          ("|tq+e4tq| INDEX proxy", both, (0, 500, 1000, 1500, 2000, 2500,
                                                           3000, 1e9)),
                          ("|tq-e4tq| sign check ", diff, (0, 500, 1000, 1500, 2000, 2500,
                                                           3000, 1e9))):
        print(f"\n  bit6 (`a` >= 512) duty vs {lab}:")
        print(f"    {'bin':>16s} {'ALL':>22s} {'ENGAGED CREEP <4':>24s} {'ENGAGED HWY >13.9':>24s}")
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (x >= lo) & (x < hi)
            cells = []
            for sel in (m, m & eng & (v < CREEP_MS), m & eng & (v > HIGHWAY_MS)):
                p, k, nn = duty(a512, sel)
                cells.append(f"{p:6.2f}% ({k:5d}/{nn:6d})" if nn else f"{'EMPTY':>21s}")
            rng = f"{lo:.0f}-{hi:.0f}" if hi < 1e9 else f">={lo:.0f}"
            print(f"    {rng:>16s} {cells[0]:>22s} {cells[1]:>24s} {cells[2]:>24s}")
    print("\n  ★ THE OPERATOR'S EXACT REGIME -- engaged, moving creep 0.5-4 m/s, near centre:")
    nc = eng & (v >= 0.5) & (v < CREEP_MS) & (angc <= 10)
    p, k, nn = duty(a512, nc)
    print(f"     |angc| <= 10 deg: n={nn} ({dt[nc].sum():.1f} s)   bit6 duty {p:.4f}% ({k})")
    if nn:
        for lab, x in (("|cs_tq|", tq), ("|e4tq|", e4), ("|tq+e4tq|", both)):
            q = np.percentile(x[nc], [50, 95, 99, 100])
            print(f"       {lab:>10s} p50/p95/p99/max = {q[0]:7.0f} {q[1]:7.0f} {q[2]:7.0f} "
                  f"{q[3]:7.0f}")
    print("     ⇒ compare against the engaged-HIGHWAY frames where `a` DOES cross 0.5.")

    # ---------------------------------------------------------------- 2. the damper --------------
    hdr("§2  bit4 -- |gp-0x6bd0| >= 64: IS LEVER B (the base damper) IN FORCE? "
        "WITH ITS OWN POSITIVE CONTROL")
    for lab, m, expect in ((f"below {FACTORC_ONSET_KMH:.0f} km/h  (THE TEST)   ",
                            kmh < FACTORC_ONSET_KMH,
                            "stock is a HARD ZERO here -- any firing is LEVER B"),
                           (f"at/above {FACTORC_ONSET_KMH:.0f} km/h (CONTROL)",
                            kmh >= FACTORC_ONSET_KMH,
                            "stock ALREADY damps here -- a silent rung is BROKEN, not null")):
        p, k, nn = duty(damp, m)
        print(f"  {lab}: {p:7.4f}%  ({k} / {nn}, {dt[m].sum():.1f} s)   {expect}")
    for lab, m in (("engaged creep (<4 m/s)", eng & creep), ("manual creep  (<4 m/s)", ~eng & creep),
                   ("engaged highway       ", eng & (v > HIGHWAY_MS))):
        p, k, nn = duty(damp, m)
        print(f"  {lab}: {p:7.4f}%  ({k} / {nn})")
    hi_m = kmh >= FACTORC_ONSET_KMH
    if hi_m.sum() >= 128 and not damp[hi_m].any():
        print("\n  🛑🛑 THE POSITIVE CONTROL FAILED. Stock firmware produces non-zero base-assist")
        print("       damping above 35 km/h, and this rung read ZERO in every one of those frames.")
        print("       Per the rung's OWN pre-registered decision rule, the creep reading is")
        print("       UNINTERPRETABLE: it cannot be read as 'Lever B is not in force'.")
        print("  ⚠ BUT THE CAVE IS DEMONSTRABLY LIVE (bit3 and bit6 both vary), so this is a")
        print("     reading OF gp-0x6bd0, not a dead probe. Either the cell is not the damper's")
        print("     post-clamp output, or |gp-0x6bd0| < 64 everywhere on this drive.")

    # ---------------------------------------------------------------- 3. the rate axis -----------
    hdr(f"§3  📋 bit3 -- gp-0x6ac0 >= 512 counts = {RATE_DEGS:.2f} deg/s. "
        f"PRE-REGISTERED at {PREREG_BIT3}% engaged")
    pe, ke, ne = duty(rate, eng)
    pa, ka, _ = duty(rate, np.ones(n, bool))
    pm, km, nm = duty(rate, ~eng)
    print(f"  engaged duty : {pe:8.4f}%  ({ke} / {ne})   📋 predicted {PREREG_BIT3}%")
    print(f"  manual  duty : {pm:8.4f}%  ({km} / {nm})")
    print(f"  all frames   : {pa:8.4f}%  ({ka} / {n})")
    if pe == 0.0:
        print("  🛑 ZERO ENGAGED -- indicts the cave, not the scale.")
    elif abs(pe - PREREG_BIT3) <= 0.5 * PREREG_BIT3:
        print("  ✅ within a factor of 1.5 of the pre-registration.")
    else:
        print("  ⚠ OUTSIDE the pre-registration. Report the number; do not re-explain it after the")
        print("     fact -- that is exactly what pre-registration exists to prevent.")
    # ---- frame-for-frame against the BUS -----------------------------------------------------
    print(f"\n  FRAME-FOR-FRAME vs bus |rate_c| >= {RATE_DEGS:.2f} deg/s "
          "(same 0x14A frame, so alignment is exact):")
    busfast = rate_c >= RATE_DEGS
    tp = int((rate & busfast).sum()); fp = int((rate & ~busfast).sum())
    fn = int((~rate & busfast).sum()); tn = int((~rate & ~busfast).sum())
    print(f"     bit3=1 & bus>=thr {tp:7d}   bit3=1 & bus<thr {fp:7d}")
    print(f"     bit3=0 & bus>=thr {fn:7d}   bit3=0 & bus<thr {tn:7d}")
    print(f"     agreement {100.0 * (tp + tn) / n:.4f}%   "
          f"MCC-style: recall {100.0 * tp / max(tp + fn, 1):.2f}%  "
          f"precision {100.0 * tp / max(tp + fp, 1):.2f}%")
    # what bus threshold best matches the rung -- an independent read of the axis scale
    cand = np.arange(20.0, 400.0, 1.0)
    agree = [float(((rate_c >= c) == rate).mean()) for c in cand]
    best = cand[int(np.argmax(agree))]
    print(f"     BEST-MATCHING bus threshold: {best:.0f} deg/s (agreement {100 * max(agree):.3f}%) "
          f"vs the {RATE_DEGS:.1f} deg/s the 4.7121 scale predicts")
    print(f"     ⇒ implied counts-per-deg-s if bit3 is truly `>= 512 counts`: "
          f"{512.0 / best:.3f}  (settled value 4.7121)")
    # distribution of bus rate on each side of the rung
    for lab, m in (("bit3 SET  ", rate), ("bit3 CLEAR", ~rate)):
        if m.sum():
            q = np.percentile(rate_c[m], [5, 50, 95])
            print(f"     |rate_c| where {lab}: p5 {q[0]:7.1f}  median {q[1]:7.1f}  "
                  f"p95 {q[2]:7.1f} deg/s   (n={int(m.sum())})")

    # ---------------------------------------------------------------- 4. exposure census ---------
    hdr("§4  EXPOSURE CENSUS -- 🛑 'EMPTY' IS NOT 'NULL'")
    print(f"  total                                    : {dt.sum():9.1f} s  ({n} frames)")
    print(f"  engaged (cc_lat)                         : {dt[eng].sum():9.1f} s  "
          f"({int(eng.sum())})   sca agrees {100.0 * (eng == sca).mean():.3f}%")
    print(f"  manual                                   : {dt[~eng].sum():9.1f} s  "
          f"({int((~eng).sum())})")
    rows = [
        ("creep        v < 4 m/s (incl. standstill)", v < CREEP_MS),
        ("  ... engaged", (v < CREEP_MS) & eng),
        ("  ... manual", (v < CREEP_MS) & ~eng),
        ("MOVING creep 0.5 <= v < 4 m/s  ★ grind #1's regime", (v >= 0.5) & (v < CREEP_MS)),
        ("  ... engaged", (v >= 0.5) & (v < CREEP_MS) & eng),
        ("  ... engaged, near centre |cs_ang| <= 10",
         (v >= 0.5) & (v < CREEP_MS) & eng & (ang <= 10)),
        ("  ... engaged, near centre AND |cc_req| > 0.05",
         (v >= 0.5) & (v < CREEP_MS) & eng & (ang <= 10) & (req > 0.05)),
        ("  ... manual", (v >= 0.5) & (v < CREEP_MS) & ~eng),
        ("mid       4 <= v < 11", (v >= CREEP_MS) & (v < 11)),
        ("  ... engaged", (v >= CREEP_MS) & (v < 11) & eng),
        ("highway     v > 13.9 m/s", v > HIGHWAY_MS),
        ("  ... engaged", (v > HIGHWAY_MS) & eng),
        (f"above {FACTORC_ONSET_KMH:.0f} km/h (damper control)", kmh >= FACTORC_ONSET_KMH),
        ("ENGAGED CREEP near centre |cs_ang|<=10", (v < CREEP_MS) & eng & (ang <= 10)),
        ("   ... same, bus |ang| <= 10", (v < CREEP_MS) & eng & (bang <= 10)),
        ("ENGAGED CREEP cornering |ang|>=100 & |tq|>=1200",
         (v < CREEP_MS) & eng & (ang >= 100) & (tq >= 1200)),
        ("   ... cornering, |ang|>=100 only", (v < CREEP_MS) & eng & (ang >= 100)),
        ("   ... cornering, |tq|>=1200 only", (v < CREEP_MS) & eng & (tq >= 1200)),
        ("standstill v < 0.1", v < 0.1),
        ("in park (gear==1)", gear == 1.0),
        ("in reverse (gear==4)", gear == 4.0),
    ]
    for lab, m in rows:
        sec = dt[m].sum()
        flag = "   🛑 ZERO EXPOSURE -- unpowered, NOT a null" if m.sum() == 0 else ""
        print(f"  {lab:<46s}: {sec:9.1f} s  ({int(m.sum()):7d}){flag}")
    print(f"\n  speed span: {v.min():.2f} .. {v.max():.2f} m/s "
          f"({kmh.min():.1f} .. {kmh.max():.1f} km/h)")

    # ---------------------------------------------------------------- 5. flight health -----------
    hdr("§5  FLIGHT HEALTH")
    sstat = cat(segs, "sstat")
    print(f"  ST==4 {int((sstat == 4).sum())}   ST==3 {int((sstat == 3).sum())}   "
          f"ST==0 {int((sstat == 0).sum())}")
    import json
    bad = {}
    for s in SEGS:
        f = CACHE / f"{PFX}{s}_events.json"
        if f.exists():
            for e in json.loads(f.read_text()):
                if e["immediate"] or e["soft"]:
                    bad[e["name"]] = bad.get(e["name"], 0) + 1
    print(f"  soft/immediate-disable events: {bad if bad else 'NONE'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
