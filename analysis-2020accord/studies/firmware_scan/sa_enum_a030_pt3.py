#!/usr/bin/env python3
"""
Part 3: Final confirmation — who invokes 0x3EBD4 dispatcher?
Scan for ALL indirect JSR where the loaded register is 0x3EBD4,
and find the function that contains the literal @0x4A864 = 0x0003EBD4.
Also scan for BSRF (register-relative BSR) targeting 0x3EBD4.
Also: map the record structure at 0x4A96C (the table loaded by 0x3EC1E).
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
from pathlib import Path
ANALYSIS_DIR = Path(__file__).resolve().parents[2]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import OTHER_BINS
BIN_PATH = OTHER_BINS / '39990-TBA-A030 (stock).bin'

try:
    import capstone
    HAVE_CAPSTONE = True
except ImportError:
    HAVE_CAPSTONE = False

def load_bin(path):
    with open(path,'rb') as f: data=bytearray(f.read())
    print(f"Loaded: {len(data):,} bytes")
    return data

def be16(data,off): return struct.unpack_from('>H',data,off)[0]
def be32(data,off): return struct.unpack_from('>I',data,off)[0]

def disasm_range(data,start,length,indent="    "):
    if not HAVE_CAPSTONE:
        for i in range(0,min(length,128),2):
            if start+i+1<len(data): print(f"{indent}{start+i:#06x}: {data[start+i]:02x}{data[start+i+1]:02x}")
        return
    md=capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2A|capstone.CS_MODE_BIG_ENDIAN)
    md.detail=True
    chunk=bytes(data[start:start+length])
    for insn in md.disasm(chunk,start):
        print(f"{indent}{insn.address:#06x}: {insn.mnemonic:<14} {insn.op_str}")

def main():
    data=load_bin(BIN_PATH)

    TARGET=0x3EBD4

    print("\n"+"="*70)
    print("1. Who loads 0x0003EBD4 from literal pool 0x4A864?")
    print("   Wide scan: all MOV.L @(disp,PC),Rn with target==0x4A864")
    print("="*70)
    # Scan entire file
    found=[]
    for off in range(0, len(data)-2, 2):
        hw=be16(data,off)
        if (hw>>12)==0xD:
            rn=(hw>>8)&0xF
            d=hw&0xFF
            target=(off+2+d*4)&~3
            if target==0x4A864:
                found.append((off,rn))
    print(f"  MOV.L loaders (whole binary): {len(found)}")
    for addr,rn in found:
        print(f"    {addr:#06x}: mov.l @(disp,pc),r{rn}  target={0x4A864:#06x}")
        disasm_range(data,addr-32,80)

    print("\n"+"="*70)
    print("2. Scan for BSRF Rn (0100 nnnn 0000 0011) that could reach 0x3EBD4")
    print("   bsrf Rn: PC+4+Rn => target, so Rn = target - PC - 4")
    print("   (Can't statically resolve register value, so just list all BSRF sites)")
    print("="*70)
    bsrf_hits=[]
    for off in range(0,len(data)-2,2):
        hw=be16(data,off)
        if (hw&0xF0FF)==0x4003:
            rn=(hw>>8)&0xF
            bsrf_hits.append((off,rn))
    print(f"  Total BSRF Rn in binary: {len(bsrf_hits)}")
    # Show ones near the orphan region
    for addr,rn in bsrf_hits:
        if 0x3E000<=addr<=0x50000:
            print(f"    {addr:#06x}: bsrf r{rn}")

    print("\n"+"="*70)
    print("3. Look for the FUNCTION that USES 0x4A864 as a base for table lookup")
    print("   The literal @0x3EDA0 = 0x0004AA0C (table base) is loaded at 0x3EC1E and 0x3EC3C")
    print("   The literal @0x4A864 = 0x0003EBD4 is used AS DATA in a larger table")
    print("   Let's find what code block READS @0x4A864 as a function pointer")
    print("="*70)
    # The orphan dispatcher at 0x3EBD4 is stored at flash offset 0x4A864.
    # The function at 0x3EBD4 is itself a sub-handler.
    # Who loads its address? Search for MOV.L at 0x4A864 loader in larger window.
    # Also check if there's an indirect table read: e.g. base addr in a register + offset
    # pointing to 0x4A864.
    # Let's see what's in the table around 0x4A850-0x4A870 in structured form
    print("  Table at 0x4A840-0x4A930 (24-byte record check):")
    for off in range(0x4A840, 0x4A930, 24):
        if off+24>len(data): break
        chunk=data[off:off+24]
        vals=[be32(data,off+i*4) for i in range(6)]
        print(f"    @{off:#06x}: {chunk[:8].hex()} | {chunk[8:16].hex()} | {chunk[16:24].hex()}")
        print(f"             vals: {[f'{v:#010x}' for v in vals]}")

    print("\n"+"="*70)
    print("4. What is at code-address 0x3EB20 (seen in table entries @0x4AA20,0x4AA38,etc.)?")
    print("   This address appears in the sub-func table for 0x07/0x41/0x7B/0x61")
    print("="*70)
    disasm_range(data, 0x3EB20, 0x60)

    print("\n"+"="*70)
    print("5. What is at code-address 0x3EB64 (seen in table entries for 0x08/0x42/0x7C/0x62)?")
    print("="*70)
    disasm_range(data, 0x3EB64, 0x60)

    print("\n"+"="*70)
    print("6. Full table at 0x4A96C — stride=24 bytes, first field = sub-func ID")
    print("   This is the table loaded by 0x3EC1E (literal @0x3EDA0=0x0004AA0C)")
    print("   Wait — 0x3EDA0 literal = 0x4AA0C. So the TABLE starts at 0x4AA0C.")
    print("   Records: stride appears to be 24 bytes based on prior scan.")
    print("   Let's decode: byte[0]=subFunc, byte[4..7]=handler_addr?, byte[20..23]=?")
    print("="*70)
    TABLE_BASE=0x4AA0C
    RECORD_SIZE=24
    NUM_RECORDS=10
    print(f"  Table @{TABLE_BASE:#06x}, {RECORD_SIZE}-byte records, {NUM_RECORDS} records:")
    for i in range(NUM_RECORDS):
        off=TABLE_BASE+i*RECORD_SIZE
        if off+RECORD_SIZE>len(data): break
        b=data[off:off+RECORD_SIZE]
        subfunc=b[0]
        # Check field offsets
        f4=be32(data,off+4) if off+8<=len(data) else 0
        f8=be32(data,off+8) if off+12<=len(data) else 0
        f12=be32(data,off+12) if off+16<=len(data) else 0
        f16=be32(data,off+16) if off+20<=len(data) else 0
        f20=be32(data,off+20) if off+24<=len(data) else 0
        print(f"  Record {i}: @{off:#06x}")
        print(f"    [0]={subfunc:#04x}  [4]={f4:#010x}  [8]={f8:#010x}")
        print(f"    [12]={f12:#010x}  [16]={f16:#010x}  [20]={f20:#010x}")
        print(f"    raw: {b.hex()}")
        if 0x3E000<=f20<=0x60000:
            print(f"    *** [20] looks like handler addr: {f20:#06x}")
        if 0x3E000<=f4<=0x60000:
            print(f"    *** [4] looks like handler addr: {f4:#06x}")

    print("\n"+"="*70)
    print("7. BSRF context at 0x3ED50 (seen in dispatcher disasm)")
    print("="*70)
    disasm_range(data, 0x3ED48, 0x20)

    print("\n"+"="*70)
    print("8. Who calls (BSR to) 0x3EBD4, 0x3ED30, 0x3EEAE, 0x3EFA6, 0x3F17E, 0x3F240?")
    print("   These are the function ptrs in the outer table at 0x4A864,0x4A874,etc.")
    print("="*70)
    targets_to_check=[0x3EBD4, 0x3ED30, 0x3EEAE, 0x3EFA6, 0x3F17E, 0x3F240]
    for target in targets_to_check:
        hits=[]
        for off in range(0,len(data)-2,2):
            hw=be16(data,off)
            if (hw>>12)==0xB:  # BSR
                d=hw&0xFFF
                if d&0x800: d=d-0x1000
                dest=off+4+d*2
                if dest==target: hits.append(off)
        print(f"  BSR to {target:#06x}: {len(hits)} direct callers")
        for h in hits[:3]: print(f"    from {h:#06x}")
        # Also check BRA
        bra_hits=[]
        for off in range(0,len(data)-2,2):
            hw=be16(data,off)
            if (hw>>12)==0xA:  # BRA
                d=hw&0xFFF
                if d&0x800: d=d-0x1000
                dest=off+4+d*2
                if dest==target: bra_hits.append(off)
        if bra_hits: print(f"  BRA to {target:#06x}: {bra_hits}")

    print("\n"+"="*70)
    print("9. Check what loads the OUTER table at 0x4A864 region (0x4A860 = outer table?)")
    print("   Scan for literal pools containing 0x4A860, 0x4A868, 0x4A870...")
    print("="*70)
    for outer_base in [0x4A860, 0x4A86C, 0x4A864, 0x4A878, 0x4A858]:
        target_bytes=struct.pack('>I', outer_base)
        off=0
        found_lits=[]
        while True:
            idx=data.find(target_bytes,off)
            if idx==-1: break
            found_lits.append(idx)
            off=idx+1
        if found_lits:
            print(f"  Literal containing {outer_base:#010x}: {[f'{x:#06x}' for x in found_lits]}")

    print("\n"+"="*70)
    print("10. SA handler at 0x529F8 — what session state does it check?")
    print("    Disasm 0x529F8-0x52A20 (entry point and checks)")
    print("="*70)
    disasm_range(data, 0x529F8, 0x30)

    print("\n"+"="*70)
    print("11. The 0x52782 function (DiagSession-gated SA helper?) — full disasm")
    print("="*70)
    disasm_range(data, 0x52782, 0xC0)

    print("\nDONE.")

if __name__=='__main__':
    main()
