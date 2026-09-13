# -*- coding: utf-8 -*-
r"""V292 -- V291 (C10) IMPLEMENTED BYTE-EXACTLY: the fb-lag filter's two `sar 0xa` floors get
ERROR-FEEDBACK REMAINDERS, in a 52-byte code cave, so the integer filter's MEAN equals its LINEAR
model's at EVERY amplitude.  The pole itself does not move -- V291's cal pair stays byte-identical.

BASE            V282   (_v282_..._plain_image.bin, sha256 0ea98d06...)
INHERITED       V291's three cal/displacement edits, byte-for-byte:
                  0xC63E8  fb-lag pole `a`   923 -> 962     (9.94 Hz corner, DC held to 0.004 %)
                  0xC63EA  fb-lag pole `b`  1560 -> 958
                  0xC6446  r24 ENGAGED arm  5244 -> 4725    (V84's Lever B, -9.90 %, a partial REVERT)
                  0xC4BAA  0x14A cave b3 rung displacement  -0x3680 -> -0x3D30 = sign(fb state `s`)
NEW IN V292     one 4-byte HOOK + one 52-byte CAVE, 56 code bytes, nothing else:
                  0x28F8E  `mul r16,r7,r0` (f0 3f 20 02) -> `jr 0xC4C00` (89 07 72 bc)
                  0xC4C00  the cave, 15 instructions, ending `jr 0x28FA2` (b6 07 72 43)
                  gp-0x6D74 / gp-0x6D72  two NEW halfword RAM cells, the two remainders
plus the 4-byte CRC trailers of the two blocks that own those bytes (0xC4FFC and 0xC6FFC).

There is NO dose switch.  V292 has exactly one dose -- V291 C10's -- and implements it exactly.

=== 0. 🛑 WHAT THIS BUILD IS, IN ONE PARAGRAPH ====================================================
V291 (C10) lowered the LKAS rate loop's feedback-lag pole 16.53 -> 9.94 Hz to collapse the loop's
return ratio over 12-26 Hz and give the 20 Hz plant mode its damping back.  Its pre-registered
adversarial pass failed exactly ONE clause -- B4's steady state, x1.00 +- 1 % -- and it failed it for
an INTEGER-ARITHMETIC reason, not a control-design one: the smaller `b` widens the filter's input
quantiser from 0.66 to 1.07 raw counts, so at the 1-3 count wheel rates of a grinding episode the
feedback UNDER-READS and the closed loop's steady state departs from its own linear DC by x1.34-1.80
(`ADV-V291-B-LOOP-2026-09-13.md` sec.5.2, sec.11.4).  **V292 keeps the pole cells byte-identical --
the pole stays cal-visible -- and fixes the quantiser instead**, by carrying each `sar 0xa` floor's
residue into the next tick.  Measured, byte-exactly, at the clause's own operating point: the
closed-loop steady state goes from x1.4155 (V291) to **x1.00000** (V292).

🛑 THE MECHANISM STATED PLAINLY, BECAUSE IT IS BIGGER THAN "A QUANTUM OF 1.07 COUNTS":
   Each of the two floors loses half an LSB per tick on average; the state integrates that loss to
   0.5*1024/(1024-a) counts per term, and the two-sample sum doubles it.  On C10 that is a CONSTANT
   -32-count DC OFFSET on the feedback signal, at every amplitude (measured -32.67 / -31.21 / -32.24 /
   -32.93 / -32.44 at A = 1 / 3 / 8 / 64 / 512).  Against `E = 32*sp - fb`, a -32 offset in `fb` is
   **+32 counts of PHANTOM ERROR -- one whole extra setpoint count, permanently.**  At sp = 3
   (E = 96 nominal) that is +33 % of demand.  V282's own bias is -20 counts, which is why V282 is the
   smaller offender rather than an innocent one.

=== 1. THE CAVE, AS INTEGER PYTHON, WITH THE INSTRUCTION ADDRESSES ================================
V850 is LITTLE-ENDIAN and `sar` is an ARITHMETIC shift (floors toward -inf), which Python's `>>` on
`int` matches exactly.  `t & 0x3FF` IS `t - ((t >> 10) << 10)` for two's-complement `t` of EITHER
sign -- worked both ways: t = -1025 -> sar 10 = -2, -2<<10 = -2048, t-(-2048) = 1023; and
(-1025) & 0x3FF = 0xFFFFFBFF & 0x3FF = 1023.  One `andi` therefore replaces mov/shl/sub: 4 bytes
instead of 6, and that is why the cave fits in 52.

    def lkas_fb_lag_v292(x, s, rem_b, rem_a, a=962, b=958, C=46080):
        # --- the cave, 0xC4C00..0xC4C33 ---------------------------------------------------------
        t_b    = b * x + rem_b        # 0xC4C00 mul r16,r7,r0  [copy of 0x28F8E] ; 0xC4C0C add r13,r7
        rem_b  = t_b & 0x3FF          # 0xC4C0E andi 0x3ff,r7,r13 ; 0xC4C12 st.h r13,-0x6d74,gp
        step_b = t_b >> 10            # 0xC4C16 sar 0xa,r7      [copy of 0x28F9A]
        t_a    = a * s + rem_a        # 0xC4C04 mul r26,r9,r0   [copy of 0x28F92] ; 0xC4C1C add r13,r9
        rem_a  = t_a & 0x3FF          # 0xC4C1E andi 0x3ff,r9,r13 ; 0xC4C22 st.h r13,-0x6d72,gp
        step_a = t_a >> 10            # 0xC4C26 sar 0xa,r9      [copy of 0x28FA0]
        #        0xC4C28 ld.hu 0x72e6,tp,r13  and  0xC4C2C ld.hu 0x72e6,tp,r14   RESTORE the clamp
        #        0xC4C30 jr 0x28FA2                                              return
        # --- UNMODIFIED HONDA CODE from here on -------------------------------------------------
        s_new = step_a + step_b       # 0x28FA2 add r7,r9        <-- the return point
        out   = s + s_new             # 0x28FA4 add r9,r26       the TWO-SAMPLE SUM
        s     = s_new                 # 0x28FA8 st.w r9,-0x3d30[gp]   32-bit, stored BEFORE the clamp
        out   = max(-C, min(C, out))  # 0x28FA6..0x28FBC, C = ld.hu 0xC62E6 = 46080
        return out, s, rem_b, rem_a   # out -> r26 -> E = 32*sp - r26 @0x29D78

WHY THE MEAN BECOMES EXACT.  step_b[n] = (b*x[n] + rem_b[n-1] - rem_b[n]) / 1024, so summing
TELESCOPES: Sum(step_b) = (b*Sum(x) + rem_b[0] - rem_b[N]) / 1024 with rem bounded in [0,1023].  The
quantisation error is a FIRST DIFFERENCE of a bounded sequence -- (1 - z^-1)-shaped -- so it carries
EXACTLY ZERO DC and is bounded by 1 LSB per term.  Therefore

    mean(out) -> 2*b*x/(1024-a)  EXACTLY, at every amplitude, x = +-1 included.

Asserted at [10] by EMULATING THE BUILT BYTES, not by running this docstring.

=== 2. WHAT V291 DELIVERS TODAY AND WHAT V292 DELIVERS ============================================
All five rows measured, not asserted.  V291 and V292 carry the SAME a, b and therefore the SAME
linear model; the only difference is how each `sar` disposes of its residue.

  (i)   MEAN GAIN, exact rational over the full periodic orbit, EXHAUSTIVE x = -1491..-1 and 1..1491
        (both signs; the negative side is where V291's floor is biased):
              V292  max |mean/x - 2b/(1024-a)| = EXACTLY ZERO       V291 at x=1: 0.000000 (dead)
        Above |x| = 1491 = C(1024-a)/(2b) = 186.4 deg/s the PRE-EXISTING +-46080 output clamp binds
        and V291 and V292 sit on that rail IDENTICALLY.  That is the clamp, not the quantiser.
  (ii)  FIRST TICK to a sustained 1-count x:  V282 = 1, V291 = 0 on 100 % of phases FOREVER,
        V292 = 1 on 958/1024 phases (mean 0.9355 = b/1024).  vs V291 PASS; vs V282 the clause is
        NOT met deterministically and is REPORTED, not claimed -- it compares two different poles.
        Cumulatively V292 overtakes V282 by tick 5 (11..18 vs 9) and V291 never leaves zero.
  (iii) DESCRIBING-FUNCTION GAIN at 20.3 Hz vs the linear model, A = 1..16 counts:
              V292  0.9994..1.0009, phase error <= 0.16 deg      (tolerance +-0.02)
              V291  0.0735..1.0065, phase error up to +60.3 deg at A = 1, -5.9 deg at A = 3
        An AMPLITUDE-DEPENDENT gain AND phase error inside the very loop whose margin is C10's point.
  (iv)  BYTE-EXACT CLOSED-LOOP STEADY STATE, family median fit, 12000 ticks:
              sp = 3   V282 0.26804   V291 0.37942 (x1.4155)   V292 0.26804 (x1.00000)   <-- B4
              sp = 33  V282 3.10189   V291 3.08251 (x0.9938)   V292 3.05735 (x0.9856)
              sp = 330 V282 30.81275  V291 30.75805 (x0.9982)  V292 30.69103 (x0.9960)
        🛑 sp = 33 is 1.44 % low, OUTSIDE the brief's +-1 %, and it is REPORTED AS A MISS.  The
        control column says why: V282's OWN cal pair with the SAME cave lands at x0.9848, i.e. V282's
        integer reference is itself inflated ~1.5 % by ITS floor bias, and V292 is within 0.09 % of
        V282-with-the-same-correction.  The clause measures V292 against an uncorrected reference
        that carries the very bias V292 removes.  Flagged, not redefined.  [ADV prereg B4 amendment]
  (v)   DEVIATION FROM THE EXACT LINEAR FILTER, 20.3 Hz sine, 20000 scored ticks:
              A=1    V292 mean +0.0000 rms 0.6952 max 1.84    V291 mean -32.6666 rms 10.2508 max 48.46
              A=3    V292 mean -0.0000 rms 0.6767 max 1.91    V291 mean -31.2098 rms  5.3176 max 41.84
              A=512  V292 mean +0.0000 rms 0.5795 max 2.00    V291 mean -32.4370 rms  2.2901 max 40.11
        Arithmetic check on the -32: 0.5*1024/(1024-962) = 8.26 per term x 2 terms x 2 (two-sample
        sum) = 33.  ✔

⇒ THE LINEAR LOOP IS UNCHANGED, so every C10 gate carries over as the SAME NUMBER, not an
  approximation: `gate73` = 1.0099, `Ms` and `pkR` as scored for C10.  gate73/Ms/pkR are functions of
  (a, b, structure) only; the quantiser is not represented in the linear model at all.  What V292
  changes is the small-amplitude NONLINEAR behaviour, which those linear gates never measured.

=== 3. ⭐ THE FREE POSITIVE CONTROL THAT THE CAVE IS LIVE -- ZERO TELEMETRY BITS SPENT ============
V291 already publishes `sign(gp-0x3d30)` -- the fb filter state `s` -- on CAN 0x14A byte 4 bit 3
(`ld.w -0x3d30,gp,r6 ; cmp 0,r6 ; bge +4 ; add 8,r7`).  That rung is on the wire TODAY and V292
does not touch it.

The `s = -1 .. -16` ABSORBING STATE exists on stock, V282 and V291 and NOT on V292: `floor(-a/1024)`
= -1 for every a < 1024, so a negative state below the decay threshold never returns to zero.  With
error feedback, `x = 0` and `s = 0` give `t_a = rem_a < 1024 => step_a = 0` -- a TRUE FIXED POINT.

  measured, symmetric oscillation stopped at 400 different phases, then x = 0 for 2000 ticks:
     osc amplitude      V291 b3 duty at rest (s range)      V292 b3 duty at rest (s range)
        1 count              1.000  (-16..-16)                   0.000  (0..0)
        2                    1.000  (-16.. -4)                   0.000  (0..0)
        3                    0.805  (-16..  0)                   0.000  (0..0)
        5                    0.655  (-16..  0)                   0.000  (0..0)
       16                    0.547  (-16..  0)                   0.000  (0..0)
       64                    0.517  (-16..  0)                   0.000  (0..0)

🛑 PRE-REGISTERED PREDICTION: **0x14A bit-3 duty, measured over wheel-still / near-still intervals,
   falls from 0.52-1.00 on V291 to 0.000 on V292.**  Deterministic on the V292 side (`s` rests at
   EXACTLY 0 on all 400 phases at every amplitude).  If b3 does NOT go to ~0 at rest on a V292 drive,
   THE CAVE IS NOT RUNNING -- that is the instrument for this build's own edit, and it is free.
   [the design memo records its own correction here: an earlier single-phase test read V291 as
    resting at 0 for amplitudes >= 3; the 400-phase sweep shows that was an unlucky sample.]

=== 4. THE SENTENCE A NULL WOULD LICENSE -- WRITTEN BEFORE THE DRIVE ==============================
V292 carries V291's whole pre-registered read (half-peak decay ~545 -> ~183 ms on hands-off creep;
-14 deg +- 4 deg at 10 Hz; b3 transition rate x0.785 of the V282-pole mirror, within-drive,
conditioned on |rate| >= 2 counts and mean rate <= ~1.5 deg/s) PLUS the b3-at-rest control above.

  * If b3-at-rest duty is ~0: the cave IS running and the arithmetic IS mean-exact.  A null on the
    operator's symptom then falsifies **the loop-opening class at the 9.94 Hz dose**, not the
    implementation -- which is precisely what V291 could not license, because V291's own B4 failure
    left "the loop was effectively open below 0.5 deg/s" as a live alternative explanation.
  * If b3-at-rest duty stays 0.5-1.0: the cave is NOT live and NOTHING about the pole is licensed.
    That is a build/flash failure, not a result.

=== 5. 🛑 THE RISK STATEMENT -- UNCHANGED FROM V291, AND IT MUST BE SAID BEFORE THE DRIVE =========
  (a) **THE 9-18 Hz SENSITIVITY SHOULDER.**  C10's worst-fit disturbance sensitivity |1/(1+L)| is
      HIGHER than V282's on 121/121 fits over 3.0-18.2 Hz, peak ratio x1.99 at 12.85 Hz.  It is
      pre-registered as a NAMED REVERT SIGNATURE, not a gate (`ADVERSARIAL-V292-PREREG-2026-09-13.md`):
          f Hz    9     12.85   14     16     18     20.3
          V282  0.70    1.41   1.78   2.58   3.96   18.42
          C10   0.91    2.81   3.25   3.40   3.54    2.64
      **ANY new roughness, tone or line at 10-18 Hz on the drive REVERTS THE BUILD.**  In absolute
      terms C10's shoulder (2.6-3.5 over 12-20 Hz) sits inside what V282 already carries at 16-18 Hz
      (2.6-4.0) with no symptom on record, and the band-wide worst peak falls 18.4 -> 3.5 (x5); the
      shoulder is well damped (no closed-loop pole below zeta 0.36 in 3-30 Hz).  That is the reason
      it is a signature and not a blocker -- the orchestrator's adjudication, marked as such.
  (b) **THE r24 CUT IS A PLANT-SIDE UNKNOWN.**  The 304-fit plant `G` was identified with r24 = 5244
      INSIDE it, so every 20 Hz number is SERVO-SIDE ONLY; and the record disagrees with itself on
      r24's 20 Hz sign (`accord-r24-pumps-at-7hz-and-damps-at-20hz` says it DAMPS at 20 Hz, while
      `grind_loop_shape.py` sec.G measured 5244 -> 512 improving both bands).  If r24 damps at 20 Hz
      this build's two edits fight each other there.  **NOT RESOLVED.  Inherited from V291 unchanged.**
  (c) **THE r24 ARM INVERSION IS PRE-EXISTING AND UNCHANGED.**  `gp-0x671d` is a saturating
      rising-edge latch; on any post-V280 image a latch event COLLAPSES r24 to the 1024 arm (x0.217
      of 4725) rather than doubling it as on stock.  Model r24 as BIMODAL, never as a single gain.
  (d) **THE FORK TOGGLE `AccordCurvatureLead` MUST BE OFF.**  With it ON the prereg's B5 clause fails.
  (e) **NEW IN V292: A CODE CAVE.**  Code caves are this kit's only bricking class (V24, V27, V48B).
      The mitigations are structural and are asserted at [4]/[5]/[9]/[14]/[15]: the displaced span
      0x28F8E..0x28FA0 is straight-line and unconditionally WRITES r7/r9/r13/r14 before reading any
      of them, so the cave's entire register footprint {r7, r9, r13, r14} is dead at the hook BY THE
      ORIGINAL CODE'S OWN STRUCTURE -- zero new liveness claims; `lp` is untouched (jr, never jarl);
      nothing branches into the displaced span (25,418 targets scanned, 12/12 controls); the two RAM
      cells have zero accessors image-wide and boot to 0 from `.data`; and the hook sits AFTER
      Honda's +-12000 plausibility bail at 0x28F50, so the cave's output never re-enters that test.

=== 6. THE DELIVERED SURFACE -- READ FROM THE BUILT IMAGE, NEVER FROM THESE CONSTANTS =============
The FORWARD path is untouched.  Peak delivered forward torque
= clamp((0xC61BE SUM * 0xC6CD0 GAIN) >> 15, +-0xC61B4 OUT) = clamp((15360 * 5346) >> 15, +-3072)
= **2505 counts**, identical to V282 and V291; the output clamp does not bind.  The assist map's top
Y is 1032 at X = 240 -- the x6 LINEAR map, unchanged.  Kp flat 248, Kd flat 128, Ki = 0.  Asserted
at [16] from the image's own bytes.

=== 7. CLASS OF BUILD -- HOW IT DIFFERS FROM THE RECENT ARC ======================================
  * V288 was a REFERENCE-SIDE cave (setpoint pre-filter); it flew and the grinding was UNCHANGED, so
    the excitation-side class is EXHAUSTED.  V289 was an IN-LOOP FILTER (a 20.04 Hz notch on the loop
    output); it flew, removed the 20 Hz mode entirely, and a DIFFERENT pre-existing 15-17 Hz pole
    took its margin.  V291 was the FIRST LOOP-OPENING build -- a pole move that collapses the return
    ratio rather than shaping it.
  * **V292 is not a new lever at all.  It is the SAME lever as V291, at the SAME dose, with its
    INTEGER IMPLEMENTATION corrected.**  That is a class this kit has never cut: every previous
    "same lever again" build changed the dose or the direction.  V292 changes NEITHER -- the cal pair
    is byte-identical to V291's -- and changes only the arithmetic that realises it.
  * What makes a different result likely is measured, not hoped: on V291 the rate loop is effectively
    OPEN below ~0.5 deg/s (the 1.07-count quantum) and carries a constant -32-count phantom error;
    on V292 neither is true at any amplitude.  V291's B4 failure and V292's B4 pass are the same
    number computed on the two images.
  * V292 DOMINATES V291 and supersedes it: same cells, same dose, strictly better arithmetic, plus a
    free liveness control.  On write, V291's rwd and image are renamed SUPERSEDED-DO-NOT-FLASH-*.

=== 8. WHAT THIS SCRIPT DOES *NOT* ASSERT ========================================================
  1. `Ts = 1 ms` is EVIDENCE-BY-CONSISTENCY (stock a = 923 -> 16.53 Hz matches the record's "16.5 Hz";
     V289's a = 875 -> 25.03 Hz matches its own build tag).  It is NOT a scheduler read.  Every
     frequency printed here inherits that.
  2. CYCLE COST IN REAL TIME.  The cave is +10 instructions on a 1,874-instruction 1 kHz function
     (+0.53 %).  For scale, V289's flown cave was 53 instructions; V292's is 15.  No core clock, no
     wait states, no measurement.  BELIEF, bounded by a flown precedent.
  3. GATE 2 AGAINST THE LOOP'S OTHER NONLINEARITIES.  V292 removes one nonlinearity and is measured
     more linear at every amplitude tested; it is NOT proved free of adverse interaction with the P
     clamp, the D clamp, the sum clamp or the output-lag `sar 5`, none of which it touches.
  4. THE COLD-BOOT RAM CLEAR.  Both remainder cells' `.data` SOURCE is proved zero (flash 0x8633C /
     0x8633E, anchor-controlled against gp-0x6AB0's known non-zero source).  The startup clear loop
     was NOT located.  This is why the design uses `ld.hu` and not `ld.w`: any value the cell could
     hold is bounded to 65,535, and one `andi 0x3ff` returns it to [0,1023] on the first tick.
  5. A BIT-OP (`set1`/`clr1`/`not1`/`tst1`) POSITIVE CONTROL FROM THE WILD.  The image contains no
     attested gp/tp-relative Format-VIII instruction, so that scanner is controlled SYNTHETICALLY at
     [14] (the form is injected into a scratch copy and must be found).  Stated as such.
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
# the V292 cave mirror lives in the rlog-tools kit, one level up from this kit's root
_grind = _d.parent / "rlog-tools" / "studies" / "grind"
if _grind.is_dir() and str(_grind) not in sys.path:
    sys.path.insert(0, str(_grind))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, ANALYSIS_ROOT                # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402
import v292_cave_mirror as MIR                                                     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
GP_BASE, TP_BASE = 0xFEDF8000, 0xBF000
TICK_S = 0.001
WRITE_MODE = os.environ.get("ACCORD_V292_WRITE", "").strip().lower()
FULL = ("--full" in sys.argv) or os.environ.get("ACCORD_V292_FULL", "") == "1"

# ---- [A] the base ---------------------------------------------------------------------------------
BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080"
             ".TORQUE.TAP_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"

# ---- [B] V291's edits, inherited byte-for-byte -----------------------------------------------------
FB_A_CELL, FB_A_OLD, FB_A_NEW = 0xC63E8, 923, 962      # ld.h  0x73e8[tp] @0x28F8A   ** SIGNED **
FB_B_CELL, FB_B_OLD, FB_B_NEW = 0xC63EA, 1560, 958     # ld.hu 0x73ea[tp] @0x28F86   UNSIGNED
R24_CELL, R24_OLD, R24_NEW = 0xC6446, 5244, 4725       # ld.hu 0x7446[tp] @0x3AC08   Q10, ENGAGED arm
K_GATE = 0.9012                                        # the memo's published k that restores gate73
FB_A_LOAD, FB_A_LOAD_BYTES = 0x28F8A, bytes.fromhex("254fe873")
FB_B_LOAD, FB_B_LOAD_BYTES = 0x28F86, bytes.fromhex("e587eb73")
R24_LOAD, R24_LOAD_BYTES = 0x3AC08, bytes.fromhex("e5574774")
R24_SIBLINGS = {0x3ABFE: (0xC6442, "the gp-0x671d LATCH arm -- outranks all"),
                0x3AC12: (0xC6440, "the r2 arm")}
FB_X_SAT = 12000
FB_CLAMP_CELL, FB_CLAMP = 0xC62E6, 46080
DC_TARGET = 3120.0 / 101.0                             # V282's 2b/(1024-a) = 30.8911
DC_TOL = 0.002

# the 0x14A telemetry cave and V291's b3 rung repoint
CAVE14A_START, CAVE14A_END = 0xC4B34, 0xC4BD8
CAVE14A_HOOK, CAVE14A_HOOK4 = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp
B3_INSN, B3_HW1 = 0xC4BA8, 0x3724                      # ld.w <disp>,gp,r6   -- hw1 NEVER touched
B3_HW2_OLD, B3_HW2_NEW = 0xC981, 0xC2D1                # -0x3680 (Stage C) -> -0x3D30 (the fb state)
S_DISP = -0x3D30                                       # gp-0x3d30 = 0xFEDF42D0, the fb-lag state `s`
CAVE14A_OTHER_LOADS = {0xC4B34: (0x3724, 0x9526), 0xC4B40: (0x3724, 0x94C8),   # b6: |r24| >= |T|
                       0xC4B62: (0x3724, 0x9526), 0xC4B6E: (0x3724, 0x946C),   # b5: |r24| >= |agg|
                       0xC4B9C: (0x3724, 0x9526)}                              # b4: sign(r24)
B3_MASK_SITE, B3_MASK, STOCK_B4_BITS = 0xC4BB8, 0x0067, 0x07

# ---- [C] THE NEW CAVE -----------------------------------------------------------------------------
HOOK = 0x28F8E                     # `mul r16,r7,r0`, f0 3f 20 02
HOOK_STOCK = bytes.fromhex("f03f2002")
RETURN_TO = 0x28FA2                # `add r7,r9`, c7 49
RETURN_STOCK = bytes.fromhex("c749")
CAVE = 0xC4C00
CAVE_LEN = 52
REM_B_DISP, REM_A_DISP = -0x6D74, -0x6D72
REM_B_ABS, REM_A_ABS = GP_BASE + REM_B_DISP, GP_BASE + REM_A_DISP      # 0xFEDF128C / 0xFEDF128E
FREE_RUN_LO, FREE_RUN_HI = GP_BASE - 0x6D74, GP_BASE - 0x6D2C          # the certified 72-byte run
DATA_SRC_ANCHOR_RAM, DATA_SRC_ANCHOR_FLASH = 0xFEDF11B0, 0x86260       # .data map anchor
REM_B_SRC, REM_A_SRC = 0x8633C, 0x8633E
DATA_CTRL_RAM, DATA_CTRL_BYTES = GP_BASE - 0x6AB0, bytes.fromhex("88028802")   # known NON-zero .data
SKIPPED_LO, SKIPPED_HI = 0x28F92, 0x28FA2       # the now-orphaned instructions
STOCK_WIN_LO, STOCK_WIN_HI = 0x28F86, 0x28FAC   # the encoder's whole-window positive control
STRUCT_12B = (0xC4FF0, bytes.fromhex("010101010000c600130 0b200".replace(" ", "")))
CAVE_FF_LO, CAVE_FF_HI = 0xC4C00, 0xC4C40       # 52 cave bytes + 12 bytes of asserted margin

# the memo's own listing, sec.5 -- asserted against an INDEPENDENT re-encode AND an INDEPENDENT decode
MEMO_CAVE = [
    (0xC4C00, "f03f2002", "mul   r16,r7,r0"),
    (0xC4C04, "fa4f2002", "mul   r26,r9,r0"),
    (0xC4C08, "e46f8d92", "ld.hu -0x6d74,gp,r13"),
    (0xC4C0C, "cd39",     "add   r13,r7"),
    (0xC4C0E, "c76eff03", "andi  0x3ff,r7,r13"),
    (0xC4C12, "646f8c92", "st.h  r13,-0x6d74,gp"),
    (0xC4C16, "aa3a",     "sar   0xa,r7"),
    (0xC4C18, "e46f8f92", "ld.hu -0x6d72,gp,r13"),
    (0xC4C1C, "cd49",     "add   r13,r9"),
    (0xC4C1E, "c96eff03", "andi  0x3ff,r9,r13"),
    (0xC4C22, "646f8e92", "st.h  r13,-0x6d72,gp"),
    (0xC4C26, "aa4a",     "sar   0xa,r9"),
    (0xC4C28, "e56fe772", "ld.hu 0x72e6,tp,r13"),
    (0xC4C2C, "e577e772", "ld.hu 0x72e6,tp,r14"),
    (0xC4C30, "b60772 43".replace(" ", ""), "jr    0x28fa2"),
]
MEMO_HOOK = "890772bc"
# every encoding form, with the STOCK instance that pins it (memo sec.5.1) -- each one re-read from
# the base image's own bytes, and each one confirmed by GHIDRA's V850 decoder (2026-09-13).
ENC_CONTROLS = [
    (0x28F8E, "f03f2002", "mul r16,r7,r0",        "the displaced instruction itself"),
    (0x28F92, "fa4f2002", "mul r26,r9,r0",        "the second displaced mul"),
    (0x28F96, "e56fe772", "ld.hu 0x72e6,tp,r13",  "pins ld.hu-tp into r13"),
    (0x28F9C, "e577e772", "ld.hu 0x72e6,tp,r14",  "pins ld.hu-tp into r14"),
    (0x28F9A, "aa3a",     "sar 0xa,r7",           "pins sar imm5 into r7"),
    (0x28FA0, "aa4a",     "sar 0xa,r9",           "pins sar imm5 into r9"),
    (0x17B74, "cd39",     "add r13,r7",           "pins the add reg1=13 field"),
    (0x28FA2, "c749",     "add r7,r9",            "pins the add reg2=9 field"),
    # 🛑 The design memo sec.5.1 cites 0xAD7E (`andi 0x2,r7,r13`) and 0x2378 (`andi 0x3,r13,r10`) for
    #    these two forms.  Both are BELOW 0x13000, i.e. OUTSIDE the flashed region, so in every plain
    #    image they read 0xFF filler and cannot control anything here.  (The memo's own control script
    #    reads the stock `code.bin` dump, where they are real.)  These two replacements are inside
    #    [0x13000,0xC5000), are byte-identical to stock, and are STRICTLY BETTER controls -- each
    #    carries the EXACT hw1 of the cave instruction it pins, so only the imm16 differs.
    (0x1537C, "c76eff00", "andi 0xff,r7,r13",     "EXACT hw1 of andi 0x3ff,r7,r13 -- only imm16 differs"),
    (0x34566, "c96effff", "andi 0xffff,r9,r13",   "EXACT hw1 of andi 0x3ff,r9,r13 -- only imm16 differs"),
    (0x1982E, "e46f6995", "ld.hu -0x6a98,gp,r13", "SAME hw1 as the cave's two gp ld.hu"),
    (0x19C84, "646f1cc1", "st.h r13,-0x3ee4,gp",  "SAME hw1 as the cave's two gp st.h; disp EVEN => st.h"),
    (0x28F62, "80074e01", "jr 0x290b0",           "Format-V disp22, small +ve"),
    (0x14030, "87073206", "jr 0x84662",           "Format-V disp22, large +ve (+0x70632)"),
    (0x86252, "b80792e9", "jr 0x14be4",           "Format-V disp22, large -ve (-0x7166e), sign bit set"),
]

# ---- [D] carried from V282/V291, asserted byte-identical -------------------------------------------
PACK_LO, PACK_HI = 0x55DF0, 0x55E12            # the CAN-427 delivered-torque tap
MAP_PTR, MAP_N = 0xC9A88, 10
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y = (0, 68, 112, 136, 208), (248,) * 5
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)
FWD_GAIN_REPOINT = (0x2A1F0, bytes.fromhex("d07c"))
ISLAND_LO, ISLAND_HI = 0x2A30E, 0x2B422
LIVE_FWD_T = 0x2A2EA
ISLAND_CONTROLS = {0xC63EC: [0x2A8A2], 0xC63EE: [0x2A892], 0xC61B6: [0x2ADD4, 0x2ADDC, 0x2ADEC]}

FROZEN = {
    0xC61B2: 3072, 0xC61B4: 3072,            # forward tracking clamps
    0xC61B6: 10240,                          # D clamp
    0xC61B8: 102,                            # post-lag deadband
    0xC61BA: 10240,                          # integrator anti-windup
    0xC61BC: 15360,                          # P clamp
    0xC61BE: 15360,                          # post-gain SUM clamp -- the 2505 ceiling
    0xC61F6: 3,                              # Coulomb deadband on the r24 lane
    0xC61F8: 1024, 0xC61FA: 5530,            # the gp-0x671d latch RELEASE / SET thresholds
    0xC62E4: 4,
    0xC62E6: 46080,                          # feedback saturation clamp -- the cave RESTORES it
    0xC63E6: 0,                              # Ki -- ships at ZERO
    0xC63EC: 992, 0xC63EE: 507,              # OUTPUT-lag pole -- deliberately NOT moved
    0xC6440: 2048, 0xC6442: 1024, 0xC6444: 512, 0xC6448: 1024, 0xC644A: 1024,
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


def corner_hz(a, ts=TICK_S):
    return -math.log(a / 1024.0) / (2 * math.pi * ts)


def dc_gain(a, b):
    return 2.0 * b / (1024 - a)


# ---- [E] 🛑 D2 FIX: THE OUTPUT TAG IS DERIVED FROM THE INTEGERS, never a hard-coded literal --------
# V291's defect D2: `DOSES["C10"]["tag"]` was the string "FBPOLE.10HZ.962.958-R24.4725" and nothing
# tied it to a/b/r24 -- a copy with r24 = 4722 passed 487/487 assertions and shipped under the 4725
# name.  Here every number in the name comes from the variable that is written to the image, and [17]
# re-derives the whole name FROM THE BUILT IMAGE'S OWN BYTES and asserts it is the name being used.
def make_tag(a, b, r24, cave_addr, rem_b_disp):
    # Every field comes from a variable that is written to the image.  Kept SHORT on purpose: the
    # .rwd path must stay under this machine's 259-character limit (measured), and [18] asserts it.
    return (f"V292-V282BASE-EFCAVE.{cave_addr:05X}.{abs(rem_b_disp):04X}"
            f"-FBPOLE.{corner_hz(a):.0f}HZ.{a}.{b}-R24.{r24}"
            f"-B3.FBSTATE-KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP")


TAG = make_tag(FB_A_NEW, FB_B_NEW, R24_NEW, CAVE, REM_B_DISP)
IMG_NAME = f"_v292_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
# the build V292 supersedes -- renamed on write, never deleted
V291_IMG = ("_v291c10_V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-KP.FLAT.Y0"
            "-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V291_RWD = ("39990-TVA,A160-V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-KP.FLAT.Y0"
            "-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd")
V291_IMG_SHA = "a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657"
# V291's cal-block CRC, recorded in DESIGN-V292-FBLP-CAVE-2026-09-13.md sec.4.3 before this script
# existed.  V292 touches NO cal byte beyond V291's three cells, so 0xC6FFC must come out identical.
V291_CAL_CRC = 0xED9B12BB
# 🛑 24 characters, deliberately.  V291's rwd path is already 232 chars and this machine refuses
# any path of 260 or more (measured: 259 opens, 260 fails, for both open and rename).
SUPERSEDE_PREFIX = "SUPERSEDED-DO-NOT-FLASH-"
MAX_PATH = 259

OK, BAD = "[PASS]", "[FAIL]"
# ---- assertion census -----------------------------------------------------------------------------
#  S = SUBSTANTIVE -- a wrong edit could fail it AND it is not entailed by an assertion already made
#  V = VACUOUS     -- entailed by the base sha256 (reads only `base`), or entailed by an EARLIER
#                     assertion in this same run.  The entailing assertion is named in the message.
#  T = TAUTOLOGICAL-- a readback of a value this script just wrote
# 🛑 V291's script reported 377 SUBSTANTIVE and an independent auditor counted 67 (ADV-V291-C D1).
#    The rule applied here is ENTAILMENT, not call sites: the full-coverage diff at [6] entails every
#    byte-identity check that follows it, so those are V and say so.
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
#  AN INDEPENDENT V850E2 DECODER -- written from the ISA field layout, NOT by inverting the encoder.
#  It is the second decoder required by the design memo sec.7 item 12.  Every rule below was
#  confirmed against GHIDRA's own V850 decoder on a stock instance (2026-09-13):
#     jr      0x28F62 80074e01 -> jr 0x290b0          (reg2 == 0, hw2 bit0 == 0)
#     jarl    0x22522 80ff8469 -> jarl 0x28ea6, lp    (reg2 != 0, hw2 bit0 == 0)
#     ld.bu   0x28F66 844fd5c2 -> ld.bu -0x3d2c,gp,r9 (reg2 != 0, hw2 bit0 == 1  <-- THE DISCRIMINATOR)
#  `jr`/`jarl`/`ld.bu` all share opcode bits 10..6 = 0x1E; hw2 bit 0 separates the load from the
#  branch, and `ld.bu` carries displacement bit 0 in hw1 bit 5, never in hw2.  This decoder RAISES on
#  anything it cannot resolve -- it never guesses.
# =====================================================================================================
def decode_one(buf, off):
    """Return (length, mnemonic, operand_text, fields_dict).  Raises on an unresolvable encoding."""
    hw1 = struct.unpack_from("<H", buf, off)[0]
    reg1, opc, reg2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, (hw1 >> 11) & 0x1F
    rn = (lambda r: {0: "r0", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}.get(r, f"r{r}"))
    # ---- 2-byte Format I (reg-reg) and Format II (imm5) ------------------------------------------
    if opc == 0x0E:
        return 2, "add", f"{rn(reg1)},{rn(reg2)}", dict(reg1=reg1, reg2=reg2)
    if opc == 0x0F:
        return 2, "cmp", f"{rn(reg1)},{rn(reg2)}", dict(reg1=reg1, reg2=reg2)
    if opc == 0x15:
        return 2, "sar", f"{reg1:#x},{rn(reg2)}", dict(imm5=reg1, reg2=reg2)
    # ---- the 0x1E group: jr / jarl / ld.bu, separated by reg2 and hw2 bit 0 ------------------------
    if (hw1 >> 6) & 0x1F == 0x1E:
        hw2 = struct.unpack_from("<H", buf, off + 2)[0]
        if hw2 & 1:
            disp = sext16((hw2 & 0xFFFE) | ((hw1 >> 5) & 1))
            return 4, "ld.bu", f"{disp:#x},{rn(reg1)},{rn(reg2)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        d = ((hw1 & 0x3F) << 16) | hw2
        if d & (1 << 21):
            d -= (1 << 22)
        tgt = off + d
        if reg2 == 0:
            return 4, "jr", f"{tgt:#x}", dict(disp=d, target=tgt)
        return 4, "jarl", f"{tgt:#x},{rn(reg2)}", dict(disp=d, target=tgt, reg2=reg2)
    # ---- 4-byte Format VI (imm16 ALU) -------------------------------------------------------------
    if opc == 0x36:
        imm = struct.unpack_from("<H", buf, off + 2)[0]
        return 4, "andi", f"{imm:#x},{rn(reg1)},{rn(reg2)}", dict(imm16=imm, reg1=reg1, reg2=reg2)
    # ---- 4-byte Format VII (disp16 load/store) ----------------------------------------------------
    if opc in (0x38, 0x39, 0x3A, 0x3B, 0x3F):
        hw2 = struct.unpack_from("<H", buf, off + 2)[0]
        if opc == 0x38:
            return 4, "ld.b", f"{sext16(hw2):#x},{rn(reg1)},{rn(reg2)}", dict(disp=sext16(hw2))
        if opc == 0x3A:
            return 4, "st.b", f"{rn(reg2)},{sext16(hw2):#x},{rn(reg1)}", dict(disp=sext16(hw2))
        disp = sext16(hw2 & 0xFFFE)
        if opc == 0x39:
            m = "ld.w" if hw2 & 1 else "ld.h"
            return 4, m, f"{disp:#x},{rn(reg1)},{rn(reg2)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        if opc == 0x3B:
            m = "st.w" if hw2 & 1 else "st.h"
            return 4, m, f"{rn(reg2)},{disp:#x},{rn(reg1)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        # opc 0x3F: ld.hu (hw2 bit0 == 1) or the Format XI/IX group (mul, ...)
        if hw2 & 1:
            return 4, "ld.hu", f"{disp:#x},{rn(reg1)},{rn(reg2)}", dict(disp=disp, reg1=reg1, reg2=reg2)
        if (hw2 & 0x07FF) == 0x0220:
            reg3 = (hw2 >> 11) & 0x1F
            return 4, "mul", f"{rn(reg1)},{rn(reg2)},{rn(reg3)}", dict(reg1=reg1, reg2=reg2, reg3=reg3)
        raise ValueError(f"0x{off:05X}: opcode 0x3F with hw2 0x{hw2:04X} -- UNRESOLVED, refusing to guess")
    raise ValueError(f"0x{off:05X}: hw1 0x{hw1:04X} (opc 0x{opc:02X}) -- UNRESOLVED, refusing to guess")


def decode_range(buf, lo, hi):
    out, pc = [], lo
    while pc < hi:
        n, mn, ops, f = decode_one(buf, pc)
        out.append((pc, bytes(buf[pc:pc + n]), mn, ops, f))
        pc += n
    return out


# =====================================================================================================
#  A MICRO-EMULATOR FOR THE BUILT CAVE BYTES.  Design memo sec.7 item 13: "assert the arithmetic
#  behaviourally, by EMULATING THE BUILT CAVE'S BYTES".  Nothing here reads the encoder or the
#  mirror's model -- the decoded instruction stream drives it.
# =====================================================================================================
class CaveVM:
    """Executes the decoded cave.  Memory is two gp halfwords plus the tp cal reads, taken from the
    image being tested.  `sar` floors toward -inf (Python `>>` on int).  32-bit wrap on every write."""

    def __init__(self, img, cave=CAVE, ret=RETURN_TO):
        self.img = bytes(img)
        self.prog = decode_range(self.img, cave, cave + CAVE_LEN)
        self.entry, self.ret = cave, ret
        self.ram = {}                      # gp-relative displacement -> halfword value
        # the two Honda instructions after the return point, decoded from the SAME image
        self.epi = [decode_one(self.img, RETURN_TO), decode_one(self.img, RETURN_TO + 2)]

    # -- helpers ------------------------------------------------------------------------------------
    @staticmethod
    def _w32(v):
        v &= 0xFFFFFFFF
        return v - 0x100000000 if v & 0x80000000 else v

    def _load_hu(self, base, disp):
        if base == 4:                                   # gp -- our RAM cells
            return self.ram.get(disp, 0) & 0xFFFF
        if base == 5:                                   # tp -- a cal read straight out of the image
            return u16(self.img, TP_BASE + disp)
        raise ValueError(f"ld.hu from an unexpected base r{base}")

    def _store_h(self, base, disp, val):
        if base != 4:
            raise ValueError(f"st.h to an unexpected base r{base}")
        self.ram[disp] = val & 0xFFFF

    # -- one filter tick ----------------------------------------------------------------------------
    def tick(self, x, s, a, b, clamp):
        """Run the hook's target (the cave) then Honda's two adds.  Returns (out_preclamp, s_new)."""
        R = [0] * 32
        R[7], R[9], R[16], R[26] = x, a, b, s        # the live inputs at the hook, per the disassembly
        touched = set()
        for pc, by, mn, ops, f in self.prog:
            if mn == "mul":
                R[f["reg2"]] = self._w32(R[f["reg1"]] * R[f["reg2"]])
                if f["reg3"]:
                    R[f["reg3"]] = self._w32((R[f["reg1"]] * R[f["reg2"]]) >> 32)
            elif mn == "add":
                R[f["reg2"]] = self._w32(R[f["reg2"]] + R[f["reg1"]])
            elif mn == "sar":
                R[f["reg2"]] = R[f["reg2"]] >> f["imm5"]
            elif mn == "andi":
                R[f["reg2"]] = (R[f["reg1"]] & 0xFFFFFFFF) & f["imm16"]
            elif mn == "ld.hu":
                R[f["reg2"]] = self._load_hu(f["reg1"], f["disp"])
            elif mn == "st.h":
                self._store_h(f["reg1"], f["disp"], R[f["reg2"]])
                touched.add(f["disp"])
            elif mn == "jr":
                if f["target"] != self.ret:
                    raise ValueError(f"cave jr at 0x{pc:05X} goes to 0x{f['target']:05X}, not the return")
                break
            else:
                raise ValueError(f"cave carries an instruction the VM does not model: {mn}")
            R[0] = 0                                  # r0 is hardwired zero on V850
        # Honda's unmodified epilogue, decoded from the image: add r7,r9 ; add r9,r26
        for n, mn, ops, f in self.epi:
            if mn != "add":
                raise ValueError(f"epilogue at the return point is {mn}, expected add")
            R[f["reg2"]] = self._w32(R[f["reg2"]] + R[f["reg1"]])
        out = max(-clamp, min(clamp, R[26]))
        return out, R[9], self.ram.get(REM_B_DISP, 0), self.ram.get(REM_A_DISP, 0)

    def run(self, xs, a, b, clamp, s0=0):
        s, outs = s0, []
        for x in xs:
            o, s, _rb, _ra = self.tick(x, s, a, b, clamp)
            outs.append(o)
        return outs, s


def vm_mean_over_cycle(vm, a, b, clamp, x, max_ticks=200000):
    """Drive a CONSTANT x through the EMULATED BYTES to its periodic orbit; exact rational mean."""
    from fractions import Fraction
    vm.ram.clear()
    s, seen, hist = 0, {}, []
    for k in range(max_ticks):
        key = (s, vm.ram.get(REM_B_DISP, 0), vm.ram.get(REM_A_DISP, 0))
        if key in seen:
            cyc = hist[seen[key]:]
            return Fraction(sum(cyc), len(cyc)), len(cyc)
        seen[key] = len(hist)
        o, s, _rb, _ra = vm.tick(x, s, a, b, clamp)
        hist.append(o)
    raise RuntimeError(f"no cycle found for x = {x}")


# =====================================================================================================
#  THE TWO-ENCODING gp/tp-RELATIVE CENSUS (V291's scanner, unchanged) + a Format-VIII bit-op scanner.
# =====================================================================================================
def scan_rel(img, lo=START, hi=END):
    out, n = [], min(hi, len(img))
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


def scan_bitop(img, lo=START, hi=END):
    """Format VIII: hw1 = op<<14 | bit#<<11 | 0x3E<<5 | reg1 ; hw2 = disp16 (FULL 16 bits, no mask).
    The image contains no attested gp/tp instance, so this scanner is SYNTHETICALLY controlled."""
    names = {0: "set1", 1: "not1", 2: "clr1", 3: "tst1"}
    out = []
    for a in range(lo, min(hi, len(img)) - 3, 2):
        w0 = struct.unpack_from("<H", img, a)[0]
        if ((w0 >> 5) & 0x3F) != 0x3E:
            continue
        reg1 = w0 & 0x1F
        if reg1 not in (4, 5):
            continue
        w1 = struct.unpack_from("<H", img, a + 2)[0]
        out.append((a, "gp" if reg1 == 4 else "tp", sext16(w1), names[(w0 >> 14) & 3], (w0 >> 11) & 7))
    return out


def hits_at(scan, abs_addr):
    return [h for h in scan
            if ((TP_BASE + h[2]) if h[1] == "tp" else (GP_BASE + h[2])) == abs_addr]


def scan_abs(img, target, lo=START, hi=END):
    return [a for a in range(lo, min(hi, len(img)) - 3)
            if struct.unpack_from("<I", img, a)[0] == target]


def scan_movhi_movea(img, lo, hi, ram_lo, ram_hi):
    """`movhi imm16,reg1,reg2` (opc 0x32) followed within 8 bytes by `movea imm16,reg1,reg2` (0x31)
    whose combined 32-bit value lands in [ram_lo, ram_hi)."""
    out = []
    for a in range(lo, min(hi, len(img)) - 11, 2):
        w0 = struct.unpack_from("<H", img, a)[0]
        if ((w0 >> 5) & 0x3F) != 0x32:
            continue
        hi16 = struct.unpack_from("<H", img, a + 2)[0]
        for d in (4, 6, 8):
            w2 = struct.unpack_from("<H", img, a + d)[0]
            if ((w2 >> 5) & 0x3F) != 0x31:
                continue
            lo16 = struct.unpack_from("<H", img, a + d + 2)[0]
            val = ((hi16 << 16) + sext16(lo16)) & 0xFFFFFFFF
            if ram_lo <= val < ram_hi:
                out.append((a, val))
    return out


def scan_branch_targets(img, lo=START, hi=0xC5000):
    """Every STATICALLY RESOLVABLE branch target: Format-V (`jr`/`jarl`, disp22) and Format-III
    (`Bcond`, disp9).  Returns {target: [(kind, site), ...]}.  The recorded traps are applied:
      * the 0x1E opcode group is SHARED with `ld.bu`, so a candidate whose hw2 bit 0 is set is a
        LOAD, not a branch (Ghidra-confirmed on 0x28F66 `ld.bu -0x3d2c,gp,r9`);
      * odd Format-V targets are rejected -- a V850 instruction is always halfword aligned;
      * Format III is `ddddd 1011 ddd cccc`: disp[8:4] in bits 15-11, disp[3:1] in bits 6-4, the
        displacement is in HALFWORDS, sign-extended at bit 8 and then doubled.  Confirmed on
        `ble 0x28FB2` @0x28FAC (b7 05) and `bge +4` (ae 05).
    🛑 BOUNDARY: indirect dispatch (`jmp [reg]`, a jump table) cannot be resolved statically and is
    NOT covered by this or by any scan in this kit."""
    tg = {}
    n = min(hi, len(img))
    for a in range(lo, n - 4, 2):
        w0 = struct.unpack_from("<H", img, a)[0]
        if w0 == 0xFFFF:
            continue
        if (w0 >> 6) & 0x1F == 0x1E:
            w1 = struct.unpack_from("<H", img, a + 2)[0]
            if not (w1 & 1):
                d = ((w0 & 0x3F) << 16) | (w1 & 0xFFFE)
                if d & (1 << 21):
                    d -= (1 << 22)
                t = a + d
                if lo <= t < n and t % 2 == 0:
                    tg.setdefault(t, []).append(("jarl" if (w0 >> 11) else "jr", a))
        if (w0 & 0x0780) == 0x0580:                        # Format III  Bcond disp9
            d = (((w0 >> 11) & 0x1F) << 4) | ((w0 >> 4) & 0x7)
            if d & 0x100:
                d -= 0x200
            t = a + 2 * d
            if lo <= t < n:
                tg.setdefault(t, []).append(("bcond", a))
    return tg


# the 12 targets the scanner MUST find before any of its nulls is worth anything.  Every one is read
# off Ghidra's own listing, and they deliberately span both formats and both directions.
BRANCH_CONTROLS = [
    (0x290B0, "jr", 0x28F62), (0x28F66, "bcond", 0x28F60), (0x28F82, "bcond", 0x28F76),
    (0x28F86, "bcond", 0x28F80), (0x28FB2, "bcond", 0x28FAC), (0x28FBE, "bcond", 0x28FB0),
    (0x28FBE, "bcond", 0x28FB6), (0x28FC8, "bcond", 0x28FC4), (0x2A164, "jr", 0x29A5C),
    (0x2A164, "jr", 0x29A64), (0x2A0C6, "jr", 0x29A70), (0x28EA6, "jarl", 0x22522),
]


def independent_rebuild(base):
    """A SECOND implementation with none of build()'s bookkeeping: patch the halfwords and splice the
    cave directly, then re-CRC every owning block via FF.crc_block_map rather than V53.owning_block.
    🛑 It shares this module's constants, so it CANNOT catch a wrong constant (V291 defect D4) -- it
    is a CRC-LOCATION and SPLICE cross-check, and it is labelled as exactly that."""
    img = bytearray(base)
    touched = set()
    for addr, old, new in ((FB_A_CELL, FB_A_OLD, FB_A_NEW), (FB_B_CELL, FB_B_OLD, FB_B_NEW),
                           (R24_CELL, R24_OLD, R24_NEW)):
        assert struct.unpack_from("<H", img, addr)[0] == old
        struct.pack_into("<H", img, addr, new)
        touched |= {addr, addr + 1}
    assert struct.unpack_from("<H", img, B3_INSN + 2)[0] == B3_HW2_OLD
    struct.pack_into("<H", img, B3_INSN + 2, B3_HW2_NEW)
    touched |= {B3_INSN + 2, B3_INSN + 3}
    hk, cv, _ = MIR.build_cave(cave=CAVE, hook=HOOK, ret=RETURN_TO, rb=REM_B_DISP, ra=REM_A_DISP)
    img[HOOK:HOOK + 4] = hk
    img[CAVE:CAVE + len(cv)] = cv
    touched |= set(range(HOOK, HOOK + 4)) | set(range(CAVE, CAVE + len(cv)))
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


# =====================================================================================================
def build():
    print("=" * 116)
    print(f"  V292 -- V291 (C10) with ERROR-FEEDBACK REMAINDERS on both `sar 0xa` floors.")
    print(f"          pole cells UNCHANGED from V291 ({FB_A_NEW}/{FB_B_NEW}, {corner_hz(FB_A_NEW):.2f} Hz); "
          f"r24 arm UNCHANGED ({R24_NEW}); b3 rung UNCHANGED")
    print(f"          NEW: hook 0x{HOOK:05X} + {CAVE_LEN}-byte cave 0x{CAVE:05X} "
          f"+ two RAM halfwords gp{REM_B_DISP:+#x}/gp{REM_A_DISP:+#x}")
    print(f"  🛑 V291's B4 failure was ARITHMETIC, not control design: the 1.07-count input quantum")
    print(f"     left the rate loop effectively OPEN below ~0.5 deg/s and carried a CONSTANT -32-count")
    print(f"     phantom error.  V292 removes both.  The 9-18 Hz shoulder REVERT SIGNATURE is unchanged.")
    print("=" * 116)

    # ---------------------------------------------------------------------------------------------
    print("\n  [1] BASE = V282")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          "V282 base sha256 matches the record (build_v287/v289/v291 BASE_SHA)", "S")
    # 🛑 PIN THE MIRROR.  Several kit modules put `rlog-tools/studies/grind` on sys.path themselves,
    #    so plain import order does NOT decide which `v292_cave_mirror.py` is loaded.  A build script
    #    that silently picks up a different assembler is a V274-class hazard.
    mir_path = Path(MIR.__file__).resolve()
    want_mir = (_d.parent / "rlog-tools" / "studies" / "grind" / "v292_cave_mirror.py").resolve()
    check(mir_path == want_mir,
          f"the cave mirror/assembler loaded is EXACTLY {want_mir}, not some other copy on sys.path "
          f"(got {mir_path})", "S")
    print(f"      mirror sha256[:16] = {hashlib.sha256(mir_path.read_bytes()).hexdigest()[:16]}")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    check(u16(base, FB_A_CELL) == FB_A_OLD and u16(base, FB_B_CELL) == FB_B_OLD
          and u16(base, R24_CELL) == R24_OLD,
          f"base cells: fb pole {FB_A_OLD}/{FB_B_OLD}, r24 arm {R24_OLD}", "V")
    check(u16(base, B3_INSN) == B3_HW1 and u16(base, B3_INSN + 2) == B3_HW2_OLD,
          f"base b3 rung 0x{B3_INSN:05X} = hw1 0x{B3_HW1:04X} / hw2 0x{B3_HW2_OLD:04X} "
          f"(ld.w -0x3680,gp,r6)", "V")
    check(bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK,
          f"🛑 the HOOK SITE 0x{HOOK:05X} is the stock `mul r16,r7,r0` ({HOOK_STOCK.hex()}) on V282 "
          f"-- nothing has ever been written here (memo sec.7 item 2)", "S")
    check(bytes(base[RETURN_TO:RETURN_TO + 2]) == RETURN_STOCK,
          f"the RETURN TARGET 0x{RETURN_TO:05X} is the stock `add r7,r9` ({RETURN_STOCK.hex()})", "S")
    ff = bytes(base[CAVE_FF_LO:CAVE_FF_HI])
    check(ff == b"\xff" * len(ff),
          f"🛑 the CAVE'S FLASH REGION 0x{CAVE_FF_LO:05X}-0x{CAVE_FF_HI - 1:05X} "
          f"({len(ff)} B = {CAVE_LEN} cave + {len(ff) - CAVE_LEN} margin) is VIRGIN 0xFF on V282 "
          f"-- the cave overwrites nothing (memo sec.7 item 3)", "S")
    gap = bytes(base[CAVE14A_END:0xC4FF0])
    check(gap == b"\xff" * len(gap),
          f"and the whole gap 0x{CAVE14A_END:05X}-0xC4FEF ({len(gap)} B) is 0xFF -- the 0x14A cave "
          f"ends at 0x{CAVE14A_END:05X} and V289's notch cave is ABSENT from this base", "S")
    sa, sb = STRUCT_12B
    check(bytes(base[sa:sa + len(sb)]) == sb,
          f"the pre-existing 12-byte structure at 0x{sa:05X} reads {sb.hex()} -- unidentified, and "
          f"V292 does not disturb it", "V")
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

    # ---------------------------------------------------------------------------------------------
    print("\n  [2] CELL IDENTITY -- every edited cal cell's reader decoded from the BASE image's OWN"
          " bytes\n      (all vacuous by construction: they read only `base`, which the sha256 pins)")
    for addr, want, cell, mnem, is_signed in (
            (FB_A_LOAD, FB_A_LOAD_BYTES, FB_A_CELL, "ld.h", True),
            (FB_B_LOAD, FB_B_LOAD_BYTES, FB_B_CELL, "ld.hu", False),
            (R24_LOAD, R24_LOAD_BYTES, R24_CELL, "ld.hu", False)):
        _n, mn, ops, f = decode_one(bytes(base), addr)
        print(f"      0x{addr:05X}  {bytes(base[addr:addr + 4]).hex()}  {mn:6s} {ops}")
        check(bytes(base[addr:addr + 4]) == want and mn == mnem and f["reg1"] == 5
              and TP_BASE + f["disp"] == cell,
              f"0x{addr:05X}: the INDEPENDENT DECODER reads `{mn} {ops}`, and tp 0x{TP_BASE:05X} "
              f"{f['disp']:+#x} == 0x{cell:05X} -- this reader reads THE CELL V292 CARRIES "
              f"({'SIGNED, cap 32767' if is_signed else 'UNSIGNED, cap 65535'}). No off-by-0x1000", "V")
    for addr, (cell, what) in sorted(R24_SIBLINGS.items()):
        _n, mn, ops, f = decode_one(bytes(base), addr)
        check(TP_BASE + f["disp"] == cell and f["reg1"] == 5,
              f"r24 gate arm 0x{addr:05X} `{mn} {ops}` -> 0x{cell:05X} = {u16(base, cell)} ({what})", "V")
    check(u16(base, 0xC6442) == 1024 and R24_NEW > 1024,
          f"the LATCH arm 0xC6442 (1024) is BELOW the engaged arm ({R24_NEW}), so on this V280+ image "
          f"a gp-0x671d latch COLLAPSES r24 to x{1024 / R24_NEW:.3f} -- the pre-existing inversion, "
          f"unchanged by V292.  Model r24 as BIMODAL", "V")

    # ---------------------------------------------------------------------------------------------
    print("\n  [3] THE INHERITED ARITHMETIC -- computed from the integers ACTUALLY WRITTEN")
    # 🛑 V292's CENTRAL PREMISE is "V291's dose, byte-identical".  A band check is NOT enough: the
    #    r24 value 4722 and the b value 957 both sit inside the k_gate / DC bands and would be a
    #    DIFFERENT BUILD under the V292 name.  These two assertions pin the exact integers, and [7]
    #    then pins all three at once against V291's independently recorded cal-block CRC.
    check((FB_A_NEW, FB_B_NEW, R24_NEW) == (962, 958, 4725),
          f"🛑 THE THREE CELLS ARE V291 C10's EXACT INTEGERS: a = {FB_A_NEW} (962), b = {FB_B_NEW} "
          f"(958), r24 = {R24_NEW} (4725).  V292 changes the ARITHMETIC, not the dose -- a different "
          f"integer here would be a different build, not a V292", "S")
    check(0 < FB_A_NEW <= 1023,
          f"a = {FB_A_NEW} is strictly < 1024: the pole a/1024 = {FB_A_NEW / 1024:.6f} < 1, a decaying "
          f"lag, not an integrator (1024) or a divergence (> 1024)", "S")
    check(FB_A_NEW <= 32767, f"a = {FB_A_NEW} <= 32767: read with ld.h (SIGNED) at 0x{FB_A_LOAD:05X}", "S")
    check(0 < FB_B_NEW <= 65535, f"b = {FB_B_NEW} in [1,65535]: ld.hu (UNSIGNED) at 0x{FB_B_LOAD:05X}", "S")
    dc_new, dc_old = dc_gain(FB_A_NEW, FB_B_NEW), dc_gain(FB_A_OLD, FB_B_OLD)
    check(abs(dc_new / DC_TARGET - 1) <= DC_TOL,
          f"realised DC 2b/(1024-a) = {dc_new:.6f} is {100 * (dc_new / DC_TARGET - 1):+.4f} % of "
          f"V282's {DC_TARGET:.6f} -- inside {100 * DC_TOL:.1f} %, so STEADY-STATE FEEDBACK GAIN and "
          f"therefore steady-state authority are UNCHANGED", "S")
    f_old, f_new = corner_hz(FB_A_OLD), corner_hz(FB_A_NEW)
    check(f_new < f_old,
          f"the pole is DOWN: {f_old:.4f} -> {f_new:.4f} Hz, a x{f_old / f_new:.2f} OPENING of the "
          f"loop at high frequency (V289 moved this same cell UP to 25 Hz)", "S")
    k_real = R24_NEW / R24_OLD
    check(k_real <= K_GATE and abs(k_real / K_GATE - 1) < 0.001,
          f"r24 ROUNDING DIRECTION: realised k = {R24_NEW}/{R24_OLD} = {k_real:.6f} is AT OR BELOW the "
          f"memo's k_gate {K_GATE:.4f} ({100 * (k_real / K_GATE - 1):+.4f} %) -- rounding UP would "
          f"land on the WRONG SIDE of the 7.3 Hz gate", "S")
    check(512 < R24_NEW < R24_OLD,
          f"the r24 dose is a PARTIAL REVERT toward stock: 512 < {R24_NEW} < {R24_OLD}", "S")
    # overflow with the error feedback added -- memo sec.5.2 and sec.7 item 14
    s_ss = FB_B_NEW * FB_X_SAT / (1024 - FB_A_NEW)
    bound_a = FB_A_NEW * s_ss + 1023
    bound_b = FB_B_NEW * FB_X_SAT + 1023
    check(bound_a < 2 ** 31 and bound_b < 2 ** 31,
          f"int32 headroom WITH the remainder added: a*s+rem = {bound_a:.3e} (x{2 ** 31 / bound_a:.2f}), "
          f"b*x+rem = {bound_b:.3e} (x{2 ** 31 / bound_b:.1f}) -- the error feedback adds "
          f"{100 * 1023 / (FB_A_NEW * s_ss):.5f} % to the binding bound", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [4] THE CAVE -- assembled, then checked THREE independent ways")
    hook_b, cave_b, listing = MIR.build_cave(cave=CAVE, hook=HOOK, ret=RETURN_TO,
                                             rb=REM_B_DISP, ra=REM_A_DISP)
    check(len(cave_b) == CAVE_LEN and len(hook_b) == 4,
          f"the assembled cave is {len(cave_b)} bytes / {len(listing)} instructions and the hook is "
          f"{len(hook_b)} bytes -- exactly the size the flash margin was checked for", "S")
    print("      (a) ENCODER POSITIVE CONTROLS -- every cave FORM re-encoded against a STOCK instance")
    for addr, wantbytes, text, why in ENC_CONTROLS:
        got = bytes(base[addr:addr + len(bytes.fromhex(wantbytes))])
        _n, mn, ops, _f = decode_one(bytes(base), addr)
        check(addr >= START and got.hex() == wantbytes
              and "".join(f"{mn} {ops}".split()) == "".join(text.split()),
              f"control 0x{addr:05X} {wantbytes} decodes to `{mn} {ops}` == `{text}`  -- {why}", "V")
    print("      (b) WHOLE-WINDOW re-encode: the 38 stock bytes 0x28F86-0x28FAB from our own encoder")
    win = bytes(base[STOCK_WIN_LO:STOCK_WIN_HI])
    reenc = (MIR.i_ld_hu(0x73EA, MIR.TPr, MIR.R16)
             + MIR.i_f67("ld.h", MIR.TPr, MIR.R9, 0x73E8)
             + MIR.i_mul(MIR.R16, MIR.R7) + MIR.i_mul(MIR.R26, MIR.R9)
             + MIR.i_ld_hu(0x72E6, MIR.TPr, MIR.R13) + MIR.i_f2("sar", 10, MIR.R7)
             + MIR.i_ld_hu(0x72E6, MIR.TPr, MIR.R14) + MIR.i_f2("sar", 10, MIR.R9)
             + MIR.i_f1("add", MIR.R7, MIR.R9) + MIR.i_f1("add", MIR.R9, MIR.R26)
             + MIR.i_f1("cmp", MIR.R13, MIR.R26)
             + MIR.i_f67("st.h", MIR.GPr, MIR.R9, (S_DISP & 0xFFFF) | 1))
    check(reenc == win,
          f"🛑 THE ENCODER'S OWN POSITIVE CONTROL: our encoder re-creates the 38 stock bytes "
          f"0x{STOCK_WIN_LO:05X}-0x{STOCK_WIN_HI - 1:05X} BYTE-IDENTICALLY ({win.hex()}) -- without "
          f"this a mis-encoded cave byte could pass silently (memo sec.7 item 4)", "S")
    print("      (c) the memo sec.5 LISTING, address by address")
    for (pc, by, mn, cm), (m_pc, m_hex, m_txt) in zip(listing, MEMO_CAVE):
        check(pc == m_pc and by.hex() == m_hex,
              f"0x{pc:05X}  {by.hex():8s}  {mn:22s} == memo `{m_txt}`", "S")
    check(hook_b.hex() == MEMO_HOOK,
          f"HOOK 0x{HOOK:05X}: {hook_b.hex()} == memo `jr 0x{CAVE:05X}` ({MEMO_HOOK})", "S")
    print(f"      cave sha256[:16] = {hashlib.sha256(cave_b).hexdigest()[:16]}   "
          f"occupies 0x{CAVE:05X}-0x{CAVE + CAVE_LEN - 1:05X}")

    # ---------------------------------------------------------------------------------------------
    print("\n  [5] APPLY")
    code = bytearray(base)
    attributed = set()
    for addr, old, new, what in ((FB_A_CELL, FB_A_OLD, FB_A_NEW, "fb pole a"),
                                 (FB_B_CELL, FB_B_OLD, FB_B_NEW, "fb pole b"),
                                 (R24_CELL, R24_OLD, R24_NEW, "r24 engaged arm")):
        check(u16(code, addr) == old, f"pre-write 0x{addr:05X} == {old}", "T")
        struct.pack_into("<H", code, addr, new)
        check(u16(code, addr) == new, f"0x{addr:05X} {what}: {old} -> {new}", "T")
        attributed |= {addr, addr + 1}
    check(u16(code, B3_INSN + 2) == B3_HW2_OLD, f"pre-write b3 hw2 == 0x{B3_HW2_OLD:04X}", "T")
    struct.pack_into("<H", code, B3_INSN + 2, B3_HW2_NEW)
    attributed |= {B3_INSN + 2, B3_INSN + 3}
    _n, mn, ops, f = decode_one(bytes(code), B3_INSN)
    check(mn == "ld.w" and f["reg1"] == 4 and f["reg2"] == 6 and f["disp"] == S_DISP
          and u16(code, B3_INSN) == B3_HW1,
          f"b3 rung repointed: the INDEPENDENT DECODER reads `{mn} {ops}` -- hw1 UNCHANGED "
          f"(0x{B3_HW1:04X}: same opcode, base register and destination), only the displacement moved, "
          f"and the target gp{S_DISP:+#x} = 0x{GP_BASE + S_DISP:08X} is 4-BYTE ALIGNED so the load "
          f"cannot tear against the filter's own st.w at 0x28FA8", "S")
    check(bytes(code[HOOK:HOOK + 4]) == HOOK_STOCK, f"pre-write hook == {HOOK_STOCK.hex()}", "T")
    code[HOOK:HOOK + 4] = hook_b
    attributed |= set(range(HOOK, HOOK + 4))
    check(bytes(code[CAVE:CAVE + CAVE_LEN]) == b"\xff" * CAVE_LEN, "pre-write cave == 0xFF", "T")
    code[CAVE:CAVE + CAVE_LEN] = cave_b
    attributed |= set(range(CAVE, CAVE + CAVE_LEN))
    print(f"      {len(attributed)} payload bytes written: 7 V291 cal/displacement + 4 hook + "
          f"{CAVE_LEN} cave")

    # ---------------------------------------------------------------------------------------------
    print("\n  [6] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    print("      🛑 The FIRST assertion below is FULL-COVERAGE over [0x13000,0x100000).  Every named")
    print("         byte-identity check that follows is ENTAILED BY IT and is marked [V] accordingly.")
    outside = [x for x in range(START, END) if x not in attributed and code[x] != base[x]]
    check(outside == [],
          f"NO byte in [0x{START:05X},0x{END:05X}) outside the {len(attributed)} attributed payload "
          f"bytes differs from V282 before the CRC recompute ({len(outside)} stray diffs)", "S")
    for a, v in FROZEN.items():
        check(u16(code, a) == u16(base, a) == v, f"0x{a:05X} == base == {v}   [entailed by the above]", "V")
    for a, v in EME_FLOATS.items():
        check(bytes(code[a:a + 4]) == bytes(base[a:a + 4]),
              f"EME float mirror 0x{a:05X} == {v} (int/float lockstep)   [entailed]", "V")
    for addr, want in ((FB_A_LOAD, FB_A_LOAD_BYTES), (FB_B_LOAD, FB_B_LOAD_BYTES),
                       (R24_LOAD, R24_LOAD_BYTES)):
        check(bytes(code[addr:addr + 4]) == want,
              f"cal reader 0x{addr:05X} byte-identical ({want.hex()}) -- CAL ONLY on those three "
              f"cells, no code byte   [entailed]", "V")
    for addr in sorted(R24_SIBLINGS):
        check(bytes(code[addr:addr + 4]) == bytes(base[addr:addr + 4]),
              f"r24 sibling arm reader 0x{addr:05X} byte-identical   [entailed]", "V")
    cave14a_diff = [x for x in range(CAVE14A_START, CAVE14A_END) if code[x] != base[x]]
    check(cave14a_diff == [B3_INSN + 2, B3_INSN + 3],
          f"the 0x14A telemetry cave 0x{CAVE14A_START:05X}-0x{CAVE14A_END - 1:05X} differs in EXACTLY "
          f"the b3 displacement {[hex(x) for x in cave14a_diff]} -- b4/b5/b6/b7 and the epilogue keep "
          f"V282's meaning, the r24 comparator instrument included", "S")
    for addr, (h1, h2) in sorted(CAVE14A_OTHER_LOADS.items()):
        check((u16(code, addr), u16(code, addr + 2)) == (h1, h2),
              f"0x14A cave load 0x{addr:05X} == hw1 0x{h1:04X} / hw2 0x{h2:04X}   [entailed]", "V")
    check(u16(code, B3_MASK_SITE) == B3_MASK and (B3_MASK & STOCK_B4_BITS) == STOCK_B4_BITS,
          f"the rung's andi mask 0x{B3_MASK_SITE:05X} = 0x{B3_MASK:04X} PRESERVES Honda's bits 2-0 "
          f"(0x{STOCK_B4_BITS:02X})   [entailed]", "V")
    check(bytes(code[CAVE14A_HOOK:CAVE14A_HOOK + 4]) == CAVE14A_HOOK4,
          "0x14A cave hook 0x55C0E byte-identical   [entailed]", "V")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          f"427 torque tap 0x{PACK_LO:05X}-0x{PACK_HI - 1:05X} byte-identical   [entailed]", "V")
    _fa, _fb = FWD_GAIN_REPOINT
    check(bytes(code[_fa:_fa + 2]) == _fb,
          f"0x{_fa:05X} still carries the V57/V81 forward-gain repoint   [entailed]", "V")
    map_ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]) for p in map_ptrs),
          f"all {len(map_ptrs)} assist-map records byte-identical   [entailed]", "V")
    kpkd_ok = True
    for ptr in (KP_PTR, KD_PTR):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = u16(base, p)
            kpkd_ok &= bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n])
    check(kpkd_ok, f"all {2 * N_SLOTS} Kp/Kd slot records byte-identical   [entailed]", "V")
    tps = sorted({u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)})
    check(all(bytes(code[p:p + 2 + 4 * s16(base, p)]) == bytes(base[p:p + 2 + 4 * s16(base, p)])
              for p in tps), f"all {len(tps)} override-taper records byte-identical   [entailed]", "V")
    ctrl = [x for x in range(START, 0xC0000) if x not in attributed and code[x] != base[x]]
    check(ctrl == [],
          f"the code region [0x{START:05X},0xC0000) differs ONLY at the hook and the cave   [entailed]", "V")

    # ---------------------------------------------------------------------------------------------
    print("\n  [7] CRC TRAILERS -- blocks located GENERICALLY by walking the chain from the image")
    owners = {}
    for a in sorted(attributed):
        owners.setdefault(tuple(V53.owning_block(code, a)), []).append(a)
    blocks = sorted(owners)
    check(len(blocks) == 2, f"exactly 2 CRC blocks own the payload: "
                            f"{[(hex(s), hex(e)) for s, e in blocks]}", "S")
    cal_bytes = {FB_A_CELL, FB_A_CELL + 1, FB_B_CELL, FB_B_CELL + 1, R24_CELL, R24_CELL + 1}
    code_bytes = set(attributed) - cal_bytes
    for b0, b1 in blocks:
        own = set(owners[(b0, b1)])
        if b1 == 0xC6FFC:
            check(own == cal_bytes,
                  f"block [0x{b0:05X},0x{b1:05X}) owns EXACTLY the 6 cal bytes "
                  f"{sorted(hex(x) for x in own)} -- 0xC6FFC therefore moves ONLY because of the "
                  f"three cal cells", "S")
        elif b1 == 0xC4FFC:
            check(own == code_bytes and len(own) == 4 + CAVE_LEN + 2,
                  f"block [0x{b0:05X},0x{b1:05X}) owns EXACTLY the b3 displacement (2) + the hook (4) "
                  f"+ the cave ({CAVE_LEN}) = {len(own)} bytes -- 0xC4FFC therefore moves because of "
                  f"the rung, the hook and the cave, and the chain makes this ONE block [0x13000,"
                  f"0x{b1:05X}) spanning both", "S")
        else:
            check(False, f"UNEXPECTED CRC block trailer 0x{b1:05X}", "S")
        check(not any(b1 <= a < b1 + 4 for a in attributed), f"no edit lands on the trailer 0x{b1:06X}", "S")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved", "S")
        if b1 == 0xC6FFC:
            check(newc == V291_CAL_CRC,
                  f"🛑 THE CAL-BLOCK CRC COMES OUT 0x{newc:08X} == V291's OWN 0x{V291_CAL_CRC:08X} "
                  f"(design memo sec.4.3, recorded BEFORE this script existed).  One 32-bit number "
                  f"pins ALL THREE cal halfwords simultaneously against an independent record: a "
                  f"single wrong cal byte anywhere in [0xC6000,0xC6FFC) changes it.  This is the "
                  f"assertion that makes 'V291's dose, byte-identical' checkable rather than claimed", "S")
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      page [0x{b0:06X},0x{b1:06X})  trailer 0x{b1:06X}  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [8] FULL BYTE DIFF vs V282 -- every differing offset enumerated and COUNTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(set(diff) <= attributed, f"all {len(diff)} differing bytes are attributed payload or CRC", "S")
    v291_payload = 0
    for addr, old, new in ((FB_A_CELL, FB_A_OLD, FB_A_NEW), (FB_B_CELL, FB_B_OLD, FB_B_NEW),
                           (R24_CELL, R24_OLD, R24_NEW), (B3_INSN + 2, B3_HW2_OLD, B3_HW2_NEW)):
        v291_payload += sum(1 for j in (0, 1)
                            if struct.pack("<H", old)[j] != struct.pack("<H", new)[j])
    # 🛑 Two cave bytes are themselves 0xFF -- the low half of each `andi 0x3ff` imm16, at 0xC4C10 and
    #    0xC4C20 -- so they COINCIDE with the erased flash and do not appear as differing bytes.  The
    #    WRITTEN EXTENT is still 4 + 52; the DIFF COUNT is 2 lower, and that is computed here rather
    #    than assumed, so a genuinely missing cave byte cannot hide behind the discrepancy.
    cave_ff = [CAVE + i for i in range(CAVE_LEN) if cave_b[i] == 0xFF]
    hook_same = [HOOK + i for i in range(4) if hook_b[i] == HOOK_STOCK[i]]
    expected = v291_payload + (4 - len(hook_same)) + (CAVE_LEN - len(cave_ff)) + 8
    check(len(diff) == expected and v291_payload == 7 and cave_ff == [0xC4C10, 0xC4C20]
          and hook_same == [],
          f"total diff vs V282 = {v291_payload} V291 payload + {4 - len(hook_same)} hook + "
          f"{CAVE_LEN - len(cave_ff)} cave ({CAVE_LEN} written, {len(cave_ff)} of them 0xFF at "
          f"{[hex(a) for a in cave_ff]} = the low byte of each `andi 0x3ff` imm16, so they coincide "
          f"with erased flash) + 8 CRC = {expected}, got {len(diff)}.  Every term is COMPUTED from "
          f"the bytes, none asserted; 7 payload + 8 CRC = 15 is exactly V291's own full-range diff", "S")
    check(set(range(CAVE, CAVE + CAVE_LEN)) <= attributed
          and set(range(HOOK, HOOK + 4)) <= attributed,
          f"and the WRITTEN EXTENT is the full {CAVE_LEN}-byte cave plus the 4-byte hook regardless "
          f"of which bytes happened to coincide -- [9] decodes all {CAVE_LEN} back", "S")
    names = {FB_A_CELL: (2, "fb pole a   0xC63E8 [V291]"), FB_B_CELL: (2, "fb pole b   0xC63EA [V291]"),
             R24_CELL: (2, "r24 arm     0xC6446 [V291]"), B3_INSN + 2: (2, "b3 disp     0xC4BAA [V291]"),
             HOOK: (4, "HOOK jr cave 0x28F8E [V292]"), CAVE: (CAVE_LEN, "THE CAVE     0xC4C00 [V292]")}
    print("      offset               len  what                             base -> built")
    for s, e in runs(diff):
        lbl = next((v for k, (n, v) in names.items() if k <= s < k + n), None) \
            or ("CRC trailer 0x%06X" % s if s in {b1 for _b0, b1 in blocks} else "?")
        shown = (bytes(base[s:e]).hex(), bytes(code[s:e]).hex()) if e - s <= 8 else \
            (f"{bytes(base[s:s + 4]).hex()}..({e - s} B)", f"{bytes(code[s:s + 4]).hex()}..({e - s} B)")
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:2d} B)  {lbl:31s}  {shown[0]} -> {shown[1]}")

    # ---------------------------------------------------------------------------------------------
    print("\n  [9] THE BUILT CAVE, DISASSEMBLED BACK BY THE INDEPENDENT DECODER (memo sec.7 item 12)")
    print("      Decoded from the image bytes by field layout, NOT by inverting the encoder.")
    dec = decode_range(bytes(code), CAVE, CAVE + CAVE_LEN)
    check(len(dec) == 15, f"the built cave decodes to exactly 15 instructions (got {len(dec)})", "S")
    for (pc, by, mn, ops, f), (m_pc, m_hex, m_txt) in zip(dec, MEMO_CAVE):
        norm = f"{mn} {ops}".replace(" ", "").replace("0x3ff", "0x3ff")
        want = m_txt.replace(" ", "")
        print(f"      0x{pc:05X}  {by.hex():8s}  {mn:6s} {ops}")
        check(pc == m_pc and by.hex() == m_hex and norm == want,
              f"0x{pc:05X} decodes to `{mn} {ops}` == the memo's `{m_txt}`", "S")
    _n, hmn, hops, hf = decode_one(bytes(code), HOOK)
    check(hmn == "jr" and hf["target"] == CAVE,
          f"the HOOK decodes to `{hmn} {hops}` -- target 0x{hf['target']:05X} == the cave, disp22 "
          f"{hf['disp']:+#x}, and it is a `jr` NOT a `jarl`, so `lp` is untouched", "S")
    last = dec[-1]
    check(last[2] == "jr" and last[4]["target"] == RETURN_TO,
          f"the cave's last instruction decodes to `jr 0x{last[4]['target']:05X}` == 0x{RETURN_TO:05X}, "
          f"the instruction IMMEDIATELY AFTER the displaced span -- not a stub, not a fallthrough", "S")
    _n2, rmn, rops, rf = decode_one(bytes(code), RETURN_TO)
    check(rmn == "add" and rf["reg1"] == 7 and rf["reg2"] == 9,
          f"and the return target 0x{RETURN_TO:05X} decodes to `{rmn} {rops}` = Honda's own "
          f"`add r7,r9` -- s_new = step_a + step_b, unmodified", "S")
    repl = {(mn, ops) for _p, _b, mn, ops, _f in dec}
    for a in (0x28F8E, 0x28F92, 0x28F96, 0x28F9A, 0x28F9C, 0x28FA0):
        _n3, dmn, dops, _df = decode_one(bytes(base), a)
        check((dmn, dops) in repl,
              f"displaced instruction 0x{a:05X} `{dmn} {dops}` IS replicated inside the cave", "S")
    check(all(mn != "jarl" for _p, _b, mn, _o, _f in dec) and
          sum(1 for _p, _b, mn, _o, _f in dec if mn == "jr") == 1,
          "the cave contains exactly ONE branch (the return `jr`) and NO `jarl` -- no call, no `lp` "
          "clobber, no nested control flow", "S")
    wrote = {f["reg2"] for _p, _b, mn, _o, f in dec if mn in ("mul", "add", "sar", "andi", "ld.hu")}
    check(wrote <= {7, 9, 13, 14},
          f"the cave's ENTIRE register write set is {sorted(wrote)} ⊆ {{7,9,13,14}} -- exactly the four "
          f"registers the displaced span unconditionally WRITES BEFORE READING, so they are dead at "
          f"the hook by the original code's own structure.  r1/r2/r6/r10/r25/r26/lp untouched", "S")
    restored = [(pc, ops) for pc, _b, mn, ops, f in dec if mn == "ld.hu" and f["reg1"] == 5]
    check(len(restored) == 2 and {r[1].split(",")[-1] for r in restored} == {"r13", "r14"},
          f"and r13/r14 are RESTORED to their intended clamp values by the two replicated tp loads at "
          f"{[hex(r[0]) for r in restored]} before the return", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [10] BEHAVIOURAL PROOFS -- driven by EMULATING THE BUILT BYTES (memo sec.7 item 13)")
    from fractions import Fraction
    clamp_img = u16(code, FB_CLAMP_CELL)
    check(clamp_img == FB_CLAMP, f"the output clamp cell 0x{FB_CLAMP_CELL:05X} reads {clamp_img} from "
                                 f"the built image -- the VM uses the IMAGE's value, not a constant", "S")
    vm = CaveVM(bytes(code))
    # (0) the VM is the bytes; the mirror is the model.  Bridge them on a heavy mixed trace.
    import random
    rng = random.Random(292)
    trace = ([0] * 40 + [1, -1, 2, -2, 3, -3, 5, -5] * 40
             + [rng.randint(-FB_X_SAT, FB_X_SAT) for _ in range(4000)]
             + [rng.choice([-1, 0, 1]) for _ in range(4000)]
             + [FB_X_SAT, -FB_X_SAT] * 200)
    s_vm, rb_vm, ra_vm = 0, 0, 0
    s_md, rb_md, ra_md = 0, 0, 0
    vm.ram.clear()
    agree = True
    for x in trace:
        o1, s_vm, rb_vm, ra_vm = vm.tick(x, s_vm, FB_A_NEW, FB_B_NEW, clamp_img)
        o2, s_md, rb_md, ra_md = MIR.fb_lag_v292(x, s_md, rb_md, ra_md, FB_A_NEW, FB_B_NEW, FB_CLAMP)
        agree &= (o1, s_vm, rb_vm, ra_vm) == (o2, s_md, rb_md, ra_md)
        if not agree:
            break
    check(agree,
          f"🛑 BYTES == MODEL: the emulated cave and the mirror's `fb_lag_v292` agree on (out, s, "
          f"rem_b, rem_a) for ALL {len(trace)} ticks of a mixed trace (zeros, +-1..5, {4000} uniform "
          f"random over the full +-{FB_X_SAT} range, {4000} near-zero, and the saturation square "
          f"wave).  Every model-driven row below inherits this bridge", "S")
    # (i) MEAN GAIN EXACT -- from the emulated bytes
    dc_exact = Fraction(2 * FB_B_NEW, 1024 - FB_A_NEW)
    x_rail = int(clamp_img * (1024 - FB_A_NEW) / (2 * FB_B_NEW))
    check(x_rail == 1491,
          f"the +-{clamp_img} OUTPUT clamp (pre-existing, untouched) binds for |x| >= "
          f"C(1024-a)/2b = {x_rail} counts = {x_rail / 8:.1f} deg/s -- above that V291 and V292 sit "
          f"on the same rail, so the exactness claim is made BELOW it and the boundary is named", "S")
    amps = sorted(set(list(range(1, 65)) + [100, 333, 1000, 1491]
                      + [-v for v in list(range(1, 65)) + [100, 333, 1000, 1491]]))
    if FULL:
        amps = sorted(set(list(range(1, x_rail + 1)) + [-v for v in range(1, x_rail + 1)]))
    worst, wx = Fraction(0), None
    for x in amps:
        m, _p = vm_mean_over_cycle(vm, FB_A_NEW, FB_B_NEW, clamp_img, x)
        d = abs(m / x - dc_exact)
        if d > worst:
            worst, wx = d, x
    check(worst == 0,
          f"(i) MEAN GAIN IS EXACTLY 2b/(1024-a) = {dc_exact} = {float(dc_exact):.9f} on ALL "
          f"{len(amps)} amplitudes {'(EXHAUSTIVE x = -%d..-1, 1..%d, both signs)' % (x_rail, x_rail) if FULL else '(|x| = 1..64 both signs, plus 100/333/1000/1491 both signs)'}"
          f" -- max |mean/x - DC| = {worst}.  Driven through THE EMULATED CAVE BYTES", "S")
    if not FULL:
        worst_m, _ = Fraction(0), None
        for x in list(range(1, x_rail + 1)) + list(range(-x_rail, 0)):
            m, _p, _k = MIR.mean_over_cycle(FB_A_NEW, FB_B_NEW, x, ef=True)
            worst_m = max(worst_m, abs(m / x - dc_exact))
        check(worst_m == 0,
              f"(i-exh) and the EXHAUSTIVE sweep x = -{x_rail}..-1 and 1..{x_rail} ({2 * x_rail} "
              f"amplitudes, both signs) is exact through the MIRROR MODEL, which the bytes==model "
              f"bridge above licenses.  Run with --full to drive all {2 * x_rail} through the bytes", "S")
    # the absorbing state, from the bytes
    vm.ram.clear()
    s_ = -1
    for _ in range(200):
        _o, s_, _rb, _ra = vm.tick(0, s_, FB_A_NEW, FB_B_NEW, clamp_img)
    vm.ram.clear()
    s2 = -500
    k = 0
    while s2 != 0 and k < 100000:
        _o, s2, _rb, _ra = vm.tick(0, s2, FB_A_NEW, FB_B_NEW, clamp_img)
        k += 1
    f291 = MIR.FbLag(FB_A_NEW, FB_B_NEW, ef=False, s=-1)
    for _ in range(200):
        f291.tick(0)
    check(s_ == 0 and s2 == 0 and f291.s == -1,
          f"⭐ THE s = -1 ABSORBING STATE IS RELEASED: from the BYTES, s0 = -1 with x = 0 rests at "
          f"s = {s_} after 200 ticks and s0 = -500 reaches EXACTLY 0 in {k} ticks; V291 rests at "
          f"s = {f291.s} FOREVER.  This is the free 0x14A b3 positive control -- bit-3 duty at rest "
          f"goes 0.52-1.00 -> 0.000", "S")
    # (iii) describing function at 20.3 Hz -- the prereg A3 clause
    print("       (iii) describing-function gain at 20.3 Hz vs the linear model (tolerance +-0.03):")
    worst_df = 0.0
    for A in (1, 2, 3, 5, 8, 16, 24):
        g, ph = MIR.describing_fn(FB_A_NEW, FB_B_NEW, 20.3, A, ef=True)
        g0, ph0 = MIR.describing_fn(FB_A_NEW, FB_B_NEW, 20.3, A, ef=False)
        worst_df = max(worst_df, abs(g - 1.0))
        print(f"          A = {A:3d} cnts   V292 {g:.4f} ({ph:+.2f} deg)      V291 {g0:.4f} ({ph0:+.2f} deg)")
    check(worst_df <= 0.03,
          f"(iii) worst |gain - 1.00| over A in {{1,2,3,5,8,16,24}} is {worst_df:.4f} <= 0.03 -- the "
          f"prereg A3 clause.  V291 ranges 0.07-1.01 with up to +60 deg of AMPLITUDE-DEPENDENT PHASE "
          f"error at A = 1", "S")
    # (iv) byte-exact closed-loop steady state -- the B4 clause
    print("       (iv) byte-exact closed-loop steady state, family median fit, 12000 ticks:")
    try:
        import json
        import design290b_candidates as D
        _c289, c282 = D.cells()
        # 🛑 PROVENANCE.  `design290b_candidates.cells()` reads its controller cells out of the V289
        #    image and then overrides fb_a/fb_b.  Nothing in the mirror checks that those cells match
        #    the image V292 is actually built from -- so the B4 proof would silently be about a
        #    DIFFERENT controller if they ever diverged.  Checked here, from the built image's bytes.
        ga = TP_BASE + u16(code, 0x2A1F0)
        want_cells = {"lag_a": s16(code, 0xC63EC), "lag_b": u16(code, 0xC63EE),
                      "gain_addr": ga, "gain": s16(code, ga),
                      "p_clamp": u16(code, 0xC61BC), "d_clamp": u16(code, 0xC61B6),
                      "sum_clamp": u16(code, 0xC61BE), "t_clamp": u16(code, 0xC61B4),
                      "fb_clamp": u16(code, FB_CLAMP_CELL), "deadband": u16(code, 0xC61B8),
                      "kp_Y": [u16(code, u32(code, KP_PTR + 4 * LIVE_SLOT) + 12 + 2 * i) for i in range(5)],
                      "kd_Y": [u16(code, u32(code, KD_PTR + 4 * LIVE_SLOT) + 10 + 2 * i) for i in range(4)]}
        bad = []
        for k, v in sorted(want_cells.items()):
            got = c282[k]
            same = (list(got) == list(v)) if isinstance(v, list) else (got == v)
            if not same:
                bad.append(f"{k}: proof {got!r} vs image {v!r}")
        check(not bad,
              f"🛑 CLOSED-LOOP CELL PROVENANCE: all {len(want_cells)} controller cells the B4 proof "
              f"uses (lag pole, gain, the four clamps, deadband, Kp, Kd) are read from "
              f"`{os.path.basename(_c289['path'])[:40]}...` and are BYTE-EQUAL to the V292 image's own "
              f"({want_cells['lag_a']}/{want_cells['lag_b']} lag, gain {want_cells['gain']} @"
              f"0x{ga:05X}, clamps {want_cells['p_clamp']}/{want_cells['d_clamp']}/"
              f"{want_cells['sum_clamp']}/{want_cells['t_clamp']}/{want_cells['fb_clamp']}, Kp "
              f"{want_cells['kp_Y'][0]}, Kd {want_cells['kd_Y'][0]}).  Mismatches: {bad}.  Only "
              f"fb_a/fb_b are set by the proof itself.  Without this the B4 number could silently "
              f"describe a different controller", "S")
        fam = json.load(open(os.path.join(MIR.SCR, "design290b_family.json")))
        stab = [p for p in fam if p["z289"] >= D.Z289_STABLE]
        med = sorted(stab, key=lambda p: p["g0"])[len(stab) // 2]
        pl = D.mkplant(med)
        print(f"          median of {len(stab)} stable fits: fp {med['fp']:.2f} zp {med['zp']:.4f} "
              f"tau {1e3 * med['tau']:.0f} ms f1 {med['f1']:.1f} g0 {med['g0']:.4f}")
        print(f"          {'sp':>5} | {'V282 lin ref':>13} | {'V291 = C10':>11} | {'V292':>11} | "
              f"{'V282+cave':>11} | {'V291/ref':>9} | {'V292/ref':>9}")
        rows = {}
        for sp in (3, 33, 330):
            ss282, pk282 = MIR.closed_loop_ss(c282, pl, False, MIR.V282_A, MIR.V282_B, sp, 12000, 2000)
            ss291, pk291 = MIR.closed_loop_ss(c282, pl, False, FB_A_NEW, FB_B_NEW, sp, 12000, 2000)
            ss292, pk292 = MIR.closed_loop_ss(c282, pl, True, FB_A_NEW, FB_B_NEW, sp, 12000, 2000)
            ssctl, _ = MIR.closed_loop_ss(c282, pl, True, MIR.V282_A, MIR.V282_B, sp, 12000, 2000)
            rows[sp] = (ss282, ss291, ss292, ssctl, pk282, pk291, pk292)
            print(f"          {sp:5d} | {ss282:13.5f} | {ss291:11.5f} | {ss292:11.5f} | {ssctl:11.5f} "
                  f"| {ss291 / ss282:9.4f} | {ss292 / ss282:9.4f}")
        r3 = rows[3][2] / rows[3][0]
        check(abs(r3 - 1.0) <= 0.01,
              f"🛑 (iv) B4 AT ITS OWN OPERATING POINT: sp = 3 gives V292/V282 = x{r3:.5f}, inside "
              f"x1.00 +- 1 %.  V291 reads x{rows[3][1] / rows[3][0]:.4f} -- squarely inside the "
              f"adversary's x1.34-1.80 band.  THE CLAUSE V291 FAILED IS CLOSED", "S")
        r33, r330 = rows[33][2] / rows[33][0], rows[330][2] / rows[330][0]
        c33 = rows[33][3] / rows[33][0]
        check(abs(r330 - 1.0) <= 0.01, f"(iv) sp = 330 gives x{r330:.4f}, inside +-1 %", "S")
        print(f"          🛑 REPORTED AS A MISS, NOT ROUNDED AWAY: sp = 33 gives x{r33:.4f}, "
              f"{100 * (1 - r33):.2f} % low, OUTSIDE +-1 %.")
        print(f"             The control column says why: V282's OWN cal pair with the SAME cave lands "
              f"at x{c33:.4f}, i.e. V282's")
        print(f"             integer reference is itself inflated {100 * (1 - c33):.1f} % by ITS floor "
              f"bias.  V292 is within {100 * abs(r33 - c33):.2f} % of V282-corrected.")
        print(f"             The prereg's B4 amendment (2026-09-13) names the LINEAR surface as the "
              f"reference and predicts exactly this.")
        print(f"          peak wheel rate (transient authority):")
        for sp in (3, 33, 330):
            _a, _b2, _c2, _d2, p282, p291, p292 = rows[sp]
            print(f"             sp {sp:3d}: V282 {p282:8.4f} | V291 {p291:8.4f} (x{p291 / p282:.3f}) "
                  f"| V292 {p292:8.4f} (x{p292 / p282:.3f})")
        check(rows[3][6] / rows[3][4] <= 1.205,
              f"(iv) byte-exact capped-step overshoot at sp = 3 is x{rows[3][6] / rows[3][4]:.3f} of "
              f"V282's, inside the prereg's 1.205 ceiling (V291: x{rows[3][5] / rows[3][4]:.3f})", "S")
    except Exception as e:
        check(False, f"(iv) closed-loop proof UNAVAILABLE: {type(e).__name__}: {e}", "S")
    # (v) deviation from the exact linear filter
    print("       (v) deviation from the EXACT LINEAR filter, 20.3 Hz sine, 20000 scored ticks:")
    import numpy as np
    worst_mean = 0.0
    for A in (1, 3, 8, 64, 512):
        w = 2 * np.pi * 20.3 * TICK_S
        vm.ram.clear()
        s_i, sl = 0, 0.0
        devs = []
        for kk in range(30000):
            xk = int(round(A * np.sin(w * kk)))
            oi, s_i, _rb, _ra = vm.tick(xk, s_i, FB_A_NEW, FB_B_NEW, clamp_img)
            snl = (FB_A_NEW * sl + FB_B_NEW * xk) / 1024.0
            ol = sl + snl
            sl = snl
            if kk >= 10000:
                devs.append(oi - ol)
        d = np.array(devs)
        worst_mean = max(worst_mean, abs(float(d.mean())))
        print(f"          A = {A:3d}  mean {d.mean():+.4f}  rms {float(np.sqrt((d ** 2).mean())):.4f}  "
              f"max |dev| {float(np.abs(d).max()):.2f}")
    check(worst_mean < 0.01,
          f"(v) the EMULATED BYTES deviate from the exact linear filter by a ZERO-MEAN dither at every "
          f"amplitude (worst |mean| = {worst_mean:.4f} counts, peak <= 2).  V291 carries a CONSTANT "
          f"-32-count offset = +32 counts of PHANTOM ERROR against E = 32*sp - fb", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [11] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V292 output")
    back = bytearray(base)
    back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(back) == bytes(code),
          "the decoded .rwd is BYTE-IDENTICAL to the built image -- this single assertion entails "
          "every per-cell readback of the decoded image, so none is repeated below", "S")
    check(walk_all_blocks(bytes(back)) == 0 and walk(bytes(back)) == 0,
          "readback CRC chain 50/50 and BOOTLOADER replay 49/49   [entailed by the above]", "V")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [12] INDEPENDENT REBUILD -- a second splice + a different CRC locator reproduce the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild == built image sha256.  🛑 HONEST LABEL (V291 defect D4): it shares "
          "this module's constants, so it CANNOT catch a wrong constant -- it is a CRC-LOCATION and "
          "SPLICE cross-check (FF.crc_block_map vs V53.owning_block), nothing more", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [13] GATE 1 -- THE TWO REMAINDER CELLS, CENSUSED ON THE *BUILT* IMAGE")
    print("       (a null from the V282 or V291 image is NOT a null for an image carrying code edits)")
    S = scan_rel(bytes(code))
    print(f"      scanned {len(S)} gp/tp-relative accesses in [0x{START:X},0x{END:X})")
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
          f"CONTROL the 6-BYTE extended-displacement path is LIVE: gp-0x6752 at "
          f"{[hex(h[0]) for h in six]}", "S")
    check([h[0] for h in hits_at(S, 0xC63EC)] == [0x2A184, 0x2A8A2]
          and [h[0] for h in hits_at(S, 0xC63EE)] == [0x2A174, 0x2A892],
          "CONTROL the output-lag pole pair is found without being told (0xC63EC/0xC63EE)", "S")
    check(scan_abs(bytes(code), 0xCB844) == [0x28FCE],
          "CONTROL scan_abs finds the imm32 0xCB844 at 0x28FCE (the absolute-pointer path works)", "S")
    mv_all = scan_movhi_movea(bytes(code), START, END, 0xFEDF0000, 0xFEDFFFFF)
    check(len(mv_all) >= 5,
          f"CONTROL the movhi/movea pair scanner finds {len(mv_all)} pairs reaching the 0xFEDFxxxx "
          f"window image-wide -- so its null on our run is a verified zero", "S")
    # SYNTHETIC control for the Format-VIII bit-op scanner (no attested gp/tp instance exists)
    probe = bytearray(code)
    inj = 0xC4F00
    assert bytes(probe[inj:inj + 12]) == b"\xff" * 12
    for i, (op, bitn, disp) in enumerate(((0, 3, REM_B_DISP), (2, 3, REM_A_DISP), (3, 0, REM_B_DISP))):
        struct.pack_into("<HH", probe, inj + 4 * i,
                         (op << 14) | (bitn << 11) | (0x3E << 5) | 4, disp & 0xFFFF)
    pb = scan_bitop(bytes(probe))
    check(len([h for h in pb if h[0] in (inj, inj + 4, inj + 8)]) == 3,
          f"SYNTHETIC CONTROL for the Format-VIII bit-op scanner: three injected set1/clr1/tst1 on "
          f"gp{REM_B_DISP:+#x}/gp{REM_A_DISP:+#x} are all found.  🛑 The control is SYNTHETIC because "
          f"this image contains NO attested gp/tp-relative Format-VIII instruction -- it bounds the "
          f"SCANNER, not the prevalence of the form", "S")
    print("      -- controls pass; the nulls below are now worth something --")
    cave_sites = {CAVE + 8, CAVE + 0x12, CAVE + 0x18, CAVE + 0x22}          # the four RAM accesses
    for disp, nm in ((REM_B_DISP, "rem_b"), (REM_A_DISP, "rem_a")):
        abs_a = GP_BASE + disp
        h = sorted(x[0] for x in hits_at(S, abs_a))
        want = sorted(a for a in cave_sites if u16(code, a + 2) & 0xFFFE == (disp & 0xFFFF) & 0xFFFE)
        check(h == want and len(h) == 2,
              f"{nm} gp{disp:+#x} = 0x{abs_a:08X}: EXACTLY {len(h)} accessors image-wide, at "
              f"{[hex(a) for a in h]} -- BOTH INSIDE THE CAVE (the ld.hu and the st.h).  Zero other "
              f"readers, zero other writers, zero 6-byte forms", "S")
        check(not scan_abs(bytes(code), abs_a),
              f"{nm}: no LE32 anywhere in the image equals 0x{abs_a:08X} -- no pointer reaches it", "S")
        check(not [x for x in scan_bitop(bytes(code)) if GP_BASE + x[2] == abs_a],
              f"{nm}: no Format-VIII bit-op addresses it", "S")
        check(not scan_movhi_movea(bytes(code), START, END, abs_a, abs_a + 2),
              f"{nm}: no movhi/movea pair constructs its address", "S")
    run_touched = sorted({GP_BASE + h[2] for h in S
                          if h[1] == "gp" and FREE_RUN_LO <= GP_BASE + h[2] < FREE_RUN_HI
                          and h[0] not in cave_sites})
    check(run_touched == [],
          f"and the WHOLE certified free run 0x{FREE_RUN_LO:08X}-0x{FREE_RUN_HI - 1:08X} ({FREE_RUN_HI - FREE_RUN_LO} "
          f"bytes) has ZERO gp accessors outside the cave's own four", "S")
    print("      boot value -- the .data initialiser SOURCE, read from the image's own flash:")
    check(bytes(code[REM_B_SRC:REM_B_SRC + 2]) == b"\x00\x00"
          and bytes(code[REM_A_SRC:REM_A_SRC + 2]) == b"\x00\x00",
          f"rem_b's .data source flash 0x{REM_B_SRC:05X} and rem_a's 0x{REM_A_SRC:05X} both read "
          f"00 00 -- both cells BOOT TO EXACTLY 0 (mapping anchor 0x{DATA_SRC_ANCHOR_RAM:08X} -> "
          f"flash 0x{DATA_SRC_ANCHOR_FLASH:05X})", "S")
    ctrl_off = DATA_SRC_ANCHOR_FLASH + (DATA_CTRL_RAM - DATA_SRC_ANCHOR_RAM)
    check(bytes(code[ctrl_off:ctrl_off + 4]) == DATA_CTRL_BYTES,
          f"ANCHOR CONTROL: gp-0x6AB0's .data source at flash 0x{ctrl_off:05X} reads "
          f"{DATA_CTRL_BYTES.hex()} -- the known NON-ZERO cell that falsified an earlier 'free' claim, "
          f"so the .data mapping is right and the two zeros above are EVIDENCE", "S")
    print("      and the startup clear loop was NOT located -- which is why the cave uses ld.hu, not")
    print("      ld.w: any value either cell could hold is bounded to 65,535 and one `andi 0x3ff`")
    print("      returns it to [0,1023] on the first tick.  The remainders are SELF-HEALING.")

    # ---------------------------------------------------------------------------------------------
    print("\n  [14] GATE 1 (cont.) -- the fb state, the cal cells, and the dead twin island")
    s_hits = sorted(hits_at(S, GP_BASE + S_DISP), key=lambda h: h[0])
    check([x[0] for x in s_hits] == [0x28F7C, 0x28FA8, B3_INSN],
          f"gp-0x3d30 (the fb-lag state s): {[hex(x[0]) for x in s_hits]} "
          f"{[x[3] for x in s_hits]} -- the filter's own ld.w/st.w PLUS the b3 telemetry reader. "
          f"V292 adds NO accessor of its own and NO writer", "S")
    check(all(x[3] != "st.w" for x in s_hits if x[0] == B3_INSN),
          "the b3 cave access to gp-0x3d30 is a LOAD, never a store", "S")
    for cell, site, what in ((FB_A_CELL, FB_A_LOAD, "fb pole a"), (FB_B_CELL, FB_B_LOAD, "fb pole b"),
                             (R24_CELL, R24_LOAD, "r24 engaged arm")):
        h = hits_at(S, cell)
        check(len(h) == 1 and h[0][0] == site and h[0][3].startswith("ld"),
              f"0x{cell:05X} ({what}): EXACTLY 1 reader on the BUILT image, at 0x{site:05X} "
              f"({h[0][3]}) -- 0 writers, 0 six-byte forms.  A cal change here is PRIVATE", "S")
        check(not scan_abs(bytes(code), cell),
              f"0x{cell:05X}: no LE32 in the image equals this address", "S")
    check(not [a for a in range(START, END - 3) if 0xC6300 <= u32(code, a) < 0xC6500],
          "no LE32 table base anywhere in [0xC6300,0xC6500) -- no LERP stride can walk INTO the "
          "fb-pole or r24 cells", "S")
    for _c, _sites in sorted(ISLAND_CONTROLS.items()):
        got = sorted(h[0] for h in hits_at(S, _c) if ISLAND_LO <= h[0] < ISLAND_HI)
        check(got == sorted(_sites),
              f"CONTROL the dead twin island DOES read 0x{_c:05X} at {[hex(a) for a in got]}", "S")
    for _c, _w in ((FB_A_CELL, "fb pole a"), (FB_B_CELL, "fb pole b"), (R24_CELL, "r24 arm"),
                   (GP_BASE + REM_B_DISP, "rem_b"), (GP_BASE + REM_A_DISP, "rem_a"),
                   (GP_BASE + S_DISP, "the fb state s")):
        check([h[0] for h in hits_at(S, _c) if ISLAND_LO <= h[0] < ISLAND_HI] == [],
              f"0x{_c:X} ({_w}) is read ZERO times inside the dead island 0x{ISLAND_LO:05X}-"
              f"0x{ISLAND_HI:05X} -- V292 cannot be silently half-applied through the twin", "S")
    check(LIVE_FWD_T in [h[0] for h in hits_at(S, GP_BASE - 0x6B3C)],
          f"the LIVE forward of the gated T is 0x{LIVE_FWD_T:05X}, inside FUN_00028ea6 -- not the "
          f"island's dead 0x2B41C copy", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [15] NOTHING BRANCHES INTO THE DISPLACED SPAN -- scanned on the BUILT image")
    tg = scan_branch_targets(bytes(code))
    missing = [(t, k, s) for t, k, s in BRANCH_CONTROLS if (k, s) not in tg.get(t, [])]
    check(not missing,
          f"POSITIVE CONTROL {len(BRANCH_CONTROLS) - len(missing)}/{len(BRANCH_CONTROLS)}: every "
          f"target Ghidra lists for this function -- BAIL 4 (jr), the three engagement skips (jr), "
          f"the function's own caller (jarl), and six Bcond targets inside the filter block -- is "
          f"found.  {len(tg)} distinct targets in [0x{START:05X},0xC5000).  Missing: {missing}", "S")
    inside = sorted(t for t in tg if SKIPPED_LO <= t < SKIPPED_HI)
    check(inside == [],
          f"ZERO of the {len(tg)} distinct branch targets land in [0x{SKIPPED_LO:05X},0x{SKIPPED_HI:05X}) "
          f"-- the {SKIPPED_HI - SKIPPED_LO} bytes the hook orphans are UNREACHABLE, so leaving them "
          f"in place is inert", "S")
    tg_base = scan_branch_targets(bytes(base))
    check(RETURN_TO not in tg_base and CAVE not in tg_base,
          f"on the V282 BASE, neither 0x{RETURN_TO:05X} (the return point) nor 0x{CAVE:05X} (the cave) "
          f"is a branch target from anywhere -- both are reached ONLY by fall-through today", "S")
    hx = (lambda v: [(k, hex(s)) for k, s in (v or [])])
    check(tg.get(RETURN_TO) == [("jr", CAVE + CAVE_LEN - 4)],
          f"on the BUILT image 0x{RETURN_TO:05X} has EXACTLY ONE branch predecessor, "
          f"{hx(tg.get(RETURN_TO))} -- the cave's own return `jr` at 0x{CAVE + CAVE_LEN - 4:05X}, and "
          f"nothing else", "S")
    check(tg.get(CAVE) == [("jr", HOOK)],
          f"and 0x{CAVE:05X} has EXACTLY ONE branch predecessor, {hx(tg.get(CAVE))} -- the hook.  The "
          f"cave is entered from one site and leaves to one site", "S")
    check(HOOK not in tg and HOOK not in tg_base,
          f"and 0x{HOOK:05X} (the hook) is a branch target on NEITHER image -- nothing jumps into the "
          f"replaced instruction.  🛑 BOUNDARY: indirect dispatch (`jmp [reg]`, a jump table) is not "
          f"statically resolvable and is covered by NO scan in this kit", "S")
    check(len(tg) == len(tg_base) + 2,
          f"the built image has EXACTLY 2 more distinct branch targets than V282 ({len(tg)} vs "
          f"{len(tg_base)}) -- 0x{CAVE:05X} and 0x{RETURN_TO:05X}, the cave's own two.  V292 creates "
          f"no other control-flow edge anywhere in [0x{START:05X},0xC5000)", "S")

    # ---------------------------------------------------------------------------------------------
    print("\n  [16] THE DELIVERED SURFACE -- read from the BUILT image, never from a constant")
    sumc, gain, outc = u16(code, 0xC61BE), u16(code, 0xC6CD0), u16(code, 0xC61B4)
    peak = min((sumc * gain) >> 15, outc)
    check(peak == 2505 and ((sumc * gain) >> 15) < outc,
          f"peak delivered forward torque = clamp(0xC61BE {sumc} * 0xC6CD0 {gain} >> 15, +-0xC61B4 "
          f"{outc}) = {peak} counts, and the output clamp does NOT bind -- UNCHANGED from V282/V291", "S")
    mp = u32(code, MAP_PTR + 4 * LIVE_SLOT)
    _nm, Xm, Ym = rec(code, mp)
    check(Ym[-1] == 1032 and Xm[-1] == 240 and u16(code, 0xC63E6) == 0,
          f"assist map slot {LIVE_SLOT} @0x{mp:05X}: top Y {Ym[-1]} at X {Xm[-1]} (x{1032 / 172:.2f} of "
          f"Honda's 172) -- the x6 LINEAR map; Ki still ZERO.  Forward path UNCHANGED", "S")
    check(u16(code, 0xC61BE) <= 32767,
          f"0xC61BE = {u16(code, 0xC61BE)} <= 32767 -- the standing ld.hu/ld.h mismatch trap at "
          f"0x2A142/0x2A146 (unchanged by V292, but it is a trap on this path)", "S")
    print(f"      forward path UNCHANGED:  map top {Ym[-1]}  Kp {Y7[0]}  Kd {Ykd[0]}  Ki 0  G {gain}  "
          f"OUT {outc}  SUM {sumc}  -> peak {peak}")
    print(f"      feedback path        :  pole {f_old:.2f} -> {f_new:.2f} Hz (V291's cells, byte-"
          f"identical)   DC {dc_old:.4f} -> {dc_new:.4f} ({100 * (dc_new / dc_old - 1):+.3f} %)")
    print(f"      feedback QUANTISER   :  floor -> floor WITH ERROR FEEDBACK.  mean gain exact at "
          f"every amplitude; the -32-count DC offset is GONE")
    print(f"      r24 lane             :  engaged gain x{R24_OLD / 1024:.4f} -> x{R24_NEW / 1024:.4f} "
          f"({100.0 * (R24_NEW / R24_OLD - 1):+.2f} %), V291's cell byte-identical")

    # ---------------------------------------------------------------------------------------------
    print("\n  [17] THE OUTPUT NAME, RE-DERIVED FROM THE BUILT IMAGE (V291 defect D2 closed)")
    img_tag = make_tag(u16(code, FB_A_CELL), u16(code, FB_B_CELL), u16(code, R24_CELL),
                       CAVE, decode_one(bytes(code), CAVE + 8)[3]["disp"])
    check(img_tag == TAG,
          f"the tag re-derived from the image's OWN halfwords (a = {u16(code, FB_A_CELL)}, b = "
          f"{u16(code, FB_B_CELL)}, r24 = {u16(code, R24_CELL)}, and the cave's own ld.hu "
          f"displacement) is CHARACTER-IDENTICAL to the tag on the output file.  A transcription "
          f"error would RENAME the file, not mislabel it", "S")
    print(f"      {IMG_NAME}")
    print(f"      {RWD_NAME}")

    # ---------------------------------------------------------------------------------------------
    scr = os.environ.get("ACCORD_V292_SCRATCH", "").strip()
    if scr:
        Path(scr, IMG_NAME).write_bytes(bytes(code))
        Path(scr, RWD_NAME).write_bytes(rwd)
        print(f"\n      scratch copy written to {scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        print("\n  [18] WRITE -- guarded BEFORE the write (V291 defect D3 closed)")
        out_img = Path(plain_image_path(IMG_NAME))
        out_rwd = Path(RWD_DIR, RWD_NAME)
        pre_i = [f.name for f in Path(ANALYSIS_ROOT).glob("_v292*")
                 if not f.name.startswith("SUPERSEDED")]
        pre_r = [f.name for f in Path(RWD_DIR).glob("*V292*") if not f.name.startswith("SUPERSEDED")]
        # 🛑 PATH-LENGTH GUARD.  Measured on this machine: a 259-character path opens and renames, a
        #    260-character one fails with FileNotFoundError -- for open() AND for rename().  Without
        #    this check the failure mode is an unhelpful "No such file or directory" on a path that is
        #    plainly there.  Checked for BOTH outputs and BOTH supersede targets before anything moves.
        paths = {"V292 image": out_img, "V292 rwd": out_rwd,
                 "SUPERSEDED V291 image": Path(ANALYSIS_ROOT, SUPERSEDE_PREFIX + V291_IMG),
                 "SUPERSEDED V291 rwd": Path(RWD_DIR, SUPERSEDE_PREFIX + V291_RWD)}
        over = {k: len(str(v)) for k, v in paths.items() if len(str(v)) > MAX_PATH}
        for k, v in paths.items():
            print(f"      path len {len(str(v)):3d}/{MAX_PATH}  {k}")
        check(not over,
              f"every output and rename path is at or under this machine's {MAX_PATH}-character limit "
              f"(over: {over})", "S")
        check(not pre_i and not pre_r,
              f"🛑 WRITE GUARD, CHECKED BEFORE ANY BYTE IS WRITTEN: no non-superseded V292 image "
              f"({pre_i}) or rwd ({pre_r}) exists on disk.  Both files are then opened 'xb', so the "
              f"OS refuses an overwrite even if this check were wrong", "S")
        with open(out_img, "xb") as fh:
            fh.write(bytes(code))
        with open(out_rwd, "xb") as fh:
            fh.write(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha
              and hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha,
              "both files re-hashed FROM THE FILESYSTEM match the reported sha256", "S")
        # supersede V291 -- V292 dominates it: same cells, same dose, mean-exact arithmetic
        for d, nm in ((Path(ANALYSIS_ROOT), V291_IMG), (Path(RWD_DIR), V291_RWD)):
            src_p, dst_p = d / nm, d / (SUPERSEDE_PREFIX + nm)
            if src_p.exists():
                check(not dst_p.exists(), f"the superseded name is free: {dst_p.name}", "S")
                src_p.rename(dst_p)
                print(f"      renamed  {nm}\n            -> {dst_p.name}")
            else:
                print(f"      (V291 artifact already absent or renamed: {nm})")
        left_r = sorted(f.name for f in Path(RWD_DIR).glob("*V292*")
                        if not f.name.startswith("SUPERSEDED"))
        left_i = sorted(f.name for f in Path(ANALYSIS_ROOT).glob("_v292*")
                        if not f.name.startswith("SUPERSEDED"))
        v291_left = sorted(f.name for f in Path(RWD_DIR).glob("*V291*")
                           if not f.name.startswith("SUPERSEDED"))
        check(left_r == [RWD_NAME] and left_i == [IMG_NAME] and v291_left == [],
              f"EXACTLY ONE flashable V292 rwd and ONE V292 image on disk, and ZERO flashable V291 "
              f"rwds remain ({left_r}, {left_i}, V291 left: {v291_left})", "S")
        print("\n      WROTE image + rwd to the firmware root; V291 superseded")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V292_WRITE=rwd to emit the files "
              "(and to supersede V291)")

    print("\n" + "=" * 116)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- census: {_census['S']} SUBSTANTIVE, "
          f"{_census['V']} vacuous (entailed by the base sha256 or by an earlier assertion), "
          f"{_census['T']} tautological (readback of a write)")
    print(f"  ** V292 = V291 C10's THREE CELLS, BYTE-IDENTICAL, plus a {CAVE_LEN}-byte error-feedback "
          f"cave at 0x{CAVE:05X} hooked at 0x{HOOK:05X}.")
    print(f"  ** {len(diff)} bytes DIFFER from V282 ({v291_payload} V291 payload + 4 hook + "
          f"{CAVE_LEN - len(cave_ff)} cave + 8 CRC); {4 + CAVE_LEN} code bytes are WRITTEN "
          f"({len(cave_ff)} cave bytes happen to equal the 0xFF they replace).  Forward path "
          f"UNTOUCHED, peak torque {peak}.")
    print(f"  ** The mean input gain is now EXACTLY b/1024 and the mean decay EXACTLY a/1024 at every "
          f"amplitude; the -32-count phantom error is gone.")
    print(f"  ** FREE POSITIVE CONTROL: 0x14A byte 4 bit 3 (sign of the fb state) must read duty "
          f"~0.000 at rest.  On V291 it reads 0.52-1.00.")
    print(f"  ** 🛑 REVERT SIGNATURE, PRE-REGISTERED: any new roughness, tone or line at 10-18 Hz. "
          f"The 20 Hz claim is SERVO-SIDE ONLY (the plant was identified with r24 = 5244 inside it).")
    print(f"  ** 🛑 `AccordCurvatureLead` must be OFF on the fork.")
    print("=" * 116)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
