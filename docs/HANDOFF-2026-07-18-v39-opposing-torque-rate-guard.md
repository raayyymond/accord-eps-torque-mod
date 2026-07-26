# HANDOFF - 2026-07-18 - V39 opposing Sensor-B torque-rate assist guard

> **SUPERSEDED 2026-07-19:** this records the initial opposing-only V39 draft. New on-car feedback split
> the several-Hz hard-turn ratchet from a common tens-of-Hz high-LKAS vibration. The current V39 suppresses
> direct `r24` for both signs at the exact V9 full-scale equivalent (`|LKAS lane|>=417`) and low driver torque. Use
> `HANDOFF-2026-07-19-v39-direct-torque-rate-guard.md` and the golden chain model for current behavior.

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V39 is BUILT and statically VERIFIED, NOT FLASHED. No CAN, UDS, or flash operation occurred.
**Issue:** `accord-eps-torque-mod-u08` (closed after build/model/artifact verification).

## On-car input

V38 was flashed and works without dashboard or DTC errors. On hard turns, however, its 4x LKAS authority
appears to be limited by a feedback loop. The operator's physical hypothesis is:

```text
hard LKAS torque
  -> steering-column jerk
  -> steering-wheel inertia creates phantom opposing column torque
  -> EPS generates driver-side assist in that opposing direction
  -> net LKAS authority falls
```

V39 is a narrow experiment for that mechanism. It does not raise or disable the independent motor-rate
governor.

## Artifact

```text
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V39-LKAS-4x-V38guards-opposing-rate-guard1536-driver320-0x13000-0x100000.rwd
```

| Artifact | Size | SHA-256 |
|---|---:|---|
| `../accord-firmware/flashing-2020accord/rwd/` V39 RWD | 986042 | `d3d988d3fb2f751c685570dfdf87ccf43d2a7d4a362c51064491b635ee034276` |
| `../accord-firmware/analysis-2020accord/_v39_plain_image.bin` | 1048576 | `0dd667ec3d729909f6b3b68a8066a6ce074be1bbd15a4fb88520d146087e9952` |
| `../accord-firmware/analysis-2020accord/_v38_plain_image.bin` baseline | 1048576 | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/build_v39_tva.py`.

## New reverse-engineering findings

### The aggregator contains two Sensor-B torque-rate lanes

`gp-0x4f62` is not a second static torque signal. Its producer computes a four-sample finite difference
of Sensor-B column torque `gp-0x4f60`:

```c
gp_4f62 = 2 * (sensor_b_now - sensor_b_delayed) / wrapped_sample_delta;
// delay calibration tp+0x7c42 = 4
```

`FUN_0003aa2c` converts it into two inline aggregator lanes:

- `r24`: direct torque-rate lane, generated positive Q10 gain, +/-3 deadzone, final +/-8192 clamp.
- `r26`: torque rate multiplied by the adaptive slope `gp-0x69a4` and another generated Q10 gain,
  final +/-8192 clamp.

The direct `r24` lane is the best static match for a short inertial counter-assist transient. At low
voted torque and low motor rate its gain is 3.0, so `gp-0x4f62=+512` produces `r24=+1533`; a sufficiently
large derivative reaches the +/-8192 lane clamp. V38's full-scale LKAS lane is only about 1782 counts,
so this lane is easily large enough to cancel it before the common governor.

The exact full-mode sum at `0x3acc8..0x3ace6` is:

```c
total = inline_a_r26;
total += inline_b_r24;
total += range_gate(gp_6b86, 0x3000);
total += range_gate(gp_6bd0, 0x0800);
total += range_gate(gp_6bbe, 0x0800);
total += range_gate(gp_6b26, 0x0400);
total += range_gate(gp_6b62, 0x2000);
total += range_gate(gp_6ad4, 0x2800);
total += range_gate(gp_6b4c_lkas, 0x2800);
total += gp_6ade_dead;
total += FUN_00036682();
gp_6b94 = clamp(total, -0x2800, 0x2800);
```

Range failures contribute zero rather than endpoint-clipping.

### Correction: `gp-0x6b86` is active in normal driving

The prior assist model inverted the final validity branch in `FUN_000352b4`. Normal Sensor-B torque in
the inclusive `[-25600,+25600]` window stores the computed `gp-0x6b86`; only an out-of-window value
forces it to zero. Its exact adaptive magnitude remains open and is an explicit replay input in the model.

### The reduced aggregator mode is not an LKAS flag

`gp-0x67ac==1` selects a reduced sum, but its only writer derives it from source modes 6/7. A160's
`tp+0x5124` source-mode bytes contain no 6/7 entries, so this state remains zero in normal execution.
Changing that calibration would globally remove assist lanes and alter mixer semantics; it was rejected.

## Competing limiter: motor-rate governor

The independent trace strengthened the alternative explanation. `FUN_0007b022` computes `gp-0x4f64`
as the minimum of nominal 4762, a normalized motor electrical-angle-rate table, and - in the operative
branch - an unresolved feasibility budget.

A160's exact fixed-point table is:

| Normalized axis `z` | 1050 | 1700 | 2500 | 3700 | 4100 |
|---:|---:|---:|---:|---:|---:|
| Stored Y | 5325 | 3584 | 2406 | 1587 | 512 |

Q13 slopes are `[-21940,-12059,-5593,-22021]`, with shift `0xC5160=13`. Due to arithmetic-shift
rounding, exact results include 4607 at `z=1318`, 4342 at `z=1417`, and 1586 at `z=3700`.

The former 4608/4342 "maximum command" argument omitted the newly mapped assist lanes. The conservative
integrator-input envelope is `abs(gp-0x6acc) <= 4762 governor + 2560 compensation = 7322`; no sign
exclusion or intervening clamp narrows it before the shaper's +/-8192 sanitize.

There is no on-car capture of `z`, `gp-0x4f64`, `gp-0x6b94`, or `gp-0x6ace`, so static analysis does not
prove this table binds in the reported turn. V39 leaves it completely unchanged. Raising `0xC6202`
alone would not lift the descending table or budget minimum and would broaden thermal/mechanical risk.

## V39 behavior

The patch runs only on the normal/full aggregator path:

```c
if ((uint16_t)gp_6a62 < *(uint16_t *)(tp + 0x7312) &&  // existing threshold 320
    abs(lkas_r7) >= 1536 &&                            // high LKAS only
    (int16_t)lkas_r7 * (int16_t)torque_rate_r24 < 0) { // opposing, both nonzero
  torque_rate_r24 = 0;
}
```

Why 1536:

- V38's primary gain-limited contribution is approximately `16384*3564>>15 = 1782`, so 1536 catches
  the intended high-demand regime in the simplified single-source case.
- `r7` is the LKAS-internal mixer output, not the raw comma command. Other internal terms can move the
  activation point, and 2048 is not globally unreachable. No exact raw-command percentage is claimed.
- `abs(LKAS)==1536` is eligible; 1535 is not.

Truth table:

| Condition | Result |
|---|---|
| voted driver torque >=320 or invalid sentinel `0xFFFF` | unchanged, fails open |
| LKAS absent or `abs(LKAS)<1536` | unchanged |
| torque-rate lane zero or same direction as LKAS | unchanged |
| high LKAS, voted torque <320, torque-rate lane opposes LKAS | only `r24` becomes zero |

The instant sign test cannot distinguish wheel inertia from a real human below 320 counts. The guard is
therefore intentionally limited to near-saturated LKAS. A stronger human input preserves the lane, and
openpilot's own driver-override behavior remains untouched.

Removing an opposing term can increase the aggregate magnitude toward the LKAS direction. V39 retains
the first governor, gp-0x6acc sanitize, soft-EME state machines, second governor, and final clamp, but the
5120 boost floor is not a static proof against the full 7322 assist-inclusive envelope. V38 is fault-free
in observed driving; V39 remains an on-car experiment rather than a proof of every combination.

## Code patch

Hook:

```text
0x3ac78  old 24 4f 30 94  ld.h -0x6bd0[gp],r9
         new 88 07 bc 9e  jr 0x000c4b34
```

Cave `0xc4b34..0xc4b5f`, independently decoded in Ghidra from the final plain-image hash:

```text
0xc4b34  ld.hu  -0x6a62[gp],r6
0xc4b38  ld.hu   0x7312[tp],r8
0xc4b3c  cmp     r8,r6
0xc4b3e  bnc     0xc4b58          ; driver >=320 or sentinel: bypass
0xc4b40  mov     r7,r6
0xc4b42  cmp     r0,r6
0xc4b44  bge     0xc4b48
0xc4b46  subr    r0,r6            ; abs(LKAS)
0xc4b48  addi   -0x600,r6,r0
0xc4b4c  blt     0xc4b58          ; abs(LKAS)<1536: bypass
0xc4b4e  mov     r24,r6
0xc4b50  mulh    r7,r6            ; signed 16x16 product
0xc4b52  cmp     r0,r6
0xc4b54  bge     0xc4b58          ; zero/same sign: bypass
0xc4b56  mov     r0,r24
0xc4b58  ld.h   -0x6bd0[gp],r9    ; displaced instruction
0xc4b5c  jr      0x0003ac7c
```

Contiguous cave bytes:

```text
e4379f95e5471373e831d90d0730e031ae058031060600fa
e6051830e730e031ae0500c0244f3094b7072061
```

`r6` and `r8` are scratch and are overwritten before their first original uses. `r7`, `r9`, `r16`,
`r22`, `r23`, `r26`, `r28`, `gp`, `tp`, `lp`, and the stack are preserved. The modified `r24` feeds both
its live add at `0x3acca` and its later diagnostic/shadow store, which keeps those paths coherent.

## Verification

- V39-vs-V38 is exactly 52 bytes in three runs:
  - `0x3ac78..0x3ac7b`: 4-byte hook.
  - `0xc4b34..0xc4b5f`: 44-byte cave.
  - `0xc4ffc..0xc4fff`: main-block CRC.
- Main CRC: `0xCC2134EF -> 0xEA1E7121`.
- A strict chain validator requires the C6000 bridge, exactly 49 blocks, region-start termination, and a
  matching CRC at every block on the baseline, plain output, and decoded RWD readback.
- RWD decodes byte-for-byte to `../accord-firmware/analysis-2020accord/_v39_plain_image.bin[0x13000:0x100000]`.
- V38 source RWD hash, x31 checksum, key, six headers, block map, decoded payload, and plain-image hash
  are pinned before patching. V39 RWD/plain hashes are deterministic assertions.
- Every V38 calibration and all non-main CRC blocks are byte-identical.
- Final V39 hash matches the independently Ghidra-disassembled temporary image hash.
- Artifacts are written through temporary files and atomically replaced.
- Model self-checks cover the 1535/1536 and 319/320 boundaries, invalid sentinel, both sign directions,
  same-sign/zero/reduced-mode bypass, directional governor slew, Q15 integrator units, and split shaper paths.
- Hook/cave timing and worst-case execution time were not measured.

## Golden model update

`analysis-2020accord/eps_lkas_chain_model.py` is the canonical executable source of truth. This session
updated it with:

- V38's shipped 16384 setpoint limit, which the previous `for_build("V38")` accidentally omitted.
- Exact inline Sensor-B torque-rate A/B calculations and all A160 Q10 table records.
- Correct `gp-0x6b86` validity polarity.
- Exact full aggregator sum order and range gates.
- Exact A160 Q13 motor-rate governor table and away-from-zero-only first-governor slew.
- Exact `gp-0x6acc` +/-8192 preprocessing and signed-Q15 `gp-0x3570` integrator update/authority units.
- Split shaper topology: `gp-0x6acc` drives the integrator, while
  `range_gate(gp-0x6afe)+r20 -> second governor -> +/-8192 -> gp-0x6b98` drives final output.
- SM3's saturation dwell and V38/V39's `tp+0x74cc==3` inhibition of the modeled SM2 entry.
- V39's narrow `r24` guard and executable boundary checks.

Unknown assist-lane magnitudes, governor normalization/budget, bound-arm producers, `r20` blend inputs,
and full SM2 recovery remain explicit replay inputs or documented abstractions rather than fabricated formulas.

## Road-test interpretation

V39 changes only one hypothesized feedback term, so the result is discriminating:

- More authority or less oscillatory cancellation on hard turns supports the Sensor-B torque-rate assist
  hypothesis.
- Little or no change is ambiguous without guard-fired telemetry: the guard may not have become eligible,
  or the unchanged motor-rate governor, inline lane A, or another assist lane may dominate.
- New overshoot or reduced damping means `r24` was serving an important stabilizing role even in this
  narrow regime; return to V38.

The best future RAM capture is `gp-0x4f62`, `gp-0x6b4c`, `r24` (or its shadow), `gp-0x6b94`,
`gp-0x4f64`, `gp-0x6ace`, `gp-0x6acc`, and `gp-0x6b98` across the same hard-turn maneuver.
