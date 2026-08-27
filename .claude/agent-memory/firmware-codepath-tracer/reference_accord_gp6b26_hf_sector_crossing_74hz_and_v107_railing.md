---
name: reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing
description: gp-0x6b26's torque-phasor-vs-motor-rate crosses from the 180-270deg (damping+added-inertia) sector into 90-180deg (the sector that CAN raise a resonance) at f=74.5Hz and stays there continuously to Nyquist (500Hz) -- the prior "falsified for both signs" verdict was correct only for the <=40Hz range it checked. Also: on V107, a sub-perceptible ~0.04deg (2.5 arcmin) peak column-angle wobble at 100Hz is enough to fully saturate the +-511 clamp at 24km/h -- railing needs 6-9x LESS displacement amplitude at 100Hz than at the original 21.7Hz grind target.
metadata:
  type: reference
---

# `gp-0x6b26` above 50Hz — a sector crossing at 74.5Hz, and how easily V106/V107 rail it there

2026-08-26, `hfmech` task (team-lead: explain a NEW higher-pitched ~100Hz grinding on V107, 15-40mph,
absent <=8-10km/h, returns in hard turns at 50mph). Extends
[[reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape]] (the "falsified for both signs" memory)
to the frequency range that memory never checked (it stopped at 40Hz).

## Fresh verification this session [EVIDENCE]
Byte-read `_v107_...plain_image.bin` directly (not from record): cascade constants `0xC643C`=37,
`0xC40DC`=22, `0xC40DA`=3, `0xC407E`=511 all byte-identical stock/V106/V107. `gp-0x6b26` Y-table
(modes 26/27, `0xD7A5C`/`0xD7A6C`) = `(-29490,-24000,-16000)` on V107, matching RESHAPE B exactly.
Fresh `decompile_function(0x36c12)` (not relying on a prior session's decompile) confirms the exact
arithmetic byte-for-byte: `iVar4=((g*Y)>>6)*0x111; iVar5=iVar4>>18` = `g*Y*273/2^24`, clamped to
±cal(`0xC407E`), shadow-paired to `gp-0x4cd0`. `H(f) = 64·H1(f)·(1−z⁻¹)·H2(f)`, H1/H2 one-pole EMAs
a1=37/128, a2=22/64, fs=1000Hz (task 1, confirmed). Full script:
`C:/Users/dudei/AppData/Local/Temp/claude/.../scratchpad/gp6b26_hf_transfer.py` (scratch, not in repo).

## 🛑🛑 THE SECTOR CROSSING — new, not in any prior memory (all prior phase work stopped at 40Hz)
"Torque phasor vs motor rate" = `phase(H_accel(f)) + 180°` (the −k sign), verified to match
[[reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape]]'s own anchors exactly (233.64°@21.73Hz,
209.09°@40Hz — reproduced to 2 decimal places). Swept 40-500Hz at 0.5Hz resolution:
```
f=40.00Hz   phasor=209.09deg   [180-270, damping+added-inertia]  <- where all prior work stopped
f=74.50Hz   phasor=179.77deg   CROSSES INTO [90-180, RESONANCE-RAISING]
... stays in 90-180 continuously ...
f=500.00Hz  phasor=180.00deg   (exactly the boundary; Nyquist forces a real-valued H)
```
**Only one crossing found in the entire 40-500Hz sweep.** ⇒ the ENTIRE 75-500Hz band — which squarely
contains the operator's suspected ~100Hz grinding — sits in the ONE sector
[[reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape]] proved gp-0x6b26 could never reach at
its own checked frequencies (≤40Hz). **That memory's "falsified for both signs" verdict is CORRECT for
its own scope (≤40Hz, where V106/V107's actual measured targets — grind #1 21-28Hz, grind #2 ~42-45Hz —
live) and DOES NOT extend to this new band.** `|H_accel(f)|` stays substantial throughout (10.86× at
100Hz — actually 40% MORE gain than at 21.7Hz's 7.72× — declining to 5.45× at 300Hz, never below 4.49×
anywhere to 500Hz; global peak ≈12.13× near 60-70Hz).

## Railing/clamp-crossing amplitude at V106 vs V107 [EVIDENCE, arithmetic from the confirmed H(f)]
For a pure-tone column-angle oscillation θ(t)=A·sin(2πft): peak(gp-0x4f50) = 4.7121·A·2πf counts, so
clamp-crossing amplitude `A_clamp(f,v) = 511 / (|H_total(f,v)| · 4.7121 · 2π · f)`.
```
              V106 @24km/h            V107 @24km/h
f(Hz)  peak-rate(deg/s)  A(deg,arcmin)  peak-rate(deg/s)  A(deg,arcmin)
7.79    130.7   160.2'    91.9   112.7'
21.73    52.1    22.9'    36.7    16.1'
100      37.1     3.5'    26.1     2.5'
300      73.9     2.4'    52.0     1.7'
```
**At 100Hz, V107 saturates gp-0x6b26 with a peak column-angle wobble of only ~0.04° (2.5 arcminutes)
and a peak rate of just 26°/s — 6-9× LESS displacement amplitude than railing needs at the original
21.7Hz grind target, and far below anything a driver could feel through the wheel or that any CAN
channel (Nyquist ~50Hz) could see.** V107 needs ~30% less input than V106 to rail at the same
freq/speed, because RESHAPE B raised authority specifically in the 20-90km/h band V106 had tapered.
**Answers the brief's own question directly: yes, a sub-perceptible 100Hz vibration is structurally
enough to rail this term into a relay** — the V80 precedent (`accord-v80-damper-relay-and-grind1-inert`,
project memory) for "clamped/saturating term → relay → grinding" applies with a very low excitation bar.

## Synthesis [BELIEF — code-grounded interpretation, no on-car confirmation this session]
Once railed, gp-0x6b26 stops being a linear filter and becomes a ±511 bang-bang relay at whatever
excites it — rich in harmonics, consistent with the operator's own uncertain "several hundred Hz,
possibly ~100Hz" (a relay's output is not a clean single tone). Independently, the 90-180° sector
finding above means even the UNCLAMPED (linear) part of this term is now structurally capable of
raising/sharpening a resonance in the 75-500Hz range, not merely damping one — two reinforcing routes
to the same outcome. Neither route was evaluated by V106/V107's own design process, which only ever
priced the 18-30Hz band. Not independently confirmed against real ~100Hz-domain telemetry (no wire
channel can see it; would need the `rawAudioData` 16kHz-PCM channel another session in this session was
extracting from two new V107 drives).

## Related
[[reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape]] (the ≤40Hz analysis this extends),
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]],
[[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]] (the <16km/h, <50Hz clamp-duty
telemetry this is structurally blind above; that finding is UNCHANGED, this is a different frequency
regime it never covered), `accord-v80-damper-relay-and-grind1-inert` (project memory, the relay precedent).
