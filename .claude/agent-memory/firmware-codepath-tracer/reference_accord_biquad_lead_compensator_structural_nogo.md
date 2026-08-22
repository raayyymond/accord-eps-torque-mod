---
name: reference_accord_biquad_lead_compensator_structural_nogo
description: The V105 notch biquad's 4-cal structure (H(z)=c4(1+b1z^-1+z^-2)/(1+a1z^-1+a2z^-2)) CANNOT be reconfigured as a phase-lead/damping-injection network at 18-30Hz -- every zero-below-pole configuration tried produces +8 to +22dB (2.7-16x) gain right in the target band, because a near-unit-circle pole always peaks near its own frequency and only a CO-LOCATED zero (a notch, not a lead) cancels it. Confirmed by direct calculation, not just structural argument.
metadata:
  type: reference
---

# Can the V105 biquad be reconfigured as a lead compensator at 18-30Hz? NO — confirmed by calculation, 2026-08-22

`dynamics-designer` task (V106 candidate C). Builds on the confirmed biquad structure from
[[reference_accord_biquad_26hz_notch_design_and_dc_hf_traps]] (same 4 cal cells, same palindromic-
numerator theorem) — extends it to a new question (lead instead of notch) that memory did not ask.

## The structural constraint [EVIDENCE — the confirmed V105 formula]
`H(z) = c4·(1 + b1·z⁻¹ + z⁻²) / (1 + a1·z⁻¹ + a2·z⁻²)`, only 4 free cal cells (`0xC60A8`=a1,
`0xC60AC`=a2, `0xC60B0`=b1, `0xC60B4`=c4). The numerator is ALWAYS palindromic (1, b1, 1) — there is no
separate b0/b2 cell — so its zeros are ALWAYS exactly on the unit circle (for |b1|≤2). A true
minimum-phase lead compensator needs a zero STRICTLY INSIDE the unit circle (closer to DC than the
pole) — this structure cannot produce one.

## The calculation [EVIDENCE — Python, exact confirmed formula, 4 configurations tried]
Tried explicit "zero below pole" (classic lead-network) placements:
```
zero 8Hz / pole 26Hz r=0.90:   +17.0 dB @21.9Hz, +19.7 dB @25.5Hz, +20.0 dB @26Hz  (phase +108..+123°)
zero 12Hz / pole 24Hz r=0.85:  +6.5 dB @21.9Hz, +9.6 dB @25.5Hz, +10.0 dB @26Hz
zero 15Hz / pole 22Hz r=0.80:  -0.1 dB @21.9Hz, +3.9 dB @26Hz  (tightest r tried)
zero 19Hz / pole 27Hz r=0.93 (closest zero/pole spacing tried): +0.9 dB @25.5Hz, +1.6 dB @26Hz
```
Every configuration that produces phase-lead character (+90-130°) in 18-30Hz ALSO produces a net
MAGNITUDE INCREASE in that same band — smallest tried is still +0.9 to +1.6 dB, i.e. still a gain
RAISE at the exact frequency where gain margin is already only 1.2-1.6× (1.6-4.1dB). This is the
opposite of a margin improvement — it would directly shrink the already-thin margin.

## Why — the topological reason, confirmed not just argued
A pole pair near the unit circle (r=0.80-0.95) ALWAYS produces a resonant peak near its own frequency,
regardless of where the zero sits — only a CO-LOCATED zero (adjacent frequency, as in the V105 notch:
zero 25.5Hz, pole 22.0Hz, only 3.5Hz apart) cancels enough of that peak to avoid it. V105's own report
confirms this directly: `max|H| over 0-500Hz = 0.999999564, NEVER reaches unity` — zero peaking
anywhere, because the zero/pole pair is adjacent. Separating zero and pole to create a lead REGION
between them necessarily uncovers the pole's own peak in that gap.

## Verdict
**NO-GO, confirmed by direct calculation, not merely structural intuition.** This specific 4-parameter
hardware biquad can only implement notch-family shapes (deep null, adjacent zero/pole) or harmful
resonant-boost-with-adjacent-notch shapes (separated zero/pole) — never a clean lead. A genuine lead
compensator at 18-30Hz would need a DIFFERENT filter topology (a zero strictly inside the unit circle,
i.e. a real/near-DC zero, which this hardware's cal layout cannot express) — that would require a cave
with new coefficient handling, not a reconfiguration of the existing cells.

## Related
[[reference_accord_biquad_26hz_notch_design_and_dc_hf_traps]] (the notch this extends),
[[reference_accord_dc_domain_aggregator_census_and_biquad_numerator_theorem]] (the palindromic-numerator
theorem this structural argument depends on).
