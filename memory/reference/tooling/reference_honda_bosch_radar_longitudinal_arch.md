---
name: reference-honda-bosch-radar-longitudinal-arch
description: "Civic Bosch (2019-21) + Accord 2018-22 are Bosch-WITH-radar, NOT radarless (only Civic 2022+/HR-V 3G/City 7G are BOSCH_RADARLESS). openpilot sets radarUnavailable=True for ALL Honda Bosch so it never reads the stock radar's points. openpilotLongitudinalControl is gated behind alpha_long; default OFF = stock ACC drives long (pcmCruise). Enabling OP-long on a radar-equipped Bosch DISABLES the stock radar via UDS (disable_ecu 0x18DAB0F1) + tester-present keepalive, which DISABLES factory AEB. So feeding an addon radar into OP-long = replacing the stock AEB sensing path. CAN layout: bus0=ACC-CAN radar side, bus1=F-CAN B powertrain, bus2=ACC-CAN camera side, bus3=OBDII. Source-verified (opendbc Python); firmware-level AEB-coexistence is an OPEN question, not a proven impossibility."
metadata:
  type: reference
---

# Honda Bosch radar + longitudinal architecture (openpilot side)

**Established 2026-05-28** (code-first audit of `analysis-2020accord/reference/opendbc/honda/` for the addon-radar spec). Corrects an earlier research-agent mislabel that called these cars "radarless."

## Platform identity — these cars have a STOCK radar
- `HONDA_CIVIC_BOSCH` (Civic 2019-21, Hatch 2017-21) and `HONDA_ACCORD` (2018-22) are `HondaBoschPlatformConfig` **without** the `BOSCH_RADARLESS` flag (`values.py:178-187`, `:161-170`). They run a stock Bosch front radar (part `36802-TBA-*` / `36802-TVA-*` in the calib DB).
- Only `HONDA_CIVIC_2022` (2022+), `HONDA_HRV_3G`, `HONDA_CITY_7G` carry `BOSCH_RADARLESS` (`values.py:204,230,236`). Don't conflate.

## openpilot never reads the stock radar
- `ret.radarUnavailable = True` is set for **all** Honda Bosch (`interface.py:47`). The honda `RadarInterface.update()` then just sleeps 0.05s and returns no points (`radar_interface.py:30-34`). So discrete radar leads are unavailable on every Bosch Honda regardless of the radarless flag — registering a radar DBC is NOT enough to get points; `radarUnavailable` must be overridden or `RadarInterface` replaced.

## Longitudinal is gated behind alpha-long, and enabling it kills stock AEB
- `ret.alphaLongitudinalAvailable = candidate not in HONDA_BOSCH_CANFD`; `ret.openpilotLongitudinalControl = alpha_long and (not CANFD)`; `ret.pcmCruise = not openpilotLongitudinalControl` (`interface.py:52-54`). Default (alpha_long off) = **stock ACC drives longitudinal**; injected radar leads reach the actuators ONLY with alpha-long ON.
- Turning OP-long ON for a radar-equipped Bosch car **disables the stock radar ECU** via UDS communication-control `disable_ecu(... addr=0x18DAB0F1 ...)` (`interface.py:245-251`) and keeps it disabled with a tester-present every 10 frames (`carcontroller.py:150-152`). Code comment is explicit: *"WARNING: THIS DISABLES AEB! If Bosch radarless, this blocks ACC messages from the camera"* (`interface.py:48-50`).
- **Implication:** feeding an addon radar into OP-long replaces the factory AEB sensing path → addon-radar lead quality becomes safety-critical, not a nice-to-have. This raises the live-test gate bar specifically.

## CAN bus layout + actuation path
- Bus map (`hondacan.py:6-10`): `0 = ACC-CAN radar side`, `1 = F-CAN B powertrain`, `2 = ACC-CAN camera side`, `3 = F-CAN A OBDII`. For Bosch-with-radar (`HONDA_BOSCH - RADARLESS - CANFD`): `pt=bus1`, `radar=bus0`; LKAS routes direct to powertrain when OP-long (radar relay opened) else through the radar (`hondacan.py:19-25`). An addon radar would naturally join **bus 0** (radar side), which is freed when the stock radar is UDS-disabled.
- Under OP-long, `create_acc_commands` sends `ACC_CONTROL` (`ACCEL_COMMAND` + `GAS_COMMAND` via `BOSCH_GAS_LOOKUP_BP/V`) on `CAN.pt`/bus1 (`hondacan.py:73-114`); the engine/VSA actuate it (the black-box plant — see [[reference-longitudinal-understanding-asymmetry]]). `compute_gb_honda_bosch` returns 0,0/unused (`carcontroller.py:14-16`) — Bosch sends accel directly, not gas/brake fractions. `create_radar_hud` (CMBS_OFF) + `create_legacy_brake_command` are sent under OP-long to tell the car the radar/CMBS is off (`carcontroller.py:233-236`).

## The open door (don't flatten)
All of the above is openpilot's **Python default behavior**. Whether stock AEB can be kept alive while an addon radar feeds OP — or whether the stock radar's own object data can be read directly — is an **open firmware-level question** (Ghidra on `36802` radar fw). "OP disables it" ≠ "it physically cannot coexist." Alt architectures to keep on the table: (a) addon radar as sensor/data-only with stock ACC+AEB retained (no OP-long), (b) firmware coexistence path.

## How to keep AEB (MVL, 2026-05-07) — gateway-intercept + forward-AEB ★
**This answers the "open door" above — at the CAN/harness layer, not the firmware layer.** Per MVL (the Honda Bosch openpilot dev): on Bosch cars **the radar itself commands gas/brake** (it is the ACC controller), in **parallel with the camera** — so you **cannot intercept its commands at the camera harness** (where the comma harness normally sits; this is why stock OP-long just UDS-disables the radar and kills AEB). **Solution: move the comma harness to the GATEWAY (behind the dash)**, where you CAN intercept the radar→car commands — **forward the AEB commands, intercept/override the normal gas/brake.** "That is what Nidec does."
- ⇒ Keeping factory AEB is a **harness-placement + CAN-interception** problem, NOT a radar-firmware-mod problem. The Ghidra R3 "find the firmware inhibit gate" framing was the WRONG LAYER — off the critical path.
- ⇒ No addon radar and no radar-disable needed: the stock radar keeps doing AEB; you intercept its normal gas/brake at the gateway.
- Sniff-confirmed: the radar's gas/brake command is **CAN `0x1DF` (ACC_CONTROL) on bus 1 (powertrain)**, payload `8ad0..`+4-bit counter. That's the message a gateway-intercept fork overrides; the AEB/CMBS message (~`0x370`, see [[reference-36802-radar-can-protocol]]) is the one it forwards.
- New critical path for OP-long + keep-AEB: **gateway harness location → fork that forwards AEB + overrides `0x1DF`** (Nidec pattern). Object data (`0x400`/`0x280-0x287`) feeds leads/UI but is not the control mechanism.

## CORRECTION (2026-05-28) — AEB shares 0x1DF; no separate 0x370; intercept = bit-mux
MSG_TAXONOMY + OP_LONGCONTROL agents (cross-checked vs live opendbc + the panda safety source) correct the gateway section above: on Bosch, **AEB and normal ACC braking are the SAME message `0x1DF`** — `AEB_STATUS`@33, `AEB_PREPARE`@43, `AEB_BRAKING`@47, beside `ACCEL_COMMAND`@31/`GAS_COMMAND`/`BRAKE_REQUEST`. The firmware swarm's `~0x370 ACC_CMBS_PT` was a **FALSE POSITIVE** (opendbc has no msg there; `0x1FA`=LEGACY_BRAKE, `0x374`=STALK_STATUS). ⇒ the gateway fork does NOT "forward msg X / override msg Y" — it **bit-muxes `0x1DF`**: yield to the radar's AEB_* bits, override ACCEL/GAS on normal frames, recompute the 4-bit checksum. Reference = Nidec's **panda-safety 3-hook pattern** (`opendbc/safety/modes/honda.h`: rx-latch stock AEB, tx-mute OP brake, fwd-unblock) adapted to one shared message; also DROP stock OP-Bosch's radar-UDS-disable (`0x18DAB0F1`) + tester-present (that is what kills AEB today). OPEN: whether a dedicated factory-AEB frame exists separately is unconfirmed — needs a controlled AEB/closing-event sniff (R0 caught no braking event).

## OPT-A design status (2026-05-28, 3-agent converged) — concrete + first-on-Bosch
Fork base = **MVL's `boschc-long`** (`mvl-boston` / `fongy604/mvl`). Copy Nidec's `honda_fwd_brake` 3-hook safety arbiter (`opendbc/safety/modes/honda.h`); **bit-mux `0x1DF`**; relocate harness camera→gateway (= the gauge **cluster**; ACC-CAN at radar conn **A74 pin3 Pink / pin4 Blue**); drop the stock radar-UDS-disable; invert default → AEB-on. **No public Bosch forward-AEB precedent — we'd be first.** The ONE remaining RE unknown = exact `0x1DF` AEB-bit behavior (firmware decompile is blocked by the AUTOSAR RTOS dispatch) → settled by a controlled AEB/closing-event sniff. Full consolidation: `radar-re/gateway/HORDE_SYNTHESIS.md`.

## Cross-links
- [[reference-longitudinal-understanding-asymmetry]] — the car-side accel→throttle/brake black box this rides on
- [[reference-civic-steer-motor-torque-can427]] — sibling "signal openpilot doesn't read" (carstate omission)
- [[reference-operator-flash-hardware-topology]] — red-panda harness reaches these buses
