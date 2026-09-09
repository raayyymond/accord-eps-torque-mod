# -*- coding: utf-8 -*-
r"""V289 REV 1 -- V282 + a SECOND-ORDER NOTCH ON THE CLAMPED LKAS RATE-LOOP OUTPUT S (code cave, hooked
at 0x2A174) + the FEEDBACK-LAG POLE moved 16.5 -> 25 Hz at constant DC gain (2 cal halfwords) + two
telemetry bits on CAN 0x14A byte 4 that publish the notch's own removed component.

Base: V282 (NOT V288 -- the setpoint pre-filter flew 2026-09-08, the D-clamp bind duty fell x0.03 as
designed, and the grind was UNCHANGED; the reference-side class is exhausted, see
memory/accord/builds/accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted.md).
Design: docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md sec. 8.1 ("THE PAIR").
Trace:  docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md (Q10-Q12, the hook;
        the two FINAL ADDENDA, the RAM census).
Every load-bearing number below is re-derived from the V282 IMAGE by this script; where the trace or
the design disagrees with the image, the image wins and the disagreement is named.

=== WHAT THIS BUILD IS, AGAINST THE ARC ========================================================
The 20 Hz creep grind is, per the 2026-09-08 census, a PLANT MODE that the LKAS rate loop DE-DAMPS
(five builds pin the line at 20.03-20.08 Hz; Kp 248 -> 696 moves it +0.4 Hz and halves its damping
without instability).  V288 cut the excitation and the ring did not shrink.  V289 removes the loop's
ACTION at the mode instead: a unity-DC notch on the PID sum S takes the loop gain to ~0 in a +-3 Hz
band around 20.04 Hz and leaves it untouched below 13 Hz and above 30 Hz.  The fb-pole move is the
design's partner term: it returns +8 deg at 7.3 Hz so the strong-turn 7 Hz gate stays neutral
(1.005 vs 1.003) and +4.4 deg at openpilot's 3.9 Hz to cancel the notch's -3.8 deg there.
CLASS: an IN-LOOP PHASE/GAIN-SHAPING FILTER.  The kit's notch history is F61 (V48B: a biquad on the
shared bar input in the ALWAYS-ON loop -- BRICK, RAM collision), F67 (V105: 25.5 Hz on the gp-0x6b86
assist lane, relocated the mode 22.7 -> 20.5) and F68 (V144-V241, same lane, never flown).  This one
is in a DIFFERENT loop -- the engaged-only LKAS rate PID, on the path that carries 79 % of the tap's
20 Hz -- with its state in censused RAM and a 1 kHz cave that runs on EVERY tick (no skipped route,
so no stale state and no engage-init is needed; see STATE below).  The fb pole 0xC63E8/EA has been
923/1560 in all ~285 images: this is its FIRST move.
No P/D gain, no clamp, no map, no forward gain, no r24 cell moves.

=== EDIT 1 -- THE NOTCH CAVE (hook 0x2A174 -> 0xC4C00) ==========================================
Hook: the 4-byte `ld.hu 0x73ee,tp,r7` at 0x2A174 (bytes e5 3f ef 73) becomes `jr 0xC4C00`.  0x2A174
is the ONLY convergence point of the four routes that produce the clamped sum S in r12: the three
clip branches (`br 0x2a174` at 0x2A14A / 0x2A15E / 0x2A162) and the 0x2A164 reset path that falls
through with `mov 0x0,r12`.  Ghidra: xrefs to 0x2A174 are exactly those three `br`; xrefs to 0x2A176
and 0x2A178: none.  The cave filters r12 in place, replicates the displaced load (r7 := 507) as its
last act and returns to 0x2A178.  `jr` only -- lp is live across the whole 0x29A2C-0x2A29A window.

  r12 = x = S, |S| <= 15360 on EVERY route (the 0xC61BE clamp at 0x2A13E-0x2A162 bounds all three
        engaged/0x2A0C6 outcomes; 0x2A172 zeroes it on the 0x2A164 route) -- read off the listing,
        asserted at [1c] by re-encoding the whole 0x2A13A-0x2A1B4 window byte-identically.
        NAMING (tracer2, 2026-09-08): S is the clamped LOOP OUTPUT -- P+D after the per-variant gain
        LERPs (0xCBB54/0xCBC34/0xCBBC4/0xCBAE4) and the 254/256 fade, then the 0xC61BE clamp -- not
        the bare "P+I+D sum".  Nothing rescales r12 between that clamp and 0x2A174 on any route.
        The 0x2A0C6 route is gated on gp-0x680a == 1, a byte with ZERO writers image-wide (tracer2,
        BELIEF: dead), and even there |S| <= 832 (LERP y-knots 608-832) before the clamp.
  LIVE across the hook, never touched:  r16 (E / sentinel, stored 0x2A18C), r22, r24, r27, r29
        (stored 0x2A1A2/0x2A190/0x2A19C/0x2A188), lp, AND r11 / r14 / r15 (read at 0x2A1FC / 0x2A1E6 /
        0x2A228 with no prior write -- NOT in the trace's live list; added here from the listing).  The
        emulator seeds every one of them with a marker and asserts it comes back unchanged on every tick.
  SCRATCH: r6 (next access = WRITE ld.h @0x2A1BE), r7 (WRITE @0x2A174 = the displaced load we
        replicate), r9 (WRITE ld.w @0x2A178), r13 (WRITE ld.h @0x2A1F2 / @0x2A1D4 on both arms of
        the bne @0x2A1B4).  PSW: the first flag consumer after the hook is `bne` @0x2A1B4, preceded
        by `cmp 0x1,r16` @0x2A1AE, so the cave's compares are harmless.

FILTER: RBJ notch, f0 20.05 Hz, Q 3, fs 1 kHz, quantised to Q14 with a0 = 16384 implied:
        b = [16048, -31842, 16048]   a = [16384, -31842, 15712]
  DC gain   = (16048-31842+16048) / (16384-31842+15712) = 254/254 = 1  EXACTLY  (asserted)
  Nyquist   = (16048+31842+16048) / (16384+31842+15712) = 63938/63938 = 1 EXACTLY (asserted)
  REALISED from the integers (not the float design; [4]):  notch centre = the numerator zero, ON the
  unit circle because b0 == b2, at acos(31842/32096) -> 20.036 Hz; -3 dB band 16.98-23.64 Hz,
  Q_realised = 3.007; |H| = 0.0042 (-47.6 dB) at 20.05, 0.0018 at 20.03, 0.013 at 20.08 (the census
  centres); 0.998 / -3.85 deg at 3.9 Hz; 0.990 / -8.0 deg at 7.3 Hz; 0.925 at 13.5 Hz; 0.93 at 30 Hz.
  STRUCTURE: transposed direct form II, two int32 state words, plus FIRST-ORDER ERROR FEEDBACK:
        acc = b0*x + s1 + e            ; e = the previous tick's remainder, 0..16383
        y   = acc >> 14 (sar, floors)  ; e' = acc & 0x3FFF     (so acc == (y << 14) + e' exactly)
        n   = x - y                    ; the removed component (what the telemetry publishes)
        s1' = b1*n + s2                ; b1 == a1, so b1*x - a1*y collapses to one multiply
        s2' = b0*x - a2*y
  WHY the error feedback: a notch this narrow at 0.02 fs has A(1) = 254 against a0 = 16384, so the
  noise gain from the output quantiser to DC is a0/A(1) = 64.5.  Plain TDF-II with a floored y would
  therefore sit anywhere from X-64 to X for a constant input X (a 64-count DC deadband, asserted by
  the CONTROL at [4]).  Feeding the remainder back makes the quantisation error (1 - z^-1)-shaped:
  the DC deadband is gone -- for constant X, y dithers within +-1 of X with time-average EXACTLY X --
  and the in-band noise gain falls from ~48 to ~6 (rms noise into the lag < 2 counts of S).
  OVERFLOW: linear worst case from the l1 norms of the exact impulse responses x -> {s1, s2, acc}
  at |x| = 15360: |s1| <= 0.147 * 2^31, |s2| <= 0.146 * 2^31, |acc| <= 0.262 * 2^31 (+16383 for e).
  The worst-case sign sequences are actually driven through the byte-level emulator at [4] and
  reach those bounds with no 32-bit wrap; chirp, step, rail square-wave and random tests likewise.
  |y| linear worst case = 2.236 * 15360 = 34340 -- MORE than the 16-bit `st.h r12,-0x6b2e` at
  0x2A17C could hold and more than the sum clamp ever let through, so:
  OUTPUT CLAMP: r12 := clamp(y, +-cal(0xC61BE)) -- read from the SAME cal cell Honda's sum clamp
  uses, so the value the lag filter / the gp-0x6b2e publish / everything downstream receives can
  never exceed what V282 delivered.  The clamp is on the OUTPUT ONLY; the recursion uses the linear
  y, so the filter stays exactly linear (the l1 bounds hold unconditionally).  It binds only when the
  linear notch output overshoots the rail (a 0 -> 15360 step peaks at 1.155x = 17735 for ~10 ms).
  STATE (RAM), all in the censused run gp-0x6c44..gp-0x6c39 (the ONLY one of the trace's three
  candidates that survives a byte-granular re-census, see GATE 1):
        gp-0x6c44 (0xFEDF13BC)  s1   int32
        gp-0x6c40 (0xFEDF13C0)  s2   int32
        gp-0x6c3c (0xFEDF13C4)  e    low halfword of the third word (0..16383)
        gp-0x6c3a (0xFEDF13C6)  FLAG high halfword of the third word -- the telemetry handoff
  All four boot to 0 (.data source flash 0x8646C-0x86477 is 12 zero bytes, asserted).  The e load is
  masked with `andi 0x3fff` so the FLAG half never enters the arithmetic.
  NO ENGAGE-INIT IS NEEDED (the V288 rev 1 lesson does NOT apply here): V288's hook was SKIPPED by
  three routes and its state froze; THIS hook is on the one address every route passes every tick,
  the input is bounded on every route, and a stable notch driven by a bounded input has bounded
  state that decays with tau ~ 48 ticks while S = 0.  There is nothing to re-initialise.  A
  one-constant switch (INIT_ON_SENTINEL below, shipped FALSE; ACCORD_V289_INIT=1 flips it for a
  scratch run, which the write path refuses) adds the V288-style prologue that zeroes the three words
  on the tick after any gp-0x6cf8 == 0x7FFFFFFF.  The True path is ASSEMBLED and BEHAVIOURALLY TESTED
  on every run at [4](x) -- the emulator executes the prologue variant on a scratch image and asserts
  it zeroes only on 0x7FFFFFFF (not on 0, 1234, -82176, 0x7FFFFFFE), leaves the live registers and
  r7 == 507 intact, and is byte-identical to the shipped cave after its 26-byte prologue except for the
  return `jr` displacement -- but its bytes are NOT emitted in this build (adversary C, F1).

=== EDIT 2 -- THE FEEDBACK-LAG POLE, cal only =================================================
  0xC63E8  a: 923 -> 875    loaded SIGNED   `ld.h  0x73e8,tp,r9`  @0x28F8A (25 4f e8 73)
  0xC63EA  b: 1560 -> 2301  loaded UNSIGNED `ld.hu 0x73ea,tp,r16` @0x28F86 (e5 87 eb 73)
  Filter (0x28F86-0x28FA8): s' = (a*s >> 10) + (b*x >> 10); r26 = clamp(s + s', +-46080); s := s'.
  Pole: a/1024 = 0.85449 -> 25.03 Hz (was 923/1024 = 0.90137 -> 16.53 Hz).
  DC gain 2b/(1024-a): 2*2301/149 = 30.8859 (was 2*1560/101 = 30.8911) -- equal to 4 s.f. (30.89).
  Both values fit their load widths (875 < 32768 signed; 2301 < 65536 unsigned) and the filter's own
  headroom is unchanged in kind: |x| <= 12000 (guard 0x28F50-58), steady |s| <= 2301*12000/149 =
  185,315, a*s <= 1.63e8, b*x <= 2.77e7 -- all far inside int32.  E's bound is unchanged (r26 is still
  clamped to +-46080 by 0xC62E6).  Cost, from the design: loop gain x1.3 at 25-50 Hz (x1.48 rms
  noise into D) -- the 26-33 / 2-6 Hz guard statistic is the instrument for it.

=== EDIT 3 -- TELEMETRY on CAN 0x14A byte 4 (cave 0xC4B34, hook 0x55C0E, cell gp-0x1514) ==========
  The 1 kHz notch cave computes, every tick, from full-precision registers:
        bit 5 (0x20) := 1 when n = S - y < 0                (sign of the removed component)
        bit 7 (0x80) := 1 when |n| >= |y|                   (comparator, scale-free)
  and stores the pair as ONE halfword FLAG at gp-0x6c3a (values in {0, 0x20, 0x80, 0xA0} only).
  The 0x14A cave's `jmp [lp]` at 0xC4BD6 becomes `jr 0xC4BDC`; the 28-byte tail there reads the FLAG
  halfword (one atomic load -- the two bits can never come from different ticks), masks it with
  0xA0, clears bits 5 and 7 of byte 4 (andi 0x5F) and ORs the flag in, then re-issues the relocated
  epilogue `movea -0x1518,gp,r6 ; jmp [lp]`.  r6/r7 only, as every flown rung; lp untouched.
  DEVIATION FROM THE BRIEF, stated: the brief asked for y and S-y as two handoff WORDS compared in
  the 100 Hz cave.  Two words were not available to the standard needed -- of the trace's three
  certified runs, gp-0x68b0 is byte-occupied (ld.bu -0x68ad @0x19AE0, st.b -0x68af @0x1FB4E, st.b
  -0x68ac @0x4285A, Ghidra-confirmed) and gp-0x6ab0 boots to non-zero initialised .data (0x0288 x4,
  flash 0x86600) with no direct reference -- the signature of pointer-reached data.  Comparing at
  1 kHz in the cave is the same measurement at full precision, atomic by construction.
  BIT MAP AFTER V289 (bits 0-2 are STOCK HONDA: frame builder 0x55AC0/0x55AE8/0x55B06, never touched):
        7  |n| >= |y|          (was V282: sign(gp-0x6b4c), never used in any analysis)
        6  |r24| >= |T|        KEPT -- positive control (V282 duty 0.114-0.156)
        5  sign(n) = n < 0     (was V282: |r24| >= |aggregator|; V288 used it for sign(y_sp))
        4  sign(r24)           KEPT -- positive control (V282 duty ~0.404)
        3  sign(gp-0x3680)     KEPT as-is (design 8.1 lists it spendable; not spent -- nothing to put
                               on it that a null would need)
        2-0 STOCK              untouched (masks 0x5F in the tail, 0x3fff/0xA0 on the flag path)
  The existing rungs still write bits 7/5 first (mask 0x67 / 0xDF); our tail runs after them and wins.

=== WHAT THE WIRE SHOWS, AND THE SENTENCE A NULL LICENSES (design sec. 8.1, verbatim in substance) ==
  Liveness: b4.5 duty strictly inside (0,1) and b4.7 firing at episode onsets prove the notch
  executed on the 20 Hz content of the PID sum; b4.4/b4.6 keep their V282 duties (positive control);
  bits 0-2 keep their stock values (FAIL-A check).  The 0x1AB/427 tap (T, after the notch) is
  predicted tick-for-tick by the byte-exact mirror with the notch inserted.
  Success looks like: the 18-22 Hz line on the bar / wheel rate at a bookmarked turn-out is absent or
  decays at zeta >= 0.1 while b4.7 fires; the tap's 18-22 Hz content falls >= x0.5 against the
  mirror-without-notch; the 6-9 Hz band at |ang| > 60 deg and the 26-33 / 2-6 guard stay inside
  V282's spread (x1.09 / x1.25).
  NULL: "b4.5 in (0,1) and b4.7 firing at onsets, yet the bar/rate line at the bookmarks is unchanged
  in frequency and decay => the loop's own action at 20 Hz is not what sustains the ring; the mode
  is rung and damped outside this loop and the in-loop filter class for grind #1 is CLOSED."
  FAIL BRANCH: a NEW line at 14-17 Hz => the plant is the smooth near-critical one after all, the
  notch relocated the critical point exactly as the design's 5a rows predict -> revert.
  What the operator should expect if the design is right: grinding SHORTER and RARER, not gone
  (a rung ring decays ~1.7x faster); the design says so and this script claims nothing more.

=== RISK BEFORE THE DRIVE, stated ==============================================================
  * Code cave = this kit's only bricking class (V24/V27/V48B).  GATE 1 (RAM) is re-censused here by
    a byte-granular scanner over every gp-relative form incl. bit-ops and the 6-byte form, positive-
    controlled, and the state boots to 0; GATE 2 (loop) is the design's, on three plant fits, and
    its 7 Hz / 3.9 Hz / 25-50 Hz costs are quoted above.  The register-indirect residual that no
    static scan can exclude (gp-0x1500) is the same as for every flown cave.
  * Authority: DC of every path unchanged; capped-step peak rate/accel x1.00 on the census fit
    (design sec. 7); the output clamp guarantees the cave never delivers more than V282's sum clamp.
  * The fb pole's HF gain rise (x1.3 at 25-50 Hz) is the one term that adds gain anywhere.
  * 1 kHz task budget: 52 instructions / 140 bytes static, 50-51 executed per tick (emulator count),
    est. <= 3 us at 40 MHz (0.3 % of the tick) -- BELIEF; the tick's slack has never been measured.

=== LAYOUT AND DIFF (printed back from the built image at [3]-[9]; these are rev 1's numbers) =========
  0x2A174-0x2A177    hook: e5 3f ef 73 -> 89 07 8c aa  (jr 0xC4C00)
  0xC4BD6-0xC4BD9    0x14A cave exit: jmp [lp] -> jr 0xC4BDC  (2 bytes of 0xFF filler consumed)
  0xC4BDC-0xC4BF7    the 28-byte tail (telemetry rung + relocated epilogue)
  0xC4C00-0xC4C8B    the notch cave, 140 bytes, 52 instructions  (0xC4BF8-0xC4BFF stay 0xFF)
  0xC63E8 / 0xC63EA  875 / 2301
  0xC4FFC, 0xC6FFC   the two CRC trailers (code block [0x13000,0xC4FFC) and cal block [0xC6000,0xC6FFC))
  Full-file diff vs V282: 185 bytes differ of 188 touched, in 10 runs.  The three touched-but-unchanged
  bytes are 0xC4C0A and 0xC4C20 (two cave bytes that equal the 0xFF they replaced, so the cave shows as
  three runs) and 0xC63E9 (the shared 0x03 high byte of 923 and 875).  Nothing else moves: Kp/Kd/map/
  tapers/clamps/427 tap all byte-identical, asserted.
  NAMING: the tag says SUMNOTCH.20.05HZ (the DESIGN value the coefficients were quantised from); the
  REALISED centre of the integer notch is 20.036 Hz (the docs quote 20.04).  Asserted at [4].

=== ASSERTION CENSUS ============================================================================
  S = substantive (can falsify something about THIS build) | V = vacuous (entailed by the base
  sha256) | T = tautological (readback of a write just made) | E = entailed by a sibling assertion.
  Printed at the end of every run; the counts are print-derived, not quoted here, because FAST and
  --full differ (--full adds the long byte-emulator equivalence checks).  Adversary C's independent
  classification (2026-09-08) put 28 of the S-labelled checks in the entailed/tautological buckets, so
  read the S count as an upper bound (~28 high).  Only S counts as evidence.
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

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V289_WRITE", "").strip().lower()
FULL = ("--full" in sys.argv) or os.environ.get("ACCORD_V289_FULL", "") == "1"   # long sweeps; default FAST (< 60 s)
TICK_HZ = 1000.0           # BELIEF (0xC64DF=100 debounce measured 100.00 ms on the wire); numbers only

BASE_NAME = ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080"
             ".TORQUE.TAP_plain_image.bin")
BASE_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
PARENT_NAME = ("_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
               "_plain_image.bin")
PARENT_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"
V288_IMG_SHA = "94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c"   # NOT the base

TAG = ("V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5"
       "-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP")
IMG_NAME = f"_v289_{TAG}_plain_image.bin"
RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"

# ---- the ONE switch the brief asked for ---------------------------------------------------------
INIT_ON_SENTINEL = os.environ.get("ACCORD_V289_INIT", "") == "1"
                            # True adds a prologue that zeroes s1/s2/e on the tick after gp-0x6cf8 ==
                            # 0x7FFFFFFF (a hook-skipping tick in the V288 sense).  Shipped FALSE: this
                            # hook is never skipped, so there is no stale state (see docstring).  The
                            # env flip exists so the True path can be assembled and tested on a scratch
                            # run; the write path refuses it.
if INIT_ON_SENTINEL:
    TAG = TAG.replace("SUMNOTCH.", "SUMNOTCH.EINIT.")
    IMG_NAME = f"_v289_{TAG}_plain_image.bin"
    RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
# the hashes the shipped (INIT_ON_SENTINEL = False) build produced on 2026-09-08 and every re-run must reproduce
EXPECTED_IMG_SHA = "f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed"
EXPECTED_RWD_SHA = "20fa175721eb9712cd9aada27c6ecc84e43108fcdd0c21d387b80db4a105625c"

# ---- registers ---------------------------------------------------------------------------------
R0, GP, TP, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16, R22, R24, R26, R27, R29, LP = \
    0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 22, 24, 26, 27, 29, 31

# ---- [1] the notch hook -------------------------------------------------------------------------
HOOK = 0x2A174
HOOK_OLD = bytes.fromhex("e53fef73")   # ld.hu 0x73ee,tp,r7
HOOK_RET = 0x2A178                     # ld.w -0x3d3c,gp,r9 -- resume here, untouched
LAG_B_TP = 0x73EE                      # tp+0x73ee = 0xC63EE (507) -- the displaced load's operand
SUM_CLAMP_TP = 0x71BE                  # tp+0x71be = 0xC61BE (15360) -- the sum clamp; our output clamp reads it
TP_BASE, GP_BASE = 0xBF000, 0xFEDF8000
HOOK_WINDOW = (0x2A13A, 0x2A1B4)       # re-encoded byte-identically at [1c]
LIVE_ACROSS_HOOK = (R11, R14, R15, R16, R22, R24, R27, R29, LP)   # r11/r14/r15 read at 0x2A1FC/0x2A1E6/0x2A228 with no prior write
SCRATCH = (R6, R7, R9, R13)

# ---- [1b] the notch, Q14 ------------------------------------------------------------------------
NOTCH_F0_DESIGN, NOTCH_Q_DESIGN = 20.05, 3.0
QSH = 14
B0, B1, B2 = 16048, -31842, 16048
A0, A1, A2 = 16384, -31842, 15712
assert B0 == B2 and A1 == B1 and A0 == 1 << QSH
S_MAX = 15360                          # |x| bound = the sum clamp (read from the image at [1])

# ---- [1c] RAM: the run gp-0x6c44..gp-0x6c39 -----------------------------------------------------
S1_DISP, S2_DISP, E_DISP, FLAG_DISP = -0x6C44, -0x6C40, -0x6C3C, -0x6C3A
STATE_RUN = (-0x6C44, 12)              # (first byte disp, length) -- censused at [2]
DATA_RAM_LO, DATA_RAM_HI, DATA_ROM_LO = 0xFEDF11B0, 0xFEDF5A68, 0x86260   # .data copy (kit memory)
E_MASK = 0x3FFF

# ---- [1d] the sentinel (only used if INIT_ON_SENTINEL) -------------------------------------------
EINIT_CELL_DISP, EINIT_SENTINEL = -0x6CF8, 0x7FFFFFFF

# ---- [2] the fb pole ----------------------------------------------------------------------------
FB_A_CELL, FB_A_OLD, FB_A_NEW = 0xC63E8, 923, 875
FB_B_CELL, FB_B_OLD, FB_B_NEW = 0xC63EA, 1560, 2301
FB_A_LOAD, FB_A_LOAD_BYTES = 0x28F8A, bytes.fromhex("254fe873")   # ld.h  0x73e8,tp,r9   SIGNED
FB_B_LOAD, FB_B_LOAD_BYTES = 0x28F86, bytes.fromhex("e587eb73")   # ld.hu 0x73ea,tp,r16  UNSIGNED
FB_X_GUARD = 12000
FB_CLAMP_CELL, FB_CLAMP = 0xC62E6, 46080

# ---- [3] the 0x14A telemetry cave ---------------------------------------------------------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8
CAVE_EPILOGUE = 0xC4BD2               # movea -0x1518,gp,r6
CAVE_JMP_LP = 0xC4BD6                 # jmp [lp]
CAVE_JMP_LP_OLD = bytes.fromhex("7f00")
BUF_BYTE4_DISP, BUF_BASE_DISP = -0x1514, -0x1518
CAVE_HOOK, CAVE_HOOK4 = 0x55C0E, bytes.fromhex("86ff26ef")
BIT_SIGN, BIT_CMP = 0x20, 0x80
OUR_BITS = BIT_SIGN | BIT_CMP         # 0xA0
TAIL_MASK = 0xFF & ~OUR_BITS          # 0x5F
STOCK_B4_BITS = 0x07
STOCK_B4_WRITERS = {0x55AC0: bytes.fromhex("4447ecea"), 0x55AE8: bytes.fromhex("4437ecea"),
                    0x55B06: bytes.fromhex("447fecea")}
STOCK_B4_MASKS = {0x55AB4: 0xFB, 0x55ADC: 0xFD, 0x55AFC: 0xFE}

# ---- [4] free flash / layout --------------------------------------------------------------------
FREE_LO, FREE_HI = 0xC4BD8, 0xC4FF0
STRUCT_LO, STRUCT_HI = 0xC4FF0, 0xC4FFC
TELE = 0xC4BDC                        # 28 B tail
NOTCH = 0xC4C00                       # the notch cave (extent derived from the emitted bytes)

PACK_LO, PACK_HI = 0x55DF0, 0x55E12
MAP_PTR, MAP_N = 0xC9A88, 10
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y = (0, 68, 112, 136, 208), (248,) * 5
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

FROZEN = {
    0xC61B2: 3072, 0xC61B4: 3072, 0xC61B6: 10240, 0xC61BA: 10240, 0xC61BC: 15360, 0xC61BE: 15360,
    0xC63E6: 0, 0xC63EC: 992, 0xC63EE: 507, 0xC62E4: 4, 0xC62E6: 46080, 0xC6446: 5244,
    0xC644A: 1024, 0xC6AE6: 2048, 0xC6B12: 98, 0xC6B26: 256, 0xC6CD0: 5346,
}
MOVED = {FB_A_CELL: (FB_A_OLD, FB_A_NEW), FB_B_CELL: (FB_B_OLD, FB_B_NEW)}

OK, BAD = "[PASS]", "[FAIL]"
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


def _s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


# ==================================================================================================
#  V850E2 ENCODER (V288's, verbatim where reused, + mul / movea-r0 / andi imm16 / ld.hu-tp forms).
#  Every form is positive-controlled at [1c]/[1d] against bytes already on the flown V282 image.
# ==================================================================================================
OP1 = {"mov": 0x00, "jmp": 0x03, "mulh": 0x07, "or": 0x08, "subr": 0x0C, "sub": 0x0D,
       "add": 0x0E, "cmp": 0x0F}
OP2 = {"movi": 0x10, "addi5": 0x12, "cmpi": 0x13, "shr": 0x14, "sar": 0x15, "shl": 0x16}
OP67 = {"addi": 0x30, "movea": 0x31, "andi": 0x36, "ld.b": 0x38, "ld.h": 0x39, "st.b": 0x3A,
        "st.h": 0x3B, "ld.hu": 0x3F}
COND = {"bl": 0x1, "be": 0x2, "br": 0x5, "blt": 0x6, "ble": 0x7, "bne": 0xA, "bge": 0xE, "bgt": 0xF}


def _hw(v):
    return struct.pack("<H", v & 0xFFFF)


def f1(mn, reg1, reg2):
    """Format I, 2 B: reg2[15:11] | op[10:5] | reg1[4:0].  reg2 <- reg2 OP reg1 (mov: reg2 <- reg1)."""
    return _hw((reg2 << 11) | (OP1[mn] << 5) | reg1)


def f2(mn, imm5, reg2):
    assert -16 <= imm5 <= 31
    return _hw((reg2 << 11) | (OP2[mn] << 5) | (imm5 & 0x1F))


def f67(mn, reg1, reg2, disp):
    return _hw((reg2 << 11) | (OP67[mn] << 5) | reg1) + _hw(disp)


def ld_h(disp, base, dst):
    assert disp % 2 == 0, f"ld.h disp {disp:#x} must be EVEN (odd hw2 bit0 -> ld.w)"
    return f67("ld.h", base, dst, disp)


def ld_hu(disp, base, dst):
    """hw2 bit 0 is FIXED 1 in ld.hu (V850 has no ld.wu); the displacement must be even."""
    assert disp % 2 == 0
    return f67("ld.hu", base, dst, (disp & 0xFFFE) | 1)


def st_h(src, disp, base):
    assert disp % 2 == 0, f"st.h disp {disp:#x} must be EVEN (odd hw2 bit0 -> st.w)"
    return f67("st.h", base, src, disp)


def ld_w(disp, base, dst):
    assert disp % 4 == 0, f"ld.w disp {disp:#x} must be word-aligned"
    return f67("ld.h", base, dst, (disp & 0xFFFE) | 1)


def st_w(src, disp, base):
    assert disp % 4 == 0, f"st.w disp {disp:#x} must be word-aligned"
    return f67("st.h", base, src, (disp & 0xFFFE) | 1)


def ld_bu(disp, base, dst):
    hw1 = (dst << 11) | ((0x3C | (disp & 1)) << 5) | base
    return _hw(hw1) + _hw((disp & 0xFFFE) | 1)


def st_b(src, disp, base):
    return f67("st.b", base, src, disp)


def movea(imm, base, dst):
    assert -32768 <= imm <= 32767
    return f67("movea", base, dst, imm)


def andi(imm16, reg1, reg2):
    assert 0 <= imm16 <= 0xFFFF
    return f67("andi", reg1, reg2, imm16)


def mul(reg1, reg2, reg3=R0):
    """Format XI, 4 B: reg2[15:11] | 0x3F<<5 | reg1 ; hw2 = reg3[15:11] | 0x220.
    (reg3,reg2) <- reg2 * reg1 signed 64-bit; reg3 = r0 discards the high word.
    Controls: 0x2A180 `mul r7,r12,r0` = e7 67 20 02, 0x28F8E `mul r16,r7,r0` = f0 3f 20 02."""
    return _hw((reg2 << 11) | (0x3F << 5) | reg1) + _hw((reg3 << 11) | 0x0220)


def mov_imm32(imm, reg1):
    return _hw((0 << 11) | (0x31 << 5) | reg1) + struct.pack("<i", imm if imm < (1 << 31) else imm - (1 << 32))


def bcond(mn, disp):
    assert disp % 2 == 0 and -256 <= disp <= 254, f"Bcond disp {disp} out of the 9-bit signed range"
    d = disp & 0x1FF
    return _hw(((d >> 4) << 11) | (0b1011 << 7) | (((d >> 1) & 0x7) << 4) | COND[mn])


def _fmt5(pc, target, lnk):
    d = target - pc
    assert d % 2 == 0 and -(1 << 21) <= d < (1 << 21), f"Format-V disp22 out of range: {d:#x}"
    d &= 0x3FFFFF
    return _hw((lnk << 11) | (0x1E << 6) | ((d >> 16) & 0x3F)) + _hw(d & 0xFFFE)


def jr(pc, target):
    return _fmt5(pc, target, 0)


def jarl(pc, target, lnk):
    return _fmt5(pc, target, lnk)


# ==================================================================================================
#  THE INDEPENDENT DECODER.  Written from the ISA field layout, NOT by inverting the encoder above:
#  it is table-driven on opcode fields and renders Ghidra-style text.  It is positive-controlled at
#  [1e] against Ghidra's own listing of the stock hook window (captured 2026-09-08, `disassemble_bytes
#  dry_run`), and then used at [5]/[11] to decode the BUILT cave bytes.
# ==================================================================================================
_RN = {0: "r0", 3: "sp", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}


def _rn(r):
    return _RN.get(r, f"r{r}")


def _sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


_COND_NAME = {0x0: "bv", 0x1: "bl", 0x2: "be", 0x3: "bnh", 0x4: "bn", 0x5: "br", 0x6: "blt", 0x7: "ble",
              0x8: "bnv", 0x9: "bnl", 0xA: "bne", 0xB: "bh", 0xC: "bp", 0xD: "bsa", 0xE: "bge", 0xF: "bgt"}
_F1 = {0x00: "mov", 0x01: "not", 0x02: "divh", 0x03: "jmp", 0x04: "satsubr", 0x05: "satsub", 0x06: "satadd",
       0x07: "mulh", 0x08: "or", 0x09: "xor", 0x0A: "and", 0x0B: "tst", 0x0C: "subr", 0x0D: "sub",
       0x0E: "add", 0x0F: "cmp"}
_F2 = {0x10: "mov", 0x11: "satadd", 0x12: "add", 0x13: "cmp", 0x14: "shr", 0x15: "sar", 0x16: "shl",
       0x17: "mulh"}
_F6 = {0x30: "addi", 0x31: "movea", 0x32: "movhi", 0x33: "satsubi", 0x34: "ori", 0x35: "xori",
       0x36: "andi", 0x37: "mulhi"}


def decode_one(b, pc):
    """Return (length, text) for the instruction at b[pc:] (V850E2 subset used by this firmware's
    hook windows and by the caves).  Unknown forms raise, so a mis-encoded byte cannot pass silently."""
    hw1 = u16(b, pc)
    reg1, reg2, op = hw1 & 0x1F, hw1 >> 11, (hw1 >> 5) & 0x3F
    if ((hw1 >> 7) & 0xF) == 0xB and op < 0x30:
        # Format III Bcond: bits 10:7 == 1011, i.e. op field 0x2C..0x2F
        d = ((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1)
        d = _sx(d, 9)
        return 2, f"{_COND_NAME[hw1 & 0xF]} {pc + d:#010x}"
    if op <= 0x0F:
        mn = _F1[op]
        if mn == "jmp":
            return 2, f"jmp [{_rn(reg1)}]"
        if mn == "mov" and reg2 == 0 and reg1 != 0:
            # 6-byte mov imm32 is op 0x31 with reg2 == 0, not here
            pass
        return 2, f"{mn} {_rn(reg1)}, {_rn(reg2)}"
    if 0x10 <= op <= 0x17:
        imm = _sx(reg1, 5) if op in (0x10, 0x11, 0x12, 0x13, 0x17) else reg1
        return 2, f"{_F2[op]} {imm:#x}, {_rn(reg2)}" if imm >= 0 else f"{_F2[op]} -{-imm:#x}, {_rn(reg2)}"
    if 0x18 <= op <= 0x2F:
        raise ValueError(f"short-form sld/sst at {pc:#x} not supported by this decoder")
    hw2 = u16(b, pc + 2)
    if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0:
        d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
        d = _sx(d, 22)
        lnk = hw1 >> 11
        return 4, (f"jr {pc + d:#010x}" if lnk == 0 else f"jarl {pc + d:#010x}, {_rn(lnk)}")
    if op == 0x31 and reg2 == 0:
        imm = struct.unpack_from("<i", b, pc + 2)[0]
        return 6, f"mov {imm & 0xFFFFFFFF:#x}, {_rn(reg1)}"
    if op in _F6:
        imm = _sx(hw2, 16) if op in (0x30, 0x31, 0x33) else hw2
        s = f"{imm:#x}" if imm >= 0 else f"-{-imm:#x}"
        return 4, f"{_F6[op]} {s}, {_rn(reg1)}, {_rn(reg2)}"
    if op == 0x3F and (hw2 & 0x7FF) == 0x220:
        return 4, f"mul {_rn(reg1)}, {_rn(reg2)}, {_rn(hw2 >> 11)}"
    if op == 0x3F and (hw2 & 0x7FF) == 0x222:
        return 4, f"mulu {_rn(reg1)}, {_rn(reg2)}, {_rn(hw2 >> 11)}"
    if op in (0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F):
        if op == 0x38:
            mn, d = "ld.b", _sx(hw2, 16)
        elif op == 0x3A:
            mn, d = "st.b", _sx(hw2, 16)
        elif op == 0x39:
            mn, d = ("ld.w" if hw2 & 1 else "ld.h"), _sx(hw2 & 0xFFFE, 16)
        elif op == 0x3B:
            mn, d = ("st.w" if hw2 & 1 else "st.h"), _sx(hw2 & 0xFFFE, 16)
        elif op == 0x3F:
            if not hw2 & 1:
                raise ValueError(f"op 0x3F with even hw2 at {pc:#x}: not ld.hu")
            mn, d = "ld.hu", _sx(hw2 & 0xFFFE, 16)
        else:
            if not hw2 & 1:
                raise ValueError(f"op 0x3C/0x3D with even hw2 at {pc:#x}: Format V, handled above")
            mn, d = "ld.bu", _sx((hw2 & 0xFFFE) | (op & 1), 16)
        s = f"{d:#x}" if d >= 0 else f"-{-d:#x}"
        if mn.startswith("st"):
            return 4, f"{mn} {_rn(reg2)}, {s}, {_rn(reg1)}"
        return 4, f"{mn} {s}, {_rn(reg1)}, {_rn(reg2)}"
    raise ValueError(f"undecodable halfword {hw1:#06x} at {pc:#x}")


def decode_range(b, lo, hi):
    out, pc = [], lo
    while pc < hi:
        n, txt = decode_one(b, pc)
        out.append((pc, n, txt))
        pc += n
    return out


def _norm(t):
    return " ".join(t.replace(",", " ").split()).lower()


# Ghidra's listing of the stock hook neighbourhood (disassemble_bytes dry_run, program code.bin,
# 2026-09-08).  The decoder must reproduce every one of these before its reading of the caves counts.
GHIDRA_STOCK_LISTING = {
    0x2A13A: "mulh r10, r12", 0x2A13C: "subr r0, r12", 0x2A13E: "ld.hu 0x71be, tp, r9",
    0x2A142: "cmp r9, r12", 0x2A144: "ble 0x0002a14c", 0x2A146: "ld.h 0x71be, tp, r12",
    0x2A14A: "br 0x0002a174", 0x2A14C: "ld.hu 0x71be, tp, r6", 0x2A150: "subr r0, r6",
    0x2A152: "cmp r6, r12", 0x2A154: "bge 0x0002a160", 0x2A156: "ld.hu 0x71be, tp, r12",
    0x2A15A: "subr r0, r12", 0x2A15E: "br 0x0002a174", 0x2A162: "br 0x0002a174",
    0x2A164: "mov 0x0, r24", 0x2A166: "mov 0x0, r29", 0x2A168: "mov 0x0, r27", 0x2A16A: "mov 0x0, r22",
    0x2A16C: "mov 0x7fffffff, r16", 0x2A172: "mov 0x0, r12", 0x2A174: "ld.hu 0x73ee, tp, r7",
    0x2A178: "ld.w -0x3d3c, gp, r9", 0x2A17C: "st.h r12, -0x6b2e, gp", 0x2A180: "mul r7, r12, r0",
    0x2A184: "ld.h 0x73ec, tp, r7", 0x2A188: "st.h r29, -0x6b32, gp", 0x2A18C: "st.w r16, -0x6cf8, gp",
    0x2A190: "st.w r24, -0x6dd0, gp", 0x2A194: "mul r9, r7, r0", 0x2A198: "ld.bu 0x74a3, tp, r16",
    0x2A19C: "st.h r27, -0x6b36, gp", 0x2A1A0: "sar 0xa, r12", 0x2A1A2: "st.h r22, -0x6b34, gp",
    0x2A1A6: "sar 0xa, r7", 0x2A1A8: "add r12, r7", 0x2A1AA: "add r7, r9", 0x2A1AC: "sar 0x5, r9",
    0x2A1AE: "cmp 0x1, r16", 0x2A1B0: "st.w r7, -0x3d3c, gp", 0x2A1B4: "bne 0x0002a1e6",
    0x2A1B6: "ld.bu -0x6806, gp, r12", 0x2A1BE: "ld.h 0x71b8, tp, r6", 0x2A1D4: "ld.h -0x6b30, gp, r13",
    0x2A1DA: "mul r13, r6, r0", 0x2A1E6: "mul r14, r9, r0", 0x2A1F2: "ld.b -0x6752, gp, r13",
    0x28F86: "ld.hu 0x73ea, tp, r16", 0x28F8A: "ld.h 0x73e8, tp, r9", 0x28F8E: "mul r16, r7, r0",
    0x55C0E: "movea -0x1518, gp, r6", 0x55C12: "mov 0x8, r7", 0x55C14: "movea 0x14a, r0, r8",
    0x55BF6: "andi 0x3, r10, r6", 0x26E9E: "sar 0xe, r7", 0x2A256: "movea 0x400, r0, r8",
    0x1C1C2: "shl 0x4, r7", 0x55AD4: "ld.bu -0x1514, gp, r6", 0x55AE8: "st.b r6, -0x1514, gp",
    0x14AAA: "jmp [lp]", 0x29D82: "ble 0x00029d8c", 0x1AFD0: "be 0x0001afd4",
}
# 0x55C0E is `jarl 0xc4b34,lp` on V282 (the V105+ hook); the movea text above is STOCK's, checked against
# the stock bytes 24 36 e8 ea that the cave's own epilogue at 0xC4BD2 carries.
GHIDRA_BYTES_OVERRIDE = {0x55C0E: bytes.fromhex("2436e8ea")}


# ==================================================================================================
#  THE CAVES.  (address, bytes, mnemonic, comment).  Sizes are SUMMED, never assumed.
# ==================================================================================================
def notch_cave(at=NOTCH, ret=HOOK_RET, init=INIT_ON_SENTINEL):
    """Entered by `jr` from 0x2A174 with r12 = S (clamped, |S| <= 15360).  Leaves r12 = clamp(y),
    r7 = cal(0xC63EE) (the displaced load), FLAG halfword written, and returns to 0x2A178.
    Uses r6, r7, r9, r13 only.  No jarl.  No write to r14/r16/r22/r24/r27/r29/lp."""
    seq = []
    if init:
        seq += [
            (ld_w(EINIT_CELL_DISP, GP, R6), "ld.w  -0x6cf8[gp],r6", "Honda's shared-epilogue marker, previous tick"),
            (mov_imm32(EINIT_SENTINEL, R9), "mov   0x7fffffff,r9", "the sentinel"),
            (f1("cmp", R9, R6), "cmp   r9,r6", "== ?"),
            (bcond("bne", 2 + 12), "bne   +14", "not a first tick -> skip the zeroing"),
            (st_w(R0, S1_DISP, GP), "st.w  r0,-0x6c44[gp]", "s1 := 0"),
            (st_w(R0, S2_DISP, GP), "st.w  r0,-0x6c40[gp]", "s2 := 0"),
            (st_w(R0, E_DISP, GP), "st.w  r0,-0x6c3c[gp]", "e := 0, FLAG := 0"),
        ]
    seq += [
        # ---- acc = b0*x + s1 + e -----------------------------------------------------------------
        (ld_w(S1_DISP, GP, R9),       "ld.w  -0x6c44[gp],r9",   "r9 = s1"),
        (ld_w(E_DISP, GP, R13),       "ld.w  -0x6c3c[gp],r13",  "r13 = (FLAG<<16) | e"),
        (andi(E_MASK, R13, R13),      "andi  0x3fff,r13,r13",   "r13 = e  (strips the FLAG half; also boot-safe)"),
        (f1("add", R13, R9),          "add   r13,r9",           "r9 = s1 + e"),
        (movea(B0, R0, R13),          f"movea 0x{B0:x},r0,r13",     "r13 = b0"),
        (mul(R12, R13),               "mul   r12,r13,r0",       "r13 = b0*x  (low 32; |b0*x| <= 2.47e8)"),
        (f1("mov", R13, R7),          "mov   r13,r7",           "r7 = b0*x, kept for s2'"),
        (f1("add", R13, R9),          "add   r13,r9",           "r9 = acc = b0*x + s1 + e"),
        # ---- y, e' -------------------------------------------------------------------------------
        (f1("mov", R9, R6),           "mov   r9,r6",            ""),
        (f2("sar", QSH, R6),          f"sar   0x{QSH:x},r6",    "r6 = y = acc >> 14  (arithmetic: floors)"),
        (andi(E_MASK, R9, R9),        "andi  0x3fff,r9,r9",     "r9 = e' = acc & 0x3fff  (acc == (y<<14) + e')"),
        (st_w(R9, E_DISP, GP),        "st.w  r9,-0x6c3c[gp]",   "e := e'  (FLAG half := 0 for now)"),
        # ---- s2' = b0*x - a2*y -------------------------------------------------------------------
        (movea(A2, R0, R13),          f"movea 0x{A2:x},r0,r13",     "r13 = a2"),
        (mul(R6, R13),                "mul   r6,r13,r0",        "r13 = a2*y"),
        (f1("sub", R13, R7),          "sub   r13,r7",           "r7 = s2' = b0*x - a2*y"),
        (ld_w(S2_DISP, GP, R13),      "ld.w  -0x6c40[gp],r13",  "r13 = s2 (old)"),
        (st_w(R7, S2_DISP, GP),       "st.w  r7,-0x6c40[gp]",   "s2 := s2'"),
        # ---- n = x - y ; s1' = b1*n + s2_old ----------------------------------------------------
        (f1("mov", R12, R9),          "mov   r12,r9",           ""),
        (f1("sub", R6, R9),           "sub   r6,r9",            "r9 = n = x - y  (the removed component)"),
        (movea(B1, R0, R7),           f"movea -0x{-B1:x},r0,r7",      "r7 = b1 (== a1)"),
        (mul(R9, R7),                 "mul   r9,r7,r0",         "r7 = b1*n"),
        (f1("add", R7, R13),          "add   r7,r13",           "r13 = s1' = b1*n + s2_old"),
        (st_w(R13, S1_DISP, GP),      "st.w  r13,-0x6c44[gp]",  "s1 := s1'"),
        # ---- FLAG: bit5 = n<0 ; bit7 = |n| >= |y| ---------------------------------------------
        (f2("movi", 0, R13),          "mov   0x0,r13",          "flag nibble = 0"),
        (f2("cmpi", 0, R9),           "cmp   0x0,r9",           "n < 0 ?"),
        (bcond("bge", 4),             "bge   +4",               ""),
        (f2("movi", BIT_SIGN >> 4, R13), f"mov   0x{BIT_SIGN >> 4:x},r13", "n < 0 -> 2 (becomes 0x20 after shl 4)"),
        (f1("mov", R6, R12),          "mov   r6,r12",           "r12 = y (the output, pre-clamp); x is dead now"),
        (f1("mov", R9, R7),           "mov   r9,r7",            ""),
        (f2("cmpi", 0, R7),           "cmp   0x0,r7",           ""),
        (bcond("bge", 4),             "bge   +4",               ""),
        (f1("subr", R0, R7),          "subr  r0,r7",            "r7 = |n|"),
        (f2("cmpi", 0, R6),           "cmp   0x0,r6",           ""),
        (bcond("bge", 4),             "bge   +4",               ""),
        (f1("subr", R0, R6),          "subr  r0,r6",            "r6 = |y|"),
        (f1("cmp", R6, R7),           "cmp   r6,r7",            "flags of |n| - |y|"),
        (f2("movi", BIT_CMP >> 4, R7), f"mov   0x{BIT_CMP >> 4:x},r7", "8 (becomes 0x80)"),
        (bcond("bge", 4),             "bge   +4",               "|n| >= |y| -> keep"),
        (f2("movi", 0, R7),           "mov   0x0,r7",           ""),
        (f1("or", R7, R13),           "or    r7,r13",           "nibble = {0,2,8,10}"),
        (f2("shl", 4, R13),           "shl   0x4,r13",          "r13 = FLAG in {0,0x20,0x80,0xa0}"),
        (st_h(R13, FLAG_DISP, GP),    "st.h  r13,-0x6c3a[gp]",  "FLAG := the two bits (high half of the e word)"),
        # ---- output clamp to +-cal(0xC61BE), the sum clamp's own cell ----------------------------
        (ld_hu(SUM_CLAMP_TP, TP, R9), "ld.hu 0x71be[tp],r9",    "r9 = +L (15360)"),
        (f1("cmp", R9, R12),          "cmp   r9,r12",           "y - L"),
        (bcond("ble", 4),             "ble   +4",               "y <= L -> skip"),
        (f1("mov", R9, R12),          "mov   r9,r12",           "y := L"),
        (f1("subr", R0, R9),          "subr  r0,r9",            "r9 = -L"),
        (f1("cmp", R9, R12),          "cmp   r9,r12",           "y + L"),
        (bcond("bge", 4),             "bge   +4",               "y >= -L -> skip"),
        (f1("mov", R9, R12),          "mov   r9,r12",           "y := -L"),
        # ---- the displaced instruction, then home ------------------------------------------------
        (ld_hu(LAG_B_TP, TP, R7),     "ld.hu 0x73ee[tp],r7",    "REPLICATED displaced load: r7 = 507"),
    ]
    out, pc = [], at
    for by, mn, cm in seq:
        out.append((pc, by, mn, cm))
        pc += len(by)
    out.append((pc, jr(pc, ret), f"jr    0x{ret:05x}", "resume at the untouched ld.w -0x3d3c,gp,r9"))
    return out


def telemetry_rung(at=TELE):
    """Entered by `jr` from 0xC4BD6 (where `jmp [lp]` was).  r6/r7 scratch (the caller sets r7/r8
    immediately after; r6 is the return value the relocated movea restores).  lp untouched."""
    seq = [
        (ld_hu(FLAG_DISP, GP, R7),      "ld.hu -0x6c3a[gp],r7",  "r7 = FLAG  (one atomic halfword load)"),
        (andi(OUR_BITS, R7, R7),        f"andi  0x{OUR_BITS:x},r7,r7", "keep bits 7 and 5 ONLY, whatever RAM held"),
        (ld_bu(BUF_BYTE4_DISP, GP, R6), "ld.bu -0x1514[gp],r6",  "0x14A byte 4"),
        (andi(TAIL_MASK, R6, R6),       f"andi  0x{TAIL_MASK:x},r6,r6", "clear bits 7 and 5; stock 0-2 and ours 6,4,3 kept"),
        (f1("or", R7, R6),              "or    r7,r6",           ""),
        (st_b(R6, BUF_BYTE4_DISP, GP),  "st.b  r6,-0x1514[gp]",  "write back; runs AFTER the flown rungs, so wins"),
        (movea(BUF_BASE_DISP, GP, R6),  "movea -0x1518,gp,r6",   "RELOCATED epilogue: r6 = buffer base"),
        (f1("jmp", LP, R0),             "jmp   [lp]",            "RELOCATED epilogue: return"),
    ]
    out, pc = [], at
    for by, mn, cm in seq:
        out.append((pc, by, mn, cm))
        pc += len(by)
    return out


# ==================================================================================================
#  THE ALGORITHMIC MIRROR (what the cave is meant to compute) and the BYTE-LEVEL EMULATOR (what the
#  emitted bytes actually do).  [4] asserts they agree on every test and that nothing wraps.
# ==================================================================================================
def notch_tick(x, st, wrapcheck=None):
    """st = [s1, s2, e]; returns (y_out_clamped, y_lin, n, flag).  Exact-integer; V850 sar == Python >>
    on negative operands (both floor), mul low word == Python product when |product| < 2^31 (asserted
    by wrapcheck).  Addresses in the comments are those of the emitted cave (checked at [4c])."""
    s1, s2, e = st
    e &= E_MASK                                  # 0xC4C08 andi 0x3fff
    b0x = B0 * x                                 # 0xC4C12 mul r12,r13
    acc = s1 + e + b0x                           # 0xC4C0C add ; 0xC4C18 add
    y = acc >> QSH                               # 0xC4C1C sar 0xe
    e2 = acc & E_MASK                            # 0xC4C1E andi 0x3fff
    a2y = A2 * y                                 # 0xC4C2A mul r6,r13
    s2n = b0x - a2y                              # 0xC4C2E sub r13,r7
    n = x - y                                    # 0xC4C3A sub r6,r9
    b1n = B1 * n                                 # 0xC4C40 mul r9,r7
    s1n = b1n + s2                               # 0xC4C44 add r7,r13
    flag = (BIT_SIGN if n < 0 else 0) | (BIT_CMP if abs(n) >= abs(y) else 0)
    L = S_MAX
    yo = L if y > L else (-L if y < -L else y)
    if wrapcheck is not None:
        for k, v in (("s1", s1n), ("s2", s2n), ("acc", acc), ("b0x", b0x), ("a2y", a2y), ("b1n", b1n),
                     ("s1e", s1 + e), ("y", y), ("n", n)):
            wrapcheck[k] = max(wrapcheck.get(k, 0), abs(v))
            if not -(1 << 31) <= v < (1 << 31):
                wrapcheck["wraps"] = wrapcheck.get("wraps", 0) + 1
        wrapcheck["all"] = max(wrapcheck.get("all", 0), max(abs(v) for v in (b0x, acc, a2y, s2n, b1n, s1n, s1 + e)))
    st[:] = [s1n, s2n, e2]
    return yo, y, n, flag


class V850Emu:
    """Executes the actual cave bytes.  Registers wrap to 32 bits; mul keeps the low word; sar floors;
    Bcond on signed compare semantics; gp/tp memory is a dict of byte-addressed cells."""

    def __init__(self, img, mem=None):
        self.img = img
        self.r = [0] * 32
        self.mem = mem if mem is not None else {}
        self.flags = (0, 0, 0, 0)          # (Z, S, OV, CY)
        self.trace = []

    def _rd(self, a, n, signed):
        v = 0
        for i in range(n):
            v |= self.mem.get(a + i, 0) << (8 * i)
        if signed and v & (1 << (8 * n - 1)):
            v -= 1 << (8 * n)
        return v & 0xFFFFFFFF

    def _wr(self, a, n, v):
        for i in range(n):
            self.mem[a + i] = (v >> (8 * i)) & 0xFF

    def _set(self, r, v):
        if r != 0:
            self.r[r] = v & 0xFFFFFFFF

    def _cmp(self, a, b):   # flags of b - a (reg2 - reg1)
        sa, sb = _s32(a), _s32(b)
        d = sb - sa
        Z = int(d == 0)
        S = int((d & 0xFFFFFFFF) >> 31)
        OV = int(not (-(1 << 31) <= d < (1 << 31)))
        CY = int((b & 0xFFFFFFFF) < (a & 0xFFFFFFFF))
        self.flags = (Z, S, OV, CY)

    def _cond(self, c):
        Z, S, OV, CY = self.flags
        return {0x1: CY, 0x2: Z, 0x5: 1, 0x6: S ^ OV, 0x7: (S ^ OV) | Z, 0xA: 1 - Z,
                0xE: 1 - (S ^ OV), 0xF: 1 - ((S ^ OV) | Z), 0xC: 1 - S, 0x4: S}[c]

    def run(self, pc, stop_at, max_steps=500):
        b = self.img
        steps = 0
        while pc != stop_at:
            steps += 1
            assert steps < max_steps, "runaway"
            hw1 = u16(b, pc)
            reg1, reg2, op = hw1 & 0x1F, hw1 >> 11, (hw1 >> 5) & 0x3F
            self.trace.append(pc)
            if ((hw1 >> 7) & 0xF) == 0xB and op < 0x30:
                d = _sx(((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1), 9)
                pc = pc + d if self._cond(hw1 & 0xF) else pc + 2
                continue
            if op <= 0x0F:
                a, bb = self.r[reg1], self.r[reg2]
                if op == 0x00:
                    self._set(reg2, a)
                elif op == 0x03:
                    pc = self.r[reg1]
                    continue
                elif op == 0x08:
                    self._set(reg2, a | bb)
                elif op == 0x0C:
                    self._set(reg2, a - bb)
                    self._cmp(bb, a)
                elif op == 0x0D:
                    self._set(reg2, bb - a)
                    self._cmp(a, bb)
                elif op == 0x0E:
                    self._set(reg2, a + bb)
                elif op == 0x0F:
                    self._cmp(a, bb)
                else:
                    raise ValueError(f"emu: F1 op {op:#x} at {pc:#x}")
                pc += 2
                continue
            if 0x10 <= op <= 0x17:
                imm = _sx(reg1, 5)
                v = self.r[reg2]
                if op == 0x10:
                    self._set(reg2, imm)
                elif op == 0x13:
                    self._cmp(imm & 0xFFFFFFFF, v)
                elif op == 0x15:
                    self._set(reg2, _s32(v) >> reg1)
                elif op == 0x16:
                    self._set(reg2, v << reg1)
                elif op == 0x14:
                    self._set(reg2, v >> reg1)
                else:
                    raise ValueError(f"emu: F2 op {op:#x} at {pc:#x}")
                pc += 2
                continue
            hw2 = u16(b, pc + 2)
            if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0:
                d = _sx(((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE), 22)
                if (hw1 >> 11) != 0:
                    self._set(hw1 >> 11, pc + 4)
                pc = pc + d
                continue
            if op == 0x31 and reg2 == 0:
                self._set(reg1, struct.unpack_from("<i", b, pc + 2)[0])
                pc += 6
                continue
            base = self.r[reg1]
            if op == 0x31:
                self._set(reg2, base + _sx(hw2, 16))
            elif op == 0x36:
                self._set(reg2, self.r[reg1] & hw2)
            elif op == 0x3F and (hw2 & 0x7FF) == 0x220:
                p = _s32(self.r[reg2]) * _s32(self.r[reg1])
                self._set(reg2, p & 0xFFFFFFFF)
                self._set(hw2 >> 11, (p >> 32) & 0xFFFFFFFF)
            elif op == 0x3F:
                self._set(reg2, self._rd(base + _sx(hw2 & 0xFFFE, 16), 2, False))
            elif op == 0x39:
                d = _sx(hw2 & 0xFFFE, 16)
                self._set(reg2, self._rd(base + d, 4, True) if hw2 & 1 else self._rd(base + d, 2, True))
            elif op == 0x3B:
                d = _sx(hw2 & 0xFFFE, 16)
                self._wr(base + d, 4 if hw2 & 1 else 2, self.r[reg2])
            elif op in (0x3C, 0x3D):
                self._set(reg2, self._rd(base + _sx((hw2 & 0xFFFE) | (op & 1), 16), 1, False))
            elif op == 0x3A:
                self._wr(base + _sx(hw2, 16), 1, self.r[reg2])
            else:
                raise ValueError(f"emu: op {op:#x} at {pc:#x}")
            pc += 4
        return steps


def emu_tick(img, x, mem, entry=HOOK, exit_=HOOK_RET, live_seed=0x51A7E000):
    """One tick through the real hook -> cave -> return.  Returns (r12, regs, mem, steps).  Every
    non-scratch register is seeded with a distinct marker so a clobber is detectable."""
    e = V850Emu(img, mem)
    for i in range(1, 32):
        e.r[i] = (live_seed + i * 0x01010101) & 0xFFFFFFFF
    e.r[GP], e.r[TP], e.r[R12] = GP_BASE, TP_BASE, x & 0xFFFFFFFF
    # the tp-relative cals the cave reads come from the image
    for tpd in (SUM_CLAMP_TP, LAG_B_TP):
        for i in range(2):
            e.mem[TP_BASE + tpd + i] = img[TP_BASE + tpd + i]
    steps = e.run(entry, exit_)
    return _s32(e.r[R12]), e.r, e.mem, steps, e


def mem_state(mem):
    def rd(d, n, signed=True):
        v = 0
        for i in range(n):
            v |= mem.get(GP_BASE + d + i, 0) << (8 * i)
        if signed and v & (1 << (8 * n - 1)):
            v -= 1 << (8 * n)
        return v
    return rd(S1_DISP, 4), rd(S2_DISP, 4), rd(E_DISP, 2, False), rd(FLAG_DISP, 2, False)


def set_state(mem, s1, s2, e, flag=0):
    for d, n, v in ((S1_DISP, 4, s1), (S2_DISP, 4, s2), (E_DISP, 2, e), (FLAG_DISP, 2, flag)):
        for i in range(n):
            mem[GP_BASE + d + i] = (v >> (8 * i)) & 0xFF


# ==================================================================================================
#  ANALYSIS: the realised notch from the INTEGER coefficients, and the l1 worst-case bounds.
# ==================================================================================================
def H(f, fs=TICK_HZ):
    z = complex(math.cos(2 * math.pi * f / fs), math.sin(2 * math.pi * f / fs))
    num = B0 + B1 / z + B2 / z ** 2
    den = A0 + A1 / z + A2 / z ** 2
    return num / den


def realised_notch():
    thz = math.acos(-B1 / (2.0 * B0))
    fz = thz * TICK_HZ / (2 * math.pi)
    # -3 dB points by bisection on each side of fz
    def m(f):
        return abs(H(f))
    lo, hi = 5.0, fz
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if m(mid) > 2 ** -0.5 else (lo, mid)
    f_lo = lo
    lo, hi = fz, 60.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if m(mid) > 2 ** -0.5 else (mid, hi)
    f_hi = lo
    return dict(f0=fz, f_lo=f_lo, f_hi=f_hi, bw=f_hi - f_lo, Q=fz / (f_hi - f_lo),
                r_pole=math.sqrt(A2 / A0),
                f_pole=math.acos(-A1 / (2 * math.sqrt(A0 * A2))) * TICK_HZ / (2 * math.pi))


def impulse_l1(N=6000):
    """Impulse responses of the LINEAR TDF-II (no quantiser) x -> y, s1, s2, acc, in double precision
    (the pole radius is 0.979, so 6000 samples truncate at 0.979^6000 ~ 1e-55), and their l1 norms.
    Worst case |.| under |x| <= X is l1 * X (a theorem for LTI systems)."""
    s1 = s2 = 0.0
    h = {"y": [], "s1": [], "s2": [], "acc": []}
    for nn in range(N):
        x = 1.0 if nn == 0 else 0.0
        acc = B0 * x + s1
        y = acc / A0
        s1n = B1 * x - A1 * y + s2
        s2n = B2 * x - A2 * y
        s1, s2 = s1n, s2n
        h["y"].append(y)
        h["s1"].append(s1)
        h["s2"].append(s2)
        h["acc"].append(acc)
    return {k: sum(abs(v) for v in vals) for k, vals in h.items()}, h


# ==================================================================================================
#  GATE 1 -- byte-granular census of every gp-relative access form.  Positive-controlled.
# ==================================================================================================
def gp_accesses(img):
    """Every gp-based access in [START,END): (addr, kind, first byte disp, width).  Covers the 4-byte
    ld.b/ld.bu/ld.h/ld.hu/ld.w/st.b/st.h/st.w forms (with the hw2-bit0 width flag and the ld.bu
    hw1-bit5 parity steal), the Format VIII bit-ops (set1/clr1/not1/tst1, byte target), the 6-byte
    extended-displacement form (reg2 == 0, op 0x3C/0x3D, disp23), and addi/movea materialisations.
    A linear halfword scan over-reports (it also decodes the middles of longer instructions); that
    is the safe direction for a null."""
    out = []
    for a in range(START, END - 6, 2):
        hw1 = u16(img, a)
        reg1, op, reg2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, hw1 >> 11
        if reg1 != GP:
            continue
        hw2 = u16(img, a + 2)
        if op == 0x38:
            out.append((a, "ld.b", _sx(hw2, 16), 1))
        elif op == 0x3A:
            out.append((a, "st.b", _sx(hw2, 16), 1))
        elif op == 0x39:
            out.append((a, "ld.w" if hw2 & 1 else "ld.h", _sx(hw2 & 0xFFFE, 16), 4 if hw2 & 1 else 2))
        elif op == 0x3B:
            out.append((a, "st.w" if hw2 & 1 else "st.h", _sx(hw2 & 0xFFFE, 16), 4 if hw2 & 1 else 2))
        elif op == 0x3F:
            out.append((a, "ld.hu", _sx(hw2 & 0xFFFE, 16), 2))
        elif op in (0x3C, 0x3D):
            if reg2 == 0:
                hw3 = u16(img, a + 4)
                d = _sx((hw3 << 7) | ((hw2 >> 4) & 0x7F), 23)
                out.append((a, f"ext6.{hw2 & 0xF:x}", d, 4))
            elif hw2 & 1:
                out.append((a, "ld.bu", _sx((hw2 & 0xFFFE) | (op & 1), 16), 1))
        elif op == 0x3E:
            out.append((a, "bitop", _sx(hw2, 16), 1))
        elif op in (0x30, 0x31):
            out.append((a, "addi/movea", _sx(hw2, 16), 1))
    return out


def hits_in(acc, disp, width):
    return [(a, k, d) for a, k, d, w in acc if d < disp + width and d + w > disp]


def literal_and_movhi(img, disp):
    abs_addr = (GP_BASE + disp) & 0xFFFFFFFF
    hi, lo = (abs_addr >> 16) & 0xFFFF, abs_addr & 0xFFFF
    if lo & 0x8000:
        hi = (hi + 1) & 0xFFFF
    lit = [a for a in range(START, END - 4, 2) if u32(img, a) == abs_addr]
    pairs = []
    for a in range(START, END - 20, 2):
        h1 = u16(img, a)
        if ((h1 >> 5) & 0x3F) != 0x32 or u16(img, a + 2) != hi:
            continue
        dst = h1 >> 11
        for j in range(4, 20, 2):
            h1b, h2b = u16(img, a + j), u16(img, a + j + 2)
            if (h1b & 0x1F) == dst and ((h1b >> 5) & 0x3F) >= 0x30 and (h2b & 0xFFFE) == (lo & 0xFFFE):
                pairs.append((a, a + j))
                break
    return lit, pairs


def boot_value(img, disp, n):
    a = GP_BASE + disp
    if not (DATA_RAM_LO <= a < DATA_RAM_HI):
        return None, "bss"
    off = DATA_ROM_LO + (a - DATA_RAM_LO)
    return bytes(img[off:off + n]), f"flash 0x{off:05X}"


# ==================================================================================================
def independent_rebuild(base):
    """SECOND implementation: literal opcode arithmetic, none of the builders/encoders above, generic
    re-CRC.  Shares only module-level addresses/constants."""
    img = bytearray(base)

    def hw(v):
        return struct.pack("<H", v & 0xFFFF)

    def fmt5(pc, tgt, lnk=0):
        d = (tgt - pc) & 0x3FFFFF
        return hw((lnk << 11) | (0x1E << 6) | ((d >> 16) & 0x3F)) + hw(d & 0xFFFE)

    def bc(cond, d):
        dd = d & 0x1FF
        return hw(((dd >> 4) << 11) | (0xB << 7) | (((dd >> 1) & 7) << 4) | cond)

    def LDW(d, r):
        return hw((r << 11) | (0x39 << 5) | 4) + hw((d & 0xFFFE) | 1)

    def STW(r, d):
        return hw((r << 11) | (0x3B << 5) | 4) + hw((d & 0xFFFE) | 1)

    def STH(r, d):
        return hw((r << 11) | (0x3B << 5) | 4) + hw(d & 0xFFFE)

    def LDHU_TP(d, r):
        return hw((r << 11) | (0x3F << 5) | 5) + hw(d | 1)

    def MOVEA(imm, r):
        return hw((r << 11) | (0x31 << 5) | 0) + hw(imm)

    def ANDI(imm, r1, r2):
        return hw((r2 << 11) | (0x36 << 5) | r1) + hw(imm)

    def MUL(r1, r2):
        return hw((r2 << 11) | (0x3F << 5) | r1) + hw(0x0220)

    def F1(op, r1, r2):
        return hw((r2 << 11) | (op << 5) | r1)

    def F2(op, imm, r2):
        return hw((r2 << 11) | (op << 5) | (imm & 0x1F))

    S1, S2, E, FL = S1_DISP & 0xFFFF, S2_DISP & 0xFFFF, E_DISP & 0xFFFF, FLAG_DISP & 0xFFFF
    body = b"".join([
        LDW(S1, 9), LDW(E, 13), ANDI(0x3FFF, 13, 13), F1(0x0E, 13, 9),
        MOVEA(B0, 13), MUL(12, 13), F1(0x00, 13, 7), F1(0x0E, 13, 9),
        F1(0x00, 9, 6), F2(0x15, 14, 6), ANDI(0x3FFF, 9, 9), STW(9, E),
        MOVEA(A2, 13), MUL(6, 13), F1(0x0D, 13, 7), LDW(S2, 13), STW(7, S2),
        F1(0x00, 12, 9), F1(0x0D, 6, 9), MOVEA(B1, 7), MUL(9, 7), F1(0x0E, 7, 13), STW(13, S1),
        F2(0x10, 0, 13), F2(0x13, 0, 9), bc(0xE, 4), F2(0x10, 2, 13),
        F1(0x00, 6, 12), F1(0x00, 9, 7), F2(0x13, 0, 7), bc(0xE, 4), F1(0x0C, 0, 7),
        F2(0x13, 0, 6), bc(0xE, 4), F1(0x0C, 0, 6),
        F1(0x0F, 6, 7), F2(0x10, 8, 7), bc(0xE, 4), F2(0x10, 0, 7), F1(0x08, 7, 13), F2(0x16, 4, 13),
        STH(13, FL),
        LDHU_TP(SUM_CLAMP_TP, 9), F1(0x0F, 9, 12), bc(0x7, 4), F1(0x00, 9, 12),
        F1(0x0C, 0, 9), F1(0x0F, 9, 12), bc(0xE, 4), F1(0x00, 9, 12),
        LDHU_TP(LAG_B_TP, 7),
    ])
    if INIT_ON_SENTINEL:
        pro = (LDW(EINIT_CELL_DISP & 0xFFFF, 6) + hw((0 << 11) | (0x31 << 5) | 9) + struct.pack("<i", EINIT_SENTINEL)
               + F1(0x0F, 9, 6) + bc(0xA, 14) + STW(0, S1) + STW(0, S2) + STW(0, E))
        body = pro + body
    body += fmt5(NOTCH + len(body), HOOK_RET)
    B4 = BUF_BYTE4_DISP & 0xFFFF
    tele = b"".join([
        hw((7 << 11) | (0x3F << 5) | 4) + hw(FL | 1),               # ld.hu -0x6c3a[gp],r7
        ANDI(OUR_BITS, 7, 7),
        hw((6 << 11) | (0x3C << 5) | 4) + hw(B4 | 1),               # ld.bu -0x1514[gp],r6
        ANDI(TAIL_MASK, 6, 6),
        F1(0x08, 7, 6),
        hw((6 << 11) | (0x3A << 5) | 4) + hw(B4),                   # st.b r6,-0x1514[gp]
        hw((6 << 11) | (0x31 << 5) | 4) + hw(BUF_BASE_DISP & 0xFFFF),
        hw((0 << 11) | (0x03 << 5) | 31),
    ])
    touched = set()
    for at, blob in ((HOOK, fmt5(HOOK, NOTCH)), (NOTCH, body), (CAVE_JMP_LP, fmt5(CAVE_JMP_LP, TELE)), (TELE, tele)):
        img[at:at + len(blob)] = blob
        touched |= set(range(at, at + len(blob)))
    for cell, (_o, new) in MOVED.items():
        struct.pack_into("<H", img, cell, new)
        touched |= {cell, cell + 1}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


# ==================================================================================================
def build():
    RN = realised_notch()
    print("=" * 112)
    print("  V289 rev 1 -- V282 + NOTCH on the clamped PID sum (cave @0xC4C00, hook 0x2A174) + fb pole 16.5->25 Hz")
    print(f"  notch realised: f0 {RN['f0']:.3f} Hz, -3 dB {RN['f_lo']:.2f}-{RN['f_hi']:.2f} Hz, Q {RN['Q']:.3f};"
          f" DC {B0 + B1 + B2}/{A0 + A1 + A2}; fb pole DC {2 * FB_B_NEW / (1024 - FB_A_NEW):.4f} (was"
          f" {2 * FB_B_OLD / (1024 - FB_A_OLD):.4f}); INIT_ON_SENTINEL = {INIT_ON_SENTINEL}")
    print("=" * 112)

    # ------------------------------------------------------------------------------------------
    print("\n  [1] BASE = V282 (not V288)")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V282 base sha256 matches build_v282's recorded output", "S")
    check(hashlib.sha256(bytes(base)).hexdigest() != V288_IMG_SHA, "the base is NOT the V288 image", "V")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    for a, (old, _n) in MOVED.items():
        check(u16(base, a) == old, f"base 0x{a:05X} == {old} (about to move)", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y,
          f"base live Kp slot {LIVE_SLOT} == V281 rev 3 flat-248", "V")
    check(bytes(base[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, "base 0x55C0E == jarl 0xc4b34,lp", "V")
    check(u16(base, SUM_CLAMP_TP + TP_BASE) == S_MAX, f"sum clamp cal 0xC61BE == {S_MAX} = |S| bound (tp+0x71be, tp=0xBF000)", "V")
    check(u16(base, LAG_B_TP + TP_BASE) == 507, "0xC63EE == 507 = the value the displaced load produces", "V")

    print("\n  [1b] THE HOOK SITE, AS FOUND")
    check(bytes(base[HOOK:HOOK + 4]) == HOOK_OLD, f"0x{HOOK:05X} == {HOOK_OLD.hex()} = ld.hu 0x73ee,tp,r7 (4 B, jr-length)", "V")
    check(bytes(base[HOOK_RET:HOOK_RET + 4]) == ld_w(-0x3D3C, GP, R9), f"0x{HOOK_RET:05X} == ld.w -0x3d3c,gp,r9 (the return point)", "V")
    check(bytes(base[0x2A172:0x2A174]) == f2("movi", 0, R12), "0x2A172 == mov 0x0,r12 -- the 0x2A164 route enters the hook with S = 0", "V")
    check(bytes(base[0x2A17C:0x2A180]) == st_h(R12, -0x6B2E, GP) and bytes(base[0x2A180:0x2A184]) == mul(R7, R12),
          "0x2A17C/0x2A180 == st.h r12,-0x6b2e ; mul r7,r12,r0 -- r12 IS the value the lag consumes", "V")
    for a in (0x2A14A, 0x2A15E, 0x2A162):
        check(bytes(base[a:a + 2]) == bcond("br", HOOK - a), f"0x{a:05X} == br 0x{HOOK:05X} (a clip branch converging on the hook)", "V")

    print("\n  [1c] ENCODER POSITIVE CONTROL -- the WHOLE 0x2A13A-0x2A1B4 window re-encoded byte-identically")
    win = (f1("mulh", R10, R12) + f1("subr", R0, R12) + ld_hu(SUM_CLAMP_TP, TP, R9) + f1("cmp", R9, R12)
           + bcond("ble", 8) + f67("ld.h", TP, R12, SUM_CLAMP_TP) + bcond("br", HOOK - 0x2A14A)
           + ld_hu(SUM_CLAMP_TP, TP, R6) + f1("subr", R0, R6) + f1("cmp", R6, R12) + bcond("bge", 0x2A160 - 0x2A154)
           + ld_hu(SUM_CLAMP_TP, TP, R12) + f1("subr", R0, R12) + bytes.fromhex("ec00") + bcond("br", HOOK - 0x2A15E)
           + bytes.fromhex("ec00") + bcond("br", HOOK - 0x2A162)
           + f2("movi", 0, R24) + f2("movi", 0, R29) + f2("movi", 0, R27) + f2("movi", 0, R22)
           + mov_imm32(EINIT_SENTINEL, R16) + f2("movi", 0, R12)
           + ld_hu(LAG_B_TP, TP, R7) + ld_w(-0x3D3C, GP, R9) + st_h(R12, -0x6B2E, GP) + mul(R7, R12)
           + f67("ld.h", TP, R7, 0x73EC) + st_h(R29, -0x6B32, GP) + st_w(R16, EINIT_CELL_DISP, GP)
           + st_w(R24, -0x6DD0, GP) + mul(R9, R7) + ld_bu(0x74A3, TP, R16) + st_h(R27, -0x6B36, GP)
           + f2("sar", 10, R12) + st_h(R22, -0x6B34, GP) + f2("sar", 10, R7) + f1("add", R12, R7)
           + f1("add", R7, R9) + f2("sar", 5, R9) + f2("cmpi", 1, R16) + st_w(R7, -0x3D3C, GP))
    check(win == bytes(base[HOOK_WINDOW[0]:HOOK_WINDOW[1]]),
          f"0x{HOOK_WINDOW[0]:05X}-0x{HOOK_WINDOW[1] - 1:05X} ({len(win)} B) re-encodes byte-identically: mulh/subr/ld.hu-tp/"
          "cmp/ble/bge/br/ld.h-tp/movi/mov-imm32/ld.w/st.h/st.w/mul/ld.bu-tp/sar/add/cmpi all controlled", "S")
    tail_win = (movea(BUF_BASE_DISP, GP, R6) + f2("movi", 8, R7) + movea(0x14A, R0, R8))
    check(tail_win == bytes.fromhex("2436e8ea") + bytes(base[0x55C12:0x55C18]),
          "movea gp / movi / movea r0 controlled against the 0x14A cave caller (0x55C0E stock bytes + 0x55C12-0x55C17)", "S")
    check(andi(0x3, R10, R6) == bytes(base[0x55BF6:0x55BFA]) and f2("sar", 14, R7) == bytes(base[0x26E9E:0x26EA0])
          and f2("shl", 4, R7) == bytes(base[0x1C1C2:0x1C1C4]) and f1("or", R7, R6) == bytes(base[0x68728:0x6872A])
          and f1("jmp", LP, R0) == bytes(base[0x14AAA:0x14AAC]) and ld_bu(BUF_BYTE4_DISP, GP, R6) == bytes(base[0x55AD4:0x55AD8])
          and st_b(R6, BUF_BYTE4_DISP, GP) == bytes(base[0x55AE8:0x55AEC]) and mul(R13, R6) == bytes(base[0x2A1DA:0x2A1DE])
          and mul(R16, R7) == bytes(base[0x28F8E:0x28F92]) and jarl(CAVE_HOOK, CAVE_START, LP) == CAVE_HOOK4,
          "andi imm16 / sar 0xe / shl 4 / or / jmp[lp] / ld.bu / st.b / two more mul forms / jarl controlled", "S")
    nfv = okfv = 0
    for a in range(START, END - 6, 2):
        hw1, hw2 = struct.unpack_from("<HH", base, a)
        if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and hw1 != 0xFFFF:
            d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
            d -= (1 << 22) if d & (1 << 21) else 0
            nfv += 1
            okfv += (_fmt5(a, a + d, hw1 >> 11) == bytes(base[a:a + 4]))
    check(okfv == nfv and nfv > 5000, f"Format-V disp22 round trip on all {nfv} sites ({okfv} match)", "S")

    print("\n  [1d] THE FLOWN 0x14A CAVE re-encodes byte-identically (the forms the tail reuses)")

    def sgn(cell):
        return ld_h(cell, GP, R6) + f2("cmpi", 0, R6) + bcond("bge", 4) + f1("subr", R0, R6)

    def cmprung(a_, b_, bit):
        return (sgn(a_) + f1("mov", R6, R7) + sgn(b_) + f1("cmp", R6, R7) + f2("movi", bit, R7)
                + bcond("bge", 4) + f2("movi", 0, R7) + f2("shl", 4, R7)
                + ld_bu(BUF_BYTE4_DISP, GP, R6) + andi(0xFF & ~(bit << 4), R6, R6)
                + f1("or", R7, R6) + st_b(R6, BUF_BYTE4_DISP, GP))
    cave_re = (cmprung(-0x6ADA, -0x6B38, 4) + cmprung(-0x6ADA, -0x6B94, 2)
               + f2("movi", 0, R7)
               + ld_h(-0x6B4C, GP, R6) + f2("cmpi", 0, R6) + bcond("bge", 4) + f2("addi5", 8, R7)
               + ld_h(-0x6ADA, GP, R6) + f2("cmpi", 0, R6) + bcond("bge", 4) + f2("addi5", 1, R7)
               + f2("shl", 4, R7)
               + f67("ld.h", GP, R6, (-0x3680) | 1) + f2("cmpi", 0, R6) + bcond("bge", 4) + f2("addi5", 8, R7)
               + ld_bu(BUF_BYTE4_DISP, GP, R6) + andi(0x67, R6, R6) + f1("or", R7, R6) + st_b(R6, BUF_BYTE4_DISP, GP)
               + f2("movi", 3, R7) + f2("shl", 6, R7)
               + ld_bu(-0x1511, GP, R6) + andi(0x3F, R6, R6) + f1("or", R7, R6) + st_b(R6, -0x1511, GP)
               + movea(BUF_BASE_DISP, GP, R6) + f1("jmp", LP, R0))
    check(len(cave_re) == CAVE_END - CAVE_START and cave_re == bytes(base[CAVE_START:CAVE_END]),
          f"the WHOLE {CAVE_END - CAVE_START}-byte 0x14A cave re-encodes byte-identically", "S")
    masks = []
    for a in range(CAVE_START, CAVE_END - 8, 2):
        if bytes(base[a:a + 2]) == andi(0, R6, R6)[:2] and bytes(base[a + 4:a + 6]) == f1("or", R7, R6) \
                and bytes(base[a + 6:a + 10]) == st_b(R6, BUF_BYTE4_DISP, GP):
            masks.append((a, u16(base, a + 2)))
    written = 0
    for _a, m in masks:
        written |= (~m) & 0xFF
    check(len(masks) == 3 and written == 0xF8, f"the cave's 3 byte-4 rungs write bits {written:#04x} = 7,6,5,4,3 (masks {[hex(m) for _, m in masks]})", "V")
    for a, want in STOCK_B4_WRITERS.items():
        check(bytes(base[a:a + 4]) == want, f"0x{a:05X} == {want.hex()} = a STOCK frame-builder writer of byte 4", "V")
    stock_bits = 0
    for a, m in STOCK_B4_MASKS.items():
        check(u16(base, a + 2) == m, f"0x{a:05X} andi 0x{m:02x} (stock rung, bit {(~m & 0xFF).bit_length() - 1})", "V")
        stock_bits |= (~m) & 0xFF
    check(stock_bits == STOCK_B4_BITS and all(a < CAVE_HOOK for a in STOCK_B4_WRITERS),
          "stock owns bits 2,1,0 and all three stock writers run BEFORE the cave hook -- they are NOT free", "S")
    check(OUR_BITS & stock_bits == 0 and OUR_BITS & written == OUR_BITS and TAIL_MASK & STOCK_B4_BITS == STOCK_B4_BITS
          and (~TAIL_MASK & 0xFF) == OUR_BITS,
          f"bits 5 and 7 are the CAVE's; the tail mask 0x{TAIL_MASK:02X} clears exactly them and preserves 2,1,0 (and 6,4,3)", "S")

    print("\n  [1e] THE INDEPENDENT DECODER, positive-controlled against Ghidra's listing of stock code")
    n_ok = 0
    for a, txt in sorted(GHIDRA_STOCK_LISTING.items()):
        src = GHIDRA_BYTES_OVERRIDE.get(a)
        blob = src if src else bytes(base[a:a + 8])
        n_, got = decode_one(blob + b"\0" * 8, 0)
        if src is None:
            got = got  # decoded at pc 0; Bcond/jr targets are pc-relative -> re-decode in place
            n_, got = decode_one(bytes(base), a)
        ok = _norm(got) == _norm(txt)
        n_ok += ok
        if not ok:
            print(f"        MISMATCH 0x{a:05X}: decoder `{got}` vs Ghidra `{txt}`")
    check(n_ok == len(GHIDRA_STOCK_LISTING), f"decoder reproduces Ghidra on {n_ok}/{len(GHIDRA_STOCK_LISTING)} stock instructions"
                                             " (every form the caves use, incl. mul/movea-r0/andi/ld.hu-tp/st.w/Bcond/jr/jmp)", "S")
    # and it must REJECT a deliberately corrupted form rather than guess
    try:
        decode_one(bytes.fromhex("e07f0000") + b"\0" * 8, 0)   # op 0x3F, hw2 even and not the mul/mulu sub-op
        rejected = False
    except ValueError:
        rejected = True
    check(rejected, "decoder REJECTS an undecodable form (raises) instead of guessing -- a bad byte cannot pass silently", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [2] GATE 1 -- RAM census of the state run gp-0x6c44..gp-0x6c39, byte-granular, all forms, controlled")
    acc = gp_accesses(bytes(base))
    ctl = {(-0x3D3C, 4): 4, (-0x6CF8, 4): 4, (-0x6A32, 2): 2, (-0x1514, 1): 14, (-0x6B2E, 2): 3}
    for (d, w), n in ctl.items():
        got = hits_in(acc, d, w)
        check(len(got) == n, f"POSITIVE CONTROL gp{d:+#07x}: {len(got)} hits (expected {n}) -- {[(hex(a), k) for a, k, _ in got][:6]}", "S")
    ctl_b = [(a, k, d) for a, k, d in hits_in(acc, -0x68AD, 1)] + [(a, k, d) for a, k, d in hits_in(acc, -0x68AF, 1)]
    check(any(a == 0x19AE0 and k == "ld.bu" for a, k, _ in ctl_b) and any(a == 0x1FB4E and k == "st.b" for a, k, _ in ctl_b),
          "POSITIVE CONTROL (byte forms): finds Ghidra-confirmed `ld.bu -0x68ad` @0x19AE0 and `st.b -0x68af` @0x1FB4E"
          " -- the byte accesses that disqualify the trace's gp-0x68b0 run", "S")
    ext_ctl = [(a, k, d) for a, k, d in hits_in(acc, -0x4F60, 2) if k.startswith("ext6")]
    check(any(a == 0x59BFA for a, _, _ in ext_ctl), "POSITIVE CONTROL (6-byte form): decodes `ld.h -0x4f60,gp,r6` @0x59BFA (84 07 07 32 61 ff)", "S")
    check(sum(1 for _a, k, _d, _w in acc if k == "bitop") >= 20, "the bit-op class (op 0x3E, gp base) is exercised (>= 20 candidate sites)", "S")
    st_hits = hits_in(acc, STATE_RUN[0], STATE_RUN[1])
    check(st_hits == [], f"ZERO accesses of ANY form touch gp-0x6c44..gp-0x6c39 (12 bytes) in V282 ({st_hits})", "S")
    below, above = hits_in(acc, -0x6C48, 4), hits_in(acc, -0x6C38, 4)
    check(below and above, f"the run's neighbours ARE occupied (gp-0x6c48: {len(below)} hits, gp-0x6c38..: {len(above)}) -- so the"
                           " scanner sees this neighbourhood, and the run is exactly 12 bytes wide", "S")
    for d in (S1_DISP, S2_DISP, E_DISP):
        lit, pairs = literal_and_movhi(bytes(base), d)
        check(not lit and not pairs, f"no dword literal and no movhi/low-half pair materialises 0x{(GP_BASE + d) & 0xFFFFFFFF:08X} (gp{d:+#07x})", "S")
    near = [(hex(a), hex(d)) for a, k, d, w in acc if k == "addi/movea" and STATE_RUN[0] - 0x100 <= d <= STATE_RUN[0] + 0x40]
    check(not near, f"no addi/movea materialises a gp base within [-0x100,+0x40] of the run ({near}) -- no nearby array base to walk from", "S")
    bv, where = boot_value(bytes(base), STATE_RUN[0], 12)
    check(bv == bytes(12), f"the run is in .data and its boot image ({where}) is 12 ZERO bytes -> s1 = s2 = e = FLAG = 0 at power-on", "S")
    print("      RESIDUAL [BELIEF]: a fully register-indirect access from a base not materialised near the cell cannot be")
    print("      excluded statically (the gp-0x1500 precedent).  The run boots clean, has no accessor of any form, and no")
    print("      nearby base -- the same standard the flown gp-0x6a32 cell met.")
    print("\n  [2a] the trace's OTHER two candidate runs, re-censused (why they were NOT used)")
    c_hits = hits_in(acc, -0x68B0, 8)
    check(len(c_hits) >= 3, f"gp-0x68b0..gp-0x68a9 has {len(c_hits)} BYTE accesses (e.g. {[(hex(a), k, hex(d)) for a, k, d in c_hits[:3]]})"
                            " -- the trace certified it free on a halfword sweep; it is NOT free", "S")
    b_hits = hits_in(acc, -0x6AB0, 8)
    bvb, whereb = boot_value(bytes(base), -0x6AB0, 8)
    check(b_hits == [] and bvb != bytes(8),
          f"gp-0x6ab0..gp-0x6aa9 has no direct accessor but boots to {bvb.hex()} ({whereb}) -- initialised data with no"
          " direct reader is the signature of pointer-reached data; not used", "S")
    print("\n  [2b] the S publish cell gp-0x6b2e (now receives the clamped notch output)")
    s_hits = hits_in(acc, -0x6B2E, 2)
    live = [(a, k) for a, k, _ in s_hits if not (0x2A508 <= a < 0x2B422) and not (0x2A30E <= a < 0x2A508)]
    check(live == [(0x2A17C, "st.h")], f"gp-0x6b2e's only LIVE accessor is the writer 0x2A17C; the ld.h 0x2A896 and st.h 0x2B064 sit in the"
                                       f" duplicate PID span [0x2A30E,0x2B422) proven unreachable (TRACE-2026-09-06) -- {s_hits}", "S")

    print("\n  [2c] nothing branches INTO the hook or the return point")
    intos = []
    for a in range(START, END - 6, 2):
        hw1, hw2 = struct.unpack_from("<HH", base, a)
        if ((hw1 >> 7) & 0xF) == 0xB and ((hw1 >> 5) & 0x3F) < 0x30:
            d = ((hw1 >> 11) << 4) | (((hw1 >> 4) & 7) << 1)
            d -= 0x200 if d & 0x100 else 0
            if a + d in (HOOK, HOOK + 2, HOOK_RET):
                intos.append((a, a + d, "Bcond"))
        if ((hw1 >> 6) & 0x1F) == 0x1E and (hw2 & 1) == 0 and hw1 != 0xFFFF:
            d = ((hw1 & 0x3F) << 16) | (hw2 & 0xFFFE)
            d -= (1 << 22) if d & (1 << 21) else 0
            if a + d in (HOOK, HOOK + 2, HOOK_RET):
                intos.append((a, a + d, "Format V"))
    check(sorted(a for a, t, _ in intos if t == HOOK) == [0x2A14A, 0x2A15E, 0x2A162],
          "POSITIVE CONTROL: the branch scan finds exactly the three known `br 0x2a174` (Ghidra xrefs agree)", "S")
    check(not [x for x in intos if x[1] != HOOK],
          f"nothing targets 0x{HOOK + 2:05X} (mid-instruction) or 0x{HOOK_RET:05X} ({[x for x in intos if x[1] != HOOK]})", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [3] EDIT 2 -- the fb pole: widths and signedness from the LOADS, DC held")
    check(bytes(base[FB_A_LOAD:FB_A_LOAD + 4]) == FB_A_LOAD_BYTES == f67("ld.h", TP, R9, 0x73E8),
          f"0x{FB_A_LOAD:05X} == ld.h 0x73e8,tp,r9 (SIGNED 16-bit load of 0xC63E8 = tp+0x73e8)", "V")
    check(bytes(base[FB_B_LOAD:FB_B_LOAD + 4]) == FB_B_LOAD_BYTES == ld_hu(0x73EA, TP, R16),
          f"0x{FB_B_LOAD:05X} == ld.hu 0x73ea,tp,r16 (UNSIGNED 16-bit load of 0xC63EA)", "V")
    check(TP_BASE + 0x73E8 == FB_A_CELL and TP_BASE + 0x73EA == FB_B_CELL, "tp+0x73e8/ea == 0xC63E8/EA (tp = 0xBF000; the off-by-0x1000 trap)", "S")
    check(-32768 <= FB_A_NEW <= 32767 and 0 <= FB_B_NEW <= 65535 and FB_B_NEW < 32768,
          f"{FB_A_NEW} fits the signed load, {FB_B_NEW} fits the unsigned load (and would even fit signed)", "S")
    dc_old, dc_new = 2 * FB_B_OLD / (1024 - FB_A_OLD), 2 * FB_B_NEW / (1024 - FB_A_NEW)
    check(f"{dc_old:.4g}" == f"{dc_new:.4g}" == "30.89", f"DC gain 2b/(1024-a): {dc_old:.6f} -> {dc_new:.6f}, equal to 4 s.f. (30.89)", "S")
    f_old = -math.log(FB_A_OLD / 1024) * TICK_HZ / (2 * math.pi)
    f_new = -math.log(FB_A_NEW / 1024) * TICK_HZ / (2 * math.pi)
    check(16.4 < f_old < 16.6 and 24.9 < f_new < 25.1, f"pole {f_old:.2f} Hz -> {f_new:.2f} Hz", "S")
    s_ss = FB_B_NEW * FB_X_GUARD / (1024 - FB_A_NEW)
    check(FB_A_NEW * s_ss < 2 ** 31 / 10 and FB_B_NEW * FB_X_GUARD < 2 ** 31 / 10 and 2 * s_ss > FB_CLAMP,
          f"fb filter headroom: steady |s| <= {s_ss:.0f} at |x| = {FB_X_GUARD}; a*s = {FB_A_NEW * s_ss:.3g}, b*x = {FB_B_NEW * FB_X_GUARD:.3g}"
          f" (>= 10x inside int32); r26 clamp {FB_CLAMP} still binds before the sum can", "S")
    check(u16(base, FB_CLAMP_CELL) == FB_CLAMP, "0xC62E6 == 46080 (r26 clamp unchanged -> E's bound unchanged)", "V")
    for i, (ff, ph_want) in enumerate(((7.3, 8.0), (3.9, 4.4))):
        def fbH(a_, b_, f):
            z = complex(math.cos(2 * math.pi * f / TICK_HZ), math.sin(2 * math.pi * f / TICK_HZ))
            return (b_ / 1024) * (1 + 1 / z) / (1 - (a_ / 1024) / z)
        dph = math.degrees(math.atan2(fbH(FB_A_NEW, FB_B_NEW, ff).imag, fbH(FB_A_NEW, FB_B_NEW, ff).real)
                           - math.atan2(fbH(FB_A_OLD, FB_B_OLD, ff).imag, fbH(FB_A_OLD, FB_B_OLD, ff).real))
        check(abs(dph - ph_want) < 1.0, f"fb-pole phase change at {ff} Hz = {dph:+.1f} deg (design: {ph_want:+.1f})", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] THE NOTCH -- realised from the integers, l1 bounds, and the byte-level emulator vs the mirror")
    check(B0 + B1 + B2 == A0 + A1 + A2 == 254, f"DC gain EXACTLY 1: B(1) = A(1) = {B0 + B1 + B2}", "S")
    check(B0 - B1 + B2 == A0 - A1 + A2 == 63938, f"Nyquist gain EXACTLY 1: B(-1) = A(-1) = {B0 - B1 + B2}", "S")
    check(B0 == B2, "b0 == b2 -> the zeros are ON the unit circle: infinite depth at the centre in exact arithmetic", "S")
    check(A2 < A0 and A1 * A1 < 4 * A0 * A2, f"poles complex and inside the circle: r = {RN['r_pole']:.5f}", "S")
    check(abs(RN["f0"] - 20.036) < 0.002 and abs(RN["f0"] - NOTCH_F0_DESIGN) < 0.05,
          f"realised centre {RN['f0']:.4f} Hz (design {NOTCH_F0_DESIGN}; within the Q14 quantisation +-0.05 Hz)", "S")
    check(abs(RN["Q"] - NOTCH_Q_DESIGN) < 0.02, f"realised Q {RN['Q']:.4f} (-3 dB {RN['f_lo']:.3f}-{RN['f_hi']:.3f} Hz, BW {RN['bw']:.3f})", "S")
    for f, lo, hi in ((20.05, 0, 0.006), (20.03, 0, 0.003), (20.08, 0, 0.02), (3.9, 0.997, 0.999), (7.3, 0.989, 0.992),
                      (13.5, 0.92, 0.93), (30.0, 0.925, 0.932), (100.0, 0.997, 0.999)):
        m = abs(H(f))
        check(lo <= m <= hi, f"|H({f} Hz)| = {m:.4f} ({20 * math.log10(max(m, 1e-9)):.1f} dB)", "S")
    ph39 = math.degrees(math.atan2(H(3.9).imag, H(3.9).real))
    ph73 = math.degrees(math.atan2(H(7.3).imag, H(7.3).real))
    check(-4.2 < ph39 < -3.5 and -8.5 < ph73 < -7.5, f"phase {ph39:+.2f} deg at 3.9 Hz, {ph73:+.2f} deg at 7.3 Hz (design: -3.8 / -8)", "S")
    l1, hh = impulse_l1()
    bound = {k: v * S_MAX for k, v in l1.items()}
    print(f"      l1 norms: y {l1['y']:.4f}  s1 {l1['s1']:.1f}  s2 {l1['s2']:.1f}  acc {l1['acc']:.1f}")
    check(bound["acc"] + E_MASK < 0.30 * 2 ** 31 and bound["s1"] < 0.16 * 2 ** 31 and bound["s2"] < 0.16 * 2 ** 31,
          f"LINEAR WORST CASE at |x| = {S_MAX}: |acc| <= {bound['acc'] / 2 ** 31:.3f} * 2^31 (+e), |s1| <= {bound['s1'] / 2 ** 31:.3f},"
          f" |s2| <= {bound['s2'] / 2 ** 31:.3f} -- >= 3.8x headroom on every int32", "S")
    check(bound["y"] > 32767, f"|y| linear worst case = {bound['y']:.0f} > 32767 -- WHY the output is clamped before the 16-bit"
                              " publish at 0x2A17C and the lag", "S")
    check(B0 * S_MAX < 2 ** 31 and abs(B1) * (S_MAX + bound["y"]) < 2 ** 31 and A2 * bound["y"] < 2 ** 31,
          f"every product is inside int32 at the linear worst case -- the TIGHTEST is b1*n <= {abs(B1) * (S_MAX + bound['y']) / 2 ** 31:.3f} * 2^31"
          f" (n = x - y, |n| <= {S_MAX + bound['y']:.0f}); b0*x {B0 * S_MAX / 2 ** 31:.3f}, a2*y {A2 * bound['y'] / 2 ** 31:.3f}", "S")

    # ---- the caves, emitted ----
    notch = notch_cave()
    tele = telemetry_rung()
    notch_bytes = b"".join(by for _, by, _, _ in notch)
    tele_bytes = b"".join(by for _, by, _, _ in tele)
    n_lo, n_hi = NOTCH, NOTCH + len(notch_bytes)
    t_lo, t_hi = TELE, TELE + len(tele_bytes)
    print(f"\n      NOTCH CAVE  0x{n_lo:05X}-0x{n_hi - 1:05X}  ({len(notch_bytes)} bytes, {len(notch)} instructions)")
    for a, by, mn, cm in notch:
        print(f"        0x{a:05X}  {by.hex():<12}  {mn:<24}  ; {cm}")
    print(f"\n      TELEMETRY   0x{t_lo:05X}-0x{t_hi - 1:05X}  ({len(tele_bytes)} bytes)")
    for a, by, mn, cm in tele:
        print(f"        0x{a:05X}  {by.hex():<12}  {mn:<24}  ; {cm}")

    # a scratch image with the caves + hooks applied, for the emulator (CRC not yet; not needed to execute)
    sim = bytearray(base)
    sim[HOOK:HOOK + 4] = jr(HOOK, NOTCH)
    sim[n_lo:n_hi] = notch_bytes
    sim[CAVE_JMP_LP:CAVE_JMP_LP + 4] = jr(CAVE_JMP_LP, TELE)
    sim[t_lo:t_hi] = tele_bytes

    simb = bytes(sim)          # ONE copy; the emulator reads it, never copies it

    def run_mirror(xs, st0=(0, 0, 0)):
        """The pure-Python integer mirror (fast).  Returns lists + the wrap monitor + the end state."""
        st = list(st0)
        wc = {"wraps": 0, "all": 0, "s1": 0, "s2": 0, "acc": 0, "b1n": 0}
        ys, yl, ns, fl = [], [], [], []
        for x in xs:
            yo, y, n, flag = notch_tick(x, st, wc)
            ys.append(yo)
            yl.append(y)
            ns.append(n)
            fl.append(flag)
        return ys, yl, ns, fl, wc, st

    def run_equiv(xs, st0=(0, 0, 0)):
        """The byte emulator executing the ACTUAL cave bytes, tick by tick against the mirror: r12,
        all four RAM cells, r7 == 507 and every live register asserted equal on EVERY tick."""
        st = list(st0)
        mem = {}
        set_state(mem, *st0)
        steps_max, n_ok = 0, 0
        for x in xs:
            yo, y, n, flag = notch_tick(x, st)
            r12, regs, mem, steps, e = emu_tick(simb, x, mem)
            steps_max = max(steps_max, steps)
            same = (r12 == yo and mem_state(mem) == (st[0], st[1], st[2], flag) and _s32(regs[R7]) == 507
                    and all(regs[r] == (0x51A7E000 + r * 0x01010101) & 0xFFFFFFFF for r in LIVE_ACROSS_HOOK))
            if not same:
                return n_ok, steps_max, (x, r12, yo, mem_state(mem), tuple(st), flag)
            n_ok += 1
        return n_ok, steps_max, None

    import random
    random.seed(289)
    rnd = [random.randint(-S_MAX, S_MAX) for _ in range(6000)]
    sq = [S_MAX if (i // 25) % 2 == 0 else -S_MAX for i in range(4000)]
    chirp = [int(round(S_MAX * math.sin(2 * math.pi * (1 + 119 * (i / 6000) / 2) * i / TICK_HZ))) for i in range(6000)]

    print(f"\n  [4a] BYTES == MIRROR: the emulator executes the real cave bytes against the integer mirror ({'FULL' if FULL else 'FAST'})")
    seqs = [("step +rail, decay, step -rail, random, small values", [S_MAX] * 60 + [0] * 60 + [-S_MAX] * 40 + rnd[:120]
             + [2, -3, 1, -1, 0, 16383, -16384, 7, -7] + sq[:60]),
            ("from a large state, zero input", [0] * 80)]
    st_big = ((int(0.14 * 2 ** 31), -int(0.14 * 2 ** 31), 16383),)
    for (nm_, xs_), st0_ in zip(seqs, ((0, 0, 0),) + st_big):
        n_ok, steps_max, why = run_equiv(xs_, st0_)
        check(why is None and n_ok == len(xs_), f"bytes == mirror on {n_ok}/{len(xs_)} ticks ({nm_}); max {steps_max} instructions/tick"
                                                 f"{'' if why is None else ' -- FIRST DIVERGENCE ' + str(why)}", "S")
    check(steps_max <= 60, f"the cave executes <= 60 instructions per tick ({steps_max})", "S")
    if FULL:
        for nm_, xs_ in (("random 6000", rnd), ("rail square 4000", sq), ("chirp 6000", chirp), ("DC 15360 x 2000", [S_MAX] * 2000),
                         ("DC -4097 x 2000", [-4097] * 2000)):
            n_ok, steps_max, why = run_equiv(xs_)
            check(why is None and n_ok == len(xs_), f"FULL: bytes == mirror on {n_ok}/{len(xs_)} ticks ({nm_})", "S")
        for key in ("s1", "s2", "acc"):
            xs_ = [S_MAX if hh[key][2999 - i] >= 0 else -S_MAX for i in range(3000)]
            n_ok, steps_max, why = run_equiv(xs_)
            check(why is None and n_ok == 3000, f"FULL: bytes == mirror on the l1 worst-case sequence for {key} (3000 ticks)", "S")
    print("      (everything below runs on the MIRROR, which [4a] has just shown to be what the bytes compute)")

    # (i) impulse: mirror == exact linear response, quantisation aside
    ys, yl, *_ = run_mirror([15360] + [0] * 3000)
    lin = [15360 * v for v in hh["y"][:3001]]
    err = max(abs(a - b) for a, b in zip(yl, lin))
    rms = (sum((a - b) ** 2 for a, b in zip(yl, lin)) / len(lin)) ** 0.5
    check(err < 8.0 and rms < 2.0, f"impulse 15360: mirror vs the linear response, max |err| = {err:.2f} counts,"
                                   f" rms {rms:.2f} (the shaped quantisation noise; 15360 -> 0.05 %)", "S")
    # (ii) DC: constant X -> time-average exactly X, |y - X| <= 1 (the error feedback at work)
    for X in (15360, -15360, 1, -1, 100, -4097, 12345):
        ys, yl, ns, fl, wc, st = run_mirror([X] * 4000)
        tail = yl[2000:]
        mean = sum(tail) / len(tail)
        check(max(abs(v - X) for v in tail) <= 1 and abs(mean - X) < 0.02 and max(abs(v - X) for v in ys[2000:]) <= 1,
              f"DC X={X}: steady |y-X| <= 1, mean {mean:.4f} (== X to 0.02)", "S")
    # CONTROL: WITHOUT the error feedback the same filter parks up to 64 counts low
    def plain_tdf2(X, n=4000):
        s1 = s2 = 0
        for _ in range(n):
            acc = B0 * X + s1
            y = acc >> QSH
            s1, s2 = B1 * (X - y) + s2, B0 * X - A2 * y
        return y
    dead = [X - plain_tdf2(X) for X in (15360, 1000, 100, 7)]
    check(max(dead) >= 30 and all(0 <= d <= 64 for d in dead),
          f"CONTROL: plain TDF-II (no error feedback) parks {dead} counts BELOW X for X = 15360/1000/100/7 (anywhere in the"
          " 0..64 deadband, where the dynamics happen to land) -- the error feedback is doing real work", "S")
    # (iii) zero input from arbitrary state decays to |y| <= 1
    for st0 in ((0.14 * 2 ** 31, -0.14 * 2 ** 31, 16383), (-300000000, 300000000, 1), (12345678, -87654321, 8191)):
        st0 = tuple(int(v) for v in st0)
        ys, yl, ns, fl, wc, st = run_mirror([0] * 3000, st0)
        check(max(abs(v) for v in yl[1500:]) <= 1 and wc["wraps"] == 0,
              f"zero input from state {tuple(hex(v) for v in st0)}: |y| <= 1 after 1.5 s, no wrap (max intermediate {wc['all'] / 2 ** 31:.3f} * 2^31)", "S")
    # (iv) step 0 -> +-15360: the clamp binds on the overshoot, states bounded
    ys, yl, ns, fl, wc, _ = run_mirror([15360] * 400)
    check(max(yl) > 15360 and max(ys) == 15360 and min(ys) > 10000 and wc["wraps"] == 0,
          f"step 0->15360: linear peak {max(yl)} (x{max(yl) / 15360:.3f}), delivered peak {max(ys)} (clamped), trough {min(ys)}", "S")
    ys, yl, ns, fl, wc, _ = run_mirror([-15360] * 400)
    check(min(yl) < -15360 and min(ys) == -15360 and wc["wraps"] == 0, f"step 0->-15360: linear trough {min(yl)}, delivered {min(ys)} (clamped)", "S")
    # (v) the l1 WORST-CASE sign sequences, one per state variable -- reach the bound, no wrap
    for key in ("s1", "s2", "acc"):
        N = 3000
        xs = [S_MAX if hh[key][N - 1 - i] >= 0 else -S_MAX for i in range(N)]
        ys, yl, ns, fl, wc, st = run_mirror(xs)
        slack = 0.002 * 2 ** 31   # the shaped quantisation noise, a few thousand counts x the coefficients
        check(wc["wraps"] == 0 and wc[key] <= bound[key] + E_MASK + slack and wc[key] > 0.9 * bound[key],
              f"l1 worst-case input for {key}: |{key}| reaches {wc[key] / 2 ** 31:.3f} * 2^31 (analytic bound {(bound[key] + E_MASK) / 2 ** 31:.3f});"
              f" largest intermediate of any kind {wc['all'] / 2 ** 31:.3f} * 2^31 (b1*n {wc['b1n'] / 2 ** 31:.3f}); no wrap", "S")
    # (vi) rail square wave at 20 Hz, chirp 1-120 Hz at full scale, random full-scale
    ys, yl, ns, fl, wc, _ = run_mirror(sq)
    rms_y = (sum(v * v for v in yl[1000:]) / 3000) ** 0.5
    check(wc["wraps"] == 0 and 0.38 < rms_y / S_MAX < 0.50,
          f"20 Hz rail square: no wrap; steady rms(y)/rms(x) = {rms_y / S_MAX:.3f} (the fundamental carries 8/pi^2 = 81 % of a square's"
          f" power -> residual rms 0.44 if it is removed); peak |y| {max(abs(v) for v in yl[1000:])} at the edges (harmonics pass);"
          f" duty(b7) = {sum(1 for v in fl[1000:] if v & BIT_CMP) / 3000:.2f}", "S")
    ys, yl, ns, fl, wc, _ = run_mirror(chirp)
    check(wc["wraps"] == 0, f"full-scale 1-120 Hz chirp: no wrap (max intermediate {wc['all'] / 2 ** 31:.3f} * 2^31)", "S")
    ys, yl, ns, fl, wc, _ = run_mirror(rnd)
    check(wc["wraps"] == 0, f"random full-scale input: no wrap (max intermediate {wc['all'] / 2 ** 31:.3f} * 2^31)", "S")
    # (vii) frequency response of the integer mirror by lock-in, vs the float coefficients
    def lockin(f, A):
        xs = [int(round(A * math.sin(2 * math.pi * f * i / TICK_HZ))) for i in range(3000)]
        ys, yl, *_ = run_mirror(xs)
        I = sum(yl[i] * math.sin(2 * math.pi * f * i / TICK_HZ) for i in range(2000, 3000))
        Q = sum(yl[i] * math.cos(2 * math.pi * f * i / TICK_HZ) for i in range(2000, 3000))
        Ix = sum(xs[i] * math.sin(2 * math.pi * f * i / TICK_HZ) for i in range(2000, 3000))
        Qx = sum(xs[i] * math.cos(2 * math.pi * f * i / TICK_HZ) for i in range(2000, 3000))
        return complex(I, Q) / complex(Ix, Qx)
    for f, A in ((20.036, 3000), (20.05, 15000), (17.0, 3000), (23.0, 3000), (7.3, 3000), (3.9, 3000), (13.5, 3000), (30.0, 3000)):
        got, want = lockin(f, A), H(f)
        check(abs(abs(got) - abs(want)) < 0.01, f"integer mirror: |H({f} Hz)| = {abs(got):.4f} (float {abs(want):.4f}), A = {A}", "S")
    # (viii) FLAG semantics on the emulated bytes vs the definition, incl. the boundary |n| == |y|
    ok = 0
    mem = {}
    set_state(mem, 0, 0, 0)
    nflag = 1500 if FULL else 300
    for x in rnd[:nflag] + [0, 1, -1, 2, -2]:
        r12, regs, mem, steps, e = emu_tick(simb, x, mem)
        s1, s2, ee, fg = mem_state(mem)
        ok += fg in (0, 0x20, 0x80, 0xA0)
    check(ok == nflag + 5, f"FLAG halfword only ever holds {{0, 0x20, 0x80, 0xA0}} over {nflag + 5} emulated ticks", "S")
    # boundary: n == y in magnitude -> bit 7 SET (>=), tested by direct construction
    mem = {}
    set_state(mem, 0, 0, 0)
    r12, regs, mem, *_ = emu_tick(simb, 2, mem)     # y = floor(2*16048/16384) = 1, n = 1 -> |n| >= |y| and n >= 0
    check(mem_state(mem)[3] == BIT_CMP and r12 == 1, "boundary |n| == |y| (x = 2 from rest: y = 1, n = 1) -> bit 7 SET, bit 5 clear", "S")
    mem = {}
    set_state(mem, 0, 0, 0)
    r12, regs, mem, *_ = emu_tick(simb, -3, mem)    # y = floor(-3*16048/16384) = -3 (floor), n = 0
    check(mem_state(mem)[3] == 0 and r12 == -3, "x = -3 from rest: y = -3 (floor), n = 0 -> both bits clear", "S")
    # (ix) the 100 Hz tail on the emulator: byte 4 gets exactly bits 5/7 from FLAG, stock bits untouched
    for flag, b4 in ((0xA0, 0b00000111), (0x20, 0b11111111), (0x80, 0), (0, 0xFF), (0xFF, 0x07)):
        e = V850Emu(simb, {})
        e.r[GP], e.r[LP] = GP_BASE, 0x55C12
        e.r[R6], e.r[R7] = 0xDEAD0006, 0xDEAD0007
        for i in range(2):
            e.mem[GP_BASE + FLAG_DISP + i] = (flag >> (8 * i)) & 0xFF
        e.mem[GP_BASE + BUF_BYTE4_DISP] = b4
        e.run(CAVE_JMP_LP, 0x55C12)
        got = e.mem[GP_BASE + BUF_BYTE4_DISP]
        want = (b4 & TAIL_MASK) | (flag & OUR_BITS)
        check(got == want and _s32(e.r[R6]) == _s32(GP_BASE + BUF_BASE_DISP),
              f"tail: FLAG 0x{flag:02X}, byte4 0x{b4:02X} -> 0x{got:02X} (bits 0-2,3,4,6 preserved, 5/7 from FLAG & 0xA0); r6 = buffer base", "S")
    # (x) the INIT switch: BOTH variants assembled; the prologue variant executed on a scratch image
    plain = notch_cave(init=False)
    withp = notch_cave(init=True)
    plain_b = b"".join(by for _, by, _, _ in plain)
    withp_b = b"".join(by for _, by, _, _ in withp)
    PRO_LEN = 26
    check(len(withp_b) == len(plain_b) + PRO_LEN and withp_b[PRO_LEN:-4] == plain_b[:-4]
          and decode_one(withp_b + b"\0" * 8, len(withp_b) - 4)[1].startswith("jr")
          and jr(NOTCH + len(withp_b) - 4, HOOK_RET) == withp_b[-4:],
          f"INIT variant = {PRO_LEN}-byte prologue + the shipped cave byte-for-byte (only the return jr displacement differs);"
          f" {len(withp_b)} vs {len(plain_b)} B; this build EMITS the {'INIT' if INIT_ON_SENTINEL else 'plain'} variant", "S")
    pro_txt = [t for _, _, t in decode_range(withp_b + b"\0" * 8, 0, PRO_LEN)]
    check(pro_txt[0].startswith("ld.w -0x6cf8, gp, r6") and pro_txt[1] == "mov 0x7fffffff, r9" and pro_txt[2] == "cmp r9, r6"
          and pro_txt[3].startswith("bne") and int(pro_txt[3].split()[1], 16) == PRO_LEN
          and pro_txt[4:] == ["st.w r0, -0x6c44, gp", "st.w r0, -0x6c40, gp", "st.w r0, -0x6c3c, gp"],
          f"prologue decodes (independent decoder) as ld.w marker / mov sentinel / cmp / bne +{PRO_LEN} / three st.w r0: {pro_txt}", "S")
    # behavioural: assemble the INIT variant on a scratch image and run the real bytes
    sim2 = bytearray(base)
    sim2[HOOK:HOOK + 4] = jr(HOOK, NOTCH)
    sim2[NOTCH:NOTCH + len(withp_b)] = withp_b
    sim2b = bytes(sim2)

    def init_tick(marker, x, st0):
        mem = {}
        set_state(mem, *st0)
        for i in range(4):
            mem[GP_BASE + EINIT_CELL_DISP + i] = ((marker & 0xFFFFFFFF) >> (8 * i)) & 0xFF
        r12, regs, mem, steps, e = emu_tick(sim2b, x, mem)
        live_ok = all(regs[r] == (0x51A7E000 + r * 0x01010101) & 0xFFFFFFFF for r in LIVE_ACROSS_HOOK) and _s32(regs[R7]) == 507
        return r12, mem_state(mem), steps, live_ok

    seed = (123456, -654321, 777)
    for marker in (0, 1234, -82176, 0x7FFFFFFE, 0x70000000, -1):
        st_m = list(seed)
        yo, y, n, flag = notch_tick(500, st_m)
        r12, ms, steps, live_ok = init_tick(marker, 500, seed)
        check(r12 == yo and ms == (st_m[0], st_m[1], st_m[2], flag) and live_ok,
              f"INIT variant, marker 0x{marker & 0xFFFFFFFF:08X}: NOT a sentinel -> state kept, output {r12} == mirror {yo}, live regs + r7 intact", "S")
    st_z = [0, 0, 0]
    yo, y, n, flag = notch_tick(500, st_z)
    r12, ms, steps, live_ok = init_tick(EINIT_SENTINEL, 500, seed)
    check(r12 == yo and ms == (st_z[0], st_z[1], st_z[2], flag) and live_ok and steps <= 60,
          f"INIT variant, marker 0x7FFFFFFF: state ZEROED first -> output {r12} == mirror-from-zero {yo}, RAM == mirror-from-zero, live regs + r7 intact,"
          f" {steps} instructions", "S")
    check(not INIT_ON_SENTINEL or os.environ.get("ACCORD_V289_INIT") == "1",
          f"INIT_ON_SENTINEL = {INIT_ON_SENTINEL} (shipped build: FALSE -- the hook is on every route; nothing to re-init)", "V")

    print("\n  [4c] MIRROR-vs-LAYOUT DRIFT GUARD")
    import inspect
    import re
    src = inspect.getsource(notch_tick)
    ann = sorted({int(m, 16) for line in src.split("\n") if "#" in line
                  for m in re.findall(r"0x[0-9A-Fa-f]{5}", line.split("#", 1)[1])} & set(range(FREE_LO, FREE_HI)))
    emitted = {a: mn for a, _, mn, _ in plain}       # the mirror annotates the SHIPPED (no-prologue) layout
    check(ann and all(a in emitted for a in ann), f"every address the mirror annotates ({[hex(a) for a in ann]}) is a real instruction of the shipped layout", "S")
    want_mn = {"andi", "mul", "add", "sar", "sub"}
    check(all(emitted[a].split()[0] in want_mn for a in ann), "and each annotated address carries the mnemonic the mirror line describes", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [4d] DOCSTRING-vs-BUILD GUARD -- the text must describe the SHIPPED revision's bytes")
    _doc = __doc__ or ""
    _pl_hi, _pl_n = NOTCH + len(plain_b), len(plain)
    for required, why in ((f"0xC4C00-0x{_pl_hi - 1:05X}", "the shipped notch-cave extent"),
                          (f"{len(plain_b)} bytes, {_pl_n} instructions", "the shipped cave size"),
                          (f"0xC4BDC-0x{t_hi - 1:05X}", "the live tail extent"), (f"{len(tele_bytes)}-byte tail", "the tail size"),
                          ("gp-0x6c3a", "the FLAG cell"), ("INIT_ON_SENTINEL", "the switch"), ("andi 0x5F", "the tail mask"),
                          ("875 / 2301", "the cal values"), ("0xC4FFC, 0xC6FFC", "both CRC trailers"),
                          ("30.8859", "the realised fb DC"), ("20.036 Hz", "the realised notch centre")):
        check(required in _doc, f"the docstring names {required!r} -- {why}", "S")
    for banned, why in (("gp-0x6ab0 (0xFEDF1550)  y", "the two-word handoff this build does NOT use"),
                        ("0xC4C00-0xC4C2F", "V288's cave extent")):
        check(banned not in _doc, f"the docstring does NOT carry {banned!r} -- {why}", "S")

    print("\n  [5] FREE FLASH, LAYOUT, and the three `jr` displacements decoded BOTH ways")
    ff_end = FREE_LO
    while base[ff_end] == 0xFF:
        ff_end += 1
    check(ff_end == FREE_HI, f"0xFF run 0x{FREE_LO:05X}-0x{ff_end - 1:05X} in V282 ({ff_end - FREE_LO} B) -- V288's cave is NOT here", "V")
    check(bytes(base[STRUCT_LO:STRUCT_HI]).hex() == "010101010000c6001300b200", f"the 12 non-FF bytes at 0x{STRUCT_LO:05X} are the known structure", "V")
    for lo, hi, nm in ((n_lo, n_hi, "notch cave"), (t_lo, t_hi, "telemetry tail")):
        check(FREE_LO <= lo and hi <= FREE_HI and all(x == 0xFF for x in base[lo:hi]), f"{nm} [0x{lo:05X},0x{hi:05X}) is inside the free run and all-0xFF in V282", "S")
    check(t_hi <= n_lo and CAVE_JMP_LP + 4 <= t_lo, "tail, notch cave and the 0xC4BD6 jr do not overlap", "S")
    check(STRUCT_LO - n_hi >= 0, f"{STRUCT_LO - n_hi} bytes still free after the notch cave", "S")
    hook_jr, tele_jr, ret_jr = jr(HOOK, NOTCH), jr(CAVE_JMP_LP, TELE), notch[-1][1]
    for at, blob, want in ((HOOK, hook_jr, NOTCH), (CAVE_JMP_LP, tele_jr, TELE), (notch[-1][0], ret_jr, HOOK_RET)):
        n_, txt = decode_one(bytes(sim), at)                 # decoded IN PLACE, so the target is absolute
        tgt = int(txt.split()[1], 16)
        check(n_ == 4 and txt.startswith("jr ") and tgt == want and bytes(sim[at:at + 4]) == blob,
              f"jr @0x{at:05X}: {blob.hex()} -> independent decoder `{txt}` == 0x{want:05X}; hw2 bit0 = {blob[2] & 1} (0 = jr, not ld.bu)", "S")

    print("\n  [6] APPLY")
    code = bytearray(base)
    attributed = set()
    for at, blob, nm in ((HOOK, hook_jr, "hook -> jr notch cave"), (n_lo, notch_bytes, "notch cave"),
                         (CAVE_JMP_LP, tele_jr, "0x14A cave exit -> jr tail"), (t_lo, tele_bytes, "telemetry tail")):
        code[at:at + len(blob)] = blob
        attributed |= set(range(at, at + len(blob)))
        check(bytes(code[at:at + len(blob)]) == blob, f"0x{at:05X}: {len(blob)} bytes written ({nm})", "T")
    for cell, (old, new) in MOVED.items():
        check(u16(code, cell) == old, f"0x{cell:05X} pre-write == {old}", "T")
        struct.pack_into("<H", code, cell, new)
        attributed |= {cell, cell + 1}
        check(u16(code, cell) == new, f"0x{cell:05X} := {new}", "T")
    check(len(hook_jr) == len(HOOK_OLD) == 4, "same-length hook swap: 0x2A178 onward does not move", "S")
    check(bytes(code[CAVE_START:CAVE_JMP_LP]) == bytes(base[CAVE_START:CAVE_JMP_LP]), "every existing 0x14A rung byte-identical; only the 2-byte jmp[lp] exit moved", "S")
    check(bytes(code[t_hi - 6:t_hi]) == bytes(base[CAVE_EPILOGUE:CAVE_EPILOGUE + 4]) + CAVE_JMP_LP_OLD, "the relocated epilogue is byte-identical to `movea -0x1518,gp,r6 ; jmp [lp]`", "S")
    check(bytes(code[n_hi - 8:n_hi - 4]) == HOOK_OLD, "the cave's penultimate instruction IS the displaced `ld.hu 0x73ee,tp,r7`, byte-identical", "S")

    print("\n  [7] EVERYTHING ELSE BYTE-IDENTICAL TO V282")
    stray = [x for x in range(START, END) if code[x] != base[x] and x not in attributed]
    check(stray == [], f"no byte outside the written regions changed ({len(stray)} stray)", "S")
    check(bytes(code[CAVE_HOOK:CAVE_HOOK + 4]) == CAVE_HOOK4, "0x55C0E jarl untouched", "E")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), "427 tap window byte-identical", "E")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == u16(base, a_) == v, f"0x{a_:05X} == base == {v}", "E")
    for p in sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)}):
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]), f"map 0x{p:05X} byte-identical", "E")
    for arr, nm in ((KP_PTR, "Kp"), (KD_PTR, "Kd")):
        for s in range(N_SLOTS):
            p = u32(base, arr + 4 * s)
            n = u16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"{nm} slot {s} @0x{p:05X} byte-identical", "E")
    for p in sorted({u32(base, arr + 4 * s) for arr in TAPER_PTRS for s in range(N_SLOTS)}):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "E")

    print("\n  [8] CRC -- owning blocks located GENERICALLY via V53.owning_block; zlib.crc32 recomputed per block")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    check(blocks == [(START, 0xC4FFC), (0xC6000, 0xC6FFC)],
          f"exactly TWO CRC blocks own the edited bytes: [0x13000,0xC4FFC) (hook + both caves) and [0xC6000,0xC6FFC) (the two fb-pole"
          f" cal cells) -- {[(hex(a_), hex(b_)) for a_, b_ in blocks]}", "S")
    trailers = []
    for b0_, b1_ in blocks:
        check(not any(b1_ <= x < b1_ + 4 for x in attributed), f"no edit lands ON the trailer 0x{b1_:06X}", "S")
        oldc, newc = u32(code, b1_), zlib.crc32(bytes(code[b0_:b1_])) & 0xFFFFFFFF
        check(newc != oldc, f"block [0x{b0_:06X},0x{b1_:06X}) CRC moved 0x{oldc:08X} -> 0x{newc:08X}", "S")
        struct.pack_into("<I", code, b1_, newc)
        attributed |= set(range(b1_, b1_ + 4))
        trailers.append(b1_)
    check(zlib.crc32(bytes(code[0x13000:0xC4FFC])) & 0xFFFFFFFF == u32(code, 0xC4FFC)
          and zlib.crc32(bytes(code[0xC6000:0xC6FFC])) & 0xFFFFFFFF == u32(code, 0xC6FFC),
          "zlib.crc32([0x13000,0xC4FFC)) == cell 0xC4FFC and zlib.crc32([0xC6000,0xC6FFC)) == cell 0xC6FFC", "T")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    print("\n  [9] FULL BYTE DIFF vs V282 -- every changed run")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    regions = ((HOOK, HOOK + 4, "hook 0x2A174 (ld.hu -> jr)"), (CAVE_JMP_LP, CAVE_JMP_LP + 4, "0x14A cave exit (jmp[lp] -> jr)"),
               (t_lo, t_hi, "telemetry tail (NEW)"), (n_lo, n_hi, "notch cave (NEW)"),
               (FB_A_CELL, FB_A_CELL + 2, "fb pole a 923 -> 875"), (FB_B_CELL, FB_B_CELL + 2, "fb pole b 1560 -> 2301"),
               (trailers[0], trailers[0] + 4, "CRC trailer (code block)"), (trailers[1], trailers[1] + 4, "CRC trailer (cal block)"))
    allowed = set()
    for lo, hi, _ in regions:
        allowed |= set(range(lo, hi))
    check(set(diff) <= allowed, f"every one of the {len(diff)} differing bytes lies in the eight expected regions", "S")

    def _region(s_, e_):
        for lo_, hi_, nm_ in regions:
            if lo_ <= s_ and e_ <= hi_:
                return nm_
        return f"?? UNATTRIBUTED 0x{s_:06X}-0x{e_ - 1:06X}"
    for s, e in runs(diff):
        kind = _region(s, e)
        check(not kind.startswith("??"), f"diff run 0x{s:06X}-0x{e - 1:06X} attributable", "S")
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {kind:<34}  {bytes(base[s:e]).hex() if e - s <= 16 else '...'}"
              f" -> {bytes(code[s:e]).hex() if e - s <= 16 else '...'}")
    print(f"      {len(diff)} bytes differ in {len(runs(diff))} runs: 4 hook + {len(notch_bytes)} notch + 4 exit + {len(tele_bytes)} tail"
          f" + 2+2 cal + 4+4 CRC = {4 + len(notch_bytes) + 4 + len(tele_bytes) + 4 + 8} touched (runs split where a written byte equals the 0xFF it replaced)")

    print("\n  [9b] CROSS-IMAGE vs V281 rev 3")
    parent = Path(plain_image_path(PARENT_NAME)).read_bytes()
    check(hashlib.sha256(parent).hexdigest() == PARENT_SHA, "V281 rev 3 image sha256 matches", "S")
    d_v282 = {x for x in range(START, END) if base[x] != parent[x]}
    d_v289 = {x for x in range(START, END) if code[x] != parent[x]}
    check(d_v289 == (d_v282 | set(diff)) - {x for x in d_v282 & set(diff) if code[x] == parent[x]},
          f"V289 vs V281 rev 3 ({len(d_v289)} B) == V282's own diff ({len(d_v282)}) UNION this build's ({len(diff)}), modulo the shared CRC cell", "S")

    print("\n  [10] .rwd ENCODE + READBACK")
    src_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src_rwd, "V38 source")
    info = parse_x31(src_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V289 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0 and walk(bytes(dec)) == 0, "readback CRC 50/50 and bootloader replay 49/49", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src_rwd)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    print("\n  [11] END STATE -- the BUILT image decoded by the independent decoder; pins to bytes on the flown image")
    for nm, im in (("code", code), ("dec ", dec)):
        kd = "T" if nm == "code" else "E"
        listing = decode_range(bytes(im), n_lo, n_hi)
        want = [(a, _norm(mn.replace("[gp]", ", gp").replace("[tp]", ", tp"))) for a, _, mn, _ in notch]
        got = [(a, _norm(t)) for a, _, t in listing]

        def _same(w, g, a):
            # the builder's mnemonic text is shorthand; compare mnemonic + register/immediate tokens.
            # Bcond: the builder writes a relative "+4", the decoder an absolute target -> resolve and compare.
            wt, gt = w.split(), g.split()
            if wt[0] != gt[0]:
                return False
            if wt[0] == "jr":
                return int(gt[1], 16) == HOOK_RET
            if wt[0] in COND and wt[1].startswith(("+", "-")):
                return int(gt[1], 16) == a + int(wt[1])
            wt2 = [t.replace("[gp]", "").replace("[tp]", "") for t in wt[1:]]
            return all(any(tok == x or tok.lstrip("-").lstrip("0x").lstrip("0") == x.lstrip("-").lstrip("0x").lstrip("0")
                           for x in gt[1:]) for tok in wt2 if tok not in ("gp", "tp", "r0", ""))
        mism = [(hex(a), w, g) for (a, w), (a2, g) in zip(want, got) if a != a2 or not _same(w, g, a)]
        check(len(listing) == len(notch) and not mism,
              f"{nm}: the {len(listing)} instructions decoded from the built cave match the intended listing, address by address ({mism[:2]})", "S")
        tl = decode_range(bytes(im), t_lo, t_hi)
        check(len(tl) == len(tele) and tl[-1][2] == "jmp [lp]" and tl[-2][2].startswith("movea") and "-0x1518" in tl[-2][2],
              f"{nm}: tail decodes to {len(tl)} instructions ending `movea -0x1518, gp, r6 ; jmp [lp]`", "S")
        check(decode_one(bytes(im), HOOK)[1] == f"jr {NOTCH:#010x}" and decode_one(bytes(im), CAVE_JMP_LP)[1] == f"jr {TELE:#010x}"
              and decode_one(bytes(im), notch[-1][0])[1] == f"jr {HOOK_RET:#010x}",
              f"{nm}: decoder resolves hook -> 0x{NOTCH:05X}, exit -> 0x{TELE:05X}, return -> 0x{HOOK_RET:05X}", "S")
        # register discipline read from the decoded text, not from the tables
        writes = set()
        for a, n_, t in listing:
            toks = t.replace(",", " ").split()
            mn = toks[0]
            if mn in ("st.w", "st.h", "st.b", "cmp", "jr") or mn.startswith("b"):
                continue
            if mn == "mul":
                writes |= {toks[2], toks[3]}          # reg2 = low word, reg3 = high word (r0 = discarded)
            else:
                writes.add(toks[-1])
        writes.discard("r0")                          # writes to r0 are architecturally ignored
        check(writes <= {"r6", "r7", "r9", "r12", "r13"} and not writes & {f"r{r}" for r in LIVE_ACROSS_HOOK} | {"lp"} & writes,
              f"{nm}: the cave writes only {sorted(writes)} -- never r14/r16/r22/r24/r27/r29/lp", "S")
        check(not any(t.startswith("jarl") for _, _, t in listing + tl), f"{nm}: no jarl anywhere in the new code (lp is live)", "S")
        # cell pins
        gp_cells = sorted({int(t.split()[1].rstrip(","), 16) if t.split()[1].startswith("0x") else -int(t.split()[1].rstrip(",").lstrip("-"), 16)
                           for _, _, t in listing if ", gp" in t and t.split()[0].startswith("ld")}
                          | {-int(t.split()[2].rstrip(",").lstrip("-"), 16) for _, _, t in listing if ", gp" in t and t.split()[0].startswith("st")})
        _want_cells = {S1_DISP, S2_DISP, E_DISP, FLAG_DISP} | ({EINIT_CELL_DISP} if INIT_ON_SENTINEL else set())
        check(gp_cells == sorted(_want_cells), f"{nm}: the cave's gp cells are EXACTLY {[hex(c) for c in gp_cells]}", "S")
        tp_cells = sorted({int(t.split()[1].rstrip(","), 16) for _, _, t in listing if ", tp" in t})
        check(tp_cells == [SUM_CLAMP_TP, LAG_B_TP], f"{nm}: the cave's tp cells are exactly 0x71be (sum clamp) and 0x73ee (lag b) -- both read-only", "S")
        check(u16(im, FB_A_CELL) == FB_A_NEW and u16(im, FB_B_CELL) == FB_B_NEW, f"{nm}: 0xC63E8 = {FB_A_NEW}, 0xC63EA = {FB_B_NEW}", kd)
        check(bytes(im[FB_A_LOAD:FB_A_LOAD + 4]) == FB_A_LOAD_BYTES and bytes(im[FB_B_LOAD:FB_B_LOAD + 4]) == FB_B_LOAD_BYTES,
              f"{nm}: the two loads at 0x28F86/0x28F8A are untouched (ld.hu / ld.h)", "S")
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}", kd)
        n_, X_, Y_ = rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(X_) == LIVE_KP_X and tuple(Y_) == LIVE_KP_Y, f"{nm}: live Kp record == flat-248", kd)
        # the tail's andi masks
        tmasks = [int(t.split()[1].rstrip(","), 16) for _, _, t in tl if t.startswith("andi")]
        check(tmasks == [OUR_BITS, TAIL_MASK] and all(m & STOCK_B4_BITS == STOCK_B4_BITS for m in tmasks[1:]),
              f"{nm}: tail masks {[hex(m) for m in tmasks]}: FLAG & 0xA0, byte4 & 0x5F -- stock bits 2-0 cannot be cleared", "S")
        # re-run the emulator on the FINAL image (post-CRC) for a short sequence
        mem = {}
        set_state(mem, 0, 0, 0)
        st = [0, 0, 0]
        okk = 0
        imb = bytes(im)
        for x in (15360, 0, -7000, 123, -15360, 0, 0):
            yo, y, n, flag = notch_tick(x, st)
            r12, regs, mem, *_ = emu_tick(imb, x, mem)
            okk += (r12 == yo and mem_state(mem) == (st[0], st[1], st[2], flag))
        check(okk == 7, f"{nm}: the FINAL image's bytes execute identically to the mirror (7/7 ticks)", "S")

    print("\n  [12] INDEPENDENT REBUILD reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha, "independent rebuild (literal opcode arithmetic, generic re-CRC) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n  [13] 0x14A BYTE-4 BIT MAP")
    print("      bit  owner   V282                                  V289 rev 1")
    print("       7   cave    sign(gp-0x6b4c)                       |n| >= |y|   n = S - y (notch removed component)")
    print("       6   cave    |r24| >= |T (gp-0x6b38)|              unchanged (positive control)")
    print("       5   cave    |r24| >= |aggregator (gp-0x6b94)|     sign(n): 1 when S - y < 0")
    print("       4   cave    sign(r24)                             unchanged (positive control)")
    print("       3   cave    sign(gp-0x3680)                       unchanged")
    print("       2-0 STOCK   frame builder                         unchanged -- NOT OURS")
    print("      FLAG halfword gp-0x6c3a = {0,0x20,0x80,0xA0}, written at 1 kHz; the tail ORs FLAG & 0xA0 into byte 4 after andi 0x5F.")

    _scr = os.environ.get("ACCORD_V289_SCRATCH", "").strip()
    if _scr:
        Path(_scr, RWD_NAME).write_bytes(rwd)
        Path(_scr, IMG_NAME).write_bytes(bytes(code))
        print(f"      scratch copy written to {_scr}")
    if not INIT_ON_SENTINEL:
        check(img_sha == EXPECTED_IMG_SHA and rwd_sha == EXPECTED_RWD_SHA,
              f"image {img_sha[:8]}... and rwd {rwd_sha[:8]}... == the hashes of the shipped 2026-09-08 build (text-only edits leave them unchanged)", "S")
    if WRITE_MODE == "rwd":
        check(not INIT_ON_SENTINEL, "the write path refuses the INIT scratch variant", "S")
        out_img = Path(plain_image_path(IMG_NAME))
        out_rwd = Path(RWD_DIR, RWD_NAME)
        check(max(len(str(out_img)), len(str(out_rwd))) < 255, "output paths fit the 255-char limit", "S")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        others = [f.name for f in Path(RWD_DIR).glob("*V289*.rwd") if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"exactly ONE flashable V289 rwd on disk (others: {others})", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V289_WRITE=rwd to emit the files")

    print("\n" + "=" * 112)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    _bk = _census["E"] + _census["V"] + _census["T"]
    print(f"  {_checks[1]}/{_checks[0]} assertions passed.  READ THE BUCKETS:")
    print(f"    {_census['S']:4d}  SUBSTANTIVE   -- can falsify something about this build")
    print(f"    {_census['E']:4d}  ENTAILED      -- follows from a sibling assertion in this run")
    print(f"    {_census['V']:4d}  VACUOUS       -- entailed by the base sha256")
    print(f"    {_census['T']:4d}  TAUTOLOGICAL  -- readback of a write this script just made")
    print(f"  Only the {_census['S']} substantive checks are evidence; the other {_bk} are bookkeeping.")
    print("=" * 112)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
