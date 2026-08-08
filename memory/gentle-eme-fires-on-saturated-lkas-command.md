---
name: gentle-eme-fires-on-saturated-lkas-command
description: Gentle EME (STEER_STATUS=NO_TORQUE_ALERT_2) diagnosed from the 2020 Accord rlogs — it fires when the sensor-A column-torque voter crosses cal 0xC6312=320 during a demanding curve where openpilot's LKAS command is SATURATED (4096) and a road disturbance (railroad tracks) rings the column torque past threshold. Reconstructed from CAN 399/427/228 (no epsTelemetry in the logs).
metadata:
  node_type: memory
  type: reference
  originSessionId: da1ed7ee-745a-43f9-a29b-a7b80b6ac40f
  modified: 2026-07-18T15:55:28.952Z
---

> **UPDATE 2026-07-18 — THE CAUSAL DIRECTION IN THIS MEMORY'S TITLE AND DESCRIPTION IS BACKWARDS.**
> The debounce SM's torque channel is **DRIVER column torque, not the LKAS command**:
> `gp-0x682f = min(|r15| >> 5, 255)` where `r15` is loaded once at `0x28f26` (`ld.h -0x4f60,gp,r15`) and
> never rewritten through the store at `0x29068` — every instruction in that span was read directly.
> `gp-0x4f60` = Sensor-B (TAS) column torque, proven by CAN-399 packer `FUN_00055c42`
> (`STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`). See [[reference-accord-gp4f60-is-sensor-b-column-torque]].
>
> So: **the LKAS setpoint magnitude cannot trigger the gentle EME at all.** The observed correlation with
> saturated (4096) LKAS commands is real but INCIDENTAL — hard curves are exactly where the driver is also
> loading the column. This is why LKAS-command-side experiments (V33's decider gate) kept missing, and it
> fits the operator's report that the felt event was mid-turn *with hands on the wheel*.
> V37 still works and for the believed reason: raising the gate to 255 means `torque > 255` can never fire
> against a channel that saturates *at* 255. Only the "why" changes, not the fix.
> (Title/filename retained for stable linking; treat the name as historical, not a claim.)

> **UPDATE 2026-07-14 (route 7f, V31P-V2 telemetry + Ghidra — supersedes the decider-gate root cause below).**
> The gentle EME is NOT the engage-SM decider `FUN_00040d58` `gp-0x6a62≥0xC6312`=320 gate (that fires ~10 Hz
> BENIGN and does not correlate with the cut). It is the **debounce state machine `FUN_0002a30e` (+ inline twin
> in `m_steer_torque_arbitration`)**: STEER_STATUS=4 fires after **5 sustained cycles** (cal `0xC64E2`=5,
> counter `gp-0x6757`) of `torque gp-0x682f>cal 0xC64B4(112) OR angle-rate param_1>cal 0xC61C0(1600)`. Full
> mechanism + corrections in [[v36-debounce-sm-root-cause-and-build]]. Also: `STEER_STATUS=4` is a **lagging
> report** (not the torque cut); `gp-0x6809` (prior 'cut anchor') is **dead code, 0 writers**; the actual
> motor-zeroing instruction is still unlocated.
> **Operator anchor (record for all future docs):** on route 7f the gentle EME was at **route 5:27** (root
> cause ~5:26), felt as a **sharp, slight straightening of the wheel in the middle of a turn** — NOT the
> STEER_STATUS=4 report at 5:31.3 (that lags / is a separate later event; the felt 5:27 straightening does not
> raise STEER_STATUS=4 on CAN and is below CAN angle resolution). The observable signature to look for is the
> wheel-straightening, not `STEER_STATUS`. V36 (debounce-SM disable) built to test this — [[v36-debounce-sm-root-cause-and-build]].

Diagnosed 2026-07-12 from route `807a3c21c9f405e8_00000058` (rlogs in `analysis-2020accord/rlogs/`). The gentle EME is the stock EPS torque disengage (engage-SM decider `FUN_00040d58`, `gp-0x6a62` MAX-of-5 rising-edge sensor-A column torque ≥ cal `0xC6312`=320) — **still live on V31U** (V33's 320→65535 disable is unflashed).

**On CAN it is `STEER_STATUS`(CAN 399, bits 39|4) = 4 `NO_TORQUE_ALERT_2` + `STEER_CONTROL_ACTIVE`→0 + delivered torque→0.** openpilot deliberately does NOT treat NO_TORQUE_ALERT_2 as a fault (`opendbc/car/honda/carstate.py:128`; comment: "can be caused by bump or steering nudge from driver") → it is INVISIBLE in `carState`; you must decode raw CAN 399. There was **no `epsTelemetry`** in these logs (see [[comma4-eps-uds-poll-comma-vs-redpanda]]), so the whole diagnosis is from comma-visible CAN.

**The 2:08 event** (route t≈130.4–132.0 s, ~42 mph, LKAS engaged, left curve): **3 cuts, 91/91/130 ms.** The column-torque sensor rings ±2000–3000 LSB (angle-rate spikes 40–70°/s = the railroad-track jolt) on top of a LKAS command **saturated at 4096**; the internal voter crosses 320 → 3 cuts. The trip is NOT a fixed CAN |torque| (cut#3 tripped at −2262 while −1961 ms earlier was normal; cut#1 at +1467) — that's the rising-edge/MAX-of-5 internal signal; CAN `STEER_TORQUE_SENSOR` is only a lagging filtered proxy. 6 gentle-EME runs total in the drive.

**Direction asymmetry** (why one way over the tracks and not the other): the trip needs the column-torque PEAK > 320 = directional (camber/curve) steady load + the disturbance. Only in the EME direction was the LKAS command SATURATED (column pre-loaded near threshold), so the bump crossed it; the reverse pass had margin. This is the practical trigger: **hard/saturated-command curve + a road bump**, not the bump alone.

**Why it matters / how to apply:** the targeted fix should reshape the `0xC6312`=320 gate (raise/rate-limit/hysteresis on the rising-edge voter) rather than V33's blunt disable — but designing it well wants the internal voter trace at the cut, which needs the live-RAM-logging capability that is currently blocked (see [[comma4-eps-uds-poll-comma-vs-redpanda]]). Full write-up: `docs/HANDOFF-2026-07-12-comma4-uds-live-telemetry-bus-analysis.md` §1.
