"""UDS dispatcher hunter for code.bin (V850E2 LE).

Strategies:
  A. Byte-window scan: find regions where >= 6 distinct known UDS service IDs
     appear within a small window (suggests either a switch ladder of cmp
     immediates or a function-pointer table).
  B. Constant-pool scan: find every word-aligned u32 in [0x14810, 0x86242]
     where the low byte is a UDS service ID and the upper 3 bytes look like
     a code pointer into code clusters.
  C. V850 'cmp imm5,reg' encoding hunt for cmp 0x27.
"""
from __future__ import annotations

import collections
import struct
from pathlib import Path
import sys

ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"
DATA = FW.read_bytes()

# UDS service IDs we expect in a dispatcher
UDS_REQ_IDS = {
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
    0x2F: "InputOutputControlById",
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

# Positive-response = request | 0x40
UDS_RESP_IDS = {sid | 0x40: name + "_RESP" for sid, name in UDS_REQ_IDS.items()}

# Common UDS NRCs (negative response codes)
UDS_NRC = {
    0x10: "GeneralReject",
    0x11: "ServiceNotSupported",
    0x12: "SubFunctionNotSupported",
    0x13: "IncorrectMessageLength",
    0x22: "ConditionsNotCorrect",
    0x24: "RequestSequenceError",
    0x31: "RequestOutOfRange",
    0x33: "SecurityAccessDenied",
    0x35: "InvalidKey",
    0x36: "ExceedNumberOfAttempts",
    0x37: "RequiredTimeDelayNotExpired",
    0x70: "UploadDownloadNotAccepted",
    0x71: "TransferDataSuspended",
    0x72: "GeneralProgrammingFailure",
    0x78: "RequestCorrectlyReceivedResponsePending",
    0x7E: "SubFunctionNotSupportedInActiveSession",
    0x7F: "ServiceNotSupportedInActiveSession",
}


def strategy_a_proximity_scan(window: int = 256, min_distinct: int = 6) -> list[tuple[int, list[int]]]:
    """Find every window of `window` bytes containing at least `min_distinct` UDS req IDs.

    Sliding window with low overlap (step=64) — we just want hot regions.
    """
    hits = []
    req_set = set(UDS_REQ_IDS.keys())
    step = 64
    for start in range(0, len(DATA) - window, step):
        chunk = DATA[start:start + window]
        seen_ids = collections.OrderedDict()
        for i, b in enumerate(chunk):
            if b in req_set and b not in seen_ids:
                seen_ids[b] = i
        if len(seen_ids) >= min_distinct:
            hits.append((start, list(seen_ids.keys())))
    # Coalesce overlapping hits (same region picked up at multiple step starts)
    coalesced = []
    last_end = -1
    for start, ids in hits:
        if start < last_end:
            continue
        coalesced.append((start, ids))
        last_end = start + window
    return coalesced


def strategy_b_function_pointer_table() -> list[tuple[int, list[tuple[int, int, int]]]]:
    """Scan for arrays of [u8_or_u16 service_id | u32 handler_addr] records.

    Common dispatcher layout:
        struct { uint8_t sid; uint8_t flags; uint32_t handler; }   // 6 bytes
        struct { uint16_t sid; uint16_t flags; uint32_t handler; } // 8 bytes
        struct { uint8_t sid; uint32_t handler; }                  // 5 bytes (rare, unaligned)
        struct { uint32_t handler; uint8_t sid; uint8_t flags; uint16_t pad; } // 8 bytes
    Detection: a region where consecutive records share a fixed stride and
    every record's SID slot is a known UDS req ID, while the addr slot
    decodes to a valid code address.
    """
    code_lo = 0x00000024
    code_hi = 0x00086243
    req_set = set(UDS_REQ_IDS.keys())

    candidates: list[tuple[int, list[tuple[int, int, int]]]] = []

    # Try strides 4, 5, 6, 8, 12; SID at byte offset 0 or 4 of the record
    for stride in (4, 5, 6, 8, 12, 16):
        for sid_off in (0, 1, 2, 3, 4):
            # The u32 handler can be at any 4-byte-aligned slot within the record;
            # try the two most likely positions.
            for addr_off in (stride - 4, 0 if sid_off >= 4 else 2 if sid_off < 2 else 4):
                if addr_off < 0 or addr_off + 4 > stride:
                    continue
                if addr_off == sid_off:
                    continue
                # Sweep table-start candidates
                for start in range(0x14000, len(DATA) - stride * 8, 2):
                    # Need at least 6 consecutive valid records
                    n_valid = 0
                    records: list[tuple[int, int, int]] = []
                    for k in range(20):  # cap scan at 20 records
                        rec_off = start + k * stride
                        if rec_off + stride > len(DATA):
                            break
                        sid = DATA[rec_off + sid_off]
                        addr = struct.unpack_from("<I", DATA, rec_off + addr_off)[0]
                        if sid not in req_set:
                            break
                        if not (code_lo <= addr < code_hi):
                            break
                        records.append((rec_off, sid, addr))
                        n_valid += 1
                    if n_valid >= 6:
                        candidates.append((start, records))
    # De-duplicate by start address
    seen_starts = set()
    out = []
    for start, recs in candidates:
        if start in seen_starts:
            continue
        seen_starts.add(start)
        out.append((start, recs))
    return out


def strategy_c_cmp_27_scan() -> list[int]:
    """Find V850 'cmp 0x27, reg' or 'mov 0x27, reg' encodings.

    V850 cmp imm5,reg: 16-bit, format 0b1011_0RRR_RRii_iiir? — but 0x27 is
    > 5 bits (39 dec), so 'cmp 0x27,r' uses the imm5 *register* form via
    a preceding 'mov 0x27, rN' instruction.
    'mov imm5,reg' is 0b0001_0iii_iiRR_RRRR for small imms; for 0x27 which
    is also > 5 bits (max imm5 = 0x1F), use 'movea 0x27, r0, rN' which is
    a 32-bit instruction.

    movea encoding: 0b0110_001A_AAAA_RRRR  iiii_iiii_iiii_iiii  (op=0x31)
    -> first halfword pattern: 0110_001A_AAAA_RRRR where 'A' is dst reg
    high bit (5-bit reg = AAAAA), R is src reg.
    For movea 0x27, r0, rN: src=r0=0, imm=0x0027.
    Halfword 1: 0b0110_001<dst5>_0000_0000 == 0x6200 | (dst5<<8) ... actually
    rizin shows the byte order so easier to just search for the byte
    sequence: low-halfword = 0x6260 (dst=r12 example) is too specific.

    Easier: search for the *literal halfword 0x0027 at an even offset*,
    immediately preceded by a halfword whose top 6 bits are 011000 (0x18..0x1B
    in the high byte). That captures all movea/movhi/addi imm16 forms with
    value 0x27.

    Even easier still: just locate all 2-byte-aligned 0x0027 little-endian
    halfwords in code clusters and report counts/positions for follow-up
    disasm.
    """
    code_ranges = [(0x000024, 0x00EF72), (0x014810, 0x086242)]
    hits = []
    for lo, hi in code_ranges:
        for off in range(lo, hi - 1, 2):
            if DATA[off] == 0x27 and DATA[off + 1] == 0x00:
                hits.append(off)
    return hits


def hexdump_window(addr: int, length: int = 64) -> str:
    chunk = DATA[addr:addr + length]
    lines = []
    for i in range(0, len(chunk), 16):
        row = chunk[i:i + 16]
        hexs = " ".join(f"{b:02x}" for b in row)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"  0x{addr+i:06X}  {hexs:<48s}  {asc}")
    return "\n".join(lines)


def main():
    print("=== Strategy A: UDS service-ID proximity windows ===")
    print(f"  (window=256B, min_distinct=8)")
    hits_a = strategy_a_proximity_scan(window=256, min_distinct=8)
    print(f"  Found {len(hits_a)} hot windows.")
    for start, ids in hits_a[:30]:
        id_str = ", ".join(f"0x{i:02X}" for i in ids)
        print(f"    0x{start:06X}  ({len(ids)} distinct): {id_str}")

    print()
    print("=== Strategy A (tighter): min_distinct=10 ===")
    hits_a2 = strategy_a_proximity_scan(window=512, min_distinct=10)
    print(f"  Found {len(hits_a2)} hot windows with >= 10 distinct service IDs in 512B.")
    for start, ids in hits_a2[:20]:
        id_str = ", ".join(f"0x{i:02X}" for i in ids)
        print(f"    0x{start:06X}  ({len(ids)} distinct): {id_str}")
        # Check if 0x27 is in the window
        if 0x27 in ids:
            print(f"      [HAS 0x27 SecurityAccess]")

    print()
    print("=== Strategy B: function-pointer-table candidates ===")
    hits_b = strategy_b_function_pointer_table()
    print(f"  Found {len(hits_b)} candidate tables.")
    for start, recs in hits_b[:20]:
        sids = [f"0x{s:02X}" for _, s, _ in recs]
        addrs = [f"0x{a:06X}" for _, _, a in recs]
        print(f"    table @ 0x{start:06X}: {len(recs)} records")
        print(f"      sids:  {', '.join(sids)}")
        print(f"      addrs: {', '.join(addrs)}")
        if 0x27 in [s for _, s, _ in recs]:
            print(f"      [HAS 0x27 SecurityAccess]")

    print()
    print("=== Strategy C: 0x0027 LE halfword in code clusters ===")
    hits_c = strategy_c_cmp_27_scan()
    print(f"  Found {len(hits_c)} 0x0027-LE halfwords in code clusters.")
    print(f"  First 40: {[hex(h) for h in hits_c[:40]]}")


if __name__ == "__main__":
    main()
