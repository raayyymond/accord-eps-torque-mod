"""Decrypt v4 + v9b with honda_rwd_decode and diff at v4's regions. One-shot."""
import sys, os
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import RWD_DIR
sys.path.insert(0, r"C:\Users\joey\Downloads")
from honda_rwd_decode import parse_x31, decode_x31_record

V4 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v4.rwd")
V9B = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd")
KEY = (0xBF, 0x10, 0x9E)
OPS = "^^-"

def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    p = parse_x31(raw)
    # sparse {flash_address: byte}
    img = {}
    for rec in p.records:
        dec = decode_x31_record(rec.encoded, KEY, OPS)
        for i, b in enumerate(dec):
            img[rec.address + i] = b
    # also compute contiguous regions for printing
    addrs = sorted(img.keys())
    runs = []
    if addrs:
        run_start = addrs[0]; prev = run_start
        for a in addrs[1:]:
            if a != prev + 1:
                runs.append((run_start, prev + 1))
                run_start = a
            prev = a
        runs.append((run_start, prev + 1))
    return p, img, runs

print(f"key = {' '.join(f'{b:02x}' for b in KEY)}   ops = {OPS}")

p4, img4, runs4 = load(V4)
p9, img9, runs9 = load(V9B)

print(f"\nv4  file size = {len(p4.raw):,}  records = {len(p4.records)}  regions = {runs4}")
print(f"v9b file size = {len(p9.raw):,}  records = {len(p9.records)}  regions = {[(hex(a),hex(b)) for a,b in runs9]}")
print(f"v4 checksum ok? {p4.checksum_ok}    v9b checksum ok? {p9.checksum_ok}")

# Sanity: probe for part number in each decoded image
def find_probe(img, probe):
    if not img: return -1
    lo = min(img); hi = max(img) + 1
    # only check contiguous spans we have
    buf = bytearray(b"\x00" * (hi - lo))
    for a, b in img.items():
        buf[a - lo] = b
    pos = buf.find(probe)
    return (pos + lo) if pos >= 0 else -1

for probe in (b"39990-TVA-A160", b"39990-TVA-A110", b"2018/01/30"):
    p4_pos = find_probe(img4, probe)
    p9_pos = find_probe(img9, probe)
    print(f"  probe {probe!r:30s}: v4 @ {hex(p4_pos)},   v9b @ {hex(p9_pos)}")

print("\n=== DIFF AT v4's REGIONS ===")
for (lo, hi) in runs4:
    print(f"\n## region 0x{lo:06X}-0x{hi:06X}  ({hi-lo} bytes)")
    v9_cov = sum(1 for a in range(lo, hi) if a in img9)
    print(f"  v9b coverage of this region: {v9_cov}/{hi-lo}")
    if v9_cov == 0:
        continue
    diffs = []
    for a in range(lo, hi):
        if a in img9 and img4[a] != img9[a]:
            diffs.append((a, img4[a], img9[a]))
    eq = sum(1 for a in range(lo, hi) if a in img9 and img4[a] == img9[a])
    print(f"  v4 == v9b: {eq} bytes   v4 != v9b: {len(diffs)} bytes")
    if diffs:
        # Compress diff into runs
        runs = []
        rs = diffs[0][0]; prev = rs
        for off, _, _ in diffs[1:]:
            if off != prev + 1:
                runs.append((rs, prev + 1))
                rs = off
            prev = off
        runs.append((rs, prev + 1))
        print(f"  contiguous diff runs: {len(runs)}")
        for (rlo, rhi) in runs[:20]:
            # Show side-by-side hex for this run (cap at 64 bytes per run for printing)
            shown = min(rhi - rlo, 64)
            h4 = " ".join(f"{img4[rlo+i]:02x}" for i in range(shown))
            h9 = " ".join(f"{img9[rlo+i]:02x}" for i in range(shown))
            tag = "" if rhi - rlo <= 64 else f"  (showing first 64 of {rhi-rlo})"
            print(f"\n  0x{rlo:08X}-0x{rhi:08X}  ({rhi-rlo} bytes){tag}")
            print(f"    v4 : {h4}")
            print(f"    v9b: {h9}")
        if len(runs) > 20:
            print(f"  ... and {len(runs)-20} more runs")
