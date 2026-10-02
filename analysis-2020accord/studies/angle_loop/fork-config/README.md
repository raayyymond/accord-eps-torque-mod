# V298 fork config (drive 1, the angle loop)

**Fork:** `raayyymond-StarPilot/StarPilot` @ `Dom`, local commits **`51c199f28`** (the angle interface),
**`38cff0247`** (lagd: no lag seed across a steer-control-type change) and **`2712e1336`** (the review follow-up:
missing-EPS fault, hold predicate, first-frame and release seeds), on top of `20d24ab79`. **Not pushed.**

| file | sha256 | what |
|---|---|---|
| `toggle-config_V298_angle_loop.json` | `3e6c7b64ea9c8727fd7597720fcf015e3a3c7803fbc5711a1e84c96feb71078d` | **restore this for drive 1.** V295 r2's 26 keys unchanged + `AccordEpsAngleLoop` true + `UseAutoSteerDelay` true + `SteerRatio` 16.84 |
| `toggle-config_V298_angle_loop_REVERT_to_V295_r2.json` | `c6a5a84e02a6f9b1a2226f0d6a8d6eddb6dd31a7e2c152c52e7582f94cb25a9f` | the revert: V295 r2 + `AccordEpsAngleLoop` false + `UseAutoSteerDelay` true + `SteerRatio` 16.84 |
| `toggle-config_V298_angle_loop.decoded.json` | `55fd02615b55040c8224c6af20a4de2be196fc362a9634f02da882a4f3f0b6ef` | readable copy |
| `toggle-config_V298_angle_loop_REVERT_to_V295_r2.decoded.json` | `40918c98c85f6274b6d114df3046bdfc0f83c5838bfa4fa74418d8e2db4fb5e3` | readable copy |
| `write_v298_config.py` | | the writer (kit codec, positive control, fork codec, key check against the fork's `params_keys.h`) |
| `superseded/` | | rev 1 (no `SteerRatio` pin): `5af15f8c…` (drive 1) and `9eb24039…` (revert). **Do not restore.** |

### `SteerRatio` is pinned at 16.84 (rev 2, 2026-10-01)
In angle mode the `SteerRatio` level scales the setpoint directly: a 3 % level error is a 3 % curvature error the EPS
will not correct. So both files now set it.
- **EVIDENCE:** 16.84 is the device's value in route 71b's initData (`00000071--a7b8ba5d9d`, flown 2026-09-29, the
  latest drive). Method: a raw scan of segment 0's decompressed params list. BUILD-LINEAGE PART6 also records "VSR map
  level 16.84" for that drive.
- The operator's 2026-09-10 backup, which the writer uses to check the codec, reads **16.33**. It predates that drive by
  three weeks, so it is stale and is **not** used. If the operator has changed `SteerRatio` since route 71b, regenerate.

## Order
1. Pull `Dom` on the device, then **Rebuild Params**. Without it Galaxy skips the new key, and the switch reads off
   (on the A16A image that is the permanent fault below).
2. Flash V298 (the operator names the file and the bus).
3. **Reboot after the flash.** The switch and the EPS fwVersion are read at fingerprinting, and `CarParamsCache` clears
   on manager start.
4. Restore `toggle-config_V298_angle_loop.json` while parked, then **reboot after the restore**.
5. Check before driving: `carParams.steerControlType` = angle, carFw EPS `39990-TVA,A16A`, `AccordEpsAngleLoop` = 1,
   `SteerRatio` = 16.84, no LKAS fault on the onroad screen.

**Revert:** restore the `REVERT` file, reflash V295, then reboot after both steps. Do them in either order: until both
are done the car shows the fault below, which is safe.

## 🛑 When the switch and the EPS image disagree, openpilot is disabled entirely
The fork raises a **permanent steer fault** (`steerFaultPermanent` → `steerUnavailable`, which is `NO_ENTRY` +
`IMMEDIATE_DISABLE`) in two cases:
- **The A16A (V298) image with the switch off.** This includes the switch reading unknown because Params was not
  rebuilt, and Safe Mode, which forces it off as a managed key. That EPS lane ignores torque frames.
- **The switch on with no EPS fwVersion reading `39990-TVA,A16A`.** That covers V295 or any other image, and an EPS
  missing from carFw (the fw query did not answer). Since `2712e1336`, the switch can never quietly leave lateral
  in torque mode.

While the fault is up, **openpilot will not engage at all, longitudinal included**, not only lateral.
The alert reads **"LKAS Fault: Restart the Car". That text is wrong for this fault: restarting does not clear it,**
because the fault comes from CarParams (switch + fwVersion), which a restart rebuilds the same way.
**Remedy:** make the switch match the image, then reboot.
- A16A image: turn the switch on (run Rebuild Params first if the switch is missing, and turn Safe Mode off).
- Otherwise: reflash V295 with the switch off.
- For the missing-EPS case: reboot so that fingerprinting re-reads the EPS. If it still does not answer, turn the
  switch off.

## What the switch does (EVIDENCE: the fork tests, 50 in `test_honda_accord_angle_loop.py`; every test added in `2712e1336` fails on `51c199f28`)
- Angle mode only when the EPS reads `A16A` **and** the switch is on. Any other EPS with the switch off gives the torque
  path, byte-identical to `20d24ab79` on 800 recorded frames. The mismatched cases are the fault above.
- 0xE4: `raw = round(−10·deg)`, ±4000; byte 2 bits 3:2 = 2 on every frame.
  - Active: the limited setpoint, request 1.
  - Lateral off but allowed (ACC main on **and** (engaged **or** always-on lateral) = the panda's predicate exactly):
    the measured angle, request 0.
  - Not allowed: 0. For example, engaged with main off sends `00 00 08`.
- Limits: 120 °/s or the 3.6 m/s³ jerk limit; 400°; error clip to the measured angle 17/15.5/19.5/17/8.5/4.5° at
  3.1/8/10/11.75/17.5/26.9 m/s.
- The limiter starts from the measured angle on the first frame. So a first active frame cannot step the setpoint
  toward 0°.
- Hand torque > 600 (off < 500): the setpoint follows the wheel plus a 0.06 s lead. On release the limiter restarts
  from the measured angle (the lead is dropped) and slews back to the model's angle.
- **No fork angle integral** (P4): `LatControlAngle` is pure feed-forward, and the tests hold a constant setpoint
  under a constant error.

## Drive-read (integration review note)
**Take θ_sp from the wire:** `sendcan` 0xE4 bytes 0–1, or `carOutput.actuatorsOutput.torqueOutputCan` (the same
field, raw = −10·deg). **Do not use** `actuatorsOutput.steeringAngleDeg`, which is the limiter's output. It is not what
the EPS received: the wire field is rounded to 0.1° and clipped to ±4000, and it is 0 while not allowed. In that
state the float still reads the measured angle.

## BELIEF, not measured
- The error-clip values and `steerActuatorDelay` 0.15 s come from the V298 gain table and the V294 plant model.
- The pre-V298 `UseAutoSteerDelay` was true. The 2026-09-23 handoff says so, and route 71b's initData reads 1. The
  revert restores true.
- That the `SteerRatio` the operator has now is still 16.84 (see above).
