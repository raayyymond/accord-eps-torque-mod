---
name: reference_accord_can427_dbc_confirms_4_spare_bits_and_undefined_neq_unwritten
description: opendbc's BO_ 427 STEER_MOTOR_TORQUE (3 bytes) exactly matches the V282 firmware's own byte0/byte1/byte2 writer census for that CAN buffer (gp-0x13CC/-0x13CB/-0x13CA) -- every DBC signal lands on a bit the firmware writes. byte0 bits 2/5/6 and byte2 bit7 are DBC-undefined AND firmware-unwritten (top-tier spare, V31P standard). byte0 bits 3/4 are DBC-undefined but ARE firmware-written -- proof that DBC-undefined alone does not certify a bit free.
metadata:
  type: reference
---

# CAN 427 (`0x1AB`) DBC cross-check: confirms 4 spare bits, and demonstrates why "DBC-undefined" alone is not enough

2026-09-04, subagent `telem285`, cross-checking a firmware-side writer census
(`reference_accord_can427_frame_byte0_byte2_free_bit_census`, see below / BUILD-LINEAGE for the full
V282 cave writeup) against `opendbc`.

**DBC files** (identical `BO_ 427` definition in both):
`C:\Users\dudei\Desktop\Projects\openpilots\StarPilot\opendbc_repo\opendbc\dbc\honda_accord_2017_can_ext_generated.dbc`
`C:\Users\dudei\Desktop\Projects\openpilots\StarPilot\opendbc_repo\opendbc\dbc\honda_bosch_radarless_generated.dbc`

```
BO_ 427 STEER_MOTOR_TORQUE: 3 EPS
 SG_ CONFIG_VALID    : 7|1@0+   [0|1]    -> byte0 bit7
 SG_ MOTOR_TORQUE    : 1|10@0+  [0|256]  -> byte0 bits[1:0] + all of byte1 (10 bits, Motorola)
 SG_ OUTPUT_DISABLED : 22|1@0+  [0|1]    -> byte2 bit6
 SG_ COUNTER         : 21|2@0+  [0|3]    -> byte2 bits[5:4]
 SG_ CHECKSUM        : 19|4@0+  [0|15]   -> byte2 bits[3:0]
```

## Cross-check: every DBC signal matches a firmware writer exactly

The firmware buffer `gp-0x13CC` (byte0) / `gp-0x13CB` (byte1, inferred) / `gp-0x13CA` (byte2) was
independently traced from `FUN_00055d80` (the 427 packer) and its callee `FUN_00021864` (the generic
10-bit pack helper). Every bit the firmware writes lands on a named DBC signal:

| bit(s) | DBC signal | firmware writer |
|---|---|---|
| byte0[1:0] + byte1 | `MOTOR_TORQUE` | `FUN_00021864` (T field, `sign(T)<<9\|\|T\|>>3`) |
| byte0[7] | `CONFIG_VALID` | `0x55E74`, conditional `ori 0x80` |
| byte2[6] | `OUTPUT_DISABLED` | `0x55DA8`, `r10&1` |
| byte2[5:4] | `COUNTER` | `0x55EEE`, a processed 2-bit value |
| byte2[3:0] | `CHECKSUM` | `0x55F16`, `r10&0xf` nibble |

This is a clean, independent validation of the firmware-side writer census — every physical bit
found occupied maps to a real, named opendbc signal, no unexplained residue.

## The two undocumented-but-live bits, and the lesson

`byte0` bits **3** and **4** are firmware-written (`gp-0x685b`, `gp-0x685a` respectively, both Honda
state cells) but **NOT covered by any DBC signal above.** The DBC's own bit accounting (`CONFIG_VALID`
+ `MOTOR_TORQUE` + the three byte2 signals) leaves byte0 bits 2,3,4,5,6 all nominally "spare" — yet
two of those five are demonstrably live in the firmware.

🛑 **"DBC-undefined" does not imply "firmware-unwritten."** opendbc documents what openpilot's
receivers decode, not what the transmitting ECU writes — an ECU can pack bits for another consumer
on the bus (or a debug/reserved purpose) that the DBC never names. Any bit-repurposing decision on a
Honda CAN frame needs BOTH checks — the firmware-side writer census AND the DBC — matching the V31P
precedent's "3-audit + own-Ghidra" standard, and this frame is proof neither check alone is
sufficient: byte0 bits 3/4 would have passed a DBC-only check and failed on the wire.

## The 4 confirmed-clean bits

Of byte0's five nominally-spare bits (2,3,4,5,6), only **2, 5, 6** are ALSO firmware-unwritten
(bits 3,4 are the counter-example above). Combined with byte2 bit **7** (also DBC-undefined and
firmware-unwritten): **`gp-0x13CC` bits 2/5/6 and `gp-0x13CA` bit 7 — 4 bits total — pass both
checks** and are the top-tier-spare candidates for new telemetry on this frame, without touching
`0x14A` byte4's existing rungs at all. See the V282/V285/V286 telemetry design threads
(`docs/specs/design/V285-TELEMETRY-2026-09-04.md` and the `team-lead` conversation thread this
session) for how they were allocated.
