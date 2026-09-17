"""ATTRIBUTION: rev 6.4 over-delivers 1.25-1.28 at 0.15-0.60 Hz on the highway.
Is AccordHoldLevel responsible?

HONDA_ACCORD_HOLD_LEVEL_V = [1.15, 1.45] on breakpoints [12.5, 17.5] m/s, i.e.
  <=12.5 m/s : x1.15      17.5+ m/s : x1.45      linear between.
If the level is the cause, the over-delivery must TRACK THAT SCHEDULE across speed.
If it is flat in speed, something else is doing it.
"""
import math, numpy as np
from scipy import signal
CA='analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),
                v=np.interp(t,D['t_cst'],D['vego']),pr=np.interp(t,D['t_cst'],D['spress'])>0.5,
                lad=D['cs_la_des'],laa=D['cs_la_act'],f=D['cs_f'],p=D['cs_p'],i=D['cs_i'],out=D['cs_out'],
                sa=np.interp(t,D['t_cst'],D['sa_deg']))
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz'); C=load('r76_v293_ident.npz')
FS=A['FS']
LVL=lambda v: np.interp(v,[12.5,17.5],[1.15,1.45])

def segs(sets,vlo,vhi,ml):
    out=[]
    for S in sets:
        t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo)&(S['v']<vhi); n,i=len(m),0
        while i<n:
            if not m[i]: i+=1; continue
            j=i
            while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
            if (j+1-i)/FS>=ml: out.append((S['lad'][i:j+1],S['laa'][i:j+1],float(np.median(S['v'][i:j+1]))))
            i=j+1
    return out
def band(sg,f1,f2):
    if not sg: return None
    nps=int(2**np.floor(np.log2(min(len(x) for x,_,_ in sg))))
    if nps<64: return None
    Pxx=Pyy=Pxy=None; fr=None; sec=0
    for x,y,_ in sg:
        xs,ys=x-x.mean(),y-y.mean()
        fq,pxx=signal.welch(xs,FS,nperseg=nps,noverlap=nps//2)
        _,pyy=signal.welch(ys,FS,nperseg=nps,noverlap=nps//2)
        _,pxy=signal.csd(xs,ys,FS,nperseg=nps,noverlap=nps//2)
        w=len(xs); Pxx=pxx*w if Pxx is None else Pxx+pxx*w
        Pyy=pyy*w if Pyy is None else Pyy+pyy*w; Pxy=pxy*w if Pxy is None else Pxy+pxy*w
        fr=fq; sec+=w/FS
    s=(fr>=f1)&(fr<f2)
    if s.sum()<2: return None
    Hf=np.abs(Pxy[s])/np.maximum(Pxx[s],1e-30)
    coh=np.abs(Pxy[s])**2/np.maximum(Pxx[s]*Pyy[s],1e-30)
    return float(np.average(Hf,weights=Pxx[s])), float(np.average(coh,weights=Pxx[s])), sec, len(sg)

print("="*96)
print("DOES THE OVER-DELIVERY TRACK THE AccordHoldLevel SCHEDULE?")
print("="*96)
print(f"  {'speed':>12} {'level':>6} | {'MID 0.15-0.30':^22} | {'FINE 0.30-0.60':^22}")
print(f"  {'':>12} {'':>6} | {'|H|':>6} {'coh':>6} {'s':>4} {'n':>3} | {'|H|':>6} {'coh':>6} {'s':>4} {'n':>3}")
for lo,hi in [(12.5,16.),(16.,19.),(19.,23.),(23.,27.),(27.,34.)]:
    row=f"  {lo:5.1f}-{hi:<5.1f} {LVL((lo+hi)/2):6.2f} |"
    for f1,f2,ml in [(0.15,0.30,30.),(0.30,0.60,20.)]:
        r=band(segs([A,B],lo,hi,ml),f1,f2)
        row += (f" {r[0]:6.3f} {r[1]:6.3f} {r[2]:4.0f} {r[3]:3d} |" if r else f" {'--':>6} {'--':>6} {'--':>4} {'--':>3} |")
    print(row)

print()
print("="*96)
print("WHO IS SUPPLYING THE EXTRA?  feedforward vs P vs I, highway engaged (lat-accel units)")
print("="*96)
print(f"  {'route':>10} {'rev':>6} {'mean|f|':>9} {'mean|p|':>9} {'mean|i|':>9} {'f share':>9} {'mean|out| tq':>13}")
for tag,S,rev in [('6c',A,'6.4'),('6d',B,'6.4'),('76',C,'5')]:
    m=S['act']&~S['pr']&(S['v']>=17.5)
    if m.sum()<500: continue
    tot=np.abs(S['f'][m])+np.abs(S['p'][m])+np.abs(S['i'][m])
    print(f"  {tag:>10} {rev:>6} {np.mean(np.abs(S['f'][m])):9.4f} {np.mean(np.abs(S['p'][m])):9.4f} "
          f"{np.mean(np.abs(S['i'][m])):9.4f} {np.mean(np.abs(S['f'][m])/np.maximum(tot,1e-9)):9.3f} "
          f"{np.mean(np.abs(S['out'][m])):13.4f}")

print()
print("="*96)
print("SANITY: is the FEEDFORWARD itself bigger per degree of angle on rev 6.4 than rev 5?")
print("  (the hold level multiplies the hold term, so at matched speed+angle |f| should scale by it)")
print("="*96)
print(f"  {'speed':>12} {'|angle| 1-4 deg':>28}")
print(f"  {'':>12} {'rev5 |f|/deg':>14} {'rev6.4 |f|/deg':>14} {'ratio':>8} {'expected':>9}")
for lo,hi in [(17.5,22.),(22.,27.)]:
    vals={}
    for tag,sets in [('5',[C]),('6.4',[A,B])]:
        num=den=0.0
        for S in sets:
            m=S['act']&~S['pr']&(S['v']>=lo)&(S['v']<hi)&(np.abs(S['sa'])>1.0)&(np.abs(S['sa'])<4.0)
            if m.sum()<100: continue
            num+=float(np.sum(np.abs(S['f'][m]))); den+=float(np.sum(np.abs(S['sa'][m])))
        vals[tag]=num/den if den>0 else float('nan')
    exp=LVL((lo+hi)/2)/1.0   # rev 5 had no level
    print(f"  {lo:5.1f}-{hi:<5.1f} {vals.get('5',float('nan')):14.5f} {vals.get('6.4',float('nan')):14.5f} "
          f"{vals.get('6.4',float('nan'))/max(vals.get('5',float('nan')),1e-9):8.3f} {exp:9.2f}")
