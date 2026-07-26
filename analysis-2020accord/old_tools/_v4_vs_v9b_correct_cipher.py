"""Confirm v4 plaintext (with correct cipher) == v9b plaintext at v4's regions."""
import sys, os, operator
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import RWD_DIR
sys.path.insert(0, r"C:\Users\joey\Downloads")
from honda_rwd_decode import parse_x31, decode_x31_record

V4 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v4.rwd")
V9B = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd")

# v4 actual cipher: brute-force found (BF, 10, 9E) with ops -+^
# That is: ((c - k1) + k2) ^ k3
def decode_v4(enc, key=(0xBF, 0x10, 0x9E)):
    k1, k2, k3 = key
    return bytes((((c - k1) & 0xFF) + k2) & 0xFF ^ k3 for c in enc)

# v9b uses canonical ^^- from honda_rwd_decode
def decode_v9b(enc, key=(0xBF, 0x10, 0x9E)):
    return decode_x31_record(enc, key, "^^-")

def load(path, decoder):
    with open(path, "rb") as f:
        p = parse_x31(f.read())
    img = {}
    for rec in p.records:
        dec = decoder(rec.encoded)
        for i, b in enumerate(dec):
            img[rec.address + i] = b
    return p, img

p4, img4 = load(V4, decode_v4)
p9, img9 = load(V9B, decode_v9b)

print(f"v4: {len(p4.records)} records, regions = 0x{p4.first_address:X}-0x{p4.last_address:X}")
print(f"v9b: {len(p9.records)} records, regions = 0x{p9.first_address:X}-0x{p9.last_address:X}")

# Diff v4's regions against v9b
# v4 regions
runs = []
addrs = sorted(img4.keys())
rs = addrs[0]; prev = rs
for a in addrs[1:]:
    if a != prev + 1:
        runs.append((rs, prev + 1)); rs = a
    prev = a
runs.append((rs, prev + 1))

print(f"\nv4 regions: {[(hex(a),hex(b)) for a,b in runs]}")
for (lo, hi) in runs:
    eq = sum(1 for a in range(lo, hi) if a in img9 and img4[a] == img9[a])
    df = sum(1 for a in range(lo, hi) if a in img9 and img4[a] != img9[a])
    print(f"\n## 0x{lo:06X}-0x{hi:06X} ({hi-lo} bytes): v4==v9b = {eq}   v4!=v9b = {df}")
    if df > 0:
        # show first 16 diffs
        diffs = [(a, img4[a], img9[a]) for a in range(lo, hi) if a in img9 and img4[a] != img9[a]]
        for a, b4, b9 in diffs[:16]:
            print(f"  0x{a:08X}: v4={b4:02X}  v9b={b9:02X}")
        if df > 16:
            print(f"  ... and {df-16} more")
