---
name: reference-accord-gp4f60-no-producer-filter-raw-sensor
description: gp-0x4f60 (Sensor-B/TAS driver column torque) has NO dynamic filtering anywhere in its producer chain -- FUN_0007f300 is a static zero-offset bias, not a phase-correction filter -- so it is a raw, near-instantaneous read with no compensation for the EPS motor's own reaction torque.
metadata:
  type: reference
---

# gp-0x4f60's producer chain has ZERO dynamic filtering -- CORRECTS inherited kit memory

Traced fresh 2026-09-01 (GhidraMCP, stock `code.bin`), while adjudicating the operator's
driver-torque-feedback-loop hypothesis for V276/V277 (see [[reference-accord-second-driver-torque-gate-cbae4-cbbc4]]).

## The correction

Prior kit memory (`reference_accord_gp4f60_is_sensor_b_column_torque.md`) described the producer
chain as: "2-pt interp + per-sensor gain `gp-0x25d4` + **phase correction** `FUN_0007f300` + learned
gain `gp-0x698c` / offset `gp-0x6b50` + clamp `gp-0x4f54`". **"Phase correction" is wrong.**
`FUN_0007f300`, freshly decompiled:

```c
int FUN_0007f300(short param_1) {
    short sVar1 = *(short *)(unaff_gp + -0x6b66);
    if ((sVar1 + 0x134U) < 0x269) param_1 = param_1 + sVar1;
    else if (sVar1 < 1)           param_1 = param_1 + -0x134;
    else                          param_1 = param_1 + 0x134;
    return param_1;
}
```

This is a **static mechanical zero-offset bias** (adds a calibrated constant `gp-0x6b66`, clamped to
±0x134 = 308) with **no internal state, no history, no time constant**. It runs once per call and
returns immediately -- there is nothing here that could introduce phase lag. That other memory file
has been corrected in place to remove the "phase correction" label (2026-09-01).

## Consequence: the whole producer chain is undelayed

Walking the full chain (`FUN_0007ec34` → `FUN_0007f3f8`): 2-point ADC interpolation → per-sensor gain
`gp-0x25d4` → the static bias above → learned gain `gp-0x698c` / offset `gp-0x6b50` → clamp
`gp-0x4f54` → store. **Every stage is a static (memoryless) transform.** There is no low-pass, no
debounce, no moving average anywhere between the ADC sample and `gp-0x4f60`.

Combined with the separately-confirmed fact that the taper index `gp-0x682f = min(|gp-0x4f60|>>5,
255)` is ALSO computed fresh every call with zero lag (`0x29048-0x29068`, re-confirmed this session
against V277's own build-script byte assertions), **the entire path from raw torsion-bar ADC sample to
the LKAS taper's gating decision carries no firmware-side delay at all** -- any dynamics in a
torque-sensor feedback loop through this path come entirely from the mechanical plant, not from
signal processing.

## Identity and contamination verdict (unchanged from prior memory, restated for context)

`gp-0x4f60` = Sensor-B/TAS **raw driver column torque**, signed. Decisive evidence (prior session,
not re-derived here): CAN-399 packer `FUN_00055c42` emits `STEER_TORQUE_SENSOR = -(gp-0x4f60 *
125/128)` directly -- a value packed onto the bus AS the torque sensor is the torque sensor, not a
derived/compensated "driver intent" estimate.

**Contamination verdict: BELIEF, not derivable from firmware alone.** A torsion-bar sensor sitting
between the driver's hands and the point where EPS assist enters the column/rack is, by mechanical
construction, in the same load path as the motor's reaction torque. With zero compensation for
motor-current or commanded-assist reaction found anywhere in this producer chain, **there is nothing
in this firmware that would prevent the motor's own output from appearing on this channel** when
driver hand impedance is low -- the textbook EPS "torque sensor sees its own assist" pathology.
Fully consistent with the operator's report that holding the wheel firmly (raising driver-side
mechanical impedance at the exact point that closes the loop) suppresses the V276 oscillation.

## Related
[[reference-accord-second-driver-torque-gate-cbae4-cbbc4]] -- the two consumer gates this raw signal drives.
[[reference-accord-pid-output-5hz-lag-dc-gain-trap]] -- the one real dynamic element downstream, in the forward path.
