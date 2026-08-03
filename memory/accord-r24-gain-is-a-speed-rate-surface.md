---
name: accord-r24-gain-is-a-speed-rate-surface
description: r24's gain is a two-axis speed×rate LERP surface; its rate axis is arithmetically dead for every symptom, and a flat arm inverts Honda's own schedule
metadata:
  type: reference
---

★★★★ **r24's gain is NOT a scalar.** `FUN_0003ad74` rebuilds it every cycle by cross-interpolating four
ROM records on **VEHICLE SPEED** (`gp-0x6a5e`; cross axis `0xC6010` = `[0, 640, 3200, 6400]` =
0 / 9.99 / 49.95 / 99.9 km/h) and then LERPing on **MOTOR RATE** (`gp-0x6ac0`). Byte-verified in stock
`code.bin` and in `_v65`/`_v66`/`_v67_plain_image.bin`; ladder confirmed in Ghidra.

Record layout is **20 bytes**: `u16 count=4`, `X[4]`, `Y[4]`, pad. Mode 10 → `0xD2A74` / `0xD2AB0` /
`0xD2AEC` / `0xD2B28`; mode 11 → `0xD2A88` / `0xD2AC4` / `0xD2B00` / `0xD2B3C`, **interleaved at stride
0x14**. Honda **rolls the gain off with speed**: 3072 at 0 km/h → 2151 at 100 km/h.

## ★★ 1. THE RATE AXIS IS ARITHMETICALLY DEAD FOR EVERY SYMPTOM
Measured on-car, **100% of the windows in all three populations land inside the FLAT first segment
`[0, 400]`**, where `Y[0] == Y[1]`:

| population | bus counts | **gp-0x6ac0** |
|---|---|---|
| grind #1 | ~128 | ~75 |
| grind #2 creep | ~256 | ~151 |
| grind #2 highway | 30–42 | ~18–25 |

⇒ `Y[2]`/`Y[3]` never participate. The rate axis is not a *weak* discriminator — it is **incapable** of
discriminating, which explains the previously measured 81.1%/48.5% rather than being a separate fact.
**Only the SPEED axis can separate anything on this surface**, and speed separates grind #1 (creep) from
the *highway* grind #2 cleanly but **not** from the *creep* grind #2, which shares its cells.

🛑 **Sharpening the rate breakpoints to force a rolloff between axis 75 and 151 is REJECTED ON GATE 2.**
`gp-0x6ac0` is a **rectified** filtered motor rate, so it sweeps at 2× the mode frequency; a steep gain
slope on it is a **parametric pump** — the failure mode V58/V59/V60 chased for three builds. Keeping the
operating point inside the flat segment gives zero local slope. **Do not propose it.**

## 🛑 2. UNITS — and a real error inside a flashed build's sizing
Cal `tp+0x713a` = `0xC613A` = **1159**, so `bus = (gp-0x6abe × 48 × 1159) >> 15` = **1.697754 ×
`gp-0x6ac0`**, and `gp-0x6ac0` = `2^18/(48×1159)` = **4.71210813** counts per deg/s exactly.
⇒ **bus counts = 8 × deg/s, exactly.**
**V67's build note sized its arm as "creep 7.2 km/h, 128 deg/s ⇒ LERP 2622 ⇒ 5244 = 2.00×" — but 128 was
BUS COUNTS** (axis 603 instead of 75). The true LERP at grind #1's operating point is **2704**, so the
arm delivers **1.94×**. Numerically small; a units error inside a load-bearing calculation is not.
**Byte-read the scale cal before converting any bus quantity into a firmware axis.**

## ★★ 3. A FLAT ARM INVERTS HONDA'S SCHEDULE — and cannot fix two operating points at once
Because the surface rolls off with speed, V67's scalar arm delivers its **largest** multiplier where the
stock design wanted the **least**:

| operating point | stock LERP | V62/V65 | **V67** |
|---|---|---|---|
| grind #1 — creep 7.2 km/h | 2704 | 2.00× | **1.94×** |
| grind #2 creep — 5 km/h | 2409 | 2.00× | **2.18×** |
| **highway — 100+ km/h** | 2151 | 2.00× | **2.44×** |

🛑 **Structurally incapable of fixing the highway: one degree of freedom, two constraints.** 1.00× at
highway needs arm 2151 = **0.80× at grind #1** (worse than stock); 2.00× at grind #1 needs arm 5408 =
**2.51× at highway**. ⚠ **But the predicted highway harm did NOT materialise on-car** — see
[[accord-v67-flew-both-grinds-fixed]]. The arithmetic is right; the inference from it was wrong.

## ✅ 4. A CAL-ONLY SPEED SCHEDULE IS SAFE — and is on the shelf, not recommended
Raising `Y[0]`/`Y[1]` in the 0 and 10 km/h records only (50/100 km/h left byte-identical) gives 2.00× to
10 km/h tapering to 1.00× at 50 km/h and stock above. Blast radius verified two ways: **exactly one
pointer image-wide per record** (`0xCBF84`/`0xCC06C`/`0xCC154`/`0xCC23C`, full 32-bit LE scan), all four
in **one CRC block** `(0xD2000, 0xD2FFC)`, and a full-image 32-bit float scan finds **no float mirror**
for any Y value and no clustered mirror table ⇒ **the V27 int/float desync class does not apply.**
⚠ It is **mutually exclusive with the LKAS gate** — taking the arm discards the LERP entirely
(`0x3AC04`–`0x3AC16`) — so it would re-expose the creep grind #2 in manual driving that V67's gate
currently suppresses. **Not recommended**: the highway dose response it would target does not exist.

Arithmetic and the edit's exact bytes: `analysis-2020accord/v68_design_math.py`.
Related: [[accord-r24-gain-b-four-pointer-arrays]], [[accord-v62-fixed-the-grinding]].
