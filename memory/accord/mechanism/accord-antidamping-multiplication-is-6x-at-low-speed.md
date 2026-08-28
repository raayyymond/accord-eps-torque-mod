---
name: accord-antidamping-multiplication-is-6x-at-low-speed
description: "Measured against the cached STOCK arm (route 97): our multiplication of Honda's 6-9 Hz anti-damping is 6.17-6.57x at 0-15 km/h and falls monotonically to 1.78-2.56x above 50 km/h. The kit's published table had no low-speed bin and understated it. Separately, at 22-26 Hz stock is +3..+8 (damped) and V112 measures ~0, so V106/V112 largely recovered the band whose sign we had reversed. A full stock-to-V112 calibration diff is 81 runs."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE ANTI-DAMPING MULTIPLICATION IS **~6× AT LOW SPEED**, FALLING WITH SPEED

2026-08-27. `Re(Z) = Re(H1[rate → column torque])`, engaged & low-torque, 1024-pt Welch @100 Hz,
measured against the cached **STOCK** arm (route `97`, V9b).

## THE MULTIPLICATION, 6–9 Hz (mod ÷ stock)
```
   build        0-15    29-50   50-70   70-86   86-115 km/h
   r21 V111     6.57     3.73    2.01    1.98      -
   r22 V112     6.17     4.46    1.78    2.31      -
   r23 V112      -       5.64    1.80    2.56     1.89
```
🛑 **Strongest at 0–15 km/h (6.2–6.6×) and monotonically weaker with speed.** The kit's published
table ([[accord-the-antidamping-is-hondas]]: 2.60× @29–58, 2.39× @58–86, 0.69× @86–115) **had no
low-speed bin** — the effect is roughly **2.5× larger than recorded**, and it peaks exactly where
grind #1 and the ratchet live.
⚠ My 86–115 figure (1.89) disagrees with the published 0.69; different routes and estimator windows.
Treat the **shape** (monotone fall with speed) as the finding, not the individual cells.

## ⭐ AND 22–26 Hz IS LARGELY RECOVERED
```
   22-26 Hz   0-15   29-50   50-70   70-86   86-115 km/h
   STOCK       -7      +6      +3      +5      +8      (damped)
   r21 V111    -3      +1      +1      -4       -
   r22 V112    -1      +3      +1       0       -
   r23 V112     -      +1      -1       0       -0
```
Stock is **damped (+3…+8)**; V111/V112 sit at **~0** — near-neutral rather than the sign-REVERSED
−134/−99 the kit recorded for V102. ⇒ **V106/V112 largely recovered the band we had inverted**,
which is consistent with the operator calling V112 the smoothest build yet.

## THE FULL STOCK → V112 CALIBRATION INVENTORY — 81 RUNS
Main block (the dynamics cells):
```
  0xC40BC   600 -> 1800   relay knee (V112)      0xC61B3/B5  2048 -> 3072  arb clamps
  0xC40D2   102 ->  612   K1 (V89 x2, V112 x3)   0xC63A1     08 -> 04
  0xC40DC   22  ->   14   alpha2 (V109/V111)     0xC6446     512 -> 5244   (x10.24, "Lever B")
  0xC4B34.. 164-byte cave                        0xC649B     00 -> 01
  0xC6CD0   3564 -> 5346  the forward gain
  0xCE532/546  950 -> 0   ZEROED                 0xCF532/546 1356 -> 0  ZEROED
  + ~60 more runs across the mode records (0xD07xx..0xD98xx), a repeating pattern of
    0x??7DA/7EE 566 -> 0 · 0x??810 200 -> 400 · 0x??818 536/539 -> 142/140 (x0.26)
```
⚠ **DO NOT read `0xC6CD0` 3564 → 5346 as "the mod is only ×1.5 on stock."** V57 *repointed* the
forward reader onto `0xC6CD0`; whatever stock held there was not serving as this gain, so the
stock-vs-mod ratio on that cell is not a gain ratio. (I nearly recorded that error.)

## ⚠ WHAT IS STILL NOT IDENTIFIED
**What produces the ~6× low-speed multiplication.** Checked and rejected as the explanation:
`gp-0x6b26`'s Y row is speed-LERPed on `gp-0x6a5e` with knots **[0, 20, 90] km/h**, but its dose vs
stock is **×3.00 / ×3.00 / ×8.14** — *rising* with speed, the **opposite** of the measured shape.
⇒ **`gp-0x6b26` does not explain it.** The candidate must be speed-scheduled with a falling profile
and be engagement-conditional but command-independent
([[accord-antidamping-is-a-state-effect-of-engaging]]).

Related: [[accord-the-742hz-mode-is-stocks-and-our-q-is-lower]]

## 🛑🛑 CORRECTION, SAME DAY — THE "81 RUNS" DIFF USED THE WRONG BASELINE
The file I diffed against was **`SUPERSEDED-DO-NOT-FLASH-_v83a_FACTORE.STOCK-GAINA.STOCK_plain_image.bin`**
— that is **V83a**, whose filename contains "STOCK" only because *FactorE was reverted to stock*.
**The real stock dump is `accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin`.**
⇒ the "81 calibration runs" figure and every stock-value in it are **V112-vs-V83a**, not vs stock.

### THE TRUE V112-vs-STOCK PICTURE — **29 runs** in the main cal block
```
  0xC40BC   600 -> 1800   relay knee          0xC6446    512 -> 5244   Lever B
  0xC40D2   102 ->  612   K1  (x6 on STOCK)   0xC649B     00 -> 01
  0xC40DC    22 ->   14   alpha2              0xC64B4  5 B -> 0xFF
  0xC4B34  164 B cave (stock is all 0xFF)     0xC64DE     11 -> 1b
  0xC61B3/B5  512 -> 3072  arb clamps         0xC659A..0xC65CE  corridor floats 1.0f -> 5.0f
  0xC61C0   6 B -> 0xFF                       0xC674F..0xC676D  boost floor
  0xC62EA   320 ->    0   🛑 LOW-SPEED STEER LOCKOUT REMOVED
  0xC6CD0  65535 -> 5346  the forward gain    (+ 0xD7A5C/6C friction Y x3, V106)
```
⭐ **`0xC6CD0`'s stock value is 65535, NOT 3564** — confirming the caution above: V57 repointed the
forward reader onto an unset cell, so there is no meaningful "stock gain" on it.
⭐⭐ **ALL FOUR base-assist factor tables (B/C/D/E) are BYTE-IDENTICAL TO STOCK on this car's live
indices 24/26/27**, resolved through their own pointer arrays (`0xC9CCC/0xC9E9C/0xC9DB4/0xC9F84`).
⇒ **the V74–V86 damper work is either on dead records or has been fully reverted. The base-assist
damper on this car is Honda's.** The `0xCE5xx/0xCF5xx/0xD0xxx/0xD2xxx` zeroings I flagged are V83a
edits on records this car does not select.
⭐ **`0xC62EA` 320 → 0 removes Honda's low-speed steer lockout** (~5 km/h; failing it sets
STEER_STATUS = 3 and kills the authority ramp). ⇒ **at 0–5 km/h stock has essentially NO LKAS
authority and we have full authority**, so the 6.2–6.6× figure in the 0–15 km/h bin is **partly a
not-like-for-like comparison** and must not be quoted as a pure gain multiplication.
⚠ Grind #1 lives at 5–10 mph = 8–16 km/h, **above** the lockout, so the lockout is unlikely to be
grind #1's mechanism — but it does contaminate the lowest Re(Z) bin.
