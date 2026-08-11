---
name: reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism
description: Full trace of the operator's "return-to-centre restricted when LKAS is non-zero, even if aligned" hypothesis. NO discrete LKAS-magnitude gate exists on gp-0x6b62 (return-centre) anywhere -- both candidate hard gates (gp-0x67ac, gp-0x67fa) are structurally closed/unreachable/decoupled. The best-supported real mechanism is the MOTOR-RATE-ADAPTIVE governor ceiling (gp-0x4f64, table 0xC520C) shared by return-centre and LKAS's in-aggregator term gp-0x6b4c, amplified by the kit's own 4x LKAS gain 0xC6CD0.
metadata:
  type: reference
---

# Return-to-centre gate hunt — verdict: no LKAS-magnitude gate; the real shared limiter is a rate-adaptive governor ceiling

Full session: `docs/TRACE-2026-08-11-return-to-centre-gate.md`. Task from team-lead, driven by the
operator's on-car report: *"it's almost like the return to zero assist is not running unless LKAS command
is near zero. It restricts return to zero even if it's aligned with return to zero degrees."*

## Verdict

**No discrete `if (LKAS != 0) suppress return` branch exists anywhere in this firmware.** Return-centre's
producer (`FUN_00036388`/`FUN_000360fe`, writing `gp-0x6b62`) reads driver-torque-margin and motor-rate
signals only — zero hits on `gp-0x6b3c/6b4a/6b4c/6afe/6b98` in a scoped, full-function instruction search
of both producer functions (206+72 instructions, `truncated:false`). Both candidate hard gates named in
the brief are structurally closed:
- `gp-0x67ac` (aggregator's alternate "reduced" branch, which explicitly special-cases return-centre via
  `0xC74AC`) is **provably always 0** — the aggregator always takes the FULL 11-lane branch where
  return-centre and LKAS's `gp-0x6b4c` are simply, unconditionally ADDED. (Pre-existing finding,
  re-confirmed, see [[reference_accord_gp67ac_reduced_branch_unreachable]].)
- `gp-0x67fa` (the state gate wrapping return-centre's very call) is **provably decoupled from LKAS
  engagement** — a health/fault/UDS-test-mode state machine, zero reference to `gp-0x67fe`/`gp-0x6806`/
  `gp-0x69ae`/`gp-0x1426` across all ~20 transition guards. (Pre-existing finding, re-confirmed.)

**CORRECTION this session**: the brief's own named LKAS-magnitude candidate `gp-0x6afe`/`gp-0x6b4e` is
**provably, structurally always zero** — see [[reference_accord_gp6afe_gp6b4e_provably_zero_correction]].
There is no LKAS injection at the shaper's final summation stage at all.

## The mechanism that DOES exist [EVIDENCE for the structure; BELIEF for its numeric applicability to a
## real return-to-centre event — see Open item below]

Return-centre (`gp-0x6b62`) and LKAS's in-aggregator term (`gp-0x6b4c`, carrying the kit's own 4x
forward-path gain `0xC6CD0`=3564) are two of 11 lanes UNCONDITIONALLY summed inside `FUN_0003aa2c`, whose
total (`gp-0x6b94`) feeds a governor (`FUN_0004503c`) and comp-add (`FUN_000456a4`) before reaching the
shaper (`FUN_00042af8`). Inside the shaper, the combined signal is clamped `+/-gp-0x4f64` — and
`gp-0x4f64` is **not fixed**: in steady-state LKAS mode it equals `MIN(gp+0x130, gp+0x128, fVar54)*1024`,
where `gp+0x128` is a LERP over **motor electrical rate** (`gp-0x6ac0`) against `0xC520C`:
`X=[1050,1700,2500,3700,4100]` -> `Y=[5325,3584,2406,1587,512]` (falling; byte-confirmed stock across
V37-V74). At rate >= 4100 the ceiling falls to 512, a ~90% cut from the 4762 nominal.

**Physical reading**: when LKAS is aligned with return-to-centre, the wheel returns FASTER (both terms
push the same way) — which RAISES `gp-0x6ac0` — which SHRINKS the governed ceiling — which caps the
combined delivered command HARDER, for both terms together, precisely when the push is largest. A
rate-adaptive, symmetric (both directions) self-throttle, not a magnitude relay, but it produces the
described symptom without needing an LKAS-specific gate. **Per `docs/FEASIBILITY-8X-LKAS.md` (2026-08-06,
independent prior session), this table is ALREADY the dominant real-world binder on the current (4x) car
even outside a return-to-centre scenario** ("even at TODAY's 4x, moderately fast steering already clips
here, before the flat 4762 ceiling matters") — so the mechanism's existence and its current-build
significance are both independently corroborated, not new to this session.

**Secondary, direction-asymmetric hard relay** (real, but a weaker match): the shaper's OWN input
zero-gate on `gp-0x6acc` (`gp-0x6acc+0x2000<0x4001`) hard-zeroes the ENTIRE base-assist leg (return-centre
included) for POSITIVE excursions above +8192, no hysteresis (a single combinational compare, no dwell
counter — a textbook limit-cycle generator if the gated signal dithers near the boundary). One-sided,
so it explains restriction on only one sign of the combined command, not the general case the operator
described.

## Item 6 (our own cells) — checked

`0xC6CD0`=3564 (4x LKAS forward-path gain, live on the current build per `build_v90_tva.py`) sits
upstream of `gp-0x6b4c`, the exact term sharing the rate-adaptive ceiling with return-centre. It does
NOT touch return-centre's own producer cals directly (`0xC618A`/`0xC627E`/`0xC63C0`/`0xC6132`/
`0xC695C-0xC6970`/`0xC63BE`, all confirmed untouched by any `build_v*_tva.py`). **If the rate-adaptive
mechanism is confirmed live at ordinary return-to-centre rates, the fix is closer to reverting `0xC6CD0`
toward stock than adding a new lever** — since a smaller LKAS command needs a smaller wheel rate to reach
the same total, so it trips this ceiling less often. Not proposed as a build this session; structural
finding only, per the brief's cal-only/no-cave constraint and the operator's explicit no-rate-limiting
constraint (this ceiling is NOT a designed rate limiter on LKAS specifically, but any edit to it needs
the same caution).

## What would close the "BELIEF" gap

`gp-0x6ac0`'s counts-per-deg/s scale is not independently established this session (it may differ from
`gp-0x6abe`'s settled 4.7121 ct/(deg/s) — same producer family, `FUN_00041464`, but not confirmed
identical scale). Whether an ORDINARY (not extreme) return-to-centre event reaches the `0xC520C` table's
1050-4100 count breakpoints, at both 1x (stock) and 4x (current) LKAS gain, is the single number that
would convert this from a structural argument into a quantitative one. Next step: trace `FUN_00041464`'s
scale constant for `gp-0x6ac0` specifically, or pull `gp-0x6ac0`/`gp-0x6abc` telemetry from an existing
rlog during a documented return-to-centre stretch.

## Related
[[reference_accord_gp6afe_gp6b4e_provably_zero_correction]] — the dead-cell correction this trace turned up.
[[reference_accord_gp67ac_reduced_branch_unreachable]] — one of the two closed hard-gate candidates.
[[reference_accord_gp67fa_writer_census_decoupled_from_engagement]] — the other closed hard-gate candidate.
[[reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive]] — prior full trace of
return-centre's own internal mechanics (no angle term, torque-margin/motor-rate gated).
