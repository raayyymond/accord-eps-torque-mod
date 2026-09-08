# -*- coding: utf-8 -*-
r"""V288 REV 2 -- V282 + a FIRST-ORDER LAG ON THE LKAS RATE-PID *SETPOINT*, with an ENGAGE-TIME INIT,
in a new code cave, plus ONE telemetry bit that publishes the filter's own state on CAN 0x14A b4.5.

=== REV 1 IS SUPERSEDED -- DO NOT FLASH IT =====================================================
Rev 1 (image bc8a5b1a…, rwd 862cb525…) FAILED the adversarial pass on two counts.  Both are fixed
here, and both fixes are asserted from the image rather than asserted in prose:

  FAIL A -- IT OVERWROTE A STOCK CAN FLAG.  Rev 1 put its new telemetry bit on 0x14A byte 4 bit 0,
    having concluded "bits 2-0 are free" from the CAVE's own andi masks.  That census was
    incomplete: the STOCK FRAME BUILDER writes bits 2, 1 and 0 of the same byte at 0x55AC0
    (bit 2 <- gp-0x6799 b0), 0x55AE8 (bit 1 <- gp-0x679b b0) and 0x55B06 (bit 0 <- gp-0x679a b0),
    and all three run BEFORE the cave hook at 0x55C0E -- so rev 1's rung won the race and silently
    destroyed a live flag.
    FIX: rev 2 puts the bit on b4.5, which the CAVE already owns.  It REDEFINES V282's bit 5 (the
    |r24| >= |aggregator sum| comparator, the lower-value of the two).  The flown bit-5 rung at
    0xC4B7A-0xC4B8F keeps its bytes; our tail runs after it and overwrites the bit.  Mask 0xDF
    clears bit 5 and nothing else.  Asserted at [1b2] and again at [11].

  FAIL B -- THE FILTER STATE WENT STALE ACROSS A DISENGAGEMENT.  All three routes that skip our hook
    (0x29A5C and 0x29A64 -> 0x2A164 ; 0x29A70 -> 0x2A0C6) leave gp-0x6a32 untouched, so y kept an
    old setpoint for the whole gap and seeded the next engagement with it -- up to ~11 ms of railed
    P in the stale direction.
    FIX: an ENGAGE-INIT prologue.  See below.

=== THE ENGAGE-INIT (rev 2's prologue) =========================================================
gp-0x6cf8 is a 32-bit cell in the LKAS PID's SHARED EPILOGUE.  It is written EVERY tick by the single
store `st.w r16,-0x6cf8,gp` @0x2A18C, and read once @0x29E5E, which is AFTER our hook in tick order.
  * on the engaged route  r16 = the current E (Honda's own "previous E" for the D term);
  * on ALL THREE HOOK-SKIPPING routes r16 = 0x7FFFFFFF, loaded at 0x2A16C or 0x2A0EA -- the only two
    such sites in the image.  The two routes through 0x2A164 (from 0x29A5C and 0x29A64) take
    0x2A16C.  The THIRD route, 0x29A70 -> 0x2A0C6, takes 0x2A0EA and then reaches the same store
    via 0x2A14A / 0x2A15E / 0x2A162 (or 0x2A154 -> 0x2A160 -> br).  Nothing on either span rewrites
    r16 before the store: verified instruction by instruction over both spans, and asserted at [2c].
    So all three skips arm the init; there is no route that leaves y stale without arming it.
So at our hook, `gp-0x6cf8 == 0x7FFFFFFF` <=> the PREVIOUS tick did not execute 0x29D72 <=> this is
the first engaged tick after a gap.  Exact in both directions.  Honda already uses this very cell at
0x29E5E as its own first-tick-after-gap guard (|prev| > 768000 => dE := 0), so we are reading a
marker Honda itself maintains, not inventing one.

  ld.w -0x6cf8[gp], r6     ; hw2 = 0x9309 -- bit 0 SET selects the 32-bit WORD form
  mov  0x7fffffff, r9      ; 6-byte Format VI; the DESTINATION is the reg1 field, bits 4:0
  cmp  r9, r6              ; an EXACT 32-bit equality
  be   <the st.h>          ; first tick after a gap: y := sp.  r16 is UNTOUCHED by the prologue, so
                           ; it still holds raw sp; the shared store+reload+return then give a tick
                           ; BYTE-IDENTICAL to V282.  No new store, no filter arithmetic changed.

An EXACT compare, not the cheaper `sar 0x1c ; cmp 7` top-nibble test.  The nibble test would have
fired for ANY value in [0x70000000, 0x7FFFFFFF]; that band is far above the largest possible |E|
(32*1128 + 46080 = 82176, a 26132x margin) so it was defensible, but it is a BOUND rather than an
exclusion.  The exact form costs 4 bytes and removes the question entirely: the only 32-bit value
that can trip the init is the sentinel itself, which makes the property exhaustive by construction
rather than sampled.  r6 and r9 are both dead at the hook, and the filter body below overwrites both
before reading either, so the prologue's use of them costs nothing.

🛑 0x2A164 IS A SHARED EPILOGUE, NOT A PRIVATE RESET PATH.  Three unconditional `br` (0x2A14A,
0x2A15E, 0x2A162) enter the same store block at 0x2A174, one instruction past the reset constants.
A store added at 0x2A164 would therefore fire on EVERY tick.  Do not put one there.  This is also
what makes the sentinel TRANSIENT rather than a latch, and hence what makes the init fire exactly
once per re-engage.  Re-derived at [2c] by a positive-controlled branch scan, not relayed.

=== LAYOUT MOVED IN REV 2 ======================================================================
The prologue is 14 bytes (exact 32-bit compare) and rev 1's filter cave had only 2 bytes of slack before the telemetry rung.
Both regions were relocated: telemetry now at 0xC4BDC (34 B), filter at 0xC4C00 (48 B).  Every
displacement -- the hook `jr`, the return `jr`, the 0xC4BD6 `jr` and both Bcond -- is re-derived and
checked in both directions at [5], and the diff regions below are re-stated accordingly.

Spec: docs/specs/design/SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md (author: agent `tracer`).
This script re-derives EVERY load-bearing number from the V282 IMAGE.  Where it disagrees with the spec
the disagreement is called out in the comment, and the image wins.

=== WHAT THIS BUILD IS =========================================================================
A REFERENCE PRE-FILTER.  The LKAS rate PID computes `E = 32*sp - fb` where `sp` is the assist-map output
(`mulh r13,r16` @0x29D6C) and `fb` is the rate feedback.  `dE = E[n] - E[n-1]` feeds the D term.  There is
NO state anywhere on the setpoint side, so the 100 Hz command staircase arrives at a 1 kHz loop as a
staircase and every step edge is a full-height impulse into D.  V288 puts a one-pole lag on `sp` ALONE,
BEFORE it multiplies into E.

  Honda today:      sp -> [x32] -> (-) -> E -> P,I,D -> ... -> motor
                                     ^ fb
  V288:      sp -> [lag 2^-K] -> [x32] -> (-) -> E -> P,I,D -> ... -> motor
                                            ^ fb                    (loop C(s)*P(s) UNCHANGED)

This is the textbook 2-DOF structure: the return ratio is untouched, only the reference is shaped.  No
gain moves, no clamp moves, no authority moves, no cal byte moves.

=== CLASS OF BUILD, AGAINST THE WHOLE POST-V38 ARC =============================================
The arc has been: V38-V52 authority/filters/poles/caves; V53-V61 telemetry probes and lane mutes;
V62-V73 the rate lane (r24/r26); V74-V83a the base-assist damper; V84 damper reverted; V90-V122 the
notch/biquad arc; V235-V264 notch re-aims and the damper census; V268-V282 the map, the feedback clamp,
Kp, and the 0x14A comparator cave; V283-V287 Ki, Kp shape, and the D clamp (V287 rev 2, D 10240->7680).

  * EVERY ONE of those moved a CALIBRATION CONSTANT or a comparator's operands.  Grind #1's cal-only
    surface was declared EXHAUSTED at the V287 close-out.
  * V288 is the FIRST build in the arc to add STATE to the setpoint path.  It is not "the same lever the
    other way": no existing cell has a filter on `sp`, because `sp` had no filter to move.  It is new
    CODE, in a new cave, which is why the cave-discipline gates below are run in full.
  * It is also the first build since V112 to add code to the 0x14A telemetry cave.

    RE-RUN WARNING, stated plainly: code caves are this kit's ONLY bricking class (V24, V27, V48B all
    bricked the ECU).  Every success since V29 has been cal-only or a single in-place edit.  This build
    is deliberately in the dangerous class, so GATE 1 (RAM ownership) and GATE 2 (closed-loop stability)
    are argued explicitly below and the register-liveness claim is re-derived from the bytes here, not
    inherited.

=== THE EDIT, VERIFIED FROM THE IMAGE ==========================================================
FOUR changed regions (plus one CRC trailer).  Sizes and addresses below are REV 2's and are printed
back from the built image at [3]/[9]; do not read them from an earlier revision's description.

 (1) 0x29D72          the HOOK.  `st.h r16,-0x6a32,gp` (64 87 ce 95) -> `jr 0xC4C00` (4 bytes, the
     SAME LENGTH, so 0x29D76 onward does not move).  The displaced store was a DEAD store (gp-0x6a32
     has zero readers, see GATE 1); the cave re-issues it, now carrying the FILTERED value.
 (2) 0xC4C00-0xC4C2F  the FILTER CAVE, 48 bytes in confirmed-free flash, in two parts:
        * a 14-byte ENGAGE-INIT PROLOGUE -- `ld.w -0x6cf8[gp],r6 ; mov 0x7fffffff,r9 ; cmp r9,r6 ;
          be <the st.h>`.  An EXACT 32-bit equality against Honda's own shared-epilogue marker.  On
          the first engaged tick after any gap it branches straight to the store with r16 still
          holding RAW sp, so that tick is byte-identical to V282.  See THE ENGAGE-INIT above.
        * a 34-byte FILTER BODY + shared tail -- reads gp-0x6a32 as y[n-1], computes the lag with
          the rounding fix, stores y[n] back, reloads it so the register and the 16-bit cell cannot
          diverge, and `jr`s to 0x29D76 (the untouched `shl 0x5,r16`).
     (The diff at [9] shows this cave as TWO runs, 6 B + 39 B, because three bytes of the 0x7FFFFFFF
     immediate happen to equal the 0xFF filler they replaced.  Runs are labelled by range, not by
     start address, and every run is asserted attributable.)
 (3) 0xC4BD6-0xC4BD9  the 0x14A cave's `jmp [lp]` epilogue (7f 00) -> `jr 0xC4BDC` (4 bytes; the
     extra 2 land on 0xC4BD8-0xC4BD9, which were 0xFF filler).  NO existing rung's bytes move.
 (4) 0xC4BDC-0xC4BFD  the TELEMETRY RUNG, 34 bytes: one sign rung publishing sign(gp-0x6a32) to
     0x14A byte 4 BIT 5 (mask 0xDF, built as `mov 0x2,r7 ; shl 0x4,r7`, the flown rungs' own idiom),
     then the RELOCATED epilogue (`movea -0x1518,gp,r6 ; jmp [lp]`) byte-identical to what
     0xC4BD2/0xC4BD6 held.  Bit 5 REPLACES V282's `|r24| >= |aggregator sum (gp-0x6b94)|` comparator,
     the lower-value of its two comparator bits; that rung keeps its bytes and our tail, running
     after it, overwrites the bit.  See the INSTRUMENT section for why bit 5 and not a low bit.

=== GATE 1 -- RAM OWNERSHIP OF gp-0x6a32 (0xFEDF15CE) ==========================================
Re-derived here at [2] by a raw little-endian Python scan of the whole 1 MiB V282 image, POSITIVE-
CONTROLLED against known accesses before its null is trusted (`firmware-decompile` skill: an uncontrolled
null is a guess with a number attached).  The scan covers, for the target cell:
    * 4-byte gp-relative disp16 loads AND stores (ld.h/ld.w/ld.hu/ld.b/ld.bu/st.b/st.h/st.w),
      including the hw2-bit0 and the ld.bu hw1-bit5 displacement traps -- see ENCODING TRAPS below;
    * the 6-byte extended-displacement gp form;
    * `movhi`+`movea` materialisation of the absolute address 0xFEDF15CE;
    * a raw dword-literal scan for 0xFEDF15CE.
Result: exactly TWO accesses, both `st.h`, both writers, ZERO readers, no indirect route.
    0x29D72  st.h r16,-0x6a32,gp   -- LIVE.  This build replaces it (the cave re-issues it).
    0x2AC68  st.h r9, -0x6a32,gp   -- inside [0x2A508,0x2B422), the duplicate PID copy the source trace
                                      proved unreachable.  NOT re-verified independently here: carried
                                      as BELIEF from TRACE-2026-09-06 Addendum 3.  It is a WRITER, not a
                                      reader, so even if it did execute it would only reset the filter
                                      state, never read a wrong value out of it.
So the cave introduces no new writer and no new reader that any OTHER function can observe.  GATE 1 PASS.

=== GATE 2 -- CLOSED-LOOP STABILITY ============================================================
Magnitude AND phase, in every loop the signal is in.

  🛑 ATTRIBUTION: the sentence "`sp` is in NO loop" is BELIEF-INHERITED from
  TRACE-2026-09-06 and is NOT re-derived by this script.  Adversary ADV-V288-B verified it
  independently FROM THE DECOMPILE; cite B's report as the evidence, and read this paragraph as a
  summary of it, not as a second confirmation.  What THIS script does establish from the image is the
  narrower half: gp-0x6a32 has zero readers (GATE 1, [2], positive-controlled).

`sp` is in no loop: nothing downstream of E feeds back into `sp`, and gp-0x6a32 has zero readers, so
the filter's state is not in any feedback path either.
The inner rate loop's return ratio (Kp, Kd, the fb pole, the output lag, the clamps) is byte-identical to
V282.  A reference pre-filter cannot move the gain or phase margin of a loop it is not inside.
  * What it DOES change: the OUTER loop (openpilot's lateral controller closing around the car) now sees
    an extra 15 ms of group delay at K=4 and 0.960 magnitude at 3 Hz.  That is a real cost and it is the
    one honest risk of this build -- stated on the page, not buried.  At the outer loop's ~3 Hz it is
    ~16 deg of extra phase lag.
  * The filter is NOT exactly linear: the rounding fix imposes a 1-count/tick slew floor whenever
    |d| < 2^K.  With |sp| <= 1032 that regime is only entered within 16 counts of convergence, so the
    linear response above describes the grind-band behaviour; the small-signal limit cycle is +-1 count.

=== THE ROUNDING FIX, AND WHY THE NAIVE FORM IS WRONG ==========================================
V850 `sar` is ARITHMETIC and floors toward -infinity.  `y += (sp-y) >> K` is therefore ASYMMETRIC:
approaching from ABOVE, d in [-2^K,-1] gives step -1 and converges; approaching from BELOW, 0 < d < 2^K
gives step 0 and the state STICKS, permanently, up to 2^K-1 short of the target.  Verified by exhaustive
simulation at [4].  The cave adds: `if step == 0 and d != 0: step = +1`.
  Because sar never rounds a NEGATIVE d to zero, `step == 0 and d != 0` implies d > 0 in every case --
  proven exhaustively over d in [-4096,4096] for K = 1..7 at [4] -- so a bare `mov 0x1,r16` is correct and
  no sign test is needed.  That is 2 bytes and one branch cheaper than the general `d>0 ? +1 : -1`.

=== ENCODING TRAPS THIS SCRIPT HAD TO GET RIGHT (all found by positive control, not by reading a manual) =
 (a) `ld.h` / `ld.w` share opcode field 0x39 and `st.h` / `st.w` share 0x3B; hw2 BIT 0 selects the 32-bit
     form.  An odd displacement silently WIDENS the access.  Both cells here are even; asserted at [3].
 (b) `ld.bu` steals displacement bit 0 into hw1 bit 5 (opcode field 0x3C even / 0x3D odd) AND sets
     hw2 bit 0 to a fixed 1.  Encoding hw2 as `disp & 0xFFFE` addresses the cell BELOW -- caught by the
     control at [1c] against the flown cave's own `ld.bu -0x1514,gp,r6` = 84 37 ed ea.
 (c) `ld.bu` and Format-V `jr`/`jarl` COLLIDE in hw1 bits 10:6 (both 0b11110).  The discriminator is
     hw2 bit 0: 0 -> jr/jarl, 1 -> ld.bu.  A decoder without this reads every `ld.bu -0x1514,gp,r6` in
     the flown cave as `jarl 0x113640,r6`.  Both directions are controlled at [1c].
 (d) tp-relative: tp = 0xBF000, so the idx clamp `ld.bu 0x74f0,tp` is 0xC64F0, NOT 0xC74F0.

=== INSTRUMENT (mandatory -- no build ships without the telemetry to measure it) ================
The lever is a filter on `sp`.  What must be observable is that the filter RAN and how much it DELAYED.
  * `sp_raw` needs no tap: the source trace proved the whole chain from the 0xE4 CAN byte to `sp` is
    memoryless, so `sp_raw` is exactly reconstructable offline, tick for tick, from the logged 0xE4
    stream plus the map tables read out of this very image.
  * `sp_filtered` is NOT reconstructable without knowing the filter ran, so it goes on the wire:
    0x14A byte 4 BIT 5 = (gp-0x6a32 < 0), written with mask 0xDF.
    WHICH BITS ARE OURS TO SPEND, re-derived at [1b]/[1b2] from the image and NOT from the cave alone:
      - bits 7,6,5,4,3 belong to the V112 cave (andi masks 0xBF, 0xDF, 0x67 -- 0x67 clears 7,4,3
        together, which is the three-sign rung);
      - bits 2,1,0 are STOCK HONDA, written by the FRAME BUILDER at 0x55AC0 (bit 2 <- gp-0x6799 b0),
        0x55AE8 (bit 1 <- gp-0x679b b0) and 0x55B06 (bit 0 <- gp-0x679a b0), all of which run BEFORE
        the cave hook at 0x55C0E.  They are NOT free.  Rev 1 read "free" off the cave's own masks
        alone, took bit 0, and destroyed a live CAN flag -- that is FAIL A.
    So the bit had to come out of the cave's OWN five, and bit 5 is the cheapest of them: its V282
    comparator `|r24| >= |aggregator sum|` has never appeared in any analysis, whereas bit 6
    (`|r24| >= |T|`) is the one V282 was cut to measure and bit 4 (sign(r24)) carries recorded phase
    behaviour on four routes.
  * WHAT A NULL LICENSES, written before the cut: the zero-crossing lag between BIT 5 on the wire and
    the offline-reconstructed sign(sp_raw) IS the group delay, in ms, measured directly.  If that lag
    reads ~15 ms at K=4 the filter ran at the designed corner.  If it reads 0 ms, the filter did not
    act.  If BIT 5's duty is 0.000 or 1.000 over >= 20 s of engaged lateral driving, the rung did not
    execute at all -- that is a BUILD-IDENTITY failure and the drive says NOTHING about the lever, not
    a null on the hypothesis.  The CAN-427 delivered-torque tap (gp-0x6b38) is untouched and remains
    the magnitude channel the lag is read against.  Bit 4 (sign(r24)) and bit 6 (|r24| >= |T|) keep
    working and are the positive control that separates "the new rung is wrong" from "the cave stopped
    firing"; bits 2-0 must still carry their stock Honda values, which is the check that FAIL A has
    not recurred on the wire.
  * This is a paired SIGN BIT + a reconstructable MAGNITUDE, which is the shape the design law says has
    decided something in every probe build that ever decided anything.

=== WHAT IS CARRIED, UNCHANGED, FROM V282 ======================================================
Every V281 rev 3 / V282 cal edit: Kp LERP flat Y0=248 on all 28 records, map linear to 6x, feedback clamp
0xC62E6 = 46080, Kd 128, the tapers, the 427 delivered-torque tap window 0x55DF0-0x55E11, the 0x55C0E
cave hook, and all five existing 0x14A rungs.  Asserted byte-identical at [6]/[7].  V287's D-clamp edit
(0xC61B6 -> 7680) is NOT carried: this build branches from V282, not from V287.

=== THE DOSE ===================================================================================
ONE constant selects it: `K_SHIFT` below.  Nothing else in this file changes with it -- the cave
encoding, the output names, the docstring numbers printed at run time, the unit tests and every
assertion all follow from it.  Re-cutting at K=3 is the single character `"4"` -> `"3"`.

  K   pole a    f_c      |H| 3 Hz   |H| 20 Hz   |H| 40 Hz   tau      group delay   per-tick kick
  --  --------  -------  ---------  ----------  ----------  -------  ------------  -------------
  3   0.87500   21.28 Hz   0.990      0.729       0.470      7.5 ms     7.0 ms        x 1/8
  4   0.93750   10.28 Hz   0.960      0.457       0.249     15.5 ms    15.0 ms        x 1/16   <-- FLOWN
  5   0.96875    5.05 Hz   0.860      0.245       0.126     31.5 ms    31.0 ms        x 1/32

**K = 4 is the confirmed dose** (orchestrator, 2026-09-07).  The wire study priced the 10 Hz IIR at:
command content in the 18-22 Hz grind band x0.446, per-tick D kick x0.059, and D-rail duty inside
episodes 1.81 % -> 0.30 %.  Those four figures are the WIRE STUDY'S, measured off logged frames; they
are NOT re-derived by this script and are quoted here as the reason for the dose, not as its output.

K=3 is the fallback if 15 ms of outer-loop group delay proves too much to drive: it is the same lever,
half the delay, and roughly half the grind-band attenuation (0.729 vs 0.457 at 20 Hz).  K=5 is priced
above for completeness and is NOT recommended -- 31 ms of delay and 14 % attenuation at the outer
loop's own 3 Hz band is a large cost for 21 % more grind-band rejection than K=4.

=== NO CLAIM MADE ==============================================================================
This docstring claims NO peak torque, NO cure, and NO symptom outcome.  What THIS SCRIPT claims, all
computed from K at [4] and all re-read from the BUILT image at [8]:
    corner frequency f_c, |H| at 3/20/40 Hz, DC group delay tau, and a first-tick kick reduction of 2^K.
Whether that changes what the operator feels is for the operator to say, after a drive.
"""
import hashlib
import math
import os
import re
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

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V288_WRITE", "").strip().lower()

# ================================================================================================
#  THE ONE DOSE KNOB.  Everything else in this file is derived from it.  Re-run with a different K
#  and NOTHING else needs to change -- names, docstring numbers, tests and assertions all follow.
# ================================================================================================
#  K = 4 is the CONFIRMED dose (orchestrator, 2026-09-07): 10.3 Hz corner, 15 ms group delay,
#  per-tick kick x1/16.  To re-cut at the K=3 fallback, change the "4" below to "3" and NOTHING else.
K_SHIFT = int(os.environ.get("ACCORD_V288_K", "4"))
assert 1 <= K_SHIFT <= 15, "K must be 1..15 (imm5 sar; K=0 would be a pure pass-through)"
DOSE_CONFIRMED_K = 4                  # what the wire study priced and the orchestrator selected
# The wire study's own numbers for K=4, quoted (NOT re-derived here) as the reason for the dose:
WIRE_STUDY_K4 = dict(band_18_22_hz=0.446, per_tick_d_kick=0.059,
                     d_rail_duty_before=0.0181, d_rail_duty_after=0.0030,
                     source="wire study, 2026-09-07, logged frames -- not recomputed by this script")

TICK_HZ = 1000.0          # BELIEF, inherited from TRACE-2026-09-06 sec 3.2 (0xC64DF=100 debounce
                          # measured at 100.00 ms on the wire).  Only the f_c/tau NUMBERS depend on it;
                          # the code and every safety argument do not.

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080"
             ".TORQUE.TAP_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"

# The cave segment SPELLS OUT the instrument change, so the filename alone says which 0x14A bits
# this build defines: B6 = |r24| >= |T| RETAINED from V282; B5 = sign(y), REPLACING V282's
# |r24| >= |aggregator sum|.  Adversary A's finding was that a build must not be identifiable only
# by a name that still claims V282's bit map.
TAG = (f"V288R2-V282BASE-SPFILT.K{K_SHIFT}.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5"
       "-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP")
IMG_NAME = f"_v288r2_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
# REV 1, SUPERSEDED -- DO NOT FLASH.  Recorded here so the record is complete and so the rev-1
# artifacts on disk can be identified by hash.  It failed the adversarial pass on two counts:
#   FAIL A  its telemetry rung wrote 0x14A byte-4 bit 0, which is a STOCK Honda flag written by the
#           frame builder at 0x55B06 before the cave runs.  Fixed in rev 2 by moving to OUR bit 5.
#   FAIL B  the filter state y went stale across a disengagement, because all three hook-skipping
#           routes leave gp-0x6a32 untouched, so a re-engage started from an old setpoint and could
#           rail P in the stale direction.  Fixed in rev 2 by the engage-init prologue.
REV1_IMG_SHA = "bc8a5b1ac2f796faa5563bb79e221a2f884f55ec040c654114fa2861f2ef5571"
REV1_RWD_SHA = "862cb52591f6899223053bf5e833f77d148b7ab89c895ac86dab008adfbb6f26"

# ---- registers ---------------------------------------------------------------------------------
R0, GP, TP, R6, R7, R8, R9, R10, R13, R16, R26, LP = 0, 4, 5, 6, 7, 8, 9, 10, 13, 16, 26, 31

# ---- [1] the hook site -------------------------------------------------------------------------
HOOK_SP = 0x29D72                     # st.h r16,-0x6a32,gp -- the dead publish of the raw setpoint
HOOK_SP_OLD = bytes.fromhex("6487ce95")
HOOK_RET = 0x29D76                    # shl 0x5,r16 -- resume here, untouched
SP_CELL_DISP = -0x6A32                # gp-relative; absolute RAM 0xFEDF8000-0x6A32 = 0xFEDF15CE
GP_BASE = 0xFEDF8000
SP_CELL_ABS = GP_BASE + SP_CELL_DISP
# every instruction of the hook window, re-encoded at [1c] and asserted byte-identical
HOOK_WINDOW = (0x29D6A, 0x29D84)

# ---- [2] the 0x14A telemetry cave (V112; byte-identical on the car since V105, repointed by V282) -
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
CAVE_EPILOGUE = 0xC4BD2               # movea -0x1518,gp,r6   (4 B, the buffer base -> return value)
CAVE_JMP_LP = 0xC4BD6                 # jmp [lp]              (2 B, the cave's single exit)
CAVE_JMP_LP_OLD = bytes.fromhex("7f00")
BUF_BYTE4_DISP = -0x1514              # 0x14A byte 4 (buffer base gp-0x1518 + 4)
BUF_BASE_DISP = -0x1518
CAVE_HOOK = 0x55C0E                   # jarl 0xc4b34,lp -- UNTOUCHED
CAVE_HOOK4 = bytes.fromhex("86ff26ef")

# 🛑 REV 1's BIT CHOICE WAS A FAIL.  byte-4 bits 0,1,2 are STOCK HONDA flags written by the FRAME
# BUILDER, not free: 0x55AC0 (bit 2 <- gp-0x6799 b0, mask 0xfb), 0x55AE8 (bit 1 <- gp-0x679b b0,
# mask 0xfd), 0x55B06 (bit 0 <- gp-0x679a b0, mask 0xfe).  All three run BEFORE the cave hook at
# 0x55C0E, so rev 1's bit-0 rung silently overwrote a live CAN flag.  Rev 1's census scanned only
# the CAVE's own masks and never looked at the frame builder.
# REV 2 repurposes OUR OWN bit 5 instead -- the lower-value of V282's two comparator bits.  The
# flown bit-5 rung at 0xC4B7A-0xC4B8F keeps its bytes; the tail runs after it and wins the race.
NEW_BIT = 0x20                        # byte 4 bit 5 = sign(y).  1 when y < 0.
NEW_BIT_NIB = 0x02                    # built as `mov 0x2,r7 ; shl 0x4,r7` -- the flown rungs' own idiom
NEW_BIT_MASK = 0xFF & ~NEW_BIT        # 0xDF: clears ONLY bit 5, preserves stock bits 0-2 and ours 7,6,4,3
STOCK_B4_BITS = 0x07                  # bits 0-2: STOCK.  No rung of ours may ever clear one.
STOCK_B4_WRITERS = {                  # frame-builder stores to gp-0x1514, asserted byte-identical
    0x55AC0: bytes.fromhex("4447ecea"),   # st.b r8,-0x1514,gp   (bit 2)
    0x55AE8: bytes.fromhex("4437ecea"),   # st.b r6,-0x1514,gp   (bit 1)
    0x55B06: bytes.fromhex("447fecea"),   # st.b r15,-0x1514,gp  (bit 0)
}
STOCK_B4_MASKS = {                    # and the andi immediately feeding each, also byte-identical
    0x55AB4: 0xFB, 0x55ADC: 0xFD, 0x55AFC: 0xFE,
}

# ---- [2b] the ENGAGE-INIT marker (rev 2) --------------------------------------------------------
# gp-0x6cf8 is a 32-bit cell in the LKAS PID's SHARED EPILOGUE.  It is written EVERY tick by the one
# store `st.w r16,-0x6cf8,gp` @0x2A18C, and read once @0x29E5E -- AFTER our hook in tick order.
#   * engaged route      -> r16 = the current E (Honda's own "previous E" for the D term)
#   * the three HOOK-SKIPPING routes (0x29A5C, 0x29A64 -> 0x2A164 ; 0x29A70 -> 0x2A0C6) load
#     0x7FFFFFFF into r16 (only two sites, 0x2A16C and 0x2A0EA) and store THAT.
# So at our hook, `gp-0x6cf8 == 0x7FFFFFFF` <=> the previous tick did not execute 0x29D72 <=> this
# is the first engaged tick after a gap.  Exact in both directions.  Honda already uses this same
# cell at 0x29E5E as its own first-tick-after-gap guard (|prev| > 768000 => dE := 0).
# 🛑 0x2A164 is a SHARED EPILOGUE, not a private reset path: three unconditional `br` from 0x2A14A,
# 0x2A15E and 0x2A162 enter the SAME store block at 0x2A174, one instruction past the reset
# constants.  Do NOT add a store there -- it would fire on every tick.  [Verified by main in Ghidra
# 0x2A160-0x2A194; independently re-derived here at [2c] by a positive-controlled branch scan.]
EINIT_CELL_DISP = -0x6CF8
EINIT_SENTINEL = 0x7FFFFFFF
# (the superseded top-nibble test `sar 0x1c ; cmp 7` is NOT used; rev 2 compares the full 32-bit sentinel)
EINIT_EPILOGUE_ST = 0x2A18C           # st.w r16,-0x6cf8,gp   -- the every-tick writer
EINIT_READER = 0x29E5E                # ld.w -0x6cf8,gp,r8    -- Honda's own consumer, AFTER our hook
EINIT_SENTINEL_SITES = (0x2A16C, 0x2A0EA)   # the only two `mov 0x7fffffff,rX`
EINIT_SHARED_ENTRY = 0x2A174          # where the NORMAL path enters the shared store block
# |E| can never reach the tag: 32*max(map Y) + the feedback clamp = 32*1128 + 46080 = 82176, and
# 7 << 28 = 0x70000000 = 1879048192.  Margin 22863x.  Asserted from the image at [4].
E_MAX_BOUND = 32 * 1128 + 46080

# ---- [3] free flash and the new cave layout (RELOCATED for rev 2 -- the prologue needs 10 B more) -
FREE_LO, FREE_HI = 0xC4BD8, 0xC4FF0   # 0xFF filler, re-confirmed by direct read at [3]
STRUCT_LO, STRUCT_HI = 0xC4FF0, 0xC4FFC   # 12 unidentified non-FF bytes -- NOT free, never touched
TELE = 0xC4BDC                        # telemetry rung   (34 B) -> 0xC4BDC..0xC4BFD
FILT = 0xC4C00                        # filter cave      (48 B) -> 0xC4C00..0xC4C2F  (extent derived from the emitted bytes)

PACK_LO, PACK_HI = 0x55DF0, 0x55E12   # the CAN-427 delivered-torque tap -- untouched
FB_CELL, FB_V280 = 0xC62E6, 46080
MAP_PTR, MAP_N = 0xC9A88, 10
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y = (0, 68, 112, 136, 208), (248,) * 5
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)
IDX_CLAMP_TP = 0x74F0                 # tp+0x74F0 = 0xC64F0 (tp = 0xBF000).  ld.bu -> 240, the map idx clamp.
IPATH_CLAMP_TP = 0x72E4               # tp+0x72E4 = 0xC62E4 (== 4) -- the cal `ld.hu ...,r10` @0x29D6E
                                      # loads and `cmp r10,r6` @0x29D7E consumes.  r10 MUST SURVIVE.
TP_BASE = 0xBF000

FROZEN = {
    0xC61B2: 3072,
    0xC61B4: 3072,
    0xC61B6: 10240,   # D clamp -- V282's value.  V287 rev 2 moved it to 7680; NOT carried here.
    0xC61BA: 10240,
    0xC61BC: 15360,
    0xC61BE: 15360,
    0xC63E6: 0,                        # Ki
    0xC63E8: 923,    0xC63EA: 1560,    # fb pole
    0xC63EC: 992,    0xC63EE: 507,     # output-lag pole
    0xC62E4: 4,
    0xC62E6: 46080,
    0xC6446: 5244,                     # the r24 gain arm
    0xC644A: 1024,
    0xC6AE6: 2048,
    0xC6B12: 98,     0xC6B26: 256,
    0xC6CD0: 5346,
}

OK, BAD = "[PASS]", "[FAIL]"
# S substantive | V vacuous (entailed by the base sha256) | T tautological (readback of a
# write) | E ENTAILED BY A SIBLING ASSERTION already made in this same run (adversary C:
# an independent classification put 218 of the 347 "substantive" checks in this bucket --
# e.g. every per-table byte-identical check after "no byte outside the 4 regions changed").
_census = {"S": 0, "V": 0, "T": 0, "E": 0}
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


# ==================================================================================================
#  V850E2 ENCODER.  Every form below is POSITIVE-CONTROLLED at [1c] by re-encoding real instructions
#  already on the flown V282 image and asserting byte equality.  Nothing here is taken on trust.
# ==================================================================================================
OP1 = {"mov": 0x00, "jmp": 0x03, "mulh": 0x07, "or": 0x08, "subr": 0x0C, "sub": 0x0D,
       "add": 0x0E, "cmp": 0x0F}
OP2 = {"movi": 0x10, "addi": 0x12, "cmpi": 0x13, "shr": 0x14, "sar": 0x15, "shl": 0x16}
OP67 = {"movea": 0x31, "andi": 0x36, "ld.h": 0x39, "st.b": 0x3A, "st.h": 0x3B, "ld.hu": 0x3F}
COND = {"be": 0x2, "br": 0x5, "ble": 0x7, "bne": 0xA, "bge": 0xE}


def _hw(v):
    return struct.pack("<H", v & 0xFFFF)


def f1(mn, reg1, reg2):
    """Format I, 2 B: reg2[15:11] | op[10:5] | reg1[4:0].  Semantics: reg2 <- reg2 OP reg1."""
    return _hw((reg2 << 11) | (OP1[mn] << 5) | reg1)


def f2(mn, imm5, reg2):
    """Format II, 2 B: reg2[15:11] | op[10:5] | imm5[4:0]."""
    assert -16 <= imm5 <= 31
    return _hw((reg2 << 11) | (OP2[mn] << 5) | (imm5 & 0x1F))


def f67(mn, reg1, reg2, disp):
    """Format VI/VII, 4 B: reg2[15:11] | op[10:5] | reg1[4:0] ; hw2 = the 16-bit disp/imm field."""
    return _hw((reg2 << 11) | (OP67[mn] << 5) | reg1) + _hw(disp)


def ld_h(disp, base, dst):
    # TRAP (a): hw2 bit 0 selects ld.w.  An odd displacement silently widens the load to 32 bits.
    assert disp % 2 == 0, f"ld.h disp {disp:#x} must be EVEN (odd hw2 bit0 -> ld.w)"
    return f67("ld.h", base, dst, disp)


def st_h(src, disp, base):
    assert disp % 2 == 0, f"st.h disp {disp:#x} must be EVEN (odd hw2 bit0 -> st.w)"
    return f67("st.h", base, src, disp)


def mov_imm32(imm, reg1):
    """6-byte `mov imm32, reg1`.  Format VI with opcode field 0x31 (shared with movea) and reg2 == 0
    as the escape; the DESTINATION is the reg1 field, bits 4:0, not reg2.  Controls, all Ghidra-
    disassembled this session: 0x2A16C and 0x2A0EA `mov 0x7fffffff,r16` = 30 06 ff ff ff 7f
    (hw1 0x0630), 0x29E62 `mov 0x177001,r13` (hw1 0x062d), 0x29CFC `mov 0xc9a88,r16`."""
    return _hw((0 << 11) | (0x31 << 5) | reg1) + struct.pack("<i", imm if imm < (1 << 31) else imm - (1 << 32))


def ld_w(disp, base, dst):
    """32-bit load.  SAME opcode field as ld.h (0x39); hw2 bit 0 = 1 is what selects the word form.
    Controls: 0x2194A `ld.w -0x1514,gp,r14` = 2477edea and 0x29E5E `ld.w -0x6cf8,gp,r8` = 24470993,
    both Ghidra-disassembled.  The displacement must be EVEN -- bit 0 is the format flag, not disp[0]."""
    assert disp % 2 == 0, f"ld.w disp {disp:#x} must be EVEN (hw2 bit0 is the w-form flag)"
    return f67("ld.h", base, dst, (disp & 0xFFFE) | 1)


def ld_bu(disp, base, dst):
    # TRAP (b): disp bit 0 -> hw1 bit 5 (opcode field 0x3C even / 0x3D odd); hw2 bit 0 is a FIXED 1.
    hw1 = (dst << 11) | ((0x3C | (disp & 1)) << 5) | base
    return _hw(hw1) + _hw((disp & 0xFFFE) | 1)


def st_b(src, disp, base):
    return f67("st.b", base, src, disp)


def bcond(mn, disp):
    """Format III, 2 B: disp[8:4] in bits 15:11, 0b1011 in 10:7, disp[3:1] in 6:4, cond in 3:0."""
    assert disp % 2 == 0 and -256 <= disp <= 254, f"Bcond disp {disp} out of the 9-bit signed range"
    d = disp & 0x1FF
    return _hw(((d >> 4) << 11) | (0b1011 << 7) | (((d >> 1) & 0x7) << 4) | COND[mn])


def _fmt5(pc, target, lnk):
    """Format V, 4 B: lnk[15:11] | 0b11110[10:6] | disp[21:16] ; hw2 = disp[15:0] with bit 0 = 0.
    TRAP (c): shares bits 10:6 with ld.bu; hw2 bit 0 (here always 0) is the discriminator."""
    d = target - pc
    assert d % 2 == 0 and -(1 << 21) <= d < (1 << 21), f"Format-V disp22 out of range: {d:#x}"
    d &= 0x3FFFFF
    return _hw((lnk << 11) | (0x1E << 6) | ((d >> 16) & 0x3F)) + _hw(d & 0xFFFE)


def jr(pc, target):
    return _fmt5(pc, target, 0)


def jarl(pc, target, lnk):
    return _fmt5(pc, target, lnk)


def jr_target(pc, b4):
    """The INVERSE of jr(), written independently so [5] can check the displacement BOTH ways."""
    hw1, hw2 = struct.unpack_from("<HH", b4, 0)
    assert ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and (hw1 >> 11) == 0, "not a jr"
    d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
    if d & (1 << 21):
        d -= (1 << 22)
    return pc + d


# ==================================================================================================
#  GHIDRA CONTROL TABLE.  Every instruction FORM the two new caves emit, paired with a real address
#  in the ALREADY-ANALYSED stock program where the identical bytes sit, and the mnemonic GhidraMCP
#  `disassemble_bytes` (dry_run) returned there on 2026-09-07.  The new caves sit at 0xC4Bxx, which
#  is 0xFF in stock, so Ghidra cannot read them directly -- this is how the encoder gets an
#  INDEPENDENT DISASSEMBLER behind it instead of only my own decoder.  Asserted at [1d].
#  Each of these addresses is byte-identical in stock and in V282 (the check below reads V282).
# ==================================================================================================
def _GC():
    return [
        (0x29124, f67("ld.h", GP, R9, -0x69AE),        "ld.h  -0x69ae, gp, r9"),
        (0x2194A, ld_w(BUF_BYTE4_DISP, GP, 14),        "ld.w  -0x1514, gp, r14"),
        (0x29E5E, ld_w(-0x6CF8, GP, R8),               "ld.w  -0x6cf8, gp, r8"),
        (0x29D72, st_h(R16, SP_CELL_DISP, GP),         "st.h  r16, -0x6a32, gp"),
        (0x29942, f1("sub", R9, R16),                  "sub   r9, r16"),
        (0x2E08C, f1("add", R9, R16),                  "add   r9, r16"),
        (0x29D7A, f1("mov", R16, R6),                  "mov   r16, r6"),
        (0x6A59E, f2("sar", 4, R16),                   "sar   0x4, r16"),
        (0x14D46, f2("cmpi", 1, R6),                   "cmp   0x1, r6"),
        (0x149BC, bcond("bne", 8),                     "bne   0x000149c4   (+8)"),
        (0x1AFD0, bcond("be", 4),                      "be    0x0001afd4   (+4)"),
        (0x29D82, bcond("ble", 10),                    "ble   0x00029d8c   (+10)"),
        (0x1A4CC, f2("movi", 1, R16),                  "mov   0x1, r16"),
        (0x14D40, f2("movi", 1, R7),                   "mov   0x1, r7"),
        (0x14000, jr(0x14000, 0x14084),                "jr    0x00014084"),
        (0x55AD4, ld_bu(BUF_BYTE4_DISP, GP, R6),       "ld.bu -0x1514, gp, r6"),
        (0x55AE8, st_b(R6, BUF_BYTE4_DISP, GP),        "st.b  r6, -0x1514, gp"),
        (0x68728, f1("or", R7, R6),                    "or    r7, r6"),
        (0x152EC, f67("andi", R6, R6, 0x32),           "andi  0x32, r6, r6"),
        (0x14AAA, f1("jmp", LP, R0),                   "jmp   lp"),
        # --- forms the REV 2 prologue and the bit-5 rung add -----------------------------------
        (0x2A18C, f67("st.h", GP, R16, (EINIT_CELL_DISP & 0xFFFE) | 1),
                                                       "st.w  r16, -0x6cf8, gp"),
        (0x2A16C, mov_imm32(EINIT_SENTINEL, R16),      "mov   0x7fffffff, r16"),
        (0x2A0EA, mov_imm32(EINIT_SENTINEL, R16),      "mov   0x7fffffff, r16"),
        (0x29E62, mov_imm32(0x177001, R13),            "mov   0x177001, r13"),
        (0x29E68, mov_imm32(-0xBB800, R10),            "mov   0xfff44800, r10"),
        (0x29E50, f1("cmp", R13, R8),                  "cmp   r13, r8"),
        (0x2A1AC, f2("sar", 5, R9),                    "sar   0x5, r9"),
        (0x29096, bcond("bge", 4),                     "bge   0x0002909a   (+4)"),
        (0x1C1C2, f2("shl", 4, R7),                    "shl   0x4, r7"),
        (0x1708C, f2("movi", NEW_BIT_NIB, R7),         "mov   0x2, r7"),
    ]


# ==================================================================================================
#  THE CAVES.  Each entry is (address, bytes, mnemonic, comment).  Sizes are SUMMED, never assumed.
# ==================================================================================================
def filter_cave(k, at=FILT, ret=HOOK_RET):
    """The setpoint pre-filter.  Entered by `jr` from 0x29D72 with r16 = sp (the raw map output,
    a full 32-bit signed `mulh` product).  Leaves r16 = y[n] and returns to 0x29D76.

    LIVE-ACROSS-THE-HOOK REGISTERS, re-derived from the bytes at [1c] and Ghidra-confirmed:
        r10  loaded 0x29D6E (cal 0xC62E4), consumed 0x29D7E   -- MUST SURVIVE, never touched here
        r26  the rate feedback fb,          consumed 0x29D78   -- MUST SURVIVE, never touched here
        r16  the setpoint sp,               consumed 0x29D76   -- this cave replaces it with y[n]
        lp   not referenced in the window; `jr` (not `jarl`) leaves it alone
    DEAD SCRATCH (written before any read on EVERY path after 0x29D72):
        r6   next access is the WRITE `mov r16,r6` at 0x29D7A
        r9   next access is the WRITE `mov 0x0,r9` at 0x29D80
    PSW flags: the first flag consumer after the hook is `ble` @0x29D82, and `cmp r10,r6` @0x29D7E
    re-sets the flags before it, so clobbering PSW inside the cave is harmless.
    """
    # --- PROLOGUE (rev 2): the engage-init.  14 bytes, in r6/r9 (both dead), r16 untouched. -----
    pro = [
        (ld_w(EINIT_CELL_DISP, GP, R6), "ld.w  -0x6cf8[gp],r6",
         "r6 = Honda's shared-epilogue cell, as the PREVIOUS tick left it (hw2 bit0 SET = WORD form)"),
        (mov_imm32(EINIT_SENTINEL, R9), f"mov   0x{EINIT_SENTINEL:08x},r9",
         "the sentinel, materialised in full -- an EXACT 32-bit compare, not a top-nibble test, so"
         " there is no band of ordinary values that could ever be mistaken for it"),
        (f1("cmp", R9, R6),             "cmp   r9,r6", "marker == sentinel ?"),
        # `be` target is filled in below, once the body length is known -- it is the st.h
        (None,                          f"be    <st.h>",
         "YES -> the previous tick skipped this hook.  y := sp: r16 still holds RAW sp, so the"
         " store+reload+return below give a tick BYTE-IDENTICAL to V282."),
    ]
    # --- BODY: the filter proper.  Unchanged from rev 1. ----------------------------------------
    body = [
        (ld_h(SP_CELL_DISP, GP, R9),  "ld.h  -0x6a32[gp],r9", "r9 = y[n-1], sign-extended from the 16-bit cell"),
        (f1("sub", R9, R16),          "sub   r9,r16",         "r16 = d = sp - y[n-1]   (32-bit signed)"),
        (f1("mov", R16, R6),          "mov   r16,r6",         "r6 = d, saved for the zero test"),
        (f2("sar", k, R16),           f"sar   0x{k:x},r16",   f"r16 = step = d >> {k}  (ARITHMETIC: floors toward -inf)"),
        (f2("cmpi", 0, R16),          "cmp   0x0,r16",        "step == 0 ?"),
        (bcond("bne", 8),             "bne   +8",             "step != 0 -> no correction needed"),
        (f2("cmpi", 0, R6),           "cmp   0x0,r6",         "d == 0 ?"),
        (bcond("be", 4),              "be    +4",             "d == 0 -> converged, leave step at 0"),
        (f2("movi", 1, R16),          "mov   0x1,r16",        f"step = +1.  Reached ONLY for 0 < d < {1 << k}:"
                                                              " sar never rounds a NEGATIVE d to 0."),
        (f1("add", R9, R16),          "add   r9,r16",         "r16 = y[n] = y[n-1] + step"),
    ]
    # --- TAIL: shared by BOTH paths.  The `be` lands on the st.h. -------------------------------
    tail = [
        (st_h(R16, SP_CELL_DISP, GP), "st.h  r16,-0x6a32[gp]", "publish y[n] (replaces the displaced dead store)"
                                                               "  <-- the engage-init `be` lands HERE"),
        (ld_h(SP_CELL_DISP, GP, R16), "ld.h  -0x6a32[gp],r16", "r16 = y[n] read BACK, so the register and the"
                                                               " 16-bit cell can never diverge"),
    ]
    pro_len = sum(len(b) for b, _, _ in pro[:-1]) + 2          # +2 for the `be` itself
    store_at = at + pro_len + sum(len(b) for b, _, _ in body)
    be_pc = at + pro_len - 2
    pro[-1] = (bcond("be", store_at - be_pc), pro[-1][1], pro[-1][2])
    out, pc = [], at
    for by, mn, cm in pro + body + tail:
        out.append((pc, by, mn, cm))
        pc += len(by)
    assert pc == store_at + 8, (hex(pc), hex(store_at))
    out.append((pc, jr(pc, ret), f"jr    0x{ret:05x}", "resume at the untouched `shl 0x5,r16`"))
    return out


def telemetry_rung(at=TELE):
    """ONE new sign rung + the RELOCATED cave epilogue.  Entered by `jr` from 0xC4BD6, which is where
    the cave's `jmp [lp]` used to be.  r6/r7 are the cave's own scratch and are both dead on return
    (the caller does `mov 0x8,r7 ; movea 0x14a,r0,r8` at 0x55C12 immediately); r6 must come back
    holding the buffer base, which the relocated `movea` restores.  lp is untouched.
    Rung shape is the existing sign(r24) rung's, with the `shl 0x4` dropped because the target is bit 0.
    """
    seq = [
        (f2("movi", 0, R7),                     "mov   0x0,r7",          "default: bit clear"),
        (ld_h(SP_CELL_DISP, GP, R6),            "ld.h  -0x6a32[gp],r6",  "r6 = y[n] = the filtered setpoint"),
        (f2("cmpi", 0, R6),                     "cmp   0x0,r6",          ""),
        (bcond("bge", 4),                       "bge   +4",              "y >= 0 -> leave the bit clear"),
        (f2("movi", NEW_BIT_NIB, R7),           f"mov   0x{NEW_BIT_NIB:x},r7", "y < 0 -> 2, which the shl makes bit 5"),
        (f2("shl", 4, R7),                      "shl   0x4,r7",          f"r7 = 0x{NEW_BIT:02x} or 0 -- the flown"
                                                                         " rungs' own bit-building idiom"),
        (ld_bu(BUF_BYTE4_DISP, GP, R6),         "ld.bu -0x1514[gp],r6",  "read 0x14A byte 4"),
        (f67("andi", R6, R6, NEW_BIT_MASK),     f"andi  0x{NEW_BIT_MASK:x},r6,r6",
                                                "clear ONLY bit 5 -- preserves STOCK bits 0-2 and ours 7,6,4,3"),
        (f1("or", R7, R6),                      "or    r7,r6",           ""),
        (st_b(R6, BUF_BYTE4_DISP, GP),          "st.b  r6,-0x1514[gp]",  "write 0x14A byte 4 back; runs AFTER the"
                                                                         " flown bit-5 rung, so it wins the race"),
        (f67("movea", GP, R6, BUF_BASE_DISP),   "movea -0x1518,gp,r6",   "RELOCATED epilogue: r6 = buffer base"),
        (f1("jmp", LP, R0),                     "jmp   [lp]",            "RELOCATED epilogue: return"),
    ]
    out, pc = [], at
    for by, mn, cm in seq:
        out.append((pc, by, mn, cm))
        pc += len(by)
    return out


# ==================================================================================================
#  THE PYTHON MIRROR of the cave arithmetic.  Integer-exact, one line per cave instruction, each
#  annotated with the address of the instruction it mirrors.  V850 `sar` and Python `>>` both floor
#  toward -infinity on negative operands, so this is EXACT, not approximate.
# ==================================================================================================
def _s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def sp_filter_tick(sp, y_prev, k, marker=0):
    """y[n] from sp, y[n-1] and Honda's shared-epilogue cell.  Mirrors the cave instruction for
    instruction; addresses are for the K=4 layout (FILT = 0xC4C00).  `marker` is gp-0x6cf8 as the
    PREVIOUS tick left it: 0x7FFFFFFF after any hook-skipping tick, otherwise that tick's E.
    Returns r16 as handed back to 0x29D76.

    🛑 THE PER-LINE ADDRESSES BELOW ARE CHECKED AGAINST THE EMITTED LAYOUT at [4c].  They drifted
    once already -- they were left at rev 1's 0xC4BDC.. after the cave moved to 0xC4C00 -- so the
    assertion exists to stop a stale mirror ever being read as a description of the built code."""
    r6 = _s32(marker)                 # 0xC4C00 ld.w  -0x6cf8[gp],r6
    r9 = _s32(EINIT_SENTINEL)         # 0xC4C04 mov   0x7fffffff,r9
    if r6 != r9:                      # 0xC4C0A cmp r9,r6 ; 0xC4C0C be <st.h>  (NOT taken -> filter)
        r9 = y_prev                   # 0xC4C0E ld.h  -0x6a32[gp],r9
        r16 = sp - r9                 # 0xC4C12 sub   r9,r16            -> d
        r6 = r16                      # 0xC4C14 mov   r16,r6
        r16 = r16 >> k                # 0xC4C16 sar   K,r16             -> step (arithmetic, floors)
        if r16 == 0:                  # 0xC4C18 cmp   0x0,r16
            if r6 != 0:               # 0xC4C1C cmp   0x0,r6   (reached only when step == 0)
                r16 = 1               # 0xC4C20 mov   0x1,r16  (reached only when 0 < d < 2^K)
        r16 = r16 + r9                # 0xC4C22 add   r9,r16            -> y[n]
    else:
        r16 = sp                      # the `be` path: r16 was NEVER touched, it still holds RAW sp
    cell = r16 & 0xFFFF               # 0xC4C24 st.h  r16,-0x6a32[gp]   (low 16 bits only)
    r16 = cell - 0x10000 if cell & 0x8000 else cell   # 0xC4C28 ld.h back, sign-extended
    return r16                        # 0xC4C2C jr 0x29d76


def response(k, fs=TICK_HZ):
    """The linear small-signal response of y[n] = a*y[n-1] + (1-a)*sp[n], a = 1 - 2^-k."""
    a = 1.0 - 2.0 ** -k

    def H(f):
        w = 2 * math.pi * f / fs
        return (1 - a) / abs(complex(1.0, 0.0) - a * complex(math.cos(w), -math.sin(w)))
    lo, hi = 1e-3, fs / 2
    for _ in range(200):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if H(m) > 2 ** -0.5 else (lo, m)
    return dict(a=a, fc=lo, h3=H(3.0), h20=H(20.0), h40=H(40.0),
                tau_ms=-1000.0 / (fs * math.log(a)), gd_ms=1000.0 * (a / (1 - a)) / fs, kick=2 ** k)


# ==================================================================================================
#  GATE 1 -- the gp-0x6a32 census.  Raw little-endian scan, POSITIVE-CONTROLLED before its null counts.
# ==================================================================================================
def gp_census(img, disp, controls):
    """Return (hits, control_hits).  `hits` = every gp-relative access to `disp`, by ANY width, in
    BOTH the 4-byte disp16 form and the 6-byte extended-displacement form, plus any absolute
    materialisation of the cell.  `controls` is a dict {disp: expected_count} scanned identically --
    if a control's count is wrong the whole scan is void (firmware-decompile: control every null)."""
    def scan(d):
        out = []
        for a in range(START, END - 6, 2):
            hw1 = struct.unpack_from("<H", img, a)[0]
            op, reg1 = (hw1 >> 5) & 0x3F, hw1 & 0x1F
            if reg1 != GP:
                continue
            hw2 = struct.unpack_from("<H", img, a + 2)[0]
            eff = None
            if op in (0x38, 0x3A, 0x31, 0x36, 0x30, 0x32, 0x33, 0x34, 0x35, 0x37):
                eff = hw2                                   # raw 16-bit field
            elif op in (0x39, 0x3B, 0x3F):
                if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0:
                    continue                                # Format V jr/jarl, not a load  (TRAP c)
                eff = hw2 & 0xFFFE                          # ld.h/ld.w/st.h/st.w/ld.hu     (TRAP a)
            elif op in (0x3C, 0x3D):
                if (hw2 & 1) == 0:
                    continue                                # Format V, not ld.bu           (TRAP c)
                eff = (hw2 & 0xFFFE) | (op & 1)             # ld.bu bit-5 steal             (TRAP b)
            if eff is None:
                continue
            eff = eff - 0x10000 if eff & 0x8000 else eff
            if eff == d and op in (0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F):
                out.append((a, op))
        return out

    hits = scan(disp)
    ctl = {d: len(scan(d)) for d in controls}
    # ABSOLUTE-ADDRESS ROUTE: a `movhi hi,rX,rD` that materialises the page, PAIRED within 16 bytes
    # with an instruction that applies the LOW half 0x15CE off rD (movea / addi / any ld / any st).
    # Counting bare `movhi 0xFEDF` alone is useless -- 0xFEDF is the whole RAM page and appears
    # hundreds of times.  The pairing is what makes the null mean something.
    abs_addr = (GP_BASE + disp) & 0xFFFFFFFF
    hi, lo = (abs_addr >> 16) & 0xFFFF, abs_addr & 0xFFFF
    if lo & 0x8000:
        hi = (hi + 1) & 0xFFFF          # movea/ld/st sign-extend the low half
    movhi_page, movhi = 0, []
    for a in range(START, END - 20, 2):
        h1 = struct.unpack_from("<H", img, a)[0]
        if ((h1 >> 5) & 0x3F) != 0x32 or struct.unpack_from("<H", img, a + 2)[0] != hi:
            continue
        movhi_page += 1
        dst = h1 >> 11
        for j in range(4, 20, 2):
            h1b = struct.unpack_from("<H", img, a + j)[0]
            h2b = struct.unpack_from("<H", img, a + j + 2)[0]
            opb = (h1b >> 5) & 0x3F
            if (h1b & 0x1F) == dst and opb >= 0x30 and (h2b & 0xFFFE) == (lo & 0xFFFE):
                movhi.append((a, a + j))
                break
    lit = [a for a in range(START, END - 4, 2) if struct.unpack_from("<I", img, a)[0] == abs_addr]
    return hits, ctl, movhi, lit, movhi_page


# ==================================================================================================
def independent_rebuild(base, k):
    """A SECOND implementation with none of build()'s bookkeeping and none of its tables: it re-derives
    the encodings from scratch with literal opcode arithmetic, patches, and re-CRCs via FF.crc_block_map.
    Shares only the module-level addresses and K -- deliberately not the cave builders above."""
    img = bytearray(base)

    def hw(v):
        return struct.pack("<H", v & 0xFFFF)

    def fmt5(pc, tgt, lnk=0):
        d = (tgt - pc) & 0x3FFFFF
        return hw((lnk << 11) | (0x1E << 6) | ((d >> 16) & 0x3F)) + hw(d & 0xFFFE)

    def bc(cond, d):
        dd = d & 0x1FF
        return hw(((dd >> 4) << 11) | (0xB << 7) | (((dd >> 1) & 7) << 4) | cond)

    D = SP_CELL_DISP & 0xFFFF
    M = EINIT_CELL_DISP & 0xFFFF
    body = b"".join([
        hw((9 << 11) | (0x39 << 5) | 4) + hw(D),          # ld.h  -0x6a32[gp],r9
        hw((16 << 11) | (0x0D << 5) | 9),                 # sub   r9,r16
        hw((6 << 11) | (0x00 << 5) | 16),                 # mov   r16,r6
        hw((16 << 11) | (0x15 << 5) | k),                 # sar   k,r16
        hw((16 << 11) | (0x13 << 5) | 0),                 # cmp   0,r16
        bc(0xA, 8),                                       # bne   +8
        hw((6 << 11) | (0x13 << 5) | 0),                  # cmp   0,r6
        bc(0x2, 4),                                       # be    +4
        hw((16 << 11) | (0x10 << 5) | 1),                 # mov   1,r16
        hw((16 << 11) | (0x0E << 5) | 9),                 # add   r9,r16
    ])
    pro = b"".join([
        hw((6 << 11) | (0x39 << 5) | 4) + hw(M | 1),      # ld.w  -0x6cf8[gp],r6   (bit0 = word form)
        hw((0 << 11) | (0x31 << 5) | 9) + struct.pack("<i", EINIT_SENTINEL),   # mov 0x7fffffff,r9
        hw((6 << 11) | (0x0F << 5) | 9),                  # cmp   r9,r6
        bc(0x2, 2 + len(body)),                           # be    <st.h>
    ])
    filt = pro + body + b"".join([
        hw((16 << 11) | (0x3B << 5) | 4) + hw(D),         # st.h  r16,-0x6a32[gp]
        hw((16 << 11) | (0x39 << 5) | 4) + hw(D),         # ld.h  -0x6a32[gp],r16
    ])
    filt += fmt5(FILT + len(filt), HOOK_RET)
    B4 = BUF_BYTE4_DISP & 0xFFFF
    tele = b"".join([
        hw((7 << 11) | (0x10 << 5) | 0),                  # mov   0,r7
        hw((6 << 11) | (0x39 << 5) | 4) + hw(D),          # ld.h  -0x6a32[gp],r6
        hw((6 << 11) | (0x13 << 5) | 0),                  # cmp   0,r6
        bc(0xE, 4),                                       # bge   +4
        hw((7 << 11) | (0x10 << 5) | NEW_BIT_NIB),        # mov   2,r7
        hw((7 << 11) | (0x16 << 5) | 4),                  # shl   0x4,r7   -> 0x20
        hw((6 << 11) | (0x3C << 5) | 4) + hw(B4 | 1),     # ld.bu -0x1514[gp],r6
        hw((6 << 11) | (0x36 << 5) | 6) + hw(NEW_BIT_MASK),      # andi 0xdf,r6,r6
        hw((6 << 11) | (0x08 << 5) | 7),                  # or    r7,r6
        hw((6 << 11) | (0x3A << 5) | 4) + hw(B4),         # st.b  r6,-0x1514[gp]
        hw((6 << 11) | (0x31 << 5) | 4) + hw(BUF_BASE_DISP & 0xFFFF),   # movea -0x1518,gp,r6
        hw((0 << 11) | (0x03 << 5) | 31),                 # jmp   [lp]
    ])
    touched = set()
    for at, blob in ((HOOK_SP, fmt5(HOOK_SP, FILT)), (FILT, filt),
                     (CAVE_JMP_LP, fmt5(CAVE_JMP_LP, TELE)), (TELE, tele)):
        img[at:at + len(blob)] = blob
        touched |= set(range(at, at + len(blob)))
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


# ==================================================================================================
def build():
    R = response(K_SHIFT)
    print("=" * 112)
    print(f"  V288 -- V282 + a FIRST-ORDER LAG on the LKAS rate-PID SETPOINT (K = {K_SHIFT}), in a new"
          f" code cave, + 1 telemetry bit.")
    print(f"  f_c {R['fc']:.2f} Hz | |H| 3 Hz {R['h3']:.3f} / 20 Hz {R['h20']:.3f} / 40 Hz {R['h40']:.3f}"
          f" | tau {R['tau_ms']:.1f} ms | group delay {R['gd_ms']:.1f} ms | first-tick kick /{R['kick']}")
    print("=" * 112)
    print("\n  [0] THE DOSE LADDER -- one constant, K_SHIFT, selects it; nothing else in this file changes")
    print("      K   pole a    f_c        |H|3Hz  |H|20Hz  |H|40Hz   tau       group delay   kick")
    for k_ in (3, 4, 5):
        r_ = response(k_)
        mark = "  <-- BUILT" if k_ == K_SHIFT else ("  (confirmed dose)" if k_ == DOSE_CONFIRMED_K else "")
        print(f"      {k_}   {r_['a']:.5f}   {r_['fc']:6.2f} Hz   {r_['h3']:.3f}   {r_['h20']:.3f}"
              f"    {r_['h40']:.3f}   {r_['tau_ms']:5.1f} ms   {r_['gd_ms']:5.1f} ms      x1/{r_['kick']}{mark}")
    w = WIRE_STUDY_K4
    print(f"\n      WIRE STUDY's pricing of K=4 (quoted, NOT recomputed here -- {w['source']}):")
    print(f"        command content 18-22 Hz  x{w['band_18_22_hz']:.3f}"
          f"   |   per-tick D kick  x{w['per_tick_d_kick']:.3f}"
          f"   |   D-rail duty in episodes  {w['d_rail_duty_before'] * 100:.2f}%"
          f" -> {w['d_rail_duty_after'] * 100:.2f}%")
    if K_SHIFT != DOSE_CONFIRMED_K:
        print(f"\n      NOTE: building K={K_SHIFT}, which is NOT the confirmed dose"
              f" (K={DOSE_CONFIRMED_K}).  The output names carry K{K_SHIFT}, so this cannot be"
              " confused with the confirmed build on disk.")
    # VACUOUS by construction: TAG is an f-string built from K_SHIFT a few lines above, so this can
    # only fail if that f-string is edited.  Kept as a tripwire on the NAME, bucketed V, not S.
    check(f"SPFILT.K{K_SHIFT}" in TAG, f"the output name carries the dose (K{K_SHIFT}), so two doses"
                                       " can never collide on disk", "V")

    # ------------------------------------------------------------------------------------------
    print("\n  [1] BASE = V282")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V282 base sha256 matches", "S")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and tuple(X7) == LIVE_KP_X
          and tuple(Y7) == LIVE_KP_Y, f"base live Kp slot {LIVE_SLOT} == V281 rev 3 flat-248", "V")
    check(bytes(base[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, "base 0x55C0E == jarl 0xc4b34,lp", "V")

    print("\n  [1b] THE HOOK SITE AND THE 0x14A CAVE, AS FOUND")
    check(bytes(base[HOOK_SP:HOOK_SP + 4]) == HOOK_SP_OLD,
          f"0x{HOOK_SP:05X} == {HOOK_SP_OLD.hex()} = st.h r16,-0x6a32,gp (4 bytes, same length as a jr)", "V")
    check(bytes(base[CAVE_JMP_LP:CAVE_JMP_LP + 2]) == CAVE_JMP_LP_OLD,
          f"0x{CAVE_JMP_LP:05X} == {CAVE_JMP_LP_OLD.hex()} = jmp [lp], the 0x14A cave's single exit", "V")
    check(bytes(base[CAVE_EPILOGUE:CAVE_EPILOGUE + 4]) == f67("movea", GP, R6, BUF_BASE_DISP),
          f"0x{CAVE_EPILOGUE:05X} == movea -0x1518,gp,r6 (the buffer base the caller consumes)", "V")
    # which byte-4 bits do the EXISTING rungs write?  Read it off their andi masks, not off the doc.
    masks = [(a, u16(base, a + 2)) for a in range(CAVE_START, CAVE_END - 4)
             if bytes(base[a:a + 2]) == f67("andi", R6, R6, 0)[:2]
             and bytes(base[a + 4:a + 8])[:2] == f1("or", R7, R6) + b""[:0]]
    b4_masks = [(a, m) for a, m in masks
                if bytes(base[a + 6:a + 10]) == st_b(R6, BUF_BYTE4_DISP, GP)]
    written = 0
    for a, m in b4_masks:
        written |= (~m) & 0xFF
    print(f"      byte-4 andi masks found IN THE CAVE: {[(hex(a), hex(m)) for a, m in b4_masks]}")
    check(len(b4_masks) == 3, f"exactly 3 CAVE rungs write 0x14A byte 4 (found {len(b4_masks)})", "V")
    check(written == 0xF8, f"the cave's rungs write byte-4 bits {written:#04x} = 7,6,5,4,3", "V")

    print("\n  [1b2] THE BITS THE CAVE DOES *NOT* OWN -- rev 1's FAIL A, re-derived from the image")
    print("       Rev 1 concluded 'bits 2-0 are free' from the CAVE's masks alone.  That census was")
    print("       incomplete: the STOCK FRAME BUILDER writes bits 2, 1 and 0 before the cave runs.")
    for a, want in STOCK_B4_WRITERS.items():
        check(bytes(base[a:a + 4]) == want,
              f"0x{a:05X} == {want.hex()} = st.b rX,-0x1514,gp -- a STOCK writer of 0x14A byte 4", "V")
    for a, m in STOCK_B4_MASKS.items():
        check(u16(base, a + 2) == m,
              f"0x{a:05X} andi 0x{m:02x} -- the stock rung clears exactly bit {(~m & 0xFF).bit_length() - 1}", "V")
    stock_bits = 0
    for m in STOCK_B4_MASKS.values():
        stock_bits |= (~m) & 0xFF
    check(stock_bits == STOCK_B4_BITS,
          f"the stock frame builder owns byte-4 bits {stock_bits:#04x} = 2,1,0 -- NOT free, rev 1 was WRONG", "S")
    check(all(a < CAVE_HOOK for a in STOCK_B4_WRITERS),
          f"all three stock writers run BEFORE the cave hook 0x{CAVE_HOOK:05X}, so a cave rung that"
          " cleared one of their bits would silently win and corrupt a live CAN flag", "S")
    check(stock_bits & written == 0,
          "stock bits 2-0 and cave bits 7-3 partition byte 4 with no overlap -- the flown cave has"
          " never touched a stock bit (masks 0xBF/0xDF/0x67 all preserve bits 2-0)", "S")
    check(NEW_BIT == 0x20 and NEW_BIT & stock_bits == 0 and NEW_BIT & written == NEW_BIT,
          f"REV 2's bit {NEW_BIT:#04x} is bit 5 -- one the CAVE already owns, not a stock bit", "S")
    check(NEW_BIT_MASK & STOCK_B4_BITS == STOCK_B4_BITS,
          f"the new rung's mask {NEW_BIT_MASK:#04x} PRESERVES every stock bit (2,1,0)", "S")
    check(NEW_BIT_MASK | 0xF8 == 0xFF and (~NEW_BIT_MASK & 0xFF) == NEW_BIT,
          f"the new rung's mask clears bit 5 and NOTHING else", "S")

    print("\n  [1c] ENCODER POSITIVE CONTROL -- re-encode code ALREADY ON THE CAR and demand byte equality")
    hook_re = (f1("mov", R8, R16) + f1("mulh", R13, R16) + f67("ld.hu", TP, R10, IPATH_CLAMP_TP | 1)
               + st_h(R16, SP_CELL_DISP, GP) + f2("shl", 5, R16) + f1("sub", R26, R16)
               + f1("mov", R16, R6) + f2("sar", 5, R6) + f1("cmp", R10, R6)
               + f2("movi", 0, R9) + bcond("ble", 0x29D8C - 0x29D82))
    check(hook_re == bytes(base[HOOK_WINDOW[0]:HOOK_WINDOW[1]]),
          f"the WHOLE hook window 0x{HOOK_WINDOW[0]:05X}-0x{HOOK_WINDOW[1] - 1:05X} re-encodes byte-identically"
          " (mov/mulh/ld.hu/st.h/shl/sub/sar/cmp/movi/Bcond all controlled)", "S")

    def sgn(cell):
        return ld_h(cell, GP, R6) + f2("cmpi", 0, R6) + bcond("bge", 4) + f1("subr", R0, R6)

    def cmprung(a_, b_, bit):
        return (sgn(a_) + f1("mov", R6, R7) + sgn(b_) + f1("cmp", R6, R7) + f2("movi", bit, R7)
                + bcond("bge", 4) + f2("movi", 0, R7) + f2("shl", 4, R7)
                + ld_bu(BUF_BYTE4_DISP, GP, R6) + f67("andi", R6, R6, 0xFF & ~(bit << 4))
                + f1("or", R7, R6) + st_b(R6, BUF_BYTE4_DISP, GP))
    cave_re = (cmprung(-0x6ADA, -0x6B38, 4) + cmprung(-0x6ADA, -0x6B94, 2)
               + f2("movi", 0, R7)
               + ld_h(-0x6B4C, GP, R6) + f2("cmpi", 0, R6) + bcond("bge", 4) + f2("addi", 8, R7)
               + ld_h(-0x6ADA, GP, R6) + f2("cmpi", 0, R6) + bcond("bge", 4) + f2("addi", 1, R7)
               + f2("shl", 4, R7)
               + f67("ld.h", GP, R6, (-0x3680) | 1) + f2("cmpi", 0, R6) + bcond("bge", 4)
               + f2("addi", 8, R7)
               + ld_bu(BUF_BYTE4_DISP, GP, R6) + f67("andi", R6, R6, 0x67) + f1("or", R7, R6)
               + st_b(R6, BUF_BYTE4_DISP, GP)
               + f2("movi", 3, R7) + f2("shl", 6, R7)
               + ld_bu(-0x1511, GP, R6) + f67("andi", R6, R6, 0x3F) + f1("or", R7, R6)
               + st_b(R6, -0x1511, GP)
               + f67("movea", GP, R6, BUF_BASE_DISP) + f1("jmp", LP, R0))
    check(len(cave_re) == CAVE_END - CAVE_START and cave_re == bytes(base[CAVE_START:CAVE_END]),
          f"the WHOLE {CAVE_END - CAVE_START}-byte 0x14A cave re-encodes byte-identically -- ld.h/ld.w"
          " (hw2 bit0), ld.bu (hw1 bit5 + hw2 bit0), andi/or/st.b/movea/jmp[lp] ALL controlled", "S")
    check(jarl(CAVE_HOOK, CAVE_START, LP) == bytes(base[CAVE_HOOK:CAVE_HOOK + 4]),
          "Format-V control: the flown `jarl 0xc4b34,lp` @0x55C0E re-encodes byte-identically", "S")
    nfv = okfv = 0
    for a in range(START, END - 6, 2):
        hw1, hw2 = struct.unpack_from("<HH", base, a)
        if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and hw1 != 0xFFFF:
            d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
            d -= (1 << 22) if d & (1 << 21) else 0
            nfv += 1
            okfv += (_fmt5(a, a + d, hw1 >> 11) == bytes(base[a:a + 4]))
    check(okfv == nfv and nfv > 5000,
          f"Format-V disp22 encode/decode round trip on all {nfv} sites in the image ({okfv} match)", "S")

    print("\n  [1d] GHIDRA CONTROL -- every instruction FORM the new caves emit, disassembled by Ghidra")
    print("       on the STOCK program at a real analysed address, and re-encoded here to the same bytes.")
    print("       (The new caves live at 0xC4Bxx, which is 0xFF in stock, so this is how the forms get an")
    print("        independent disassembler behind them rather than only my own decoder.)")
    for addr, enc, ghidra in _GC():
        got = bytes(base[addr:addr + len(enc)])
        check(got == enc, f"0x{addr:05X}  {got.hex():<8}  Ghidra says `{ghidra}` ; encoder agrees", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [2] GATE 1 -- RAM OWNERSHIP of gp-0x6a32 (0x%08X), controlled census" % SP_CELL_ABS)
    hits, ctl, movhi, lit, movhi_page = gp_census(bytes(base), SP_CELL_DISP,
                                                  {-0x6ADA: 3, -0x6B38: 1, -0x1514: 4, -0x6B94: 1})
    for d, n in sorted(ctl.items()):
        print(f"      control gp{d:+#07x}: {n} hits")
    check(ctl[-0x6ADA] >= 3 and ctl[-0x1514] >= 4 and ctl[-0x6B38] >= 1,
          "POSITIVE CONTROL: the scanner finds the cave's own known gp accesses (r24 x3, byte4 x4, T x1)"
          " -- its null on other cells is therefore worth something", "S")
    for a, op in hits:
        print(f"      0x{a:05X}  opfield 0x{op:02X} ({'st.h' if op == 0x3B else 'other'})  reg2=r{u16(base, a) >> 11}")
    check(len(hits) == 2, f"exactly 2 gp-relative accesses to gp-0x6a32 image-wide (got {len(hits)})", "S")
    check(sorted(a for a, _ in hits) == [HOOK_SP, 0x2AC68],
          "they are 0x29D72 (the live hook) and 0x2AC68 (inside the unreachable duplicate PID copy)", "S")
    check(all(op == 0x3B for _, op in hits), "BOTH are st.h -- WRITERS.  ZERO readers image-wide", "S")
    check(not movhi and not lit,
          f"no movhi/low-half PAIR materialises 0x{SP_CELL_ABS:08X} and no dword literal of it exists"
          f" ({len(movhi)}/{len(lit)} hits; {movhi_page} bare `movhi 0x{(SP_CELL_ABS >> 16):04X}` sites"
          " exist, which is just the RAM page and is why the pairing test is the one that counts)", "S")
    print("      GATE 1 PASS: reusing an existing dead cell adds no writer and no reader any other")
    print("      function can see.  RESIDUAL, stated honestly [BELIEF, not EVIDENCE]: a static scan")
    print("      cannot see a fully register-indirect access built from an arbitrary base already in a")
    print("      register.  What it CAN say is that no code constructs this address, no code holds it")
    print("      as a literal, and the only two gp-relative accesses are both stores.")

    print("\n  [2b] the hook site is on STRAIGHT-LINE code -- nothing branches into it")
    intos = []
    for a in range(START, END - 6, 2):
        hw1, hw2 = struct.unpack_from("<HH", base, a)
        if ((hw1 >> 7) & 0xF) == 0xB and ((hw1 >> 5) & 0x3F) < 0x30:
            d = ((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1)
            d -= 0x200 if d & 0x100 else 0
            if a + d in (HOOK_SP, HOOK_SP + 2, HOOK_RET):
                intos.append((a, "Bcond"))
        if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and hw1 != 0xFFFF:
            d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
            d -= (1 << 22) if d & (1 << 21) else 0
            if a + d in (HOOK_SP, HOOK_SP + 2, HOOK_RET):
                intos.append((a, "Format V"))
    check(not intos, f"no Bcond and no jr/jarl in the image targets 0x{HOOK_SP:05X}, +2, or the return"
                     f" point 0x{HOOK_RET:05X} ({intos}) -- the 4-byte hook cannot be entered mid-instruction", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [2c] THE ENGAGE-INIT PREMISE -- re-derived here, not relayed")
    check(bytes(base[EINIT_EPILOGUE_ST:EINIT_EPILOGUE_ST + 4])
          == f67("st.h", GP, R16, (EINIT_CELL_DISP & 0xFFFE) | 1),
          f"0x{EINIT_EPILOGUE_ST:05X} == st.w r16,-0x6cf8,gp (hw2 0x9309, bit 0 SET = word form)", "V")
    check(bytes(base[EINIT_READER:EINIT_READER + 4]) == ld_w(EINIT_CELL_DISP, GP, R8),
          f"0x{EINIT_READER:05X} == ld.w -0x6cf8,gp,r8 -- Honda's own reader, and it sits AFTER our"
          f" hook 0x{HOOK_SP:05X} in tick order, so we read the PREVIOUS tick's value", "V")
    for a in EINIT_SENTINEL_SITES:
        check(bytes(base[a:a + 6]) == f2("movi", 0, R16)[:0] + b"\x30\x06" + struct.pack("<I", EINIT_SENTINEL),
              f"0x{a:05X} == mov 0x7fffffff,r16 -- a sentinel load on a hook-skipping route", "V")
    n_sent = sum(1 for a in range(START, END - 6, 2)
                 if bytes(base[a:a + 2]) == b"\x30\x06"
                 and struct.unpack_from("<I", base, a + 2)[0] == EINIT_SENTINEL)
    check(n_sent == len(EINIT_SENTINEL_SITES),
          f"exactly {len(EINIT_SENTINEL_SITES)} `mov 0x7fffffff,r16` sites image-wide (got {n_sent}) --"
          " no third route can plant the sentinel", "S")
    # 🛑 0x2A164 is a SHARED epilogue.  Positive-controlled branch scan: the two known jr must appear.
    ent = {"jr": [], "br": []}
    for a in range(START, END - 6, 2):
        hw1, hw2 = struct.unpack_from("<HH", base, a)
        if ((hw1 >> 7) & 0xF) == 0xB and ((hw1 >> 5) & 0x3F) < 0x30:
            d = ((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1)
            d -= 0x200 if d & 0x100 else 0
            if 0x2A160 <= a + d <= 0x2A1B4:
                ent["br"].append((a, a + d))
        if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and hw1 != 0xFFFF:
            d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
            d -= (1 << 22) if d & (1 << 21) else 0
            if 0x2A160 <= a + d <= 0x2A1B4:
                ent["jr"].append((a, a + d))
    print(f"      entries into 0x2A160-0x2A1B4:  jr {[(hex(a), hex(t)) for a, t in ent['jr']]}")
    print(f"                                     br {[(hex(a), hex(t)) for a, t in ent['br']]}")
    check(sorted(a for a, _ in ent["jr"]) == [0x29A5C, 0x29A64],
          "POSITIVE CONTROL: the scan finds both known `jr 0x2a164` (0x29A5C, 0x29A64)", "S")
    check(all(t == 0x2A164 for _, t in ent["jr"]),
          "both jr entries land on 0x2A164, the head of the reset constants", "S")
    to_shared = [a for a, t in ent["br"] if t == EINIT_SHARED_ENTRY]
    into_consts = [(a, t) for a, t in ent["br"] + ent["jr"] if 0x2A164 < t <= 0x2A173]
    check(sorted(to_shared) == [0x2A14A, 0x2A15E, 0x2A162] and not into_consts,
          f"3 conditional-path `br` (0x2A14A, 0x2A15E, 0x2A162) enter at 0x{EINIT_SHARED_ENTRY:05X},"
          " ONE INSTRUCTION PAST the reset constants, and nothing enters the constants' interior"
          f" ({into_consts}) -- so 0x2A164 is a SHARED EPILOGUE, gp-0x6cf8 is written EVERY tick,"
          " and the sentinel is transient rather than a latch.  That is what makes the init fire"
          " exactly once per re-engage.", "S")
    # the one remaining in-window branch, 0x2A154 -> 0x2A160, is INTERNAL: 0x2A160 is `sxh r12`
    # followed by `br 0x2a174`, so it too reaches the shared entry without touching the constants.
    others = [(a, t) for a, t in ent["br"] if t != EINIT_SHARED_ENTRY]
    check(others == [(0x2A154, 0x2A160)]
          and bytes(base[0x2A160:0x2A162]) == bytes.fromhex("ec00")
          and bytes(base[0x2A162:0x2A164]) == bcond("br", EINIT_SHARED_ENTRY - 0x2A162),
          f"the only other in-window branch is 0x2A154 -> 0x2A160, and 0x2A160 is `sxh r12` +"
          f" `br 0x{EINIT_SHARED_ENTRY:05X}` -- internal, and it also skips the reset constants", "S")
    check(E_MAX_BOUND < EINIT_SENTINEL,
          f"|E| can never equal the sentinel: max |E| = 32*1128 + 46080 = {E_MAX_BOUND}, the sentinel"
          f" is 0x{EINIT_SENTINEL:08X} = {EINIT_SENTINEL} ({EINIT_SENTINEL // E_MAX_BOUND}x larger)", "S")
    # and the r16 that the epilogue stores IS the sentinel on a skip route -- nothing rewrites r16
    # between either `mov 0x7fffffff,r16` and the store at 0x2A18C.  Linear scan of both spans.
    for lo_ in EINIT_SENTINEL_SITES:
        clob = []
        pc_ = lo_ + 6
        while pc_ < EINIT_EPILOGUE_ST:
            h1 = u16(base, pc_)
            op_, r2_ = (h1 >> 5) & 0x3F, h1 >> 11
            n_ = 2 if op_ <= 0x17 or ((h1 >> 7) & 0xF) == 0xB else (6 if op_ == 0x31 and r2_ == 0 else 4)
            writes = (op_ <= 0x17 and op_ not in (0x03, 0x0B, 0x0F, 0x13)) or op_ in (
                0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3C, 0x3D, 0x3F)
            if writes and r2_ == R16 and ((h1 >> 7) & 0xF) != 0xB:
                clob.append(hex(pc_))
            pc_ += n_
        check(not clob,
              f"no instruction between the sentinel load at 0x{lo_:05X} and the epilogue store at"
              f" 0x{EINIT_EPILOGUE_ST:05X} rewrites r16 ({clob}) -- so the sentinel really is what"
              " gets stored on that skip route", "S")

    print("\n  [3] FREE FLASH -- re-read directly, not inherited")
    ff_end = FREE_LO
    while base[ff_end] == 0xFF:
        ff_end += 1
    check(ff_end == FREE_HI, f"0xFF run 0x{FREE_LO:05X}-0x{ff_end - 1:05X} = {ff_end - FREE_LO} bytes"
                             f" (expected end 0x{FREE_HI:05X})", "V")
    check(bytes(base[STRUCT_LO:STRUCT_HI]).hex() == "010101010000c60013 00b200".replace(" ", ""),
          f"the 12 non-FF bytes at 0x{STRUCT_LO:05X} are the known structure -- left untouched", "V")

    filt = filter_cave(K_SHIFT)
    tele = telemetry_rung()
    filt_bytes = b"".join(by for _, by, _, _ in filt)
    tele_bytes = b"".join(by for _, by, _, _ in tele)
    f_lo, f_hi = FILT, FILT + len(filt_bytes)
    t_lo, t_hi = TELE, TELE + len(tele_bytes)
    print(f"\n      FILTER CAVE  0x{f_lo:05X}-0x{f_hi - 1:05X}  ({len(filt_bytes)} bytes)")
    for a, by, mn, cm in filt:
        print(f"        0x{a:05X}  {by.hex():<8}  {mn:<22}  ; {cm}")
    print(f"\n      TELEMETRY    0x{t_lo:05X}-0x{t_hi - 1:05X}  ({len(tele_bytes)} bytes)")
    for a, by, mn, cm in tele:
        print(f"        0x{a:05X}  {by.hex():<8}  {mn:<22}  ; {cm}")
    for lo, hi, nm in ((f_lo, f_hi, "filter cave"), (t_lo, t_hi, "telemetry rung")):
        check(FREE_LO <= lo and hi <= FREE_HI, f"{nm} [0x{lo:05X},0x{hi:05X}) lies inside the free run", "S")
        check(all(x == 0xFF for x in base[lo:hi]), f"{nm} target range is all-0xFF in the base image", "S")
    check(f_hi <= t_lo or t_hi <= f_lo,
          f"the filter cave [0x{f_lo:05X},0x{f_hi:05X}) and the telemetry rung [0x{t_lo:05X},0x{t_hi:05X})"
          " do not overlap (rev 2 RELOCATED both: the prologue made the filter 10 bytes longer than"
          " the 2 bytes rev 1 had spare)", "S")
    check(CAVE_JMP_LP + 4 <= min(f_lo, t_lo),
          f"the 4-byte `jr` at 0x{CAVE_JMP_LP:05X} overlaps neither cave", "S")
    spare = STRUCT_LO - max(f_hi, t_hi)
    check(spare >= 0,
          f"{spare} free bytes still spare between the last cave byte and the 0x{STRUCT_LO:05X}"
          " structure", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] THE ARITHMETIC -- unit tests on the Python mirror of the cave")
    bad = [d for k in range(1, 16) for d in range(-8192, 8193) if (d >> k) == 0 and d < 0]
    check(not bad, "EXHAUSTIVE d in [-8192,8192], K=1..15: `step==0 and d!=0` implies d>0 in EVERY case"
                   " -- so the bare `mov 0x1,r16` (no sign test) is correct", "S")
    for y0 in (1, -1, 17, -17, 1032, -1032, 1128, -1128, 32767, -32768):
        y, n = y0, 0
        while y != 0 and n < 500000:
            y = sp_filter_tick(0, y, K_SHIFT)
            n += 1
        check(y == 0, f"K={K_SHIFT}: decays to EXACTLY 0 from y0={y0} in {n} ticks ({n * 1000 / TICK_HZ:.0f} ms)"
                      " -- no stuck LSB from either direction", "S")
    naive_stuck = 0
    for y0 in range(-64, 65):
        y = y0
        for _ in range(5000):
            d = 0 - y
            y = y + (d >> K_SHIFT)
        naive_stuck += (y != 0)
    check(naive_stuck > 0, f"CONTROL: the NAIVE form (no rounding fix) sticks for {naive_stuck} of 129"
                           " start values -- the fix is doing real work, not decorating", "S")
    for tgt in (1032, -1032, 500, -7, 1):
        y, n = 0, 0
        while y != tgt and n < 500000:
            y = sp_filter_tick(tgt, y, K_SHIFT)
            n += 1
        check(y == tgt, f"K={K_SHIFT}: step response 0 -> {tgt} converges EXACTLY in {n} ticks", "S")
    y = 0
    check(sp_filter_tick(1032, 0, K_SHIFT) == 1032 >> K_SHIFT,
          f"first tick of a 0 -> 1032 step moves {1032 >> K_SHIFT}, not 1032: the kick into dE is"
          f" divided by 2^{K_SHIFT} = {2 ** K_SHIFT}", "S")
    max_d = max_y = 0
    for i in range(20000):
        sp = 1128 if (i // 25) % 2 == 0 else -1128
        max_d = max(max_d, abs(sp - y))
        y = sp_filter_tick(sp, y, K_SHIFT)
        max_y = max(max_y, abs(y))
    check(max_y <= 32767 and max_d <= 2 ** 31 - 1,
          f"full-swing +-1128 20 Hz square wave: max |y| (the 16-bit CELL) = {max_y}"
          f" ({32767 / max_y:.1f}x headroom); max |d| (a 32-bit REGISTER) = {max_d}. No overflow.", "S")
    gmaxY = 0
    for s in range(N_SLOTS):
        gmaxY = max(gmaxY, max(rec(base, u32(base, MAP_PTR + 4 * s))[2]))
    check(gmaxY == 1128, f"|sp| bound re-derived FROM THE IMAGE, not inherited: sp = (+-1) * mulh(map Y)"
                         f" and max Y over ALL {N_SLOTS} map slots = {gmaxY}"
                         f" -> a 16-bit state cell has {32767 / gmaxY:.1f}x headroom on ANY selector", "S")
    check(max(rec(base, u32(base, MAP_PTR + 4 * LIVE_SLOT))[2]) == 1032,
          "the LIVE selector-7 map peaks at 1032, matching the spec's +-1032 figure", "V")
    print(f"      K={K_SHIFT}: a = {R['a']:.6f} | f_c = {R['fc']:.2f} Hz | |H|: 3 Hz {R['h3']:.3f},"
          f" 20 Hz {R['h20']:.3f}, 40 Hz {R['h40']:.3f} | tau {R['tau_ms']:.1f} ms"
          f" | group delay {R['gd_ms']:.1f} ms")

    print("\n  [4b] THE ENGAGE-INIT -- unit tests on the same mirror (rev 2's fix for FAIL B)")
    # (ii) the EXACT compare's discriminating power.  With a full 32-bit equality test the only
    # false positive possible is the literal value itself, so the property is exhaustive by
    # construction rather than sampled -- that is the whole reason for preferring it.
    check(all(_s32(v) != _s32(EINIT_SENTINEL)
              for v in list(range(-E_MAX_BOUND, E_MAX_BOUND + 1, 7))
              + [-768000, 0, 768000, E_MAX_BOUND, -E_MAX_BOUND, EINIT_SENTINEL - 1, -(1 << 31)]),
          f"NO value other than 0x{EINIT_SENTINEL:08X} itself can trip the init: an exact 32-bit"
          f" equality has no band.  Checked every 7th value across +-|E|max={E_MAX_BOUND}, the exact"
          " bounds, the sentinel minus one, and the most negative int32", "S")
    check(_s32(EINIT_SENTINEL) == _s32(EINIT_SENTINEL),
          f"and the sentinel 0x{EINIT_SENTINEL:08X} itself DOES trip it", "S")
    check(EINIT_SENTINEL > E_MAX_BOUND * 25000,
          f"for scale: the sentinel is {EINIT_SENTINEL // E_MAX_BOUND}x larger than the largest"
          f" possible |E| ({E_MAX_BOUND}), so it is not a value the loop could ever produce", "S")
    # (i) the reset -> engage sequence
    y, cell = 0, 0
    for _ in range(400):                                  # engaged, sp = 800, marker = a normal E
        y = sp_filter_tick(800, y, K_SHIFT, marker=1234)
    y_before_gap = y
    check(y_before_gap == 800, f"after 400 engaged ticks at sp=800 the filter has converged (y={y})", "S")
    # ... a gap: the hook does NOT run, y stays stale at 800, and the epilogue plants the sentinel
    y_first = sp_filter_tick(-300, y_before_gap, K_SHIFT, marker=EINIT_SENTINEL)
    check(y_first == -300,
          f"FIRST engaged tick after the gap with sp=-300 returns EXACTLY -300 (got {y_first}), not a"
          f" value dragged from the stale y={y_before_gap} -- this is rev 1's FAIL B, fixed", "S")
    rev1_would_be = sp_filter_tick(-300, y_before_gap, K_SHIFT, marker=1234)
    check(rev1_would_be != y_first,
          f"CONTROL: without the init the same tick would return {rev1_would_be}, i.e."
          f" {abs(rev1_would_be - y_first)} counts of stale setpoint -- the fix is doing real work", "S")
    seq = [y_first]
    yy = y_first
    for _ in range(200):
        yy = sp_filter_tick(-300, yy, K_SHIFT, marker=1234)
        seq.append(yy)
    check(seq[0] == -300 and all(s == -300 for s in seq),
          "and every tick after it filters normally (already at the target here, so it holds -300)", "S")
    # a harder case: the init tick jumps, then the filter must ramp from THERE, not from the stale y
    yy = sp_filter_tick(-300, 800, K_SHIFT, marker=EINIT_SENTINEL)
    step2 = sp_filter_tick(1000, yy, K_SHIFT, marker=1234)
    check(yy == -300 and step2 == -300 + ((1000 - (-300)) >> K_SHIFT),
          f"init tick gives -300, and the NEXT tick filters from -300 toward 1000 by"
          f" {(1000 - (-300)) >> K_SHIFT} counts (got {step2}) -- normal filter behaviour resumes", "S")
    check(sp_filter_tick(1032, 0, K_SHIFT, marker=EINIT_SENTINEL) == 1032,
          "on an init tick the returned r16 is the RAW setpoint, byte-identical to V282's behaviour", "S")

    # (iii) a FULL TICK-LEVEL simulation carrying the REAL epilogue semantics:
    #        skip tick     -> the hook does not run, y is untouched, epilogue stores the SENTINEL
    #        engaged tick  -> the hook runs, then the epilogue stores this tick's E = 32*y - fb
    #      Asserted: the init fires on EXACTLY the first engaged tick of each engagement, and never
    #      on any other tick, over a schedule with several engagements of differing length.
    def run(schedule, fb=0):
        y, marker, fired = 0, EINIT_SENTINEL, []
        for i, (engaged, sp) in enumerate(schedule):
            if not engaged:
                marker = EINIT_SENTINEL          # epilogue on a hook-skipping route
                continue
            fired.append(i if marker == EINIT_SENTINEL else None)
            y = sp_filter_tick(sp, y, K_SHIFT, marker=marker)
            marker = 32 * y - fb                 # epilogue on the engaged route: r16 = the current E
            assert abs(marker) <= E_MAX_BOUND, marker
        return [f for f in fired if f is not None], y

    sched = ([(False, 0)] * 5 + [(True, 900)] * 60 + [(False, 0)] * 3
             + [(True, -400)] * 40 + [(False, 0)] * 1 + [(True, 250)] * 30)
    fired, y_end = run(sched)
    first_engaged = [5, 68, 109]
    check(fired == first_engaged,
          f"over a 139-tick schedule with THREE engagements the init fires on exactly ticks {fired}"
          f" -- the first engaged tick of each, and no other (expected {first_engaged})", "S")
    check(len(fired) == 3,
          "exactly once per re-engage: not zero (the marker would be stale) and not every tick (the"
          " marker would be a latch, which is what a shared-epilogue misreading would have caused)", "S")
    fired2, _ = run([(True, 500)] * 300)
    check(fired2 == [0],
          "and on a single uninterrupted engagement it fires ONLY on tick 0 -- 299 further engaged"
          " ticks all take the filter path", "S")
    # (iv) THE WHOLE POINT OF THE EXACT COMPARE: the band the cheap `sar 0x1c ; cmp 7` test would
    #      have fired on must NOT fire now.  Sampled densely across it, plus both endpoints.
    band = list(range(0x70000000, 0x7FFFFFFF, 0x00100001)) + [0x70000000, 0x7FFFFFFE, 0x7FFFFFFF - 1]
    fires = [v for v in band if sp_filter_tick(777, 111, K_SHIFT, marker=v) == 777]
    check(not fires,
          f"the init does NOT fire anywhere in 0x70000000..0x7FFFFFFE ({len(band)} values sampled,"
          " including both endpoints) -- exactly the band the cheaper top-nibble test would have"
          f" tripped on.  This is why the exact compare is worth its 4 extra bytes.  (Hits: {fires[:4]})", "S")
    check(sp_filter_tick(777, 111, K_SHIFT, marker=EINIT_SENTINEL) == 777,
          "while 0x7FFFFFFF itself DOES fire -- the band test above is not vacuous", "S")

    print("\n  [4bb] DOCSTRING-vs-BUILD GUARD -- the text must not describe a superseded revision")
    # Adversary C on rev 2: the BYTES passed but the docstring body still described rev 1 (34-byte
    # filter cave, 32-byte rung, "bit 0 is the lowest free").  Prose drifts silently because nothing
    # executes it.  These string checks are cheap and they fail loudly.
    _doc = __doc__ or ""
    for banned, why in (
            ("Bit 0 is the lowest free", "rev 1's exact FAIL-A claim"),
            ("bit 0 = (gp-0x6a32", "rev 1's telemetry assignment"),
            ("bits 2-0 are written by nothing", "rev 1's false free-bit census"),
            ("the filter cave, 34 bytes", "rev 1's cave size (rev 2 is 48 B; 34 B is the RUNG)"),
            ("TELE     32 bytes", "rev 1's rung size (rev 2 is 34 B)")):
        check(banned not in _doc,
              f"the docstring does NOT contain {banned!r} -- {why}", "S")
    # "bit 0" may still legitimately appear -- the FAIL A narrative has to name what rev 1 broke.
    # What must NOT happen is a bare mention with no ownership context, which is how the rev-1 claim
    # read.  So: every occurrence must sit near STOCK / FAIL A / the writer's address.
    # Scope the scan to TELEMETRY mentions.  "bit 0" also appears legitimately in the ENCODING TRAPS
    # section, where it means hw2 bit 0 / displacement bit 0 and has nothing to do with CAN 0x14A.
    _ctx = ("STOCK", "FAIL A", "0x55B06", "gp-0x679a", "NOT free", "destroyed", "Honda")
    _tele = ("0x14A", "byte 4", "byte-4")
    _bare = []
    for i in range(len(_doc)):
        if not (_doc.startswith("bit 0", i) or _doc.startswith("Bit 0", i)):
            continue
        w = _doc[max(0, i - 260):i + 260]
        if any(t in w for t in _tele) and not any(c in w for c in _ctx):
            _bare.append(i)
    check(not _bare,
          f"every TELEMETRY 'bit 0' in the docstring sits in an ownership context (STOCK / FAIL A /"
          f" the stock writer's address) -- {len(_bare)} bare mention(s) that could read as a live"
          " claim.  Encoding-level 'bit 0' (hw2 bit 0, displacement bit 0) is out of scope.", "S")
    for required, why in (
            ("BIT 5", "the live telemetry bit"),
            ("0xC4C00-0xC4C2F", "the live filter-cave extent"),
            ("0xC4BDC-0xC4BFD", "the live telemetry-rung extent"),
            ("ENGAGE-INIT PROLOGUE", "the rev-2 prologue must appear in the edit walkthrough"),
            ("0x55B06", "the stock bit-0 writer that FAIL A collided with")):
        check(required in _doc, f"the docstring DOES describe {required!r} -- {why}", "S")
    check(f"{len(filt_bytes)} bytes" in _doc or f"{len(filt_bytes)}-byte" in _doc
          or f"0xC4C00-0x{f_hi - 1:05X}".upper() in _doc.upper(),
          f"the docstring's cave extent agrees with the {len(filt_bytes)}-byte cave actually emitted", "S")

    print("\n  [4c] MIRROR-vs-LAYOUT DRIFT GUARD")
    import inspect                                                                    # noqa: E402
    src = inspect.getsource(sp_filter_tick)
    # only the PER-LINE trailing annotations count -- take the text after each line's first '#'.
    # (Prose in the docstring may legitimately mention an OLD address while explaining the drift.)
    ann = sorted({int(m, 16)
                  for line in src.split("\n") if "#" in line
                  for m in re.findall(r"0x[0-9A-Fa-f]{5}", line.split("#", 1)[1])}
                 & set(range(FREE_LO, FREE_HI)))
    emitted = {a for a, _, _, _ in filter_cave(K_SHIFT)}
    check(ann and set(ann) <= emitted,
          f"every cave address annotated in the Python mirror ({[hex(a) for a in ann]}) is a REAL"
          f" instruction address in the emitted filter cave -- the mirror cannot silently describe"
          f" a layout the build no longer has", "S")
    check(min(ann) == FILT and max(ann) == filt[-1][0],
          f"the mirror's first annotation is the cave entry 0x{FILT:05X} and its last is the return"
          f" jr 0x{filt[-1][0]:05X} -- the mirror spans exactly the emitted cave", "S")
    check(f"FILT = 0x{FILT:05X}".lower() in src.lower() or f"0x{FILT:05X}".lower() in src.lower(),
          f"the mirror's own docstring names the live cave base 0x{FILT:05X}", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [5] THE TWO `jr` DISPLACEMENTS -- checked BOTH ways")
    code = bytearray(base)
    attributed = set()
    hook_jr = jr(HOOK_SP, FILT)
    tele_jr = jr(CAVE_JMP_LP, TELE)
    ret_jr = filt[-1][1]
    for at, blob, nm in ((HOOK_SP, hook_jr, f"hook  0x{HOOK_SP:05X} -> filter cave 0x{FILT:05X}"),
                         (CAVE_JMP_LP, tele_jr, f"cave  0x{CAVE_JMP_LP:05X} -> telemetry   0x{TELE:05X}"),
                         (filt[-1][0], ret_jr, f"return 0x{filt[-1][0]:05X} -> 0x{HOOK_RET:05X}")):
        tgt = jr_target(at, blob)
        want = {HOOK_SP: FILT, CAVE_JMP_LP: TELE, filt[-1][0]: HOOK_RET}[at]
        print(f"      {nm}   bytes {blob.hex()}  disp {want - at:+#08x}  decoded target 0x{tgt:05X}")
        check(tgt == want, f"{nm}: independent decoder recovers the intended target", "S")
        check(len(blob) == 4 and (blob[2] & 1) == 0,
              f"{nm}: 4 bytes, hw2 bit0 == 0 (a jr, NOT an ld.bu -- the Format-V/ld.bu collision)", "S")

    print("\n  [6] APPLY")
    for at, blob, nm in ((HOOK_SP, hook_jr, "hook -> jr filter cave"),
                         (FILT, filt_bytes, "filter cave"),
                         (CAVE_JMP_LP, tele_jr, "cave epilogue -> jr telemetry"),
                         (TELE, tele_bytes, "telemetry rung + relocated epilogue")):
        code[at:at + len(blob)] = blob
        attributed |= set(range(at, at + len(blob)))
        check(bytes(code[at:at + len(blob)]) == blob,
              f"0x{at:05X}: {len(blob)} bytes written ({nm})", "T")
    check(bytes(code[HOOK_SP:HOOK_SP + 4]) == hook_jr and len(hook_jr) == len(HOOK_SP_OLD),
          "the hook is a SAME-LENGTH swap: 4-byte st.h -> 4-byte jr, so 0x29D76 onward does not move", "S")
    check(bytes(code[CAVE_START:CAVE_JMP_LP]) == bytes(base[CAVE_START:CAVE_JMP_LP]),
          f"every existing 0x14A rung (0x{CAVE_START:05X}-0x{CAVE_JMP_LP - 1:05X},"
          f" {CAVE_JMP_LP - CAVE_START} bytes, incl. the identity rung and `movea -0x1518`)"
          " is BYTE-IDENTICAL -- only the 2-byte `jmp [lp]` exit moved", "S")
    check(bytes(code[TELE + len(tele_bytes) - 6:TELE + len(tele_bytes)])
          == bytes(base[CAVE_EPILOGUE:CAVE_EPILOGUE + 4]) + CAVE_JMP_LP_OLD,
          "the relocated epilogue is byte-identical to the `movea -0x1518,gp,r6 ; jmp [lp]` it replaces", "S")

    print("\n  [7] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    stray = [x for x in range(START, END) if code[x] != base[x] and x not in attributed]
    check(stray == [], f"no byte outside the 4 written regions changed ({len(stray)} stray)", "S")
    # EVERYTHING BELOW IS ENTAILED BY THE `stray == []` CHECK ABOVE (adversary C's finding): if no byte
    # outside the 4 written regions differs from the base, then every table that lies outside them is
    # byte-identical by construction.  Kept because they name the cells a reader cares about, but
    # bucketed E so the headline census cannot pass them off as independent evidence.
    check(bytes(code[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, "0x55C0E jarl 0xc4b34,lp untouched", "E")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]),
          "the CAN-427 delivered-torque tap window 0x55DF0-0x55E11 is byte-identical", "E")
    check(u16(code, FB_CELL) == FB_V280, f"feedback clamp 0xC62E6 == {FB_V280}", "E")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == u16(base, a_) == v, f"0x{a_:05X} == base == {v}", "E")
    for p in sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)}):
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]),
              f"map 0x{p:05X} byte-identical", "E")
    for arr, nm in ((KP_PTR, "Kp"), (KD_PTR, "Kd")):
        for s in range(N_SLOTS):
            p = u32(base, arr + 4 * s)
            n = u16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
                  f"{nm} slot {s} @0x{p:05X} byte-identical", "E")
    tps = {u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)}
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "E")

    # ------------------------------------------------------------------------------------------
    print("\n  [8] CRC -- owning block located GENERICALLY via V53.owning_block")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    check(len(blocks) == 1, f"exactly ONE CRC block owns all {len(attributed)} edited bytes ({blocks})", "S")
    b0, b1 = blocks[0]
    check(b1 == 0xC4FFC, f"the block's trailer sits at 0x{b1:05X}", "S")
    check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit lands ON the trailer 0x{b1:06X}", "S")
    oldc, newc = u32(code, b1), zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved", "S")
    struct.pack_into("<I", code, b1, newc)
    attributed |= set(range(b1, b1 + 4))
    print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    print("\n  [9] FULL BYTE DIFF vs V282")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    allowed = (set(range(HOOK_SP, HOOK_SP + 4)) | set(range(f_lo, f_hi))
               | set(range(CAVE_JMP_LP, CAVE_JMP_LP + 4)) | set(range(t_lo, t_hi))
               | set(range(b1, b1 + 4)))
    check(set(diff) <= allowed,
          f"every one of the {len(diff)} differing bytes lies in {{hook 0x{HOOK_SP:05X}..0x{HOOK_SP + 3:05X},"
          f" filter cave 0x{f_lo:05X}..0x{f_hi - 1:05X}, 0x14A extension 0x{CAVE_JMP_LP:05X}..0x{CAVE_JMP_LP + 3:05X},"
          f" telemetry 0x{t_lo:05X}..0x{t_hi - 1:05X}, CRC 0x{b1:05X}..0x{b1 + 3:05X}}}", "S")
    # NB label by RANGE MEMBERSHIP, not by run start: a run splits wherever a written byte happens
    # to equal the 0xFF filler it replaced (the 0x7FFFFFFF immediate's three 0xFF bytes do exactly
    # that), and keying the label off `s ==` would then mislabel the remainder of the cave.
    def _region(s_, e_):
        for lo_, hi_, nm_ in ((HOOK_SP, HOOK_SP + 4, "hook (st.h -> jr)"),
                              (CAVE_JMP_LP, CAVE_JMP_LP + 4, "0x14A cave exit (jmp[lp] -> jr)"),
                              (t_lo, t_hi, "telemetry rung (NEW)"),
                              (f_lo, f_hi, "filter cave (NEW)"),
                              (b1, b1 + 4, "CRC trailer")):
            if lo_ <= s_ and e_ <= hi_:
                return nm_
        return f"?? UNATTRIBUTED 0x{s_:06X}-0x{e_ - 1:06X}"
    for s, e in runs(diff):
        kind = _region(s, e)
        check(not kind.startswith("??"), f"diff run 0x{s:06X}-0x{e - 1:06X} is attributable", "S")
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {kind:<28}  {bytes(base[s:e]).hex()}"
              f" -> {bytes(code[s:e]).hex()}")
    print(f"      {len(diff)} bytes total: 4 hook + {len(filt_bytes)} filter cave"
          f" + 4 cave-exit + {len(tele_bytes)} telemetry + 4 CRC")

    print("\n  [9b] CROSS-IMAGE vs V281 rev 3 -- V282's own cave diff + this build's, nothing else")
    parent = Path(plain_image_path(PARENT_NAME)).read_bytes()
    check(hashlib.sha256(parent).hexdigest() == PARENT_SHA, "V281 rev 3 image sha256 matches", "S")
    d_v282 = {x for x in range(START, END) if base[x] != parent[x]}
    d_v288 = {x for x in range(START, END) if code[x] != parent[x]}
    check(d_v288 == (d_v282 | set(diff)) - {x for x in d_v282 & set(diff) if code[x] == parent[x]},
          f"V288 vs V281 rev 3 ({len(d_v288)} bytes) == V282's own diff ({len(d_v282)}) UNION this"
          f" build's ({len(diff)}), modulo the shared CRC cell", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [10] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V288 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN exists -- the non-circular cipher test is reachable", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    print("\n  [11] END STATE -- re-read from the FINAL image AND from the DECODED .rwd")
    for nm, im in (("code", code), ("dec ", dec)):
        # the `dec` arm is ENTAILED by the [10] assertion "decoded .rwd is byte-identical to
        # the built image" -- it re-reads the same bytes through a second name.  Bucketed E.
        kd = "T" if nm == "code" else "E"
        check(bytes(im[HOOK_SP:HOOK_SP + 4]) == hook_jr, f"{nm}: hook == jr 0x{FILT:05X}", kd)
        check(jr_target(HOOK_SP, bytes(im[HOOK_SP:HOOK_SP + 4])) == FILT,
              f"{nm}: hook jr decodes to the filter cave", "S")
        check(bytes(im[f_lo:f_hi]) == filt_bytes, f"{nm}: filter cave intact", kd)
        check(jr_target(filt[-1][0], bytes(im[filt[-1][0]:filt[-1][0] + 4])) == HOOK_RET,
              f"{nm}: the cave's return jr decodes to 0x{HOOK_RET:05X}", "S")
        check(jr_target(CAVE_JMP_LP, bytes(im[CAVE_JMP_LP:CAVE_JMP_LP + 4])) == TELE,
              f"{nm}: the 0x14A cave exit jr decodes to the telemetry rung", "S")
        check(bytes(im[t_lo:t_hi]) == tele_bytes, f"{nm}: telemetry rung intact", kd)
        check(bytes(im[CAVE_START:CAVE_JMP_LP]) == bytes(base[CAVE_START:CAVE_JMP_LP]),
              f"{nm}: all five existing 0x14A rungs byte-identical", "S")
        check(bytes(im[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, f"{nm}: 0x55C0E untouched", kd)
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: 427 tap untouched", kd)
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}", kd)
        n_, X_, Y_ = rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(X_) == LIVE_KP_X and tuple(Y_) == LIVE_KP_Y, f"{nm}: live Kp record == flat-248", kd)
        # PINS: tie the new code to bytes already on the flown image, not to this script's tables
        # every 4-byte instruction in the two new caves that touches gp-0x6a32, found by SCANNING the
        # built bytes rather than by trusting the tables above
        sp_sites = []
        for lo_, hi_ in ((f_lo, f_hi), (t_lo, t_hi)):
            for a_ in range(lo_, hi_ - 2, 2):
                h1 = struct.unpack_from("<H", im, a_)[0]
                op_ = (h1 >> 5) & 0x3F
                if (h1 & 0x1F) == GP and op_ in (0x39, 0x3B) \
                        and (struct.unpack_from("<H", im, a_ + 2)[0] & 0xFFFE) == (SP_CELL_DISP & 0xFFFE):
                    sp_sites.append((a_, op_, h1 >> 11))
        check([(op_, r_) for _, op_, r_ in sp_sites]
              == [(0x39, R9), (0x3B, R16), (0x39, R16), (0x39, R6)],
              f"{nm}: exactly 4 accesses to gp-0x6a32 in the new code, in order: ld.h->r9 (y[n-1]),"
              f" st.h r16 (publish y[n]), ld.h->r16 (read back), ld.h->r6 (the telemetry rung)"
              f" -- got {[(hex(a_), hex(o_), 'r%d' % r_) for a_, o_, r_ in sp_sites]}", "S")
        check(all(struct.unpack_from("<h", im, a_ + 2)[0]
                  == struct.unpack_from("<h", base, HOOK_SP + 2)[0] for a_, _, _ in sp_sites),
              f"{nm}: every one carries the SAME displacement halfword as the ORIGINAL st.h at 0x29D74"
              " -- the state cell is pinned to a byte on the flown image, not to a constant in this file", "S")
        check(all((struct.unpack_from("<H", im, a_ + 2)[0] & 1) == 0 for a_, _, _ in sp_sites),
              f"{nm}: every one has hw2 bit0 == 0 -> the 16-bit ld.h/st.h form, NOT the 32-bit"
              " ld.w/st.w the odd-displacement trap would silently produce", "S")
        _tb4 = [a for a, by, _, _ in tele if by[:2] == st_b(R6, 0, GP)[:2]][0]
        check(struct.unpack_from("<h", im, _tb4 + 2)[0]
              == struct.unpack_from("<h", base, 0xC4B5E + 2)[0] == BUF_BYTE4_DISP,
              f"{nm}: the new rung writes the SAME 0x14A byte-4 cell the flown bit-6 rung writes", "S")
        _andi = [a for a, by, _, _ in tele if by[:2] == f67("andi", R6, R6, 0)[:2]][0]
        check(u16(im, _andi + 2) == NEW_BIT_MASK,
              f"{nm}: the new rung's andi mask is 0x{NEW_BIT_MASK:02X} -- it clears ONLY bit 5", "S")
        check(u16(im, _andi + 2) & STOCK_B4_BITS == STOCK_B4_BITS,
              f"{nm}: the mask PRESERVES stock bits 2,1,0 -- rev 1's FAIL A cannot recur", "S")
        # and no OTHER new byte-4 mask anywhere in the two new caves may clear a stock bit either
        for lo_, hi_ in ((f_lo, f_hi), (t_lo, t_hi)):
            for a_ in range(lo_, hi_ - 2, 2):
                if bytes(im[a_:a_ + 2]) == f67("andi", R6, R6, 0)[:2]:
                    check(u16(im, a_ + 2) & STOCK_B4_BITS == STOCK_B4_BITS,
                          f"{nm}: andi at 0x{a_:05X} (mask 0x{u16(im, a_ + 2):02X}) preserves stock bits 2-0", "S")
        # the ENGAGE-INIT prologue, pinned to bytes on the flown image rather than to constants here
        _ldw = f_lo
        check(struct.unpack_from("<h", im, _ldw + 2)[0]
              == struct.unpack_from("<h", base, EINIT_EPILOGUE_ST + 2)[0],
              f"{nm}: the prologue's ld.w displacement halfword == Honda's own st.w at"
              f" 0x{EINIT_EPILOGUE_ST:05X} -- the marker cell is pinned to the flown image", "S")
        check(struct.unpack_from("<H", im, _ldw + 2)[0] & 1 == 1,
              f"{nm}: the prologue's hw2 bit0 is SET -> the 32-bit ld.w form, matching the cell's width", "S")
        check(bytes(im[_ldw + 4:_ldw + 10]) == mov_imm32(EINIT_SENTINEL, R9)
              and bytes(im[_ldw + 10:_ldw + 12]) == f1("cmp", R9, R6),
              f"{nm}: prologue materialises the FULL 0x{EINIT_SENTINEL:08X} into r9 and does an EXACT"
              " 32-bit `cmp r9,r6` -- no top-nibble band, no value class that can be mistaken for it", "S")
        check(struct.unpack_from("<i", im, _ldw + 6)[0] == EINIT_SENTINEL
              == struct.unpack_from("<i", base, EINIT_SENTINEL_SITES[0] + 2)[0]
              == struct.unpack_from("<i", base, EINIT_SENTINEL_SITES[1] + 2)[0],
              f"{nm}: the immediate is pinned to the SAME 32-bit literal both of Honda's own"
              f" sentinel loads carry (0x{EINIT_SENTINEL_SITES[0]:05X}, 0x{EINIT_SENTINEL_SITES[1]:05X})", "S")
        _be = _ldw + 12
        _bd = ((u16(im, _be) >> 11) << 4) | (((u16(im, _be) >> 4) & 7) << 1)
        _bd -= 0x200 if _bd & 0x100 else 0
        _st_pc = [a for a, by, _, _ in filt if by[:2] == st_h(R16, 0, GP)[:2]][0]
        check((u16(im, _be) & 0xF) == 0x2 and _be + _bd == _st_pc,
              f"{nm}: the engage-init `be` at 0x{_be:05X} targets 0x{_be + _bd:05X}, which IS the"
              f" st.h at 0x{_st_pc:05X} -- so the init path stores RAW sp and returns, touching"
              " no filter arithmetic", "S")
        check(all(bytes(im[a_:a_ + 2]) != f1("mov", R16, R6)[:2] for a_ in range(_ldw, _be + 2, 2)),
              f"{nm}: the prologue never writes r16 -- on the init path r16 still holds raw sp when"
              " the `be` lands on the store", "S")

    print("\n  [12] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base), K_SHIFT)
    check(hashlib.sha256(ind).hexdigest() == img_sha,
          "independent rebuild (literal opcode arithmetic, no shared encoder, generic re-CRC)"
          " == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n  [13] 0x14A BYTE-4 BIT MAP (for the close-out artifact / handoff)")
    print("      bit  owner   V282                                        V288 rev 2")
    print("       7   cave    sign(gp-0x6b4c) [11-slot assist sum]        unchanged")
    print("       6   cave    |r24| >= |T (gp-0x6b38, the 427 tap)|       unchanged")
    print("       5   cave    |r24| >= |aggregator sum (gp-0x6b94)|       REDEFINED: sign(y) = sign(sp_filtered)")
    print("       4   cave    sign(gp-0x6ada = r24)                       unchanged")
    print("       3   cave    sign(gp-0x3680)                             unchanged")
    print("       2   STOCK   frame builder 0x55AC0 <- gp-0x6799 b0       unchanged -- NOT OURS")
    print("       1   STOCK   frame builder 0x55AE8 <- gp-0x679b b0       unchanged -- NOT OURS")
    print("       0   STOCK   frame builder 0x55B06 <- gp-0x679a b0       unchanged -- NOT OURS")
    print("      (rev 1 wrote bit 0 and destroyed a stock flag.  Bits 2-0 are Honda's; bits 7-3 are the cave's.)")

    _scr = os.environ.get("ACCORD_V288_SCRATCH", "").strip()
    if _scr:
        # RWD FIRST, then the image.  The rwd name is the longer of the two, so if the scratch dir
        # sits deep enough to blow the Windows path limit, the failure happens BEFORE any file is
        # written rather than leaving a lone image behind that looks like a complete pair.
        _p_rwd, _p_img = Path(_scr, RWD_NAME), Path(_scr, IMG_NAME)
        check(max(len(str(_p_rwd)), len(str(_p_img))) < 255,
              f"scratch paths fit inside the 255-char limit (longest {max(len(str(_p_rwd)), len(str(_p_img)))})", "S")
        _p_rwd.write_bytes(rwd)
        _p_img.write_bytes(bytes(code))
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(IMG_NAME))
        out_rwd = Path(RWD_DIR, RWD_NAME)
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        mine = [f.name for f in Path(RWD_DIR).glob("*V288R2*.rwd")
                if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not mine, f"exactly ONE flashable V288 REV 2 rwd on disk (others: {mine})", "S")
        others = [f for f in Path(RWD_DIR).glob("*V288*.rwd")
                  if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"NO other V288 rwd carries a flashable name ({[f.name for f in others]})"
                          " -- rev 1 was renamed on the orchestrator's instruction", "S")
        # and the renamed rev-1 files must still BE rev 1, by hash -- a rename must not have picked
        # up the wrong file, and nothing else may hide behind the SUPERSEDED prefix.
        sup_rwd = [f for f in Path(RWD_DIR).glob("SUPERSEDED*V288*.rwd")]
        sup_img = [f for f in Path(out_img.parent).glob("SUPERSEDED*v288*plain_image.bin")]
        for f, want, what in ([(f, REV1_RWD_SHA, "rwd") for f in sup_rwd]
                              + [(f, REV1_IMG_SHA, "image") for f in sup_img]):
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            check(h == want,
                  f"the SUPERSEDED V288 {what} is the KNOWN rev-1 artifact by hash, not an"
                  f" unidentified stray ({f.name})", "S")
        check(len(sup_rwd) == 1 and len(sup_img) == 1,
              f"exactly one SUPERSEDED V288 image and one rwd on disk"
              f" ({len(sup_img)} / {len(sup_rwd)})", "S")
        print(f"      rev 1 is parked as SUPERSEDED-DO-NOT-FLASH (image {REV1_IMG_SHA[:8]}…,"
              f" rwd {REV1_RWD_SHA[:8]}…); the ONLY flashable V288 is {out_rwd.name}")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V288_WRITE=rwd to emit the files")

    print("\n" + "=" * 112)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    _bk = _census["E"] + _census["V"] + _census["T"]
    print(f"  {_checks[1]}/{_checks[0]} assertions passed.  READ THE BUCKETS, NOT A HEADLINE NUMBER:")
    print(f"    {_census['S']:4d}  SUBSTANTIVE   -- can actually falsify something")
    print(f"    {_census['E']:4d}  ENTAILED      -- follows from a sibling assertion in this same run")
    print(f"    {_census['V']:4d}  VACUOUS       -- entailed by the base sha256")
    print(f"    {_census['T']:4d}  TAUTOLOGICAL  -- readback of a write this script just made")
    print(f"  Only the {_census['S']} substantive checks are evidence; the other {_bk} are bookkeeping.")
    print("=" * 112)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
