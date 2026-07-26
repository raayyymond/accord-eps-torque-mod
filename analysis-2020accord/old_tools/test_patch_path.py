"""Patch test: flip a byte in a decoded block, re-encode, re-decode, assert the
flip survives and EVERYTHING ELSE is byte-identical to original except the file
checksum (which is sum of all bytes and will change predictably)."""
import os, sys, gzip
ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from encode_eps import (parse_x31, build_rwd_from_template, crack_cipher,
                         invert_table)

src = str(CALIB_FILES / "39990-T2F-A210.rwd.gz")
raw = gzip.decompress(open(src,'rb').read())
info = parse_x31(raw)
dec_table, sym = crack_cipher(info['encs'], info['key'], b'39990-T2F-A210')
enc_table = invert_table(dec_table)

# Decode block 0, patch byte at offset 0x100 (somewhere in real code), re-encode
plain = info['encs'][0].translate(dec_table)
orig_byte = plain[0x100]
new_byte = (orig_byte + 1) & 0xFF
patched = bytearray(plain); patched[0x100] = new_byte
print(f"Patching block 0 offset 0x100: 0x{orig_byte:02X} -> 0x{new_byte:02X}")

rebuilt = build_rwd_from_template(src, patched_blocks={0: bytes(patched)})

# Re-decode the rebuilt file and verify
info2 = parse_x31(rebuilt)
plain2 = info2['encs'][0].translate(dec_table)
assert plain2[0x100] == new_byte, f"Patched byte didn't survive: {plain2[0x100]:#X}"
print(f"Patched byte at decoded offset 0x100 = 0x{plain2[0x100]:02X}  OK")

# All other decoded bytes should be identical to original
plain_orig = info['encs'][0].translate(dec_table)
diffs = [i for i in range(len(plain_orig)) if plain_orig[i] != plain2[i]]
print(f"Other byte differences in block 0: {len(diffs)-1} (should be 0)")
assert diffs == [0x100], f"Unexpected diffs: {diffs[:10]}"

# Check that other blocks are entirely untouched
for k in range(1, len(info['encs'])):
    pa = info['encs'][k].translate(dec_table)
    pb = info2['encs'][k].translate(dec_table)
    assert pa == pb, f"Block {k} differs unexpectedly"
print(f"All {len(info['encs'])-1} other blocks unchanged. OK")

# File length unchanged
assert len(rebuilt) == len(raw)
print(f"File length unchanged: 0x{len(rebuilt):X}")

# File checksum should be different (sum of bytes changed by encode_table[new]-encode_table[orig])
print(f"Trailing checksum: orig={raw[-4:].hex()} new={rebuilt[-4:].hex()} (expected to differ)")
