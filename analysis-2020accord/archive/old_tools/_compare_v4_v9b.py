"""One-shot diff: v4 vs v9b .rwd structure. Delete after use."""
import sys, os
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import RWD_DIR
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from encode_eps import parse_x31

V4 = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v4.rwd")
V9B = str(RWD_DIR / "39990-TVA-A160-RECONSTRUCTED-v9b-0x13000-0x100000.rwd")

def summary(path):
    with open(path, "rb") as f:
        data = f.read()
    print(f"\n=== {os.path.basename(path)} ({len(data):,} bytes) ===")
    try:
        parsed = parse_x31(data)
    except Exception as e:
        print(f"  parse failed: {type(e).__name__}: {e}")
        return None
    print(f"  headers: {len(parsed['headers'])} entries")
    for tag, vals in parsed["headers"]:
        # tag is bytes like b'/', b'%', b'!', etc — show ASCII or hex
        tag_str = tag.decode("ascii", errors="replace")
        if isinstance(vals, list):
            shown = [v.hex() if isinstance(v, (bytes, bytearray)) else repr(v) for v in vals]
            print(f"    tag {tag_str!r:4s}: {len(vals)} val(s): {shown[:4]}{' ...' if len(shown)>4 else ''}")
        else:
            print(f"    tag {tag_str!r:4s}: {vals!r}")
    blocks = parsed.get("blocks", [])
    print(f"  blocks: {len(blocks)} flash region(s)")
    total_payload = 0
    for i, blk in enumerate(blocks):
        addr = blk.get("address", "?")
        length = blk.get("length", len(blk.get("data", b"")))
        data_len = len(blk.get("data", b""))
        total_payload += data_len
        end = addr + length if isinstance(addr, int) and isinstance(length, int) else "?"
        print(f"    [{i}] flash 0x{addr:08x}-0x{end:08x}  ({length:,} bytes, payload {data_len:,})" if isinstance(addr,int) else f"    [{i}] {blk!r}")
    print(f"  total payload: {total_payload:,} bytes")
    return parsed

p4 = summary(V4)
p9 = summary(V9B)

if p4 and p9:
    print("\n=== HEADER DIFF ===")
    h4 = {(tag, str(vals)) for tag, vals in p4["headers"]}
    h9 = {(tag, str(vals)) for tag, vals in p9["headers"]}
    only4 = h4 - h9
    only9 = h9 - h4
    if not only4 and not only9:
        print("  headers IDENTICAL")
    else:
        for x in only4: print(f"  v4 only: {x}")
        for x in only9: print(f"  v9b only: {x}")

    print("\n=== BLOCK COVERAGE DIFF ===")
    def regions(p):
        return [(b.get("address"), b.get("length", len(b.get("data", b"")))) for b in p.get("blocks", [])]
    r4 = regions(p4)
    r9 = regions(p9)
    print(f"  v4  regions: {r4}")
    print(f"  v9b regions: {r9}")
