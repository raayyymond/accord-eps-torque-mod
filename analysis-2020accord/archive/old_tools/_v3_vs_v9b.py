"""v3 vs v9b: same workflow as v4 — structure, cipher detection, plaintext diff."""
import sys, os, itertools, operator
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import RWD_DIR
sys.path.insert(0, r"C:\Users\joey\Downloads")
from honda_rwd_decode import parse_x31, decode_x31_record

V3 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v3.rwd")
V4 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v4.rwd")
V5 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v5.rwd")
V9B = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd")
KEYVAL = (0xBF, 0x10, 0x9E)

OPS = {"^": operator.xor, "+": operator.add, "-": lambda a,b: a-b, "*": operator.mul, "&": operator.and_, "|": operator.or_}
OPSYMS = list(OPS.keys())

def build_table(key, ops):
    tbl = bytearray(256); seen = set()
    for c in range(256):
        try:
            v = c
            v = OPS[ops[0]](v, key[0]) & 0xFF
            v = OPS[ops[1]](v, key[1]) & 0xFF
            v = OPS[ops[2]](v, key[2]) & 0xFF
        except (ZeroDivisionError, OverflowError):
            return None
        tbl[c] = v
        seen.add(v)
    if len(seen) != 256: return None
    return bytes(tbl)

def find_cipher(rwd_path):
    with open(rwd_path, "rb") as f:
        raw = f.read()
    p = parse_x31(raw)
    enc = b"".join(r.encoded for r in p.records)
    best = None
    for key in set(itertools.permutations(KEYVAL)):
        for ops in itertools.product(OPSYMS, repeat=3):
            t = build_table(key, ops)
            if t is None: continue
            dec = enc.translate(t)
            zeros = dec.count(0)
            fhits = sum(1 for i in range(0, len(dec)-3, 4)
                        if dec[i+3] in (0x3f,0x40,0x41,0xbf,0xc0) and dec[i]==0 and dec[i+1]==0)
            score = fhits*1000 + zeros
            if best is None or score > best[0]:
                best = (score, key, "".join(ops), zeros, fhits)
    return p, best

def header_summary(p):
    out = []
    for h in p.headers:
        tag = h.prefix[0:1].decode("ascii", "replace")
        vals = [v.decode("latin1", "replace") for v in h.values]
        out.append(f"  {tag!r:4s}: {vals}")
    return "\n".join(out)

def region_summary(p):
    if not p.records: return "no records"
    addrs = [r.address for r in p.records]
    runs = []
    rs = addrs[0]; prev = rs
    for r in p.records[1:]:
        if r.address != prev + 0x80:
            runs.append((rs, prev + 0x80))
            rs = r.address
        prev = r.address
    runs.append((rs, prev + 0x80))
    return " ".join(f"0x{a:X}-0x{b:X}" for a,b in runs)

for label, path in [("v3", V3), ("v4", V4), ("v5", V5), ("v9b", V9B)]:
    print(f"\n=== {label}: {os.path.basename(path)} ===")
    with open(path, "rb") as f:
        raw = f.read()
    p = parse_x31(raw)
    print(f"  size: {len(raw):,} bytes  records: {len(p.records)}")
    print(f"  regions: {region_summary(p)}")
    print(f"  headers:")
    print(header_summary(p))
    score, key, ops, zeros, fhits = find_cipher(path)[1]
    print(f"  best cipher: key={tuple(f'{k:02x}' for k in key)} ops={ops}  (zeros={zeros}, float_hits={fhits})")

# Now diff v3 plaintext vs v9b plaintext at v3's regions
print("\n\n=== v3 vs v9b PLAINTEXT DIFF AT v3's REGIONS ===")
p3, best3 = find_cipher(V3)
score3, key3, ops3, _, _ = best3
print(f"v3 cipher: key={tuple(f'{k:02x}' for k in key3)} ops={ops3}")

p9, best9 = find_cipher(V9B)
score9, key9, ops9, _, _ = best9
print(f"v9b cipher: key={tuple(f'{k:02x}' for k in key9)} ops={ops9}")

def decode_records(p, key, ops):
    t = build_table(key, ops)
    img = {}
    for r in p.records:
        dec = r.encoded.translate(t)
        for i, b in enumerate(dec):
            img[r.address + i] = b
    return img

img3 = decode_records(p3, key3, ops3)
img9 = decode_records(p9, key9, ops9)

# v3 contiguous regions
addrs = sorted(img3.keys())
runs = []
rs = addrs[0]; prev = rs
for a in addrs[1:]:
    if a != prev + 1:
        runs.append((rs, prev + 1)); rs = a
    prev = a
runs.append((rs, prev + 1))

for (lo, hi) in runs:
    eq = sum(1 for a in range(lo, hi) if a in img9 and img3[a] == img9[a])
    df = sum(1 for a in range(lo, hi) if a in img9 and img3[a] != img9[a])
    uncov = sum(1 for a in range(lo, hi) if a not in img9)
    print(f"\n## 0x{lo:06X}-0x{hi:06X} ({hi-lo} bytes): v3==v9b={eq}  v3!=v9b={df}  v9b-uncovered={uncov}")
    if df > 0 and df <= 256:
        diffs = [(a, img3[a], img9[a]) for a in range(lo, hi) if a in img9 and img3[a] != img9[a]]
        # show contiguous diff runs
        druns = []
        drs = diffs[0][0]; dprev = drs
        for a, _, _ in diffs[1:]:
            if a != dprev + 1:
                druns.append((drs, dprev+1)); drs = a
            dprev = a
        druns.append((drs, dprev+1))
        print(f"  diff runs: {len(druns)}")
        for dlo, dhi in druns[:10]:
            h3 = " ".join(f"{img3[dlo+i]:02x}" for i in range(min(dhi-dlo, 32)))
            h9 = " ".join(f"{img9[dlo+i]:02x}" for i in range(min(dhi-dlo, 32)))
            print(f"  0x{dlo:08X}-0x{dhi:08X} ({dhi-dlo}B):")
            print(f"    v3 : {h3}")
            print(f"    v9b: {h9}")
    elif df > 256:
        print(f"  (too many diffs to print individually — showing first 32 bytes of region)")
        h3 = " ".join(f"{img3[lo+i]:02x}" for i in range(32))
        h9 = " ".join(f"{img9[lo+i]:02x}" for i in range(32))
        print(f"  v3 : {h3}")
        print(f"  v9b: {h9}")
