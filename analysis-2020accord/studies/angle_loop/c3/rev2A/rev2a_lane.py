# -*- coding: utf-8 -*-
r"""rev2a_lane.py -- REVISER-1 rev2A time-domain lane on top of the validated c3nl_sim (K3/K4 bit-exact to the common
time scorer).  Per-column config lets C3-P (orig) / R1-P (rev2A) / P2 run side-by-side through c3nl_lens' own scenarios.
Edits vs C3-P (each a named finding fix, all PER-COLUMN):
  (F1) Ki 56->18 (cal 0xC63E6, 0 bytes); (N2) dip knot 463->520 (table DATA, 0 code bytes);
  (N1/N5) bound on the SETPOINT gp-0x69ae (|sp|<<2/<<4), byte-neutral; (F3) E:=0 on rate-invalid (+4 B cmovh);
  (H-cam) optional gate on gp-0x6803==2 (r25), off unless requested.
Control: a column with ki56/theta/no-f3/orig-table reproduces c3nl_sim.Lane tick-for-tick."""
from __future__ import annotations
import struct, sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import c3nl_sim as S

def raise_dip_hex(src_hex, newG=520):
    b=bytearray(S.hexbytes(src_hex)); i=b.find(bytes.fromhex("2906"))
    taddr=struct.unpack_from("<I",b,i+2)[0]; off=taddr-0xC4C00
    rows=[list(struct.unpack_from("<HHh",b,off+6*k)) for k in range((len(b)-off)//6)]
    j=[k for k,r in enumerate(rows) if r[0]==2707][0]; rows[j][1]=newG
    def sl(k):
        n=(rows[k+1][1]-rows[k][1])*4096; d=rows[k+1][0]-rows[k][0]; q=abs(n)//abs(d); return -q if n<0 else q
    rows[j-1][2]=sl(j-1); rows[j][2]=sl(j)
    for k,r in enumerate(rows): struct.pack_into("<HHh",b,off+6*k,r[0]&0xFFFF,r[1]&0xFFFF,r[2])
    return bytes(b)

A3_SP=(2,4,2880,1250,1382,4096); A2_SP=(2,4,2880,1250,-1,0)
# base impls (rows + arb shifts for theta_sp-ref); Ki is set per-column in CFG so one hex serves every Ki variant
for cid,src,dop,kd,arb in (("R1-P","C3-P","fresh",48,A3_SP),("R1-F","C3-F","held",24,A3_SP),
                           ("R1-PA2","C3-PA2","fresh",48,A2_SP)):
    p=HERE/f"_rev2a_rows_{cid}.hex"; p.write_text(raise_dip_hex(S.C3D/f"c3_cave_{src}.hex",520).hex(" "))
    S._impl(cid,p,dop,kd,8192,arb)
# Ki variants reuse the same registered rows/arb (alias to the base impl bytes)
for base in ("R1-P","R1-F"):
    for ki in (18,32,36,40,44,48,56):
        nm=f"{base}{ki}"
        S.IMPL[nm]=dict(S.IMPL[base])   # same rows/glut/arb/dop/kd/icl

# per-impl rev2A config (ki, bound-ref, f3-zero-E).  C3/P2/E2 originals keep their published behaviour.
CFG={"R1-P":dict(ki=40,bound="sp",f3=True),"R1-F":dict(ki=40,bound="sp",f3=True),"R1-PA2":dict(ki=40,bound="sp",f3=True)}
for base in ("R1-P","R1-F"):
    for ki in (18,32,36,40,44,48,56):
        CFG[f"{base}{ki}"]=dict(ki=ki,bound="sp",f3=True)
DEFAULT=dict(ki=56,bound="theta",f3=False)

class Rev2ALane(S.Lane):
    def __init__(self, impls, cam=False):
        super().__init__(impls); self.impls=list(impls); self.cam_on=cam
        cf=[dict(DEFAULT,**CFG.get(i,{})) for i in impls]
        self.kiv=np.array([c["ki"] for c in cf],np.int64)
        self.use_sp=np.array([c["bound"]=="sp" for c in cf])
        self.f3v=np.array([c["f3"] for c in cf])
    def tick(self,a6a00,abe,x6a56,sp69ae,tq,ramp,act,req,vw,pol=-1,r6803=None):
        c=S.CAL; B=self.B
        bc=lambda a:np.broadcast_to(np.asarray(a,np.int64),(B,))
        ramp,act,req,tq,vw=bc(ramp),bc(act),bc(req),bc(tq),bc(vw)&0xFFFF
        x=S.s16(a6a00); valid=(x>=-12000)&(x<=12000)
        s_old=np.where(self.lane_ok==1,self.s,0); s_new=S.s32((S.s32(0*s_old)>>10)+(S.s32(x*8192)>>10))
        r26=np.clip(S.s32(s_old+s_new),-65535,65535)
        self.s=np.where(valid,s_new,self.s); r26=np.where(valid,r26,0); self.lane_ok=np.where(valid,1,2)
        run=valid&(ramp!=0)&(req==1)
        if self.cam_on and r6803 is not None: run=run&(bc(r6803)==2)
        sp=S.s16(sp69ae); E=S.s32(S.s32(sp<<2)-r26)
        ab=S.s16(abe); vabe=((ab+13000)&0xFFFFFFFF)<=26000; op=np.where(vabe,ab,0)
        E=np.where(self.f3v & ~vabe, 0, E)                             # F3
        G=self.gl[self.ar,vw]; prod=E*G; self.wraps+=int(np.count_nonzero(S.s32(prod)!=prod)); Ep=S.s32(prod)>>8
        atq=np.minimum(np.abs(tq),0xFFFF); f_hard=atq>512
        bref=np.where(self.use_sp,S.s16(sp69ae),S.s16(a6a00))          # N1/N5
        ath=np.abs(bref); sh=np.where(vw>self.vth,self.sh_hi,self.sh_lo); bound=S.s32((ath<<sh)+self.Bb)
        capon=(self.vcap>=0)&~(vw>self.vcap); bound=np.where(capon&(bound>self.cap),self.cap,bound)
        Is=self.I8>>10; t=np.where(Ep>=0,Is,-Is); f_arb=self.arb_on&(t>=bound); f_ramp=(ramp&0x8000)==0
        frz=f_hard|(~f_hard&(f_arb|f_ramp))
        e5=np.where(frz,0,Ep>>5); inc=S.s32(e5*self.kiv)>>3; acc=(self.I8>>3)+inc
        self.wraps+=int(np.count_nonzero(S.s32(acc)!=acc)); I=np.clip(S.s32(acc),-self.icl,self.icl); I8n=S.s32(I<<3)
        P=np.clip(S.s32(Ep*S.KP)>>8,-c["PCL"],c["PCL"])
        Dp=S.s32(self.kd*op)>>3; Dh=S.s32(-self.kd*S.s16(x6a56))>>3; D=np.clip(np.where(self.fresh,Dp,Dh),-S.DCL,S.DCL)
        Sv=S.s32((I>>7)+P+D); i682f=np.minimum(np.abs(tq>>5),255); fB=S.lerp_vec(*c["fadeB"],i682f); f=((S.FA0*fB)&0xFFFF)>>8
        Sf=S.s32(Sv*f)>>8; SCL=c["SCL"]; Sc=np.where(Sf>SCL,SCL,np.where(Sf<-SCL,-SCL,S.s16(Sf))); Sc=np.where(run,Sc,0)
        self.I8=np.where(run,I8n,0)
        t1=S.s32(Sc*c["ob"])>>10; t2=S.s32(c["oa"]*self.olag)>>10; o_new=S.s32(t2+t1); y=S.s32(self.olag+o_new)>>5; self.olag=o_new
        yr=S.s16(S.s32(y*ramp)>>15)
        if c["g74a3"]==1:
            blk=((S.s16(y)<=c["dz"])&(y>=-c["dz"]))|(S.s32(y*self.Tprev)<=0); yr=np.where((act==0)&blk,0,yr)
        k=pol*c["fwd"]; r11=S.s32(yr*k)>>15; T=np.clip(r11,-c["OCL"],c["OCL"]); self.Tprev=yr
        self.log=dict(I=np.where(run,I>>7,0),P=np.where(run,P,0),D=np.where(run,D,0),frz=frz&run,
                      farb=f_arb&~f_hard&run,bound=bound,Ep=Ep,run=run)
        return S.s16(T)

def control():
    rng=np.random.default_rng(5); ids=["C3-P","C3-F"]; base=S.Lane(ids); mirror=Rev2ALane(ids); B=2; bad=0
    for it in range(20000):
        a6=int(rng.choice([rng.integers(-3000,3001),12000,0])); abe=int(rng.choice([rng.integers(-13001,13002),0x7FFF,13000,-13000]))
        x56=int(rng.integers(-12000,12001)); sp=int(rng.choice([rng.integers(-16384,16385),4*a6,0x7FFF]))
        tq=int(rng.choice([rng.integers(-3000,3001),512,-512,0])); ramp=int(rng.choice([0x8000,0,int(rng.integers(0,0x8001))]))
        req=int(rng.choice([1,1,0])); act=int(rng.choice([1,0])); vw=int(rng.choice([0,714,1843,2304,2707,2880,4032,int(rng.integers(0,9000))]))
        Tb=base.tick(np.full(B,a6),np.full(B,abe),np.full(B,x56),np.full(B,sp),tq,ramp,act,req,np.full(B,vw))
        Tm=mirror.tick(np.full(B,a6),np.full(B,abe),np.full(B,x56),np.full(B,sp),tq,ramp,act,req,np.full(B,vw))
        if not (np.array_equal(Tb,Tm) and np.array_equal(base.I8,mirror.I8) and np.array_equal(base.olag,mirror.olag)): bad+=1
    return bad
if __name__=="__main__":
    print("control (C3-P/C3-F cols via Rev2ALane == c3nl_sim.Lane):",control(),"/ 20000")
