# V298 fork config (drive 1, the angle loop)

**Fork:** `raayyymond-StarPilot/StarPilot` @ `Dom`, local commits **`51c199f28`** (the angle interface) and
**`38cff0247`** (lagd: no lag seed across a steer-control-type change), on top of `20d24ab79`. **Not pushed.**

| file | what |
|---|---|
| `toggle-config_V298_angle_loop.json` | **restore this for drive 1.** V295 r2's 26 keys unchanged + `AccordEpsAngleLoop` true + `UseAutoSteerDelay` true |
| `toggle-config_V298_angle_loop_REVERT_to_V295_r2.json` | the revert: V295 r2 + `AccordEpsAngleLoop` false + `UseAutoSteerDelay` true |
| `*.decoded.json` | readable copies |
| `write_v298_config.py` | the writer (kit codec, positive control, fork codec, key check against the fork's `params_keys.h`) |

## Order
1. Pull `Dom` on the device, then **Rebuild Params**. Without it Galaxy skips the new key and the switch reads off.
2. Flash V298 (the operator names the file and the bus).
3. **Reboot** (the switch and the EPS fwVersion are read at fingerprinting; `CarParamsCache` clears on manager start).
4. Restore `toggle-config_V298_angle_loop.json` parked, then reboot again.
5. Check before driving: `carParams.steerControlType` = angle, carFw EPS `39990-TVA,A16A`, `AccordEpsAngleLoop` = 1.

## What the switch does (EVIDENCE: the fork tests, 42 + 4 new, 16/16 mutants killed)
- Angle mode only when the EPS reads `A16A` **and** the switch is on. `A16A` with the switch off (or unknown):
  a permanent steer fault, because that EPS ignores torque frames. Any other EPS: the torque path, byte-identical
  to `20d24ab79` on 800 recorded frames.
- 0xE4: `raw = round(−10·deg)`, ±4000; byte 2 bits 3:2 = 2 on every frame. Active: the limited setpoint, request 1.
  Lateral off but allowed: the measured angle, request 0. Not allowed: 0.
- Limits: 120 °/s or the 3.6 m/s³ jerk limit; 400°; error clip to the measured angle 17/15.5/19.5/17/8.5/4.5° at
  3.1/8/10/11.75/17.5/26.9 m/s. Hand torque > 600 (off < 500): the setpoint follows the wheel.
- **No fork angle integral** (P4): `LatControlAngle` is pure feed-forward, and the tests hold a constant setpoint
  under a constant error.

## BELIEF, not measured
- The error-clip values and `steerActuatorDelay` 0.15 s come from the V298 gain table and the V294 plant model.
- The pre-V298 `UseAutoSteerDelay` was true (the 2026-09-23 handoff). The revert restores true.
- In angle mode the `SteerRatio` level scales the setpoint directly: a 3 % level error is a 3 % curvature error
  the EPS will not correct.
