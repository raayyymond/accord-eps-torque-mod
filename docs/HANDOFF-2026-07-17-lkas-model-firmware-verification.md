# HANDOFF — 2026-07-17 — LKAS CAN→motor model firmware-verified (5 operator review comments)

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Target:** stock Ghidra `code.bin`, flat base 0; `gp=r4=0xFEDF8000`, `tp=r5=0xBF000`. **Tooling:** GhidraMCP on the open `code.bin`, 3 parallel `firmware-codepath-tracer` subagents (Sonnet 5) + local `opendbc_reference/honda`.

## What happened

The operator reviewed `analysis-2020accord/eps_lkas_chain_model.py` after V38 and raised 5 comments. Each was resolved by decompilation (instruction-pinned against stock `code.bin`) and the model was corrected. **No CAN, UDS, or flash operation occurred. No build changed.** This was a model-accuracy pass only.

> **SUPERSEDED MODEL DETAILS (2026-07-18 V39 session):** the later aggregator/governor trace found additional corrections: assist-inclusive `gp-0x6acc` can conservatively reach 7322; `gp-0x3570` is signed Q15; first-governor slew limits only movement away from zero; and final `gp-0x6b98` comes from `gp-0x6afe+r20`, not directly from `gp-0x6acc`. The canonical current implementation is `analysis-2020accord/eps_lkas_chain_model.py`; see the V39 handoff.

## The 5 comments and their firmware verdicts

### 1. `arb_setpoint_limit` (15360) < 0x4000 → LKAS clipped at top-end — **CONFIRMED**
The LKAS setpoint (max `0x4000`=16384) is clamped to `±LERP(mode/gear curve)` in `FUN_00028ea6` @0x28fc8–0x29044: index `gp-0x674e` → pointer array `0xCB844` → curve `@0xE4180`, mode-0 value row **constant 15360**. So full-scale LKAS *is* clipped ~6% at the top. Data-driven LERP, not a flat literal (only mode 0 byte-dumped; other modes open).

### 2. `lkas_term` shift `>>10` labelled "illustrative" — **WRONG; actual is Q15 `>>15`**
The final gain multiply is `sar 0xf` (>>15) @0x2a202, not `>>10`. The `>>10` was a real instruction (`sar 0xa` @0x2a1a0) but belongs to an **earlier Q10-IIR blend** of `gp-0x3d3c`, mis-attributed to the gain. With Q15: `15360×891>>15 ≈ 418`, inside the ±512 clamp (`>>10` gave ~13,370 — 26× over the clamp; that was the "32768 > clamp" smell the operator caught). Cal reads confirmed: gain `0xC646C`=891, arb clamp `0xC61B4`=512, pack clamp `0xC61B2`=512.

### 3. "driver assist added to `arb_signal`" — **REFUTED**
No driver-assist term is added inside `FUN_00028ea6`. The two adds feeding the `gp-0x6b3c` store @0x2a2ea are both **internal setpoint-descended terms** (one gated on the dead `gp-0x6809`, so ≈0); the final store is `shaped_term × (0/1 mode gate gp-0x67a4∈{2,3})` — **multiplicative, not additive**. Driver-assist is a **separate downstream mixer source** (LKAS = distribute source index 1, one of ~10 summed into `gp-0x6b94`). Model: `+ assist` removed from arbitration, merge relocated to the mixer stage.

### 4. LKAS ignored below 3 mph — **NOT in firmware; openpilot-side**
A dedicated trace found **no speed threshold anywhere** in CAN-decode → arbitration → decider → engage-SM → mixer → shaper. The 3-mph number is openpilot's: `STEER_GLOBAL_MIN_SPEED = 3·MPH_TO_MS` and Accord `minSteerSpeed = 3·MPH_TO_MS` (`opendbc_reference/honda/values.py`). Below that, controls runs `latActive=False` → `create_steering_control` TXes STEER_REQUEST=0. The EPS *also* locks out near standstill and reports `STEER_STATUS=LOW_SPEED_LOCKOUT` on CAN 399 (opendbc comment: "All Honda EPS cut off slightly above standstill"), treated as expected below `min_steer_speed`. **[OPEN]** the firmware producer of `LOW_SPEED_LOCKOUT` is not in the LKAS command pipeline (wheel-speed decoder unlocated; `KFC_WHEEL_SPEED` strings @0xB9BA4 dead-end at a DTC table). Model: dedicated note added; nothing to add to the firmware chain.

### 5. Runtime governor — **statically traced; NOT a flat clamp, and NOT speed-adaptive**
`gp-0x4f64` is **computed**, not flat ±4762. Motor-state byte `gp-0x4e5a` selects 3 branches; the operative LKAS-engaged branch (==1): `gov = MIN(4762, adaptive_LERP, energy_budget)` → ceiling 4762, floor 0. **7-hop instruction trace proved the adaptive LERP axis (`gp+0x128`) is the MOTOR RESOLVER electrical-angle RATE, not vehicle road speed:**

```
gp+0x128 LERP (tp+0x6030/tp+0x620E) axis = gp-0x6ac0
 ← FUN_00041464  (slew-limit + IIR + sign-gate vs commanded torque gp-0x6b98)
 ← gp-0x4f50     (IIR, range-clamped ±13000, 65535=invalid  → not a raw wrapping angle)
 ← FUN_00068fbe  (IRQ-guarded snapshot of resolver-rate reg gp-0x29c4)
 ← FUN_00068f52  (Δ of consecutive angle samples, 0x4000=14-bit wraparound correction → RATE)
 ← FUN_00065afe  (resolver sin/cos ATAN2 decode, output & 0x3fff = 14-bit electrical angle)
```

So the governor tapers authority during **fast steering motion** (quick corrections, parking lock-to-lock), NOT at highway speed. Applied across **3 consumers** (not 1): (1) `m_motor_torque_governor` FUN_0004503c @0x453f0 `clamp(gp-0x6b94, ±(gov×speed_scale)>>15)` upstream; (2) shaper FUN_00042af8 @0x43b0a `clamp(demand, ±gov)` **then a separate static ±0x2000** @0x43b0e (two sequential clamps); (3) a steady-state diagnostic override FUN_0006e09a/e140 @0x6e0f2 (gated `delta<25`) that writes `gp-0x6b98 = gov×1` directly, likely a motor self-test (dispatch caller 0xBCB14/18 untraced). **[OPEN]** normalization ratio `fVar48`; Consumer-1's own `speed_scale` `gp-0x6a64` identity; diagnostic path trigger.

## Files changed

- `analysis-2020accord/eps_lkas_chain_model.py` — all 5 corrections landed; runs clean; V9 still shows the gentle EME, V37/V38 resolve it (command magnitudes now realistic post-Q15).
- Memory corrected (stale "speed-adaptive governor" → motor-rate): `memory/reference_accord_lkas_delivery_and_governor.md`, `memory/MEMORY_CONSTELLATION.md`, `memory/project_accord_torque_mod_v0.md`, `memory/MEMORY.md`, `analysis-2020accord/FUN_00043e44_FLOAT_MONITOR.md`, and the tracer agent-memory (`reference_accord_governor_gp0x184_chain.md`, `reference_accord_post_governor_comp_add.md`, new `reference_accord_gp4f64_three_consumers.md`).
- `docs/HANDOFF-2026-07-17-v38.md` — governor caveat corrected + update pointer.

## Bonus discrepancy (not one of the 5; flagged, not yet acted on)

arb_tracer found the arbitration final store gated by `gp-0x67a4 ∈ {2,3}`, but the model's `enable_fsm_producer` claims `gp-0x67a4` has **zero readers** ("dead gate"). If confirmed, the ENABLE byte IS consumed as a multiplicative LKAS-delivery gate. Left the model's `[OPEN]` note as-is; candidate next trace.
