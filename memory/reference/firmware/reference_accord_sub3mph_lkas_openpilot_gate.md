---
name: reference-accord-sub3mph-lkas-openpilot-gate
description: "The ~3 mph LKAS cutoff on the Accord is OPENPILOT-side, NOT an EPS firmware pipeline gate. A dedicated firmware trace (2026-07-17) found NO speed threshold anywhere in CAN-decode->arbitration->decider->engage-SM->mixer->shaper. The 3 mph number = openpilot STEER_GLOBAL_MIN_SPEED (3*MPH_TO_MS, values.py:41) AND Accord minSteerSpeed (3*MPH_TO_MS, values.py:163): below max(those), controls runs latActive=False so create_steering_control TXes STEER_REQUEST=0 (openpilot stops commanding). The EPS ALSO locks out near standstill and reports STEER_STATUS=LOW_SPEED_LOCKOUT on CAN 399 (opendbc: 'All Honda EPS cut off slightly above standstill'), treated as expected below min_steer_speed. OPEN: the firmware producer of LOW_SPEED_LOCKOUT is NOT in the LKAS command pipeline (wheel-speed decoder unlocated; KFC_WHEEL_SPEED strings @0xB9BA4 dead-end at a DTC-name table)."
metadata:
  node_type: memory
  type: reference
---

> 🛑 **SUPERSEDED 2026-07-25 — THE CENTRAL CLAIM OF THIS MEMORY IS FALSE.** Read
> [[accord-low-speed-lockout-window-c62ea]] and `docs/handoffs/2026-07/HANDOFF-2026-07-24-low-speed-steer-lockout.md`.
> **(1) openpilot is NOT the operative gate.** `CP.minSteerSpeed = 0.0` for HONDA_ACCORD — verified in
> the pinned repo: `CarSpecs.minSteerSpeed` defaults to `0.0` (`opendbc/car/__init__.py:154`),
> `interfaces.py:140` reads **`CarSpecs`**, and the Accord's `CarSpecs(...)` sets no such kwarg. The
> `min_steer_speed=3.*CV.MPH_TO_MS` cited below at `values.py:163` is a **`HondaCarDocs`** kwarg —
> car-compatibility *website metadata* that nothing reads into `CarParams`. The only OP floor is a
> hardcoded **0.3 m/s (0.67 mph)** in `controlsd.py:178`, bypassable only via `CP.steerAtStandstill`
> (which Honda sets nowhere).
> **(2) The EPS firmware DOES have a real low-speed lockout**, and this memory's "not a firmware
> command-pipeline gate" framing is wrong. It is cal **`0xC62EA` = 320 ≈ 5 km/h**, a two-sided window vs
> voted vehicle speed `gp-0x6a5e` evaluated in `FUN_00028ea6`; failing it writes `STEER_STATUS = 3`,
> which via an **intra-function** `cmp 0x2` @`0x29382` blocks `STEER_CONTROL_ACTIVE` (`gp-0x6806`) and
> the authority ramp (`gp-0x69b0`). Proven on-car by three independent decoders over ~305k CAN-399
> frames. **(3) The "producer of LOW_SPEED_LOCKOUT was not located" open item below is CLOSED.**
> What still stands: the *arbitration/shaper* path itself contains no speed compare — the window sits
> upstream of it, in the same function but before the command math.

Established 2026-07-17 while firmware-verifying `analysis-2020accord/model/eps_lkas_chain_model.py` against 5 operator review comments (see `docs/handoffs/2026-07/HANDOFF-2026-07-17-lkas-model-firmware-verification.md`). A `firmware-codepath-tracer` swarm searched the full LKAS command chain in stock `code.bin` and the local `analysis-2020accord/reference/opendbc/honda`.

**Why LKAS is "ignored" below ~3 mph — two cooperating layers, neither a firmware command-pipeline gate:**

1. **openpilot (the operative 3-mph number, CONFIRMED in-repo).** `CarControllerParams.STEER_GLOBAL_MIN_SPEED = 3 * CV.MPH_TO_MS` (`values.py:41`); the Accord's `minSteerSpeed = 3 * CV.MPH_TO_MS` (`values.py:163`). `carcontroller.py:227` gates the HUD `steering_available` on `vEgo > max(STEER_GLOBAL_MIN_SPEED, minSteerSpeed)`; upstream controls drops `latActive` below that, so `hondacan.create_steering_control(..., latActive=False)` sends STEER_REQUEST=0 — openpilot stops *commanding* steer. `carstate.py:100/104` list `LOW_SPEED_LOCKOUT` among the expected (non-fault) statuses below `min_steer_speed`.

2. **EPS firmware (corroborating, partial).** The EPS itself won't actuate near standstill and reports `STEER_STATUS = LOW_SPEED_LOCKOUT` on CAN 399. opendbc's own comment (`carstate.py:116`): *"All Honda EPS cut off slightly above standstill, some much higher."* So the firmware has a low-speed behavior — but it surfaces as a STATUS report, and the actual command-pipeline (arbitration/decider/mixer/shaper) has **no speed gate** (see [[reference-accord-arbitration-limit-family]] — even the 0xC6534 speed curve is NOT read by arbitration). The producer of `LOW_SPEED_LOCKOUT` lives in the STEER_STATUS producer / a wheel-speed CAN consumer that was **not located** (the `KFC_WHEEL_SPEED` string trail @0xB9BA4 dead-ends at a DTC-name table, not live decoder code).

**Consequence / rule for future sessions:** do NOT hunt the LKAS firmware command chain for a sub-3-mph gate — it isn't there (already ruled out). If a firmware low-speed threshold is ever needed, trace the STEER_STATUS producer and the wheel-speed unpacker, not the arbitration/shaper path. Related: [[honda-op-steeringtorqueeps-always-zero]] (anchor cuts on raw CAN 399 STEER_STATUS), [[gentle-eme-fires-on-saturated-lkas-command]].
