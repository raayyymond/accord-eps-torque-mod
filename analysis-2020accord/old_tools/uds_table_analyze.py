"""Analyze the UDS service-permission table found at 0x009330 and find xrefs.

The table is a 4-byte record array: [sid:u8][pad:u16][flags:u8].
Walk it to find its full extent, then scan code for movhi/movea pairs
that build 0x9330 (or any address in the table range) to identify the
dispatcher function.
"""
from __future__ import annotations

import struct
import subprocess
from pathlib import Path
import sys

ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"
DATA = FW.read_bytes()

UDS_NAME = {
    0x10: "DiagnosticSessionControl",
    0x11: "ECUReset",
    0x14: "ClearDTC",
    0x19: "ReadDTCInformation",
    0x22: "ReadDataByIdentifier",
    0x23: "ReadMemoryByAddress",
    0x27: "SecurityAccess",
    0x28: "CommunicationControl",
    0x2A: "ReadDataByPeriodicId",
    0x2C: "DynamicallyDefineDataIdentifier",
    0x2E: "WriteDataByIdentifier",
    0x2F: "InputOutputControlByIdentifier",
    0x31: "RoutineControl",
    0x34: "RequestDownload",
    0x35: "RequestUpload",
    0x36: "TransferData",
    0x37: "RequestTransferExit",
    0x3D: "WriteMemoryByAddress",
    0x3E: "TesterPresent",
    0x83: "AccessTimingParameter",
    0x84: "SecuredDataTransmission",
    0x85: "ControlDTCSetting",
    0x86: "ResponseOnEvent",
    0x87: "LinkControl",
}


def walk_table(start: int, stride: int = 4, max_rows: int = 40) -> list[tuple[int, int, int]]:
    """Walk 4-byte records [sid][00][00][flags] until we find a non-UDS sid."""
    rows = []
    for k in range(max_rows):
        off = start + k * stride
        if off + stride > len(DATA):
            break
        sid = DATA[off]
        b1 = DATA[off + 1]
        b2 = DATA[off + 2]
        flags = DATA[off + 3]
        if sid not in UDS_NAME:
            # Allow zero-row continuation if it looks like end-marker / padding
            if sid == 0:
                # could be end of table
                break
            # Maybe table has a different stride or this is a sub-table boundary
            break
        if b1 != 0 or b2 != 0:
            # If b1/b2 not 00 00 then the structure assumption breaks
            break
        rows.append((off, sid, flags))
    return rows


def find_table_extent_backward(start: int, stride: int = 4) -> int:
    """Walk backward from start to find the true table start."""
    cur = start
    while cur >= 4:
        cand = cur - stride
        sid = DATA[cand]
        b1 = DATA[cand + 1]
        b2 = DATA[cand + 2]
        if sid in UDS_NAME and b1 == 0 and b2 == 0:
            cur = cand
        else:
            break
    return cur


def rizin_xref_search_for_table(addr: int) -> str:
    """Use rizin to search for movhi+movea pairs forming the table address.

    rizin's /v4 finds literal u32 values. The table address as a u32 literal
    is unlikely to appear as such, but movhi 0x0,r0 + movea 0x9330,rA might.
    Easier: search for byte sequence 0x9330 LE.
    """
    # The table at 0x9330 means a movea instruction would need imm=0x9330.
    # The movea+movhi pair must satisfy (imm_hi<<16) + sign_ext_16(lo) = 0x9330,
    # so most likely movhi 0 + movea 0x9330.
    # 0x9330 as little-endian halfword in instruction bytes => "30 93"
    # The full movea encoding for "movea 0x9330, rN, rM" depends on registers.
    # Let's just brute-search for the 16-bit pattern.
    return ""


def search_bytes(needle: bytes) -> list[int]:
    """Find all occurrences of needle in DATA."""
    out = []
    pos = 0
    while True:
        i = DATA.find(needle, pos)
        if i < 0:
            break
        out.append(i)
        pos = i + 1
    return out


def disasm_at(addr: int, n: int = 16) -> str:
    out = subprocess.run(
        ["rizin", "-a", "v850", "-b", "32", "-m", "0x0", "-N",
         "-qc", f"pd {n} @ 0x{addr:x}", str(FW)],
        capture_output=True, text=True,
    )
    return out.stdout


def main():
    # Step 1: identify table extent
    print("=== Step 1: table extent ===")
    fwd = walk_table(0x9330, max_rows=40)
    back = find_table_extent_backward(0x9330)
    print(f"  Walking backward from 0x9330: table starts at 0x{back:06X}")
    full = walk_table(back, max_rows=80)
    print(f"  Full table: {len(full)} records, [0x{full[0][0]:06X} .. 0x{full[-1][0]+3:06X})")
    print()
    print("  Records:")
    for off, sid, flags in full:
        name = UDS_NAME.get(sid, "?")
        print(f"    0x{off:06X}  sid=0x{sid:02X} {name:32s}  flags=0x{flags:02X}")

    # Step 2: search for xrefs by byte-scan for halfword 0x9330 LE
    # AND for movhi+movea pair that resolves to start of table
    table_start = back
    table_end = full[-1][0] + 4 if full else table_start + 4
    print()
    print(f"=== Step 2: searching for code refs to table range [0x{table_start:X}, 0x{table_end:X}) ===")

    # Search for movea imm forms: movea imm16, rA, rB.
    # The full address we want is 0x09320 (if back=0x09320).
    # On V850 movea has 32-bit encoding: 0b0110001A_AAAA_BBBB iiii_iiii_iiii_iiii
    # where AAAAA is dst reg, BBBBB is src reg, imm16 follows.
    # Halfword 2 = imm16 little-endian.
    # So byte sequence at instruction+2..+3 = LE(imm16) = (table_start & 0xFFFF) then (table_start>>8 & 0xFF)
    # For table_start = 0x9320: imm16 = 0x9320, bytes = 20 93
    lo16 = table_start & 0xFFFF
    needle_lo = bytes([lo16 & 0xFF, (lo16 >> 8) & 0xFF])
    print(f"  Searching for halfword 0x{lo16:04X} LE bytes {needle_lo.hex()} ...")
    hits = search_bytes(needle_lo)
    # Filter to code regions only, and only those at instruction-aligned positions
    code_hits = []
    for h in hits:
        # The imm16 of a movea sits at +2 of a 4-byte instruction.
        # So the instruction starts at h-2 (must be 2-byte aligned).
        if (h - 2) % 2 == 0 and 0x24 <= h - 2 < 0x86242:
            code_hits.append(h - 2)
    print(f"  {len(hits)} total occurrences, {len(code_hits)} potentially at movea imm16 positions in code")

    # Disassemble each candidate
    print()
    print("=== Step 3: disassemble candidate sites ===")
    for site in code_hits[:30]:
        # Check if preceding 4 bytes look like 'movhi 0, r0, rX' (since addr = 0x09320 < 0x10000,
        # the high half is 0, so movhi might not even be present — could just be 'movea imm, r0, rX')
        # rizin disasm 4 insns ending at site
        before = max(0x24, site - 8)
        out = subprocess.run(
            ["rizin", "-a", "v850", "-b", "32", "-m", "0x0", "-N",
             "-qc", f"pd 6 @ 0x{before:x}", str(FW)],
            capture_output=True, text=True,
        )
        text = out.stdout
        # Only print if the disasm at site contains 'movea ... 9320' or similar
        if f"{lo16:04x}" in text.lower() or f"0x{lo16:x}" in text.lower() or f"{lo16}" in text:
            print(f"--- site near 0x{site:06X} ---")
            print(text)


if __name__ == "__main__":
    main()
