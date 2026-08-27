#!/usr/bin/env python3
"""builds/v80_v107/build_v84_tva.py -- V84 = V83a + LEVER B RESTORED + THE ENGAGED-ONLY DAMPER DELETED. CAL + 1 BYTE.

🛑 STATUS: BUILT (dry-run by default), UNFLASHED. Writing is gated on `ACCORD_V84_WRITE`; the
default is a DRY RUN that verifies everything -- including a full in-memory .rwd encode/decode --
and writes nothing. **NO CAVE CHANGE, NO NEW CODE, NO NEW RAM.** Seven cells: ONE instruction
byte (a displacement repoint that has flown twice) and six calibration halfwords.

★ THE ONE-LINE REASON THIS BUILD EXISTS
----------------------------------------
**RAISE THE DC-NEUTRAL DAMPING AND REMOVE THE DC-OPPOSING DAMPING.** The r24/r26 rate lanes are pure
derivative terms -- at constant torque they contribute nothing, so raising r24 damps oscillation at
**zero steady-state impedance cost**. The mode-26/27 Coulomb damper is `-sign(motor rate) x M(|rate|)`
-- it opposes at *every* rate including a sustained slew, it is **ours** (Honda ships modes 24 == 26
byte-identical) and it was first armed at V74. So: rate lane up, our added damper out. That answers
the operator's constraint verbatim -- *"I just want ratchet gone without limiting the max steering
angle rate under strong LKAS command"* -- because neither lever touches the command path.

THE BASE.  `_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin`
  sha256 `bb717ce8322d35c587e95084e697a5ad98ba6564ee9265bb09a88a2a241cd25a`, asserted before a byte
  moves. V83a is BUILT AND FLOWN (route 68). Measured, cell-stratified against V81:
  **18-22 Hz grind #1 = 2.674x WORSE [1.956, 3.885]**, 6-9 Hz micro-ratchet 1.526x worse, 26-31 Hz
  ring FLAT (1.021) -- which **falsified V83a's own pre-registered damper-dose model of the ring**.
  ⇒ V83a carries NO measured grind-#1 fix, and this build's job is to put one back.

THE EDIT SET -- 7 cells (ONE byte + six halfwords)
--------------------------------------------------------------------------------------------------
  #   cell                       addr      V83a     V84     bytes        equals
  1   r24/r26 gate repoint       0x3AA96   0xC5    0xFB     c5 -> fb     the FLOWN V67 and V68
  2   r24 engaged arm            0xC6446    512    5244     0002 -> 7c14 the FLOWN V67 and V68
  3   FactorC mode-26 Y[0]       0xD77DA    566       0     3602 -> 0000 STOCK (Honda's)
  4   FactorC mode-27 Y[0]       0xD77EE    566       0     3602 -> 0000 STOCK (Honda's)
  5   FactorE mode-27 X[0]       0xD7822     12      60     0c00 -> 3c00 STOCK (Honda's)
  6   FactorE mode-27 X[1]       0xD7824    200     400     c800 -> 9001 STOCK (Honda's)
  7   FactorE mode-27 Y[1]       0xD782C    539     140     1b02 -> 8c00 STOCK (Honda's)

🛑 **EVERY EDIT IS ASSERTED EQUAL TO SOMETHING THAT HAS ALREADY BEEN ON THIS CAR.** Edits 1-2 are
asserted byte-identical to the FLOWN V67 *and* the FLOWN V68 images; edits 3-7 are asserted
byte-identical to `stock_fw_dump/code.bin` at the same address, and their three records are asserted
byte-STOCK over their FULL `rec_len`. Nothing in V84 is a number somebody invented.

⚠ COUNT CELLS, NOT BYTES. Three different numbers describe this build; all three are derived
independently and asserted, so none can absorb an error in the others:
  · **7 cells / 7 functional runs** -- the right way to count a lever set
  ·  13 bytes WRITTEN   -- one `st.b`-shaped byte + six `struct.pack_into` halfwords
  ·  **12 bytes DIFFER** -- edit 5 (12 -> 60) shares its high byte with the base, so it moves ONE byte

LEVER B (EDITS 1-2) -- THE BEST-MEASURED GRIND-#1 RESULT IN THE KIT, PUT BACK
-------------------------------------------------------------------------------
**WHY.** Two flights carried exactly these two cells at exactly these two values: V67 and V68. The
measured result is the best this kit has: **grind #1 (18-22 Hz) 0.40 [0.27, 0.58]**, median
`e_18-22` **109 against stock's 879**, and at creep grind #2 went to **0 bursts**. No other lever in
the corpus has produced a grind-#1 confidence interval that clears 1.0 by that margin. V81, V83a and
every build since V71c have been **byte-stock at both addresses** -- route 67's and route 68's
grinding is *an absence of any fix, not a regression*. This is the third silent loss of a confirmed
fix in this kit (after `0x454FE`), and V84 is the correction.

**EDIT 1, MECHANICALLY.** `0x3AA94` is `84 7f c5 97` = `ld.bu -0x683c[gp],r15`. V850 Format-VII puts
the displacement's bit 0 in the OPCODE field (0x3C vs 0x3D) and hw2's LSB is the width selector, so
because `-0x6806` = `0x97FA` is EVEN, **only `0x3AA96` moves** -- hw1, both register fields and the
high displacement byte are untouched. The result `84 7f fb 97` = `ld.bu -0x6806[gp],r15` is a real
instruction that **already executes at `0x42842` and `0x55C76`**, all four bytes, register fields
included; a third at `0x2A1B6` differs only in reg2. All three are asserted from the image, and the
emitted bytes are re-decoded through `scan_gp_accesses`' INDEPENDENT decoder rather than compared
against our own intent.

**WHAT THE REPOINT BUYS.** `gp-0x683c` has **1 reader / 0 writers** image-wide (that one reader IS
`0x3AA94`) -- it is a dead cell, so `lp` is presently a constant. `gp-0x6806` is the LKAS-active
flag: **99.899% / 99.943% agreement with `carControl.latActive` over 37,914 frames** on V57's flown
probe, at two very different duty cycles (21.73% and 49.88%), 13 transitions total = **0.03-0.05/s**
against a kill band that starts at 30/s. After the repoint the single register `lp` (one writer,
`setfne lp` @`0x3AAA8`, no `jarl` before either consumer) IS "LKAS is applying". Polarity rests on one
byte of V57's flown cave -- `ba05` = `bne`, so V57's bit6 meant `gp-0x6806 == 0` and the agreement
belongs to `!= 0`; re-asserted from the V57 artifact on every run.

**EDIT 2, AND THE NUMBER 5244.** With `sar 0xa` kept stock the lane divides by 1024, so the arm is a
DIRECT replacement for the LERP and `arm / LERP` is the multiplier.
🛑 **A CORRECTION THIS BUILD MAKES TO ITS OWN PARENT.** `v66_v67_explained.r24_gain_q10` hardcodes
**mode 10's** `gain_B` records, and **this car is `TVCA4` -> modes 24/25/26/27** (variant table
`0xCD000`, stride `0x24`, row 11, re-derived here). V67 therefore derived 5244 from a table this car
does not read. It happens to be right -- mode 26's own records give the same **2622** at grind #1's
operating point (7.2 km/h, 128 deg/s) -- but *that was luck, not method*, so V84 re-derives the LERP
by **dereferencing the four `gain_B` pointer arrays at mode 26** and asserts both routes agree.
⊕ The same trap already cost this kit V69/V70: those builds wrote mode-10 `gain_B` and were
**functionally byte-stock**. Their `[5244]x4` is still sitting in mode 10 on this image, inert, and
V84 asserts it unmoved rather than silently "fixing" it.
MEASURED from the image over the engaged regime, `5244 / gain_B_LERP(mode 26)`:
**1.766x at 2 km/h / 20 deg/s ... 2.000x exactly at grind #1's point ... 2.592x at 100 km/h**.
Saturation is closed by arithmetic, not argument: 5120 (input clamp) x 5244 = 1.25% of INT32_MAX, and
the +-8192 lane clamp is first reached at **|dtorque| >= 1601** (derived here through the real lane
including the 3-count deadzone `0xC61F6`) against a MEASURED range of 123-839.

**AND THE PART V67 GOT WRONG, RESTATED HONESTLY.** The repoint puts **r26's arm on the SAME gate**:
`0xC6444` stays stock 512, so while LKAS applies r26's gain becomes a flat 512 instead of its
`gain_A` LERP. V67's header called that harmless because *"r26 is structurally inert"*.
🛑 **THAT ARGUMENT IS RETRACTED** -- the record now splits it: **LEG 1 (the gate) is REVERSED
[EVIDENCE]**, it does not kill r26 in ordinary driving; LEG 2 (magnitude) is downgraded to BELIEF.
**V84 does not rely on it.** It adopts the r26 cut *deliberately*, as the S3 lever, because the
numbers say it is one: measured from the images, V84's engaged r26 arm is **512 at every speed**, and
the flown V72-lineage `gain_A` cut the operator **twice reported fixed the macro ratchet** is
**exactly 512 at every speed up to 10 km/h** -- identical, asserted point by point.
⚠ **Above 10 km/h they diverge and V84 cuts DEEPER**: V72's LERP climbs back to 2664 by 50 km/h,
V84's flat arm does not (0.192x there). That is a real difference from V72 and it is stated rather
than smoothed over -- but it is not unflown: **V67 and V68 carried this exact configuration at road
speed, fault-free.** Direction is loop gain DOWN on that lane, i.e. the safe direction.

**MANUAL ARM: BYTE-FOR-BYTE STOCK.** `lp = 0` selects Honda's LERPs on both lanes. This answers the
operator's standing objection that rate-lane builds change manual feel for an engaged-only symptom.

★★ THE DOSE LADDER -- r24 IS THE ACTIVE INGREDIENT FOR GRIND #1, r26 IS NOT
-----------------------------------------------------------------------------
Delivered dose at grind #1's operating point (7 km/h, 128 deg/s, engaged), with the mode-10 builds
correctly EXCLUDED (they were byte-stock on this car -- see the `gain_B` correction above):

    build                r26 x     **r24 x**     grind #1 median `e_18-22`
    V61                  0.000     **0.000**            2501
    stock / V69 / V70    1.000     **1.000**       879 / 746 / 729
    V72                  0.177     **1.000**        unmoved (0.953)
    V62 / V65            2.000     **2.000**             168
    **V67 / V68**        0.177     **1.994**             **109**

**r24 is monotone across 0x -> 1x -> 2x.** r26 swings **11.3x** at fixed r24 (V72 vs stock) and grind
#1 barely moves (0.953). ⇒ the r24 raise is the active ingredient; the r26 cut is not, and is carried
here for S3 (the macro ratchet) rather than for S1. **This table is also the argument AGAINST restoring
V62's `sar`**: V62/V65 got their 2.00x on BOTH lanes and produced grind #2, where V67/V68 got the same
r24 dose with r26 CUT and produced the best result in the kit at 109.

⚠ **AND IT IS WHY `gain_A` IS LEFT ALONE.** The r26 priority chain is
`lp != 0` -> `0xC6444` (**outranks**) -> `gp-0x671a >= 5` -> `0xC643E` -> the `gain_A` LERP. **Once the
gate is armed, `gain_A` is the MANUAL-ONLY path** and therefore cannot touch an engaged-only symptom.
All four records are asserted equal to Honda's. ⚠ Note the arms **REPLACE** the LERP rather than
scaling it, so Lever B's engaged r26 cut holds at **~0.19x even at >=50 km/h**, where V72's `gain_A`
cut relaxes to exactly 1.000x. That is a deliberate, declared difference from V72, not an oversight.

⊕ **`0xC643E` / `0xC6440` ARE UNREACHABLE IN PRACTICE -- asserted stock, and NOT spent as a lever.**
`gp-0x671a` has **one writer image-wide** (`st.b r7,-0x671a[gp]` @`0x42A12`, in `FUN_000428d4`) whose
only non-zero source is the oscillation detector via `gp-0x67df` -- and `gp-0x67df` (1 reader
`0x428E6`, 1 writer `0x4299C`) has **never been non-zero in this kit** (0/53,991 on V68, 0/186,321 on
V67). So the `state >= 5` arms are dead in practice and a cell spent on them would buy nothing.

THE DAMPER REVERT (EDITS 3-7) -- MAKING ENGAGED IDENTICAL TO MANUAL AND TO HONDA
----------------------------------------------------------------------------------
**WHY.** Honda ships modes **24 == 26** byte-identical across all six factor families, and
`FactorC Y[0] == 0` in all 13 distinct stock records. **The engaged-only damper is OURS, armed at
V74.** Its sign is `-sign(motor rate)`, so it fights the **driver** too, even turning WITH the
command -- which is what "manual steering much heavier when engaged" is. Measured engaged/manual
effort per deg/s at 10-40 km/h: **1.471 [0.980, 1.812]**, direction-independent.

🛑🛑 **AND MODE 27 IS NOT OPTIONAL -- IT IS CARRYING V81's ENTIRE DAMPER PACKAGE.** Row 11 `TVCA4`
resolves to mode indices **[24, 25, 26, 27]**, columns 2/3 being the engaged pair, and row 11 is one
of only four rows where all four columns are distinct ⇒ **mode 27 is a genuinely separate engaged
mode on this car.** V83a reverted mode 26 and left mode 27 untouched. Measured from the V83a bytes by
this build, the delivered `|gp-0x6bd0|` at 5 km/h over rates [20,40,99,119,150,255,530,1000,1941]:

    mode 24 (Honda)  0   0   0   0   0   0   0   0   0     <- dead below 35 km/h, by design
    mode 26 (V83a)   0   0   8  13  20  44  90 140 238
    mode 27 (V83a)  12  44 137 169 218 297 297 297 297     <- a 297-count PLATEAU. V75's damper, whole.

**Mode 27's describing-function relay index `N(50)/N(500)` on V83a is 1.45; Honda's is 0.00.** The
1.45 is not a coincidence -- it reproduces STATE.md's recorded V75 row to three decimals
(`[0.581, 1.065, 1.319, 1.410, 1.317, 0.734, 0.375]` vs the recorded
`[0.580, 1.065, 1.319, 1.410, 1.317, 0.734, 0.375]`), which is how this build's `describing_function`
is validated against the record before it is trusted. Leaving mode 27 would be both an uncontrolled
confound and a live relay-shaped surface. After V84 both engaged modes read **0.00 -- Honda's viscous
surface**, and every record is byte-STOCK.

⚠ **A CORRECTION TO THE AUTHORISING BRIEF, MEASURED.** The brief's gate said *"both engaged modes
must be byte-identical to mode 24"*. **Mode 27's Honda pair is mode 25, not mode 24.** Stock
`FactorC` m25/m27 are `[0, 233, 426, 875]` while m24/m26 are `[0, 234, 429, 908]` -- the pairing is
24<->26 and 25<->27, re-derived here from the variant table and asserted both ways. Holding mode 27
to mode 24 would fail on Honda's own firmware. The edit set is unchanged; only the gate is corrected.

⚠ **AND A SECOND ONE:** the brief's `TOUCHED_BLOCKS` named `0x13000` for `0x3AA96`. That block is
**[0x013000, 0x0C4FFC)** -- named by its START, its CRC trailer is at **0x0C4FFC**. Three blocks
move, trailers `0x0C4FFC / 0x0C6FFC / 0x0D7FFC`, derived by `V53.owning_block` and asserted. **The
cave at `0xC4B34` lands in that same first block**, so the probe repoint adds no fourth block.

★ AND THE FOLD: THE ENGAGED `FactorC` WAS NON-MONOTONE, AND EDITS 3-4 REMOVE IT
---------------------------------------------------------------------------------
V83a's `FactorC` m26 is `Y = [566, 234, 429, 908]` -- it **FALLS** 566 -> 234 between X = 2240 and
3840, a **2.42x dip**. A damper factor that decreases as its axis rises is a negative-slope
characteristic and is exactly the shape RULE 12 warns about. Mode 27 carries the identical fold
(`[566, 233, 426, 875]`). Edits 3 and 4 remove both and restore Honda's monotone rows. Measured here
and asserted: **`FactorC`/`FactorE` Y are non-decreasing for modes 24, 25, 26 AND 27 on the OUTPUT**,
and the m26/m27 folds are shown to be present on the INPUT so the check cannot be vacuous.

⊕ TWO CHEAP INSURANCE GUARDS, named explicitly rather than left to the whole-image identity check:
  · the damper **ceiling record `0xD209C`** and its **float twin `0xC6554/58/5C/60`** (300.0 / 800.0 /
    0.5 / 1.0) -- lockstep-checked at 5/1024 in firmware and escalating to a **DTC 0x1d hard
    shutdown** on mismatch. Asserted byte-STOCK.
  · the **role table `0xC4124`** -- a slot carrying role **6 or 7** lets `gp-0x67ac` read 1, which
    makes the aggregator drop r24, r26 **and** the damper, i.e. it would make **every lever in V84
    vacuous**. Asserted byte-STOCK, and asserted to contain no 6 and no 7 (measured: it does not).

★★ THE STRONGEST GATE THIS BUILD HAS -- V84 == THE FLOWN V67/V68 ON THIS CAR'S OWN MODES
------------------------------------------------------------------------------------------
Because edits 3-7 put the damper back to Honda, and because V67/V68 predate the damper's arming,
**every assist surface this car reads ends up byte-identical to the two builds whose 0.40 [0.27,0.58]
grind-#1 result V84's prediction rests on.** Asserted, not asserted-ish: all six factor families
(`FactorB/C/D/E`, ceiling, friction) at modes **24, 25, 26 and 27**, all four `gain_B` pointer arrays
at those four modes, and all four `gain_A` records -- **V84 == V67 == V68 == STOCK**, whole records,
dereferenced through their pointer arrays. Over the FULL 1 MiB V84 differs from the flown V67 at only
**236 bytes**, and every one is attributable: `0x454FE` (V42's macro-ratchet fix, which V84 HAS at
`0xB5` and V67 did NOT at `0xBA`), the 68-byte probe cave, the CRC trailers, mode-10 `gain_B`
(V69/V70's inert writes) and **other cars'** `FactorC`/`FactorE` records at modes this car never
dereferences. ⇒ the S1 prediction below is an interpolation onto a measured point, not an
extrapolation off one.

★★ THE PROBE -- THE EXISTING 68-BYTE CAVE, REPOINTED. NO NEW CAVE, NO SECOND HOOK.
------------------------------------------------------------------------------------
**WHY IT HAD TO MOVE.** V83a's five bits ride a magnitude thermometer on `gp-0x6bd0`, the damper --
and V84 deliberately drives the engaged damper's creep contribution to **exactly zero** (edits 3-4,
and `FactorC` is flat below 35 km/h). Every rung would report a structurally predictable zero. That
is the recorded V64/V68/V69 failure mode: **a probe spent on a quantity that cannot vary.**

**WHAT IT NOW MEASURES**, on `0x14A` byte 4 bits 7:3 -- the field V55/V75/V81/V83a have proven
end-to-end on the comma:

| bit | rung | why |
|---|---|---|
| `byte4[7]` | `gp-0x6ada >= +1024` | **the most important bit in the build** -- delivered r24, positive |
| `byte4[6]` | `gp-0x6ada <= -1024` | delivered r24, negative. `bit7 OR bit6` = |r24| >= ~1024 at FULL duty |
| `byte4[5]` | `gp-0x67fe in {1,2}` | FactorD's liveness gate. **If this reads 0, every FactorD number in the kit is void.** |
| `byte4[4]` | `gp-0x6a10 >= 8` | FactorD's angle-error axis -- converts the physics estimate to EVIDENCE |
| `byte4[3]` | **hard-coded 1** | build fingerprint, so route-69 logs can never be confused with route-68's |

🛑🛑 **THE ONE DEVIATION FROM THE SPECIFIED BIT MAP, AND IT IS FORCED BY THE 68-BYTE EXTENT.** The
brief asked for `byte4[7]`/`byte4[6]` as **two magnitude levels** on `gp-0x6ada`, plus `byte7[7:6]`
carrying `gp-0x6a10 >= 4` and `>= 20`. **Neither fits, and the arithmetic is exact, not approximate:**
  · Two magnitude levels need an ABS (`cmp r0,r6` / `bge` / `subr`), and the r24 section then costs
    24 B instead of 18. Total **72 B > 68**.
  · `byte7` is a SECOND read-modify-write (`ld.bu` 4 + `andi` 4 + `or` 2 + `st.b` 4 = **14 B
    minimum**, before any rung). Total **>= 80 B**.
  Mandatory tail (payload RMW + displaced `movea` + `jmp [lp]`) is 20 B and the accumulator overhead
  (`mov`/`shl`/fingerprint) is 6 B, leaving **42 B** for all logic. The shipped design uses **66 of
  68**, with the last 2 bytes asserted `0xFF`.
  **What was traded:** `bit6` becomes the NEGATIVE excursion instead of a second magnitude level.
  ⊕ That is arguably the better trade and not merely the affordable one: `bit7 OR bit6` gives
  `|r24| >= 1024` at **full duty** (an abs-thermometer's two rungs each see only half the waveform),
  and the pair additionally reveals any DC asymmetry in the lane for free.

⚠ **BUT `byte7[7:6]` IS CONFIRMED FREE AND CONFIRMED SURVIVABLE** -- measured from the packer, as
asked, not inferred from the rlogs. Around our hook at `0x55C0E`:
```
0x55BF6  andi 0x0003,r10,r6   /  0x55BFA shl 0x4,r6      ; r10&3 -> bits 5:4
0x55BFC  andi 0x00cf,r8,r8    ; PRESERVES bits 7:6, writes 5:4
0x55C02  st.b r8,-0x1511[gp]
0x55C0E  <-- OUR HOOK
0x55C1C  ld.bu -0x1511[gp],r6
0x55C24  andi 0x00f0,r6,r6    ; 🛑 PRESERVES bits 7:4 -- anything we write to 7:6 SURVIVES
0x55C2A  st.b r6,-0x1511[gp]
```
⇒ `byte7[7:6]` is written by **nothing**, and the post-hook RMW's `0x00f0` mask keeps it. It is
available to a future build that is allowed more than 68 cave bytes. 🛑 **`byte7[5:4]` is NOT free** --
`0x55BF6`/`0x55BFA` pack `gp-0x6880 & 3` there every cycle.

**RUNG SIZING, from the lane's own reachable output** (`feedback-size-probe-rungs-against-lane-
reachable-output`; V69 spent all three rungs for nothing because bit4 was structurally vacuous):
  `r24 = (clamp(gp-0x4f62, +-5120) * gain) >> 10`, deadzone 3, clamp +-8192. Measured `d`: p50 ~ 104,
  21 Hz peak ~ 367. Manual arm (stock `gain_B` ~ 3072 at creep): r24 p50 ~ 312, peak ~ 1101. Engaged
  arm (Lever B, 5244): p50 ~ 532, peak ~ 1880. After `sar 0x8` (/256): manual 1.2 / 4.3, engaged
  2.1 / 7.3. **T = +-4 counts of q, i.e. |r24| >= 1024.**
  · CAN IT FIRE? yes -- engaged peaks reach q ~ 7.3, manual ~ 4.3.
  · CAN IT NOT FIRE? yes -- both p50s (1.2 and 2.1) are well below 4.
  · Predicted duty for a sinusoid, `(2/pi)*arccos(T/A)`: manual **0.24**, engaged **0.64** -- a
    **2.6x step at the engagement edge**, and the manual arm is byte-stock by construction, so **the
    drive contains its own within-route A/B**.
  `gp-0x6a10 >= 8`: the physics estimate is 6.71 ct @ 27.75 Hz, 9.31 @ 20 Hz, 23.89 @ 7.79 Hz, so 8
  sits between the ring and 20 Hz. Fires at 20 Hz and at the ratchet, does not fire at the ring.
  **Neither rung is implied by another and every rung can both fire and not fire.** ⚠ the operating-
  range estimate is [BELIEF]; this probe is what converts it to EVIDENCE.
  🛑 **`sar` FLOORS TOWARD -inf, AND THE EXHAUSTIVE SELF-CHECK CAUGHT ME GETTING THIS WRONG.** The
  obvious `cmp -0x4` fires at `r24 <= -769`, NOT -1024 -- a **255-count asymmetry** a hand-check
  would have shipped. The two immediates are therefore **NOT** `+-N`: `cmp 0x4` / `blt` gives
  `r24 >= +1024`, and `cmp -0x5` / `bgt` gives `r24 <= -1025`. Symmetric within **ONE count in
  1024**, and both are asserted EXHAUSTIVELY over the lane's entire reachable range -- all 16,385
  values of `r24` in [-8192, +8192].

**MECHANICS AND WHAT IS *NOT* CHANGING.** Same hook `0x55C0E`, same `jarl`, same cave base
`0xC4B34`, **`CAVE_EXTENT` = 68, NOT GROWN**, same 5 bits of `0x14A` byte4[7:3], same `andi 0x7`
preserving the live `STEER_SENSOR_STATUS` bits 2:0, same displaced-`movea` re-execution, same
`jmp [lp]`. This is the repoint V58/V59/V64/V68/V69/V70/V75 have all performed. **No new RAM is
allocated** (V48B's brick was a RAM collision at `gp-0x14FA`) and **no dynamics enter any loop**
(V48B's other leg). **No latched or sticky bits** -- no stock writer clears `0x14A` byte4[7:3], so a
latched bit could never clear; every rung is recomputed from scratch each pass.

**GATE 1 FOR THE PROBE**, by `build_v81_tva.census_gp4` (disp16 + **disp23** + absolute literal +
`movhi`/`movea`), re-run on input, output and readback:
    `gp-0x6ada`  **1 writer** (`st.h r24,-0x6ada[gp]` @`0x3AD5A`) / **0 readers** -- free, blast-radius zero
    `gp-0x6adc`  **1 writer** (`st.h r26,-0x6adc[gp]` @`0x3AD4E`) / **0 readers** -- not used by V84
    `gp-0x6a10`  3 writers / 14 readers, **every reader `ld.hu` ⇒ UNSIGNED, so no ABS is needed**
    `gp-0x67fe`  5 writers / 55 readers, all `ld.bu` ⇒ unsigned byte
  Zero absolute-literal hits and zero `movhi`/`movea` hits on all four. **The cave READS these cells
  and writes NONE of them**, asserted as a measurement.
  🛑 **THE ONE-BIT TRAP, CLOSED EXPLICITLY**: `ld.h` is op `0x39` and `st.h` is op `0x3B` -- ONE BIT
  apart -- and `gp-0x6ada`'s only firmware instance **IS the store**. The cave emits `0x39` (a LOAD)
  and the build asserts both: our emitted opcode is 0x39, and the firmware's instance is 0x3B.

**SAMPLING RATE, stated because it bounds the interpretation.** The hook runs in the CAN-TX packer at
**100 Hz**. That is ~12.8 samples/cycle at 7.79 Hz (fine), but it is **UNDER-SAMPLED at 27.75 Hz** ⇒
**every rung is a DUTY-CYCLE statistic, never a peak**, and the ring's numbers must be read that way.

**HONEST COST.** This takes V84 from "cal + one code byte" to "cal + one code byte + a cave repoint",
which is a higher risk class -- caves are this kit's ONLY bricking class (V24, V27, V48B). The
mitigations, each checked rather than asserted: the extent is unchanged at 68; the hook is unchanged;
no RAM is allocated; no loop dynamics change; the checksum `FUN_00057b24` is called after the hook and
**auto-covers** whatever the cave wrote; every emitted halfword is pinned to a real instruction in the
stock image; and **both the cave and its re-disassembly are read back out of the BUILT image** by a
self-contained Python decoder that is first calibrated against V75's decoder on V75's own cave bytes.
⊕ **The probe is read-only telemetry into spare CAN bits and touches no control path**, so it cannot
confound Lever B's measurement.

GATE 1 -- RAM OWNERSHIP.  **PASS.** [EVIDENCE]
------------------------------------------------
V84 allocates no RAM, adds no instruction, moves no cave byte and introduces no new writer of
anything. The one code byte **retargets an existing load**; it does not create one.
  · **The census is re-run FRESH on this image, not inherited** -- a raw Python LE scan over BOTH
    displacement parities PLUS the 6-byte extended-disp/disp23 form, by TWO independent decoders,
    on the input, the output and the `.rwd` readback:
      before: `gp-0x683c` **1 reader / 0 writers** (the reader is `0x3AA94` itself),
              `gp-0x6806` **13 readers / 16 writers**, all `ld.bu`/`st.b`
      after : `gp-0x683c` **0 readers / 0 writers -- UNREFERENCED image-wide**,
              `gp-0x6806` **14 readers / 16 writers**, the 14th being the repoint
    The write set is asserted IDENTICAL across the edit: **a repoint cannot create a writer, and this
    build fails if it did.** The 7 extended-form candidates on `gp-0x6806` are each confirmed to be
    32-bit aliases of an already-counted `st.b`, not new accesses.
  · V84 READS `gp-0x6806`; it never writes it. It writes no RAM at all.
  · The `lp` chain is asserted instruction by instruction from the image -- `cmp r0,r15` @`0x3AAA6`,
    `setfne lp` @`0x3AAA8`, both consumers (`0x3AB56`/`0x3AB5E` r26, `0x3AC04`/`0x3AC08` r24), and the
    FIRST `jarl` @`0x3ACDC` which is **after both consumers**, so `lp` cannot be clobbered.
  · The 68-byte cave at `0xC4B34` and the hook at `0x55C0E`: byte-identical to V83a AND equal to
    `build_v75_tva.build_cave()`'s from-scratch re-derivation, then re-disassembled out of the built
    image by V75's own decoder. **Zero cave risk spent.** Caves are this kit's ONLY bricking class.
  · `0xC407E`'s census (0 writers / 3 signed `ld.h` readers) and `0xC63A0`'s (1 reader `0x381AC`,
    0 writers) are both re-run and asserted unchanged across the edit.

GATE 2 -- CLOSED-LOOP STABILITY (MAGNITUDE **AND** PHASE).  Argued honestly.
------------------------------------------------------------------------------
  PHASE. **Unchanged, literally.** V84 introduces no filter, no pole, no zero, no delay, no new
  state, no new sample point and no task-order change. Edit 1 changes WHICH RAM byte an existing
  `ld.bu` reads -- same instruction, same cycle, same slot. Edits 2-7 replace static table outputs
  with other static values. Every pole, zero and task-order relationship in the image is bit-identical
  to V83a's. [EVIDENCE]

  MAGNITUDE. Three directions, stated separately because they do not all point the same way:
   (a) **r24 RISES while engaged**, to 1.766-2.592x measured over the regime. This is the one loop
       gain that goes UP, and its GATE-2 justification is not "it is small" -- it is that **this
       exact cell at this exact value flew twice (V67, V68), fault-free, at all speeds**, and the
       lane is linear there (saturation at 1601 vs a measured max of 839).
   (b) **r26 FALLS while engaged** (512 flat, 0.167-0.200x of Honda's LERP) -- DOWN.
   (c) **The damper FALLS to Honda's** in both engaged modes -- DOWN, and it moves AWAY from every
       nonlinearity: the relay index goes 1.45 -> 0.00 on mode 27 and the delivered dose goes to
       exactly mode 24's / mode 25's. Nothing on the reported grid clips.
  🛑 **RULE 12 IS APPLIED AS SHAPE, NOT AS A BOUND.** "Does not clip" is NOT "is not a relay" -- V80
  proved that on-car with a supremum that equalled the ceiling EXACTLY and passed every no-clip
  guard. This build computes the **delivered dose over the full (speed x rate) grid from the BUILT
  image**, plus the **describing-function relay index `N(50)/N(500)`** and the **flatness `max/min`**,
  for modes 24/25/26/27, and asserts the engaged columns equal their manual pairs EXACTLY.

★ PRE-REGISTERED, FALSIFIABLE -- recorded BEFORE the drive, on purpose
------------------------------------------------------------------------
  **S1, grind #1 (18-22 Hz, engaged creep):** expect **~0.40x V83a's level**, i.e. back to V67/V68's
  median `e_18-22` ~109 from V83a's stock-band level.
  🛑 **IF GRIND #1 DOES NOT IMPROVE, LEVER B IS FALSIFIED ON A THIRD INDEPENDENT FLIGHT AND THE RATE
  LANE SHOULD BE ABANDONED AS AN S1 LEVER.**
  **S3, macro ratchet (<=30 mph under strong command):** expect improvement -- the engaged r26 arm is
  numerically V72's cut, which the operator twice reported fixed it. **No instrument exists; the
  operator's report is the arbiter.**
  **S2, micro-ratchet (7.79 Hz):** **GENUINELY UNCERTAIN, and V84 is its first real test.** At
  7.79 Hz r24's transfer is ~0.52 with `Re/|G|` ~ **-0.995** (near-pure damping), so a 1.77-2.59x
  raise adds real damping there at zero DC cost. ⚠ **[BELIEF]** -- that transfer figure is carried
  from the authorising analysis and is NOT re-derived from the bytes here. No build has ever moved S2
  except V80's unflyable `k` = 4.16. **This is a hypothesis, not a promise.**
  **S4, excess friction / impedance:** the engaged-vs-manual asymmetry should be **STRUCTURALLY
  ZERO** afterwards -- all six families identical across modes 24/25/26/27. **This one is checkable
  from the bytes, not just from feel, and this build checks it.**

🛑 WHAT V84 DOES **NOT** ADDRESS -- say it plainly so it cannot be discovered later
-------------------------------------------------------------------------------------
  · **The highway / high-speed grind.** V67 and V68 both carried Lever B and **the highway grind was
    still present.** Lever B is not the highway answer and V84 does not claim to be one.
  · **The ~28 Hz lane-change transient.** Measured **dose-independent**, full amplitude on the STOCK
    rate lane, non-monotone in dose ⇒ **excitation, not gain.** Do not chase the rate lane for it.
  · **Grind #2 under LKAS.** V67's own header said it: the gate removes V62's amplification from
    every condition where the gate is FALSE, but it does not act on grind #2's mechanism.

🛑 THE HONEST COST, NOT BURIED
--------------------------------
  · **Engaged r26 damping is cut to 512 flat at ALL speeds** -- deeper than V72 above 10 km/h and
    deeper than anything except V67/V68. "Less damping" is not "no effect"; V56 is on record for
    exactly that.
  · **V84 gives up the last of the damper dose.** 6-9 Hz was FLAT across `k` = 0.58 -> 1.58 and
    improved only at V80's `k` = 4.16, which cost a 2.09x broadband HF lift and the worst grinding
    ever recorded -- so on the measured evidence the dose was cheap to give up. But V84 goes to
    **zero engaged damper below 35 km/h**, which is Honda's operating point and not a tested one for
    *this* car's symptoms. If the micro-ratchet gets worse, edits 3-7 are the cause and reverting
    them is 10 bytes.
  · **A feel change the operator will notice first:** the engaged wheel gets LIGHTER, at every speed,
    because the added Coulomb drag is gone.

Usage:
    python builds/v80_v107/build_v84_tva.py                            # DRY RUN, verifies everything, writes nothing
    ACCORD_V84_WRITE=rwd python builds/v80_v107/build_v84_tva.py       # writes the plain image AND the flashable .rwd
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, START/END, encoders)
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v54_tva as V54                # noqa: E402  (shl, andi, or_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldh, cmp_imm5, ldbu_any encoders)
import build_v64_tva as V64                # noqa: E402  (gp_access_census)
import build_v67_tva as V67                # noqa: E402  ★ LEVER B's origin -- repoint, arm, guards
import build_v68_tva as V68                # noqa: E402  (cave geometry; Lever B's second flight)
import build_v71b_tva as GA                # noqa: E402  ★ the gain_A record model + its own guard
import build_v72_tva as V72                # noqa: E402  (CAVE_EXTENT, 0xC63A0 census)
import build_v74_tva as V74                # noqa: E402  (record readers, censuses, mode columns)
import build_v75_tva as V75                # noqa: E402  (cave re-derivation, probe census, surface)
import build_v81_tva as V81                # noqa: E402  ★ census_gp4 -- the kit's 4-method gp census
import build_v83a_tva as V83A              # noqa: E402  ★ THE BASE's builder -- its attributed set
import scan_gp_accesses as SCAN            # noqa: E402  (the INDEPENDENT Format-VII decoder)
import v66_v67_explained as EX             # noqa: E402  (the r24 lane arithmetic)
import v72_lane_model as LM                # noqa: E402  (lerp_int)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
CAVE_BASE = V68.CAVE_BASE                          # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT                      # 68 -- the PROVEN extent. Never grow it.
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
TP = LM.TP                                         # 0xBF000
GP = V67.GP                                        # 4

u16, s16, u32 = V75.u16, V75.s16, V75.u32
rec_any, rec_len, rec4_y = V74.rec_any, V74.rec_len, V74.rec4_y
factor_rec, ceiling_floor = V74.factor_rec, V74.ceiling_floor
damper_authority = V74.damper_authority

# =====================================================================================================
# THE BASE -- V83a, the cut that flew route 68
# =====================================================================================================
SRC_BIN = plain_image_path("_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin")
SRC_SHA256 = "bb717ce8322d35c587e95084e697a5ad98ba6564ee9265bb09a88a2a241cd25a"
NOT_THE_BASE = {  # sha256 -> why it must never be accepted
    "38baa9cad1f858e4b719f7135ff4ff3b3442d38052fdb38835bc9914bfb98f5c":
        "the SUPERSEDED 11-edit V83a cut. It carries 0xC63A0 = 2048 and NEVER FLEW.",
    "4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b":
        "_v81 -- V83a's OWN base. It carries the FactorE m26 dose and V72's gain_A cut; V84's "
        "preconditions are stated against V83a, not V81.",
    "e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c":
        "_v75_CY0.566-EX1.200_magprobe -- it carries 0xC407E = 850, the DTC-0x1d fault mechanism.",
}
STOCK_BIN = stock_fw_path("code.bin")
# ⊕ the two images LEVER B's on-car result belongs to. Edits 1-2 are asserted against BOTH.
V67_BIN, V67_SHA256 = (plain_image_path("_v67_plain_image.bin"),
                       "5e01bcc4b34a52831fd524cb9af765a01a8dfa3e2c4782d81b3efcb6c94f8c96")
V68_BIN, V68_SHA256 = (plain_image_path("_v68_plain_image.bin"),
                       "9106044abc835529b014d6204904c86bc0587fab4a55facd08d77a84cd0c6226")
# ⊕ the chain anchor: the base's own base, so V84 = V81 + V83a's set + V84's set + CRC.
V81_BIN, V81_SHA256 = V83A.SRC_BIN, V83A.SRC_SHA256

# =====================================================================================================
# THE MODE COLUMNS -- 🛑 THIS CAR IS `TVCA4` -> [24, 25, 26, 27], and 24<->26 / 25<->27 ARE THE PAIRS
# =====================================================================================================
LIVE_MODE = V75.LIVE_MODE                       # 26 -- the engaged mode confirmed twice on-car
LIVE_MODE_2 = 27                                # the SECOND engaged column. V83a left it fully loaded.
MANUAL_MODE = 24                                # mode 26's Honda pair
MANUAL_MODE_2 = 25                              # 🛑 mode 27's Honda pair -- NOT mode 24
MODE_PAIRS = ((LIVE_MODE, MANUAL_MODE), (LIVE_MODE_2, MANUAL_MODE_2))
THIS_CAR_MODES = (MANUAL_MODE, MANUAL_MODE_2, LIVE_MODE, LIVE_MODE_2)
ENGAGED_EXPECTED, DISENGAGED_EXPECTED = V75.ENGAGED_EXPECTED, V75.DISENGAGED_EXPECTED
THIS_CAR_ROW, THIS_CAR_KEY = V75.THIS_CAR_ROW, V75.THIS_CAR_KEY     # 11, "TVCA4"
VARIANT_TABLE, VARIANT_STRIDE = 0xCD000, 0x24
VARIANT_MODE_OFF = 0x12                         # the four mode indices, at row + 0x12
N_MODES = 34
Q10 = V75.Q10

# =====================================================================================================
# THE EDIT SET -- (addr, width, V83a value to ASSERT, value to WRITE, group, label)
# 🛑 width 1 = ONE instruction byte (the repoint). width 2 = a calibration halfword.
# =====================================================================================================
REPOINT_ADDR = V67.REPOINT_ADDR                 # 0x3AA94  `ld.bu -0x683c[gp],r15`
REPOINT_BYTE = V67.REPOINT_BYTE                 # 0x3AA96  the ONLY byte that moves
REPOINT_FROM, REPOINT_TO = V67.REPOINT_FROM, V67.REPOINT_TO     # 847fc597 -> 847ffb97
DEAD_DISP, GATE_DISP = V67.DEAD_DISP, V67.GATE_DISP             # 0x683C (dead) -> 0x6806 (latActive)
ARM_ADDR, ARM_STOCK, ARM_NEW = V67.ARM_ADDR, V67.ARM_STOCK, V67.ARM_NEW     # 0xC6446, 512, 5244
R26_ARM_ADDR, R26_ARM_STOCK = V67.R26_ARM_ADDR, V67.R26_ARM_STOCK           # 0xC6444, 512
GRIND1_KMH, GRIND1_DEGS = V67.GRIND1_KMH, V67.GRIND1_DEGS                   # 7.2 km/h, 128 deg/s
GRIND1_LERP = V67.GRIND1_LERP                                               # 2622

FACTOR_C_M26_REC, FACTOR_C_M27_REC = 0xD77D0, 0xD77E4
FACTOR_E_M26_REC, FACTOR_E_M27_REC = 0xD780C, 0xD7820
REC4_X_OFF, REC4_Y_OFF = V75.REC4_X_OFF, V75.REC4_Y_OFF                     # 0x02, 0x0A

EDITS = (
    (0x3AA96, 1, 0xC5, 0xFB, "repoint",   "r24/r26 gate repoint"),
    (0xC6446, 2,  512, 5244, "arm",       "r24 engaged arm"),
    (0xD77DA, 2,  566,    0, "FactorC26", "FactorC mode-26 Y[0]"),
    (0xD77EE, 2,  566,    0, "FactorC27", "FactorC mode-27 Y[0]"),
    (0xD7822, 2,   12,   60, "FactorE27", "FactorE mode-27 X[0]"),
    (0xD7824, 2,  200,  400, "FactorE27", "FactorE mode-27 X[1]"),
    (0xD782C, 2,  539,  140, "FactorE27", "FactorE mode-27 Y[1]"),
)
# 🛑 The two provenance classes. Every edit is in exactly one, and the build asserts BOTH.
FLOWN_V67_GROUPS = ("repoint", "arm")                       # == the FLOWN V67 AND V68, byte for byte
STOCK_GROUPS = ("FactorC26", "FactorC27", "FactorE27")      # == HONDA, byte for byte, whole record
REVERTED_RECORDS = {"FactorC26": FACTOR_C_M26_REC, "FactorC27": FACTOR_C_M27_REC,
                    "FactorE27": FACTOR_E_M27_REC}

# ---- the surfaces, before and after, stated as literals so an import drift FAILS here --------------
FACTOR_C_M26_BASE_Y, FACTOR_C_M26_NEW_Y = [566, 234, 429, 908], [0, 234, 429, 908]
FACTOR_C_M27_BASE_Y, FACTOR_C_M27_NEW_Y = [566, 233, 426, 875], [0, 233, 426, 875]
FACTOR_E_M27_BASE_XY = ([12, 200, 2500, 4000], [0, 539, 539, 927])      # == the FLOWN V81's m26
FACTOR_E_M27_NEW_XY = ([60, 400, 2500, 4000], [0, 140, 539, 927])       # == Honda's
FACTOR_E_M26_XY = FACTOR_E_M27_NEW_XY                                   # V83a already reverted m26

# =====================================================================================================
# WHAT MUST NOT MOVE -- stated by VALUE, as literals, so a drift in any imported module FAILS here
# =====================================================================================================
KEEP_CELLS = {
    0xC6444: (512,  "🛑 r26's arm -- it rides the SAME `lp` the repoint makes live. LEFT AT STOCK "
                    "512 DELIBERATELY: that is the S3 lever (== V72's cut at <=10 km/h). NOT raised."),
    0xC643E: (1536, "gain_A arm, stock."),
    0xC6440: (2048, "the third arm (gp-0x671a), stock."),
    0xC6442: (1024, "gp-0x671d's arm -- it OUTRANKS the repointed gate. Stock."),
    0xC644A: (1024, "V43's dirty-derivative pole. FLASHED, NULL. Stock."),
    0xC6450: (1024, "V46's lever. FLASHED, NULL. Stock."),
    0xC6CD0: (3564, "V57's decoupled forward-reader cell -- the 4x LKAS setpoint. INTACT."),
    0xC646C: (891,  "the SHARED sensor scale -- V57 decoupled the forward reader OFF it. STOCK."),
    # 🛑 RELABELLED 2026-08-08. These are NOT a deadband arm -- the pre-gain deadband is
    # 0xC61B8 = 102, the NEXT cell, and it was never rescaled alongside the gain. Both of
    # these are output clamps and both are 4x Honda (512 -> 1024 at V22 -> 2048 at V38).
    0xC61B2: (2048, "ARBITRATION output clamp (FUN_0002b422, +/-tp+0x71b2). 4x Honda's 512."),
    0xC61B4: (2048, "LKAS-GAIN output clamp (+/-tp+0x71b4). 4x Honda's 512."),
    0xC61B8: (102,  "the fixed 102-count pre-gain deadband. ELIMINATED for the vibration; frozen."),
    0xC61F6: (3,    "the r24 lane deadzone -- the 1601 saturation threshold is DERIVED from it."),
    0xC407E: (511,  "🛑 THE DTC-0x1d INTERLOCK. Honda's clamp, one count under its own 512 trip. "
                    "V73 raised it to 850 and V74/V75 HARD-FAULTED. RULE 11."),
    0xC62EA: (0,    "the low-speed steer lockout, removed since V52."),
    0xC63A0: (1024, "🛑 the Path-2 damper weight. V83a set it to Honda's 1024. RAISING IT IS NOT "
                    "AUTHORISED -- the directive was retired as a FREEZE, not as a licence."),
    0xC63AC: (102,  "the Path-2 accumulator's one-pole IIR coefficient. UNTOUCHED."),
    0xC6206: (512,  "stock -- V40 bricked the ignition here."),
    0xC6208: (205,  "stock -- V40 bricked the ignition here."),
    0xC521A: (3584, "🛑 inside the CRC-SKIPPED block [0xC5000,0xC5FFC). Untouched."),
    0xC5232: (3584, "🛑 inside the CRC-SKIPPED block [0xC5000,0xC5FFC). Untouched."),
    0xC6158: (512,  "the ceiling's tp+0x7158 FALLBACK -- both branches must still yield 512."),
    0xC407C: (461,  "the interlock clamp's NEIGHBOUR. Owner UNIDENTIFIED. Untouched."),
}
KEEP_BYTES = {
    0x454FE: (0xB5, "V42's macro-ratchet fix (`br` not `bne`). 🛑 KEEP -- it was silently lost once "
                    "already, and V67/V68 did NOT have it (they read 0xBA)."),
    0x3AB76: (0xAA, "the r26 `sar` site -- STOCK. 🛑 V62's `a9` CAUSES GRIND #2, and on a GATED "
                    "build it doubles the PRODUCT of the 512 arm, partially undoing Lever B."),
    0x3AC20: (0xAA, "the r24 `sar` site -- STOCK. Same reason; the fix is an ABSENCE."),
    0xC64C8: (0x00, "the aggregator mode selector -- 0 = pass-through. Mode 1 DELETES the aggregator "
                    "contribution. UNTESTED, and not this build's business."),
    0xC64C9: (0x00, "the blend mux. Never written by any build."),
    0xC64FA: (0x05, "CEIL, a BYTE cal (reading it as u16 gives 517). The third arm's threshold."),
}
KEEP_HALFWORDS = {
    0x2A1F0: (0x7CD0, "V57's decoupling displacement -> tp+0x7CD0 = 0xC6CD0. The 4x LKAS path."),
}
KEEP_F32 = {
    0xC4004: (bytes.fromhex("0000003f"), 0.5,
              "the DTC-0x1d monitor's THRESHOLD (512 counts). FROZEN -- V84 loosens nothing."),
}
KEEP_ZERO_RUNS = {
    0xC6564: (40, "the r26 average's cal base -- 40 bytes of exact zero. V67 leaned its whole "
                  "'r26 is inert' argument on this; 🛑 THAT ARGUMENT IS RETRACTED and V84 does not "
                  "rely on it, but the record is still asserted so a change would be VISIBLE."),
}
SAR_SITES = V75.SAR_SITES                       # both at STOCK, checked as full halfwords too


# ---- addendum guards: cheap insurance, named rather than left to whole-image identity --------------
CEILING_REC_ADDR = 0xD209C          # the damper ceiling record -- lockstep-checked at 5/1024
CEILING_FLOAT_TWIN = {0xC6554: 300.0, 0xC6558: 800.0, 0xC655C: 0.5, 0xC6560: 1.0}
ROLE_TABLE_ADDR, ROLE_TABLE_LEN = 0xC4124, 0x20     # a slot with role 6 or 7 voids EVERY V84 lever
ROLE_FORBIDDEN = (6, 7)

# ---- 🛑 the frame-399 channel is ON HOLD by operator direction. Asserted ABSENT, not just unbuilt.
HOOK_399_STOCK = {0x55D50: bytes.fromhex("2436e0eb"),      # frame 399 (0x18F) packer hook site
                  0x55EFA: bytes.fromhex("243634ec")}      # frame 427 (0x1AB) packer hook site
CAVE_FREE_END = 0xC4FF0                                    # 🛑 0xC4FF0+ is the CRC block self-descriptor

# 🛑 V69/V70 wrote MODE 10's gain_B and this car never reads it. Asserted UNMOVED -- V84 does not
# 🛑 silently "fix" an inert edit, because that would change what a future diff attributes to V84.
GAIN_B_PTRS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
GAIN_B_MODE10_INERT = {0xD2A74: [5244] * 4, 0xD2AB0: [5244] * 4,
                       0xD2AEC: [2305, 2304, 2149, 1948], 0xD2B28: [2151, 2151, 2049, 1947]}

FACTOR_B_PTRS, FACTOR_C_PTRS = V75.FACTOR_B_PTRS, V75.FACTOR_C_PTRS
FACTOR_D_PTRS, FACTOR_E_PTRS = V75.FACTOR_D_PTRS, V75.FACTOR_E_PTRS
CEILING_PTRS, FRICTION_PTR_ARRAY = V75.CEILING_PTRS, V74.FRICTION_PTR_ARRAY
ALL_PTR_ARRAYS = {"FactorB": FACTOR_B_PTRS, "FactorC": FACTOR_C_PTRS, "FactorD": FACTOR_D_PTRS,
                  "FactorE": FACTOR_E_PTRS, "ceiling": CEILING_PTRS, "friction": FRICTION_PTR_ARRAY}
MANUAL_EXPECT = {"B": 0xD6760, "C": 0xD67E4, "D": 0xD67A4, "E": 0xD6820,
                 "ceiling": 0xD60B4, "friction": 0xD6A64}
CEILING_X, CEILING_Y = V74.CEILING_X, V74.CEILING_Y      # [300, 800], [512, 1024]
CEILING_FLOOR = V75.CEILING_FLOOR                        # 512
FRICTION_NPT, FRICTION_X = V74.FRICTION_NPT, V74.FRICTION_X
FRICTION_Y_STOCK = V74.FRICTION_Y_STOCK

# ---- the axes, stated once ------------------------------------------------------------------------
SPEED_COUNTS_PER_KMH = 64.0625          # voted vehicle speed, FactorB/FactorC axis
RATE_COUNTS_PER_DEG_S = 4.7121          # motor rate, FactorD/FactorE axis
REPORT_SPEEDS_KMH = (5, 35, 60, 100)
REPORT_RATES = (20, 40, 99, 119, 150, 255, 530, 1000, 1941, 4000)
DF_AMPLITUDES = (25, 50, 99, 150, 250, 500, 1000)
# ⊕ STATE.md's recorded N(R) row for V75's damper at creep. `describing_function` is VALIDATED
# ⊕ against it before it is trusted -- V83a's mode 27 IS V75's damper package, byte for byte.
V75_DF_ROW_RECORDED = (0.580, 1.065, 1.319, 1.410, 1.317, 0.734, 0.375)
V75_RELAY_INDEX_RECORDED = 1.45
HONDA_RELAY_INDEX = 0.0                 # Honda's surface is VISCOUS: N(50) is identically zero

# =====================================================================================================
# THE PROBE -- the EXISTING 68-byte cave, REPOINTED. 🛑 CAVE_EXTENT IS NOT GROWN.
# =====================================================================================================
R0, R6, R7 = 0, 6, 7
PAYLOAD_BYTE4_DISP = V75.PAYLOAD_BYTE4_DISP        # 0x1514 -- CAN-330 byte 4
PAYLOAD_KEEP_MASK = V75.PAYLOAD_KEEP_MASK          # 0x7 -- live STEER_SENSOR_STATUS bits 2:0
HOOK_RETURN_INSN = V75.HOOK_RETURN_INSN            # `mov 0x8,r7` -- proves r7 is DEAD across the hook

# ---- the cells the cave reads. NONE of them is written by the cave. --------------------------------
R24_DISP = 0x6ADA            # post-clamp r24 mirror. SIGNED. 1 writer (0x3AD5A `st.h`), 0 readers
R26_DISP = 0x6ADC            # post-clamp r26 mirror -- NOT read by V84's cave; censused anyway
FD_GATE_DISP = 0x67FE        # FactorD liveness gate, UNSIGNED byte
FD_AXIS_DISP = 0x6A10        # FactorD angle-error axis, UNSIGNED halfword (all 14 readers are ld.hu)
R24_MIRROR_WRITER, R26_MIRROR_WRITER = 0x3AD5A, 0x3AD4E
OP_LDH, OP_STH = 0x39, 0x3B  # 🛑 ONE BIT APART, and 0x6ada's firmware instance IS the store

# ---- V850 condition codes, pinned to real instructions in the image below --------------------------
COND_BE, COND_BLT, COND_BGE = 0x2, 0x6, 0xE
COND_BH, COND_BGT = 0xB, 0xF          # unsigned `>` and signed `>`  -- NEW to this kit's caves
BR_SKIP = 4                            # every rung's branch skips exactly one 2-byte `add`

# ---- the rungs ------------------------------------------------------------------------------------
R24_SHIFT = 8                          # `sar 0x8` -- ARITHMETIC, so negatives stay negative
# 🛑 THE TWO IMMEDIATES ARE NOT +-N. `sar` FLOORS TOWARD -inf, so `q <= -4` fires at r24 <= -769,
# 🛑 not -1024 -- a 255-count asymmetry that the exhaustive wire self-check caught and that a
# 🛑 hand-checked "+-4" would have shipped. `q <= -5` gives -1025, symmetric to +1024 within ONE count.
R24_Q_POS, R24_Q_NEG = 4, -5
# both are stated as MAGNITUDES, and both are re-derived from the shift rather than written down:
#   q >= P   <=>  r24 >= P*2^s                      (floor is exact on the positive side)
#   q <= N   <=>  r24 <  (N+1)*2^s  <=>  r24 <= (N+1)*2^s - 1     (N is NEGATIVE)
R24_COUNTS_POS = R24_Q_POS << R24_SHIFT                    # 1024
R24_COUNTS_NEG = -(((R24_Q_NEG + 1) << R24_SHIFT) - 1)     # 1025 -- the MAGNITUDE of the -ve trip
FD_AXIS_THRESH = 8                     # gp-0x6a10 >= 8  (0.1 deg/count ⇒ 0.8 deg of tracking error)
FD_GATE_LO, FD_GATE_HI = 1, 2          # gp-0x67fe in {1,2}
BIT_R24_POS, BIT_R24_NEG = 0x80, 0x40
BIT_FD_GATE, BIT_FD_AXIS, BIT_FINGERPRINT = 0x20, 0x10, 0x08
W_B7, W_B6, W_B5, W_B4, HI_SHIFT = 8, 4, 2, 1, 4    # pre-shift weights, then `shl 0x4`
LANE_CLAMP = EX.LANE_CLAMP             # 8192 -- r24's own clamp, the rung's reachable range

# ---- the four cells GATE 1 covers for the probe: (disp, firmware writers, firmware readers, why) ---
PROBE_CELLS = (
    (R24_DISP, 1, 0, "post-clamp r24 mirror -- READ by the cave"),
    (R26_DISP, 1, 0, "post-clamp r26 mirror -- not read by V84, censused so a change is VISIBLE"),
    (FD_AXIS_DISP, 3, 14, "FactorD angle-error axis -- READ by the cave"),
    (FD_GATE_DISP, 5, 55, "FactorD liveness gate -- READ by the cave"),
)


def sar_imm5(imm5, reg2):
    """Format II `sar imm5,reg2`, opcode 0x15. 🛑 ARITHMETIC -- `shr` (0x14) would turn every
    negative r24 into a huge positive and the thermometer would read ~100% duty forever."""
    assert 0 <= imm5 <= 31 and 0 <= reg2 < 32
    return struct.pack("<H", (reg2 << 11) | (0x15 << 5) | imm5)


def assert_probe_encoders(stock):
    """🛑 EVERY halfword the cave emits is PINNED to a real instruction in the STOCK image.

    The kit had no `sar` emitter and no `bh`/`bgt` emitter before V84, so both are pinned here rather
    than trusted. `sar` lands on the two `sar 0xa` sites that are already on this build's keep-list.
    """
    assert sar_imm5(0xA, R6) == bytes(stock[0x3AB76:0x3AB78]), \
        f"the `sar` emitter gives {sar_imm5(0xA, R6).hex()}, the image's `sar 0xa,r6` @0x3AB76 is " \
        f"{bytes(stock[0x3AB76:0x3AB78]).hex()}"
    assert sar_imm5(0xA, 8) == bytes(stock[0x3AC20:0x3AC22]), \
        "the `sar` emitter disagrees with the image's `sar 0xa,r8` @0x3AC20"
    assert (struct.unpack("<H", sar_imm5(R24_SHIFT, R6))[0] >> 5) & 0x3F == 0x15, \
        "🛑 the emitted shift is not opcode 0x15 (`sar`) -- 0x14 is `shr` and would INVERT the rung"
    for cond, name in ((COND_BE, "be"), (COND_BLT, "blt"), (COND_BGE, "bge"),
                       (COND_BH, "bh"), (COND_BGT, "bgt")):
        raw = FF.bcond(cond, BR_SKIP)
        assert (struct.unpack("<H", raw)[0] >> 7) & 0xF == 0xB, f"the `{name}` emitter is not Format III"
        assert struct.unpack("<H", raw)[0] & 0xF == cond, f"the `{name}` emitter lost its condition"
    # the two NEW conditions must differ from every condition the kit has flown, or the pin is vacuous
    assert len({COND_BE, COND_BLT, COND_BGE, COND_BH, COND_BGT}) == 5
    assert V55.cmp_imm5(R24_Q_NEG, R6) != V55.cmp_imm5(R24_Q_POS, R6), \
        "the signed cmp emitter is not sign-sensitive -- the negative rung would duplicate the positive"


def build_cave():
    """pack_v84_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        mov   0x0,r7            ; r7 = 0
        ld.h  -0x6ada[gp],r6    ; ★★★★ DELIVERED r24, post-clamp. SIGNED (op 0x39, NOT 0x3B = st.h)
        sar   0x8,r6            ; q = r24 >> 8, ARITHMETIC -- sign PRESERVED
        cmp   0x4,r6
        blt   +4
        add   0x8,r7            ; bit7 = (r24 >= +1024)
        cmp   -0x4,r6
        bgt   +4
        add   0x4,r7            ; bit6 = (r24 <= -1024)   ⇒ bit7|bit6 = |r24| >= 1024, FULL duty
        ld.bu -0x67fe[gp],r6    ; ★★ FactorD's LIVENESS GATE
        add   -0x1,r6           ; r6 = v - 1
        cmp   0x1,r6
        bh    +4                ; UNSIGNED > : v=0 wraps to 0xFFFFFFFF and is correctly EXCLUDED
        add   0x2,r7            ; bit5 = (gp-0x67fe in {1,2})
        ld.hu -0x6a10[gp],r6    ; ★★ FactorD's ANGLE-ERROR AXIS (UNSIGNED; hw2 LSB = 1)
        cmp   0x8,r6
        blt   +4
        add   0x1,r7            ; bit4 = (gp-0x6a10 >= 8)
        shl   0x4,r7            ; the 4-bit thermometer -> bits 7:4
        add   0x8,r7            ; bit3 = 1, THE BUILD FINGERPRINT, weight 8 POST-shift
        ld.bu -0x1514[gp],r6    ; CAN-330 payload byte4
        andi  0x7,r6,r6         ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6             ; THE MERGE. 🛑 not `or r6,r7`
        st.b  r6,-0x1514[gp]    ; THE ONLY STORE
        movea -0x1518,gp,r6     ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
        66 bytes; the final 2 of the 68-byte extent are 0xFF PADDING.
    """
    body, listing = bytearray(), []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movi5(0, R7), "mov 0x0,r7           ; r7 = 0")
    emit(V55.ldh(R24_DISP, R6),
         f"ld.h -0x{R24_DISP:04x}[gp],r6  ; ★★★★ DELIVERED r24 (SIGNED, op MUST be 0x39)")
    emit(sar_imm5(R24_SHIFT, R6),
         f"sar 0x{R24_SHIFT:x},r6            ; q = r24 >> {R24_SHIFT}, ARITHMETIC (op 0x15)")
    pos_idx = len(listing)
    emit(V55.cmp_imm5(R24_Q_POS, R6), f"cmp 0x{R24_Q_POS:x},r6            ; q >= "
                                      f"{R24_Q_POS} <=> r24 >= +{R24_COUNTS_POS}")
    emit(FF.bcond(COND_BLT, BR_SKIP), "blt +4")
    emit(V75.addi5(W_B7, R7), f"add 0x{W_B7:x},r7            ; bit7 = r24 >= +{R24_COUNTS_POS}")
    neg_idx = len(listing)
    emit(V55.cmp_imm5(R24_Q_NEG, R6), f"cmp {R24_Q_NEG},r6             ; q <= "
                                      f"{R24_Q_NEG} <=> r24 <= -{R24_COUNTS_NEG}")
    emit(FF.bcond(COND_BGT, BR_SKIP), "bgt +4               ; SIGNED > -- skip when q > -T")
    emit(V75.addi5(W_B6, R7), f"add 0x{W_B6:x},r7            ; bit6 = r24 <= -{R24_COUNTS_NEG}")
    emit(V55.ldbu_any(-FD_GATE_DISP, R6),
         f"ld.bu -0x{FD_GATE_DISP:04x}[gp],r6 ; ★★ FactorD's LIVENESS GATE")
    gate_idx = len(listing)
    emit(V75.addi5(-FD_GATE_LO, R6), f"add -0x{FD_GATE_LO:x},r6           ; r6 = v - {FD_GATE_LO}")
    emit(V55.cmp_imm5(FD_GATE_HI - FD_GATE_LO, R6),
         f"cmp 0x{FD_GATE_HI - FD_GATE_LO:x},r6            ; range width")
    emit(FF.bcond(COND_BH, BR_SKIP), "bh +4                ; UNSIGNED > : v=0 wraps and is EXCLUDED")
    emit(V75.addi5(W_B5, R7),
         f"add 0x{W_B5:x},r7            ; bit5 = gp-0x{FD_GATE_DISP:04x} in "
         f"{{{FD_GATE_LO},{FD_GATE_HI}}}")
    emit(V75.ldhu_gp(FD_AXIS_DISP, R6),
         f"ld.hu -0x{FD_AXIS_DISP:04x}[gp],r6 ; ★★ FactorD's ANGLE-ERROR AXIS (UNSIGNED)")
    axis_idx = len(listing)
    emit(V55.cmp_imm5(FD_AXIS_THRESH, R6), f"cmp 0x{FD_AXIS_THRESH:x},r6            ; >= "
                                           f"{FD_AXIS_THRESH} counts = {FD_AXIS_THRESH / 10:.1f} deg")
    emit(FF.bcond(COND_BLT, BR_SKIP), "blt +4")
    emit(V75.addi5(W_B4, R7), f"add 0x{W_B4:x},r7            ; bit4")
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
    for idx, what in ((pos_idx, "r24 positive"), (neg_idx, "r24 negative"),
                      (axis_idx, "FactorD axis")):
        assert ((struct.unpack("<H", listing[idx][1])[0] >> 5) & 0x3F) == 0x13, \
            f"the {what} rung does not start with a `cmp imm5`"
        assert listing[idx][0] + 2 == listing[idx + 1][0] and \
            listing[idx + 1][0] + 2 == listing[idx + 2][0], \
            f"the {what} cmp/branch/add triple is not contiguous -- the branch would read STALE flags"
    assert struct.unpack("<H", listing[gate_idx + 1][1])[0] >> 5 & 0x3F == 0x13 and \
        listing[gate_idx][0] + 2 == listing[gate_idx + 1][0], \
        "the liveness-gate `add -1` / `cmp` pair is not adjacent"
    # the conditions themselves -- an inverted rung is the recorded `ba05`/`b205` trap
    for idx, cond, why in ((pos_idx + 1, COND_BLT, "r24+ must be `blt` -- `bge` INVERTS the rung"),
                           (neg_idx + 1, COND_BGT, "r24- must be `bgt` (SIGNED)"),
                           (gate_idx + 2, COND_BH, "the gate must be `bh` (UNSIGNED) or v=0 leaks in"),
                           (axis_idx + 1, COND_BLT, "the axis rung must be `blt`")):
        hw = struct.unpack("<H", listing[idx][1])[0]
        assert (hw >> 7) & 0xF == 0xB and (hw & 0xF) == cond, f"🛑 {why}"

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
    # ---- 🛑 the ONE-BIT trap: our r24 access must be a LOAD (0x39), not a STORE (0x3B) ------------
    ldh_raw = V55.ldh(R24_DISP, R6)
    ldh_op = (struct.unpack_from("<H", ldh_raw, 0)[0] >> 5) & 0x3F
    assert ldh_op == OP_LDH, \
        f"🛑 the r24 access is opcode 0x{ldh_op:02X}, not " \
        f"0x{OP_LDH:02X} (`ld.h`). 0x{OP_STH:02X} is `st.h` -- ONE BIT away -- and it would CLOBBER " \
        "the aggregator's own mirror instead of reading it."
    assert len(body) == 66, f"the cave body is {len(body)} bytes, expected 66"
    body.extend(b"\xff" * (CAVE_EXTENT - len(body)))      # 🛑 pad to the PROVEN extent; never grow it
    assert len(body) == CAVE_EXTENT == 68
    return bytes(body), listing


def redisassemble_v84_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, from raw bytes, self-contained.

    🛑 Deliberately NOT `V75.redisassemble_cave` -- that decoder's Bcond map has no `bh`/`bgt` and
    would render two of V84's four branches as `b?b` / `b?f`. It is the readback's independent
    witness, so it must not inherit the builder's assumptions. `assert_decoder_calibrated` checks
    this decoder against V75's on V75's OWN cave first, so it cannot be silently wrong.
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
    """🛑 CALIBRATE THE WITNESS BEFORE USING IT -- on V75's cave, which V75's own decoder defines."""
    v75_cave, _l = V75.build_cave()
    mine = [(a, r, m) for a, r, m in redisassemble_v84_cave(v75_cave)]
    theirs = V75.redisassemble_cave(v75_cave)
    assert [(a, r) for a, r, _m in mine] == [(a, r) for a, r, _m in theirs], \
        "🛑 V84's decoder splits V75's cave into different instructions than V75's own decoder"
    for (a, _r, m), (_a, _r2, t) in zip(mine, theirs):
        assert m == t, f"🛑 at 0x{a:05X} V84's decoder says {m!r}, V75's says {t!r}"
    return len(mine)


def wire_byte4(r24, fd_gate, fd_axis, status_bits=0x7):
    """A Python mirror of the cave, instruction for instruction, on the SAME integer arithmetic."""
    q = r24 >> R24_SHIFT                       # Python >> on a negative int IS an arithmetic shift
    b = 0
    if q >= R24_Q_POS:
        b |= W_B7
    if q <= R24_Q_NEG:
        b |= W_B6
    if ((fd_gate & 0xFF) - FD_GATE_LO) & 0xFFFFFFFF <= (FD_GATE_HI - FD_GATE_LO):   # UNSIGNED
        b |= W_B5
    if (fd_axis & 0xFFFF) >= FD_AXIS_THRESH:
        b |= W_B4
    return ((b << HI_SHIFT) | BIT_FINGERPRINT) | (status_bits & PAYLOAD_KEEP_MASK)


def decode_byte4(byte4):
    """Decode `0x14A` byte4. 🛑 A frame whose FINGERPRINT is clear is NOT V84 -- refuse it."""
    if not byte4 & BIT_FINGERPRINT:
        return None
    return {"r24_pos": bool(byte4 & BIT_R24_POS), "r24_neg": bool(byte4 & BIT_R24_NEG),
            "r24_mag": bool(byte4 & (BIT_R24_POS | BIT_R24_NEG)),
            "fd_gate": bool(byte4 & BIT_FD_GATE), "fd_axis": bool(byte4 & BIT_FD_AXIS),
            "fingerprint": True}


def _self_check_wire():
    """Every rung EXHAUSTIVELY over its reachable range, and jointly over a product grid."""
    assert_decoder_calibrated()
    # ---- r24 over its ENTIRE reachable range, +-LANE_CLAMP, both rungs ---------------------------
    for r24 in range(-LANE_CLAMP, LANE_CLAMP + 1):
        d = decode_byte4(wire_byte4(r24, 1, 0))
        assert d is not None and d["fingerprint"]
        assert d["r24_pos"] == (r24 >= R24_COUNTS_POS), f"bit7 wrong at r24={r24}"
        assert d["r24_neg"] == (r24 <= -R24_COUNTS_NEG), f"bit6 wrong at r24={r24}"
        assert not (d["r24_pos"] and d["r24_neg"]), f"both r24 rungs fired at r24={r24}"
    # 🛑 the thresholds are SYMMETRIC at the breakpoint -- `sar` floors toward -inf, so this is a
    # 🛑 real question and not a formality.
    assert wire_byte4(R24_COUNTS_POS, 1, 0) & BIT_R24_POS
    assert not wire_byte4(R24_COUNTS_POS - 1, 1, 0) & BIT_R24_POS
    assert wire_byte4(-R24_COUNTS_NEG, 1, 0) & BIT_R24_NEG
    assert not wire_byte4(-R24_COUNTS_NEG + 1, 1, 0) & BIT_R24_NEG
    assert abs(R24_COUNTS_POS - R24_COUNTS_NEG) <= 1, \
        f"the r24 rungs are asymmetric: +{R24_COUNTS_POS} vs -{R24_COUNTS_NEG}"
    # ---- the liveness gate over ALL 256 byte values ----------------------------------------------
    for v in range(256):
        d = decode_byte4(wire_byte4(0, v, 0))
        assert d["fd_gate"] == (v in (FD_GATE_LO, FD_GATE_HI)), f"bit5 wrong at gp-0x67fe={v}"
    assert not decode_byte4(wire_byte4(0, 0, 0))["fd_gate"], \
        "🛑 v=0 must be EXCLUDED -- an unsigned compare is what makes the wrap safe"
    # ---- the axis over its full unsigned halfword range ------------------------------------------
    for v in (0, 1, 6, 7, 8, 9, 20, 23, 24, 50, 100, 700, 0x7FFF, 0xFFFF):
        d = decode_byte4(wire_byte4(0, 1, v))
        assert d["fd_axis"] == (v >= FD_AXIS_THRESH), f"bit4 wrong at gp-0x6a10={v}"
    # ---- EVERY rung must be able to BOTH fire and not fire (V69's bit4 was structurally vacuous) --
    for name, on, off in (("r24_pos", wire_byte4(2000, 1, 0), wire_byte4(0, 1, 0)),
                          ("r24_neg", wire_byte4(-2000, 1, 0), wire_byte4(0, 1, 0)),
                          ("fd_gate", wire_byte4(0, 2, 0), wire_byte4(0, 0, 0)),
                          ("fd_axis", wire_byte4(0, 1, 24), wire_byte4(0, 1, 6))):
        assert decode_byte4(on)[name] and not decode_byte4(off)[name], \
            f"🛑 rung {name} cannot both fire and not fire -- it is VACUOUS"
    # ---- no rung is implied by another: all 16 combinations are reachable -------------------------
    seen = set()
    for r24 in (-2000, 0, 2000):
        for g in (0, 1):
            for ax in (0, 24):
                d = decode_byte4(wire_byte4(r24, g, ax))
                seen.add((d["r24_pos"], d["r24_neg"], d["fd_gate"], d["fd_axis"]))
    assert len(seen) == 12, f"{len(seen)} rung combinations reachable, expected 12 (r24 is 3-valued)"
    # ---- the fingerprint is ALWAYS set, and the live status bits ALWAYS survive -------------------
    for r24 in (-8192, -1024, 0, 1024, 8192):
        for st in range(8):
            b = wire_byte4(r24, 1, 0, status_bits=st)
            assert b & BIT_FINGERPRINT, "🛑 the fingerprint is not set on a reachable payload"
            assert b & PAYLOAD_KEEP_MASK == st, "🛑 the live STEER_SENSOR_STATUS bits were destroyed"
            assert decode_byte4(b) is not None
    # ---- 🛑 a V83a frame must NOT decode as V84 --------------------------------------------------
    # V83a's bit3 is `gp-0x6ac2 != 0`, a VARIABLE. Any V83a frame with that cell zero has bit3 clear
    # and this decoder refuses it. That is the fingerprint's whole job.
    assert decode_byte4(0x87) is None, "🛑 a bit3-clear frame must be REFUSED, not decoded"
    assert decode_byte4(0x80) is None and decode_byte4(0x00) is None
    # ---- no latched/sticky bits: the payload is a pure function of the three inputs ---------------
    assert wire_byte4(0, 0, 0, 0) == BIT_FINGERPRINT, \
        "🛑 the all-clear payload is not just the fingerprint -- something is latched"


_self_check_wire()

# 🛑 THE BUILDER->DECODER LINK, MADE MECHANICAL. `studies/probes/decode_v84_probe.py` IMPORTS these names rather
# than copying them, so the V66 failure mode -- a decoder header that said bit4 = gp-0x683c for one
# revision while the image read gp-0x67fe -- is structurally impossible here, not merely unlikely.
CAVE_HEX = build_cave()[0].hex()


def assert_decoder_module():
    """Import the shipped decoder and run its own self-test against THIS build's constants."""
    if not os.path.exists(os.path.join(HERE, "studies/probes/decode_v84_probe.py")):
        print("    ⚠ studies/probes/decode_v84_probe.py not found -- the decoder/image link is NOT verified")
        return False
    import importlib
    dec = importlib.import_module("decode_v84_probe")
    importlib.reload(dec)
    assert dec.CAVE_HEX == CAVE_HEX, \
        "🛑 the shipped decoder's cave hex does not match this build's -- it is STALE"
    for name, want in (("BIT_R24_POS", BIT_R24_POS), ("BIT_R24_NEG", BIT_R24_NEG),
                       ("BIT_FD_GATE", BIT_FD_GATE), ("BIT_FD_AXIS", BIT_FD_AXIS),
                       ("BIT_FINGERPRINT", BIT_FINGERPRINT),
                       ("R24_COUNTS_POS", R24_COUNTS_POS), ("R24_COUNTS_NEG", R24_COUNTS_NEG),
                       ("FD_AXIS_THRESH", FD_AXIS_THRESH)):
        assert getattr(dec, name) == want, \
            f"🛑 the decoder's {name} is {getattr(dec, name)}, not {want}"
    dec._selftest()
    return True

# ---- the census, re-derived on this image and NOT inherited ----------------------------------------
CENSUS_SRC = {DEAD_DISP: (1, 0), GATE_DISP: (13, 16)}       # on the V83a INPUT
CENSUS_OUT = {DEAD_DISP: (0, 0), GATE_DISP: (14, 16)}       # on the V84 OUTPUT -- ONE reader moves
_READ_MNEM = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}

# =====================================================================================================
# OUTPUT NAMING -- 🛑 exactly ONE flashable .rwd and ONE plain image per build number on disk
# =====================================================================================================
# 🛑 THE SEPARATOR IS `.`/`-`, NEVER `+`: the Ghidra MCP layer once URL-decoded a `+` to a SPACE.
# 🛑 THE PROBE IS IN THE NAME, IN **BOTH** FILENAMES. V83a shipped as `magprobe-6bd0-thermo-6ac2`;
# 🛑 V84's cave measures ENTIRELY DIFFERENT CELLS, and a name that still said `6bd0` would be a lie
# 🛑 on the shelf. The lever set going in the filename is the rule that made the V83a re-cut safe.
VARIANT_TOKEN = "LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10"
TAG = f"V83ABASE-{VARIANT_TOKEN}"
# 🛑🛑 THIS BUILD WAS RE-CUT. The control-path-only cut (image `bdd857c9…`, .rwd `54985b45…`) was
# WRITTEN AND REPORTED before the probe repoint was authorised. Its artefacts are NOT overwritten --
# the kit's rule is exactly ONE flashable .rwd per build number, and a same-name re-cut destroys its
# predecessor's snapshot and leaves a flashable artefact no gate can check. The probe cut therefore
# carries its lever set in BOTH filenames and the first pair was renamed `SUPERSEDED-DO-NOT-FLASH-`.
# Both remain on disk and both remain verifiable.
SUPERSEDED_CONTROL_ONLY = {
    "image": "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27_plain_image.bin",
    "image_sha": "bdd857c942cab37a26b7d78e4c76cefeec054b33fc46d887d448291e15ab2825",
    "rwd_sha": "54985b457125784b72c045da68069f2089a24a23da354a63c553a10f3206ac9e",
    "why": "the SEVEN control-path cells WITHOUT the cave repoint -- it still carried V75's damper "
           "magprobe, which V84's own edits drive to a structurally predictable zero.",
}
BIN_OUT = str(plain_image_path(f"_v84_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V84-{TAG}-0x{START:X}-0x{END:X}.rwd")

WRITE_MODE = os.environ.get("ACCORD_V84_WRITE", "").strip().lower()
assert WRITE_MODE in ("", "none", "bin", "rwd"), \
    f"ACCORD_V84_WRITE={WRITE_MODE!r} -- expected '' (dry run), 'bin' or 'rwd'"


# =====================================================================================================
# THE MODE COLUMNS AND THE RECORD GEOMETRY -- DERIVED, never quoted
# =====================================================================================================

def derive_this_cars_modes(buf):
    """Row 11's four mode indices, read out of the variant table itself.

    🛑 The whole reason mode 27 is in this build. `TVCA4` is one of only four rows whose four columns
    are DISTINCT, so column 3 is a genuinely separate engaged mode and not an alias of column 2.
    """
    row = VARIANT_TABLE + THIS_CAR_ROW * VARIANT_STRIDE
    key = bytes(buf[row:row + 5]).decode("ascii", "replace")
    modes = tuple(buf[row + VARIANT_MODE_OFF:row + VARIANT_MODE_OFF + 4])
    assert key == THIS_CAR_KEY, f"variant row {THIS_CAR_ROW} is {key!r}, expected {THIS_CAR_KEY!r}"
    assert modes == THIS_CAR_MODES, \
        f"row {THIS_CAR_ROW} resolves to modes {modes}, expected {THIS_CAR_MODES}"
    assert len(set(modes)) == 4, "🛑 this car's four mode columns are NOT distinct -- mode 27 would " \
                                 "be an alias and the m27 edits would be pointless"
    distinct = [r for r in range(16)
                if len(set(buf[VARIANT_TABLE + r * VARIANT_STRIDE + VARIANT_MODE_OFF:
                               VARIANT_TABLE + r * VARIANT_STRIDE + VARIANT_MODE_OFF + 4])) == 4]
    return key, modes, distinct


def assert_edit_geometry(buf, label):
    """🛑 Every edit address is DERIVED from its record, never trusted as a literal.

    The `X at base+2, not base+4` trap is on this kit's record. `npt` is read from the record's OWN
    count word every time -- FactorD is a FIVE-point record and a fixed 4-point reader silently
    returns `[X[4], Y[0], Y[1], Y[2]]` for it.
    """
    want = {}
    for name, ptrs, mode, rec_expect in (("FactorC", FACTOR_C_PTRS, LIVE_MODE, FACTOR_C_M26_REC),
                                         ("FactorC", FACTOR_C_PTRS, LIVE_MODE_2, FACTOR_C_M27_REC),
                                         ("FactorE", FACTOR_E_PTRS, LIVE_MODE, FACTOR_E_M26_REC),
                                         ("FactorE", FACTOR_E_PTRS, LIVE_MODE_2, FACTOR_E_M27_REC)):
        rec = factor_rec(buf, ptrs, mode)
        assert rec == rec_expect, \
            f"🛑 {label}: {name} m{mode} DEREFERENCES to 0x{rec:05X}, expected 0x{rec_expect:05X} " \
            "-- the brief warned not to assume mode 27 is adjacent to mode 26. It is not."
        n = u16(buf, rec)
        assert n == 4 and rec_len(buf, rec) == 0x14, f"{label}: {name} m{mode} count is {n}"
        # 🛑 npt-DERIVED offsets: X at base+2, Y at base + 2 + 2*npt
        assert rec + 2 == rec + REC4_X_OFF and rec + 2 + 2 * n == rec + REC4_Y_OFF, \
            f"{label}: the npt-derived offsets disagree with REC4_X_OFF/REC4_Y_OFF"
    want[0xD77DA] = FACTOR_C_M26_REC + REC4_Y_OFF + 0        # FactorC m26 Y[0]
    want[0xD77EE] = FACTOR_C_M27_REC + REC4_Y_OFF + 0        # FactorC m27 Y[0]
    want[0xD7822] = FACTOR_E_M27_REC + REC4_X_OFF + 0        # FactorE m27 X[0]
    want[0xD7824] = FACTOR_E_M27_REC + REC4_X_OFF + 2        # FactorE m27 X[1]
    want[0xD782C] = FACTOR_E_M27_REC + REC4_Y_OFF + 2        # FactorE m27 Y[1]
    for addr, derived in want.items():
        assert addr == derived, \
            f"🛑 {label}: the edit at 0x{addr:05X} is NOT where the record puts it (0x{derived:05X})"
    # ---- FactorD is n=5 and V84 does NOT touch it. Asserted flat-unity on every mode it could reach.
    for mode in THIS_CAR_MODES:
        n, xs, ys = rec_any(buf, factor_rec(buf, FACTOR_D_PTRS, mode))
        assert (n, xs, ys) == (5, [0, 50, 100, 150, 700], [Q10] * 5), \
            f"{label}: FactorD m{mode} is ({n}, {xs}, {ys}), expected Honda's flat-unity 5-point"
        assert rec_len(buf, factor_rec(buf, FACTOR_D_PTRS, mode)) == 0x18, \
            f"{label}: FactorD m{mode} rec_len is not 0x18 -- the +0x0C Y offset would be wrong"
    # ---- edit 1 is an INSTRUCTION byte, not a record member ----------------------------------------
    assert REPOINT_BYTE == REPOINT_ADDR + 2, "the repoint byte is not hw2's low half"
    assert ARM_ADDR - TP == 0x7446, \
        f"🛑 {label}: 0x{ARM_ADDR:05X} is not tp+0x7446 -- the off-by-0x1000 trap (tp = 0xBF000)"
    assert R26_ARM_ADDR - TP == 0x7444


# =====================================================================================================
# EDIT 1 -- THE REPOINT, ITS PROVENANCE AND ITS CENSUS
# =====================================================================================================

def assert_repoint_and_chain(buf, label, done):
    """The one byte, decoded by an INDEPENDENT decoder, plus the whole `lp` chain it feeds."""
    V67.assert_repoint(buf, label, done=done)
    got = bytes(buf[REPOINT_ADDR:REPOINT_ADDR + 4])
    mnem, disp, reg1, reg2 = V67.decode_ldbu(got)
    assert (mnem, reg1, reg2) == ("ld.bu", GP, 15)
    assert disp == (GATE_DISP if done else DEAD_DISP), \
        f"{label}: 0x{REPOINT_ADDR:05X} addresses gp-0x{disp:04x}"
    assert got[:2] == REPOINT_FROM[:2], \
        f"🛑 {label}: hw1 MOVED -- the 'one byte' claim is false and the opcode parity field changed"
    # the FIRST jarl is AFTER both consumers, so `lp` is scratch and cannot be clobbered
    assert V67.FIRST_JARL_AFTER > 0x3AC08, "the first jarl is no longer after both lp consumers"
    for addr, raw, what in V67.LP_CHAIN:
        assert bytes(buf[addr:addr + len(raw)]) == raw, f"{label}: the lp chain at 0x{addr:05X} " \
                                                        f"({what}) moved"
    return mnem, disp, reg1, reg2


def gp_census(buf, disp, cave_span):
    """Reader/writer census for a gp cell, by TWO independent decoders + the extended form.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    still reports `truncated:false` while undercounting. It has produced wrong sets four times.
    """
    hits = V64.gp_access_census(buf, disp)
    assert all(m in {"ld.bu", "st.b"} for _a, m, _r in hits), \
        f"gp-0x{disp:04x} has an access outside ld.bu/st.b -- wrong WIDTH or SIGN"
    fw = [h for h in hits if h[0] not in cave_span]
    reads = sorted(a for a, m, _r in fw if m in _READ_MNEM)
    writes = sorted(a for a, m, _r in fw if m not in _READ_MNEM)
    # ---- SECOND METHOD: per-opcode decode over EVERY byte offset (both parities) ----------------
    alt = SCAN.scan(buf, (-disp) & 0xFFFF)
    alt_even = [h for h in alt if h["even"]]
    assert sorted(h["addr"] for h in alt_even) == sorted(a for a, _m, _r in hits), \
        f"🛑 the two decoders disagree on WHICH addresses touch gp-0x{disp:04x}"
    assert not [h for h in alt if not h["even"]], \
        f"🛑 gp-0x{disp:04x} has an ODD-OFFSET hit -- confirm the instruction boundary"
    # ---- THIRD: the 6-byte extended-displacement / disp23 form ----------------------------------
    ext = SCAN.scan_ext(buf, -disp)
    genuine = []
    for h in ext:
        d7 = SCAN.decode_fmt7(buf, h["addr"])
        if d7 is None or d7[4] != GP:
            genuine.append(h)
    assert not genuine, \
        f"🛑 gp-0x{disp:04x} has {len(genuine)} extended-form candidate(s) that are NOT 32-bit " \
        f"aliases: {[hex(h['addr']) for h in genuine[:8]]}"
    return reads, writes, len(ext)


def assert_gate_census(buf, label, done, cave_span):
    """🛑 GATE 1's core, re-run FRESH on every image -- NOT inherited from V67."""
    expect = CENSUS_OUT if done else CENSUS_SRC
    out = {}
    for disp in (DEAD_DISP, GATE_DISP):
        reads, writes, n_ext = gp_census(buf, disp, cave_span)
        n_r, n_w = expect[disp]
        assert (len(reads), len(writes)) == (n_r, n_w), \
            f"🛑 {label}: gp-0x{disp:04x} has {len(reads)}r/{len(writes)}w, expected {n_r}r/{n_w}w: " \
            f"reads {[hex(a) for a in reads]}"
        out[disp] = (reads, writes, n_ext)
    dead_r, dead_w, _ = out[DEAD_DISP]
    gate_r, gate_w, _ = out[GATE_DISP]
    if done:
        assert not dead_r and not dead_w, \
            f"🛑 {label}: gp-0x{DEAD_DISP:04x} is not UNREFERENCED after the repoint"
        assert REPOINT_ADDR in gate_r, \
            f"🛑 {label}: 0x{REPOINT_ADDR:05X} is not a reader of gp-0x{GATE_DISP:04x}"
    else:
        assert dead_r == [REPOINT_ADDR], \
            f"{label}: gp-0x{DEAD_DISP:04x}'s sole reader is not the repoint site"
        assert REPOINT_ADDR not in gate_r
    # 🛑 the cave touches NEITHER cell -- V84's cave is V75's magprobe, which reads gp-0x6bd0/6ac2.
    for disp in (DEAD_DISP, GATE_DISP):
        cave = [a for a, _m, _r in V64.gp_access_census(buf, disp) if a in cave_span]
        assert not cave, f"{label}: the cave touches gp-0x{disp:04x} at {[hex(a) for a in cave]}"
    return out


def assert_repoint_twins(buf, label):
    """The exact halfword pair V84 writes ALREADY EXECUTES at two addresses in this ROM."""
    for a in V67.REPOINT_TWINS:
        assert bytes(buf[a:a + 4]) == REPOINT_TO, \
            f"{label}: the byte-identical twin @0x{a:05X} is not {REPOINT_TO.hex()}"
    a, raw, _reg = V67.REPOINT_REG2_TWIN
    assert bytes(buf[a:a + 4]) == raw, f"{label}: the reg2-only twin @0x{a:05X} moved"
    return list(V67.REPOINT_TWINS) + [a]


# =====================================================================================================
# EDIT 2 -- THE ARM, DERIVED FROM **THIS CAR'S** gain_B RECORDS
# =====================================================================================================

def gain_b_lerp(buf, mode, speed_counts, rate_counts):
    """r24's default gain: `FUN_0003ad74`'s cross-interpolated, **MODE-INDEXED** gain_B curve.

    🛑 DEREFERENCED at `mode` through the four pointer arrays. `v66_v67_explained.r24_gain_q10`
    hardcodes MODE 10's records and this car is `TVCA4` -> modes 24/25/26/27, so V67's 2622 was only
    the right number if mode 26 happened to agree. It does -- but that is asserted here, not assumed.
    """
    recs = []
    for base in GAIN_B_PTRS:
        rec = u32(buf, base + mode * 4)
        n = u16(buf, rec)
        assert n == 4, f"gain_B m{mode} @0x{rec:05X} declares count {n}"
        recs.append((list(struct.unpack_from("<4h", buf, rec + REC4_X_OFF)),
                     list(struct.unpack_from("<4h", buf, rec + REC4_Y_OFF))))
    key = 0 if rate_counts >= EX.RATE_FOLD else rate_counts     # 0x3AAC8 addi / 0x3AACC cmovc
    xs = [EX._lerp_flat(speed_counts, EX.CROSS_X, [r[0][i] for r in recs]) for i in range(4)]
    ys = [EX._lerp_flat(speed_counts, EX.CROSS_X, [r[1][i] for r in recs]) for i in range(4)]
    return EX._lerp_flat(key, xs, ys)


def assert_arm_derivation(buf, label):
    """🛑 5244 is DERIVED at grind #1's operating point, twice, by two routes that must agree."""
    sc = int(GRIND1_KMH * SPEED_COUNTS_PER_KMH)
    rc = int(GRIND1_DEGS * EX.RATE_COUNTS_PER_DEGS)
    live = gain_b_lerp(buf, LIVE_MODE, sc, rc)
    model = EX.r24_gain_q10(sc, rc, 0, 0, 0)
    assert live == model == GRIND1_LERP == 2622, \
        f"🛑 {label}: the LERP at grind #1's point is {live} from THIS CAR's mode-{LIVE_MODE} " \
        f"records and {model} from the mode-10 model; both must be {GRIND1_LERP}"
    assert ARM_NEW == 2 * GRIND1_LERP == 5244, "the arm is not 2.00x the LERP"
    assert 0 < ARM_NEW <= 0xFFFF and ARM_NEW == s16(struct.pack("<H", ARM_NEW), 0), \
        "the arm does not fit a POSITIVE signed halfword"
    # ---- saturation, through the REAL lane arithmetic including the deadzone --------------------
    sat = next(d for d in range(1, EX.INPUT_CLAMP + 1)
               if abs(EX.r24_lane(d, ARM_NEW, 10)) >= EX.LANE_CLAMP)
    naive = -(-EX.LANE_CLAMP * 1024 // ARM_NEW)
    assert (sat, naive) == (1601, 1600), \
        f"{label}: lane saturation re-derives at {sat} (naive {naive}), expected 1601/1600"
    assert EX.INPUT_CLAMP * ARM_NEW < 0x7FFFFFFF // 50, "the mul is not comfortably inside INT32"
    assert u16(buf, 0xC61F6) == EX.DEADZONE == 3, "the deadzone cal moved -- 1601 depends on it"
    return sc, rc, live, sat


def arm_multiplier_grid(buf):
    """`5244 / gain_B_LERP` over the engaged regime -- a SCALAR arm cannot track a CURVE."""
    out = {}
    for kmh in (2, 5, GRIND1_KMH, 10, 20, 40, 60, 100):
        for degs in (20, GRIND1_DEGS, 400):
            sc = int(kmh * SPEED_COUNTS_PER_KMH)
            rc = int(degs * EX.RATE_COUNTS_PER_DEGS)
            out[(kmh, degs)] = (gain_b_lerp(buf, LIVE_MODE, sc, rc), ARM_NEW)
    return out


def assert_gain_b_inert_mode10(buf, label):
    """🛑 V69/V70's mode-10 `[5244]x4` is INERT on this car. Asserted UNMOVED, not 'fixed'."""
    for base in GAIN_B_PTRS:
        rec = u32(buf, base + 10 * 4)
        got = list(struct.unpack_from("<4h", buf, rec + REC4_Y_OFF))
        want = GAIN_B_MODE10_INERT[rec]
        assert got == want, \
            f"🛑 {label}: mode-10 gain_B @0x{rec:05X} Y is {got}, expected the INERT {want} -- V84 " \
            "does not touch mode 10; a change here would be UNATTRIBUTED"


# =====================================================================================================
# EDITS 3-7 -- THE DAMPER SURFACE, AND RULE 12 AS **SHAPE**
# =====================================================================================================

def describing_function(buf, mode, R, speed_counts, nharm=4096):
    """`N(R)` for `force = -sign(rate) * M(|rate|)` driven by `rate(t) = R*sin(wt)`.

    The fundamental-harmonic gain. **Constant `N` over `R` = viscous = stabilising; `N` rising as the
    amplitude falls = relay = limit-cycle generator.** `M` is read from the BUILT image's own records
    through `damper_authority`, so this measures the SHAPE that will actually be flown.

    🛑 THIS IS THE TEST V80's BUILD DID NOT HAVE. Every no-clip guard tests `product > ceiling`;
    V80's supremum EQUALLED the ceiling, so it clipped 0.00%, passed, and still delivered a constant
    495 counts across a 34x rate range. **"Does not clip" and "is not a relay" are different
    statements.** Validated against STATE.md's recorded V75 row before it is trusted -- see
    `assert_describing_function_calibrated`.
    """
    acc = 0.0
    for k in range(nharm):
        th = 2.0 * math.pi * (k + 0.5) / nharm
        rate = R * math.sin(th)
        m = damper_authority(buf, mode, speed_counts, int(abs(rate)))
        acc += (-m if rate > 0 else m) * math.sin(th)
    return abs(2.0 / nharm * acc) / R


def relay_index(buf, mode, speed_counts):
    """`N(50)/N(500)`. Returns None when the damper is identically DEAD (0/0 is not 'flat')."""
    n50, n500 = describing_function(buf, mode, 50, speed_counts), \
        describing_function(buf, mode, 500, speed_counts)
    if n500 == 0.0:
        return None
    return n50 / n500


def dose_row(buf, mode, speed_counts):
    return [damper_authority(buf, mode, speed_counts, r) for r in REPORT_RATES]


def flatness(buf, mode, speed_counts):
    """`max/min` over the NON-ZERO delivered doses. A flat plateau is the relay's fingerprint."""
    nz = [v for v in dose_row(buf, mode, speed_counts) if v > 0]
    return (max(nz) / min(nz)) if nz else None


def assert_describing_function_calibrated(base_img):
    """🛑 CALIBRATE THE INSTRUMENT BEFORE USING IT.

    V83a's mode 27 IS V75's damper package byte-for-byte, and STATE.md records V75's `N(R)` row and
    its 1.45 relay index. If this implementation cannot reproduce them, no number it produces about
    V84 is worth anything.
    """
    got = [describing_function(base_img, LIVE_MODE_2, R, 0) for R in DF_AMPLITUDES]
    for g, w in zip(got, V75_DF_ROW_RECORDED):
        assert abs(g - w) < 2e-3, \
            f"🛑 the describing function re-derives V75's row as {[round(x, 3) for x in got]}, " \
            f"STATE.md records {list(V75_DF_ROW_RECORDED)} -- the INSTRUMENT is wrong, not the build"
    ri = relay_index(base_img, LIVE_MODE_2, 0)
    assert ri is not None and abs(ri - V75_RELAY_INDEX_RECORDED) < 5e-3, \
        f"🛑 V83a's mode-27 relay index re-derives as {ri}, STATE.md records " \
        f"{V75_RELAY_INDEX_RECORDED}"
    return got, ri


def assert_engaged_equals_manual(buf, stock, label):
    """🛑 RULE 12 / GATE 5 / S4, as BYTES and as DELIVERED DOSE.

    ⚠ THE PAIRING IS 24<->26 AND **25<->27**. The authorising brief said mode 27 must match mode 24;
    Honda's own firmware disagrees (`FactorC` m25/m27 = [0,233,426,875] vs m24/m26 = [0,234,429,908]),
    so holding m27 to m24 would fail on STOCK. Re-derived from the variant table, asserted both ways.
    """
    for live, manual in MODE_PAIRS:
        for name, arr in ALL_PTR_ARRAYS.items():
            lr, mr = factor_rec(buf, arr, live), factor_rec(buf, arr, manual)
            ln, mn = rec_len(buf, lr), rec_len(buf, mr)
            assert ln == mn, f"{label}: {name} m{live}/m{manual} record lengths differ"
            assert bytes(buf[lr:lr + ln]) == bytes(buf[mr:mr + mn]), \
                f"🛑 {label}: {name} ENGAGED m{live} @0x{lr:05X} != MANUAL m{manual} @0x{mr:05X}"
            assert bytes(buf[lr:lr + ln]) == bytes(stock[lr:lr + ln]), \
                f"🛑 {label}: {name} m{live} @0x{lr:05X} is not byte-STOCK"
            assert bytes(buf[mr:mr + mn]) == bytes(stock[mr:mr + mn]), \
                f"🛑 {label}: {name} m{manual} @0x{mr:05X} is not byte-STOCK"
        for kmh in REPORT_SPEEDS_KMH + (0, 15, 25, 45, 80, 140):
            sc = int(kmh * SPEED_COUNTS_PER_KMH)
            assert dose_row(buf, live, sc) == dose_row(buf, manual, sc), \
                f"🛑 {label}: at {kmh} km/h the m{live} dose != the m{manual} dose"
            ri_l, ri_m = relay_index(buf, live, sc), relay_index(buf, manual, sc)
            assert ri_l == ri_m, \
                f"🛑 {label}: at {kmh} km/h m{live}'s relay index {ri_l} != m{manual}'s {ri_m}"
            if ri_l is not None:
                assert abs(ri_l - HONDA_RELAY_INDEX) < 1e-9, \
                    f"🛑 {label}: at {kmh} km/h the relay index is {ri_l}, not Honda's " \
                    f"{HONDA_RELAY_INDEX} -- the surface is still relay-shaped"
    # 🛑 the ASYMMETRY SEARCH -- exhaustive over speed, not just the reported grid
    bad = [sc for sc in range(0, 14001, 8)
           for live, manual in MODE_PAIRS
           if dose_row(buf, live, sc) != dose_row(buf, manual, sc)]
    assert not bad, f"🛑 {label}: engaged/manual asymmetry survives at speed counts {bad[:8]}"


def assert_factor_surface(buf, stock, label, reverted):
    """FactorC m26/m27 and FactorE m26/m27, by value and -- after the revert -- byte-STOCK."""
    want_c = {LIVE_MODE: FACTOR_C_M26_NEW_Y if reverted else FACTOR_C_M26_BASE_Y,
              LIVE_MODE_2: FACTOR_C_M27_NEW_Y if reverted else FACTOR_C_M27_BASE_Y}
    want_e = {LIVE_MODE: FACTOR_E_M26_XY,
              LIVE_MODE_2: FACTOR_E_M27_NEW_XY if reverted else FACTOR_E_M27_BASE_XY}
    for mode, ys in want_c.items():
        n, xs, got = rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, mode))
        assert (n, got) == (4, ys), f"🛑 {label}: FactorC m{mode} Y is {got}, expected {ys}"
        assert xs == [2240, 3840, 5120, 8960], f"{label}: FactorC m{mode} X moved"
    for mode, (ex_w, ey_w) in want_e.items():
        n, ex, ey = rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, mode))
        assert (n, ex, ey) == (4, ex_w, ey_w), \
            f"🛑 {label}: FactorE m{mode} is ({ex}, {ey}), expected ({ex_w}, {ey_w})"
    if reverted:
        for name, rec in REVERTED_RECORDS.items():
            n = rec_len(buf, rec)
            assert bytes(buf[rec:rec + n]) == bytes(stock[rec:rec + n]), \
                f"🛑 {label}: {name} @0x{rec:05X} is not byte-STOCK over its full {n}-byte record"
    # FactorB / FactorD FLAT 1024 and the ceiling floor, per engaged mode, read BY COUNT
    for mode in ENGAGED_EXPECTED:
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD")):
            cnt, _x, y = rec_any(buf, factor_rec(buf, ptrs, mode))
            assert set(y) == {Q10}, f"{label}: {name} m{mode} ({cnt}-point) is not FLAT {Q10}: {y}"
        assert ceiling_floor(buf, mode) == CEILING_FLOOR, f"{label}: mode {mode}'s ceiling floor moved"


# =====================================================================================================
# THE INHERITED GUARDS -- V83a's keep-list plus V67's parent tables, all re-run
# =====================================================================================================

def assert_factor_monotone(buf, label, must_have_fold):
    """🛑 A damper factor that FALLS as its axis rises is a negative-slope characteristic -- the
    shape RULE 12 warns about. V83a's engaged `FactorC` has a 2.42x FOLD (566 -> 234) in BOTH
    engaged modes; edits 3-4 remove it. The `must_have_fold` arm asserts the fold IS present on the
    input, so the output check cannot be vacuous."""
    folds = []
    for name, ptrs in (("FactorC", FACTOR_C_PTRS), ("FactorE", FACTOR_E_PTRS)):
        for mode in THIS_CAR_MODES:
            n, _xs, ys = rec_any(buf, factor_rec(buf, ptrs, mode))
            bad = [i for i in range(n - 1) if ys[i] > ys[i + 1]]
            if bad:
                folds.append((name, mode, ys))
    if must_have_fold:
        assert {(f[0], f[1]) for f in folds} == {("FactorC", LIVE_MODE), ("FactorC", LIVE_MODE_2)}, \
            f"🛑 {label}: expected the engaged FactorC fold on modes {LIVE_MODE}/{LIVE_MODE_2} and " \
            f"nothing else, found {[(f[0], f[1]) for f in folds]}"
    else:
        assert not folds, \
            f"🛑 {label}: FactorC/FactorE Y is NON-MONOTONE at {[(f[0], f[1], f[2]) for f in folds]}"
    return folds


def assert_insurance_guards(buf, stock, label):
    """The damper ceiling record + its float twin, and the role table. One check each."""
    n = rec_len(buf, CEILING_REC_ADDR)
    assert bytes(buf[CEILING_REC_ADDR:CEILING_REC_ADDR + n]) == \
        bytes(stock[CEILING_REC_ADDR:CEILING_REC_ADDR + n]), \
        f"🛑 {label}: the damper ceiling record 0x{CEILING_REC_ADDR:05X} is not byte-STOCK -- it is " \
        "lockstep-checked at 5/1024 and a mismatch escalates to a DTC 0x1d HARD SHUTDOWN"
    for addr, val in CEILING_FLOAT_TWIN.items():
        raw = bytes(buf[addr:addr + 4])
        assert raw == bytes(stock[addr:addr + 4]) and \
            abs(struct.unpack("<f", raw)[0] - val) < 1e-6, \
            f"🛑 {label}: the ceiling float twin 0x{addr:05X} is {raw.hex()}, expected f32 {val}"
    role = bytes(buf[ROLE_TABLE_ADDR:ROLE_TABLE_ADDR + ROLE_TABLE_LEN])
    assert role == bytes(stock[ROLE_TABLE_ADDR:ROLE_TABLE_ADDR + ROLE_TABLE_LEN]), \
        f"🛑 {label}: the role table 0x{ROLE_TABLE_ADDR:05X} is not byte-STOCK"
    bad = [i for i, v in enumerate(role) if v in ROLE_FORBIDDEN]
    assert not bad, \
        f"🛑 {label}: role table slots {bad} carry role 6 or 7 -- `gp-0x67ac` would read 1 and the " \
        "aggregator would DROP r24, r26 and the damper, making EVERY lever in V84 vacuous"


def assert_keep_list(buf, label):
    for addr, (want, why) in KEEP_CELLS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: 0x{addr:05X} = {got}, expected {want} -- {why}"
    for addr, (want, why) in KEEP_BYTES.items():
        assert buf[addr] == want, \
            f"🛑 {label}: 0x{addr:05X} = 0x{buf[addr]:02X}, expected 0x{want:02X} -- {why}"
    for addr, (want, why) in KEEP_HALFWORDS.items():
        got = u16(buf, addr)
        assert got == want, f"🛑 {label}: 0x{addr:05X} = 0x{got:04X}, expected 0x{want:04X} -- {why}"
    for addr, (raw, val, why) in KEEP_F32.items():
        got = bytes(buf[addr:addr + 4])
        assert got == raw and struct.unpack("<f", got)[0] == val, \
            f"🛑 {label}: 0x{addr:05X} = {got.hex()}, expected {raw.hex()} ({val}) -- {why}"
    for addr, (n, why) in KEEP_ZERO_RUNS.items():
        assert set(buf[addr:addr + n]) == {0}, \
            f"🛑 {label}: 0x{addr:05X}+{n} is no longer all-zero -- {why}"
    for addr, raw in SAR_SITES.items():
        assert bytes(buf[addr:addr + 2]) == raw, \
            f"🛑 {label}: the `sar` site 0x{addr:05X} is {bytes(buf[addr:addr + 2]).hex()}, expected " \
            f"the STOCK {raw.hex()} -- V62's `a9` CAUSES GRIND #2, and on a GATED build it doubles " \
            "the PRODUCT of the 512 arm, partially undoing Lever B"


def assert_pointer_arrays_stock(buf, stock, label):
    """🛑 Every record is reachable ONLY through these. A moved pointer redirects a lever silently."""
    for name, arr in ALL_PTR_ARRAYS.items():
        for mode in range(N_MODES):
            got, want = u32(buf, arr + mode * 4), u32(stock, arr + mode * 4)
            assert got == want, \
                f"{label}: {name} array 0x{arr:05X}[{mode}] -> 0x{got:05X}, STOCK says 0x{want:05X}"
    for i, arr in enumerate(GAIN_B_PTRS):
        for mode in range(N_MODES):
            got, want = u32(buf, arr + mode * 4), u32(stock, arr + mode * 4)
            assert got == want, \
                f"{label}: gain_B array {i} 0x{arr:05X}[{mode}] -> 0x{got:05X}, STOCK 0x{want:05X}"


def assert_manual_modes_frozen(buf, base_img, stock, label):
    """🛑 Modes 24 AND 25 are THIS car's MANUAL columns. Byte-identical to the BASE and to STOCK."""
    out = {}
    for manual in (MANUAL_MODE, MANUAL_MODE_2):
        for name, arr in ALL_PTR_ARRAYS.items():
            key = {"FactorB": "B", "FactorC": "C", "FactorD": "D", "FactorE": "E"}.get(name, name)
            rec = factor_rec(buf, arr, manual)
            if manual == MANUAL_MODE:
                assert rec == MANUAL_EXPECT[key], \
                    f"{label}: {name} m{manual} -> 0x{rec:05X}, expected 0x{MANUAL_EXPECT[key]:05X}"
            n = rec_len(buf, rec)                # 🛑 the record's OWN length: 4 + 4*count
            assert bytes(buf[rec:rec + n]) == bytes(base_img[rec:rec + n]), \
                f"🛑 {label}: MANUAL mode {manual} {name} @0x{rec:05X} ({n} B) differs from the BASE"
            assert bytes(buf[rec:rec + n]) == bytes(stock[rec:rec + n]), \
                f"🛑 {label}: MANUAL mode {manual} {name} @0x{rec:05X} ({n} B) differs from STOCK"
            out[(manual, key)] = rec
    return out


def assert_friction_all_stock(buf, stock, label):
    """All 34 friction records byte-STOCK -- V81 reverted them and V84 must not touch them."""
    for mode in range(N_MODES):
        rec = factor_rec(buf, FRICTION_PTR_ARRAY, mode)
        n, xs, ys = rec_any(buf, rec)
        assert (n, xs, ys) == (FRICTION_NPT, FRICTION_X, FRICTION_Y_STOCK), \
            f"🛑 {label}: friction m{mode} @0x{rec:05X} is ({n}, {xs}, {ys}), expected Honda's"
        ln = rec_len(buf, rec)
        assert bytes(buf[rec:rec + ln]) == bytes(stock[rec:rec + ln]), \
            f"🛑 {label}: friction m{mode} @0x{rec:05X} is not byte-STOCK"


def assert_gain_a_honda(buf, stock, label):
    """gain_A: all four records == Honda's, whole record. `lp != 0` bypasses them while engaged."""
    for i, base in enumerate(GA.RATE_A_RECORDS):
        got = rec4_y(buf, base)
        want = list(GA.RATE_A_Y_STOCK[i])
        assert got == want, f"🛑 {label}: gain_A 0x{base:05X} Y is {got}, expected Honda's {want}"
        for y in got:
            assert 0 < y < 0x8000, \
                f"🛑 {label}: gain_A 0x{base:05X} Y = {y} is not a positive SIGNED halfword"
        n = rec_len(buf, base)
        assert bytes(buf[base:base + n]) == bytes(stock[base:base + n]), \
            f"🛑 {label}: gain_A 0x{base:05X} is not byte-STOCK"
    GA.assert_gain_a(buf, label, doubled=False)     # the kit's OWN guard, unmodified


def assert_cave_is_v75s(buf, label):
    """The BASE must still carry V75's magprobe cave, unmodified, before V84 repoints it."""
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    derived, _l = V75.build_cave()
    assert cave == derived, \
        f"🛑 {label}: the cave is not `build_v75_tva.build_cave()`'s 68 bytes -- V84's repoint is " \
        "defined as a delta from EXACTLY that cave"
    V75.assert_probe_censuses(bytes(buf), range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT),
                              V75.CAVE_ACCESS_ON_OUTPUT)
    return cave


def assert_cave_repointed(buf, label):
    """🛑 THE CAVE, RE-DERIVED AND RE-DISASSEMBLED OUT OF THE BUILT IMAGE.

    Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU). Nothing here
    is taken on trust: the 68 bytes are rebuilt from scratch by `build_cave()` (which re-runs every
    flag-liveness, branch-target and single-store gate), compared against the image, then decoded
    back out of the image by a SELF-CONTAINED decoder that was first calibrated against V75's
    decoder on V75's own cave.
    """
    cave = bytes(buf[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])
    derived, listing = build_cave()
    assert cave == derived, \
        f"🛑 {label}: the cave in the image is not `build_cave()`'s re-derivation\n" \
        f"      image  {cave.hex()}\n      derive {derived.hex()}"
    assert len(cave) == CAVE_EXTENT == 68, f"{label}: THE CAVE EXTENT MOVED -- it must stay 68"
    assert cave[66:68] == b"\xff\xff", f"{label}: the 2 padding bytes are not 0xFF"
    redis = redisassemble_v84_cave(cave)
    assert [(a, r) for a, r, _m in redis] == [(a, r) for a, r, _t in listing] + \
        [(CAVE_BASE + 66, b"\xff\xff")], \
        f"{label}: the readback re-disassembly diverges from the emitted listing"
    assert not [m for _a, _r, m in redis if m == "nop" or m.startswith("??")], \
        f"{label}: the cave re-disassembly contains a nop or an undecoded halfword"
    stores = [m for _a, _r, m in redis if m.startswith(("st.b", "st.h", "st.w"))]
    assert len(stores) == 1 and stores[0].startswith("st.b"), \
        f"{label}: the cave contains {stores}, expected exactly ONE st.b to the CAN-330 payload"
    # 🛑 THE ONE-BIT TRAP, checked on the IMAGE and not just on the emitter
    r24_insn = cave[2:6]
    assert ((struct.unpack_from("<H", r24_insn, 0)[0] >> 5) & 0x3F) == OP_LDH, \
        f"🛑 {label}: the cave's gp-0x6ada access is not `ld.h` (0x39). `st.h` is 0x3B, ONE BIT away."
    assert ((struct.unpack_from("<H", buf, R24_MIRROR_WRITER)[0] >> 5) & 0x3F) == OP_STH, \
        f"🛑 {label}: the firmware's own gp-0x6ada instance @0x{R24_MIRROR_WRITER:05X} is not `st.h`"
    assert bytes(r24_insn[2:4]) == bytes(buf[R24_MIRROR_WRITER + 2:R24_MIRROR_WRITER + 4]), \
        f"🛑 {label}: our load and the firmware's store do not address the SAME cell"
    # the hook is UNCHANGED -- same jarl, same return, same displaced movea
    assert bytes(buf[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: the hook @0x{HOOK_ADDR:05X} is not `jarl 0x{CAVE_BASE:05X}`"
    assert bytes(buf[HOOK_ADDR + 4:HOOK_ADDR + 6]) == HOOK_RETURN_INSN, \
        f"{label}: 0x{HOOK_ADDR + 4:05X} is not `mov 0x8,r7` -- r7 is not provably dead"
    assert cave.count(HOOK_STOCK) == 1, f"{label}: the displaced movea is not present exactly once"
    return cave, redis


def assert_no_399_channel(buf, label):
    """🛑 THE 399 CHANNEL IS ON HOLD BY OPERATOR DIRECTION. Assert it is genuinely absent.

    The standing instruction is: do not touch `0x55D50`, `0x55EFA`, or the cave region above
    `0xC4B78` until the wide-signal question is settled. Printing "not in this build" is a claim;
    this is the check behind it.
    """
    for addr, want in HOOK_399_STOCK.items():
        got = bytes(buf[addr:addr + 4])
        assert got == want, \
            f"🛑 {label}: the frame-399/427 hook site 0x{addr:05X} is {got.hex()}, expected the " \
            f"byte-stock {want.hex()} -- V84 must not have touched it"
    tail = bytes(buf[CAVE_BASE + CAVE_EXTENT:CAVE_FREE_END])
    assert set(tail) == {0xFF}, \
        f"🛑 {label}: the cave region above 0x{CAVE_BASE + CAVE_EXTENT:05X} is not untouched 0xFF " \
        f"({len(tail) - tail.count(0xFF)} non-FF byte(s)) -- a second cave was built"
    return len(tail)


def assert_probe_cells(buf, label):
    """🛑 GATE 1 FOR THE PROBE -- `census_gp4`: disp16 + disp23 + abs literal + movhi/movea.

    Run on input, output and readback. The cave READS these cells and WRITES NONE of them, which is
    asserted as a MEASUREMENT rather than argued: `gp-0x1500` passed both static methods and still
    failed on-car, so nothing here is taken from a previous build's notes.
    """
    span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    out = {}
    for disp, n_w, n_r, why in PROBE_CELLS:
        w, r, (lit, mhi) = V81.census_gp4(buf, disp)
        fw_w = [x for x in w if x[0] not in span]
        fw_r = [x for x in r if x[0] not in span]
        assert (len(fw_w), len(fw_r)) == (n_w, n_r), \
            f"🛑 {label}: gp-0x{disp:04x} ({why}) has {len(fw_w)}w/{len(fw_r)}r, expected " \
            f"{n_w}w/{n_r}r: writers {[hex(x[0]) for x in fw_w]}"
        assert not lit and not mhi, \
            f"🛑 {label}: gp-0x{disp:04x} has {len(lit)} absolute-literal and {len(mhi)} movhi/movea " \
            "reference(s) -- an ALIASED access the displacement scans cannot see"
        cave_w = [x for x in w if x[0] in span]
        assert not cave_w, \
            f"🛑 {label}: THE CAVE WRITES gp-0x{disp:04x} at {[hex(x[0]) for x in cave_w]} -- the " \
            "probe is supposed to be READ-ONLY telemetry"
        out[disp] = (len(fw_w), len(fw_r), len([x for x in r if x[0] in span]))
    # the two mirrors must have EXACTLY the writers the design names, by address
    for disp, addr in ((R24_DISP, R24_MIRROR_WRITER), (R26_DISP, R26_MIRROR_WRITER)):
        w, r, _e = V81.census_gp4(buf, disp)
        assert [x[0] for x in w] == [addr], \
            f"🛑 {label}: gp-0x{disp:04x}'s writer is {[hex(x[0]) for x in w]}, expected 0x{addr:05X}"
        assert not [x for x in r if x[0] not in span], \
            f"🛑 {label}: gp-0x{disp:04x} has acquired a FIRMWARE reader -- it is no longer free " \
            "telemetry and the blast-radius-zero claim is VOID"
    return out


def assert_matches_flown_v67(buf, v67, v68, stock, label):
    """★★ THE STRONGEST GATE THIS BUILD HAS.

    Every assist surface THIS CAR reads ends up byte-identical to the two builds whose measured
    grind-#1 result (0.40 [0.27, 0.58]) V84's S1 prediction rests on -- AND to Honda. Records are
    DEREFERENCED through their pointer arrays at this car's own four modes, never spanned.
    """
    for name, arr in ALL_PTR_ARRAYS.items():
        for mode in THIS_CAR_MODES:
            r = factor_rec(buf, arr, mode)
            assert u32(v67, arr + mode * 4) == u32(v68, arr + mode * 4) == r, \
                f"{label}: {name}[{mode}] points elsewhere on V67/V68"
            n = rec_len(buf, r)
            assert bytes(buf[r:r + n]) == bytes(v67[r:r + n]) == bytes(v68[r:r + n]) == \
                bytes(stock[r:r + n]), \
                f"🛑 {label}: {name} m{mode} @0x{r:05X} != the FLOWN V67/V68 and STOCK"
    for i, arr in enumerate(GAIN_B_PTRS):
        for mode in THIS_CAR_MODES:
            r = u32(buf, arr + mode * 4)
            assert bytes(buf[r:r + 0x14]) == bytes(v67[r:r + 0x14]) == bytes(v68[r:r + 0x14]) == \
                bytes(stock[r:r + 0x14]), f"🛑 {label}: gain_B {i} m{mode} != V67/V68/STOCK"
    for r in GA.RATE_A_RECORDS:
        assert bytes(buf[r:r + 0x14]) == bytes(v67[r:r + 0x14]) == bytes(v68[r:r + 0x14]) == \
            bytes(stock[r:r + 0x14]), f"🛑 {label}: gain_A 0x{r:05X} != V67/V68/STOCK"
    # ---- and the two Lever B cells themselves -----------------------------------------------------
    assert bytes(buf[REPOINT_ADDR:REPOINT_ADDR + 4]) == bytes(v67[REPOINT_ADDR:REPOINT_ADDR + 4]) \
        == bytes(v68[REPOINT_ADDR:REPOINT_ADDR + 4]) == REPOINT_TO, \
        f"🛑 {label}: the repoint does not match the FLOWN V67/V68"
    assert u16(buf, ARM_ADDR) == u16(v67, ARM_ADDR) == u16(v68, ARM_ADDR) == ARM_NEW, \
        f"🛑 {label}: the arm does not match the FLOWN V67/V68"
    assert u16(buf, R26_ARM_ADDR) == u16(v67, R26_ARM_ADDR) == u16(v68, R26_ARM_ADDR) == \
        R26_ARM_STOCK, f"🛑 {label}: r26's arm does not match the FLOWN V67/V68"
    return sum(1 for i in range(0x100000) if buf[i] != v67[i])


def assert_identity_modulo(buf, ref_img, allowed, label, refname):
    """🛑 THE VALUE-ANCHORED VERIFIER -- whole-image identity modulo an ATTRIBUTED set.

    `verify/diff_build_vs_stock.py` is SPAN-based and will pass a WRONG VALUE inside a RIGHT RANGE. This is
    the strongest statement available: restore every byte V84 is ALLOWED to have changed, then
    assert the result is byte-for-byte the reference over the FULL 1 MiB -- not over [START, END).
    """
    probe = bytearray(buf)
    for a in allowed:
        probe[a] = ref_img[a]
    diff = [i for i in range(len(ref_img)) if probe[i] != ref_img[i]]
    assert not diff, \
        f"🛑 {label}: after restoring the {len(allowed)} ATTRIBUTED bytes, the image still differs " \
        f"from {refname} at {len(diff)} byte(s): {[hex(x) for x in diff[:16]]}. V84 is defined as " \
        f"{refname} plus the attributed set and NOTHING else."
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

    v83a = bytes(Path(SRC_BIN).read_bytes())
    stock = bytes(Path(STOCK_BIN).read_bytes())
    v67 = bytes(Path(V67_BIN).read_bytes())
    v68 = bytes(Path(V68_BIN).read_bytes())
    v81 = bytes(Path(V81_BIN).read_bytes())
    print("=" * 102)
    print(f"SOURCE (V83a, flown route 68): {SRC_BIN}")
    src_sha = hashlib.sha256(v83a).hexdigest()
    print(f"  SHA256 {src_sha}")
    for name, img in (("V83a", v83a), ("stock", stock), ("V67", v67), ("V68", v68), ("V81", v81)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert src_sha not in NOT_THE_BASE, f"🛑🛑 THE BASE IS {NOT_THE_BASE.get(src_sha)}"
    assert src_sha == SRC_SHA256, \
        f"🛑🛑 THE BASE IS NOT V83a. SHA256 is {src_sha}, expected {SRC_SHA256}."
    assert hashlib.sha256(v67).hexdigest() == V67_SHA256, "the FLOWN V67 anchor drifted"
    assert hashlib.sha256(v68).hexdigest() == V68_SHA256, "the FLOWN V68 anchor drifted"
    assert hashlib.sha256(v81).hexdigest() == V81_SHA256, "the V81 chain anchor drifted"
    print("  ✅ the base SHA256 is the V83a cut EXACTLY, and the FLOWN V67/V68/V81 anchors verify.")
    print(f"  WRITE MODE: {WRITE_MODE or 'DRY RUN -- nothing will be written to disk'}")

    # =================================================================================================
    # GATE THE SOURCE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  GATING THE SOURCE -- everything below is measured on the INPUT before a byte moves")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert walk_all_blocks(v83a) == 0, "the V83a source's own CRC chain does not verify"

    key, modes, distinct_rows = derive_this_cars_modes(v83a)
    rows, ENGAGED, DISENGAGED = V74.derive_mode_columns(v83a)
    assert tuple(ENGAGED) == ENGAGED_EXPECTED and tuple(DISENGAGED) == DISENGAGED_EXPECTED
    assert not (set(ENGAGED) & set(DISENGAGED)), "🛑 THE MODE COLUMNS ARE NOT DISJOINT"
    for m in (LIVE_MODE, LIVE_MODE_2):
        assert m in ENGAGED, f"mode {m} is not an ENGAGED column"
    for m in (MANUAL_MODE, MANUAL_MODE_2):
        assert m in DISENGAGED, f"mode {m} is not a DISENGAGED column"
    print(f"    ✅ variant table 0x{VARIANT_TABLE:05X} row {THIS_CAR_ROW} = {key!r} -> modes "
          f"{modes}; all four DISTINCT")
    print(f"       (only rows {distinct_rows} in the whole table have four distinct columns)")
    print(f"       ⇒ ENGAGED = ({LIVE_MODE}, {LIVE_MODE_2}) · MANUAL = ({MANUAL_MODE}, "
          f"{MANUAL_MODE_2}) · 🛑 THE PAIRS ARE {MODE_PAIRS}")
    print(f"       ⚠ CORRECTION TO THE BRIEF: mode {LIVE_MODE_2}'s Honda pair is mode "
          f"{MANUAL_MODE_2}, NOT mode {MANUAL_MODE}.")
    print(f"         STOCK FactorC m{MANUAL_MODE_2}/m{LIVE_MODE_2} = {FACTOR_C_M27_NEW_Y} vs "
          f"m{MANUAL_MODE}/m{LIVE_MODE} = {FACTOR_C_M26_NEW_Y}.")

    # ---- the base preconditions, per edit ----------------------------------------------------------
    for addr, width, pre, _new, _grp, lbl in EDITS:
        got = v83a[addr] if width == 1 else u16(v83a, addr)
        assert got == pre, f"🛑 the base's 0x{addr:05X} ({lbl}) is {got}, expected V83a's {pre}"
    # ---- and where each TARGET value comes from ----------------------------------------------------
    for addr, width, _pre, new, grp, lbl in EDITS:
        if grp in STOCK_GROUPS:
            got = stock[addr] if width == 1 else u16(stock, addr)
            assert got == new, \
                f"🛑🛑 0x{addr:05X} ({lbl}): STOCK carries {got}, V84 wants {new}. Edits 3-7 are " \
                "DEFINED as pure reverts to Honda -- if a target is not stock's value, STOP."
        else:
            g67 = v67[addr] if width == 1 else u16(v67, addr)
            g68 = v68[addr] if width == 1 else u16(v68, addr)
            assert g67 == g68 == new, \
                f"🛑🛑 0x{addr:05X} ({lbl}): the FLOWN V67 carries {g67} and V68 {g68}, V84 wants " \
                f"{new}. Edits 1-2 are DEFINED as the FLOWN V67/V68 values. STOP."
    print(f"    ✅ all {len(EDITS)} base preconditions hold, and every TARGET is provenanced:")
    print(f"       edits 1-2 == the FLOWN V67 AND V68 · edits 3-7 == STOCK, byte for byte.")

    assert_edit_geometry(v83a, "V83a source")
    assert_keep_list(v83a, "V83a source")
    assert_pointer_arrays_stock(v83a, stock, "V83a source")
    assert_manual_modes_frozen(v83a, v83a, stock, "V83a source")
    assert_friction_all_stock(v83a, stock, "V83a source")
    assert_gain_a_honda(v83a, stock, "V83a source")
    assert_gain_b_inert_mode10(v83a, "V83a source")
    assert_factor_surface(v83a, stock, "V83a source", reverted=False)
    assert_cave_is_v75s(v83a, "V83a source")
    assert_probe_encoders(stock)
    n_decoder = assert_decoder_calibrated()
    decoder_ok = assert_decoder_module()
    assert_no_399_channel(v83a, "V83a source")
    probe_src = assert_probe_cells(v83a, "V83a source")
    assert_insurance_guards(v83a, stock, "V83a source")
    src_folds = assert_factor_monotone(v83a, "V83a source", must_have_fold=True)
    V74.assert_clamp_census(v83a)
    V72.assert_lever_c_single_reader(v83a)
    assert_repoint_and_chain(v83a, "V83a source", done=False)
    census_src = assert_gate_census(v83a, "V83a source", done=False, cave_span=cave_span)
    assert_repoint_twins(v83a, "V83a source")
    V67.assert_v57_probe_polarity("V84")
    gate_val = V67.assert_gate_validation("V84")
    sc1, rc1, lerp1, sat = assert_arm_derivation(v83a, "V83a source")
    print(f"    ✅ CRC 50/50 · mode columns re-derived (row {THIS_CAR_ROW} {key!r} = "
          f"{rows[THIS_CAR_ROW][2]})")
    print(f"    ✅ the keep-list, the six pointer arrays + all four gain_B arrays over {N_MODES} "
          "modes, MANUAL modes")
    print(f"       {MANUAL_MODE}/{MANUAL_MODE_2} byte-STOCK, all 34 friction records byte-STOCK, "
          "gain_A == Honda, the 68-byte")
    print("       cave and the probe census: ALL verified on the INPUT.")
    print(f"    ✅ 0xC407E = {u16(v83a, 0xC407E)} (Honda's), threshold 0xC4004 = f32 "
          f"{struct.unpack_from('<f', v83a, 0xC4004)[0]} ⇒ DTC-0x1d interlock intact and FROZEN.")
    print(f"    ✅ INSURANCE GUARDS: ceiling record 0x{CEILING_REC_ADDR:05X} + float twin "
          f"{[hex(a) for a in CEILING_FLOAT_TWIN]} byte-STOCK (DTC-0x1d lockstep),")
    print(f"       role table 0x{ROLE_TABLE_ADDR:05X} byte-STOCK with NO slot carrying role 6 or 7 "
          "(which would make every V84 lever vacuous).")
    print(f"    ⚠ THE FOLD IS PRESENT ON THE INPUT, so the output check is not vacuous: "
          f"{[(f[0], f'm{f[1]}', f[2]) for f in src_folds]}")
    print(f"       FactorC m{LIVE_MODE} FALLS {FACTOR_C_M26_BASE_Y[0]} -> "
          f"{FACTOR_C_M26_BASE_Y[1]} = a "
          f"{FACTOR_C_M26_BASE_Y[0] / FACTOR_C_M26_BASE_Y[1]:.2f}x DIP -- a negative-slope damper "
          "characteristic (RULE 12).")

    # ---- GATE 1: the census, FRESH ---------------------------------------------------------------
    print("\n    ★ GATE 1 -- THE CENSUS, RE-DERIVED ON THIS IMAGE (raw LE bytes, TWO decoders, both")
    print("      displacement parities, plus the 6-byte extended-disp/disp23 form). NOT inherited.")
    for disp in (DEAD_DISP, GATE_DISP):
        r, w, n_ext = census_src[disp]
        print(f"      gp-0x{disp:04x}  BEFORE: {len(r):2d} reader(s) / {len(w):2d} writer(s) · "
              f"{n_ext} extended-form candidate(s), all 32-bit aliases")
    print(f"        gp-0x{DEAD_DISP:04x}'s sole reader is 0x{census_src[DEAD_DISP][0][0]:05X} -- "
          "the repoint site ITSELF ⇒ the cell is DEAD and `lp` is a constant.")
    print(f"        gp-0x{GATE_DISP:04x} is the LKAS-active flag: agreement with `latActive` "
          f"{gate_val['_scratch/cache/r28']['agreement_pct']}% / "
          f"{gate_val['_scratch/cache/r29']['agreement_pct']}%")
    print(f"        over {gate_val['_scratch/cache/r28']['frames'] + gate_val['_scratch/cache/r29']['frames']:,} "
          f"frames at duty {gate_val['_scratch/cache/r28']['duty_pct']}% / "
          f"{gate_val['_scratch/cache/r29']['duty_pct']}%, "
          f"{gate_val['_scratch/cache/r28']['transitions'] + gate_val['_scratch/cache/r29']['transitions']} "
          "transitions")
    print("        ⇒ 0.03-0.05 transitions/s against a kill band starting at 30/s. V57's `ba05` = "
          "`bne` fixes the polarity.")
    print("\n    ★ GATE 1 FOR THE PROBE -- `build_v81_tva.census_gp4`: disp16 + disp23 + absolute")
    print("      literal + movhi/movea, on every cell the repointed cave touches.")
    for _d, _w, _r, _why in PROBE_CELLS:
        nw, nr, nc = probe_src[_d]
        print(f"      gp-0x{_d:04x}  {nw} writer(s) / {nr} firmware reader(s) · 0 abs-literal · "
              f"0 movhi/movea   {_why}")
    print(f"      ⇒ gp-0x{R24_DISP:04x} and gp-0x{R26_DISP:04x} are POST-CLAMP MIRRORS NOTHING "
          "READS: free, blast-radius-zero telemetry.")
    print(f"      ⇒ gp-0x{FD_AXIS_DISP:04x}'s readers are ALL `ld.hu` ⇒ UNSIGNED ⇒ the cave needs "
          "no ABS on it.")
    print(f"    ✅ the probe decoder was calibrated against V75's own decoder on V75's cave "
          f"({n_decoder} instructions, exact match)")
    print(f"    ✅ studies/probes/decode_v84_probe.py: {'imports THIS build\'s bit map; its self-test PASSES' if decoder_ok else 'NOT FOUND'}")
    print("       -- it REFUSES any log whose byte4 bit3 is ever clear, which is exactly how a "
          "V83a log gets rejected.")
    print(f"    ✅ the arm: gain_B LERP at grind #1's point ({GRIND1_KMH} km/h, {GRIND1_DEGS} deg/s "
          f"= {sc1}/{rc1} counts)")
    print(f"       re-derived TWO ways -- this car's mode-{LIVE_MODE} records give {lerp1}, the "
          f"mode-10 model gives {EX.r24_gain_q10(sc1, rc1, 0, 0, 0)} ⇒ arm = 2 x {lerp1} = {ARM_NEW}")
    print(f"       lane saturation at |dtorque| >= {sat} vs a MEASURED 123-839 ⇒ LINEAR. "
          f"{EX.INPUT_CLAMP} x {ARM_NEW} = "
          f"{100 * EX.INPUT_CLAMP * ARM_NEW / 0x7FFFFFFF:.2f}% of INT32_MAX.")

    # ---- calibrate the describing function BEFORE using it ----------------------------------------
    df_row, ri_v75 = assert_describing_function_calibrated(v83a)
    print(f"\n    ★ THE INSTRUMENT, CALIBRATED BEFORE USE. V83a's mode {LIVE_MODE_2} IS V75's damper "
          "package byte-for-byte.")
    print(f"      N(R) at R = {list(DF_AMPLITUDES)}")
    print(f"        this build : {[round(x, 3) for x in df_row]}")
    print(f"        STATE.md   : {list(V75_DF_ROW_RECORDED)}   ⇒ relay index "
          f"{ri_v75:.3f} vs the recorded {V75_RELAY_INDEX_RECORDED}")

    # =================================================================================================
    # APPLY THE EDITS
    # =================================================================================================
    code = bytearray(v83a)
    print("\n" + "-" * 102)
    print(f"  APPLYING THE {len(EDITS)} EDITS -- every one asserted BEFORE, AFTER, and against its "
          "provenance")
    print(f"      {'#':>2s} {'addr':<9s} {'cell':<22s} {'V83a':>6s} {'V84':>6s}  {'bytes':<16s} "
          "provenance")
    attributed = set()
    for i, (addr, width, pre, new, grp, lbl) in enumerate(EDITS, 1):
        got = code[addr] if width == 1 else u16(code, addr)
        assert got == pre, f"0x{addr:05X} moved between the gate and the write"
        old_raw = bytes(code[addr:addr + width])
        if width == 1:
            code[addr] = new
        else:
            struct.pack_into("<H", code, addr, new)
        new_raw = bytes(code[addr:addr + width])
        back = code[addr] if width == 1 else u16(code, addr)
        assert back == new, f"the write at 0x{addr:05X} did not take"
        if width == 2:
            assert s16(code, addr) == new, f"{new} does not round-trip as a signed int16"
        ref = stock if grp in STOCK_GROUPS else v67
        prov = "== STOCK" if grp in STOCK_GROUPS else "== FLOWN V67/V68"
        assert new_raw == bytes(ref[addr:addr + width]), \
            f"🛑🛑 0x{addr:05X} is now {new_raw.hex()}, the reference is " \
            f"{bytes(ref[addr:addr + width]).hex()}"
        attributed |= {addr + k for k in range(width)}
        # ⚠ edit 1 is an INSTRUCTION byte -- show it as hex, or `0xC5 -> 0xFB` reads as `197 -> 251`
        fmt = (lambda v: f"0x{v:02X}") if width == 1 else (lambda v: f"{v:d}")
        print(f"      {i:2d} 0x{addr:05X}  {lbl:<22s} {fmt(pre):>6s} {fmt(new):>6s}  "
              f"{old_raw.hex():<6s} -> {new_raw.hex():<6s}  {prov}")
    assert len(attributed) == 13, f"{len(attributed)} attributed bytes, expected 13 (1 + 6x2)"

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
    print(f"      V83a  {old_cave.hex()}")

    print(f"      V84   {new_cave.hex()}")
    print(f"      ⇒ {len(cave_attributed)} of {CAVE_EXTENT} cave bytes differ; the last 2 are 0xFF "
          "PADDING (the design needs 66).")
    for _a, _r, _t in cave_listing:
        print(f"        0x{_a:05X} {_r.hex():<10s} {_t}")

    # ---- edit 1's own re-decode, through the INDEPENDENT decoder -----------------------------------
    mnem, disp, reg1, reg2 = assert_repoint_and_chain(code, "V84", done=True)
    print(f"\n    EDIT 1, RE-DECODED FROM THE BUILT IMAGE by `scan_gp_accesses` (not by our encoder):")
    print(f"      0x{REPOINT_ADDR:05X}  {REPOINT_FROM.hex()} -> "
          f"{bytes(code[REPOINT_ADDR:REPOINT_ADDR + 4]).hex()}   {mnem} -0x{disp:04x}[r{reg1}],"
          f"r{reg2}")
    twins = assert_repoint_twins(code, "V84")
    print(f"      the EXACT four bytes already execute at {', '.join(f'0x{a:05X}' for a in twins[:2])}"
          f" (byte-identical) and 0x{twins[2]:05X} (reg2 only)")
    print(f"      hw1 UNCHANGED ⇒ the 'one byte' claim is machine-checked: -0x{GATE_DISP:04x} = "
          f"0x{(-GATE_DISP) & 0xFFFF:04X} is EVEN, so the opcode parity field never moves")

    # ---- whole-record identity, the thing that makes edits 3-7 a REVERT ----------------------------
    print("\n    WHOLE-RECORD IDENTITY (the `0xD2A7E` hybrid's failure mode, closed by construction):")
    for name, rec in REVERTED_RECORDS.items():
        n = rec_len(code, rec)
        assert bytes(code[rec:rec + n]) == bytes(stock[rec:rec + n]), \
            f"🛑 {name} @0x{rec:05X} is not byte-STOCK after the revert"
        print(f"      {name:<10s} @0x{rec:05X}  {n:2d} B  {bytes(code[rec:rec + n]).hex()}  "
              "== STOCK, whole record")

    # =================================================================================================
    # RE-ASSERT EVERYTHING ON THE FINISHED IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  RE-ASSERTING ON THE FINISHED IMAGE")
    assert_edit_geometry(code, "V84")
    assert_keep_list(code, "V84")
    assert_pointer_arrays_stock(code, stock, "V84")
    man = assert_manual_modes_frozen(code, v83a, stock, "V84")
    assert_friction_all_stock(code, stock, "V84")
    assert_gain_a_honda(code, stock, "V84")
    assert_gain_b_inert_mode10(code, "V84")
    assert_factor_surface(code, stock, "V84", reverted=True)
    assert_engaged_equals_manual(code, stock, "V84")
    cave, cave_redis = assert_cave_repointed(code, "V84")
    probe_out = assert_probe_cells(code, "V84")
    # 🛑 The FIRMWARE census cannot move -- V84 adds no firmware access to any of these cells. What
    # 🛑 DOES move is the CAVE's own read count, and it must move by EXACTLY the design: +1 read on
    # 🛑 the three cells the cave reads, and 0 on gp-0x6adc, which V84 does not use.
    CAVE_READS_EXPECTED = {R24_DISP: 1, R26_DISP: 0, FD_AXIS_DISP: 1, FD_GATE_DISP: 1}
    for _d, _w, _r, _why in PROBE_CELLS:
        assert probe_out[_d][:2] == probe_src[_d][:2], \
            f"🛑 gp-0x{_d:04x}'s FIRMWARE census moved across the edit ({probe_src[_d][:2]} -> " \
            f"{probe_out[_d][:2]}) -- impossible for a cave repoint; STOP AND REPORT"
        assert probe_src[_d][2] == 0, \
            f"🛑 V83a's cave already read gp-0x{_d:04x} -- the delta below would not be V84's"
        assert probe_out[_d][2] == CAVE_READS_EXPECTED[_d], \
            f"🛑 V84's cave reads gp-0x{_d:04x} {probe_out[_d][2]} time(s), expected " \
            f"{CAVE_READS_EXPECTED[_d]}"
    assert_insurance_guards(code, stock, "V84")
    assert_factor_monotone(code, "V84", must_have_fold=False)
    V74.assert_clamp_census(bytes(code))
    V72.assert_lever_c_single_reader(bytes(code))
    census_out = assert_gate_census(code, "V84", done=True, cave_span=cave_span)
    assert_arm_derivation(code, "V84")
    # 🛑 the parent guards, re-run with the ONE documented exception (0xC6446 = the arm)
    V67.assert_untouched_context_v67(code, "V84")
    V67.assert_untouched_v67(code, "V84")
    V67.assert_signal_sites(code, "V84")
    _r2, eng2, dis2 = V74.derive_mode_columns(bytes(code))
    assert (eng2, dis2) == (ENGAGED, DISENGAGED), "the mode columns moved"
    assert derive_this_cars_modes(bytes(code))[1] == THIS_CAR_MODES

    # 🛑 A REPOINT CANNOT CREATE A WRITER. Asserted across the edit, not merely counted after it.
    assert census_out[GATE_DISP][1] == census_src[GATE_DISP][1], \
        "🛑 gp-0x6806's WRITER SET moved across a repoint -- impossible; STOP AND REPORT"
    assert census_out[DEAD_DISP][1] == census_src[DEAD_DISP][1] == [], "gp-0x683c acquired a writer"
    moved = set(census_out[GATE_DISP][0]) - set(census_src[GATE_DISP][0])
    assert moved == {REPOINT_ADDR}, f"the reader delta is {[hex(a) for a in moved]}, not the repoint"
    print(f"    ✅ GATE 1: gp-0x{DEAD_DISP:04x} {len(census_src[DEAD_DISP][0])}r/0w -> "
          f"**{len(census_out[DEAD_DISP][0])}r/0w = UNREFERENCED IMAGE-WIDE**")
    print(f"       gp-0x{GATE_DISP:04x} {len(census_src[GATE_DISP][0])}r/"
          f"{len(census_src[GATE_DISP][1])}w -> {len(census_out[GATE_DISP][0])}r/"
          f"{len(census_out[GATE_DISP][1])}w; the reader delta is EXACTLY "
          f"{{0x{REPOINT_ADDR:05X}}} and the")
    print("       WRITER SET IS BYTE-FOR-BYTE UNCHANGED. V84 writes no RAM at all.")
    print(f"    ✅ MANUAL modes {MANUAL_MODE}/{MANUAL_MODE_2} byte-STOCK on all six record types "
          f"({len(man)} records checked)")
    print("    ✅ gain_A all four records == HONDA · all 34 friction records byte-STOCK · mode-10 "
          "gain_B INERT and unmoved")
    print(f"    ✅ MONOTONE: FactorC/FactorE Y is non-decreasing on ALL of modes {THIS_CAR_MODES} "
          "-- the 2.42x engaged fold is GONE.")
    print(f"    ✅ CAVE: {CAVE_EXTENT} B @0x{CAVE_BASE:05X} == `build_cave()`'s re-derivation, "
          f"re-disassembled out of the BUILT image")
    print(f"       into {len(cave_redis)} instructions with no nop and no undecoded halfword; "
          "exactly ONE store; hook UNCHANGED.")
    print(f"       {cave.hex()}")
    print(f"    ✅ PROBE GATE 1 unchanged across the edit; the cave WRITES none of its four cells.")
    print(f"       🛑 the one-bit trap: our gp-0x{R24_DISP:04x} access is `ld.h` op 0x{OP_LDH:02X}; "
          f"the firmware's own instance")
    print(f"       @0x{R24_MIRROR_WRITER:05X} is `st.h` op 0x{OP_STH:02X}, and both carry the SAME "
          "displacement halfword.")

    # =================================================================================================
    # ★ THE DAMPER SURFACE -- RULE 12 AS SHAPE, RE-DERIVED FROM THE BUILT IMAGE
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  ★ GATE 5 (RULE 12) -- THE DAMPER SHAPE, RE-DERIVED FROM THE BUILT IMAGE")
    print("    🛑 'Does not clip' is NOT 'is not a relay'. V80 clipped 0.00% and was a bang-bang "
          "relay. SHAPE, not bound.")
    print(f"\n    DELIVERED |gp-0x6bd0| over rates {list(REPORT_RATES)} counts "
          f"(/{RATE_COUNTS_PER_DEG_S} = deg/s)")
    print(f"      {'img':<5s} {'mode':>4s} {'km/h':>5s} | " +
          "  ".join(f"{r:>5d}" for r in REPORT_RATES))
    for tag, img, ms in (("V83a", v83a, (MANUAL_MODE, LIVE_MODE, LIVE_MODE_2)),
                         ("V84", code, (MANUAL_MODE, MANUAL_MODE_2, LIVE_MODE, LIVE_MODE_2))):
        for mode in ms:
            for kmh in REPORT_SPEEDS_KMH:
                sc = int(kmh * SPEED_COUNTS_PER_KMH)
                row = "  ".join(f"{v:5d}" for v in dose_row(img, mode, sc))
                print(f"      {tag:<5s} {mode:4d} {kmh:5d} | {row}")
        print()
    print(f"    RELAY INDEX N(50)/N(500) and FLATNESS max/min  "
          f"(Honda = {HONDA_RELAY_INDEX:.2f} = VISCOUS; V80 = 3.27 = RELAY)")
    print(f"      {'img':<5s} {'mode':>4s} {'km/h':>5s} {'N(50)/N(500)':>13s} {'flat max/min':>13s}")
    for tag, img, ms in (("V83a", v83a, (MANUAL_MODE, LIVE_MODE, LIVE_MODE_2)),
                         ("V84", code, (MANUAL_MODE, MANUAL_MODE_2, LIVE_MODE, LIVE_MODE_2))):
        for mode in ms:
            for kmh in REPORT_SPEEDS_KMH:
                sc = int(kmh * SPEED_COUNTS_PER_KMH)
                ri, fl = relay_index(img, mode, sc), flatness(img, mode, sc)
                ris = "DEAD (M==0)" if ri is None else f"{ri:.4f}"
                fls = "DEAD (M==0)" if fl is None else f"{fl:.3f}"
                print(f"      {tag:<5s} {mode:4d} {kmh:5d} {ris:>13s} {fls:>13s}")
        print()
    ri27_before = relay_index(v83a, LIVE_MODE_2, int(5 * SPEED_COUNTS_PER_KMH))
    ri27_after = relay_index(code, LIVE_MODE_2, int(5 * SPEED_COUNTS_PER_KMH))
    print(f"    🛑 MODE {LIVE_MODE_2} WAS CARRYING V81's ENTIRE DAMPER PACKAGE: relay index at "
          f"5 km/h {ri27_before:.3f} -> "
          f"{'DEAD' if ri27_after is None else f'{ri27_after:.3f}'} (Honda's).")
    # 🛑 THE NO-CLIP TEST, STATED CORRECTLY. `max dose < ceiling FLOOR` is the WEAK test and on a
    # 🛑 wide enough grid **HONDA'S OWN SURFACE FAILS IT** -- mode 24 delivers 533 at 100 km/h and
    # 🛑 rate 4000 (849 deg/s), above the 512 floor, on STOCK. That is not a defect and V84 must not
    # 🛑 pretend to a bound Honda does not hold. The CORRECT gate is POINTWISE IDENTITY TO STOCK:
    # 🛑 V84 clips exactly where, and only where, Honda clips. That subsumes no-clip entirely.
    worst, where = 0, None
    for m in THIS_CAR_MODES:
        for kmh in REPORT_SPEEDS_KMH + (0, 15, 25, 45, 80, 140):
            sc = int(kmh * SPEED_COUNTS_PER_KMH)
            got, want = dose_row(code, m, sc), dose_row(stock, m, sc)
            assert got == want, \
                f"🛑 {'V84'}: mode {m} at {kmh} km/h delivers {got}, STOCK delivers {want} -- the " \
                "engaged surface is supposed to BE Honda's after edits 3-7"
            for r, v in zip(REPORT_RATES, got):
                if v > worst:
                    worst, where = v, (m, kmh, r)
    m_w, k_w, r_w = where
    assert damper_authority(stock, m_w, int(k_w * SPEED_COUNTS_PER_KMH), r_w) == worst, \
        "the worst dose is not Honda's own value at that point"
    print(f"    ✅ POINTWISE IDENTITY TO STOCK: every one of the four modes delivers EXACTLY Honda's "
          "dose at every")
    print("       reported (speed x rate) point ⇒ V84 clips exactly where, and only where, Honda "
          "clips. This SUBSUMES")
    print(f"       the no-clip test. ⚠ The weak `max < ceiling FLOOR {CEILING_FLOOR}` bound would "
          f"FAIL here: the worst dose is")
    print(f"       {worst} at mode {m_w}, {k_w} km/h, rate {r_w} "
          f"(= {r_w / RATE_COUNTS_PER_DEG_S:.0f} deg/s) -- and that is **STOCK's own value**, "
          "asserted.")
    print(f"    ✅ every engaged column equals its manual pair EXACTLY over speed counts 0..14000 "
          "(the STRONG test).")
    print(f"    ✅ S4 IS STRUCTURALLY SATISFIED: modes {LIVE_MODE}=={MANUAL_MODE} and "
          f"{LIVE_MODE_2}=={MANUAL_MODE_2}, byte-identical, all six families.")

    # =================================================================================================
    # ★ THE RATE LANES -- WHAT ACTUALLY CHANGES WHILE ENGAGED
    # =================================================================================================
    print("\n" + "-" * 102)
    print("  ★ THE RATE LANES WHILE ENGAGED (lp != 0). MANUAL (lp == 0) IS BYTE-FOR-BYTE STOCK.")
    grid = arm_multiplier_grid(code)
    print(f"\n    r24: arm 0x{ARM_ADDR:05X} = {ARM_NEW} REPLACES the mode-{LIVE_MODE} gain_B LERP")
    print(f"      {'km/h':>6s} {'deg/s':>6s} {'LERP':>7s} {'arm/LERP':>9s}")
    for (kmh, degs), (lerp, arm) in grid.items():
        print(f"      {kmh:6.1f} {degs:6d} {lerp:7d} {arm / lerp:9.3f}")
    mults = [a / l for l, a in grid.values()]
    print(f"      ⇒ a SCALAR arm cannot track a CURVE: {min(mults):.3f}x .. {max(mults):.3f}x over "
          f"the regime, 2.000x exactly at grind #1's point.")
    print(f"\n    r26: arm 0x{R26_ARM_ADDR:05X} = {R26_ARM_STOCK} (STOCK, LEFT ALONE) REPLACES the "
          "gain_A LERP ⇒ the S3 lever")
    print(f"      {'km/h':>6s} {'HONDA LERP':>11s} {'V72 cut':>9s} {'V84 arm':>9s} "
          f"{'V84/HONDA':>10s} {'== V72?':>8s}")
    for kmh in (0, 2, 5, 7.2, 10, 15, 20, 30, 50, 100):
        sc = int(kmh * SPEED_COUNTS_PER_KMH)
        honda, v72cut = GA.gain_a_q10(code, sc, 0), GA.gain_a_q10(v81, sc, 0)
        print(f"      {kmh:6.1f} {honda:11d} {v72cut:9d} {R26_ARM_STOCK:9d} "
              f"{R26_ARM_STOCK / honda:10.3f} {str(v72cut == R26_ARM_STOCK):>8s}")
    same = [k for k in (0, 2, 5, 7.2, 10)
            if GA.gain_a_q10(v81, int(k * SPEED_COUNTS_PER_KMH), 0) == R26_ARM_STOCK]
    assert same == [0, 2, 5, 7.2, 10], \
        "🛑 V84's engaged r26 arm is NOT numerically V72's cut at <=10 km/h -- the S3 rationale fails"
    print("      ✅ V84's engaged r26 arm IS V72's cut, numerically, at every speed up to 10 km/h "
          "(asserted).")
    print("      ⚠ ABOVE 10 km/h THEY DIVERGE AND V84 CUTS DEEPER -- V72's LERP climbs back to 2664 "
          "by 50 km/h, V84's")
    print("        flat arm does not. Not unflown: V67 and V68 carried this exact configuration at "
          "road speed, fault-free.")
    print("      🛑 V67 justified this side-effect with 'r26 is structurally inert'. THAT ARGUMENT "
          "IS RETRACTED (leg 1")
    print("        REVERSED, leg 2 downgraded to BELIEF). V84 does not rely on it -- it adopts the "
          "cut DELIBERATELY, as S3.")

    # ---- ★★ the equivalence gate -------------------------------------------------------------------
    n_v67 = assert_matches_flown_v67(code, v67, v68, stock, "V84")
    print(f"\n    ★★ V84 == THE FLOWN V67 == THE FLOWN V68 == STOCK on ALL SIX factor families, all "
          f"four gain_B arrays")
    print(f"       and all four gain_A records, at THIS CAR'S OWN MODES {THIS_CAR_MODES} -- whole "
          "records, dereferenced.")
    print(f"       Over the full 1 MiB, V84 differs from the flown V67 at {n_v67} bytes: 0x454FE "
          "(V42's macro-ratchet fix,")
    print(f"       which V84 HAS at 0x{KEEP_BYTES[0x454FE][0]:02X} and V67 did NOT at "
          f"0x{v67[0x454FE]:02X}), the 68-byte probe cave, the CRC trailers,")
    print("       mode-10 gain_B (V69/V70's inert writes) and OTHER CARS' records at modes this car "
          "never dereferences.")
    print("       ⇒ the S1 prediction is an INTERPOLATION ONTO a measured point, not an "
          "extrapolation off one.")

    # =================================================================================================
    # CRC
    # =================================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = [0xC4FFC, 0xC6FFC, 0xD7FFC]
    assert [b[1] for b in blocks] == expect_trailers, \
        f"expected trailers {[hex(t) for t in expect_trailers]}, got {[hex(b[1]) for b in blocks]}"
    print("\n" + "-" * 102)
    print(f"  CRC -- EXACTLY {len(blocks)} block(s) move (ASSERTED against "
          f"{[hex(t) for t in expect_trailers]}, not observed):")
    print("    ⚠ the brief named the first block '0x13000'. That is its START; the block is "
          "[0x013000,0x0C4FFC) and")
    print("      its TRAILER is at 0x0C4FFC. Derived by V53.owning_block, never assumed.")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        owners = [hex(a) for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}"
              f"   owns {owners}")
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
    for a, w, pre, new, _g, lbl in EDITS:
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
    print("  🛑 FULL BYTE DIFF: BUILT V84 vs V83a -- over the WHOLE 1 MiB image")
    runs = diff_runs(code, v83a, attribute)
    total = sum(b - a + 1 for a, b in runs)
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    print(f"      {'range':<21s} {'len':>4s}  {'V83a':<10s}    {'V84':<10s}  attribution")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {bytes(v83a[a:b + 1]).hex():<10s} -> "
              f"{bytes(code[a:b + 1]).hex():<10s}  {attribute(a)}")
    assert not stray, \
        f"🛑 UNATTRIBUTED bytes vs V83a: {[hex(x) for x in stray[:16]]} -- STOP AND REPORT"
    diff_bytes = {d for a, b in runs for d in range(a, b + 1)}
    functional = total - len(crc_only & diff_bytes)
    fn_runs = [r for r in runs if attribute(r[0]) != "CRC trailer"]
    # 🛑 THE WRITE COUNT AND THE DIFF COUNT ARE NOT THE SAME NUMBER. V84 WRITES 13 bytes but only
    # DIFFERS in 12, because edit 5 (12 -> 60 = `0c00` -> `3c00`) shares its high byte with the base.
    # 🛑 COUNT CELLS, NOT BYTES -- the right number for a lever set is 7. All three are asserted here,
    # derived independently, so none can silently absorb an error in the others.
    expect_diff = 0
    for a, w, _p, new, _g, _l in EDITS:
        raw = bytes([new]) if w == 1 else struct.pack("<H", new)
        expect_diff += sum(1 for k in range(w) if v83a[a + k] != raw[k])
    assert expect_diff == 12, f"the per-edit differing-byte count re-derives as {expect_diff}, not 12"
    assert functional == expect_diff + len(cave_attributed), \
        f"{functional} functional bytes differ, expected {expect_diff} cell + " \
        f"{len(cave_attributed)} cave"
    assert len(attributed) == 13 + len(cave_attributed), \
        f"{len(attributed)} attributed bytes, expected 13 cell + {len(cave_attributed)} cave"
    cave_runs = [r for r in fn_runs if CAVE_BASE <= r[0] < CAVE_BASE + CAVE_EXTENT]
    cell_runs = [r for r in fn_runs if r not in cave_runs]
    assert len(cell_runs) == len(EDITS) == 7, \
        f"{len(cell_runs)} CELL runs, expected {len(EDITS)}"
    assert sum(b - a + 1 for a, b in cave_runs) == len(cave_attributed), \
        "the cave runs do not cover exactly the differing cave bytes"
    assert len(runs) == len(cell_runs) + len(cave_runs) + len(blocks), \
        f"{len(runs)} runs, expected {len(cell_runs)} cell + {len(cave_runs)} cave + " \
        f"{len(blocks)} CRC"
    print(f"    ⇒ {len(cell_runs)} CELL run(s) = {len(EDITS)} cells covering {expect_diff} "
          f"differing byte(s), + {len(cave_runs)} CAVE run(s) covering")
    print(f"      {len(cave_attributed)} of the {CAVE_EXTENT} cave bytes, + {total - functional} "
          f"CRC byte(s) in {len(blocks)} run(s).")
    print("      🛑 COUNT CELLS, NOT BYTES. The CONTROL-PATH lever set is SEVEN cells; the cave is "
          "ONE repoint inside an")
    print(f"      unchanged {CAVE_EXTENT}-byte extent, not {len(cave_attributed)} separate edits. "
          "Edit 5 (12 -> 60) shares its high byte")
    print("      with the base and so moves ONE byte, not two. Every count is asserted "
          "independently.")

    # ---- THE VALUE-ANCHORED VERIFIERS: whole-image identity modulo the attributed set --------------
    assert_identity_modulo(code, v83a, attributed | crc_only, "V84", "V83a")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = v83a[a]
    rt_sha = hashlib.sha256(bytes(rt)).hexdigest()
    assert rt_sha == SRC_SHA256, f"the round trip yields {rt_sha}, expected {SRC_SHA256}"
    print(f"    ✅ VALUE-ANCHORED ROUND TRIP: restoring the {len(attributed)} attributed + "
          f"{len(crc_only)} CRC bytes reproduces")
    print(f"       V83a BIT-FOR-BIT -- sha256 back to {rt_sha[:16]}… over all 0x100000 bytes. A "
          "TOTAL statement.")

    # ---- chained to the flown V81, so the whole post-V81 delta is attributed in one statement ------
    v83a_attr = {a + k for a, _p, _n, _r, _l in V83A.EDITS for k in range(2)}
    v83a_crc = {t + k for t in (0xC6FFC, 0xD7FFC) for k in range(4)}
    assert_identity_modulo(code, v81, attributed | crc_only | v83a_attr | v83a_crc, "V84",
                           "the flown V81")
    print(f"    ✅ CHAINED: restoring V84's {len(attributed)} bytes AND V83a's own {len(v83a_attr)} "
          "attributed bytes plus")
    print("       both builds' CRC trailers reproduces the FLOWN V81 byte-for-byte ⇒ the entire "
          "V81 -> V84 delta is")
    print("       attributed, with nothing unexplained anywhere in the image.")
    d_stock = sum(1 for i in range(0x100000) if code[i] != stock[i])
    d_stock_base = sum(1 for i in range(0x100000) if v83a[i] != stock[i])
    print(f"    ⊕ vs STOCK: V84 differs at {d_stock} bytes, V83a at {d_stock_base}. V84 is NOT a "
          "pure revert -- edits 1-2 are")
    print("      deliberate departures from Honda, and they are the two that have flown and worked.")

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
    FF.assert_x31_checksum(rwd, "V84 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v83a)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, never from the in-memory build.
    assert_edit_geometry(dec, "V84 readback")
    assert_keep_list(dec, "V84 readback")
    assert_pointer_arrays_stock(dec, stock, "V84 readback")
    assert_manual_modes_frozen(dec, v83a, stock, "V84 readback")
    assert_friction_all_stock(dec, stock, "V84 readback")
    assert_gain_a_honda(dec, stock, "V84 readback")
    assert_gain_b_inert_mode10(dec, "V84 readback")
    assert_factor_surface(dec, stock, "V84 readback", reverted=True)
    assert_engaged_equals_manual(dec, stock, "V84 readback")
    assert_cave_repointed(dec, "V84 readback")
    assert assert_probe_cells(dec, "V84 readback") == probe_out, "the readback probe census differs"
    assert_insurance_guards(dec, stock, "V84 readback")
    assert_factor_monotone(dec, "V84 readback", must_have_fold=False)
    V74.assert_clamp_census(bytes(dec))
    V72.assert_lever_c_single_reader(bytes(dec))
    assert_repoint_and_chain(dec, "V84 readback", done=True)
    assert assert_gate_census(dec, "V84 readback", done=True, cave_span=cave_span) == census_out, \
        "🛑 the readback census differs from the built image's"
    assert_repoint_twins(dec, "V84 readback")
    assert_arm_derivation(dec, "V84 readback")
    assert_matches_flown_v67(dec, v67, v68, stock, "V84 readback")
    assert V74.derive_mode_columns(bytes(dec))[1:] == (ENGAGED, DISENGAGED)
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    assert_identity_modulo(dec, v83a, attributed | crc_only, "V84 readback", "V83a")
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    print(f"    ✅ READBACK: the edit geometry, all {len(EDITS)} values, the repoint's INDEPENDENT "
          "re-decode and its")
    print("       gp census, the arm derivation, the keep-list, the pointer arrays, MANUAL modes "
          f"{MANUAL_MODE}/{MANUAL_MODE_2},")
    print("       all 34 friction records, gain_A, the FactorC/FactorE surface, the engaged==manual "
          "dose identity,")
    print("       the V67/V68 equivalence, the 68-byte cave and its re-disassembly, identity to "
          "V83a outside the")
    print("       attributed set, and the full 50/50 CRC chain: ALL re-verified FROM THE DECODED "
          ".rwd PAYLOAD.")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # =================================================================================================
    # WRITE -- only if explicitly enabled
    # =================================================================================================
    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WAS WRITTEN TO DISK.")
        print("     Re-run with ACCORD_V84_WRITE=rwd to cut the artefacts.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(
                f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists (on disk "
                f"{hashlib.sha256(existing).hexdigest()}, about to write {img_sha}). A same-number "
                "re-cut destroyed a predecessor's snapshot once already and produced an artefact NO "
                "gate could check. Rename or delete it deliberately, then re-run.")
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
            FF.assert_x31_checksum(shipped, "V84 shipped")
            sb = parse_x31(shipped)
            assert sb["headers"] == FF.EXPECTED_HEADERS
            assert sb["blocks"] == [{"start": START, "length": END - START}]
            sd = bytearray(v83a)
            sd[START:END] = bytes(sb["encs"][0]).translate(decode)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert_repoint_and_chain(sd, "V84 shipped-from-disk", done=True)
            assert_gate_census(sd, "V84 shipped-from-disk", done=True, cave_span=cave_span)
            assert_factor_surface(sd, stock, "V84 shipped-from-disk", reverted=True)
            assert_engaged_equals_manual(sd, stock, "V84 shipped-from-disk")
            assert_gain_a_honda(sd, stock, "V84 shipped-from-disk")
            assert_keep_list(sd, "V84 shipped-from-disk")
            assert_matches_flown_v67(sd, v67, v68, stock, "V84 shipped-from-disk")
            assert_cave_repointed(sd, "V84 shipped-from-disk")
            assert_probe_cells(sd, "V84 shipped-from-disk")
            assert_insurance_guards(sd, stock, "V84 shipped-from-disk")
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code), \
                "the written plain image does not re-read as the built image"
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded, and its payload")
            print("     re-verified (the repoint + its census, the damper surface, engaged==manual, "
                  "gain_A, the keep-list,")
            print("     the V67/V68 equivalence, 50/50 CRC) INDEPENDENTLY of the in-memory build.")

    print(f"\n  V84 [{VARIANT_TOKEN}] -- image SHA256 {img_sha}")
    print(f"                                    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  ★ CONTROL PATH: {len(EDITS)} CELLS (13 bytes written, {expect_diff} differing) -- "
          f"LEVER B restored (0x{REPOINT_BYTE:05X} 0xC5->0xFB,")
    print(f"    0x{ARM_ADDR:05X} {ARM_STOCK}->{ARM_NEW}, the FLOWN V67/V68 values) + the "
          f"engaged-only damper DELETED in BOTH")
    print(f"    engaged modes {LIVE_MODE} and {LIVE_MODE_2} (relay index "
          f"{ri27_before:.2f} -> Honda's {HONDA_RELAY_INDEX:.2f}).")
    print(f"  ★ TELEMETRY: the cave @0x{CAVE_BASE:05X} REPOINTED off the damper onto the delivered "
          f"r24 mirror + FactorD's")
    print(f"    two open gates -- {len(cave_attributed)}/{CAVE_EXTENT} bytes differ, "
          f"EXTENT UNCHANGED at {CAVE_EXTENT}, hook 0x{HOOK_ADDR:05X} unchanged, ONE store.")
    print(f"    0x14A byte4: b7 r24>=+{R24_COUNTS_POS} · b6 r24<=-{R24_COUNTS_NEG} · "
          f"b5 gp-0x{FD_GATE_DISP:04x} in {{1,2}} · b4 gp-0x{FD_AXIS_DISP:04x}>={FD_AXIS_THRESH} · "
          "b3 FINGERPRINT=1")
    print("  🛑 THE 399 CHANNEL IS **NOT** IN THIS BUILD -- 0x55D50 / 0x55EFA are byte-stock and "
          "0xC4B78+ is untouched 0xFF.")
    print("  🛑 PRE-REGISTERED: S1 ~0.40x V83a. **If grind #1 does not improve, Lever B is "
          "FALSIFIED on a third")
    print("     independent flight and the rate lane should be abandoned as an S1 lever.** S2 is a "
          "HYPOTHESIS, not a promise.")
    print("  🛑 NOT ADDRESSED: the highway/high-speed grind (V67/V68 carried Lever B and it "
          "persisted) and the ~28 Hz")
    print("     lane-change transient (dose-independent, full amplitude on the stock lane -- "
          "EXCITATION, not gain).")
    print("  🛑 THE COST: engaged r26 damping is cut to 512 flat at ALL speeds, and the engaged "
          "wheel gets LIGHTER at every")
    print("     speed. If the micro-ratchet gets worse, edits 3-7 are the cause and reverting them "
          "is 10 bytes.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without touching an image."""
    assert len(EDITS) == 7 and len({a for a, *_ in EDITS}) == 7
    assert sum(1 for _a, w, _p, _n, _g, _l in EDITS if w == 1) == 1, "exactly ONE byte-wide edit"
    assert sum(1 for _a, _w, _p, _n, g, _l in EDITS if g in FLOWN_V67_GROUPS) == 2
    assert sum(1 for _a, _w, _p, _n, g, _l in EDITS if g in STOCK_GROUPS) == 5
    assert {g for _a, _w, _p, _n, g, _l in EDITS} == set(FLOWN_V67_GROUPS) | set(STOCK_GROUPS)
    assert all(0 <= n < 0x8000 for _a, _w, _p, n, _g, _l in EDITS), "a target is not a valid int16"
    # ---- the byte/cell/run arithmetic, derived rather than quoted --------------------------------
    assert sum(w for _a, w, _p, _n, _g, _l in EDITS) == 13, "the write count is not 13"
    assert struct.pack("<H", 12)[1] == struct.pack("<H", 60)[1], \
        "🛑 12 -> 60 must move exactly ONE byte -- COUNT CELLS, NOT BYTES"
    assert struct.pack("<H", 200) != struct.pack("<H", 400)[:1] + struct.pack("<H", 200)[1:]
    assert struct.pack("<H", ARM_NEW) == bytes.fromhex("7c14") and ARM_NEW == 0x147C
    # ---- edit 1's parity claim, the one that makes it a ONE-BYTE edit ----------------------------
    assert ((-GATE_DISP) & 0xFFFF) % 2 == 0, \
        "🛑 -0x6806 is ODD -- the repoint would be a THREE-byte edit across both halfwords"
    assert REPOINT_FROM[:2] == REPOINT_TO[:2] and REPOINT_FROM[3] == REPOINT_TO[3], \
        "the repoint moves more than hw2's low byte"
    assert sum(1 for k in range(4) if REPOINT_FROM[k] != REPOINT_TO[k]) == 1
    assert V67.decode_ldbu(REPOINT_TO) == ("ld.bu", GATE_DISP, GP, 15)
    assert V67.decode_ldbu(REPOINT_FROM) == ("ld.bu", DEAD_DISP, GP, 15)
    # ---- the mode pairing, as an executable fact -------------------------------------------------
    assert MODE_PAIRS == ((26, 24), (27, 25)), "🛑 the pairing is 24<->26 and 25<->27"
    assert FACTOR_C_M26_NEW_Y != FACTOR_C_M27_NEW_Y, \
        "🛑 if Honda's m26 and m27 FactorC were equal, the brief's 'match mode 24' gate would work"
    assert FACTOR_C_M26_NEW_Y[0] == FACTOR_C_M27_NEW_Y[0] == 0, "Honda's FactorC Y[0] is 0"
    assert set(THIS_CAR_MODES) == {24, 25, 26, 27}
    # ---- the arm ---------------------------------------------------------------------------------
    assert ARM_NEW == 2 * GRIND1_LERP == 5244 and GRIND1_LERP == 2622
    assert V83A.SRC_SHA256 == V81_SHA256, "the V81 anchor is not V83a's own base"
    assert SRC_SHA256 not in NOT_THE_BASE
    assert "+" not in VARIANT_TOKEN and all(c.isalnum() or c in ".-" for c in VARIANT_TOKEN)


if __name__ == "__main__":
    _self_check()
    build()
