---
name: reference_accord_openpilot_dbc_repoint_clearance_2026-08-11
description: Read-only SSH check of the comma device's actual opendbc/carstate.py/safety C code, run against the DBC this car's platform config really maps to (honda_civic_hatchback_ex_2017_can_generated.dbc, via CAR.HONDA_ACCORD in values.py, NOT an Accord-named DBC). Settles which multi-bit fields on 0x14A/0x18F/0x1AB are safe to repoint for telemetry vs actively used by openpilot.
metadata:
  type: reference
---

# openpilot DBC/carstate clearance for CAN-TX telemetry repointing (2026-08-11)

Method: `ssh comma "..."` (read-only, no writes — per standing operator instruction that openpilot is a
measurement instrument only). `find /data/openpilot -iname '*honda*.dbc'` then matched the ACTUAL DBC
via `opendbc/car/honda/values.py`'s `CAR.HONDA_ACCORD = HondaBoschPlatformConfig(..., {Bus.pt:
'honda_civic_hatchback_ex_2017_can_generated'}, ...)` — **this platform's DBC is Civic-named, not
Accord-named; don't guess the filename from the car's own name.**

## Per-signal clearance, from the DBC + `grep -rn` across `car/honda/` and `safety/`

| signal | frame.bytes | `carstate.py` use | verdict |
|---|---|---|---|
| `STEER_ANGLE` | `0x14A`(330) byte0-1 | `ret.steeringAngleDeg` | **actively used — NEVER repoint** |
| `STEER_ANGLE_RATE` (330's copy) | `0x14A` byte2-3 | `ret.steeringRateDeg` | **actively used — NEVER repoint** |
| `STEER_TORQUE_SENSOR` | `0x18F`(399) byte0-1 | `ret.steeringTorque` | **actively used, likely safety-adjacent (driver-override signal) — NEVER repoint** |
| `STEER_STATUS` | `0x18F` byte4[7:4] | decoded fault string | Honda-populated, not a candidate anyway |
| **`STEER_WHEEL_ANGLE`** | `0x14A` byte5-6 | **zero refs in `car/honda/` or `safety/`** | **DBC-defined but code-unused — safe 2nd 16-bit channel** |
| **`STEER_ANGLE_RATE` (399's own copy)** | `0x18F` byte2-3 | **zero refs anywhere** | **DBC-defined but code-unused — safe 3rd 16-bit channel** |
| `STEER_CONFIG_INDEX` | `0x18F` byte5[3:0] | zero refs | resolves the earlier "mask-edit, elevated risk" framing — same unused tier |
| `STEER_CONTROL_ACTIVE`, `STEER_SENSOR_STATUS_1/2/3`, `MOTOR_TORQUE`, `OUTPUT_DISABLED`, `CONFIG_VALID` | various | zero refs | consistent with the existing free-bit map, no surprises |

**All previously-identified free bits** (`0x14A` byte7[7:6]; `0x18F` byte4[2:0]/byte5[7:6]/byte6[6];
`0x1AB` byte0[6:5]/byte2[7]) **have zero overlapping DBC signal** — clean on both the Honda-firmware
side and the openpilot-DBC side.

## Confidence tiers, not a binary

1. **Never registered by the CANParser at all** — `0x1AB`/427's `MOTOR_TORQUE`. Strongest clearance;
   openpilot's Honda code doesn't even subscribe to the message.
2. **DBC-defined, zero references in `car/honda/` or `safety/`** — `STEER_WHEEL_ANGLE`, 399's own
   `STEER_ANGLE_RATE`, `STEER_CONFIG_INDEX`. One tier weaker — the signal IS parseable and named, just
   not currently wired to anything; a future openpilot update could start reading it. Still cleared for
   use, with that caveat stated.
3. **Actively assigned into `ret.*`** — `STEER_ANGLE`, `STEER_ANGLE_RATE`(330), `STEER_TORQUE_SENSOR`.
   Never repoint.

## Safety layer

`opendbc/safety/modes/honda.h` references neither `0x14A`/330 nor `0x18F`/399 at all — no panda-level
safety check depends on any byte in either frame. Checksum: the CANParser validates generally (an
explicit `ignore_checksum=True` opt-out exists for a different message ID, confirming validation is
otherwise on), but the EPS's own checksum call runs after any spare-bit write and stays self-consistent
— the same mechanism 10+ flights (V31P/V49P/V90) have already proven safe on-car.

## Reproducibility

```bash
ssh comma "find /data/openpilot -iname '*honda*.dbc'"                          # locate DBCs
ssh comma "grep -n 'ACCORD' /data/openpilot/opendbc_repo/opendbc/car/honda/values.py"  # find the platform->DBC mapping
ssh comma "grep -n 'BO_ 399 \|BO_ 330 \|BO_ 427 ' <the matched .dbc>"           # message defs
ssh comma "grep -n '<SIGNAL_NAME>' /data/openpilot/opendbc_repo/opendbc/car/honda/carstate.py"
ssh comma "grep -rn '<SIGNAL_NAME>' /data/openpilot/opendbc_repo/opendbc/car/honda/ /data/openpilot/opendbc_repo/opendbc/safety/"
```

Related: `docs/SPEC-2026-08-11-telemetry-budget.md` (T1/T2/T3, this finding folded in), the CAN-TX
free-bit census memories (`reference_accord_can_tx_399_427_bitmap.md`,
`reference-accord-can-tx-frame-0x14a-bytemap.md`, `reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget.md`)
which this extends to the openpilot side rather than just the firmware side.
