"""Two things the config diff surfaced.

(1) 6c and 6d are NOT identical: SteerFriction = 0.0 on 6c, 0.212 on 6d. I pooled them. The code
    says the generic SteerFriction relay is OFF whenever AccordFrictionHyst > 0 (it is, 0.015), so
    it SHOULD make no difference -- but that is an assumption I imported from a comment. 6c vs 6d
    is a NATURAL EXPERIMENT that tests it on the car. 0.212 is the exact value the code comment
    blames for "4 Hz chatter on straights, 21% of hard-turn frames at the Honda rate cap" on route 73.

(2) AccordRateLoopGain does NOT appear in the rev5-vs-rev6.4 diff, so route 76 flew it too.
    It is therefore not a candidate cause of the CHANGE, though it may still be wrong in absolute terms.
"""
import sys, glob, math
import numpy as np
from scipy import signal
sys.path.insert(0,'/home/user/accord-eps-torque-mod/rlog-tools/lib')
from rlog_parse import read_messages

print("="*96)
print("(2) WHAT DID ROUTE 76 ACTUALLY FLY?  all Accord params, rev 5")
print("="*96)
p=sorted(glob.glob('/home/user/accord-eps-torque-mod/analysis-2020accord/rlogs/'
                   '75604b0a432fdc89_00000076--*--0--rlog.zst'))[0]
n=0
for evt in read_messages(p):
    try: w=evt.which()
    except Exception: continue
    n+=1
    if w=='initData':
        for e in evt.initData.params.entries:
            k=e.key if isinstance(e.key,str) else e.key.decode('utf8','ignore')
            if k.startswith('Accord') or k in ('SteerFriction','SteerRatio','SteerKp','SteerLatAccel'):
                v=e.value
                v=v.decode('utf8','ignore') if isinstance(v,(bytes,bytearray)) else str(v)
                print(f"   {k:34s} = {v[:30]}")
        break
    if n>5000: break

print()
print("="*96)
print("(1) NATURAL EXPERIMENT: 6c (SteerFriction 0.0) vs 6d (SteerFriction 0.212)")
print("    If the AccordFrictionHyst gate works on the car, the two must agree.")
print("="*96)
CA='analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']; v=np.interp(t,D['t_cst'],D['vego'])
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),v=v,
                pr=np.interp(t,D['t_cst'],D['spress'])>0.5, model=D['cs_des_curv']*v*v,
                laa=D['cs_la_act'], out=D['cs_out'], sr=np.interp(t,D['t_cst'],D['sr_deg']))
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz'); FS=A['FS']
def segs(S,vlo,vhi,ml):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo)&(S['v']<vhi); out=[]; n,i=len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=ml: out.append((S['model'][i:j+1],S['laa'][i:j+1]))
        i=j+1
    return out
def band(sg,f1,f2):
    if not sg: return None
    nps=int(2**np.floor(np.log2(min(len(x) for x,_ in sg))))
    if nps<64: return None
    Pxx=Pyy=Pxy=None; fr=None; sec=0
    for x,y in sg:
        xs,ys=x-x.mean(),y-y.mean()
        f,pxx=signal.welch(xs,FS,nperseg=nps,noverlap=nps//2)
        _,pyy=signal.welch(ys,FS,nperseg=nps,noverlap=nps//2)
        _,pxy=signal.csd(xs,ys,FS,nperseg=nps,noverlap=nps//2)
        w=len(xs); Pxx=pxx*w if Pxx is None else Pxx+pxx*w
        Pyy=pyy*w if Pyy is None else Pyy+pyy*w; Pxy=pxy*w if Pxy is None else Pxy+pxy*w
        fr=f; sec+=w/FS
    s=(fr>=f1)&(fr<f2)
    if s.sum()<2: return None
    Hf=np.abs(Pxy[s])/np.maximum(Pxx[s],1e-30)
    coh=np.abs(Pxy[s])**2/np.maximum(Pxx[s]*Pyy[s],1e-30)
    return float(np.average(Hf,weights=Pxx[s])),float(np.average(coh,weights=Pxx[s])),sec,len(sg)
print(f"  {'band':>16} {'6c (SF=0)':>18} {'6d (SF=0.212)':>18}   delta")
for name,f1,f2,ml in [('MID  0.15-0.30',0.15,0.30,40.),('FINE 0.30-0.60',0.30,0.60,24.),
                      ('TRANS 0.60-1.20',0.60,1.20,12.)]:
    ra=band(segs(A,15.,34.,ml),f1,f2); rb=band(segs(B,15.,34.,ml),f1,f2)
    sa=f"{ra[0]:.3f} (coh {ra[1]:.2f}, {ra[2]:.0f}s)" if ra else "--"
    sb=f"{rb[0]:.3f} (coh {rb[1]:.2f}, {rb[2]:.0f}s)" if rb else "--"
    d=f"{ra[0]-rb[0]:+.3f}" if (ra and rb) else "--"
    print(f"  {name:>16} {sa:>18} {sb:>18}   {d}")

print()
print("  The 4 Hz chatter signature the comment blames on SteerFriction 0.212:")
print(f"  {'route':>8} {'SteerFric':>10} {'3-5 Hz rms of d(cmd)/dt':>26} {'3-5 Hz rms steering rate':>26}")
for tag,S,sf in [('6c',A,'0.0'),('6d',B,'0.212')]:
    m=S['act']&~S['pr']&(S['v']>15)
    sos=signal.butter(4,[3.0,5.0],btype='band',fs=FS,output='sos')
    # contiguous chunk to avoid filtering across gaps
    idx=np.where(m)[0]
    br=np.where(np.diff(idx)>4)[0]
    chunks=np.split(idx,br+1)
    c=max(chunks,key=len)
    dcmd=np.diff(S['out'][c])*FS
    print(f"  {tag:>8} {sf:>10} {np.std(signal.sosfiltfilt(sos,dcmd)):26.5f} "
          f"{np.std(signal.sosfiltfilt(sos,S['sr'][c])):26.4f}")
