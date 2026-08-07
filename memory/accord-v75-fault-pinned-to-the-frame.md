---
name: accord-v75-fault-pinned-to-the-frame
description: V75's hard fault located to a single 100 Hz frame on route 5e (t = 284.7947 s, segment 4) with everything latching together. The faulting launch was the MILDEST of four — magnitude and rail contact are NOT the discriminator. A 20.0 Hz oscillation runs in the 300 ms before it.
metadata:
  type: reference
---

# ★★★★★ V75's FAULT IS PINNED TO ONE FRAME — and magnitude is NOT the discriminator

**Route `5e` (`75604b0a432fdc89_0000005e--857d0bd164`), 7 segments, 401.2 s.** The fault is a single
100 Hz frame at **t = 284.7947 s, segment 4**, with everything latching in the same frame:

| signal | before → after |
|---|---|
| bus `STEER_STATUS` (`gp-0x6807`) | 0 → **7** |
| `STEER_CONTROL_ACTIVE` | 1 → 0 |
| `gp-0x6880` | 0 → **1** (0 for the entire prior drive) |
| **`0x1AB` byte0 bit2 — the firmware's own DTC-active flag** | 0 → **1** |
| `0x14A` STEER_ANGLE / ANGLE_RATE / WHEEL_ANGLE | all → **`0x7FFF` sentinel** |
| `STEER_SENSOR_STATUS` | 7 → 4 |

openpilot reacted **+5 ms** later; dash-lamp frames appear on `0x450` / `0x440` at **+0.12 / +0.28 /
+0.52 s**. The `0x7FFF` sentinel and the sensor-status change are **consequences**, not causes — see
[[accord-descriptor-bit13-is-the-fault-fingerprint]].

## ★★ THE FAULTING LAUNCH WAS THE MILDEST OF FOUR

Four engaged stoplight launches exist on the route. The one that faulted was the **least severe** on
every magnitude axis:

- **Launch #2** sat on openpilot's ±4096 rail for **76 %** of its window and drove the damper into a
  **higher bracket** — and did not fault.
- **Launch #4** had **0.00 % rail contact** and the lowest driver torque.

⇒ 🛑 **magnitude and rail contact are NOT the discriminator, and every magnitude-based mechanism is
dead.** This kills the "maximum-demand / minimum-speed corner" sizing that
[[reference-accord-monitor2-corridor-and-the-c64a4-trap]] offered as the plausible route to a trip.

## ★★ The damper never approached its ceiling
The `≥ 448` probe bit fired **0 / 39,961 frames**. Whatever tripped, it was not the damper running out
of headroom.

## ★★ 300 ms pre-fault: a 20.0 Hz oscillation
In the 300 ms before the frame: **1,368 counts p-p driver torque**, **93 counts p-p angle rate**,
dominant line **20.0 Hz on both channels**, and **absent from openpilot's command** (which sits at
3.3 Hz). That is this kit's own ~21 Hz plant mode
([[reference_accord_loop_through_torque_sensor_uncompensated]]), running hard, inside the EPS.

The damper thermometer **stepped up one bracket 20 ms before the fault, then froze for 116 s** — the
freeze being the latched state, not a separate event.

## ★ Post-fault: a MOTOR-OFF LATCH, not a task death or a reset
- **Control task ALIVE** — the probe cave is still executing, **2,165 `gp-0x6ac2` transitions** after the
  fault.
- **CAN alive** — `0x14A` and `0x18F` both at exactly **100.0 Hz**.
- **MOTOR_TORQUE frozen.**
- **Driver effort median rose 12×** (the operator now turning an unassisted rack).

⇒ the assist output was cut and held; the ECU kept running. This is the `FUN_00045608`-class authority
latch ([[accord-fun45608-authority-slots-not-motoroff]]), reached through the DTC-eligibility chain, not
a watchdog reset.

## ✅ 2026-08-07 — THE DAMPER IS ELIMINATED AT THE FRAME, AND THE JERK SIGNATURE FITS `0xC407E`

In the last **5 s** before the trip the damper was **identically zero for 4.98 s** and reached only
level 2 (128–288) **19 ms** before the fault. The car was stationary T−5 → T−1 s then launched
(0 → 7.6 km/h); column rate reversed sign **twice** in the final 150 ms (+55, +31, −38 °/s) and **peak
jerk hit 7,154 °/s² = 4.3× that route's own p99.9 (1,664), and the route maximum.**
⇒ **Exactly what the `0xC407E` = 850 friction-lane mechanism predicts**
([[accord-friction-lane-ceiling-is-the-hard-fault]]) — a rate-family single-frame excursion, not a
magnitude or a rail contact. **V81 restores the 511 interlock**
([[accord-v81-built-c407e511-friction-stock]]).

Related: [[accord-v74-hard-faulted-in-manual-over-a-bump]] ·
[[reference-accord-v75-fault-refutation-ledger]] · [[accord-dtc-read-is-structurally-blind-here]] ·
[[reference-accord-v74-v75-damper-is-a-sampled-relay]] · [[accord-friction-lane-ceiling-is-the-hard-fault]]
