# -*- coding: utf-8 -*-
r"""V278 -- THE REFERENCE BROUGHT BACK INTO REACH.  K = 2.  BASE: V268.  Plus a DAMPING tap.

=== WHY THIS BUILD EXISTS ======================================================================
V276 (reference x6) FLEW on 2026-09-01.  Operator: "Amazing authority now on turns as I would like
on 6x torque.  However, there is now a large, slower (2-4 Hz) oscillation when LKAS engaged ...
excites itself even on straight roads.  Only way to stop it is to hold the steering wheel very firmly."

THE MECHANISM (EVIDENCE, from the bytes and from his rlog r2e):
  E = 32*setpoint - feedback   at 0x29d78.   E > 0 the lane PUSHES.   E < 0 the lane DAMPS.
  Kp, Kd, the forward gain (0xC6CD0 = 5346) and the cap (0xC61B4 = 3072) are byte-identical
  V268 -> V276.  V276 scaled the setpoint AND the feedback clamp by 6, so the rate at which E can go
  negative moved OUT OF PHYSICAL REACH: the loop can no longer change sign, so it never damps.
  His log: a 3.9 Hz amplitude-modulated sinusoid (Q 4, rate excess 4.58 vs corpus median 0.83,
  no flown build has this mode), openpilot's command following the MEASURED angle with coh >= 0.97
  while its desired path is flat -- a COMBINED-loop instability: an EPS lane that never damps plus
  openpilot's outer follower.  The same openpilot did not ring before V276.

THE DOSE, SIZED FROM HIS OWN DRIVE -- frame by frame, not from the map's ceiling.
The feedback operand r26 at 0x29d78 is s_old + s_new of the lag filter (add r9,r26 @0x28FA4 --
verified by the orchestrator), DC gain 2*1560/101 = 30.89 per raw count; the 0x18F wire is
-gp-0x6a56 at 1:1 and 8 counts/deg/s (measured on the log, corr 0.997).  So stock's crossover at
the map's CEILING is 5504/30.89 = 178 wire = 22.3 deg/s -- the inherited figure, reconciled.
But the ceiling is the wrong operating point: during the straight-road oscillation openpilot's
command is only +-300-1300 counts (median 354 -> demand index 22 -> Y 46, not 172), so the
crossover during the oscillation is command-dependent and far lower.  Computed on all 7 episodes
(87 half-cycle peaks) and on normal engaged driving, with the real command, the real rate, the exact
filter and the taper (rlog-tools/studies/osc-2to4/dose_e_sign_by_k.py):

    K    OSC frames: lane OPPOSES wheel    NORMAL engaged: lane opposes wheel
    1            0.94                              0.80        <- stock: no oscillation
    1.5          0.90                              0.75
  * 2            0.86                              0.70
    2.5          0.82                              0.65
    3            0.78                              0.61
    6            0.57                              0.48        <- V276: oscillates

THE MECHANISM IS A MATTER OF DEGREE, NOT A THRESHOLD.  V276 did not stop damping outright; it
cut the fraction of oscillation time in which the lane opposes the wheel from 0.94 to 0.57, and
the combined loop (EPS lane + openpilot's follower) went unstable somewhere in between.  K=2
restores 0.86 of it while keeping the ceiling crossover at 44.5 deg/s (stock 22.3, V276 134) --
so on turns the lane still pushes through the median achieved rate (~27 deg/s) where stock yielded.
The crossover does NOT cap the oscillation's amplitude (V276's peaks overshot theirs 1.5-2x), so a
residual, if any, is not predicted to settle at a particular size.  K=1.5 (0.90) is the fallback.
PEAK TORQUE IS UNTOUCHED AT EVERY K.  The 6x TORQUE (V112: gain redirect + 0xC61B4) stays.

=== THE CELLS ==================================================================================
  [A] ASSIST MAP  -- the 28 LERP records reached via the pointer family 0xC9A88 (data at
      0xE4000-0xE8105): every Y knot xK from the V268 (stock-shape) base.  Honda's SHAPE preserved.
      All 28 dosed, as V276 did; the live slot is 7 (record 11, TVCA4, selector 7 -- CONFIRMED on
      the V276 wire, 35 = 7x5, 46,576/46,576 frames, two decoders).  Slot 7 ceiling 172 -> 344.
  [B] FEEDBACK CLAMP  0xC62E6:  7680 -> 7680*K (stored x256: 30 -> 60).  Ratio 1.395 preserved --
      STRUCTURALLY, because the clamp bounds the same r26 that is subtracted at 0x29d78.
  [C] TELEMETRY -- the CAN-427 packer 0x55DF0-0x55E11 rewritten IN PLACE, 34 bytes, same length,
      jarl 0x55E12 (-> 0x49A90 clamp) untouched:
          wire = (sel & 0x0F) | (DAMPING << 9)      DAMPING = sign(E) != sign(fb_state)
      bit 9 = 1 when the lane's push OPPOSES the wheel's motion -- E = gp-0x6cf8 (32-bit, st.w at
      0x2A18C every tick) XOR the feedback state gp-0x3d30 (st.w at 0x28FA8), sign bit isolated by
      `shr 0x1f`.  Its DUTY is the instrument: the table above, read on the wire.  A plain sign(E)
      bit was designed first and FALSIFIED offline -- it reads ~0.50 at every K because E's sign
      follows the direction of motion.  The comparator is the quantity that discriminates.
      The demand field, the beacon and P-at-clamp did not fit; the selector (7, nonzero) is its
      own liveness signal.  No stores in the window; r6/r7/r8 dead scratch (saved in the prologue,
      never restored); r9 never saved by the prologue.  4 trailing bytes are nop.

=== THE SENTENCE A NULL LICENSES ===============================================================
The wire reads bit-9 DUTY over engaged frames.  On V276 it must read ~0.57 in an oscillation
episode; on V278 the prediction is ~0.86.  If the duty reads ~0.86 AND the oscillation is gone,
the mechanism is confirmed.  If it reads ~0.86 AND the oscillation persists, the damping fraction
is NOT the whole mechanism (openpilot's follower gain is the other term) and a comma-side change
is next.  If it reads ~0.57 on V278, the map is not the live setpoint source and the build is
inert -- the selector in bits 3:0 (must read 7) and the map bytes settle which.  No outcome is
uninterpretable.

=== RISK, PLAINLY ==============================================================================
This is a REDUCTION of a live gain -- the third in ~240 builds, and the first in response to a
symptom a build of ours created.  The two prior reductions (V93/V94) made the car worse.  The felt
authority on turns WILL be less than V276's; it should be clearly more than stock's.  The
oscillation may shrink rather than vanish (see above).  The override taper is byte-stock, so the
operator's escape hatch (a firm grip at ~2500 raw, where the cliff begins) is unchanged.

=== CLASS OF BUILD =============================================================================
The same lever as V276 (the reference), pushed the OTHER way, sized from the operator's own drive
rather than guessed -- plus the first tap in this kit that reads the loop's damping state directly.
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
WRITE_MODE = os.environ.get("ACCORD_V278_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
K = 2                                                   # the reference scale -- THE dose
TAG = f"V278-V268BASE-REFERENCE{K}X.MAP.FEEDBACK.SIGNE.TAP"

# ---- [A] assist map --------------------------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
LIVE_SLOTS = (0, 1, 3, 4, 6, 7, 8, 9)                   # selector max 9; 2 and 5 are dead shapes
LIVE_SLOT = 7                                           # record 11 TVCA4 -- on the wire, 35 = 7x5
MAP_CHANGED_EXPECT = 378                                # 28 x 9 nonzero knots: 252 low bytes + 126 high bytes (x2 of Y<128 leaves the high byte 0) -- audited

# ---- [B] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK = 0xC62E6, 7680
FB_NEW = FB_STOCK * K
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)                  # must all be ld.hu (low byte 0xe5)

# ---- [C] the packer --------------------------------------------------------------------------
PACK_LO, PACK_HI, JARL_CLAMP = 0x55DF0, 0x55E12, 0x55E12
PACK_V268 = bytes.fromhex("24374495bfff663c0a30803effffbfff7a3cca36ffff"
                          "e53740022046ff03003aa332")
PACK_NEW = bytes.fromhex(
    "8437b398"      # ld.bu -0x674e[gp],r6    selector
    "c6360f00"      # andi  0x0f,r6,r6
    "244f0993"      # ld.w  -0x6cf8[gp],r9    E = 32*setpoint - feedback
    "243fd1c2"      # ld.w  -0x3d30[gp],r7    feedback state s_new (same sign as r26)
    "2749"          # xor   r7,r9             r9 = E ^ fb
    "9f4a"          # shr   0x1f,r9           -> 1 iff signs differ = the lane OPPOSES the wheel
    "c94a"          # shl   0x9,r9            -> bit 9
    "0931"          # or    r9,r6
    "2046ff03"      # movea 0x3ff,r0,r8       clamp hi (unchanged)
    "003a"          # mov   0x0,r7            clamp lo (unchanged)
    "00000000")     # nop nop
FB_STATE_DISP, FB_STATE_STORE, FB_STATE_STORE_BYTES = -0x3d30, 0x28FA8, bytes.fromhex("644fd1c2")
FB_SUM_SITE, FB_SUM_BYTES = 0x28FA4, bytes.fromhex("c9d1")     # add r9,r26 -- the two-sample sum
XOR_CONTROL, XOR_CONTROL_BYTES = 0x504E2, bytes.fromhex("2961") # xor r9,r12 in FUN_0005046c -- a real instance
E_CELL_DISP, E_STORE_SITE, E_STORE_BYTES = -0x6cf8, 0x2A18C, bytes.fromhex("64870993")
SEL_WRITER = 0x4272A                                    # st.b -> gp-0x674e, the ONE writer
DEMAND_WRITER = 0x29D14

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


def dec_imm16(img, a):            # andi / movea: (op, reg2, reg1, imm16)
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


def build():
    print("=" * 102)
    print(f"  V278 -- THE REFERENCE x{K} (from x6).  Kp/Kd/taper/gain/clamps FROZEN.  sign(E) TAP.  BASE V268.")
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
    disp = u16(base, E_STORE_SITE + 2) & ~1
    check(disp - 0x10000 == E_CELL_DISP, f"  ... disp = {E_CELL_DISP:#x} (decoded from the bytes)")
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
    print(f"\n  [2] [A] ASSIST MAP -- scaled x{K} from STOCK shape, all {N_SLOTS} records")
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
        newY = tuple(K * y for y in Y)
        check(all(isinstance(v, int) for v in newY), f"map 0x{p:05X} every knot scales to an INTEGER at K={K}")
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        bY = rec(base, p, n)[1]                                    # re-read from BASE, not the loop's tuple
        check(all(gY[i] == K * bY[i] for i in range(n)) and gY[-1] == K * bY[-1],
              f"map 0x{p:05X} every WRITTEN knot == {K} x BASE knot (independent re-read), ceiling {bY[-1]} -> {gY[-1]}")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  ceiling {oldY[-1]:4d} -> {newY[-1]:5d}   (Honda's shape, x{K})")
    for p in ptrs:
        bY, gY = rec(base, p, MAP_N)[1], rec(code, p, MAP_N)[1]
        rs = {gY[i] / bY[i] for i in range(MAP_N) if bY[i]}
        check(rs == {float(K)}, f"map 0x{p:05X}: every nonzero knot ratio to BASE is exactly {K} (no over-dose, no reshape)")
    n_scaled = sum(len(ps) for ps in shapes.values())
    check(n_scaled == len(ptrs) == 28, f"ALL 28 records scaled ({n_scaled}) -- an under-dosed record cannot pass silently")
    map_changed = sum(1 for p in ptrs for i in range(MAP_N) for k in (0, 1)
                      if code[p + 2 + 2 * MAP_N + 2 * i + k] != base[p + 2 + 2 * MAP_N + 2 * i + k])
    check(map_changed == MAP_CHANGED_EXPECT, f"exactly {MAP_CHANGED_EXPECT} map bytes changed ({map_changed})")
    live_p = u32(base, MAP_PTR + 4 * LIVE_SLOT)
    lX, lY = rec(code, live_p, MAP_N)
    check(lY[-1] == 172 * K, f"LIVE slot {LIVE_SLOT} (record 11 TVCA4) ceiling = 172 x {K} = {172 * K}")
    print(f"      live slot {LIVE_SLOT} @0x{live_p:05X}: Y = {lY}")
    print(f"      crossover threshold (operand counts) = 32 x {172 * K} = {32 * 172 * K}")

    # ------------------------------------------------------------------------------------------
    print(f"\n  [3] [B] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == FB_NEW and FB_NEW < 65536, f"feedback clamp == {FB_NEW}, fits u16")
    r0 = FB_STOCK / (32 * 172)
    r1 = FB_NEW / (32 * 172 * K)
    check(abs(r1 - r0) < 1e-9, f"Honda's setpoint:feedback ratio {r0:.4f} preserved EXACTLY")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] [C] THE PACKER -- 34 bytes in place, sign(E) on bit 9")
    check(bytes(base[PACK_LO:PACK_HI]) == PACK_V268, "base packer window == the V268/stock 34 bytes")
    check(jarl_target(JARL_CLAMP, base) == 0x49A90, "0x55E12 is `jarl 0x49A90` (the clamp) -- DECODED")
    check(jarl_target(0x55DF4, base) == 0x49A5A and jarl_target(0x55DFE, base) == 0x49A78,
          "base window calls abs (0x49A5A) and min (0x49A78) -- both DELETED by this rewrite")
    check(len(PACK_NEW) == PACK_HI - PACK_LO == 34, "new window is exactly 34 bytes -- jarl untouched")
    code[PACK_LO:PACK_HI] = PACK_NEW
    attributed |= set(range(PACK_LO, PACK_HI))
    check(jarl_target(JARL_CLAMP, code) == 0x49A90, "jarl 0x49A90 still intact after the rewrite")
    # decode every instruction from the WRITTEN bytes -- the claim is proven from the image
    a = PACK_LO
    check(dec_ld(code, a) == ("ld.bu", 6, 4, -0x674e), "ld.bu -0x674e[gp],r6  (selector)"); a += 4
    check(dec_imm16(code, a) == (0x36, 6, 6, 0x0F), "andi 0x0f,r6,r6"); a += 4
    check(dec_ld(code, a) == ("ld.w", 9, 4, -0x6cf8), "ld.w -0x6cf8[gp],r9  (E)"); a += 4
    check(dec_ld(code, a) == ("ld.w", 7, 4, FB_STATE_DISP), f"ld.w {FB_STATE_DISP:#x}[gp],r7  (feedback state)"); a += 4
    check(f_I(u16(code, a)) == (9, 0x09, 7), "xor r7,r9  (E ^ fb)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x14, 0x1F), "shr 0x1f,r9  (sign of the xor -> 0/1 = DAMPING)"); a += 2
    check(f_II(u16(code, a)) == (9, 0x16, 9), "shl 0x9,r9  (-> bit 9)"); a += 2
    check(f_I(u16(code, a)) == (6, 0x08, 9), "or r9,r6"); a += 2
    check(dec_imm16(code, a) == (0x31, 8, 0, 0x3FF), "movea 0x3ff,r0,r8  (clamp hi)"); a += 4
    check(f_II(u16(code, a)) == (7, 0x10, 0), "mov 0x0,r7  (clamp lo)"); a += 2
    check(u16(code, a) == 0 and u16(code, a + 2) == 0, "2 x nop"); a += 4
    check(a == PACK_HI, "the 10 decoded instructions + 2 nop tile the window exactly")
    # positive controls for the Format-II shift opcodes against a real instance in the base
    check(f_II(u16(base, 0x2A1AC)) == (9, 0x15, 5), "POSITIVE CONTROL: 0x2A1AC decodes as `sar 0x5,r9` (Format II, op 0x15)")
    check(f_I(u16(base, 0x2A1A8)) == (7, 0x0E, 12), "POSITIVE CONTROL: 0x2A1A8 decodes as `add r12,r7` (Format I)")
    check(bytes(base[XOR_CONTROL:XOR_CONTROL + 2]) == XOR_CONTROL_BYTES and f_I(u16(base, XOR_CONTROL)) == (12, 0x09, 9),
          "POSITIVE CONTROL: 0x504E2 is `xor r9,r12` = 29 61 -> Format I op 0x09 is xor")
    check(dec_ld(base, 0x28F7C) == ("ld.w", 26, 4, FB_STATE_DISP), "POSITIVE CONTROL: 0x28F7C is `ld.w -0x3d30[gp],r26` (the PID's own read of the state)")
    check(bytes(base[FB_STATE_STORE:FB_STATE_STORE + 4]) == FB_STATE_STORE_BYTES, "0x28FA8 is `st.w r9,-0x3d30,gp` -- the feedback state is stored every tick")
    check(bytes(base[FB_SUM_SITE:FB_SUM_SITE + 2]) == FB_SUM_BYTES and f_I(u16(base, FB_SUM_SITE)) == (26, 0x0E, 9),
          "0x28FA4 is `add r9,r26` -- r26 = s_old + s_new, DC gain 2*1560/101 = 30.89 (the operand at 0x29d78)")
    # the selector writer and demand writer are untouched
    check(bytes(code[SEL_WRITER:SEL_WRITER + 4]) == bytes(base[SEL_WRITER:SEL_WRITER + 4]), "selector writer untouched")
    check(bytes(code[DEMAND_WRITER:DEMAND_WRITER + 4]) == bytes(base[DEMAND_WRITER:DEMAND_WRITER + 4]), "demand writer untouched")
    check(bytes(code[E_STORE_SITE:E_STORE_SITE + 4]) == E_STORE_BYTES, "E store untouched")
    print("      wire = (sel & 0x0F) | ((sign(E) != sign(fb)) << 9)     max 0x20F = 527 < 1023")
    print("      -> bit 9 duty = fraction of samples in which the lane OPPOSES the wheel = DAMPING.")
    print("      -> selector 7 (this car) reads in bits 3:0; 0 there = dead channel.")

    def decode(w):
        return {"sel": w & 0xF, "damping": (w >> 9) & 1}
    check(decode(0x207) == {"sel": 7, "damping": 1}, "decode(0x207): this car, lane opposing the wheel")
    check(decode(7) == {"sel": 7, "damping": 0}, "decode(7): this car, lane pushing with the wheel")

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

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V278 output")
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

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    _scr = os.environ.get("ACCORD_V278_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v278_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v278_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v278_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V278_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
