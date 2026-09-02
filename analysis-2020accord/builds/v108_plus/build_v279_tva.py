# -*- coding: utf-8 -*-
r"""V279 -- PURE FEEDFORWARD.  The LKAS rate PID becomes a linear torque interface.  BASE: V268.  CAL-ONLY.

=== THE OPERATOR'S DESIGN (2026-09-02) ==========================================================
"openpilot is driving a steering angular velocity setpoint instead of a torque ... turn the PID loop
mechanism in the firmware into a pure feedforward: zero out the angular velocity feedback term, zero out
Kd so the D term is 0, linearize the entire feedforward path.  Keep the effective peak torque at 6x stock."

=== WHAT IT IS ================================================================================
Honda's EPS maps openpilot's torque command to an ANGULAR-RATE SETPOINT and closes a PID on measured
column rate (FUN_00028ea6):  E = 32*setpoint - feedback;  P = clamp(32*E*Kp >> 8, +-15360);
D = clamp(dE*Kd >> 3, +-10240);  delivered = clamp(P+D) * 5346 >> 15.  openpilot's own lateral controller
is wrapped around that inner loop without knowing it.  V279 removes the inner loop:

  [A] FEEDBACK CLAMP 0xC62E6:  7680 -> 0.   The filter output r26 is clamped to +-0xC62E6 at
      0x28fa6-0x28fbc BEFORE the subtraction at 0x29d78, so a zero clamp forces the operand to exactly 0
      on every path (r26>0 -> r14=0; r26<0 -> -0; r26==0 -> 0).  E = 32*setpoint, unconditionally.
      The filter STATE keeps running (st.w @0x28fa8 precedes the clamp) -- only the operand is zeroed.
  [B] Kd -> 0, all 4 knots, all 28 records of the 0xCB7D4 bank.  With no feedback the D term would be
      pure setpoint-kick (dE = 32*d(setpoint)); zeroing it makes D = (dE*0)>>3 = 0 exactly.
  [C] LINEARIZED FEEDFORWARD:  map Y = 2*X at X = (0,12,20,24,32,64,96,128,160,240)  ->  Y = 0..480,
      and Kp FLAT at 256 on all 5 knots.   P = 32 * (2*idx) * 256 >> 8 = 64*idx  EXACTLY, for every
      integer idx 0..240 (asserted from the built image).  P(240) = 15360 = the P clamp 0xC61BC and the
      sum clamp 0xC61BE, so the ceiling is reached exactly at full demand and never exceeded.
      delivered(idx) = 64*idx * 5346 >> 15 = 10.44*idx  ->  2505 at idx 240.  PEAK TORQUE = 6x STOCK,
      UNCHANGED: 0xC61B4, 0xC61BC, 0xC61BE, 0xC6CD0 are all frozen and asserted.
      demand idx = |cmd|/16.2 capped at 240 (0xC64F0/F1), so torque = 2505 * cmd/3886, linear, saturating
      for the top ~5% of openpilot's +-4096 range.
      * Stock's OWN small-signal slope (slot 7, fb=0) is P(12)/12 = 73.5/idx and rises with Kp (248->696)
        before the map's 172 ceiling rolls it off; stock reaches P = 14964 at idx 240.  V279's flat 64/idx
        is within 15% of stock's initial slope and reaches 15360 at 240: stock's feedforward, straightened.
  [D] TELEMETRY -- the CAN-427 packer 0x55DF0-0x55E11 rewritten IN PLACE (34 bytes, jarl untouched):
          wire = (sign(T) << 9) | (|T| >> 3)        T = gp-0x6b38, the DELIVERED lane torque
      gp-0x6b38 is the lane's ramped, gain-multiplied, +-0xC61B4-clamped output, `st.h r1,-0x6b38,gp` at
      0x2A23C, stored unconditionally every tick at the end of FUN_00028ea6; its only other readers are two
      UDS diagnostic loads in FUN_0004e82e -- it has NEVER been on a broadcast frame.  |T| <= 3072 -> /8 <= 384,
      9 bits; the 2505 ceiling reads 313.  Resolution 8 torque counts.
      The operator rejected carrying the selector (measured: 7) and the demand index (computable offline from
      0xE4 and 0x18F).  This is the quantity that is NOT otherwise observable: steeringTorqueEps is ~0 on the wire.
      What it reads: (a) sign(T) == -sign(0xE4 cmd) on every engaged, in-taper, ramped frame proves the feedback
      is dead (~0.5 agreement if it is not); (b) T vs cmd is the delivered surface -- predicted slope
      2505/3886 x taper(driver torque) -- read from the CAR, not the build script.
      ⚠ KNOWN CAVEAT: at 0x2A1FC `add r9,r11` sums the lane's lag readout with a value already in r11 before
      the gain; if that is a second contribution, T = lane + other.  Pinned in the adversarial pass.
      The window reuses the STOCK packer's own skeleton (ld.h / jarl abs / mov r10,r6 / sar 3 / clamp bounds),
      retargets the load to gp-0x6b38, deletes the dead ori/min/andi and the mul 5, and packs the sign from a
      copy in r9 taken BEFORE the abs call (FUN_00049a5a touches only r6, r10, lp -- r9 survives).

=== THE SENTENCE A NULL LICENSES ===============================================================
T == 0 while engaged with cmd != 0, outside taper-closed and ramp-low frames: gp-0x6b38 is not the lane's
output or is gated -- do not trust any other conclusion.  T saturating at 313 (2505) at commands well below
3886: the map is not the live setpoint source.  sign(T) disagreeing with -sign(cmd) on ~50% of qualifying
frames: the feedback is NOT dead.  sign agreement ~1.00 AND T linear in cmd AND the car stable: the operator
has the torque interface he asked for, and openpilot's plant model is on the wire for free.  If the car
oscillates with the tap reading clean, the fix is StarPilot's torque tune (friction first), not the firmware.

=== RISK, PLAINLY ==============================================================================
V276 cut the fraction of oscillation time in which the lane opposes the wheel from 0.94 to 0.57 and the
COMBINED loop (EPS + openpilot's angle follower) rang at 3.9 Hz.  V279 takes that fraction to ZERO by
construction: the EPS supplies NO rate damping at all.  Whether the car is stable now depends entirely
on openpilot's tune and the column's own mechanics.  openpilot's Honda tune was fitted THROUGH the rate
loop; the operator has committed to retuning StarPilot's Kp/Ki multipliers alongside this build.
The override taper is byte-stock: the grip escape (~2500 raw, where the cliff begins) is unchanged.
Everything else -- V112's gain redirect, cap, cave, the pump/mode work -- is byte-identical to V268.

=== CLASS OF BUILD =============================================================================
GENUINELY NEW: the first build to change WHAT THE LOOP IS (a rate regulator -> a torque map) rather than
how hard it pushes or what it asks for.  Cal-only: outside the kit's only bricking class.
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
WRITE_MODE = os.environ.get("ACCORD_V279_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
TAG = "V279-V268BASE-PURE.FEEDFORWARD.FB0.KD0.LINEAR.TORQUE.TAP"

# ---- [C] the linear feedforward -------------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
MAP_SLOPE = 2                                           # Y = 2*X
KP_PTR, KP_N, KP_FLAT = 0xCB994, 5, 256
KD_PTR, KD_N, KD_ZERO = 0xCB7D4, 4, 0
LIVE_SLOTS = (0, 1, 3, 4, 6, 7, 8, 9)
LIVE_SLOT = 7                                           # record 11 TVCA4 -- MEASURED on the V276 wire
P_CLAMP, SUM_CLAMP, GAIN, OUT_CAP = 0xC61BC, 0xC61BE, 0xC6CD0, 0xC61B4
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1

# ---- [A] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK, FB_NEW = 0xC62E6, 7680, 0
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)                  # the three ld.hu readers, all in the clamp block
FB_CLAMP_BLOCK = (0x28FA6, 0x28FBE)
FB_STATE_STORE, FB_STATE_STORE_BYTES = 0x28FA8, bytes.fromhex("644fd1c2")   # st.w r9,-0x3d30 -- BEFORE the clamp
FB_SUM_SITE, FB_SUM_BYTES = 0x28FA4, bytes.fromhex("c9d1")                   # add r9,r26
E_SUB_SITE, E_SUB_BYTES = 0x29D78, bytes.fromhex("ba81")                     # sub r26,r16  (r16 -= r26)

# ---- [D] the packer (V278 rev 1 window, audited) --------------------------------------------
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
E_CELL_DISP, E_STORE_SITE, E_STORE_BYTES = -0x6cf8, 0x2A18C, bytes.fromhex("64870993")
SEL_WRITER, DEMAND_WRITER = 0x4272A, 0x29D14

# ---- frozen torque path, all asserted --------------------------------------------------------
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,     # output cap / forward gain -- the 6x TORQUE, untouched
    0xC61B6: 10240,  0xC61BA: 10240,    # D clamp / I anti-windup
    0xC61BC: 15360,  0xC61BE: 15360,    # P clamp / SUM clamp -- P(240) lands EXACTLY here
    0xC63E6: 0,                         # Ki OFF
    0xC63E8: 923,    0xC63EA: 1560,     # feedback lag (state keeps running; operand is zeroed)
    0xC63EC: 992,    0xC63EE: 507,      # output lag
    0xC62E4: 4,                         # error deadband
    0xC6B26: 256,    0xC6B12: 98,
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
}
GAIN_SITE = 0x2A1EE
CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
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


def put_y(b, p, n, Y, attributed):
    for i, y in enumerate(Y):
        o = p + 2 + 2 * n + 2 * i
        struct.pack_into("<h", b, o, y)
        attributed |= {o, o + 1}


def lerp(X, Y, x):                    # the firmware's integer LERP (floor division on positive slopes)
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X) - 1):
        if X[i] <= x <= X[i + 1]:
            return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])
    raise AssertionError


def f_I(hw):
    return hw >> 11, (hw >> 5) & 0x3F, hw & 0x1F


f_II = f_I


def dec_ld(img, a):
    hw1, hw2 = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    if op in (0x3C, 0x3D):
        disp = (hw2 & ~1) | (op & 1)
        if disp & 0x8000:
            disp -= 0x10000
        return "ld.bu", r2, r1, disp
    if op == 0x39 and hw2 & 1:
        disp = hw2 & ~1
        if disp & 0x8000:
            disp -= 0x10000
        return "ld.w", r2, r1, disp
    return "?", r2, r1, None


def dec_imm16(img, a):
    hw1, imm = u16(img, a), u16(img, a + 2)
    r2, op, r1 = f_I(hw1)
    return op, r2, r1, imm


def jarl_target(addr, img):
    hw1, hw2 = u16(img, addr), u16(img, addr + 2)
    if (hw1 >> 6) & 0x1F != 0b11110:
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
    print("  V279 -- PURE FEEDFORWARD.  fb clamp 0 / Kd 0 / map linear / Kp flat.  Peak 6x stock.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK} (stock, stored x256 = 30)")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "demand index clamp +-240")
    check(base[GAIN_SITE] == 0x25, f"0x{GAIN_SITE:05X} is ld.h (sign-ext) -- gain capped at 32767")

    print("\n  [1b] THE FEEDBACK CLAMP BLOCK -- a zero clamp forces the operand to 0 on every path")
    for a in FB_SITES:
        check(base[a] == 0xE5, f"0xC62E6 read @0x{a:05X} is ld.hu (zero-extend): 0 reads as 0, not as a sign trap")
    check(all(FB_CLAMP_BLOCK[0] - 0x12 <= a < FB_CLAMP_BLOCK[1] for a in FB_SITES),
          "all three readers sit inside the clamp block 0x28F96-0x28FBC -- no reader elsewhere (census in the pass)")
    check(bytes(base[FB_SUM_SITE:FB_SUM_SITE + 2]) == FB_SUM_BYTES and f_I(u16(base, FB_SUM_SITE)) == (26, 0x0E, 9),
          "0x28FA4 `add r9,r26`: r26 = s_old + s_new -- the operand that gets clamped")
    check(bytes(base[FB_STATE_STORE:FB_STATE_STORE + 4]) == FB_STATE_STORE_BYTES,
          "0x28FA8 `st.w r9,-0x3d30,gp` precedes the clamp -- the filter STATE keeps running")
    check(bytes(base[E_SUB_SITE:E_SUB_SITE + 2]) == E_SUB_BYTES and f_I(u16(base, E_SUB_SITE)) == (16, 0x0D, 26),
          "0x29D78 `sub r26,r16`: E = 32*setpoint - r26 -- with r26 forced to 0, E = 32*setpoint")
    # the clamp semantics, mirrored in integer Python from 0x28fa6-0x28fbc
    def fb_clamp(r26, c):
        if not (r26 <= c):          # cmp r13,r26 ; ble  -> taken when r26 <= c
            return c                #   mov r14,r26  (r14 = c)
        if r26 >= -c:               # subr r0,r14 ; cmp r14,r26 ; bge
            return r26
        return -c                   # ld.hu ; subr
    check(all(fb_clamp(v, 0) == 0 for v in (-46080, -1, 0, 1, 7680, 46080)),
          "clamp(r26, +-0) == 0 for r26 < 0, == 0, > 0  (mirrored arithmetic)")
    check(fb_clamp(9000, 7680) == 7680 and fb_clamp(-9000, 7680) == -7680 and fb_clamp(5, 7680) == 5,
          "POSITIVE CONTROL: the same mirror reproduces stock's +-7680 clamp")

    print("\n  [1c] THE SECOND WRITER OF gp-0x6cf8 IS UNREACHABLE -- scanned from the image")
    _jt = jump_targets(base)
    check(0x22522 in _jt.get(0x28EA6, []), "POSITIVE CONTROL: the scan finds FUN_00028ea6's real caller at 0x22522")
    check(0x2A93A not in _jt, "NO jarl/jr/jarl32/jr32 targets FUN_0002a93a (0x2A93A)")
    check(bytes(base).find(struct.pack("<I", 0x2A93A), START) == -1, "NO absolute pointer to 0x2A93A")
    check(bytes(base[E_STORE_SITE:E_STORE_SITE + 4]) == E_STORE_BYTES, "0x2A18C is `st.w r16,-0x6cf8,gp` -- E stored every tick")

    code = bytearray(base)
    attributed = set()

    # ------------------------------------------------------------------------------------------
    print(f"\n  [2] [C] MAP LINEARIZED -- Y = {MAP_SLOPE}*X on all {N_SLOTS} records, X untouched")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(len(ptrs) == 28 and all(START <= p < END for p in ptrs), "28 unique map pointers in range")
    check(bytes(code[MAP_PTR:MAP_PTR + 4 * N_SLOTS]) == bytes(base[MAP_PTR:MAP_PTR + 4 * N_SLOTS]), "pointer family 0xC9A88 byte-identical")
    LIN_Y = tuple(MAP_SLOPE * x for x in MAP_X)
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, _ = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock")
        put_y(code, p, n, LIN_Y, attributed)
        gX, gY = rec(code, p, n)
        check(tuple(gX) == MAP_X and tuple(gY) == LIN_Y, f"map 0x{p:05X} Y == {MAP_SLOPE}*X (re-read from the image)")
        check(all(lerp(gX, gY, i) == MAP_SLOPE * i for i in range(241)), f"map 0x{p:05X} LERP(idx) == {MAP_SLOPE}*idx at every idx 0..240")
    print(f"      Y = {LIN_Y}   (stock slot 7 was {rec(base, u32(base, MAP_PTR + 28), MAP_N)[1]})")

    print(f"\n  [3] [C] Kp FLAT at {KP_FLAT} -- all 5 knots, all {N_SLOTS} records")
    kps = sorted({u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(len(kps) == 28, "28 unique Kp records")
    for p in kps:
        n = s16(base, p)
        check(n == KP_N, f"Kp 0x{p:05X} npt == {KP_N}")
        put_y(code, p, n, (KP_FLAT,) * KP_N, attributed)
        gX, gY = rec(code, p, n)
        check(tuple(gX) == tuple(rec(base, p, n)[0]) and all(y == KP_FLAT for y in gY), f"Kp 0x{p:05X} == {KP_FLAT} flat, X untouched")
        check(all(lerp(gX, gY, i) == KP_FLAT for i in range(241)), f"Kp 0x{p:05X} LERP == {KP_FLAT} at every idx 0..240 (beyond X[-1]=208 too)")
    print(f"      stock slot 7 Kp was {rec(base, u32(base, KP_PTR + 28), KP_N)}")

    print(f"\n  [4] [B] Kd -> {KD_ZERO} -- all 4 knots, all {N_SLOTS} records")
    kds = sorted({u32(base, KD_PTR + 4 * s) for s in range(N_SLOTS)})
    check(len(kds) == 28, "28 unique Kd records")
    for p in kds:
        n = s16(base, p)
        check(n == KD_N, f"Kd 0x{p:05X} npt == {KD_N}")
        put_y(code, p, n, (KD_ZERO,) * KD_N, attributed)
        gX, gY = rec(code, p, n)
        check(tuple(gX) == tuple(rec(base, p, n)[0]) and all(y == 0 for y in gY), f"Kd 0x{p:05X} == 0, X untouched")
    print(f"      stock slot 7 Kd was {rec(base, u32(base, KD_PTR + 28), KD_N)[1]}  -> D = (dE*0)>>3 = 0")

    print(f"\n  [5] [A] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == 0, "feedback clamp == 0  ->  operand r26 == 0 every tick  ->  E = 32*setpoint")

    # ------------------------------------------------------------------------------------------
    print("\n  [6] THE DELIVERED SURFACE, FROM THE BUILT IMAGE -- slot 7 (live), and every live slot")
    PC, SC, G, OC = u16(code, P_CLAMP), u16(code, SUM_CLAMP), u16(code, GAIN), u16(code, OUT_CAP)
    check((PC, SC, G, OC) == (15360, 15360, 5346, 3072), "P clamp / sum clamp / gain / cap frozen on the built image")

    def P_of(slot, idx, img):
        mX, mY = rec(img, u32(base, MAP_PTR + 4 * slot), MAP_N)
        kX, kY = rec(img, u32(base, KP_PTR + 4 * slot), KP_N)
        sp = lerp(mX, mY, idx)
        return max(-PC, min(PC, (32 * sp * lerp(kX, kY, idx)) >> 8))

    for s in LIVE_SLOTS:
        check(all(P_of(s, i, code) == 64 * i for i in range(241)), f"slot {s}: P(idx) == 64*idx EXACTLY for idx 0..240 (fb = 0)")
    check(P_of(LIVE_SLOT, 240, code) == 15360 == PC, "slot 7: P(240) == 15360 == the P clamp -- reached exactly, never exceeded")
    tbl = [(i, P_of(LIVE_SLOT, i, code), (P_of(LIVE_SLOT, i, code) * G) >> 15) for i in (0, 12, 22, 32, 64, 96, 128, 160, 200, 240)]
    print("      idx |     P | delivered (x5346>>15) | ~cmd")
    for i, P, d in tbl:
        print(f"      {i:3d} | {P:5d} | {d:5d}                 | {int(i * 16.2):4d}")
    check(tbl[-1][2] == 2505, "delivered(240) == 2505 == 6x stock's 417 -- PEAK TORQUE UNCHANGED")
    check(all(tbl[k][2] <= tbl[k + 1][2] for k in range(len(tbl) - 1)), "delivered surface monotone")
    s0 = [(P_of(LIVE_SLOT, i, base) * 891) >> 15 for i in (240,)]
    print(f"      stock (891 gain, fb=0): delivered(240) = {s0[0]}   -- the recorded stock max is 417")
    # stock's own low-index slope, for the record
    bX, bY = rec(base, u32(base, MAP_PTR + 28), MAP_N)
    kX, kY = rec(base, u32(base, KP_PTR + 28), KP_N)
    slope0 = (32 * lerp(bX, bY, 12) * lerp(kX, kY, 12) >> 8) / 12
    print(f"      stock slot 7 small-signal slope: P(12)/12 = {slope0:.1f}/idx   vs V279 64/idx")

    # ------------------------------------------------------------------------------------------
    print("\n  [7] [D] THE PACKER -- signed delivered lane torque: sign(T)<<9 | |T|>>3, T = gp-0x6b38")
    check(bytes(base[PACK_LO:PACK_HI]) == PACK_V268, "base packer window == the V268/stock 34 bytes")
    check(jarl_target(JARL_CLAMP, base) == 0x49A90, "0x55E12 is `jarl 0x49A90` (the clamp) -- DECODED")
    check(len(PACK_NEW) == 34, "new window is exactly 34 bytes")
    code[PACK_LO:PACK_HI] = PACK_NEW
    attributed |= set(range(PACK_LO, PACK_HI))
    check(jarl_target(JARL_CLAMP, code) == 0x49A90, "jarl 0x49A90 intact after the rewrite")
    a = PACK_LO
    hw1_t, hw2_t = u16(code, a), u16(code, a + 2)
    check(f_I(hw1_t) == (6, 0x39, 4) and not (hw2_t & 1) and (hw2_t - 0x10000) == T_CELL_DISP,
          "ld.h -0x6b38[gp],r6  (op 0x39 with EVEN hw2 = ld.h; disp decoded from the bytes)"); a += 4
    check(f_I(u16(code, a)) == (9, 0x00, 6), "mov r6,r9  (signed copy before the abs)"); a += 2
    check(jarl_target(a, code) == ABS_FN, "jarl 0x49A5A  (abs) -- target DECODED from the moved site"); a += 4
    check(f_I(u16(code, a)) == (6, 0x00, 10), "mov r10,r6  (|T|)"); a += 2
    check(f_II(u16(code, a)) == (6, 0x15, 3), "sar 0x3,r6  (|T| >> 3)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x14, 0x1F), "shr 0x1f,r9  (sign(T) -> 0/1)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x16, 9), "shl 0x9,r9  (-> bit 9)"); a += 2
    check(f_I(u16(code, a)) == (6, 0x08, 9), "or r9,r6"); a += 2
    check(dec_imm16(code, a) == (0x31, 8, 0, 0x3FF), "movea 0x3ff,r0,r8  (clamp hi)"); a += 4
    check(f_II(u16(code, a)) == (7, 0x10, 0), "mov 0x0,r7  (clamp lo)"); a += 2
    check(all(u16(code, a + k) == 0 for k in (0, 2, 4, 6)), "4 x nop"); a += 8
    check(a == PACK_HI, "the 10 decoded instructions + 4 nop tile the window exactly")
    check(u16(base, PACK_LO) == hw1_t, "POSITIVE CONTROL: the stock window's own `ld.h -0x6c18,gp,r6` has the SAME hw1 (24 37) -- only the disp changed")
    check(jarl_target(0x55DF4, base) == ABS_FN, "POSITIVE CONTROL: the stock window's jarl at 0x55DF4 decodes to the same abs 0x49A5A")
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
    print("      -> T = (-1 if bit9 else 1) * ((wire & 0x1ff) << 3);  2505 reads 313;  sign(T) == -sign(cmd) proves fb dead")

    def decode(w):
        return (-1 if (w >> 9) & 1 else 1) * ((w & 0x1FF) << 3)
    check(decode(313) == 2504 and decode(512 | 313) == -2504 and decode(0) == 0, "decode: 313 -> +2504 (the 2505 ceiling at 8-count resolution), bit 9 -> negative")
    check((3072 >> 3) | 0x200 == 896 < 1023, "max wire value 896 -- the clamp helper stays a pass-through")

    # ------------------------------------------------------------------------------------------
    print("\n  [8] EVERYTHING ELSE BYTE-IDENTICAL TO V268")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "V112 cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]), "FUN_00028ea6 byte-identical -- CAL-ONLY, the PID code is untouched")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == v, f"0x{a_:05X} still {v}")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-stock")
    print(f"      {len(tps)} taper records byte-stock: the grip escape (cliff at 2240-2560 raw) is unchanged")

    print("\n  [9] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [9b] END-STATE, FROM THE FINAL IMAGE -- every edit re-read against the CONSTANTS, not the loop")
    def end_state(img, label):
        check(u16(img, FB_CELL) == 0, f"{label}: 0xC62E6 == 0 (the PRIMARY edit, re-read after CRC)")
        for p in ptrs:
            gX, gY = rec(img, p, MAP_N)
            check(tuple(gX) == MAP_X and tuple(gY) == LIN_Y, f"{label}: map 0x{p:05X} == (X stock, Y = 2X) exactly -- no overdose, no skipped record")
        for p in kps:
            gY = rec(img, p, KP_N)[1]
            check(tuple(gY) == (KP_FLAT,) * KP_N, f"{label}: Kp 0x{p:05X} == 256 x5")
        for p in kds:
            gY = rec(img, p, KD_N)[1]
            check(tuple(gY) == (0,) * KD_N, f"{label}: Kd 0x{p:05X} == 0 x4")
        # the D term itself, from the image: Kd(idx) == 0 for every idx on every slot
        for s in range(N_SLOTS):
            kX, kY = rec(img, u32(base, KD_PTR + 4 * s), KD_N)
            check(all(lerp(kX, kY, i) == 0 for i in range(241)), f"{label}: slot {s} Kd(idx) == 0 for idx 0..240 -> D == 0")
    end_state(code, "final image")

    print("\n  [10] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(PACK_LO, PACK_HI)) | {FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    for p in kps:
        allow |= {p + 2 + 2 * KP_N + k for k in range(2 * KP_N)}
    for p in kds:
        allow |= {p + 2 + 2 * KD_N + k for k in range(2 * KD_N)}
    check(set(pay) <= allow, "every payload byte is a map/Kp/Kd Y knot, the feedback clamp, or the packer window")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(all(PACK_LO <= x < PACK_HI for x in cb), f"all {len(cb)} changed code bytes lie inside the packer window")
    print(f"      {len(pay)} payload bytes, {len(cb)} code, {len(blocks)} CRC trailers")

    print("\n  [11] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V279 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    end_state(dec, "decoded .rwd")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN EXISTS -- the non-circular cipher test is REACHABLE")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    _scr = os.environ.get("ACCORD_V279_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v279_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v279_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v279_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [12] NOT WRITTEN -- set ACCORD_V279_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
