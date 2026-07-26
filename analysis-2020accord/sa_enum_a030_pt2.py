#!/usr/bin/env python3
"""
Part 2: Deep trace of 0x3EBD4 dispatcher and 0x514AE jsr @r5 path.
Focus:
  1. The literal @0x4A864 = 0x0003EBD4. Who loads it? (MOV.L loader search)
  2. The function containing 0x3EC1E (which loads the orphan table via literal @0x3EDA0).
     Trace: what is the sub-func value at that point? How is the table indexed?
  3. What function contains 0x3EC76 (cmp/eq #0x08)?  Is it part of the orphan dispatcher?
  4. The 0x514AE literal pool: literal @0x51608 = 0x00054F98 (verifier).
     What function contains 0x514AE? What calls IT?
  5. What does literal @0x50814 = 0x00054F98 and @0x50818 = 0x00054F6A feed?
     (caller context around 0x50800-0x50830)
  6. Disasm 0x3EC00-0x3EE00 to see full dispatcher body.
  7. BSR analysis: all callers of the function at 0x3EBD4 via BSR/indirect.
  8. Look at 0x3EDA0 loader context — 0x3EC1E loads the orphan table ptr.
  9. Session-state compares in dispatcher body (0x3EBD4 function).
  10. What is at literal @0x4A864-0x4A870 (context of the 0x3EBD4 address in table)?
"""

import struct
import sys
from firmware_paths import OTHER_BINS

BIN_PATH = OTHER_BINS / '39990-TBA-A030 (stock).bin'

try:
    import capstone
    HAVE_CAPSTONE = True
except ImportError:
    HAVE_CAPSTONE = False

def load_bin(path):
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    print(f"Loaded: {len(data):,} bytes")
    return data

def be16(data, off): return struct.unpack_from('>H', data, off)[0]
def be32(data, off): return struct.unpack_from('>I', data, off)[0]

def disasm_range(data, start, length):
    if not HAVE_CAPSTONE:
        for i in range(0, min(length, 128), 2):
            if start + i + 1 < len(data):
                print(f"    {start+i:#06x}: {data[start+i]:02x}{data[start+i+1]:02x}")
        return
    md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2A | capstone.CS_MODE_BIG_ENDIAN)
    md.detail = True
    chunk = bytes(data[start:start+length])
    for insn in md.disasm(chunk, start):
        print(f"    {insn.address:#06x}: {insn.mnemonic:<14} {insn.op_str}")

def find_mov_l_loading_literal(data, literal_pool_addr, window=1024):
    """Find MOV.L @(disp,PC),Rn that loads from literal_pool_addr."""
    hits = []
    start = max(0, literal_pool_addr - window)
    end = min(len(data), literal_pool_addr + 4)
    for off in range(start, end, 2):
        hw = be16(data, off)
        if (hw >> 12) == 0xD:  # MOV.L @(disp,PC),Rn
            rn = (hw >> 8) & 0xF
            d = hw & 0xFF
            target = (off + 2 + d * 4) & ~3
            if target == literal_pool_addr:
                hits.append((off, rn, target))
    return hits

def scan_bsr_to(data, target_addr):
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw >> 12) == 0xB:
            d = hw & 0xFFF
            if d & 0x800: d = d - 0x1000
            dest = off + 4 + d * 2
            if dest == target_addr:
                hits.append(off)
    return hits

def scan_jsr_r_indirect(data):
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw & 0xF00F) == 0x400B:
            rn = (hw >> 8) & 0xF
            hits.append((off, rn))
    return hits

def scan_literal_for(data, target_addr):
    target_bytes = struct.pack('>I', target_addr)
    hits = []
    off = 0
    while True:
        idx = data.find(target_bytes, off)
        if idx == -1:
            break
        hits.append(idx)
        off = idx + 1
    return hits

def main():
    data = load_bin(BIN_PATH)

    print("\n" + "="*70)
    print("A. Who loads literal @0x4A864 (= 0x0003EBD4)?")
    print("   Searching for MOV.L with target 0x4A864 in wide window")
    print("="*70)
    # 0x4A864 is a literal pool location — find all MOV.L that load FROM it
    loaders = find_mov_l_loading_literal(data, 0x4A864, window=4096)
    print(f"  MOV.L loaders of 0x4A864 (within ±4096 bytes): {len(loaders)}")
    for addr, rn, tgt in loaders:
        print(f"    {addr:#06x}: mov.l @(disp,pc),r{rn}  -> {tgt:#06x}")
        disasm_range(data, addr - 16, 64)

    # Also check if 0x4A864 itself could be loaded differently
    # (e.g. via a table lookup at a known base)
    print(f"\n  All literal occurrences of 0x0004A864 (as pointer to this slot):")
    hits = scan_literal_for(data, 0x4A864)
    for h in hits:
        print(f"    @{h:#06x}: {data[h:h+4].hex()}")

    print("\n" + "="*70)
    print("B. Context around literal 0x4A864 in the table (wider view: 0x4A840-0x4AB00)")
    print("   — looking for the full 10-record table structure and sub-func bytes")
    print("="*70)
    print("  Bytes 0x4A840-0x4AB00 (stride analysis — each record should be uniform):")
    # From prior analysis: records contain sub-func bytes 0x01,0x07,0x41,0x7B,0x61 + 0x02,0x08,0x42,0x7C,0x62
    # Let's print 12-byte and 8-byte aligned views
    # Earlier analysis shows 0x4AA0C has first record: 01 00 ...
    # Also 0x4AA22: 00 03 eb 20 — that 0x03EB20 looks like it could be an address (0x3EB20 near orphan dispatcher)
    print("  Checking if embedded 4-byte BE values in table are code addresses:")
    for off in range(0x4A860, min(0x4AB00, len(data)-3), 4):
        val = be32(data, off)
        if 0x00003E00 <= val <= 0x00060000:
            print(f"    @{off:#06x}: {val:#010x} (code-range address)")

    print("\n" + "="*70)
    print("C. Full disasm of 0x3EBD4 function body (0x3EBD4-0x3EF00)")
    print("   — especially cmp/eq patterns and table indexing")
    print("="*70)
    disasm_range(data, 0x3EBD4, 0x200)  # 512 bytes

    print("\n" + "="*70)
    print("D. Disasm 0x3EC60-0x3ED30 (orphan table load and table walk region)")
    print("="*70)
    disasm_range(data, 0x3EC60, 0xD0)

    print("\n" + "="*70)
    print("E. Context around 0x3EC76 (cmp/eq #0x08 — is it in orphan dispatcher?)")
    print("="*70)
    print("  0x3EC76 disasm context:")
    disasm_range(data, 0x3EC60, 0x40)

    print("\n" + "="*70)
    print("F. Who calls the function containing 0x514AE?")
    print("   Function starts somewhere before 0x51400 — find BSR callers")
    print("="*70)
    # Scan for BSR to addresses 0x51400-0x51490
    print("  BSR to 0x51400 (function containing jsr @r5 at 0x514AE):")
    bsr_hits = scan_bsr_to(data, 0x51400)
    print(f"    Count: {len(bsr_hits)}")
    for h in bsr_hits:
        print(f"    {h:#06x}: BSR 0x51400")
        disasm_range(data, h - 16, 48)

    print("\n  BSR to 0x51486 (second function in block, starts at 0x51486):")
    bsr_hits2 = scan_bsr_to(data, 0x51486)
    print(f"    Count: {len(bsr_hits2)}")
    for h in bsr_hits2:
        print(f"    {h:#06x}: BSR 0x51486")
        disasm_range(data, h - 16, 48)

    # The literal at 0x51608 = 0x00054F98 is loaded by MOV.L at 0x514AE and 0x514DC
    # 0x514AE is in a subroutine that starts before 0x51400
    # Let's find what BSR calls 0x51400 region
    for target in [0x51400, 0x51486, 0x51488]:
        hits = scan_bsr_to(data, target)
        if hits:
            print(f"\n  BSR to {target:#06x}: {hits}")

    print("\n" + "="*70)
    print("G. Context around literals at 0x50814/0x50818 (verifier/key_calc ptrs)")
    print("   — find what function these belong to")
    print("="*70)
    disasm_range(data, 0x507E0, 0xC0)

    print("\n" + "="*70)
    print("H. Disasm 0x50800-0x51000 — full context of verifier/key_calc literal area")
    print("="*70)
    disasm_range(data, 0x50800, 0x200)

    print("\n" + "="*70)
    print("I. All BSR to 0x50000-0x51000 range (find callers of functions there)")
    print("="*70)
    # Find which functions BSR into the 0x50000 region
    found = {}
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw >> 12) == 0xB:
            d = hw & 0xFFF
            if d & 0x800: d = d - 0x1000
            dest = off + 4 + d * 2
            if 0x50000 <= dest <= 0x51500:
                found.setdefault(dest, []).append(off)
    for dest in sorted(found.keys()):
        callers = found[dest]
        print(f"  BSR to {dest:#06x}: {len(callers)} callers")
        for c in callers[:5]:
            print(f"    from {c:#06x}")

    print("\n" + "="*70)
    print("J. Disasm 0x52700-0x52A00 — SA handler preamble, looking for session-state reads")
    print("="*70)
    disasm_range(data, 0x52700, 0x200)

    print("\n" + "="*70)
    print("K. Disasm 0x52A00-0x52D00 — SA handler sub-func dispatch (full L1 handler)")
    print("="*70)
    disasm_range(data, 0x52A00, 0x300)

    print("\n" + "="*70)
    print("L. What is the function at 0x52B6C (called at 0x536CC from UDS router — SID 0x28?)")
    print("="*70)
    print(f"  cmp/eq #0x28 = 0x8828 scan:")
    for off in range(0, len(data)-1, 2):
        if data[off] == 0x88 and data[off+1] == 0x28:
            print(f"    {off:#06x}: 88 28 (cmp/eq #0x28)")
    disasm_range(data, 0x52B6C, 0x80)

    print("\n" + "="*70)
    print("M. Check sub-func #0x07 context at 0x53580 (cmp/eq #7 hit)")
    print("="*70)
    disasm_range(data, 0x53560, 0x60)

    print("\n" + "="*70)
    print("N. Extended check: bytes around orphan table record boundaries")
    print("   Table starts 0x4A9EC based on pointer scan, confirm stride")
    print("="*70)
    # From scan: first pointer candidate at 0x3E870 -> 0x4A96C
    # 0x4A864 contains 0x0003EBD4 (the dispatcher address)
    # Let's read a big chunk of the table region including pre-table
    print("  Bytes 0x4A850-0x4AB20 (full table view, 12-byte stride check):")
    for off in range(0x4A850, min(0x4AB20, len(data)), 2):
        b0, b1 = data[off], data[off+1]
        marker = ""
        # flag bytes that match known sub-func values
        if b0 in (0x01, 0x02, 0x07, 0x08, 0x41, 0x42, 0x61, 0x62, 0x7B, 0x7C):
            marker = f"  <-- sub-func {b0:#04x}"
        elif b1 in (0x01, 0x02, 0x07, 0x08, 0x41, 0x42, 0x61, 0x62, 0x7B, 0x7C):
            marker = f"  <-- sub-func {b1:#04x}"
        print(f"    {off:#06x}: {b0:02x} {b1:02x}{marker}")

    print("\nDONE.")

if __name__ == '__main__':
    main()
