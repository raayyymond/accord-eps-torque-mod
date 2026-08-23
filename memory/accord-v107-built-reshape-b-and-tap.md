---
name: accord-v107-built-reshape-b-and-tap
description: "V107 BUILT: gp-0x6b26's SPEED SCHEDULE reshaped (Y[1]/Y[2] raised, Y[0] byte-identical) because the uniform dose axis is int16-exhausted and the residual line is above 70 km/h where Honda's taper made V106 4.2x weaker. Plus the 427 tap re-aimed from the biquad lane to gp-0x6c2c at sar 3, to measure the cell that sizes V108 in a band no route has ever covered."
metadata:
  type: project
---

# ★★★★★ V107 BUILT — THE SCHEDULE, AND AN INSTRUMENT AIMED AT THE RIGHT CELL

2026-08-23. `analysis-2020accord/build_v107_tva.py`, **55/55 assertions**, BASE = V106 (flown as `a6`).
```
image  c32c3ba5da859335fa7637cca59e9ac3e40f8f6cdcb817dd582884be080a0c45
.rwd   78eae7da20a87f1a95295eca11da0d08f4cf2b3b823785594cde4be93a7b24ff
file   39990-TVA,A160-V107-V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3-0x13000-0x100000.rwd
E1  0xD7A5C / 0xD7A6C  (-29490,-17202,-5898) -> (-29490,-24000,-16000)   modes 26/27, X untouched
E2  0x55DF2  7a 94 -> d4 93   (427 tap: gp-0x6b86 -> gp-0x6c2c)
    0x55E10  a4 -> a3         (sar 4 -> sar 3)
```
**10 payload + 8 CRC = 18 bytes vs V106. ZERO unattributed vs stock. Two CRC trailers.**

## WHY A RESHAPE AND NOT MORE DOSE
The uniform axis is **int16-exhausted** — see [[accord-uniform-dose-axis-exhausted-schedule-is-the-lever]].
V106 extinguished the mode at low speed and at 55–70 km/h; **the residual is above ~70 km/h**, which
is exactly where Honda's taper delivers **−5898 vs −24546 at creep, 4.2× weaker.**
**Y[0] is byte-identical**, so creep clamp duty and the relay index are unchanged *by construction* —
and only **4 bytes per row** actually change, so the diff itself proves the creep dose did not move.

## WHY B AND NOT A — A IS RELAY TERRITORY
Constant-free duty (measured wire × a ratio of two flash tables), r77 **undamped** = conservative:
```
variant       <16      16-40     40-70     70-90
V106 today  0.00643   0.00044   0.00007   0.00000
RESHAPE A   0.01871   0.00519   0.01174   0.06223   <- 6.2 % at 70-90.  V80 TERRITORY.
RESHAPE B   0.01218   0.00180   0.00255   0.01048   <- <=1.05 % everywhere
RESHAPE C   0.01871   0.00414   0.00607   0.03391   <- 3.4 % at 70-90
```
**B's clamp knee (1963) sits ABOVE r77's undamped 70–90 p99 of 1836** — safe against the worst
distribution the corpus has ever measured, not merely the damped one. And **route a6 spent 809 s of
its 1,224 engaged seconds above 70 km/h**: the band the reshape hits hardest is the majority of the
operator's engaged driving, not a corner. On a6's own damped α, B holds ≤0.09 % at ≥70.

## WHY THE TAP MOVED — and why `gp-0x6c2c` beats `gp-0x6b26`
The tap watched `gp-0x6b86`, the biquad lane — **a filter this session decided not to build on.**
Meanwhile **no route has EVER measured `gp-0x6c2c` above 90 km/h near V106's dose** (r77: 1.1 s;
r78: 99.8 s at ×1.5), and every duty number above rests on that cell.
⭐ **`|gp-0x6b26|` is bounded at ±511 BY CONSTRUCTION, so the moment it matters it censors exactly
the information you need — it can say *that* you clamped, never *how far past*.** From `c2c` you can
compute `|b26|` exactly (Y_eff is in flash, the clamp is known) **and** get the headroom for any
candidate Y. **Prefer the unclamped input over the clamped output whenever both are tappable.**

**`sar 3`** — LSB 8 counts, full scale 8184, against a measured corpus max of **5,286**:
```
shift  LSB  full scale  clip frac  clip frac of the p99.9 tail
sar 2    4        4092   0.000012          0.011765     <- clips 1.18 % of the tail
sar 3    8        8184   0.000000          0.000000
```
Measured `|gp-0x6c2c|` engaged (r77+r78 pooled, n = 169,449): p50 40 · p90 323 · p99 1,121 ·
p99.9 1,922 · max 5,286. **The tail is the whole point, so zero clipping wins over resolution.**

## PRE-REGISTRATION (written BEFORE the build existed)
> *V107's drive must measure `|gp-0x6c2c|` and the resulting clamp duty above 70 km/h — the band
> where the residual line lives, where the reshape does all its work, and where no route in this
> corpus has ever measured this cell at a comparable dose. V106's own drive could not answer it
> because its tap was pointed at `gp-0x6b86`.*

## UNTOUCHED
`0xC407E` = 511 (the RULE-11 interlock) · `0xC6CD0` = 5346 (the 6× gain) · both MANUAL mode records
· the X breakpoints (**no LERP denominator can reach zero**) · the biquad · **the whole cave, so
`b5` still means what route a6 measured it against and the dose still reads itself out** · Lever B ·
and `0xC640A`/`0xC640C`, the `gp-0x671a` fallback branch — **proven dead, and NOT virgin: V93/V94
cut it ×0.75 and V94 flew as route `7d`, the drive the operator aborted.**

Related: [[accord-v106-extinguished-the-mode-at-low-speed]] · [[accord-uniform-dose-axis-exhausted-schedule-is-the-lever]] ·
[[accord-feedforward-lane-exists-one-cal-byte]] · [[feedback-a-stationary-mode-returns-a-fake-frequency-slope]]
