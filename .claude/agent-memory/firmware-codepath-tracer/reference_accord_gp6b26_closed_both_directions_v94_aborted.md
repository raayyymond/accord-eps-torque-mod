---
name: reference_accord_gp6b26_closed_both_directions_v94_aborted
description: gp-0x6b26 (the 0xCBE74-scheduled "apparent inertia" term) is CLOSED as a lever in BOTH directions, not just untested-downward as the theory suggests. V91/V92 raised it (x1.5), measured inert (confounded). V93/V94 LOWERED it (x0.167..x0.5), and the OPERATOR ABORTED THE DRIVE (V94, route 7d) reporting it "made the stuttering and grinding worse, by a lot... vibrated the entire car... not safe to drive." Measured afterward: the term carries a REAL +518/+565-count positive Re(Z) 6-9Hz damping contribution in the closed loop, contradicting the pure-inertia (zero real part) theory. Also documents the CURRENT car's actual (non-stock) gp-0x6b26 configuration.
metadata:
  type: reference
---

Found/consolidated 2026-08-19 while re-scoping a damping-lever hunt under an operator constraint of
"no DC/slew cost." The orchestrator's brief stated "gp-0x6b26 ... DOWN has never been tried" —
**this is wrong, and the on-car result is the single most decision-relevant fact in this domain.**

## The lineage [EVIDENCE — build_v93_tva.py, build_v94_tva.py, build_v96_tva.py, docs/STATE.md:589,
## docs/BUILD-LINEAGE.md:1170-1198, docs/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md]

`0xCBE74` is a 34-entry pointer array of per-mode LERP records (X in km/h, Y in Q-ish counts) that
`FUN_00036c12` uses to scale `gp-0x6b26 = -K(speed)·gp-0x6c2c` (gp-0x6c2c = filtered motor-rate first
difference = angular acceleration). 13+ builds have touched this family:

- V73-V77, V81, V83a, V84, V86, V90: raised or restored stock.
- **V91/V92: raised x1.5 on modes 26/27 (engaged).** Flown, MEASURED INERT (engaged stratified ratio
  0.99 [0.91,1.26] vs pre-registered 1.50) — but confounded (RULE 7: mode-record identity suspect).
- **V93/V94: LOWERED it — mode24 x0.50, modes 26/27 x0.25, fallback constants x0.75.** V93's own
  docstring: *"LOWERING IT HAS NEVER BEEN TRIED... V93 is a new lever, not a re-run"* — true AT THE
  TIME, no longer true now. V94 = same lever, rescaled CAN427 instrument so the dose could be seen.
  **V94 flew as route `7d`, fault-free, and the OPERATOR ABORTED THE DRIVE HIMSELF**: *"made the
  stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided
  it was not safe to drive."*
- **V96 reverted the cut BY CONSTRUCTION**, explicitly to "get the car back to a configuration the
  operator drove and did not abort" (= V92's ×1.5-engaged-only state). Carried unchanged V96→V101.

## Why the clean "pure inertia, zero real part, safe to lower" theory was wrong in practice

V96's own measurement, two independent drives, omega-partialled against a shuffled control: the
delivered lane sits at **+137°/+139° vs WHEEL rate at 6-9Hz ⇒ |cos|=0.73 ⇒ +518/+565 counts of
POSITIVE Re(Z).** That is a real, measured 6-9Hz damping contribution in the CLOSED loop, not the
90°-out-of-phase pure reactive term the isolated-signal-identity argument (gp-0x6b26 = -K·accel,
accel is 90° from velocity) predicts. **V94 removed 6/6ths of it, and the car got measurably and
subjectively worse.** The lesson generalises: isolated-stage phase/DC analysis of a term that FEEDS
a real closed loop is not sufficient — phase accumulates around the loop in a way a single-stage
transfer function does not capture. Apply this caution to any other "looks reactive in isolation"
term before trusting a zero-DC-cost argument for it (e.g. `0xC646E`, see
[[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]] for a sibling
case that has NOT yet been measured this way).

## Verdict and current car state

**`0xCBE74`/`gp-0x6b26` is CLOSED as a lever in BOTH directions** — up is measured inert (though
confounded), down is measured actively worse and was unsafe enough that the operator stopped
driving. Do not propose moving it either way without a fundamentally different plan than "raise" or
"lower the Y values."

**The car as currently built (V101, byte-verified this session) does NOT run Honda-stock
`gp-0x6b26`** — mode26/27 (engaged) Y-row = `(-14745,-8601,-2949)` = exactly ×1.5 of stock
`(-9830,-5734,-1966)`; mode24 (manual) = stock. This is V92's configuration, carried since V96,
unrelated to any V101-specific edit — worth stating in any "what's non-stock about this ECU" summary
independent of what else gets proposed.

## Related
[[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]] — the
structurally SEPARATE Path-2 "inertia" term (`0xC646E`, inside `FUN_0003b8f6`, NOT the same
mechanism as this file's `gp-0x6b26`/`0xCBE74`, still virgin) that this file's caution now applies to.
