#!/usr/bin/env python3
r"""
V108 -- THE HIGH-FREQUENCY AUDIT.  Two reverts to flown-good, plus the instrument fix that
         makes the next drive solvable.  The virgin authority cell was BUILT AND PULLED on its
         own pre-registered null -- see E3.

WHY THIS BUILD EXISTS
---------------------
V107 flew (routes `1b` and `1e`, 988.6 s engaged on 1e, fault-free) and the operator reported a
symptom that had NEVER appeared before in this arc:

    "The audible grinding is still at a HIGHER FREQUENCY AND PITCH -- several hundred Hz,
     potentially around 100 Hz -- between 15 and 40 mph.  The steering wheel visibly oscillates
     back and forth under/around 10 Hz.  It drops off completely at 5-6 mph and below.  Absent at
     high speed straight; RETURNS at high speed during hard turns (a sharp turn at 50 mph).  The
     grinding PERSISTS FOR A FEW SECONDS AFTER OPENPILOT IS DISENGAGED.  The maximum angular
     velocity openpilot can command still feels limited."

Every clause of that is now explained, and the explanation is that THE CAR IS CARRYING TWO
HIGH-FREQUENCY AMPLIFIERS WHOSE PEAKS ARE 5 Hz APART, BOTH PUT THERE BY THIS KIT.

    AMPLIFIER 1 -- gp-0x6b26, the "damper" V106/V107 dosed.  Derived from the image:
        H(f) = 64 * H1(f) * (1 - z^-1) * H2(f)     H1,H2 = one-pole EMAs a0=37/128, a2=22/64
    That is NOT a differencer rising to Nyquist.  It is a BANDPASS.
        f Hz     1     7.79   21.73    40    61.1    100    200    300    499
        |H|    0.40   3.08    7.72   11.15  12.14  10.86   7.15   5.45   4.49
    PEAK 61.1 Hz.  -3 dB span 25.1 -> 153.0 Hz.  NEVER below 4.49x anywhere to Nyquist.
    V106 multiplied it x3.0 uniformly.  V107 delivers x3.0 at creep, x4.19 at 20 km/h and
    **x8.14 at >=90 km/h**.  At 100 Hz the lane runs at 10.86x -- 40 % MORE gain than at the
    21.7 Hz mode it was designed to damp.

    AMPLIFIER 2 -- V105's notch, still on the car, unexamined through V106 and V107.
    Honda ships that biquad with its zero at 55.225 Hz -- a true null, -103 dB.  V105 moved it to
    25.5 Hz.  Measured from the image floats, V105-vs-Honda:
        f Hz     21.7    25.5     30     42      55.2      60      100     200
        ratio   0.489   ~0      0.497  1.718   ~1.4e5   6.091    1.168   0.888
    **V105 is worse than Honda over a contiguous 35.7 -- 126.9 Hz band, peaking at 6.09x
    (+15.7 dB) at 60 Hz**, and it deleted Honda's own null at 55.2 Hz.
    (This kit's own acoustic inversion independently places a high-speed grind excess at
     63.5 Hz [54, 80].  Honda notched exactly there.  V105 removed it.)

THE MEASURED CONSEQUENCE -- THE DAMPER IS A COULOMB RELAY
---------------------------------------------------------
V107's own 427 tap (re-aimed at gp-0x6c2c, the lane's raw pre-gain pre-clamp input) measured it.
Reconstructed P(|gp-0x6b26| = 511) on route `1e`, engaged, LOWER BOUNDS (the wire itself
saturates at 1636.8 counts, so every number is a floor):

        km/h      n eng   p50|c2c|   p90    wire-sat   RAIL DUTY (floor)
        <10        6248        62     461      0.72%       1.60%
        10-25     14950       974    1637     15.46%      33.49%
        25-40     14569       856    1637     10.32%      20.77%
        40-65     30719       549    1290      3.38%       5.04%
        24-64     45733       651    1466      5.81%      10.51%   <- the operator's window
        ALL ENG   99910       261    1378      4.95%       9.69%

    V107's own builder predicted "all below 1 %", worst cell 0.00861, and it REJECTED variant
    RESHAPE_A because 6.2 % at 70-90 km/h was "V80 relay territory".
    THE MEASURED FLOOR IS 9.69 % ENGAGED OVERALL AND 33.49 % AT 10-25 km/h.

    A railed acceleration term is sign(alpha) * 511 -- a bang-bang Coulomb relay.  That is
    precisely `accord-v80-damper-relay-and-grind1-inert`: "the damper became a RELAY ... worst
    grinding ever recorded", with its standing warning "the no-clip gate is blind to
    = ceiling - 17".

    WHY THE SAFETY CASE COULD NOT SEE IT: every duty number behind V107 came off CAN 427, which
    arrives at 49.8 Hz (Nyquist 24.9 Hz).  THE LANE'S ENTIRE -3 dB BAND (25-153 Hz) IS ABOVE THAT
    NYQUIST.  The instrument is structurally blind to the passband of the thing it was sizing.

    RAIL THRESHOLDS, computed from FUN_00036c12's own two-stage shift and verified twice:
        |gp-0x6b26| = clamp( ((|c2c| * |Y_eff(v)|) >> 6) * 273 >> 18 , +-511 )
        km/h  mph  | V106 Y   rails at |c2c| | V107 Y   rails at |c2c| | shrink
           8  5.0  |  24575        1278      |  27294       1151      | 1.11x   <- Y[0] IDENTICAL
          24 14.9  |  16556        1897      |  23543       1334      | 1.42x
          40 24.9  |  13972        2248      |  21714       1446      | 1.55x
          64 39.8  |  10097        3110      |  18971       1655      | 1.88x
          90 55.9  |   5898        5324      |  16000       1963      | 2.71x
    V107 shrank the rail threshold 1.42-2.71x, and Y[0] is BYTE-IDENTICAL to V106 below 20 km/h.
    ** THE SYMPTOM MAP AND THE RAIL-DUTY MAP ARE THE SAME MAP. **

TWO MORE MECHANISMS, BOTH POINTING AT THE SAME BAND
----------------------------------------------------
[a] A PHASE SECTOR CROSSING AT 74.5 Hz.  The standing conclusion "gp-0x6b26 can never RAISE a
    resonance; its phasor is stuck in 180-270 deg" was only ever verified to 40 Hz.  Swept to
    Nyquist, the phasor CROSSES INTO 90-180 deg at 74.5 Hz -- the one sector that raises a
    resonance's frequency while nominally damping it -- and stays there continuously to 500 Hz.
    That is a LINEAR mechanism for a new higher-pitched mode appearing when this term's dose
    goes up, independent of the relay.
[b] ALIASING.  gp-0x4f50, the cascade's raw input, is DECIMATED 4 kHz -> 1 kHz in FUN_00068fbe
    with no anti-alias filter beyond a 2-tap boxcar (~8 % attenuation at 500 Hz).  Content at
    900/1100/1900/2100/2900/3100/3900 Hz folds onto exactly 100 Hz.  Structure code-confirmed;
    the 4 kHz domain has never been measured, so the CONTENT is BELIEF.

AND THE PROOF THAT SURVIVES A CONFOUND: "IT PERSISTS AFTER DISENGAGE"
---------------------------------------------------------------------
The engaged mode records 26/27 -- the ONLY cells V106/V107 dosed -- are not released when
latActive drops.  FUN_00042746 may only flip the mode pair once gp-0x69b0 has ramped to exactly
0, and that ramp is driven by FUN_00028ea6 at 1 kHz using one of five calibrated per-tick rates
(328/66/33/16 ct/tick over a 32768 range = 100/497/993/2048 ms), plus a ~40 ms commit hold
(cal(0xC624E) = 40).  Two prior on-car measurements agree: bit7 = (gp-0x6bd0 != 0) shows
28.4 %/44.9 % duty at 0-1 s after disengage decaying to 0.000 % by 4-6 s (routes 61 and 5d),
replicated on V76 (100 % of 943 manual frames within 5 s, 0 of 40,398 beyond).
=> OUR DOSE STAYS IN FORCE FOR ~1-4 SECONDS AFTER OPENPILOT LETS GO.  Nothing else in the build
has a multi-second latch: Lever B's gate is gp-0x6806 = latActive (same tick), the biquad arms
on the same flag with a 99 % ring-down of 89.7 ms, the 6x gain lane goes idle with the command,
and 0xC64DE's dither is amplitude-zero.  ** The operator's symptom 5 is our own lever's gating
structure, and it is very nearly a single-variable experiment. **

WHAT V108 DOES -- FOUR CAL EDITS AND ONE TELEMETRY BYTE.  NO CODE-CAVE EDIT.
-----------------------------------------------------------------------------
E1  0xC60A8..B7   THE V105 NOTCH -> HONDA'S OWN COEFFICIENTS.  16 bytes, copied byte-for-byte
                  from stock; NO FLOAT IS EVER TYPED (feedback-float-spec-must-be-the-formula:
                  three agents once produced three different byte strings for one coefficient).
                  Removes up to +15.7 dB of loop gain at 60 Hz and restores Honda's 55.2 Hz null.
                  ** THE ARM STAYS ON. **  Unarmed, FUN_000352b4 passes gp-0x6b82 through
                  UNFILTERED (H == 1) -- it is a BYPASS, not a mute -- and Honda's armed notch has
                  max|H| = 1.000033 over 0.05-500 Hz, i.e. it can only ever REMOVE loop gain.
                  Disarming would be worse than Honda at every frequency.  The reverted state is
                  V103/V104's, flown twice, fault-free.
                  COST: x2.05 at 21.7 Hz.  Priced below.

E2  0xD7A5C/6C    gp-0x6b26 Y ROW -> (-29490, -17202, -16000): V106's Y0 AND Y1 EXACTLY,
                  V107's Y2 KEPT.  Measured on route 1e, episode-bootstrapped over 10 episodes,
                  ALL THE RAIL DAMAGE IS AT THE Y1 (20 km/h) KNOT that V107 raised 1.40x:
                      bin      V107 rail duty        V106 same samples     V108 candidate
                      <10      1.68% [0.86,2.58]     1.47% EXACT           1.47% EXACT
                      10-25   32.32% [29.93,35.68]   <= 15.46%             <= 15.46%
                      24-40   21.27% [19.93,22.51]   <= 10.45%             <= 10.45%
                      40-64    4.27% [4.35,6.31]     <=  3.43%             <=  3.43%
                      65-90   <= 0.23%               <=  0.23%             <=  0.23%
                        90+   <= 0.03%               <=  0.03%             <=  0.03%
                  ** >=65 km/h carries NO measurable rail risk on either build, so V107's
                  high-speed dose is KEPT IN FULL (2.71x V106 at 94 km/h) -- it is the half of the
                  reshape that was aimed at V106's own >70 km/h residual and it costs nothing. **
                  🛑 THE ROW IS A TARGETED REVERT, NOT A SOLVED OPTIMUM, AND THAT IS DELIBERATE.
                  The solve could not be run: V106's own clamp threshold EXCEEDS the 1636.8-count
                  wire rail everywhere above ~10 km/h, so the empirical target is itself censored in
                  5 of 6 bins.  Run naively the optimiser drives |Y_eff| to ~19195, exactly where
                  the threshold crosses the rail, and certifies "0.00 % duty" for a row that truly
                  rails 15.46 %.  ** That is V107's own failure reproduced one level up. **  E5 is
                  what makes the next drive able to solve it.  X row untouched; modes 24/25 (MANUAL)
                  and the other 28 records byte-stock.  V106 is the configuration the operator described as
                  "grinding attenuated in all three scenarios" -- the best report in this kit's
                  history -- and the row whose 18-30 Hz ratio CLEARED its own within-drive
                  split-half null, the first band-power result in the kit ever to do so.
                  X row untouched.  Modes 24/25 (MANUAL) and the other 28 records byte-stock.

E3  0xC61BE       *** BUILT, THEN PULLED ON A PRE-REGISTERED NULL.  NOT IN THIS IMAGE. ***
                  The plan was 15360 -> 16384 for +6.7 % of delivered LKAS authority, on a
                  cell never touched in 107 builds.  The sentence a null would license was
                  written before the measurement: 'if achieved rate keeps rising to the top of
                  the command range, nothing in this lane saturates, the clip is idle, and the
                  raise buys zero -- pull it.'  Route 1e, authority-ramp-complete, 93,356
                  frames / 924 s, with |e4tq| p99 = max = 4096 so the region IS exercised:
                      speed     p90 low half   p90 top   ratio   95% CI          knee?
                      10-25         27.0        105.0     3.89   [2.42, 5.48]     NO
                      25-40         25.0         78.0     3.12   [2.22, 4.45]     NO
                      40-64         15.0         43.7     2.91   [2.38, 3.13]     NO
                      64-90          8.0         21.0     2.62   [2.10, 2.62]     NO
                     90-200          7.0         15.0     2.14   [1.67, 2.14]     NO
                  Every CI excludes 1.0 at all five speeds, so a speed-command correlation
                  cannot manufacture or hide it.  ** THE CLIP IS IDLE.  PULLED. **
                  ⚠ Limit on the null, stated so it is not over-read: the clipped quantity is
                  NOT a memoryless function of the command (int32 recursive state gp-0x6cf8 /
                  gp-0x6dd0, 4 accesses each, all inside FUN_00028ea6 or its dead copy, zero
                  external readers or writers), so a clip binding only along particular state
                  trajectories could smear across the command axis instead of showing a sharp
                  knee.  This is strong evidence the clip does not ROUTINELY bind; it is not
                  proof it never can.  The zero-firmware confirmation, if it is ever wanted,
                  is stock UDS DID 0x48AC bytes 7-8 = gp-0x6b38 (RDBI entry 0xB7864, handler
                  0x4E82E, default session, no security, byte-identical in V107): a bound clip
                  pins it at ~2481 against the 3072 clamp, and anything above 2505 falsifies
                  the model outright.  NO CAN OR UDS WAS SENT.
                  KEPT BELOW FOR THE RECORD -- the full pricing, because the cell is still the
                  only never-tried authority lever and the next session should not re-derive it.
                  ORIGINAL RATIONALE, NOW SUPERSEDED BY THE MEASUREMENT:
                  It is a symmetric saturation at 0x2A13E..0x2A15E, UPSTREAM of the 6x gain at
                  0x2A1EE, so the lane's ceiling is (0xC61BE * cal(0xC6CD0)) >> 15:
                      build        gain   out-clamp   reach   % of clamp
                      stock 1x      891       512      417      81.45 %
                      V38-V100 4x  3564      2048     1670      81.54 %
                      V101 8x      7128      4096     3341      81.57 %
                      V102-V107 6x 5346      3072     2505      81.54 %   <- ON THE CAR
                      V108 6x      5346      3072     2673      87.0 %    <- THIS BUILD
                  ** Every gain step this kit ever made raised the OUTPUT clamp and left the
                  INPUT clip at Honda's 15360.  The reach has been 81.5 % on every build since
                  V14.  That is also the mechanism behind the long-unexplained "0xC61B2/0xC61B4
                  are 0 % of the effect": they are inert BECAUSE this clip caps the lane 18.5 %
                  below them. **  Independent confirmation: (15360*891)>>15 = 417, and the kit
                  separately recorded "stock V9's max LKAS command was 417".
                  GATE 1: 8 accesses image-wide, ALL loads, ZERO writers, 4 live in FUN_00028ea6
                  + 4 in dead FUN_0002a93a; no lockstep twin; no ASIL monitor reads it; no
                  0xC5000-block mirror (0xC51BE = 220, not 15360).
                  STRUCTURAL SAFETY: the lane's output passes clamp(+-cal(0xC61B4) = 3072) AFTER
                  the gain, unconditionally.  Raising the clip can only move the lane WITHIN a
                  bound Honda's own downstream clamp already enforces.  16384 reaches 2673 =
                  87.0 %, so 0xC61B4 STILL NEVER BINDS and this stays a pure single-cell edit --
                  no other cell has to move with it, which matters because 0xC61B2/0xC61B4 sit in
                  the SAME int-vs-float lockstep family as 0xC674E, and V27 HARD-FAULTED THE INSTANT
                  THE WHEEL WAS TURNED after doubling one side of that lockstep without the other.
                  ** WHY 16384 AND NOT 18836, WHICH WOULD FILL THE CLAMP.  A SATURATION IS A
                  STABILISER. **  Its describing function N(A) = (2/pi)[asin(C/A) + (C/A)sqrt(1-(C/A)^2)]
                  is 1 below the limit and BELOW 1 above it, so on saturating frames the clip has
                  been REDUCING loop gain -- and raising it gives that reduction back on exactly the
                  most energetic frames.  The distinction "a gain raise scales every frame, a ceiling
                  raise touches only saturating frames" is an EXACT identity in the integer arithmetic
                  for EXCITATION and it FAILS for LOOP GAIN.  V101's failure at 8x was explicitly a
                  loop-gain failure ("the peak MOVING 20.3 -> 23.0 Hz -- a pole moving, not
                  excitation"), so this lever touches the mechanism that hurt.
                  Against the record's own yardstick (|kG| 0.63 @4x, 0.75 @8x, log-interp 0.700 @6x):
                      16384 -> deep-saturation worst case 0.700 x 1.0667 = 0.747
                               <- BELOW the 0.75 that V101 ACTUALLY FLEW
                      18836 -> 0.700 x 1.2263 = 0.859   <- 15 % BEYOND anything ever flown
                  And at 18836 the lane reaches 100.03 % of the 3072 clamp, so BOTH nonlinearities
                  would engage at nearly the same amplitude -- the worst possible arrangement for
                  reading the drive.  16384 keeps a deliberate 13 % margin and ONE nonlinearity in
                  play.  17408 (+13.4 %, worst case 0.737) is the natural second rung IF the clip is
                  ever shown to bind.
                  🛑 RETRACTED BEFORE THIS BUILD WAS CUT, AND DELIBERATELY NOT USED AS A REASON:
                  an earlier draft of this rationale called 16384 "a principled stopping point -- V38
                  gave the E4/E5 taper exactly 16384, so the two ceilings finally agree, closing a
                  nine-build-old miss."  ** THAT IS VOID. **  The taper clamps `gp-0x69ae`, which
                  FUN_00052676 (the CAN 0x0E4 handler) writes as `clamp(wire * -4, +-16384)` at
                  0x5268C/0x526F2/0x52726/0x527C6; with openpilot's STEER_MAX = 4096 that is bounded
                  at 16384 BY CONSTRUCTION.  So V38 set the taper exactly equal to the command's own
                  bound and made it a no-op by design -- V38 was CORRECT AND COMPLETE, there was no
                  miss, and 16384 here is unrelated to 16384 there.
                  ** 16384 IS AN ARBITRARY-BUT-CONSERVATIVE DOSE SET BY THE |kG| ARGUMENT ABOVE, NOT
                  A PRINCIPLED ONE.  It must be described that way. **
                  NOT IN SERIES with anything: 0xC61BC (15360), 0xC61B6 (10240) and 0xC61BA
                  (10240) clamp THREE PARALLEL BRANCHES whose sum can reach 35,559 = 2.32x the
                  clip, so the clip is binding-capable and stays binding across the whole raise.
                  Honda's own budget is "any one branch may saturate, the total shall not exceed
                  15360"; this widens the total and disturbs no branch clamp.
                  ** REACHABILITY IS UNMEASURED.  If the setpoint never reaches 15360 this edit
                  is inert-but-harmless.  Labelled as such to the operator. **  It is NOT
                  reconstructible from logs: the branch computation carries int32 recursive state
                  (gp-0x6cf8, gp-0x6dd0, written at decompile lines 1219-1220 and read at the top of
                  the same 1 kHz tick), so it is not a memoryless function of the 0xE4 command.
                  ⭐ BUT HONDA ALREADY EXPOSES THE ANSWER: gp-0x6b38, the final clamped LKAS output,
                  is at BYTES 7-8 (big-endian) of stock UDS DID 0x48AC -- RDBI table entry 0xB7864,
                  handler 0x4E82E, default session 0xDF, security 0x0F = NONE, length 0x38.  Byte-
                  identical in V107.  Signature: the clip binding pins |gp-0x6b38| at 2481 (80.8 %
                  of the 3072 clamp) at full authority.  FALSIFIER: any observation above 2505
                  refutes this whole model and E3 must be pulled.  ** NO CAN OR UDS IS SENT BY THIS
                  BUILD OR THIS SESSION -- the surface is reported, not used. **

E4  0xC40BC       300 -> 600 (Honda).  The V99 Coulomb ramp normaliser, RETRACTED AS A FIX BY THE
                  SESSION THAT CUT IT, BEFORE IT FLEW: the dose delivers 0.5-1.2 % against Path-2's
                  own ~9 % perceptual floor, 93.1 % of the operator's hands-on frames sit ABOVE the
                  knee where 300 and 600 are arithmetically identical (mean ramp ratio 1.050, not
                  2x), GATE 2 was never closed, and it is NOT engagement-gated so it acts in MANUAL
                  too.  The only within-route friction dose ever flown gives 6-9 Hz engaged/manual
                  2.89x at 600 vs 6.58x at 6000 => MORE friction, MORE ratchet, and 300 is more
                  friction than 600.  Reverting removes a non-Honda cell that has never measured
                  anything and pushes the ratchet's own axis the right way.

E5  0x55E10       sar 3 -> sar 5.  ONE BYTE, TELEMETRY ONLY, AND THE NEXT DRIVE IS UNINTERPRETABLE
                  WITHOUT IT.  The 427 packer is
                      wire = clamp( (min(|src|,65535) * 5) >> sar , 0, 0x3FF )
                  -- the `mul 0x5, r6, r0` at 0x55E06 is in Honda's code and V107's builder print
                  OMITTED IT, reporting full scale 8184 when the truth is 1023 * 2^sar / 5.
                  At sar 3 that is 1636.8 counts, and route 1e SATURATED 4.95 % of engaged samples
                  (15.46 % at 10-25 km/h).  V107's own drive card asked for the clamp duty above
                  70 km/h; at sar 3 the rail threshold there (1963) is ABOVE the wire's ceiling, so
                  THAT QUESTION WAS UNANSWERABLE BY CONSTRUCTION.
                      sar   LSB   full scale   covers V106's 90 km/h rail threshold of 5324?
                        3   1.6      1636.8    NO
                        4   3.2      3273.6    NO
                        5   6.4      6547.2    YES
                  sar 5 is the design criterion "the RAIL must be measurable at every speed", not
                  "clips nothing" -- which is the criterion that produced the 5x error.

NOT DONE, AND WHY -- these are decisions, not omissions
--------------------------------------------------------
* 0xC40DC = 22 (the cascade's second EMA pole, a2 = 22/64) is VIRGIN on all 102 images and is the
  structurally correct fix: lowering it band-limits the lane, moving its 61 Hz peak down onto the
  mode and rolling off the 75-500 Hz skirt.  First-pass arithmetic says halving it to 11 costs
  ~15 % at 21.7 Hz and buys ~48 % at 100 Hz and ~54 % at 300 Hz.
  ** HELD OUT OF V108 pending GATE 1 (it sits in the 0xC40xx observer/plant block, two bytes from
  K1 and 0x20 from the Coulomb normaliser -- its membership in this cascade must be proven from
  the decompile, not from adjacency) and GATE 2 (a slower EMA adds lag; the term must stay inside
  the dissipative sector at 21.7 Hz). **  It is the V109 candidate.
* 0xC40D2 = 204 (K1) KEPT, knowingly.  It is a measured null ("fixed nothing, still only as good
  as V88"), but the sign chain says 204 makes the wheel LIGHTER, so reverting makes it HEAVIER --
  the wrong way for an operator who complains about excess friction and never about lightness.
* 0xC63F6 = 16 ct/tick, the mode-column release rate, would cut the post-disengage hold from
  ~2.05 s to ~0.54 s at 66.  NOT TOUCHED: the same ramp governs ENGAGEMENT, so a faster rate makes
  engagement abrupt; and the tail is a SYMPTOM OF THE RELAY, not an independent defect.  Fixing the
  tail without fixing the relay would only shorten how long you hear it.
* THE CAVE IS BYTE-IDENTICAL TO V107.  Code caves are this kit's ONLY bricking class -- V24, V27
  and V48B all bricked the ECU -- and every success since V29 has been cal-only or a single
  in-place branch/displacement edit.  b5 therefore still means exactly what route a6 measured it
  against, and V108 is 100 % calibration plus one telemetry shift byte.
* 0xC6CD0 = 5346 FROZEN.  It is exactly 6.000x (891 = 1x) and it is the operator's own dose
  decision off a measured curve.  It is also the measured carrier of the 21-27 Hz line, so V108
  must fix the grinding WITHOUT touching it.  "STABILITY BINDS FIRST, AND IT WAS HIT AT 8x."

THE 21-27 Hz RISK, STATED PLAINLY
----------------------------------
E1 raises loop gain at 21.7 Hz by x2.05 on the base-assist lane.  E2 reverts the damper from
V107's row to V106's, which LOWERS the damper's delivered coefficient at 20-90 km/h.  Both move
the 18-30 Hz mode's net loop gain the WRONG way versus V107.  V106 extinguished that mode and
this build must not quietly give it back.  Three things make the risk acceptable, and they are
recorded here so the next reader can attack them:
 1. V105's own flight measured 18-30 Hz band power at 0.769 [0.548, 1.135] -- **a CI spanning 1**
    -- with the session concluding "the mode moved to where the notch costs it LESS, with band
    power CONSERVED ... a describing-function intersection sliding, not attenuation."  The notch
    never delivered 2.05x of margin, so removing it should return a frequency slide, not multiply
    band power.  (BELIEF that removal is symmetric with insertion -- that is the residual risk.)
 2. Only 1.2 % of the engaged <16 km/h 18-30 Hz power ever sat inside V105's own stopband.
 3. V106's damper (gain 3.706 at 21.73 Hz) did not exist when V105 was cut.  The 2.05x is being
    spent into a loop with materially more damping than the one V105 was designed for.
And E2 is a revert TO the row that produced the best operator report in the arc, not away from it.

HOW V108 DIFFERS FROM THE ARC SINCE V38
----------------------------------------
    V38-V52    authority / filters / poles / caves
    V53-V61    telemetry probes and lane mutes
    V62-V73    the rate lane (r24/r26)
    V74-V83a   the base-assist damper
    V84        damper reverted to Honda
    V85-V99    observer / plant-model probes
    V100-V103  the gain ladder + arming the biquad
    V104       c4, a flat lane gain                    FLOWN, NULL
    V105       the biquad's SHAPE                      FLOWN, relocated the mode, never reverted
    V106       gp-0x6b26 Y row x3.0 uniform            FLOWN, EXTINGUISHED the mode at low speed
    V107       gp-0x6b26's SPEED SCHEDULE              FLOWN, made the damper a RELAY
    V108       ** SUBTRACTIVE AND ABOVE 50 Hz **       <- a class this arc has never run
V104 through V107 were four consecutive ADDITIVE builds on one lane, each sized by a 25-50 Hz
instrument.  V108 is the first build in this arc to (a) REMOVE kit-added loop gain rather than add
more, and (b) be designed against the 50-500 Hz band at all -- a band in which this kit has never
measured anything, because every channel it owns is Nyquist-limited below it.  It is also the first
build ever to touch the LKAS request ceiling itself rather than the gain in front of it.

Usage:
    ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares \
    ACCORD_V108_WRITE=rwd python builds/v108_plus/build_v108_tva.py
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
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V108_WRITE", "").strip().lower()
GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = "_v107_V106BASE-GP6B26.RESHAPE_B-TAP.6C2C.SAR3_plain_image.bin"
BASE_SHA = "c32c3ba5da859335fa7637cca59e9ac3e40f8f6cdcb817dd582884be080a0c45"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_addr, rec_y, rec_x = V106B.rec_addr, V106B.rec_y, V106B.rec_x
Y_STOCK = V106B.Y_STOCK                       # (-9830, -5734, -1966)
Y_V106 = V106B.Y_V106                         # (-29490, -17202, -5898)  == x3.0 stock
Y_V107 = (-29490, -24000, -16000)             # RESHAPE_B, what is on the car
Y_V108 = (-29490, -17202, -16000)             # V106's Y0+Y1 (measured good) + V107's Y2 (no rail risk)
X_EXPECT = (0, 1280, 5760)                    # counts, 64 counts/km/h => (0, 20, 90) km/h
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
CLAMP_CAL, MONITOR_TRIP = V106B.CLAMP_CAL, V106B.MONITOR_TRIP    # 0xC407E = 511 ; trip 512

# ---------------------------------------------------------------------------------------------
# THE FIVE EDITS.  Every value here is either read from the STOCK image at build time (E1) or is
# an integer whose derivation is in the docstring (E2-E5).  No float is ever typed.
# ---------------------------------------------------------------------------------------------
BQ_ADDR, BQ_LEN = 0xC60A8, 16          # E1  c1,c2,c3,c4 as 4x float32, little-endian
BQ_ARM_CAL = 0xC649B                   #     the ENABLE byte -- stays 1
BQ_ARM_SITES = (0x35A08, 0x35A09, 0x35A12, 0x35A18)   # V103's arm repoint -- stays as-is

Y_ADDRS = (0xD7A5C, 0xD7A6C)           # E2  modes 26/27 (ENGAGED) Y rows

CLIP_CAL = 0xC61BE                     # E3  the LKAS request clip, UPSTREAM of the 6x gain
CLIP_OLD, CLIP_NEW = 15360, 15360   # E3 PULLED on a pre-registered null -- NOT WRITTEN
GAIN_CAL = 0xC6CD0                     #     5346 = exactly 6.000x (891 = 1x).  FROZEN.
OUT_CLAMP_CAL = 0xC61B4                #     3072.  Must stay > the reach, or it starts binding.
BRANCH_CLAMPS = {0xC61B6: 10240, 0xC61BA: 10240, 0xC61BC: 15360}   # parallel, all byte-stock

COULOMB_CAL = 0xC40BC                  # E4  Coulomb ramp normaliser
COULOMB_OLD, COULOMB_NEW = 300, 600

TAP_SCALER_ADDR = 0x55E10              # E5  low byte of `sar imm5,r6`; imm5 = byte & 0x1F
TAP_SAR_OLD, TAP_SAR_NEW = 3, 5
TAP_SRC_ADDR = 0x55DF2                 #     disp16 of the 427 source load -- UNCHANGED (gp-0x6c2c)
TAP_SRC_EXPECT = 0x93D4                #     gp-0x6c2c
TAP_MUL5_ADDR = 0x55E06                #     `mul 0x5,r6,r0` -- Honda's, must be present

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def lerp_delivered(y, kmh):
    """Honda's LERP in FUN_00036c12 @0x36C60-0x36CB0, integer, truncating."""
    c = int(kmh * 64)
    xs = X_EXPECT
    if c <= xs[0]:
        return y[0]
    if c >= xs[-1]:
        return y[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= c < xs[i + 1]:
            return y[i] + ((y[i + 1] - y[i]) * (c - xs[i])) // (xs[i + 1] - xs[i])
    return y[-1]


def rail_c2c(y, kmh):
    """The |gp-0x6c2c| at which gp-0x6b26 reaches its +-511 clamp.

    gp-0x6b26 = clamp( ((c2c * Y_eff) >> 6) * 0x111 >> 0x12 , +-511 )   [0x36CBE..0x36CCA]
    Net gain is Y_eff * 273 / 2**24.  Solve for c2c at 511.
    """
    g = abs(lerp_delivered(y, kmh)) * 273 / 2 ** 24
    return 511 / g if g else float("inf")


FROZEN = dict(V106B.FROZEN)
FROZEN[GAIN_CAL] = (2, 5346, "0xC6CD0 -- the 6.000x forward LKAS gain.  NEVER lower it.")
FROZEN[OUT_CLAMP_CAL] = (2, 3072, "0xC61B4 -- the post-gain output clamp; E3 must stay under it")
FROZEN[0xC61B2] = (2, 3072, "0xC61B2 -- the arbitration output clamp, tracks the gain")
for _a, _v in BRANCH_CLAMPS.items():
    FROZEN[_a] = (2, _v, f"0x{_a:05X} -- a PARALLEL branch clamp, not in series with 0xC61BE")
FROZEN[0xC40D2] = (1, 204, "K1 -- kept knowingly; reverting makes the wheel HEAVIER")
FROZEN[0xC6C42] = (2, 4, "D for gp-0x4f62; the r24/r26 lane peaks at 125 Hz -- untouched")
FROZEN[0xC643C] = (2, 37, "alpha0 = 37/128, the cascade's FIRST EMA pole -- untouched")
FROZEN[0xC40DC] = (2, 22, "alpha2 = 22/64, the SECOND EMA pole -- HELD OUT, V109 candidate")
FROZEN[BQ_ARM_CAL] = (1, 1, "the biquad ENABLE -- stays ARMED; unarmed is a BYPASS (H == 1)")
# V106's FROZEN table pins the 427 tap at V106's own values.  V107 re-aimed the SOURCE to
# gp-0x6c2c (0x55DF2 low byte 0x7a -> 0xd4) and V108 moves the SCALER (0x55E10 0xa3 -> 0xa5).
# Re-pin both to what THIS build must carry, so they stay asserted rather than merely exempted.
FROZEN[0x55DF2] = (1, 0xD4, "427 SOURCE low byte -- gp-0x6c2c, carried from V107 unchanged")
FROZEN[0x55E10] = (1, 0xA5, "427 SCALER -- sar 5, THIS BUILD (E5)")
FROZEN[COULOMB_CAL] = (2, COULOMB_NEW, "0xC40BC -- REVERTED to Honda's 600 by THIS build (E4)")
FROZEN[CLIP_CAL] = (2, CLIP_OLD, "0xC61BE -- the LKAS request clip.  E3 PULLED; stays Honda-stock")


def assert_frozen(buf, label, extra_exempt=()):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        if a in extra_exempt:
            continue
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got!r}, expected {exp!r} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN) - len(extra_exempt)} FROZEN cells at expected values")


def assert_family(buf, label, engaged_want):
    print(f"\n    dose family 0x{V106B.FRICTION_PTR_ARRAY:05X} ({label})")
    bad = []
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(buf, m)
        want = Y_STOCK if m in MANUAL_MODES else engaged_want
        got, gx = rec_y(buf, m), rec_x(buf, m)
        role = "MANUAL " if m in MANUAL_MODES else "ENGAGED"
        ok = got == want and gx == X_EXPECT
        if not ok:
            bad.append(m)
        print(f"      {OK if ok else BAD} mode {m:2d} {role} 0x{ra:05X} Y = {got}  "
              f"x{got[0] / Y_STOCK[0]:.2f} stock   X = {gx}")
    check(not bad, f"{label}: 4 records as expected (manual STOCK, engaged {engaged_want}, X fixed)")


def build():
    print("=" * 102)
    print("  V108 -- THE HIGH-FREQUENCY AUDIT.  Two reverts to flown-good, one virgin ceiling.")
    print("=" * 102)

    print("\n  [1] LOAD AND PIN THE BASE AND STOCK IMAGES")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(base).hexdigest() == BASE_SHA, f"base is V107 ({BASE_SHA[:16]}...)")
    check(hashlib.sha256(stock).hexdigest() == STOCK_SHA, "stock image sha256 matches the record")
    check(len(base) == len(stock) == 0x100000, "both images are exactly 1 MiB")
    check(walk_all_blocks(bytes(base)) == 0, "base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] PRE-IMAGE -- assert every cell we are about to move is where we think it is")
    check(rd(base, BQ_ADDR, BQ_LEN) != rd(stock, BQ_ADDR, BQ_LEN),
          "  E1: the biquad coefficients on the car DIFFER from Honda's (V105 is still in force)")
    check(rec_y(base, ENGAGED_MODES[0]) == Y_V107 and rec_y(base, ENGAGED_MODES[1]) == Y_V107,
          f"  E2: both engaged records carry V107's RESHAPE_B {Y_V107}")
    check(u16(base, CLIP_CAL) == CLIP_OLD == u16(stock, CLIP_CAL),
          f"  E3 (PULLED): 0x{CLIP_CAL:05X} = {CLIP_OLD} on the car AND in stock -- stays that way")
    check(u16(base, COULOMB_CAL) == COULOMB_OLD and u16(stock, COULOMB_CAL) == COULOMB_NEW,
          f"  E4: 0x{COULOMB_CAL:05X} is {COULOMB_OLD} on the car, {COULOMB_NEW} in stock")
    check(base[TAP_SCALER_ADDR] & 0x1F == TAP_SAR_OLD,
          f"  E5: 0x{TAP_SCALER_ADDR:05X} is sar {TAP_SAR_OLD},r6")
    check(u16(base, TAP_SRC_ADDR) == TAP_SRC_EXPECT,
          "  E5: the 427 source is still gp-0x6c2c -- V108 moves the SCALER only")
    check(rd(base, TAP_MUL5_ADDR, 4) == rd(stock, TAP_MUL5_ADDR, 4),
          "  E5: Honda's `mul 0x5,r6,r0` at 0x55E06 is present and untouched (the x5 V107 omitted)")
    assert_frozen(base, "BASE(V107)", extra_exempt=(COULOMB_CAL, 0x55E10))

    print("\n  [3] E1 -- THE V105 NOTCH -> HONDA'S OWN COEFFICIENTS (16 B, COPIED, NEVER TYPED)")
    honda = rd(stock, BQ_ADDR, BQ_LEN)
    code[BQ_ADDR:BQ_ADDR + BQ_LEN] = honda
    attributed |= set(range(BQ_ADDR, BQ_ADDR + BQ_LEN))
    v105f = struct.unpack_from("<4f", base, BQ_ADDR)
    hondaf = struct.unpack_from("<4f", code, BQ_ADDR)
    print(f"      V105  {bytes(rd(base, BQ_ADDR, BQ_LEN)).hex()}")
    print(f"            c1={v105f[0]:.6f} c2={v105f[1]:.6f} c3={v105f[2]:.6f} c4={v105f[3]:.6f}")
    print(f"      HONDA {bytes(honda).hex()}")
    print(f"            c1={hondaf[0]:.6f} c2={hondaf[1]:.6f} c3={hondaf[2]:.6f} c4={hondaf[3]:.6f}")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(stock, BQ_ADDR, BQ_LEN),
          "  the four coefficients are byte-identical to Honda's -- no float was typed")
    check(code[BQ_ARM_CAL] == 1, "  the biquad stays ARMED (unarmed is a BYPASS, H == 1: worse)")
    for a in BQ_ARM_SITES:
        check(code[a] == base[a], f"  V103's arm repoint at 0x{a:05X} untouched")

    print("\n  [4] E2 -- gp-0x6b26 Y ROW -> V106's, THE ROW THAT EXTINGUISHED THE MODE")
    for a in Y_ADDRS:
        struct.pack_into("<3h", code, a + V106B.REC_Y_OFF - V106B.REC_Y_OFF, *(0, 0, 0)) \
            if False else None
    for m in ENGAGED_MODES:
        ra = rec_addr(code, m)
        ya = ra + V106B.REC_Y_OFF
        struct.pack_into("<3h", code, ya, *Y_V108)
        attributed |= set(range(ya, ya + 6))
    print(f"      {'km/h':>6} {'mph':>5} | {'V107 Y_eff':>10} {'rail |c2c|':>10} | "
          f"{'V108 Y_eff':>10} {'rail |c2c|':>10} | {'headroom':>8}")
    for v in (5, 8, 16, 24, 40, 56, 64, 90):
        print(f"      {v:6.0f} {v / 1.609:5.1f} | {lerp_delivered(Y_V107, v):10d} "
              f"{rail_c2c(Y_V107, v):10.0f} | {lerp_delivered(Y_V108, v):10d} "
              f"{rail_c2c(Y_V108, v):10.0f} | {rail_c2c(Y_V108, v) / rail_c2c(Y_V107, v):7.2f}x")

    check(min(Y_V108) > -32768, "  every Y is a legal signed int16 -- no overflow")
    check(Y_V108[0] == Y_V106[0] and Y_V108[1] == Y_V106[1],
          "  Y0 and Y1 are V106's EXACTLY -- the rail damage was measured to be all at the Y1 knot")
    check(Y_V108[2] == Y_V107[2],
          "  Y2 is V107's -- >=65 km/h rail duty measured <=0.23 %, so the high-speed dose is kept")
    check(Y_V108[0] <= Y_V108[1] <= Y_V108[2], "  the schedule is monotone in speed")

    print("\n  [5] E3 -- 0xC61BE -- PULLED ON A PRE-REGISTERED NULL.  NOT WRITTEN.")
    print("      Route 1e, authority-ramp-complete (>1 s engaged, >10 km/h), 93,356 frames /")
    print("      924 s, |e4tq| p99 = 4096 and max = 4096 so the saturation region IS exercised.")
    print("      p90 achieved |rate_c|, low half (256-1536) vs top (>=2048), episode-bootstrapped:")
    print("        speed     low     top   ratio   95% CI          knee?")
    print("        10-25    27.0   105.0    3.89   [2.42, 5.48]     NO")
    print("        25-40    25.0    78.0    3.12   [2.22, 4.45]     NO")
    print("        40-64    15.0    43.7    2.91   [2.38, 3.13]     NO")
    print("        64-90     8.0    21.0    2.62   [2.10, 2.62]     NO")
    print("       90-200     7.0    15.0    2.14   [1.67, 2.14]     NO")
    print("      Achieved rate is STILL RISING 2.1-3.9x where a bound clip would have pinned it")
    print("      flat, at all five speeds, every CI excluding 1.0.  => THE CLIP IS IDLE AND THE")
    print("      RAISE BUYS ZERO.  The sentence a null would license was written BEFORE the")
    print("      measurement (see the docstring) and it is honoured here.")
    gain = u16(code, GAIN_CAL)
    clamp = u16(code, OUT_CLAMP_CAL)
    reach_old = (CLIP_OLD * gain) >> 15
    reach_new = (CLIP_NEW * gain) >> 15
    print(f"      0x{CLIP_CAL:05X} LEFT AT {CLIP_OLD}; lane reach stays {reach_old} counts = "
          f"{100 * reach_old / clamp:.1f} % of cal(0xC61B4) = {clamp}")
    check(u16(code, CLIP_CAL) == u16(base, CLIP_CAL) == u16(stock, CLIP_CAL) == CLIP_OLD,
          "  0xC61BE is byte-stock AND byte-identical to V107 -- E3 was PULLED, not shipped")
    check(reach_old == 2505 and (15360 * 891) >> 15 == 417,
          "  arithmetic anchored: 2505 at 6x today, and 417 at stock 1x == the recorded V9 maximum")
    for a, want in BRANCH_CLAMPS.items():
        check(u16(code, a) == want and u16(stock, a) == want,
              f"  parallel branch clamp 0x{a:05X} = {want}, byte-stock -- unchanged")

    print("\n  [6] E4 -- 0xC40BC COULOMB RAMP NORMALISER -> HONDA'S 600")
    struct.pack_into("<H", code, COULOMB_CAL, COULOMB_NEW)
    attributed |= {COULOMB_CAL, COULOMB_CAL + 1}
    print(f"      0x{COULOMB_CAL:05X}  {COULOMB_OLD} -> {COULOMB_NEW}   "
          f"friction knee 5.31 -> 10.61 deg/s (back to Honda)")
    check(u16(code, COULOMB_CAL) == u16(stock, COULOMB_CAL),
          "  0xC40BC is byte-identical to Honda")

    print("\n  [7] E5 -- 427 TELEMETRY SCALER sar 3 -> sar 5")
    old_byte = code[TAP_SCALER_ADDR]
    code[TAP_SCALER_ADDR] = (old_byte & 0xE0) | TAP_SAR_NEW
    attributed.add(TAP_SCALER_ADDR)
    print(f"      0x{TAP_SCALER_ADDR:05X}  {old_byte:02x} -> {code[TAP_SCALER_ADDR]:02x}"
          f"        sar {TAP_SAR_OLD},r6 -> sar {TAP_SAR_NEW},r6")
    print(f"      packer: wire = clamp( (min(|gp-0x6c2c|,65535) * 5) >> sar , 0, 0x3FF )")
    for s in (3, 4, 5, 6):
        fs = 1023 * (1 << s) / 5
        print(f"        sar {s}  LSB {(1 << s) / 5:4.1f}  full scale {fs:7.1f}  "
              f"covers V106's 90 km/h rail (5324)?  {'YES' if fs > 5324 else 'no'}")
    check(code[TAP_SCALER_ADDR] & 0x1F == TAP_SAR_NEW, "  imm5 is now 5")
    check(code[TAP_SCALER_ADDR] & 0xE0 == old_byte & 0xE0, "  the opcode bits did not move")
    fs = 1023 * (1 << TAP_SAR_NEW) / 5
    check(fs > rail_c2c(Y_V108, 90),
          f"  full scale {fs:.0f} EXCEEDS THIS build's own worst rail "
          f"({rail_c2c(Y_V108, 90):.0f} at >=90 km/h) -- V108's rail duty is measurable everywhere")
    check(fs > rail_c2c(Y_V106, 90),
          f"  and it also exceeds V106's Y2 rail ({rail_c2c(Y_V106, 90):.0f}) -- so the NEXT drive can"
          f" size a WEAKER candidate row too, which is the failure E5 exists to fix.  sar 4 (fs 3274)"
          f" would cover V108 but NOT that, and sar 3 covers neither.")
    check(rd(code, 0x55D50, 4) == rd(base, 0x55D50, 4),
          "  the 399 packer at 0x55D50 is untouched -- E5 is on the 427 lane only")

    print("\n  [8] POST-IMAGE -- everything that must NOT have moved")
    assert_family(code, "V108", Y_V108)
    for m in MANUAL_MODES:
        check(rec_y(code, m) == Y_STOCK, f"  mode {m} (MANUAL) still Honda stock")
    for m in ENGAGED_MODES:
        check(rec_x(code, m) == X_EXPECT, f"  mode {m} X row untouched {X_EXPECT}")
    check(rd(code, V106B.CAVE_BASE, V106B.CAVE_LEN) == rd(base, V106B.CAVE_BASE, V106B.CAVE_LEN),
          "  THE CAVE IS BYTE-IDENTICAL TO V107 -- no code-cave edit; b5 still means what a6 measured")
    check(s16(code, V106B.B5_OPERAND_B_ADDR) == V106B.B5_OPERAND_B_DISP,
          "  b5's operand B is still gp-0x6b26 -- the dose still reads itself out")
    check(s16(code, CLAMP_CAL) == 511 and 511 < MONITOR_TRIP,
          f"  0xC407E = 511 < {MONITOR_TRIP} -- RULE-11 interlock intact BY CONSTRUCTION")
    assert_frozen(code, "V108", extra_exempt=())
    check(rd(code, 0x2A1F0, 2) == rd(base, 0x2A1F0, 2),
          "  V57's forward-reader repoint untouched (reverting it would put 6x on 4 feedback readers)")
    check(rd(code, 0x3AA96, 1) == rd(base, 0x3AA96, 1) and u16(code, 0xC6446) == 5244,
          "  Lever B (gate + arm 5244) carried -- the kit's only measured fix")
    check(code[0x454FE] == base[0x454FE], "  0x454FE state-4 governor byte carried")

    print("\n  [9] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [10] FULL BYTE DIFF vs V107 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    for lo, hi in runs:
        tag = "CRC" if any(lo <= x < hi for x in
                           (b[1] for b in blocks)) else "payload"
        print(f"      0x{lo:05X}..0x{hi - 1:05X}  {hi - lo:3d} B  {tag}   "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed to an edit")

    print("\n  [11] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V108 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V108-V107BASE-NOTCH.HONDA-GP6B26.Y1REVERT-C40BC.600-TAP.SAR5"
    img_out = plain_image_path(f"_v108_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [12] NOT WRITTEN -- set ACCORD_V108_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
