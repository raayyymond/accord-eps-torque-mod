---
name: reference-accord-four-unprobed-lanes-abcd-solved
description: Full arithmetic for the four never-probed aggregator lanes (FUN_00036388/gp-0x6b62, FUN_000352b4/gp-0x6b86, FUN_00036c12/gp-0x6b26, FUN_00036682/filtered term) -- all four are NET DAMPING or too attenuated to carry 21 Hz; the ONE real discontinuity is the aggregator's +-0x2000 zero-gate on lane A, which drops a damper and halves lane B's IIR gain simultaneously. Also CORRECTS gp-0x6c2c (not gp-0x6c2e) and the "cascade" framing in reference-accord-fun41464-sign-filter-phase-response.
metadata:
  type: reference
---

# The four un-audited aggregator lanes -- Accord TVA-A160, traced 2026-07-30

Program: `code.bin` (stock, flat base 0). gp=0xFEDF8000, tp=0xBF000. All cals byte-read LE.
Reader/writer counts from a 4-method scan (disp16 + disp23 + `search_instructions` + LE32 literal);
scanner saved at `scratchpad/scan.py`, per-opcode rules from [[v850e2-extended-disp23-encoding-solved]].

## Call graph / rate [VERIFIED]
All of A, B, C are called from `FUN_0002214a` (the confirmed 1 kHz control task), **every tick** --
gated only on `cmp r0,r28; be`, **not** a 16-phase mask (unlike `FUN_00041464`, which is 5/16 = 312.5 Hz).
Order within the tick: **B `0x227b4` -> A `0x22882` -> C `0x228cc`**. D (`FUN_00036682`) is called from
the aggregator `FUN_0003aa2c` itself.

## 🛑 NEW STRUCTURAL FACT: lanes A and B are MUTUALLY COUPLED
- B writes `gp-0x6b96` @`0x3574a`; A reads it @`0x3646a` (same tick, zero delay -- B runs first).
- A writes `gp-0x6b62` @`0x36514`; B reads it @`0x3593e` (one-tick delay).
B's read is a **switch**: `gp-0x6b62 != 0 && |gp-0x6b62| <= 0x2000` selects B's output-IIR gain
**41/2048 instead of 20/2048** (cal `0xC6382`=41 vs LERP Y=20) -- a 2x pole step.
That is the **same +-0x2000 threshold** as the aggregator's zero-gate on lane A, so one threshold
crossing fires two discontinuities at once. This coupling was not in the golden model.

## (A) FUN_00036388 -> gp-0x6b62  "return-to-centre"
`gp-0x6b62 = sgn(S)*(acc>20 ? 1024 : |S|)  +  [sgn(T)*min(clamp(gp-0x6b96-1024,0,8192),|T|) * gp-0x6990 >> 15]`
- `S = gp-0x6b64` from `FUN_000360fe`: `-(LERP(gp-0x6bda)*gp-0x6abc >>10)*1024 >>10`, clamp +-0x2800.
  **`gp-0x6abc` is a `FUN_00041464` rate-filter output** (writers `0x416fc/0x4170c/0x41968/0x4197c`),
  LERP Y plateau 2560 = Q10 2.5 -> **term1 ~= -2.5 x filtered motor rate = a VISCOUS DAMPER.**
- `T = gp-0x6b5e` from `FUN_000361c8`: trapezoid LERP on `gp-0x6bda`,
  X=[-384,-128,128,294,384] Y=[0,4762,4762,717,0], x`0xC63C2`=1024 >>10, x polarity, negated if `gp-0x6bf0>=1`.
- **`acc` = gp-0x6a82, a +-1/tick counter in [0,21]**, increments while `|S| > 1024` (`0xC618A`),
  threshold `0xC627E`=20. This is the "slow +-1/tick accumulator with hysteresis" from STATE.md --
  it is a **21-tick debounce on a damper saturation**, not a backlash.
- **`gp-0x6990` = a +-33/tick ramp clamped [0,32768]** (`0xC63C0`=33), NOT +-1/tick. 993 ticks full-scale.
  Its DECREMENT branch needs `gp-0x6ac0 < 200` (`0xC620C`) -- i.e. motor essentially stopped -- so during
  any real oscillation it pins at 32768.
- **`0xC64A1`=1 makes the simple `S+T` branch at `0x3651e` DEAD CODE.**
- Sign verdict: both relay branches (`-2.5*rate` and `-1024*sgn(rate)`) share the same sign ->
  a time-varying but **always-positive damper. Cannot inject net energy over a cycle.** [NET DAMPING]

## (B) FUN_000352b4 -> gp-0x6b86 + gp-0x69a4  "friction magnitude"
- **`gp-0x69a4`'s producer is RESOLVED: `0x355c6`, inside this function** -- it is the local SLOPE of the
  10-segment curve, zeroed outside the +-25600 Sensor-B window. Its 3 readers: `0x355a4`, `0x3575a`,
  `0x3ab3a` (the r26 lane in the aggregator).
- Output stage is a **magnitude PEAK-HOLD** @`0x35884` (see [[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stagea-pole]]),
  then an IIR whose gain switches 20<->41/2048 on lane A (above). 21 Hz: -22.6 dB / -16.4 dB.
- **Float biquad is DEAD**: gate `0xC649B` = 0x00 (1 reader, `0x359fe`). Coefficients `0xC60A8..0xC60B4`
  = -1.5372 / 0.63462 / -1.8808 / 0.81731. **This is the only float twin among the four lanes and it is
  gated off** -- do not touch `0xC649B`; enabling it is a V27-class int/float desync risk.

## (C) FUN_00036c12 -> gp-0x6b26  "friction comp"
🛑 **The multiplier is `gp-0x6c2c`, NOT `gp-0x6c2e`** [VERIFIED @`0x36c1a`, bytes `24 4f d4 93`, hw2=0x93D4].
- `gp-0x6b26 = clamp( ((gate(gp-0x6c2c) * Y_speed) >> 6) * 273 >> 18, +-511 )`; limit cal `0xC407E`=511
  (3 readers, all in this function). Gate is the +-32000 plausibility window @`0x36c22-0x36c2c`.
- **LERP `0xCBE74` -> INDEX 10 -> `0x0D2A44`. 3-point, axis = `gp-0x6a5e` VOTED VEHICLE SPEED.
  X = [0, 20, 90] km/h ; Y = [-9830, -5734, -1966] -- ALL NEGATIVE, and ALL 16 variant rows identical.**
  Net coefficient -0.148 at 1 m/s vs -0.054 at 18 m/s = **2.74x stronger at creep**.
- **`gp-0x6c2c` = filtered motor rate**, live writer `0x4184e` (`sar 0x9` of `gp-0x35a0`), fault writer
  `0x41ac2` pins 0x7FFF -- which **exceeds the +-32000 gate, so a rate fault zeroes this lane.**
- Verdict: `-K(speed) x rate` added to the command = **VISCOUS DAMPING**, 21 Hz phase -45.9 deg total
  (EMA -33.8 + ZOH -12.1), cos = +0.696. [NET DAMPING, sign convention INFERRED -- see below]

## (D) FUN_00036682 -> the 11th summand  "filtered Sensor-B"
`x[n] = gp-0x6b48 + sgn*(SensorB*891 >> 15)` (`0xC646C`=891, **6 readers** incl. the once-missed `0x2a904`)
`e[n] = x[n] - y[n-1]` @`0x366a4`; backlash; clamp +-512 @`0x367de`; `acc += ((u<<10 - acc)*6)>>10` (`0xC63D2`=6, **1 reader**).
- The brief's "y[n-1] subtracted twice" is **CORRECT but benign**: linear closure is
  `y[n] = y[n-1](1-2a) + a*x[n]` -> **single real positive pole 0.98828, DC gain exactly 0.5**, corner 1.87 Hz.
  It is **NOT** two-pole/oscillatory -- `(1-2a)` only goes negative for `a >= 0.5` and `a = 0.00586`.
- **The backlash at `0x367a4-0x367d8` is LIVE but the peak/level block `0x366be-0x36732` is DEAD**:
  the entry gate needs `|y[n-1]| > 1024` and `y` is structurally bounded to +-512, so the reset path
  (`0x36734`: level=0x8000, counter=1) is taken **every tick**. Backlash width = `gp-0x6b44` unity-scaled
  (1 reader `0x36760`, 1 writer `0x36bb0` in `FUN_00036828`; cals `0xC619E`=307 / `0xC61A0`=123 / `0xC619A`=102).
- **Limit-cycle test: loop gain <= 0.0445 = -27.0 dB at 21 Hz** (backlash `|N| <= 1`). 27 dB short of
  oscillation. Output bounded +-512. **RULED OUT.**

## 🛑 CORRECTION to [[reference-accord-fun41464-sign-filter-phase-response]] (do NOT delete that file)
That memory says `gp-0x6c2c`/`gp-0x6c2e` come from a "second-stage filter cascade". **They are two
PARALLEL first-order EMAs sharing one input**, not a cascade [VERIFIED `0x41622-0x4164c`: `r22` is
copied to `r26` at `0x4162e` and is NOT modified before its own use at `0x4163c`]:
- `gp-0x35a0`: `acc += ((x-acc)*22)>>6`  -> **alpha = 22/64 = 0.34375** (`0xC40DC`=22) -> `gp-0x6c2c` (>>9)
- `gp-0x35a4`: `acc += ((x-acc)*3)>>7`   -> **alpha = 3/128 = 0.02344** (`0xC40DA`=3)  -> `gp-0x6c2e` (>>9)
Input `x` = raw resolver rate `gp-0x4f50` << 5, floor-clamped @`0x41612-0x4161a`.

## Open / unresolved
- **The absolute sign convention of `gp-0x4f50`-derived rate vs `gp-0x6b98`** is INFERRED, not proven.
  Supporting evidence: lanes A/C do not apply the `gp-0x6752` polarity byte that the sensor-domain lanes
  (B, D) do, and `FUN_00041464` loads `gp-0x6b98` at `0x41846` in the same block. **To settle it:
  decompile `FUN_00041464` around `0x41cd6` (`gp-0x6abe` read) and find the explicit
  `sign(rate) vs sign(gp-0x6b98)` comparison.** All three damping verdicts above flip if this is wrong.
- `gp-0x6bda` (the shared LERP axis for both S and T in lane A) -- sole writer `0x3608c` in
  `FUN_00036022`; physical identity not resolved this session.

## Related
[[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stagea-pole]] -- lane B's peak-hold, still valid.
[[reference-accord-gp6b98-aggregator-definitive-lane-table-v57]] -- the 11-lane table these four sit in.
[[reference-accord-aggregator-domain-audit-no-angle-lane-found]] -- consistent: lanes A and C are
rate-domain, not angle-domain, which is why the domain audit found no angle lane.
