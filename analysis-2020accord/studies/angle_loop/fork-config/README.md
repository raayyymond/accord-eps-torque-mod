# V299 fork config (the angle loop's drive 2)

**Fork:** `raayyymond-StarPilot/StarPilot` @ `Dom`, local commit **`c6452361e43812c7a7931c76dd4e036bbe5a1835`**
on top of `2712e1336`. **Not pushed.** The device can only "pull Dom" after the operator pushes it, or copies it
over.

Commit message: "Accord V299: no fork override (operator ruling), EPS torque bar from 0x1AB, A16 family detection,
AccordAngle* params, status field". Kit brief: `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev2-2026-10-02.md` §2,
as corrected by the two rev-2 re-refutations.

| file | sha256 | what |
|---|---|---|
| `toggle-config_V299-A_relays-bar.json` | `d1aeab7e2abc8e0a5d2f558ebb2b7fb49dd645c44a299c28188489abf81c0cc4` | **Restore this for V299's first drive.** It is the V298 drive-1 config's 29 keys unchanged, plus `AccordAngleBarFromEps` true, `AccordAngleMaxRate` 120.0 and `AccordAngleClipScale` 1.0. MaxRate and ClipScale equal their defaults (= V298), so the only live toggle change is the torque bar. |
| `toggle-config_V299-B_cap250.json` | `ced2a4e28fcc971e41fb986eaba120d9aed39415dfd39ed985acdd37bf0b9098` | 🛑 **OPTIONAL / LATER DOSE. Not for V299's first drive.** Config A with `AccordAngleMaxRate` 250.0 and nothing else changed (the setpoint rate cap goes from 120 to 250 °/s). Fly one dose per drive. Stop it if hands-off 1229-freeze onsets reach ≥ 50 % of turn-ins at ≤ 8 m/s, or if stall-surges per turn double (brief §7, X3). |
| `toggle-config_V299_REVERT_to_V298.json` | `4633091a47d7646d5077a2bbd0a64995508c92a22e36fa73dcb848388b8324fb` | The revert: the V298 drive-1 values, with the three new keys at their V298 defaults (`AccordAngleBarFromEps` false, 120.0, 1.0). **On its own it does not revert anything.** See REVERT below. |
| `toggle-config_V299-A_relays-bar.decoded.json` | `6a2758928887d52390125ea1664ce06b5bb4c83d9d88c6a238532914857ecc12` | Readable copy. |
| `toggle-config_V299-B_cap250.decoded.json` | `f4b34e98811390fba1aa3e9275118c60dc882c0523e6f766afcf797d028d86e4` | Readable copy. Its `_comment` key holds the OPTIONAL / LATER DOSE label; that key is **not** in the encoded file. |
| `toggle-config_V299_REVERT_to_V298.decoded.json` | `647e5022adcce41205911cb75cf04f397ecc39e7b4ec83354cbc93a9ca6a90cb` | Readable copy. |
| `write_v299_config.py` | | The writer. It runs these checks: <br>• the base file is re-hashed (`3e6c7b64…`); <br>• the kit codec is positive-controlled; <br>• the fork codec is read with `git show` at the V299 commit and asserted unchanged since `20d24ab79`; <br>• every key and declaration is checked against `params_keys.h` at the V299 commit; <br>• every file is decoded back from disk by both codecs. |

### Deploy order (V299)
1. **Pull `Dom`** (commit `c6452361…`) on the device, then **Rebuild Params**. Without the rebuild, Galaxy skips the
   three new keys and the fork uses their defaults: the bar stays the V298 bar, which is safe.
2. **Flash V299** (A16B). The operator names the file and the bus, and openpilot is killed first.
3. **Reboot.** The switch and the EPS fwVersion are read at fingerprinting.
4. **Restore `toggle-config_V299-A_relays-bar.json`** while parked.
5. **Reboot.** The params are read once, when the controller is built.
6. Check before driving:
   - carFw EPS `39990-TVA,A16B`;
   - `carParams.steerControlType` = angle, `AccordEpsAngleLoop` = 1, `AccordAngleBarFromEps` = 1, `SteerRatio` = 16.84;
   - `starpilotCarState.accordAngleStatus` is present;
   - the torque bar moves with the EPS's push;
   - no LKAS fault.

**Order matters.** Pull the fork **before** flashing. The old fork (`2712e1336`) matches only `A16A`, so on A16B with
the switch on it raises the permanent fault: safe, but no drive.

### REVERT (to V298)
1. Restore `toggle-config_V299_REVERT_to_V298.json`.
2. **Reflash the re-headered V298 rwd** (`…V298-REHEADERED-FOR-REVERT-FROM-V299-A16B-…rwd`, from the V299 build round,
   brief §11.2).
3. **Check out `Dom` `2712e1336`** on the device. The override removal is code, so no toggle restores V298's O1.
4. **Reboot.**

Until every step is done, the two in-between states are:
- the V299 fork on the V298 image (A16A): steers, as V299 with no override;
- the `2712e1336` fork on A16B: the permanent fault, which is safe.

On `2712e1336` the three new keys are undeclared. Galaxy skips them (BELIEF, as with V298's own key before Rebuild
Params).

### What changed in the fork (EVIDENCE: fork tests at `c6452361…`)
- **No fork override** (operator ruling, 2026-10-02):
  - `angle_override`, `ANGLE_OVERRIDE_ON/OFF/LEAD_S` and the O1 branch are deleted. The setpoint never follows the hand.
  - The limiter restarts from the wheel only on the first frame and on the latActive rising edge.
  - The error clip is the only bound. The EPS fade and its freeze at raw 1229 (wire 1200) are the override.
  - `test_angle_v299.py` replays route 79's limiter inputs (fixture `accord_angle_r79_v299.npz`) through the new
    `_update_angle` and through the vendored `2712e1336` `_update_angle` with `ANGLE_OVERRIDE_ON = OFF = inf`. Raw
    and setpoint are **identical on 66,775/66,775 frames**.
  - At the defaults against V298 as flown, the only difference is **3,245 latActive frames outside O1 (5.72 %)**. All
    of them sit in the convergence windows after V298's 415 O1 releases, where V298 restarted its limiter from the
    wheel.
- **Firmware family:** `is_accord_eps_angle_loop_fw` strips the NULs, then matches `39990-TVA,A16` + one capital
  letter. A16A and A16B are accepted; A160 (V294/V295) is not.
- **0x1AB torque bar:**
  - Listed (nan, `ignore_checksum`, `ignore_counter`) only on the angle firmware.
  - Checksum-checked in carstate, then `steeringTorqueEps = −8·s10`. It reads 0 once the last good frame is more than
    100 ms old on the parser's clock.
  - The opendbc `honda_checksum` validates **61,113/61,113** route-79 0x1AB frames.
  - The bar is `clip(−steeringTorqueEps/2461)`. Its sign matches the V298 bar's on 0.854 of 31,987 frames.
- **Params**, each read once (unknown, non-finite or unreadable → default, then clamped):
  - `AccordAngleMaxRate` °/s: default 120, range 60–250.
  - `AccordAngleClipScale` (×) the knots ≤ 11.75 m/s: default 1.0, range 1.0–1.6. From 11.75 to 17.5 m/s the clip
    blends 17·s → 8.5°: 13.67° at 14 m/s for s = 1.0, 19.88° for s = 1.6.
  - `AccordAngleBarFromEps`: default false.
- **Status:** `starpilotCarState.accordAngleStatus @31`. 4 = the rate/jerk limit bound the setpoint; 16 = the error
  clip bound it; 256 = 0x1AB stale. `actuatorsOutput.torque` is untouched.

---

# V298 fork config (drive 1, the angle loop) — the record

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
  from the measured angle (the lead is dropped) and slews back to the model's angle. **(V298 only: removed in V299 by
  the operator's 2026-10-02 ruling; see the V299 section above.)**
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
