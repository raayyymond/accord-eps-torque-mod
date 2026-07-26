"""
build_v51probe_tva.py -- V51P = V38 + READ-ONLY telemetry that reads TWO candidate RAM cells,
gp-0x1300 (0xFEDF6D00, "B") and gp-0x1100 (0xFEDF6F00, "D"), into CAN 330 spare bits: a FULL 16-bit
nonzero flag per cell (not just a low-byte/low-nibble sample), plus a low-value sample and a liveness
beacon bit that proves the probe executed even when both cells read clean.

PURPOSE
    A future cave build needs a scratch/state cell in one of these two candidate regions. Static
    analysis alone cannot rule out a register-indirect writer touching them (the same residual class
    of doubt V50PROBE closed for gp-0x1500). The only way to settle it is a live watch: read both
    cells into CAN 330 spare bits on the CURRENT firmware (V38, no arbitrary-RAM UDS read) and drive.
        * if a cell's nonzero flag stays 0 for the whole drive with the beacon confirmed present ->
          nothing writes ANY of its 16 bits -> that cell is CONFIRMED free for the next cave.
        * if the nonzero flag ever reads 1 -> a writer exists somewhere in the full 16-bit cell ->
          that cell must be avoided.
    v1 of this probe only sampled a few low bits of each cell (B's low nibble / D's low 2 bits), which
    left a blind spot: a writer that only ever touches the HIGH byte (or a low bit outside the sampled
    range) would have shown up as "clean" without being clean. v2 closes that gap by reducing the
    FULL 16-bit cell to a single "was any bit ever nonzero" flag (ld.hu, zero-extended, then a
    branchless != 0 reduction -- see CAVE ENCODING), so a clean verdict now covers every bit, not just
    the sampled ones. The low-value sample bits are kept alongside the flag purely as bonus value
    richness (e.g. to see the low bits toggle if a writer IS found); the flag is the load-bearing bit.
    The beacon (byte4 bit7, forced to 1 on every packed frame) is what makes a "both clean" result
    trustworthy: without it, "B and D read 0 all drive" is indistinguishable from "the probe never
    executed / this isn't even a probe frame" -- an ambiguity that has bitten this kit before (V31P's
    early gate-flag telemetry needed the same discriminating-signal lesson). Beacon present + nonzero
    flag 0 all drive => clean. Beacon absent (or 0) anywhere => the probe didn't run on that frame;
    treat the drive as inconclusive, not confirming.

WHY THIS IS SAFE (the proven-safe telemetry cave class -- NOT the bricked control-cave class)
    PURE OBSERVABILITY: the cave READS gp-0x1300 and gp-0x1100 (never writes either) and writes only
    CAN-330 spare bits (byte4[7:3]/byte7[7:6], never-written elsewhere + undefined in the openpilot
    DBC -- V31P audit, reused unchanged by V49P/V50P). It inserts NO dynamics into ANY control loop ->
    Gate 2 N/A; it allocates NO scratch RAM -> Gate 1 N/A. This is the class flashed + DRIVEN fine as
    V31P/V31P-V2/V49P. All V38 cals + code are byte-identical -> the car drives exactly as V38.

TECHNIQUE (identical mechanics to build_v50probe_tva.py / build_v49p_tva.py)
    CHANNEL: CAN 330 / 0x14A (DLC8, 100 Hz, gateway-forwarded/comma-visible), builder FUN_00055a98,
    buffer 0xFEDF6AE8. Honda 4-bit counter/checksum computed AFTER the pack hook -> covers the bits.
    HOOK: site 0x55c0e `movea -0x1518,gp,r6` -> `jarl pack,lp` (re-exec the displaced movea, then
    jmp [lp] -> 0x55c12). Clobbers r6/r7/r8 -- all three are inside V31P's ORIGINAL proven-safe
    register set (V49P/V50P used only the r6/r7 subset because they didn't need a third scratch reg;
    r8 is required here for the nonzero-reduction accumulator). Independently confirmed dead-at-return
    this session by disassembling FUN_00055a98's return site directly: 0x55c12 `mov 0x8,r7` and
    0x55c14 `movea 0x14a,r0,r8` both OVERWRITE r7/r8 before any read -- whatever the cave leaves in
    them is provably discarded.
    WIRE PAYLOAD (stock low bits preserved exactly; only the genuinely-spare bits are written):
      byte4 = (stock_byte4 & 0x07) | 0x80 | (B_nz << 6) | ((gp-0x1300 & 0x07) << 3)
          bits[2:0] stock, bit7 = LIVENESS BEACON (constant 1), bit6 = B_nz (B's full 16 bits != 0),
          bits[5:3] = B's low 3 bits (value richness)
      byte7 = (stock_byte7 & 0x3F) | (D_nz << 7) | ((gp-0x1100 & 0x01) << 6)
          bits[5:0] stock (Honda counter/checksum), bit7 = D_nz (D's full 16 bits != 0),
          bit6 = D's low bit
    DECODE (from the raw rlog):
      beacon    = (byte4 >> 7) & 0x1   -- must be 1 on every probe frame (liveness)
      B_nonzero = (byte4 >> 6) & 0x1   -- 0 on ALL frames = B clean (full 16-bit coverage)
      B_low3    = (byte4 >> 3) & 0x7   -- B's low 3 bits, bonus value richness
      D_nonzero = (byte7 >> 7) & 0x1   -- 0 on ALL frames = D clean (full 16-bit coverage)
      D_low1    = (byte7 >> 6) & 0x1   -- D's low bit, bonus value richness

CAVE ENCODING (pack_bd_nz16, 86 bytes @0xC4B34). The two ld.bu/st.b read-modify-write pairs on
    CAN-330 byte4/byte7 (-0x1514/-0x1511) and the hook/trampoline (movea -0x1518, jmp [lp]) are
    UNCHANGED LITERAL bytes copied from V49P/V50P -- NOT re-derived. This matters: while verifying
    this cave, hand-decoding the two existing ld.bu instances (-0x1514 -> op-word "8437edea",
    -0x1511 -> op-word "a437efea") showed their raw opcode field differs by 1 despite both being
    "ld.bu ...,gp,r6" per Ghidra -- i.e. ld.bu's op bits are NOT a clean function of the destination
    register alone (some other factor, plausibly the ORIGINAL pre-negation displacement's parity,
    also selects between the two). Rather than trust a hand-rolled ld.bu encoder for a case it hasn't
    been proven against, this build reuses those two instructions verbatim and does not synthesize any
    NEW ld.bu displacement. See CAVE_HEX below for exactly which tokens are literal vs. derived.
    Every token that WAS derived (not reused) is formula-checked in build() against either a real
    code.bin instance (via GhidraMCP search_instructions, this session) or a previously
    Ghidra-round-tripped cave (v50_cave_asm.py, the V50 low-pass cave):
      e43f01ed / e43f01ef -- ld.hu -0x1300[gp]/-0x1100[gp],r7 (zero-extended full-16-bit read).
          op=0x3F, field=((-disp)&0xFFFE)|1 -- cross-checked against 4 real gp-relative ld.hu
          instances in code.bin (FUN_00014ef8/FUN_0001500e, disps -0x22ba/-0x22b8/-0x22bc/-0x24c4,
          regs r6/r7/r8/r12), all of which reproduce op=0x3F regardless of reg2 or displacement, and
          all of which -- like our -0x1300/-0x1100 targets -- have an EVEN pre-negation displacement
          (the one axis the ld.bu anomaly above showed could matter).
      0040 / a741 / bf42 / c8460100 -- mov r0,r8 ; sub r7,r8 ; sar 0x1f,r8 ; andi 0x1,r8,r8: the
          branchless "!=0 -> 1" reduction. r8=0; r8-=B (r8=-B); sar 0x1f replicates bit31 (which is
          set iff B!=0, since B is zero-extended into [0,65535] and -B has bit31 set for any B!=0);
          andi 0x1 isolates that into a clean 0/1. Chosen over cmp+branch/setf specifically BECAUSE
          it needs no new opcode at all: mov(op 0x00) cross-checked vs real code.bin (`mov r0,r7`
          @0x8e); sub(op 0x0D) and sar(op 0x15) are the SAME encoders already Ghidra-round-tripped in
          the V50 low-pass cave (v50_cave_asm.py), sar additionally cross-checked here vs a real
          code.bin instance (`sar 0x8,r2` @0xae00) to confirm the imm5=10-only prior use generalizes;
          andi(op 0x36) is the same encoder already used repeatedly in this cave family.
      06368000 -- addi 0x80,r6,r6, the beacon-bit set (kept from v1): r6 spans bits[6:0] only at that
          point (max 0x7F) so addi 0x80 == or 0x80, no carry/overlap. Same op-0x30 encoder as the V50
          cave's stack-pointer adjustment.
    All remaining tokens (shl 0x3/0x6/0x7, andi 0x7/0x1/0x3f, or r7,r6/or r8,r6) reuse the SAME
    already-verified op bytes as v1's andi/shl/or tokens, just with new immediates/registers plugged
    into the identical bit-field formula (verified in build()'s self-check, see there for the full
    list). The assembled cave was re-disassembled from the BUILT image in Ghidra before trusting it
    (kit rule for any cave, no exceptions) -- see the handoff/report for the full listing.

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
    raise RuntimeError("V51-probe builder requires assertions; do not run with python -O")

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

TAG = "v51probe-nz16-gp1300-gp1100-can330-beacon-caveC4B34-onV38"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V51PROBE-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v51probe_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

CAVE_BASE = 0xC4B34
HOOK_ADDR = 0x55C0E
HOOK_STOCK = bytes.fromhex("2436e8ea")   # movea -0x1518,gp,r6

# pack_bd_nz16 -- reads gp-0x1300 ("B") and gp-0x1100 ("D") FULL 16-bit, reduces each to a
# "!=0 anywhere in 16 bits" flag (branchless: mov r0,r8; sub rX,r8; sar 0x1f,r8; andi 1,r8,r8),
# and packs {flag, low value bits, beacon} into CAN 330 byte4/byte7. See docstring for exactly
# which tokens are literal-reused vs formula-derived-and-verified.
CAVE_HEX = (
    "e43f01ed"   # ld.hu -0x1300[gp],r7   (r7 = candidate cell B, full 16-bit zero-ext)   [new]
    "0040"       # mov r0,r8              (r8 = 0)
    "a741"       # sub r7,r8              (r8 = r8 - r7 = -B)
    "bf42"       # sar 0x1f,r8            (r8 = bit31 replicated: 0xFFFFFFFF if B!=0 else 0)
    "c8460100"   # andi 0x1,r8,r8         (r8 = B_nz, 0/1)
    "c642"       # shl 0x6,r8             (into byte4 bit6)
    "8437edea"   # ld.bu -0x1514[gp],r6   (CAN-330 byte4)                       [literal, unchanged]
    "c6360700"   # andi 0x7,r6,r6         (keep stock bits 2:0)
    "0831"       # or r8,r6               (bit6 = B_nz)
    "c73e0700"   # andi 0x7,r7,r7         (r7 = B low 3 bits; r7 still holds full B from load)
    "c33a"       # shl 0x3,r7             (into byte4[5:3])
    "0731"       # or r7,r6               (bits[5:3] = B low3)
    "06368000"   # addi 0x80,r6,r6        (beacon bit7 = 1; r6 spans bits[6:0] only, no overlap)
    "4437ecea"   # st.b r6,-0x1514[gp]    (write byte4)                         [literal, unchanged]
    "e43f01ef"   # ld.hu -0x1100[gp],r7   (r7 = candidate cell D, full 16-bit zero-ext)   [new]
    "0040"       # mov r0,r8              (r8 = 0)
    "a741"       # sub r7,r8              (r8 = -D)
    "bf42"       # sar 0x1f,r8            (r8 = bit31 replicated)
    "c8460100"   # andi 0x1,r8,r8         (r8 = D_nz, 0/1)
    "c742"       # shl 0x7,r8             (into byte7 bit7)
    "a437efea"   # ld.bu -0x1511[gp],r6   (CAN-330 byte7)                       [literal, unchanged]
    "c6363f00"   # andi 0x3f,r6,r6        (keep stock bits 5:0 counter/checksum)
    "0831"       # or r8,r6               (bit7 = D_nz)
    "c73e0100"   # andi 0x1,r7,r7         (r7 = D low bit)
    "c63a"       # shl 0x6,r7             (into byte7 bit6)
    "0731"       # or r7,r6               (bit6 = D low bit)
    "4437efea"   # st.b r6,-0x1511[gp]    (write byte7)                         [literal, unchanged]
    "2436e8ea"   # movea -0x1518,gp,r6    (re-exec displaced hook instruction)  [literal, unchanged]
    "7f00"       # jmp [lp]               (return to 0x55c12)                  [literal, unchanged]
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

    # cave-encoding self-check: every DERIVED token (not the literal-reused ld.bu/st.b/movea/jmp
    # pieces) must reproduce by formula, and the formula must ALSO reproduce real code.bin instances
    # (found via GhidraMCP search_instructions this session) or the V50 cave's already-Ghidra-verified
    # tokens. See docstring for why ld.bu itself is deliberately NOT re-derived here.
    def _gp_field_load(disp_neg):
        assert 0 < disp_neg <= 0x8000
        return ((0x10000 - disp_neg) & 0xFFFE) | 1

    def _fmt1(op, reg1, reg2):
        return _le16((reg2 << 11) | (op << 5) | reg1)

    def _ldhu(disp_neg, reg2, reg1=4):
        return _fmt1(0x3F, reg1, reg2) + _le16(_gp_field_load(disp_neg))

    def _mov(reg1, reg2):
        return _fmt1(0x00, reg1, reg2)

    def _sub(reg1, reg2):
        return _fmt1(0x0D, reg1, reg2)

    def _sar(imm5, reg2):
        assert 0 <= imm5 <= 31
        return _fmt1(0x15, imm5, reg2)

    def _shl(imm5, reg2):
        assert 0 <= imm5 <= 31
        return _fmt1(0x16, imm5, reg2)

    def _orr(reg1, reg2):
        return _fmt1(0x08, reg1, reg2)

    def _andi(imm16, reg1, reg2):
        return _fmt1(0x36, reg1, reg2) + _le16(imm16)

    def _addi(imm16, reg1, reg2):
        return _fmt1(0x30, reg1, reg2) + _le16(imm16 & 0xFFFF)

    # every token actually used in CAVE_HEX, by formula
    assert _ldhu(0x1300, 7).hex() == "e43f01ed", "ld.hu -0x1300[gp],r7 formula mismatch"
    assert _ldhu(0x1100, 7).hex() == "e43f01ef", "ld.hu -0x1100[gp],r7 formula mismatch"
    assert _mov(0, 8).hex() == "0040", "mov r0,r8 formula mismatch"
    assert _sub(7, 8).hex() == "a741", "sub r7,r8 formula mismatch"
    assert _sar(0x1F, 8).hex() == "bf42", "sar 0x1f,r8 formula mismatch"
    assert _andi(0x1, 8, 8).hex() == "c8460100", "andi 0x1,r8,r8 formula mismatch"
    assert _shl(0x6, 8).hex() == "c642", "shl 0x6,r8 formula mismatch"
    assert _orr(8, 6).hex() == "0831", "or r8,r6 formula mismatch"
    assert _andi(0x7, 7, 7).hex() == "c73e0700", "andi 0x7,r7,r7 formula mismatch"
    assert _shl(0x3, 7).hex() == "c33a", "shl 0x3,r7 formula mismatch"
    assert _orr(7, 6).hex() == "0731", "or r7,r6 formula mismatch"
    assert _addi(0x80, 6, 6).hex() == "06368000", "addi 0x80,r6,r6 formula mismatch"
    assert _shl(0x7, 8).hex() == "c742", "shl 0x7,r8 formula mismatch"
    assert _andi(0x1, 7, 7).hex() == "c73e0100", "andi 0x1,r7,r7 formula mismatch"
    assert _shl(0x6, 7).hex() == "c63a", "shl 0x6,r7 formula mismatch"

    # cross-checks vs REAL code.bin instances (GhidraMCP search_instructions, this session) -- all
    # ld.hu cases are EVEN pre-negation displacement like our -0x1300/-0x1100 targets
    assert _ldhu(0x22BA, 8).hex() == "e44747dd", "formula fails real code.bin ld.hu -0x22ba,r8@0x14f0a"
    assert _ldhu(0x22B8, 12).hex() == "e46749dd", "formula fails real code.bin ld.hu -0x22b8,r12@0x14f12"
    assert _ldhu(0x22BC, 6).hex() == "e43745dd", "formula fails real code.bin ld.hu -0x22bc,r6@0x14f30"
    assert _ldhu(0x24C4, 7).hex() == "e43f3ddb", "formula fails real code.bin ld.hu -0x24c4,r7@0x15012"
    assert _mov(0, 7).hex() == "0038", "formula fails real code.bin mov r0,r7 @0x8e"
    assert _sar(0x8, 2).hex() == "a812", "formula fails real code.bin sar 0x8,r2 @0xae00"

    # the literal-reused pieces must be present unchanged (not re-derived -- see docstring)
    assert CAVE_HEX.count("8437edea") == 1 and CAVE_HEX.count("4437ecea") == 1, \
        "byte4 ld.bu/st.b literal tokens missing/duplicated"
    assert CAVE_HEX.count("a437efea") == 1 and CAVE_HEX.count("4437efea") == 1, \
        "byte7 ld.bu/st.b literal tokens missing/duplicated"

    code = bytearray(baseline)
    hook_bytes = jarl_lp(CAVE_BASE, HOOK_ADDR)
    print(f"  cave  @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes  {CAVE_BYTES.hex()}")
    print(f"  hook  @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  (movea -> jarl 0x{CAVE_BASE:05X},lp)")
    print(f"  reads gp-0x1300 (0xFEDF6D00,'B') full-16bit -> 330 byte4[6]=nz, byte4[5:3]=low3, byte4[7]=beacon")
    print(f"  reads gp-0x1100 (0xFEDF6F00,'D') full-16bit -> 330 byte7[7]=nz, byte7[6]=low1")

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes

    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(CAVE_BYTES)), "cave tail moved"
    assert CAVE_BASE + len(CAVE_BYTES) <= 0xC4FF0, "cave overruns its free region"

    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    allowed = set(range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES)))
    allowed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V51PROBE-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:0x100000]) == bytes(baseline[0xC5000:0x100000]), "any cal/data block moved"

    assert_crc_chain(code, "V51PROBE plain")
    assert walk(bytes(code), label="V51PROBE") == 0
    assert walk_all_blocks(bytes(code), label="V51PROBE") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V51PROBE emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V51PROBE RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V51PROBE RWD readback")
    assert walk(readback, label="V51PROBE RWD readback") == 0
    assert walk_all_blocks(readback, label="V51PROBE RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert struct.unpack_from("<H", readback, 0xC646C)[0] == 3564

    print(f"\n  V51PROBE-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        kind = ("cave pack_bd_nz16" if first == CAVE_BASE else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else "UNEXPECTED")
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:      {V38_SHA256}")
    print(f"  V51PROBE SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V51PROBE RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V51PROBE-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(OUT)]
    for path in stale + [OUT, BIN_OUT, OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V51-PROBE v2 = V38 + READ-ONLY telemetry: gp-0x1300('B') + gp-0x1100('D') FULL 16-bit")
    print("  nonzero flags -> CAN 330 spare bits + a liveness beacon (byte4 bit7=1 on every frame).")
    print("  Read-only telemetry cave (V49P/V50P class, flashed+driven fine as V31P/V49P). Drives")
    print("  exactly as V38.")
    print("  Decode: beacon=(byte4>>7)&1 (must be 1); B_nonzero=(byte4>>6)&1; B_low3=(byte4>>3)&0x7;")
    print("          D_nonzero=(byte7>>7)&1; D_low1=(byte7>>6)&1.")
    print("  Expectation if both cells are free: beacon=1 always, B_nonzero=0 and D_nonzero=0 all drive.\n")
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
    print("  the file + bus. After a drive, decode CAN 330: beacon=1 always + B=0/D=0 all drive confirms")
    print("  both cells free.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
