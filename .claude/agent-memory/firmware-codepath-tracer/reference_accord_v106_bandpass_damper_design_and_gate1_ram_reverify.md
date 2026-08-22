---
name: reference_accord_v106_bandpass_damper_design_and_gate1_ram_reverify
description: "V106 band-pass damper proposal: 2-stage real-pole EMA cascade (Honda's own idiom, zero complex poles, cannot ring) reading gp-0x6abe, added to FUN_00034350's r8 before its own clamp at 0x346a4. Coefficients, computed magnitude/phase table 0.5-46Hz, and the independent GATE-1 re-verification of the 5 candidate RAM cells (gp-0x6d08/6d04/6d00/6de8/6de4) via Ghidra + raw Python dual-encoding scan with every raw hit adjudicated (all false positives: ori-immediate and jarl aliasing). Also: the junction-dilution-adjusted efficiency ratio between 7.79Hz and 21.73Hz for this exact design."
metadata:
  type: reference
---

# V106 band-pass damper — filter design + independently re-verified GATE-1 RAM

2026-08-22, `damper-cave` subagent, for the operator's band-limited-damper mandate.

## The filter [EVIDENCE, own derivation + integer-arithmetic simulation cross-check]

Structure (Honda's own EMA idiom, `y[n]=y[n-1]+((x[n]-y[n-1])*K)>>shift`, used verbatim elsewhere in
this firmware e.g. `FUN_00041464`'s own accel EMAs):
```python
s1 += ((x - s1) * 11) >> 9          # a1 = 11/512 = 0.021484, corner 3.457 Hz  (DC-blocking LP)
hp  = x - s1                         # highpass = input minus its own lowpass; H(0)=0 EXACTLY, by construction
s2 += ((hp - s2) * 33) >> 8          # a2 = 33/256 = 0.128906, corner 21.999 Hz (top LP)
bp  = s2                             # band-pass output
out = -K * bp                        # sign convention: see FUN_00034350's own -sgn(gp-0x6abe), matched
```
Input `x = gp-0x6abe` (Honda's own slew-limited signed motor rate — see
[[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]]). **2 persistent 32-bit state
words (`s1`,`s2`), NO complex poles anywhere** — both stages are independent real-axis EMAs; the
structure cannot ring or exhibit V48B's Q≈3.2 resonant-pole tuning sensitivity by construction.

### Computed response (fs=1000Hz, verified by a from-scratch integer Q16 simulation matching the
closed-form prediction to 4 significant figures at 7.79/21.73/44.9 Hz)
```
 f(Hz)   |H_BP|  phase   |  combined with gp-0x6abe's OWN 1-pole lag (a=37/128, corner 54.8Hz)
  0.50   0.142  +80.6°   |  0.142  +80.1°
  1.00   0.275  +71.4°   |  0.275  +70.5°
  3.00   0.642  +41.8°   |  0.641  +39.1°
  6.00   0.827  +15.7°   |  0.822  +10.4°
  7.79   0.852   +5.8°   |  0.844   -1.1°   <- near-pure damping (cos5.8°=0.995)
  9.00   0.855   +0.3°   |  0.843   -7.6°
 12.00   0.834  -10.5°   |  0.815  -20.9°
 18.00   0.752  -25.3°   |  0.714  -40.6°
 21.73   0.695  -31.8°   |  0.646  -50.0°   <- cos31.8°=0.85: still 85% dissipative, no sign flip
 26.00   0.634  -37.7°   |  0.572  -58.9°
 40.00   0.476  -49.3°   |  0.384  -78.9°
 42.30   0.456  -50.5°   |  0.361  -81.2°
 44.90   0.435  -51.7°   |  0.336  -83.6°   <- cos83.6°=0.11: near-neutral, still NOT past 90° (not anti-damping)
```
**DC and 0-3Hz**: exact zero at DC by construction; 0.5Hz attenuated to 14%, 1Hz to 28% — meets the
operator's "zero at DC, minimal at 0-3Hz" requirement without being literally zero at 3Hz (64%, the edge
of the target passband, unavoidable trade against phase purity at 7.79/21.73 — see design-tradeoff note).

**Design tradeoff, stated explicitly, not hidden**: a Pareto sweep (single-pole-per-side vs 2-pole-top)
showed 2-pole-top designs buy much stronger 44.9Hz rejection (down to ~0.14-0.19) at the cost of
30-90° MORE phase error at 21.73Hz specifically — turning a chunk of the grind#1 contribution reactive
rather than dissipative. **This design deliberately chose single-pole-per-side to keep phase small at
BOTH target frequencies**, accepting weaker (~0.44, -52°) rejection at 44.9Hz. Given the structure has
NO resonant peak anywhere (monotonic real-pole rolloff), 44.9Hz content that leaks through is at worst
near-neutral (phase 84-90° band), not reinforcing. If grind#2 (Q≈37) proves sensitive to even this
residual, the 2-pole-top alternative is on record above as the fallback, with its own cost named.

## Sign & entry point [EVIDENCE]
`out = -K*bp` added to `r8` (Honda's `uVar7`) at hook `0x346a4` inside `FUN_00034350`, BEFORE Honda's own
`clamp(r8,-r6,+r6)`+shadow-store at `0x34720`. Matches Honda's own `sign=-sgn(gp-0x6abe)` convention for
`gp-0x6bd0` exactly — this is not a new sign rule, it is Honda's rule extended to a filtered version of
the same signal.

## Junction-dilution-adjusted efficiency, 7.79Hz vs 21.73Hz [EVIDENCE for the two inputs, arithmetic is mine]
Using this filter's own |H| (0.852 @7.79, 0.695 @21.73) and the independently-measured lane:sum
cancellation law from [[reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed]]
(4:1 @6-9Hz, 1.68:1 @21-22.5Hz — measured for a generic junction addend, `gp-0x6bd0` is literally one of
the addends that law was measured over, so it transfers directly to this term):
```
net_survival(7.79Hz)  ~= 0.852 / 4.00 = 0.213   (relative units, per unit of K)
net_survival(21.73Hz) ~= 0.695 / 1.68 = 0.414
ratio = 0.414 / 0.213 ~= 1.94x
```
**⇒ At a single flat gain K, this design delivers ~1.9x more NET effect (after the loop's own
compensating reaction) at grind#1 (21.73Hz) than at the ratchet (7.79Hz).** Both survive (neither is
fully cancelled), but a K sized to move the 6-9Hz ratchet meaningfully will deliver a proportionally
larger effect at 21.73Hz — consistent with, and now quantitatively explaining, the retrodiction in the
compensator memory that V62/V88 (both grind#1-band edits) are the kit's only two measured wins.

## GATE-1 — 5 candidate RAM cells, independently re-verified [EVIDENCE, 2 methods, every hit adjudicated]
Candidates (from [[reference_accord_gate1_write_only_diag_taps_are_the_best_cave_ram]], `tq-lowpass`,
same day): `gp-0x6d08`,`gp-0x6d04`,`gp-0x6d00`,`gp-0x6de8`,`gp-0x6de4`, all in `FUN_0003b66a` (task 1,
1kHz, sole caller `FUN_0002214a` per fresh `get_function_callers`).

Method: (a) `search_instructions` on the exact operand text — 1 hit each, all `st.w`, matching the
memory's cited addresses exactly. (b) A raw Python LE byte scan for BOTH the 4-byte disp16 form (using
the documented `hw2=(disp|1)` .h/.w discriminator-bit trap) AND the 6-byte extended-displacement form
(`disp=(sext16(hw2)<<7)|((hw1>>4)&0x7F)`), across the whole 1MB image. This surfaced 4 additional raw
hits beyond the 5 known writers. **Every one was disassembled at the actual address and confirmed a
false positive**: three are `ori 0x9300,r0,r7` (an unrelated immediate-mask instruction whose imm16
coincides numerically with `-0x6d00`'s two's-complement pattern; base reg is `r0` not `gp`), one is a
`jarl` call instruction (Format-V aliasing), one is a `mov r10,r28`+`jarl` pair my 6-byte scan mis-parsed
across an instruction boundary (not even landing on a real instruction start). **Result: all 5 cells have
exactly ONE gp-relative access image-wide (Honda's own writer) and ZERO readers, to a higher standard of
adjudication than any prior static check in this kit's record.**

⚠ **Static clearance is still not sufficient by the kit's own rule** (`gp-0x1500` passed both static
methods and still failed on-car via V50P, being a register-indirect-dispatched I/O-mailbox slot). A live
probe on 1-2 of these 5 cells (comparator/magnitude channel over CAN, V50P-class) is the recommended next
step before trusting them for real filter state. Proposed allocation: `s1 -> gp-0x6d08`, `s2 -> gp-0x6de8`
(arbitrary pick among the 5; all equally clean by this session's re-verification).

Related: [[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]],
[[reference_accord_v39_v48b_1khz_hook_precedent_correction]],
[[reference_accord_gate1_write_only_diag_taps_are_the_best_cave_ram]].
