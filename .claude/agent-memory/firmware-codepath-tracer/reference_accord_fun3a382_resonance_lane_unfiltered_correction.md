---
name: reference-accord-fun3a382-resonance-lane-unfiltered-correction
description: "FUN_0003a382 (gp-0x6ad4 'resonance' aggregator lane) is NOT heavily damped -- both its Q10 'lag' gains read 1024 (unity, zero filtering) in stock/V38/V42, not the '4' a prior memory claimed. It is an unfiltered channel carrying raw Sensor-B torque minus a feedforward command model straight into the demand aggregator, untouched by V39/V41/V42."
metadata:
  type: reference
---

Traced 2026-07-19/20 on stock `code.bin` (Ghidra decompile) + byte-verified against `_v38_plain_image.bin`,
`_v42_plain_image.bin`, and stock `code.bin` (all three agree), tasked by team-lead for a "fast signal
coupling" audit into the demand aggregator `FUN_0003aa2c`. Builds on [[reference-accord-post-governor-comp-add]]
and the `model/eps_lkas_chain_model.py` `assist_shaping_lanes()` docstring, which had labeled this lane
"*** PARTIALLY PINNED -- and it ARGUES AGAINST this lane resonating ... VERY heavily damped ***"
citing "gp-0x367c stage, gain = cal tp+0x7450 (0xC6450) = 4" and "gp-0x3680 stage, gain = cal tp+0x744a
(0xC644A) = 4" (tau ~ 256 cycles). **That gain reading was WRONG.**

## Correction [VERIFIED]

Direct byte read of `0xC6450` and `0xC644A`, all three images (`stock code.bin`, `_v38_plain_image.bin`,
`_v42_plain_image.bin`):
```
0xC6450 = 1024 (0x0400)   -- NOT 4
0xC644A = 1024 (0x0400)   -- NOT 4
```
1024 in this codebase's Q10 fixed-point convention is **unity gain (1.0)**, not a damping factor. The
update rule at each site is `state_new = state + ((target - state) * gain) >> 10`. With `gain == 1024`,
`(target - state) * 1024 >> 10 == target - state` **exactly** (no rounding loss -- 1024 = 2^10 divides
out cleanly), so `state_new == target` **every single cycle**. This is not a lag with a long time
constant -- it is algebraically equivalent to direct assignment, i.e. **zero filtering, one-cycle
settling**. Cross-check on my own tp-offset arithmetic: the same dump also read `0xC6202 = 4762`
(matches the independently-verified governor headroom) and `0xC6204 = 3072` (matches the independently
verified post-governor-comp Q10 gain) at their expected addresses, so the addressing is not the error --
the earlier "4" reading was.

## Full structure of FUN_0003a382 (gp-0x6ad4, aggregator's "resonance" lane) [VERIFIED via decompile]

Input error term (byte-verified, `unaff_gp`/`unaff_tp` = gp/tp per this kit's convention):
```
errorterm = clamp( gp-0x4f60 (raw Sensor-B/TAS column torque, SIGNED)
                    - clamp(gp-0x6ad6, +/- cal 0xC6200 = 8192),
                    +/- 0x2800 )
```
`gp-0x6ad6` has exactly ONE writer image-wide (`search_instructions` on operand "6ad6": 3 hits total --
1 store in `FUN_00037fe6`, 2 loads in `FUN_0003a382` itself; `get_xrefs_to` on the raw RAM address
0xFEDF152A found nothing -- a known tool limitation for gp-relative addresses, not evidence of zero
writers). `FUN_00037fe6` computes gp-0x6ad6 EVERY CALL (no persisted/lagged state visible in that
function either) as a **weighted sum of ~7 other internal command-cluster lanes**
(`gp-0x6b4a, -0x6bc2, -0x6b60, -0x6b2a, -0x6bce, -0x6b6e, -0x6bbc, -0x6b70`, each range-gated
zero-type, each weighted by an 8-bit cal at `tp+0x74ad..0x74b3`), then scaled by a flat-extrapolated
LERP keyed on `gp-0x69aa` (role not identified this session). This reads as a **feedforward model of
the torque the motor's own commanded lanes should be producing** -- i.e. `errorterm` is
"real sensor reading minus an idealized digital prediction," a classic residual/observer-error
construction.

Three parallel branches, all fed by `errorterm` (or its LERP-scaled variants) and gp-0x6ac0 (motor
electrical rate) as the LERP axis for three separate gain tables, all byte-dumped this session
(V38 == V42 == stock):
```
L1 (0xC6B20/24, Y@0xC6B26/28/2A/2C) = (256, 256, 225, 153)  -- FALLING with motor rate, NOT flat
L2 (0xC6B0C/10, Y@0xC6B12/14/16/18) = (98, 98, 98, 98)      -- FLAT/constant, no motor-rate coupling
L3 (0xC6AE0/E4, Y@0xC6AE6/E8/EA/EC) = (2048, 2048, 2048, 2048) -- FLAT/constant = 2.0 in Q10
```
- Stage A (`gp-0x367c`): `state += ((L1*errorterm>>10)*32 - state) * 1024 >> 10` => **state = target
  exactly, every cycle** (the corrected gain above). Feeds the final sum directly.
- Stage B (`gp-0x3688`): a windowed running accumulator, `state += (L2*errorterm)>>10`, clamped to a
  window derived from Stage A's target -- L2 is a flat 98/1024 (~0.096), so this adds a SMALL but
  UNFILTERED (no lag term at all, the addition each cycle is raw) increment of errorterm every cycle.
- Stage C (`gp-0x3684`/`gp-0x3680`): a raw one-sample DIFFERENCE `(errorterm_now - errorterm_prev) * L3`
  (L3 flat 2.0), clamped +/-0x2800, THEN passed through the SAME corrected-unity "lag" (gain 0xC644A =
  1024) -- i.e. the derivative's own smoothing stage also does not filter anything; the 2x-amplified
  raw derivative reaches the final sum unattenuated.

Final combine: `(StageA + StageB + StageC) >> 5`, times a 4th LERP keyed on `gp-0x671a` (assist state),
times polarity `gp-0x6752`, clamped against a separate authority/tracking-error-derived dynamic bound
(built from `gp-0x6bda`, `gp-0x6966` = soft-EME AUTHORITY, `gp-0x6a98`) -> `gp-0x6ad4`. Consumed by the
aggregator `FUN_0003aa2c` through the ALREADY-VERIFIED zero-type range gate `+/-0x2800` (re-confirmed
2026-07-19 per [[reference-accord-post-governor-comp-add]]'s sibling note) -- out-of-window contributes
exactly 0 (a hard cliff), in-window passes unclipped.

## Net structural conclusion [VERIFIED, structure only]

**This lane applies effectively ZERO low-pass filtering at the current cal values.** Both nominal "lag"
stages are unity-gain identity operations; the two multiplicative gain tables that are NOT flat-constant
(L1) or ARE flat-constant (L2, L3) never introduce smoothing across cycles -- there is no state variable
in this function whose update coefficient is < 1024. This directly contradicts the prior memory's
"heavily overdamped" conclusion, which was the basis for `model/eps_lkas_chain_model.py` ruling this lane out
as "arguing against this lane resonating." **The corrected reading argues the OPPOSITE: this is a
genuinely fast, largely unfiltered lane carrying (real Sensor-B torque) minus (an idealized feedforward
model of commanded torque) directly into the demand aggregator**, independent of and untouched by V39
(r24 zeroed), V41 (motor-rate cap table flattened), or V42 (r26 gain zeroed) -- none of those builds
touch `FUN_0003a382`, `gp-0x6ad4`, `gp-0x6ad6`, `0xC6450`, `0xC644A`, or any of the L1/L2/L3 tables above.

## Why this satisfies the team-lead's "multiplicative-with-command" test [INFERRED, physical]

`errorterm` is not a purely digital quantity scaled by a table -- its dominant term is the REAL sensor
reading `gp-0x4f60`, which physically reflects whatever torque is actually present at the column,
including the motor's own reaction torque. `gp-0x6ad6` (the subtracted reference) is built from an
idealized weighted sum of the SAME command lanes, i.e. it approximates what the sensor "should" read if
the motor delivered torque with no mechanical nonideality. **Any unmodeled physical ripple in the
motor's actual torque delivery (cogging, current ripple, backlash) will NOT be canceled by the
subtraction and will show up undamped in `errorterm`.** If that physical ripple's amplitude scales with
commanded torque amplitude (a standard characteristic of PMSM/BLDC motors under proportional current
control), then V38's 4x larger delivered torque for the same steering maneuver would produce
correspondingly larger real ripple on `gp-0x4f60`, which this UNFILTERED lane passes essentially
unattenuated into the aggregator. This is NOT captured by the gain-rescaling-invariance argument in
CLAUDE.md, because that argument concerns digital replay of the SAME counts through downstream stages --
it says nothing about a term sourced from a REAL sensor responding to REAL delivered torque, which is
exactly the loophole this lane represents.

**[INFERRED, not verified]**: that real motor torque ripple actually scales with commanded torque
amplitude in this specific EPS motor -- this is a physical/mechanical claim outside firmware and cannot
be settled by disassembly; it needs live telemetry (e.g. logging `gp-0x6ad4` or `gp-0x4f60` at high rate
during LKAS-only vs hands-on steering at matched wheel angle).
**[OPEN]**: `gp-0x6ad4`'s realistic runtime magnitude and whether it approaches the `+/-0x2800` zero-gate
boundary (a bound-crossing chatter risk distinct from simple amplitude scaling, flagged but not
evaluated this session). `gp-0x69aa`'s identity (the LERP axis in `FUN_00037fe6`). Full identity of the
7 lanes summed into `gp-0x6ad6`.

## Secondary finding: 0xC646C reuse in FUN_00036682 [VERIFIED, but NOT a fast carrier]

`FUN_00036682` ("filtered Sensor-B term," the 9th aggregator input, `assist_shaping_lanes()`'s
`filtered_36682`) computes `gp-0x6b48 + polarity*((gp-0x4f60 * cal_0xC646C) >> 15)` as part of its
target, where `0xC646C` (`tp+0x746c`) is **the exact same calibration cell that IS V38's 4x LKAS gain**
(byte-verified: `0xC646C = 3564` in `_v38_plain_image.bin` = `4 * 891` stock). So this term's
contribution from a given raw Sensor-B reading is now genuinely 4x larger than stock, by construction of
V38's single-cal-edit gain raise -- previously this cal's blast radius was audited only for the
int/float lockstep question (CLAUDE.md: "0xC646C has exactly 5 readers -- ... 0x36686, 0x3684a ... none
in FUN_00043e44" -- those two addresses ARE inside this function, so this was already a known reader,
just not previously connected to its role as an aggregator input). **However this specific term IS
genuinely low-pass filtered** -- its own final IIR gain at `0xC63D2 = 6` (Q10, i.e. 6/1024, tau ~ 170
cycles) is CONFIRMED to match the prior memory's claim (unlike the 0xC6450/0xC644A misread above), so
`FUN_00036682`'s output is not a tens-of-Hz carrier. Worth recording as a verified, V38-linked, but
NOT primary-vibration-relevant fact.

## Weaker candidates checked and largely ruled out this session

- `FUN_00034350` (gp-0x6bd0, damping): product of 5 LERP gain factors, 2 keyed on `gp-0x6a5e` AVG driver
  torque. Whether it is dormant hands-off depends on the AVG-torque tables' Y-value AT X=0
  (`0xC9CCC`/`0xC9E9C`), which were NOT dumped this session -- **[OPEN]**, not confirmed either way.
  Already independently downgraded in `model/eps_lkas_chain_model.py` for a different reason (the sign-flip
  hypothesis, pinned positive in normal driving).
- `FUN_00036c12` (gp-0x6b26, friction): primary key is `gp-0x6a5e` AVG DRIVER torque (not command-
  derived, not motor-reaction-derived) -- structurally this predicts MORE contribution with MORE driver
  hand torque, the OPPOSITE of the operator's report that the vibration vanishes when the driver adds
  torque. Weak candidate on structural grounds alone; table values not dumped to confirm the dormant-at-
  zero assumption.
- Base assist boost (`gp-0x6bbe`, `FUN_00034a72`): the already-byte-dumped boost curve
  (`ASSIST_BOOST_CURVE` mode 10, Y=(541,639,653,551,439,439)) has a **NONZERO floor at X=0** -- boost is
  NOT dormant hands-off. But it is a slow function of AVG torque (rate-limited to 13880/tick) with no
  fast/derivative term, so it is a DC-offset contributor, not a vibration carrier.

## Related
[[reference-accord-post-governor-comp-add]] -- sibling aggregator-lane documentation, the zero-type gate
re-verification this note relies on.
[[reference-accord-r26-adaptive-lane-full-trace-and-sign]] -- the other confirmed Sensor-B-derived lane
family (r24/r26), both already falsified on-car (V39/V42); this lane is a THIRD, independent, untested
carrier of Sensor-B content that neither of those builds touches.
[[reference-accord-gp4f64-three-consumers]], [[reference-accord-shaper-fun42af8]] -- downstream of the
aggregator, unaffected by this finding.

**ACTION FOR OPERATOR/TEAM-LEAD**: the `model/eps_lkas_chain_model.py` docstring for `FUN_0003a382` (and the
CLAUDE.md-adjacent characterization deriving from it) should be corrected -- the "VERY heavily damped"
verdict is wrong at these cal values. I have not edited the golden model or CLAUDE.md myself; flagging
per this kit's "ask before updating a memory you didn't just verify fresh" norm, though in this case I
DID verify fresh (3-image byte read) and am proposing the correction, not asserting it silently.
