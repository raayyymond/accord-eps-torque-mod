"""
eps_lkas_chain_model.py
=======================================================================================================
🛑 THIS FILE IS NOW A THIN FACADE. The model itself lives in four modules beside it.
    It was ~302 KB / ~4000 LINES — larger than a single `Read` can return (256 KB cap), so a plain
    `Read` SILENTLY TRUNCATED THE TAIL with no warning. Split on 2026-08-12; code moved VERBATIM.
    Importing THIS module still gives you the whole model — every name is re-exported below, so
    `import eps_lkas_chain_model as M` and `from eps_lkas_chain_model import X` are unchanged.

    WHERE THE CODE ACTUALLY IS — grep/read these, not this file:
      eps_chain_core.py       SECTIONS 0-1  calibration constants, Calibration/CanSteeringControl/
                                            SensorInputs/EpsState, the integer helpers. No intra-kit
                                            imports — the bottom of the graph.
      eps_chain_lanes.py      SECTIONS 2-3  CAN intake + LKAS setpoint, driver torque sensor + voter,
                                            base driver assist, boost index, the assist-shaping
                                            rate lanes (r24/r26).
      eps_chain_control.py    SECTIONS 4-6  engage decider, steer torque arbitration, limit/pack ->
                                            distribute -> mixer -> gate, the demand aggregator, the
                                            motor-rate governor, and the analysis functions.
      eps_chain_delivery.py   SECTIONS 7-10 soft-EME windup shaper, hard-DTC lockstep monitor,
                                            delivery/FOC/PWM, control_task, _self_check/_demo, and
                                            the plant-model disturbance observer.
    Import order is core -> lanes -> control -> delivery; there are no cycles.

    Sections you are most likely to want (grep these strings across eps_chain_*.py):
      "Path 1" / "Path 2"        the two arms of the observer residual   [delivery]
      "FUN_00038148"             iVar6 = MODEL + REQUEST - ACTUAL, and the 0xC63AC pole
      "FUN_0003b8f6"             the 1 kHz plant model (K0 0xC4080, K1 0xC40D2, relay 0xC40BC)
      "OSTM0"                    ⚠ the 80 MHz red herring — PCLK is 40 MHz, OSTM0 is 500 Hz.
                                 The 1 kHz control-task rate is anchored on 0xC64DF, NOT on OSTM0.
    ⚠ Line-number citations of the form `eps_lkas_chain_model.py:NNNN` written before 2026-08-12
      (in build scripts, handoffs and memories) point into the PRE-SPLIT file and are now STALE.
      Grep for the symbol name instead.
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
  🛑 THE V57 DECOUPLE WAS OFF THE CAR FOR V76/V78/V79/V80 ONLY -- those read 0x2A1F0 disp 0x746C
  (shared 0xC646C = 3564). ✅ CORRECTED 2026-08-08: V81/V83A/V84 read disp 0x7CD0 (private 0xC6CD0 =
  3564, 0xC646C stock 891) because they descend from V75, as do V62/V68/V74/V75. Real uncosted headroom
  regression on that four-build window; NOT the 27 Hz driver.
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
                 ★★ LOAD-BEARING: boost (FUN_00034a72) and the TABLE DAMPER (FUN_00034350, sole caller
                 FUN_00022ca0) run in TASK 5 = 100 Hz, while the aggregator FUN_0003aa2c and the
                 residual lane FUN_0003a382 run in TASK 1 = 1 kHz. A zero-order hold costs 37.6 deg
                 average / 75.2 deg worst-case transport lag at 20.9 Hz BEFORE any plant phase, and the
                 ZOH CROSSOVER IS 25 Hz -- above it the 100 Hz damper can be sampled into an
                 ANTI-DAMPING force. Damping needs force in phase with velocity => the damper
                 structurally cannot damp the 20.9 Hz mode. ⇒ THE 1 kHz RATE LANES r24/r26 ARE THE ONLY
                 DAMPING IN THIS FIRMWARE FAST ENOUGH TO ACT ON A 20 Hz MODE. That is an
                 explanation for every null damper lever (V44 FactorC; V47 FactorC+FactorE together --
                 🛑 CORRECTED 2026-08-06: both wrote modes 10/11 on a modes-24/26 car, so they were
                 INERT BY TABLE SELECTION and their nulls carry no information about this at all)
                 INDEPENDENT of the FactorC speed axis,
                 and a candidate reason the damping-SIGN question flip-flopped for four sessions: a
                 sign correct by construction can still act with the wrong phase when it is refreshed
                 10x slower than the mode. It also invalidates V59's eps table, which bracketed 1 kHz
                 and 500 Hz for task 5. 🛑 Prefer task 1 for any dynamics fix.
                 See memory/accord-task5-is-100hz-damper-cannot-damp-21hz.md.

                 ★★★ CORRECTION 2026-08-09 late (V87 session), TWO STRUCTURAL FACTS THIS MODEL LACKED:
                 (1) FUN_0003b66a holds a REAL BAND-PASS at 8.13 Hz -- backward difference x 17.453293
                     -> TWO cascaded first-order EMAs sharing alpha 0xC63B4 = 51 -> gain 0xC63B8 = 41
                     -> clamp +-10 -> x1024. Peak 8.14 Hz, Q 0.501, phase +1.44 deg. Byte-identical to
                     stock in ALL 88 build images. 🛑 BUT IT IS NOT A DAMPER: the output is FULL-WAVE
                     RECTIFIED (gp-0x6ba6 = |gp-0x6b9a|, subr r0,r13 @0x3b87a) and consumed as a LERP
                     INDEX into the boost gain tables (falling 16384 -> 8188). abs() destroys the
                     phase, FactorB is flat unity in all 34 records, and the boost arm is the
                     V58/V59/V60 parametric pump already flown NULL. ⇒ the closure argument's PREMISE
                     ("every gain element is a flat scalar or a differentiator") is FALSE -- a
                     differentiator into two poles IS a localised band structure -- but its CONCLUSION
                     survives: nothing in the control region has Q > 0.52, so the firmware shapes and
                     drives the band, the plant rings in it.
                     See memory/accord-c63b8-8hz-bandpass-is-a-rectified-boost-index.md.
                 (2) FUN_00043e44 is a FLOAT TWIN of the shaper and it BLOCKS filter insertion. It
                     reads gp-0x6acc @0x4467a with the SAME 0xC64C8 mode byte and 0xC61D4 cal, compares
                     against the delivered command at 5/1024 = 0.0048828125 counts, and after 0.01 s
                     (0x3c23d70b) escalates by +1024.0 against a 128.0 threshold -> FUN_000462e6(0x3f1b)
                     -> DTC 0xF00049, the V74/V75 LOSS-OF-ASSIST class. At 8 Hz a half-cycle is 62 ms,
                     six times the trip dwell. ⇒ 0x431C4 and 0x43206 are INSIDE its coverage; the phase
                     budget there is 2.4 deg; the only monitor-clean single-instruction site on the
                     spine is 0x453e0 (the gp-0x6b94 read).
                     See memory/accord-shaper-float-twin-blocks-filter-insertion.md.
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

from eps_chain_core import (
    Calibration,
    CanSteeringControl,
    EpsState,
    SensorInputs,
    V9_FULL_SCALE_MIN_MAGNITUDE,
    V9_FULL_SCALE_NEGATIVE,
    V9_FULL_SCALE_POSITIVE,
    _clamp,
    _div_trunc_zero,
    _range_gate,
    _signed16,
)
from eps_chain_lanes import (
    ASSIST_BOOST_CURVE,
    ASSIST_BOOST_X_FALLING,
    ASSIST_BOOST_X_RISING,
    ASSIST_CEILING_DEFAULT,
    ASSIST_CEILING_X,
    ASSIST_CEILING_Y,
    ASSIST_RATE_A_RECORDS,
    ASSIST_RATE_B_RECORDS,
    ASSIST_RATE_CROSS_X,
    ASSIST_RATE_STEP,
    ASSIST_SENTINEL,
    ASSIST_TORQUE_RATE_CLAMP,
    ASSIST_TORQUE_RATE_DEADZONE,
    ASSIST_TORQUE_RATE_OUTPUT_CLAMP,
    BOOST_AMP1_X,
    BOOST_AMP1_Y,
    BOOST_AMP4_X,
    BOOST_AMP4_Y,
    BOOST_AMP_BLEND_Q10,
    COUNTS_PER_KMH,
    FAULT_SENTINEL_6B9A,
    FAULT_SENTINEL_6BA6,
    _assist_rate_gain_q10,
    _generated_assist_rate_curve,
    _inline_torque_rate_a,
    _inline_torque_rate_b,
    _lerp_flat,
    assist_shaping_lanes,
    base_driver_assist_lane,
    boost_amplitude_index,
    can_rx_stage_steer_torque,
    detector_input_6c2c,
    lkas_process_steer_cmd,
    read_column_torque_voter,
    steer_status_low_speed_lockout,
)
from eps_chain_control import (
    GOVERNOR_RATE_SHIFT,
    GOVERNOR_RATE_SLOPE_Q13,
    GOVERNOR_RATE_X,
    GOVERNOR_RATE_Y,
    a160_governor_rate_cap,
    arb_deadband_relative_width,
    computed_runtime_governor,
    dirty_derivative_pole_analysis,
    dtc49_fault_counter,
    engage_decider,
    gain_rescaling_invariance_analysis,
    governor_slew_0xffff_postmortem,
    governor_step_selector_bandwidth,
    limit_distribute_mixer_gate,
    lkas_iir_quantization_analysis,
    motor_torque_demand_aggregator,
    motor_torque_governor,
    openpilot_command_slew_invariance,
    rate_cap_binding_analysis,
    slew_ramp_time_analysis,
    steer_status_debounce_sm,
    steer_torque_arbitration,
    vibration_hands_off_analysis,
)
from eps_chain_delivery import (
    FRICTION_CLAMP,
    MODEL_OUT_CLAMP,
    _demo,
    _self_check,
    control_task,
    enable_fsm_producer,
    foc_current_loop,
    hard_dtc_lockstep_monitor,
    motor_pwm_output,
    observer_residual,
    plant_model_friction,
    plant_model_output,
    soft_eme_windup_shaper,
)


if __name__ == "__main__":
    _self_check()
    _demo()
