# 2020 Accord EPS — Base Assist Cluster 4 Cal Tables
## Context
- Ghidra program: `code.bin` (V850:LE:32, image_base=0x0)
- gp = 0xFEDF8000, tp = 0xBF000 → abs addr = tp + offset = 0xBF000 + offset
- READ-ONLY session (no writes). Session date: 2026-05-27.
- Abs addresses given as 0xBF000 + tp_offset. Ghidra address = abs addr (image_base=0).

---

## Part A — RAM Variables (gp-relative, abs = 0xFEDF8000 − offset)

| gp-Offset | Abs RAM Addr | Width | Direction | Functions / Addresses | Semantic |
|---|---|---|---|---|---|
| `-0x4e65` | `0xFEDF319B` | u8 / s8 | **R** FUN_00065af8 @ 0x65AF8; **R** FUN_00065eda @ 0x65F04, 0x65F82, 0x65FE8; **R+W** FUN_0006651e @ 0x665E8,0x66614,0x6669C,0x666BA,0x666E0,0x666F0,0x666FC; **R** FUN_0006964c @ 0x6968E | **Assist-mode state byte.** Values: 0=NORMAL (calls FUN_0006634e), 1=STARTING/RAMP (calls FUN_00068dfe + sets gp-0x4e6c=1; transitions→2 when speed threshold met), 2=ACTIVE, 3=TRANSITION (condition checks for mode-0→1 re-init), 4=FAULT/INHIBIT (set by multi-sensor fault path FUN_0005b2be(4/5/0x2A) returning 3). The final `st.b r28,-0x4e65,gp` write at 0x65F8E (FUN_65eda) and 0x666FC (FUN_6651e) has a lockstep redundancy check against mirror at gp-0x4458 — mismatch calls FUN_0006b9ee. |
| `-0x4fb8` | `0xFEDF0048` | s16 | **W** FUN_0006634e @ 0x663C2, 0x6649C; **R** FUN_000690f8 @ 0x690F8 | Assist demand output channel A (motor current, signed 16). Written by curve-interpolation in the initialization path. Read by FOC/current-control handler. |
| `-0x4fbc` | `0xFEDF0044` | s16 | **W** FUN_0006634e @ 0x66412, 0x664AC; **R** FUN_000690f8 @ 0x6911A | Assist demand output channel B. Parallel to -0x4fb8; separate coil/phase. |
| `-0x4fb6` | `0xFEDF004A` | s16 | **W** FUN_0006634e @ 0x664CC; **R** FUN_000690f8 @ 0x6913A | Assist demand output channel C. |
| `-0x4fba` | `0xFEDF0046` | s16 | **W** FUN_0006634e @ 0x664DE; **R** FUN_000690f8 @ 0x6912C | Assist demand output channel D. |
| `-0x34ec` | `0xFEDFCB14` | ptr (s32) | **W** FUN_00048a40 @ 0x48C90; **R+W** FUN_00049180 @ 0x4929C, 0x492CE; **R** FUN_000498de @ 0x4998A; **R** FUN_0006634e @ 0x66352; **R** FUN_0007dae4 @ 0x7DB04, 0x7DBC6 | Assist-curve **row pointer A** (pointer to lower row struct). FUN_0006634e reads both this and -0x34e8 to perform LERP between two assist-curve table rows. |
| `-0x34e8` | `0xFEDFCB18` | ptr (s32) | **W** FUN_00048a40 @ 0x48CB0; **R+W** FUN_00049180 @ 0x492D2, 0x49304; **R** FUN_000498de @ 0x49992; **R** FUN_0006634e @ 0x66356; **R** FUN_0007dae4 @ 0x7DB00 | Assist-curve **row pointer B** (pointer to upper row struct). Together with -0x34ec forms the two surrounding rows for temperature-interpolated assist demand. |
| `-0x2a40` | `0xFEDFD5C0` | s32 | **W** FUN_00065eda @ 0x661CE (=7), 0x66346 (=0); **W** FUN_0006634e @ 0x66512 (=13); **W** FUN_0006651e @ 0x666DC (=6), 0x666EC (=7), 0x6689C (=0); **R** FUN_0006651e @ 0x6670E | **Assist trigger / demand-ready flag.** Set to 1 by the active assist path to signal that current demand outputs are valid. Cleared to 0 at end of cycle. Used as a guard by FUN_0006651e to decide whether to update the motor current setpoints. |

### Assist-mode dropout path (gp-0x4e65 forced to fault/non-normal state)

`FUN_00065eda` (the outer assist-mode manager) tests two gates before entering the normal assist branch:

1. **Gate 1 — global fault bit 15:** `FUN_000197d0(0xf)` tests bit 15 of a fault-flag word at `gp-0x6d78`. If set → forced to the fault branch.
2. **Gate 2 — `FUN_0006fd42()`:** Returns 1 when a fault condition is active. If it returns 1, also forced to the fault branch.
3. **Gate 3 — `gp-0x4e6a == 1`:** An inhibit flag. Any one of these gates being true bypasses the normal path.

When in the fault/non-normal branch (gates 1/2/3 true), `FUN_00065eda` tests: if `cVar14 == 3` (current assist mode is TRANSITION) AND `gp-0x4e67 == 0`, it sets `gp-0x4e6b = 1` (the re-init flag).

**State 4 (FAULT/INHIBIT) trigger path:** `FUN_0005b2be(param)` is called with params 4, 5, and 0x2A — if any returns 3 (fault active), `cVar14` is set to 4 before the lockstep write. This is the **sensor fault path** that sets mode=4 without a latched DTC.

In `FUN_0006651e`, the assist-mode state machine:
- State 3 (TRANSITION) + flag `gp-0x4e6b == 1` → calls the convergence check (torque-sensor plausibility window via `gp-0x5000`/`gp-0x4ffe` vs. tp+0x5978/0x5970 thresholds). If the channels fail to converge within `tp+0x5x14` counts → state transitions to 1 (STARTING), re-initiating the full ramp sequence. **This is the re-engagement ratchet.** Every failed convergence check fires another state-1 ramp from scratch.

**Core dropout mechanism (confirmed by Era-15 EME constellation note):**
- Driver applies large hand torque on a sharp turn → column torque sensor dual-coil plausibility voter `FUN_00041eec` (5 ADC channels `gp-0x6a44/40/3c/38/46`) fires plausibility inhibit or the inter-channel delta exceeds the threshold → sets `gp-0x4e6b` (re-init flag) or forces state to 3 → re-init ramp cycle.
- With 2× arb gain (`tp+0x746c` 891→1782), the amplified arb output makes the delivered LKAS zero at the same instant (ENABLE byte `0xFEDF195C` written at 0x2b51e clears), and re-ramp through the shaper's deadband (tp+0x7424=29491, ~90% of range) is slow → **whole-assist dropout + ratchet**.
- **The gp-0x4e65 state byte does NOT latch a DTC.** The transition through states 3→1→2→3 is purely runtime and self-recovers when sensor channels reconverge.

---

## Part B — Flash Calibration Constants (tp+offset, abs = 0xBF000+offset)

### Core torque path

| tp-Offset | Abs Addr | Current Value (u16 LE) | Decoded | Code Load Site(s) | Semantic | Editable? |
|---|---|---|---|---|---|---|
| `0x746c` | `0xC646C` | `7b 03` | **891** | `m_steer_torque_arbitration` @ 0x2A1EE (ld.h); FUN_0002b62c @ 0x2B656; FUN_0002c478 @ 0x2C488; FUN_00036682 @ 0x36686; FUN_00036828 @ 0x3684A | **Arb output Q15 gain.** `out = (combined_torque × polarity × GAIN[891]) >> 15`. V14 raised this to 1782 (×2). Primary lever for LKAS magnitude. | YES — V14 doubled this. |
| `0x71b2` | `0xC61B2` | `00 02` | **512** | `m_steer_torque_limit_and_pack` @ 0x2B42A, 0x2B436, 0x2B43C, 0x2B446; FUN_0002b57a @ 0x2B5B6 | **Arb output clamp magnitude** (unsigned half). Used as ±512 symmetric clamp on arb output before limit_and_pack. V14 raised to 1024. | YES — V14 doubled this. |
| `0x71b4` | `0xC61B4` | `00 02` | **512** | `m_steer_torque_arbitration` @ 0x2A1F8, 0x2A20C, 0x2A212, 0x2A21C | **Arb output clamp in the arbitration function itself** (pre-pack). Paired with 0x71b2; both need raising in tandem. V14 raised to 1024. | YES — V14 doubled this. |
| `0x71d6` | `0xC61D6` | `00 00` | **0** | `s_motor_torque_rate_shaper` @ 0x43350 (ld.hu r16) | **Slew step** (incremental ramp step per cycle in the shaper). 0 = no ramp / instantaneous. Non-zero enables a ramp-up that reduces hard cutout severity on re-engage. Verified address and confirmed **0x0000** in current flash. | YES — raising to 14 (0x0E 0x00) proposed in Era 15 memory. |
| `0x71da` | `0xC61DA` | `44 04` | **1092** | `s_motor_torque_rate_shaper` @ 0x432B0; FUN_00043e44 @ 0x448F6 | **Slew scale** (divisor/multiplier in slew computation). Used alongside slew step to set the per-cycle ramp rate. | Caution — paired with slew step; adjust together. |
| `0x71dc` | `0xC61DC` | `00 78` | **30720** | `s_motor_torque_rate_shaper` @ 0x43268; FUN_00043e44 @ 0x4474A | **Accumulator clamp** in the rate shaper (±30720). Defines the maximum integrated value before hard clamp. Well above the 4762 governor; not the operative ceiling. | Low priority. |
| `0x7424` | `0xC6424` | `33 73` | **29491** | `s_motor_torque_rate_shaper` @ 0x43358 (ld.hu r18) | **Shaper deadband / dropout threshold.** ~90% of max. If accumulated shaper value falls below this on a transient zero, the output goes to zero (cold-start behavior). At 2× gain, the ratchet re-engages through this deadband from zero → slow ramp → the dropout feels like a power-steering loss. **Primary dropout severity lever.** | YES — lower to reduce dropout duration (e.g. 14746 = 50%). Safety note: too low and shaper won't zero on true disengage. |
| `0x7288` | `0xC6288` | `2c 01` | **300** | `m_steer_torque_arbitration` @ 0x29752, 0x2998E, 0x29A28 | **Re-engage init-wait** (count threshold; 300 cycles before re-engage ramp starts). | Moderate priority. |
| `0x728a` | `0xC628A` | `98 01` | **408** | `m_steer_torque_arbitration` @ 0x29866, 0x298AC | **Re-engage ramp ceiling** (408 — maximum value during ramp-up phase). | Moderate priority. |
| `0x74de` | `0xC64DE` | `11 64` | ramp_step=0x11=**17**, second byte=0x64=100 | `m_steer_torque_arbitration` @ 0x2976E, 0x2984E, 0x29862, 0x29874, 0x29896, 0x298A8, 0x298B0, 0x299AA (ld.bu — byte loads) | **Ramp step byte** (17 per cycle). Controls per-cycle increment during the arb re-engage ramp sequence. Higher = faster ramp back to full assist after dropout. | YES — can raise to reduce ratchet duration. |
| `0x7202` | `0xC6202` | `9a 12` | **4762** | FUN_0007b022 @ 0x7B06A (governor initializer) | **Governor constant** (max speed-scaled ceiling = 4762). Loaded once at init; runtime copy at gp-0x4f64 and mirror gp-0x448a. Well above the V14 ±1024 arb clamp; not binding for 2× scenario. | LOW priority at 2× — only needed for >9× push. |
| `0x7206` | `0xC6206` | `00 0c` | **3072** (= 0x0C00) | `m_motor_torque_governor` @ 0x45410 | **Governor voter step A.** One of two speed-interpolation step values used inside the governor for the adaptive binder. | Informational; not a short-term lever. |
| `0x7208` | `0xC6208` | `00 02` | **512** | `m_motor_torque_governor` @ 0x45416 | **Governor voter step B** (512). Second interpolation step. | Informational. |

### Shaper cluster

| tp-Offset | Abs Addr | Value | Code Load Site | Semantic |
|---|---|---|---|---|
| `0x71d4` | `0xC61D4` | `00 00` (=0) | `s_motor_torque_rate_shaper` @ 0x431C8; FUN_00043e44 @ 0x446C8, 0x446D6 | Shaper coefficient / init threshold (0 = no offset). |
| `0x71de` | `0xC61DE` | `00 08` (=2048) | `s_motor_torque_rate_shaper` @ 0x43360 | Shaper inner limit A. |
| `0x71e0` | `0xC61E0` | `00 1c` (=7168) | `s_motor_torque_rate_shaper` @ 0x4335C | Shaper inner limit B. |
| `0x71e2` | `0xC61E2` | `00 1c` (=7168) | `s_motor_torque_rate_shaper` @ 0x43388 | Shaper inner limit C. |
| `0x7420` | `0xC7420` | `cc b0 0e 00` — reads as u16 at 0xC7420 = 0xB0CC=45260 | `s_motor_torque_rate_shaper` @ 0x43398 | Shaper auxiliary threshold (used with deadband logic). |
| `0x7298` | `0xC7298` | bytes `74 b0 0e 00` → u16=0xB074=45172 | `s_motor_torque_rate_shaper` @ 0x43392 | Shaper LERP axis reference A. |
| `0x729a` | `0xC729A` | `76 b0 0e 00` → u16=0xB076=45174 | `s_motor_torque_rate_shaper` @ 0x43366 | Shaper LERP axis reference B. |
| `0x729c` | `0xC729C` | `76 b0 0e 00` (shared region) → u16=0xB076 | `s_motor_torque_rate_shaper` @ 0x4337E | Shaper LERP axis reference C. |
| `0x74a4` | `0xC74A4` | `ea b0 0e 00` → byte at 0xC74A4=0xEA=234 (ld.bu) | `s_motor_torque_rate_shaper` @ 0x4334C; FUN_00043e44 @ 0x44950 | Shaper mode selector byte A. |
| `0x74c9` | `0xC74C9` | bytes: `b0 0e 00 f2 b0 0e 00 f4` → byte at 0xC74C9=0xB0=176 | `s_motor_torque_rate_shaper` @ 0x4339E (ld.bu); FUN_00043e44 @ 0x44896 | Shaper mode selector byte B. |
| `0x74cd` | `0xC74CD` | byte at 0xC74CD (`f2 b0 0e 00 f4...`) = 0xF2=242 | `s_motor_torque_rate_shaper` @ 0x43372 (ld.bu) | Shaper mode selector byte C. |
| `0x74fe` | `0xC74FE` | `0e 00 00 b1` → byte at 0xC74FE=0x0E=14 | `s_motor_torque_rate_shaper` @ 0x4336C (ld.bu) | Shaper ramp parameter byte A. |
| `0x74ff` | `0xC74FF` | byte at 0xC74FF=0x00 | `s_motor_torque_rate_shaper` @ 0x43378 (ld.bu) | Shaper ramp parameter byte B. |

### LERP block 0x7a0a..0x7a44 (binary-search axis/value table)

Abs: 0xC7A0A–0xC7A46. 15 entries × 4 bytes (u16 value LE + u16 axis LE). Single code load site: `s_motor_torque_rate_shaper` @ 0x432F0 (`ld.hu 0x7a0a, tp, r8`).

Structure: `[u16 value][u16 axis_breakpoint]` — the shaper performs a binary search on the axis breakpoints to select the interpolated value (motor speed or angle LUT).

| Entry | Value (u16) | Axis breakpoint (u16) | Axis (decimal) |
|---|---|---|---|
| 0 | 13 | 0xB0F0 | 45296 |
| 1 | 13 | 0xC0C0 | 49344 |
| 2 | 13 | 0xC0D8 | 49368 |
| 3 | 13 | 0xC0F0 | 49392 |
| 4 | 13 | 0xD0C0 | 53440 |
| 5 | 13 | 0xD0D8 | 53464 |
| 6 | 13 | 0xD0F0 | 53488 |
| 7 | 13 | 0xE0C0 | 57536 |
| 8 | 13 | 0xE0D8 | 57560 |
| 9 | 13 | 0xE0F0 | 57584 |
| 10 | 13 | 0xF0C0 | 61632 |
| 11 | 13 | 0xF0D8 | 61656 |
| 12 | 13 | 0xF0F0 | 61680 |
| 13 | 13 | 0x00C0 | 192 (wraps u16; = 65536+192 in context) |
| 14 | 14 | 0x00D8 | 216 (wraps; = 65536+216 in context) |

All axis breakpoints have constant value=13 except the last two (value=14). This is a step function with a single transition at the upper end — the shaper uses it as a threshold table, not a continuous interpolation. Axis values appear to be motor electrical angle / speed codes spanning roughly 45296–61680 in the main range.

---

## Ranked Cal Levers — Preventing Transient Dropout/Ratchet While Keeping 2× LKAS

Ranked by expected impact on the dropout symptom, from highest to lowest.

| Rank | Addr | Current | Proposed Direction | Expected Effect | Safety Note |
|---|---|---|---|---|---|
| **1** | `0xC61D6` (tp+0x71d6) slew step | **0** | **Raise to ~14 (0x0E 0x00)** | Enables incremental ramp in the shaper instead of an instantaneous jump to zero. Re-engage after a transient plausibility event ramps up smoothly (14 units/cycle through the 29491 deadband) instead of the hard cutout. Directly addresses the "jerk" part of the EME symptom. | Per Era-15 memory this exact value was verified as the fix in the prior Accord analysis (the slew_limiter memory). At 0, the ramp is absent and any inhibit event causes a hard zero. Raising to 14 is low-risk: it only affects the ramp-up trajectory, not the maximum torque ceiling. Do NOT raise above ~50 — too fast a ramp is indistinguishable from a clamp bypass. |
| **2** | `0xC74DE` (tp+0x74de) ramp step byte | **17** | **Raise to ~25–30** | Faster per-cycle increment during the arb re-engage ramp sequence. Shortens the time spent at zero assist after a sensor plausibility dropout, reducing the "10-second heavy steering" window. | 8-bit byte field (max 255). Raising from 17 to ~25 = ~47% faster ramp. Do not raise above 50 — the ramp exists to validate sensor convergence before full assist resumes. Exceeding that range risks re-engaging before channels have truly re-converged. |
| **3** | `0xC6288` (tp+0x7288) re-engage init-wait | **300** | **Lower to ~150–200** | Reduces the mandatory wait before the re-engage ramp starts. Currently 300 cycles (~15ms @ 50Hz). Cutting to 150 halves the minimum dropout window. | Minimum wait exists to confirm channel stability. Do not lower below 100. Paired change with ramp step for coherent shortening. |
| **4** | `0xC628A` (tp+0x728a) ramp ceiling | **408** | **Raise to ~600–700** | Higher ceiling for the re-engage ramp allows the system to reach full-assist faster without spending cycles near zero. Most effective when combined with lever 2. | Must stay below the arb output clamp (1024 in V14) to avoid a step discontinuity at the top of the ramp. |
| **5** | `0xC6424` (tp+0x7424) shaper deadband | **29491** (~90%) | **Lower to ~20000–22000** (~65–70%) | Reduces the threshold that forces shaper output to zero during a transient. At 90%, any inter-sample dip to 90% of range triggers a full zero. At 65–70% the zero only fires on genuine large transients. Directly shortens the ratchet. | This deadband is a GENUINE FAULT DETECTOR for the shaper, not just a cosmetic clamp. Lowering too far risks missing a real motor fault. Recommended floor: 50% (= ~16384). Do NOT zero this out — it is load-bearing for no-assist-on-fault behavior. Safety: test at 70% first. |
| **6** | `0xC646C` (tp+0x746c) arb gain | **1782** (V14) | **Reduce to ~1300 (×1.46)** | Reduces the amplitude of the arb output that triggers the plausibility voltage ceiling in the torque sensor voter. Directly reduces EME frequency. Trade-off: less LKAS torque at the wheel. Consider as a fallback if levers 1–5 don't suppress the EME to an acceptable level. | This is the V14 value. Reverting all the way to 891 (stock) is the nuclear option / full revert. 1300 is a middle ground (~1.46× over stock). |

### Do NOT touch
- **Torque-sensor plausibility threshold** (`FUN_00041eec` voter, channels gp-0x6a44/40/3c/38/46, threshold ~0x7D00=32000): this is a **genuine column-torque-sensor fault detector**. Widening it risks masking a real dual-coil disagreement and is a safety regression. The Era-15 constellation note explicitly flags this as off-limits.
- **Governor `0xC6202` (4762)**: not binding at 2× (arb output ≤1024 << 4762). Only relevant for >9× scenarios.

### Summary: the dropout trigger
The `gp-0x4e65` assist-mode byte transitions to state 3 (TRANSITION) → state 1 (STARTING/RAMP) — NOT to state 4 (FAULT) — during the EME event. The trigger is NOT a latched DTC. It is the **torque-sensor dual-coil plausibility voter firing a transient inhibit** when driver hand-torque during a sharp low-speed turn pushes one or more ADC channels beyond the inter-channel delta threshold in `FUN_00041eec`. The re-initialization sequence (states 3→1→2 ramp cycle) runs through the shaper deadband (29491) from zero with slew step = 0 (instantaneous), causing the "snapping straight + heavy/jerky" symptom. At 2× arb gain, the pre-existing normally-imperceptible inhibit becomes the violent EME. The gp-0x4e65 state machine self-recovers within ~10s as channels reconverge — exactly matching the reported symptom.
