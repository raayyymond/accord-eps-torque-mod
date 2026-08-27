#!/usr/bin/env python3
r"""=================================================================================================
V99 -- THE COULOMB RAMP KNEE.  Move the modelled friction INTO the micro regime.
=================================================================================================

BASE: **V98** (`_v98_V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2_plain_image.bin`) --
**the build ON THE CAR**, flown as route 0x81, fault-free.

    THREE EDITS -- **FOUR DIFFERING BYTES IN THE WHOLE IMAGE** (+ 8 CRC trailer bytes).
    TWO CALIBRATION CELLS + ONE IN-PLACE, SAME-LENGTH CAVE INSTRUCTION.  NO CAVE-LOGIC CHANGE.

    0xC40BC   600 -> 300   THE LEVER.  The Coulomb-friction rate-ramp normaliser.  VIRGIN BELOW 600
    0xC63AC   150 -> 102   BASE HYGIENE.  A REVERT TO HONDA'S OWN VALUE (undoes V97).
    cave+0x1E `003a` -> `023a`   BUILD IDENTITY.  `mov 0x0,r7` -> `mov 0x2,r7`  ⇒ byte4 b5 == 1.

-------------------------------------------------------------------------------------------------
🛑 WHAT THIS BUILD IS, AND WHAT IT IS NOT
-------------------------------------------------------------------------------------------------
V98 was a ZERO-CAL INSTRUMENT and made no symptom claim.  **V99 is a FIX ATTEMPT with the V98
instrument carried forward BYTE-INTACT.**  The comparator rung `b6` -- the thing that produced the
kit's first within-symptom decomposition -- is **byte-identical to the build that produced it**,
because an endpoint you have already validated is worth more than a new rung.

**The symptom verdict is the OPERATOR'S, in HIS words** (grinding · vibrating · micro-ratcheting ·
ratcheting · excess friction).  Everything below is a DIAGNOSTIC, and nothing here is a claim that
any symptom is fixed.

-------------------------------------------------------------------------------------------------
THE LEVER -- 0xC40BC, decompiled first, then read at instruction level
-------------------------------------------------------------------------------------------------
`FUN_0003b8f6` is the 1 kHz PLANT MODEL.  Its output `gp-0x6bfc` -> `gp-0x6bfe` is the **MODEL arm**
of the observer residual that V98 measured.  From my own `decompile_function(0x3b8f6)` [EVIDENCE]:

    iVar20  = polarity * gp-0x6abc * 12                       # signed motor rate * 12
    ramp    = clamp( (iVar20 * 0.5) / (0xC40BC * 0.5), -1.0, +1.0 )        # 0x3bab0..0x3bae4
    friction_raw = |fVar18| * ramp * (0xC40D2/1024)  +  ramp * (0xC4080/1024)     # 0x3bb16
    friction     = clamp( EMA(friction_raw, alpha = 0xC40D0/4096), -10.0, +10.0 )  # 0x3bb22
    inertia      = clamp( ... 0xC40D6 x2 ... * 0xC646E , -10.0, +10.0 )
    🛑 MODEL   = clamp( (fVar18 - friction - inertia) * 0xC6468 , -20000, +20000 )   # ONE LINE:
                 `iVar20 = (int)((fVar18 - (fVar13 + fVar14)) * (float)uVar7);`

⇒ **`0xC40BC` IS A SATURATING RAMP ON MOTOR RATE.  IT DOES NOT SCALE THE OUTPUT CEILING.**  The
peak friction is `K1*|fVar18|/1024 + K0/1024`, which does not contain `0xC40BC` at all.  What the
cell sets is **WHERE the ramp reaches that peak** -- the KNEE -- and therefore the small-signal
gain below it.

    knee, in motor-rate counts   = 0xC40BC / 12
    knee, in degrees/s           = (0xC40BC / 12) / 4.7121        (4.7121 ct per deg/s)

    | 0xC40BC | knee ct | knee deg/s | small-signal gain | history                                |
    |---------|---------|------------|-------------------|----------------------------------------|
    |    150  |   12.5  |   2.65     |  4.0x             | never built                            |
    | ** 300**| **25.0**| ** 5.31**  | ** 2.0x**         | 🛑 VIRGIN -- THIS BUILD                |
    |    600  |   50.0  |  10.61     |  1.0x  (STOCK)    | every image V38..V98 except v85/86/86b |
    |   6000  |  500.0  | 106.1      |  0.1x             | V85 -- FLEW, and it was 2.3x WORSE     |

⚠ **[BELIEF]** that `gp-0x6abc` carries the same 4.7121 ct/(deg/s) scale the damper work uses for
the column.  The **PATTERN** predictions below survive ANY monotone rate scale; only the crossover
LOCATION depends on this constant.  Stated, not assumed away.

### 🛑 WHY DOWN, AND WHY THIS IS NOT A RE-RUN OF V85
V85 raised the cell to 6000, moving the knee to **106 deg/s -- far above the operator's entire
symptom regime**, so inside 1-13 deg/s the term became effectively **viscous and 10x smaller**.
Measured on-car: engaged/manual 6-9 Hz went **2.89x -> 6.58x**, band contrast **+0.682
[+0.213, +1.166]** = the micro-ratchet **2.3x WORSE**.  That is the kit's own observer logic running
forwards: **under-modelled friction is CHASED by a disturbance observer ⇒ stick-slip.**

**V99 is the same cell pushed the OTHER WAY, and below 600 is VIRGIN on all 94 images.**  It is
NOT a new lever and this build does not pretend otherwise -- it is *the same lever, the other
direction, into never-visited range*, which is a different claim from "a new lever" and is stated
as such.  What is different this time: V85's direction has a **measured on-car sign**, so the
prediction for the opposite direction is a sign flip on a measurement, not a fresh guess.

### ⭐ AND IT IS WHAT TURNS V89 ON
V89 doubled `0xC40D2` (K1) 102 -> 204 and measured **FLAT** (0.947 [0.827, 0.979] inside a
[0.900, 1.111] placebo band); the operator said *"fixed nothing."*  At 1 deg/s the STOCK ramp
delivers only `4.71 * 12 / 600` = **9.4 %** of full friction -- **V89 doubled a term the ramp was
switching OFF in exactly the regime the operator names.**  V99 moves the ramp instead.

    DELIVERED |friction| RELATIVE TO HONDA STOCK  (K1 x ramp, K0 = 0)
    column deg/s :   1     2     3     5     8    10    13  |   20    30    60
    STOCK (102,600):1.00  1.00  1.00  1.00  1.00  1.00  1.00 | 1.00  1.00  1.00
    V98   (204,600):2.00  2.00  2.00  2.00  2.00  2.00  2.00 | 2.00  2.00  2.00
    V99   (204,300):4.00  4.00  4.00  4.00  3.77  3.02  2.32 | 2.00  2.00  2.00   <- SATURATED == V98
                    <----- the operator's MICRO regime, 1-13 deg/s ----->

🛑 **SO THE COMBINED ON-CAR DOSE BELOW 5.31 deg/s IS 4x HONDA, NOT 2x.**  `0xC40BC` multiplies with
V89's K1, which is still on the car.  The operator must be told the compounded number, and it is
printed by this script from the built image.

⊕ **A REAL STRUCTURAL SAFETY PROPERTY, and it is checkable:** `ramp` is clamped to +-1.0 for **any**
value of `0xC40BC`, so the **REACHABLE SET of the friction term is BIT-IDENTICAL between V98 and
V99**.  V99 introduces no value the friction path could not already produce -- it only reaches
those values at a LOWER motor rate.  This is asserted numerically below, not argued.
🛑 **That is NOT a stability proof.  See GATE 2.**

-------------------------------------------------------------------------------------------------
BASE HYGIENE -- 0xC63AC 150 -> 102.  A REVERT TO HONDA, NOT A NEW LEVER.
-------------------------------------------------------------------------------------------------
⭐ **STOCK ENCODES AN EXACT PHASE MATCH BETWEEN THE TWO ARMS, AND V97 BROKE IT.** [EVIDENCE -- both
values read little-endian from `code.bin` and from the V98 image by this script:]

    0xC40D0 = 408 / 4096 = 0.099609375     MODEL arm, friction-path EMA   @0x3bb22
    0xC63AC = 102 / 1024 = 0.099609375     ACTUAL arm, accumulator pole   @0x38202
                           ^^^^^^^^^^^  BIT-IDENTICAL, both -23.63 deg at 7.79 Hz

Two **differently scaled** cells (/4096 and /1024) carrying **different numbers** (408 and 102),
chosen so the resulting alpha matches **to the last bit**.  V97 set 150 ⇒ alpha = 0.146484375 ⇒
-15.81 deg, i.e. it moved the two stages from 9.62 deg apart to **17.45 deg apart -- further out of
alignment, not closer.**  V97's own flight: *"I did not feel any difference ... so I stopped."*

**This is a REVERT to Honda's own value.  It adds no dynamics Honda did not ship**, and after it the
ACTUAL arm is byte-for-byte stock.  ⚠ It also means **V99 IS NOT A SINGLE-VARIABLE BUILD** -- two
cells move.  They sit on **OPPOSITE arms** and the reverted one returns to stock, so the only
non-Honda cells left on the observer structure are `0xC40D2` (V89) and `0xC40BC` (V99), **both on
the MODEL arm.**  That is the cleanest the structure has been since V89.

🛑 **SCOPE LIMIT, stated rather than glossed:** the alpha match is EVIDENCE about **two filter
stages**.  It is **not** a total arm-to-arm phase budget -- the six lanes feeding the accumulator
have upstream dynamics that are not summed here.  *"V97 went the wrong way"* is **EVIDENCE about
the two poles and BELIEF about the arms.**

-------------------------------------------------------------------------------------------------
IDENTITY -- and the honest statement of what it is worth
-------------------------------------------------------------------------------------------------
🛑 **byte7[7:6] IS EXHAUSTED.  All four codes are burned** (0 = <=V91 · 1 and 3 = V96/V97 · 2 = V98,
and V92 can also emit 2).  V98's own docstring predicted this: *"the build after this one has only
{1,3} left, both ambiguous."*

**V99 therefore takes its identity from a rung that V98 MEASURED DEAD.**  Route 81: `b5` duty
**0.0000 over 6,591 engaged frames**, 0.0034 in manual (38 frames of 11,391), and V98's own
comparator result (`b5` = 0 ⇒ REQUEST is the smallest arm) means the rung has already delivered
everything it was built for.

    V98  +0x18 cmp r6,r7 / +0x1A mov 0x2,r7 / +0x1C bge +4 / +0x1E `mov 0x0,r7`  -> b5 = measurand
    V99  ...................................................  +0x1E `mov 0x2,r7`  -> b5 == 1 ALWAYS

**Both branch arms now leave r7 = 2 ⇒ byte4 b5 is a HARD-WIRED CONSTANT 1.**

⭐ **WHY THIS IS THE SMALLEST POSSIBLE CAVE EDIT** -- code caves are this kit's ONLY bricking class
(V24, V27, V48B all bricked the ECU), so the edit is priced byte by byte:
  * **ONE INSTRUCTION, IN PLACE, SAME LENGTH -- and only ONE of its two bytes actually differs**
    (`mov imm5,r7` carries the immediate in the low byte; the opcode byte 0x3A is common to both).
    Payload stays **154 B / 59 instructions**.  V97 was a one-byte build too.
  * `023a` is **already in the flown V98 payload TWICE** -- at `+0x1A` (this very rung) and `+0x82`
    (the byte7 identity) -- and is Ghidra-certified Honda at `0x1708C`.  **ZERO hand-encoding.**
  * **No new branch, no new branch condition, no new target, no length change, no new register
    write, no new load, no new store.**  🛑 Nothing resembling a hand-encoded Format IX
    `shl reg,reg,reg` -- the class that bricked all three.
  * The PSW window is untouched: `+0x1E` lies **after** the `bge`, not inside a `cmp`->branch gap.
  * `ld.h -0x6bfa[gp]` and one `ld.w -0x374c[gp]` in pass 1 become **dead computation**.  They are
    **pure loads with no side effects** and are left in place, because removing them would be a
    strictly larger edit than leaving them.

🛑 **AND THE HONEST LIMIT: THIS IS A DUTY IDENTITY, NOT A SINGLE-FRAME ONE.**  V98 can emit `b5` = 1
on an isolated frame (its own build proved all four `(b6,b5)` codes structurally reachable, and 38
such frames were observed in manual).  So **ONE frame does not prove V99.**  What does:

    🛑 IDENTITY RULE, PRE-REGISTERED:  b5 duty >= 0.999 over the whole route  AND  byte7[7:6] == 2.
       V98 measured b5 duty 0.0022 over 17,982 frames.  Roughly 1 s of frames is decisive.
       IF THE IDENTITY RULE FAILS, NOTHING IN THE READOUT MAY BE REPORTED.

That is a **regression** from V98's single-frame identity and it is not hidden.  The durable fix --
a >= 3-bit identity field on its own `0x18F` hook -- must be **its own build**, never bolted onto a
measurement class.  That is how V24/V27/V48B bricked ECUs.

-------------------------------------------------------------------------------------------------
🛑 THE PRE-REGISTERED ENDPOINT -- written BEFORE the cut.  The sentence a null will license.
-------------------------------------------------------------------------------------------------
⭐ **E1 -- PRIMARY, AND IT CARRIES ITS OWN NULL-BY-CONSTRUCTION CONTROL.**

`0xC40BC` = 300 and 600 are **ARITHMETICALLY IDENTICAL wherever the ramp is saturated**, i.e.
wherever `|motor rate| >= 50 ct` (= 10.61 deg/s).  They differ by **exactly 2.00x** below 25 ct
(5.31 deg/s) and by a factor between 1 and 2 in between.  ⇒ **the drive contains its own internal
control band, needing no second build, no second drive and no matched episode.**  This is the first
lever in the arc whose negative control is a consequence of its own arithmetic.

    b6 = (|MODEL| >= |ACTUAL|), engaged, stratified by |wheel rate| -- V98 route 81 measured:
       0-5 deg/s   n=894   b6 = 0.4911     <- LEVER BAND, full 2.00x dose
       5-25        n=2469  b6 = 0.3556     <- LEVER BAND, partial dose
       25-60       n=1781  b6 = 0.3268     <- 🛑 CONTROL BAND, dose ratio == 1.000
       60+         n=1447  b6 = 0.6164     <- 🛑 CONTROL BAND, dose ratio == 1.000

  PREDICTED:  the 0-5 and 5-25 deg/s duties MOVE; the 25-60 and 60+ duties DO NOT, beyond their own
  sampling error.  **A change in ALL FOUR bins is an operating-point / route artefact, NOT the
  lever, and must be reported as such.**
  ⚠ **The control band is not perfectly clean** -- the 0xC40D0 EMA has tau = 9.53 ms at 1 kHz
  (~1 frame at 100 Hz), so a high-rate frame carries ~1 frame of low-rate history through the zero
  crossings of a 7.79 Hz oscillation.  Expect a residual leak of order 10 %, not zero.  And
  `gp-0x6abc` is the **MOTOR** rate while the bins are **COLUMN** rate; the two are coupled through
  the torsion bar, so **the prediction is ORDINAL (monotonically decreasing in |rate|, zero above
  the V98 knee), not a bin-exact number.**

  🛑 **A NULL ON E1 LICENSES, VERBATIM:** *"Doubling the modelled-Coulomb small-signal gain in the
  1-13 deg/s micro regime does not move the MODEL-vs-ACTUAL arm balance at any wheel rate, so the
  friction ramp's KNEE POSITION is not what sets that balance while he feels the symptom -- and
  since the reachable friction set is unchanged, no larger dose of THIS cell can do it either.
  The next lever must be outside FUN_0003b8f6's friction path."*

⭐ **E2 -- THE WITHIN-SYMPTOM SLOPE.  This is the statistic that worked on V98 and it is preserved
   EXACTLY: the `b6` rung is byte-identical to the build that produced it.**

  Partial Spearman( log(6-9 Hz band RMS) , b6 window duty | speed, |wheel rate|, press ),
  1.28 s windows, block-permutation null over 5.12 s blocks, 5,000 permutations.
     V98 route 81:  b6  r = -0.321,  p = 0.0050,  null 95 % |r| <= 0.221
                    b4  r = +0.087   NULL   |   b7  r = +0.037   NULL   <- the two controls
  PREDICTED for V99: **|r| shrinks toward the null band (|r| < 0.221)** if the friction knee is what
  modulates the mismatch during the symptom.  `b4` and `b7` must stay NULL on the identical test.

  🛑 **A NULL ON E2 -- i.e. r reproduces -0.32 within its own null width -- LICENSES, VERBATIM:**
  *"The ACTUAL arm's swelling during the symptom is NOT modulated by the modelled-Coulomb ramp
  knee.  The V98 comparator result stands and is reproducible across two builds, but its source
  lies outside the friction path, and FUN_0003b8f6's friction family (K0/K1/0xC40BC/0xC40D0) is
  closed as a lever for it."*
  ⊕ A **reproduction** of -0.32 is itself a first for the kit: no within-symptom statistic has ever
  been replicated on a second build.  A null on E2 is therefore still a result.

**E3 -- the overall engaged `b6` duty**, against V98's 0.4235 [0.363, 0.484] (SE from the bit's own
measured tau = 0.254 s).  Reported with its CI, never as a verdict on its own.

**POS-1 (identity)** byte7[7:6] == 2 at duty 1.0000 **AND** b5 == 1 at duty >= 0.999.
**POS-2 (analogue half)** CAN 427 non-degenerate: >= 20 distinct codes, p99 >= 8.  427 is UNTOUCHED
        by this build and measured 251 codes / 0.000 % saturation on route 81.
**POS-3** b3 constant (V98: duty 0.0000, 0 transitions ⇒ `gp-0x6752` is constant and NEGATIVE).
**R5b -- THE CONVERSE POSITIVE CONTROL, CARRIED:** `arg(V) - arg(B')` = +-180 deg reproduced on all
        four routes 7e/7f/80/81 to within 1 deg.  A broken bit map cannot produce it.  `b4`/`b7` are
        byte-identical, so this must reproduce a fifth time or the readout is void.

🛑 **UNBUILDABLE ENDPOINTS, EXPLICITLY NOT PROPOSED**, per the exposure the operator actually gives:
cross-build band ratios · episode bootstraps (min_ep = 2; one drive gives <= 3 episodes) · ring-down
zeta/Q · any >= 50 km/h claim · any dose ladder · any 5.12 s override statistic (5,013 contiguous
override runs corpus-wide have median 0.02 s and only SEVEN reach 5.12 s).

-------------------------------------------------------------------------------------------------
DRIVE PROTOCOL -- what the operator is asked to do
-------------------------------------------------------------------------------------------------
  1. **ONE parking-lot creep, LKAS ENGAGED, HANDS ON, using override to provoke the symptom** --
     exactly as he already drives it.  **STOP THE MOMENT THE SYMPTOM IS FELT.**  ~15-30 s engaged is
     enough for every endpoint above.  No highway, no matched episodes, no second drive.
  2. ⭐ **MANDATORY, NOT OPTIONAL: a within-drive LKAS-OFF arm of the SAME creep at matched speed.**
     Route 81 proved this is obtainable back-to-back -- the last engaged frame was t = 110.56 s and
     the LKAS-off demonstration began at t = 110.57 s, consecutive frames, same lot, same tyres,
     seconds apart.  **V98's spec called this "optional and free".  IT IS NEITHER: without it there
     is no control arm at all**, and the engaged/manual `b6` contrast (0.4235 vs 0.8041) is the
     sharpest reading V98 produced.
  3. ⚠ **`0xC40BC` IS NOT ENGAGEMENT-GATED -- IT ACTS IN MANUAL TOO.**  I re-derived the four entry
     guards of `FUN_0003b8f6` from my own decompile and every one is a plausibility/range check:
     `|gp-0x6b98| <= 8192` AND `|gp-0x4f60| <= 25600` AND `gp-0x6abc in [-13000, 12968]` AND
     `gp-0x6752 in {-1,0,+1}`.  **There is no LKAS gate.**  The live precedent is V65:
     *"makes the entire car vibrate, almost like I have a subwoofer, regardless of LKAS
     engagement."*  **He should expect the LKAS-off arm to feel different too, and that is the
     lever, not a fault.**

-------------------------------------------------------------------------------------------------
🛑 GATE 1 -- RAM OWNERSHIP
-------------------------------------------------------------------------------------------------
**The cave's STORE SET is UNCHANGED BY CONSTRUCTION: 3 stores across 2 cells, `{gp-0x1514,
gp-0x1511}`** -- byte-identical to V96's cave, which has now flown FOUR routes (7e / 7f / 80 / 81).
The identity edit changes an immediate inside a `mov`; it adds no store, no load and no register.
Asserted three ways, all from the BUILT IMAGE's own bytes and never from this source file:
  (a) the cave re-disassembles to a 59-instruction rung table, offset for offset;
  (b) the **DIFFERENTIAL whole-image gp-relative store scan, V99 vs STOCK**, returns exactly those
      three `st.b` and nothing else -- which also rules out an accidental write edit anywhere in
      [0x13000, 0x100000);
  (c) registers written subset {r0, r6, r7}; registers referenced subset {r0, gp, r6, r7, lp}.
🛑 **Static clearance is NOT sufficient on its own -- `gp-0x1500` passed both static methods and
still failed on-car.**  What carries the weight here is that the store set is byte-identical to a
cave that has flown four routes fault-free.

**The two calibration cells are FLASH, and both are read-only single-reader cells.**  Re-derived
this session by BOTH methods and set-differenced:
    `0xC40BC` (tp+0x50BC)  **1 site: `ld.hu 0x50bc[tp],r16` @0x3BAB4.**  Ghidra decompile shows one
                            consumer; a raw both-parity LE scan of every 4-byte tp-relative form
                            image-wide returns the same single site.  **0 writers.**
    `0xC63AC` (tp+0x73AC)  **1 site: `ld.hu 0x73ad[tp],r13` @0x38202** (hw2 = 0x73AC|1 -- the parity
                            trap, asserted from the bytes).  **0 writers.**
    Whole-image scan of every tp-relative STORE encoding: **49 distinct effective addresses, NONE
    within +-4 bytes of either cell.**
🛑 **NEVER-TOUCH, honoured:** `gp-0x6bfa` is shadowed at `gp-0x4cfa` under an ACTIVE LOCKSTEP
MONITOR (`cmp r6,r14 / bne -> FUN_0006b9fa`).  **V99 writes nothing to it.**  It only *reads* it,
exactly as V98 did on four fault-free routes -- and after the identity edit that read is dead.

-------------------------------------------------------------------------------------------------
🛑🛑 GATE 2 -- CLOSED-LOOP STABILITY.  **I CANNOT CLOSE IT FOR 0xC40BC, AND I AM NOT GOING TO
     ARGUE IT AWAY.**
-------------------------------------------------------------------------------------------------
Closing GATE 2 needs the loop transfer `L` around `FUN_0003b8f6` -> observer -> PID -> aggregator ->
governor -> shaper -> FOC -> plant -> sensor.  **`L` IS UNMEASURED.**  No magnitude-and-phase
argument in this build closes it, and none is offered.

**WHAT IS ACTUALLY TRUE, priced honestly:**
  * ✅ **The reachable set of the friction term is BIT-IDENTICAL to V98's** (|ramp| <= 1.0 for any
    normaliser).  V99 cannot produce a friction value V98 could not.  **Asserted numerically.**
  * ✅ **ZERO added phase in the algebraic sense** -- `0xC40BC` appears only inside a memoryless
    saturating gain.  No pole, no zero, no delay is added anywhere.
  * 🛑 **AND THAT IS EXACTLY WHY IT IS STILL DANGEROUS.**  A harder ramp raises the **describing-
    function gain of a memoryless nonlinearity at small amplitude** -- the classic limit-cycle
    setup.  The linear-loop model is DEAD here anyway: V86 falsified it, and the ~8 Hz ratcheting is
    a lightly-damped **RESONANCE, Q = 14-29**.  A describing-function gain change is precisely the
    thing that can move a resonance into a limit cycle.
  * 🛑🛑 **THE PRECEDENT, AND IT IS THE WORST ONE IN THE KIT: V80.**  *"Loud, strong, felt through
    the whole car, ~90 % of LKAS-engaged time, **noticeable vehicle instability**"* -- worst
    grinding ever recorded, a **30 s sustained 27.4 Hz limit cycle**, and **ZERO DTCs.**
    ⇒ **A STABILITY FAILURE HERE IS INVISIBLE TO THE FAULT SYSTEM.  The operator's own judgement
    on the road is the only detector, which is why the protocol says STOP THE MOMENT IT FEELS
    WRONG.**  V94 -- the only build he has ever aborted -- also produced no fault.
  * ⚠ **300 is the CONSERVATIVE dose and the floor is hard.**  `0xC40BC` is read UNSIGNED
    (`cvtf.uws` @0x3BABC) and used as a **DIVISOR** (`divf.s` @0x3BAD0) ⇒ **0 gives +-Inf/NaN** into
    `gp-0x6bfc`/`gp-0x6bfe` and thence into float comparisons.  **HARD FLOOR >= 1.**  At 300 the
    ramp still has a genuine linear region 0 -> 5.31 deg/s, so the term stays **VISCOUS below the
    knee and Coulomb above** -- it is 300x away from the pure-sign relay that value 1 would give,
    and it does **not** re-arm `0xC4080` (K0 = 0, and `ramp * 0 == 0` for every ramp).
  * ✅ Untouched and asserted: `0xC4080` (K0, NEVER-RAISE), `0xC407E` (Honda's 511 interlock -- V73
    raised it and V74/V75 hard-faulted), `0xC6CD0` (the 4x gain), `0xC6446`/`0x3AA96` (Lever B --
    the only measured fix on the car), `0x454FE`, all four authority curves, the shaper, 427.

-------------------------------------------------------------------------------------------------
CLASS, AGAINST THE WHOLE ARC SINCE V38 -- what is genuinely new, and what is a re-run
-------------------------------------------------------------------------------------------------
V38-V52 authority/filters/poles/caves · V53-V61 telemetry + lane mutes · V62-V73 the rate lane ·
V74-V83a the base-assist damper · V84-V86B damper reverts + phase · V87 subtractive rebase ·
V88 Lever B · V89 the plant model's K1 · V90 control · V91/V92 0xCBE74 x1.5 · V93/V94 0xCBE74 CUT
(ABORTED) · V96 instrument · V97 the first loop pole · V98 the first RELATIONAL instrument.

**V99 is the first build in the arc to be AIMED BY AN IN-FRAME MEASUREMENT FROM THE PREVIOUS BUILD.**
Every earlier lever was chosen from structure, from a cross-build band ratio, or from a desk
argument.  V98's `b6` said, from inside the ECU during the symptom itself, *"the ACTUAL arm swells
relative to MODEL when the grinding is loudest"* -- and V99 moves the one cell that changes the
MODEL arm's behaviour **specifically in the rate regime where that was measured**, while carrying
the measuring rung byte-intact so the same statistic can be re-read.

🛑 **AND WHAT IS NOT NEW, SAID PLAINLY BEFORE HE DRIVES IT:**
  * `0xC40BC` **has flown** -- at 6000 on V85/V86/V86B.  V99 is **the same cell, the other way.**
    What is different: 600 -> 300 is **VIRGIN on all 94 images**, the knee lands **inside** the
    symptom regime instead of far above it, and V85's direction carries a **measured on-car sign**
    (2.3x worse) so the opposite direction is a sign flip on a measurement, not a fresh guess.
  * `0xC63AC` **has flown** -- at 150 on V97.  V99 puts it **back to Honda's 102**.  That is a
    REVERT, not a lever, and no improvement is claimed for it on its own.
  * **NOTHING HAS MOVED MICRO-RATCHETING OR RATCHETING IN SIXTY BUILDS.**  The one operator report
    of micro-ratchet attenuation (V75) is totally confounded and its build hard-faulted.  Only V62
    and V88 ever produced both a measured change and an operator report of improvement, and both
    were the **grinding**, via a different mechanism (rate-derivative damping in the delivered
    command) that V88's own out-of-sample test proved does **not** reach the ratchet.
    **V99 is a bet on a mechanism, not a continuation of a working class.**

CROSS-BUILD CELL MATRIX -- printed by this script FROM THE IMAGES, not from the build scripts.
=================================================================================================
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, ANALYSIS_ROOT, RWD_DIR              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V99_WRITE", "").strip().lower()

TP = 0xBF000                      # 🛑 tp+0x50BC = 0xC40BC and tp+0x73AC = 0xC63AC, NOT 0xC5.../0xC7...

BASE_NAME = "_v98_V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "c9babfed6acf24c0c5877754149a60fd5866dae8407029d7a3a5d74870d151d9"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))

# =================================================================================================
# THE TWO CALIBRATION EDITS.  Named constants so the dose is a ONE-LINE change.
# =================================================================================================
NORM_CELL, NORM_TP_OFF = 0xC40BC, 0x50BC       # the Coulomb ramp normaliser
NORM_FROM, NORM_TO = 600, 300                  # 🛑 HARD FLOOR >= 1 (it is a DIVISOR)
NORM_READER = 0x3BAB4                          # `ld.hu 0x50bc[tp],r16`  -- the SOLE reader

POLE_CELL, POLE_TP_OFF = 0xC63AC, 0x73AC       # the ACTUAL accumulator's IIR pole
POLE_FROM, POLE_TO = 150, 102                  # V97 -> STOCK.  A REVERT.
POLE_READER = 0x38202                          # `ld.hu 0x73ad[tp],r13`  -- the SOLE reader

FRIC_EMA_CELL = 0xC40D0                        # 408/4096 -- the alpha 0xC63AC must match
K1_CELL, K0_CELL = 0xC40D2, 0xC4080
RATE_CT_PER_DEG = 4.7121                       # ⚠ BELIEF: gp-0x6abc shares the column rate scale

# =================================================================================================
# THE CAVE -- 2 BYTES, ONE INSTRUCTION, IN PLACE.  Everything else is byte-identical to V98.
# =================================================================================================
CAVE_BASE, CAVE_FREE_END, CAVE_LEN = 0xC4B34, 0xC4FF0, 154
IDENT_OFF = 0x1E
IDENT_FROM = bytes.fromhex("003a")             # mov 0x0,r7   -- V98's CLEAR arm
IDENT_TO = bytes.fromhex("023a")               # mov 0x2,r7   -- V99: both arms leave r7 = 2
TWIN_MOV_2_R7 = 0x1708C                        # Honda's own `mov 0x2,r7`, Ghidra-certified in V98
IDENT_TWINS_IN_PAYLOAD = (0x1A, 0x82)          # the SAME two bytes, already flown, in this payload

SRC_427, SRC_MODEL, SRC_REQ = 0x6B70, 0x6BFE, 0x6BFA
SRC_ACC, SRC_POL = 0x374C, 0x6752
DST_B4, DST_B7 = 0x1514, 0x1511
ACC_FW_SHIFT, POL_THRESHOLD, IDENTITY_CODE = 4, 0x80, 2
MASK_B4_PASS1, MASK_B4_PASS2, MASK_B7 = 0x00DF, 0x0027, 0x003F

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp
DI_CALL_ADDR, DI_TARGET = 0x55C0A, 0x1FA42                   # interrupts OFF
EI_CALL_ADDR, EI_TARGET = 0x55C2E, 0x1FA72                   # interrupts ON
CKSUM_CALL_ADDR = 0x55C18
R427_ADDR, R427_SRC = 0x55DF2, SRC_427
R427_SAR_ADDR, R427_SAR = 0x55E10, bytes.fromhex("a632")

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  Values are V99's EXPECTED values, asserted on the built image AND
# on the shipped .rwd.  The two cells this build MOVES are asserted separately, at both ends.
# =================================================================================================
FROZEN = {
    0xC4080: (2, 0, "🛑 K0 -- NEVER RAISE (latent pure Coulomb relay). ramp*0 == 0 for any ramp"),
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip. V73 "
                      "raised it and V74/V75 HARD-FAULTED"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- the value 0xC63AC=102 matches BIT-EXACTLY"),
    0xC40D2: (2, 204, "V89's K1 -- CARRIED. It MULTIPLIES with 0xC40BC: 4x stock below the knee"),
    0xC40D4: (2, 573, "command-branch EMA x2 -- V86 took it to 286 and was FALSIFIED"),
    0xC40D6: (2, 246, "🛑 accel/inertia EMA x2, fc 9.86 Hz -- VIRGIN 94/94. NOT touched"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP (-0.6 deg). Kill any proposal to move it"),
    0xC4048: (4, None, "FIR tap b0 = 1.0 (the 3-tap FIR is an IDENTITY)"),
    0xC404C: (4, None, "FIR tap b1 = 0.0"),
    0xC4050: (4, None, "FIR tap b2 = 0.0"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0 -- lane measured ~0 on 87,940 frames; frozen since V83a"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN 94/94. NOT this build"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN. A cliff edge, not a lever"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e -- lane PROVABLY == 0; editing it is a guaranteed null"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane"),
    0xC63AE: (2, 1024, "🛑 LERP index scale -- NEVER 0 (index goes constant = full relay)"),
    0xC6200: (2, 8192, "🛑 gp-0x6b70's OUTPUT CLAMP -- never below Y[0]"),
    0xC6468: (2, 2639, "shared model gain -- scales BOTH arms, cannot change their ratio"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
    0xC6446: (2, 5244, "🛑 Lever B ARM -- the ONLY measured fix on the car. Reverted 3x at rebases"),
    0x3AA96: (1, 0xFB, "🛑 Lever B GATE -- both halves or neither"),
    0xC6CD0: (2, 3564, "🛑 the 4x forward LKAS gain -- NEVER lower"),
    0xC62EA: (2, 0, "steer-to-zero, V53, on the car"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC640A: (2, 0xE000, "🛑 FALLBACK-2 = -8192 (STOCK) -- V94 cut it to -6144"),
    0xC640C: (2, 0xF333, "🛑 FALLBACK-1 = -3277 (STOCK) -- V94 cut it to -2458"),
    0xC63D2: (2, 6, "🛑 FUN_00036682 pole, fc 0.93 Hz -- ALREADY the tilt"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through"),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN. Pure phase; do NOT lower"),
    0xC6B12: (2, 98, "PID Ki -- VIRGIN but INERT"),
    0xC6B26: (2, 256, "PID Kp -- VIRGIN. Blunt"),
    0xC6194: (2, 3, "the REAL LKAS slew limiter -- dead because 0xC4118 is all-1. Do not arm"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried because free. Claim nothing for it"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE (UNGATED; V65's subwoofer)"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC64A1: (1, 1, "🛑 READ-ONLY"),
    0xE547C: (2, None, "🛑 AUTHORITY CURVE -- virgin on all 100 images. NOT touched"),
    0xE5404: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE52FC: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE5284: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xC520C: (2, None, "🛑 governor rate ceiling -- V40 BRICKED on a neighbour. NOT touched"),
}

# the friction DOSE family -- V92's x1.5 on the ENGAGED columns, CARRIED unchanged.
FRICTION_PTR_ARRAY, FRICTION_N_MODES = 0xCBE74, 34
REC_X_OFF, REC_Y_OFF, REC_LEN = 0x02, 0x08, 0x10
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_X = (0, 1280, 5760)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)
DOSE_FAMILY_Y = {24: 0xD6A6C, 26: 0xD7A5C, 27: 0xD7A6C}

VARIANT_TOKEN = "V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v99_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V99-{TAG}-0x{START:X}-0x{END:X}.rwd")

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    """Every assertion prints a BOOLEAN. A check that produces no output is not a check."""
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"🛑 ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rdw(buf, a, w):
    return u16(buf, a) if w == 2 else (buf[a] if w == 1 else rd(buf, a, w))


def rec_addr(buf, mode):
    """🛑 DEREFERENCE. An address is not a mode. Never hard-code a record address."""
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


def assert_frozen(buf, label, ref=None):
    """`want is None` means 'must equal the reference image', for cells whose value is not declared."""
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        exp = want if want is not None else rdw(ref, a, w)
        if got != exp:
            bad.append((a, got, exp, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


# =================================================================================================
# THE 0xC40BC ARITHMETIC, MIRRORED EXACTLY FROM THE DECOMPILE.  Integer/float as the ECU has it.
#   0x3BAB0  mul 0xc,r6,r0          x    = polarity * gp-0x6abc * 12
#   0x3BAB4  ld.hu 0x50bc[tp],r16   norm = 0xC40BC
#   0x3BAB8  cvtf.ws  r6,r7         SIGNED convert of x
#   0x3BABC  cvtf.uws r16,r9        UNSIGNED convert of norm   <- why the floor is >= 1
#   0x3BAD0  divf.s r14,r12,r14     ramp = (x*0.5) / (norm*0.5)   <- REAL FP DIVISION
#   0x3BAD8/0x3BAE4                 clamp to [-1, +1]
#   0x3BB16  maddf.s                friction = ramp*K1/1024*|model| + ramp*K0/1024
# =================================================================================================
def ramp(rate_ct, norm, pol=-1):
    """The saturating rate ramp.  `pol` is gp-0x6752; V98 measured it CONSTANT and NEGATIVE."""
    x = pol * rate_ct * 12
    return max(-1.0, min(1.0, (x * 0.5) / (norm * 0.5)))


def friction_gain(rate_ct, norm, k1, k0=0):
    """|friction| per unit |fVar18|, in the SAME units for every build -- so ratios are meaningful."""
    return abs(ramp(rate_ct, norm)) * (k1 / 1024.0) + 0.0 * k0


def knee_deg(norm):
    return (norm / 12.0) / RATE_CT_PER_DEG


# =================================================================================================
# A V850E2 decoder covering exactly the formats this cave uses.  It exists so the script
# RE-DISASSEMBLES THE PAYLOAD FROM THE BUILT IMAGE and checks it against the RUNG TABLE, rather
# than checking the bytes against the string it was handed.
# =================================================================================================
COND = {0x3: "bnh", 0xE: "bge"}
RN = {0: "r0", 3: "sp", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}


def rn(i):
    return RN.get(i, f"r{i}")


def _s16(v):
    return v - 0x10000 if v >= 0x8000 else v


def decode(img, addr):
    """Return (text, length, kind, operand, writes, refs) for one instruction at `addr`."""
    hw1 = struct.unpack_from("<H", img, addr)[0]
    reg2, op, reg1 = (hw1 >> 11) & 0x1F, (hw1 >> 5) & 0x3F, hw1 & 0x1F
    imm5 = hw1 & 0x1F
    if op == 0x00 and reg2 != 0:
        return f"mov   {rn(reg1)},{rn(reg2)}", 2, "mov_r", None, {reg2}, {reg1, reg2}
    if op == 0x10:
        return f"mov   0x{imm5:x},{rn(reg2)}", 2, "mov", imm5, {reg2}, {reg2}
    if op == 0x12:
        return f"add   0x{imm5:x},{rn(reg2)}", 2, "add", imm5, {reg2}, {reg2}
    if op == 0x13:
        return f"cmp   0x{imm5:x},{rn(reg2)}", 2, "cmp", imm5, set(), {reg2}
    if op == 0x0F:
        return f"cmp   {rn(reg1)},{rn(reg2)}", 2, "cmp_r", None, set(), {reg1, reg2}
    if op == 0x14:
        return f"shr   0x{imm5:x},{rn(reg2)}", 2, "shr", imm5, {reg2}, {reg2}
    if op == 0x15:
        return f"sar   0x{imm5:x},{rn(reg2)}", 2, "sar", imm5, {reg2}, {reg2}
    if op == 0x16:
        return f"shl   0x{imm5:x},{rn(reg2)}", 2, "shl", imm5, {reg2}, {reg2}
    if op == 0x0C:
        return f"subr  {rn(reg1)},{rn(reg2)}", 2, "subr", None, {reg2}, {reg1, reg2}
    if op == 0x08:
        return f"or    {rn(reg1)},{rn(reg2)}", 2, "or", None, {reg2}, {reg1, reg2}
    if op == 0x03 and reg2 == 0:
        return f"jmp   [{rn(reg1)}]", 2, "jmp", None, set(), {reg1}
    if (hw1 >> 7) & 0xF == 0xB:                                  # Format III  bcond disp9
        disp = (((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 0x7) << 1)
        disp -= 0x200 if disp & 0x100 else 0
        c = hw1 & 0xF
        return f"{COND.get(c, f'b?{c:x}'):5s} +{disp}", 2, "branch", disp, set(), set()
    hw2 = struct.unpack_from("<H", img, addr + 2)[0]
    if op == 0x30:                                # addi imm16,reg1,reg2 -- reg2 == r0 = flags only
        return (f"addi  {_s16(hw2):#x},{rn(reg1)},{rn(reg2)}", 4, "addi",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op == 0x36:
        return (f"andi  0x{hw2:x},{rn(reg1)},{rn(reg2)}", 4, "andi", (reg1, hw2),
                {reg2}, {reg1, reg2})
    if op == 0x31:
        return (f"movea {_s16(hw2):#x},{rn(reg1)},{rn(reg2)}", 4, "movea",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op == 0x39:                                # ld.h (hw2 bit0 == 0) / ld.w (bit0 == 1)
        name, d = ("ld.w", hw2 & ~1) if hw2 & 1 else ("ld.h", hw2)
        return (f"{name}  {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, name,
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op == 0x38:                                # ld.b, full disp16
        return (f"ld.b  {_s16(hw2):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.b",
                (reg1, _s16(hw2)), {reg2}, {reg1, reg2})
    if op in (0x3C, 0x3D):                        # ld.bu -- disp bit0 lives in the op field LSB
        d = (hw2 & ~1) | (op & 1)
        return (f"ld.bu {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.bu",
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op in (0x3E, 0x3F):                        # ld.hu -- hw2 bit0 is a marker, disp is even
        d = hw2 & ~1
        return (f"ld.hu {_s16(d):#x}[{rn(reg1)}],{rn(reg2)}", 4, "ld.hu",
                (reg1, _s16(d)), {reg2}, {reg1, reg2})
    if op == 0x3A:                                # st.b, full disp16
        return (f"st.b  {rn(reg2)},{_s16(hw2):#x}[{rn(reg1)}]", 4, "st.b",
                (reg1, _s16(hw2)), set(), {reg1, reg2})
    if op == 0x3B:                                # st.h (bit0 == 0) / st.w (bit0 == 1)
        name, d = ("st.w", hw2 & ~1) if hw2 & 1 else ("st.h", hw2)
        return (f"{name}  {rn(reg2)},{_s16(d):#x}[{rn(reg1)}]", 4, name,
                (reg1, _s16(d)), set(), {reg1, reg2})
    return f"op{op:02x} ??", 4, f"op{op:02x}", None, {reg2}, {reg1, reg2}


PSW_SETTERS = {"cmp", "cmp_r", "add", "addi", "sar", "shl", "shr", "subr", "or", "andi"}
PSW_TRANSPARENT = {"mov", "mov_r", "movea", "ld.h", "ld.w", "ld.b", "ld.bu", "ld.hu",
                   "st.b", "st.h", "st.w", "jmp"}


def assert_psw_windows(listing):
    """For EVERY branch, walk back to the nearest flag-setter and prove the gap is transparent.

    ⚠ `mov`'s flag-transparency is [BELIEF], not [EVIDENCE]: it rests on the SLEIGH model plus
    Honda's own compiled code scheduling `mov` into exactly this gap (0x1bd32, 0x1539a, 0x1a7b6),
    not on a quotation from the V850E2 manual.  It is UNCHANGED from V98, which has flown it.
    """
    rows, bad, windows = list(listing), [], []
    for i, (off, _, _, text, kind, _, _, _) in enumerate(rows):
        if kind != "branch":
            continue
        j, gap = i - 1, []
        while j >= 0 and rows[j][4] not in PSW_SETTERS:
            gap.append(rows[j])
            if rows[j][4] not in PSW_TRANSPARENT:
                bad.append(f"+0x{off:02X}: unclassified `{rows[j][3].strip()}` in the window")
            j -= 1
        if j < 0:
            bad.append(f"+0x{off:02X} {text.strip()}: NO flag-setter precedes it")
            continue
        windows.append((rows[j][0], rows[j][3].strip(), off, text.strip(),
                        [g[3].strip() for g in reversed(gap)]))
    return windows, bad


def scan_gp_stores(img, lo=START, hi=END):
    """EVERY gp-relative STORE encoding image-wide, as a raw LE byte scan.

    🛑 The DIFFERENTIAL GATE-1/2 proof: run it on the BUILT image and on STOCK and diff.  Keyed on
    the STORE OPCODE, reporting whatever displacement it finds -- so it is NOT blind to a 32-bit
    access at a different displacement covering the same byte (the method gap V96 itself found).
    """
    out = set()
    for a in range(lo, hi - 3, 2):
        hw1 = struct.unpack_from("<H", img, a)[0]
        op, reg1 = (hw1 >> 5) & 0x3F, hw1 & 0x1F
        if op not in (0x3A, 0x3B) or reg1 != 4:
            continue
        hw2 = struct.unpack_from("<H", img, a + 2)[0]
        if op == 0x3A:
            name, d = "st.b", hw2
        else:
            name, d = ("st.w", hw2 & ~1) if hw2 & 1 else ("st.h", hw2)
        out.add((a, name, _s16(d)))
    return out


def scan_tp_accesses(img, lo=START, hi=END):
    """EVERY tp-relative 4-byte reg-disp16 access, both load and store, ALL parity traps covered.

    🛑 This is the second method for the calibration-cell census.  `search_instructions` silently
    undercounts while reporting truncated:false, so every count that matters is confirmed here.
    """
    forms = {0x38: "ld.b", 0x39: "ld.h/w", 0x3A: "st.b", 0x3B: "st.h/w", 0x3C: "ld.bu",
             0x3D: "ld.bu", 0x3E: "ld.hu", 0x3F: "ld.hu", 0x30: "addi", 0x31: "movea",
             0x36: "andi", 0x37: "ori"}
    out = []
    for a in range(lo, hi - 3, 2):
        hw1 = struct.unpack_from("<H", img, a)[0]
        op, reg1 = (hw1 >> 5) & 0x3F, hw1 & 0x1F
        if reg1 != 5 or op not in forms:
            continue
        hw2 = struct.unpack_from("<H", img, a + 2)[0]
        if op in (0x3C, 0x3D):
            d = (hw2 & ~1) | (op & 1)
        elif op in (0x39, 0x3B, 0x3E, 0x3F):
            d = hw2 & ~1
        else:
            d = hw2
        out.append((a, forms[op], TP + d, op in (0x3A, 0x3B)))
    return out


def disassemble_cave(img, base, length):
    out, off = [], 0
    while off < length:
        text, n, kind, operand, writes, refs = decode(img, base + off)
        out.append((off, base + off, rd(img, base + off, n).hex(), text, kind, operand,
                    writes, refs))
        off += n
    assert off == length, f"the last instruction overruns the payload by {off - length} byte(s)"
    return out


# The rung table, as INTENT.  The BUILT image is checked against THIS, not against any hex string.
# 🛑 EXACTLY ONE ENTRY DIFFERS FROM V98'S TABLE: +0x1E.
EXPECTED = [
    # ---- PASS 1: b5 -- 🛑 NOW A HARD-WIRED CONSTANT 1 (the BUILD IDENTITY) ----------------------
    (0x00, "ld.h  -0x6bfa[gp],r6", "the REQUEST arm -- now DEAD computation, a pure load"),
    (0x04, "cmp   0x0,r6", ""), (0x06, "bge   +4", "-> +0x0A"),
    (0x08, "subr  r0,r6", "r6 = |REQUEST|"),
    (0x0A, "mov   r6,r7", "r7 = |REQUEST|"),
    (0x0C, "ld.w  -0x374c[gp],r6", "the ACTUAL arm, 32-bit -- also dead now"),
    (0x10, "sar   0x4,r6", "the FIRMWARE's own >>4 @0x38236"),
    (0x12, "cmp   0x0,r6", ""), (0x14, "bge   +4", "-> +0x18"),
    (0x16, "subr  r0,r6", "r6 = |ACTUAL|"),
    (0x18, "cmp   r6,r7", "flags = |REQUEST| - |ACTUAL|  (result now discarded)"),
    (0x1A, "mov   0x2,r7", "SET arm"),
    (0x1C, "bge   +4", "-> +0x20"),
    (0x1E, "mov   0x2,r7", "🛑 V99: was `mov 0x0,r7`. BOTH arms leave r7 = 2 ⇒ b5 == 1 ALWAYS"),
    (0x20, "shl   0x4,r7", "-> byte4 bit 5"),
    (0x22, "ld.bu -0x1514[gp],r6", ""),
    (0x26, "andi  0xdf,r6,r6", "clear ONLY bit 5"),
    (0x2A, "or    r7,r6", ""),
    (0x2C, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4, pass 1"),
    # ---- PASS 2: b6, b7, b4, b3 -- 🛑 BYTE-IDENTICAL TO V98 -------------------------------------
    (0x30, "ld.h  -0x6bfe[gp],r6", "the MODEL arm, UNFILTERED by FUN_00038148"),
    (0x34, "cmp   0x0,r6", ""), (0x36, "bge   +4", "-> +0x3A"),
    (0x38, "subr  r0,r6", "r6 = |MODEL|"),
    (0x3A, "mov   r6,r7", "r7 = |MODEL|"),
    (0x3C, "ld.w  -0x374c[gp],r6", "the ACTUAL arm, re-read (atomic -- interrupts are off)"),
    (0x40, "sar   0x4,r6", ""),
    (0x42, "cmp   0x0,r6", ""), (0x44, "bge   +4", "-> +0x48"),
    (0x46, "subr  r0,r6", "r6 = |ACTUAL|"),
    (0x48, "cmp   r6,r7", "flags = |MODEL| - |ACTUAL|"),
    (0x4A, "mov   0x4,r7", "ASSUME SET -- ⭐ THE PRIMARY INSTRUMENT, byte-identical to V98"),
    (0x4C, "bge   +4", "-> +0x50, taken iff |MODEL| >= |ACTUAL| ⇒ KEEP"),
    (0x4E, "mov   0x0,r7", "else CLEAR"),
    (0x50, "ld.h  -0x6b70[gp],r6", "Stage-2 output / the PID reference"),
    (0x54, "cmp   0x0,r6", ""), (0x56, "bge   +4", "-> +0x5A"),
    (0x58, "add   0x8,r7", "b7 = gp-0x6b70 < 0   -- CONTROL, unchanged"),
    (0x5A, "ld.w  -0x374c[gp],r6", "third read"),
    (0x5E, "sar   0x4,r6", ""),
    (0x60, "cmp   0x0,r6", ""), (0x62, "bge   +4", "-> +0x66"),
    (0x64, "add   0x1,r7", "b4 = (gp-0x374c>>4) < 0   -- CONTROL, unchanged"),
    (0x66, "shl   0x4,r7", "-> bits 7, 6, 4"),
    (0x68, "ld.b  -0x6752[gp],r6", "the POLARITY CONSTANT -- SIGN-extends"),
    (0x6C, f"addi  {-POL_THRESHOLD:#x},r6,r0", "flags only; CY|Z = (r6 >=u 128)"),
    (0x70, "bnh   +4", "-> +0x74, skip iff gp-0x6752 < 0"),
    (0x72, "add   0x8,r7", "b3 = (gp-0x6752 >= 0) -> bit 3"),
    (0x74, "ld.bu -0x1514[gp],r6", ""),
    (0x78, "andi  0x27,r6,r6", "keep bit 5 (pass 1) and Honda's 2:0"),
    (0x7C, "or    r7,r6", ""),
    (0x7E, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4, pass 2"),
    # ---- byte 7: CARRIED FROM V98 ----------------------------------------------------------------
    (0x82, "mov   0x2,r7", "byte7[7:6] == 2, carried. 🛑 NO LONGER DISCRIMINATING -- V98 also emits 2"),
    (0x84, "shl   0x6,r7", "-> bits 7:6 = 0b10 = 2"),
    (0x86, "ld.bu -0x1511[gp],r6", ""),
    (0x8A, "andi  0x3f,r6,r6", "keep Honda's bits 5:0"),
    (0x8E, "or    r7,r6", ""),
    (0x90, "st.b  r6,-0x1511[gp]", "CAN 0x14A byte 7"),
    # ---- return ----------------------------------------------------------------------------------
    (0x94, "movea -0x1518,gp,r6", "restore the hooked instruction"),
    (0x98, "jmp   [lp]", ""),
]

M32 = 0xFFFFFFFF


def s32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def _abs_rung(v):
    """`cmp 0x0,rN / bge +4 / subr r0,rN` -- the cave's abs, in 32-bit register arithmetic."""
    return s32(0 - v) if not v >= 0 else v


def wire_byte4(x6b70, x6bfe, x6bfa, acc32, pol, honda_bits=0x7):
    """Mirrors the V99 cave's integer arithmetic EXACTLY, one line per instruction offset."""
    out = honda_bits & 0x7
    # ---- PASS 1 -- the arithmetic still RUNS; only the store value is now unconditional ---------
    r6 = _abs_rung(s32(x6bfa))                       # +0x00..+0x08
    r7 = r6                                          # +0x0A
    r6 = _abs_rung(s32(acc32) >> ACC_FW_SHIFT)       # +0x0C..+0x16
    _ = r7 >= r6                                     # +0x18 flags -- COMPUTED AND DISCARDED
    r7 = 2                                           # +0x1A SET / +0x1E now also SET  ⇒ CONSTANT
    r7 = (r7 << 4) & M32                             # +0x20
    out = ((out & MASK_B4_PASS1) | (r7 & 0xFF)) & 0xFF
    # ---- PASS 2 -- byte-identical to V98 --------------------------------------------------------
    r6 = _abs_rung(s32(x6bfe))                       # +0x30..+0x38
    r7 = r6                                          # +0x3A
    r6 = _abs_rung(s32(acc32) >> ACC_FW_SHIFT)       # +0x3C..+0x46
    r7 = 4 if r7 >= r6 else 0                        # +0x48..+0x4E   b6
    if not s32(x6b70) >= 0:
        r7 += 8                                      # +0x50..+0x58   b7
    if not (s32(acc32) >> ACC_FW_SHIFT) >= 0:
        r7 += 1                                      # +0x5A..+0x64   b4
    assert 0 <= r7 <= 0xD and (r7 & 0x2) == 0, "the pass-2 accumulator escaped bits 3,2,0"
    r7 = (r7 << 4) & M32                             # +0x66
    p = pol & 0xFF                                   # +0x68 ld.b
    r6u = (p - 256) & M32 if p >= 0x80 else p
    if not r6u >= POL_THRESHOLD:
        r7 += 8                                      # +0x72   b3
    return ((out & MASK_B4_PASS2) | (r7 & 0xFF)) & 0xFF


def wire_byte7(honda_bits=0x3F):
    return ((honda_bits & MASK_B7) | ((IDENTITY_CODE << 6) & M32)) & 0xFF


def decode_wire(b4, b7):
    """The SCORER's reconstruction, written here so it is pre-registered WITH the build."""
    return dict(identity_byte7=(b7 >> 6) & 0x3, identity_b5=bool(b4 & 0x20),
                valid=(((b7 >> 6) & 0x3) == IDENTITY_CODE) and bool(b4 & 0x20),
                sign_6b70=-1 if (b4 & 0x80) else +1,
                model_ge_actual=bool(b4 & 0x40),
                sign_actual=-1 if (b4 & 0x10) else +1,
                polarity_nonneg=bool(b4 & 0x08))


def assert_rung_semantics():
    """Every rung proven by EXHAUSTION or a corner grid, before a single byte is written."""
    bad = [p for p in range(256) if bool(wire_byte4(0, 0, 0, 0, p) & 0x08) != (p < 0x80)]
    assert not bad, f"the polarity rung is wrong at {bad[:8]}"
    print(f"    ✅ b3 == (gp-0x{SRC_POL:04X} >= 0) on ALL 256 byte values -- the `addi "
          f"{-POL_THRESHOLD:#x},r6,r0` + `bnh` unsigned-range idiom on a SIGN-EXTENDED `ld.b`, "
          f"proven BY EXHAUSTION.  Byte-identical to V98, which flew it")

    acts, arms = [], []
    for k in (0, 1, 2, 3, 7, 15, 16, 100, 511, 512, 2047, 2048, 4095, 8192, 20000, 32767):
        acts += [k << ACC_FW_SHIFT, -(k << ACC_FW_SHIFT), (k << ACC_FW_SHIFT) + 15,
                 -((k << ACC_FW_SHIFT) + 15)]
        arms += [k, -k]
    acts += [0, 1, -1, 15, -15, 1 << 30, -(1 << 30), -(1 << 31), (1 << 31) - 1]
    arms += [-32768, 32767, 0]
    acts, arms = sorted(set(acts)), sorted(set(arms))
    n, b5_seen, b6_seen = 0, set(), set()
    for a70 in (-8192, -1, 0, 1, 8192):
        for mdl in arms:
            for req in arms:
                for acc in acts:
                    for pol in (1, 0xFF):
                        w4, w7 = wire_byte4(a70, mdl, req, acc, pol), wire_byte7()
                        act = abs(s32(acc) >> ACC_FW_SHIFT)
                        assert bool(w4 & 0x80) == (a70 < 0), "b7 is not sign(gp-0x6b70)"
                        assert bool(w4 & 0x40) == (abs(mdl) >= act), "b6 is not |MODEL| >= |ACTUAL|"
                        assert (w4 & 0x20) == 0x20, "🛑 b5 IS NOT A CONSTANT 1 -- IDENTITY BROKEN"
                        assert bool(w4 & 0x10) == ((s32(acc) >> ACC_FW_SHIFT) < 0), \
                            "b4 is not sign(gp-0x374c>>4)"
                        assert bool(w4 & 0x08) == (pol < 0x80), "b3 is not (gp-0x6752 >= 0)"
                        assert w4 & 0x07 == 0x07, "Honda's byte4 bits 2:0 were not preserved"
                        assert w7 & 0x3F == 0x3F, "Honda's byte7 bits 5:0 were not preserved"
                        d = decode_wire(w4, w7)
                        assert d["valid"] and d["model_ge_actual"] == (abs(mdl) >= act), \
                            "the scorer's reconstruction does not round-trip"
                        b5_seen.add(bool(w4 & 0x20))
                        b6_seen.add(bool(w4 & 0x40))
                        n += 1
    print(f"    ✅ {n:,} corner cases, ZERO deviations, accumulators to +-2^31 and arms to +-32768")
    assert b5_seen == {True}, f"🛑 b5 reachable set is {b5_seen}, must be {{True}}"
    print(f"    ✅ 🛑 THE IDENTITY: b5 == 1 on EVERY input -- the REQUEST comparator's result is "
          f"computed and DISCARDED.  V98 measured this bit at duty 0.0000 over 6,591 engaged "
          f"frames and 0.0034 in manual ⇒ a SUSTAINED b5 == 1 is a reading V98 has never produced")
    assert b6_seen == {True, False}, "b6 must remain a live measurand"
    print(f"    ✅ ⭐ b6 IS STILL A LIVE MEASURAND (both values reachable) and its rung bytes are "
          f"UNCHANGED from V98 ⇒ the -0.321 within-symptom slope is re-readable with the SAME "
          f"instrument, which is the whole point of not touching it")
    for v in (0, 1, 100, 2048):
        assert wire_byte4(0, v, v, (v << ACC_FW_SHIFT), 1) & 0x40 == 0x40, \
            f"the |MODEL| == |ACTUAL| TIE at {v} does not read 1 -- the rung is `>`, not `>=`"
    print(f"    ✅ the TIE |MODEL| == |ACTUAL| still reads 1 (the rung is `>=`, not `>`)")
    assert {wire_byte7(h) >> 6 for h in range(64)} == {IDENTITY_CODE}
    print(f"    ✅ byte7[7:6] == {IDENTITY_CODE} on every Honda bit pattern -- CARRIED from V98. "
          f"🛑 It NO LONGER DISCRIMINATES (V98 emits 2 as well); b5 is the V99 identity")
    par = {wire_byte4(0, 0, 0, 0, p) & 0x08 for p in range(0x80, 0x100)}
    assert par == {0x00}, "b3 does not go 0 for a NEGATIVE polarity byte"
    print(f"    ✅ 🛑 CONVENTION BREAK CARRIED FROM V98: gp-0x{SRC_POL:04X} is measured NEGATIVE ⇒ "
          f"b3 == 0 ⇒ byte4[7:3] is EVEN.  The ~50-build 'always ODD' convention DOES NOT HOLD. "
          f"Route 81 confirmed it: alphabet {{2,8,10,12,16,24,26,28}}, EVEN on 100 % of frames. "
          f"⚠ V99 ADDS b5 == 1 ⇒ the byte4[7:3] field is now V98's value + 4 on every frame")


def assert_lever_arithmetic():
    """The 0xC40BC dose, mirrored from the decompile and asserted -- not described in prose."""
    k1_stock, k1_car = 102, 204
    print(f"    knee: 0xC40BC = {NORM_FROM} ⇒ {NORM_FROM / 12:.1f} ct = {knee_deg(NORM_FROM):.2f} "
          f"deg/s   |   0xC40BC = {NORM_TO} ⇒ {NORM_TO / 12:.1f} ct = {knee_deg(NORM_TO):.2f} deg/s")
    print(f"      {'deg/s':>7s} " + "".join(f"{d:>8.0f}" for d in
                                            (1, 2, 3, 5, 8, 10, 13, 20, 30, 60)))
    rows = (("STOCK 102/600", k1_stock, NORM_FROM), ("V98   204/600", k1_car, NORM_FROM),
            ("V99   204/300", k1_car, NORM_TO))
    ref = [friction_gain(d * RATE_CT_PER_DEG, NORM_FROM, k1_stock)
           for d in (1, 2, 3, 5, 8, 10, 13, 20, 30, 60)]
    for name, k1, nm in rows:
        vals = [friction_gain(d * RATE_CT_PER_DEG, nm, k1) / r
                for d, r in zip((1, 2, 3, 5, 8, 10, 13, 20, 30, 60), ref)]
        print(f"      {name:>13s} " + "".join(f"{v:>8.2f}" for v in vals))
    check(abs(friction_gain(1 * RATE_CT_PER_DEG, NORM_TO, k1_car)
              / friction_gain(1 * RATE_CT_PER_DEG, NORM_FROM, k1_stock) - 4.0) < 1e-9,
          f"🛑 THE COMPOUNDED DOSE: at 1 deg/s the delivered |friction| is EXACTLY 4.00x HONDA "
          f"(V89's K1 x2 TIMES V99's ramp x2). The operator must be told 4x, not 2x")
    check(abs(friction_gain(30 * RATE_CT_PER_DEG, NORM_TO, k1_car)
              / friction_gain(30 * RATE_CT_PER_DEG, NORM_FROM, k1_car) - 1.0) < 1e-12,
          f"🛑 THE NULL-BY-CONSTRUCTION CONTROL: at 30 deg/s V99 and V98 are ARITHMETICALLY "
          f"IDENTICAL (both ramps saturated at +-1.0) ⇒ the >= {knee_deg(NORM_FROM):.1f} deg/s "
          f"band is an internal negative control needing NO second build and NO second drive")
    lo, hi = knee_deg(NORM_TO), knee_deg(NORM_FROM)
    check(abs(friction_gain(lo * RATE_CT_PER_DEG, NORM_TO, k1_car)
              - friction_gain(lo * RATE_CT_PER_DEG, NORM_FROM, k1_car) * 2.0) < 1e-9
          and lo < hi,
          f"the dose ratio V99/V98 is EXACTLY 2.00x below {lo:.2f} deg/s, tapers to 1.00x at "
          f"{hi:.2f} deg/s, and is 1.00x above it -- monotone, so the E1 prediction is ORDINAL")
    reach99 = {round(abs(ramp(r, NORM_TO)), 12) for r in range(-4000, 4001)}
    reach98 = {round(abs(ramp(r, NORM_FROM)), 12) for r in range(-4000, 4001)}
    check(max(reach99) == max(reach98) == 1.0 and min(reach99) == min(reach98) == 0.0,
          f"🛑 GATE 2 (partial): |ramp| spans EXACTLY [0.0, 1.0] for BOTH normalisers ⇒ the "
          f"REACHABLE SET of the friction term is UNCHANGED. V99 introduces no value V98 could not "
          f"produce; it reaches them at a lower motor rate. ⚠ NOT a stability proof -- see GATE 2")
    check(NORM_TO >= 1,
          f"🛑 HARD FLOOR: 0xC40BC = {NORM_TO} >= 1. It is read UNSIGNED (cvtf.uws @0x3BABC) and "
          f"used as a DIVISOR (divf.s @0x3BAD0) ⇒ 0 would give +-Inf/NaN into gp-0x6bfc/gp-0x6bfe")
    check(NORM_TO >= 300,
          f"and {NORM_TO} PRESERVES a genuine viscous region 0 -> {knee_deg(NORM_TO):.2f} deg/s "
          f"below the knee -- it is {NORM_TO}x away from the pure-sign relay that value 1 gives")


def build():
    print("=" * 102)
    print("  V99 -- THE COULOMB RAMP KNEE.  0xC40BC 600 -> 300, into the micro regime.")
    print("  + 0xC63AC 150 -> 102 (REVERT TO HONDA)  + a 2-byte in-place cave edit (IDENTITY).")
    print("=" * 102)

    # ==============================================================================================
    print("\n  [1] THE BASE -- V98, the build ON THE CAR (route 0x81, fault-free)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    check(base_sha == BASE_SHA, f"base is V98, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(len(stock) == 0x100000, "stock reference dump loaded")

    # ==============================================================================================
    print("\n  [2] ADDRESS ARITHMETIC -- computed, never eyeballed (off-by-0x1000 has recurred 5x)")
    check(TP + NORM_TP_OFF == NORM_CELL,
          f"tp(0x{TP:X}) + 0x{NORM_TP_OFF:X} == 0x{NORM_CELL:X}  (NOT 0x{TP + 0x1000 + NORM_TP_OFF:X})")
    check(TP + POLE_TP_OFF == POLE_CELL,
          f"tp(0x{TP:X}) + 0x{POLE_TP_OFF:X} == 0x{POLE_CELL:X}  (NOT 0x{TP + 0x1000 + POLE_TP_OFF:X})")
    check(u16(base, NORM_CELL) == NORM_FROM and u16(stock, NORM_CELL) == NORM_FROM,
          f"ANCHOR: 0x{NORM_CELL:X} reads {NORM_FROM} on BOTH the V98 base and STOCK -- if the tp "
          f"offset were wrong this would not land on a known value")
    check(u16(base, POLE_CELL) == POLE_FROM and u16(stock, POLE_CELL) == POLE_TO,
          f"ANCHOR: 0x{POLE_CELL:X} reads {POLE_FROM} on the base (V97's) and {POLE_TO} on STOCK -- "
          f"so the revert target IS Honda's own value, read from Honda's own image")
    check(u16(base, FRIC_EMA_CELL) == 408 and u16(base, K1_CELL) == 204
          and u16(base, K0_CELL) == 0,
          f"anchors 0x{FRIC_EMA_CELL:X} = 408, 0x{K1_CELL:X} = 204 (V89), 0x{K0_CELL:X} = 0 (K0)")

    print("\n  [2b] ⭐ THE EXACT ALPHA MATCH -- computed from the images, both scalings")
    a_model = u16(base, FRIC_EMA_CELL) / 4096.0
    a_stock = u16(stock, POLE_CELL) / 1024.0
    a_v97 = u16(base, POLE_CELL) / 1024.0
    check(a_model == a_stock,
          f"🛑 0x{FRIC_EMA_CELL:X}/4096 = {a_model!r} == 0x{POLE_CELL:X}(STOCK)/1024 = {a_stock!r} "
          f"-- BIT-IDENTICAL across two DIFFERENT scalings and two DIFFERENT numbers (408 vs 102). "
          f"[EVIDENCE, read LE from code.bin. BELIEF, strong: a deliberate factory phase match]")
    check(a_v97 != a_model,
          f"and V97's {u16(base, POLE_CELL)}/1024 = {a_v97!r} BREAKS it. Reverting to {POLE_TO} "
          f"restores Honda's alignment; this build claims nothing more for that cell")

    # ==============================================================================================
    print("\n  [3] THE READER SITES -- both cells, both parities, from the BYTES")
    check(rd(base, NORM_READER, 4) == rd(stock, NORM_READER, 4),
          f"0x{NORM_READER:X} is byte-identical to stock -- V99 makes NO code edit at the reader")
    hw1n, hw2n = u16(base, NORM_READER), u16(base, NORM_READER + 2)
    check(((hw1n >> 5) & 0x3F) in (0x3E, 0x3F) and (hw1n & 0x1F) == 5
          and (hw2n & ~1) == NORM_TP_OFF,
          f"0x{NORM_READER:X} = {rd(base, NORM_READER, 4).hex()} decodes `ld.hu 0x{hw2n & ~1:X}[tp],"
          f"r{(hw1n >> 11) & 0x1F}` ⇒ UNSIGNED 16-bit load of 0x{NORM_CELL:X}. UNSIGNED is why the "
          f"floor is >= 1: the value goes straight into cvtf.uws and then a divf.s DIVISOR")
    hw1p, hw2p = u16(base, POLE_READER), u16(base, POLE_READER + 2)
    check(rd(base, POLE_READER, 4) == bytes.fromhex("e56fad73") and hw2p == (POLE_TP_OFF | 1),
          f"0x{POLE_READER:X} = e56fad73, hw2 = 0x{hw2p:04X} == (0x{POLE_TP_OFF:X} | 1) -- 🛑 THE "
          f"PARITY TRAP: the displacement does NOT appear literally in hw2 for this form")
    check(rd(base, 0x381FE, 4) == bytes.fromhex("2437b5c8")
          and rd(base, 0x38236, 2) == bytes.fromhex("a432")
          and rd(base, 0x38238, 2) == bytes.fromhex("8f31")
          and rd(base, 0x3823A, 2) == bytes.fromhex("c931"),
          "the three-arm subtraction is unchanged: 0x38236 `sar 0x4,r6` / 0x38238 `subr r15,r6` "
          "(coeff -1) / 0x3823A `add r9,r6` (coeff +1) ⇒ iVar6 = MODEL - (ACTUAL>>4) + REQUEST")

    print("\n  [3b] 🛑 GATE 1 FOR THE TWO CAL CELLS -- BOTH METHODS, SET-DIFFERENCED")
    tp_acc = scan_tp_accesses(base)
    for cell, name, want_site in ((NORM_CELL, "0xC40BC norm", NORM_READER),
                                  (POLE_CELL, "0xC63AC pole", POLE_READER)):
        sites = [(a, nm, is_st) for a, nm, ea, is_st in tp_acc if ea == cell]
        loads = [s for s in sites if not s[2]]
        stores = [s for s in sites if s[2]]
        check([a for a, _, _ in loads] == [want_site] and not stores,
              f"{name}: raw LE both-parity scan of EVERY tp-relative form image-wide finds "
              f"{len(loads)} reader ({hex(want_site)}) and {len(stores)} writers -- and Ghidra's "
              f"decompile of FUN_{0x3B8F6 if cell == NORM_CELL else 0x38148:08X} shows the same "
              f"single consumer. SET-DIFFERENCE: no disagreement to adjudicate")
    st_eas = {ea for _, _, ea, is_st in tp_acc if is_st}
    near = sorted(e for e in st_eas if abs(e - NORM_CELL) <= 4 or abs(e - POLE_CELL) <= 4)
    check(not near,
          f"and of the {len(st_eas)} distinct tp-relative STORE effective addresses image-wide, "
          f"NONE lies within +-4 bytes of either cell ({[hex(x) for x in near]}) -- these are FLASH "
          f"cells and nothing writes them")

    # ==============================================================================================
    print("\n  [4] THE LEVER ARITHMETIC -- mirrored from the decompile, asserted not described")
    assert_lever_arithmetic()

    # ==============================================================================================
    print("\n  [5] THE CAVE REGION AND ITS HOOK -- unchanged from the build that is flying")
    V98_CAVE = rd(base, CAVE_BASE, CAVE_LEN)
    check(len(V98_CAVE) == CAVE_LEN and all(b == 0xFF for b in
                                            base[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"V98's flown cave 0x{CAVE_BASE:05X}..0x{CAVE_BASE + CAVE_LEN - 1:05X} ({CAVE_LEN} B) is "
          f"present and the tail to 0x{CAVE_FREE_END:05X} is virgin 0xFF")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"cave hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp UNCHANGED")
    hk1, hk2 = u16(base, HOOK_ADDR), u16(base, HOOK_ADDR + 2)
    check(HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2) == CAVE_BASE,
          f"the hook's disp22 DECODES to 0x{HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2):05X} == the "
          f"cave base -- derived from the bytes, not assumed")

    def jarl_target(a):
        """🛑 Format-V disp22 is SIGNED; the DI/EI calls branch BACKWARD."""
        h1, h2 = u16(base, a), u16(base, a + 2)
        d = ((h1 & 0x3F) << 16) | h2
        return a + (d - 0x400000 if d & 0x200000 else d)

    check(jarl_target(DI_CALL_ADDR) == DI_TARGET and jarl_target(EI_CALL_ADDR) == EI_TARGET
          and DI_CALL_ADDR < HOOK_ADDR < EI_CALL_ADDR,
          f"🛑 INTERRUPTS ARE OFF ACROSS THE CAVE: 0x{DI_CALL_ADDR:05X} -> 0x{DI_TARGET:05X} (DI) "
          f"and 0x{EI_CALL_ADDR:05X} -> 0x{EI_TARGET:05X} (EI), hook between them")
    check(CKSUM_CALL_ADDR > HOOK_ADDR,
          f"the checksum call at 0x{CKSUM_CALL_ADDR:05X} runs AFTER the hook ⇒ both bytes the cave "
          f"writes are covered by 0x14A's own checksum")
    hw1_id, id_imm = u16(base, 0x55C14), u16(base, 0x55C16)
    check(((hw1_id >> 5) & 0x3F) == 0x31 and (hw1_id & 0x1F) == 0 and id_imm == 0x14A,
          f"🛑 THE HOOK IS THE 100 Hz CAN-TX BUILDER, NOT THE 1 kHz CONTROL TASK: 0x55C14 decodes "
          f"`movea 0x{id_imm:X},r0,r{(hw1_id >> 11) & 0x1F}` -- the builder loads the literal CAN "
          f"ID 0x{id_imm:X} four instructions after the hook")

    # ==============================================================================================
    print("\n  [6] 🛑 ZERO 427 BYTES -- asserted, not assumed")
    check(s16(base, R427_ADDR) == -R427_SRC and rd(base, R427_SAR_ADDR, 2) == R427_SAR,
          f"0x{R427_ADDR:05X} still selects gp-0x{R427_SRC:04X} and 0x{R427_SAR_ADDR:05X} is still "
          f"`sar 0x6,r6` ⇒ 427 = clamp(|gp-0x{R427_SRC:04X}| * 5 >> 6, 0, 0x3FF). Route 81: 251 "
          f"codes, 0.000 % saturation ⇒ POS-2 is already MEASURED PASSING on this exact channel")

    # ==============================================================================================
    print("\n  [7] THE PAYLOAD -- 152 of 154 bytes are the FLOWN V98 cave, byte for byte")
    payload = bytearray(V98_CAVE)
    check(rd(payload, IDENT_OFF, 2) == IDENT_FROM,
          f"V98 cave +0x{IDENT_OFF:02X} = {IDENT_FROM.hex()} = `mov 0x0,r7` -- the CLEAR arm we "
          f"are about to turn into a SET arm")
    payload[IDENT_OFF:IDENT_OFF + 2] = IDENT_TO
    payload = bytes(payload)
    diff = [i for i in range(CAVE_LEN) if payload[i] != V98_CAVE[i]]
    check(diff == [IDENT_OFF],
          f"🛑 THE CAVE DELTA IS EXACTLY **ONE BYTE**, AT +0x{IDENT_OFF:02X}: "
          f"{[hex(d) for d in diff]}. `mov imm5,r7` carries the immediate in the LOW byte, so "
          f"`003a` -> `023a` moves ONE byte and the opcode byte 0x3A is common to both -- the same "
          f"shape as V97, which was also a one-byte build. Payload stays {len(payload)} B: NO "
          f"GROWTH, NO NEW INSTRUCTION, NO NEW BRANCH, NO NEW STORE, NO NEW REGISTER")
    check(rd(base, TWIN_MOV_2_R7, 2) == IDENT_TO
          and rd(base, TWIN_MOV_2_R7, 2) == rd(stock, TWIN_MOV_2_R7, 2),
          f"🛑 TWIN: the 2 new bytes {IDENT_TO.hex()} are HONDA's own `mov 0x2,r7` at "
          f"0x{TWIN_MOV_2_R7:05X}, byte-identical in STOCK and V98 (Ghidra-certified as V98's "
          f"TWIN_MOV_2_R7). ZERO HAND-ENCODING -- the class that bricked V24/V27/V48B")
    for off in IDENT_TWINS_IN_PAYLOAD:
        check(rd(V98_CAVE, off, 2) == IDENT_TO,
              f"and the identical 2 bytes ALREADY FLY in V98's own payload at +0x{off:02X} "
              f"(routes 7e/7f/80/81, all fault-free) -- this is not a new encoding on this car")
    check(len(payload) == CAVE_LEN and payload[:IDENT_OFF] == V98_CAVE[:IDENT_OFF]
          and payload[IDENT_OFF + 2:] == V98_CAVE[IDENT_OFF + 2:],
          f"🛑 PAYLOAD COVERAGE {CAVE_LEN}/{CAVE_LEN}: {CAVE_LEN - 2} bytes are the FLOWN V98 cave "
          f"verbatim and 2 are a Honda twin. Zero bytes are hand-derived")

    # ==============================================================================================
    print("\n  [8] RUNG SEMANTICS -- proven by exhaustion / corner grid BEFORE any byte is written")
    assert_rung_semantics()

    # ==============================================================================================
    code = bytearray(base)
    attributed, by_addr = set(), {}

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
            by_addr[addr + k] = label
        print(f"    0x{addr:05X}  {len(post):4d} B   {label}")

    print("\n  [9] THE EDIT -- THREE, AND EVERY BYTE IS NAMED")
    apply(NORM_CELL, struct.pack("<H", NORM_FROM), struct.pack("<H", NORM_TO),
          f"EDIT 1  THE LEVER    0x{NORM_CELL:05X} {NORM_FROM} -> {NORM_TO}  Coulomb ramp knee "
          f"{knee_deg(NORM_FROM):.2f} -> {knee_deg(NORM_TO):.2f} deg/s")
    apply(POLE_CELL, struct.pack("<H", POLE_FROM), struct.pack("<H", POLE_TO),
          f"EDIT 2  THE REVERT   0x{POLE_CELL:05X} {POLE_FROM} -> {POLE_TO}  back to HONDA "
          f"(alpha {POLE_FROM / 1024.0} -> {POLE_TO / 1024.0}, re-matching 0x{FRIC_EMA_CELL:X})")
    apply(CAVE_BASE + IDENT_OFF, IDENT_FROM, IDENT_TO,
          f"EDIT 3  THE IDENTITY cave +0x{IDENT_OFF:02X} `mov 0x0,r7` -> `mov 0x2,r7` ⇒ byte4 "
          f"b5 == 1 on every frame")
    check(len(attributed) == 6,
          f"TOTAL ATTRIBUTED = {len(attributed)} bytes = 2 + 2 + 2 and NOTHING ELSE")
    check(rd(code, CAVE_BASE, CAVE_LEN) == payload,
          "the cave in the built image is byte-identical to the payload built above")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"cave tail 0x{CAVE_BASE + CAVE_LEN:05X}-0x{CAVE_FREE_END:05X} still virgin 0xFF")

    # ==============================================================================================
    print("\n  [10] 🛑 EVERY OTHER CALIBRATION CELL IS BYTE-EQUAL TO V98, CELL BY CELL")
    assert_frozen(code, "built image", ref=base)
    assert_frozen(base, "V98 base", ref=base)
    check(u16(code, NORM_CELL) == NORM_TO and u16(code, POLE_CELL) == POLE_TO,
          f"and the two MOVED cells read 0x{NORM_CELL:X} = {NORM_TO}, 0x{POLE_CELL:X} = {POLE_TO}")
    check(u16(code, POLE_CELL) == u16(stock, POLE_CELL),
          f"🛑 0x{POLE_CELL:X} now lands BYTE-EXACTLY ON STOCK ({u16(stock, POLE_CELL)}) -- "
          f"asserted against Honda's own image, not against a remembered number")
    check(rd(code, POLE_CELL, 2) == rd(stock, POLE_CELL, 2),
          "and byte-for-byte, not merely equal as an integer")
    moved = [m for m in range(FRICTION_N_MODES)
             if rd(code, rec_addr(code, m), REC_LEN) != rd(base, rec_addr(base, m), REC_LEN)]
    check(not moved,
          f"all {FRICTION_N_MODES} friction records are BYTE-IDENTICAL to V98 -- zero moved")
    for m, want_addr in sorted(DOSE_FAMILY_Y.items()):
        got = rec_addr(code, m) + REC_Y_OFF
        check(got == want_addr and rd(code, got, 6) == rd(base, got, 6),
              f"the DOSE FAMILY: mode {m}'s Y array DEREFERENCES to 0x{got:05X} == the named "
              f"0x{want_addr:05X} and its 6 bytes are byte-equal to V98")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == FRICTION_Y_STOCK, f"mode {m} (MANUAL)  Y = STOCK, unchanged")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == FRICTION_Y_V92, f"mode {m} (ENGAGED) Y = V92's x1.5, CARRIED")
    for m in MANUAL_MODES + ENGAGED_MODES:
        check(struct.unpack_from("<3h", code, rec_addr(code, m) + REC_X_OFF) == FRICTION_X,
              f"mode {m}: X = {FRICTION_X} UNCHANGED (no breakpoint moved anywhere)")
    check(rd(code, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4)
          == rd(base, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4),
          "the friction pointer array is byte-identical -- no pointer was rewritten")

    # ==============================================================================================
    print("\n  [11] 🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE, checked against the RUNG TABLE")
    listing = disassemble_cave(code, CAVE_BASE, CAVE_LEN)
    check(len(listing) == len(EXPECTED) == 59,
          f"{len(listing)} instructions decoded, rung table has {len(EXPECTED)}, expected 59 -- "
          f"UNCHANGED from V98")
    boundaries = {off for off, *_ in listing}
    writes, refs, conds = set(), set(), set()
    bad_text, bad_tgt, nbranch = [], [], 0
    for (off, addr, hx, text, kind, operand, w, r), (eoff, etext, note) in zip(listing, EXPECTED):
        if off != eoff or text.split() != etext.split():
            bad_text.append(f"+0x{off:02X} got `{text}` want `{etext}` @+0x{eoff:02X}")
        if kind == "branch":
            nbranch += 1
            conds.add(text.split()[0])
            if off + operand not in boundaries:
                bad_tgt.append(f"+0x{off:02X} -> +0x{off + operand:02X}")
        writes |= w
        refs |= r
        mark = "   <== V99" if off == IDENT_OFF else ""
        print(f"    +0x{off:02X}  0x{addr:05X}  {hx:12s}  {text:22s}  {note}{mark}")
    check(not bad_text,
          f"all {len(listing)} instructions match the RUNG TABLE offset-for-offset ({bad_text[:3]})")
    check(nbranch == 9 and not bad_tgt,
          f"{nbranch} branches, EVERY target lands on an instruction BOUNDARY ({bad_tgt[:3]})")
    check(conds == {"bge", "bnh"},
          f"🛑 NO NEW BRANCH CONDITION: exactly {sorted(conds)} == V92's/V96's/V98's proven set")
    v98_listing = disassemble_cave(base, CAVE_BASE, CAVE_LEN)
    delta = [(a[0], a[3].strip(), b[3].strip())
             for a, b in zip(v98_listing, listing) if a[3] != b[3]]
    check(delta == [(IDENT_OFF, "mov   0x0,r7", "mov   0x2,r7")],
          f"🛑 INSTRUCTION-LEVEL DIFF V98 -> V99, re-disassembled from BOTH images: EXACTLY ONE "
          f"instruction changed -- {delta}. Every other rung, branch, load and store is identical")
    bad_mn = [t.split()[0] for _, _, _, t, _, _, _, _ in listing
              if t.split()[0].startswith("op") or "?" in t
              or t.split()[0] in ("jarl", "jr", "callt", "div", "divh", "prepare", "dispose")]
    check(not bad_mn,
          f"the cave is a STRAIGHT-LINE LEAF: no call, no loop, no divide, no float, no unknown "
          f"opcode ({bad_mn[:4]})")
    check(writes <= {0, 6, 7},
          f"🛑 registers WRITTEN = {sorted(writes)} ⊆ {{r0, r6, r7}} -- IDENTICAL to V96/V98. "
          f"NO NEW LIVENESS CLAIM IS MADE AT THE HOOK")
    check(refs <= {0, 4, 6, 7, 31},
          f"🛑 every register REFERENCED = {sorted(refs)} ⊆ {{r0, gp, r6, r7, lp}} -- r8 and r10 "
          f"are LIVE across the hook (0x55C20 `andi 0xf,r10,r8`) and the cave never touches them")
    stores = [(off, operand) for off, _, _, _, k, operand, _, _ in listing if k.startswith("st.")]
    check([(o, d) for o, (rb, d) in stores] == [(0x2C, -DST_B4), (0x7E, -DST_B4), (0x90, -DST_B7)]
          and all(rb == 4 for _, (rb, _) in stores),
          f"🛑 GATE 1: the STORE SET is exactly {{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} -- three "
          f"store instructions, TWO cells, IDENTICAL to the cave that has flown FOUR routes")
    loads = sorted({row[5][1] & 0xFFFF for row in listing if row[4].startswith("ld.")})
    want_loads = sorted({(-x) & 0xFFFF for x in (SRC_427, SRC_MODEL, SRC_REQ, SRC_ACC, SRC_POL,
                                                 DST_B4, DST_B7)})
    check(loads == want_loads,
          f"and it LOADS exactly the same seven cells as V98. ALL PURE LOADS, no side effects")
    windows, psw_bad = assert_psw_windows(listing)
    for foff, ftext, boff, btext, gap in windows:
        print(f"      +0x{foff:02X} {ftext:<20s} -> +0x{boff:02X} {btext:<10s} gap: "
              f"{gap if gap else '(adjacent)'}")
    check(not psw_bad,
          f"🛑 PSW WINDOW: all {len(windows)} cmp/addi -> branch windows contain ONLY "
          f"PSW-TRANSPARENT instructions ({psw_bad[:3]})")
    gapped = [w for w in windows if w[4]]
    check(all(all(g.split()[0] == "mov" for g in w[4]) for w in gapped) and len(gapped) == 2,
          f"🛑 exactly {len(gapped)} windows are non-adjacent and BOTH contain only a `mov imm5` -- "
          f"UNCHANGED from V98. ⚠ `mov`'s flag transparency remains BELIEF (SLEIGH + Honda's own "
          f"scheduling at 0x1bd32/0x1539a/0x1a7b6), and V99 does not change the exposure")
    check(not any(w[0] <= IDENT_OFF < w[2] for w in windows),
          f"🛑 AND THE EDITED BYTE IS OUTSIDE EVERY cmp->branch WINDOW: +0x{IDENT_OFF:02X} lies "
          f"AFTER the +0x1C `bge`, not inside its gap ⇒ the PSW exposure is bit-for-bit V98's")
    kinds = {row[4] for row in listing if row[4].startswith("ld.")}
    check(kinds == {"ld.h", "ld.w", "ld.b", "ld.bu"},
          f"🛑 load CLASSES = {sorted(kinds)} -- the decode of the BUILT image separates all four")

    # ==============================================================================================
    print("\n  [12] VALUE-ANCHORED READBACK (a span diff is NOT a value check)")
    check(u16(code, NORM_CELL) == NORM_TO
          and rd(code, NORM_CELL, 2) == struct.pack("<H", NORM_TO),
          f"built 0x{NORM_CELL:X} = {NORM_TO}, bytes {rd(code, NORM_CELL, 2).hex()} (LITTLE-ENDIAN)")
    check(u16(code, POLE_CELL) == POLE_TO
          and rd(code, POLE_CELL, 2) == struct.pack("<H", POLE_TO),
          f"built 0x{POLE_CELL:X} = {POLE_TO}, bytes {rd(code, POLE_CELL, 2).hex()}")
    check(u16(code, FRIC_EMA_CELL) / 4096.0 == u16(code, POLE_CELL) / 1024.0,
          f"⭐ AND THE ALPHA MATCH IS RESTORED IN THE BUILT IMAGE: "
          f"{u16(code, FRIC_EMA_CELL)}/4096 == {u16(code, POLE_CELL)}/1024 == "
          f"{u16(code, POLE_CELL) / 1024.0!r}")
    check(code[CAVE_BASE + IDENT_OFF] == 0x02 and code[CAVE_BASE + IDENT_OFF + 1] == 0x3A,
          f"cave +0x{IDENT_OFF:02X} = `mov 0x2,r7` ⇒ 🛑 b5 == 1 STRUCTURALLY, on every frame")
    check(code[CAVE_BASE + 0x4A] == 0x04 and code[CAVE_BASE + 0x4B] == 0x3A,
          "⭐ cave +0x4A = `mov 0x4,r7` -- THE b6 SET VALUE, byte-identical to V98 ⇒ the primary "
          "instrument is untouched")
    check(code[CAVE_BASE + 0x82] == IDENTITY_CODE and code[CAVE_BASE + 0x83] == 0x3A,
          f"cave +0x82 = `mov 0x{IDENTITY_CODE:x},r7` ⇒ byte7[7:6] == {IDENTITY_CODE}, CARRIED")
    check(u16(code, CAVE_BASE + 0x28) == MASK_B4_PASS1
          and u16(code, CAVE_BASE + 0x7A) == MASK_B4_PASS2
          and u16(code, CAVE_BASE + 0x8C) == MASK_B7
          and (MASK_B4_PASS1 & MASK_B4_PASS2) == 0x07
          and (MASK_B4_PASS1 | MASK_B4_PASS2) == 0xFF,
          "the three RMW masks are unchanged and still PARTITION byte 4: pass 1 owns exactly {b5}, "
          "pass 2 exactly {b7,b6,b4,b3}, Honda's 2:0 survive both")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"cave hook 0x{HOOK_ADDR:05X} byte-identical")
    check(s16(code, R427_ADDR) == -R427_SRC and rd(code, R427_SAR_ADDR, 2) == R427_SAR,
          "🛑 427 is STILL byte-identical to V98 in the BUILT image -- zero 427 edits")

    # ==============================================================================================
    print("\n  [12b] 🛑 THE DIFFERENTIAL STORE-SET SCAN: every gp-relative WRITE, V99 vs STOCK")
    v99_st, stock_st = scan_gp_stores(code), scan_gp_stores(stock)
    added, removed = sorted(v99_st - stock_st), sorted(stock_st - v99_st)
    for a, nm, d in added:
        print(f"       + 0x{a:05X}  {nm}  gp{d:+#07x}   {rd(code, a, 4).hex()}")
    for a, nm, d in removed:
        print(f"       - 0x{a:05X}  {nm}  gp{d:+#07x}")
    check(not removed, f"no gp-relative store present in STOCK was removed or moved ({removed[:3]})")
    check([(a, nm, d) for a, nm, d in added]
          == [(CAVE_BASE + 0x2C, "st.b", -DST_B4), (CAVE_BASE + 0x7E, "st.b", -DST_B4),
              (CAVE_BASE + 0x90, "st.b", -DST_B7)],
          f"🛑 GATE 1, DIFFERENTIALLY: diffing ALL gp-relative writes image-wide, V99 vs STOCK "
          f"returns EXACTLY {len(added)} -- three `st.b` across TWO cells, and NOTHING was added "
          f"or removed anywhere else in [0x{START:X},0x{END:X}). Read from the BUILT IMAGE's own "
          f"bytes, not from the payload string")
    check(sorted(v99_st) == sorted(scan_gp_stores(base)),
          "⇒ and the store set is IDENTICAL to V98's -- V99 adds no RAM ownership claim at all")

    # ==============================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  [13] CRC -- {len(blocks)} block(s) move, trailer set DERIVED from the image's own "
          f"self-describing 50-block map")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len([a for a in touched if blk[0] <= a < blk[1]])} of "
              f"{len(touched)} touched byte(s)")
    derived = {blk[1] for blk in blocks}
    check(derived == {0xC4FFC, 0xC6FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xc4ffc, 0xc6ffc}} -- "
          f"0x{NORM_CELL:X} and the cave lie in the MAIN block [0x013000,0x0C4FFC); 0x{POLE_CELL:X} "
          f"lies in the calibration block [0x0C6000,0x0C6FFC). Derived, then asserted")
    check(len(blocks) == 2, f"EXACTLY ONE CRC trailer per edited block, {len(blocks)} blocks")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    check(0x055FFC not in crc_only,
          "🛑 0x055FFC is LIVE CODE (`6477b8f0`), NOT a CRC trailer -- writing there would silently "
          "overwrite 4 bytes of executable code and the recompute would HIDE it")
    check(walk_all_blocks(bytes(code)) == 0,
          "built image CRC chain 50/50 (NECESSARY, NOT SUFFICIENT -- see [14])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC])
          and not [a for a in attributed if 0xC5000 <= a < 0xC5FFC],
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(not [a for a in attributed if a < START or a >= END],
          f"every edit lies inside [0x{START:X},0x{END:X})")
    check(bytes(code[:START]) == bytes(base[:START]),
          f"nothing below 0x{START:X} changed (the bootloader region)")

    # ==============================================================================================
    runs, i = [], START
    while i < END:
        if code[i] != base[i]:
            j = i
            while j < END and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1

    def attribute(d):
        return by_addr.get(d, "CRC trailer" if d in crc_only else None)

    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  [14] 🛑 FULL BYTE DIFF: BUILT V99 vs the FLOWN V98 -- over [0x13000, 0x100000)")
    print(f"       {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"       0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    check(not stray, f"ZERO unattributed bytes vs V98 (stray = {[hex(x) for x in stray[:16]]})")
    non_crc = sorted(d for a, b in runs for d in range(a, b + 1) if d not in crc_only)
    check(non_crc == sorted([NORM_CELL, NORM_CELL + 1, POLE_CELL, CAVE_BASE + IDENT_OFF]),
          f"🛑 AND OUTSIDE THE CRC TRAILERS THE WHOLE BUILD IS **FOUR BYTES**: "
          f"{[hex(x) for x in non_crc]} = 2 bytes for the lever (600 = 0x0258 -> 300 = 0x012C, both "
          f"bytes move), 1 byte for the revert (150 = 0x0096 -> 102 = 0x0066, the HIGH byte is 0x00 "
          f"in both) and 1 byte for the identity. {total} differing bytes in total including the "
          f"two 4-byte CRC trailers")
    for lo, hi, why in ((0xC4000, 0xC40BC, "🛑 K0/K1/the FIR taps -- below the lever"),
                        (0xC40BE, 0xC4B34, "🛑 the rest of FUN_0003b8f6's cal family"),
                        (0xC4B34 + IDENT_OFF + 2, 0xC5000, "the rest of the cave and its tail"),
                        (0xC6000, 0xC63AC, "🛑 lane weights below the pole"),
                        (0xC63AE, 0xC7000, "🛑 LERP scale, clamps, model gain, Lever B"),
                        (0xE5000, 0xE6000, "🛑 THE AUTHORITY CURVE -- virgin, and it stays virgin"),
                        (0xCB000, 0xE0000, "every friction/gain record page (the dose family)"),
                        (0xD6000, 0xD8000, "the mode records"),
                        (0x55D00, 0x55F00, "🛑 the 0x1AB / 427 builder -- ZERO 427 edits")):
        check(not [d for a, b in runs for d in range(a, b + 1)
                   if lo <= d < hi and d not in crc_only],
              f"ZERO differing bytes in [0x{lo:05X},0x{hi:05X}) -- {why}. Proven by DIFF, not a list")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    check(hashlib.sha256(bytes(rt)).hexdigest() == base_sha,
          "restoring the attributed set reproduces the flown V98 BIT-FOR-BIT")

    print("\n  [14b] 🛑 THE CUMULATIVE NON-STOCK DELTA -- V99 vs HONDA, read from the IMAGES")
    print(f"       {'cell':>10s} {'stock':>8s} {'V98':>8s} {'V99':>8s}   what it is / which build")
    ledger = [
        (0xC40BC, 2, "Coulomb ramp normaliser -- knee position     **V99**"),
        (0xC63AC, 2, "ACTUAL accumulator IIR pole                  V97 -> REVERTED by V99"),
        (0xC40D2, 2, "K1, modelled Coulomb gain                    V89 (measured FLAT)"),
        (0xC6446, 2, "Lever B arm, r24 gate scale                  V88 (the ONLY measured fix)"),
        (0xC6CD0, 2, "the 4x forward LKAS gain                     V57/V31 lineage"),
        (0xC62EA, 2, "low-speed steer lockout (steer-to-zero)      V53"),
        (0xC61F6, 2, "r24 deadzone                                 pre-V38"),
        (0xC646C, 2, "shared sensor scale                          pre-V38"),
        (0xC4080, 2, "K0 -- NEVER RAISE                            stock, untouched"),
        (0xC407E, 2, "hard-fault interlock                         stock, untouched"),
        (0xC40D6, 2, "accel/inertia EMA -- VIRGIN                  stock, untouched"),
        (0xC63AE, 2, "LERP index scale -- VIRGIN                   stock, untouched"),
    ]
    for a, w, why in ledger:
        print(f"       0x{a:05X} {rdw(stock, a, w):8d} {rdw(base, a, w):8d} {rdw(code, a, w):8d}   "
              f"{why}")
    for a, w, why in ((0x3AA96, 1, "Lever B gate byte                            V88"),
                      (0x454FE, 1, "V42 state-4 byte -- MEASURED INERT           V42/V80")):
        print(f"       0x{a:05X} {rdw(stock, a, w):8d} {rdw(base, a, w):8d} {rdw(code, a, w):8d}   "
              f"{why}")
    n_stock_runs = len([1 for i in range(START, END) if code[i] != stock[i]])
    print(f"       (whole-image V99 vs STOCK: {n_stock_runs} differing bytes in "
          f"[0x{START:X},0x{END:X}), dominated by the {CAVE_LEN} B cave and the CRC trailers)")
    check(rdw(code, 0xC63AC, 2) == rdw(stock, 0xC63AC, 2),
          "⇒ after V99 the ACTUAL arm of the observer is BYTE-FOR-BYTE HONDA. The only non-Honda "
          "cells left on the observer structure are 0xC40D2 (V89) and 0xC40BC (V99), BOTH on the "
          "MODEL arm")

    # ==============================================================================================
    print("\n  [15] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V99 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V99_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            print("\n  [16] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V99 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk", ref=base)
            check(u16(sd, NORM_CELL) == NORM_TO,
                  f"🛑 shipped .rwd: THE LEVER 0x{NORM_CELL:X} == {NORM_TO} is in the artefact that "
                  f"will actually be flashed")
            check(u16(sd, POLE_CELL) == POLE_TO == u16(stock, POLE_CELL),
                  f"🛑 shipped .rwd: 0x{POLE_CELL:X} == {POLE_TO} == STOCK -- the revert landed")
            check(u16(sd, FRIC_EMA_CELL) / 4096.0 == u16(sd, POLE_CELL) / 1024.0,
                  "shipped .rwd: the alpha match is restored in the flashable artefact")
            check(u16(sd, K1_CELL) == 204 and u16(sd, K0_CELL) == 0 and u16(sd, 0xC407E) == 511,
                  "shipped .rwd: K1 = 204 (V89, carried), K0 = 0 (NEVER-RAISE) and the 0xC407E "
                  "interlock = 511 -- the cell V73 raised and V74/V75 hard-faulted on")
            check(u16(sd, 0xC6446) == 5244 and sd[0x3AA96] == 0xFB and sd[0x454FE] == 0xB5
                  and u16(sd, 0xC6CD0) == 3564,
                  "shipped .rwd: Lever B BOTH halves, 0x454FE = 0xB5, and the 4x gain = 3564")
            for m in MANUAL_MODES:
                check(rec_y(sd, m) == FRICTION_Y_STOCK, f"shipped .rwd: MANUAL mode {m} = STOCK")
            for m in ENGAGED_MODES:
                check(rec_y(sd, m) == FRICTION_Y_V92, f"shipped .rwd: ENGAGED mode {m} = V92 x1.5")
            check(rd(sd, CAVE_BASE, CAVE_LEN) == payload,
                  f"shipped .rwd: the {CAVE_LEN}-byte cave payload is byte-identical")
            check(all(b == 0xFF for b in sd[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
                  "shipped .rwd: the cave tail is virgin 0xFF")
            check(rd(sd, HOOK_ADDR, 4) == HOOK_BYTES, "shipped .rwd: the cave hook is unchanged")
            check(s16(sd, R427_ADDR) == -R427_SRC and rd(sd, R427_SAR_ADDR, 2) == R427_SAR,
                  "shipped .rwd: 427 is byte-identical to V98 -- ZERO 427 edits")
            check(sd[CAVE_BASE + IDENT_OFF] == 0x02 and sd[CAVE_BASE + IDENT_OFF + 1] == 0x3A,
                  f"🛑 shipped .rwd: the IDENTITY (`mov 0x2,r7` @+0x{IDENT_OFF:02X}) is present ⇒ "
                  f"b5 == 1 is live in the artefact that will actually be flashed")
            check(sd[CAVE_BASE + 0x4A] == 0x04,
                  "⭐ shipped .rwd: the b6 SET value is still 0x4 -- the primary instrument is "
                  "byte-identical to the build that produced the -0.321 slope")
            sd_listing = disassemble_cave(sd, CAVE_BASE, CAVE_LEN)
            check([(row[0], row[3].split()) for row in sd_listing]
                  == [(e[0], e[1].split()) for e in EXPECTED],
                  f"shipped .rwd: the cave RE-DISASSEMBLES to the same {len(EXPECTED)}-instruction "
                  f"rung table, offset for offset")
            sd_stores = [op for _, _, _, _, k, op, _, _ in sd_listing if k.startswith("st.")]
            check(sorted({d for _, d in sd_stores}) == sorted([-DST_B4, -DST_B7]),
                  f"🛑 shipped .rwd: the STORE SET re-disassembles to "
                  f"{{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} -- GATE 1 verified from the ARTEFACT")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

            print("\n  [17] 🛑 ARTEFACT UNIQUENESS -- every V99-matching file in both directories")
            stray_rwd = sorted(p for p in Path(RWD_DIR).iterdir()
                               if p.is_file() and "v99" in p.name.lower())
            stray_img = sorted(p for p in Path(ANALYSIS_ROOT).iterdir()
                               if p.is_file() and "v99" in p.name.lower())
            for p in stray_rwd + stray_img:
                mark = "  <-- THIS BUILD" if str(p) in (OUT, BIN_OUT) else "  🛑 STRAY"
                print(f"       {p.name}{mark}")
            check([str(p) for p in stray_rwd] == [OUT],
                  f"exactly ONE V99 .rwd in {RWD_DIR} (found {len(stray_rwd)})")
            check([str(p) for p in stray_img] == [BIN_OUT],
                  f"exactly ONE V99 image in {ANALYSIS_ROOT} (found {len(stray_img)})")
            check(hashlib.sha256(plain_image_path(BASE_NAME).read_bytes()).hexdigest() == BASE_SHA,
                  "🛑 the V98 base image is STILL byte-identical after the V99 cut -- untouched")

    print("\n" + "=" * 102)
    print(f"  V99 [{VARIANT_TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  THREE EDITS -- **4 DIFFERING BYTES** + 8 CRC trailer bytes: 0x{NORM_CELL:X} "
          f"{NORM_FROM}->{NORM_TO} (THE LEVER, 2 B) · 0x{POLE_CELL:X} {POLE_FROM}->{POLE_TO} "
          f"(REVERT TO HONDA, 1 B) · cave +0x{IDENT_OFF:02X} (IDENTITY, 1 B).")
    print(f"  🛑 CAVE: NO GROWTH. {CAVE_LEN} B / 59 instructions, unchanged. ONE instruction differs "
          f"from the flown V98 cave.")
    print(f"  🛑 GATE 2 IS NOT CLOSED for 0x{NORM_CELL:X} -- it needs L, which is UNMEASURED. A "
          f"stability failure here\n     is INVISIBLE to the fault system (V80: worst grinding "
          f"ever, a 30 s 27.4 Hz limit cycle, ZERO DTCs).")
    print(f"  ⚠ 0x{NORM_CELL:X} IS NOT ENGAGEMENT-GATED -- it acts in MANUAL too (V65's "
          f"'subwoofer... regardless of\n     LKAS engagement' is the precedent). Expect the "
          f"LKAS-off arm to feel different; that is the lever.")
    print(f"  ⚠ COMPOUNDED DOSE: with V89's K1 still on the car, delivered |friction| below "
          f"{knee_deg(NORM_TO):.2f} deg/s is\n     4.00x HONDA -- not 2x. Above "
          f"{knee_deg(NORM_FROM):.2f} deg/s it is arithmetically IDENTICAL to V98.")
    print(f"  🛑 IDENTITY IS A DUTY, NOT A SINGLE FRAME: b5 duty >= 0.999 AND byte7[7:6] == 2. "
          f"V98 measured\n     b5 duty 0.0022 over 17,982 frames. If the rule fails, NOTHING may "
          f"be reported.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
