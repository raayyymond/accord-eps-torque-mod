"""builds/telemetry/build_tier1_telem_tva.py - TIER-1 telemetry: V31 base + CAN 0x660 gentle-EME gate signals + 100Hz rate bump.

WHAT THIS IS (2026-07-08)
=========================================================================================================
Tier-1 comma-visible RAM telemetry for the gentle-EME diagnosis. Identical to V31T (V31 + a passive
telemetry piggyback on CAN 0x660's builder FUN_000561b0) EXCEPT:
  (1) the 3rd logged signal is gp-0x4f68 (Gate-5 |torque|) instead of gp-0x4f60 (CAN-torque source),
      because gp-0x4f60 is already recoverable from the comma-visible 399 STEER_TORQUE; and
  (2) ONE data byte bumps 0x660's TX interval from 20 ticks (~5 Hz) to 1 tick (~100 Hz) so the ~90 ms
      gentle-EME cut is sampled ~9x instead of <1x.

0x660 PAYLOAD (little-endian, DLC 8):
  byte 0:1 = gp-0x6a62 (0xFEDF159E)  voter-MAX  column torque   -> the 0xC6312 (V33) decider gate signal
  byte 2:3 = gp-0x6a5e (0xFEDF15A2)  voter-AVG  column torque   -> the 0xC62FE (V35) deliver-commit gate signal
  byte 4:5 = gp-0x4f68 (0xFEDF3098)  |column torque| clamp       -> the Gate-5 (0xC61EA=4096) signal
  byte 6   = 0 (unchanged)
  byte 7   = rolling counter (hi nibble) + Honda 4-bit checksum (lo nibble)  (unchanged)

On a V31 BASE both torque gates are ARMED at stock threshold 320 (0xC6312 on MAX, 0xC62FE on AVG), so a
capture shows WHICH voter signal crosses 320 at the instant of the cut -- the confirmation V32/V33/V34/V35
never had. Correlate against comma-visible 399 (STEER_TORQUE / gp-0x4f60) + 427 (STEER_MOTOR_TORQUE = the
delivered-torque cut) + STEER_STATUS.

*** VISIBILITY CAVEAT -- READ BEFORE FLASHING (2026-07-08 analysis) ***
=========================================================================================================
This build's telemetry only helps IF CAN 0x660 reaches the comma-tapped bus. Current evidence says it
probably does NOT: the EPS software schedules + transmits 0x660 on FCN0 exactly like 399 (same mailbox 6,
same suppression mask 0xB71CC=0xC1, active-from-ROM 0xB7D00[4]=1), yet 0x660 -- and 0x19F, which the same
table clocks at 100 Hz -- are ABSENT from a raw comma scan (38409 frames/10 s, no DBC filter). A 100 Hz
FCN0 frame that never reaches the comma is the fingerprint of an EXTERNAL GATEWAY that forwards only
{399,427,0x14A} onto the bus the comma taps. That gateway is NOT in this firmware and cannot be overridden
by any EPS edit. THEREFORE THIS BUILD IS PRIMARILY A VISIBILITY EXPERIMENT:
  FLASH -> `tmux kill-server; python3 comma4_can_inventory.py` -> look for ID 0x660 at ~100 Hz on bus 1.
    * 0x660 APPEARS  -> not gateway-filtered; you now have working telemetry (decode buf 0:1/2:3/4:5).
    * 0x660 ABSENT   -> gateway-filtered; the 0x660-repurpose path is dead. Pivot to (a) telemetry in
                        spare bits of a whitelisted frame 399/427/0x14A, or (b) K-line readout of RAM via
                        KWP SID 0xF4 (needs a K-line adapter on OBD pin 7, not the comma).
The build is SAFE either way: it drives byte-identical to the currently-studied V31 (telemetry is in the
0x660 content builder only; no command/torque/motor/soft-EME/engage-SM/fault code is touched).

THE CODE EDIT (6 in-place, equal-length V850E2 swaps in FUN_000561b0; encodings image-verified)
=========================================================================================================
FUN_000561b0 zeroes payload bytes 0..6 as `st.b r0,-0x15NN[gp]` inside di/ei. We replace bytes 0..5's
zero-stores with 3 load/store pairs via r15 (r15 survives the di/ei wrappers FUN_0001fa42/72 -- verified
in V31T). ld.hu/st.h reg,disp16[gp] are all 4-byte Format-VII == equal length, zero added bytes.
  gp-0x6a62 load E4 7F 9F 95, gp-0x6a5e load E4 7F A3 95  (both from V31T, Ghidra-verified)
  gp-0x4f68 load E4 7F 99 B0  (derived; verified against stock `ld.hu -0x4f68,gp,r12`=e46799b0 @0x2438c)
  st.h r15,-0x1510/-0x150e/-0x150c[gp] = 64 7F F0/F2/F4 EA  (from V31T, Ghidra-verified)

SAFETY: STUDY ARTIFACT. No flash until the operator names file + bus (kit iron rule).
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
import os, sys, gzip, struct, zlib

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR
BIN_OUT      = plain_image_path("_tier1_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V31 CALIBRATION EDITS (base; ALL RETAINED, UNCHANGED from V31/V31T) =====================
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME ramp)"),
]
CORRIDOR_PATCHES = [
    (0xC674E,  1024,  CORRIDOR_INT, "INT dir1 Y[0] tp+0x774e  UPPER corridor  +1024->+4096 (x4)"),
    (0xC6750,  1024,  CORRIDOR_INT, "INT dir1 Y[1] tp+0x7750  UPPER corridor  +1024->+4096 (x4)"),
    (0xC675A, -1024, -CORRIDOR_INT, "INT dir2 Y[0] tp+0x775a  LOWER corridor  -1024->-4096 (x4)"),
    (0xC675C, -1024, -CORRIDOR_INT, "INT dir2 Y[1] tp+0x775c  LOWER corridor  -1024->-4096 (x4)"),
]
CORRIDOR_GUARD = [
    (0xC6748,     2, "INT TABLE1 N (count)"),
    (0xC674A, -8192, "INT TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "INT TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "INT TABLE2 N (count)"),
    (0xC6756,  1024, "INT TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "INT TABLE2 X[1] velocity bkpt"),
]
FLOAT_CORRIDOR_PATCHES = [
    (0xC6598,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[0] tp+0x7598  corridor mirror  +1.0->+4.0 (x4)"),
    (0xC659C,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[1] tp+0x759c  corridor mirror  +1.0->+4.0 (x4)"),
    (0xC65AC, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[0] tp+0x75ac  corridor mirror  -1.0->-4.0 (x4)"),
    (0xC65B0, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[1] tp+0x75b0  corridor mirror  -1.0->-4.0 (x4)"),
]
FLOAT_CORRIDOR_GUARD_I = [
    (0xC658C, 2, "FLOAT dir1 N (count, int32)"),
    (0xC65A0, 2, "FLOAT dir2 N (count, int32)"),
]
FLOAT_CORRIDOR_GUARD_F = [
    (0xC6590, -8.0, "FLOAT dir1 X[0]"),
    (0xC6594, -1.0, "FLOAT dir1 X[1]"),
    (0xC65A4,  1.0, "FLOAT dir2 X[0]"),
    (0xC65A8,  8.0, "FLOAT dir2 X[1]"),
]
INT_BOOST_FLOOR_PATCHES = [
    (0xC6768,    0, BOOST_INT, "INT boost Y[0] tp+0x7768  rate<=700  0->4096   (FLOOR)"),
    (0xC676A, 1536, BOOST_INT, "INT boost Y[1] tp+0x776a             1536->4096 (FLOOR)"),
    (0xC676C, 2048, BOOST_INT, "INT boost Y[2] tp+0x776c             2048->4096 (FLOOR)"),
]
FLOAT_BOOST_FLOOR_PATCHES = [
    (0xC65C4, 0.0, BOOST_FLT, "FLOAT boost Y[0] tp+0x75c4  mirror  0.0->4.0 (FLOOR)"),
    (0xC65C8, 1.5, BOOST_FLT, "FLOAT boost Y[1] tp+0x75c8  mirror  1.5->4.0 (FLOOR)"),
    (0xC65CC, 2.0, BOOST_FLT, "FLOAT boost Y[2] tp+0x75cc  mirror  2.0->4.0 (FLOOR)"),
]
INT_BOOST_GUARD = [
    (0xC6760,    3, "INT boost N (count)"),
    (0xC6762,  700, "INT boost X[0] tp+0x7762"),
    (0xC6764,  800, "INT boost X[1] tp+0x7764"),
    (0xC6766, 1100, "INT boost X[2] tp+0x7766"),
]
FLOAT_BOOST_GUARD_I = [
    (0xC65B4, 3, "FLOAT boost N (count, int32)"),
]
FLOAT_BOOST_GUARD_F = [
    (0xC65B8,  700.0, "FLOAT boost X[0]"),
    (0xC65BC,  800.0, "FLOAT boost X[1]"),
    (0xC65C0, 1100.0, "FLOAT boost X[2]"),
]
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "ENVELOPE LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0"),
    (0xC6668, 1.0, "ENVELOPE LERP_B Y[1]"),
    (0xC666C, 1.0, "ENVELOPE LERP_B Y[2]"),
    (0xC6670, 1.0, "ENVELOPE LERP_B Y[3]"),
    (0xC6674, 1.0, "ENVELOPE LERP_B Y[4]"),
    (0xC6678, 1.0, "ENVELOPE LERP_B Y[5]"),
    (0xC667C, 1.0, "ENVELOPE LERP_B Y[6]"),
]
FLOAT_SPEEDGAIN_GUARD_F = [
    (0xC65F0,   2.0, "SPEED-gain float Y[0] -- stock"),
    (0xC65F8,   0.5, "SPEED-gain float Y[2] -- stock"),
]
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# ===================== TIER-1 telemetry code edit on CAN 0x660 (refined signal set) =====================
# 6 in-place, equal-length (4-byte) V850E2 instruction swaps in FUN_000561b0 (0x660 content builder).
# (file_offset, stock_bytes, new_bytes, note)
CODE_PATCHES = [
    (0x561C2, bytes.fromhex("4407F0EA"), bytes.fromhex("E47F9F95"),
     "byte0 slot: st.b r0,-0x1510[gp] -> ld.hu -0x6a62[gp],r15  (voter-MAX gp-0x6a62=0xFEDF159E, 0xC6312 gate)"),
    (0x561CE, bytes.fromhex("4407F1EA"), bytes.fromhex("647FF0EA"),
     "byte1 slot: st.b r0,-0x150f[gp] -> st.h  r15,-0x1510[gp]  (0x660 buf 0:1 = gp-0x6a62, LE u16)"),
    (0x561DA, bytes.fromhex("4407F2EA"), bytes.fromhex("E47FA395"),
     "byte2 slot: st.b r0,-0x150e[gp] -> ld.hu -0x6a5e[gp],r15  (voter-AVG gp-0x6a5e=0xFEDF15A2, 0xC62FE gate)"),
    (0x561E6, bytes.fromhex("4407F3EA"), bytes.fromhex("647FF2EA"),
     "byte3 slot: st.b r0,-0x150d[gp] -> st.h  r15,-0x150e[gp]  (0x660 buf 2:3 = gp-0x6a5e, LE u16)"),
    (0x561F2, bytes.fromhex("4407F4EA"), bytes.fromhex("E47F99B0"),
     "byte4 slot: st.b r0,-0x150c[gp] -> ld.hu -0x4f68[gp],r15  (|torque| gp-0x4f68=0xFEDF3098, Gate-5)"),
    (0x561FE, bytes.fromhex("4407F5EA"), bytes.fromhex("647FF4EA"),
     "byte5 slot: st.b r0,-0x150b[gp] -> st.h  r15,-0x150c[gp]  (0x660 buf 4:5 = gp-0x4f68, LE u16)"),
]
# byte6 zero-store @0x5620A (st.b r0,-0x150a[gp] = 44 07 F6 EA) MUST stay stock (byte6 = 0).
CODE_STOCK_GUARD = [
    (0x5620A, bytes.fromhex("4407F6EA"), "byte6 zero-store st.b r0,-0x150a[gp] -- MUST stay stock"),
]

# ===================== TIER-1 NEW: 0x660 TX rate 5 Hz -> 100 Hz (one ROM data byte) =====================
# tp-0x7364 inter-TX interval table @ 0xB7C9C, slot 4 (0x660) @ 0xB7CA0. Interval ticks; tick ~= 100 Hz
# (visible frames verify the scale: 399/idx9=1=100Hz, 427/idx7=2=50Hz, 0x14A/idx10=1=100Hz). 20 -> 1.
# Single reader FUN_0001e942 @0x1e9a8 (ld.bu -0x7364[r10],r6); no aliasing (independently byte-verified).
RATE_PATCH = [
    (0xB7CA0, 0x14, 0x01, "0x660 TX interval tp-0x7364[4] @0xB7CA0  20 ticks(~5Hz) -> 1 tick(~100Hz)"),
]
RATE_TABLE_GUARD = [   # neighbours must stay stock (proves we hit the right table slot)
    (0xB7CA5, 0x01, "399 (idx9) interval = 1 (100Hz) -- stock, proves table identity"),
    (0xB7CA3, 0x02, "427 (idx7) interval = 2 (50Hz)  -- stock, proves table identity"),
    (0xB7CA6, 0x01, "0x14A(idx10) interval = 1 (100Hz)-- stock, proves table identity"),
]

# --- NO-CODE-EDIT guard: these stock soft-EME code sites MUST remain byte-identical ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
]
CAVE_GUARD = (0xC4E00, 0x18)


def patch_cal_u(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_corridor(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<h", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_float(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<f", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6.1f} -> {new:6.1f}   {note}")


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


def patch_code(code, table):
    for addr, old, new, note in table:
        assert len(old) == len(new), f"code patch length mismatch @0x{addr:05X}"
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(f"CODE 0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}: {old.hex()} -> {new.hex()}   {note}")


def guard_s16(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_int32(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<i", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_float(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_bytes(code, table):
    for addr, expect_bytes, note in table:
        got = bytes(code[addr:addr + len(expect_bytes)])
        if got != expect_bytes:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect_bytes.hex()} got {got.hex()} ({note})")


def guard_byte(code, table):
    for addr, expect, note in table:
        if code[addr] != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect:#04x} got {code[addr]:#04x} ({note})")


def make_tva_headers(template_info):
    new = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new.append((tag, [b"39990-TVA-A110", b"39990-TVA,A160"]))
        elif tag == b"!":
            new.append((tag, [vals[0], vals[0]]))
        elif tag == b"%":
            new.append((tag, [CAN_SIG_BYTE]))
        else:
            new.append((tag, list(vals)))
    return new


def full_image(plain_window):
    img = bytearray(b"\xff" * 0x100000)
    img[START:END] = plain_window
    return bytes(img)


def recompute_crc(code, start, crc_off):
    old = struct.unpack_from("<I", code, crc_off)[0]
    new = zlib.crc32(code[start:crc_off]) & 0xFFFFFFFF
    struct.pack_into("<I", code, crc_off, new)
    print(f"  CRC [0x{start:X},0x{crc_off:X}) @0x{crc_off:X}: 0x{old:08X} -> 0x{new:08X}")


TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),
    (0x13000, 0xC4FFC),   # covers PN + the 0x561xx telemetry edit + the 0xB7CA0 rate byte
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V31 base + CAN 0x660 gentle-EME telemetry (MAX/AVG/Gate5) + 100Hz rate bump")
    code = bytearray(code_stock)

    # pre-patch guards
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_bytes(code, NO_CODE_EDIT_SITES)
    guard_bytes(code, CODE_STOCK_GUARD)
    guard_byte(code, RATE_TABLE_GUARD)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF (no caves)"

    # V31 calibration patches (base, unchanged)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)
    # Tier-1 telemetry code edit + rate bump
    print("  --- telemetry code edit (CAN 0x660 piggyback: MAX / AVG / Gate5) ---")
    patch_code(code, CODE_PATCHES)
    print("  --- 0x660 TX rate 5Hz -> 100Hz ---")
    patch_bytes(code, RATE_PATCH)

    # post-patch guards (untouched arms + protected sites still stock)
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_bytes(code, NO_CODE_EDIT_SITES)
    guard_bytes(code, CODE_STOCK_GUARD)
    guard_byte(code, RATE_TABLE_GUARD)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave tail must remain 0xFF"

    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

    # readback asserts (decode the emitted .rwd from scratch)
    assert struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0] == 1782, "GAIN lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B4 - START)[0] == 1024, "CLAMP b4 lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B2 - START)[0] == 1024, "CLAMP b2 lost"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lost"
    for addr, _, new, _ in CORRIDOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int corridor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_CORRIDOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float corridor @0x{addr:X}"
    for addr, _, new, _ in INT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int boost floor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float boost floor @0x{addr:X}"
    for addr, expect, note in CORRIDOR_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int corridor GUARD @0x{addr:X}"
    for addr, expect, note in INT_BOOST_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int boost GUARD @0x{addr:X}"
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"LERP_B stock GUARD @0x{addr:X}"
    for addr, expect_bytes, note in NO_CODE_EDIT_SITES:
        got = bytes(ecu_plain[addr - START:addr - START + len(expect_bytes)])
        assert got == expect_bytes, f"unexpected code edit @0x{addr:X} ({note})"
    # telemetry code edit present + protected code stock in the decoded .rwd
    for addr, _old, new, note in CODE_PATCHES:
        got = bytes(ecu_plain[addr - START:addr - START + len(new)])
        assert got == new, f"telemetry code edit lost @0x{addr:X} ({note}): got {got.hex()}"
    for addr, expect_bytes, note in CODE_STOCK_GUARD:
        got = bytes(ecu_plain[addr - START:addr - START + len(expect_bytes)])
        assert got == expect_bytes, f"code-stock guard @0x{addr:X} ({note}): got {got.hex()}"
    # rate bump present + neighbours stock in the decoded .rwd
    assert ecu_plain[0xB7CA0 - START] == 0x01, "0x660 rate bump lost (0xB7CA0 != 1)"
    for addr, expect, note in RATE_TABLE_GUARD:
        assert ecu_plain[addr - START] == expect, f"rate table GUARD @0x{addr:X} ({note})"
    assert bytes(ecu_plain[0xC4E00 - START:0xC4E18 - START]) == b"\xff" * 0x18, "cave region must be 0xFF (no caves)"
    pn_old = b"39990-TVA-A160"; pn_new = b"39990-TVA,A160"
    assert ecu_plain.count(pn_old) == 0 and ecu_plain.count(pn_new) == 2, "PN lost"

    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, b in runs:
        print(f"     0x{a:05X}-0x{b:05X} ({b - a + 1}B)")

    # delta vs V31T (should be: 2 changed telemetry loads + the rate byte + the 2 recomputed CRCs)
    v31t_bin = plain_image_path("_v31t_plain_image.bin")
    if os.path.exists(v31t_bin):
        v31t = open(v31t_bin, "rb").read()
        t1 = full_image(ecu_plain)
        d = [i for i in range(START, END) if t1[i] != v31t[i]]
        print(f"  Tier1-vs-V31T delta: {len(d)} bytes at {[hex(x) for x in d]}")

    if not matches or fails:
        print(f"  *** {label} self-check FAILED -- not writing ***\n")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    with open(BIN_OUT, "wb") as f:
        f.write(full_image(ecu_plain))
    print(f"  WROTE {os.path.relpath(out, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)} (1MB plain image for Ghidra verify)\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock)")
    print("TIER1 = V31 (gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN)")
    print("      + CAN 0x660 telemetry (buf 0:1=gp-0x6a62 MAX  2:3=gp-0x6a5e AVG  4:5=gp-0x4f68 Gate5)")
    print("      + 0x660 TX rate 20->1 tick (5Hz -> 100Hz)")
    print("      ** VISIBILITY EXPERIMENT: flash, then comma4_can_inventory -> is 0x660 on bus1 @100Hz? **\n")
    build("TIER1", code, headers, tag="telem-0x660-MAX-AVG-Gate5-100Hz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
