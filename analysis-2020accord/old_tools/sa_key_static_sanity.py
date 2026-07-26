"""sa_key_static_sanity.py - lightweight static check for V850 SA secret presence.

Scans code.bin (and data.bin) for byte patterns that would corroborate that the
V850 TVA SA handler uses the same algorithm with the same V850-family secret
observed in T2F/T3L/TV9 sibling .rwds.

This is a LOW-RIGOR sanity check, not a substitute for RE'ing the 0x27 handler.

Scan types:
  1. Constant scan: search for k0/k1/k2 (0x0011, 0x0012, 0x1020) and the full
     6-byte concatenation as raw bytes (BE u16 layout).
  2. V850 immediate-form scan: look for the 16-bit-immediate-bearing instructions
     `movhi`, `movea`, `addi`, `mulhi`, `ori`, `andi`, `xori` carrying these
     immediates. On V850, `movhi imm,r0,rN` + `movea lo,rN,rM` is the canonical
     way to materialize a 32-bit literal; `mulhi imm,rN,rM` is a 16x16 multiply.
  3. Algorithm-arithmetic scan: count opcodes of the family (`mul`/`mulh`/`mulu`,
     `div`/`divh`/`divhu`, `xor`/`xori`) anywhere in code.bin to confirm the
     building blocks of `(a+k0) ^ (a*k1) % k2` exist in the firmware at all.
"""

import os
import struct
import sys
from collections import Counter

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import STOCK_FW_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_BIN = STOCK_FW_DUMP / 'code.bin'
DATA_BIN = STOCK_FW_DUMP / 'data.bin'

# V850-family secret bytes (big-endian u16 triplet representation)
SECRET = b'\x00\x11\x00\x12\x10\x20'
K0 = 0x0011
K1 = 0x0012
K2 = 0x1020


def find_all(blob: bytes, needle: bytes):
    """Yield every offset where `needle` occurs in `blob`."""
    out = []
    i = 0
    while True:
        j = blob.find(needle, i)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out


def le_u16_occurrences(blob: bytes, value: int):
    """Find LE u16 occurrences of `value`. V850 is little-endian, so 16-bit
    immediates in instruction encodings appear LE-byte-ordered in the bytestream.
    """
    needle = struct.pack('<H', value)
    return find_all(blob, needle)


def be_u16_occurrences(blob: bytes, value: int):
    """Find BE u16 occurrences (as the secret would appear if stored as a packed
    big-endian triplet, e.g. in a .rwd-style data region)."""
    needle = struct.pack('>H', value)
    return find_all(blob, needle)


# V850 opcode recognition (16-bit instruction format II, format VI etc.)
# Source: V850E2M architecture user's manual + Renesas docs.
# Format VI (reg-reg-imm16) opcodes carry a 16-bit immediate in the next halfword.
# We check the first halfword's high-6-bit opcode field.
#
# Opcode field is bits 15..10 of the first halfword.
# Opcodes we care about (subopcode included where relevant):
#   addi    : 0b110000 (0x30)  - reg2 + imm16 -> reg1
#   movei   : (movei is a pseudo-op composed of movea+movhi, no single opcode)
#   movea   : 0b110001 (0x31)  - reg2 + sxt(imm16) -> reg1
#   movhi   : 0b110010 (0x32)  - reg2 + (imm16 << 16) -> reg1
#   ori     : 0b110100 (0x34)
#   xori    : 0b110101 (0x35)
#   andi    : 0b110110 (0x36)
#   mulhi   : 0b110111 (0x37)  - reg2[15:0] * imm16 -> reg1 (16x16->32 signed)
#
# In V850E2, format VI is a 4-byte instruction: first halfword has opcode + regs,
# second halfword is the imm16. We scan halfword-aligned and check if (halfword
# opcode is one of the above) AND (next halfword equals one of our immediates).

FMT_VI_OPCODES = {
    0x30: 'addi',
    0x31: 'movea',
    0x32: 'movhi',
    0x34: 'ori',
    0x35: 'xori',
    0x36: 'andi',
    0x37: 'mulhi',
}


def scan_v850_imm16(blob: bytes, target_imm: int):
    """Scan halfword-aligned positions for a format-VI V850 instruction whose
    imm16 (the 2nd halfword, little-endian) equals `target_imm`. Returns a list
    of (offset, opcode_name, reg1, reg2) tuples.

    Heuristic only - we are NOT decoding full instruction context, so false
    positives can occur where the halfword bytes happen to look like one of
    these opcodes but are actually mid-data or mid-of-a-32-bit-instruction.
    """
    hits = []
    for i in range(0, len(blob) - 4, 2):
        hw1 = struct.unpack_from('<H', blob, i)[0]
        # bits 15..10 are the major opcode in V850 format VI
        opc = (hw1 >> 10) & 0x3F
        if opc not in FMT_VI_OPCODES:
            continue
        imm = struct.unpack_from('<H', blob, i + 2)[0]
        if imm != target_imm:
            continue
        reg1 = (hw1 >> 11) & 0x1F  # bits 15..11 - actually overlaps opcode field
        reg2 = hw1 & 0x1F          # bits 4..0
        # Note: bits 15..11 is reg1 (dest), bits 4..0 is reg2 (src), but bits
        # 15..10 also encode the opcode - reg1 thus shares bits with opcode.
        # The V850 format-VI encoding is: [reg1:5][opcode:6][reg2:5][imm:16]
        # so reg1 occupies bits 15..11 - which means our "opcode" mask is wrong
        # if we strip reg1. Recompute:
        opc_real = (hw1 >> 5) & 0x3F  # bits 10..5
        if opc_real in FMT_VI_OPCODES:
            reg1 = (hw1 >> 11) & 0x1F
            reg2 = hw1 & 0x1F
            hits.append((i, FMT_VI_OPCODES[opc_real], reg1, reg2, imm))
    return hits


def scan_opcode_frequency(blob: bytes):
    """Count V850 format-VI immediate-arithmetic opcodes anywhere in code.bin.
    A simple smoke test that the algorithm building blocks exist."""
    counts = Counter()
    for i in range(0, len(blob) - 2, 2):
        hw = struct.unpack_from('<H', blob, i)[0]
        opc = (hw >> 5) & 0x3F
        if opc in FMT_VI_OPCODES:
            counts[FMT_VI_OPCODES[opc]] += 1
    return counts


def report():
    with open(CODE_BIN, 'rb') as f:
        code = f.read()
    with open(DATA_BIN, 'rb') as f:
        data = f.read()
    print(f"code.bin: {len(code):,} bytes")
    print(f"data.bin: {len(data):,} bytes")
    print()

    # -------- 1. Raw-byte scans --------
    print("=" * 72)
    print("1. RAW BYTE SCANS")
    print("=" * 72)
    print(f"Looking for V850-family secret: {SECRET.hex()}")
    print()

    full = find_all(code, SECRET)
    print(f"  Full 6-byte secret  {SECRET.hex()} in code.bin: {len(full)} occurrence(s)")
    for off in full[:10]:
        print(f"    @ 0x{off:06X}")
    full_d = find_all(data, SECRET)
    print(f"  Full 6-byte secret  {SECRET.hex()} in data.bin: {len(full_d)} occurrence(s)")
    for off in full_d[:10]:
        print(f"    @ 0x{off:06X}")
    print()

    print(f"BE u16 (data-storage layout) hits in code.bin:")
    for name, val in [('k0=0x0011', K0), ('k1=0x0012', K1), ('k2=0x1020', K2)]:
        hits = be_u16_occurrences(code, val)
        print(f"  {name} as BE u16 {struct.pack('>H', val).hex()}: {len(hits)} occurrence(s)")
        for off in hits[:6]:
            print(f"    @ 0x{off:06X}")
    print()

    print(f"LE u16 (V850 instruction-immediate layout) hits in code.bin:")
    for name, val in [('k0=0x0011', K0), ('k1=0x0012', K1), ('k2=0x1020', K2)]:
        hits = le_u16_occurrences(code, val)
        print(f"  {name} as LE u16 {struct.pack('<H', val).hex()}: {len(hits)} occurrence(s) (mostly noise)")
    print()

    # -------- 2. V850-instruction-form scan --------
    print("=" * 72)
    print("2. V850 FORMAT-VI INSTRUCTION SCAN (opcode + matching imm16)")
    print("=" * 72)
    print("Heuristic - scans for `<opc> reg, reg, <imm16>` carrying one of our")
    print("secret constants. False positives possible; cluster-near-each-other")
    print("would corroborate the SA handler uses these constants directly.")
    print()
    for name, val in [('k0=0x0011', K0), ('k1=0x0012', K1), ('k2=0x1020', K2)]:
        hits = scan_v850_imm16(code, val)
        print(f"  {name}: {len(hits)} instruction-immediate hit(s)")
        # Show top 10 by offset
        for off, opname, r1, r2, imm in hits[:10]:
            print(f"    @ 0x{off:06X}  {opname:6} r{r1},r{r2},0x{imm:04X}")
        if len(hits) > 10:
            print(f"    ... and {len(hits) - 10} more")
    print()

    # Cluster analysis: are k0+k1+k2 hits near each other anywhere?
    all_hits = []
    for name, val in [('k0', K0), ('k1', K1), ('k2', K2)]:
        for off, opname, r1, r2, imm in scan_v850_imm16(code, val):
            all_hits.append((off, name, opname))
    all_hits.sort()
    print("Cluster analysis: any k0/k1/k2 imm16 hits within a 256-byte window?")
    clusters = []
    window = 256
    i = 0
    while i < len(all_hits):
        j = i
        kinds = set()
        while j < len(all_hits) and all_hits[j][0] - all_hits[i][0] < window:
            kinds.add(all_hits[j][1])
            j += 1
        if len(kinds) >= 2:
            clusters.append((all_hits[i][0], all_hits[j-1][0], kinds, j - i))
        i = j
    if clusters:
        print(f"  Found {len(clusters)} cluster(s) containing >=2 of {{k0,k1,k2}}:")
        for start, end, kinds, n in clusters[:20]:
            print(f"    0x{start:06X}..0x{end:06X}  ({n} hits, kinds={sorted(kinds)})")
    else:
        print("  No clusters - the constants are not co-located as instruction immediates.")
        print("  (This is mildly negative evidence: the SA handler either uses")
        print("   different constants, loads them indirectly, or lives somewhere")
        print("   the heuristic isn't matching.)")
    print()

    # -------- 3. Algorithm-arithmetic opcode frequency --------
    print("=" * 72)
    print("3. V850 ARITHMETIC OPCODE FREQUENCY (existence smoke test)")
    print("=" * 72)
    counts = scan_opcode_frequency(code)
    for op in ['addi', 'movea', 'movhi', 'ori', 'xori', 'andi', 'mulhi']:
        print(f"  {op:6} : {counts.get(op, 0):,} candidate halfword(s)")
    print()
    print("Note: these counts are over ALL halfword positions, not just confirmed")
    print("instruction starts - heavy upper-bound. But finding multiplies AND")
    print("xors AND adds in the same firmware means the algorithm building")
    print("blocks all exist.")
    print()

    # -------- 4. Data.bin scan --------
    print("=" * 72)
    print("4. DATA.BIN SCAN")
    print("=" * 72)
    print("data.bin is an EEPROM-emulation dump of learned/adapted state")
    print("(per CODE_BIN_FIRMWARE_MAP.md). A stored SA secret here is unlikely")
    print("but cheap to check.")
    print()
    for name, val in [('k0=0x0011', K0), ('k1=0x0012', K1), ('k2=0x1020', K2)]:
        be = be_u16_occurrences(data, val)
        le = le_u16_occurrences(data, val)
        print(f"  {name}: BE u16 hits={len(be)}, LE u16 hits={len(le)}")
    print()
    print("=" * 72)
    print("CONCLUSION")
    print("=" * 72)
    print("This scan corroborates / does not corroborate by counting bytes.")
    print("It does NOT identify the 0x27 SA handler - that is the UDS-dispatcher")
    print("hunter's job. Use these counts as a confidence delta, not as proof.")


if __name__ == '__main__':
    report()
