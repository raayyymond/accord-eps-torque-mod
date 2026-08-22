---
name: reference_accord_model_feeds_reference_not_error_and_fprime_flatten_traps
description: Answers the operator's architecture question (does the assist chain react to estimated driver torque or total bar torque) -- Honda's self-torque estimate MODEL (gp-0x6bfc, FUN_0003b8f6) exists but feeds only the PID's REFERENCE (gp-0x6ad6) via Path 2, never corrects the raw gp-0x4f60 sensor before it becomes the PID's error term (confirmed fresh in FUN_0003a382's decompile). A hypothetical sensor-side correction would be the same topological class of edit that bricked V48B. Also: the f' LERP is a real flash-table lever, cal-reachable, but 0xC63AE and 0xC6200 are BOTH "flatten into a relay" traps (the V72/V80 mechanism), and 0xC6200 is additionally self-cancelling and a fault-detection threshold -- do not edit either.
metadata:
  type: reference
---

# MODEL feeds the reference, not the error — and the f′ LERP has two do-not-edit neighbours

Traced 2026-08-22, task `loop-topology` round 2 (team-lead mandate: map the architectural fix for
"assist chain reacts to total bar torque, not driver torque," cal-only boundary lifted, caves in scope
but staged/gated). Full report sent to team-lead in 2 messages. Builds directly on
[[reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open]] (same
task, round 1) — that file's DC-cancellation resolution used the same `FUN_0003b8f6` decompile this
file's finding depends on.

## [EVIDENCE, fresh decompile this session, `FUN_0003a382` @0x3a382] The PID's error is RAW `gp-0x4f60`, never a corrected version

```c
uVar24 = clamp(gp-0x6ad6, +-cal(0xC6200)=8192);        // the REFERENCE, clamped
iVar30 = (int)*(short *)(gp-0x4f60) - uVar24;           // <-- THE ERROR. RAW sensor minus reference.
iVar31 = clamp(iVar30, +-0x2800);
... P/I/D cascade runs on this iVar31 -> gp-0x6ad4 (PID output)
```
No reference to `gp-0x6bfc`/`gp-0x6bfe` (MODEL) anywhere in this function's body — checked, none appear.
`gp-0x4f60` is the raw torsion-bar reading, undifferentiated driver+motor torque, exactly the signal the
operator's torsion-bar objection is about.

## The self-torque estimate DOES exist — `FUN_0003b8f6`'s MODEL — but only reaches the REFERENCE side

`MODEL` (`gp-0x6bfc`/`gp-0x6bfe`) is computed at 1kHz from `gp-0x6b98` (delivered motor command) via a
2-stage EMA (`cmd_branch`) plus a smaller `gp-0x4f60`-derived sensor term, scaled by `0xC6468`. Its only
route into the loop: `iVar6` (`FUN_00038148` Stage 2) → `gp-0x6b70` → `FUN_00037fe6`'s 7-term sum →
`gp-0x6ad6` (the reference `FUN_0003a382` reads above). **It shapes what the PID is told to TRACK, never
what the PID is told it's tracking FROM.**

**And per the companion file's round-2 finding, at DC this contribution is ≈null** — Honda's own
construction (matched `0xC6468`/`polarity` scale factors between MODEL's cmd_branch and Stage-1's
composite, which includes the LKAS command as one of six terms) makes the estimate cancel its own
command-dependence before it reaches the reference. **Functionally: the self-torque-estimate machinery
is present, architecturally located on the correct (reference) side rather than the dangerous (error)
side, but empirically contributes almost nothing at steady state.** This is the precise sense in which
"the existing MODEL term is already doing this, and doing it badly."

## The minimal edit matching the operator's literal ask is HIGH RISK — same class as V48B

The literal ask ("respond to driver torque, not bar torque") maps to: subtract a rescaled MODEL from
`gp-0x4f60` BEFORE the `iVar30 = gp-0x4f60 - uVar24` line above. This is architecturally different from
`0xC6CD0` in a way that matters:

1. **`MODEL`'s transfer function (gp-0x6b98 counts → gp-0x4f60-equivalent counts) has never been
   validated against the real mechanical plant** (motor→gearbox→torsion bar→sensor) in gain OR phase.
   It's two generic EMA/FIR stages, not an explicit mechanical model. Wrong gain/phase at 18-30Hz
   specifically means the "correction" doesn't remove self-torque, it injects a wrong-shaped one.
2. **This edit is NOT exogenous the way `0xC6CD0` is** (see the companion file's Mason's-formula
   argument). `gp-0x4f60` is the loop's own feedback signal; subtracting anything built from `gp-0x6b98`
   (the loop's own output) from it before forming the error is a literal, direct reshaping of the loop's
   return ratio `L(s)`. This IS the "inside the loop, multiplies the return ratio" case the team-lead's
   original `0xC6CD0` hypothesis described — just the wrong address. Here it's the right description.
3. **🛑🛑 Same topological class as V48B's brick** [relayed, `reference_accord_v101_v102_resonance_mechanism_and_biquad_direction`
   §5]: V48B put a notch "on `gp-0x4f60`/errorterm, before fan-out," in the "ALWAYS-ON base-assist
   loop... whose closed-loop stability was never checked" — bricked on startup, parked, no LKAS command,
   full-authority oscillation. A self-torque subtraction at this exact point is the same move (modify
   what feeds the error, ahead of the PID, always-on) that produced this kit's worst incident.

**Staged path proposed to team-lead**: (1) telemetry-only validation of MODEL vs real hands-off `tq`
response before trusting it for anything: (2) a cal-only rebalancing of Stage-1's own weight on
`gp-0x6b4c` (`0xC63AA`) to deliberately un-cancel the LKAS-command-specific part of the reference,
staying reference-side; (3) only if both are favorable, the sensor-side correction, gated by a FULL
magnitude+phase Bode check across the whole always-on-loop frequency range (not just 18-30Hz), preceded
by a small-K partial dose and a comparator/telemetry cave before any symptom-scoring flight.

## [EVIDENCE, relayed + fresh-decompile-corroborated] The `f′` LERP: real flash lever, TWO do-not-edit neighbours

The LERP (`FUN_00038148` Stage 2's gain-scheduled nonlinearity) is a genuine 2-D flash table — mode +
speed indexed, 9-point X/Y records at `0xC7B40/C7C28/C7D10/C7DF8/C7EE0/C7FC8/C80B0`, populated via
`FUN_000382d8`→`FUN_000389ec` into RAM `gp-0x64b8[]`/`gp-0x641c[]`, read by the Stage-2 code I decompiled
this session. Honda enforces `f′≥0`/monotonicity at 3 independent ungated sites — editing the Y-values
directly to flatten the curve stays inside that envelope. **But per `accord-plant-model-residual-aggregator-chain.md`'s own explicit table
("THREE NEW 'FLATTEN A CURVE INTO A RELAY' HAZARDS... V80 is the recorded cost of making this error
once: the worst grinding in this car's history")**:
- `0xC63AE` (the LERP's INDEX SCALE, stock 1024) — never → 0: index becomes ≡0 ⇒ output ≡ ±Y[0], a
  CONSTANT ⇒ a pure relay at full authority.
- `0xC6200` (the ±8192 clamp) — never < Y[0]: produces the same relay from the other side.

`0xC6200` is doubly disqualified regardless: [EVIDENCE, `accord-c6200-clamps-the-pid-reference.md`,
cross-confirmed by my own fresh decompiles of BOTH `FUN_00038148` (clamps `gp-0x6b70`) and
`FUN_0003a382` (clamps `gp-0x6ad6`) this session] it has FOUR roles on the SAME cell (also
`FUN_000352b4`'s biquad-friction clamp and `FUN_000389ec`'s `Y[9]` ceiling), is **self-cancelling as a
global edit** (bounds both a numerator and the threshold it's compared against, so the ratio is
invariant to raising it), and its 5th reader (`0x39ff6`, `FUN_00039702`) is a **fault-detection
threshold in the motor-phase plausibility monitor** — raising it raises a fault trip point.
**⇒ `0xC6200` must not be proposed as a lever, and any "flatten f′" design must avoid `0xC63AE` too —
edit only the Y-values of the flash records themselves.**

⚠ Given the DC-cancellation finding above, flattening f′'s slope-variation is NOT obviously connected to
the gain-dose symptom (it changes sensitivity to whatever DOES reach `iVar6`, not to the LKAS command
specifically, which cancels out before arriving). Recommended NOT building this without first closing
what actually reaches `iVar6` in practice (Stage 1's telemetry step above).

## Related
[[reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open]] — the
round-1 finding this file's DC-cancellation citation depends on, same session.
[[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]] — V48B precedent, §5.
[[accord-plant-model-residual-aggregator-chain]], [[accord-c6200-clamps-the-pid-reference]],
[[accord-ram-lerp-is-flash-derived-and-fprime-is-nonneg]] — project memory this file's evidence rests on.
