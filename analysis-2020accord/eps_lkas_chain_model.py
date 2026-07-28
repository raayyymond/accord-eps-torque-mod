"""
eps_lkas_chain_model.py
=======================================================================================================
Executable PSEUDOCODE model of the 2020 Honda Accord EPS LKAS logic chain, from the openpilot/comma
CAN steering command all the way to motor torque (3-phase PWM) output.

Platform : 2020 Honda Accord Touring, EPS part 39990-TVA-A160, Renesas V850E2 (little-endian, 1 MB).
Purpose  : A single readable reference that captures *our current understanding* of how a CAN
           STEER_TORQUE request becomes motor current, including the driver steering-torque sensor
           path, vehicle speed, the arbitration/limit cascade, and every state machine that can gate
           or cut the LKAS term (engage decider, the STEER_STATUS "gentle-EME" debounce SM, the
           DTC-0x49 fault counter, the soft-EME windup shaper, and the hard-DTC lockstep monitor).

This is a MODEL, not the firmware. It is arithmetic-faithful where we have byte evidence and clearly
labelled where it is inferred. It is written to be read top-to-bottom.

-------------------------------------------------------------------------------------------------------
LATEST (2026-07-24, later) — V51P GATE-1 PASS + V52 built-but-INCOMPLETE (gp-0x4f60 = 19-carrier surface).
  V51P flashed+driven (rlog 7): BOTH gp-0x1300 and gp-0x1100 read 0/24000 CAN-330 frames (beacon 100%, two
  decoders) -> the EMA state cell is now definitively free. V52 (build_v52_tva.py + v52_cave_asm.py) = V50
  rebuilt on gp-0x1300 + round-to-nearest ((74*d+512)>>10) + the 3 FUN_0002eda8 branches V50 missed --
  BUILT, 50/50 CRC, UNFLASHED, 10 repoints. *** CORRECTION to the "7 collocated carriers" line below: a
  definitive byte-scan proved gp-0x4f60 has 64 raw readers / ~19 COMMAND-PATH CARRIERS across BOTH the 1kHz
  control task AND the ~100Hz assist task (not 7). *** V52 repoints only 10 -> INCOMPLETE (misses 9, incl.
  3 that self-filter -> cascade risk, + 2 mode-gated). NO monitor hazards (M1 0x42C20 / M2 0x43EDA / gate
  0x28F26 all compare raw gp-0x4f60 vs LITERAL constants -> risk is feel, not a brick). GATE-2 was closed
  for 7 lanes and does NOT carry to 19 lanes + cascades -> the source-filter is a broad/fragile surface =
  the empirical case for FFT-narrow (filter ONE lane at a convergence point: gp-0x6ad6 via FUN_00037fe6,
  gp-0x6b70 via FUN_00038148). See memory/reference-accord-gp4f60-carrier-surface.md +
  memory/reference-accord-v51p-gate1-both-cells-clean.md + docs/HANDOFF-2026-07-24-v51p-v52-carrier-surface.md.
-------------------------------------------------------------------------------------------------------
LATEST (2026-07-24) — V50 NO-FLASH (gp-0x1500 is a live I/O-mailbox writer @0xb7260; GATE-1 failed on-car
  per the V50P probe). Fix strategy pivoted to DIAGNOSE-THEN-FILTER: log the backward chain from the FOC
  setpoint (anchor gp-0x6b98 <- gp-0x6acc <- gp-0x6ace governor <- gp-0x6b94 aggregator FUN_0003aa2c
  summands), FFT to find which lane carries the ~21 Hz, then filter it LATE + FEW signals. Diagnostic = a
  four-frame CAN-TX telemetry cave on NEW IDs 0x6a0-0x6a3 (build_vfourframe_tva.py, red-panda-visible only).
  This model's aggregator summands were RE-CONFIRMED accurate this session (gp-0x6ade dead, gp-0x67ac
  const-0 both already noted below). *** FALSIFIED != UNTESTED ***: the cal-only lane cuts (r24/r26/0xC644A
  /0xC6450/damping) are validly dead, but the gp-0x4f60 SIGNAL-FILTER is UNTESTED (V48B bricked before
  testing efficacy; V50 unflashed) -> leading OPEN hypothesis. See
  memory/reference-accord-vibration-levers-falsified-vs-untested.md,
  memory/reference-accord-can-tx-architecture-new-id.md, memory/reference-accord-b7260-io-mailbox-array.md.
-------------------------------------------------------------------------------------------------------
LATEST (2026-07-22) — vibration + V50; see memory/reference-accord-v50-lowpass-ema-cave.md for detail.
-------------------------------------------------------------------------------------------------------
  * The ~21 Hz LKAS vibration is a FIRMWARE/PLANT closed-loop mode, SPEED-DEPENDENT (~21.7 Hz at 3-8 m/s
    -> ~8-12 Hz highway), sustained by the collocated base-assist lanes that read Sensor-B torque
    gp-0x4f60. The openpilot bus command STRIPS it (comma is a passenger); the operator's new OP-output
    low-pass did NOT fix it -> firmware-side fix required.
  * The operator's FOC-current-loop hypothesis is RULED OUT as a lever: FUN_00071272 (FOC core, ~8 kHz)
    reads gp-0x6b98 only for sign, has NO isolable Kp/Ki, and its model-based coeffs live at 0xC50D0-
    0xC5D84 (inside the risky 0xC5000 block). The inner loop is the ACTUATOR delivering the mode, not the
    source. (agent-memory: reference_accord_foc_inner_current_loop_architecture.md)
  * V50 (BUILT, UNFLASHED) inserts a first-order EMA low-pass (fc~12 Hz) on gp-0x4f60 via a code cave,
    repointing the 7 collocated carriers to the filtered copy — a low-pass on the base-assist FEEDBACK
    signal, upstream of the aggregator gp-0x6b94 the chain below models. Keeps the 4x forward gain
    (0xC646C=3564) untouched. See build_v50_tva.py / eps_v50_gate2_lowpass.py; this chain model is
    otherwise unchanged (the cave adds no cal-path arithmetic).
  * ★ SUPERSEDED BY V52C (2026-07-24, BUILT + FULLY GATED, UNFLASHED). gp-0x4f60 does NOT have 7
    carriers — it has **19**, and V52C repoints ALL of them to the filtered cell gp-0x1300 (V50's
    gp-0x1500 FAILED its on-car live probe: it is slot 5 of the 0xb7260 I/O-mailbox array and has a
    live writer). V52C also adds round-to-nearest to the EMA step, killing V50's -6.5-count DC-bias
    ratchet (deadband becomes a SYMMETRIC +/-6, midpoint exactly 0).
      - WHY ALL 19, not a chosen subset: a MIXED raw/filtered population is itself the hazard — any
        self-consistency / dual-path / lockstep check straddling the split sees a divergence that does
        not exist today. That is precisely how V27 bricked (ASYMMETRY, not magnitude). Uniform
        filtering is ALSO the most stable option: stability edge 4.66x (stock) -> 21.19x at 19/19,
        monotonic in the filtered fraction. See eps_v52c_gate2_broad.py.
      - Only 5 gp-0x4f60 reads remain raw on the command path, all comparing against LITERAL constants:
        the 3 health gates (0x28F26, 0x42C20 M1, 0x43EDA M2) and the 2 cal-gated dormant mux arms
        (0x34392, 0x34ACE). Plus 2 diagnostic + 3 dead. Health gates MUST see the raw sensor.
      - ⚠ gp-0x4f60 is SHADOWED (shadow gp-0x4486); a mismatch calls FUN_0006b9ee -> fault 0x17 ->
        HARD motor-off. This is why the filter writes a COPY and never the source. Do not "simplify"
        that by filtering gp-0x4f60 in place.
      - Reader enumeration: 76 accesses total (71 loads + 5 stores) across BOTH the 4-byte disp16 AND
        the 6-byte extended-displacement encodings. Any count quoted for only one encoding is wrong.
      See build_v52c_tva.py / verify_v52c_image.py / eps_v52c_gate2_broad.py and
      docs/HANDOFF-2026-07-24-v52c-complete-broad-lowpass.md. The chain model below is still unchanged
      (the cave adds no cal-path arithmetic; it only changes WHICH cell 19 loads read).

-------------------------------------------------------------------------------------------------------
CONFIDENCE LEGEND  (the operator's calibration: treat everything as inferred unless it is one of the
two CONFIRMED anchors, then let the labels tell you how much weight the rest carries)
-------------------------------------------------------------------------------------------------------
  [CONFIRMED]  On-car / DBC ground truth. Exactly TWO things:
                 (1) the LKAS torque command arriving on CAN 0xE4, and
                 (2) the physical steering-wheel torque sensor readings.
  [VERIFIED]   Byte-verified in Ghidra/rizin against the stock code.bin in a prior session (the
               address block below each function cites where). Strong, but firmware-static, not
               dynamically observed.
  [INFERRED]   Structurally reasoned from the disassembly but not pinned instruction-for-instruction,
               OR a role/label that could still be wrong.
  [OPEN]       Explicitly unknown / unlocated. Named so it is not silently assumed.

-------------------------------------------------------------------------------------------------------
ADDRESS CONVENTION (kept OUT of the code per request; used only in the comment blocks)
-------------------------------------------------------------------------------------------------------
  Ghidra program  : code.bin  (flat base 0, so file-offset == address; 2113 functions)
  gp (r4)         = 0xFEDF8000   ->  a RAM var written "gp-0xNNNN" is absolute 0xFEDF8000 - 0xNNNN
  tp (r5)         = 0xBF000      ->  a calibration "tp+0x7NNN" is absolute 0xBF000 + 0x7NNN
                                     (e.g. tp+0x746c == 0xC646C -- see the CORRECTION below)
  Tool note       : r2's default 'v850' plugin mis-decodes V850E2 -- use 'v850.gnu' or Ghidra.
                    (Superseded: GhidraMCP is now the kit's only sanctioned disassembler.)

  *** CORRECTION OF RECORD 2026-07-27 -- 0xC646C IS NOT "THE LKAS OUTPUT GAIN" ***
  Everywhere this model calls tp+0x746c the "LKAS output gain", read it as: the firmware's SINGLE SHARED
  Q15 sensor-to-command-domain SCALE. Enumerated twice independently (raw byte scan, BOTH tp encodings
  including the disp|1 form used by ld.hu/ld.w): EXACTLY 6 readers, no stores, no float mirror, and
  neither hard-shutdown monitor among them.
      0x2a1ee  FUN_00028ea6 arbitration  -- FORWARD: the LKAS setpoint. The one this model describes.
      0x2a904  unclaimed gap             -- DEAD (0 xrefs)
      0x2b656  FUN_0002b62c (~100 Hz)    -- FEEDBACK (by elimination)
      0x2c488  FUN_0002c478 (1 kHz)      -- feedback-shaped inputs, DEAD OUTPUT
      0x36686  FUN_00036682              -- FEEDBACK: (gp-0x4f60 RAW SENSOR * gain)>>15, and its return
                                            is summed into the aggregator (jarl @0x3acdc, add @0x3ace6)
                                            -> gp-0x6b94 -> governor @0x453e0 -> motor. Verified.
      0x3684a  FUN_00036828              -- FEEDBACK: same form, feeds 0x36686
  CONSEQUENCE: V38's 891 -> 3564 raised the gain on TWO RAW-SENSOR FEEDBACK PATHS as well as the LKAS
  setpoint. The forward path's clamps were raised 4x with it (0xC61B2/0xC61B4 512 -> 2048); the feedback
  path's limit is a HARDCODED +/-0x200 literal (0x367E0/E4/EA/EE), byte-identical to stock.
  Probably NOT the 21 Hz driver: FUN_00036682's output is IIR'd with tp+0x73d2=14/1024 (fc ~2.18 Hz,
  -19.7 dB at 21 Hz) and clamped to 5% of the aggregator range; and the saturation hypothesis is
  EMPIRICALLY DEAD (0 of 10,178 active-LKAS route-13 frames reach the clamp threshold).
  See memory/reference-accord-c646c-shared-gain-not-lkas-only.md and docs/BUILD-LINEAGE.md.

-------------------------------------------------------------------------------------------------------
THE FIVE BUILDS THIS MODEL PARAMETERISES  (Calibration.for_build("V9"|"V31"|"V37"|"V38"|"V39"))
-------------------------------------------------------------------------------------------------------
  V9  ("v9b")  = reconstructed STOCK. The confirmed-correct baseline (flashed 2026-05-24). Every cal
                 below sits at its stock value. This is the reference behaviour.
  V31          = V9 + 2x LKAS reach (GAIN/clamps/ramp) + the SOFT-EME fix: widen the windup-shaper
                 "corridor" x4 and add a flat BOOST FLOOR 4096 so the soft-EME integrator can never
                 wind up on a hard sustained hands-off turn. (Cal-only; fixes the V30 residual soft EME.)
  V37          = V31 + the GENTLE-EME fix: raise the STEER_STATUS debounce-SM torque/rate thresholds to
                 unsigned max so the 5-cycle debounce can never fire, AND raise the DTC-0x49 fault-
                 counter gate 112->255 so disabling STEER_STATUS=4 cannot unmask DTC 0x49.
                 *** V37 was flashed and RESOLVED the gentle EME on-car (operator-confirmed 2026-07-14). ***
  V38          = V37 + 4x-stock LKAS reach (gain 3564, source clamps 2048) + matched 5120/5.0
                  corridor and boost walls + the setpoint limit raised 15360->16384. Flashed on-car:
                  no faults, but hard turns show an apparent authority feedback limit. The exact motor-
                  rate governor schedule and the Sensor-B torque-rate assist lane are modelled below.
  V39          = V38 + an EXPERIMENTAL, narrow aggregator guard: at >=100% V9 LKAS (|lane|>=417) and below
                   the existing 320-count strong-driver threshold, suppress the direct Sensor-B torque-
                   rate lane r24 for BOTH signs. Adaptive lane r26, static boost, damping, manual assist,
                   governor, and every downstream motor-protection path remain unchanged.
                   V38 road input distinguishes a several-Hz hard-turn ratchet from a common tens-of-Hz
                   vibration under high LKAS at low and high road speed. Strong driver-side torque moves
                   the wheel quickly without either symptom, contradicting an intrinsic moving-motor
                   torque limit. V39 targeted the vibration; it did not claim the slower ratchet is solved.
                   *** V39 WAS FLASHED 2026-07-19 AND FIXED NEITHER SYMPTOM. *** The direct derivative
                   lane r24 is therefore FALSIFIED as the cause of either. NOTE the falsification is
                   narrower than it looks: the ADAPTIVE lane r26 still carries the SAME gp-0x4f62 signal
                   through the SAME producer/consumer phase masks, so V39 falsified one lane, not the
                   derivative signal. See rate_cap_binding_analysis() for the leading replacement
                   hypothesis, which is a SHARED post-aggregator stage rather than any single lane.
  V40          = V38 + governor slew steps 0xC6206/0xC6208 -> 0xFFFF + motor-rate cap flattened.
                   *** FLASHED -> IMMEDIATE EPS LAMP + POWER STEERING FULLY DISABLED AT IGNITION. ***
  V41          = V38 + the motor-rate cap flattened to 5325 with Q13 slopes zeroed (both mirror copies)
                   + the vestigial 0xC5FFC CRC. The 0xC6000 block is UNTOUCHED, so the governor slew
                   cals stay stock at 512/205.
                   *** V41 WAS FLASHED 2026-07-20 AND FIXED NEITHER SYMPTOM. ***
                   TWO consequences, both load-bearing:
                   (1) The motor-rate adaptive cap is FALSIFIED as the cause of either symptom. The
                       rate_cap_binding_analysis() relaxation-oscillator hypothesis below is DEAD as a
                       root cause; its arithmetic stands but its on-car prediction failed.
                   (2) V41 boots and drives CLEANLY while containing V40's ENTIRE cap-flatten change.
                       V41 is therefore a clean subtractive experiment on V40, and the only surviving
                       delta is the slew edit. *** V40's ignition fault is attributable to writing
                       0xFFFF into 0xC6206/0xC6208. *** See governor_slew_0xffff_postmortem().

  V42          = V38 + TWO independent changes:
                   Change 1 (CODE, one byte @0x454FE, bne->br): disable the state-4 governor
                     substitution in FUN_0004503c, which while gp-0x67fa==4 forbids the command
                     MAGNITUDE from increasing and writes the suppressed value back (cumulative).
                   Change 2 (CAL, 18 halfwords): zero the r26 adaptive torque-rate gain surface
                     (0xC6A72/86/9A/AE Y rows + overrides 0xC6444, 0xC643E).
                   *** V42 WAS FLASHED 2026-07-20/21. RESULT IS SPLIT AND BOTH HALVES MATTER: ***
                   (1) Change 1 FIXED THE HARD-TURN RATCHET on-car. The state-4 governor
                       substitution is a CONFIRMED root cause, not merely a hypothesis. It is the
                       first symptom in this lineage traced to a specific branch and closed by a
                       single-byte code edit. KEEP THIS IN EVERY SUBSEQUENT BUILD.
                   (2) Change 2 DID NOT touch the vibration. *** r26 IS FALSIFIED. *** With r24
                       (V39) and r26 (V42) both zeroed on-car to no effect, the ENTIRE Sensor-B
                       torque-rate derivative family is now eliminated as the vibration's cause --
                       this is the stronger, family-level negative that V39 alone could not deliver.

  V43          = **FLASHED -> FIXED NEITHER SYMPTOM. The dirty-derivative pole is FALSIFIED.** V38 + 11 bytes:
                   Change 1 (CODE, 1 byte @0x454FE): KEPT FROM V42 verbatim. Confirmed on-car, NOT
                     under test in V43.
                   Change 2 (CAL, 1 halfword @0xC644A, 1024 -> 32): restore the DISABLED first-order
                     pole immediately downstream of FUN_0003a382's RAW ONE-SAMPLE DIFFERENCE -- a
                     "dirty derivative". That lane is an UNFILTERED model-vs-reality residual on the
                     PHYSICAL Sensor-B torque sensor and feeds the aggregator, which IS the governor's
                     slew target. An EMA has UNITY DC GAIN, so this changes NO steady-state value --
                     only a settling time -- which makes it SIGN-AGNOSTIC where zeroing the term
                     would not be. See dirty_derivative_pole_analysis().
                   REVERTED: V42's Change 2. The r26 gain surface is asserted back at STOCK.
                   docs/HANDOFF-2026-07-21-v43-dirty-derivative-pole.md

  V44          = **BUILT + INDEPENDENTLY VERIFIED, NOT FLASHED. The current candidate.** V43 + 12 bytes:
                   Change 1 (CAL, 1 halfword @0xC644A, 32 -> 1024): REVERT V43's falsified pole to stock.
                   Change 2 (CAL, 2 low bytes): restore the base-assist DAMPING term hands-off --
                     0xD27C6 (mode 10 Y[0]) 0 -> 235, 0xD27DA (mode 11 Y[0]) 0 -> 234, each = that
                     table's own Y[1]. Below 2240 counts of driver torque the damping product
                     (FUN_00034350 -> gp-0x6bd0) was multiplied by ZERO; this makes it live hands-off.
                   Ratchet fix (0x454FE) carried through unchanged. See vibration_hands_off_analysis().
                   Safety: sign source FUN_00041464 confirmed 1 kHz -> damper phase -22 deg (cos +0.93);
                     net-dissipative even if the producer task runs at 100 Hz (cos +0.55). MITIGATION of
                     a Q=13.6 mechanical resonance, not a root-cause repair. Efficacy (is 235 enough?) is
                     a plant question the car resolves. docs/HANDOFF-2026-07-20-v44-handsoff-damping.md

  V45          = V44 + the governor slew-STEP selector edit (cal 0xC6206 512->205, narrowing the
                   hands-off rate-limit bandwidth ~4x; see governor_step_selector_bandwidth()).
                   *** FLASHED 2026-07-21. NO EFFECT ON THE VIBRATION. *** The bandwidth-narrowing
                   lever is now a NEGATIVE result, not merely untested.
  V46          = V45 + filtering FUN_0003a382's "Stage A" reinforcing carrier (cal 0xC6450 1024->32,
                   Q10 unity down to a heavy pole; see the FUN_0003a382 entry in assist_shaping_lanes()).
                   *** FLASHED 2026-07-21. NO EFFECT ON THE VIBRATION -- LEVER A IS FALSIFIED. ***
                   With V45 and V46 both null, the two add-on levers explored after V44 (governor
                   bandwidth, Stage A filtering) are both ruled out; neither is necessary or sufficient.
  V47          = **BUILT + VERIFIED, NOT FLASHED. The current candidate.** Drops V45's and V46's
                   falsified levers and returns to V44's mechanism -- ratchet fix (0x454FE, unchanged
                   since V42) + the base-assist DAMPING RESTORE -- but sized AGGRESSIVELY across BOTH
                   hands-off deadzones identified in the FUN_00034350 factor breakdown (see
                   assist_shaping_lanes()), not just one:
                     Factor C (voted driver torque, 0xD27C6/0xD27DA) Y[0] 0 -> 235/234, as V44.
                     Factor E (motor/resolver rate, 0xD2802/0xD2804/0xD2806 mode 10 and
                       0xD2816/0xD2818/0xD281A mode 11) raised toward the table's own Y[3]/Y[2]
                       region -> 700/750/800 across the low breakpoints, so the damper is live at
                       much lower motor rate, not just above the old Y[0]=0 floor at 60 counts.
                   *** MUST carry the matching float-mirror edit at cal 0xC6554/58/5C/60 for the
                   DTC-0x1d clamp lockstep (FUN_000347b8) if the clamp bound table is touched at all --
                   see the SAFETY TRAP note in the FUN_00034350 factor breakdown. ***
  V47 (FLASHED)= barely quieter at 5 mph, NO effect on the in-motion vibration. The motor-rate damper is
                   NON-COLLOCATED with the wheel-side mode -- see the collocation keystone in
                   docs/VIBRATION-DOSSIER.md and eps_loop_gain_model.py. STOP tuning it.
  V48A (FLASHED, FAILED) = V38 + ratchet + cal-only MUTE of the two strongest 21 Hz carriers: type-8
                   (mixer slot-8 sum gate 0xC4120 1->0) + FUN_0003a382 output (uVar27 0xC67B8/BA/BC
                   1024->256). Keeps 4x. build_v48a_tva.py. *** ON-CAR: did NOT fix the vibration ***
                   => the anti-damping is DISTRIBUTED, not in those two lanes => go to the notch.
  V48B (BUILT + GHIDRA-VERIFIED, UNFLASHED) = the 21.4 Hz NOTCH (biquad DF-I Q12, b0=4045 b1=-7949
                   b2=3977 a1=-7949 a2=3926; eps_v48b_notch_design.py + eps_v48b_cave_model.py) on a
                   FILTERED COPY of gp-0x4f60 (source-filter is NO-GO: shadow-lockstep + 2 hard-shutdown
                   monitors). CODE CAVE @0xC4B34 (138 B, 41 instrs) + trampoline jr @0x7FEAC (displaces
                   cmp r0,r8/mov r8,r14, re-exec'd last so the bge at 0x7feb0 sees correct flags) + 7
                   live carrier repoints gp-0x4f60->gp-0x1500 (FUN_0002c478/000352b4/0003a382/0003b49a/
                   0003b66a). 2 DORMANT reads (0x34392/0x34ace) left raw. New RAM: y1/out=gp-0x1500
                   (V31P flash-validated), x1/x2/y2=gp-0x14FC/FA/F8. build_v48b_tva.py + v48b_cave_asm.py;
                   50/50 CRC, RWD round-trip, every edit re-disassembled in Ghidra. Notch exactly unity
                   at DC (73/73). ***PENDING before flash: the lockstep-asymmetry red-team (is any
                   repointed carrier paired with a monitor that reads RAW gp-0x4f60?) + operator flash.***
                   The full loop-gain characterization + V48 menu is in docs/VIBRATION-DOSSIER.md.

  So the lineage is a story of three distinct cut mechanisms, each fixed in turn:
     V9  -> baseline (2x reach came first, in the V14->V18 sub-lineage folded into V31's base)
     V31 -> kills the SOFT EME  (slow windup shaper SM2/SM3)      -- see soft_eme_windup_shaper()
     V37 -> kills the GENTLE EME (STEER_STATUS debounce SM) + its DTC-0x49 side effect
                                                                  -- see steer_status_debounce_sm()

-------------------------------------------------------------------------------------------------------
EXECUTION MODEL  (Ghidra-verified this session; the one soft spot is the absolute clock frequency)
-------------------------------------------------------------------------------------------------------
This firmware runs a small RTOS. The steering/decider tasks are NOT called from a main loop -- their
addresses sit in a TCB-like table (~0xbb900) and a kernel scheduler dispatches them indirectly; each
returns through a context-switch tail (FUN_000847be, `eiret` off a per-task stack).

  BASE TICK       : OSTM0 timer interrupt. FUN_00014c5c programs OSTM0 compare = 0x1387F (79999) =>
                    an ~80000-cycle period. 80000 cyc @ 80 MHz == 1 ms,- so the base tick is *likely*
                    1 kHz - but the OSTM0 input-clock frequency was not independently confirmed, so
                    treat "1 ms" as strong-inference, not proven. w_steer_control_task bumps a 32-bit
                    counter (gp-0x6d28) once per call, consistent with once-per-base-tick.
                    [VERIFIED: OSTM0 as tick source + 80000-cycle reload | INFERRED: the 1 ms value]

  *** MAJOR CORRECTION 2026-07-20 -- THE "16-PHASE DUTY CYCLE" READING IS WRONG AND IS RETRACTED. ***
  The masks below are STATE masks, not phase masks. There is no round-robin phase counter anywhere in
  this task. [VERIFIED at instruction level]

      0x221bc  ld.bu -0x67fa[gp],r6     ; the ECU STATE-MACHINE byte
      0x221c2  andi 0xf,r6,r8           ; low nibble of the STATE
      0x221c6  shl  r8,r15,r25          ; r25 = 1 << state      (r15 = 1)
      0x221f8  andi 0xd30,r25,r23       ; r23 = does the CURRENT STATE belong to this set?

  gp-0x67fa is the top-level init/operating/fault state machine (lockstep-shadowed at gp-0x4c39;
  4 = init/activate, 8 = hard-shutdown/emergency, 10 = another system mode). It is dispatched by
  FUN_00019f7c to ~10 handlers that each write a LITERAL state constant -- including a direct 1 -> 8
  jump @0x19ffe that skips 2..7, which is categorically incompatible with a "+1 mod 16" counter.

  CONSEQUENCE: `andi 0xNNN` means "run this subsystem WHILE THE ECU IS IN ONE OF THESE STATES", not
  "run this on N of every 16 ticks". So the arbitration, aggregator, governor and shaper do NOT run at
  a divided sub-rate -- in whatever state is steady-state driving, they all run at the FULL
  w_steer_control_task rate, and they run in lockstep with each other. Any prior reasoning that derived
  an "effective ~100-250 Hz" from a 4/16 or 5/16 duty cycle is INVALID, including the argument that the
  Sensor-B derivative cadence is "compatible with tens-of-Hz feedback" -- that inference is withdrawn.

  STEERING TASK   : w_steer_control_task (FUN_0002214a), an RTOS task. Gate masks, all STATE sets:
                      arbitration FUN_00028ea6 @0x22522  <- andi 0x930 @0x22518  = states {4,5,8,11}
                      aggregator  FUN_0003aa2c @0x2291e  <- andi 0xc30 @0x2269a  = states {4,5,10,11}
                      governor    FUN_0004503c @0x2293a  \
                      shaper      FUN_00042af8 @0x229ce   > all share r23 <- andi 0xd30 @0x221f8
                      monitors    FUN_0004595a @0x22978,  |  = states {4,5,8,10,11}
                                  FUN_00045a20 @0x229c2,  |
                                  FUN_00043e44 @0x22a10  /
                    Note 0xd30 is a strict SUPERSET of 0xc30, so governor+shaper fire whenever the
                    aggregator does. [VERIFIED]
                    *** NOTE state 4 is inside ALL THREE masks, and the governor has a SUBSTITUTION
                    branch @0x454f8-0x45526 that, while gp-0x67fa == 4, forbids the command MAGNITUDE
                    from increasing. State 4 is therefore an active-but-ratcheting state, not a
                    quiescent one -- see the ratchet investigation. ***
                    [OPEN] which state value is steady-state normal driving. Cheap to settle on-car:
                    flashing-2020accord/eps-read-dtcs.py already live-reads 0xFEDF1806 (= gp-0x67fa).

  TASK RATE       : *** UNRESOLVED, and now the dominant uncertainty for every Hz claim. ***
                    w_steer_control_task has ZERO direct JARL callers image-wide. Its address appears
                    exactly once as a raw pointer, at ROM 0xbb928, inside an RTOS task-control-block
                    array at 0xbb8c0-0xbb9bf (4 records x 0x30 bytes; steer task = ID 1; siblings
                    FUN_00022a88/FUN_00022b20/FUN_00022b24). The code that WALKS that table was not
                    located -- no xrefs to 0xbb8c0/0xbb928 -- so it is reached through a runtime-loaded
                    base pointer. Until that walker is found, cycle counts CANNOT be converted to Hz.
                    Cycle counts in this model are exact; milliseconds are deliberately not computed.

  SENSOR-B RATE   : FUN_0007f3f8 calls derivative producer FUN_0007e74a, updating lockstep pair
                     gp-0x4f62/gp-0x4488; FUN_0003aa2c consumes the held derivative. Delay
                     tp+0x7c42 = 4 spans four PRODUCER samples. The masks are STATE sets (above), so
                     no producer/consumer RATE MISMATCH exists -- the previously claimed 5/16-vs-4/16
                     beat frequency was an artifact of the retracted phase-mask reading.
                     [VERIFIED: functions, delay, lockstep | OPEN: wall-clock Hz]

  DECIDER TASK    : the engage decider + deliver-commit run from a sibling RTOS task FUN_00022ca0
                    (jarl FUN_000413ae dispatcher @0x22e9c ; jarl FUN_0003d4a2 @0x22dd8). [VERIFIED]

  FOC + PWM (ISR) : one shared EI-level interrupt trampoline FUN_0001492a (full V850E2 EI prologue;
                    a genuine hardware entry) dispatches on the EIIC cause code:
                      EIIC 0x600 -> FUN_0006404c  ADC-complete -> FOC (Park/Clarke/PI/SVPWM 0x71272)
                      EIIC 0x970 -> FUN_00061614  -> FUN_0006c5ce writes TSG20 CMPU/V/W (= MOTOR)
                    (plus several other EIIC codes: 0x340/0x470/0x110/0x100/0xf0). The FOC inner loop
                    is fast and synchronous to the ADC/PWM carrier; the carrier frequency itself is
                    UNRESOLVED (TSG20 clock/register semantics not confirmed; init writes 5000/5160).
                    [VERIFIED: EIIC dispatch + both handler chains byte-exact | OPEN: carrier Hz]

  CAN RX          : hardware mailbox RX interrupt stages STEER_TORQUE into the routed buffer. Its EIIC
                    trampoline was not among the 5 `eiret` functions found; the raw EIBASE vector table
                    was not located this session. [OPEN: exact CAN-RX ISR entry / rate]

=======================================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional


# =====================================================================================================
# SECTION 0 -- CALIBRATION CONSTANTS
# -----------------------------------------------------------------------------------------------------
# Every named field is a firmware calibration in the CRC-protected 0xC6000 block (unless noted). The
# default value is the STOCK (V9b) value. Build variants override a subset -- see for_build().
# Addresses are given per-field so the code body can stay address-free.
#
#   Memory addresses (all tp-relative, tp=0xBF000; absolute in parentheses):
#     LKAS reach ......... gain tp+0x746c(0xC646C) arb_clamp tp+0x71b4(0xC61B4)
#                          pack_clamp tp+0x71b2(0xC61B2) reengage_ramp tp+0x74de(0xC64DE)
#     Setpoint ........... scale=-4 & +/-0x4000 clamp are CODE literals in FUN_00052676 (not cals)
#     Debounce SM ........ torque tp+0x74b4/b5/b7/b6 (0xC64B4/B5/B7/B6)
#                          rate   tp+0x71c0/c2/c4    (0xC61C0/C2/C4)
#                          count  tp+0x74e2(0xC64E2)=5   hold tp+0x74df(0xC64DF)=100
#     DTC-0x49 counter ... gate tp+0x74b8(0xC64B8)=112  sat tp+0x74e0+tp+0x74e1(0xC64E0/E1)=50+50
#     Engage decider ..... torqueMAX tp+0x7312(0xC6312)=320  angle tp+0x7354(0xC6354)=4825
#                          rate tp+0x7310(0xC6310)=1600  gate6 tp+0x71ce(0xC61CE)=4096
#                          gate7 tp+0x71cc(0xC61CC)=3584
#     Soft-EME shaper .... corridorY tp+0x774e/50/5a/5c(0xC674E/50/5A/5C)
#                          boostY int tp+0x7768/6a/6c(0xC6768/6A/6C) float mirror 0xC65C4/C8/CC
#                          authority_scale tp+0x71da(0xC61DA)=1092
#                          SM2_arm tp+0x7422(0xC6422)=16384  SM3_clamp tp+0x71dc(0xC61DC)=30720
#                          SM1_arm tp+0x71de(0xC61DE)=2048   corridor_gate tp+0x7156(0xC6156)=9216
#                          boost_latch_auth tp+0x741e(0xC641E)=16384 boost_latch_dwell tp+0x74e3(0xC64E3)=20
#     Runtime governor ... tp+0x7202(0xC6202)=4762; adaptive tables 0xC520C/0xC5224,
#                          Q13 slopes 0xC5038/0xC5030, shift tp+0x6160(0xC5160)=13
# =====================================================================================================

V9_FULL_SCALE_POSITIVE = (15360 * 891) >> 15
V9_FULL_SCALE_NEGATIVE = (-15360 * 891) >> 15
V9_FULL_SCALE_MIN_MAGNITUDE = min(abs(V9_FULL_SCALE_POSITIVE), abs(V9_FULL_SCALE_NEGATIVE))


@dataclass
class Calibration:
    # ---- LKAS reach (V14/V18 lineage, retained by V31 & V37) --------------------------------------
    lkas_output_gain: int = 891          # Q15 arb output gain. V31/V37=1782; V38=3564 (4x stock)
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

    # ---- Low-speed steer lockout: the two-sided speed window at the top of FUN_00028ea6 ------------
    # [SOLVED 2026-07-24; sole-reader re-confirmed in Python 2026-07-27] Compared against gp-0x6a5e =
    # VOTED VEHICLE SPEED at 64.0625 counts/km/h. Failing the window is the ONLY writer of
    # STEER_STATUS=3, which gates BOTH STEER_CONTROL_ACTIVE and the authority ramp (intra-function
    # `cmp 0x2` @0x29382). Each cal has exactly ONE reader image-wide.
    speed_window_lo: int = 320           # tp+0x72ea (0xC62EA) = 4.995 km/h = 3.104 mph. V53 -> 0
    speed_window_hi: int = 12800         # tp+0x72e8 (0xC62E8) = 199.8 km/h. NEVER edited: the 0x7FFF
                                         #   SNA sentinel (32767) must keep failing this bound.
    # NB the window BYPASS gp-0x68b3 is deliberately NOT a field here -- it is a runtime RAM flag, set
    # in FUN_0004d0d0 only when gp-0x6a62 == 0 (exactly true standstill), so it is DERIVED from speed
    # inside steer_status_low_speed_lockout() rather than configured. That derivation is what makes
    # stock permit 0 km/h yet forbid 1-319 counts.

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
    arb_setpoint_limit: int = 15360      # symmetric +/- clamp on the LKAS setpoint.
                                         # [VERIFIED 2026-07-18, byte-dumped + Ghidra] this is NOT a
                                         # shaped curve: it is a DEGENERATE 9-point LERP whose Y row is
                                         # FLAT 15360 at every breakpoint, in ALL 28 records across all
                                         # 5 banks (0xE4180/0xE5180/0xE6180/0xE7180/0xE8100). The axis
                                         # input is irrelevant to the output; both out-of-range early
                                         # exits (@0x28fec -> Y[0], @0x29002 -> Y[8]) also return 15360.
                                         # Selected by gp-0x674e via pointer array 0xCB844 (the ONLY
                                         # code site referencing it, @0x28FCE). gp-0x674e is STATIC per
                                         # part number: written @0x4272a from tp+0xE01A (base 0xCD01A,
                                         # stride 0x24); A160 = ECU-ID entry 2 ("TVAA1") -> mode 1 ->
                                         # live record 0xE41A8, whose Y row is 0xE41BC..0xE41CC.
                                         # Clips the full-scale setpoint: openpilot CAR.HONDA_ACCORD
                                         # uses torqueBP 4096 -> setpoint 4096*4 = 16384 > 15360, so the
                                         # top 6.25% of the command range is clamped (= +6.71% top-end
                                         # torque if raised to 16384, at EVERY build tier -- the arb
                                         # output clamp never binds). Raising it is SAFE: no float twin
                                         # of 15360 exists anywhere in the image, and the gentle-EME
                                         # debounce is driven by gp-0x4f60 (driver torque), not by this.
                                         #
                                         # AXIS: gp-0x6a5e (the AVG voter = DRIVER COLUMN TORQUE), read
                                         # @0x28f0e -- so the clamp is nominally gated on how hard the
                                         # driver is pushing. Moot in stock, since the Y row is flat.
                                         #
                                         # PATCH SURFACE: gp-0x674e is NOT the 0..15 variant
                                         # slot index. FUN_00057f8e returns the slot (0..15, matching a
                                         # 5-byte HW-ID key at 0xCD000+slot*0x24 against gp-0x6408..640C);
                                         # that slot is then used as an INDEX to FETCH the selector byte
                                         # (`mulhi 0x24` @0x4271e, `ld.bu 0xe01a` @0x42724). Across all
                                         # 16 slots gp-0x674e takes only {0,1,3,4,6,7,8,9}; for the TVA
                                         # (Accord) slots 0-7 it is only 0 or 1. Slots 8-15 are TVC/TWA
                                         # parts -- other vehicles. V38 patches all 8 reachable records,
                                         # 72 halfwords total, so the raise is independent of HW-ID slot
                                         # resolution. Live A160 remains selector 1 @0xE41BC..0xE41CC.
                                         #
                                         # SHIPPED IN V38: build_v38_tva.py covers [0xE4000,0xE4FFC) and
                                         # [0xE5000,0xE5FFC), rewrites both trailers, and verifies 49/49.
    assist_ramp_ticks: int = 10          # tp+0x74d1 * 10; assist engage-ramp dwell per state (gp-0x68c8)
    distribute_lkas_lane_clamp: int = 0x2800   # LKAS rides the +/-0x2800 distributor lane
    mixer_gate_clamp: int = 0x2800       # gate: |x|<=0x2800 ? x : 0x7FFF-sentinel
    shaper_final_clamp: int = 0x2000     # shaper output final +/-0x2000 clamp
    runtime_governor: int = 4762         # NOMINAL CEILING of the computed runtime governor gp-0x4f64
                                          #   (cal 0xC6202). NOT a flat clamp -- see soft_eme_windup_shaper
                                          #   for the MIN(4762, adaptive LERP, unresolved budget B) schedule.
    governor_slew_step_normal: int = 512 # tp+0x7206 (0xC6206), before a Q15 step scale. V40 -> 0xFFFF
    governor_slew_step_alt: int = 205    # tp+0x7208 (0xC6208). V40 -> 0xFFFF
                                         # Step selector is gp-0x67f5: ==0 picks normal, else alt.
                                         # The voter FUN_00041eec forces gp-0x67f5=0xFF with NO
                                         # debounce once raw driver torque diverges from the vote by
                                         # >=65 counts, and debounces it to 1 while voted |torque| >=
                                         # 640 -- so a hard dynamic turn is PINNED to the slow step.

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
        """Return the calibration set for V9, V31, V37, V38, or the experimental V39."""
        cal = Calibration(build=name)
        if name == "V9":
            return cal
        # --- V31: 2x reach + soft-EME fix (corridor x4 + boost floor 4096) --------------------------
        cal = replace(
            cal,
            lkas_output_gain=1782, arb_output_clamp=1024, pack_output_clamp=1024, reengage_ramp_step=0x1B,
            corridor_upper=4096, corridor_lower=-4096, boost_floor=4096, boost_y1=4096, boost_y2=4096,
        )
        if name == "V31":
            return cal
        # --- V37 onward: gentle-EME debounce SM off + DTC-0x49 counter off -------------------------
        if name in ("V37", "V38", "V39", "V40", "V41", "V42", "V53", "V54", "V55"):
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
                lkas_output_gain=3564, arb_output_clamp=2048, pack_output_clamp=2048,
                corridor_upper=5120, corridor_lower=-5120,
                boost_floor=5120, boost_y1=5120, boost_y2=5120,
                arb_setpoint_limit=16384,
            )
            if name == "V38":
                return cal
            # --- V53: the V38 cal set + the FOURFRAME2 read-only telemetry cave + min steer speed 0.
            # ✅ FLASHED AND DRIVEN 2026-07-27 -- the speed-window prediction below is CONFIRMED on-car
            # (route 1a: STEER_STATUS=0 in 5,995/5,995 frames, 226 frames of STEER_CONTROL_ACTIVE=1
            # below 5 km/h). The cave is PASSIVE (ld.hu reads straight into CAN mailbox DAT registers,
            # never a store back into firmware RAM), so it changes nothing modelled here; the single
            # modelled change is the speed-window LO bound. ⚠ V53 is cut from V38 like FOURFRAME2 and
            # therefore does NOT carry V42's confirmed ratchet fix.
            # ⚠ The cave itself NEVER TRANSMITTED -- 0 frames of 0x6A0-0x6A3 -- and the null is
            # uninterpretable (6 stock EPS broadcast IDs are equally absent at the comma tap). That is
            # a channel fact, not a firmware-behaviour fact, so it does not affect this model.
            if name == "V53":
                return replace(cal, speed_window_lo=0)
            # --- V54: V38 + the SAME speed-window edit + a 5-bit gp-0x6966 authority probe piggybacked
            # into CAN 330 (0x14A) byte4 bits 7:3. ✅ FLASHED AND DRIVEN 2026-07-27, fault-free.
            # The probe is REPORT-ONLY (it reads gp-0x6966 and read-modify-writes ONE CAN payload byte
            # that no control path consumes), so V54 is behaviourally IDENTICAL to V53 in everything
            # this model computes.
            #
            # ⚠ CORRECTION to the V53 note above: these caves are NOT "never a store back into firmware
            # RAM". They DO write firmware RAM -- st.b into the CAN TX payload buffer at gp-0x1514. The
            # reason they are safe is narrower and must be stated correctly: the byte they write is a
            # TX payload byte no control path reads, and they allocate no scratch RAM.
            #
            # ★★ THE MEASUREMENT (route 1b, 5,989/5,989 frames): wire == 1 throughout, i.e.
            # gp-0x6966 in [0,127] -- 0.39% of its saturation -- with ZERO variation, including 17% of
            # requesting frames at openpilot's +-4096 rail. This is not "authority happened to be low":
            # gp-0x6966 is the soft-EME wind-up magnitude |gp-0x3570>>15| * 1092 >> 10, and V31's boost
            # floor (0xC6768/6A/6C = 5120, NOT the 4096 the V31 memory records) holds the bound above
            # the worst-case command so the integrator can never wind. Authority is therefore ~0 BY
            # DESIGN on every V31+ build, at any speed, in any normal driving.
            # ⇒ The 0xC6AF0 LERP selects Y = 32768 (unity) in 100% of normal operation, so the
            # FUN_0003a382 residual lane runs at its FULL output bound -- "keep-live" is a no-op and
            # mute is the only meaningful edit. GATE 2 (the lane's damping sign) remains OPEN.
            # ⇒ Do NOT re-drive faster to move this reading. It is wind-up-driven, not speed-driven.
            if name == "V54":
                return replace(cal, speed_window_lo=0)
            # --- V55: V38 + the SAME speed-window edit + a DUAL report-only probe on the same proven
            # 0x14A byte4 piggyback: bit7 = (damper variant INDEX >= 10), bits 6:3 = a 4-bit window on
            # gp-0x6b98, the FINAL MERGED COMMAND (the only path to FOC). BUILT 2026-07-28, UNFLASHED.
            # Report-only, so again behaviourally identical to V53/V54 here.
            #
            # V55 exists to PARTITION rather than to test a lever: every falsified vibration lever
            # (V39, V41, V42ch2, V43, V45, V46, V48A, V52C) sits on the command path and assumes the
            # ~20 Hz is COMMANDED. If it is absent from gp-0x6b98, all eight were doomed by
            # construction and the search moves to the plant. A null BOUNDS the command's 20 Hz content
            # to ~<512 counts (one level) against the sensor's ~550 rms -- it does not prove zero, and
            # a 100 Hz probe cannot separate 20 Hz from 80 Hz.
            if name == "V55":
                return replace(cal, speed_window_lo=0)
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
            f"(expected V9, V31, V37, V38, V39, V40, V41, V42, V53, V54, or V55)")


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
    # *** 2026-07-21 said this field drives nothing downstream because a full audit found ZERO
    # vehicle-speed input anywhere in the command chain. 🛑 THAT SCOPE IS FALSIFIED -- see
    # steer_status_low_speed_lockout() below and the corrected note in can_rx_stage_steer_torque().
    # Two real speed consumers exist: (1) FUN_00028ea6's window vs cals 0xC62EA/0xC62E8, which gates
    # STEER_CONTROL_ACTIVE and the authority ramp; (2) the G1 governor FUN_0004503c reading gp-0x6a64
    # against cal 0xC6316 = 640 to SKIP the slew limiter below ~10 km/h. What SURVIVES from that audit
    # is narrower and still true: none of the 9 AGGREGATOR LANES reads road speed, and every
    # rate-adaptive TABLE is keyed on motor/resolver electrical-angle rate (gp-0x6ac0), not road speed.
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
    # gp-0x6ad0 input to FUN_000456a4.
    # *** CEILING: 2560. An intermediate 2026-07-19 edit raised this to 4762 and was WRONG -- that
    # figure was a conflation with the unrelated governor cal 0xC6202=4762 in m_motor_torque_governor.
    # RETRACTED and restored. Lesson: it was propagated from a subagent report without the lead
    # reading the table bytes; the bytes were read on the second pass and did not support it. ***
    #
    # *** FULLY DISASSEMBLED 2026-07-20 -- BOTH TABLES ARE 3-POINT, NOT 2-POINT. [VERIFIED] ***
    # LERP1 (the GATE THRESHOLD), base tp+0x7830 == 0xC6830, raw `03 00 D8 0E A0 0F 36 10 88 13 DD 0B E8 03`:
    #   X = (3800, 4000, 4150) @ 0xC6832/34/36   Y = (5000, 3037, 1000) @ 0xC6838/3A/3C   -- FALLING
    # LERP2 (the MIN-CLAMP), base tp+0x77d0 == 0xC67D0, raw `03 00 80 0C D8 0E 36 10 00 02 00 04 00 0A`:
    #   X = (3200, 3800, 4150) @ 0xC67D2/D4/D6   Y = (512, 1024, 2560) @ 0xC67D8/DA/DC     -- RISING
    # Gain cal 0xC6204 = 3072, and 3072/1024 reduces to an exact integer 3 (no rounding loss):
    #   term = sign(-gp-0x6abe) * MIN( (gp-0x6ac0 - LERP1(gp-0x6a10)) * 3, LERP2(gp-0x6a10) )
    #   forced to 0 when gp-0x6ac0 <= LERP1(gp-0x6a10).
    #
    # *** THE GATE IS A BARE, UNHYSTERETIC 2-INSTRUCTION COMPARE. [VERIFIED @0x45780-0x4578a] ***
    #   0x45780 ld.hu -0x6ac0[gp],r6   ; RATE loaded LIVE, no filtered copy
    #   0x45784 zxh r15                ; r15 = LERP1(INDEX), recomputed from scratch every call @0x45716
    #   0x45786 cmp r6,r15
    #   0x45788 bc 0x4578e             ; LERP1 < RATE -> term path
    #   0x4578a jr 0x458b6             ; else -> term = 0
    # NO second release threshold, NO counter/dwell, NO persisted state, NO debounce. Both operands
    # are read fresh each cycle. The term therefore steps 0 -> full clamped magnitude in ONE cycle
    # whenever the two signals' relative order flips -- up to 2560 counts, which EXCEEDS V38's
    # ~1782-count primary LKAS lane. That is a structurally sufficient chatter source.
    #
    # *** gp-0x6ad0 IS A WRITE-ONLY TELEMETRY MIRROR -- CORRECTION OF RECORD. [VERIFIED] ***
    # Exactly ONE operand referencing 6ad0 exists image-wide: `st.h r6,-0x6ad0,gp` @0x458c4. Zero
    # readers. The functional sum never goes through it -- r6 is added to r12 @0x458c8 in the same
    # instruction stream, same cycle it was computed. So there is no reload, no delay, no ramp, and
    # nothing can filter this term. (The model keeps the field as a replay input; it is the VALUE
    # that is real, not the variable's role as a data path.)
    #
    # *** gp-0x6a10 IS NOT A FILTERED gp-0x6ac0 -- the self-reference worry is REFUTED. [VERIFIED] ***
    # Sole non-zeroing producer FUN_0003fc16:
    #   gp-0x6a10 = min( abs( gp-0x69ca - clamp(gp-0x69e0 + DAT_641c, +/-(tp+0x733a)) ), ceiling )
    #   and it is forced to 0 outright unless gp-0x67fe (assist substate) is 1 or 2.
    # gp-0x69ca / gp-0x69e0 are written by the ENGAGE-SM cluster (FUN_0003bd7c, FUN_0003e462/e6d8/e760,
    # FUN_0003f884, FUN_0003fd9c) -- a completely separate producer chain from gp-0x6ac0's resolver/FOC
    # path (FUN_00041464). They share no source register, filter, or call chain.
    # *** CLOSED 2026-07-20 -- gp-0x6a10 IS NOT COMMAND-DERIVED. CLEAN NEGATIVE. [VERIFIED] ***
    # Full decompiles of FUN_0003bd7c (sole non-zero writer of gp-0x69ca) and FUN_0003f884 (sole
    # writer of gp-0x69e0). Both are built from a 36000-scale ANGLE/POSITION accumulator cluster
    # (gp-0x69d0/d2/d4/de, gp-0x69c8, gp-0x6cc0, gp-0x6cdc, gp-0x35f4), gated by the FOC-mode/engage
    # state machine (gp-0x6772, gp-0x67fe, gp-0x671d), plus -- in FUN_0003f884 -- DRIVER hand torque
    # gp-0x4f60. Every line of both was read for any reference to gp-0x69ae (setpoint), gp-0x6b3c
    # (arb out), gp-0x6b4c (LKAS lane), gp-0x6b94 (aggregator), gp-0x6ace (governed) or gp-0x6b98
    # (final command): NONE APPEARS IN EITHER FUNCTION.
    # CONSEQUENCE: the gate threshold LERP1(gp-0x6a10) sits entirely upstream of, and structurally
    # independent from, the LKAS gain / aggregator / governor / shaper. So the invariance argument
    # SURVIVES here -- V38 and stock see the same INDEX behaviour for the same physical steering
    # motion, and FUN_000456a4 is DEPRIORITISED as a V38-vs-stock regression candidate. The
    # no-hysteresis and dead-mirror findings above remain true as structural facts about the
    # firmware; what fails is the argument that V38 would make this gate fire DIFFERENTLY.
    # Residual caveat, flagged not papered over: gp-0x69ca/gp-0x69e0 do track physical steering ANGLE,
    # and angle is a physical consequence of delivered torque. That is the same indirect
    # plant-feedback path the invariance argument already assumes is matched, not a firmware bypass.
    # RELATED [VERIFIED]: gp-0x67fe has exactly 4 writers, all inside FUN_0003bd7c, gated on FOC-mode
    # gp-0x6772 reaching 4/5 AND a diagnostic AND a startup dwell, behind a sticky latch gp-0x6845
    # that clears only on a full FOC-mode reset. It is a per-drive-cycle readiness state, NOT a
    # tens-of-Hz toggle -- so it is not a second zeroing discontinuity. [INFERRED: dwell timing]
    #
    # BLAST RADIUS: all 11 cal cells above (both table bases, all X/Y breakpoints, and the 3072 gain)
    # have ZERO consumers anywhere outside FUN_000456a4 -- exhaustive 185,693-instruction operand sweep.
    # This is the cleanest patch surface found in the kit to date. [VERIFIED]
    #
    # CONSEQUENCE for the collapse boundary: the conservative gp-0x6acc envelope is 4762 governor +
    # 2560 compensation = 7322, BELOW the +/-8192 sanitize. So the "gp-0x6acc crosses 8192 and
    # gp-0x6b08 collapses to zero" mechanism is NOT reachable on static grounds -- but the margin is
    # only 870 counts, and it rests on the governor's Q15 limiter-bank output never exceeding unity,
    # which is a MODEL DEFAULT and not a verified fact. gp-0x6acc = gp-0x6ace + gp-0x6ad0 with NO
    # clamp at the write (the alternate branch in FUN_000456a4 is provably dead: it needs cal
    # 0xC64BA==0xE9 but the byte is 0, and even then 0xC648E=0 / 0xC6134=1000 make it a no-op).
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
    col_torque_avg: int = 0       # gp-0x6a5e (0xFEDF15A2) AVG voter
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
    assist_mode: int = 10         # gp+0x63fd (0xFEDFE3FD) POSITIVE displacement; assist curve select
                                  #   0..33. =10 for THIS car (ECU-ID slot 2, col tp+0xE012)
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
    assist_rate_state: int = 0    # gp-0x6bb2/4/6/8 internal cluster behind the FUN_0004613e rate limiter
    assist_polarity: int = 1      # gp-0x6752 assist polarity (-1/0/+1)
    assist_lane: int = 0          # gp-0x6bbe (0xFEDF1442) the base-assist aggregator lane
    assist_state_671a: int = 0     # exact branch input; physical state label unresolved
    assist_gate_671d: int = 0
    assist_gate_683c: int = 0
    assist_gate_6b5e: int = 0
    assist_slope_q10: Optional[int] = None  # gp-0x69a4; unresolved producer, replay when captured
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
    governed_demand: int = 0             # gp-0x6ace, after FUN_0004503c clamp/Q15/slew
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
    Stage the incoming CAN 0xE4 STEER_TORQUE into the routed LKAS buffer.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Scheduled by : CAN hardware mailbox RX interrupt (mailbox 0x36 for 0xE4) -> dispatcher.  [ISR]
      Rate         : event-driven, once per received 0xE4 frame (~100 Hz on the wire; openpilot TX
                     cadence). Exact EI trampoline for CAN-RX not located this session. [rate: OPEN]
      Functions    : FUN_0001cf30  CAN mailbox/MID filter config (0xE4 entry @ 0xB7394)
                     FUN_0001ce68  universal RX extractor -> shared scratch 0xFEDF68CC
                     FUN_0001ddd0  s_can_rx_dispatch: route table @0xB739C -> slot 17 dest 0xFEDF6BD8
                     FUN_00021724  s_get_lkas_steer_torque_be: reads 0xFEDF6BD8/9, returns BE int16
      Buffers      : 0xFEDF68CC shared RX scratch (overwritten every frame; NOT the LKAS buffer)
                     0xFEDF6BD8 routed LKAS buffer (int16 BE @+0/+1; flags @+2,+4)
    CONFIDENCE     : [CONFIRMED] the 0xE4 STEER_TORQUE payload + [VERIFIED] the routing to 0xFEDF6BD8.

    The 5 intake gates (checksum / counter / STATUS_WORD / timeout) are COMMS-VALIDITY only -- they
    cannot cut LKAS based on a torque/rate *value*, so a road bump cannot trip them.

    -------------------------------------------------------------------------------------------------
    SUB-3-MPH LKAS CUTOFF -- ★ IT *IS* A FIRMWARE SPEED GATE. CAL 0xC62EA. [SOLVED 2026-07-24]
    -------------------------------------------------------------------------------------------------
    🛑 EVERYTHING THIS BLOCK SAID BEFORE 2026-07-24 WAS WRONG AND IS RETAINED ONLY AS A METHOD LESSON.
    It claimed "NOT by any speed gate in this firmware command chain" and "the exact firmware low-speed
    threshold is unquantified", on the strength of a dedicated trace that found no discrete speed
    threshold. That trace returned a FALSE NEGATIVE: it required a two-sided compare FOLLOWED BY a
    boolean store, and the window's boolean `bVar2` is never stored to RAM -- it lives in a register and
    is consumed immediately by the AND-chain. See docs/HANDOFF-2026-07-24-low-speed-steer-lockout.md
    Sec.4d. *** Method rule: never require "compare -> boolean store"; search for the compare alone. ***

    THE REAL MECHANISM -- a two-sided speed window at the TOP of FUN_00028ea6 (the LIVE ~1 kHz
    m_steer_torque_arbitration, sole caller FUN_0002214a @0x22522):
        0x28EB6  ld.hu 0x72e8[tp],r2    ; r2 = cal 0xC62E8 = 12800 = 199.8 km/h   HI bound
        0x28EBC  ld.hu 0x72ea[tp],lp    ; lp = cal 0xC62EA =   320 =   4.995 km/h LO bound  <== LEVER
        0x290C8  cmp r2,r10  / setfnh r9  ; r9 = (speed <= 12800)
        0x290D2  cmp lp,r10  / setfnc r7  ; r7 = (speed >=   320)      [unsigned]
        0x290EA  ld.bu -0x68b3[gp],r13    ; BYPASS: if != 0 the window is ignored
      compared against gp-0x6a5e = VOTED VEHICLE SPEED (FUN_00041eec, 5-channel voter; unit
      64.0625 counts/km/h from FUN_000522fe's x41>>6 on CAN 0x158 XMISSION_SPEED2 @0.01 km/h).
      Failing the window is the ONLY writer of STEER_STATUS=3 (0x29192 mov 3,r6 / 0x29194 st.b).
      Each cal has EXACTLY ONE reader image-wide (re-confirmed by Python sweep of both V850E2
      encodings, 2026-07-27: the `disp|1` halfword 0x72EB occurs once, at 0x28EBE).

    ✅ IT IS AUTHORITY-BEARING, NOT REPORT-ONLY. The gating is INTRA-FUNCTION (an earlier sweep for
    *external* gp-0x6807 readers structurally could not see it): 0x2937E ld.bu -0x6807 / 0x29382
    cmp 0x2 / 0x29384 bnh guards BOTH the STEER_CONTROL_ACTIVE=1 write (0x293A6, gp-0x6806) AND the
    authority ramp (0x293AC, gp-0x69b0 += cal 0xC63F8=33). All four live gp-0x6806=1 writers require
    STEER_STATUS <= 2. So lowering 0xC62EA restores REAL authority, not just the reported label.

    ★ THE STANDSTILL ASYMMETRY IS DELIBERATE. gp-0x68b3 (the window bypass) is written in FUN_0004d0d0
    ONLY when gp-0x6a62 == 0, i.e. EXACTLY at true standstill. So stock PERMITS 0 km/h and FORBIDS
    1-319 counts (0 < v < 5 km/h). That is designed, not incidental -- and it is why V53 sets the LO
    bound to 0 rather than to 64: 0 REMOVES that discontinuity instead of moving it.

    openpilot's contribution is real but is NOT the whole story, and the two numbers coincide:
      1) [openpilot] STEER_GLOBAL_MIN_SPEED = 3*MPH_TO_MS. ⚠ The StarPilot fork actually on the car
         runs CP.minSteerSpeed = 0.0 and steerAtStandstill = False, so openpilot is NOT the obstacle
         below 3 mph -- it will command down to a dead stop but not AT one.
      2) [EPS] the 0xC62EA window above, releasing at 4.995 km/h = 3.104 mph. On-car rlog measurement
         puts the release edge in the 3-4 mph bucket, matching the cal to within the bucket width.

    *** V53 CONSEQUENCE -- PREDICTION MADE 2026-07-27, ✅ CONFIRMED ON-CAR THE SAME DAY. ***
    V53 sets 0xC62EA = 0, making the LO test unconditionally true. Combined with this model's separate
    finding that STEER_STATUS 4 and 7 are UNREACHABLE on the V37/V38 cal set (see the engage-SM
    section), STEER_STATUS=3 becomes unreachable too except on an implausible-speed HI-bound failure.
    PREDICTED: the ST=3 excursion that fires every time the car crosses ~3 mph disappears.
    MEASURED (route 75604b0a432fdc89_0000001a, segment 0, 58 s, raw CAN 399 decoded independently of
    carState):
        STEER_STATUS == 0 in 5,995 / 5,995 frames  -- ST=3 never fires, anywhere, at any speed
        STEER_CONTROL_ACTIVE == 1 in 226 frames below 5 km/h, with openpilot TORQUE_REQUEST=1 and
            |STEER_TORQUE| > 50 in 224 of them   -- a cell that is IDENTICALLY EMPTY on V38
    This is a clean confirmation of the whole chain 0xC62EA -> window -> ST=3 -> STEER_CONTROL_ACTIVE,
    and it is the first time the model has predicted an on-car state-machine change in advance.
    ⚠ STILL OPEN: what this did to the VIBRATION is unanalysed. The prediction was two-sided ("if the
    transient reading is right V53 should change it; if the sustained reading is right it should not")
    and neither arm has been tested -- route 1a is a single 58 s segment and the low-speed engaged cell
    has not been examined for 21 Hz content. Removing ONE ramp-restart route is not removing the
    mechanism: other disengage arms still zero gp-0x6806.
    ⚠ The HI bound 0xC62E8 = 12800 is deliberately UNTOUCHED, so the 0x7FFF SNA sentinel (32767) still
    fails the window and an invalid speed still locks out exactly as at stock.

    *** COMPLETENESS PASS 2026-07-21 -- "NO VEHICLE-SPEED INPUT ANYWHERE": 🛑 FALSIFIED TWICE. ***
    That pass concluded NONE of the 9 aggregator lanes reads a road-speed signal, and that every
    rate-adaptive table is keyed on MOTOR/resolver electrical-angle rate. Two later results overturn
    the "anywhere" scope, though the per-lane observation still stands for the aggregator lanes:
      1) FUN_00028ea6 reads gp-0x6a5e (voted speed) for the window above -- in the command path.
      2) The G1 governor FUN_0004503c reads gp-0x6a64 (voted speed) at 0x451E2/0x45308 against cal
         0xC6316 = 640 (9.99 km/h) and SKIPS the slew-rate limiter below it (0x45310/14/16), so r26
         tracks its MIN-chain value instantly -- more responsive at low speed, not more restrictive.
    ⇒ Treat "no vehicle-speed input in the command path" as RETIRED. Do not cite it.

    *** PLANT ARCHITECTURE (external research, 2026-07-21) -- WHY THE VIBRATION PEAKS NEAR ~5 MPH. ***
    The 2020 Accord EPS is a DUAL-PINION design: the assist motor drives a SECOND pinion on the rack,
    mounted off the steering-column axis specifically for vibration isolation from the driver's hands.
    Sensor A and Sensor B (gp-0x682f / gp-0x4f60 elsewhere in this model) are the MAIN and SUB Hall
    channels of ONE torsion-bar torque sensor at the column input, not two independent sensors --
    corroborated by Honda DTC C1420 "Main/Sub Torque Sensor Incorrect Correlation", which only makes
    sense as a cross-check between two channels of a shared sensor. Motor position is sensed by a
    resolver (matches gp-0x6ac0's atan2 sin/cos decode elsewhere in this model). The measured ~21.4 Hz,
    Q~=13.6 mode is therefore best read as a RACK-COUPLED DRIVELINE RESONANCE, sensed at the torsion
    bar -- not a control-loop artifact. openpilot config for this platform: "Honda Bosch A connector",
    minSteerSpeed=0, minEnableSpeed=3 mph.

    🛑 CORRECTED 2026-07-24/27 -- the original claim here ("the ~5 mph peak is NOT a firmware speed
    gate; none exists") rested on the falsified negative above and must not be cited. A firmware speed
    gate DOES exist: cal 0xC62EA = 320 = 4.995 km/h = 3.104 mph, releasing within a bucket-width of the
    observed edge. The honest current reading of the low-speed amplitude peak is that THREE effects are
    collinear on every route captured so far and have never been separated:
      (a) the EPS firmware window (0xC62EA) releasing at 3.104 mph;
      (b) openpilot's own engage floor; and
      (c) ordinary plant physics -- assist demand highest and road/tire noise lowest at low speed, so
          the resonance is both most excited and least masked there.
    Route 13's A/B/C split narrowed this a long way (openpilot commanding into the lockout produces
    NOTHING, 1.33x over baseline; commanding AND applying gives 14,750x -- so APPLIED torque, not mere
    transmission, is required) but could not break the speed/applied-torque collinearity, because on
    that route STEER_CONTROL_ACTIVE is a deterministic function of speed: cells B and C have ZERO speed
    overlap and the "engaged at low speed" cell is structurally EMPTY.
    *** V53 (0xC62EA -> 0) is the experiment that fills that cell. It is the ONLY way to observe (c)
    with (a) removed. Until it is driven, do not assert which of the three the peak belongs to. ***
    ---------------------------------------------------------------------------------------------------
    """
    if not (frame.checksum_ok and frame.counter_ok and frame.fresh):
        return None  # invalid frame -> downstream will use the fault sentinel
    return frame.steer_torque  # signed16, big-endian, as decoded from bytes[0:1]


COUNTS_PER_KMH = 64.0625   # FUN_000522fe implements x41>>6 on a 0.01 km/h raw value (NOT a clean 64)


def steer_status_low_speed_lockout(sensors: "SensorInputs", cal: Calibration) -> bool:
    """True when the speed window FAILS, i.e. the firmware writes STEER_STATUS = 3 (LOW_SPEED_LOCKOUT).

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_00028ea6 (m_steer_torque_arbitration), the LIVE ~1 kHz arbitration.
                     Sole caller FUN_0002214a @0x22522. FUN_0002a30e is the DEAD copy -- do not trace it.
      Cals         : 0xC62EA (LO, tp+0x72ea) @0x28EBC ; 0xC62E8 (HI, tp+0x72e8) @0x28EB6.
                     Exactly ONE reader each, image-wide, both V850E2 encodings swept.
      Input        : gp-0x6a5e = VOTED vehicle speed (FUN_00041eec 5-channel voter), ld.hu = UNSIGNED.
      Compares     : 0x290C8 cmp r2,r10 / setfnh  -> speed <= HI
                     0x290D2 cmp lp,r10 / setfnc  -> speed >= LO
      Bypass       : 0x290EA ld.bu -0x68b3[gp] -- nonzero ignores the window entirely. Written in
                     FUN_0004d0d0 ONLY when gp-0x6a62 == 0, i.e. EXACTLY at true standstill.
      Consequence  : failing the window is the ONLY writer of STEER_STATUS=3 (0x29192/0x29194), and
                     0x2937E/0x29382 `cmp 0x2` gates BOTH the STEER_CONTROL_ACTIVE=1 write (0x293A6)
                     and the authority ramp (0x293AC). So this is authority-bearing, not report-only.
    CONFIDENCE     : [VERIFIED] cals, reader sites, compares, and the intra-function consumer.
                     [CONFIRMED] on-car: ST=3 is 100% below 2 mph and 0% above 4 mph, 98,053 frames.

    ⚠ This models the SPEED CONJUNCT ONLY. bVar2 is a 5-way AND -- the other conjuncts (voter-channel
    validity, gp-0x67f4==1, gp-0x67fe==2, gp-0x69aa==0x8000 "no derate", gp-0x69ae within +/-0x4000)
    are not replayed here, so a False from this function means "the speed window passed", NOT
    "STEER_STATUS will be <= 2". In particular gp-0x69aa == 0x8000 shares the same ST=3 write, so an
    on-car ST=3 cannot distinguish "speed window failed" from "a derate is active".
    ---------------------------------------------------------------------------------------------------
    """
    counts = int(sensors.vehicle_speed * COUNTS_PER_KMH)
    if counts == 0:
        # gp-0x68b3 bypass: FUN_0004d0d0 sets it only when the voted speed cell is EXACTLY 0.
        return False
    return not (cal.speed_window_lo <= counts <= cal.speed_window_hi)


def lkas_process_steer_cmd(steer_torque: Optional[int], st: EpsState, cal: Calibration) -> int:
    """
    Convert the raw CAN STEER_TORQUE into the internal LKAS setpoint.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_00052676  (s_lkas_process_steer_cmd)
      Scheduled by : RTOS steering task chain (base tick ~1 ms; see control_task).
      Writes       : setpoint -> gp-0x69ae (0xFEDF1652)
      Instruction  : sxh ; shl 2 ; subr r0  ==  x * -4 ; then clamp(-0x4000, +0x4000)
      Fault path   : checksum/counter/timeout -> write sentinel 0x7FFF (500-tick validity timeout)
    CONFIDENCE     : [VERIFIED] the *-4 scale + +/-0x4000 clamp are instruction-verified.

    NOTE the polarity: STEER_TORQUE is multiplied by -4. The sign flips openpilot's convention to the
    EPS motor convention; the x4 is a fixed-point up-shift (Q2). Full-scale input (4096) lands exactly
    on the -0x4000 wall.
    ---------------------------------------------------------------------------------------------------
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
    Turn the redundant torque-sensor coil ADC channels into the voted column-torque signals, and
    derive the angular-RATE magnitude the decider/debounce gates compare against.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Sensor origin: 3 torque channels from hardware Timer Array Unit TAUA0 capture regs (0xFFFFC400):
                     FUN_00061ca0 (captures) -> FUN_0006195e (lookup + float scale from an option-reg
                     trim) -> raw gp-0x4e8c/8a/88 (0xFEDF3174/76/78) + refs gp-0x4e94/92/90 (../316C/6E/70)
      Plausibility : FUN_00062948  compares the 3 raw vs 3 ref channels; bounds tp+0x59ca/0x59ce, delta
                     tp+0x59c6; each guarded by a `!=0xFFFF` sentinel; sets fault bits 0x20/0x40/0x80.
      Voter        : FUN_00041eec  -> MAX gp-0x6a62 (0xFEDF159E) [2 writers], AVG gp-0x6a5e (0xFEDF15A2)
      Rate path    : FUN_0003f776  -> gp-0x6a60 (0xFEDF15A0) = |clamp(angle-rate gp-0x6a56, +/-12000)|
      Scheduled by : RTOS torque-demand task (FUN_0006651e); sibling to the steering task. [INFERRED]
      Sentinel     : gp-0x6a62 = 0xFFFF on quorum loss; consumed live by the decider (xori 0xffff; be).
    CONFIDENCE     : [CONFIRMED] the 3-channel torque readings are the physical wheel-torque source.
                     [VERIFIED] 3-channel plausibility + voter/rate producers + rate!=torque + sentinel
                     consumer. [INFERRED] only the exact 0xFFFF *producer* store under total quorum loss.

    KEY FACT (load-bearing for the decider): gp-0x6a60 is a RATE (angular velocity) magnitude, NOT a
    torque. The rising edge of gp-0x6a62 is UNFILTERED (only a fall-limiter), so a value reaches the
    gates the same cycle it happens -- there is no debounce in the *rising* voter chain.
    ---------------------------------------------------------------------------------------------------
    """
    coils = sensors.column_torque_coils
    valid = sum(1 for c in coils if c is not None)
    if valid < 3:  # cal 0xC6501 = 3-of-4 quorum
        st.col_torque_max = 0xFFFF  # invalid-sensor sentinel (a distinct decider path, kept in V37)
        st.col_torque_avg = 0xFFFF
    else:
        st.col_torque_max = max(abs(c) for c in coils)
        st.col_torque_avg = sum(abs(c) for c in coils) // valid
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
# SECTION 3B -- BASE DRIVER ASSIST (normal power steering)  [rewritten 2026-07-18 from disasm]
# -----------------------------------------------------------------------------------------------------
# This section replaces the previous abstract `driver_assist_demand` stub, which was wrong in three
# structural ways: (1) it named FUN_0006651e/FUN_0006634e as the producer -- the real producer is
# FUN_00034a72; (2) it modelled a thermal-gain polynomial that is not on this path; and (3) it had
# assist merging at the LKAS mixer -- assist actually joins ONE STAGE LATER, at the motor-torque
# DEMAND AGGREGATOR (FUN_0003aa2c), together with ~8 sibling lanes. See Section 6B.
#
# Assist is not one term. The aggregator receives the boost producer, five named sibling producers,
# TWO inline Sensor-B torque-rate lanes, and one filtered Sensor-B term from FUN_00036682:
#     FUN_00034a72 -> gp-0x6bbe   the boost curve proper (the "assist" everyone means)
#     FUN_00034350 -> gp-0x6bd0   5 multiplied gain factors, sign forced opposite gp-0x6abe [damping]
#     FUN_00036c12 -> gp-0x6b26   curve x gp-0x6c2e angle term                   [friction comp]
#     FUN_0003a382 -> gp-0x6ad4   UNFILTERED residual lane (2 passthroughs + a raw derivative)
#                                 *** NOT "cascaded IIR", NOT damped -- corrected 2026-07-21 ***
#     FUN_00036388 -> gp-0x6b62   slow +/-1/tick accumulator w/ hysteresis       [return-to-centre]
#     FUN_000352b4 -> gp-0x6b86 + gp-0x69a4                                      [friction magnitude]
#     inline r24   <- gp-0x4f62 x generated Q10 gain                              [VERIFIED torque-rate]
#     inline r26   <- gp-0x4f62 x avg(gp-0x69a4) x generated Q10 gain             [VERIFIED torque-rate]
#     FUN_00036682 -> filtered Sensor-B term, final slow IIR (6/1024)              [role OPEN]
# The bracketed roles are [INFERRED] from structure (gating, signs, which signals combine) -- none of
# these functions carries a confirming string or symbol. The addresses/plumbing are [VERIFIED].
# -----------------------------------------------------------------------------------------------------

# [VERIFIED 2026-07-18, byte-dumped from stock code.bin] mode-indexed assist tables.
# Selector = the BYTE at gp+0x63fd (POSITIVE gp displacement; absolute 0xFEDFE3FD), range 0..33.
# NOTE this is a DIFFERENT selector from the LKAS setpoint-limit mode gp-0x674e (static per part
# number = 1 for A160). gp+0x63fd is read at 0x34abc and is written by a factory/diagnostic command
# dispatcher FUN_0004a798 ("Bitte mit PasCom flashen"). [OPEN] whether any runtime/CAN writer exists
# -- that is exactly the open "is SPORT mode done in this ECU" question.
# ⚠ The selector range is 0..33, NOT 0..7. An earlier 8-entry read of this array was truncated and
# mis-mapped which curve this car runs. Our A160 = ECU-ID slot 2 -> gp+0x63fd = 10 -> curve @0xD2834.
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

# *** SPORT MODE: NOT implemented by this ECU. [CONFIRMED 2026-07-18] ***
# All 3 writers of gp+0x63fd were traced to instruction level and NONE reads a CAN RX buffer:
#   FUN_00042692 @0x426ae -- boot-latched from column tp+0xE012 of the SAME per-part-number table at
#                            0xCD000 (stride 0x24) that produces gp-0x674c/d/e. Gated on a one-time
#                            init flag (gp-0x6d78 & 8). Static per part number.
#   FUN_00042746 @0x4279e/0x427c4/0x427fc/0x42822 -- runtime re-derive, but gated on internal
#                            sensor-fault/timeout state (angle sentinel gp-0x69ba, countdown
#                            gp-0x3e54/gp-0x138c vs tp+0x724e, gp-0x4f68 angular velocity vs
#                            tp+0x7180/0x7182). Picks among columns e012/e013/e014/e015 of the SAME
#                            row via a 2-bit state (gp-0x67e2/gp-0x67f6) -- a FAILOVER reselector.
#   FUN_0004a798 @0x4a7fc -- UDS/PasCom bench-diagnostic command 1, writes from the UDS payload.
# The EPS decodes 21 standard CAN IDs (0x94,0xE4,0x130,0x13C,0x158,0x17C,0x198,0x1A4,0x1B0,0x1D0,
# 0x1DC,0x1EA,0x305,0x324,0x326,0x328,0x374,0x3A1,0x6FA,0x72A,0x752,0x78E) -- none reaches this byte.
#
# ID-TABLE LAYOUT (both fields verified by two independent dumps): each 0x24-byte record holds its
# 5-byte ASCII key at offset +0x00 (NOT +0x22 -- an early misread), and the selector columns at
# +0x12/+0x16/+0x17/+0x19/+0x1A. The 16 keys are: "00000"(blank default), TVAA0, TVAA1, TVAC1, TVAA2,
# TVAA4, TVAA6, TVAC4, TVAA7, TVCA0, TVCA3, TVCA4, TVCA6, TWAA0, TWAA1, TWAA2. Our A160 = slot 2
# "TVAA1" -> gp-0x674e = 1 (setpoint record 0xE41A8) and gp+0x63fd = 10 (assist curve 0xD2834).
#
# ⚠ PROVENANCE CAVEAT: FUN_00057f8e matches this ECU's OWN 5-byte HW-ID at gp-0x6408..640C against
# those keys. That HW-ID is NOT in code.bin -- per reference_accord_tva_hw_id_provenance it is written
# at manufacture via a Honda-proprietary UDS service-0x84. So "our car matches slot 2" rests on the
# part number resembling the key string, and can only be CLOSED by a live UDS read of gp-0x6408..640C.
# Robustness: it does not matter much. Every real TVAA* slot (1-8) yields a setpoint record that is
# byte-identical flat-15360, and an assist curve in the FALLING family (e012 in {4,10,12}). Only the
# blank "00000" no-match fallback (slot 0) selects the RISING assist family -- worth knowing, because
# an ECU whose HW-ID was never programmed would run noticeably HEAVIER-assist-at-top-end than stock.
#
# The DECISIVE evidence is the table data itself: our part number's four selectable columns are
# (e012,e013,e014,e015) = (10,10,11,11), and curves 10 and 11 differ by ~1% (541/639/653/551/439/439
# vs 547/645/659/557/445/445). A real Sport mode would need to swing between the FALLING family
# (top-end 439) and the RISING family (top-end 1238) -- a ~2.8x change. This ECU's variant row simply
# does not offer that pair. Whatever tightens the wheel in Sport is not this firmware.
# Safety-ceiling curve, pointer array @0xC7970, keyed on the MAX voter. In THIS image every mode is a
# FLAT 512 -- it is a constant ceiling, not a shaped curve. Default fallback tp+0x715a (0xC615A) = 512
# is used when the key is >= 0x7d01 (saturated / the 0xFFFF invalid-sensor sentinel). [VERIFIED]
ASSIST_CEILING_X = (0, 640, 2560, 5760, 6400)
ASSIST_CEILING_Y = (512, 512, 512, 512, 512)
ASSIST_CEILING_DEFAULT = 512                   # tp+0x715a
ASSIST_SENTINEL = 0x7d01                       # >= this => invalid/saturated sensor path
ASSIST_RATE_STEP = 0x3638                      # 13880/tick, FUN_0004613e rate limiter at fn entry


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

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_00034a72  (0x34a72 - 0x35150)
      Scheduled by : w_steer_control_task FUN_0002214a -- the SAME task as arbitration.
                     [OPEN] whether this call site carries an `andi` phase mask like the arbitration
                     call @0x22522 does. Not checked; do NOT assume it runs every base tick.
      Mode select  : ld.bu 0x63fd[gp] @0x34abc -> 0..33, indexes every table below
      Primary key  : gp-0x6a5e = the AVG voter output  (shapes the curve)      [VERIFIED]
      Ceiling key  : gp-0x6a62 = the MAX voter output  (bounds the result)     [VERIFIED]
                     *** 2026-07-25 -- WHAT the voter votes ON is now in dispute. Two independent
                     firmware traces this session conclude gp-0x6a5e / gp-0x6a62 / gp-0x6a64 are all
                     outputs of FUN_00041eec, a 5-CHANNEL REDUNDANT VEHICLE-SPEED voter (4 wheel
                     speeds from CAN 0x1D0 + a transmission reference channel gp-0x6a46 written in
                     FUN_000522fe from CAN 0x158 XMISSION_SPEED2, scale x41>>6 ~ 64.06 counts/km/h),
                     i.e. VOTED VEHICLE SPEED -- not voted driver/column torque as labelled here and
                     elsewhere in this file.
                     Supporting (lead-verified bytes): gp-0x6a5e is read ld.hu (UNSIGNED); the
                     low-speed lockout window cals 0xC62EA=320 and 0xC62E8=12800 divide by ~64 to
                     exactly 5 and 200 km/h; the V44/V47 "Factor C" axis [2240,3840,5120,8960]
                     divides to [35,60,80,140] km/h exactly.
                     *** NOT ADOPTED INTO THE MODEL YET -- this would reclassify the boost curve's
                     keys and the V44/V47 damper mechanism, and it must get its own verification pass
                     first. If it holds, "Factor C is zero HANDS-OFF" becomes "zero BELOW 35 km/h".
                     See docs/HANDOFF-2026-07-24-low-speed-steer-lockout.md Sec.9 item 10. ***
      Tables       : boost @0xCA154 | ceiling @0xC7970 | gain-scalar @0xCA324 (points at a bare short,
                     mode0=0xCE008, mode1=0xCE00A) | rate-keyed LERP @0xCA4F4 | per-mode scalar clamp
                     @0xC7A58 | gp-0x69ba-keyed LERP @0xCA23C.
                     [OPEN] contents of 0xCA324 / 0xCA4F4 / 0xC7A58 / 0xCA23C not yet dumped.
      Polarity     : gp-0x6752 (the same assist-polarity global the corridor/monitor paths use)
      Rate limit   : FUN_0004613e(0x3638, ...) over the internal cluster gp-0x6bb2/4/6/8 at entry;
                     its output feeds the 0xCA4F4 curve key.
      Ramp SM      : byte gp-0x682e in {0,1,2,3}, timer gp-0x68c8 vs (tp+0x74d1 * 10). This is the
                     ASSIST's own engage ramp -- entirely separate from the LKAS engage SM.
      Writes       : gp-0x6bbe (0xFEDF1442), lockstep-shadowed at gp-0x4cf0 (mismatch -> FUN_0006b9fa)
    CONFIDENCE     : [VERIFIED] producer, both voter inputs, mode selector + its diagnostic writer,
                     the boost + ceiling table contents (byte-dumped 2026-07-18), the store + lockstep.
                     [OPEN] the four undumped scaling tables; the phase-gating question.
    ---------------------------------------------------------------------------------------------------
    """
    mode = st.assist_mode                             # gp+0x63fd, range 0..33 (NOT 0..7)

    # --- validity gate ("bVar10"): ALL of these must hold or the lane collapses to the ramp-down path
    valid = (st.assist_substate in (1, 2)             # gp-0x67fe  EPS assist substate
             and st.plausibility_ok                    # gp-0x67f4 == 1, from the voter FUN_00041eec
             and st.col_torque_avg < ASSIST_SENTINEL   # gp-0x6a5e not invalid/saturated
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
    key_avg = min(abs(st.col_torque_avg), 0xFFFF)
    xs, ys = ASSIST_BOOST_CURVE.get(mode, ASSIST_BOOST_CURVE[10])   # default = this car's curve
    raw = _lerp_flat(key_avg, xs, ys)

    # --- rate limiter on the internal cluster, feeding the secondary rate-keyed curve --------------
    delta = raw - st.assist_rate_state
    if delta > ASSIST_RATE_STEP:
        delta = ASSIST_RATE_STEP
    elif delta < -ASSIST_RATE_STEP:
        delta = -ASSIST_RATE_STEP
    st.assist_rate_state += delta

    # --- safety ceiling, keyed on the MAX voter (flat 512 in this image) ---------------------------
    key_max = abs(st.col_torque_max)
    ceiling = (ASSIST_CEILING_DEFAULT if key_max >= ASSIST_SENTINEL
               else _lerp_flat(key_max, ASSIST_CEILING_X, ASSIST_CEILING_Y))

    # --- gain modulation, polarity, and the final clamp against the ceiling ------------------------
    # [SIMPLIFIED -- flagged] the four undumped tables (0xCA324 gain scalar, 0xCA4F4 rate curve,
    # 0xC7A58 clamp, 0xCA23C) fold in here as additional multiplicative factors. Modelled as unity
    # until their contents are dumped; this is the one place this function is NOT literal.
    signed = int(st.assist_rate_state * ramp_scale) * st.assist_polarity   # gp-0x6752
    return _clamp(signed, -ceiling, ceiling)                               # -> gp-0x6bbe


ASSIST_RATE_CROSS_X = (0, 640, 3200, 6400)  # gp-0x6a5e AVG-voted torque magnitude

# FUN_0003ad74 cross-interpolates each X/Y element across the four AVG-torque records, producing the
# runtime arrays consumed by FUN_0003aa2c. Y is Q10 (1024 == 1.0); every value is byte-verified.
ASSIST_RATE_B_RECORDS = (
    ((0, 400, 1400, 3000), (3072, 3072, 2322, 1536)),
    ((0, 400, 1500, 3000), (2561, 2561, 2247, 1947)),
    ((0, 400, 1500, 3000), (2305, 2304, 2149, 1948)),
    ((0, 400, 1500, 3000), (2151, 2151, 2049, 1947)),
)
ASSIST_RATE_A_RECORDS = (
    ((0, 400, 1600, 3000), (3072, 3072, 2434, 2048)),
    ((0, 250, 1200, 3000), (3072, 3072, 2488, 1536)),
    ((0, 400, 1250, 3000), (2664, 2664, 2243, 1436)),
    ((0, 400, 1250, 3000), (2560, 2560, 2145, 1331)),
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
    avg_key = abs(st.col_torque_avg) if st.plausibility_ok else 5120
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


def _inline_torque_rate_a(st: EpsState) -> int:
    """
    FUN_0003aa2c r26 -- the ADAPTIVE Sensor-B torque-rate lane. Returns zero until the gp-0x69a4
    producer is replay-supplied.

    ---------------------------------------------------------------------------------------------------
    *** FULLY TRACED 2026-07-20. THE r24-vs-r26 SIGN QUESTION IS SETTLED. [VERIFIED] ***

      r26 = clamp( polarity * ((dtorque * avg(gp-0x69a4)) >> 10 * gain_A) >> 10 , +/-0x2000 )
      dtorque = clamp(gp-0x4f62, +/-5120)   -- shared register r1, IDENTICAL for both lanes

    *** r24 AND r26 CARRY THE SAME SIGN, ALWAYS. There is no cancellation between them. ***
    Two independent proofs:
      (1) gp-0x69a4 is an UNSIGNED MAGNITUDE at both ends. Consumer uses `ld.hu` @0x3ab3a and
          @0x3ab4a plus an unsigned `shr 0x1` @0x3ab54 for the average. Producer FUN_000352b4
          @0x355a4-c6 stores only via `cmovnc r0,r8,r10` where r8 comes from `ld.hu`/`sld.hu` table
          loads, forced to 0 outside the +/-25600 gp-0x4f60 plausibility window. Never negative.
          Since avg >= 0 and gain_A >= 0 (all-positive Y rows), r26 inherits dtorque's sign exactly.
      (2) There is exactly ONE `ld.b -0x6752[gp]` in the entire function (@0x3ab78). Both lanes
          consume that same polarity register unmodified -- r26 @0x3ab7e, r24 @0x3ac3e.
    CONSEQUENCE: V39 removed roughly HALF of a same-signed pair, not a counterweight. That is
    consistent with V39 changing nothing on the road, and it means the derivative SIGNAL was never
    actually tested -- only one of its two carriers.

    *** THE NEAR-ZERO ASYMMETRY -- this is the load-bearing structural difference. [VERIFIED] ***
      r24 applies a +/-3 DEADZONE (cal 0xC61F6) before its polarity multiply.
      r26 has NO deadzone -- it goes straight from the double-shift product to the clip.
    So in the small-|dtorque| regime, r24 is SUPPRESSED BY CONSTRUCTION and r26 is the only live
    derivative lane. *** V39 zeroed the lane that was already deadzone-suppressed exactly where the
    ~5 mph small-command vibration lives. *** That alone predicts V39 would be a no-op for that
    symptom, independently of the invariance argument.

    OTHER r26-ONLY STRUCTURE r24 LACKS:
      - a PERSISTED 2-sample rolling average (previous sample gp-0x3672, valid flag gp-0x3670)
      - a HARD ZERO-FORCE GATE @0x3ab2a-34: when gp-0x6b5e != 0 AND assist_state_671a < cal 0xC64FA,
        the entire pre-polarity term is forced to 0 for that cycle. r24's analogous gates only SWITCH
        which gain cal is used; they never zero it. This is a genuine single-cycle discontinuity
        unique to r26 and it was never examined by V39.

    GAIN_A: a 4-point flat-extrapolated LERP over the motor-rate axis gp-0x6ac0 (zeroed at >= 13001),
    against a table FUN_0003ad74 rebuilds every cycle by cross-interpolating 4 ROM records on the
    AVG-torque axis. Records byte-read from ROM, exact stride 0x14, and they match
    ASSIST_RATE_A_RECORDS below exactly:
      0xC6A68: X=(0,400,1600,3000) Y=(3072,3072,2434,2048)
      0xC6A7C: X=(0,250,1200,3000) Y=(3072,3072,2488,1536)
      0xC6A90: X=(0,400,1250,3000) Y=(2664,2664,2243,1436)
      0xC6AA4: X=(0,400,1250,3000) Y=(2560,2560,2145,1331)
    r24 uses the SAME LERP mechanics but a structurally DISJOINT mode-indexed bank
    (gp-0x6e40/gp-0x6e38 via pointer arrays 0xcbf5c/0xcc044/0xcc12c + tp+0xd214).

    CAL-ONLY KILL SURFACE (18 halfwords, all r26-exclusive, all single-reader verified by a
    185,693-instruction operand sweep; all inside the 0xC6000 block this kit has patched safely
    since V29; no float mirror -- the function contains zero mulf.s/cvtf):
      16 Y values: 0xC6A72/74/76/78, 0xC6A86/88/8A/8C, 0xC6A9A/9C/9E/A0, 0xC6AAE/B0/B2/B4
      2 overrides: 0xC6444 (tp+0x7444) and 0xC643E (tp+0x743e)
    Zeroing all 18 forces gain_A = 0 in every reachable state => r26 == 0 unconditionally, without
    touching gp-0x69a4's producer (shared with the still-live gp-0x6b86 lane).

    [OPEN] r26's realistic magnitude. It reaches the +/-8192 clip only if avg(gp-0x69a4) > ~546
           (8192 = 5120 * avg * 3072 / 2^20). Whether that happens was NOT resolved.
    [OPEN] the MECHANICAL loop sign -- whether a positive motor command actually produces a positive
           dTorque/dt back at the sensor. That decides positive-feedback vs benign feedforward and
           CANNOT be settled by disassembly; it needs live telemetry.
    [OPEN] gp-0x6752's concrete A160 runtime value (3 writers, all static config-record parsers
           selecting 1 vs 0xff). Does not affect the relative-sign proof above.
    ---------------------------------------------------------------------------------------------------
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
    The five sibling assist-shaping lanes. Each is its OWN function writing its OWN aggregator lane --
    they are NOT applied in series to the boost curve. All five read gp-0x6a5e (AVG torque) directly.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP  (all producers + lane variables [VERIFIED]; the ROLE labels are [INFERRED])
      FUN_00034350 -> gp-0x6bd0 : product of FIVE mode-indexed LERP gain factors -- @0xC9CCC (AVG
                      torque, plausibility-gated), @0xC9E9C (AVG torque), @0xC9DB4 (gp-0x6a10, gated
                      gp-0x67fe in {1,2} and gp-0x6a10<10000), @0xC9F84 (gp-0x6ac0 = the MOTOR
                      ELECTRICAL RATE axis the governor re-trace pinned), @0xC77A0 (gp-0x6ac2, a
                      second rate-like axis). Final sign FORCED OPPOSITE to sign(gp-0x6abe)
                      -- a velocity-opposing signature. [INFERRED] viscous damping.
                      The sign flip `if (0 < *(short*)(gp-0x6abe)) term = -term` is real and
                      hysteresis-free (verified @0x3469e).
                      *** CORRECTED 2026-07-20 -- THE PINNING WAS BACKWARDS, AND THIS LANE IS NOT RULED
                      OUT. It is the V44 mechanism. *** gp-0x6abe is produced by FUN_00041464 (sole
                      caller w_steer_control_task @0x22200, once per cycle, state-gated not phase-gated
                      -- CONFIRMED ~1000 Hz, same task the STEER_STATUS=4 dwell measured):
                        @0x415b0-0x415ce a bias-compare `addi 0x32c8,r15,r11 ; addi -0x6591,r11,r0`
                        tests |gp-0x4f50| > 13000 (SYMMETRIC -- settled from Ghidra pcode
                        `INT_LESS(26000, r15+13000)`, the standard unsigned(x+K)<=2K magnitude idiom;
                        an earlier "one-sided" read was retracted). Call that bVar2.
                        bVar2 TRUE (|rate| > 13000): gp-0x6abe PINNED to LITERAL 0x7fff.
                        bVar2 FALSE (normal driving): gp-0x6abe carries the LIVE signed filtered rate.
                      ★ THE PIN IS STRUCTURALLY UNREACHABLE: gp-0x4f50's producer FUN_00068f52 clamps
                      it to EXACTLY +/-13000 (14-bit wraparound fold bounds the raw delta to +/-8192,
                      scaled *120000/16384 to +/-60000 pre-clamp, then hard-clamped +/-13000), so
                      |gp-0x4f50| > 13000 CANNOT hold. gp-0x6abe is therefore ALWAYS the live value in
                      normal driving; the consumer's own |gp-0x6abe|>13000 self-zero @0x34608 likewise
                      never fires. The prior "PINNED POSITIVE in normal driving, so the flip is a no-op,
                      so this lane is ruled out" reasoning inverted the branch and is fully RETRACTED.
                      *** ALSO RETRACTED: the "half-wave rectified damper" claim (V43 handoff) that
                      `ld.hu -0x6ac0[gp]` @0x345fa dead-bands one rotation direction. gp-0x6ac0's own
                      producer applies abs() BEFORE the store, so ld.hu vs ld.h is a no-op on an
                      already-non-negative value. (The real half-cycle effect is on sibling gp-0x6ac2,
                      the clamp BOUND, not the gate.)
                      Cal context: tp+0x748e (0xC648E) offset = 0, tp+0x7134 (0xC6134) gain = 1000
                      (so the *1000/1000 formula is an identity), and the per-channel selector bytes
                      0xC40EB-0xC40EE are all 0 while the gate needs 0xE9 -- dormant on all 4
                      channels, and moot since formula and fallback agree numerically in this ROM.

                      *** FACTOR-BY-FACTOR BREAKDOWN, 2026-07-21 -- WHY V44's Y[0]-ONLY FIX WAS
                      INCOMPLETE. Multiple independent GhidraMCP traces this session pinned the FIVE
                      factors by name and table contents (labels A-E for cross-reference only): ***
                        A (seed)   gp-0x698a, a MIN-clamped seed, USUALLY UNITY (1024) -- inert.
                        B (table)  gp-0x6bcc, a driver-torque table that is FLAT 1024 in this ROM --
                                   inert.
                        C (table)  gp-0x6a5e (VOTED DRIVER COLUMN TORQUE) through a LERP -- mode 10 at
                                   0xD27BC, mode 11 at 0xD27D0. X = [2240, 3840, 5120, 8960],
                                   Y = [0, 235, 430, 877]. *** Y[0] = 0 -- HANDS-OFF DEADZONE #1: below
                                   2240 counts of driver torque this factor alone zeroes the product. ***
                        D (table)  gp-0x6a10 (the angle-deviation term modelled above), a LERP that is
                                   FLAT 1024 in this ROM -- inert.
                        E (table)  |gp-0x6ac0| (MOTOR/RESOLVER ELECTRICAL-ANGLE RATE, magnitude) through
                                   a LERP -- mode 10 at 0xD27F8, mode 11 at 0xD280C. X = [60, 400, 2500,
                                   4000], Y = [0, 140, 539, 927]. *** Y[0] = 0 -- HANDS-OFF DEADZONE #2:
                                   below 60 counts of motor rate this factor alone zeroes the product,
                                   INDEPENDENTLY of C. ***
                      *** CONSEQUENCE: TWO INDEPENDENT ZEROES, NOT ONE. *** V44 raised only Factor C's
                      Y[0] (0xD27C6/0xD27DA, 0->235/234). That reopens the damper once driver torque
                      exceeds 2240 counts, but Factor E still zeroes it below 60 counts of motor rate --
                      i.e. whenever the resonance itself is small/just-starting, which is exactly the
                      regime a damper needs to catch it early. This is the leading explanation for why
                      V44's mitigation (as carried into V45/V46, see the module docstring build lineage)
                      did not resolve the symptom on-car, and why V47 raises BOTH factors' floors.
                      *** OUTPUT CLAMP IS DYNAMIC, NOT A FLAT +/-2048. *** Downstream of the product,
                      FUN_00034350's own clamp bound on gp-0x6bd0 is keyed on gp-0x6ac2 through a LERP
                      at 0xD209C/0xD20A8, X = [300, 800], Y = [512, 1024] counts, fallback cal
                      0xC6158 = 512 when the table is out of range. *** This is a SEPARATE, narrower
                      clamp than the aggregator's own +/-0x800 (2048) zero-type gate on the same lane
                      (see motor_torque_demand_aggregator()'s FIRMWARE MAP) -- the aggregator gate is a
                      contribute-or-zero window on the WHOLE lane; this LERP is the producer's own
                      output ceiling, and it never reaches the aggregator's 2048 bound in this ROM. ***
                      *** SAFETY TRAP FOR ANY FUTURE EDIT TO THIS CLAMP (DTC-0x1d, hard shutdown, no
                      debounce): FUN_000347b8 independently RE-DERIVES this same clamp bound in FLOAT
                      from a mirror at cal 0xC6554/58/5C/60 (= 300.0/800.0/0.5/1.0, i.e. the float twin
                      of the 0xD209C/0xD20A8 int table above) and compares it against the int result;
                      if they diverge by more than 5/1024 it calls FUN_000462e6 -> FUN_00016de6(0x1d) --
                      a NO-DEBOUNCE hard shutdown (see hard_dtc_lockstep_monitor() for this monitor
                      family). RULE, same as every other lockstep pair in this kit: never edit the int
                      clamp table (0xD209C/0xD20A8) without a bit-exact matching edit to the float
                      mirror (0xC6554/58/5C/60). This is exactly the kind of pair a damping-restore
                      build (V47) must get right, and it is why V47's build script must patch both. ***
      FUN_00036c12 -> gp-0x6b26 : LERP @0xCBE74 (AVG torque; gated gp-0x671a vs tp+0x74fd and
                      gp-0x67f4==1) multiplied by gp-0x6c2e, then range-limited. [INFERRED] friction.
      FUN_0003a382 -> gp-0x6ad4 : 3-stage cascaded IIR/rate-limit over gp-0x6ac0 (motor rate),
                      gp-0x4f60 (sensor-B column torque), gp-0x6a5e, gp-0x67fe. [INFERRED] resonance
                      damping.
                      *** 2026-07-21 MAJOR CORRECTION -- THE "VERY HEAVILY DAMPED" VERDICT BELOW IS
                      WRONG AND IS RETRACTED. THIS LANE IS UNFILTERED. ***
                      The two "lag" gains were read as 4. They are 1024. Byte-read this session at
                      cal tp+0x7450 (0xC6450) and cal tp+0x744a (0xC644A) in THREE images -- stock
                      code.bin, _v38_plain_image.bin and _v42_plain_image.bin -- all give **1024**,
                      i.e. Q10 UNITY. Substituting into the lane's own update:
                          state_new = state + ((target - state) * 1024) >> 10  ==  target
                      Both "first-order lags" are therefore DIRECT ASSIGNMENTS -- passthroughs with no
                      filtering whatsoever, not tau ~ 256-cycle lags. The reader's addressing was
                      sanity-checked in the same dump by independently reproducing 0xC6202 = 4762 and
                      0xC6204 = 3072 at their expected offsets, so this is not an address-math error.
                      *** CONSEQUENCE: this lane does not argue against resonating -- it is the most
                      plausible fast path into the aggregator found to date. See
                      vibration_hands_off_analysis(). ***
                      [RETRACTED TEXT, kept for provenance] "Two genuine first-order lags ... both are
                      4/1024 in Q10 => tau ~ 256 cycles per stage: VERY heavily damped, i.e. strongly
                      overdamped rather than resonant."
                      The third stage
                      (gp-0x3688/gp-0x3684) is NOT a lag -- it is a raw sample-to-sample DIFFERENCE
                      ((current - previous) * gain) combined by a branchless min-select, i.e. a
                      derivative term that passes high-frequency content straight through. The five
                      LERP lookups feeding the lane (keyed on gp-0x6ac0 motor rate, gp-0x6a5e,
                      gp-0x6bda, gp-0x6966 = the soft-EME AUTHORITY value, and gp-0x6a98) are also
                      recomputed unsmoothed every cycle. So: the lags are not the risk; the
                      derivative stage and the raw table lookups are. [OPEN] full transfer function
                      (needs the table contents). Note gp-0x6966 makes this lane a FEEDBACK path from
                      the soft-EME integrator back into the torque aggregate.
                      *** ROLE SHARPENED 2026-07-21: this is a REINFORCING carrier, not neutral. ***
                      Stage A's pole (cal 0xC6450 = 1024, exact Q10 unity) makes it an unfiltered
                      passthrough of an error term = gp-0x4f60 (Sensor-B driver torque) minus a model
                      gp-0x6ad6, summed into the aggregator with ASSIST POLARITY -- i.e. it feeds back
                      the raw sensor-vs-model residual as positive/reinforcing content, not damping.
                      *** V46 FLASHED, NO EFFECT -- LEVER A IS FALSIFIED. *** Filtering this exact pole
                      (0xC6450 1024 -> 32, shipped as V46, built on V44/V45) was flashed and driven; the
                      ~21 Hz vibration was UNCHANGED on-car. So suppressing Stage A's reinforcing carrier
                      is neither necessary nor sufficient by itself -- consistent with the mode being a
                      genuine mechanical resonance (see the plant-architecture note in
                      can_rx_stage_steer_torque()) that a single upstream residual-carrier pole cannot
                      starve out on its own. Do not re-propose "just filter Stage A" as a standalone fix.
      FUN_00036388 -> gp-0x6b62 : slow +/-1-per-tick accumulator gp-0x6a82 with a hysteresis window
                      (tp+0x718a); consumes gp-0x6b96 from FUN_000352b4. [INFERRED] return-to-centre.
      FUN_000352b4 -> gp-0x6b86 and gp-0x69a4 : CORRECTION 2026-07-18 -- normal Sensor-B torque in the
                      inclusive +/-25600 plausibility window PASSES; only an out-of-window value forces
                      both outputs to zero (@0x35aa4..0x35ace). The prior model inverted this branch and
                      wrongly called gp-0x6b86 inert. Its adaptive 10-segment magnitude remains OPEN.
      inline r24     : exact direct gp-0x4f62 Sensor-B torque-rate lane; generated positive Q10 gain,
                      +/-3 deadzone, +/-8192 final clamp. This is the strongest static match for a short
                      wheel-inertia counter-assist transient. [VERIFIED arithmetic; physical role INFERRED]
      inline r26     : gp-0x4f62 x avg(gp-0x69a4) x generated Q10 gain, +/-8192. Exact when gp-0x69a4
                      is replay-supplied; otherwise modelled zero rather than inventing its producer.
    ---------------------------------------------------------------------------------------------------
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
    Decide whether LKAS is allowed to deliver this tick, and (if not) why.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Dispatcher   : FUN_000413ae  (state gp-0x67DC)      called via FUN_00022ca0
      Decider      : FUN_00040d58  -> verdict r12 ; disengage hook @0x40e64
      Consensus    : FUN_000406ae  (angle-consensus helper on gp-0x6cc4)
      Scheduled by : sibling RTOS task FUN_00022ca0 (jarl FUN_000413ae @0x22e9c). [VERIFIED task]
      Deliver flag : gp-0x6809 is DEAD CODE (0 writers). Do NOT treat it as the cut. [OPEN cut site]
    CONFIDENCE     : [VERIFIED] the gate arithmetic + verdict codes.
                     [OPEN]     which verdict actually zeroes the motor term is UNLOCATED.

    Verdict codes:  0 = pass (deliver)          2 = torque-MAX gate (dec_torque_max, stock 320)
                    4 = angle-consensus gate     5 = rate gate (dec_rate_gate, 1600)
                    6 = gate6 (4096)             7 = gate7 (3584)
    IMPORTANT (2026-07-14 finding): the torque-MAX gate (verdict 2) fires ~10 Hz BENIGN and is NOT the
    gentle-EME trigger -- V33's raise of dec_torque_max chased the wrong gate. The gates here are real
    refusals of *engagement*, but the felt gentle cut is produced by the debounce SM (Section 5),
    not here.
    ---------------------------------------------------------------------------------------------------
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
# This one function is the crossroads. It (a) limits the LKAS setpoint by a mode/gear LERP curve,
# (b) applies the LKAS gain+clamp in Q15, and -- inlined into the same body, running each time it is
# dispatched (phase-gated) -- hosts TWO counters off the same torque channel:
#     - the STEER_STATUS debounce SM  -> gentle EME   (fixed in V37)
#     - the DTC-0x49 fail counter     -> dash lights  (unmasked by V36, fixed in V37)
# NOTE (2026-07-17 firmware re-verification): driver-assist is NOT summed here. FUN_00028ea6 keeps the
# command a standalone LKAS-descended signal; base-assist merges DOWNSTREAM as a separate mixer source
# (Section 6). The old "setpoint limit + assist merge" framing was refuted at the instruction level.
# =====================================================================================================

def steer_status_debounce_sm(arb_torque_byte: int, rate_mag: int, st: EpsState, cal: Calibration) -> None:
    """
    The GENTLE-EME producer: a 5-cycle debounce that raises STEER_STATUS=4 (NO_TORQUE_ALERT_2).

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Live code    : inlined in m_steer_torque_arbitration, ~0x29120-0x2931e (rise 0x2923e, hold 0x292b8)
      Dead twins   : FUN_0002a30e and FUN_0002a93a are DEAD (0 callers/xrefs/ptrs) -- compiler
                     out-of-line copies that never execute. The LIVE logic is the inline one above.
      Signals      : arb_torque_byte = gp-0x682f = min(|arb signal r15| >> 5, 255)   (@0x29068)
                     rate_mag        = param_1 = clamped angular-rate magnitude (<=65535)
      Counter      : gp-0x6757 signed, seeded at -deb_count_seed(5); fires STEER_STATUS=4 (gp-0x6807)
                     after 5 sustained qualifying cycles; holds deb_hold_seed(100) cycles.
      Scheduled by : inside phase-gated arbitration (4 of 16 phases of w_steer_control_task). So the
                     "5 cycles" are 5 arbitration invocations, ~ tens of ms (base tick ~1 ms, /4).
    CONFIDENCE     : [VERIFIED] byte-verified both branches; all loads UNSIGNED, all compares
                     `cmp; bh` (unsigned "branch if higher" == cal < signal).

    The qualifying envelope (fires if ANY tier is true) -- a staircase approximation of "moderate
    torque AND moderate rate together are dangerous even if neither is extreme alone" (loaded-curve
    + bump). V37 raises all 7 thresholds to unsigned max so no tier can ever be true.

    *** V37 flashed on-car and this cut STOPPED (operator-confirmed 2026-07-14). ***
    ---------------------------------------------------------------------------------------------------
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

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Live code    : inlined in m_steer_torque_arbitration; gate reads @0x2920a/0x2921c; fire @0x291b8
                     -> 0x291ca jarl FUN_00016de6(0x49,1,1,1)  (= set DTC 0x49) + STEER_STATUS=7
      Signal       : arb_torque_byte = gp-0x682f (same byte the debounce SM uses)
      Counter      : gp-0x6758; increments while torque > dtc49_torque_gate(112); saturates at
                     dtc49_saturation(100 = 50+50 cyc, ~1 s @ ~100 Hz) -> DTC 0x49.
      Interlock    : zeroed by every STEER_STATUS=4 branch (see steer_status_debounce_sm).
      Scheduled by : same phase-gated arbitration as the debounce SM. "100 cycles" ~ 0.4-1 s of
                     sustained torque>112 (the "halfway through a drive" V36 dash-lights onset).
    CONFIDENCE     : [VERIFIED] this session (V36 regression root-cause + V37 fix).

    Why V37 exists: V36 raised the debounce thresholds so STEER_STATUS=4 never fires -> the interlock
    `dtc49_counter = 0` never runs -> under sustained torque>112 this counter free-runs to 100 -> DTC
    0x49 + STEER_STATUS=7 -> dashboard lights + openpilot drops LKAS (steerFaultPermanent); base assist
    survives. V37 raises dtc49_torque_gate 112->255 so the counter can never increment.
    ---------------------------------------------------------------------------------------------------
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
    Limit the LKAS setpoint, apply the Q15 gain/clamp, and run the two inlined SMs.
    (Driver assist is NOT merged here -- it is a separate downstream mixer source; see Section 6.)

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_00028ea6 / m_steer_torque_arbitration  (entry ~0x28ea6, body into 0x2a3xx)
      Scheduled by : w_steer_control_task FUN_0002214a, call @0x22522 -- PHASE-GATED (andi 0x930 on a
                     16-phase counter => runs on 4 of 16 phases, NOT every base tick). [VERIFIED gate]
      Reads        : setpoint gp-0x69ae (0xFEDF1652)
      Limit tables : mode/gear-indexed LERP pointer arrays 0xC9A88..0xCBC34 -> curves @0xE4xxx
                     (setpoint symmetrically clamped to +/-LERP(curve[mode]); const ~15360 base)
      Gain/clamp   : gain tp+0x746c(0xC646C)=891; output clamp tp+0x71b4(0xC61B4)=512. Applied as
                     (setpoint-descended term x gain) >> 15  [VERIFIED @0x2a1ee gain-load / @0x2a202
                     `sar 0xf`]. The scale is Q15 (>>15), NOT >>10. (A real >>10 `sar 0xa` exists @0x2a1a0
                     but belongs to an earlier Q10-IIR blend of gp-0x3d3c, a different stage.)
      High-tq arb  : @0x29a78  torque>dtc49_torque_gate(112) ? high-torque cutoff : full curve interp
                     -- NOTE V37's 0xC64B8 112->255 also flips THIS live branch for torque in (112,255],
                     an accepted drivability side effect (runs full interp instead of the cutoff).
      Writes       : arb gated command -> gp-0x6b3c (0xFEDF14C4). Final store @0x2a2ea is
                     (shaped term) x (0/1 mode gate gp-0x67a4 in {2,3}) -- MULTIPLICATIVE, no add.
                     internal torque byte gp-0x682f (@0x29068) feeds both inlined counters.
    CONFIDENCE     : [VERIFIED] gain/clamp cals, the Q15 (>>15) scale, the LERP pointer arrays
                     (0xCB844 -> 0xE4180..), the debounce/DTC counters, AND that NO driver-assist term
                     is added in this function (disasm-confirmed 2026-07-17: the two adds feeding the
                     store are both internal setpoint-descended terms, one gated on the dead gp-0x6809).
    ---------------------------------------------------------------------------------------------------
    """
    # 1) mode/gear LERP limit on the LKAS setpoint. [VERIFIED @0x28fc8-0x29044] index=gp-0x674e into
    #    pointer array 0xCB844 -> curve @0xE4180; mode-0 value row is CONSTANT 15360, so the full-scale
    #    setpoint (0x4000=16384) IS clipped ~6% at the top end. (Only mode 0 byte-dumped; other modes
    #    open.) Modelled as the flat mode-0 limit.
    limited = _clamp(st.lkas_setpoint, -cal.arb_setpoint_limit, cal.arb_setpoint_limit)

    # 2) apply the LKAS output gain in Q15 (>>15), then a symmetric +/-arb_output_clamp. [VERIFIED]
    #    The real path first shapes `limited` through a mode/axis curve+IIR chain; the binding final
    #    scale is (setpoint-descended term * gain) >> 15. At full scale V850 `sar` yields +417/-418,
    #    both below 512, so stock never hits the clamp (this is why the old >>10 -- ~13370, 26x over
    #    the 512 clamp -- was
    #    self-evidently wrong; the operator caught it).
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

    *** CORRECTED 2026-07-18: base driver assist does NOT join here. ***
    The previous version of this function summed `assist` into the lane at this stage. That was wrong.
    FUN_00026c80 (mixer) + FUN_00025c32 (distribute) only sum ~11 LKAS-INTERNAL channels (the tp+0x5124
    mode array) into gp-0x6b4c -- this whole stage is still an LKAS-only lane. Base assist joins ONE
    STAGE LATER, at the motor-torque demand aggregator FUN_0003aa2c (see Section 6B below), where
    gp-0x6b4c is summed with gp-0x6bbe and ~8 sibling lanes into gp-0x6b94.
    So "distribute source index 1" (the old note) and "the ~10 aggregator lanes" are TWO SEPARATE
    summing stages that were previously conflated into one.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP  (all clamp literals CONFIRMED live this session)
      limit_and_pack : FUN_0002b422  reads gp-0x6b3c, clamp +/-tp+0x71b2 (0xC61B2), writes gp-0x6b3a
      distribute     : FUN_00025c32  per-lane clamps  +/-0x4000 / +/-0x2800 / +/-0x384 / +/-0x4E20
                       (code literals @0x25c80/9c/b8/d4). LKAS rides the +/-0x2800 lane.
      mixer          : FUN_00026c80  cross-lane MAX/SUM into accumulators gp-0x3d70..3d98;
                       LKAS lane final clamp +/-0x2800 (@0x276de..0x27704) -> gp-0x6b4c
      gate           : FUN_00042ac6  |x| <= 0x2800 ? x : 0x7FFF-sentinel -> gp-0x6afe (0xFEDF1502)
      Assist merge   : the mixer SUMS ~10 distribute sources into the LKAS-lane accumulator; the LKAS
                       arb output is source index 1 (tagged @0x2b522 mov 0x1). Base driver-assist is a
                       SEPARATE source that joins HERE, not in arbitration.
      Scheduled by   : RTOS steering task chain, downstream of arbitration (base tick ~1 ms).
    CONFIDENCE       : [VERIFIED] the clamp topology + gate idiom, LKAS distribute source idx 1, and
                       that this stage remains LKAS-internal. The separate FUN_0003aa2c lane sum is
                       reproduced explicitly in Section 6B.

    The gate's 0x7FFF sentinel (for anything outside +/-0x2800) is deliberately out-of-range so the
    shaper's own range-check collapses it to 0 (see soft_eme_windup_shaper).
    ---------------------------------------------------------------------------------------------------
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

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_0003aa2c  (m_motor_torque_demand_aggregator, 0x3aa2c - 0x3ad70)
      Lanes read   : gp-0x6b62, gp-0x6b4c (LKAS, +/-0x2800), gp-0x6ade (DEAD -- read @0x3aa48, ZERO
                      writers found image-wide), gp-0x6ad4, gp-0x6b26, gp-0x6bbe (boost assist),
                      gp-0x6bd0, gp-0x6b86, inline torque-rate r26/r24, and FUN_00036682's filtered term.
      Per-lane gate: each lane is range-gated by the `addi <window>, rN, rM ; addi -<limit>, rM, r0 ;
                     cmovc 0x0, rN, rX` idiom -- out-of-window lanes contribute 0 rather than clipping.
                     *** ALL EIGHT gates re-verified individually 2026-07-19 as ZERO-type, and every
                     window below matches this model exactly: ***
                       6b62 return-centre +/-0x2000  @0x3aa38 load / 0x3aa50-58 gate
                       6b4c LKAS          +/-0x2800  @0x3aa3e / 0x3aa5c-64
                       6ade (dead)        +/-0x400   @0x3aa48 / 0x3aa68-74
                       6b86 magnitude     +/-0x3000  @0x3ac7c / 0x3aca0-ac
                       6bbe boost assist  +/-0x800   @0x3ac80 / 0x3ac90-9c
                       6bd0 damping       +/-0x800   @0x3ac78 load / 0x3ac84-8c gate
                       6b26 friction      +/-0x400   @0x3ac98 / 0x3acb0-b8
                       6ad4 resonance     +/-0x2800  @0x3aca8 / 0x3acbc-c4
                     CAUTION for future tracers: in the V39 image the 6bd0 load at 0x3ac78 is REPLACED
                     by the cave hook (`jr 0xc4b34`) and reappears at 0xc4b58. Trace stock/V38 for
                     structure; a V39 trace will misreport the cave as native control flow.
      r24/r26 gate : NOT the zero-type idiom -- these two are SATURATING CLIPS to +/-0x2000
                     (`cmovle` selects, @0x3ab82-94 for r26 and @0x3ac42-54 for r24), then summed
                     ungated @0x3acc8-ca. [VERIFIED 2026-07-19] They are therefore the LOWEST
                     discontinuity risk of the group, which is consistent with V39's r24 suppression
                     not changing the on-car vibration.
      Add order    : @0x3acc8-0x3acda  r26+r24 -> +6b86 -> +6bd0 -> +6bbe -> +6b26 -> +[6b62/6ade]
                     -> +6ad4 -> +[accumulator] -> jarl FUN_00036682, whose return in r10 is combined
                     @0x3ace6 (`add r14,r10`). [VERIFIED 2026-07-19]
      Output clamp : @0x3acf0-0x3ad2a this is a true SATURATING CLAMP, not a zeroing gate: positive
                     overflow stores +0x2800 (@0x3acf6/fa), negative stores -0x2800 (@0x3ad0e/12),
                     in-range stores the raw sum (@0x3ad20). Lockstep gp-0x4ce0 checked on all three
                     paths -> FUN_0006b9fa on MISMATCH (not on saturation). So the aggregator output
                     is NOT itself a chatter source. [VERIFIED 2026-07-19]
      Mode         : POLARITY VERIFIED 2026-07-19 on stock code.bin at the instruction level.
                       0x3aa34  ld.bu -0x67ac[gp],r8      (a BYTE, not a word)
                       0x3aa3c  cmp 0x1,r8 ; cmovh 0x0,r8,r11 ; cmp 0x1,r11 ; setfe r20
                       0x3ac58  cmp r0,r20 ; be 0x3ac78    -> r20==0 takes the FULL path
                     So gp-0x67ac == 1 selects the REDUCED path; anything else selects FULL.
                     REDUCED (fallthrough, `br 0x3ace2` @0x3ac76) = LKAS + [dead, gated by cal
                     0xC64AB] + [s62, gated by cal 0xC64AC]; BOTH cals read 0x00 in the V38 image, so
                     reduced == LKAS + s62 (dead has no writers). It skips the six sibling lanes,
                     r24/r26, AND the FUN_00036682 filtered-term call @0x3acdc entirely.

                     *** MECHANISM CORRECTED -- the old "sticky mixer-source state, dormant because
                     A160 has no source mode 6/7" line was WRONG on the mechanism. *** VERIFIED:
                       0x27732  ld.bu -0x3d98[gp],r8
                       0x2773a  st.b  r8,-0x67ac[gp]      (+ shadow gp-0x4c37 @0x2773e)
                     gp-0x67ac is an UNCONDITIONAL per-call COPY of gp-0x3d98, not a latch. And
                     gp-0x3d98 is itself RECOMPUTED FRESH each call (@0x27314, a 32-bit store) by an
                     11-iteration loop (0x271de-0x27304) over the byte array gp-0x61a0[0..10],
                     comparing each element against literals 2/3/4 and folding to a BOOLEAN -- so it
                     can only ever be 0 or 1. The "no 6/7" argument is therefore moot: the value is a
                     live per-cycle boolean, not a mode index.

                     *** RESOLVED 2026-07-19 -- THE REDUCED MODE IS UNREACHABLE ON THE A160. ***
                     gp-0x61a0 is distribute's 11-entry per-source TYPE array, echoing the cal table
                     at tp+0x5124 == 0xC4124. Read from both stock code.bin and _v38_plain_image.bin,
                     that array is (0,0,5,0,5,5,0,0,0,5,0) -- and the fold qualifies an element only
                     if it equals 2, 3, or 4. NO A160 ENTRY MATCHES, so the boolean is always 0 =>
                     gp-0x3d98 = 0 => gp-0x67ac = 0 => the aggregator takes the FULL path every
                     cycle. It cannot toggle, so it is NOT the tens-of-Hz vibration source.
                     So the old "dormant" verdict was RIGHT, but its stated reason was garbled: the
                     discriminating literals are 2/3/4, not "6/7". build_v39_tva.py already guards
                     this array (@0xC4124) for exactly this reason -- keep that guard in every build.
                     [Residual inference: that gp-0x61a0[i] mirrors tp+0x5124[i] rather than carrying
                     an independent runtime value. Consistent with all ~30 touch sites living in
                     FUN_00025c32, but not separately instruction-proven.]

                     RATE MISMATCH worth noting: FUN_00026c80's call site @0x225f6 is gated ONLY by
                     the master task-enable flag with NO phase mask, so gp-0x67ac refreshes every task
                     tick -- but the aggregator samples it on only 4 of 16 phases.
      Scheduling   : aggregator call VERIFIED @0x2291e from w_steer_control_task FUN_0002214a, gated
                     by `andi 0xc30,r25,r22` @0x2269a + `cmp r0,r22 ; be` @0x22916. This pins the
                     previously-inferred 0xC30 mask ({4,5,10,11}, 4 of 16) to real instructions.
      Writes       : sum -> clamp +/-0x2800 -> gp-0x6b94 (0xFEDF146C), lockstep-shadowed at gp-0x4ce0
    CONFIDENCE     : [VERIFIED] the lane list, the per-lane range-gate idiom, the store + lockstep, and
                     that gp-0x6b94 is the SAME variable the governor chain already consumes.

    *** THE LOAD-BEARING CONSEQUENCE ***
    Every base-assist lane joins LKAS in gp-0x6b94 before the first governor, compensation add, and
    gp-0x6acc-driven Q15 shaper/integrator. The shaper's final output also receives a separate
    gp-0x6afe lane before the second governor, so this is not literally a single path to the motor.
    The aggregate-derived assist path nevertheless shares the same first governor and r20 state factor,
    explaining why a soft-EME event can feel like broad power-assist loss rather than only LKAS easing.
    ---------------------------------------------------------------------------------------------------
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
        resonance = _range_gate(lanes["resonance_6ad4"], 0x2800)
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
# MOTOR-RATE ADAPTIVE CAP -- exact byte layout, verified against _v38_plain_image.bin 2026-07-19.
#
# LIVE (app) BANK A, addressed off app tp=0xBF000 exactly as the governor trace cites:
#   tp+0x620E -> 0xC520E   X array          tp+0x6030 -> 0xC5030   Q13 slopes
# Record layout at 0xC520C: u16 count(=5), then X[5], then Y[5]  -- 22 bytes.
#   copy 1: header 0xC520C, X 0xC520E, Y 0xC5218 | slopes 0xC5030 (8 bytes, 4 x s16)
#   copy 2: header 0xC5224, X 0xC5226, Y 0xC5230 | slopes 0xC5038 (8 bytes, 4 x s16)
# Both copies are byte-identical in stock and V38. Shift cal tp+0x6160 -> 0xC5160 = 13.
#
# *** TWO FURTHER BANKS EXIST, byte-identical to bank A, at a +0x34C00 then +0xC00 stride: ***
#   bank B: tables 0xF9E0C / 0xF9E24, slopes 0xF9C30 / 0xF9C38
#   bank C: tables 0xFAA0C / 0xFAA24, slopes 0xFA830 / 0xFA838
# Bank A is the tp-addressable one the app reads. Banks B and C are NOT reachable from app tp and
# their role is [OPEN] -- other part-number variants, or a second-partition copy.
#
# *** SHADOW RESOLVED 2026-07-19 -- IT IS A PURE DUPLICATE STORE, NOT A RECOMPUTATION. ***
# [VERIFIED at raw instruction level; this is what cleared V40 to patch bank A alone.]
# All three mode branches of FUN_0007b022 compare OLD gp-0x4f64 against OLD gp-0x448a *to each other*
# -- never against table bytes -- then store ONE locally-computed register to both, back-to-back with
# no intervening load:
#     0x7c2d2 ld.hu -0x4f64[gp],r16 ; 0x7c2da ld.hu -0x448a[gp],r7 ; 0x7c2de cmp r7,r16
#     0x7c2e0 bne 0x7c2ec -> jarl FUN_0006b9ee (fault 0x17)
#     0x7c2e2 st.h r9,-0x4f64[gp]   ; 0x7c2e6 st.h r9,-0x448a[gp]     opcode halfword 644f in BOTH
#     branch 2: st.h r7  @0x7c3b4 / 0x7c3b8 (643f)
#     branch 3: st.h r16 @0x7c47c / 0x7c480 (6487)
# The identical opcode halfword within each pair encodes the SAME source register, which is direct
# byte evidence of a duplicate store rather than two independent derivations. The -0x448a
# displacement occurs 8 times image-wide, 6 of them here; there is no other writer.
# CONSEQUENCE: hard-fault-eligible index 0x17 (motor off + power cycle) can fire only on RAM
# divergence BETWEEN cycles. A calibration edit to ANY bank cannot trip it.
#
# Still [OPEN]: FUN_0007b022's preamble reads BOTH bank-A copies every cycle and builds two parallel
# parameter blocks; whether they cross-check each other was not established. Given the V27
# asymmetric-mirror precedent, always patch the two copies byte-identically.
#
# CRC: the 49-block chain has exactly ONE gap, [0xC5000,0xC6000) -- 4096 bytes, and bank A lives in
# it. Bank A therefore needs NO CRC recompute. Banks B and C are inside block [0xF9000,0xFCFFC),
# trailer 0xFCFFC, which no build in this kit has ever touched.
#
# NO FLOAT MIRROR EXISTS for this table: an image-wide scan for f32/f64 encodings of every Y value,
# at raw and 1/1024 scale, found nothing for 5325, 2406, or 1587 in any form. The V27 int/float
# asymmetry failure mode does not apply here. Likewise the slew step cals 0xC6206/0xC6208 have no
# matched float pair (205 has no float representation anywhere in the image at any scale).
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

    ---------------------------------------------------------------------------------------------------
    *** THE LEADING V38 RATCHET HYPOTHESIS (2026-07-19) ***

    The adaptive cap's axis is MOTOR RESOLVER ELECTRICAL-ANGLE RATE (7-hop verified; see
    soft_eme_windup_shaper's FIRMWARE MAP), so the cap tapers with how fast the MOTOR is turning,
    not with road speed. The A160 table falls 5325 -> 512 across z = 1050 -> 4100, and its FLOOR is 512.

    The load-bearing consequence, which this function makes numeric:

        STOCK V9's maximum LKAS demand is 417 counts, which is BELOW the cap's 512 floor.
        Stock LKAS can therefore NEVER be rate-capped -- at any motor rate whatsoever.

    Every build that raises LKAS reach above 512 crosses that line. V31 (835) binds from z~3980;
    V38 (1782) binds from z~3414, and with base assist in the aggregate from z~2229. Because the
    aggregate is capped BEFORE the motor responds, this closes a loop:

        torque applied -> motor accelerates -> z rises -> cap falls -> torque cut
                       -> motor decelerates -> z falls  -> cap rises -> torque restored -> repeat

    That is a relaxation oscillator whose period is set by motor + column inertia, and the taper is
    steep enough to make it violent: 1586 at z=3700, 780 at z=4000, 512 at z=4100 -- a ~3x swing
    across a 400-count rate change. It predicts a ratchet that (a) appears only while the wheel is
    MOVING, (b) is worst during fast steering motion such as pulling away from a stop, (c) is
    independent of ROAD speed, and (d) is absent when the driver supplies the torque, because the
    driver's torque is mechanical and never passes through this cap. All four match the on-car report.

    It also explains why no prior build showed it: V38 is the first flashed build whose LKAS-path
    demand clears the 512 floor by a wide margin.

    *** CALIBRATION WARNING ***
    A prior session investigated and REJECTED raising the nominal governor cal 0xC6202, on the
    reasoning that "nominal 4762 > max command, so the governor does not bind". That reasoning is
    sound for the NOMINAL term and irrelevant here: this hypothesis is entirely about the TAPERED
    regime, which that session explicitly set aside as "the thermal/mechanical protection working".
    The taper is RATE-scheduled, not thermal, so the dismissal does not transfer -- but the protection
    concern is real. This cap limits torque during fast motor motion; flattening it wholesale would
    remove genuine mechanical protection. Any change here must be a measured raise of the taper's low
    end, not its removal, and must be scored against motor thermal behaviour.

    CONFIDENCE : [VERIFIED] the table values, the cap's rate axis, and this arithmetic.
                 [INFERRED] that the loop actually oscillates on-car at the observed frequency --
                            that requires plant inertia this model does not have.
    ---------------------------------------------------------------------------------------------------
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

    ---------------------------------------------------------------------------------------------------
    *** THE LEADING V38 RATCHET ROOT CAUSE (2026-07-19) -- see motor_torque_governor's FIRMWARE MAP ***

    The governor's away-from-zero slew step is an ABSOLUTE count (cal 0xC6206=512 fast /
    0xC6208=205 slow), and the SLOW 205 step is the one selected during a hard dynamic turn --
    verified: gp-0x67f5 is forced to 0xFF with no debounce whenever the driver's raw torque diverges
    from the voted average by >= 65 counts, and also goes slow whenever voted |torque| >= 640.

    V38 raised the LKAS target ~4x and left both step cals at stock. Ramp time is target/step, so
    the ramp got ~4x longer -- while the sign-crossing reset (which zeroes the held value outright)
    stayed instantaneous. Slow build + instant collapse = a ratchet.

    *** THE INVARIANT V38 BROKE IS RAMP TIME, NOT STEP SIZE. ***
    This is the same class of error as the pre-V31 soft-EME lineage, where the invariant turned out
    to be the ABSOLUTE margin between command and bound rather than the ratio. Here the quantity that
    must be held constant across a reach change is the number of cycles to full command. A build that
    multiplies reach by N and leaves the slew steps alone multiplies its own ramp time by N.

    CONFIDENCE : [VERIFIED] the slew structure, the sign-crossing reset, the step cals, and the
                            gp-0x67f4/gp-0x67f5 selector logic that pins the step slow on hard turns.
                 [OPEN]     the wall-clock conversion -- the task rate is contested (100 Hz vs 1 kHz)
                            and MUST be settled before any Hz claim. Cycle counts below are exact;
                            milliseconds are deliberately not computed.
    ---------------------------------------------------------------------------------------------------
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
    *** THE CENTRAL ANALYTICAL CONSTRAINT OF THE 2026-07-20 SESSION. READ THIS BEFORE PROPOSING ANY
    FIX FOR EITHER ON-CAR SYMPTOM. It partitions the two symptoms into DIFFERENT stages of the chain
    and it retro-explains why both V39 and V41 changed nothing. ***

    ---------------------------------------------------------------------------------------------------
    THE ARGUMENT

    V38 raised the arbitration output gain 0xC646C 891 -> 3564 (4x). The operator CORRESPONDINGLY
    quartered openpilot's lateral PID (kp 0.6 -> 0.15, ki 0.18 -> 0.045), confirmed 2026-07-20. So the
    closed-loop gain is back at its stock value.

    Now follow the units. The chain is

        C (CAN STEER_TORQUE)  ->  setpoint = C * -4  ->  lane = (setpoint * gain) >> 15  ->  everything

    and everything downstream of the gain -- the aggregator, the governor and its 512/205 slew, the
    motor-rate cap and its 512 floor, the +/-8192 sanitize, the shaper walls -- is calibrated in
    ABSOLUTE LANE COUNTS, and V38 did not change how lane counts map to motor torque.

    Therefore, for THE SAME PHYSICAL TORQUE AT THE WHEEL:
        * the comma now sends C/4, the gain multiplies by 4, and the LANE COUNTS ARE IDENTICAL to stock
        * => every stage DOWNSTREAM of the gain sees EXACTLY the stock count sequence
        * => no downstream absolute-count limit can bind any differently than it did on stock
        * but the SETPOINT is 4x SMALLER than stock, because setpoint = C * -4 and C is quartered
        * => every stage UPSTREAM of the gain sees counts 4x closer to zero than stock did

    The ONE exception downstream: torque ABOVE what stock could ever produce. Stock's maximum LKAS lane
    was 417 counts. Between 418 and 1782 the chain is operating in a regime that literally never
    existed before, so downstream limits calibrated around stock's range are newly reachable there.

    ---------------------------------------------------------------------------------------------------
    THE PARTITION THIS FORCES

      RATCHET on sharp turns (large commanded torque):
          The request EXCEEDS stock's 417-count ceiling, so this is the genuinely-new downstream
          regime. A downstream absolute-count limit is a legitimate suspect here.
          Surviving candidates: the governor slew (512/205 per cycle + sign-crossing reset).
          FALSIFIED by V41: the motor-rate adaptive cap.

      VIBRATION -- *** THE PREMISE BELOW WAS WRONG AND IS RETRACTED 2026-07-21. See the correction. ***
          [RETRACTED] "at ~5 mph, small command dithering around zero: the request sits WELL WITHIN
          the range stock produced every day, so a downstream limit CANNOT be the mechanism; the cause
          must be UPSTREAM of the gain where counts are 4x nearer zero."

          *** CORRECTION OF RECORD (operator, after the V42 drive) ***
          The vibration occurs while **LKAS ALONE IS TURNING THE WHEEL**. That is a LARGE command,
          not a near-zero one -- pure-LKAS steering against tyre/rack load is exactly the regime where
          the request runs at or near V38's ceiling. And it VANISHES the moment the driver adds hand
          torque, which REDUCES the LKAS command (the driver supplies part of the effort and the PID
          error collapses). So the correlation is:

                LARGE pure-LKAS command  -> vibration
                SMALLER / shared command -> no vibration

          The vibration therefore lives in the SAME ">417-count, never-existed-before" downstream
          regime as the ratchet, NOT in a near-zero upstream deadband. This inverts the partition:
          downstream stages (governor, shaper walls, motor-protection limits) are BACK IN SCOPE for
          the vibration, and the near-zero upstream candidates (the 0xC61B8 deadband, the sign latch,
          quantisation of a shrunken setpoint) are OUT unless independently re-motivated.

          Two prior "eliminations" that rested on the retracted premise are downgraded to UNTESTED,
          not re-opened as leading candidates: they were argued against a near-zero symptom that is
          not the symptom we have.

          Corroborating on-car facts that SURVIVE the correction: the vibration appears only with
          openpilot engaged, and the driver can move the wheel fast by hand without provoking it.
          NOTE the second fact is weaker than it was recorded as being -- see
          vibration_hands_off_analysis(), "the damping confound".

    ---------------------------------------------------------------------------------------------------
    WHY THIS RETRO-EXPLAINS TWO FAILED BUILDS
      V39 suppressed the direct Sensor-B derivative lane r24  -- DOWNSTREAM of the gain. No effect.
      V41 flattened the motor-rate adaptive cap                -- DOWNSTREAM of the gain. No effect.
    Both were aimed at the vibration, and by this argument neither could ever have moved it.

    CONFIDENCE : [VERIFIED] the gain/setpoint arithmetic and the stage ordering.
                 [CONFIRMED] the openpilot PID rescale and the engaged-only character of the vibration
                             (operator, 2026-07-20).
                 [INFERRED]  the partition itself. It is a units argument, not a trace, and it assumes
                             the ONLY V38 change relevant near zero is the gain. V38 also moved the
                             source clamps 512->2048, the corridor/boost walls 4096->5120, and the
                             setpoint limit 15360->16384 -- none of which bind near zero, which is why
                             the argument is believed to hold there. It would NOT hold at large command.
    ---------------------------------------------------------------------------------------------------
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
        # *** REVISED 2026-07-21 after the V42 drive. The old value here was
        # "UPSTREAM of gain 0xC646C", which followed from the RETRACTED near-zero premise. The
        # operator reports the vibration during pure-LKAS TURNING, i.e. LARGE command, so it sits in
        # the same >stock-ceiling downstream regime as the ratchet. ***
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
    *** THE GOVERNOR SLEW-STEP SELECTOR IS A DRIVER-TORQUE-KEYED BANDWIDTH GATE ON THE TORQUE
    COMMAND. Found 2026-07-21. It is the FIRST candidate in this investigation whose gating condition
    is itself byte-verified to match the operator's hands-off/hands-on discriminator. ***

    ---------------------------------------------------------------------------------------------------
    THE MECHANISM  [VERIFIED -- FUN_0004503c consumer, FUN_00041eec producer]

    The governor's per-cycle slew STEP is not a constant. It is selected by `gp-0x67f5`, which is
    written ONLY by FUN_00041eec -- the same function that produces the column-torque voters
    gp-0x6a62 / gp-0x6a5e. The selector is:

        puVar29 (rate-limited vote of gp-0x6a5e, i.e. DRIVER COLUMN TORQUE)
            >= cal 0xC531E (1062), sustained cal 0xC64E7 (10) cycles  -> gp-0x67f5 = 1 -> STEP = 205
            <  1062, sustained 10 cycles                              -> gp-0x67f5 = 0 -> STEP = 512
        reset state (0xFF)                                            -> routes to the SLOW step

    So:   HANDS OFF  -> STEP = 512  (fast tracking, wide bandwidth, LESS damped)
          HANDS ON   -> STEP = 205  (2.5x slower, narrow bandwidth, MORE damped)

    *** THE DIRECTION MATCHES THE OPERATOR'S OBSERVATION EXACTLY. *** Note also that the SLOW step is
    the reset/default state, so "always slow" is the conservative side of this switch, not a novel one.

    ---------------------------------------------------------------------------------------------------
    WHY A RATE LIMIT IS A BANDWIDTH GATE, AND WHY IT LANDS IN THE TENS-OF-Hz BAND

    A per-cycle slew limit passes a sinusoid of amplitude A at frequency f only while its peak slope
    fits in one step:   2*pi*f*A/tick <= STEP   =>   f_max = STEP*tick / (2*pi*A)

    Above f_max the limiter clips the waveform -- it attenuates amplitude and adds phase lag. So the
    STEP selector is literally switching the command path's bandwidth, and the switch is thrown by
    driver torque. Evaluated below for both steps. The key quantity is not the corner on the FULL
    command but the amplitude of RIPPLE the limiter will pass at the symptom frequency: at a given f,
    the largest ripple that survives is A_max = STEP*tick/(2*pi*f), which is 2.5x larger on the fast
    step. Hands-off therefore passes ~2.5x more tens-of-Hz ripple to the motor than hands-on does.

    ---------------------------------------------------------------------------------------------------
    WHAT THIS DOES AND DOES NOT ESTABLISH

    [VERIFIED] the selector, its cals, its driver-torque input, the debounce, and the 2.5x step ratio.
    [VERIFIED] the direction of the effect matches the operator's report.
    [INFERRED] that this CAUSES the vibration. A bandwidth gate only matters if something is actually
               oscillating in that band. The trace found no fast-fluctuating target: the upstream Q15
               bound-factor voting loop is MIN/clamp-only (not toggling) and the selector's own
               debounce is 10 cycles (far too slow to be the beat itself).
    [OPEN]     the identity of the 6-element voting-loop channels feeding the slew target
               (gp-0x6544/652c/6514/64fc/6538/6520/6508/64f0). If any carries fast content, this
               closes into a full mechanism.

    So this is a TRANSMISSION PATH for the vibration, demonstrably gated by the right variable -- not
    yet a proven SOURCE. That is still a materially better position than r24/r26/the rate cap, none of
    which had any verified linkage to the hands-off condition at all.

    *** TICK-RATE CAVEAT: every Hz figure below scales linearly with `tick_hz`, which is [INFERRED]
    1 kHz from the OSTM0 reload (80000 counts, ~80 MHz assumed but NOT confirmed). The CYCLE counts and
    the 2.5x RATIO are tick-independent and are the load-bearing parts. ***
    ---------------------------------------------------------------------------------------------------
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
    *** THE V43 EDIT: restore the disabled pole on FUN_0003a382's derivative branch. ***
    cal 0xC644A (tp+0x744a): 1024 -> 64.   Cal-only, one halfword.

    ---------------------------------------------------------------------------------------------------
    WHICH CAL, AND WHY THIS ONE  [VERIFIED at instruction level, two independent agents]

        0xC6450  read @0x3a7f0, consumed @0x3a7fa  -> EMA of state gp-0x367c
                 target = (clamp(gp-0x4f60 - reference, +/-0x2800) * LERP_A) >> 10
                 == the PROPORTIONAL / filtered-torque branch.  NOT the edit target.

        0xC644A  read @0x3a860, consumed @0x3a86c  -> EMA of state gp-0x3680
                 target = clamp(FACTOR_D * (TARGET_RAW - gp-0x3684_prev) >> 10, +/-0x2800)
                 gp-0x3684 is a PURE ONE-SAMPLE DELAY, rewritten unconditionally every cycle
                 (`0x3a840 st.w r14,-0x3684[gp]`, no filtering), so (TARGET_RAW - gp-0x3684_prev)
                 is a literal one-sample discrete difference.
                 *** 0xC644A IS THE GAIN ON THE LAG IMMEDIATELY DOWNSTREAM OF THAT RAW DIFFERENCE.
                 IT IS THE DIRTY-DERIVATIVE POLE, AND IT IS CALIBRATED TO UNITY, I.E. SWITCHED OFF. ***

    Model phrasing corrected en route: the standing text described "gp-0x3688/gp-0x3684 ... a raw
    sample-to-sample difference" as though nothing filtered it afterwards. Half right -- gp-0x3684 is
    the delay feeding the difference, but there IS a dedicated lag right after it (state gp-0x3680,
    gain 0xC644A); it has simply been calibrated to unity so it currently does nothing. gp-0x3688 is a
    SEPARATE fourth state (holds max(0, stateA_new - an authority term), @0x3a800/0x3a83c) feeding a
    different min-select later; it is NOT on the 0xC644A path and this edit does not touch it.

    ---------------------------------------------------------------------------------------------------
    WHY IT IS SAFE  -- and the DC claim is verified in INTEGER arithmetic, not just idealised

        state_new = state_prev + (((target*32) - state_prev) * GAIN) >> 10
        `shl 0x5` (=*32) confirmed @0x3a7f6 and @0x3a868; the summing junction's single
        `sar 0x5` (=/32) confirmed @0x3a880.

    *** PRECISION CORRECTION -- "changes NO steady-state value" is TOO STRONG. The accurate claim is
    "changes it by a bounded, one-sided, sub-count amount". ***
    In REAL arithmetic the fixed point is state == target*32 for any nonzero GAIN. In the ACTUAL integer
    arithmetic, V850 `sar` floors toward -infinity, which makes the fixed-point set ASYMMETRIC:
      * approaching the target from ABOVE (diff negative): any nonzero product floors to <= -1, so the
        state always keeps decrementing and converges EXACTLY.
      * approaching from BELOW (diff positive): floor(diff*GAIN/1024) == 0 for any diff < 1024/GAIN, so
        the state can STALL anywhere in the half-open band (target - 1024/GAIN, target].
    So there IS a genuine steady-state residual for every GAIN < 1024. It is bounded, and one-sided in
    the direction of UNDER-reporting a sustained RISING derivative -- never over-reporting.

        max residual ~= 32 / GAIN   counts at the output (after the summing junction's >>5)

        GAIN=1024 (stock) -> <=0.03 counts      GAIN=64 -> <=0.5 counts
        GAIN= 128         -> <=0.25 counts      GAIN=32 -> <=1.0 counts
        GAIN=  16         -> <=2 counts         GAIN= 4 -> <=8 counts
    Verified two ways that agree: direct integer simulation (measured 15 state-counts at GAIN=64) and an
    analytic bound (1024/GAIN = 16 state-counts). The simulation independently reproduced the asymmetry
    -- positive targets stalled one LSB short, negative targets landed exact -- before the analytic
    explanation was available, which is why the two are a genuine cross-check and not one restating the
    other.

    *** PRACTICAL BOUND ON HOW FAR THIS LEVER CAN BE PUSHED: below roughly GAIN=16-32 the residual stops
    being negligible and becomes a real few-count bias. At GAIN>=64 it is sub-count against a lane
    contributing an estimated 150-250 counts and a 1782-count LKAS reference. ***

    *** GAIN = 0 IS DEGENERATE AND MUST NEVER BE USED: the state freezes and never converges. It is
    NOT "just a slower version of the same thing". Do not round a candidate down to zero. ***

    Both reads are `ld.hu` (UNSIGNED) -- no analogue of the 0xC61B8 dual-signedness trap at these
    sites, and all candidate values are small positive numbers safe under either interpretation.
    No shadow/lockstep partner: a direct scan of FUN_0003a382's full disassembly finds NO `-0x4c`
    displacement anywhere, so none of gp-0x6ad4, gp-0x367c, gp-0x3680, gp-0x3684, gp-0x3688 is
    lockstep-mirrored. The function is a pure leaf (zero `jarl`), so nothing inside it can raise a
    shadow-mismatch fault. gp-0x6ad4 itself has exactly TWO touches image-wide (writer @0x3a8a0,
    aggregator reader @0x3aca8).

    [OPEN, dispatched] a genuine image-wide read-site count for 0xC644A / 0xC6450. Ghidra does not
    resolve tp-relative displacements to xrefs (it returns zero hits for cals that provably ARE read),
    so only an r2 instruction-pattern scan can settle it. Expected clean; not yet verified clean.

    ---------------------------------------------------------------------------------------------------
    *** IS THERE A SHADOW FLOAT PATH FOR THE DRIVER-ASSIST CHAIN? NO. ARCHITECTURAL FINDING,
    2026-07-21 -- and it is the reason a DYNAMICS edit here is safe, not just a CLAMP edit. ***

    This firmware has TWO shadow mechanisms and only one is dangerous for a calibration edit:
      (1) SAME-TYPE duplicate stores (the gp-0x4cXX / gp-0x44XX idiom). Both stores receive the
          identical freshly-computed value in the same instruction sequence, so a cal edit CANNOT
          desync them. FUN_0003a382 has none at all.
      (2) INT/FLOAT LOCKSTEP: an INDEPENDENT float re-computation compared against the integer result,
          with SEPARATE float calibration mirrors. *** This is the V27 brick class. ***

    The standing justification for cal edits was "raising a clamp translates BOTH sides and opens no
    gap". That argument is about CLAMPS. V43 changes DYNAMICS -- it adds a ~15.5-cycle lag to an integer
    lane. If any float path re-derived the aggregate from float sources with its own filtering, a lag on
    the integer side alone would open a divergence no clamp edit ever could. So this had to be checked.

    IT IS CLEAR, AND FOR A STRUCTURAL REASON [VERIFIED -- full decompile of FUN_00043e44, 0x43e44-0x449fc,
    every input classified as INT-READ-THEN-CONVERTED vs FLOAT-RAM-READ]:

        gp-0x6acc  (post-governor command)      (double)(int)*(short*)  -> INT read, converted
        gp-0x6b98  (final FOC demand)           (float)(int)*(short*)   -> INT read, converted
        gp-0x6bf0  (driver-assist magnitude)    (double)(int)*(short*)  -> INT read, converted
        gp-0x6b94  (raw aggregate)              DOES NOT APPEAR in the function at all
        every individual aggregator lane -- gp-0x6bbe boost, gp-0x6bd0 damping, gp-0x6b26 friction,
        gp-0x6b62 return-to-centre, gp-0x6b86/gp-0x69a4, the inline r24/r26, and gp-0x6ad4 itself --
                                                NONE APPEAR ANYWHERE

    What the float side DOES independently re-derive is the WALL/BOUND, not the command: its own float
    LERP tables (tp+0x75d4, tp+0x7648-0x767c, tp+0x7594-0x75c4 -- genuine *(float*) reads, not
    conversions) and its own persisted float lag/ramp state (gp-0x3554, gp-0x3558, gain tp+0x7418),
    tracking the corridor/boost bound independently of FUN_00042af8's integer wall. That is the
    already-known wall lockstep, and the bound's inputs are untouched by V43.

    *** THE GENERALISATION THAT MATTERS BEYOND V43: THE ASSIST CHAIN IS INTEGER-ONLY END TO END. ***
    gp-0x6acc and gp-0x6b98 are read FRESH, as integers, every cycle, with NO MEMORY of how they were
    computed. The float side has no independent expectation of what they "should" be -- it takes
    whatever the integer path produced and checks it against the wall. So there is only ONE computation
    of the assist/aggregate quantity in this firmware, and a second path cannot fall out of step with
    it because no second path exists. The V27 risk class does not apply to the assist chain at all.
    *** The int/float discipline in this firmware guards BOUNDS, not the COMMAND. ***

    NO FLOAT MIRROR EXISTS FOR 0xC644A / 0xC6450 -- closed on two independent grounds [VERIFIED]:
      1. FUN_0003a382 contains ZERO floating-point instructions (468/468 scanned for any FP mnemonic).
         A pure-integer function: nothing in this lane could read a float mirror even if one existed.
      2. Both cals sit in ordinary integer cal space -- float-reinterpreted in place they read
         -1.435e-42, denormal garbage. The genuine float-cal complex starts ~0x110 bytes later.

    FLOAT-CAL COMPLEX MAP, 0xC6560-0xC668C (count-prefixed sub-tables, all clean engineering values):
        0xC6598/9C     5.0f      CORRIDOR upper mirror   (int 0xC674E/50 = 5120)
        0xC65AC/B0    -5.0f      CORRIDOR lower mirror   (int 0xC675A/5C = -5120)
        0xC65C4/C8/CC  5.0f x3   BOOST floor mirror      (int 0xC6768/6A/6C = 5120)
        0xC6664-67C    1.0f x7   LERP_B envelope         (see reference_c6664_lerp_b_envelope.md)
    *** Note what this map SHOWS: every float mirror in it twins a WALL or an ENVELOPE. None twins a
    command lane. That is the same conclusion as the structural argument above, reached from the data
    layout instead of from the code. ***
    One cluster flagged unattributed, 0xC6634-40 = 0.25f x4. CHECKED AND EXCLUDED: not a mirror of any
    FUN_0003a382 table. L1 = [0.25, 0.25, 0.2197, 0.1494] -- the first TWO match, the last two do not;
    L2 = [0.0957 x4]; L3 = [2.0 x4]; L4 = [1.0 x3]. A casual check against L1's leading values would
    have produced a FALSE MATCH; only the full row rules it out.
    Also verified zero (every hit adjudicated): gp-0x6bf0 (23 genuine touches, 13 functions) and
    gp-0x6bbe (8 touches) are ALL ld.h/st.h 16-bit signed int -- no float twin, no gp-0x6dXX companion.

    *** ⚠ REOPENED -- I CLOSED THIS PREMATURELY. See the RETRACTION at the end of this block.
    THE WEIGHT-32 FLAG: two of three inputs traced safe, the third UNRESOLVED. [PARTIAL] ***
    Traced to concrete registers (FUN_00043e44) and cross-checked against the kit's existing
    reference_accord_eme_bit32_float_monitor.md, which had already characterised this exact structure
    at these exact addresses -- an independent corroboration, not a re-derivation:

        0x4486e  gp-0x4f64  governor limit         INT ld.hu -> cvtf.ws        }
        0x4487a  gp-0x6dac  "speed-scaled float"   genuine ld.w float RAM read } -> summed, clamped
        0x4489c  selector tp+0x74c9 picks gp-0x6b04 (INT ld.h -> cvtf) OR an  }    to (floor, 9.0)
                 SM2/SM3 consensus term rooted in the SAME gp-0x6acc int conv }    = r9 = "cmd_final"
        0x448d6  gp-0x6b98  delivered FOC demand   INT ld.h -> cvtf.ws
        0x448de  nmsubf.s -> r1 = cmd_final - delivered/1024
        0x448e2  compared against +/-5/1024 ~= +/-5 raw counts -> weight 32

    So it is an AGREEMENT check between two points on the integer command pipeline, plus an untouched
    additive float offset. The command-side term (gp-0x6acc or gp-0x6b04) and the delivered-side term
    (gp-0x6b98) BOTH come from the integer path, so V43's lag shifts BOTH SIDES OF THE SUBTRACTION
    IDENTICALLY -- this is case (a), not the feared case (c). gp-0x6dac is an additive term V43 does
    not touch.

    *** ⚠⚠ RETRACTION -- TWO ARGUMENTS I USED TO CLOSE THIS WERE WRONG. THE ITEM IS REOPENED AND IT
    GATES THE FLASH. ***

    [RETRACTED #1] "gp-0x6dac is a small untouched ADDITIVE OFFSET, so V43 shifts both sides of the
    subtraction identically." WRONG ON MAGNITUDE. gp-0x6dac is gated to ~+/-10 and cmd_final clamps at
    9.0, i.e. up to ~10240 counts -- FULL COMMAND SCALE, not a trim term. And the comparison is tight:
    cmd_final*1024 must match the delivered demand within 5 COUNTS. That is a close EXPECTATION of the
    delivered value, not a loose bound, so "additive offset" was never a safe reading.

    [RETRACTED #2] "V43 smooths the command, reducing d(cmd)/dt and therefore any pipeline-lag residual,
    so it moves the monitor toward its safe side." Only valid if the float side is NOT independently
    tracking the command. If gp-0x6dac IS a float tracker with its own filtering, then adding a lag to
    the INTEGER side and not the float side makes them diverge MORE during transients, not less --
    exactly backwards.

    So the case genuinely turns on what gp-0x6dac is, and I do not know:
      (b) wall/bound/envelope-adjacent, or otherwise not command-tracking -> additive -> V43 CLEAR
      (c) an independent float re-derivation of the command with its own filtering -> V43 NEEDS REWORK
    gp-0x6dac's WRITER is UNLOCATED. Excluded by full decompile: FUN_00043e44 itself (one occurrence,
    the read at 0x4487a, no store), FUN_0004503c (the governor -- pure fixed-point, zero float
    instructions), FUN_00037fe6 (producer of gp-0x6ad6 -- also pure fixed-point). Under dispatch.

    Suggestive but NOT evidence: gp-0x6dac sits immediately adjacent to gp-0x6db0 / gp-0x6db4 /
    gp-0x6db8 -- the known float corridor twins and the LERP_B velocity clamp -- so the RAM
    neighbourhood is float-twin territory, and the kit's own
    reference_accord_eme_bit32_float_monitor.md already labels it "speed-scaled float" at this exact
    address. Adjacency and an unverified label are not a trace. Do not close on them.

    *** ⚠ THIRD RETRACTION -- THE "127 < 128" BACKSTOP IS MUCH WEAKER THAN IT WAS REPEATEDLY STATED. ***
    It was offered several times as "even all seven flags true cannot trip it". Reading the dwell SM
    properly (reference_accord_eme_bit32_float_monitor.md):
        state 1: ANY flag set (fVar22 > 0)          -> state 2, timer starts
        state 2: fVar22 > 0 AND timer >= ~10 cycles -> state 3, fVar22 += 1024.0
        state 3: unconditional                          fVar22 += 1024.0  -> 1024 >> 128 -> FAULT
    So 127 < 128 only rules out a SINGLE-CYCLE trip. *** ANY ONE FLAG HELD FOR ~10 CONSECUTIVE CYCLES
    ESCALATES AND TRIPS. *** Weight-32 firing continuously for 10 cycles IS motor-off. This makes the
    item more consequential, not less, and the margin should never have been cited as reassurance.

    *** ✅ gp-0x6dac IS RESOLVED BY TRACE: VERDICT (b), NOT COMMAND-TRACKING. [VERIFIED] ***
    Single write site image-wide (adjudicated scan: 8 raw hits, 6 branch-target coincidences excluded
    with reasons, 1 read @0x4487a, 1 write): `0x42af2 st.w r6,-0x6dac,gp` in FUN_00042adc -- a thin
    sanitizing setter whose ONLY caller is FUN_00027b0a. That function is a MULTI-CHANNEL SENSOR
    REDUNDANCY / PLAUSIBILITY MONITOR over a separate address family (gp-0x61xx/62xx/63xx), scoring
    channel agreement and tripping its own DTC set (0x3d00-0x3d04, 0x3ce6-0x3cff, 0x4157-0x4158). Same
    KIND as the 5-channel torque voter FUN_00041eec, different instance, different channels. Tail:
    gp-0x6dac = clamp(channel-agreement score, +/-10.0). Its inputs NEVER touch gp-0x6acc, gp-0x6b98,
    gp-0x6b94, gp-0x6ad4 or anything downstream of the shaper/governor -- so it cannot depend on V43's
    edit at any hop. This is the (b) branch: an independent diagnostic quantity, additive to a compare
    whose OTHER operand is the command-side term V43 moves.
    (The kit's old "speed-scaled float" label was wrong on the physical description but right on the
    classification; corrected in reference_accord_eme_bit32_float_monitor.md.)
    [OPEN, minor] FUN_00027b0a's ~150 lines of channel arithmetic were not replayed literal-by-literal;
    the classification rests on its structure plus ZERO references to any torque-command address.

    *** THE SUPPORTING ARGUMENTS, WHICH NOW CORROBORATE RATHER THAN CARRY THE VERDICT: ***
    The accumulator (gp-0x6dc8, owned by this watchdog) is
        integral of ( clamp(gp-0x6acc, +/-12) - gp-0x4f60/1024 )
    i.e. COMMANDED torque minus RAW Sensor-B column torque -- read directly, +/-25 sanity only, no
    filtering, untouched by V43. It measures HOW WELL THE PLANT FOLLOWS THE COMMAND.

    Stage C injects fast content the plant CANNOT follow -- that unfollowable content IS the vibration.
    Removing it makes the command MORE followable, so the residual SHRINKS. Quantified against the
    5-count (0.004883) epsilon, for ripple amplitudes 100/300/1000 counts at 20/30/50 Hz: the change is
    2.7x to 100x the epsilon and is a REDUCTION in every single case. The DIRECTION is robust to the
    ripple amplitude (which is an explicit guess, no telemetry exists); only the magnitude is not.

    *** THE EMPIRICAL PROOF-POINT, which outranks all of the above: V38 IS FLASHED AND FAULT-FREE WITH
    THIS LANE FULLY UNFILTERED. V43 only ATTENUATES it. V43 cannot make the command less followable than
    V38's already is. *** A lag also cannot open a new command-vs-sensor gap, because the sensor responds
    to the DELIVERED command -- delay the command and the response delays with it.

    [OPEN, detail-level, does NOT change the conclusion] two tracers disagree on fVar23's exact
    decomposition: gp-0x6dac (@0x4487a) vs gp-0x6dc8 as the persisted term; MIN vs ADD at the combine;
    clamp ceiling 8.0 vs 9.0. They AGREE on the load-bearing structure -- governor cap, a shaper-sibling
    term (gp-0x6b04, whose only two writers are inside FUN_00042af8, the same shaper that produces
    gp-0x6acc/gp-0x6b98), and a persisted accumulator, all compared against delivered within 5 counts.
    Worth reconciling before anyone edits in this region; not worth holding V43 for.

    *** PROCESS NOTE, worth more than the bytes: the sub-agent that ran this trace refused to round
    "2 of 3 inputs traced safe, 1 unlocated" up to a clean verdict, and re-sent its finding when it
    thought the caveat had been lost. The lead had already propagated the premature closure. This kit's
    own record says a verifier and the assertion it checks must not share an assumption -- the same
    failure mode as V40's assert_crc_gap_is_real(). Here the caveat was correct and the summary was not.

    [SOFT DATA POINT on the standing TASK-RATE question] tp+0x74e3's byte-to-float scale is *0.001,
    i.e. the firmware's own float math treats one cycle unit as ~1 ms. Weakly consistent with a 1 kHz
    tick. [INFERRED] -- the first independent-ish evidence for the tick rate this kit has produced, but
    NOT a resolution. Every Hz figure in this model still rests on the unproven 1 kHz assumption.

    ---------------------------------------------------------------------------------------------------
    CHOOSING THE VALUE. Single-pole rolloff is -6 dB/octave past the corner.
    *** Land the edit against the CYCLE-domain column. The Hz column assumes a 1 kHz tick, which this
    kit has NEVER proven -- and specifically has not proven for THIS function's call rate. Illustrative
    only. ***
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
    *** THE V44 TARGET, ROOT-CAUSED. The ratchet is SOLVED (V42 Change 1, on-car). This is the vibration. ***

    *** ROOT CAUSE (2026-07-20): the base-assist VISCOUS DAMPING lane gp-0x6bd0 (FUN_00034350) is a
    product of four Q10 factors, and the factor keyed on voted driver torque gp-0x6a5e (LERP @0xD27BC
    mode 10 / @0xD27D0 mode 11) has Y[0] = 0 at X[0] = 2240. Below 2240 counts of driver torque -- i.e.
    HANDS OFF -- one zero multiplicand kills the whole product, so there is NO damping. The firmware has
    NO notch filter anywhere in the command path (whole-image search: single-pole EMAs only). So hands
    off, the resonance rings undamped; hands on, the damper engages and it vanishes -- the operator's
    exact report. V44 raises Y[0] 0->235 (mode 10) / 0->234 (mode 11), = each table's own Y[1].
    The damper is net-damping at 21 Hz (sign source FUN_00041464 confirmed 1 kHz -> phase -22 deg,
    cos +0.93; even at a 100 Hz producer it is cos +0.55, still dissipative -- see the phase note below).
    ⚠ SCOPE: zero damping was equally true pre-V38 (which did not vibrate), so it is an ENABLING
    condition; V38's 4x authority excites the mode. V44 is a MITIGATION, not a root-cause repair. ***

    ---------------------------------------------------------------------------------------------------
    *** ★★ THE VIBRATION IS MEASURED. Route b9 (V38), 2026-07-20. ***
    First post-V38 driving telemetry in the kit's history. 12 segments, raw CAN 399. Time base
    reconstructed from 399's 2-bit COUNTER (rlog timestamps are batched and unusable); frame rate
    measured 99.99849 Hz (100.000 Hz to ~1.5 ppm). Analysis: analysis-2020accord/rlogs + scratchpad.

    *** IT IS A LIGHTLY-DAMPED MECHANICAL RESONANCE: peak 21.4 Hz, Q = 13.6, -3 dB width 1.58 Hz,
    coherence time ~0.23 s (~4 cycles). *** 60 non-overlapping 5.12 s windows. Confirmed three ways:
    instrumental width is only 18% of the measured width; coherence ~4 cycles; peak-height-vs-window
    slope +0.635 (a coherent line gives 1.0). ⚠ RETRACTED: the earlier "SHARP ISOLATED 21.02 Hz line,
    top-5 bins within 0.09 Hz" was an FFT ARTIFACT of concatenating discontiguous windows -- redone
    properly the top five span 0.94 Hz. Q=13.6 is textbook lightly-damped mechanics; a digital limit
    cycle would be orders of magnitude sharper. The clock-locked / limit-cycle reading is withdrawn, and
    with it the "invariant across speed => clock-derived" inference (the estimates only looked invariant
    because they all sit inside one broad hump). The 1/A rate-limiter model is also falsified (predicts
    13.4 Hz at high amplitude; measured 21.8).

    IT IS A V38 REGRESSION, MEASURED [route b9 vs routes 77/79, the V31P/2x era, 201 s matched]:
        band        V38 power     pre-V38      ratio
        0.5-5  Hz    1131646      3044219      0.37x   <- LOWER on V38 (the quartered PID, as predicted)
        5-10   Hz    1239069       878122      1.41x
        10-20  Hz    1490254       707565      2.11x
        20-30  Hz    2794974        43905     63.66x   <-- ***
        30-40  Hz     100850        11717      8.61x
        40-50  Hz     115255        23783      4.85x
    *** 64x in the peak band. *** And the 0.5-5 Hz band going DOWN is a strong internal control: it is
    exactly what gain-rescaling invariance predicts, and it means the 64x is not a global scale factor.

    THE HANDS-OFF DISCRIMINATOR, SPEED-MATCHED (19-23 Hz band) -- this removes the speed confound that
    made the pre-V38 numbers uninterpretable:
        2-10  mph   hands-off 137668138  assisting   437839   314x
        10-20 mph   hands-off  92378641  assisting   868225   106x
        20-30 mph   hands-off  29087505  assisting   386860    75x
    The operator's key observation is CONFIRMED at 75-314x within the peak band, at matched speed.

    SPEED DEPENDENCE -- a small REFINEMENT of the operator's "speed-independent" report, in their
    favour: the peak is present at every speed but is ~10x STRONGER at low speed (137e6 at 2-10 mph vs
    14.5e6 at 30-45 mph), and its ratio to the 0.5-5 Hz control band falls 21.5x -> 1.0x across that
    range. So it is not purely road-noise masking that makes it audible near 5 mph -- it genuinely is
    strongest there. Consistent with low speed demanding the most motor torque, hence most excitation.
    (n=1 segment in the 2-10 mph bin; treat that bin as indicative.)

    ⚠ CAVEAT -- ALIASING. Sampling is ~100 Hz, so 21.4 Hz is indistinguishable from 78.6 Hz. This does
      NOT weaken a damping fix. (The STABILITY caveat is resolved: the peak is NOT a stable narrow line;
      Q=13.6 and ~0.23 s coherence are exactly what a lightly-damped mechanical mode looks like, so the
      "clock-derived" story is closed, not open.)
    ⚠ THE 2-10 mph BIN IS EMPTY for spectral purposes: 14.5 s of hands-off exists below 10 mph but the
      longest contiguous run is 2.5 s, under one FFT window. Route b9 cannot speak to the regime the
      operator reports as worst. A slow-speed hands-off log is the single highest-value data to collect.

    ---------------------------------------------------------------------------------------------------
    THE OBSERVATION SET  [CONFIRMED -- operator, on-car, after flashing V42]

      1. Vibration occurs when **LKAS ALONE turns the wheel**. Tens of Hz.
      2. It **VANISHES when the driver adds hand torque** to assist the same manoeuvre.
      3. **Speed-independent** -- present at all speeds; audible as "grinding" only near 5 mph, which
         the operator attributes to road-noise masking elsewhere. So audibility is speed-dependent,
         the phenomenon is not.
      4. Present since V38 (4x gain); not reported on V31 (2x) or earlier.
      5. NOT fixed by: r24 zeroed (V39), motor-rate cap flattened (V41), r26 zeroed (V42).

    ---------------------------------------------------------------------------------------------------
    THE THREE CONSTRAINTS, AND WHY THEY ARE HARD TO SATISFY TOGETHER

      C1 (FAST). Tens of Hz. But the LKAS lane is a ~1-5 Hz LOW-PASS (arbitration IIR gp-0x3d3c, pole
         0.96875, tau ~31.5 cycles). A tens-of-Hz component therefore CANNOT BE COMMANDED down the LKAS
         path. Whatever oscillates must be downstream of that IIR, or carried by a signal that does not
         pass through it, or be generated locally (a latch/limit toggling, or the mechanical plant).

      C2 (V38-ONSET). Downstream of the gain, V38 replays stock's exact count sequence for the same
         physical torque -- see gain_rescaling_invariance_analysis(). The ONLY downstream loophole is
         command ABOVE stock's 417-count ceiling. Pure-LKAS turning is exactly that regime, so C2 is
         satisfied by "a downstream limit that stock never reached and V38 now sits against".

      C3 (HANDS-OFF). Something must differ between hands-off and driver-assisting. Known levers:
           - the soft-EME CORRIDOR arm is gated OFF when |gp-0x6bf0| <= cal 0xC6156 (=9216), i.e.
             hands-off. Driver assist switches this arm ON and raises the monitor wall.
           - driver torque enters the base-assist lane, the voters, and several LERP breakpoints.
           - MECHANICALLY: hands on the wheel add mass and damping to a torsion-bar/wheel-inertia mode.

    *** THE STRUCTURE THAT SATISFIES ALL THREE. ***
    Either (a) a DOWNSTREAM LIMIT that V38 sits marginally against, whose binding is modulated by a
    fast input -- a marginally-binding limit with a dynamic input chatters on/off at the input's rate;
    or (b) a MECHANICAL RESONANCE excited by the 4x-larger command and damped by the driver's hands.

    The headroom numbers make (a) concrete and quantitative. NOTE two max-command conventions are in
    circulation in this kit and they give different absolute figures; the RATIO is the robust part:
        using max command = lane + compensation ceiling (this model's computed value):
            V31 (2x): 4762 - 3395 = 1367 counts of headroom
            V38 (4x): 4762 - 4342 =  420 counts of headroom      -> 3.3x reduction
        using the scaling audit's max command = 3584 / 4608:
            V31: 1178 counts     V38: 154 counts                 -> 7.6x reduction
    Either way this is the single largest V31->V38 regression in the kit's own audit, and a margin of
    a few percent against a limit whose other MIN terms are DYNAMIC is the textbook setup for
    intermittent binding. [OPEN] which convention is right -- it decides whether the margin is 3% or
    9%, and therefore how marginal "marginal" actually is.

    ---------------------------------------------------------------------------------------------------
    *** THE DAMPING CONFOUND -- a correction to a recorded elimination. ***

    "Motor torque ripple is RULED OUT" was accepted on the argument: hand steering delivers comparable
    motor torque through the same aggregator/governor/shaper/FOC path and is smooth, so the shared
    output stage is clean at this torque level.

    That argument has a hole. Its comparison case -- hand steering -- ALWAYS has the driver's hands on
    the wheel, which is precisely the damping condition under test in observation (2). The excitation
    could be identical in both cases with only the mechanical Q differing. The elimination is therefore
    NOT clean: it does not distinguish "the output stage is smooth" from "the plant is damped whenever
    we have measured it".

    This does not make motor ripple a firmware fix target. It does mean hypothesis (b) -- a lightly
    damped hands-off torsion-bar/wheel-inertia mode, excited by a 4x larger command and damped by the
    driver's hands -- is NOT excluded by the existing evidence, and it explains observations 1,2,3 and 4
    without requiring any firmware oscillator at all. Under (b) the correct firmware response is to ADD
    damping in the band, not to remove more terms.

    *** NOTE THE DIRECTION-OF-EDIT WARNING THIS IMPLIES. ***
    V39 and V42 both REMOVED torque-rate (derivative) feedback -- r24 and r26. Derivative feedback on
    column torque is a DAMPING term if its sign opposes the rate and an ANTI-damping term if it aids it.
    Both were removed with no observed change, which is weak evidence that neither dominates the damping
    of this mode -- but it also means the kit has twice moved in the "less damping" direction while
    chasing a vibration. V43 should not make a third such edit without a reason that survives (b).

    ---------------------------------------------------------------------------------------------------
    *** THE MECHANISM CLOSED 2026-07-21. Two independent traces converged on the same chain. ***

        gp-0x4f60  RAW Sensor-B (TAS) column torque -- a PHYSICAL sensor, unfiltered
              |
              v    errorterm = clamp( gp-0x4f60 - clamp(gp-0x6ad6, +/-8192), +/-0x2800 )
        FUN_0003a382                 where gp-0x6ad6 (from FUN_00037fe6) is a FEEDFORWARD MODEL of the
              |                      column torque the command lanes predict -- so errorterm is a
              |                      MODEL-vs-REALITY RESIDUAL, recomputed every cycle with no lag
              |      Stage A: "lag" with gain cal 0xC6450 = 1024 Q10  -> PASSTHROUGH (corrected)
              |      Stage B: windowed accumulator, adds L2(=98 flat) * errorterm RAW every cycle
              |      Stage C: RAW one-sample DIFFERENCE of errorterm * L3(=2048 Q10 = 2.0 flat),
              |               then a second "lag" cal 0xC644A = 1024 Q10 -> ALSO PASSTHROUGH
              |               ==> Stage C is a pure DERIVATIVE, i.e. a HIGH-PASS, unattenuated
              v
        gp-0x6ad4 --> aggregator gp-0x6b94   (via the +/-0x2800 zero-type gate; in-window passes whole)
              |
              v
        gp-0x6b94 IS THE GOVERNOR'S SLEW TARGET  [VERIFIED: FUN_0004503c's first instruction @0x453e0
              |                                   is `ld.h -0x6b94[gp],r6`]
              v
        governor slew, whose STEP is DRIVER-TORQUE-GATED via gp-0x67f5:
              512 hands-off (wide band, less damped)  /  205 hands-on (2.5x narrower, more damped)

    *** WHY THIS SURVIVES THE GAIN-RESCALING INVARIANCE ARGUMENT -- the loophole that matters. ***
    The invariance argument says every stage downstream of the gain replays stock's exact COUNTS,
    because the operator quartered openpilot's PID. That is an argument about DIGITAL replay. It does
    not cover a term sourced from a PHYSICAL SENSOR reacting to REAL DELIVERED TORQUE. Motor torque
    ripple (cogging, current ripple, backlash) scales with delivered torque amplitude -- standard PMSM
    behaviour. V38 delivers ~4x the torque for the same manoeuvre, so the REAL ripple on gp-0x4f60 is
    ~4x larger, and this lane passes it essentially unattenuated into the aggregator. Nothing in the
    digital chain was rescaled to compensate, because the amplification happened in the PLANT.
    [INFERRED, physical -- cannot be settled by disassembly; this is the one link in the chain that
    disassembly cannot close, and it should be treated as the weakest.]

    *** THIS VINDICATES THE DAMPING-CONFOUND CORRECTION ABOVE. *** The kit had recorded "motor torque
    ripple is RULED OUT". The ripple is real and physical; what makes it a FIRMWARE problem is that
    this residual lane re-injects it into the torque command. The right conclusion was never "the motor
    is clean" -- it was "the motor's ripple has a path back into the command that nothing filters".

    *** WHY NO PRIOR BUILD TOUCHED IT. *** V39 (r24), V41 (cap table) and V42 (r26) touch none of
    FUN_0003a382, gp-0x6ad4, gp-0x6ad6, 0xC6450, 0xC644A, or the L1/L2/L3 tables. It is the SAME
    physical input family as r24/r26 -- Sensor-B torque -- reaching the aggregator by a completely
    independent, never-tested computational path. That is why falsifying r24 and r26 did not falsify
    the family: we had only tested two of its three routes.

    [OPEN, and it GATES a ZEROING edit] the SIGN of Stage C. A residual-feedback lane with a
    derivative term is classically an active DAMPER. If Stage C opposes column-torque rate it is
    damping a real resonance and zeroing it would make the car worse -- and this kit has already
    removed derivative feedback twice (V39, V42) while chasing this vibration.

    *** THE SIGN QUESTION IS SIDESTEPPED BY THE BETTER EDIT: ADD A POLE, DO NOT ZERO THE TERM. ***
    A raw one-sample difference is an UNBOUNDED DIFFERENTIATOR. Every real controller band-limits one
    with a first-order lag -- the standard "dirty derivative". Stages A and C already HAVE that lag
    structure; cals 0xC6450 and 0xC644A are its gains, and both are pinned at 1024 = Q10 unity, which
    DISABLES the pole. Lowering a gain restores it.

    The EMA is `state += ((target*32 - state) * GAIN) >> 10`, state held at 32x. At GAIN = 1024 the
    state settles at exactly 32*target in ONE cycle. At GAIN < 1024 it settles at the SAME 32*target,
    just over ~1024/GAIN cycles. *** So an EMA has UNITY DC GAIN: lowering the gain cannot change any
    steady-state value, only the time constant. *** [Under verification -- the whole edit rests on it.]

    This is SIGN-AGNOSTIC in the way that matters. Damping or anti-damping, band-limiting the branch
    preserves its low-frequency action and removes only the tens-of-Hz content -- exactly our symptom
    band and nothing else. It is a strictly better edit than zeroing L3, and it is why the [OPEN] sign
    question above does not block V43.

    ---------------------------------------------------------------------------------------------------
    FUN_0003a382 -- FULL COEFFICIENT DUMP AND SAFETY VERDICT [VERIFIED 2026-07-21, byte-level, all
    tables identical in stock / V38 / V42, i.e. NEVER TOUCHED BY ANY BUILD]

        L1  X@0xC6B20/24  Y@0xC6B26/28/2A/2C = 256,256,225,153   Stage A gain, falls with motor rate
        L2  X@0xC6B0C/10  Y@0xC6B12/14/16/18 =  98, 98, 98, 98   Stage B accumulator gain, FLAT
        L3  X@0xC6AE0/E4  Y@0xC6AE6/E8/EA/EC = 2048,...          Stage C DERIVATIVE gain, FLAT = 2.0
        L4  X@0xC67B4/B6  Y@0xC67B8/BA/BC    = 1024,1024,1024    assist-state gain, FLAT unity = no-op
        lag gains: 0xC6450, 0xC644A = 1024 (Q10 unity -> pole DISABLED, see the correction above)

    SIGN -- narrowed, NOT closed [see the honesty note]. Every coefficient above is POSITIVE and NO
    branch inside FUN_0003a382 conditionally negates Stage A/B/C. The only sign-bearing operation in
    the entire function is the final polarity multiply by gp-0x6752. Therefore the raw pre-polarity
    gp-0x6ad4 carries the SAME sign as errorterm (Stages A/B) and as d(errorterm)/dt (Stage C), and it
    is added to gp-0x6b94 with no further flip.
    What is NOT resolved: gp-0x6752's runtime value for A160, and the physical wiring convention
    relating "positive gp-0x4f60" to "positive delivered torque". The second is a HARDWARE fact, not a
    firmware fact -- the same irreducible gap already on record for r24/r26.
    *** BUT THE RISK IS BOUNDED: gp-0x6752 is the SAME byte that scales boost, r24, r26 and every other
    assist lane. There is no lane-specific inversion anywhere in FUN_0003a382. Whatever sign convention
    makes the already-flashed, road-validated assist lanes work is the convention this lane inherits.
    It is not uniquely-signed or specially risky -- its risk is entirely in being UNFILTERED. ***
    (Correction picked up en route: the SM1 check at 0x43680/0x43686, described in an older memory as a
    "driver-torque-opposition detector", actually tests gp-0x6af8, the angular-velocity fight trigger --
    NOT gp-0x4f60. That memory's wording was imprecise and it does not provide a Sensor-B sign anchor.)

    MAGNITUDE [INFERRED -- a plausibility estimate, NOT a measurement; no live telemetry of gp-0x4f60
    or gp-0x6ad4 exists]. errorterm is hard-clamped to +/-10240; Stage C is separately clamped to
    +/-10240 and saturates once |d(errorterm)|/cycle > 5120. For an ASSUMED 300-count ripple at 30 Hz:
    Stage C ~ 113 counts, Stage A ~ 45-75, combined ~150-250 -- roughly 8-14% of V38's 1782-count LKAS
    lane. Not dominant on its own, not negligible, and the derivative's share GROWS with frequency
    while Stage A's does not. The honest position: the errorterm amplitude is unknown and cannot be
    obtained without live logging.

    SAFETY VERDICT FOR A CAL-ONLY EDIT HERE [VERIFIED by exhaustive operand scan, 185,693 instructions]
    gp-0x6ad4 has EXACTLY TWO touches image-wide: the writer `st.h r10,-0x6ad4,gp` @0x3a8a0 and the
    reader `ld.h -0x6ad4,gp,r6` @0x3aca8 (aggregator). No lockstep shadow, no DTC call, no monitor.
    FUN_0003a382 contains ZERO `jarl` instructions -- a pure leaf function -- so nothing inside it can
    invoke a shadow-mismatch fault. The only lockstep in the chain is on the aggregate sum gp-0x6b94
    (shadow gp-0x4ce0), and both mirrors derive from the identical summed register in the identical
    instruction sequence, so a cal-only edit changes both identically and cannot desync them. This is
    the same property every cal-only edit since V29 has relied on.

    *** NEW RISK SURFACED, AND IT IS ALSO A CANDIDATE MECHANISM IN ITS OWN RIGHT. *** The aggregator's
    gate on gp-0x6ad4 is a ZERO-TYPE gate at +/-0x2800 (10240): an out-of-window value contributes
    EXACTLY 0, not a clipped 10240. So a ripple riding on a larger V38-scale term that crosses that
    boundary on peaks makes the whole lane SNAP TO ZERO and back, at the ripple's own rate -- a hard
    nonlinearity and a chatter generator. [OPEN] whether gp-0x6ad4's realistic magnitude approaches
    +/-10240. Note this cuts BOTH ways on edit choice: RAISING L3 (if Stage C turned out to be damping)
    would push peaks toward that boundary and make crossing MORE likely, while adding a pole reduces
    peak excursions and makes crossing LESS likely. It is another reason to prefer the pole.

    ---------------------------------------------------------------------------------------------------
    *** THE DAMPING TERM: FUN_00034350 -> gp-0x6bd0. TWO CORRECTIONS OF RECORD, 2026-07-21. ***

    SIGN [VERIFIED from bytes, not from the label]: `0x3469e cmp r0,r11 / ble 0x346a4 / subr r0,r8`
    negates the product when gp-0x6abe > 0. The product is built from non-negative LERP outputs, so
        term sign = -sign(gp-0x6abe)
    It is TRUE DAMPING -- it opposes the rate -- when it fires.

    CORRECTION 1 -- IT IS LIVE IN NORMAL DRIVING, NOT DEAD. A standing agent-memory note had the
    producer's branch polarity SWAPPED. Traced in FUN_00041464: for |gp-0x4f50| within ~13000 (i.e.
    NORMAL driving) the code takes 0x4169c and stores a LIVE lightly-filtered resolver rate
    (gain cal 0xC643C = 37, Q7) at `0x417a0 st.h r24,-0x6abe[gp]`. Only for ABNORMAL/saturating rate
    does 0x41902 pin gp-0x6abe = 0x7fff, which then trips this function's own magnitude gate and
    zeroes the damper. The old note had it backwards. Verified twice -- decompile and raw disassembly
    register-tracing -- before being reported, because it reverses the term's whole behavioural story.

    CORRECTION 2 -- NEW FINDING: A ONE-SIDED GATE HALVES THE DAMPER'S COVERAGE.
        0x345fa  ld.hu -0x6ac0[gp],r14      <-- UNSIGNED load of a SIGNED quantity
        0x345fe  addi -0x32c9,r14,r0
        0x34602  bc 0x34612                 <-- zero the whole term if r14 >= 12999 unsigned
    gp-0x6ac0 is signed, clamped +/-13000. Read unsigned, every NEGATIVE value becomes a huge unsigned
    number >= 12999, so *** the damping term is unconditionally ZERO for one rotation direction. ***
    This is the same signed-value-via-unsigned-compare footgun already recorded at the shaper's
    one-sided +/-8192 gate -- same idiom, new location.

    WHY THIS MATTERS FOR A LIMIT CYCLE: during a tens-of-Hz oscillation the motor rate gp-0x6ac0
    ALTERNATES SIGN every half cycle. So this is a HALF-WAVE-RECTIFIED DAMPER -- present on one half
    cycle, absent on the other. It delivers half the damping it appears to, and the on/off switching
    is itself a nonlinearity at the oscillation frequency. [INFERRED] as a sustaining mechanism.

    BUT -- the damper measures MOTOR RESOLVER RATE (gp-0x6abe and gp-0x6ac0 both derive from
    gp-0x4f50), i.e. the MOTOR side of the torsion bar. Under the hands-off wheel-inertia model the
    resonant mode is on the WHEEL side. A motor-side damper may not reach a wheel-side mode at any
    gain. Both things are true at once: the term is live and correctly signed, AND it may be measuring
    the wrong side. This tempers the "we have been detuning the damper" concern for THIS term -- it
    was already asymmetric and half-blind by construction, independent of anything V39/V42 did.

    *** NOT SHIPPING A FIX FOR THE ONE-SIDED GATE IN V43. *** It is a code-level ld.hu/ld.h asymmetry,
    and correcting it would make a term active in a rotation direction where it has NEVER been active
    in ANY build including stock. That is novel-behaviour territory. This kit's rule -- the one that
    made V42's branch flip safe -- is that a change should WIDEN AN ALREADY-LIVE PATH, not invent one.
    Recorded as a characterised asymmetry for a later, separately-scored build.

    ---------------------------------------------------------------------------------------------------
    *** SECONDARY V43 CANDIDATE 2026-07-21: THE GOVERNOR SLEW-STEP SELECTOR (gp-0x67f5). ***
    See governor_step_selector_bandwidth() for the full mechanism and arithmetic.

    The governor's per-cycle slew STEP is switched by DRIVER COLUMN TORQUE (vote of gp-0x6a5e vs cal
    0xC531E = 1062, debounced 10 cycles by cal 0xC64E7):
        hands OFF -> STEP 512 (cal 0xC6206), wide bandwidth, less damped
        hands ON  -> STEP 205 (cal 0xC6208), 2.5x narrower, more damped
    At 30 Hz the fast step passes ripple up to ~2716 counts; the slow step clips it to ~1088. So the
    command path carries ~2.5x more tens-of-Hz content with hands off -- and the switch is thrown by
    exactly the variable the operator's observation turns on.

    This satisfies all three constraints: C1 (a rate limit acts squarely in the tens-of-Hz band at
    these amplitudes), C3 (the gate IS driver torque, byte-verified), and -- the part worth dwelling
    on -- C2:

        the rate-limit corner scales as 1/amplitude:  f_corner = STEP * tick / (2*pi*A)

        pure-LKAS hands-off governor target, STOCK (LKAS lane 417):    ~195 Hz
        pure-LKAS hands-off governor target, V38   (LKAS lane 1782):    ~46 Hz

    On stock this limiter sits at ~195 Hz -- far above anything audible or feelable, so it never binds
    in the symptom band. V38's 4.27x larger LKAS lane drags the corner down BY THE SAME FACTOR, to
    ~46 Hz, which is inside "tens of Hz". *** V38 is the first build in the lineage where this rate
    limiter binds in the symptom band at all. *** That is a retrodiction of the V38 onset from an
    independent mechanism, not a fitted parameter.

    (Amplitude caveat, stated because it moves the number: the post-governor COMPENSATION term, up to
    2560 counts, is added AFTER this limiter, so the governor's own target is the LKAS lane plus base
    assist, not the 4342/4608 whole-command figure. Using 4342 instead gives ~19 Hz. Both are inside
    the band; ~46 Hz is the defensible figure for the pure-LKAS hands-off case this symptom occurs in.)

    PROPOSED V43 EDIT: cal 0xC6206  512 -> 205. One halfword, cal-only, ONE reader image-wide.
    Why this is the safe direction and a safe magnitude, unlike V40:
      * V40 wrote 0xFFFF here and REMOVED rate limiting -> snap-to-target -> motor-off. This edit moves
        the OPPOSITE way: strictly MORE rate limiting.
      * The resulting behaviour is not novel -- it is exactly what the car already does every time the
        driver holds the wheel, which is the condition the operator reports as SMOOTH.
      * The slow step is the selector's RESET/default state, i.e. the conservative side of the switch.
      * V42's monitor-safety proof survives unchanged: in the away-from-zero branches a smaller STEP
        only brings the output closer to HELD, so |output| <= |TARGET| with matching signs still holds
        for any STEP; the toward-zero branches snap to TARGET regardless of STEP. FUN_0004595a's two
        fault conditions therefore remain unreachable.
      * Cost: LKAS reaches full command in ~22 cycles instead of ~9 (~22 ms vs ~9 ms if the tick is
        1 kHz), well inside openpilot's 100 ms steerActuatorDelay. Drivability risk is a slightly
        softer initial bite hands-off; flag it to the operator rather than assuming it is nil.

    *** HONESTY GATE: this is [INFERRED] as a CAUSE. It is a verified TRANSMISSION PATH gated by the
    right variable, but no fast-fluctuating target has been found feeding it. If nothing oscillates in
    that band, this edit changes nothing -- exactly as happened with r24 (V39), the rate cap (V41) and
    r26 (V42). What makes it worth shipping anyway is that it is the first candidate whose gating
    condition matches the operator's discriminator IN THE BYTES rather than by analogy. ***

    ---------------------------------------------------------------------------------------------------
    *** CANDIDATE ELIMINATED 2026-07-21: THE ENERGY / THERMAL BUDGET TERM. ***
    [VERIFIED -- provably unreachable, not merely untriggered]
    A genuine hysteretic accumulator exists (fStack_48/gp+0x300, latch gp-0x285f), charged when
    gp-0x6ba4 > cal 0xC509E. But gp-0x6ba4 is |DELIVERED TORQUE| (written at shaper 0x43c0c, right
    after the final +/-0x2000 clamp), the threshold is 5325 counts, and delivered torque is
    structurally bounded by the governor ceiling cal 0xC6202 = 4762 < 5325. It cannot fire at ANY
    steady-state command, on V38 (~4342) or stock (~417). Its hysteresis band is separately collapsed
    to a same-cycle comparator by cal 0xC5164 = 0. The only lever that could wake it is raising
    0xC6202 past 5325 -- independently rejected by the governor-raise audit. Dead.
    The SEPARATE current-based term (fVar54/gp+0x13c, a 32-sample rolling average x cal 0xC5638) has
    no latch: it is a plain moving average, i.e. another low-pass, not an oscillator candidate.

    *** RELABEL, 2026-07-21: "GOVERNOR G1" (FUN_0004503c, this function) is a MOTOR-RATE-ADAPTIVE
    TOTAL-COMMAND CEILING, not thermal protection. *** Two independent findings retire the "thermal"
    framing: (1) instruction-level tracing confirms it clamps gp-0x6b94, the AGGREGATOR's output --
    i.e. the TOTAL of LKAS plus every base-assist lane, not an LKAS-only path (see
    motor_torque_demand_aggregator()'s "every base-assist lane joins LKAS in gp-0x6b94 before the
    first governor" note -- this function IS that first governor); (2) the one genuine hysteretic
    accumulator that would justify a thermal label (immediately above) is structurally unreachable, so
    what remains is a pure rate-scheduled ceiling, not a charge/discharge thermal model. It also does
    NOT bind at the resonance's own amplitude: the measured vibration sits at roughly 139 counts
    peak-to-peak on the aggregated command, far below every tier of this governor's floor (512 at its
    steepest taper) -- so G1 is not a candidate suppressor OR aggravator of the ~21 Hz mode at this
    amplitude, consistent with rate_cap_binding_analysis() only implicating it at LKAS-scale (>=512
    count) demands.

    ---------------------------------------------------------------------------------------------------
    *** CANDIDATE ELIMINATED 2026-07-21: THE SOFT-EME WALL / BOOST-LATCH RELAXATION OSCILLATOR. ***
    [VERIFIED -- fresh byte reads of V31/V38/V42 images + fresh decompile of stock FUN_00042af8]

    This was the leading structural candidate entering the session, because hands-off is exactly the
    condition that gates the CORRIDOR arm off (cal 0xC6156 = 9216), so the wall visibly collapses in
    precisely the regime that vibrates. It is dead on the numbers:

        hands-off wall (V38/V42) = max(corridor=0, IIR>=0, boost floor=5120) >= 5120 unconditionally
        max LKAS-alone hands-off command                                     = 4342 .. 4608
        margin                                                              = 512 .. 778 counts

    The wall never binds, so the integrator never winds, so authority never rises above 0, so the
    boost latch (needs authority > 16384 sustained 20 cycles) CANNOT BOOTSTRAP. There is no path into
    the oscillator under LKAS-alone on V38/V42. The mechanism is real, correctly characterised, and
    dormant here. Lineage check that corroborates the arithmetic: stock's boost arm is a genuine
    angular-rate LERP with Y0 = 0, so stock's bound really could sit near zero hands-off and V9's
    417-count command bound easily -- which IS the historically confirmed pre-V31 soft EME. V31's flat
    4096 floor vs ~3395 command gave a 701-count margin and fixed it. The story is self-consistent.

    TWO THINGS WORTH KEEPING FROM THIS TRACE, both newly established rather than re-quoted:
      * The wall is ON THE LIVE TORQUE PATH, not monitor-only: state_scale = min(sm2,sm3) multiplies
        into the shaper term, which reaches gp-0x6b98 (the FOC demand) via the second governor clamp
        and the final +/-0x2000 clamp. So an SM3 trip genuinely zeroes delivered torque. Distinct from
        FUN_00043e44, which only cross-checks int-vs-float and raises a DTC on divergence.
      * [OPEN, the one door left here] the elimination is proven for LKAS-ALONE. If base assist can
        stack with LKAS while |gp-0x6bf0| still reads under the 9216 corridor gate (residual grip
        rather than hands fully off), the aggregate could exceed 5120. NOT established as reachable.
        Note it also predicts the WRONG DIRECTION for our symptom -- stacking needs some driver input,
        yet the operator reports driver input REMOVES the vibration -- so it is a low-priority door.

    ADDRESS TRAP recorded so it is not repeated: the shaper's corridor cal is tp+0x774e = **0xC674E**
    (not 0xC774E) and the boost cal is tp+0x7768 = **0xC6768**. A dispatch in this session mis-added
    the tp base and sent 0xC774E/0xC7760; the trace caught it. tp = 0xBF000, so tp+0x7NNN = 0xC6NNN
    or 0xC7NNN depending on the digit -- add, do not concatenate.
    ---------------------------------------------------------------------------------------------------

    CONFIDENCE : [CONFIRMED] observations 1-5.
                 [VERIFIED]  the IIR low-pass, the 0xC6156 corridor gate, the governor headroom figures,
                             and the soft-EME wall elimination above.
                 [INFERRED]  the (a)/(b) partition, and that these are the only two structures that fit.
                 [OPEN]      which of (a) or (b) it is. Distinguishing them is V43's design problem, and
                             an rlog spectral comparison of hands-off vs hands-on segments would settle
                             it without a build.
    ---------------------------------------------------------------------------------------------------
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
        "leading_candidate": {
            "name": "base-assist DAMPING lane FUN_00034350 -> gp-0x6bd0, BOTH hands-off deadzones "
                     "(Factor C driver-torque LERP Y[0], Factor E motor-rate LERP Y[0])",
            "edit": "V44 opened only Factor C (0xD27C6/0xD27DA 0->235/234); V47 additionally raises "
                    "Factor E's low breakpoints (0xD2802/04/06 mode 10, 0xD2816/18/1A mode 11 -> "
                    "700/750/800) so the damper is live at low motor rate too, not just high driver "
                    "torque -- see assist_shaping_lanes()'s FUN_00034350 factor breakdown",
            "status": "[VERIFIED] both deadzones + table contents; [INFERRED] as sufficient cause; "
                      "V47 BUILT + verified, UNFLASHED (current candidate, 2026-07-21)",
            "see": "assist_shaping_lanes()",
        },
        "elimination_downgraded": "motor torque ripple -- the damping confound, see docstring",
    }


def arb_deadband_relative_width(cal: Calibration, op_pid_scale: float = 0.25,
                                deadband_ivar34: int = 102) -> dict:
    """
    *** THE PRE-GAIN DEADBAND -- found 2026-07-20 exactly where gain_rescaling_invariance_analysis()
    predicted the vibration mechanism would be. Leading FIRMWARE candidate. ***

    ---------------------------------------------------------------------------------------------------
    THE STRUCTURE  [VERIFIED at raw-instruction level, FUN_00028ea6, block 0x2a1ae-0x2a206]

    Inside the arbitration core, BEFORE the polarity x GAIN multiply (@0x2a1f6/0x2a1fe), there is a
    deadband + sign-consistency gate on the IIR output iVar34:

        if (cal 0xC64A3 == 1  &&  gp-0x6806 == 0) {          # both must hold, else block is SKIPPED
            if (|iVar34| <= L)                    iVar34 = 0     # flat deadband
            else if (sign(iVar34) != sign(gp-0x6b30_prev)
                     || gp-0x6b30_prev == 0)      iVar34 = 0     # sign-consistency rule
        }
        iVar34 = (iVar34 * ramp_gain gp-0x69b0) >> 15
        st.h iVar34 -> gp-0x6b30                                  # @0x2a206, feeds next cycle's test

    Cals, freshly read from stock:
        L      = cal 0xC61B8 (tp+0x71b8) = 102
                 *** MIXED SIGNEDNESS TRAP: read `ld.h` SIGNED @0x2a1be and `ld.hu` UNSIGNED @0x2a1ca.
                 Any edit must stay in 0..32767 to behave identically under both reads. ***
        ENABLE = cal 0xC64A3 (tp+0x74a3) = 1, single byte, `ld.bu`, SOLE READER image-wide
    gp-0x6b30 has exactly 2 references image-wide, both inside this gate (read 0x2a1d4, write 0x2a206).

    Upstream state, and a long-standing disambiguation SETTLED:
        gp-0x3d3c  = a 32-bit one-pole IIR accumulator, updated UNCONDITIONALLY every cycle
                     (cal 0xC63EC = 992 on the old state, cal 0xC63EE = 507 on the new term, both Q10);
                     iVar34 = gp-0x3d3c >> 5.
        gp-0x69b0  = a SEPARATE 0..0x8000 Q15 ramp-gain driven by its own 8-state SM (gp-0x3d38).
    *** Two prior descriptions of "an integrator before the gain" DISAGREED. Both were half right:
    they were describing these TWO DIFFERENT REAL VARIABLES. gp-0x3d3c is a filter, gp-0x69b0 is a
    smooth fade-in gain. NEITHER is a torque-error integrator that winds up. ***

    ---------------------------------------------------------------------------------------------------
    WHY THIS IS A V38 REGRESSION -- and it is the invariance argument's own prediction coming true

    L = 102 is a FIXED ABSOLUTE threshold in the PRE-GAIN domain. With openpilot's PID quartered to
    compensate the 4x gain, the pre-gain domain operates 4x CLOSER TO ZERO for the same physical
    torque. The deadband did not move; the signal shrank into it. So the flat band occupies ~4x more
    of the working range than it did on stock, and small low-speed commands that used to sit well
    clear of it now dither in and out of it -- forced to zero on one cycle, passed on the next.
    That is a chatter generator, it is specific to near-zero command, and it needs openpilot engaged.

    *** CONTRADICTION -- MUST BE RESOLVED BEFORE ACTING. [OPEN] ***
    Taken literally the sign rule SELF-LATCHES: once the gate stores 0, the next cycle's test is
    0 * x = 0, which fails `bgt`, forcing 0 again -- permanently. The car's LKAS works, so exactly one
    of these holds, and which one decides whether this is our bug:
        (A) gp-0x6806 != 0 in normal driving  -> block bypassed, gate INERT, 0xC64A3 edit is a NO-OP.
        (B) the self-latch reading is wrong   -> pure deadband + sign rule -> LEADING candidate.
        (C) gp-0x6806 toggles periodically    -> latch heals on a cadence -> a RELAXATION OSCILLATOR
                                                 whose period IS the grinding, not merely permits it.
    Being chased via a scoped pcode read of 0x2a1a0-0x2a206 plus a trace of the gp-0x3d38 SM.

    MITIGATION (pending the above): cal 0xC64A3 -> 0x00. Single unsigned byte, sole reader image-wide,
    and it does NOT invent a code path -- it forces the `bne 0x2a1e6` branch that ALREADY executes
    routinely whenever gp-0x6806 != 0 (every re-engage ramp). Second option, narrower: 0xC61B8 -> 0,
    which removes the flat band but keeps the sign rule.

    CLEAN NEGATIVE from the same pass: the polarity byte gp-0x6752 is NOT a live sign. It is a static
    per-variant config constant parsed once at boot (FUN_00048a40 record type 0x54, shadow gp-0x4c2d),
    re-validated only for memory integrity, taking only {0, +1, -1}. It cannot chatter. The
    "bare unhysteretic sign multiplier near zero" hypothesis is REFUTED. [VERIFIED]

    *** (A)/(B)/(C) RESOLVED 2026-07-20 -- and the gate is INERT in steady driving. ***
    The gate is enabled only while cal 0xC64A3 == 1 AND gp-0x6806 == 0. gp-0x6806 is driven by the
    9-state LKAS engage-ramp SM (state gp-0x3d38, gain gp-0x69b0):
      - state 2 (steady hold): gp-0x6806 retains the 1 set at ramp saturation => GATE SKIPPED.
      - the SM drops gp-0x6806 to 0 whenever STEER_STATUS gp-0x6807 visits {3,4,7}, then holds it at
        0 through a fast ramp-DOWN (cal 0xC63F4=328/cyc) and the whole subsequent ramp-UP
        (cal 0xC63F8=33/cyc in mode 0 -> 0x8000/33 ~= 993 CYCLES; cal 0xC63FC=328/cyc in mode 2).
    So the gate is live only during engage ramps, not during steady engaged driving. [VERIFIED]

    *** STEER_STATUS 4 AND 7 ARE UNREACHABLE ON V37/V38's CAL SET. [VERIFIED] ***
    gp-0x6807 has exactly two writer sets: FUN_00028ea6 (live) and FUN_0002a30e (dead, 0 callers).
    The =4 trip is a strict `cal < operand` OR-chain, but the torque channel gp-0x682f is explicitly
    saturated to 254 and the rate term's ceiling is 25600>>5 = 800 -- against cals raised to 0xFF /
    0xFFFF, every term is permanently false. The =7 path needs the DTC-0x49 counter gp-0x6758 to
    saturate, and its only entry increments are gated by 0xC64B8(=0xFF) < 254 -- so the counter never
    leaves 0 and a third, apparently-unconditional increment site is unreachable because it sits
    downstream of the counter having already climbed. Both dead.

    *** THEREFORE STEER_STATUS==3 IS THE ONLY SURVIVING TRIGGER -- AND IT IS THE LOW-SPEED LOCKOUT. ***
    [CONFIRMED from 98,053 raw CAN-399 frames across 18 rlogs, analysis-2020accord/_ss_vs_speed.py]
        0-1 mph  100.0% ST=3      3-4 mph   8.9% ST=3   <- release boundary
        1-2 mph  100.0% ST=3      4-5 mph   0.0% ST=3
        2-3 mph   99.6% ST=3      5+  mph   0.0% ST=3
    ST=3 releases at ~3 mph, exactly openpilot's minSteerSpeed / STEER_GLOBAL_MIN_SPEED. Only 11
    0->3 and 8 3->0 transitions across all logs, so it is a SUSTAINED state, not a chatter source.

    CONSEQUENCE FOR THE ~5 MPH VIBRATION -- TWO DIFFERENT ANSWERS, AND THE OPERATOR DECIDES WHICH:
      * SUSTAINED vibration at a steady 5 mph  -> ST=0 there, gate inert, cal 0xC64A3=0 is a NO-OP.
                                                  This candidate is DEAD; do not ship it.
      * TRANSIENT vibration just after pulling away -> crossing ~3 mph releases ST=3, which RESTARTS
        the ramp and holds gp-0x6806 at 0 for the FULL ~993-cycle mode-0 ramp-up. The gate is LIVE
        for that entire window, which lands squarely in the 4-6 mph range a few seconds after a stop.
        Under this reading the candidate is very much alive, and the 4x-narrowed effective range
        (below) is what makes it newly perceptible on V38.

    CONFIDENCE : [VERIFIED] the gate structure, both cal values, the IIR coefficients, the polarity
                            negative, the gp-0x3d3c / gp-0x69b0 disambiguation, the ramp SM, and the
                            unreachability of ST=4/7 on V38.
                 [CONFIRMED] the ST=3 / speed correlation (on-car rlog data, 98k frames).
                 [OPEN]     whether the felt vibration is sustained or transient-after-pullaway -- the
                            single question that decides this candidate.
                 [OPEN]     the CAN-domain equivalent of L=102. The IIR's steady-state fixed point is
                            iVar34 ~= raw_term (S* = (992*S* + 507*T)>>10 -> S* ~= 15.8*T, then
                            iVar34 = 2*S*/32 ~= 0.99*T), so the threshold applies at ~1:1 to whatever
                            the LERP cascade emits -- but that cascade's gain vs gp-0x69ae is NOT
                            traced. The relative-width number below is ILLUSTRATIVE, not measured.
    ---------------------------------------------------------------------------------------------------
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
    *** ❌ HYPOTHESIS DEAD (2026-07-20). NO LIMIT CYCLE IS POSSIBLE HERE -- PROVEN, NOT JUST UNOBSERVED.
    *** But this trace produced the session's most useful STRUCTURAL constraint. Read the LOW-PASS
    *** section below before proposing any vibration mechanism anywhere in the LKAS lane.

    THE EXACT RECURRENCE [VERIFIED byte-level, FUN_00028ea6 @0x2a174-0x2a1b0]:
        term1[n] = floor(507 * x[n]   / 1024)     cal 0xC63EE, `ld.hu` @0x2a174
        term2[n] = floor(992 * s[n-1] / 1024)     cal 0xC63EC, `ld.h` SIGNED @0x2a184
        s[n]     = term1[n] + term2[n]            -> stored to gp-0x3d3c @0x2a1b0
        out[n]   = floor((s[n-1] + s[n]) / 32)    -> iVar34, the LKAS command carried onward
      x[n] is the LERP-cascade result, clamped +/-15360 (cal 0xC61BE) upstream @0x2a13e-0x2a162.
      All three shifts are `sar` (arithmetic/floor). NO rounding term is added before any of them.
      gp-0x3d3c is EXCLUSIVELY owned by this recurrence: exactly one ld.w and one st.w image-wide.
      ⚠ CAL CORRECTION: an earlier draft cited tp+0x73e8 (0xC63E8). That is a DIFFERENT cal (=923) and
      is not read here. The recurrence reads 0xC63EC and 0xC63EE only.
      ⚠ SIGNEDNESS TRAP: 0xC63EC is loaded `ld.h` SIGNED. Inert at 992, but raising it to >= 0x8000
      would read NEGATIVE and flip the pole sign -- the one change that COULD create real
      sign-alternating oscillation. A reason to leave it alone, not a lever.

    WHY NO LIMIT CYCLE IS POSSIBLE [VERIFIED -- structural proof, not a value-specific result]:
    For constant input the state recursion collapses to the affine 1-D map s[n] = K + floor(a*s[n-1])
    with a = 992/1024 = 0.96875. `floor(a*s)` with 0 < a < 1 is MONOTONE NON-DECREASING in integer s,
    and a < 1 forbids overshoot past the fixed point. A monotone bounded sequence cannot have a
    periodic orbit of period > 1 -- it must land on an exact integer fixed point and stay. The classic
    granularity limit cycle needs either a NEGATIVE pole or round-to-nearest with sign-dependent bias;
    neither is present. Simulation across 20+ scenarios agrees, including adversarial +/-1 LSB input
    dither: the internal state does enter a period-2 orbit (68768<->68769) but the `>>5` output is
    CONSTANT, because a swing of 1 in the state cannot move a >>5 result.

    *** ★★ THE REAL FINDING: THE ENTIRE LKAS COMMAND LANE IS LOW-PASSED AT ROUGHLY 1-5 Hz. ***
    Pole 0.96875 => tau = -1/ln(a) = 31.5 CYCLES, with ~unity DC gain (state ~15.84x the input, then
    the >>5 output stage brings it back to ~0.99x). At any plausible loop period (1-10 ms) that is a
    corner frequency of about 0.5-5 Hz. A tens-of-Hz component arriving at x[n] is attenuated ~12-30 dB.

    CONSEQUENCE, and it is sweeping: **a tens-of-Hz vibration CANNOT be COMMANDED through the LKAS
    lane.** Everything upstream of this filter -- the CAN intake, the setpoint, the setpoint-limit LERP,
    the whole LERP cascade, and openpilot's own command dynamics including STEER_DELTA -- is band-
    limited to a few Hz before it ever reaches the gain. So no upstream-of-IIR mechanism can produce a
    fast vibration, and this stage is actively SMOOTHING such a component rather than creating one.
    That eliminates an entire half of the search space in one stroke, and it materially WEAKENS the
    openpilot STEER_DELTA hypothesis for a FAST symptom (it remains viable only for a several-Hz one).

    *** THE DEAD-BAND / STICK-SLIP VARIANT IS ALSO DEAD [VERIFIED by enumeration + simulation]. ***
    A second pass tested the likelier variant (positive pole => dead band, not free-running):
      - Static dead band enumerated over X = 0..2200: 1089 distinct output plateaus, width min 1 /
        max 5 / MEAN 2.02 X-units. That is just 1024/507 = 2.02, i.e. the ORDINARY input quantisation
        of term1 -- not a pathological recursive artifact.
      - ⚠ MY OWN ARITHMETIC WAS WRONG, and in the conservative direction. The naive LSB/(1-pole) = 32
        applies to the raw STATE s, not to what reaches the gain. `iVar34 = (s[n-1]+s[n]) >> 5` is a
        TWO-SAMPLE ROLLING AVERAGE, which RECOVERS almost all the resolution the state-domain floor
        discards. So the `>>5` makes iVar34 FINER than estimated, not coarser -- the opposite of the
        rescue I was hoping for.
      - Ramp sweep 0.25 -> 25 X-units/cycle: step sizes track instantaneous slope, dwell never exceeds
        ~4-5 cycles at the slowest rate and is 1 cycle at rates >= 2. NO multi-cycle freeze followed by
        a catch-up jump anywhere. Indistinguishable from plain 1-LSB quantisation; a round-to-nearest
        filter would look materially the same. Sinusoids (periods 60-500 cyc, amp 20-2000) agree.
      - AT THE MOTOR: an iVar34 step of 1 or 2 yields ZERO counts at gp-0x6b3c on BOTH builds
        (stock needs S>=37 to register 1 count, V38 needs S>=10). Even the most aggressive ramp tested
        (25 X/cycle) gives 0 counts stock / 2 counts V38 = 0.046% of the 4342 lane. To reach a
        marginally perceptible 10 counts on V38 would require a sustained ~92/cycle iVar34 step, i.e. a
        near-discontinuous setpoint jump EVERY control cycle -- not a hand turn.

    *** THE UPSTREAM-LERP DOOR IS CLOSED ANALYTICALLY -- no further trace needed for a FAST symptom. ***
    The tracer flagged one unclosed possibility: that the divq-based LERP cascade feeding x[n]
    (@0x2a090-0x2a172, clamped +/-cal 0xC61BE = 15360) carries its own coarse quantisation, which this
    nearly-transparent dead band would pass through. That reasoning conflates QUANTISATION with
    FREQUENCY RESPONSE. The dead band being ~2 wide says the filter is transparent in AMPLITUDE; it
    says nothing about time. A step at x[n] entering a one-pole low-pass with tau = 31.5 cycles emerges
    as a SMOOTH EXPONENTIAL over ~31 cycles, not as a step. So even a coarsely quantised upstream
    signal arrives at the gain as low-frequency stepping (a few Hz at most), never as a tens-of-Hz
    edge. Door (b) cannot produce a fast vibration. [INFERRED from the verified pole; standard
    first-order response, no ringing is possible with a single positive real pole.]

    WHAT SURVIVES: a fast vibration must arise DOWNSTREAM of this IIR and still be LKAS-conditional.
    The standout is the r26 adaptive Sensor-B torque-rate lane in the aggregator -- a DERIVATIVE (i.e.
    HIGH-pass) of driver column torque, so it passes exactly the band this filter blocks; no deadzone
    (unlike r24, which carries +/-3 via cal 0xC61F6 -- why V39's r24 kill was a no-op near zero);
    never tested on-car; and it closes a loop through the mechanical plant. See _inline_torque_rate_a().
    ---------------------------------------------------------------------------------------------------
    HISTORICAL: the original hypothesis and its provisional numbers follow, retained because the
    reasoning pattern (an absolute, non-scaling quantity upstream of a raised gain) is sound and will
    apply again -- it simply is not instantiated here.

    ---------------------------------------------------------------------------------------------------
    WHY THE SEARCH LANDED HERE

    Two independent arguments converge on the LKAS-only segment upstream of the aggregator:
      (1) UNITS -- gain_rescaling_invariance_analysis(): with the PID quartered, every stage downstream
          of the gain replays stock's exact counts, so a symptom inside stock's torque range cannot
          originate there.
      (2) EMPIRICAL (operator, accepted) -- hand steering delivers comparable or greater motor torque
          through the same shared downstream path with NO vibration, so the motor and that whole stage
          are clean at this torque level. MOTOR TORQUE RIPPLE IS RULED OUT.

    The only stateful, LKAS-specific element in what remains is the one-pole IIR at gp-0x3d3c inside
    the arbitration core FUN_00028ea6 (@0x2a194-0x2a1b0): a multiply, TWO truncating `sar 0xa` shifts,
    an accumulator, then `sar 0x5` producing iVar34. Reported pole ~992/1024 = 0.96875.

    ---------------------------------------------------------------------------------------------------
    THE MECHANISM, AND WHY IT SURVIVES THE PID RESCALE

    A fixed-point recursive filter with a near-unity POSITIVE pole and truncating shifts does not
    settle cleanly. It has a DEAD BAND roughly LSB/(1-pole) wide -- a contiguous set of fixed points
    around the input inside which the truncation eats the increment and the output stops moving. With
    a static input the output sits still; with a CHANGING input it sticks, then jumps: stick-slip in
    the low bits. (A free-running limit cycle is the other variant, but it needs a negative pole and
    is less likely here.)

    *** THE LOAD-BEARING POINT: this IIR sits UPSTREAM of the 4x gain cal 0xC646C. ***
    The dead-band step is an ABSOLUTE quantity in iVar34 counts, fixed by the LSB and the pole. It does
    NOT scale with signal level. So:
      - V38 multiplies it by GAIN/32768 = 3564/32768, four times what stock's 891/32768 did;
      - and QUARTERING THE PID CANNOT COMPENSATE IT, because the quantity is not proportional to the
        command. The operator applied the correct linear compensation and the vibration persisted --
        which is exactly what a non-scaling upstream quantisation would predict, and is the single
        strongest reason to suspect this class of mechanism.

    IT ALSO MATCHES THE "WHEEL MUST BE TURNING" CONSTRAINT. Stick-slip needs a CHANGING input. A
    free-running oscillation would buzz with a static command and a static wheel; the operator reports
    it does not. Dead-band behaviour appears only while the command is moving -- i.e. while steering.

    ---------------------------------------------------------------------------------------------------
    THE TEST THIS HYPOTHESIS MUST PASS, AND WHERE IT MAY DIE

    Stock carries the identical IIR and did not vibrate perceptibly, so the explanation must be that
    the step was always present and stock's 891 gain kept it below the perception floor. That is
    arithmetically consistent -- but a rough estimate (dead band ~32 iVar34 LSBs) maps to only ~3.5
    counts at gp-0x6b3c on V38 versus ~0.9 on stock: a real 4x regression, but only ~0.2% of the
    1782-count full scale, which may be far too small to feel through the rim.
    *** If the simulated step size stays a fraction of a percent of full scale, THIS HYPOTHESIS DIES. ***
    Two things could rescue it and are being checked: whether the `>>5` makes the effective motor-side
    LSB much coarser than assumed, and whether the LERP cascade feeding the filter carries its own
    coarser quantisation that dominates.

    CONFIDENCE : [VERIFIED] the IIR exists, is LKAS-specific, is stateful, truncates, and sits upstream
                            of the gain; and that ripple + the shared downstream path are excluded.
                 [OPEN]     the exact cal set (a reported 0xC63EC/0xC63EE conflicts with a disassembled
                            read of tp+0x73e8 = 0xC63E8), the true pole, the dead-band width, and
                            whether the motor-side magnitude is perceptible. All being simulated.
    ---------------------------------------------------------------------------------------------------
    """
    stock = Calibration.for_build("V9")
    pole = pole_q10 / 1024.0
    band = deadband_lsb if deadband_lsb is not None else round(1.0 / (1.0 - pole))

    def at_motor(gain):
        return band * (ramp_gain_q15 / 0x8000) * gain / 32768.0

    # *** UNITS TRAP -- DO NOT MEASURE THIS AGAINST FULL SCALE. ***
    # An earlier draft reported the step as a % of the build's own full scale and got ~0.2% for BOTH
    # stock and V38, making the regression vanish. That denominator is wrong: V38's full scale is
    # itself 4x stock's, so dividing by it cancels the very effect being measured. This is the same
    # class of error as the retracted "~15360" authority-vs-setpoint conflation in the V31->V38 audit.
    #
    # The correct denominator is a FIXED PHYSICAL TORQUE. With the PID quartered, the same physical
    # torque is the same LANE COUNT in both builds -- so hold the reference fixed at stock's own
    # full-scale command (417 counts) and compare absolute motor-side step against it.
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
    *** THE HOLE IN gain_rescaling_invariance_analysis(), AND THE LEADING VIBRATION CANDIDATE. ***
    *** It is NOT a firmware defect. It is a comma-side scaling that was never updated. ***

    ---------------------------------------------------------------------------------------------------
    THE MECHANISM  [VERIFIED against opendbc_reference/honda/{carcontroller,values,interface}.py]

    openpilot rate-limits the steering command in NORMALIZED units, BEFORE scaling to CAN counts:

        carcontroller.py:126
            limited_torque = rate_limit(actuators.torque, self.last_torque,
                                        -STEER_DELTA_DOWN * DT_CTRL, STEER_DELTA_UP * DT_CTRL)
        carcontroller.py:143
            apply_torque = int(np.interp(-limited_torque * STEER_MAX, STEER_LOOKUP_BP, STEER_LOOKUP_V))

        values.py: STEER_DELTA_UP = STEER_DELTA_DOWN = 3, STEER_STEP = 1 (100 Hz), DT_CTRL = 0.01
                   STEER_MAX = CP.lateralParams.torqueBP[-1] = 4096 for the Accord
        interface.py:115  CAR.HONDA_ACCORD torqueBP = torqueV = [0, 4096]  => STEER_LOOKUP is IDENTITY

    So the normalized command may move +/-0.03 per 10 ms tick -- full scale in 0.33 s -- and that limit
    is applied to `actuators.torque`, the PID's NORMALIZED output, upstream of BOTH STEER_MAX and the
    firmware gain.

    *** QUARTERING THE PID RESTORED THE LOOP GAIN. IT DID NOTHING TO THE COMMAND SLEW RATE. ***
    The slew ceiling in firmware lane counts is (0.03 * STEER_MAX * 4 * gain) >> 15, which scales with
    the FIRMWARE GAIN and is completely untouched by the PID rescale:

        stock (gain 891) :  13.4 lane counts per 10 ms tick
        V38   (gain 3564):  53.5 lane counts per 10 ms tick     <- 4x faster, uncompensated

    Equivalently, the time to reach the SAME PHYSICAL TORQUE fell from ~170 ms to ~42 ms.

    *** WHY THAT DESTABILISES: THE RATE LIMITER WAS LOAD-BEARING DAMPING. ***
    interface.py sets steerActuatorDelay = 0.1 s. At stock the command rise time (~170 ms) was LONGER
    than the actuator delay, so the rate limiter dominated the loop dynamics and heavily damped it. On
    V38 the rise time (~42 ms) sits well INSIDE the delay, so the delay now dominates with the damping
    removed -- the classic recipe for a limit cycle. Stock's slow slew was suppressing an oscillatory
    tendency the loop always had; V38 loosened that suppression 4x and let it out.

    *** WHY THIS FITS THE ON-CAR EVIDENCE WHERE EVERY FIRMWARE CANDIDATE STRUGGLED ***
      - It is NOT a firmware mechanism, so it is exempt from the invariance partition entirely -- it
        does not need to be upstream or downstream of the gain.
      - It appeared with V38, because the 4x gain is exactly what un-scaled it.
      - It requires openpilot ENGAGED (operator-confirmed: absent in plain manual driving).
      - It is absent when the driver moves the wheel by hand -- no command is involved.
      - It is worst at low speed, where the lateral loop is most marginal.
      - It is immune to V39 and V41, which were both firmware and both downstream.

    *** MOTOR TORQUE RIPPLE IS RULED OUT (operator argument, 2026-07-20, accepted). ***
    Hand steering at low speed makes base assist deliver motor torque of COMPARABLE OR GREATER
    magnitude than V38's 1782-count LKAS lane -- the boost lane gp-0x6bbe alone is range-gated at
    +/-0x800 and the aggregate is far larger -- through the SAME aggregator -> governor -> shaper ->
    FOC path, and it is SMOOTH. So the motor and the entire shared output stage are demonstrably clean
    at this torque level. Any ripple explanation would have to explain why the same motor, at the same
    current, ripples only when the torque was requested over CAN. It cannot. DEAD.

    *** WHAT THAT LEAVES: THE LKAS-ONLY SEGMENT, UPSTREAM OF THE AGGREGATOR. ***
    This is the same conclusion gain_rescaling_invariance_analysis() reaches from units, now confirmed
    empirically from a completely independent direction. The remaining search space is exactly:
        CAN intake FUN_00052676 -> setpoint gp-0x69ae -> arbitration FUN_00028ea6 -> limit_and_pack
        -> distribute -> mixer -> gp-0x6b4c
    Within it, the standout is the ONE-POLE IIR at gp-0x3d3c in the arbitration core (pole ~0.969,
    TRUNCATING >>10 shifts, then >>5 to iVar34) -- the only stateful, LKAS-specific element with a
    near-unity pole. See lkas_iir_quantization_analysis() for the live hypothesis and its numbers.

    *** THE COUPLING TO r26 -- excitation vs amplifier, not competing hypotheses. ***
    A 4x faster command slew produces a ~4x larger driver column-torque derivative gp-0x4f62 for the
    same maneuver. r26 is LINEAR in that derivative and, unlike r24, has NO deadzone (r24 subtracts
    cal 0xC61F6 = +/-3 first), so r26 is the only derivative lane live near zero -- and both lanes
    carry the SAME sign, so there is no cancellation. That closes a loop: faster command slew ->
    bigger dtorque -> bigger r26 -> more motor torque -> more column motion -> repeat.
    So STEER_DELTA is the EXCITATION and r26 is the AMPLIFIER of one mechanism.

    *** TEST ORDER MATTERS. *** STEER_DELTA_UP/DOWN 3 -> 0.75 restores the stock physical slew rate.
    It is a one-line comma-side change, reversible in seconds, NO FLASH and no brick risk, and it
    attacks the driver of the loop. Do that BEFORE building any firmware image. If the symptom
    softens but persists, the r26 cal kill attacks the amplifier. Bundling both loses the discriminator.

    CONFIDENCE : [VERIFIED] the openpilot code path, the constants, and the 4x arithmetic.
                 [CONFIRMED] the PID rescale and the engaged-only character of the symptom (operator).
                 [INFERRED] that this specific loosening is what produces the felt vibration. The
                            damping argument is control theory over a plant model this kit does not
                            have. It is a PREDICTION, and the road test is the discriminator.
    ---------------------------------------------------------------------------------------------------
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
    Why V40 lost all power steering at ignition, and what that permits V42 to do.

    ---------------------------------------------------------------------------------------------------
    THE SUBTRACTIVE EXPERIMENT [CONFIRMED on-car 2026-07-20]

        V40 = V38 + cap flatten + slew cals 0xC6206/0xC6208 -> 0xFFFF   -> EPS lamp, NO power steering
        V41 = V38 + cap flatten                                          -> boots and drives cleanly

    V41 contains V40's ENTIRE cap-flatten edit (both mirror copies, Q13 slopes zeroed). The only
    surviving delta is the slew edit. The stale 0xC5FFC CRC that V40 also carried was independently
    cleared as a red herring (zero xrefs image-wide; boot does a blank-check only; the bootloader
    hard-codes a bridge past that block). *** V40's fault is the 0xFFFF slew write. ***

    *** THE ARITHMETIC MECHANISMS ARE BOTH REFUTED. [VERIFIED 2026-07-20, byte-level] ***
    An earlier draft of this function proposed (a) a signed load making 0xFFFF = -1, or (b) a signed-16
    overflow of `previous + step`. NEITHER survives the bytes:

        0x45410  ld.hu 0x7206[tp],r16     e5 87 07 72      <- UNSIGNED. 0xFFFF loads as 65535, not -1.
        0x45416  ld.hu 0x7208[tp],r16     e5 87 09 72      <- likewise.
        0x4541a  mul r23,r16,r0 ; 0x4541e sar 0xf,r16      <- step = (STEP * r23) >> 15

    r23 is provably bounded to [0, 32768] (seeded `ori 0x8000,r0,r6` @0x45380 = 32768, then two chained
    unsigned MINs via FUN_00049a78, each masked `andi 0xffff`). Ceiling: 65535 * 32768 = 0x7FFF8000 <
    0x80000000, so the signed-32 multiply CANNOT overflow for any u16 step. And the slew guard
    (@0x4543a-0x4545a) only ever USES the raw `HELD +/- STEP` candidate when it has already proven the
    candidate lies strictly inside [HELD, TARGET] -- so no 16-bit wraparound can reach the `st.h`.
    Both cals have exactly ONE reader image-wide (0x45410 / 0x45416). Zero blast radius.

    SO WHAT DID 0xFFFF ACTUALLY DO? It made the guard never fire, i.e. it SNAPPED THE COMMAND TO TARGET
    EVERY CYCLE -- complete removal of rate limiting on the merged command, not a sign error.
    [INFERRED] the fault then follows from that: with zero filtering, at ignition the target is sensor
    noise around zero and the command chases it at full bandwidth. The monitors FUN_0004595a and
    FUN_00045a20 share the SAME state gate as the governor (r23, mask 0xd30) and reach
    FUN_00016de6(0x1d,...) -- which is HARD-FAULT-ELIGIBLE and has NO debounce counter, so ONE
    out-of-bounds cycle suffices for motor-off + power-cycle-to-recover. That matches V40's signature
    exactly: EPS lamp and total loss of assist, at ignition, before the car ever moved.

    *** THE DEFECT WAS THE MAGNITUDE, NOT THE DIRECTION OF THE EDIT. *** A step large enough to snap to
    target removes the protection; a moderate step preserves it. Concretely: for a noise excursion
    smaller than the step, stock and a raised step behave IDENTICALLY (both pass it whole). The two
    only differ for excursions BETWEEN the old and new step. 0xFFFF passes a full-scale ~4762 jump in
    one cycle; 820 does not.

    *** THE CONSEQUENCE FOR V42: raising the slew step is NOT itself disqualified. ***
    A MODERATE, POSITIVE, in-range raise is a different edit from 0xFFFF. The safe ceiling is set by
    the arithmetic width -- if the load is signed, stay well inside 0x7FFF, and keep
    (max |held| = 10240) + step inside signed-16 with margin.

    THE PRINCIPLED VALUE IS RAMP-TIME PARITY, NOT "AS FAST AS POSSIBLE". The step cals are ABSOLUTE
    counts; V38 multiplied the reachable target by 4 and left them alone, so the number of cycles to
    full command grew ~4x. Restoring the STOCK CYCLE COUNT at V38's reach means scaling the steps by
    the same 4: 512 -> 2048 and 205 -> 820. That is a bounded, invariant-preserving edit rather than
    the removal of a protection, and it leaves the limiter fully functional for base assist.

    *** SCOPE WARNING, from gain_rescaling_invariance_analysis(): this addresses the RATCHET ONLY. ***
    With the openpilot PID quartered, the slew sees stock-equivalent counts for stock-equivalent
    torque, so it cannot be the ~5 mph small-command vibration. Do not expect V42's slew edit to move
    that symptom, and do not read "vibration unchanged" as evidence the slew edit failed.
    ---------------------------------------------------------------------------------------------------
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
    Apply FUN_0004503c then FUN_000456a4 before the soft-EME integrator.

    [VERIFIED] FUN_0004503c loads gp-0x6b94 @0x453e0 and gp-0x4f64 @0x453f0, applies a Q15-scaled
    symmetric clamp, a second Q15 scale, and a 512/205-calibrated slew, then writes gp-0x6ace.
    FUN_000456a4 adds gp-0x6ad0 and writes gp-0x6acc, which the shaper reads @0x431c4. The three Q15
    bank outputs are exposed as replay inputs; identity is an explicit model default, not a signal ID.

    ---------------------------------------------------------------------------------------------------
    *** 2026-07-19 INSTRUCTION-LEVEL VERIFICATION -- and the V38 RATCHET ROOT CAUSE ***

    ASYMMETRIC SLEW [VERIFIED @0x4543a-0x4545e]. Register map confirmed @0x45420-0x4542e:
    r10 = TARGET, r14 = HELD (gp-0x138a). Motion AWAY from zero is capped to HELD +/- STEP; motion
    TOWARD zero, or a TARGET on the opposite side of zero from HELD, is immediate and unlimited.
    This is NOT a symmetric delta clamp -- the model's reconstruction was correct.

    SIGN-CROSSING RESET [VERIFIED @0x45420-0x45436]. Fires when TARGET and HELD have opposite
    nonzero signs; zeroes BOTH the working register r14 and the persisted cell gp-0x138a
    (`mov 0x0,r14 ; st.h r0,-0x138a[gp]` @0x45434). NUANCE: after the reset the slew still applies
    this cycle with HELD=0, so the output does NOT jump to the opposite-sign target -- it is capped
    to +/-STEP from zero. The model already implements this correctly.

    *** THE STEP SELECTOR IS THE FINDING [VERIFIED @0x45402-0x45419] ***
        ld.bu -0x67f5[gp],r11 ; cmp r0,r11 ; bne -> cal 0xC6208 (205)
                                            else -> cal 0xC6206 (512)
    So gp-0x67f5 == 0 selects the FAST 512 step; 1 or 0xFF selects the SLOW 205 step.
    gp-0x67f5 is written by the driver-torque voter FUN_00041eec (@0x4222a/0x42258/0x42288):
      - if the "driver holding steady" flag gp-0x67f4 == 0 (raw driver torque diverges from the
        voted average by >= 65 counts, i.e. fast hand motion), gp-0x67f5 is forced to 0xFF
        IMMEDIATELY, with no debounce -> the SLOW 205 step.
      - if gp-0x67f4 == 1, gp-0x67f5 debounces over cal 0xC64E7=10 cycles toward 1 while the voted
        |torque| stays >= cal 0xC631E=640 -> also the SLOW 205 step; below 640 -> the FAST 512 step.

    CONSEQUENCE: the fast 512 step applies ONLY when the driver is holding steady AND below 640
    counts. During a hard, dynamic, hand-over-hand turn BOTH conditions point the same way, so the
    away-from-zero step is pinned at 205 -- precisely in the regime where the ratchet is reported.

    *** WHY V38 REGRESSED AND STOCK DID NOT: THE INVARIANT IS RAMP TIME, NOT STEP SIZE. ***
    The step cals 512/205 are ABSOLUTE counts and V38 did not touch them, but V38 raised the target
    ~4x. Ramp time scales as target/step, so V38 silently made the ramp ~4x longer. Combined with a
    sign-crossing reset that dumps the accumulated value INSTANTLY, this is mechanically a ratchet:
    slow build, instant collapse, repeat. It predicts exactly the reported "the wheel appears capable
    of turning harder but is intermittently stopped," and it is worst on hard dynamic turns because
    that is where the step is pinned slow. See slew_ramp_time_analysis().

    *** SUBSTITUTION STATE -- FULLY TRACED 2026-07-20. THIS IS THE LEADING RATCHET ROOT CAUSE. ***
    *** The model's prior "state 4 is probably one-time bring-up" assumption is REFUTED. ***

    THE MECHANISM [VERIFIED, every sub-point, raw instructions @0x454f8-0x45526 and @0x455cc]:
        0x454f8  ld.bu -0x67fa[gp],r12
        0x454fc  cmp 0x4,r12                  (a) the compare IS against literal 4
        0x454fe  bne 0x455c4                  not state 4 -> accept the fresh value, no substitution
        0x45500  jarl FUN_00049a5a (abs) on fresh gp-0x6ace ; 0x4550a jarl FUN_00049a78 (clamp)
        0x4550e  ld.h -0x138a[gp],r6          the PERSISTED previous value
        0x45516  jarl FUN_00049a5a (abs)      ; 0x45520 jarl FUN_00049a78 (clamp)
        0x45526  cmp r10,r24 ; bnh 0x455c4    (c) the compare is on ABS+CLAMPED MAGNITUDE, unsigned;
                                                  substitution runs ONLY when |fresh| > |previous|
        (b) the substituted value is NOT a hard freeze: it re-runs the SAME rate-interpolation block
            (0x4553a-0x455aa, cals tp+0x7134 / tp+0x748e) that mirrors the unconditional primary
            computation at 0x4546a-0x454e4, but SEEDED FROM gp-0x138a instead of the fresh candidate.
            Net effect: "hold near the old value, rate-shaped."
        (d) *** 0x455cc  st.h r6,-0x138a[gp]  UNCONDITIONAL WRITEBACK. ***
            The suppressed output becomes NEXT cycle's comparison baseline. So this is CUMULATIVE
            across consecutive state-4 cycles -- a genuine self-sustaining ratchet, not a one-shot
            clamp. Each cycle that wants more torque gets pulled back toward the held value, and that
            pulled-back value is what the next cycle must beat.

    *** STATE 4 IS REACHABLE MID-DRIVE, NON-DIAGNOSTICALLY. [VERIFIED] ***
    Image-wide search found 5 `st.b 4,-0x67fa[gp]` sites. Two are reachable in ORDINARY operation with
    no UDS session and no power cycle:
        0x19bb0  in FUN_00019b10 : 5 -> 4, normal mode, when gp-0x68ad == 0
        0x19e54  in FUN_00019d90 : 10 -> 4, normal mode, when NOT(gp-0x4378==1 && gp-0x3eec!=0)
                                   AND NOT(gp-0x6d78 & 0x5080) AND FUN_000197d0(0xf)==0
    (The other three -- 0x198d8, 0x19de0 and 0x57e94 -- are diag-mode-only or the power-on reset.)
    State graph: 1->3->{4,6} ; 4->{11,10,6, or 5 iff gp-0x68ad==1} ; 5->{11 if ready, 4 if
    gp-0x68ad==0} ; 10->{6,4} ; 11->6 ; 6->{7,9} ; 9->7 ; 7 = dead-end sink. {6,7,9} is a one-way
    degraded branch. Steady driving sits somewhere in {4,5,10,11}; 11 is the best "settled" candidate
    but the SM can oscillate within that cluster. [INFERRED: which value is steady state]

    *** AND THE TRIGGER IS TORQUE-SENSOR LINKED -- which is why it shows up on HARD turns. ***
    gp-0x68ad's sole updater FUN_0001a104 runs every cycle at the top of BOTH the state-4 and state-5
    handlers. Critically, NO branch in it leaves gp-0x68ad unchanged at 1: it is either cleared
    unconditionally (when gp-0x4378==1 && gp-0x6a98!=0) or passed to FUN_00022016, which PRESERVES it
    only while gp-0x679d==1 OR (gp-0x6a5e != 0 AND gp-0x67f4 == 1) -- i.e. nonzero voted column torque
    AND the voter's plausibility latch converged. So a column-torque zero crossing, or a momentary
    plausibility drop near sensor saturation, flips gp-0x68ad to 0 and trips 5->4 on the very next
    dispatch cycle. Both are physically plausible during a hard, large-angle turn.

    WHY IT SURFACED ONLY ON V38 -- consistent with gain_rescaling_invariance_analysis()'s partition.
    The substitution caps the INCREASE, so the felt severity is the shortfall (demanded - held). Stock
    could only ever demand 417 LKAS counts, bounding the shortfall; V38 can demand 1782. The ratchet
    amplitude is therefore ~4x deeper, in exactly the ">417 counts, downstream of the gain" regime the
    partition assigns to the ratchet. The mechanism is old; V38 made it perceptible.
    It also explains why strong DRIVER torque moves the wheel fast with no symptom: driver torque is
    mechanical and never passes through this governor.

    STATE 4 IS SPECIALLY HANDLED IN 4 OTHER COMMAND-PATH FUNCTIONS, so it is a live operating
    condition rather than a boot value: FUN_00044cf0 @0x44cfe (state==4 SUPPRESSES a torque-cap LERP
    branch -- an independent second torque-shaping effect), FUN_0002cc2a, FUN_0002e734, FUN_00041304.
    Separately FUN_0003d04c @0x3d074 REJECTS the LKAS deliver-commit outright (return 6) when
    gp-0x67fa == 10, confirming state 10 is also a live torque-relevant excursion.

    *** gp-0x437c / gp-0x4378 RESOLVED 2026-07-20 -- THEY ARE UDS DIAGNOSTIC ARTIFACTS. [VERIFIED] ***
    The gp-relative search missed them because they are written via a 32-bit IMMEDIATE base:
    `mov 0xfedf3c80,rX` then small-displacement stores at +4/+8. Sole writers are FUN_0001a4cc /
    FUN_0001a4f2 / FUN_0001a516, called ONLY from the service-ID dispatch walker FUN_0001a24e (table
    at 0x8ac1c), called ONLY from FUN_0001b47a's `uVar5 == 0x41` arm -- a UDS-style service switch
    whose siblings are 0x22 (ReadDataByIdentifier-shaped), 0x34/0x35/0x37 (RequestDownload/Upload/
    TransferExit-shaped) and a textbook SecurityAccess seed/key routine (FUN_0001a33e: seed ^ 0x395a,
    key^2 + 0x9176, 4-stage session counter). Gated at entry on a "request pending" flag gp-0x3ed8 and
    a frame-validity parse. With no diagnostic tool attached and issuing service 0x41, BOTH cells read
    their power-on default 0 (no static initializer, no other writer image-wide).
    [INFERRED, one hop] FUN_0001b47a's own caller has zero static xrefs -- almost certainly a periodic
    diagnostic-RX poll task dispatched by function pointer.

    *** CONSEQUENCE: THE WORST CASE IS RULED OUT. *** Because gp-0x4378 is ~always 0 in the field, the
    UNCONDITIONAL clear @0x1a142 essentially never fires. gp-0x68ad is therefore genuinely HELD across
    cycles once engaged -- NOT a 1-cycle pulse, and the SM does NOT bounce 5<->4 every cycle. It clears
    only through FUN_00022016's CONDITIONAL path: gp-0x679d != 1 AND (gp-0x6a5e == 0 OR gp-0x67f4 != 1).
    So the ratchet is EVENT-DRIVEN by genuine torque/plausibility transients -- physically plausible to
    recur repeatedly during a sustained hard, large-angle turn near sensor saturation, but not a fixed
    per-cycle duty cycle. [OPEN] its actual frequency is a LIVE-TELEMETRY question, not a static one:
    it needs gp-0x6a5e / gp-0x67f4 / gp-0x679d read during an actual hard-turn drive.

    *** NO CALIBRATION-ONLY FIX EXISTS. [VERIFIED -- structural, whole-chain walk] ***
      (a) ENTRY: all six functions in the 5->4, 10->4 and 3->4 reachability chains (FUN_0001a104,
          FUN_00022016, FUN_00022034, FUN_00019d90's normal legs, FUN_000220ba, FUN_00022078) contain
          ZERO tp+-relative calibration reads. They are pure runtime flag/state/counter logic.
      (b) SUBSTITUTION: cals tp+0x7134 (0xC6134 = 1000, ld.hu at all 23 readers) and tp+0x748e
          (0xC648E = 0, ld.h SIGNED at all 22 readers -- a real mixed-signedness trap) are read at
          IDENTICAL displacements in BOTH the primary block (0x454a8-0x454d8) and the substitution
          block (0x45578-0x455aa) -- same cells, not mirrors -- and ALSO in FUN_00041464 (16 sites for
          0x7134 alone) and FUN_000456a4. Editing either changes >=3 functions.
      (c) DECISIVE: the branch decision itself reads NO cal. `cmp 0x4,r12` @0x454fc and
          `cmp r10,r24 ; bnh` @0x45526 are unconditional once true. No cal can make a value seeded
          from gp-0x138a equal one seeded from the fresh candidate, so even a "pass-through" edit is
          structurally impossible.

    *** THEREFORE: FIXING THE RATCHET REQUIRES A CODE EDIT. ***
    Candidate, the most surgical the disassembly offers: a SINGLE CONDITION-CODE NIBBLE at 0x454fe,
    `bne 0x455c4` -> `br 0x455c4` (V850 cond field 1010 -> 0101), making the substitution
    unconditionally skipped. No relocation, no cave, no instruction-length change, no address shifts --
    categorically unlike the V24/V27 trampolines that faulted.
    *** SAFETY: PROVED BY CONSTRUCTION 2026-07-20 (was an argument; now a proof). ***
    The slew at 0x4543a-0x45458 is ASYMMETRIC, not a symmetric [held-step, held+step] clamp -- it has two
    toward-zero fast paths (`cmp r0,r10 ; ble 0x45458` @0x4543e/40 and `cmp r0,r10 ; bge 0x45458`
    @0x4544c/4e) that snap straight to TARGET. Walking all four branches, output is TARGET,
    min(TARGET,HELD+STEP), TARGET, or max(TARGET,HELD-STEP) -- so in EVERY branch |output| <= |TARGET|
    and sign(output) == sign(TARGET). With TARGET = clamp(gp-0x6b94, +/-bound) that yields
    |gp-0x6ace| <= |gp-0x6b94| with matching sign FOR ANY HELD VALUE, including the larger held values
    the V42 edit permits. Those are exactly FUN_0004595a's two fault conditions, so that monitor CANNOT
    trip on the primary path. Under the symmetric-clamp reading it would NOT have held (a fast decrease
    with a large held value overshoots) -- the distinction was load-bearing.
    STANDING FACT, recorded but NOT gating V42: FUN_00016de6(0x1d,data,1,1) has NO debounce either --
    it walks straight to FUN_0001611e (record[+8]&0x41, nonzero for 0x1d) then FUN_00018738 = motor-off.
    One true condition anywhere on that path reaches motor-off with no grace period.
    ORDERING [VERIFIED]: the substitution at 0x454f8 sits AFTER the
    slew limiter (0x4543a-0x4545e) and AFTER the primary rate interpolation (0x4546a-0x454e4), so
    skipping it leaves the command still governor-clamped (<=4762) and still slew-limited (512/205 per
    cycle). It is a SECOND, state-4-only constraint on top of the primary one -- not the only thing
    preventing a torque step. If that ordering is wrong the argument collapses.
    *** GO/NO-GO CLOSED 2026-07-20 -- V42 IS BUILT (one byte @0x454FE, bne -> br). [VERIFIED] ***
    FUN_00043e44 reads NEITHER gp-0x67fa NOR gp-0x6ace/gp-0x138a/gp-0x4cca anywhere in 0x43e44-0x44a8b.
    gp-0x6ace's shadow gp-0x4cca is written by the SAME instruction pairs on every path, so the pair
    cannot desynchronise; gp-0x138a is unshadowed with no external reader. FUN_00045a20 compares against
    gp-0x6acc, which FUN_000456a4 recomputes fresh FROM gp-0x6ace every cycle, so it tracks automatically.
    FUN_0004595a is the one real external monitor and it cannot trip -- see the proof above.

    *** RESOLVED 2026-07-20: the control task FUN_0002214a runs at ~1000 Hz. *** Two independent routes:
    (a) OSTM0 -- OSTM0CMP=79999 auto-reload / ~80 MHz PCLK = 1000 Hz (PCLK is one of the 4 DFLASH.DCLKWAIT
    options {48,64,80,160} MHz; 80 MHz is the only one giving a clean ~1 ms, and 100 Hz would need a
    non-existent 7.95 MHz); (b) the STEER_STATUS=4 dwell -- cal 0xC64DF = 100 cycles, measured at 100.00 ms
    on the bus (dwell counter gp-0x6757 decrements INSIDE arbitration, so it measures that task directly).
    Cycle counts in FUN_0002214a's tree (arbitration, aggregator, shaper, governor, sign filter
    FUN_00041464) convert to Hz at 1000 tick/s. ⚠ The ASSIST-SHAPING task FUN_00022ca0 (boost, damping
    producer FUN_00034350) is a DIFFERENT task; its own rate is not statically determinable (~100 Hz would
    be an architecturally normal fast-control / slow-input-processing split) -- but that is an EFFICACY
    question for the V44 damper, not a safety one (the damper stays net-dissipative at either rate).
    The 100.01362 Hz figure once cited for CAN 399 was inflated by gap-reconstruction; the true frame
    rate is 99.99849 Hz, and 399 is a 100 Hz COMMS cadence inside the 1000 Hz task, not the task rate.
    ---------------------------------------------------------------------------------------------------
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
    Rate-shape the merged command and run the slow-windup soft-EME cut (SM2/SM3).

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP  (function named s_motor_torque_rate_shaper in the project)
      Function     : FUN_00042af8  (shaper; integrator update block 0x431c4-0x4327c)
      Reads        : gp-0x6afe (0xFEDF1502) gated input (dual range-check @0x43ae8);
                     the integrator's command is gp-0x6acc (0xFEDF1534) = governed aggregate demand +
                     post-governor compensation, read at 0x431c4.
      Integrator   : gp-0x3570 (0xFEDF4A90) winds on (gp-0x6acc command - bound); store @0x4327c
      Bound        : 3-way MAX/MIN of three arms (each independently gated):
                       corridor arm  cal tp+0x774e(0xC674E)  -- DRIVER-OVERRIDE gated:
                                     OFF when |pos_err gp-0x6bf0| <= corridor_gate(9216)  (hands-off)
                       IIR arm       gp-0x3574 >> 8           -- column-velocity envelope (decays held)
                       boost arm     cal tp+0x7768(0xC6768)   -- ANGULAR-RATE keyed; AUTHORITY-latched
                                     to 0 once authority > boost_latch_auth(16384) for
                                     boost_latch_dwell(20) cyc
      Authority    : gp-0x6966 = (|gp-0x3570 >> 15| * authority_scale(1092)) >> 10
      SM2          : state-1 entry requires command!=0, authority>=16384, AND tp+0x74cc!=3. V38/V39
                     carry 3, so this specific authority transition is inhibited. Recovery/ramp is OPEN.
      SM3          : |integrator>>15|>=30720 enters a dwell state; only after 20 sustained cycles does
                     its Q15 factor become tp+0x7420=0. Saturation is not an immediate cut.
      SM1          : sm1_arm(2048), velocity+opposition gated (fast anti-runaway) -- SEPARATE, untouched

      *** 2026-07-19 SHAPER RE-TRACE against _v38_plain_image.bin (cal VALUES read from the V38 file
      itself; structural walk done on the V39 decompile, whose code region is byte-identical here). ***

      BOOST-LATCH RECOVERY IS AN EXACT-ZERO TEST [VERIFIED]. In state 2 the code is
      `boost_output = boost_output * (authority == 0)`, so the boost arm is forced to 0 EVERY cycle
      unless authority is PRECISELY 0, in which case it passes and the state resets to 1 that same
      cycle.

      *** CORRECTION 2026-07-21 [VERIFIED by decompile of the integrator update, gp-0x3570 update
      branches]: the previous text here said authority==0 is "a narrow band ... hard to reach, not
      merely slow", and the SM3 paragraph called it "a measure-zero target for a continuously driven
      integrator". BOTH ARE WRONG. The decay branches clamp with max(0,...)/min(0,...), so the
      integrator SNAPS TO EXACTLY 0 on the cycle it crosses zero -- it does not overshoot and drift
      past. Exact zero is therefore the integrator's natural RESTING STATE whenever the command dwells
      within-bound long enough to decay there, not a knife-edge coincidence. Recovery from both the
      boost latch and SM3 is consequently EASIER than this model previously claimed, and the
      "independent rapid-re-cut ratchet candidate" inferred from the measure-zero premise does not
      follow. (The ratchet's real cause was separately established as the state-4 governor
      substitution and fixed in V42.) ***

      SM3 IS THE ONLY LIVE CUT [VERIFIED structure]. State 3 recovers on exact `|integrator>>15| == 0`
      -- reachable per the correction above. The freshly-recovered state 1 is still fragile: if raw
      authority <= 0x7fff and the integrator is any nonzero value, it returns to state 3 (cut) with NO
      new 20-cycle dwell.

      gp-0x3570 HAS EXACTLY ONE WRITE SITE in this function (the windup update). SM3's trip does NOT
      reset it, so nothing internal forces the integrator down; whether it ever returns toward zero
      depends entirely on the command falling below the bound. If the command SUSTAINS above the
      bound, SM3 stays cut steadily rather than oscillating -- so a ratchet requires the command or
      bound to fluctuate, which this function alone does not establish.

      IIR ARM CEILING IS 12288 [VERIFIED], so it CAN exceed the 5120 floor and win the 3-way MAX --
      this closes a long-standing OPEN question. But it does so only when the column is actively
      ROTATING. That is a genuine premise problem for any "all three arms collapse together"
      hypothesis: on a MOVING wheel the IIR arm should be populated, not collapsed. (It is
      self-consistent only if the ratchet itself is what periodically arrests the wheel.) Note also
      that the IIR's own smoothing is BYPASSED when authority > cal 0xC641C=32440 -- just below SM3's
      ~32730 trip-equivalent -- so the arm briefly tracks instantaneous velocity right at the trip.

      *** CONTESTED -- DO NOT ACT ON EITHER READING WITHOUT A SECOND PASS. *** The same re-trace
      reports that SM1 and SM2 are PERMANENTLY BLOCKED on every build INCLUDING STOCK, by byte gates
      tp+0x74cd (0xC64CD) and tp+0x74cc (0xC64CC), both = 3 in stock/V31/V38/V39: SM2's only arm
      transition takes an unconditional no-arm path when the gate is 3, and SM1 has the same shaped
      gate. If true, SM3 is the sole live cut and this model's SM2 arming is unreachable rather than
      merely inhibited. This CONTRADICTS the standing `override_snap_state_machines` memory, whose
      "SM2 and SM3 are reachable" conclusion underwrote V19's 0xC6422 rescale. The finding came from
      DECOMPILER PSEUDOCODE ONLY, with no instruction addresses. Re-verify against raw disassembly
      before editing 0xC6422 or 0xC61DE on the strength of either claim.
      Governor     : runtime torque governor gp-0x4f64 (0xFEDF309C) -- NOMINAL 4762 (cal tp+0x7202,
                     0xC6202) but COMPUTED, not a flat clamp. Writer FUN_0007b022 (lockstep shadow
                     gp-0x448a; fault FUN_0006b9ee on mismatch). Motor-state byte gp-0x4e5a selects:
                       ==0/2: gov = MIN(4762, adaptive_LERP) through gp+0x184.
                       other (including operative 1): gov = MIN(4762, adaptive_LERP, unresolved
                            feasibility budget B) x1024 -> ceiling 4762, floor 0.
                     *** The adaptive_LERP (gp+0x128) axis is the MOTOR RESOLVER ELECTRICAL-ANGLE RATE
                     (motor angular velocity), NOT vehicle road speed *** -- 7-hop instruction trace:
                       gp+0x128 LERP (tp+0x6030/tp+0x620E) axis = gp-0x6ac0
                        <- FUN_00041464 (slew-limit + sign-gate vs commanded torque gp-0x6b98)
                        <- gp-0x4f50 (IIR, range-clamped +/-13000, 65535=invalid -> not an angle)
                        <- FUN_00068fbe (IRQ-guarded snapshot of resolver-rate reg gp-0x29c4)
                        <- FUN_00068f52 (delta of consecutive angle samples, 0x4000=14-bit wraparound
                                         correction, scaled to a rate -- a position->velocity diff)
                        <- FUN_00065afe (resolver sin/cos ATAN2 decode, output & 0x3fff = 14-bit angle).
                     So the governor tapers authority during FAST STEERING MOTION (quick corrections,
                     parking lock-to-lock), NOT at highway speed. [OPEN: a secondary normalization
                     ratio fVar48 not fully pinned -- minor, doesn't change the axis identity.]
                     A160 table: X=[1050,1700,2500,3700,4100], Y=[5325,3584,2406,1587,512],
                     Q13 slopes=[-21940,-12059,-5593,-22021]. It reaches 4607 at z=1318; note that
                     assist-inclusive gp-0x6acc can conservatively reach 7322 before its +/-8192 sanitize.
                     Applied in TWO firmware places (modelled separately):
                       (1) m_motor_torque_governor FUN_0004503c @0x453f0: clamp(gp-0x6b94,
                           +/-(gov x Q15 limiter-bank output)>>15) upstream of the shaper. gp-0x6a64
                           is only a separate threshold input, not this multiplicand;
                       (2) HERE @0x43b0a: clamp(demand, +/-gov), THEN a SEPARATE static +/-0x2000 clamp
                           @0x43b0e -- two SEQUENTIAL clamps, not one.
                     A third, DIAGNOSTIC path (FUN_0006e09a/e140 @0x6e0f2, gated on column-still
                     delta<25) can OVERWRITE gp-0x6b98 = gov x1 directly, bypassing both clamps --
                     likely a motor self-test; dispatch-table caller (0xBCB14/18) untraced.
      Output       : gp-0x6b98 (0xFEDF1468), final +/-0x2000 clamp (@0x43b0e); lockstep shadow gp-0x4ce2.
      Scheduled by : RTOS steering task chain, after the gate (base tick ~1 ms).
    CONFIDENCE     : [VERIFIED] bound arms + arm gating + SM arming (V30/V31 sessions); the governor
                     MIN structure, its motor-RATE (not road-speed) LERP axis (7-hop trace), the two
                     sequential clamps, and the 3 consumers (2026-07-17 governor re-trace).

    V31's boost floor fixed its observed soft EME and V38 is fault-free on-car. The earlier static proof
    that 5120 exceeds every possible integrator input was too narrow: assist joins before the first
    governor, so the conservative gp-0x6acc envelope is 4762 governor + 2560 compensation = 7322. This
    model accepts explicit bound and shaper-term replay inputs; it does not claim every assist-inclusive
    combination is contained by the 5120 floor.
    ---------------------------------------------------------------------------------------------------
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

    # gp-0x6acc drives the integrator through a ONE-SIDED zero-gate and the mode preprocessor.
    #
    # *** CORRECTION 2026-07-20 -- THIS GATE IS NOT A SYMMETRIC +/-8192 WINDOW. [VERIFIED] ***
    # The model previously used a symmetric _range_gate here. The bytes at 0x431c4 say otherwise:
    #   0x431c4 ld.h  -0x6acc,gp,r9      24 4f 34 95   SIGNED load, sign-extended
    #   0x431d0 addi  0x2000,r9,r6       09 36 00 20   r6 = x + 8192
    #   0x431d4 addi  -0x4001,r6,r0      06 06 ff bf   flags on r6 - 16385 (result discarded)
    #   0x431d8 cmovc 0x0,r9,r11         e0 4f 02 5b   r11 = CY ? 0 : r9
    #   0x43206 st.h  r11,-0x6b08,gp                   -> gp-0x6b08
    # The condition is the PLAIN inequality `x + 8192 < 16385`, i.e. `x <= 8192`. There is no absolute
    # value. So the ENTIRE negative range passes through unchanged, and ONLY x > +8192 is zeroed.
    # A chatter mechanism riding on this gate could therefore only ever appear on the POSITIVE
    # command side -- worth checking against whether an observed symptom favours one steering
    # direction. Mode selector cal 0xC64C8 reads 0x00 in this build, so the default path above is the
    # live one (the mode==1 / mode==2 branches never fire). Confirmed by two independent methods.
    #
    # NOT REACHABLE at the verified maximum, and both bounds are now VERIFIED rather than assumed:
    #   max|gp-0x6ace| = 4762  -- the Q15 limiter bank is LITERAL-SEEDED at 0x8000 (exactly unity)
    #                             immediately after the prologue and combined ONLY through
    #                             FUN_00049a78 (min) and FUN_00049a90 (clamp/median-of-3). No add and
    #                             no amplifying multiply exists anywhere on that data path, and the
    #                             downstream slew limiter cannot overshoot its own target. So the
    #                             model's old "bank output <= unity" DEFAULT is now a verified fact.
    #   max|gp-0x6ad0| = 2560  -- LERP2 short-circuits to the literal ceiling cell once INDEX >= 4150
    #                             (@0x4580a / bnc 0x45824); there is NO extrapolation past the table.
    #   => 7322 < 8192, an 870-count margin that genuinely holds.
    # And an excursion past -8192 would not meet this gate at all; it would meet the separate
    # SATURATING +/-0x2000 clamp near the function's end (~0x43b0e-0x43b24) -- a smooth clamp, not a
    # cliff, so no chatter mechanism there either.
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
    The ASIL cross-check: an independent float twin recomputes the same bound wall; if the int wall and
    the float twin diverge beyond tolerance, latch DTC 0xF00049 and kill the motor.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_00043e44  (float monitor twin of the shaper bound)
      Twin arms    : float mirror of corridor (0xC6598..) + boost (0xC65C4..); float Y = int Y / 1024
      Tolerance    : +/-5 LSB lockstep (movhi imm 0x3ba0 / 0xbba0 = +/-5/1024) @0x44640..
      On divergence: DTC 0xF00049 -> latched motor-off (hard EME)
      Scheduled by : RTOS steering task chain, paired with the shaper (base tick ~1 ms).
    CONFIDENCE     : [VERIFIED] this is WHY every soft-EME edit must move int AND float in lockstep.

    This is the class the V25-V27 builds tripped (int/float desync -> hard fault). V31 keeps the twin
    matched exactly (boost float 4.0 == int 4096 / 1024), so the monitor delta stays 0.
    ---------------------------------------------------------------------------------------------------
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
    Produce the ENABLE/mode byte gp-0x67a4.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Function     : FUN_0002b422 region ~0x2b422-0x2b51e  (an 8-state handshake PRODUCER FSM)
      Writes       : gp-0x67a4 (0xFEDF185C) in {0,1,2,3,4,5}  @0x2b51e (st.b r14,-0x67a4[gp])
      Inputs       : gp-0x67a1/a2/a3/a7 + prior state gp-0x3d28
      Scheduled by : RTOS steering task chain (base tick ~1 ms).
    CONFIDENCE     : [VERIFIED] it PRODUCES gp-0x67a4.
                     [OPEN]     the previously-assumed "{2,3} else LKAS=0" CONSUMER gate is NOT
                                substantiated -- a Ghidra xref sweep found ZERO readers of gp-0x67a4
                                (0xFEDF185C), the same dead-gate pattern as gp-0x6809. Do NOT model an
                                ENABLE cut here until a reader is located. (Caveat: an ep-relative /
                                computed-base read could be missed by the xref index.)
    ---------------------------------------------------------------------------------------------------
    """
    # Modelled as a passthrough producer; no confirmed consumer gate exists, so it does not cut here.
    st.enable_fsm = 2 if st.decider_verdict == 0 else 0


def foc_current_loop(sensors: SensorInputs, st: EpsState) -> float:
    """
    Field-oriented control inner loop: turn the merged command into a q-axis current reference and
    drive the PI/SVPWM voltage computation.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      ISR          : shared EI trampoline FUN_0001492a, EIIC 0x600 -> FUN_0006404c (ADC-complete) [ISR]
      Chain        : 0x6428e (2 phase currents) -> 0x65afe (resolver sin/cos -> atan2 rotor angle)
                     -> 0x68f52 (rotor-SPEED estimator) -> 0x711f8/0x710d4 (ASIL sum self-checks)
                     -> FUN_00071272 (Park/Clarke + PI current regulator + SVPWM; duties x51200.0)
      Consumes     : the q-current reference derived from the merged command gp-0x6b98
      Scheduled by : EI interrupt (EIIC 0x600), fast inner loop synchronous to the ADC/PWM carrier.
                     [VERIFIED dispatch + chain | rate tied to carrier, absolute Hz OPEN]
    CONFIDENCE     : [VERIFIED] the loop is angle/speed/current feedback + regulator.
                     [OPEN]     the exact RAM var handing mixer/shaper output into the q-ref is not
                                pinned (may route off-die over CSIG0). The on-chip FOC->PWM is verified.

    This is where "command" finally becomes "motor torque": q-axis current is proportional to torque.
    ---------------------------------------------------------------------------------------------------
    """
    # abstract: q-current reference tracks the merged command (torque ~ Iq), gated by FOC enable/fault
    st.q_current_ref = float(st.merged_command)   # proportional stand-in for the Park/PI result
    return st.q_current_ref


def motor_pwm_output(st: EpsState) -> tuple:
    """
    Emit the 3-phase PWM compare values that actually move the motor.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      ISR          : shared EI trampoline FUN_0001492a, EIIC 0x970 -> FUN_00061614 (TSG20)        [ISR]
      Chain        : FUN_00061614 -> FUN_0006c5ce  (Park/inverse -> duty compute)
      Writes       : TSG20 CMPU/CMPV/CMPW = 0xFFFFCCB0 / 0xB4 / 0xB8  (÷51200.0, period-clamped) = MOTOR
      Commutation  : table @ tp-0x2d40 (0xF52C0)
      Scheduled by : EI interrupt (EIIC 0x970). PWM carrier frequency unresolved (TSG20 clock not
                     confirmed; init writes period 5000 / compares 5160).          [rate: OPEN]
    CONFIDENCE     : [VERIFIED] EIIC dispatch + the CMPU/V/W write is the physical motor output endpoint.
    ---------------------------------------------------------------------------------------------------
    """
    duty = st.q_current_ref / 51200.0
    return (duty, duty, duty)   # CMPU/CMPV/CMPW (3-phase commutation applied in the real emitter)


# =====================================================================================================
# SECTION 10 -- EXECUTION MODEL / ORCHESTRATION
# -----------------------------------------------------------------------------------------------------
# Two clocks drive everything:
#   (1) the RTOS STEERING TASK (w_steer_control_task, FUN_0002214a) on the OSTM0 base tick (~1 ms),
#       which runs the command pipeline (arbitration + its inlined SMs are phase-gated, 4 of 16); and
#   (2) fast INTERRUPTS via the shared EI trampoline FUN_0001492a -- EIIC 0x600 = ADC-complete/FOC
#       inner loop, EIIC 0x970 = TSG20 PWM output -- plus the CAN-RX mailbox ISR that stages the command.
# See each function's "Scheduled by" banner above for the evidence; this function shows the ORDER.
# =====================================================================================================

def control_task(frame: CanSteeringControl, sensors: SensorInputs, st: EpsState, cal: Calibration) -> tuple:
    """
    One tick of the periodic steering control task: CAN command -> motor PWM.

    ---------------------------------------------------------------------------------------------------
    FIRMWARE MAP
      Task root    : FUN_0002214a  (w_steer_control_task), an RTOS task (address in the ~0xbb900 TCB
                     table; dispatched indirectly by the kernel, returns via FUN_000847be `eiret`).
      Sub-dispatch : FUN_00022ca0  (jarl FUN_000413ae decider ; jarl FUN_0003d4a2), a sibling RTOS task
      Scheduled by : OSTM0 base tick (compare 0x1387F=79999 => ~1 ms @ 80 MHz, likely 1 kHz -- the
                     OSTM0 clock is not independently confirmed). Arbitration is phase-gated within it.
    NOTE: this Python runs the whole chain sequentially per call for readability. In the firmware the
    FOC/PWM ISRs (EIIC 0x600/0x970) run asynchronously and far faster than this steering-task tick.
    ---------------------------------------------------------------------------------------------------
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

    st = EpsState(col_torque_avg=0, col_torque_rate=512, motor_rate_raw=0)
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

