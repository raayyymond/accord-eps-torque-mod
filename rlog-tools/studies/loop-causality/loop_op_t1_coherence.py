#!/usr/bin/env python3
"""T1 -- PHASE-RESOLVED COHERENCE AND TRANSFER, openpilot's 0x0E4 command <-> the torsion bar.

This is the measurement `docs/STATE.md` says is missing:
    "correlated +0.93 at lag 0 with the bar ... [BELIEF] an echo, not a cause ...
     Settling it needs a phase-resolved coherence, not the lag-0 correlation that was run."

===================================================================================================
WHY THE GROUP DELAY OF H1 ANSWERS THE DIRECTION QUESTION -- the closed-loop algebra, in full
===================================================================================================
Let x = cmd (openpilot's 0x0E4), y = bar.  The loop, if it exists, is

    y = G*x + d        G = EPS+plant transfer, d = everything driving the bar that is not the
                           command (road, driver, EPS-internal limit cycle)
    x = C*y + r        C = openpilot's own controller acting on what it measures, r = openpilot's
                           exogenous input (the lane model / desired curvature)

Solving and forming the standard H1 estimator  H1 = Sxy/Sxx  with r and d uncorrelated:

    Sxx = (|C|^2 * Sdd + Srr) / |1 - C*G|^2
    Sxy = (conj(C) * Sdd + G * Srr) / |1 - C*G|^2
    H1  = (conj(C)*Sdd + G*Srr) / (|C|^2*Sdd + Srr)

  * Srr dominates (openpilot's own exogenous demand is the source)  =>  H1 -> G
        arg(G) falls with f at the ACTUATOR delay  =>  group delay POSITIVE.
  * Sdd dominates (the bar content originates in the EPS/plant)     =>  H1 -> conj(C)/|C|^2 = 1/C
        C is causal with openpilot's own reaction lag tau_C, so 1/C has phase +w*tau_C
        =>  group delay NEGATIVE, and its magnitude IS openpilot's reaction lag.

⇒ **sign(group delay of H1) is the direction test**, and it is immune to the 180 deg sign ambiguity
between the corpus's `bar` (x -1.0) and the raw `cmd`, because a constant offset does not change a
slope.  [This is the standard closed-loop-identification bias, used here as the signal rather than
fought as a nuisance.]

BIAS DIRECTION OF THE UNMEASURED LATENCIES  (see `loop_op_lib` docstring)
    bus->EPS latch and bar-sample->0x18F-TX are both >= 0 and both push the measured delay POSITIVE.
    ⇒ a measured NEGATIVE delay is CONSERVATIVE evidence for ECHO.  A positive one is not.

CHANNELS AND CONTROLS
    cmd -> bar     the question
    cmd -> ang     the same question against the angle (0x14A, a different message => a different
                   set of unmeasured latencies; agreement across the two is a real check)
    ang -> cmd     the STRUCTURAL echo test: is openpilot's command a function of the angle it
                   measured?  A negative-delay cmd->bar and a positive-delay ang->cmd with matching
                   magnitudes are the same statement seen twice.
    cam -> bar     NULL CONTROL: the stock camera's own 0x0E4 on bus 2.  Same message class, same
                   100 Hz cadence, but its output is NOT applied to the rack.

Writes `_scratch/cache/loop_op/t1_coherence.json`.
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
import json
import sys

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 🛑 TWO CONTROLS THAT WERE PLANNED AND ARE UNINFORMATIVE -- measured, not assumed:
#   `cam` (the stock camera's 0x0E4 on bus 2) is IDENTICALLY ZERO on 24 of 27 engaged segments
#     (sd = 0.0, absmax = 0).  It only wakes on route 66 segs 7-10, which are DISENGAGED.
#     => it cannot serve as an engaged null.  Dropped.
#   MANUAL cmd -> bar is likewise vacuous: openpilot's own command is 0 counts when disengaged
#     (sd 0.0-29 ct, `creq` mean 0.000-0.008).  A null against a constant-zero input carries no
#     information about the engaged case, and is reported as REFUSED rather than as a clean null.
PAIRS = [("cmd", "bar"), ("cmd", "ang"), ("ang", "cmd"), ("rate_c", "cmd"), ("cmd", "rate_c")]
FINE = [("S2 micro-ratchet", 7.0, 9.0), ("S1 grind #1", 18.0, 22.0),
        ("the ring", 26.0, 31.0), ("grind #2", 40.0, 49.0)]


def ep_extra(d, i0, i1):
    """Per-episode covariates for the conditional splits in T4."""
    c = np.asarray(d["cmd"], float)[i0:i1 + 1]
    dc = np.abs(np.diff(c))
    return dict(cap_duty=float(np.mean(dc >= L.SLEW_CAP - 0.5)) if len(dc) else np.nan,
                amp_duty=float(np.mean(np.abs(c) >= L.STEER_MAX - 0.5)),
                cmd_absmean=float(np.mean(np.abs(c))))


def report(f, Sxx, Syy, Sxy, K, label, recs=None, boot=True):
    print(f"\n--- {label}   K = {K} episodes   g2_crit(K) = {L.g2_crit(K):.4f}")
    print(f"  {'band':>8} {'g2':>7} {'g2 CI':>18} {'|H|':>10} {'phase':>8} "
          f"{'tau_ms':>16} {'r2':>6} {'rmsY/rmsX':>10}")
    rows = {}
    for bn, (lo, hi) in L.BANDS.items():
        s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
        ci = {}
        if boot and recs and len(recs) >= 4:
            _, ci = L.boot_band(recs, lo, hi, nboot=1000)
        s["ci"] = {k: list(v) for k, v in ci.items()}
        g2ci = ci.get("g2", (np.nan, np.nan))
        tci = ci.get("tau_ms", (np.nan, np.nan))
        print(f"  {bn:>8} {s['g2']:7.4f} [{g2ci[0]:6.3f},{g2ci[1]:6.3f}] {s['H']:10.4g} "
              f"{s['ph']:8.1f} {s['tau_ms']:6.1f}[{tci[0]:5.1f},{tci[1]:5.1f}] "
              f"{s['r2']:6.3f} {s['ratio']:10.3g}")
        rows[bn] = s
    w = L.coh(Sxx, Syy, Sxy) * Sxx
    for nm, lo, hi in (("wideband 2-25", 2.0, 25.0), ("wideband 5-45", 5.0, 45.0)):
        tau, ph0, r2, nb = L.band_delay(f, Sxy, lo, hi, wgt=w)
        print(f"  {nm}: tau = {tau*1e3:+.2f} ms  intercept {ph0:+.1f} deg  r2 {r2:.3f}")
        rows[nm] = dict(tau_ms=tau * 1e3, phi0_deg=ph0, r2=r2, nbin=nb)
    return rows


def main():
    out = {"pairs": {}, "null": {}, "per_route": {}}

    for xch, ych in PAIRS:
        allrec = []
        for route in L.ROUTES:
            allrec += L.collect_native(route, L.mask_engaged, xch=xch, ych=ych, extra=ep_extra)
        if not allrec:
            print(f"\n--- {xch} -> {ych}: NO EPISODES")
            continue
        f, Sxx, Syy, Sxy, K = L.stack(allrec)
        out["pairs"][f"{xch}->{ych}"] = report(f, Sxx, Syy, Sxy, K,
                                               f"ENGAGED, all 4 builds pooled: {xch} -> {ych}",
                                               recs=allrec)
        if (xch, ych) == ("cmd", "bar"):
            g2n, Kn = L.mismatch_null(allrec)
            print("  PHASE-RANDOMISED EPISODE NULL (the coherence floor):")
            for bn, (lo, hi) in L.BANDS.items():
                sel = (f >= lo) & (f <= hi)
                print(f"    {bn:>8}  null g2 = {np.nanmean(g2n[sel]):.4f}   "
                      f"(1/K = {1/Kn:.4f})")
            out["null"] = {bn: float(np.nanmean(g2n[(f >= lo) & (f <= hi)]))
                           for bn, (lo, hi) in L.BANDS.items()}
            # fine bands at the symptom frequencies
            print("  FINE BANDS (cmd -> bar):")
            fine = {}
            for nm, lo, hi in FINE:
                s = L.band_stats(f, Sxx, Syy, Sxy, lo, hi, K)
                pt, ci = L.boot_band(allrec, lo, hi, nboot=2000)
                print(f"    {nm:18s} {lo:.0f}-{hi:.0f} Hz  g2 = "
                      f"{L.fmt_ci(s['g2'], ci['g2'])}   tau = "
                      f"{L.fmt_ci(s['tau_ms'], ci['tau_ms'])} ms   "
                      f"barRMS/cmdRMS = {L.fmt_ci(s['ratio'], ci['ratio'])}")
                s["ci"] = {k: list(v) for k, v in ci.items()}
                fine[nm] = s
            out["fine_cmd_bar"] = fine
            out["_recs_meta"] = [dict(route=r["route"], seg=r["seg"], sec=r["sec"],
                                      v_mean=r["v_mean"], nblk=r["nblk"],
                                      cap_duty=r["cap_duty"], amp_duty=r["amp_duty"])
                                 for r in allrec]

    # ------------------------------------------------------- per-route, cmd -> bar --------------
    print("\n\n=== PER-BUILD cmd -> bar (does the answer replicate across four builds?)")
    for route in L.ROUTES:
        recs = L.collect_native(route, L.mask_engaged, xch="cmd", ych="bar", extra=ep_extra)
        if len(recs) < 3:
            print(f"  {route}: only {len(recs)} episodes -- skipped")
            continue
        f, Sxx, Syy, Sxy, K = L.stack(recs)
        out["per_route"][route] = report(f, Sxx, Syy, Sxy, K, route, recs=recs, boot=True)

    # ---------------------------------------- MANUAL: recorded as REFUSED, with the reason -------
    print("\n\n=== MANUAL (latActive == 0)")
    print("  REFUSED as a control: openpilot's 0x0E4 is a CONSTANT ZERO when disengaged "
          "(sd 0.0-29 ct across 27 segments, creq mean 0.000-0.008).  A coherence against a "
          "constant input is undefined, not a null.")
    out["manual_cmd_bar"] = "REFUSED: command is constant 0 when disengaged"

    (L.CACHE / "t1_coherence.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"\n-> {L.CACHE / 't1_coherence.json'}")


if __name__ == "__main__":
    main()
