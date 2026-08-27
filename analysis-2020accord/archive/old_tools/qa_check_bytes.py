"""Adversarial QA for ACCORD_TVA_ARCHITECTURE_MAP claims that can be verified
purely from code.bin bytes (no disassembly needed).

Verifies:
  - Claim 1: Near-clone block pairs differ only at +0xFF6, +0xFF8 (2 bytes total)
             and those 2 bytes encode the block's own page address as a self-tag.
  - Claim 4: CRC-32 trailer scheme (zlib.crc32(block[:0xFFC]) == LE u32 @ +0xFFC)
             on 3 selected protected blocks.
  - Claim 5 part 1: V850 decode table is bijective.
  - Claim 8: Calibration table seed candidates have the claimed structure.

Read-only. Does not modify code.bin.
"""
import zlib
import struct
import sys
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"
BIN = FW.read_bytes()
assert len(BIN) == 0x100000


def hexb(b):
    return b.hex(' ')


# =============================================================================
# Claim 1: Near-clone 4 KB block pairs
# =============================================================================
print("=" * 78)
print("CLAIM 1: Near-clone 4KB block pairs (differ only at +0xFF6, +0xFF8)")
print("=" * 78)

PAIRS = [
    (0xCE000, 0xCF000),
    (0xD0000, 0xD4000),
    (0xD1000, 0xD5000),
]

CLUSTER = [(0xDA000 + 0x1000 * i, 0xDA000 + 0x1000 * (i + 1)) for i in range(7)]

claim1_results = []

def diff_blocks(a_off, b_off, label):
    A = BIN[a_off:a_off + 0x1000]
    B = BIN[b_off:b_off + 0x1000]
    diffs = [i for i in range(0x1000) if A[i] != B[i]]
    expected_set = {0xFF6, 0xFF7, 0xFF8, 0xFF9}  # the claim says "+0xFF6 and +0xFF8" but those are 2-byte halfwords
    # The map literally says "those 2 bytes encode the block's own page address as a self-tag"
    # "2 bytes total" — that's the literal claim. Let's test BOTH interpretations:
    #  (a) literal 2 bytes at +0xFF6 and +0xFF8 (positions 0xFF6 and 0xFF8 exactly)
    #  (b) 2 halfwords at +0xFF6..0xFF7 and +0xFF8..0xFF9 (4 bytes total)
    crc_trailer_a = struct.unpack('<I', A[0xFFC:0x1000])[0]
    crc_trailer_b = struct.unpack('<I', B[0xFFC:0x1000])[0]
    a_ff6 = A[0xFF6:0xFFA]  # 4 bytes spanning FF6..FF9
    b_ff6 = B[0xFF6:0xFFA]
    return {
        'label': label,
        'a_off': a_off,
        'b_off': b_off,
        'n_diffs': len(diffs),
        'diff_positions': diffs,
        'a_at_ff6_ff9': hexb(a_ff6),
        'b_at_ff6_ff9': hexb(b_ff6),
        'a_crc': crc_trailer_a,
        'b_crc': crc_trailer_b,
        'a_full_trailer_zone': hexb(A[0xFF0:0x1000]),
        'b_full_trailer_zone': hexb(B[0xFF0:0x1000]),
    }


for a, b in PAIRS:
    r = diff_blocks(a, b, f"0x{a:X} <-> 0x{b:X}")
    claim1_results.append(r)
    print(f"\n-- {r['label']} --")
    print(f"  total diffs: {r['n_diffs']}")
    print(f"  diff positions: {[hex(p) for p in r['diff_positions']]}")
    print(f"  A[0xFF0:0x1000] = {r['a_full_trailer_zone']}")
    print(f"  B[0xFF0:0x1000] = {r['b_full_trailer_zone']}")

print("\n-- Cluster: 0xDA000..0xE1000 (8-block, pairwise adjacent) --")
for a, b in CLUSTER:
    r = diff_blocks(a, b, f"0x{a:X} <-> 0x{b:X}")
    claim1_results.append(r)
    print(f"  {r['label']}: diffs={r['n_diffs']}  positions={[hex(p) for p in r['diff_positions']]}")
    print(f"    A[0xFF0:0x1000] = {r['a_full_trailer_zone']}")
    print(f"    B[0xFF0:0x1000] = {r['b_full_trailer_zone']}")

# Verdict on Claim 1
print("\n[Claim 1 summary]")
all_just_2 = all(r['n_diffs'] == 2 and set(r['diff_positions']) == {0xFF6, 0xFF8}
                 for r in claim1_results)
# Test the self-tag claim: at +0xFF6 / +0xFF8, the bytes should match the block's page address
def page_byte(off):
    return (off >> 12) & 0xFF  # e.g. 0xCE000 -> 0xCE


print("Self-tag check (does the diff byte at +0xFF6/+0xFF8 contain the page byte?):")
for r in claim1_results:
    A = BIN[r['a_off']:r['a_off'] + 0x1000]
    B = BIN[r['b_off']:r['b_off'] + 0x1000]
    pa = page_byte(r['a_off'])
    pb = page_byte(r['b_off'])
    a_ff6 = A[0xFF6]; a_ff7 = A[0xFF7]; a_ff8 = A[0xFF8]; a_ff9 = A[0xFF9]
    b_ff6 = B[0xFF6]; b_ff7 = B[0xFF7]; b_ff8 = B[0xFF8]; b_ff9 = B[0xFF9]
    print(f"  {r['label']}: A=0x{pa:02X} expects in tag, B=0x{pb:02X} expects in tag")
    print(f"    A: ff6={a_ff6:02X} ff7={a_ff7:02X} ff8={a_ff8:02X} ff9={a_ff9:02X}")
    print(f"    B: ff6={b_ff6:02X} ff7={b_ff7:02X} ff8={b_ff8:02X} ff9={b_ff9:02X}")


# =============================================================================
# Claim 4: CRC-32 trailer scheme
# =============================================================================
print("\n" + "=" * 78)
print("CLAIM 4: CRC-32 trailer scheme on 3 selected blocks")
print("=" * 78)

for blk_off in (0x00000, 0x08000, 0xCD000):
    block = BIN[blk_off:blk_off + 0x1000]
    computed = zlib.crc32(block[:0xFFC])
    stored = struct.unpack('<I', block[0xFFC:0x1000])[0]
    ok = "PASS" if computed == stored else "FAIL"
    print(f"  block 0x{blk_off:05X}: computed=0x{computed:08X} stored=0x{stored:08X}  -> {ok}")


# =============================================================================
# Claim 5 (part 1): V850 decode table is bijective
# =============================================================================
print("\n" + "=" * 78)
print("CLAIM 5 (part 1): V850 cipher decode table bijection")
print("=" * 78)

def decode(i):
    return (((i - 0x9E) & 0xFF) + 0xBF) & 0xFF ^ 0x10  # interpretation 1

def decode_v2(i):
    return ((((i - 0x9E) + 0xBF) & 0xFF) ^ 0x10) & 0xFF  # interpretation 2

# The most likely Python translation matching the formula in build_decode_table:
def decode_official(i):
    # operator.sub, operator.add, operator.xor — modular each step
    return ((( ((i - 0x9E) & 0xFF) + 0xBF) & 0xFF) ^ 0x10) & 0xFF


outs = [decode_official(i) for i in range(256)]
print(f"  decode (official chained mask): {len(set(outs))}/256 unique  ->",
      "PASS" if len(set(outs)) == 256 else "FAIL")

# Also: pure formula no intermediate mask
outs2 = [(((i - 0x9E) + 0xBF) ^ 0x10) & 0xFF for i in range(256)]
print(f"  decode (pure formula final mask): {len(set(outs2))}/256 unique  ->",
      "PASS" if len(set(outs2)) == 256 else "FAIL")


# =============================================================================
# Claim 8: Calibration table seed candidates structure
# =============================================================================
print("\n" + "=" * 78)
print("CLAIM 8: Calibration seed candidate structures")
print("=" * 78)

def read_int16_le(off, n):
    return [int.from_bytes(BIN[off + 2*i:off + 2*i + 2], 'little', signed=True) for i in range(n)]


print("\n  [0xC6B66] 13 int16 LE, monotonically increasing, start 0, max 4776")
seq = read_int16_le(0xC6B66, 13)
print(f"    values: {seq}")
mono = all(seq[i] <= seq[i+1] for i in range(len(seq)-1))
print(f"    monotonic: {mono}, start==0: {seq[0]==0}, max==4776: {max(seq)==4776}")

print("\n  [0xC4A42] 12-point int16 LE (curve A)")
seqA = read_int16_le(0xC4A42, 12)
print(f"    {seqA}")
print("  [0xC4A6E] 12-point int16 LE (curve B, mirror)")
seqB = read_int16_le(0xC4A6E, 12)
print(f"    {seqB}")
print(f"    both start at 0? A={seqA[0]==0} B={seqB[0]==0}")
print(f"    paired length? equal={len(seqA)==len(seqB)}")

print("\n  [0xE417E/0xE41A6/0xE41CE/0xE41F6] 4 identical 12-point int16 LE rows")
rows = [read_int16_le(off, 12) for off in (0xE417E, 0xE41A6, 0xE41CE, 0xE41F6)]
for off, r in zip((0xE417E, 0xE41A6, 0xE41CE, 0xE41F6), rows):
    print(f"    @ 0x{off:X}: {r}")
print(f"    all 4 rows identical: {len(set(tuple(r) for r in rows))==1}")

print("\n  [0xC4784] float block with monotonic axis-like values")
floats = struct.unpack('<32f', BIN[0xC4784:0xC4784 + 4*32])
print(f"    first 32 floats:")
for i, v in enumerate(floats):
    print(f"      [{i:2d}] {v}")
# Check claim: "...3.062, 3.141, 3.219, 3.273, ... 3.609 interleaved with 0"
# Strip zeros and check monotone
nonzero = [v for v in floats if v != 0.0]
nonzero_mono = all(nonzero[i] <= nonzero[i+1] for i in range(len(nonzero)-1)) if nonzero else True
print(f"    nonzero values monotone? {nonzero_mono}")
print(f"    nonzero values: {nonzero}")


print("\nDONE")
