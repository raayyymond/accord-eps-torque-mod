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

## WHAT IS STILL NEEDED BEFORE A BUILD
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
