#!/usr/bin/env python3
"""build_v68_tva.py -- V68 = V67's CONTROL PATH, BYTE-IDENTICAL, with a re-aimed probe.

WHAT V68 IS, AND WHAT IT DELIBERATELY IS NOT
---------------------------------------------
V68 is a **MEASUREMENT BUILD**. It changes NOTHING that touches torque. V67's two control-path
edits -- the one-byte repoint at `0x3AA96` and the arm `0xC6446 = 5244` -- are carried forward
byte-for-byte, and the build asserts that the ONLY differences from V67 anywhere in
`[0x13000,0x100000)` are the cave span and the two CRC trailers.

🛑 **NO CONTROL-PATH CHANGE IS JUSTIFIED BY THE CURRENT EVIDENCE.** V67 is the best build this kit
has measured: grind #1 fixed (18-22 Hz 0.55 [0.34, 0.65] vs the Kd=1 pool against a split-half null
of [0.88, 1.13]), creep grind #2 eliminated (0 burst blocks in 113 s vs 24 at Kd=2x), flight-clean,
and byte-stock on the rate lane whenever LKAS is off. The operator reports a highway resonance, and
a three-dose highway comparison showed no rate-lane dose response at 40-49 Hz -- but **bit5 below is
the one firmware-side way that null could be an artifact**, so V68 measures it instead of assuming.

THE TWO CHANGES: bit5 and bit4 are re-aimed. bit6, bit7, bit3 are untouched.
-----------------------------------------------------------------------------
On routes `47` (150,327 frames) and `4a` (35,999 frames) -- both V67 -- bit5 (`gp-0x671d != 0`) and
bit4 (`gp-0x671a >= 5`) BOTH read **0.000%**, i.e. ~1,860 s of ordinary driving with two frozen
rungs. Both are re-spent, each on a question that a frozen reading could not answer:

    bit5 = (gp-0x67df != 0)    the detector FSM LEFT NEUTRAL -- |gp-0x6c2c| crossed +-T.
    bit4 = (gp-0x671a >= 1)    ...and then REVERSED at least once (V67 tested >= 5).

🛑🛑 **bit5 WAS AIMED AT `gp-0x67ac`, AND THAT CELL IS PROVABLY 0 ON THIS BUILD. RE-POINTED.**
`FUN_0003aa2c` skips the r24/r26 aggregate add iff `gp-0x67ac == 1` exactly, so a lane dropout would
have invalidated last session's highway null. It cannot happen here, and the proof is a **calibration
byte read**, not a runtime argument: `gp-0x67ac` is fed by an 11-slot OR-latch in `FUN_00026c80` whose
only set path requires a per-slot role of **6 or 7**, and the static role table at `tp+0x5124` =
**`0xC4124`** reads **`[0,0,5,0,5,5,0,0,0,5,0]`** -- no slot is ever 6 or 7. The fallthrough path was
refuted at register level too (`0x27258 cmp 0x4,r12` / `setfe` / `be 0x2727c` leaves r12 = 0).
⇒ the rate lanes cannot silently drop out, and the highway null was NOT reading a disconnected lane.
**That question is CLOSED without spending a rung on it** -- probing a proven zero is exactly the error
V68's original bit4 made.
⚠ **THIS RESTS ON CALIBRATION BYTES, NOT ON STRUCTURE.** `assert_signal_sites()` re-reads `0xC4124`
on every build and STOPS if any slot ever carries a 6 or a 7. If that table changes, this reopens.
⚠ OPEN, not a blocker, recorded so it is not lost: `gp-0x61a0`'s writer is unresolved (search the
**callers** of `FUN_00026c80` and its sibling mixer-state functions, not the function itself -- the
slot selection is likely populated upstream), and `gp-0x61e8`'s identity is unestablished.

★★ **THE RUNG NOW BUYS A SECOND DETECTOR STAGE -- `gp-0x67df`, AND IT HAS ALREADY FLOWN.**
bit5 and bit4 are two **strictly ordered stages of the same 1 kHz band-pass detector**:

    bit5 = (gp-0x67df != 0)   the FSM has LEFT NEUTRAL: |gp-0x6c2c| crossed +-T = 12800.
                              *** NO REVERSAL REQUIRED. ***
    bit4 = (gp-0x671a >= 1)   ...and then REVERSED at least once.

`gp-0x67df` fires on events that are **too brief or too one-sided to produce a reversal** -- precisely
the marginal, intermittent case the operator describes, and the case bit4 alone cannot see. Both cells
hold >= 50 ms (the `0xC64DD` = 50-tick dwell), so both are reliably catchable by a 100 Hz probe.
✅ Its encoding is **LIFTED, NOT RE-DERIVED**: `ld.bu -0x67df[gp],r6` = `a4372198` is byte-identical
to **V64's own flown cave word at `0xC4B4C`**, where it was V64's bit4 and drove route 35.
🛑 **AND ITS DISPLACEMENT IS ODD.** `gp-0x67df`'s disp16 is `0x9821`, so the `ld.bu` opcode field
is **`0x3D`** (hw1 `a437`), not the `0x3C` (hw1 `8437`) that bit4's EVEN `0x98E6` carries. `ld.bu`
hides displacement bit 0 in the OPCODE FIELD, so assuming one parity silently addresses the
NEIGHBOURING cell with every other field perfect. Both parities are asserted from the image.

⚠ **THE TRADE, STATED PLAINLY:** this spends the rung on a second *stage* rather than on the `>= 5`
persistence bracket. Justified because V67 already measured `gp-0x671a >= 5` at **0.000% over 186,321
frames across routes 47 and 4a** -- the information is at the BOTTOM of the ladder, not the top -- and
because a positive on `>= 1` is itself the detection we want; whether it reached 5 is secondary.

★★ **bit4 IS THE KIT'S ONLY ABOVE-50-Hz INSTRUMENT.** `gp-0x6c2c`'s cascade is a **BAND-PASS peaking
near 61 Hz**, not a low-pass. Gain relative to 21.09 Hz: 1 Hz **0.05x** · 45 Hz **1.54x** ·
61 Hz **1.61x (max)** · 100 Hz **1.43x** · 200 Hz 0.94x. So the amplitude needed to TRIP it FALLS
above 50 Hz: 21.3 Hz needs **1683** counts, 45 Hz **1104**, 60 Hz **1056**, 100 Hz **1186**,
150 Hz 1478, 200 Hz 1735. Sanity-checked against the golden model's own sizing (1683 -> 12804 trips
T = 12800; 1682 -> 12797 does not). **Honda's own 1 kHz detector is MORE sensitive exactly where CAN
(Nyquist 50.00 Hz) and the comma IMU (50.51 Hz) are blind.**
⚠ V67's 0.000% does not speak to this: V67's rung tested `>= 5`, the CEIL (cal `0xC64FA` = 5). This
one tests `>= 1`, the lowest rung of the same 0..5 counter. A null at 5 does not imply a null at 1.

★★ WHY THAT IS THE HIGHEST-VALUE BIT AVAILABLE -- IT ADJUDICATES A LIVE CONTRADICTION
--------------------------------------------------------------------------------------
Two of this kit's own load-bearing numbers disagree about which side of that breakpoint the car
operates on, and NOTHING in the record resolves it:

  * The **telemetry derivation**: bus counts = 1.697754 x `gp-0x6ac0` (byte-verified through cal
    `0xC613A` = 1159), from which 100% of all symptom windows were placed INSIDE the flat first
    segment `[0, 400]`. That was never measured directly -- it is bus telemetry pushed through a
    scale chain.
  * **V67's own arm value**: `5244 = 2 x 2622`, where 2622 is the LERP at "motor rate 128 deg/s".
    128 deg/s is **603 counts** -- which is on the SLOPED segment, i.e. the opposite side.

Both cannot be right, and the difference is not cosmetic. Read from the four mode-10 `gain_B`
records this build asserts byte-identical (`0xD2A74/0xD2AB0/0xD2AEC/0xD2B28`):

    X = (0, 400, 1400|1500, 3000)      Y = (3072, 3072, 2322, 1536)  etc.
    => the segment [0, 400] is EXACTLY FLAT in three of four records and flat to one count
       (2305 -> 2304) in the fourth.

    at 7.2 km/h:   rate <  400 counts  ->  LERP = 2704   (flat)
                   rate =  603 counts  ->  LERP = 2622   (sloped -- what 5244 was derived from)

⇒ if bit4 reads ~0%, V67's arm is delivering **5244/2704 = 1.94x**, not the 2.00x its docstring
claims, and the arm for exactly 2.00x is **5408**. That is a 3% correction -- immaterial to the fix,
but it is the difference between a number we measured and a number we assumed. More importantly it
decides, for every FUTURE calibration on this lane, whether the rate axis can discriminate at all:
**a lane whose operating point never leaves a flat segment cannot be tuned on wheel rate.**

🛑🛑 THE PRE-REGISTERED PREDICTION IS RETRACTED (2026-08-03). THE PROBE IS UNCHANGED AND STILL VALID
-----------------------------------------------------------------------------------------------------
An earlier revision of this docstring predicted **bit4 == 0.000%** with a "1.442x headroom", derived
from route 47's cache through `gp-0x6ac0 = |0x18F rate counts| x 32768/(48*1159) = x 0.5890135`
(p50 0.6 · p90 10.6 · p99 105.4 · p99.9 221.3 · MAX 277.4 counts; 0 of 150,327 at or above 400).

**THAT DERIVATION IS STRUCK.** It rests on the relation `bus = 8 x deg/s`, which `CLAUDE.md` records
as **RETRACTED** -- the bus field IS deg/s (slope 0.95-1.00, r >= 0.985 against the differentiated
angle), which is also what makes V67's own arm derivation (LERP 2622 => exactly 2.00x) correct. The
contradiction is arithmetically exact and is asserted below rather than described:

    this file's own import  EX.RATE_COUNTS_PER_DEGS = 4.71210813920046   counts per deg/s
    the struck chain factor                          0.5890135
    ratio                                            8.000000236          <- the retracted x8

Under the surviving chain, route 47's numbers map ~8x higher (MAX ~2219, p99 ~843 counts), so bit4
would be a GRADED reading of order a few percent, **not a frozen zero**. No replacement prediction is
pre-registered here: the two chains disagree by construction and settling that is the probe's job.

★ THE RUNG IS UNAFFECTED, AND THAT IS THE POINT OF READING THE CELL DIRECTLY. bit4 compares the
firmware's OWN `gp-0x6ac0` against the LERP's own breakpoint, in the firmware's own units, **with the
scale chain removed from the question entirely.** It answers the same structural question either way:

    bit4 ~ 0 over a long mixed drive  =>  the operating point IS inside the flat first segment and
                                          the lane's rate axis is a CONSTANT in use.
    bit4 > 0                          =>  the operating point leaves the flat segment, the
                                          flat-segment claim is dead, and every conclusion resting
                                          on it -- including V67's arm derivation -- needs re-deriving.

🛑 WHAT MUST NOT BE REPEATED: a *derived* quantity was pre-registered as if it were a measurement, and
the same file imported the constant that contradicts it. If a future build pre-registers a prediction,
assert the chain it rests on against every other copy of that chain in the same module.

⚠ THE THRESHOLD IS A CHOICE, AND IT IS THE ORCHESTRATOR'S TO OVERRIDE.

🛑 THE DUTY TABLE BELOW IS COMPUTED ON THE STRUCK CHAIN AND IS THEREFORE VOID AS A PREDICTION. It is
left visible because the *ordering* it encodes is what the threshold choice rested on, and hiding it
would hide the reasoning. Every percentage in it assumes the retracted x8; on the surviving chain each
row corresponds to a threshold 8x LOWER, so none of these numbers describes T = 400.

       T      ALL    gate TRUE   creep<=5 m/s        [VOID -- struck chain]
      50    3.640%     0.728%      13.396%
     100    1.132%     0.000%       4.478%
     200    0.160%     0.000%       0.632%
     400    0.000%     0.000%       0.000%      <- SHIPPED

**Shipped at 400** because it is the LERP's own first breakpoint, read in the firmware's own units
with the scale chain removed from the question. That reason is independent of the struck derivation
and survives it; the "predicted frozen / one-sided" argument does NOT and is withdrawn.
T = 100 would be strictly more informative *about the chain* but answers the breakpoint question
only by extrapolating through the chain it is testing. Changing it costs a 2-byte `movea` immediate
plus relaxing the `_self_check_wire` flatness assertion -- trivially re-buildable if preferred.

⚠ ONE ASYMMETRY, STATED RATHER THAN DISCOVERED LATER. The LERP folds its key to 0 above
`RATE_FOLD = 13001` (`0x3AAC8 addi -0x32c9 / 0x3AACC cmovc`), so a folded value ALSO lands on the
flat first point. bit4 does not test the fold -- a second compare costs 6 more bytes than the cave
has. Therefore:

    bit4 == 0  =>  DEFINITELY inside the flat segment.                        (unambiguous)
    bit4 == 1  =>  on the sloped segment, OR folded past 13001 counts.        (two readings)

13001 counts is **2759 deg/s** of motor rate, roughly 20x the fastest this kit has ever recorded,
so the fold is implausible rather than impossible. The asymmetry runs in the safe direction: the
claim under test is "always flat", and bit4 == 0 confirms it outright.

★ bit3 BECOMES A BUILD-CLASS MARKER -- AND IT COSTS ZERO BYTES
---------------------------------------------------------------
🛑 The V64 lesson: a constant `0x87` has meant FOUR different things across builds (V64's detector
null, V65's neutral ladder bucket, V66's all-gates-zero, V67's gate-never-true), and V66/V67 are
**mutually inseparable by payload** -- `route_build_registry.identify()` asserts that as a property.
That ambiguity has already cost this kit a session.

V68 ends it for itself by folding bit3 into the liveness immediate: `movea 0x88,r0,r7` instead of
`movea 0x80,r0,r7`. **Same instruction, same four bytes, same encoder, different immediate.** So:

    EVERY legal V68 frame has BOTH bit7 AND bit3 set, and V68 NEVER emits 0x87.

🛑 STATED AT ITS REAL STRENGTH, IN TWO TIERS -- both machine-checked below, not typed. An earlier
draft of this docstring said "no prior build can produce that". **That is FALSE**, and the check in
`_self_check_wire()` caught it:

  TIER 1 -- STRUCTURALLY DISJOINT, absolute. V53 emits only `0x07`; V54 only `0x0F` (bit7 clear);
    V66 and V67 both ASSERT that bit3 is never set by their caves, so their entire eight-payload
    space is disjoint from V68's. These can never be confused with V68 by payload.
  TIER 2 -- EXCLUDED BY THEIR RECORDED ROUTES ONLY, and against V59/V62 the marker is WEAK:
      V59/V62 thermometer space ∩ V68 = {0x8F, 0x9F, 0xBF, 0xCF, 0xDF, 0xFF}   SIX of eight
      V65 ladder space          ∩ V68 = {0x9F}                                 one of eight
    So V65 is nearly excluded on structure; **V59/V62 are not excluded on structure at all.** They
    are excluded because both of their recorded routes contain `0x87`, which V68 cannot emit. A
    hypothetical V59 log whose boost index never dropped below 512 would be indistinguishable from
    V68 by payload alone. `identify()` and the decoder both say this rather than rounding it up.

The marker also doubles as a second liveness bit: a frame with bit7 set and bit3 clear is ILLEGAL
under V68, so a partial or foreign write is caught rather than silently interpreted.

⚠ It is a marker, not proof of the flashed file. It cannot exclude a FUTURE build. The .rwd
filename remains the primary evidence and the decoder still says so.

THE PAYLOAD -- 0x14A byte4 bits 7:3
------------------------------------
    bit7 = 1                    LIVENESS.  field == 0 => the cave did not fire => the reading is VOID
    bit6 = gp-0x6806 != 0       *** THE GATE *** -- carried from V67 unchanged. V67's own route
                                measured it at 99.983% agreement with carControl.latActive over
                                150,327 frames; bit6 keeps re-measuring it, and it is the
                                engagement covariate every other bit is conditioned on.
    bit5 = gp-0x67df != 0       *** NEW *** the detector FSM has LEFT NEUTRAL: |gp-0x6c2c| crossed
                                +-T = 12800. NO reversal required -- this is the stage BELOW bit4,
                                and it catches events too brief or one-sided to reverse.
    bit4 = gp-0x671a >= 1       *** NEW THRESHOLD *** Honda's 1 kHz oscillation detector, lowest
                                rung. A HOLD-TIME statistic, not an event rate -- see below.
    bit3 = 1                    the V68 BUILD-CLASS MARKER. Constant.
    bits 2:0                    stock STEER_SENSOR_STATUS, preserved.

🛑 HOW TO READ bit4 -- DUTY IS NOT OCCUPANCY, AND GETTING THIS WRONG INFLATES THE DETECTOR RATE
------------------------------------------------------------------------------------------------
`gp-0x671a` counts REVERSALS of `gp-0x6c2c` past +-T (cal `0xC620A` = 12800), via raw counter
`gp-0x357c` and FSM state `gp-0x67df`. It is a 0..CEIL counter and bit4 asks only "is it >= 1".

  * **SUB-CEIL (1..4)** -- cleared by the **50-tick dwell** (cal `0xC64DD` = 50), so a trip is
    visible for only ~**50 ms** => about **5 frames** at the 100 Hz TX rate.
    ⚠ **BRIEF EVENTS WILL BE UNDER-COUNTED**, and an isolated reversal may be missed entirely.
  * **AT CEIL (5, cal `0xC64FA`)** -- the output is RE-PINNED every tick. Release requires **5000
    ticks (cal `0xC6270` = 5.0 s)** with `gp-0x6a5e >= 640` AND no reversals. `gp-0x6a5e` is voted
    **VEHICLE SPEED** (voter `FUN_00041eec`, settled 2026-07-29) and 640 counts is **~10 km/h**.
    ⇒ **below ~10 km/h the latch NEVER releases**; at road speed it releases 5 s after the last
    reversal.

⇒ **bit4 is a HOLD-TIME statistic.** Duty over-states brief events at speed and saturates at creep.
🛑 **AND IT IS A DETECTOR, NOT A SPECTROMETER.** It reports THAT a reversal past +-T occurred. It
gives **neither amplitude nor frequency**. Any frequency attribution must come from conditioning on
something else (speed, maneuver, the gate) -- never from bit4 alone.
⚠ The 100 Hz sampling barrier is unchanged: bit4's own TIME SERIES is aliased like everything else.
What is new is that the QUANTITY it reports was computed at 1 kHz inside the ECU. **bit4 carries
above-50-Hz information; it does not carry an above-50-Hz waveform.**

🛑🛑 WHAT THE STICKY / HIGH-FREQUENCY RUNG WOULD HAVE BEEN, AND WHY IT IS NOT HERE
-----------------------------------------------------------------------------------
The brief asked for a latching rung sampling inside the 1 kHz task, to break the ~50 Hz aliasing
barrier (CAN 100.5 Hz, comma IMU 99.9-100.5 Hz; grind #2's "44.9 Hz" is itself an alias of ~55.6).
**It is not built, and the reason is not caution. FOUR independent walls, and the first one is
fatal on its own.**

  0. 🛑🛑 **THE HOOK RUNS AT 100 Hz, NOT 1 kHz. THE PREMISE IS FALSE.** Traced end to end this
     session: `0x55C0E` sits in `FUN_00055a98`, the CAN-0x14A builder (`movea 0x14a,r0,r8`
     @0x55C14). Its ONLY pointer image-wide is at `0xB72D4` = index 10 of handler table
     `PTR_FUN_000b72ac`. Message-10's pending bit is set only by `FUN_0001eaa6(0xa)` @`0x5560C` in
     `FUN_00055540`, whose sole caller is `FUN_00022ca0` @`0x234C4` = **TCB idx-4 = task 5 =
     `c % 10 == 4` = 100 Hz.** The inner "frame due" test at `0x555F2-0x5560C` is a one-shot
     power-on suppression (down-counter `gp-0x2f68` with NO reload path), so steady state is a
     clean 100 Hz.
     ⇒ **A latch at this hook cannot sample faster than the frame it is written into**, so it
     degenerates to a plain sample no matter how many bytes or RAM cells it is given.
     ⇒ 🛑 **NO PROBE ON THIS HOOK CAN EVER BREAK THE ALIASING BARRIER.** Doing so needs a SECOND
     hook inside task 1, which is new code on the 1 kHz path and carries the DTC-0x18 cadence
     watchdog's timing budget. That is a different and much larger decision.
     ⚠ **V67's docstring says "the 1 kHz TX path". THAT IS WRONG** and is corrected here; the
     `accord-can-tx-100hz-base-tick-and-gateway` memory was right all along.
  1. **BUDGET. It does not fit, and the cave must not grow.** V55's proven extent is 68 bytes and
     has flown eight times (V55/V57/V58/V59/V64/V65/V66/V67). Fixed overhead -- liveness, the
     payload read-modify-write, the displaced hook instruction, `jmp [lp]` -- is 24 bytes. Keeping
     bit6 and bit5 costs 12 bytes each. **That leaves 20 bytes.** A latch rung on `gp-0x4f62`
     needs, at minimum: `ld.h` (4) + abs via `cmp`/`bge`/`subr` (6) + a threshold compare (4+2+2)
     + the bit `movea` (4) = **22 bytes before any latch machinery at all**, and a genuine latch
     adds a RAM-cell load, a store and a clear -- 42 bytes total, 2.1x the space. Growing the cave
     past 68 is precisely this kit's only bricking class (V24, V27, V48B).
  2. **IT IS NOT FREQUENCY-SELECTIVE, so it would not answer the question.** `gp-0x4f62` is read
     `ld.h` at 6 sites -- a SIGNED halfword, confirmed independently this session -- and it is the
     raw 4-sample finite difference. A scalar threshold on |it| is an amplitude detector, not a band
     detector. Its low-frequency content (driver steering) already measures 123-839 counts, so any
     threshold that ignores the driver must sit above ~839 -- at which point the bit fires exactly
     during large driver inputs, which is *also* the condition under which grind #2 occurs. **The
     bit would be confounded with its own hypothesis by construction.** Making it band-selective
     needs a filter, and this kit has already established (see `docs/STATE.md`) that a filter able
     to bite by 42 Hz destroys the 20.9 Hz lead V62/V67 bought.
  3. **THE CLEAR EVENT DOES NOT EXIST -- now CONFIRMED FROM THE CODE, not inferred.** A latch is
     informative only if reset once per transmitted frame. `gp-0x1514` has exactly EIGHT accesses
     image-wide (Ghidra and a raw byte scan agree) and **not one of them writes bits 7:3**:
     `0x2194A`/`0x21964` is a WORD read-modify-write that ANDs with `0xff0000ff` and ORs in a term
     whose low byte is zero, so our byte goes back **bit-identical**; the three pairs at
     `0x55AAC`/`0x55AD4`/`0x55AF4` mask with `0xFB`/`0xFD`/`0xFE` and touch only bits 2:0. The
     block-copy / memset / register-indirect class is CLEAN too: the only two `movea` constructions
     into the frame region are our own hook and `0x56288` (a different frame's base), and
     `gp-0x1515`/`gp-0x1517` have zero accesses while `gp-0x1516`'s single `st.h` writes bytes 2-3
     only. ⇒ a never-cleared latch would pin ON after the first trip -- a dead probe that still
     looks alive.

⇒ **The sticky rung is impossible at this hook, and would not have measured what it was meant to
measure even if it were. GATE 1 was never reached, so no RAM cell is claimed and GATE 1 stays
VACUOUS.** V68's only store is the existing CAN-330 payload byte `gp-0x1514`, asserted from the
emitted listing to be the ONE AND ONLY store in the cave -- exactly as on V55 through V67.

★★ AND THE GATE-1 AUDIT ON `gp-0x683c` CAME BACK MOSTLY CLOSED -- RECORDED, STILL UNUSED
------------------------------------------------------------------------------------------
The cell is unreferenced by any displacement form after V67's repoint (0 readers, 0 writers, 0
extended-form candidates -- asserted below on every build). This session took the audit further and
**found the boot writers nobody in this kit had**, which is the leg a displacement scan is blind to:

    0x146C0   mov 0xfedec000,ep / sst.w r0,{0,4,8,c}[ep] / addi 0x10,ep,ep / cmp r6,ep / bc
              => zeroes ALL of 0xFEDEC000..0xFEDFFFFF        (the bss clear)
    0x14766   mov 0xfedf11b0,ep, src r14 = 0x86260, end r10 = 0x8ab18
              => copies flash 0x86260..0x8AB18 (18,616 B) into 0xFEDF11B0..0xFEDF5A68   (.data)

Both go through `sst.w` with a COMPUTED `ep`, so they are invisible to disp16 scans, disp23 scans,
`search_instructions` AND `get_xrefs_to` -- exactly the blind spot that let `gp-0x1500` pass two
static methods and still fail on-car. ⇒ `gp-0x683c` (= 0xFEDF17C4) is **.data, not bss**, and its
boot value is `flash[0x86260 + 0x614]` = `flash[0x86874]` = **0x00**. That *positively explains* the
dead gate -- a declared object whose writer was compiled out, defaulting to 0 -- instead of merely
failing to find a writer.

Also closed: all 712 `movhi 0xFEDF/0xFEE0` resolved (nearest effective address 1,559 B away); every
`mov imm32` enumerated (a +-1.5 KB pointer-free zone around the cell); the LE32 literal
`0xFEDF17C2/C3/C4` appears **0** times; the `ep`-relative leg (three `ep` constants land in this
page but all three converge on `sst.b r6,0x0,ep`, displacement 0); and the stack
(`sp = 0xFEDEF91C`, growing down -- the cell sits 7,848 B above the stack top).
Neighbourhood: 42 of the 49 bytes in `gp-0x6850..gp-0x6820` are individually gp-addressed from ~30
different functions with **no base pointer anywhere in the page** ⇒ independent scalars, NOT an
indexed struct.

🛑 STILL OPEN, and this is why V68 does not use it: **(a)** a base pointer loaded from RAM/flash at
runtime plus a computed index, **(b)** DMA, **(c)** transitive `ep` inheritance below
`FUN_00046f20`. None leaves a constant in the image, so none is statically excludable for ANY
candidate cell. The cell is not used here because the rung that would need it fails on walls 0-2 --
not because the cell failed.
🛑 AND THE VERDICT IS V67-AND-LATER ONLY. On a STOCK-based build `0x3AA94` still reads this byte,
and writing it would flip `FUN_0003aa2c`'s r24/r26 gain arm onto cals `0xC6446`/`0xC6444`. Do not
carry this clearance back to a stock base.

★ A LEVER FOR LATER, free of cave bytes: because .data initializers live in flash at a computable
offset, a build can CHOOSE a cell's boot value by editing `0x86260 + (addr - 0xFEDF11B0)`. That is
inside the main-app CRC region, so it re-CRCs like any other edit. If a future rung needs a
configured constant rather than a runtime latch, it costs **0 cave bytes**.

THE NEW RUNG -- ENCODING, AND WHY IT IS 16 BYTES
-------------------------------------------------
`gp-0x6ac0` is a HALFWORD, read `ld.hu` at all 26 firmware read sites (byte-verified; zero `ld.h`,
zero `ld.b`), so it is UNSIGNED and no sign trap exists. 400 = 0x190 does not fit Format-II's
signed 5-bit `cmp` immediate, so the compare is done by subtracting the breakpoint with `movea`
(which sign-extends its imm16) and testing the sign:

    ld.hu -0x6ac0[gp],r6      e4374195     r6 = zero_extend(cell)          in [0, 65535]
    movea -0x190,r6,r6        263670fe     r6 = r6 - 400                   in [-400, 65135]
    cmp   r0,r6               e031         S = (r6 < 0), OV = 0 (no overflow is reachable)
    blt   +6                  b605         taken iff S^OV, i.e. iff cell < 400 -> skip
    movea 0x10,r7,r7          273e1000     bit4 = (cell >= 400)

The wire model checks that EXHAUSTIVELY over all 65,536 reachable cell values, not on a sample.

ENCODER PROVENANCE -- every emitted instruction pinned to a real instance
--------------------------------------------------------------------------
    ld.hu -0x6ac0[gp],r6   e4374195   *** BYTE-IDENTICAL at 0x45780, 0x4E6BA, 0x7CCCA, 0x7CE26 ***
    cmp   r0,r6            e031       BYTE-IDENTICAL at 398 sites, and FLOWN: it is V57's own
                                      cave rung at 0xC4B3C.
    blt   +6               b605       BYTE-IDENTICAL @0x1C006 (V65's pin) + 29 more
    movea 0x10,r7,r7       273e1000   FLOWN: V67's own bit4 movea at 0xC4B58
    movea -0x190,r6,r6     263670fe   ⚠ no byte-identical instance. hw1 `2636` -- opcode AND both
                                      register fields -- is byte-identical to 7 real instructions
                                      (0x1B114, 0x1B158, 0x4A712, 0x4A756, 0x5AE26, 0x60C56,
                                      0x85D8A); only the 16-bit IMMEDIATE is ours, which is data,
                                      not an encoding field. The reg1==reg2 "movea as add-immediate"
                                      shape is flown on seven builds (`movea 0xBB,r7,r7`), and the
                                      NEGATIVE-imm16 sign-extension it relies on is proven by the
                                      hook's own displaced instruction, `movea -0x1518,gp,r6`,
                                      which this very cave re-executes.
    movea 0x88,r0,r7       203e8800   hw1 `203e` byte-identical to `movea 0x80,r0,r7` at 0x1ED14 /
                                      0x51568 / 0x63726 (all real) and flown since V54; immediate
                                      differs only.
    ld.bu -0x6806[gp],r6   8437fb97   BYTE-IDENTICAL @0x2A8C0; flown V66/V67
    ld.bu -0x671d[gp],r6   a437e398   BYTE-IDENTICAL @0x3AB98 -- r24's own priority-chain read
    cmp   0x1,r6           6132       BYTE-IDENTICAL @0x14D46
    ld.bu -0x1514[gp],r6 / andi 0x7,r6,r6 / or r7,r6 / st.b r6,-0x1514[gp]   flashed since V31P

GATES
-----
GATE 1 (RAM ownership): **VACUOUS, and asserted as a MEASUREMENT.** No RAM cell is claimed. The
    cave's only store is the existing payload byte; the emitted listing is scanned and must contain
    EXACTLY ONE store. Every probed cell is asserted to be READ by the cave and WRITTEN nowhere.
    `gp-0x6ac0`'s own census (26 readers / 4 writers, all `ld.hu`/`st.h`, one extended-form hit that
    is a 32-bit alias of an already-counted store) is re-derived from raw bytes by TWO decoders.
GATE 2 (closed-loop stability): **NOT ENGAGED.** V68 changes no control path. The control-path
    assertions below are the proof of that, not a summary of it: the CAL block is asserted
    byte-identical to V67's, and the only permitted differences image-wide are the cave and the CRCs.
    V67's own GATE 2 argument carries over unchanged and is not restated here.
    *** Still CODE in the CAN-330 TX path -- which this session traced to **100 Hz** (task 5,
    `c % 10 == 4`), NOT the 1 kHz V67's docstring claims. That is why base/hook/extent are reused
    and not moved, and it is also why no probe on this hook can see above ~50 Hz.

⚠ ONE RESIDUAL ON THE NEW BIT, stated because it is real: the cave samples `gp-0x6ac0` at the TX
hook, while the LERP reads it inside `FUN_0003aa2c`. They are different points in the schedule, so
the probe's sample can be one tick stale relative to the gain evaluation. Immaterial for a
DISTRIBUTION question ("which side of 400 does the car live on"), and it is the same residual class
V67 recorded for the state mask. It would matter for a per-tick correlation; do not use it that way.

CAVE DISCIPLINE
---------------
Same base 0xC4B34, same hook 0x55C0E, same 68-byte proven extent as V55/V57/V58/V59/V64/V65/V66/V67
-- all EIGHT flew clean. Read-only; r6/r7 only. **64 of 68 bytes used, 4 spare.**

BASE = V67. Every V67 invariant is re-asserted on the output with ZERO exceptions on the control
path, and the exception set is machine-checked to be exactly {the cave span, the two CRC trailers}.

Decoder: rlog-tools/decode_v68_probe.py
"""
import hashlib
import itertools
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v54_tva as V54                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v59_tva as V59                # noqa: E402
import build_v62_tva as V62                # noqa: E402
import build_v63_tva as V63                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (census helper)
import build_v65_tva as V65                # noqa: E402  (COND_BLT and its pin)
import build_v66_tva as V66                # noqa: E402  (gain_B surface)
import build_v67_tva as V67                # noqa: E402  (direct base -- control path comes from here)
import scan_gp_accesses as SCAN            # noqa: E402  (the INDEPENDENT second decoder)
import v66_v67_explained as EX             # noqa: E402  (the arithmetic the new bit indexes)

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402
from build_vfourframe_tva import GP, R0, R6, R7                                  # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged since V55
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN

# =======================================================================================================
# V67's control path -- CARRIED, NOT RE-DERIVED. Every one of these is asserted on the output.
# =======================================================================================================
REPOINT_ADDR = V67.REPOINT_ADDR                # 0x3AA94
REPOINT_BYTE = V67.REPOINT_BYTE                # 0x3AA96 -- the one byte V67 moved
REPOINT_TO = V67.REPOINT_TO                    # ld.bu -0x6806[gp],r15
ARM_ADDR = V67.ARM_ADDR                        # 0xC6446
ARM_VALUE = V67.ARM_NEW                        # 5244
R26_ARM_ADDR = V67.R26_ARM_ADDR                # 0xC6444, stays stock 512
R26_AVG_CAL, R26_AVG_LEN = V67.R26_AVG_CAL, V67.R26_AVG_LEN
GATE_DISP = V67.GATE_DISP                      # 0x6806
DEAD_DISP = V67.DEAD_DISP                      # 0x683c -- UNREFERENCED after the repoint

# ★★ THE BOOT-INIT MAP, found this session and pinned here so it cannot rot. These two loops write
# RAM through `sst.w` with a COMPUTED `ep`, so they are invisible to disp16 scans, disp23 scans,
# `search_instructions` AND `get_xrefs_to` -- the exact blind spot that let gp-0x1500 pass two
# static methods and still fail on-car. Any future GATE 1 audit MUST clear this class.
GP_ABS = 0xFEDF8000                            # derived at 0x140C0 `ori 0x8000,r0,r1`, not assumed
BSS_CLEAR = (0x146C0, 0xFEDEC000)              # `mov 0xfedec000,ep` -> zeroes ..0xFEDFFFFF
DATA_SRC = (0x1475C, 0x00086260)               # `mov 0x86260,r14`   -- flash source
DATA_DST = (0x14766, 0xFEDF11B0)               # `mov 0xfedf11b0,ep` -- RAM destination
DATA_END = (0x14786, 0x0008AB18)               # `mov 0x8ab18,r10`   -- flash source end
# => gp-0x683c is .data, and its BOOT VALUE is this flash byte. Asserted == 0 on every build.
DEAD_INIT_FLASH = DATA_SRC[1] + (GP_ABS - DEAD_DISP - DATA_DST[1])       # 0x86260 + 0x614 = 0x86874
MASK_DISP = V67.MASK_DISP                      # 0x671d
ARM3_DISP = V67.ARM3_DISP                      # 0x671a -- watched, but no longer probed

# The three `sar` sites the brief names explicitly, all STOCK (V66's revert, kept by V67 and V68).
SAR_SITES_STOCK = ((0x3AB70, 0x32AA), (0x3AB76, 0x32AA), (0x3AC20, 0x42AA))
# The four mode-10 gain_B records the new bit's breakpoint is read out of.
GAIN_B_RECORDS = V66.GAIN_B_RECORDS            # 0xD2A74 / 0xD2AB0 / 0xD2AEC / 0xD2B28
# The three sibling arms, all stock.
ARM_671D_ADDR, ARM_671D_STOCK = 0xC6442, EX.ARM_671D      # 1024
ARM_671A_ADDR, ARM_671A_STOCK = 0xC6440, EX.ARM_671A      # 2048
D2000_BLOCK = (0xD2000, 0xD2010)               # the slew-blend block V60 falsified; must not move

# =======================================================================================================
# THE ONE CHANGE -- the probe. bit4 is repointed; bit3 becomes the build-class marker.
# =======================================================================================================
BIT_LIVE = 0x80
BIT_GATE, BIT_MASK, BIT_RATE = 0x40, 0x20, 0x10
BIT_CLASS = 0x08               # bit3: CONSTANT 1 on V68. The build-class marker.
LIVE_IMM = BIT_LIVE | BIT_CLASS                            # 0x88 -- one movea, zero extra bytes

RATE_DISP = 0x6AC0             # the r24 gain LERP's INNER axis. HALFWORD, ld.hu, unsigned.
RATE_BREAKPOINT = 400          # xs[1] in every mode-10 gain_B record -- asserted from the image
RATE_FOLD = EX.RATE_FOLD       # 13001; above this the LERP key folds to 0 -- the stated asymmetry

# 🛑 RETRACTED 2026-08-03 -- KEPT ONLY AS A RECORD OF A STRUCK CLAIM, NEVER AS A PREDICTION.
# Derived from route 47's cache through `x 32768/(48*1159)`, which is EX.RATE_COUNTS_PER_DEGS / 8 --
# i.e. it rests on `bus = 8 x deg/s`, the relation CLAUDE.md records as RETRACTED. See the docstring.
R47_CHAIN_STRUCK = 32768 / (48 * 1159)         # 0.5890135 -- exactly EX.RATE_COUNTS_PER_DEGS / 8
R47_PREDICT = {"retracted": True, "n": 150327, "at_or_above_400": 0, "max": 277.4,
               "p50": 0.6, "p90": 10.6, "p99": 105.4, "p99_9": 221.3, "p99_99": 264.4}

COND_BLT = V65.COND_BLT        # 0x6, SIGNED < -- pinned to the real `blt` @0x1C006
COND_BNE = 0xA                 # Z == 0. Pinned to a real `bne +6` -- 1455 byte-identical instances.

# ⚠ gp-0x67ac IS NOT PROBED. It was the intended bit5 until 2026-08-03, when it was shown to be
# PERMANENTLY 0 on this build -- see the docstring. Kept named so the retired candidate is legible.
DROPOUT_DISP = 0x67AC          # PROVEN 0. Never probed. BYTE, 2r/1w (reader 0x3AA34, writer 0x2773A).
FSM_DISP = 0x67DF              # the detector FSM state. BYTE, 1r/1w. *** FLOWN as V64's bit4 ***
DETECT_DISP = ARM3_DISP        # 0x671a -- Honda's 1 kHz oscillation detector, BYTE (7r/1w).
# 🛑 gp-0x67ac's role table, the fact the exclusion rests on. Re-read from the image every build.
ROLE_TABLE_ADDR = 0xC4124      # tp+0x5124 -- 11 per-slot role bytes. Anchored, NOT the +0x1000 trap.
ROLE_TABLE_EXPECT = bytes((0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0))    # no slot is 6 or 7 => latch never fires

# Rung kinds. "byte_ge" = ld.bu + cmp imm5 + blt   + movea            (12 bytes)
#             "byte_eq" = ld.bu + cmp imm5 + bne   + movea            (12 bytes)  <- SAME COST
#             "hword_ge" = ld.hu + movea(-T) + cmp r0 + blt + movea   (16 bytes)  <- unused on V68
KIND_BYTE, KIND_BYTE_EQ, KIND_HWORD = "byte_ge", "byte_eq", "hword_ge"
RUNG_LEN = {KIND_BYTE: 12, KIND_BYTE_EQ: 12, KIND_HWORD: 16}
RUNG_COND = {KIND_BYTE: COND_BLT, KIND_BYTE_EQ: COND_BNE, KIND_HWORD: COND_BLT}

# (gp displacement, bit, name, kind, threshold, what it decides)
CELLS = (
    (GATE_DISP, BIT_GATE, "gate_6806", KIND_BYTE, 1,
     "*** THE GATE *** -- carried from V67; duty vs latActive and the engagement covariate"),
    (FSM_DISP, BIT_MASK, "fsm_67df", KIND_BYTE, 1,
     "*** NEW *** detector FSM LEFT NEUTRAL: |gp-0x6c2c| crossed +-T. NO reversal required"),
    (DETECT_DISP, BIT_RATE, "detect_671a", KIND_BYTE, 1,
     "*** NEW THRESHOLD *** ...and then REVERSED at least once (V67 tested >= 5)"),
)

# ---- encoder pins, all read back FROM THE IMAGE in assert_signal_sites() -----------------------------
PIN_CMP_P1_R6 = V65.PIN_CMP_P1_R6                                    # (0x14D46, 6132, 1, r6)
PIN_BLT6 = V65.PIN_BLT6                                              # (0x1C006, b605)
PIN_LDBU_6806_R6 = V66.PIN_LDBU_6806_R6                              # (0x2A8C0, 8437fb97, 0x6806, 6)
PIN_LDBU_671D_R6 = V67.PIN_LDBU_671D_R6                              # (0x3AB98, a437e398, 0x671d, 6)
PIN_LDBU_6806_R15 = V67.PIN_LDBU_6806_R15                            # the repoint, byte-identical
# ⚠ PROVENANCE OF THE TWO NEW LOADS, STATED AT ITS REAL STRENGTH. Neither `ld.bu -0x671a[gp],r6` nor
# `ld.bu -0x67ac[gp],r6` has a byte-identical instance in the STOCK image: every real reader of both
# cells targets a different destination register, so only the reg2 field is ours. What IS byte-
# identical at real sites is hw2 -- the entire displacement, including the parity bit that the
# hw1-bit-5 trap turns on. Both are asserted from the image below.
PIN_LDBU_671A_HW2 = (bytes.fromhex("e798"),
                     (0x35A06, 0x35BEA, 0x36C1E, 0x3A4A6, 0x3AA70, 0x429C4, 0x429D2))
# ★ bit5's load needs NO hedge: `ld.bu -0x67df[gp],r6` = a4372198 is BYTE-IDENTICAL to V64's own
# flown cave word at 0xC4B4C, where it was V64's bit4 and drove route 35. Lifted, not re-derived.
PIN_LDBU_67DF_FLOWN = (0xC4B4C, bytes.fromhex("a4372198"))
PIN_LDBU_67DF_HW2 = (bytes.fromhex("2198"), (0x428E6, 0x4299C))   # its reader and its sole writer
# ★ AND bit4's full word is FLOWN: V67's own cave carried `8437e798` verbatim at 0xC4B50 and drove
# routes 47 and 4a. Asserted against the V67 SOURCE image, not against stock (where it cannot exist).
PIN_LDBU_671A_FLOWN = (0xC4B50, bytes.fromhex("8437e798"))
PIN_BNE6 = (0x14CB2, bytes.fromhex("ba05"))                          # `bne +6`, 1455 exact instances
# `cmp r0,r6` -- kept as a pin even though no rung uses it now; V57's flown cave rung.
PIN_LDHU_6AC0_R6 = (0x45780, bytes.fromhex("e4374195"), RATE_DISP, 6)
PIN_LDHU_6AC0_TWINS = (0x45780, 0x4E6BA, 0x7CCCA, 0x7CE26)
# `cmp r0,r6`. Byte-identical at 398 sites; the pin chosen is the FLOWN one -- V57's own cave rung.
PIN_CMP_R0_R6 = (0xC4B3C, bytes.fromhex("e031"))
PIN_CMP_R0_R6_ROM = 0x1507C                                          # a real, non-cave instance
# `movea 0x80,r0,r7` -- hw1 donor for the 0x88 liveness immediate.
PIN_MOVEA_R0_R7 = (0x1ED14, bytes.fromhex("203e8000"))
# ⚠ WEAKER PROVENANCE, declared rather than buried: `movea -0x190,r6,r6` has no byte-identical
# instance image-wide. hw1 (opcode + BOTH register fields) is byte-identical to these seven.
PIN_MOVEA_R6_R6_HW1 = (bytes.fromhex("2636"),
                       (0x1B114, 0x1B158, 0x4A712, 0x4A756, 0x5AE26, 0x60C56, 0x85D8A))
WEAK_PINS = ("movea -0x190,r6,r6",)

TAG = "LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-fsm67df-detector671a-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V68-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v68_plain_image.bin"))
V67_BIN = str(plain_image_path("_v67_plain_image.bin"))
DECODER = os.path.join(os.path.dirname(HERE), "rlog-tools", "decode_v68_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def decode_fmt2(halfword):
    """V850 Format-II split: imm5 = bits[4:0] (SIGNED), opcode = bits[10:5], reg2 = bits[15:11]."""
    imm = halfword & 0x1F
    return {"imm5": imm - 32 if imm & 0x10 else imm,
            "opcode": (halfword >> 5) & 0x3F,
            "reg2": (halfword >> 11) & 0x1F}


def decode_load(raw):
    """Decode an emitted 4-byte load through the INDEPENDENT scan_gp_accesses decoder.

    🛑 The hw1-bit-5 guard. `ld.bu` puts the displacement's bit 0 in the OPCODE FIELD (0x3C/0x3D),
    so a parity slip silently addresses the NEIGHBOURING cell with every other field still perfect.
    Returns (mnemonic, gp offset as a POSITIVE kit-convention number, reg1, reg2).
    """
    hw1, hw2 = struct.unpack("<HH", raw)
    d = SCAN.decode_op((hw1 >> 5) & 0x3F, hw1, hw2)
    assert d is not None, f"{raw.hex()} is not a Format-VII load/store at all"
    mnem, disp_u16, _is_store = d
    return mnem, (0x10000 - disp_u16) & 0xFFFF, hw1 & 0x1F, (hw1 >> 11) & 0x1F


def _emit_load(disp, kind):
    """The one place a cell's load is encoded, so the wire model and the cave cannot diverge."""
    return FF.ldhu(disp, R6) if kind == KIND_HWORD else V55.ldbu_any(-disp, R6)


# =======================================================================================================
# Encoders
# =======================================================================================================

def _self_check_encoders():
    """Reproduce a real instance, or an already-self-checked ancestor encoder. No exceptions."""
    V67._self_check_encoders()          # inherits the whole chain back to FOURFRAME
    assert GP == 4, "GP is not r4; every real gp-relative instance in this image carries reg1 = r4"

    # ---- ALL THREE rungs are BYTE rungs on this revision -------------------------------------------
    for disp, _bit, name, kind, lvl, _why in CELLS:
        if kind == KIND_HWORD:
            continue
        raw = V55.ldbu_any(-disp, R6)
        mnem, got, reg1, reg2 = decode_load(raw)
        assert (mnem, got, reg1, reg2) == ("ld.bu", disp, GP, R6), \
            f"{name}: emitted load decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2} -- the " \
            "hw1-bit-5 trap, and the neighbouring cell is a real live cell"
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        assert op == (0x3C | (((0x10000 - disp) & 0xFFFF) & 1)), \
            f"{name}: opcode field 0x{op:02X} does not match the displacement parity"
        assert struct.unpack_from("<H", raw, 2)[0] & 1 == 1, f"{name}: ld.bu hw2 LSB must be SET"
        assert raw != FF.stb(R6, -disp, GP), f"{name}: the load collapsed onto an st.b"
        assert raw != FF.ldhu(disp, R6), f"{name}: ld.bu collapsed onto ld.hu -- it would straddle"
        assert V55.cmp_imm5(lvl, R6) == PIN_CMP_P1_R6[1], f"{name}: `cmp 0x1,r6` is not the pin"

    # ---- ★★ THE EQUALITY RUNG. `== 1` is NOT `>= 1`, and the difference is the whole point. --------
    # FUN_0003aa2c skips the r24/r26 aggregate add iff gp-0x67ac == 1 EXACTLY (0x3aa34 ld.bu ->
    # 0x3aa3c cmp 0x1 -> 0x3aa42 cmovh 0x0,r8,r11 -> branch on r11 == 1); a value >= 2 does NOT skip.
    # A `>= 1` rung would report a lane dropout that is not happening. The equality form costs the
    # SAME 12 bytes -- only the branch CONDITION changes, blt (0x6) -> bne (0xA).
    eq_br = FF.bcond(COND_BNE, +6)
    assert eq_br == PIN_BNE6[1], f"`bne +6` encodes as {eq_br.hex()}, not the real {PIN_BNE6[1].hex()}"
    assert COND_BNE == 0xA and struct.unpack("<H", eq_br)[0] & 0xF == COND_BNE, "COND_BNE drifted"
    assert eq_br != FF.bcond(COND_BLT, +6), "the equality branch collapsed onto the `>=` branch"
    assert RUNG_LEN[KIND_BYTE_EQ] == RUNG_LEN[KIND_BYTE] == 12, \
        "the equality rung is no longer the same 12 bytes as the >= rung"
    assert RUNG_COND[KIND_BYTE_EQ] == COND_BNE and RUNG_COND[KIND_BYTE] == COND_BLT, \
        "a rung kind is wired to the wrong branch condition -- == and >= would swap silently"
    assert len(eq_br) == len(FF.bcond(COND_BLT, +6)) == 2, "a Bcond is not 2 bytes"

    # ---- ★ THE TWO NEW LOADS, and the PARITY TRAP that differs between them ----------------------
    # 🛑 gp-0x671a's disp16 is 0x98E6 (EVEN -> opcode field 0x3C, hw1 `8437`) but gp-0x67df's is
    # 0x9821 (ODD -> opcode field 0x3D, hw1 `a437`). `ld.bu` carries displacement bit 0 in the
    # OPCODE FIELD, so a scan or an encoder that assumes one parity silently addresses the
    # NEIGHBOURING cell with every other field still perfect. Both parities are asserted here.
    for disp, (hw2, sites), want_hw1, what in (
            (DETECT_DISP, PIN_LDBU_671A_HW2, "8437", "gp-0x671a (bit4), EVEN disp"),
            (FSM_DISP, PIN_LDBU_67DF_HW2, "a437", "gp-0x67df (bit5), ODD disp")):
        raw = V55.ldbu_any(-disp, R6)
        assert raw[2:] == hw2, \
            f"{what}: the emitted displacement halfword {raw[2:].hex()} is not the one that appears " \
            f"at the cell's own real accesses ({hw2.hex()}) -- WRONG CELL"
        assert raw[:2] == bytes.fromhex(want_hw1), \
            f"{what}: hw1 is {raw[:2].hex()}, not `{want_hw1}` -- the opcode field does not match " \
            "the displacement parity, so this load addresses the NEIGHBOURING cell"
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        assert op == (0x3C | (((0x10000 - disp) & 0xFFFF) & 1)), f"{what}: opcode/parity mismatch"
        assert len(sites) >= 2, f"{what}: fewer than two real hw2 donors"
    # ★ and bit5's FULL WORD is byte-identical to V64's flown cave rung -- no hedge needed.
    assert V55.ldbu_any(-FSM_DISP, R6) == PIN_LDBU_67DF_FLOWN[1], \
        f"the encoder builds {V55.ldbu_any(-FSM_DISP, R6).hex()} for `ld.bu -0x67df[gp],r6`, not " \
        f"V64's flown {PIN_LDBU_67DF_FLOWN[1].hex()}"

    # ---- the HWORD encoder is retained and self-checked even though no rung uses it now ------------
    load = FF.ldhu(RATE_DISP, R6)
    assert load == PIN_LDHU_6AC0_R6[1], \
        f"the encoder builds {load.hex()} for `ld.hu -0x6ac0[gp],r6`, not the real instance " \
        f"{PIN_LDHU_6AC0_R6[1].hex()} @0x{PIN_LDHU_6AC0_R6[0]:05X}"
    mnem, got, reg1, reg2 = decode_load(load)
    assert (mnem, got, reg1, reg2) == ("ld.hu", RATE_DISP, GP, R6), \
        f"the new rung's load decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
    assert struct.unpack_from("<H", load, 2)[0] & 1 == 1, \
        "ld.hu hw2 LSB must be SET -- a clear LSB is the ld.h (SIGNED) form and would invert the test"
    assert load != V55.ldh(RATE_DISP, R6), \
        "the emitted ld.hu collapsed onto the SIGNED ld.h -- negative cells would then pass `>= 400`"
    assert load != V55.ldbu_any(-RATE_DISP, R6), "ld.hu collapsed onto ld.bu -- it would read 8 bits"
    assert load != FF.sth(R6, -RATE_DISP, GP), "the emitted load collapsed onto an st.h"

    sub = FF.movea((-RATE_BREAKPOINT) & 0xFFFF, R6, R6)
    assert sub == bytes.fromhex("263670fe"), f"`movea -0x190,r6,r6` encodes as {sub.hex()}"
    assert sub[:2] == PIN_MOVEA_R6_R6_HW1[0], \
        f"the movea hw1 {sub[:2].hex()} is not the real {PIN_MOVEA_R6_R6_HW1[0].hex()}"
    hw1 = struct.unpack("<H", sub[:2])[0]
    assert ((hw1 >> 5) & 0x3F, hw1 & 0x1F, hw1 >> 11) == (0x31, R6, R6), \
        "the movea's opcode/reg1/reg2 fields are not (0x31, r6, r6)"
    assert struct.unpack("<H", sub[2:])[0] == (0x10000 - RATE_BREAKPOINT), \
        "the movea's imm16 is not -400"
    # 🛑 sign-extension is the whole rung. Pinned to the hook's OWN displaced instruction, which is a
    # real `movea` with a NEGATIVE imm16 and which this cave re-executes verbatim.
    assert HOOK_STOCK == FF.movea((-0x1518) & 0xFFFF, GP, R6), \
        "the displaced hook instruction is not `movea -0x1518,gp,r6` -- the sign-extension pin is gone"
    assert struct.unpack("<H", HOOK_STOCK[2:])[0] & 0x8000, \
        "the hook's movea imm16 is not negative -- it no longer demonstrates sign-extension"
    # ...and the reg1 == reg2 "movea as add-immediate" SHAPE is FLOWN, not merely present in ROM:
    # V67's own cave (on the car) carries `movea 0x40,r7,r7`, the same shape with r7 for r6.
    assert FF.movea(BIT_GATE, R7, R7) in V67.CAVE_BYTES, \
        "the reg1==reg2 movea shape is not byte-present in V67's FLOWN cave"
    assert struct.unpack("<H", FF.movea(BIT_GATE, R7, R7)[:2])[0] & 0x1F == R7, \
        "the flown reg1==reg2 precedent does not actually carry reg1 == reg2"
    assert (struct.unpack("<H", sub[:2])[0] & 0x1F) == (struct.unpack("<H", sub[:2])[0] >> 11), \
        "our movea's reg1 and reg2 fields are not equal -- it is not the flown shape"
    # ⚠ The ONLY genuinely new thing is the register NUMBER (r6 instead of r7). reg2 == r6 in a
    # movea is itself real and flown -- it is the hook's own displaced instruction.
    assert (struct.unpack("<H", HOOK_STOCK[:2])[0] >> 11) == R6, \
        "the hook's movea does not target r6 -- the reg2 = r6 leg of the provenance is gone"

    cmp_rr = V54.cmp_rr(R0, R6)
    assert cmp_rr == PIN_CMP_R0_R6[1], f"`cmp r0,r6` encodes as {cmp_rr.hex()}, not e031"
    f = decode_fmt2(struct.unpack("<H", cmp_rr)[0])
    assert (f["opcode"], f["reg2"]) == (0x0F, R6) and struct.unpack("<H", cmp_rr)[0] & 0x1F == R0, \
        f"`cmp r0,r6` decodes as {f} -- not Format-I cmp reg1=r0 reg2=r6"
    assert V54.cmp_rr(R0, R6) != V54.cmp_rr(R0, R7), "cmp_rr ignores reg2"
    assert V54.cmp_rr(R0, R6) != V54.cmp_rr(R7, R6), "cmp_rr ignores reg1"
    assert cmp_rr != V55.cmp_imm5(0, R6), "the reg-reg cmp collapsed onto the imm5 form"

    assert FF.bcond(COND_BLT, +6) == PIN_BLT6[1], \
        f"`blt +6` fails the real `blt` @0x{PIN_BLT6[0]:05X}"
    assert COND_BLT == 0x6, "COND_BLT drifted"
    assert struct.unpack("<H", FF.bcond(COND_BLT, +6))[0] & 0xF == COND_BLT

    # ---- the bit-set moveas ----------------------------------------------------------------------
    for _d, bit, name, _k, _l, _w in CELLS:
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"{name}: movea 0x{bit:x},r7,r7 bad"
    live = FF.movea(LIVE_IMM, R0, R7)
    assert live.hex() == "203e8800", f"`movea 0x88,r0,r7` encodes as {live.hex()}"
    assert live[:2] == PIN_MOVEA_R0_R7[1][:2], \
        "the liveness movea's hw1 differs from the real `movea 0x80,r0,r7` -- more than the immediate"
    assert live != FF.movea(BIT_LIVE, R0, R7), "the class marker did not change the immediate"
    assert FF.movea(LIVE_IMM, R0, R7)[:2] != FF.movea(LIVE_IMM, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 is ADDED to itself, not loaded"

    # ---- the bit map -----------------------------------------------------------------------------
    bits = (BIT_LIVE, BIT_CLASS) + tuple(b for _, b, _, _, _, _ in CELLS)
    assert len(set(bits)) == len(bits) and all(b & (b - 1) == 0 for b in bits), \
        "probe bits are not distinct single bits"
    assert sum(bits) == 0xF8, "probe bits must span exactly 7:3 with NO bit unassigned on V68"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert LIVE_IMM == BIT_LIVE | BIT_CLASS, "the liveness immediate does not carry the class marker"
    assert [b for _, b, _, _, _, _ in CELLS] == \
        sorted((b for _, b, _, _, _, _ in CELLS), reverse=True), \
        "the cell bits are not in descending bit order"
    assert {c[0] for c in CELLS} == {GATE_DISP, FSM_DISP, DETECT_DISP}, "the probed cell set moved"
    assert DROPOUT_DISP not in {c[0] for c in CELLS}, \
        "gp-0x67ac is probed again -- it is PROVEN 0 on this build (see the docstring). Probing a " \
        "proven zero repeats the exact error that wasted V68's original bit4."
    assert not any(c[3] == KIND_BYTE_EQ for c in CELLS), \
        "an equality rung is present -- the only candidate for one was gp-0x67ac, which is not probed"

    # ★★ WHY gp-0x671a IS PROBED AGAIN, AND WHY THE ASSERT THAT FORBADE IT IS GONE.
    # An earlier revision of this file asserted `ARM3_DISP not in CELLS` with the message "gp-0x671a is
    # still probed -- V68's whole point is that bit4 was a wasted rung". That assert is REMOVED, and
    # this is the rationale replacing it rather than a silent deletion:
    #   1. THE NULL WAS AT A DIFFERENT THRESHOLD. Route 47 (and route 4a) read gp-0x671a 0.000% -- but
    #      V67's rung tested `>= 5`, the CEIL (cal 0xC64FA = 5). This rung tests `>= 1`, the LOWEST
    #      rung of the same counter. A null at 5 does not imply a null at 1; they are different
    #      questions about a 0..5 counter, and only the second one asks "did the detector see
    #      ANYTHING".
    #   2. THE DETECTOR IS THE KIT'S ONLY ABOVE-50-Hz INSTRUMENT. gp-0x6c2c's cascade is a BAND-PASS
    #      peaking near 61 Hz (1 Hz 0.05x, 45 Hz 1.54x, 61 Hz 1.61x, 100 Hz 1.43x, relative to
    #      21.09 Hz), so the trip amplitude FALLS above 50 Hz: 21.3 Hz needs 1683 counts, 45 Hz 1104,
    #      60 Hz 1056, 100 Hz 1186. Honda's own 1 kHz detector is MORE sensitive where both CAN
    #      (Nyquist 50.00) and the comma IMU (50.51) are blind. This bit is the only way to see there.
    #   3. IT COSTS NOTHING AND RISKS NOTHING. 12 bytes, read-only, no new store, GATE 1 stays vacuous.
    assert DETECT_DISP == ARM3_DISP == 0x671A, "the detector cell moved"
    assert [c[4] for c in CELLS if c[0] == DETECT_DISP] == [1], \
        "bit4's threshold is not 1 -- the whole reason for re-probing gp-0x671a is that V67 tested 5"
    assert V67.CELLS and any(c[0] == DETECT_DISP and c[3] != 1 for c in V67.CELLS), \
        "V67 no longer tests gp-0x671a at a threshold other than 1 -- the premise above is stale"


# =======================================================================================================
# The cave -- 64 bytes of the 68-byte proven extent
# =======================================================================================================

def build_cave():
    """pack_dropout_detector_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x88,r0,r7       ; r7 = 0x88   bit7 LIVENESS + bit3 BUILD-CLASS MARKER
        ld.bu -0x6806[gp],r6   ; *** THE GATE *** -- carried from V67
        cmp   0x1,r6           ; ld.bu zero-extends => SIGNED < 1 is exactly == 0
        blt   +6
        movea 0x40,r7,r7       ; bit6 = gp-0x6806 != 0
      g_gate:
        ld.bu -0x67ac[gp],r6   ; *** NEW *** the r24/r26 LANE DROPOUT flag
        cmp   0x1,r6
        bne   +6               ; 🛑 EQUALITY, not >=. Skip unless the byte is EXACTLY 1.
        movea 0x20,r7,r7       ; bit5 = (gp-0x67ac == 1)
      g_dropout:
        ld.bu -0x671a[gp],r6   ; *** NEW THRESHOLD *** Honda's oscillation detector
        cmp   0x1,r6
        blt   +6
        movea 0x10,r7,r7       ; bit4 = gp-0x671a >= 1   (V67 tested >= 5)
      g_detect:
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(LIVE_IMM, R0, R7), "movea 0x88,r0,r7    ; bit7 LIVENESS + bit3 CLASS MARKER")

    rungs = []
    for disp, bit, name, kind, lvl, _why in CELLS:
        load_idx = len(listing)
        emit(_emit_load(disp, kind),
             f"ld.{'hu' if kind == KIND_HWORD else 'bu'} -0x{disp:04x}[gp],r6 ; {name}")
        if kind == KIND_HWORD:
            emit(FF.movea((-lvl) & 0xFFFF, R6, R6),
                 f"movea -0x{lvl:x},r6,r6  ; r6 = value - {lvl}  (movea SIGN-EXTENDS imm16)")
            emit(V54.cmp_rr(R0, R6), "cmp r0,r6           ; S = (r6 < 0), OV = 0")
        else:
            emit(V55.cmp_imm5(lvl, R6), f"cmp 0x{lvl:x},r6          ; zero-extended byte")
        br_idx = len(listing)
        cond = RUNG_COND[kind]
        op = "==" if kind == KIND_BYTE_EQ else ">="
        emit(FF.bcond(cond, +6),
             f"{'bne' if kind == KIND_BYTE_EQ else 'blt'} +6              ; skip -> {name}")
        emit(FF.movea(bit, R7, R7),
             f"movea 0x{bit:x},r7,r7   ; bit{bit.bit_length() - 1} = gp-0x{disp:04x} {op} {lvl}")
        rungs.append((load_idx, br_idx, CAVE_BASE + len(body), name, disp, bit, kind, lvl))

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands exactly on its label. Located BY POSITION, not by content --
    # the cave emits near-identical Bconds, so a content lookup is ambiguous by construction.
    assert [r[1] for r in rungs] == [3, 7, 11], f"rung branch indices drifted: {[r[1] for r in rungs]}"
    for load_idx, br_idx, label, name, disp, _bit, kind, lvl in rungs:
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"
        # 🛑 THE == / >= TRAP. The two rung kinds are byte-for-byte identical except for this nibble.
        # A blt where a bne belongs turns "the lane dropped out" into "the flag is non-zero" -- a
        # SUPERSET of the real condition -- and nothing else in the image would look wrong.
        assert struct.unpack("<H", raw)[0] & 0xF == RUNG_COND[kind], \
            f"{name}: branch condition is 0x{struct.unpack('<H', raw)[0] & 0xF:X}, not " \
            f"0x{RUNG_COND[kind]:X} for a {kind} rung -- == and >= have been swapped"
        assert listing[load_idx][1] == _emit_load(disp, kind), f"{name}: wrong cell loaded"
        n_mid = br_idx - load_idx - 1
        assert n_mid == (2 if kind == KIND_HWORD else 1), \
            f"{name}: {n_mid} instruction(s) between the load and the branch, expected " \
            f"{2 if kind == KIND_HWORD else 1} for a {kind} rung"
        if kind == KIND_HWORD:
            assert listing[load_idx + 1][1] == FF.movea((-lvl) & 0xFFFF, R6, R6), \
                f"{name}: the threshold subtract is not `movea -0x{lvl:x},r6,r6`"
            assert listing[load_idx + 2][1] == V54.cmp_rr(R0, R6), f"{name}: the compare is not `cmp r0,r6`"
        else:
            assert listing[load_idx + 1][1] == V55.cmp_imm5(lvl, R6), f"{name}: cmp is not `0x{lvl:x},r6`"
    # ...and NO rung is an equality rung on this revision. The only candidate for one was gp-0x67ac,
    # which is provably 0 on this build and is therefore not probed. KIND_BYTE_EQ stays defined and
    # self-checked so the capability is proven and costed, but shipping it now would be a rung spent
    # on a known constant -- exactly the error V68's original bit4 made.
    eq_rungs = [r[3] for r in rungs if r[6] == KIND_BYTE_EQ]
    assert eq_rungs == [], f"the equality rungs are {eq_rungs}; none should be present"
    assert all(r[6] == KIND_BYTE for r in rungs), "every rung on this revision is a plain byte rung"

    # ---- GATE 2b: r6/r7 LIVENESS. Only the rung's own load and its threshold subtract may write r6;
    # everything else in the rung region writes r7. Nothing else may be touched at all.
    load_addrs = {listing[r[0]][0] for r in rungs}
    sub_addrs = {listing[r[0] + 1][0] for r in rungs if r[6] == KIND_HWORD}
    for idx in range(1, rungs[-1][1] + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        op = (hw >> 5) & 0x3F
        if op in (0x13, 0x0F):                                # cmp imm5,reg2 / cmp reg1,reg2 -- flags only
            continue
        if addr in load_addrs or addr in sub_addrs:
            assert (hw >> 11) == R6, f"listing[{idx}] '{text}' writes r{hw >> 11}, not r6"
            continue
        assert (hw >> 11) == R7, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{R7}"
    for disp, _bit, name, kind, _l, _w in CELLS:
        assert sum(1 for _, r, _ in listing if r == _emit_load(disp, kind)) == 1, \
            f"{name}: gp-0x{disp:04x} is loaded more than once"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store, the payload byte.
    store_ops = {0x3A: "st.b", 0x3B: "st.h/st.w"}
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in store_ops]
    assert store_idx == [16], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[16][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
        "the sole store is not the payload byte"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry ---------------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    want = 24 + sum(RUNG_LEN[c[3]] for c in CELLS)
    assert len(body) == want == 60, f"the cave is {len(body)}B; the budget says {want}B"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V68 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B) -- STOP, " \
        "do not grow it: caves are this kit's only bricking class"
    spare = len(V55.CAVE_BYTES) - len(body)
    assert spare == 8, f"{spare} spare bytes, expected 8"
    need = sticky_rung_budget()
    assert spare < need["minimum"], \
        f"{spare} spare bytes now, and the cheapest HF rung needs {need['minimum']} -- the budget " \
        "argument in this build's docstring no longer holds. RE-EXAMINE the sticky rung."
    build_cave.sticky_budget = need
    return bytes(body), listing


def sticky_rung_budget():
    """🛑 The sticky/HF rung's byte cost, SUMMED FROM THE REAL ENCODERS -- not asserted in prose.

    The brief asked for a latching rung on `gp-0x4f62` to break the ~50 Hz aliasing barrier. This
    function is why it is not here: the arithmetic, executable, so a future session can re-run it
    instead of trusting a paragraph. Fixed overhead is 24 bytes and bit6 + bit5 cost 12 each, so
    exactly 20 bytes are free after the two rungs that must stay.

    ⚠ `subr r0,r6` (the negate, Format I) has NO encoder in this kit and is counted at its
    architectural width of 2 bytes rather than built -- introducing an opcode into a cave for a
    budget calculation would be exactly the risk this function exists to avoid.
    """
    negate_bytes = 2                       # `subr r0,r6`, Format I -- counted, deliberately NOT built
    threshold = 0x400                      # any value needing more than a signed imm5
    parts = [("ld.h  -0x4f62[gp],r6  (SIGNED halfword -- byte-verified at 6 read sites)",
              len(V55.ldh(0x4F62, R6))),
             ("cmp   r0,r6           (sign test for the abs)", len(V54.cmp_rr(R0, R6))),
             ("bge   +4              (skip the negate)", len(FF.bcond(0xE, +4))),
             ("subr  r0,r6           (the negate -- counted, not encoded)", negate_bytes),
             (f"movea -0x{threshold:x},r6,r6   (subtract the threshold)",
              len(FF.movea((-threshold) & 0xFFFF, R6, R6))),
             ("cmp   r0,r6", len(V54.cmp_rr(R0, R6))),
             ("blt   +6", len(FF.bcond(COND_BLT, +6))),
             ("movea 0x10,r7,r7      (set the bit)", len(FF.movea(BIT_RATE, R7, R7)))]
    minimum = sum(n for _, n in parts)
    # ...and the LATCH machinery on top, if a free RAM byte were ever proven safe.
    latch = [("st.b  r7,-LATCH[gp]   (set the latch)", len(FF.stb(R7, -0x683C, GP))),
             ("ld.bu -LATCH[gp],r6   (read it back)", len(V55.ldbu_any(-0x683C, R6))),
             ("cmp   0x1,r6", len(V55.cmp_imm5(1, R6))),
             ("blt   +6", len(FF.bcond(COND_BLT, +6))),
             ("movea 0x10,r7,r7", len(FF.movea(BIT_RATE, R7, R7))),
             ("st.b  r0,-LATCH[gp]   (clear it)", len(FF.stb(R0, -0x683C, GP)))]
    free = len(V55.CAVE_BYTES) - 24 - 2 * RUNG_LEN[KIND_BYTE]
    assert (minimum, free) == (22, 20), \
        f"the sticky-rung budget moved: {minimum} needed vs {free} free (was 22 vs 20)"
    return {"parts": parts, "minimum": minimum, "latch": latch,
            "with_latch": minimum + sum(n for _, n in latch), "free_after_bit6_bit5": free}


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =======================================================================================================

def rung_predicate(kind, lvl):
    """The EXACT predicate each rung kind computes, in one place, so no caller can guess wrong."""
    if kind == KIND_BYTE_EQ:
        return lambda v: v == lvl               # cmp imm5 ; bne  -> set iff EXACTLY equal
    return lambda v: v >= lvl                   # cmp/sub  ; blt  -> set iff >=


def wire_byte4(values, status_bits=0x7):
    """Exactly what the cave writes, given each cell's RAM value. `values` is keyed by displacement."""
    b = LIVE_IMM                                # bit7 liveness + bit3 class marker
    for disp, bit, _name, kind, lvl, _why in CELLS:
        if kind == KIND_HWORD:
            v = values[disp] & 0xFFFF           # ld.hu ZERO-EXTENDS a halfword -> r6 in [0,65535]
            hit = (v - lvl) >= 0                # movea then SIGNED blt, in 32 bits
        elif kind == KIND_BYTE_EQ:
            v = values[disp] & 0xFF             # ld.bu ZERO-EXTENDS a byte -> r6 in [0,255]
            hit = (v == lvl)                    # `cmp 0x1,r6` sets Z iff r6 == 1; `bne` skips unless
        else:
            v = values[disp] & 0xFF
            hit = (v >= lvl)                    # signed and unsigned agree on a zero-extended byte
        assert hit == rung_predicate(kind, lvl)(v), "wire model and rung_predicate disagree"
        if hit:
            b |= bit
    return b | (status_bits & PAYLOAD_KEEP_MASK)


def decode_field(byte4):
    """Decode 0x14A byte4. field == 0 => THE CAVE DID NOT FIRE (VOID), never "everything false"."""
    if (byte4 >> 3) & 0x1F == 0:
        return None
    out = {"live": bool(byte4 & BIT_LIVE), "class_marker": bool(byte4 & BIT_CLASS)}
    for disp, bit, name, _k, _l, _w in CELLS:
        out[name] = bool(byte4 & bit)
    # ★ V68's structural signature: BOTH constants must be set on every legal frame.
    out["structural_ok"] = out["live"] and out["class_marker"]
    return out


def _self_check_wire():
    """Every cell EXHAUSTIVELY over its full width -- 256 for a byte, 65,536 for a halfword."""
    zeros = {d: 0 for d, _, _, _, _, _ in CELLS}
    for other in (0, 0xFF):
        for disp, bit, name, kind, lvl, _w in CELLS:
            want = rung_predicate(kind, lvl)
            span = 65536 if kind == KIND_HWORD else 256
            for v in range(span):
                vals = {d: (v if d == disp else other) for d, _, _, _, _, _ in CELLS}
                d_ = decode_field(wire_byte4(vals))
                assert d_ is not None and d_["live"], f"{name}={v} decodes as VOID"
                assert d_["class_marker"], f"{name}={v}: the class marker is CLEAR"
                assert d_[name] == want(v), f"{name}: bit wrong at value {v} (kind {kind}, lvl {lvl})"

    # ★★ THE TWO RUNGS ARE STRICTLY ORDERED STAGES OF ONE DETECTOR, and the ordering is a WIRE
    # INVARIANT the log can be checked against. gp-0x67df leaves NEUTRAL when |gp-0x6c2c| crosses
    # +-T; gp-0x671a only counts once a REVERSAL follows. So a reversal implies a crossing:
    #     bit4 set (reversed) => bit5 set (crossed)      [expected on the wire]
    #     bit5 set, bit4 clear                            = crossed but never reversed -- the NEW
    #                                                       information this revision buys
    # 🛑 It is an EXPECTATION, not an encoding guarantee: the two cells are sampled at the same TX
    # tick but cleared by different rules, so bit4 && !bit5 is possible at a clear boundary. The
    # decoder reports its rate rather than asserting it away.
    assert [c[0] for c in CELLS].index(FSM_DISP) < [c[0] for c in CELLS].index(DETECT_DISP), \
        "the FSM stage must be emitted before the reversal stage -- bit5 outranks bit4 here"
    assert BIT_MASK > BIT_RATE, "the crossing stage must own the HIGHER bit of the two"

    grid = (0, 1, 2, 5, 0xFF)
    for combo in itertools.product(grid, repeat=len(CELLS)):
        vals = {c[0]: v for c, v in zip(CELLS, combo)}
        d_ = decode_field(wire_byte4(vals))
        for (disp, _bit, name, kind, lvl, _w), v in zip(CELLS, combo):
            assert d_[name] == rung_predicate(kind, lvl)(v), f"{name} wrong in combo {combo}"

    # 🛑 THE SIGN TRAP, for the two `>=` byte rungs. `ld.bu` ZERO-extends, so r6 is in [0,255] and a
    # SIGNED `blt` against a small positive imm5 is the same test as an unsigned one. A high bit in
    # the byte (0x80..0xFF) must therefore read as a LARGE number, never as negative. If the load
    # were ever `ld.b` (SIGNED), every value 0x80..0xFF would flip and the bit would read 0.
    for disp, bit, name, kind, lvl, _w in CELLS:
        if kind != KIND_BYTE:
            continue
        for v in (0x80, 0xC0, 0xFF):
            assert wire_byte4({**zeros, disp: v}) & bit, \
                f"{name}: byte 0x{v:02X} reads as BELOW {lvl} -- the load is behaving as SIGNED"
        for v in range(0, lvl):
            assert not (wire_byte4({**zeros, disp: v}) & bit), f"{name}: {v} < {lvl} set the bit"
        for v in range(lvl, 256):
            assert wire_byte4({**zeros, disp: v}) & bit, f"{name}: {v} >= {lvl} cleared the bit"
    # bit4 counts a 0..CEIL counter, so spell out what `>= 1` means across its whole domain.
    for v in range(0, 6):
        assert bool(wire_byte4({**zeros, DETECT_DISP: v}) & BIT_RATE) == (v >= 1), \
            f"the detector bit is wrong at counter value {v}"

    # exactly EIGHT payloads are reachable, all with bit7 AND bit3 set
    legal = {wire_byte4({c[0]: (c[4] if on else 0) for c, on in zip(CELLS, sel)}, status_bits=0)
             for sel in itertools.product((0, 1), repeat=len(CELLS))}
    assert len(legal) == 2 ** len(CELLS), f"the probe emits {len(legal)} payloads, expected 8"
    assert all(b & BIT_LIVE and b & BIT_CLASS for b in legal), \
        "a reachable payload is missing the liveness bit or the class marker"
    assert decode_field(0x07) is None, "field == 0 must decode as VOID"

    # ★★ THE BUILD-CLASS MARKER, as an executable claim: V68's payload set is DISJOINT from the
    # payload sets of every prior build with a probe. This is the thing V66/V67 could not do.
    v67_legal = {V67.wire_byte4({d: (lvl if on else 0)
                                 for (d, _, _, lvl, _, _), on in zip(V67.CELLS, sel)}, status_bits=0)
                 for sel in itertools.product((0, 1), repeat=len(V67.CELLS))}
    v66_legal = {V66.wire_byte4({d: (1 if on else 0) for (d, _, _, _), on in zip(V66.CELLS, sel)},
                                status_bits=0)
                 for sel in itertools.product((0, 1), repeat=len(V66.CELLS))}
    # TIER 1 -- structural disjointness from V66/V67 (both of which never set bit3).
    assert not (legal & v67_legal), \
        f"V68 and V67 share payloads {sorted(hex(b) for b in legal & v67_legal)} -- the marker fails"
    assert not (legal & v66_legal), "V68 and V66 share a payload -- the marker fails"
    assert v66_legal == v67_legal, \
        "V66 and V67 no longer emit identical payload sets -- the premise of the marker has moved"
    on_wire = {b | PAYLOAD_KEEP_MASK for b in legal}     # as transmitted, status bits all set
    assert 0x87 not in on_wire and 0x8F in on_wire, \
        "V68 must never emit 0x87 (the four-way-ambiguous byte) and must emit 0x8F"
    assert all(b & 0xF8 != 0 for b in legal), "a legal payload collides with the VOID sentinel"
    assert not (on_wire & {0x07, 0x0F}), "V68 overlaps V53's or V54's payload"

    # 🛑 TIER 2 -- the HONEST overlap, DERIVED from each build's own invariant rather than typed.
    # This is the assertion that caught the docstring claiming "no prior build can produce that".
    def _therm(v):      # V59/V62: bit5 => bit4 => bit3
        return (not (v >> 5 & 1) or (v >> 4 & 1)) and (not (v >> 4 & 1) or (v >> 3 & 1))

    def _ladder(v):     # V65: bit6 => bit5, bit3 => bit4, never both sides
        return ((not (v >> 6 & 1) or (v >> 5 & 1)) and (not (v >> 3 & 1) or (v >> 4 & 1))
                and not (((v >> 5) & 3) and ((v >> 3) & 3)))

    space = [b for b in range(0x80, 0x100) if b & 0x07 == 0x07]
    v59_overlap = {b for b in space if _therm(b)} & on_wire
    v65_overlap = {b for b in space if _ladder(b)} & on_wire
    assert v59_overlap == {0x8F, 0x9F, 0xBF, 0xCF, 0xDF, 0xFF}, \
        f"the V59/V62 thermometer overlap is {sorted(hex(b) for b in v59_overlap)}, not the six " \
        "payloads the docstring states -- the TIER 2 numbers are stale"
    assert len(v59_overlap) == 6, \
        "V59/V62 overlap V68 in SIX of eight payloads. The marker does NOT separate them " \
        "structurally, and no wording in this file may say that it does."
    assert v65_overlap == {0x9F}, \
        f"the V65 ladder overlap is {sorted(hex(b) for b in v65_overlap)}, not {{0x9F}}"
    _self_check_wire.overlaps = {"V59/V62": v59_overlap, "V65": v65_overlap}

    # ---- the gain_B surface, asserted as CONTEXT ---------------------------------------------------
    # ⚠ No rung probes gp-0x6ac0 on this revision, so these are no longer claims about a probe bit --
    # they are claims about the IMAGE, kept because V67's arm derivation rests on them and V68 carries
    # that arm byte-identically. If this surface moves, V67's 5244 stops meaning what it meant.
    sc = int(7.2 * 64.0625)
    flat = EX.r24_gain_q10(sc, 0, 0, 0, 0)
    assert EX.r24_gain_q10(sc, RATE_BREAKPOINT - 1, 0, 0, 0) == flat, \
        "the segment below the breakpoint is not flat -- the gain_B surface moved"
    # ⚠ "FLAT" IS AN ENGINEERING CLAIM, NOT AN EXACT ONE, AND THE EXCEPTION IS PINNED HERE.
    # Record 0xD2AEC (the 50 km/h curve) has Y0 = 2305, Y1 = 2304 -- a ONE-count downward slope,
    # 0.04%. Three of four records are exactly flat. Asserted as EXACTLY this shape so a real ramp
    # could never hide behind the word "flat", and so no assertion elsewhere rests on Y0 == Y1.
    exact = [ys[0] == ys[1] for _xs, ys in V66.GAIN_B_EXPECT]
    assert exact == [True, True, False, True], f"the gain_B flatness pattern moved: {exact}"
    droop = [ys[0] - ys[1] for _xs, ys in V66.GAIN_B_EXPECT]
    assert droop == [0, 0, 1, 0], f"the first segment's droop is {droop}, not [0,0,1,0]"
    assert max(abs(d) / ys[0] for d, (_xs, ys) in zip(droop, V66.GAIN_B_EXPECT)) < 0.0005, \
        "the first segment droops by more than 0.05% -- it is a RAMP, not a flat segment"
    assert EX.r24_gain_q10(sc, RATE_BREAKPOINT + 200, 0, 0, 0) < flat, \
        "the segment above the breakpoint does not fall -- the breakpoint is not where we think"
    assert EX.r24_gain_q10(sc, RATE_FOLD, 0, 0, 0) == flat, \
        "the fold above RATE_FOLD does not land on the flat first point -- the stated asymmetry is wrong"
    _self_check_wire.flat_lerp = flat
    _self_check_wire.arm_for_2x_if_flat = 2 * flat

    # 🛑 THE PRE-REGISTERED PREDICTION IS RETRACTED (2026-08-03) -- see the docstring. The old
    # `assert 1.4 < headroom < 1.5` pinned a number derived through `bus = 8 x deg/s`, a relation
    # CLAUDE.md records as retracted, while THIS SAME MODULE imports the constant that contradicts it.
    # What is asserted now is the CONTRADICTION ITSELF, so it cannot be forgotten a second time.
    assert abs(EX.RATE_COUNTS_PER_DEGS / R47_CHAIN_STRUCK - 8.0) < 1e-6, \
        f"the struck chain is no longer exactly 8x from EX.RATE_COUNTS_PER_DEGS " \
        f"({EX.RATE_COUNTS_PER_DEGS / R47_CHAIN_STRUCK:.6f}) -- re-read the retraction before " \
        "trusting either number"
    assert R47_PREDICT["retracted"] is True, \
        "R47_PREDICT is no longer flagged as retracted -- it must never be quoted as a prediction"
    # Kept only so the readout below can print BOTH chains side by side. NOT a prediction.
    _self_check_wire.struck_headroom = RATE_BREAKPOINT / R47_PREDICT["max"]


_self_check_wire()

FLAT_LERP = _self_check_wire.flat_lerp                       # 2704
ARM_FOR_2X_IF_FLAT = _self_check_wire.arm_for_2x_if_flat     # 5408
STRUCK_HEADROOM = _self_check_wire.struck_headroom           # 1.442x -- RETRACTED, record only


# =======================================================================================================
# Image-level gates
# =======================================================================================================

DROPOUT_WRITERS = [0x2773A]                 # gp-0x67ac's ONE writer -- watched, never probed
FSM_WRITERS = [0x4299C]                     # gp-0x67df's SOLE writer, image-wide (V64 found it)
CENSUS_EXPECTED = {                         # on the V68 OUTPUT
    GATE_DISP: (14, 16, V67.GATE_WRITERS, {"ld.bu", "st.b"}, "ld.bu"),
    DEAD_DISP: (0, 0, [], {"ld.bu"}, None),     # UNREFERENCED image-wide since V67's repoint
    MASK_DISP: (14, 2, V67.MASK_WRITERS, {"ld.bu", "st.b"}, None),  # watched; V67 probed it, V68 not
    FSM_DISP: (1, 1, FSM_WRITERS, {"ld.bu", "st.b"}, "ld.bu"),                  # *** NEW bit5 ***
    DETECT_DISP: (7, 1, V67.ARM3_WRITERS, {"ld.bu", "st.b"}, "ld.bu"),          # *** NEW bit4 ***
    # ⚠ WATCHED, NEVER PROBED: the retired bit5 candidate. Its census is asserted so the "proven 0"
    # argument keeps being re-checked against the image on every build.
    DROPOUT_DISP: (2, 1, DROPOUT_WRITERS, {"ld.bu", "st.b"}, None),
    RATE_DISP: (26, 4, [0x41820, 0x41832, 0x41A8C, 0x41AAC], {"ld.hu", "st.h"}, None),
}
# On the V67 SOURCE the cave reads gp-0x671d (not gp-0x67df), and reads gp-0x671a at the same site.
CENSUS_EXPECTED_SRC = dict(CENSUS_EXPECTED)
CENSUS_EXPECTED_SRC[MASK_DISP] = (14, 2, V67.MASK_WRITERS, {"ld.bu", "st.b"}, "ld.bu")
CENSUS_EXPECTED_SRC[FSM_DISP] = (1, 1, FSM_WRITERS, {"ld.bu", "st.b"}, None)

CENSUS_CONSUMERS = {GATE_DISP: REPOINT_ADDR,        # the repoint itself, asserted as a reader
                    MASK_DISP: 0x3AB98,
                    # ★ the FSM state's own consumer, inside the detector FUN_000428d4
                    FSM_DISP: 0x428E6,
                    DETECT_DISP: 0x3AA70,
                    RATE_DISP: 0x3AAC4}             # r24's own LERP index read in FUN_0003aa2c
_READ_MNEM = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}

# Where THIS cave reads each cell, derived from the listing so it can never drift from the code.
CAVE_CELL_READS = {}
for _disp, _bit, _name, _kind, _l, _w in CELLS:
    _sites = [a for a, r, _ in CAVE_LISTING if r == _emit_load(_disp, _kind)]
    assert len(_sites) == 1, f"gp-0x{_disp:04x} must be read EXACTLY once in the cave"
    CAVE_CELL_READS[_disp] = (_sites[0], "ld.hu" if _kind == KIND_HWORD else "ld.bu")

V67_CAVE_CELL_READS = {d: (a, "ld.bu") for d, a in V67.CAVE_CELL_READS.items()}


def assert_cell_census(buf, label="V68", cave_reads=None, expected=None):
    """Re-derive the reader/writer sets from raw bytes and assert them exactly, by TWO decoders.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    """
    expected = CENSUS_EXPECTED if expected is None else expected
    cave_reads = CAVE_CELL_READS if cave_reads is None else cave_reads
    span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
    for disp, (n_read, n_write, writers, mnems, _cave_mnem) in expected.items():
        hits = V64.gp_access_census(buf, disp)
        assert all(m in mnems for _, m, _ in hits), \
            f"{label}: gp-0x{disp:04x} has an access outside {sorted(mnems)} -- wrong WIDTH or SIGN"
        fw = [h for h in hits if h[0] not in span]
        reads = [h for h in fw if h[1] in _READ_MNEM]
        writes = [h for h in fw if h[1] not in _READ_MNEM]
        assert len(reads) == n_read, \
            f"{label}: gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}: " \
            f"{[hex(a) for a, _, _ in reads]}"
        assert len(writes) == n_write, \
            f"{label}: gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}: " \
            f"{[hex(a) for a, _, _ in writes]}"
        assert [a for a, _, _ in writes] == writers, \
            f"{label}: gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}"
        if disp in CENSUS_CONSUMERS:
            assert any(a == CENSUS_CONSUMERS[disp] for a, _, _ in reads), \
                f"{label}: the consumer at 0x{CENSUS_CONSUMERS[disp]:05X} no longer reads " \
                f"gp-0x{disp:04x} -- the cell the probe reports on is not the one the gain uses"
        # ⚠ GATE 1 restated as a MEASUREMENT: the cave READS this cell and WRITES it nowhere.
        cave = [h for h in hits if h[0] in span]
        want = [(cave_reads[disp][0], cave_reads[disp][1], R6)] if disp in cave_reads else []
        assert cave == want, \
            f"{label}: cave accesses to gp-0x{disp:04x} are {[(hex(a), m, r) for a, m, r in cave]}, " \
            f"expected {[(hex(a), m, r) for a, m, r in want]}"

        # ---- SECOND METHOD: per-opcode decode over EVERY byte offset + the 48-bit extended form.
        alt = SCAN.scan(buf, (-disp) & 0xFFFF)
        alt_even = [h for h in alt if h["even"]]
        assert len(alt_even) == len(hits), \
            f"{label}: the two decoders disagree on gp-0x{disp:04x}: {len(hits)} vs {len(alt_even)}"
        assert sorted(h["addr"] for h in alt_even) == sorted(a for a, _, _ in hits), \
            f"{label}: the two decoders disagree on WHICH addresses touch gp-0x{disp:04x}"
        assert not [h for h in alt if not h["even"]], \
            f"{label}: gp-0x{disp:04x} has an ODD-OFFSET hit -- confirm the instruction boundary"
        ext = SCAN.scan_ext(buf, -disp)
        genuine = []
        for h in ext:
            d7 = SCAN.decode_fmt7(buf, h["addr"])
            if d7 is None or d7[4] != GP:
                genuine.append(h)
        if disp == DEAD_DISP:
            # ⚠ The record, kept alive on every build: gp-0x683c is UNREFERENCED by ANY displacement
            # form after V67's repoint. GATE 1's boot/pointer/ep/stack legs were closed separately
            # this session (see the docstring); the runtime-base-pointer and DMA legs were NOT, and
            # V68 does not use the cell. Its .data initializer is flash[0x86874].
            assert not ext, f"{label}: gp-0x683c has {len(ext)} extended-displacement candidates"
            assert buf[DEAD_INIT_FLASH] == 0, \
                f"{label}: gp-0x683c's .data initializer flash[0x{DEAD_INIT_FLASH:05X}] is " \
                f"0x{buf[DEAD_INIT_FLASH]:02X}, not 0x00 -- the boot value of the DEAD gate MOVED, " \
                "which would make V67's repointed-away cell non-zero at boot. STOP."
            assert n_read == 0 and n_write == 0 and not reads and not writes, \
                f"{label}: gp-0x683c has acquired an access"
        assert not genuine, \
            f"{label}: gp-0x{disp:04x} has {len(genuine)} extended-form candidate(s) that are NOT " \
            f"32-bit aliases: {[hex(h['addr']) for h in genuine[:8]]}"


def assert_probe_sites(code, label="V68"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V67 cave remnants survive past our payload"


def assert_signal_sites(code, label="V68"):
    """Every instruction donor the emitted encoders are pinned to, read FROM THE IMAGE."""
    for addr, raw, disp, reg2 in (PIN_LDBU_6806_R6, PIN_LDBU_671D_R6, PIN_LDBU_6806_R15,
                                  PIN_LDHU_6AC0_R6):
        assert bytes(code[addr:addr + 4]) == raw, \
            f"{label}: the pinned load at 0x{addr:05X} is {bytes(code[addr:addr+4]).hex()}, not {raw.hex()}"
        assert decode_load(raw)[1:] == (disp, GP, reg2), \
            f"{label}: the donor @0x{addr:05X} does not decode as gp-0x{disp:04x} -> r{reg2}"
    # ★ all FOUR byte-identical twins of the new rung's load
    for a in PIN_LDHU_6AC0_TWINS:
        assert bytes(code[a:a + 4]) == PIN_LDHU_6AC0_R6[1], \
            f"{label}: the `ld.hu -0x6ac0[gp],r6` twin @0x{a:05X} moved"
    assert bytes(code[PIN_BLT6[0]:PIN_BLT6[0] + 2]) == PIN_BLT6[1], \
        f"{label}: the pinned `blt +6` at 0x{PIN_BLT6[0]:05X} moved"
    # ★★ the EQUALITY branch, and the two new loads' displacement halfwords -- all from the image.
    assert bytes(code[PIN_BNE6[0]:PIN_BNE6[0] + 2]) == PIN_BNE6[1], \
        f"{label}: the pinned `bne +6` at 0x{PIN_BNE6[0]:05X} is " \
        f"{bytes(code[PIN_BNE6[0]:PIN_BNE6[0]+2]).hex()}, not {PIN_BNE6[1].hex()}"
    assert PIN_BNE6[1] != PIN_BLT6[1], "the `bne` and `blt` pins are the same bytes"
    for disp, (hw2, sites), what in ((DETECT_DISP, PIN_LDBU_671A_HW2, "gp-0x671a (bit4)"),
                                     (FSM_DISP, PIN_LDBU_67DF_HW2, "gp-0x67df (bit5)")):
        for a in sites:
            assert bytes(code[a + 2:a + 4]) == hw2, \
                f"{label}: {what}'s hw2 donor @0x{a:05X} is {bytes(code[a+2:a+4]).hex()}, not " \
                f"{hw2.hex()} -- the cell's own accesses moved and the displacement is unpinned"
            assert (struct.unpack_from("<H", code, a)[0] >> 5) & 0x3F in (0x3C, 0x3D, 0x3A), \
                f"{label}: {what}'s donor @0x{a:05X} is not an ld.bu/st.b opcode field"
    # 🛑🛑 THE FACT THE gp-0x67ac EXCLUSION RESTS ON, re-read from the image on EVERY build. This is
    # a CALIBRATION fact, not a structural guarantee: if this table ever carries a 6 or a 7, the
    # OR-latch becomes reachable, gp-0x67ac stops being provably 0, and the analysis REOPENS.
    got_roles = bytes(code[ROLE_TABLE_ADDR:ROLE_TABLE_ADDR + len(ROLE_TABLE_EXPECT)])
    assert got_roles == ROLE_TABLE_EXPECT, \
        f"{label}: the per-slot role table at 0x{ROLE_TABLE_ADDR:05X} is {list(got_roles)}, not " \
        f"{list(ROLE_TABLE_EXPECT)} -- the gp-0x67ac exclusion is STALE. STOP and re-derive."
    assert not (set(got_roles) & {6, 7}), \
        f"{label}: a slot role is 6 or 7 -- gp-0x617c can now be set, so the OR-latch can fire and " \
        "gp-0x67ac is NO LONGER provably 0. The retired bit5 candidate is live again."
    # ★ bit4's FULL word is FLOWN -- asserted against the V67 image on disk, where it actually ran
    # (routes 47 and 4a). It cannot be asserted against `code`: on V68 that site holds OUR copy, and
    # on stock the word does not exist at all (every real reader of gp-0x671a targets a different
    # register). Reading the file is the only honest form of this check.
    if os.path.exists(V67_BIN):
        _v67 = open(V67_BIN, "rb").read()
        a, want = PIN_LDBU_671A_FLOWN
        assert bytes(_v67[a:a + 4]) == want, \
            f"{label}: V67's flown cave word at 0x{a:05X} is {bytes(_v67[a:a+4]).hex()}, not " \
            f"{want.hex()} -- bit4's 'this exact word already flew' provenance is gone"
    assert V55.ldbu_any(-DETECT_DISP, R6) == PIN_LDBU_671A_FLOWN[1], \
        f"{label}: the encoder no longer reproduces V67's flown `ld.bu -0x671a[gp],r6`"
    assert bytes(code[PIN_CMP_P1_R6[0]:PIN_CMP_P1_R6[0] + 2]) == PIN_CMP_P1_R6[1], \
        f"{label}: the pinned `cmp 0x1,r6` at 0x{PIN_CMP_P1_R6[0]:05X} moved"
    assert bytes(code[PIN_CMP_R0_R6_ROM:PIN_CMP_R0_R6_ROM + 2]) == PIN_CMP_R0_R6[1], \
        f"{label}: the real `cmp r0,r6` at 0x{PIN_CMP_R0_R6_ROM:05X} moved"
    assert bytes(code[PIN_MOVEA_R0_R7[0]:PIN_MOVEA_R0_R7[0] + 4]) == PIN_MOVEA_R0_R7[1], \
        f"{label}: the real `movea 0x80,r0,r7` at 0x{PIN_MOVEA_R0_R7[0]:05X} moved"
    # ⚠ the WEAK pin: hw1 only, at seven real sites. Assert every one of them.
    hw1, sites = PIN_MOVEA_R6_R6_HW1
    for a in sites:
        assert bytes(code[a:a + 2]) == hw1, \
            f"{label}: the `movea imm,r6,r6` hw1 donor @0x{a:05X} is " \
            f"{bytes(code[a:a+2]).hex()}, not {hw1.hex()} -- the new rung's only provenance"
    # ★★ the BOOT-INIT map, pinned from the image. `mov imm32,reg` is 6 bytes: 2 opcode + LE32.
    for addr, imm in (BSS_CLEAR, DATA_SRC, DATA_DST, DATA_END):
        got = struct.unpack_from("<H", code, addr + 2)[0] | \
            (struct.unpack_from("<H", code, addr + 4)[0] << 16)
        assert got == imm, \
            f"{label}: the boot-init constant at 0x{addr:05X} is 0x{got:08X}, not 0x{imm:08X} -- " \
            "the RAM map moved and every GATE 1 clearance derived from it is now STALE"
    assert DATA_DST[1] <= (GP_ABS - DEAD_DISP) < DATA_END[1] - DATA_SRC[1] + DATA_DST[1], \
        f"{label}: gp-0x683c is not inside the .data copy range -- it is not .data after all"
    assert DEAD_INIT_FLASH == 0x86874, f"{label}: the initializer offset computed to {DEAD_INIT_FLASH:#x}"
    # r24's own LERP index read and the fold, so the new bit provably indexes the SAME cell the gain does
    assert bytes(code[0x3AAC4:0x3AAC8]) == bytes.fromhex("e45f4195"), \
        f"{label}: `ld.hu -0x6ac0[gp],r11` @0x3AAC4 moved -- r24's own read of the LERP index"
    assert u16(code, 0x3AAC8) == 0x060B and u16(code, 0x3AACC) == 0x5FE0, \
        f"{label}: the RATE_FOLD test at 0x3AAC8/0x3AACC moved -- the stated bit4 asymmetry is stale"
    V67.assert_signal_sites(code, label)


def assert_control_path(code, v67, label="V68"):
    """🛑 V68's core claim: the control path is V67's, byte for byte. Asserted, never assumed."""
    # --- the two V67 edits, from the image
    V67.assert_repoint(code, label, done=True)
    assert code[REPOINT_BYTE] == REPOINT_TO[2] == 0xFB, \
        f"{label}: 0x{REPOINT_BYTE:05X} is 0x{code[REPOINT_BYTE]:02X}, not 0xFB -- V67's repoint"
    assert u16(code, ARM_ADDR) == ARM_VALUE, \
        f"{label}: the arm 0x{ARM_ADDR:05X} is {u16(code, ARM_ADDR)}, not V67's {ARM_VALUE}"
    # --- the three `sar` sites, ALL STOCK
    for addr, want in SAR_SITES_STOCK:
        assert u16(code, addr) == want, \
            f"{label}: 0x{addr:05X} is 0x{u16(code, addr):04X}, not the stock 0x{want:04X}"
    # --- the sibling arms
    for addr, want, what in ((ARM_671A_ADDR, ARM_671A_STOCK, "0xC6440 the third arm"),
                             (ARM_671D_ADDR, ARM_671D_STOCK, "0xC6442 the masking arm"),
                             (R26_ARM_ADDR, V67.R26_ARM_STOCK, "0xC6444 r26's arm")):
        assert u16(code, addr) == want, f"{label}: {what} is {u16(code, addr)}, not {want}"
    # --- the four mode-10 gain_B records the new bit's breakpoint is read out of
    for rec in GAIN_B_RECORDS:
        assert bytes(code[rec:rec + V66.GAIN_B_RECORD_LEN]) == \
            bytes(v67[rec:rec + V66.GAIN_B_RECORD_LEN]), \
            f"{label}: mode-10 gain_B record 0x{rec:05X} differs from V67's"
    # --- the blend block, the lockout, the decoupled private gain
    assert bytes(code[D2000_BLOCK[0]:D2000_BLOCK[1]]) == bytes(v67[D2000_BLOCK[0]:D2000_BLOCK[1]]), \
        f"{label}: the 0xD2000 block differs from V67's"
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW == 0, \
        f"{label}: 0xC62EA is {u16(code, V53.LOCKOUT_ADDR)}, not 0"
    assert u16(code, V57.PRIVATE_ADDR) == V57.GAIN_4X == 3564, \
        f"{label}: 0xC6CD0 is {u16(code, V57.PRIVATE_ADDR)}, not 3564"
    # --- and every inherited table, re-run through V67's own assertions
    V62.assert_sar_sites(code, label, expect_doubled=False)
    V67.assert_untouched_context_v67(code, label)
    V63.assert_arms(code, label, expect_raised=False)
    V67.assert_untouched_v67(code, label)
    V57.assert_decoupled(code, label)
    V55.assert_variant_tables(code)
    V59.assert_index_chain(code, label)
    V66.assert_gain_b_surface(code, v67, label)
    assert set(code[R26_AVG_CAL:R26_AVG_CAL + R26_AVG_LEN]) == {0}, \
        f"{label}: 0xC6564 is no longer all-zero -- the r26-INERT record is what makes V67's shared " \
        "gate harmless, and V68 carries that gate unchanged. STOP and re-derive."


def assert_decoder_matches(cave_bytes, label="V68"):
    """🛑 The decoder's header must match the BUILT image, not a previous revision."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, f"{label}: {DECODER} carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"{label}: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   " \
        f"{cave_bytes.hex()}"
    for disp, bit, _name, _k, _l, _w in CELLS:
        assert f"gp-0x{disp:04x}" in txt, \
            f"{label}: the decoder never mentions gp-0x{disp:04x} (bit{bit.bit_length() - 1})"
    for token in ("0x67df", "0x671a", "0xC4124", str(ARM_VALUE), os.path.basename(OUT)):
        assert token in txt, f"{label}: the decoder does not carry '{token}'"
    return True


def build():
    if not os.path.exists(V67_BIN):
        print(f"  {V67_BIN} missing -- running the V67 builder first\n")
        V67.build()
    v67 = bytearray(open(V67_BIN, "rb").read())
    sha = hashlib.sha256(bytes(v67)).hexdigest()
    print(f"  V67 source {V67_BIN}\n    SHA256 {sha}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v67, "V67 source")
    assert walk(bytes(v67), label="V67 source") == 0
    assert walk_all_blocks(bytes(v67), label="V67 source") == 0
    V67.assert_probe_sites(v67, "V67 source")        # V67's OWN cave must be intact first
    assert_signal_sites(v67, "V67 source")
    assert_control_path(v67, v67, "V67 source")
    assert_cell_census(bytes(v67), "V67 source",
                       cave_reads=V67_CAVE_CELL_READS, expected=CENSUS_EXPECTED_SRC)
    V67.scan_self_check(bytes(v67), "V67 source", repointed=True)
    print("    census OK (TWO decoders): gp-0x6806 14r/16w, gp-0x683c 0r/0w, gp-0x671d 14r/2w,")
    print("               gp-0x671a 7r/1w, gp-0x6ac0 26r/4w (ALL ld.hu/st.h -> UNSIGNED halfword)")
    print(f"    control path: 0x{REPOINT_BYTE:05X}=0x{v67[REPOINT_BYTE]:02X}  "
          f"0x{ARM_ADDR:05X}={u16(v67, ARM_ADDR)}  sar "
          + "  ".join(f"0x{a:05X}=0x{u16(v67, a):04X}" for a, _ in SAR_SITES_STOCK))

    # ---- ★★ the on-car gate validation V67 rests on, re-asserted because V68 carries the gate ----
    print("\n  ★★ V67's gate validation is CARRIED, and re-checked rather than quoted:")
    pol = V67.assert_v57_probe_polarity("V68")
    val = V67.assert_gate_validation("V68")
    if pol:
        print("    V57's `bne` polarity byte re-read from the FLOWN V57 image                 PASS")
    if val:
        for route, v in val.items():
            print(f"    {route.replace('_cache_r', 'route '):>10s} {v['frames']:>8d} frames  "
                  f"{v['agreement_pct']:>7.3f}% agreement  duty {v['duty_pct']:>5.2f}%  "
                  f"{v['transitions_per_s']:.4f} transitions/s")
    print("    ⇒ and route 47 re-measured it end-to-end: bit6 == carControl.latActive in")
    print("      150,302 / 150,327 frames (99.983%) over 26 segments, the 25 disagreements all")
    print("      single-frame transition edges. bit6 is carried unchanged to keep measuring it.")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v67)

    # ---- THE ONLY EDIT: replace the cave payload --------------------------------------------------
    print(f"\n  THE ONLY EDIT -- replace V67's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes of the proven {len(V55.CAVE_BYTES)}, "
          f"{len(V55.CAVE_BYTES) - len(CAVE_BYTES)} spare):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v67[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V67's -- same cave base, same jarl"
    assert_probe_sites(code, "V68")
    assert_signal_sites(code, "V68")
    assert_cell_census(bytes(code), "V68")
    V67.scan_self_check(bytes(code), "V68", repointed=True)

    # ---- 🛑 THE CORE CLAIM: the control path is V67's, byte for byte -----------------------------
    print("\n  🛑 CONTROL PATH -- asserted byte-identical to V67, not summarised:")
    assert_control_path(code, v67, "V68")
    print(f"    0x{REPOINT_BYTE:05X} = 0x{code[REPOINT_BYTE]:02X}   the V67 repoint "
          f"(ld.bu -0x6806[gp],r15 @0x{REPOINT_ADDR:05X})")
    print(f"    0x{ARM_ADDR:05X} = {u16(code, ARM_ADDR):<6d} r24's LKAS arm")
    print(f"    0x{ARM_671A_ADDR:05X} = {u16(code, ARM_671A_ADDR):<6d} 0x{ARM_671D_ADDR:05X} = "
          f"{u16(code, ARM_671D_ADDR):<6d} 0x{R26_ARM_ADDR:05X} = {u16(code, R26_ARM_ADDR):<6d} "
          "(all stock)")
    print("    sar  " + "   ".join(f"0x{a:05X} = 0x{u16(code, a):04X}" for a, _ in SAR_SITES_STOCK)
          + "   ALL STOCK")
    for rec, (xs, ys) in zip(GAIN_B_RECORDS, V66.GAIN_B_EXPECT):
        print(f"    gain_B 0x{rec:05X}  X{xs}  Y{ys}   identical to V67")
    print(f"    0xD2000 block, 0x{V53.LOCKOUT_ADDR:05X} = {u16(code, V53.LOCKOUT_ADDR)}, "
          f"0x{V57.PRIVATE_ADDR:05X} = {u16(code, V57.PRIVATE_ADDR)}   all carried")

    # ---- MACHINE PROOF: the CAL block is byte-identical to V67's ---------------------------------
    cal_d = [i for i in range(CAL_BLOCK[0], CAL_BLOCK[1]) if code[i] != v67[i]]
    assert cal_d == [], \
        f"the CAL block differs from V67's at {[hex(x) for x in cal_d]} -- V68 must not touch calibration"
    print(f"    ⇒ the ENTIRE CAL block [0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X}) is byte-identical to "
          "V67's: 0 differing bytes")

    # ---- GATES ------------------------------------------------------------------------------------
    print("\n  GATES on the built image (each re-derived, not inherited):")
    n_store = sum(1 for _, raw, _ in CAVE_LISTING if len(raw) >= 4
                  and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B))
    print(f"    GATE 1  cave stores = {n_store} (the CAN-330 payload byte only); NO RAM cell is")
    print("            claimed and no store is added                                       PASS")
    print("    GATE 2  NOT ENGAGED -- V68 changes no control path (CAL block 0 bytes differ) PASS")

    # ---- 🛑 the sticky/HF rung, priced from the real encoders ------------------------------------
    b = build_cave.sticky_budget
    print("\n  🛑 WHY THE STICKY / HIGH-FREQUENCY RUNG IS NOT HERE -- priced, not argued:")
    print(f"    proven cave extent {len(V55.CAVE_BYTES)}B - fixed overhead 24B - bit6 12B - bit5 12B "
          f"= {b['free_after_bit6_bit5']}B FREE")
    print("    the CHEAPEST possible HF rung on gp-0x4f62 (no latch at all):")
    for text, nb in b["parts"]:
        print(f"      {nb:2d}B  {text}")
    print(f"      {b['minimum']:2d}B  TOTAL  -- already {b['minimum'] - b['free_after_bit6_bit5']}B "
          f"over budget, before any latch exists")
    print("    and a real latch (set / read-back / clear) adds:")
    for text, nb in b["latch"]:
        print(f"      {nb:2d}B  {text}")
    print(f"      {b['with_latch']:2d}B  TOTAL WITH LATCH -- "
          f"{b['with_latch'] / b['free_after_bit6_bit5']:.1f}x the available space")
    print("    ⇒ it does not fit, and the cave MUST NOT GROW: caves are this kit's only bricking")
    print("      class (V24, V27, V48B).")
    print("    🛑🛑 AND THE PREMISE IS FALSE ANYWAY -- THIS HOOK RUNS AT 100 Hz, NOT 1 kHz.")
    print("      0x55C0E is in FUN_00055a98 (the 0x14A builder); its ONLY pointer is 0xB72D4 =")
    print("      index 10 of PTR_FUN_000b72ac; msg-10's pending bit is set only by")
    print("      FUN_0001eaa6(0xa) @0x5560C, whose sole caller is FUN_00022ca0 @0x234C4 =")
    print("      TCB idx-4 = task 5 = c%10==4 = 100 Hz. A latch here CANNOT sample faster than the")
    print("      frame it is written into, so it degenerates to a plain sample at any budget.")
    print("      ⇒ NO PROBE ON THIS HOOK CAN BREAK THE ALIASING BARRIER. That needs a SECOND hook")
    print("        in task 1, i.e. new code on the 1 kHz path under the DTC-0x18 cadence watchdog.")
    print("      ⚠ V67's docstring says '1 kHz TX path'. That is WRONG and is corrected here.")
    print("    ⇒ two further reasons in the docstring: the rung is not frequency-selective, and the")
    print("      clear event does not exist -- CONFIRMED, all 8 accesses to gp-0x1514 leave bits 7:3")
    print("      untouched (the word RMW at 0x21964 ANDs 0xff0000ff and writes our byte back")
    print("      bit-identical), and the block-copy/register-indirect class is clean.")
    print("    ⇒ GATE 1 WAS NEVER REACHED. No RAM cell is claimed by V68.")
    print(f"    ⚠ RECORDED, UNUSED: gp-0x683c is .data (boot copy flash 0x{DATA_SRC[1]:05X} -> RAM "
          f"0x{DATA_DST[1]:08X} @0x{DATA_DST[0]:05X}),")
    print(f"      boot value flash[0x{DEAD_INIT_FLASH:05X}] = 0x{code[DEAD_INIT_FLASH]:02X}. The "
          "pointer / ep / stack / boot legs are CLOSED;")
    print("      the runtime-base-pointer and DMA legs are NOT, for this or any candidate.")
    print("    census (TWO decoders, on the OUTPUT):")
    for disp in (GATE_DISP, DEAD_DISP, MASK_DISP, ARM3_DISP, RATE_DISP):
        hits = V64.gp_access_census(bytes(code), disp)
        span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
        fw = [h for h in hits if h[0] not in span]
        r = len([h for h in fw if h[1] in _READ_MNEM])
        cv = [f"{hex(h[0])} {h[1]}" for h in hits if h[0] in span]
        note = {DEAD_DISP: "  *** UNREFERENCED image-wide; .data, boot value 0x00 @flash 0x86874",
                ARM3_DISP: "  (V67's bit4; V68 stops probing it -- it read 0.000% on route 47)",
                RATE_DISP: "  *** V68's NEW bit4 -- the LERP inner axis"}.get(disp, "")
        print(f"      gp-0x{disp:04x}  {r:2d}r / {len(fw) - r:2d}w firmware, cave "
              f"{cv or 'none'}{note}")

    # ---- CRC. ONLY the MAIN block moves: V68 edits code and no calibration. -----------------------
    for a, what, blk in ((CAVE_BASE, "cave base", MAIN_BLOCK),
                         (CAVE_BASE + len(V55.CAVE_BYTES) - 1, "cave last byte", MAIN_BLOCK)):
        assert V53.owning_block(code, a) == blk, \
            f"{what} 0x{a:05X} is not in the expected CRC block {[hex(x) for x in blk]}"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        moved = old_crc != new_crc
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({'RECOMPUTED' if moved else 'unchanged'})")
        if block == MAIN_BLOCK:
            assert moved, "the MAIN CRC did not move, but the cave did"
        else:
            assert not moved, "the CAL CRC MOVED -- V68 must not touch calibration"

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff a built image: full_image() writes 0xFF filler below 0x13000 and a naive
    # diff reports ~51,000 bogus bytes. Restricted to [0x13000,0x100000) throughout.
    cave_span = set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    allowed = cave_span | main_crc

    d67 = [i for i in range(0x13000, 0x100000) if code[i] != v67[i]]
    stray = [i for i in d67 if i not in allowed]
    assert not stray, \
        f"V68 differs from V67 outside the cave + the MAIN CRC: {[hex(x) for x in stray[:16]]}"
    assert main_crc <= set(d67), "the MAIN CRC trailer did not move"
    n_cave = len([i for i in d67 if i in cave_span])
    print(f"\n  V68 vs V67: {len(d67)} bytes  ({n_cave} cave + 4 MAIN CRC).  ZERO bytes outside "
          "the cave span")
    print("    EXACT byte list within the cave span:")
    for i in sorted(i for i in d67 if i in cave_span):
        print(f"      0x{i:05X}  0x{v67[i]:02X} -> 0x{code[i]:02X}")
    print(f"    MAIN CRC 0x{MAIN_BLOCK[1]:05X}: 4 bytes")
    print(f"    ⇒ no calibration byte moved; the CAL CRC 0x{CAL_BLOCK[1]:05X} is unchanged, which is")
    print("      itself the proof that V68's control path is V67's.")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V68 vs V38 baseline: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V68")
    assert walk(bytes(code), label="V68") == 0
    assert walk_all_blocks(bytes(code), label="V68") == 0
    assert_probe_sites(code, "V68")
    assert_signal_sites(code, "V68")
    assert_control_path(code, v67, "V68")

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the READBACK ------------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V68 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V68 readback")
    assert walk(bytes(readback), label="V68 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V68 readback") == 0
    assert_probe_sites(readback, "V68 readback")
    assert_signal_sites(readback, "V68 readback")
    assert_cell_census(bytes(readback), "V68 readback")
    V67.scan_self_check(bytes(readback), "V68 readback", repointed=True)
    assert_control_path(readback, v67, "V68 readback")
    assert bytes(readback[0x13000:0x100000]) == bytes(code[0x13000:0x100000]), \
        "the readback differs from the built image inside the flashed span"

    # re-decode the cave FROM THE READBACK, instruction by instruction, against the listing
    print("\n  cave re-decoded from the READBACK (not from what we meant to write):")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)

    print("\n  cell loads re-decoded from the READBACK by scan_gp_accesses (the hw1-bit-5 guard):")
    print(f"    {'site':>9s}  {'bytes':<10s} {'cell':<12s} {'disp':<8s} {'parity':<7s} {'op':<6s} "
          f"{'bit':<5s} {'test':<12s} provenance")
    for disp, bit, name, kind, lvl, _why in CELLS:
        a, want_mnem = CAVE_CELL_READS[disp]
        raw = bytes(readback[a:a + 4])
        mnem, got, reg1, reg2 = decode_load(raw)
        assert (mnem, got, reg1, reg2) == (want_mnem, disp, GP, R6), \
            f"{name}: readback @0x{a:05X} decodes as {mnem} gp-0x{got:04x} r{reg1}/r{reg2}"
        d16 = (0x10000 - disp) & 0xFFFF
        op = (struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F
        prov = {DETECT_DISP: "hw2 at 7 real readers; FULL WORD FLOWN on V67",
                DROPOUT_DISP: "hw2 at both real readers (incl. the consumer)",
                GATE_DISP: "byte-identical instance"}.get(disp, "see pins")
        op_s = "==" if kind == KIND_BYTE_EQ else ">="
        print(f"    0x{a:05X}  {raw.hex():<10s} gp-0x{disp:04x}    0x{d16:04X}   "
              f"{'ODD' if d16 & 1 else 'EVEN':<7s} 0x{op:02X}   bit{bit.bit_length() - 1}  "
              f"{op_s} {lvl:<9d} {prov}")
    print("    ★ PROVENANCE -- BOTH new loads are FLOWN WORDS, lifted rather than re-derived:")
    print("      bit5 `ld.bu -0x67df[gp],r6` a4372198 == V64's cave word @0xC4B4C (its bit4, route 35)")
    print("      bit4 `ld.bu -0x671a[gp],r6` 8437e798 == V67's cave word @0xC4B50 (its bit4, rt 47/4a)")
    print("      Neither has a byte-identical instance in STOCK -- every real reader of both cells")
    print("      targets a different destination register -- but hw2 (the whole displacement, parity")
    print("      bit included) IS byte-identical at each cell's own accesses, and both full words")
    print("      have already run on the car. 🛑 NOTE THE PARITY SPLIT: gp-0x67df disp16 0x9821 is")
    print("      ODD (opcode 0x3D, hw1 a437); gp-0x671a disp16 0x98E6 is EVEN (opcode 0x3C, hw1 8437).")

    print("\n  the CONTROL PATH, read back:")
    raw = bytes(readback[REPOINT_ADDR:REPOINT_ADDR + 4])
    mnem, got, reg1, reg2 = decode_load(raw)
    print(f"    0x{REPOINT_ADDR:05X}  {raw.hex()}  {mnem} -0x{got:04x}[r{reg1}],r{reg2}   "
          "(V67's repoint, carried)")
    print(f"    0x{ARM_ADDR:05X}  {u16(readback, ARM_ADDR)}   r24's LKAS arm (V67's, carried)")
    for addr, want in SAR_SITES_STOCK:
        print(f"    0x{addr:05X}  0x{u16(readback, addr):04X}  STOCK sar")

    print("\n★★ bit5 AND bit4 ARE TWO ORDERED STAGES OF ONE 1 kHz DETECTOR:")
    print("     bit5  gp-0x67df != 0   the FSM LEFT NEUTRAL: |gp-0x6c2c| crossed +/-12800.")
    print("                            *** NO REVERSAL REQUIRED. *** Catches events too brief or")
    print("                            too one-sided to reverse -- the marginal, intermittent case.")
    print("     bit4  gp-0x671a >= 1   ...and then REVERSED at least once.")
    print("     ⇒ EXPECT bit4 => bit5 on the wire. bit5 set with bit4 clear is the NEW information")
    print("       this revision buys: a crossing that never became a reversal.")
    print("     ⚠ An EXPECTATION, not an encoding guarantee -- the cells are sampled at the same")
    print("       tick but cleared by different rules, so bit4 && !bit5 can occur at a clear boundary.")
    print("       The decoder reports its RATE rather than asserting it away.")
    print("\n🛑 gp-0x67ac IS NOT PROBED -- IT IS PROVABLY 0 ON THIS BUILD.")
    print("     The r24/r26 lane-dropout skip fires iff gp-0x67ac == 1, and its 11-slot OR-latch can")
    print("     only be set for a per-slot role of 6 or 7. The static role table at tp+0x5124 =")
    print(f"     0x{ROLE_TABLE_ADDR:05X} reads "
          f"{list(readback[ROLE_TABLE_ADDR:ROLE_TABLE_ADDR + 11])} -- no slot is ever 6 or 7.")
    print("     ⇒ the rate lanes CANNOT silently drop out, so last session's highway null was NOT")
    print("       reading a disconnected lane. The question is CLOSED without spending a rung on it.")
    print("     ⚠ This rests on CALIBRATION BYTES, not structure. assert_signal_sites() re-reads the")
    print("       table every build and STOPS if a 6 or 7 ever appears. OPEN follow-up: gp-0x61a0's")
    print("       writer (search FUN_00026c80's CALLERS) and gp-0x61e8's identity.")

    print("\n  🛑 WHAT bit4 MEANS -- DUTY IS NOT OCCUPANCY. READ THIS BEFORE ANALYSING IT.")
    print("     gp-0x671a counts REVERSALS of gp-0x6c2c past +/-T (cal 0xC620A = 12800), via raw")
    print("     counter gp-0x357c and FSM state gp-0x67df. It is 0..CEIL, and bit4 is `>= 1`.")
    print("       SUB-CEIL (1..4): cleared by a 50-tick dwell (cal 0xC64DD = 50) => visible ~50 ms")
    print("                        => only ~5 frames at the 100 Hz TX rate. ⚠ BRIEF EVENTS WILL BE")
    print("                        UNDER-COUNTED, and a single reversal may be missed entirely.")
    print("       AT CEIL  (5, cal 0xC64FA = 5): the output is RE-PINNED every tick. Release needs")
    print("                        5000 ticks (cal 0xC6270 = 5.0 s) with gp-0x6a5e >= 640 AND no")
    print("                        reversals. gp-0x6a5e is voted VEHICLE SPEED (voter FUN_00041eec,")
    print("                        settled 2026-07-29) and 640 counts is ~10 km/h.")
    print("                        => BELOW ~10 km/h THE LATCH NEVER RELEASES; at road speed it")
    print("                        releases 5 s after the last reversal.")
    print("     ⇒ bit4 IS A HOLD-TIME STATISTIC, NOT AN EVENT RATE. Duty over-states brief events at")
    print("       speed and vastly over-states them at creep. Do NOT read duty as a detector rate.")
    print("     🛑 AND IT IS A DETECTOR, NOT A SPECTROMETER: it reports THAT a reversal past +/-T")
    print("       happened. It gives NEITHER amplitude NOR frequency. Any frequency attribution must")
    print("       come from conditioning on something else (speed, maneuver, the gate), never bit4.")
    print("     ★ WHY IT IS WORTH A RUNG ANYWAY -- the band-pass result:")
    print("       gp-0x6c2c's cascade PEAKS near 61 Hz. Relative to 21.09 Hz: 1 Hz 0.05x, 45 Hz 1.54x,")
    print("       61 Hz 1.61x (max), 100 Hz 1.43x, 200 Hz 0.94x. So the trip AMPLITUDE falls above")
    print("       50 Hz: 21.3 Hz needs 1683 counts, 45 Hz 1104, 60 Hz 1056, 100 Hz 1186, 200 Hz 1735.")
    print("       Honda's own 1 kHz detector is MORE sensitive exactly where CAN (Nyquist 50.00) and")
    print("       the comma IMU (50.51) are blind. ⇒ THE ONLY ABOVE-50-Hz INSTRUMENT THIS KIT HAS,")
    print("       and V67's 0.000% does not speak to it: V67 tested `>= 5` (CEIL), this tests `>= 1`.")

    ok = assert_decoder_matches(CAVE_BYTES, "V68")
    print(f"\n  decoder link: rlog-tools/decode_v68_probe.py CAVE_HEX "
          f"{'MATCHES the built image' if ok else 'NOT CHECKED'}")

    print("\n  PROBE: 0x14A byte4  bit7 = LIVENESS (constant 1)")
    for disp, bit, name, kind, lvl, why in CELLS:
        op_s = "==" if kind == KIND_BYTE_EQ else ">="
        print(f"                      bit{bit.bit_length() - 1} = gp-0x{disp:04x} {op_s} {lvl:<4d} "
              f"{name:13s} {why}")
    print("                      bit3 = 1  *** THE V68 BUILD-CLASS MARKER *** (constant)")
    print("                      bits 2:0 = stock STEER_SENSOR_STATUS, preserved")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    ov = _self_check_wire.overlaps
    print("  ★★ V68 NEVER EMITS 0x87. Every legal frame carries bit7 AND bit3. Strength, in two")
    print("     tiers, both DERIVED above rather than asserted:")
    print("       TIER 1 structural, absolute: V53 (0x07), V54 (0x0F, bit7 clear), and V66/V67")
    print("              (bit3 NEVER set -- both builds assert it) are wholly disjoint from V68.")
    print(f"       TIER 2 empirical, and WEAK vs V59/V62: their thermometer reaches "
          f"{len(ov['V59/V62'])} of V68's 8")
    print(f"              payloads {sorted(hex(b) for b in ov['V59/V62'])};")
    print(f"              V65's ladder reaches only {sorted(hex(b) for b in ov['V65'])}. V59/V62 are")
    print("              excluded ONLY because both of their recorded routes contain 0x87.")
    print("     ⚠ None of this excludes a FUTURE build. Confirm the .rwd on the car.")
    print("  🛑 WHAT EACH BIT CAN AND CANNOT DISTINGUISH:")
    print("     bit6 CAN: engagement duty, transitions/s, and whether the gate ever toggles in the")
    print("               15-60 Hz kill band (aliased above ~50 Hz -- the tool says so).")
    print("          CANNOT: tell an inert gate from a mis-timed one within a single 10 ms frame.")
    print("     bit5 CAN: see a threshold CROSSING that never became a reversal -- the stage below")
    print("               bit4, and the only rung that can catch a brief or one-sided event. Same")
    print("               band-pass, so it inherits bit4's above-50-Hz sensitivity.")
    print("          CANNOT: separate one long crossing from several inside a dwell, and gives no")
    print("               amplitude or frequency. Also a HOLD (>= 50 ms), not an event count.")
    print("     bit4 CAN: see ABOVE 50 Hz -- the only instrument in this kit that can. Honda's 1 kHz")
    print("               detector sits behind a band-pass peaking near 61 Hz and needs LESS")
    print("               amplitude at 45-100 Hz (1056-1186 counts) than at 21.3 Hz (1683).")
    print("          CANNOT: give amplitude or frequency -- it is a DETECTOR, not a spectrometer. And")
    print("               duty is a HOLD TIME, not an event rate: sub-CEIL trips are visible ~50 ms")
    print("               (~5 frames) so brief events are UNDER-counted, while at CEIL the latch")
    print("               holds until 5.0 s above ~10 km/h with no reversals -- so below ~10 km/h it")
    print("               NEVER releases and duty saturates. Never read bit4 duty as detector rate.")
    print("     🛑 THE SAMPLING BARRIER IS UNCHANGED: the cave still writes into a 100 Hz frame, so")
    print("               bit4's own TIME SERIES is aliased like everything else. What is new is that")
    print("               the QUANTITY it reports was computed at 1 kHz inside the ECU. bit4 carries")
    print("               above-50-Hz information; it does not carry an above-50-Hz waveform.")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("     🛑 START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is")
    print("        unmeasurable. Long drive, mixed: highway engaged, city manual, parking-lot creep.")
    print("     Condition on carControl.latActive or 0x18F byte4 bit3, NEVER carState.cruiseState.")
    print("     Decode with rlog-tools/decode_v68_probe.py.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
