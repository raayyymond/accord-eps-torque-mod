---
name: reference-accord-piggyback-channel-audit-dbc-panda
description: Full audit of the three whitelisted EPS frames as telemetry carriers — exact free-bit budget per byte from the Honda DBC, the panda RX-check list, and the checksum constraint. 0x14A byte4 bits 7:3 is the only channel that is both proven-to-cross and has a located pre-checksum hook.
metadata:
  type: reference
---

Audited 2026-07-27 against the StarPilot/sunnypilot fork on disk, not from memory.

## Free-bit budget — "constant on the wire" is NOT "free"

| byte | DBC content | openpilot reads? | genuinely free |
|---|---|---|---|
| `0x14A` byte4 | bits 2:0 = `STEER_SENSOR_STATUS_1/2/3` (**live in firmware**, `gp-0x679a/9b/99`) | **no** — carstate takes only `STEER_ANGLE`, `STEER_ANGLE_RATE` (bytes 0-3) | **5 bits** @100 Hz |
| `0x18F` byte5 | bits 3:0 = `STEER_CONFIG_INDEX`; **bits 5:4 LIVE** (`gp-0x6880 & 3`, packer `0x55CAE`-`0x55CC2`) | no — carstate takes `STEER_STATUS` (byte4) + `STEER_TORQUE_SENSOR` (bytes 0-1) | 2 safe (+4 if you take the unread `CONFIG_INDEX` nibble) |
| `0x1AB` byte0 | bit7 `CONFIG_VALID`, bit3 `UNKNOWN_TORQUE_STATE_BIT`, bits 1:0 = `MOTOR_TORQUE[9:8]` | no — 427 never parsed into carState | 4 bits, non-contiguous (6,5,4,2), 48.7 Hz |

⚠ **A DBC-only read of `0x18F` byte5 says "bits 7:4 free". That is wrong** — bits 5:4 are written by the
firmware packer. They read constant on route 13 and route 1a only because those bits did not happen to
change. Always check the *firmware* packer as well as the DBC. `0x18F` also has **no located
pre-checksum hook site**, so it is not usable today regardless.

## Panda does not gate any of them

Honda RX check list is `0x1A6`, `0x296`, `0x158`, `0x17C`, `0x326`, `0x1BE`
(`opendbc/safety/modes/honda.h`). None of `0x14A`/`0x18F`/`0x1AB` appears — no counter or quality gating
from that direction.

## 🛑 The checksum is the real constraint

`honda_checksum` lives in `opendbc/can/dbc.py` and the parser **verifies it**. A bad checksum invalidates
the message and drops `can_valid` — that is a **disengage**, not a cosmetic glitch. Any piggyback must be
written **before** the checksum is computed.

`0x55C0E` is inside the 330 content builder immediately before `FUN_00057b24` @`0x55C18`. Confirmed by
disassembly of the built image:

```
00055c0e  jarl   <cave>, lp
00055c12  mov    0x8, r7          <- r7 REASSIGNED: proven dead at the hook, not assumed
00055c14  movea  0x14a, r0, r8    <- the literal 0x14A: this IS the 330 builder
00055c18  jarl   0x00057b24, lp   <- checksum runs after; also clobbers lp, proving lp dead at 0x55c0e
```

The displaced instruction is `movea -0x1518,gp,r6` (the buffer base), so **`gp-0x1514` is arithmetically
buffer+4** — byte 4 of the exact frame being built.

⇒ `0x14A` byte4 bits 7:3 is the channel: 4 successful flashes (V31P/V49P/V50P/V51P), proven to cross the
gateway (5,994 frames @97.3 Hz on route 1a), openpilot-invisible, checksum handled.
Related: [[reference-accord-v53-flashed-steer-to-zero-confirmed-telemetry-null]],
[[accord-can-tx-100hz-base-tick-and-gateway]].
