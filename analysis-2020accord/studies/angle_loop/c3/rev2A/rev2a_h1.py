# -*- coding: utf-8 -*-
r"""rev2a_h1.py -- H1 for the rev2A cave: the ASSEMBLED R1-P bytes EXECUTED by e2_asm's validated V850E2 interpreter
(CONTROL-B equal to ds_asm) against a scalar reference of the rev2A cave decision (theta_sp-ref bound + F3 E-zero).
Edge-heavy inputs incl. the 0x7FFF/+-13000 validity edges, |tq| at 512+-1, the bound edges, ramp states, table knots.
ANALYSIS ONLY.  BELIEF until Ghidra decodes a BUILT image (builder H5)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; AL=HERE.parents[1]
sys.path.insert(0,str(AL/"panel2"/"E2-integral-most-margin")); sys.path.insert(0,str(AL/"panel"/"D-structure"))
sys.path.insert(0,str(HERE))
import e2_asm as EA
import c1_lib as C
import rev2a_asm as RA
CAVE,RET,FRZ_RET,GP=EA.CAVE,EA.RET,EA.FRZ_RET,EA.GP

CELLS={"6a5e":(-0x6A5E,2),"4f68":(-0x4F68,2),"4f60":(-0x4F60,2),"6abe":(-0x6ABE,2),
       "6a00":(-0x6A00,2),"69ae":(-0x69AE,2),"6dd0":(-0x6DD0,4)}
SCRATCH=(6,8,9,13,16,26)

def rev2a_ref(pol, tbl, sp, r26, cells, ramp):
    """rev2A cave decision: bound on gp-0x69ae (|sp|<<2/<<4); F3: op invalid -> E:=0 -> Ep=0."""
    G=C.cave_G(cells["6a5e"]&0xFFFF, tbl)
    E=EA.s32((sp<<2)-r26)
    ab=cells["6abe"]; valid=((ab+13000)&0xFFFFFFFF)<=26000
    op= ab if valid else 0
    if not valid: E=0                                  # F3: cmovh r0,r16,r16
    Ep=EA.s32(E*G)>>8
    atq=cells["4f68"]&0xFFFF
    if atq>pol.get("thr",512): return Ep,FRZ_RET,0,op
    # theta_sp-ref bound
    thsp=cells["69ae"]
    sh=pol["arb_sh"]
    if pol.get("arb_sh_lo") is not None and (cells["6a5e"]&0xFFFF)<=pol["arb_vth"]: sh=pol["arb_sh_lo"]
    bound=EA.s32((abs(thsp)<<sh)+pol["arb_B"])
    if pol.get("arb_vcap") is not None and (cells["6a5e"]&0xFFFF)<=pol["arb_vcap"] and bound>pol["arb_cap"]:
        bound=pol["arb_cap"]
    I_S=cells["6dd0"]>>10
    t=I_S if Ep>=0 else -I_S
    if t>=bound: return Ep,FRZ_RET,0,op
    if (ramp&0x8000)==0: return Ep,FRZ_RET,0,op
    return Ep,RET,None,op

def h1(pol, src, N=40000, seed=11):
    rows=RA.raised_rows(src); tbl=[tuple(r) for r in rows]
    ent=RA.rev2a_entries(pol,tbl,f3=True); code,labels,lines=RA.assemble(ent)
    rng=np.random.default_rng(seed); bad=0
    edges=[0,32000,65535]+[x+d for x,_,_ in tbl if x<0xFFFF for d in (-1,0,1)]
    thr=pol.get("thr",512)
    for k in range(N):
        sp=int(rng.integers(-16384,16385)) if k%50 else 32767
        r26=int(rng.integers(-65535,65536))
        v=int(rng.integers(0,32001)) if k%7 else int(rng.choice(edges))
        tq=int(rng.integers(-3000,3000)) if k%3 else int(rng.choice([0,thr,thr+1,-thr,-thr-1,32767,-32768]))
        ramp=int(rng.choice([0x8000,0x8000,0x8000,int(rng.integers(1,0x8000))]))
        i8=int(rng.integers(-16384*8*128,16384*8*128)) if k%5 else int(rng.choice([0,1023,1024,-1024,-1025]))
        thsp=int(rng.integers(-16384,16385)) if k%4 else int(rng.choice([0,1,-1,16000,-16000]))
        if pol.get("arb_sh") and k%2:
            shv=pol["arb_sh_lo"] if (cells_vth:=(pol.get("arb_sh_lo") is not None)) and v<=pol["arb_vth"] else pol["arb_sh"]
            b=(abs(thsp)<<shv)+pol["arb_B"]; i8=int(rng.choice([b,b-1,b+1,-b,-b-1]))*1024+int(rng.integers(0,1024))
        abe=int(rng.choice([32767,int(rng.integers(-14000,14000)),-13001,13000,-13000,13001]))
        cells={"6a5e":v,"4f68":min(abs(tq),0xFFFF),"4f60":tq,"6abe":abe,"6a00":int(rng.integers(-12000,12001)),
               "69ae":thsp,"6dd0":i8}
        mem={}
        for nm,(off,w) in CELLS.items():
            a=(GP+off)&0xFFFFFFFF; val=cells[nm]&((1<<(8*w))-1)
            for i in range(w): mem[a+i]=(val>>(8*i))&0xFF
        for i,bb in enumerate(code): mem[CAVE+i]=bb
        regs={i:int(rng.integers(-2**31,2**31)) for i in range(32)}
        regs.update({0:0,16:sp,26:r26,14:ramp,4:EA.s32(GP),6:RET,25:int(rng.integers(-2**31,2**31))})
        pc_exit,rr,mem2=EA.run_bytes(code,CAVE,regs,mem,CAVE)
        r16,ex,r6,op=rev2a_ref(pol,tbl,sp,r26,cells,ramp)
        ok=rr[16]==r16 and pc_exit==ex and (r6 is None or rr[6]==r6) and rr[26]==op
        ok=ok and all(rr[i]==regs[i] for i in range(32) if i not in SCRATCH) and mem2==mem
        if not ok:
            bad+=1
            if bad<=3: print("  MISMATCH",dict(sp=sp,r26=r26,tq=tq,ramp=ramp),cells,"got",rr[16],rr[26],rr[6],hex(pc_exit),"want",r16,op,r6,hex(ex))
    return bad

if __name__=="__main__":
    for nm,(pol,src) in {"R1-P":(RA.POL_A3,"C3-P"),"R1-PA2":(RA.POL_A2,"C3-PA2")}.items():
        b=h1(pol,src)
        print(f"{nm}: H1 bytes-vs-rev2a_ref (theta_sp bound + F3), 40000 edge-heavy inputs: {b} mismatches")
