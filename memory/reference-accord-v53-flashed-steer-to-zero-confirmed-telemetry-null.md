---
name: reference-accord-v53-flashed-steer-to-zero-confirmed-telemetry-null
description: V53 FLASHED 2026-07-27 — steer-to-zero (0xC62EA 320→0) CONFIRMED working on-car from raw CAN 399; the four-frame telemetry 0x6A0-0x6A3 was STILL absent, and that null is UNINTERPRETABLE because 6 stock EPS broadcast IDs are equally absent at the comma tap.
metadata:
  type: reference
---

**V53 is the image on the car as of 2026-07-27.** V38 cal + the FOURFRAME2 telemetry cave +
`0xC62EA` 320→0. Fault-free, drives normally.

## ✅ Steer-to-zero works — measured, not reported

Route `75604b0a432fdc89_0000001a` segment 0, 58 s, 301,824 CAN frames. Decoded from **raw CAN 399**
(`STEER_STATUS = (byte4>>4)&0xF`, `STEER_CONTROL_ACTIVE = (byte4>>3)&1`), independently of `carState`:

```
STEER_STATUS == 0 in 5,995 / 5,995 frames     -- ST=3 never fires, at any speed
STEER_CONTROL_ACTIVE == 1 in 226 frames below 5 km/h
  with openpilot TORQUE_REQUEST=1, and |STEER_TORQUE| > 50 in 224 of them
```

On V38 that low-speed cell is **identically empty** — ST=3 *is* the sub-5 km/h gate. This is the first
time the golden model predicted an on-car state-machine change in advance and was confirmed.
⇒ an rlog **can** now identify V53+ behaviourally (ST=3 never firing), even though the version string
cannot. See [[accord-low-speed-lockout-window-c62ea]].

## 🛑 The telemetry null is NOT evidence the cave failed

**Zero** frames of `0x6A0`-`0x6A3` on buses 0/1/2/128/129. But in the *same* log:

| ID | status |
|---|---|
| `0x14A`, `0x18F`, `0x1AB` — the three openpilot's DBC knows | present, 97.3 / 97.4 / 48.7 Hz |
| `0x19F`, `0x32E`, `0x64D`, `0x660`, `0x722`, `0x723` — **stock firmware broadcasts** | **absent** |
| `0x6A0`-`0x6A3` — FOURFRAME2 | absent |

And **non-DBC IDs are logged**: `0x669`, `0x750` (50 Hz), `0x674` all appear and are in **no** Honda DBC.
The `can` service is raw pandad frames written before any DBC exists in the pipeline. So "openpilot
didn't know the ID" is **excluded**; the frames are not arriving.

⇒ The STRB=0x01 fix ([[reference-accord-fourframe-strb-ssam-defect]]) is neither confirmed nor refuted.
**A new-mailbox channel cannot deliver a measurement on this car.** Do not build a third one — see
[[reference-accord-piggyback-channel-audit-dbc-panda]] for the channel that does work.

⚠ V53 does **not** carry the V42 ratchet fix (`0x454FE` stock `0x65BA`).
⚠ What V53 did to the **vibration** is UNANALYSED — route 1a is one 58 s segment and the newly-populated
engaged-at-low-speed cell has not been examined for 21 Hz content. That analysis is free and unclaimed.
