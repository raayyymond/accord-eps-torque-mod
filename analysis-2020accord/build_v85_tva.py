#!/usr/bin/env python3
"""build_v85_tva.py -- V85 = V84 + ONE CALIBRATION CELL. The friction RELAY becomes VISCOUS.

🛑 STATUS: BUILT (dry-run by default), UNFLASHED. Writing is gated on `ACCORD_V85_WRITE`; the default
is a DRY RUN that verifies everything -- including a full in-memory .rwd encode/decode -- and writes
nothing. **ONE control cell, TWO bytes. NO new code, NO new RAM, NO new cave extent, NO second hook.**

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
`FUN_0003b8f6`'s FRICTION term is a **Coulomb RELAY**, not a viscous damper. Its normaliser
`0xC40BC` = 600 makes `ratio = clamp(motor_rate * 12 / 600, +-1)` saturate at **|motor rate| = 50
counts**, against the function's own enable gate of **13000** -- so `ratio` is pinned at +-1 across
**99.62%** of its valid input range and IS `sign(motor rate)`. Raising the normaliser to **6000** moves
saturation to **500 counts**, makes the term **linear (viscous) over the whole ordinary driving range**,
and leaves the steady-slew friction **bit-identical above 500 counts**. Describing-function relay index
`N(50)/N(500)`: **7.87 -> 1.00** (Honda's viscous damper = 1.00; V75's engaged-only damper = 1.45;
V80's bang-bang, the worst grinding this kit ever recorded, = **3.27**).
⇒ **V85 removes a relay that is FOUR TIMES more relay-shaped than V80's, and it does it in one cell.**

THE BASE.  `_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin`
  sha256 `344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a`, asserted before a byte
  moves. **This is the cut that FLEW route `6d`.** Its damper package fixed the highway ring (burst duty
  25.1% on V81 -> 2.54% on V84, on 3.4x the exposure) and every one of its cells is FROZEN here by
  operator decision, asserted individually from the BUILT image.

THE EDIT SET -- 1 cell, 2 bytes
--------------------------------------------------------------------------------------------------
  #   cell                       addr      V84     V85     bytes          equals
  1   friction ratio normaliser  0xC40BC   600    6000     5802 -> 7017   NOTHING PREVIOUSLY FLOWN

🛑 **THIS VALUE HAS NEVER BEEN ON THE CAR AND IS NOT A REVERT TO HONDA.** Honda ships 600 and every
build in this kit's history carries 600 (asserted here against STOCK, V38, V67, V81 and V84). That is
stated first, not buried: V85's provenance argument is **structural**, not historical.

THE ARITHMETIC, MIRRORING THE DECOMPILE EXACTLY  (`FUN_0003b8f6` @`0x3b8f6`, task 1 = 1 kHz)
--------------------------------------------------------------------------------------------------
Sole caller `FUN_0002214a` @`0x2240e`, and 🛑 **the `jarl` IS state-guarded**:
`0x2217C shl r15,r11,r25` (r25 = 1 << (state & 0xF)) -> `0x221D6 andi 0x830,r25,r28` ->
`0x2240A cmp r0,r28` / `0x2240C be 0x22412` ⇒ **the function runs only in states {4, 5, 11}.**

    gate  : |gp-0x6b98| <= 0x2000  AND  |gp-0x4f60| <= 0x6400  AND  |gp-0x6abc| <= 13000
            AND gp-0x6752 in {-1,0,1}       -- else the lane emits the 0x7FFF sentinel and
                                               gp-0x6ae2 IS NOT WRITTEN (it holds a STALE value)
    model = EMA2(gp-0x6b98 * polarity / 1024, a=0xC40D4)                  <- DELIVERED MOTOR COMMAND
            + clamp(FIR(EMA2(gp-0x4f60/1024, a=0xC40D8) * 0xC613A/32768), +-15) * LERP(gp-0x6a10)/1024
    iVar20  = polarity * gp-0x6abc * 12                                    @0x3bab0
    ratio   = clamp( iVar20 / cal(0xC40BC), +-1.0 )                        @0x3bab4  <-- THE RELAY
    FRICTION= clamp( EMA(|model|*ratio*cal(0xC40D2=102)/1024
                         + cal(0xC4080=0)/1024*ratio, a=cal(0xC40D0=408)/4096), +-10 )
    gp-0x6ae2 = FRICTION * 1024                                            @0x3bc04   <-- THE FREE TAP
    gp-0x6bfc = clamp( cal(0xC6468=2639) * (model - FRICTION - INERTIA), +-20000 )    @0x3bc1a

⊕ **The FIR is a PASS-THROUGH, measured**: `0xC4048/0xC404C/0xC4050` = f32 `1.0 / 0.0 / 0.0`. And the
torque term is SMALL: `gp-0x4f60/1024 * 1159/32768 * LERP/1024` <= **0.936** at the gate's own 25600
ceiling. ⇒ **`model` is dominated by the delivered command**, exactly as the design assumes.

WHY 6000 AND NOT SOMETHING ELSE
---------------------------------
`ratio` saturates at `cal/12`. The three anchors, all computed here from the image, not quoted:
  · **600 (Honda/V84)** -> saturates at **50** counts ⇒ linear over 0.38% of the valid range,
    relay over **99.62%**. `N(50)/N(500)` = **7.87**.
  · **6000 (V85)**      -> saturates at **500** counts ⇒ `N(50)/N(500)` = **1.00**, i.e. exactly
    viscous everywhere the describing function is evaluated, and **identical to 600 above 500 counts**
    because both saturate there.
  · 12000+ buys nothing further -- `N` is already flat -- and each step costs low-rate dissipation.
500 counts = **106 deg/s** of column rate at 4.7121 ct/(deg/s); route 5d's measured maximum was 1,941
counts (412 deg/s), so 6000 puts the knee comfortably inside the real envelope rather than beyond it.

★ REPRODUCTION: `analysis-2020accord/fun3b8f6_friction_relay.py` computes the same table from the
shipped images. Its row for 600 is `N(25..1000) = 1.000 1.000 0.609 0.253 0.127 0.064`, relay index
**7.87**; for 6000 it is `1.000 1.000 1.000 1.000 1.000 0.609`, relay index **1.00**. This build
re-derives both independently and asserts they agree, so neither file can drift from the other.

GATE 1 -- RAM OWNERSHIP.  **PASS.** [EVIDENCE]
------------------------------------------------
V85 allocates no RAM, adds no instruction outside the already-proven 68-byte cave, grows no extent and
introduces no new writer of anything. The census is re-run **FRESH on the BUILT image**, by TWO
independent methods (`build_v81_tva.census_gp4` = disp16 + disp23 + LE32 absolute literal +
movhi/movea, AND a from-scratch Format-VII byte scan written in this file), on the input, the output
and the `.rwd` readback:
  · `0xC40BC` (= `tp+0x50bc`): **1 reader / 0 writers image-wide.** The reader is `0x3BAB4`,
    `ld.hu 0x50bd[tp],r16` -- **inside `FUN_0003b8f6` itself.** 0 absolute literals, 0 disp23 hits.
    🛑 The displacement encodes as **`0x50BD`**, not `0x50BC`: `ld.hu` carries hw2's LSB as the
    width selector. A scan for `0x50BC` returns ZERO and would have "proved" the cell dead.
  · `gp-0x6abc` (the cave READS it): **4 writers / 16 readers**, every access a `ld.h`/`ld.hu`/`st.h`;
    the 2 six-byte extended-displacement hits (`0x5999C`, `0x599A4`) are confirmed READS in a
    diagnostic byte-packer, not writes. 0 absolute literals, 0 movhi/movea.
  · `gp-0x6ae2` (the cave READS it): **1 writer (`st.h` @`0x3BC04`) / 0 readers** -- the same
    blast-radius-zero class as `gp-0x6ada`. Free telemetry.
  · **The cave WRITES exactly one cell, `gp-0x1514` (the CAN-330 payload byte 4), as it always has.**
  🛑 THE ONE-BIT TRAP, CLOSED ON THE IMAGE: `ld.h` is op `0x39`, `st.h` is op `0x3B`. Both cave loads
  are asserted to be `0x39`, and `gp-0x6ae2`'s only firmware instance is asserted to be `0x3B`.

🛑 **RULE 11 -- IS `0xC40BC` A CLAMP WITH A MONITOR? NO, and here is the proof, not the assertion.**
It is a DIVISOR, not a clamp: the clamp is the `+-1.0` on `ratio`, which V85 does not touch. Its ONLY
reader is the arithmetic site itself, so **no monitor, no lockstep twin and no float mirror can read
it** -- a census of 1 reader / 0 writers settles this by construction. Likewise `gp-0x6ae2` has **zero
readers**, so nothing tests it either. ⊕ For contrast, `0xC407E` -- the cell RULE 11 was written for --
has 3 readers, all inside `FUN_00036c12`, and a float twin at `0xC4004`; V85 asserts it byte-frozen
at Honda's **511**.

GATE 2 -- CLOSED-LOOP STABILITY (MAGNITUDE **AND** PHASE).  Argued honestly, worst news first.
------------------------------------------------------------------------------------------------
🛑 **THE HONEST RISK, STATED FIRST: THIS REMOVES DISSIPATION AT LOW RATE.** The FRICTION term is
subtracted from `model`, i.e. it is dissipative, and below 500 counts V85 delivers **up to 10x less of
it** (**a flat 10x at and below 50 counts**, 5x at 100, 2x at 250, **1x at >=500**). Since 50 counts is
only **10.6 deg/s** of column rate, *most ordinary steering sits in the full-10x regime.* "Less
damping" is not "no effect" --
**V56 muted a lane and the record says it cost damping.** The argument for doing it anyway is that a
**relay** is a limit-cycle generator whose harmonic injection is not clean damping: a memoryless
sign-nonlinearity feeds odd harmonics into a loop that already has a measured 21.09 Hz / 27.4 Hz
resonance, and its describing-function gain RISES as amplitude falls (7.87x from 500 counts down to
50), which is the textbook condition for a stable limit cycle. **That is an argument, not a
measurement**, and the probe below is what turns it into one.
⚠ **The counter-argument, stated so it cannot be discovered later:** if the 6-9 Hz micro-ratchet or the
18-22 Hz grind gets WORSE on V85, the most likely cause is exactly this lost low-rate dissipation, and
reverting is **TWO BYTES**.

  PHASE. **Unchanged, literally.** V85 introduces no filter, no pole, no zero, no delay, no new state,
  no new sample point and no task-order change. `0xC40BC` is a DIVISOR inside a memoryless
  saturation; the EMA that follows it (`0xC40D0` = 408/4096) is untouched, so the lane's only pole is
  bit-identical to V84's. Every pole, zero and task-order relationship in the image is bit-identical.
  [EVIDENCE -- the whole-image identity check below proves no other byte moved.]

  MAGNITUDE. **REDUCED, in one lane, at low rate only**, and by a factor that is exactly
  `min(|rate|/500, 1) / min(|rate|/50, 1)`:
      |rate| counts     10     25     50    100    250    500   1000   1941
      V85 / V84       0.10   0.10   0.10   0.20   0.50   1.00   1.00   1.00
  🛑 **The 10x loss applies at EVERY rate at or below 50 counts, not only at 50** -- both normalisers
  are linear there, but their slopes differ by exactly `cal_old/cal_new` = 0.1. (An earlier draft of
  this header said "unchanged below 50"; the build's own computed table refuted it, which is why the
  table is computed rather than quoted.) At and above **500** counts both saturate and the delivered
  friction is **BIT-IDENTICAL**.

  🛑 **THE ZERO-REJECT CLIFF -- THE BRIEF'S CLAIM IS WRONG IN ONE DIRECTION, AND HERE IS THE REPAIR.**
  The brief reasoned "the edit only ever REDUCES this lane's magnitude, so it cannot newly cross a
  cliff". **FRICTION is SUBTRACTED**, so reducing it can *increase* `|gp-0x6bfc|` whenever FRICTION and
  `model` share a sign. The bound is what saves it, and it is computed here rather than asserted:
  `|dFRICTION| <= 0.0996 * |model|`, so the change in the pre-clamp argument is at most
  `2639 * 0.0996 * |model|` = **263 counts per unit of |model|**, i.e. <= **2,363 counts** at the
  absolute worst case |model| = 8.96 and <= **53 counts** at the measured working point.
  **And the cliff itself cannot be reached at all:** `gp-0x6bfc` has exactly **1 writer (`0x3BC1A`) and
  1 reader (`0x3BC20`)**, and `FUN_0003bc20` emits its `0x7FFF` sentinel iff `|gp-0x6bfc| > 20000` --
  **one count outside the +-20000 clamp applied to the very same value four instructions earlier.**
  ⇒ **the clamped value is untrippable BY CONSTRUCTION**, exactly the `0xC407E`/`0xC4004` interlock
  pattern RULE 11 records, and V85 touches neither the clamp nor the threshold. The ONLY path to the
  sentinel is the enable-gate fail, which V85 does not touch. [EVIDENCE, decompile + 2-method census.]
  ⊕ Downstream saturating clamps (`gp-0x6b70`, `gp-0x6ad4`, the aggregator output, all +-10240) are
  saturating, not zero-rejecting, and are unchanged.

  ⚠ **WHAT GATE 2 DOES NOT COVER.** RULE 8b: a magnitude bound is blind to step size, switching rate
  and phase. The step-size answer here is favourable and is the point of the build -- V85 *removes* a
  discontinuity rather than adding one, and the removed discontinuity is
  `2 * 2639 * 0.0996 * |model|` = **526 counts of instantaneous p-p per unit |model|** at every
  velocity zero-crossing (up to 4,206 counts at |model| = 8). There is no regime in which V85 makes the
  lane switch faster or harder than V84.

★★ THE PROBE -- THE EXISTING 68-BYTE CAVE, REPOINTED. NO NEW EXTENT, NO SECOND HOOK.
---------------------------------------------------------------------------------------
Same hook `0x55C0E`, same `jarl`, same cave base `0xC4B34`, **`CAVE_EXTENT` = 68, NOT GROWN**, same 5
bits of `0x14A` byte4[7:3], same `andi 0x7` preserving the live `STEER_SENSOR_STATUS` bits 2:0, same
displaced-`movea` re-execution, same `jmp [lp]`. This is the repoint V58/V59/V64/V68/V69/V70/V75/V84
have all performed.

| bit | rung | why |
|---|---|---|
| `b7` | `\|gp-0x6abc\| >= 64`  | the OLD saturation point (50) -- **positive control AND scale calibrator** |
| `b6` | `\|gp-0x6abc\| >= 512` | the NEW saturation point (500) -- **high duty here means the relay STILL saturates and the edit under-delivered.** This is what makes a null interpretable |
| `b5` | `\|gp-0x6ae2\| >= 8`   | FRICTION x 1024, HIGH rung |
| `b4` | `\|gp-0x6ae2\| >= 2`   | FRICTION x 1024, LOW rung -- the liveness anchor |
| `b3` | hard-coded **1**       | field-liveness control / build fingerprint |

🛑🛑 **THE ONE DEVIATION FROM THE SPECIFIED BIT MAP, AND IT IS FORCED BY EVIDENCE, NOT BY BYTES.**
The brief specified `b5` = `|gp-0x6b98| > 8192`, the function's own enable gate, on the grounds that the
gate legs are "the mechanism's own thresholds, not guesses". **That leg CANNOT FIRE**, and shipping it
would have spent a rung on a structurally predictable zero -- the exact V64/V68/V69 failure the brief
warns about. Two independent legs, both re-asserted by this build:
  · **STRUCTURAL.** `gp-0x6b98` has 4 writers. The only two that run in the control loop are
    `0x43B52` and `0x43DFC`, both in `FUN_00042af8`, and both store **`r21 = clamp(r14, +-0x2000)`** --
    the clamp is explicit at `0x43B0E` `addi -0x2000,r14,r0` / `0x43B12` `movea 0x2000,r0,r21` /
    `0x43B16` `bgt` / `0x43B1C` `movea -0x2000,r0,r6` / `0x43B20` `cmovle r6,r14,r21`. The gate tests
    `|gp-0x6b98| <= 0x2000` on a value clamped to exactly `+-0x2000` ⇒ **it can never fail.** The other
    two writers (`0x6E104` in `FUN_0006e09a`, `0x6E1DC` in `FUN_0006e140`) are a **caller-less pair of
    actuator-test routines** that disable the control path (`FUN_0006d026(4,1,0)`, `FUN_0005a97c`)
    before writing, and are not reachable while driving.
  · **ON-CAR.** V55's flown 4-bit `gp-0x6b98` probe, route `24`, **n = 69,607 engaged frames / 943 s**:
    **99.2% inside +-512**, and the `|x| >= 3584` level occurred **0.00% of the time.** 8192 is 2.3x
    beyond a level that never occurred in 943 s.
  ⊕ **And the same check retires the brief's b4/b5 staleness caveat and replaces it with the real one.**
  `gp-0x6ae2` is written only on `FUN_0003b8f6`'s success path, so the brief flagged it as stale
  whenever the gate fails. The gate effectively never fails -- **but the CALLER's state guard
  (`andi 0x830,r25,r28` @`0x221D6`) skips the whole function outside states {4, 5, 11}**, and *that* is
  the genuine staleness source. `gp-0x6abc` keeps being written throughout (4 writers, none in
  `FUN_0003b8f6`), so `b7`/`b6` stay live while `b5`/`b4` hold. **Document, do not gate: no bit is
  spent on it, and V70's flown probe already characterised the state distribution.**

★ WHAT THE FREED BYTES BOUGHT: **ALL FOUR RUNGS ARE TWO-SIDED**, symmetric within ONE count.
The arithmetic is exact, not approximate. The 68-byte extent leaves
**68 - 20 (mandatory tail) - 6 (accumulator) = 42 bytes** for all rung logic. Costed:
  · a two-sided rung via `cmp r0 / bge / subr` ABS costs **6 B of ABS** plus 6-8 B of test;
  · the brief's four rungs with ABS come to **60 B**, and even ONE-SIDED they come to **42 B exactly**,
    leaving nothing;
  · the **unsigned-window** form used here -- `add k,r6` / `cmp 2k-1,r6` / `bnh +4` / `add w,r7` -- is
    **8 B and TWO-SIDED**, and consecutive rungs on the same cell share both the load and the shift.
  ⇒ the shipped design is **68 of 68 bytes, four two-sided rungs, zero padding.**
  🛑 That matters because two of the four cells are **DC-biased**: V55 measured `gp-0x6b98` NEGATIVE on
  **59.0%** of frames against 40.1% positive, and `gp-0x6ae2`'s sign follows `sign(polarity * rate)`,
  which is one-signed through any sustained slew. **A one-sided rung on those would have been
  systematically blind through exactly the manoeuvres this build is about.**

**RUNG SIZING -- `T` IS THE ONLY FREE PARAMETER, AND HERE IS ITS ARITHMETIC.**
Steady-state `|gp-0x6ae2| ~= 102 * |model| * min(|rate|/500, 1)` (the EMA at `0xC40D0` = 408/4096 is a
~16 Hz corner at 1 kHz, so it tracks 7.79 Hz at ~0.9 and 21 Hz at ~0.6 -- it shapes the duty, it does
not move the mean). `|model|` is the quantity this lane has **never had a usable measurement of**:
  · term 1 is bounded to **8.0** by the `+-0x2000` clamp, and MEASURED at **< 0.5 on 99.2% of engaged
    frames** (V55, route 24). Working median taken as **|model| ~ 0.2**;
  · term 2 (torque) is bounded to **0.936** by the gate's own 25600 ceiling.
Post-edit, with `|model| = 0.2`:
  · **`b4`, T = 2**  fires ⟺ `|model| * min(|rate|/500,1) >= 0.0196` ⟺ **|rate| >= 49 counts (10 deg/s)**
    ⇒ **predicted duty 35-70%** -- it is the liveness anchor and the smallest threshold safely above
    the integer LSB.
  · **`b5`, T = 8**  fires ⟺ `>= 0.0784` ⟺ **|rate| >= 196 counts (42 deg/s)**
    ⇒ **predicted duty 10-25%.**
**WHAT THEY WOULD HAVE READ ON V84** (where `ratio ~= +-1` for `|rate| >= 50`), same `|model|`:
  · `b4`: fires whenever `|model| >= 0.0196`, i.e. `|gp-0x6b98| >~ 20` ⇒ **~85-95%**;
  · `b5`: fires whenever `|model| >= 0.0784`, i.e. `|gp-0x6b98| >~ 80` ⇒ **~55-80%**.
⇒ **the pair should FALL 2-4x (b4) and 3-6x (b5) if the edit is in force.** That is the dose readout,
and it is measured against V85's OWN rate rungs rather than against a build we cannot re-fly.
⚠ **[BELIEF]** on the duty numbers -- `|model|`'s median is an inference from a 1.5-bit probe. **[EVIDENCE]**
on the thresholds, the transfer law and the bounds. This probe is what converts the first to the second.

★ A FREE THREE-POINT INVERSION FOR `|model|`, at no extra bytes. On V85, `b4` fires at
`|rate| >= 9.80/|model|`, `b5` at `|rate| >= 39.2/|model|`; `b7` fires at 64 and `b6` at 512. Equating
them brackets `|model|` at **0.0766 / 0.153 / 0.613**: if `b4 duty > b7 duty` then `|model| > 0.153`,
if `b5 duty > b7 duty` then `|model| > 0.613`, if `b5 duty > b6 duty` then `|model| > 0.0766`.
⚠ `|rate|` and `|model|` are correlated, so this is a **ranking, not a point estimate.** Say so.

★★ TWO FREE STRUCTURAL SELF-CHECKS THE DECODER MUST RUN, AND THEY ARE EXACT (NO SAMPLING RACE).
`b6 => b7` and `b5 => b4`, because each pair is computed from the **same register in the same pass**.
Unlike V84's `bit4 => bit5` (two different cells, one task period apart), these admit **zero**
violations. A single violating frame means the decoder or the image is wrong. **V84 cannot satisfy
them**: its `b7`/`b6` were `gp-0x6ada >= +1024` and `<= -1025`, mutually EXCLUSIVE, never nested.

**BUILD IDENTITY, WITH NO FREE PARAMETER.** V84's observed field alphabet on route `6d` is exactly
`{0x2F, 0x3F}` -- `b7` and `b6` were identically **0 for all 68,236 frames**. V85's `b7` fires at
`|motor rate| >= 64` counts = **13.6 deg/s**, which occurs constantly in motion. ⇒ **any frame with b7
set proves the log is not V84**, and a `b7` duty above 1% is impossible for V84 at
`P ~ 0`. The nesting invariants above are a second, independent discriminator. `b3` = 1 on every pass
is the third (field liveness). **Three tests, no fitted parameter.**

CRC.  `0xC40BC` and the cave at `0xC4B34` are BOTH inside the block **[0x013000, 0x0C4FFC)**, whose
trailer is at **0x0C4FFC**. ⇒ **exactly ONE block moves**, derived by `V53.owning_block` and asserted
against that literal, never observed. Full 50/50 chain re-walked on the built image and on the
`.rwd` readback.

🛑 WHAT V85 DOES **NOT** ADDRESS -- said plainly so it cannot be discovered later
-----------------------------------------------------------------------------------
  · **It is not a rate-lane lever and carries no new S1 dose.** V84's Lever B is carried unchanged;
    if V84's pre-registered S1 falsifier fired, V85 does not repair it and does not claim to.
  · **The ~28 Hz lane-change transient.** Measured DOSE-INDEPENDENT, full amplitude on the stock rate
    lane ⇒ **excitation, not gain.**
  · **The operator's hard constraint is respected**: the edit reduces a lane that OPPOSES motion, so it
    can only RAISE, never lower, the maximum commandable steering angular velocity.

★ PRE-REGISTERED, FALSIFIABLE -- recorded BEFORE the drive, on purpose
------------------------------------------------------------------------
  **S4, excess friction / impedance under max command:** expect a **lighter, less notchy** wheel at low
  rate, engaged AND manual (the cell is MODE-PROOF -- a bare `tp` scalar with no mode index, so it is
  live in both). This is the one prediction the operator can falsify by feel alone.
  **S2, micro-ratchet (7.79 Hz):** the relay's harmonic injection is the mechanism this build attacks.
  🛑 **IF S2 DOES NOT IMPROVE, THE "FRICTION RELAY DRIVES THE MICRO-RATCHET" HYPOTHESIS IS FALSIFIED**
  and `0xC40BC` should be reverted rather than dosed further -- `N` is already flat at 6000, so there
  is no larger dose to try.
  **S1/grind #1 and the ring:** **GENUINELY UNCERTAIN.** [BELIEF] only.
  **THE PROBE'S OWN FALSIFIER:** if `b6` duty is HIGH (say > 30%), the relay still saturates most of
  the time and the edit under-delivered; if `b4`/`b5` read ~0, the tap or the state guard is the story,
  not the lever.
  ⊕ **Ship this instruction with the drive** (RULE 9, costs no bytes): **~90 s of deliberate ENGAGED
  hard cornering at creep**, to take grind #2's P(0) from ~0.61 to < 0.05 in one drive.

Usage:
    python build_v85_tva.py                            # DRY RUN, verifies everything, writes nothing
    ACCORD_V85_WRITE=rwd python build_v85_tva.py       # writes the plain image AND the flashable .rwd
"""
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, START/END, encoders)
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v54_tva as V54                # noqa: E402  (shl, andi, or_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldh, cmp_imm5, ldbu_any encoders)
import build_v67_tva as V67                # noqa: E402  (Lever B's repoint + guards)
import build_v68_tva as V68                # noqa: E402  (cave geometry)
import build_v72_tva as V72                # noqa: E402  (CAVE_EXTENT, 0xC63A0 census)
import build_v74_tva as V74                # noqa: E402  (record readers, censuses, mode columns)
import build_v75_tva as V75                # noqa: E402  (addi5, ldhu_gp, cave helpers)
import build_v81_tva as V81                # noqa: E402  ★ census_gp4 -- the kit's 4-method gp census
import build_v84_tva as V84B               # noqa: E402  ★ THE BASE's builder -- every frozen guard
import scan_gp_accesses as SCAN            # noqa: E402  (the INDEPENDENT Format-VII decoder)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
CAVE_BASE = V68.CAVE_BASE                          # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT                      # 68 -- the PROVEN extent. Never grow it.
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
TP = 0xBF000
GP, TPREG = 4, 5

u16, s16, u32 = V75.u16, V75.s16, V75.u32

# =====================================================================================================
# THE BASE -- V84, the cut that flew route 6d
# =====================================================================================================
SRC_BIN = plain_image_path(
    "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin")
SRC_SHA256 = "344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a"
NOT_THE_BASE = {  # sha256 -> why it must never be accepted
    "bdd857c942cab37a26b7d78e4c76cefeec054b33fc46d887d448291e15ab2825":
        "the SUPERSEDED control-path-only V84 cut. It never flew and it carries V75's damper "
        "magprobe cave, which V84's own edits drive to a structurally predictable zero.",
    "bb717ce8322d35c587e95084e697a5ad98ba6564ee9265bb09a88a2a241cd25a":
        "_v83a -- V84's OWN base. It carries the engaged-only damper V84 deleted.",
    "4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b":
        "_v81 -- two builds back.",
    "e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c":
        "_v75_CY0.566-EX1.200_magprobe -- it carries 0xC407E = 850, the DTC-0x1d fault mechanism.",
}
STOCK_BIN = stock_fw_path("code.bin")
# ⊕ the provenance anchors -- 0xC40BC is asserted 600 on ALL of them, so "never flown" is measured.
NEVER_FLOWN_ANCHORS = {
    "STOCK": (STOCK_BIN, None),
    "V38": (plain_image_path("_v38_plain_image.bin"), None),
    "V67": (plain_image_path("_v67_plain_image.bin"),
            "5e01bcc4b34a52831fd524cb9af765a01a8dfa3e2c4782d81b3efcb6c94f8c96"),
    "V68": (plain_image_path("_v68_plain_image.bin"),
            "9106044abc835529b014d6204904c86bc0587fab4a55facd08d77a84cd0c6226"),
    "V81": (plain_image_path("_v81_C407E.511-FRICTION.STOCK_plain_image.bin"),
            "4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b"),
}

# =====================================================================================================
# THE EDIT -- (addr, width, V84 value to ASSERT, value to WRITE, label)
# =====================================================================================================
RATIO_NORM_ADDR = 0xC40BC                       # tp+0x50bc
RATIO_NORM_OLD, RATIO_NORM_NEW = 600, 6000
RATIO_NORM_DISP = 0x50BC                        # 🛑 the `ld.hu` encodes it as 0x50BD (disp | 1)
RATIO_NORM_DISP_ENC = 0x50BD
RATIO_NORM_READER = 0x3BAB4                     # the ONLY reader image-wide
RATE_MUL = 12                                   # `iVar20 = polarity * gp-0x6abc * 12`  @0x3bab0
RATE_ENABLE_GATE = 13000                        # the function's own |gp-0x6abc| bound

EDITS = ((RATIO_NORM_ADDR, 2, RATIO_NORM_OLD, RATIO_NORM_NEW, "friction ratio normaliser"),)

# =====================================================================================================
# 🛑 FROZEN BY OPERATOR DECISION -- V84's damper package is what fixed the highway ring.
# Asserted individually from the BUILT image; the build FAILS if any one differs.
# =====================================================================================================
FROZEN_CELLS = {
    0xD77DA: (0,    "FactorC mode-26 Y[0] -> Honda. The engaged-only damper, DELETED at V84."),
    0xD77EE: (0,    "FactorC mode-27 Y[0] -> Honda."),
    0xD7822: (60,   "FactorE mode-27 X[0] -> Honda."),
    0xD7824: (400,  "FactorE mode-27 X[1] -> Honda."),
    0xD782C: (140,  "FactorE mode-27 Y[1] -> Honda."),
    0xC6446: (5244, "Lever B's r24 engaged arm -- the FLOWN V67/V68 value."),
    0xC6444: (512,  "r26's engaged arm -- STOCK, deliberately, as the S3 lever."),
    0xC407E: (511,  "🛑 THE DTC-0x1d INTERLOCK. Honda's clamp, ONE count under its own 512 trip."),
    0xC6CD0: (3564, "V57's decoupled forward-reader cell -- the 4x LKAS setpoint. INTACT."),
    0xC63A0: (1024, "the Path-2 damper weight. Honda's."),
}
FROZEN_BYTES = {
    0x3AA96: (0xFB, "Lever B's gate repoint -- the FLOWN V67/V68 byte."),
    0x454FE: (0xB5, "V42's macro-ratchet fix (`br` not `bne`). Lost twice already; KEEP."),
}
# the friction-lane cals the arithmetic depends on -- if any moves, every number above is void
LANE_CALS = {
    0xC40D0: (408,  "friction EMA alpha /4096 -- the lane's ONLY pole. UNTOUCHED (phase gate)."),
    0xC40D2: (102,  "friction scale /1024."),
    0xC4080: (0,    "friction constant /1024 -- zero, so FRICTION is purely |model|-proportional."),
    0xC40D4: (573,  "command EMA alpha /4096."),
    0xC40D6: (246,  "inertia EMA alpha /4096."),
    0xC40D8: (3686, "torque EMA alpha /4096."),
    0xC613A: (1159, "torque scale /32768."),
    0xC6468: (2639, "output scale on gp-0x6bfc."),
    0xC646E: (1428, "INERTIA gain."),
}
LANE_FLOATS = {0xC4048: 1.0, 0xC404C: 0.0, 0xC4050: 0.0}    # the FIR taps -- a PASS-THROUGH
CMD_GATE = 0x2000            # |gp-0x6b98| <= 0x2000, and gp-0x6b98 is CLAMPED to exactly +-0x2000
TORQUE_GATE = 0x6400         # |gp-0x4f60| <= 0x6400
OUT_CLAMP = 20000            # |gp-0x6bfc| clamp -- and FUN_0003bc20's sentinel test is > 20000
LERP_MIN, LERP_MAX = 899, 1084                 # the gp-0x6a10 LERP's Y range, read from the image
RATE_COUNTS_PER_DEG_S = 4.7121

# ---- the b5 refutation, as addresses so it is checkable ---------------------------------------------
CMD_WRITERS = (0x43B52, 0x43DFC, 0x6E104, 0x6E1DC)
CMD_CLAMP_SITES = {0x43B0E: bytes.fromhex("0e0600e0"),      # addi -0x2000,r14,r0
                   0x43B12: bytes.fromhex("20ae0020"),      # movea 0x2000,r0,r21
                   0x43B16: bytes.fromhex("ff05"),          # bgt
                   0x43B1C: bytes.fromhex("203600e0"),      # movea -0x2000,r0,r6
                   0x43B20: bytes.fromhex("e6772eab")}      # cmovle r6,r14,r21
CALLER_GUARD = {0x2217C: bytes.fromhex("ef5fc2c8"),         # shl r15,r11,r25  (r25 = 1 << state)
                0x221D6: bytes.fromhex("d9e63008"),         # andi 0x830,r25,r28
                0x2240A: bytes.fromhex("e0e1"),             # cmp r0,r28
                0x2240C: bytes.fromhex("b205"),             # be  0x22412  -> SKIPS the jarl
                0x2240E: bytes.fromhex("81ffe894")}         # jarl 0x3b8f6,lp
CALLER_GUARD_MASK = 0x830                                   # states {4, 5, 11}
# gp-0x6bfc's cliff: 1 writer, 1 reader, and the reader's threshold is OUTSIDE the writer's clamp
OUT_CELL_WRITER, OUT_CELL_READER = 0x3BC1A, 0x3BC20

# =====================================================================================================
# THE PROBE -- the EXISTING 68-byte cave, REPOINTED. 🛑 CAVE_EXTENT IS NOT GROWN.
# =====================================================================================================
R0, R6, R7 = 0, 6, 7
PAYLOAD_BYTE4_DISP = V75.PAYLOAD_BYTE4_DISP        # 0x1514 -- CAN-330 byte 4
PAYLOAD_KEEP_MASK = V75.PAYLOAD_KEEP_MASK          # 0x7 -- live STEER_SENSOR_STATUS bits 2:0
HOOK_RETURN_INSN = V75.HOOK_RETURN_INSN            # `mov 0x8,r7` -- proves r7 is DEAD across the hook

RATE_DISP = 0x6ABC           # motor rate -- the RELAY's input. SIGNED. 4 writers / 16 readers
FRIC_DISP = 0x6AE2           # FRICTION*1024 -- SIGNED. 1 writer (0x3BC04 st.h) / 0 readers. FREE.
FRIC_WRITER = 0x3BC04
OP_LDH, OP_STH = 0x39, 0x3B  # 🛑 ONE BIT APART

# ---- V850 condition codes ---------------------------------------------------------------------------
COND_BNH = 0x3               # unsigned <=  (CY or Z). Pinned to `bnh` @0x2784E below.
BR_SKIP = 4                  # every rung's branch skips exactly one 2-byte `add`
BNH_PIN_ADDR = 0x2784E       # a real `bnh +4` in the stock image -- byte-identical to our emitter
SAR_PIN_SITES = {0x3AB76: (0xA, R6), 0x3AC20: (0xA, 8)}    # real `sar 0xa,rN` -- pins the emitter

# ---- the rungs, as WINDOW tests: fire <=> value OUTSIDE [-k, k-1] ⇒ |value| >= k within ONE count ----
RATE_SHIFT = 6                                  # `sar 0x6` -- ARITHMETIC, sign preserved
RATE_K_LO, RATE_K_HI = 1, 8                     # on q = rate >> 6  ⇒ 64 and 512 counts
RATE_T_LO = RATE_K_LO << RATE_SHIFT             # 64
RATE_T_HI = RATE_K_HI << RATE_SHIFT             # 512
FRIC_T_LO, FRIC_T_HI = 2, 8                     # on the raw halfword -- no shift
BIT_RATE_LO, BIT_RATE_HI = 0x80, 0x40           # b7, b6
BIT_FRIC_HI, BIT_FRIC_LO = 0x20, 0x10           # b5, b4
BIT_FINGERPRINT = 0x08                          # b3
W_B7, W_B6, W_B5, W_B4, HI_SHIFT = 8, 4, 2, 1, 4    # pre-shift weights, then `shl 0x4`
M32 = 0xFFFFFFFF

# ---- what the mechanism's own numbers are, so the rungs can be checked against them -----------------
OLD_SAT = RATIO_NORM_OLD // RATE_MUL            # 50
NEW_SAT = RATIO_NORM_NEW // RATE_MUL            # 500

# ---- GATE 1's cells for the probe: (disp, firmware writers, firmware readers, why) ------------------
PROBE_CELLS = (
    (RATE_DISP, 4, 16, "motor rate -- the RELAY's own input, READ by the cave"),
    (FRIC_DISP, 1, 0, "FRICTION x 1024 -- 1 writer / 0 readers, READ by the cave. FREE telemetry"),
)
# the 48-bit disp23 accesses each probe cell has, BY ADDRESS -- both are READS in a diagnostic packer
PROBE_DISP23 = {RATE_DISP: (0x5999C, 0x599A4), FRIC_DISP: ()}

# =====================================================================================================
# OUTPUT NAMING -- 🛑 exactly ONE flashable .rwd and ONE plain image per build number on disk
# =====================================================================================================
# 🛑 THE SEPARATOR IS `.`/`-`, NEVER `+`: the Ghidra MCP layer once URL-decoded a `+` to a SPACE.
# 🛑 THE PROBE IS IN THE NAME, IN **BOTH** FILENAMES -- V85's cave measures entirely different cells
# 🛑 from V84's, and a name that still said `6ada` would be a lie on the shelf.
VARIANT_TOKEN = "FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2"
TAG = f"V84BASE-{VARIANT_TOKEN}"
BIN_OUT = str(plain_image_path(f"_v85_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V85-{TAG}-0x{START:X}-0x{END:X}.rwd")

WRITE_MODE = os.environ.get("ACCORD_V85_WRITE", "").strip().lower()
assert WRITE_MODE in ("", "none", "bin", "rwd"), \
    f"ACCORD_V85_WRITE={WRITE_MODE!r} -- expected '' (dry run), 'bin' or 'rwd'"


# =====================================================================================================
# THE RELAY, AS ARITHMETIC -- reproduced here, and cross-checked against fun3b8f6_friction_relay.py
# =====================================================================================================

def ratio(rate_counts, norm):
    """`clamp(polarity * gp-0x6abc * 12 / cal, +-1)` at polarity = +1. @0x3bab0 / @0x3bab4."""
    return max(-1.0, min(1.0, RATE_MUL * rate_counts / float(norm)))


def describing_function(amp_counts, norm, nharm=4096):
    """Fundamental-harmonic gain of `clamp(x, +-1)` driven by `x = (12*R/norm) sin(th)`, normalised
    by the input scale so a purely linear (viscous) term returns exactly 1.0.

    **Constant `N` over `R` = viscous = stabilising; `N` rising as amplitude falls = RELAY = a
    limit-cycle generator.** Computed by quadrature here, and cross-checked against the closed form
    so neither can be silently wrong.
    """
    a = RATE_MUL * amp_counts / float(norm)
    if a <= 0:
        return 1.0
    acc = 0.0
    for k in range(nharm):
        th = 2.0 * math.pi * (k + 0.5) / nharm
        acc += max(-1.0, min(1.0, a * math.sin(th))) * math.sin(th)
    return abs(2.0 / nharm * acc) / a


def describing_function_closed(amp_counts, norm):
    """The analytic form -- the SECOND method. `fun3b8f6_friction_relay.py` uses exactly this."""
    a = RATE_MUL * amp_counts / float(norm)
    if a <= 1.0:
        return 1.0
    return (2.0 / math.pi) * (math.asin(1.0 / a) + (1.0 / a) * math.sqrt(1.0 - 1.0 / a ** 2))


def relay_index(norm):
    """`N(50)/N(500)`. 1.00 = viscous · V75's damper = 1.45 · V80's bang-bang = 3.27."""
    return describing_function_closed(50, norm) / describing_function_closed(500, norm)


def assert_relay_arithmetic():
    """🛑 CALIBRATE THE INSTRUMENT BEFORE USING IT -- two independent implementations must agree."""
    for norm in (RATIO_NORM_OLD, RATIO_NORM_NEW, 1200, 3000, 12000):
        for r in (25, 50, 100, 250, 500, 1000):
            q, c = describing_function(r, norm), describing_function_closed(r, norm)
            assert abs(q - c) < 2e-3, \
                f"🛑 the describing function disagrees with its closed form at N({r}) norm={norm}: " \
                f"{q:.5f} vs {c:.5f} -- the INSTRUMENT is wrong, not the build"
    ri_old, ri_new = relay_index(RATIO_NORM_OLD), relay_index(RATIO_NORM_NEW)
    assert abs(ri_old - 7.87) < 0.01, f"the OLD relay index re-derives as {ri_old}, expected 7.87"
    assert abs(ri_new - 1.00) < 1e-9, f"the NEW relay index re-derives as {ri_new}, expected 1.00"
    # the saturation points, from the cal alone
    assert OLD_SAT == 50 and NEW_SAT == 500
    assert abs(ratio(OLD_SAT, RATIO_NORM_OLD)) == 1.0 and abs(ratio(OLD_SAT - 1, RATIO_NORM_OLD)) < 1.0
    assert abs(ratio(NEW_SAT, RATIO_NORM_NEW)) == 1.0 and abs(ratio(NEW_SAT - 1, RATIO_NORM_NEW)) < 1.0
    # ⇒ identical at and above the OLD saturation only when BOTH saturate, i.e. >= 500
    for r in (500, 1000, 1941, 13000):
        assert ratio(r, RATIO_NORM_OLD) == ratio(r, RATIO_NORM_NEW) == 1.0, \
            f"🛑 at |rate| = {r} the two normalisers do NOT agree -- the 'unchanged above 500' claim"
    # 🛑 BELOW the old saturation BOTH are linear -- but with slopes 10x apart, so the ratio is 0.1
    # 🛑 there, NOT 1.0. This assert exists because the header's first draft claimed 1.0.
    for r in (1, 10, 25, 49, 50):
        assert abs(ratio(r, RATIO_NORM_NEW) / ratio(r, RATIO_NORM_OLD) - 0.1) < 1e-12, \
            "below 50 counts BOTH are linear, so V85/V84 is exactly cal_old/cal_new = 0.1"
    return ri_old, ri_new


def dose_ratio(rate_counts):
    """V85 / V84 for the delivered FRICTION magnitude at a given |motor rate|."""
    a, b = ratio(rate_counts, RATIO_NORM_OLD), ratio(rate_counts, RATIO_NORM_NEW)
    return b / a if a else 1.0


# =====================================================================================================
# THE CAVE
# =====================================================================================================

def sar_imm5(imm5, reg2):
    """Format II `sar imm5,reg2`, opcode 0x15. 🛑 ARITHMETIC -- `shr` (0x14) would turn every negative
    rate into a huge positive and the thermometer would read ~100% duty forever."""
    assert 0 <= imm5 <= 31 and 0 <= reg2 < 32
    return struct.pack("<H", (reg2 << 11) | (0x15 << 5) | imm5)


def assert_probe_encoders(stock):
    """🛑 EVERY halfword the cave emits is PINNED to a real instruction in the STOCK image."""
    for addr, (imm, reg) in SAR_PIN_SITES.items():
        assert sar_imm5(imm, reg) == bytes(stock[addr:addr + 2]), \
            f"the `sar` emitter gives {sar_imm5(imm, reg).hex()}, the image's site @0x{addr:05X} is " \
            f"{bytes(stock[addr:addr + 2]).hex()}"
    assert (struct.unpack("<H", sar_imm5(RATE_SHIFT, R6))[0] >> 5) & 0x3F == 0x15, \
        "🛑 the emitted shift is not opcode 0x15 (`sar`) -- 0x14 is `shr` and would INVERT the rung"
    # 🛑 `bnh` is the ONLY condition new to this kit's caves, and it is pinned BYTE-IDENTICAL
    bnh = FF.bcond(COND_BNH, BR_SKIP)
    assert bnh == bytes(stock[BNH_PIN_ADDR:BNH_PIN_ADDR + 2]), \
        f"🛑 the `bnh +4` emitter gives {bnh.hex()}, the stock image's `bnh` @0x{BNH_PIN_ADDR:05X} " \
        f"is {bytes(stock[BNH_PIN_ADDR:BNH_PIN_ADDR + 2]).hex()}"
    hw = struct.unpack("<H", bnh)[0]
    assert (hw >> 7) & 0xF == 0xB and (hw & 0xF) == COND_BNH, "the `bnh` emitter is not Format III/0x3"
    # the two loads must be `ld.h` (SIGNED), never `ld.hu`, and never `st.h`
    for disp in (RATE_DISP, FRIC_DISP):
        raw = V55.ldh(disp, R6)
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        assert op == OP_LDH, f"🛑 the gp-0x{disp:04x} access is opcode 0x{op:02X}, not `ld.h` 0x39"
        assert struct.unpack_from("<H", raw, 2)[0] % 2 == 0, \
            f"🛑 gp-0x{disp:04x}'s hw2 LSB is SET -- that selects a different width class"


def build_cave():
    """pack_v85_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

    Every rung is an UNSIGNED WINDOW test. For a signed value `v` and a window half-width `k`:
        fire  <=>  v NOT in [-k, k-1]  <=>  (unsigned)(v + k) > 2k - 1
    which is `add k,r6` / `cmp 2k-1,r6` / `bnh +4` / `add w,r7` -- **8 bytes and TWO-SIDED**, with
    trip points at `+k` and `-(k+1)`, i.e. symmetric within ONE count. Consecutive rungs on the same
    cell share the load AND the offset already in r6, so the second costs the same 8 bytes.

        mov   0x0,r7            ; r7 = 0
        ld.h  -0x6abc[gp],r6    ; ★★★★ MOTOR RATE -- the RELAY's own input. SIGNED (op 0x39)
        sar   0x6,r6            ; q = rate >> 6, ARITHMETIC -- sign PRESERVED
        add   0x1,r6            ; q + 1
        cmp   0x1,r6
        bnh   +4                ; UNSIGNED <= 1  <=>  q in {-1,0}  <=>  rate in [-64, 63]
        add   0x8,r7            ; b7 = |rate| >= 64      (trips +64 / -65)
        add   0x7,r6            ; q + 8
        cmp   0xf,r6
        bnh   +4                ; UNSIGNED <= 15 <=>  q in [-8,7]  <=>  rate in [-512, 511]
        add   0x4,r7            ; b6 = |rate| >= 512     (trips +512 / -513)
        ld.h  -0x6ae2[gp],r6    ; ★★ FRICTION x 1024 -- 1 writer, 0 readers, blast radius ZERO
        add   0x8,r6            ; f + 8
        cmp   0xf,r6
        bnh   +4                ; f in [-8, 7]
        add   0x2,r7            ; b5 = |fric| >= 8       (trips +8 / -9)
        add   -0x6,r6           ; f + 2
        cmp   0x3,r6
        bnh   +4                ; f in [-2, 1]
        add   0x1,r7            ; b4 = |fric| >= 2       (trips +2 / -3)
        shl   0x4,r7            ; the 4-bit thermometer -> bits 7:4
        add   0x8,r7            ; bit3 = 1, THE BUILD FINGERPRINT, weight 8 POST-shift
        ld.bu -0x1514[gp],r6    ; CAN-330 payload byte4
        andi  0x7,r6,r6         ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6             ; THE MERGE. 🛑 not `or r6,r7`
        st.b  r6,-0x1514[gp]    ; THE ONLY STORE
        movea -0x1518,gp,r6     ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
        exactly 68 bytes -- the PROVEN extent, filled, with NO padding.
    """
    body, listing = bytearray(), []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    def window(off, half, weight, label):
        """`add off,r6` / `cmp 2*half-1,r6` / `bnh +4` / `add weight,r7`. Returns the rung's index."""
        assert -16 <= off <= 15, f"the window offset {off} is outside Format II's signed imm5"
        assert 1 <= half <= 8, f"half-width {half} needs cmp {2 * half - 1}, outside imm5's +15"
        idx = len(listing)
        emit(V75.addi5(off, R6), f"add {off:#x},r6".replace("0x-", "-0x") +
             f"            ; window offset -> +{half}")
        emit(V55.cmp_imm5(2 * half - 1, R6), f"cmp {2 * half - 1:#x},r6            ; window width")
        emit(FF.bcond(COND_BNH, BR_SKIP), "bnh +4               ; UNSIGNED <= : inside the window")
        emit(V75.addi5(weight, R7), f"add {weight:#x},r7            ; {label}")
        return idx

    emit(FF.movi5(0, R7), "mov 0x0,r7           ; r7 = 0")
    emit(V55.ldh(RATE_DISP, R6),
         f"ld.h -0x{RATE_DISP:04x}[gp],r6  ; ★★★★ MOTOR RATE, the RELAY's input (SIGNED, op 0x39)")
    emit(sar_imm5(RATE_SHIFT, R6),
         f"sar 0x{RATE_SHIFT:x},r6            ; q = rate >> {RATE_SHIFT}, ARITHMETIC (op 0x15)")
    r_lo = window(RATE_K_LO, RATE_K_LO, W_B7, f"b7 = |rate| >= {RATE_T_LO}")
    r_hi = window(RATE_K_HI - RATE_K_LO, RATE_K_HI, W_B6, f"b6 = |rate| >= {RATE_T_HI}")
    emit(V55.ldh(FRIC_DISP, R6),
         f"ld.h -0x{FRIC_DISP:04x}[gp],r6  ; ★★ FRICTION x 1024 (SIGNED; 1 writer / 0 readers)")
    f_hi = window(FRIC_T_HI, FRIC_T_HI, W_B5, f"b5 = |fric| >= {FRIC_T_HI}")
    f_lo = window(FRIC_T_LO - FRIC_T_HI, FRIC_T_LO, W_B4, f"b4 = |fric| >= {FRIC_T_LO}")
    emit(V54.shl(HI_SHIFT, R7), f"shl 0x{HI_SHIFT:x},r7            ; the thermometer -> bits 7:4")
    emit(V75.addi5(BIT_FINGERPRINT, R7),
         f"add 0x{BIT_FINGERPRINT:x},r7            ; bit3 = 1, THE FINGERPRINT (POST-shift)")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6       ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6             ; THE MERGE  🛑 NOT `or r6,r7`")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]  ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6  ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]             ; -> 0x55C12")

    # ---- 🛑 FLAG LIVENESS: every branch reads its OWN cmp's flags, and nothing sits between --------
    for idx, what in ((r_lo, "rate LOW"), (r_hi, "rate HIGH"),
                      (f_hi, "friction HIGH"), (f_lo, "friction LOW")):
        assert ((struct.unpack("<H", listing[idx][1])[0] >> 5) & 0x3F) == 0x12, \
            f"the {what} rung does not start with an `add imm5`"
        assert ((struct.unpack("<H", listing[idx + 1][1])[0] >> 5) & 0x3F) == 0x13, \
            f"the {what} rung's second instruction is not a `cmp imm5`"
        for k in range(3):
            assert listing[idx + k][0] + 2 == listing[idx + k + 1][0], \
                f"the {what} add/cmp/bnh/add quadruple is not contiguous -- STALE flags"
        hw = struct.unpack("<H", listing[idx + 2][1])[0]
        assert (hw >> 7) & 0xF == 0xB and (hw & 0xF) == COND_BNH, \
            f"🛑 the {what} rung's branch is not `bnh` -- a SIGNED condition would leak negatives"

    # ---- GATE 2a: EVERY branch lands EXACTLY on an emitted instruction boundary -------------------
    bounds = {a for a, _r, _t in listing}
    branches = [(a, r) for a, r, _t in listing
                if len(r) == 2 and (struct.unpack("<H", r)[0] >> 7) & 0xF == 0xB]
    assert len(branches) == 4, f"the cave has {len(branches)} Bcond(s), expected exactly 4"
    for a, raw in branches:
        hw = struct.unpack("<H", raw)[0]
        d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)      # decoded from the field split
        d -= 0x200 if d & 0x100 else 0
        assert d == BR_SKIP, f"the branch at 0x{a:05X} has displacement {d}, expected +{BR_SKIP}"
        assert a + d in bounds, \
            f"🛑 the branch at 0x{a:05X} lands at 0x{a + d:05X}, which is NOT an instruction boundary"
    # ---- exactly ONE store, and it is the payload ------------------------------------------------
    stores = [(a, r, t) for a, r, t in listing
              if len(r) == 4 and ((struct.unpack_from("<H", r, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert len(stores) == 1 and \
        ((struct.unpack_from("<H", stores[0][1], 0)[0] >> 5) & 0x3F) == 0x3A, \
        f"the cave contains {len(stores)} store(s), expected exactly ONE `st.b` to the CAN-330 payload"
    # ---- 🛑 the ONE-BIT trap: BOTH our accesses must be LOADS (0x39), not STORES (0x3B) -----------
    for disp in (RATE_DISP, FRIC_DISP):
        raw = V55.ldh(disp, R6)
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        assert op == OP_LDH, \
            f"🛑 the gp-0x{disp:04x} access is opcode 0x{op:02X}, not 0x{OP_LDH:02X} (`ld.h`). " \
            f"0x{OP_STH:02X} is `st.h` -- ONE BIT away -- and it would CLOBBER the cell."
    assert len(body) == CAVE_EXTENT == 68, \
        f"the cave body is {len(body)} bytes; the PROVEN extent is {CAVE_EXTENT} and must be filled " \
        "exactly -- never grown, and any shortfall would leave stale V84 bytes executing"
    return bytes(body), listing


def redisassemble_v85_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, from raw bytes, self-contained.

    🛑 The readback's INDEPENDENT witness. `assert_decoder_calibrated` checks it against V75's own
    decoder on V75's own cave first, so it cannot be silently wrong.
    """
    out, i = [], 0
    while i < len(raw):
        hw = struct.unpack_from("<H", raw, i)[0]
        op6 = (hw >> 5) & 0x3F
        reg2, reg1 = hw >> 11, hw & 0x1F
        if hw == 0xFFFF:
            n, m = 2, "(pad 0xffff)"
        elif hw == 0x0000:
            n, m = 2, "nop"
        elif (hw >> 7) & 0xF == 0xB:                                      # Format III Bcond
            n = 2
            m = {0x6: "blt", 0xE: "bge", 0xA: "bne", 0x2: "be", 0xB: "bh", 0xF: "bgt",
                 0x1: "bl", 0x3: "bnh", 0x9: "bnl"}.get(hw & 0xF, f"b?{hw & 0xF:x}")
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            m = f"{m} {d:+d}"
        elif op6 in (0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F, 0x31, 0x36):
            n = 4
            hw2 = struct.unpack_from("<H", raw, i + 2)[0]
            disp = hw2 - 0x10000 if hw2 & 0x8000 else hw2
            m = {0x39: "ld.h", 0x3A: "st.b", 0x3B: "st.h", 0x3C: "ld.bu", 0x3D: "ld.bu",
                 0x3F: "ld.hu" if hw2 & 1 else "ld.w", 0x31: "movea", 0x36: "andi"}[op6]
            if op6 in (0x31, 0x36):
                m = f"{m} 0x{hw2:04x},r{reg1},r{reg2}"
            else:
                eff = (disp & ~1) | (op6 & 1 if op6 in (0x3C, 0x3D) else 0) \
                    if op6 in (0x3C, 0x3D, 0x3F) else disp
                m = (f"{m} r{reg2},{eff}[r{reg1}]" if op6 in (0x3A, 0x3B)
                     else f"{m} {eff}[r{reg1}],r{reg2}")
        elif hw == 0x007F or (op6 == 0x03 and reg2 == 0):
            n, m = 2, "jmp [lp]"
        elif op6 in (0x10, 0x12, 0x13):
            v = (hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F              # imm5 is SIGN-extended
            n, m = 2, f"{ {0x10: 'mov', 0x12: 'add', 0x13: 'cmp'}[op6] } {v},r{reg2}"
        elif op6 in (0x14, 0x15, 0x16):
            n, m = 2, f"{ {0x14: 'shr', 0x15: 'sar', 0x16: 'shl'}[op6] } 0x{hw & 0x1F:x},r{reg2}"
        elif op6 in (0x0C, 0x0D, 0x0F, 0x08):
            n, m = 2, f"{ {0x0C: 'subr', 0x0D: 'sub', 0x0F: 'cmp', 0x08: 'or'}[op6] } r{reg1},r{reg2}"
        else:
            n, m = 2, f"?? 0x{hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


def assert_decoder_calibrated():
    """🛑 CALIBRATE THE WITNESS BEFORE USING IT -- on V75's cave, which V75's own decoder defines,
    and on V84's cave, which V84's own decoder defines."""
    n = 0
    for builder, decoder in ((V75.build_cave, V75.redisassemble_cave),
                             (V84B.build_cave, V84B.redisassemble_v84_cave)):
        cave, _l = builder()
        mine = redisassemble_v85_cave(cave)
        theirs = decoder(cave)
        assert [(a, r) for a, r, _m in mine] == [(a, r) for a, r, _m in theirs], \
            "🛑 V85's decoder splits an earlier cave into different instructions than its own decoder"
        for (a, _r, m), (_a, _r2, t) in zip(mine, theirs):
            assert m == t, f"🛑 at 0x{a:05X} V85's decoder says {m!r}, the reference says {t!r}"
        n += len(mine)
    return n


def wire_byte4(rate, fric, status_bits=0x7):
    """A Python mirror of the cave, instruction for instruction, on 32-bit register semantics."""
    r7 = 0                                                     # mov 0x0,r7
    r6 = rate                                                  # ld.h  (SIGN-extended int16)
    r6 = r6 >> RATE_SHIFT                                      # sar  (Python >> IS arithmetic)
    r6 = r6 + RATE_K_LO                                        # add
    if (r6 & M32) > 2 * RATE_K_LO - 1:                         # cmp / bnh (UNSIGNED)
        r7 += W_B7
    r6 = r6 + (RATE_K_HI - RATE_K_LO)                          # add
    if (r6 & M32) > 2 * RATE_K_HI - 1:
        r7 += W_B6
    r6 = fric                                                  # ld.h
    r6 = r6 + FRIC_T_HI
    if (r6 & M32) > 2 * FRIC_T_HI - 1:
        r7 += W_B5
    r6 = r6 + (FRIC_T_LO - FRIC_T_HI)
    if (r6 & M32) > 2 * FRIC_T_LO - 1:
        r7 += W_B4
    r7 = (r7 << HI_SHIFT) & M32                                # shl 0x4,r7
    r7 += BIT_FINGERPRINT                                      # add 0x8,r7
    r6 = status_bits & PAYLOAD_KEEP_MASK                       # ld.bu / andi
    return (r6 | r7) & 0xFF                                    # or / st.b (LOW BYTE only)


def decode_byte4(byte4):
    """Decode `0x14A` byte4. 🛑 A frame whose FINGERPRINT is clear is NOT V85 -- refuse it."""
    if not byte4 & BIT_FINGERPRINT:
        return None
    return {"rate_lo": bool(byte4 & BIT_RATE_LO), "rate_hi": bool(byte4 & BIT_RATE_HI),
            "fric_hi": bool(byte4 & BIT_FRIC_HI), "fric_lo": bool(byte4 & BIT_FRIC_LO),
            "fingerprint": True}


def _self_check_wire():
    """Every rung EXHAUSTIVELY over the FULL int16 range, and jointly over a product grid."""
    assert_decoder_calibrated()
    # ---- both rate rungs over EVERY reachable int16 ----------------------------------------------
    for v in range(-32768, 32768):
        d = decode_byte4(wire_byte4(v, 0))
        assert d is not None and d["fingerprint"]
        assert d["rate_lo"] == (v >= RATE_T_LO or v <= -RATE_T_LO - 1), f"b7 wrong at rate={v}"
        assert d["rate_hi"] == (v >= RATE_T_HI or v <= -RATE_T_HI - 1), f"b6 wrong at rate={v}"
        # 🛑 THE NESTING INVARIANT -- exact, same register, same pass. No sampling race.
        assert not (d["rate_hi"] and not d["rate_lo"]), f"b6 without b7 at rate={v}"
    # ---- both friction rungs over EVERY reachable int16 ------------------------------------------
    for v in range(-32768, 32768):
        d = decode_byte4(wire_byte4(0, v))
        assert d["fric_hi"] == (v >= FRIC_T_HI or v <= -FRIC_T_HI - 1), f"b5 wrong at fric={v}"
        assert d["fric_lo"] == (v >= FRIC_T_LO or v <= -FRIC_T_LO - 1), f"b4 wrong at fric={v}"
        assert not (d["fric_hi"] and not d["fric_lo"]), f"b5 without b4 at fric={v}"
    # ---- the trip points, stated as literals so a silent drift FAILS -----------------------------
    for t, bit, getter in ((RATE_T_LO, "rate_lo", lambda x: wire_byte4(x, 0)),
                           (RATE_T_HI, "rate_hi", lambda x: wire_byte4(x, 0)),
                           (FRIC_T_HI, "fric_hi", lambda x: wire_byte4(0, x)),
                           (FRIC_T_LO, "fric_lo", lambda x: wire_byte4(0, x))):
        assert decode_byte4(getter(t))[bit] and not decode_byte4(getter(t - 1))[bit], \
            f"🛑 {bit}'s POSITIVE trip is not exactly +{t}"
        assert decode_byte4(getter(-t - 1))[bit] and not decode_byte4(getter(-t))[bit], \
            f"🛑 {bit}'s NEGATIVE trip is not exactly -{t + 1}"
    # ---- EVERY rung must be able to BOTH fire and not fire (V69's bit4 was structurally vacuous) --
    for name, on, off in (("rate_lo", wire_byte4(100, 0), wire_byte4(0, 0)),
                          ("rate_hi", wire_byte4(-900, 0), wire_byte4(100, 0)),
                          ("fric_hi", wire_byte4(0, -40), wire_byte4(0, 4)),
                          ("fric_lo", wire_byte4(0, 4), wire_byte4(0, 1))):
        assert decode_byte4(on)[name] and not decode_byte4(off)[name], \
            f"🛑 rung {name} cannot both fire and not fire -- it is VACUOUS"
    # ---- no rung is implied by another beyond the two DECLARED nestings --------------------------
    seen = set()
    for rate in (-900, -100, 0, 100, 900):
        for fric in (-40, -4, 0, 4, 40):
            d = decode_byte4(wire_byte4(rate, fric))
            seen.add((d["rate_lo"], d["rate_hi"], d["fric_lo"], d["fric_hi"]))
    assert len(seen) == 9, f"{len(seen)} rung combinations reachable, expected 9 (3 x 3 nested)"
    # ---- the fingerprint is ALWAYS set, and the live status bits ALWAYS survive -------------------
    for rate in (-32768, -512, 0, 512, 32767):
        for st in range(8):
            b = wire_byte4(rate, 0, status_bits=st)
            assert b & BIT_FINGERPRINT, "🛑 the fingerprint is not set on a reachable payload"
            assert b & PAYLOAD_KEEP_MASK == st, "🛑 the live STEER_SENSOR_STATUS bits were destroyed"
            assert decode_byte4(b) is not None
    # ---- 🛑 a V84 frame must NOT decode as V85, and vice versa ------------------------------------
    assert decode_byte4(0x87) is None, "🛑 a bit3-clear frame must be REFUSED, not decoded"
    assert decode_byte4(0x00) is None and decode_byte4(0x80) is None
    # V84's OBSERVED alphabet on route 6d was exactly {0x2F, 0x3F}: b7 = b6 = 0 on all 68,236 frames.
    for v84 in (0x2F, 0x3F):
        assert not v84 & BIT_RATE_LO and not v84 & BIT_RATE_HI, \
            "🛑 V84's observed alphabet is not b7=b6=0 -- the identity argument is void"
    # 🛑 and V84's b7/b6 were MUTUALLY EXCLUSIVE (>= +1024 / <= -1025), so they can never NEST.
    assert V84B.wire_byte4(2000, 1, 0) & V84B.BIT_R24_NEG == 0
    assert V84B.wire_byte4(-2000, 1, 0) & V84B.BIT_R24_POS == 0
    # ---- no latched/sticky bits: the payload is a pure function of the two inputs -----------------
    assert wire_byte4(0, 0, 0) == BIT_FINGERPRINT, \
        "🛑 the all-clear payload is not just the fingerprint -- something is latched"


_self_check_wire()

# 🛑 THE BUILDER->DECODER LINK, MADE MECHANICAL. `decode_v85_probe.py` IMPORTS these names rather than
# copying them, so the V66 failure mode -- a stale decoder header -- is structurally impossible.
CAVE_HEX = build_cave()[0].hex()


def assert_decoder_module():
    """Import the shipped decoder and run its own self-test against THIS build's constants."""
    if not os.path.exists(os.path.join(HERE, "decode_v85_probe.py")):
        print("    ⚠ decode_v85_probe.py not found -- the decoder/image link is NOT verified")
        return False
    import importlib
    dec = importlib.import_module("decode_v85_probe")
    importlib.reload(dec)
    assert dec.CAVE_HEX == CAVE_HEX, \
        "🛑 the shipped decoder's cave hex does not match this build's -- it is STALE"
    for name, want in (("BIT_RATE_LO", BIT_RATE_LO), ("BIT_RATE_HI", BIT_RATE_HI),
                       ("BIT_FRIC_HI", BIT_FRIC_HI), ("BIT_FRIC_LO", BIT_FRIC_LO),
                       ("BIT_FINGERPRINT", BIT_FINGERPRINT),
                       ("RATE_T_LO", RATE_T_LO), ("RATE_T_HI", RATE_T_HI),
                       ("FRIC_T_LO", FRIC_T_LO), ("FRIC_T_HI", FRIC_T_HI)):
        assert getattr(dec, name) == want, \
            f"🛑 the decoder's {name} is {getattr(dec, name)}, not {want}"
    dec._selftest()
    return True


# =====================================================================================================
# GATE 1 -- THE CENSUSES, RE-DERIVED ON EVERY IMAGE
# =====================================================================================================
_READ_OPS = {0x38: "ld.b", 0x39: "ld.h", 0x3C: "ld.bu", 0x3D: "ld.bu", 0x3F: "ld.hu/ld.w"}
_WRITE_OPS = {0x3A: "st.b", 0x3B: "st.h", 0x3E: "st.w"}


def fmt7_scan(buf, reg1, disp_enc):
    """A from-scratch Format-VII disp16 scan -- THE SECOND METHOD, written here, not imported.

    🛑 Python, not `search_instructions`: that tool counts only already-analysed instructions and
    still reports `truncated:false` while undercounting. It has produced wrong sets four times.
    🛑 `disp_enc` is the ENCODED halfword, not the address offset: `ld.bu`/`ld.hu` carry the width
    selector in hw2's LSB, so `tp+0x50bc` is encoded as **0x50BD**.
    """
    hits = []
    for a in range(0, len(buf) - 4, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        op6 = (hw1 >> 5) & 0x3F
        if op6 not in _READ_OPS and op6 not in _WRITE_OPS:
            continue
        if (hw1 & 0x1F) != reg1:
            continue
        if struct.unpack_from("<H", buf, a + 2)[0] != disp_enc:
            continue
        hits.append((a, _READ_OPS.get(op6) or _WRITE_OPS[op6], op6 in _WRITE_OPS))
    return hits


# =====================================================================================================
# 🛑 THE 48-BIT (disp23) FORM -- DECODED PROPERLY, AND CALIBRATED BEFORE USE
# =====================================================================================================
# `scan_gp_accesses.scan_ext` is a LOOSE CANDIDATE FINDER, not a decoder: it requires `disp < 0` (so
# it is STRUCTURALLY BLIND to a positive `tp` displacement, and a null from it on `tp+0x50bc` would be
# worthless), and its packing does not reproduce the real one -- asked for `-0x4ee8` it returns three
# addresses and MISSES the genuine `ld.hu -0x4ee8[gp],r10` at 0x59992 that Ghidra decodes there.
# The real layout, derived from four Ghidra-decoded instances and re-validated on every run:
#     disp23 = (sign_extend16(hw3) << 7) | ((hw2 >> 4) & 0x7F)     reg2 = hw2 >> 11
#     reg1   = hw1 & 0x1F                                          op6  = (hw1 >> 5) & 0x3F
DISP23_CAL = (                       # (addr, disp, reg1, reg2, op6) -- all four from Ghidra
    (0x59992, -0x4EE8, 4, 10, 0x3D),     # ld.hu -0x4ee8[gp],r10
    (0x5999C, -0x6ABC, 4, 8, 0x3C),      # ld.h  -0x6abc[gp],r8
    (0x599A4, -0x6ABC, 4, 8, 0x3D),      # ld.hu -0x6abc[gp],r8
    (0x599AE, -0x6A5E, 4, 6, 0x3D),      # ld.hu -0x6a5e[gp],r6
)


def decode_disp23(buf, a):
    """(disp, reg1, reg2, op6) for the 6-byte extended-displacement form at `a`."""
    hw1, hw2, hw3 = struct.unpack_from("<HHH", buf, a)
    hi = hw3 - 0x10000 if hw3 & 0x8000 else hw3
    return (hi << 7) | ((hw2 >> 4) & 0x7F), hw1 & 0x1F, hw2 >> 11, (hw1 >> 5) & 0x3F


def assert_disp23_calibrated(buf):
    """🛑 CALIBRATE THE INSTRUMENT BEFORE USING IT. A disp23 null is load-bearing for GATE 1."""
    for addr, disp, reg1, reg2, op6 in DISP23_CAL:
        got = decode_disp23(buf, addr)
        assert got == (disp, reg1, reg2, op6), \
            f"🛑 the disp23 decoder gives {got} at 0x{addr:05X}, Ghidra says " \
            f"{(disp, reg1, reg2, op6)} -- the INSTRUMENT is wrong and every disp23 null is void"
    return len(DISP23_CAL)


def disp23_scan(buf, reg1, disp, mask_lsb=False):
    """Every 6-byte extended-displacement access to `reg1 + disp`. Works for EITHER sign."""
    m = ~1 if mask_lsb else ~0
    return [(a, buf[a:a + 6].hex()) for a in range(0, len(buf) - 6)
            if (struct.unpack_from("<H", buf, a)[0] & 0x1F) == reg1
            and (decode_disp23(buf, a)[0] & m) == (disp & m)]


def assert_ratio_norm_census(buf, label):
    """🛑 `0xC40BC`: 1 reader / 0 writers image-wide, by TWO methods + the disp23 and literal forms."""
    mine = fmt7_scan(buf, TPREG, RATIO_NORM_DISP_ENC)
    assert [(a, w) for a, _m, w in mine] == [(RATIO_NORM_READER, False)], \
        f"🛑 {label}: tp+0x{RATIO_NORM_DISP:04x} has {[(hex(a), m) for a, m, _w in mine]}, expected " \
        f"exactly one READ at 0x{RATIO_NORM_READER:05X}"
    # the naive scan for the UNencoded displacement must return ZERO -- the recorded trap
    assert not fmt7_scan(buf, TPREG, RATIO_NORM_DISP), \
        f"{label}: a scan for the raw 0x{RATIO_NORM_DISP:04x} found hits -- the disp|1 rule changed"
    # SECOND METHOD: the independent Format-VII decoder. 🛑 It NORMALISES the displacement (strips
    # the width-selector LSB), so it is asked for 0x50BC while our own scan matched the RAW 0x50BD --
    # two decoders with OPPOSITE conventions landing on the same single address.
    alt = SCAN.scan(buf, RATIO_NORM_DISP, SCAN.TP_REG)
    assert sorted(h["addr"] for h in alt) == [RATIO_NORM_READER], \
        f"🛑 {label}: the two decoders disagree on tp+0x{RATIO_NORM_DISP:04x}: " \
        f"{[hex(h['addr']) for h in alt]}"
    assert all(h["even"] and not h["is_store"] for h in alt), \
        f"{label}: tp+0x{RATIO_NORM_DISP:04x} has an odd-offset or STORE hit"
    assert not SCAN.scan(buf, RATIO_NORM_DISP_ENC, SCAN.TP_REG), \
        f"{label}: the normalising decoder found the RAW 0x{RATIO_NORM_DISP_ENC:04X} -- convention " \
        "drift, and the two-method claim would be vacuous"
    # THIRD METHOD: the 48-bit disp23 form, with a decoder CALIBRATED on four Ghidra-decoded
    # instances first -- a null here is load-bearing, so the instrument is checked before it is used.
    assert_disp23_calibrated(buf)
    assert not disp23_scan(buf, TPREG, RATIO_NORM_DISP, mask_lsb=True), \
        f"🛑 {label}: tp+0x{RATIO_NORM_DISP:04x} has a 6-byte extended-displacement access"
    # THIRD: an LE32 absolute literal of the cell's address would be an alias no disp scan can see
    lit = buf.find(struct.pack("<I", TP + RATIO_NORM_DISP))
    assert lit < 0, f"🛑 {label}: an LE32 literal 0x{TP + RATIO_NORM_DISP:08X} exists at 0x{lit:05X}"
    # ⇒ RULE 11 IS SATISFIED BY CONSTRUCTION: the sole reader is the arithmetic site itself, so no
    #   monitor, lockstep twin or float mirror can be reading this cell.
    assert 0x3B8F6 <= RATIO_NORM_READER < 0x3BC20, \
        "🛑 the sole reader is not inside FUN_0003b8f6 -- RULE 11's 'no monitor' argument fails"
    return mine


def assert_probe_cells(buf, label, cave_span):
    """🛑 GATE 1 FOR THE PROBE -- `census_gp4` (disp16 + disp23 + abs literal + movhi/movea) AND the
    from-scratch scan above. The cave READS these cells and WRITES NONE of them."""
    out = {}
    for disp, n_w, n_r, why in PROBE_CELLS:
        w, r, (lit, mhi) = V81.census_gp4(buf, disp)
        fw_w = [x for x in w if x[0] not in cave_span]
        fw_r = [x for x in r if x[0] not in cave_span]
        assert (len(fw_w), len(fw_r)) == (n_w, n_r), \
            f"🛑 {label}: gp-0x{disp:04x} ({why}) has {len(fw_w)}w/{len(fw_r)}r, expected " \
            f"{n_w}w/{n_r}r: writers {[hex(x[0]) for x in fw_w]}"
        assert not lit and not mhi, \
            f"🛑 {label}: gp-0x{disp:04x} has {len(lit)} absolute-literal and {len(mhi)} movhi/movea " \
            "reference(s) -- an ALIASED access the displacement scans cannot see"
        cave_w = [x for x in w if x[0] in cave_span]
        assert not cave_w, \
            f"🛑 {label}: THE CAVE WRITES gp-0x{disp:04x} at {[hex(x[0]) for x in cave_w]} -- the " \
            "probe is supposed to be READ-ONLY telemetry"
        # SECOND METHOD, from scratch: our own Format-VII scan over the ld.h encoding
        mine_w = [h for h in fmt7_scan(buf, GP, (0x10000 - disp) & 0xFFFF) if h[2]]
        assert len(mine_w) == n_w, \
            f"🛑 {label}: the second method finds {len(mine_w)} writer(s) of gp-0x{disp:04x}"
        # THIRD METHOD: the calibrated 48-bit disp23 decoder, by ADDRESS not just by count
        ext = disp23_scan(buf, GP, -disp)
        assert tuple(a for a, _b in ext) == PROBE_DISP23[disp], \
            f"🛑 {label}: gp-0x{disp:04x}'s disp23 accesses are {[hex(a) for a, _b in ext]}, " \
            f"expected {[hex(a) for a in PROBE_DISP23[disp]]}"
        for a, _b in ext:
            assert decode_disp23(buf, a)[3] in (0x3C, 0x3D), \
                f"🛑 {label}: the disp23 access at 0x{a:05X} is not a LOAD (op6 0x3C/0x3D)"
        out[disp] = (len(fw_w), len(fw_r), len([x for x in r if x[0] in cave_span]))
    # the free tap must have EXACTLY the writer the design names, by address, and NO firmware reader
    w, r, _e = V81.census_gp4(buf, FRIC_DISP)
    assert [x[0] for x in w] == [FRIC_WRITER], \
        f"🛑 {label}: gp-0x{FRIC_DISP:04x}'s writer is {[hex(x[0]) for x in w]}, expected " \
        f"0x{FRIC_WRITER:05X}"
    assert not [x for x in r if x[0] not in cave_span], \
        f"🛑 {label}: gp-0x{FRIC_DISP:04x} has acquired a FIRMWARE reader -- it is no longer free " \
        "telemetry, the blast-radius-zero claim is VOID, and RULE 11's 'no monitor' argument fails"
    return out


def assert_b5_refutation(buf, label):
    """🛑 THE EVIDENCE THAT `|gp-0x6b98| > 8192` CANNOT FIRE -- re-asserted on every image.

    This is why the brief's `b5` was replaced. If ANY of it stops holding, the substitution is
    unjustified and the build must fail rather than ship a rung on a false premise.
    """
    w, _r, _e = V81.census_gp4(buf, 0x6B98)
    assert tuple(sorted(x[0] for x in w)) == CMD_WRITERS, \
        f"🛑 {label}: gp-0x6b98's writer set is {[hex(x[0]) for x in w]}, expected " \
        f"{[hex(a) for a in CMD_WRITERS]}"
    for addr, raw in CMD_CLAMP_SITES.items():
        assert bytes(buf[addr:addr + len(raw)]) == raw, \
            f"🛑 {label}: the +-0x2000 clamp instruction at 0x{addr:05X} is " \
            f"{bytes(buf[addr:addr + len(raw)]).hex()}, expected {raw.hex()} -- the b5 refutation " \
            "rests on this clamp and it has MOVED"
    # the two clamp bounds appear as literal movea immediates, checked as VALUES not just bytes
    assert struct.unpack_from("<h", buf, 0x43B14)[0] == CMD_GATE
    assert struct.unpack_from("<h", buf, 0x43B1E)[0] == -CMD_GATE
    return True


def assert_caller_guard(buf, label):
    """🛑 The state guard that wraps the `jarl` -- the REAL staleness source for gp-0x6ae2."""
    for addr, raw in CALLER_GUARD.items():
        assert bytes(buf[addr:addr + len(raw)]) == raw, \
            f"🛑 {label}: the caller guard at 0x{addr:05X} is " \
            f"{bytes(buf[addr:addr + len(raw)]).hex()}, expected {raw.hex()}"
    assert struct.unpack_from("<H", buf, 0x221D8)[0] == CALLER_GUARD_MASK, \
        f"{label}: the state mask is not 0x{CALLER_GUARD_MASK:03X}"
    return [i for i in range(16) if CALLER_GUARD_MASK >> i & 1]


def assert_out_cliff(buf, label):
    """🛑 GATE 2's zero-reject question: `gp-0x6bfc`'s sentinel is OUTSIDE its own clamp."""
    w, r, (lit, mhi) = V81.census_gp4(buf, 0x6BFC)
    assert [x[0] for x in w] == [OUT_CELL_WRITER] and [x[0] for x in r] == [OUT_CELL_READER], \
        f"🛑 {label}: gp-0x6bfc is {[hex(x[0]) for x in w]}w / {[hex(x[0]) for x in r]}r, expected " \
        f"1 writer 0x{OUT_CELL_WRITER:05X} / 1 reader 0x{OUT_CELL_READER:05X}"
    assert not lit and not mhi, f"{label}: gp-0x6bfc has an aliased access"
    # the clamp's own literal (0x4e21 = 20001 as the `< ` bound) and the reader's window (0x9c41)
    assert struct.pack("<H", 0x9C41) in bytes(buf[OUT_CELL_READER:OUT_CELL_READER + 0x20]), \
        f"{label}: FUN_0003bc20's +-20000 window literal is not where it was"
    return True


def assert_lane_cals(buf, label):
    """Every constant the header's arithmetic depends on. If one moves, the numbers are void."""
    for addr, (want, why) in LANE_CALS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: 0x{addr:05X} = {got}, expected {want} -- {why}"
    for addr, want in LANE_FLOATS.items():
        got = struct.unpack_from("<f", buf, addr)[0]
        assert got == want, \
            f"🛑 {label}: the FIR tap 0x{addr:05X} = {got}, expected {want} -- the 'pass-through' " \
            "claim, and with it the |model| bound, would be void"
    # the gp-0x6a10 LERP the model's torque term is scaled by
    ys = [u16(buf, TP + 0x7B80 + 2 * i) for i in range(13)]
    assert min(ys) == LERP_MIN and max(ys) == LERP_MAX, \
        f"{label}: the gp-0x6a10 LERP Y range is [{min(ys)}, {max(ys)}], expected " \
        f"[{LERP_MIN}, {LERP_MAX}]"
    return ys


def assert_frozen(buf, label):
    """🛑 V84's package, FROZEN BY OPERATOR DECISION. Asserted from the image, one cell at a time."""
    for addr, (want, why) in FROZEN_CELLS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: FROZEN 0x{addr:05X} = {got}, expected {want} -- {why}"
    for addr, (want, why) in FROZEN_BYTES.items():
        assert buf[addr] == want, \
            f"🛑 {label}: FROZEN 0x{addr:05X} = 0x{buf[addr]:02X}, expected 0x{want:02X} -- {why}"


def assert_no_399_channel(buf, label):
    """🛑 THE 399 CHANNEL IS ON HOLD BY OPERATOR DIRECTION. Assert it is genuinely absent."""
    for addr, want in V84B.HOOK_399_STOCK.items():
        got = bytes(buf[addr:addr + 4])
        assert got == want, \
            f"🛑 {label}: the frame-399/427 hook site 0x{addr:05X} is {got.hex()}, expected the " \
            f"byte-stock {want.hex()}"
    tail = bytes(buf[CAVE_BASE + CAVE_EXTENT:V84B.CAVE_FREE_END])
    assert set(tail) == {0xFF}, \
        f"🛑 {label}: the cave region above 0x{CAVE_BASE + CAVE_EXTENT:05X} is not untouched 0xFF " \
        f"({len(tail) - tail.count(0xFF)} non-FF byte(s)) -- a second cave was built"
    return len(tail)


def assert_cave_v85(buf, label):
    """🛑 THE CAVE, RE-DERIVED AND RE-DISASSEMBLED OUT OF THE BUILT IMAGE."""
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    derived, listing = build_cave()
    assert cave == derived, \
        f"🛑 {label}: the cave in the image is not `build_cave()`'s re-derivation\n" \
        f"      image  {cave.hex()}\n      derive {derived.hex()}"
    assert len(cave) == CAVE_EXTENT == 68, f"{label}: THE CAVE EXTENT MOVED -- it must stay 68"
    redis = redisassemble_v85_cave(cave)
    assert [(a, r) for a, r, _m in redis] == [(a, r) for a, r, _t in listing], \
        f"{label}: the readback re-disassembly diverges from the emitted listing"
    assert not [m for _a, _r, m in redis if m == "nop" or m.startswith("??")], \
        f"{label}: the cave re-disassembly contains a nop or an undecoded halfword"
    stores = [m for _a, _r, m in redis if m.startswith(("st.b", "st.h", "st.w"))]
    assert len(stores) == 1 and stores[0].startswith("st.b"), \
        f"{label}: the cave contains {stores}, expected exactly ONE st.b to the CAN-330 payload"
    # 🛑 THE ONE-BIT TRAP, checked on the IMAGE and not just on the emitter
    for off, disp in ((2, RATE_DISP), (24, FRIC_DISP)):
        assert ((struct.unpack_from("<H", cave, off)[0] >> 5) & 0x3F) == OP_LDH, \
            f"🛑 {label}: the cave's gp-0x{disp:04x} access at +{off} is not `ld.h` (0x39)"
        assert struct.unpack_from("<H", cave, off + 2)[0] == (0x10000 - disp) & 0xFFFF, \
            f"🛑 {label}: the cave's access at +{off} does not address gp-0x{disp:04x}"
    assert ((struct.unpack_from("<H", buf, FRIC_WRITER)[0] >> 5) & 0x3F) == OP_STH, \
        f"🛑 {label}: the firmware's own gp-0x{FRIC_DISP:04x} instance @0x{FRIC_WRITER:05X} is not " \
        "`st.h` -- the one-bit contrast is vacuous"
    assert bytes(cave[26:28]) == bytes(buf[FRIC_WRITER + 2:FRIC_WRITER + 4]), \
        f"🛑 {label}: our load and the firmware's store do not address the SAME cell"
    # the hook is UNCHANGED -- same jarl, same return, same displaced movea
    assert bytes(buf[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: the hook @0x{HOOK_ADDR:05X} is not `jarl 0x{CAVE_BASE:05X}`"
    assert bytes(buf[HOOK_ADDR + 4:HOOK_ADDR + 6]) == HOOK_RETURN_INSN, \
        f"{label}: 0x{HOOK_ADDR + 4:05X} is not `mov 0x8,r7` -- r7 is not provably dead"
    assert cave.count(HOOK_STOCK) == 1, f"{label}: the displaced movea is not present exactly once"
    return cave, redis


def assert_identity_modulo(buf, ref_img, allowed, label, refname):
    """🛑 THE VALUE-ANCHORED VERIFIER -- whole-image identity modulo an ATTRIBUTED set.

    `diff_build_vs_stock.py` is SPAN-based and will pass a WRONG VALUE inside a RIGHT RANGE. This is
    the strongest statement available: restore every byte V85 is ALLOWED to have changed, then assert
    the result is byte-for-byte the reference over the FULL 1 MiB -- not over [START, END).
    """
    probe = bytearray(buf)
    for a in allowed:
        probe[a] = ref_img[a]
    diff = [i for i in range(len(ref_img)) if probe[i] != ref_img[i]]
    assert not diff, \
        f"🛑 {label}: after restoring the {len(allowed)} ATTRIBUTED bytes, the image still differs " \
        f"from {refname} at {len(diff)} byte(s): {[hex(x) for x in diff[:16]]}."
    return bytes(probe)


def diff_runs(a_img, b_img, attribute, lo=0, hi=0x100000):
    """Contiguous differing runs, split wherever the attribution changes."""
    runs, prev = [], None
    for d in range(lo, hi):
        if a_img[d] == b_img[d]:
            prev = None
            continue
        if prev is not None and d == prev[1] + 1 and attribute(d) == attribute(prev[0]):
            prev = (prev[0], d)
            runs[-1] = prev
        else:
            prev = (d, d)
            runs.append(prev)
    return runs


# =====================================================================================================
# THE BUILD
# =====================================================================================================

def build():
    print(__doc__)
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it."
    assert VARIANT_TOKEN in os.path.basename(BIN_OUT) and VARIANT_TOKEN in os.path.basename(OUT), \
        "🛑 the variant is not in BOTH filenames"
    assert "+" not in OUT and "+" not in BIN_OUT, "🛑 `+` in a filename URL-decodes to a SPACE"

    v84 = bytes(Path(SRC_BIN).read_bytes())
    stock = bytes(Path(STOCK_BIN).read_bytes())
    print("=" * 102)
    print(f"SOURCE (V84, flown route 6d): {SRC_BIN}")
    src_sha = hashlib.sha256(v84).hexdigest()
    print(f"  SHA256 {src_sha}")
    assert len(v84) == len(stock) == 0x100000, "an image is not 1 MiB"
    assert src_sha not in NOT_THE_BASE, f"🛑🛑 THE BASE IS {NOT_THE_BASE.get(src_sha)}"
    assert src_sha == SRC_SHA256, \
        f"🛑🛑 THE BASE IS NOT V84. SHA256 is {src_sha}, expected {SRC_SHA256}."
    print("  ✅ the base SHA256 is the V84 cut that FLEW ROUTE 6d, EXACTLY.")
    print(f"  WRITE MODE: {WRITE_MODE or 'DRY RUN -- nothing will be written to disk'}")

    # =================================================================================================
    # GATE THE SOURCE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  GATING THE SOURCE -- everything below is measured on the INPUT before a byte moves")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert walk_all_blocks(v84) == 0, "the V84 source's own CRC chain does not verify"

    # ---- the edit's precondition, and its PROVENANCE stated as a NEGATIVE ---------------------------
    for addr, width, pre, _new, lbl in EDITS:
        got = u16(v84, addr)
        assert got == pre, f"🛑 the base's 0x{addr:05X} ({lbl}) is {got}, expected V84's {pre}"
    print(f"\n    🛑 PROVENANCE, STATED AS A NEGATIVE -- 0x{RATIO_NORM_ADDR:05X} on every image on "
          "disk:")
    for name, (path, sha) in NEVER_FLOWN_ANCHORS.items():
        if not os.path.exists(path):
            print(f"      {name:<6s} NOT ON DISK -- skipped")
            continue
        img = Path(path).read_bytes()
        if sha:
            assert hashlib.sha256(img).hexdigest() == sha, f"the {name} anchor drifted"
        got = u16(img, RATIO_NORM_ADDR)
        assert got == RATIO_NORM_OLD, \
            f"🛑 {name} carries 0x{RATIO_NORM_ADDR:05X} = {got}, not {RATIO_NORM_OLD} -- the " \
            "'never flown' claim is FALSE and the lineage must be re-checked"
        print(f"      {name:<6s} {got}")
    print(f"      ⇒ {RATIO_NORM_NEW} HAS NEVER BEEN ON THIS CAR. V85's case is STRUCTURAL, not "
          "historical.")

    assert_frozen(v84, "V84 source")
    assert_lane_cals(v84, "V84 source")
    ratio_census = assert_ratio_norm_census(v84, "V84 source")
    assert_b5_refutation(v84, "V84 source")
    guard_states = assert_caller_guard(v84, "V84 source")
    assert_out_cliff(v84, "V84 source")
    V84B.assert_keep_list(v84, "V84 source")
    V84B.assert_pointer_arrays_stock(v84, stock, "V84 source")
    V84B.assert_manual_modes_frozen(v84, v84, stock, "V84 source")
    V84B.assert_friction_all_stock(v84, stock, "V84 source")
    V84B.assert_gain_a_honda(v84, stock, "V84 source")
    V84B.assert_gain_b_inert_mode10(v84, "V84 source")
    V84B.assert_factor_surface(v84, stock, "V84 source", reverted=True)
    V84B.assert_engaged_equals_manual(v84, stock, "V84 source")
    V84B.assert_factor_monotone(v84, "V84 source", must_have_fold=False)
    V84B.assert_insurance_guards(v84, stock, "V84 source")
    V84B.assert_edit_geometry(v84, "V84 source")
    V84B.assert_repoint_and_chain(v84, "V84 source", done=True)
    V84B.assert_repoint_twins(v84, "V84 source")
    V84B.assert_arm_derivation(v84, "V84 source")
    V74.assert_clamp_census(v84)
    V72.assert_lever_c_single_reader(v84)
    assert_no_399_channel(v84, "V84 source")
    assert_probe_encoders(stock)
    n_decoder = assert_decoder_calibrated()
    decoder_ok = assert_decoder_module()
    # the BASE must still carry V84's own cave, byte for byte, before V85 repoints it
    v84_cave, _l = V84B.build_cave()
    assert bytes(v84[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v84_cave, \
        "🛑 the base's cave is not `build_v84_tva.build_cave()`'s 68 bytes"
    probe_src = assert_probe_cells(v84, "V84 source", cave_span)
    ri_old, ri_new = assert_relay_arithmetic()

    print(f"\n    ✅ CRC 50/50 on the INPUT · the {len(FROZEN_CELLS)} FROZEN cells + "
          f"{len(FROZEN_BYTES)} FROZEN bytes verified")
    print("    ✅ V84's whole guard suite re-run on the INPUT: the keep-list, all six pointer arrays "
          "over 34 modes,")
    print("       MANUAL modes 24/25 byte-STOCK, all 34 friction records byte-STOCK, gain_A == Honda, "
          "the FactorC/E")
    print("       surface, engaged==manual dose identity, Lever B's repoint + arm + lp chain, the "
          "insurance guards.")
    print(f"    ✅ the friction-lane cals: " +
          " · ".join(f"0x{a:05X}={v}" for a, (v, _w) in list(LANE_CALS.items())[:5]))
    print(f"       FIR taps 0xC4048/4C/50 = {[LANE_FLOATS[a] for a in (0xC4048, 0xC404C, 0xC4050)]}"
          " ⇒ a PASS-THROUGH, so `model` IS the delivered command.")

    print(f"\n    ★ GATE 1 -- 0x{RATIO_NORM_ADDR:05X} (tp+0x{RATIO_NORM_DISP:04x}), THE CELL V85 "
          "MOVES, censused FOUR ways:")
    print(f"      disp16 (encoded 0x{RATIO_NORM_DISP_ENC:04X}) : "
          f"{[(hex(a), m) for a, m, _w in ratio_census]}")
    print(f"      disp16 (RAW 0x{RATIO_NORM_DISP:04X})        : 0 hits  🛑 the `disp | 1` trap -- a "
          "scan for the raw value 'proves' the cell dead")
    print("      disp23 / 6-byte extended form  : 0 hits")
    print("      LE32 absolute literal          : 0 hits")
    print(f"      ⇒ **1 reader / 0 writers image-wide**, and the reader is 0x{RATIO_NORM_READER:05X} "
          "INSIDE FUN_0003b8f6 itself.")
    print("      ⇒ 🛑 RULE 11 SATISFIED BY CONSTRUCTION: no monitor, lockstep twin or float mirror "
          "can read this cell.")
    print("        (For contrast, 0xC407E -- the cell RULE 11 was written for -- has 3 readers and a "
          "float twin at 0xC4004.)")

    print("\n    ★ GATE 1 FOR THE PROBE -- census_gp4 (disp16+disp23+literal+movhi) AND a "
          "from-scratch Format-VII scan:")
    for _d, _w, _r, _why in PROBE_CELLS:
        nw, nr, nc = probe_src[_d]
        print(f"      gp-0x{_d:04x}  {nw} writer(s) / {nr} firmware reader(s) · 0 abs-literal · "
              f"0 movhi/movea   {_why}")
    print(f"      ⇒ gp-0x{FRIC_DISP:04x} is a POST-CLAMP TAP NOTHING READS "
          f"(1 writer 0x{FRIC_WRITER:05X}): free, blast-radius-zero telemetry.")

    print("\n    🛑 THE b5 REFUTATION -- why `|gp-0x6b98| > 8192` was NOT shipped, asserted from the "
          "image:")
    print(f"      gp-0x6b98 writers: {[hex(a) for a in CMD_WRITERS]}")
    print("      0x43B0E addi -0x2000,r14,r0 · 0x43B12 movea 0x2000,r0,r21 · 0x43B16 bgt · "
          "0x43B1C movea -0x2000,r0,r6")
    print("      0x43B20 cmovle r6,r14,r21   ⇒ r21 = clamp(r14, +-0x2000), and 0x43B52/0x43DFC store "
          "EXACTLY r21.")
    print("      ⇒ the gate `|gp-0x6b98| <= 0x2000` tests a value clamped to +-0x2000. **IT CANNOT "
          "FAIL.**")
    print("      ⊕ 0x6E104/0x6E1DC are a CALLER-LESS pair of actuator-test routines that disable the "
          "control path first.")
    print("      ⊕ ON-CAR: V55's flown gp-0x6b98 probe, route 24, n=69,607 engaged frames / 943 s -- "
          "99.2% inside +-512,")
    print("        and the |x| >= 3584 level occurred **0.00%** of the time. 8192 is 2.3x beyond a "
          "level that never occurred.")
    print(f"      ⇒ b5 was re-pointed onto a SECOND threshold of the friction tap. The freed bytes "
          "made ALL FOUR rungs TWO-SIDED.")
    print(f"      🛑 THE REAL STALENESS SOURCE, found instead: the CALLER's guard "
          f"`andi 0x{CALLER_GUARD_MASK:03X},r25,r28` @0x221D6")
    print(f"        + `cmp r0,r28` / `be` @0x2240C skips the whole function outside states "
          f"{guard_states}. gp-0x6ae2 HOLDS there;")
    print("        gp-0x6abc keeps being written (4 writers, none in FUN_0003b8f6) ⇒ b7/b6 stay live "
          "while b5/b4 hold.")

    print("\n    ★ GATE 2 -- THE ZERO-REJECT CLIFF, and the correction it forced:")
    print(f"      gp-0x6bfc: 1 writer 0x{OUT_CELL_WRITER:05X} / 1 reader 0x{OUT_CELL_READER:05X}. "
          f"FUN_0003bc20 emits its 0x7FFF sentinel iff |gp-0x6bfc| > {OUT_CLAMP},")
    print(f"      ONE count outside the +-{OUT_CLAMP} clamp applied to the same value four "
          "instructions earlier ⇒ **untrippable by construction**,")
    print("      the same interlock pattern as 0xC407E/0xC4004. V85 touches neither. The only path to "
          "the sentinel is the ENABLE-GATE")
    print("      fail, which V85 does not touch.")
    print("      ⚠ AND THE BRIEF'S PREMISE IS CORRECTED: FRICTION is SUBTRACTED, so REDUCING it can "
          "INCREASE |gp-0x6bfc|.")
    print(f"        Bound: |dFRICTION| <= {u16(v84, 0xC40D2)}/1024 * |model| ⇒ "
          f"<= {u16(v84, 0xC6468)} * {u16(v84, 0xC40D2) / 1024:.4f} = "
          f"{u16(v84, 0xC6468) * u16(v84, 0xC40D2) / 1024:.0f} counts per unit |model|,")
    print(f"        i.e. <= {u16(v84, 0xC6468) * u16(v84, 0xC40D2) / 1024 * (CMD_GATE / 1024 + 0.936):.0f}"
          f" counts at the absolute worst case and <= "
          f"{u16(v84, 0xC6468) * u16(v84, 0xC40D2) / 1024 * 0.2:.0f} at the measured working point, "
          f"against a +-{OUT_CLAMP} clamp.")

    print("\n    ★ THE RELAY, RE-DERIVED FROM THE IMAGE (two implementations, quadrature + closed "
          "form, asserted equal)")
    print(f"      {'0xC40BC':>9} {'sat @ counts':>13} {'linear over':>12} " +
          "".join(f"{f'N({r})':>8}" for r in (25, 50, 100, 250, 500, 1000)) + f"{'RELAY IDX':>11}")
    for cand in (RATIO_NORM_OLD, 1200, 3000, RATIO_NORM_NEW, 12000):
        sat = cand / RATE_MUL
        row = "".join(f"{describing_function_closed(r, cand):>8.3f}"
                      for r in (25, 50, 100, 250, 500, 1000))
        mark = ("   <-- V84 / HONDA" if cand == RATIO_NORM_OLD else
                "   <-- V85" if cand == RATIO_NORM_NEW else "")
        print(f"      {cand:>9} {sat:>13.0f} {100.0 * sat / RATE_ENABLE_GATE:>11.2f}% " + row +
              f"{relay_index(cand):>11.2f}" + mark)
    print(f"      ⇒ relay index {ri_old:.2f} -> {ri_new:.2f}. Honda's VISCOUS damper = 1.00 · "
          "V75's engaged damper = 1.45 · V80's bang-bang = 3.27.")
    print("      🛑 V80's 3.27 produced the WORST GRINDING EVER RECORDED. V84 is shipping 7.87 in "
          "this lane, right now.")
    print(f"\n      DELIVERED FRICTION, V85 / V84, by |motor rate| "
          f"(/{RATE_COUNTS_PER_DEG_S} = deg/s):")
    print("      " + "".join(f"{r:>8}" for r in (10, 25, 49, 50, 100, 250, 500, 1000, 1941)))
    print("      " + "".join(f"{dose_ratio(r):>8.2f}" for r in
                             (10, 25, 49, 50, 100, 250, 500, 1000, 1941)))
    print("      ⇒ 🛑 a FLAT 0.10 at and below 50 counts (both linear, slopes 10x apart), rising to "
          "an exact 1.00 at/above 500")
    print("        (both saturated). The 10x loss is the FULL low-rate regime, not just the "
          "breakpoint.")

    # =================================================================================================
    # APPLY THE EDIT
    # =================================================================================================
    code = bytearray(v84)
    print("\n" + "-" * 102)
    print(f"  APPLYING THE {len(EDITS)} EDIT")
    print(f"      {'#':>2s} {'addr':<9s} {'cell':<26s} {'V84':>6s} {'V85':>6s}  {'bytes':<16s}")
    attributed = set()
    for i, (addr, width, pre, new, lbl) in enumerate(EDITS, 1):
        got = u16(code, addr)
        assert got == pre, f"0x{addr:05X} moved between the gate and the write"
        old_raw = bytes(code[addr:addr + width])
        struct.pack_into("<H", code, addr, new)
        new_raw = bytes(code[addr:addr + width])
        assert u16(code, addr) == new, f"the write at 0x{addr:05X} did not take"
        assert s16(code, addr) == new, f"{new} does not round-trip as a signed int16"
        assert 0 < new <= 0x7FFF, "the new value is not a positive signed halfword"
        attributed |= {addr + k for k in range(width)}
        print(f"      {i:2d} 0x{addr:05X}  {lbl:<26s} {pre:>6d} {new:>6d}  "
              f"{old_raw.hex():<6s} -> {new_raw.hex():<6s}")
    assert len(attributed) == 2, f"{len(attributed)} attributed control bytes, expected 2"

    # =================================================================================================
    # THE CAVE REPOINT -- inside the PROVEN 68-byte extent. Same hook, same base, same 5 payload bits.
    # =================================================================================================
    old_cave = bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    new_cave, cave_listing = build_cave()
    assert len(new_cave) == len(old_cave) == CAVE_EXTENT == 68, "🛑 THE CAVE EXTENT MOVED"
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = new_cave
    cave_attributed = {CAVE_BASE + k for k in range(CAVE_EXTENT) if old_cave[k] != new_cave[k]}
    attributed |= cave_attributed
    print(f"\n    THE CAVE REPOINT -- 0x{CAVE_BASE:05X}, {CAVE_EXTENT} B, extent UNCHANGED, hook "
          f"0x{HOOK_ADDR:05X} UNCHANGED")
    print(f"      V84   {old_cave.hex()}")
    print(f"      V85   {new_cave.hex()}")
    print(f"      ⇒ {len(cave_attributed)} of {CAVE_EXTENT} cave bytes differ; the design fills all "
          "68 with NO padding.")
    for _a, _r, _t in cave_listing:
        print(f"        0x{_a:05X} {_r.hex():<10s} {_t}")

    # =================================================================================================
    # RE-ASSERT EVERYTHING ON THE FINISHED IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  RE-ASSERTING ON THE FINISHED IMAGE")
    assert u16(code, RATIO_NORM_ADDR) == RATIO_NORM_NEW
    assert_frozen(code, "V85")
    assert_lane_cals(code, "V85")
    assert_ratio_norm_census(code, "V85")
    assert_b5_refutation(code, "V85")
    assert_caller_guard(code, "V85")
    assert_out_cliff(code, "V85")
    V84B.assert_keep_list(code, "V85")
    V84B.assert_pointer_arrays_stock(code, stock, "V85")
    V84B.assert_manual_modes_frozen(code, v84, stock, "V85")
    V84B.assert_friction_all_stock(code, stock, "V85")
    V84B.assert_gain_a_honda(code, stock, "V85")
    V84B.assert_gain_b_inert_mode10(code, "V85")
    V84B.assert_factor_surface(code, stock, "V85", reverted=True)
    V84B.assert_engaged_equals_manual(code, stock, "V85")
    V84B.assert_factor_monotone(code, "V85", must_have_fold=False)
    V84B.assert_insurance_guards(code, stock, "V85")
    V84B.assert_edit_geometry(code, "V85")
    V84B.assert_repoint_and_chain(code, "V85", done=True)
    V84B.assert_repoint_twins(code, "V85")
    V84B.assert_arm_derivation(code, "V85")
    V84B.assert_untouched_v67 = getattr(V84B.V67, "assert_untouched_v67", None)
    V67.assert_untouched_context_v67(code, "V85")
    V67.assert_untouched_v67(code, "V85")
    V67.assert_signal_sites(code, "V85")
    V74.assert_clamp_census(bytes(code))
    V72.assert_lever_c_single_reader(bytes(code))
    assert_no_399_channel(code, "V85")
    cave, cave_redis = assert_cave_v85(code, "V85")
    probe_out = assert_probe_cells(code, "V85", cave_span)
    # 🛑 The FIRMWARE census cannot move -- V85 adds no firmware access. What DOES move is the CAVE's
    # 🛑 own read count: +1 on each of the two cells it reads, 0 elsewhere.
    for _d, _w, _r, _why in PROBE_CELLS:
        assert probe_out[_d][:2] == probe_src[_d][:2], \
            f"🛑 gp-0x{_d:04x}'s FIRMWARE census moved across the edit ({probe_src[_d][:2]} -> " \
            f"{probe_out[_d][:2]}) -- impossible for a cal + cave repoint; STOP AND REPORT"
        assert probe_src[_d][2] == 0, \
            f"🛑 V84's cave already read gp-0x{_d:04x} -- the delta below would not be V85's"
        assert probe_out[_d][2] == 1, \
            f"🛑 V85's cave reads gp-0x{_d:04x} {probe_out[_d][2]} time(s), expected 1"
    # and V84's OWN probe cells must be UNREFERENCED by the new cave
    v84_probe = V84B.assert_probe_cells(code, "V85 (V84's cells)")
    for _d, _w, _r, _why in V84B.PROBE_CELLS:
        assert v84_probe[_d][2] == 0, \
            f"🛑 V85's cave still reads V84's gp-0x{_d:04x} -- the repoint did not take"
    _r2, eng2, dis2 = V74.derive_mode_columns(bytes(code))
    assert V84B.derive_this_cars_modes(bytes(code))[1] == V84B.THIS_CAR_MODES
    print(f"    ✅ every FROZEN cell/byte, V84's full guard suite, Lever B, the damper surface, the "
          "mode columns: RE-VERIFIED.")
    print(f"    ✅ GATE 1: 0x{RATIO_NORM_ADDR:05X} still 1 reader / 0 writers; gp-0x{RATE_DISP:04x} "
          f"{probe_out[RATE_DISP][0]}w/{probe_out[RATE_DISP][1]}r and "
          f"gp-0x{FRIC_DISP:04x} {probe_out[FRIC_DISP][0]}w/{probe_out[FRIC_DISP][1]}r UNCHANGED "
          "across the edit;")
    print("       the cave reads each exactly ONCE and writes NEITHER. V85 writes no RAM at all.")
    print(f"    ✅ CAVE: {CAVE_EXTENT} B @0x{CAVE_BASE:05X} == `build_cave()`'s re-derivation, "
          f"re-disassembled out of the BUILT image into")
    print(f"       {len(cave_redis)} instructions with no nop and no undecoded halfword; exactly ONE "
          "store; hook UNCHANGED; 4 branches, all")
    print("       landing on instruction boundaries; every cmp/branch pair contiguous (no stale "
          "flags).")
    print(f"       🛑 the one-bit trap: both cave accesses are `ld.h` op 0x{OP_LDH:02X}; the "
          f"firmware's gp-0x{FRIC_DISP:04x} instance @0x{FRIC_WRITER:05X}")
    print(f"       is `st.h` op 0x{OP_STH:02X}, and both carry the SAME displacement halfword.")
    print(f"    ✅ the probe decoder was calibrated against V75's AND V84's own decoders on their own "
          f"caves ({n_decoder} instructions).")
    print(f"    ✅ decode_v85_probe.py: "
          f"{'imports THIS build s bit map; its self-test PASSES' if decoder_ok else 'NOT FOUND'}")

    print("\n    ★ THE RUNGS, AND WHAT THEY WILL READ  (predictions are [BELIEF]; thresholds are "
          "[EVIDENCE])")
    print(f"      b7  |gp-0x{RATE_DISP:04x}| >= {RATE_T_LO:<4d}  (trips +{RATE_T_LO} / "
          f"-{RATE_T_LO + 1})   the OLD saturation point is {OLD_SAT} ⇒ b7 set ⇒ V84's relay WAS "
          "saturated")
    print(f"      b6  |gp-0x{RATE_DISP:04x}| >= {RATE_T_HI:<4d}  (trips +{RATE_T_HI} / "
          f"-{RATE_T_HI + 1})   the NEW saturation point is {NEW_SAT} ⇒ b6 set ⇒ V85's relay IS "
          "saturated")
    print(f"      b5  |gp-0x{FRIC_DISP:04x}| >= {FRIC_T_HI:<4d}  (trips +{FRIC_T_HI} / "
          f"-{FRIC_T_HI + 1})   predicted duty 10-25% on V85 · ~55-80% on V84")
    print(f"      b4  |gp-0x{FRIC_DISP:04x}| >= {FRIC_T_LO:<4d}  (trips +{FRIC_T_LO} / "
          f"-{FRIC_T_LO + 1})   predicted duty 35-70% on V85 · ~85-95% on V84")
    print("      b3  = 1                       field liveness / build fingerprint")
    fric_max = (CMD_GATE / 1024.0 + 0.936) * u16(code, 0xC40D2)
    print(f"      ⇒ |gp-0x{FRIC_DISP:04x}| = {u16(code, 0xC40D2)} * |model| * min(|rate|/{NEW_SAT},1)"
          f", and |model| <= {CMD_GATE / 1024.0:.1f} + 0.936 ⇒ the tap is bounded by "
          f"{fric_max:.0f} counts.")
    for m in (0.1, 0.2, 0.5, 1.0):
        r4 = NEW_SAT * FRIC_T_LO / (u16(code, 0xC40D2) * m)
        r5 = NEW_SAT * FRIC_T_HI / (u16(code, 0xC40D2) * m)
        print(f"        |model| = {m:<4.1f} ⇒ b4 fires above |rate| = {r4:6.1f} counts "
              f"({r4 / RATE_COUNTS_PER_DEG_S:5.1f} deg/s) · b5 above {r5:6.1f} "
              f"({r5 / RATE_COUNTS_PER_DEG_S:5.1f} deg/s)")
    print(f"      ⇒ THE FREE INVERSION: b4 vs b7 crosses at |model| = "
          f"{NEW_SAT * FRIC_T_LO / (u16(code, 0xC40D2) * RATE_T_LO):.3f}, b5 vs b7 at "
          f"{NEW_SAT * FRIC_T_HI / (u16(code, 0xC40D2) * RATE_T_LO):.3f}, b5 vs b6 at "
          f"{NEW_SAT * FRIC_T_HI / (u16(code, 0xC40D2) * RATE_T_HI):.4f}")
    print("        ⇒ the four rungs BRACKET |model| -- the one quantity in this lane with no usable "
          "measurement. ⚠ a RANKING, not a point estimate.")

    # =================================================================================================
    # CRC
    # =================================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = [0xC4FFC]
    assert [b[1] for b in blocks] == expect_trailers, \
        f"expected trailers {[hex(t) for t in expect_trailers]}, got {[hex(b[1]) for b in blocks]}"
    print("\n" + "-" * 102)
    print(f"  CRC -- EXACTLY {len(blocks)} block(s) move (ASSERTED against "
          f"{[hex(t) for t in expect_trailers]}, not observed):")
    print("    ⊕ 0xC40BC AND the cave at 0xC4B34 are both inside [0x013000,0x0C4FFC) ⇒ ONE trailer, "
          "not three as V84 needed.")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        owners = [hex(a) for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}"
              f"   owns {len(owners)} byte(s): {owners[:4]}{' …' if len(owners) > 4 else ''}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full 50-block chain re-walked: 50/50 PASS (0 mismatches)")
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block, V40 ignition precedent"
    assert not [a for a in attributed if a < START or a >= END], \
        f"an edit landed outside the flashable region [0x{START:X},0x{END:X})"
    print(f"    ✅ none of the {len(attributed)} edited bytes lands in [0xC5000,0xC5FFC), and all of "
          f"them lie inside [0x{START:X},0x{END:X}).")

    # =================================================================================================
    # 🛑 THE FULL BYTE DIFF vs THE BASE
    # =================================================================================================
    by_addr = {}
    for a, w, pre, new, lbl in EDITS:
        for k in range(w):
            by_addr[a + k] = f"0x{a:05X} {lbl}  {pre} -> {new}"

    def attribute(d):
        if d in by_addr:
            return by_addr[d]
        if d in crc_only:
            return "CRC trailer"
        if CAVE_BASE <= d < CAVE_BASE + CAVE_EXTENT:
            return f"the CAVE REPOINT @0x{CAVE_BASE:05X} ({CAVE_EXTENT} B, extent UNCHANGED)"
        return None

    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V85 vs V84 -- over the WHOLE 1 MiB image")
    runs = diff_runs(code, v84, attribute)
    total = sum(b - a + 1 for a, b in runs)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    print(f"      {'range':<21s} {'len':>4s}  attribution")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, \
        f"🛑 UNATTRIBUTED bytes vs V84: {[hex(x) for x in stray[:16]]} -- STOP AND REPORT"
    diff_bytes = {d for a, b in runs for d in range(a, b + 1)}
    functional = total - len(crc_only & diff_bytes)
    fn_runs = [r for r in runs if attribute(r[0]) != "CRC trailer"]
    expect_diff = 0
    for a, w, _p, new, _l in EDITS:
        raw = struct.pack("<H", new)
        expect_diff += sum(1 for k in range(w) if v84[a + k] != raw[k])
    assert expect_diff == 2, f"the per-edit differing-byte count re-derives as {expect_diff}, not 2"
    assert functional == expect_diff + len(cave_attributed), \
        f"{functional} functional bytes differ, expected {expect_diff} cell + " \
        f"{len(cave_attributed)} cave"
    cave_runs = [r for r in fn_runs if CAVE_BASE <= r[0] < CAVE_BASE + CAVE_EXTENT]
    cell_runs = [r for r in fn_runs if r not in cave_runs]
    assert len(cell_runs) == len(EDITS) == 1, f"{len(cell_runs)} CELL run(s), expected {len(EDITS)}"
    assert len(runs) == len(cell_runs) + len(cave_runs) + len(blocks), \
        f"{len(runs)} runs, expected {len(cell_runs)} cell + {len(cave_runs)} cave + " \
        f"{len(blocks)} CRC"
    print(f"    ⇒ EXACTLY: {len(cell_runs)} CELL run ({expect_diff} bytes at "
          f"0x{RATIO_NORM_ADDR:05X}) + {len(cave_runs)} CAVE run(s) covering "
          f"{len(cave_attributed)} of the {CAVE_EXTENT} cave bytes")
    print(f"      + {total - functional} CRC byte(s) in {len(blocks)} run. NOTHING ELSE MOVED.")

    # ---- THE VALUE-ANCHORED VERIFIERS: whole-image identity modulo the attributed set --------------
    assert_identity_modulo(code, v84, attributed | crc_only, "V85", "V84")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = v84[a]
    rt_sha = hashlib.sha256(bytes(rt)).hexdigest()
    assert rt_sha == SRC_SHA256, f"the round trip yields {rt_sha}, expected {SRC_SHA256}"
    print(f"    ✅ VALUE-ANCHORED ROUND TRIP: restoring the {len(attributed)} attributed + "
          f"{len(crc_only)} CRC bytes reproduces")
    print(f"       V84 BIT-FOR-BIT -- sha256 back to {rt_sha} over all 0x100000 bytes.")
    # ---- and the CONTROL-ONLY round trip: reverting the TWO bytes alone reproduces V84 -------------
    rt2 = bytearray(code)
    rt2[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = v84[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]
    struct.pack_into("<H", rt2, RATIO_NORM_ADDR, RATIO_NORM_OLD)
    for a in crc_only:
        rt2[a] = v84[a]
    assert hashlib.sha256(bytes(rt2)).hexdigest() == SRC_SHA256, \
        "🛑 reverting the 2 control bytes + the cave does not reproduce V84"
    print("    ✅ CONTROL-ONLY ROUND TRIP: reverting `70 17` -> `58 02` at 0xC40BC and restoring "
          "V84's cave reproduces")
    print("       V84 bit-for-bit ⇒ the revert really is TWO BYTES plus the probe.")
    d_stock = sum(1 for i in range(0x100000) if code[i] != stock[i])
    d_stock_base = sum(1 for i in range(0x100000) if v84[i] != stock[i])
    print(f"    ⊕ vs STOCK: V85 differs at {d_stock} bytes, V84 at {d_stock_base}.")

    # =================================================================================================
    # THE .rwd -- ENCODED AND READ BACK IN MEMORY EVEN ON A DRY RUN
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  .rwd ENCODE + READBACK (in memory even on a dry run)")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    FF.assert_x31_checksum(rwd, "V85 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v84)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, never from the in-memory build.
    assert u16(dec, RATIO_NORM_ADDR) == RATIO_NORM_NEW
    assert_frozen(dec, "V85 readback")
    assert_lane_cals(dec, "V85 readback")
    assert_ratio_norm_census(dec, "V85 readback")
    assert_b5_refutation(dec, "V85 readback")
    assert_caller_guard(dec, "V85 readback")
    assert_out_cliff(dec, "V85 readback")
    V84B.assert_keep_list(dec, "V85 readback")
    V84B.assert_pointer_arrays_stock(dec, stock, "V85 readback")
    V84B.assert_manual_modes_frozen(dec, v84, stock, "V85 readback")
    V84B.assert_friction_all_stock(dec, stock, "V85 readback")
    V84B.assert_gain_a_honda(dec, stock, "V85 readback")
    V84B.assert_factor_surface(dec, stock, "V85 readback", reverted=True)
    V84B.assert_engaged_equals_manual(dec, stock, "V85 readback")
    V84B.assert_repoint_and_chain(dec, "V85 readback", done=True)
    V84B.assert_arm_derivation(dec, "V85 readback")
    V84B.assert_insurance_guards(dec, stock, "V85 readback")
    assert_cave_v85(dec, "V85 readback")
    assert assert_probe_cells(dec, "V85 readback", cave_span) == probe_out, \
        "🛑 the readback probe census differs from the built image's"
    assert_no_399_channel(dec, "V85 readback")
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert_identity_modulo(dec, v84, attributed | crc_only, "V85 readback", "V84")
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    print("    ✅ READBACK: the edit value, 0xC40BC's census, the b5 refutation, the caller guard, "
          "the gp-0x6bfc cliff,")
    print("       every FROZEN cell, V84's whole guard suite, the 68-byte cave and its "
          "re-disassembly, the probe census,")
    print("       identity to V84 outside the attributed set, and the full 50/50 CRC chain: ALL "
          "re-verified FROM THE DECODED")
    print("       .rwd PAYLOAD.")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # =================================================================================================
    # WRITE -- only if explicitly enabled
    # =================================================================================================
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WAS WRITTEN TO DISK.")
        print("     Re-run with ACCORD_V85_WRITE=rwd to cut the artefacts.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(
                f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists (on disk "
                f"{hashlib.sha256(existing).hexdigest()}, about to write {img_sha}). A same-number "
                "re-cut destroys a predecessor's snapshot and leaves a flashable artefact NO gate "
                "can check. Rename it `SUPERSEDED-DO-NOT-FLASH-…` deliberately, then re-run.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(
                    f"🛑 a DIFFERENT {OUT} already exists -- exactly ONE flashable .rwd per build "
                    "number. Rename or delete it deliberately, then re-run.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            # ---- 🛑 A SEPARATE FROM-DISK DECODE OF THE SHIPPED FILE -------------------------------
            shipped = Path(OUT).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha, "the shipped .rwd re-hashes wrong"
            FF.assert_x31_checksum(shipped, "V85 shipped")
            sb = parse_x31(shipped)
            assert sb["headers"] == FF.EXPECTED_HEADERS
            assert sb["blocks"] == [{"start": START, "length": END - START}]
            sd = bytearray(v84)
            sd[START:END] = bytes(sb["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert u16(sd, RATIO_NORM_ADDR) == RATIO_NORM_NEW
            assert_frozen(sd, "V85 shipped-from-disk")
            assert_lane_cals(sd, "V85 shipped-from-disk")
            assert_ratio_norm_census(sd, "V85 shipped-from-disk")
            assert_b5_refutation(sd, "V85 shipped-from-disk")
            assert_cave_v85(sd, "V85 shipped-from-disk")
            assert_probe_cells(sd, "V85 shipped-from-disk", cave_span)
            V84B.assert_keep_list(sd, "V85 shipped-from-disk")
            V84B.assert_engaged_equals_manual(sd, stock, "V85 shipped-from-disk")
            V84B.assert_repoint_and_chain(sd, "V85 shipped-from-disk", done=True)
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code), \
                "the written plain image does not re-read as the built image"
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded, and its payload")
            print("     re-verified (the edit, its census, the b5 refutation, the cave, every FROZEN "
                  "cell, engaged==manual,")
            print("     Lever B, 50/50 CRC) INDEPENDENTLY of the in-memory build.")

    print(f"\n  V85 [{VARIANT_TOKEN}] -- image SHA256 {img_sha}")
    print(f"                                    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  ★ CONTROL PATH: ONE CELL, TWO BYTES -- 0x{RATIO_NORM_ADDR:05X} "
          f"{RATIO_NORM_OLD} -> {RATIO_NORM_NEW} (`5802` -> `7017`).")
    print(f"    The friction RELAY becomes VISCOUS: saturation moves {OLD_SAT} -> {NEW_SAT} counts, "
          f"relay index {ri_old:.2f} -> {ri_new:.2f}.")
    print("    Steady-slew friction at/above 500 counts is BIT-IDENTICAL; at/below 50 counts it is "
          "cut by a FLAT 10x.")
    print(f"  ★ TELEMETRY: the cave @0x{CAVE_BASE:05X} REPOINTED onto the relay's own input and its "
          f"own output -- {len(cave_attributed)}/{CAVE_EXTENT} bytes differ,")
    print(f"    EXTENT UNCHANGED at {CAVE_EXTENT} (filled, no padding), hook 0x{HOOK_ADDR:05X} "
          "unchanged, ONE store, no new RAM.")
    print(f"    0x14A byte4: b7 |rate|>={RATE_T_LO} · b6 |rate|>={RATE_T_HI} · "
          f"b5 |fric|>={FRIC_T_HI} · b4 |fric|>={FRIC_T_LO} · b3 FINGERPRINT=1  "
          "(ALL FOUR TWO-SIDED)")
    print("  🛑 THE BRIEF'S b5 (`|gp-0x6b98| > 8192`) WAS **NOT** SHIPPED -- it is structurally "
          "unable to fire (the cell is")
    print("     hard-clamped to +-0x2000 at both live writers, and V55's flown probe saw 99.2% "
          "inside +-512 over 943 s).")
    print("  🛑 THE HONEST RISK: this REMOVES DISSIPATION at low rate -- a FLAT 10x at and below 50 "
          "counts (10.6 deg/s), i.e. most")
    print("     ordinary steering. If S2 or S1 gets WORSE, this is why,")
    print("     and reverting is TWO BYTES. The case for doing it anyway is that a relay is a "
          "limit-cycle generator, not clean damping.")
    print("  🛑 NOT ADDRESSED: no new S1 rate-lane dose, and the ~28 Hz lane-change transient "
          "(excitation, not gain).")
    print("  ⊕ SHIP WITH THE DRIVE (RULE 9, costs no bytes): ~90 s of deliberate ENGAGED hard "
          "cornering at creep.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without touching an image."""
    assert len(EDITS) == 1 and EDITS[0][0] == RATIO_NORM_ADDR
    assert struct.pack("<H", RATIO_NORM_OLD) == bytes.fromhex("5802")
    assert struct.pack("<H", RATIO_NORM_NEW) == bytes.fromhex("7017")
    assert RATIO_NORM_NEW == 10 * RATIO_NORM_OLD, "the edit is a clean 10x on the normaliser"
    assert RATIO_NORM_DISP_ENC == RATIO_NORM_DISP | 1, "🛑 the ld.hu displacement is disp | 1"
    assert 0 < RATIO_NORM_NEW <= 0x7FFF
    # the rung thresholds, re-derived from the shift rather than written down
    assert RATE_T_LO == RATE_K_LO << RATE_SHIFT == 64
    assert RATE_T_HI == RATE_K_HI << RATE_SHIFT == 512
    assert RATE_T_LO > OLD_SAT and RATE_T_HI > NEW_SAT, \
        "🛑 each rate rung must sit ABOVE its saturation point, so `set` IMPLIES `saturated`"
    assert RATE_T_LO / OLD_SAT < 1.3 and RATE_T_HI / NEW_SAT < 1.05, \
        "the rungs are too far above the thresholds they stand for"
    # every window's immediates must fit Format II's signed imm5
    for off, half in ((RATE_K_LO, RATE_K_LO), (RATE_K_HI - RATE_K_LO, RATE_K_HI),
                      (FRIC_T_HI, FRIC_T_HI), (FRIC_T_LO - FRIC_T_HI, FRIC_T_LO)):
        assert -16 <= off <= 15 and 1 <= half <= 8 and -16 <= 2 * half - 1 <= 15
    assert FRIC_T_LO < FRIC_T_HI, "the friction thermometer is not ordered"
    assert len(build_cave()[0]) == CAVE_EXTENT == 68
    assert "+" not in VARIANT_TOKEN and all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN)
    assert SRC_SHA256 not in NOT_THE_BASE
    # the describing-function anchors, as executable facts
    assert abs(relay_index(RATIO_NORM_OLD) - 7.87) < 0.01
    assert relay_index(RATIO_NORM_NEW) == 1.0
    assert relay_index(RATIO_NORM_OLD) / 3.27 > 2.4, \
        "🛑 the claim 'more relay-shaped than V80's bang-bang' must be re-derived, not quoted"


if __name__ == "__main__":
    _self_check()
    build()
