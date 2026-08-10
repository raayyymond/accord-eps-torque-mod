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
| # | where | effect |
|---|---|---|
| 1 | `0x3BBC2 subf.s r10,r8,r8` - friction SUBTRACTED from the model | model out down |
| 2 | `FUN_0003bc20` -> `gp-0x6bfe` | down |
| 3 | `FUN_00038148` `residual = MODEL - ACTUAL` | down |
| 4 | `gp-0x6b70 = sign(res) x LERP(|res|)` | more negative |
| 5 | `FUN_00037fe6` `gp-0x6ad6 = (... + 32 x gp-0x6b70) x LERP >> 10` (`0xC74B0`=32, gate open 100 %) | down |
| 6 | `FUN_0003a382` `error = gp-0x4f60 (measured driver torque) - clamp(gp-0x6ad6)` | up |
| 7 | PID, P/I/D all positive-coefficient -> `gp-0x6ad4` | up |
| 8 | `0x3ACA8` -> windowed -> **`mov`, `add` x8, NO negation** -> `0x3AD20 st.h r10,-0x6b94[gp]` | up |
| 9 | `gp-0x6b94` -> governor -> `gp-0x6acc` -> shaper -> `gp-0x6b98` -> motor | **more assist** |

=> **MORE modelled Coulomb friction => MORE assist => LIGHTER wheel. It does not fight LKAS.**

**`gp-0x6ad6` is a torque-tracking REFERENCE, not a torque added to the motor.** The loop holds the
driver's FELT torque at that target; telling it the plant has more dry friction LOWERS the target
effort, so the PID delivers more motor torque. And Coulomb friction **flips sign at every reversal**,
so a constant error in the estimate is a **step error at every reversal - which is a ratchet.**

## The honest caveat
**V56 muted this exact lane** (`0xC6AFC`/`0xC6AFE` 32768->0) and the memory says it is *"ELIMINATED as
the driver - do not re-propose"*. **That null was scored on `P[15-26 Hz]`, the 20-25 Hz mode, NOT on
6-9 Hz**, and route `24` is not on disk. `0xC6AFC` = 32768 on all 30 other builds, so the corpus
cannot test it. => **the elimination is BAND-SCOPED and has been carried as general.** It is the main
risk to V89's thesis and only a flight settles it.

`gp-0x6b70`'s magnitude response to the dose is unsized - its LERP lives in RAM
(`gp-0x64b8`/`gp-0x641c`), not in the image.
Method: a hand field-split of the `add` chain (Format-VII layout on a Format-I instruction) gave
nonsense. **Ghidra's listing is the authority** - the standing *"assembly CONFIRMS, it does not
FORM"* rule working exactly as written. See [[feedback-decompile-first-then-assembly]].
