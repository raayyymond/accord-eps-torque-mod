---
name: reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm
description: Full pole/frequency-response characterization of the calibration-dead 2nd-order recursive filter in FUN_000352b4 (previously found structurally by reference-accord-fun352b4-untested-carrier-and-dead-biquad.md but not pole-located). Confirmed genuinely VIRGIN (grep of all build_v*_tva.py, zero hits on 0xC649B/0xC64FA/0xC60A8/AC/B0/B4). Its arm condition reuses the SAME oscillation-reversal-counter threshold (gp-0x671a>=5, cal 0xC64FA=5) already established elsewhere to fire specifically during 18-21Hz oscillation episodes -- suggesting Honda's original intent was an adaptive anti-oscillation stage, shipped disabled.
metadata:
  type: reference
---

Found 2026-08-19, damping/stability-lever hunt for the V101 self-oscillation report (8x LKAS gain,
Lever B reverted). Program: stock `code.bin`, cross-checked against both stock and the built V101
image (`_v101_V99BASE-GAIN8X.C6CD0.7128-NOLEVERB-CAVE.LKASSAT.SIGNS-427.6B94_plain_image.bin`) via
direct Python LE byte reads.

## Gate [EVIDENCE, fresh `decompile_function(0x352b4)` this session]

```c
cVar4 = *(char *)(tp+0x749b);      // 0xC649B, byte
bVar12 = *(byte *)(tp+0x74fa);     // 0xC64FA, byte = 5 (stock AND V101, unchanged)
if ((cVar4 == 1) && (bVar12 <= gp-0x671a)) { /* biquad runs */ }
```
`gp-0x671a` is the kit's already-established oscillation-REVERSAL counter
([[reference_accord_state671a_is_oscillation_reversal_counter]]: rises on reversals of `gp-0x6c2c`,
saturates >=5 in ~125-150ms of 18-21Hz oscillation). **The arm threshold (5) is exactly the
saturation value already tied to that oscillation signature** -- this gate is not a random constant,
it is sized to the same phenomenon the kit uses elsewhere to detect ringing.

Byte-read `0xC649B = 0x00` on BOTH stock and the V101 image -- **the gate has NEVER been non-zero**.
Grepped all `analysis-2020accord/build_v*_tva.py`: **zero hits** on `0xC649B`, `0xC60A8`, `0xC60AC`,
`0xC60B0`, `0xC60B4`, and `0xC64FA` -- this cell and its coefficients have never been touched by any
build in the kit's history. Genuinely virgin.

## Recursion, hand-expanded from the decompile [EVIDENCE]

States `x1=gp-0x3814`, `x2=gp-0x3818`; input `u = iVar34_prev / 1024` (iVar34 is the pre-biquad
value of a mid-pipeline term also stored to `gp-0x6b82` when the gate is closed). Coefficients
`c1..c4` = floats at `tp+0x70a8/ac/b0/b4` = `0xC60A8/AC/B0/B4` = **-1.5372, 0.63462, -1.8808,
0.81731** (byte-identical stock vs V101).

```
x1' = x2
x2' = -c1*x2 - c2*x1 + c4*u
y   = x1 + c3*x2 + x2'              // clamped +/-12.0, then *1024 -> replaces iVar34
```
(Careful double-negation expansion required -- an unchecked first pass mis-signed the state matrix;
redone and confirmed with `numpy` state-space eigen/transfer-function evaluation, not by hand.)

## Poles and frequency response [EVIDENCE, computed with numpy/cmath, not estimated]

State matrix `M=[[0,1],[-c2,-c1]]` -> complex pole pair `0.7686 +/- j0.2095`, `|z|=0.7966`,
`angle=15.24 deg`. **`ζ≈0.65` (`Q≈0.77`) -- comfortably damped, no resonant peak** (confirmed by
direct `|H(e^jω)|` sweep, monotonic roll-off, no bump anywhere).

Caller (`get_function_callers(0x352b4)`) = **`FUN_0002214a` only, the confirmed 1 kHz task** ⇒ pole
sits at **≈42.3 Hz**. Full response at fs=1000Hz:
```
 7.79 Hz: -0.15 dB / -10.6°     21 Hz: -1.25 dB / -30.0°     30 Hz: -3.0 dB / -45.0°
40 Hz:    -6.9 dB / -63.1°      42.35 Hz (pole): -8.3 dB / -67.5°
```
Phase stays well under 90° through 40Hz (safe from sign-flip/anti-damping), but attenuation at the
LOW end of the operator's 5-40Hz band (7-9Hz) is negligible (-0.15dB) -- **this stage, if armed,
reads as a mild high-shelf roll-off with a knee around 25-40Hz, not a targeted low-frequency notch.**
Its practical value against a 6-9Hz or 18-22Hz ratchet is likely small; it would attenuate content
closer to 30-42Hz meaningfully.

## Destination [from reference-accord-fun352b4-untested-carrier-and-dead-biquad.md, corroborated]

The filtered value re-enters the pipeline feeding `gp-0x6b86`, the **widest** of all 11
`FUN_0003aa2c` aggregator summands (±12288, wider than even the LKAS command's own ±10240 gate).
No speed gate was found on this path in this session's decompile (the only late-stage gate is a
sanity check on raw torque `gp-0x4f60` exceeding an extreme ~25600-count bound) -- **reachable at
any speed**, unlike the FactorC/E damper (`FUN_00034350`, dead below 35 km/h).

## What is NOT resolved

- The exact physical meaning of `iVar34`/`u` (the pre-biquad value it would replace) was not fully
  traced this session -- it descends from a friction-hold combinator earlier in the same function,
  itself downstream of `gp-0x4f60` (raw torque) and mode-indexed LERPs. Needed before sizing any
  build around this lever.
- Whether the coefficients were authored for THIS call site (1kHz) or copy-pasted from a
  higher-rate context (e.g. the 4kHz FOC region) and simply never wired up here -- the ~42Hz corner
  is a plausible-but-unconfirmed "adaptive de-ring stage" fit, not a proven one.

## Related
[[reference-accord-fun352b4-untested-carrier-and-dead-biquad]] -- original structural find (no pole
location). [[reference_accord_state671a_is_oscillation_reversal_counter]] -- the reversal-counter arm
condition this file's gate reuses. [[reference-accord-notch-biquad-search-negative-result]] -- the
prior "no biquad" sweep this corrects (a dead one exists; the "no LIVE biquad" conclusion still
stands, and the search remains non-exhaustive: only 6 of 128 candidate 2-state functions
characterized per [[reference_accord_fun41d56_state_space_complex_poles]]).
[[reference_accord_gp6b26_closed_both_directions_v94_aborted]] -- CAUTION, read before proposing this
biquad in a build: a sibling "looks safe/reactive in isolation" term (gp-0x6b26) turned out to carry
a real, measured closed-loop damping contribution the operator's own aborted drive exposed. This
biquad's isolated DC-gain/phase safety (above) has NOT been checked against the full aggregator loop
the way gp-0x6b26 eventually was.
