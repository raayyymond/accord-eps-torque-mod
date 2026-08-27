"""
builds/v50_v79/build_v50probe_tva.py -- V50-PROBE = V38 + READ-ONLY telemetry that reads gp-0x1500 (0xFEDF6B00) into
CAN 330 spare bits. Closes V50's Gate-1 residual WITHOUT flashing the V50 control cave.

PURPOSE
    V50 puts its EMA-low-pass filter state in gp-0x1500. Static analysis proved the cell direct-clean and
    V48B-flash-proven, but the walker of the 0xbb640/0xb7260 diagnostic tables (which list 0xFEDF6B00) is
    unfindable, so a register-indirect writer is not PROVEN absent. The ONLY way to settle it is a live
    watch. The current on-car firmware (V38) has no arbitrary-RAM UDS read (its DIDs read fixed globals),
    so we borrow the proven-safe V49P/V31P telemetry-cave technique: read gp-0x1500 into CAN 330 spare bits
    on the CURRENT firmware and drive. On stock/V38 gp-0x1500 is unused, so:
      * if it stays 0 across a full drive -> nothing writes it -> gp-0x1500 is CONFIRMED free for V50.
      * if it ever reads non-zero -> a writer exists -> V50 must move the cell.
    Decode with the existing studies/probes/decode_v49p_polarity.py (byte4>>3 & 0x1F, byte7>>6 & 0x3 -> gp-0x1500 low bits).

WHY THIS IS SAFE (the proven-safe telemetry cave class -- NOT the bricked control-cave class)
    PURE OBSERVABILITY: the cave READS gp-0x1500 (never writes it) and writes only CAN-330 spare bits
    (byte4[7:3]/byte7[7:6], never-written elsewhere + undefined in the openpilot DBC -- V31P audit). It
    inserts NO dynamics into ANY control loop -> Gate 2 N/A; it allocates NO scratch RAM -> Gate 1 N/A.
    This is the class flashed + DRIVEN fine as V31P/V31P-V2/V49P. All V38 cals + code are byte-identical
    -> the car drives exactly as V38.

TECHNIQUE (identical to builds/v18_v49/build_v49p_tva.py, which is identical to the flashed-and-driven V31P-V2)
    CHANNEL: CAN 330 / 0x14A (DLC8, 100 Hz, gateway-forwarded/comma-visible), builder FUN_00055a98,
    buffer 0xFEDF6AE8. Honda 4-bit counter/checksum computed AFTER the pack hook -> covers the bits.
    HOOK: site 0x55c0e `movea -0x1518,gp,r6` -> `jarl pack,lp` (re-exec the displaced movea, then jmp [lp]
    -> 0x55c12). Clobbers only r6/r7 (a subset of V31P's proven-safe r6/r7/r8).
    WIRE PAYLOAD: byte4 bits 7:3 = (gp-0x1500 & 0x1F); byte7 bits 7:6 = (gp-0x1500 & 0x03). (Both sample the
    low byte of gp-0x1500 -- sufficient to detect any write; on stock they read 0.)

ONLY DIFFERENCE vs V49P: the two ld.bu displacements are -0x1500 (read gp-0x1500) instead of -0x6752/-0x6762.
    843f01eb = ld.bu -0x1500[gp],r7 -- verified against the two proven V49P even-ld.bu encodings
    (843faf98/843f9f98) by the same ((-disp & 0xFFFE)|1) formula.

SAFETY: STUDY ARTIFACT. UNFLASHED. Flash only on explicit operator instruction naming file + bus.
=======================================================================================================
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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
# --- end path bootstrap ---------------------------------------------------

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V50-probe builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

TAG = "v50probe-read-gp1500-can330-caveC4B34-onV38"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V50PROBE-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v50probe_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

CAVE_BASE = 0xC4B34
HOOK_ADDR = 0x55C0E
HOOK_STOCK = bytes.fromhex("2436e8ea")   # movea -0x1518,gp,r6

# pack_gp1500 -- identical to V49P except the two ld.bu displacements read gp-0x1500 (843f01eb).
CAVE_HEX = (
    "843f01eb"   # ld.bu -0x1500[gp],r7   (r7 = gp-0x1500 low byte)   [was -0x6752]
    "c73e1f00"   # andi 0x1f,r7,r7        (low 5 bits)
    "c33a"       # shl 0x3,r7             (into byte4[7:3])
    "8437edea"   # ld.bu -0x1514[gp],r6   (CAN-330 byte4)
    "c6360700"   # andi 0x7,r6,r6         (keep stock bits 2:0)
    "0731"       # or r7,r6
    "4437ecea"   # st.b r6,-0x1514[gp]    (write byte4)
    "843f01eb"   # ld.bu -0x1500[gp],r7   (r7 = gp-0x1500 low byte again)   [was -0x6762]
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

MAIN_BLOCK = (0x13000, 0xC4FFC)
EXPECTED_BLOCKS = 50


def _le16(v):
    return struct.pack("<H", v & 0xFFFF)


def jarl_lp(target, pc):
    disp = (target - pc) & 0x3FFFFF
    return _le16(0xFF80 | ((disp >> 16) & 0x3F)) + _le16(disp & 0xFFFF)


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
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)
    hook_bytes = jarl_lp(CAVE_BASE, HOOK_ADDR)
    print(f"  cave  @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes  {CAVE_BYTES.hex()}")
    print(f"  hook  @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  (movea -> jarl 0x{CAVE_BASE:05X},lp)")
    print(f"  reads gp-0x1500 (0xFEDF6B00) -> 330 byte4[7:3] (low5) + byte7[7:6] (low2)")

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes

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
    assert set(diffs) <= allowed, f"unexpected V50PROBE-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:0x100000]) == bytes(baseline[0xC5000:0x100000]), "any cal/data block moved"

    assert_crc_chain(code, "V50PROBE plain")
    assert walk(bytes(code), label="V50PROBE") == 0
    assert walk_all_blocks(bytes(code), label="V50PROBE") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V50PROBE emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V50PROBE RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V50PROBE RWD readback")
    assert walk(readback, label="V50PROBE RWD readback") == 0
    assert walk_all_blocks(readback, label="V50PROBE RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert struct.unpack_from("<H", readback, 0xC646C)[0] == 3564

    print(f"\n  V50PROBE-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        kind = ("cave pack_gp1500" if first == CAVE_BASE else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else "UNEXPECTED")
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:      {V38_SHA256}")
    print(f"  V50PROBE SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V50PROBE RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V50PROBE-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(OUT)]
    for path in stale + [OUT, BIN_OUT, OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V50-PROBE = V38 + READ-ONLY telemetry: gp-0x1500 -> CAN 330 spare bits (Gate-1 residual check).")
    print("  Read-only telemetry cave (V49P/V31P class, flashed+driven fine). Drives exactly as V38.")
    print("  Decode with studies/probes/decode_v49p_polarity.py: 330 byte4>>3&0x1F + byte7>>6&0x3 = gp-0x1500 low bits.")
    print("  Expectation if gp-0x1500 is free: BOTH read 0 across the whole drive (a writer -> non-zero).\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".tmp", "wb") as h:
        h.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as h:
        h.write(code)
    os.replace(OUT + ".tmp", OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  READ-ONLY telemetry cave. NOT FLASHED. Flash only on explicit operator instruction naming")
    print("  the file + bus. After a drive, decode CAN 330 to confirm gp-0x1500 stays 0 (= free for V50).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
