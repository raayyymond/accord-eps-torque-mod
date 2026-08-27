---
name: accord-the-coulomb-relay-is-located-c40bc-is-its-knee
description: The command-proportional Coulomb relay the kit has named since V80 is LOCATED - FUN_0003b8f6 computes clamp(POL*gp-0x6abc*12 / cal(0xC40BC), -1, +1) and multiplies it by a |model|-proportional magnitude. 0xC40BC is the relay KNEE, V108 already doubled it 300->600 with a positive operator report, and raising it converts Coulomb into viscous - at the cost of assist.
metadata:
  node_type: memory
  type: reference
---

# THE COULOMB RELAY IS **LOCATED** — `0xC40BC` IS ITS KNEE

★★★★★ **EVIDENCE — decompile of `FUN_0003b8f6` @`0x3B8F6`**, 2026-08-27. The kit has called the
mechanism *"a command-proportional Coulomb relay"* since [[accord-engagement-amplifies-6-9hz]] and
[[accord-v80-damper-relay-and-grind1-inert]] **without ever pointing at the instruction that makes
it a relay.** This is that instruction.

## THE ARITHMETIC, mirrored from the decompile (`tp = 0xBF000`)
```
iVar20  = (int)POL * (int)gp-0x6abc * 12                 # POL = *(char*)(gp-0x6752), gated (POL+1)<3
                                                          # gp-0x6abc is RATE-like
fVar14  = (iVar20 * 0.5) / (cal(0xC40BC) * 0.5)          # = iVar20 / knee
fVar13  = clamp(fVar14, -1.0, +1.0)                      # <-- THE RELAY.  tp+0x50bc
fVar15  = EMA( |model| * cal(0xC40D2)/1024 * fVar13
               + cal(0xC4080)/1024 * fVar13 ,             # tp+0x50d2 = K1, tp+0x5080 = offset
               pole cal(0xC40D0) )                        # tp+0x50d0
friction = clamp(fVar15, -10.0, +10.0)
gp-0x6ae2 = friction * 1024                               # the telemetered friction cell
iVar20   = (model - friction - inertia) * cal(0xC7468)    # subtracted from the model
```
⇒ **A saturating sign function whose MAGNITUDE is `|model|`-proportional.** Below the knee it is
LINEAR in rate (= viscous damping); above it, a pure **±1 sign** (= Coulomb friction, the relay).
**Saturation point: `|gp-0x6abc| >= knee/12`.**
```
   knee   |gp-0x6abc| at saturation
    300   (STOCK)      25
    600   (V108)       50
   1200               100
   2400               200
```

## ⭐ WHY THIS IS THE RIGHT TARGET
[[accord-ratchet-and-grind-are-command-gated-saturation]] measured, and its 2-D control confirmed,
that the 6–9 Hz ratchet band is **command-gated at MATCHED steering rate**: at rms 8–20 °/s the
6-9/1-3 band shape goes **0.93 → 1.13 → 4.72 → 44.71** across command bins — a **48× fold at constant
rate** — while the pure rate effect at matched command is only **2.8×**.
⇒ **A nonlinearity keyed to command magnitude and not to motion is exactly what this term is**: the
relay's amplitude is `|model|`-proportional and `|model|` tracks command, while its *shape* is set by
rate against the knee. **The two axes of the measurement map onto the two factors of the product.**

## ⭐⭐ THE DOSE-RESPONSE SIGNAL ALREADY EXISTS
**V108 raised `0xC40BC` 300 → 600** (one of its four cal edits) and the operator reported
*"twenty miles an hour and above, generally, this is the best that it's ever been in that regime at
six x"*. ⚠ **V108 changed four cells, so this is NOT attributed** — the notch revert and the
`gp-0x6b26` Y-row revert are equally credited. But it is a positive signal on a cell that moves the
relay's corner, and it is the only cal in the build that touches the relay.

## 🛑 THE COST, STATED BEFORE ANY DOSE IS PROPOSED
`fVar13 = clamp(x/knee, ±1)` is **monotonically DECREASING in the knee** — a larger knee can only
SHRINK `|fVar13|` at a given rate. And [[accord-friction-polarity-more-assist]] is verified
nine ways: **more modelled friction = MORE assist.** ⇒ **raising the knee REDUCES ASSIST.**
**That trades directly against the operator's 6× goal**, and it is the same direction that made V93/V94
unsafe when the *damper* was lowered (*"made the stuttering and grinding worse, by a lot"*).
🛑 **DO NOT PROPOSE A KNEE DOSE UNTIL THE ASSIST COST IS PRICED IN COUNTS AT THE RATES THAT MATTER.**

## ✅ THE CRUX IS RESOLVED — `gp-0x6abc` IS ON THE SAME SCALE AS `gp-0x6ac0`
**Decompile of `FUN_00041464`** (the writer), normal non-fault path:
```
sVar15 = gp-0x4f50                      # the source
uVar18 = sVar15 * 0x400 ; uVar16 = EMA(uVar18, cal(0xC743C))
gp-0x6abc <- sVar15                     # RAW, signed, unfiltered
gp-0x6abe <- (short)(uVar16 >> 10)      # filtered, signed
gp-0x6ac0 <- |uVar16| >> 10             # filtered, ABSOLUTE   <- the 0xC520C index
gp-0x6ac2 <- |uVar16| >> 10, sign-gated against gp-0x6b98
```
⇒ **`gp-0x6abc`, `gp-0x6abe` and `gp-0x6ac0` are the SAME underlying quantity**, differing only in
filtering and sign — `uVar16` is just `gp-0x4f50 × 1024` filtered, and the `>>10` undoes the `×1024`.
**So `gp-0x6ac0`'s 4.7121 ct/(column °/s) scale transfers to `gp-0x6abc`.**
⊕ Sanity: peak `gp-0x6ac0` on record is **1462 ct = 310 °/s**, consistent with the 400–500 °/s max
steering rates measured directly from `ang`. **The scale is not assumed — it is derived and checked.**

```
   knee   saturates above        fVar13 at 10.6 deg/s
    300      5.3 deg/s   STOCK          1.000
    600     10.6 deg/s   V108           1.000     <- ON THE CAR
    900     15.9                        0.666
   1200     21.2                        0.499
   1800     31.8                        0.333
   2400     42.4                        0.250
```
⭐⭐ **V108's relay corner is 10.6 °/s — the bottom edge of the 8–20 °/s band in which the ratchet was
isolated.** Stock's was 5.3 °/s, i.e. saturated essentially always.

## ✅ GATE 1 — CLOSED, TWO METHODS AGREEING
**Exactly ONE tp-relative access image-wide, at file `0x3BAB4`, inside `FUN_0003b8f6`.** Zero writers
(ROM cal). Method 1: raw Python LE scan for `disp16 ∈ {0x50BC, 0x50BD}` filtered to `tp`/`gp` base.
Method 2: the decompile itself shows exactly one use of `tp + 0x50bc` in the whole function, at the
relay. **The two independently agree on both the count and the location.**
⊕ Same for the other two factors: `0xC40D2` (K1) one hit at `0x3BAFE`; `0xC4080` (offset) one hit at
`0x3BAF6`. Both inside the same function.
⚠ **Residual, stated:** neither method can see register-indirect access to a cal. For a tp-relative
ROM constant this is the same standard accepted for `0xC40DC`, but it is not zero.

## 🛑 THE ASSIST COST, PRICED — AND IT IS **LARGE**
`fVar13 = clamp(x/knee, ±1)` leaves `|fVar13|` **unchanged above `knee_new/12`** and scales it by
`knee_old/knee_new` at the OLD corner. So a 600→2400 raise is a **4× cut at 10.6 °/s**, tapering to
no change at 42.4 °/s — **the cut lands squarely in the ratchet band.**
**Magnitude bound:** friction is clamped to ±10.0 float ⇒ `gp-0x6ae2` spans **±10,240 counts**, against
a residual clamped at **±20,000** ⇒ **the term can reach 51 % of the residual range.**
⇒ 🛑 **A 4× cut in a term that large is NOT a small edit, and modelling it is not good enough.**
Per [[accord-friction-polarity-more-assist]] (verified nine ways) it is a **direct assist reduction**,
in the same direction that made V93/V94 unsafe to drive.

## ✅ GATE 2 — DONE. NO PHASE RISK, BUT THE **SAME SIGN REVERSAL** THAT KILLED Kd.
⭐ **THE KNEE ADDS ZERO PHASE, STRUCTURALLY.** `clamp(POL·gp-0x6abc·12 / knee, ±1)` is an **odd,
memoryless** nonlinearity, so its describing function `N(A)` is **REAL for every input amplitude**:
```
   A <= k :  N = 1/k                                          k = knee/12
   A >  k :  N = (1/k)(2/pi)[ asin(k/A) + (k/A)sqrt(1-(k/A)^2) ]
```
⇒ **raising the knee changes MAGNITUDE ONLY and cannot rotate anything into a new sector.**
**GATE 2 does not block this lever** — the same structural argument V110's docstring made for Kd,
and here it is exact rather than approximate.
```
  describing-function gain vs |gp-0x6abc| amplitude A
     A      N(knee=600)  N(knee=2400)   ratio
     25       0.02000      0.00500       0.250
     50       0.02000      0.00500       0.250
    100       0.01218      0.00500       0.411
    200       0.00630      0.00500       0.794
    400       0.00317      0.00304       0.959
    800       0.00159      0.00157       0.990
```
⇒ a 600→2400 raise cuts this term **up to 4× at low rate and ≈1× above ~400 counts (85 °/s)**.

🛑 **BUT THE LANE REVERSES SIGN BETWEEN THE RATCHET AND THE GRINDING BANDS.** The lane's own
dynamics are one EMA, `cal(0xC40D0) = 408`, `α = 408/4096 = 0.0996` at 1 kHz ⇒ corner **15.9 Hz**.
Rotating it through the **measured** `arg Z(f)` (three drives, 628 windows —
[[accord-rez-antidamping-replicated-three-drives]]), exactly as the Kd verdict was computed:
```
  band     f Hz    |H_f|   argH_f   cos(argZ+argH)     |H|*cos
  6-9      7.79   0.9063   -23.6      -/+ 0.865         0.784   <- the RATCHET
  9-12    10.50   0.8467   -30.3      -/+ 0.994         0.842
  12-16   14.00   0.7666   -37.5      -/+ 0.821         0.629
  16-18   17.00   0.7011   -42.5      -/+ 0.321         0.225
  18-22   20.00   0.6414   -46.6      +/- 0.254         0.163   <- the GRIND
  22-26   24.00   0.5717   -50.9      +/- 0.602         0.344   <- the GRIND
  26-31   28.50   0.5062   -54.6      +/- 0.983         0.497   <- the GRIND
  31-35   33.00   0.4523   -57.3      +/- 0.815         0.369
```
⇒ **the sign flips between 16–18 and 18–22 Hz** — the same reversal, at almost the same place, that
killed the Kd lever. And because the knee is a **magnitude-only** change it shrinks `|H|` in **every
band simultaneously**: it necessarily helps one family and hurts the other.

## 🛑 THE TRADE, PRICED — AND IT IS ~1.28:1, NOT Kd's 3–4:1
Summing the three grinding bands equally against the ratchet band:
```
  benefit  6-9 Hz            0.784
  cost     18-22+22-26+26-31 0.163 + 0.344 + 0.497 = 1.004
  ratio    cost / benefit    1.28 : 1  AGAINST
```
⭐ **That is far better than Kd** (2.96× at 18–22 and 3.92× at 26–31 —
[[accord-kd-is-one-knot-of-a-flat-lerp]]), **which is precisely why Kd is dead and this one is not.**
⇒ **[EVIDENCE for the arithmetic; BELIEF for the weighting] the knee is a genuine TRADE, not a fix
and not an obvious loss.** Whether 1.28:1 is worth taking depends on how the operator weights
ratcheting against 18–31 Hz grinding — **that is his call, not a number this kit can settle.**
⚠ The ratio assumes equal weight on three grinding bands and one ratchet band, and it assumes the
kit's sign convention. **Under the inverted branch the trade simply runs the other way** — helping
the grind at the ratchet's expense — and either way it is a trade.
⚠ It also assumes the operating amplitude is **at or below ~200 counts** of `|gp-0x6abc|`; above
~400 the knee raise does almost nothing (ratio 0.96–0.99). **V111 measures exactly that amplitude.**

## ⭐ A SECOND FINDING FROM THE SAME READ: `0xC4080` = **0**
The relay's constant offset term is **ZERO** in the flown image, so
`friction = EMA(|model| · K1/1024 · fVar13)` with **no Coulomb floor**. ⇒ **the term vanishes when
there is no command**, which confirms *"command-proportional Coulomb relay"*
([[accord-engagement-amplifies-6-9hz]]) **at the instruction level** rather than by inference.

## ⭐⭐ THEREFORE THE NEXT BUILD IS A **PROBE**, NOT A DOSE — and it is zero-risk
The design law says **compare, don't measure**, and **never spend a rung on a bare threshold against a
distribution you have not seen.** Here the distribution IS known, through the sibling: `gp-0x6ac0`
peaks at 1462 ct, so thresholds at 50 and 200 sit well inside it.
```
  rung A :  |gp-0x6abc| >= 50    "is the relay SATURATED at V108's knee?"      (10.6 deg/s)
  rung B :  |gp-0x6abc| >= 200   "would a knee of 2400 STILL saturate?"        (42.4 deg/s)
```
⭐ **`(A=1, B=0)` is EXACTLY the population a 600→2400 knee raise would affect.** Its duty, stratified
by speed and command post-hoc from the wire, **sizes the dose before a single byte of the relay moves.**
⊕ Both are **single-operand** rungs against an immediate — they keep V96's proven cave discipline and
need no second scratch register.
⊕ If `(A=1, B=0)` duty is near zero in the symptomatic regime, **the knee lever is dead and no dose
was ever spent** — the null is interpretable, which is the whole point.

## WHAT IS STILL NEEDED BEFORE A BUILD (updated — items 1 and 2 now CLOSED)
1. **The scale of `gp-0x6abc`.** If it shares the 4.7121 ct/(°/s) column-rate scale
   ([[reference-accord-rate-scale-4p7121-stands]]) then V108's knee saturates at **~10.6 °/s** —
   **inside the 8–20 °/s band where the ratchet was isolated.** ⚠ **NOT VERIFIED**; `gp-0x6abc` is a
   different cell from `gp-0x6ac0` and the scale must not be assumed. This is the crux.
2. **GATE 1 on `0xC40BC`** — reader/writer census by BOTH methods (Ghidra + a raw LE Python scan),
   including the 6-byte extended-displacement form and register-indirect access.
3. **GATE 2** — the term sits inside the observer, so the phase question is whether converting
   Coulomb→viscous at 6–9 Hz changes the sign of its contribution to `Re(Z)`.
4. **The assist cost in counts**, from `gp-0x6ae2` (which IS telemetered and has flown).
⊕ `gp-0x6ae2` is already a probe channel — V106's `b5` rung compares `|gp-0x6ae2|` against
`|gp-0x6b26|`. **A knee dose has an instrument on it already.**

## ⚠ WHAT THIS DOES **NOT** SAY
- It does **not** say the relay causes the ratchet. It says the relay is a command-gated nonlinearity
  in the right place with the right two factors. **[BELIEF, mechanism-grounded, not measured.]**
- The 44.71 cell rests on **36 windows**; the 2-D table is unbalanced (high command with low rate is
  rare by construction). The 48× fold is robust in direction, not in magnitude.
- `0xC40D2` (K1) is the OTHER factor and is **already closed on arithmetic** for a different reason —
  collinear with `|model|` above 1 °/s ([[accord-six-levers-closed-on-arithmetic]]). **The knee is
  not collinear with anything**: it changes the SHAPE, not the magnitude.

Related: [[accord-c40dc-is-the-band-limit-lever]] (adjacent cell, different function — the adjacency
is a documented trap) · [[accord-v80-damper-relay-and-grind1-inert]]
