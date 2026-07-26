"""Examine x31 file tail in detail and verify a checksum hypothesis."""
import gzip, struct, os
import sys

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES

FILES = [
    str(CALIB_FILES / "39990-T2F-A210.rwd.gz"),
    str(CALIB_FILES / "39990-T3L-A210.rwd.gz"),
    str(CALIB_FILES / "39990-TV9-A910.rwd.gz"),
]

for path in FILES:
    raw = open(path,'rb').read()
    if path.endswith('.gz'): raw = gzip.decompress(raw)
    print("="*72)
    print(f"{os.path.basename(path)}  total_len=0x{len(raw):X}")
    print(f"  last 32 bytes: {raw[-32:].hex(' ')}")
    # Hypothesis: file_checksum = sum(all_bytes_before_checksum) & 0xFFFFFFFF, LE
    body = raw[:-4]
    chk = sum(body) & 0xFFFFFFFF
    stored = struct.unpack('<I', raw[-4:])[0]
    print(f"  sum(body)        = 0x{chk:08X}")
    print(f"  stored trailer LE= 0x{stored:08X}")
    print(f"  MATCH (LE sum)?  = {chk == stored}")
    # Try BE
    stored_be = struct.unpack('>I', raw[-4:])[0]
    print(f"  stored trailer BE= 0x{stored_be:08X}")
    print(f"  MATCH (BE sum)?  = {chk == stored_be}")

    # Now: figure out the EOF sentinel by reverse-walking 130-byte chunks
    # from the parser perspective: the chunk loop walks payload as [hi][mid][128B],
    # where addr = (hi<<12)|(mid<<4). The data after the final real block must be
    # the wrap/EOF sentinel.
    i = 3
    for h in range(6):
        hp = raw[i:i+3]; i += 3
        while raw[i:i+3] != hp:
            end = raw.find(b'\x0d\x0a', i); i = end + 2
        i += 3
    payload_start = i
    payload_bytes = raw[payload_start:-4]
    print(f"  payload range: 0x{payload_start:X}..0x{len(raw)-4:X} (len 0x{len(payload_bytes):X})")
    # Chunk count
    n_chunks = len(payload_bytes) // 130
    rem = len(payload_bytes) % 130
    print(f"  130B chunks: {n_chunks}  remainder: {rem}")
    # Last 3 chunks
    for k in range(max(0, n_chunks-3), n_chunks):
        chunk = payload_bytes[k*130:(k+1)*130]
        addr = (chunk[0]<<12)|(chunk[1]<<4)
        print(f"    chunk[{k}] addr=0x{addr:X} head={chunk[:4].hex(' ')} tail={chunk[-8:].hex(' ')}")
    # Also: does the decoder's loop stop before a sentinel? Check whether
    # `range(0, len(fw)-chunk+1, chunk)` truncates a partial sentinel.
    # If rem != 0, the parser ignores rem bytes (trailing sentinel material).
    if rem:
        print(f"    trailing-after-last-chunk bytes (0x{rem:X}): {payload_bytes[n_chunks*130:].hex(' ')}")
    print()
