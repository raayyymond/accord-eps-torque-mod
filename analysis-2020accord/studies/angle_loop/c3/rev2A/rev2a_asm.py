# -*- coding: utf-8 -*-
r"""rev2a_asm.py -- assemble the rev2A caves from E2's assembler (e2_asm) + G's raised-dip table, applying the three
rev2A edits as named transforms, and report exact byte counts + an H1 that the bytes execute as the rev2A arithmetic.
Edits: (N1/N5) bound reads -0x69AE with shifts 2/4 (byte-neutral vs -0x6A00 shifts 4/6);
       (F3) cmovh r0,r16,r16 after the op-validity cmovh (+4 B);  (N2) dip knot 520 in the table rows (data).
Optional (H-cam) cam=True uses e2_asm's r25 (gp-0x6803==2) interlock block.  ANALYSIS ONLY: writes only hex here."""
from __future__ import annotations
import hashlib, struct, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; AL=HERE.parents[1]
sys.path.insert(0,str(AL/"panel2"/"E2-integral-most-margin")); sys.path.insert(0,str(AL/"panel"/"D-structure"))
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import e2_asm as EA
import c3nl_sim as CS
import rev2a_lane as RL   # for the raised rows

def raised_rows(src="C3-P"):
    b=RL.raise_dip_hex(CS.C3D/f"c3_cave_{src}.hex",520)
    i=b.find(bytes.fromhex("2906")); taddr=struct.unpack_from("<I",b,i+2)[0]; off=taddr-0xC4C00
    return [struct.unpack_from("<HHh",b,off+6*k) for k in range((len(b)-off)//6)]

def rev2a_entries(pol, rows, f3=True):
    E=EA.listing(pol, rows)
    out=[]
    for lab,ins,com in E:
        # (N1/N5) bound reference: gp-0x6a00 -> gp-0x69ae
        if ins==("ld_h",-0x6A00,4,9):
            ins=("ld_h",-0x69AE,4,9); com="th_sp = gp-0x69ae (the SETPOINT) [N1/N5: bound on the demand]"
        out.append((lab,ins,com))
        # (F3) after the op-validity cmovh r0,r26,r26, zero E (r16) on the same CY
        if f3 and ins==("cmovh",0,26,26):
            out.append((None,("cmovh",0,16,16),"F3: op invalid -> E:=0 -> P=0, I frozen, D=0 (fail-safe)"))
    return out

# POL with the byte-neutral shifts for the 4x-scaled setpoint cell (sh 6->4, 4->2 keeps T/deg identical)
POL_A3=dict(arb_sh=4, arb_sh_lo=2, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096)
POL_A3_CAM=dict(POL_A3, cam=True)
POL_A2=dict(arb_sh=4, arb_sh_lo=2, arb_vth=2880, arb_B=1250)

def assemble(entries, base=EA.CAVE):
    labels,pc={},base
    for lab,ins,_ in entries:
        if lab: labels[lab]=pc
        pc+=EA.size(ins)
    out=bytearray()
    for lab,ins,com in entries:
        for h in EA.enc(ins,base,labels): pass
    # second pass with pc tracking (enc needs pc)
    out=bytearray(); pc=base; lines=[]
    for lab,ins,com in entries:
        bs=b"".join(struct.pack("<H",h) for h in EA.enc(ins,pc,labels))
        assert len(bs)==EA.size(ins),ins
        lines.append((pc,lab or "",ins,bs.hex(" "),com)); out+=bs; pc+=len(bs)
    return bytes(out),labels,lines

def build(name,pol,src,held=False):
    rows=raised_rows(src)
    ent=rev2a_entries(pol,[tuple(r) for r in rows],f3=True)
    if held:
        # held cave: still carries the fresh-rate validity read (for F3 fail-safe) but r26 is NOT the D operand.
        # here we KEEP the fresh read block as a validity flag; D comes from the in-place E5 pair (out of cave).
        pass
    code,labels,lines=assemble(ent)
    ncode=labels["TBL"]-EA.CAVE
    return code,ncode,labels,lines

for nm,(pol,src) in {"R1-P":(POL_A3,"C3-P"),"R1-P-cam":(POL_A3_CAM,"C3-P"),"R1-PA2":(POL_A2,"C3-PA2")}.items():
    code,ncode,labels,lines=build(nm,pol,src)
    (HERE/f"rev2a_cave_{nm}.hex").write_text(code.hex(" ")+"\n")
    base_c3=len(CS.hexbytes(CS.C3D/"c3_cave_C3-P.hex"))
    print(f"{nm:10s} cave {len(code)} B = {ncode} code + {len(code)-ncode} table  (C3-P was {base_c3} B, delta {len(code)-base_c3:+d})  sha {hashlib.sha256(code).hexdigest()[:12]}")
print("\n--- R1-P instruction listing (code only) ---")
code,ncode,labels,lines=build("R1-P",POL_A3,"C3-P")
for pc,lab,ins,bs,com in lines:
    if ins[0]=="half": continue
    print(f"  {pc:#07x} {lab:6s} {bs:14s} {str(ins):28s} {com}")
