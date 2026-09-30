# -*- coding: utf-8 -*-
r"""V295 -- THE V294 ACCELERATION TRIM x1.852.  ONE calibration cell, 0xC63EA (fb-lag input gain b): 567 -> 1050.

BASE            V294  (_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0
                       -R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin, sha256 3143616d...dbdd85) -- FLOWN on r71b
EDIT
  CAL (one u16, two data bytes, plus the four-byte CRC trailer of the block that holds it):
    0xC63EA  fb-lag input gain b   567 -> 1050   (LE 37 02 -> 1a 04)   tp+0x73EA, SOLE reader `ld.hu 0x73ea,tp,r16`
                                                                       @0x28F86 (Ghidra = raw LE scan, positive-controlled)
    trailer  0xC6FFC  crc32 of block [0xC6000, 0xC6FFC)  (the SAME block V294 already re-CRC'd and flew)
  NOTHING ELSE.  No code byte, no opcode, no second cal cell.  Every other byte of [0x13000, 0x100000) == V294.

=== 0. WHAT THE CELL IS ==================================================================================
b is the INPUT GAIN of the LKAS PID's feedback-lag filter, the one-pole low-pass on the 1 kHz wheel rate x
(gp-0x6a56, 8.00 counts per deg/s -- the 0x14A field is -x>>3 @0x55B48).  Since V294 flipped the `add` at 0x28FA4
to `subr`, the filter's OUTPUT operand is no longer the lagged rate but its per-tick CHANGE:

    s_new = (a*s >> 10) + (b*x >> 10)            0x28F86 ld.hu b ; 0x28F8A ld.h a ; 0x28F8E/92 mul ; 0x28F9A/A0 sar 0xa
    r26   = clamp(s_new - s_old, +-C)            0x28FA4 subr r9,r26 (V294) ; 0x28FA6..0x28FBE, C = 1024
    E     = (sp << 2) - r26                      0x29D76 shl 0x2,r16 (V294) ; 0x29D78 sub r26,r16
    P     = clamp((E*960) >> 8, +-15360)         0x29E36 mul ; 0x29E3E sar 0x8      = 15*sp - 3.75*r26

At the 2.03 Hz pole (a = 1011) r26 = (b/1024)*(x - lag(x)) is a WASHOUT of the wheel rate -- the wheel's ACCELERATION
seen through a first-order low-pass.  b is the ONLY gain on that operand that is not shared with the feedforward:
Kp scales 15*sp too, the pole moves the bandwidth, C only bounds it.  So b alone is THE TRIM GAIN.  It is read at
exactly one site and written at none (census [3]; V289 and V291/V292 moved it on the SUM operand, only V294's 567
has flown on the DIFF operand).

=== 0b. THE PHYSICS (one paragraph) ======================================================================
The trim is T_trim = -3.75*r26 P-counts, x(254/256 taper)(0.990 output lag)(5346/32768 forward gain) = 0.16029 T
per P-count.  Below the pole r26 = b/(1024-a) * dx per tick, so the torque per wheel ACCELERATION is
K_alpha = 3.75 * b/13 * 1e-3 * 8 * 0.16029 T counts per deg/s^2: 0.210 at b 567 (V294), 0.388 at 1050 -- an added
INERTIA below 2 Hz.  Above the pole |r26/x| saturates at ~b/1024 with phase leading toward 0 deg, so at the 2-3 Hz
wheel mode the trim is ~97 % in phase with RATE: a DAMPER, ~1.85 -> ~3.4 T counts opposing each deg/s of rate.
🛑 UNITS (adversary B, 2026-09-30): every per-deg/s and per-deg/s^2 number here is per unit of the EPS's OWN rate
x/8, which is rack-side; the steering WHEEL moves kappa = 1.16x more on centre (0.965x beyond 80 deg), so per
steering-wheel deg/s^2 K_alpha is 0.336 on centre and the damping ~2.9 T per steering-wheel deg/s.  The x1.852
ratios are unit-free.  At 20 Hz the controller gain |P/x| goes 2.079 -> 3.850 (V282, which ground at 20 Hz, was
44.90; V292, a revert, 31.4).  Everything that does not multiply r26 is untouched: the feedforward 15*sp is
bit-identical, so the static surface, the rail +2461/-2463, the sub-rail slope 0.64100 T per wire count and the
616 T trim cap (C and Kp unchanged) are V294's to the count -- asserted from the built image at [8]/[9].  The trim
reaches C (r26 = +-1024) at 1585 deg/s^2 below the pole, or 177 deg/s of 2 Hz rate / 161 at 2.5 Hz / 125 at the HF
limit (V294: 2935 deg/s^2, 231 deg/s); on r71b's recorded motion V295 would have hit C on 66-69 ticks (0.007 %).

=== 1. CUMULATIVE NON-STOCK DELTA ON V295 (stock -> V295, read from the BUILT image at [15]) ================
  V282's 28 rows, unchanged by V293/V294/V295 except where listed below
  (docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md: version marker, forward-gain repoint 0x2A1F0,
   biquad arm 0x35A08.., rate-lane gate 0x3AA96, 0x454FE, 0x14A cave + hook 0x55C0E, the CAN-427 tap
   0x55DF2..0x55E11, forward gain 0xC6CD0 5346, clamps 0xC61B2/B4 3072, the EME quad/ramp/floats, the lockout
   0xC62EA 0, the Coulomb relay, STEER_STATUS debounce, DTC-0x49 gate, the square-wave hold, the damper bank
   flatten, the x6 map, Kp FLAT, the setpoint ceiling 16384, page CRCs)
  + V293's five:  fb clamp 0xC62E6 46080 -> 0 | Kd bank 0xCB7D4 all 28 records -> 0 | D clamp 0xC61B6 10240 -> 0 |
                  Kp bank 0xCB994 all 28 records -> 120 flat | r24 engaged arm 0xC6446 5244 -> 2048
  + V294's six:   0x28FA4 `add r9,r26` -> `subr r9,r26` | 0x29D76 `shl 0x5,r16` -> `shl 0x2,r16` |
                  fb clamp 0xC62E6 0 -> 1024 | pole a 0xC63E8 923 -> 1011 | gain b 0xC63EA 1560 -> 567 |
                  Kp bank 120 -> 960 flat on all 28 records
  + V295's one:   gain b 0xC63EA 567 -> 1050
  On V295, vs STOCK: fb clamp 1024 (stock 7680) | Kp 960 flat (stock slot 7 248/512/645/696/696) | Kd 0 (stock 128) |
  D clamp 0 (stock 10240) | r24 arm 2048 (stock 512) | a 1011 (stock 923) | b 1050 (stock 1560) | `subr` (stock `add`)
  | `shl 0x2` (stock `shl 0x5`).  [15] reads every one of these from the stock dump AND the built image.

=== 2. THE PRE-REGISTERED WIRE READ -- written before the drive ==========================================
The instrument is the EXISTING CAN-427 delivered-torque tap (T = gp-0x6b38, `(sign<<9)|(|T|>>3)`), the 0x18F wheel
rate and the 0xE4 command.  No new instrument: the changed value is a gain on a quantity the tap already carries.
On every engaged window, OLS  T_tap = c0 + c1*FF_V294(cmd) + c2*TRIM_V294(cmd, x), where FF_V294 and TRIM_V294 are
V294's byte-exact null and live-minus-null marches on the drive's OWN recorded 0xE4 and 0x18F.  c1 reads the
feedforward gain, c2 reads Kp*b/(960*567).  PREDICTED: c1 ~0.99 (V294's own), c2 ~1.83-1.85 (= 1050/567 x V294's
0.986).  On r71b V294 reads c2 0.99 [0.93, 1.04] (30 s hands-off windows).
  PROTOCOL (adversary B's corrections, 2026-09-30 -- binding on the flight read):
  * BOTH regressors are V294's cells (b 567), never V295's own trim (that would need a 0.78 threshold).
  * CALIBRATE FIRST: the analyst's code must reproduce r71b (V294) before it reads the V295 route -- pooled
    c2 0.96-1.02, c1 0.97-1.01, rms(tap - quant(V294 march)) <= 3.0 counts.  A negated x (the bytes say x = -raw
    0x18F) flips c2's sign and would fire the REVERT rule on a correct image.
  * EXCITATION GATE: score a window only if rms(TRIM_V294) >= 4 counts (half a tap LSB); straight-driving windows
    below it are NO-CALL (ungated, a live V295 reads 1.450 in one straight 15 s window on r71b).
  * PRIMARY READ: pooled hands-off c2 with a 10 s block-bootstrap CI.  Predicted V295 1.837 [1.829, 1.844]
    (positive control through r71b's real tap residual); V294 reads 0.989 [0.977, 0.999]; inverted -1.85.
  * c2 > 1.45 (pooled, or on any gated window >= 15 s; hard-turn +-10 s windows read 1.81-1.87)  ->  b 1050 LIVE.
  * c1 inside V294's own r71b spread (0.94-1.00 at 15 s; pooled 0.99)                          ->  the FF did not move.
  * c2 < 1.45 on the gated read                                                                ->  NOT V295; STOP.
    Nothing else from that drive is licensed about V295.
  * c2 < 0 after the calibration step passed                                                   ->  SIGN INVERTED; REVERT.
    (Structurally impossible for a b-only edit; it is the positive check.)
  * FF identity (the V294 attribution's identity_block, V293 cells): expected ~0.965 on a correct V295 (V294 0.987);
    keep the 0.90 line -- 0.98 would misfire on the correct image; the identity is BLIND to an inverted operand
    (0.974), so the sign is c2's job alone.
  * The V294 E3 estimator would read ~0.39 on V295 (0.21 on V294); its > 0.10 LIVE line does not separate them.
  NULL SENTENCES, given b live:
  * An unchanged 1.6-3 Hz hard-turn wheel-rate band licenses NOTHING: the predicted change (x0.68-0.93 over the
    design family) sits inside that band's one-drive scatter (x0.78-1.26 at 15 s).
  * An unchanged "jerky on hard turns" cannot distinguish "EPS damping at 1-5 Hz does not limit that symptom" from
    "this dose is below what he can feel".  A reported IMPROVEMENT is attributable to b if the fork config did not
    change in the same drive.
  * "Loose on straights / at low speed" and "loose/understeer at highway turns" are NOT TESTED: c1 = 1 is the proof
    the static gain did not move.  The operator scores the symptoms, not this sentence.
  * NO SECONDARY OUTCOME IS DECIDABLE FROM ONE DRIVE (r71b block bootstraps, adversary B): the 0.5-1 Hz low-speed
    lat-accel error's no-change scatter is x0.70-1.48 even at 300 s (the whole predicted x1.04-1.40 sits inside);
    tracking gain scatters +-0.06 and turn-hold +-0.12-0.15 at 120 s against predicted +-0.01.  Do NOT adopt "an
    unchanged 0.5-1 Hz error means the inertia shift did not reach the car".  Report the bands; he scores the feel.
  * REVERT SIGNATURE: grinding, stutter, or a NEW spectral line in 5-30 Hz on the tap or 0x18F (the controller's HF
    gain rises x1.852 at every frequency).

=== 3. THE COSTS, stated before the drive =================================================================
  (a) Added inertia below 2 Hz: low-speed 0.5-1 Hz lateral error predicted UP x1.04-1.4 (design panel, BELIEF:
      the 1-8 Hz plant is not identified).
  (b) Driver-override resistance roughly DOUBLES under the unchanged 616 T cap: on r71b's recorded hands-on motion
      (91.8 s) the byte-exact V295 march reads |trim| p99 166 -> 307 T, max 309 -> 554 T (adversary A; the
      clamped march is sub-linear, not x1.852 of 309), and the part opposing the driver's own torque p99 68 -> 125,
      max 163 -> 301 T.  Time with |trim| > 300 T on the r71b replay: 0.042 s -> 1.362 s (1 -> 13 episodes, longest
      42 -> 308 ms, 7 of them >= 75 ms), all but one below 5 m/s and mostly hands-on -- a rise in soft-EME dwell
      EXPOSURE with the reachable RANGE unchanged; V282's flown tap (|T| >= 1277 for up to 2.3 s at 0-5 m/s) bounds
      it; base assist is not modelled (BELIEF for the consequence).
  (c) The restart pulse after a filter bail (fault path only: |x| > 12000 = 1500 deg/s, implausible bar, invalid
      polarity -- never within 50 % of any of the three in 7.9 h of cached routes) roughly doubles.  At 100 deg/s
      over all 241 idx x demand sign x rate sign: zero command 146 -> 270 T, worst REACHABLE 165 -> 288 T (idx 238,
      output lag at the low end of its fixed-point interval after a falling demand; the cold-boot end reads 287 at
      idx 227 -- adversary A's correction of this record), worst per-point ratio x1.93.  🛑 ORCHESTRATOR'S RULING
      ON THE CAP (2026-09-30): H-SAFE-3 = 288 T was the design panel's own '2 x V294' policy bound, evaluated for a
      ONE-tick bail.  A 2-tick bail reads 308 T on V295 vs 192 on V294 (b <= 970 would keep the absolute 288 at
      every bail length); at every bail length the per-lane ratio to V294 is <= x2.0 and the b-dependent part is
      <= 124 T.  The cap is applied as the RELATIVE reading (<= 2 x V294 per lane, any bail length), which V295
      meets; the absolute 288 is met with ZERO margin at 1 tick and exceeded at 2 ticks.  Both readings are stated
      on the page.  Capped by construction at the 616 T trim cap.
  (c'') P-clamp rectification near the rail (adversary A, new): under zero-mean wheel-rate oscillation at idx >= ~230
      the P clamp binds on one half-cycle only, so mean |T| falls -- V295 about twice V294's loss (idx 240, 2.4 Hz,
      50 deg/s: -23 -> -51 T).  Torque-REDUCING only; never engaged on r71b (max |T| 1467).
  (c') int32: the a*s product's margin at the |x| = 12000 bail edge falls 4.058 -> 2.191 (the largest b keeping
      >= 2.0 at this pole is 1150).
  (d) The HF controller gain is x1.852 at every frequency (|P/x| 20 Hz 2.079 -> 3.850), inside the design's x3
      guard and x11.7 below V282's grinder.  Nothing above ~8 Hz is identified on this car.  The trim's 20 Hz
      damping SIGN is delay-dependent: damping at <= 2 ms after the tap, ANTI-damping from ~4-6 ms (and at 2 ms on
      the prior's flexible modes); at the delays where the model reproduces V282's on-car de-damping it removes
      3-6 % of what V282 removed (about twice V294's share), up to ~10-12 % in worlds where V282 is itself
      unstable in the model (adversary D).  The simulated 13-17 Hz delivered torque under the replayed road
      disturbance is x1.56-1.59 of V294 (0.93 vs 0.59 T rms, ~0.04 % of the rail; x0.97-1.08 under the plant-alone
      model) -- this CROSSES the trim-ratio lens's own x1.5 simulated-HF clause; the orchestrator re-decided the
      HF guard as 'controller gain < x3 of V294' and states so here.
  (d') Outer loop with the UNCHANGED fork law: gain margin improves on every simulated row (x1.05-1.66) and Ms is
      never worse, but the phase margin at 5 m/s falls by up to 7.7 deg (b_lo, relay on: 97.9 -> 90.2 deg) -- the
      inertia cost in the outer loop (adversary D).
  (e) The same lever as V294 pushed further at a comparable predicted step; the first step left "jerky on hard
      turns" in place.  Untested is not falsified, and the operator should be told before he drives it.
  REVERT PATH: V294's .rwd (sha256 a2b418f0...9f706a) stays on disk untouched; this script re-hashes it before and
  after writing.

=== 4. THE RISK STATEMENT ================================================================================
  Cal-only, two data bytes in a block V294 already re-CRC'd and flew.  The cell's sole reader is the fb lag; the
  quantities it scales (s gp-0x3d30, r26, |r26>>5| gp-0x6a34) have no monitor readers (census by two adversaries,
  2026-09-30).  int32: the one b-dependent product a*s keeps margin >= 2.0 at the |x| = 12000 bail edge ([10]).
  Authority does NOT rise: the rail, the surface and the zero-command trim cap are V294's ([8]); what rises is the
  TRIM GAIN below the cap (x1.852) and the fault-path restart pulse ([11]).
"""
import contextlib
import hashlib
import io
import math
import os
import struct
import sys
import zlib
from dataclasses import replace
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

import numpy as np                                                                   # noqa: E402

import build_vfourframe_tva as FF                                                    # noqa: E402
import build_v53_tva as V53                                                          # noqa: E402
import build_v293_tva as V293                                                        # noqa: E402
import build_v294_tva as V294                                                        # noqa: E402
import eps_lkas_chain_model as M                                                     # noqa: E402
from build_v293_tva import qwalk, u16, s16, u32, rec, y_off, runs, decode_one, scan_abs   # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table        # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path, RWD_DIR, ANALYSIS_ROOT   # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                              # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END, CODE_END = 0x13000, 0x100000, 0xC0000
WRITE_MODE = os.environ.get("ACCORD_V295_WRITE", "").strip().lower()
MAX_PATH = 259

# ---- the base: V294 --------------------------------------------------------------------------------------
BASE_NAME = ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0"
             "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
BASE_SHA = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
V294_RWD_NAME = ("39990-TVA,A160-V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960"
                 ".ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd")
V294_RWD_SHA = "a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a"
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# ---- THE EDIT -- the orchestrator's decision, 2026-09-30 --------------------------------------------------
B_CELL, B_BASE, B_NEW = 0xC63EA, 567, 1050
B_SITE = 0x28F86                     # ld.hu 0x73ea,tp,r16 -- the sole reader
A_CELL, A_SITE, A_VAL = 0xC63E8, 0x28F8A, 1011
C_CELL, C_SITES, C_VAL = 0xC62E6, (0x28F96, 0x28F9C, 0x28FB8), 1024
MUL_BX_SITE = 0x28F8E                # mul r16,r7,r0 -- b * x
CAL_BLOCK = (0xC6000, 0xC6FFC)
TRAILER = CAL_BLOCK[1]
ALLOWED = {B_CELL, B_CELL + 1} | set(range(TRAILER, TRAILER + 4))
TP_SETUP = (0x140C0, 0x140D8)        # ori 0x8000,r0,r1 ; movhi 0xfedf,r0,gp ; movea 0,gp,gp ; add r1,gp ;
                                     # movhi 0xb,r0,tp ; movea 0x7000,tp,tp ; add r1,tp
SUBR_SITE, SHL_SITE = 0x28FA4, 0x29D76
X_PER_DEGS = 8                       # 8.00 x-counts per deg/s: the 0x14A field is -x>>3 (0x55B48); measured 7.1-7.8
X_BAIL = 12000                       # |x| > 12000 bails (0x2EE0 + x < 0x5DC1 @0x28F5A)
RESTART_CAP = 288                    # H-SAFE-3: 2 x V294's 144/145 T (by sign) at 100 deg/s, 1-tick bail, cold-boot
                                     # lag end. Adversary A: the worst REACHABLE 1-tick pulse is 288 (0 T margin) and a
                                     # 2-tick bail reads 308; the orchestrator applies the cap as <= 2 x V294 per lane
                                     # at any bail length (docstring 3(c)). [11] asserts the 1-tick cold-boot reading.
INT32_MARGIN_MIN = 2.0               # H-SAFE-2
HF_RATIO_MAX = 3.0                   # H-HF-1
V282_PX_20HZ = 44.90                 # V282's |P+D / x| at 20 Hz (the flown grinder)
LIVE_SLOT, N_SLOTS = 7, 28
KP_PTR, KD_PTR, MAP_PTR = 0xCB994, 0xCB7D4, 0xC9A88
R24_CELL, DCLAMP_CELL, KI_CELL = 0xC6446, 0xC61B6, 0xC63E6
P_CLAMP, SUM_CLAMP, GAIN_CELL, OUT_CAP = 0xC61BC, 0xC61BE, 0xC6CD0, 0xC61B4
LAG_A_CELL, LAG_B_CELL, DEADBAND_CELL, ICLAMP_CELL = 0xC63EC, 0xC63EE, 0xC62E4, 0xC61BA
WIRE_PER_IDX = 16.125736
# the V294 values of every other cell in this lane -- read from the base and asserted [entailed] at [1]
FROZEN = dict(V294.FROZEN)
FROZEN.update({C_CELL: C_VAL, A_CELL: A_VAL, B_CELL: B_BASE})
# the address formers the two adversaries adjudicated VALUE-AGNOSTIC for the cal page (ADV-bytes-robust-joint sec.2.2):
#   mov imm32 0xC6000 @0x146DC (boot copy of the page to the RAM overlay) and @0x59560/0x5963E/0x59862 (page ops);
#   movea tp+0x7000 @0x140D2 (the tp set-up itself); movea tp+0x7010 @0x3ADFC/0x3AF1E (indexes <= 3 halfwords).
ADJUDICATED_MOV32 = {0x146DC, 0x59560, 0x5963E, 0x59862}
ADJUDICATED_MOVEA_TP = {0x140D2, 0x3ADFC, 0x3AF1E}
# found by THIS build's census, 2026-09-30 (not in the adversaries' lists), pinned so a new one cannot slip in:
#  * movhi bases 0xFA80 / 0xC / 0xD in [0x13000, 0xC5000): page-level bases (the boot overlay copy 0x146E4, the page
#    and memory-controller set-up 0x1BB1E..0x1CA54 and 0x59540..0x5989E, and six 0xC/0xD bases whose next access lands
#    at 0xC6FF4 / 0xCEFF4 / 0xBC2B8 / 0xBB7FC / 0xBBA70 -- none on the cell).  The kit's standing residual is that a
#    register-indirect index off one of them is invisible to any operand scan; V294 flew with b changed through all of
#    them (567 vs 1560) with no fault, which is the only evidence that they are value-agnostic.
#  * an any-base Format VII access with the cell's displacement: ONE hit, 0xBC3BA `st.w ..,0x3ea[r11]` -- DATA, not
#    code: no Ghidra function contains it and its bytes are a halving table (3217 1899 1003 509 256 128 64 ...).
ADJUDICATED_MOVHI = {0x146E4, 0x1BB1E, 0x1BBC2, 0x1C3CC, 0x1C4D4, 0x1C4F2, 0x1C756, 0x1C850, 0x1C91C, 0x1CA0A,
                     0x1CA54, 0x50B3C, 0x59540, 0x59574, 0x595D2, 0x596BE, 0x597B6, 0x597C8, 0x5989E, 0x5D6EA,
                     0x84692, 0x8496C, 0x849F0}
ADJUDICATED_ANYBASE_DATA = {0xBC3BA}


def pole_hz(a, ts=1e-3):
    return -math.log(a / 1024) / (2 * math.pi * ts)


def make_tag(b, a, C, kp, subr, shl, r24):
    return (f"V295-V294BASE-ACCELTRIM.B{b}-{'SUBR' if subr else 'ADD'}.SHL{shl}-FB.DIFF.C{C}"
            f"-POLE.{pole_hz(a):.1f}HZ.{a}.{b}-KP.FLAT.{kp}.ALL-KD0-R24.{r24}-MAP.LINEAR.TO6X.TORQUE.TAP")


# =======================================================================================================
#  ASSERTION MACHINERY -- FOUR census kinds (the kit's S/V/T plus C), so the count cannot flatter itself:
#   S  SUBSTANTIVE        a wrong EDIT of the image could fail it, and no earlier assertion entails it
#   C  CONSTANT-CHECK     fixed by the base hash, but would fail if one of THIS SCRIPT'S CONSTANTS were wrong
#                         (the reader census, the decoder's address, the stock table) -- it validates the script
#   V  VACUOUS            entailed by the base sha256 alone, or by an earlier passing assertion (the full diff)
#   T  TAUTOLOGICAL       a readback of a value this script just wrote, or a pin of one constant against another
# =======================================================================================================
OK, BAD = "[PASS]", "[FAIL]"


class Run:
    def __init__(self, quiet=False, collect=False):
        self.n = self.ok = 0
        self.census = {"S": 0, "C": 0, "V": 0, "T": 0}
        self.quiet, self.collect, self.failures = quiet, collect, []

    def check(self, cond, msg, kind="S"):
        assert kind in self.census
        self.n += 1
        self.census[kind] += 1
        cond = bool(cond)
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


# =======================================================================================================
#  AN INDEPENDENT DECODER for the handful of forms this build leans on -- written for V295 from the V850E2
#  field layout (hw1 = reg2[15:11] | opcode[10:5] | reg1[4:0]); it shares NO code with build_v293_tva.decode_one,
#  and [2] asserts the two agree on every site used.  It RAISES on anything else.
# =======================================================================================================
def _sx16(v):
    return v - 0x10000 if v & 0x8000 else v


def ind_decode(buf, off):
    hw1 = struct.unpack_from("<H", buf, off)[0]
    r1, op6, r2 = hw1 & 0x1F, (hw1 >> 5) & 0x3F, (hw1 >> 11) & 0x1F
    if op6 == 0b001110:                                             # Format I   add reg1,reg2
        return dict(kind="add", n=2, reg1=r1, reg2=r2)
    if op6 == 0b001100:                                             # Format I   subr reg1,reg2
        return dict(kind="subr", n=2, reg1=r1, reg2=r2)
    hw2 = struct.unpack_from("<H", buf, off + 2)[0]
    if op6 == 0b110100:                                             # Format VI  ori imm16 (ZERO-extended)
        return dict(kind="ori", n=4, reg1=r1, reg2=r2, imm=hw2)
    if op6 == 0b110010:                                             # Format VI  movhi imm16 -> imm16 << 16
        return dict(kind="movhi", n=4, reg1=r1, reg2=r2, imm=hw2)
    if op6 == 0b110001:                                             # Format VI  movea imm16 (SIGN-extended)
        return dict(kind="movea", n=4, reg1=r1, reg2=r2, imm=_sx16(hw2))
    if op6 == 0b111111 and (hw2 & 1):                               # Format VII ld.hu disp16[reg1], reg2
        return dict(kind="ld.hu", n=4, reg1=r1, reg2=r2, disp=_sx16(hw2 & 0xFFFE), width=2, signed=False)
    if op6 == 0b111001 and not (hw2 & 1):                           # Format VII ld.h
        return dict(kind="ld.h", n=4, reg1=r1, reg2=r2, disp=_sx16(hw2 & 0xFFFE), width=2, signed=True)
    if op6 == 0b111111 and (hw2 & 0x07FF) == 0x0220:                # Format XI  mul reg1,reg2,reg3
        return dict(kind="mul", n=4, reg1=r1, reg2=r2, reg3=hw2 >> 11)
    raise ValueError(f"ind_decode 0x{off:05X}: hw1 {hw1:04x} op6 {op6:#x} -- not a form V295 decodes")


def boot_regs(buf):
    """Execute the tp/gp set-up at 0x140C0..0x140D6 of THIS image with the independent decoder -> {reg: value}."""
    regs = {0: 0}
    pc = TP_SETUP[0]
    kinds = []
    while pc < TP_SETUP[1]:
        d = ind_decode(buf, pc)
        kinds.append(d["kind"])
        g = lambda r: regs.get(r, 0) if r else 0                     # noqa: E731
        if d["kind"] == "ori":
            regs[d["reg2"]] = (g(d["reg1"]) | d["imm"]) & 0xFFFFFFFF
        elif d["kind"] == "movhi":
            regs[d["reg2"]] = (g(d["reg1"]) + (d["imm"] << 16)) & 0xFFFFFFFF
        elif d["kind"] == "movea":
            regs[d["reg2"]] = (g(d["reg1"]) + d["imm"]) & 0xFFFFFFFF
        elif d["kind"] == "add":
            regs[d["reg2"]] = (g(d["reg1"]) + g(d["reg2"])) & 0xFFFFFFFF
        else:
            raise ValueError(f"unexpected {d['kind']} in the tp set-up")
        pc += d["n"]
    return regs, kinds


def read_through_reader(buf, site, want_kind):
    """Follow the instruction at `site`: decode it, resolve reg1 through the image's OWN boot set-up, and read the
    halfword it loads.  Returns (address, value, decoded)."""
    regs, _ = boot_regs(buf)
    d = ind_decode(buf, site)
    if d["kind"] != want_kind:
        raise ValueError(f"0x{site:05X} decodes as {d['kind']}, not {want_kind}")
    addr = (regs[d["reg1"]] + d["disp"]) & 0xFFFFFFFF
    raw = struct.unpack_from("<H", buf, addr)[0]
    return addr, (_sx16(raw) if d["signed"] else raw), d


# =======================================================================================================
#  GATE 1 -- a raw census of every instruction shape that could touch a cal byte (own scanner, positive controls)
# =======================================================================================================
ANYBASE_DISPS = {0x63E8, 0x63E9, 0x63EA, 0x63EB, 0x3E8, 0x3E9, 0x3EA, 0x3EB}   # cell offset from 0xC0000 / from the alias


def census_scan(buf, tp=0xBF000):
    f7, f14, mov32, movea_tp, movhi, f7any = [], [], [], [], [], []
    for o in range(START, END - 6, 2):
        hw1, hw2 = struct.unpack_from("<HH", buf, o)
        op6, r1, r2 = (hw1 >> 5) & 0x3F, hw1 & 0x1F, hw1 >> 11
        if r1 not in (4, 5) and o < 0xC5000 and op6 in (0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F):
            dsp = (_sx16(hw2) if op6 in (0x38, 0x3A) else _sx16((hw2 & 0xFFFE) | (op6 & 1)) if op6 in (0x3C, 0x3D)
                   else _sx16(hw2 & 0xFFFE))
            real = op6 in (0x38, 0x39, 0x3A, 0x3B) or ((hw2 & 1) and r2 != 0)
            if real and dsp in ANYBASE_DISPS:
                f7any.append((o, op6, r1, dsp))
        if r1 == 5:                                                       # tp-relative Format VII disp16
            k = None
            if op6 == 0x38:
                k, w, dsp = "ld.b", 1, _sx16(hw2)
            elif op6 == 0x3A:
                k, w, dsp = "st.b", 1, _sx16(hw2)
            elif op6 == 0x39:
                k, w, dsp = ("ld.w", 4, _sx16(hw2 & 0xFFFE)) if hw2 & 1 else ("ld.h", 2, _sx16(hw2 & 0xFFFE))
            elif op6 == 0x3B:
                k, w, dsp = ("st.w", 4, _sx16(hw2 & 0xFFFE)) if hw2 & 1 else ("st.h", 2, _sx16(hw2 & 0xFFFE))
            elif op6 in (0x3C, 0x3D) and (hw2 & 1) and r2 != 0:
                k, w, dsp = "ld.bu", 1, _sx16((hw2 & 0xFFFE) | (op6 & 1))
            elif op6 == 0x3F and (hw2 & 1) and r2 != 0:
                k, w, dsp = "ld.hu", 2, _sx16(hw2 & 0xFFFE)
            if k:
                f7.append((o, k, tp + dsp, w))
        grp = hw1 & 0xFFE0                                                 # Format XIV 6-byte disp23
        if grp in (0x0780, 0x07A0) and r1 in (4, 5):
            hw3 = struct.unpack_from("<H", buf, o + 4)[0]
            lo4, lo5 = hw2 & 0xF, hw2 & 0x1F
            bd = (hw3 << 7) | ((hw2 >> 4) & 0x7F)
            hd = (hw3 << 7) | (((hw2 >> 5) & 0x3F) << 1)
            bd = bd - (1 << 23) if bd & (1 << 22) else bd
            hd = hd - (1 << 23) if hd & (1 << 22) else hd
            k = None
            if grp == 0x0780:
                k, w, dsp = (("ld.b/23", 1, bd) if lo4 == 0x5 else ("ld.h/23", 2, hd) if lo5 == 0x07 else
                             ("ld.w/23", 4, hd) if lo5 == 0x09 else ("st.b/23", 1, bd) if lo4 == 0xD else
                             ("st.w/23", 4, hd) if lo5 == 0x0F else (None, 0, 0))
            else:
                k, w, dsp = (("ld.bu/23", 1, bd) if lo4 == 0x5 else ("ld.hu/23", 2, hd) if lo5 == 0x07 else
                             ("st.h/23", 2, hd) if lo5 == 0x0D else (None, 0, 0))
            if k:
                f14.append((o, k, r1, dsp, w))
        if (hw1 & 0xFFE0) == 0x0620:                                       # mov imm32, reg1
            mov32.append((o, r1, struct.unpack_from("<I", buf, o + 2)[0]))
        if op6 in (0x30, 0x31) and r1 == 5:                                # addi / movea imm16, tp, reg2
            movea_tp.append((o, tp + _sx16(hw2)))
        if op6 == 0x32:                                                    # movhi imm16, reg1, reg2
            movhi.append((o, r2, hw2))
    return dict(f7=f7, f14=f14, mov32=mov32, movea_tp=movea_tp, movhi=movhi, f7any=f7any)


_CENSUS = {}


def census_cached(buf):
    k = hashlib.sha256(bytes(buf[START:END])).hexdigest()
    if k not in _CENSUS:
        _CENSUS[k] = census_scan(bytes(buf))
    return _CENSUS[k]


def overlaps(addr, width, lo, hi):
    return addr < hi and addr + width > lo


# =======================================================================================================
#  THE LANE, TWO IMPLEMENTATIONS: (1) a vectorised numpy integer mirror (every `>>` floors like `sar`; int64 with an
#  int32 audit), and (2) the GOLDEN MODEL's own lkas_fb_lag + lkas_rate_pid_tick, tick for tick.  (1) is asserted
#  EQUAL to (2) on sampled lanes before any number from (1) is used.  Bail semantics from the V294 decompile of
#  FUN_00028ea6: the guard's else-arm sets the sentinel gp-0x3d2c := 2 (uVar12 = 2) and the PID arm's else feeds
#  S = 0 into the output lag (gp-0x3d3c), so the NEXT good tick reads s_old as 0 -> r26 = clamp(b*x >> 10).
# =======================================================================================================
def lane_cells(img):
    """Every constant of the lane, read from `img`.  a, b and C through the DECODED instructions that read them."""
    _, b, _ = read_through_reader(img, B_SITE, "ld.hu")
    _, a, _ = read_through_reader(img, A_SITE, "ld.h")
    _, C, _ = read_through_reader(img, C_SITES[0], "ld.hu")
    op = ind_decode(img, SUBR_SITE)["kind"]
    shl_hw = u16(img, SHL_SITE)
    assert (shl_hw >> 5) & 0x3F == 0x16 and (shl_hw >> 11) == 16, "0x29D76 is not shl imm5,r16"
    mX, mY = rec(img, u32(img, MAP_PTR + 4 * LIVE_SLOT))[1:]
    kX, kY = rec(img, u32(img, KP_PTR + 4 * LIVE_SLOT))[1:]
    dX, dY = rec(img, u32(img, KD_PTR + 4 * LIVE_SLOT))[1:]
    return dict(a=a, b=b, C=C, op={"subr": "diff", "add": "sum"}[op], shl=shl_hw & 0x1F,
                mX=tuple(mX), mY=tuple(mY), kX=tuple(kX), kY=tuple(kY), dX=tuple(dX), dY=tuple(dY),
                PC=u16(img, P_CLAMP), SC=u16(img, SUM_CLAMP), DC=u16(img, DCLAMP_CELL), Ki=u16(img, KI_CELL),
                LA=s16(img, LAG_A_CELL), LB=u16(img, LAG_B_CELL), G=s16(img, GAIN_CELL), OC=u16(img, OUT_CAP),
                DB=u16(img, DEADBAND_CELL), IC=u16(img, ICLAMP_CELL),
                FADE=V293.taper_factor(img, V293.TAPER_C))


def golden_cal(c):
    return replace(M.Calibration(), fb_lag_a=c["a"], fb_lag_b=c["b"], fb_clamp=c["C"], fb_op=c["op"],
                   e_shift=c["shl"], sum_clamp=c["SC"], pid_p_clamp=c["PC"], pid_d_clamp=c["DC"], pid_ki=c["Ki"],
                   pid_err_deadband=c["DB"], pid_i_clamp=c["IC"], out_lag_a=c["LA"], out_lag_b=c["LB"],
                   lkas_forward_gain=c["G"], out_clamp=c["OC"], override_taper_factor=c["FADE"],
                   assist_map_x=c["mX"], assist_map_y=c["mY"], kp_x=c["kX"], kp_y=c["kY"], kd_x=c["dX"], kd_y=c["dY"])


def golden_surface_signed(idx, sign, cal, fb=0):
    """lkas_rate_pid_surface's own algorithm (march from the cold-boot state until the output-lag state repeats)
    with sp = sign * LERP(map, idx), because the golden function only takes the positive demand."""
    sp = sign * M.lkas_rate_lerp(cal.assist_map_x, cal.assist_map_y, idx)
    st, seen, last = M.EpsState(), set(), None
    for _ in range(500000):
        if st.out_lag_s in seen:
            break
        seen.add(st.out_lag_s)
        last = M.lkas_rate_pid_tick(sp, fb, idx, st, cal)
    a, bb = M._signed16(cal.out_lag_a), cal.out_lag_b & 0xFFFF
    step = (last["S"] * bb) >> 10
    fixed = [L for L in range(st.out_lag_s - 96, st.out_lag_s + 96) if L == ((a * L) >> 10) + step]

    def deliver(s_state):
        yy = M._signed16((((s_state + s_state) >> 5) * st.pid_ramp) >> 15)
        return M._clamp((yy * M._signed16(cal.lkas_forward_gain)) >> 15, -cal.out_clamp, cal.out_clamp)
    band = sorted(deliver(L) for L in fixed) if fixed else [last["T"], last["T"]]
    return dict(sp=sp, T=last["T"], T_lo=band[0], T_hi=band[-1], P=last["P"], S=last["S"])


def golden_march(cal, x, sp, idx, n, bail_at=None):
    """Tick-for-tick golden march with the bail arm modelled as above.  Returns (T list, r26 list)."""
    st, sent, Ts, Rs = M.EpsState(), 0, [], []
    for t in range(n):
        if t == bail_at:
            sent = 2
            y = M.lkas_output_lag(0, st, cal)
            st.pid_prev_err_cell, st.pid_i_state = 0x7FFFFFFF, 0          # decompile: iVar31 = 0x7fffffff, iVar34 = 0
            yr = M._signed16((y * st.pid_ramp) >> 15)
            Ts.append(M._clamp((yr * M._signed16(cal.lkas_forward_gain)) >> 15, -cal.out_clamp, cal.out_clamp))
            Rs.append(0)
            continue
        fb = M.lkas_fb_lag(x, st, cal, lane_live=(sent == 1))
        sent = 1
        Ts.append(M.lkas_rate_pid_tick(sp, fb, idx, st, cal)["T"])
        Rs.append(fb)
    return Ts, Rs


def np_march(c, x, sp, n, bail_at=None, keep=None):
    """Vectorised integer lane over len(x) lanes.  Returns (T[n_keep, lanes], r26[n_keep, lanes], audit)."""
    x = np.asarray(x, np.int64)
    sp = np.asarray(sp, np.int64)
    kp = np.asarray([M.lkas_rate_lerp(c["kX"], c["kY"], i) for i in c["_idx"]], np.int64)
    kd = [M.lkas_rate_lerp(c["dX"], c["dY"], i) for i in c["_idx"]]
    assert all(v == 0 for v in kd) and c["DC"] == 0 and c["Ki"] == 0, "the np mirror assumes D = I = 0 (V294/V295)"
    a, b, C, shl = c["a"], c["b"], c["C"], c["shl"]
    s = np.zeros_like(x)
    L = np.zeros_like(x)
    sent = 0
    keep = range(n) if keep is None else keep
    keep = set(keep)
    Tk, Rk = [], []
    audit = 0
    for t in range(n):
        if t == bail_at:
            sent = 2
            S = np.zeros_like(x)
            r26 = np.zeros_like(x)
        else:
            s_old = s if sent == 1 else np.zeros_like(x)
            pa, pb = a * s_old, x * b
            audit = max(audit, int(np.abs(pa).max()), int(np.abs(pb).max()))
            s_new = (pa >> 10) + (pb >> 10)
            r26 = (s_new - s_old) if c["op"] == "diff" else (s_old + s_new)
            s = s_new
            sent = 1
            r26 = np.where(r26 > C, C, np.where(r26 < -C, -C, r26))
            E = (sp << shl) - r26
            pk = E * kp
            audit = max(audit, int(np.abs(pk).max()))
            P = np.clip(pk >> 8, -c["PC"], c["PC"])
            S = np.clip((c["FADE"] * P) >> 8, -c["SC"], c["SC"])
        la_L, S_lb = c["LA"] * L, S * c["LB"]
        audit = max(audit, int(np.abs(la_L).max()), int(np.abs(S_lb).max()))
        Ln = (la_L >> 10) + (S_lb >> 10)
        y = (L + Ln) >> 5
        L = Ln
        yr = (y * 0x8000) >> 15
        yr = ((yr + 0x8000) & 0xFFFF) - 0x8000
        T = np.clip((yr * c["G"]) >> 15, -c["OC"], c["OC"])
        if t in keep:
            Tk.append(T)
            Rk.append(r26)
    return np.array(Tk), np.array(Rk), audit


def fb_fixed_point(a, b, x):
    """The exact fixed point of s' = (a*s >> 10) + (b*x >> 10) from s = 0 (monotone map, so the max |s| too)."""
    s, peak = 0, 0
    for _ in range(1000000):
        s2 = ((a * s) >> 10) + ((b * x) >> 10)
        peak = max(peak, abs(a * s))
        if s2 == s:
            return s, peak
        s = s2
    raise AssertionError("no fixed point")


def px_20hz(a, b, kp, f=20.0):
    z = complex(math.cos(2 * math.pi * f * 1e-3), math.sin(2 * math.pi * f * 1e-3))
    return kp / 256 * abs((b / 1024) * (z - 1) / (z - a / 1024))


# =======================================================================================================
def build(b_new=None, quiet=False, do_rwd=True, base_bytes=None, mutate_payload=None, mutate_final=None,
          dose_check=True, collect=False, run=None):
    b_new = B_NEW if b_new is None else b_new
    R = run if run is not None else Run(quiet, collect)
    ck, say = R.check, R.say
    say("=" * 118)
    say(f"  V295 -- the V294 acceleration trim x{b_new / B_BASE:.3f}: ONE cal cell 0x{B_CELL:05X} (fb-lag input gain b) "
        f"{B_BASE} -> {b_new}")
    say("=" * 118)

    # ---------------------------------------------------------------------------------------------------
    say("\n  [1] BASE = V294")
    base = bytes(base_bytes if base_bytes is not None else Path(plain_image_path(BASE_NAME)).read_bytes())
    ck(hashlib.sha256(base).hexdigest() == BASE_SHA, f"V294 base sha256 == {BASE_SHA[:16]}...", "S")
    ck(qwalk(walk_all_blocks, base) == 0, "base CRC chain 50/50  [entailed]", "V")
    ck(qwalk(walk, base) == 0, "base BOOTLOADER CRC replay 49/49  [entailed]", "V")
    for addr, v in sorted(FROZEN.items()):
        ck(u16(base, addr) == v, f"base 0x{addr:05X} == {v}  [entailed]", "V")
    ck(base[B_CELL:B_CELL + 2] == bytes.fromhex("3702"), "base 0xC63EA-EB == 37 02 (567)  [entailed]", "V")
    ck(ind_decode(base, SUBR_SITE)["kind"] == "subr" and u16(base, SHL_SITE) == 0x82C2,
       "base carries V294's `subr r9,r26` @0x28FA4 and `shl 0x2,r16` @0x29D76  [entailed]", "V")
    kptrs = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    dptrs = [u32(base, KD_PTR + 4 * s) for s in range(N_SLOTS)]
    ck(all(rec(base, p)[2] == [960] * 5 for p in kptrs) and all(rec(base, p)[2] == [0] * 4 for p in dptrs),
       "base Kp bank [960]x5 and Kd bank [0]x4 on all 28 records  [entailed]", "V")
    if dose_check:
        ck(b_new == B_NEW, f"b_new {b_new} == the orchestrator's decision {B_NEW} (a pin: bites only off the default path)", "T")
        ck(0 < b_new < 32768, "b < 32768: `ld.hu` reads it unsigned; no sign question", "T")
    else:
        say("      (dose_check RELAXED -- the ZERO-EDIT CONTROL, not a flight candidate)")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [2] THE READER, DECODED INDEPENDENTLY (V295's own decoder; tp resolved from the image's own boot code)")
    regs, kinds = boot_regs(base)
    ck(kinds == ["ori", "movhi", "movea", "add", "movhi", "movea", "add"] and regs.get(5) == 0xBF000
       and regs.get(4) == 0xFEDF8000,
       f"0x140C0..0x140D6 executes {kinds}: tp = 0x{regs.get(5, 0):X}, gp = 0x{regs.get(4, 0):X}", "C")
    addr_b, val_b, d_b = read_through_reader(base, B_SITE, "ld.hu")
    ck(d_b["reg1"] == 5 and d_b["reg2"] == 16 and d_b["disp"] == 0x73EA and addr_b == B_CELL and val_b == B_BASE,
       f"0x{B_SITE:05X}: ld.hu 0x{d_b['disp']:X}[r{d_b['reg1']}=tp], r{d_b['reg2']} -> 0x{addr_b:05X} = {val_b} "
       f"(the EDIT's address 0x{B_CELL:05X} and V294's 567 -- anchored)", "C")
    addr_a, val_a, d_a = read_through_reader(base, A_SITE, "ld.h")
    ck(addr_a == A_CELL and val_a == A_VAL, f"0x{A_SITE:05X}: ld.h -> 0x{addr_a:05X} = {val_a} (the neighbour a, SIGNED)", "C")
    dm = ind_decode(base, MUL_BX_SITE)
    ck(dm["kind"] == "mul" and dm["reg1"] == 16 and dm["reg2"] == 7 and dm["reg3"] == 0,
       f"0x{MUL_BX_SITE:05X}: mul r{dm['reg1']},r{dm['reg2']},r{dm['reg3']} -- b (r16) multiplies x (r7), low word kept", "C")
    for site in (B_SITE, A_SITE, MUL_BX_SITE, SUBR_SITE):
        n2, m2, o2, f2 = decode_one(base, site)
        mine = ind_decode(base, site)
        ck(n2 == mine["n"] and m2 == mine["kind"], f"0x{site:05X}: the kit's decoder agrees (`{m2} {o2}`)", "C")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [3] GATE 1 -- who reads [0xC63EA, 0xC63EC)?  raw census, V295's own scanner, positive controls FIRST")
    cen = census_cached(base)
    f7 = cen["f7"]
    ck((B_SITE, "ld.hu", B_CELL, 2) in f7 and (A_SITE, "ld.h", A_CELL, 2) in f7
       and all((s_, "ld.hu", C_CELL, 2) in f7 for s_ in C_SITES),
       "CONTROL 4-byte: b @0x28F86, a @0x28F8A and all three C readers FOUND", "C")
    ck(any(o == 0x48E56 and k.endswith("/23") and r == 4 and dsp == -0x6752 for o, k, r, dsp, w in cen["f14"]),
       "CONTROL 6-byte Format XIV: gp-0x6752 @0x48E56 FOUND", "C")
    ck((0x29DC6, 0xCB994) in [(o, v) for o, r, v in cen["mov32"]], "CONTROL mov imm32 0xCB994 @0x29DC6 FOUND", "C")
    ck(KP_PTR + 4 * LIVE_SLOT in scan_abs(base, 0xE5378), "CONTROL LE32 absolute: the live Kp record pointer FOUND", "C")
    hit_b = [h for h in f7 if overlaps(h[2], h[3], B_CELL, B_CELL + 2)]
    hit_a = [h for h in f7 if overlaps(h[2], h[3], A_CELL, A_CELL + 2)]
    ck(hit_b == [(B_SITE, "ld.hu", B_CELL, 2)],
       f"4-byte tp-relative accesses overlapping 0xC63EA-EB (any width): {[(hex(h[0]), h[1]) for h in hit_b]} -- ONE, a load", "C")
    ck(hit_a == [(A_SITE, "ld.h", A_CELL, 2)], f"... and overlapping 0xC63E8-E9 (the neighbour a): {[(hex(h[0]), h[1]) for h in hit_a]}", "C")
    h14 = [h for h in cen["f14"] if h[2] == 5 and overlaps(0xBF000 + h[3], h[4], B_CELL - 2, B_CELL + 2)]
    ck(not h14, f"6-byte tp-relative accesses overlapping 0xC63E8-EB: {len(h14)}", "C")
    ck(not [a for a in range(START, END - 3) if B_CELL - 4 <= u32(base, a) < B_CELL + 2],
       "no LE32 anywhere in [0x13000,0x100000) points into [0xC63E6, 0xC63EC)", "C")
    m32 = {o for o, r, v in cen["mov32"] if 0xC6000 <= v < B_CELL + 2}
    ck(m32 == ADJUDICATED_MOV32, f"mov imm32 into [0xC6000, 0xC63EC): {sorted(hex(o) for o in m32)} == the "
                                 f"adversaries' value-agnostic set", "C")
    # the RAM overlay alias the boot copy at 0x146DC targets (0xFA800000 + page offset).  Found by THIS census
    # (2026-09-30, not in the adversaries' list): six `mov imm32 -> ep` at 0x1BB48..0x1BBAA with ep = 0xFA800050..5C,
    # each consumed by a Format IV sld.w/sst.w at disp 0.  Format IV reaches at most 0xFE (+3) above ep, so an ep base
    # below alias(0xC63EA) - 0x101 cannot touch the cell; any non-ep base register in the alias would need adjudication.
    alias_cell = 0xFA800000 + (B_CELL - 0xC6000)
    m32a = [(o, r, v) for o, r, v in cen["mov32"] if 0xFA800000 <= v < alias_cell + 2]
    ck(all(r == 30 and v + 0x101 < alias_cell for o, r, v in m32a),
       f"mov imm32 into the RAM alias [0xFA800000, 0x{alias_cell + 2:X}): {len(m32a)} sites "
       f"{sorted(hex(o) for o, r, v in m32a)}, ALL ep bases {sorted({hex(v) for o, r, v in m32a})} whose Format IV reach "
       f"(<= ep + 0x100) stops short of the cell's alias 0x{alias_cell:X}", "C")
    mtp = {o for o, v in cen["movea_tp"] if 0xC6000 <= v < B_CELL + 2}
    ck(mtp == ADJUDICATED_MOVEA_TP, f"movea/addi on tp into [0xC6000, 0xC63EC): {sorted(hex(o) for o in mtp)} == the adjudicated set", "C")
    ep_hits = [o for o, r, v in cen["mov32"] if r == 30 and B_CELL - 256 <= v <= B_CELL + 1]
    ck(not ep_hits, f"mov imm32 -> ep within sld reach (256 B) of the cell: {ep_hits}", "C")
    mh = [(o, r2, imm) for o, r2, imm in cen["movhi"] if imm in (0xC, 0xD, 0xFA80, 0xFA81) and o < 0xC5000]
    reach = []
    for o, r2, imm in mh:                                      # the ONE-instruction lookahead off each base
        h1, h2 = struct.unpack_from("<HH", base, o + 4)
        op6n, r1n = (h1 >> 5) & 0x3F, h1 & 0x1F
        if r1n == r2 and op6n in (0x30, 0x31, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F):
            ea = ((imm << 16) + (_sx16(h2) if op6n in (0x30, 0x31, 0x38, 0x3A) else _sx16(h2 & 0xFFFE))) & 0xFFFFFFFF
            if overlaps(ea, 4, B_CELL - 2, B_CELL + 2) or overlaps(ea, 4, alias_cell - 2, alias_cell + 2):
                reach.append(hex(o))
    ck({o for o, _r, _i in mh} == ADJUDICATED_MOVHI and not reach,
       f"movhi 0xC/0xD/0xFA80/0xFA81 bases in [0x13000,0xC5000): {len(mh)} == the pinned set; none whose next access "
       f"lands on the cell or its alias ({reach})", "C")
    anyb = {o for o, _op, _r, _d in cen["f7any"]}
    ck(anyb == ADJUDICATED_ANYBASE_DATA,
       f"any-base-register Format VII with the cell's displacement (0x63E8-EB / 0x3E8-EB): {sorted(hex(o) for o in anyb)} "
       f"== the one adjudicated DATA false positive", "C")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [4] APPLY -- one u16")
    code = bytearray(base)
    attributed = set()
    if u16(base, B_CELL) != b_new:
        struct.pack_into("<H", code, B_CELL, b_new)
        attributed |= {B_CELL, B_CELL + 1}
    ck(u16(code, B_CELL) == b_new, f"0x{B_CELL:05X} {u16(base, B_CELL)} -> {u16(code, B_CELL)} "
                                  f"({bytes(base[B_CELL:B_CELL + 2]).hex(' ')} -> {bytes(code[B_CELL:B_CELL + 2]).hex(' ')})", "T")
    if mutate_payload is not None:
        mutate_payload(code, attributed)

    # ---------------------------------------------------------------------------------------------------
    say("\n  [5] CRC -- the owning block located by walking the chain FROM THE IMAGE, trailer recomputed")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in attributed})
    if attributed:
        ck(blocks == [CAL_BLOCK], f"the edit's owning block(s) {[(hex(s_), hex(e_)) for s_, e_ in blocks]} == [0xC6000, 0xC6FFC)", "C")
    for b0, b1 in blocks:
        oldc, newc = u32(code, b1), zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        say(f"      block [0x{b0:06X},0x{b1:06X})  trailer 0x{oldc:08X} -> 0x{newc:08X}")
    if mutate_final is not None:
        mutate_final(code)
    ck(qwalk(walk_all_blocks, bytes(code)) == 0, "built image CRC chain 50/50 (the full linked list)", "S")
    ck(qwalk(walk, bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (NRC 0x72 predictor)", "S")
    ck(u32(code, TRAILER) == zlib.crc32(bytes(code[CAL_BLOCK[0]:CAL_BLOCK[1]])) & 0xFFFFFFFF,
       f"trailer 0x{TRAILER:05X} == crc32([0xC6000,0xC6FFC)) recomputed directly  [entailed by the walk]", "V")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [6] FULL BYTE DIFF vs V294 over [0x13000, 0x100000) -- EVERY differing offset listed")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    for s_, e_ in runs(diff):
        lbl = ("gain b 0xC63EA" if s_ <= B_CELL + 1 and e_ > B_CELL else
               "CRC trailer 0xC6FFC" if s_ >= TRAILER and e_ <= TRAILER + 4 else "UNATTRIBUTED")
        say(f"      0x{s_:06X}-0x{e_ - 1:06X} ({e_ - s_} B)  {lbl:22s} {bytes(base[s_:e_]).hex(' ')} -> {bytes(code[s_:e_]).hex(' ')}")
    say(f"      differing offsets: {[hex(a) for a in diff]}")
    stray = [hex(a) for a in diff if a not in ALLOWED]
    ck(not stray, f"every differing byte is 0xC63EA/0xC63EB or a trailer byte 0xC6FFC-FF ({len(stray)} stray: {stray[:6]})", "S")
    want_payload = {a for a in (B_CELL, B_CELL + 1) if struct.pack("<H", B_NEW)[a - B_CELL] != base[a]}
    trailer_diff = {a for a in range(TRAILER, TRAILER + 4) if code[a] != base[a]}
    ck(set(diff) == want_payload | trailer_diff and want_payload <= set(diff),
       f"the diff is EXACTLY the {len(want_payload)} payload bytes the decision requires + {len(trailer_diff)} trailer bytes "
       f"= {len(want_payload) + len(trailer_diff)} (got {len(diff)})", "S")
    ck(not [a for a in diff if a < CODE_END], "the code region [0x13000, 0xC0000) is BYTE-IDENTICAL to V294  [entailed by the line above]", "V")
    ck(bytes(code[0xC4B34:0xC4BD8]) == bytes(base[0xC4B34:0xC4BD8]) and bytes(code[0x55DF0:0x55E12]) == V293.PACK_V282,
       "the 0x14A cave and the CAN-427 tap window are V294's: THE INSTRUMENT IS ON THE WIRE  [entailed]", "V")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [7] b READ BACK THROUGH THE READER on the BUILT image (decode 0x28F86 -> tp from boot code -> value)")
    addr_b2, val_b2, _ = read_through_reader(bytes(code), B_SITE, "ld.hu")
    ck(addr_b2 == B_CELL and val_b2 == B_NEW,
       f"the instruction the lane executes reads 0x{addr_b2:05X} = {val_b2} (decision {B_NEW}); bytes "
       f"{bytes(code[addr_b2:addr_b2 + 2]).hex(' ')}", "T")
    addr_a2, val_a2, _ = read_through_reader(bytes(code), A_SITE, "ld.h")
    ck(val_a2 == A_VAL, f"the neighbour a through 0x28F8A is still {val_a2}  [entailed by the diff]", "V")
    ck(all(read_through_reader(bytes(code), s_, "ld.hu")[1] == C_VAL for s_ in C_SITES),
       "C through all three readers is still 1024  [entailed by the diff]", "V")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [8] THE DELIVERED SURFACE (golden model, cells read from EACH image) -- 241 idx x both demand signs")
    c_new, c_old = lane_cells(bytes(code)), lane_cells(base)
    g_new, g_old = golden_cal(c_new), golden_cal(c_old)
    ctl = [(M.lkas_rate_pid_surface(i, g_old)["T"], golden_surface_signed(i, +1, g_old)["T"]) for i in (0, 37, 120, 239, 240)]
    ck(all(p == q for p, q in ctl), f"CONTROL: the signed wrapper == lkas_rate_pid_surface itself at + sign {ctl}", "C")
    mism, surf = [], {}
    for sg in (+1, -1):
        for i in range(241):
            v, w = golden_surface_signed(i, sg, g_new), golden_surface_signed(i, sg, g_old)
            surf[(sg, i)] = v
            if (v["T"], v["T_lo"], v["T_hi"], v["P"], v["S"]) != (w["T"], w["T_lo"], w["T_hi"], w["P"], w["S"]):
                mism.append((sg, i))
    ck(not mism, f"V295 == V294 at r26 = 0 on T, T_lo, T_hi, P, S at all 482 idx x sign ({len(mism)} differ)  "
                 f"[entailed: b is not read at r26 = 0 and no other byte moved]", "V")
    ck(surf[(1, 240)]["T"] == 2461 and surf[(-1, 240)]["T"] == -2463,
       f"rail +{surf[(1, 240)]['T']} / {surf[(-1, 240)]['T']}  [entailed]", "V")
    say("      idx    T(+)    T(-)")
    for i in (0, 12, 32, 60, 120, 180, 238, 240):
        say(f"      {i:3d}  {surf[(1, i)]['T']:6d}  {surf[(-1, i)]['T']:6d}")
    cap = {sg: (golden_surface_signed(0, 1, g_new, fb=sg * c_new["C"])["T"], golden_surface_signed(0, 1, g_old, fb=sg * c_old["C"])["T"])
           for sg in (+1, -1)}
    ck(cap[1][0] == cap[1][1] and cap[-1][0] == cap[-1][1],
       f"the zero-command trim cap at r26 = +C / -C: {cap[1][0]} / {cap[-1][0]} (V294 {cap[1][1]} / {cap[-1][1]})  [entailed]", "V")
    xs = np.array([i * WIRE_PER_IDX for i in range(1, 239)])
    slope_new = float(np.polyfit(xs, [surf[(1, i)]["T"] for i in range(1, 239)], 1)[0])
    slope_old = float(np.polyfit(xs, [golden_surface_signed(i, 1, g_old)["T"] for i in range(1, 239)], 1)[0])
    ck(slope_new == slope_old, f"sub-rail slope {slope_new:.4f} T per wire count (V294 {slope_old:.4f})  [entailed]", "V")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [9] THE FULL LANE WITH b IN THE TRANSIENT -- constant wheel rate x from cold boot, V295 vs V294")
    idxs = list(range(241))
    xs_const = (80, -80, 800, -800, 12000, -12000)
    lanes = [(i, sg, xv) for xv in xs_const for sg in (1, -1) for i in idxs]
    for cc in (c_new, c_old):
        cc["_idx"] = [ln[0] for ln in lanes]
    sp_l = [ln[1] * M.lkas_rate_lerp(c_new["mX"], c_new["mY"], ln[0]) for ln in lanes]
    x_l = [ln[2] for ln in lanes]
    NT = 6000
    Tn, Rn, aud_n = np_march(c_new, x_l, sp_l, NT, keep=range(NT - 1000, NT))
    To, Ro, aud_o = np_march(c_old, x_l, sp_l, NT, keep=range(NT - 1000, NT))
    # two implementations: the golden march, tick for tick, on sampled lanes
    samp = [k for k, ln in enumerate(lanes) if ln[0] in (0, 57, 120, 238, 240) and ln[2] in (800, -12000)]
    for cc in (c_new,):
        cc["_idx"] = [lanes[k][0] for k in samp]
    Ts_np, Rs_np, _ = np_march(c_new, [x_l[k] for k in samp], [sp_l[k] for k in samp], 3000)
    bad = 0
    for j, k in enumerate(samp):
        Tg, Rg = golden_march(g_new, x_l[k], sp_l[k], lanes[k][0], 3000)
        bad += int(any(Tg[t] != Ts_np[t, j] or Rg[t] != Rs_np[t, j] for t in range(3000)))
    ck(bad == 0, f"CONTROL: the numpy lane == the golden model tick for tick on {len(samp)} lanes x 3000 ticks ({bad} lanes differ)", "C")
    ck(aud_n < 2 ** 31 and aud_o < 2 ** 31, f"int32 audit of every product in the march: max |.| = {aud_n:,} (< 2^31)", "S")
    ck(not np.any(Rn[-500:]) and np.all(Tn[-1] == Tn[-500]),
       f"r26 settles to EXACTLY 0 and T is constant over the last 500 ticks on all {len(lanes)} lanes (x in {xs_const})", "S")
    dif = int(np.sum(Tn[-1] != To[-1]))
    ck(dif == 0, f"the settled T equals V294's on all {len(lanes)} idx x sign x rate lanes ({dif} differ) -- b's transient "
                 f"does not land the output lag on a different fixed point", "S")
    gold_off = sum(1 for k, ln in enumerate(lanes) if not (surf[(ln[1], ln[0])]["T_lo"] <= Tn[-1, k] <= surf[(ln[1], ln[0])]["T_hi"]))
    say(f"      (settled T outside the golden fixed-point band [T_lo, T_hi]: {gold_off} of {len(lanes)} lanes -- identical on V294)")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [10] int32 -- the one b-dependent product a*s, at the exact fixed point of the |x| = 12000 bail edge")
    marg = {}
    for tag_, cc in (("V295", c_new), ("V294", c_old)):
        sp_, pk_p = fb_fixed_point(cc["a"], cc["b"], X_BAIL)
        sn_, pk_n = fb_fixed_point(cc["a"], cc["b"], -X_BAIL)
        marg[tag_] = (2 ** 31) / max(pk_p, pk_n)
        say(f"      {tag_}: s* = {sn_:,} / {sp_:,};  max |a*s| = {max(pk_p, pk_n):,};  margin {marg[tag_]:.3f};  |b*x| = {cc['b'] * X_BAIL:,}")
    def _m(bb):
        return (2 ** 31) / max(fb_fixed_point(c_new["a"], bb, X_BAIL)[1], fb_fixed_point(c_new["a"], bb, -X_BAIL)[1])
    lo_, hi_ = 1, 4096                                  # the margin falls monotonically in b: bisect for the last >= 2.0
    while hi_ - lo_ > 1:
        mid = (lo_ + hi_) // 2
        lo_, hi_ = (mid, hi_) if _m(mid) >= 2.0 else (lo_, mid)
    b_max2 = lo_
    ck(marg["V295"] >= INT32_MARGIN_MIN, f"int32 margin {marg['V295']:.3f} >= {INT32_MARGIN_MIN} (V294 {marg['V294']:.3f}; the "
                                         f"largest b with margin >= 2.0 at this pole is {b_max2})", "S")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [11] THE RESTART PULSE after one bail tick, 100 deg/s (x = +-800), over idx 0..240 x demand sign x rate sign")
    rl = [(i, sg, rs) for i in idxs for sg in (1, -1) for rs in (1, -1)]
    for cc in (c_new, c_old):
        cc["_idx"] = [ln[0] for ln in rl]
    sp_r = [ln[1] * M.lkas_rate_lerp(c_new["mX"], c_new["mY"], ln[0]) for ln in rl]
    x_r = [ln[2] * 100 * X_PER_DEGS for ln in rl]
    PRE, POST = 3000, 1500
    pulse = {}
    for tag_, cc in (("V295", c_new), ("V294", c_old)):
        TT, RR, _ = np_march(cc, x_r, sp_r, PRE + 1 + POST, bail_at=PRE, keep=range(PRE - 500, PRE + 1 + POST))
        ck(not np.any(RR[:500]) and np.all(TT[498] == TT[499]),
           f"{tag_}: every lane settled before the bail (r26 == 0 and T constant on the last 500 pre ticks)"
           + ("" if tag_ == "V295" else "  [entailed by the base hash]"), "S" if tag_ == "V295" else "V")
        dev = np.abs(TT[500:] - TT[499])
        pulse[tag_] = (dev.max(axis=0), dev[1:].max(axis=0))
    inc, exc = pulse["V295"]
    k = int(np.argmax(inc))
    ratio = inc / np.maximum(pulse["V294"][0], 1)
    kz = [j for j, ln in enumerate(rl) if ln[0] == 0]
    say(f"      V295 worst {int(inc[k])} T at idx {rl[k][0]} demand {rl[k][1]:+d} rate {rl[k][2]:+d} (excluding the bail tick itself: "
        f"{int(exc.max())});  V294 worst {int(pulse['V294'][0].max())}")
    say(f"      zero command (idx 0): V295 {sorted({int(inc[j]) for j in kz})}  V294 {sorted({int(pulse['V294'][0][j]) for j in kz})};  "
        f"worst per-point ratio {ratio.max():.3f} at idx {rl[int(np.argmax(ratio))][0]};  worst/worst "
        f"{inc.max() / pulse['V294'][0].max():.3f};  lanes over {RESTART_CAP}: {int(np.sum(inc > RESTART_CAP))}")
    for i in (0, 60, 120, 180, 238, 240):
        js = [j for j, ln in enumerate(rl) if ln[0] == i]
        say(f"        idx {i:3d}: V295 max {int(max(inc[j] for j in js)):4d}   V294 max {int(max(pulse['V294'][0][j] for j in js)):4d}")
    ck(inc.max() <= RESTART_CAP, f"restart pulse max {int(inc.max())} T <= {RESTART_CAP} over all {len(rl)} lanes (bail tick included)", "S")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [12] THE TRIM IN PHYSICAL TERMS, from the built cells")
    kp_live = c_new["kY"][0]
    fwd = (c_new["FADE"] / 256) * (2 * c_new["LB"] / ((1024 - c_new["LA"]) * 32)) * (c_new["G"] / 32768)
    for tag_, cc in (("V294", c_old), ("V295", c_new)):
        ka = (kp_live / 256) * cc["b"] / (1024 - cc["a"]) * 1e-3 * X_PER_DEGS * fwd
        say(f"      {tag_}: K_alpha = {ka:.3f} T counts per deg/s^2 below the {pole_hz(cc['a']):.2f} Hz pole;  "
            f"|P/x| at 20 Hz {px_20hz(cc['a'], cc['b'], kp_live):.3f};  2.4 Hz {px_20hz(cc['a'], cc['b'], kp_live, 2.4):.3f}")
    p_new, p_old = px_20hz(c_new["a"], c_new["b"], kp_live), px_20hz(c_old["a"], c_old["b"], kp_live)
    ck(abs(p_new / (p_old * B_NEW / B_BASE) - 1) < 0.01 and p_new / p_old < HF_RATIO_MAX,
       f"|P/x| at 20 Hz {p_new:.3f} = {p_new / p_old:.3f} x V294's {p_old:.3f} (< x{HF_RATIO_MAX}); "
       f"{20 * math.log10(p_new / V282_PX_20HZ):.1f} dB below V282's {V282_PX_20HZ}", "S")

    # ---------------------------------------------------------------------------------------------------
    say("\n  [13] THE OUTPUT NAME, RE-DERIVED FROM THE BUILT IMAGE'S OWN BYTES")
    kp_all = {v for s_ in range(N_SLOTS) for v in rec(code, u32(code, KP_PTR + 4 * s_))[2]}
    kd_all = {v for s_ in range(N_SLOTS) for v in rec(code, u32(code, KD_PTR + 4 * s_))[2]}
    ck(len(kp_all) == 1 and kd_all == {0} and u16(code, DCLAMP_CELL) == 0,
       f"Kp flat {sorted(kp_all)} on all 28, Kd {sorted(kd_all)} and D clamp 0  [entailed]", "V")
    tag = make_tag(val_b2, val_a2, u16(code, C_CELL), kp_all.pop() if len(kp_all) == 1 else -1,
                   ind_decode(bytes(code), SUBR_SITE)["kind"] == "subr", u16(code, SHL_SITE) & 0x1F, u16(code, R24_CELL))
    TAG = make_tag(B_NEW, A_VAL, C_VAL, 960, True, 2, 2048)
    ck(tag == TAG, f"the tag from the image's own halfwords == the decision's tag ({tag})", "S")
    IMG_NAME = f"_v295_{TAG}_plain_image.bin"
    RWD_NAME = f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd"
    say(f"      {IMG_NAME}\n      {RWD_NAME}")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd = rwd_sha = None
    if do_rwd:
        say("\n  [14] .rwd ENCODE + READBACK + an independent re-splice")
        src = Path(FF.V38_RWD).read_bytes()
        ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches (the container template)", "C")
        FF.assert_x31_checksum(src, "V38 source")
        info = parse_x31(src)
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(invert_table(dec_tbl))])
        FF.assert_x31_checksum(rwd, "V295 output")
        back = bytearray(base)
        back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
        ck(bytes(back) == bytes(code), "the .rwd decoded back is BYTE-IDENTICAL to the built image", "S")
        v38 = bytearray(base)
        v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
        ck(hashlib.sha256(bytes(v38[START:END])).hexdigest()
           == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
           "cipher table validated NON-CIRCULARLY against the known V38 plain image", "S")
        rwd_sha = hashlib.sha256(rwd).hexdigest()
        ind = bytearray(base)
        struct.pack_into("<H", ind, B_CELL, B_NEW)
        for s0, s1 in FF.crc_block_map(bytes(ind)):
            if s0 <= B_CELL < s1:
                struct.pack_into("<I", ind, s1, zlib.crc32(bytes(ind[s0:s1])) & 0xFFFFFFFF)
        ck(hashlib.sha256(bytes(ind)).hexdigest() == img_sha,
           "independent re-splice (FF.crc_block_map locator) == the built image sha256", "S")

        say("\n  [15] THE CUMULATIVE NON-STOCK DELTA of the lane, read from the STOCK dump and the BUILT image")
        stock = Path(stock_fw_path("code.bin")).read_bytes()
        ck(hashlib.sha256(stock).hexdigest() == STOCK_SHA, "stock dump sha256 matches", "C")
        rows = [("fb clamp C", C_CELL, 7680, 1024), ("pole a", A_CELL, 923, 1011), ("gain b", B_CELL, 1560, 1050),
                ("D clamp", DCLAMP_CELL, 10240, 0), ("r24 engaged arm", R24_CELL, 512, 2048), ("Ki", KI_CELL, 0, 0)]
        for name, addr, st_v, v295_v in rows:
            ck(u16(stock, addr) == st_v and u16(code, addr) == v295_v,
               f"{name:16s} 0x{addr:05X}: stock {u16(stock, addr):6d}  ->  V295 {u16(code, addr):6d}", "C")
        sk = rec(stock, u32(stock, KP_PTR + 4 * LIVE_SLOT))[2]
        sd = rec(stock, u32(stock, KD_PTR + 4 * LIVE_SLOT))[2]
        ck(sk == [248, 512, 645, 696, 696] and sd == [128] * 4 and c_new["kY"] == (960,) * 5 and c_new["dY"] == (0,) * 4,
           f"Kp slot 7 stock {sk} -> V295 {list(c_new['kY'])};  Kd stock {sd} -> V295 {list(c_new['dY'])}", "C")
        ck(ind_decode(stock, SUBR_SITE)["kind"] == "add" and u16(stock, SHL_SITE) & 0x1F == 5
           and ind_decode(bytes(code), SUBR_SITE)["kind"] == "subr" and u16(code, SHL_SITE) & 0x1F == 2,
           "0x28FA4 stock `add` -> V295 `subr`;  0x29D76 stock `shl 0x5` -> V295 `shl 0x2`", "C")
        d295 = {a for a in range(START, END) if code[a] != stock[a]}
        d294 = {a for a in range(START, END) if base[a] != stock[a]}
        say(f"      bytes differing from STOCK in [0x13000,0x100000): V295 {len(d295)}  V294 {len(d294)}  "
            f"(symmetric difference {sorted(hex(a) for a in d295 ^ d294)})")
        ck(d295 - d294 <= ALLOWED and d294 - d295 <= ALLOWED,
           "V295's non-stock byte set == V294's up to the cell and the trailer  [entailed]", "V")

    out_i, out_r = Path(plain_image_path(IMG_NAME)), Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_i)) <= MAX_PATH and len(str(out_r)) <= MAX_PATH,
       f"both output paths fit {MAX_PATH} chars (image {len(str(out_i))}, rwd {len(str(out_r))})", "C")
    say("\n" + "=" * 118)
    say(f"  PREDICTED image SHA256 {img_sha}")
    if rwd_sha:
        say(f"  PREDICTED .rwd  SHA256 {rwd_sha}")
    say(f"  {R.ok}/{R.n} assertions -- census: {R.census['S']} substantive, {R.census['C']} constant-checks, "
        f"{R.census['V']} vacuous/entailed, {R.census['T']} tautological")
    say("=" * 118)
    return dict(code=bytes(code), base=base, rwd=rwd, img_sha=img_sha, rwd_sha=rwd_sha, tag=TAG,
                img_name=IMG_NAME, rwd_name=RWD_NAME, run=R, diff=diff, restart=int(inc.max()),
                margin=marg["V295"], px20=p_new)


# =======================================================================================================
def zero_edit_control(base):
    r = build(b_new=B_BASE, quiet=True, do_rwd=False, base_bytes=base, dose_check=False, collect=True)
    return r["img_sha"], len(r["diff"]), r["run"].failures


def mutation_test(base):
    """Each mutation must be CAUGHT (>= 1 assertion fires or the build raises).  (a)-(d) are the brief's four."""
    def a_wrong_byte(code, att):            # (a) the value landed ONE BYTE HIGH: 0xC63EA restored, 1050 at 0xC63EB
        code[B_CELL:B_CELL + 2] = base[B_CELL:B_CELL + 2]
        struct.pack_into("<H", code, B_CELL + 1, B_NEW)

    def a2_low_byte_only(code, att):        # (a') only the low byte written: 02 1a -> 0x021a = 538
        code[B_CELL + 1] = base[B_CELL + 1]

    def b_1051(code, att):                  # (b) 1050 -> 1051
        struct.pack_into("<H", code, B_CELL, B_NEW + 1)

    def c_trailer_flip(code):               # (c) the trailer, AFTER the CRC step
        code[TRAILER] ^= 0x01

    def d_neighbour_a(code, att):           # (d) the neighbouring cell 0xC63E8 (a) 1011 -> 1012, CRC recomputed
        struct.pack_into("<H", code, A_CELL, A_VAL + 1)

    def e_big_endian(code, att):            # the value byte-swapped: 04 1a
        code[B_CELL:B_CELL + 2] = struct.pack(">H", B_NEW)

    def f_edit_not_taken(code, att):        # b left at 567
        struct.pack_into("<H", code, B_CELL, B_BASE)

    def g_code_stray(code, att):            # an unattributed code byte (main block CRC left stale)
        code[0x2A1F0] ^= 0x01

    def h_same_block_cell(code, att):       # D clamp resurrected IN THE SAME BLOCK, so the CRC is consistent
        struct.pack_into("<H", code, DCLAMP_CELL, 10240)

    def i_kp_live_knot(code, att):          # the live Kp knot 960 -> 961 (another block)
        struct.pack_into("<H", code, y_off(0xE5378, 5, 0), 961)

    muts = [("(a) wrong byte: 1050 at 0xC63EB", a_wrong_byte, None), ("(a') low byte only", a2_low_byte_only, None),
            ("(b) 1050 -> 1051", b_1051, None), ("(c) trailer bit flip", None, c_trailer_flip),
            ("(d) neighbour a 1011 -> 1012", d_neighbour_a, None), ("big-endian 04 1a", e_big_endian, None),
            ("edit not taken (567)", f_edit_not_taken, None), ("stray code byte 0x2A1F0", g_code_stray, None),
            ("D clamp 10240, same block", h_same_block_cell, None), ("Kp live knot 961", i_kp_live_knot, None)]
    out = []
    for name, mp, mf in muts:
        R = Run(quiet=True, collect=True)        # kept across an exception, so every catch is attributed
        try:
            build(do_rwd=False, base_bytes=base, mutate_payload=mp, mutate_final=mf, run=R)
            fails = list(R.failures)
        except SystemExit as e:
            fails = list(R.failures) + [("S", str(e))]
        except Exception as e:                  # a mutation that breaks a decoder or a mirror is ALSO a catch
            fails = list(R.failures) + [("X", f"raised {type(e).__name__}: {e}")]
        out.append((name, fails))
    return out


def v295_artifacts():
    img = [f for f in Path(ANALYSIS_ROOT).glob("_v295*") if not f.name.startswith("SUPERSEDED")]
    rwd = [f for f in Path(RWD_DIR).glob("*-V295-*") if not f.name.startswith("SUPERSEDED")]
    return img, rwd


def v294_tripwire():
    i = hashlib.sha256(Path(plain_image_path(BASE_NAME)).read_bytes()).hexdigest()
    r = hashlib.sha256(Path(RWD_DIR, V294_RWD_NAME).read_bytes()).hexdigest()
    return i == BASE_SHA and r == V294_RWD_SHA, i, r


def main():
    base = Path(plain_image_path(BASE_NAME)).read_bytes()
    if hashlib.sha256(base).hexdigest() != BASE_SHA:
        raise SystemExit("V294 base sha256 mismatch -- refusing to go further")
    ok294, i294, r294 = v294_tripwire()
    print(f"      V294 image {i294[:16]}...  V294 rwd {r294[:16]}...  -> {'UNCHANGED' if ok294 else '🛑 CHANGED'}")
    if not ok294:
        raise SystemExit("V294's own artifacts have changed -- stopping.")

    print("=" * 118)
    print("  [0] ZERO-EDIT CONTROL -- b left at 567 must reproduce the V294 image BIT FOR BIT")
    sha0, d0, f0 = zero_edit_control(base)
    print(f"      {'[PASS]' if sha0 == BASE_SHA and d0 == 0 else '[FAIL]'} zero-edit sha256 {sha0[:16]}... == V294 "
          f"{BASE_SHA[:16]}... ({d0} differing bytes; {len(f0)} assertion(s) fired with the dose pin relaxed)")
    for _k, m in f0[:4]:
        print(f"         - {m[:110]}")
    if sha0 != BASE_SHA or d0 != 0:
        raise SystemExit("ZERO-EDIT CONTROL FAILED")

    print("\n  [0c] MUTATION TEST -- each flip must be CAUGHT")
    res = mutation_test(base)
    missed = []
    for name, fails in res:
        by = {k_: sum(1 for kk, _m in fails if kk == k_) for k_ in ("S", "C", "V", "T", "X")}
        print(f"      {'[CAUGHT]' if fails else '🛑 [MISSED]'} {name:34s} {len(fails):3d} fire  "
              f"(S {by['S']} C {by['C']} V {by['V']} T {by['T']} raised {by['X']})")
        for kind, m in fails[:4]:
            print(f"                   - [{kind}] {m[:104]}")
        if not fails:
            missed.append(name)
    print(f"      {'[PASS]' if not missed else '[FAIL]'} {len(res) - len(missed)}/{len(res)} mutations caught"
          + (f"  MISSED: {missed}" if missed else ""))
    if missed:
        raise SystemExit("MUTATION TEST FAILED")

    print()
    r = build()
    print(f"\n  PREDICTION, printed BEFORE any write:  image {r['img_sha']}\n                                          rwd   {r['rwd_sha']}")
    if WRITE_MODE == "rwd":
        print("\n  [16] WRITE -- guarded BEFORE the write, re-hashed and decoded AFTER")
        pre_i, pre_r = v295_artifacts()
        if pre_i or pre_r:
            raise SystemExit(f"WRITE GUARD: a non-superseded V295 artifact already exists "
                             f"({[f.name for f in pre_i]}, {[f.name for f in pre_r]}) -- refusing to overwrite.")
        out_img, out_rwd = Path(plain_image_path(r["img_name"])), Path(RWD_DIR, r["rwd_name"])
        with open(out_img, "xb") as fh:
            fh.write(r["code"])
        with open(out_rwd, "xb") as fh:
            fh.write(r["rwd"])
        disk_i, disk_r = out_img.read_bytes(), out_rwd.read_bytes()
        hi, hr = hashlib.sha256(disk_i).hexdigest(), hashlib.sha256(disk_r).hexdigest()
        assert hi == r["img_sha"], f"on-disk image {hi} != predicted {r['img_sha']}"
        assert hr == r["rwd_sha"], f"on-disk rwd {hr} != predicted {r['rwd_sha']}"
        dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        FF.assert_x31_checksum(disk_r, "V295 rwd on disk")
        back = bytearray(r["base"])
        back[START:END] = bytes(parse_x31(disk_r)["encs"][0]).translate(dec_tbl)
        assert bytes(back) == disk_i, "the on-disk rwd does not decode to the on-disk image"
        post_i, post_r = v295_artifacts()
        assert len(post_i) == 1 and len(post_r) == 1, f"expected exactly one V295 image and rwd, got {post_i}, {post_r}"
        ok294b, _, _ = v294_tripwire()
        assert ok294b, "V294's artifacts changed during the write"
        print(f"      [PASS] image on disk re-hashes to the prediction  {hi}")
        print(f"      [PASS] rwd   on disk re-hashes to the prediction  {hr}")
        print(f"      [PASS] the on-disk rwd decodes to the on-disk image; x31 checksum OK")
        print(f"      [PASS] exactly one V295 image and one V295 rwd on disk; V294's image and rwd unchanged")
        print(f"      {out_img}\n      {out_rwd}")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V295_WRITE=rwd to emit the files.")


if __name__ == "__main__":
    main()
