"""Brute-force what cipher actually decodes v4 into real firmware."""
import sys, os, itertools, operator
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import RWD_DIR
sys.path.insert(0, r"C:\Users\joey\Downloads")
from honda_rwd_decode import parse_x31

V4 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v4.rwd")
KEYVAL = (0xBF, 0x10, 0x9E)

OPS = {"^": operator.xor, "+": operator.add, "-": lambda a,b: a-b, "*": operator.mul, "&": operator.and_, "|": operator.or_}
OPSYMS = list(OPS.keys())

def decode_byte(c, k1, k2, k3, o1, o2, o3):
    return (OPS[o3](OPS[o2](OPS[o1](c, k1) & 0xFF, k2) & 0xFF, k3)) & 0xFF

def build_table(key, ops):
    tbl = bytearray(256)
    seen = set()
    for c in range(256):
        try:
            d = decode_byte(c, *key, *ops)
        except (ZeroDivisionError, OverflowError):
            return None
        tbl[c] = d
        seen.add(d)
    if len(seen) != 256:  # not bijective
        return None
    return bytes(tbl)

with open(V4, "rb") as f:
    raw = f.read()
p = parse_x31(raw)
print(f"v4 records: {len(p.records)}  region: 0x{p.first_address:X}-0x{p.last_address:X}")

# Encrypted bytes (just concat all record payloads)
enc = b"".join(rec.encoded for rec in p.records)
print(f"encrypted payload: {len(enc)} bytes")

# Try all key permutations × all 3-op combinations
candidates = []
for key in set(itertools.permutations(KEYVAL)):
    for ops in itertools.product(OPSYMS, repeat=3):
        tbl = build_table(key, ops)
        if tbl is None:
            continue
        dec = enc.translate(tbl)
        # scoring: ratio of zero bytes (real firmware tables = lots of zeros)
        # AND check if decoded contains IEEE 754 float patterns 0x00 0x00 ?? 0x3f (1.0-ish floats)
        zeros = dec.count(0)
        float_hits = 0
        # scan for "00 00 ?? 3f" or "?? 00 80 3f" little-endian-float-ish
        for i in range(0, len(dec) - 3, 4):
            if dec[i+3] in (0x3f, 0x40, 0x41, 0xbf, 0xc0) and dec[i] == 0x00 and dec[i+1] == 0x00:
                float_hits += 1
        candidates.append((zeros, float_hits, key, "".join(ops), dec[:80]))

# Sort by float_hits desc, then zeros desc
candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)

print("\nTOP CANDIDATES (by IEEE-754-like float pattern density):")
print(f"  {'zeros':>5}  {'floats':>6}  key                    ops    first 32 decoded bytes")
for zeros, fhits, key, ops, sample in candidates[:10]:
    keystr = " ".join(f"{k:02x}" for k in key)
    print(f"  {zeros:5d}  {fhits:6d}  ({keystr})  {ops:4s}  {' '.join(f'{b:02x}' for b in sample[:32])}")
