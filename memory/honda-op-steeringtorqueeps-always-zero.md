---
name: honda-op-steeringtorqueeps-always-zero
description: "openpilot's carState.steeringTorqueEps is 0 on the Accord because Honda carState never assigns it — NOT because the EPS sends zero. 🛑 CORRECTED 2026-08-08: raw 0x1AB MOTOR_TORQUE genuinely VARIES on the wire, so those bits are FORBIDDEN as a telemetry channel; 'reads 0' is about openpilot's decoded value being SMALL, not about the bits being unwritten."
metadata:
  type: reference
---

> 🛑 **CORRECTED 2026-08-08 — DO NOT READ THIS AS "THE 427 BITS ARE FREE".**
> The recollection that *"a steering torque value reads 0"* is about **openpilot's decoded
> `steeringTorqueEps` being SMALL** — the V81 handoff uses it as a **ring detector at magnitudes < 15** —
> **not** about the underlying `0x1AB` bits being unwritten.
> ⇒ **Raw `0x1AB` `MOTOR_TORQUE` VARIES on the wire, and is FORBIDDEN as a piggyback channel.**
> Overwriting it would destroy a live signal *and* a working detector. The 3 genuinely spare `0x1AB` bits
> are `byte0[6:5]` and `byte2[7]` — those and only those. See
> [[accord-can-telemetry-surface-census-1p66m-frames]] and
> [[accord-can-tx-gateway-whitelist-and-20-free-bits]].
> ⊕ The wider rule the same census produced: **an empirical zero is not proof a bit is free.**
> `0x18F byte5[4]` read flat zero on 28 of 30 routes and is a **live** `STEER_STATUS`→7 indicator.

**Observed by operator (2026-07-13) + verified:** `carState.steeringTorqueEps` (the `str_torque_eps`
column in `rlog-tools/extract_eps_telemetry.py`) reads **0 for the entire drive** in the Accord rlogs.

**Root cause — an openpilot omission, not a firmware/EPS behaviour:**
- The extractor sources it from `cs.steeringTorqueEps` (`rlog-tools/extract_eps_telemetry.py:86`).
- Openpilot's Honda carState **never assigns `steeringTorqueEps`** — a grep of `opendbc/car/honda/`
  (carstate / carcontroller / hondacan / interface / radar_interface) finds **zero writes**, so the
  cereal field stays at its default `0.0`.
- The 2026-07-13 OP-consumption audit confirmed **427 / `0x1AB` `STEER_MOTOR_TORQUE` is never registered
  by the Honda CANParser** (empty message list; lazy registration never triggers) — so it is not in
  `message_states` and its COUNTER/CHECKSUM are not checked either.
- The **firmware DOES send a real value**: builder `FUN_00055d80` packs a 10-bit clamped motor torque
  (from `gp-0x6c18` via `FUN_00049a5a` → … → `FUN_00021864`) into 427 `byte0[1:0]` + `byte1`.
  openpilot simply never decodes it.

**How to apply:**
- Do **not** treat `steeringTorqueEps` / `str_torque_eps` as a *delivered EPS motor torque* signal — the
  cereal field is flat 0 and carries no information on this platform.
- This **corrects** the 2026-07-12 handoff wording *"delivered torque → 0 at the cut"*: that observation
  came from `STEER_STATUS = NO_TORQUE_ALERT_2` and `STEER_CONTROL_ACTIVE → 0` (CAN 399), not from 427.
- **(2026-07-13, routes 77/79)** raw-decoding 427 does not give a usable *delivered-torque* signal
  either: raw `MOTOR_TORQUE` is **small** — 0 for entire segments (route 77 seg2 = 0 in all 3,000 frames;
  whole route max 128, mean 1.4), topping ~553 on route 79 — and it never rails or collapses
  distinctively at the gentle-EME cuts. `OUTPUT_DISABLED` (427 `byte2` bit6) never fires at any cut.
  ⇒ `gp-0x6c18` is **not** the LKAS delivered torque; do not use raw 427 as a **cut anchor**.
  🛑 **"Small and not a cut anchor" ≠ "constant zero and therefore free."** See the banner.
- The internal deliver flag `gp-0x6809` (V31P `DELIVER_CUT` bit) is also broken — see
  [[eps-deliver-cut-gp6809-broken]]. For the gentle-EME cut, anchor on raw CAN 399
  `STEER_STATUS = no_torque_alert_2`. The true delivered LKAS-command global is **`gp-0x6b98`**
  (`0xFEDF1468`, shaper `FUN_00042af8`), not 427's source.

Related: [[gentle-eme-fires-on-saturated-lkas-command]] · [[eps-deliver-cut-gp6809-broken]] ·
[[accord-can-telemetry-surface-census-1p66m-frames]]
