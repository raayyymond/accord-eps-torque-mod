"""Build V39: V38 plus a narrow direct Sensor-B torque-rate assist guard.

V38 is fault-free on-car, but hard turns show an apparent feedback limit. Targeted Ghidra tracing found
two independent mechanisms that can explain it:

1. The runtime governor gp-0x4f64 falls with normalized motor electrical-angle rate. Its A160 table is
   already 4607 counts at axis z=1318. The assist-inclusive aggregate can reach the first governor and
   gp-0x6acc can conservatively reach 7322 after compensation. V39 deliberately leaves the governor,
   its budget minimum, downstream clamps, and every calibration byte unchanged.
2. FUN_0003aa2c computes an inline assist lane r24 from gp-0x4f62, a four-sample finite difference of
   Sensor-B column torque. Positive Q10 gain can amplify a short inertial torque impulse to +/-8192
   before it is summed with the LKAS lane r7. The derivative producer runs on 5/16 task phases and the
   aggregator on 4/16, making this direct sampled feedback lane the strongest static match for the
   reported audible tens-of-Hz vibration under high LKAS torque.

V39 is a discriminating experiment for mechanism 2. In the normal/full aggregator mode only:

    if (u16(gp-0x6a62) < u16(tp+0x7312)       # below existing strong-driver threshold 320
        and abs(r7_lkas) >= 417):              # exact lower V9 full-scale magnitude
        r24_torque_rate = 0                    # both signs; r26 remains live

Why 417: stock V9 clips its setpoint to 15360 and applies Q15 gain 891. V850 `sar` gives +417 for
+15360 and -418 for -15360, so 417 is the exact lower full-scale magnitude and includes 100% stock torque
in both directions. A threshold of the rounded prose value 418 would miss the +417 direction. `r7` is the
LKAS-internal mixer output, not the raw comma command, so other internal terms can move activation.
When LKAS is absent/moderate or voted driver torque is >=320 (including the 0xFFFF invalid sentinel),
torque arithmetic remains stock V38 (with added hook/cave execution latency). Static boost, adaptive
inline lane r26, damping, friction, resonance, return-to-center, driver sensing, openpilot override,
governor, and EME guards all remain live.

The broader all-sign suppression supersedes the initial opposing-only V39 draft after the operator
separated two on-car symptoms: a several-Hz hard-turn ratchet and a much more common tens-of-Hz audible
vibration at high LKAS torque across low and high road speeds. Strong driver-side torque can move the
wheel quickly through the same downstream motor loop without either symptom, contradicting an intrinsic
"motor cannot make torque while moving" limit. This build does not claim to solve the slower ratchet.

Patch, Ghidra-disassembled from a temporary V38 copy:

    0x3ac78: ld.h -0x6bd0[gp],r9  -> jr 0xc4b34
    0xc4b34..0xc4b5f: 44-byte guard, displaced load, jr 0x3ac7c

The patch mutates r24 before its live add @0x3acca and its later diagnostic/shadow store. Scratch r6/r8
are overwritten before their next original uses; r7/r9/r16/r22/r23/r26/r28/gp/tp/lp are preserved.
Both edits live in main CRC block [0x13000,0xc4ffc). V39-vs-V38 must be exactly 52 changed bytes: hook
(4), cave (44), and trailer CRC (4). Study artifact; no flash operation is performed by this script.
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

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V39 builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk


START, END = 0x13000, 0x100000
V38_PLAIN = plain_image_path("_v38_plain_image.bin")
V38_RWD = os.path.join(
    RWD_DIR,
    "39990-TVA,A160-V38-LKAS-4x-V37guards-softwall5120-float5-setpoint16384-0x13000-0x100000.rwd",
)
V38_SHA256 = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
V38_RWD_SHA256 = "c6fdb297635b43681d7692ebf86de2071bd687566bb96ff0ee06977cc4d4b990"
V39_SHA256 = "43754b39bed7d2911a4d2e6964cef3f6d6ce5329ad442ff2be869172291f890d"
V39_RWD_SHA256 = "1e9b5ea8b91e43b715ecdf7e7888f83746b5125975ed094040ce64fb4262d505"
EXPECTED_HEADERS = [
    (b"#", [b"\x00"]),
    (b"?", [b"A1"]),
    (b"/", [b"39990-TVA-A110", b"39990-TVA,A160"]),
    (b"!", [b"001100121020", b"001100121020"]),
    (b"&", [b"BF109E"]),
    (b"%", [b"30"]),
]

V39_TAG = "LKAS-4x-V38guards-direct-rate-off417-driver320"
V39_OUT = os.path.join(
    RWD_DIR, f"39990-TVA,A160-V39-{V39_TAG}-0x{START:X}-0x{END:X}.rwd"
)
BIN_OUT = plain_image_path("_v39_plain_image.bin")

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

HOOK_ADDR = 0x3AC78
HOOK_OLD = bytes.fromhex("24 4f 30 94")             # ld.h -0x6bd0[gp],r9
HOOK_NEW = bytes.fromhex("88 07 bc 9e")             # jr 0x000c4b34
V9_FULL_SCALE_POSITIVE = (15360 * 891) >> 15
V9_FULL_SCALE_NEGATIVE = (-15360 * 891) >> 15
DIRECT_RATE_LKAS_THRESHOLD = min(abs(V9_FULL_SCALE_POSITIVE), abs(V9_FULL_SCALE_NEGATIVE))
assert (V9_FULL_SCALE_POSITIVE, V9_FULL_SCALE_NEGATIVE, DIRECT_RATE_LKAS_THRESHOLD) == (417, -418, 417)
CAVE_ADDR = 0xC4B34
CAVE_NEW = bytes.fromhex(
    "e4 37 9f 95 "  # ld.hu -0x6a62[gp],r6
    "e5 47 13 73 "  # ld.hu 0x7312[tp],r8
    "e8 31 "        # cmp r8,r6
    "d9 0d "        # bnc 0xc4b58: max torque >= 320 -> bypass
    "07 30 "        # mov r7,r6
    "e0 31 "        # cmp r0,r6
    "ae 05 "        # bge 0xc4b48
    "80 31 "        # subr r0,r6: abs(r7)
    "06 06 5f fe "  # addi -0x1a1,r6,r0: compare |LKAS| against V9 full-scale 417
    "e6 05 "        # blt 0xc4b58: moderate LKAS -> bypass
    "18 30 "        # mov r24,r6: retain original r24 in scratch for the legacy tail
    "00 c0 "        # mov r0,r24: suppress both signs of the direct torque-rate lane
    "e0 31 "        # cmp r0,r6
    "ae 05 "        # bge 0xc4b58: legacy sign branch; r24 is already zero
    "00 c0 "        # mov r0,r24: legacy negative-sign path, now redundant
    "24 4f 30 94 "  # displaced ld.h -0x6bd0[gp],r9
    "b7 07 20 61"   # jr 0x0003ac7c
)
CAVE_END = CAVE_ADDR + len(CAVE_NEW)
assert len(CAVE_NEW) == 44 and CAVE_END == 0xC4B60
assert struct.unpack_from("<h", CAVE_NEW, 0x16)[0] == -DIRECT_RATE_LKAS_THRESHOLD

MAIN_BLOCK = (0x13000, 0xC4FFC)
V38_MAIN_CRC = 0xCC2134EF
V39_MAIN_CRC = 0x7CCB9546


def full_image(window):
    image = bytearray(b"\xff" * 0x100000)
    image[START:END] = window
    return bytes(image)


def assert_x31_checksum(raw, label):
    stored = struct.unpack_from("<I", raw, len(raw) - 4)[0]
    calculated = sum(raw[:-4]) & 0xFFFFFFFF
    assert calculated == stored, f"{label} x31 checksum: 0x{calculated:08X} != 0x{stored:08X}"


def assert_crc_chain(code, label):
    """Strict companion to verbose walk(): require the TVA chain to reach main exactly once in 49 blocks."""
    region_start, region_end = START, END
    start_page, num_pages = struct.unpack_from("<HH", code, region_end - 8)
    block_start = start_page << 12
    block_length = (num_pages << 12) - 4
    visited = set()
    bridged = False
    blocks = 0

    while True:
        assert block_start not in visited, f"{label}: CRC chain loop at 0x{block_start:X}"
        visited.add(block_start)
        assert block_start >= 8 and block_length >= 0, f"{label}: invalid block geometry"
        trailer = block_start + block_length
        assert trailer + 4 <= len(code), f"{label}: block 0x{block_start:X} out of bounds"
        calculated = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        stored = struct.unpack_from("<I", code, trailer)[0]
        assert calculated == stored, \
            f"{label}: CRC mismatch block 0x{block_start:X}: 0x{calculated:08X} != 0x{stored:08X}"
        blocks += 1

        if block_start == region_start:
            break
        if block_start == 0xC6000:
            assert not bridged, f"{label}: duplicate C6000 bridge"
            bridged = True
            block_start, block_length = region_start, 0xB1FFC
            continue

        next_page, next_num_pages = struct.unpack_from("<HH", code, block_start - 8)
        next_start = next_page << 12
        assert next_start != block_start, f"{label}: CRC chain self-loop at 0x{block_start:X}"
        block_start = next_start
        block_length = (next_num_pages << 12) - 4
        assert blocks <= 200, f"{label}: runaway CRC chain"

    assert bridged, f"{label}: CRC chain never used C6000 bridge"
    assert blocks == 49, f"{label}: expected 49 CRC blocks, traversed {blocks}"
    return blocks


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    digest = hashlib.sha256(code).hexdigest()
    assert digest == V38_SHA256, f"unexpected V38 baseline SHA-256: {digest}"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_OLD, "V38 hook site is not stock"
    assert bytes(code[CAVE_ADDR:CAVE_END]) == b"\xff" * len(CAVE_NEW), "V38 cave is occupied"
    assert bytes(code[CAVE_END:0xC4FF0]) == b"\xff" * (0xC4FF0 - CAVE_END), "V38 cave tail moved"
    assert struct.unpack_from("<I", code, MAIN_BLOCK[1])[0] == V38_MAIN_CRC

    # V38 lineage guards: reach, V37 fault guards, matched walls, and all reachable setpoint records.
    assert struct.unpack_from("<H", code, 0xC646C)[0] == 3564
    assert struct.unpack_from("<H", code, 0xC61B4)[0] == 2048
    assert struct.unpack_from("<H", code, 0xC61B2)[0] == 2048
    assert struct.unpack_from("<H", code, 0xC6312)[0] == 320, "strong-driver threshold moved"
    assert bytes(code[0xC4124:0xC412F]) == bytes((0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0)), \
        "A160 source modes changed; gp-0x67ac reduced-mode reachability must be re-audited"
    assert all(code[a] == 0xFF for a in (0xC64B4, 0xC64B5, 0xC64B6, 0xC64B7, 0xC64B8))
    assert all(struct.unpack_from("<H", code, a)[0] == 0xFFFF for a in (0xC61C0, 0xC61C2, 0xC61C4))
    assert all(struct.unpack_from("<h", code, a)[0] == value for a, value in (
        (0xC674E, 5120), (0xC6750, 5120), (0xC675A, -5120), (0xC675C, -5120),
        (0xC6768, 5120), (0xC676A, 5120), (0xC676C, 5120),
    ))
    assert all(struct.unpack_from("<f", code, a)[0] == value for a, value in (
        (0xC6598, 5.0), (0xC659C, 5.0), (0xC65AC, -5.0), (0xC65B0, -5.0),
        (0xC65C4, 5.0), (0xC65C8, 5.0), (0xC65CC, 5.0),
    ))
    for record in (0xE4180, 0xE41A8, 0xE41F8, 0xE4220, 0xE5180, 0xE51A8, 0xE51D0, 0xE51F8):
        assert struct.unpack_from("<9H", code, record + 0x14) == (16384,) * 9

    # The competing motor-rate limiter is intentionally untouched and pinned to its exact A160 table.
    assert struct.unpack_from("<H", code, 0xC6202)[0] == 4762
    assert struct.unpack_from("<H", code, 0xC5160)[0] == 13
    for record in (0xC520C, 0xC5224):
        assert struct.unpack_from("<H", code, record)[0] == 5
        assert struct.unpack_from("<5H", code, record + 2) == (1050, 1700, 2500, 3700, 4100)
        assert struct.unpack_from("<5H", code, record + 12) == (5325, 3584, 2406, 1587, 512)
    assert struct.unpack_from("<4h", code, 0xC5030) == (-21940, -12059, -5593, -22021)
    assert struct.unpack_from("<4h", code, 0xC5038) == (-21940, -12059, -5593, -22021)
    assert_crc_chain(code, "V38 baseline")
    assert walk(bytes(code), label="V38 baseline") == 0


def patch_exact(code, address, old, new, note):
    assert len(old) == len(new)
    got = bytes(code[address:address + len(old)])
    assert got == old, f"0x{address:05X}: expected {old.hex()} got {got.hex()} ({note})"
    code[address:address + len(new)] = new
    print(f"  0x{address:05X}: {old.hex()} -> {new.hex()}  {note}")


def changed_runs(before, after):
    diffs = [i for i in range(START, END) if before[i] != after[i]]
    runs = []
    for address in diffs:
        if runs and address == runs[-1][1] + 1:
            runs[-1][1] = address
        else:
            runs.append([address, address])
    return diffs, runs


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)

    source_rwd = open(V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V38_RWD_SHA256
    assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["key"] == list(V9B["keys"])
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    assert decode is not None
    encode = invert_table(decode)
    source_window = bytes(source_info["encs"][0]).translate(decode)
    assert source_window == bytes(baseline[START:END]), "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)
    patch_exact(code, HOOK_ADDR, HOOK_OLD, HOOK_NEW, "aggregator full-mode hook -> V39 cave")
    patch_exact(code, CAVE_ADDR, b"\xff" * len(CAVE_NEW), CAVE_NEW,
                "suppress all direct r24 at |LKAS|>=417 (V9 full scale) and driver MAX<320")
    assert bytes(code[CAVE_END:0xC4FF0]) == bytes(baseline[CAVE_END:0xC4FF0])

    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    assert old_crc == V38_MAIN_CRC and new_crc == V39_MAIN_CRC
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: "
          f"0x{old_crc:08X} -> 0x{new_crc:08X}")

    allowed = set(range(HOOK_ADDR, HOOK_ADDR + len(HOOK_NEW)))
    allowed.update(range(CAVE_ADDR, CAVE_END))
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) == allowed, f"unexpected V39-vs-V38 bytes: {sorted(set(diffs) ^ allowed)}"
    assert len(diffs) == 52
    assert runs == [[HOOK_ADDR, HOOK_ADDR + 3], [CAVE_ADDR, CAVE_END - 1],
                    [MAIN_BLOCK[1], MAIN_BLOCK[1] + 3]]
    assert_crc_chain(code, "V39 plain")
    assert walk(bytes(code), label="V39") == 0

    # All non-main CRC blocks and every V38 calibration/data byte are inherited byte-for-byte.
    assert bytes(code[0xC5000:0x100000]) == bytes(baseline[0xC5000:0x100000])
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR])
    assert bytes(code[HOOK_ADDR + 4:CAVE_ADDR]) == bytes(baseline[HOOK_ADDR + 4:CAVE_ADDR])
    assert bytes(code[CAVE_END:MAIN_BLOCK[1]]) == bytes(baseline[CAVE_END:MAIN_BLOCK[1]])

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V39 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window
    readback_image = full_image(decoded)
    assert_crc_chain(readback_image, "V39 RWD readback")
    assert walk(readback_image, label="V39 RWD readback") == 0
    assert decoded[HOOK_ADDR - START:HOOK_ADDR - START + 4] == HOOK_NEW
    assert decoded[CAVE_ADDR - START:CAVE_END - START] == CAVE_NEW
    assert struct.unpack_from("<I", decoded, MAIN_BLOCK[1] - START)[0] == V39_MAIN_CRC

    print(f"  V39-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)")
    print(f"  V38 SHA-256: {V38_SHA256}")
    assert hashlib.sha256(code).hexdigest() == V39_SHA256
    assert hashlib.sha256(rwd).hexdigest() == V39_RWD_SHA256
    print(f"  V39 SHA-256: {V39_SHA256}")
    return bytes(code), rwd


def main():
    stale = [path for path in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V39-*.rwd"))
             if os.path.abspath(path) != os.path.abspath(V39_OUT)]
    for path in stale + [V39_OUT, BIN_OUT, V39_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V39 = exact on-car V38 baseline + conditional direct Sensor-B torque-rate lane guard")
    print("      guard: driver MAX < 320, |LKAS lane| >= 417 (V9 full scale), suppress r24 both signs")
    print("      governor tables/budget and all V38 calibrations remain byte-identical\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V39_OUT), exist_ok=True)
    with open(V39_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V39_OUT + ".tmp", V39_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"  WROTE {os.path.relpath(V39_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
