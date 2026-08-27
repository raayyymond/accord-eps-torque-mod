"""Adversarial QA for cipher and CRC claims.

- Claim 5 part 2: V850 decode table works on T2F-A210 real file (finds 39990-T2F string)
- Bonus: Verify CRC trailers on ALL claimed protected blocks
- Bonus: Re-verify self-tag structure (+0xFF6, +0xFF8) — what exactly does it encode?
"""
import sys, gzip, zlib, struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import CALIB_FILES, STOCK_FW_DUMP
from encode_eps import parse_x31

FW = STOCK_FW_DUMP / "code.bin"
BIN = FW.read_bytes()

print("=" * 78)
print("CLAIM 5 part 2: V850 cipher decode table on real T2F file")
print("=" * 78)

t2f_path = CALIB_FILES / "39990-T2F-A210.rwd.gz"
raw = gzip.decompress(open(t2f_path, 'rb').read())
info = parse_x31(raw)

# Build decode table per claim: decode(i) = ((i - 0x9E) + 0xBF) ^ 0x10  (mod 256)
dec_table = bytes((((i - 0x9E) + 0xBF) ^ 0x10) & 0xFF for i in range(256))
print(f"  decode table bijective: {len(set(dec_table))==256}")

# Decode block 0 of T2F
block0_enc = info['encs'][0]
block0_plain = block0_enc.translate(dec_table)
target = b'39990-T2F'
pos = block0_plain.find(target)
print(f"  block 0 length: {len(block0_enc)}")
print(f"  '39990-T2F' found in decoded block 0: {pos != -1} (pos={pos})")
if pos >= 0:
    print(f"  context: {block0_plain[max(0,pos-5):pos+25]!r}")

# Cross-check: the encoder's actual produced decode table
from encode_eps import build_decode_table, OPS
import operator
# (((i - 0x9E) + 0xBF) ^ 0x10)
ops_canonical = [operator.sub, operator.add, operator.xor]
keys_canonical = (0x9E, 0xBF, 0x10)
dec_canonical = build_decode_table(keys_canonical, ops_canonical)
print(f"  matches encode_eps build_decode_table((0x9E,0xBF,0x10), [sub,add,xor]): {dec_canonical == dec_table}")


# =============================================================================
# Full CRC verification on all claimed protected blocks (48 total)
# =============================================================================
print("\n" + "=" * 78)
print("BONUS: CRC verification on ALL 48 claimed protected blocks")
print("=" * 78)

protected = []
protected.append(0x00000)
protected.append(0x08000)
protected.extend([0xC5000, 0xC6000])
# 0xCD000 - 0xF8000 inclusive (44 blocks)
for off in range(0xCD000, 0xF8000 + 0x1000, 0x1000):
    protected.append(off)

print(f"  blocks to check: {len(protected)}")

results = []
for off in protected:
    block = BIN[off:off + 0x1000]
    computed = zlib.crc32(block[:0xFFC])
    stored = struct.unpack('<I', block[0xFFC:0x1000])[0]
    ok = computed == stored
    results.append((off, ok, computed, stored))

n_ok = sum(1 for _, ok, _, _ in results if ok)
print(f"  CRC matches: {n_ok}/{len(results)}")
if n_ok != len(results):
    print("  FAILURES:")
    for off, ok, c, s in results:
        if not ok:
            print(f"    0x{off:05X}: computed=0x{c:08X} stored=0x{s:08X}")


# =============================================================================
# Self-tag deep analysis: what's at +0xFF6..+0xFF9 in EVERY protected block?
# =============================================================================
print("\n" + "=" * 78)
print("BONUS: Self-tag structure at +0xFF6..+0xFF9 in all protected blocks")
print("=" * 78)

print(f"  {'block':>8} {'ff6':>4} {'ff7':>4} {'ff8':>4} {'ff9':>4}")
n_matches_pattern = 0
for off in protected:
    page = off >> 12
    blk = BIN[off:off + 0x1000]
    ff6 = blk[0xFF6]; ff7 = blk[0xFF7]
    ff8 = blk[0xFF8]; ff9 = blk[0xFF9]
    matches_pattern = (ff6 == ((page + 2) & 0xFF) and ff7 == 0 and
                       ff8 == (page & 0xFF) and ff9 == 0)
    if matches_pattern:
        n_matches_pattern += 1
    print(f"  0x{off:05X}:  {ff6:02X}   {ff7:02X}   {ff8:02X}   {ff9:02X}    page=0x{page:03X}  match_(+2,own)_pattern={matches_pattern}")

print(f"\n  {n_matches_pattern}/{len(protected)} blocks match the [+2:u16][own:u16] pattern at +0xFF6..+0xFF9")
