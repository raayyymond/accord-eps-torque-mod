"""build_v31t_tva.py - V31T = V31 (UNCHANGED) + a passive TELEMETRY piggyback on CAN 0x660.

PURPOSE (2026-06-30, operator-directed)
=========================================================================================================
We need a LIVE RAM read of the gentle-EME gate signal gp-0x6a62 (= 0xFEDF159E, the sensor-A column-torque
voter MAX) to (1) CONFIRM the gentle EME fires on the gp-0x6a62 >= cal 0xC6312 (=320) path, and (2) size a
new 0xC6312. gp-0x6a62 is a SEPARATE acquisition from the CAN STEER_TORQUE_SENSOR (sensor B = gp-0x4f60 =
0xFEDF30A0), so its scale cannot be derived statically -- it must be read on the car.

METHOD (ported from the Clarity four-frame passive-telemetry bundle, adapted to V850E2)
=========================================================================================================
The Clarity reference is SH-2A; the Accord is Renesas V850E2 -- so this is a METHOD port, not a byte copy.
Instead of adding a new CAN ID + mailbox/descriptor + a code-cave stub (the heavy four-frame path), we
PIGGYBACK an existing, already-transmitting EPS frame:

  CAN 0x660 (1632), DLC 8, built by FUN_000561b0, buffer = gp-0x1510 (0xFEDF6AF0).
  Stock 0x660 is a near-empty heartbeat: it explicitly ZEROES payload bytes 0..6 (st.b r0,-0x1510..-0x150a
  [gp]) and uses only byte 7 (gp-0x1509) for the rolling counter + 4-bit checksum.

We overwrite the byte-0..5 zero-stores with three telemetry halfword stores. The CAN counter/checksum
(FUN_00057b24, computed AFTER these stores over the buffer) covers the telemetry bytes, and the transmit
driver FUN_000541d8's re-verify reads the SAME buffer -> counter/checksum stay self-consistent and the
frame transmits exactly as today. NO new CAN ID, NO mailbox/descriptor surgery, NO code cave, NO new bytes.

  0x660 wire byte 0:1 = gp-0x6a62 (gate signal, sensor-A MAX)        little-endian u16
  0x660 wire byte 2:3 = gp-0x4f60 (sensor B / CAN STEER_TORQUE src)  little-endian s16  (scale bridge)
  0x660 wire byte 4:5 = gp-0x6a5e (sensor-A AVG / boost-curve axis)   little-endian s16
  0x660 wire byte 6   = 0 (unchanged)
  0x660 wire byte 7   = rolling counter (hi nibble) + checksum (lo nibble)  (unchanged)

THE CODE EDIT (6 instructions, EQUAL-LENGTH, in-place; zero added bytes, zero jarl re-encode, zero NOPs)
=========================================================================================================
FUN_000561b0 zeroes each payload byte inside its own di/ei critical section:
   [jarl fa42] st.b r0,-0x15NN[gp] [jarl fa72]   x7  (bytes 0..6)
We replace 6 of the single-instruction slots (bytes 0..5) with paired load/store using r15:
   slot byte0 @0x561c2 : st.b r0,-0x1510 -> ld.hu -0x6a62[gp],r15
   slot byte1 @0x561ce : st.b r0,-0x150f -> st.h  r15,-0x1510[gp]   (buf 0:1 = gp-0x6a62)
   slot byte2 @0x561da : st.b r0,-0x150e -> ld.hu -0x4f60[gp],r15
   slot byte3 @0x561e6 : st.b r0,-0x150d -> st.h  r15,-0x150e[gp]   (buf 2:3 = gp-0x4f60)
   slot byte4 @0x561f2 : st.b r0,-0x150c -> ld.hu -0x6a5e[gp],r15
   slot byte5 @0x561fe : st.b r0,-0x150b -> st.h  r15,-0x150c[gp]   (buf 4:5 = gp-0x6a5e)
   slot byte6 @0x5620a : st.b r0,-0x150a  UNCHANGED (byte6 stays 0)

r15 SURVIVES the intervening fa72/fa42 calls: FUN_0001fa42 writes only r8/r14 (its nested call
FUN_0001f98e is empty), FUN_0001fa72 writes only r12/r14 -- NEITHER touches r15. r15 is dead before
0x56232 (first stock use) so no live value is clobbered. V850 ld.hu/st.h/st.b reg,disp16[gp] are all
4-byte Format-VII, so each swap is byte-for-byte equal length. Encodings derived empirically from stock
reference instructions (st.h r0,-2[r24]=78 07 FE FF; ld.hu -0x1be0[ep],r15=FE 7F 21 E4) and re-verified
by disassembling the built image in Ghidra.

LOCKSTEP / SAFETY
=========================================================================================================
- The code edit is in the CAN-TX content builder ONLY. It does NOT touch command math, torque tables,
  motor-current control, the soft-EME rate-shaper/walls (FUN_00042af8/FUN_00043e44), the engage SM, or any
  fault gate. The int/float consistency monitors do not read this packer.
- All V31 calibration edits (GAIN 1782, clamps 1024, ramp 0x1B, corridor x4 int+float, BOOST FLOOR 4096
  int+float, PN) are RETAINED UNCHANGED, so the car drives EXACTLY as the currently-flashed V31 -- we
  observe the gentle EME in the wild while logging gp-0x6a62.
- Edit lies in the main CRC block [0x13000,0xC4FFC) (CRC @0xC4FFC), already recomputed by the V31 builder.

SAFETY: STUDY ARTIFACT. No flash until the operator names file + bus (kit iron rule). Before flashing,
confirm via a passive CAN capture (tools/comma4_panda_test.py) that 0x660 transmits and that nothing on the
bus consumes 0x660 payload bytes 0..6 (stock = all zero).
"""
import os, sys, gzip, struct, zlib

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
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
BIN_OUT      = plain_image_path("_v31t_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V31 CALIBRATION EDITS (ALL RETAINED, UNCHANGED) =====================
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

# ===================== V31T NEW: passive telemetry code edit on CAN 0x660 =====================
# 6 in-place, equal-length (4-byte) V850E2 instruction swaps in FUN_000561b0 (0x660 content builder).
# (file_offset, stock_bytes, new_bytes, note)
CODE_PATCHES = [
    (0x561C2, bytes.fromhex("4407F0EA"), bytes.fromhex("E47F9F95"),
     "byte0 slot: st.b r0,-0x1510[gp] -> ld.hu -0x6a62[gp],r15  (load gate signal gp-0x6a62=0xFEDF159E)"),
    (0x561CE, bytes.fromhex("4407F1EA"), bytes.fromhex("647FF0EA"),
     "byte1 slot: st.b r0,-0x150f[gp] -> st.h  r15,-0x1510[gp]   (0x660 buf 0:1 = gp-0x6a62, LE u16)"),
    (0x561DA, bytes.fromhex("4407F2EA"), bytes.fromhex("E47FA1B0"),
     "byte2 slot: st.b r0,-0x150e[gp] -> ld.hu -0x4f60[gp],r15  (load sensorB/CAN-torque gp-0x4f60=0xFEDF30A0)"),
    (0x561E6, bytes.fromhex("4407F3EA"), bytes.fromhex("647FF2EA"),
     "byte3 slot: st.b r0,-0x150d[gp] -> st.h  r15,-0x150e[gp]   (0x660 buf 2:3 = gp-0x4f60, LE s16)"),
    (0x561F2, bytes.fromhex("4407F4EA"), bytes.fromhex("E47FA395"),
     "byte4 slot: st.b r0,-0x150c[gp] -> ld.hu -0x6a5e[gp],r15  (load sensorA-avg gp-0x6a5e=0xFEDF15A2)"),
    (0x561FE, bytes.fromhex("4407F5EA"), bytes.fromhex("647FF4EA"),
     "byte5 slot: st.b r0,-0x150b[gp] -> st.h  r15,-0x150c[gp]   (0x660 buf 4:5 = gp-0x6a5e, LE s16)"),
]
# byte6 zero-store @0x5620A (st.b r0,-0x150a[gp] = 44 07 F6 EA) MUST stay stock (byte6 = 0).
CODE_STOCK_GUARD = [
    (0x5620A, bytes.fromhex("4407F6EA"), "byte6 zero-store st.b r0,-0x150a[gp] -- MUST stay stock"),
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
    (0x13000, 0xC4FFC),   # covers BOTH the PN bytes and the 0x561xx telemetry code edit
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V31 (unchanged) + passive telemetry piggyback on CAN 0x660 (FUN_000561b0)")
    code = bytearray(code_stock)

    # pre-patch guards (cal arms + the code region we touch + sites we must NOT touch)
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
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF (no caves)"

    # V31 calibration patches (retained, unchanged)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)
    # V31T telemetry code edit
    print("  --- telemetry code edit (CAN 0x660 piggyback) ---")
    patch_code(code, CODE_PATCHES)

    # post-patch guards (untouched arms still stock; protected code sites still stock)
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
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int corridor GUARD @0x{addr:X} ({note})"
    for addr, expect, note in INT_BOOST_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int boost GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_BOOST_GUARD_I:
        assert struct.unpack_from("<i", ecu_plain, addr - START)[0] == expect, f"float boost N GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_BOOST_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"float boost X GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"LERP_B stock GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_SPEEDGAIN_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"speed-gain stock GUARD @0x{addr:X} ({note})"
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
    print("V31T = V31 (gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN)")
    print("       + PASSIVE TELEMETRY piggyback on CAN 0x660 (FUN_000561b0):")
    print("         buf 0:1=gp-0x6a62 (gate)  2:3=gp-0x4f60 (sensorB)  4:5=gp-0x6a5e (sensorA-avg)\n")
    build("V31T", code, headers, tag="telem-0x660-piggyback-sensorA-gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
