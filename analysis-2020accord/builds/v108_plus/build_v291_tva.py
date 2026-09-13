# -*- coding: utf-8 -*-
r"""V291 -- V282 + OPEN THE LKAS RATE LOOP AT HIGH FREQUENCY, PAID FOR BY A PARTIAL REVERT OF LEVER B.

THREE CAL HALFWORDS, ZERO CODE BYTES on the control path:
    0xC63E8  `a`  fb-lag pole feedback coefficient   923  -> 950 (C12) / 962 (C10) / 974 (C8)
    0xC63EA  `b`  fb-lag pole input coefficient     1560  -> 1143 (C12) / 958 (C10) / 772 (C8)
    0xC6446  r24 ENGAGED gain arm (V84's Lever B)   5244  -> 4923 (C12) / 4725 (C10) / 4512 (C8)
plus the 4-byte CRC trailer of the 0xC6000 cal page.

OPTIONALLY (TELEMETRY_BIT, default "b3") ONE MORE DISPLACEMENT HALFWORD, read-only, inside the
already-flown 0x14A telemetry cave -- it repoints ONE sign rung onto the fb-lag filter's own state:
    TELEMETRY_BIT = "b3"  0xC4BAA  -0x3680 (0xC981) -> -0x3D30 (0xC2D1)   ** RECOMMENDED, see sec.5 **
    TELEMETRY_BIT = "b7"  0xC4B94  -0x6B4C (0x94B4) -> -0x3D30 (0xC2D1)
    TELEMETRY_BIT = "off" the cave stays byte-identical to V282 and the pole move has NO instrument
plus the 4-byte CRC trailer of the block that owns the cave.  `hw1` (0x3724) is NOT touched in either
case -- exactly the V282 class of edit.  The b3 rung is ALREADY an `ld.w`, so on the default the load
WIDTH does not even change: only the 16-bit displacement moves.

=== 0. 🛑 WHAT THIS BUILD IS, IN ONE PARAGRAPH ====================================================
The 18-22 Hz grinding is an EXCITED PLANT MODE that the LKAS rate loop DE-DAMPS: at plant damping
zeta_p = 0.05 the V282 loop drives the 20 Hz mode to zeta = -0.019, i.e. unstable
(`DESIGN-V291-FBLP-2026-09-13.md` sec.7).  Lowering the feedback-lag pole collapses the loop's return
ratio over the whole 12-26 Hz band and returns the mode to positive damping -- the ONLY candidate ever
scored in this kit that improves zeta, Ms over 12-26 Hz, phase margin, gain margin, HF motor noise AND
transient authority at once, with 0/121 unstable fits.  It is blocked by exactly one thing: a roll-off
IS phase lag below its corner, and the operator's 7.3 Hz gate prices lag at 0.55 per radian against the
r24 pump's FIXED arm LR73 = 1.19 angle -27 deg.  `gate73` goes 1.0028 -> 1.0750 at the mildest dose,
7.5x over the whole allowance, and the memo's body verdict is DO NOT BUILD **for the pole alone**.
V291 pays the gate by SHRINKING THE ARM: cutting 0xC6446 scales `LR73`, and a 6.1 % cut restores
gate73 = 1.010 at the 11.94 Hz pole, 13.9 % at 7.97 Hz (memo ADDENDUM A2).  The r24 cut is a REVERT of
a non-stock V84 edit (stock = 512), not a new lever -- a materially safer byte class.

🛑 THE HONEST CAVEAT, STATED BEFORE THE NUMBERS, NOT AFTER:
   **EVERY 20 Hz NUMBER IN A2 IS SERVO-SIDE ONLY.**  The 304-fit plant `G` was identified with r24 at
   5244 *inside* it, so scaling r24 changes the plant and the zeta / Ms / ring / pkR columns do NOT
   include that change.  They are the k = 1 values.  The record also disagrees with itself on r24's
   20 Hz sign -- `accord-r24-pumps-at-7hz-and-damps-at-20hz` says r24 **damps** at 20 Hz, while
   `grind_loop_shape.py` sec.G measured 5244 -> 512 improving **both** bands (18-22 x0.81, 7-9 x0.64).
   If r24 damps at 20 Hz, this build's two edits fight each other there.  **That disagreement is NOT
   resolved.  It is the single largest open risk on this image and it must be said to the operator.**
   `gate73` itself is plant-free, so the 7 Hz side of the trade does not depend on the resolution.

=== 1. THE TWO DOSES ============================================================================
`DOSE` (below, or env ACCORD_V291_DOSE) selects one; every output name carries it.  The default is
**not a recommendation** -- the orchestrator picks the dose at write time.

   dose   a     b      realised corner   realised DC     r24 arm   r24 cut   gate73 (A2)   ring (memo sec.3)
   C12   950   1143     11.9382 Hz       30.8919         4923      -6.12 %    1.0750 -> ~1.010   249 ms (x2.34)
   C10   962    958      9.9404 Hz       30.9032         4725      -9.90 %    1.1163 -> ~1.010   180 ms (x3.23)
   C8    974    772      7.9674 Hz       30.8800         4512     -13.96 %    1.1624 -> ~1.010   137 ms (x4.25)
   --    923   1560     16.5271 Hz       30.8911         5244       --        1.0028             582 ms  (V282)

🛑 THE r24 INTEGERS ROUND **DOWN**, DELIBERATELY.  The memo's A2 table gives the multiplier k that
restores gate73 = 1.010 as 0.9390 (C12) / 0.9012 (C10) / 0.8605 (C8).  Rounding k*5244 UP lands on the
WRONG SIDE of the gate; each value above is the rounded-DOWN integer, so the realised k is 0.938787 /
0.901030 / 0.860412 -- at or below the requirement at every dose, never above.  Asserted at [3] against
the memo's published k, not against a constant restated here.

Both clear the kit's x1.22 readability floor (`V290-ROWS-READABILITY-2026-09-09.md`) by a wide margin;
the pole-only frontier did not, which is why the pole alone was refused.
DC is held to 0.003 % (C12) / 0.036 % (C8) of V282's 30.8911, so **steady-state feedback gain and
therefore steady-state authority are unchanged** (memo G1).  Asserted at [3] from the written integers.

=== 2. THE FIRST EDITED PATH, MIRRORED EXACTLY FROM THE DISASSEMBLY ==============================
The LKAS rate-PID feedback-lag filter, FUN_00028ea6 @ 0x28F4C-0x28FBE, Ts = 1 ms.  V850 is
little-endian and `sar` is an ARITHMETIC shift (floors toward -inf).  Instruction addresses inline;
byte-exact source `docs/traces/TRACE-2026-09-13-fb-lag-filter-bytes.md` sec.1, re-read from the image
at [2] of this script.

    def lkas_fb_lag(x, s, sentinel_ok, a, b, C):
        # x = ld.h -0x6a56[gp]  @0x28F4C   SIGNED 16-bit steering rate, 8 raw counts per deg/s,
        #     already SATURATED to +-12000 by its producer at 0x3F7B8/0x3F7D0/0x3F7E0
        if not (-12000 <= x <= 12000):       # 0x28F50 addi 0x2ee0 / 0x28F54 addi -0x5dc1 / 0x28F58 bnc
            return 0, s, False               #   -> BAIL 3 to 0x290B0: r25 := 0, r26 := 0, sentinel := 2
        if not sentinel_ok:                  # 0x28F72 cmp 0x1,r9 / 0x28F76 bne 0x28F82
            s = 0                            # 0x28F84 mov 0x0,r26   COLD START
        # b = ld.hu 0x73ea[tp] @0x28F86  UNSIGNED     a = ld.h 0x73e8[tp] @0x28F8A  ** SIGNED **
        s_new  = (a * x0 if False else (b * x)) >> 10   # 0x28F8E mul r16,r7,r0 ; 0x28F9A sar 0xa
        s_new += (a * s) >> 10                          # 0x28F92 mul r26,r9,r0 ; 0x28FA0 sar 0xa
        #   ^^ TWO SEPARATE floors.  `mul rX,rY,r0` throws the high word of the 64-bit product away,
        #      so every intermediate is low-32 only.  No 16-bit narrowing anywhere in the chain.
        out = s + s_new                      # 0x28FA4 add r9,r26   the TWO-SAMPLE SUM
        s   = s_new                          # 0x28FA8 st.w r9,-0x3d30[gp]   32-BIT state, stored BEFORE
                                             #   the clamp, so the STATE is never clamped
        out = C if out > C else (-C if out < -C else out)    # 0x28FA6..0x28FBC, C = ld.hu 0xC62E6 = 46080
        return out, s, True                  # out -> r26 -> E = 32*sp - r26 @0x29D78

    DC gain      = 2*b / (1024 - a)          the two-sample sum doubles the single-pole DC b/(1024-a)
    corner f_c   = -ln(a/1024) / (2*pi*Ts)   Ts = 1 ms  [EVIDENCE-by-consistency: 923 -> 16.53 Hz and
                                             V289's byte-read 875 -> 25.03 Hz match both build labels]

🛑 THE THREE INTEGER FACTS THAT BOUND THE DOSE, all asserted at [3] from the values actually written:
  (a) `a` is read with **ld.h (SIGNED)**.  a >= 32768 reads NEGATIVE and the filter becomes an unstable
      alternating recurrence.  And a >= 1024 makes the pole >= 1 (pure integrator or divergent).
      Both doses are far below: 950 and 974.  **Assert a <= 1023 strictly.**
  (b) `b` is read with **ld.hu (UNSIGNED)**, cap 65535.  Both doses lower it.
  (c) int32 headroom on `a*s` at the producer's own |x| = 12000 saturation:
      s_ss = b*12000/(1024-a) = 185,351 (C12) / 185,280 (C8);  a*s = 1.76e8 / 1.81e8 against 2^31.
      **x12.20 (C12) / x11.90 (C8).**  No overflow, and the C8 margin is the smaller of the two.

=== 3. THE DEAD ZONE AND THE STICK FLOOR -- read from the trace, re-derived here ==================
`floor(b*x/1024)` is identically ZERO for |x| < 1024/b, so a CONSTANT small rate produces NO state
motion at all -- not attenuation, a dead zone.  And because `sar` floors toward -inf, `s = -1` (and
every |s| < 1024/(1024-a)) is an ABSORBING state, so the filter RESTS NEGATIVE with the wheel still.

   dose   b      f_c        dead zone        = deg/s   sticks below |s| <   resting fb offset (E-counts)
   V282  1560  16.53 Hz   |x| < 0.656 cnt    0.082      10.1                 -20
   C12   1143  11.94 Hz   |x| < 0.896 cnt    0.112      13.8                 -26
   C8     772   7.97 Hz   |x| < 1.326 cnt    0.166      20.5                 -40
   (for scale, the memo's 2 Hz dose -- NOT built -- would be 5.095 cnt / 0.637 deg/s / 78.8 / -156)

⭐ **THE RING IS ABOVE EVERY DEAD ZONE AT BOTH DOSES, by x12 to x21.**  The 18-22 Hz ring at the wheel
is **15.8-28.2 raw counts of x** (memo ADDENDUM A8, which RETRACTS sec.6.3's "0.17-0.28 counts" -- that
number is in ANGLE LSBs, not rate counts, and reading it as rate counts was a factor-of-100 error).
Byte-exact check in A8.2: driven at A = 16 counts the integer filter's measured 20 Hz component is
0.983-1.021 of the linear prediction at every dose.  **The feedback leg is LINEAR at ring amplitude**,
so the linear attenuation figures are the right ones.  The dead zone binds only at NEAR-ZERO rate
(< 0.08-0.17 deg/s) and the stick floor only with the wheel at rest.  Both are pre-existing artefacts
whose WIDTH this build changes by x1.37 (C12) / x2.02 (C8), never their existence.

=== 4. THE SECOND EDITED PATH -- the r24 gain arm, mirrored from 0x3ABFA-0x3AC20 ==================
Confirmed by `disassemble_bytes(0x3ABE0, 72, dry_run)` against the V282 image's own bytes, and by the
two-encoding census at [11] which finds EXACTLY ONE reader of each arm.

    # the 4-way gain_B priority gate, FUN_0003aa2c region
    if gp_0x671d != 0:            # 0x3ABFA cmp r0,r6 / 0x3ABFC be 0x3AC04
        K = cal(0xC6442)          # 0x3ABFE ld.hu 0x7442,tp,r10   = 1024   ** OUTRANKS EVERYTHING **
    elif engaged != 0:            # 0x3AC04 cmp r0,lp / 0x3AC06 be 0x3AC0E   (lp = STEER_CONTROL_ACTIVE
                                  #   since V104 repointed 0x3AA96 c5 -> fb)
        K = cal(0xC6446)          # 0x3AC08 ld.hu 0x7446,tp,r10   = 5244    ** THE CELL V291 EDITS **
    elif r2 != 0:                 # 0x3AC0E cmp r0,r2 / 0x3AC10 be 0x3AC16
        K = cal(0xC6440)          # 0x3AC12 ld.hu 0x7440,tp,r10   = 2048
    r8  = d                       # 0x3AC16 mov r1,r8     d = the 4-tap derivative of bar torque
    r8  = (K * d)                 # 0x3AC18 mul r10,r8,r0            low 32
    r24 = r8 >> 10                # 0x3AC20 sar 0xa,r8               ** Q10 **  -> gain = K/1024

    gain:  5244/1024 = x5.1211 (V282)  ->  4923 = x4.8076 (C12) / 4725 = x4.6143 (C10) / 4512 = x4.4062 (C8)
    stock is 512/1024 = x0.500.  This build reverts 6.1 % / 9.9 % / 14.0 % of a x10.24 non-stock raise.

🛑 **THE r24 ARM INVERSION HAZARD -- PRE-EXISTING, UNCHANGED BY V291, AND IT MUST BE STATED.**
`gp-0x671d` is a SATURATING RISING-EDGE SCHMITT LATCH (writer FUN_00041d56 @0x41EC6, lockstep twin
gp-0x4c24): SET at |x_motor| >= cal(0xC61FA) = 5530, RELEASE at |x_motor| < cal(0xC61F8) = 1024,
counting rising edges, saturating at 255, cleared ONLY by FUN_0003bcb2 @0x3BD2A.  The selector at
0x3ABFA tests **!= 0**, NOT ">= 3" -- so **ONE crossing flips the arm and it stays flipped for the rest
of the drive cycle**, well before the DTC (maturation count cal(0xC6500) & 0xFF = 3) matures.

  arm taken      stock     V282      V291 C12   V291 C10   V291 C8
  engaged 0xC6446  512      5244       4923       4725       4512
  latched 0xC6442 1024      1024       1024       1024       1024
  ratio           x2.00     x0.195     x0.208     x0.217     x0.227

⇒ **On stock the fault arm DOUBLES r24; on every V280+ image it COLLAPSES it.**  V291 does not change
that inversion and does not change its threshold -- it moves the engaged arm 6-14 % closer to the latch
value, i.e. it makes a latch event slightly LESS disruptive.  `gp-0x6ad8` (0x41E5C) mirrors the
monitored magnitude and is never read anywhere in the image -- an inert tap that would settle the
crossing rate at zero risk, if it is ever worth a rung.
**Model r24 as BIMODAL on any post-V280 image, never as a single gain.**
[`.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict.md`]

=== 5. THE TELEMETRY -- ONE SIGN RUNG REPOINTED ONTO THE FILTER'S OWN STATE ======================
🛑 The standing rule: **every build must carry the instrument for its own edit.**  V291 has two edits.

  * **The r24 cut is ALREADY instrumented and needs nothing new.**  b5 and b6 are V282's comparator
    rungs, `|r24| >= |gp-0x6b94 aggregator|` and `|r24| >= |gp-0x6b38 T|`.  They are the POSITIVE
    CONTROL for the r24 edit and they STAY BYTE-IDENTICAL: a -6 to -14 % cut of the arm moves both
    duties down, on the same wire, on any engaged drive.  A comparator needs no scale assumption (the
    V96 law), and both duties were measured live on r32/r34 before V282 flew.
  * **The pole move had NO instrument.**  The state `s` at gp-0x3d30 is invisible: the census at [11]
    finds exactly TWO accesses to it image-wide, both inside the filter (ld.w @0x28F7C, st.w @0x28FA8).
    No side lane, no UDS packer, no diagnostic reader.  Without a probe the pole move is exactly the
    "cal-only edit with no observability" the 2026-08-31 operator instruction names.

WHICH BIT TO SPEND -- **MEASURED, and it is b3, NOT b7.**  Both rungs have the identical form (a
`mov 0,r7` / load / `cmp 0,r6` / `bge +4` / `add <n>,r7` chain sharing one `shl 0x4` and one
`andi 0x67`), so either is a 2-byte displacement edit.  Duties and transition rates read straight off
`0x14A` byte 4 on four V282-class routes (r39 / r3a / r3c / r35), engaged-lateral frames only:

   bit  what it reads today                        duty        transitions/s   verdict
   b7   sign(gp-0x6b4c), the LKAS aggregator term  0.49-0.55    4.8 - 5.5      INFORMATIVE -- keep
   b3   sign(gp-0x3680), base-assist Stage C       0.47-0.48   45.4 - 46.7     ALIASED TO NOISE -- spend
   b4   sign(r24)                                  0.39-0.41    (the control)
   b6   |r24| >= |T|                               0.00-0.16    (r24 instrument, keep)
   b5   |r24| >= |aggregator|                      0.13-0.25    (r24 instrument, keep)

⭐ **b3 transitions 45-47 times a second against a 50/s ceiling at the 100 Hz frame rate.**  Its
underlying quantity flips faster than the frame, so what reaches the wire is an aliased coin flip: duty
0.48, and agreement with b4 (0.57-0.59) barely above chance.  **b3 carries almost no information at the
rate it is sampled.**  b7, by contrast, transitions 4.8-5.5 /s -- a well-resolved, slowly varying sign
-- and `docs/traces/TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md` sec.0/3.2 has now
RESOLVED the old record conflict IN ITS FAVOUR: `gp-0x6b4c` **is** the aggregator term that carries the
LKAS lane, with unit weight.  🛑 **That retires the earlier reading -- including this build's own first
pass -- that b7's meaning was disputed and therefore cheap.  It is not cheap.  b3 is.**
Neither bit is read by any analysis script in the kit today (grepped), so the cost is potential rather
than actual -- but b7's potential is real and b3's is aliased away.

THE EDIT (ONE displacement halfword; no length change, no register change, no width change on b3):
    b3 (default) 0xC4BA8:  24 37 | 81 c9   ld.w -0x3680[gp], r6   -> base-assist Stage C state
                 0xC4BA8:  24 37 | d1 c2   ld.w -0x3d30[gp], r6   -> the fb-lag filter STATE `s`
    b7 (option)  0xC4B92:  24 37 | b4 94   ld.h -0x6b4c[gp], r6   -> the LKAS aggregator summand
                 0xC4B92:  24 37 | d1 c2   ld.w -0x3d30[gp], r6   -> the fb-lag filter STATE `s`
                  ^^^^^ hw1 UNTOUCHED in both.  hw2 bit 0 selects .h (0) vs .w (1); 0xC2D1 is ODD -> ld.w,
                  and the disp field 0xC2D1 & 0xFFFE = 0xC2D0 = -0x3D30.  On b3 the load is ALREADY
                  `ld.w` (hw2 0xC981, odd), so the default edit changes nothing but the displacement.

WHY ld.w AND NOT ld.h:  `s` is a 32-BIT cell and it is NOT clamped (the +-46080 clamp is applied to the
output AFTER the state is stored at 0x28FA8).  Measured on r39/r3a/r3c/r35, |s| exceeds 32767 on
0.18-0.36 % of frames and peaks at 52,821 -- so a 16-bit `ld.h` of the LOW halfword (disp 0xC2D0, even)
would report the WRONG SIGN on about 1 frame in 300, in exactly the high-rate frames.  The 32-bit
load's sign is exact at every amplitude and costs the same two bytes.
ENCODING PROVEN BY A SECOND DECODER: Ghidra's own V850 disassembler reads `24 37 01 b3` at 0x18B62 as
`ld.w -0x4d00, gp, r6` and `24 37 15 c1` at 0x19A98 as `ld.w -0x3eec, gp, r6` -- identical hw1, odd
hw2.  Asserted at [2c].  0xC4BA8 itself is the in-cave instance.

THE DECODER -- CAN 0x14A, 100 Hz, byte 4, AFTER V291 (default TELEMETRY_BIT = "b3"):
    bit 7 (0x80) = 1 iff  gp-0x6b4c < 0   the LKAS lane's aggregator summand   UNCHANGED from V282
    bit 6 (0x40) = 1 iff  |r24| >= |T|           (gp-0x6ada vs gp-0x6b38)      unchanged
    bit 5 (0x20) = 1 iff  |r24| >= |aggregator|  (gp-0x6ada vs gp-0x6b94)      unchanged
    bit 4 (0x10) = 1 iff  r24 < 0                (gp-0x6ada)                   unchanged
    bit 3 (0x08) = 1 iff  s < 0     s = int32 @ gp-0x3d30 = 0xFEDF42D0, the   ** NEW IN V291 **
                   fb-lag state, updated every 1 ms at 0x28FA8.  BEFORE V291 this bit was
                   sign(gp-0x3680), the base-assist Stage C derivative state (V103's rung).
    bits 2-0     = STOCK HONDA.  The cave NEVER writes them (the andi 0x67 at 0xC4BB8 preserves them).
  SIGN CONVENTION: the rung is `cmp 0,r6 ; bge +4 ; add <n>,r7`, so the bit is SET iff the loaded value
  is STRICTLY NEGATIVE.  s == 0 reads as bit CLEAR.
  🛑 **ATTRIBUTE THE BUILD FROM THE TAP, NOT THE LABEL** -- a decoder pointed at V282's b3 reads
  nonsense on V291 and vice versa.  With TELEMETRY_BIT = "b7" the two meanings swap places instead.

WHAT THE NEW BIT BUYS, SIZED OFFLINE ON FOUR REAL ROUTES (`rlog-tools/studies/grind/
v291_b7_state_sign_sizing.py`; the byte-exact mirror below driven by each route's own 0x18F
STEER_ANGLE_RATE in raw counts, upsampled 100 Hz -> 1 kHz; both linear and zero-order-hold
reconstructions run, and the RATIO columns agree between them):

  statistic                                     V282       C12        C10        C8
  TRANSITIONS per second, engaged               5.2-7.6   x0.863     x0.785     x0.695
    range over the four routes                            .843-.872  .762-.805  .683-.712
  TRANSITIONS per second, hands-off creep       3.5-4.8   x0.869     x0.816     x0.760
  duty( sign(s) != sign(0x18F rate) ), engaged  0.18-0.26 x1.048     x1.071     x1.101

⭐ **THE TRANSITION RATE IS THE READOUT, NOT THE DUTY.**  x0.70 (C8) / x0.86 (C12) reproduces to +-0.02
across four routes AND two reconstructions; the duty moves only x1.05-1.10 and its own baseline shifts
x1.13 between reconstructions, i.e. the reconstruction noise exceeds the signal.  Both statistics come
off the same published bit, so nothing is lost -- only the analysis changes.
⭐ AND THE NEW BIT LANDS IN THE RESOLVABLE REGIME: sign(s) is predicted at 3.5-7.6 transitions/s, the
same band b7 occupies today and an order of magnitude below the 50/s aliasing ceiling that makes b3
useless.  **The repoint moves the slot from a quantity too fast to sample onto one well inside the
frame rate.**
🛑 **Score it WITHIN-DRIVE against the mirror, never cross-build.**  The V282 baseline rate ranges
5.2-7.6 /s across routes, so a cross-route contrast is confounded by traffic.  Replay the flown drive's
OWN 0x18F trace through the mirror at BOTH the V282 pole and the flown pole and ask which predicts the
observed rate: the predictions differ by 18 % (C12) / 27 % (C10) / 31 % (C8) while the ambiguity
is 2 %.  A LIVENESS AND DOSE test that accrues on ordinary engaged driving, symptom or no symptom.
⚠ **Per-FRAME agreement is NOT a clean test**: sign(s) differs between the V282 and C8 poles on only
3.3-4.4 % of frames while the reconstruction ambiguity is 2.0-3.4 %.  Use the aggregate rate.

POSITIVE CONTROL / FAIL MODE for the repoint itself: on V282 the spent bit reads duty 0.47-0.48 with
45-47 transitions/s (b3) or 0.49-0.55 with 4.8-5.5 /s (b7).  After V291 that slot must read 3.5-7.6
transitions/s AND track the mirror.  A slot still reading 45+ /s (b3), or still matching
sign(gp-0x6b4c) (b7), means the displacement did not land.  A slot stuck at 0 or 1 over >= 20 s engaged
means the cave stopped firing -- b5/b6 staying live separates those two cases.

GATE 1 (RAM ownership): the cave gains a READER and no writer.  gp-0x3d30 is 32-bit aligned
(0xFEDF42D0), so a 32-bit load cannot tear against the filter's 32-bit store.  GATE 2 (closed-loop
stability): not applicable -- the rung writes no control cell and changes no timing (one 4-byte load
replaced by one 4-byte load).  Set TELEMETRY_BIT = "off" to build with the cave byte-identical; the
pole move then has no instrument at all, which the standing instruction forbids without a stated reason.

=== 6. THE DELIVERED SURFACE -- READ FROM THE BUILT IMAGE, NOT FROM THESE CONSTANTS ===============
Asserted at [12] against the image's own bytes:
    peak delivered forward torque = clamp(cal(0xC61BE) * cal(0xC6CD0) >> 15, +-cal(0xC61B4))
                                  = (15360 * 5346) >> 15 = **2505 counts**, clamp (3072) does NOT bind
    assist-map top (X = 240)      = **1032** = x6.00 of Honda's 172; slope 4.30 flat at every knot
    Kp                            = **248 flat**;  Kd = **128 flat**;  Ki = **0**
**UNCHANGED BY V291 AT EITHER DOSE.**  This build moves no forward-path cell: not the map, not the
gain, not either clamp, not Kp/Kd/Ki.  It moves only the FEEDBACK pole and the r24 lane's gain.
DC feedback gain is held to 0.036 %, so steady-state authority is unchanged too.

=== 6b. WHERE THE EDITED LANES LAND -- and the DEAD TWIN that must not be patched =================
[`docs/traces/TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`, EVIDENCE, instruction-anchored]

    FUN_00028ea6 (1 kHz, jarl from 0x22522)
      0x2a23c  st.h r1,-0x6b38[gp]     T = clamp((y*gain)>>15, +-0xC61B4)   <- the 427 tap's source
      0x2a2c2  cmove 0x0,r1,r16        the engagement gate
      0x2a2ea  st.h r16,-0x6b3c[gp]    gated T                    *** THE LIVE FORWARD ***
    FUN_0002b422 -> mode bank slot 1 -> FUN_00026c80
      0x276f0  st.h r8,-0x6b4c[gp]     gp-0x6b4c = clamp(sum, +-0x2800)
                 |
                 +-- 0x3aa3e ld.h -0x6b4c[gp],r6   FUN_0003aa2c   DIRECT summand, ** UNIT WEIGHT **
                 +-- 0x3816c ld.h -0x6b4c[gp],r14  -> gp-0x6ad6 -> gp-0x6ad4, a second indirect route
    r24: 0x3ac20 sar 0xa -> gp-0x6ada -> the SAME aggregator FUN_0003aa2c, also unit weight
      => r24 and the LKAS lane meet at gp-0x6b94 as unit-weight siblings, 1 : 1 at the motor.
         That is why V291's two edits trade against each other on one summing junction.

🛑 **THE LIVE FORWARD IS 0x2A2EA, NOT 0x2B41C.**  `0x2A30E-0x2B421` is a 4,372-byte UNCALLED ISLAND --
six functions, zero callers by three independent methods -- and it is a near-duplicate of the live LKAS
output path.  The older record's "T is forwarded to gp-0x6b3c @0x2B41C" names the DEAD copy.  Anyone
patching 0x2B41C would patch dead code and see nothing on the car.
**NEITHER CELL V291 EDITS IS READ ANYWHERE IN THAT ISLAND** -- asserted at [11] by a byte scan of the
BUILT image restricted to [0x2A30E, 0x2B422), and POSITIVELY CONTROLLED by the island's own reads of
the OUTPUT-lag pole (0xC63EC @0x2A8A2, 0xC63EE @0x2A892) and of the D clamp (0xC61B6 @0x2ADD4/DC/EC).
The scan finds those, then finds nothing for 0xC63E8 / 0xC63EA / 0xC6446, so the null is worth
something.  ⇒ V291 cannot be silently half-applied through a dead twin, in either direction.

=== 7. WHAT THIS BUILD DOES *NOT* CHANGE ========================================================
Kp record 0xE5378 (flat 248) - Kd record 0xE511C (flat 128) - Ki 0xC63E6 (0) - forward clamps
0xC61B2/B4 (3072/3072) - D clamp 0xC61B6 (10240) - post-lag deadband 0xC61B8 (102) - anti-windup
0xC61BA (10240) - P clamp 0xC61BC (15360) - sum clamp 0xC61BE (15360) - output-lag pole 0xC63EC/EE
(992/507) - feedback clamp 0xC62E6 (46080) - private forward gain 0xC6CD0 (5346) - r24 latch arm
0xC6442 (1024) and the other gate arms 0xC6440/44/48/4A - the Coulomb deadband 0xC61F6 (3) and the
latch thresholds 0xC61F8/FA (1024/5530) - the EME quads 0xC674E/0xC6750/0xC675A/0xC675C and ramp
0xC6768/6A/6C and their float mirrors - the assist map family - the tapers - the 427 torque tap
0x55DF0-0x55E11 - the cave hook 0x55C0E - **every code byte in [0x13000, 0xC0000)**.
With TELEMETRY = False the cave 0xC4B34-0xC4BD7 is byte-identical too; with TELEMETRY = True exactly
two bytes of it move and they are a load DISPLACEMENT.

=== 8. THE SENTENCE A NULL WOULD LICENSE -- WRITTEN BEFORE THE DRIVE ==============================
"If b7's transition rate matches the C8 (or C12) mirror -- confirming the pole is live at the flown
dose -- and b5/b6's duties fall as the r24 cut predicts -- confirming the arm moved -- and the 18-22 Hz
envelope of the 427 torque tap on hands-off creep is UNCHANGED, then the 20 Hz mode's damping is not
set by the LKAS rate loop's return ratio at 20 Hz, and the WHOLE in-loop loop-shaping class is closed."
That sentence is writable because both edits carry their own instrument and both instruments read out
on ordinary engaged driving rather than needing a symptomatic episode.

🛑 PRE-REGISTERED REVERT SIGNATURES (memo sec.10; these bind whichever dose flies):
  6-9 Hz    ANY return of the 7 Hz strong-turn cycle V281 rev 3 removed -- F7 episodes >= 2 per 100 s,
            or ripple/level >= 0.25 on the torque tap in loaded turns.  **This is the predicted failure
            mode and it is what the r24 cut is there to prevent.  If it fires, the r24 cut was too
            small or `LR73 proportional to the r24 gain` is false.**  REVERT.
  6.9-12 Hz a NEW line where none existed; max Ms over 3-12 Hz rises 1.2 -> 1.7 (C12) / 3.2 (C8), and
            its frequency identifies the dose.
  8-17 Hz   a LOW-PITCHED component at 17.1 Hz (C12) / 13.5 Hz (C8), zeta +0.36..+0.54, so it should
            NOT be audible.  If it IS audible the plant family is wrong -- itself the finding.
  18-22 Hz  the target.  Grinding unchanged or louder => the in-loop class is closed.
  22-30 Hz  any new line.  Predicted ABSENT; its appearance falsifies the fit family (the V289 trap in
            mirror image -- V289's ring MOVED to 15-17 Hz rather than going away).
  feel      wheel-rate overshoot on a command step rises from ~39 % toward 49 % (C12) / 60 % (C8); a
            "loose" or "darty" feel on lane-centring corrections, more return-to-centre hunting.
            Separately, the r24 cut removes 6-14 % of the base-assist rate lane: watch for LESS damping
            of on-centre wheel motion and for any change in the 20 Hz grinding in EITHER direction.
  creep     a one-sided standing pull at rest, or step-like "notchiness" as |rate| crosses 0.11-0.17
            deg/s (the widened dead zone).  Pre-existing on V282 at 0.08 deg/s.
  openpilot |T(3.9 Hz)| rises x1.03 (C12) / x1.11 (C8) with +3.1 / +8.1 deg of PHASE LEAD; |dL| below
            5 Hz 11 % / 28 %.  The fork's lateral tune sees a slightly livelier plant.
**Cost FAIL outranks every number: any report of weaker or slower response, any new vibration or noise,
or any worsening of grinding, vibrating, micro-ratcheting, ratcheting or excess friction.  Report the
operator's own words.  An absence of a complaint is not a cure.**

=== 9. CLASS OF BUILD -- HOW IT DIFFERS FROM THE RECENT ARC ======================================
The post-V38 arc: V38-V52 authority/filters/poles/caves - V53-V61 telemetry probes - V62-V73 the rate
lane - V74-V83a the base-assist damper - V84 damper reverted - V101/V102/V112 the forward gain -
V276/V278/V280 the assist map (the REFERENCE) - V281r3 Kp - V283 Ki - V284/V285 Kp again - V287 the D
clamp - V288 a setpoint PRE-FILTER (reference side, null) - V289 a NOTCH on the loop output plus the fb
pole pushed UP to 25 Hz (flew; the ring MOVED to 15-17 Hz) - V290 designed and NOT cut.

**V291 is the first build in the whole arc to move the feedback pole DOWNWARD, and the first ever to
move TWO loop elements in OPPOSITE directions to buy a gate.**
  * The fb pole has been moved exactly once before, by V289, and **UPWARD** (16.53 -> 25 Hz).  This is
    the same cell pushed the OTHER WAY -- a different claim from "a new lever", and the operator is
    entitled to be told so.  The one prior downward scoring (`grind_loop_shape.py:463-464`, 2026-09-03)
    was DEFECTIVE: its "5.0 Hz" row (994, 690) carries DC 46.000, x1.49 the held value, i.e. a pole
    move PLUS a 49 % feedback-gain rise.  **A clean DC-held test below 16.5 Hz had never been run.**
  * `0xC6446` has moved before (V67 -> V88's 5244, frozen since V247, 60+ builds).  V291 is the FIRST
    DOWNWARD move of it since V88, and it is a partial REVERT toward stock (512), not a new raise.
  * What is genuinely new is the PAIRING.  Neither edit alone survives: the pole alone fails the 7 Hz
    gate at 7.5x the allowance; the r24 cut alone re-opens the 20 Hz grinding the record says it damps.
    The claim under test is that they cancel on the 7 Hz gate and add on the 20 Hz mode.
  * ⚠ **THAT CLAIM RESTS ON AN UNMEASURED ASSUMPTION** -- `gate73` hard-codes `LR73` and nothing in the
    kit has measured how the 7.3 Hz pump arm scales with 0xC6446.  The extension `gate_k = |LS73*R73 +
    k*LR73|` is declared as an EXTENSION of the record's gate, not the record's gate.  [BELIEF]
"""
import hashlib
import math
import os
import struct
import sys
import zlib
from pathlib import Path

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
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
GP_BASE, TP_BASE = 0xFEDF8000, 0xBF000
TICK_S = 0.001                    # Ts = 1 ms.  EVIDENCE-by-consistency (two label<->byte agreements),
                                  # not a scheduler read.  Used for the printed corner only.
WRITE_MODE = os.environ.get("ACCORD_V291_WRITE", "").strip().lower()
FULL = ("--full" in sys.argv) or os.environ.get("ACCORD_V291_FULL", "") == "1"

# ---- THE DOSE SWITCH ------------------------------------------------------------------------------
# The default is NOT a recommendation.  The orchestrator selects the dose at write time.
DOSE = os.environ.get("ACCORD_V291_DOSE", "C12").strip().upper()
# ---- THE TELEMETRY SWITCH -------------------------------------------------------------------------
# "b3"  -> the b3 rung repointed onto the fb-lag state.  ** RECOMMENDED AND DEFAULT ** -- b3 is measured
#          ALIASED (45-47 transitions/s against a 50/s ceiling) so it carries almost nothing today,
#          while b7 is a well-resolved sign of the LKAS aggregator summand.  Docstring sec.5.
# "b7"  -> the b7 rung repointed instead, keeping b3.  Costs the informative bit; offered because the
#          orchestrator's brief named b7 before the aliasing was measured.
# "off" -> the cave stays byte-identical to V282 and the pole move has NO instrument.
TELEMETRY_BIT = os.environ.get("ACCORD_V291_TELEMETRY_BIT", "").strip().lower()
if not TELEMETRY_BIT:      # legacy switch kept working: ACCORD_V291_TELEMETRY=0 means "off"
    TELEMETRY_BIT = "off" if os.environ.get("ACCORD_V291_TELEMETRY", "1").strip() in \
        ("0", "false", "no") else "b3"
assert TELEMETRY_BIT in ("b3", "b7", "off"), f'TELEMETRY_BIT must be b3 / b7 / off, got {TELEMETRY_BIT!r}'
TELEMETRY = TELEMETRY_BIT != "off"

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080"
             ".TORQUE.TAP_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
BASE_RWD_SHA = "618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"

# ---- [A] the three edited cal cells, their readers, and the base values ---------------------------
FB_A_CELL, FB_A_OLD = 0xC63E8, 923          # ld.h   0x73e8[tp] @0x28F8A   ** SIGNED **
FB_B_CELL, FB_B_OLD = 0xC63EA, 1560         # ld.hu  0x73ea[tp] @0x28F86   UNSIGNED
R24_CELL, R24_OLD = 0xC6446, 5244           # ld.hu  0x7446[tp] @0x3AC08   Q10, ENGAGED arm
FB_A_LOAD, FB_A_LOAD_BYTES = 0x28F8A, bytes.fromhex("254fe873")   # ld.h  0x73e8,tp,r9
FB_B_LOAD, FB_B_LOAD_BYTES = 0x28F86, bytes.fromhex("e587eb73")   # ld.hu 0x73ea,tp,r16
R24_LOAD, R24_LOAD_BYTES = 0x3AC08, bytes.fromhex("e5574774")     # ld.hu 0x7446,tp,r10
R24_SIBLINGS = {0x3ABFE: (0xC6442, "the gp-0x671d LATCH arm -- outranks all"),
                0x3AC12: (0xC6440, "the r2 arm")}
FB_X_SAT = 12000                             # producer saturation at 0x3F7B8/D0/E0
FB_CLAMP_CELL, FB_CLAMP = 0xC62E6, 46080     # ld.hu, applied to the OUTPUT, never to the state
DC_TARGET = 3120.0 / 101.0                   # V282's 2b/(1024-a) = 30.8911
DC_TOL = 0.002                               # 0.2 %, per the brief

# `k_gate` is the memo's OWN published multiplier that restores gate73 = 1.010 at that pole
# (DESIGN-V291-FBLP-2026-09-13.md ADDENDUM A2).  The r24 integer is the value rounded DOWN from
# k_gate * 5244, so the realised cut is at or beyond the requirement, never short of it.  Asserted
# at [3] against k_gate, not against the integer restated here.
DOSES = {
    "C12": dict(a=950, b=1143, r24=4923, corner=11.94, k_gate=0.9390,
                tag="FBPOLE.12HZ.950.1143-R24.4923",
                note="the mild dose: gate73 1.0750 at k=1, restored to ~1.010 by the -6.1 % r24 cut"),
    "C10": dict(a=962, b=958, r24=4725, corner=9.94, k_gate=0.9012,
                tag="FBPOLE.10HZ.962.958-R24.4725",
                note="the middle dose: gate73 1.1163 at k=1, restored to ~1.010 by the -9.9 % r24 cut"),
    "C8": dict(a=974, b=772, r24=4512, corner=7.97, k_gate=0.8605,
               tag="FBPOLE.8HZ.974.772-R24.4512",
               note="the strong dose: gate73 1.1624 at k=1, restored to ~1.010 by the -14.0 % r24 cut"),
}
assert DOSE in DOSES, f"ACCORD_V291_DOSE must be one of {sorted(DOSES)}, got {DOSE!r}"
_D = DOSES[DOSE]
FB_A_NEW, FB_B_NEW, R24_NEW = _D["a"], _D["b"], _D["r24"]

# ---- [B] the 0x14A telemetry cave -- V282's, and the ONE displacement V291 may move ---------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
CAVE_HOOK, CAVE_HOOK4 = 0x55C0E, bytes.fromhex("86ff26ef")     # jarl 0xC4B34,lp
RUNG_HW1 = 0x3724                            # reg1=gp(4), opc=0x39 (ld.h/.w), reg2=r6 -- NEVER touched
HW2_NEW = 0xC2D1                             # ODD -> ld.w, disp field 0xC2D0 = -0x3D30, the state `s`
# Both candidate rungs have the SAME form.  `bit` is the 0x14A byte-4 bit each one drives.
RUNGS = {
    "b3": dict(insn=0xC4BA8, hw2_old=0xC981, bit=0x08, disp_old=-0x3680,
               was="ld.w", what="sign(gp-0x3680), the base-assist Stage C derivative state (V103)",
               measured="duty 0.47-0.48, 45.4-46.7 transitions/s -- ALIASED at the 100 Hz frame"),
    "b7": dict(insn=0xC4B92, hw2_old=0x94B4, bit=0x80, disp_old=-0x6B4C,
               was="ld.h", what="sign(gp-0x6b4c), the LKAS lane's unit-weight aggregator summand",
               measured="duty 0.49-0.55, 4.8-5.5 transitions/s -- WELL RESOLVED"),
}
_R = RUNGS.get(TELEMETRY_BIT)
B7_INSN = _R["insn"] if _R else RUNGS["b3"]["insn"]        # the rung this build actually edits
B7_HW1 = RUNG_HW1
B7_HW2_OLD = _R["hw2_old"] if _R else RUNGS["b3"]["hw2_old"]
B7_HW2_NEW = HW2_NEW
S_DISP = -0x3D30                             # gp-0x3d30 = 0xFEDF42D0, 32-bit, 2 accesses image-wide
LDW_PRECEDENT = 0xC4BA8                      # 24 37 81 c9 = ld.w -0x3680[gp],r6 -- the in-cave proof
# Two MORE `ld.w <disp>,gp,r6` sites with the IDENTICAL hw1 0x3724, outside the cave, present on STOCK,
# and READ BACK FROM GHIDRA'S OWN V850 DECODER (disassemble_bytes dry_run, 2026-09-13) rather than from
# a hand decode.  They pin "hw1 0x3724 + ODD hw2 == ld.w into r6" as EVIDENCE from a second decoder:
#     0x18B62  24 37 01 b3  ->  ld.w -0x4d00, gp, r6     (hw2 0xB301, disp field 0xB300)
#     0x19A98  24 37 15 c1  ->  ld.w -0x3eec, gp, r6     (hw2 0xC115, disp field 0xC114)
# By the same rule 24 37 d1 c2 is ld.w -0x3d30, gp, r6.
LDW_GHIDRA = {0x18B62: (0xB301, -0x4D00), 0x19A98: (0xC115, -0x3EEC)}
# every other ld in the cave, pinned so a stray edit cannot hide inside it
CAVE_OTHER_LOADS = {0xC4B34: (0x3724, 0x9526), 0xC4B40: (0x3724, 0x94C8),     # b6: |r24| >= |T|
                    0xC4B62: (0x3724, 0x9526), 0xC4B6E: (0x3724, 0x946C),     # b5: |r24| >= |agg|
                    0xC4B9C: (0x3724, 0x9526),                                # b4: sign(r24)
                    0xC4BA8: (0x3724, 0xC981)}                                # b3: sign(gp-0x3680)
STOCK_B4_BITS = 0x07                         # bits 2-0 are Honda's; the cave's 0xC4BB6 mask is 0x67
B7_MASK_SITE, B7_MASK = 0xC4BB8, 0x0067   # the andi imm16 (the insn itself starts at 0xC4BB6)

# ---- [C] carried from V282, asserted byte-identical ----------------------------------------------
PACK_LO, PACK_HI = 0x55DF0, 0x55E12          # the CAN-427 delivered-torque tap
MAP_PTR, MAP_N = 0xC9A88, 10
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y = (0, 68, 112, 136, 208), (248,) * 5
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)
FWD_GAIN_REPOINT = (0x2A1F0, bytes.fromhex("d07c"))   # V57/V81: the ONLY code delta vs stock here
# The UNCALLED TWIN ISLAND -- six functions, zero callers, a near-duplicate of the live LKAS output
# path.  The live forward of the gated T is 0x2A2EA; the island's 0x2B41C copy is DEAD.
ISLAND_LO, ISLAND_HI = 0x2A30E, 0x2B422
LIVE_FWD_T = 0x2A2EA                                  # st.h r16,-0x6b3c[gp]  -- the LIVE one
# cells the island DOES read -- the positive control that makes its null for our cells meaningful
ISLAND_CONTROLS = {0xC63EC: [0x2A8A2], 0xC63EE: [0x2A892], 0xC61B6: [0x2ADD4, 0x2ADDC, 0x2ADEC]}

FROZEN = {
    0xC61B2: 3072, 0xC61B4: 3072,            # forward tracking clamps
    0xC61B6: 10240,                          # D clamp (V287's cell -- NOT flown on this base)
    0xC61B8: 102,                            # post-lag deadband
    0xC61BA: 10240,                          # integrator anti-windup
    0xC61BC: 15360,                          # P clamp
    0xC61BE: 15360,                          # post-gain SUM clamp -- the 2505 ceiling
    0xC61F6: 3,                              # Coulomb deadband on the r24 lane
    0xC61F8: 1024, 0xC61FA: 5530,            # the gp-0x671d latch RELEASE / SET thresholds
    0xC62E4: 4,
    0xC62E6: 46080,                          # feedback saturation clamp
    0xC63E6: 0,                              # Ki -- ships at ZERO
    0xC63EC: 992, 0xC63EE: 507,              # OUTPUT-lag pole -- deliberately NOT moved
    0xC6440: 2048, 0xC6442: 1024, 0xC6444: 512, 0xC6448: 1024, 0xC644A: 1024,   # r24 gate siblings
    0xC6500: 771,                            # DTC maturation count (&0xFF = 3)
    0xC674E: 5120, 0xC6750: 5120,            # EME soft-limit quad (int16)
    0xC675A: 0x10000 - 5120, 0xC675C: 0x10000 - 5120,
    0xC6768: 5120, 0xC676A: 5120, 0xC676C: 5120,                                # EME ramp triple
    0xC6AE6: 2048, 0xC6B12: 98, 0xC6B26: 256,
    0xC6CD0: 5346,                           # the private forward LKAS gain -- the x6
}
EME_FLOATS = {0xC6598: 5.0, 0xC659C: 5.0, 0xC65AC: -5.0, 0xC65B0: -5.0,
              0xC65C4: 5.0, 0xC65C8: 5.0, 0xC65CC: 5.0}
for _c in (FB_A_CELL, FB_B_CELL, R24_CELL):
    assert _c not in FROZEN, f"0x{_c:05X} cannot be both edited and frozen"

TAG = (f"V291-V282BASE-{_D['tag']}" +
       (f"-{TELEMETRY_BIT.upper()}.FBSTATE" if TELEMETRY else "-CAVE.V282") +
       "-KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP")
IMG_NAME = f"_v291{DOSE.lower()}_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"

OK, BAD = "[PASS]", "[FAIL]"
# assertion census:  S = substantive (a wrong edit could fail it)
#                    V = vacuous     (entailed by the base sha256 -- it says nothing about THIS build)
#                    T = tautological(readback of a value this script just wrote)
_census = {"S": 0, "V": 0, "T": 0}
_checks = [0, 0]


def check(cond, msg, kind="S"):
    assert kind in _census
    _checks[0] += 1
    _census[kind] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} [{kind}] {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


# =====================================================================================================
#  THE TWO EDITED PATHS, MIRRORED EXACTLY.  Integer Python, instruction addresses in the comments.
# =====================================================================================================
def lkas_fb_lag(x, s, sentinel_ok, a, b, C=FB_CLAMP):
    """FUN_00028ea6 @0x28F4C-0x28FBE.  Returns (out -> r26, s', sentinel_ok')."""
    if not (-FB_X_SAT <= x <= FB_X_SAT):      # 0x28F50 addi / 0x28F54 addi / 0x28F58 bnc -> BAIL 0x290B0
        return 0, s, False                    #   r25 := 0 (forces PID skip 2), r26 := 0, sentinel := 2
    if not sentinel_ok:                       # 0x28F72 cmp 0x1,r9 / 0x28F76 bne 0x28F82
        s = 0                                 # 0x28F84 mov 0x0,r26
    s_new = (b * x) >> 10                     # 0x28F8E mul r16,r7,r0 ; 0x28F9A sar 0xa   (SEPARATE floor)
    s_new += (a * s) >> 10                    # 0x28F92 mul r26,r9,r0 ; 0x28FA0 sar 0xa   (SEPARATE floor)
    out = s + s_new                           # 0x28FA4 add r9,r26     the TWO-SAMPLE SUM
    s = s_new                                 # 0x28FA8 st.w r9,-0x3d30[gp]   32-bit, BEFORE the clamp
    out = C if out > C else (-C if out < -C else out)          # 0x28FA6..0x28FBC
    return out, s, True


def r24_gain_arm(d, latched, engaged, r2, k_latch, k_eng, k_other, k_default=0):
    """the gain_B priority gate + Q10 scale, 0x3ABFA-0x3AC20."""
    K = k_default
    if latched != 0:                          # 0x3ABFA cmp r0,r6 / 0x3ABFC be 0x3AC04
        K = k_latch                           # 0x3ABFE ld.hu 0x7442,tp,r10
    elif engaged != 0:                        # 0x3AC04 cmp r0,lp / 0x3AC06 be 0x3AC0E
        K = k_eng                             # 0x3AC08 ld.hu 0x7446,tp,r10  ** THE EDITED CELL **
    elif r2 != 0:                             # 0x3AC0E cmp r0,r2 / 0x3AC10 be 0x3AC16
        K = k_other                           # 0x3AC12 ld.hu 0x7440,tp,r10
    return (K * d) >> 10                      # 0x3AC18 mul / 0x3AC20 sar 0xa   -> r24


def dc_gain(a, b):
    return 2.0 * b / (1024 - a)


def corner_hz(a, ts=TICK_S):
    return -math.log(a / 1024.0) / (2 * math.pi * ts)


# =====================================================================================================
#  THE TWO-ENCODING gp/tp-RELATIVE CENSUS.  Re-run on the BUILT image at [11].
#  A null from the stock image is NOT a null for a modded one, so this scans the built bytes.
# =====================================================================================================
def scan_rel(img, lo=START, hi=END):
    """(addr, base, disp_signed, mnem, reg2, nbytes) for every 4-byte and 6-byte gp/tp-relative access.
    Displacement rules derived empirically from THIS binary (see TRACE-2026-09-13 sec.2.1):
      0x38 ld.b / 0x3A st.b   -> disp = hw2
      0x39 / 0x3B             -> .w if hw2 bit0 else .h ; disp = hw2 & 0xFFFE
      0x3C/0x3D ld.bu         -> disp = (hw2 & 0xFFFE) | (opc & 1)      <-- the bit-5 parity trap
      0x3E/0x3F ld.hu         -> disp = hw2 & 0xFFFE
    """
    out = []
    n = min(hi, len(img))
    for a in range(lo, n - 5, 2):
        w0 = struct.unpack_from("<H", img, a)[0]
        reg1, opc, reg2 = w0 & 0x1F, (w0 >> 5) & 0x3F, (w0 >> 11) & 0x1F
        if reg1 in (4, 5) and 0x38 <= opc <= 0x3F:
            w1 = struct.unpack_from("<H", img, a + 2)[0]
            if opc in (0x38, 0x3A):
                disp, mnem = w1, ("ld.b" if opc == 0x38 else "st.b")
            elif opc in (0x39, 0x3B):
                disp = w1 & 0xFFFE
                mnem = ("ld" if opc == 0x39 else "st") + (".w" if (w1 & 1) else ".h")
            elif opc in (0x3C, 0x3D):
                disp, mnem = (w1 & 0xFFFE) | (opc & 1), "ld.bu"
            else:
                disp, mnem = w1 & 0xFFFE, "ld.hu"
            out.append((a, "gp" if reg1 == 4 else "tp", sext16(disp), mnem, reg2, 4))
        if (w0 & 0xFFE0) in (0x0780, 0x07A0) and reg1 in (4, 5):
            w1 = struct.unpack_from("<H", img, a + 2)[0]
            w2 = struct.unpack_from("<H", img, a + 4)[0]
            out.append((a, "gp" if reg1 == 4 else "tp",
                        (sext16(w2) << 7) | ((w1 >> 4) & 0x7F), "ld/st(6B)", (w1 >> 11) & 0x1F, 6))
    return out


def hits_at(scan, abs_addr):
    return [h for h in scan
            if ((TP_BASE + h[2]) if h[1] == "tp" else (GP_BASE + h[2])) == abs_addr]


def scan_abs(img, target, lo=START, hi=END):
    return [a for a in range(lo, min(hi, len(img)) - 3)
            if struct.unpack_from("<I", img, a)[0] == target]


def independent_rebuild(base):
    """A second, minimal implementation with NONE of build()'s bookkeeping: patch the halfwords
    directly, then re-CRC every owning block via FF.crc_block_map (not a hardcoded trailer address)."""
    img = bytearray(base)
    touched = set()
    for addr, old, new in ((FB_A_CELL, FB_A_OLD, FB_A_NEW), (FB_B_CELL, FB_B_OLD, FB_B_NEW),
                           (R24_CELL, R24_OLD, R24_NEW)):
        assert struct.unpack_from("<H", img, addr)[0] == old
        struct.pack_into("<H", img, addr, new)
        touched |= {addr, addr + 1}
    if TELEMETRY:
        assert struct.unpack_from("<H", img, B7_INSN + 2)[0] == B7_HW2_OLD
        struct.pack_into("<H", img, B7_INSN + 2, B7_HW2_NEW)
        touched |= {B7_INSN + 2, B7_INSN + 3}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 112)
    print(f"  V291 dose {DOSE} -- V282 + fb-lag pole DOWN ({FB_A_OLD}/{FB_B_OLD} -> {FB_A_NEW}/{FB_B_NEW}, "
          f"{corner_hz(FB_A_OLD):.2f} -> {corner_hz(FB_A_NEW):.2f} Hz)")
    print(f"                 + r24 ENGAGED arm 0xC6446 {R24_OLD} -> {R24_NEW} "
          f"({100.0 * (R24_NEW / R24_OLD - 1):+.2f} %, a PARTIAL REVERT of V84's Lever B)")
    print(f"                 + telemetry {TELEMETRY_BIT} -> sign(fb-lag state gp-0x3d30)"
          f"   [TELEMETRY_BIT = {TELEMETRY_BIT!r}]")
    print(f"  🛑 EVERY 20 Hz NUMBER BEHIND THIS BUILD IS SERVO-SIDE ONLY -- the 304-fit plant was")
    print(f"     identified with r24 = 5244 INSIDE it, and the record disagrees with itself on r24's")
    print(f"     20 Hz sign.  That is the largest open risk on this image.  See docstring sec.0.")
    print("=" * 112)

    # ---------------------------------------------------------------------------------------------
    print("\n  [1] BASE = V282")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          "V282 base sha256 matches the record (build_v287/v289 BASE_SHA, "
          "V282-CUMULATIVE-NONSTOCK-DELTA table)", "S")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    check(u16(base, FB_A_CELL) == FB_A_OLD and u16(base, FB_B_CELL) == FB_B_OLD,
          f"base fb pole 0x{FB_A_CELL:05X}/0x{FB_B_CELL:05X} == {FB_A_OLD}/{FB_B_OLD}", "V")
    check(u16(base, R24_CELL) == R24_OLD, f"base r24 engaged arm 0x{R24_CELL:05X} == {R24_OLD} "
                                          f"(V84's Lever B; stock is 512)", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    for a, v in EME_FLOATS.items():
        check(abs(f32(base, a) - v) < 1e-6, f"base EME float mirror 0x{a:05X} == {v}", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and tuple(X7) == LIVE_KP_X
          and tuple(Y7) == LIVE_KP_Y, f"base live Kp slot {LIVE_SLOT} @0x{LIVE_KP_REC:05X} flat-248", "V")
    nkd, _Xk, Ykd = rec(base, u32(base, KD_PTR + 4 * LIVE_SLOT))
    check(u32(base, KD_PTR + 4 * LIVE_SLOT) == LIVE_KD_REC and tuple(Ykd) == LIVE_KD_Y,
          f"base live Kd slot {LIVE_SLOT} @0x{LIVE_KD_REC:05X} flat 128", "V")
    check(bytes(base[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, "base cave hook 0x55C0E == jarl 0xC4B34,lp", "V")
    _fa, _fb = FWD_GAIN_REPOINT
    check(bytes(base[_fa:_fa + 2]) == _fb,
          f"base 0x{_fa:05X} carries the V57/V81 forward-gain repoint ({_fb.hex()}) -- the ONE code "
          f"byte pair in [0x28F00,0x2A260) that differs from stock", "V")
    base_cave_sha = hashlib.sha256(bytes(base[CAVE_START:CAVE_END])).hexdigest()
    print(f"      base cave 0x{CAVE_START:05X}-0x{CAVE_END - 1:05X} ({CAVE_END - CAVE_START} B) "
          f"sha256[:8] = {base_cave_sha[:8]}   (V112's frozen cave is d3bb75d8; V282 re-pointed b5/b6)")

    # ---------------------------------------------------------------------------------------------
    print("\n  [2] CELL IDENTITY -- every edited cell's reader decoded from the BASE image's OWN bytes")
    # (site, expected bytes, cell, expected opcode field, expected hw2 bit0, mnemonic, IS the load SIGNED?)
    for addr, want, cell, e_opc, e_b0, mnem, is_signed in (
            (FB_A_LOAD, FB_A_LOAD_BYTES, FB_A_CELL, 0x39, 0, "ld.h", True),
            (FB_B_LOAD, FB_B_LOAD_BYTES, FB_B_CELL, 0x3F, 1, "ld.hu", False),
            (R24_LOAD, R24_LOAD_BYTES, R24_CELL, 0x3F, 1, "ld.hu", False)):
        got = bytes(base[addr:addr + 4])
        hw1, hw2 = struct.unpack_from("<HH", got, 0)
        reg1, opc, reg2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, (hw1 >> 11) & 0x1F
        disp = hw2 & 0xFFFE
        print(f"      0x{addr:05X}  {got.hex()}  hw1=0x{hw1:04X} reg1=r{reg1} opc=0x{opc:02X} "
              f"reg2=r{reg2}  hw2=0x{hw2:04X} disp=0x{disp:04X} {mnem}  -> 0x{TP_BASE + disp:05X}")
        check(got == want, f"0x{addr:05X} carries the expected reader bytes {want.hex()}", "V")
        check(reg1 == 5, f"0x{addr:05X} base register is r5 = tp", "S")
        check(TP_BASE + disp == cell,
              f"0x{addr:05X}: tp 0x{TP_BASE:05X} + disp 0x{disp:04X} == 0x{cell:05X} -- this reader "
              f"reads THE CELL THIS BUILD EDITS (anchor check, no off-by-0x1000)", "S")
        check(opc == e_opc and (hw2 & 1) == e_b0,
              f"0x{addr:05X} opcode field 0x{opc:02X} + hw2 bit0 {hw2 & 1} == {mnem}, which is "
              f"{'SIGNED -- the cell is capped at 32767' if is_signed else 'UNSIGNED -- cap 65535'}", "S")
    check(len(hits_at(scan_rel(bytes(base), FB_A_LOAD - 2, FB_A_LOAD + 6), FB_A_CELL)) == 1,
          "local re-scan around 0x28F8A finds the `a` reader exactly once (scanner sanity)", "S")

    print("\n  [2b] THE r24 GATE -- all three cal arms decoded, so the EDITED arm cannot be confused")
    for addr, (cell, what) in sorted(R24_SIBLINGS.items()):
        hw1, hw2 = struct.unpack_from("<HH", bytes(base), addr)
        check(TP_BASE + (hw2 & 0xFFFE) == cell and (hw1 & 0x1F) == 5,
              f"0x{addr:05X} ld.hu 0x{hw2 & 0xFFFE:04X}[tp] -> 0x{cell:05X} = {u16(base, cell)}  ({what})", "S")
    check(u16(base, 0xC6442) == 1024 and R24_OLD > 1024,
          f"the LATCH arm 0x{0xC6442:05X} (1024) is BELOW the engaged arm ({R24_OLD}), so on this "
          f"V280+ base a gp-0x671d latch COLLAPSES r24 to x{1024 / R24_OLD:.3f} -- the inversion the "
          f"docstring warns about.  V291 moves the engaged arm to x{1024 / R24_NEW:.3f} of the latch", "S")

    print("\n  [2c] THE TELEMETRY RUNGS -- both candidates decoded from the BASE cave's own bytes")
    for nm, R in sorted(RUNGS.items()):
        g1, g2 = struct.unpack_from("<HH", bytes(base), R["insn"])
        mark = "  <== V291 EDITS THIS ONE" if nm == TELEMETRY_BIT else ""
        print(f"      {nm}: 0x{R['insn']:05X}  {bytes(base[R['insn']:R['insn'] + 4]).hex()}  "
              f"{'ld.w' if g2 & 1 else 'ld.h'} {sext16(g2 & 0xFFFE):+#x}[gp],r6  bit 0x{R['bit']:02X}"
              f"  = {R['what']}{mark}")
        print(f"          on the wire today: {R['measured']}")
        check(g1 == RUNG_HW1 and g2 == R["hw2_old"] and sext16(g2 & 0xFFFE) == R["disp_old"],
              f"base {nm} load = hw1 0x{RUNG_HW1:04X} / hw2 0x{R['hw2_old']:04X} = "
              f"{R['was']} {R['disp_old']:+#x}[gp],r6", "V")
        # the rung FORM: the 2 bytes before the load and the 6 after must be the standard chain
        pre = bytes(base[R["insn"] - 2:R["insn"]])
        post = bytes(base[R["insn"] + 4:R["insn"] + 10])
        add_imm = 0x3A00 | (R["bit"] if nm == "b3" else (R["bit"] >> 4)) | 0x40
        check(post[:4] == bytes.fromhex("6032ae05") and struct.unpack("<H", post[4:6])[0] == add_imm,
              f"{nm} rung FORM: after the load comes cmp 0,r6 / bge +4 / add "
              f"0x{add_imm & 0x1F:X},r7 ({post.hex()}) -- so ONLY the load's operand decides the bit, "
              f"and a displacement edit cannot change the rung's shape.  Preceded by {pre.hex()}", "S")
    hw1, hw2 = struct.unpack_from("<HH", bytes(base), B7_INSN)
    check(hw1 == B7_HW1 and hw2 == B7_HW2_OLD,
          f"the rung selected by TELEMETRY_BIT = {TELEMETRY_BIT!r} is 0x{B7_INSN:05X}, hw2 "
          f"0x{B7_HW2_OLD:04X}", "V")
    lp_hw1, lp_hw2 = struct.unpack_from("<HH", bytes(base), LDW_PRECEDENT)
    check(lp_hw1 == B7_HW1 and (lp_hw2 & 1) == 1 and GP_BASE + sext16(lp_hw2 & 0xFFFE) == GP_BASE - 0x3680,
          f"IN-CAVE PRECEDENT for the ld.w form: 0x{LDW_PRECEDENT:05X} is hw1 0x{lp_hw1:04X} (IDENTICAL) "
          f"+ hw2 0x{lp_hw2:04X} (ODD -> ld.w) reading gp-0x3680 -- so hw2 bit 0 alone selects the width "
          f"and 0x{B7_HW2_NEW:04X} is a proven encoding, not an inferred one", "S")
    for _a, (_h2, _disp) in sorted(LDW_GHIDRA.items()):
        _g1, _g2 = struct.unpack_from("<HH", bytes(base), _a)
        check(_g1 == B7_HW1 and _g2 == _h2 and sext16(_g2 & 0xFFFE) == _disp,
              f"GHIDRA-CONFIRMED precedent 0x{_a:05X} = {bytes(base[_a:_a + 4]).hex()} -> "
              f"ld.w {_disp:+#x}, gp, r6  (hw1 0x{_g1:04X} IDENTICAL to b7's, hw2 0x{_g2:04X} "
              f"ODD).  Ghidra's own V850 decoder read these two back, so 24 37 d1 c2 = "
              f"ld.w -0x3d30,gp,r6 is EVIDENCE from a SECOND decoder, not a hand decode", "S")
    check(u16(base, B7_MASK_SITE) == B7_MASK and (B7_MASK & STOCK_B4_BITS) == STOCK_B4_BITS,
          f"the rung's andi mask at 0x{B7_MASK_SITE:05X} is 0x{B7_MASK:04X}, which PRESERVES Honda's "
          f"bits 2-0 (0x{STOCK_B4_BITS:02X}) and clears only b7/b4/b3 -- the cave never owns b0-b2", "S")
    for addr, (h1, h2) in sorted(CAVE_OTHER_LOADS.items()):
        g1, g2 = struct.unpack_from("<HH", bytes(base), addr)
        check((g1, g2) == (h1, h2), f"cave load 0x{addr:05X} == hw1 0x{h1:04X} / hw2 0x{h2:04X} "
                                    f"(gp{sext16(h2 & 0xFFFE):+#x}) -- pinned so no stray edit hides", "V")

    # ---------------------------------------------------------------------------------------------
    print("\n  [3] THE ARITHMETIC -- computed from the integers ACTUALLY WRITTEN, not from the docstring")
    check(0 < FB_A_NEW <= 1023,
          f"a = {FB_A_NEW} is strictly < 1024: the pole a/1024 = {FB_A_NEW / 1024:.6f} < 1, so the "
          f"recurrence is a decaying lag, not an integrator (a = 1024) or a divergence (a > 1024)", "S")
    check(FB_A_NEW <= 32767, f"a = {FB_A_NEW} <= 32767: it is read with ld.h (SIGNED) at 0x{FB_A_LOAD:05X}, "
                             f"so >= 32768 would read NEGATIVE and alternate", "S")
    check(0 < FB_B_NEW <= 65535, f"b = {FB_B_NEW} in [1,65535]: ld.hu (UNSIGNED) at 0x{FB_B_LOAD:05X}", "S")
    dc_new, dc_old = dc_gain(FB_A_NEW, FB_B_NEW), dc_gain(FB_A_OLD, FB_B_OLD)
    check(abs(dc_old - DC_TARGET) < 1e-6, f"base DC 2b/(1024-a) = {dc_old:.6f} == 3120/101", "V")
    check(abs(dc_new / DC_TARGET - 1) <= DC_TOL,
          f"realised DC {dc_new:.6f} is {100 * (dc_new / DC_TARGET - 1):+.4f} % of V282's "
          f"{DC_TARGET:.6f} -- within the {100 * DC_TOL:.1f} % band, so STEADY-STATE FEEDBACK GAIN "
          f"(and therefore steady-state authority) IS UNCHANGED", "S")
    f_old, f_new = corner_hz(FB_A_OLD), corner_hz(FB_A_NEW)
    check(abs(f_new - _D["corner"]) < 0.05,
          f"realised corner from the integer a = {FB_A_NEW}: {f_new:.4f} Hz (label {_D['corner']} Hz); "
          f"base {f_old:.4f} Hz -- a x{f_old / f_new:.2f} OPENING of the loop at high frequency", "S")
    check(f_new < f_old, f"the pole moved DOWN ({f_old:.2f} -> {f_new:.2f} Hz).  V289 moved this same "
                         f"cell UP (16.53 -> 25 Hz); this is the same lever the OTHER way", "S")
    s_ss = FB_B_NEW * FB_X_SAT / (1024 - FB_A_NEW)
    head = (2 ** 31) / (FB_A_NEW * s_ss)
    check(head > 4.0, f"int32 headroom on a*s at the producer's |x| = {FB_X_SAT} saturation: "
                      f"s_ss = {s_ss:.0f}, a*s = {FB_A_NEW * s_ss:.3e} vs 2^31 -> x{head:.2f}", "S")
    dz_old, dz_new = 1024.0 / FB_B_OLD, 1024.0 / FB_B_NEW
    st_old, st_new = 1024.0 / (1024 - FB_A_OLD), 1024.0 / (1024 - FB_A_NEW)
    print(f"      dead zone 1024/b : |x| < {dz_old:.3f} -> {dz_new:.3f} raw counts "
          f"({dz_old / 8:.4f} -> {dz_new / 8:.4f} deg/s), x{dz_new / dz_old:.2f} WIDER")
    print(f"      stick floor      : |s| < {st_old:.2f} -> {st_new:.2f}  (resting fb offset "
          f"{-2 * round(st_old):+.0f} -> {-2 * round(st_new):+.0f} E-counts)")
    check(dz_new < 16.0, f"the widened dead zone {dz_new:.3f} counts ({dz_new / 8:.4f} deg/s) is still "
                         f"x{15.8 / dz_new:.1f} BELOW the 15.8-28.2-count ring amplitude (memo A8), so "
                         f"the feedback leg stays LINEAR at ring amplitude", "S")
    # mirror checks -- the filter, exercised
    o0, s0, ok0 = lkas_fb_lag(1, 0, True, FB_A_NEW, FB_B_NEW)
    check(s0 == (FB_B_NEW >> 10) and ok0,
          f"mirror: one-count step from s = 0 gives s' = floor({FB_B_NEW}/1024) = {s0} "
          f"(V282 gives {FB_B_OLD >> 10}) -- the first-tick D kick per rate LSB", "S")
    s_, ok_ = 0, True
    for _ in range(4000):
        _o, s_, ok_ = lkas_fb_lag(1000, s_, ok_, FB_A_NEW, FB_B_NEW)
    ideal = FB_B_NEW * 1000 / (1024 - FB_A_NEW)
    check(abs(s_ / ideal - 1) < 0.02,
          f"mirror: driven at constant x = 1000 the integer state settles to {s_} vs the ideal "
          f"{ideal:.1f} ({100 * (s_ / ideal - 1):+.2f} %) -- the >>10 truncation does not eat the DC", "S")
    _o, _s, _ok = lkas_fb_lag(FB_X_SAT + 1, 12345, True, FB_A_NEW, FB_B_NEW)
    check(_o == 0 and _s == 12345 and _ok is False,
          f"mirror: |x| > {FB_X_SAT} BAILS (r26 := 0, sentinel := 2 so s is zeroed NEXT tick) -- "
          f"it is a plausibility bail, not a clamp; the producer already saturates x", "S")
    # mirror checks -- the r24 arm
    for d in (1, 10, 100, 1000, -1000):
        old = r24_gain_arm(d, 0, 1, 0, 1024, R24_OLD, 2048)
        new = r24_gain_arm(d, 0, 1, 0, 1024, R24_NEW, 2048)
        assert new == (R24_NEW * d) >> 10 and old == (R24_OLD * d) >> 10
    check(r24_gain_arm(1000, 1, 1, 0, 1024, R24_NEW, 2048) == (1024 * 1000) >> 10,
          f"mirror: with the gp-0x671d latch SET the engaged arm is bypassed entirely and r24 uses "
          f"1024 -- V291's cell is NOT read on a latched drive (the bimodality, unchanged)", "S")
    check(r24_gain_arm(1000, 0, 1, 0, 1024, R24_NEW, 2048)
          < r24_gain_arm(1000, 0, 1, 0, 1024, R24_OLD, 2048),
          f"mirror: engaged, unlatched, the r24 gain falls x{R24_NEW / R24_OLD:.4f} "
          f"({R24_OLD / 1024:.4f} -> {R24_NEW / 1024:.4f} per count of the bar-torque derivative)", "S")
    k_real, k_gate = R24_NEW / R24_OLD, _D["k_gate"]
    check(k_real <= k_gate,
          f"r24 ROUNDING DIRECTION: realised k = {R24_NEW}/{R24_OLD} = {k_real:.6f} is AT OR BELOW the "
          f"memo's published k_gate {k_gate:.4f} for this pole (ADDENDUM A2) -- the integer rounds "
          f"DOWN, so the cut is at least the requirement.  Rounding UP would land on the WRONG SIDE "
          f"of the 7 Hz gate", "S")
    check(abs(k_real / k_gate - 1) < 0.001,
          f"and it is within 0.1 % of k_gate ({100 * (k_real / k_gate - 1):+.4f} %), so it is the "
          f"intended dose and not a transcription error", "S")
    check(512 < R24_NEW < R24_OLD,
          f"the r24 dose is a PARTIAL REVERT toward stock: 512 (stock) < {R24_NEW} < {R24_OLD} (V88's "
          f"optimum, frozen since V247).  It does not cross stock and it does not raise anything", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [4] APPLY")
    code = bytearray(base)
    attributed = set()
    for addr, old, new, what in ((FB_A_CELL, FB_A_OLD, FB_A_NEW, "fb pole a"),
                                 (FB_B_CELL, FB_B_OLD, FB_B_NEW, "fb pole b"),
                                 (R24_CELL, R24_OLD, R24_NEW, "r24 engaged arm")):
        check(u16(code, addr) == old, f"pre-write 0x{addr:05X} == {old}", "T")
        struct.pack_into("<H", code, addr, new)
        check(u16(code, addr) == new, f"0x{addr:05X} {what}: {old} -> {new} "
                                      f"(0x{old:04X} -> 0x{new:04X})", "T")
        attributed |= {addr, addr + 1}
    if TELEMETRY:
        _RR = RUNGS[TELEMETRY_BIT]
        check(u16(code, B7_INSN + 2) == B7_HW2_OLD,
              f"pre-write {TELEMETRY_BIT} hw2 == 0x{B7_HW2_OLD:04X}", "T")
        struct.pack_into("<H", code, B7_INSN + 2, B7_HW2_NEW)
        attributed |= {B7_INSN + 2, B7_INSN + 3}
        check(u16(code, B7_INSN) == B7_HW1,
              f"{TELEMETRY_BIT} hw1 at 0x{B7_INSN:05X} is STILL 0x{B7_HW1:04X} -- the opcode, base "
              f"register and destination register are untouched; only the displacement moved", "S")
        check(u16(code, B7_INSN + 2) == B7_HW2_NEW and (B7_HW2_NEW & 1) == 1,
              f"{TELEMETRY_BIT} hw2 0x{B7_HW2_OLD:04X} -> 0x{B7_HW2_NEW:04X}: bit 0 = 1 selects ld.w "
              f"(32-bit) and the disp field 0x{B7_HW2_NEW & 0xFFFE:04X} = "
              f"{sext16(B7_HW2_NEW & 0xFFFE):+#x} -> gp{S_DISP:+#x} = 0x{GP_BASE + S_DISP:08X}, the "
              f"fb-lag state `s`", "T")
        check((_RR["was"] == "ld.w") == (_RR["hw2_old"] & 1 == 1),
              f"{TELEMETRY_BIT} was a {_RR['was']} before the edit and is an ld.w after; on b3 that "
              f"means the load WIDTH does not change at all, only the displacement", "S")
        check(GP_BASE + sext16(B7_HW2_NEW & 0xFFFE) == GP_BASE + S_DISP
              and (GP_BASE + S_DISP) % 4 == 0,
              f"the new target 0x{GP_BASE + S_DISP:08X} is 4-BYTE ALIGNED, so the cave's 32-bit load "
              f"cannot tear against the filter's 32-bit store at 0x28FA8", "S")
        for _o, _OR in sorted(RUNGS.items()):
            if _o == TELEMETRY_BIT:
                continue
            check(u16(code, _OR["insn"]) == RUNG_HW1 and u16(code, _OR["insn"] + 2) == _OR["hw2_old"],
                  f"the OTHER rung {_o} @0x{_OR['insn']:05X} is byte-identical -- it still reads "
                  f"{_OR['what']}", "S")
    else:
        check(bytes(code[CAVE_START:CAVE_END]) == bytes(base[CAVE_START:CAVE_END]),
              "TELEMETRY_BIT = off: the cave is untouched, every bit keeps V282's meaning, and the "
              "pole move has NO instrument", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [5] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    outside = [x for x in range(START, END) if x not in attributed and code[x] != base[x]]
    check(outside == [], f"no byte outside the {len(attributed)} attributed payload bytes changed "
                         f"before the CRC recompute ({len(outside)} stray diffs)", "S")
    for a, v in FROZEN.items():
        check(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}", "S")
    for a, v in EME_FLOATS.items():
        check(abs(f32(code, a) - v) < 1e-6 and bytes(code[a:a + 4]) == bytes(base[a:a + 4]),
              f"EME float mirror 0x{a:05X} == {v} (int/float lockstep intact)", "S")
    for addr, want in ((FB_A_LOAD, FB_A_LOAD_BYTES), (FB_B_LOAD, FB_B_LOAD_BYTES),
                       (R24_LOAD, R24_LOAD_BYTES)):
        check(bytes(code[addr:addr + 4]) == want == bytes(base[addr:addr + 4]),
              f"reader instruction 0x{addr:05X} byte-identical ({want.hex()}) -- CAL ONLY on the "
              f"control path, no code byte", "S")
    for addr, (h1, h2) in sorted(R24_SIBLINGS.items()):
        check(bytes(code[addr:addr + 4]) == bytes(base[addr:addr + 4]),
              f"r24 sibling arm reader 0x{addr:05X} byte-identical", "S")
    ctrl_region = [x for x in range(START, 0xC0000) if x not in attributed and code[x] != base[x]]
    check(ctrl_region == [], f"the entire code region [0x{START:05X},0xC0000) is byte-identical outside "
                             f"the cave displacement ({len(ctrl_region)} diffs)", "S")
    cave_diff = [x for x in range(CAVE_START, CAVE_END) if code[x] != base[x]]
    check(cave_diff == (sorted(attributed & set(range(CAVE_START, CAVE_END)))),
          f"cave diff is EXACTLY the attributed bytes {[hex(x) for x in cave_diff]} "
          f"({len(cave_diff)} of {CAVE_END - CAVE_START})", "S")
    check(bytes(code[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, "cave hook 0x55C0E byte-identical", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          f"427 torque tap window 0x{PACK_LO:05X}-0x{PACK_HI - 1:05X} byte-identical -- the primary "
          f"endpoint's instrument is kept", "S")
    check(bytes(code[0xC4BD2:0xC4BD8]) == bytes(base[0xC4BD2:0xC4BD8]),
          "cave epilogue (movea -0x1518,gp,r6 ; jmp [lp]) byte-identical -- no length change, the "
          "return path is untouched", "S")
    map_ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    for p in map_ptrs:
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]),
              f"assist map 0x{p:05X} byte-identical", "S")
    for nm, ptr in (("Kp", KP_PTR), ("Kd", KD_PTR)):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = u16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
                  f"{nm} slot {s} @0x{p:05X} byte-identical", "S")
    tps = {u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)}
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [6] CRC TRAILERS -- located GENERICALLY via V53.owning_block (content-derived)")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    check(len(blocks) == (2 if TELEMETRY else 1),
          f"exactly {2 if TELEMETRY else 1} CRC block(s) own the payload: "
          f"{[(hex(s), hex(e)) for s, e in blocks]}", "S")
    for b0, b1 in blocks:
        check(b1 in (0xC6FFC, 0xC4FFC),
              f"block [0x{b0:05X},0x{b1:05X}) has a KNOWN trailer 0x{b1:05X} -- 0xC6FFC is the main cal "
              f"page's, 0xC4FFC is the one whose block also spans the cave (the chain makes the first "
              f"block [0x13000,0xC4FFC), so a cave byte re-CRCs that whole block)", "S")
        check(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:06X}", "S")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved", "S")
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      page [0x{b0:06X},0x{b1:06X})  trailer 0x{b1:06X}  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [7] FULL BYTE DIFF vs V282 -- every differing offset enumerated")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(set(diff) <= attributed,
          f"every one of the {len(diff)} differing bytes is an attributed payload byte or a CRC trailer", "S")
    payload_expected = 0
    for addr, old, new in ((FB_A_CELL, FB_A_OLD, FB_A_NEW), (FB_B_CELL, FB_B_OLD, FB_B_NEW),
                           (R24_CELL, R24_OLD, R24_NEW)):
        payload_expected += sum(1 for j in (0, 1)
                                if struct.pack("<H", old)[j] != struct.pack("<H", new)[j])
    if TELEMETRY:
        payload_expected += sum(1 for j in (0, 1) if struct.pack("<H", B7_HW2_OLD)[j]
                                != struct.pack("<H", B7_HW2_NEW)[j])
    check(len(diff) == payload_expected + 4 * len(blocks),
          f"total diff vs V282 = {payload_expected} payload bytes + {len(blocks)} x 4 CRC trailer bytes "
          f"= {payload_expected + 4 * len(blocks)}, got {len(diff)}  (payload count COMPUTED from the "
          f"base and dose bytes, not asserted)", "S")
    print("      offset              len  what                              base -> built")
    names = {FB_A_CELL: "fb pole a   0xC63E8", FB_B_CELL: "fb pole b   0xC63EA",
             R24_CELL: "r24 arm     0xC6446",
             B7_INSN + 2: f"{TELEMETRY_BIT} disp     0x{B7_INSN + 2:05X}"}
    for s, e in runs(diff):
        lbl = next((v for k, v in names.items() if k <= s < k + 2), None) or \
            ("CRC trailer 0x%06X" % s if s in {b1 for _b0, b1 in blocks} else "?")
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:2d} B)  {lbl:32s}  "
              f"{bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")
    print(f"      ENUMERATED DIFFERING OFFSETS: {[hex(a) for a in diff]}")

    # ---------------------------------------------------------------------------------------------
    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V291 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [9] END STATE -- re-read from the FINAL image AND from the DECODED .rwd")
    for nm, im in (("code", code), ("dec ", dec)):
        kind = "T" if nm == "code" else "S"
        check(u16(im, FB_A_CELL) == FB_A_NEW and u16(im, FB_B_CELL) == FB_B_NEW,
              f"{nm}: fb pole == {FB_A_NEW}/{FB_B_NEW}", kind)
        check(u16(im, R24_CELL) == R24_NEW, f"{nm}: r24 engaged arm == {R24_NEW}", kind)
        check(abs(dc_gain(u16(im, FB_A_CELL), u16(im, FB_B_CELL)) / DC_TARGET - 1) <= DC_TOL,
              f"{nm}: DC recomputed FROM THE IMAGE'S OWN BYTES = "
              f"{dc_gain(u16(im, FB_A_CELL), u16(im, FB_B_CELL)):.6f}", kind)
        check(u16(im, FB_A_CELL) <= 1023, f"{nm}: a <= 1023 on the image", kind)
        check(u16(im, B7_INSN) == B7_HW1, f"{nm}: b7 hw1 unchanged (0x{B7_HW1:04X})", kind)
        check(u16(im, B7_INSN + 2) == (B7_HW2_NEW if TELEMETRY else B7_HW2_OLD),
              f"{nm}: b7 hw2 == 0x{(B7_HW2_NEW if TELEMETRY else B7_HW2_OLD):04X}", kind)
        for a, v in FROZEN.items():
            check(u16(im, a) == v, f"{nm}: 0x{a:05X} == {v}", kind)
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: 427 tap untouched", kind)
        check(bytes(im[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, f"{nm}: cave hook untouched", kind)
        _n, Xi, Yi = rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(Xi) == LIVE_KP_X and tuple(Yi) == LIVE_KP_Y, f"{nm}: live Kp == flat-248", kind)
        _n, _X, Yk = rec(im, u32(im, KD_PTR + 4 * LIVE_SLOT))
        check(tuple(Yk) == LIVE_KD_Y, f"{nm}: live Kd == flat 128", kind)

    # ---------------------------------------------------------------------------------------------
    print("\n  [10] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild (direct halfword patches + generic re-CRC, no shared state) == built "
          "image sha256", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [11] READER-PRIVACY CENSUS -- RE-RUN ON THE *BUILT* IMAGE, two encodings, controlled")
    print("       (a null from the stock image is NOT a null for a modded one)")
    S = scan_rel(bytes(code))
    print(f"      scanned {len(S)} gp/tp-relative accesses in [0x{START:X},0x{END:X})")
    # POSITIVE CONTROLS FIRST.  Every one of these is a case the record already knows exists.
    x_hits = hits_at(S, GP_BASE - 0x6A56)
    kinds = {}
    for h in x_hits:
        kinds[h[3]] = kinds.get(h[3], 0) + 1
    check(len(x_hits) == 30 and kinds.get("ld.h") == 25 and kinds.get("st.h") == 4
          and kinds.get("ld.bu") == 1,
          f"CONTROL gp-0x6a56 (the rate operand x): {len(x_hits)} accesses {kinds} -- reproduces the "
          f"trace's 25 ld.h + 4 st.h + 1 ld.bu EXACTLY", "S")
    six = [h for h in S if h[5] == 6 and h[1] == "gp" and h[2] == -0x6752]
    check(len(six) == 4 and [h[0] for h in six] == [0x48E56, 0x48E68, 0x48E76, 0x48E88],
          f"CONTROL the 6-BYTE extended-displacement path is LIVE in this scanner: gp-0x6752 found at "
          f"{[hex(h[0]) for h in six]}", "S")
    lag = {c: [h[0] for h in hits_at(S, c)] for c in (0xC63EC, 0xC63EE)}
    check(lag[0xC63EC] == [0x2A184, 0x2A8A2] and lag[0xC63EE] == [0x2A174, 0x2A892],
          f"CONTROL the output-lag pole pair is found without being told: 0xC63EC {[hex(a) for a in lag[0xC63EC]]}, "
          f"0xC63EE {[hex(a) for a in lag[0xC63EE]]}", "S")
    dcl = [h[0] for h in hits_at(S, 0xC61B6)]
    check(dcl == [0x29EE8, 0x29EF2, 0x29EF8, 0x29F02, 0x2ADD4, 0x2ADDC, 0x2ADEC],
          f"CONTROL the D clamp's 4 live + 3 dead-block readers: {[hex(a) for a in dcl]}", "S")
    check(scan_abs(bytes(code), 0xCB844) == [0x28FCE],
          "CONTROL scan_abs finds the imm32 0xCB844 at 0x28FCE (the absolute-pointer path works)", "S")
    print("      -- controls pass; the nulls below are now worth something --")
    # THE TARGETS
    for cell, want_n, want_sites, what in ((FB_A_CELL, 1, [FB_A_LOAD], "fb pole a"),
                                           (FB_B_CELL, 1, [FB_B_LOAD], "fb pole b"),
                                           (R24_CELL, 1, [R24_LOAD], "r24 engaged arm")):
        h = hits_at(S, cell)
        check(len(h) == want_n and [x[0] for x in h] == want_sites,
              f"0x{cell:05X} ({what}): EXACTLY {want_n} reader, at "
              f"{[hex(x[0]) for x in h]} {[x[3] for x in h]} -- 0 writers, 0 six-byte forms, "
              f"no other consumer.  A cal change here is PRIVATE", "S")
        check(all(x[3].startswith("ld") for x in h), f"0x{cell:05X}: every access is a LOAD", "S")
        check(not scan_abs(bytes(code), cell),
              f"0x{cell:05X}: no LE32 anywhere in the image equals this address -- no pointer reaches it", "S")
    tbl = [a for a in range(START, END - 3) if 0xC6300 <= u32(code, a) < 0xC6500]
    check(not tbl, "no LE32 table base anywhere in [0xC6300,0xC6500) -- no LERP/table stride can walk "
                   "INTO the fb-pole or r24 cells", "S")
    for addr, (cell, what) in sorted(R24_SIBLINGS.items()):
        h = hits_at(S, cell)
        check(len(h) == 1 and h[0][0] == addr,
              f"r24 gate sibling 0x{cell:05X} still has exactly 1 reader, at 0x{addr:05X} ({what}) -- "
              f"the gate's three cal arms are 0x3ABFE / 0x3AC08 / 0x3AC12 and only the middle one moved", "S")
    s_hits = hits_at(S, GP_BASE + S_DISP)
    want_s = [0x28F7C, 0x28FA8] + ([B7_INSN] if TELEMETRY else [])
    check(sorted(x[0] for x in s_hits) == sorted(want_s),
          f"gp-0x3d30 (the fb-lag state s): {[hex(x[0]) for x in sorted(s_hits)]} "
          f"{[x[3] for x in sorted(s_hits)]} -- the filter's own ld.w/st.w"
          + (f" PLUS the new cave reader at 0x{B7_INSN:05X}" if TELEMETRY else "")
          + ".  No other consumer, and V291 adds NO WRITER (GATE 1 clean)", "S")
    check(all(x[3] != "st.w" for x in s_hits if x[0] == B7_INSN) if TELEMETRY else True,
          "the new cave access to gp-0x3d30 is a LOAD, never a store", "S")
    if TELEMETRY:
        _RR = RUNGS[TELEMETRY_BIT]
        old = hits_at(S, GP_BASE + _RR["disp_old"])
        check(B7_INSN not in [x[0] for x in old],
              f"0x{B7_INSN:05X} no longer reads gp{_RR['disp_old']:+#x} ({len(old)} readers remain "
              f"elsewhere) -- the repoint took, and {TELEMETRY_BIT}'s OLD meaning is gone (attribute "
              f"the build from the tap, not from the label)", "S")
        for _o, _OR in sorted(RUNGS.items()):
            if _o == TELEMETRY_BIT:
                continue
            _keep = hits_at(S, GP_BASE + _OR["disp_old"])
            check(_OR["insn"] in [x[0] for x in _keep],
                  f"the OTHER rung {_o} @0x{_OR['insn']:05X} STILL reads gp{_OR['disp_old']:+#x} -- "
                  f"{_OR['what']} is preserved", "S")

    print("\n  [11b] THE UNCALLED TWIN ISLAND -- no edited cell is read inside it")
    isl = [h for h in S if ISLAND_LO <= h[0] < ISLAND_HI]
    print(f"      {len(isl)} gp/tp-relative accesses inside [0x{ISLAND_LO:05X},0x{ISLAND_HI:05X}) "
          f"({ISLAND_HI - ISLAND_LO} B, six functions, zero callers)")
    for _c, _sites in sorted(ISLAND_CONTROLS.items()):
        got = sorted(h[0] for h in hits_at(S, _c) if ISLAND_LO <= h[0] < ISLAND_HI)
        check(got == sorted(_sites),
              f"CONTROL the island DOES read 0x{_c:05X} at {[hex(a) for a in got]} -- so a null for "
              f"our cells inside this same window is EVIDENCE, not a broken scan", "S")
    for _c, _what in ((FB_A_CELL, "fb pole a"), (FB_B_CELL, "fb pole b"), (R24_CELL, "r24 arm")):
        got = [h[0] for h in hits_at(S, _c) if ISLAND_LO <= h[0] < ISLAND_HI]
        check(got == [],
              f"0x{_c:05X} ({_what}) is read ZERO times inside the dead island -- V291 cannot be "
              f"silently half-applied through the twin, in either direction", "S")
    check(hits_at(S, GP_BASE - 0x6B3C) and
          LIVE_FWD_T in [h[0] for h in hits_at(S, GP_BASE - 0x6B3C)],
          f"the LIVE forward of the gated T is 0x{LIVE_FWD_T:05X} (st.h r16,-0x6b3c[gp]), inside "
          f"FUN_00028ea6 -- NOT the island's dead 0x2B41C copy the older record named", "S")
    check(any(h[0] == 0x2B41C for h in hits_at(S, GP_BASE - 0x6B3C)),
          "and the island's 0x2B41C twin store is present but UNREACHABLE -- both sites are in the "
          "image, only 0x2A2EA runs.  Patching 0x2B41C would patch dead code", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [12] THE DELIVERED SURFACE -- read from the BUILT image, never from a constant")
    sumc, gain, outc = u16(code, 0xC61BE), u16(code, 0xC6CD0), u16(code, 0xC61B4)
    peak = min((sumc * gain) >> 15, outc)
    check(peak == 2505 and ((sumc * gain) >> 15) < outc,
          f"peak delivered forward torque = clamp(0xC61BE {sumc} * 0xC6CD0 {gain} >> 15, +-0xC61B4 "
          f"{outc}) = {peak} counts, and the output clamp does NOT bind -- **UNCHANGED from V282**", "S")
    mp = u32(code, MAP_PTR + 4 * LIVE_SLOT)
    nm_, Xm, Ym = rec(code, mp)
    check(Ym[-1] == 1032 and Xm[-1] == 240,
          f"assist map slot {LIVE_SLOT} @0x{mp:05X}: top Y = {Ym[-1]} at X = {Xm[-1]} (x{1032 / 172:.2f} "
          f"of Honda's 172), slope {Ym[-1] / Xm[-1]:.2f} -- the x6 LINEAR map, UNCHANGED", "S")
    check(u16(code, 0xC63E6) == 0, "Ki is still ZERO -- the integral term is inert, UNCHANGED", "S")
    print(f"      forward path UNCHANGED:  map top {Ym[-1]}  Kp {Y7[0]}  Kd {Ykd[0]}  Ki 0  "
          f"G {gain}  OUT {outc}  SUM {sumc}  -> peak {peak}")
    print(f"      feedback path CHANGED :  pole {f_old:.2f} -> {f_new:.2f} Hz   DC {dc_old:.4f} -> "
          f"{dc_new:.4f} ({100 * (dc_new / dc_old - 1):+.3f} %)   clamp {u16(code, FB_CLAMP_CELL)}")
    print(f"      r24 lane      CHANGED :  engaged gain x{R24_OLD / 1024:.4f} -> x{R24_NEW / 1024:.4f} "
          f"({100.0 * (R24_NEW / R24_OLD - 1):+.2f} %);  latch arm x{1024 / 1024:.4f} UNCHANGED")

    if FULL:
        print("\n  [13] --full: the integer filter driven over the full |x| range at both poles")
        worst = 0
        for xv in list(range(-FB_X_SAT, FB_X_SAT + 1, 37)):
            s_, ok_ = 0, True
            for _ in range(3000):
                _o, s_, ok_ = lkas_fb_lag(xv, s_, ok_, FB_A_NEW, FB_B_NEW)
            worst = max(worst, abs(FB_A_NEW * s_))
        check(worst < 2 ** 31,
              f"--full: worst |a*s| over a full sweep of x in [-{FB_X_SAT},{FB_X_SAT}] is {worst:.3e} "
              f"= x{2 ** 31 / worst:.2f} inside int32", "S")

    # ---------------------------------------------------------------------------------------------
    _scr = os.environ.get("ACCORD_V291_SCRATCH", "").strip()
    if _scr:
        Path(_scr, IMG_NAME).write_bytes(bytes(code))
        Path(_scr, RWD_NAME).write_bytes(rwd)
        print(f"\n      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(IMG_NAME))
        out_rwd = Path(RWD_DIR, RWD_NAME)
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha,
              f"on-disk image re-hashed from the filesystem: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha,
              f"on-disk rwd re-hashed from the filesystem: {out_rwd.name}", "S")
        v291 = sorted(f.name for f in Path(RWD_DIR).glob("*V291*.rwd"))
        others = [n for n in v291 if n != out_rwd.name and not n.startswith("SUPERSEDED")]
        print(f"      V291-line rwds on disk: {len(v291)}  {v291}")
        check(not others, f"exactly ONE flashable V291 rwd on disk (other non-superseded: {others})", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V291_WRITE=rwd to emit the files")

    print("\n" + "=" * 112)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- census: {_census['S']} SUBSTANTIVE, "
          f"{_census['V']} vacuous (entailed by the base sha256), {_census['T']} tautological "
          f"(readback of a write)")
    print(f"  ** V291 {DOSE}: fb pole {corner_hz(FB_A_OLD):.2f} -> {corner_hz(FB_A_NEW):.2f} Hz DC-held "
          f"({100 * (dc_new / dc_old - 1):+.3f} %), r24 engaged arm {R24_OLD} -> {R24_NEW} "
          f"({100.0 * (R24_NEW / R24_OLD - 1):+.2f} %).")
    print(f"  ** {len(diff)} bytes differ from V282: {payload_expected} payload + "
          f"{4 * len(blocks)} CRC.  Forward path (map/gain/clamps/Kp/Kd/Ki) UNTOUCHED, peak torque "
          f"{peak}.")
    if TELEMETRY:
        print(f"  ** CAN 0x14A byte 4 bit {RUNGS[TELEMETRY_BIT]['bit']:#04x} ({TELEMETRY_BIT}) = "
              f"sign(fb-lag state s @gp-0x3d30) -- NEW, set iff s < 0.")
        print(f"  ** every other cave bit keeps V282's meaning, b5/b6 included (the r24 instrument).")
    else:
        print("  ** CAN 0x14A byte 4 UNCHANGED -- the pole move has NO instrument on this image.")
    print(f"  ** 🛑 The 20 Hz benefit is SERVO-SIDE ONLY; r24's 20 Hz sign is UNRESOLVED in the record.")
    print("=" * 112)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
