---
name: reference-accord-v49-stagec-flip-collocated-damper
description: 2026-07-22 21 Hz re-audit + V49 candidate. The vibration is a FIRMWARE/PLANT closed loop — the openpilot bus command (CAN 0xE4) STRIPS 21.5 Hz via its slew-saturated rate limiter (52% of active steps at the ±123 cap), so the comma is a PASSENGER and no comma-side (Kp/LPF) fix can help. Measurement corrected (broad 10–22 Hz shelf, not a sharp Q=13.6 line; 21.5-vs-78.6 Hz aliasing UNRESOLVED). Aggregator topology COMPLETE. V49 = the state-4 ratchet + a COLLOCATED torque-rate damper made by flipping FUN_0003a382 StageC's sign (subr→sub @0x3a836) AND band-limiting it (pole 0xC644A 1024→64). BUILT+VERIFIED, UNFLASHED — GATED on polarity gp-0x6752=+1 (EEPROM-resident, brick if −1).
metadata:
  type: reference
---

# 2026-07-22 — the 21 Hz vibration is a FIRMWARE/PLANT loop (comma is a passenger); V49 = StageC-flip collocated damper

## Corrections of record (verified this session; these overturn prior framing)
1. **The comma is a PASSENGER at 21.5 Hz.** Re-derived from route b9 raw CAN 399 (`studies/spectra/reanalyze_b9_vibration.py`,
   re-runnable): openpilot's INTERNAL command (`carControl.actuators.torque`) is 0.66-coherent with the
   399 torque at 21.5 Hz, BUT the ACTUAL bus command (`sendcan` addr 228 = 0xE4 STEER_TORQUE) STRIPS it —
   internal→bus attenuation −10 dB, coherence(0xE4, 399torque)@21.5 = **0.17**, no 21.5 peak on the bus.
   Mechanism: the openpilot rate limiter is **slew-saturated** — 52% of active steps sit exactly at the
   ±123/step cap (`|delta|` histogram, `max|cmd|`=4096) — so bus amplitude is set by the slew rate, not the
   input gain, and Kp/feedback-LPF (both UPSTREAM of the clip) cannot change the bus 21.5 Hz. **=> the
   openpilot Kp/feedback-LPF lever is DEAD; the loop closes entirely in firmware/plant.** (The only comma
   knob that touches the bus 21.5 Hz is TIGHTENING STEER_DELTA — weak residual, unlikely cure.)
2. **The measurement was overstated.** Verified from the b9 PSD: peak 21.48 Hz reproduces, but it is a
   **broad 10–22 Hz shelf** with a soft bump only **~1.3 dB** above the 10 Hz level; true Q ≈ 2–8, NOT the
   recorded 13.6; per-window peak wanders (median 19.9, std 2.8 Hz). "Sharp Q=13.6 resonance" is retracted.
   **Aliasing is UNRESOLVED again** — 21.5 Hz is indistinguishable from an aliased 78.6 Hz (no >100 Hz
   witness in the rlog); the earlier "must be 21.5" argument depended on the comma being in the loop, which
   just collapsed. The 1 kHz firmware loop CAN sustain a 78.6 Hz mode. **A frequency-tuned fix risks the
   wrong center.** The `Q_MEAS_4X=13.6` / `|L(21.4)|=0.875` anchors in `studies/models/eps_loop_gain_model.py` /
   `studies/models/eps_v48c_gate2_closed_loop.py` are calibrated to the falsified sharp-line reading and need re-fitting.
3. **The aggregator topology is COMPLETE** (carrier-topo trace, full decompile of the sole gp-0x6b94 writer
   FUN_0003aa2c). No missed dominant carrier. Two new lanes: **gp-0x6ade is DEAD** (zero writers,
   two-method), **gp-0x6b62** (FUN_00036388) is new+live but a slow debounce-like integrator, not a fast
   carrier. So V49A ("there's a carrier we missed") is closed.

## FUN_0003a382 exact datapath (disasm-exact; all gains byte-verified)
`H_a382(z) = [ StageA + StageC + S3 ] / 32 × uVar27 × polarity gp-0x6752`, all EMA poles + uVar27 = UNITY
(nothing filters 21.5 Hz), gains are motor-rate LERPs:
- **StageA** `= 8·residual` (flat, prop; L1 0xC6B26=256, pole 0xC6450=1024 unity)
- **StageC** `= 64·(1−z⁻¹)·residual` (genuine 1-sample DERIVATIVE; L3-deriv 0xC6AE6=2048; pole 0xC644A=1024
  unity; the diff is `subr r14,r15` @**0x3a836** = 0x798E, r15=current−previous)
- **S3** `= (98/1024)/(1−z⁻¹)·residual` (pure integrator, NO pole; 32× DOWN vs StageA/C → minor at 21.5 Hz)
- residual `= clamp(gp-0x4f60 − ref, ±10240)`, ref = signed 3-way select vs cal 0xC6200=8192.
- **Polarity gp-0x6752** is a RAM byte set from an EEPROM/NVM config record (type 0x54: ','→+1, −6→−1),
  default +1; **NOT readable from code.bin** — irreducible via static analysis (V43's "irreducible gap",
  mechanism now pinned).
- Task rates (carrier-topo): magnitude FUN_000352b4 + friction FUN_00036c12 = 1 kHz (confirmed); damping
  FUN_00034350 + boost FUN_00034a72 = separate task FUN_00022ca0 (period not pinned).

## Why V49 = flip StageC's sign + band-limit it (model: `studies/models/eps_v49_a382_stagec_flip_model.py`, re-runnable)
Every carrier MAGNITUDE cut failed (V39 r24, V42 r26, V43/V46 a382 poles, **V48A a382 uVar27 ×0.25 + type-8
mute → null**): shrinking a minority anti-damping term toward zero does little. StageC is the top-ranked,
never-isolated collocated 1 kHz torque DERIVATIVE at unity gain. FLIPPING its sign is categorically
different — it ADDS damping (crosses past zero), not shrinks anti-damping. At polarity +1 the model moves
the a382 loop factor Re from **+0.63 (anti-damping) → damping**, ~2–3.7× the null V48A cut, correct direction.
- **★ GATE 2 forced the band-limit.** The BARE flip (pole left at unity) helps at 21.5 Hz but CREATES new
  anti-damping at **55–140 Hz** (a derivative amplifies with frequency) — a GATE-2 FAIL, and a real brick
  risk given the unresolved 78.6 Hz alias. Lowering the StageC pole **0xC644A → 64** (corner ~10 Hz) rolls
  the derivative off: the loop is DAMPING at 21.5 Hz and has **NO anti-damping anywhere 1–140 Hz** (clean).
  Bonus: confined to ~21.5 Hz, so if the true mode is the 78.6 Hz alias, V49 is a NULL (safe), not a brick.
  (This is V43's pole value, which ALONE was null; the flip is what makes the band-limit do something.)

## V49 build (BUILT + VERIFIED, UNFLASHED — `builds/v18_v49/build_v49_tva.py`)
V38 + THREE edits, 12 bytes / 5 runs, 2 CRC blocks (MAIN 0xC4FFC + CAL 0xC6FFC), 50/50 chain on plain +
RWD round-trip, flip re-decodes as `sub r14,r15`:
- EDIT 1 (code): 0x454FE `bne→br` — the CONFIRMED state-4 ratchet fix.
- EDIT 2 (code): 0x3A836 `0x798E→0x79AE` — subr→sub, single opcode bit 0x20; StageC current−prev → prev−current.
- EDIT 3 (cal): 0xC644A `1024→64` — band-limit StageC to ~10 Hz.
- GATE 1 clean (no new RAM; gp-0x6ad4 not in any int/float lockstep — no interlock to trip, no safety net).

## 🛑 The flash gate (do NOT relax)
Direction depends on **polarity gp-0x6752 (abs 0xFEDF18AE)**: **+1 → DAMPING (fix); −1 → ANTI-DAMPING (a
V48B-class brick)**. Default +1 and a working power-steering car strongly imply +1, but that is INFERENCE.
**Confirm gp-0x6752 = +1 via a read-only, at-rest RAM read BEFORE any flash** (at rest, not steering →
dodges the OBD-mux blocker; exact UDS payload confirmed first, iron rule). Also pre-flash: Ghidra
re-disassemble `_v49_plain_image.bin` @0x3A836 (kit rule for code edits). **Honest residual:** a382 is a
MINORITY carrier (V48A null) → V49 may be a PARTIAL cure even at +1; but it cannot brick at +1. If partial
with the mode confirmed at 21.5 Hz, raise the StageC pole (64→96→128) for more damping + re-check the HF band.

## Related
[[reference-accord-collocation-motor-rate-damper-dead]] (the collocation model this refines — StageC IS the
collocated torque-derivative, the sign-correct version of the OEM damper), [[feedback-cave-two-gates-ram-ownership-and-closed-loop]]
(GATE 2 caught the bare-flip HF anti-damping), [[reference-accord-fun3a382-unfiltered-residual-lane]],
[[reference-accord-v48b-flashed-catastrophic-ram-collision]], [[feedback-default-maximal-thoroughness]].
