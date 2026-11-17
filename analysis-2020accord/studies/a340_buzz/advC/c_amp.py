import numpy as np
A=dict(np.load('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/_scratch/cache/a340_user55/_features.npz'))
eng=A['eng'];bz=A['bz'];v=A['v'];tq=np.abs(A['tlp']);ang=np.abs(A['ang']);rl=np.abs(A['rlp']);pr=A['pressed']
base=(v>8)&(rl<2)&(ang<10)
print('cell: |tq| bin | engaged: n s, duty, BZ p50 | in-buzz BZ p50 | manual: n s, duty, BZ p50 | in-buzz p50')
for lo,hi in ((0,80),(80,300),(300,800),(800,3000)):
    out=[]
    for e in (True,False):
        m=base&(eng==e)&(tq>=lo)&(tq<hi)
        b=m&(bz>4)
        out.append(f'{m.sum()/100:5.0f}s duty {100*(bz[m]>4).mean() if m.sum()>50 else np.nan:5.1f}% p50 {np.median(bz[m]) if m.sum()>50 else np.nan:5.2f} | buzzing p50 {np.median(bz[b]) if b.sum()>50 else np.nan:5.2f}')
    print(f'{lo:4d}-{hi:4d}  E: {out[0]}   M: {out[1]}')
