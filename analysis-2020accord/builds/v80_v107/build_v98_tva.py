#!/usr/bin/env python3
r"""=================================================================================================
V98 -- THE COMPARATOR. Which ARM of the observer residual is the large one?
=================================================================================================

BASE: **V97** (`_v97_V96BASE-C63AC.102to150_plain_image.bin`) -- **the build ON THE CAR**, flown as
route 0x80, fault-free.  V98 = V97 + a cave rewrite and NOTHING else.

    🛑 ZERO calibration bytes.  ZERO 427 bytes.  ONE hook -- 0x14A's own, proven on V90/V92/V96/V97.

-------------------------------------------------------------------------------------------------
WHAT THIS BUILD IS -- AN INSTRUMENT, EXPLICITLY NOT A FIX
-------------------------------------------------------------------------------------------------
Nothing in V98 is claimed to improve the car.  It changes no control signal, no calibration and no
table.  It answers the one question the V97 session could not: **which of the three arms of the
observer residual actually dominates, in the operator's own regime.**

`FUN_00038148` @0x38236-0x3823A, coefficients EXACTLY +-1, verified from raw bytes
(`0x38238 subr r15,r6` opcode 0x0C; `0x3823A add r9,r6` opcode 0x0E):

    00038236  a432  sar   0x4,r6      r6 = gp-0x374c >> 4     <- the SIX-LANE sum, low-passed
    00038238  8f31  subr  r15,r6      r6 = gp-0x6bfe - r6         by 0xC63AC (= ALL OF V97)
    0003823a  c931  add   r9,r6       r6 = ... + gp-0x6bfa

    iVar6 =  gp-0x6bfe            MODEL    UNFILTERED   <-- V89's K1 (0xC40D2 = 204) acts HERE
           + gp-0x6bfa            REQUEST  UNFILTERED
           - (gp-0x374c >> 4)     ACTUAL                <-- V97's pole (0xC63AC = 150) acts HERE

**V89 moved one arm (K1 102 -> 204) and measured FLAT over 8 builds.  V97 moved the other
(0xC63AC 102 -> 150) and the operator felt nothing.  NEITHER ARM'S SHARE HAS EVER BEEN MEASURED.**
Both arms are estimates of the SAME quantity, in the SAME units, scaled by the SAME cal
(0xC6468 = 2639), entering a DIFFERENCE -- so a difference of two correlated estimates is smaller
than either, and **no bound on the split can be argued from admitted ranges**.  (The earlier
"<= 9 % share" bound was withdrawn for exactly that reason; it must not be quoted.)

-------------------------------------------------------------------------------------------------
WHY A COMPARATOR AND NOT A QUANTISER -- the structural fix for V96's failure class
-------------------------------------------------------------------------------------------------
V96 spent a 3-bit thermometer on `|gp-0x374c>>4|` sized against a guessed distribution.  It came
back **34x over-range**: `Mhi == 0` on 10,749/10,749 frames of route 80, `Mlo` duty 0.0000.  S1 and
S2 were VOID -- not because the hypothesis was wrong but because **we could not see it**.

    ⭐ WHEN YOU DO NOT KNOW A SIGNAL'S SCALE, DO NOT MEASURE IT -- COMPARE IT.

A comparator rung is **immune to UNDER-RANGED and OVER-RANGED by construction**: no LSB, no
ceiling, no assumed distribution.  It compares two values at FULL 32-bit precision INSIDE the cave,
before any quantisation exists.  `gp-0x374c` being small is then not a problem -- it is the
measurement.  This is the first comparator in the kit, and it is the direct answer to
*"we could not see it."*

-------------------------------------------------------------------------------------------------
THE PAYLOAD -- what each bit measures
-------------------------------------------------------------------------------------------------
    CAN 0x1AB / 427   🛑 UNCHANGED.  clamp(|gp-0x6b70| * 5 >> 6, 0, 1023).  ZERO 427 edits --
                      no 0x55DF2 repoint, no 0x55E10 rescale.  Measured healthy on THIS firmware
                      (route 80: 250 distinct codes, 0.000 % saturation, p99 239).  It carries
                      |resid| via the flash LERP, and f' from the same table -- for free.

    0x14A byte4 b7    gp-0x6b70 < 0                     UNCHANGED from V96/V97.  De-rectifies 427;
                                                        this exact rung has flown three routes.
    0x14A byte4 b6 ⭐ |gp-0x6bfe| >= |gp-0x374c>>4|     THE SHARE BIT -- MODEL vs ACTUAL.
    0x14A byte4 b5 ⭐ |gp-0x6bfa| >= |gp-0x374c>>4|     the same for REQUEST vs ACTUAL.
                                                        (b6,b5) ranks all three arms PER FRAME,
                                                        with NO scale assumption.
    0x14A byte4 b4    (gp-0x374c>>4) < 0                V96's OWN b6 rung, byte-identical ⇒ the
                                                        CONVERSE POSITIVE CONTROL (see below).
    0x14A byte4 b3    gp-0x6752 >= 0                    🛑 a DEPENDENCY, not a rider -- see below.
    0x14A byte7[7:6]  hard-wired 2                      BUILD IDENTITY + liveness positive control.

🛑 **WHY b3 IS NOT OPTIONAL.**  `gp-0x6752` is a signed char that multiplies the ENTIRE six-lane
sum at 0x381EE/0x381F6:

    target = ((sum6 * gp-0x6752 * 2639) >> 10) << 4
    ⇒  sign(gp-0x374c>>4)  =  sign(gp-0x6752) * sign(sum6)

⇒ **b4 measures a PRODUCT, and without b3 its physical meaning is ambiguous by a global sign
flip.**  That is exactly "probe the gate and the input, not just the output".  It also closes a
standing multi-session blocker: `sign(gp-0x6752)` has been called unreadable ("a +-1 EEPROM
constant") and it is not -- it is a live RAM signed byte with 49 readers and a whole 4-byte Honda
twin at 0x28F22.
⚠ [BELIEF] that |gp-0x6752| == 1.  The record says +-1, but 6 writers exist and the read
sign-extends, so +-2 and 0 are not excluded by structure.  b3 gives the SIGN, which is what b4
needs; the magnitude stays an assumption and is flagged here rather than assumed away.

-------------------------------------------------------------------------------------------------
🛑 PRE-REGISTERED SCORING PLAN -- declared HERE, BEFORE the flight
-------------------------------------------------------------------------------------------------
**PRIMARY ENDPOINT: the per-frame ORDERING of the three arms, from the (b6,b5) duties over the
engaged symptomatic frames.**  It is a duty, not a contrast, so the placebo floor, the 1.28 s onset
windows and the episode bootstrap do NOT bind -- there is no second arm to compare against.

    p     = duty of a comparator bit over engaged symptomatic frames
    n_eff = T / tau                        tau = the bit's correlation time
    SE(p) = sqrt( p(1-p) / n_eff )

      tau        n_eff at T = 17.2 s      SE at p = 0.5      SE at p = 0.9
      0.125 s    138                      0.043              0.026
      0.5   s     34                      0.086              0.051
      1.0   s     17  (PESSIMISTIC)       0.121              0.073

⇒ **~15-30 s of engaged symptomatic frames IS SUFFICIENT for the primary endpoint.**  Even at the
pessimistic 1 s correlation time, duties of 0.9 / 0.5 / 0.1 are separated by ~3 sigma.  What 17 s
resolves is the ORDERING.  What it does NOT resolve is a duty to better than ~+-12 %, which is not
the endpoint and is not claimed.  **Do not ask the operator for a longer drive.**

🛑 **THERE IS NO COMBINATION OF READINGS THAT LICENSES "UNINTERPRETABLE".**  Every bit is either a
hard constant (so its failure is diagnostic), a comparator (whose EVERY duty is a statement about
an ordering), or a rung with a PRIOR MEASUREMENT on this same firmware to check against.

  byte7[7:6] == 2   "This build is on the car."  Hard constant.  🛑 != 2 ⇒ NOTHING is reported.
  byte7[7:6] != 2   "The cave did not run, or the byte7 offset is wrong."

  b6 duty -> 1      "The MODEL arm exceeds the ACTUAL arm on essentially every frame ⇒ 0xC63AC and
                     the six lane weights move a MINOR arm; the Path-2 weight class is weakly
                     levered and the search should move to FUN_0003b8f6."
  b6 duty -> 0      "The ACTUAL arm dominates ⇒ Path-2 is WELL levered, V97 was correctly aimed,
                     and its null is about DOSE or DIRECTION, not REACH."
  b6 duty ~ 0.5     "The arms are comparable ⇒ both live, and the residual is a genuine difference
                     of two similar numbers -- the CANCELLATION regime."
  b5                the same three sentences for the REQUEST arm.

  🛑 ALL FOUR (b6,b5) CODES NAME A DIFFERENT ARM ORDERING.  None is "uninterpretable":
      (1,1)  |MODEL| >= |ACTUAL|  and  |REQUEST| >= |ACTUAL|   ⇒ ACTUAL is the SMALLEST arm.
                                                                 V97's whole lever sits on the
                                                                 minor term.  Move to FUN_0003b8f6.
      (0,0)  |MODEL| <  |ACTUAL|  and  |REQUEST| <  |ACTUAL|   ⇒ ACTUAL is the LARGEST arm.
                                                                 Path-2 IS the residual; V97's null
                                                                 is dose/direction, not reach.
      (1,0)  |MODEL| >= |ACTUAL| > |REQUEST|                    ⇒ MODEL vs ACTUAL is the live pair;
                                                                 REQUEST is the small one.  K1 and
                                                                 0xC63AC are the two live levers.
      (0,1)  |REQUEST| >= |ACTUAL| > |MODEL|                    ⇒ the LKAS REQUEST term dominates
                                                                 the residual.  Neither V89 nor V97
                                                                 was ever aimed at the big arm.
     ⚠ (b6,b5) read DIFFERENT numerators against a SHARED denominator, so **all four codes are
       reachable and none is a never-occurs validator.**  Stated rather than invented.

  b4 varies, 6-9 Hz phase vs wheel rate ~ +78 deg
                    ⭐ "The ACTUAL lane is live and the bit map is right."  THE CONVERSE POSITIVE
                     CONTROL -- see below.
  b4 railed         "The six-lane sum does not change sign during the symptom ⇒ it is a DC bias,
                     not a dynamic participant."  A real finding.

  b3 == 1           "gp-0x6752 >= 0; b4 reads sign(sum6) directly."
  b3 == 0           "gp-0x6752 < 0; every b4 sign flips, and the standing blocker is closed."
                     🛑 byte4 goes EVEN -- BY DESIGN, see the convention-break warning below.
  b3 varies         "gp-0x6752 is not static, or the bit offset is wrong."  Indicts the map.

  427 non-degenerate  |resid| and f' at the real operating point, via the flash LERP.
  427 pinned          "POS-2 failed; the analogue half is void and the cave half stands."
                      The two halves fail INDEPENDENTLY, on purpose.

🛑 **THE ONE WAY b6 CAN LIE, AND HOW THE READER DETECTS IT -- PRE-REGISTERED.**
`gp-0x6bfe` is a **GATED SENTINEL**: `FUN_0003bc20` plausibility-checks the model and, when
`|model| > 20000`, forces the cell to **`0x7FFF`** instead of a magnitude.  In that state
`|gp-0x6bfe| >= |gp-0x374c>>4|` reads TRUE for a reason that has **nothing to do with the share**,
and a naive duty would be quietly poisoned.
    ⇒ **THE DETECTOR IS FREE AND ALREADY ON THE WIRE.**  The latch forces `gp-0x6b70` to its rail,
      so **427 pins at exactly 1023** on precisely those frames.  **Score b6 ONLY on frames with
      427 != 1023, and report the excluded-frame count as a first-class output.**
    ⊕ It is not expected to fire: **427 == 1023 duty is 0 on 87,423 frames** across routes
      80 / 7e / 7f.  But the exclusion is pre-registered anyway, because "measured never" is not
      "structurally impossible".

⚠ **`gp-0x374c` STALENESS, noted and dismissed.**  A cave read concurrent with `FUN_00038148`'s own
read-modify-write can return a logically stale accumulator.  **An aligned `ld.w` is atomic on V850,
so there is NO TORN WORD** -- the exposure is staleness only, bounded by one 1 kHz tick, and benign
for telemetry.  ⊕ Interrupts are off across the cave, so the cave's THREE reads of `gp-0x374c`
cannot disagree with EACH OTHER, which is what the comparators actually require.

**SECONDARY (a bonus, explicitly NOT an acceptance criterion):** the 6-9 Hz band share from the
sign bits' coherence with |resid| and with column torque.  At 17 s that is ~13 windows; it may or
may not resolve.  **Reported with its exposure, NEVER as a verdict.**

**DROPPED, and not carried as future work:** hands-off return episodes (unbuildable under how the
operator drives) and any cross-build band ratio (60 builds of track record say it decides nothing).

-------------------------------------------------------------------------------------------------
POSITIVE CONTROLS AND VALIDATORS
-------------------------------------------------------------------------------------------------
POS-1  byte7[7:6] == 2 on >= 99.9 % of frames.  A hard-wired constant (`mov 0x2,r7`), not a
       measurand.  **If POS-1 fails, NOTHING in the readout is interpretable and nothing may be
       reported.**  V96's identical pattern read its constant on 100.0000 % of 164,096 frames.
POS-2  427 non-degenerate: >= 20 distinct codes, p99 >= 8.  Already MEASURED PASSING on this exact
       firmware (route 80: 250 codes, p99 239) because 427 is untouched.
POS-3  b3 CONSTANT across the drive.
R5b ⭐ **THE CONVERSE POSITIVE CONTROL -- a reading only possible if the mechanism is real.**
       POS-1 proves the INSTRUMENT is alive.  b4 proves the MECHANISM is: it is V96's own b6 rung,
       unchanged, and V96 measured `arg(B') - arg(rate) = +78.6 deg / +78.0 deg` on two independent
       routes.  **Reproducing +78 deg is a reading a broken bit map, a wrong offset or a dead lane
       CANNOT produce.**  This is the prior-registered, mechanism-specific control that V64 and V68
       lacked.

🛑 **VAL -- THE CONVENTION-BREAK WARNING, PRE-REGISTERED.**  The ~50-build *"byte4[7:3] is always
ODD"* convention **DOES NOT HOLD on this build.**  b3 is a MEASURAND, so **byte4 goes EVEN whenever
`gp-0x6752 < 0` -- and that is THE FINDING, not a fault.**  Liveness has moved to byte7.
**Without this pre-registration a scorer sees even values and pulls a working build.**

⚠ **The freeze detector is WEAKER than V96's, and that is a real regression I am not hiding.**
V96's freeze exclusion worked because a shut `gp-0x67fa` gate held BOTH members of its pair, so a
common-mode bit-exact hold was a strong detector.  Here `gp-0x6bfe` and `gp-0x6bfa` are written
OUTSIDE `FUN_00038148` and keep moving when the gate shuts; only the ACTUAL arm freezes.
⊕ Mitigating, and a genuine improvement in kind: a shut gate now produces a DISTINCTIVE ASYMMETRIC
signature -- b4 frozen while 427 and b6/b5 keep moving -- rather than a common-mode hold.
**Pre-registered rule: report the duty of `(b4 constant for >= 20 consecutive frames) AND (427 code
changing over the same span)` as a first-class output.**  Weaker than V96's, and labelled as one.

-------------------------------------------------------------------------------------------------
IDENTITY -- single-frame, structural, and its residual stated
-------------------------------------------------------------------------------------------------
**0x14A byte7[7:6] == 2 on ANY SINGLE FRAME proves V98.**
  * Builds <= V91 never write byte 7 at all ⇒ byte7[7:6] == 0.  EXCLUDED, structurally.
  * **V96 and V97 -- the builds actually on the car -- hard-wire byte7 b6 == 1** (`mov 0x1,r7`,
    measured 1 on 100.0000 % of 164,096 frames) ⇒ they can only produce {1,3}.  EXCLUDED,
    structurally.  This is exactly the gap that made route 80 "V96-or-V97" and cost a session.
  * ⚠ **Residual, stated: V92 can also produce 2.**  A shelf artefact that is not a flash
    candidate.  **I am NOT claiming a structural separation from V92.**
  * Cost: **ZERO extra cave bytes** -- it is V96's `mov 0x1,r7` with a different immediate.
  🛑 **AND THE HONEST ANSWER TO "IS 2 BITS ENOUGH": NO.**  byte7 has 4 codes and V96/V97 already
  burn {1,3}.  This scheme gives EXACTLY ONE clean generation; the build after this one has only
  {1,3} left, both ambiguous.  A durable field needs >= 3 bits and its own `0x18F` hook --
  **as its own build**, never bolted onto a new measurement class.  That is how V24/V27/V48B
  bricked ECUs.  **This build ships the 2-bit interim.**

-------------------------------------------------------------------------------------------------
🛑 GATE 1 -- RAM OWNERSHIP.  ZERO NEW RAM.  PURE LOADS ONLY.
-------------------------------------------------------------------------------------------------
**The STORE SET is IDENTICAL to V96's flown cave: {gp-0x1514, gp-0x1511}.**  Nothing else in memory
is written.  Every new access is a pure LOAD, and a load has no side effect.

    cell         writers                      readers   V98 adds   profile
    gp-0x6bfe    FUN_0003bc20 @0x3BC3E, SOLE  1R         1 reader  1R/1W -- the same profile as
                                                                   gp-0x374c, which V96 FLEW
    gp-0x6bfa    FUN_00026c80, 3 st.h         2R         1 reader  2R/3W. Writer clamps to +-20000
                 (each paired with a lockstep                      and shadows each store at
                  shadow at gp-0x4cfa)                             gp-0x4cfa
    gp-0x374c    FUN_00038148 @0x38230        1R         3 readers ALREADY READ TWICE by V96's
                                                                   FLOWN cave (0xC4B40, 0xC4B78)
                                                                   -- EMPIRICAL clearance
    gp-0x6752    5 writers, none in the       51R        a 52nd    boot-parsed, shadow-validated
                 control path                                      STATIC in {-1, 0, +1}
    gp-0x6b70    FUN_00038148 @0x382D2        1R         1 reader  V96/V97 already read it

🛑 **CORRECTION TO THE COUNTS THIS BUILD WAS BRIEFED WITH: `gp-0x6752` is 51 R / 5 W, NOT
"49 readers / 6 writers", and NOT 55 sites.**  The five *named* writer addresses were right; the
counts were a hand miscount.  The 56th candidate site `0x2A90A` is a READ inside an unanalysed gap
-- the **seventh** recorded reproduction of `search_instructions` undercounting while reporting
`truncated:false`.
⚠ **And a tool caveat that invalidates a whole class of evidence on this program:** Ghidra's memory
map here is a single flat `ram: 0x00000000-0x000FFFFF` with **no block at `0xFEDF____`**, so
`get_xrefs_to` / `list_globals` / `audit_global` can **never** answer a gp-cell ownership question.
**Any zero they return is a TOOL ZERO, not a fact.**  Every count above rests on raw LE byte scans
adjudicated against `search_instructions`/`disassemble_function`.

Results of the mandatory wider scan, for the record: **67 accesses across the four cells, ZERO
span-only hits** -- every access is exact, and the filter was proven live by correctly rejecting
the near-misses `st.h -0x374e` and `st.w -0x3748`.  The 6-byte extended form exists only for
`gp-0x6752` (4 sites in `FUN_00048a40`; Ghidra independently agreed `length:6`), zero for the other
three.  Address synthesis: 0 literal-32-bit hits and 0 `movhi` with `0xFEDF`/`0xFEE0`, from a
detector validated by finding 7,647 `movhi` candidates image-wide -- so the zero is a fact, not a
filter artefact.  All 58 peripheral base addresses live in `0x40000000-0x407EC000`, none in
`0xFEDF____`, so **the loads are side-effect-free**.

🛑 **THE WIDER 32-BIT SCAN IS MANDATORY AND WAS RUN.**  A scan keyed on st.b/st.h whose hw2 equals
the exact displacement is **structurally blind to a 32-bit access at a DIFFERENT displacement
covering the same byte** -- the method gap V96 itself found (`ld.w`/`st.w -0x1514[gp]` at
0x2194A/0x21964, benign but invisible to the narrow method).  Both methods -- GhidraMCP AND an
independent whole-image Python LE byte scan of every store encoding, including the 6-byte extended
gp-relative form and the `hw2 = disp|1` and `ld.bu` op-field parity traps -- were run and
set-differenced.  🛑 **Static clearance is NOT sufficient on its own: `gp-0x1500` passed both
static methods and still failed on-car.**  What carries the weight here is that the store set is
byte-identical to a cave that has FLOWN four routes.

-------------------------------------------------------------------------------------------------
🛑 GATE 2 -- CLOSED-LOOP STABILITY
-------------------------------------------------------------------------------------------------
1. **NO CONTROL SIGNAL IS MODIFIED AT ALL ⇒ the phase added to every control loop is EXACTLY 0
   degrees.**  This is not the sentence that shipped V94 ("a scalar on an existing term adds ZERO
   phase" -- true, irrelevant, and about an edit that DID alter a control signal).  Here the cave's
   stores are {gp-0x1514, gp-0x1511}, **no control-path instruction reads either byte**, and the
   store set is read back from the BUILT IMAGE'S OWN RE-DISASSEMBLY, not from this source file.
2. **ZERO calibration bytes.**  Asserted cell by cell against the V97 image AND by a
   zero-unattributed whole-image diff restricted to [0x13000, 0x100000).
3. **ZERO 427 bytes.**  0x55DF2 and 0x55E10 are asserted byte-identical to V97.
4. The cave hangs off the **100 Hz** CAN-TX builder, not the 1 kHz control task.  V92 flew 43
   instructions at this site (route 79) and V96/V97 flew 43 at the identical site (routes 7e/7f/80),
   all fault-free.  V98 runs **59** instructions there -- see the DI-window pricing below.
5. Untouched and asserted: 0xC4080 (K0, the NEVER-RAISE relay hazard), 0xC407E (Honda's 511 hard-
   fault interlock), the shaper, and all four authority-curve records.
6. 🛑 **0xC63AC stays at V97's 150 and 0xC40D2 stays at V89's 204.**  This build MEASURES what those
   two levers act on; it does not move either of them.

-------------------------------------------------------------------------------------------------
🛑 CAVE DISCIPLINE -- V24, V27 and V48B all BRICKED the ECU.  Every cave byte is risk.
-------------------------------------------------------------------------------------------------
⚠ **GROWTH IS STATED, NOT CLAIMED AWAY: 112 B -> 154 B (+42 B, +37.5 %), 43 -> 59 instructions.**
  Extent 0xC4B34 .. 0xC4FF0 = **1212 B free**; 154 B is **12.7 %** of it.  V90 -> V92 already grew
  74 -> 116 B and flew fault-free.  **This build does NOT claim NO-GROWTH.**

★ **WHY IT GREW: a comparator is TWO-OPERAND and V96's cave had only r6/r7.**  Two paths were
  priced.  **Path 1 was taken, as the conservative default**: recompute `|gp-0x374c>>4|` inside
  each comparator rung and pay one extra read-modify-write of `gp-0x1514`.  That keeps V96's proven
  `r6`/`r7` register discipline EXACTLY and makes **no new liveness claim at the hook**.  Path 2
  (prove a third scratch register dead) would have been ~28 B smaller but is a NEW liveness claim,
  and `r8`/`r10` are known LIVE across the hook (`0x55C20 andi 0xf,r10,r8`).
  ⊕ `r7` needs no new claim: `0x55C12` = `083a` = **`mov 0x8,r7`**, the instruction immediately
  after the hook, overwrites it. Read out of the image, not inherited.

  🛑 **A CORRECTION TO THE SPEC, RECORDED SO IT IS NOT RE-MADE.**  `SPEC §R8` priced path 1 at
  *"+~10 B per rung, ~+20 B total ⇒ cave 125-135 B"*.  **That under-prices it, and the shortfall is
  structural, not arithmetic.**  Recomputing the denominator does not solve the register problem at
  all: at the moment of the SECOND comparison the cave must hold `|ACTUAL|`, `|A_2|` **and the
  first comparator's result** -- **three live values in two registers**, which is impossible no
  matter how many times the denominator is recomputed.  The real cost of path 1 is therefore the
  recomputation **plus an extra read-modify-write**, and the cave lands at **154 B, not 135 B**.
  **The store SET is unchanged; there is one additional store INSTRUCTION to a cell the cave
  already owned**, and the two masks are asserted to partition the byte.

★ **NO NEW BRANCH CONDITION.**  The cave uses exactly `{bge, bnh}` -- V92's and V96's set.  The
  comparator gets the CORRECT polarity from `bge` alone by the *assume-set-then-clear* idiom
  (`cmp` / `mov <bit>,r7` / `bge +4` / `mov 0x0,r7`).  A `blt`/`bh`/`bl` form would have been a new
  condition and the recorded `ba05`/`b205` (`bne` vs `be`) inversion hazard.  b3 reuses V96's own
  proven `addi -imm,r6,r0` + `bnh` unsigned-range idiom, proven **by exhaustion over all 256 byte
  values**, not argued.
  ✅ **`cmp rA,rB` sets flags from `rB - rA`, and `bge` is taken iff `rB >= rA` signed** --
  confirmed three independent ways across two branch families, and independently re-read here from
  Honda's own `cmp r0,r28` at `0x22672` (`e0e1`: reg2=28, op=0x0F, reg1=0) whose following `be`
  skips iff `r28 == 0`.  ⇒ **the comparators do NOT invert.**  That was the single biggest semantic
  risk in the build.

🛑 **THE PSW HAZARD, AND WHY IT IS CHECKED MECHANICALLY RATHER THAN BY EYE.**
  The assume-set-then-clear idiom is only correct because `mov imm5` is **flag-transparent**, and it
  fails **silently** -- producing a plausible-looking duty rather than an obvious fault -- if any
  arithmetic slips into the `cmp` -> `bge` gap.  **Two of this cave's own twins DO update the PSW:
  `add 0x1,r7` and `sar 0x4,r6`.**  So the build walks the BUILT image's own decode, finds the
  nearest flag-setter before every branch, and asserts the gap is PSW-transparent:
      9 windows · 7 adjacent · 2 containing exactly one `mov imm5` · 0 violations
      `add 0x1,r7` appears ONCE, at +0x64, and is the CONSEQUENCE of the +0x62 branch, not
      something scheduled into a gap.  All three `sar 0x4,r6` (+0x10/+0x40/+0x5E) are IMMEDIATELY
      followed by the `cmp 0x0,r6` that re-establishes the flags, so their PSW writes are dead.
  ⚠ **`mov`'s flag transparency is [BELIEF], not [EVIDENCE].**  It rests on the SLEIGH model plus
  Honda's own compiled code scheduling a `mov` into exactly this gap (`0x1BD32`, `0x1539A`,
  `0x1A7B6`) -- **not on a quotation from the V850E2 manual.**  That is the one open gap in this
  build, and it should be closed against the manual before any flash decision.

★ **EVERY non-trivial byte is copied from a Ghidra-verified instruction, and the source address is
  recorded for each.**  Coverage is asserted 154/154.  The traps this defeats:
    * `subr r0,r6` is `8031`.  The hand-derived `3080` is **`satsubr`**, which SATURATES instead of
      negating and corrupts |v| on NEGATIVES ONLY -- a defect that survives a flight.
    * 🛑 `ld.h X[gp],rN` and `ld.w X[gp],rN` **SHARE hw1**; the class is decided **SOLELY by hw2
      bit 0**, and this cave deliberately uses BOTH.  The image contains its own A/B with identical
      hw1: `0x381FE` `2437 b5c8` (hw2 ODD ⇒ `ld.w`) against `0x55DF0` `2437 e893` (hw2 EVEN ⇒
      `ld.h`).  Our `gp-0x6bfe` / `gp-0x6bfa` twins both carry EVEN hw2 ⇒ both correctly `ld.h`.
      ⚠ **Cite `0x55DF0` for its hw1 `2437` ONLY, never for its displacement** -- `0x55DF2` is the
      kit's own CAN-427 repoint cell and has moved every few builds (stock `e893` = `gp-0x6c18` ->
      V87 `6894` -> V90 `da94` -> V92 `4294` -> V96/V97 `9094`).  The hw1 is stock and unchanged.
    * ⚠ **A raw byte hit is NOT a twin.**  Roughly **1 in 6** of this session's scan candidates was
      not at an instruction boundary at all (`0x20CB8`, `0x1E41E`, `0x1B9DA` -- no instruction, no
      function).  `0x1E41E` was this build's FIRST choice for `cmp r6,r7`.  Only the twelve
      Ghidra-certified addresses are used.
    * `ld.b` (sign-extending) vs `ld.bu` (zero-extending) -- b3 needs the SIGN-extending form and
      takes the whole 4-byte Honda twin `0437ae98` @0x28F22.

🛑 **THE CAVE RUNS WITH INTERRUPTS DISABLED -- DECODED, NOT ASSERTED.**  The Format-V jarl
   displacements around the hook decode to 0x55C0A -> 0x1FA42 (DI) and 0x55C2E -> 0x1FA72 (EI),
   with the hook at 0x55C0E between them.  V98 lengthens that DI window by **16 instructions**.
   Priced: 59 straight-line instructions, no call/loop/divide/float, ~15 of them 4-byte loads;
   at the V850E2's clock that is on the order of **~1-2 microseconds**, against a **1000 us**
   control-task period and a **10 ms** CAN-TX period.  ⊕ DTC 0x18 is **BOOT-ONLY** (a reset-cause
   REPORT, not a live deadline monitor), so caves have **no 0x18 timing budget** to blow.
   ⊕ The atomicity is a BENEFIT here: the cave's three reads of `gp-0x374c` cannot disagree.

-------------------------------------------------------------------------------------------------
CLASS, AGAINST THE WHOLE ARC SINCE V38 -- what is genuinely new
-------------------------------------------------------------------------------------------------
V38-V52 authority/filters/poles/caves · V53-V61 telemetry + lane mutes · V62-V73 the rate lane ·
V74-V83a the base-assist damper · V84-V86B damper reverts + phase · V87 subtractive · V88 Lever B ·
V89 plant model (K1) · V90 instrument · V91/V92 0xCBE74 x1.5 · V93/V94 0xCBE74 CUT (ABORTED) ·
V96 instrument + revert · V97 the first LOOP POLE.

**V98 is the first RELATIONAL instrument in the arc.**  Every probe since V53 has telemetered the
VALUE of one signal -- a sign, a magnitude, a thermometer, a gate.  V98 telemeters a **RELATION
BETWEEN TWO SIGNALS**, evaluated at full precision inside the ECU.  That is a different class, and
it exists because the value-class failed in a specific, diagnosed way (V96's 34x over-range).
🛑 It is **NOT** a re-run of an earlier lever in a different direction -- it moves **no lever at
all**.  `0xC63AC` has been at V97's 150 for **1** build; `0xC40D2` at V89's 204 since V89 -- **8**
builds carried, V98 the 9th.  The six lane weights `0xC63A0`-`0xC63AA` are all at 1024, and **five
of them (`0xC63A2`..`0xC63AA`) are VIRGIN across every image in the kit**; `0xC63A0` moved over
V72-V81 and has been back at 1024 since V83a.  **V98 moves none of them, and that is the point:
it prices the class before a fifth build is spent inside it.**

WHAT THIS BUILD CONCLUDES FROM ~17 s -- none of it needs a second drive or a matched arm:
  1. The ORDERING of the three arms of the observer residual, per frame, with no scale assumption.
     **Never measured on any build.**
  2. |resid| and f' at the real operating point, from 427 through the flash LERP -- what V96 was
     built to get and failed to get, here for free from a channel already flying.
  3. Whether 0xC63AC (V97) and the six virgin lane weights sit on the MAJOR or the MINOR arm ⇒
     whether that class is worth another build, or the search moves to FUN_0003b8f6.
  4. sign(gp-0x6752) -- a standing multi-session blocker, closed permanently.
  5. Whether the ACTUAL arm is a dynamic participant or a DC bias during the symptom.
  6. WHICH BUILD IS ON THE CAR -- single-frame and structural, for the first time since V96.

WHAT THE OPERATOR IS ASKED TO DO:
  **One parking-lot creep, LKAS engaged, hands on, exactly as he already drives it -- and he should
  STOP THE MOMENT HE FEELS THE SYMPTOM, as he said he would.**  ~15-30 s of engaged symptomatic
  frames is enough.  No matched arms, no episode counts, no second drive, no highway.
  ⊕ If free: a few seconds of the same creep with LKAS OFF strengthens the reading; the primary
  endpoint does not depend on it.
  ⊕ Context for interpreting anything at that speed: route 80's median engaged speed is 5.13 km/h,
  right on the knee of 0xC62EA = 320 ~ 5 km/h -- Honda's low-speed steer lockout, which this kit
  has held at 0 since V53/V81.
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
WRITE_MODE = os.environ.get("ACCORD_V98_WRITE", "").strip().lower()

TP = 0xBF000                       # 🛑 tp+0x73ac = 0xC63AC, NOT 0xC73AC (off-by-0x1000, 5 times)

BASE_NAME = "_v97_V96BASE-C63AC.102to150_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))

# =================================================================================================
# THE SOURCE CELLS -- named constants so swapping one is a ONE-LINE change.
# =================================================================================================
SRC_427 = 0x6B70        # gp-0x6b70   Stage-2 output / the PID reference.  b7.  Also CAN 427.
SRC_MODEL = 0x6BFE      # gp-0x6bfe   the observer MODEL arm, UNFILTERED.  b6 numerator.
SRC_REQ = 0x6BFA        # gp-0x6bfa   the 11-slot REQUEST aggregator, UNFILTERED.  b5 numerator.
SRC_ACC = 0x374C        # gp-0x374c   the Stage-1 accumulator = the ACTUAL arm.  Shared denominator.
SRC_POL = 0x6752        # gp-0x6752   the signed polarity constant multiplying the six-lane sum.
DST_B4 = 0x1514         # gp-0x1514   CAN 0x14A byte 4   (~50 flown builds)
DST_B7 = 0x1511         # gp-0x1511   CAN 0x14A byte 7   (V92/V96/V97)

ACC_FW_SHIFT = 4        # the firmware's OWN >>4 at 0x38236 -- mirrored EXACTLY
POL_THRESHOLD = 0x80    # b3 = (sext8(gp-0x6752) <u 128) == (gp-0x6752 >= 0)
IDENTITY_CODE = 2       # byte7[7:6].  V96/V97 burn {1,3}; builds <= V91 give 0.

MASK_B4_PASS1 = 0x00DF  # pass 1 writes bit 5 only        -> preserve 7,6,4,3 and Honda 2:0
MASK_B4_PASS2 = 0x0027  # pass 2 writes bits 7,6,4,3      -> preserve 5 (pass 1) and Honda 2:0
MASK_B7 = 0x003F        # byte7 writes bits 7:6           -> preserve Honda 5:0

# =================================================================================================
# THE CAVE
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V96_CAVE = bytes.fromhex(
    "003a243790946032ae05483a2437b5c8a4326032ae05443a6032ae058031ac32"
    "6332a30503320639c43a8437b3980606e4ffa305483a8437edeac63607000731"
    "4437ecea2437b5c8a4326032ae058031aa32c6360200013a0639c63aa437efea"
    "c6363f0007314437efea2436e8ea7f00")

PAYLOAD = bytes.fromhex(
    # =============================================================================================
    # PASS 1 -- the REQUEST comparator.  byte4 b5 = (|gp-0x6bfa| >= |gp-0x374c>>4|)
    # =============================================================================================
    "24370694"      # +0x00  ld.h  -0x6bfa[gp],r6     the REQUEST arm  (sign-extends)
    "6032" "ae05"   # +0x04  cmp 0x0,r6 / bge +4 -> +0x0A
    "8031"          # +0x08  subr  r0,r6              r6 = |REQUEST|   (NOT satsubr 3080)
    "0638"          # +0x0A  mov   r6,r7              r7 = |REQUEST|   -- frees r6 for the denom
    "2437b5c8"      # +0x0C  ld.w  -0x374c[gp],r6     the ACTUAL arm, 32-bit
    "a432"          # +0x10  sar   0x4,r6             the FIRMWARE's OWN >>4 (0x38236)
    "6032" "ae05"   # +0x12  cmp 0x0,r6 / bge +4 -> +0x18
    "8031"          # +0x16  subr  r0,r6              r6 = |ACTUAL|
    "e639"          # +0x18  cmp   r6,r7              flags = r7 - r6 = |REQUEST| - |ACTUAL|
    "023a"          # +0x1A  mov   0x2,r7             ASSUME SET.  🛑 `mov imm5` does NOT touch PSW
    "ae05"          # +0x1C  bge   +4 -> +0x20        taken iff |REQUEST| >= |ACTUAL| ⇒ KEEP
    "003a"          # +0x1E  mov   0x0,r7             else CLEAR
    "c43a"          # +0x20  shl   0x4,r7             -> bit 5
    "8437edea"      # +0x22  ld.bu -0x1514[gp],r6
    "c636" "df00"   # +0x26  andi  0xdf,r6,r6         clear ONLY bit 5; keep 7,6,4,3 and Honda 2:0
    "0731"          # +0x2A  or    r7,r6
    "4437ecea"      # +0x2C  st.b  r6,-0x1514[gp]     CAN 0x14A byte 4, pass 1
    # =============================================================================================
    # PASS 2 -- the MODEL comparator + the three single-operand rungs.  b7, b6, b4, b3
    # =============================================================================================
    "24370294"      # +0x30  ld.h  -0x6bfe[gp],r6     the MODEL arm  (sign-extends)
    "6032" "ae05"   # +0x34  cmp 0x0,r6 / bge +4 -> +0x3A
    "8031"          # +0x38  subr  r0,r6              r6 = |MODEL|
    "0638"          # +0x3A  mov   r6,r7              r7 = |MODEL|
    "2437b5c8"      # +0x3C  ld.w  -0x374c[gp],r6     the ACTUAL arm, RE-READ (atomic: DI is on)
    "a432"          # +0x40  sar   0x4,r6
    "6032" "ae05"   # +0x42  cmp 0x0,r6 / bge +4 -> +0x48
    "8031"          # +0x46  subr  r0,r6              r6 = |ACTUAL|
    "e639"          # +0x48  cmp   r6,r7             flags = r7 - r6 = |MODEL| - |ACTUAL|
    "043a"          # +0x4A  mov   0x4,r7             ASSUME SET -- pre-shift bit 2 -> byte4 b6
    "ae05"          # +0x4C  bge   +4 -> +0x50        taken iff |MODEL| >= |ACTUAL| ⇒ KEEP
    "003a"          # +0x4E  mov   0x0,r7             else CLEAR
    "24379094"      # +0x50  ld.h  -0x6b70[gp],r6     Stage-2 output / the PID reference
    "6032" "ae05"   # +0x54  cmp 0x0,r6 / bge +4 -> +0x5A
    "483a"          # +0x58  add   0x8,r7             b7 = (gp-0x6b70 < 0)  -- V96's rung, UNCHANGED
    "2437b5c8"      # +0x5A  ld.w  -0x374c[gp],r6     the ACTUAL arm, third read
    "a432"          # +0x5E  sar   0x4,r6
    "6032" "ae05"   # +0x60  cmp 0x0,r6 / bge +4 -> +0x66
    "413a"          # +0x64  add   0x1,r7             b4 = ((gp-0x374c>>4) < 0)  -- V96's OWN b6 rung
    "c43a"          # +0x66  shl   0x4,r7             -> bits 7, 6, 4   (bit 5 stays 0, pass 1 owns it)
    "0437ae98"      # +0x68  ld.b  -0x6752[gp],r6     the POLARITY CONSTANT  (SIGN-extends)
    "0606" "80ff"   # +0x6C  addi  -0x80,r6,r0        flags only; CY|Z == (r6 >=u 128)
    "a305"          # +0x70  bnh   +4 -> +0x74        skip iff gp-0x6752 < 0
    "483a"          # +0x72  add   0x8,r7             b3 = (gp-0x6752 >= 0)  -> bit 3
    "8437edea"      # +0x74  ld.bu -0x1514[gp],r6
    "c636" "2700"   # +0x78  andi  0x27,r6,r6         keep bit 5 (pass 1) and Honda's bits 2:0
    "0731"          # +0x7C  or    r7,r6
    "4437ecea"      # +0x7E  st.b  r6,-0x1514[gp]     CAN 0x14A byte 4, pass 2
    # =============================================================================================
    # byte 7 -- THE BUILD IDENTITY.  A CONSTANT, not a measurand.
    # =============================================================================================
    "023a"          # +0x82  mov   0x2,r7             🛑 IDENTITY: byte7[7:6] == 2, hard-wired
    "c63a"          # +0x84  shl   0x6,r7             -> 0x80
    "a437efea"      # +0x86  ld.bu -0x1511[gp],r6
    "c636" "3f00"   # +0x8A  andi  0x3f,r6,r6         keep Honda's bits 5:0
    "0731"          # +0x8E  or    r7,r6
    "4437efea"      # +0x90  st.b  r6,-0x1511[gp]     CAN 0x14A byte 7
    # =============================================================================================
    # return
    # =============================================================================================
    "2436e8ea"      # +0x94  movea -0x1518,gp,r6      restore the hooked instruction
    "7f00")         # +0x98  jmp   [lp]

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp -- V90/V92/V96/V97's
DI_CALL_ADDR, DI_TARGET = 0x55C0A, 0x1FA42                   # jarl FUN_0001fa42  (interrupts OFF)
EI_CALL_ADDR, EI_TARGET = 0x55C2E, 0x1FA72                   # jarl FUN_0001fa72  (interrupts ON)
CKSUM_CALL_ADDR = 0x55C18                                    # jarl FUN_00057b24(gp-0x1518,8,0x14a)

# 🛑 427 IS UNTOUCHED.  Asserted, not assumed.
R427_ADDR, R427_SRC = 0x55DF2, SRC_427       # hw2 of `ld.h ..[gp],r6` inside the 0x1AB builder
R427_SAR_ADDR, R427_SAR = 0x55E10, bytes.fromhex("a632")     # sar 0x6,r6 -- V96/V97's, CARRIED

# =================================================================================================
# 🛑 EVERY BYTE OF THE PAYLOAD, AND THE ADDRESS IT IS COPIED FROM.  Coverage asserted 154/154.
#    `CAVE_BASE + k` sources are V96's OWN payload, present in the V97 base image and FLOWN on
#    routes 7e / 7f / 80.  Everything else is a Honda instruction in this same image.
# =================================================================================================
# 🛑 THESE FIVE ARE THE **GHIDRA-CERTIFIED** ADDRESSES, and four of them are NOT the ones a raw
#    byte scan first offered.  A raw byte hit is NOT a twin: ~1 in 6 of the scan's candidates was
#    not at an instruction boundary at all (0x20CB8, 0x1E41E, 0x1B9DA -- no instruction, no
#    function).  0x1E41E in particular was this build's FIRST choice for `cmp r6,r7` and is one of
#    the three duds.  Each address below is certified by Ghidra as a real instruction inside a
#    defined function, and each is byte-identical between STOCK (the analysed program) and V97.
TWIN_MOV_R6_R7 = 0x14EEE     # `mov r6,r7`   0638   Format I reg-reg move
TWIN_CMP_R6_R7 = 0x1BD96     # `cmp r6,r7`   e639   flags = r7 - r6  (reg2 - reg1)
TWIN_MOV_4_R7 = 0x1A79C      # `mov 0x4,r7`  043a
TWIN_MOV_2_R7 = 0x1708C      # `mov 0x2,r7`  023a
TWIN_ADD_1_R7 = 0x15404      # `add 0x1,r7`  413a   🛑 SETS THE PSW -- see the PSW-window check

TWINS = [
    # ---- PASS 1 --------------------------------------------------------------------------------
    (0x00, 2, CAVE_BASE + 0x02, "ld.h hw1 `2437` (gp,r6)        V96 cave +0x02 (FLOWN) -- an ld.h"),
    (0x02, 2, 0x3820A, "hw2 -0x6bfa `0694`             HONDA @0x38208 `ld.h -0x6bfa[gp],r7` --"
                       " hw2 of a real ld.h, bit 0 CLEAR ⇒ ld.h, not ld.w"),
    (0x04, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V96 cave +0x06"),
    (0x06, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x08, 2, CAVE_BASE + 0x1C, "subr  r0,r6  `8031`            V96 cave +0x1C  🛑 NOT satsubr 3080"),
    (0x0A, 2, TWIN_MOV_R6_R7, "mov   r6,r7  `0638`            HONDA -- Format I reg-reg move"),
    (0x0C, 4, 0x381FE, "ld.w  -0x374c[gp],r6           HONDA: FUN_00038148's OWN read of the"
                       " accumulator -- whole 4 bytes, so ld.w vs ld.h cannot be got wrong"),
    (0x10, 2, 0x38236, "sar   0x4,r6 `a432`            HONDA @0x38236 -- the FIRMWARE's OWN"
                       " (gp-0x374c >> 4), same register"),
    (0x12, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V96 cave +0x06"),
    (0x14, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x16, 2, CAVE_BASE + 0x1C, "subr  r0,r6                    V96 cave +0x1C"),
    (0x18, 2, TWIN_CMP_R6_R7, "cmp   r6,r7  `e639`            HONDA -- flags = r7 - r6"),
    (0x1A, 2, TWIN_MOV_2_R7, "mov   0x2,r7 `023a`            HONDA"),
    (0x1C, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x1E, 2, CAVE_BASE + 0x00, "mov   0x0,r7 `003a`            V96 cave +0x00"),
    (0x20, 2, CAVE_BASE + 0x28, "shl   0x4,r7 `c43a`            V96 cave +0x28"),
    (0x22, 4, CAVE_BASE + 0x36, "ld.bu -0x1514[gp],r6           V96 cave +0x36, whole"),
    (0x26, 2, CAVE_BASE + 0x3A, "andi hw1 `c636` (imm,r6,r6)    V96 cave +0x3A"),
    # +0x28 the imm16 0x00DF -- DERIVED, pure data, see DERIVED_IMM
    (0x2A, 2, CAVE_BASE + 0x3E, "or    r7,r6  `0731`            V96 cave +0x3E"),
    (0x2C, 4, CAVE_BASE + 0x40, "st.b  r6,-0x1514[gp]           V96 cave +0x40, whole"),
    # ---- PASS 2 --------------------------------------------------------------------------------
    (0x30, 2, CAVE_BASE + 0x02, "ld.h hw1 `2437` (gp,r6)        V96 cave +0x02"),
    (0x32, 2, 0x3821A, "hw2 -0x6bfe `0294`             HONDA @0x38218 `ld.h -0x6bfe[gp],r15` --"
                       " hw2 of a real ld.h, bit 0 CLEAR ⇒ ld.h"),
    (0x34, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V96 cave +0x06"),
    (0x36, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x38, 2, CAVE_BASE + 0x1C, "subr  r0,r6                    V96 cave +0x1C"),
    (0x3A, 2, TWIN_MOV_R6_R7, "mov   r6,r7  `0638`            HONDA"),
    (0x3C, 4, 0x381FE, "ld.w  -0x374c[gp],r6           HONDA @0x381FE, whole"),
    (0x40, 2, 0x38236, "sar   0x4,r6                   HONDA @0x38236"),
    (0x42, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V96 cave +0x06"),
    (0x44, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x46, 2, CAVE_BASE + 0x1C, "subr  r0,r6                    V96 cave +0x1C"),
    (0x48, 2, TWIN_CMP_R6_R7, "cmp   r6,r7  `e639`            HONDA"),
    (0x4A, 2, TWIN_MOV_4_R7, "mov   0x4,r7 `043a`            HONDA"),
    (0x4C, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x4E, 2, CAVE_BASE + 0x00, "mov   0x0,r7                   V96 cave +0x00"),
    (0x50, 4, CAVE_BASE + 0x02, "ld.h  -0x6b70[gp],r6           V96 cave +0x02, WHOLE -- the exact"
                                " 4 bytes that have flown routes 7e/7f/80 (Honda twin @0x55DF0)"),
    (0x54, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V96 cave +0x06"),
    (0x56, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x58, 2, CAVE_BASE + 0x0A, "add   0x8,r7 `483a`            V96 cave +0x0A"),
    (0x5A, 4, 0x381FE, "ld.w  -0x374c[gp],r6           HONDA @0x381FE, whole"),
    (0x5E, 2, 0x38236, "sar   0x4,r6                   HONDA @0x38236"),
    (0x60, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V96 cave +0x06"),
    (0x62, 2, CAVE_BASE + 0x08, "bge   +4                       V96 cave +0x08"),
    (0x64, 2, TWIN_ADD_1_R7, "add   0x1,r7 `413a`            HONDA"),
    (0x66, 2, CAVE_BASE + 0x28, "shl   0x4,r7                   V96 cave +0x28"),
    (0x68, 4, 0x28F22, "ld.b  -0x6752[gp],r6           HONDA @0x28F22 -- WHOLE 4 bytes; 49 readers"
                       " exist, and ld.b SIGN-extends where ld.bu would not"),
    (0x6C, 2, CAVE_BASE + 0x2E, "addi hw1 `0606` (imm,r6,r0)    V96 cave +0x2E (Honda @0x498E0) --"
                                " r0 = discard, flags only"),
    # +0x6E the imm16 -0x80 -- DERIVED, pure data, see DERIVED_IMM
    (0x70, 2, CAVE_BASE + 0x32, "bnh   +4     `a305`            V96 cave +0x32"),
    (0x72, 2, CAVE_BASE + 0x0A, "add   0x8,r7                   V96 cave +0x0A"),
    (0x74, 4, CAVE_BASE + 0x36, "ld.bu -0x1514[gp],r6           V96 cave +0x36, whole"),
    (0x78, 2, CAVE_BASE + 0x3A, "andi hw1 `c636`                V96 cave +0x3A"),
    # +0x7A the imm16 0x0027 -- DERIVED, pure data, see DERIVED_IMM
    (0x7C, 2, CAVE_BASE + 0x3E, "or    r7,r6                    V96 cave +0x3E"),
    (0x7E, 4, CAVE_BASE + 0x40, "st.b  r6,-0x1514[gp]           V96 cave +0x40, whole"),
    # ---- byte 7 --------------------------------------------------------------------------------
    (0x82, 2, TWIN_MOV_2_R7, "mov   0x2,r7 `023a`            HONDA  🛑 THE IDENTITY CONSTANT"),
    (0x84, 2, CAVE_BASE + 0x5A, "shl   0x6,r7 `c63a`            V96 cave +0x5A"),
    (0x86, 4, CAVE_BASE + 0x5C, "ld.bu -0x1511[gp],r6           V96 cave +0x5C, whole"),
    (0x8A, 4, CAVE_BASE + 0x60, "andi  0x3f,r6,r6               V96 cave +0x60, whole (imm too)"),
    (0x8E, 2, CAVE_BASE + 0x64, "or    r7,r6                    V96 cave +0x64"),
    (0x90, 4, CAVE_BASE + 0x66, "st.b  r6,-0x1511[gp]           V96 cave +0x66, whole"),
    # ---- return --------------------------------------------------------------------------------
    (0x94, 6, CAVE_BASE + 0x6A, "movea -0x1518,gp,r6 / jmp [lp] V96 cave +0x6A, the return"),
]

# 🛑 The ONLY payload bytes with no twin: three pure-data imm16 halfwords.  No encoding ambiguity
#    exists in an imm16 -- it is struct.pack and nothing else.  Each is DERIVED from the constant
#    the rung map requires, asserted here AND again from the built image.
DERIVED_IMM = [
    (0x28, lambda: struct.pack("<H", MASK_B4_PASS1),
     f"andi imm16 = 0x{MASK_B4_PASS1:04X} ⇒ pass 1 clears ONLY byte4 bit 5 and preserves bits "
     f"7,6,4,3 (pass 2's) and Honda's 2:0"),
    (0x6E, lambda: struct.pack("<h", -POL_THRESHOLD),
     f"addi imm16 = -0x{POL_THRESHOLD:02X} ⇒ after this add, CY|Z == (r6 >=u {POL_THRESHOLD}); "
     f"`bnh` takes CY|Z, so b3 = (sext8(gp-0x6752) < {POL_THRESHOLD} unsigned) = (gp-0x6752 >= 0)"),
    (0x7A, lambda: struct.pack("<H", MASK_B4_PASS2),
     f"andi imm16 = 0x{MASK_B4_PASS2:04X} ⇒ pass 2 preserves byte4 bit 5 (pass 1's b5) and "
     f"Honda's bits 2:0, and clears the four bits it owns"),
]

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  Asserted on the base, on the built image, and on the shipped .rwd.
# 🛑 V98 writes ZERO calibration bytes, so EVERY one of these is asserted EQUAL TO THE V97 IMAGE.
# =================================================================================================
FROZEN = {
    0xC63AC: (2, 150, "🛑 V97's LOOP POLE -- the ACTUAL arm's IIR. V98 MEASURES it, does NOT move it"),
    0xC40D2: (2, 204, "🛑 V89's K1 -- the MODEL arm's Coulomb gain. MEASURED FLAT; carried, not moved"),
    0xC40BC: (2, 600, "🛑 Coulomb relay gate -- 6000 measured 2.3x WORSE. Do not restore"),
    0xC4080: (2, 0, "🛑 K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK CLAMP -- Honda's 511, one under its own 512 trip"),
    0xC40D0: (2, 408, "friction EMA alpha (16.7 Hz)"),
    0xC40D4: (2, 573, "observer torque IIR -- V86 took it to 286 and was FALSIFIED"),
    0xC40D6: (2, 246, "🛑 accel/inertia IIR -- VIRGIN 92/92. Same branch V86 nulled. NOT touched"),
    0xC40D8: (2, 3686, "gp-0x4f60 IIR -- a NO-OP (-0.6 deg). Kill any proposal to move it"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0 -- lane measured ~0; frozen since V83a"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN. NOT this build"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN. A cliff edge, not a lever"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e -- lane PROVABLY == 0"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS lane"),
    0xC63AE: (2, 1024, "🛑 Stage-2 input scale -- index == |iVar6| exactly. Never 0"),
    0xC6200: (2, 8192, "🛑 gp-0x6b70's OUTPUT CLAMP"),
    0xC6468: (2, 2639, "model output gain -- SHARED, scales BOTH arms of the residual"),
    0xC6446: (2, 5244, "🛑 Lever B ARM -- silently reverted at a rebase THREE times"),
    0x3AA96: (1, 0xFB, "🛑 Lever B GATE -- both halves or neither"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
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
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC64A1: (1, 1, "🛑 READ-ONLY"),
    0xE547C: (2, None, "🛑 AUTHORITY CURVE -- virgin on all 99 images. NOT touched"),
    0xE5404: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE52FC: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE5284: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xC520C: (2, None, "🛑 governor rate ceiling -- V40 BRICKED on a neighbour. NOT touched"),
}

# 🛑 the friction DOSE family the brief names explicitly -- V92's x1.5 on the ENGAGED columns.
#    The record addresses are DEREFERENCED from the pointer array, never hard-coded, then the
#    dereferenced addresses are themselves asserted against the named ones.
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_N_MODES = 34
REC_X_OFF, REC_Y_OFF, REC_LEN = 0x02, 0x08, 0x10
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_X = (0, 1280, 5760)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)
# 🛑 the named addresses are the **Y-ARRAY** addresses (record base + REC_Y_OFF), NOT the record
#    bases -- mode 24's record is at 0xD6A64 and its Y triple at 0xD6A6C. Resolved by dereferencing
#    the pointer array and adding the offset, then asserted; an eyeballed record base would be
#    8 bytes wrong and would silently read the X breakpoints instead.
DOSE_FAMILY_Y = {24: 0xD6A6C, 26: 0xD7A5C, 27: 0xD7A6C}

VARIANT_TOKEN = "V97BASE-CAVE.CMP.6BFE.6BFA.374C-POL.6752-ID.BYTE7.2"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v98_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V98-{TAG}-0x{START:X}-0x{END:X}.rwd")

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    """Every assertion prints a BOOLEAN. A check that produces no output is not a check that passed."""
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


def rec_addr(buf, mode):
    """🛑 DEREFERENCE. An address is not a mode. Never hard-code a record address."""
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


def assert_frozen(buf, label, ref=None):
    """`want is None` means 'must equal the reference image', for cells whose value is not declared."""
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = u16(buf, a) if w == 2 else buf[a]
        exp = want if want is not None else (u16(ref, a) if w == 2 else ref[a])
        if got != exp:
            bad.append((a, got, exp, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


# =================================================================================================
# A V850E2 decoder covering exactly the formats this cave uses. It exists so the script
# RE-DISASSEMBLES THE PAYLOAD FROM THE BUILT IMAGE and checks it against the RUNG TABLE, rather
# than checking the bytes against the string it was handed.
# 🛑 op 0x00 (`mov reg1,reg2`) is NEW in V98 and is NOT in V96's decoder -- V96 never used it.
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


# 🛑 PSW MODEL. Which instruction kinds UPDATE the condition flags, and which are TRANSPARENT.
#    This build's comparator idiom puts a `mov` between the `cmp` and the `bge`, so the whole rung
#    is only correct if `mov` is transparent -- and it is silently WRONG, not obviously broken, if
#    anything arithmetic slips into that gap. `add 0x1,r7` and `sar 0x4,r6` are BOTH twins used by
#    this cave and BOTH set the PSW, so the window is checked MECHANICALLY below, not by eye.
PSW_SETTERS = {"cmp", "cmp_r", "add", "addi", "sar", "shl", "shr", "subr", "or", "andi"}
PSW_TRANSPARENT = {"mov", "mov_r", "movea", "ld.h", "ld.w", "ld.b", "ld.bu", "ld.hu",
                   "st.b", "st.h", "st.w", "jmp"}


def assert_psw_windows(listing):
    """For EVERY branch, walk back to the nearest flag-setter and prove the gap is transparent.

    ⚠ `mov`'s flag-transparency is [BELIEF], not [EVIDENCE]: it rests on the SLEIGH model plus
    Honda's own compiled code scheduling `mov` into exactly this gap (0x1bd32, 0x1539a, 0x1a7b6),
    not on a quotation from the V850E2 manual. Recorded as the one open gap before any flash.
    """
    rows, bad, windows = list(listing), [], []
    for i, (off, _, _, text, kind, _, _, _) in enumerate(rows):
        if kind != "branch":
            continue
        j = i - 1
        gap = []
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

    🛑 This is the DIFFERENTIAL GATE-2 proof: run it on the BUILT image and on STOCK and diff.
    A scan keyed on one displacement is structurally blind to a 32-bit access at a DIFFERENT
    displacement covering the same byte -- the method gap V96 itself found -- so this keys on the
    STORE OPCODE and reports whatever displacement it finds.
        op 0x3A = st.b (disp16 whole)   op 0x3B = st.h (hw2 bit0 == 0) / st.w (bit0 == 1)
    reg1 == 4 selects gp as the base register.
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


def disassemble_cave(img, base, length):
    out, off = [], 0
    while off < length:
        text, n, kind, operand, writes, refs = decode(img, base + off)
        out.append((off, base + off, rd(img, base + off, n).hex(), text, kind, operand,
                    writes, refs))
        off += n
    assert off == length, f"the last instruction overruns the payload by {off - length} byte(s)"
    return out


# The rung table, as INTENT. The built image is checked against THIS, not against the payload hex.
EXPECTED = [
    # ---- PASS 1: b5 = |gp-0x6bfa| >= |gp-0x374c>>4| ---------------------------------------------
    (0x00, "ld.h  -0x6bfa[gp],r6", "the REQUEST arm, UNFILTERED"),
    (0x04, "cmp   0x0,r6", ""), (0x06, "bge   +4", "-> +0x0A"),
    (0x08, "subr  r0,r6", "r6 = |REQUEST|"),
    (0x0A, "mov   r6,r7", "r7 = |REQUEST| -- frees r6 for the shared denominator"),
    (0x0C, "ld.w  -0x374c[gp],r6", "the ACTUAL arm, 32-bit"),
    (0x10, "sar   0x4,r6", "the FIRMWARE's own >>4 @0x38236"),
    (0x12, "cmp   0x0,r6", ""), (0x14, "bge   +4", "-> +0x18"),
    (0x16, "subr  r0,r6", "r6 = |ACTUAL|"),
    (0x18, "cmp   r6,r7", "flags = r7 - r6 = |REQUEST| - |ACTUAL|"),
    (0x1A, "mov   0x2,r7", "ASSUME SET -- `mov imm5` does NOT touch the PSW"),
    (0x1C, "bge   +4", "-> +0x20, taken iff |REQUEST| >= |ACTUAL| ⇒ KEEP"),
    (0x1E, "mov   0x0,r7", "else CLEAR"),
    (0x20, "shl   0x4,r7", "-> byte4 bit 5"),
    (0x22, "ld.bu -0x1514[gp],r6", ""),
    (0x26, "andi  0xdf,r6,r6", "clear ONLY bit 5"),
    (0x2A, "or    r7,r6", ""),
    (0x2C, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4, pass 1"),
    # ---- PASS 2: b6, b7, b4, b3 -----------------------------------------------------------------
    (0x30, "ld.h  -0x6bfe[gp],r6", "the MODEL arm, UNFILTERED"),
    (0x34, "cmp   0x0,r6", ""), (0x36, "bge   +4", "-> +0x3A"),
    (0x38, "subr  r0,r6", "r6 = |MODEL|"),
    (0x3A, "mov   r6,r7", "r7 = |MODEL|"),
    (0x3C, "ld.w  -0x374c[gp],r6", "the ACTUAL arm, re-read (atomic -- interrupts are off)"),
    (0x40, "sar   0x4,r6", ""),
    (0x42, "cmp   0x0,r6", ""), (0x44, "bge   +4", "-> +0x48"),
    (0x46, "subr  r0,r6", "r6 = |ACTUAL|"),
    (0x48, "cmp   r6,r7", "flags = |MODEL| - |ACTUAL|"),
    (0x4A, "mov   0x4,r7", "ASSUME SET -- pre-shift bit 2 -> byte4 b6"),
    (0x4C, "bge   +4", "-> +0x50, taken iff |MODEL| >= |ACTUAL| ⇒ KEEP"),
    (0x4E, "mov   0x0,r7", "else CLEAR"),
    (0x50, "ld.h  -0x6b70[gp],r6", "Stage-2 output / the PID reference"),
    (0x54, "cmp   0x0,r6", ""), (0x56, "bge   +4", "-> +0x5A"),
    (0x58, "add   0x8,r7", "b7 = gp-0x6b70 < 0   -- V96's rung, UNCHANGED"),
    (0x5A, "ld.w  -0x374c[gp],r6", "third read"),
    (0x5E, "sar   0x4,r6", ""),
    (0x60, "cmp   0x0,r6", ""), (0x62, "bge   +4", "-> +0x66"),
    (0x64, "add   0x1,r7", "b4 = (gp-0x374c>>4) < 0   -- V96's OWN b6 rung"),
    (0x66, "shl   0x4,r7", "-> bits 7, 6, 4"),
    (0x68, "ld.b  -0x6752[gp],r6", "the POLARITY CONSTANT -- SIGN-extends"),
    (0x6C, f"addi  {-POL_THRESHOLD:#x},r6,r0", "flags only; CY|Z = (r6 >=u 128)"),
    (0x70, "bnh   +4", "-> +0x74, skip iff gp-0x6752 < 0"),
    (0x72, "add   0x8,r7", "b3 = (gp-0x6752 >= 0) -> bit 3"),
    (0x74, "ld.bu -0x1514[gp],r6", ""),
    (0x78, "andi  0x27,r6,r6", "keep bit 5 (pass 1) and Honda's 2:0"),
    (0x7C, "or    r7,r6", ""),
    (0x7E, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4, pass 2"),
    # ---- byte 7: THE IDENTITY -------------------------------------------------------------------
    (0x82, "mov   0x2,r7", "🛑 THE IDENTITY -- a CONSTANT, not a measurand"),
    (0x84, "shl   0x6,r7", "-> bits 7:6 = 0b10 = 2"),
    (0x86, "ld.bu -0x1511[gp],r6", ""),
    (0x8A, "andi  0x3f,r6,r6", "keep Honda's bits 5:0"),
    (0x8E, "or    r7,r6", ""),
    (0x90, "st.b  r6,-0x1511[gp]", "CAN 0x14A byte 7"),
    # ---- return ---------------------------------------------------------------------------------
    (0x94, "movea -0x1518,gp,r6", "restore the hooked instruction"),
    (0x98, "jmp   [lp]", ""),
]

M32 = 0xFFFFFFFF


def s32(v):
    """Wrap to a 32-bit signed value -- the register width the cave actually works in."""
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def _abs_rung(v):
    """`cmp 0x0,rN / bge +4 / subr r0,rN` -- the cave's abs, in 32-bit register arithmetic."""
    return s32(0 - v) if not v >= 0 else v


def wire_byte4(x6b70, x6bfe, x6bfa, acc32, pol, honda_bits=0x7):
    """Mirrors the cave's integer arithmetic EXACTLY, one line per instruction offset.

    `acc32` is the 32-bit signed value of gp-0x374c; `pol` is the RAW BYTE at gp-0x6752.
    Returns the delivered CAN 0x14A byte 4, both passes applied in order.
    """
    out = honda_bits & 0x7

    # ---- PASS 1 --------------------------------------------------------------------------------
    r6 = s32(x6bfa)                                  # +0x00 ld.h   (SIGN-EXTENDS)
    r6 = _abs_rung(r6)                               # +0x04/+0x06/+0x08   r6 = |REQUEST|
    r7 = r6                                          # +0x0A mov r6,r7
    r6 = s32(acc32)                                  # +0x0C ld.w   (full 32 bits)
    r6 = r6 >> ACC_FW_SHIFT                          # +0x10 sar 0x4   -- Python >> IS arithmetic
    r6 = _abs_rung(r6)                               # +0x12/+0x14/+0x16  r6 = |ACTUAL|
    #  +0x18 `cmp r6,r7` sets flags from r7 - r6.  +0x1A `mov 0x2,r7` does NOT touch the PSW.
    #  +0x1C `bge` is taken iff r7 >= r6 signed ⇒ the SET value survives.
    b5 = 2 if r7 >= r6 else 0                        # +0x1A/+0x1C/+0x1E
    r7 = (b5 << 4) & M32                             # +0x20 shl 0x4      -> bit 5
    out = (out & MASK_B4_PASS1) | (r7 & 0xFF)        # +0x22..+0x2C  ld.bu / andi / or / st.b
    out &= 0xFF

    # ---- PASS 2 --------------------------------------------------------------------------------
    r6 = s32(x6bfe)                                  # +0x30 ld.h
    r6 = _abs_rung(r6)                               # +0x34/+0x36/+0x38  r6 = |MODEL|
    r7 = r6                                          # +0x3A mov r6,r7
    r6 = s32(acc32)                                  # +0x3C ld.w
    r6 = r6 >> ACC_FW_SHIFT                          # +0x40 sar 0x4
    r6 = _abs_rung(r6)                               # +0x42/+0x44/+0x46  r6 = |ACTUAL|
    r7 = 4 if r7 >= r6 else 0                        # +0x48/+0x4A/+0x4C/+0x4E   b6, pre-shift bit 2
    r6 = s32(x6b70)                                  # +0x50 ld.h
    if not r6 >= 0:          r7 += 8                 # +0x54/+0x56/+0x58   b7, pre-shift bit 3
    r6 = s32(acc32) >> ACC_FW_SHIFT                  # +0x5A/+0x5E
    if not r6 >= 0:          r7 += 1                 # +0x60/+0x62/+0x64   b4, pre-shift bit 0
    assert 0 <= r7 <= 0xD and (r7 & 0x2) == 0, \
        "the pass-2 accumulator escaped bits 3,2,0 -- bit 1 belongs to pass 1's b5"
    r7 = (r7 << 4) & M32                             # +0x66 shl 0x4   -> bits 7, 6, 4
    p = pol & 0xFF                                   # +0x68 ld.b -- but the RUNG only needs the byte
    #  +0x6C `addi -0x80,r6,r0`: CY is the carry-OUT of a 32-bit add, so CY|Z == (r6 >=u 128).
    #  For a SIGN-EXTENDED byte, r6 >=u 128 <=> the byte is NEGATIVE (0xFFFFFF80..0xFFFFFFFF).
    #  +0x70 `bnh` takes CY|Z ⇒ the add is skipped exactly when gp-0x6752 < 0.
    r6u = (p - 256) & M32 if p >= 0x80 else p        # the sign-extended value, as unsigned 32
    if not r6u >= POL_THRESHOLD: r7 += 8             # +0x72 add 0x8,r7   b3 -> bit 3
    out = (out & MASK_B4_PASS2) | (r7 & 0xFF)        # +0x74..+0x7E
    return out & 0xFF


def wire_byte7(honda_bits=0x3F):
    """byte 7 is a CONSTANT -- it takes no measurand at all. That is the whole point."""
    r7 = IDENTITY_CODE                               # +0x82 mov 0x2,r7
    return ((honda_bits & MASK_B7) | ((r7 << 6) & M32)) & 0xFF      # +0x84 shl 0x6


def decode_wire(b4, b7):
    """The SCORER's reconstruction, written here so it is pre-registered WITH the build."""
    ident = (b7 >> 6) & 0x3
    b6, b5 = bool(b4 & 0x40), bool(b4 & 0x20)
    order = {(True, True): "ACTUAL is the SMALLEST arm  (MODEL>=ACTUAL, REQUEST>=ACTUAL)",
             (False, False): "ACTUAL is the LARGEST arm  (MODEL<ACTUAL, REQUEST<ACTUAL)",
             (True, False): "MODEL >= ACTUAL > REQUEST",
             (False, True): "REQUEST >= ACTUAL > MODEL"}[(b6, b5)]
    return dict(identity=ident, valid=(ident == IDENTITY_CODE),
                sign_6b70=-1 if (b4 & 0x80) else +1,
                model_ge_actual=b6, request_ge_actual=b5, ordering=order,
                sign_actual=-1 if (b4 & 0x10) else +1,
                polarity_nonneg=bool(b4 & 0x08))


def assert_rung_semantics():
    """Every rung proven by EXHAUSTION or by a corner grid, before a single byte is written."""
    # ---- b3, the polarity rung: EXHAUSTIVE over all 256 byte values ------------------------------
    bad = [p for p in range(256)
           if bool(wire_byte4(0, 0, 0, 0, p) & 0x08) != (p < 0x80)]
    assert not bad, f"the polarity rung is wrong at {bad[:8]}"
    print(f"    ✅ b3 == (gp-0x{SRC_POL:04X} >= 0) on ALL 256 byte values -- the `addi "
          f"{-POL_THRESHOLD:#x},r6,r0` + `bnh` unsigned-range idiom on a SIGN-EXTENDED `ld.b` is "
          f"proven BY EXHAUSTION, not argued. No `blt`, no new branch condition")

    # ---- the comparators: a corner grid over both signs and every tie -----------------------------
    acts, arms = [], []
    for k in (0, 1, 2, 3, 7, 15, 16, 100, 511, 512, 2047, 2048, 4095, 8192, 20000, 32767):
        acts += [k << ACC_FW_SHIFT, -(k << ACC_FW_SHIFT), (k << ACC_FW_SHIFT) + 15,
                 -((k << ACC_FW_SHIFT) + 15)]
        arms += [k, -k]
    acts += [0, 1, -1, 15, -15, 1 << 30, -(1 << 30), -(1 << 31), (1 << 31) - 1]
    arms += [-32768, 32767, 0]
    acts, arms = sorted(set(acts)), sorted(set(arms))
    n, seen65 = 0, set()
    for a70 in (-8192, -1, 0, 1, 8192):
        for mdl in arms:
            for req in arms:
                for acc in acts:
                    for pol in (1, 0xFF):
                        w4 = wire_byte4(a70, mdl, req, acc, pol)
                        w7 = wire_byte7()
                        act = abs(s32(acc) >> ACC_FW_SHIFT)
                        assert bool(w4 & 0x80) == (a70 < 0), "b7 is not sign(gp-0x6b70)"
                        assert bool(w4 & 0x40) == (abs(mdl) >= act), "b6 is not |MODEL| >= |ACTUAL|"
                        assert bool(w4 & 0x20) == (abs(req) >= act), "b5 is not |REQ| >= |ACTUAL|"
                        assert bool(w4 & 0x10) == ((s32(acc) >> ACC_FW_SHIFT) < 0), \
                            "b4 is not sign(gp-0x374c>>4)"
                        assert bool(w4 & 0x08) == (pol < 0x80), "b3 is not (gp-0x6752 >= 0)"
                        assert w4 & 0x07 == 0x07, "Honda's byte4 bits 2:0 were not preserved"
                        assert w7 & 0x3F == 0x3F, "Honda's byte7 bits 5:0 were not preserved"
                        assert (w7 >> 6) == IDENTITY_CODE, "🛑 THE IDENTITY IS NOT 2"
                        d = decode_wire(w4, w7)
                        assert d["valid"] and d["model_ge_actual"] == (abs(mdl) >= act) \
                            and d["request_ge_actual"] == (abs(req) >= act), \
                            "the scorer's reconstruction does not round-trip"
                        seen65.add((bool(w4 & 0x40), bool(w4 & 0x20)))
                        n += 1
    print(f"    ✅ {n:,} corner cases, ZERO deviations. Both comparators are EXACT `>=` (ties "
          f"included) at full 32-bit precision, over accumulators to +-2^31 and arms to +-32768 -- "
          f"there is NO LSB, NO CEILING and NO assumed distribution to over- or under-range")
    assert seen65 == {(0, 0), (0, 1), (1, 0), (1, 1)}, f"only {sorted(seen65)} reachable"
    print(f"    ✅ ALL FOUR (b6,b5) codes are REACHABLE and each names a DIFFERENT arm ordering ⇒ "
          f"🛑 no reading is 'uninterpretable'.  ⚠ and therefore NONE of them is a never-occurs "
          f"validator -- stated rather than invented (they share a denominator, not a numerator)")

    # ---- the tie case, called out because `>` vs `>=` is where a comparator silently rots --------
    for v in (0, 1, 100, 2048):
        assert wire_byte4(0, v, v, (v << ACC_FW_SHIFT), 1) & 0x60 == 0x60, \
            f"the |arm| == |ACTUAL| TIE at {v} does not read 1 -- the rung is `>`, not `>=`"
    print(f"    ✅ the TIE |arm| == |ACTUAL| reads 1 on both comparators (the rung is `>=`, not "
          f"`>`) -- checked explicitly because 0 == 0 is a REACHABLE tie at rest")

    # ---- byte7 is a constant: prove it cannot be moved by ANY measurand --------------------------
    codes7 = {wire_byte7(h) >> 6 for h in range(64)}
    assert codes7 == {IDENTITY_CODE}, f"byte7[7:6] reachable set is {sorted(codes7)}"
    print(f"    ✅ byte7[7:6] == {IDENTITY_CODE} on EVERY input and every Honda bit pattern ⇒ the "
          f"IDENTITY is STRUCTURAL, not measurand-dependent. V96/V97 can only produce {{1,3}} and "
          f"builds <= V91 only 0 ⇒ ONE FRAME separates this build from the one on the car")

    # ---- the convention break, asserted so it cannot be discovered on the road -------------------
    par = {wire_byte4(0, 0, 0, 0, p) & 0x08 for p in range(0x80, 0x100)}
    assert par == {0x00}, "b3 does not go 0 for a NEGATIVE polarity byte"
    print(f"    ✅ 🛑 PRE-REGISTERED CONVENTION BREAK: if gp-0x{SRC_POL:04X} < 0 then b3 == 0 and "
          f"**byte4[7:3] goes EVEN**. The ~50-build 'always ODD' convention DOES NOT HOLD here. "
          f"That is THE FINDING, not a fault -- liveness has moved to byte7")


def build():
    print("=" * 102)
    print("  V98 -- THE COMPARATOR.  Which ARM of the observer residual is the large one?")
    print("  🛑 AN INSTRUMENT, NOT A FIX.  ZERO calibration bytes.  ZERO 427 bytes.  CAVE ONLY.")
    print("=" * 102)

    # ==============================================================================================
    # 1. THE BASE
    # ==============================================================================================
    print("\n  [1] THE BASE -- V97, the build ON THE CAR")
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    check(base_sha == BASE_SHA, f"base is V97, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(len(stock) == 0x100000, "stock reference dump loaded")

    # ==============================================================================================
    # 2. THE ADDRESSES -- computed, never eyeballed
    # ==============================================================================================
    print("\n  [2] ADDRESS ARITHMETIC -- computed, never eyeballed (off-by-0x1000 has recurred 5x)")
    check(TP + 0x73AC == 0xC63AC,
          f"tp(0x{TP:X}) + 0x73AC == 0xC63AC  (NOT 0x{TP + 0x1000 + 0x73AC:X}) -- V97's cell")
    check(u16(base, 0xC63AC) == 150 and u16(stock, 0xC63AC) == 102,
          "0xC63AC reads 150 on the base and 102 on STOCK -- the anchor that proves the tp offset")
    for cell, want in ((0xC64DF, 100), (0xC6468, 2639), (0xC63AE, 1024),
                       (0xC40D2, 204), (0xC40BC, 600), (0xC4080, 0)):
        got = base[cell] if cell == 0xC64DF else u16(base, cell)
        check(got == want, f"anchor 0x{cell:X} == {want} on the base")
    for name, d in (("SRC_MODEL", SRC_MODEL), ("SRC_REQ", SRC_REQ), ("SRC_ACC", SRC_ACC),
                    ("SRC_427", SRC_427), ("SRC_POL", SRC_POL)):
        check(((-d) & 0xFFFF) % 2 == 0,
              f"{name}: disp16 for gp-0x{d:04X} is 0x{(-d) & 0xFFFF:04X}, EVEN -- an odd one would "
              f"select ld.w over ld.h (they share hw1)")

    # ==============================================================================================
    # 3. THE STRUCTURE -- the three arms, read out of the base image's own bytes
    # ==============================================================================================
    print("\n  [3] THE THREE-ARM SUBTRACTION, read from the BASE IMAGE, not from a claim")
    check(rd(base, 0x38236, 2) == bytes.fromhex("a432"),
          "0x38236 = `sar 0x4,r6` -- the ACTUAL arm's >>4, mirrored EXACTLY by the cave")
    check(rd(base, 0x38238, 2) == bytes.fromhex("8f31"),
          "0x38238 = `subr r15,r6` opcode 0x0C ⇒ iVar6 = gp-0x6bfe - (gp-0x374c>>4). COEFF -1 EXACT")
    check(rd(base, 0x3823A, 2) == bytes.fromhex("c931"),
          "0x3823A = `add r9,r6`   opcode 0x0E ⇒ ... + gp-0x6bfa.               COEFF +1 EXACT")
    check(rd(base, 0x38218, 4) == bytes.fromhex("247f0294"),
          "0x38218 = `ld.h -0x6bfe[gp],r15` -- the MODEL arm's ONLY reader; its hw2 is our twin")
    check(rd(base, 0x38208, 4) == bytes.fromhex("243f0694"),
          "0x38208 = `ld.h -0x6bfa[gp],r7`  -- the REQUEST arm's ONLY reader; its hw2 is our twin")
    check(rd(base, 0x381FE, 4) == bytes.fromhex("2437b5c8"),
          "0x381FE = `ld.w -0x374c[gp],r6`  -- the ACTUAL arm, whole 4-byte twin (V96 flew it)")
    check(rd(base, 0x28F22, 4) == bytes.fromhex("0437ae98"),
          "0x28F22 = `ld.b -0x6752[gp],r6`  -- the POLARITY byte, whole 4-byte Honda twin")
    check(rd(base, 0x55DF0, 4) == bytes.fromhex("24379094"),
          "0x55DF0 = `ld.h -0x6b70[gp],r6`  -- a real ld.h into r6, the hw1 class anchor")
    for a in (0x38202,):
        check(rd(base, a, 4) == bytes.fromhex("e56fad73"),
              f"0x{a:X} = `ld.hu 0x73ad[tp],r13` -- V97's pole, hw2 = 0x73AC|1 (the parity trap)")

    # ==============================================================================================
    # 4. THE CAVE REGION AND THE HOOK -- unchanged from the build that is flying
    # ==============================================================================================
    print("\n  [4] THE CAVE REGION AND ITS HOOK")
    check(rd(base, CAVE_BASE, len(V96_CAVE)) == V96_CAVE,
          f"V96 cave 0x{CAVE_BASE:05X}-0x{CAVE_BASE + len(V96_CAVE) - 1:05X} "
          f"({len(V96_CAVE)} B) byte-exact on the base -- the FLOWN payload, our twin source")
    check(all(b == 0xFF for b in base[CAVE_BASE + len(V96_CAVE):CAVE_FREE_END]),
          f"0x{CAVE_BASE + len(V96_CAVE):05X}-0x{CAVE_FREE_END:05X} all virgin 0xFF")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"cave hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp UNCHANGED")
    hk1, hk2 = u16(base, HOOK_ADDR), u16(base, HOOK_ADDR + 2)
    check(HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2) == CAVE_BASE,
          f"the hook's disp22 DECODES to 0x{HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2):05X} == the "
          f"cave base -- derived from the bytes, not assumed")

    def jarl_target(a):
        """🛑 Format-V disp22 is SIGNED. The DI/EI calls branch BACKWARD, so a naive unsigned
        decode returns 0x41FA42 instead of 0x1FA42 -- caught by this very assertion."""
        h1, h2 = u16(base, a), u16(base, a + 2)
        d = ((h1 & 0x3F) << 16) | h2
        return a + (d - 0x400000 if d & 0x200000 else d)

    check(jarl_target(DI_CALL_ADDR) == DI_TARGET and jarl_target(EI_CALL_ADDR) == EI_TARGET
          and DI_CALL_ADDR < HOOK_ADDR < EI_CALL_ADDR,
          f"🛑 INTERRUPTS ARE OFF ACROSS THE CAVE: 0x{DI_CALL_ADDR:05X} jarl -> "
          f"0x{jarl_target(DI_CALL_ADDR):05X} (DI) and 0x{EI_CALL_ADDR:05X} jarl -> "
          f"0x{jarl_target(EI_CALL_ADDR):05X} (EI), hook between them ⇒ the cave's THREE reads of "
          f"gp-0x{SRC_ACC:04X} are ATOMIC and cannot disagree")
    check(CKSUM_CALL_ADDR > HOOK_ADDR,
          f"and the checksum call at 0x{CKSUM_CALL_ADDR:05X} runs AFTER the hook ⇒ both bytes the "
          f"cave writes are covered by 0x14A's own checksum")

    # 🛑 CHECK 3 -- WHICH HOOK, AND THEREFORE WHICH RATE. Proven from the image, not from a claim.
    #    A hook inside the 1 kHz control task is the bricking class (V24/V27/V48B). This one is
    #    inside the 0x14A CAN-TX BUILDER, and the proof is that the very next thing the builder
    #    does is load the literal CAN ID 0x14A for its checksum call.
    hw1_id, id_imm = u16(base, 0x55C14), u16(base, 0x55C16)
    check(((hw1_id >> 5) & 0x3F) == 0x31 and (hw1_id & 0x1F) == 0 and id_imm == 0x14A,
          f"🛑 THE HOOK IS THE 100 Hz CAN-TX BUILDER, NOT THE 1 kHz CONTROL TASK: 0x55C14 = "
          f"{rd(base, 0x55C14, 4).hex()} decodes `movea 0x{id_imm:X},r0,r{(hw1_id >> 11) & 0x1F}` "
          f"-- the builder loads the literal CAN ID 0x{id_imm:X} for its checksum call at "
          f"0x{CKSUM_CALL_ADDR:05X}, four instructions after the hook. 0x14A is a 100 Hz frame ⇒ "
          f"the cave runs at 100 Hz, and the two extra |gp-0x{SRC_ACC:04X}>>4| recomputations "
          f"(24 B, 12 instructions) are spent on a 10 ms budget, not a 1 ms one")

    # ==============================================================================================
    # 5. 🛑 427 IS UNTOUCHED
    # ==============================================================================================
    print("\n  [5] 🛑 ZERO 427 BYTES -- asserted, not assumed")
    check(s16(base, R427_ADDR) == -R427_SRC,
          f"0x{R427_ADDR:05X} still selects gp-0x{R427_SRC:04X} (V96/V97's) -- NO repoint")
    check(rd(base, R427_SAR_ADDR, 2) == R427_SAR,
          f"0x{R427_SAR_ADDR:05X} still `sar 0x6,r6` ({R427_SAR.hex()}) -- NO rescale. 427 stays "
          f"clamp(|gp-0x{R427_SRC:04X}| * 5 >> 6, 0, 0x3FF), measured 250 codes / 0.000 % sat")

    # ==============================================================================================
    # 6. TWIN COVERAGE -- every payload byte, and where it was copied FROM
    # ==============================================================================================
    print("\n  [6] TWIN COVERAGE -- every payload byte copied from a verified instruction")
    covered = bytearray(len(PAYLOAD))
    n_twin = 0
    for off, w, src, why in TWINS:
        got, twin = PAYLOAD[off:off + w], rd(base, src, w)
        check(got == twin, f"+0x{off:02X} {got.hex():<14s} <- 0x{src:05X}  {why}")
        for k in range(w):
            covered[off + k] = 1
        n_twin += w
    for off, fn, why in DERIVED_IMM:
        check(PAYLOAD[off:off + 2] == fn(),
              f"+0x{off:02X} {PAYLOAD[off:off + 2].hex():<14s} DERIVED   {why}")
        covered[off] = covered[off + 1] = 1
    check(sum(covered) == len(PAYLOAD),
          f"🛑 PAYLOAD COVERAGE {sum(covered)}/{len(PAYLOAD)} bytes = {n_twin} TWINNED from verified "
          f"instructions + {len(PAYLOAD) - n_twin} DERIVED imm16 data bytes. Zero hand-encoded")
    check(PAYLOAD[0x08:0x0A] == PAYLOAD[0x16:0x18] == PAYLOAD[0x38:0x3A]
          == PAYLOAD[0x46:0x48] == bytes.fromhex("8031"),
          "🛑 all four abs instructions are `subr r0,r6` = 8031, NOT satsubr 3080 (which SATURATES "
          "instead of negating and would corrupt |v| on NEGATIVES ONLY -- a flight-surviving defect)")
    for off in (0x0C, 0x3C, 0x5A):
        check(PAYLOAD[off:off + 4] == rd(base, 0x381FE, 4),
              f"+0x{off:02X} is the WHOLE Honda `ld.w -0x374c[gp],r6` -- ld.w vs ld.h cannot be "
              f"got wrong when the twin is taken whole")
    check(len(PAYLOAD) == 154, f"payload length = {len(PAYLOAD)} bytes")
    check(len(PAYLOAD) <= CAVE_FREE_END - CAVE_BASE,
          f"⚠ GROWTH, STATED NOT CLAIMED AWAY: {len(V96_CAVE)} B -> {len(PAYLOAD)} B "
          f"(+{len(PAYLOAD) - len(V96_CAVE)} B, +{100 * (len(PAYLOAD) / len(V96_CAVE) - 1):.1f} %) "
          f"in a {CAVE_FREE_END - CAVE_BASE} B extent = "
          f"{100 * len(PAYLOAD) / (CAVE_FREE_END - CAVE_BASE):.1f} % used. This build does NOT "
          f"claim NO-GROWTH")

    # ==============================================================================================
    # 7. SEMANTICS -- the rung table as arithmetic, before a byte is written
    # ==============================================================================================
    print("\n  [7] RUNG SEMANTICS -- proven by exhaustion / corner grid BEFORE any byte is written")
    assert_rung_semantics()

    # ==============================================================================================
    # 8. THE EDIT
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

    print("\n  [8] THE EDIT -- 🛑 EXACTLY ONE, AND IT IS NOT A CALIBRATION BYTE")
    prev = rd(base, CAVE_BASE, len(PAYLOAD))
    apply(CAVE_BASE, prev, PAYLOAD,
          f"EDIT 1 (the ONLY one)   cave {len(V96_CAVE)} B -> {len(PAYLOAD)} B, "
          f"{len(EXPECTED)} instructions, FIVE rungs (b7,b6,b5,b4,b3) + the identity")
    check(len(attributed) == len(PAYLOAD),
          f"TOTAL ATTRIBUTED = {len(attributed)} = the cave payload and NOTHING ELSE")
    check(all(b == 0xFF for b in code[CAVE_BASE + len(PAYLOAD):CAVE_FREE_END]),
          f"tail 0x{CAVE_BASE + len(PAYLOAD):05X}-0x{CAVE_FREE_END:05X} still virgin 0xFF")

    # ==============================================================================================
    # 9. 🛑 ZERO CALIBRATION BYTES -- cell by cell against the V97 image
    # ==============================================================================================
    print("\n  [9] 🛑 EVERY CALIBRATION CELL IS BYTE-EQUAL TO V97, CELL BY CELL")
    assert_frozen(code, "built image", ref=base)
    assert_frozen(base, "V97 base", ref=base)
    moved = [m for m in range(FRICTION_N_MODES)
             if rd(code, rec_addr(code, m), REC_LEN) != rd(base, rec_addr(base, m), REC_LEN)]
    check(not moved,
          f"all {FRICTION_N_MODES} friction records are BYTE-IDENTICAL to V97 -- zero moved")
    for m, want_addr in sorted(DOSE_FAMILY_Y.items()):
        got = rec_addr(code, m) + REC_Y_OFF
        check(got == want_addr and rd(code, got, 6) == rd(base, got, 6),
              f"the DOSE FAMILY: mode {m}'s Y array DEREFERENCES to 0x{got:05X} == the named "
              f"0x{want_addr:05X} (record base 0x{rec_addr(code, m):05X} + 0x{REC_Y_OFF:02X}) and "
              f"its 6 bytes are byte-equal to V97 -- dereferenced, then asserted; never hard-coded")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == FRICTION_Y_STOCK,
              f"mode {m} (MANUAL)  Y = {rec_y(code, m)} = Honda STOCK, unchanged")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == FRICTION_Y_V92,
              f"mode {m} (ENGAGED) Y = {rec_y(code, m)} = V92's x1.5, CARRIED unchanged")
    for m in MANUAL_MODES + ENGAGED_MODES:
        check(struct.unpack_from("<3h", code, rec_addr(code, m) + REC_X_OFF) == FRICTION_X,
              f"mode {m}: X = {FRICTION_X} UNCHANGED (no breakpoint moved anywhere)")
    check(rd(code, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4)
          == rd(base, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4),
          "the friction pointer array is byte-identical -- no pointer was rewritten")
    check(u16(code, 0xC6446) == 5244 and code[0x3AA96] == 0xFB,
          "🛑 LEVER B, BOTH HALVES: 0xC6446 = 5244 (arm) AND 0x3AA96 = 0xFB (gate). Silently "
          "reverted at a rebase THREE times; asserted as a PAIR, not singly")
    check(code[0x454FE] == 0xB5 and u16(code, 0xC62EA) == 0 and u16(code, 0xC6CD0) == 3564,
          "🛑 0x454FE = 0xB5 (V42, MEASURED INERT, carried because free), 0xC62EA = 0 "
          "(steer-to-zero) and 0xC6CD0 = 3564 (the 4x forward gain -- NEVER lower)")

    # ==============================================================================================
    # 10. RE-DISASSEMBLE THE CAVE FROM THE BUILT IMAGE, against the RUNG TABLE
    # ==============================================================================================
    print("\n  [10] 🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE, checked against the RUNG TABLE")
    listing = disassemble_cave(code, CAVE_BASE, len(PAYLOAD))
    check(len(listing) == len(EXPECTED) == 59,
          f"{len(listing)} instructions decoded, rung table has {len(EXPECTED)}, expected 59")
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
        print(f"    +0x{off:02X}  0x{addr:05X}  {hx:12s}  {text:22s}  {note}")
    check(not bad_text,
          f"all {len(listing)} instructions match the RUNG TABLE offset-for-offset ({bad_text[:3]})")
    check(nbranch == 9 and not bad_tgt,
          f"{nbranch} branches, EVERY target lands on an instruction BOUNDARY ({bad_tgt[:3]})")
    check(conds == {"bge", "bnh"},
          f"🛑 NO NEW BRANCH CONDITION: the cave uses exactly {sorted(conds)} == V92's and V96's "
          f"proven set. The comparator gets the CORRECT `>=` polarity from `bge` alone via the "
          f"assume-set-then-clear idiom, so no `blt`/`bh`/`bl` and none of the ba05/b205 hazard")
    bad_mn = [t.split()[0] for _, _, _, t, _, _, _, _ in listing
              if t.split()[0].startswith("op") or "?" in t
              or t.split()[0] in ("jarl", "jr", "callt", "div", "divh", "prepare", "dispose")]
    check(not bad_mn,
          f"the cave is a STRAIGHT-LINE LEAF: no call, no loop, no divide, no float, no unknown "
          f"opcode ({bad_mn[:4]})")
    check(writes <= {0, 6, 7},
          f"🛑 registers WRITTEN by the cave = {sorted(writes)} ⊆ {{r0, r6, r7}} -- IDENTICAL to "
          f"V96. r6 is restored by the trailing movea; r7 is overwritten at 0x55C12 `mov 0x8,r7` "
          f"immediately after the hook. NO NEW LIVENESS CLAIM IS MADE AT THE HOOK")
    check(refs <= {0, 4, 6, 7, 31},
          f"🛑 every register REFERENCED = {sorted(refs)} ⊆ {{r0, gp, r6, r7, lp}} -- r8 and r10 "
          f"are LIVE across the hook (0x55C20 `andi 0xf,r10,r8`) and the cave never touches them")
    stores = [(off, operand) for off, _, _, _, k, operand, _, _ in listing if k.startswith("st.")]
    check([(o, d) for o, (rb, d) in stores] == [(0x2C, -DST_B4), (0x7E, -DST_B4), (0x90, -DST_B7)]
          and all(rb == 4 for _, (rb, _) in stores),
          f"🛑 GATE 2 (1): the cave's STORE SET is exactly {{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} "
          f"-- IDENTICAL to V96's flown cave. Three store INSTRUCTIONS, two store CELLS: byte 4 is "
          f"written twice because a two-operand comparator plus an accumulator needs three live "
          f"values in two registers. NO OTHER MEMORY IS WRITTEN ⇒ no control signal is modified")
    check(len({d for _, (_, d) in stores}) == 2,
          "and the cell COUNT is 2, not 3 -- the extra store is to a cell the cave already owned")
    loads = sorted({row[5][1] & 0xFFFF for row in listing if row[4].startswith("ld.")})
    want_loads = sorted({(-x) & 0xFFFF for x in (SRC_427, SRC_MODEL, SRC_REQ, SRC_ACC, SRC_POL,
                                                 DST_B4, DST_B7)})
    check(loads == want_loads,
          f"and it LOADS exactly {[hex(x) for x in loads]} = the five source cells and the two CAN "
          f"payload bytes it read-modify-writes. Nothing else is touched. ALL PURE LOADS")
    # ---- 🛑 CHECK 1 -- THE PSW WINDOW, proven mechanically over the BUILT image's own decode ----
    windows, psw_bad = assert_psw_windows(listing)
    for foff, ftext, boff, btext, gap in windows:
        print(f"      +0x{foff:02X} {ftext:<20s} -> +0x{boff:02X} {btext:<10s} gap: "
              f"{gap if gap else '(adjacent)'}")
    check(not psw_bad,
          f"🛑 PSW WINDOW: all {len(windows)} cmp/addi -> branch windows contain ONLY "
          f"PSW-TRANSPARENT instructions ({psw_bad[:3]})")
    gapped = [w for w in windows if w[4]]
    check(all(all(g.split()[0] == "mov" for g in w[4]) for w in gapped) and len(gapped) == 2,
          f"🛑 exactly {len(gapped)} windows are non-adjacent, and BOTH contain only a `mov imm5` "
          f"-- the assume-set-then-clear idiom. ⚠ `mov`'s flag transparency is BELIEF (SLEIGH + "
          f"Honda's own scheduling at 0x1bd32/0x1539a/0x1a7b6), not a manual quotation")
    add1 = [row for row in listing if row[3].split()[:2] == ["add", "0x1,r7"]]
    check(len(add1) == 1 and add1[0][0] == 0x64
          and not any(0x64 in range(w[0], w[2]) for w in windows),
          f"🛑 `add 0x1,r7` (a PSW SETTER) is used ONCE, at +0x{add1[0][0]:02X}, and it lies "
          f"OUTSIDE every cmp->branch window -- it is the CONSEQUENCE of the b4 branch at +0x62, "
          f"not something scheduled into a gap. Same for all three `sar 0x4,r6` (+0x10/+0x40/"
          f"+0x5E): each PRECEDES its rung's `cmp 0x0,r6`, so the cmp re-establishes the flags")
    sars = [row[0] for row in listing if row[4] == "sar"]
    check(sars == [0x10, 0x40, 0x5E]
          and all(listing[[r[0] for r in listing].index(s) + 1][4] == "cmp" for s in sars),
          f"and every `sar` at {[hex(s) for s in sars]} is IMMEDIATELY followed by the `cmp 0x0,r6` "
          f"that re-establishes the flags ⇒ its PSW write is dead")

    kinds = {row[4] for row in listing if row[4].startswith("ld.")}
    check(kinds == {"ld.h", "ld.w", "ld.b", "ld.bu"},
          f"🛑 load CLASSES = {sorted(kinds)}. The cave deliberately uses ld.h AND ld.w (which share "
          f"hw1) and ld.b AND ld.bu (whose disp parity lives in different fields), and the decode "
          f"of the BUILT image separates all four correctly")

    # ==============================================================================================
    # 11. VALUE-ANCHORED READBACK (a span diff is NOT a value check)
    # ==============================================================================================
    print("\n  [11] VALUE-ANCHORED VERIFICATION, read back from the BUILT image")
    for off, cell, cls in ((0x00, SRC_REQ, "ld.h"), (0x30, SRC_MODEL, "ld.h"),
                           (0x50, SRC_427, "ld.h")):
        got = u16(code, CAVE_BASE + off + 2)
        check(got == ((-cell) & 0xFFFF) and (got & 1) == 0,
              f"cave +0x{off:02X} = {cls} -0x{cell:04X}[gp],r6  (hw2 = 0x{got:04X}, bit 0 CLEAR ⇒ "
              f"ld.h, a 16-bit SIGN-EXTENDING load -- NOT ld.w)")
    for off in (0x0C, 0x3C, 0x5A):
        got = u16(code, CAVE_BASE + off + 2)
        check((got & ~1) == ((-SRC_ACC) & 0xFFFF) and (got & 1) == 1,
              f"cave +0x{off:02X} = ld.w -0x{SRC_ACC:04X}[gp],r6 (hw2 = 0x{got:04X}, bit 0 SET ⇒ "
              f"ld.w, a 32-bit load -- NOT ld.h)")
    check(s16(code, CAVE_BASE + 0x6A) == -SRC_POL,
          f"cave +0x68 = ld.b -0x{SRC_POL:04X}[gp],r6  (hw2 = 0x{u16(code, CAVE_BASE + 0x6A):04X}) "
          f"-- ld.b SIGN-extends; ld.bu would zero-extend and the b3 rung would read garbage")
    check(s16(code, CAVE_BASE + 0x6E) == -POL_THRESHOLD,
          f"cave +0x6C addi imm16 = {s16(code, CAVE_BASE + 0x6E)} ⇒ b3 = (gp-0x{SRC_POL:04X} >= 0)")
    for off, want in ((0x10, ACC_FW_SHIFT), (0x40, ACC_FW_SHIFT), (0x5E, ACC_FW_SHIFT)):
        b = code[CAVE_BASE + off]
        check(b & 0xE0 == 0xA0 and b & 0x1F == want,
              f"cave +0x{off:02X} = `sar 0x{b & 0x1F:x},r6` -- the FIRMWARE's OWN >>{want} on the "
              f"accumulator, mirrored exactly (Honda @0x38236)")
    check(u16(code, CAVE_BASE + 0x28) == MASK_B4_PASS1
          and u16(code, CAVE_BASE + 0x7A) == MASK_B4_PASS2
          and u16(code, CAVE_BASE + 0x8C) == MASK_B7,
          f"the three RMW masks read 0x{MASK_B4_PASS1:04X} / 0x{MASK_B4_PASS2:04X} / "
          f"0x{MASK_B7:04X} -- pass 1 owns bit 5, pass 2 owns 7/6/4/3, and Honda's low bits survive "
          f"both. (0x{MASK_B4_PASS1:02X} & 0x{MASK_B4_PASS2:02X}) == 0x07 == Honda's byte4 bits")
    check((MASK_B4_PASS1 & MASK_B4_PASS2) == 0x07
          and (MASK_B4_PASS1 | MASK_B4_PASS2) == 0xFF
          and (~MASK_B4_PASS1 & 0xFF) == 0x20 and (~MASK_B4_PASS2 & 0xFF) == 0xD8,
          "🛑 the two masks PARTITION byte 4: pass 1 clears exactly {b5}, pass 2 exactly "
          "{b7,b6,b4,b3}, their intersection is exactly Honda's 2:0, and their union is the whole "
          "byte ⇒ no bit is written twice and no bit is left undefined")
    check(code[CAVE_BASE + 0x82] == IDENTITY_CODE and code[CAVE_BASE + 0x83] == 0x3A,
          f"cave +0x82 = `mov 0x{IDENTITY_CODE:x},r7` ⇒ 🛑 THE IDENTITY IS A CONSTANT ⇒ "
          f"byte7[7:6] == {IDENTITY_CODE} on every frame, and V96/V97 can only produce {{1,3}}")
    check(code[CAVE_BASE + 0x1A] == 0x02 and code[CAVE_BASE + 0x4A] == 0x04,
          "cave +0x1A / +0x4A = `mov 0x2,r7` / `mov 0x4,r7` -- the two comparator SET values, "
          "landing on byte4 bits 5 and 6 after the shl 0x4")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"cave hook 0x{HOOK_ADDR:05X} byte-identical")
    check(s16(code, R427_ADDR) == -R427_SRC and rd(code, R427_SAR_ADDR, 2) == R427_SAR,
          "🛑 and 427 is STILL byte-identical to V97 in the BUILT image -- zero 427 edits")

    # ==============================================================================================
    # 11b. 🛑 CHECK 2 -- GATE 2, PROVEN DIFFERENTIALLY FROM THE IMAGE, NOT FROM THIS SOURCE FILE
    # ==============================================================================================
    print("\n  [11b] 🛑 GATE 2 -- the DIFFERENTIAL store-set scan: every gp-relative WRITE, V98 vs "
          "STOCK")
    v98_st, stock_st = scan_gp_stores(code), scan_gp_stores(stock)
    added = sorted(v98_st - stock_st)
    removed = sorted(stock_st - v98_st)
    for a, nm, d in added:
        print(f"       + 0x{a:05X}  {nm}  gp{d:+#07x}   {rd(code, a, 4).hex()}")
    for a, nm, d in removed:
        print(f"       - 0x{a:05X}  {nm}  gp{d:+#07x}")
    check(not removed,
          f"no gp-relative store present in STOCK was removed or moved ({removed[:3]})")
    check([(a, nm, d) for a, nm, d in added]
          == [(CAVE_BASE + 0x2C, "st.b", -DST_B4), (CAVE_BASE + 0x7E, "st.b", -DST_B4),
              (CAVE_BASE + 0x90, "st.b", -DST_B7)],
          f"🛑 GATE 2, DIFFERENTIALLY: diffing ALL gp-relative writes image-wide, V98 vs STOCK "
          f"returns EXACTLY {len(added)} -- three `st.b` across TWO cells, gp-0x{DST_B4:04X} "
          f"(CAN 0x14A byte 4) and gp-0x{DST_B7:04X} (byte 7). This is read from the BUILT IMAGE's "
          f"own bytes, not from the payload string, and it also rules out an accidental write edit "
          f"ANYWHERE else in [0x{START:X},0x{END:X})")
    check({d for _, _, d in added} == {-DST_B4, -DST_B7},
          f"⇒ the STORE SET is exactly {{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} = V96's flown set. "
          f"NO CONTROL SIGNAL IS MODIFIED ⇒ the phase added to every control loop is EXACTLY 0 deg. "
          f"Neither byte is read by any control-path instruction; both reach only the 0x14A payload")

    # ==============================================================================================
    # 12. CRC -- DERIVED IN CODE from the image's own 50-block map
    # ==============================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  [12] CRC -- {len(blocks)} block(s) move, trailer set DERIVED from the image's own "
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
    check(derived == {0xC4FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xc4ffc}} -- the cave lies "
          f"in the MAIN block [0x013000,0x0C4FFC). V98 writes no calibration, so the 0xC6FFC and "
          f"0xD7FFC blocks do NOT move. Derived, then asserted; never hard-coded")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    check(0x055FFC not in crc_only,
          "🛑 0x055FFC is LIVE CODE (`6477b8f0`), NOT a CRC trailer -- writing there would silently "
          "overwrite 4 bytes of executable code and the recompute would HIDE it")
    check(walk_all_blocks(bytes(code)) == 0,
          "built image CRC chain 50/50 (NECESSARY, NOT SUFFICIENT -- see [13])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(not [a for a in attributed if 0xC5000 <= a < 0xC5FFC],
          "no edit landed inside [0xC5000,0xC5FFC) -- the block the bootloader SKIPS")
    check(not [a for a in attributed if a < START or a >= END],
          f"every edit lies inside [0x{START:X},0x{END:X})")
    check(bytes(code[:START]) == bytes(base[:START]),
          f"nothing below 0x{START:X} changed (the bootloader region)")

    # ==============================================================================================
    # 13. ZERO-UNATTRIBUTED FULL BYTE DIFF -- the INDEPENDENT check
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
    print("  [13] 🛑 FULL BYTE DIFF: BUILT V98 vs the FLOWN V97 -- over [0x13000, 0x100000)")
    print(f"       {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"       0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    check(not stray, f"ZERO unattributed bytes vs V97 (stray = {[hex(x) for x in stray[:16]]})")
    for lo, hi, why in ((0xC6000, 0xC7000, "🛑 lane weights, model gain, clamps, V97's POLE"),
                        (0xC4000, 0xC4B34, "🛑 the K0/K1 friction family -- V89's lever lives here"),
                        (0xE5000, 0xE6000, "🛑 THE AUTHORITY CURVE -- virgin, and it stays virgin"),
                        (0xCB000, 0xE0000, "every friction/gain record page (the dose family)"),
                        (0xD6000, 0xD8000, "the mode records"),
                        (0x55D00, 0x55F00, "🛑 the 0x1AB / 427 builder -- ZERO 427 edits")):
        check(not [d for a, b in runs for d in range(a, b + 1) if lo <= d < hi],
              f"ZERO differing bytes in [0x{lo:05X},0x{hi:05X}) -- {why}. Proven by DIFF, not by a list")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    check(hashlib.sha256(bytes(rt)).hexdigest() == base_sha,
          "restoring the attributed set reproduces the flown V97 BIT-FOR-BIT")

    # ==============================================================================================
    # 14. .rwd
    # ==============================================================================================
    print("\n  [14] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V98 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V98_WRITE=rwd to cut.")
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

            print("\n  [15] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V98 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk", ref=base)
            for m in MANUAL_MODES:
                check(rec_y(sd, m) == FRICTION_Y_STOCK, f"shipped .rwd: MANUAL mode {m} = STOCK")
            for m in ENGAGED_MODES:
                check(rec_y(sd, m) == FRICTION_Y_V92, f"shipped .rwd: ENGAGED mode {m} = V92 x1.5")
            check(u16(sd, 0xC63AC) == 150 and u16(sd, 0xC40D2) == 204,
                  "🛑 shipped .rwd: V97's pole (0xC63AC = 150) and V89's K1 (0xC40D2 = 204) are "
                  "BOTH present and BOTH unchanged -- V98 measures them, it does not move them")
            check(u16(sd, 0xC6446) == 5244 and sd[0x3AA96] == 0xFB and sd[0x454FE] == 0xB5,
                  "shipped .rwd: Lever B BOTH halves and 0x454FE = 0xB5 are in the artefact that "
                  "will actually be flashed")
            check(rd(sd, CAVE_BASE, len(PAYLOAD)) == PAYLOAD,
                  f"shipped .rwd: the {len(PAYLOAD)}-byte cave payload is byte-identical")
            check(all(b == 0xFF for b in sd[CAVE_BASE + len(PAYLOAD):CAVE_FREE_END]),
                  "shipped .rwd: the cave tail is virgin 0xFF")
            check(rd(sd, HOOK_ADDR, 4) == HOOK_BYTES, "shipped .rwd: the cave hook is unchanged")
            check(s16(sd, R427_ADDR) == -R427_SRC and rd(sd, R427_SAR_ADDR, 2) == R427_SAR,
                  "shipped .rwd: 427 is byte-identical to V97 -- ZERO 427 edits")
            check(sd[CAVE_BASE + 0x82] == IDENTITY_CODE and sd[CAVE_BASE + 0x83] == 0x3A,
                  "shipped .rwd: the IDENTITY (`mov 0x2,r7` @+0x82) is present ⇒ byte7[7:6] == 2 "
                  "is live in the artefact that will actually be flashed")
            sd_listing = disassemble_cave(sd, CAVE_BASE, len(PAYLOAD))
            check([(row[0], row[3].split()) for row in sd_listing]
                  == [(e[0], e[1].split()) for e in EXPECTED],
                  f"shipped .rwd: the cave RE-DISASSEMBLES to the same {len(EXPECTED)}-instruction "
                  f"rung table, offset for offset")
            sd_stores = [op for _, _, _, _, k, op, _, _ in sd_listing if k.startswith("st.")]
            check(sorted({d for _, d in sd_stores}) == sorted([-DST_B4, -DST_B7]),
                  f"🛑 shipped .rwd: the STORE SET re-disassembles to "
                  f"{{gp-0x{DST_B4:04X}, gp-0x{DST_B7:04X}}} -- GATE 2 verified from the ARTEFACT")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

            print("\n  [16] 🛑 ARTEFACT UNIQUENESS -- every V98-matching file in both directories")
            stray_rwd = sorted(p for p in Path(RWD_DIR).iterdir()
                               if p.is_file() and "v98" in p.name.lower())
            stray_img = sorted(p for p in Path(ANALYSIS_ROOT).iterdir()
                               if p.is_file() and "v98" in p.name.lower())
            for p in stray_rwd + stray_img:
                mark = "  <-- THIS BUILD" if str(p) in (OUT, BIN_OUT) else "  🛑 STRAY"
                print(f"       {p.name}{mark}")
            check([str(p) for p in stray_rwd] == [OUT],
                  f"exactly ONE V98 .rwd in {RWD_DIR} (found {len(stray_rwd)})")
            check([str(p) for p in stray_img] == [BIN_OUT],
                  f"exactly ONE V98 image in {ANALYSIS_ROOT} (found {len(stray_img)})")
            p = plain_image_path(BASE_NAME)
            check(hashlib.sha256(p.read_bytes()).hexdigest() == BASE_SHA,
                  "🛑 the V97 base image is STILL byte-identical after the V98 cut -- untouched")

    print("\n" + "=" * 102)
    print(f"  V98 [{VARIANT_TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  🛑 ZERO calibration bytes. ZERO 427 bytes. ONE edit: {len(PAYLOAD)} cave bytes "
          f"+ 4 CRC.")
    print(f"  ⚠ CAVE GROWTH: {len(V96_CAVE)} B -> {len(PAYLOAD)} B "
          f"(+{len(PAYLOAD) - len(V96_CAVE)} B), 43 -> {len(EXPECTED)} instructions, in a "
          f"{CAVE_FREE_END - CAVE_BASE} B extent. NOT a no-growth build, and it does not claim to be.")
    print("  🛑 THIS IS AN INSTRUMENT, NOT A FIX. No control signal is modified; V97's pole and")
    print("     V89's K1 are both carried UNCHANGED. Nothing here is claimed to improve the car.")
    print(f"  🛑 IDENTITY: byte7[7:6] == {IDENTITY_CODE} on EVERY frame. V96/V97 -- the builds that "
          f"could be\n     on the car -- can only produce {{1,3}}, so ONE FRAME identifies this build.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    assert len(PAYLOAD) == 154 and len(V96_CAVE) == 112
    build()
