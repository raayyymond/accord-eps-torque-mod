"""
build_v49p_tva.py -- V49P = V38 + READ-ONLY POLARITY TELEMETRY (no cal/logic change).

PURPOSE
    Read the V49 flash-gate value -- the shared polarity byte gp-0x6752 (and its companion gp-0x6762) --
    off the car, WITHOUT UDS/OBD-mux, using the proven V31P CAN-spare-bits technique. A read-only cave
    packs both bytes into CAN 330 (0x14A) genuinely-spare bits; they ride the raw `can` rlog at 100 Hz.
    After driving (or just key-on) with this flashed, the operator's rlog lets the lead read the polarity
    directly and decide whether V49 (the StageC-flip damper) is a fix (gp-0x6752 == +1) or a brick (-1).

WHY THIS IS SAFE (the proven-safe telemetry cave class -- NOT the bricked control-cave class)
    * PURE OBSERVABILITY: the cave READS gp-0x6752/gp-0x6762 (never writes them) and writes only spare
      bits of the CAN-330 broadcast buffer. It inserts NO dynamics into ANY control loop -> GATE 2
      (closed-loop stability) is N/A. GATE 1: it allocates NO scratch RAM (unlike V31P's flag byte) -- it
      only touches CAN-330 byte4[7:3]/byte7[7:6], confirmed never-written elsewhere + undefined in the
      openpilot DBC (V31P audit). This is the class flashed + DRIVEN fine as V31P/V31P-V2; the bricks
      (V24/V27/V48B) were all CONTROL caves. All V38 cals + code are byte-identical -> car drives as V38.

TECHNIQUE (identical mechanics to build_v31p_v2_tva.py, verified there)
    CHANNEL: CAN 330 / 0x14A (DLC8, 100 Hz, gateway-forwarded/comma-visible), builder FUN_00055a98,
    buffer 0xFEDF6AE8. The Honda 4-bit counter/checksum (FUN_00057b24 @0x55c18) is computed AFTER the
    pack hook, so it covers the telemetry bits and openpilot validates the frame normally.
    HOOK: site 0x55c0e `movea -0x1518,gp,r6` -> `jarl pack_polarity,lp` (pack helper re-executes the
    displaced movea, then `jmp [lp]` -> 0x55c12; transparent except the pack). Clobbers only r6/r7 (a
    subset of V31P's proven-safe r6/r7/r8).
    WIRE PAYLOAD (V49P adds; all other 330 bits stock):
      byte4 bits 7:3 = (gp-0x6752 & 0x1F)   -> +1 reads 0b00001, -1 (0xFF) reads 0b11111
      byte7 bits 7:6 = (gp-0x6762 & 0x03)   -> +1 reads 0b01,    -1 (0xFF) reads 0b11
    DECODE (from the raw rlog): CAN 330 byte4>>3 & 0x1F = gp-0x6752 low-5; byte7>>6 & 0x3 = gp-0x6762 low-2.

CAVE ENCODING (pack_polarity, 54 bytes @0xC4B34). Every instruction reuses a V31P byte-verified encoding;
    only the two ld.bu displacements are new and were cross-checked against V31P's disp pattern
    ((-disp & 0xFFFE)|1) -- matches 0xEB01/0xEAED/0xEAEF exactly. STILL re-disassemble the built image in
    Ghidra before flash (kit rule for any cave).

SAFETY: STUDY ARTIFACT. UNFLASHED. Flash only on explicit operator instruction naming file + bus.
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V49P builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks


START, END = 0x13000, 0x100000
V38_PLAIN = str(plain_image_path("_v38_plain_image.bin"))
V38_RWD = os.path.join(
    RWD_DIR,
    "39990-TVA,A160-V38-LKAS-4x-V37guards-softwall5120-float5-setpoint16384-0x13000-0x100000.rwd",
)
V38_SHA256 = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
V38_RWD_SHA256 = "c6fdb297635b43681d7692ebf86de2071bd687566bb96ff0ee06977cc4d4b990"
EXPECTED_HEADERS = [
    (b"#", [b"\x00"]),
    (b"?", [b"A1"]),
    (b"/", [b"39990-TVA-A110", b"39990-TVA,A160"]),
    (b"!", [b"001100121020", b"001100121020"]),
    (b"&", [b"BF109E"]),
    (b"%", [b"30"]),
]

V49P_TAG = "polarity-telem-gp6752-gp6762-can330-caveC4B34-onV38"
V49P_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V49P-{V49P_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v49p_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

CAVE_BASE = 0xC4B34
HOOK_ADDR = 0x55C0E
HOOK_STOCK = bytes.fromhex("2436e8ea")   # movea -0x1518,gp,r6


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def jarl_lp(target, pc):
    """V850 jarl disp22,lp (4 bytes). Same helper as V31P (verified vs stock jarl @0x55aa8)."""
    disp = (target - pc) & 0x3FFFFF
    return _le16(0xFF80 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


# pack_polarity -- every 4/2-byte token is a V31P byte-verified encoding except the 2 new ld.bu disps.
CAVE_HEX = (
    "843faf98"   # ld.bu -0x6752[gp],r7   (r7 = gp-0x6752 polarity1)   [new disp, verified pattern]
    "c73e1f00"   # andi 0x1f,r7,r7        (low 5 bits)
    "c33a"       # shl 0x3,r7             (into byte4[7:3])
    "8437edea"   # ld.bu -0x1514[gp],r6   (CAN-330 byte4)
    "c6360700"   # andi 0x7,r6,r6         (keep stock bits 2:0)
    "0731"       # or r7,r6
    "4437ecea"   # st.b r6,-0x1514[gp]    (write byte4)
    "843f9f98"   # ld.bu -0x6762[gp],r7   (r7 = gp-0x6762 polarity2)   [new disp, verified pattern]
    "c73e0300"   # andi 0x3,r7,r7         (low 2 bits)
    "c63a"       # shl 0x6,r7             (into byte7[7:6])
    "a437efea"   # ld.bu -0x1511[gp],r6   (CAN-330 byte7)
    "c6363f00"   # andi 0x3f,r6,r6        (keep stock bits 5:0 counter/checksum)
    "0731"       # or r7,r6
    "4437efea"   # st.b r6,-0x1511[gp]    (write byte7)
    "2436e8ea"   # movea -0x1518,gp,r6    (re-exec displaced hook instruction)
    "7f00"       # jmp [lp]               (return to 0x55c12)
)
CAVE_BYTES = bytes.fromhex(CAVE_HEX)

MAIN_BLOCK = (0x13000, 0xC4FFC)  # holds the cave + the hook; CRC @0xC4FFC
EXPECTED_BLOCKS = 50


def full_image(window):
    image = bytearray(b"\xff" * 0x100000)
    image[START:END] = window
    return bytes(image)


def assert_x31_checksum(raw, label):
    stored = struct.unpack_from("<I", raw, len(raw) - 4)[0]
    calculated = sum(raw[:-4]) & 0xFFFFFFFF
    assert calculated == stored, f"{label} x31 checksum: 0x{calculated:08X} != 0x{stored:08X}"


def crc_block_map(code):
    start_page, num_pages = struct.unpack_from("<HH", code, END - 8)
    block_start, block_length = start_page << 12, (num_pages << 12) - 4
    blocks, visited = [], set()
    while True:
        assert block_start not in visited, f"CRC chain loop at 0x{block_start:X}"
        visited.add(block_start)
        trailer = block_start + block_length
        assert trailer + 4 <= len(code), f"block 0x{block_start:X} out of bounds"
        blocks.append((block_start, trailer))
        if block_start == START:
            break
        next_page, next_num_pages = struct.unpack_from("<HH", code, block_start - 8)
        block_start, block_length = next_page << 12, (next_num_pages << 12) - 4
        assert len(blocks) <= 200, "runaway CRC chain"
    return blocks


def assert_crc_chain(code, label):
    blocks = crc_block_map(code)
    for block_start, trailer in blocks:
        calc = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        stored = struct.unpack_from("<I", code, trailer)[0]
        assert calc == stored, f"{label}: CRC mismatch 0x{block_start:X}: 0x{calc:08X}!=0x{stored:08X}"
    assert len(blocks) == EXPECTED_BLOCKS, f"{label}: {len(blocks)} blocks != {EXPECTED_BLOCKS}"
    return len(blocks)


def changed_runs(before, after):
    diffs = [i for i in range(START, END) if before[i] != after[i]]
    runs = []
    for a in diffs:
        if runs and a == runs[-1][1] + 1:
            runs[-1][1] = a
        else:
            runs.append([a, a])
    return diffs, runs


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "hook site is not stock movea"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == b"\xff" * len(CAVE_BYTES), \
        "cave target is not all 0xFF -- refusing to overwrite"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(CAVE_BYTES)), "cave tail is not 0xFF"
    # V38 lineage sanity (4x + fault guards) so we know we're on the right baseline
    assert struct.unpack_from("<H", code, 0xC646C)[0] == 3564, "not the V38 4x baseline"
    assert struct.unpack_from("<H", code, 0xC6312)[0] == 320


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)
    assert_crc_chain(baseline, "V38 baseline")
    assert walk(bytes(baseline), label="V38 baseline") == 0
    assert walk_all_blocks(bytes(baseline), label="V38 baseline") == 0

    source_rwd = open(V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V38_RWD_SHA256
    assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    assert decode is not None
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)
    hook_bytes = jarl_lp(CAVE_BASE, HOOK_ADDR)

    print(f"  cave  @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes  {CAVE_BYTES.hex()}")
    print(f"  hook  @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  (movea -> jarl 0x{CAVE_BASE:05X},lp)")
    print(f"  reads gp-0x6752 (0xFEDF18AE) -> 330 byte4[7:3]; gp-0x6762 (0xFEDF189E) -> 330 byte7[7:6]")

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes

    # everything outside the cave, the hook, and the CRC trailer is byte-identical to V38
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(CAVE_BYTES)), "cave tail moved"

    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    allowed = set(range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES)))
    allowed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V49P-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # the entire app + all cal blocks are stock (only the cave + hook + MAIN CRC move)
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:0x100000]) == bytes(baseline[0xC5000:0x100000]), "any cal/data block moved"

    assert_crc_chain(code, "V49P plain")
    assert walk(bytes(code), label="V49P") == 0
    assert walk_all_blocks(bytes(code), label="V49P") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V49P emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V49P RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V49P RWD readback")
    assert walk(readback, label="V49P RWD readback") == 0
    assert walk_all_blocks(readback, label="V49P RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert struct.unpack_from("<H", readback, 0xC646C - START if False else 0xC646C)[0] == 3564

    print(f"\n  V49P-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        kind = ("cave pack_polarity" if first == CAVE_BASE else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else "UNEXPECTED")
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:  {V38_SHA256}")
    print(f"  V49P SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V49P RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V49P-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V49P_OUT)]
    for path in stale + [V49P_OUT, BIN_OUT, V49P_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V49P = V38 + READ-ONLY polarity telemetry (gp-0x6752/gp-0x6762 -> CAN 330 spare bits).")
    print("  Reads the V49 flash-gate value off the car via the proven V31P CAN-spare-bits technique.")
    print("  Pure observability: no cal/logic change, drives exactly as V38. Study artifact.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V49P_OUT), exist_ok=True)
    with open(V49P_OUT + ".tmp", "wb") as h:
        h.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as h:
        h.write(code)
    os.replace(V49P_OUT + ".tmp", V49P_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V49P_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  NOT FLASHED. Re-disassemble _v49p_plain_image.bin @0xC4B34 in Ghidra before trusting the")
    print("  cave; then flash only on explicit operator instruction naming the file + bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
