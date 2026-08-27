---
name: reference_accord_gp4f50_4khz_to_1khz_decimation_and_polepair_derivation
description: gp-0x4f50 (the raw input to the gp-0x6c2c/gp-0x6b26 accel cascade) is written by copying a 4kHz-domain value (gp-0x29c4, itself only a weak 2-tap boxcar average of the raw resolver-rate estimate) into the 1kHz domain with NO further anti-alias filtering -- a structural decimation-without-antialiasing that could fold real 500-2000Hz motor/electrical content down into the 0-500Hz band the 1kHz cascade sees, including ~100Hz. Also derives pole_pairs*reduction_ratio ~= 56.5 from two independently-confirmed scale constants (4.7121 ct/column-deg/s and gp-0x6ac0~=30*f_electrical), giving f_electrical(Hz) ~= 0.157*column_rate(deg/s) -- a 6th-electrical-harmonic torque-ripple order at 100Hz needs only ~106 deg/s column rate, well within LKAS correction range and easily enough to rail gp-0x6b26 per the sibling memory. Confirms FOC/current-loop core (FUN_00071272) has exactly one caller, the 4kHz ADC-complete ISR (FUN_0006404c) -- no faster loop found.
metadata:
  type: reference
---

# `gp-0x4f50` producer chain (4kHz->1kHz decimation) + electrical-order arithmetic, for the V107 HF-grinding trace

2026-08-26, `hfmech` task. Fresh decompiles this session (not relayed from a prior session).

## The producer chain, freshly decompiled end to end [EVIDENCE]
```
FUN_00068f52 (writer of gp-0x29c4/gp-0x4f4e; caller FUN_00065afe -- rate not independently re-confirmed
              this session, inherited "4kHz, resolver ISR" attribution from
              [[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]]):
    iVar2 = wrapped resolver-angle delta (mod 0x4000 = 16384 counts/electrical-rev)
    iVar3 = iVar2 * 120000 >> 14                      # raw electrical-rate estimate, this sample
    gp-0x29c4 = clamp((gp-0x4f4e_prev + iVar3)/2, +-13000)   # <- ONLY a 2-TAP BOXCAR AVERAGE
    gp-0x4f4e = iVar3                                  # unaveraged raw, kept for next tap

FUN_00068fbe (writer of gp-0x4f50, address 0x68fde matches the "sole writer" cited in
              [[reference_accord_gp6c2c_transfer_function_triple_verified]]):
    __disable_irq(); sVar2 = gp-0x29c4; __enable_irq()      # critical-section READ -- strongly implies
                                                              # this runs in a DIFFERENT/SLOWER context
                                                              # than whatever writes gp-0x29c4
    if (gp-0x4f50 == gp-0x4484): gp-0x4f50 = sVar2; gp-0x4484 = sVar2      # shadow-lockstep write,
    else: FUN_0006b9ee(&gp-0x4484)                                          # NO FURTHER FILTERING
    [+ a plausibility gate vs cal(tp+0x591a)/cal(tp+0x591c), FUN_0006d026 diagnostic,
       + a separate byte-counter/threshold escalation to FUN_0006ba04 -- not traced further]
```
**`gp-0x4f50 = gp-0x29c4` directly, point-sampled.** No EMA/boxcar/decimation filter runs between the
4kHz-domain value and the 1kHz-domain copy — the ONLY smoothing anywhere in this path is
`FUN_00068f52`'s own 2-tap boxcar (`|H|=|cos(πf/4000)|`, only ~8% attenuation at 500Hz, i.e.
essentially none — this is a very weak anti-alias filter for a 4kHz→1kHz decimation).

## 🛑 Structural aliasing vulnerability [EVIDENCE for the structure; BELIEF for whether it matters in
practice -- no spectral measurement of gp-0x29c4/gp-0x4f4e exists in this kit]
If the true 4kHz-domain electrical-rate signal carries energy anywhere in (500Hz, 3500Hz) — plausible
for a raw resolver/PWM-adjacent electrical estimate — decimating it to 1kHz with only ~8% attenuation
at the fold boundary will alias that energy into [0,500Hz]. Content at 900Hz, 1100Hz, 1900Hz, 2100Hz,
2900Hz, 3100Hz, or 3900Hz ALL alias to exactly 100Hz once inside the 1kHz-sampled `gp-0x4f50` that
`FUN_00041464`'s `gp-0x6c2c`/`gp-0x6b26` cascade consumes. This is a THIRD candidate source for the
operator's ~100Hz symptom, additional to (a) a genuine fixed mechanical resonance and (b) a genuine
speed-proportional electrical order (below) — not mutually exclusive with either.

## Pole-pairs x reduction-ratio derivation [EVIDENCE, arithmetic combining two independently-confirmed facts]
[[reference-accord-rate-limits-c6194-partition-and-c520c-ceiling-scale]]: `gp-0x4f50`/`gp-0x6abe`/
`gp-0x6ac0` = **4.7121 counts per COLUMN deg/s**.
[[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]]: `gp-0x6ac0`(settled) ≈ **30 ×
f_electrical(Hz)**, derived from the confirmed 4kHz ISR rate and the 16384-count/electrical-rev modulus.
Both describe the SAME cell ⇒ `4.7121 * columnRate[deg/s] = 30 * f_e[Hz]`
⇒ **f_e[Hz] = 0.15707 * columnRate[deg/s]**, equivalently **pole_pairs × reduction_ratio ≈ 56.5**
(since f_e = pole_pairs·N·columnRate/360). Neither factor is individually recoverable from firmware
alone (BELIEF: plausible splits are pole_pairs=3,N≈18.8 or pole_pairs=4,N≈14.1 — both in the range of
typical column-EPS worm-gear ratios; not decided).

Electrical-order candidates for a 100Hz observation:
```
order 1 (fundamental):  columnRate = 100/0.15707 = 636.7 deg/s   -- ~1.8 rev/s, plausible only as a brief flick
order 6 (common BLDC/PMSM ripple order): columnRate = 106.1 deg/s -- plausible SUSTAINED LKAS-correction rate
order 3:                 columnRate = 212.2 deg/s
```
Order-6 at ~106°/s is well inside what the sibling memory
([[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]]) shows is more than sufficient to
saturate gp-0x6b26 at 100Hz (clamp-crossing needs only ~26°/s on V107 @24km/h) — i.e. this candidate
easily clears the railing threshold, it is not a fine-tuned coincidence.

## No loop faster than 4kHz found [EVIDENCE]
Fresh `get_function_callers(0x71272)` (the FOC/current-loop core): **exactly one caller,
`FUN_0006404c`** (the ADC-complete ISR, confirmed elsewhere to fire once per 4kHz carrier period —
[[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]]: TS0CTL4 peak-reload-only, i.e. ONE
duty/sample update per full carrier period, not two). `gp-0x6b98`'s own direct xref lookup returned a
Ghidra-blind null (matches the known `search_instructions`/xref trap already on record for this exact
cell — not treated as evidence of zero writers). Everything from `gp-0x6b94` (aggregator) through
`gp-0x6b98` (FOC setpoint) is the existing 1kHz outer loop
([[accord-aggregator-reaches-motor-via-gp6acc-bridge]], project memory); `gp-0x6b98` is the handoff
point into the 4kHz FOC/current inner loop, which does not itself add new frequency content — it tracks
whatever the 1kHz outer loop already computed. ⇒ any real 100-300Hz content in the delivered command
must originate at or before the 1kHz stage (consistent with the decimation finding above, and with
gp-0x6b26 itself being fully capable of 0-500Hz content since it runs at 1kHz).

## Related
[[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]] (companion finding, same session),
[[reference_accord_pwm_carrier_4khz_and_adc_trigger_corrected]], [[reference-accord-c520c-cap-table-axis-provenance]],
[[reference_accord_gp6c2c_transfer_function_triple_verified]] (source of the "sole writer 0x68FDE" citation
this traces to its containing function, FUN_00068fbe).
