---
name: reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected
description: Fresh disasm of FUN_000389ec's 9-slot slew mechanism that populates gp-0x6442-family (the raw per-segment values feeding gp-0x69a4="a", r26's weight). Confirms slot-0 hard-zero + a genuine floor-at-zero/snap-to-step(cal 0xC6178=5274) discontinuity. CORRECTS a sibling agent's (F4) claim that 0xC6564's causal link to the array is "broken" -- the link is real (traced through FUN_00039702's blend into the -0x3714 target array), only the seed VALUE is zero. Two new, never-before-referenced cals found (0xC6178, 0xC6468) that ARE single-purpose editable levers on the rate/threshold side, though the target/shape side (FUN_000352b4's own second adaptive stage, FUN_000352a0 + gp-0x69a0) remains unclosed.
metadata:
  type: reference
---

# `gp-0x69a4` ("a", r26's relative-weight index) — slot-fill mechanism traced fresh, 2026-08-05

Dispatched by team-lead after a sibling agent (F4) traced `a`'s LERP INDEX formula
(`abs(clamp(gp-0x4f60,±0xC6200) + gp-0x6b4a)`, disasm `0x354CE-0x35528`) and flagged the underlying
10-segment curve as "not a single static ROM table" — a live 3-function chain `FUN_00039702 ->
FUN_000389ec -> FUN_000352b4`, with `FUN_0003897a` and two boost-curve cal families (`tp+0x769a-0x76b4`,
`tp+0x7b66-0x7b98`) left as gaps. This session closes the GATE-FILL mechanism gap; the curve-shape gap
(F4's other open item) is NOT closed — see Open Items.

## The 9-slot slew mechanism [EVIDENCE, fresh `disassemble_bytes` this session, `0x38fa0-0x390d6`]

`FUN_000389ec` populates `gp-0x6444`(slot 0) through `gp-0x6432`(slot 9), the RAW per-segment array
`FUN_000352b4` later reads (as `uVar17` in its own build loop, confirmed by cross-reading both
functions' decompiles):

- **Slot 0 (`gp-0x6444`) is unconditionally HARD-ZEROED every cycle** (`0x38fee: st.h r0,-0x6444,gp`
  — register r0 is architecturally always 0 on V850). Confirms F4's claim exactly.
- **Slots 1-9 (`gp-0x6442` downward, loop `0x39018-0x390d6`, r29=1..9)** are filled by:
```
slew_target = (r23 * target[-0x3714+off]) >> 0x12        # target array written by FUN_00039702, see below
delta       = (r17 * (prior[-0x373c+off] - slew_target)) >> 0xe    # r17 = a runtime scale (source not traced)
if delta very negative              -> slot = 0                     # HARD FLOOR at zero
elif delta < cal(0xC6178) = 5274    -> slot = cal(0xC6178) = 5274    # SNAP to the step-cal, NOT a smooth ramp
else                                 -> slot = delta                 # linear pass-through
```
Every store is lockstep-shadowed (`gp-0x4bf6`/`-0x4be2` families, standard `FUN_0006b9fa` fault-check
pattern used throughout this firmware) — no surprises in the fault-monitor layer.
`r23` (the target-scale multiplier) = `(cal(0xC6468)=2639 * cal(0xC613A)=1159) >> 7 << 10 / 1024`-ish
Q-format rescale, disasm `0x38fb0-0x38fc8`. `0xC613A` is the SAME multi-purpose cal V68's own docstring
flags as reused elsewhere and high-risk to touch (bus-counts-per-degps scale chain).

**This is a genuine, freshly-found NEAR-ZERO discontinuity**: for small positive target-vs-prior deltas
(0 < delta < 5274), the slot jumps directly to 5274 rather than ramping proportionally — a threshold-snap,
not a smooth curve. Distinct in kind from every other candidate found in this session's earlier sweep
(the flat-zero angle-tracking table, the wiring-isolated pre-gain deadband) — this one is architecturally
present and unresolved to a magnitude/frequency verdict. See Open Items and the parametric-pump caveat
below before treating it as a finding rather than a lead.

## `0xC6564`'s causal link — CORRECTS F4's retraction; PRACTICAL conclusion likely still holds

[EVIDENCE, fresh decompile of `FUN_00039702`, `0x39702-0x3a1xx`, cross-checked against the disasm above]
`FUN_00039702` computes, for each of 10 segments:
```
local_5c[2..11] = cal(tp+0x7564..0x7588, i.e. 0xC6564-family)/1024 + gp-0x6444-family/1024
```
then blends (`fVar22*local_5c[N] + otherFvar*fVar7`) into `gp-0x6704/6700/66f8/66fc/66f4/66f0/66ec/
66e8/66e4/66e0` — the SAME RAM region `FUN_000389ec` reads at its own entry (confirmed by address match
against my earlier, separate decompile of `FUN_000389ec`'s opening lines, done in an unrelated part of
this same session's work) and eventually turns into the `-0x3714`-relative `slew_target` array the loop
above reads. **The causal chain from `0xC6564` to the array IS intact — F4's "does not write back"
framing is WRONG on the mechanism.**

However, **`0xC6564`, 40 bytes, re-read fresh this session: still all zero** — matching F4's own byte
claim and every `builds/v50_v79/build_v67_tva.py`-through-`builds/v50_v79/build_v70_tva.py` assertion on record (`R26_AVG_CAL = 0xC6564`,
"40 bytes of exact zero == the r26-inert record"). So `0xC6564`'s specific CONTRIBUTION genuinely is 0 —
the mechanism works, the seed is just empty. **Net effect on the standing memory chain**
([[reference-accord-r26-is-structurally-inert]], LEG 2 "downgraded to belief... link to gp-0x69a4 never
verified"): the link is now verified, and the PRACTICAL conclusion (0xC6564 contributes nothing on the
current calibration) is UNCHANGED — but the REASONING should be corrected from "link broken" to "link
intact, seed empty," which matters for anyone considering editing `0xC6564` in future (a broken link
would make that edit pointless; an intact one with a zero seed means it WOULD propagate if raised).

## Calibration-addressability — partially overturns F4's "no single ROM cal" verdict

Two cals found this round, **both with zero mentions in any `build_v*_tva.py`** (genuinely unexplored,
not RULE-4-style "referenced but never written" like `0xC61B8` — literally never named before):
- **`0xC6178`** (tp+0x7178) = **5274** — the snap-threshold in the slot-fill loop, directly sizes the
  discontinuity above. Single-purpose looking (only this one loop reads it, not independently re-swept
  for other readers this session — flag before building on it).
- **`0xC6468`** (tp+0x7468) = **2639** — part of the slew-rate scale `r23`, combined with the
  already-flagged-multi-purpose `0xC613A`.
So: the RATE/THRESHOLD side of this mechanism DOES have real, addressable, apparently single-purpose
cals — F4's "no single ROM cal you could edit" verdict is overturned for that side. The TARGET/SHAPE
side (see below) is NOT overturned — no single cal found there yet.

## Open items — the actual numeric shape of `a` at low index is NOT closed

`FUN_000389ec`'s 9 raw slot values feed into a SECOND, separate adaptive stage inside `FUN_000352b4`
itself — a build loop using `FUN_000352a0` (not decompiled this session) plus `gp-0x69a0` (producer not
traced), which constructs `a`'s ACTUAL X/Y breakpoint arrays before the index-driven interpolation F4
already mapped. **No literal X/Y numbers for `a`'s first 1-2 segments are established from this session's
work.** Also open: `r17`'s source (the runtime scale multiplying the delta each cycle), the exact sign
convention on the "very negative" floor branch (read from disasm control-flow, not independently
simulated), and whether `0xC6178`/`0xC6468` have OTHER readers elsewhere in the image (not re-swept).

**Parametric-pump caveat, stated explicitly per team-lead's standing instruction**: this discontinuity is
INTERNAL to how the 9-slot array gets (re)computed cycle to cycle — a different signal, different
timescale from the boost-amplitude-index modulation V60 closed (measured depth 1.002-1.004, "index never
leaves the plateau"). Not shown to collide with that closed family, but also NOT established as a live
mechanism — no time-domain simulation or telemetry run this session. Report as a structural lead only.

## Related
[[reference-accord-r26-is-structurally-inert]] — the memory chain this session's `0xC6564` finding
refines (LEG 2's "link never verified" is now verified, conclusion unchanged).
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] — this session's earlier
work, same overall investigation (near-centre grind #1 structure hunt).
