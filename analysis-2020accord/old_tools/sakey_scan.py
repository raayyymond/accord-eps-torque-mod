"""
sakey_scan.py — extract SA-keys ('!' header for x31, headers[4] for x5a)
from every Honda 39990-* rwd in the configured calibration directory.

Output: prints a CSV-like table to stdout. NO writes to C:.
"""
import gzip
import os
import re
import struct
import sys
from pathlib import Path
from binascii import a2b_hex, b2a_hex
from collections import defaultdict

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import CALIB_FILES

def read_artifact(path):
    """Read an artifact without depending on the caller's working directory."""
    return (CALIB_FILES / path).read_bytes()

def parse_x31_headers(data):
    """Parse x31 headers and return {tag_byte: [values_bytes...]}. Returns None on failure."""
    if data[0:3] != b'1\r\n':
        return None
    i = 3
    headers = {}
    try:
        for _ in range(6):
            hp = data[i:i+3]
            if hp[1:3] != b'\r\n':
                return None
            tag = hp[0:1]
            i += 3
            vals = []
            while data[i:i+3] != hp:
                end = data.find(b'\r\n', i)
                if end < 0:
                    return None
                vals.append(data[i:end])
                i = end + 2
            i += 3
            headers[tag] = vals
        return headers
    except Exception:
        return None

def parse_x5a_headers(data):
    """Parse x5a headers and return list-of-6 [values_bytes...]. Returns None on failure."""
    if data[0:3] != b'Z\r\n':
        return None
    i = 3
    try:
        headers = []
        for _ in range(6):
            cnt = data[i]; i += 1
            vals = []
            for _ in range(cnt):
                ln = data[i]; i += 1
                vals.append(data[i:i+ln])
                i += ln
            headers.append(vals)
        return headers
    except Exception:
        return None

def chassis_of(path):
    base = os.path.basename(path)
    # Try dashed: 39990-XXX-YYY
    m = re.search(r'39990[-_]?([A-Za-z0-9]{2,3})[-_]?([A-Za-z0-9]{4})', base)
    if not m:
        return "???"
    return m.group(1).upper()

def main():
    paths = [
        path.name
        for path in CALIB_FILES.glob("39990*")
    ]

    print(f"# Honda EPS rwds found in configured calibration directory: {len(paths)}")
    print("# Columns: container | chassis | filename | sa_keys (! or headers[4]) | cipher_key | versions (/ or headers[3])")
    print()

    # Group results by SA-key signature
    sakey_groups = defaultdict(list)
    parse_failures = []

    for path in sorted(paths):
        try:
            raw = read_artifact(path)
            if path.endswith('.gz'):
                raw = gzip.decompress(raw)
        except Exception as e:
            parse_failures.append((path, f"read: {e}"))
            continue

        fmt = raw[0:1]
        chassis = chassis_of(path)
        fname = os.path.basename(path)
        if fmt == b'1':
            h = parse_x31_headers(raw)
            if h is None:
                parse_failures.append((path, "x31 parse fail"))
                continue
            sa_vals = h.get(b'!', [])
            cipher_vals = h.get(b'&', [])
            ver_vals = h.get(b'/', [])
            sa_str = ",".join(v.decode('ascii', 'replace') for v in sa_vals)
            cipher_str = ",".join(v.decode('ascii', 'replace') for v in cipher_vals)
            ver_str = ",".join(v.decode('ascii', 'replace') for v in ver_vals)
            print(f"x31 | {chassis:3} | {fname:42} | SA=[{sa_str}] | cipher=[{cipher_str}] | ver=[{ver_str}]")
            sakey_groups[(sa_str, "x31")].append((chassis, fname))
        elif fmt == b'Z':
            h = parse_x5a_headers(raw)
            if h is None:
                parse_failures.append((path, "x5a parse fail"))
                continue
            # headers[4] is sa_keys, headers[3] is versions, headers[5] is cipher
            sa_vals = h[4] if len(h) > 4 else []
            cipher_vals = h[5] if len(h) > 5 else []
            ver_vals = h[3] if len(h) > 3 else []
            sa_str = ",".join(b2a_hex(v).decode() for v in sa_vals)
            cipher_str = ",".join(b2a_hex(v).decode() for v in cipher_vals)
            ver_str = ",".join(v.rstrip(b'\x00').decode('ascii', 'replace') for v in ver_vals)
            print(f"x5a | {chassis:3} | {fname:42} | SA=[{sa_str}] | cipher=[{cipher_str}] | ver=[{ver_str}]")
            sakey_groups[(sa_str, "x5a")].append((chassis, fname))
        else:
            parse_failures.append((path, f"unknown fmt {fmt}"))

    print()
    print("=" * 80)
    print("SUMMARY: SA-key groupings")
    print("=" * 80)
    for (sa, fmt), members in sorted(sakey_groups.items(), key=lambda x: -len(x[1])):
        chass = sorted({c for c, _ in members})
        print(f"\n[{fmt}] SA={sa!r}  ({len(members)} files, chassis: {chass})")
        for c, f in members[:5]:
            print(f"    {f}")
        if len(members) > 5:
            print(f"    ... and {len(members)-5} more")

    if parse_failures:
        print()
        print("=" * 80)
        print(f"PARSE FAILURES ({len(parse_failures)}):")
        for p, e in parse_failures:
            print(f"  {p}: {e}")

if __name__ == "__main__":
    main()
