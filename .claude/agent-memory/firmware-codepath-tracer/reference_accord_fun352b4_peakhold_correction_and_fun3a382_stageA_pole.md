---
name: reference-accord-fun352b4-peakhold-correction-and-fun3a382-stageA-pole
description: CORRECTS reference_accord_fun352b4_untested_carrier_and_dead_biquad -- the "10-point LERP table near cal tp+0x6444" does not exist (that address is gp-relative RAM, disasm-confirmed), and the lane's output stage is a magnitude peak-hold, not a near-unity passthrough -- downgrades gp-0x6b86 as a 21Hz carrier. Separately pins FUN_0003a382's Stage A pole (cal 0xC6450, gp-0x367c) as an EXACT unity-gain identity at all frequencies, single-reader, no lockstep, untouched by any build including V43.
metadata:
  type: reference
---

# Correction + new pole ID -- Accord TVA-A160, traced 2026-07-20/21 for team-lead's road-feel/21Hz feedback audit

Dispatched to rank base-assist feed-forward lanes by 21Hz positive-feedback contribution. Both
`FUN_000352b4` (`gp-0x6b86`) and `FUN_0003a382` (`gp-0x6ad4`) had prior sessions' partial characterizations
in memory. This session re-traced `FUN_000352b4` at the **disassembly** level (not just decompile) and
found the prior session's "10-point LERP table" premise was wrong, plus quantified `FUN_0003a382`'s
untested Stage A pole precisely.

## CORRECTION: no static calibration LERP table in `FUN_000352b4` at "tp+0x6444"

[[reference-accord-fun352b4-untested-carrier-and-dead-biquad]] (prior session, this same file set) described
"a 10-point piecewise-linear LERP (a static lookup ... cal region around `tp+0x6444`)" but flagged the
table itself as "NOT fully quantified ... NOT byte-dumped this session." Fresh disassembly this session
resolves it: **`0x35378`: `movea -0x6444,gp,ep`** -- this is a **gp-relative RAM** base register load, not
`tp` (calibration/ROM). There is no static table to dump at that address; it does not exist as calibration
data. What's actually there is a self-referential RAM "moving curve": ~9 knot-points individually kept
strictly-monotonic-increasing by a helper function `FUN_000352a0`, which decompiles to:
```c
uint FUN_000352a0(uint param_1, uint param_2) {
  param_1 &= 0xffff; param_2 &= 0xffff;
  if ((int)(param_1-param_2) < 0 || param_1==param_2) param_1 = param_2+1 & 0xffff;
  return param_1;
}
```
i.e. "return param_1 if it's strictly greater than param_2, else param_2+1" -- a **monotonicity enforcer**,
NOT a rate/slew limiter as its call-site pattern first suggested. The knot targets it enforces ordering on
are themselves prior RAM state (from `gp-0x6420..-0x6444`), not calibration-sourced within this function.

## CORRECTION: the lane's output combinator is a magnitude PEAK-HOLD, not a passthrough

Disasm-confirmed at `0x35884-0x358dc` (not just decompile pseudocode): a comparison `cmp r10,r13` where
`r10=abs(gp-0x6b7a)` (previously held magnitude) and `r13` = freshly LERP-interpolated candidate magnitude,
sets a flag (`setfc r9`) consumed by `cmovne r8,r12,r10` at `0x358d0` -- **the new candidate is only adopted
if it EXCEEDS the currently-held magnitude; otherwise the prior value is retained bit-for-bit.** This is a
classic peak/envelope-hold nonlinearity. For a bounded-amplitude periodic input (e.g. a steady 21Hz
oscillation), a peak-hold converges toward the oscillation's ENVELOPE (~DC), not an in-phase replica of the
waveform -- it does not reproduce instantaneous phase at all. It only ratchets upward meaningfully if
successive peaks are GROWING (onset of an underdamped oscillation), which is a slow-timescale effect
distinct from steady-state 21Hz carrier gain.

Downstream of the hold there's a genuine dynamically-gained IIR (state `gp-0x381c`, gain term clamped to
`[2,0xcc]`=`[2,204]` out of a `>>0xb`=2048 divisor, i.e. α∈[0.001,0.0996]). Sole caller of `FUN_000352b4`
is `FUN_0002214a` -- **the CONFIRMED ~1kHz control task** (per `control-task-tick-confirmed-1khz`), so at
its fastest setting (α≈0.0996, fs=1000Hz) this IIR's corner is ≈16Hz (`α·fs/2π`), same order as the 21Hz
target -- real attenuation even in the best case, more at typical (lower) α.

**Biquad gate re-confirmed dead, fresh byte read this session**: `0xC649B = 0x00` (bytes at `0xC6498`:
`01 01 00 00 00 00 01 01`, offset+3 = `0xC649B` = `0x00`). Matches prior session's finding, now
independently re-verified.

**Net verdict, corrected**: `gp-0x6b86` structurally resists carrying a 21Hz in-phase signal (peak-hold
kills phase reproduction; the IIR provides real attenuation even at its fastest setting). **Downgrade from
"TOP PRIORITY / untested, ±12288 widest gate" to LOW-priority as a 21Hz carrier.** The widest-aggregator-gate
fact from the prior session remains true and byte-verified, but a wide gate on a lane that structurally
can't carry the frequency in question is not load-bearing for this specific hypothesis.

## `FUN_0003a382` Stage A pole (`0xC6450`, `gp-0x367c`) -- the strongest live finding this session

[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] (prior session, 3-image byte-verified)
already established both `0xC6450` and `0xC644A` = 1024 (Q10 unity), and that V43 (FLASHED, per CLAUDE.md)
lowered **`0xC644A`** (Stage C's pole) 1024→32 and it did NOT fix the vibration on-car. That leaves
**Stage A's `0xC6450` completely untested** -- still live, still exactly unity.

Because `1024 = 2^10` divides the `>>10` shift with zero rounding loss, Stage A's update rule
`state_new = state + (target-state)*1024>>10` collapses to **`state_new == target`, exactly, every cycle**
-- an algebraic identity. This is gain = 1.0 **at every frequency including 21Hz, by construction**, not an
approximation or a measurement -- the strongest "unfiltered" claim substantiated in this whole audit.

**New this session -- blast-radius / lockstep check on `0xC6450`, before proposing it as an edit target:**
- `search_instructions` operand scan for "7450": **3 hits total, only 1 real** -- `0x3a7f0` inside
  `FUN_0003a382` (`ld.hu 0x7450, tp, r13`). The other two (`0x744f0`, `0x744fe` in unrelated function
  `FUN_00071272`) are branch-target-address-text false positives (their operand is a jump target
  `0x00074502`/`0x0007450c` that happens to contain the substring "7450") -- same false-positive class as
  prior sessions' finds, excluded with stated reason.
- `gp-0x367c` (Stage A's RAM state): exactly one reader (`0x3a7ec`) + one writer (`0x3a826`), both inside
  `FUN_0003a382` itself. **No shadow-lockstep pair, no float mirror, no external consumer** -- clean
  single-site scalar constant, same low-blast-radius profile V43 already validated safe for the sibling
  `0xC644A`.
- Sole caller of `FUN_0003a382` is also `FUN_0002214a` (1kHz control task) -- confirms the rate for this
  lane too (previously only "compatible with," now directly confirmed via the caller check).

## Proposed cal-only reduction (not applied -- proposal only)

**`0xC6450` 1024 → 32** -- mirrors V43's already-flown, fault-free precedent on the sibling constant
`0xC644A` in the same function. Converts Stage A from exact identity to a real first-order low-pass,
corner ≈ α·fs/2π ≈ 0.03×1000/6.28 ≈ 4.8Hz -- preserves low-frequency road-feel content, cuts 21Hz by
roughly 12-13dB (single-pole rolloff estimate `20·log10(21/4.8)`). Single reader, no lockstep, no mirror.

## Related
[[reference-accord-fun352b4-untested-carrier-and-dead-biquad]] -- the prior session's characterization;
this file corrects its LERP-table premise and output-stage read, but its aggregator-gate-width table and
biquad-coefficient dump remain valid and are not superseded.
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] -- source of the Stage A/B/C gain
values this file builds on; this file adds the blast-radius check and the concrete reduction proposal.
[[control-task-tick-confirmed-1khz]] -- both `FUN_000352b4` and `FUN_0003a382`'s sole caller
(`FUN_0002214a`) confirmed as the 1kHz control task this session, resolving a previously-open rate question
for both lanes.
