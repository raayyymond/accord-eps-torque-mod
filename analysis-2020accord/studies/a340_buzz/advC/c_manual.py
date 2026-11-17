import sys,glob,os
sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/_scratch')
import numpy as np
from a340_buzz_lib import load,segs
C='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/_scratch/cache/a340_user55'
T=[];BZ=[];REQ=[];CMD=[];V=[];ANG=[];RLP=[];TLP=[];PR=[];RATE=[]
for s,p in segs(C):
    d=load(p); T.append(d['t']+s*60);BZ.append(d['bz']);REQ.append(d['req']);CMD.append(d['cmd']);V.append(d['v']);ANG.append(d['ang']);RLP.append(d['rlp']);TLP.append(d['tlp']);PR.append(d['pressed']);RATE.append(d['rate'])
c=np.concatenate
T,BZ,REQ,CMD,V,ANG,RLP,TLP,PR,RATE=map(c,(T,BZ,REQ,CMD,V,ANG,RLP,TLP,PR,RATE))
print('samples',len(T),'req frac',REQ.mean())
# time since last engaged sample
last=-1e9;since=np.zeros(len(T))
for i in range(len(T)):
    if REQ[i]: last=T[i]
    since[i]=T[i]-last
man=~REQ
buzz=BZ>4
print('manual buzz samples',(man&buzz).sum(),' cmd==0 among them',(CMD[man&buzz]==0).mean(),' |cmd| max',np.abs(CMD[man&buzz]).max())
for th in (0,2,5,10,30,60):
    m=man&(V>2)&(since>=th)&(np.abs(ANG)<30)
    print(f'manual since>={th:3d}s moving near-centre n={m.sum()/100:.0f}s duty={100*buzz[m].mean():.1f}%  BZ p50={np.median(BZ[m]):.2f}')
# episodes: contiguous manual buzz runs >=1s starting >=5 s after last engagement
m=man&buzz&(since>=5)&(V>2)
idx=np.flatnonzero(m); 
runs=np.split(idx,np.flatnonzero(np.diff(idx)>20)+1) if len(idx) else []
runs=[r for r in runs if len(r)>=100]
print('manual buzz runs >=1 s, >=5 s after last engagement:',len(runs),' total s',sum(len(r) for r in runs)/100)
for r in runs[:8]: print('  t=%.1f len=%.1fs since=%.0f v=%.1f cmd=%d req=%d'%(T[r[0]],len(r)/100,since[r[0]],V[r[0]],np.abs(CMD[r]).max(),REQ[r].max()))
# speed profile engaged vs manual, still near centre
print('speed duty (still wheel,|tq|<800,|ang|<10):')
for lo in (0,1,2,4,6,8,10,12,16,20,26):
    hi={0:1,1:2,2:4,4:6,6:8,8:10,10:12,12:16,16:20,20:26,26:34}[lo]
    out=[]
    for lab,e in (('E',REQ),('M',man)):
        mm=(V>=lo)&(V<hi)&(np.abs(RLP)<2)&(np.abs(TLP)<800)&(np.abs(ANG)<10)&e
        out.append(f'{lab} {100*buzz[mm].mean() if mm.sum()>200 else float("nan"):5.1f}%({mm.sum()//100}s)')
    print(f'  {lo:2d}-{hi:2d} m/s ',' '.join(out))
