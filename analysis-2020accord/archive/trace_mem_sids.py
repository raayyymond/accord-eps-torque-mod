"""Trace memory/transfer SID handlers in A030 full binary."""
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
import struct, sys
from firmware_paths import OTHER_BINS

FNAME = OTHER_BINS / "39990-TBA-A030 (stock).bin"
with open(FNAME, 'rb') as f:
    data = f.read()

def r16(a): return struct.unpack_from('>H', data, a)[0]
def r32(a): return struct.unpack_from('>I', data, a)[0]

def disasm(start_addr, n=80, label=""):
    if label:
        print(f"\n=== {label} @ {start_addr:#07x} ===")
    for i in range(n):
        a = start_addr + i*2
        if a + 2 > len(data): break
        w = r16(a)
        hi = w >> 8; lo = w & 0xFF
        opc = w >> 12

        # BSR
        if opc == 0xB:
            d = w & 0xFFF
            if d & 0x800: d -= 0x1000
            t = a + 4 + d*2
            print(f"  {a:#07x}: {w:04X}  bsr {t:#07x}")
            continue
        # BRA
        if opc == 0xA:
            d = w & 0xFFF
            if d & 0x800: d -= 0x1000
            t = a + 4 + d*2
            print(f"  {a:#07x}: {w:04X}  bra {t:#07x}")
            continue
        # BT
        if hi == 0x89:
            d = lo if lo < 0x80 else lo - 0x100
            t = a + 4 + d*2
            print(f"  {a:#07x}: {w:04X}  bt {t:#07x}")
            continue
        # BT/S
        if hi == 0x8D:
            d = lo if lo < 0x80 else lo - 0x100
            t = a + 4 + d*2
            print(f"  {a:#07x}: {w:04X}  bt/s {t:#07x}")
            continue
        # BF
        if hi == 0x8B:
            d = lo if lo < 0x80 else lo - 0x100
            t = a + 4 + d*2
            print(f"  {a:#07x}: {w:04X}  bf {t:#07x}")
            continue
        # BF/S
        if hi == 0x8F:
            d = lo if lo < 0x80 else lo - 0x100
            t = a + 4 + d*2
            print(f"  {a:#07x}: {w:04X}  bf/s {t:#07x}")
            continue
        # CMP/EQ imm,R0
        if hi == 0x88:
            print(f"  {a:#07x}: {w:04X}  cmp/eq #{lo:#04x},r0")
            continue
        # CMP/EQ Rm,Rn
        if opc == 0x3 and (w & 0xF) == 0x0:
            print(f"  {a:#07x}: {w:04X}  cmp/eq r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # CMP/GE
        if opc == 0x3 and (w & 0xF) == 0x3:
            print(f"  {a:#07x}: {w:04X}  cmp/ge r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # CMP/GT
        if opc == 0x3 and (w & 0xF) == 0x7:
            print(f"  {a:#07x}: {w:04X}  cmp/gt r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # CMP/HI
        if opc == 0x3 and (w & 0xF) == 0x6:
            print(f"  {a:#07x}: {w:04X}  cmp/hi r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # CMP/HS
        if opc == 0x3 and (w & 0xF) == 0x2:
            print(f"  {a:#07x}: {w:04X}  cmp/hs r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MOV.L @(disp,PC),Rn
        if opc == 0xD:
            rn = (w >> 8) & 0xF
            d = w & 0xFF
            pa = (a & ~3) + 4 + d*4
            v = r32(pa) if pa + 4 <= len(data) else 0xDEAD
            print(f"  {a:#07x}: {w:04X}  mov.l [pool{pa:#07x}={v:#010x}],r{rn}")
            continue
        # MOV.W @(disp,PC),Rn
        if opc == 0x9:
            rn = (w >> 8) & 0xF
            d = w & 0xFF
            pa = (a & ~1) + 4 + d*2
            v = struct.unpack_from('>H', data, pa)[0] if pa + 2 <= len(data) else 0xDEAD
            print(f"  {a:#07x}: {w:04X}  mov.w [pool{pa:#07x}={v:#06x}],r{rn}")
            continue
        # MOV #imm,Rn
        if opc == 0xE:
            rn = (w >> 8) & 0xF
            imm = lo if lo < 0x80 else lo - 0x100
            print(f"  {a:#07x}: {w:04X}  mov #{imm},r{rn}")
            continue
        # ADD #imm,Rn
        if opc == 0x7:
            rn = (w >> 8) & 0xF
            imm = lo if lo < 0x80 else lo - 0x100
            print(f"  {a:#07x}: {w:04X}  add #{imm},r{rn}")
            continue
        # MOV.L @Rn,Rm
        if opc == 0x6 and (w & 0xF) == 2:
            print(f"  {a:#07x}: {w:04X}  mov.l @r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MOV.W @Rn,Rm
        if opc == 0x6 and (w & 0xF) == 1:
            print(f"  {a:#07x}: {w:04X}  mov.w @r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MOV.B @Rn,Rm
        if opc == 0x6 and (w & 0xF) == 0:
            print(f"  {a:#07x}: {w:04X}  mov.b @r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MOV Rm,Rn
        if opc == 0x6 and (w & 0xF) == 3:
            print(f"  {a:#07x}: {w:04X}  mov r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MOV.L @Rm+,Rn
        if opc == 0x6 and (w & 0xF) == 6:
            print(f"  {a:#07x}: {w:04X}  mov.l @r{(w>>4)&0xF}+,r{(w>>8)&0xF}")
            continue
        # MOV.L Rm,@Rn
        if opc == 0x2 and (w & 0xF) == 2:
            print(f"  {a:#07x}: {w:04X}  mov.l r{(w>>4)&0xF},@r{(w>>8)&0xF}")
            continue
        # MOV.W Rm,@Rn
        if opc == 0x2 and (w & 0xF) == 1:
            print(f"  {a:#07x}: {w:04X}  mov.w r{(w>>4)&0xF},@r{(w>>8)&0xF}")
            continue
        # MOV.B Rm,@Rn
        if opc == 0x2 and (w & 0xF) == 0:
            print(f"  {a:#07x}: {w:04X}  mov.b r{(w>>4)&0xF},@r{(w>>8)&0xF}")
            continue
        # MOV.L Rm,@-Rn
        if opc == 0x2 and (w & 0xF) == 6:
            print(f"  {a:#07x}: {w:04X}  mov.l r{(w>>4)&0xF},@-r{(w>>8)&0xF}")
            continue
        # MOV.L @(disp,Rn)
        if opc == 0x5:
            rn = (w >> 4) & 0xF; rm = (w >> 8) & 0xF; d = (w & 0xF)*4
            print(f"  {a:#07x}: {w:04X}  mov.l @({d},r{rn}),r{rm}")
            continue
        # MOV.W @(disp,Rn)
        if opc == 0x8 and hi == 0x85:
            # 0x85xd
            rn = (w >> 4) & 0xF; d = (w & 0xF)*2
            print(f"  {a:#07x}: {w:04X}  mov.w @({d},r{rn}),r0")
            continue
        # MOV.L Rm,@(disp,Rn)
        if opc == 0x1:
            rn = (w >> 8) & 0xF; rm = (w >> 4) & 0xF; d = (w & 0xF)*4
            print(f"  {a:#07x}: {w:04X}  mov.l r{rm},@({d},r{rn})")
            continue
        # JSR @Rn
        if (w & 0xF00F) == 0x400B:
            print(f"  {a:#07x}: {w:04X}  jsr @r{(w>>8)&0xF}")
            continue
        # JMP @Rn
        if (w & 0xF0FF) == 0x402B:
            print(f"  {a:#07x}: {w:04X}  jmp @r{(w>>8)&0xF}")
            continue
        # RTS
        if w == 0x000B:
            print(f"  {a:#07x}: {w:04X}  rts"); break
        # NOP
        if w == 0x0009:
            print(f"  {a:#07x}: {w:04X}  nop")
            continue
        # TST Rm,Rn
        if opc == 0x2 and (w & 0xF) == 8:
            print(f"  {a:#07x}: {w:04X}  tst r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # AND Rm,Rn
        if opc == 0x2 and (w & 0xF) == 9:
            print(f"  {a:#07x}: {w:04X}  and r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # XOR Rm,Rn
        if opc == 0x2 and (w & 0xF) == 0xA:
            print(f"  {a:#07x}: {w:04X}  xor r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # OR Rm,Rn
        if opc == 0x2 and (w & 0xF) == 0xB:
            print(f"  {a:#07x}: {w:04X}  or r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # NOT Rm,Rn
        if opc == 0x6 and (w & 0xF) == 7:
            print(f"  {a:#07x}: {w:04X}  not r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # STS.L PR,@-Rn
        if (w & 0xF0FF) == 0x4022:
            print(f"  {a:#07x}: {w:04X}  sts.l pr,@-r{(w>>8)&0xF}")
            continue
        # LDS.L @Rn+,PR
        if (w & 0xF0FF) == 0x4026:
            print(f"  {a:#07x}: {w:04X}  lds.l @r{(w>>8)&0xF}+,pr")
            continue
        # ADD Rm,Rn
        if opc == 0x3 and (w & 0xF) == 0xC:
            print(f"  {a:#07x}: {w:04X}  add r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # SUB Rm,Rn
        if opc == 0x3 and (w & 0xF) == 8:
            print(f"  {a:#07x}: {w:04X}  sub r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MUL
        if opc == 0x0 and (w & 0xF) == 7:
            print(f"  {a:#07x}: {w:04X}  mul.l r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MULS.W
        if opc == 0x2 and (w & 0xF) == 0xF:
            print(f"  {a:#07x}: {w:04X}  muls.w r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # MULU.W
        if opc == 0x2 and (w & 0xF) == 0xE:
            print(f"  {a:#07x}: {w:04X}  mulu.w r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # SHLL/SHAL
        if opc == 0x4 and (w & 0xFF) == 0x00:
            print(f"  {a:#07x}: {w:04X}  shll r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x20:
            print(f"  {a:#07x}: {w:04X}  shal r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x08:
            print(f"  {a:#07x}: {w:04X}  shll2 r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x18:
            print(f"  {a:#07x}: {w:04X}  shll8 r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x28:
            print(f"  {a:#07x}: {w:04X}  shll16 r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x09:
            print(f"  {a:#07x}: {w:04X}  shlr2 r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x19:
            print(f"  {a:#07x}: {w:04X}  shlr8 r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x29:
            print(f"  {a:#07x}: {w:04X}  shlr16 r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x01:
            print(f"  {a:#07x}: {w:04X}  shlr r{(w>>8)&0xF}")
            continue
        if opc == 0x4 and (w & 0xFF) == 0x21:
            print(f"  {a:#07x}: {w:04X}  shar r{(w>>8)&0xF}")
            continue
        # NEG
        if opc == 0x6 and (w & 0xF) == 0xB:
            print(f"  {a:#07x}: {w:04X}  neg r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # NEGC
        if opc == 0x6 and (w & 0xF) == 0xA:
            print(f"  {a:#07x}: {w:04X}  negc r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # EXTU.B
        if opc == 0x6 and (w & 0xF) == 0xC:
            print(f"  {a:#07x}: {w:04X}  extu.b r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # EXTU.W
        if opc == 0x6 and (w & 0xF) == 0xD:
            print(f"  {a:#07x}: {w:04X}  extu.w r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # EXTS.B
        if opc == 0x6 and (w & 0xF) == 0xE:
            print(f"  {a:#07x}: {w:04X}  exts.b r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # EXTS.W
        if opc == 0x6 and (w & 0xF) == 0xF:
            print(f"  {a:#07x}: {w:04X}  exts.w r{(w>>4)&0xF},r{(w>>8)&0xF}")
            continue
        # STS MACL/MACH
        if w == 0x001A:
            print(f"  {a:#07x}: {w:04X}  sts macl,r0"); continue
        if (w & 0xF0FF) == 0x000A:
            print(f"  {a:#07x}: {w:04X}  sts mach,r{(w>>8)&0xF}"); continue
        if (w & 0xF0FF) == 0x001A:
            print(f"  {a:#07x}: {w:04X}  sts macl,r{(w>>8)&0xF}"); continue
        # LDS Rn,MACL
        if (w & 0xF0FF) == 0x401A:
            print(f"  {a:#07x}: {w:04X}  lds r{(w>>8)&0xF},macl"); continue
        # LDS Rn,MACH
        if (w & 0xF0FF) == 0x400A:
            print(f"  {a:#07x}: {w:04X}  lds r{(w>>8)&0xF},mach"); continue
        # CLRT
        if w == 0x0008:
            print(f"  {a:#07x}: {w:04X}  clrt"); continue
        # SETT
        if w == 0x0018:
            print(f"  {a:#07x}: {w:04X}  sett"); continue
        # ROTL
        if (w & 0xF0FF) == 0x4004:
            print(f"  {a:#07x}: {w:04X}  rotl r{(w>>8)&0xF}"); continue
        # ROTR
        if (w & 0xF0FF) == 0x4005:
            print(f"  {a:#07x}: {w:04X}  rotr r{(w>>8)&0xF}"); continue
        # ROTCL
        if (w & 0xF0FF) == 0x4024:
            print(f"  {a:#07x}: {w:04X}  rotcl r{(w>>8)&0xF}"); continue
        # ROTCR
        if (w & 0xF0FF) == 0x4025:
            print(f"  {a:#07x}: {w:04X}  rotcr r{(w>>8)&0xF}"); continue
        # DMULS.L / DMULU.L
        if opc == 0x3 and (w & 0xF) == 0xD:
            print(f"  {a:#07x}: {w:04X}  dmuls.l r{(w>>4)&0xF},r{(w>>8)&0xF}"); continue
        if opc == 0x3 and (w & 0xF) == 0x5:
            print(f"  {a:#07x}: {w:04X}  dmulu.l r{(w>>4)&0xF},r{(w>>8)&0xF}"); continue
        # ADDC / ADDV
        if opc == 0x3 and (w & 0xF) == 0xE:
            print(f"  {a:#07x}: {w:04X}  addc r{(w>>4)&0xF},r{(w>>8)&0xF}"); continue
        # SUBC / SUBV
        if opc == 0x3 and (w & 0xF) == 0xA:
            print(f"  {a:#07x}: {w:04X}  subc r{(w>>4)&0xF},r{(w>>8)&0xF}"); continue
        print(f"  {a:#07x}: {w:04X}  ?")


# Key handlers
disasm(0x5300a, 120, "SID 0x34 RequestDownload FUN_0005300a")
disasm(0x5341a, 8, "SID 0x36 TransferData entry")
disasm(0x5341e, 8, "SID 0x37 RequestTransferExit entry")
disasm(0x53760, 20, "Common bra tail 0x53760")
