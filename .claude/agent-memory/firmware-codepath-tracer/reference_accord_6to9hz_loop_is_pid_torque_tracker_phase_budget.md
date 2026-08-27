---
name: reference-accord-6to9hz-loop-is-pid-torque-tracker-phase-budget
description: "The 6-9 Hz loop is the PID driver-torque tracking servo (FUN_0003a382), not the base-assist loop. Full phase budget read from code.bin: the firmware contributes only -3 to +10 deg at 6-9 Hz, so 7.8 Hz CANNOT be a firmware phase-crossover pole. Corrects STATE.md A6b: the PID LEADS +8.2 deg at 7.79 Hz, it does not lag -11..-27 deg. Includes the task-1 execution ordering (Path 2 reads the previous tick) and the PID authority clamp that makes the lane a relay."
metadata:
  type: reference
---

# The 6–9 Hz loop, from `code.bin` (2026-08-12, agent `fw-loop`)

Model that reproduces all of this: `analysis-2020accord/sessions/v97/loop_phase_model.py`.
Write-up: `analysis-2020accord/sessions/v97/fw_loop.md`.

## 1. THE LOOP IS A TORQUE-TRACKING SERVO [EVIDENCE]

```
gp-0x4f60 → PID error → FUN_0003a382 → gp-0x6ad4 → aggregator FUN_0003aa2c
          → gp-0x6b94 → governor → shaper → gp-0x6b98 → FOC → motor → bar → gp-0x4f60
```
with the **reference** built by Path 2:
`FUN_00036682 → gp-0x6b46 → FUN_00038148 → gp-0x6b70 → FUN_00037fe6 → gp-0x6ad6`,
and `e = clamp(gp-0x4f60 − clamp(gp-0x6ad6, ±8192), ±10240)` — the reference is **subtracted**.

`gp-0x6ad6 = clamp(−gp-0x6b4a + Σ flagged lanes + gp-0x6b70, ±25600)`, `st.h @0x38142`.
🛑 `0xC64AD..0xC64B3` are **BYTE ENABLE FLAGS, all = 1** — `gp-0x6b70`'s is `0xC64B0`. They are
NOT `0xC74Bx` "weights" (the recurring tp off-by-0x1000).
**`gp-0x6b4a` is the direct LKAS term and is zero disengaged ⇒ "engaged-only" falls out of the
arithmetic; no separate gate is needed.**

## 2. ⭐ TASK-1 EXECUTION ORDER — Path 2 is ONE TICK STALE [EVIDENCE]

`search_instructions mnemonic=jarl function=FUN_0002214a`, all at 1 kHz:
`0x22676` FUN_00038148 · `0x22696` FUN_00037fe6 · `0x226a0` FUN_0003a382 ·
`0x228cc` FUN_00036c12 (→gp-0x6b26) · `0x2291e` FUN_0003aa2c (calls FUN_00036682→gp-0x6b46) ·
`0x2293a` governor · `0x229ce` shaper.
⇒ **Path 1 reads same-tick `gp-0x6b26`/`gp-0x6b46`; Path 2 reads the PREVIOUS tick.**
−2.80° extra at 7.79 Hz on Path 2 only. Not previously recorded.

⊕ FUN_00038148's sole caller is FUN_0002214a (1 kHz, two independent methods). Independently
corroborated: `0xC63AC` = 102 gives |H| 0.94/0.91/0.88 and −18.7/−23.6/−26.8° **only at
fs = 1000**, matching both STATE.md §A6b and `builds/v80_v107/build_v96_tva.py:42`.

## 3. 🛑 CORRECTS STATE.md §A6b — THE PID **LEADS** IN BAND [EVIDENCE]

Stock cals, LE-read: `0xC6B26` Kp = **256**, `0xC6B12` Ki = **98** (flat), `0xC6AE6` Kd = **2048**
(flat). **`0xC6450` (P pole) and `0xC644A` (D pole) are BOTH 1024 = PASS-THROUGH: P and D are
UNFILTERED on stock.**

🛑 **The 32× asymmetry, confirmed at instruction level:** exactly three `shl 0x5` in
`FUN_0003a382` — `0x3a7ae` (anti-windup bound), `0x3a7f6` (P), `0x3a868` (D). **The I accumulator
`gp-0x3688` has none.** Final `sar 0x5 @0x3a880`.
⇒ Kp′ = 0.250, Ki′ = 0.00299072/tick, Kd′ = 2.000 tick ⇒ `fi` = **1.904 Hz**, `fd` = **19.894 Hz**
⇒ 6–9 Hz sits **inside the flat window**.

| f | \|K\| | arg K |
|---|---|---|
| 6.00 | 0.2529 | **−0.89°** |
| 7.79 | 0.2565 | **+8.24°** |
| 9.00 | 0.2617 | **+13.29°** |

**STATE.md §A6b's "the PID's own −11° to −27° at that band" is WRONG in sign.** Its Path-2 total
(≈ −30° to −54°) is therefore understated in lag by ~10–35°.

## 4. THE PHASE BUDGET — and why 7.8 Hz cannot be a firmware pole [EVIDENCE]

Fast loop (sensor → PID → aggregator → governor → shaper → ZOH/FOC), total:
**0.253 ∠−3.05° · 0.257 ∠+5.43° · 0.262 ∠+10.05°** at 6 / 7.79 / 9 Hz.
Governor (`0xC6206` = 512 ct/tick = 512,000 ct/s) cannot bind below ≈10,400 ct of 7.8 Hz
amplitude ⇒ pass-through, 0°. Shaper `0xC64C8` = 0 ⇒ pass-through.

Path 2: `0xC63D2` = **6** (fc **0.93 Hz**) → 0.119 ∠−81.8°; +1 tick; `0xC63AC` = 102 →
0.906 ∠−23.6°. **Total 0.108 ∠−108.2°** for the torque-derived lane; **0.906 ∠−26.4°** for
`gp-0x6b26` into Path 2.

⇒ **There is nowhere near 180° of firmware phase at 6–9 Hz. The FREQUENCY is a plant resonance;
the DAMPING is firmware.** Prediction: `0xC6AE6` 2048→4096 adds +19.5°; loop-phase slope is
+4.73 °/Hz, so a true loop pole would move ≈+4 Hz. **<0.3 Hz movement ⇒ plant mode.**

## 5. ⭐ THE PID LANE IS A RELAY IN THE SYMPTOM REGIME [BELIEF — clamps are EVIDENCE]

`AUTH = min( LERP_{gp-0x6bda}(0xC67A2 X=[384,1280,12800] Y=[0,5120,5120]),
             LERP_{gp-0x6a5e}(0xC67C2 X=[128,1280,3200] Y=[0,1024,1024]) or 0xC61FE=307,
             5120 ) × (gp-0x6765==3) × LERP(gp-0x6966)/32768`
`gp-0x6a5e` = 64 ct/km/h ⇒ AUTH = **227 ct at 6 km/h**, 1024 at ≥20 km/h. With |K| = 0.2565 the
lane saturates at |e| = 885 ct at 6 km/h, against a **measured median override torque of 2235**.
Anti-windup pins P+I at the rail ⇒ **D sets the switching instants.**
Fits: engaged-only · not command-magnitude dependent · not the ±4096 rail · survives a command
reversal · `gp-0x6b70` coherence 0.966. **Settle it by telemetering `gp-0x6ad4`.**

## 6. LINEAGE — SIX VIRGIN CELLS [EVIDENCE, grepped `build_v*_tva.py`]

`0xC6AE6`/`0xC6B12`/`0xC6B26` appear **only in v43/v49 as invariant assertions**; `0xC63AC` only
in v79–v96 as an invariant; `0xC63D2` only in v52c–v64 as an invariant; `0xC67C8` in **zero**
scripts. **None has ever been written. Never-tried, not FALSIFIED.**

Δφ at 7.79 Hz: `0xC63AC` 102→512 **+20.8°** (gain 1.10×, Path 2 only) · `0xC6AE6` 2048→4096
**+19.5°** (but **2.2× gain at 21 Hz — GATE-2 risk**) · `0xC6B12` 98→0 **+13.0°** ·
`0xC6B26` 256→128 +7.7° (gain 0.52×) · `0xC63D2` 6→102 +58° but **7.6× gain — unusable**.

## 7. HYPOTHESIS RAISED AND KILLED IN THE SAME SESSION

"`gp-0x6b26` clamps at `0xC407E` = 511, which is why V92's ×1.5 was inert and V94's ×0.25 was
catastrophic." **KILLED.** `0xCBE74`[mode 24/26] Y = [−9830, −5734, −1966, 0] over
X = [0, 1280, 5760] ct; gain = |K|×1.6272e−5 ⇒ ≈0.140 at 6 km/h, so 511 needs |gp-0x6c2c| ≈ 3651.
At the measured rim amplitude the lane runs ~14–16 ct. **Not clamping.** The kit's own
mode-record explanation stands. ⊕ But note: **V92 raised only modes 26/27; V94 lowered mode 24
too. Raising the dose on mode 24 has never been flashed.**

Links: [[reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan]] ·
[[reference_accord_fun38148_six_weight_v95_candidate_census]] ·
[[reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split]] ·
[[reference_accord_task5_rate_resolved_100hz_and_fun389ec_structure]] ·
[[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]]
