# HANDOFF - 2026-07-19 - V39 direct Sensor-B torque-rate guard

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V39 is BUILT and statically VERIFIED, NOT FLASHED. No CAN, UDS, or flash operation occurred.
**Supersedes:** the opposing-only V39 draft in `handoffs/2026-07/HANDOFF-2026-07-18-v39-opposing-torque-rate-guard.md`.

## On-car input

V38 remains fault-free, but the operator separated the remaining behavior into two distinct symptoms:

1. **Several-Hz ratchet:** on hard turns, especially after a stop sign or light, the wheel appears capable
   of turning harder but is intermittently stopped by a feedback loop.
2. **Tens-of-Hz vibration:** under high LKAS torque while the wheel is moving, a frequent steering-wheel
   vibration is felt and can be audible. It occurs at low and high road speed, although it is especially
   pronounced around 5 mph.

The downstream motor/current loop is not intrinsically unable to apply high torque while moving. Strong
driver-side torque can move the wheel quickly through the same motor loop without either vibration or
ratcheting. That on-car observation contradicts the universal motor-capability hypothesis and favors a
driver-conditioned LKAS/assist-lane interaction.

V39 now targets the high-frequency symptom without claiming that both symptoms share one root cause.

## Artifact

```text
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V39-LKAS-4x-V38guards-direct-rate-off417-driver320-0x13000-0x100000.rwd
```

| Artifact | Size | SHA-256 |
|---|---:|---|
| `../accord-firmware/flashing-2020accord/rwd/` V39 RWD | 986042 | `1e9b5ea8b91e43b715ecdf7e7888f83746b5125975ed094040ce64fb4262d505` |
| `../accord-firmware/analysis-2020accord/_v39_plain_image.bin` | 1048576 | `43754b39bed7d2911a4d2e6964cef3f6d6ce5329ad442ff2be869172291f890d` |
| `../accord-firmware/analysis-2020accord/_v38_plain_image.bin` baseline | 1048576 | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/builds/v18_v49/build_v39_tva.py`.

## Why the direct derivative lane

The derivative producer is now instruction-traced rather than inferred from the aggregator alone:

```c
// FUN_0007e74a, called by FUN_0007f3f8
gp_4f62 = 2 * (sensor_b_now - sensor_b_delayed) / wrapped_sample_delta;
// delay calibration tp+0x7c42 = 4
// lockstep shadow = gp-0x4488
```

The producer runs on phase mask `0xD30` (`{4,5,8,10,11}`, 5/16 base ticks). The aggregator
`FUN_0003aa2c` consumes the held value on mask `0xC30` (`{4,5,10,11}`, 4/16 base ticks). If the inferred
1 kHz base tick is correct, the four-producer-sample difference spans about 12.8 ms and the aggregator
runs around 250 Hz. The masks and delay are verified; the conversion to wall-clock Hz remains inferred.

`FUN_0003aa2c` forms two independent lanes from `gp-0x4f62`:

- `r24`: direct derivative times a generated positive Q10 gain, post-gain +/-3 deadzone, +/-8192 clamp.
- `r26`: derivative times adaptive slope `gp-0x69a4` and another positive Q10 gain, +/-8192 clamp.

At the low-rate/low-voted-torque table point, `gp-0x4f62=512` produces `r24=1533`. That is comparable
to V38's approximately 1782-count full LKAS contribution and is large enough to create torque ripple
before the common governor. The direct sampled lane is therefore the strongest static match for the
tens-of-Hz symptom. `r26` remains a live secondary candidate because its on-car adaptive slope is unknown.

## Why the governor remains unchanged

The governor is motor-resolver-rate scheduled, not road-speed scheduled, so it can operate at low and
high vehicle speed. It also contains state, one-sided 512/205-count slew, and held-value substitution,
which makes it a credible secondary candidate for the slower ratchet.

It is not the leading explanation for the common high-frequency vibration:

- the adaptive table is monotone piecewise-linear and its quantization is only a few counts;
- strong driver torque demonstrates that the same downstream motor loop can deliver high moving torque
  smoothly under a different demand composition;
- changing the governor would affect manual assist and intentional motor protection while confounding the
  direct-lane experiment.

V39 leaves `FUN_0007b022`, `gp-0x4f64`, both governor applications, post-governor compensation, the
shaper, FOC, PWM, and every V38 calibration byte unchanged.

## V39 behavior

On the normal/full aggregator path only:

```c
if ((uint16_t)gp_6a62 < *(uint16_t *)(tp + 0x7312) &&  // existing threshold 320
    abs(lkas_r7) >= 417) {                             // exact lower V9 full-scale magnitude
  direct_torque_rate_r24 = 0;                          // both signs
}
```

Truth table:

| Condition | Result |
|---|---|
| voted driver torque >=320 or invalid sentinel `0xFFFF` | V38 behavior |
| LKAS below 100% V9 magnitude, `abs(LKAS)<417` | V38 behavior |
| reduced aggregator mode | V38 behavior; guard is not reached |
| at least 100% V9 LKAS magnitude and voted driver torque <320 | direct `r24` is zero for both signs |

The threshold comes from stock V9 arithmetic: `15360*891>>15` is `+417`, while the negative direction is
`-418` because V850 `sar` rounds downward. Using 417 ensures 100% V9 torque is eligible in both directions;
the rounded prose value 418 would miss the positive direction. Because `r7` is an internal mixer lane,
417 is not an exact raw-comma-command percentage in V38.

The initial V39 draft suppressed only `r24` samples opposing LKAS. That was sufficient to test a
unidirectional cancellation hypothesis, but it retained same-sign pulses and half-wave rectified a lane
whose sign can alternate at the control cadence. The revised all-sign guard is the smallest experiment
that tests the direct derivative lane as the source of bidirectional high-frequency torque ripple.

The adaptive derivative lane `r26` stays live. V39 also does not suppress `gp-0x6bd0`, `gp-0x6ad4`,
`gp-0x6b26`, `gp-0x6b62`, or `FUN_00036682`.

## Code patch

Hook:

```text
0x3ac78  old 24 4f 30 94  ld.h -0x6bd0[gp],r9
         new 88 07 bc 9e  jr 0x000c4b34
```

Exact cave disassembled from final image SHA-256
`43754b39bed7d2911a4d2e6964cef3f6d6ce5329ad442ff2be869172291f890d`:

```text
0xc4b34  ld.hu  -0x6a62[gp],r6
0xc4b38  ld.hu   0x7312[tp],r8
0xc4b3c  cmp     r8,r6
0xc4b3e  bnc     0xc4b58          ; driver >=320 or sentinel: bypass
0xc4b40  mov     r7,r6
0xc4b42  cmp     r0,r6
0xc4b44  bge     0xc4b48
0xc4b46  subr    r0,r6            ; abs(LKAS)
0xc4b48  addi   -0x1a1,r6,r0
0xc4b4c  blt     0xc4b58          ; abs(LKAS)<417: bypass
0xc4b4e  mov     r24,r6           ; preserve old r24 in scratch
0xc4b50  mov     r0,r24           ; suppress direct lane for both signs
0xc4b52  cmp     r0,r6            ; legacy sign tail, now behaviorally redundant
0xc4b54  bge     0xc4b58
0xc4b56  mov     r0,r24           ; negative path writes zero again
0xc4b58  ld.h   -0x6bd0[gp],r9    ; displaced instruction
0xc4b5c  jr      0x0003ac7c
```

If old `r24>=0`, the branch at `0xC4B54` skips to the displaced load after `r24` was zeroed. If old
`r24<0`, `0xC4B56` writes zero a second time. No path after `0xC4B50` can restore `r24`.

`r6` is reloaded by original code at `0x3AC80`; `r8` is overwritten before its next original use. `r26`
and all other live registers are preserved. The cave has no call, stack operation, or link-register write.

Contiguous cave bytes:

```text
e4379f95e5471373e831d90d0730e031ae05803106065ffe
e605183000c0e031ae0500c0244f3094b7072061
```

## Verification

- Final image independently imported as raw `V850:LE:32` and hash-verified in Ghidra.
- V39-vs-V38 is exactly 52 bytes in three runs:
  - `0x3ac78..0x3ac7b`: 4-byte hook.
  - `0xc4b34..0xc4b5f`: 44-byte cave.
  - `0xc4ffc..0xc4fff`: 4-byte main-block CRC.
- Main CRC: `0xCC2134EF -> 0x7CCB9546`.
- Strict chain verification passes all 49 blocks on V38, V39 plain, and decoded V39 RWD.
- RWD readback equals `../accord-firmware/analysis-2020accord/_v39_plain_image.bin[0x13000:0x100000]` byte-for-byte.
- V39 retains every V38 calibration and every non-main CRC block byte-for-byte.
- Relative to the preceding all-sign/1536 V39, this revision changes two immediate bytes plus the
  recomputed main CRC. Relative to V38, the changed-byte geometry remains the same 52 bytes.
- Golden model self-checks cover 416/417, exact V9 `+417/-418`, 319/320, invalid sentinel, both `r24` signs, zero `r24`,
  reduced-mode bypass, and preservation of `r26`.
- Hook/cave worst-case execution time remains unmeasured.

## Road-test interpretation

The two symptoms must be scored separately:

- **Tens-of-Hz vibration improves, ratchet remains:** direct `r24` is strongly implicated in the vibration;
  the slower stateful ratchet is separate. Next investigate governor held/mode state or filtered feedback.
- **Both improve:** `r24` contributes to both time scales, but this does not prove it is the only ratchet path.
- **Vibration remains:** inspect adaptive `r26` first, then `gp-0x6bd0`/`gp-0x6ad4`; do not jump directly to
  weakening the governor.
- **New overshoot or reduced damping:** `r24` was providing useful stabilization inside the guard envelope;
  return to V38.

The best synchronized capture remains `gp-0x4f62`, `gp-0x6ada` (`r24` snapshot), `gp-0x6adc` (`r26`
snapshot), `gp-0x6b4c`, `gp-0x6b94`, `gp-0x4f64`, `gp-0x138a`, `gp-0x6ace`, `gp-0x6acc`, and
`gp-0x6b98`. CAN-rate telemetry may undersample the tens-of-Hz event.

`analysis-2020accord/model/eps_lkas_chain_model.py` is the live golden reference and was updated with the exact
producer/consumer phase masks, lockstep derivative producer, revised all-sign V39 guard, and executable
boundary/preservation checks.
