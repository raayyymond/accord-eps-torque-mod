#!/usr/bin/env python3
"""
Part 4: Decode the outer SID table at 0x4A840-0x4A930 and find its caller.
Also: find all references to this table in code.
The outer table has 24-byte records with:
  [0..3] = some ID/session field (BE u32: first byte is SID candidate)
  [8..11] = SID (BE u32: 0x27000000 etc.)
  [12..15] = handler function pointer
  [16..19] = second handler pointer

Let's parse it properly and find who loads the outer table base.
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

    print("\n"+"="*70)
    print("1. Parse the outer SID dispatch table at 0x4A840")
    print("   Record size: 24 bytes. Field layout from prior scan:")
    print("   [0] = SID byte (BE, rest zero-padded)")
    print("   [8] = session/type flags?")
    print("   [12] = handler fn ptr A (requestSeed type)")
    print("   [16] = handler fn ptr B (sendKey type)")
    print("="*70)
    # From prior output:
    # @0x4a858: 0004a608 | 06000000 | 27000000 | 0003ebd4 | 0004a620 | 20000000
    # So stride=24, and: val0=ptr, val1=flags, val2=SID<<24, val3=handlerA, val4=handlerB, val5=more_flags
    # Let's re-parse: each 24-byte record starting from 0x4A840
    # At 0x4A840: 21 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 22 00 00 00 00 03 ea 58
    #   SID@[0]=0x21, handler@[20]=0x3EA58
    # At 0x4A858: 00 04 A6 08 06 00 00 00 27 00 00 00 00 03 EB D4 00 04 A6 20 20 00 00 00
    #   ptr_a@[0]=0x4A608, flags@[4]=0x06, SID@[8]=0x27, handlerA@[12]=0x3EBD4, handlerB@[16]=0x4A620, flags2@[20]=0x20
    # At 0x4A870: 28 00 00 00 00 03 ED 30 00 04 A6 A0 14 00 00 00 2E 00 00 00 00 03 EE AE
    #   SID@[0]=0x28, handlerA@[4]=0x3ED30, handlerB@[8]=0x4A6A0, flags@[12]=0x14, SID2@[16]=0x2E, handler2A@[20]=0x3EEAE
    # Hmm, the stride and offsets are a bit irregular. Let me try 8-byte stride.

    # Actually let's try: the table at 0x4A840 uses 8-byte records:
    # 0x4A840: 21 00 00 00 00 00 00 00  -> SID=0x21, ptr=0
    # 0x4A848: 00 00 00 00 00 00 00 00
    # 0x4A850: 22 00 00 00 00 03 EA 58  -> SID=0x22, handler=0x3EA58
    # 0x4A858: 00 04 A6 08 06 00 00 00  -> ptr=0x4A608, flags=0x06
    # 0x4A860: 27 00 00 00 00 03 EB D4  -> SID=0x27, handler=0x3EBD4 !!!
    # 0x4A868: 00 04 A6 20 20 00 00 00  -> ptr=0x4A620, flags=0x20
    # 0x4A870: 28 00 00 00 00 03 ED 30  -> SID=0x28, handler=0x3ED30
    # 0x4A878: 00 04 A6 A0 14 00 00 00
    # 0x4A880: 2E 00 00 00 00 03 EE AE  -> SID=0x2E, handler=0x3EEAE
    # 0x4A888: 00 04 A6 F0 0C 00 00 00
    # 0x4A890: 30 00 00 00 00 00 00 00  -> SID=0x30
    # 0x4A898: 00 00 00 00 00 00 00 00
    # 0x4A8A0: 31 00 00 00 00 03 EF A6  -> SID=0x31, handler=0x3EFA6
    # 0x4A8A8: 00 04 A7 20 1C 00 00 00
    # 0x4A8B0: 34 00 00 00 00 00 00 00  -> SID=0x34 (upload/download)
    # ....

    print("  8-byte record parse of 0x4A840-0x4A960:")
    for off in range(0x4A840, min(0x4A960, len(data)), 8):
        b = data[off:off+8]
        b0 = b[0]
        val = struct.unpack_from('>I', b, 4)[0]  # last 4 bytes as addr
        val2 = struct.unpack_from('>I', b, 0)[0]
        marker = ""
        # Is first byte a UDS SID?
        if b[1]==0 and b[2]==0 and b[3]==0:
            if 0x10<=b0<=0x7F:
                marker = f" <-- SID={b0:#04x}"
                if 0x3E000<=val<=0x60000:
                    marker += f", handler={val:#06x}"
        elif 0x3E000<=val2<=0x60000:
            marker = f" <-- handler={val2:#06x}"
        elif 0x3E000<=val<=0x60000:
            marker = f" <-- ptr={val:#06x}"
        print(f"    {off:#06x}: {b.hex()}{marker}")

    print("\n"+"="*70)
    print("2. Find all code that loads from the outer table base addresses")
    print("   Looking for literals: 0x4A840, 0x4A860, 0x4A858, 0x4A848")
    print("="*70)
    for tbl_base in [0x4A840, 0x4A848, 0x4A858, 0x4A860, 0x4A868,
                     0x4A870, 0x4A880, 0x4A850]:
        target_bytes = struct.pack('>I', tbl_base)
        off = 0
        hits = []
        while True:
            idx = data.find(target_bytes, off)
            if idx == -1: break
            hits.append(idx)
            off = idx + 1
        if hits:
            print(f"  Literal {tbl_base:#010x}: found at {[f'{h:#06x}' for h in hits]}")
            for h in hits:
                # Find MOV.L loaders
                for load_off in range(max(0,h-512), h, 2):
                    hw = be16(data, load_off)
                    if (hw>>12)==0xD:
                        rn=(hw>>8)&0xF
                        d=hw&0xFF
                        target=(load_off+2+d*4)&~3
                        if target==h:
                            print(f"    MOV.L loader @{load_off:#06x}: mov.l @(disp,pc),r{rn} -> {h:#06x}")

    print("\n"+"="*70)
    print("3. Find who calls 0x3EC1C (loop head in orphan dispatcher)")
    print("   The dispatcher at 0x3EBD4 calls 0x3EC1E via its loop.")
    print("   Who calls the OUTER dispatch framework (i.e., 0x3EBD4 etc.)?")
    print("   Search for JSR @Rn where Rn was loaded from 0x4A860 region")
    print("="*70)
    # The outer table entry for SID 0x27 is at 0x4A860:
    # 0x4A860: 27 00 00 00 00 03 EB D4
    # So the handler address 0x3EBD4 is at offset 0x4A864 (bytes 4-7).
    # To call it, code would:
    # 1. Load base of outer table -> some reg
    # 2. Compute offset for 0x27 entry -> add to base
    # 3. Load @(4, base+offset) -> call register
    # Or: load the table entry base, read at offset 4 = handler addr
    # Let's search for the outer framework caller.
    # The Clarity (TRW-A020) has it at 0x3F990 — for A030 it would be somewhere similar.

    # Let's look for what loads 0x4A96C (from earlier scan: 0x3E870 -> 0x4A96C)
    # 0x3E870 literal = 0x0004A96C -> MOV.L loader context
    target_bytes = struct.pack('>I', 0x4A96C)
    off=0; hits=[]
    while True:
        idx=data.find(target_bytes,off)
        if idx==-1: break
        hits.append(idx)
        off=idx+1
    print(f"  Literal 0x4A96C (outer table candidate): {[f'{h:#06x}' for h in hits]}")
    for h in hits:
        for load_off in range(max(0,h-512),h,2):
            hw=be16(data,load_off)
            if (hw>>12)==0xD:
                rn=(hw>>8)&0xF; d=hw&0xFF
                target=(load_off+2+d*4)&~3
                if target==h:
                    print(f"    MOV.L loader @{load_off:#06x}: mov.l @(disp,pc),r{rn}")
                    disasm_range(data,load_off-32,80)

    print("\n"+"="*70)
    print("4. Find who loads 0x4A9BC (second outer table candidate from 0x3E888)")
    print("="*70)
    for tbl_cand in [0x4A9BC, 0x4A9D0, 0x4A9BC, 0x4A608]:
        target_bytes = struct.pack('>I', tbl_cand)
        off=0; hits=[]
        while True:
            idx=data.find(target_bytes,off)
            if idx==-1: break
            hits.append(idx); off=idx+1
        if hits:
            print(f"  Literal {tbl_cand:#010x}: {[f'{h:#06x}' for h in hits]}")
            for h in hits:
                for load_off in range(max(0,h-512),h,2):
                    hw=be16(data,load_off)
                    if (hw>>12)==0xD:
                        rn=(hw>>8)&0xF; d=hw&0xFF
                        target=(load_off+2+d*4)&~3
                        if target==h:
                            print(f"    MOV.L @{load_off:#06x}: r{rn}")
                            disasm_range(data,load_off-16,48)

    print("\n"+"="*70)
    print("5. Disasm the function at 0x3F5D0 (contains BSRF r0 @0x3F5D6)")
    print("   BSRF is a computed branch — could jump to 0x3EBD4 based on r0 value")
    print("="*70)
    disasm_range(data, 0x3F590, 0x80)

    print("\n"+"="*70)
    print("6. Disasm 0x3F6C0-0x3F700 (contains BSRF r0 @0x3F6CE)")
    print("="*70)
    disasm_range(data, 0x3F6C0, 0x60)

    print("\n"+"="*70)
    print("7. What function at 0x3F5D6 or 0x3F6CE — does r0 hold a dispatch offset?")
    print("   Scan for any code that computes offset into the outer table")
    print("   Look for: shll2 + add + mov.l @(r0,rx) pattern near the BSRF sites")
    print("="*70)
    # Context around 0x3F5D6
    print("  Context 0x3F580-0x3F620:")
    disasm_range(data, 0x3F580, 0xA0)

    print("\n"+"="*70)
    print("8. Is there a SID dispatch function at 0x3F990 (as in Clarity)?")
    print("   Check 0x3F980-0x3FA20")
    print("="*70)
    disasm_range(data, 0x3F980, 0xA0)

    print("\n"+"="*70)
    print("9. Find all BSR to the orphan region function cluster (0x3EBD4-0x3F400)")
    print("   These would be direct callers of the SA sub-handlers")
    print("="*70)
    caller_map = {}
    for off in range(0,len(data)-2,2):
        hw=be16(data,off)
        if (hw>>12)==0xB:
            d=hw&0xFFF
            if d&0x800: d=d-0x1000
            dest=off+4+d*2
            if 0x3EA00<=dest<=0x3FF00:
                caller_map.setdefault(dest,[]).append(off)
    print(f"  Functions called via BSR in 0x3EA00-0x3FF00:")
    for dest in sorted(caller_map.keys()):
        callers=caller_map[dest]
        print(f"    BSR to {dest:#06x}: {len(callers)} callers — from: {[f'{c:#06x}' for c in callers[:4]]}")

    print("\n"+"="*70)
    print("10. Disasm 0x3F400-0x3F600 (function cluster — framework dispatcher?)")
    print("="*70)
    disasm_range(data, 0x3F400, 0x100)

    print("\nDONE.")

if __name__=='__main__':
    main()
