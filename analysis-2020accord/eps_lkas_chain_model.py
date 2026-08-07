"""
eps_lkas_chain_model.py
=======================================================================================================
Executable PSEUDOCODE model of the 2020 Honda Accord EPS LKAS logic chain, from the openpilot/comma
CAN steering command through to motor torque (3-phase PWM) output.

Platform : 2020 Honda Accord Touring, EPS part 39990-TVA-A160, Renesas V850E2 (little-endian, 1 MB).
Purpose  : a single readable reference for our current understanding of how a CAN STEER_TORQUE request
           becomes motor current -- driver torque sensor path, vehicle speed, the arbitration/limit
           cascade, and every state machine that can gate or cut the LKAS term (engage decider,
           STEER_STATUS gentle-EME debounce, DTC-0x49 counter, soft-EME windup shaper, hard-DTC
           lockstep monitor). It is a MODEL: arithmetic-faithful where we have byte evidence, labelled
           where inferred. Durable findings and session narrative live in docs/HANDOFF-*.md,
           docs/STATE.md, docs/BUILD-LINEAGE.md and memory/ -- not here.

-------------------------------------------------------------------------------------------------------
CONFIDENCE LEGEND
-------------------------------------------------------------------------------------------------------
  [CONFIRMED]  On-car / DBC ground truth: (1) the LKAS torque command on CAN 0xE4, (2) the physical
               steering-wheel torque sensor readings.
  [VERIFIED]   Byte-verified in Ghidra against stock code.bin. Static, not dynamically observed.
  [INFERRED]   Structurally reasoned from disassembly but not pinned instruction-for-instruction.
  [OPEN]       Explicitly unknown / unlocated.

-------------------------------------------------------------------------------------------------------
ADDRESS CONVENTION
-------------------------------------------------------------------------------------------------------
  Ghidra program : code.bin (flat base 0, file-offset == address).
  gp (r4) = 0xFEDF8000  ->  "gp-0xNNNN" is absolute 0xFEDF8000 - 0xNNNN
  tp (r5) = 0xBF000      ->  "tp+0x7NNN" is absolute 0xBF000 + 0x7NNN (e.g. tp+0x746c == 0xC646C)

  CORRECTION OF RECORD: 0xC646C is NOT "the LKAS output gain" -- it is the firmware's single shared
  Q15 sensor-to-command-domain scale, with 6 readers: ONE forward (0x2a1ee, the LKAS setpoint path,
  modelled by lkas_output_gain), ONE dead (0x2a904), and FOUR feedback (0x2b656, 0x2c488, 0x36686,
  0x3684a, modelled by shared_sensor_scale). V38's 891->3564 raised the gain on the feedback paths
  too; V57 decouples the forward reader onto its own cal cell (0xC6CD0) and reverts 0xC646C to stock
  891 for the feedback readers only. See memory/reference-accord-c646c-shared-gain-not-lkas-only.md.
  ✅ RE-ENUMERATED 2026-08-07 (Ghidra + a fresh raw Python LE scan of both encodings + fresh
  decompiles, all three agreeing): exactly 6 readers, 0 stores, 0 disp23 hits, 0 LE32-pointer hits;
  every site is (x * cal) >> 0xf, and 3564 = 4 x 891 exactly. Two roles CHANGE:
    #3 (0x2b656, FUN_0002b62c) RECLASSIFIED -- its output gp-0x6af0 reaches only a private
       2-function mode-flag debounce (gp-0x677d has exactly 2 static refs image-wide) and a UDS
       packer with 0 static callers => NO TORQUE PATH at all, not a feedback lane.
    #4 (0x2c488, FUN_0002c478) output gp-0x6b10 has 3 refs, ALL st.h, ZERO loads => proven dead.
  => #5 (0x36686) is the ONLY reader that reaches the motor. 🛑 It CANNOT drive a 21-27 Hz mode, on a
  BANDWIDTH argument: its IIR alpha = tp+0x73d2 = 6 (6/1024 = 0.00586) => corner ~0.93 Hz, ~-26.6 dB
  at 21 Hz. [EVIDENCE] This settles the prior "6 vs 14" discrepancy in favour of 6.
  ⚠ Reader #5's pre-filter +-0x200 clamp trips at |gp-0x4f60| ~18,829 counts at stock but ~4,707 at
  4x. On route 66 (V80) |bar| engaged max was 3,849 and >= 4707 fired 0/89,997 => it did NOT bind --
  but the margin is only 22% and the CAN count scale is not proven identical to gp-0x4f60's.
  🛑 THE V57 DECOUPLE IS OFF THE CAR since the V38 rebase: V76/V78/V79/V80 read 0x2A1F0 disp 0x746C
  (shared 0xC646C = 3564), where V62/V68/V74/V75 read 0x7CD0 (private 0xC6CD0 = 3564, 0xC646C stock
  891). Nothing in V76->V80 re-applies it. Real uncosted headroom regression; NOT the 27 Hz driver.
  ✅ 0xC6CD0 = 0xFFFF on V76/V78/V80 is provably inert -- 0 instructions read tp+0x7cd0 anywhere.

-------------------------------------------------------------------------------------------------------
BUILDS THIS MODEL PARAMETERISES  (Calibration.for_build(...))
-------------------------------------------------------------------------------------------------------
  V9  = reconstructed STOCK baseline (flashed, confirmed-correct reference).
  V31 = V9 + 2x LKAS reach + soft-EME fix (corridor x4, boost floor 4096). FLASHED.
  V37 = V31 + gentle-EME debounce-SM disable + DTC-0x49 gate raise. FLASHED, RESOLVED gentle EME.
  V38 = V37 + 4x-stock LKAS reach (gain 3564) + matched corridor/boost + setpoint limit 16384. FLASHED,
        fault-free; hard turns showed an authority feedback limit (later root-caused, see V42).
  V39 = V38 + experimental suppression of the direct Sensor-B torque-rate lane r24. FLASHED, FALSIFIED
        (fixed neither the ratchet nor the vibration).
  V40 = V38 + governor slew steps -> 0xFFFF + motor-rate cap flattened. FLASHED -> EPS lamp + no power
        steering at ignition. Do not repeat the slew-step edit.
  V41 = V38 + motor-rate cap flattened only (slew untouched). FLASHED, boots clean, FALSIFIED as a
        vibration/ratchet cause; isolates V40's fault to the slew-step edit.
  V42 = V38 + (1) one-byte governor state-4 substitution disable (0x454fe) + (2) r26 adaptive gain
        zeroed. FLASHED: (1) CONFIRMED root cause, fixed the hard-turn ratchet; (2) FALSIFIED, no
        effect on the vibration.
        🛑🛑 CORRECTED 2026-08-04 -- "kept in all later builds" WAS FALSE. Byte-read across all 60
        built images: 0x454FE is carried by V42-V52C ONLY and is STOCK in V53 -> V70, lost at the
        V38/FOURFRAME rebase because V53+ descends from a branch point BEFORE V42. Nobody decided
        it. ⚠ And the argument that later retired it as a cause of the CURRENT ratchet --
        "STEER_STATUS == 4 fires 0/37,922" -- was VOIDED when bus STEER_STATUS was shown not to be
        gp-0x67fa (state 4 sits inside all three gate masks). It was never actually eliminated.
        The same audit found V62's 0x3AB76/0x3AC20 sar pair -- the kit's ONLY measured grind-#1 fix
        -- carried by V62 and V65 ONLY, removed as V66's confirmatory control and never restored.
        ⇒ FROM V66 TO V70 THE CAR CARRIED NEITHER CONFIRMED FIX. Both are restored in V71.
        ⇒ RULE 3 (docs/BUILD-LINEAGE.md): byte-check the CURRENT image before reasoning from any
        recorded result, and when you remove a confirmed fix to run a control, write the restore
        into the next build's spec.
  V53 = V38 + FOURFRAME2 read-only telemetry cave + min steer speed 0 (0xC62EA -> 0). FLASHED: speed
        window prediction CONFIRMED on-car; the telemetry cave never transmitted (uninterpretable null).
  V54 = V38 + speed-window-0 + a report-only gp-0x6966 (soft-EME authority) probe on CAN 0x14A. FLASHED:
        authority measured ~0 by design (V31's boost floor prevents windup) on every V31+ build.
  V55 = V38 + speed-window-0 + a report-only probe on gp-0x6b98 (final merged command). FLASHED: proved
        the ~21 Hz mode IS in the command and closes inside the EPS, not commanded by openpilot.
  V56 = V55 + mute the FUN_0003a382 residual lane (0xC6AF0 LERP -> 0). FLASHED: FALSIFIED (21 Hz
        unchanged) and cost hands-off damping -- REVERTED.
  V57 = V55 (not V56) + (A) decouple 0xC646C's forward LKAS reader onto a private cal cell, reverting
        the shared cal to stock 891 for the 4 feedback readers, and (B) a report-only deadband-gate
        probe on CAN 0x14A. FLASHED, fault-free; its calibration is carried by V58.
  V58 = V57 + the angle-rate/boost-lane probe. FLASHED, flight-clean. Established the grinding is
        ENGAGEMENT-GATED (absent disengaged, 60 s moving-but-disengaged control) and creep-dominant.
  V59 = V58 + a thermometer on the boost-amplitude index gp-0x6ba6. FLASHED, flight-clean. Measured the
        parametric pump's DEPTH (42.19 Hz = 2x the mode, absent disengaged).
  V60 = V59 + the amplitude-blend coefficient 0xD2006 102 -> 43. FLASHED 2026-07-31: NULL. Built as a
        DISCRIMINATOR, and it did its job -- the parametric-pump mechanism is CLOSED. It also closes
        0xC63BA, whose only consumers are the same two amplitude LERPs.
  V61 = V59 (NOT V60 -- the falsified blend is reverted by construction) + kill the torsion-bar RATE
        lane at BOTH taps of its shared value: 0x3AB6C mul r1,r6,r0 -> mul r0,r6,r0 (r26) and
        0x3AC16 mov r1,r8 -> mov r0,r8 (r24), two single-BIT reg1 r1->r0 changes, no cave. r24 and r26
        are two gain-scalings of ONE value, r1 = clamp(gp-0x4f62, +/-5120); V39 killed only r24 and only
        CONDITIONALLY, V42 killed only r26, and byte-checking every flashed image confirms NO build ever
        had both dead -- so each recorded null was uninformative about the lane. BUILT, UNFLASHED.

  🛑 V52C ("halved the mode") did NOT halve anything: -6.1 dB IS 0.496x IS the filter's own transfer
     function at 20.9 Hz, written as a caveat on why its NULL was weak and later restated as a positive
     result. Operator's on-car report was "did not fix the vibration; clearly changed manual feel", and
     no V52C rlog exists. See memory/accord-a-caveat-can-mutate-into-a-result.md.

-------------------------------------------------------------------------------------------------------
EXECUTION MODEL
-------------------------------------------------------------------------------------------------------
  BASE TICK    : 🛑 CORRECTED 2026-07-31 -- this line used to read "OSTM0 timer, compare 79999 ->
                 ~80000-cycle period; strong-inference 1 kHz at 80 MHz". BOTH HALVES WERE WRONG.
                 OSTM0 is NOT the RTOS tick (the EI trampoline FUN_0001492a has no OSTM0 arm; the rate
                 divider's trigger gp-0x42fc is written ONLY by EIIC 0x340 = TAUJ1I2), and PCLK is
                 40 MHz not 80, so OSTM0 is a free-running 500 Hz timer with no path into the
                 scheduler. The REAL tick is TAUJ1I2, whose period register has not been located.
                 [VERIFIED: dispatcher + PCLK | OPEN: TAUJ1 period register]
                 ✅ The 1 kHz figure itself SURVIVES on ON-CAR MEASUREMENT, which never used either:
                 the STEER_STATUS=4 dwell (cal 0xC64DF = 100 counts, measured 100.00 ms => 1.000
                 ms/decrement) and CAN 399 wire-fitted at exactly 100.000 Hz. [CONFIRMED, on-car]
                 See the TASK RATE entry below and memory/accord-task5-is-100hz-damper-cannot-damp-21hz.md.
  STEERING TASK: w_steer_control_task (FUN_0002214a), RTOS task. Gate masks are ECU STATE-MACHINE
                 masks (gp-0x67fa), NOT phase/duty-cycle counters.
                 🛑🛑 "ALL RUN IN LOCKSTEP WHENEVER THE STATE QUALIFIES" IS FALSIFIED -- corrected
                 2026-08-04. THE MASKS DIFFER, AND STATE 10 SPLITS THE CHAIN IN HALF. Verified at
                 instruction level in FUN_0002214a (0x2214a-0x22a84); the guard wraps the `jarl`
                 in the CALLER, so a masked-out state means the callee is NEVER INVOKED -- no stack
                 frame, 0% of body. Index is a plain `1 << (gp-0x67fa & 0xf)`, no off-by-one
                 (0x2214e ld.bu / 0x22172 andi 0xf / 0x2217c shl, recomputed identically @0x221bc).
                     0x221d6  andi 0x830 -> {4,5,11}     FUN_00036388 @0x22882 (return-to-centre)
                                                         FUN_000428d4 @0x22926 (OSC DETECTOR)
                     0x22518  andi 0x930 -> {4,5,8,11}   FUN_00028ea6 / FUN_0002b422 / FUN_0002b57a
                                                         (ARBITRATION = gp-0x6806's producer)
                     0x2269a  andi 0xc30 -> {4,5,10,11}  FUN_0003a382 @0x226a0 (residual lane)
                                                         FUN_0003aa2c @0x2291e (THE AGGREGATOR)
                 ⇒ IN STATE 10 THE AGGREGATOR AND THE RESIDUAL LANE RUN, WHILE THE DETECTOR, THE
                 RETURN-TO-CENTRE LANE AND ARBITRATION DO NOT. Assist is delivered from a stale
                 gp-0x6806. [EVIDENCE]
                 ★ State 10 is REACHABLE IN NORMAL OPERATION: written twice in FUN_00019970 (the
                 state-4 handler) -- 0x199CC (diagnostic, tp+0x74d0 == 0xa) and 0x19A72 (NORMAL,
                 gated on bit 15 of gp-0x6d78, with bit 16 -> state 11 taking priority). Writer set
                 over 33 st.b sites (Ghidra and a raw LE byte scan agree exactly, no undercount):
                 {1,3,4,5,6,7,8,9,10,11}, max 11.
                 ✅✅ SETTLED ON-CAR 2026-08-04 (route 50, V70's bit5): gp-0x67fa == 10 reads 0.0000%
                 of 18,010 frames ⇒ state ∈ {4,5,11} ⇒ FUN_00036388 AND FUN_000428d4 WERE INVOKED
                 ⇒ the gp-0x67df detector nulls on V64/V67/V68 are GENUINE and the state-gate
                 explanation below is REFUTED. Five builds vindicated, on a PRE-REGISTERED
                 prediction. [EVIDENCE] ⚠ It licenses "the call was made", NOT "the body ran" --
                 FUN_00046ea6(5) stays OPEN (see below).
                 🛑 AND THE STATE MACHINE HAS NO CADENCE [EVIDENCE, instruction level 2026-08-04]:
                 gp-0x68ad can NEVER be set in the field (both SET paths need permanently-zero flags
                 -- gp-0x437c, a UDS artifact, and gp-0x679d, whose sole writer FUN_000567c0
                 @0x567e2 reads gp-0x67ba, which has exactly ONE access image-wide and ZERO writers)
                 ⇒ FUN_00019970's `if (gp-0x68ad != 1) return;` ⇒ 4->5 NEVER FIRES; state 5 is DEAD
                 CODE on the road. And gp-0x6d78 bit 15 is a ONE-WAY, OR-ONLY latch (15 sites, one
                 writer FUN_000197b8 @0x197ca `|= 1<<n`, NO clear anywhere image-wide) ⇒ 4->10 is a
                 ONE-SHOT DRIFT and 10->4 can never fire after. ⇒ state 4 is STICKY once entered,
                 then leaves permanently; "the state-4 entry/exit cadence sets the ratchet's period"
                 is REFUTED structurally. Reachable set on a normal drive: {4, 11}.
                 ⚠ TENSION TO CARRY: the V42 substitution (0x454FE) is ASYMMETRIC (clamps command
                 increases, passes decreases) so continuously active it should print a RECTIFIED
                 waveform -- yet the ratchet measures SYMMETRIC (skew -0.16..+0.06, crest 2.07-2.45
                 vs a sine's 1.414). Evidence AGAINST it shaping the CURRENT ratchet. V71 restores
                 0x454FE because it is a confirmed fix LOST BY ACCIDENT (stock in V53->V70), not
                 because this mechanism is established.
                 [OPEN] what sets bits 15/16 of gp-0x6d78 mid-drive -- FUN_000197b8 has 21 callers,
                 untraced. That decides whether state 4 is sticky for a whole drive or only briefly.
                 ⇒ 🛑 (SUPERSEDED BY THE ABOVE, kept for the reasoning) A LIVE ALTERNATIVE
                 EXPLANATION FOR THE FIVE-BUILD DETECTOR NULL
                 (gp-0x67df 0/14,980 V64, 0/186,321 V67, 0/53,991 V68): "FUN_000428d4 was never
                 CALLED" has never been on the table and has the identical signature to "it ran and
                 found nothing".
                 ⚠ BUT V67's OWN PROBE ARGUES AGAINST IT, and this must be quoted alongside: state
                 10 is absent from 0x930 too, so arbitration -- gp-0x6806's producer -- is also
                 skipped there and the flag would go STALE. V67 measured gp-0x6806 == latActive in
                 150,302/150,327 = 99.983% of frames, all 25 disagreements single-frame transition
                 edges. A stale flag cannot track transitions that closely ⇒ the ECU is
                 predominantly NOT in state 10 while engaged, and the detector nulls are probably
                 GENUINE. [BELIEF -- indirect.] V70's bit5 rung (gp-0x67fa == 10) settles it
                 directly, and is non-vacuous in BOTH directions.
                 ⚠ FUN_000428d4 carries a SECOND, independent entry gate: FUN_00046ea6(5) on bit 5
                 of gp-0x18d0/gp-0x18d4, a fault/DTC-style bitmask, falling to a 0x8000 sentinel if
                 set. The record's earlier closure established only that that FUNCTION has one
                 caller -- NOT that the BIT is clear in operation. Still [OPEN].
                 [VERIFIED] State 4 sits inside all three masks and is where the governor's ratchet
                 substitution (fixed in V42) used to fire.
                 🛑 BUS `STEER_STATUS` IS NOT gp-0x67fa: route 4f reads ST == 0 on 47,990/47,990
                 frames while the car steered, and state 0 is in no mask. Any reasoning that equated
                 them (e.g. "ST==4 fires 0/37,922" as evidence about gp-0x67fa == 4) is invalid.
  TASK RATE    : ✅ RESOLVED 2026-07-31. The dispatcher is FUN_00014be4, a mod-100 rate divider on the
                 1 kHz tick (counter gp-0x4304); its wake argument is a 0-BASED TCB SLOT INDEX, proven
                 by byte-reading tp-0x3814 = 0xBB7EC = 0x000BB920 and confirming idx*0x30 + 0xBB920
                 reproduces all seven task entry points at +0x08 exactly. [VERIFIED]
                     idx 0  FUN_0002214A  task 1  every tick     -> 1000 Hz
                     idx 1  FUN_00022A88  task 2  c & 1          ->  500 Hz
                     idx 3  FUN_00022B24  task 4  c % 5 == 2     ->  200 Hz
                     idx 4  FUN_00022CA0  task 5  c % 10 == 4    ->  100 Hz   <<< boost + damping
                     idx 5  FUN_0002351E  task 6  c == 0x10      ->   10 Hz
                 Task 1 hosts arbitration, FUN_0003b66a, the aggregator, the governor and the shaper.
                 ★★ LOAD-BEARING: boost (FUN_00034a72) and damping (FUN_00034350) run at 100 Hz, so a
                 zero-order hold costs 37.6 deg average / 75.2 deg worst-case transport lag at 20.9 Hz
                 BEFORE any plant phase. Damping needs force in phase with velocity => the damper
                 structurally cannot damp the 20.9 Hz mode, and may be ANTI-damping there. That is an
                 explanation for every null damper lever (V44 FactorC; V47 FactorC+FactorE together --
                 🛑 CORRECTED 2026-08-06: both wrote modes 10/11 on a modes-24/26 car, so they were
                 INERT BY TABLE SELECTION and their nulls carry no information about this at all)
                 INDEPENDENT of the FactorC speed axis,
                 and a candidate reason the damping-SIGN question flip-flopped for four sessions: a
                 sign correct by construction can still act with the wrong phase when it is refreshed
                 10x slower than the mode. It also invalidates V59's eps table, which bracketed 1 kHz
                 and 500 Hz for task 5. 🛑 Prefer task 1 for any dynamics fix.
                 See memory/accord-task5-is-100hz-damper-cannot-damp-21hz.md.
                 ✅ CLOCK AUDIT RESOLVED 2026-07-31 -- the NUMBER survives, the REASON was wrong.
                   🛑 PCLK = 40 MHz, NOT 80. Likely original error: conflating HEAPCLK (80 MHz) with
                      PCLK; option-byte Table 6-7 makes PCLK = HEAPCLK/2 the ONLY legal setting at
                      HEAPCLK = 80 MHz. HEAPCLK = 80 MHz is pinned by the firmware's own CLMA1 compare
                      values, orchestrator-verified in the stock dump: 0x0053 @0x5C8D8 and 0x004D
                      @0x5C8E0 -> CLMA1CMPH/CMPL, an exact match to the datasheet's worked row for
                      CLMA1 @80 MHz / 16 MHz main OSC.
                   🛑🛑 OSTM0 IS NOT THE RTOS TICK and never was. At 40 MHz it is 2.000 ms = 500 Hz,
                      but that is moot: the EI trampoline FUN_0001492a dispatches only EIIC
                      0x970/0x600/0x340/0x470/0x110/0x100/0xf0 + default -- NO OSTM0 arm exists, and
                      gp-0x42fc (the rate divider's trigger flag) is written ONLY by the 0x340 arm.
                      EIIC 0x340 = TAUJ1I2. Orchestrator-verified by decompile. ⇒ the whole
                      "OSTM0CMP = 79999 ⇒ 1 kHz control tick" chain was a red herring at BOTH ends.
                      ⚠ TAUJ1's own period register was NOT located, so the base rate is still not
                      pinned to a register value.
                   ✅ THE 1 kHz / 100 Hz FIGURES SURVIVE, because they never depended on that chain:
                      task 1 = 1 kHz is an ON-CAR MEASUREMENT (STEER_STATUS=4 dwell, cal 0xC64DF = 100
                      counts measured at 100.00 ms; CAN 399 wire-fitted at exactly 100.000 Hz), and
                      task 5 = task 1 / 10 is integer arithmetic. 37.6/75.2 deg stand as written.
                   ⚠ WHAT DOES PROPAGATE: the FOC/TSG20 carrier "~8 kHz" was computed explicitly
                      conditioned on PCLK = 80 MHz => it is ~4 kHz at 40 MHz, and TSG20's own
                      clock-select has never been verified. Treat both as OPEN. Also: EIIC 0x600 is
                      CSIH1IR (serial), not ADC-complete; EIIC 0x970 is TSG21I05, not TSG20 (= 0x860).
                 (superseded) the provisional flag that prompted the audit:
                   SOLID, clock-independent: the DIVIDER RATIO. Task 5 fires once per 10 task-1
                     invocations. That is integer arithmetic in FUN_00014be4 and holds whatever the
                     clock is, so "the damper is refreshed 10x slower than the 1 kHz chain" stands.
                   ⚠ CLOCK-DEPENDENT: every ABSOLUTE Hz and therefore every DEGREE above. The 1 kHz
                     base tick comes from OSTM0CMP = 79999 and an assumed PCLK = 80 MHz -- and that
                     80 MHz was NEVER read from the datasheet. The kit derived it by elimination
                     ("PCLK is one of {48,64,80,160}; only 80 gives a clean 1 ms"), which is CIRCULAR:
                     it assumes the answer to select the clock that produces it. At 160 MHz task 5
                     would be 200 Hz (lag halves); at 48 MHz, 60 Hz (lag rises ~1.7x).
                     A datasheet-grounded audit of the whole clock tree is running. Treat 37.6/75.2
                     deg as PROVISIONAL until it lands. The on-car 100.000 Hz CAN cadence is an
                     independent anchor that the audit must reproduce.
  SENSOR-B RATE: FUN_0007f3f8/FUN_0007e74a produce gp-0x4f62 (torque-rate) with delay cal tp+0x7c42=4
                 producer samples; consumer/producer share the same state-mask phase, so no rate
                 mismatch exists. [VERIFIED functions/delay | OPEN wall-clock Hz]
  DECIDER TASK : engage decider + deliver-commit run on a sibling RTOS task FUN_00022ca0. [VERIFIED]
  FOC + PWM    : shared EI trampoline FUN_0001492a dispatches by EIIC cause: 0x600 -> ADC-complete ->
                 FOC (FUN_00071272); 0x970 -> FUN_00061614 -> TSG20 PWM compare write (the motor).
                 [VERIFIED dispatch | OPEN carrier Hz]
  CAN RX       : hardware mailbox ISR stages STEER_TORQUE into the routed buffer; exact ISR entry not
                 located. [OPEN]
=======================================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional


# =====================================================================================================
# SECTION 0 -- CALIBRATION CONSTANTS
# -----------------------------------------------------------------------------------------------------
# Every field is a firmware calibration in the CRC-protected 0xC6000 block (unless noted); default is
# the stock (V9b) value, and build variants override a subset (see for_build()). Per-field tp/absolute
# addresses are noted in each field's own trailing comment below.
# =====================================================================================================

V9_FULL_SCALE_POSITIVE = (15360 * 891) >> 15
V9_FULL_SCALE_NEGATIVE = (-15360 * 891) >> 15
V9_FULL_SCALE_MIN_MAGNITUDE = min(abs(V9_FULL_SCALE_POSITIVE), abs(V9_FULL_SCALE_NEGATIVE))


@dataclass
class Calibration:
    # ---- LKAS reach (V14/V18 lineage, retained by V31 & V37) --------------------------------------
    lkas_output_gain: int = 891          # Q15 arb output gain. V31/V37=1782; V38=3564 (4x stock)
    # 0xC646C has 6 readers: 1 forward (this field), 1 dead, 4 feedback (shared_sensor_scale below).
    # V57 decouples the forward reader onto private cal 0xC6CD0, reverting 0xC646C to stock 891 for
    # the feedback readers only. Gain history is TWO doublings: 891 (V9) -> 1782 (V22-V37) -> 3564 (V38+).
    shared_sensor_scale: int = 891       # 0xC646C as seen by the 4 feedback readers; == lkas_output_gain
                                         # through V56, reverts to stock 891 on V57 (decoupled).
                                         # 🛑 3564 again on V76/V78/V79/V80 -- the V38 rebase silently
                                         # dropped V57's decouple (see the header block).
    arb_output_clamp: int = 512          # symmetric arb clamp. V31/V37=1024; V38=2048
    pack_output_clamp: int = 512         # symmetric limit&pack clamp. V31/V37=1024; V38=2048
    reengage_ramp_step: int = 0x11       # re-engage/debounce ramp ceiling (17). V31/V37 -> 0x1B (27)

    # ---- CAN setpoint shaping (CODE literals, shown as cals for readability) -----------------------
    setpoint_scale: int = -4             # STEER_TORQUE * -4  (sign + Q-shift), FUN_00052676
    setpoint_clamp: int = 0x4000         # +/- clamp on the scaled setpoint
    setpoint_fault_sentinel: int = 0x7FFF  # written on checksum/counter/timeout fault
    lkas_validity_timeout_ticks: int = 500  # STEER_TORQUE staleness timeout

    # ---- Gentle-EME STEER_STATUS debounce SM (V36/V37 disable these) -------------------------------
    # Signals: torque channel = min(|arb signal| >> 5, 255)  (a byte, <=255)
    #          rate   channel = angular-rate magnitude       (u16, <=65535)
    deb_torque_rise: int = 112           # torque > this (rise). V37 -> 255 (u8 max => never fires)
    deb_torque_hold: int = 96            # torque > this (hold). V37 -> 255
    deb_torque_and_hi: int = 64          # torque > this AND rate>deb_rate_and_hi. V37 -> 255
    deb_torque_and_lo: int = 54          # torque > this AND rate>deb_rate_and_lo. V37 -> 255
    deb_rate_primary: int = 1600         # rate > this (alone). V37 -> 65535 (u16 max => never fires)
    deb_rate_and_hi: int = 896           # combined tier A. V37 -> 65535
    deb_rate_and_lo: int = 1280          # combined tier B. V37 -> 65535
    deb_count_seed: int = 5              # counter starts at -5; fires after 5 sustained qualifying cyc
    deb_hold_seed: int = 100             # STEER_STATUS=4 hold length once fired

    # ---- DTC-0x49 fault counter (V37 disables via the gate) ----------------------------------------
    dtc49_torque_gate: int = 112         # counter B increments while torque > this. V37 -> 255 (off)
    dtc49_saturation: int = 100          # counter B trips DTC 0x49 after this many cycles (50+50)

    # ---- Engage/disengage decider gates (the "engage SM"; V33/V34/V35 tried these, none were it) ---
    dec_torque_max: int = 320            # voter MAX torque >= this -> refuse/leave (verdict 2)
    dec_angle_consensus: int = 4825      # angle deviation >= this -> verdict 4
    dec_rate_gate: int = 1600            # rate magnitude >= this -> refuse (verdict 5)
    dec_gate6: int = 4096                # gp-0x4f68 >= this -> refuse (verdict 6)
    dec_gate7: int = 3584               # gp-0x6ba4 >= this -> verdict 7

    # ---- Low-speed steer lockout: two-sided speed window at top of FUN_00028ea6. [VERIFIED] ---------
    # vs gp-0x6a5e (voted vehicle speed, 64.0625 counts/km/h); failing it is the ONLY writer of
    # STEER_STATUS=3, which gates STEER_CONTROL_ACTIVE + the authority ramp; each cal has exactly one
    # reader image-wide. The bypass gp-0x68b3 (set only at true standstill, FUN_0004d0d0) is a runtime
    # flag, not a field here -- see steer_status_low_speed_lockout(). resonance_lane_output_bound_q15
    # is FUN_0003a382's Q15 output-bound LERP Y[0]/Y[1] (0xC6AFC/FE): V54 measured it selecting unity
    # in 100% of normal frames; V56 zeroed it (muted the lane) and was later reverted.
    resonance_lane_output_bound_q15: int = 32768   # 0xC6AFC / 0xC6AFE. V56 -> 0
    speed_window_lo: int = 320           # tp+0x72ea (0xC62EA) = 4.995 km/h = 3.104 mph. V53 -> 0
    speed_window_hi: int = 12800         # tp+0x72e8 (0xC62E8) = 199.8 km/h. Never edited (0x7FFF SNA
                                         #   sentinel must keep failing this bound).

    # ---- Soft-EME windup shaper (V30 widens corridor; V31 adds the boost floor) --------------------
    corridor_upper: int = 1024           # corridor arm magnitude (driver-override arm). V31/V37 -> 4096
    corridor_lower: int = -1024          #                                               V31/V37 -> -4096
    boost_floor: int = 0                 # boost arm Y[0] (stock 0/1536/2048). V31/V37 -> flat 4096
    boost_y1: int = 1536                 # boost arm Y[1].                     V31/V37 -> 4096
    boost_y2: int = 2048                 # boost arm Y[2].                     V31/V37 -> 4096
    authority_scale: int = 1092          # authority = (|integrator>>15| * this) >> 10
    sm2_arm: int = 16384                 # authority threshold; entry also requires command and gate!=3
    sm3_clamp: int = 30720               # |integrator>>15| saturation threshold before SM3 dwell
    sm1_arm: int = 2048                  # SM1 (fast anti-runaway; velocity+opposition gated) -- untouched
    corridor_gate: int = 9216            # corridor arm forced off when |pos_err| <= this (hands-off)
    boost_latch_auth: int = 16384        # boost arm latched to 0 once authority > this ...
    boost_latch_dwell: int = 20          #   ... sustained this many cycles
    sm2_variant_gate: int = 3            # tp+0x74cc; 3 inhibits the SM2 authority-threshold entry
    sm3_dwell: int = 20                  # tp+0x7298; saturation dwell before factor becomes cal_7420
    sm3_cut_factor_q15: int = 0          # tp+0x7420; V38/V39 cut factor
    shaper_mode: int = 0                 # tp+0x74c8; selects gp-0x6acc preprocessing
    shaper_bias: int = 0                 # tp+0x71d4
    shaper_term_selector: int = 0        # tp+0x74c9; 0 selects computed r28 as final r20

    # ---- Downstream fixed clamps (CODE literals in the limit cascade) ------------------------------
    arb_setpoint_limit: int = 15360      # symmetric +/- clamp on the LKAS setpoint. [VERIFIED,
                                         # byte-dumped] a degenerate 9-point LERP, flat 15360 at every
                                         # breakpoint in all 28 records/5 banks; axis gp-0x6a5e (voted
                                         # VEHICLE SPEED) is moot since the Y row is flat. Selected by
                                         # gp-0x674e, static per part number (A160 -> selector 1, record
                                         # 0xE41A8). openpilot's torqueBP*4=16384 clips the top 6.25% at
                                         # 15360; raising is safe (no float twin). V38 patches all 8
                                         # reachable per-part-number records (72 halfwords total,
                                         # build_v38_tva.py, verifies 49/49).
    assist_ramp_ticks: int = 10          # tp+0x74d1 * 10; assist engage-ramp dwell per state (gp-0x68c8)
    distribute_lkas_lane_clamp: int = 0x2800   # LKAS rides the +/-0x2800 distributor lane
    mixer_gate_clamp: int = 0x2800       # gate: |x|<=0x2800 ? x : 0x7FFF-sentinel
    shaper_final_clamp: int = 0x2000     # shaper output final +/-0x2000 clamp
    runtime_governor: int = 4762         # NOMINAL CEILING of the computed runtime governor gp-0x4f64
                                          #   (cal 0xC6202). NOT a flat clamp -- see soft_eme_windup_shaper
                                          #   for the MIN(4762, adaptive LERP, unresolved budget B) schedule.
    governor_slew_step_normal: int = 512 # tp+0x7206 (0xC6206), before a Q15 step scale. V40 -> 0xFFFF
    governor_slew_step_alt: int = 205    # tp+0x7208 (0xC6208). V40 -> 0xFFFF
                                         # Selector gp-0x67f5 (0=normal else alt); FUN_00041eec forces
                                         # alt with no debounce on a >=65-count vote divergence, pinning
                                         # hard dynamic turns to the slow step.

    # ---- motor-rate adaptive torque cap (bank A, tp+0x620C/0x6224 records; slopes tp+0x6030/0x6038)
    # V40 flattens Y to the table max AND zeroes the slopes; a flat Y with live slopes still
    # interpolates. See rate_cap_binding_analysis() for why this matters only above stock reach.
    rate_cap_y: tuple = (5325, 3584, 2406, 1587, 512)
    rate_cap_slope_q13: tuple = (-21940, -12059, -5593, -22021)

    # ---- V39 experimental direct torque-rate guard (CODE literals / reused driver threshold) ------
    suppress_direct_torque_rate_assist: bool = False
    direct_rate_lkas_threshold: int = V9_FULL_SCALE_MIN_MAGNITUDE  # 417; includes +/- V9 full scale

    build: str = "V9"

    @staticmethod
    def for_build(name: str) -> "Calibration":
        """Return the calibration set for any modelled build (V9 .. V57)."""
        cal = Calibration(build=name)
        if name == "V9":
            return cal
        # --- V31: 2x reach + soft-EME fix (corridor x4 + boost floor 4096) --------------------------
        cal = replace(
            cal,
            lkas_output_gain=1782, shared_sensor_scale=1782,
            arb_output_clamp=1024, pack_output_clamp=1024, reengage_ramp_step=0x1B,
            corridor_upper=4096, corridor_lower=-4096, boost_floor=4096, boost_y1=4096, boost_y2=4096,
        )
        if name == "V31":
            return cal
        # --- V37 onward: gentle-EME debounce SM off + DTC-0x49 counter off -------------------------
        if name in ("V37", "V38", "V39", "V40", "V41", "V42", "V53", "V54", "V55", "V56", "V57"):
            cal = replace(
                cal,
                deb_torque_rise=255, deb_torque_hold=255, deb_torque_and_hi=255, deb_torque_and_lo=255,
                deb_rate_primary=65535, deb_rate_and_hi=65535, deb_rate_and_lo=65535,
                dtc49_torque_gate=255,
            )
            if name == "V37":
                return cal
            cal = replace(
                cal,
                lkas_output_gain=3564, shared_sensor_scale=3564,
                arb_output_clamp=2048, pack_output_clamp=2048,
                corridor_upper=5120, corridor_lower=-5120,
                boost_floor=5120, boost_y1=5120, boost_y2=5120,
                arb_setpoint_limit=16384,
            )
            if name == "V38":
                return cal
            # --- V53: V38 + FOURFRAME2 read-only telemetry cave + min steer speed 0. FLASHED; the
            # speed-window prediction below is CONFIRMED on-car (route 1a); the telemetry cave never
            # transmitted (uninterpretable null, does not affect this model). Cut from V38, so it does
            # NOT carry V42's ratchet fix.
            if name == "V53":
                return replace(cal, speed_window_lo=0)
            # --- V54: V38 + speed-window-0 + a report-only gp-0x6966 (soft-EME authority) probe on CAN
            # 0x14A byte4 bits 7:3. FLASHED, fault-free. MEASUREMENT (route 1b): authority stayed in
            # [0,127] (~0.39% of saturation) with zero variation -- V31's boost floor (5120, not the
            # memoried 4096) prevents windup, so authority is ~0 BY DESIGN on every V31+ build. The
            # 0xC6AF0 LERP therefore selects unity in ~100% of normal operation; GATE 2 (the lane's
            # damping sign) remains OPEN.
            if name == "V54":
                return replace(cal, speed_window_lo=0)
            # --- V55: V38 + speed-window-0 + a DUAL report-only probe on CAN 0x14A: damper-variant
            # index bit + a 4-bit window on gp-0x6b98 (final merged command). BUILT to PARTITION whether
            # the ~21 Hz mode is commanded or plant-only. FLASHED (route 1c): the mode IS in gp-0x6b98
            # (coherence 0.93 with the sensor); openpilot's own contribution is 8.7-38x too small to
            # explain it and is exactly 0 while railed yet the command still carries the mode, so the
            # loop closes INSIDE the EPS; the sensor->command transfer is flat across 1-21 Hz, ruling out
            # every 0xC646C-gated (filtered) lane; bit7=1 in 100% of frames confirms V44/V47 hit the live
            # damper tables. Direction (damping sign) is NOT settled by this closed-loop measurement --
            # that is V56's GATE 2.
            if name == "V55":
                return replace(cal, speed_window_lo=0)
            # --- V56: V55 + mute FUN_0003a382's residual lane (0xC6AF0 LERP Y[0]/Y[1] -> 0, both the
            # below-knot and interpolated paths). BUILT then FLASHED (route 24, first road drive with a
            # probe): 21 Hz UNCHANGED (786x engaged/disengaged, matching V55) -- gp-0x6ad4/FUN_0003a382
            # is ELIMINATED as the source, all three branches at once -- AND operator reports damping
            # removed, with a new sharp 8.69 Hz line appearing 15-20 m/s engaged+hands-off. REVERTED to
            # V55; a partial restore is not a candidate (0% and 100% authority gave the same 21 Hz).
            # Monitor/protection risk was and remains closed; the real cost was manual feel.
            if name == "V56":
                return replace(cal, speed_window_lo=0, resonance_lane_output_bound_q15=0)
            # --- V57: V55 (not V56) + (A) decouple 0xC646C's forward LKAS reader onto private cal
            # 0xC6CD0 (still 3564), reverting the shared cal to stock 891 for the 4 feedback readers
            # only -- expected NULL for the 20-25 Hz mode (<=0.28 dB at 22 Hz, the most attenuated
            # aggregator lane) and NULL for manual feel (operator has driven 891/1782/3564 and reports
            # no difference; disengaged, only the feedback readers are live). (B) a report-only
            # deadband-gate probe on CAN 0x14A (bit6 tests gp-0x6806==0 by exact equality, closing a
            # parity gap in the prior STEER_CONTROL_ACTIVE measurement); expected NEGATIVE.
            if name == "V57":
                return replace(cal, speed_window_lo=0, shared_sensor_scale=891)
            if name == "V39":
                return replace(cal, suppress_direct_torque_rate_assist=True)
            # --- V40: V38 baseline (NOT V39 -- the r24 guard is dropped entirely) + two cal edits.
            # 1. governor slew steps -> 0xFFFF, so recovery after a sign-crossing reset is immediate
            # 2. motor-rate cap flattened to the table max with zeroed slopes, so the taper never binds
            if name == "V40":
                return replace(
                    cal,
                    governor_slew_step_normal=0xFFFF, governor_slew_step_alt=0xFFFF,
                    rate_cap_y=(5325,) * 5, rate_cap_slope_q13=(0, 0, 0, 0),
                )
            # --- V41: V38 + the cap flatten ONLY. 0xC6000 untouched, so the slew stays stock.
            # FLASHED 2026-07-20: boots and drives cleanly, fixes NEITHER symptom. Falsifies the cap
            # as a root cause, and exonerates the cap flatten as V40's ignition-fault mechanism.
            if name == "V41":
                return replace(cal, rate_cap_y=(5325,) * 5, rate_cap_slope_q13=(0, 0, 0, 0))
            # --- V42: V38 + RAMP-TIME PARITY on the merged-governor slew. Steps scaled by the same 4x
            # V38 applied to reach, restoring stock's cycles-to-full-command. Cap left STOCK (V41
            # falsified it, so there is no reason to carry that edit). Targets the RATCHET only --
            # see gain_rescaling_invariance_analysis() for why it cannot touch the 5 mph vibration.
            if name == "V42":
                return replace(cal, governor_slew_step_normal=2048, governor_slew_step_alt=820)
        raise ValueError(
            f"unknown build {name!r} "
            f"(expected V9, V31, V37, V38, V39, V40, V41, V42, V53, V54, V55, V56, or V57)")


# =====================================================================================================
# SECTION 1 -- SIGNAL / STATE CONTAINERS
# =====================================================================================================

@dataclass
class CanSteeringControl:
    """[CONFIRMED] CAN 0xE4 STEERING_CONTROL from the comma (openpilot -> EPS). DLC 5.
    STEER_TORQUE = signed 16-bit, bytes[0:1] big-endian, range ~ +/-4096 (opendbc _bosch_2018.dbc).
    Also carries STEER_REQUEST / status bits in byte2/byte4 and a checksum+counter for validity."""
    steer_torque: int = 0        # signed16 BE, +/-4096  [CONFIRMED anchor #1]
    steer_request: bool = False  # request/enable bit (byte2/byte4)
    checksum_ok: bool = True     # comms-validity (intake gate; cannot cut on value)
    counter_ok: bool = True
    fresh: bool = True           # not stale (within lkas_validity_timeout_ticks)


@dataclass
class SensorInputs:
    """Physical plant sensors read by the EPS ADC / resolver each loop."""
    # [CONFIRMED anchor #2] steering-wheel (column) torque sensor -- 3 redundant channels read via the
    # hardware Timer Array Unit (TAUA0 capture regs @0xFFFFC400), float-scaled -- NOT raw ADC coils.
    column_torque_coils: tuple = (0, 0, 0)   # 3 raw torque channels (timer-capture, float-scaled)
    column_torque_refs: tuple = (0, 0, 0)    # 3 reference channels for plausibility
    column_torque_sensor_b: Optional[int] = None  # gp-0x4f60; explicit replay input when available
    column_torque_rate: Optional[int] = None      # gp-0x4f62; exact replay overrides local 4-sample model
    # [VERIFIED] derived plant signals used downstream:
    steering_angle: float = 0.0              # column angle
    steering_angle_rate: float = 0.0         # column angular velocity (deg/s-ish, signed)
    # [VERIFIED] two real speed consumers exist: FUN_00028ea6's low-speed window (cals 0xC62EA/0xC62E8,
    # gating STEER_CONTROL_ACTIVE + the authority ramp) and the G1 governor FUN_0004503c (cal 0xC6316
    # skips the slew limiter below ~10 km/h); no aggregator lane and no rate-adaptive table reads road
    # speed -- those are keyed on motor/resolver electrical-angle rate (gp-0x6ac0) instead.
    vehicle_speed: float = 0.0               # km/h; consumed by steer_status_low_speed_lockout()
    eps_temperature: float = 25.0            # thermal-gain compensation input
    foc_rotor_angle: float = 0.0             # resolver atan2 electrical angle
    foc_phase_currents: tuple = (0.0, 0.0)   # measured phase currents (FOC feedback)
    motor_rate_raw: int = 0                  # gp-0x6ac0, motor resolver electrical-angle rate

    # The normalization that maps gp-0x6ac0 to the governor table axis is only partly characterized.
    # None means "term not replayed; assume nonbinding", never "firmware computed exactly this value".
    governor_axis_z: Optional[int] = None
    governor_budget_limit: Optional[int] = None
    governor_motor_state: int = 1            # gp-0x4e5a; states 0/2 omit the unresolved budget minimum
    runtime_governor_override: Optional[int] = None  # observed gp-0x4f64, preferred for RAM replay
    governor_limit_scale_q15: int = 0x8000   # exact bank output can be supplied; identity by default
    governor_post_scale_q15: int = 0x8000
    governor_step_scale_q15: int = 0x8000
    governor_slew_alt: bool = False
    governor_substitution_state: int = 0  # gp-0x67fa; state 4 keeps the lower-magnitude held value
    # gp-0x6ad0: input to FUN_000456a4, a WRITE-ONLY telemetry mirror (no reader anywhere image-wide)
    # of a rate-vs-motor-rate compensation term (two 3-point LERPs, gate-threshold @0xC6830 falling,
    # min-clamp @0xC67D0 rising, gain cal 0xC6204=3072/1024=3 exact; ceiling 2560, not the previously
    # recorded 4762). [VERIFIED] The gate is a bare 2-instruction compare (no hysteresis/dwell) on
    # gp-0x6a10 vs LERP1(gp-0x6ac0) -- structurally sufficient for a 0->2560 one-cycle step -- but
    # gp-0x6a10 is NOT command-derived (a separate engage-SM producer chain from gp-0x6ac0's resolver
    # path), so the V38 invariance argument still holds here; all 11 cal cells have zero consumers
    # outside FUN_000456a4, making this the cleanest patch surface found to date if ever revisited.
    post_governor_compensation: int = 0

    # FUN_00042af8 has two distinct inputs: gp-0x6acc drives the integrator; gp-0x6afe + r20 drives
    # final gp-0x6b98. Unfinished producers are explicit replay controls rather than guessed aliases.
    secondary_mixer_command: int = 0          # gp-0x6afe
    shaper_upper_bound_override: Optional[int] = None  # r29 / gp-0x6af6
    shaper_lower_bound_override: Optional[int] = None  # r27 / gp-0x6b00
    shaper_term_r20_override: Optional[int] = None     # gp-0x6b04 when C64C9==0
    shaper_blend_q15: int = 0
    shaper_alternate_term: int = 0
    shaper_state_scale_q15_override: Optional[int] = None
    shaper_hands_off: bool = True

    # Unfinished assist producers remain explicit replay inputs rather than invented zero-labelled facts.
    assist_lane_overrides: dict = field(default_factory=dict)


@dataclass
class EpsState:
    """Persistent RAM the state machines carry between ticks. gp-relative address in each comment."""
    # ---- LKAS command pipeline stages ----
    lkas_setpoint: int = 0        # gp-0x69ae (0xFEDF1652) clamp(STEER_TORQUE*-4)
    arb_command: int = 0          # gp-0x6b3c (0xFEDF14C4) arbitration gated command
    mixed_command: int = 0        # gp-0x6b4c, LKAS-internal lane into the demand aggregator
    secondary_mixer_command: int = 0  # gp-0x6afe, separate lane consumed at final shaper output
    merged_command: int = 0       # gp-0x6b98 (0xFEDF1468) post-shaper command to the FOC loop
    q_current_ref: float = 0.0    # FOC q-axis current reference (the actual "motor torque" demand)

    # ---- Driver-torque voter outputs ----
    col_torque_max: int = 0       # gp-0x6a62 (0xFEDF159E) MAX voter (0xFFFF = invalid-sensor sentinel)
    # ✅ RENAMED 2026-08-03 from `col_torque_avg`. gp-0x6a5e is voted VEHICLE SPEED (voter
    # FUN_00041eec, settled 2026-07-29), never column torque; the old name predated that
    # reclassification and read as evidence of a role it never had. All 8 call sites moved together.
    speed_voted: int = 0          # gp-0x6a5e (0xFEDF15A2) AVG voter -- VOTED VEHICLE SPEED
    col_rate_mag: int = 0         # gp-0x6a60 (0xFEDF15A0) angular-RATE magnitude (NOT torque)

    # ---- Engage/disengage decider ----
    engage_state: int = 0         # gp-0x67DC (0xFEDF1824) dispatcher state
    decider_verdict: int = 0      # r12: 0=pass 2=torqueMAX 4=angle 5=rate 6/7=other refusals
    enable_fsm: int = 0           # gp-0x67a4 (0xFEDF185C) ENABLE gate; LKAS passes only in {2,3}

    # ---- STEER_STATUS debounce SM (gentle EME) ----
    steer_status: int = 0         # gp-0x6807 (0xFEDF17F9) 4=NO_TORQUE_ALERT_2 (gentle EME), 7=fault
    deb_counter: int = 0          # gp-0x6757 signed; starts at -deb_count_seed, fires at >=0
    dtc49_counter: int = 0        # gp-0x6758 DTC-0x49 fail counter (interlocked to STEER_STATUS=4)

    # ---- Soft-EME windup shaper (SM2/SM3) ----
    soft_eme_integrator_q15: int = 0  # gp-0x3570 (0xFEDF4A90), signed32 Q15
    iir_envelope: int = 0         # gp-0x3574 column-velocity IIR envelope arm
    boost_latch_state: int = 1    # gp-0x3562; state 2 suppresses boost until authority returns to zero
    boost_latch_counter: int = 0  # gp-0x355c
    boost_latched_off: bool = False  # derived compatibility view used by the monitor abstraction
    authority: int = 0            # gp-0x6966 = (|integrator>>15| * authority_scale) >> 10
    sm2_state: int = 1            # gp-0x355e
    sm2_factor_q15: int = 0x8000  # gp-0x6962; recovery/ramp internals remain an explicit abstraction
    sm2_entry_seen: bool = False
    sm3_state: int = 2            # gp-0x355f
    sm3_counter: int = 0          # gp-0x3568
    sm3_factor_q15: int = 0x8000
    lkas_authority_cut: bool = False  # true when the consolidated modeled state factor reaches zero
    shaper_internal_command: int = 0  # gp-0x6b08, sanitized/preprocessed gp-0x6acc
    shaper_term_r20: int = 0      # gp-0x6b04 on V38/V39 (C64C9==0)

    # ---- Base driver assist (Section 3B) ----
    assist_mode: int = 26         # gp+0x63fd (0xFEDFE3FD) POSITIVE displacement; assist curve select
                                  #   0..33. NOT static (2026-08-05): V73's probe read it live over 104,061
                                  #   frames, switching on EVERY LKAS engagement edge (1.02s on rise, 2.08s
                                  #   on fall, 18/18 transitions, 99.09% lag-matched).
                                  #   🛑 The probe field is 4 BITS and DROPS BIT 4, so its {8,10} readings mean
                                  #   true in {8,24} and {10,26}. Raw 8 is in NO row of 0xCD000 => manual = 24;
                                  #   only row 11 'TVCA4' holds 24 and all four columns come from one row =>
                                  #   engaged = 26 (this default). The car is TVCA4, NOT TVAA1.
                                  #   Writer = FUN_00042746, see below.
    assist_substate: int = 1      # gp-0x67fe EPS assist substate; assist valid only in {1,2}
    plausibility_ok: bool = True  # gp-0x67f4 == 1, converge/plausible flag from the voter FUN_00041eec
    col_torque_sensor_b: int = 0  # gp-0x4f60 (0xFEDF30A0) SENSOR-B (TAS) column torque -- the signal
                                  #   packed to CAN 399 STEER_TORQUE_SENSOR. NOT vehicle speed, and NOT
                                   #   angular velocity (both labels appear in older notes and are wrong).
    col_torque_rate: int = 0       # gp-0x4f62: 4-sample finite difference of Sensor-B torque
    col_torque_history: list = field(default_factory=list)
    motor_rate_raw: int = 0        # gp-0x6ac0: motor resolver electrical-angle rate
    assist_ramp_state: int = 0    # gp-0x682e 4-state assist engage ramp {0,1,2,3}
    assist_ramp_timer: int = 0    # gp-0x68c8 ramp timer vs (tp+0x74d1 * 10)
    assist_rate_state: int = 0    # gp-0x6bb2/4/6/8 cross-tick integrity WATCHDOG (NOT a rate limiter)
    assist_polarity: int = 1      # gp-0x6752 assist polarity (-1/0/+1)
    assist_lane: int = 0          # gp-0x6bbe (0xFEDF1442) the base-assist aggregator lane
    boost_fir_out: int = 0        # gp-0x6b9a, signed FUN_0003b66a output; gp-0x6ba6 is its magnitude
    # ★★★ RESOLVED 2026-07-31: gp-0x671a is an OSCILLATION DETECTOR -- a hard-REVERSAL COUNTER, latched.
    # FUN_000428d4 @1 kHz, FSM {neutral, +latched, -latched} at gp-0x67df, dwell gp-0x6759, raw count
    # gp-0x357c. NEUTRAL zeroes dwell AND raw count EVERY tick (0x428FE/0x42906) and exits only if
    # |gp-0x6c2c| > T; a crossing of the OPPOSITE threshold increments; HYST=50 quiet ticks -> neutral.
    #   T = 12800 (0xC620A, ld.h) · HYST = 50 (0xC64DD, ld.bu) · CEIL = 5 (0xC64FA, ld.bu)
    # => reads 0 during smooth steering; `>= 5` means AN OSCILLATION IS HAPPENING.
    # 🛑🛑 MEASURED ON-CAR 2026-07-31 (V64, route 35): IT NEVER ARMS. gp-0x671a and gp-0x67df read ZERO
    # on all 14,980 frames of a 149.8 s all-creep drive with the grinding present throughout, through
    # 1,158 steering-rate sign reversals. The struck prediction below was wrong:
    #   ~~"Arms in ~125-150 ms at 18-21 Hz (half-period 24-28 ms, inside the 50 ms dwell timeout)"~~
    # It reasoned from the DWELL timeout only and never checked whether the INPUT reaches T at all.
    # It does not: |gp-0x6c2c| never crossed 12800 once. => V63/V64's oscillation-gated cal edits
    # (0xC6440, 0xC643E) are INERT on this firmware. Detector-gated damping is CLOSED at this threshold.
    # gp-0x6c2c is a MOTOR-RATE DERIVATIVE, not torque -- see _detector_input_6c2c() below.
    # ⚠ AND EVEN IF ARMED THE RISE IS SMALL: at the hands-off-creep LERP axis (X=0) the DEFAULT arms are
    # r24 2305 (0xD2AEC) and r26 3072 (gain_A rec0/rec1), vs osc arms 2048 and 1536 -- i.e. Honda's
    # oscillation arms are gain REDUCTIONS. V64 delivers r24 x1.78 and r26 x1.00 (a no-op) against
    # V62's clean x2 on both lanes under every arm.
    # 🛑 THE OUTPUT IS A ONE-WAY LATCH WITH A 5 s HOLD (output stage 0x429A0-0x42A12, the sole st.b to
    # gp-0x671a is 0x42A12): once the held value reaches CEIL it is RE-PINNED to CEIL every tick. The
    # only way down is 5000 consecutive ticks (cal 0xC6270) with gp-0x6a5e >= 640 (cal 0xC62DE) AND
    # raw count == 0.
    # ⚠ CORRECTED 2026-08-03: gp-0x6a5e is VOTED VEHICLE SPEED, not driver torque (voter FUN_00041eec,
    # settled 2026-07-29 -- the same reclassification that invalidated V44/V47's rationale).
    # ✅ CONFIRMED from fresh disassembly (0x429a0-0x429d8): `bh`@0x429A8 RELOADS the hold timer (latch
    # held) iff gp-0x6a5e < 0xC62DE=640=10.0 km/h OR a fresh reversal this tick; ABOVE 10 km/h with no
    # reversal the timer decrements and the latch releases to EXACTLY 0 the tick it hits zero -- a clean
    # 5.0 s timeout, not a probabilistic reload. The old "torque dips every direction change" reading is
    # retired: at highway speed this is a real, self-clearing event flag, not a permanently-reloaded one.
    # Also confirmed (0x429da-0x429f0, `mov r14,r8` fallthrough): the held value passes through 1,2,3,4
    # before saturating at CEIL=5 -- `>=1` is genuinely more sensitive than `>=5`, not a relabel only.
    # ✅ The latch is PROTECTIVE: a per-tick-gated gain would modulate AT the mode frequency, i.e. a
    # parametric pump -- the exact failure mode V58/V59/V60 chased for three builds.
    # 🛑 NOT private to r24/r26 -- also read by FUN_0003a382, FUN_000352b4, FUN_00035b20, FUN_00036c12.
    # Irrelevant to raising the two arm cals; DECISIVE against ever moving T/HYST/CEIL. FUN_0003a382 uses
    # it as a CONTINUOUS LERP INDEX (not a gate) shaping the live P/I/D lane gp-0x6ad4, and FUN_00036c12's
    # friction-comp lane gp-0x6b26 sums into the SAME aggregator. => lowering T changes FIVE things at
    # once, four uncontrolled, one a shape parameter on a lane already known to be load-bearing (V56).
    # By contrast gp-0x67df is CLEAN (2 hits, both inside FUN_000428d4) and T has 4 readers, all inside
    # the detector. CEIL (0xC64FA) is NOT private -- 3 external readers.
    # 🛑 The whole detector body is gated on FUN_00046ea6(5)==0 (bit 5 of gp-0x18d0|gp-0x18d4). If set,
    # FUN_000428d4 jumps 0x428E2 -> 0x42A76 and NEITHER cell is written -- indistinguishable from "T never
    # crossed" on a bus log. RULED OUT as the cause of the V64 null: raw byte scan of all 47 jarl sites
    # (Ghidra's search finds only 44 -- the documented undercount) shows bit 5 has exactly ONE caller
    # image-wide, the detector itself @0x428DA; the only dynamic indices are cals 0xB9A14-16 = 0,2,6.
    # The mask is DTC-driven (tp-0x72c4, stride 28, u32 at +8) and self-clearing (gp-0x18d4 is rebuilt by
    # plain assignment each active-fault sweep); gp-0x18d0 is OR-only but written only on the rare
    # "8+ simultaneous faults, evict oldest" overflow path.
    # The arm selection below is CORRECT as written and was verified in Ghidra 2026-07-31; a subagent's
    # prose summary claimed the opposite polarity and was wrong.
    assist_state_671a: int = 0
    assist_gate_671d: int = 0      # r24's HIGHER-priority override; live (2 writers: 0x3BD2A, 0x41EC6)
    assist_gate_683c: int = 0      # DEAD -- zero st.b writers image-wide, so the 512 arms are unreachable
    assist_gate_6b5e: int = 0      # LERP output on axis gp-0x6bda, tested only as a boolean.
                                  # ★★ RESOLVED 2026-08-04, and it REVERSES the old reading:
                                  # gp-0x6b5e = ((LERP(gp-0x6bda)*0xC63C2)>>10)*polarity, producer
                                  # FUN_000361c8 @0x36256/0x36264 (shadow pair gp-0x4cd8). Trapezoid
                                  # @0xC66CC: X=[-384,-128,128,294,384] Y=[0,4762,4762,717,0],
                                  # 0xC63C2 = 1024 (Q10 unity). r26 == 0 IFF gp-0x6b5e != 0, so r26
                                  # is killed only where the LERP is ZERO -- i.e. |gp-0x6bda| >= 384.
                                  # AND gp-0x6bda is a MARGIN TO A PEAK-HOLD ENVELOPE of driver
                                  # assist torque gp-0x6bf0 (FUN_00036022 @0x36068-0x3608C; envelope
                                  # gp-0x6bd8/gp-0x6bd6 from FUN_00035d38, half-width never < 9390;
                                  # 0xC614A = +-10048, margin cal 0xC614C = 128). HANDS-OFF the
                                  # margin is ~9262 = 24x the threshold.
                                  # => THE GATE DOES NOT KILL r26 IN ORDINARY DRIVING, and least of
                                  # all hands-off at creep. The kill window is a ~512-count sliver at
                                  # the DRIVER-OVERRIDE end (cf. 0xC6156 = 9216).
    assist_slope_q10: Optional[int] = None  # gp-0x69a4; producer RESOLVED @0x355c6 (FUN_000352b4) --
                                  # the local SLOPE of a 10-segment curve, gated |gp-0x4f60| <= 25600.
                                  # 🛑 ~ZERO ON THIS CALIBRATION: FUN_00039702 shows the RAM array
                                  # gp-0x641E..gp-0x6444 is an ADJUSTMENT added in Q10 float to a fixed
                                  # cal base at tp+0x7564, and 0xC6564-0xC658C byte-reads as 40 bytes of
                                  # EXACT ZERO with no writer found for the RAM side (10 of 18 cells
                                  # checked). => r26 contributes ~nothing; r24 carries the lane.
                                  # [BELIEF, not proof: live RAM is unreadable, 8 cells unchecked.]
    previous_assist_slope_q10: int = 0
    assist_slope_history_valid: bool = False
    assist_inline_a: int = 0       # r26 in FUN_0003aa2c, Sensor-B torque-rate x gp-0x69a4
    assist_inline_b_raw: int = 0   # r24 before the optional V39 guard
    assist_inline_b: int = 0       # r24 in FUN_0003aa2c, direct Sensor-B torque-rate lane
    direct_rate_guard_fired: bool = False
    aggregator_reduced_mode: bool = False  # gp-0x67ac==1; dormant with A160 source-mode table
    non_lkas_sum: int = 0
    demand_sum: int = 0           # gp-0x6b94 (0xFEDF146C) aggregator output, lockstep gp-0x4ce0

    # ---- Runtime governor chain ----
    runtime_governor_value: int = 4762  # gp-0x4f64
    governed_demand: int = 0             # gp-0x6ace, after FUN_0004503c clamp/Q15/slew (via FUN_00049a90);
                                         # its ONLY readers are FUN_000456a4/FUN_00045a20, both
                                         # hard-shutdown monitors -- NOT a forward path to the motor.
    governor_initialized: bool = False    # gp-0x1388
    governor_held: int = 0                # gp-0x138a
    post_governor_compensation: int = 0  # gp-0x6ad0
    post_governor_command: int = 0       # gp-0x6acc, shaper/integrator input

    # ---- diagnostics ----
    dtc_0x49_set: bool = False    # DTC 0x49 latched (dash lights + openpilot steerFaultPermanent)
    dtc_0xF00049_set: bool = False  # hard-DTC lockstep (int/float twin divergence) -> motor off


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _div_trunc_zero(numerator: int, denominator: int) -> int:
    """Integer division with V850 `divq` signed truncation toward zero."""
    if denominator == 0:
        raise ZeroDivisionError("firmware model divisor must be nonzero")
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def _range_gate(value: int, limit: int) -> int:
    """Aggregator idiom: an out-of-window lane contributes zero; it is not endpoint-clipped."""
    return value if -limit <= value <= limit else 0


def _signed16(value: int) -> int:
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


# =====================================================================================================
# SECTION 2 -- CAN INTAKE + LKAS SETPOINT
# =====================================================================================================

def can_rx_stage_steer_torque(frame: CanSteeringControl) -> Optional[int]:
    """
    Stage the incoming CAN 0xE4 STEER_TORQUE into the routed LKAS buffer. [VERIFIED] CAN mailbox RX ISR
    (mailbox 0x36) -> FUN_0001cf30/FUN_0001ce68/FUN_0001ddd0 -> FUN_00021724, landing in routed buffer
    0xFEDF6BD8 (int16 BE); exact ISR entry/rate not located. [CONFIRMED] the 0xE4 payload itself.

    The 5 intake gates modelled here (checksum/counter/status/timeout) are comms-validity only -- they
    cannot cut LKAS on a torque/rate value. The separate low-speed steer lockout (cal 0xC62EA, two-sided
    window on voted vehicle speed gp-0x6a5e) is modelled in steer_status_low_speed_lockout() below; it
    IS authority-bearing (gates STEER_CONTROL_ACTIVE + the authority ramp), was flashed as V53 (LO bound
    -> 0), and was confirmed on-car (route 1a: STEER_STATUS=3 never fires; 226 low-speed engaged frames
    appear that are empty on V38). Vehicle speed also gates the G1 governor's slew-limiter skip below
    ~10 km/h, so "no vehicle-speed input in the command path" is a retired claim, not current.
    """
    if not (frame.checksum_ok and frame.counter_ok and frame.fresh):
        return None  # invalid frame -> downstream will use the fault sentinel
    return frame.steer_torque  # signed16, big-endian, as decoded from bytes[0:1]


COUNTS_PER_KMH = 64.0625   # FUN_000522fe implements x41>>6 on a 0.01 km/h raw value (NOT a clean 64)


def steer_status_low_speed_lockout(sensors: "SensorInputs", cal: Calibration) -> bool:
    """True when the speed window FAILS, i.e. firmware writes STEER_STATUS=3 (LOW_SPEED_LOCKOUT).
    [VERIFIED] FUN_00028ea6 (m_steer_torque_arbitration, the live ~1kHz arbitration; FUN_0002a30e is a
    dead copy): compares voted vehicle speed gp-0x6a5e against cal 0xC62EA (LO, tp+0x72ea) and 0xC62E8
    (HI, tp+0x72e8), each with exactly one reader image-wide; bypassed at true standstill via gp-0x68b3
    (set only when gp-0x6a62==0). Failing the window is the ONLY writer of STEER_STATUS=3, which gates
    STEER_CONTROL_ACTIVE and the authority ramp -- authority-bearing, not report-only. [CONFIRMED]
    on-car: ST=3 is 100% below 2 mph and 0% above 4 mph (98,053 frames). Models the SPEED CONJUNCT ONLY:
    the real bVar2 is a 5-way AND, so False here means "the speed window passed", not "STEER_STATUS <=
    2" (e.g. gp-0x69aa==0x8000 "derate" shares the same ST=3 write).
    """
    counts = int(sensors.vehicle_speed * COUNTS_PER_KMH)
    if counts == 0:
        # gp-0x68b3 bypass: FUN_0004d0d0 sets it only when the voted speed cell is EXACTLY 0.
        return False
    return not (cal.speed_window_lo <= counts <= cal.speed_window_hi)


def lkas_process_steer_cmd(steer_torque: Optional[int], st: EpsState, cal: Calibration) -> int:
    """
    Convert the raw CAN STEER_TORQUE into the internal LKAS setpoint. [VERIFIED] FUN_00052676
    (s_lkas_process_steer_cmd): `x*-4` then clamp(+/-0x4000), writing gp-0x69ae (0xFEDF1652); a
    checksum/counter/timeout fault instead writes sentinel 0x7FFF. The -4 flips openpilot's sign
    convention to the EPS motor convention with a Q2 up-shift; full-scale input (4096) lands exactly
    on the -0x4000 wall.
    """
    if steer_torque is None:
        st.lkas_setpoint = cal.setpoint_fault_sentinel  # 0x7FFF, an out-of-range flag consumed later
        return st.lkas_setpoint
    scaled = steer_torque * cal.setpoint_scale                    # * -4
    st.lkas_setpoint = _clamp(scaled, -cal.setpoint_clamp, cal.setpoint_clamp)  # +/-0x4000
    return st.lkas_setpoint


# =====================================================================================================
# SECTION 3 -- DRIVER STEERING-TORQUE SENSOR + VOTER  (the physical steering-wheel torque path)
# =====================================================================================================

def read_column_torque_voter(sensors: SensorInputs, st: EpsState, cal: Calibration) -> None:
    """
    Turn the redundant torque-sensor coil ADC channels into the voted column-torque signals and derive
    the angular-rate magnitude the decider/debounce gates compare against. [VERIFIED] 3 channels from
    TAUA0 capture regs -> FUN_00061ca0/FUN_0006195e (gp-0x4e8c/8a/88 + refs gp-0x4e94/92/90);
    plausibility FUN_00062948; voter FUN_00041eec -> MAX gp-0x6a62 (0xFFFF sentinel on quorum loss) /
    AVG gp-0x6a5e; rate FUN_0003f776 -> gp-0x6a56 then gp-0x6a60 = |gp-0x6a56|. [CONFIRMED] the
    3-channel readings are the physical wheel-torque source. KEY FACT: gp-0x6a60 is a RATE magnitude,
    NOT a torque, and its rising edge is unfiltered (only a fall-limiter), so no debounce exists in the
    rising voter chain.
    🛑 2026-07-30: gp-0x6a56 -- what the EPS transmits as STEER_ANGLE_RATE on 0x14A[2:4]/0x18F[2:4] --
    is NOT independently sensed. FUN_0003f776 (its sole producer, 4 st.h, all inside it) computes
    gp-0x6a56 = clamp(polarity(gp-0x6752) * ((gp-0x6abe * 48 * cal(tp+0x713a)) >> 15), +-12000),
    i.e. a fixed Q15 scale of the MOTOR/resolver electrical rate. The +-12000 is a MAGNITUDE clamp
    recomputed fresh each tick, not a rate/slew limit, and gp-0x6a60 just mirrors its magnitude
    (the min-vs-65535 at 0x3f7f6 never binds). CONSEQUENCE: STEER_ANGLE_RATE is opendbc-named but is
    NOT an independent angle sensor, so "996x on rate vs 877x on torque" is two EPS-internal
    derivations, not independent corroboration -- and because gp-0x6bbe's `baseline` is ALSO
    gp-0x6abe-derived, `rate_error = baseline - angle_rate` may partially cancel. That is why the
    lane's damping sign is UNRESOLVED and why V58 measures its phase on-car instead.
    """
    coils = sensors.column_torque_coils
    valid = sum(1 for c in coils if c is not None)
    if valid < 3:  # cal 0xC6501 = 3-of-4 quorum
        st.col_torque_max = 0xFFFF  # invalid-sensor sentinel (a distinct decider path, kept in V37)
        st.speed_voted = 0xFFFF
    else:
        st.col_torque_max = max(abs(c) for c in coils)
        st.speed_voted = sum(abs(c) for c in coils) // valid
    st.col_rate_mag = min(abs(int(sensors.steering_angle_rate)), 12000)  # rate magnitude, clamp +/-12000

    # Sensor-B is a signed, independently processed TAS torque channel (gp-0x4f60). During synthetic
    # runs only, fall back to the signed mean of the available coils; RAM/log replay should provide it.
    valid_coils = [int(c) for c in coils if c is not None]
    st.col_torque_sensor_b = (int(sensors.column_torque_sensor_b)
                              if sensors.column_torque_sensor_b is not None
                              else (_div_trunc_zero(sum(valid_coils), len(valid_coils)) if valid_coils else 0))

    # FUN_0007f3f8 calls FUN_0007e74a, which keeps a ring and writes lockstep gp-0x4f62/gp-0x4488:
    # 2*(current-delayed)/wrapped_sample_delta, with delay cal tp+0x7c42=4. It runs on phase mask 0xD30
    # while the aggregator consumes on 0xC30. The actual RAM value is the preferred replay input. The
    # local fallback assumes one producer sample per model tick and therefore dt=4.
    if sensors.column_torque_rate is not None:
        st.col_torque_rate = int(sensors.column_torque_rate)
    else:
        st.col_torque_history.append(st.col_torque_sensor_b)
        if len(st.col_torque_history) > 5:
            st.col_torque_history.pop(0)
        st.col_torque_rate = (_div_trunc_zero(2 * (st.col_torque_history[-1] - st.col_torque_history[0]), 4)
                              if len(st.col_torque_history) == 5 else 0)
    st.motor_rate_raw = int(sensors.motor_rate_raw)


# -----------------------------------------------------------------------------------------------------
# SECTION 3B -- BASE DRIVER ASSIST (normal power steering)
# -----------------------------------------------------------------------------------------------------
# Assist is not one term: the demand aggregator (FUN_0003aa2c) sums the boost curve, five sibling lanes,
# two inline Sensor-B torque-rate lanes, and one filtered Sensor-B term:
#     FUN_00034a72 -> gp-0x6bbe   the boost curve proper (the "assist" everyone means)
#     FUN_00034350 -> gp-0x6bd0   5 multiplied gain factors, sign forced opposite gp-0x6abe [damping]
# 🛑🛑 ALL FIVE DAMPING FACTORS ARE MODE-TABLE SELECTED (2026-08-05). FUN_00034350 (sole caller
# FUN_00022ca0) picks B/C/D/E AND the ceiling through pointer arrays indexed by mode*4,
# mode = *(byte)(gp+0x63fd), 13 variants:
#     FactorB 0xC9CCC[m]  FactorC 0xC9E9C[m]  FactorD 0xC9DB4[m]  FactorE 0xC9F84[m]  ceiling 0xC77A0[m]
# ★ RECORD LAYOUT (byte-verified on modes 24/26, 2026-08-07): u16 n@+0, i16 X[]@+2 (🛑 NOT +4 -- that
# misread yields [X1,X2,X3,Y0]), i16 Y[] Q10 @+2+2n, u16 terminator 0x0000 @+2+4n. Below X[0] clamps to
# Y[0] (STRICT <=, so idx==X[0] clamps too); above X[n-1] clamps to Y[n-1]; else truncating LERP.
# 🛑🛑 n IS NEVER READ BY THE EVALUATOR: each factor's `while(X[i]<=idx) i++` loop is real, but its
# length is PINNED by hardcoded immediates -- FactorB/C/E n=4, FactorD n=5, ceiling n=2, confirmed
# against every shipped record (friction n=3, same mechanism). => adding a breakpoint is a CODE edit;
# relocating a same-size record is cal-only (one u32 pointer-array write).
# The product carries NO signal magnitude -- it is five Q10 GAINS; rate enters via FactorE's LERP index
# and speed via FactorC's, and the SIGN comes from gp-0x6abe.
# ✅ RESOLVED 2026-08-07 -- gp-0x6abe IS THE SIGNED TWIN OF gp-0x6ac0. Both are filtered from gp-0x4f50
# in FUN_00041464 and stored at 0x41b56: gp-0x6abe = (short)(uVar16 >> 10) SIGNED, gp-0x6ac0 =
# |uVar16| >> 10 RECTIFIED. So the damper's index and its sign are the SAME motor-rate signal, and
# sign(gp-0x6bd0) = -sign(motor rate) exactly (applied at 0x3469E-0x346A2, `cmp r0,r11 / ble /
# subr r0,r8`). [EVIDENCE] ⇒ gp-0x6bd0 is -sign(rate) x M(|rate|): a viscous damper when M is
# proportional to |rate|, a COULOMB RELAY when M is flat. seed = gp-0x698a (the "FactorA" long sought
# as a separate table) is MIN-clamped to <=1024 -- corrected 2026-08-07, it is NOT "pinned"; an
# unclamped seed below 1024 passes through, matching the "MIN-clamped seed" phrase already used in
# assist_shaping_lanes' docstring, which this line previously contradicted.
# ★★★★★ THE LIVE MODE IS SETTLED (2026-08-05, V73's probe, 104,061 frames): the car is row 11 'TVCA4' and
# runs mode 24 DISENGAGED / 26 ENGAGED -- the mode TOGGLES with engagement (gp-0x67f6 picks e012 when
# settled-disengaged, e014 when settled-engaged). Forced by the MANUAL arm: the 4-bit probe field drops
# bit 4, so observed 8 means true in {8,24}, and raw 8 appears in NO row of 0xCD000 => manual = 24; only
# row 11 holds 24, and all four columns come from one row => engaged = 26. The engaged reading of 10
# alone would NOT have closed it (rows 2/3/6/7 all carry raw 10).
# => V72 edited modes 10/11 on the ASSUMPTION that 39990-TVA-A160 -> row 2 'TVAA1'. That was wrong, and
# V44, V47, V72's Levers B/C and BOTH of V73's levers were INERT BY TABLE SELECTION -- uninterpretable,
# not falsified. RULE 7 (docs/BUILD-LINEAGE.md): a lever is mode-proof, or it is a bet.
# ★ Engaged (e014/e015) and disengaged (e012/e013) column sets are DISJOINT across all 16 rows, so dosing
# the engaged columns delivers whatever row is live while leaving manual byte-stock.
#
# 🛑🛑 THERE ARE TWO DEAD ZONES, ON DIFFERENT AXES, AND TOGETHER THEY ARE WHY CREEP HAS NEVER HAD DAMPING:
#     FactorC 0xC9E9C[m]  axis = SPEED gp-0x6a5e   X[0] = 2240 = 35.0 km/h on the live modes   Y[0] = 0
#     FactorE 0xC9F84[m]  axis = RATE  gp-0x6ac0   X[0] = 60                                   Y[0] = 0
# A LERP clamps flat to Y[0] below X[0], and zero x anything = 0, so the speed factor alone forces the
# damper to exactly zero at creep. ⚠ The speed onset is MODE-DEPENDENT: X[0] = 1280 (20 km/h) on modes
# 0-3, 1920 (30 km/h) on 4/5, 2240 (35 km/h) on 10-15 and 22-27. Never quote "35 km/h" without the mode.
# 🛑 CONSEQUENCE FOR SIZING: because both Y[0] are zero, SCALING a record by any k is structurally vacuous
# at creep (k x 0 = 0); only lifting Y[0] delivers, and Y[0] := Y[1] is the largest monotone lift of Y[0]
# alone. Raising FactorC costs NO rate-proportionality (it is speed-indexed); FactorE's shape IS the
# rate-proportionality.
# ★★★★ MEASURED OPERATING POINT: gp-0x6ac0 in-burst = 99 counts [94, 113] -- INSIDE FactorE's dead zone,
# on its first rising segment. Priced there against a requirement of ~43 [30,60]: stock 0; FactorC
# Y[0]:=Y[2] alone 6; FactorC Y[0]:=Y[3] alone 14; BOTH dead zones opened ~50. => NO FactorC rung alone
# reaches it. The lever is FactorC Y[0]:=Y[2] + FactorE X[0]: 60 -> 12 + FactorE Y[1]:=Y[2], on the 13
# ENGAGED modes. ★ It OPENS THE RATE DEAD ZONE rather than raising a gain, so the damper becomes genuinely
# rate-proportional in the symptom's range -- the OPPOSITE of V72's flatten-to-relay error, not a larger
# version of it. 🛑 Always price a damper rung at the symptom's OWN measured rate: 330 vs 99 inverted the
# recommendation here.
# 🛑 X[0] IS 12, NOT 6, AND THE REASONING MUST SURVIVE (a bare "12" invites re-optimising it down):
#   (1) a firmware review flagged X0 < 30 with Y1 > 300 as the zone it would not fly without telemetry;
#       12 is the TOP of its own 6-12 band and halves that concern for a ~6% dose cost (53 -> ~50).
#   (2) the rate conversion is rigid-body and biased LOW through a resonance -- measured at the COLUMN,
#       indexed at the MOTOR, and 18-22 Hz is TORSIONAL, so the true dose is HIGHER than computed.
#       Erring low is the correct side of that error.
# ⚠ GATE 2 NOTE: V72 set mode 10's FactorE Y[0..2] -> 927, i.e. FLAT across the whole rate axis, turning a
# rate-proportional damper into a near-BANG-BANG RELAY (magnitude ~constant, sign = -sgn(gp-0x6abe)). A
# relay in a loop at a lightly-damped resonance is a limit-cycle GENERATOR. Had it been delivered it could
# have made the ratchet WORSE. V73 instead sets Y[0] := that record's own Y[1], preserving proportionality.
# ⚠ Both this lane and the friction lane below are gated by the SAME andi 0x830 state mask on gp-0x67fa
# (damper via FUN_00022ca0; friction via FUN_0002214a @0x228cc) => if the live state is outside {4,5,11},
# NEITHER delivers. 0x830 is a SUBSET of 0xc30, so no state runs the aggregator without the damper.
# ✅ SETTLED ON-CAR (route 5d, 101,118 frames): gp-0x67fa reads 5 on 101,117 and 4 on 1 (the last frame,
# in PARK), and FUN_0002214a's guard is literally `uVar2 = 1 << (gp-0x67fa & 0xf)` then `uVar2 & MASK`, so
# state 5 => 0x20 clears 0x830 / 0x930 / 0xc30 / 0xd30 / 0xd38 / 0xdfa / 0x83a / 0x820 -- the whole chain
# ran on every frame, and gp-0x67fa == 4 is dead (third replication; 0x454FE never executes).
# 🛑 TWO MORE GATES, INSIDE FactorC/FactorE THEMSELVES, byte+decompile confirmed 2026-08-07:
#   FactorC: if (gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1) -> FC forced to UNITY (0x400), bypassing the
#     LERP and its speed dead zone entirely. [OPEN] gp-0x67f4 != 1 (voter implausible) forcing UNITY
#     rather than a fail-safe zero has never been probed on this car.
#   FactorE: if !((gp-0x6ac0 < 0x32c9) && (gp-0x6abe + 13000 <= 0x6590)) -> the WHOLE damper term is 0,
#     not just FactorE -- a second validity/kickback window layered on top of the rate dead zone above.
#
# 🛑🛑 THE OUTPUT CEILING IS EFFECTIVELY A CONSTANT 512, NOT A DYNAMIC 512..1024 (2026-08-06).
# ceiling = LERP(gp-0x6ac2, 0xC77A0[mode*4]), and all 26 modes carry an identical X=[300,800] Y=[512,1024]
# (byte-verified on modes 24/26 too, 2026-08-07). gp-0x6ac2 is NOT a rate: FUN_00041464 sets it to
# |motor rate| >> 10 only when sign(motor rate) differs from sign(gp-0x6b98), and to 0 otherwise -- a
# SIGN-GATED BACK-DRIVE (kickback) DETECTOR. In ordinary same-sign driving the index is 0, the LERP
# clamps flat to Y[0], and the ceiling sits on its 512 floor.
# => SIZE EVERY DAMPER LEVER AGAINST 512. The build-time rule (FactorC x FactorE[3]) >> 10 <= 512 is the
# real constraint, not a conservative one.
# ✅ RESOLVED 2026-08-07 (was: "ld.h or ld.hu, floors to -1 or rails to 65535, one bit, opposite
# answers"). There is a THIRD path AHEAD of the LERP: `if gp-0x6ac2 >= 0x32c9: uVar10 = *(u16*)0xC6158`
# (=512, byte-verified) BEFORE the LERP runs. The 0x41852 validity bypass's 0xFFFF sentinel is >= 0x32c9
# under either a signed or unsigned read, so it lands on this SAFE LOW override, not on the LERP's own
# Y[n-1]=1024 -- the ld.h/ld.hu question is moot either way.
# gp-0x6bd0 = clamp(product, -uVar10, +uVar10), symmetric, and is itself int/int lockstep-shadowed at
# gp-0x4cf2 (`if cur == shadow: store both; else FUN_0006b9fa(gp-0x4cf2)`) -- distinct from the ceiling
# LERP's own int/float lockstep at cal 0xC6554/58/5C/60 noted at assist_shaping_lanes below.
#
# ★★★★ FIRST EMPIRICAL ANCHOR ON gp-0x6bd0 (V74, route 5d, 101,118 frames -- the kit's first positive
# control on the damper). bit7 = (gp-0x6bd0 != 0) fired on 23,603 frames = 23.342%: ENGAGED 39.927%,
# ENGAGED CREEP <=4 m/s 67.443% vs MANUAL CREEP 0.292% (230.7x). V72's probe on the same cell read
# 0/87,940. All 943 manual bit7 frames lie within 5 s of a disengagement and 0 of 40,398 beyond it, which
# confirms the engaged-column-only design AND re-measures the 2.08 s mode fall lag on a different cell.
# Delivered dose at the ratchet's own 99 counts = exactly 50 (design target); stock 0 at every creep
# speed; 0 frames reached the ceiling. 🛑 The ~43 requirement is TORSION-BAR counts and this is AGGREGATOR
# counts -- still unconverted. ⚠ A (speed, column-rate) model reproduces bit7 on 91.240% of frames with a
# one-way residual (under-predicts), so every modelled dose is a LOWER BOUND.
#
# 🛑🛑🛑 AND V74 HARD-FAULTED (2026-08-06): a latched total loss of power steering, LKAS DISENGAGED, over
# a bump -- and these edits were NOT IN FORCE when it did. [EVIDENCE, verified two ways] disengaged is
# MODE 24, and all five mode-24 damper records are BYTE-IDENTICAL TO STOCK on V74 and V75 (FactorC
# 0xD67E4, FactorE 0xD6820, FactorB 0xD6760, FactorD 0xD67A4, ceiling 0xD60B4), and 0 of the 54 non-CRC
# V73->V74 diff runs lands inside a mode-24 record. ⇒ a MANUAL fault can only come from the MODE-PROOF
# residue, not from this lane's dose, and on V74 that residue included 0xC63A0 = 2048 (end of section).
# 🛑 k* in (0.580, 1.580] is VOID: it was fitted from "V74 flew clean" + "V75 faulted", and V74 did not
# fly clean. No build in the current lineage has demonstrated safety. V75 then hard-faulted too.
# ★★★★ DOSE-RESPONSE over V72 (k=0) / V73 (k=0) / V74 (k=0.5799) / V75 (k=1.5798): the 18-22 Hz slope is
# -0.599 [-0.856, -0.348] = -5.20 dB per unit k, CI EXCLUDES ZERO, while the 6-9 Hz slope is
# -0.089 [-0.350, +0.163], CI INCLUDES ZERO -- FLAT.
# 🛑🛑 THE 18-22 Hz LEG IS RETRACTED 2026-08-07 -- see "GRIND #1 IS INERT TO THE DAMPER DOSE" below.
# On one instrument across k = 0.58 -> 4.16 every grind-#1 point sits inside its own split-half null.
# The 6-9 Hz leg SURVIVES and is EXTENDED: it does move, but only at V80's k = 4.16.
# ⇒ THE DAMPER FIXES THE GRIND AND CANNOT FIX THE MICRO-RATCHET: the ratchet needs k = 4.2-13.5 against
# the 1.5798 that faulted, so stop sizing this lane for it.
#
# ★ DOSE AXIS, for consistency with the build scripts: dose(v,r) = min((C(v)*E(r))>>10, ceiling), with
# FactorB and FactorD byte-read flat 1024 (inert unity) in BOTH modes 24 and 26 on this car (confirmed
# 2026-08-07), so it collapses to just C x E, ceiling-clamped. Reference rate R_OP = 99 counts =
# 21.0 deg/s (in-burst p50 for grind #1). SPEED_CTS_PER_KMH = 64.0625 (== COUNTS_PER_KMH above);
# RATE_CTS_PER_DEGS = 4.7121 (== gp-0x6ac0's scale, cited above). On the ramp segment, incremental gain
# k = ((C_Y0 * E_Y1) >> 10) / (E_X1 - E_X0), and dose(r) = k * (r - E_X0) exactly (r on [E_X0, E_X1]).
# Flown creep doses at r=99, all from the build scripts, not re-derived here: stock/V38 = 0 ·
# V74 (C_Y0=429, E_X0=12, E_X1=400, E_Y1=539) = 50, k=0.5799 · V75 (E_X0 carried at 12, EX1 dropped) =
# 137, k=1.5798 (this is the pair the slope fit above uses) · V76 (mode 26 only, C_Y0=566, E_X0=0
# (operator-authorised override of V74's own E_X0_MIN_SAFE=12 guard -- E_Y0 stays 0, so no torque at
# zero rate), E_X1=119, E_Y1=300) = 137, k=1.3866 -- same dose as V75 off a shallower ramp starting at
# zero. ✅ FLOWN 2026-08-07 (route 65, 636 s / 63,477 frames, clean) and IS in the slope fit above --
# it sits BETWEEN V74 and V75, so the monotone model made a falsifiable POINT prediction: grind #1
# observed 1.577 vs predicted 1.613 (held to 0.19 dB) => DOSE-LIMITED, slope -0.614 [-0.810, -0.416];
# ratchet observed 3.877 vs predicted 3.906 => DOSE-INDEPENDENT, slope -0.094 [-0.291, +0.098].
#
# ═══ V80 FLEW 2026-08-07 AND THE DAMPER SURFACE IS A RELAY. THE SINGLE MOST IMPORTANT DAMPER RESULT. ═══
# Route 66 (75604b0a432fdc89|00000066), 901.71 s / 89,997 frames, engaged 33.62%. Operator's verdict:
# THE WORST GRINDING THE CAR HAS EVER PRODUCED -- ~90% of engaged time, both low and high speed, with
# noticeable vehicle instability. 🛑 IT DID NOT FAULT (0x1AB DTC-active 0 transitions, 0.000% duty,
# 0 sentinels) ⇒ a STABILITY failure, not a fault-class failure. [EVIDENCE]
# k (small-signal loop gain, = ((C_Y0*E_Y1)>>10)/(E_X1-E_X0)):  V74 0.5799 · V76 1.3866 · V75 1.5798 ·
# V80 4.1597 (2.63x V75; V81 == V75's 1.5798 exactly, it does not touch the surface).
# Damper dose vs motor rate at 5 km/h, mode 26, from the shipped plain images (identical at EVERY speed
# on V80 -- its FactorC is flat):
#   rate ct     20   40   99  119  150  255  530 1000 1941 4000     (4.7121 ct per deg/s)
#   V75         12   44  137  169  218  297  297  297  297  512
#   V80         82  166  412  495  495  495  496  498  501  512
# ⇒ V80 emits a CONSTANT 495 counts -- 3.4% variation over a 34x rate range -- at 97% of the 512 ceiling,
#   above only ~25 deg/s. That is -sign(rate) x const: a Coulomb RELAY, not a viscous damper.
# 🛑🛑 WHY EVERY BUILD-TIME GATE WAS BLIND: they all test `product > ceiling`. V80's supremum is
#   (566*927)>>10 = 512 = the ceiling EXACTLY, so it clips 0.00% and passes. The relay was not removed by
#   the flat-FactorC edit, it was MOVED from the ceiling clamp to FactorE's OWN KNEE, 17 counts under the
#   rail (slope drops ~1200x at X[1]=119). "DOES NOT CLIP" AND "IS NOT A RELAY" ARE DIFFERENT
#   STATEMENTS, AND ONLY THE FIRST WAS EVER CHECKED. [EVIDENCE]
# Describing function N(R) of force = -sign(rate)*M(|rate|) (constant N = viscous = stabilising; N rising
# as amplitude falls = relay = limit-cycle generator), numerically integrated:
#   R ct         25     50     99    150    250    500   1000
#   V75 creep  0.580  1.065  1.319  1.410  1.317  0.734  0.375
#   V80 creep  4.007  4.087  4.127  3.698  2.421  1.250  0.632
#   relay-ness N(50)/N(500):  V75 1.45x (creep) / 1.43x (60 km/h);  V80 3.27x at BOTH.
# ★ MEASURED, by both builds' own cave probes -- the cleanest statement of the root cause:
#   |gp-0x6bd0| >= 448 counts, engaged:  V75 (route 5e, 28,317 pre-fault frames) 0.000%, never above 128
#   counts at all over 40 km/h;  V80 (route 66) 19.4% overall, 32.7% above 15 m/s, 71% through the worst
#   29 s event. V75's level census L0 56.8 / L1 25.3 / L2 9.3 / L3 8.6 / L4 0.000% ⇒ V75's damper never
#   entered its saturated regime; V80's LIVES there. [EVIDENCE]
# ★ WHAT V80 DID ON THE ROAD: a broadband HF FLOOR LIFT, not a new peak -- median engaged periodogram
#   V80-V76 is ~0 dB through 22 Hz and +8..+11 dB from 34 Hz up; cell-stratified 30-49 Hz 2.09x
#   [1.46, 2.70] with a pre-declared 32-38 Hz negative control failing identically (2.035). IMU vertical
#   20-49 Hz 1.07 [0.92, 1.33] ⇒ not a rougher road. FFT-free confirmation: engaged windows containing a
#   sample-to-sample reversal of |step| > 800 counts -- V75 0.0% · V74 0.5% · V76 0.6% · V80 23.3% --
#   exactly the near-Nyquist chatter a bang-bang relay injects.
# ★ AND A SUSTAINED ~27.4 Hz LIMIT CYCLE NO OTHER BUILD PRODUCES: 26-31 Hz envelope > 1000 counts in
#   32/215 engaged windows (V74 0/413, V76 0/328, V75 0/133); worst event ~30 s unbroken at 99-104 km/h,
#   27.56 Hz at x92 over the in-band median (manual x3.1 at the same speed), bar 6,830 counts p-p,
#   Q ~ 140, crest 1.838 (near-sinusoidal), damper >= 448 duty 71%, no fault and no lockout throughout.
#   NOT wheel order 2 (measured df/dv = -0.131 [-0.231, -0.016] Hz per m/s where order 2 needs +0.961);
#   frequency pinned across a 20x speed range while amplitude explodes with speed. ⚠ It is the kit's
#   own ~28 Hz line AMPLIFIED (~2.7x, f0 down 1-2 Hz), not a new mode. ⚠ fs ~ 100 Hz, so 27.34 Hz aliases
#   with 72.66/127.34 -- identical on all four routes, so it cannot affect the contrast.
# 🛑 MODELLING NOTE: k is a FREQUENCY-INDEPENDENT scalar on the whole damper path, so it is the loop gain
#   at every frequency -- no plant model is needed to compare two builds that differ only in k, and a
#   phase argument is only needed when a filter, delay or sample point moves.
#
# 🛑🛑 RETRACTION -- GRIND #1 IS INERT TO THE DAMPER DOSE (2026-08-07, four builds on ONE instrument,
# rlog-tools/compare_v75_v76_v80_grind.py, NFFT 256, p99 analytic band envelope, ~10.2 s bootstrap blocks
# nested inside engagement runs; ratio to V76):
#   band            V74 k=0.58        V76 k=1.39   V75 k=1.58        V80 k=4.16
#   18-22 grind #1  1.166 [.98,1.41]  1.000 ref    0.735 [.50,1.22]  0.835 [0.64,1.07]
#   6-9 ratchet     0.818 [.70,1.09]  1.000 ref    0.821 [.66,1.09]  0.418 [0.33,0.61]
#   40-49 grind #2  0.810 [.70,0.97]  1.000 ref    0.961 [.77,1.24]  2.017 [1.32,2.83]
#   30-49 HF floor  0.820 [.73,1.01]  1.000 ref    0.953 [.81,1.26]  2.091 [1.46,2.70]
#   32-38 neg ctrl  0.865 [.76,1.03]  1.000 ref    0.959 [.82,1.22]  2.035 [1.45,2.57]
# Split-half null for 18-22 Hz is [0.63, 1.60]: EVERY grind-#1 point lies inside its own noise floor over
# k = 0.58 -> 4.16. ⇒ V80 did NOT "overshoot an optimum" on grind #1; grind #1 never responded to k at
# all, and V75-vs-V76's apparent difference is a creep-EXPOSURE difference (V76's creep windows carry
# 3.4x V75's steering effort). ★ The operationally useful statement: k in [1.39, 1.58] buys most of the
# ratchet benefit at ZERO HF cost, and something switches on between 1.58 and 4.16 that costs 2x
# broadband HF plus a limit cycle -- WHERE in that gap it switches on is UNMEASURED. The micro-ratchet is
# the one band that improves with k and is best at V80's dose (0.418), consistent with the older
# "the ratchet needs k = 4.2-13.5" estimate.
# ⚠ DO NOT READ V80's CREEP NUMBERS: its engaged creep windows have median sustained effort 173 counts
# and |angle rate| 1.3 deg/s against V74/V76/V75's 685/588/1113 and 33/33/48 -- ZERO matched cells. The
# 10-40 and 40-80 km/h strata are well matched and carry the load; >80 km/h is 1 engagement run on V80
# and never reached on V75.
#     FUN_00036c12 -> gp-0x6b26   speed-LERP x gp-0x6c2c motor-rate-deriv, LINEAR [friction comp]
#     FUN_0003a382 -> gp-0x6ad4   UNFILTERED residual lane (2 passthroughs + a raw derivative)
#     FUN_00036388 -> gp-0x6b62   slow +/-1/tick accumulator w/ hysteresis       [return-to-centre]
#     FUN_000352b4 -> gp-0x6b86 + gp-0x69a4                                      [friction magnitude]
#     inline r24   <- gp-0x4f62 x generated Q10 gain                              [VERIFIED torque-rate]
#     inline r26   <- gp-0x4f62 x avg(gp-0x69a4) x generated Q10 gain             [VERIFIED torque-rate]
#     FUN_00036682 -> filtered Sensor-B term, final slow IIR (6/1024)              [role OPEN]
# Bracketed roles are [INFERRED] from structure; addresses/plumbing are [VERIFIED].
#
# ═══ THE HARD-FAULT MECHANISM: 0xC407E IS THE WHOLE STORY (Ghidra-confirmed 2026-08-07) ═══════════════
# 0xC407E = tp+0x507E (anchor 0xBF000+0x507E -- the off-by-0x1000 trap avoided).
#   MONITOR FUN_00036d74, from the 1 kHz task FUN_0002214a @0x2290A:
#       fVar3 = gp-0x6b26 * 0.0009765625;  if |fVar3| > *(float*)(tp+0x5004) -> FUN_000462e6(0x39bc,..)
#       -> FUN_00016de6(0x1d,..) = DTC 0x1d, LATCHED TOTAL LOSS OF ASSIST.
#   0xC4004 bytes 0000003f = f32 0.5 ⇒ trips at 512 counts. Symmetric, NO debounce. The caller's
#   gp-0x67fa in {4,5,11} gate is the SAME gate that wraps the producer's call ⇒ unconditional
#   RELATIVE TO THE PRODUCER: no path writes gp-0x6b26 without the monitor checking it that cycle.
#   SOLE WRITER of gp-0x6b26: st.h r6,-0x6b26[gp] @0x36CF0 in FUN_00036c12 -- exactly ONE writer
#   image-wide (Ghidra + a raw Python LE scan of disp16, the 6-byte disp23 form, LE32 address literals
#   and movhi/movea pairs: 0 hits on all three alternatives). The stored value is ALREADY clamped to
#   +-0xC407E (clamp arms 0x36CCC-0x36CE2). 0xC407E itself: 0 writers, 3 readers, all ld.h SIGNED, all
#   three INSIDE FUN_00036c12 ⇒ the cell's entire blast radius is one lane's clamp magnitude.
#   MARGINS: stock/V38/V76/V78/V79/V80/V81 = 511 ⇒ +1, UNTRIPPABLE BY CONSTRUCTION (the only value that
#   can reach the cell is already clamped below the trip, whatever the plant or mode does).
#   V73/V74/V75 = 850 ⇒ -338, TRIPPABLE. [EVIDENCE] 🛑 0xC407E is a DO-NOT-RAISE cell.
#   ⚠ The ×1.5 friction table was introduced by V73, NOT V74 (verified across the lineage:
#   stock/V70/V71c/V72 carry Honda's row; V73/V74/V75 carry ×1.5, and V73 also raised 0xC407E).
# 🛑 AND 0xC63A0 IS EXONERATED. The standing directive "do not double 0xC63A0, that is what was causing
#   hard faults" rests on a FALSE PREMISE. 0xC63A0 = tp+0x73A0 has exactly ONE reader (ld.hu @0x381AC),
#   0 writers, 0 disp23 hits; its reader FUN_00038148 writes exactly two cells -- gp-0x374c (its own
#   accumulator) and gp-0x6b70 (its output) -- and NEVER gp-0x6b26, gp-0x6c2c or gp-0x6a5e. gp-0x6c2c's
#   two writers are both inside FUN_00041464 (0x4184E, 0x41AC2). NO FIRMWARE DATA PATH from 0xC63A0 to
#   the faulting monitor. A physical path exists (aggregator -> motor -> plant -> motor rate ->
#   gp-0x6c2c) and is IRRELEVANT, because the clamp acts BEFORE the store. [EVIDENCE]
#   ⇒ Keep the two questions apart: 0xC63A0 DOES move delivered torque (Path 2, above) and CANNOT move
#   what any monitor compares. Raising it is a GATE 2 loop-gain question, not a fault question.
# ★ V75's FAULT WAS NOT THE DAMPER: in the last 5 s the damper was identically ZERO for 4.98 s and
#   reached only level 2 (128-288) 19 ms before the trip. The car was stationary T-5..T-1 s then launched
#   (0 -> 7.6 km/h); column rate reversed sign twice in the final 150 ms (+55, +31, -38 deg/s) and PEAK
#   JERK hit 7,154 deg/s^2 = 4.3x that route's own p99.9 and the route maximum -- exactly what the
#   0xC407E mechanism predicts. [EVIDENCE] ⚠ "0xC407E=850 caused BOTH faults" is still [BELIEF]: the DTC
#   number was never confirmed on-car. EVIDENCE is that the mechanism exists, is single-frame, is
#   mode-proof, and the build history lines up exactly.
#
# ★★★★ gp-0x6bd0 REACHES THE MOTOR TWO WAYS, AND ONLY ONE OF THEM DELIVERS THE DAMPING (2026-08-06).
#   PATH 1 = FUN_0003aa2c, the aggregator above: UNITY weight, ZERO phase -- this is the damping.
#   PATH 2 = FUN_00038148 stage 1: six gated terms, plain ADD, each (x * gate * w) >> 10, with weights
#     tp+0x73a0/a2/a4/a6/a8/aa == 0xC63A0/A2/A4/A6/A8/AA.
#   The gates are ZEROING, not clamping (out of window contributes 0); gp-0x6bd0's is |x| <= 2048.
#   Stage 1's sum is then x polarity x tp+0x7468 (0xC6468 = 2639) >> 10, then a 1 kHz IIR with
#   tp+0x73ac (0xC63AC = 102) => corner 16.70 Hz, then stage 2 -> gp-0x6b70 -> FUN_00037fe6 ->
#   gp-0x6ad6 -> FUN_0003a382 -> gp-0x6ad4 -> the aggregator.
# 🛑🛑 THREE CORRECTIONS TO THIS CHAIN, 2026-08-07 -- the line above USED to end "-> gp-0x6b98":
#   (a) THE AGGREGATOR DOES NOT FEED gp-0x6b98. FUN_0003aa2c's sum output is gp-0x6b94 (+shadow
#       gp-0x4ce0). FUN_00042af8 -- the governor that actually WRITES gp-0x6b98 -- never references
#       gp-0x6b94 in its 1,424-line body; it runs on gp-0x6afe / gp-0x6b08 / gp-0x4f64. [EVIDENCE,
#       full decompile] => there is AT LEAST ONE UNRESOLVED HOP here. gp-0x6b94's 4 unchecked
#       readers: FUN_00036bec, FUN_0004503c, FUN_0004595a, FUN_0007ff08.  [OPEN]
#       🛑 STILL OPEN 2026-08-07, and NARROWED, not closed. New node: gp-0x6ace = the GOVERNOR-CLAMPED
#       form of gp-0x6b94 (written by FUN_0004503c via FUN_00049a90), and its ONLY readers are
#       FUN_000456a4 / FUN_00045a20 -- both HARD-SHUTDOWN MONITORS, not a forward path. Both of
#       FUN_00042af8's documented external inputs are now RULED OUT as the bridge: gp-0x6b08 is
#       self-referential, and gp-0x6afe's sole writer FUN_00042ac6 is fed by FUN_00026c80, an
#       independent Sensor-B lane that runs BEFORE FUN_0003aa2c in the same tick. ⇒ A MISSING LINK,
#       NOT A DISCOVERED INVERSION. Next: a raw LE scan for the 6-byte extended-disp encoding of
#       gp-0x6ace/6b94/6afe/6b08 (a disp16 scan is blind to it), plus a full decompile of
#       FUN_00042af8 -- its "no gp-0x6b94 reference" characterisation was inherited, never re-verified.
#   (b) FUN_0003a382 IS A GAIN-SCHEDULED PID -- the model's original wording was RIGHT.
#       🛑 A subagent claimed this round that "gp-0x6ad6 is a GATE input only, never a DATA input,
#       therefore 0xC63A0 changes delivered damping by 0.00 dB". THAT IS FALSE and was caught by the
#       orchestrator reading the decompile. gp-0x6ad6 appears THREE times in FUN_0003a382:
#         1. the entry gate    if (|gp-0x6ad6| > 0x6400 || |gp-0x4f60| > 0x6400) -> bVar1 = false
#                              (plus gp-0x2588/gp-0x2584 bit 27, and gp-0x6ac0 < 0x32c9);
#                              when bVar1 is false the function returns gp-0x6ad4 = 0 unconditionally.
#         2. uVar19 = (uint)*(short *)(gp - 0x6ad6)     <-- A DATA READ
#         3. its sign bit, for the symmetric-clamp comparison.
#       uVar19 is clamped to +/-(tp+0x7200) into uVar24, then  iVar30 = gp-0x4f60 - uVar24  forms the
#       ERROR, clamped to +/-0x2800 as iVar31, which drives three gain-scheduled lanes that sum into
#       gp-0x6ad4:
#         P: iVar14 = IIR((iVar31 * LERP_uVar20) >> 10 * 0x20, tp+0x7450)      state gp-0x367c
#         I: iVar18 = ((LERP_uVar16 * iVar31) >> 10) + gp-0x3688               state gp-0x3688
#         D: iVar29 = ((iVar31 - gp-0x3684) * LERP_uVar12) >> 10               state gp-0x3684
#       final: gp-0x6ad4 = (((I + D + P) >> 5) * LERP_uVar27) >> 10 * polarity gp-0x6752, then a
#       symmetric magnitude clamp against iVar10 (the feedforward term).
#       => gp-0x6ad6 IS the PID's FEEDBACK term. Path 2 therefore DOES reach gp-0x6ad4 proportionally,
#          and 0xC63A0's effect on delivered command is REAL, not 0.00 dB.
#       LERP index sources: gp-0x6ac0 (P/I/D gains), gp-0x671a, gp-0x6a5e, gp-0x6966, gp-0x6bda.
#   (c) FUN_00037fe6 is EXACTLY UNITY: all 7 term weights tp+0x74ad..0x74b3 read 1 in stock/V74/V77,
#       and the LERP(gp-0x69aa) table 0xC6ABA-0xC6AD8 is a constant 1024/1024 across its domain.
# 🛑 PATH 2 IS A CLOSED LOOP INSIDE THE FIRMWARE -- but it is a SUBTRACTION, not positive feedback.
#   The re-entry closes through gp-0x6bfc alone -> FUN_0003bc20 (0x3bc20 @0x22416, pure identity
#   passthrough) -> gp-0x6bfe -> FUN_00038148 @0x38218 reads iVar5 = gp-0x6bfe - (iVar4 >> 4), where
#   iVar4 is Path 2's OWN forward six-term sum. 0xC63A0 scales BOTH operands of that subtraction.
#   gp-0x6bf6 / gp-0x6c00 / gp-0x6ae0 / gp-0x6ae2 have ZERO readers anywhere -- write-only telemetry.
#   The "B" input branch (gp-0x4f60) is DEAD CODE in every build: its combine coefficients
#   0xC4048 / 0xC404C / 0xC4050 are all 0x0000 in stock, V74, V77 and V77B.
#   The re-entry is NOT a bare z^-1 -- the 2-pole LPF (0xC40D4 = 573/4096) gives:
#       7.79 Hz: -0.87 dB, -36.06 deg   |   21.09 Hz: -4.96 dB, -82.84 deg (incl. 1-tick transport)
#   vs Path 2's own iVar4 IIR: -0.85 dB/-23.63 deg and -4.13 dB/-47.90 deg.
#   => the two operands sit ~12 deg apart at 7.79 Hz but ~35 deg apart at 21 Hz, so they cancel best
#      at low frequency and WORST near the resonance.
# ★ 0xC63A0 ACTS ON PATH 2 ONLY. Path 1 (gp-0x6bd0 unity-weighted straight into FUN_0003aa2c's sum,
#   unweighted and gate-only) is untouched by it. And gp-0x6ad4 is the ONLY thing this whole branch
#   feeds, so when bVar1 is off the entire Path-2 loop is DISCONNECTED from the motor command, not
#   merely attenuated. [OPEN] what sets gp-0x2588/gp-0x2584 bit 27 -- so whether bVar1 was off at
#   V74's fault is NOT established, and given the 2.5 s mode lag it plausibly was still ON.
# ★★ 0xC63A0 IS THE DAMPER'S PATH-2 WEIGHT: stock 1024, V72 set 2048, and NO build reverted it until V77
#   (V77/V77B -> 1024 = -6.02 dB, zero phase, zero cost to Path 1).
#   It is MODE-PROOF -- a bare tp scalar reached without an index -- so it is live in MANUAL as well as
#   ENGAGED (RULE 7), and it has 1 reader (0x381AC), 0 writers, no monitor and no float mirror.
#   It is the odd one out of the six siblings (all stock 1024) and the only one any build ever moved.
#   ⚠ It was only FUNCTIONALLY ARMED AT V74: gp-0x6bd0 was 0 at creep on every build through V73 and
#   2 x 0 = 0, so V74 -- which opened both dead zones -- is the first build whose doubled weight carried
#   signal, and the first to hard-fault. [EVIDENCE: plumbing, byte lineage, arming | BELIEF: causal link]
#
# ★★★ 0xC63A0's BLAST RADIUS IS A STRICT SINGLE-FILE CHAIN (orchestrator, 2026-08-07, reg1==gp-validated
#   byte scan + decompiles). Every hop has exactly ONE functional consumer -- no branch, no telemetry tap:
#     0xC63A0        1 reader  0x381AC (FUN_00038148)
#     FUN_00038148   stores gp-0x6b70 (out) and gp-0x374c (its OWN IIR state; 2 refs, both internal)
#     gp-0x6b70      2 refs = the store + ONE read @0x38006 in FUN_00037fe6
#     FUN_00037fe6   1 store -> gp-0x6ad6      (7-lane sum; its byte weights 0xC64AD..0xC64B3 are ALL 1,
#                    and the tp+0x7aba LERP is flat 1024 => a UNITY-GAIN adder on stock)
#     gp-0x6ad6      2 real refs, BOTH inside FUN_0003a382 (the PID)
#     FUN_0003a382   1 store -> gp-0x6ad4
#     gp-0x6ad4      1 real ref @0x3ACA8 in FUN_0003aa2c (the aggregator)
#   ⚠ 3 raw byte hits discarded as FALSE POSITIVES: 0x767a8 / 0x767b2 land INSIDE 4-byte `mulf.s`
#   instructions (not on an instruction boundary), and 0xBCC52 / 0xBDF92 sit in data with no function.
#   => not even UDS telemetry reads this chain. ⚠ disp16 gp/tp only; extended-disp and ep-relative
#   forms were not swept image-wide (ep was refuted by decompile for FUN_00026c80/42af8/36682 only).
#   🛑 0xC63A0 scales ONE SUMMAND, not a signal: FUN_00038148 sums 6 weighted inputs and FUN_00037fe6
#   sums 7, so the friction / main-command / boost terms on the same wires are untouched by it.
#
# ★★★ FUN_0003a382 IS A REAL THREE-TERM CONTROLLER -- a TORQUE-TRACKING SERVO (decompiled 2026-08-07):
#     feedback = clamp(gp-0x6ad6, +/- tp+0x7200)          # Path 2 arrives HERE, as the FEEDBACK term
#     err      = clamp(gp-0x4f60 - feedback, +/- 0x2800)  # setpoint = driver torsion-bar torque
#     filtP: gp-0x367c += ((K_p*err*32) - gp-0x367c) * (tp+0x7450) >> 10      # first-order lag
#     integ: gp-0x3688 += (K_i*err) >> 10, CLAMPED into a window built from the authority limit (anti-windup)
#     deriv: gp-0x3684 holds err_prev; (err-err_prev)*K_d, clamp +/-0x2800, then low-passed into
#            gp-0x3680 with alpha = tp+0x744a                                # a DIRTY DERIVATIVE
#     out = ((D + I + P) >> 5) * LERP(gp-0x671a) * polarity(gp-0x6752), clamped to +/- authority
#     authority soft-starts via gp-0x3678 (up tp+0x744e / down tp+0x744c), scaled by LERP(gp-0x6966)
#     HARD GATE -> output 0 unless |gp-0x6ad6| <= 0x6400 AND |gp-0x4f60| <= 0x6400 AND gp-0x6ac0 < 0x32c9
#   🛑🛑 ALL THREE LANE GAINS ARE LERPs INDEXED ON gp-0x6ac0 (tables tp+0x7b1e / tp+0x7b0a / tp+0x7ade)
#   -- the SAME rectified motor rate that indexes FactorE. So a FactorE slope change and this PID's own
#   gain schedule move on ONE axis; they are NOT independent. That is the mechanism behind the recorded
#   +41.8..+55.0 deg phase lead at 21 Hz with |D| ~ |P|: at the grind frequency this loop is
#   derivative-dominated, exactly where a rate-scheduled gain on a RECTIFIED index (which sweeps at 2f)
#   interacts with the parametric pump. [GATE 2 -- size any FactorE edit against this, not just dose.]
#   ✅ RESOLVED 2026-08-07 -- THE DAMPER'S NET SIGN IS DISSIPATIVE AT gp-0x6b94, AND PATH 2 IS
#   NON-INVERTING. Was [OPEN] here for four sessions. The Stage-2 subtraction in FUN_00038148 and the
#   PID's own err = setpoint - feedback CANCEL, and the two polarity(gp-0x6752) multiplications cancel
#   whatever that value is: (-P)(+1)(-1)(+P) = P^2 = +1. FUN_00037fe6 is a genuine UNITY adder (all 7
#   weights tp+0x74ad..0x74b3 read 01). So Path 1 (bare, unity) and Path 2 (via the PID) both enter
#   FUN_0003aa2c with unity weight and REINFORCE -- they do not fight. Combined with
#   sign(gp-0x6bd0) = -sign(motor rate) above ⇒ DISSIPATIVE BY CONSTRUCTION at gp-0x6b94. [EVIDENCE]
#   ⚠ This is a sign result at gp-0x6b94, NOT at the motor: the gp-0x6b94 -> motor hop is still missing
#   (below), and the 100 Hz zero-order hold still costs 37.6/75.2 deg of phase at 21 Hz on top.
# -----------------------------------------------------------------------------------------------------

# [VERIFIED, byte-dumped] mode-indexed assist tables, selector = byte at gp+0x63fd (0xFEDFE3FD, NOT the
# LKAS setpoint-limit mode gp-0x674e), range 0..33.
# 🛑 "gp+0x63fd = 10" AND "written only by factory/diagnostic paths (no CAN RX reaches it)" ARE BOTH
#   STALE -- CORRECTED 2026-08-05 and 2026-08-07. THIS CAR IS TVCA4: gp+0x63fd = 24 DISENGAGED /
#   26 ENGAGED, and the selector is REWRITTEN LIVE, every 100 Hz task-5 tick, by FUN_00042746 (sole
#   caller FUN_00022ca0), gated on (1 << (gp-0x67fa & 0xF)) & 0x30 == states {4,5}. It picks one of
#   four HW-ID column tables DAT_0000e012/13/14/15 via FUN_00057f8e(), selected by gp-0x67f6 in {0,1}
#   x gp-0x67e2 in {1,2}.  All five factor evaluators read it: 0x34470 / 0x34502 / 0x34592 / 0x34616
#   / 0x346b4.  [EVIDENCE, decompile + byte reads]
# ★★★★ THE MODE FALLS 26 -> 24 WITH A MULTI-SECOND LAG, AND THAT LAG IS LOAD-BEARING FOR SAFETY.
#   Measured on-car, two routes of V74 (61 and 5d): the engaged-column damper stays live for ~4 s
#   after openpilot drops lateral control, then is HARD ZERO -- 0 of 9,286 and 0 of 39,794 frames
#   beyond the band. V74's hard fault fired at 2.509 s past disengagement, i.e. STILL ON MODE 26.
#   => "disengaged" on the bus does NOT mean "mode 24 is active". Any argument of the form
#      "the operator was in manual, therefore the engaged-column edits were not in force" IS UNSOUND.
#      This exact inference produced a wrong EVIDENCE-marked conclusion on 2026-08-06.
#   [OPEN] the ROM mechanism for the multi-second hold. The only real debounce found is 0xC624E = 40
#   (=40 ms at 1 kHz; ~150 ms with the ramp-settle requirement) -- NOT 2.5 s. The candidate is the
#   gp-0x6733 == -1 "transitioning" sentinel written by FUN_000527da, which blocks the reselect from
#   even arming, but that function's callers resolve to null under both get_function_callers and
#   get_xrefs_to (register-indirect/RTOS dispatch). Closeable only with a live probe on gp+0x63fd
#   across a disengage event -- bytes alone will not get the number.
ASSIST_BOOST_X_RISING = (0, 640, 2560, 5120, 8960, 12800)   # the "rising" family (high top-end assist)
ASSIST_BOOST_X_FALLING = (0, 640, 2560, 5120, 7808, 10240)  # the "falling" family -- what THIS car runs
ASSIST_BOOST_CURVE = {                         # pointer array @0xCA154, 6-point LERP, indices 0..33
    #  idx: (X row,                Y row,                              table addr)
    0:  (ASSIST_BOOST_X_RISING,  (612, 787, 992, 1141, 1211, 1238)),   # 0xCE578 (the sensor-A memory's curve)
    4:  (ASSIST_BOOST_X_FALLING, (529, 632, 645, 546, 438, 438)),      # 0xD0834
    6:  (ASSIST_BOOST_X_RISING,  (607, 718, 943, 1145, 1258, 1284)),   # 0xD086C
    10: (ASSIST_BOOST_X_FALLING, (541, 639, 653, 551, 439, 439)),      # 0xD2834  <<< OUR CAR
    11: (ASSIST_BOOST_X_FALLING, (547, 645, 659, 557, 445, 445)),      # 0xD2850  <<< our failover partner
    28: (ASSIST_BOOST_X_FALLING, (568, 635, 647, 540, 438, 438)),      # 0xD8834 (TWA parts)
    33: (ASSIST_BOOST_X_FALLING, (526, 629, 646, 436, 351, 351)),      # 0xD986C (lightest assist in image)
}   # (representative subset; indices 1-3,5,7-9,12-27,29-32 are duplicates/near-duplicates of the above)

# [CONFIRMED] SPORT MODE is NOT implemented by this ECU: no writer of gp+0x63fd reads a CAN RX buffer.
# 🛑🛑 CORRECTED 2026-08-05 (full enumeration, disp16 + disp23 + UDS-indirect, cross-validated by
# independent Python byte scan against search_instructions -- both agree exactly): 3 REAL runtime/boot
# writers (not "sensor-fault failover", ENGAGEMENT-linked, matches V73's {8,10} probe):
#   FUN_00042692 (1 write) -- BOOT-TIME populator, gated `gp-0x6d78 & 8 != 0`; resolves the row via
#     FUN_00057f8e (HW-ID match) and copies column tp+0xE012. Was previously "never boot-populated in
#     any path found" -- that gap is now closed.
#   FUN_00042746 (4 writes) -- the RUNTIME re-selector. Picks one of 4 HW-ID-row columns (tp+0xE012/13/
#     14/15) keyed on two 2-state flags (gp-0x67f6, gp-0x67e2); those flags' own transitions are driven
#     by gp-0x6806 (== latActive, 99.983% per prior memory) and gp-0x69b0 (engagement gate) crossing
#     sentinels -0x8000/0. This is the engagement-edge writer V73's probe found; NOT a fault failover in
#     the ordinary sense, though gp-0x67e2's branch also depends on a consistency check vs cal tp+0x7182.
#   FUN_0004a798 (1 write, extended disp23 encoding) -- UDS WDBI, request-ID case 1; bench-only, folded
#     into the same gp+0x63e8..0x6427 config cluster as gp+0x6408 (see [[reference_accord_tva_hw_id_provenance]]).
# Plus a UDS RDBI reader (FUN_0004a8ca, register-indirect `mov 0xfedfe3fd,r6`) and a diagnostics packer
# (FUN_000508e8, 2 reads) that reports the raw byte as telemetry -- neither is a torque-path consumer.
# A160 = ID-table slot 2 "TVAA1" (gp-0x674e=1, gp+0x63fd=10 when engaged, =8 manual) via FUN_00057f8e's
# own-HW-ID match (the HW-ID itself is programmed at manufacture, not in code.bin).
# Every real TVAA* slot yields the same FALLING assist family and a flat-15360 setpoint record, so
# whatever tightens the wheel in Sport is not this firmware.
# 🛑 READERS (13 total distinct pointer arrays confirmed this session, up from 2 previously mapped):
#   already known: FUN_00034350's 5 damping factors (0xC9CCC/0xC9E9C/0xC9DB4/0xC9F84/0xC77A0, see above),
#   FUN_00036c12 friction (0xCBE74), FUN_0003ad74 r24/r26 speed-blend coefficient sets (LAB_000cbf5c/
#   c044/c12c + tp+0xd214, keyed 0/10/50/100 km/h breakpoints at tp+0x7010).
#   NEW: FUN_00034a72 boost (PTR_DAT_000ca324, scalar per-mode cal); FUN_000348e0 angle-tracking blend
#   (5 arrays, already the gp-0x6a10 "flat zero at creep" chain); FUN_00035154 (PTR_DAT_000c7888, speed
#   gp-0x6a62-keyed float LERP); FUN_000382d8 (LAB_000cc9fc/PTR_DAT_000c7b40, speed gp-0x6a64-keyed
#   selector, same shape as FUN_0003ad74); FUN_0003b338 (0xC8198), FUN_0003b416 (0xCA5DC, speed
#   gp-0x6a5e-keyed), FUN_0003b49a (0xCBCA4, feeds gp-0x6b28) -- roles of these last 3 NOT resolved this
#   session (index variables / downstream consumers open).
# ⇒ Engagement re-indexes damping, friction, boost, and both rate lanes simultaneously -- wide reach, but
#   FactorC's Y[0]=0 floor holds at BOTH mode 8 (X0=1280=20km/h) and mode 10 (X0=2240=35km/h), so the
#   "damping architecturally zero at 8 km/h" finding is UNCHANGED by which mode is active. Whether any of
#   the 7 NEW arrays differ meaningfully between mode 8/10 at low speed is OPEN -- not checked this session.
# Safety-ceiling curve, pointer array @0xC7970, keyed on the MAX voter. In THIS image every mode is a
# FLAT 512 -- it is a constant ceiling, not a shaped curve. Default fallback tp+0x715a (0xC615A) = 512
# is used when the key is >= 0x7d01 (saturated / the 0xFFFF invalid-sensor sentinel). [VERIFIED]
ASSIST_CEILING_X = (0, 640, 2560, 5760, 6400)
ASSIST_CEILING_Y = (512, 512, 512, 512, 512)
ASSIST_CEILING_DEFAULT = 512                   # tp+0x715a
ASSIST_SENTINEL = 0x7d01                       # >= this => invalid/saturated sensor path
# 🛑 0x3638 is NOT a rate step. FUN_0004613e only snapshots its params into log cells and calls
# FUN_00016de6(0x1c,...) -- a fault LOGGER; 13880 is a diagnostic TAG (the same callee takes 0x38c7
# elsewhere). Its call site @0x34a94 is a cross-tick computation-integrity WATCHDOG on gp-0x6bb2/4/6/8
# re-verifying the SAME +-512 ceiling, with no forward path into any control signal. Corrected 2026-07-30.
ASSIST_RATE_STEP = 0x3638                      # diagnostic tag, kept only so the watchdog is modelled


def _lerp_flat(x: int, xs, ys) -> int:
    """Piecewise-linear interpolation with FLAT extrapolation outside the breakpoints.

    This is the firmware's LERP idiom, byte-confirmed at the setpoint-limit site 0x28fc8-0x29044:
    below xs[0] it returns ys[0] (early exit @0x28fec), above xs[-1] it returns ys[-1] (early exit
    @0x29002), and in between it does (dy * (x - x0)) / dx via `mul` @0x29026 + `divq` @0x2902c.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            span = xs[i + 1] - xs[i]
            return ys[i] + _div_trunc_zero((ys[i + 1] - ys[i]) * (x - xs[i]), span)
    return ys[-1]


def base_driver_assist_lane(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    The base power-steering boost curve: driver column torque -> motor assist demand (lane gp-0x6bbe).
    [VERIFIED] FUN_00034a72, scheduled from w_steer_control_task (phase-mask gating unconfirmed); mode
    select ld.bu gp+0x63fd (0..33); primary key gp-0x6a5e (AVG voter), ceiling key gp-0x6a62 (MAX
    voter); tables: boost @0xCA154, ceiling @0xC7970 (both byte-dumped), plus 4 undumped scaling tables
    [OPEN] (gain-scalar 0xCA324, rate-keyed LERP 0xCA4F4, clamp 0xC7A58, gp-0x69ba LERP 0xCA23C);
    polarity gp-0x6752; gp-0x6bb2/4/6/8 is a cross-tick integrity WATCHDOG, NOT a rate limiter
    (corrected 2026-07-30 -- FUN_0004613e is a fault logger and 0x3638 is its diagnostic tag);
    its own 4-state ramp SM
    (gp-0x682e, timer gp-0x68c8 vs tp+0x74d1*10), separate from the LKAS engage SM; writes gp-0x6bbe,
    lockstep-shadowed at gp-0x4cf0.

    🛑 SETTLED 2026-07-30, and this function has NOT yet been migrated: gp-0x6a5e/0x6a62/0x6a64 are a
    5-channel VOTED VEHICLE SPEED, not voted driver torque. Producer chain FUN_00053216 ->
    FUN_000534da -> FUN_00041eec (the voter, sole writer of all three), scale 64.0625 counts/km/h.
    Independently corroborated here by byte-reading this very curve: mode 10 = 0xD2834 has
    X = (0, 640, 2560, 5120, 7808, 10240) which divides to (0, 10.0, 40.0, 79.9, 121.9, 159.8) km/h --
    textbook speed breakpoints that no torque axis would produce. See the agent memory
    `reference_accord_gp6a5e_producer_chain_and_creep_zero_damping.md`.
    ✅ THE RENAME HAS LANDED (2026-08-03): `col_torque_avg` -> `speed_voted`, all 8 call sites in one
    contained pass, module re-imported and every self-check re-run. The identifier no longer asserts a
    role the cell does not have. `col_torque_rate` is a DIFFERENT cell (gp-0x4f62, Sensor-B torque
    finite difference) and was deliberately NOT touched.
    ⚠ STILL OPEN, and it is a MODELLING issue rather than a naming one: the producer below is still
    written as averaging torque-sensor *coils*. The averaging STRUCTURE is right -- FUN_00041eec
    averages the agreeing channels -- but the local names and surrounding prose still describe those
    channels as torque. Re-word against the voter's real 5-channel speed inputs. Separate contained
    pass; it changes no numeric result.

    ★ Load-bearing consequence already byte-verified (all 34 mode tables, _v59_plain_image.bin):
    damper FactorC (0xc9e9c[mode], mode 10 = 0xD27BC, X=(2240,3840,5120,8960) Y=(0,235,430,877)) has
    Y[0] == 0 in EVERY mode, with X0 = 20/30/35 km/h. It is multiplicative and the LERP clamps to Y0
    below X0, so BASE-ASSIST DAMPING IS EXACTLY ZERO BELOW 35 km/h on this car.
    ⚠ But V59 shows that is NOT what suppresses the ~21 Hz grinding: engaged hands-off, speed-stable
    windows (n=159) give mode prominence 1521x / 935x / 91x / 6.0x at 1-2 / 2-3 / 4-6 / 6-9.72 m/s --
    the mode and the pump are BOTH already dead at 6 m/s, BELOW the 9.71 m/s FactorC onset. Raising
    FactorC would buy a base-assist feel change for nothing. Lever NOT supported by the data.
    ⚠ Also refuted: the speed-keyed boost curve does not concentrate assist at creep. It is nearly
    flat -- relative gain 0.856 / 0.979 / 0.987 / 0.997 / 0.903 at 0.5 / 3 / 6 / 10 / 18 m/s.
    """
    mode = st.assist_mode                             # gp+0x63fd, range 0..33 (NOT 0..7)

    # --- validity gate ("bVar10"): ALL of these must hold or the lane collapses to the ramp-down path
    valid = (st.assist_substate in (1, 2)             # gp-0x67fe  EPS assist substate
             and st.plausibility_ok                    # gp-0x67f4 == 1, from the voter FUN_00041eec
             and st.speed_voted < ASSIST_SENTINEL   # gp-0x6a5e not invalid/saturated
             and abs(st.col_torque_sensor_b) <= 25600) # gp-0x4f60 plausibility window (same +/-25600
                                                       #   window the arb hard-bail uses @0x28f30)

    # --- 4-state ramp SM (gp-0x682e), timer gp-0x68c8 vs tp+0x74d1*10 -----------------------------
    if not valid:
        st.assist_ramp_state = 0
        st.assist_ramp_timer = 0
    elif st.assist_ramp_state < 3:
        st.assist_ramp_timer += 1
        if st.assist_ramp_timer >= cal.assist_ramp_ticks:
            st.assist_ramp_state += 1
            st.assist_ramp_timer = 0
    ramp_scale = st.assist_ramp_state / 3.0           # 0 -> 1 over the 4 states

    # --- the boost curve proper: AVG driver torque -> raw assist -----------------------------------
    key_avg = min(abs(st.speed_voted), 0xFFFF)
    xs, ys = ASSIST_BOOST_CURVE.get(mode, ASSIST_BOOST_CURVE[10])   # default = this car's curve
    raw = _lerp_flat(key_avg, xs, ys)

    # --- NO rate limiter here. 🛑 Corrected 2026-07-30: the gp-0x6bb2/4/6/8 cluster is a cross-tick
    # WATCHDOG (FUN_00035154 re-derives this lane's ceiling in float and stores a +-5-count tolerance
    # for FUN_00034a72 to check next tick), not a limiter -- it has no forward path into gp-0x6bbe.
    # The model previously clamped `delta` to +-0x3638 here, which limited nothing (0x3638 = 13880
    # against a lane clamped to +-512) and mis-taught the chain. Pass through.
    st.assist_rate_state = raw

    # --- safety ceiling, keyed on the MAX voter (flat 512 in this image) ---------------------------
    key_max = abs(st.col_torque_max)
    ceiling = (ASSIST_CEILING_DEFAULT if key_max >= ASSIST_SENTINEL
               else _lerp_flat(key_max, ASSIST_CEILING_X, ASSIST_CEILING_Y))

    # --- gain modulation, polarity, and the final clamp against the ceiling ------------------------
    # 🛑 CORRECTED 2026-07-30 from the decompile of FUN_00034a72 + a byte-level shift/multiply scan.
    # The previous rendering ("both curves multiply the same assist term in series, >>14 twice") was
    # WRONG about the structure. The two curves enter at DIFFERENT points and are separated by a
    # subtraction and two clamps, so they compose multiplicatively only while none of those bind:
    #
    #   y1 @0xD28DC (via 0xCA4F4[mode]) -> blended -> * clamp(gp-0x6986, 0x400) >>14  @0x34C26
    #        -> * 0xCA40C[mode] >>7 -> ... -> DIFFERENCED against gp-0x6a56 -> clamp +-12000
    #   then * 0xCA324[mode] >>7 -> * boost curve 0xCA154[mode] (keyed on SPEED gp-0x6a5e)
    #        -> clamp(>>10, +-0xC7A58[mode])
    #   y4 @0xD2888 (via 0xCA23C[mode]) -> blended -> * clamp(gp-0x6988, 0x400) >>10
    #        -> * (the above) >>14  @0x35008 -> * polarity (mulh @0x35010) -> clamp +-ceiling
    #
    # ⚠ A subagent argued y1 is a DEAD END (only 3 image-wide refs to its state cell gp-0x69bc, all
    # in this function). That argument is INVALID: a byte scan of the STATE CELL cannot show whether
    # the blended value is consumed in a REGISTER in the same tick -- which is exactly what a
    # slew-limited gain does. Byte scan of FUN_00034a72 finds exactly two `>>14` sites:
    # `shr 0xe,r28` @0x34C26 (the y1 multiply, before the subagent's trace start of 0x34F20) and
    # `sar 0xe,r13` @0x35008 (y4). Both curves are live. gp-0x6986 / gp-0x6988 are DIFFERENT adjacent
    # cells, one clamped companion per LERP -- the symmetric two-lane structure.
    #
    # ★★ AND BOTH LERP OUTPUTS ARE SLEW-BLENDED BEFORE USE -- previously unmodelled entirely:
    #   y1: blended toward persisted gp-0x69bc, rate cal 0xCA06C[mode] -> 0xD2006 -> 102 (Q10)
    #   y4: blended toward persisted gp-0x69ba, rate cal tp+0xB06C[mode] (same table)   -> 102
    # Both lockstep-shadowed (gp-0x4c6e / gp-0x4c6c). A 1-pole blend at 102/1024 passes only ~0.37 of
    # 42 Hz, so it ATTENUATES the parametric pump measured by V59. ⚠ The blend sits inside an `if`
    # (guard ~0x34BF0) => it is an ASYMMETRIC slew, direction unresolved; simulating the literal
    # integer arithmetic at 1 kHz gives eps 0.016-0.034 at median hands-off amplitude, 0.085-0.161 at
    # p90, 0.132-0.255 at p99, against a Mathieu threshold of ~2/Q = 0.147. ⇒ the pump is
    # SUB-THRESHOLD at typical amplitude and crosses only in the loudest bursts: an amplitude-gated
    # bootstrap, which is what makes the grinding bursty rather than continuous.
    # ⚠ gp-0x6986 / gp-0x6988 values are UNMEASURED; eps is not final until they are dumped.
    # [STILL SIMPLIFIED] the model below keeps the flat series form for continuity. It is a
    # first-order stand-in, NOT the literal chain -- see the sequence above before using it.
    amp = boost_amplitude_index(st)
    y1 = _lerp_flat(amp, BOOST_AMP1_X, BOOST_AMP1_Y)      # 0xD28DC via 0xCA4F4, then blended
    y4 = _lerp_flat(amp, BOOST_AMP4_X, BOOST_AMP4_Y)      # 0xD2888 via 0xCA23C, then blended
    scaled = (int(st.assist_rate_state * ramp_scale) * y1) >> 14
    scaled = (scaled * y4) >> 14
    signed = scaled * st.assist_polarity                                   # gp-0x6752
    return _clamp(signed, -ceiling, ceiling)                               # -> gp-0x6bbe


# Blend/slew rate applied to BOTH amplitude-LERP outputs before they multiply anything.
# 0xCA06C[mode 10] -> 0xD2006, first u16 = 102 (Q10 = 0.0996). Byte-verified on _v59_plain_image.bin.
# ⚠ 0xD2000 is a SHARED overlapping block: [666,666,666, 102,102,102, 43,43,43, 32896,128, 0,5,0...]
#   0xC7A58[10] -> 0xD2000 reads 666 (output clamp) | 0xCA06C[10] -> 0xD2006 reads 102 (this blend)
#   0xCA324[10] -> 0xD200C reads 43 (gain scalar).  Do NOT edit one offset without resolving what
#   else reads the block -- that check is OPEN and gates any build on this lever.
BOOST_AMP_BLEND_Q10 = 102


# --- the boost AMPLITUDE index and its two curves -------------------------------------------------
# 🛑 gp-0x6ba6 == abs(gp-0x6b9a). FUN_0003b66a writes both from one r28: `cmp r0,r28 / mov r28,r13 /
# bge 0x3b886 / subr r0,r13` @0x3b874-87c, then st.h @0x3b892 (gp-0x6ba6) and @0x3b8b0 (gp-0x6b9a).
# Sole writer each, byte-scanned for both gp-relative encodings.
# gp-0x6b9a itself indexes NOTHING: its only live consumer is a 5-input plausibility gate
# (|x| <= 25600 @0x34c9c-cb4 -> r21 -> zeroes r24 @0x34fc8), so its SIGN has no output effect, and two
# of its three reads in FUN_00034a72 are dead (tp+0x7499 == 1 takes the branch @0x34b3c).
# ⇒ V58 measured the SIGNED sibling crossing zero at 20.93 Hz only when LKAS applies, so this index is
# that signal RECTIFIED -- a minimum at every zero crossing, sweeping both curves at ~2x the mode
# frequency on the BASE ASSIST path.
#
# ★★ V59 FLEW 2026-07-30 (route 2c) AND MEASURED THE DEPTH. The mechanism is LIVE, not weak.
# Thermometer probe on gp-0x6ba6, 50,963 frames, 100% live / 100% monotonic / fault sentinel 0.000%.
# Conditioned on engaged + creep + SUSTAINED hands-off (|lowpass(tq,3Hz)| <= 200), 50.2 s, n=5016:
#     depth   76.93% <512 | 18.46% 512-1k | 4.57% 1k-2k | 0.04% >=2048
#             (disengaged + creep + hands-off, n=6944: 99.83% <512 -- the index barely leaves the pin)
#     the index's OWN spectrum peaks at 42.19 Hz = 2 x the 21.09 Hz mode, prominence 11.10x,
#     coherence 0.795 vs the torsion bar (K=30, periodograms averaged across 13 DISJOINT runs, never
#     spliced). The 18-26 Hz band shows only 1.23x. That is the full-wave-rectification signature.
#     Disengaged: bit5 NEVER toggles -- 0/4 runs, 61.2 s, K=90, prominence 0.00x. Pump absent.
# ⇒ a parametric gain pump at 2f into a mode at f. Depth epsilon = (1-g)/(1+g) from the swept range:
#     index 0..512 -> 0.162 | 0..1024 (p95) -> 0.333 | 0..2048 -> 0.490   [SERIES, see the >>14 pair
#     below -- HALVE these if only one curve applies; that block is flagged non-literal]
# 🛑 CAUSALITY IS NOT SETTLED AND CANNOT BE FROM THIS DATA. The index is |x| of a bar-derived signal,
# so "pump tracks mode" is partly guaranteed by rectification: a mode dying for its own reasons quiets
# the bar, pins the index, and produces identical numbers. Only an INTERVENTION (flatten the swept
# range, re-fly) separates drive from echo.
# ⚠ Blast radius, byte-verified on _v59_plain_image.bin: 0xD28DC and 0xD2888 are each referenced
# EXACTLY ONCE image-wide (0xca51c and 0xca264, mode slot 10 of their own pointer tables); all 34
# slots in both tables are distinct targets. Editing them touches mode 10 only. GATE 1 is clean;
# GATE 2 is NOT -- both sit on the base-assist path and change manual feel.
BOOST_AMP1_X = (0, 512, 1490, 2529, 3645, 5120)     # 0xD28DC, byte-verified
BOOST_AMP1_Y = (16384, 14657, 11672, 9365, 8244, 8187)
BOOST_AMP4_X = (0, 307, 1024, 1741, 3072, 6144)     # 0xD2888, byte-verified
BOOST_AMP4_Y = (16384, 14392, 10265, 8997, 8176, 8176)

FAULT_SENTINEL_6BA6 = 0xFFFF    # FUN_0003b66a input-gate failure; > 25600 so r21 catches it
FAULT_SENTINEL_6B9A = 0x7FFF


def boost_amplitude_index(st: EpsState) -> int:
    """gp-0x6ba6, the index into both boost amplitude curves; the magnitude of gp-0x6b9a."""
    return abs(st.boost_fir_out)


# tp+0x7010 = 0xC6010, byte-read [0, 640, 3200, 6400] = 0 / 9.99 / 49.95 / 99.9 km/h at 64.0625
# counts/km/h. The key is gp-0x6a5e (VOTED VEHICLE SPEED -- see the rename note in
# base_driver_assist_lane), substituting cal tp+0x7314 when gp-0x67f4 != 1.
ASSIST_RATE_CROSS_X = (0, 640, 3200, 6400)

# ★ RESOLVED 2026-08-01 from the FUN_0003ad74 decompile + byte reads (orchestrator, first-hand).
# The two halves of FUN_0003ad74 are NOT symmetric, and the record had this wrong in two ways:
#
#   gain_B (r24)  -- MODE-INDEXED, through FOUR SEPARATE POINTER ARRAYS, each indexed by mode*4:
#         0xCBF5C   0xCC044   0xCC12C   tp+0xD214 = 0xCC214
#     For OUR CAR (gp+0x63fd == 10) they resolve to records 0xD2A74 / 0xD2AB0 / 0xD2AEC / 0xD2B28.
#     ⚠ These are NOT four consecutive records at a stride -- reading them as consecutive from
#     0xD2AEC lands on modes 10/11's interleaved rows and gives a nearly FLAT surface (2305->1948),
#     understating the real rolloff by 2x. Records are PRIVATE per mode (mode 11 -> 0xD2A88/...).
#     ⚠ build_v62_tva.py's GAIN_B_LERP_MODE10 tripwire watches only 0xD2AEC and 0xD2B28, so it is
#     blind to an edit landing on 0xD2A74 or 0xD2AB0. Widen it before any cal work on this lane.
#     Output: runtime X row -> gp-0x6e40, runtime Y row -> gp-0x6e38 (read by r24 @0x3AB9C-0x3ABF8).
#
#   gain_A (r26)  -- NOT mode-indexed at all. Four FIXED records at tp+0x7a68/0x7a7c/0x7a90/0x7aa4
#     = 0xC6A68 / 0xC6A7C / 0xC6A90 / 0xC6AA4, hard-coded in the instruction stream.
#     Output: runtime X row -> gp-0x6e30, runtime Y row -> gp-0x6e28.
#     (Moot in practice -- r26 is structurally inert, see assist_slope_q10.)
#
# Y is Q10 (1024 == 1.0); every value below byte-verified in _v65_plain_image.bin.
ASSIST_RATE_B_RECORDS = (
    ((0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),   # 0xD2A74  <- 0xCBF5C[10], speed 0 km/h
    ((0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),   # 0xD2AB0  <- 0xCC044[10], speed 10 km/h
    ((0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),   # 0xD2AEC  <- 0xCC12C[10], speed 50 km/h
    ((0, 400, 1500, 3000), (2151, 2151, 2049, 1947)),   # 0xD2B28  <- 0xCC214[10], speed 100 km/h
)
# ⇒ THE SURFACE, which matters for any lever on this lane: at CREEP the gain is 3072 and FLAT out to
# motor rate 400 counts (~85 deg/s at 4.7121 counts per deg/s), then falls to 1536 at 3000 (~637
# deg/s) -- a genuine 2x rolloff. At road speed it flattens (0.80x at 32 km/h). So Honda ALREADY
# de-escalates this lane when the wheel is moving fast, and only at low speed. The commonly-quoted
# "r24 default arm = 2305" is the 50 km/h record; at the hands-off-creep operating point it is 3072.
#
# ★★★★ RESOLVED 2026-08-02, orchestrator-verified from the images and from route 47:
#
#   1. THE RATE AXIS IS USABLE -- the three symptom populations sit at DIFFERENT points on it:
#          grind #1            ~128 deg/s -> gp-0x6ac0 ~ 603    [400,1400] ON the rolloff
#          grind #2 creep      ~256       ->           ~1206    [400,1400] further along the rolloff
#          grind #2 highway   30-42       ->         ~141-198   [0,400]    FLAT (Y0 == Y1)
#      X1 = 400 = 0x0190 EXACTLY, and Y0 == Y1 in every curve EXCEPT mode-10's 50 km/h
#      record 0xD2AEC, which is Y0 = 2305 / Y1 = 2304 (byte-verified `01 09` then `00 09`) -- a +1
#      cal-tool rounding artifact, 0.04%, behaviourally nil, but an exact Y0 == Y1 equality test
#      WILL break on it. The [0,400] segment is flat to within 1 count at every speed.
#      GATE 2 caution on any rate-axis edit: gp-0x6ac0 is a RECTIFIED filtered motor rate, so it
#      sweeps at 2x the mode frequency and a steeply rate-dependent gain modulates at 2f (the
#      parametric-pump failure mode V58/V59/V60 chased). Stock ALREADY has a rolloff there, so the
#      mechanism is not new and is tolerable at stock slope; any edit that STEEPENS it must state the
#      new slope and argue the pump margin. Quantitative caution, not a structural veto.
#
#   2. UNITS -- SETTLED EMPIRICALLY, after the orchestrator got this WRONG once on 2026-08-02.
#      The 0x14A rate field IS deg/s (factor 1): regressing `rate_c` on the differentiated ANGLE
#      channel (0x14A b0:1, factor -0.1 => degrees) gives slope 0.95-1.00 with r >= 0.985 on every
#      clean segment. And gp-0x6ac0 = 4.71210813 counts per deg/s, so the inner breakpoints
#      [0, 400, 1400/1500, 3000] are [0, 85, 297, 637] DEG/S -- which real driving reaches (|rate|
#      over 407,617 frames peaks at 521 deg/s, p99.9 = 408), whereas the erroneous 0.589 counts per
#      deg/s would put them at 679/2377/5093 where Honda's 2x rolloff could never engage at all.
#      RETRACTED: "bus counts = 8 x deg/s" and "V67's arm delivers 1.94x". V67's build note was
#      CORRECT -- LERP 2622 at grind #1's operating point, arm 5244 = exactly 2.00x. The error was
#      composing two UNVERIFIED structural relations (gp-0x6ac0 = |gp-0x6abe|, and
#      bus = (gp-0x6abe*48*1159)>>15) into a scale instead of MEASURING it against a channel already
#      in the cache. One of those two premises is wrong; which one is OPEN.
#
#   3. V67's FLAT ARM INVERTS HONDA'S OWN SCHEDULE. Because the surface rolls off with speed, a scalar
#      arm delivers its LARGEST multiplier where the stock design wanted the LEAST:
#          grind #1  creep 7.2 km/h   LERP 2622 -> 2.00x
#          grind #2  creep 5 km/h     LERP 2409 -> 2.18x
#          highway   100+ km/h        LERP 2151 -> 2.44x   <- the maximum
#      🛑 A flat arm is STRUCTURALLY INCAPABLE of fixing the highway: one degree of freedom, two
#      constraints. 1.00x at highway needs arm 2151, which is 0.80x at grind #1 (WORSE than stock);
#      2.00x at grind #1 needs arm 5408, which is 2.51x at highway.
#      ⚠ AND THE PREDICTED HIGHWAY COST DID NOT MATERIALISE -- see openpilot_command_slew_invariance().
#
#   4. BLAST RADIUS IS CLEAN for a cal-only speed schedule (raise Y[0]/Y[1] in the 0 and 10 km/h
#      records only): EXACTLY ONE pointer image-wide per record (0xCBF84 / 0xCC06C / 0xCC154 /
#      0xCC23C, full 32-bit LE scan), all four in ONE CRC block (0xD2000, 0xD2FFC), and a full-image
#      32-bit float scan finds NO float mirror for any Y value and no clustered mirror table => the
#      V27 int/float desync class does not apply. Buildable and safe -- but NOT recommended, because
#      the highway dose response it would target does not exist in the data.
#      Arithmetic + the edit's exact bytes: analysis-2020accord/v68_design_math.py.
ASSIST_RATE_A_RECORDS = (
    ((0, 400, 1600, 3000), (3072, 3072, 2434, 2048)),   # 0xC6A68
    ((0, 250, 1200, 3000), (3072, 3072, 2488, 1536)),   # 0xC6A7C
    ((0, 400, 1250, 3000), (2664, 2664, 2243, 1436)),   # 0xC6A90
    ((0, 400, 1250, 3000), (2560, 2560, 2145, 1331)),   # 0xC6AA4
)
ASSIST_TORQUE_RATE_CLAMP = 5120             # aggregator input clamp on gp-0x4f62
ASSIST_TORQUE_RATE_DEADZONE = 3              # tp+0x71f6 (0xC61F6)
ASSIST_TORQUE_RATE_OUTPUT_CLAMP = 8192


def _generated_assist_rate_curve(avg_torque: int, records) -> tuple:
    """Reproduce FUN_0003ad74's element-by-element cross-interpolation."""
    key = _clamp(avg_torque, ASSIST_RATE_CROSS_X[0], ASSIST_RATE_CROSS_X[-1])
    xs = tuple(_lerp_flat(key, ASSIST_RATE_CROSS_X, tuple(record[0][i] for record in records))
               for i in range(4))
    ys = tuple(_lerp_flat(key, ASSIST_RATE_CROSS_X, tuple(record[1][i] for record in records))
               for i in range(4))
    return xs, ys


def _assist_rate_gain_q10(st: EpsState, records) -> int:
    # Invalid voter path substitutes tp+0x7314=5120 for the AVG cross-axis.
    avg_key = abs(st.speed_voted) if st.plausibility_ok else 5120
    xs, ys = _generated_assist_rate_curve(avg_key, records)
    # Firmware folds an out-of-domain motor rate >=13001 back to zero before the LERP.
    rate_key = st.motor_rate_raw if 0 <= st.motor_rate_raw < 13001 else 0
    return _lerp_flat(rate_key, xs, ys)


def _inline_torque_rate_b(st: EpsState) -> int:
    """FUN_0003aa2c r24: the direct, inertia-sensitive Sensor-B torque-rate assist lane."""
    gain_q10 = _assist_rate_gain_q10(st, ASSIST_RATE_B_RECORDS)
    if st.assist_gate_671d != 0:
        gain_q10 = 1024                              # tp+0x7442 (0xC6442)
    elif st.assist_gate_683c != 0:
        gain_q10 = 512                               # tp+0x7446 (0xC6446)
    elif st.assist_state_671a >= 5:
        gain_q10 = 2048                              # tp+0x7440 (0xC6440)

    dtorque = _clamp(st.col_torque_rate, -ASSIST_TORQUE_RATE_CLAMP, ASSIST_TORQUE_RATE_CLAMP)
    scaled = (dtorque * gain_q10) >> 10              # V850 `sar`: floor for negative products
    if scaled > ASSIST_TORQUE_RATE_DEADZONE:
        shaped = scaled - ASSIST_TORQUE_RATE_DEADZONE
    elif scaled < -ASSIST_TORQUE_RATE_DEADZONE:
        shaped = scaled + ASSIST_TORQUE_RATE_DEADZONE
    else:
        shaped = 0
    return _clamp(st.assist_polarity * shaped,
                  -ASSIST_TORQUE_RATE_OUTPUT_CLAMP, ASSIST_TORQUE_RATE_OUTPUT_CLAMP)


def detector_input_6c2c(rate_raw: int, ema_old: int, state_fast: int) -> tuple:
    """
    FUN_00041464 @0x4184E -- produces gp-0x6c2c, the ONLY input to the oscillation detector's threshold
    test. [VERIFIED 2026-07-31, cals byte-read LE.] It is a MOTOR-RATE DERIVATIVE off gp-0x4f50 (the
    resolver/motor ELECTRICAL rate), NOT torque and NOT a raw per-tick difference: differencing kills DC,
    so a sustained large steering input cannot drive it -- it needs the motor rate actively reversing.
    Returns (gp_0x6c2c, ema_new, state_fast_new). A slower sibling gp-0x6c2e takes the same `acc` through
    cal 0xC40DA = 3 (>>7).

    Sizing: a 21.3 Hz sinusoid needs |gp-0x4f50| ~= 1683 counts @1 kHz (1821 @100 Hz) to reach T = 12800,
    inside that signal's own +-13000 validity ceiling => the detector is NOT structurally blind to the
    ~21 Hz mode; route 35 was ~1.7-2x short. Cross-checked in the frequency domain (|1-H1| = 0.43041 x
    |H2| = 0.95375 => 7.5965*U => U = 1685), agreeing to 4 significant figures. The `acc` clamp bites at
    U ~= 4017, so T sits at ~42% of saturation and the response is linear there.
    🛑 Do NOT size T from bus torque -- gp-0x6c2c does not share the 0x18F torque LSB. [OPEN] gp-0x4f50's
    physical units (needs the ISR writing gp-0x29c4, or a probe).

    ✅ FULL 1-500 Hz SWEEP 2026-08-0x (integer-exact simulation, sanity-checked against the 1683/1682 trip
    pair above): it is a BAND-PASS, not a low-pass -- gain PEAKS at 61 Hz (1.61x the 21.09 Hz gain), stays
    >90% of that out to ~180 Hz, and rejects 1 Hz driver-band content ~30x for free. Trip amplitude
    (counts of gp-0x4f50) needs LESS at 45-100 Hz than at 21 Hz: 21.3->1683, 45->1104, 60->1056 (min),
    80->1092, 100->1186, 150->1478, 200->1735 -- all inside the +-13000 clamp, nothing here is untrippable.
    🛑 gp-0x4f50's deg/s scale is still [OPEN] -- do NOT borrow gp-0x6ac0's 4.7121 counts/deg-s here, a
    different internal signal; that composition is exactly what produced the retracted "bus=8x deg/s".
    ★ This makes gp-0x671a the kit's only above-50-Hz-capable instrument: CAN is Nyquist 50.00, the comma
    IMU 50.51.
    """
    K1, K2 = 37, 22                                   # cals 0xC643C (>>7), 0xC40DC (>>6)
    if abs(rate_raw) > 13000:                         # 0x415be-0x415ce plausibility gate
        return 0x7FFF, 0, 0                           # 0x41AC2 fault sentinel; both EMAs reset
    target = rate_raw * 1024                          # 0x415d0  Q10
    step = ((target - ema_old) * K1) >> 7             # 0x415e8  EMA #1 increment -- THE DIFFERENCE
    ema_new = ema_old + step
    acc = _clamp(step * 0x20, -0xFA0000, 0xFA0000)    # 0x41604-0x4161a  x32, clamp +-16,384,000
    state_fast = state_fast + (((acc - state_fast) * K2) >> 6)   # 0x41622  EMA #2
    return state_fast >> 9, ema_new, state_fast       # 0x4184a/0x4184e  range +-32,000; T = 40.0% of it


def _inline_torque_rate_a(st: EpsState) -> int:
    """
    FUN_0003aa2c r26 -- the ADAPTIVE Sensor-B torque-rate lane. Returns zero until gp-0x69a4 is
    replay-supplied. [VERIFIED] r26 = clamp(polarity * ((dtorque * avg(gp-0x69a4)) >> 10 * gain_A) >>
    10, +/-0x2000), dtorque = clamp(gp-0x4f62, +/-5120) -- the same dtorque and the same single
    polarity read (gp-0x6752 @0x3ab78) as r24, so r24 and r26 always carry the SAME sign (gp-0x69a4 is
    an unsigned magnitude at both ends); V39 zeroing r24 therefore removed half of a same-signed pair,
    not a counterweight. r24 applies a +/-3 deadzone (cal 0xC61F6) before its polarity multiply; r26
    has none, so near zero dtorque r26 is the only live derivative lane -- V39 predicted a no-op for
    the ~5 mph small-command regime independent of the invariance argument. r26 also has a persisted
    2-sample rolling average and a hard zero-force gate (gp-0x6b5e!=0 AND assist_state_671a < cal
    0xC64FA) that r24 lacks. GAIN_A is a 4-point flat LERP over motor-rate gp-0x6ac0 (zeroed >= 13001)
    against a table FUN_0003ad74 rebuilds each cycle from 4 ROM records on the AVG-torque axis
    (ASSIST_RATE_A_RECORDS, cals 0xC6A68/7C/90/A4); the cal-only kill surface is 18 halfwords (16 Y
    values 0xC6A72-B4, overrides 0xC6444/0xC643E), all single-reader, no float mirror.

    ★★★★ r26 IS LIVE ON-CAR -- MEASURED 2026-08-04, route 50 (V70). [EVIDENCE, existence proof]
    V70's bit4/bit3 sign pair read gp-0x6adc (r26's post-clamp RAM mirror) STRICTLY NEGATIVE on
    1,644 of 18,010 frames. A cell pinned at zero can never clear a `>= 0` test, so r26 is not
    identically zero. ⇒ "r26 is inert / r24 carries the entire lane" is REFUTED, and every
    re-attribution of V42/V61/V62 that rested on it must be re-priced.
    ⚠ Magnitude still unmeasured -- the probe gives SIGN only, so `a = gp-0x69a4/1024` is bounded
    away from 0 but not otherwise known. NEW asymmetry the same-sign model does NOT predict, and it
    must be carried: `bit3 => bit4` STRICTLY (0/18,010 frames with r24 >= 0 while r26 < 0), which is
    explained by "r26 is ZERO part of the time and same-signed otherwise" -- a `>= 0` test cannot
    separate zero from positive. Same-sign-when-nonzero stands; "always the same sign" does not.

    🛑🛑 r24 AND r26 HAVE SEPARATE GAIN SELECTORS SHARING ONE GATE -- and every multiplier this kit
    has published is an r24-only number. [EVIDENCE, orchestrator disassembly 2026-08-04]
        r26 -> gain_A: 0x3AB5E ld.hu 0x7444,tp,r8 (0xC6444=512, taken when lp != 0)
                     ▸ 0x3AB68 0xC643E ▸ else gain_A's own LERP (3072 at creep)
        r24 -> gain_B: 0x3ABFE ld.hu 0x7442,tp,r10 (0xC6442=1024, gp-0x671d, OUTRANKS ALL)
                     ▸ 0x3AC08 0xC6446 (lp != 0) ▸ 0x3AC12 0xC6440=2048 ▸ else the mode-10 surface
    The SAME `lp` gates both, so V67/V68's one-byte gate repoint raises r24 AND cuts r26 6.00x
    (3072 -> 512) simultaneously. Net vs stock = (5244 + 512a)/(3072 + 3072a): 1.707x at a=0,
    PARITY at a=0.848, BELOW stock above it. V69/V70 edited the mode-10 gain_B records only, so they
    never touched r26 at all.
    🛑🛑 AND THERE **IS** ONE CLEAN SINGLE-VARIABLE SERIES, AND IT SAYS r24 IS NEAR-INERT.
    [EVIDENCE 2026-08-04, medians recomputed from _grind2_lib.wrecs] stock -> V70 -> V69 holds r26 at
    x1 and steps r24 x1 -> x2 -> x4, reading 879 -> 729 -> 746, ALL THREE CIs MUTUALLY OVERLAPPING.
    => r24 is close to INERT for grind #1 across a 4:1 dose range. And every build that FIXED grind #1
    changed r26 (V62 x2; V67/V68 /6.00), while every build that changed only r24 did not.
    => THE HEADLINE IS NOT "nothing is single-variable" -- IT IS "THE DOSE AXIS THIS KIT HAS USED
    SINCE V62 IS THE WRONG LANE."
    ★ Four supporting byte facts: (1) gain_A's records 0xC6A68/0xC6A7C/0xC6A90/0xC6AA4 are
    BYTE-IDENTICAL across all 11 images => V67/V68's /6.00 (= 512/3072) is EXACT and engaged-only;
    (2) the two LERPs live in separate RAM -- gp-0x6e40/gp-0x6e38 for gain_B, gp-0x6e30/gp-0x6e28 for
    gain_A -- filled by the two halves of FUN_0003ad74; (3) gain_B is filled from the MODE-INDEXED
    arrays and gain_A from FIXED, non-mode-indexed records, which is why V69/V70's mode-10 surface
    edit could not reach r26 even in principle; (4) there is NO gp-0x671d mask arm on the r26 side --
    gain_A is 2 arms + default, not 3.
    ⚠⚠ CARRY THIS UNEXPLAINED, DO NOT SMOOTH IT: r26 x2 (V62/V65) AND r26 /6.00 (V67/V68) BOTH HELPED,
    and /6 helped MORE (168 vs 109 against stock's 879). A monotone "more r26 damping is better" story
    and a monotone "less is better" story are BOTH refuted by the same two rows. The corpus cannot say
    why, and that is the leading open question. Anyone proposing an r26 dose must state which
    direction they are betting on and why.
    ⚠ Grind #1 is BLIND to r24 gain -- log-log slope -0.144 [-0.991, +0.347], pairwise
    P = 0.667/0.610/0.426 -- so it CANNOT be used as an in-force check for the r24 lane on any future
    build. Structural, not a power limit.
    ⇒ NO TWO POST-V38 RATE-LANE BUILDS ARE A SINGLE-VARIABLE CONTRAST. Measured grind #1 medians:
    V61 (both x0) 2501 · stock 879 · V70 (r24 x2, r26 x1) 729 · V69 (r24 x4, r26 x1) 746 ·
    V62/V65 (BOTH x2) 168 · V67/V68 (r24 x1.71, r26 /6, gated) 109. r24's dose is FLAT across
    x2 -> x4; the only always-on build that fixed grind #1 is the only one that also doubled r26.
    ✅ V62/V65's `sar` route (0x3AB76 AND 0x3AC20, 0xa -> 0x9) is the ONLY encoding that is
    dose-exact independent of `a`, because it scales both lanes identically.

    [OPEN] r26's realistic MAGNITUDE (clips only if avg(gp-0x69a4) > ~546); the mechanical loop sign
    (positive-feedback vs feedforward, needs live telemetry, not disassembly); gp-0x6752's concrete
    runtime value; and whether gain_A's LERP rolls off with rateKey the same way gain_B's does --
    if not, the a=0.848 parity point moves.
    """
    if st.assist_slope_q10 is None:
        return 0

    state_lt_5 = st.assist_state_671a < 5
    selected_state_value = 1 if state_lt_5 else 0     # C6138=1 / C6136=0
    if st.assist_gate_6b5e != 0 and selected_state_value == 1:
        pre_polarity = 0
    else:
        current = int(st.assist_slope_q10) & 0xFFFF
        previous = st.previous_assist_slope_q10 if st.assist_slope_history_valid else current
        st.previous_assist_slope_q10 = current
        st.assist_slope_history_valid = True
        avg_slope_q10 = (current + previous) >> 1

        gain_q10 = _assist_rate_gain_q10(st, ASSIST_RATE_A_RECORDS)
        if st.assist_gate_683c != 0:
            gain_q10 = 512                           # tp+0x7444 (0xC6444)
        elif not state_lt_5:
            gain_q10 = 1536                          # tp+0x743e (0xC643E)

        dtorque = _clamp(st.col_torque_rate, -ASSIST_TORQUE_RATE_CLAMP, ASSIST_TORQUE_RATE_CLAMP)
        stage1 = (dtorque * avg_slope_q10) >> 10
        pre_polarity = (stage1 * gain_q10) >> 10

    return _clamp(st.assist_polarity * pre_polarity,
                  -ASSIST_TORQUE_RATE_OUTPUT_CLAMP, ASSIST_TORQUE_RATE_OUTPUT_CLAMP)


def assist_shaping_lanes(sensors: SensorInputs, st: EpsState) -> dict:
    """
    The five sibling assist-shaping lanes (Section 3B), each writing its own aggregator lane rather than
    applying in series to the boost curve; all read gp-0x6a5e (voted VEHICLE SPEED) directly. [VERIFIED
    addresses; INFERRED role labels] FUN_00034350 -> gp-0x6bd0 (damping) is the product of 5
    mode-indexed LERP gain factors (a MIN-clamped seed, a flat driver-torque table, an angle-deviation
    term, |motor rate| gp-0x6ac0, and gp-0x6ac2), sign forced opposite gp-0x6abe; two independent
    hands-off deadzones exist (Factor C's Y[0]=0 below 2240 counts driver torque, mode 10/11
    @0xD27BC/D27D0, raised by V44/V47; Factor E's Y[0]=0 below 60 counts motor rate, @0xD27F8/D280C,
    raised only by V47), and its output clamp is a dynamic LERP keyed on gp-0x6ac2 (@0xD209C/D20A8)
    with a float-mirror lockstep at cal 0xC6554/58/5C/60 (DTC-0x1d no-debounce hard shutdown on
    divergence -- any edit to the int clamp table needs a bit-exact float twin). FUN_00036c12 ->
    gp-0x6b26 (friction comp) is LERP(gp-0x6a5e voted VEHICLE SPEED, @0xCBE74, mode10@0xD2A44) x
    gp-0x6c2c (motor-rate derivative), a plain signed multiply -- NO sign()/abs/hysteresis anywhere in
    the lane, so it is smooth and continuous through zero and cannot itself generate stick-slip; magnitude
    is LARGEST at 0 km/h (Y[0]=-9830) and falls ~5x by 90 km/h (Y[2]=-1966); self-clamps +/-511 (0xC407E)
    before the aggregator's own +/-0x400 gate -- and that 511, one count under FUN_00036d74's 512 trip, is
    Honda's HARD-FAULT INTERLOCK (raised to 850 by V73-V75, restored by V81; see Section 3B).
    [VERIFIED 2026-08-04, disasm 0x36c12-0x36cbe]. FUN_0003a382 ->
    gp-0x6ad4 (resonance lane) is a genuine discrete PID on ERR = clamp(gp-0x4f60 - bias, +/-0x2800):
    P = (LERP(motor_rate)*ERR>>10)*32, I = accumulate(98*ERR>>10), D = clamp((ERR-ERR_prev)*2048>>10,
    +/-0x2800)*32, summed and rescaled to +/-ceiling; both of its smoothing EMAs (cals 0xC6450, 0xC644A)
    are Q10 unity (defeated passthroughs, not lags) -- V43/V46 each re-introduced one pole and both were
    flashed null, and V56's mute of this lane's output bound also left the ~21 Hz mode unchanged,
    eliminating this lane as the sole source (it enters gp-0x6b98 through one of the other eight
    aggregator lanes). FUN_00036388 -> gp-0x6b62 (return-to-centre) is a slow +/-1/tick accumulator
    with hysteresis. FUN_000352b4 -> gp-0x6b86 + gp-0x69a4 (friction magnitude) zeroes only OUTSIDE the
    +/-25600 Sensor-B plausibility window; its adaptive 10-segment magnitude is [OPEN]. inline r24/r26
    are the Sensor-B torque-rate lanes modelled by _inline_torque_rate_b/_a above.
    """
    supplied = sensors.assist_lane_overrides
    st.assist_inline_a = _inline_torque_rate_a(st)
    st.assist_inline_b_raw = _inline_torque_rate_b(st)
    st.assist_inline_b = st.assist_inline_b_raw

    sensor_b_valid = -25600 <= st.col_torque_sensor_b <= 25600
    magnitude = int(supplied.get("magnitude_6b86", 0)) if sensor_b_valid else 0
    magnitude = _clamp(magnitude, -0x3000, 0x3000)  # producer's verified final bound

    # The remaining role names are structural inference. Their values stay explicit replay inputs.
    return {
        "inline_a": st.assist_inline_a,
        "inline_b": st.assist_inline_b,
        "magnitude_6b86": magnitude,
        "damping_6bd0": int(supplied.get("damping_6bd0", 0)),
        "friction_6b26": int(supplied.get("friction_6b26", 0)),
        "resonance_6ad4": int(supplied.get("resonance_6ad4", 0)),
        "return_centre_6b62": int(supplied.get("return_centre_6b62", 0)),
        "filtered_36682": int(supplied.get("filtered_36682", 0)),
    }


# =====================================================================================================
# SECTION 4 -- ENGAGE / DISENGAGE DECIDER STATE MACHINE  (the "engage SM")
# =====================================================================================================

def engage_decider(st: EpsState, cal: Calibration) -> int:
    """
    Decide whether LKAS is allowed to deliver this tick, and (if not) why. [VERIFIED] Dispatcher
    FUN_000413ae (state gp-0x67DC) via sibling RTOS task FUN_00022ca0; decider FUN_00040d58 -> verdict
    r12 (disengage hook @0x40e64); consensus helper FUN_000406ae (gp-0x6cc4). Verdict codes: 0=pass,
    2=torque-MAX gate (dec_torque_max, stock 320), 4=angle-consensus, 5=rate gate (dec_rate_gate,
    1600), 6=gate6 (4096), 7=gate7 (3584). The torque-MAX gate (verdict 2) fires ~10 Hz BENIGN and is
    NOT the gentle-EME trigger (V33's raise of dec_torque_max chased the wrong gate) -- the felt gentle
    cut is produced by the debounce SM (Section 5), not here. [OPEN] gp-0x6809 is dead code (0
    writers), so which verdict actually zeroes the motor term is unlocated.
    """
    if st.col_torque_max == 0xFFFF:
        st.decider_verdict = 2        # invalid-sensor sentinel (kept live in V37)
    elif st.col_torque_max >= cal.dec_torque_max:
        st.decider_verdict = 2        # torque-MAX refusal (benign ~10 Hz; NOT the felt cut)
    elif st.col_rate_mag >= cal.dec_rate_gate:
        st.decider_verdict = 5        # rate refusal
    else:
        st.decider_verdict = 0        # pass
    return st.decider_verdict


# =====================================================================================================
# SECTION 5 -- STEER TORQUE ARBITRATION  (setpoint limit + LKAS gain)  with the two inlined SMs
# -----------------------------------------------------------------------------------------------------
# This one function is the crossroads: it limits the LKAS setpoint by a mode/gear LERP curve, applies
# the LKAS gain+clamp in Q15, and inline hosts two counters off the same torque channel -- the
# STEER_STATUS debounce SM (gentle EME, fixed V37) and the DTC-0x49 fail counter (dash lights, fixed
# V37). Driver-assist is NOT summed here; it merges downstream as a separate mixer source (Section 6).
# =====================================================================================================

def steer_status_debounce_sm(arb_torque_byte: int, rate_mag: int, st: EpsState, cal: Calibration) -> None:
    """
    The GENTLE-EME producer: a 5-cycle debounce that raises STEER_STATUS=4 (NO_TORQUE_ALERT_2).
    [VERIFIED] Inlined in m_steer_torque_arbitration (~0x29120-0x2931e); FUN_0002a30e/FUN_0002a93a are
    dead out-of-line copies, never executed. Signals: arb_torque_byte = gp-0x682f = min(|arb
    signal|>>5, 255) (@0x29068); rate_mag = clamped angular-rate magnitude (<=65535). Counter gp-0x6757
    (signed) seeded at -deb_count_seed(5), fires STEER_STATUS=4 after 5 sustained qualifying cycles,
    holds deb_hold_seed(100) cycles; all compares are unsigned `cmp;bh`. The qualifying envelope (any
    of 7 tiers true) approximates "moderate torque AND moderate rate together are dangerous even if
    neither is extreme alone"; V37 raises all 7 thresholds to unsigned max so no tier can ever fire,
    and this cut STOPPED on-car (operator-confirmed 2026-07-14).
    """
    qualifies = (
        arb_torque_byte > cal.deb_torque_rise                                             # torque alone (rise)
        or rate_mag > cal.deb_rate_primary                                                # rate alone
        or (arb_torque_byte > cal.deb_torque_and_hi and rate_mag > cal.deb_rate_and_hi)   # combined tier A
        or (arb_torque_byte > cal.deb_torque_and_lo and rate_mag > cal.deb_rate_and_lo)   # combined tier B
    )
    # hold tier uses deb_torque_hold(96) hysteresis once already firing -- folded in here for the model
    if st.steer_status == 4:
        qualifies = qualifies or arb_torque_byte > cal.deb_torque_hold

    if qualifies:
        st.deb_counter += 1
        if st.deb_counter >= 0:                # started at -5; reaches 0 after 5 sustained cycles
            st.steer_status = 4                # gentle EME: openpilot sees NO_TORQUE_ALERT_2 on CAN 399
            st.deb_counter = min(st.deb_counter, cal.deb_hold_seed)
            # ---- IN-CODE INTERLOCK (the V36 regression, the V37 fix's reason to exist) ----
            # Every STEER_STATUS=4 branch also zeroes the DTC-0x49 counter. In stock this is the ONLY
            # thing that keeps the DTC counter from saturating on a hard loaded curve.
            st.dtc49_counter = 0
    else:
        st.deb_counter = -cal.deb_count_seed   # reset the debounce
        if st.steer_status == 4:
            st.steer_status = 0


def dtc49_fault_counter(arb_torque_byte: int, st: EpsState, cal: Calibration) -> None:
    """
    The SECOND counter on the same torque channel: the DTC-0x49 fail counter (dash-lights path).
    [VERIFIED] Inlined in m_steer_torque_arbitration (gate reads @0x2920a/0x2921c, fire @0x291b8 ->
    jarl FUN_00016de6(0x49) + STEER_STATUS=7); counter gp-0x6758 increments while torque >
    dtc49_torque_gate(112), saturating at dtc49_saturation(100 = 50+50 cyc, ~1s @ ~100Hz); interlocked
    to zero by every STEER_STATUS=4 branch (see steer_status_debounce_sm). V36 raised the debounce
    thresholds so STEER_STATUS=4 never fired, so the interlock never ran and this counter free-ran to
    DTC 0x49 + STEER_STATUS=7 (dash lights, openpilot drops LKAS) -- V37's fix raises
    dtc49_torque_gate 112->255 so the counter can never increment.
    """
    if arb_torque_byte > cal.dtc49_torque_gate:
        st.dtc49_counter += 1
        if st.dtc49_counter >= cal.dtc49_saturation:
            st.dtc_0x49_set = True     # FUN_00016de6(0x49) -- confirmed DTC, dash MIL
            st.steer_status = 7        # openpilot treats 7 as steerFaultPermanent -> LKAS drops
    else:
        # NOTE: no decrement here -- stock relies on the STEER_STATUS=4 interlock to reset it.
        pass


def steer_torque_arbitration(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    Limit the LKAS setpoint, apply the Q15 gain/clamp, and run the two inlined SMs (driver assist is
    NOT merged here -- it joins downstream, Section 6). [VERIFIED] FUN_00028ea6 /
    m_steer_torque_arbitration, called from w_steer_control_task @0x22522, state-gated (andi 0x930,
    states {4,5,8,11}); limits setpoint gp-0x69ae via mode/gear LERP curves (0xC9A88..0xCBC34 ->
    0xE4xxx); applies gain tp+0x746c(0xC646C)=891 and clamp tp+0x71b4(0xC61B4)=512 as (term * gain) >>
    15 (Q15, not Q10 -- a real >>10 nearby belongs to an unrelated IIR blend); a high-torque branch
    @0x29a78 swaps in a cutoff above the same 112 gate V37 raises; writes gp-0x6b3c multiplicatively
    gated by mode gp-0x67a4 in {2,3}; feeds gp-0x682f to both inlined counters. No driver-assist term
    is added here (disasm-confirmed): the two adds feeding the store are both internal
    setpoint-descended terms.
    """
    # 1) mode/gear LERP limit on the LKAS setpoint. [VERIFIED @0x28fc8-0x29044] index=gp-0x674e into
    #    pointer array 0xCB844 -> curve @0xE4180; mode-0 value row is CONSTANT 15360, so the full-scale
    #    setpoint (0x4000=16384) IS clipped ~6% at the top end. (Only mode 0 byte-dumped; other modes
    #    open.) Modelled as the flat mode-0 limit.
    limited = _clamp(st.lkas_setpoint, -cal.arb_setpoint_limit, cal.arb_setpoint_limit)

    # 2) apply the LKAS output gain in Q15 (>>15), then a symmetric +/-arb_output_clamp. [VERIFIED] At
    #    full scale V850 `sar` yields +417/-418, both below 512, so stock never hits the clamp (an
    #    earlier >>10 reading was ~13370, 26x over the clamp, and was wrong).
    lkas_term = (limited * cal.lkas_output_gain) >> 15
    lkas_term = _clamp(lkas_term, -cal.arb_output_clamp, cal.arb_output_clamp)

    # 3) the arb command is a STANDALONE LKAS-descended signal -- NO driver-assist add here [VERIFIED,
    #    REFUTED the old `+ assist`]. Assist merges as a separate mixer source downstream (Section 6).
    arb_signal = lkas_term

    # 4) the internal torque channel the two inlined SMs watch: gp-0x682f = min(|arb signal|>>5, 255)
    arb_torque_byte = min(abs(arb_signal) >> 5, 255)

    # 5) high-torque arbitration branch (@0x29a78): a cutoff above the same 112 gate V37 raises
    if arb_torque_byte > cal.dtc49_torque_gate:
        arb_signal = arb_signal            # (V9/V31: high-torque CUTOFF taken here; V37: full interp)

    # 6) run BOTH inlined state machines on this tick's torque byte (order as in the firmware)
    steer_status_debounce_sm(arb_torque_byte, st.col_rate_mag, st, cal)  # gentle EME
    dtc49_fault_counter(arb_torque_byte, st, cal)                        # DTC-0x49

    st.arb_command = arb_signal            # -> gp-0x6b3c (0xFEDF14C4)
    return st.arb_command


# =====================================================================================================
# SECTION 6 -- LIMIT/PACK -> DISTRIBUTE/CLAMP -> MIXER -> GATE  (the fixed-clamp cascade)
# =====================================================================================================

def limit_distribute_mixer_gate(st: EpsState, cal: Calibration) -> int:
    """
    Carry the arbitration command through the per-lane clamp cascade to the LKAS lane output.
    [VERIFIED] limit_and_pack FUN_0002b422 (clamp +/-tp+0x71b2/0xC61B2) -> distribute FUN_00025c32
    (per-lane clamps +/-0x4000/0x2800/0x384/0x4E20, LKAS rides +/-0x2800) -> mixer FUN_00026c80
    (cross-lane sum into gp-0x3d70..3d98, LKAS final clamp +/-0x2800 -> gp-0x6b4c) -> gate
    FUN_00042ac6 (|x|<=0x2800 ? x : 0x7FFF sentinel -> gp-0x6afe). This whole stage stays
    LKAS-internal: the mixer sums ~11 LKAS-internal distribute sources (LKAS itself is source index 1)
    into gp-0x6b4c; base driver-assist joins ONE STAGE LATER, at the demand aggregator FUN_0003aa2c
    (Section 6B), where gp-0x6b4c is summed with gp-0x6bbe and ~8 sibling lanes into gp-0x6b94. The
    gate's 0x7FFF sentinel is deliberately out-of-range so the shaper's own range-check later
    collapses it to 0.
    """
    packed = _clamp(st.arb_command, -cal.pack_output_clamp, cal.pack_output_clamp)   # limit_and_pack (LKAS=idx 1)
    # distribute + mixer: the LKAS lane accumulates its ~11 LKAS-INTERNAL channels only (NO base
    # assist here), then the lane is clamped to +/-0x2800 before the gate.
    lkas_lane = _clamp(packed, -cal.distribute_lkas_lane_clamp, cal.distribute_lkas_lane_clamp)
    # gate: pass within the window, else emit the 0x7FFF sentinel
    if abs(lkas_lane) <= cal.mixer_gate_clamp:
        st.mixed_command = lkas_lane
    else:
        st.mixed_command = 0x7FFF            # sentinel -> shaper will zero it
    return st.mixed_command                  # -> gp-0x6b4c, the LKAS lane into the aggregator


# -----------------------------------------------------------------------------------------------------
# SECTION 6B -- MOTOR TORQUE DEMAND AGGREGATOR  (where LKAS and BASE ASSIST finally meet)
# -----------------------------------------------------------------------------------------------------

def motor_torque_demand_aggregator(st: EpsState, lanes: dict, cal: Calibration) -> int:
    """
    Sum every torque-demand lane -- LKAS and base assist alike -- into the single shared command.
    [VERIFIED] FUN_0003aa2c (0x3aa2c-0x3ad70) reads gp-0x6b62 (return-centre), gp-0x6b4c (LKAS,
    +/-0x2800), gp-0x6ade (dead, 0 writers image-wide), gp-0x6ad4 (resonance), gp-0x6b26 (friction),
    gp-0x6bbe (boost assist), gp-0x6bd0 (damping), gp-0x6b86 (magnitude), inline r26/r24 (torque-rate),
    and FUN_00036682's filtered term. Eight of these are ZERO-type range gates (out-of-window
    contributes 0, not clipped): 6b62 +/-0x2000, 6b4c +/-0x2800, 6ade +/-0x400, 6b86 +/-0x3000, 6bbe
    +/-0x800, 6bd0 +/-0x800, 6b26 +/-0x400, 6ad4 +/-0x2800 (@0x3aa38-0x3acc4).
    🛑 ALL EIGHT ARE STRUCTURALLY VACUOUS -- MEASURED 2026-08-04, every ceiling byte-read. Each gate
    is capped by its OWN PRODUCER's ceiling at or inside its gate window, on every drive, every
    build: boost 512 vs 2048 · damping <=512 (the gp-0x6ac2 ceiling floor) vs 2048 -- ⚠ the old
    "EXACTLY 0 at creep (FactorC Y[0]=0)" holds for stock and V44-V73 but NOT for V74, which opened
    both dead zones and measured 67.4% duty at engaged creep; the gate stays vacuous either way
    because 388 is the surface max at creep · friction 511 vs 1024 · magnitude +/-0x3000 ==
    window exactly (inclusive) · LKAS +/-0x2800 == window exactly · gp-0x6ade 0 writers · resonance
    max 1024 (164-341 at the ratchet's speeds) vs 2800 · return-centre gp-0x6b62 max 5786 vs 8192.
    ⇒ THE AGGREGATOR STAGE CONTAINS NO REACHABLE HARD NONLINEARITY, joining the aggregator SUM
    (V65, 120,049 frames). The relay / limit-cycle framing for the aggregator is REFUTED -- do not
    re-propose it. [EVIDENCE] ★ FUN_00036388's own counters give ~20-40 ms or ~1 s periods, nowhere
    near 7.8 Hz ⇒ it INHERITS the ratchet, it does not GENERATE it.
    ★★★ AND THE RATCHET'S Q IS NOW MEASURED: Q ~= 40 at f0 = 7.793 Hz (route 50, one 12.81 s
    provoked episode), confirmed by a WINDOW-CAP INVARIANCE TEST -- 39.0 at cap 54, 40.0 at cap 111,
    where a window-limited estimate would have doubled. ⇒ zeta ~= 0.0125, ~3x more lightly damped
    than the 21 Hz mode. ✅ Q ~= 40 CONFIRMS the record's Q ~= 36; the ONLY thing superseded is
    "Q is not measurable at NFFT 256" -- the claim it could not be measured, not the value.
    ✅ And it is measured on the RIGHT data: the episode reconciles with the transition trace below
    (2 x 2,452 = 4,904 ~= 4,894; speed span = the post-engagement window, NOT the operator's
    cranking), so it is not contaminated by driver input. ⚠ ONE episode, and f0 drift inside the
    window would DEFLATE it ⇒ 40 is a LOWER BOUND.
    ★★★★ THE RATCHET IS ENGAGEMENT-**REQUIRED**, AND NO BUILD IN THIS KIT HAS EVER MOVED IT.
    [EVIDENCE 2026-08-04] Grip confound removed (BOTH arms hands-off, |lowpass(tq,3Hz)| <= 300, creep
    < 4 m/s), pooled over four routes/builds: engaged hands-off 73/88 = 83.0% vs manual hands-off
    0/118 = 0.0%, Fisher p = 3.8e-41 -- ZERO hits in 118 manual hands-off creep windows / 302 s.
    Per-build rate 80/81/79/94% (V70/V69/V62/V59) => BUILD-INDEPENDENT. This SUPERSEDES the earlier
    "engagement-conditional, 44/46 windows" statement.
    ★ Converse: a hand on the wheel SUPPRESSES it while engaged (V59 94->14%, p=3.5e-4; V69 81->37%,
    p=4.5e-3). ★★ Transition trace at constant speed (6-9 Hz Butterworth, sosfiltfilt): lat 0.06 /
    effort 320 -> 134 counts, then lat 0.31 / effort 441 -> 1,179 counts -- 8.8x in 0.7 s with speed
    FALLING 1.75 -> 1.60 m/s; the death is effort 1,548 -> 2,129 over 0.6 s collapsing 910 -> 273.
    🛑 CORRECTION TO THE OPERATOR'S FRAMING, and it corroborates rather than contradicts him: his hard
    MANUAL provocation produced NO ratchet at all (6-9 Hz p-p 422-797, prominence 1-6). The manoeuvres
    SET UP the condition (creep, loaded wheel, LKAS about to take over); the ratchet fires WHEN LKAS
    ENGAGES AND HE LETS GO. Both parts of his account are right; the causal order is reversed.
    ★★ Two consequences: 0x454FE is a GENUINELY UNTESTED lever for the ratchet (absent from all four
    measurements -- V59/V62/V69/V70 are post-V53 and stock there); and engagement-required +
    hands-off-conditional + Q ~= 40 + base-assist damping exactly ZERO below ~35 km/h fuse into
    "AT CREEP THE DRIVER'S HAND IS THE ONLY DAMPING IN THE SYSTEM".
    ⚠ THE LEVER THIS RE-OPENS: base-assist damping is EXACTLY ZERO below ~35 km/h (the FactorC row
    above) while the ratchet lives at 4.9-8.0 km/h with Q ~= 40 -- and V47 raised FactorC AND FactorE
    together and reported "marginally quieter at 5 mph", filed null against the 21 Hz vibration.
    That positive whisper has never been evaluated against the RATCHET. Deferred to V72.
    ⚠ Note the overlap with GATE 3: the resonance row (164-341 reachable vs a 2800 window) is the
    same arithmetic that made V69's bit4 vacuous. A gate's width says what the CONSUMER accepts; it
    says nothing about what the PRODUCER can emit.
    r24/r26 are instead
    SATURATING CLIPS to +/-0x2000 (`cmovle`, @0x3ab82-94/@0x3ac42-54), summed ungated -- the lowest
    discontinuity risk of the group, consistent with V39's r24 suppression not moving the on-car
    vibration. Add order @0x3acc8-0x3ace6: r26+r24 -> +6b86 -> +6bd0 -> +6bbe -> +6b26 -> +[6b62/6ade]
    -> +6ad4 -> +filtered (FUN_00036682). The output clamp @0x3acf0-0x3ad2a is a true SATURATING clamp
    (not a zeroing gate) to +/-0x2800, lockstep-checked at gp-0x4ce0 on all three paths (mismatch, not
    saturation, trips FUN_0006b9fa) -- so the aggregator output is not itself a chatter source.
    [VERIFIED 2026-08-04] ** BOTH INLINE LANES ARE MIRRORED TO RAM, POST-CLAMP, AND NOTHING READS
    THEM: ** st.h r26 -> gp-0x6adc @0x3AD4E and st.h r24 -> gp-0x6ada @0x3AD5A, each 0 readers /
    1 writer image-wide (V64.gp_access_census, two decoders). They are free, blast-radius-zero
    telemetry taps on the exact quantity the rate-lane builds scale -- V69's probe reads gp-0x6ada.
    Note the ld.h/st.h one-bit trap: gp-0x6ada's only real instance IS the st.h form (opcode 0x3B)
    and carries the same displacement halfword as the ld.h (0x39) a probe must emit. A
    REDUCED mode exists (gp-0x67ac==1 selects LKAS+s62 only, skipping 6 sibling lanes + r24/r26 + the
    filtered term) but is UNREACHABLE on the A160: its selector traces to distribute's per-source TYPE
    array gp-0x61a0 (mirrors cal tp+0x5124/0xC4124), which on this ROM is (0,0,5,0,5,5,0,0,0,5,0) and
    never matches the qualifying literals {2,3,4} -- so gp-0x67ac is always 0 and the FULL path always
    runs; keep the 0xC4124 guard in every build regardless. Scheduled from w_steer_control_task
    @0x2291e, state-gated (andi 0xc30, states {4,5,10,11}). Writes sum -> clamp -> gp-0x6b94,
    lockstep-shadowed at gp-0x4ce0 -- the same variable the governor chain consumes. LOAD-BEARING
    CONSEQUENCE: every base-assist lane joins LKAS here, before the first governor/compensation/shaper
    stage, so a soft-EME event can feel like broad power-assist loss, not just LKAS easing.
    """
    s62 = _range_gate(lanes["return_centre_6b62"], 0x2000)
    lkas = _range_gate(st.mixed_command, 0x2800)
    dead = 0                                             # gp-0x6ade: no writers image-wide

    st.direct_rate_guard_fired = False
    if st.aggregator_reduced_mode:
        total = lkas + dead + s62
    else:
        inline_a = _clamp(lanes["inline_a"], -0x2000, 0x2000)
        inline_b = _clamp(lanes["inline_b"], -0x2000, 0x2000)

        # V39 experimental patch: suppress the verified direct derivative lane for both signs. The
        # strong-driver check fails open on the 0xFFFF invalid-voter sentinel. r26 and every downstream
        # governor/shaper/protection path remain live; this is a narrow high-frequency-ripple experiment.
        # Firmware hook: 0x3ac78 -> cave 0xc4b34..0xc4b5f -> return 0x3ac7c.
        if (cal.suppress_direct_torque_rate_assist
                and st.col_torque_max < cal.dec_torque_max
                and abs(lkas) >= cal.direct_rate_lkas_threshold):
            st.direct_rate_guard_fired = inline_b != 0
            inline_b = 0
        st.assist_inline_b = inline_b

        magnitude = _range_gate(lanes["magnitude_6b86"], 0x3000)
        damping = _range_gate(lanes["damping_6bd0"], 0x0800)
        boost = _range_gate(st.assist_lane, 0x0800)
        friction = _range_gate(lanes["friction_6b26"], 0x0400)
        # The 0xC6AF0 LERP scales the lane's own output ceiling BEFORE the aggregator's range gate.
        # Modelled as a Q15 scale on the lane value, which is equivalent for the mute case that
        # matters (bound 0 -> lane 0) and for the unity case that is live on every build to date.
        resonance = (lanes["resonance_6ad4"] * cal.resonance_lane_output_bound_q15) >> 15
        resonance = _range_gate(resonance, 0x2800)
        filtered = lanes["filtered_36682"]

        # Exact instruction order at 0x3acc8..0x3ace6.
        total = inline_a
        total += inline_b
        total += magnitude
        total += damping
        total += boost
        total += friction
        total += s62
        total += resonance
        total += lkas
        total += dead
        total += filtered

    st.non_lkas_sum = total - lkas
    st.demand_sum = _clamp(total, -cal.distribute_lkas_lane_clamp, cal.distribute_lkas_lane_clamp)
    return st.demand_sum                     # -> gp-0x6b94, then governor -> shaper -> gp-0x6b98


# -----------------------------------------------------------------------------------------------------
# SECTION 6C -- MOTOR-RATE ADAPTIVE GOVERNOR  (gp-0x6b94 -> gp-0x6ace -> gp-0x6acc)
# -----------------------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------------------
# MOTOR-RATE ADAPTIVE CAP -- exact byte layout. [VERIFIED against _v38_plain_image.bin]
# Bank A (the tp-addressable one the app reads): header+X+Y at tp+0x620C/0xC520C (22 bytes: u16
# count=5, X[5], Y[5]), Q13 slopes at tp+0x6030/0xC5030 (8 bytes), shift tp+0x6160/0xC5160=13; a
# byte-identical second copy at 0xC5224/0xC5038. Two further byte-identical banks exist (B @0xF9E0C/
# 0xF9C30, C @0xFAA0C/0xFA830) but are NOT reachable from app tp -- role [OPEN].
# The two bank-A copies are a PURE DUPLICATE STORE, not independent recomputations (FUN_0007b022
# stores one locally-computed register to both copies back-to-back, same opcode halfword) -- hard-
# fault index 0x17 can only fire on cross-cycle RAM divergence, never from a calibration edit to
# either copy. Bank A sits inside the CRC chain's one gap [0xC5000,0xC6000), so it needs NO CRC
# recompute; banks B/C are inside the untouched [0xF9000,0xFCFFC) block. No float mirror exists for
# any of these values.
# ---------------------------------------------------------------------------------------------------
GOVERNOR_RATE_X = (1050, 1700, 2500, 3700, 4100)
GOVERNOR_RATE_Y = (5325, 3584, 2406, 1587, 512)
GOVERNOR_RATE_SLOPE_Q13 = (-21940, -12059, -5593, -22021)
GOVERNOR_RATE_SHIFT = 13                     # tp+0x6160 (0xC5160)


def a160_governor_rate_cap(axis_z: int, ys=None, slopes=None) -> int:
    """Exact fixed-point A160 adaptive-cap table used by FUN_0007b022.

    `ys`/`slopes` default to the stock table. Pass a build's own rows to model a flattened cap --
    note the firmware evaluates Y[i] + ((z - X[i]) * slope >> 13), so a flat Y with non-zero slopes
    would STILL interpolate. V40 therefore zeroes both.
    """
    ys = GOVERNOR_RATE_Y if ys is None else tuple(ys)
    slopes = GOVERNOR_RATE_SLOPE_Q13 if slopes is None else tuple(slopes)
    z = int(axis_z)
    if z <= GOVERNOR_RATE_X[0]:
        return ys[0]
    if z <= GOVERNOR_RATE_X[1]:
        i = 0
    elif z <= GOVERNOR_RATE_X[2]:
        i = 1
    elif z <= GOVERNOR_RATE_X[3]:
        i = 2
    elif z < GOVERNOR_RATE_X[4]:
        i = 3
    else:
        return ys[-1]
    value = ys[i] + (((z - GOVERNOR_RATE_X[i]) * slopes[i]) >> GOVERNOR_RATE_SHIFT)
    return _clamp(value, -32767, 32767)


def rate_cap_binding_analysis(cal: Calibration, assist_counts: int = 0) -> dict:
    """
    Does the motor-RATE adaptive cap bind on the LKAS path for this build, and from what rate?
    [VERIFIED] The cap's axis is motor resolver electrical-angle rate (not road speed), falling
    5325->512 over z = 1050-4100 with a 512 floor. Stock V9's max LKAS demand (417) sits below that
    floor and can never be capped; V31 (835) binds from z~3980, V38 (1782) binds from z~3414 (with
    base assist in the aggregate, z~2229). Because the aggregate is capped before the motor responds,
    raised-reach builds close a relaxation-oscillator loop (torque applied -> motor accelerates -> z
    rises -> cap falls -> torque cut -> motor decelerates -> z falls -> cap rises -> torque restored
    -> repeat), whose signature (moving-only, worst on fast steering motion, road-speed-independent,
    absent when the driver supplies the torque) matched the on-car ratchet report -- V38 is the first
    build whose LKAS-path demand clears the 512 floor by a wide margin, explaining why no prior build
    showed it. [INFERRED] that the loop actually oscillates on-car at the observed frequency (needs
    plant inertia this model lacks). CALIBRATION WARNING: this cap is a genuine motor thermal/
    mechanical protection, rate-scheduled (not thermal-triggered) -- any change must be a measured
    raise of the taper's low end, never a wholesale flattening, and must be scored against motor
    thermal behaviour.
    """
    lkas_max = min((cal.arb_setpoint_limit * cal.lkas_output_gain) >> 15, cal.arb_output_clamp)
    demand = lkas_max + int(assist_counts)
    binds_from = next(
        (z for z in range(0, 9000)
         if a160_governor_rate_cap(z, cal.rate_cap_y, cal.rate_cap_slope_q13) < demand),
        None,
    )
    return {
        "build": cal.build,
        "lkas_max_counts": lkas_max,
        "demand_counts": demand,
        "cap_floor": cal.rate_cap_y[-1],
        "binds_from_motor_rate": binds_from,       # None => this build can never be rate-capped
        "can_be_rate_capped": binds_from is not None,
    }


def slew_ramp_time_analysis(cal: Calibration, assist_counts: int = 1024) -> dict:
    """
    How many governor cycles does each build need to ramp from zero to its own full demand?
    [VERIFIED] The governor's away-from-zero slew step is an ABSOLUTE count (cal 0xC6206=512 fast /
    0xC6208=205 slow), and the SLOW step is selected during a hard dynamic turn (gp-0x67f5 forced via
    the gp-0x67f4/gp-0x67f5 selector logic whenever raw driver torque diverges from the vote by >=65
    counts, or voted |torque|>=640). V38 raised the LKAS target ~4x while leaving both step cals at
    stock, so ramp time (target/step) got ~4x longer while the sign-crossing reset (zeroing the held
    value outright) stayed instantaneous -- slow build + instant collapse = a ratchet; the invariant
    V38 broke is RAMP TIME (cycles to full command), not step size. This was the leading ratchet
    hypothesis and was later CONFIRMED as a real contributor, though the state-4 governor substitution
    (V42 Change 1) is the root-cause fix that actually resolved it on-car. [OPEN] the wall-clock
    conversion (task rate contested); cycle counts here are exact, milliseconds are deliberately not
    computed.
    """
    lkas_max = min((cal.arb_setpoint_limit * cal.lkas_output_gain) >> 15, cal.arb_output_clamp)
    target = min(lkas_max + int(assist_counts), cal.distribute_lkas_lane_clamp)
    fast = cal.governor_slew_step_normal
    slow = cal.governor_slew_step_alt
    return {
        "build": cal.build,
        "target_counts": target,
        "fast_step": fast,
        "slow_step": slow,
        "cycles_at_fast_step": -(-target // fast),   # ceil
        "cycles_at_slow_step": -(-target // slow),   # the hard-turn case
    }


def gain_rescaling_invariance_analysis(cal: Calibration, op_pid_scale: float = 0.25) -> dict:
    """
    Central units argument: V38 raised the arbitration gain 0xC646C 891->3564 (4x) while the operator
    correspondingly quartered openpilot's lateral PID, restoring stock's closed-loop gain. Following
    units through setpoint=C*-4 -> lane=(setpoint*gain)>>15 -> everything downstream (calibrated in
    absolute lane counts): for the SAME physical torque, every stage DOWNSTREAM of the gain sees the
    identical stock count sequence (so no downstream absolute-count limit can bind differently than
    stock), while every stage UPSTREAM of the gain sees counts 4x closer to zero -- EXCEPT torque above
    stock's 417-count ceiling, which enters a regime that never existed before and makes downstream
    limits newly reachable. This partitions the RATCHET (large commanded torque, genuinely
    downstream-novel; the governor slew survives as a candidate, later confirmed root cause via V42;
    the motor-rate cap was falsified by V41) from the VIBRATION. [CORRECTED 2026-07-21] the vibration
    was originally assumed near-zero/upstream, but the operator reports it occurs during LARGE
    pure-LKAS commands (near V38's ceiling) and vanishes when the driver shares torque -- so it in fact
    lives in the SAME downstream-novel regime as the ratchet, not a near-zero upstream deadband; the
    earlier upstream eliminations are downgraded to UNTESTED, not re-opened as leading candidates. V39
    (r24 suppression) and V41 (motor-rate cap) are both downstream levers and both were flashed with no
    effect on the vibration regardless. [VERIFIED] the gain/setpoint arithmetic and stage ordering;
    [CONFIRMED] the PID rescale and engaged-only vibration character; [INFERRED] the partition itself,
    a units argument assuming the gain is the only V38 change relevant near zero (the source clamps,
    corridor/boost walls, and setpoint limit also moved, but none binds near zero).
    """
    stock = Calibration.for_build("V9")
    stock_max_lane = min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15, stock.arb_output_clamp)
    build_max_lane = min((cal.arb_setpoint_limit * cal.lkas_output_gain) >> 15, cal.arb_output_clamp)
    return {
        "build": cal.build,
        "gain_ratio_vs_stock": cal.lkas_output_gain / stock.lkas_output_gain,
        "op_pid_scale_applied": op_pid_scale,
        "loop_gain_vs_stock": (cal.lkas_output_gain / stock.lkas_output_gain) * op_pid_scale,
        "stock_max_lane_counts": stock_max_lane,
        "build_max_lane_counts": build_max_lane,
        # Below this lane count the downstream chain is replaying stock's own count sequence.
        "downstream_novel_above_lane_counts": stock_max_lane,
        "setpoint_shrink_factor_upstream": op_pid_scale,
        # Corrected 2026-07-21: the vibration occurs during pure-LKAS TURNING (a LARGE command), so it
        # sits in the same >stock-ceiling downstream regime as the ratchet, not upstream of the gain.
        "vibration_stage": "DOWNSTREAM of gain, above %d lane counts (same novel regime as the ratchet)"
                           % stock_max_lane,
        "ratchet_stage": "DOWNSTREAM of gain, and only above %d lane counts -- SOLVED by V42 Change 1"
                         % stock_max_lane,
        "downstream_candidates_falsified_on_car": [
            "r24 direct derivative lane (V39)",
            "r26 adaptive derivative lane (V42) -- with r24, the WHOLE Sensor-B rate family is out",
            "motor-rate adaptive cap (V41)",
        ],
        "confirmed_root_causes": ["state-4 governor substitution ratchet (V42 Change 1, fixed on-car)"],
    }


def governor_step_selector_bandwidth(cal: Calibration, tick_hz: float = 1000.0,
                                     command_counts: int = 4342) -> dict:
    """
    The governor's per-cycle slew STEP is selected by gp-0x67f5 (written only by FUN_00041eec, the
    column-torque voter): sustained driver column torque >= cal 0xC531E (1062) for cal 0xC64E7 (10)
    cycles selects the SLOW step (205, more damped); below that, or on reset, selects FAST (512, less
    damped) -- so hands-off runs ~2.5x wider bandwidth than hands-on, matching the operator's
    hands-off/hands-on discriminator direction. [VERIFIED] the selector, cals, debounce, and step
    ratio. A per-cycle slew limit is a bandwidth gate (ripple amplitude passed at frequency f is
    A_max = STEP*tick/(2*pi*f)), so this is a genuine TRANSMISSION PATH for tens-of-Hz content -- but
    [INFERRED, not established] that anything actually oscillates in that band upstream (the
    voting-loop channels feeding the slew target are OPEN). V45 (narrowing the hands-off step, cal
    0xC6206 512->205) was FLASHED and had NO EFFECT on the vibration, so this bandwidth-narrowing lever
    is now falsified as a fix, though the mechanism description stands. [OPEN] every Hz figure here
    scales with the unconfirmed 1 kHz tick assumption; cycle counts and the 2.5x ratio are
    tick-independent.
    """
    import math
    fast, slow = cal.governor_slew_step_normal, cal.governor_slew_step_alt

    def corner_hz(step, amplitude):
        return step * tick_hz / (2.0 * math.pi * amplitude)

    def max_ripple(step, f):
        return step * tick_hz / (2.0 * math.pi * f)

    return {
        "build": cal.build,
        "selector_var": "gp-0x67f5 (written only by FUN_00041eec, the column-torque voter producer)",
        "selector_threshold_cal": {"addr": "0xC531E", "value": 1062, "domain": "driver column torque"},
        "selector_debounce_cal": {"addr": "0xC64E7", "cycles": 10},
        "step_hands_off_fast": fast,
        "step_hands_on_slow": slow,
        "step_ratio": round(fast / slow, 3),
        "cycles_to_full_command": {
            "hands_off": -(-command_counts // fast),
            "hands_on": -(-command_counts // slow),
        },
        "corner_hz_at_full_command": {
            "hands_off": round(corner_hz(fast, command_counts), 1),
            "hands_on": round(corner_hz(slow, command_counts), 1),
        },
        # The decisive number: ripple amplitude transmitted at the symptom frequency.
        "max_ripple_counts_at_30hz": {
            "hands_off": round(max_ripple(fast, 30.0)),
            "hands_on": round(max_ripple(slow, 30.0)),
        },
        "tick_hz_assumed": tick_hz,
        "status": "[VERIFIED] transmission path gated by driver torque; [INFERRED] as the cause",
    }


def dirty_derivative_pole_analysis(gain: int = 64, tick_hz: float = 1000.0) -> dict:
    """
    Models the V43 edit: cal 0xC644A (tp+0x744a) 1024->64, restoring the disabled EMA pole immediately
    downstream of FUN_0003a382's raw one-sample difference (the "dirty derivative" on state gp-0x3680,
    distinct from the flat/passthrough proportional branch at 0xC6450). [VERIFIED] state_new =
    state_prev + (((target*32) - state_prev)*GAIN)>>10 has unity DC gain in real arithmetic; V850
    `sar` floors toward -infinity, so the integer fixed point is a bounded, ONE-SIDED residual of
    ~32/GAIN counts (sub-count at GAIN>=64; degenerate and must never be used at GAIN=0). No shadow/
    lockstep exists on this cal (pure-leaf function, zero jarl, no -0x4c displacement) and no float
    mirror exists (FUN_0003a382 has zero floating-point instructions); the nearby weight-32
    hard-shutdown monitor's input gp-0x6dac was traced to an independent sensor-plausibility watchdog
    (FUN_00027b0a) with no dependency on this lane, so it cannot be tripped by this edit. V43 (this
    exact cal) was FLASHED 2026-07-21 and fixed neither symptom -- the mechanism is confirmed SAFE but
    the dirty-derivative pole is FALSIFIED as the vibration's cause.
    """
    import math
    alpha = gain / 1024.0
    tau_exact = -1.0 / math.log(1.0 - alpha) if 0 < alpha < 1 else float("inf")
    fc_cycles = alpha / (2.0 * math.pi)
    deadband_state = (1024 // gain) - 1 if gain else None
    return {
        "cal": "0xC644A (tp+0x744a)",
        "stock_value": 1024,
        "proposed_value": gain,
        "alpha": round(alpha, 5),
        "tau_cycles_exact": round(tau_exact, 2),
        "corner_cycles_inverse": round(fc_cycles, 5),
        "corner_hz_if_tick_1khz": round(fc_cycles * tick_hz, 2),
        "truncation_deadband_state_counts": deadband_state,
        "truncation_deadband_target_counts": round(deadband_state / 32.0, 3),
        "dc_gain_preserved": True,
        "shadow_or_lockstep": "none in FUN_0003a382 (no -0x4c displacement; pure leaf, zero jarl)",
        "degenerate_value_never_use": 0,
    }


def vibration_hands_off_analysis(cal: Calibration) -> dict:
    """
    Computes the vibration-investigation headroom/discriminator dict as of the V42-V47 era: the LKAS
    lane is a ~1-5 Hz low-pass (gp-0x3d3c IIR) so a tens-of-Hz mode cannot be COMMANDED through it
    (constraint C1); downstream of the gain V38 replays stock's exact count sequence except above
    stock's 417-count ceiling, which pure-LKAS turning reaches (C2, see
    gain_rescaling_invariance_analysis()); and something must differ hands-off vs hands-on (C3) -- the
    soft-EME corridor arm gates off at |gp-0x6bf0|<=cal 0xC6156 (9216). [CONFIRMED, on-car, route b9]
    the mode is a lightly-damped mechanical resonance, 21.4 Hz, Q=13.6 (not a digital limit cycle: Q
    this low and ~0.23s coherence rule that out), a measured V38 regression (64x in the 20-30 Hz band
    vs pre-V38 routes, 75-314x hands-off vs assisting at matched speed), present at every speed but
    ~10x stronger at low speed. [VERIFIED] the mechanism chain gp-0x4f60 (raw Sensor-B torque) ->
    FUN_0003a382's model-vs-reality residual (a genuine PID, not cascaded lags -- see
    assist_shaping_lanes()) -> gp-0x6ad4 -> the aggregator -> gp-0x6b94, which IS the governor's slew
    target, whose STEP is driver-torque-gated (see governor_step_selector_bandwidth()) -- this
    survives the gain-rescaling invariance argument because it is sourced from a PHYSICAL sensor
    reacting to REAL delivered torque (which scales 4x with V38), not a digital replay. ROOT CAUSE
    [🛑 CORRECTED 2026-08-06: this read "[CONFIRMED, V44 restored damping]" and that is VOID under RULE 7
    -- V44 and V47 wrote modes 10/11 on a modes-24/26 car, so neither table was ever read and neither
    restored anything; they are INERT BY TABLE SELECTION, not falsified, and the FactorC/FactorE approach
    was not actually tested until V74]: the base-assist DAMPING lane FUN_00034350->gp-0x6bd0 is
    multiplied by a Q10 factor that is exactly ZERO below 2240 counts of driver torque (hands-off), and
    the firmware has no notch filter anywhere, so the resonance rings undamped hands-off and is damped
    hands-on -- V44 targeted that floor and V47 additionally targeted a second independent hands-off
    deadzone (motor-rate Factor E), both at the wrong mode. Eliminated as causes, on-car: r24 (V39), r26 (V42), the dirty-derivative
    pole (V43), the governor slew-step selector (V45), and the FUN_0003a382 Stage A carrier filter
    (V46). Eliminated analytically: the soft-EME wall/boost-latch oscillator (cannot bootstrap under
    LKAS-alone) and the governor's thermal/energy budget term (structurally unreachable). NOTE this
    thread continued past V47 -- see the module docstring's build lineage for V55/V56/V57, which
    established the mode is genuinely commanded and that muting FUN_0003a382 entirely (V56) did not
    remove it.
    """
    stock = Calibration.for_build("V9")
    v31 = Calibration.for_build("V31")

    def max_cmd(c):
        lane = min((c.arb_setpoint_limit * c.lkas_output_gain) >> 15, c.arb_output_clamp)
        return lane + 2560   # + the post-governor compensation ceiling

    return {
        "build": cal.build,
        "constraints": {
            "C1_fast": "tens of Hz; LKAS lane is a ~1-5 Hz low-pass, so NOT commandable via LKAS",
            "C2_v38_onset": "only loophole is command above stock's %d-count ceiling"
                            % min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15,
                                  stock.arb_output_clamp),
            "C3_hands_off": "corridor arm gated off when |gp-0x6bf0| <= 9216 (cal 0xC6156)",
        },
        "governor_headroom_counts": {
            "V31": v31.runtime_governor - max_cmd(v31),
            cal.build: cal.runtime_governor - max_cmd(cal),
        },
        "surviving_structures": {
            "a_marginal_downstream_limit": "a limit V38 sits against, chattered by a dynamic MIN term",
            "b_mechanical_resonance": "hands-off torsion-bar/wheel-inertia mode, excited 4x harder",
        },
        "falsified_on_car": [
            "r24 (V39)", "motor-rate cap (V41)", "r26 (V42)", "dirty-derivative pole (V43)",
            "governor slew-STEP selector gp-0x67f5 (V45, cal 0xC6206 512->205 -- narrowed bandwidth, "
            "flashed 2026-07-21, no effect)",
            "FUN_0003a382 Stage A reinforcing-carrier filter (V46, cal 0xC6450 1024->32 -- "
            "'lever A', flashed 2026-07-21, no effect)",
        ],
        "falsified_analytically": [
            "soft-EME wall / boost-latch relaxation oscillator -- wall 5120 vs command 4342-4608, "
            "cannot bootstrap under LKAS-alone (2026-07-21)",
            "governor energy/thermal budget -- threshold 5325 > structural max delivered 4762, "
            "provably unreachable (2026-07-21); RELABELED motor-rate-adaptive total-command ceiling, "
            "does not bind at the resonance's own ~139-count amplitude",
        ],
        "voided_candidate_v44_v47": {
            "name": "base-assist DAMPING lane FUN_00034350 -> gp-0x6bd0, BOTH hands-off deadzones "
                     "(Factor C driver-torque LERP Y[0], Factor E motor-rate LERP Y[0])",
            "edit": "V44 opened only Factor C (0xD27C6/0xD27DA 0->235/234); V47 additionally raised "
                    "Factor E's low breakpoints (0xD2802/04/06 mode 10, 0xD2816/18/1A mode 11 -> "
                    "700/750/800) -- both MODE 10/11 records on a modes-24/26 car",
            "status": "🛑 VOID UNDER RULE 7 (2026-08-06): this entry used to read 'leading_candidate' "
                      "with V47 as the current candidate. Neither V44 nor V47 was ever read by the car "
                      "-- INERT BY TABLE SELECTION, not falsified. The FactorC/FactorE approach was "
                      "first genuinely tested at V74 (engaged columns of all 16 rows), which measured "
                      "the damper live (67.4% duty at engaged creep) and then HARD-FAULTED in MANUAL, "
                      "where its records are byte-stock -- see SECTION 3B",
            "see": "assist_shaping_lanes()",
        },
        "elimination_downgraded": "motor torque ripple -- the damping confound, see docstring",
    }


def arb_deadband_relative_width(cal: Calibration, op_pid_scale: float = 0.25,
                                deadband_ivar34: int = 102) -> dict:
    """
    Models the PRE-GAIN deadband + sign-consistency gate inside arbitration (FUN_00028ea6,
    0x2a1ae-0x2a206, before the polarity*gain multiply): if cal 0xC64A3==1 (sole reader) AND
    gp-0x6806==0, values with |iVar34|<=cal 0xC61B8 (=102, MIXED ld.h/ld.hu read -- keep any edit in
    0..32767) are forced to 0, and a sign-mismatch vs the previous cycle (gp-0x6b30, 2 refs
    image-wide) also forces 0; the result is then scaled by ramp-gain gp-0x69b0 (a separate 0..0x8000
    fade-in SM, NOT a torque-error integrator -- distinct from the gp-0x3d3c IIR filter, resolving a
    long-standing two-variable confusion). [VERIFIED] L=102 is a FIXED absolute threshold in the
    pre-gain domain; with the PID quartered to compensate the 4x gain, the same physical torque sits
    4x closer to zero, so the deadband occupies ~4x more of the working range -- the invariance
    argument's own predicted mechanism. The apparent self-latch (once iVar34 stores 0, does the next
    test also force 0?) is RESOLVED: the gate is enabled only during the LKAS engage ramp
    (gp-0x6806==0), and steady engaged driving holds gp-0x6806==1, making the gate INERT in steady
    state. STEER_STATUS 4 and 7 are separately proven unreachable on V37/V38, leaving ST=3 (the
    low-speed lockout, releasing at ~3 mph, CONFIRMED sustained not chattering across 98k frames) as
    the only surviving trigger -- so this candidate is either DEAD (if the felt vibration is sustained
    at a steady speed, gate inert) or ALIVE (if it is transient just after pulling away, when the
    ~993-cycle ramp-up holds the gate open through the 4-6 mph window). [OPEN] which of the two the
    operator's report actually is -- the single question that decides this candidate. Separately,
    gp-0x6752 (assist polarity) is confirmed a static per-variant boot constant, refuting a
    "chattering sign multiplier" hypothesis.
    """
    stock = Calibration.for_build("V9")
    # Illustrative only: assumes iVar34 scales linearly with the setpoint, which is plausible for a
    # LERP-blend + linear IIR but is NOT verified. Do not quote as a firmware fact.
    stock_span = stock.arb_setpoint_limit
    build_span = cal.arb_setpoint_limit * op_pid_scale
    return {
        "build": cal.build,
        "deadband_ivar34_counts": deadband_ivar34,
        "enable_cal": "0xC64A3 = 1 (sole reader image-wide)",
        "threshold_cal": "0xC61B8 = 102 (MIXED ld.h / ld.hu -- keep any edit in 0..32767)",
        "stock_effective_setpoint_span": stock_span,
        "build_effective_setpoint_span": build_span,
        "relative_deadband_widening": round(stock_span / build_span, 2),
        "predicted_by": "gain_rescaling_invariance_analysis()",
        "blocking_question": "(A) inert / (B) pure deadband / (C) relaxation oscillator",
    }


def lkas_iir_quantization_analysis(cal: Calibration, pole_q10: int = 992, deadband_lsb: int = None,
                                   ramp_gain_q15: int = 0x8000) -> dict:
    """
    Tests whether the one-pole IIR at gp-0x3d3c inside arbitration FUN_00028ea6 (@0x2a174-0x2a1b0:
    term1=floor(507*x/1024) cal 0xC63EE, term2=floor(992*s_prev/1024) cal 0xC63EC, s=term1+term2,
    iVar34=floor((s_prev+s)/32)) can produce a limit cycle or a perceptible dead-band/stick-slip
    artifact. [VERIFIED, HYPOTHESIS DEAD] structurally no limit cycle is possible (a monotone affine
    map with 0<pole<1 cannot overshoot or oscillate; simulation confirms the internal state can enter a
    period-2 orbit but the >>5 output stage is constant through it), and the dead-band/stick-slip
    variant is also dead by enumeration + simulation (the quantisation is ordinary input rounding, not
    a pathological recursive artifact, and even the most aggressive tested ramp yields <=2 motor
    counts on V38, ~0.05% of full scale). THE REAL FINDING kept from this trace: pole 0.96875 makes
    the ENTIRE LKAS command lane a ~1-5 Hz low-pass (tau=31.5 cycles, ~unity DC gain), so a
    tens-of-Hz component CANNOT be commanded through the LKAS lane at all -- everything upstream of
    this IIR (CAN intake, setpoint, LERP cascade, openpilot's own command dynamics) is band-limited
    before reaching the gain, which eliminates an entire half of the search space and weakens (but
    does not kill -- see openpilot_command_slew_invariance()'s closed-loop-instability argument, a
    different mechanism) the STEER_DELTA hypothesis for a fast symptom. What survives: a fast
    vibration must arise DOWNSTREAM of this IIR and still be LKAS-conditional -- the standout is the
    r26 adaptive Sensor-B torque-rate lane (a derivative, so it passes exactly the band this filter
    blocks, with no deadzone unlike r24).
    """
    stock = Calibration.for_build("V9")
    pole = pole_q10 / 1024.0
    band = deadband_lsb if deadband_lsb is not None else round(1.0 / (1.0 - pole))

    def at_motor(gain):
        return band * (ramp_gain_q15 / 0x8000) * gain / 32768.0

    # UNITS TRAP: measure against a FIXED PHYSICAL TORQUE, not each build's own full scale (V38's is
    # itself 4x stock's, so dividing by it would cancel the effect being measured). With the PID
    # quartered, the same physical torque is the same lane count in both builds, so the reference is
    # held at stock's own full-scale command (417 counts).
    reference_counts = min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15,
                           stock.arb_output_clamp)
    return {
        "build": cal.build,
        "pole": round(pole, 5),
        "time_constant_cycles": round(1.0 / (1.0 - pole), 1),
        "deadband_ivar34_lsb": band,
        "step_at_motor_stock": round(at_motor(stock.lkas_output_gain), 2),
        "step_at_motor_build": round(at_motor(cal.lkas_output_gain), 2),
        "regression_factor": round(cal.lkas_output_gain / stock.lkas_output_gain, 2),
        # Ripple-to-signal at the SAME physical torque -- the only comparison that means anything.
        "reference_physical_torque_counts": reference_counts,
        "ripple_pct_at_ref_stock": round(100 * at_motor(stock.lkas_output_gain) / reference_counts, 3),
        "ripple_pct_at_ref_build": round(100 * at_motor(cal.lkas_output_gain) / reference_counts, 3),
        "survives_only_if": "the step is large enough to feel; see the docstring's kill criterion",
    }


def openpilot_command_slew_invariance(cal: Calibration, steer_delta: float = 3.0,
                                      dt_ctrl: float = 0.01, steer_max: int = 4096) -> dict:
    """
    openpilot rate-limits the steering command in NORMALIZED units, upstream of both STEER_MAX and the
    firmware gain (STEER_DELTA_UP/DOWN=3, DT_CTRL=0.01, STEER_MAX=4096, identity lookup for the
    Accord). [VERIFIED against opendbc]
    ★★★ BOTH RAILS ARE NOW MEASURED, NOT MODELLED (2026-08-06). The slew rail reads 123 counts/frame with
    ZERO frames exceeding it, which is exactly this function's 0.03*STEER_MAX term; and the AMPLITUDE rail
    is matched EXACTLY to the firmware intake FUN_00052676 = clamp(req * -4, +/-0x4000), since
    4096 * 4 = 0x4000. => RAISING STEER_MAX ALONE BUYS ZERO -- the intake clamp removes every extra count,
    so amplitude work must move both sides and the firmware side binds. 16.07% of engaged time sits against
    one rail or the other, slew dominating at highway speed. ⚠ Sibling-agent measurement, not replicated
    here; the 4096*4 identity is arithmetic. Not a licence to edit openpilot (it stays an instrument).
    Quartering the PID restored the loop GAIN but left the command
    SLEW RATE untouched: the slew ceiling in firmware lane counts is (0.03*STEER_MAX*4*gain)>>15, so it
    scales with the FIRMWARE gain -- stock 13.4 counts/10ms tick vs V38 53.5 (4x faster, uncompensated),
    cutting the time to full physical torque from ~170ms to ~42ms and crossing INSIDE openpilot's
    100ms steerActuatorDelay (stock's slow slew dominated and damped the loop; V38's fast slew lets
    the delay dominate instead -- a classic limit-cycle recipe). This is a comma-side scaling gap, not
    a firmware defect, and fits the on-car evidence (V38 onset, engaged-only, absent hands-on, worst
    at low speed, immune to firmware-only V39/V41).
    🛑🛑 THE r26 "AMPLIFIER" COUPLING BELOW IS FALSIFIED ON-CAR BY V61, 2026-07-31. It used to read:
    "It couples to r26 (the adaptive Sensor-B derivative lane) as excitation-to-amplifier: faster slew ->
    bigger column-torque derivative -> bigger r26 -> more motor torque -> more column motion -> repeat",
    and it predicted that KILLING r26 helps. V61 killed BOTH rate taps unconditionally and the grinding
    got WORSE with LKAS on AND appeared in manual driving (worst in reverse) where there was none.
    r24/r26 are +Kd*d(T_bar)/dt added IN PHASE with assist (polarity gp-0x6752 is one load @0x3AB78
    shared by both lanes and by FUN_0003a382's P-term, so it cancels; the combine chain 0x3ACC8-0x3ACDA
    is ten `add`s, no `sub`). In the closed loop that is VISCOUS DAMPING ACROSS THE TORSION BAR: for the
    wheel-inertia-on-bar mode, phi'' + (Kd*k/J_c)*phi' + k*(1/J_w + (1+K)/J_c)*phi = T_road/J_c, so the
    phi' coefficient is positive and LINEAR in Kd. At Kd=0 the mode has no damping term at all.
    ⇒ the lane is the mode's DAMPER, not its amplifier, and the direction of interest is RAISING it.
    V62 doubles it via two `sar 0xa`->`sar 0x9` immediates (0x3AC20, 0x3AB76).
    ★★★★ V62 FLASHED 2026-07-31, DRIVEN route 37 -- THE GRINDING IS FIXED. Engaged creep, speed-
    standardised, episode-clustered bootstrap: 18-22 Hz V62/V59 = 0.124 [0.036, 0.387] (8x), and
    0.024 [0.016, 0.234] at |rate| 16-32 deg/s (42x), with a 30-40 Hz negative control at ~1.0 so the
    effect is band-specific. Transient rates 0.793/0.486/0.338 at >200/>500/>1000. The kit's first
    measured fix, and it confirms the V61 gradient.

    🛑🛑🛑 AND IT IS ALSO THE CAUSE OF "GRIND #2" -- ESTABLISHED 2026-08-01 ON V65 ROUTES 3a/3b.
    The "30-40 Hz negative control at ~1.0" above is a MEAN statistic and it is blind to the
    phenomenon: the matched q99 threshold is 317 while the events are 3000-4000. Corner-conditioned
    EXTREME-TAIL maxima (creep AND |driver torque| >= 1200 AND |angle| >= 100 deg), Kd=1x vs Kd=2x,
    219 blocks:
        1-4 Hz  1.01 | 6-9  1.20 | 10-16  0.80 | 18-22  0.35 | 24-28  2.66 | 30-40  2.98
        40-49 Hz  11.71   (p = 0.0003)
    A MONOTONE FREQUENCY RESPONSE WITH A CROSSOVER AT 22-24 Hz, driver band flat as a control =>
    NOT generic roughness. ONE KNOB CUT GRIND #1 BY 2.9x AND RAISED GRIND #2 BY 11.7x.
    Reproduced independently on the COMMA IMU (40-49 Hz p95 6.27x, max 6.71x; 1-4 Hz 0.76).
    WHY: gp-0x4f62 is a 4-SAMPLE FINITE DIFFERENCE at 1 kHz (2*(x[n]-x[n-4])/4, delay cal 0xC6C42 = 4),
    so its gain RISES with frequency -- 1.93x at 41.6 Hz vs 20.9 Hz. V62's x2 is FLAT in frequency, so
    it raised the high band harder, in absolute terms, than the mode it fixed. V62's own note computed
    selectivity only against the DRIVER (1 Hz, 14.6:1) and never against a HIGHER mode.
    🛑 A FILTER CANNOT FIX IT: differentiator +20 dB/dec vs one real pole -20 dB/dec is FLAT above the
    corner, so one pole drives the 41.6/20.9 selectivity toward 1.0 and never below; two poles low
    enough to bite by 42 Hz cost -92 deg at 20.9 Hz and destroy the lead. Raising 0xC6C42 fails the
    same way (D=24 zeroes 41.7 Hz but leaves -0.3 deg at 20.9 Hz = a pure spring). Confirmed
    structurally: FUN_0007e74a has NO EMA/IIR anywhere, and gp-0x4f60 is a SINGLE physical measurement
    of driver + motor-reaction torque, so no V57-style cal fork exists either.
    => the separation must come from an OPERATING CONDITION. Driver torque separates the two symptoms
    >8x (grind #1 hands-off; grind #2 at tq_avg 1600-2700); LKAS engagement separates only grind #1
    (100% vs a 54.7% base rate, p99 6.63x, against grind #2's 84.5% and 1.33x).
    See analysis-2020accord/rate_lane_frequency_response.py and docs/V66-V67-DESIGN.md.

    ★★ THE FIX: V67 = V66 + the grind #1 fix GATED ON LKAS. Two edits, no cave:
        0x3AA96  c5 -> fb    ld.bu -0x683c[gp],r15 -> ld.bu -0x6806[gp],r15   ONE BYTE
        0xC6446  512 -> 5244                                                  ONE HALFWORD
      with BOTH sar sites left at STOCK 0xa. gp-0x683c has ONE access and ZERO writers image-wide,
      and its flag `lp` already selects cal 0xC6446 for r24 (and 0xC6444 for r26) -- so the firmware
      already HAS a conditional-gain arm and it is merely wired to a dead cell. Repointing it makes
      the gain conditional with no code cave, this kit's only bricking class.
        gate FALSE (LKAS off) -> the LERP, unchanged  => byte-for-byte STOCK base steering
        gate TRUE  (LKAS on)  -> flat 5244 = 2.00x the LERP at grind #1's operating point
                                 (creep 7.2 km/h, 128 deg/s, LERP 2622)
      Arithmetic: 5120*5244 = 26.8M = 1.25% of INT32_MAX; lane saturates at |dtorque| >= 1599 vs a
      measured 123-839. GATE 1 vacuous (read-only load displacement, no RAM claimed).
      GATE 2: the lane is a DERIVATIVE => DC-neutral, so a gain step at engagement is not a torque
      step; and the gate itself is measured below.

    ✅✅ THE GATE IS VALIDATED ON-CAR, from V57's own probe (which flew routes 28/29 in July and had
    never been correlated). `analysis-2020accord/validate_gp6806_gate.py`:
        route 29   7,924 frames /  79.2 s   99.90% agreement with latActive   0.0505 transitions/s
        route 28  29,990 frames / 299.9 s   99.94% agreement                  0.0300 transitions/s
      => gp-0x6806 != 0 IS "LKAS is applying"; it does NOT drop out during steady engaged holding
      (the one ambiguity static analysis could not close, since it is a ramp-FSM phase flag whose
      "settled" phases 5/6/7 could not be ruled out); and it toggles THREE ORDERS OF MAGNITUDE below
      the 21/45 Hz modes, so it cannot parametrically pump.

    ★★★★ V67 FLASHED AND DRIVEN 2026-08-02, route 47 (26 segs, 150,327 frames, 1,495 s, an ordinary
    street->highway->street->parking-lot commute). IT IS THE BEST BUILD THIS KIT HAS MEASURED.
      ✅ PROBE LIVE: byte4 = {0x87, 0xC7} only; bit6 == carControl.latActive in 150,302/150,327 =
         99.983% (the 25 disagreements are single-frame transition edges) => the gate is CONFIRMED
         on-car; bit5 (gp-0x671d, the masking risk that pins the gain to 1024 BELOW stock) = 0 in
         EVERY frame, as is bit4 => the arm was a clean binary. FLIGHT-CLEAN: ST==4 = 0/150,327.
      ★★ GRIND #1 FIXED, and route 47 is the FIRST route to contain BOTH doses with the arm state
         recorded per frame, so the contrast is WITHIN-ROUTE and needs no cross-route comparison:
         18-22 Hz engaged creep, cell-stratified, episode-clustered --
             ENGAGED arm     0.524 [0.337, 0.804] vs Kd=1   (1.183 [0.773, 1.617] vs Kd=2)
             DISENGAGED arm  1.055 [0.669, 1.354] vs Kd=1
         => suppression in ONE ARM ONLY, which is V67's conditional design and which no other built
         artifact produces (it is also the first evidence ever to separate V66 from V67).
         Independent orchestrator pass agrees: 0.55 [0.35, 0.65] on a monotone four-point ladder
         1.50 (Kd=0) / 1.00 / 0.55 (V67) / 0.39 (Kd=2), split-half null [0.90, 1.12].
      ★★ CREEP GRIND #2 ELIMINATED: 40-49 Hz bursts (window envelope p99 > 500; V62/V65 bursts ran
         2000-4000) -- V67 0 in 22 s engaged and 0 in 91 s manual, max 83.5/48.8, against Kd=2x's
         18 and 6 with max 1830.7/1469.6. 🛑 The arms are NOT equally supported: manual expects 3.91
         bursts, P(0) = 0.020 (solid); engaged expects 1.04, P(0) = 0.35 => UNRESOLVED. Needs a
         parking lot, not a build.

    🛑🛑 THE PREDICTED HIGHWAY COST DID NOT MATERIALISE, AND THE PREDICTION IS WITHDRAWN.
    The line that stood here read: "Grind #2 SURVIVES under LKAS, at 2.21x". The delivered multiplier
    is real and is worse than that (2.44x at highway, V67's maximum, 22% above V62's flat 2.00x --
    see ASSIST_RATE_B_RECORDS note 3). But the SYMPTOM does not follow it. With route 2b (V58,
    Kd=1.00x, 227 s of highway -- a baseline two sessions assumed did not exist) brought in, the
    three-dose highway comparison is NULL: 40-49 Hz ratios 0.970 [0.787, 1.154] and 0.938 [0.764,
    1.184] against a split-half null of [0.73, 1.37], no dose ordering, and the corpus-max highway
    envelope (851.5) is on the STOCK Kd=1.00 lane.
    🛑 CORRECTED 2026-08-03. This paragraph read "0.98 [0.71, 1.63] and 0.77 [0.56, 1.44] against a
    split-half null of [0.53, 1.86] ... and ZERO burst windows at any dose across ~1,400 s". Those came
    from an estimator that skipped the detrend + Hann taper and ran 1.4-1.9x LOW. Corrected values above.
    ✅ INDEPENDENTLY CORROBORATED: an event-RATE re-test (a different statistic, blind to the pooled
    level's weakness for rare threshold events) reaches the SAME null -- 0.855 [0.432, 1.702] and
    1.152 [0.496, 2.690] vs split-half null [0.36, 2.50], min detectable ratio 1.61x -- with BOTH
    positive controls firing: wheel order 1 at prominence 79, and grind #1's event rate falling
    monotonically with dose, 0.319 [0.130, 0.661]. Two statistics, same answer.
    Identity settled by amplitude: creep grind #2 runs f0 43-45 Hz at prominence
    48-1062x and envelope 2000-4000; the highway population runs f0 45-47 Hz at prominence ~6x and
    envelope 155-370 => NOT grind #2. What IS real at highway is BROADBAND: 21 maneuvers vs 21
    MATCHED straight-line controls give 6-9 Hz 2.78x and 40-49 Hz 2.13x -- 6-9 rises MORE.
    🛑 BOTH VIBRATION INSTRUMENTS ARE BLIND ABOVE ~50 Hz: CAN is 100.000 Hz EXACTLY (Nyquist 50.00)
    and the comma IMU is 101.02 Hz (Nyquist 50.51) -- 0.51 Hz of headroom, not usable. (An earlier
    figure of 99.9-100.5 Hz for the IMU came from the dt MEAN; ~1% of samples are dropped, so use the
    MEDIAN. Settled by a lattice fit, 77 us vs 2889 us, and a synthetic fold test where 7 of 7 known
    tones fold per 101.02 Hz.) ⇒ every highway null on THESE channels is silent about a >50 Hz event,
    and IMU/CAN agreement carries NO information about the alias -- the discriminant is a 1.021 Hz
    apparent-peak difference against a measured sem of 0.856, so it needs a log at a different IMU
    ODR (208/416 Hz).
    ⚠ THE COMMA MICROPHONE has no FREQUENCY ceiling but bears VERY LITTLE WEIGHT on a TACTILE event,
    and the operator reports FEELING rather than hearing. 🛑 CORRECTED 2026-08-03: `soundPressure` is
    ONE RMS over 1600 samples of 16 kHz PCM => 0-8000 Hz ANALYSED, level at 10.000 Hz -- this line
    previously said "audio at 16-48 kHz". The correction is load-bearing in the direction that WEAKENS
    the null: the 26.4 dB bandwidth penalty vs the ear's ~1/3-octave critical bands (18.5 Hz at 80 Hz),
    which is what downgrades this instrument, DEPENDS on the band being 0-8 kHz. Anyone reading the old
    figure will OVER-weight the null. It reads 4.14x un-weighted p95 / +9.7 dB(A) on the creep grind #2
    and ~1.0x on highway manoeuvres, but that sole positive control sits 64x above the smallest event
    the highway null excludes (25.3% excess power), and it was validated at CREEP where the floor is
    9.9x lower in power. 🛑 A-weighting is the trap (-30 dB at 50 Hz): use the UN-weighted channel.
    ⚠ Also: `_grind2_lib.fs_of()` is biased +0.5-1.4% route-dependently, so grind #2's long-quoted
    "44.9 Hz" is 44.6 Hz.
    🛑🛑 RETIRED 2026-08-03 -- this line read "at highway 40-49 Hz is WHEEL ORDER 3, 10-16 Hz is ORDER 1
    -- peak-finding in 40-49 on a highway log finds a tyre, not the mode." The order-3 half is an
    ESTIMATOR TAUTOLOGY: order = f0*CIRC/v returns ~3.00 BY ARITHMETIC whenever a band-limited argmax
    sits near the centre of 30-49.5 Hz at ~28 m/s. The order-2 figure (1.995 for 26-32 Hz) has the
    IDENTICAL defect -- band centre 29 Hz at 28-30 m/s -- so the two are one tautology counted twice,
    not mutual corroboration. THERE IS NO LINE AT ALL in 30-49.5 Hz at highway: averaged-periodogram
    prominence 1.23-3.83 against a >4 criterion, on every route, build and channel.
    ⇒ Do NOT let this discourage looking there. ✅ SURVIVING: 10-16 Hz ORDER 1 is real (prominence up
    to 79, order 1.00-1.02 per bin) and the general "do not mistake a wheel order for a firmware
    effect" warning stands, better founded. GENERAL RULE: a matching order is evidence only when the
    band is WIDE relative to the order spacing, or when the order is TRACKED ACROSS A SPEED SWEEP.
    And: AVERAGE THE PERIODOGRAMS, THEN PEAK-FIND -- a median-of-per-window-argmax estimator
    manufactures a line at band centre when none exists, and did so this session at ΔBIC 249-460.
    ⇒ KEEP V67. No control-path change is supported by this evidence.
    Reproduce: analysis-2020accord/r47_orchestrator_checks.py.

    ★★★ SUPERSEDED 2026-08-04 BY V69 -- and by a symptom this chain now explains. Routes 4c/4e
    captured the operator's highway lane-change vibration: 4e seg 33 t=51.3 s, an ALC right lane
    change at 25.93 m/s -- bar 1468 counts p-p, 26-30 Hz envelope 614 (20x the route median), lines
    at 28.12/28.51 Hz at prominence 100-107, while 40-49 Hz reads 69 IN THE SAME WINDOW. Not wheel
    order 2 (24.93) or 3 (37.40); not engine order 1 (26.10) or 2 (52.20). And "only when engaged"
    is REFUTED at 40-49 Hz (maneuver/control 2.516 [1.561,3.701] engaged vs 2.558 [1.469,3.747]
    manual) -- the engagement-conditional part is at 18-28 Hz, not grind #2's band.

    V69 (BUILT 2026-08-04, RE-CUT to x4, FLASHED, DRIVEN route 4f--61171e660d 2026-08-04) removed
    the mechanism named at item 3 above rather than trimming it. The gate branch 0x3AC04-0x3AC0C is
    cmp(2)+be(2)+ld.hu(4)+br(2) = 10 bytes with ZERO SLACK, and it REPLACES the LERP rather than
    scaling it -- so speed shaping can reach the engaged lane ONLY if the gate is off. Hence:

        0x3AA96  fb -> c5      gate REVERTS to the dead gp-0x683c (0 writers image-wide)
        0xC6446  5244 -> 512   the now-unreachable arm returns to stock
        0xD2A7E/0xD2A80  3072 -> 12288   mode-10 gain_B  0 km/h record Y[0..1]   (x4 as SHIPPED)
        0xD2ABA/0xD2ABC  2561 -> 10244   mode-10 gain_B 10 km/h record Y[0..1]   (x4 as SHIPPED)

    Delivered multiplier: 4.000x to 10 km/h -> 3.658 @15 -> 3.307 @20 -> 2.578 @30 -> 1.808 @40 ->
    EXACTLY 1.000x at and above 50 km/h, in BOTH arms. ⚠ THE x2 FIGURES THAT STOOD HERE
    (6144/5122, "2.000x ... 1.270 @40") WERE THE SPEC, NOT THE SHIP. Corrected 2026-08-04.

    ★★★★ V69 FLEW AND GRIND #1 CAME BACK -- AT CREEP, NOT AT SPEED. Route 4f, 481.7 s, 8 segs,
    flight-clean (ST==4 0/47,996 and ST==3 0, gridded AND raw 0x18F). Engaged pooled 18-22 Hz
    f0 20.42 Hz prominence 13.47 (criterion >4), f0 IDENTICAL across all 8 search bands, manual 1.25
    = no line. Order veto cleared by the engaged-vs-manual WITHIN-ROUTE speed-matched contrast --
    4.726 [1.082, 18.20] vs null [0.36, 3.24] -- which no tyre or engine order can survive.
        creep <20 km/h vs V62/r37   2.244 [1.438, 3.191] blk, 2.235 [1.533, 3.429] ep  (BOTH units)
        >= 50 km/h vs stock          1.066 [0.690, 1.677] INSIDE NULL  => LANDS ON STOCK
    ⚠ the ALL-SPEEDS headline (1.381 [1.026, 1.724] vs Kd2) loses its CI under the conservative
    episode unit; the CREEP result does not.

    ★★★ THE DOSE-RESPONSE IS NON-MONOTONE, and this is the finding:
        0x (V61) 2501 | 1x stock 879 | 2x (V62/V65) 168 | 2x gated (V67/V68) 109 | 4x (V69) 746
    median e_18-22, engaged creep. THE MINIMUM IS AROUND 2x AND V69's 4x OVERSHOT IT.
    ⚠ cross-route medians without covariate matching -- read beside the matched contrasts above.

    ★★ AND THE EFFECT IS ENGAGEMENT-CONDITIONAL THOUGH THE DOSE IS NOT. V69's 4x applies identically
    in both arms (the gate is dead), yet manual at 4x is INDISTINGUISHABLE FROM STOCK (1.070
    [0.383, 1.396], inside null) while engaged is 2.244x. => the mechanism is inside the CLOSED LKAS
    LOOP, not open-loop damping quality.

    🛑 SATURATION IS ELIMINATED AS THE CAUSE, two independent ways. (a) MEASURED: |dtorque| max
    633.9 on 4f, 0.0000% above V69's 683 rail => >=99.9% of engaged time received the FULL 4.000x;
    it is not a partially-delivered dose. (b) ARITHMETIC: stock and V69 share the SAME +-8192 clip,
    and N(A) is monotone increasing in K, so V69/stock decays toward 1.0 FROM ABOVE and never
    crosses -- minimum 1.049x over the entire reachable input domain. A rail cannot produce
    sub-stock damping. See analysis-2020accord/v70_rail_describing_function.py.

    ⚠ MECHANISM NOT UNIQUELY DETERMINED [BELIEF]. Two candidates fit the dose-response equally:
      (a) a plain derivative-feedback optimum, overshot;
      (b) PARAMETRIC GAIN COLLAPSE -- gp-0x6ac0 is loaded `ld.hu` (UNSIGNED) @0x3AAC4, so the gain
          index is a MAGNITUDE that sweeps 0 -> peak -> 0 TWICE PER CYCLE. V69 turned Honda's 2.00x
          rate rolloff into 8.00x (Y[0]/Y[1] raised, Y[2]/Y[3] left stock), making the damper
          STRONGEST at the zero-crossing and WEAKEST at peak velocity. Modulation depth within one
          cycle at A_rk 1927: stock/V62 1.49x, V69 5.96x, and V67's scalar arm EXACTLY 1.00x -- the
          arm does not merely raise the gain, it LINEARISES it, a virtue never articulated at the
          time. Effective-gain crossover below V62 at A_rk ~1300 (two independent derivations).
          See v70_parametric_gain_collapse.py and v70_surface_vs_rate.py.
    The dose-response is the EVIDENCE; the mechanism is BELIEF.

    🛑🛑 V69's OWN STATED PURPOSE FAILED. The ~26-30 Hz lane-change transient is DOSE-INDEPENDENT:
    it survived (2599 and 4094 counts p-p vs V68's 1468) and runs at FULL amplitude on the STOCK
    rate lane -- V59/r2c at dose 1.000x carries the corpus's LARGEST p-p, 3283 @27.07 Hz. Pooled
    speed-matched 2.000x/1.000x = 1.176 [0.641, 2.320] inside null; route-level Theil-Sen slope on
    dose +5.736 [-25.432, +34.934], 0 inside. ★ The live candidate is EXCITATION, not gain: within
    dose = 1.000x exactly, ALC vs driver-commanded = 2.389 [1.453, 4.898]. Holding excitation fixed
    collapsed the 2.403x contrast 2.849 -> 2.013 with its CI crossing 1 -- an excitation contrast
    wearing a dose label. => DO NOT CHASE THE RATE LANE FOR THIS SYMPTOM.

    🛑 EDIT-ORDER INVARIANT, and it INVERTS for V70: V69 asserts arm == 512 => gate byte == 0xc5.
    V70 restores the gate, so it must assert gate == 0xfb => arm == 5244. Shipping 0xfb with 512
    pins the engaged lane ~5x BELOW stock everywhere -- worse than V61, which measured worse on-car.
    🛑 NEIGHBOUR TRAP: mode 11/12's 0 km/h records are BYTE-IDENTICAL to mode 10's, so the target
    pattern occurs 3x within 40 bytes; address absolutely, never by pattern.
    See docs/V69-DESIGN.md and docs/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md.

    For the record, the pre-drive separation table (measured on V65's creep windows):
        LKAS active   98.7% / 15.7%      driver torque  96.8% / 50.5%     steering rate  81.1% / 48.5%
    ⚠ An earlier claim that driver torque separates them ">8x" is WITHDRAWN -- it compared grind #2's
    measured torque against the DEFINITION of hands-off, not against grind #1's measured
    distribution. The real figure is 1.70x (1268 vs 2158), with heavy overlap.
    🛑 gp-0x671d OUTRANKS the arm and is LIVE. If it fires, the gain is pinned to 0xC6442 = 1024,
    BELOW the stock default, and V67 becomes worse than V66. V67's probe bit5 measures it.
    🛑🛑 "0x3AB76 WAS A NO-OP / r26 IS STRUCTURALLY INERT" -- DOWNGRADED TO BELIEF 2026-08-04, AND
    HALF OF ITS ARGUMENT IS NOW REVERSED. The claim rested on TWO legs. Separate them:
      LEG 1, the GATE -- REVERSED. r26 == 0 iff gp-0x6b5e != 0, and gp-0x6b5e is a trapezoid LERP on
        gp-0x6bda, which is a MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque. Hands-off the
        margin sits ~24x above the kill threshold => THE GATE LEAVES r26 LIVE in ordinary driving and
        most strongly live in hands-off creep -- exactly where the grinds and the ratchet occur.
        See assist_gate_6b5e above for the full byte-level derivation.
      LEG 2, the MAGNITUDE -- STILL BELIEF, unresolved either way. avg's cal base 0xC6564 byte-reads
        as 40 bytes of EXACT ZERO, and no writer was found for the RAM adjustment at
        gp-0x641E..gp-0x6444 (10 of 18 cells checked) => stage1 ~ 0 IF that cal base is really what
        feeds gp-0x69a4. ⚠ THAT LINK WAS NEVER VERIFIED; gp-0x69a4's actual producer is a LIVE
        runtime 10-segment LERP at 0x355C6 in FUN_000352b4, 1 writer / 3 readers (0x355A4, 0x3575A,
        and 0x3AB3A = the aggregator).
    => "r24 carries the ENTIRE lane" is a BELIEF resting on LEG 2 alone. It may still be right, and
    one indirect argument says it is: the measured dose-response is only self-consistent if
    a = gp-0x69a4/1024 is SMALL, because at a ~ 1 the V67/V68 gate (which forces gain_A 3072 -> 512,
    a 6.00x CUT) would put their engaged TOTAL at ~0.94x stock -- essentially ON stock -- yet they
    measured the best grind #1 result in the kit (109 vs stock's 879).
    🛑 CONSEQUENCE FOR ANY GATE-RESTORING BUILD: 0xC6444 = 512 is carried by every build including
    V69, so restoring the V67 gate also restores a 6x r26 cut whenever LKAS applies.
    🛑🛑 STRUCK 2026-08-04 -- 0xC6444 IS A NULL BY CONSTRUCTION, NOT AN UNTESTED LEVER. [EVIDENCE] it
    is read ONLY at 0x3AB5E, and only when lp != 0. On every GATELESS build -- stock, V62, V65, V69,
    V70, V71 -- the gate 0x3AA96 is 0xc5, so lp derives from gp-0x683c, which has 0 WRITERS
    image-wide => that load NEVER EXECUTES. Raising it changes NOTHING unless 0x3AA96 is also
    repointed, which reintroduces the V67/V68 control path the operator rejected. => it is reachable
    only on a build whose control path is already ruled out, and THERE IS NO SINGLE-VARIABLE r26 TEST
    ON THE CURRENT TOPOLOGY. The old "genuinely untested upward (V42 tested it downward, 512 -> 0,
    FALSIFIED)" framing was correct arithmetic about the wrong question. Blast radius, kept for the
    record: 1 reader / 0 writers, no float mirror, same CRC block #48 as 0xC6446, ceiling <= 6553.
    ★ MEASURE IT, DO NOT ARGUE IT: gp-0x6adc is r26's post-clamp mirror (st.h @0x3AD4E, 0 readers /
    1 writer image-wide), the same blast-radius-free class as gp-0x6ada. Because r24 and r26 share
    ONE polarity load (ld.b -0x6752[gp],r14 @0x3AB78, reused at 0x3AB7E for r26 and 0x3AC3E for r24)
    they ALWAYS carry the same sign -- so sign(gp-0x6adc) vs sign(gp-0x6ada) is a matched pair:
    bit4 pinned at 1 while bit3 toggles => r26 is zero; bit4 tracking bit3 => r26 is live. V70 flies
    exactly that pair. This re-attribution of V42/V61/V62 stands only if LEG 2 holds.
    ⚠ The pre-committed r24 saturation caveat did NOT bind: measured dtorque is 123-839 (the route's
    most violent transient implies 739) against a clamp that needs 1820 under V62.
    ★★ V63/V64 do it BETTER: gp-0x671a is an oscillation detector (see EpsState.assist_state_671a), so
    raising only the state>=5 arms -- 0xC6440 2048->4096 and 0xC643E 1536->3072 -- adds damping only once
    an oscillation has been detected, leaving a never-oscillating drive on its stock LERP default.
    ⚠ NOT "only while oscillating": the counter is a ONE-WAY LATCH with a 5 s hold, so once tripped it
    carries into subsequent manual steering. V63/V64 is "V62, but only after an oscillation has happened".
    V64 = V63 + the cave probe repointed at the detector (0x14A byte4: bit6 state>=5, bit5 state!=0,
    bit4 FSM left neutral, bit3 r24 override), so a null is interpretable instead of ambiguous.
    See rate_lane_damping_model.py, build_v62_tva.py, build_v63_tva.py, build_v64_tva.py. Motor ripple is ruled out (hand steering
    delivers comparable torque through the same smooth output stage), which leaves the LKAS-only
    segment upstream of the aggregator -- see lkas_iir_quantization_analysis() for the standout
    stateful element there (gp-0x3d3c). PROPOSED TEST, in order: comma-side STEER_DELTA_UP/DOWN
    3->0.75 first (reversible, no flash/brick risk) before building any firmware image; if the symptom
    only softens, ~~the r26 cal kill attacks the amplifier~~ 🛑 STRUCK 2026-07-31: the r26 kill was flown
    (V42 alone, then V61 with r24) and made the grinding WORSE -- r26 is a damper, see above; the
    remaining lever on this lane is RAISING it (V62). [CONFIRMED] the PID rescale and engaged-only
    character; [INFERRED] that this loosening causes the felt vibration (a control-theory prediction,
    not yet road-tested in isolation).
    """
    stock = Calibration.for_build("V9")
    per_tick_norm = steer_delta * dt_ctrl

    def lane_per_tick(gain):
        return per_tick_norm * steer_max * abs(stock.setpoint_scale) * gain / 32768.0

    stock_rate = lane_per_tick(stock.lkas_output_gain)
    build_rate = lane_per_tick(cal.lkas_output_gain)
    stock_max_lane = min((stock.arb_setpoint_limit * stock.lkas_output_gain) >> 15, stock.arb_output_clamp)
    return {
        "build": cal.build,
        "normalized_step_per_tick": per_tick_norm,
        "stock_lane_counts_per_tick": round(stock_rate, 1),
        "build_lane_counts_per_tick": round(build_rate, 1),
        "slew_loosening_factor": round(build_rate / stock_rate, 2),
        "ms_to_stock_full_scale_stock": round(1000 * dt_ctrl * stock_max_lane / stock_rate),
        "ms_to_stock_full_scale_build": round(1000 * dt_ctrl * stock_max_lane / build_rate),
        "steer_actuator_delay_ms": 100,
        "rate_limiter_still_dominant": (1000 * dt_ctrl * stock_max_lane / build_rate) > 100,
        "compensating_steer_delta": round(steer_delta * stock.lkas_output_gain / cal.lkas_output_gain, 3),
    }


def governor_slew_0xffff_postmortem() -> dict:
    """
    Why V40 (V38 + slew cals 0xC6206/0xC6208 -> 0xFFFF) lost all power steering at ignition, while V41
    (V38 + only the cap flatten, slew untouched) boots and drives cleanly -- isolating the fault to the
    0xFFFF slew write. [VERIFIED, byte-level] Both refuted mechanisms (a signed-load -1, a signed-16
    overflow) are ruled out: the cals are `ld.hu` (unsigned, 0xFFFF=65535) and the product is provably
    bounded below 0x80000000, so no wraparound is possible. What 0xFFFF actually did: it made the slew
    guard never fire, snapping the command to target every cycle -- complete removal of rate limiting,
    not a sign error. [INFERRED] fault path: with zero filtering, at ignition the target is sensor
    noise around zero and the command chases it at full bandwidth, tripping the hard-fault-eligible,
    no-debounce monitors FUN_0004595a/FUN_00045a20 (same 0xd30 state gate as the governor) -> motor off
    + power-cycle. The defect is the MAGNITUDE of the edit, not its direction -- a moderate raise
    preserves protection. The principled value is RAMP-TIME PARITY: scale both step cals by the same
    4x V38 applied to reach (512->2048, 205->820), which V42 uses; this addresses the RATCHET only and,
    per gain_rescaling_invariance_analysis(), cannot touch the speed-independent vibration.
    """
    return {
        "v40_fault": "EPS lamp + total loss of assist at ignition",
        "attributed_to": "0xC6206/0xC6208 <- 0xFFFF",
        "exonerated_by_v41": ["motor-rate cap flatten", "stale 0xC5FFC CRC"],
        "refuted_mechanisms": ["signed load -> -1 (cals are ld.hu)",
                               "signed-16 overflow (guard is self-bounded; product < 0x80000000)"],
        "actual_effect_of_0xffff": "guard never fires -> snap-to-target -> zero rate limiting",
        "inferred_fault_path": "unfiltered command -> FUN_0004595a / FUN_00045a20 (same 0xd30 state "
                               "gate as the governor) -> FUN_00016de6(0x1d) -> hard-eligible, no "
                               "debounce -> motor off",
        "cal_readers_image_wide": {"0xC6206": 1, "0xC6208": 1},
        "arithmetically_safe_range": "0..65535 (no wrap possible); the limit is BEHAVIOURAL",
        "snap_to_target_threshold": "step approaching TARGET magnitude (~4762) collapses to 1 cycle",
        "ramp_time_parity_steps": {"0xC6206": 512 * 4, "0xC6208": 205 * 4},
        # A slew raise cannot touch the vibration: that symptom is speed-independent and sits
        # DOWNSTREAM of the LKAS-lane low-pass, which this cal is upstream of.
        "addresses_symptom": "hard-turn ratchet only",
        "caveat": "ratchet attribution now depends on the UNRESOLVED task rate -- see EXECUTION MODEL",
    }


def computed_runtime_governor(sensors: SensorInputs, cal: Calibration) -> int:
    """Model gp-0x4f64 without inventing the still-unresolved axis normalization or budget formula."""
    if sensors.runtime_governor_override is not None:
        return _clamp(int(sensors.runtime_governor_override), 0, 0xFFFF)

    adaptive = cal.runtime_governor
    if sensors.governor_axis_z is not None:
        adaptive = min(adaptive, max(0, a160_governor_rate_cap(
            sensors.governor_axis_z, cal.rate_cap_y, cal.rate_cap_slope_q13)))

    # Motor states 0 and 2 use the nominal-capped adaptive result. Other states add the B minimum.
    if sensors.governor_motor_state in (0, 2):
        return adaptive
    budget = (cal.runtime_governor if sensors.governor_budget_limit is None
              else max(0, int(sensors.governor_budget_limit)))
    return min(cal.runtime_governor, adaptive, budget)


def motor_torque_governor(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    Applies FUN_0004503c (Q15-scaled symmetric clamp + second Q15 scale + 512/205-calibrated
    asymmetric slew, writing gp-0x6ace) then FUN_000456a4 (adds gp-0x6ad0, writes gp-0x6acc, read by
    the shaper). [VERIFIED] Motion away from zero is capped to HELD+/-STEP; motion toward zero, or a
    sign-crossing, is immediate (a sign-crossing also zeroes HELD). STEP is selected by gp-0x67f5 (see
    governor_step_selector_bandwidth()): the fast 512 step applies only when the driver holds steady
    AND below 640 counts, so a hard dynamic turn pins the slow 205 step -- combined with V38's ~4x
    larger target, ramp time (target/step) grew ~4x while the sign-crossing reset stayed instant,
    producing a ratchet (see slew_ramp_time_analysis()). ROOT CAUSE, CONFIRMED ON-CAR (V42 Change 1):
    while gp-0x67fa (ECU state) == 4, FUN_0004503c substitutes the fresh governed value with a
    rate-shaped version of the PERSISTED previous value (gp-0x138a) whenever |fresh| > |previous|,
    then unconditionally writes the (possibly suppressed) result back as next cycle's baseline -- a
    genuine, cumulative, self-sustaining ratchet, not a one-shot clamp. State 4 is reachable mid-drive
    (non-diagnostically, via two ordinary 5->4 and 10->4 transitions gated on torque/plausibility
    flags) and no calibration-only fix exists (the branch reads no cal; the decision is unconditional
    once state==4). The fix is a single condition-code nibble at 0x454fe (`bne`->`br`), unconditionally
    skipping the substitution; PROVED SAFE BY CONSTRUCTION because the slew's asymmetric structure
    guarantees |output|<=|target| with matching sign in every branch regardless of HELD, so the
    hard-fault monitor FUN_0004595a cannot trip. [VERIFIED] the control task FUN_0002214a runs at
    ~1000 Hz (OSTM0 79999-count reload at ~80 MHz, cross-checked by the STEER_STATUS=4 dwell cal
    0xC64DF=100 measuring 100.00 ms on the bus); the separate assist-shaping task FUN_00022ca0
    (boost/damping producer) runs at an unresolved rate, an efficacy question only (the V44 damper
    stays net-dissipative at either rate).
    """
    raw_demand = _signed16(st.demand_sum)
    if not st.governor_initialized:
        st.governor_held = raw_demand
        st.governor_initialized = True

    st.runtime_governor_value = computed_runtime_governor(sensors, cal)
    limit = (st.runtime_governor_value * sensors.governor_limit_scale_q15) >> 15
    clamped = _clamp(raw_demand, -limit, limit)
    target = (clamped * sensors.governor_post_scale_q15) >> 15

    step_cal = cal.governor_slew_step_alt if sensors.governor_slew_alt else cal.governor_slew_step_normal
    step = max(0, (step_cal * sensors.governor_step_scale_q15) >> 15)
    previous = _signed16(st.governor_held)

    # Zero or a sign crossing resets the held value. Slew limits only motion AWAY from zero; motion
    # toward zero is accepted immediately. This is not a symmetric delta clamp.
    if (target >= 0 and previous < 0) or (target <= 0 and previous > 0):
        previous = 0
        st.governor_held = 0

    if target > previous:
        if target <= 0:
            governed = target
        else:
            candidate = previous + step
            governed = target if target <= candidate else candidate
    elif target < previous:
        if target >= 0:
            governed = target
        else:
            candidate = previous - step
            governed = target if target >= candidate else candidate
    else:
        governed = target

    governed = _signed16(governed)
    if (sensors.governor_substitution_state == 4
            and abs(governed) > abs(_signed16(st.governor_held))):
        governed = _signed16(st.governor_held)         # state 4 keeps the lower-magnitude held value

    st.governed_demand = governed                      # gp-0x6ace
    st.governor_held = governed

    st.post_governor_compensation = int(sensors.post_governor_compensation)
    st.post_governor_command = _signed16(st.governed_demand + st.post_governor_compensation)  # gp-0x6acc
    return st.post_governor_command


# =====================================================================================================
# SECTION 7 -- SOFT-EME WINDUP SHAPER  (SM2 / SM3)  -- the mechanism V31 neutralises
# -----------------------------------------------------------------------------------------------------
# A different cut class from the gentle EME. gp-0x6acc drives a Q15 integrator against upper/lower
# bounds; sustained saturation enters the SM3 dwell before its factor becomes zero. V31's boost floor
# fixed the observed soft EME, but the later-discovered assist-inclusive gp-0x6acc envelope means this
# model does not claim the floor contains every static combination.
# =====================================================================================================

def soft_eme_windup_shaper(sensors: SensorInputs, st: EpsState, cal: Calibration) -> int:
    """
    Rate-shape the merged command and run the slow-windup soft-EME cut (SM2/SM3). [VERIFIED]
    FUN_00042af8: integrator gp-0x3570 winds on (gp-0x6acc command - bound), where bound is the 3-way
    MAX of a corridor arm (cal 0xC674E, gated OFF hands-off when |gp-0x6bf0|<=corridor_gate 9216), an
    IIR arm (gp-0x3574>>8, ceiling 12288 -- can exceed the 5120 boost floor while the column is
    actively rotating), and a boost arm (cal 0xC6768, authority-latched to 0 once authority>16384 for
    20 cycles via an EXACT-ZERO recovery test). Authority = (|integrator>>15| * 1092)>>10. SM2 entry
    needs command!=0, authority>=16384, AND cal tp+0x74cc!=3 -- V38/V39 carry 3, inhibiting this
    transition. SM3 enters a dwell at |integrator>>15|>=30720, going to a zero Q15 factor after 20
    sustained cycles; the decay branches clamp with max(0,.)/min(0,.), so the integrator snaps to
    EXACTLY 0 on the crossing cycle (not a measure-zero target), making SM3 the only LIVE cut and
    recovery easier than previously modelled -- the ratchet's real cause is the separate state-4
    governor substitution (fixed in V42), not this shaper. [CONTESTED, unresolved] a re-trace argues
    SM1/SM2 are PERMANENTLY blocked on every build including stock by gates 0xC64CD/0xC64CC=3,
    contradicting an older memory; re-verify against raw disassembly before editing 0xC6422 or
    0xC61DE on the strength of either claim. The governor input (gp-0x4f64, motor-rate-adaptive, NOT
    road-speed) is fully described in motor_torque_governor()/rate_cap_binding_analysis(); it is
    applied here as clamp(demand, +/-gov) followed by a separate static +/-0x2000 clamp, output ->
    gp-0x6b98, lockstep-shadowed at gp-0x4ce2. V31's boost floor fixed the observed soft EME on-car;
    the conservative assist-inclusive envelope (4762 governor + 2560 compensation = 7322) exceeds the
    5120 floor, so this model does not claim every combination is contained.
    """
    # Boost-latch logic consumes the PREVIOUS authority before this invocation computes the next value.
    previous_authority = st.authority
    if st.boost_latch_state == 1:
        if previous_authority > cal.boost_latch_auth:
            if st.boost_latch_counter >= cal.boost_latch_dwell:
                st.boost_latch_state = 2
            else:
                st.boost_latch_counter += 1
        else:
            st.boost_latch_counter = 0
    elif st.boost_latch_state == 2:
        if previous_authority == 0:
            st.boost_latch_counter = 0
            st.boost_latch_state = 1
    else:
        st.boost_latch_counter = 0
        st.boost_latch_state = 1
    st.boost_latched_off = st.boost_latch_state == 2 and previous_authority != 0

    # gp-0x6acc drives the integrator through a ONE-SIDED zero-gate (NOT symmetric +/-8192): the
    # condition is the plain inequality x<=8192 (@0x431c4-0x431d8), so the entire negative range passes
    # unchanged and only x>+8192 is zeroed -- any chatter riding this gate could only appear on the
    # POSITIVE command side. Mode selector cal 0xC64C8=0 confirms the default path below is live.
    # [VERIFIED] max|gp-0x6ace|=4762 (Q15 bank seeded at exact unity, no amplifying op on that path) +
    # max|gp-0x6ad0|=2560 (LERP2 ceilings at INDEX>=4150, no extrapolation) = 7322 < 8192, an 870-count
    # margin that genuinely holds; excursions past -8192 hit the separate SATURATING +/-0x2000 clamp
    # near the function's end instead, a smooth clamp with no chatter mechanism.
    sanitized = 0 if _signed16(st.post_governor_command) > 0x2000 else _signed16(st.post_governor_command)
    if cal.shaper_mode == 1:
        command = cal.shaper_bias
    elif cal.shaper_mode == 2:
        command = _clamp(sanitized + cal.shaper_bias, -0x3000, 0x3000)
    else:
        command = sanitized
    st.shaper_internal_command = _signed16(command)     # gp-0x6b08

    corridor_arm = 0 if sensors.shaper_hands_off else cal.corridor_upper
    iir_arm = st.iir_envelope >> 8
    boost_arm = 0 if st.boost_latched_off else cal.boost_floor
    default_bound = max(corridor_arm, iir_arm, boost_arm)
    upper = (default_bound if sensors.shaper_upper_bound_override is None
             else int(sensors.shaper_upper_bound_override))
    lower = (-default_bound if sensors.shaper_lower_bound_override is None
             else int(sensors.shaper_lower_bound_override))

    def q15_delta(a_q15, b_q15):
        return ((a_q15 >> 2) - (b_q15 >> 2)) << 2

    command_q15 = st.shaper_internal_command << 15
    upper_q15 = _signed16(upper) << 15
    lower_q15 = _signed16(lower) << 15
    integrator = st.soft_eme_integrator_q15
    if command_q15 > upper_q15:
        integrator += q15_delta(command_q15, upper_q15)
    elif command_q15 < lower_q15:
        integrator += q15_delta(command_q15, lower_q15)
    elif integrator > 0:
        integrator = max(0, integrator + q15_delta(command_q15, upper_q15))
    elif integrator < 0:
        integrator = min(0, integrator + q15_delta(command_q15, lower_q15))
    else:
        integrator = 0
    integrator_limit_q15 = cal.sm3_clamp << 15
    st.soft_eme_integrator_q15 = _clamp(integrator, -integrator_limit_q15, integrator_limit_q15)
    integrator_magnitude = abs(st.soft_eme_integrator_q15 >> 15)
    st.authority = (integrator_magnitude * cal.authority_scale) >> 10

    # V38/V39's variant gate (3) inhibits this SM2 authority-threshold entry. The downstream SM2
    # recovery/ramp is not reconstructed; its Q15 factor remains replayable state.
    if (st.sm2_state == 1 and st.shaper_internal_command != 0
            and st.authority >= cal.sm2_arm and cal.sm2_variant_gate != 3):
        st.sm2_state = 3
        st.sm2_entry_seen = True

    # SM3 requires sustained saturation before selecting the zero factor.
    if st.sm3_state == 2:
        st.sm3_factor_q15 = 0x8000
        if integrator_magnitude >= cal.sm3_clamp:
            st.sm3_state = 4
            st.sm3_counter = 1
    elif st.sm3_state == 4:
        if integrator_magnitude < cal.sm3_clamp:
            st.sm3_counter = 0
            st.sm3_state = 2
            st.sm3_factor_q15 = 0x8000
        elif st.sm3_counter < cal.sm3_dwell:
            st.sm3_counter += 1
            st.sm3_factor_q15 = 0x8000
        else:
            st.sm3_counter = 0
            st.sm3_state = 3
            st.sm3_factor_q15 = cal.sm3_cut_factor_q15
    elif st.sm3_state == 3:
        if integrator_magnitude == 0:
            st.sm3_counter = 0
            st.sm3_state = 1
            st.sm3_factor_q15 = 0x8000
        else:
            st.sm3_factor_q15 = cal.sm3_cut_factor_q15
    else:
        st.sm3_factor_q15 = 0x8000  # state-1 recovery details remain outside this model

    state_scale = (min(st.sm2_factor_q15, st.sm3_factor_q15)
                   if sensors.shaper_state_scale_q15_override is None
                   else int(sensors.shaper_state_scale_q15_override))
    blend = _clamp(int(sensors.shaper_blend_q15), 0, 0x8000)
    inverse_blend = 0x8000 - blend
    part_a = ((st.shaper_internal_command * inverse_blend) << 2) >> 17
    part_b = (blend * int(sensors.shaper_alternate_term)) >> 15
    r28 = ((part_a + part_b) * state_scale) >> 15
    st.shaper_term_r20 = (int(sensors.shaper_term_r20_override)
                          if sensors.shaper_term_r20_override is not None
                          else (r28 if cal.shaper_term_selector == 0 else st.shaper_internal_command))

    # Final gp-0x6b98 is a SEPARATE path: range_gate(gp-0x6afe) + r20, then the second governor and
    # static +/-0x2000 clamp. It is not gp-0x6acc passed through another clamp.
    st.secondary_mixer_command = _signed16(sensors.secondary_mixer_command)
    gated_secondary = _range_gate(st.secondary_mixer_command, 0x2800)
    pre_governor_output = gated_secondary + st.shaper_term_r20
    governor_limit = st.runtime_governor_value if st.runtime_governor_value <= 0x2800 else 0
    second_governed = _clamp(pre_governor_output, -governor_limit, governor_limit)
    st.merged_command = _clamp(second_governed, -cal.shaper_final_clamp, cal.shaper_final_clamp)
    st.lkas_authority_cut = state_scale == 0
    return st.merged_command                 # -> gp-0x6b98 (0xFEDF1468), the FOC demand


# =====================================================================================================
# SECTION 8 -- HARD-DTC LOCKSTEP MONITOR  (int wall vs float twin)  -- the hardest cut class
# =====================================================================================================

def hard_dtc_lockstep_monitor(st: EpsState, cal: Calibration) -> None:
    """
    The ASIL cross-check: an independent float twin recomputes the same shaper bound; if the int wall
    and the float twin diverge beyond tolerance, latch DTC 0xF00049 and kill the motor. [VERIFIED]
    FUN_00043e44 mirrors the corridor (0xC6598..) and boost (0xC65C4..) arms in float (float Y = int
    Y/1024), tolerant to +/-5 LSB (@0x44640); this is the class the V25-V27 builds tripped (int/float
    desync -> hard fault) -- V31 keeps the twin matched exactly (boost float 4.0 == int 4096/1024), so
    the monitor delta stays 0 and every soft-EME edit must move int AND float in lockstep.
    """
    # Modelled as: the matched builds never diverge; an UNMATCHED edit would set the DTC.
    int_wall = max(0 if True else cal.corridor_upper, st.iir_envelope >> 8,
                   0 if st.boost_latched_off else cal.boost_floor)
    float_twin = int_wall  # matched by construction in V9/V31/V37/V38/V39
    if abs(int_wall - float_twin) > 5:
        st.dtc_0xF00049_set = True   # hard EME: latched motor-off


# =====================================================================================================
# SECTION 9 -- DELIVERY / FOC CURRENT LOOP / MOTOR PWM OUTPUT  (the ISR side)
# =====================================================================================================

def enable_fsm_producer(st: EpsState) -> None:
    """
    Produce the ENABLE/mode byte gp-0x67a4. [VERIFIED] FUN_0002b422 (~0x2b422-0x2b51e, an 8-state
    handshake producer FSM) writes gp-0x67a4 in {0,1,2,3,4,5} from gp-0x67a1/a2/a3/a7 + prior state
    gp-0x3d28. [OPEN] the previously-assumed "{2,3} else LKAS=0" consumer gate is NOT substantiated --
    a Ghidra xref sweep found ZERO readers of gp-0x67a4, the same dead-gate pattern as gp-0x6809; do
    not model an ENABLE cut here until a reader is located (an ep-relative/computed-base read could be
    missed by the xref index).
    """
    # Modelled as a passthrough producer; no confirmed consumer gate exists, so it does not cut here.
    st.enable_fsm = 2 if st.decider_verdict == 0 else 0


def foc_current_loop(sensors: SensorInputs, st: EpsState) -> float:
    """
    Field-oriented control inner loop: turn the merged command into a q-axis current reference and
    drive the PI/SVPWM voltage computation. [VERIFIED] shared EI trampoline FUN_0001492a, EIIC 0x600
    -> FUN_0006404c (ADC-complete) -> phase currents -> FUN_00065afe (resolver sin/cos atan2 rotor
    angle) -> FUN_00068f52 (rotor-speed estimator) -> ASIL sum self-checks -> FUN_00071272 (Park/Clarke
    + PI current regulator + SVPWM, duties x51200.0). This is where "command" finally becomes "motor
    torque": q-axis current is proportional to torque. [OPEN] the exact RAM var handing mixer/shaper
    output into the q-ref is not pinned (may route off-die over CSIG0); the on-chip FOC->PWM chain
    itself is verified, and the carrier's absolute Hz is open.
    """
    # abstract: q-current reference tracks the merged command (torque ~ Iq), gated by FOC enable/fault
    st.q_current_ref = float(st.merged_command)   # proportional stand-in for the Park/PI result
    return st.q_current_ref


def motor_pwm_output(st: EpsState) -> tuple:
    """
    Emit the 3-phase PWM compare values that actually move the motor. [VERIFIED] shared EI trampoline
    FUN_0001492a, EIIC 0x970 -> FUN_00061614 (TSG20) -> FUN_0006c5ce (Park/inverse -> duty compute),
    writing TSG20 CMPU/CMPV/CMPW (0xFFFFCCB0/B4/B8, /51200.0, period-clamped) -- the physical motor
    output endpoint; commutation table at tp-0x2d40 (0xF52C0). [OPEN] the PWM carrier frequency
    (TSG20 clock not confirmed; init writes period 5000 / compares 5160).
    """
    duty = st.q_current_ref / 51200.0
    return (duty, duty, duty)   # CMPU/CMPV/CMPW (3-phase commutation applied in the real emitter)


# =====================================================================================================
# SECTION 10 -- EXECUTION MODEL / ORCHESTRATION
# -----------------------------------------------------------------------------------------------------
# Two clocks drive everything: (1) the RTOS steering task (w_steer_control_task, FUN_0002214a) on the
# OSTM0 base tick (~1 ms), running the command pipeline (arbitration + its inlined SMs are state-gated,
# not phase-gated -- see the module docstring's EXECUTION MODEL); and (2) fast interrupts via the
# shared EI trampoline FUN_0001492a (EIIC 0x600 = ADC-complete/FOC inner loop, EIIC 0x970 = TSG20 PWM
# output) plus the CAN-RX mailbox ISR that stages the command. This function shows the ORDER.
# =====================================================================================================

def control_task(frame: CanSteeringControl, sensors: SensorInputs, st: EpsState, cal: Calibration) -> tuple:
    """
    One tick of the periodic steering control task: CAN command -> motor PWM. [VERIFIED] Task root
    FUN_0002214a (w_steer_control_task, an RTOS task in the ~0xbb900 TCB table) plus sibling task
    FUN_00022ca0 (decider); scheduled off the OSTM0 base tick (compare 0x1387F=79999 => ~1 ms @ 80 MHz,
    likely 1 kHz though the OSTM0 clock is not independently confirmed), with arbitration phase-gated
    within it. This Python runs the whole chain sequentially per call for readability; in the firmware
    the FOC/PWM ISRs (EIIC 0x600/0x970) run asynchronously and far faster than this steering-task tick.
    """
    # -- interrupt-staged input (runs asynchronously in the CAN-RX ISR; shown here for order) --
    steer_torque = can_rx_stage_steer_torque(frame)

    # -- RTOS steering-task body, in firmware order (arbitration block is phase-gated in HW) --
    read_column_torque_voter(sensors, st, cal)                 # driver-torque voter (slot-3 task)
    st.assist_lane = base_driver_assist_lane(sensors, st, cal) # base assist boost curve -> gp-0x6bbe
    shaping = assist_shaping_lanes(sensors, st)                # the 5 sibling assist lanes
    lkas_process_steer_cmd(steer_torque, st, cal)              # CAN setpoint -> gp-0x69ae
    engage_decider(st, cal)                                    # engage/disengage verdict
    steer_torque_arbitration(sensors, st, cal)                 # limit + Q15 gain (+ debounce SM + DTC-49)
    limit_distribute_mixer_gate(st, cal)                       # LKAS-only clamp cascade -> gp-0x6b4c
    motor_torque_demand_aggregator(st, shaping, cal)           # LKAS + assist + 8 lanes -> gp-0x6b94
    motor_torque_governor(sensors, st, cal)                    # adaptive cap/slew + comp -> gp-0x6acc
    soft_eme_windup_shaper(sensors, st, cal)                   # SM2/SM3 + gp-0x6afe/r20 -> gp-0x6b98
    hard_dtc_lockstep_monitor(st, cal)                         # int/float lockstep (hard EME)
    enable_fsm_producer(st)                                    # ENABLE byte producer (no confirmed gate)

    # -- fast ISRs consume the merged command and drive the motor --
    foc_current_loop(sensors, st)                              # ADC-complete ISR (fast inner loop)
    duties = motor_pwm_output(st)                              # TSG20 carrier-valley ISR -> motor

    return duties, st


# =====================================================================================================
# DEMO -- show the five modeled builds across the two historical failure regimes
# =====================================================================================================

def _self_check():
    assert (V9_FULL_SCALE_POSITIVE, V9_FULL_SCALE_NEGATIVE, V9_FULL_SCALE_MIN_MAGNITUDE) == (417, -418, 417)
    expected_governors = {
        0: 5325, 1050: 5325, 1260: 4762, 1318: 4607, 1417: 4342,
        1700: 3584, 2500: 2406, 3700: 1586, 4100: 512, 5000: 512,
    }
    assert {z: a160_governor_rate_cap(z) for z in expected_governors} == expected_governors

    st = EpsState(speed_voted=0, col_torque_rate=512, motor_rate_raw=0)
    assert _inline_torque_rate_b(st) == 1533
    st.col_torque_rate = -512
    assert _inline_torque_rate_b(st) == -1533

    # V38 setpoint raise must actually be represented; this was missing before the 2026-07-18 update.
    assert Calibration.for_build("V38").arb_setpoint_limit == 16384
    assert Calibration.for_build("V39").suppress_direct_torque_rate_assist

    lanes = {
        "inline_a": 0, "inline_b": 1533, "magnitude_6b86": 0, "damping_6bd0": 0,
        "friction_6b26": 0, "resonance_6ad4": 0, "return_centre_6b62": 0,
        "filtered_36682": 0,
    }
    v38 = EpsState(mixed_command=-1782, col_torque_max=100)
    v39 = EpsState(mixed_command=-1782, col_torque_max=100)
    assert motor_torque_demand_aggregator(v38, lanes, Calibration.for_build("V38")) == -249
    assert motor_torque_demand_aggregator(v39, lanes, Calibration.for_build("V39")) == -1782
    assert v39.direct_rate_guard_fired

    strong_driver = EpsState(mixed_command=-1782, col_torque_max=320)
    assert motor_torque_demand_aggregator(strong_driver, lanes, Calibration.for_build("V39")) == -249
    assert not strong_driver.direct_rate_guard_fired

    def guard_result(lkas, inline_b, driver, reduced=False):
        case_lanes = dict(lanes, inline_b=inline_b)
        state = EpsState(mixed_command=lkas, col_torque_max=driver, aggregator_reduced_mode=reduced)
        result = motor_torque_demand_aggregator(state, case_lanes, Calibration.for_build("V39"))
        return result, state

    assert not guard_result(-416, 100, 319)[1].direct_rate_guard_fired
    assert guard_result(-417, 100, 319)[1].direct_rate_guard_fired
    assert guard_result(417, -100, 319)[1].direct_rate_guard_fired
    same_sign_result, same_sign = guard_result(417, 100, 319)
    assert same_sign_result == 417 and same_sign.direct_rate_guard_fired
    assert not guard_result(417, 0, 319)[1].direct_rate_guard_fired
    assert not guard_result(417, -100, 320)[1].direct_rate_guard_fired
    assert not guard_result(417, -100, 0xFFFF)[1].direct_rate_guard_fired
    assert not guard_result(417, -100, 0, reduced=True)[1].direct_rate_guard_fired

    # V39 intentionally leaves the adaptive r26 derivative lane untouched.
    adaptive_lanes = dict(lanes, inline_a=200, inline_b=-100)
    adaptive = EpsState(mixed_command=417, col_torque_max=319)
    assert motor_torque_demand_aggregator(adaptive, adaptive_lanes, Calibration.for_build("V39")) == 617
    assert adaptive.direct_rate_guard_fired

    # FUN_0004503c limits only movement away from zero; zero/toward-zero changes are immediate.
    governor_cal = Calibration.for_build("V38")
    toward_zero = EpsState(demand_sum=1000, governor_initialized=True, governor_held=2000)
    assert motor_torque_governor(SensorInputs(), toward_zero, governor_cal) == 1000
    to_zero = EpsState(demand_sum=0, governor_initialized=True, governor_held=2000)
    assert motor_torque_governor(SensorInputs(), to_zero, governor_cal) == 0
    away = EpsState(demand_sum=1000, governor_initialized=True, governor_held=0)
    assert motor_torque_governor(SensorInputs(), away, governor_cal) == 512
    zero_step = EpsState(demand_sum=1000, governor_initialized=True, governor_held=0)
    assert motor_torque_governor(SensorInputs(governor_step_scale_q15=0), zero_step, governor_cal) == 0
    state4 = EpsState(demand_sum=1000, governor_initialized=True, governor_held=500)
    assert motor_torque_governor(SensorInputs(governor_substitution_state=4), state4, governor_cal) == 500

    # RAMP TIME is the invariant V38 broke: same absolute slew steps, ~4x the target. On a hard turn
    # the step is pinned to the SLOW 205 cal, so V38 needs ~14 cycles where stock needed ~3.
    v9_ramp = slew_ramp_time_analysis(Calibration.for_build("V9"))
    v38_ramp = slew_ramp_time_analysis(Calibration.for_build("V38"))
    assert v9_ramp["target_counts"] == 1441 and v38_ramp["target_counts"] == 2806
    assert v9_ramp["cycles_at_slow_step"] == 8 and v38_ramp["cycles_at_slow_step"] == 14
    # LKAS-only (no assist) is the starker comparison: stock reaches full command in 3 slow cycles.
    assert slew_ramp_time_analysis(Calibration.for_build("V9"), 0)["cycles_at_slow_step"] == 3
    assert slew_ramp_time_analysis(Calibration.for_build("V38"), 0)["cycles_at_slow_step"] == 9
    # Both step cals are stock in every build to date -- nothing has ever compensated for the raise.
    for _b in ("V9", "V31", "V37", "V38", "V39"):  # V40 deliberately excluded: it moves them
        _c = Calibration.for_build(_b)
        assert (_c.governor_slew_step_normal, _c.governor_slew_step_alt) == (512, 205)

    # ---- V40: the two cal edits, and what each is supposed to buy ---------------------------------
    v40 = Calibration.for_build("V40")
    # It baselines on V38, NOT V39 -- the r24 guard is dropped entirely.
    assert not v40.suppress_direct_torque_rate_assist
    assert (v40.lkas_output_gain, v40.arb_output_clamp, v40.arb_setpoint_limit) == (3564, 2048, 16384)
    assert v40.boost_floor == 5120 and v40.corridor_upper == 5120
    assert v40.runtime_governor == 4762, "V40 must leave the governor nominal at stock"
    # Edit 1: the slew can never bind, so a sign-crossing reset recovers in a single cycle.
    assert (v40.governor_slew_step_normal, v40.governor_slew_step_alt) == (0xFFFF, 0xFFFF)
    assert slew_ramp_time_analysis(v40)["cycles_at_slow_step"] == 1
    assert slew_ramp_time_analysis(v40, 0)["cycles_at_slow_step"] == 1
    # A step of 0xFFFF exceeds the largest possible demand swing (2 * 0x2800), so it cannot bind.
    assert v40.governor_slew_step_alt > 2 * v40.distribute_lkas_lane_clamp
    # Edit 2: the cap is flat at the table max and can never bind on any build.
    assert v40.rate_cap_y == (5325,) * 5 and v40.rate_cap_slope_q13 == (0, 0, 0, 0)
    assert not rate_cap_binding_analysis(v40)["can_be_rate_capped"]
    assert not rate_cap_binding_analysis(v40, 1024)["can_be_rate_capped"]
    # Flattening does NOT raise the ceiling: MIN(4762 nominal, flat 5325) == 4762 at every rate,
    # which is exactly what the motor already sees at low rate under stock.
    for z in (0, 1050, 1700, 2500, 3700, 4100, 6000):
        flat = a160_governor_rate_cap(z, v40.rate_cap_y, v40.rate_cap_slope_q13)
        assert flat == 5325, f"flat cap not flat at z={z}: {flat}"
        assert min(v40.runtime_governor, flat) == 4762
        assert computed_runtime_governor(SensorInputs(governor_axis_z=z), v40) == 4762
    # Under V38 the same sweep tapers hard -- this is the difference V40 is buying.
    v38_cal = Calibration.for_build("V38")
    assert computed_runtime_governor(SensorInputs(governor_axis_z=4100), v38_cal) == 512
    assert computed_runtime_governor(SensorInputs(governor_axis_z=1050), v38_cal) == 4762
    # A flat Y with LIVE slopes would still interpolate -- the trap V40's slope-zeroing avoids.
    assert a160_governor_rate_cap(4000, (5325,) * 5, GOVERNOR_RATE_SLOPE_Q13) != 5325

    # The motor-rate cap cannot bind on stock LKAS (417 < the 512 cap floor) but does on V31/V38.
    # This is the numeric core of the V38 ratchet hypothesis -- see rate_cap_binding_analysis().
    assert rate_cap_binding_analysis(Calibration.for_build("V9"))["can_be_rate_capped"] is False
    assert rate_cap_binding_analysis(Calibration.for_build("V9"))["lkas_max_counts"] == 417
    v31_cap = rate_cap_binding_analysis(Calibration.for_build("V31"))
    v38_cap = rate_cap_binding_analysis(Calibration.for_build("V38"))
    assert v31_cap["binds_from_motor_rate"] == 3980
    assert v38_cap["binds_from_motor_rate"] == 3414
    assert v38_cap["lkas_max_counts"] == 1782
    # Base assist in the aggregate pulls the binding rate substantially lower still.
    assert rate_cap_binding_analysis(Calibration.for_build("V38"), 1024)["binds_from_motor_rate"] == 2229

    # gp-0x6acc and gp-0x6afe+r20 are distinct paths. The integrator stores Q15, while final output uses
    # the secondary lane and replayed r20 through the second governor.
    shaper = EpsState(post_governor_command=1000, runtime_governor_value=400)
    shaper_inputs = SensorInputs(secondary_mixer_command=200, shaper_term_r20_override=300)
    assert soft_eme_windup_shaper(shaper_inputs, shaper, Calibration.for_build("V38")) == 400
    assert shaper.shaper_internal_command == 1000
    assert shaper.soft_eme_integrator_q15 == 0  # V38 boost floor 5120 contains this command

    q15 = EpsState(post_governor_command=1000, runtime_governor_value=4762)
    assert soft_eme_windup_shaper(SensorInputs(), q15, Calibration.for_build("V9")) == 1000
    assert q15.soft_eme_integrator_q15 == 1000 << 15
    assert q15.authority == (1000 * 1092) >> 10


def _demo():
    print("build |  scenario                         | STEER_STATUS | DTC0x49 | soft-cut | guard | merged_cmd")
    print("-" * 102)
    scenarios = {
        "hard sustained hands-off turn (soft EME)": SensorInputs(
            column_torque_coils=(120, 118, 121), steering_angle=180.0, steering_angle_rate=2.0,
            vehicle_speed=45.0),
        "loaded curve + bump (gentle EME / DTC49)": SensorInputs(
            column_torque_coils=(2100, 2080, 2110), steering_angle=90.0, steering_angle_rate=1700.0,
            vehicle_speed=55.0),
    }
    for build in ("V9", "V31", "V37", "V38", "V39", "V40"):
        cal = Calibration.for_build(build)
        for name, sensors in scenarios.items():
            st = EpsState()
            frame = CanSteeringControl(steer_torque=1000, steer_request=True)
            # run ~1.5 s worth of sustained ticks to let the debounce/DTC/windup counters evolve
            for _ in range(150):
                control_task(frame, sensors, st, cal)
            print(f" {build:4} | {name:33} |     {st.steer_status:1}        |   {int(st.dtc_0x49_set)}     "
                  f"|    {int(st.lkas_authority_cut)}     |   {int(st.direct_rate_guard_fired)}   "
                  f"| {st.merged_command:6}")
        print("-" * 102)

    print("\nV38/V39 discriminating synthetic: saturated LKAS + direct Sensor-B torque-rate impulse")
    print("build | LKAS lane | inline r24 | guard | pre-governor sum | final command")
    print("-" * 78)
    impulse = SensorInputs(
        column_torque_coils=(100, 98, 102), column_torque_sensor_b=100, column_torque_rate=512,
        steering_angle=90.0, steering_angle_rate=100.0, motor_rate_raw=0,
    )
    for build in ("V38", "V39"):
        st = EpsState()
        frame = CanSteeringControl(steer_torque=4096, steer_request=True)
        for _ in range(50):
            control_task(frame, impulse, st, Calibration.for_build(build))
        print(f" {build:4} | {st.mixed_command:9d} | {st.assist_inline_b:10d} |"
              f"   {int(st.direct_rate_guard_fired)}   | {st.demand_sum:16d} | {st.merged_command:13d}")
    print("-" * 78)


if __name__ == "__main__":
    _self_check()
    _demo()

