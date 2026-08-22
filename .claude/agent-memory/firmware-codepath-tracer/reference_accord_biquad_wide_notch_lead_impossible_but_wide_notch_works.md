---
name: reference_accord_biquad_wide_notch_lead_impossible_but_wide_notch_works
description: Exhaustive grid search (zero 5-25Hz x pole up to 35Hz x r 0.10-0.98, 595+ configs checked against max|H| over 28-200Hz) PROVES the biquad's palindromic-numerator structure cannot deliver lead phase in 18-24Hz while staying <=1.0 above 28Hz -- zero passing configs in the lead (zero<pole) topology. But V105's OWN topology (zero>pole, a true notch) WIDENED via lower pole-radius r and re-centered DOES satisfy the constraint: two candidates given (pole=14/r=.95/zero=20.5, and pole=14/r=.90/zero=22.0, the latter halving V105's own ring time) delivering 4-11x more attenuation than V105 across the whole 18-24Hz migration range with no new resonance at 6-18Hz and grind #2/#3 both attenuated not excited.
metadata:
  type: reference
---

# Wide-stopband biquad — lead is structurally impossible under the ceiling constraint; a wide notch is not

2026-08-22, `dynamics-designer` task (team-lead's re-optimization after my first candidate excited
grind #2 at 42Hz). Extends [[reference_accord_biquad_lead_compensator_structural_nogo]] (that file
proved lead is impossible AT ALL for a classical zero-below-pole placement; this one adds the specific
"and stay under a hard 28Hz+ ceiling" constraint, and finds the escape valve — drop lead, keep notch).

## 🛑 PROVEN: lead phase + ≤0dB above 28Hz is impossible for this structure [EVIDENCE, exhaustive grid]
Zero 5.0-25.0Hz (0.5Hz steps) × pole (zero+0.5)-35.5Hz (0.5Hz steps) × r 0.10-0.98 (0.05 steps),
checked against `max|H|` over 28-200Hz. **Zero of the several thousand zero<pole (lead) configurations
tested pass ≤1.0.** Not a limited-grid artifact — r as low as 0.10 tested, wide zero/pole spans tested.
This is a structural result: the topology that gives lead phase (zero below pole, uncancelled
resonance beyond the pole) always produces a magnitude excursion above unity somewhere past 28Hz. Kills
the "lead" objective specifically for this 4-cal biquad; does not kill the notch-shape use of it.

## The working alternative — V105's OWN zero>pole topology, widened [EVIDENCE]
Same exhaustive search, zero>pole (matching V105's own ordering): **595 configurations pass
`max|H|`≤1.0 over 28-200Hz.** Two Pareto points selected:

**A — pole=14.0Hz r=0.95 zero=20.5Hz** (max coverage, no ring-time win):
```
a1=-1.89265386  a2=0.9025  b1=-1.98343212  c4=0.594291047
```
Worst-case |H| across 18-24Hz coverage grid = **-13.96dB** (vs V105's own -2.56dB — ~11x deeper at the
worst point). Global max|H| 0-500Hz = 1.000000 exactly (V105's property held). Max|H| 28-500Hz=0.620
(comfortable margin). Grind #2 (44.9Hz)=-5.60dB, grind #3 (46Hz)=-5.52dB, BOTH ATTENUATED not excited.
No resonance anywhere in 6-18Hz checked explicitly (monotonic 0.97->0.20, no bump near the 6-9Hz
ratchet). Ring = 89.8ms, UNCHANGED from V105 (same r).

**B — pole=14.0Hz r=0.90 zero=22.0Hz** (real ring-time win):
```
a1=-1.7930405  a2=0.81  b1=-1.98092285  c4=0.888995724
```
Worst-case coverage attenuation -11.93 to -30.5dB across 18-24Hz. Max|H| 30-60Hz=**0.827** (clean
margin); max 28-500Hz=0.982 (edge case sits at Nyquist/500Hz, not in any physical band — 30-60Hz is
where it matters and that's clean). Grind #2/#3: -3.08/-2.92dB, attenuated. No 6-18Hz resonance
(peak 0.91 at 6Hz, monotonic decline). **Ring = 43.7ms — ~2.05x faster than V105's 89.8ms**, the
ring-time win the operator/team-lead wanted preserved.

## Phase character across the coverage band
Below the null: LAG (18-20Hz, -76° to -108° depending on candidate). Above the null: LEAD (21.5-24Hz,
+45° to +87°). **The measured 6x migration range (20.48-22.98Hz) sits almost entirely ABOVE the null**
— in the region delivering BOTH real attenuation AND lead phase simultaneously, which V105 never
achieved at any of its own f0 points (V105's phase at f0 was always LAG, -78 to -100°).

## Highway band, side effect not a trade-off
At 26Hz: candidate A -11.4dB, candidate B -13.5dB — both meaningfully better than V105's own highway
number. Unlike a narrow re-centered notch (which `a5-scorer` showed just relocates the mode), widening
did not appear to trade low-speed for highway performance in this design — both improved.

## Falsifiable relocation prediction [BELIEF, no L(jw) exists to make this rigorous]
`a5-scorer`'s "mode slides to the nearest local opening" logic correctly predicted V105's 20.48Hz
escape (V105's null recovered steeply and NEARBY — from -24dB to -2.56dB in just 4.4Hz). Neither
candidate here offers a comparably close, steep opening — the shape stays deep and wide from ~18 to
~24Hz, recovering only gradually beyond (candidate A: -11.4dB@26, -8.6dB@30, -5.8dB@42.3 — nothing
within 15Hz of the coverage band reaches back to unity). Prediction: if the mode relocates under either
candidate, it should move UP past ~28-35Hz, not escape downward or nearby the way V105's did. Not
provable without a real loop-gain model; stated as a falsifiable claim for the next drive.

## Related
[[reference_accord_biquad_lead_compensator_structural_nogo]] (the original lead-impossibility finding
this extends with the hard 28Hz+ ceiling), [[reference_accord_biquad_26hz_notch_design_and_dc_hf_traps]]
(V105's own design, the baseline these candidates are compared against).
