---
name: accord-friction-polarity-more-friction-is-more-assist
description: Verified end to end - raising the modelled Coulomb friction K1 (0xC40D2) INCREASES assist and makes the wheel lighter; gp-0x6ad6 is a torque-tracking reference, not a torque added to the motor.
metadata:
  type: reference
---

**THE QUESTION** (operator, 2026-08-09): *"I thought we didn't want friction to let the LKAS demand as
much spin as possible. Also how do we know it's modelling friction?"* The second half exposed an
unverified sign that had already been built into V89.

## It IS Coulomb friction - five ways, four independent of the session that asked
1. **Form.** `friction = |model| x sign(polarity x gp-0x6abc) x K1/1024` = `F = mu*N*sign(v)`.
2. **The sign is a VELOCITY sign.** `FUN_00041464` @`0x4170C`: `gp-0x6abc <- gp-0x4f50` =
   the **resolver/motor ELECTRICAL RATE** (`STATE.md`'s own signal table).
3. **Its companion is INERTIA** - a term proportional to `d(rate)/dt` scaled by `0xC646E`, a cal the
   kit's FROZEN lists already label **"INERTIA gain"**. torque - friction - inertia = a plant model.
4. **The record named it first:** `BUILD-LINEAGE.md`'s V87 row already calls `gp-0x6b70`
   *"the Coulomb friction compensator"*, measured on-car at **non-zero 99.80 %, negative 67.19 %,
   aggregator gate OPEN 100 %.**
5. + **Coulomb friction is rate-INDEPENDENT by definition**, and the 30-route model measured the
   engagement effect as rate-independent (+0.022 [-0.070, +0.116]) - corroboration nobody designed for.

## THE SIGN CHAIN - raising K1 makes the wheel LIGHTER
🛑 **CORRECTED 2026-08-23. The earlier table was RIGHT FOR THE WRONG REASON - two errors that
cancelled.** `gp-0x6752` = -1 is the **DRIVER-FRAME <-> AGGREGATOR-FRAME CONVERTER**, not a stray
negation, and it is applied at exactly the 7 places a signal crosses between the two frames
(`0x3B92E`, `0x3B91C`, `0x381EE`, `0x3668E`, `0x358C2`, `0x3AB78`, `0x3A71A`).
**Do NOT answer this by counting negations - count FRAME CROSSINGS.** See
[[accord-gp6752-is-a-frame-converter-count-crossings]].

| # | where | effect (all signs relative to the driver's push direction) |
|---|---|---|
| 1 | `0x3BBC2 subf.s` - friction SUBTRACTED from the model | \|model out\| down |
| 2 | `FUN_0003bc20` -> `gp-0x6bfe` | pass-through, gain +1 |
| 3 | `FUN_00038148` `res = MODEL - ACTUAL` | shifts against the push |
| 4 | `gp-0x6b70 = clamp(sgn(res)*LERP(\|res\|), +-8192)`, `f' >= 0` => **d/d(MODEL) >= 0 EVERYWHERE** | against the push |
| 5 | `FUN_00037fe6` `gp-0x6ad6 += gp-0x6b70 * w(0xC64B0)=1`; output LERP flat [1024]x8 => **gain 1.000** | target effort DOWN |
| 6 | `0x3A7CA` `e = gp-0x4f60 - clamp(gp-0x6ad6, +-0xC6200=8192)` | \|e\| UP |
| 7 | PID, P/I/D all positive-coefficient, **then `0x3A71A`/`0x3A874` x `gp-0x6752` = -1** -> `gp-0x6ad4` | moves AWAY from zero in the AGGREGATOR frame |
| 8 | `0x3A8A0` sole writer -> `0x3ACA8` sole reader (**2 touches program-wide**) -> `gp-0x6b94` at +1 | no negation possible between |
| 9 | `delivered = gp-0x6752 x gp-0x6b94` => **torque in the DRIVER'S OWN direction** | **more assist** |

=> **MORE modelled Coulomb friction => LOWER target felt effort => MORE assist => LIGHTER.**

**The closed-loop statement, self-checking, needs no parity count:**
`u = POL*K*(Ts - Tref)`, `Ts = P*u + Text` => `Ts = (L*Tref + Text)/(1+L)`, `L = -P*POL*K`.
**`L > 0` is forced PHYSICALLY** - at `L < 0` the loop amplifies `Text`; at `L < -1` it runs away.
=> `dTs/dTref = L/(1+L) > 0`: **`gp-0x6ad6` IS a target felt effort.**
+ Cross-check: this predicts `d(gp-0x6b94)/d(gp-0x6b70) > 0`; the kit MEASURED **+0.2529 / +0.2565 /
+0.2617** with a passing positive control. One extra or one missing negation would predict negative.

🛑 **`0xC40D2` (K1, a tp-block scalar in the plant model, `FUN_0003b8f6`) is NOT the x1.5
friction TABLE** (14 mode-record sites `0xCF6E0...0xD9A6C` behind `0xCBE74`, feeding the `gp-0x6b26`
lane) that V73 introduced and V81 reverted. **Two different mechanisms sharing one word.** V81's
*"removes drag the operator is used to"* is about the TABLE and is **NOT evidence about `0xC40D2`.**

⚠ **The one honest route by which K1=204 could still feel bad:** Coulomb friction flips sign at
every reversal, so larger K1 = a larger **STEP at each reversal** - notchiness on turn-in, not steady
drag. Transient, unmeasured, pre-registered in V89's own docstring. [BELIEF, structural]

## The honest caveat
**V56 muted this exact lane** (`0xC6AFC`/`0xC6AFE` 32768->0) and the memory says it is *"ELIMINATED as
the driver - do not re-propose"*. **That null was scored on `P[15-26 Hz]`, the 20-25 Hz mode, NOT on
6-9 Hz**, and route `24` is not on disk. `0xC6AFC` = 32768 on all 30 other builds, so the corpus
cannot test it. => **the elimination is BAND-SCOPED and has been carried as general.** It is the main
risk to V89's thesis and only a flight settles it.

🛑 **CORRECTION:** an earlier draft said "lane weight `0xC74B0` = 32". **Off-by-0x1000** - `tp` =
`0xBF000` so `tp+0x74B0` = **`0xC64B0`**, a 0/1 ENABLE FLAG = 1, not a weight. Sign chain unaffected.
**Fifth recurrence of that trap.**
`gp-0x6b70`'s magnitude response to the dose is unsized - its LERP lives in RAM
(`gp-0x64b8`/`gp-0x641c`), not in the image.
Method: a hand field-split of the `add` chain (Format-VII layout on a Format-I instruction) gave
nonsense. **Ghidra's listing is the authority** - the standing *"assembly CONFIRMS, it does not
FORM"* rule working exactly as written. See [[feedback-decompile-first-then-assembly]].
