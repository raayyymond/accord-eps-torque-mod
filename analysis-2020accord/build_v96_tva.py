#!/usr/bin/env python3
r"""build_v96_tva.py -- V96 = V92, BYTE-FOR-BYTE ON EVERY CALIBRATION CELL, + a 112-byte INSTRUMENT
                        that measures the Path-2 LERP's LOCAL SLOPE at the real operating point.

    base   _v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4_plain_image.bin
           sha256 c8e89fe35ebc445e4c4b19663ba9655dfeb8ba5cada2172aeb033eeb9f9eb939

    0xC4B34  cave payload  116 B -> 112 B (+4 B restored to virgin 0xFF)   NO GROWTH
    0x55DF2  4294 -> 9094      CAN 427 MOTOR_TORQUE source: gp-0x6bbe -> gp-0x6b70
    0x55E10  a432 -> a632      CAN 427 packer scale: sar 4 -> sar 6, so the new source CANNOT CLIP

Three edits: 116 cave-span bytes, 2 repoint bytes, 2 scale bytes (1 differs), 4 CRC bytes.
🛑 **ZERO CALIBRATION BYTES.** Not one. That is the point of the build.

===================================================================================================
🛑🛑 WHY V96 EXISTS -- READ THIS BEFORE THE DESIGN
===================================================================================================
**V94 is on the car and the operator STOPPED DRIVING IT.** Route 7d, fault-free, but: *"made the
stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided
it was not safe to drive."*

V94 cut 0xCBE74 6x against V92 on the premise that gp-0x6b26 is APPARENT INERTIA and therefore
*"lowering is strictly safe on both binding bounds."* Measured afterwards on two independent drives,
omega-partialled against a shuffled control, the DELIVERED lane sits at +137 deg / +139 deg versus
WHEEL rate at 6-9 Hz => |cos| = 0.73 => +518 / +565 counts of POSITIVE Re(Z). It is a real 6-9 Hz
damper and V94 removed 6/6ths of it.

V96 has two jobs, in this order:
    JOB 1  GET THE CAR BACK TO A CONFIGURATION THE OPERATOR DROVE AND DID NOT ABORT -- that is V92.
    JOB 2  MEASURE THE ONE QUANTITY THAT IS CURRENTLY BLOCKING EVERY REMAINING LEVER.

🛑 **V96 IS NOT A FIX AND IS NOT BUILT AS ONE.** No candidate fix lever survived this session's
controls. There is no "while we're in there" gain change anywhere in this file. Single purpose.

===================================================================================================
🛑 WHAT THE PROBE MEASURES, AND WHY IT IS THE RIGHT QUANTITY
===================================================================================================
`FUN_00038148` (1 kHz, sole caller FUN_0002214a) computes:

    sum6   = SUM over 6 lanes of (x_lane * gate_lane(x_lane) * W_lane) >> 10     # all W = 1024
    target = ((sum6 * polarity * 2639) >> 10) * 16                               # 0xC6468 = 2639
    gp-0x374c += ((target - gp-0x374c) * 102) >> 10          # 0xC63AC, fc ~15.9 Hz at 1 kHz
    iVar6      = gp-0x6bfe + gated(gp-0x6bfa, +-20000) - (gp-0x374c >> 4)   # @0x38236-0x3823a
    gp-0x6b70  = clamp( sign(iVar6) * f(|iVar6| * 1024 >> 10), +-8192 )     # 0xC6200 = 8192
                 #        ^^^^^^^^^^^ f = a RAM-RESIDENT LERP, populated at runtime by FUN_000389ec
    gp-0x6b70 --> FUN_00037fe6 --> gp-0x6ad6 --> the PID REFERENCE --> aggregator --> motor

**`f` has never been reverse-engineered.** Two attempts at FUN_000389ec failed; the table lives in
RAM (gp-0x64b6../gp-0x641c..). Its LOCAL SLOPE `f'` at the operating point is the blocking unknown
behind the whole Path-2 weight class -- it is why `0xC63A6` came back NO-GO (a lever whose sign is
unresolved is not a lever; that is exactly how V94 got onto the car).

**THE IDENTITY THAT MAKES THE PAIR SUFFICIENT** -- verified here from my own decompile, not taken on
trust. `gp-0x6b70 = sign(iVar6) * f(|iVar6|)` and `iVar6` depends on `gp-0x374c` only through the
`-(gp-0x374c >> 4)` term, so

    d(gp-0x6b70)/d(gp-0x374c>>4) = sign(iVar6) * f'(|iVar6|) * d|iVar6|/d(iVar6) * (-1)
                                 = sign(iVar6) * f'          * sign(iVar6)       * (-1)
                                 = -f'(|iVar6|)                                  # the signs SQUARE

⇒ **the empirical slope of `gp-0x6b70` against `gp-0x374c>>4`, from the flown pair ALONE, IS `-f'`
-- regardless of sign(iVar6) and regardless of gp-0x6bfe / gp-0x6bfa.** Those two do NOT need to be
observed. That is what makes a two-channel probe sufficient, and it is why this build answers a
question that a six-lane ranking probe could not.

⊕ And it is the same lesson the V94 flight taught, applied: `gp-0x6b26` was mis-priced TWICE from
its producer's transfer function (+90 deg, then +75 deg), and what settled it was **measuring the
delivered lane on-car**. `f'` measured this way needs no knowledge of the loop gain `L` (eight
never-byte-read floats at tp+0x50d4) and no knowledge of the LERP knots.

===================================================================================================
WHAT CLASS OF BUILD THIS IS -- against the whole arc since V38
===================================================================================================
V38-V52 authority/filters/poles/caves - V53-V61 telemetry + lane mutes - V62-V73 the rate lane
(r24/r26) - V74-V83a the base-assist damper - V84-V86B damper reverts and phase - V87 subtractive
measurement - V88 Lever B restored - V89 the PLANT MODEL - V90 pure instrument - V91/V92 the
0xCBE74 x1.5 dose + instrument - V93/V94 the 0xCBE74 CUT (aborted on-car).

**V96 is a PURE INSTRUMENT build with a REVERT underneath it, and it is the first build in the whole
arc to telemeter a TRANSFER rather than a SIGNAL.** Every cave from V53 to V94 put single cells on
the wire and asked "how big is it / what sign is it". V96 puts BOTH ENDS OF ONE NONLINEARITY on the
wire so the *slope between them* is the measurement. Nothing in the kit has done that.

RE-RUN vs NEW, stated plainly:
    * The CALIBRATION is a RE-RUN of V92 -- exactly, byte for byte, deliberately. That is JOB 1.
      V92 flew (route 79) fault-free and is the last configuration the operator drove and did not
      abort. Nothing about it is new and nothing about it is claimed.
    * The 427 repoint is the same CLASS of edit as V88/V90/V92/V94 (a 2-byte source halfword plus a
      1-byte scale), pointed at a cell no build has ever telemetered.
    * The cave rungs are ALL new signals. gp-0x6b70, gp-0x374c and gp-0x674e have never been on any
      wire on any build.

FROZEN CELLS, by count, all re-asserted here and NONE moved by V96:
    0xC40D2 (K1) unmoved since V89 = 6 builds.   0xC6446 + 0x3AA96 (Lever B) unmoved since V88 = 7.
    0x454FE unmoved since V80.                    0xC407E at Honda's 511 since V81.
    0xC63A0..0xC63AE (all six lane weights + alpha + scale) at stock on EVERY build in the kit.
    0xCBE74 modes 24/25 STOCK and modes 26/27 at V92's x1.5.  0xC640A/0xC640C at Honda's.

===================================================================================================
THE PAYLOAD -- what each bit measures
===================================================================================================
    CAN 0x14A, 100 Hz            (Honda's byte4[2:0] and byte7[5:0] preserved by mask)
      byte4 b7  gp-0x6b70 < 0            SIGN of the PRIMARY -- de-rectifies the CAN 427 magnitude
      byte4 b6  (gp-0x374c >> 4) < 0     SIGN of the REGRESSOR
      byte4 b5  Mhi bit 1  \  Mhi = min(|gp-0x374c>>4| >> 12, 3)   🛑 SATURATING
      byte4 b4  Mhi bit 0  /  Mhi == 3  <=>  SATURATED (|v| >= 12288). Its DUTY is an OUTPUT.
      byte7 b7  Mlo = bit 11 of |gp-0x374c>>4|     M = 2*Mhi + Mlo = |v|>>11 exactly when Mhi < 3
      byte4 b3  gp-0x674e < 28           the AUTHORITY-CURVE MODE rung. EXPECTED 1.
      byte7 b6  1                        FINGERPRINT / IDENTITY. See IDENTITY below.
    CAN 427 (0x1AB) MOTOR_TORQUE, 50 Hz
      clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF)        <- >>6, NOT Honda's >>3. See THE 427 SCALE.

🛑 **BOTH CHANNELS ARE SIGNED, AND THAT IS NOT OPTIONAL.** A rectified channel folds on 2f. At
100 Hz a rectified regressor would fold **3-4.5 Hz straight into 6-9 Hz**, and the LKAS command's
energy is 88-95 % inside 0.5-3 Hz. On 427 at 50 Hz a rectified channel folds 26/29/31 Hz to 2/8/12
Hz. With the sign bits both fold on |f - fs*k| instead: 26-31 Hz lands at 19-24 Hz on 427, outside
the target band. **A slope regressed on a rectified regressor is meaningless anyway.**

===================================================================================================
🛑 SIZING -- V93 failed here, and both numbers are stated in BOTH directions
===================================================================================================
V93's flight was wasted because V93's own instrument could not see V93's edit. Neither of V96's
cells has ever been observed, so there is no flown distribution. They are sized differently and
deliberately so:

**PRIMARY, gp-0x6b70 on CAN 427.** The cell is HARD-CLAMPED to +-8192 by `0xC6200`, read from the
image. `wire = clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF)`:
    no-clip   8192*5>>6 = 640 <= 1023      (sar 5 gives 1280 and goes flat from |x| >= 6554)
    LSB = 64/5 = **12.8 counts** = 0.156 % of the cell's own +-8192 range; ~9.3 effective bits.
    6-9 Hz invisibility floor ~ 3.6 counts amplitude (0.044 % of range). Nothing meaningful is
    invisible on the primary channel.

**REGRESSOR, gp-0x374c>>4 on the cave.** 🛑 **DELIBERATELY SATURATING, NOT LINEARLY SIZED.**
`gp-0x374c` is a 32-bit accumulator holding `target * 16` and it has **no explicit clamp**. The only
available bound is structural -- sum6 max ~26,624 with all six lanes pinned => `gp-0x374c>>4` max
~68,600 -- and that is **almost certainly a large overestimate** (gp-0x6bd0's damper lane alone is
dead on ~96 % of engaged frames). **Sizing a tight linear scale off 68,600 is exactly the gp-0x6b98
"1-bit comparator" mistake: a probe under-ranged from a bad guess.** So:
    * telemeter `gp-0x374c >> 4`, **the firmware's OWN shift** (mirrored from `sar 0x4,r6` @0x38236,
      which is the instruction that forms this very term of iVar6), NOT the raw 32-bit accumulator.
      That lands it in the same domain as gp-0x6b70, which is the point -- the endpoint is a slope
      BETWEEN them.
    * 3-bit magnitude, LSB 2048, **saturating at 12288** with `Mhi == 3` as the explicit top code.
    * 🛑 **THE SATURATION DUTY IS A FIRST-CLASS REPORTED OUTPUT**, so V96 can size linearly off real
      data instead of off a guess. A saturating channel that tells you it saturated is fine; a
      linear one sized off 68,600 is not.
    * ⚠ **Errors-in-variables:** a coarse regressor ATTENUATES the fitted slope toward zero. It does
      **not** flip its sign. The decisive output is the SIGN of `f'`, which survives; the magnitude
      is a lower bound on |f'|. Stated here so it is not rediscovered as a defect.

===================================================================================================
🛑 CAVE DISCIPLINE -- V24, V27 and V48B all BRICKED the ECU. Every cave byte is risk.
===================================================================================================
★ **NO GROWTH. 112 bytes inside V92's own 116-byte footprint**, same base `0xC4B34`, same hook, same
  `jarl`. V92's cave flew fault-free as route 79, so the region, its extent and its RAM footprint
  are already proven on-car. The 4 unused bytes are restored to virgin `0xFF`.
★ **NO NEW BRANCH CONDITION.** The cave uses only `{bge, bnh}` -- exactly V92's set. The `!= 7`
  form of the mode rung would have needed `bne`, a third condition and the recorded `ba05`/`b205`
  inversion hazard; `>= 28` reuses V92's own proven `addi -imm,r6,r0` + `bnh` unsigned-range idiom.
★ **108 of 112 bytes are copied from a Ghidra-verified instruction in THIS base image**; the other
  4 are two pure-data imm16 halfwords. Every Honda source was confirmed to sit at a real instruction
  boundary, not merely to appear as a matching halfword (which could be the hw2 of a 4-byte insn):
      ld.w -0x374c[gp],r6  2437b5c8 @0x381FE  <- FUN_00038148's OWN read of the accumulator, whole
      sar 0x4,r6           a432     @0x38236  <- the firmware's OWN `gp-0x374c >> 4`, same register
      hw2 9094 (-0x6b70)            @0x38008 · hw2 b398 (-0x674e) @0x28FCA
      sar 0xc,r6 ac32 @0x2C0BA · sar 0xa,r6 aa32 @0x2C13C · or r6,r7 0639 @0x1C1C4
      cmp 0x3,r6 6332 @0x1695A · mov 0x3,r6 0332 @0x14B88 · mov 0x1,r7 013a @0x14D40
      sar 0x6,r6 a632 @0x2401A (the new 427 shift)
The specific traps this defeats:
    * `subr r0,r6` is 8031. The hand-derived 3080 is `satsubr`, which SATURATES instead of negating
      and would corrupt |v| on negative values ONLY -- a defect that survives a flight.
    * 🛑 **`ld.h X[gp],rN` and `ld.w X[gp],rN` SHARE hw1; only hw2 bit 0 separates them**, and this
      cave deliberately uses BOTH (`ld.h -0x6b70`, `ld.w -0x374c`). Every one of those 4-byte
      sequences is therefore twinned WHOLE or has its hw2 twinned from a Honda instruction of the
      SAME class, and the built image is re-disassembled and the class re-checked.
    * `ld.bu -0x674e` has an EVEN displacement so its op field is 0x3C, and Honda encodes it with
      hw2 bit 0 SET as a don't-care marker (`b398`, not `b298`). Both halves are twinned from real
      Honda instructions rather than computed, so the parity cannot be got wrong.
    * The mode-rung predicate uses `bnh` after `addi -0x1c,r6,r0`: CY is the carry-OUT, so CY|Z is
      exactly `r6 >=u 28`. Proven by exhaustion over all 256 byte values below, not argued.

GATE 1 -- RAM OWNERSHIP. **ZERO NEW RAM.** Verified this session by TWO methods (GhidraMCP +
an independent whole-image Python LE byte scan of both store encodings):
    reads   gp-0x6b70  1 reader (`ld.h -0x6b70,gp,r13` @0x38006, FUN_00037fe6) and 1 writer
                       (`st.h -0x6b70,gp,r11` @0x382D2, FUN_00038148). V96 adds a second reader.
            gp-0x374c  **exactly 2 access sites image-wide** -- `ld.w` @0x381FE and `st.w` @0x38230,
                       BOTH inside FUN_00038148 itself. Zero other readers, zero other writers.
                       Reading it adds no writer and touches pre-existing Honda RAM whose only other
                       accessor is the function that owns it.
            gp-0x674e  1 writer (`st.b -0x674e,gp,r8` @0x4272A, from the variant config table at
                       0xCD000 stride 0x24 col +0x08) and 6 readers. A STATIC configuration byte.
            -- ALL are `ld.h`/`ld.w`/`ld.bu`. A load has no side effect. NO new RAM is claimed.
    writes  gp-0x1514 bits 7:3   -- the byte ~50 flown builds have written
            gp-0x1511 bits 7:6   -- V92's own, flown on route 79
    scratch r6 and r7 ONLY, asserted mechanically from the BUILT image's decode.

🛑 A SITE V92's GATE-1 METHOD COULD NOT SEE, FOUND AND CLEARED HERE. V92 scanned for st.b/st.h whose
   hw2 equalled the exact displacement. That is structurally blind to a **32-bit** access at a
   DIFFERENT displacement covering the same byte. A wider scan finds
       0x2194A  2477edea  ld.w  -0x1514[gp],r14      FUN_0002193e, called by the 0x14A builder
       0x21964  6477edea  st.w  r14,-0x1514[gp]
   -- a word RMW spanning 0x14A bytes 4,5,6,7, i.e. BOTH of our bytes. **It is benign**: 0x21954
   `mov 0xff0000ff,r15` + 0x21960 `and r15,r14` preserves bits 7:0 (byte 4) and 31:24 (byte 7)
   exactly; it rewrites only bytes 5 and 6. Asserted from the image. Method gap real, result harmless.

🛑 THE CAVE RUNS WITH INTERRUPTS DISABLED -- DECODED, NOT ASSERTED. The Format-V jarl displacements
   around the hook decode to 0x55C0A -> 0x1FA42 (DI) and 0x55C2E -> 0x1FA72 (EI), with the hook at
   0x55C0E between them. Therefore the cave's TWO reads of `gp-0x374c` (one for the byte4 half, one
   for the byte7 half) are atomic with respect to the 1 kHz producer and **cannot disagree** -- which
   matters more here than it did on V92, because both halves encode ONE number. The checksum call
   jarl 0x57B24 at 0x55C18 still runs AFTER the hook, and 0x55C24 `andi 0xf0,r6,r6` preserves 7:4.

GATE 2 -- CLOSED-LOOP STABILITY, magnitude AND phase, DEMONSTRATED not asserted:
  (1) The cave's STORE SET is exactly {gp-0x1514, gp-0x1511}, read back from the BUILT image's own
      re-disassembly. A whole-image scan of every access to those two addresses returns only the
      0x14A builder's own RMWs, the benign word RMW above, and the checksum tail. **No control-path
      instruction reads either byte** => the probe closes no loop. That is the demonstration.
  (2) The cave hangs off the 100 Hz CAN-TX builder, not the 1 kHz control task: 43 instructions at
      100 Hz, against V92's 43 at the identical site, flown fault-free. Identical instruction count.
  (3) The two 427 edits change WHAT A CAN FIELD REPORTS, NOT WHAT THE ECU DOES. 0x55DF2 selects
      which cell loads into r6 for `jarl FUN_00049a5a`; 0x55E10 scales it; the result reaches only
      FUN_00049a90(v,0,0x3ff) -> the 0x1AB payload. Nothing feeds back.
  (4) **Phase added to every control loop is exactly 0 deg, because NO CONTROL SIGNAL IS MODIFIED
      AT ALL.** Not "a scalar adds no phase" -- that sentence shipped V94, and it was about an edit
      that DID alter a control signal. Here the calibration is byte-identical to V92's, asserted
      cell by cell AND by a zero-unattributed whole-image diff.
  (5) The shaper is untouched: a filter there DISABLES THE POWER STEERING (FUN_00043e44 float twin,
      +-5 counts, 10 ms -> DTC 0xF00049, 2.4 deg budget). 0xC4080 (NEVER-RAISE relay hazard) and
      0xC407E (hard-fault interlock, Honda's 511) untouched and asserted.
  (6) 🛑 **0xC63A6 IS NOT IN THIS BUILD.** The trace closed it NO-GO: it weights only gp-0x6b26 (one
      instruction, `ld.hu 0x73a6,tp,r15` @0x381CA, zero writers), but Path 2's SIGN is unresolved
      because gp-0x6b70 is a PID REFERENCE, not an aggregator addend, and its sign depends on the
      local slope of the very RAM LERP this build exists to measure. **A lever whose sign is
      unresolved is not a lever.** `LEVER_C63A6` is present as a guarded constant, pinned to None
      and asserted None, so it cannot be flipped without reading this paragraph.

🛑 **THE AUTHORITY CURVE IS NOT TOUCHED.** 0xE547C / 0xE5404 / 0xE52FC / 0xE5284 are virgin on all
   90 images and stay virgin. V96 measures which curve is selected; it does not steer.

===================================================================================================
IDENTITY -- structural, single-frame, and NOT dependent on any measurand
===================================================================================================
**byte7 b6 == 1 on EVERY frame, unconditionally** (`mov 0x1,r7` -- a constant, not a signal).

  * **ANY single frame with 0x14A byte7 bits[7:6] != 0 proves V96 is on the car.** V94 -- the build
    actually on the car -- carries the **V90 cave, 74 bytes**, which never writes byte 7 (verified
    from V94's own image in this script). Honda's only two writers of gp-0x1511, `andi 0xcf,r8,r8`
    @0x55BFC and `andi 0xf0,r6,r6` @0x55C24, both mask bits 7:6 off, as do all builds V53..V91.
    🛑 STRICTLY STRONGER than V92's own identity, which used two MEASURANDS and fired only because
    one of them happened to have duty 0.165. V96's cannot fail to fire.
  * Sharper: byte7[7:6] is in {1,3} on every frame. **byte7[7:6] == 2 is IMPOSSIBLE.**
  * Separation from V92 (the only other byte-7 writer) is behavioural rather than structural here:
    on V92 byte7 b6 = the dwell-snap state, measured duty **0.0000 over 75,227 engaged frames with
    an 855 s sustained run**, so "b6 == 1 on >= 99.9 % of frames" separates them overwhelmingly.
    ⚠ **Recorded as BELIEF, not EVIDENCE** -- it rests on a measured duty, not on a structural
    impossibility. V92 is a named artefact that is not being flashed, and the flash decision names
    one file, so the residual risk is bookkeeping, not physics. Stated because the V92 build claimed
    a structural separation and I am not claiming one.

MAP VALIDATOR 1: **byte4 b3 is CONSTANT for the whole drive.** `gp-0x674e` is a static configuration
    byte (one writer, from a config table read at init). Any frame-to-frame variation in b3 indicts
    either the byte4 bit offset or the staticness assumption. A per-drive alignment check.
MAP VALIDATOR 2: if b3 == 1 -- the EXPECTED reading -- then **byte4[7:3] is ODD on every frame**,
    which is the ~50-build convention preserved. b3 == 0 is the RULE-7 alarm AND flips the parity,
    so the alarm is visible at a glance in a byte histogram.
MAP VALIDATOR 3: byte7[7:6] in {1,3} on every frame; == 0 or == 2 proves a byte7 offset error.
⚠ NOT a validator: `Mhi == 3` is REACHABLE by construction (it is the saturation code), and
    b6 == 1 with M == 0 is reachable (-2048 < v < 0). Both recorded because the sharper claims are
    tempting and would mis-fire on real data, exactly as V92's nearly did.

===================================================================================================
🛑 RELATIONSHIP TO V95, AND WHY b3 IS THE MODE RUNG AND NOT THE STATE GATE
===================================================================================================
**V95 is the LANE build** (`gp-0x6b4c` / `gp-0x6b4e`, the two ±10240 `FUN_00038148` lanes) and it
stays on the shelf, verified and unflown, exactly as V93 did when V94 took a new number. V96 is the
re-scoped PAIR build. Both are valid; V96 is the one that answers a question with an action attached
on **both** branches of its outcome, which is why it flies first.

🛑 **THE `gp-0x67fa` STATE GATE WAS EVALUATED FOR b3 AND REJECTED ON BUILDABILITY, NOT ON VALUE.**
Honda's own gate, read out of this image (all four sites byte-asserted below):

    0x221BC  ld.bu -0x67fa,gp,r6        state
    0x221C0  mov   0x1,r15
    0x221C2  andi  0xf,r6,r8            s = state & 0xF
    0x221C6  shl   r8,r15,r25           r25 = 1 << s          <-- FORMAT IX VARIABLE SHIFT
    0x221D6  andi  0x830,r25,r28        r28 = r25 & 0x830     <-- 0x830 = bits 4, 5, 11
    0x22672  cmp   r0,r28 / be          the call to FUN_00038148 is SKIPPED iff r28 == 0

⇒ the exact predicate is `s ∈ {4, 5, 11}`. Three findings decided this:
  1. **The gate boolean is never stored.** `r28` is written once at 0x221D6, tested at 0x22672, and
     rewritten NOWHERE in between -- and no store in [0x2214A,0x22700) has r28 or r25 as its source.
     Scanned exhaustively. **There is no RAM cell the cave could read**; it would have to recompute.
  2. **Recomputing needs `shl reg,reg,reg` (Format IX) with HAND-DERIVED register fields.** No twin
     with our register set exists. That is exactly the hand-encoding this kit forbids, in the
     instruction class that bricked V24/V27/V48B. It also needs a third scratch register, and r8/r10
     are LIVE across the hook.
  3. 🛑 **An APPROXIMATE gate is WORSE THAN NO GATE.** The affordable form is a two-sided range
     (`4 <= s <= 11`, V92's `addi`+`bnh` idiom). That is a SUPERSET: it reads 1 in states 6-10 where
     the producer is NOT running. **A bit that can silently say "live" while the pair is frozen is
     worse than no bit, because it would be trusted.** The whole point of the rung was to make the
     freeze unmissable.

⊕ And the freeze is detectable from the wire at ZERO bit cost, because the gate freezes **both**
  members of the pair at once: see FREEZE EXCLUSION in the scoring plan. `gp-0x674e` by contrast is
  exact, static, twinned, needs no new branch condition, and settles RULE 7 for the authority curve
  permanently. If the exact gate is wanted it costs ~28 cave bytes, a new branch condition (`be`,
  twinnable from 0x22674), and growth past V92's proven footprint -- a separate build, not this one.

===================================================================================================
🛑 PRE-REGISTERED SCORING PLAN -- declared HERE, BEFORE the flight
===================================================================================================
### PRIMARY ENDPOINT -- TWO SLOPES, REPORTED AS TWO DISTINCT NUMBERS
`gp-0x6bfe` closes the Path-2 loop back through gp-0x6b98 / FUN_0003b8f6 / FUN_0003bc20 with ONE
clean sample of delay. Therefore a single whole-drive regression silently returns the second
quantity while you believe you have the first. **Both are pre-registered separately:**

  **S1  OPEN-LOOP f'** -- slope of `gp-0x6b70` on `gp-0x374c>>4` at **lag 0 and lag 1** (first
      differences, per 1.28 s window, pooled). A same-instant fluctuation in gp-0x374c cannot yet
      have propagated into gp-0x6bfe, so this isolates `f'`. **Its SIGN is the number that decides
      whether a Path-2 weight lever helps or inverts.** Report sign, magnitude, and CI.
  **S2  CLOSED-LOOP transfer** -- coherence-weighted slope over longer windows, folding in the loop
      gain `L`. **Arguably the more load-bearing number, because GATE 2 is a closed-loop question.**
  🛑 **Do NOT conflate them into one regression.** Report S1 and S2 side by side, with the lag used.
  ⚠ Errors-in-variables from the coarse regressor attenuates BOTH magnitudes toward zero and
    preserves BOTH signs. Quote the magnitudes as LOWER BOUNDS on |f'| and |L·f'|.

### SECONDARY ENDPOINT -- the symptom
Hands-on **band power in OVERRIDE** on the signed `gp-0x6b70` series (427 + byte4 b7), 6-9 Hz.
Override := `latActive` AND `|STEER_TORQUE_SENSOR| > 1200` AND driver torque opposing the command.
🛑 The kit's hands-off `steeringPressed` mask excludes that regime BY CONSTRUCTION, and override
supports only **SEVEN** 5.12 s windows corpus-wide (5013 runs, median 0.02 s, p90 0.55 s). So:
**EVENT-TRIGGERED 1.28 s windows anchored on override ONSET** (rising edge of a run >= 0.15 s,
window -0.32 s .. +0.96 s), one per event -- a point process, not sustained runs. Statistic = **p99
of the analytic envelope** of a 6-9 Hz bandpass. **BOOTSTRAP OVER EPISODES, never over windows.**

### FIRST-CLASS OUTPUTS THAT ARE NOT ENDPOINTS
  * **The saturation duty of `Mhi == 3`** -- so V96 can size the regressor linearly off real data.
  * **The full 8-code M histogram** -- if M is pinned at one code the regressor carried no
    information and S1/S2 are void; that is an interpretable failure, not a mystery.
  * **The mode reading b3** -- settles RULE 7 for the authority curve forever, on any drive.

### CONTROLS -- RUN THE CONTROL BEFORE THE MEASUREMENT
Four 6-9 Hz stories died to their own controls in one session; a probe with no control is not
evidence.
  POS-1  byte7 b6 == 1 on >= 99.9 % of frames. If it fails, **NOTHING in the readout is
         interpretable** and nothing may be reported. (The V64 / V68 lesson.)
  POS-2  the 427 wire is non-degenerate: >= 20 distinct codes and p99 >= 8.
  POS-3  b3 is CONSTANT across the drive (MAP VALIDATOR 1).
  NEG-1  band 32-38 Hz, same windows, SYMMETRIC wheel-order veto over orders 1-6 on ALL scored
         bands at once -- never per-band vetoes, which build different window sets.
  NEG-2  the same estimator on MANUAL hands-on windows matched on wheel rate.
  NEG-3  **for S1/S2: a SHUFFLED-PAIRS control.** Regress gp-0x6b70 on a time-shuffled
         gp-0x374c>>4; the slope must collapse to zero. A slope that survives shuffling is an
         artefact of the two channels' common exposure, not a transfer.
  FLOOR  **no ratio below 2x may be claimed in either direction.** Same-firmware spread: 6-9 Hz
         1.37x, 18-22 1.31x, 26-31 1.99x, 32-38 control 1.54x.

### ALIASING AND PAIRING
427 is 50 Hz; with b7 the series is SIGNED so the fold law is |f - 50k|, not |2f - 50k|: 26-31 Hz
-> 19-24 Hz, outside the band. Cross-check every 6-9 Hz claim on the independent 100 Hz channels
(`tq` on 0x18F, `rate_c` on 0x14A). Use only the `(t, probe)` or `(raw14_t, raw14_b4)` pairings --
NEVER crossed (the kit-wide off-by-one is 28 deg at 7.79 Hz). `rate_f` for PHASE, `rate_c` for
MAGNITUDE, and say which, every time.
⚠ **The two members of the pair arrive on DIFFERENT MESSAGES at DIFFERENT RATES** (427 at 50 Hz,
0x14A at 100 Hz). S1's lag-0/lag-1 distinction is therefore defined on the 50 Hz 427 grid with the
nearest 0x14A frame within 10 ms; **state the pairing rule in the scorer and check it with a byte
test, not a `searchsorted`** (co-logged frames share a logMonoTime and searchsorted mispairs them).

### 🛑 FREEZE EXCLUSION -- MANDATORY, and it replaces the state-gate rung
`FUN_00038148` is called only when `s = gp-0x67fa & 0xF` is in {4,5,11} (0x22672 `cmp r0,r28 / be`).
**When that gate shuts, BOTH `gp-0x6b70` and `gp-0x374c` stop updating and the wire HOLDS.** A held
wire looks like a dead signal and would enter S1/S2 as spurious zero-slope samples.
**PRE-REGISTERED RULE: drop every run of >= 5 consecutive 427 frames in which the 427 code AND the
byte4 field are BOTH bit-exactly unchanged.** This is a good detector precisely because the freeze
is COMMON-MODE: the 427 channel is ~9.3 effective bits at a 12.8-count LSB fed by a 1 kHz signal,
and a live pair essentially never holds both channels bit-exact across many frames at once.
**Report the dropped fraction as a first-class output**, next to the saturation duty.
⚠ Its residual is stated honestly: this is a heuristic on the wire, not a read of the gate. It is
what is available without hand-encoding a Format IX shift -- see the section above. ⊕ Mitigating:
the gate's shut states are assist-off / fault / standstill, which the engaged+override+moving mask
already removes, so the exposure the rule has to catch is small to begin with.

### NULL INTERPRETABILITY BUDGET -- what each null MEANS, decided in advance
  * "the cave never ran" is separable from "the signal is zero": byte7 b6 is a constant.
  * If **M is pinned at 0**: |gp-0x374c>>4| < 2048 throughout -- a real bound, and it tells V96 to
    use a smaller shift. If **M is pinned at 7 (Mhi == 3)**: |v| >= 12288 throughout -- also a real
    bound, telling V96 to use a larger one. Either way the next build sizes off data.
  * If the 427 wire is pinned, POS-2 fails and the primary half is void while the cave half stands.
    The two channels fail independently, on purpose.
  * 🛑 **If S1's CI spans zero, the answer is "f' is not resolved by this flight" -- NOT "f' is
    zero".** A Path-2 weight lever stays blocked in that case, and that is the correct conclusion.

===================================================================================================
🛑 PREMISE-ENCODING AUDIT -- V94 shipped 133/133 GREEN with its own hypothesis as a PASS condition
===================================================================================================
V94's suite contained `check(y_max_all < y_max_stock, "the largest gain magnitude STRICTLY
DECREASES")` -- an assertion that restates the build's hypothesis is not a check, it is the
hypothesis wearing a green tick. Every assertion class in this file was audited against that:

  CLASS                          IS IT A PREMISE?   WHY NOT
  base sha256 / CRC / rwd        no                 facts about the input and the encoder
  cal == V92 cell-by-cell        no                 that IS the deliverable (JOB 1), not a bet
  twins, coverage, decode        no                 facts about bytes and their sources
  rung-semantics corner grid     no                 self-consistency of the ENCODING against the
                                                    declared predicate; no physical claim
  clamp / gate / writer censuses no                 instruction immediates and store sites read
                                                    from the image; structural facts, not outcomes
  427 no-clip, both directions   no                 reachable-set arithmetic vs a PROVEN cell clamp
  zero-unattributed diff         no                 fact about the output

  🛑 **THIS FILE ASSERTS NOTHING ABOUT WHAT THE PROBE WILL SEE.** There is no assertion about the
  sign of f', the size of either cell, the saturation rate, the value of gp-0x674e, or any band
  contrast. There cannot be: no distribution for any of the three cells exists anywhere, which is
  the entire reason V96 is being flown.

===================================================================================================
THE TRAPS THIS SCRIPT IS BUILT AGAINST
===================================================================================================
* AN ADDRESS IS NOT A MODE. Every friction record address is DEREFERENCED from 0xCBE74 + mode*4.
* Y IS AT RECORD BASE + 8. V96 writes no Y anywhere; the rows are read back and compared to V92's.
* THE POINTER ARRAY HAS EXACTLY 34 SLOTS, modes 0..33 -- a GIVEN BOUND, never a walk.
* tp = 0xBF000. tp+0x73a8 is 0xC63A8, NOT 0xC73A8. Every tp+off is COMPUTED IN CODE and anchored
  against a known value before use. The off-by-0x1000 trap has recurred FIVE times.
* 🛑 **V92's 427 shift is `a4` (sar 4), NOT `a3`.** BUILD-LINEAGE's V94 row reads `a3 -> a1`, which
  is correct against V90 and WRONG against V92. This script asserts `a4` on the base and refuses to
  build otherwise.
* NEVER whole-file diff against stock: build images carry 0xFF filler below 0x13000. All diffs are
  restricted to [0x13000, 0x100000).
* A CHECK THAT PRODUCES NO OUTPUT IS NOT A CHECK THAT PASSED. Every assertion emits a boolean.
* A SPAN DIFF IS NOT A VALUE CHECK. Section [17] is a VALUE-ANCHORED verifier reading the VALUE of
  every decision-bearing cell out of the shipped .rwd.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, ANALYSIS_ROOT, RWD_DIR              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V96_WRITE", "").strip().lower()

TP = 0xBF000                                   # 🛑 tp+0x73a8 = 0xC63A8, NOT 0xC73A8

BASE_NAME = ("_v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4"
             "_plain_image.bin")
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "c8e89fe35ebc445e4c4b19663ba9655dfeb8ba5cada2172aeb033eeb9f9eb939"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
V94_BIN = str(plain_image_path(
    "_v94_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75-427.SAR1_plain_image.bin"))
V94_SHA = "cd971c05d483fe9cc657144d724b7cfdbeb946719a968094f8fcb34ee4c78001"

# =================================================================================================
# 🛑 THE THREE SOURCE CELLS -- named constants so swapping one is a ONE-LINE change.
# =================================================================================================
SRC_427 = 0x6B70        # gp-0x6b70  PRIMARY: Stage-2 output / PID reference. Clamped +-8192.
SRC_ACC = 0x374C        # gp-0x374c  REGRESSOR: the 32-bit Stage-1 accumulator. Telemetered >> 4.
SRC_MODE = 0x674E       # gp-0x674e  the authority-curve MODE index. Static config byte.

SRC_427_CLAMP = 8192            # 0xC6200, read from the image and asserted
ACC_FW_SHIFT = 4                # the firmware's OWN >>4 (0x38236) -- mirrored exactly
ACC_HI_SHIFT = 12               # byte4 b5:b4 = |v| >> 12
ACC_HI_SAT = 3                  # ...saturating at 3  <=>  |v| >= 3<<12 = 12288
ACC_LO_SHIFT = 10               # byte7 b7 = bit 1 of (|v| >> 10) = bit 11 of |v|
ACC_LSB = 1 << (ACC_HI_SHIFT - 1)       # 2048 counts per M step
MODE_THRESHOLD = 28             # b3 = (gp-0x674e < 28). >= 28 is the RULE-7 alarm (Y[last] = 51).

# 🛑 NO-GO, and pinned so it cannot be flipped without reading the header. See GATE 2 (6).
LEVER_C63A6 = None

# =================================================================================================
# PART 1 -- THE CALIBRATION THAT MUST NOT MOVE. V96 writes ZERO calibration bytes; this section
#           exists to PROVE that, cell by cell, against the V92 image and against V94's cut.
# =================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_N_MODES = 34                  # 🛑 modes 0..33. A GIVEN BOUND, not a walk.
FRICTION_ARRAY_END = FRICTION_PTR_ARRAY + FRICTION_N_MODES * 4      # 0xCBEFC
REC_N_OFF, REC_X_OFF, REC_Y_OFF, REC_PAD_OFF, REC_LEN = 0x00, 0x02, 0x08, 0x0E, 0x10

MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)        # TVCA4: 24/25 MANUAL, 26/27 ENGAGED
FRICTION_X = (0, 1280, 5760)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)        # V92's x1.5 on the ENGAGED columns -- CARRIED

# 🛑 the five calibration sites V94 moved and V96 must NOT carry. Read from V94's own image below.
#    Note V92 is STOCK on three of them and x1.5 on two -- "revert to V92" != "revert to stock".
V94_CAL_DELTA = {
    0xC640A: (-8192, -6144, "FALLBACK-2 flat gain in FUN_00036c12  (V92 = STOCK)"),
    0xC640C: (-3277, -2458, "FALLBACK-1 flat gain in FUN_00036c12  (V92 = STOCK)"),
}
V94_FRICTION_ROWS = {24: (-4915, -2867, -983), 26: (-2458, -1434, -492), 27: (-2458, -1434, -492)}

# =================================================================================================
# PART 2 -- THE INSTRUMENT
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V92_CAVE = bytes.fromhex(
    "003a243742946032ae05483a24379e946032ae05443a6032a305423a2437269406368c010606"
    "f4fca305413ac43a483a8437edeac636070007314437ecea24377e95e53f7f72e731003aa305"
    "413a2437da946032ae0580316e32a305423ac63aa437efeac6363f0007314437efea2436e8ea"
    "7f00")

# ---- structural anchors, all READ FROM THE IMAGE and asserted -----------------------------------
#    addr : (bytes, what)   -- every access site to each of the three source cells
SRC_SITES = {
    SRC_427: {0x38006: ("246f9094", "ld.h  -0x6b70[gp],r13   FUN_00037fe6 -- the ONLY reader"),
              0x382D2: ("645f9094", "st.h  -0x6b70[gp],r11   FUN_00038148 -- the ONLY writer")},
    SRC_ACC: {0x381FE: ("2437b5c8", "ld.w  -0x374c[gp],r6    FUN_00038148 -- the ONLY reader"),
              0x38230: ("6437b5c8", "st.w  r6,-0x374c[gp]    FUN_00038148 -- the ONLY writer")},
    SRC_MODE: {0x28FC8: ("8467b398", "ld.bu -0x674e[gp],r12"),
               0x29AA0: ("8467b398", "ld.bu -0x674e[gp],r12"),
               0x29B7C: ("8467b398", "ld.bu -0x674e[gp],r12"),
               0x29CC4: ("8467b398", "ld.bu -0x674e[gp],r12"),
               0x2A9A6: ("8477b398", "ld.bu -0x674e[gp],r14"),
               0x2ABBA: ("8477b398", "ld.bu -0x674e[gp],r14"),
               0x4272A: ("4447b298", "st.b  r8,-0x674e[gp]    the ONLY writer, config-table init")},
}
# 🛑 Honda's own gp-0x67fa state gate on FUN_00038148 -- asserted so the REJECTION reasoning in the
#    header rests on bytes, not on a claim. V96 does NOT encode this predicate; see the header.
STATE_GATE_SITES = {
    0x221BC: ("84370798", "ld.bu -0x67fa[gp],r6      the assist STATE byte"),
    0x221C0: ("017a", "mov   0x1,r15"),
    0x221C2: ("c6460f00", "andi  0xf,r6,r8           s = state & 0xF"),
    0x221C6: ("e87fc2c8", "shl   r8,r15,r25          🛑 FORMAT IX VARIABLE SHIFT -- no twin exists "
                          "for our register set, so the cave cannot mirror this"),
    0x221D6: ("d9e63008", "andi  0x830,r25,r28       0x830 = bits 4,5,11 ⇒ s in {4,5,11}"),
    0x22672: ("e0e1", "cmp   r0,r28"),
    0x22674: ("b205", "be    0x2267a             ⇒ FUN_00038148 is SKIPPED iff r28 == 0"),
    0x22676: ("81ffd25a", "jarl  0x38148,lp          the gated call itself"),
}
STATE_GATE_MASK = 0x830

FW_SHIFT_SITE = (0x38236, "a432", "FUN_00038148's OWN `sar 0x4,r6` -- the instruction that forms "
                                  "the (gp-0x374c >> 4) term of iVar6. V96 mirrors it EXACTLY.")
CLAMP_SITE = (0xC6200, SRC_427_CLAMP, "tp+0x7200 -- gp-0x6b70's hard clamp")
# the benign 32-bit RMW over 0x14A bytes 4..7 that V92's scan method could not see
WORD_RMW = {
    0x2194A: ("2477edea", "ld.w  -0x1514[gp],r14   FUN_0002193e"),
    0x21954: ("2f06ff0000ff", "mov 0xff0000ff,r15  -- the mask, 6-byte form"),
    0x21960: ("4f71", "and   r15,r14           preserves byte4 (bits 7:0) and byte7 (bits 31:24)"),
    0x21964: ("6477edea", "st.w  r14,-0x1514[gp]   FUN_0002193e"),
}
WORD_RMW_MASK = 0xFF0000FF

PAYLOAD = bytes.fromhex(
    # ---- byte 4 field ---------------------------------------------------------------------------
    "003a"          # +0x00  mov   0x0,r7
    "24379094"      # +0x02  ld.h  -0x6b70[gp],r6      PRIMARY -- Stage-2 output / PID reference
    "6032" "ae05"   # +0x06  cmp 0x0,r6 / bge +4 -> +0x0C
    "483a"          # +0x0A  add   0x8,r7              b7 = gp-0x6b70 < 0   SIGN for CAN 427
    "2437b5c8"      # +0x0C  ld.w  -0x374c[gp],r6      REGRESSOR -- the 32-bit accumulator
    "a432"          # +0x10  sar   0x4,r6              v = gp-0x374c >> 4   (the FIRMWARE's shift)
    "6032" "ae05"   # +0x12  cmp 0x0,r6 / bge +4 -> +0x18
    "443a"          # +0x16  add   0x4,r7              b6 = v < 0           SIGN of the regressor
    "6032" "ae05"   # +0x18  cmp 0x0,r6 / bge +4 -> +0x1E   (same r6 sample)
    "8031"          # +0x1C  subr  r0,r6               r6 = |v|   (NOT satsubr 3080)
    "ac32"          # +0x1E  sar   0xc,r6              |v| >> 12
    "6332"          # +0x20  cmp   0x3,r6
    "a305"          # +0x22  bnh   +4 -> +0x26         skip iff r6 <=u 3
    "0332"          # +0x24  mov   0x3,r6              🛑 SATURATE. Also confines r6 to bits 1:0,
                    #                                  so the magnitude can NEVER reach the SIGNS.
    "0639"          # +0x26  or    r6,r7               b5:b4 = Mhi
    "c43a"          # +0x28  shl   0x4,r7              -> bits 7:4
    "8437b398"      # +0x2A  ld.bu -0x674e[gp],r6      the AUTHORITY-CURVE MODE index
    "0606" "e4ff"   # +0x2E  addi  -0x1c,r6,r0         flags only; CY|Z = (r6 >=u 28)
    "a305"          # +0x32  bnh   +4 -> +0x36         skip iff mode >= 28
    "483a"          # +0x34  add   0x8,r7              b3 = (gp-0x674e < 28)   EXPECTED 1
    "8437edea"      # +0x36  ld.bu -0x1514[gp],r6
    "c6360700"      # +0x3A  andi  0x7,r6,r6           keep Honda's bits 2:0
    "0731"          # +0x3E  or    r7,r6
    "4437ecea"      # +0x40  st.b  r6,-0x1514[gp]      CAN 0x14A byte 4
    # ---- byte 7 field ---------------------------------------------------------------------------
    "2437b5c8"      # +0x44  ld.w  -0x374c[gp],r6      REGRESSOR, re-read (atomic: interrupts off)
    "a432"          # +0x48  sar   0x4,r6              v
    "6032" "ae05"   # +0x4A  cmp 0x0,r6 / bge +4 -> +0x50
    "8031"          # +0x4E  subr  r0,r6               |v|
    "aa32"          # +0x50  sar   0xa,r6              |v| >> 10
    "c6360200"      # +0x52  andi  0x2,r6,r6           bit 11 of |v|, already at position 1
    "013a"          # +0x56  mov   0x1,r7              FINGERPRINT -- byte7 b6, ALWAYS 1
    "0639"          # +0x58  or    r6,r7               r7 in {1,3}   (bits are disjoint)
    "c63a"          # +0x5A  shl   0x6,r7              -> bits 7:6  {0x40, 0xC0}
    "a437efea"      # +0x5C  ld.bu -0x1511[gp],r6
    "c6363f00"      # +0x60  andi  0x3f,r6,r6          keep Honda's bits 5:0
    "0731"          # +0x64  or    r7,r6
    "4437efea"      # +0x66  st.b  r6,-0x1511[gp]      CAN 0x14A byte 7
    # ---- return -----------------------------------------------------------------------------------
    "2436e8ea"      # +0x6A  movea -0x1518,gp,r6       restore the hooked instruction
    "7f00")         # +0x6E  jmp   [lp]

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp -- V90/V92's
DI_CALL_ADDR, DI_TARGET = 0x55C0A, 0x1FA42                   # jarl FUN_0001fa42  (interrupts OFF)
EI_CALL_ADDR, EI_TARGET = 0x55C2E, 0x1FA72                   # jarl FUN_0001fa72  (interrupts ON)
CKSUM_CALL_ADDR = 0x55C18                                    # jarl FUN_00057b24(gp-0x1518,8,0x14a)

R427_ADDR = 0x55DF2                          # hw2 of `ld.h ..[gp],r6` inside the 0x1AB builder
R427_OLD, R427_NEW = 0x6BBE, SRC_427         # both negative, both even => ld.h form, asserted
R427_SAR_ADDR = 0x55E10
# 🛑 V92's shift is a4 (sar 4). BUILD-LINEAGE's "a3 -> a1" is against V90, NOT against V92.
R427_SAR_OLD, R427_SAR_NEW = bytes.fromhex("a432"), bytes.fromhex("a632")   # sar 4 -> sar 6
R427_SHIFT_NEW = 6
R427_MUL, R427_FIELD_MAX = 5, 0x3FF          # clamp(|src| * 5 >> shift, 0, 0x3FF)

# 🛑 EVERY BYTE OF THE PAYLOAD, and the address it is COPIED FROM. Coverage asserted 112/112.
TWINS = [
    (0x00, 2, CAVE_BASE + 0x00, "mov   0x0,r7                   V92 cave +0x00"),
    (0x02, 2, CAVE_BASE + 0x02, "ld.h hw1 `2437`                V92 cave +0x02"),
    (0x04, 2, 0x38008, "hw2 -0x6b70                    HONDA: ld.h -0x6b70,gp,r13 @0x38006 -- the"
                       " ONLY reader of the cell V96 puts on CAN 427"),
    (0x06, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V92 cave +0x06"),
    (0x08, 2, CAVE_BASE + 0x08, "bge   +4                       V92 cave +0x08"),
    (0x0A, 2, CAVE_BASE + 0x0A, "add   0x8,r7                   V92 cave +0x0A"),
    (0x0C, 4, 0x381FE, "ld.w  -0x374c[gp],r6           HONDA: FUN_00038148's OWN read of the"
                       " accumulator -- whole 4 bytes, so ld.w vs ld.h cannot be got wrong"),
    (0x10, 2, FW_SHIFT_SITE[0], "sar   0x4,r6                   HONDA @0x38236 -- the FIRMWARE's"
                                " OWN (gp-0x374c >> 4), same register"),
    (0x12, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V92 cave +0x06"),
    (0x14, 2, CAVE_BASE + 0x08, "bge   +4                       V92 cave +0x08"),
    (0x16, 2, CAVE_BASE + 0x14, "add   0x4,r7                   V92 cave +0x14"),
    (0x18, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V92 cave +0x06"),
    (0x1A, 2, CAVE_BASE + 0x08, "bge   +4                       V92 cave +0x08"),
    (0x1C, 2, CAVE_BASE + 0x56, "subr  r0,r6  `8031`            V92 cave +0x56  🛑 NOT satsubr 3080"),
    (0x1E, 2, 0x2C0BA, "sar   0xc,r6 `ac32`            HONDA @0x2C0BA"),
    (0x20, 2, 0x1695A, "cmp   0x3,r6 `6332`            HONDA @0x1695A"),
    (0x22, 2, CAVE_BASE + 0x18, "bnh   +4     `a305`            V92 cave +0x18"),
    (0x24, 2, 0x14B88, "mov   0x3,r6 `0332`            HONDA @0x14B88"),
    (0x26, 2, 0x1C1C4, "or    r6,r7  `0639`            HONDA @0x1C1C4 -- Honda's own instruction"
                       " at 0x1C1C2 is `shl 0x4,r7`: the identical field-packing idiom"),
    (0x28, 2, CAVE_BASE + 0x2C, "shl   0x4,r7 `c43a`            V92 cave +0x2C"),
    (0x2A, 2, CAVE_BASE + 0x30, "ld.bu hw1 `8437` (gp,r6)       V92 cave +0x30 (op 0x3C, EVEN disp)"),
    (0x2C, 2, 0x28FCA, "hw2 -0x674e  `b398`            HONDA: ld.bu -0x674e,gp,r12 @0x28FC8 --"
                       " note Honda sets hw2 bit 0 as a don't-care MARKER; copied, not computed"),
    (0x2E, 2, 0x498E0, "addi hw1 `0606` (imm,r6,r0)    HONDA @0x498E0 -- Honda's own compiled"
                       " unsigned range-test idiom, r0 = discard, flags only"),
    # +0x30 the imm16 -0x1c -- DERIVED, pure data, see DERIVED_IMM
    (0x32, 2, CAVE_BASE + 0x18, "bnh   +4     `a305`            V92 cave +0x18"),
    (0x34, 2, CAVE_BASE + 0x0A, "add   0x8,r7 `483a`            V92 cave +0x0A"),
    (0x36, 14, CAVE_BASE + 0x30, "the byte4 RMW epilogue, 14 B   V92 cave +0x30, byte-identical"),
    (0x44, 4, 0x381FE, "ld.w  -0x374c[gp],r6           HONDA @0x381FE, whole"),
    (0x48, 2, FW_SHIFT_SITE[0], "sar   0x4,r6                   HONDA @0x38236"),
    (0x4A, 2, CAVE_BASE + 0x06, "cmp   0x0,r6                   V92 cave +0x06"),
    (0x4C, 2, CAVE_BASE + 0x08, "bge   +4                       V92 cave +0x08"),
    (0x4E, 2, CAVE_BASE + 0x56, "subr  r0,r6                    V92 cave +0x56"),
    (0x50, 2, 0x2C13C, "sar   0xa,r6 `aa32`            HONDA @0x2C13C"),
    (0x52, 2, CAVE_BASE + 0x34, "andi hw1 `c636` (imm,r6,r6)    V92 cave +0x34"),
    # +0x54 the imm16 0x0002 -- DERIVED, pure data, see DERIVED_IMM
    (0x56, 2, 0x14D40, "mov   0x1,r7 `013a`            HONDA @0x14D40"),
    (0x58, 2, 0x1C1C4, "or    r6,r7  `0639`            HONDA @0x1C1C4"),
    (0x5A, 2, CAVE_BASE + 0x5E, "shl   0x6,r7 `c63a`            V92 cave +0x5E"),
    (0x5C, 4, CAVE_BASE + 0x60, "ld.bu -0x1511[gp],r6           V92 cave +0x60"),
    (0x60, 4, CAVE_BASE + 0x64, "andi  0x3f,r6,r6               V92 cave +0x64"),
    (0x64, 2, CAVE_BASE + 0x68, "or    r7,r6                    V92 cave +0x68"),
    (0x66, 4, CAVE_BASE + 0x6A, "st.b  r6,-0x1511[gp]           V92 cave +0x6A"),
    (0x6A, 6, CAVE_BASE + 0x6E, "movea -0x1518,gp,r6 / jmp [lp] V92 cave +0x6E, the return"),
]

# 🛑 The ONLY payload bytes with no twin: two pure-data imm16 halfwords. No encoding ambiguity
#    exists in an imm16 -- it is struct.pack and nothing else. Each is DERIVED from the constant
#    the rung map requires, asserted here AND again from the built image.
DERIVED_IMM = [
    (0x30, lambda: struct.pack("<h", -MODE_THRESHOLD),
     f"addi imm16 = -0x{MODE_THRESHOLD:02X} ⇒ after this add, CY|Z == (gp-0x674e >=u "
     f"{MODE_THRESHOLD}); `bnh` takes CY|Z, so b3 = (mode < {MODE_THRESHOLD})"),
    (0x54, lambda: struct.pack("<H", 1 << 1),
     f"andi imm16 = 0x0002 = bit {ACC_LO_SHIFT + 1} of |v|, i.e. M bit 0. The mask also makes the "
     f"byte7 FINGERPRINT immune to any value of the accumulator"),
]

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE. Asserted on the base, on the built image, and on the shipped .rwd.
# =================================================================================================
FROZEN = {
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK CLAMP -- Honda's 511, one under its own 512 trip"),
    0xC40D2: (2, 204, "K1 modelled Coulomb friction -- V89's lever, CARRIED unchanged"),
    0xC4080: (2, 0, "K0 pure-Coulomb arm -- the recorded NEVER-RAISE relay hazard, stays 0"),
    0xC40BC: (2, 600, "friction relay gate -- 600. 6000 measured 2.3x WORSE; DO NOT restore it"),
    0xC40D0: (2, 408, "friction EMA alpha (16.7 Hz)"),
    0xC40D4: (2, 573, "command-branch EMA -- V86's FALSIFIED lever"),
    0xC40D8: (2, 3686, "friction-family constant"),
    0xC646E: (2, 1428, "INERTIA/damping gain -- unmeasured sizing figure"),
    0xC63A0: (2, 1024, "Path-2 lane weight, gp-0x6bd0 (damper) -- moved V72..V81, back at 1024"),
    0xC63A2: (2, 1024, "Path-2 lane weight, gp-0x6bbe (boost) -- virgin on all 85 images"),
    0xC63A4: (2, 1024, "Path-2 lane weight, gp-0x6b46 -- virgin on all 85 images"),
    0xC63A6: (2, 1024, "🛑 Path-2 lane weight, gp-0x6b26 -- the NO-GO lever. V96 MEASURES the LERP "
                       "slope that blocks it; it does NOT move the cell"),
    0xC63A8: (2, 1024, "Path-2 lane weight, gp-0x6b4e -- virgin on all 85 images"),
    0xC63AA: (2, 1024, "Path-2 lane weight, gp-0x6b4c -- virgin on all 85 images"),
    0xC63AC: (2, 102, "Stage-1 IIR alpha -- fc ~15.9 Hz at the 1 kHz task rate"),
    0xC63AE: (2, 1024, "Stage-2 input scale"),
    0xC6200: (2, 8192, "🛑 gp-0x6b70's OUTPUT CLAMP -- the number the 427 shift is sized against"),
    0xC6468: (2, 2639, "model output gain -- SHARED, 5 readers"),
    0xC6446: (2, 5244, "🛑 Lever B ARM -- V88's 5244. Silently reverted at a rebase THREE times "
                       "(V69-V71b, V72-V76, V87). Asserted on base, built image and shipped .rwd"),
    0x3AA96: (1, 0xFB, "🛑 Lever B GATE -- V88's 0xFB (stock 0xC5). The OTHER half; both or neither"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC6CD0: (2, 3564, "private forward LKAS gain = 4.000x, NEVER lower"),
    0xC62EA: (2, 0, "steer-to-zero"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC640A: (2, 0xE000, "🛑 FALLBACK-2 = -8192 (STOCK) -- V94 cut it to -6144"),
    0xC640C: (2, 0xF333, "🛑 FALLBACK-1 = -3277 (STOCK) -- V94 cut it to -2458"),
    0x454FE: (1, 0xB5, "🛑 V42's ratchet fix -- lost V53..V70, restored at V80. ⚠ MEASURED INERT "
                       "(gp-0x67fa's reachable set excludes the guarded state). Carried because it "
                       "is FREE, not because it acts. Claim nothing for it."),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC64A1: (1, 1, "🛑 READ-ONLY"),
    # 🛑 the authority curve -- virgin on all 90 images. V96 MEASURES which curve is selected.
    0xE547C: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched; value read from the base"),
    0xE5404: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE52FC: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
    0xE5284: (2, None, "🛑 AUTHORITY CURVE -- virgin. NOT touched"),
}

VARIANT_TOKEN = "V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v96_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V96-{TAG}-0x{START:X}-0x{END:X}.rwd")

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
# than checking the bytes against the string it was handed. Every form confirmed in GhidraMCP.
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
    if op == 0x10:
        return f"mov   0x{imm5:x},{rn(reg2)}", 2, "mov", imm5, {reg2}, {reg2}
    if op == 0x12:
        return f"add   0x{imm5:x},{rn(reg2)}", 2, "add", imm5, {reg2}, {reg2}
    if op == 0x13:
        return f"cmp   0x{imm5:x},{rn(reg2)}", 2, "cmp", imm5, set(), {reg2}
    if op == 0x0F:
        return f"cmp   {rn(reg1)},{rn(reg2)}", 2, "cmp", None, set(), {reg1, reg2}
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


def disassemble_cave(img, base, length):
    out, off = [], 0
    while off < length:
        text, n, kind, operand, writes, refs = decode(img, base + off)
        out.append((off, base + off, rd(img, base + off, n).hex(), text, kind, operand,
                    writes, refs))
        off += n
    assert off == length, f"the last instruction overruns the payload by {off - length} byte(s)"
    return out


# The rung table, as INTENT. The built image is checked against THIS, not against the spec string.
EXPECTED = [
    (0x00, "mov   0x0,r7", ""),
    (0x02, "ld.h  -0x6b70[gp],r6", "PRIMARY -- Stage-2 output / PID reference"),
    (0x06, "cmp   0x0,r6", ""), (0x08, "bge   +4", "-> +0x0C"),
    (0x0A, "add   0x8,r7", "b7 = gp-0x6b70 < 0   SIGN for CAN 427"),
    (0x0C, "ld.w  -0x374c[gp],r6", "REGRESSOR -- the 32-bit accumulator"),
    (0x10, "sar   0x4,r6", "v = gp-0x374c >> 4   (the FIRMWARE's own shift @0x38236)"),
    (0x12, "cmp   0x0,r6", ""), (0x14, "bge   +4", "-> +0x18"),
    (0x16, "add   0x4,r7", "b6 = v < 0   SIGN of the regressor"),
    (0x18, "cmp   0x0,r6", "same r6 sample"), (0x1A, "bge   +4", "-> +0x1E"),
    (0x1C, "subr  r0,r6", "r6 = |v|"),
    (0x1E, "sar   0xc,r6", "|v| >> 12"),
    (0x20, "cmp   0x3,r6", ""), (0x22, "bnh   +4", "-> +0x26, skip iff r6 <=u 3"),
    (0x24, "mov   0x3,r6", "🛑 SATURATE -- also confines r6 to bits 1:0"),
    (0x26, "or    r6,r7", "b5:b4 = Mhi"),
    (0x28, "shl   0x4,r7", "-> bits 7:4"),
    (0x2A, "ld.bu -0x674e[gp],r6", "the AUTHORITY-CURVE MODE index"),
    (0x2E, f"addi  {-MODE_THRESHOLD:#x},r6,r0", "flags only; CY|Z = (mode >=u 28)"),
    (0x32, "bnh   +4", "-> +0x36, skip iff mode >= 28"),
    (0x34, "add   0x8,r7", "b3 = (gp-0x674e < 28)   EXPECTED 1"),
    (0x36, "ld.bu -0x1514[gp],r6", ""),
    (0x3A, "andi  0x7,r6,r6", "keep Honda's bits 2:0"),
    (0x3E, "or    r7,r6", ""),
    (0x40, "st.b  r6,-0x1514[gp]", "CAN 0x14A byte 4"),
    (0x44, "ld.w  -0x374c[gp],r6", "REGRESSOR, re-read (atomic -- interrupts are off)"),
    (0x48, "sar   0x4,r6", "v"),
    (0x4A, "cmp   0x0,r6", ""), (0x4C, "bge   +4", "-> +0x50"),
    (0x4E, "subr  r0,r6", "r6 = |v|"),
    (0x50, "sar   0xa,r6", "|v| >> 10"),
    (0x52, "andi  0x2,r6,r6", "M bit 0, already at position 1"),
    (0x56, "mov   0x1,r7", "FINGERPRINT -- byte7 b6, ALWAYS 1"),
    (0x58, "or    r6,r7", "r7 in {1,3}   (bits are disjoint)"),
    (0x5A, "shl   0x6,r7", "-> bits 7:6"),
    (0x5C, "ld.bu -0x1511[gp],r6", ""),
    (0x60, "andi  0x3f,r6,r6", "keep Honda's bits 5:0"),
    (0x64, "or    r7,r6", ""),
    (0x66, "st.b  r6,-0x1511[gp]", "CAN 0x14A byte 7  -- 🛑 THE IDENTITY"),
    (0x6A, "movea -0x1518,gp,r6", "restore the hooked instruction"),
    (0x6E, "jmp   [lp]", ""),
]

M32 = 0xFFFFFFFF


def wire_byte4(x6b70, acc32, mode, honda_bits=0x7):
    """Mirrors the cave's integer arithmetic EXACTLY, one line per instruction offset.

    `acc32` is the 32-bit signed value of gp-0x374c; `mode` is the raw byte at gp-0x674e.
    """
    r7 = 0
    r6 = x6b70                                   # +0x02 ld.h   (SIGN-EXTENDS)
    if not r6 >= 0:        r7 += 8               # +0x06 cmp / +0x08 bge   b7 SIGN of gp-0x6b70
    r6 = acc32                                   # +0x0C ld.w   (full 32 bits)
    r6 = r6 >> ACC_FW_SHIFT                      # +0x10 sar 0x4  -- Python >> IS arithmetic
    if not r6 >= 0:        r7 += 4               # +0x12 cmp / +0x14 bge   b6 SIGN of v
    if not r6 >= 0:        r6 = 0 - r6           # +0x18 cmp / +0x1A bge / +0x1C subr  r6 = |v|
    r6 = r6 >> ACC_HI_SHIFT                      # +0x1E sar 0xc
    if not r6 <= ACC_HI_SAT: r6 = ACC_HI_SAT     # +0x20 cmp 0x3 / +0x22 bnh / +0x24 mov 0x3
    assert r7 & 0x3 == 0, "r7 bits 1:0 were not zero before the `or` -- the OR is not an ADD here"
    assert 0 <= r6 <= ACC_HI_SAT, "the saturation failed -- the magnitude could reach the SIGN bits"
    r7 = (r7 | r6) & M32                         # +0x26 or r6,r7
    r7 = (r7 << 4) & M32                         # +0x28 shl 0x4
    m = mode & 0xFF                              # +0x2A ld.bu  (ZERO-EXTENDS)
    #  +0x2E `addi -28,r6,r0` sets CY = carry-OUT = (m >=u 28) and Z = (m == 28).
    #  +0x32 `bnh` takes CY|Z, which is exactly (m >=u 28) since Z implies CY here.
    if not m >= MODE_THRESHOLD: r7 += 8          # +0x34 add 0x8,r7   b3 = mode < 28
    return ((honda_bits & 0x7) | (r7 & 0xFF)) & 0xFF


def wire_byte7(acc32, honda_bits=0x3F):
    """Mirrors the cave's integer arithmetic EXACTLY, one line per instruction offset."""
    r6 = acc32                                   # +0x44 ld.w
    r6 = r6 >> ACC_FW_SHIFT                      # +0x48 sar 0x4
    if not r6 >= 0:        r6 = 0 - r6           # +0x4A cmp / +0x4C bge / +0x4E subr  r6 = |v|
    r6 = r6 >> ACC_LO_SHIFT                      # +0x50 sar 0xa
    r6 = r6 & 0x2                                # +0x52 andi 0x2  -- makes the FINGERPRINT immune
    r7 = 1                                       # +0x56 mov 0x1,r7   THE FINGERPRINT
    assert r7 & 0x2 == 0, "the fingerprint bit collides with the magnitude bit"
    r7 = (r7 | r6) & M32                         # +0x58 or r6,r7
    return ((honda_bits & 0x3F) | ((r7 << 6) & M32)) & 0xFF        # +0x5A shl 0x6


def decode_wire(b4, b7):
    """The SCORER's reconstruction, written here so it is pre-registered WITH the build."""
    sign70 = -1 if (b4 & 0x80) else +1
    signv = -1 if (b4 & 0x40) else +1
    mhi = (b4 >> 4) & 0x3
    mlo = (b7 >> 7) & 1
    saturated = (mhi == ACC_HI_SAT)
    m = 2 * mhi + mlo
    v_abs = None if saturated else m * ACC_LSB          # None == ">= 12288, saturated"
    return dict(sign70=sign70, signv=signv, m=m, saturated=saturated,
                v=None if saturated else signv * v_abs,
                mode_lt28=bool(b4 & 0x08), fingerprint=bool(b7 & 0x40))


def assert_rung_semantics():
    """Corner grid over both signs, every quantisation boundary and every reachable extreme."""
    accs = []
    for k in range(0, 9):
        for d in (-1, 0, 1):
            accs += [(k * ACC_LSB + d) << ACC_FW_SHIFT, (-(k * ACC_LSB) + d) << ACC_FW_SHIFT]
    accs += [0, 1, -1, 15, -15, 1 << 20, -(1 << 20), 68600 << ACC_FW_SHIFT,
             -(68600 << ACC_FW_SHIFT), (1 << 30), -(1 << 30)]
    accs = sorted(set(accs))
    prims = [-32768, -8193, -8192, -8191, -4096, -1, 0, 1, 4096, 8191, 8192, 8193, 32767]
    modes = [0, 1, 6, 7, 8, 27, 28, 29, 39, 40, 127, 128, 200, 255]
    n = 0
    for a in prims:
        for acc in accs:
            for md in (7, 28):
                w4, w7 = wire_byte4(a, acc, md), wire_byte7(acc)
                v = acc >> ACC_FW_SHIFT
                assert w7 & 0x40, "byte7 b6 FINGERPRINT is not 1 -- THE IDENTITY would not fire"
                assert bool(w4 & 0x80) == (a < 0), "byte4 b7 is not sign(gp-0x6b70)"
                assert bool(w4 & 0x40) == (v < 0), "byte4 b6 is not sign(gp-0x374c>>4)"
                assert w4 & 0x07 == 0x07, "Honda's byte4 bits 2:0 were not preserved"
                assert w7 & 0x3F == 0x3F, "Honda's byte7 bits 5:0 were not preserved"
                d = decode_wire(w4, w7)
                assert d["sign70"] == (-1 if a < 0 else 1), "the gp-0x6b70 sign does not round-trip"
                assert d["signv"] == (-1 if v < 0 else 1), "the regressor sign does not round-trip"
                # THE load-bearing claim: below saturation, M IS the linear quantisation of |v|
                if abs(v) < ACC_HI_SAT * (1 << ACC_HI_SHIFT):
                    assert not d["saturated"], f"spurious saturation at v={v}"
                    assert d["m"] == abs(v) >> (ACC_HI_SHIFT - 1), \
                        f"M != |v|>>{ACC_HI_SHIFT - 1} at v={v}: got {d['m']}"
                    assert abs(d["v"]) <= abs(v), "the reconstruction is not a TRUNCATION of |v|"
                    assert abs(v) - abs(d["v"]) < ACC_LSB, "quantisation error exceeds one LSB"
                else:
                    assert d["saturated"], f"failed to flag saturation at v={v}"
                n += 1
    print(f"    ✅ {n} corner cases, ZERO deviations. M == |gp-0x374c>>4| >> {ACC_HI_SHIFT - 1} "
          f"EXACTLY below saturation, and Mhi == {ACC_HI_SAT} flags |v| >= "
          f"{ACC_HI_SAT << ACC_HI_SHIFT} on every input up to +-2^30")
    print(f"    ✅ the two SIGN bits and the FINGERPRINT held on EVERY input, including accumulator "
          f"values far outside any plausible range -- the saturating `mov 0x3,r6` confines the "
          f"magnitude to bits 1:0, so it can never corrupt them")

    # ---- the mode rung, exhaustively over all 256 byte values -----------------------------------
    bad = [m for m in range(256) if bool(wire_byte4(0, 0, m) & 0x08) != (m < MODE_THRESHOLD)]
    assert not bad, f"the mode rung is wrong at {bad[:8]}"
    print(f"    ✅ mode rung: b3 == (gp-0x674e < {MODE_THRESHOLD}) on ALL 256 byte values -- the "
          f"`addi {-MODE_THRESHOLD:#x},r6,r0` + `bnh` unsigned-range idiom is proven by exhaustion, "
          f"not argued, so no `bne` and NO NEW BRANCH CONDITION is needed")
    for md in modes:
        assert bool(wire_byte4(0, 0, md) & 0x08) == (md < MODE_THRESHOLD)

    # ---- the reachable codeword sets = the map validators ---------------------------------------
    codes7 = {wire_byte7(acc, 0) >> 6 for acc in accs}
    assert codes7 == {1, 3}, f"byte7[7:6] reachable set is {sorted(codes7)}, expected {{1,3}}"
    print(f"    ✅ byte7[7:6] in {{1,3}} on EVERY input ⇒ b6 ≡ 1 ⇒ byte7[7:6] != 0 is STRUCTURAL, "
          f"not measurand-dependent. byte7[7:6] == 2 is IMPOSSIBLE. [MAP VALIDATOR 3]")
    par = {wire_byte4(a, acc, 7) & 0x08 for a in prims for acc in accs}
    assert par == {0x08}, "b3 is not constant for a fixed mode -- MAP VALIDATOR 1 is void"
    par28 = {wire_byte4(a, acc, 28) & 0x08 for a in prims for acc in accs}
    assert par28 == {0x00}, "b3 does not flip at the threshold -- the mode rung is inert"
    print(f"    ✅ b3 is CONSTANT for a fixed gp-0x674e (1 when < {MODE_THRESHOLD}, 0 when >=) ⇒ "
          f"[MAP VALIDATOR 1] per-drive byte4 alignment, and [MAP VALIDATOR 2] byte4[7:3] is ODD "
          f"on every frame in the EXPECTED case, preserving the ~50-build convention")
    assert LEVER_C63A6 is None


def build():
    # ==============================================================================================
    # 1. THE BASE
    # ==============================================================================================
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    print("=" * 102)
    print("  V96 -- V92's CALIBRATION UNCHANGED, BYTE FOR BYTE, + a 112-byte INSTRUMENT")
    print("         CAN 427   = clamp(|gp-0x6b70| * 5 >> 6, 0, 0x3FF), signed via 0x14A byte4 b7")
    print("         0x14A     = sign+3-bit SATURATING (gp-0x374c >> 4), + the gp-0x674e MODE rung")
    print("         ⇒ the empirical slope of the pair IS the Path-2 LERP's local -f'")
    print("         🛑 ZERO CALIBRATION BYTES. V94's 0xCBE74 cut is reverted BY CONSTRUCTION.")
    print("         🛑 THIS IS AN INSTRUMENT, NOT A FIX. Nothing here is claimed to help the car.")
    print(f"\n    base   {os.path.basename(BASE_BIN)}")
    print(f"    sha256 {base_sha}")
    print("=" * 102)

    print("\n  [1] BASE IMAGE")
    check(len(base) == 0x100000, f"base length = {len(base)} = 0x{len(base):X} bytes (1 MiB)")
    check(base_sha == BASE_SHA, f"base sha256 == V92's {BASE_SHA}")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")
    check(LEVER_C63A6 is None,
          "🛑 LEVER_C63A6 is None -- the 0xC63A6 lever is a NO-GO (Path-2 sign unresolved) and is "
          "NOT in this build. V96 MEASURES the slope that blocks it")

    # ==============================================================================================
    # 2. tp ANCHOR -- the off-by-0x1000 trap has recurred FIVE times. Anchor before trusting.
    # ==============================================================================================
    print("\n  [2] tp ANCHOR -- every tp+off is COMPUTED, never written by eye")
    check(TP + 0x73A8 == 0xC63A8 and u16(base, TP + 0x73A8) == 1024,
          f"tp = 0x{TP:05X} ⇒ tp+0x73A8 = 0x{TP + 0x73A8:05X} = {u16(base, TP + 0x73A8)}. "
          f"🛑 NOT 0x{TP + 0x73A8 + 0x1000:05X}")
    check(TP + 0x7200 == CLAMP_SITE[0] and u16(base, TP + 0x7200) == SRC_427_CLAMP,
          f"tp+0x7200 = 0x{TP + 0x7200:05X} = {u16(base, TP + 0x7200)} -- {CLAMP_SITE[2]}. "
          f"This is the number the 427 shift is sized against")

    # ==============================================================================================
    # 3. THE THREE SOURCE CELLS -- every access site, from the image, TWO methods
    # ==============================================================================================
    print("\n  [3] 🛑 GATE 1 -- every access site to every source cell, byte-exact from the image")
    for disp, sites in ((SRC_427, SRC_SITES[SRC_427]), (SRC_ACC, SRC_SITES[SRC_ACC]),
                        (SRC_MODE, SRC_SITES[SRC_MODE])):
        for a, (hx, what) in sorted(sites.items()):
            check(rd(base, a, len(hx) // 2).hex() == hx, f"0x{a:05X} {hx}  {what}")
    # INDEPENDENT whole-image byte scan (the required second method), BOTH load and store encodings
    OPS = {0x38: "ld.b", 0x39: "ld.h/w", 0x3A: "st.b", 0x3B: "st.h/w",
           0x3C: "ld.bu", 0x3D: "ld.bu", 0x3E: "ld.hu", 0x3F: "ld.hu"}
    for disp in (SRC_427, SRC_ACC, SRC_MODE):
        neg, found, i = (-disp) & 0xFFFF, [], START
        while i < END - 3:
            h1, h2 = struct.unpack_from("<HH", base, i)
            op, r1 = (h1 >> 5) & 0x3F, h1 & 0x1F
            if r1 == 4 and op in OPS:
                if op in (0x3C, 0x3D):
                    d = (h2 & ~1) | (op & 1)
                elif op in (0x3E, 0x3F):
                    d = h2 & ~1
                elif op in (0x39, 0x3B):
                    d = (h2 & ~1) if (h2 & 1) else h2
                else:
                    d = h2
                if d == neg:
                    found.append(i)
            i += 2
        check(found == sorted(SRC_SITES[disp]),
              f"gp-0x{disp:04X}: an INDEPENDENT whole-image LE byte scan finds exactly "
              f"{len(found)} access site(s) at {[hex(x) for x in found]} -- identical to the "
              f"declared set. Two methods agree")
    check(len(SRC_SITES[SRC_ACC]) == 2,
          f"🛑 gp-0x{SRC_ACC:04X} has exactly TWO access sites image-wide, ld.w @0x381FE and st.w "
          f"@0x38230, BOTH inside FUN_00038148 itself ⇒ reading it adds no writer and touches "
          f"pre-existing Honda RAM whose only other accessor is the function that owns it")
    a, hx, what = FW_SHIFT_SITE
    check(rd(base, a, 2).hex() == hx, f"0x{a:05X} {hx}  {what}")

    # ---- 🛑 the gp-0x67fa STATE GATE: asserted from bytes, NOT encoded. See the header. ---------
    print("\n  [3b] 🛑 THE gp-0x67fa STATE GATE -- evaluated for b3, REJECTED on buildability")
    for a, (hx, what) in sorted(STATE_GATE_SITES.items()):
        check(rd(base, a, len(hx) // 2).hex() == hx, f"0x{a:05X} {hx:<12s} {what}")
    gate_imm = u16(base, 0x221D8)
    check(gate_imm == STATE_GATE_MASK
          and sorted(b for b in range(16) if (1 << b) & gate_imm) == [4, 5, 11],
          f"🛑 the gate mask reads 0x{gate_imm:04X} from the image ⇒ FUN_00038148 runs iff "
          f"(gp-0x67fa & 0xF) in {sorted(b for b in range(16) if (1 << b) & gate_imm)}. When it "
          f"shuts, BOTH gp-0x{SRC_427:04X} and gp-0x{SRC_ACC:04X} FREEZE ⇒ see FREEZE EXCLUSION")
    # the boolean exists ONLY in r28 -- no store in the caller has r28 or r25 as its source
    LONG = set(range(0x30, 0x40))
    src_stores, i = [], 0x2214A
    while i < 0x22700:
        h1 = struct.unpack_from("<H", base, i)[0]
        op, reg2 = (h1 >> 5) & 0x3F, (h1 >> 11) & 0x1F
        if op in (0x3A, 0x3B) and reg2 in (25, 28):
            src_stores.append(i)
        i += 4 if op in LONG else 2
    check(not src_stores,
          f"🛑 the gate boolean is NEVER STORED: no st.b/st.h/st.w in [0x2214A,0x22700) has r28 "
          f"(the boolean) or r25 (1<<s) as its source ⇒ there is NO RAM cell the cave could read, "
          f"and recomputing needs the Format IX `shl reg,reg,reg` at 0x221C6 with HAND-DERIVED "
          f"register fields. That is why b3 carries gp-0x{SRC_MODE:04X} instead, and why the freeze "
          f"is handled by a pre-registered wire-side exclusion rule rather than by a rung")

    print("\n  [4] 🛑 THE 32-BIT RMW V92's GATE-1 METHOD COULD NOT SEE -- found, and BENIGN")
    for a, (hx, what) in sorted(WORD_RMW.items()):
        check(rd(base, a, len(hx) // 2).hex() == hx, f"0x{a:05X} {hx}  {what}")
    mask = (u16(base, 0x21958) << 16) | u16(base, 0x21956)
    check(mask == WORD_RMW_MASK and (mask & 0xFF) == 0xFF and (mask >> 24) == 0xFF,
          f"the mask decodes to 0x{mask:08X}: bits 7:0 (0x14A byte 4) and bits 31:24 (byte 7) are "
          f"BOTH preserved ⇒ FUN_0002193e rewrites only bytes 5 and 6 and cannot clobber our bits")

    print("\n  [5] CARRIED-FORWARD CELLS on the BASE")
    assert_frozen(base, "base", ref=base)
    check(rd(base, CAVE_BASE, len(V92_CAVE)) == V92_CAVE,
          f"V92 cave 0x{CAVE_BASE:05X}-0x{CAVE_BASE + len(V92_CAVE) - 1:05X} "
          f"({len(V92_CAVE)} B) byte-exact")
    check(len(PAYLOAD) <= len(V92_CAVE),
          f"🛑 NO GROWTH: V96's payload is {len(PAYLOAD)} B inside V92's proven {len(V92_CAVE)} B "
          f"footprint ({len(V92_CAVE) - len(PAYLOAD)} B returned to virgin 0xFF). Same base, same "
          f"hook, same jarl -- V92's cave flew fault-free as route 79")
    check(all(b == 0xFF for b in base[CAVE_BASE + len(V92_CAVE):CAVE_FREE_END]),
          f"0x{CAVE_BASE + len(V92_CAVE):05X}-0x{CAVE_FREE_END:05X} all virgin 0xFF")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"cave hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} = jarl 0x{CAVE_BASE:05X},lp UNCHANGED")
    hk1, hk2 = struct.unpack_from("<HH", base, HOOK_ADDR)
    check(HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2) == CAVE_BASE,
          f"the hook's disp22 DECODES to 0x{HOOK_ADDR + (((hk1 & 0x3F) << 16) | hk2):05X} == the "
          f"cave base (disp[21:16]=0x{hk1 & 0x3F:02X} in hw1[5:0], disp[15:0]=0x{hk2:04X} in hw2)")
    check(rd(base, R427_SAR_ADDR, 2) == R427_SAR_OLD,
          f"🛑 0x{R427_SAR_ADDR:05X} = {rd(base, R427_SAR_ADDR, 2).hex()} = `sar 0x4,r6` -- V92's "
          f"shift is a4, NOT a3. BUILD-LINEAGE's 'a3 -> a1' is against V90 and is WRONG here")

    def jarl_target(addr):
        h1, h2 = struct.unpack_from("<HH", base, addr)
        d = ((h1 & 0x3F) << 16) | h2
        return addr + (d - 0x400000 if d & 0x200000 else d)
    check(jarl_target(DI_CALL_ADDR) == DI_TARGET and jarl_target(EI_CALL_ADDR) == EI_TARGET,
          f"🛑 INTERRUPTS ARE OFF ACROSS THE CAVE: 0x{DI_CALL_ADDR:05X} jarl -> "
          f"0x{jarl_target(DI_CALL_ADDR):05X} (DI) and 0x{EI_CALL_ADDR:05X} jarl -> "
          f"0x{jarl_target(EI_CALL_ADDR):05X} (EI), hook at 0x{HOOK_ADDR:05X} between them ⇒ the "
          f"cave's TWO reads of gp-0x{SRC_ACC:04X} cannot disagree. Both halves encode ONE number, "
          f"so this matters more here than it did on V92")
    check(DI_CALL_ADDR < HOOK_ADDR < CKSUM_CALL_ADDR < EI_CALL_ADDR,
          f"and the checksum call at 0x{CKSUM_CALL_ADDR:05X} runs AFTER the hook ⇒ both new bytes "
          f"are covered automatically; no recompute is needed")
    check(rd(base, 0x55BFC, 4) == bytes.fromhex("c846cf00"),
          "0x55BFC = `andi 0xcf,r8,r8` -- Honda's counter writer PRESERVES byte7 bits 7:6")
    check(rd(base, 0x55C24, 4) == bytes.fromhex("c636f000"),
          "0x55C24 = `andi 0xf0,r6,r6` -- Honda's checksum-nibble writer PRESERVES bits 7:4")

    # ==============================================================================================
    # 6. THE TWINS -- 112/112 byte coverage, nothing hand-encoded
    # ==============================================================================================
    print("\n  [6] 🛑 TWINS -- every payload byte COPIED from a verified instruction in THIS image")
    covered = bytearray(len(PAYLOAD))
    for off, w, src, why in TWINS:
        got, twin = PAYLOAD[off:off + w], rd(base, src, w)
        check(got == twin, f"+0x{off:02X} {got.hex():<14s} == 0x{src:05X}  {why}")
        for k in range(w):
            covered[off + k] = 1
    n_twin = sum(covered)
    print("       ---- the ONLY untwinned bytes: two pure-data imm16 halfwords, DERIVED below")
    for off, fn, why in DERIVED_IMM:
        check(PAYLOAD[off:off + 2] == fn(),
              f"+0x{off:02X} {PAYLOAD[off:off + 2].hex():<14s} DERIVED   {why}")
        for k in range(2):
            covered[off + k] = 1
    check(sum(covered) == len(PAYLOAD),
          f"🛑 PAYLOAD COVERAGE {sum(covered)}/{len(PAYLOAD)} bytes = {n_twin} TWINNED from verified "
          f"instructions + {sum(covered) - n_twin} DERIVED imm16 -- NO INSTRUCTION HAND-ENCODED "
          f"(uncovered: {[hex(i) for i, c in enumerate(covered) if not c]})")
    check(PAYLOAD[0x1C:0x1E] == bytes.fromhex("8031") and PAYLOAD[0x4E:0x50] == bytes.fromhex("8031"),
          "🛑 both `subr r0,r6` are 8031; the hand-derived 3080 would be `satsubr`, which SATURATES "
          "instead of negating and would corrupt |v| on NEGATIVE values only")
    check(PAYLOAD[0x0C:0x10] == PAYLOAD[0x44:0x48] == rd(base, 0x381FE, 4),
          "🛑 both `ld.w -0x374c[gp],r6` are the WHOLE 4 bytes of Honda's own @0x381FE ⇒ the "
          "ld.h/ld.w hw2-bit-0 ambiguity cannot be got wrong")
    check(len(PAYLOAD) == 112, f"payload length = {len(PAYLOAD)} bytes")

    # ==============================================================================================
    # 7. SEMANTICS -- the rung table as arithmetic, before any byte is written
    # ==============================================================================================
    print("\n  [7] RUNG SEMANTICS -- integer mirrors of the cave, corner-gridded")
    assert_rung_semantics()

    print("\n  [8] SIZING -- from each cell's OWN bound, read from the image. Stated BOTH ways.")
    for shift in (3, 4, 5, 6, 7):
        packed = (SRC_427_CLAMP * R427_MUL) >> shift
        verdict = "OK, no clip" if packed <= R427_FIELD_MAX else "🛑 CLIPS"
        star = "   <-- V96" if shift == R427_SHIFT_NEW else ("   (V92's)" if shift == 4 else "")
        print(f"       427 sar {shift}: {SRC_427_CLAMP}*{R427_MUL}>>{shift} = {packed:5d} of "
              f"{R427_FIELD_MAX}  LSB {(1 << shift) / R427_MUL:6.2f} ct  {verdict}{star}")
    packed_max = (SRC_427_CLAMP * R427_MUL) >> R427_SHIFT_NEW
    lsb427 = (1 << R427_SHIFT_NEW) / R427_MUL
    check(packed_max <= R427_FIELD_MAX,
          f"🛑 427 NO-CLIP: at gp-0x{SRC_427:04X}'s OWN clamp (+-{SRC_427_CLAMP}, cal 0xC6200) the "
          f"packed value is {packed_max} <= {R427_FIELD_MAX} ⇒ the channel CANNOT saturate "
          f"anywhere the cell can go ({100 * packed_max / R427_FIELD_MAX:.1f} % of the field)")
    check(((SRC_427_CLAMP * R427_MUL) >> (R427_SHIFT_NEW - 1)) > R427_FIELD_MAX,
          f"🛑 AND THE SHIFT IS MINIMAL, not conservative: sar {R427_SHIFT_NEW - 1} packs to "
          f"{(SRC_427_CLAMP * R427_MUL) >> (R427_SHIFT_NEW - 1)} > {R427_FIELD_MAX} and would go "
          f"flat from |gp-0x{SRC_427:04X}| >= "
          f"{min(n for n in range(1 << 16) if (n * R427_MUL) >> (R427_SHIFT_NEW - 1) > R427_FIELD_MAX)}")
    qn = lsb427 / (12 ** 0.5)
    band = qn * (3.0 / 25.0) ** 0.5
    print(f"       PRIMARY  gp-0x{SRC_427:04X} on 427: LSB {lsb427:5.2f} ct @ 50 Hz ⇒ 6-9 Hz "
          f"quantisation floor {band:.2f} ct rms ⇒ a sinusoid below ~{2 * band * 2 ** 0.5:.1f} ct "
          f"({100 * 2 * band * 2 ** 0.5 / SRC_427_CLAMP:.3f} % of range) is INVISIBLE")
    sat_at = ACC_HI_SAT << ACC_HI_SHIFT
    theoretical = 26624 * 2639 >> 10
    check(sat_at < theoretical,
          f"🛑 REGRESSOR gp-0x{SRC_ACC:04X}>>4: SATURATING at {sat_at}, LSB {ACC_LSB} ct, 3 bits. "
          f"This is DELIBERATELY below the structural bound {theoretical:,} (sum6 max 26,624 x "
          f"2639 >> 10) -- that bound is a large overestimate and sizing a tight linear scale off "
          f"it is the gp-0x6b98 '1-bit comparator' mistake. **THE SATURATION DUTY (Mhi == 3) IS A "
          f"FIRST-CLASS REPORTED OUTPUT** so V96 sizes off DATA, not off a guess")
    print(f"       ⚠ errors-in-variables from the coarse regressor ATTENUATES the fitted slope "
          f"toward zero and PRESERVES its sign. The decisive output is the SIGN of f'; the "
          f"magnitudes are LOWER BOUNDS. Declared here, not discovered afterwards.")

    # ==============================================================================================
    # 9. THE EDITS
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

    print("\n  [9] THE EDITS -- 🛑 NOT ONE OF THEM IS A CALIBRATION BYTE")
    pad = b"\xff" * (len(V92_CAVE) - len(PAYLOAD))
    apply(CAVE_BASE, V92_CAVE, PAYLOAD + pad,
          f"EDIT 1     cave {len(V92_CAVE)} B -> {len(PAYLOAD)} B, SEVEN rungs "
          f"(+{len(pad)} B restored to virgin 0xFF; NO GROWTH)")
    apply(R427_ADDR, struct.pack("<h", -R427_OLD), struct.pack("<h", -R427_NEW),
          f"EDIT 2     CAN 427 MOTOR_TORQUE source: gp-0x{R427_OLD:04X} -> gp-0x{R427_NEW:04X}")
    apply(R427_SAR_ADDR, R427_SAR_OLD, R427_SAR_NEW,
          f"EDIT 3     CAN 427 packer scale: sar 0x4,r6 -> sar 0x{R427_SHIFT_NEW:x},r6 (NO-CLIP)")
    check(len(attributed) == len(V92_CAVE) + 2 + 2,
          f"TOTAL ATTRIBUTED = {len(attributed)} = {len(V92_CAVE)} cave span + 2 repoint + 2 scale")
    check((-R427_NEW & 0xFFFF) % 2 == 0 and (-R427_OLD & 0xFFFF) % 2 == 0,
          "🛑 both 427 displacements are EVEN -- an odd one would select ld.w, not ld.h")
    check(all(b == 0xFF for b in code[CAVE_BASE + len(PAYLOAD):CAVE_FREE_END]),
          f"tail 0x{CAVE_BASE + len(PAYLOAD):05X}-0x{CAVE_FREE_END:05X} virgin 0xFF")

    # ==============================================================================================
    # 10. 🛑 THE CALIBRATION IS V92's, CELL BY CELL -- JOB 1
    # ==============================================================================================
    print("\n  [10] 🛑 EVERY CALIBRATION CELL == V92, CELL BY CELL (JOB 1: the revert)")
    assert_frozen(code, "built image", ref=base)
    moved = [m for m in range(FRICTION_N_MODES)
             if rd(code, rec_addr(code, m), REC_LEN) != rd(base, rec_addr(base, m), REC_LEN)]
    check(not moved,
          f"all {FRICTION_N_MODES} friction records (modes 0..{FRICTION_N_MODES - 1}) are "
          f"BYTE-IDENTICAL to V92 -- zero moved")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == FRICTION_Y_STOCK,
              f"mode {m} (MANUAL)  rec 0x{rec_addr(code, m):05X} Y = {rec_y(code, m)} = Honda STOCK "
              f"🛑 'revert to V92' means STOCK here -- V94 was the FIRST build ever to move mode 24")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == FRICTION_Y_V92,
              f"mode {m} (ENGAGED) rec 0x{rec_addr(code, m):05X} Y = {rec_y(code, m)} = V92's x1.5 "
              f"🛑 NOT stock -- 'revert to V92' is NOT 'revert to stock' on these two records")
    for m in MANUAL_MODES + ENGAGED_MODES:
        check(struct.unpack_from("<3h", code, rec_addr(code, m) + REC_X_OFF) == FRICTION_X,
              f"mode {m}: X = {FRICTION_X} UNCHANGED (no breakpoint moved anywhere)")
    check(rd(code, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4)
          == rd(base, FRICTION_PTR_ARRAY, FRICTION_N_MODES * 4),
          f"the pointer array [0x{FRICTION_PTR_ARRAY:05X},0x{FRICTION_ARRAY_END:05X}) is "
          f"byte-identical -- no pointer was rewritten")
    check(struct.unpack_from("<I", code, FRICTION_ARRAY_END)[0] == 0xDAA44,
          f"0x{FRICTION_ARRAY_END:05X} (the FIRST SLOT PAST the {FRICTION_N_MODES}-slot array) "
          f"holds a valid-LOOKING pointer -- which is why the bound is GIVEN, never walked")
    check(u16(code, 0xC6446) == 5244 and code[0x3AA96] == 0xFB,
          "🛑 LEVER B, BOTH HALVES: 0xC6446 = 5244 (arm) AND 0x3AA96 = 0xFB (gate). Silently "
          "reverted at a rebase THREE times; asserted here as a pair, not singly")
    check(code[0x454FE] == 0xB5,
          "🛑 0x454FE = 0xB5 -- V42's ratchet fix, carried. ⚠ MEASURED INERT; carried because it "
          "is free. NOTHING is claimed for it")

    print("\n  [11] 🛑 V94's CUT IS GONE -- read from V94's OWN IMAGE, not from a build script")
    v94p = Path(V94_BIN)
    if v94p.exists():
        v94 = v94p.read_bytes()
        check(hashlib.sha256(v94).hexdigest() == V94_SHA,
              f"V94 image on disk hashes to {V94_SHA} (read-only)")
        for a, (v92v, v94v, what) in sorted(V94_CAL_DELTA.items()):
            check(s16(code, a) == v92v and s16(v94, a) == v94v,
                  f"0x{a:05X} {what}: V96 = {s16(code, a)}, V94 = {s16(v94, a)}  ⇒ REVERTED")
        for m, y94 in sorted(V94_FRICTION_ROWS.items()):
            check(struct.unpack_from("<3h", v94, rec_addr(v94, m) + REC_Y_OFF) == y94
                  and rec_y(code, m) != y94,
                  f"mode {m}: V94 Y = {y94}, V96 Y = {rec_y(code, m)}  ⇒ REVERTED")
        check(abs(FRICTION_Y_V92[0]) / abs(V94_FRICTION_ROWS[26][0]) > 5.99,
              f"and the cut V96 undoes is {abs(FRICTION_Y_V92[0]) / abs(V94_FRICTION_ROWS[26][0]):.3f}x "
              f"on the ENGAGED row -- the '6x against V92' figure, confirmed arithmetically")
        v94_cave_len = sum(1 for i in range(CAVE_BASE, CAVE_FREE_END) if v94[i] != 0xFF)
        check(v94_cave_len == 74,
              f"🛑 V94 carries the V90 cave, {v94_cave_len} bytes, which NEVER writes 0x14A byte 7 "
              f"⇒ byte7[7:6] != 0 on a single frame proves V96 and excludes the build on the car")
    else:
        print(f"    ---- {os.path.basename(V94_BIN)}: not on disk, cross-check skipped")

    # ==============================================================================================
    # 12. RE-DISASSEMBLE THE CAVE FROM THE BUILT IMAGE, against the RUNG TABLE
    # ==============================================================================================
    print("\n  [12] 🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE, checked against the RUNG TABLE")
    listing = disassemble_cave(code, CAVE_BASE, len(PAYLOAD))
    check(len(listing) == len(EXPECTED) == 43,
          f"{len(listing)} instructions decoded, rung table has {len(EXPECTED)}, expected 43")
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
    check(nbranch == 6 and not bad_tgt,
          f"{nbranch} branches, EVERY target lands on an instruction BOUNDARY ({bad_tgt[:3]})")
    check(conds == {"bge", "bnh"},
          f"🛑 the cave uses exactly the branch conditions {sorted(conds)} == V92's own set. NO NEW "
          f"BRANCH CONDITION -- the `!= 7` mode form would have needed `bne` and the recorded "
          f"ba05/b205 inversion hazard; `>= 28` reuses the proven addi+bnh idiom")
    bad_mn = [t.split()[0] for _, _, _, t, _, _, _, _ in listing
              if t.split()[0].startswith("op") or "?" in t
              or t.split()[0] in ("jarl", "jr", "callt", "div", "divh", "prepare", "dispose")]
    check(not bad_mn,
          f"the cave is a STRAIGHT-LINE LEAF: no call, no loop, no divide, no float, no unknown "
          f"opcode ({bad_mn[:4]})")
    check(writes <= {0, 6, 7},
          f"🛑 registers WRITTEN by the cave = {sorted(writes)} ⊆ {{r0, r6, r7}} -- r6 is restored "
          f"by the trailing movea, r7 is overwritten at 0x55C12 `mov 0x8,r7`")
    check(refs <= {0, 4, 6, 7, 31},
          f"🛑 every register REFERENCED = {sorted(refs)} ⊆ {{r0, gp, r6, r7, lp}} -- r8 and r10 "
          f"are LIVE across the hook (0x55C20 `andi 0xf,r10,r8`) and the cave never touches them")
    stores = [(off, operand) for off, _, _, _, k, operand, _, _ in listing if k.startswith("st.")]
    check([(o, d) for o, (rb, d) in stores] == [(0x40, -0x1514), (0x66, -0x1511)]
          and all(rb == 4 for _, (rb, _) in stores),
          f"🛑 GATE 2 (1): the cave STORES to exactly two addresses -- gp-0x1514 (0x14A byte 4, "
          f"~50 flown builds) and gp-0x1511 (byte 7, V92's). NO OTHER MEMORY IS WRITTEN, so no "
          f"control signal is modified and the probe closes no loop")
    loads = sorted({row[5][1] & 0xFFFF for row in listing if row[4].startswith("ld.")})
    want_loads = sorted({(-x) & 0xFFFF for x in (SRC_427, SRC_ACC, SRC_MODE, 0x1514, 0x1511)})
    check(loads == want_loads,
          f"and it LOADS exactly {[hex(x) for x in loads]} = the three source cells and the two "
          f"CAN payload bytes it read-modify-writes. Nothing else is touched")
    kinds = {row[4] for row in listing if row[4].startswith("ld.")}
    check(kinds == {"ld.h", "ld.w", "ld.bu"},
          f"🛑 load CLASSES present = {sorted(kinds)} -- the cave deliberately uses ld.h AND ld.w, "
          f"which share hw1, and Ghidra's own decode of the BUILT image separates them correctly")

    # ==============================================================================================
    # 13. VALUE-ANCHORED READBACK (a span diff is NOT a value check)
    # ==============================================================================================
    print("\n  [13] VALUE-ANCHORED VERIFICATION, read back from the BUILT image")
    check(s16(code, CAVE_BASE + 0x04) == -SRC_427,
          f"cave +0x02 = ld.h -0x{SRC_427:04X}[gp],r6   the PRIMARY / 427 source")
    for off in (0x0C, 0x44):
        got = u16(code, CAVE_BASE + off + 2)
        check((got & ~1) == ((-SRC_ACC) & 0xFFFF) and (got & 1) == 1,
              f"cave +0x{off:02X} = ld.w -0x{SRC_ACC:04X}[gp],r6 (hw2 = 0x{got:04X}, bit 0 SET ⇒ "
              f"ld.w, a 32-bit load -- NOT ld.h)")
    check(u16(code, CAVE_BASE + 0x2C) & ~1 == ((-SRC_MODE) & 0xFFFF),
          f"cave +0x2A = ld.bu -0x{SRC_MODE:04X}[gp],r6   the MODE rung's source")
    check(s16(code, CAVE_BASE + 0x30) == -MODE_THRESHOLD,
          f"cave +0x2E addi imm16 = {s16(code, CAVE_BASE + 0x30)} ⇒ b3 = (gp-0x{SRC_MODE:04X} < "
          f"{MODE_THRESHOLD})")
    for off, want, what in ((0x10, ACC_FW_SHIFT, "the FIRMWARE's own >>4 on the accumulator"),
                            (0x48, ACC_FW_SHIFT, "the same, byte7 half"),
                            (0x1E, ACC_HI_SHIFT, "b5:b4 = |v| >> 12"),
                            (0x50, ACC_LO_SHIFT, "byte7 b7 = bit 1 of |v| >> 10")):
        b = code[CAVE_BASE + off]
        check(b & 0xE0 == 0xA0 and b & 0x1F == want,
              f"cave +0x{off:02X} = `sar 0x{b & 0x1F:x},r6`   {what}")
    check(code[CAVE_BASE + 0x20] & 0xE0 == 0x60 and code[CAVE_BASE + 0x20] & 0x1F == ACC_HI_SAT
          and code[CAVE_BASE + 0x24] & 0xE0 == 0x00 and code[CAVE_BASE + 0x24] & 0x1F == ACC_HI_SAT,
          f"cave +0x20/+0x24 = `cmp 0x{ACC_HI_SAT:x},r6` + `mov 0x{ACC_HI_SAT:x},r6` ⇒ the "
          f"REGRESSOR SATURATES at Mhi == {ACC_HI_SAT} (|v| >= {ACC_HI_SAT << ACC_HI_SHIFT}), and "
          f"the same instruction confines the magnitude to bits 1:0 so it cannot reach the SIGNS")
    check(u16(code, CAVE_BASE + 0x54) == 2,
          f"cave +0x52 andi imm16 = 0x{u16(code, CAVE_BASE + 0x54):04X} ⇒ the M-bit-0 mask")
    check(code[CAVE_BASE + 0x56] == 0x01 and code[CAVE_BASE + 0x57] == 0x3A,
          f"cave +0x56 = `mov 0x1,r7` ⇒ 🛑 THE FINGERPRINT IS A CONSTANT ⇒ byte7 b6 ≡ 1 ⇒ the "
          f"identity is STRUCTURAL and cannot fail to fire")
    check(s16(code, R427_ADDR) == -R427_NEW,
          f"427 source: 0x{R427_ADDR - 2:05X} = {rd(code, R427_ADDR - 2, 4).hex()} = "
          f"ld.h -0x{R427_NEW:04X}[gp],r6")
    got_shift = code[R427_SAR_ADDR] & 0x1F
    check(code[R427_SAR_ADDR] & 0xE0 == 0xA0 and got_shift == R427_SHIFT_NEW
          and rd(code, R427_SAR_ADDR, 2) == R427_SAR_NEW,
          f"427 scale: 0x{R427_SAR_ADDR:05X} = {rd(code, R427_SAR_ADDR, 2).hex()} ⇒ "
          f"`sar 0x{got_shift:x},r6` ⇒ 427 = clamp(|gp-0x{R427_NEW:04X}| * {R427_MUL} >> "
          f"{got_shift}, 0, 0x{R427_FIELD_MAX:X}), LSB {(1 << got_shift) / R427_MUL:.1f} counts")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, f"cave hook 0x{HOOK_ADDR:05X} byte-identical")

    # ==============================================================================================
    # 14. CRC -- DERIVED IN CODE from the image's own 50-block map
    # ==============================================================================================
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  [14] CRC -- {len(blocks)} block(s) move, trailer set DERIVED from the image's own "
          f"self-describing 50-block map")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len(owners)} of {len(touched)} touched byte(s)")
    derived = {blk[1] for blk in blocks}
    check(derived == {0xC4FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == {{0xc4ffc}} -- the cave and "
          f"BOTH 427 edits share the MAIN block [0x013000,0x0C4FFC). V96 writes no calibration, so "
          f"unlike V92 the 0xD7FFC block does NOT move. Derived, then asserted; never hard-coded")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    check(0x055FFC not in crc_only,
          "🛑 0x055FFC is LIVE CODE (`6477b8f0`), NOT a CRC trailer -- writing there would silently "
          "overwrite 4 bytes of executable code and the recompute would HIDE it")
    check(walk_all_blocks(bytes(code)) == 0,
          "built image CRC chain 50/50 (NECESSARY, NOT SUFFICIENT -- see [15])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(not [a for a in attributed if 0xC5000 <= a < 0xC5FFC],
          "no edit landed inside [0xC5000,0xC5FFC) -- the block the bootloader SKIPS")
    check(not [a for a in attributed if a < START or a >= END],
          f"every edit lies inside [0x{START:X},0x{END:X})")
    check(bytes(code[:START]) == bytes(base[:START]),
          f"nothing below 0x{START:X} changed (the bootloader region)")
    check(bytes(code[0xD7000:0xD8000]) == bytes(base[0xD7000:0xD8000]),
          "🛑 the WHOLE calibration block [0xD7000,0xD8000) -- both engaged friction rows and its "
          "own CRC trailer -- is BYTE-IDENTICAL to V92's. JOB 1, proven at block granularity")

    # ==============================================================================================
    # 15. ZERO-UNATTRIBUTED FULL BYTE DIFF -- the INDEPENDENT check
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
    print("  [15] 🛑 FULL BYTE DIFF: BUILT V96 vs the FLOWN V92 -- over [0x13000, 0x100000)")
    print(f"       {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"       0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    check(not stray, f"ZERO unattributed bytes vs V92 (stray = {[hex(x) for x in stray[:16]]})")
    for lo, hi, why in ((0xC6000, 0xC7000, "lane weights, model gain, clamps, Lever B arm"),
                        (0xC4000, 0xC4B34, "the K0/K1 friction family"),
                        (0xE5000, 0xE6000, "🛑 THE AUTHORITY CURVE -- virgin, and it stays virgin"),
                        (0xCB000, 0xE0000, "every friction/gain record page")):
        check(not [d for a, b in runs for d in range(a, b + 1) if lo <= d < hi],
              f"ZERO differing bytes in [0x{lo:05X},0x{hi:05X}) -- {why}. Proven by DIFF, not by a list")
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    check(hashlib.sha256(bytes(rt)).hexdigest() == base_sha,
          "restoring the attributed set reproduces the flown V92 BIT-FOR-BIT")

    # ==============================================================================================
    # 16. .rwd
    # ==============================================================================================
    print("\n  [16] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V96 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V96_WRITE=rwd to cut.")
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

            print("\n  [17] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V96 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk", ref=base)
            for m in MANUAL_MODES:
                check(rec_y(sd, m) == FRICTION_Y_STOCK,
                      f"shipped .rwd: MANUAL mode {m} Y = {FRICTION_Y_STOCK} = Honda STOCK")
            for m in ENGAGED_MODES:
                check(rec_y(sd, m) == FRICTION_Y_V92,
                      f"shipped .rwd: ENGAGED mode {m} Y = {FRICTION_Y_V92} = V92's x1.5")
            for a, (v92v, _, what) in sorted(V94_CAL_DELTA.items()):
                check(s16(sd, a) == v92v, f"shipped .rwd: 0x{a:05X} = {s16(sd, a)}  {what}")
            check(u16(sd, 0xC6446) == 5244 and sd[0x3AA96] == 0xFB and sd[0x454FE] == 0xB5,
                  "shipped .rwd: Lever B BOTH halves (0xC6446 = 5244, 0x3AA96 = 0xFB) and "
                  "0x454FE = 0xB5 are all present in the artefact that will actually be flashed")
            check(rd(sd, CAVE_BASE, len(PAYLOAD)) == PAYLOAD,
                  f"shipped .rwd: the {len(PAYLOAD)}-byte cave payload is byte-identical")
            check(all(b == 0xFF for b in sd[CAVE_BASE + len(PAYLOAD):CAVE_FREE_END]),
                  "shipped .rwd: the cave tail is virgin 0xFF")
            check(s16(sd, R427_ADDR) == -R427_NEW and sd[R427_SAR_ADDR] & 0x1F == R427_SHIFT_NEW,
                  f"shipped .rwd: 427 = clamp(|gp-0x{R427_NEW:04X}| * {R427_MUL} >> "
                  f"{R427_SHIFT_NEW}, 0, 0x{R427_FIELD_MAX:X})")
            check(rd(sd, HOOK_ADDR, 4) == HOOK_BYTES, "shipped .rwd: the cave hook is unchanged")
            check(sd[CAVE_BASE + 0x56] == 0x01 and sd[CAVE_BASE + 0x57] == 0x3A,
                  "shipped .rwd: the FINGERPRINT (`mov 0x1,r7` @+0x56) is present ⇒ the IDENTITY "
                  "is live in the artefact that will actually be flashed")
            check(sd[CAVE_BASE + 0x24] & 0x1F == ACC_HI_SAT,
                  "shipped .rwd: the regressor's saturating `mov 0x3,r6` guard is present")
            sd_listing = disassemble_cave(sd, CAVE_BASE, len(PAYLOAD))
            check([(row[0], row[3].split()) for row in sd_listing]
                  == [(e[0], e[1].split()) for e in EXPECTED],
                  f"shipped .rwd: the cave RE-DISASSEMBLES to the same {len(EXPECTED)}-instruction "
                  f"rung table, offset for offset")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

            print("\n  [18] 🛑 ARTEFACT UNIQUENESS -- every V96-matching file in both directories")
            stray_rwd = sorted(p for p in Path(RWD_DIR).iterdir()
                               if p.is_file() and "v96" in p.name.lower())
            stray_img = sorted(p for p in Path(ANALYSIS_ROOT).iterdir()
                               if p.is_file() and "v96" in p.name.lower())
            for p in stray_rwd + stray_img:
                mark = "  <-- THIS BUILD" if str(p) in (OUT, BIN_OUT) else "  🛑 STRAY"
                print(f"       {p.name}{mark}")
            check([str(p) for p in stray_rwd] == [OUT],
                  f"exactly ONE V96 .rwd in {RWD_DIR}: {os.path.basename(OUT)} "
                  f"(found {len(stray_rwd)})")
            check([str(p) for p in stray_img] == [BIN_OUT],
                  f"exactly ONE V96 image in {ANALYSIS_ROOT}: {os.path.basename(BIN_OUT)} "
                  f"(found {len(stray_img)})")
            for nm, sha in ((BASE_NAME, BASE_SHA), (os.path.basename(V94_BIN), V94_SHA)):
                p = plain_image_path(nm)
                if p.exists():
                    check(hashlib.sha256(p.read_bytes()).hexdigest() == sha,
                          f"🛑 {nm[:44]} is STILL byte-identical after the V96 cut -- untouched")

    print("\n" + "=" * 102)
    print(f"  V96 [{VARIANT_TOKEN}]     {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  🛑 ZERO calibration bytes. {len(V92_CAVE)} cave-span bytes + 2 repoint + 2 scale "
          f"+ 4 CRC.")
    print("  🛑 THIS IS AN INSTRUMENT, NOT A FIX. V94's 0xCBE74 cut is reverted BY CONSTRUCTION;")
    print("     every calibration cell is V92's, and V92 is the last configuration the operator")
    print("     drove and did not abort. Nothing in this build is claimed to improve the car.")
    print("  🛑 IDENTITY: byte7 b6 ≡ 1, so ANY single frame with 0x14A byte7[7:6] != 0 proves V96.")
    print("     V94 -- the build on the car -- carries the 74-byte V90 cave and cannot write it.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    assert len(PAYLOAD) == 112 and len(V92_CAVE) == 116
    build()
