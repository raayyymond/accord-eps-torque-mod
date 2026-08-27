#!/usr/bin/env python3
"""V69 -- revert the LKAS gate, shape Honda's own low-speed rate-gain surface.

Full rationale, evidence and both gates: `docs/specs/design/V69-DESIGN.md`. This file is the executable
version of that spec and re-derives every load-bearing number from the image.

THE PROBLEM
-----------
Routes `4c`/`4e` (V68) captured the operator's highway lane-change vibration: `4e` seg 33
t = 51.3 s, an openpilot ALC right lane change at 25.93 m/s -- bar **1468 counts p-p**, 26-30 Hz
envelope 614 (20x the route median), lines at 28.12/28.51 Hz at prominence 100-107, while
**40-49 Hz reads 69 in the same window**. Not wheel order 2 (24.93 Hz) or 3 (37.40), not engine
order 1 (26.10) or 2 (52.20).

V67/V68's rate-lane arm is a FLAT scalar taken whenever the LKAS gate is open. Honda's stock
surface rolls off with speed (3072 -> 2151); the flat arm does not follow it, so the delivered
multiplier RISES with speed and peaks at highway -- 2.4383x, exactly where the symptom is:

    stock LERP  grind #1 (7.2 km/h) = 2622        arm 5244 => 2.000x
    stock LERP  highway  (110 km/h) = 2151        arm 5244 => 2.4383x

One scalar cannot serve both ends: 1.00x at highway needs 2172, which is 0.83x at grind #1 --
BELOW stock, i.e. V61 territory, and V61 made grind #1 WORSE.

THE DESIGN, AND WHY IT IS FORCED
--------------------------------
The gate branch at `0x3AC04-0x3AC0C` is `cmp`(2) + `be`(2) + `ld.hu`(4) + `br`(2) = **10 bytes,
fully packed between two other arms -- zero slack**, and it REPLACES the LERP rather than scaling
it. So speed shaping can only reach the engaged path if the gate is off. Composing "gated AND
speed-shaped" needs new instructions on the 1 kHz path -- a code cave, this kit's ONLY bricking
class (V24, V27, V48B all bricked the ECU). Rejected.

    V69 = V66's control path (gate reverted to the dead gp-0x683c, arm back to stock)
        + rec0/rec1 Y[0..1] scaled x4      <<< OPERATOR INSTRUCTION 2026-08-04, was x2
        + a probe re-aimed at the RATCHET  <<< OPERATOR INSTRUCTION 2026-08-04, was the grind detector

🛑🛑 THE 4x DOSE -- WHAT IT COSTS, STATED UP FRONT AND NOT BURIED
-----------------------------------------------------------------
The surface shape is UNCHANGED: exactly 4.000x to 10 km/h, tapering to EXACTLY 1.000x at and above
50 km/h, on BOTH open axis scales, with no hump anywhere. Only the dose moved. Three consequences,
each of which is worse at 4x than it was at 2x:

  (1) 🛑 THE FLOWN BRACKET IS BROKEN. At 2.000x, GATE 2's magnitude leg was an INTERPOLATION between
      stock (1.00x, shipped) and V62/V65 (2.00x, flown flight-clean). 4.000x is an EXTRAPOLATION to
      twice the largest dose this kit has ever driven. Phase is untouched (no filter, no pole, no
      delay, no `sar` moves), so what survives is: the lane is linear, V65 measured the aggregator
      never railing over 120,049 frames, and grind #1's dose-response was monotone through 2.00x.
  (2) 🛑 SATURATION CROSSES THE RECORD. Peak gain 12288 rails the r24 lane at |dtorque| ~683. The
      repo's recorded max |dtorque| is 839 -- so the margin is 0.81x, i.e. the lane CAN rail in
      ordinary driving, where at 2x (peak 6144, rails at 1366) it could not. Against the 511
      measured directly on the two V68 routes the margin is 1.34x, and the 28 Hz lane-change burst
      itself is only 254 counts. ⚠ Every |dtorque| figure in this kit is a LOWER BOUND (CAN's 50 Hz
      Nyquist hides content the finite difference is still rising through). Consequence: during the
      largest low-speed transients the damping lane goes from linear to a hard rail, which is a
      describing-function regime the 2x design deliberately stayed out of.
  (3) ⚠ MANUAL CREEP GETS 4.000x on the pessimistic axis scale (it got 2.000x at 2x, which was
      exactly the dose V62/V65 flew). Manual highway is still byte-identical to stock.

The FOLD step at rateKey >= 13001 (2759 deg/s, fault-level, not reachable in ordinary driving)
widens from 2.00x -> 4.00x (at 2x) to 2.00x -> 8.00x. Bounded and unreachable; recorded, not hidden.

★ THE HIGHWAY 1.000x IS STRUCTURAL, NOT TUNED. The lane-change point is 93.35 km/h = 5980 counts,
inside the cross-axis [3200, 6400] segment, so the interpolation there reads ONLY rec2 and rec3.
**Any edit confined to rec0/rec1 is exactly 1.000x at every speed >= 50 km/h, every rate, on every
axis scale.** It cannot drift with a re-tune. Asserted below by sweep, not by argument.

★ AND IT DOES NOT BET ON THE OPEN AXIS SCALE. The inner axis's counts-per-deg/s is [OPEN] (repo
runs 4.7121; the chain-direct alternative is 0.58901). V69 scales the WHOLE flat [0,400] segment
instead of leaning on where a breakpoint falls, so its creep dose is 4.000x on BOTH scales.
"Design A" (`0xD2ABC` alone -> 7051) swings 2.00x -> 1.22x at grind #1 and is a bet on one scale;
it also peaks at **2.753x** at 10 km/h / 86 deg/s, and delivers only 1.1-1.5x at |rate| 16-32 deg/s
where V62's measured fix was LARGEST. Rejected on all three counts.
⚠ The price of scale-independence, stated: grind #1 and manual creep share the same speed cells, so
on scale B nothing separates them and manual creep is also 4.000x.

🛑🛑 THE EDIT-ORDER INVARIANT -- this one can make the car WORSE THAN STOCK.
Edits 1 and 2 are jointly safe and individually dangerous in one direction: writing
`0xC6446 = 512` while the gate stays repointed leaves the arm LIVE at 512, which is ~5x BELOW the
stock LERP, degrading engaged steering everywhere. Asserted as `arm == 512 => gate byte == 0xc5`.

🛑 THE NEIGHBOUR TRAP. Modes 10/11/12 interleave at stride 0x14 and **mode 11's and mode 12's
0 km/h records are BYTE-IDENTICAL to mode 10's**, with their 10 km/h records one count below. The
target byte pattern occurs THREE times within 40 bytes. Every cell here is addressed absolutely and
the neighbours are asserted unchanged; `verify/diff_build_vs_stock.py` is span-based and would NOT catch a
stray hit.

Usage:  python builds/v50_v79/build_v69_tva.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import hashlib
import os
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v54_tva as V54                # noqa: E402  (andi / or_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldh / sar / cmp_imm5 encoders)
import build_v57_tva as V57                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the two-decoder scan)
import build_v65_tva as V65                # noqa: E402  (the SIGNED-halfword ladder, flown)
import build_v66_tva as V66                # noqa: E402
import build_v67_tva as V67                # noqa: E402
import build_v68_tva as V68                # noqa: E402  (cave machinery + census helpers)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                               # noqa: E402

START, END = V68.START, V68.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
MAIN_BLOCK, CAL_BLOCK = V68.MAIN_BLOCK, V68.CAL_BLOCK
D2000_BLOCK = V68.D2000_BLOCK              # (0xD2000, 0xD2010) -- V60's falsified cells, must not move

# ---- the control-path reverts ------------------------------------------------------------------
REPOINT_ADDR = V67.REPOINT_ADDR            # 0x3AA94  ld.bu -0x????[gp],r15
REPOINT_BYTE = V67.REPOINT_BYTE            # 0x3AA96  the one byte V67 moved
GATE_V68, GATE_STOCK = 0xFB, 0xC5          # gp-0x6806 (live)  vs  gp-0x683c (DEAD, 0 writers)
ARM_ADDR = V67.ARM_ADDR                    # 0xC6446
ARM_V68, ARM_STOCK = 5244, 512

# ---- the surface edit: rec0 and rec1, Y[0] and Y[1], each EXACTLY QUADRUPLED --------------------
# Y lives at record+0x0A (count @+0x00, X @+0x02) -- from the firmware's own accessor arithmetic.
# 🛑 OPERATOR INSTRUCTION 2026-08-04: scale the surface dose 2x -> 4x. SCALE is the ONE number that
# sets the dose; every derived assert below reads it rather than hard-coding a multiple.
SCALE = 4
REC0, REC1 = 0xD2A74, 0xD2AB0              # 0 km/h and 10 km/h, mode 10
SURFACE = (
    (REC0 + 0x0A, 3072, 3072 * SCALE, "rec0 (0 km/h)  Y[0]"),
    (REC0 + 0x0C, 3072, 3072 * SCALE, "rec0 (0 km/h)  Y[1]"),
    (REC1 + 0x0A, 2561, 2561 * SCALE, "rec1 (10 km/h) Y[0]"),
    (REC1 + 0x0C, 2561, 2561 * SCALE, "rec1 (10 km/h) Y[1]"),
)
# Records that MUST NOT move. mode 11/12 rec0 are byte-identical to mode 10's -- the neighbour trap.
NEIGHBOURS = (0xD2A88, 0xD2A9C, 0xD2AC4, 0xD2AD8, 0xD2B00, 0xD2B14, 0xD2B3C, 0xD2B50)
UNTOUCHED_RECS = (0xD2AEC, 0xD2B28)        # mode-10 50 and 100 km/h -- the structural highway 1.000x

CROSS_X_ADDR = 0xC6010                     # (0, 640, 3200, 6400) counts, 64.0625 counts/km/h

# =====================================================================================================
# THE PROBE -- RE-AIMED AT THE RATCHET.  Operator instruction, 2026-08-04.
# =====================================================================================================
# V68/V69-as-specced spent bits 5 and 4 on Honda's 1 kHz OSCILLATION DETECTOR (gp-0x67df FSM,
# gp-0x671a reversal counter) -- i.e. on the GRINDS. That instrument is now exhausted in the only way
# that matters: the FSM cell has NEVER been observed non-zero in this kit (0/53,991 frames on V68,
# 0/186,321 on V67, straight through the captured 28 Hz burst), and with no positive control the null
# is uninterpretable. Re-aiming costs nothing and the ratchet is the one symptom this channel can
# actually RESOLVE: it is ~7.4-7.6 Hz, so a 100 Hz probe gets ~13.5 samples per cycle and each bit's
# own TIME SERIES carries the line. At 21 Hz (grind #1) and 43 Hz (grind #2) it never could.
#
# WHAT THE RATCHET IS, from the record (docs/STATE.md):
#   ~7.4-7.6 Hz, within-run sd 0.07-0.10 Hz, Q ~= 36, prominence median 783x (max 2142x); creep;
#   ENGAGED; hands-off; both 9-15 deg and 133 deg. NOT the V42 state-4 governor (`ST == 4` fires
#   0/37,922). Waveform SYMMETRIC on every build (skew -0.16..+0.06 vs a -3.27 sawtooth calibration)
#   ==> an AMPLITUDE-SATURATED RESONANCE, pointing at damping / loop gain. Mechanism UNKNOWN, no cal
#   lever, and STATE step 7 says in terms: "Next step is MEASUREMENT, not a build."
#
# ==> THE PROBE HUNTS HARD NONLINEARITIES IN THE AGGREGATOR, because "symmetric + amplitude-saturated"
# is the describing-function signature of one. FUN_0003aa2c's complete list, re-read from the
# decompile this session (every lane is a SIGNED halfword, `ld.h`/`st.h`):
#
#   ZERO-type range gates -- out-of-window contributes 0, NOT clipped. A crossing is a step, not a
#   soft limit, and that is the strongest limit-cycle generator in the chain:
#       gp-0x6b62 +/-0x2000 (return-centre)  gp-0x6b4c +/-0x2800 (LKAS)   gp-0x6ade +/-0x400 (DEAD)
#       gp-0x6ad4 +/-0x2800 (residual)       gp-0x6b26 +/-0x400 (friction) gp-0x6bbe +/-0x800 (boost)
#       gp-0x6bd0 +/-0x800 (damping)         gp-0x6b86 +/-0x3000 (magnitude)
#   SATURATING clips: r24 and r26 each +/-0x2000, summed ungated.
#   Output clamp +/-0x2800 on gp-0x6b94 -- 🛑 ALREADY MEASURED AND NULL. V65's 4-level ladder,
#       120,049 frames: +RAIL 0 / -RAIL 0, only 54 frames past +/-4096. So the ratchet is NOT
#       amplitude-saturated AT THE SUM. What that null does NOT cover is every lane's OWN
#       nonlinearity upstream of the sum -- and those have never been measured. That is this probe.
#
# 🛑 THE BUDGET IS THREE RUNGS, and that is arithmetic, not preference. The proven cave extent is
# 68 B (flown 8x: V55/V57/V58/V59/V64/V65/V66/V67); prologue 4 + epilogue 20 = 24 leaves 44 B, and a
# signed-halfword rung is 14 B (ld.h 4 + sar 2 + cmp 2 + blt 2 + movea 4). 3 x 14 = 42 <= 44; a
# fourth needs 56. Growing the cave is the ONLY bricking class this kit has (V24/V27/V48B). NO.
#
# ⇒ bit6 IS FREED FROM THE LKAS GATE to buy the third ratchet rung. Justified, not assumed:
# `gp-0x6806` agreed with openpilot's `carControl.latActive` in 150,302/150,327 = 99.983% of frames
# (the 25 disagreements are single-frame transition edges), `0x18F` b4 bit3 and `0xE4` byte2 bit7
# agree 99.94-100%, and V69 REVERTS the gate at 0x3AA96 so `gp-0x6806` no longer steers anything on
# this build -- bit6 was a pure covariate, and three external channels already carry it.
#
# THE PAYLOAD -- 0x14A byte4 bits 7:3
#   bit7 = 1                   LIVENESS. field == 0 => the cave did not fire => the reading is VOID.
#   bit6 = gp-0x6ada >= +4096  *** r24's LANE OUTPUT, after its own +/-0x2000 saturating clip. ***
#                              This is the lane V69 scales, the damping/torque-rate lane the record
#                              points at, and Honda mirrors it to RAM every 1 kHz tick at 0x3AD5A.
#                              🛑 0 READERS / 1 WRITER image-wide => reading it is blast-radius-free
#                              in the strongest sense available: nothing consumes it at all.
#                              +4096 is HALF ITS RAIL, so the duty of this bit is a direct
#                              rail-proximity meter -- and it is also how the 4x dose gets priced
#                              on-car (see the SATURATION note above: 4x rails at |dtorque| ~683).
#   bit5 = gp-0x6b62 >= +4096  *** THE OPERATOR'S OWN RATCHET HYPOTHESIS, never probed in 69 builds.
#                              The return-to-centre lane: FUN_00036388, a slow +/-1/tick accumulator
#                              WITH HYSTERESIS, into a +/-0x2000 ZERO gate. +4096 is half that gate.
#   bit4 = gp-0x6ad4 >= +4096  *** the UNFILTERED residual / resonance lane (FUN_0003a382: two
#                              passthroughs and a RAW derivative on the physical torque sensor,
#                              reaching the aggregator directly), into a +/-0x2800 ZERO gate. Its
#                              gain is LERP-indexed by gp-0x671a, the oscillation counter -- so this
#                              lane closes a loop from Honda's own detector back into assist. It is
#                              also live HANDS-OFF, which the boost lane (driver-torque indexed) is
#                              not, and the ratchet is a hands-off symptom.
#   bit3 = 0                   V69 BUILD-CLASS MARKER. V68 emits bit3 = 1 in 100.000% of 53,991
#                              frames, so bit3 = 0 excludes V68 ABSOLUTELY -- and V68 is what is on
#                              the car now, which is the discrimination that matters.
#                              ⚠ RESIDUAL, STATED: V66/V67 also emit bit3 = 0 with bits 5:4 measured
#                              0 over 186,321 frames, so V69-vs-V66/V67 is not structural -- it rests
#                              on bits 5:4 ever firing, plus the flashed .rwd filename. Two builds
#                              back; accepted, not hidden.
#   bits 2:0                   stock STEER_SENSOR_STATUS, preserved.
#
# ⚠ WHAT WAS CONSIDERED AND NOT TAKEN, so the next session does not re-propose it:
#   gp-0x6bbe (boost, +/-0x800 -- the NARROWEST gate on a live lane) is indexed on DRIVER TORQUE, and
#     the ratchet is hands-off => it sits far from its gate exactly when the symptom occurs.
#   gp-0x6bd0 (damping, +/-0x800): the record has f5 = 0 at both operating points, so it likely reads
#     0 -- but that is a STATIC claim and probing it would test a closed branch. First cut if a rung
#     frees up.
#   gp-0x6b4c (LKAS lane) is the post-mixer command, already visible on CAN 0xE4. Redundant.
#   gp-0x4f62 (dtorque, r24's INPUT) -- the "probe the input too" lesson. Rung 4 if the cave ever grows.
#
# 🛑 ONE-SIDED, AND THAT IS A REAL RESIDUAL. Each rung tests the POSITIVE side only; a two-sided test
# costs 8 more bytes per rung and does not fit. For a SYMMETRIC limit cycle the positive half-cycles
# alone still put the 7.4 Hz line in the bit's own spectrum, which is the measurement. But a rung
# reading 0 bounds only that lane's POSITIVE excursions. Do not quote a null as two-sided.
# ⚠ And the sampling residual V68 recorded stands: the cave samples at the 100 Hz TX hook while the
# aggregator runs at 1 kHz, so a sample can be one tick stale relative to the lane evaluation.
# Immaterial for duty and for a 7.4 Hz line; do NOT use these bits for a per-tick correlation.
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP        # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK          # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT

BIT_LIVE = 0x80
BIT_R24_OUT, BIT_RETURN_CENTRE, BIT_RESIDUAL = 0x40, 0x20, 0x10
BIT_CLASS = 0x08                           # bit3: CONSTANT 0 on V69 (V68 emits it CONSTANT 1)
LIVE_IMM = BIT_LIVE                        # 0x80 -- one movea, zero extra bytes

# 🛑 sar is ARITHMETIC: for k >= 0, (x >> SHIFT) >= k  <=>  x >= k << SHIFT, INCLUDING negative x
# (which shift to a negative quotient and fail the test). shr would map every negative lane value to
# a huge positive one and fire the bit on the wrong half-cycle. Asserted by an exhaustive wire model.
SHIFT, LEVEL = 12, 1                       # sar 0xc + cmp 0x1
THRESHOLD = LEVEL << SHIFT                 # = +4096
COND_BLT = 0x6                             # SIGNED <. 🛑 bl (0x1) is the UNSIGNED twin and inverts

# (gp displacement, bit, name, that lane's OWN hard nonlinearity, what a 1 means)
RUNGS = (
    (0x6ADA, BIT_R24_OUT, "r24_out_6ada", 0x2000,
     "r24 torque-rate/damping lane output is in the top half of its +/-0x2000 saturating clip"),
    (0x6B62, BIT_RETURN_CENTRE, "return_centre_6b62", 0x2000,
     "the return-to-centre lane is at half its +/-0x2000 ZERO gate"),
    (0x6AD4, BIT_RESIDUAL, "residual_6ad4", 0x2800,
     "the unfiltered residual/resonance lane is at 40% of its +/-0x2800 ZERO gate"),
)

# Re-derived from raw bytes on the V68 source this session, by V64's two-decoder census.
# (firmware readers, firmware writers, writer addresses, permitted mnemonics, the consumer that
#  proves the probe reads the cell the CONTROL PATH uses -- None where the cell has no consumer.)
PROBE_CENSUS = {
    0x6ADA: (0, 1, [0x3AD5A], {"st.h"}, None),          # a pure mirror: NOTHING reads it
    0x6B62: (8, 3, [0x36514, 0x3652C, 0x36544], {"ld.h", "st.h"}, 0x3AA38),
    0x6AD4: (1, 1, [0x3A8A0], {"ld.h", "st.h"}, 0x3ACA8),
}
# `ld.h -0x6ad4[gp],r6` is BYTE-IDENTICAL to the aggregator's own read @0x3ACA8; gp-0x6b62 has eight
# real `ld.h -0x6b62[gp],rN` differing from ours ONLY in the reg2 field. gp-0x6ada has no `ld.h`
# anywhere -- its hw2 (the displacement) is byte-identical to the real `st.h` @0x3AD5A and every hw1
# FIELD is pinned by the two byte-identical `ld.h ...,r6` donors below.
PIN_LDH_6AD4 = (0x3ACA8, bytes.fromhex("24372c95"))     # BYTE-IDENTICAL to what we emit
PIN_LDH_6B94 = (0x453E0, bytes.fromhex("24376c94"))     # V65's donor: ld.h ...,r6, different cell
PIN_STH_6ADA = (0x3AD5A, bytes.fromhex("64c72695"))     # 🛑 opcode 0x3B -- ONE BIT from our 0x39

TAG = ("LKAS-4x-mss0-decouple0xC646C-ratelane-SPEEDSHAPED-gateREVERTED-"
       "gainB-rec0rec1-x4-ratchetprobe-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V69-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v69_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def rec_of(buf, addr):
    return (list(struct.unpack_from("<4H", buf, addr + 0x02)),
            list(struct.unpack_from("<4H", buf, addr + 0x0A)))


# ---- the LERP, mirroring the decompiled integer arithmetic --------------------------------------
def _lerp(x, xs, ys):
    """FUN_0003ad74 / the inline LERP at 0x3ABB2-0x3ABF8. FLAT outside; `divq` truncates to zero."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if x < xs[i + 1]:
            num = (ys[i + 1] - ys[i]) * (x - xs[i])
            q = abs(num) // (xs[i + 1] - xs[i])
            return ys[i] + (q if num >= 0 else -q)
    return ys[-1]


def gain_q10(buf, speed_counts, axis_counts):
    recs = [rec_of(buf, a) for a in (REC0, REC1, 0xD2AEC, 0xD2B28)]
    cross = list(struct.unpack_from("<4h", buf, CROSS_X_ADDR))
    k = max(cross[0], min(speed_counts, cross[-1]))
    xs = [_lerp(k, cross, [recs[i][0][j] for i in range(4)]) for j in range(4)]
    ys = [_lerp(k, cross, [recs[i][1][j] for i in range(4)]) for j in range(4)]
    idx = axis_counts if 0 <= axis_counts < 13001 else 0     # the fold @0x3AAC8/0x3AACC
    return _lerp(idx, xs, ys)


def _s16(x):
    """Interpret a 16-bit pattern the way `ld.h` does -- SIGNED."""
    return x - 0x10000 if x & 0x8000 else x


def _wire_model():
    """What the emitted rung computes, over ALL 65,536 halfword patterns -- not on a sample.

    The rung is:  r6 = sign_extend(cell) ; r6 = r6 sar SHIFT ; cmp LEVEL,r6 ; blt +6 ; set bit
    so the bit is set iff (x >> SHIFT) >= LEVEL, and the claim is that this is exactly x >= THRESHOLD.
    """
    for raw in range(0x10000):
        x = _s16(raw)
        got = (x >> SHIFT) >= LEVEL          # Python >> on a negative int floors, exactly like `sar`
        assert got == (x >= THRESHOLD), \
            f"the rung is not `>= {THRESHOLD}` at x = {x}: sar/cmp says {got}"
    # 🛑 and the UNSIGNED failure mode, spelled out rather than trusted: an `ld.hu` or an `shr` would
    # turn every negative lane value into a large positive one and fire the bit on the WRONG
    # half-cycle of a symmetric limit cycle -- i.e. it would still look plausible on the wire.
    assert ((-1 & 0xFFFF) >> SHIFT) >= LEVEL, "the unsigned reading of -1 does NOT fire -- re-derive"
    assert not ((-1 >> SHIFT) >= LEVEL), "the signed reading of -1 fires -- the model is wrong"


def _self_check_encoders():
    """Every halfword we emit is pinned to a real instruction in the image, or to a self-checked
    ancestor encoder. 🛑 Caves are this kit's ONLY bricking class."""
    V65._self_check_encoders()               # chains down through V59/V58/V57/V55/V54/FF
    src = Path(plain_image_path("_v68_plain_image.bin")).read_bytes()

    for addr, raw in (PIN_LDH_6AD4, PIN_LDH_6B94, PIN_STH_6ADA):
        assert bytes(src[addr:addr + 4]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the V68 image -- re-pin before building"

    ours_6ad4 = V55.ldh(0x6AD4, R6)
    assert ours_6ad4 == PIN_LDH_6AD4[1], \
        "ld.h -0x6ad4[gp],r6 is not byte-identical to the aggregator's own read @0x3ACA8"

    for disp, _bit, name, _win, _why in RUNGS:
        ours = V55.ldh(disp, R6)
        hw1 = struct.unpack_from("<H", ours, 0)[0]
        hw2 = struct.unpack_from("<H", ours, 2)[0]
        # 🛑🛑 THE ONE-BIT TRAP, AND IT IS NOT HYPOTHETICAL HERE. `ld.h` is opcode 0x39 and `st.h` is
        # 0x3B -- and gp-0x6ada's ONLY real instance @0x3AD5A *is* the st.h form, carrying the very
        # same displacement halfword we emit. A single bit turns this READ into a WRITE into the
        # aggregator's lanes, in the 1 kHz control path.
        assert ((hw1 >> 5) & 0x3F) == 0x39, \
            f"{name}: emitted opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x39 (ld.h)"
        assert ours != FF.sth(R6, -disp, GP) and ours[:2] != FF.sth(R6, -disp, GP)[:2], \
            f"{name}: the emitted load shares an opcode field with `st.h` -- that would WRITE the lane"
        assert ours != FF.ldhu(disp, R6), \
            f"{name}: ld.h collapsed onto ld.hu -- the lane's SIGN would be lost"
        assert hw1 & 0x1F == GP == 4, f"{name}: reg1 field is not r4 (gp)"
        assert (hw1 >> 11) == R6, f"{name}: reg2 field is not r6"
        assert hw2 & 1 == 0, f"{name}: ld.h hw2 LSB must be CLEAR (LSB set is the ld.w/ld.hu form)"
        assert hw2 == (0x10000 - disp) & 0xFFFF, f"{name}: displacement is not -0x{disp:04x}"
        # every hw1 FIELD pinned by a byte-identical real `ld.h ...,r6`; only the displacement (DATA,
        # not an encoding field) is ours -- and for two of the three even that is byte-identical.
        assert hw1 == struct.unpack_from("<H", PIN_LDH_6AD4[1], 0)[0] == \
            struct.unpack_from("<H", PIN_LDH_6B94[1], 0)[0], \
            f"{name}: hw1 differs from BOTH real `ld.h ...,r6` donors"
    assert struct.unpack_from("<H", PIN_STH_6ADA[1], 2)[0] == \
        struct.unpack_from("<H", V55.ldh(0x6ADA, R6), 2)[0], \
        "gp-0x6ada's displacement halfword does not match its real st.h @0x3AD5A"

    assert V55.sar(SHIFT, R6) == bytes.fromhex("ac32"), "sar 0xc,r6 (@0x2C0BA) encoding changed"
    assert V55.sar(SHIFT, R6) != FF.shr(SHIFT, R6), "sar collapsed onto shr -- the sign would be lost"
    assert V55.cmp_imm5(LEVEL, R6) == bytes.fromhex("6132"), "cmp 0x1,r6 (@0x14D46) encoding changed"
    assert FF.bcond(COND_BLT, +6) == bytes.fromhex("b605"), "blt +6 (@0x1C006) encoding changed"
    assert COND_BLT != V55.COND_BL, "blt collapsed onto the UNSIGNED bl"
    assert FF.movea(LIVE_IMM, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"

    bits = (BIT_LIVE,) + tuple(b for _, b, _, _, _ in RUNGS) + (BIT_CLASS,)
    assert len(set(bits)) == 5 and all(b & (b - 1) == 0 for b in bits), "probe bits are not distinct"
    assert sum(bits) == 0xF8, f"probe bits must occupy exactly 7:3, got 0x{sum(bits):02X}"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"
    assert LIVE_IMM & BIT_CLASS == 0, "bit3 must be CLEAR -- that IS V69's build class"
    assert V68.LIVE_IMM & BIT_CLASS != 0, "V68 no longer sets bit3 -- the V68/V69 discriminator is gone"
    _wire_model()


def build_cave():
    """pack_ratchet_lane_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80   bit7 LIVENESS, bit3 CLEAR = the V69 build class
        ld.h  -0x6ada[gp],r6   ; r24's lane output, post +/-0x2000 clip   (0 readers image-wide)
        sar   0xc,r6           ; ARITHMETIC: units of 4096, sign preserved
        cmp   0x1,r6
        blt   +6
        movea 0x40,r7,r7       ; bit6 = gp-0x6ada >= +4096
      g0:
        ld.h  -0x6b62[gp],r6   ; the return-to-centre lane  (the operator's own hypothesis)
        sar   0xc,r6
        cmp   0x1,r6
        blt   +6
        movea 0x20,r7,r7       ; bit5 = gp-0x6b62 >= +4096
      g1:
        ld.h  -0x6ad4[gp],r6   ; the unfiltered residual / resonance lane
        sar   0xc,r6
        cmp   0x1,r6
        blt   +6
        movea 0x10,r7,r7       ; bit4 = gp-0x6ad4 >= +4096
      g2:
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    _self_check_encoders()
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(LIVE_IMM, R0, R7), "movea 0x80,r0,r7    ; bit7 LIVENESS, bit3 CLEAR = V69 class")

    rungs = []
    for disp, bit, name, _win, _why in RUNGS:
        load_idx = len(listing)
        emit(V55.ldh(disp, R6), f"ld.h -0x{disp:04x}[gp],r6  ; {name} (SIGNED)")
        emit(V55.sar(SHIFT, R6), f"sar 0x{SHIFT:x},r6           ; ARITHMETIC -- units of {1 << SHIFT}")
        emit(V55.cmp_imm5(LEVEL, R6), f"cmp 0x{LEVEL:x},r6           ; signed compare")
        br_idx = len(listing)
        emit(FF.bcond(COND_BLT, +6), f"blt +6              ; skip -> {name}")
        emit(FF.movea(bit, R7, R7),
             f"movea 0x{bit:x},r7,r7   ; bit{bit.bit_length() - 1} = gp-0x{disp:04x} >= +{THRESHOLD}")
        rungs.append((load_idx, br_idx, CAVE_BASE + len(body), name, disp, bit))

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # ---- GATE 2a: every branch lands exactly on its label, located BY POSITION. The three rungs are
    # byte-identical apart from the displacement and the bit, so a content lookup is ambiguous.
    assert [r[1] for r in rungs] == [4, 9, 14], f"rung branch indices drifted: {[r[1] for r in rungs]}"
    for load_idx, br_idx, label, name, disp, _bit in rungs:
        addr, raw, _ = listing[br_idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{br_idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"
        assert struct.unpack("<H", raw)[0] & 0xF == COND_BLT, \
            f"{name}: branch condition is not blt (SIGNED <) -- bl would invert every negative sample"
        assert listing[load_idx][1] == V55.ldh(disp, R6), f"{name}: wrong cell loaded"
        assert listing[load_idx + 1][1] == V55.sar(SHIFT, R6), f"{name}: the shift is not `sar 0xc,r6`"
        assert listing[load_idx + 2][1] == V55.cmp_imm5(LEVEL, R6), f"{name}: cmp is not `0x1,r6`"
        assert br_idx - load_idx == 3, f"{name}: rung shape drifted"

    # ---- GATE 2b: r6/r7 LIVENESS. Only a rung's own load and shift may write r6; everything else
    # writes r7. `cmp` sets flags only. Nothing else may be touched at all.
    load_addrs = {listing[r[0]][0] for r in rungs} | {listing[r[0] + 1][0] for r in rungs}
    for idx in range(1, rungs[-1][1] + 2):
        addr, raw, text = listing[idx]
        if len(raw) == 2 and raw[1] == 0x05:
            continue                                          # a Bcond writes no GPR
        hw = struct.unpack_from("<H", raw, 0)[0]
        if ((hw >> 5) & 0x3F) in (0x13, 0x0F):                # cmp imm5,reg2 / cmp reg1,reg2
            continue
        want = R6 if addr in load_addrs else R7
        assert (hw >> 11) == want, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{want}"
    for disp, _bit, name, _w, _y in RUNGS:
        assert sum(1 for _, r, _ in listing if r == V55.ldh(disp, R6)) == 1, \
            f"{name}: gp-0x{disp:04x} is loaded more than once"

    # ---- GATE 1 restated as a property of the EMITTED CODE: exactly ONE store, the payload byte.
    store_idx = [i for i, (_, raw, _) in enumerate(listing)
                 if len(raw) >= 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert store_idx == [19], f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[19][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "the sole store is not the payload byte"
    for idx, (_, raw, text) in enumerate(listing):
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- geometry -----------------------------------------------------------------------------
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == 4 + 14 * len(RUNGS) + 20 == 66, f"the cave is {len(body)}B, the budget says 66"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"cave {len(body)}B overruns the PROVEN {len(V55.CAVE_BYTES)}B extent -- caves brick ECUs"
    return bytes(body), listing


def assert_probe_census(buf, cave_span):
    """Re-derive each probed cell's reader/writer set from RAW BYTES and assert it exactly.

    🛑 Python, not `search_instructions` -- that tool counts only already-analysed instructions and
    reports truncated:false while undercounting. It has produced wrong reader/writer sets four times.
    ⚠ GATE 1 restated as a MEASUREMENT: the cave READS each cell exactly once and WRITES it nowhere.
    """
    read_mnem = {"ld.b", "ld.h", "ld.w", "ld.bu", "ld.hu"}
    for disp, (n_read, n_write, writers, mnems, consumer) in PROBE_CENSUS.items():
        hits = V64.gp_access_census(buf, disp)
        assert all(m in mnems | {"ld.h"} for _, m, _ in hits), \
            f"gp-0x{disp:04x} has an access outside {sorted(mnems)} -- wrong WIDTH or SIGN"
        fw = [h for h in hits if h[0] not in cave_span]
        reads = [h for h in fw if h[1] in read_mnem]
        writes = [h for h in fw if h[1] not in read_mnem]
        assert len(reads) == n_read, \
            f"gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}: " \
            f"{[hex(a) for a, _, _ in reads]}"
        assert [a for a, _, _ in writes] == writers, \
            f"gp-0x{disp:04x} writers are {[hex(a) for a, _, _ in writes]}, expected " \
            f"{[hex(w) for w in writers]}"
        assert len(writes) == n_write, f"gp-0x{disp:04x} has {len(writes)} writers, expected {n_write}"
        if consumer is not None:
            assert any(a == consumer for a, _, _ in reads), \
                f"0x{consumer:05X} no longer reads gp-0x{disp:04x} -- the cell the probe reports on " \
                "is not the one the CONTROL PATH uses"
        cave = [h for h in hits if h[0] in cave_span]
        assert len(cave) == 1 and cave[0][1] == "ld.h" and cave[0][2] == R6, \
            f"gp-0x{disp:04x}: cave accesses are {[(hex(a), m, r) for a, m, r in cave]}, expected " \
            "exactly one `ld.h ...,r6`"
    # 🛑 gp-0x6ada is the strongest GATE-1 statement available anywhere in this chain: it has ZERO
    # firmware readers, so the probe cannot perturb anything even in principle.
    assert PROBE_CENSUS[0x6ADA][0] == 0, "gp-0x6ada acquired a reader -- it is no longer a free mirror"


DECODER = os.path.join(HERE, "..", "rlog-tools", "probe/decode_v69_ratchet.py")


def assert_decoder_matches(cave_bytes, label="V69"):
    """🛑 The decoder's header must match the BUILT image, not a previous revision.

    V66's decoder header was stale for one revision and claimed bit4 = gp-0x683c when the image read
    gp-0x67fe. A probe whose decoder disagrees with its cave produces a confident WRONG reading, and
    that is worse than no probe -- so this is a BUILD-time assertion, not a reminder.
    """
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, f"{label}: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"{label}: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   " \
        f"{cave_bytes.hex()}"
    for disp, bit, _name, _win, _why in RUNGS:
        assert f"gp-0x{disp:04x}" in txt, \
            f"{label}: the decoder never mentions gp-0x{disp:04x} (bit{bit.bit_length() - 1})"
    # the decoder must also carry the THRESHOLD and the artifact name, or a reader cannot tell which
    # build's semantics it is applying.
    for token in (str(THRESHOLD), "0xC4124", os.path.basename(OUT)):
        assert token in txt, f"{label}: the decoder does not carry '{token}'"
    # 🛑 and it must NOT still be describing the retired grind-detector rungs as live.
    for stale in ("bit5 gp-0x67df", "bit4 gp-0x671a"):
        assert stale not in txt, \
            f"{label}: the decoder still calls '{stale}' a live rung -- it was retired by V69"
    return True


def build():
    print(__doc__)
    src = Path(plain_image_path("_v68_plain_image.bin"))
    v68 = bytearray(src.read_bytes())
    print("=" * 102)
    print(f"SOURCE: {src}\n  SHA256 {hashlib.sha256(bytes(v68)).hexdigest()}")

    # ---- gate the SOURCE before touching it -----------------------------------------------------
    assert len(v68) == 0x100000, "source image is not 1 MiB"
    assert v68[REPOINT_BYTE] == GATE_V68, \
        f"source gate byte is 0x{v68[REPOINT_BYTE]:02X}, expected V68's 0x{GATE_V68:02X}"
    assert u16(v68, ARM_ADDR) == ARM_V68, f"source arm is {u16(v68, ARM_ADDR)}, expected {ARM_V68}"
    for addr, old, _new, name in SURFACE:
        assert u16(v68, addr) == old, f"{name} @0x{addr:05X} is {u16(v68, addr)}, expected {old}"
    role = list(v68[0xC4124:0xC4124 + 11])
    assert role == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0], f"role table drifted: {role}"
    assert not any(r in (6, 7) for r in role), \
        "a slot carries role 6 or 7 -- gp-0x67ac becomes LIVE and the rate lanes can drop out"
    assert bytes(v68[0xC6564:0xC6564 + 40]) == bytes(40), \
        "0xC6564 is no longer 40 zero bytes -- r26 may no longer be inert"
    print("  source gates: gate byte 0xFB, arm 5244, surface stock, role table "
          f"{role}, 0xC6564 = 40 zero bytes  ✅")

    code = bytearray(v68)

    # ---- EDIT 1+2: the control path reverts to V66's --------------------------------------------
    print("\n  EDIT 1-2 -- THE CONTROL PATH REVERTS (this is what lets speed shaping reach the "
          "engaged lane):")
    code[REPOINT_BYTE] = GATE_STOCK
    struct.pack_into("<H", code, ARM_ADDR, ARM_STOCK)
    print(f"    0x{REPOINT_BYTE:05X}  0x{GATE_V68:02X} -> 0x{GATE_STOCK:02X}   "
          f"ld.bu -0x6806[gp],r15 -> -0x683c   (the DEAD cell: 0 writers image-wide)")
    print(f"    0x{ARM_ADDR:05X}  {ARM_V68} -> {ARM_STOCK}       r24's LKAS arm, back to stock")
    # 🛑🛑 THE EDIT-ORDER INVARIANT. 512 is ~5x BELOW the stock LERP; live, it is worse than stock.
    assert not (u16(code, ARM_ADDR) == ARM_STOCK and code[REPOINT_BYTE] != GATE_STOCK), \
        "arm == 512 while the gate is STILL repointed -- that arm is LIVE and ~5x below the stock " \
        "LERP. Refusing to emit."
    print("    ✅ edit-order invariant asserted: arm == 512 ⟹ gate byte == 0xc5")
    assert bytes(code[REPOINT_ADDR:REPOINT_ADDR + 4]) == bytes.fromhex("847fc597"), \
        "the reverted gate load is not the stock `ld.bu -0x683c[gp],r15`"

    # ---- EDIT 3-6: the surface --------------------------------------------------------------
    print(f"\n  EDIT 3-6 -- THE SURFACE. Every halfword is EXACTLY {SCALE}x the one it replaces:")
    for addr, old, new, name in SURFACE:
        before = struct.pack("<H", old)
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   bytes {before.hex(' ')} -> "
              f"{struct.pack('<H', new).hex(' ')}   {name}")
        assert new == SCALE * old, f"{name} is not an exact {SCALE}x"
        # 🛑 SIGN HEADROOM. The Y row must stay a POSITIVE SIGNED halfword: if the accessor's load
        # is `ld.h` a value >= 0x8000 comes back NEGATIVE and inverts the lane. This assert holds the
        # property regardless of which width the accessor actually uses, so it is safe under either
        # reading. (At SCALE = 4 the peak is 12288 -- 2.7x of headroom.)
        assert 0 < new < 0x8000, f"{name} = {new} is not a positive signed halfword"

    # ---- EDIT 7: the probe, RE-AIMED AT THE RATCHET ------------------------------------------
    print("\n  EDIT 7 -- THE PROBE, RE-AIMED AT THE RATCHET (operator instruction 2026-08-04).")
    print("    Was: bit5/bit4 on Honda's 1 kHz OSCILLATION DETECTOR (gp-0x67df FSM, gp-0x671a")
    print("         reversal counter) -- a cell that has NEVER been observed non-zero in this kit.")
    print("    Now: three SIGNED-halfword rungs on the aggregator's own hard nonlinearities.")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        cave_bytes + b"\xff" * (len(V55.CAVE_BYTES) - len(cave_bytes))
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    print(f"    cave {len(cave_bytes)}B of the proven {len(V55.CAVE_BYTES)}B "
          f"({len(V55.CAVE_BYTES) - len(cave_bytes)} spare)  -- extent UNCHANGED, flown 8x")
    assert code[CAVE_BASE + 2] == LIVE_IMM, "the liveness immediate is not 0x80"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v68[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical"
    print("\n    PAYLOAD -- 0x14A byte4 bits 7:3:")
    print(f"      bit7 = 1                    LIVENESS (field == 0 ⇒ VOID)")
    for disp, bit, name, win, why in RUNGS:
        print(f"      bit{bit.bit_length() - 1} = gp-0x{disp:04x} >= +{THRESHOLD:<5d} {why}")
        print(f"             (that lane's own hard nonlinearity is ±0x{win:04X} = ±{win})")
    print("      bit3 = 0                    V69 BUILD CLASS (V68 emits bit3 = 1, 100% of frames)")
    print("      bits 2:0                    stock STEER_SENSOR_STATUS, preserved")

    # ---- GATE 1, AS A MEASUREMENT: every probed cell READ once by the cave, WRITTEN nowhere ----
    cave_span = range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))
    assert_probe_census(bytes(code), cave_span)
    print("\n    ✅ GATE 1 (RAM ownership) asserted as a MEASUREMENT, from raw bytes, two decoders:")
    for disp, (nr, nw, wr, _m, _c) in PROBE_CENSUS.items():
        print(f"       gp-0x{disp:04x}  {nr}r / {nw}w  writers {[hex(a) for a in wr]}"
              f"{'   ⇐ ZERO readers: a pure mirror, nothing can be perturbed' if nr == 0 else ''}")
    print("       the cave READS each cell exactly once (`ld.h ...,r6`) and WRITES none of them;")
    print("       its only store image-wide is the CAN-330 payload byte itself.")
    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/probe/decode_v69_ratchet.py CAVE_HEX matches the built cave byte-for-byte,")
        print("       names all three probed cells, and no longer describes the retired rungs.")

    # ---- STRUCTURAL GATES ------------------------------------------------------------------
    print("\n  GATES:")
    for a in NEIGHBOURS:
        assert bytes(code[a:a + 20]) == bytes(v68[a:a + 20]), \
            f"neighbour record 0x{a:05X} MOVED -- the byte-pattern trap fired"
    print(f"    ✅ all {len(NEIGHBOURS)} mode-11/12 neighbour records byte-identical "
          "(mode 11/12 rec0 are byte-IDENTICAL to mode 10's -- the pattern occurs 3x in 40 bytes)")
    for a in UNTOUCHED_RECS:
        assert bytes(code[a:a + 20]) == bytes(v68[a:a + 20]), f"mode-10 rec 0x{a:05X} moved"
    print("    ✅ mode-10 50 km/h and 100 km/h records byte-identical ⇒ the highway 1.000x is "
          "STRUCTURAL")
    assert bytes(code[D2000_BLOCK[0]:D2000_BLOCK[1]]) == \
        bytes(v68[D2000_BLOCK[0]:D2000_BLOCK[1]]), "V60's falsified slew-blend cells MOVED"
    print(f"    ✅ 0x{D2000_BLOCK[0]:05X}-0x{D2000_BLOCK[1]:05X} (V60's falsified cells) unchanged")
    assert u16(code, V57.PRIVATE_ADDR) == u16(v68, V57.PRIVATE_ADDR), "V57's private cell moved"
    for a, want in V68.SAR_SITES_STOCK:
        assert u16(code, a) == want, f"sar site 0x{a:05X} is not stock"
    print("    ✅ all three `sar` sites stock; V57's private gain cell carried")

    # ---- THE STRUCTURAL HIGHWAY CLAIM, PROVEN BY SWEEP -------------------------------------
    bad = [(v, r) for v in range(3200, 6401, 32) for r in range(0, 3001, 25)
           if gain_q10(code, v, r) != gain_q10(v68, v, r)]
    assert not bad, f"the surface edit changed a >=50 km/h operating point: {bad[:4]}"
    print(f"    ✅ SWEEP: {len(range(3200, 6401, 32)) * len(range(0, 3001, 25))} points at "
          "speed >= 50 km/h are byte-identical to stock ⇒ highway is EXACTLY 1.000x, all rates")

    # ---- THE DELIVERED MULTIPLIER ---------------------------------------------------------
    print("\n  DELIVERED MULTIPLIER (V69 vs stock LERP), low rate axis:")
    print("      km/h  " + "".join(f"{k:>8}" for k in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93)))
    row = []
    for kmh in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93):
        sc = int(kmh * 64.0625)
        row.append(gain_q10(code, sc, 100) / gain_q10(v68, sc, 100))
    print("      mult  " + "".join(f"{x:8.3f}" for x in row))
    mx = max(gain_q10(code, v, r) / gain_q10(v68, v, r)
             for v in range(0, 6401, 64) for r in range(0, 3001, 25))
    assert mx <= SCALE + 0.001, \
        f"the surface exceeds {SCALE}.000x somewhere ({mx:.3f}) -- the dose is not what was specified"
    print(f"    ✅ MAX multiplier anywhere = {mx:.3f}x, reached only at <= 10 km/h")
    # 🛑🛑 THE BRACKET IS BROKEN AT SCALE = 4, AND IT IS NOT HIDDEN. V69-as-specced (2.000x) sat
    # inside [stock 1.00x, V62/V65 2.00x], both flown flight-clean, so GATE 2's magnitude leg was an
    # INTERPOLATION between two measured points. At 4.000x it is an EXTRAPOLATION to 2x beyond the
    # largest dose this kit has ever driven. Phase is still untouched (no filter, no pole, no delay,
    # no `sar`), so the argument that survives is: the lane is linear, the aggregator was measured
    # never to rail (V65, 120,049 frames), and grind #1's dose-response was monotone through 2.00x.
    if mx > 2.001:
        print(f"    🛑 GATE 2 MAGNITUDE: {mx:.3f}x is OUTSIDE the flown bracket "
              "[stock 1.00x, V62/V65 2.00x]. Extrapolation, not interpolation -- by operator "
              "instruction 2026-08-04. See docs/specs/design/V69-DESIGN.md §5.2.")
    # 🛑 SATURATION -- the one metric that gets WORSE with dose, and at 4x it crosses the record.
    # r24 clamps at |dtorque| >= LANE_CLAMP*1024/gain (8192*1024/gain), through the real lane.
    peak = max(gain_q10(code, v, r) for v in range(0, 6401, 64) for r in range(0, 3001, 25))
    sat = 8192 * 1024 // peak
    print(f"    🛑 SATURATION: peak gain {peak} ⇒ the r24 lane rails at |dtorque| ~{sat}, vs the "
          f"repo-recorded max 839 (margin {sat / 839:.2f}x) and the V68-route max 511 "
          f"({sat / 511:.2f}x).")
    assert 5120 * peak < 2 ** 31, "dtorque_clamp * peak gain overflows int32"

    # ---- CRC: THREE blocks. Generic, per build_v60's template. ----------------------------
    blocks = sorted({tuple(V53.owning_block(code, a))
                     for a in (REPOINT_BYTE, ARM_ADDR, CAVE_BASE, SURFACE[0][0], SURFACE[-1][0])})
    print(f"\n  CRC -- {len(blocks)} blocks move:")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")

    # ---- EXACT DIFF vs V68 ----------------------------------------------------------------
    diffs = [i for i in range(len(code)) if code[i] != v68[i]]
    crc_words = {b[1] + k for b in blocks for k in range(4)}
    functional = [d for d in diffs if d not in crc_words]
    print(f"\n  EXACT DIFF vs V68: {len(diffs)} bytes "
          f"({len(functional)} functional + {len(diffs) - len(functional)} CRC bookkeeping)")
    expect = ({REPOINT_BYTE, ARM_ADDR, ARM_ADDR + 1}
              | {a + k for a, _, _, _ in SURFACE for k in (0, 1)}
              | set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))))
    stray = [d for d in functional if d not in expect]
    assert not stray, f"UNATTRIBUTED functional bytes: {[hex(x) for x in stray]}"
    for d in functional:
        where = ("gate byte" if d == REPOINT_BYTE else
                 "arm 0xC6446" if d in (ARM_ADDR, ARM_ADDR + 1) else
                 "cave" if CAVE_BASE <= d < CAVE_BASE + len(V55.CAVE_BYTES) else "surface")
        print(f"    0x{d:05X}  {v68[d]:02X} -> {code[d]:02X}   {where}")
    print("    ✅ zero unattributed functional bytes")

    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    # ---- ENCODE, then RE-RUN every gate on the DECODED READBACK --------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)
    rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(encode)])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V69 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v68)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    print("\n  READBACK -- decoded from the .rwd and re-gated:")
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    assert dec[REPOINT_BYTE] == GATE_STOCK, "readback gate byte wrong"
    assert u16(dec, ARM_ADDR) == ARM_STOCK, "readback arm wrong"
    for addr, _old, new, name in SURFACE:
        assert u16(dec, addr) == new, f"readback {name} wrong"
    assert dec[CAVE_BASE + 2] == LIVE_IMM, "readback liveness immediate wrong"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == cave_bytes, \
        "readback cave differs from the emitted cave"
    assert_probe_census(bytes(dec), cave_span)
    for a in NEIGHBOURS:
        assert bytes(dec[a:a + 20]) == bytes(v68[a:a + 20]), "readback neighbour moved"
    nbad2 = walk_all_blocks(bytes(dec))
    assert nbad2 == 0, f"readback CRC chain FAILED: {nbad2} mismatching block(s)"
    print("    ✅ payload, gate byte, arm, all four surface halfwords, the WHOLE 66-byte cave,")
    print("       the probe census (GATE 1 re-measured on the readback), every neighbour record,")
    print("       and the full CRC chain -- all verified ON THE DECODED READBACK")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n" + "=" * 102)
    print(f"  V69 BUILT. 7 edit sites / {len(functional)} changed bytes, 3 CRC blocks, "
          "cave extent UNCHANGED (66 of the proven 68 B).")
    print(f"  DOSE {SCALE}.000x at creep -> EXACTLY 1.000x above 50 km/h. PROBE re-aimed at the "
          "RATCHET.")
    print("  🛑 SPEC: docs/specs/design/V69-DESIGN.md §6 (the manual-feel cost) and §9 (what falsifies this).")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, hashlib.sha256(rwd).hexdigest()


if __name__ == "__main__":
    build()
