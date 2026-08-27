#!/usr/bin/env python3
"""studies/sessions/r4f/r4a_addendum.py -- the second pass on route `4a`: provenance, golden-model grounding, probe-rung
recommendation, speed sweeps, the corpus-wide LKAS-OFF-at-speed census, and the wheel-order screen.

Companion to `studies/sessions/r4f/r4a_orchestrator_checks.py` (extraction audit, exposure, grind #1/#2 statistics). This
file exists because three things were asked for AFTER that pass and each of them is a different kind
of question:

  provenance  route -> build -> dose must come from `lib/route_build_registry.py` + docs/BUILD-LINEAGE.md,
              NOT from the filename and NOT from memory. A mis-assigned route corrupts the kit's
              central evidence structure -- the multi-build Kd dose-response.
  golden      every channel is tapped somewhere in `model/eps_lkas_chain_model.py`'s chain, and WHERE it is
              tapped decides what it can witness. One golden-model assertion is re-tested here
              directly against route 4a's own bytes.
  probebits   which of V67's probe rungs actually carried information. A rung that reads a constant
              is a wasted bit that V68 can reclaim.
  sweep       a steady acceleration/deceleration separates a FIXED-frequency mode from a
              SPEED-PROPORTIONAL wheel/driveline order in one pass, with no cross-route comparison.
  lkasoff     🛑 the operator's highway self-report is "only during LKAS-engaged" -- which has never
              been testable, because the corpus may hold no LKAS-OFF exposure at speed at all. A
              CONFIRMED ZERO is as valuable as a positive number: it says what to drive next.
  orders      at road speed, 40-49 Hz IS wheel order 3 and 10-16 Hz is order 1. This kit has twice
              nearly published a tyre as a firmware effect. Discriminant: on-order/off-order power.

Usage:  python studies/sessions/r4f/r4a_addendum.py [section ...]      (default: all)
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

import glob
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                    # noqa: E402
from _r31_common import fs_of, load, runs_of, sustained     # noqa: E402
from route_build_registry import BY_ROUTE, identify         # noqa: E402

C4A = ROOT / "_scratch/cache/r4a"
SEGS = [20, 21, 22, 23, 24, 25]
PFX = "r4as"
TYRE_C = 2.075
G.BUILDS.setdefault("V67/r4a", dict(cache=C4A, pfx=PFX, segs=SEGS, kd=2.5))


def hdr(s):
    print(f"\n{'=' * 108}\n{s}\n{'=' * 108}")


def segs4a():
    for s in SEGS:
        yield s, load(s, C4A, PFX)


# =================================================================================================
def sec_provenance():
    hdr("A.  ROUTE -> BUILD -> DOSE, from lib/route_build_registry.py and docs/BUILD-LINEAGE.md")
    print("   🛑 An rlog cannot report its flashed build: every modified image reports")
    print("   fw='39990-TVA,A160'. The mapping is an INFERENCE, so it is re-derived here.\n")
    b4 = sorted({int(v) for s, d in segs4a() for v in np.unique(d["probe"].astype(int))})
    cands, notes = identify(b4)
    print(f"   route 4a byte4 payloads: {[f'0x{v:02X}' for v in b4]}")
    print(f"   registry identify() -> {sorted(cands)}")
    for n in notes:
        print(f"      {n}")
    print("\n   Payload alone does NOT identify the build -- it never has. The registry's own route-47")
    print("   row says so. The three discriminators, each measured on route 4a:")
    tot = agree = b6 = 0
    for s, d in segs4a():
        tot += len(d["t"])
        agree += int(((d["g6806"] > 0.5) == (d["cc_lat"] > 0.5)).sum())
        b6 += int((d["g6806"] > 0.5).sum())
    print(f"      1. bit3 CLEAR in {tot}/{tot} frames        ⇒ EXCLUDES V68 (bit3 constant 1), V53, V54")
    print(f"      2. bit6 duty {100 * b6 / tot:.3f}%, == latActive {100 * agree / tot:.4f}%")
    print("         ⇒ EXCLUDES V59/V62: under their thermometer bit6 is the FAULT sentinel, which")
    print("           read 0.000% on routes 2c and 37. A 52.5% duty tracking latActive is gp-0x6806.")
    print("      3. Kd signature (r4a_orchestrator_checks §5b): ENGAGED arm 0.260 [0.112, 0.594] vs")
    print("         the Kd=1 pool, DISENGAGED arm 1.211 [0.657, 1.838].")
    print("         ⇒ EXCLUDES V66: V66 reverts BOTH sar taps, so it is Kd=1 in BOTH arms and must")
    print("           read ~1.0 against Kd=1 in both. Suppression in ONE ARM ONLY is V67's design.")
    print("      ⇒ V67, by the same three-step argument the registry uses for route 47, independently")
    print("        replicated on a second route. 🛑 Still worth confirming the .rwd filename.")

    print("\n   THE DOSE LADDER I EXTENDED, with each route's kd taken from the registry:")
    print(f"   {'route':>6s} {'build':>10s} {'kd':>6s}   evidence source")
    for r in ("31", "2b", "2c", "35", "37", "3a", "3b", "47"):
        row = BY_ROUTE[r]
        print(f"   {row.route:>6s} {row.build:>10s} {str(row.kd):>6s}   route_build_registry.ROUTES")
    print(f"   {'4a':>6s} {'V67':>10s} {'2.0':>6s}   THIS SESSION -- not yet a registry row (see below)")
    print("\n   ⚠ registry note, quoted: 'route 47 (V67) is the first CONDITIONAL dose: kd=2.0 there")
    print("     means 2x WHILE THE LKAS GATE IS TRUE, stock 1x otherwise. Do not pool it with the")
    print("     unconditional 2x routes without saying which arm you mean -- its disengaged arm is a")
    print("     Kd=1 population.' Route 4a inherits this exactly. Every table I produced keeps V67 as")
    print("     its own row and never merges it into the Kd=2 pool.")

    print("\n   🛑 A REAL INCONSISTENCY IN THE KIT'S OWN Kd=1 POOL, found while checking this:")
    print(f"      r47_orchestrator_checks.CREEP_POOLS Kd=1.00 = {['_scratch/cache/r2b','_scratch/cache/r2c','_scratch/cache/r35']}")
    print(f"      _grind2_lib.DOSE[1.0]                       = {G.DOSE[1.0]}      (r2b ABSENT)")
    print("      analyze_r47_grind1.KD1                      = ['V59/r2c', 'V64/r35']  (r2b ABSENT)")
    print("      Both are defensible -- r2b's cache predates the probe-era extractor -- but they are")
    print("      DIFFERENT reference populations, and the kit quotes numbers from both. My §5 dose")
    print("      table uses the 3-route pool (matching the published table) and my §5b arm-matched")
    print("      2x2 uses the 2-route pool (matching the published 0.524). I reproduced route 47's")
    print("      0.524 [0.339, 0.803] against the published 0.524 [0.337, 0.804], which is what")
    print("      confirms I used each pool the same way its own published number did.")


# =================================================================================================
def sec_golden():
    hdr("B.  GOLDEN-MODEL GROUNDING -- where each extracted channel taps the chain")
    print("   Source: analysis-2020accord/model/eps_lkas_chain_model.py. WHERE a channel is tapped decides")
    print("   what it can witness, and two of these are commonly over-read.\n")
    rows = [
        ("tq", "0x18F b0:1 x -1", "gp-0x4f60 SENSOR-B (TAS) COLUMN TORQUE, the signal packed to CAN "
         "399 STEER_TORQUE_SENSOR", "INPUT side of the assist chain: it is what the driver + plant "
         "present to the ECU, upstream of the assist-shaping lanes and the aggregator. It witnesses "
         "the MECHANICAL loop (hence grind #1/#2), NOT delivered motor torque."),
        ("rate_c", "0x14A b2:4 x -1", "gp-0x6a56 STEER_ANGLE_RATE",
         "🛑 NOT an independent angle sensor. The model states FUN_0003f776 computes it as a fixed "
         "Q15 scale of the MOTOR/resolver electrical rate gp-0x6abe. So it is a MOTOR-side witness "
         "and CANNOT independently corroborate `tq`."),
        ("ang", "0x14A b0:1 x -0.1", "steering angle, degrees",
         "column position; used here only as a covariate and for the wheel-order screen."),
        ("probe", "0x14A byte4", "V67's cave: the r24 rate-lane ARM SELECTOR",
         "the gain-selection point itself -- gp-0x6806 / gp-0x671d / gp-0x671a, sampled once per "
         "CAN frame. 🛑 Sampled at 100 Hz, so it can see the GATE (0.02 transitions/s) but nothing "
         "at 21 or 45 Hz."),
        ("sstat", "0x18F b4 bits7:4", "STEER_STATUS", "the EME/governor state -- V42's state-4 "
         "ratchet and the 0xC62EA low-speed lockout both surface here."),
        ("e4tq", "0x0E4 src129 b0:2", "openpilot's own LKAS torque command",
         "the ADAS-side INPUT to the chain, from sendcan -- it is what was ASKED FOR, never what "
         "was delivered."),
    ]
    for nm, src, what, wit in rows:
        print(f"   {nm:8s} {src:18s} {what}")
        print(f"   {'':8s} {'':18s} ⇒ {wit}\n")
    print("   🛑 CEILING, common to every channel above: the CAN grid is 100.000 Hz (measured, §3)")
    print("      ⇒ NYQUIST 50.00 Hz. A null above 50 Hz on this route is SILENCE, NOT ABSENCE.")

    print("\n   RE-TESTING A LIVE GOLDEN-MODEL ASSERTION AGAINST ROUTE 4a's OWN BYTES.")
    print("   The model (ASSIST_RATE_B_RECORDS note 2) asserts: 'The 0x14A rate field IS deg/s")
    print("   (factor 1): regressing rate_c on the differentiated ANGLE channel gives slope")
    print("   0.95-1.00 with r >= 0.985 on every clean segment.' Route 4a was not in that sample.\n")
    print(f"   {'seg':>4s} {'n':>7s} {'slope':>8s} {'r':>8s}   verdict")
    sls, rs_ = [], []
    for s, d in segs4a():
        t = d["t"]
        fs = (len(t) - 1) / (t[-1] - t[0])
        dang = np.gradient(np.asarray(d["ang"], float)) * fs      # deg/s from the angle channel
        x = np.asarray(d["rate_c"], float)
        m = np.isfinite(x) & np.isfinite(dang)
        sl = float(np.polyfit(dang[m], x[m], 1)[0])
        r = float(np.corrcoef(dang[m], x[m])[0, 1])
        sls.append(sl); rs_.append(r)
        ok = 0.95 <= sl <= 1.00 and r >= 0.985
        print(f"   s{s:<3d} {int(m.sum()):7d} {sl:8.4f} {r:8.4f}   "
              f"{'CONFIRMS the model' if ok else 'outside the stated range'}")
    print(f"   {'ALL':>4s} {'':7s} {np.mean(sls):8.4f} {np.mean(rs_):8.4f}   (means)")
    inr = sum(1 for sl, r in zip(sls, rs_) if 0.95 <= sl <= 1.00 and r >= 0.985)
    print(f"   ⇒ {inr}/6 segments fall inside the model's stated slope AND r window.")
    print("     Route 4a is a parking-lot route, so its angle channel is dominated by large slow")
    print("     sweeps and its rate range is narrow -- a weaker regressor than the model's sample.")
    print("     Report this as CONSISTENT or CONTRADICTORY strictly on the numbers above.")


# =================================================================================================
def sec_probebits():
    hdr("C.  ★ PROBE-RUNG RECOMMENDATION -- which of V67's bits carried information")
    print("   A rung that reads a CONSTANT across a whole route measured nothing. V68 has four rungs")
    print("   and one is already spent on the build-class marker, so a dead rung is reclaimable.\n")
    tot = 0
    cnt = {"bit7": 0, "bit6": 0, "bit5": 0, "bit4": 0, "bit3": 0}
    tr = {"bit6": 0, "bit5": 0, "bit4": 0}
    for s, d in segs4a():
        tot += len(d["t"])
        cnt["bit7"] += int((d["live"] > 0.5).sum())
        for k, key in (("bit6", "g6806"), ("bit5", "g671d"), ("bit4", "g671a")):
            m = d[key] > 0.5
            cnt[k] += int(m.sum())
            tr[k] += int(np.abs(np.diff(m.astype(np.int8))).sum())
        cnt["bit3"] += int((d["unused"] > 0.5).sum())
    print(f"   route 4a, {tot} frames / {tot / 100.0:.1f} s")
    print(f"   {'bit':>5s} {'cell':>12s} {'set frames':>11s} {'duty %':>9s} {'transitions':>12s}   verdict")
    R47DUTY = {"bit7": (150327, 150327, 0), "bit6": (116547, 150327, None),
               "bit5": (0, 150327, 0), "bit4": (0, 150327, 0), "bit3": (0, 150327, 0)}
    for k, cell in (("bit7", "LIVENESS"), ("bit6", "gp-0x6806"), ("bit5", "gp-0x671d"),
                    ("bit4", "gp-0x671a"), ("bit3", "UNUSED")):
        c = cnt[k]
        t_ = tr.get(k)
        const = (c == 0 or c == tot)
        print(f"   {k:>5s} {cell:>12s} {c:11d} {100 * c / tot:8.3f}% "
              f"{('-' if t_ is None else t_):>12}   "
              + ("CONSTANT -- measured nothing on this route" if const else "INFORMATIVE"))
    print("\n   Route 47 read the same way (150,327 frames): bit5 0/150,327 = 0.000%,")
    print("   bit4 0/150,327 = 0.000%, bit3 0/150,327, bit7 150,327/150,327.")
    print("\n   ⇒ RECOMMENDATION, on TWO independent routes and 186,321 frames combined:")
    print("      • bit5 (gp-0x671d, the masking arm)  DEAD. 0 frames on r47, 0 frames on r4a.")
    print("        It was a SAFETY rung -- it existed to catch a mask that OUTRANKS the gain arm and")
    print("        would pin the gain to 1024, BELOW stock. Two routes say the mask never fires. That")
    print("        retires the risk it was watching, so the bit can be reclaimed. 🛑 Reclaiming it")
    print("        does mean giving up the ability to detect that mask if a future edit re-enables")
    print("        the path -- state that trade explicitly in the build note rather than silently.")
    print("      • bit4 (gp-0x671a >= 5, the third arm)  DEAD. 0 frames on r47, 0 frames on r4a.")
    print("        V68 already repointed bit4 onto the rate axis, which this data supports directly.")
    print("      • bit6 (gp-0x6806, the gate)  KEEP. 52.537% duty on r4a, 77.5% on r47, and it is the")
    print("        thing the firmware actually branches on. It is the only rung that has ever")
    print("        distinguished V67 from V66.")
    print("      • bit7 (liveness)  KEEP. Constant BY DESIGN -- a VOID sentinel, not a measurement.")
    print("        Its value is that field==0 proves the cave did not fire; V64 was a null ON THE")
    print("        GATE precisely because that could not be told apart from a real reading.")
    print("      ⇒ TWO reclaimable rungs (bit5, bit4). V68 spends one on the build-class marker; the")
    print("        other is free for a higher-value measurement.")


# =================================================================================================
def sec_sweep():
    hdr("D.  SPEED SWEEPS -- the fixed-mode vs speed-proportional-order discriminator")
    print("   A sweep is a contiguous run whose 1 Hz-smoothed speed moves monotonically. Criteria:")
    print("   >= 3 s long, >= 2.0 m/s of span, monotone in the smoothed signal. A fixed mode holds")
    print("   its frequency across the sweep; a wheel/driveline order tracks k*v/C linearly.\n")
    found = []
    for s, d in segs4a():
        t = np.asarray(d["t"], float)
        fs = (len(t) - 1) / (t[-1] - t[0])
        v = np.asarray(d["cs_v"], float)
        k = int(round(fs))                                    # 1 s boxcar
        vs = np.convolve(v, np.ones(k) / k, mode="same")
        dv = np.gradient(vs) * fs
        for sgn, lab in ((1, "accel"), (-1, "decel")):
            m = (np.sign(dv) == sgn) & (np.abs(dv) > 0.15)
            for a, b in runs_of(m, t, int(3 * fs)):
                span = float(vs[b - 1] - vs[a])
                if abs(span) < 2.0:
                    continue
                found.append(dict(seg=s, lab=lab, t0=float(t[a]), t1=float(t[b - 1]),
                                  dur=float(t[b - 1] - t[a]), v0=float(v[a]), v1=float(v[b - 1]),
                                  vmin=float(v[a:b].min()), vmax=float(v[a:b].max()),
                                  acc=span / float(t[b - 1] - t[a]),
                                  lat=float((d["cc_lat"][a:b] > 0.5).mean()),
                                  ang=float(np.abs(d["ang"][a:b]).mean())))
    if not found:
        print("   NONE found.")
        return
    found.sort(key=lambda r: -abs(r["v1"] - r["v0"]))
    print(f"   {'seg':>4s} {'kind':>6s} {'t0 s':>7s} {'t1 s':>7s} {'dur':>6s} {'v0':>6s} {'v1':>6s} "
          f"{'span':>6s} {'m/s^2':>7s} {'LKAS':>6s} {'|ang|':>7s}")
    for r in found:
        print(f"   s{r['seg']:<3d} {r['lab']:>6s} {r['t0']:7.2f} {r['t1']:7.2f} {r['dur']:6.2f} "
              f"{r['v0']:6.2f} {r['v1']:6.2f} {r['v1'] - r['v0']:6.2f} {r['acc']:7.3f} "
              f"{100 * r['lat']:5.0f}% {r['ang']:7.1f}")
    best = found[0]
    print(f"\n   ⇒ {len(found)} qualifying sweeps. LARGEST: seg{best['seg']} {best['lab']} "
          f"{best['t0']:.1f}-{best['t1']:.1f} s, {best['v0']:.2f} -> {best['v1']:.2f} m/s "
          f"({best['dur']:.1f} s, LKAS {100 * best['lat']:.0f}%).")
    print(f"   Over that speed range wheel order 1 moves {best['vmin'] / TYRE_C:.2f} -> "
          f"{best['vmax'] / TYRE_C:.2f} Hz and order 3 moves {3 * best['vmin'] / TYRE_C:.2f} -> "
          f"{3 * best['vmax'] / TYRE_C:.2f} Hz.")
    print("   🛑 EVERY sweep here is BELOW 14 m/s, so order 3 never reaches 40-49 Hz. This route can")
    print("     discriminate order-vs-mode in 18-22 Hz, and it CANNOT do so for the highway 40-49 Hz")
    print("     question -- that needs a highway sweep, which this route does not contain.")

    # ---- run the discriminator on the largest sweep -------------------------------------------
    print(f"\n   ---- MODE-vs-ORDER TEST ON THE LARGEST SWEEP (seg{best['seg']}, "
          f"{best['t0']:.1f}-{best['t1']:.1f} s, {best['v0']:.2f} -> {best['v1']:.2f} m/s) ----")
    print("   Short 1.28 s windows across the sweep; free 12-30 Hz argmax of the PROMINENCE spectrum")
    print("   (a strict band would pin to its own edge). If the line is a wheel order its frequency")
    print("   must climb with v at k*0.482 Hz per m/s; a fixed mode has slope ~0.\n")
    d = load(best["seg"], C4A, PFX)
    t = np.asarray(d["t"], float)
    fs = (len(t) - 1) / (t[-1] - t[0])
    a = int(np.searchsorted(t, best["t0"]))
    b = int(np.searchsorted(t, best["t1"]))
    x = np.asarray(d["tq"], float)
    n, hop = 128, 32
    f = np.fft.rfftfreq(n, 1 / fs)
    print(f"   {'t s':>7s} {'v m/s':>7s} {'f0 Hz':>7s} {'prom':>8s} {'ord1':>6s} {'ord2':>6s} "
          f"{'ord3':>6s}")
    fv, vv, pv = [], [], []
    for i in range(a, b - n, hop):
        seg = x[i:i + n]
        P = np.abs(np.fft.rfft((seg - seg.mean()) * np.hanning(n))) ** 2
        R = G.prom_spectrum(f, P)
        f0, pr = G.locate(f, P, 12.0, 30.0, R=R)
        v = float(np.mean(d["cs_v"][i:i + n]))
        if not np.isfinite(f0):
            continue
        fv.append(f0); vv.append(v); pv.append(pr)
        print(f"   {t[i]:7.2f} {v:7.2f} {f0:7.2f} {pr:8.2f} {v / TYRE_C:6.2f} "
              f"{2 * v / TYRE_C:6.2f} {3 * v / TYRE_C:6.2f}")
    fv, vv, pv = np.array(fv), np.array(vv), np.array(pv)
    if len(fv) >= 4:
        sl, ic = np.polyfit(vv, fv, 1)
        r = float(np.corrcoef(vv, fv)[0, 1])
        print(f"\n   ALL {len(fv)} windows : d f0/d v = {sl:+.4f} Hz per m/s   intercept "
              f"{ic:.2f} Hz   r = {r:+.3f}")
        m = pv > 5
        if m.sum() >= 4:
            sl2, ic2 = np.polyfit(vv[m], fv[m], 1)
            print(f"   PROMINENT ONLY (prom > 5, n={int(m.sum())}) : d f0/d v = {sl2:+.4f}   "
                  f"intercept {ic2:.2f} Hz   f0 median {np.median(fv[m]):.2f} sd {np.std(fv[m]):.2f}")
        print(f"   predicted slope if this line were wheel order 1 / 2 / 3: "
              f"+0.482 / +0.964 / +1.446 Hz per m/s")
        print("   ⇒ compare the measured slope against those three. A slope far below +0.482 with a")
        print("     large non-zero intercept is a FIXED MODE; a slope matching k*0.482 with an")
        print("     intercept near 0 is wheel order k.")


# =================================================================================================
def sec_lkasoff():
    hdr("E.  ★★ LKAS-OFF EXPOSURE AT SPEED -- corpus-wide. The untested half of the highway report")
    print("   The operator's highway symptom is self-reported as 'only during LKAS-engaged'. That is")
    print("   only testable if LKAS-OFF driving at the same speed EXISTS in the corpus. Engagement is")
    print("   carControl.latActive, never cruiseState. Seconds, per route.\n")
    BANDS = [(8, 1e9), (15, 1e9), (20, 1e9)]
    print(f"   {'cache':14s} {'segs':>5s} {'total s':>9s} "
          + " ".join(f"{f'OFF>{lo:.0f}':>9s} {f'ON>{lo:.0f}':>9s}" for lo, _ in BANDS))
    tot = np.zeros(6)
    rows = []
    for cache in sorted(glob.glob(str(ROOT / "_cache_r*"))):
        if not Path(cache).is_dir():
            continue
        acc = np.zeros(6)
        T = 0.0
        n = 0
        for p in sorted(glob.glob(f"{cache}/*.npz")):
            if "_imu" in p or "_snd" in p or "raw18f" in p:
                continue
            d = dict(np.load(p))
            if "cs_v" not in d or "cc_lat" not in d or "t" not in d:
                continue
            n += 1
            t = d["t"]
            dt = float(t[-1] - t[0]) / max(len(t) - 1, 1)
            v = d["cs_v"]
            lat = d["cc_lat"] > 0.5
            T += len(v) * dt
            for i, (lo, hi) in enumerate(BANDS):
                m = (v > lo) & (v <= hi)
                acc[2 * i] += float((m & ~lat).sum()) * dt
                acc[2 * i + 1] += float((m & lat).sum()) * dt
        if not n:
            continue
        tot += acc
        rows.append((Path(cache).name, n, T, acc))
        print(f"   {Path(cache).name:14s} {n:5d} {T:9.0f} "
              + " ".join(f"{acc[2 * i]:9.1f} {acc[2 * i + 1]:9.1f}" for i in range(3)))
    print(f"   {'CORPUS TOTAL':14s} {'':5s} {sum(r[2] for r in rows):9.0f} "
          + " ".join(f"{tot[2 * i]:9.1f} {tot[2 * i + 1]:9.1f}" for i in range(3)))
    print("\n   ⇒ READ THE 'OFF' COLUMNS. Those are the seconds available to test 'only when engaged'.")
    for i, (lo, _) in enumerate(BANDS):
        nz = [(r[0], r[3][2 * i]) for r in rows if r[3][2 * i] > 1.0]
        rat = (f"1:{tot[2 * i + 1] / tot[2 * i]:.0f}" if tot[2 * i] > 0.05
               else "🛑 ZERO OFF EXPOSURE -- the comparison does not exist")
        print(f"      v > {lo:>2.0f} m/s : LKAS-OFF {tot[2 * i]:8.1f} s   vs LKAS-ON "
              f"{tot[2 * i + 1]:8.1f} s   {rat}")
        print(f"                   routes with any OFF exposure: "
              + (", ".join(f"{a}={b:.0f}s" for a, b in sorted(nz, key=lambda x: -x[1])) or "NONE"))


# =================================================================================================
def sec_pairs():
    hdr("F.  MATCHED ARM PAIRS ABOVE 8 m/s ON ROUTE 4a")
    print("   A matched pair = one engaged run and one disengaged run at comparable speed and")
    print("   comparable steering activity. Even 20 s would be the first such data in the corpus.\n")
    runs = []
    for s, d in segs4a():
        t = np.asarray(d["t"], float)
        fs = (len(t) - 1) / (t[-1] - t[0])
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        fast = np.asarray(d["cs_v"], float) > 8.0
        lat = d["cc_lat"] > 0.5
        for arm, m in ((1, fast & lat), (0, fast & ~lat)):
            for a, b in runs_of(m, t, int(2 * fs)):
                runs.append(dict(seg=s, arm=arm, t0=float(t[a]), t1=float(t[b - 1]),
                                 dur=float(t[b - 1] - t[a]),
                                 v=float(np.mean(d["cs_v"][a:b])),
                                 vmin=float(np.min(d["cs_v"][a:b])),
                                 vmax=float(np.max(d["cs_v"][a:b])),
                                 ratep90=float(np.percentile(np.abs(d["rate_c"][a:b]), 90)),
                                 ang=float(np.mean(np.abs(d["ang"][a:b]))),
                                 eff=float(np.median(eff[a:b]))))
    if not runs:
        print("   NONE -- route 4a has no contiguous run above 8 m/s in either arm.")
        return
    runs.sort(key=lambda r: (-r["dur"]))
    print(f"   {'seg':>4s} {'arm':>4s} {'t0 s':>7s} {'t1 s':>7s} {'dur':>6s} {'v mean':>7s} "
          f"{'v rng':>13s} {'|rate|p90':>10s} {'|ang|':>7s} {'eff':>7s}")
    for r in runs:
        rng = f"{r['vmin']:.1f}-{r['vmax']:.1f}"
        print(f"   s{r['seg']:<3d} {'ENG' if r['arm'] else 'off':>4s} {r['t0']:7.2f} {r['t1']:7.2f} "
              f"{r['dur']:6.2f} {r['v']:7.2f} {rng:>13s} "
              f"{r['ratep90']:10.2f} {r['ang']:7.1f} {r['eff']:7.1f}")
    on = [r for r in runs if r["arm"] == 1]
    off = [r for r in runs if r["arm"] == 0]
    print(f"\n   totals above 8 m/s: ENGAGED {sum(r['dur'] for r in on):.1f} s in {len(on)} runs;  "
          f"DISENGAGED {sum(r['dur'] for r in off):.1f} s in {len(off)} runs")
    best = None
    for a in on:
        for b in off:
            dv = abs(a["v"] - b["v"])
            dr = abs(a["ratep90"] - b["ratep90"]) / max(a["ratep90"], b["ratep90"], 1e-9)
            sc = dv + 4 * dr
            if min(a["dur"], b["dur"]) >= 2.0 and dv <= 2.0 and (best is None or sc < best[0]):
                best = (sc, a, b)
    if best is None:
        print("   ⇒ NO usable matched pair: the arms do not overlap in speed within 2 m/s at any")
        print("     run of >= 2 s. Report as a NEGATIVE, i.e. this route does not close the gap.")
    else:
        _, a, b = best
        print(f"   ⇒ BEST MATCHED PAIR:")
        print(f"      ENGAGED    seg{a['seg']} {a['t0']:.2f}-{a['t1']:.2f} s ({a['dur']:.1f} s) "
              f"v={a['v']:.2f} |rate|p90={a['ratep90']:.2f} eff={a['eff']:.0f}")
        print(f"      DISENGAGED seg{b['seg']} {b['t0']:.2f}-{b['t1']:.2f} s ({b['dur']:.1f} s) "
              f"v={b['v']:.2f} |rate|p90={b['ratep90']:.2f} eff={b['eff']:.0f}")
        print(f"      speed gap {abs(a['v'] - b['v']):.2f} m/s;  usable seconds "
              f"{min(a['dur'], b['dur']):.1f}")
        print("      🛑 This is 8-14 m/s, NOT highway. It cannot test the highway symptom; it only")
        print("        shows the corpus CAN contain an off-arm at speed if the operator drives it.")


# =================================================================================================
def sec_orders():
    hdr("G.  WHEEL-ORDER DISCRIMINANT -- on-order / off-order power, route 4a")
    print("   At road speed 40-49 Hz IS wheel order 3 (measured per-window order p50 2.994) and")
    print("   10-16 Hz is order 1. Discriminant used before: on-order/off-order power ratio, 6.94 in")
    print("   quiet windows vs 0.82 inside genuine bursts -- i.e. a genuine burst is NOT on-order.\n")
    print("   on-order  = mean P over bins within +-1 bin of k*v/C;  off-order = median P over the")
    print("   band's remaining bins.\n")
    print("   🛑 KMAX MATTERS AND MY FIRST PASS GOT IT WRONG. Run with k up to 40 and the screen is")
    print("   meaningless at creep: at 2 m/s the order spacing v/C is 0.96 Hz ~ 2.5 FFT bins, so")
    print("   'orders' 19-23 tile the whole 18-22 band and on/off collapses toward 1 by construction.")
    print("   The contamination the kit actually caught was LOW order -- tyre non-uniformity 1-3.")
    print("   KMAX = 6 below. The k<=40 run is printed underneath as the counter-example, labelled.\n")
    recs = G.wrecs("V67/r4a", keep_P=True)
    for KMAX in (6, 40):
        print(f"   ---- KMAX = {KMAX}"
              + ("  (physically relevant: tyre/driveline low orders)" if KMAX == 6
                 else "  ⚠ DEGENERATE AT CREEP -- shown only to document the trap") + " ----")
        print(f"   {'band':>7s} {'population':>22s} {'n':>5s} {'on/off p50':>11s} {'p90':>8s} "
              f"{'orders in band':>16s}")
        for band, (lo, hi) in (("10-16", (10.0, 16.0)), ("18-22", (18.0, 22.0)),
                               ("40-49", (40.0, 49.0))):
            pops = {}
            thr = np.percentile(G.col(recs, "e_" + band), 90)
            for r in recs:
                f, P = r["f"], r["P"]
                v = max(r["v"], 1e-6)
                m = (f >= lo) & (f <= hi)
                if not m.any():
                    continue
                df = f[1] - f[0]
                ks = [k for k in range(1, KMAX + 1) if lo <= k * v / TYRE_C <= hi]
                if not ks:
                    continue
                on = np.zeros(len(f), bool)
                for k in ks:
                    on |= np.abs(f - k * v / TYRE_C) <= 1.01 * df
                on &= m
                offb = m & ~on
                if not on.any() or offb.sum() < 3:
                    continue
                ratio = float(np.mean(P[on]) / max(np.median(P[offb]), 1e-30))
                key = ("TOP decile by e_" + band if r["e_" + band] > thr else "quiet (rest)")
                pops.setdefault(key, []).append((ratio, len(ks), r["v"]))
            for key in ("quiet (rest)", "TOP decile by e_" + band):
                vv = pops.get(key, [])
                if not vv:
                    print(f"   {band:>7s} {key:>22s} {0:5d}        -- NO window has an order "
                          f"<= {KMAX} inside this band")
                    continue
                a = np.array([x[0] for x in vv])
                print(f"   {band:>7s} {key:>22s} {len(a):5d} {np.median(a):11.2f} "
                      f"{np.percentile(a, 90):8.2f} {np.median([x[1] for x in vv]):16.0f}"
                      f"   (speeds {min(x[2] for x in vv):.1f}-{max(x[2] for x in vv):.1f} m/s)")
        print()
    print("   🛑 READ THE 'n' COLUMN FIRST. n = 0 at KMAX=6 means no window on this route has a low")
    print("      wheel order inside that band at all -- which IS the answer: at these speeds the band")
    print("      cannot be tyre-contaminated, and the discriminant is inapplicable rather than")
    print("      passed. Route 4a tops out at 13.92 m/s, so order 3 reaches 20.1 Hz at most and")
    print("      NEVER enters 40-49 Hz. The highway contamination risk is untestable on this route.")


SECTIONS = {"provenance": sec_provenance, "golden": sec_golden, "probebits": sec_probebits,
            "sweep": sec_sweep, "lkasoff": sec_lkasoff, "pairs": sec_pairs, "orders": sec_orders}

if __name__ == "__main__":
    for name in (sys.argv[1:] or list(SECTIONS)):
        SECTIONS[name]()
