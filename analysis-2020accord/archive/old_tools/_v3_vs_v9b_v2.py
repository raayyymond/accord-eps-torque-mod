"""v3 vs v9b — find each file's cipher using PART-NUMBER STRING as oracle,
then diff plaintexts at overlapping regions."""
import sys, os, itertools, operator
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import RWD_DIR
sys.path.insert(0, r"C:\Users\joey\Downloads")
from honda_rwd_decode import parse_x31

V3 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v3.rwd")
V9B = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd")
KEYVAL = (0xBF, 0x10, 0x9E)
ORACLE = b"39990-TVA-A160"

OPS = {"^": operator.xor, "+": operator.add, "-": lambda a,b: a-b, "&": operator.and_, "|": operator.or_}
OPSYMS = list(OPS.keys())

def build_table(key, ops):
    tbl = bytearray(256); seen = set()
    for c in range(256):
        try:
            v = c
            v = OPS[ops[0]](v, key[0]) & 0xFF
            v = OPS[ops[1]](v, key[1]) & 0xFF
            v = OPS[ops[2]](v, key[2]) & 0xFF
        except Exception:
            return None
        tbl[c] = v
        seen.add(v)
    if len(seen) != 256: return None
    return bytes(tbl)

def find_correct_cipher(path):
    with open(path, "rb") as f:
        p = parse_x31(f.read())
    enc = b"".join(r.encoded for r in p.records)
    hits = []
    for key in set(itertools.permutations(KEYVAL)):
        for ops in itertools.product(OPSYMS, repeat=3):
            t = build_table(key, ops)
            if t is None: continue
            dec = enc.translate(t)
            if ORACLE in dec:
                # zeros score for tie-break (real fw has lots)
                hits.append((dec.count(0), key, "".join(ops), t, dec))
    return p, hits

print("Searching for ciphers that decode each file such that part number appears...\n")

for label, path in [("v3", V3), ("v9b", V9B)]:
    p, hits = find_correct_cipher(path)
    print(f"=== {label} ===")
    print(f"  records: {len(p.records)}  region: 0x{p.records[0].address:X}-0x{p.records[-1].address+0x80:X}")
    print(f"  candidates passing oracle '{ORACLE.decode()}': {len(hits)}")
    for zeros, key, ops, _, _ in sorted(hits, key=lambda x: -x[0]):
        print(f"    key={tuple(f'{k:02x}' for k in key)} ops={ops}  zeros={zeros}")
    if hits:
        best = max(hits, key=lambda x: x[0])
        _, key, ops, tbl, dec = best
        # Mount to absolute addrs
        img = {}
        for r in p.records:
            d = r.encoded.translate(tbl)
            for i, b in enumerate(d):
                img[r.address + i] = b
        # Save for diff
        if label == "v3":   v3_img = img; v3_key = (key, ops)
        else:               v9_img = img; v9_key = (key, ops)
        # Where's the part number?
        # Find in decoded image
        addrs = sorted(img.keys())
        buf = bytearray(b"\xFF" * (addrs[-1] - addrs[0] + 1))
        for a, b in img.items():
            buf[a - addrs[0]] = b
        pos = buf.find(ORACLE)
        if pos >= 0:
            print(f"  part-number string at flash address 0x{addrs[0]+pos:X}")
    print()

# Diff v3 vs v9b at overlap
if 'v3_img' in dir() and 'v9_img' in dir():
    print("=== v3 vs v9b PLAINTEXT DIFF (overlap only) ===")
    overlap = sorted(set(v3_img.keys()) & set(v9_img.keys()))
    only_v3 = sorted(set(v3_img.keys()) - set(v9_img.keys()))
    only_v9 = sorted(set(v9_img.keys()) - set(v3_img.keys()))
    print(f"  overlap bytes: {len(overlap):,}")
    print(f"  v3-only bytes: {len(only_v3):,}  (range: 0x{only_v3[0]:X}-0x{only_v3[-1]:X} if any)" if only_v3 else f"  v3-only bytes: 0")
    print(f"  v9b-only bytes: {len(only_v9):,}")

    eq = sum(1 for a in overlap if v3_img[a] == v9_img[a])
    df = sum(1 for a in overlap if v3_img[a] != v9_img[a])
    print(f"  v3 == v9b: {eq:,}  ({100*eq/len(overlap):.1f}%)")
    print(f"  v3 != v9b: {df:,}  ({100*df/len(overlap):.1f}%)")

    # Find contiguous diff regions
    diffs = [a for a in overlap if v3_img[a] != v9_img[a]]
    if diffs:
        regions = []
        rs = diffs[0]; prev = rs
        for a in diffs[1:]:
            if a != prev + 1:
                regions.append((rs, prev+1)); rs = a
            prev = a
        regions.append((rs, prev+1))
        print(f"\n  contiguous diff regions: {len(regions)}")
        # Show top 20 by size
        regions_by_size = sorted(regions, key=lambda r: -(r[1]-r[0]))
        print(f"  largest diff regions:")
        for lo, hi in regions_by_size[:20]:
            sz = hi - lo
            preview = " ".join(f"{v3_img[lo+i]:02x}" for i in range(min(sz, 12)))
            preview9 = " ".join(f"{v9_img[lo+i]:02x}" for i in range(min(sz, 12)))
            print(f"    0x{lo:08X}-0x{hi:08X}  ({sz:>6,} bytes)  v3: {preview}  v9b: {preview9}")
