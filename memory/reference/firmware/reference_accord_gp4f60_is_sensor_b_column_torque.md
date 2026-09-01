---
name: reference-accord-gp4f60-is-sensor-b-column-torque
description: "CORRECTION of record: gp-0x4f60 is SENSOR-B (TAS) DRIVER COLUMN TORQUE -- proven by the CAN 399 packer FUN_00055c42 emitting STEER_TORQUE_SENSOR = -(gp-0x4f60 x 125/128). It is NOT column/motor angular velocity (Era 18 / segmentD label) and NOT vehicle speed (assist-lane label). Consequence: the gentle-EME debounce watches DRIVER hand torque, not the LKAS command -- the V36/V37 causal story is reframed"
metadata:
  node_type: memory
  type: reference
---

A single variable-identity correction that propagates into the gentle-EME root-cause story, the assist-lane gating model, and any future reading of `m_steer_torque_arbitration`.

## The correct identity

`gp-0x4f60` (absolute `0xFEDF30A0`) = **Sensor-B / TAS driver COLUMN TORQUE**, signed.

Decisive evidence — the CAN 399 packer `FUN_00055c42`:

```
STEER_TORQUE_SENSOR (bytes[0:1]) = -(gp-0x4f60 * 0x7d >> 7)   ; = -(gp-0x4f60 * 125/128)
STEER_ANGLE_RATE    (bytes[2:3]) = -(gp-0x6a56)
```

A value packed onto the bus *as* `STEER_TORQUE_SENSOR` is the torque sensor. This was already recorded in [[reference-accord-dual-torque-sensor-architecture]] (sensor B = the CAN/TAS sensor, the only one carrying absolute angle) — the error was that two *other* memories independently attached different labels to the same address without reconciling.

Producer: `FUN_0007f3f8` (decompile fails on the ENCA0 struct — use disasm): 2-pt interp + per-sensor gain `gp-0x25d4` + a static zero-offset bias `FUN_0007f300` + learned gain `gp-0x698c` / offset `gp-0x6b50` + clamp `gp-0x4f54` -> store `@0x7f9c8`.

> 🛑 **CORRECTED 2026-09-01**: `FUN_0007f300` was mislabelled "phase correction" above. Freshly
> decompiled, it is a stateless mechanical zero-offset bias (`param_1 + clamp(gp-0x6b66, ±0x134)`),
> not a filter — no history, no time constant, no phase effect at all. The entire producer chain is
> memoryless; there is no dynamic filtering anywhere between the ADC sample and `gp-0x4f60`. See
> [[reference-accord-gp4f60-no-producer-filter-raw-sensor]] for the full re-trace and its
> consequence for the V276/V277 driver-torque-feedback-loop analysis.

## What was wrong, and where

1. **Era 18 constellation entry + `reference_accord_segmentD_fun3d04c_full_gate_map.md`** labelled it "column/motor angular velocity [STRONG]". The confusion is understandable: `gp-0x4f68 = clamp(ABS(gp-0x4f60), 0, 0xFFFF)` really *is* consumed as a rate-like gate input in Segment D. But that is a downstream *use*, not the signal's identity. Deriving "this is a velocity" from "a velocity gate reads it" was the inferential slip.
2. **The base-assist trace** first read `FUN_000352b4`'s `+/-25600` check as a speed gate, then inverted its final branch. Both are corrected: this is Sensor-B torque plausibility, and normal in-window torque stores the computed `gp-0x6b86`/`gp-0x69a4`; only out-of-window torque forces zero. The lane is active in normal driving. Separately, `gp-0x4f62` is the four-sample finite difference of this Sensor-B torque and feeds two inline aggregator lanes; see the V39 handoff and canonical model.

## The consequence that matters: the gentle-EME story is reframed

The gentle-EME debounce SM's torque channel is:

```
0x28f26  ld.h  -0x4f60, gp, r15       ; <- DRIVER column torque
   ... r15 never rewritten through 0x29068 (every instruction in the span read directly) ...
0x29048  mov r15, r7 ; sar 0x5 ; abs ; saturate 0xFF
0x29068  st.b r8, -0x682f, gp         ; the debounce/DTC-49 torque byte
```

So `gp-0x682f = min(|driver column torque| >> 5, 255)`.

**The debounce watches the driver's hands, not the LKAS command.** V37 still works, and for the reason believed — raising the gate to 255 means `torque > 255` can never fire against a channel that saturates *at* 255. But the framing "gentle EME fires on a saturated LKAS command" (see [[gentle-eme-fires-on-saturated-lkas-command]]) has the causal direction backwards. The correlation with saturated LKAS commands is real but incidental: hard curves are where the driver is also loading the column.

This also explains cleanly why the felt event was mid-turn **with hands on the wheel**, and why LKAS-command-side experiments (V33's decider gate) kept missing.

A practical corollary: **the LKAS setpoint magnitude cannot provoke the gentle EME at all**, which is what makes raising the `+/-15360` setpoint clamp safe — see [[reference-accord-setpoint-limit-15360-lerp]].

## Method note

This is the second time on this project that a *use-site* label was mistaken for a *signal identity* (compare the governor's LERP axis, corrected 2026-07-17 from "vehicle road speed" to "motor resolver electrical-angle rate"). When a memory names a signal, prefer evidence from its **producer** or from a **CAN packer** over evidence from a consumer's gate semantics.

Related: [[reference-accord-dual-torque-sensor-architecture]], [[reference-accord-can399-torque-vs-voter-scale]], [[v37-dtc0x49-fix-and-0xc64b8-blast-radius]], [[reference-accord-lkas-delivery-and-governor]]
