# -*- coding: utf-8 -*-

r"""builds/v18_v49/build_v37a_tva.py -- V37A = V37 with the 2x LKAS mod MOVED from the torque constant to the

RATE-REFERENCE MAP.  Cal-only.  Built 2026-10-17 on the operator's instruction.



=== THE OPERATOR'S ASK (2026-10-17, verbatim in substance) ========================================

"Take this RWD [the Downloads copy, SHA256 8a809d1b... == V37 byte-exact], and understanding all that we do

now at V300, change the 2x mod implementation from 2x LKAS gain through a constant: modify the LKAS angle

velocity setpoint table to have a 2x slope w.r.t. the input (from CAN bus) and remove the top cap (fixed 2x

slope all the way up)."  Naming rule given: V36 -> V36A, V36B -> V36C; the file is V37, so this is V37A.



=== WHAT V37 DID, AND WHAT V37A DOES INSTEAD ======================================================

V37's "2x torque" is THREE cells (V18, carried through V31/V36/V37):

    0xC646C  arb Q15 output gain      891 -> 1782     the LKAS lane's forward gain (shared cell; stock code

                                                      reads it at 0x2A1EE -- the V57 decouple to 0xC6CD0 does

                                                      not exist on this image)

    0xC61B4  lane output clamp        512 -> 1024     tracking the gain

    0xC61B2  limit&pack clamp         512 -> 1024     tracking the gain

That doubled how hard the LKAS rate loop PUSHES (P-rail torque 410 -> ~820 counts) and left what it ASKS FOR

untouched: the assist map, Honda's concave rate REFERENCE that saturates at 172 counts (~22 deg/s).  The

kit's post-V38 diagnosis (memory accord-lkas-commands-rate-not-torque, V276/V278/V280) is that this is why

"the angle rate never scaled with the torque".



V37A puts ALL THREE back to STOCK and instead rewrites the reference:

  [A] ASSIST MAP, 28 LERP records via the pointer family 0xC9A88 (records 0xE4000..0xE8105, n = 10,

      X = 0,12,20,24,32,64,96,128,160,240 untouched).  Per record Y'[i] = round(2 * Y[1] * X[i] / 12):

      a STRAIGHT LINE through the origin at TWICE the record's own first-segment (small-signal) slope, no

      saturation.  Live slot 7 (record 11 TVCA4, selector MEASURED 7 on the V276 wire):

          stock  Y = 0, 24, 42, 50,  62, 100, 126, 154, 166, 172     (slope 2.0/idx to idx 32, then flattens)

          V37A   Y = 0, 48, 80, 96, 128, 256, 384, 512, 640, 960     (exactly 4 * idx, EVERY idx 0..240)

      The integer LERP walk reproduces 4*idx exactly because every knot is on the line and every segment's

      (dY * dx) / dX divides exactly -- asserted below for all 241 indices with the golden model's walk.

      idx = rectified, taper-scaled, +-240-clamped 0xE4 STEER_TORQUE: 16.125736 wire counts per idx LSB;

      the LIM record (0xE51A8, flat 15360 = 3840 wire) caps idx at 238 on the stock wire, so X[9] = 240

      is never exceeded and "no cap" is fully delivered by the linear last segment.

  [B] FEEDBACK CLAMP 0xC62E6  7680 -> 42865 = round(7680 * 960 / 172): Honda's setpoint:feedback ratio

      1.3953 held at the new top (42865 / (32*960) = 1.3953).  Without this the lag output r26 (the measured

      wheel-rate feedback) saturates at 7680 = ~31 deg/s while the reference asks for up to 124 deg/s, so

      above sp = 240 (idx 60) E = 32*sp - fb could NEVER go negative and the lane would lose its damping

      exactly where the new map asks most.  V276, V278 and V280 all scaled this cell with the map for the same

      structural reason.  All 3 readers are ld.hu (0x28F96/0x28F9C/0x28FB8, asserted), so 42865 > 32767 is safe.

      ⚠ This is the ONE cell beyond the literal ask; it is the companion edit the reference lever has always

      carried, and it is flagged as such on the page and in the close-out.

  [C] GAIN / CLAMPS back to STOCK: 0xC646C 1782 -> 891, 0xC61B2 1024 -> 512, 0xC61B4 1024 -> 512.

      Peak lane torque is therefore HONDA'S again: P clamp 15360 x taper 254/256 -> output lag 0.990 -> x891

      >> 15 = 410 counts (V37: ~820).  The 512 clamp never binds (410 < 512), as on stock.



Everything else on V37 is carried byte-identical: the V36 debounce-SM cals (0xC64B4..B7 = 0xFF,

0xC61C0/C2/C4 = 0xFFFF), the V37 DTC-0x49 gate (0xC64B8 = 0xFF), the V18 EME ramp step 0xC64DE = 0x1B, the

V25-V31 corridor x4 (int 0xC674E.. / float 0xC6598..) and boost floor 4096 (int 0xC6768.. / float 0xC65C4..),

and the two part-number bytes.  No code byte changes anywhere.



=== THE DELIVERED SURFACE, READ FROM THE IMAGES (fb = 0, stalled wheel, cold-boot march) ===========

      idx   stock sp / T      V37 sp / T        V37A sp / T

       12      24 /  23         24 /  46          48 /  47
       32      62 /  76         62 / 153         128 / 158
       60      95 / 152         95 / 304         240 / 384
       64     100 / 165        100 / 331         256 / 410  <- P RAILS from idx 63 at a stalled wheel
      240     172 / 399        172 / 799         960 / 410

  (printed by this script from the three images; the fb = 0 column is a BOUND, not a description -- the loop

  nulls the error as the wheel reaches the reference.)  Kp schedule stock (248,512,645,696,696 at

  X 0,68,112,136,208), Kd 128 flat, Ki 0: untouched.



=== THE INSTRUMENT, AND THE SENTENCE A NULL LICENSES ===============================================

No cave, no tap: this is a pre-V53 image and the quantity the edit moves -- the ACHIEVED STEERING RATE per

unit of 0xE4 demand -- is already free on the wire (0x18F / 0x156 angle rate vs 0xE4 STEER_TORQUE).

Pre-registered read, one short engaged episode:

  * small/medium demand (idx <= 60, 91 % of engaged time): achieved rate per idx DOUBLES vs V37 / stock

    (stock reference 2.0 counts/idx = 0.26 deg/s per idx; V37A 4.0 = 0.52 deg/s per idx); the loop's

    damping-fraction (sign(E) != sign(fb) duty) sits at the K = 2 value ~0.86 (V278 flew it clean).

  * sustained full demand, hands light: stock/V112 rate p50 ~24 deg/s; V278 (x2 map, x6 torque) 42 deg/s.

    V37A asks 124 deg/s but pushes with HONDA'S torque, so the rate is TORQUE-limited there, not

    reference-limited: expect well below 124, above stock's 24.

  * NULL: achieved rate per idx unchanged from V37 on straight-road corrections => the map is not the

    live setpoint source on this image (selector not 7) -- the build is inert, not harmful.



=== RISK, PLAINLY ==================================================================================

  * Peak LKAS torque HALVES relative to V37 (back to Honda's 410).  The car will feel LESS strong on hard

    turns than V37 did; faster to respond on small corrections.

  * P rails from idx 63 at a stalled wheel (stock: never; Kp climbs 248 -> 512 over idx 0..68, so the
    stalled-wheel P grows ~quadratically with demand).  V280 (linear map to 1032 at x6 torque) flew

    r32/r33: "slight oscillation ... a small signal riding on top of a large one" in strong turns -- the 7 Hz

    P-desaturation mechanism.  V37A has the same reference shape at 1/6 of V280's torque: the mechanism is

    reachable, its amplitude bounded by Honda's rail.  BELIEF: milder than r32/r33; not flown.

  * The low-idx damping fraction is the K = 2 regime that V278 rev 3 flew clean (no 3.9 Hz); V280's straight

    line (4.3/idx) sim'd 0.840.  V37A's 4.0/idx sits between.  BELIEF for this image; EVIDENCE for V278/V280.

  * The V36/V37 trips (STEER_STATUS 4 debounce, DTC 0x49) stay OFF as on V37.



=== CLASS OF BUILD =================================================================================

The REFERENCE lever (V276 / V278 / V280's class) applied for the first time to a STOCK-TORQUE image: it

moves what the rate loop asks for and puts how hard it pushes back to Honda.  Cal-only, no cave, no

telemetry, 3 cells reverted + 1 cell scaled + 28 x 9 knots rewritten.

"""

# --- PATH BOOTSTRAP (kit standard) -------------------------------------------------------------

import os as _os, sys as _sys

_r = _os.path.dirname(_os.path.abspath(__file__))

while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):

    _n = _os.path.dirname(_r)

    if _n == _r:

        raise RuntimeError("no .pkgroot marker above " + __file__)

    _r = _n

_repo = _r

while not _os.path.isdir(_os.path.join(_repo, ".git")):

    _n = _os.path.dirname(_repo)

    if _n == _repo:

        _repo = None

        break

    _repo = _n

_roots = [_r]

if _repo:

    for _e in sorted(_os.listdir(_repo)):

        _d = _os.path.join(_repo, _e)

        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):

            _roots.append(_d)

_p = []

for _root in _roots:

    _p.append(_root)

    for _b, _ds, _fs in _os.walk(_root):

        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in

                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]

        _p.extend(_os.path.join(_b, _x) for _x in _ds)

_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]

for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",

           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):

    globals().pop(_v, None)

# --- end path bootstrap -------------------------------------------------------------------------

import gzip

import hashlib

import io

import contextlib

import os

import struct

import sys

import zlib

from dataclasses import replace



from firmware_paths import CALIB_FILES, RWD_DIR, STOCK_FW_DUMP, plain_image_path

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS

from verify_bootloader_crc import walk, walk_all_blocks

import build_v37_tva as V37                                      # headers / cipher / full_image, nothing runs

import eps_lkas_chain_model as GM



START, END = 0x13000, 0x100000

LABEL = "V37A"

TAG = "V37BASE-MAP.SLOPE2X.NOCAP-GAIN891-CLAMPS512-FBCLAMP42865"

BASE_IMAGE = plain_image_path("_v37_plain_image.bin")

BASE_SHA = "9ce6609059e2549246d459d593de943363ebe46e07fd984e4ec0c6a0498f0487"      # == Downloads rwd payload

BASE_RWD_SHA = "8a809d1b320957e4846c9145ee662858759d514681ce46c247a4a197784202da"  # the operator's file

BIN_OUT = plain_image_path("_v37a_plain_image.bin")

WRITE = os.environ.get("ACCORD_V37A_WRITE", "1").strip().lower() not in ("0", "no", "false")



# [A] assist map

MAP_PTR, MAP_N, N_SLOTS, LIVE_SLOT = 0xC9A88, 10, 28, 7

MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)

LIVE_Y_STOCK = (0, 24, 42, 50, 62, 100, 126, 154, 166, 172)

LIVE_Y_NEW = (0, 48, 80, 96, 128, 256, 384, 512, 640, 960)

# [B] feedback clamp

FB_CELL, FB_STOCK, FB_NEW = 0xC62E6, 7680, 42865

FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)

# [C] gain / clamps back to stock

REVERTS = [  # addr, v37, stock, note

    (0xC646C, 1782, 891, "arb Q15 output gain -- the LKAS forward gain on this image (ld.h @0x2A1EE)"),

    (0xC61B2, 1024, 512, "limit&pack clamp"),

    (0xC61B4, 1024, 512, "lane output clamp (4 readers 0x2A1F8/20C/212/21C)"),

]

GAIN_LOAD_SITE = (0x2A1EE, bytes.fromhex("253f6c74"))           # ld.h 0x746c[tp],r9 -- stock displacement

CRC_BLOCKS = [(0xC6000, 0xC6FFC), (0xE4000, 0xE4FFC), (0xE5000, 0xE5FFC), (0xE6000, 0xE6FFC),

              (0xE7000, 0xE7FFC), (0xE8000, 0xE8FFC)]



_checks = [0, 0]





def check(cond, msg):

    _checks[0] += 1

    _checks[1] += bool(cond)

    print(f"      {'[PASS]' if cond else '[FAIL]'} {msg}")

    return bool(cond)





u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]            # noqa: E731

s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]            # noqa: E731

u32 = lambda b, a: struct.unpack_from("<I", b, a)[0]            # noqa: E731





def rec(b, p, n):

    return ([u16(b, p + 2 + 2 * i) for i in range(n)], [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])





def line_y(y1, x):

    """Y'[i] = round-half-up(2 * Y[1] * X[i] / 12): twice the record's first-segment slope, through the origin."""

    return (2 * y1 * x * 2 + 12) // 24





def is_ld_hu(b, a):

    """Format VII ld.hu: opcode field 0x3F in hw1 bits 10:5 and hw2 bit 0 set (firmware-decompile skill)."""

    hw1, hw2 = u16(b, a), u16(b, a + 2)

    return ((hw1 >> 5) & 0x3F) == 0x3F and (hw2 & 1) == 1





def cal_for(img):

    """A golden-model Calibration read from THIS image's cells (the PID stage only)."""

    live = u32(img, MAP_PTR + 4 * LIVE_SLOT)

    kp = u32(img, 0xCB994 + 4 * LIVE_SLOT)

    kd = u32(img, 0xCB7D4 + 4 * LIVE_SLOT)

    mx, my = rec(img, live, MAP_N)

    kx, ky = rec(img, kp, 5)

    dx, dy = rec(img, kd, 4)

    return replace(GM.Calibration(), assist_map_x=tuple(mx), assist_map_y=tuple(my), kp_x=tuple(kx), kp_y=tuple(ky),

                   kd_x=tuple(dx), kd_y=tuple(dy), fb_clamp=u16(img, FB_CELL), pid_p_clamp=u16(img, 0xC61BC),

                   sum_clamp=u16(img, 0xC61BE), pid_d_clamp=u16(img, 0xC61B6), pid_i_clamp=u16(img, 0xC61BA),

                   pid_ki=u16(img, 0xC63E6), fb_lag_a=s16(img, 0xC63E8), fb_lag_b=u16(img, 0xC63EA),

                   out_lag_a=s16(img, 0xC63EC), out_lag_b=u16(img, 0xC63EE),

                   lkas_forward_gain=u16(img, 0xC646C), out_clamp=u16(img, 0xC61B4))





def surface(img, idxs):

    cal = cal_for(img)

    return {i: GM.lkas_rate_pid_surface(i, cal) for i in idxs}





def main():

    print("=" * 96)

    print(f"{LABEL}: V37 base; 2x LKAS moved from the torque constant to the rate-reference map; cap removed")

    base = bytearray(open(BASE_IMAGE, "rb").read())

    stock = open(STOCK_FW_DUMP / "code.bin", "rb").read()

    print("\n  [0] BASE")

    check(len(base) == 0x100000 and len(stock) == 0x100000, "base and stock are 1 MB images")

    check(hashlib.sha256(base).hexdigest() == BASE_SHA, f"base == _v37_plain_image.bin sha256 {BASE_SHA[:16]}...")

    dl = os.environ.get("ACCORD_V37_RWD", r"C:\Users\dudei\Downloads\39990-TVA-A160 (Honda Accord)\39990-TVA,A160-V37-2xTorque.rwd")

    dec = build_decode_table(V37.V9B["keys"], V37.V9B["ops"])

    enc = invert_table(dec)

    if os.path.exists(dl):

        rwd_dl = open(dl, "rb").read()

        check(hashlib.sha256(rwd_dl).hexdigest() == BASE_RWD_SHA, "the operator's Downloads rwd sha256 == V37's")

        pay = bytes(parse_x31(rwd_dl)["encs"][0]).translate(dec)

        check(pay == bytes(base[START:END]), "the Downloads rwd DECRYPTS to the base image window (byte-exact)")

    else:

        print("      [skip] Downloads rwd not present; base sha asserted above")

    for a, v37v, _, note in REVERTS:

        check(u16(base, a) == v37v, f"base 0x{a:05X} == {v37v} ({note})")

    check(u16(base, FB_CELL) == FB_STOCK, f"base 0xC62E6 == {FB_STOCK} (stock)")

    check(base[GAIN_LOAD_SITE[0]:GAIN_LOAD_SITE[0] + 4] == GAIN_LOAD_SITE[1] == stock[GAIN_LOAD_SITE[0]:GAIN_LOAD_SITE[0] + 4],

          "0x2A1EE ld.h 0x746c[tp] -- the forward gain READS 0xC646C on this image (no V57 decouple)")

    ptrs = [u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)]

    check(len(set(ptrs)) == 28 and all(START <= p < END for p in ptrs), "28 distinct in-range map records")

    check(all(u16(base, p) == MAP_N and tuple(rec(base, p, MAP_N)[0]) == MAP_X for p in ptrs), "every record n == 10, X == stock")

    check(all(base[p:p + 42] == stock[p:p + 42] for p in ptrs), "every base map record == STOCK (V37 never touched the map)")

    check(tuple(rec(base, ptrs[LIVE_SLOT], MAP_N)[1]) == LIVE_Y_STOCK, f"live slot {LIVE_SLOT} Y == stock {LIVE_Y_STOCK}")

    with contextlib.redirect_stdout(io.StringIO()):

        b_ok = walk(bytes(base)) == 0 and walk_all_blocks(bytes(base)) == 0

    check(b_ok, "base CRC: bootloader replay 49/49 and full chain 50/50")



    code = bytearray(base)

    print("\n  [1] [C] GAIN AND CLAMPS -> STOCK")

    for a, v37v, stv, note in REVERTS:

        struct.pack_into("<H", code, a, stv)

        check(u16(code, a) == stv == u16(stock, a), f"0x{a:05X}: {v37v} -> {stv} == stock  ({note})")



    print("\n  [2] [A] ASSIST MAP -> twice the small-signal slope, straight to X = 240, all 28 records")

    changed = 0

    for s, p in enumerate(ptrs):

        X, Y = rec(base, p, MAP_N)

        newY = [line_y(Y[1], x) for x in X]

        for i, v in enumerate(newY):

            struct.pack_into("<h", code, p + 2 + 2 * MAP_N + 2 * i, v)

        gX, gY = rec(code, p, MAP_N)

        changed += sum(1 for i in range(MAP_N) for k in (0, 1)

                       if code[p + 2 + 2 * MAP_N + 2 * i + k] != base[p + 2 + 2 * MAP_N + 2 * i + k])

        ok = gX == X and gY == newY and gY[0] == 0 and all(gY[i + 1] > gY[i] for i in range(MAP_N - 1)) and max(gY) < 32767

        ok &= gY[1] == 2 * Y[1]                                    # exactly 2x at the first knot, every record

        if s == LIVE_SLOT:

            ok &= tuple(gY) == LIVE_Y_NEW

        check(ok, f"slot {s:2d} rec 0x{p:05X}: Y1 {Y[1]:3d} -> {gY[1]:3d}, top {Y[-1]:3d} -> {gY[-1]:4d}   "

                  f"{'LIVE ' if s == LIVE_SLOT else ''}{gY}")

    check(252 <= changed <= 504 and all(code[p + 2 + 2 * MAP_N:p + 4 + 2 * MAP_N] == bytes(2) for p in ptrs),

          f"{changed} map bytes changed: every Y[1..9] knot of all 28 records moved, Y[0] = 0 untouched everywhere")

    live = ptrs[LIVE_SLOT]

    mx, my = rec(code, live, MAP_N)

    check(all(GM.lkas_rate_lerp(mx, my, i) == 4 * i for i in range(0, 241)),

          "golden-model integer LERP walk on the live record == 4 * idx for EVERY idx 0..240 (no cap, exact)")

    check(all(GM.lkas_rate_lerp(MAP_X, LIVE_Y_STOCK, i) == 2 * i for i in range(0, 13)) and GM.lkas_rate_lerp(MAP_X, LIVE_Y_STOCK, 240) == 172,

          "stock live record: slope 2/idx on the first segment, saturates at 172 -- the shape being replaced")



    print(f"\n  [3] [B] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")

    struct.pack_into("<H", code, FB_CELL, FB_NEW)

    check(u16(code, FB_CELL) == FB_NEW, f"0xC62E6 == {FB_NEW}")

    r0, r1 = FB_STOCK / (32 * 172), FB_NEW / (32 * 960)

    check(abs(r1 - r0) < 2e-5, f"Honda's setpoint:feedback ratio {r0:.4f} held at the new top ({r1:.4f})")

    check(all(is_ld_hu(code, a) and code[a:a + 4] == stock[a:a + 4] for a in FB_SITES),

          "all 3 readers of 0xC62E6 are ld.hu (unsigned) and byte-stock -> 42865 > 32767 is safe")

    with contextlib.redirect_stdout(io.StringIO()):

        mid = walk_all_blocks(bytes(code))

    check(mid == 6, f"before CRC recompute exactly the 6 touched blocks fail ({mid}) -- the edits landed where expected and nowhere else")



    print("\n  [4] CRC TRAILERS")

    for b0, b1 in CRC_BLOCKS:

        old = u32(code, b1)

        new = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF

        struct.pack_into("<I", code, b1, new)

        print(f"      [0x{b0:05X},0x{b1:05X}) @0x{b1:05X}: 0x{old:08X} -> 0x{new:08X}")

    with contextlib.redirect_stdout(io.StringIO()):

        c_ok = walk(bytes(code)) == 0 and walk_all_blocks(bytes(code)) == 0

    check(c_ok, "built image CRC: bootloader replay 49/49 and full chain 50/50")



    print("\n  [5] FULL-FILE DIFFS")

    d_base = [i for i in range(START, END) if code[i] != base[i]]

    allow = {a for a, *_ in REVERTS} | {a + 1 for a, *_ in REVERTS} | {FB_CELL, FB_CELL + 1}

    for p in ptrs:

        allow |= {p + 2 + 2 * MAP_N + k for k in range(2, 2 * MAP_N)}        # Y[1..9]

    allow |= {b1 + k for _, b1 in CRC_BLOCKS for k in range(4)}

    check(set(d_base) <= allow, f"vs V37: {len(d_base)} bytes, every one a reverted cell, a map Y knot (i >= 1), 0xC62E6 or a CRC trailer")

    check(not any(START <= i < 0xC0000 for i in d_base), "vs V37: ZERO code bytes changed (nothing below 0xC0000)")

    d_stock = [i for i in range(START, END) if code[i] != stock[i]]

    print(f"      vs STOCK: {len(d_stock)} bytes differ")

    runs = []

    for i in d_stock:

        if runs and i == runs[-1][1] + 1:

            runs[-1][1] = i

        else:

            runs.append([i, i])

    for a, b in runs:

        print(f"         0x{a:05X}-0x{b:05X} ({b - a + 1:3d} B)  stock {stock[a:b + 1].hex()[:24]}  v37a {bytes(code[a:b + 1]).hex()[:24]}")

    for a, _, stv, _ in REVERTS:

        check(u16(code, a) == u16(stock, a) == stv, f"0x{a:05X} == stock {stv} on the built image")

    carried = [(0xC64B4, 5), (0xC61C0, 6), (0xC64DE, 1), (0xC674E, 4), (0xC675A, 4), (0xC6768, 6), (0xC6598, 8), (0xC65AC, 8), (0xC65C4, 12), (0x13109, 1), (0x14120, 1)]

    check(all(code[a:a + n] == base[a:a + n] for a, n in carried), "V36/V37 debounce+DTC, EME ramp, corridor, boost floor, PN bytes all carried from V37 byte-identical")

    check(bytes(code[0xC4B34:0xC4BD8]) == b"\xff" * 164 and code[0x55C0E:0x55C12] == stock[0x55C0E:0x55C12],

          "no telemetry cave, no hook: pre-V53 image, nothing added")



    print("\n  [6] THE DELIVERED SURFACE, FROM THE THREE IMAGES (fb = 0 bound; cold-boot march through the golden model)")

    idxs = (0, 6, 12, 24, 32, 48, 60, 64, 86, 87, 96, 120, 160, 200, 238, 240)

    S = {nm: surface(im, idxs) for nm, im in (("stock", stock), ("V37", base), ("V37A", code))}

    print("        idx |  stock sp    P      T  |   V37  sp    P      T  |  V37A  sp     P      T")

    for i in idxs:

        row = f"        {i:3d} |"

        for nm in ("stock", "V37", "V37A"):

            r = S[nm][i]

            row += f"  {r['sp']:5d} {r['P']:6d} {r['T']:6d}  |"

        print(row)

    t_rail = S["V37A"][240]["T"]

    check(S["V37A"][240]["P"] == u16(code, 0xC61BC) and 400 <= t_rail <= 420,

          f"V37A at full demand: P railed at {u16(code, 0xC61BC)}, delivered T = {t_rail} == Honda's rail (stock gain 891)")

    check(S["V37"][240]["T"] > 1.9 * S["stock"][240]["T"], f"V37's full-demand torque {S['V37'][240]['T']} ~= 2x stock's {S['stock'][240]['T']} -- the constant it replaces")

    check(S["V37A"][12]["sp"] == 2 * S["stock"][12]["sp"] and S["V37A"][60]["sp"] == 240,

          "V37A reference == 2x stock at idx 12; 240 counts (= the stock fb clamp 7680/32) at idx 60")

    rail_from = next(i for i in range(0, 241) if GM.lkas_rate_pid_surface(i, cal_for(code))["P"] >= u16(code, 0xC61BC))

    stock_rails = any(GM.lkas_rate_pid_surface(i, cal_for(stock))["P"] >= u16(stock, 0xC61BC) for i in (120, 200, 240))

    check(60 <= rail_from <= 66 and not stock_rails, f"P rails from idx {rail_from} at a stalled wheel on V37A (Kp climbs 248 -> 512 across idx 0..68); stock never rails (14964 < 15360 at idx 240)")

    # the fb-clamp consequence, in the model: at the stock clamp the error can't change sign above sp 240

    c_old = replace(cal_for(code), fb_clamp=FB_STOCK)

    e_old = 32 * 960 - min(10 ** 9, c_old.fb_clamp)

    e_new = 32 * 960 - cal_for(code).fb_clamp

    check(e_old > 0 and e_new < 0, f"at full reference: E can never go negative with the stock clamp (min E {e_old}); it can with 42865 (min E {e_new})")



    print("\n  [7] ENCODE, READBACK, WRITE")

    headers = V37.make_tva_headers(parse_x31(gzip.decompress(open(V37.TEMPLATE_T2F, "rb").read())))

    window = bytes(code[START:END])

    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [window.translate(enc)])

    back = bytes(parse_x31(rwd)["encs"][0]).translate(dec)

    check(back == window, "rwd payload decrypts to the built window (cipher re-derived)")

    full = V37.full_image(back)

    with contextlib.redirect_stdout(io.StringIO()):

        f_ok = walk(full) == 0 and walk_all_blocks(full) == 0

    check(f_ok, "decoded rwd image CRC 49/49 + 50/50")

    check(tuple(rec(full, live, MAP_N)[1]) == LIVE_Y_NEW and u16(full, FB_CELL) == FB_NEW and u16(full, 0xC646C) == 891

          and u16(full, 0xC61B2) == 512 and u16(full, 0xC61B4) == 512, "end state re-read from the DECODED rwd: map, clamp, gain, clamps")

    check(full.count(b"39990-TVA,A160") == 2 and full.count(b"39990-TVA-A160") == 0, "part number bytes as V37")



    print(f"\n  CHECKS {_checks[1]}/{_checks[0]}")

    if _checks[1] != _checks[0]:

        print("  *** FAIL -- not writing ***")

        return 1

    if not WRITE:

        print("  (ACCORD_V37A_WRITE=0: not writing)")

        return 0

    os.makedirs(RWD_DIR, exist_ok=True)

    out = os.path.join(RWD_DIR, f"39990-TVA,A160-{LABEL}-{TAG}-0x{START:X}-0x{END:X}.rwd")

    open(out, "wb").write(rwd)

    open(BIN_OUT, "wb").write(full)

    print(f"  WROTE {out}\n        sha256 {hashlib.sha256(rwd).hexdigest()}")

    print(f"  WROTE {BIN_OUT}\n        sha256 {hashlib.sha256(full).hexdigest()}")

    return 0





if __name__ == "__main__":

    sys.exit(main())

