---
name: accord-v68-detector-still-zero-no-positive-control
description: "Honda's 1 kHz oscillation detector read zero on V68 too; the cell has never been observed non-zero in this kit, so the null has no positive control."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 95bceff4-4059-403e-a0cd-c57effc19f41
  modified: 2026-08-04T01:04:58.774Z
---

🛑 **V68's bottom rung is measured and EMPTY. bit5 (`gp-0x67df != 0` — the detector FSM left
NEUTRAL, i.e. `|gp-0x6c2c|` crossed ±12800, NO reversal required) fired 0 times in 53,991 frames**
across routes `4c` and `4e`, **including straight through the 1468-count 28 Hz lane-change burst**
(see [[accord-v68-lane-change-is-28hz]]). bit4 (`gp-0x671a >= 1`) likewise 0.

With V67 (186,321 frames at `>= 5`) and V64's route 35 flying the same `ld.bu -0x67df[gp],r6` word,
the whole ladder now reads zero across three builds.

🛑🛑 **THE LIMIT, AT FULL STRENGTH — this is the V64 lesson one layer down.** This cell has **NEVER
been observed non-zero in this kit. There is NO POSITIVE CONTROL.** The null bounds oscillation
amplitude *only if the detector is genuinely live*; **"the detector is disabled / its input is dead /
`FUN_000428d4` is not reached in this operating mode" is NOT excluded by this measurement.**

Conditional on liveness, the bound is: nothing in ~1–200 Hz reached the trip amplitude on
`gp-0x4f50` — **1056 counts at 60 Hz, 1104 at 45, 1186 at 100, 1683 at 21.3** (clamp ±13000).

⇒ **`gp-0x67df`'s writer and `FUN_000428d4`'s enable condition are OPEN and now VERDICT-AFFECTING.**
That is the highest-value firmware trace left. 🛑 `gp-0x4f50`'s deg/s conversion stays **[OPEN]** —
do not close it with `gp-0x6ac0`'s 4.7121 counts/deg-s.

⚠ **NAMING TRAP:** `builds/v50_v79/build_v68_tva.py` still calls bit4's constant `BIT_RATE` and defines
`RATE_DISP = 0x6AC0` — leftovers from the SUPERSEDED rate-axis probe (`.rwd` prefixed
SUPERSEDED-DO-NOT-FLASH). The live list is `CELLS = {0x6806, 0x67DF, 0x671A}`, confirmed by hand
from `_v68_plain_image.bin` at `0xC4B34`–`0xC4B58`. **Read `CELLS`, not the constant name.**
