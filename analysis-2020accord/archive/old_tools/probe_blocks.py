"""List all reconstructed blocks and verify the 130B chunk address sequence is monotone & contiguous within each block."""
import gzip, struct, os, sys
ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_rwd import parse_x31, crack, expected_part

FILES = [
    str(CALIB_FILES / "39990-T2F-A210.rwd.gz"),
    str(CALIB_FILES / "39990-T3L-A210.rwd.gz"),
    str(CALIB_FILES / "39990-TV9-A910.rwd.gz"),
]

for path in FILES:
    raw = open(path,'rb').read()
    if path.endswith('.gz'): raw = gzip.decompress(raw)
    key, blocks, encs, hdrs, hdr_end = parse_x31(raw)
    print("="*72)
    print(f"{os.path.basename(path)}  hdr_end=0x{hdr_end:X}  blocks={len(blocks)}")
    for i,b in enumerate(blocks):
        print(f"  blk[{i:2d}] start=0x{b['start']:X} end=0x{b['start']+b['length']:X} len=0x{b['length']:X}")
    # decode to find the V850 part-string
    exp = expected_part(path)
    table, sym, dec, n = crack(encs, key, exp)
    if dec:
        for i,d in enumerate(dec[-3:]):
            print(f"  last3 decoded blk #{len(dec)-3+i}: head={d[:16].hex(' ')} tail={d[-16:].hex(' ')}")
    print()
