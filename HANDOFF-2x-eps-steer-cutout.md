# Handoff — Honda Accord 2× EPS LKAS torque cut-out investigation

**Date:** 2026-06-29
**Vehicle:** 2020 Honda Accord (`CAR.HONDA_ACCORD`, Bosch, *not* `HONDA_BOSCH_ALT_RADAR`), comma 4
**Modification:** EPS firmware modified to **2× the LKAS torque input**. Works on the **sunnypilot** fork; being debugged on stock **openpilot**.
**Next step (this is where to resume):** re-investigate the **EPS firmware** — see "Next steps" below.

---

## 1. Symptom

On sharp turns that require >1× stock torque **and** when the car hits a bump, LKAS torque cuts out, the wheel returns toward center, and the driver must grab the wheel to continue the turn.

## 2. TL;DR — confirmed root cause

The cut is **EPS-side**, not an openpilot software fault. On a hard/saturated turn the EPS momentarily **stops delivering the torque openpilot is requesting** (it flags the *tolerated* `STEER_STATUS = NO_TORQUE_ALERT_2` and backs off), so the wheel falls back toward center under self-aligning torque while openpilot is still commanding **max**. openpilot never raises a fault and is blind to it.

**Confirmed software support (from sunnypilot):** halve the lateral PID gains for the Accord — `kp 0.6→0.3, ki 0.18→0.09` — leaving `STEER_MAX` at 4096. This cancels the 2× loop gain. The EPS-side root cause is the subject of the next step.

## 3. What was RULED OUT (with evidence)

- **openpilot's `steerFaultTemporary` / `latActive` fault gate.** In both analyzed events, `steerFaultTemporary` had **0 rising edges**, `latActive` stayed **True**, and openpilot kept *sending* full torque (`outTrq = ±1.0`) throughout the cut. So the original code-derived theory (STEER_STATUS fault → `latActive=0` → zeroed command, via `controlsd.py:100` + `hondacan.py:119`) did **not** occur here.
- **panda safety driver-torque limiting.** Honda's `safety/modes/honda.h` steer check only blocks torque when controls aren't allowed; it never calls `steer_torque_cmd_checks`, so the `lateral.h` `driver_limit_check` / `DRIVER_TORQUE_ALLOWANCE` path **does not apply to Honda** at all.
- **A non-tolerated STEER_STATUS code.** Only `NO_TORQUE_ALERT_2` (code 4, the *tolerated* "bump/nudge" code) ever appeared — never `NO_TORQUE_ALERT_1` (2), `FAULT_1` (5), or `TMP_FAULT` (6). So there is nothing to "debounce" in carstate; that block is irrelevant to this failure.

## 4. Evidence — two independent events, identical signature

> **Sign convention (corrected):** on this car, **negative `steeringAngleDeg` and negative openpilot torque = RIGHT turn; positive = LEFT.** In both events `|angle|` *decreases* during the cut = wheel returning toward center.

### Event A — route `75604b0a432fdc89_00000037`, segment 9, ~543.4–544.1 s — **RIGHT turn**, ~14.5 m/s
- Steady right turn held at angle ≈ **−34°**, openpilot **saturated at cmdTrq/outTrq = −1.0**.
- Bump/disturbance + `STEER_STATUS → NO_TORQUE_ALERT_2`.
- Wheel unwound **−34° → −10° (toward center) at up to 130°/s while openpilot still sent −1.0**. Driver torque small during the unwind → not the driver; the EPS went light.
- Recovery: driver takes over, torque sensor spikes to ≈ **−3400**, wheel hauled back to ≈ **−39°** (overshoot).

### Event B — route `75604b0a432fdc89_00000036`, segment 5, ~325.6–326.9 s — **LEFT turn**, ~17 m/s
- Left turn, openpilot ramping into **saturation (cmdTrq/outTrq = +1.0)**.
- Bump (`drvTrq` spike to +1257/−1378) + `STEER_STATUS → NO_TORQUE_ALERT_2`.
- Wheel collapsed **+21° → +4° (toward center) at up to 95°/s while openpilot still sent +1.0**. Driver torque small during the collapse → EPS-side.
- Recovery: torque sensor ramps to ≈ **+3500**, wheel hauled back to ≈ **+37°** (overshoot). Matches "I have to quickly take control to continue the turn."

Note: Event B triggered at a more modest angle but during a **rapid ramp to saturation** — confirming it's the *saturated/high command on the 2× plant + bump*, not extreme angle per se, that trips the EPS.

## 5. Why the 2× firmware causes it

> **Torque-sensor physics (corrected — an earlier draft was wrong here).** `STEER_TORQUE_SENSOR` is the **column torsion-bar** sensor: it measures **driver input torque + road/kickback disturbance**, *not* the LKAS motor's assist torque. The assist motor acts **downstream** of the torsion bar (the Accord uses dual-pinion EPS — motor on a second rack pinion; sensor + torsion bar on the steering-column pinion), so motor/LKAS torque does not register on it. openpilot itself treats this signal as **driver** torque (it's the basis for `steeringPressed`). Therefore a 2× LKAS gain does **not** scale this reading. The ±3000–3500 values seen are driver grip + road kickback — largest during the **recovery/grab** (event A 543.9–544.1, event B 326.2+), not a doubled motor torque.

- **The 2× firmware's mechanism is the control loop, not the torque sensor.** openpilot's Accord lateral PID (`kp=0.6, ki=0.18`, `interface.py`) is tuned for a 1× plant. With 2× actuation gain the **loop gain doubles** → openpilot over-drives and **saturates at max command** — confirmed independently from `sendcan`: `STEER_TORQUE=4096`, `STEER_TORQUE_REQUEST=1` held continuously through the wheel unwind. Zero headroom, and it limit-cycles on disturbance (command thrashing −1.0 → +0.96 in the recovery).
- **The cut itself is the EPS reducing assist on a bump/driver-nudge.** Per openpilot's own carstate comment, `NO_TORQUE_ALERT_2` is "caused by bump or steering nudge from driver" — the EPS detects a torque disturbance and backs off LKAS assist (standard override behavior). Because openpilot was pinned at max with no headroom (the 2× over-gain), that brief assist dip lets the wheel fall back hard instead of being a non-event.
- **Why sunnypilot's fix works:** halving `kp/ki` cancels the 2× loop gain, so openpilot commands moderate, non-saturated torque for the same maneuver — it keeps headroom, doesn't limit-cycle, and a bump-induced assist dip no longer collapses the turn.
- **Open question for the firmware step (§7):** the exact internal trigger for `NO_TORQUE_ALERT_2` / the assist back-off on this modified EPS (driver-torque threshold? road disturbance? a command-vs-response consistency check?) is not yet known.

## 6. sunnypilot comparison (diffed `../sunnypilot/`, opendbc submodule)

The **only** functional steering difference for an EPS-modified Accord:
- `opendbc/sunnypilot/car/honda/values_ext.py`: `HondaFlagsSP.EPS_MODIFIED = 2`, auto-set when the EPS firmware version string contains a `,` (`interface.py`: `if fw.ecu == "eps" and b"," in fw.fwVersion`). Also sets `dashcamOnly = False`.
- `opendbc/car/honda/interface.py` (sunnypilot), `CAR.HONDA_ACCORD` branch:
  ```python
  if ret.flags & HondaFlagsSP.EPS_MODIFIED:
      stock_cp.lateralTuning.pid.kpV, stock_cp.lateralTuning.pid.kiV = [[0.3], [0.09]]
  ```
**Identical between forks** (verified): `STEER_MAX`/`torqueBP`/`torqueV` (still `[[0,4096],[0,4096]]`), `STEER_DELTA_UP/DOWN`, `create_steering_control` (hondacan.py), and the `STEER_STATUS → steerFaultTemporary` block in carstate.py. So sunnypilot does **not** cap torque or change fault handling for the Accord — it *only* halves the PID gains.

## 7. Next steps — re-investigate the EPS firmware

The mitigation in §6 stops *provoking* the EPS, but the cut originates in the EPS's torque back-off. To address root cause:

1. **Identify the back-off / `NO_TORQUE_ALERT_2` trigger** in the firmware: what condition makes the EPS reduce assist mid-command (torsion-bar magnitude threshold? motor current/thermal limit? a torque-sensor-vs-command consistency check?). This is the thing that fires on "saturated 2× command + bump."
2. **Check whether that threshold scales with, or is independent of, the LKAS input gain.** If the mod doubled the input gain but left the back-off threshold at stock, the threshold is now effectively hit at half the intended steering effort — candidate firmware fix is to scale the threshold too.
