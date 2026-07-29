---
name: accord-gp6a5e-is-voted-vehicle-speed
description: "★★★★★ CORRECTION OF RECORD — gp-0x6a5e / gp-0x6a62 / gp-0x6a64 are VOTED VEHICLE SPEED (64 counts per km/h) from CAN 0x1D0 wheel speeds, NOT 'voted driver/column torque'. Verified end-to-end. Falsifies 'no vehicle-speed input anywhere in the assist path'."
metadata:
  type: reference
---

**`gp-0x6a5e` = VOTED VEHICLE SPEED, internal unit 64 counts per km/h.** Its siblings
`gp-0x6a62` (voter output w/ rate guard) and `gp-0x6a64` (slew-limited copy) are the same physical
quantity. **This contradicts the long-standing kit label "sensor-A voted column/driver torque".**

## Verified chain (stock `code.bin`, GhidraMCP + byte scan)

1. **CAN RX descriptor table @`0xBB5A0`, stride `0x20`** (see [[accord-can-rx-descriptor-table-bb5a0]]).
   Record 13 = ID **`0x1D0`**, handler `0x00052E32`, RX buffer **`0xFEDF6C20`** = `gp-0x13e0`.
2. **`FUN_00021646/21622/21672/2169E(gp-0x13e0)`** — four per-wheel field extractors. `FUN_00021646`
   returns `(byte3>>2) | (byte2<<6) | ((byte1&1)<<14)` = a **15-bit field** → Honda `WHEEL_SPEEDS`
   packing (4 × 15-bit in 8 bytes). ⚠ These take the buffer **address as an argument**, so the
   payload read is **register-indirect and INVISIBLE to a gp-relative load/store scan** (my direct
   scan correctly returned 0 accesses to `0xFEDF6C20`).
3. **`FUN_00053216(idx)`**, `idx = 0..3`: scales `raw * 0x29 >> 6` (×41/64), SNA → `0x7fff`,
   stores to `gp-0x6e50/0x6e4e/0x6e4c/0x6e4a` (+ prev `gp-0x6e48/46/44/42`), shadow twins
   `gp-0x4d5c..0x4d4e`.
4. **`FUN_000534da`** (entry = descriptor rec-14 handler) fans them to
   `gp-0x6a40/0x6a3e`(w0), `gp-0x6a44/0x6a42`(w1), `gp-0x6a38/0x6a36`(w2), `gp-0x6a3c/0x6a3a`(w3),
   shadow twins `gp-0x4c94..0x4ca2`. **Fallback arm substitutes ONE scalar for all four:**
   `sVar2 = (ushort)gp-0x6753 << 6` — only coherent for a vehicle speed, never for independent
   torque channels. (Gated on `gp-0x437c==1 && gp-0x6a98!=0`.)
5. **`FUN_00041eec` = the VOTER.** Inputs = the four wheel speeds + a 5th reference `gp-0x6a46`
   (written by the CAN `0x13C` handler region `0x52320..0x523FC`). Per channel validity =
   `(x + 0x1900) < 0x9601` ⟺ **`-6400 <= x <= 32000`** = `[-100, +500] km/h`. Takes `|x|`, picks the
   channel **closest to the previous output**, or the **mean** if ≥2 valid and spread < tolerance,
   clamps to `0x7d00`=32000. Writes `gp-0x6a5e` (@`0x42342`), `gp-0x6a62`, and a slew-limited
   `gp-0x6a64` (@`0x42360`, rate cal `tp+0x74ee`). Each has exactly ONE writer.

## The unit scale — two independent derivations agree
- Path A (CAN): raw in 0.01 km/h × 41/64 → 5 km/h = 500 raw → **320.3 counts**.
- Path B (substitute): km/h byte `<< 6` → 5 km/h → **320 counts**.
⇒ **internal = 64 counts / km/h.** This makes the two consumer cals exactly round:
`0xC62EA = 320 = 5.0 km/h (3.11 mph)` and `0xC62E8 = 12800 = 200.0 km/h`. Roundness in km/h on
both is not coincidence.

## THIRD independent confirmation of 64 counts/km/h — LERP axis roundness
Walking the LERP banks (layout `int16 [flags, count, X[count], Y[count]]`, one LE32 pointer per record
to its **count** field, pointer table `0xC7980..0xCBE8C`, records in **groups of 3** = variant slots):
- `0xD0xxx` bank: **20 of 90** records have **every** X an exact multiple of 64.
- `0xD2xxx` bank: **12 of 52** (it is a near-duplicate *variant* bank of `0xD0xxx`).
Dividing by 64 yields round km/h: `[0,10,40,90,100]`, `[0,32,64,96]`, `[30,60,80,140]`,
`[20,80,140,200]`, `[0,8,16,32,48,70]`, `[10,40,80,120,160,200]`, `[0,15,40,80,140,200]`.
The other ~70 records (`[0,150,300,600,900,...]`, `[0,3,9,18,29,40]`, `[0,19,50,127,209,452,...]`) are
plainly other axes. **`12800 counts = 200 km/h` is the top breakpoint of several axes — identical to
`speed_clamp_hi` cal `0xC62E8`.** ⇒ a "0.5 km/h per count" reading is FALSIFIED (it would imply
960–25600 km/h axes).

**Assist gain is MAXIMUM at standstill, never locked out:** `0xD08BE` `[0,8,24,40,64,96] km/h →
Y=[16384,13076,10086,8951,8065,7534]` and `0xD0912` `[0,8,16,32,48,70] km/h →
Y=[16384,12213,9411,5443,2628,131]`. Damping curves are the mirror image (Y=0 at the low end).

## ✅ VERIFIED: the V44/V47 "Factor C" damper axis IS a SPEED axis
Record boundaries (note the kit's `0xD27BC`/`0xD27D0` are the **count** fields; records start 2 bytes
earlier):
- `@0xD27BA` = `[0, 4, X=[2240,3840,5120,8960], Y=[0,235,430,877]]` → **`[35,60,80,140] km/h`**
- `@0xD27CE` = same axis, `Y=[0,234,431,877]`;  `@0xD27E2` = same axis, `Y=[0,234,429,908]` (3rd slot)
- Sibling in the other bank `@0xD07BA` = `[1920,3840,5120,8960]` = `[30,60,80,140] km/h`,
  `Y=[0,242,419,875]` — the same curve family.

⇒ **The kit's "Factor C has Y[0]=0 at X[0]=2240 ⇒ zero damping HANDS-OFF (below 2240 counts of driver
torque)" is WRONG.** It is **zero damping below 35 km/h** — an ordinary speed-scheduled damping ramp.
V44 (`Y[0] 0→235`) does still add low-speed damping, so its *direction* survives, but its stated
*mechanism* does not, and the "hands-on cures the buzz" observation must be explained by some other
factor keyed on real driver torque — not this one.
**Bonus:** the operator's buzz regime 3–8 m/s = **10.8–28.8 km/h = 691–1843 counts**, entirely **below**
`X[0]=2240` (35 km/h = 9.7 m/s) ⇒ stock Factor C is **exactly 0 across the whole vibration regime**.
For contrast, V47's "Factor E" record `@0xD27F6` = `X=[60,400,2500,4000]` — **not** multiples of 64, so
that one really is the motor-rate axis (`gp-0x6ac0`), consistent with the kit.
[[reference_accord_fun34350_damping_term_live_and_gated]] [[reference_accord_damper_two_deadzones_factorC_factorE]]
- **Gentle-EME decider gate** `gp-0x6a62 >= cal 0xC6312 (320)` = **speed >= 5 km/h**, not
  "column torque >= 320".
- **Governor `FUN_0004503c`** reads `gp-0x6a64` @`0x451E2`/`0x45308` vs cal `tp+0x7316 = 640`
  = **10 km/h** — gates a derate rate-limit.
- ⇒ **The standing kit claim "There is NO vehicle-speed input anywhere in the command/base-assist
  path (all 9 lanes checked)" is FALSIFIED.** So is "5 mph = openpilot `minEnableSpeed` + plant
  physics, NOT a firmware gate" — a firmware speed window provably exists.

## ✅ RE-CONFIRMED 2026-07-29 via the independent pointer-chase route (team-lead's variant-coding recipe)

Re-derived from scratch using a completely different method than the LERP-axis-roundness scan above, to
close the "is this genuinely resolved or still disputed" question after a sister agent (SensorIdentity)
re-traced the voter fresh. Team-lead's pointer-chase recipe: 5-byte coded ID -> `FUN_00057f8e` match vs
16 ASCII PN keys @`0xCD000` stride `0x24` -> ROW -> index byte @`0xCD012+ROW*0x24` -> INDEX -> `ptr_array[INDEX]`.
For our car (TVAA1 -> row 2 -> **INDEX 10**): `0xC9E9C + 10*4 = 0xC9EC4`, fresh `read_memory` = bytes
`bc 27 0d 00` = **`0x000D27BC`** exactly. `0xC9F84 + 10*4 = 0xC9FAC` = bytes `f8 27 0d 00` =
**`0x000D27F8`** exactly. Both match this file's already-recorded addresses byte-for-byte -- independent
confirmation via pointer arithmetic, not just LERP-axis-roundness inference.

**Index variable pinned by fresh disassembly of `FUN_00034350` itself** (not inferred from axis shape):
`puVar11 = *(ushort*)(gp-0x6a5e)`, gated `if (puVar11 > 0x7d00 || gp-0x67f4 != 1) uVar13 = 0x400` else
LERP against `0xC9E9C+mode*4`. **Confirms `gp-0x6a5e` is the literal index register, at the instruction
level, not just consistent axis roundness.**

**New nuance not previously on record: the gate is NOT simply "zero below 35km/h."** If `gp-0x67f4`
(newly identified this session as the SPEED VOTER's OWN validity flag -- written by `FUN_00041eec` at
`0x4218a`/`0x421a0`, the same function this file's voter trace already covers) is 0 (voted speed not
trustworthy), the whole factor defaults to **UNITY (1024/1024)**, not zero. So "Factor C = 0" requires
BOTH low speed AND a valid voted-speed reading -- a sensor-fault condition does not silently zero the
damper, it defaults to full damping instead.

Factor E `0xD27F8` byte-confirmed same session: `04 00 3c 00 90 01 c4 09 a0 0f 00 00 8c 00 1b 02 9f 03 00
00` -> X=(60,400,2500,4000), Y=(0,140,539,927) -- matches this file's record, index = `gp-0x6ac0` (motor
rate magnitude) confirmed at the instruction level in the same `FUN_00034350` decompile.

## Why the earlier traces missed it
The wheel-speed payload is read **register-indirect via an address argument**, and the 0x1D0 *status*
handler `FUN_00052E32` stores only validity/SNA flags (48 globals, **0** read by the assist path — a
verified zero, with the 0x1EA handler as a positive control showing the method detects real links).
So both a gp-relative scan and a "who reads the RX buffer" search come back clean while the values
still flow. See [[accord-gp4f60-two-encodings-enumeration-trap]] for the sibling enumeration trap.
