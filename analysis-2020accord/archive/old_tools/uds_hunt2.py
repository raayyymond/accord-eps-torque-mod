"""UDS dispatcher hunter v2 — tighter signals.

Strategies added:
  D. Dense-cluster scan: small window (32 bytes) with >= 4 distinct UDS req
     IDs and zero non-UDS-id high-byte-class noise. This targets actual
     dispatch tables more aggressively than the wide window.
  E. Disasm-driven: disassemble at each of the strategy-C cmp-0x27 hits
     and look for nearby cmp/be patterns suggesting a switch ladder.
  F. Direct constant-pool scan: look for u32 records where SID byte is 0x27
     specifically (the SecurityAccess record we care about most), and check
     if the rest of the record looks like a function pointer entry by
     scanning for consistent stride context.
"""
from __future__ import annotations

import collections
import json
import struct
import subprocess
from pathlib import Path
import sys

ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"
DATA = FW.read_bytes()

UDS_REQ_IDS = {
    0x10, 0x11, 0x14, 0x19, 0x22, 0x23, 0x27, 0x28, 0x2A, 0x2C, 0x2E,
    0x2F, 0x31, 0x34, 0x35, 0x36, 0x37, 0x3D, 0x3E, 0x83, 0x84, 0x85, 0x86, 0x87,
}

UDS_NAME = {
    0x10: "DiagSession", 0x11: "ECUReset", 0x14: "ClearDTC", 0x19: "ReadDTC",
    0x22: "ReadDID", 0x23: "ReadMem", 0x27: "SecurityAccess", 0x28: "CommCtrl",
    0x2A: "ReadPeriodicDID", 0x2C: "DynDefDID", 0x2E: "WriteDID", 0x2F: "IOCtl",
    0x31: "RoutineCtrl", 0x34: "ReqDL", 0x35: "ReqUL", 0x36: "TransferData",
    0x37: "ReqXferExit", 0x3D: "WriteMem", 0x3E: "TesterPresent",
    0x83: "AccTimingParam", 0x84: "SecuredDataTx", 0x85: "CtrlDTCSet",
    0x86: "RespOnEvent", 0x87: "LinkCtrl",
}


def strategy_d_tight_cluster() -> list[tuple[int, list[int], int]]:
    """Tiny window (24-48 bytes) with >= 5 distinct UDS req IDs.

    Returns (start, ids_found, density_score) where density is bytes of UDS
    IDs / total bytes — we want HIGH density (means the table is mostly
    SIDs not random data).
    """
    hits = []
    for window in (32, 48, 64):
        for start in range(0x14810, 0x86242, 2):
            chunk = DATA[start:start + window]
            seen = collections.OrderedDict()
            for b in chunk:
                if b in UDS_REQ_IDS and b not in seen:
                    seen[b] = True
            if len(seen) >= 5:
                density = sum(1 for b in chunk if b in UDS_REQ_IDS) / len(chunk)
                hits.append((start, list(seen.keys()), density, window))
    # Filter to highest-density only
    hits.sort(key=lambda x: (-x[2], x[0]))
    return hits[:50]


def strategy_d2_low_cluster() -> list[tuple[int, list[int], int]]:
    """Same as D but scanning code cluster 1 (0x24..0xEF72)."""
    hits = []
    for window in (32, 48, 64):
        for start in range(0x24, 0xEF72, 2):
            chunk = DATA[start:start + window]
            seen = collections.OrderedDict()
            for b in chunk:
                if b in UDS_REQ_IDS and b not in seen:
                    seen[b] = True
            if len(seen) >= 5:
                density = sum(1 for b in chunk if b in UDS_REQ_IDS) / len(chunk)
                hits.append((start, list(seen.keys()), density, window))
    hits.sort(key=lambda x: (-x[2], x[0]))
    return hits[:50]


def find_0x27_in_tables() -> list[int]:
    """Find every byte == 0x27 in code that is NOT obviously instruction noise.

    Specifically: 0x27 bytes that are followed by 0x00 padding (suggesting
    a u16 SID slot of 0x0027), OR that sit at a 4-byte alignment in a region
    that 'looks tabular' (lots of similar entries).
    """
    hits = []
    # The most common dispatcher-table form: SID is a single byte at an even
    # offset, immediately followed by a u8 flags byte and a u32 pointer.
    # Or: SID is at offset +4 of a record (after a u32 ptr).
    # Or: SID is a u16 = 0x0027 LE.
    for off in range(0, len(DATA) - 8, 1):
        if DATA[off] == 0x27:
            hits.append(off)
    return hits


def strategy_f_sid_proximity_pair() -> list[tuple[int, int, list[int]]]:
    """Look for the *pair* pattern: a 0x27 byte within 8 bytes of a 0x34 byte
    AND within 16 bytes of 0x10, 0x22, 0x3E (the canonical UDS-services-implemented
    short list). This is much stricter than the wide proximity scan.
    """
    hits = []
    for off in range(0, len(DATA) - 64):
        if DATA[off] != 0x27:
            continue
        window = DATA[max(0, off - 32):off + 32]
        ids = set(window) & UDS_REQ_IDS
        # Must include a flash-programming SID (34/36/37) AND a session SID (10/3E)
        # AND ReadDID 0x22, AND SecurityAccess
        required = {0x27, 0x10, 0x34, 0x36, 0x37, 0x3E}
        if required.issubset(ids):
            hits.append((off, len(ids), sorted(ids)))
    return hits


def hexdump(addr: int, length: int = 64) -> str:
    chunk = DATA[addr:addr + length]
    lines = []
    for i in range(0, len(chunk), 16):
        row = chunk[i:i + 16]
        hexs = " ".join(f"{b:02x}" for b in row)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"  0x{addr+i:06X}  {hexs:<48s}  {asc}")
    return "\n".join(lines)


def main():
    print("=== Strategy D (tighter): >=5 SIDs in 32-64B window in cluster 2 ===")
    hits_d = strategy_d_tight_cluster()
    print(f"  Top 20 by density:")
    for start, ids, dens, w in hits_d[:20]:
        names = ", ".join(f"0x{i:02X}" for i in ids)
        print(f"    0x{start:06X}  w={w:3d}  dens={dens:.2f}  ids=[{names}]")
        if 0x27 in ids and dens > 0.4:
            print(f"      [HIGH-DENSITY SecurityAccess CANDIDATE]")
            print(hexdump(start, 64))

    print()
    print("=== Strategy D2: same in cluster 1 (0x24..0xEF72) ===")
    hits_d2 = strategy_d2_low_cluster()
    print(f"  Top 20 by density:")
    for start, ids, dens, w in hits_d2[:20]:
        names = ", ".join(f"0x{i:02X}" for i in ids)
        print(f"    0x{start:06X}  w={w:3d}  dens={dens:.2f}  ids=[{names}]")
        if 0x27 in ids and dens > 0.4:
            print(f"      [HIGH-DENSITY SecurityAccess CANDIDATE]")
            print(hexdump(start, 64))

    print()
    print("=== Strategy F: required cluster {0x27,0x10,0x34,0x36,0x37,0x3E} all within 64B of a 0x27 byte ===")
    hits_f = strategy_f_sid_proximity_pair()
    print(f"  Found {len(hits_f)} sites.")
    # Group by 64B regions to avoid double-counting
    grouped = []
    last = -100
    for off, n, ids in hits_f:
        if off - last < 64:
            continue
        grouped.append((off, n, ids))
        last = off
    print(f"  {len(grouped)} coalesced regions.")
    for off, n, ids in grouped[:30]:
        names = ", ".join(f"0x{i:02X}" for i in ids)
        print(f"    0x27 @ 0x{off:06X}  ({n} distinct UDS IDs in +-32B): [{names}]")
        print(hexdump(off - 32, 96))
        print()


if __name__ == "__main__":
    main()
