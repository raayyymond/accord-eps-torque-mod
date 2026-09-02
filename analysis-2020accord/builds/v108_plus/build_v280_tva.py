# -*- coding: utf-8 -*-
r"""V280 rev 2 -- THE MAP MADE A STRAIGHT LINE TO THE x6 TOP.  BASE: V268.  Tap (V278 rev 3 window) unchanged.

=== REV 2 (2026-09-02) ===========================================================================
Operator, after reading rev 1 (the knee at 96): "change the setpoint curve to be linear instead of having a knee at 96,
we should linearize this response as much as possible for openpilot to control torque."  Rev 2: every record's Y is a
STRAIGHT LINE through the origin to its own x6 top -- Y'(X) = round(6 * Ytop * X / 240).  Slot 7: 0, 52, 86, 103, 138,
275, 413, 550, 688, 1032 (slope 4.3 per idx).  Relative to Honda's CONCAVE stock shape that is x2.15 at idx 12, x2.2 at 32,
x2.7 at 58, x3.3 at 96, x6 at 240 -- the low-command region is NO LONGER rev 3's x2.  The consequence for the damping
fraction in V276's ringing frames (idx <= 58), chain sim (V280-LINEAR-MAP-2026-09-02.md): 0.840 for the straight line
vs 0.863 for rev 3 / the knee (flown clean at 0.863; V276 rang at 0.576).  The loss is at idx 32-58 (0.851 -> 0.780),
where the concave stock map flattens and the line does not; idx <= 12 is unchanged.  Fully-linear alternatives that hold
0.863: slope 3.8 (top 912, x5.3, ceiling 118 deg/s); a two-segment 3.8 -> 4.48 keeps 1032 with an 18 % kink at idx 64.
The operator chose linearity; 0.840 is between K=2 (0.863) and K=2.5 (0.82), both above any value that rang.  The stall
margin at the top is unchanged from rev 1 (96 deg/s of ripple to desaturate P at a 15 deg/s stall).
Also corrected in rev 2's text: V276 is NOT cited as on-car evidence for anything -- it oscillated constantly and was
barely driven laterally engaged (operator).  "Engaged" everywhere means 0xE4 STEER_REQUEST & 0x18F STEER_CONTROL_ACTIVE.
Rev 1 (knee at 96, image 47bdfb0d...) is SUPERSEDED-DO-NOT-FLASH.


=== WHY THIS BUILD EXISTS ======================================================================
V278 rev 3 FLEW 2026-09-02 (route ..._00000031).  Operator: "amazing authority in terms of maximum angular
velocity and acceleration ... no more constant oscillations like in V276 ... stuttering and oscillations at
high angles far from center -- this is the firmware's largest issue ... it still feels like we are not quite
yet at 6x max angular velocity relative to stock -- confirm this first, then address it without introducing
the V276 oscillations."

MEASURED ON HIS DRIVE (EVIDENCE, rlog-tools/studies/osc-2to4/V278R3-READ-2026-09-02.md,
osc-highangle/HIGHANGLE-V278R3-2026-09-02.md, SERVO-AT-REFERENCE-2026-09-02.md, studies/v280/):
  - The tap is live; saturation duty 0.000 (|T| max 1704 vs the 2481 rail): the P/sum clamps never bound.
  - The 3.9 Hz mode is gone (band excess 0.76 vs V276 4.58; corpus median 0.82).
  - Max rate: sustained full demand (idx 240), hands light: rate p50 42.3 / p90 56.4 deg/s against rev 3's
    44.5 deg/s REFERENCE ceiling; V112 (x1 map) 23.9 / 41.5.  Rev 3 = 1.9x the x1 builds = 32 % of the 6x
    target.  The REFERENCE is the limiter, not torque (|T| p50 at full demand = 22 % of the rail; the lane is
    braking the wheel at its setpoint on 63 % of full-demand frames).
  - The high-angle stutter is a 7.0-7.6 Hz line in the rate AND in T (coherence 1.00), 10 episodes, all at
    |angle| >= 30 deg, 3-9 m/s, command railed (idx 237-238), planner flat, absent on stock and V112 at
    comparable exposure.  Through the chain on the measured rate: in 7 of 10 episodes the wheel is STALLED by
    road/lock load at 10-20 deg/s against a 36-45 deg/s reference, |E| = +7k..+9k, P railed ~50 % of ticks; the
    +-6000 rate ripple at 7 Hz passes through P every time P desaturates, so T carries ~100 % modulation.
    The torque sensor rings at 7 Hz with 1470-1960 raw amplitude (column twist), peaks grazing the 2240
    override cliff on 3-12 % of frames.

THE LEVER, AND WHY IT ADDRESSES BOTH COMPLAINTS AT ONCE:
  (rev 1 reasoning, kept for the record; rev 2 replaces the knee with a straight line -- see the REV 2 block above)
  Raise the map's TOP (idx > 96) from x2 toward x6, keep idx <= 96 at exactly x2.
  - Low-command region (where V276 rang; its ringing frames were idx p50 20 / max 58): byte-identical to
    rev 3, so the damping fraction in those frames is rev 3's 0.863 by construction (V276: 0.576).
  - Top: the reference at full demand goes 44.5 -> 133.6 deg/s.  At high angle the stalled wheel then sees
    E = +25k..+34k instead of +7k: the same +-6000 ripple can no longer desaturate P, so the P-path 7 Hz
    modulation collapses -- open-loop on rev 3's own stutter frames, T ripple/level 0.45 -> 0.18 (uniform
    x6: 0.11).  Margin (adv280b): at a 15 deg/s stall V280's E = 29317 vs P's 5650 linear window, so desaturation
    needs a rate ripple >= 96 deg/s; the measured ripple is 25 deg/s.  Rev 3's margin was 6.7 deg/s.  The remaining 7 Hz path is D (16*dE), map-independent, already on rev 3.  [EVIDENCE: open-loop
    sim on measured rate; BELIEF: the closed loop follows -- V276 itself (x6 everywhere, 73 s engaged) had no
    turn stutter reported.]
  - Cost stated plainly: on frames where the driver spins the wheel ABOVE the old reference (52-73 deg/s,
    3 of 10 episodes) the lane BRAKED on rev 3 (E = 11008-15360 < 0) and will PUSH WITH the driver on V280.
    Steady push at high-angle full demand ~1.3x harder (sim 2194 vs 1663; ~1000-1100 on the wire after the
    low-speed ~0.5 factor).  D-term one-tick rails on command steps (adv280b, 1 kHz tick, 100 Hz ZOH command):
    rev 3 0.71 % of engaged ticks -> V280 1.06 %; on idx >= 128 ticks 0.76 % -> 4.0 %.  Small, real, already on rev 3.  The override cliff is byte-stock; the 7 Hz torque-sensor ring grazing it is a
    known path and is NOT changed here (V277's softened cliff stays on the shelf).

=== THE CELLS ==================================================================================
  [A] ASSIST MAP -- 28 records via 0xC9A88.  REV 2: per knot, Y' = round(K_TOP x Ytop x X / 240) -- a straight line
      through the origin to the record's own x6 top (X untouched).  Slot 7 (live, record 11 TVCA4, stock top 172):
        Y = 0, 52, 86, 103, 138, 275, 413, 550, 688, 1032.   The top knot of every record == V276's image (asserted);
      the low knots are NEW values (rev 3 had x2 of stock's concave shape there).
  [B] FEEDBACK CLAMP 0xC62E6: 15360 -> 46080 = 7680 x 6 = V276's flown value.  Honda's 1.395 setpoint:feedback
      ratio holds at the ceiling (46080 / (32 x 1032) = 1.395).  Below the top the clamp is looser than stock's
      ratio would give; on rev 3's log |fb| >= 15360 on 4.7 % of ticks and the low-idx damping fraction is
      IDENTICAL at either clamp (the comparator is a sign; P rails at |E| >= 15855 at idx 0, 5650 at idx >= 136).  All 3 readers
      are ld.hu (asserted; full decode adv280b: op 0x3F, hw2 odd, reg1 = r5 = tp on this ABI -- the cell IS tp-relative,
      0xBF000 + 0x72E6): 46080 > 32767 is SAFE here.
  [C] TAP unchanged: CAN-427 = (sign(T)<<9) | (|T|>>3), T = gp-0x6b38.  Field = ((b0&3)<<8)|b1 on the wire.

=== PRE-REGISTERED READ (rlog-tools/studies/osc-highangle/PREREG-V280-READ.md) =================
On frames |angle| >= 30 deg AND idx >= 200, per >= 1 s run, with the existing tap:
  (i)  T 6-8.5 Hz amplitude / |T| p50:  rev 3 0.55-0.70;  V280 predicted <= 0.25 with |T| p50 >= 1000.
  (ii) 0x18F signed driver-torque 6-8.5 Hz amplitude: rev 3 1470-1960 raw (no tap needed).
  (iii) 7 Hz episodes per 100 s of high-angle engaged time: rev 3 10 / 102 s.
  Max rate: sustained full-demand hands-light rate p50 -- rev 3 42.3 (p90 56.4); V280 must exceed 56.
  Low-command: damping fraction on |cmd| < 1300 frames 0.30-0.40 (chain on rev 3's frames: 0.34; rev 3 read 0.40);
  2-4 Hz band excess < 1.39 (corpus p95).
  Low-command: the straight line raises the small-signal loop gain x1.6-1.8 at idx 32-58 vs rev 3 (Kp rises with idx, so
  a linear map makes the loop gain GROW with command where rev 3's fell).  A 3.9 Hz return on straight roads => slope 3.8.
  FAIL sentences: ripple/level >= 0.45 or torque ring >= 1200 raw while |T| sits at its low-speed rail  =>
  the 7 Hz is D- or plant-fed and the map top is not the lever (next: Kd, or the cliff).  Rate p50 <= 56 with
  |T| unchanged => load / the low-speed multiplier limits, not the map.  A 3.9 Hz return on straight roads
  => the slope comes down to 3.8 (top 912), which holds rev 3's 0.863.

=== RISK, PLAINLY ==============================================================================
REV 2: the top knot is x6 (as V276 carried) and every other knot (X = 12..160) is a NEW value -- the ratio to stock's
concave map runs x2.17 at idx 12 -> x4.14 at 160.  V276 is NOT a reference (it oscillated constantly and was barely
driven engaged).  In the region where V276 rang (idx <= 58) the line is x2.2-2.7 of stock vs rev 3's x2, damping
fraction 0.840 vs 0.863 (chain sim).  Authority at full demand will rise toward V276's -- the operator
liked that -- and the lane will push with, not against, a driver who spins the wheel fast.  Peak torque
unchanged (a P-only rail delivers 2461 and reads 307 through the post-sum 254/256 multiplier [BELIEF, from two
tapers at 255]; the sum-clamp rail 2481 / 310 needs D's help; the clamps and gain are frozen -- adv280b).  Override taper byte-stock.

=== CLASS OF BUILD =============================================================================
The reference lever a THIRD time, now LINEARISED: V276 (x6 of the concave stock shape) -> V278 (x2 of it) -> V280 rev 2
(a straight line, 4.3 per idx, to the same x6 top).  Flown before: the x2 region (rev 3, clean) and the x6 top knot + clamp 46080 (V276, no turn stutter).
NOT flown before (rev 2): every knot X = 12..160 -- 8 of the 10 knots per record carry values no build has carried.
There is no knee in rev 2; the rev-1 knee text above is kept as the record of the superseded design.  Cal-only; tap unchanged; interpretable from one high-angle turn and one straight road.
"""
import hashlib
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
WRITE_MODE = os.environ.get("ACCORD_V280R2_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
K = 2                                                   # rev 3's uniform scale -- kept only for the rev-3 cross-reads and messages
K_TOP = 6                                               # the scale at idx 240
KNEE_X = 0                                              # rev 2: NO knee -- the whole map is one straight line from the origin
from fractions import Fraction as _Fr
def line_y(ytop, x):                                     # rev 2: Y'(X) = round(K_TOP * ytop * X / 240), exact rationals, round half up
    v = _Fr(K_TOP * ytop * x, 240)
    return int(v + _Fr(1, 2))
TAG = f"V280R2-V268BASE-MAP.LINEAR.TO{K_TOP}X.FEEDBACK46080.TORQUE.TAP"
REV1_IMAGE = "SUPERSEDED_v280_rev1_KNEE96_plain_image.bin"
REV1_SHA = "47bdfb0ddd0e69e2302b814ee6e1c40d683b2d9625189d5e9ef4e98d5bfd7411"
REV3_IMAGE = "_v278_V278R3-V268BASE-REFERENCE2X.MAP.FEEDBACK.TORQUE.TAP_plain_image.bin"
REV3_SHA = "aadeced67ac4f9391db42e2d6779390add9d4c7cdaeeed017111ca629c3765e6"
V276_IMAGE = "_v276_V276-V268BASE-REFERENCE6X.MAP.FEEDBACK_plain_image.bin"
V276_SHA = "f4ea35df1051db25736cd52710dfb8af194d4f74ecfd798d77ba026a7ff5e846"

# ---- [A] assist map --------------------------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
LIVE_SLOTS = (0, 1, 3, 4, 6, 7, 8, 9)                   # selector max 9; 2 and 5 are dead shapes
LIVE_SLOT = 7                                           # record 11 TVCA4 -- on the wire, 35 = 7x5
MAP_CHANGED_EXPECT = None                               # computed against the profile below and cross-checked against rev 3 / V276 images

# ---- [B] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK = 0xC62E6, 7680
FB_NEW = FB_STOCK * K_TOP                               # 46080 = V276's flown value; ratio 1.395 held at the CEILING
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)                  # must all be ld.hu (low byte 0xe5)

# ---- [C] the packer --------------------------------------------------------------------------
PACK_LO, PACK_HI, JARL_CLAMP = 0x55DF0, 0x55E12, 0x55E12
PACK_V268 = bytes.fromhex("24374495bfff663c0a30803effffbfff7a3cca36ffff"
                          "e53740022046ff03003aa332")
PACK_NEW = bytes.fromhex(
    "2437c894"      # ld.h  -0x6b38[gp],r6    T = delivered lane torque (signed 16)
    "0648"          # mov   r6,r9             signed copy, taken BEFORE the abs call
    "bfff643c"      # jarl  0x49a5a           abs  (site moved +2; target unchanged)
    "0a30"          # mov   r10,r6            |T|
    "a332"          # sar   0x3,r6            |T| >> 3   (<= 384)
    "9f4a"          # shr   0x1f,r9           sign(T) -> 0/1
    "c94a"          # shl   0x9,r9            -> bit 9
    "0931"          # or    r9,r6
    "2046ff03"      # movea 0x3ff,r0,r8       clamp hi (unchanged)
    "003a"          # mov   0x0,r7            clamp lo (unchanged)
    "0000000000000000")   # 4 x nop
T_CELL_DISP, T_STORE_SITE, T_STORE_BYTES = -0x6b38, 0x2A23C, bytes.fromhex("640fc894")   # st.h r1,-0x6b38,gp
ABS_FN = 0x49A5A
E_STORE_SITE, E_STORE_BYTES = 0x2A18C, bytes.fromhex("64870993")   # E cell no longer tapped in rev 2; store still asserted untouched
SEL_WRITER, DEMAND_WRITER = 0x4272A, 0x29D14

# ---- frozen torque path, all asserted --------------------------------------------------------
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,     # output cap / forward gain -- the 6x TORQUE, untouched
    0xC61B6: 10240,  0xC61BA: 10240,    # D clamp / I anti-windup
    0xC61BC: 15360,  0xC61BE: 15360,    # P clamp / SUM clamp -- 0xC61BE is the REAL 2505 ceiling
    0xC63E6: 0,                         # Ki OFF
    0xC63E8: 923,    0xC63EA: 1560,     # feedback lag  (16.5 Hz)
    0xC63EC: 992,    0xC63EE: 507,      # output lag    (5.05 Hz)
    0xC62E4: 4,                         # error deadband
    0xC6B26: 256,    0xC6B12: 98,       # the OTHER PID (driver-side)
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
}
GAIN_SITE = 0x2A1EE
CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1
KP_PTR, KD_PTR, KP_N, KD_N = 0xCB994, 0xCB7D4, 5, 4
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p, n):
    return ([u16(b, p + 2 + 2 * i) for i in range(n)],
            [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])


# ---- V850 field decoders, used to PROVE the written bytes are the instructions claimed ---------
def f_I(hw):                      # Format I:  reg2<<11 | op<<5 | reg1
    return hw >> 11, (hw >> 5) & 0x3F, hw & 0x1F


def f_II(hw):                     # Format II: reg2<<11 | op<<5 | imm5
    r2, op, imm = f_I(hw)
    return r2, op, imm


def dec_ld(img, a):               # ld.bu / ld.w gp-relative: returns (mnemonic, reg2, disp)
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    if op in (0x3C, 0x3D):
        disp = (hw2 & ~1) | (op & 1)          # ld.bu: hw2 = disp|1, TRUE bit0 lives in the opcode
        if disp & 0x8000:
            disp -= 0x10000
        return "ld.bu", r2, r1, disp
    if op == 0x39 and hw2 & 1:
        disp = hw2 & ~1
        if disp & 0x8000:
            disp -= 0x10000
        return "ld.w", r2, r1, disp
    return "?", r2, r1, None


def dec_ld_h(img, a):              # ld.h gp-relative: op 0x39 with EVEN hw2 -> (reg2, reg1, disp)
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    if op != 0x39 or (hw2 & 1):
        return None
    return r2, r1, hw2 - 0x10000 if hw2 & 0x8000 else hw2


def dec_imm16(img, a):
    hw1, imm = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    return op, r2, r1, imm


def jarl_target(addr, img, require_lp=True):
    """Format V jarl: reg2 (hw1[15:11]) is the link register. reg2 == r0 is `jr` and reg2 != lp never
    returns to the caller -- a `jr 0x49A5A` here would make the abs helper's `jmp [lp]` return to the
    PACKER'S caller, silently skipping the rest of the window. Audit finding adv279d(a)."""
    hw1, hw2 = u16(img, addr), u16(img, addr + 2)
    if (hw1 >> 6) & 0x1F != 0b11110:
        return None
    if require_lp and (hw1 >> 11) != 31:
        return None
    disp = (((hw1 & 0x3F) << 16) | hw2) & ~1
    if disp & (1 << 21):
        disp -= 1 << 22
    return addr + disp


def jump_targets(img):
    out = {}
    for a_ in range(START, END - 4, 2):
        hw1 = u16(img, a_)
        if (hw1 >> 6) & 0x1F == 0b11110:
            d = (((hw1 & 0x3F) << 16) | u16(img, a_ + 2)) & ~1
            if d & (1 << 21):
                d -= 1 << 22
            out.setdefault(a_ + d, []).append(a_)
        if (hw1 >> 5) == 0x17 and (hw1 & 0x1F) == 0:
            d = struct.unpack_from("<i", img, a_ + 2)[0]
            out.setdefault(a_ + d, []).append(a_)
    return out


def build():
    print("=" * 102)
    print(f"  V280 rev 2 -- MAP a STRAIGHT LINE to x{K_TOP} at 240; clamp 46080.  Kp/Kd/taper/gain/clamps FROZEN.  TORQUE TAP.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK} (stock)")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "index clamp +-240")
    check(base[GAIN_SITE] == 0x25, f"0x{GAIN_SITE:05X} is ld.h (sign-ext) -- gain capped at 32767")
    for a in FB_SITES:
        check(base[a] == 0xE5, f"feedback clamp read @0x{a:05X} is ld.hu -- safe above 32768")
    SIGN_SITES = {0xC61BE: ((0x2A13E, 0xE5), (0x2A146, 0x25), (0x2A14C, 0xE5), (0x2A156, 0xE5),
                            (0x2B024, 0xE5), (0x2B02C, 0x25), (0x2B032, 0xE5), (0x2B03C, 0xE5)),
                  0xC61B4: ((0x2A1F8, 0xE5), (0x2A20C, 0x25), (0x2A212, 0xE5), (0x2A21C, 0xE5),
                            (0x2A910, 0xE5), (0x2A91E, 0x25), (0x2A924, 0xE5), (0x2A92E, 0xE5))}
    for cal_, sites in SIGN_SITES.items():
        for a, want in sites:
            check(base[a] == want, f"0x{cal_:05X} read @0x{a:05X} = {'ld.h SIGN-ext' if want == 0x25 else 'ld.hu'}")
    print("      -> 0xC61BE and 0xC61B4 each carry a sign-extended read: both FROZEN, both < 32768.")

    print("\n  [1b] THE SELECTOR AND THE E CELL, IN THE BASE")
    check(bytes(base[E_STORE_SITE:E_STORE_SITE + 4]) == E_STORE_BYTES,
          "0x2A18C is `st.w r16,-0x6cf8,gp` -- E is stored every PID tick (64 87 09 93)")
    hw1 = u16(base, E_STORE_SITE)
    check(hw1 >> 11 == 16 and (hw1 & 0x1F) == 4, "  ... reg2 = r16, reg1 = gp (decoded from the bytes)")
    check((u16(base, E_STORE_SITE + 2) & ~1) - 0x10000 == -0x6cf8, "  ... disp = -0x6cf8 (decoded from the bytes)")
    check(dec_ld(base, 0x2A178) == ("ld.w", 9, 4, -0x3d3c),
          "POSITIVE CONTROL: 0x2A178 decodes as `ld.w -0x3d3c[gp],r9` (same hw1 form as the tap's ld.w)")
    check(u16(base, 0x2A178) == 0x4F24, "  ... its hw1 is 24 4f -- identical to the tap's ld.w hw1")

    print("\n  [1c] THE SECOND WRITER OF gp-0x6cf8 IS UNREACHABLE -- scanned from the image, positive-controlled")
    # FUN_0002a93a also stores gp-0x6cf8 (at 0x2B058). If it ran, bit 9 would not mean sign(E). Prove no static
    # path reaches it: every jarl/jr disp22, every 48-bit jarl32/jr32, and every absolute pointer in the image.
    def _jump_targets(img):
        out = {}
        for a_ in range(START, END - 4, 2):
            hw1 = u16(img, a_)
            if (hw1 >> 6) & 0x1F == 0b11110:                       # Format V jarl / jr
                d = (((hw1 & 0x3F) << 16) | u16(img, a_ + 2)) & ~1
                if d & (1 << 21):
                    d -= 1 << 22
                out.setdefault(a_ + d, []).append(a_)
            if (hw1 >> 5) == 0x17 and (hw1 & 0x1F) == 0:           # Format VI jarl32 / jr32
                d = struct.unpack_from("<i", img, a_ + 2)[0]
                out.setdefault(a_ + d, []).append(a_)
        return out
    _jt = _jump_targets(base)
    check(0x22522 in _jt.get(0x28EA6, []), "POSITIVE CONTROL: the scan finds FUN_00028ea6's real caller at 0x22522")
    check(0x2A93A not in _jt, "NO jarl/jr/jarl32/jr32 anywhere in the image targets FUN_0002a93a (0x2A93A)")
    check(bytes(base).find(struct.pack("<I", 0x2A93A), START) == -1, "NO absolute pointer to 0x2A93A anywhere in the image")
    print("      -> the only writer of E that can execute is st.w at 0x2A18C in FUN_00028ea6 (residual: register-indirect call, no pointer exists)")

    code = bytearray(base)
    attributed = set()

    # ------------------------------------------------------------------------------------------
    print(f"\n  [2] [A] ASSIST MAP -- a STRAIGHT LINE from the origin to x{K_TOP} of each record's top, all {N_SLOTS} records")
    check(line_y(172, 240) == 1032 and line_y(172, 12) == 52 and line_y(172, 96) == 413, "line_y(172, .) = 52 @12, 413 @96, 1032 @240")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(START <= p < END for p in ptrs), f"all {len(ptrs)} map pointers in range")
    check(bytes(code[MAP_PTR:MAP_PTR + 4 * N_SLOTS]) == bytes(base[MAP_PTR:MAP_PTR + 4 * N_SLOTS]),
          "the pointer family 0xC9A88 itself is byte-identical (the edit is in the DATA)")
    shapes = {}
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        newY = tuple(line_y(Y[-1], x) for x in X)
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        bY = rec(base, p, n)[1]                                    # re-read from BASE, not the loop's tuple
        check(all(gY[i] == line_y(bY[-1], X[i]) for i in range(n)) and gY[-1] == K_TOP * bY[-1],
              f"map 0x{p:05X} every WRITTEN knot == round({K_TOP} x BASEtop x X/240) (independent re-read), top {bY[-1]} -> {gY[-1]}")
        check(all(abs(gY[i] * 240 - K_TOP * bY[-1] * X[i]) <= 120 for i in range(n)), f"map 0x{p:05X} every knot within half a count of the straight line")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  Y {oldY} -> {newY}")
    for p in ptrs:
        bY, gY = rec(base, p, MAP_N)[1], rec(code, p, MAP_N)[1]
        rs = [gY[i] / bY[i] for i in range(MAP_N) if bY[i]]
        check(max(rs) <= K_TOP + 1e-9 and rs[-1] == K_TOP, f"map 0x{p:05X}: no knot exceeds x{K_TOP} of BASE and the top is exactly x{K_TOP} (no over-dose)")
    n_scaled = sum(len(ps) for ps in shapes.values())
    check(n_scaled == len(ptrs) == 28, f"ALL 28 records scaled ({n_scaled}) -- an under-dosed record cannot pass silently")
    map_changed = sum(1 for p in ptrs for i in range(MAP_N) for k in (0, 1)
                      if code[p + 2 + 2 * MAP_N + 2 * i + k] != base[p + 2 + 2 * MAP_N + 2 * i + k])
    exp_changed = sum(1 for p in ptrs for i in range(MAP_N) for k in (0, 1)
                      if struct.pack("<h", line_y(rec(base, p, MAP_N)[1][-1], MAP_X[i]))[k] != struct.pack("<h", rec(base, p, MAP_N)[1][i])[k])
    check(map_changed == exp_changed, f"exactly {exp_changed} map bytes changed ({map_changed}) -- computed from the line")
    live_p = u32(base, MAP_PTR + 4 * LIVE_SLOT)
    lX, lY = rec(code, live_p, MAP_N)
    check(tuple(lY) == (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032), f"LIVE slot {LIVE_SLOT} (record 11 TVCA4) Y == 0,52,86,103,138,275,413,550,688,1032")
    print(f"      live slot {LIVE_SLOT} @0x{live_p:05X}: Y = {lY}")
    print(f"      ceiling crossover: 32 x 1032 = 33024 operand = 133.6 deg/s (rev 3: 44.5, stock 22.3)")
    # the firmware's integer LERP on the live slot: a straight line (rev 2), monotone, 1032 at 240
    def lerp(X, Y, i):
        if i <= X[0]:
            return Y[0]
        if i >= X[-1]:
            return Y[-1]
        for k in range(len(X) - 1):
            if X[k] <= i < X[k + 1]:
                return Y[k] + (Y[k + 1] - Y[k]) * (i - X[k]) // (X[k + 1] - X[k])
    bX, bY = rec(base, live_p, MAP_N)
    check(all(abs(lerp(lX, lY, i) - 4.3 * i) <= 2.0 for i in range(241)), "live LERP(idx) within 2 counts of 4.3 x idx for EVERY idx 0..240 (a straight line; knot rounding + integer LERP floor)")
    check(all(lerp(lX, lY, i + 1) >= lerp(lX, lY, i) for i in range(240)), "live LERP monotone over 0..240")
    check(lerp(lX, lY, 240) == 1032 and lerp(lX, lY, 128) == 550 and lerp(lX, lY, 96) == 413, "live LERP 413 @96, 550 @128, 1032 @240")
    dmax = max(lerp(lX, lY, i + 1) - lerp(lX, lY, i) for i in range(240))
    print(f"      steepest LERP step {dmax} counts/idx (the line is 4.3/idx); 32 x step = dE per idx")

    # ------------------------------------------------------------------------------------------
    print(f"\n  [3] [B] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == FB_NEW and FB_NEW < 65536, f"feedback clamp == {FB_NEW}, fits u16")
    r0 = FB_STOCK / (32 * 172)
    r1 = FB_NEW / (32 * 172 * K_TOP)
    check(abs(r1 - r0) < 1e-9, f"Honda's setpoint:feedback ratio {r0:.4f} preserved EXACTLY at the CEILING (x{K_TOP})")
    check(FB_NEW > 32767, "46080 exceeds int16 -- every reader MUST be ld.hu (asserted in [1]) -- and V276 flew this value")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] [C] THE PACKER -- signed delivered lane torque: sign(T)<<9 | |T|>>3, T = gp-0x6b38")
    check(bytes(base[PACK_LO:PACK_HI]) == PACK_V268, "base packer window == the V268/stock 34 bytes")
    check(jarl_target(JARL_CLAMP, base) == 0x49A90 and (u16(base, JARL_CLAMP) >> 11) == 31, "0x55E12 is `jarl 0x49A90,lp` (the clamp) -- target and lp DECODED")
    check(len(PACK_NEW) == 34, "new window is exactly 34 bytes")
    code[PACK_LO:PACK_HI] = PACK_NEW
    attributed |= set(range(PACK_LO, PACK_HI))
    check(jarl_target(JARL_CLAMP, code) == 0x49A90 and (u16(code, JARL_CLAMP) >> 11) == 31, "jarl 0x49A90,lp intact after the rewrite")
    a = PACK_LO
    hw1_t, hw2_t = u16(code, a), u16(code, a + 2)
    check(f_I(hw1_t) == (6, 0x39, 4) and not (hw2_t & 1) and (hw2_t - 0x10000) == T_CELL_DISP,
          "ld.h -0x6b38[gp],r6  (op 0x39 with EVEN hw2 = ld.h; disp decoded from the bytes)"); a += 4
    check(f_I(u16(code, a)) == (9, 0x00, 6), "mov r6,r9  (signed copy before the abs)"); a += 2
    check(jarl_target(a, code) == ABS_FN and (u16(code, a) >> 11) == 31, "jarl 0x49A5A,lp  (abs) -- target AND link register lp DECODED from the moved site"); a += 4
    check(f_I(u16(code, a)) == (6, 0x00, 10), "mov r10,r6  (|T|)"); a += 2
    check(f_II(u16(code, a)) == (6, 0x15, 3), "sar 0x3,r6  (|T| >> 3)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x14, 0x1F), "shr 0x1f,r9  (sign(T) -> 0/1)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x16, 9), "shl 0x9,r9  (-> bit 9)"); a += 2
    check(f_I(u16(code, a)) == (6, 0x08, 9), "or r9,r6"); a += 2
    check(dec_imm16(code, a) == (0x31, 8, 0, 0x3FF), "movea 0x3ff,r0,r8  (clamp hi)"); a += 4
    check(f_II(u16(code, a)) == (7, 0x10, 0), "mov 0x0,r7  (clamp lo)"); a += 2
    check(all(u16(code, a + k) == 0 for k in (0, 2, 4, 6)), "4 x nop"); a += 8
    check(a == PACK_HI, "the 10 decoded instructions + 4 nop tile the window exactly")
    check(dec_ld_h(base, PACK_LO) == (6, 4, -0x6abc), "the V268 window loads gp-0x6ABC (V112's tap), NOT stock's gp-0x6c18 -- decoded")
    check(u16(base, PACK_LO) == hw1_t, "POSITIVE CONTROL: the V268 window's own `ld.h -0x6abc,gp,r6` (V112's repoint of stock's -0x6c18) has the SAME hw1 (24 37) -- only the disp changed")
    check(jarl_target(0x55DF4, base) == ABS_FN, "POSITIVE CONTROL: the V268 window's jarl at 0x55DF4 decodes to the same abs 0x49A5A, with lp")
    check(bytes(base[T_STORE_SITE:T_STORE_SITE + 4]) == T_STORE_BYTES and f_I(u16(base, T_STORE_SITE)) == (1, 0x3B, 4)
          and (u16(base, T_STORE_SITE + 2) - 0x10000) == T_CELL_DISP,
          "0x2A23C is `st.h r1,-0x6b38,gp` -- the delivered lane torque is stored every tick (disp decoded)")
    check(bytes(code[T_STORE_SITE:T_STORE_SITE + 4]) == T_STORE_BYTES, "T store untouched")
    _abs = bytes(base[ABS_FN:ABS_FN + 0x18])
    check(all(bytes(code[ABS_FN + k:ABS_FN + k + 2]) == bytes(base[ABS_FN + k:ABS_FN + k + 2]) for k in range(0, 0x18, 2)), "abs helper 0x49A5A byte-identical")
    check(dec_ld(base, 0x2A178) == ("ld.w", 9, 4, -0x3d3c), "POSITIVE CONTROL: 0x2A178 decodes as `ld.w -0x3d3c[gp],r9`")
    check(f_II(u16(base, 0x2A1AC)) == (9, 0x15, 5), "POSITIVE CONTROL: 0x2A1AC decodes as `sar 0x5,r9`")
    for site in (SEL_WRITER, DEMAND_WRITER, E_STORE_SITE, T_STORE_SITE):
        check(bytes(code[site:site + 4]) == bytes(base[site:site + 4]), f"writer at 0x{site:05X} untouched")
    print("      wire = (sign(T) << 9) | (|T| >> 3)      T = gp-0x6b38, |T| <= 3072 -> max 0x380 = 896 < 1023")
    print("      -> T = (-1 if bit9 else 1) * ((wire & 0x1ff) << 3);  a railed sum reads 310 (2481 through the output lag), never 313")

    def decode(w):
        return (-1 if (w >> 9) & 1 else 1) * ((w & 0x1FF) << 3)
    check(decode(310) == 2480 and decode(512 | 310) == -2480 and decode(0) == 0, "decode: 310 -> +2480 (the railed-sum delivery at 8-count resolution), bit 9 -> negative")
    check((3072 >> 3) | 0x200 == 896 < 1023, "max wire value 896 -- the clamp helper stays a pass-through")

    # ------------------------------------------------------------------------------------------
    print("\n  [5] EVERYTHING ELSE BYTE-IDENTICAL TO V268")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "V112 cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]), "FUN_00028ea6 byte-identical -- the PID is not touched")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == v, f"0x{a_:05X} still {v}")
    for nm, ptr, npt in (("Kp", KP_PTR, KP_N), ("Kd", KD_PTR, KD_N)):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = s16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"{nm} slot {s} byte-identical")
            check(min(rec(code, p, n)[1]) > 0, f"{nm} slot {s}: every Y knot > 0 -- the lane keeps the sign of E (the damping decode rests on this)")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-stock")
    print(f"      {len(tps)} taper records byte-stock: the operator's grip escape (cliff at 2240-2560) is unchanged")

    # ------------------------------------------------------------------------------------------
    print("\n  [6] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [7] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(PACK_LO, PACK_HI)) | {FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    check(set(pay) <= allow, "every payload byte is a MAP Y knot, the feedback clamp, or the 34-byte packer window")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(all(PACK_LO <= x < PACK_HI for x in cb), f"all {len(cb)} changed code bytes lie inside the packer window")
    print(f"      {len(pay)} payload bytes, {len(cb)} code, {len(blocks)} CRC trailers")

    print("\n  [7b] CROSS-IMAGE: rev 3 (same window/code), V276 (same top knots, same clamp), V280 rev 1 (knee) -- read from THOSE images")
    rev3 = Path(plain_image_path(REV3_IMAGE)).read_bytes()
    v276 = Path(plain_image_path(V276_IMAGE)).read_bytes()
    check(hashlib.sha256(rev3).hexdigest() == REV3_SHA, "V278 rev 3 image sha256 matches the reported hash")
    check(hashlib.sha256(v276).hexdigest() == V276_SHA, "V276 image sha256 matches the reported hash")
    check(bytes(code[0x13000:0xC0000]) == bytes(rev3[0x13000:0xC0000]), "code region 0x13000-0xC0000 byte-identical to rev 3 (window, PID function, everything)")
    d3 = [x for x in range(0xC0000, END) if code[x] != rev3[x] and (x & 0xFFF) < 0xFFC]
    allow3 = {FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow3 |= {p + 2 + 2 * MAP_N + 2 * i + k for i in range(1, MAP_N) for k in (0, 1)}
    check(d3 and set(d3) <= allow3, f"vs rev 3: every payload difference is a map knot X>=12 or 0xC62E6 ({len(d3)} bytes)")
    rev1 = Path(plain_image_path(REV1_IMAGE)).read_bytes()
    check(hashlib.sha256(rev1).hexdigest() == REV1_SHA, "V280 rev 1 (knee) image sha256 matches the reported hash")
    d1 = [x for x in range(START, END) if code[x] != rev1[x] and (x & 0xFFF) < 0xFFC]
    allow1 = set()
    for p in ptrs:
        allow1 |= {p + 2 + 2 * MAP_N + 2 * i + k for i in range(1, 9) for k in (0, 1)}
    check(d1 and set(d1) <= allow1, f"vs rev 1: the ONLY differences are map knots X=12..160 ({len(d1)} bytes); clamp, top knots, code identical")
    for p in ptrs:
        check(rec(code, p, MAP_N)[1][-1] == rec(v276, p, MAP_N)[1][-1], f"map 0x{p:05X} top knot == V276's image")
    check(u16(v276, FB_CELL) == FB_NEW, "0xC62E6 == V276's flown value (read from the V276 image)")
    d6 = [x for x in range(0xC0000, END) if code[x] != v276[x] and (x & 0xFFF) < 0xFFC]
    allow6 = set()
    for p in ptrs:
        allow6 |= {p + 2 + 2 * MAP_N + 2 * i + k for i in range(1, 9) for k in (0, 1)}
    check(d6 and set(d6) <= allow6, f"vs V276: every cal difference is a map knot X=12..160 ({len(d6)} bytes); clamp and top knots identical")
    cb6 = [x for x in range(0x13000, 0xC0000) if code[x] != v276[x] and (x & 0xFFF) < 0xFFC]
    check(all(PACK_LO <= x < PACK_HI for x in cb6), "vs V276: the only code difference is the tap window")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V280 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49")
    # FAIL-CLOSED cipher validation (V277's fix: an hasattr-gated `else True` passed while printing "validated")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN EXISTS -- the non-circular cipher test is REACHABLE")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image")

    print("\n  [8b] END STATE -- re-read from the FINAL image and the DECODED .rwd")
    for nm, im in (("code", code), ("dec", dec)):
        check(u16(im, FB_CELL) == FB_NEW, f"{nm}: 0xC62E6 == {FB_NEW}")
        check(tuple(rec(im, u32(im, MAP_PTR + 4 * LIVE_SLOT), MAP_N)[1]) == (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032), f"{nm}: live slot Y == the straight line")
        check(all(rec(im, p, MAP_N)[1] == [line_y(rec(base, p, MAP_N)[1][-1], x) for x in MAP_X] for p in ptrs), f"{nm}: all 28 map records == line(base top)")
        check(bytes(im[PACK_LO:PACK_HI]) == PACK_NEW, f"{nm}: packer window == the torque tap")
        check((u16(im, 0xC61BE) * u16(im, 0xC6CD0)) >> 15 == 2505, f"{nm}: sum-clamp ceiling 15360 x 5346 >> 15 == 2505 (delivered 2481 through the 0.990 readout; reads 310)")
        _s = u16(im, 0xC61BE) * u16(im, 0xC63EE) >> 5; _ro = (_s + _s) >> 5
        check((_ro * u16(im, 0xC6CD0) >> 15) >> 3 == 310, f"{nm}: railed-sum delivered torque through the output lag = {(_ro * u16(im, 0xC6CD0) >> 15)} -> reads {(_ro * u16(im, 0xC6CD0) >> 15) >> 3} (never 313)")
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    _scr = os.environ.get("ACCORD_V280R2_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v280_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v280_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v280_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V280R2_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
