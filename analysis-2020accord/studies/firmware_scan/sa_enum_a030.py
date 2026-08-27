#!/usr/bin/env python3
"""
SA entry-point enumeration for 39990-TBA-A030 (stock).bin
ISA: Renesas SH-2A, big-endian, file_offset == flash_address.

Searches for ALL paths that can reach:
  - 0x529F8  (SA main handler, known entry)
  - 0x54F6A  (calculate_session_key)
  - 0x54F98  (verifier / compare)
  - 0x3EBD4  (orphaned dispatcher candidate)
  - 0x4AA0C  (10-record orphaned table)

Also finds:
  - Every cmp/eq #0x27 in the binary
  - Every BSR/JSR/BRA to 0x529F8, 0x54F6A, 0x54F98, 0x3EBD4
  - Every 4-byte literal in literal pools that equals one of those addresses
  - 0x514AE region — traces the jsr @r5 and establishes what r5 holds
  - 0x4A864 (entry word for orphaned dispatcher) — finds all references
  - Session-state flag reads/writes that gate sub-func dispatch
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------

import struct
import sys
import os
from firmware_paths import OTHER_BINS

try:
    import capstone
    from capstone.sh import *
    HAVE_CAPSTONE = True
except ImportError:
    HAVE_CAPSTONE = False
    print("WARNING: capstone not available, falling back to byte-pattern only")

BIN_PATH = OTHER_BINS / '39990-TBA-A030 (stock).bin'
FLASH_BASE = 0x0  # file offset == flash address

# Key addresses to trace
SA_HANDLER       = 0x529F8
KEY_CALC         = 0x54F6A
VERIFIER         = 0x54F98
ORPHAN_DISP      = 0x3EBD4
ORPHAN_TABLE     = 0x4AA0C
ORPHAN_ENTRY_WD  = 0x4A864
JSR_AT_514AE     = 0x514AE  # jsr @r5 site

TARGET_ADDRS = {
    SA_HANDLER:      "SA_handler@0x529F8",
    KEY_CALC:        "calc_session_key@0x54F6A",
    VERIFIER:        "verifier@0x54F98",
    ORPHAN_DISP:     "orphan_dispatcher@0x3EBD4",
    ORPHAN_TABLE:    "orphan_table@0x4AA0C",
    ORPHAN_ENTRY_WD: "orphan_entry_word@0x4A864",
}

def load_bin(path):
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    print(f"Loaded {path}: {len(data):,} bytes")
    return data

def be16(data, off):
    return struct.unpack_from('>H', data, off)[0]

def be32(data, off):
    return struct.unpack_from('>I', data, off)[0]

def scan_literal_pools_for_addr(data, target_addr, context=8):
    """Find all 4-byte big-endian occurrences of target_addr in the binary."""
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

def scan_cmp_eq_imm(data, imm_byte):
    """
    SH-2A cmp/eq #imm,r0 = 0x88 imm  (16-bit big-endian instruction)
    Returns list of flash addresses.
    """
    pattern = bytes([0x88, imm_byte])
    hits = []
    off = 0
    while True:
        idx = data.find(pattern, off)
        if idx == -1:
            break
        # Must be instruction-aligned (even address)
        if idx % 2 == 0:
            hits.append(idx)
        off = idx + 1
    return hits

def scan_bsr_to(data, target_addr):
    """
    BSR label encodes as: 0xB??? where the 12-bit signed displacement d is:
    target = PC + 4 + d*2  =>  d = (target - PC - 4) / 2
    PC = address of BSR instruction.
    Opcode: 1011 dddd dddd dddd  (big-endian halfword)
    """
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw >> 12) == 0xB:  # BSR
            d = hw & 0xFFF
            if d & 0x800:
                d = d - 0x1000  # sign-extend 12-bit
            pc = off  # SH: PC = address of instruction
            dest = pc + 4 + d * 2
            if dest == target_addr:
                hits.append(off)
    return hits

def scan_bra_to(data, target_addr):
    """BRA label: 1010 dddd dddd dddd"""
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw >> 12) == 0xA:  # BRA
            d = hw & 0xFFF
            if d & 0x800:
                d = d - 0x1000
            pc = off
            dest = pc + 4 + d * 2
            if dest == target_addr:
                hits.append(off)
    return hits

def scan_bt_bf_to(data, target_addr):
    """
    BT/BF disp8: 1000 1001 dddd dddd (BT) / 1000 1011 dddd dddd (BF)
    dest = PC + 4 + d*2 (signed 8-bit d)
    """
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        opcode_hi = (hw >> 8) & 0xFF
        if opcode_hi in (0x89, 0x8B):  # BT or BF
            d = hw & 0xFF
            if d & 0x80:
                d = d - 0x100
            pc = off
            dest = pc + 4 + d * 2
            if dest == target_addr:
                hits.append((off, 'BT' if opcode_hi == 0x89 else 'BF'))
    return hits

def scan_jsr_r_indirect(data):
    """
    JSR @Rn: 0100 nnnn 0000 1011
    Returns (addr, reg_num) pairs.
    """
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw & 0xF00F) == 0x400B:
            rn = (hw >> 8) & 0xF
            hits.append((off, rn))
    return hits

def scan_jmp_r_indirect(data):
    """
    JMP @Rn: 0100 nnnn 0010 1011
    Returns (addr, reg_num) pairs.
    """
    hits = []
    for off in range(0, len(data) - 2, 2):
        hw = be16(data, off)
        if (hw & 0xF00F) == 0x402B:
            rn = (hw >> 8) & 0xF
            hits.append((off, rn))
    return hits

def disasm_range(data, start, length, label=""):
    """Disassemble a range using capstone if available, else hex dump."""
    if not HAVE_CAPSTONE:
        print(f"  [no capstone] raw bytes @{start:#x}:")
        for i in range(0, min(length, 64), 2):
            if start + i < len(data):
                print(f"    {start+i:#06x}: {data[start+i]:02x}{data[start+i+1]:02x}")
        return

    md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2A | capstone.CS_MODE_BIG_ENDIAN)
    md.detail = True
    chunk = bytes(data[start:start+length])
    for insn in md.disasm(chunk, start):
        print(f"    {insn.address:#06x}: {insn.mnemonic:<12} {insn.op_str}")

def read_context(data, addr, before=16, after=32, label=""):
    """Print disasm context around an address."""
    start = max(0, addr - before)
    length = before + after
    print(f"  --- context @{addr:#x} {label} ---")
    disasm_range(data, start, length)
    print()

def find_mov_l_loading_literal(data, literal_pool_addr, window=256):
    """
    Find MOV.L @(disp,PC),Rn that loads from literal_pool_addr.
    MOV.L: 1101 nnnn dddd dddd
    target = (PC + 2 + d*4) & ~3  (PC is addr of MOV.L instruction)
    So: (PC + 2 + d*4) & ~3 = literal_pool_addr
    Search in a window around literal_pool_addr.
    """
    hits = []
    start = max(0, literal_pool_addr - window)
    end = min(len(data), literal_pool_addr + 4)
    for off in range(start, end, 2):
        hw = be16(data, off)
        if (hw >> 12) == 0xD:  # MOV.L @(disp,PC),Rn
            rn = (hw >> 8) & 0xF
            d = hw & 0xFF
            # PC = off, aligned: target = (off + 2 + d*4) & ~3
            target = (off + 2 + d * 4) & ~3
            if target == literal_pool_addr:
                hits.append((off, rn, target))
    return hits

def analyze_region_514AE(data):
    """
    Analyze the jsr @r5 at 0x514AE and surrounding context.
    Trace what r5 holds at that point.
    """
    print("\n" + "="*70)
    print("ANALYSIS: jsr @r5 region at 0x514AE")
    print("="*70)
    # Disasm from 0x5140A to 0x514D0 — a reasonable function window
    print("\n  Disasm 0x51400-0x514D0 (200 bytes):")
    disasm_range(data, 0x51400, 0xD0)

def analyze_region_3EBD4(data):
    """
    Analyze 0x3EBD4 orphaned dispatcher and its entry-word at 0x4A864.
    """
    print("\n" + "="*70)
    print("ANALYSIS: orphaned dispatcher @0x3EBD4 and entry word @0x4A864")
    print("="*70)
    print("\n  Disasm 0x3EBD0-0x3EC20 (80 bytes):")
    disasm_range(data, 0x3EBD0, 0x50)

    print("\n  4 bytes @ entry word 0x4A864:")
    if 0x4A864 + 4 <= len(data):
        b = data[0x4A864:0x4A868]
        print(f"    {b.hex()} = {be32(data, 0x4A864):#010x}")

    print("\n  Disasm 0x4A860-0x4A890 (48 bytes):")
    disasm_range(data, 0x4A860, 0x30)

def analyze_orphan_table(data):
    """Inspect the 10-record orphaned table @0x4AA0C."""
    print("\n" + "="*70)
    print("ANALYSIS: orphaned 10-record table @0x4AA0C")
    print("="*70)
    print("\n  Bytes 0x4AA0C - 0x4AA5C (80 bytes = 10 records * ~8 bytes):")
    for off in range(0x4AA0C, min(0x4AA0C + 80, len(data)), 2):
        hw = be16(data, off)
        print(f"    {off:#06x}: {data[off]:02x} {data[off+1]:02x}  = {hw:#06x}")

    print("\n  Context before table 0x4AA00-0x4AA10:")
    for off in range(0x4AA00, min(0x4AA10, len(data)), 2):
        hw = be16(data, off)
        print(f"    {off:#06x}: {data[off]:02x} {data[off+1]:02x}")

def main():
    data = load_bin(BIN_PATH)
    size = len(data)

    print("\n" + "="*70)
    print("STEP 1: Find every cmp/eq #0x27 (SID 0x27 = SecurityAccess)")
    print("="*70)
    hits_27 = scan_cmp_eq_imm(data, 0x27)
    print(f"  cmp/eq #0x27 hits: {len(hits_27)}")
    for h in hits_27:
        print(f"    {h:#06x}: 88 27")
        read_context(data, h, before=8, after=20)

    print("\n" + "="*70)
    print("STEP 2: All BSR/BRA to SA_handler@0x529F8")
    print("="*70)
    bsr_hits = scan_bsr_to(data, SA_HANDLER)
    bra_hits = scan_bra_to(data, SA_HANDLER)
    print(f"  BSR to 0x529F8: {len(bsr_hits)} hits")
    for h in bsr_hits:
        print(f"    {h:#06x}: BSR 0x529F8")
        read_context(data, h, before=8, after=20)
    print(f"  BRA to 0x529F8: {len(bra_hits)} hits")
    for h in bra_hits:
        print(f"    {h:#06x}: BRA 0x529F8")
        read_context(data, h, before=8, after=20)

    print("\n" + "="*70)
    print("STEP 3: Literal pool references to SA_handler / key_calc / verifier / orphan_disp")
    print("="*70)
    for target_addr, label in TARGET_ADDRS.items():
        pool_hits = scan_literal_pools_for_addr(data, target_addr)
        print(f"\n  Literal pool hits for {label}: {len(pool_hits)}")
        for ph in pool_hits:
            print(f"    Literal @{ph:#06x}: {data[ph:ph+4].hex()} = {be32(data, ph):#010x}")
            # Find MOV.L instructions that load from this literal
            movl_hits = find_mov_l_loading_literal(data, ph, window=512)
            if movl_hits:
                print(f"      MOV.L loaders ({len(movl_hits)}):")
                for mh, rn, tgt in movl_hits:
                    print(f"        {mh:#06x}: mov.l @({ph-mh:#x},pc),r{rn}  -> loads {tgt:#010x}")
            else:
                print(f"      (no MOV.L loader found within 512 bytes)")

    print("\n" + "="*70)
    print("STEP 4: BSR/BRA to calc_session_key@0x54F6A")
    print("="*70)
    bsr_key = scan_bsr_to(data, KEY_CALC)
    bra_key = scan_bra_to(data, KEY_CALC)
    print(f"  BSR to 0x54F6A: {len(bsr_key)}")
    for h in bsr_key:
        print(f"    {h:#06x}")
        read_context(data, h, before=8, after=20)
    print(f"  BRA to 0x54F6A: {len(bra_key)}")
    for h in bra_key:
        print(f"    {h:#06x}")
        read_context(data, h, before=8, after=20)

    print("\n" + "="*70)
    print("STEP 5: BSR/BRA/BT/BF to verifier@0x54F98")
    print("="*70)
    bsr_ver = scan_bsr_to(data, VERIFIER)
    bra_ver = scan_bra_to(data, VERIFIER)
    bt_bf_ver = scan_bt_bf_to(data, VERIFIER)
    print(f"  BSR to 0x54F98: {len(bsr_ver)}")
    for h in bsr_ver:
        print(f"    {h:#06x}")
        read_context(data, h, before=8, after=24)
    print(f"  BRA to 0x54F98: {len(bra_ver)}")
    for h in bra_ver:
        print(f"    {h:#06x}")
        read_context(data, h, before=8, after=24)
    print(f"  BT/BF to 0x54F98: {len(bt_bf_ver)}")
    for h, kind in bt_bf_ver:
        print(f"    {h:#06x}: {kind}")

    print("\n" + "="*70)
    print("STEP 6: BSR/BRA to orphan_dispatcher@0x3EBD4")
    print("="*70)
    bsr_orph = scan_bsr_to(data, ORPHAN_DISP)
    bra_orph = scan_bra_to(data, ORPHAN_DISP)
    bt_bf_orph = scan_bt_bf_to(data, ORPHAN_DISP)
    print(f"  BSR to 0x3EBD4: {len(bsr_orph)}")
    for h in bsr_orph:
        print(f"    {h:#06x}")
        read_context(data, h, before=8, after=20)
    print(f"  BRA to 0x3EBD4: {len(bra_orph)}")
    for h in bra_orph:
        print(f"    {h:#06x}")
    print(f"  BT/BF to 0x3EBD4: {len(bt_bf_orph)}")
    for h, kind in bt_bf_orph:
        print(f"    {h:#06x}: {kind}")

    print("\n" + "="*70)
    print("STEP 7: All JSR @Rn in the binary — find indirect calls")
    print("="*70)
    jsr_indirect = scan_jsr_r_indirect(data)
    jmp_indirect = scan_jmp_r_indirect(data)
    print(f"  Total JSR @Rn in binary: {len(jsr_indirect)}")
    print(f"  Total JMP @Rn in binary: {len(jmp_indirect)}")
    # Focus on SA-adjacent region (0x5000-0x5600)
    print(f"\n  JSR @Rn in 0x5000-0x5600 (SA zone):")
    for addr, rn in jsr_indirect:
        if 0x5000 <= addr <= 0x5600:
            print(f"    {addr:#06x}: jsr @r{rn}")
            read_context(data, addr, before=24, after=16)

    print(f"\n  JMP @Rn in 0x5000-0x5600 (SA zone):")
    for addr, rn in jmp_indirect:
        if 0x5000 <= addr <= 0x5600:
            print(f"    {addr:#06x}: jmp @r{rn}")

    print("\n" + "="*70)
    print("STEP 8: JSR @Rn in 0x3E000-0x4000 (orphan dispatcher zone)")
    print("="*70)
    for addr, rn in jsr_indirect:
        if 0x3E000 <= addr <= 0x40000:
            print(f"    {addr:#06x}: jsr @r{rn}")
            read_context(data, addr, before=24, after=16)
    for addr, rn in jmp_indirect:
        if 0x3E000 <= addr <= 0x40000:
            print(f"    {addr:#06x}: jmp @r{rn}")

    # Detailed region analyses
    analyze_region_514AE(data)
    analyze_region_3EBD4(data)
    analyze_orphan_table(data)

    print("\n" + "="*70)
    print("STEP 9: Session-state flag — find all cmp/eq in SA handler 0x529F8-0x52D00")
    print("="*70)
    print("  All cmp/eq #imm,r0 (0x88xx) in 0x529F8-0x52D00:")
    for off in range(0x529F8, min(0x52D00, len(data)-1), 2):
        if data[off] == 0x88:
            imm = data[off+1]
            print(f"    {off:#06x}: cmp/eq #{imm:#04x},r0  (0x88{imm:02x})")

    print("\n  All cmp/eq #imm,r0 (0x88xx) in 0x51400-0x51600 (jsr @r5 zone):")
    for off in range(0x51400, min(0x51600, len(data)-1), 2):
        if data[off] == 0x88:
            imm = data[off+1]
            print(f"    {off:#06x}: cmp/eq #{imm:#04x},r0  (0x88{imm:02x})")

    print("\n" + "="*70)
    print("STEP 10: Extended cmp/eq #0x27 scan — check ALL addresses including non-SA zones")
    print("="*70)
    # Also look for tst/and patterns: tst #0x27,r0 = 0xC8 0x27
    tst_hits = []
    for off in range(0, len(data)-1, 2):
        if data[off] == 0xC8 and data[off+1] == 0x27:
            tst_hits.append(off)
    print(f"  tst #0x27,r0 hits: {len(tst_hits)}")
    for h in tst_hits:
        print(f"    {h:#06x}: C8 27")

    # Look for mov.b loads of a literal containing 0x27 followed by cmp/eq
    print("\n  All cmp/eq #0x01 in 0x529F8-0x52D00 (to find ALL sub-func checks):")
    for off in range(0x529F8, min(0x52D00, len(data)-1), 2):
        if data[off] == 0x88 and data[off+1] == 0x01:
            print(f"    {off:#06x}: cmp/eq #1,r0")

    print("\n  All cmp/eq #0x07 in entire binary:")
    hits_07 = scan_cmp_eq_imm(data, 0x07)
    print(f"  Count: {len(hits_07)}")
    for h in hits_07:
        print(f"    {h:#06x}: 88 07")

    print("\n  All cmp/eq #0x08 in entire binary:")
    hits_08 = scan_cmp_eq_imm(data, 0x08)
    print(f"  Count: {len(hits_08)}")
    for h in hits_08:
        print(f"    {h:#06x}: 88 08")

    print("\n" + "="*70)
    print("STEP 11: Scan for session-state byte writes (what enables different SA levels?)")
    print("         Look for the 'extend session' handler — SID 0x10 (DiagnosticSessionControl)")
    print("="*70)
    hits_10 = scan_cmp_eq_imm(data, 0x10)
    print(f"  cmp/eq #0x10 hits: {len(hits_10)}")
    for h in hits_10:
        print(f"    {h:#06x}: 88 10")

    # Also scan for cmp/eq #0x03 (programming session) and #0x02 (extended session)
    hits_03 = scan_cmp_eq_imm(data, 0x03)
    hits_02 = scan_cmp_eq_imm(data, 0x02)
    print(f"\n  cmp/eq #0x03 (programming session) hits: {len(hits_03)}")
    for h in hits_03:
        print(f"    {h:#06x}: 88 03")
    print(f"\n  cmp/eq #0x02 (extended session) hits: {len(hits_02)}")
    # Only show ones in router zone
    for h in hits_02:
        if 0x52000 <= h <= 0x56000:
            print(f"    {h:#06x}: 88 02 [SA zone]")

    print("\n" + "="*70)
    print("STEP 12: Check if 0x3EBD4 region contains a sub-func dispatch table")
    print("         Look for embedded address table that points into SA/key code")
    print("="*70)
    # Scan 0x3EC00 - 0x3EE00 for 4-byte words that look like code addresses
    print("  Scanning 0x3E800-0x3F200 for 4-byte code pointers (0x00050000-0x00056000 range):")
    for off in range(0x3E800, min(0x3F200, len(data)-3), 4):
        val = be32(data, off)
        if 0x00050000 <= val <= 0x00060000:
            print(f"    {off:#06x}: {val:#010x} (code ptr candidate)")
        if 0x00040000 <= val <= 0x00056000:
            if (val & 0xFFFF0000) not in (0x00000000,):
                print(f"    {off:#06x}: {val:#010x} (code ptr candidate wide)")

    print("\n  Scanning 0x4A800-0x4AE00 (orphan table zone) for sub-func values 0x01/0x02/0x07/0x08/0x41/0x61/0x7B/0x7C:")
    for off in range(0x4A800, min(0x4AE00, len(data)-1), 1):
        b = data[off]
        if b in (0x01, 0x02, 0x07, 0x08, 0x41, 0x42, 0x61, 0x62, 0x7B, 0x7C):
            print(f"    {off:#06x}: {b:#04x}")

    print("\nDONE.")

if __name__ == '__main__':
    main()
