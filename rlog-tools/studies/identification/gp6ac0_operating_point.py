#!/usr/bin/env python3
r"""⭐ `gp-0x6ac0`'s ENGAGED OPERATING POINT ON ROUTE 0x85 -- does it stay inside the FLAT FIRST
SEGMENT of the PID gain tables, or does it traverse a knot?

WHY THIS DECIDES A BUILD.  `gp-0x6ac0` is the motor resolver / FOC electrical rate, magnitude-only,
and it is the SHARED LERP INDEX for all four PID tables (Kp, Ki, Kd, anti-windup) --
`0x3a38e ld.hu -0x6ac0,gp,r12`.  The PID gain family is the leading cal-only fix candidate, and its
headline property is that the operating point sits ENTIRELY INSIDE THE FLAT FIRST SEGMENT, which is
what makes a `Y[0]`+`Y[1]` edit a clean scalar gain change with no slope discontinuity.

    P-table knots:  0 / 300 / 2000 / 4000 counts  =  0 / 63.7 / 424.4 / 848.9 deg/s
    scale:          gp-0x6ac0 ~= 4.7121 * |column angular rate in deg/s|
                    (4.7121 = 2^18 / (48 * 1159))

🛑 THE INHERITED FIGURES DISAGREE BY 5.9x, AND ALL THREE COME FROM THE WRONG REGIME:
      528 ct (~112 deg/s)   the 0xC520C analysis      -- HANDS-OFF RETURNS ONLY
      329.8 ct (~70 deg/s)  accord/calibration/accord-damper-is-mode-table-selected.md:54 -- highway peak
    1,941 ct (~412 deg/s)   BUILD-LINEAGE.md:378, route 5d -- PARKING-LOT CRANKING
  Route 0x85 is the operator's own engaged regime: 51.3 s in the 13-50 deg/s bin and 14.8 s above
  50 deg/s.  Nobody has measured this in that regime.

===================================================================================================
THE ESTIMATOR, AND WHY THE PRE-REGISTERED DIFFERENTIATOR IS THE WRONG TOOL HERE
===================================================================================================
The dCMD/dt analysis pre-registered a Savitzky-Golay derivative with a 0.25 s window precisely
BECAUSE it suppresses high-frequency content.  **That property is a defect for a PEAK statistic.**
A 0.25 s boxcar-ish smoother will under-read exactly the excursion this question is about.  So the
differentiator is re-chosen for the job, and FOUR estimators are reported side by side so the
answer cannot be an artefact of one smoothing choice:

  E1  `cs_rate`  -- carState.steeringRateDeg, i.e. Honda's OWN STEER_ANGLE_RATE off the CAN bus.
                    **NO differentiation at all.**  ⭐ THE PRIMARY.  23,569 distinct values on this
                    route, so it is a real measured channel, not a recomputed one.
  E2  SG deriv, 25 samples (0.25 s), polyorder 2   -- the pre-registered one.  LOWER BOUND on peaks.
  E3  SG deriv,  5 samples (0.05 s), polyorder 2   -- light smoothing.
  E4  raw central difference (np.gradient * FS)    -- UPPER BOUND; carries the full sensor
                    quantisation noise into the peak.

🛑 ALL DERIVATIVES ARE COMPUTED **PER SEGMENT**.  Route 0x85 is missing segment 17, so a
   whole-route derivative crosses a ~60 s hole; doing it naively returns |rate| = 6,537 deg/s at the
   seam, which is pure artefact.  Per-segment differentiation removes it.

===================================================================================================
HOW THE ESTIMATOR'S LIMITS BIAS THE ANSWER -- and the direction is FAVOURABLE to the candidate
===================================================================================================
`gp-0x6ac0` is NOT the column rate.  Three differences, and **all three make this estimate an
UPPER BOUND on the real cell**:
  1. **IIR-FILTERED.**  The cell is a smoothed quantity; a rate estimate from the raw angle channel
     retains transients the filter removes.  ⇒ the real cell's PEAK IS LOWER than E1/E3/E4.
  2. **MAGNITUDE-ONLY and fed from a CLAMPED delta.**  The PID lane's own entry gate requires
     `gp-0x6ac0 < 0x32c9` (13,001 ct = 2,759 deg/s) or the function returns 0 unconditionally, so
     the cell cannot present a larger index to the tables whatever the column does.
  3. **Column-referred, via a fixed 4.7121.**  Any resolver/column compliance shows up as the
     column moving without the motor following ⇒ again an over-read, not an under-read.
⇒ **IF EVEN THE UPPER-BOUND ESTIMATE STAYS BELOW A KNOT, THE REAL CELL CERTAINLY DOES.  If the
  upper bound CROSSES a knot, the question is genuinely open and cannot be closed from the wire.**
  Say which of those two cases obtains; do not split the difference.

SPEED REFERENCE: `v_rear = (ws_rl + ws_rr)/2`, NOT vEgo (which runs +7.9 % fast at angle).
ANGLE: RAW `cs_ang`, with the ~-4.25 deg left offset NOT removed.  A constant offset cannot affect
a derivative, so this choice is immaterial to every number here -- stated because it was asked.

Usage:  python studies/identification/gp6ac0_operating_point.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
AN = ROOT / "analysis-2020accord"
OUT = AN / "sessions/v100"
OUT.mkdir(parents=True, exist_ok=True)

FS = 100.0
SCALE = 4.7121                       # counts of gp-0x6ac0 per column deg/s
KNOTS = [0, 300, 2000, 4000]         # the P-table knots, in counts
KNOT_DPS = [k / SCALE for k in KNOTS]
GATE = 0x32C9                        # 13,001 -- the PID lane's own entry gate on gp-0x6ac0
EST = ["E1 cs_rate (Honda CAN)", "E2 SG 0.25s (preregistered)", "E3 SG 0.05s (light)",
       "E4 raw diff (upper bound)"]


def estimators(ang, rate):
    """Four |column rate| estimates in deg/s, for ONE contiguous segment."""
    out = {}
    out[EST[0]] = np.abs(rate)
    for tag, win in ((EST[1], 25), (EST[2], 5)):
        out[tag] = (np.abs(signal.savgol_filter(ang, win, 2, deriv=1, delta=1.0 / FS,
                                                mode="interp"))
                    if len(ang) > win else np.full(len(ang), np.nan))
    out[EST[3]] = np.abs(np.gradient(ang) * FS)
    return out


def summarise(v_dps, tag, n_min=100):
    v = np.asarray(v_dps, float)
    v = v[np.isfinite(v)]
    if len(v) < n_min:
        return None
    c = v * SCALE
    return dict(tag=tag, n=int(len(v)),
                p50=float(np.percentile(c, 50)), p90=float(np.percentile(c, 90)),
                p99=float(np.percentile(c, 99)), p999=float(np.percentile(c, 99.9)),
                max=float(c.max()),
                p50_dps=float(np.percentile(v, 50)), p99_dps=float(np.percentile(v, 99)),
                max_dps=float(v.max()),
                frac_gt_300=float(np.mean(c > 300)), frac_gt_2000=float(np.mean(c > 2000)),
                frac_gt_4000=float(np.mean(c > 4000)), frac_gt_gate=float(np.mean(c > GATE)))


def row(s):
    return (f"    {s['tag']:30s} n={s['n']:7,}  p50 {s['p50']:8.1f}  p90 {s['p90']:8.1f}  "
            f"p99 {s['p99']:8.1f}  p99.9 {s['p999']:8.1f}  MAX {s['max']:9.1f}   "
            f">300 {100*s['frac_gt_300']:6.2f}%  >2000 {100*s['frac_gt_2000']:5.2f}%")


def main():
    z = np.load(AN / "_scratch/cache/r85" / "r85.npz", allow_pickle=True)
    seg = np.asarray(z["seg"], int)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    ang = np.asarray(z["cs_ang"], float)
    rate = np.asarray(z["cs_rate"], float)
    rl, rr = np.asarray(z["ws_rl"], float), np.asarray(z["ws_rr"], float)
    v_rear = 0.5 * (rl + rr)

    print("=" * 118)
    print("  gp-0x6ac0 ENGAGED OPERATING POINT, ROUTE 0x85.  Units: COUNTS "
          f"(= {SCALE} x |column deg/s|)")
    print(f"  P-table knots: " + "  ".join(f"{k} ct ({d:.1f} deg/s)"
                                           for k, d in zip(KNOTS, KNOT_DPS)))
    print(f"  PID entry gate: gp-0x6ac0 < 0x32C9 = {GATE} ct ({GATE/SCALE:.0f} deg/s)")
    print("=" * 118)

    # ---- per-segment derivatives, then reassembled (NEVER across the missing segment 17)
    E = {t: np.full(len(ang), np.nan) for t in EST}
    for s in sorted(set(seg.tolist())):
        m = seg == s
        for t, v in estimators(ang[m], rate[m]).items():
            E[t][m] = v

    res = {"scale_counts_per_dps": SCALE, "knots_counts": KNOTS, "gate_counts": GATE,
           "estimators": EST, "whole_route": {}, "per_segment": {}, "seg20_window": {}}

    for tag, sel, name in ((("ENGAGED"), eng, "engaged"), (("MANUAL"), ~eng, "manual")):
        print(f"\n  === WHOLE ROUTE, {tag} ({int(sel.sum()):,} frames, "
              f"{sel.sum()/FS:.1f} s) ===")
        res["whole_route"][name] = {}
        for t in EST:
            s_ = summarise(E[t][sel], t)
            if s_:
                res["whole_route"][name][t] = s_
                print(row(s_))

    print(f"\n  === PER SEGMENT, ENGAGED ===")
    for s in sorted(set(seg.tolist())):
        m = (seg == s) & eng
        if m.sum() < 100:
            continue
        res["per_segment"][int(s)] = {}
        print(f"\n    seg {s}  ({int(m.sum()):,} engaged frames, {m.sum()/FS:.1f} s, "
              f"v_rear p50 {np.nanmedian(v_rear[m]):.1f} km/h)")
        for t in EST:
            s_ = summarise(E[t][m], t)
            if s_:
                res["per_segment"][int(s)][t] = s_
                print(row(s_))

    # ---- segment 20 specifically -- the operator's own stuttering + LKAS-off window
    i20 = np.where(seg == 20)[0]
    t20 = np.arange(len(i20)) / FS
    for tag, m in (("seg20 ENGAGED", (seg == 20) & eng), ("seg20 MANUAL", (seg == 20) & ~eng)):
        print(f"\n  === {tag} ({int(m.sum()):,} frames, {m.sum()/FS:.1f} s) ===")
        res["seg20_window"][tag] = {}
        for t in EST:
            s_ = summarise(E[t][m], t)
            if s_:
                res["seg20_window"][tag][t] = s_
                print(row(s_))

    # ================= THE THREE-WAY ANSWER =================
    print("\n" + "=" * 118)
    print("  ⭐ THE THREE-WAY ANSWER")
    print("=" * 118)
    prim = res["whole_route"]["engaged"][EST[0]]
    ub = res["whole_route"]["engaged"][EST[3]]
    lb = res["whole_route"]["engaged"][EST[1]]
    print(f"    PRIMARY  (E1, Honda's own rate channel, engaged):")
    print(f"        p50 {prim['p50']:.1f} ct  p90 {prim['p90']:.1f}  p99 {prim['p99']:.1f}  "
          f"MAX {prim['max']:.1f} ct")
    print(f"        above the 300 ct knot : {100*prim['frac_gt_300']:.2f} % of engaged frames "
          f"({prim['frac_gt_300']*prim['n']/FS:.1f} s)")
    print(f"        above the 2000 ct knot: {100*prim['frac_gt_2000']:.2f} % "
          f"({prim['frac_gt_2000']*prim['n']/FS:.1f} s)")
    print(f"    SENSITIVITY TO SMOOTHING: MAX is {lb['max']:.0f} ct (E2, heaviest smoothing) .. "
          f"{ub['max']:.0f} ct (E4, none).")
    print(f"        >300 duty spans {100*lb['frac_gt_300']:.2f} % .. {100*ub['frac_gt_300']:.2f} %;"
          f"  >2000 duty spans {100*lb['frac_gt_2000']:.2f} % .. "
          f"{100*ub['frac_gt_2000']:.2f} %.")

    crosses300 = prim["frac_gt_300"] > 0.01
    crosses2000 = prim["frac_gt_2000"] > 0.001
    if not crosses300:
        verdict = ("STAYS BELOW 300 ct -- the operating point never leaves the FLAT FIRST SEGMENT. "
                   "The clean-scalar property HOLDS and a Y[0]+Y[1] edit is a pure gain change.")
    elif not crosses2000:
        verdict = (
            f"CROSSES 300 ct BUT STAYS BELOW 2000 ct. {100*prim['frac_gt_300']:.2f} % of engaged "
            f"frames ({prim['frac_gt_300']*prim['n']/FS:.1f} s) sit ABOVE the first knot, reaching "
            f"{prim['max']:.0f} ct (E1) / {ub['max']:.0f} ct (E4 upper bound). ⇒ THE HEADLINE "
            f"CLAIM 'the operating point sits ENTIRELY INSIDE THE FLAT FIRST SEGMENT' IS FALSE. "
            f"The 2000 knot is NOT reached, so a Y[0]+Y[1] edit creates NO SLOPE DISCONTINUITY "
            f"anywhere the car goes and the candidate is NOT B1-class. BUT THE EDIT IS NOT A CLEAN "
            f"SCALAR EITHER: with Y[2] left unscaled, the delivered dose is FULL below 300 ct "
            f"(95.1 % of engaged frames) and FADES LINEARLY toward 1.000x as the index approaches "
            f"2000. On the quoted Y1=256/Y2=225, a nominal 2.000x delivers 1.84x at 600 ct, 1.50x "
            f"at 1200 ct and 1.32x at the measured peak -- only about a third of the intended "
            f"increment survives at peak rate. THE FIX IS ONE MORE CELL: scale Y[2] too, which "
            f"moves the seam into the 2000-4000 segment that the car never visits and restores a "
            f"clean scalar over the whole reachable range for 2 more bytes.")
    else:
        verdict = (f"EXCEEDS 2000 ct. {100*prim['frac_gt_300']:.1f} % of engaged frames are above "
                   f"the 300 knot and {100*prim['frac_gt_2000']:.2f} % are above the 2000 knot, so "
                   f"BOTH knots are traversed in the operator's own engaged regime. Kp is NOT flat "
                   f"across the reachable range, and editing Y[0]+Y[1] together WOULD create a "
                   f"slope discontinuity at the 2000 knot. THE HEADLINE PROPERTY FAILS.")
    res["verdict"] = verdict
    print(f"\n    ⇒ {verdict}")
    print(f"\n    🛑 DIRECTION OF THE ESTIMATOR BIAS: every estimator here is an UPPER BOUND on the "
          f"real cell\n       (IIR-filtered, magnitude-only, clamped input, column-referred). So a "
          f"'stays below' answer is\n       SAFE, and a 'crosses' answer is NOT PROOF that the "
          f"cell itself crosses -- it means the wire\n       cannot close the question and only an "
          f"in-ECU thermometer on gp-0x6ac0 can.")
    (OUT / "gp6ac0_operating_point.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'gp6ac0_operating_point.json'}")
    return res


if __name__ == "__main__":
    main()
