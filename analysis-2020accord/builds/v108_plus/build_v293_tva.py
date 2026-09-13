# -*- coding: utf-8 -*-
r"""V293 -- TORQUE MODE ON A V282 BASE.  CAL-ONLY.  V279's class, rebased.

BASE            V282  (_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X
                       .FEEDBACK46080.TORQUE.TAP_plain_image.bin, sha256 0ea98d06...)
EDITS           cal cells and cal records only, NOT ONE CODE BYTE:
                  0xC62E6  fb saturation clamp     46080 -> 0      [A]  the loop is opened
                  0xCB7D4  Kd bank, ALL 28 records   var -> 0      [B]  D killed, route 1
                  0xC61B6  D clamp                 10240 -> 0      [B2] D killed, route 2
                  0xCB994  Kp bank, ALL 28 records   var -> 120    [C]  the forward path is rescaled
                  0xC6446  r24 ENGAGED arm          5244 -> 2048   [D]  the 7 Hz lever
plus the 4-byte CRC trailers of the six blocks that own those bytes.  378 bytes differ from V282.

🛑 SOURCES THAT OVERRODE THE ORIGINAL BUILD BRIEF, both 2026-09-13, both folded in here:
   * `docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` (agent `looptrace`) -- the rail is
     NOT 2505; the taper banks are not the ones an earlier draft of this file read; D can be killed
     by the D clamp alone; NEVER mute via 0xC63EA.  Sections 2b, 2d and 6 below.
   * `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` + the orchestrator's ruling -- KP_SCOPE is
     "all", KD_METHOD is "both", r24 is fixed at 2048, and clause A2 rules out KP_FLAT 119.
   Section 2c records what the ORIGINAL brief said and why each point changed.  `--grid` still
   builds the superseded brief preset so the two can be compared byte for byte.

=== 0. WHAT THIS BUILD IS, IN ONE PARAGRAPH ======================================================
Honda's EPS does not take openpilot's 0xE4 command as a torque.  It maps it through an assist map to
an ANGULAR-RATE SETPOINT and closes a PID on measured column rate inside FUN_00028ea6.  openpilot's
own lateral controller is wrapped around that inner loop without knowing it exists.  V293 REMOVES THE
INNER LOOP: with the feedback saturation clamp at ZERO the clamped operand r26 is forced to exactly 0
on every branch, so E = 32*setpoint unconditionally; with Kd at zero the derivative term is exactly 0;
and with Kp flattened to KP_FLAT the forward path becomes a near-linear map from demand index to
delivered torque whose top lands on the SAME peak V282 already delivers.  What openpilot commands is
then a TORQUE, delivered open-loop, and the only closed loop left in the vehicle is openpilot's own.
This is **V279's class, rebased onto V282** -- not a new lever.  V279 (2026-09-02) built the same
three mechanisms on a V268 base and was never flown.

=== 1. THE ARITHMETIC, MIRRORED IN INTEGER PYTHON, WITH THE INSTRUCTION ADDRESSES =================
V850E2 is LITTLE-ENDIAN; `sar` is arithmetic (floors toward -inf), which Python `>>` on int matches.
Every line below was decoded from THE V282 IMAGE'S OWN BYTES by this file's `decode_one`, and the
shift amounts (`sar 0x8` at 0x29E3E, `sar 0x3` at 0x29EEC) were read off the instruction, not
inherited.

    def lkas_rate_pid(sp, x, s_fb, E_prev, cal):
        # ---- the feedback lag, 0x28F86..0x28FA4 -------------------------------------------------
        b     = cal[0xC63EA]                       # 0x28F86 ld.hu 0x73ea,tp,r16   = 1560
        a     = cal[0xC63E8]                       # 0x28F8A ld.h  0x73e8,tp,r9    =  923
        s_new = (a * s_fb >> 10) + (b * x >> 10)   # 0x28F8E/0x28F92 mul ; 0x28F9A/0x28FA0 sar 0xa
                                                   # 0x28FA2 add r7,r9
        r26   = s_fb + s_new                       # 0x28FA4 add r9,r26   THE TWO-SAMPLE SUM
        # ---- 🛑 [A] THE CLAMP.  C = cal[0xC62E6].  THREE BRANCHES, ALL COLLAPSE AT C = 0 --------
        #      0x28FA6 cmp r13,r26 ; 0x28FAC ble +6
        #        r26 >  C :  0x28FAE mov r14,r26            -> r26 =  C
        #        r26 <= C :  0x28FB2 subr r0,r14 (r14 = -C) ; 0x28FB4 cmp ; 0x28FB6 bge +8
        #                      r26 >= -C : keep r26
        #                      r26 <  -C : 0x28FB8 ld.hu ; 0x28FBC subr r0,r26  -> r26 = -C
        r26   = max(-C, min(C, r26))               #  C = 0  =>  r26 == 0 ON ALL THREE BRANCHES
        s_fb  = s_new                              # 0x28FA8 st.w r9,-0x3d30,gp -- THE STATE KEEPS
                                                   #   RUNNING; the store PRECEDES the clamp resolve
        # ---- the error, 0x29D76..0x29D78 --------------------------------------------------------
        E     = 32 * sp - r26                      # 0x29D76 shl 0x5,r16 ; 0x29D78 sub r26,r16
        # ---- P, 0x29E34..0x29E5C ----------------------------------------------------------------
        kp    = lerp(Kp_record, idx)               # 0x29DC6.. the Kp LERP walk (record via 0xCB994)
        P     = (E * kp) >> 8                      # 0x29E36 mul r9,r8 ; 0x29E3E sar 0x8,r8
        P     = max(-PC, min(PC, P))               # 0x29E3A/44/4A/58 ld.hu 0x71bc -> +-15360
        # ---- D, 0x29EE0..0x29F06 ----------------------------------------------------------------
        kd    = lerp(Kd_record, idx)               # 0x29E76.. the Kd LERP walk (record via 0xCB7D4)
        dE    = E - E_prev                         # 0x29EE2 sub r27,r8
        D     = (dE * kd) >> 3                     # 0x29EE4 mul r7,r8 ; 0x29EEC sar 0x3,r8
        D     = max(-DC, min(DC, D))               # 0x29EE8/F2/F8/0x29F02 ld.hu 0x71b6 -> +-10240
        # ---- the sum, the forward gain and the output cap ----------------------------------------
        S     = max(-SC, min(SC, fade * (P + D) >> 8))   # 0x2A13A mulh ; 0x2A13E.. ld.hu 0x71be
        y     = output_lag(S)                            # 0x2A174..0x2A1AC, DC gain 507*2/32/... = 0.990
        T     = max(-OC, min(OC, (y * G) >> 15))         # 0x2A1EE ld.h 0x7cd0 (G) ; 0x2A1F8 0x71b4 (OC)
        return T

With KP_FLAT and the map's Y both known, and with r26 == 0, P collapses to a function of idx alone:

    P(idx) = ((32 * map_lerp(idx)) * KP_FLAT) >> 8        -- reported at [8] FROM THE BUILT BYTES

=== 2. THE THREE MECHANISMS, AND WHY EACH IS SAFE TO STATE =======================================
  [A] FEEDBACK CLAMP 0xC62E6: 46080 -> 0.
      🛑 EVIDENCE, WITH THE METHOD, because this is the claim the whole build rests on:
      (i) **THE CENSUS.**  A raw little-endian byte scan of EVERY 4-byte gp/tp-relative Format-VII
          load/store in [0x13000,0x100000) -- 17,644 of them on V282 -- finds EXACTLY THREE
          accessors of 0xC62E6: 0x28F96, 0x28F9C and 0x28FB8.  All three are `ld.hu` (ZERO-EXTEND,
          so a written 0 reads as 0 and never as a sign trap), all three sit inside the clamp block
          0x28F7C-0x28FC8, there are ZERO writers of any encoding, and no LE32 anywhere in the image
          equals the address.  Positive controls run FIRST so the null is worth something: the same
          scanner finds the 8-site sum clamp, the 7-site P clamp and the forward gain at its one
          known site.  Asserted at [3].  This is a raw BYTE scan, not Ghidra's
          `search_instructions`, which silently undercounts (the trace measures it returning 25 for
          a cell whose true count is 30).
          🛑 THE COUNT IS BASE-SPECIFIC.  On a V292 base it is FIVE, two of them orphaned by the
          cave's jump (trace sec.1.3).  Do not copy the "exactly three" assertion onto a V292 base.
      (ii) **THE BRANCHES.**  The clamp's `cmp / ble / mov / br / subr / cmp / bge / ld.hu / subr`
          is decoded from the base's own bytes at [3b] and mirrored branch for branch.  At C = 0 all
          three arms return 0.  The mirror carries a POSITIVE CONTROL that it also reproduces
          stock's +-7680 and V282's +-46080, so the zero result is the mirror working rather than
          the mirror being degenerate.
      (iii) **THE CROSS-BASE IDENTITY.**  The whole span 0x28F7C-0x28FC8, the E subtraction
          0x29D6C-0x29D84, the P and D stages 0x29E30-0x29F0C and the output/gain span
          0x2A170-0x2A250 are BYTE-IDENTICAL between V268 (V279's base) and V282 -- 0 differing
          bytes in each, asserted at [3c] against the V268 image.  So V279's proof of [A] transfers
          to this base unchanged rather than being re-assumed.
      🛑 **NEVER MUTE VIA 0xC63EA (the input gain `b`).**  It looks equivalent and is not:
      floor(-a/1024) = -1 for every a < 1024, so s = -1 is an ABSORBING state on stock/V282/V291 and
      the feedback would rest at -2 FOREVER, not 0 (trace sec.4a).  Only a V292 base, whose cave
      carries the `sar` residues, removes that absorbing state.  V293 has no cave.  [10] asserts
      both pole cells byte-identical, and a mutation that sets b := 0 is in the mutation test.
  [B] Kd -> 0.  With the feedback dead, dE = 32*d(setpoint) is a pure SETPOINT KICK: one demand-index
      count of movement near the top of the map is dE = 32*344/80 = 137, and at V282's Kd = 128 that
      is D = (137*128)>>3 = 2192 counts of torque from a SINGLE COMMAND STEP, IN THE SUM DOMAIN.
      🛑 UNIT TRAP, the kit's recurring one (adversary C's DEFECT C6-1; the same ×6.13 was also missed
      on V292's r24 fold): 2192 / 2505 = 87 % compares a SUM-domain count to an OUTPUT-domain peak --
      an overstatement of x6.13 (= 32768/5346, the motor gain).  In CONSISTENT units, through the
      forward gain ((D*5346)>>15), D is ~357 DELIVERED counts = 14.5 % of the 2461 delivered peak
      (14.3 % of the 15360 SUM ceiling).  The DIRECTION survives -- D is a real feedforward kick from
      a single command step -- but the MAGNITUDE that motivates Kd -> 0 is six times smaller than a
      naive cross-domain read gives.  Zeroing Kd makes D = (dE*0)>>3 = 0 EXACTLY, at every amplitude,
      with no clamp involved.
      Asserted two ways at [10]: the byte diff count, and a SEMANTIC check that the Kd LERP reads 0
      at every demand index 0..240 on every covered slot.
      KD_SCOPE = "all" (V279's precedent, the default) zeroes every distinct record of the 0xCB7D4
      bank -- 28 records, 112 u16 cells; "slot7" zeroes only the live record 0xE511C (4 cells).
  [C] Kp FLAT at 120 on ALL 28 RECORDS (the orchestrator's ruling; KP_SCOPE "slot7" and "live8"
      remain as switches).  V282 already carries Kp FLAT -- V281 rev 3's KP.FLAT.Y0 -- so this is a
      LEVEL change on an already-flat schedule, never a reshaping.
      🛑 V281 rev 3 flattened all 28 records each to ITS OWN Y[0], so V282's bank reads
      205 / 248 / 266 / 307 depending on the slot, NOT 248 everywhere.  Writing one KP_FLAT into all
      28 is therefore a DIFFERENT operation from what V282 did, and it is the one that ships.
      **Why global:** the fb clamp is ONE GLOBAL CELL and Kp is PER-SLOT, so a selector that is ever
      not 7 must land on the SAME linear surface rather than on zero feedback at a larger Kp.  From
      the V282 image, at fb = 0, the demand index at which P FIRST RAILS -- the point above which
      that slot delivers PEAK TORQUE and its map goes inert:
          slot 0, 4   Kp 205  -> rails at idx 140  (58 % of full demand)
          slot 3, 7   Kp 248  -> rails at idx 116  (48 %)
          slot 1, 6   Kp 266  -> rails at idx 108  (45 %)
          slot 8, 9   Kp 248  -> rails at idx 106  (44 %)   (map Ytop 1128, not 1032)
          ANY slot AT KP_FLAT 120 -> rails at idx 239 (100 %)        <-- what V293 builds
      The selector was MEASURED 7 on the V276 wire and the record says it maxes at 9, so the
      off-slot case is a CONTINGENCY, not a live defect -- the ruling closes it anyway, for 236 more
      payload bytes than the slot7 scope (378 vs 145 total).
      [5] prints this table from the base image on every run, per-slot map ceiling included.
  [B2] D CLAMP 0xC61B6 -> 0 -- the SECOND, INDEPENDENT route to D = 0, and the default.
      The D clamp block 0x29EE8..0x29F06 is the SAME three-branch `cmp / ble / mov / subr / cmp /
      bge / ld.hu / subr` idiom as the fb clamp, so a zero bound forces D to exactly 0 on every
      branch -- decoded and mirrored at [3d] against the same positive control.  The cell has SEVEN
      accessors image-wide, FOUR live (the clamp block) and THREE in the dead twin island; zero
      writers.  It is ONE halfword in the SAME 0xC6FFC CRC page as the fb clamp, where the Kd bank
      route costs 112 halfwords across five more pages.
      **KD_METHOD** picks the route: "both" (the ruling -- bank AND clamp, so one wrong byte in
      either cannot resurrect D, which is what the prereg's A1 clause demands), "bank" (V279's
      route alone, what the original brief asked for), "dclamp" (the clamp alone, the cheapest).
      [10] asserts D == 0 BEHAVIOURALLY, by driving the built surface with dE = +-1,000,000, and
      reports which of the two cells is carrying it.
  [D] r24 ENGAGED arm 0xC6446 -> 2048.  The whole ladder is on the [0b] grid: 5244 = V282 unchanged,
      4725 = V291/V292's dose, 4451 = the design agent's criterion-exact value, 2048 = the shipped
      dose, 512 = Honda stock.
      🛑 **THE 2048 CHOICE IS THE ORCHESTRATOR'S, NOT THE DESIGN AGENT'S, AND THE REASONING IS ON
      RECORD** in `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`, quoted here so the build
      carries it: *"Dose fixed by the orchestrator after `DESIGN-V293-TORQUE-MODE-2026-09-13.md` and
      before any image existed: the design's gate73 collapses to 1.19*(arm/5244) with the servo gone
      and 4451 restores exactly 1.010 (the design agent's recommendation); the orchestrator took
      2048 instead because (i) the same model under-predicted V292's measured 5-9 Hz cost
      three-fold (predicted x1.03-1.10, wire x2.9-4.3 route-normalised), so a criterion-exact arm
      carries no margin against the operator's loudest symptom; (ii) 2048 is the record's priced
      lever ("7.3 Hz ring 0.98 -> 0.48, no margin or authority cost", `GRINDING-DEEP-ANALYSIS-
      2026-09-03` sec.2-3); (iii) the design's both-poles family shows removing r24 RAISES zeta
      (20 Hz) in torque mode (+0.04...+0.18 paired, 96-100 % of plants) and the broader family's
      marginal 21-23 Hz pole at 5244 clears below ~2622 -- so the 20 Hz price of the cut is nil here
      and nowhere else.  BELIEF that 2048 is the better hedge; the adversarial B surface scores 4451
      and 2048 side by side."*
      🛑 This is the one edit that is NOT part of the torque-mode claim -- a separate lever on a
      separate lane -- and with the LKAS rate loop open it is the ONLY rate-fed term left in the
      EPS.  Its sign at 20 Hz is disputed in the record (sec.4b).  At 2048 a `gp-0x671d` latch event
      collapses it to the 1024 arm, i.e. x0.5 rather than the x0.195 it was at 5244.

=== 2c. WHAT THE ORIGINAL BRIEF SAID, AND WHY EVERY POINT CHANGED ================================
Recorded so the change is auditable rather than silent.  `--grid` builds both presets.

  |                | ORIGINAL BRIEF   | SHIPPED (the ruling) | why                                  |
  |----------------|------------------|----------------------|--------------------------------------|
  | KP_SCOPE       | slot7            | **all 28**           | the fb clamp is ONE GLOBAL cell, so   |
  |                |                  |                      | the torque map must be global too. A  |
  |                |                  |                      | selector that is ever not 7 must land |
  |                |                  |                      | on the same linear surface, not on    |
  |                |                  |                      | zero feedback at a 205-307 Kp railing |
  |                |                  |                      | at 44-58 % of demand.  [5] prints it. |
  | 0xC61B6 D clamp| frozen at 10240  | **0**, KD_METHOD     | prereg A1 FAILs if D is not exactly   |
  |                |                  | "both"               | zero "with EITHER cell alone".  The   |
  |                |                  |                      | bank alone does not satisfy it.       |
  | r24 arm        | 5244 (unchanged) | **2048**             | fixed by the orchestrator in the      |
  |                |                  |                      | prereg after the design agent's       |
  |                |                  |                      | report; 4451 was the design's         |
  |                |                  |                      | criterion-exact value and 2048 the    |
  |                |                  |                      | hedge.  The whole ladder is on [0b].  |
  | KP_FLAT        | 119 or 120       | **120**              | prereg A2 FAILs a rail differing from |
  |                |                  |                      | V282's by one count or more.  119     |
  |                |                  |                      | delivers 2460 vs V282's 2461.  The    |
  |                |                  |                      | 119 rows stay on the grid as the      |
  |                |                  |                      | control that the CLAMP pins the rail. |
  | the rail       | "2505, unchanged"| **2461**             | 2505 omits the always-on x254/256     |
  |                |                  |                      | taper AND the output lag.  Sec.2d.    |
  | the taper      | record 0xE5404   | **0xCBB54 x 0xCBAE4  | an earlier draft of this file read    |
  |                | (bank 0xCBA04)   | or 0xCBBC4**         | the DRIVER-TORQUE cliff, whose Y[0]   |
  |                |                  |                      | is ALSO 254 -- right scalar, wrong    |
  |                |                  |                      | record.  Corrected against the trace. |

=== 2d. 🛑 THE RAIL IS 2461, NOT 2505, AND THE TRACE'S 2462 IS ONE COUNT HIGH ====================
Three conventions have been quoted for the same number.  [10] prints all of them from the bytes.

  * **2505** -- (sum clamp x gain) >> 15, clamped.  No taper, no output lag.  This is what V279,
    V282, V292 and the first draft of this file all printed.  It is a CEILING, not a delivery.
    🛑 NEVER QUOTE IT AS A DELIVERY.  It survives here only as `T_ceil`, so the number can be
    recognised when it appears in an older docstring.
  * **2462** -- the trace's sec.4a.  Adds the always-on taper and the output lag's LINEAR DC
    2*507/((1024-992)*32) = 0.99023, giving y = 15091 and T = 2462.
  * **2461** -- what this script ships, and what the BYTES do.  The output lag is an integer
    recursion with two `sar 0xa` floors, and it has an INTERVAL of fixed points, not one.  Started
    from the cold-boot state 0 (the .data copy loop 0x1476C-0x14794 walks flash [0x86260,0x8AB18)
    into RAM from 0xFEDF11B0 -- CITED from the trace sec.3.6/6, not re-derived), the lag settles at
    y = 15088, and EVERY reachable fixed point in the interval gives T = 2461.  The linear y = 15091
    is not a reachable integer state.

  The 1-count gap is the SAME floor bias V292's cave removed from the FEEDBACK lag.  **V292 did not
  correct the OUTPUT lag**, and V293 does not either -- it is inherited, identical on both images,
  and it therefore cannot affect the prereg's A2 clause, which compares V293's rail to V282's.
  Both read 2461.  Asserted at [10], with the linear value computed alongside so the gap is visible
  rather than rounded away.

=== 2e. THE ALWAYS-ON TAPER, AND THE DISPUTE THIS BUILD DOES NOT HAVE TO SETTLE ==================
From the trace sec.2.4, re-read from the V282 image by this script at [7b] and [10]:

    factor = ((A * B) & 0xFFFF) >> 8        then    S = (factor * S) >> 8
    A in {0xCBB54, 0xCBC34}  on |bar-derivative|      B in {0xCBAE4 (C), 0xCBBC4 (D)}  on SPEED

  * A and B are **byte-identical record for record on all 28 slots** (asserted), so the `bVar1`
    selector only ever chooses between the two SPEED tapers.
  * At rest A(0) = 255 and both C(0) and D(0) = 255, so the factor is ((255*255)&0xFFFF)>>8 = **254
    -- an always-on x0.9922 with no driver torque and no speed.**  It is never unity.
  * 🛑 **RESOLVED 2026-09-13, AFTER THIS SCRIPT WAS FIRST WRITTEN: TABLE D (0xCBBC4) IS LIVE.**
    The prereg's erratum (adversary A's decompile) reports the selector is `gp-0x6803`, the 0xE4
    SET_ME_X00 field openpilot sends as 0 -- so the KIT MEMORY was right and the tracer's C reading
    was wrong.  The erratum also corrects A2's wording: the bytes carry ONE stage at 0x2A13x, not
    two, whose at-rest value is 254/256 because BOTH halves return 255 at rest.
    [10] still prints the surface under BOTH tables, because the difference is large with speed and
    the drive read must be conditioned on it: at v = 64 the factor is 163 (C) vs 76 (D), a delivered
    rail of 1579 vs 736.  **V293 touches NEITHER record**, and at rest they are INDISTINGUISHABLE,
    so the resolution changes nothing about this build's at-rest claim -- it changes what the lane
    delivers on the road, identically on V282 and V293.

=== 2b. THE MEASURED SURFACE -- every number below READ FROM THE BUILT IMAGE at [10] =============
The shipped dose: KP_FLAT 120, r24 2048, KD_METHOD both, KD_SCOPE all, KP_SCOPE all.  `T` is the
BYTE-EXACT delivery -- taper x254/256, output lag, gain, output cap.  `T_ceil` is the old convention
and is NOT a delivery (sec.2d).  🛑 COLUMN CONVENTION (adversary C's §2b/§4(c) labelling note): the
three right-hand columns `V282 fb=0` / `@10 deg/s` / `@20 deg/s` are ALSO `T`, byte-exact, on the
V282 image -- NEVER `T_ceil` -- so e.g. 854 at idx 40 and -379 at idx 0 are deliveries, not ceilings.

    idx    map Y    P (V293)      S       T   T_ceil |  V282 fb=0   @10 deg/s   @20 deg/s
      0        0           0      0       0        0 |         0        -379        -763
     40      172        2580   2559     413      420 |       854         476          92
     80      344        5160   5119     826      841 |      1708        1330         946
    120      515        7725   7664    1237     1260 |      2461        2180        1796
    160      688       10320  10239    1653     1683 |      2461        2461        2461
    200      860       12900  12799    2067     2104 |      2461        2461        2461
    240     1032  15480->15360  15240    2461     2505 |      2461        2461        2461

Four things that table says and prose would not:
  * **V293's surface is a STRAIGHT LINE in demand index with the SAME RAIL as V282** -- T(240) =
    2461 on both images.  P touches the 15360 clamp only at idx 239-240.  At KP_FLAT 119 it never
    touches it and the rail is 2460, one count low, which is what the prereg's A2 clause rules out.
  * **V282 AT fb = 0 rails from idx 116**, i.e. it would deliver PEAK TORQUE from 48 % of demand
    upward and the top half of its map would be INERT.  That is a PRE-EXISTING fact of V282, not
    something torque mode creates -- and it is the single number that makes [C] necessary rather
    than cosmetic: with the loop open, V282's Kp 248 is a 2.07x over-gain on the bottom half.
  * **The V282 columns at 10 and 20 deg/s of wheel rate go NEGATIVE at low demand** (-379 / -763 at
    idx 0).  That is the rate feedback doing its job -- opposing a moving wheel.  V293 removes it,
    and those columns collapse onto the fb = 0 column at every wheel rate.  Sec.4(a) is that risk.
  * **The D term V293 removes is large and is mostly FEEDFORWARD.**  The trace measures V282's D
    clamp already railing at +-10240 on 0.7 % of ticks -- 67 % of the sum ceiling -- purely from the
    100 Hz command staircase, before any wheel motion.  One demand-index count near the map top is
    dE = 137, and at Kd = 128 that is D = 2192 counts from a single command step.
The fb operand itself, through the integer filter with the BUILT clamp cell: 0 / 2434 / 4908 on V282
at 0 / 10 / 20 deg/s (linear 2b/(1024-a) = 30.8911 predicts 0 / 2471 / 4943), and 0 / 0 / 0 on V293.

=== 3. THE SENTENCE A NULL LICENSES -- WRITTEN BEFORE THE DRIVE ==================================
The instrument is already on the wire and costs this build nothing: CAN 427 (0x1AB) carries the
DELIVERED LANE TORQUE, `wire = (sign(T) << 9) | (|T| >> 3)`, T = gp-0x6b38, packed at 0x55DF0
(V279's [D], carried by every build since V280 rev 2, asserted byte-identical at [7]).  The 0x14A
cave's b4-b7 rungs are likewise untouched (cave hash e9596ad9), so the r24 comparator instrument
keeps V282's meaning.

  * **THE EDIT-LIVE IDENTITY.**  On V293 the delivered torque must be a FUNCTION OF THE COMMAND
    ALONE: `T_tap == f(cmd) * taper` on every engaged, in-taper, ramped frame, with NO dependence on
    wheel rate.  If T still moves with wheel rate at a fixed command, THE EDIT IS NOT LIVE and
    nothing below is licensed.  The prereg pre-registers this as a regression: R^2 of |427 tap| on
    f(cmd)*fade goes -4.82 (V282) -> +0.92 (V293), residual 349 -> 47 counts.
  * **THE FEEDBACK IS DEAD** if `sign(T) == -sign(0xE4 cmd)` agreement is ~1.00 over qualifying
    frames.  ~0.5 means it is NOT dead.  (Sign convention measured on V278 rev 3.)
  * **T SATURATING BELOW THE MAP'S TOP** means the map is not the live setpoint source -- V279's own
    pre-registered null.  At KP_FLAT 120 the P clamp is reached only at idx >= 239, so on V293 the
    tap should ride the command linearly all the way up.  🛑 On V282 it rails from idx 116, so this
    is the first build on which the top half of the map is not inert -- the tap will LOOK different
    above half demand even if nothing about the symptom changes.
  * **T == 0 while engaged with cmd != 0**, outside taper-closed and ramp-low frames: gp-0x6b38 is
    not the lane output or is gated.  Do not trust any other conclusion from that drive.
  * **THE CLASS-CLOSING NULL.**  If the 18-22 Hz ring's amplitude and ring-down are UNCHANGED with
    the loop open on every frame and the identity holding, the 20 Hz object is not the LKAS loop's,
    and the whole in-loop class V38 -> V293 is CLOSED.  That is the sentence this build exists to
    be able to write.
  * If the tap reads clean AND the car oscillates at 1-4 Hz, that is the V276 signature -- the OUTER
    loop -- and the fix is the fork preset, not the firmware.  The drive stops.

=== 4. 🛑 THE RISK STATEMENT, PLAINLY, BEFORE THE DRIVE ==========================================
  (a) **THE EPS SUPPLIES NO RATE DAMPING AT ALL.**  Not a reduction -- a removal by construction.
      V276 cut the fraction of oscillation time in which the lane OPPOSES the wheel from 0.94 to
      0.57, and the combined loop (EPS + openpilot's follower) then rang at 3.9 Hz.  V293 takes that
      fraction to ZERO.  Whether the car is stable depends ENTIRELY on openpilot's tune and the
      column's mechanics; openpilot's Honda tune was fitted THROUGH this rate loop.
  (b) **THE r24 LANE IS THE ONLY RATE-FED TERM LEFT, AND V293 CUTS IT TOO.**  With the LKAS rate
      loop open, r24 (0xC6446) is the sole surviving rate feedback in the EPS -- and the shipped
      dose moves it 5244 -> 2048 at the same time.  The record disagrees with itself on its 20 Hz
      sign: `accord-r24-pumps-at-7hz-and-damps-at-20hz` says it DAMPS at 20 Hz, while
      `grind_loop_shape.py` sec.G measured 5244 -> 512 improving both bands.  **NOT RESOLVED.**  The
      r24 arm inversion is also pre-existing and unchanged: `gp-0x671d` is a saturating rising-edge
      latch, and on any post-V280 image a latch event COLLAPSES r24 to the 1024 arm -- at 2048 that
      is x0.5, not the x0.195 it was at 5244.  Model r24 as BIMODAL, never as a single gain.
  (c) **AUTHORITY MOVES BOTH WAYS, AND WHICH WAY DEPENDS ON WHETHER THE WHEEL IS MOVING.**  Read
      from the built bytes at [10]:
        - at a STALLED wheel (fb = 0 on both images) V293 delivers LESS than V282 below idx 116 --
          413 vs 854 at idx 40, 826 vs 1708 at 80 -- because Kp fell 248 -> 120.  A 2.07x CUT.
        - at 10-20 deg/s of wheel rate V282's delivery COLLAPSES and REVERSES SIGN at low demand
          (-379 at idx 0, 10 deg/s) while V293's is unchanged.  Against a MOVING wheel V293 is the
          stronger of the two at low demand, and it is the one that never opposes.
        - at the TOP both deliver 2461.  The rail is pinned BY CONSTRUCTION.
      So "authority rises" and "authority falls" are BOTH true depending on wheel rate.  The honest
      one-line statement is: **V293 makes delivery a function of the COMMAND ALONE.**
  (d) 🛑 **DWELL AT THE RAIL RISES EVEN THOUGH THE RAIL DOES NOT.**  Today the lane backs off as the
      wheel follows; in torque mode it holds the commanded torque for as long as the command is
      held, however fast the wheel is already moving.  Peak is unchanged, **time at peak is not**.
      The trace names this as its ONE open item that could return "do not flash" (sec.7.5): it did
      not locate or read an EME-class monitor that integrates sustained motor effort.  `FUN_0004595a`
      is an instantaneous comparator, not an integrator -- but that is one monitor, not a census.
      **UNRESOLVED.  This is the prereg's D1 clause and it is the adversarial pass's to close.**
  (e) **THE OVERRIDE TAPER IS BYTE-STOCK** -- all 224 records, asserted at [7].  The grip escape is
      unchanged.  But see sec.2e: WHICH speed taper is live is disputed, and the two differ by
      more than 2x at 64 on the speed axis.  That changes what the lane delivers on the road for
      BOTH builds equally, so it cannot change this build's claim -- and it must condition the read.
  (f) **CAL-ONLY.**  No code byte changes, so V293 is OUTSIDE the kit's only bricking class
      (V24/V27/V48B were all code caves).  Asserted as a full-coverage diff at [7].

=== 5. CLASS OF BUILD -- HOW IT DIFFERS FROM THE RECENT ARC ======================================
  * V288 was a REFERENCE-SIDE cave (a setpoint pre-filter); it flew and the grinding was UNCHANGED,
    so the excitation-side class is exhausted.  V289 was an IN-LOOP FILTER (a 20.04 Hz notch); it
    flew, removed the 20 Hz mode entirely, and a DIFFERENT pre-existing 15-17 Hz pole took its
    margin.  V291/V292 are LOOP-OPENING BY POLE MOVE -- the fb-lag corner 16.5 -> 9.94 Hz.  V292
    flew today and hit two of its own revert signatures; the operator reports grinding still
    present and the stutter WORSE.
  * **V293 opens the loop ALL THE WAY, by CLAMP rather than by POLE.**  Not a larger dose of the
    V291 lever: a different mechanism in the same direction, and the terminal point of it.  Where
    V292 made the feedback arithmetic exact, V293 deletes the feedback.
  * 🛑 **IT IS NOT A NEW LEVER.**  V279 built this structure on a V268 base on 2026-09-02 and was
    NEVER FLOWN, so the class is UNTESTED, not falsified.  No flown build has ever zeroed the LKAS
    rate feedback; the clamp has flown at 7680, 15360 and 46080, a three-point ladder, all non-zero.
    What differs this time: (i) the base is V282, which already carries the linear x6 map, the
    46080 clamp, the 0x14A r24-comparator cave and the 427 delivered-torque tap, so V293 needs FIVE
    cal cells where V279 needed 28 map records + 28 Kp records + 28 Kd records + a 34-byte packer
    rewrite; (ii) the instrument is already flying and has been read on four drives; (iii) the rail
    is pinned to V282's byte-exact 2461 rather than to a recomputed ceiling; (iv) V279's map was
    x2.79, V293's is x6; (v) the symptom being chased is grinding and the high-angle stutter, where
    V279's stated target was the 3.9 Hz crossover.  **The honest framing for the operator: "V279 was
    this, at a x2.79 map; V293 is V279's structure at V282's x6 map, with Kp rescaled so the map is
    not inert above half demand."**
  * V279's map linearisation is NOT repeated -- V282's map is ALREADY linear (Y/X = 4.30 at every
    knot), which is why Kp does the whole rescale here and the map records stay byte-stock.

=== 6. WHAT THIS SCRIPT DOES *NOT* ASSERT ========================================================
  1. **THE 8 COUNTS PER DEG/S SCALE.**  Every deg/s figure here inherits it from the record; the
     trace sec.7.1 marks it BELIEF and names the next step (decompile FUN_00041464).  It affects the
     LABEL on the wheel-rate columns of [10], never the delivered surface.
  2. **Ts = 1 ms.**  EVIDENCE-BY-CONSISTENCY only, never a scheduler read (trace sec.7.2).  Nothing
     in this build depends on it -- V293 changes no pole.
  3. **WHICH SPEED TAPER IS LIVE** was open when this file was written and is now RESOLVED to D
     (0xCBBC4) by the prereg's erratum -- selector `gp-0x6803`, the 0xE4 SET_ME_X00 field.  This
     script did not re-derive that; it is cited.  At rest the two tables are indistinguishable, so
     nothing in the at-rest surface depended on it.
  4. **THE SUSTAINED-EFFORT INTERLOCK.**  Sec.4(d).  This is the one item that could return "do not
     flash" and it is NOT closed here.
  5. **ON-CAR STABILITY.**  GATE 2 is not met by any static argument in this file: the loop this
     build opens is the one whose phase margin previously existed.  Sec.4(a), stated, not bounded.
  6. **THAT SLOT 7 IS LIVE ON THE OPERATOR'S CAR TODAY.**  It was MEASURED 7 on the V276 wire.  With
     KP_SCOPE "all" the question stops mattering for the delivered surface, which is the point of
     the ruling; [5] prints what each slot would deliver if it were not 7.
  7. **REGISTER-INDIRECT WRITERS.**  Every "zero writers" result here comes from raw displacement
     scans, which cannot see a store through a pointer.  The trace's .data boot values corroborate
     but do not close it.
"""
import contextlib
import hashlib
import io
import os
import struct
import sys
import zlib
from pathlib import Path

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, ANALYSIS_ROOT                # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
GP_BASE, TP_BASE = 0xFEDF8000, 0xBF000
WRITE_MODE = os.environ.get("ACCORD_V293_WRITE", "").strip().lower()
MAX_PATH = 259
SUPERSEDE_PREFIX = "SUPERSEDED-DO-NOT-FLASH-"

# ---- the base -------------------------------------------------------------------------------------
BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080"
             ".TORQUE.TAP_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
# V279's own base, present for the [3c] cross-base identity check.  Optional -- skipped if absent.
V268_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
V268_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
# 🛑 V282's own rwd -- NEVER touched by this script; recorded so a stray write can be spotted.
V282_RWD_SHA = "618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22"

# ---- [A] the feedback clamp -------------------------------------------------------------------------
FB_CELL, FB_V282, FB_NEW = 0xC62E6, 46080, 0
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)          # the three ld.hu readers -- ALL of them, censused at [3]
FB_BLOCK_LO, FB_BLOCK_HI = 0x28F7C, 0x28FC8     # the whole filter + clamp span
FB_STATE_STORE, FB_STATE_STORE_B = 0x28FA8, bytes.fromhex("644fd1c2")   # st.w r9,-0x3d30,gp
FB_SUM_SITE, FB_SUM_B = 0x28FA4, bytes.fromhex("c9d1")                  # add r9,r26
E_SUB_SITE, E_SUB_B = 0x29D78, bytes.fromhex("ba81")                    # sub r26,r16
E_SHL_SITE, E_SHL_B = 0x29D76, bytes.fromhex("c582")                    # shl 0x5,r16
FB_A_CELL, FB_A, FB_B_CELL, FB_B = 0xC63E8, 923, 0xC63EA, 1560
FB_X_SAT = 12000

# ---- [B] Kd ------------------------------------------------------------------------------------------
KD_PTR, KD_N, KD_ZERO = 0xCB7D4, 4, 0
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)

# ---- [C] Kp ------------------------------------------------------------------------------------------
KP_PTR, KP_N = 0xCB994, 5
LIVE_KP_REC, LIVE_KP_X, LIVE_KP_Y = 0xE5378, (0, 68, 112, 136, 208), (248,) * 5

# ---- [B2] the D CLAMP -- an OPTIONAL SECOND, INDEPENDENT cell that forces D = 0 ---------------------
# 🛑 NOT in the build brief; REQUIRED by `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`, which
#    lists 0xC61B6 10240 -> 0 as an edit ("D = 0 by a second, independent cell") and makes A1 a FAIL
#    if "D !=~ 0 for any dE with EITHER cell alone".  DCLAMP_NEW = 10240 reproduces the brief exactly;
#    DCLAMP_NEW = 0 reproduces the pre-registration.  The clamp block 0x29EE8..0x29F06 is the SAME
#    three-branch idiom as the fb clamp, so a zero bound forces D to 0 on every branch -- decoded and
#    mirrored at [3d], with the same positive control.
DCLAMP_CELL, DCLAMP_V282 = 0xC61B6, 10240
DCLAMP_SITES = (0x29EE8, 0x29EF2, 0x29EF8, 0x29F02)          # the four LIVE readers
DCLAMP_ISLAND = (0x2ADD4, 0x2ADDC, 0x2ADEC)                  # the dead twin's three
DCLAMP_CHOICES = (10240, 0)
# KD_METHOD -- how D is forced to zero.  "both" is the default (the orchestrator's ruling): the Kd
# bank AND the D clamp, two independent cells, either of which alone is sufficient.
#   "bank"   = V279's route: 28 records x 4 Y knots, 112 halfwords, adds the 0xE4xxx-0xE8xxx pages
#   "dclamp" = ONE halfword in the SAME 0xC6FFC page as the fb clamp -- strictly cheaper
#   "both"   = both, so a single wrong byte in either cannot resurrect D
KD_METHODS = ("both", "bank", "dclamp", "none")
KD_METHOD_DCLAMP = {"both": 0, "bank": DCLAMP_V282, "dclamp": 0, "none": DCLAMP_V282}
KD_METHOD_BANK = {"both": True, "bank": True, "dclamp": False, "none": False}

# ---- [D] the r24 engaged arm -------------------------------------------------------------------------
R24_CELL, R24_V282 = 0xC6446, 5244
R24_LOAD, R24_LOAD_B = 0x3AC08, bytes.fromhex("e5574774")
R24_DOSES = {5244: "V282 -- UNCHANGED", 4725: "V291/V292's dose (-9.90 %)",
             4451: "the prereg ladder's middle rung (-15.13 %)",
             2048: "THE ORCHESTRATOR'S FIXED DOSE (prereg 2026-09-13); the record's 7 Hz lever",
             512: "Honda stock"}

# ---- the forward path, frozen and asserted -----------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
LIVE_MAP_REC = 0xE502C
LIVE_MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
LIVE_MAP_Y = (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032)
LIVE_SLOT = 7                           # record 11 TVCA4 -- MEASURED on the V276 wire
LIVE_SLOTS = (0, 1, 3, 4, 6, 7, 8, 9)   # the selector maxes at 9; 10-27 are DEAD
P_CLAMP, SUM_CLAMP, D_CLAMP, GAIN_CELL, OUT_CAP = 0xC61BC, 0xC61BE, 0xC61B6, 0xC6CD0, 0xC61B4
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1
LAG_A_CELL, LAG_B_CELL = 0xC63EC, 0xC63EE
# 🛑 THE POST-PID TAPER, per the loop tracer (TRACE-2026-09-13-lkas-pid-tracked-quantity.md sec.2.4):
#       factor = ((A * B) & 0xFFFF) >> 8   then   S = (factor * S) >> 8
#    A in {0xCBB54, 0xCBC34} on the |bar-derivative| axis; B in {0xCBAE4 (C), 0xCBBC4 (D)} on SPEED.
#    A and B are BYTE-IDENTICAL record for record on all 28 slots (asserted at [7b]), so the `bVar1`
#    selector only ever chooses between the two SPEED tapers C and D.  At rest both return 255, so
#    the factor is ((255*255)&0xFFFF)>>8 = 254 -- an ALWAYS-ON x254/256 with no driver torque and no
#    speed.  🛑 WHICH SPEED TAPER IS LIVE IS DISPUTED (tracer sec.7.4: the tracer reads C, kit memory
#    says D).  [10] computes the surface under BOTH and prints both; V293 touches neither.
TAPER_A, TAPER_B_ALT, TAPER_C, TAPER_D = 0xCBB54, 0xCBC34, 0xCBAE4, 0xCBBC4
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924, TAPER_A, TAPER_B_ALT, TAPER_C, TAPER_D)
# the earlier draft of this file used 0xE5404 (bank 0xCBA04, the DRIVER-TORQUE override cliff, X
# 70/72/78/80 Y 254/234/12/0).  Its Y[0] is ALSO 254, so it gave the right scalar for the wrong
# reason.  Corrected 2026-09-13 against the tracer.  That bank stays byte-stock and unread here.
# .data cold boot -- CITED from the tracer sec.3.6/sec.6, NOT re-derived: the copy loop at
# 0x1476C-0x14794 walks flash [0x86260, 0x8AB18) into RAM from 0xFEDF11B0, so gp-0x3d30 (the fb
# state, flash 0x89380) and gp-0x3d2c (flash 0x89384) both boot to ZERO.  EVIDENCE, not BELIEF.
BOOT_LOOP, BOOT_FLASH_LO, BOOT_FLASH_HI, BOOT_RAM = (0x1476C, 0x14794), 0x86260, 0x8AB18, 0xFEDF11B0
FB_STATE_RAM, FB_STATE_SRC = 0xFEDF42D0, 0x89380
PACK_LO, PACK_HI = 0x55DF0, 0x55E12     # the CAN-427 delivered-torque tap (V279 [D], carried since V280r2)
PACK_V282 = bytes.fromhex("2437c8940648bfff643c0a30a3329f4ac94a09312046ff03003a0000000000000000")
T_STORE_SITE, T_STORE_B = 0x2A23C, bytes.fromhex("640fc894")            # st.h r1,-0x6b38,gp
CAVE14A_LO, CAVE14A_HI, CAVE14A_SHA8 = 0xC4B34, 0xC4BD8, "e9596ad9"
CAVE14A_HOOK, CAVE14A_HOOK_B = 0x55C0E, bytes.fromhex("86ff26ef")
FWD_GAIN_REPOINT = (0x2A1F0, bytes.fromhex("d07c"))                     # ld.h 0x7cd0,tp,r7
ISLAND_LO, ISLAND_HI = 0x2A30E, 0x2B422                                 # the dead twin

FROZEN = {
    0xC61B2: 3072, 0xC61B4: 3072,       # forward tracking clamp / OUTPUT cap
    0xC61B8: 102,                       # post-lag deadband
    0xC61BA: 10240,                     # integrator anti-windup
    0xC61BC: 15360,                     # P clamp
    0xC61BE: 15360,                     # post-gain SUM clamp
    0xC61F6: 3,                         # Coulomb deadband on the r24 lane
    0xC61F8: 1024, 0xC61FA: 5530,       # the gp-0x671d latch RELEASE / SET thresholds
    0xC62E4: 4,                         # error deadband -- feeds the INTEGRAL path only (Ki = 0)
    0xC63E6: 0,                         # Ki -- ships at ZERO
    0xC63E8: 923, 0xC63EA: 1560,        # fb-lag pole (state keeps running; only the OPERAND is zeroed)
    0xC63EC: 992, 0xC63EE: 507,         # OUTPUT-lag pole
    0xC6440: 2048, 0xC6442: 1024, 0xC6444: 512, 0xC6448: 1024, 0xC644A: 1024,
    0xC6500: 771,                       # DTC maturation count
    0xC674E: 5120, 0xC6750: 5120,       # EME soft-limit quad
    0xC675A: 0x10000 - 5120, 0xC675C: 0x10000 - 5120,
    0xC6768: 5120, 0xC676A: 5120, 0xC676C: 5120,
    0xC6AE6: 2048, 0xC6B12: 98, 0xC6B26: 256,
    0xC6CD0: 5346,                      # the private forward LKAS gain -- the x6
}
EME_FLOATS = {0xC6598: 5.0, 0xC659C: 5.0, 0xC65AC: -5.0, 0xC65B0: -5.0,
              0xC65C4: 5.0, 0xC65C8: 5.0, 0xC65CC: 5.0}

# ---- the dose grid ------------------------------------------------------------------------------------
KP_CHOICES = (119, 120)
R24_CHOICES = (5244, 4725, 4451, 2048, 512)
# "none" touches no record at all.  It exists ONLY for the zero-edit control at [0] and is
# REJECTED whenever dose_check is on, so it can never reach a flight candidate.
KD_SCOPES = ("all", "slot7", "none")
KP_SCOPES = ("slot7", "live8", "all", "none")
# 🛑 TWO PRESETS, because the brief and the pre-registration disagree.  See sec.2c of the docstring.
BRIEF = dict(kp_flat=120, r24_arm=5244, kd_scope="all", kp_scope="slot7", kd_method="bank")
PREREG = dict(kp_flat=120, r24_arm=2048, kd_scope="all", kp_scope="all", kd_method="both")
# 🛑 THE ORCHESTRATOR'S RULING, 2026-09-13, supersedes the brief on both points:
#    KP_SCOPE = "all" (the fb clamp is one global cell, so the torque map must be global too) and
#    KD_METHOD = "both" (the Kd bank AND the D clamp).  DEFAULT now == PREREG.
DEFAULT = dict(PREREG)

OK, BAD = "[PASS]", "[FAIL]"


# =======================================================================================================
#  ASSERTION MACHINERY + CENSUS
#  S = SUBSTANTIVE  -- a wrong edit could fail it AND it is not entailed by an earlier assertion
#  V = VACUOUS      -- entailed by the base sha256 (reads only `base`) or by an earlier assertion here
#  T = TAUTOLOGICAL -- a readback of a value this script just wrote
#  🛑 V291's script reported 377 SUBSTANTIVE and an independent auditor counted 67.  The rule applied
#     here is ENTAILMENT, not call sites: the full-coverage diff at [6] entails every byte-identity
#     check that follows it, so those are V and say so in the message.
# =======================================================================================================
class Run:
    def __init__(self, quiet=False, collect=False):
        self.n = 0
        self.ok = 0
        self.census = {"S": 0, "V": 0, "T": 0}
        self.quiet = quiet
        self.collect = collect          # mutation mode: record EVERY failure instead of stopping
        self.failures = []

    def check(self, cond, msg, kind="S"):
        assert kind in self.census
        self.n += 1
        self.census[kind] += 1
        if cond:
            self.ok += 1
        if not self.quiet:
            print(f"      {OK if cond else BAD} [{kind}] {msg}")
        if not cond:
            self.failures.append((kind, msg))
            if not self.collect:
                raise SystemExit(f"ASSERTION FAILED: {msg}")

    def say(self, s=""):
        if not self.quiet:
            print(s)


def qwalk(fn, img):
    """`walk` / `walk_all_blocks` print 50 lines each and have no quiet flag.  Same return value."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(img)


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


def rec(b, p):
    """(n, X, Y) for a LERP record: [n][X_0..X_{n-1}][Y_0..Y_{n-1}], all halfwords."""
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def y_off(p, n, k):
    return p + 2 + 2 * n + 2 * k


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def lerp(X, Y, x):
    """The firmware's integer LERP, 0x29DC6.. (Kp) / 0x29E76.. (Kd) / 0x29CFE.. (map).
    The hardware divide truncates toward zero; every record this build touches or depends on has a
    NON-NEGATIVE slope (the map rises, Kp and Kd are flat), so trunc == floor on all of them.
    Asserted per record at [4]/[5]/[7]."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X) - 1):
        if X[i] <= x <= X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])
    raise AssertionError


# =======================================================================================================
#  AN INDEPENDENT V850E2 DECODER -- written from the ISA field layout, NOT by inverting an encoder.
#  Confirmed instruction-for-instruction against GHIDRA's V850 decoder on stock instances the kit has
#  already published (V292's ENC_CONTROLS list).  It RAISES on anything it cannot resolve.
# =======================================================================================================
_F1 = {0x00: "mov", 0x01: "not", 0x02: "divh", 0x03: "jmp", 0x04: "satsubr", 0x05: "satsub",
       0x06: "satadd", 0x07: "mulh", 0x08: "or", 0x09: "xor", 0x0A: "and", 0x0B: "tst",
       0x0C: "subr", 0x0D: "sub", 0x0E: "add", 0x0F: "cmp"}
_F2 = {0x10: "mov", 0x11: "satadd", 0x12: "add", 0x13: "cmp", 0x14: "shr", 0x15: "sar",
       0x16: "shl", 0x17: "mulh"}
_F6 = {0x30: "addi", 0x31: "movea", 0x32: "movhi", 0x33: "satsubi", 0x34: "ori", 0x35: "xori",
       0x36: "andi", 0x37: "mulhi"}
_CC = {0x0: "bv", 0x1: "bl", 0x2: "be", 0x3: "bnh", 0x4: "bn", 0x5: "br", 0x6: "blt", 0x7: "ble",
       0x8: "bnv", 0x9: "bnl", 0xA: "bne", 0xB: "bh", 0xC: "bp", 0xD: "bsa", 0xE: "bge", 0xF: "bgt"}


def _rn(r):
    return {0: "r0", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}.get(r, f"r{r}")


def decode_one(buf, off):
    """Return (length, mnemonic, operand_text, fields).  Raises on an unresolvable encoding."""
    hw1 = struct.unpack_from("<H", buf, off)[0]
    reg1, opc, reg2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, (hw1 >> 11) & 0x1F
    if (hw1 & 0x0780) == 0x0580:                                    # Format III  Bcond
        d = (((hw1 >> 4) & 0x7) | (((hw1 >> 11) & 0x1F) << 3)) << 1
        if d & 0x100:
            d -= 0x200
        return 2, _CC[hw1 & 0xF], f"{off + d:#x}", dict(target=off + d)
    if opc in _F1:
        return 2, _F1[opc], f"{_rn(reg1)},{_rn(reg2)}", dict(reg1=reg1, reg2=reg2)
    if opc in _F2:
        return 2, _F2[opc], f"{reg1:#x},{_rn(reg2)}", dict(imm5=reg1, reg2=reg2)
    if (hw1 >> 6) & 0x1F == 0x1E:                                   # jr / jarl / ld.bu
        hw2 = struct.unpack_from("<H", buf, off + 2)[0]
        if hw2 & 1:
            disp = sext16((hw2 & 0xFFFE) | ((hw1 >> 5) & 1))
            return 4, "ld.bu", f"{disp:#x},{_rn(reg1)},{_rn(reg2)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        d = ((hw1 & 0x3F) << 16) | hw2
        if d & (1 << 21):
            d -= (1 << 22)
        if reg2 == 0:
            return 4, "jr", f"{off + d:#x}", dict(disp=d, target=off + d)
        return 4, "jarl", f"{off + d:#x},{_rn(reg2)}", dict(disp=d, target=off + d, reg2=reg2)
    if opc in _F6:
        imm = struct.unpack_from("<H", buf, off + 2)[0]
        return 4, _F6[opc], f"{imm:#x},{_rn(reg1)},{_rn(reg2)}", dict(imm16=imm, reg1=reg1, reg2=reg2)
    if opc in (0x38, 0x39, 0x3A, 0x3B, 0x3F):
        hw2 = struct.unpack_from("<H", buf, off + 2)[0]
        if opc == 0x38:
            return 4, "ld.b", f"{sext16(hw2):#x},{_rn(reg1)},{_rn(reg2)}", dict(disp=sext16(hw2), reg1=reg1, reg2=reg2)
        if opc == 0x3A:
            return 4, "st.b", f"{_rn(reg2)},{sext16(hw2):#x},{_rn(reg1)}", dict(disp=sext16(hw2), reg1=reg1, reg2=reg2)
        disp = sext16(hw2 & 0xFFFE)
        if opc == 0x39:
            return 4, ("ld.w" if hw2 & 1 else "ld.h"), f"{disp:#x},{_rn(reg1)},{_rn(reg2)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        if opc == 0x3B:
            return 4, ("st.w" if hw2 & 1 else "st.h"), f"{_rn(reg2)},{disp:#x},{_rn(reg1)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        if hw2 & 1:
            return 4, "ld.hu", f"{disp:#x},{_rn(reg1)},{_rn(reg2)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        if (hw2 & 0x07FF) == 0x0220:
            return 4, "mul", f"{_rn(reg1)},{_rn(reg2)},{_rn((hw2 >> 11) & 0x1F)}", dict(reg1=reg1, reg2=reg2)
        raise ValueError(f"0x{off:05X}: opc 0x3F hw2 0x{hw2:04X} -- UNRESOLVED, refusing to guess")
    raise ValueError(f"0x{off:05X}: hw1 0x{hw1:04X} (opc 0x{opc:02X}) -- UNRESOLVED, refusing to guess")


_SCAN_CACHE = {}
_ORBIT_CACHE = {}


def scan_rel_cached(buf):
    k = hashlib.sha256(buf).hexdigest()
    if k not in _SCAN_CACHE:
        _SCAN_CACHE[k] = scan_rel(buf)
    return _SCAN_CACHE[k]


def scan_rel(buf):
    """Every 4-byte gp/tp-relative Format-VII load/store in [START,END).  Returns
    (site, base, disp, kind, abs_addr, dst_reg).  This is the RAW BYTE SCAN that Ghidra's
    `search_instructions` silently undercounts -- it scans bytes, not analysed instructions."""
    out = []
    for a in range(START, END - 3, 2):
        hw1 = struct.unpack_from("<H", buf, a)[0]
        reg1, opc, reg2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, (hw1 >> 11) & 0x1F
        if reg1 not in (4, 5) or opc not in (0x38, 0x39, 0x3A, 0x3B, 0x3F):
            continue
        hw2 = struct.unpack_from("<H", buf, a + 2)[0]
        if opc == 0x38:
            d, kind = sext16(hw2), "ld.b"
        elif opc == 0x3A:
            d, kind = sext16(hw2), "st.b"
        elif opc == 0x39:
            d, kind = sext16(hw2 & 0xFFFE), ("ld.w" if hw2 & 1 else "ld.h")
        elif opc == 0x3B:
            d, kind = sext16(hw2 & 0xFFFE), ("st.w" if hw2 & 1 else "st.h")
        else:
            if not (hw2 & 1):
                continue
            d, kind = sext16(hw2 & 0xFFFE), "ld.hu"
        base = TP_BASE if reg1 == 5 else GP_BASE
        out.append((a, "tp" if reg1 == 5 else "gp", d, kind, (base + d) & 0xFFFFFFFF, reg2))
    return out


def hits_at(S, addr):
    return sorted([h for h in S if h[4] == addr], key=lambda h: h[0])


def scan_abs(buf, val):
    return [a for a in range(START, END - 3) if struct.unpack_from("<I", buf, a)[0] == val]


# =======================================================================================================
#  THE DELIVERED SURFACE -- integer, mirroring the decoded arithmetic exactly.
# =======================================================================================================
def fb_ss(a, b, x, clamp):
    """The fb filter's EXACT integer steady state at a constant input x, run to its periodic orbit.
    Mirrors 0x28F86..0x28FA4 plus the 0x28FA6 clamp.  Returns (r26_mean_floor, r26_at_orbit)."""
    s = 0
    seen, hist = {}, []
    for k in range(200000):
        if s in seen:
            cyc = hist[seen[s]:]
            return sum(cyc) // len(cyc), cyc
        seen[s] = len(hist)
        s_new = (a * s >> 10) + (b * x >> 10)
        out = max(-clamp, min(clamp, s + s_new))
        hist.append(out)
        s = s_new
    return hist[-1], hist[-1:]


def out_lag_orbit(la, lb, S):
    """The output lag's EXACT integer orbit, 0x2A174..0x2A1AC, STARTED FROM THE COLD-BOOT STATE 0
    (the .data copy loop proves gp-0x3d3c's neighbours boot to zero; cited, see BOOT_LOOP):
           s' = (la*s >> 10) + (lb*S >> 10) ;  y = (s + s') >> 5
    🛑 The floor map has an INTERVAL of fixed points, not one, so the settled y depends on the
    trajectory.  Returns (y_from_cold_start, y_lo, y_hi) where lo/hi bracket the fixed points that
    are reachable at all.  At S = 15240 this is (15088, 15088, 15090): the LINEAR DC 0.99023 gives
    15091.17, so the byte-exact rail is ONE COUNT BELOW the linear one.  Both are reported."""
    key = (la, lb, S)
    if key in _ORBIT_CACHE:
        return _ORBIT_CACHE[key]
    s_, seen, hist = 0, {}, []
    for _k in range(500000):
        if s_ in seen:
            break
        seen[s_] = len(hist)
        s2 = (la * s_ >> 10) + (lb * S >> 10)
        hist.append((s_ + s2) >> 5)
        s_ = s2
    orbit = hist[seen.get(s_, len(hist) - 1):] or hist[-1:]
    cold = orbit[-1]
    # the reachable fixed-point interval: every L with L == (la*L>>10) + (lb*S>>10)
    step = lb * S >> 10
    lo = hi = None
    for L in range(max(0, cold * 16 - 64), cold * 16 + 96):
        if L == (la * L >> 10) + step:
            lo = L if lo is None else lo
            hi = L
    ys = ((lo + lo) >> 5, (hi + hi) >> 5) if lo is not None else (cold, cold)
    _ORBIT_CACHE[key] = (cold, min(ys), max(ys))
    return _ORBIT_CACHE[key]


def taper_factor(img, bank_b, bar_deriv=0, speed=0):
    """factor = ((A * B) & 0xFFFF) >> 8  -- the tracer's sec.2.4, read from the image's own records.
    A is on the |bar-derivative| axis, B on speed.  At rest both are 255 and the factor is 254."""
    nA, XA, YA = rec(img, u32(img, TAPER_A + 4 * LIVE_SLOT))
    nB, XB, YB = rec(img, u32(img, bank_b + 4 * LIVE_SLOT))
    return ((lerp(XA, YA, bar_deriv) * lerp(XB, YB, speed)) & 0xFFFF) >> 8


def surface(img, slot, idx, fb, cal, fade=None, dE=0):
    """The delivered lane torque at a constant demand index and a constant feedback operand, read
    from `img`.  Mirrors the tracer's sec.3.1 integer chain EXACTLY, with the instruction addresses:

        E = 32*sp - fb                               0x29D76 shl 0x5 ; 0x29D78 sub r26,r16
        I = 0                                        Ki = [0xC63E6] = 0
        P = clamp((E*Kp) >> 8, [0xC61BC])            0x29E36 mul ; 0x29E3E sar 0x8
        D = clamp((dE*Kd) >> 3, [0xC61B6])           0x29EE4 mul ; 0x29EEC sar 0x3
        S = (I>>7) + P + D                           0x29F18 sar 0x7,r2 ; 0x29F1E ; 0x29F24
        S = (factor * S) >> 8                        the ALWAYS-ON taper, 254/256 at rest
        S = clamp(S, [0xC61BE])                      0x2A13E..0x2A160
        y = output_lag(S)                            0x2A174..0x2A1AC
        T = clamp((y * gain) >> 15, [0xC61B4])       0x2A1EE ld.h gain ; 0x2A1F8 ld.hu cap

    `T_ceil` is kept only as the number the record USED to quote (no taper, no output lag).  It is
    NOT a delivery and the docstring says so."""
    fade = cal["FADE"] if fade is None else fade
    mX, mY = rec(img, u32(img, MAP_PTR + 4 * slot))[1:]
    kX, kY = rec(img, u32(img, KP_PTR + 4 * slot))[1:]
    dX, dY = rec(img, u32(img, KD_PTR + 4 * slot))[1:]
    sp = lerp(mX, mY, idx)
    kp, kd = lerp(kX, kY, idx), lerp(dX, dY, idx)
    E = 32 * sp - fb
    P_raw = (E * kp) >> 8
    P = max(-cal["PC"], min(cal["PC"], P_raw))
    D = max(-cal["DC"], min(cal["DC"], (dE * kd) >> 3))
    S = max(-cal["SC"], min(cal["SC"], (fade * (P + D)) >> 8))
    y, y_lo, y_hi = out_lag_orbit(cal["LA"], cal["LB"], S)

    def clampT(v):
        v = ((v + 0x8000) & 0xFFFF) - 0x8000
        return max(-cal["OC"], min(cal["OC"], (v * cal["G"]) >> 15))

    SUM_nofade = max(-cal["SC"], min(cal["SC"], P + D))
    return dict(sp=sp, kp=kp, kd=kd, E=E, P_raw=P_raw, P=P, D=D, rail=(P_raw != P), S=S,
                T=clampT(y), T_lo=clampT(y_lo), T_hi=clampT(y_hi),
                T_ceil=max(-cal["OC"], min(cal["OC"], (SUM_nofade * cal["G"]) >> 15)))


def read_cal(img, bank_b=None):
    return dict(PC=u16(img, P_CLAMP), SC=u16(img, SUM_CLAMP), DC=u16(img, D_CLAMP),
                G=s16(img, GAIN_CELL), OC=u16(img, OUT_CAP),
                LA=s16(img, LAG_A_CELL), LB=u16(img, LAG_B_CELL),
                FADE=taper_factor(img, bank_b or TAPER_C))


# =======================================================================================================
#  THE TAG -- 🛑 DERIVED FROM THE INTEGERS THAT ARE WRITTEN TO THE IMAGE, never a typed literal.
#  V291's defect D2: a hard-coded tag string let a copy with r24 = 4722 ship under the 4725 name.
#  [11] re-derives this WHOLE NAME from the BUILT IMAGE'S OWN BYTES and asserts it is the name used.
# =======================================================================================================
def make_tag(kp_flat, kp_scope, kd_scope, r24, fb, dclamp, kd_method):
    # 🛑 adversary C DEFECT C5-1 fix: the DCLAMPn token is DERIVED from the D-clamp INTEGER actually
    # written (never a typed literal) -- a build that ever ships dclamp != 0 must rename itself.
    dctag = f"DCLAMP{dclamp}"
    kdtag = {"both": f"BANK.{kd_scope.upper()}+{dctag}", "bank": f"BANK.{kd_scope.upper()}",
             "dclamp": dctag, "none": "NONE"}[kd_method]
    return (f"V293-V282BASE-TORQUEMODE.FB{fb}"
            f"-KD0.{kdtag}"
            f"-KP.FLAT.{kp_flat}.{kp_scope.upper()}"
            f"-R24.{r24}"
            f"-MAP.LINEAR.TO6X.TORQUE.TAP")


def kp_slots(scope):
    return {"none": (), "slot7": (LIVE_SLOT,), "live8": LIVE_SLOTS,
            "all": tuple(range(N_SLOTS))}[scope]


def kd_slots(scope):
    return {"none": (), "slot7": (LIVE_SLOT,), "all": tuple(range(N_SLOTS))}[scope]


def independent_rebuild(base, kp_flat, kp_scope, kd_scope, r24, fb, dclamp):
    """A second, minimal implementation with none of build()'s bookkeeping, using a DIFFERENT CRC
    block locator (FF.crc_block_map instead of V53.owning_block).
    🛑 HONEST LABEL: it shares this module's CONSTANTS, so it cannot catch a wrong constant.  It is a
    CRC-LOCATION and SPLICE cross-check only."""
    img = bytearray(base)
    touched = set()
    struct.pack_into("<H", img, FB_CELL, fb)
    touched |= {FB_CELL, FB_CELL + 1}
    if dclamp != u16(base, DCLAMP_CELL):
        struct.pack_into("<H", img, DCLAMP_CELL, dclamp)
        touched |= {DCLAMP_CELL, DCLAMP_CELL + 1}
    if r24 != u16(base, R24_CELL):
        struct.pack_into("<H", img, R24_CELL, r24)
        touched |= {R24_CELL, R24_CELL + 1}
    for s in kd_slots(kd_scope):
        p = u32(img, KD_PTR + 4 * s)
        n = u16(img, p)
        for k in range(n):
            o = y_off(p, n, k)
            if u16(img, o) != KD_ZERO:
                struct.pack_into("<H", img, o, KD_ZERO)
                touched.add(o)
    for s in kp_slots(kp_scope):
        p = u32(img, KP_PTR + 4 * s)
        n = u16(img, p)
        for k in range(n):
            o = y_off(p, n, k)
            if u16(img, o) != kp_flat:
                struct.pack_into("<H", img, o, kp_flat)
                touched.add(o)
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


# =======================================================================================================
#  BUILD
# =======================================================================================================
def build(kp_flat=None, r24_arm=None, kd_scope=None, kp_scope=None, fb_new=None, kd_method=None,
          dclamp=None, quiet=False, do_rwd=True, base_bytes=None, mutate=None, dose_check=True,
          collect=False):
    """mutate: a callable(code, attributed) applied AFTER the edits and BEFORE the checks, used by the
    mutation test at [12] to prove the substantive assertions actually bite."""
    kp_flat = DEFAULT["kp_flat"] if kp_flat is None else kp_flat
    r24_arm = DEFAULT["r24_arm"] if r24_arm is None else r24_arm
    kd_scope = DEFAULT["kd_scope"] if kd_scope is None else kd_scope
    kp_scope = DEFAULT["kp_scope"] if kp_scope is None else kp_scope
    fb_new = FB_NEW if fb_new is None else fb_new
    kd_method = DEFAULT["kd_method"] if kd_method is None else kd_method
    # the D clamp follows KD_METHOD unless it is overridden explicitly (the mutation test does that)
    dclamp = KD_METHOD_DCLAMP[kd_method] if dclamp is None else dclamp
    kd_bank = KD_METHOD_BANK[kd_method]
    if not kd_bank:
        kd_scope = "none"
    R = Run(quiet, collect)
    ck, say = R.check, R.say
    TAG = make_tag(kp_flat, kp_scope, kd_scope, r24_arm, fb_new, dclamp, kd_method)
    IMG_NAME = f"_v293_{TAG}_plain_image.bin"
    RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"

    say("=" * 118)
    say(f"  V293 -- TORQUE MODE on a V282 base.  CAL-ONLY.  fb clamp -> {fb_new} / KD_METHOD "
        f"{kd_method} (bank {kd_scope}, D clamp {dclamp}) / Kp flat {kp_flat} ({kp_scope}) / "
        f"r24 {r24_arm}")
    _now = dict(kp_flat=kp_flat, r24_arm=r24_arm, kd_scope=kd_scope, kp_scope=kp_scope,
                kd_method=kd_method)
    say("  == " + ("the ORCHESTRATOR'S RULING / pre-registration preset" if _now == PREREG else
                   "the ORIGINAL BUILD BRIEF preset (superseded)" if _now == BRIEF else
                   "a dose on the grid, matching neither preset exactly"))
    say("=" * 118)

    # ---------------------------------------------------------------------------------------------
    say("\n  [1] BASE = V282")
    base = bytearray(base_bytes if base_bytes is not None else
                     Path(plain_image_path(BASE_NAME)).read_bytes())
    ck(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V282 base sha256 matches", "S")
    ck(qwalk(walk_all_blocks, bytes(base)) == 0, "base CRC chain 50/50  [entailed by the sha256]", "V")
    ck(qwalk(walk, bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49  [entailed]", "V")
    for a, v in FROZEN.items():
        ck(u16(base, a) == v, f"base 0x{a:05X} == {v}  [entailed]", "V")
    ck(u16(base, FB_CELL) == FB_V282, f"base 0x{FB_CELL:05X} == {FB_V282} (V280 rev 2's clamp)  [entailed]", "V")
    ck(u16(base, R24_CELL) == R24_V282, f"base 0x{R24_CELL:05X} == {R24_V282}  [entailed]", "V")
    ck(u16(base, DCLAMP_CELL) == DCLAMP_V282,
       f"base 0x{DCLAMP_CELL:05X} (D clamp) == {DCLAMP_V282}  [entailed]", "V")
    ck(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240,
       "base demand-index clamp +-240 (BYTES, 0xC64F0/F1)  [entailed]", "V")
    if dose_check:
        ck(kp_flat in KP_CHOICES, f"KP_FLAT {kp_flat} is one of {KP_CHOICES}", "S")
        ck(r24_arm in R24_CHOICES,
           f"R24_ARM {r24_arm} is one of {R24_CHOICES} ({R24_DOSES.get(r24_arm)})", "S")
        ck(kd_method in KD_METHODS and kd_method != "none",
           f"KD_METHOD {kd_method} is one of {[m for m in KD_METHODS if m != 'none']} -- "
           f"'{kd_method}' means bank={kd_bank}, D clamp={dclamp}", "S")
        ck(dclamp in DCLAMP_CHOICES, f"D clamp {dclamp} is one of {DCLAMP_CHOICES}", "S")
        ck(kp_scope != "none" and (kd_scope != "none" or kd_method == "dclamp"),
           f"KP_SCOPE is not 'none', and KD_SCOPE is 'none' only under KD_METHOD 'dclamp' "
           f"(here: kp {kp_scope}, kd {kd_scope}, method {kd_method}) -- the zero-edit control's "
           f"setting can never reach a candidate", "S")
    else:
        say("      (dose_check RELAXED -- this is the ZERO-EDIT CONTROL, not a flight candidate)")
    ck(kd_scope in KD_SCOPES and kp_scope in KP_SCOPES, f"scopes kd={kd_scope} kp={kp_scope} are legal", "S")

    # ---------------------------------------------------------------------------------------------
    say("\n  [2] CELL IDENTITY -- every edited cell's reader DECODED from the base image's own bytes")
    say("      (vacuous by construction: they read only `base`, which the sha256 pins -- but they are")
    say("       the guard against the off-by-0x1000 tp trap that has bitten this kit five times)")
    for site, cell, mnem, dst in ((0x28F96, FB_CELL, "ld.hu", 13), (0x28F9C, FB_CELL, "ld.hu", 14),
                                  (0x28FB8, FB_CELL, "ld.hu", 26), (R24_LOAD, R24_CELL, "ld.hu", 10),
                                  (0x28F8A, FB_A_CELL, "ld.h", 9), (0x28F86, FB_B_CELL, "ld.hu", 16)):
        _n, mn, ops, f = decode_one(bytes(base), site)
        ck(mn == mnem and f["reg1"] == 5 and TP_BASE + f["disp"] == cell and f["reg2"] == dst,
           f"0x{site:05X}: `{mn} {ops}` and tp 0x{TP_BASE:05X}{f['disp']:+#x} == 0x{cell:05X} "
           f"(= {u16(base, cell)}).  {'ZERO-EXTEND' if mnem == 'ld.hu' else 'SIGN-EXTEND'}. "
           f"No off-by-0x1000", "V")

    # ---------------------------------------------------------------------------------------------
    say("\n  [3] 🛑 GATE 1 -- IMAGE-WIDE CENSUS of every cell this build writes, RAW BYTE SCAN")
    S = scan_rel_cached(bytes(base))
    say(f"      scanned {len(S)} gp/tp-relative accesses in [0x{START:X},0x{END:X}) -- a raw LE byte "
        f"scan, not Ghidra's analysed-instruction search (which silently undercounts)")
    # positive controls FIRST, so the nulls below are worth something
    ck([h[0] for h in hits_at(S, GAIN_CELL)] == [0x2A1EE],
       f"CONTROL the forward gain 0x{GAIN_CELL:05X} is found at its ONE known site 0x2A1EE", "S")
    ck(len(hits_at(S, SUM_CLAMP)) == 8 and len(hits_at(S, P_CLAMP)) == 7,
       f"CONTROL the SUM clamp has {len(hits_at(S, SUM_CLAMP))} accessors and the P clamp "
       f"{len(hits_at(S, P_CLAMP))} -- the scanner DOES find multi-site cells, so a 1- or 3-site "
       f"answer below is a measurement, not a scanner limit", "S")
    fb_h = hits_at(S, FB_CELL)
    ck([h[0] for h in fb_h] == list(FB_SITES) and all(h[3] == "ld.hu" for h in fb_h),
       f"🛑 0x{FB_CELL:05X} (the fb clamp) has EXACTLY {len(fb_h)} accessors image-wide, "
       f"{[hex(h[0]) for h in fb_h]}, ALL `ld.hu` -- ZERO writers, ZERO ld.h (so a written 0 can "
       f"never be read as a negative bound), and all three inside the clamp block "
       f"0x{FB_BLOCK_LO:05X}-0x{FB_BLOCK_HI:05X}", "S")
    ck(not scan_abs(bytes(base), FB_CELL) and not scan_abs(bytes(base), R24_CELL),
       "no LE32 anywhere in the image equals 0xC62E6 or 0xC6446 -- no pointer or LERP stride "
       "reaches either cell", "S")
    r24_h = hits_at(S, R24_CELL)
    ck([h[0] for h in r24_h] == [R24_LOAD] and r24_h[0][3] == "ld.hu",
       f"0x{R24_CELL:05X} (the r24 engaged arm): EXACTLY 1 accessor, 0x{R24_LOAD:05X} (ld.hu) -- "
       f"0 writers.  A cal change here is PRIVATE", "S")
    ck([h[0] for h in fb_h if ISLAND_LO <= h[0] < ISLAND_HI] == [],
       f"0x{FB_CELL:05X} is read ZERO times inside the dead twin island "
       f"0x{ISLAND_LO:05X}-0x{ISLAND_HI:05X} -- this edit cannot be silently half-applied", "S")

    say("\n  [3b] THE CLAMP'S THREE BRANCHES, DECODED, AND THE MIRROR THAT COLLAPSES THEM AT C = 0")
    for site, want, text in ((0x28FA6, "cmp", "cmp r13,r26"), (0x28FAC, "ble", "ble 0x28fb2"),
                             (0x28FAE, "mov", "mov r14,r26"), (0x28FB0, "br", "br 0x28fbe"),
                             (0x28FB2, "subr", "subr r0,r14"), (0x28FB4, "cmp", "cmp r14,r26"),
                             (0x28FB6, "bge", "bge 0x28fbe"), (0x28FBC, "subr", "subr r0,r26"),
                             (0x28FBE, "mov", "mov r26,r16")):
        _n, mn, ops, _f = decode_one(bytes(base), site)
        ck(mn == want and "".join(f"{mn} {ops}".split()) == "".join(text.split()),
           f"0x{site:05X} decodes to `{mn} {ops}` == `{text}`", "V")

    def fb_clamp(v, c):
        """Mirrors 0x28FA6-0x28FBE exactly, branch for branch."""
        if not (v <= c):                    # 0x28FA6 cmp ; 0x28FAC ble  (NOT taken)
            return c                        #   0x28FAE mov r14,r26   (r14 == c)
        if v >= -c:                         # 0x28FB2 subr r0,r14 ; 0x28FB4 cmp ; 0x28FB6 bge
            return v
        return -c                           # 0x28FB8 ld.hu ; 0x28FBC subr r0,r26

    ck(all(fb_clamp(v, 0) == 0 for v in (-46080, -4942, -1, 0, 1, 2471, 46080, 10 ** 6)),
       "🛑 clamp(r26, +-0) == 0 for r26 < 0, == 0 and > 0 -- the operand is forced to EXACTLY ZERO "
       "on ALL THREE branches (mirrored arithmetic, not asserted)", "S")
    ck(fb_clamp(9000, 7680) == 7680 and fb_clamp(-9000, 7680) == -7680 and fb_clamp(5, 7680) == 5
       and fb_clamp(50000, 46080) == 46080,
       "POSITIVE CONTROL: the SAME mirror reproduces stock's +-7680 clamp and V282's +-46080 -- so "
       "the zero result above is the mirror working, not the mirror being degenerate", "S")
    ck(bytes(base[FB_SUM_SITE:FB_SUM_SITE + 2]) == FB_SUM_B,
       f"0x{FB_SUM_SITE:05X} `add r9,r26`: r26 = s_old + s_new, the TWO-SAMPLE SUM that gets clamped", "V")
    ck(bytes(base[FB_STATE_STORE:FB_STATE_STORE + 4]) == FB_STATE_STORE_B,
       f"0x{FB_STATE_STORE:05X} `st.w r9,-0x3d30,gp` sits INSIDE the clamp block and stores s_new "
       f"BEFORE the clamp resolves -- the filter STATE keeps running, only the OPERAND is zeroed. "
       f"(That is what keeps the 0x14A b3 sign rung meaningful.)", "V")
    ck(bytes(base[E_SHL_SITE:E_SHL_SITE + 2]) == E_SHL_B
       and bytes(base[E_SUB_SITE:E_SUB_SITE + 2]) == E_SUB_B,
       f"0x{E_SHL_SITE:05X} `shl 0x5,r16` then 0x{E_SUB_SITE:05X} `sub r26,r16`: E = 32*sp - r26. "
       f"With r26 forced to 0, E = 32*sp UNCONDITIONALLY", "V")
    _n, mn, ops, _f = decode_one(bytes(base), 0x29E3E)
    ck(mn == "sar" and _f["imm5"] == 8, f"0x29E3E `{mn} {ops}` -- P = (E*Kp) >> 8, the shift READ "
                                        f"from the instruction, not inherited", "V")
    _n, mn, ops, _f = decode_one(bytes(base), 0x29EEC)
    ck(mn == "sar" and _f["imm5"] == 3, f"0x29EEC `{mn} {ops}` -- D = (dE*Kd) >> 3, likewise", "V")

    say("\n  [3d] THE D CLAMP BLOCK -- the SAME three-branch idiom, decoded from the base's own bytes")
    d_h = hits_at(S, DCLAMP_CELL)
    ck([h[0] for h in d_h] == sorted(DCLAMP_SITES + DCLAMP_ISLAND)
       and all(h[3] == "ld.hu" for h in d_h),
       f"0x{DCLAMP_CELL:05X} (the D clamp): {len(d_h)} accessors image-wide, "
       f"{[hex(h[0]) for h in d_h]}, ALL `ld.hu` -- the FOUR live ones are the clamp block "
       f"0x29EE8-0x29F06 and the other THREE are inside the DEAD twin island "
       f"0x{ISLAND_LO:05X}-0x{ISLAND_HI:05X}.  Zero writers", "S")
    for site, want, text in ((0x29EEE, "cmp", "cmp r10,r8"), (0x29EF0, "ble", "ble 0x29ef8"),
                             (0x29EFC, "subr", "subr r0,r7"), (0x29EFE, "cmp", "cmp r7,r8"),
                             (0x29F00, "bge", "bge 0x29f08"), (0x29F06, "subr", "subr r0,r8")):
        _n, mn, ops, _f = decode_one(bytes(base), site)
        ck(mn == want and "".join(f"{mn} {ops}".split()) == "".join(text.split()),
           f"0x{site:05X} decodes to `{mn} {ops}` == `{text}`", "V")
    ck(all(fb_clamp(v, 0) == 0 for v in (-10240, -1, 0, 1, 10240, 10 ** 6)),
       f"the D clamp is the SAME `cmp / ble / mov / subr / cmp / bge / ld.hu / subr` idiom as the fb "
       f"clamp, so the mirror above applies to it unchanged: at a bound of 0, D == 0 on all three "
       f"branches.  DCLAMP is {dclamp} in this build, so that path is "
       f"{'LIVE -- D is zero by TWO independent cells' if dclamp == 0 else 'NOT taken; Kd = 0 alone carries [B]'}",
       "S")

    say("\n  [3c] CROSS-BASE IDENTITY -- V279 proved [A] on V268; is that proof valid on V282?")
    try:
        v268 = Path(plain_image_path(V268_NAME)).read_bytes()
    except Exception:
        v268 = None
    if v268 is not None and hashlib.sha256(v268).hexdigest() == V268_SHA:
        for lo, hi, what in ((FB_BLOCK_LO, FB_BLOCK_HI, "the fb filter + clamp block"),
                             (0x29D6C, 0x29D84, "the E subtraction"),
                             (0x29E30, 0x29F0C, "the P and D stages"),
                             (0x2A170, 0x2A250, "the output lag, gain and cap")):
            d = [a for a in range(lo, hi) if v268[a] != base[a]]
            ck(d == [], f"[0x{lo:05X},0x{hi:05X}) {what}: BYTE-IDENTICAL between V268 and V282 "
                        f"({len(d)} diffs) -- V279's proof of [A] transfers to this base unchanged", "S")
    else:
        say("      (V268 image absent or hash mismatch -- cross-base check SKIPPED, and this is "
            "reported, not silently passed)")

    # ---------------------------------------------------------------------------------------------
    say("\n  [4] THE THREE BANKS, WALKED FROM THE IMAGE")
    mptrs = [u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)]
    kptrs = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    dptrs = [u32(base, KD_PTR + 4 * s) for s in range(N_SLOTS)]
    for name, ptrs, npt in (("map", mptrs, MAP_N), ("Kp", kptrs, KP_N), ("Kd", dptrs, KD_N)):
        ck(len(set(ptrs)) == N_SLOTS and all(START <= p < END for p in ptrs)
           and all(u16(base, p) == npt for p in ptrs),
           f"{name} bank: {N_SLOTS} pointers -> {len(set(ptrs))} DISTINCT records, all in "
           f"[0x{START:X},0x{END:X}), every one n == {npt}", "V")
    ck(mptrs[LIVE_SLOT] == LIVE_MAP_REC and kptrs[LIVE_SLOT] == LIVE_KP_REC
       and dptrs[LIVE_SLOT] == LIVE_KD_REC,
       f"live slot {LIVE_SLOT}: map 0x{LIVE_MAP_REC:05X}, Kp 0x{LIVE_KP_REC:05X}, "
       f"Kd 0x{LIVE_KD_REC:05X}", "V")
    _n, mX, mY = rec(base, LIVE_MAP_REC)
    _n, kX, kY = rec(base, LIVE_KP_REC)
    _n, dX, dY = rec(base, LIVE_KD_REC)
    ck(tuple(mX) == LIVE_MAP_X and tuple(mY) == LIVE_MAP_Y, f"live map X {mX} Y {mY}", "V")
    ck(tuple(kX) == LIVE_KP_X and tuple(kY) == LIVE_KP_Y, f"live Kp X {kX} Y {kY} (V281 rev 3's flat)", "V")
    ck(tuple(dX) == (0, 11, 22, 32) and tuple(dY) == LIVE_KD_Y, f"live Kd X {dX} Y {dY}", "V")
    ck(all(mY[i + 1] > mY[i] for i in range(MAP_N - 1)) and all(mX[i + 1] > mX[i] for i in range(MAP_N - 1)),
       "the live map is strictly increasing in BOTH axes -- every LERP segment has a POSITIVE slope, "
       "so the hardware divide's truncate-toward-zero equals this script's floor", "S")
    ck(len({tuple(rec(base, p)[2]) for p in kptrs}) > 1,
       f"🛑 V282's Kp bank is NOT one value: the {N_SLOTS} records carry "
       f"{sorted({rec(base, p)[2][0] for p in kptrs})} -- V281 rev 3 flattened EVERY record to ITS "
       f"OWN Y[0], so 'match what V282 did elsewhere' and 'write one KP_FLAT everywhere' are "
       f"different instructions.  KP_SCOPE names which one this build takes", "S")
    ck(all(len(set(rec(base, p)[2])) == 1 for p in kptrs),
       f"and every one of the {N_SLOTS} Kp records is ALREADY FLAT -- V293 changes a LEVEL, never a "
       f"shape", "S")

    # ---------------------------------------------------------------------------------------------
    say("\n  [5] THE PER-SLOT HAZARD, BEFORE THE EDIT -- what each slot would deliver at fb = 0")
    cal_b = read_cal(base)
    say(f"      cal from the base: P clamp {cal_b['PC']}  SUM {cal_b['SC']}  gain {cal_b['G']}  "
        f"OUT {cal_b['OC']}  out-lag ({cal_b['LA']},{cal_b['LB']})  taper-at-rest {cal_b['FADE']}")
    say("      slot |  Kp | map Ytop | rails at idx | T(240) | note")
    kp_sel = kp_slots(kp_scope)
    for s in LIVE_SLOTS:
        kpv = rec(base, kptrs[s])[2][0]
        railat = next((i for i in range(241) if surface(base, s, i, 0, cal_b)["rail"]), None)
        t240 = surface(base, s, 240, 0, cal_b)["T"]
        note = "<-- LIVE" if s == LIVE_SLOT else ("covered by KP_SCOPE" if s in kp_sel else
                                                  "🛑 NOT covered -- keeps Kp %d at fb = 0" % kpv)
        say(f"      {s:4d} | {kpv:3d} | {rec(base, mptrs[s])[2][-1]:8d} | {str(railat):>12} | {t240:6d} | {note}")
    uncovered = [s for s in LIVE_SLOTS if s not in kp_sel]
    say(f"      ⇒ KP_SCOPE = '{kp_scope}' covers {sorted(kp_sel)}; reachable-but-uncovered: {uncovered}.")
    say(f"        The fb clamp is ONE GLOBAL CELL; Kp is PER-SLOT.  If the selector were ever not "
        f"{LIVE_SLOT}, an uncovered slot runs ZERO feedback at its own (larger) Kp and rails at a low")
    say(f"        demand index.  The selector was MEASURED 7 on the V276 wire and maxes at 9.")

    # ---------------------------------------------------------------------------------------------
    say("\n  [6] APPLY")
    code = bytearray(base)
    attributed = set()
    struct.pack_into("<H", code, FB_CELL, fb_new)
    attributed |= {FB_CELL, FB_CELL + 1}
    ck(u16(code, FB_CELL) == fb_new, f"[A] 0x{FB_CELL:05X} fb clamp {FB_V282} -> {fb_new}", "T")
    kd_recs = sorted({dptrs[s] for s in kd_slots(kd_scope)}) if kd_bank else []
    kd_cells = 0
    for p in kd_recs:
        n = u16(base, p)
        for k in range(n):
            o = y_off(p, n, k)
            if u16(base, o) != KD_ZERO:
                struct.pack_into("<H", code, o, KD_ZERO)
                attributed |= {o, o + 1}
                kd_cells += 1
    ck(all(rec(code, p)[2] == [0] * KD_N for p in kd_recs),
       f"[B] Kd bank -> 0 on {len(kd_recs)} DISTINCT records ({kd_scope}), {kd_cells} u16 cells "
       f"written{'  (KD_METHOD = dclamp: the bank is NOT touched)' if not kd_bank else ''}", "T")
    kp_recs = sorted({kptrs[s] for s in kp_sel})
    kp_cells = 0
    for p in kp_recs:
        n = u16(base, p)
        for k in range(n):
            o = y_off(p, n, k)
            if u16(base, o) != kp_flat:
                struct.pack_into("<H", code, o, kp_flat)
                attributed |= {o, o + 1}
                kp_cells += 1
    ck(all(rec(code, p)[2] == [kp_flat] * KP_N for p in kp_recs),
       f"[C] Kp -> {kp_flat} flat on {len(kp_recs)} DISTINCT records ({kp_scope}), {kp_cells} cells", "T")
    if dclamp != DCLAMP_V282:
        struct.pack_into("<H", code, DCLAMP_CELL, dclamp)
        attributed |= {DCLAMP_CELL, DCLAMP_CELL + 1}
    ck(u16(code, DCLAMP_CELL) == dclamp,
       f"[B2] 0x{DCLAMP_CELL:05X} D clamp == {dclamp}"
       + ("  (PRE-REG: D is now zero by a SECOND, independent cell)" if dclamp == 0
          else "  (BRIEF: unchanged from V282)"), "T")
    if r24_arm != R24_V282:
        struct.pack_into("<H", code, R24_CELL, r24_arm)
        attributed |= {R24_CELL, R24_CELL + 1}
    ck(u16(code, R24_CELL) == r24_arm,
       f"[D] 0x{R24_CELL:05X} r24 engaged arm == {r24_arm} "
       f"({R24_DOSES.get(r24_arm, 'NOT A LISTED DOSE')})", "T")
    if mutate is not None:
        mutate(code, attributed)
    say(f"      {len(attributed)} payload bytes written")

    # ---------------------------------------------------------------------------------------------
    say("\n  [7] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    say("      🛑 The FIRST assertion is FULL-COVERAGE over [0x13000,0x100000).  Every named")
    say("         byte-identity check after it is ENTAILED BY IT and is marked [V] accordingly.")
    outside = [x for x in range(START, END) if x not in attributed and code[x] != base[x]]
    ck(outside == [],
       f"NO byte in [0x{START:05X},0x{END:05X}) outside the {len(attributed)} attributed payload bytes "
       f"differs from V282 before the CRC recompute ({len(outside)} stray diffs)", "S")
    ck([x for x in attributed if x < 0xC0000] == [],
       f"🛑 CAL-ONLY: ZERO payload bytes below 0xC0000.  Not one code byte changes, so V293 is "
       f"OUTSIDE the kit's only bricking class", "S")
    for a, v in FROZEN.items():
        ck(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}   [entailed]", "V")
    for a, v in EME_FLOATS.items():
        ck(abs(f32(code, a) - v) < 1e-6 and bytes(code[a:a + 4]) == bytes(base[a:a + 4]),
           f"EME float mirror 0x{a:05X} == {v}   [entailed]", "V")
    ck(bytes(code[PACK_LO:PACK_HI]) == PACK_V282 == bytes(base[PACK_LO:PACK_HI]),
       f"the CAN-427 delivered-torque tap 0x{PACK_LO:05X}-0x{PACK_HI - 1:05X} is byte-identical AND "
       f"equals the recorded V282 window -- THE INSTRUMENT FOR THIS BUILD'S OWN EDIT IS ON THE WIRE "
       f"AND UNTOUCHED   [byte-identity entailed; the equality to the recorded window is not]", "S")
    ck(bytes(code[T_STORE_SITE:T_STORE_SITE + 4]) == T_STORE_B,
       f"0x{T_STORE_SITE:05X} `st.h r1,-0x6b38,gp` -- the tap's SOURCE still stored every tick  [entailed]", "V")
    ck(hashlib.sha256(bytes(code[CAVE14A_LO:CAVE14A_HI])).hexdigest()[:8] == CAVE14A_SHA8
       and bytes(code[CAVE14A_HOOK:CAVE14A_HOOK + 4]) == CAVE14A_HOOK_B,
       f"the 0x14A telemetry cave 0x{CAVE14A_LO:05X}-0x{CAVE14A_HI - 1:05X} hashes to "
       f"{CAVE14A_SHA8} and its hook is intact -- the r24 comparator rungs b5/b6 keep V282's meaning", "S")
    _fa, _fb = FWD_GAIN_REPOINT
    ck(bytes(code[_fa:_fa + 2]) == _fb, f"0x{_fa:05X} still carries the forward-gain repoint  [entailed]", "V")
    ck(all(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]) for p in mptrs),
       f"all {N_SLOTS} assist-map records byte-identical -- V293 does NOT re-linearise the map; "
       f"V282's is already linear   [entailed]", "V")
    tps = sorted({u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)})
    ck(all(bytes(code[p:p + 2 + 4 * u16(base, p)]) == bytes(base[p:p + 2 + 4 * u16(base, p)]) for p in tps),
       f"all {len(tps)} override-taper records byte-stock -- the grip escape is unchanged   [entailed]", "V")
    ck(bytes(code[KP_PTR:KP_PTR + 4 * N_SLOTS]) == bytes(base[KP_PTR:KP_PTR + 4 * N_SLOTS])
       and bytes(code[KD_PTR:KD_PTR + 4 * N_SLOTS]) == bytes(base[KD_PTR:KD_PTR + 4 * N_SLOTS])
       and bytes(code[MAP_PTR:MAP_PTR + 4 * N_SLOTS]) == bytes(base[MAP_PTR:MAP_PTR + 4 * N_SLOTS]),
       "all three POINTER BANKS untouched -- the edits are in the DATA   [entailed]", "V")
    for p in kp_recs + kd_recs:
        n = u16(base, p)
        ck(u16(code, p) == n and bytes(code[p + 2:p + 2 + 2 * n]) == bytes(base[p + 2:p + 2 + 2 * n]),
           f"record 0x{p:05X}: n and the whole X axis UNTOUCHED   [entailed]", "V")

    # ---------------------------------------------------------------------------------------------
    say("\n  [8] CRC TRAILERS -- blocks located GENERICALLY by walking the chain from the image")
    owners = {}
    for a in sorted(attributed):
        owners.setdefault(tuple(V53.owning_block(code, a)), []).append(a)
    blocks = sorted(owners)
    for b0, b1 in blocks:
        ck(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:06X}", "S")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        moved = [a for a in owners[(b0, b1)] if code[a] != base[a]]
        ck((newc != oldc) == bool(moved),
           f"block [0x{b0:06X},0x{b1:06X}) CRC moves IFF a byte in it actually CHANGED VALUE: "
           f"{len(moved)} of its {len(owners[(b0, b1)])} payload bytes differ from V282 and the CRC "
           f"went 0x{oldc:08X} -> 0x{newc:08X}.  (A write of the SAME value must not move it -- that "
           f"is what makes the zero-edit control reproduce the base hash.)", "S")
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        say(f"      page [0x{b0:06X},0x{b1:06X})  trailer  0x{oldc:08X} -> 0x{newc:08X}  "
            f"({len(owners[(b0, b1)])} payload bytes)")
    ck(qwalk(walk_all_blocks, bytes(code)) == 0, "built image CRC chain 50/50", "S")
    ck(qwalk(walk, bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # ---------------------------------------------------------------------------------------------
    say("\n  [9] FULL BYTE DIFF vs V282 -- every differing offset enumerated and ATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    ck(set(diff) <= attributed, f"all {len(diff)} differing bytes are attributed payload or CRC", "S")
    exp_fb = sum(1 for j in (0, 1) if struct.pack("<H", FB_V282)[j] != struct.pack("<H", fb_new)[j])
    exp_r24 = sum(1 for j in (0, 1) if struct.pack("<H", R24_V282)[j] != struct.pack("<H", r24_arm)[j])
    exp_dc = sum(1 for j in (0, 1)
                 if struct.pack("<H", DCLAMP_V282)[j] != struct.pack("<H", dclamp)[j])
    exp_kd = sum(1 for p in kd_recs for k in range(KD_N)
                 for j in (0, 1)
                 if struct.pack("<H", u16(base, y_off(p, KD_N, k)))[j] != struct.pack("<H", KD_ZERO)[j])
    exp_kp = sum(1 for p in kp_recs for k in range(KP_N)
                 for j in (0, 1)
                 if struct.pack("<H", u16(base, y_off(p, KP_N, k)))[j] != struct.pack("<H", kp_flat)[j])
    # CRC bytes are counted by COMPARISON, not as 4 x len(blocks): a trailer whose block's payload
    # was written with an unchanged value does not move, and the zero-edit control depends on that.
    exp_crc = sum(1 for _b0, b1 in blocks for j in range(4) if code[b1 + j] != base[b1 + j])
    exp = exp_fb + exp_r24 + exp_dc + exp_kd + exp_kp + exp_crc
    ck(len(diff) == exp,
       f"total diff = {exp_fb} fb + {exp_r24} r24 + {exp_dc} Dclamp + {exp_kd} Kd + {exp_kp} Kp + "
       f"{exp_crc} CRC (over {len(blocks)} owning block(s)) = {exp}, got {len(diff)}.  Every term "
       f"COMPUTED from the base's own bytes, none asserted -- a coincidental 0x00 or 0xFF cannot "
       f"hide a missing write", "S")
    names = {FB_CELL: (2, "fb clamp    0xC62E6 [A]"), R24_CELL: (2, "r24 arm     0xC6446 [D]"),
             DCLAMP_CELL: (2, "D clamp     0xC61B6 [B2]")}
    for p in kd_recs:
        names[y_off(p, KD_N, 0)] = (2 * KD_N, f"Kd Y  rec 0x{p:05X} [B]")
    for p in kp_recs:
        names[y_off(p, KP_N, 0)] = (2 * KP_N, f"Kp Y  rec 0x{p:05X} [C]")
    trailers = {b1 for _b0, b1 in blocks}
    rr = runs(diff)
    # 🛑 a trailer run need not START at the trailer address: if only the top CRC byte changes, the
    #    run begins at b1+3.  Match the whole 4-byte span, not the first address.
    labelled = [(s, e, next((v for k, (n, v) in names.items() if k <= s < k + n), None)
                 or next((f"CRC trailer 0x{t:06X}" for t in trailers if t <= s < t + 4), None))
                for s, e in rr]
    orphan = [(hex(s), hex(e - 1)) for s, e, lbl in labelled if lbl is None]
    ck(not orphan,
       f"every one of the {len(rr)} differing RUNS is attributed to a named edit or a CRC trailer "
       f"(unattributed runs: {orphan}).  One assertion over all runs -- the per-run form inflated "
       f"V291's substantive count", "S")
    by_kind = {}
    for s, e, lbl in labelled:
        lbl = lbl or "UNATTRIBUTED"
        k = lbl.split("rec")[0].strip() if "rec" in lbl else lbl.split("0x")[0].strip() or lbl
        k = "CRC trailer" if lbl.startswith("CRC") else k
        by_kind.setdefault(k, [0, 0])
        by_kind[k][0] += 1
        by_kind[k][1] += e - s
    say("      differing runs, grouped:")
    for k, (nr, nb) in sorted(by_kind.items()):
        say(f"        {nr:4d} run(s), {nb:4d} byte(s)   {k}")
    say("      offset                len  what                       base -> built")
    for s, e, lbl in labelled[:6] + [x for x in labelled if x[2] and x[2].startswith("CRC")]:
        a_, b_ = bytes(base[s:e]), bytes(code[s:e])
        txt = (a_.hex(), b_.hex()) if e - s <= 10 else (f"{a_[:4].hex()}..({e - s}B)",
                                                        f"{b_[:4].hex()}..({e - s}B)")
        say(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {(lbl or 'UNATTRIBUTED'):26s} "
            f"{txt[0]} -> {txt[1]}")
    if "--diff" in sys.argv:
        for s, e, lbl in labelled:
            say(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {lbl or 'UNATTRIBUTED'}")

    # ---------------------------------------------------------------------------------------------
    say("\n  [10] THE DELIVERED SURFACE -- READ FROM THE BUILT IMAGE, never from these constants")
    cal = read_cal(code)
    ck((cal["PC"], cal["SC"], cal["G"], cal["OC"]) == (15360, 15360, 5346, 3072),
       f"P clamp {cal['PC']} / SUM {cal['SC']} / gain {cal['G']} / OUT {cal['OC']} -- all read from "
       f"the BUILT image and all frozen at V282's", "S")

    # ---- 🛑 adversary C DEFECT C4-2 fix: a FULL Y-TUPLE CENSUS, walked from the pointer families IN
    #      THE IMAGE and read AFTER `mutate()` has already run.  [6]'s readback runs BEFORE mutate(),
    #      so it cannot see a corrupted interior knot -- exactly the gap that let 7 of adversary C's
    #      13 mutations pass 241/241 (the byte-diff COUNT and the rail/tag checks only ever see Y[0]
    #      or Y[-1]).  Every in-scope Kp record's FULL Y tuple must be (KP_FLAT,)*5 and every in-scope
    #      Kd record's FULL Y tuple must be (0,)*4 -- not just its first or last knot.
    kp_ptrs_img = [u32(code, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    kd_ptrs_img = [u32(code, KD_PTR + 4 * s) for s in range(N_SLOTS)]
    kp_recs_set, kd_recs_set = set(kp_recs), set(kd_recs)
    kp_bad = [(s, p, rec(code, p)[2]) for s, p in enumerate(kp_ptrs_img)
              if p in kp_recs_set and rec(code, p)[2] != [kp_flat] * KP_N]
    kd_bad_y = [(s, p, rec(code, p)[2]) for s, p in enumerate(kd_ptrs_img)
                if p in kd_recs_set and rec(code, p)[2] != [0] * KD_N]
    ck(not kp_bad and not kd_bad_y,
       f"🛑 FULL Y-TUPLE CENSUS, walked from the POINTER FAMILIES in the BUILT (post-mutation) image: "
       f"every one of the {len(kp_recs_set)} in-scope Kp records' complete Y tuple is EXACTLY "
       f"({kp_flat},)*{KP_N} ({len(kp_bad)} violate it{': ' + str(kp_bad[:2]) if kp_bad else ''}), and "
       f"every one of the {len(kd_recs_set)} in-scope Kd records' complete Y tuple is EXACTLY "
       f"(0,)*{KD_N} ({len(kd_bad_y)} violate it{': ' + str(kd_bad_y[:2]) if kd_bad_y else ''})", "S")

    # the fb operand, from the built image, at the two stall operating points
    a_i, b_i, fbc = s16(code, FB_A_CELL), u16(code, FB_B_CELL), u16(code, FB_CELL)
    ck(fbc == fb_new, f"the fb clamp on the BUILT image reads {fbc}", "T")
    say(f"      fb filter a={a_i} b={b_i}, linear DC 2b/(1024-a) = {2 * b_i / (1024 - a_i):.4f}")
    ops = []
    for degs in (0, 10, 20):
        xw = 8 * degs                                     # wire counts: 8 per deg/s
        m_b, _cyc = fb_ss(a_i, b_i, xw, u16(base, FB_CELL))
        m_n, _cyc2 = fb_ss(a_i, b_i, xw, fbc)
        ops.append((degs, xw, m_b, m_n))
        say(f"      wheel rate {degs:2d} deg/s = {xw:4d} wire counts -> r26 on V282 = {m_b:6d} "
            f"(linear {2 * b_i / (1024 - a_i) * xw:8.1f}),  on V293 = {m_n}")
    ck(all(o[3] == 0 for o in ops) == (fb_new == 0),
       f"🛑 on the BUILT image the clamped operand r26 is "
       f"{'EXACTLY 0' if fb_new == 0 else 'NON-ZERO (this is the control, fb clamp = %d)' % fb_new} "
       f"at every wheel rate tested {[o[0] for o in ops]} deg/s -- computed through the integer "
       f"filter AND the built clamp cell, not assumed.  The POSITIVE CONTROL is the zero-edit run, "
       f"where the same code path returns {[o[3] for o in ops]}", "S")
    say("")
    say("      THE DELIVERED SURFACE.  T is the BYTE-EXACT delivery: taper x254/256, output lag,")
    say("      gain, output cap -- the tracer's sec.3.1 chain.  T_ceil is the number the record USED")
    say("      to quote (no taper, no output lag) and is NOT a delivery; it is printed only so the")
    say("      2505 in older docstrings can be recognised for what it is.")
    say("      idx |  map |  Kp |     P  rail |     S |   T   [lo,hi] | T_ceil | V282 fb0 | @10d/s | @20d/s")
    tbl = []
    for i in list(range(0, 241, 10)):
        v = surface(code, LIVE_SLOT, i, 0, cal)
        b0 = surface(base, LIVE_SLOT, i, 0, cal_b)
        b1 = surface(base, LIVE_SLOT, i, ops[1][2], cal_b)
        b2 = surface(base, LIVE_SLOT, i, ops[2][2], cal_b)
        tbl.append((i, v, b0, b1, b2))
        say(f"      {i:4d} | {v['sp']:4d} | {v['kp']:3d} | {v['P']:6d} "
            f"{'RAIL' if v['rail'] else '    '} | {v['S']:5d} | {v['T']:5d} "
            f"[{v['T_lo']:4d},{v['T_hi']:4d}] | {v['T_ceil']:6d} | {b0['T']:8d} | {b1['T']:6d} "
            f"| {b2['T']:6d}")
    v240, b240 = tbl[-1][1], tbl[-1][2]

    if dose_check:
        ck(u16(code, R24_CELL) in R24_DOSES,
           f"the r24 arm ON THE BUILT IMAGE reads {u16(code, R24_CELL)}, one of the LISTED doses "
           f"{sorted(R24_DOSES)} -- a SECOND, independent guard on V291's defect D2 (the tag "
           f"re-derivation at [11] is the first; a stray 4722 beats neither)", "S")

    # ---- D == 0, asserted through BOTH cells independently -------------------------------------
    kd_bad = [(sl, i) for sl in (kd_slots(kd_scope) if kd_bank else ())
              for i in range(241)
              if lerp(*rec(code, u32(code, KD_PTR + 4 * sl))[1:], i) != 0]
    d_by_bank = bool(kd_bank) and not kd_bad
    d_by_clamp = u16(code, DCLAMP_CELL) == 0
    big = 10 ** 6
    d_probe = max(abs(surface(code, LIVE_SLOT, i, 0, cal, dE=sgn * big)["D"])
                  for i in (0, 32, 120, 240) for sgn in (1, -1))
    ck((d_probe == 0 and (d_by_bank or d_by_clamp)) or kd_method == "none",
       f"🛑 D IS IDENTICALLY ZERO ON THE BUILT IMAGE, driven with dE = +-{big} (far past anything "
       f"the 100 Hz command staircase can produce): max |D| = {d_probe}.  Kd bank zero: {d_by_bank} "
       f"({len(kd_slots(kd_scope)) if kd_bank else 0} slot(s), violations {kd_bad[:3]}).  D clamp "
       f"zero: {d_by_clamp}.  KD_METHOD '{kd_method}' -- "
       f"{'EITHER CELL ALONE SUFFICES, so one wrong byte cannot resurrect D (the prereg A1 clause)' if (d_by_bank and d_by_clamp) else 'ONE cell carries it'}",
       "S")
    ck(u16(code, FB_B_CELL) == FB_B and u16(code, FB_A_CELL) == FB_A,
       f"🛑 THE POLE PAIR IS UNTOUCHED: 0x{FB_A_CELL:05X} = {u16(code, FB_A_CELL)}, "
       f"0x{FB_B_CELL:05X} = {u16(code, FB_B_CELL)}.  V293 mutes at the CLAMP, NEVER at b: "
       f"floor(-a/1024) = -1 for every a < 1024, so b = 0 would leave s = -1 ABSORBING and fb "
       f"resting at -2 forever, not 0 (tracer sec.4a)", "S")
    kd_base = lerp(*rec(base, u32(base, KD_PTR + 4 * LIVE_SLOT))[1:], 0)
    kick = 32 * (LIVE_MAP_Y[-1] - LIVE_MAP_Y[-2]) // (240 - 160)
    say(f"      the setpoint kick V282 carries and V293 does not: one demand-index count near the "
        f"map top is dE = {kick}, and at V282's Kd = {kd_base} that is D = {(kick * kd_base) >> 3} "
        f"counts.  The tracer measures the 100 Hz command staircase ALREADY railing V282's D clamp "
        f"on 0.7 % of ticks at +-10240, 67 % of the sum ceiling, from a FEEDFORWARD term.")

    # ---- the rail, from the bytes, under BOTH disputed speed tapers ----------------------------
    say("")
    say(f"      THE RAIL, FROM THE BYTES.  The always-on taper is "
        f"((A x B) & 0xFFFF) >> 8 = {cal['FADE']} at rest (A = 0x{TAPER_A:05X} on |bar-derivative|, "
        f"B on speed).")
    say(f"      🛑 WHICH SPEED TAPER IS LIVE IS DISPUTED -- C 0x{TAPER_C:05X} (the tracer) vs "
        f"D 0x{TAPER_D:05X} (kit memory).  Both computed:")
    say(f"      taper |  at rest | v=48 | v=64 | v=96 |  T(240) at rest | T(240) at v=64")
    rails_by_taper = {}
    for nm, bank in (("C", TAPER_C), ("D", TAPER_D)):
        f0 = taper_factor(code, bank, 0, 0)
        t0 = surface(code, LIVE_SLOT, 240, 0, dict(cal, FADE=f0))["T"]
        f64 = taper_factor(code, bank, 0, 64)
        t64 = surface(code, LIVE_SLOT, 240, 0, dict(cal, FADE=f64))["T"]
        rails_by_taper[nm] = (f0, t0, f64, t64)
        say(f"      {nm:>5} | {f0:7d} | {taper_factor(code, bank, 0, 48):4d} | {f64:4d} | "
            f"{taper_factor(code, bank, 0, 96):4d} | {t0:15d} | {t64:14d}")
    ck(rails_by_taper["C"][0] == rails_by_taper["D"][0] == 254
       and rails_by_taper["C"][1] == rails_by_taper["D"][1],
       f"AT REST the two disputed speed tapers are INDISTINGUISHABLE: both return 255 below their "
       f"first knot, so the factor is ((255*255)&0xFFFF)>>8 = {cal['FADE']} either way and the "
       f"at-rest rail is the same number.  They diverge ONLY above ~24 on the speed axis "
       f"(C {rails_by_taper['C'][2]} vs D {rails_by_taper['D'][2]} at v = 64), and V293 touches "
       f"NEITHER record -- so the dispute cannot change this build's claim", "S")
    # the LINEAR reading of the same stage, for the one-count comparison against the tracer's table
    y_lin = int(2 * cal["LB"] * v240["S"] / ((1024 - cal["LA"]) * 32))
    t_lin = max(-cal["OC"], min(cal["OC"], (y_lin * cal["G"]) >> 15))
    ck(v240["T_lo"] == v240["T_hi"] == v240["T"] and v240["T"] < v240["T_ceil"],
       f"🛑 THE RAIL IS {v240['T']} COUNTS, NOT {v240['T_ceil']}.  Read from the built bytes through "
       f"the taper ({cal['FADE']}/256) and the output lag, cold-started from the state 0 that the "
       f".data copy loop 0x{BOOT_LOOP[0]:05X}-0x{BOOT_LOOP[1]:05X} guarantees (flash "
       f"[0x{BOOT_FLASH_LO:05X},0x{BOOT_FLASH_HI:05X}) -> RAM 0x{BOOT_RAM:08X}; CITED from the "
       f"tracer, not re-derived).  V282 at fb = 0 reads {b240['T']}.  The integer output "
       f"lag has an INTERVAL of fixed points; EVERY reachable one gives {v240['T']} here, so the "
       f"band [{v240['T_lo']},{v240['T_hi']}] is a point", "S")
    ck(t_lin - v240["T"] in (0, 1),
       f"🛑 ONE-COUNT CORRECTION TO THE TRACE.  The LINEAR output-lag DC (2*{cal['LB']}/"
       f"((1024-{cal['LA']})*32) = 0.99023) gives y = {y_lin} and T = {t_lin} -- the 2462 of "
       f"TRACE-2026-09-13 sec.4a.  The INTEGER recursion's reachable fixed points give y <= "
       f"{(v240['T'] * 32768 + 32767) // cal['G']}-ish and T = {v240['T']}.  The two `sar 0xa` "
       f"floors in the OUTPUT lag carry the same bias V292's cave removed from the FEEDBACK lag, "
       f"and V292 did NOT correct this one.  Reported, not rounded away", "S")
    ck((v240["T_ceil"] == 2505) == (kp_flat == 120) or not dose_check,
       f"and the OLD convention (no taper, no output lag) gives {v240['T_ceil']} -- that is where the "
       f"2505/2481 in earlier docstrings came from.  🛑 NEVER QUOTE IT AS A DELIVERY", "S")

    # ---- KP_FLAT 119 vs 120 at the top, WITH the taper in place --------------------------------
    say("")
    say("      KP_FLAT 119 vs 120 at the top, with the taper and the output lag in place:")
    say("      KP  | P rails from |  idx 230           |  idx 239           |  idx 240")
    for kpv in KP_CHOICES:
        probe = bytearray(code)
        for pp in sorted({kptrs[sl] for sl in kp_sel}) or [kptrs[LIVE_SLOT]]:
            for k in range(KP_N):
                struct.pack_into("<H", probe, y_off(pp, KP_N, k), kpv)
        rl = next((i for i in range(241) if surface(probe, LIVE_SLOT, i, 0, cal)["rail"]), None)
        cells = []
        for i in (230, 239, 240):
            q = surface(probe, LIVE_SLOT, i, 0, cal)
            cells.append(f"P {q['P']:5d}{'*' if q['rail'] else ' '} T {q['T']:4d}")
        say(f"      {kpv:3d} | {str(rl):>12} |  {cells[0]}  |  {cells[1]}  |  {cells[2]}")
    say("      (* = the P clamp binds.  The pre-registration's A2 clause fails a rail that differs")
    say("       from V282's by one count or more, which is what rules 119 out.)")

    ck(((v240["T"] == b240["T"]) == (kp_flat == 120) or not dose_check)
       and abs(v240["T"] - b240["T"]) <= 1,
       f"🛑 THE RAIL IS PINNED TO V282's: V293 T(240) = {v240['T']} vs V282 at fb = 0 "
       f"({b240['T']}), difference {v240['T'] - b240['T']}.  KP_FLAT 120 lands on it EXACTLY; "
       f"KP_FLAT 119 lands ONE COUNT LOW", "S")
    ck(all(tbl[k][1]["T"] <= tbl[k + 1][1]["T"] for k in range(len(tbl) - 1)),
       "the V293 delivered surface is MONOTONE in demand index", "S")
    rails = [i for i in range(241) if surface(code, LIVE_SLOT, i, 0, cal)["rail"]]
    if dose_check:
        ck(bool(rails) == (kp_flat == 120) and (not rails or rails[0] >= 239),
           f"P rails on V293 at idx {rails[0] if rails else 'NEVER'}"
           f"{' (the top ' + str(len(rails)) + ' indices)' if rails else ''} -- "
           f"{'KP_FLAT 120 touches the P clamp ONLY at idx >= 239' if rails else 'KP_FLAT 119 never rails'}",
           "S")
    else:
        say(f"      (control: P rails at idx {rails[0] if rails else 'NEVER'})")
    b_rails = [i for i in range(241) if surface(base, LIVE_SLOT, i, 0, cal_b)["rail"]]
    say(f"      for contrast, V282 at fb = 0 rails from idx {b_rails[0] if b_rails else 'NEVER'} "
        f"-- i.e. V282 without feedback delivers PEAK TORQUE from "
        f"{100 * (b_rails[0] if b_rails else 241) / 240:.0f} % of demand upward, and the top half of "
        f"its map is INERT.  That pre-existing fact is what Kp 248 -> 120 removes.")
    dmd = 16.125736                                      # wire counts per demand-index LSB, MEASURED
    say(f"      demand index -> 0xE4 command: x{dmd:.6f} wire counts/LSB (measured); idx 240 = "
        f"{int(240 * dmd)} counts of openpilot's +-4096 range")

    # ---------------------------------------------------------------------------------------------
    say("\n  [11] THE OUTPUT NAME, RE-DERIVED FROM THE BUILT IMAGE'S OWN BYTES (V291 defect D2)")
    img_kp = rec(code, u32(code, KP_PTR + 4 * LIVE_SLOT))[2][0]
    img_kp_scope = next((sc for sc in KP_SCOPES
                         if {u32(code, KP_PTR + 4 * s) for s in kp_slots(sc)}
                         == {p for p in set(kptrs) if rec(code, p)[2] != rec(base, p)[2]}), kp_scope)
    img_kd_scope = next((sc for sc in KD_SCOPES
                         if {u32(code, KD_PTR + 4 * s) for s in kd_slots(sc)}
                         == {p for p in set(dptrs) if rec(code, p)[2] != rec(base, p)[2]}), kd_scope)
    img_tag = make_tag(img_kp, img_kp_scope, img_kd_scope if kd_bank else "none",
                       u16(code, R24_CELL), u16(code, FB_CELL), u16(code, DCLAMP_CELL), kd_method)
    ck(img_tag == TAG,
       f"the tag re-derived from the image's OWN halfwords (Kp {img_kp}, r24 {u16(code, R24_CELL)}, "
       f"fb {u16(code, FB_CELL)}, and the SET OF RECORDS that actually changed) is "
       f"CHARACTER-IDENTICAL to the tag on the output file.  A transcription error RENAMES the file "
       f"rather than mislabelling it", "S")
    say(f"      {IMG_NAME}")
    say(f"      {RWD_NAME}")

    # ---------------------------------------------------------------------------------------------
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd = rwd_sha = None
    if do_rwd:
        say("\n  [12] .rwd ENCODE + READBACK")
        src = Path(FF.V38_RWD).read_bytes()
        ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
        FF.assert_x31_checksum(src, "V38 source")
        info = parse_x31(src)
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        rwd = encode_x31(info["headers"], info["blocks"],
                         [bytes(code[START:END]).translate(invert_table(dec_tbl))])
        FF.assert_x31_checksum(rwd, "V293 output")
        back = bytearray(base)
        back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
        ck(bytes(back) == bytes(code),
           "the decoded .rwd is BYTE-IDENTICAL to the built image -- this one assertion entails every "
           "per-cell readback of the decoded image, so none is repeated", "S")
        ck(qwalk(walk_all_blocks, bytes(back)) == 0 and qwalk(walk, bytes(back)) == 0,
           "readback CRC chain 50/50 and BOOTLOADER replay 49/49   [entailed by the above]", "V")
        v38 = bytearray(base)
        v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
        ck(hashlib.sha256(bytes(v38[START:END])).hexdigest()
           == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
           "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")
        rwd_sha = hashlib.sha256(rwd).hexdigest()

        say("\n  [13] INDEPENDENT REBUILD -- a second splice + a DIFFERENT CRC locator")
        ind = independent_rebuild(bytes(base), kp_flat, kp_scope, kd_scope, r24_arm, fb_new, dclamp)
        ck(hashlib.sha256(ind).hexdigest() == img_sha,
           "independent rebuild == built image sha256.  🛑 HONEST LABEL: it shares this module's "
           "constants, so it CANNOT catch a wrong constant -- it cross-checks the CRC-BLOCK LOCATOR "
           "(FF.crc_block_map vs V53.owning_block) and the splice, nothing more", "S")

    # the Windows 260-character path guard, CHECKED IN THE DRY RUN so it cannot surprise a write
    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"both output paths fit this machine's {MAX_PATH}-character limit (image "
       f"{len(str(out_i))}, rwd {len(str(out_r))}).  Measured on this machine: 259 opens, 260 fails, "
       f"for open() AND rename() -- V292's builder hit it", "S")

    say("\n" + "=" * 118)
    say(f"  image SHA256 {img_sha}")
    if rwd_sha:
        say(f"  .rwd  SHA256 {rwd_sha}")
    say(f"  {R.ok}/{R.n} assertions passed -- census: {R.census['S']} SUBSTANTIVE, {R.census['V']} "
        f"vacuous (entailed by the base sha256 or by an earlier assertion), {R.census['T']} "
        f"tautological (readback of a write)")
    say("=" * 118)
    return dict(code=bytes(code), base=bytes(base), rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha,
                tag=TAG, img_name=IMG_NAME, rwd_name=RWD_NAME, run=R, table=tbl, cal=cal,
                blocks=blocks, diff=len(diff), attributed=len(attributed))


# =======================================================================================================
#  THE DOSE GRID, THE ZERO-EDIT CONTROL AND THE MUTATION TEST
# =======================================================================================================
def zero_edit_control(base):
    """🛑 With every edit DISABLED the script must reproduce the V282 base BIT FOR BIT.  If it does
    not, some 'edit' in this file is writing outside its own dose and every hash below is suspect."""
    r = build(kp_flat=rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))[2][0],
              r24_arm=R24_V282, kd_scope="none", kp_scope="none", fb_new=FB_V282,
              kd_method="none", quiet=True, do_rwd=False, base_bytes=base, dose_check=False)
    return r["img_sha"], r["diff"], r["attributed"]


def mutation_test(base):
    """Flip each edit in turn on the DEFAULT dose and assert the script FAILS.  A build whose own
    assertions cannot be made to fail is theatre (CLAUDE.md, the adversarial-pass rule)."""
    def mut_fb(code, attr):
        struct.pack_into("<H", code, FB_CELL, 1)                       # off by one -- not zero
    def mut_kd(code, attr):
        p = u32(code, KD_PTR + 4 * LIVE_SLOT)
        struct.pack_into("<H", code, y_off(p, KD_N, 2), 128)           # one knot left at 128
    def mut_kp(code, attr):
        p = u32(code, KP_PTR + 4 * LIVE_SLOT)
        struct.pack_into("<H", code, y_off(p, KP_N, 3), 248)           # one knot left at 248
    def mut_kp_level(code, attr):
        p = u32(code, KP_PTR + 4 * LIVE_SLOT)
        for k in range(KP_N):
            struct.pack_into("<H", code, y_off(p, KP_N, k), 121)       # the WRONG flat level
    def mut_r24(code, attr):
        struct.pack_into("<H", code, R24_CELL, 4722)                   # V291's defect D2, reproduced
    def mut_dclamp(code, attr):
        struct.pack_into("<H", code, DCLAMP_CELL, 1)                   # D clamp off by one, not zero
        attr |= {DCLAMP_CELL, DCLAMP_CELL + 1}
    def mut_taperA(code, attr):                                        # move the always-on taper
        p_ = u32(code, TAPER_A + 4 * LIVE_SLOT)
        struct.pack_into("<H", code, y_off(p_, 6, 0), 254)
        attr |= {y_off(p_, 6, 0), y_off(p_, 6, 0) + 1}
    def mut_polemute(code, attr):                                      # the WRONG mute -- b := 0
        struct.pack_into("<H", code, FB_B_CELL, 0)
        attr |= {FB_B_CELL, FB_B_CELL + 1}
    def mut_map(code, attr):
        p = u32(code, MAP_PTR + 4 * LIVE_SLOT)
        struct.pack_into("<H", code, y_off(p, MAP_N, 9), 1030)         # a stray map edit
        attr |= {y_off(p, MAP_N, 9), y_off(p, MAP_N, 9) + 1}           # ... even if ATTRIBUTED
    def mut_pack(code, attr):
        code[PACK_LO + 2] = (code[PACK_LO + 2] + 1) & 0xFF             # break the 427 instrument
        attr |= {PACK_LO + 2}
    def mut_gain(code, attr):
        struct.pack_into("<H", code, GAIN_CELL, 5347)
        attr |= {GAIN_CELL, GAIN_CELL + 1}
    def mut_taper(code, attr):                                         # the driver-torque cliff
        p_ = u32(code, 0xCBA04 + 4 * LIVE_SLOT)
        code[y_off(p_, 4, 0)] ^= 0x01
        attr |= {y_off(p_, 4, 0)}
    def mut_cave(code, attr):
        code[CAVE14A_LO + 4] ^= 0x01
        attr |= {CAVE14A_LO + 4}
    # 🛑 adversary C's DEFECT C4-2 additions -- an INTERIOR knot moved to a WRONG NEW value that
    #    keeps the SAME differing-byte WIDTH as the intended write (120->121, 0->1 both differ in one
    #    byte from their base value), so the [9] diff-COUNT check cannot see it, and an interior knot
    #    (never Y[0]/Y[-1]) so the [10] rail/[11] tag checks cannot see it either.  Only the new FULL
    #    Y-TUPLE CENSUS above catches these.  KP_N = 5 knots (0..4): index 2 is interior on every
    #    record.  KD_N = 4 knots (0..3): index 1 is interior.  Slot 0 stands in for "a non-live
    #    record" -- reachable-but-uncovered per sec.[5], and in scope under KP_SCOPE/KD_SCOPE "all".
    def mut_kp_interior_live(code, attr):
        p = u32(code, KP_PTR + 4 * LIVE_SLOT)
        struct.pack_into("<H", code, y_off(p, KP_N, 2), 121)      # ONE interior knot, 120 -> 121
    def mut_kp_interior_nonlive(code, attr):
        p = u32(code, KP_PTR + 4 * 0)                             # slot 0, a NON-LIVE record
        struct.pack_into("<H", code, y_off(p, KP_N, 2), 121)      # ONE interior knot, 120 -> 121
    def mut_kd_interior(code, attr):
        p = u32(code, KD_PTR + 4 * LIVE_SLOT)
        struct.pack_into("<H", code, y_off(p, KD_N, 1), 1)        # ONE interior knot, 0 -> 1

    cases = [("fb clamp 0 -> 1", mut_fb), ("Kd knot left at 128", mut_kd),
             ("Kp knot left at 248", mut_kp), ("Kp flat at the WRONG level 121", mut_kp_level),
             ("r24 4725 -> 4722 (V291 D2)", mut_r24), ("a stray map Y edit", mut_map),
             ("the 427 tap corrupted", mut_pack), ("the forward gain moved", mut_gain),
             ("an override-taper byte moved", mut_taper), ("the 0x14A cave corrupted", mut_cave),
             ("D clamp 0 -> 1", mut_dclamp), ("an always-on taper knot moved", mut_taperA),
             ("the WRONG mute: fb pole b := 0", mut_polemute),
             ("adv C: Kp interior knot 120->121, LIVE record", mut_kp_interior_live),
             ("adv C: Kp interior knot 120->121, slot 0 (non-live)", mut_kp_interior_nonlive),
             ("adv C: Kd interior knot 0->1, LIVE record", mut_kd_interior)]
    out = []
    for name, fn in cases:
        # collect=True: run to the END and report EVERY assertion the mutation trips, not just the
        # first.  A mutation caught only by the diff COUNTER is weaker evidence than one caught by a
        # semantic check as well, and this is the only way to see which.
        try:
            r = build(quiet=True, do_rwd=False, base_bytes=base, mutate=fn, collect=True,
                      r24_arm=4725 if "r24" in name else None)
            fails = r["run"].failures
        except SystemExit as e:
            fails = [("S", str(e).replace("ASSERTION FAILED: ", ""))]
        except Exception as e:                                          # a raise is also a catch
            fails = [("S", f"{type(e).__name__}: {e}")]
        out.append((name, fails))
    return out


def main():
    base = Path(plain_image_path(BASE_NAME)).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise SystemExit("V282 base sha256 mismatch -- refusing to go further")
    # 🛑 TRIPWIRE: V282's own .rwd is the flight article on the car's lineage and this script never
    #    writes it.  Check that it is still what the record says, so a stray write is visible here
    #    rather than at flash time.  Reported, never silently skipped.
    # 🛑 `*V282*` also matches every later build whose tag says "V282BASE" -- match the V282 BUILD.
    v282rwd = [f for f in Path(RWD_DIR).glob("*-V282-*") if not f.name.startswith("SUPERSEDED")]
    if len(v282rwd) == 1:
        got = hashlib.sha256(v282rwd[0].read_bytes()).hexdigest()
        print(f"      V282 rwd on disk: {'UNCHANGED' if got == V282_RWD_SHA else '🛑 CHANGED'} "
              f"({got[:16]}...)  {v282rwd[0].name[:60]}")
        if got != V282_RWD_SHA:
            raise SystemExit("V282's own .rwd has changed -- stopping.")
    else:
        print(f"      (V282 rwd not uniquely present: {len(v282rwd)} match(es) -- tripwire SKIPPED "
              f"and reported, not silently passed)")

    if "--grid" in sys.argv:
        print("=" * 118)
        print("  [0] ZERO-EDIT CONTROL -- every edit disabled must reproduce the V282 base BIT FOR BIT")
        print("=" * 118)
        sha0, d0, a0 = zero_edit_control(base)
        print(f"      sha256 {sha0}")
        print(f"      V282   {BASE_SHA}")
        print(f"      {'[PASS]' if sha0 == BASE_SHA else '[FAIL]'} zero-edit rebuild == V282 base "
              f"({d0} differing bytes, {a0} attributed)")
        if sha0 != BASE_SHA:
            raise SystemExit("ZERO-EDIT CONTROL FAILED -- every hash below would be suspect")

        print("\n" + "=" * 118)
        print("  [0b] THE DOSE GRID -- dry run, NOTHING WRITTEN")
        print("=" * 118)
        hdr = (f"      {'KP':>4} {'R24':>5} {'KD_METHOD':>10} {'KD_SC':>6} {'KP_SC':>6} | "
               f"{'diff':>5} {'blk':>3} {'railT':>6} {'Prail':>6} | image sha256[:16]   "
               f"rwd sha256[:16]")

        def row(tag, **kw):
            kk = dict(DEFAULT)
            kk.update(kw)
            r = build(quiet=True, base_bytes=base, **kk)
            pk = r["table"][-1][1]["T"]
            rl = next((i for i in range(241)
                       if surface(r["code"], LIVE_SLOT, i, 0, r["cal"])["rail"]), None)
            kds_ = kk["kd_scope"] if KD_METHOD_BANK[kk["kd_method"]] else "-"
            print(f"      {kk['kp_flat']:>4} {kk['r24_arm']:>5} {kk['kd_method']:>10} {kds_:>6} "
                  f"{kk['kp_scope']:>6} | {r['diff']:>5} {len(r['blocks']):>3} "
                  f"{pk:>6} {str(rl):>6} | {r['img_sha'][:16]}   {r['rwd_sha'][:16]}  {tag}")
            return r

        RULE = (PREREG["kp_flat"], PREREG["r24_arm"])
        print("      THE r24 LADDER at the ruling's KD_METHOD and KP_SCOPE, at KP 120 and 119:")
        print(hdr)
        for kp in KP_CHOICES:
            for r24 in R24_CHOICES:
                row("<-- THE RULING" if (kp, r24) == RULE else "", kp_flat=kp, r24_arm=r24)
        print("\n      THE THREE KD_METHODs at the ruling's dose:")
        print(hdr)
        for km in [x for x in KD_METHODS if x != "none"]:
            row("<-- THE RULING" if km == PREREG["kd_method"] else "", kd_method=km)
        print("\n      THE THREE KP_SCOPEs at the ruling's dose:")
        print(hdr)
        for kps in [x for x in KP_SCOPES if x != "none"]:
            row("<-- THE RULING" if kps == PREREG["kp_scope"] else "", kp_scope=kps)
        print("\n      THE Kd BANK SCOPE, with KD_METHOD = both:")
        print(hdr)
        for kds in [x for x in KD_SCOPES if x != "none"]:
            row("<-- THE RULING" if kds == PREREG["kd_scope"] else "", kd_scope=kds)
        print("\n      🛑 THE ORIGINAL BRIEF vs THE RULING.  The brief is SUPERSEDED by the")
        print("         orchestrator's 2026-09-13 ruling (KP_SCOPE all, KD_METHOD both) and by the")
        print("         pre-registration's r24 = 2048.  Both built here; NEITHER written.  Sec.2c.")
        print(hdr)
        row("<-- the ORIGINAL BRIEF, superseded", **BRIEF)
        row("<-- THE RULING / pre-registration", **PREREG)

        print("\n" + "=" * 118)
        print("  [0c] MUTATION TEST -- flip each edit and prove the script FAILS")
        print("=" * 118)
        bad, res = [], mutation_test(base)
        for name, fails in res:
            print(f"      {'[CAUGHT]' if fails else '🛑 [MISSED]'} {name:34s} "
                  f"{len(fails)} assertion(s) fire")
            for _k, m in fails[:4]:
                print(f"                   - {m.split('.')[0][:104]}")
            if len(fails) > 4:
                print(f"                   - ... and {len(fails) - 4} more")
            if not fails:
                bad.append(name)
        print(f"      {'[PASS]' if not bad else '[FAIL]'} {len(res) - len(bad)}/{len(res)} "
              f"mutations caught" + (f"  MISSED: {bad}" if bad else ""))
        return

    r = build()
    if os.environ.get("ACCORD_V293_SCRATCH", "").strip():
        scr = os.environ["ACCORD_V293_SCRATCH"].strip()
        Path(scr, r["img_name"]).write_bytes(r["code"])
        Path(scr, r["rwd_name"]).write_bytes(r["rwd"])
        print(f"\n      scratch copy written to {scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        print("\n  [14] WRITE -- guarded BEFORE the write")
        out_img = Path(plain_image_path(r["img_name"]))
        out_rwd = Path(RWD_DIR, r["rwd_name"])
        paths = {"V293 image": out_img, "V293 rwd": out_rwd}
        over = {k: len(str(v)) for k, v in paths.items() if len(str(v)) > MAX_PATH}
        for k, v in paths.items():
            print(f"      path len {len(str(v)):3d}/{MAX_PATH}  {k}")
        if over:
            raise SystemExit(f"PATH TOO LONG for this machine's {MAX_PATH}-char limit: {over}")
        pre_i = [f.name for f in Path(ANALYSIS_ROOT).glob("_v293*") if not f.name.startswith("SUPERSEDED")]
        pre_r = [f.name for f in Path(RWD_DIR).glob("*-V293-*")
                 if not f.name.startswith("SUPERSEDED")]
        if pre_i or pre_r:
            raise SystemExit(f"WRITE GUARD: a non-superseded V293 artifact already exists "
                             f"({pre_i}, {pre_r}).  Refusing to overwrite.")
        with open(out_img, "xb") as fh:                       # 'xb': the OS refuses an overwrite too
            fh.write(r["code"])
        with open(out_rwd, "xb") as fh:
            fh.write(r["rwd"])
        assert hashlib.sha256(out_img.read_bytes()).hexdigest() == r["img_sha"]
        assert hashlib.sha256(out_rwd.read_bytes()).hexdigest() == r["rwd_sha"]
        left_i = sorted(f.name for f in Path(ANALYSIS_ROOT).glob("_v293*")
                        if not f.name.startswith("SUPERSEDED"))
        left_r = sorted(f.name for f in Path(RWD_DIR).glob("*-V293-*")
                        if not f.name.startswith("SUPERSEDED"))
        assert left_i == [r["img_name"]] and left_r == [r["rwd_name"]], (left_i, left_r)
        print("\n      WROTE image + rwd, both re-hashed from the filesystem")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V293_WRITE=rwd to emit the files.")
        print("      Run with --grid for the zero-edit control, the dose grid and the mutation test.")


if __name__ == "__main__":
    main()
