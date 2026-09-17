import sys; sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'); import v282cmp as V
import numpy as np
for r in ["00000064--ce6b0b0ebb","0000006c--68c6e94b17"]:
    S=V.load(r); u=V.usable(S)
    D=np.load(V.CACHE/f"{r}.npz")
    print(r, len(S['t']), u.sum()/100)
    sr=S['sr'][u]; sa=S['sa'][u]
    print(' sr uniq steps', np.unique(np.round(np.diff(np.unique(np.round(sr,4))),4))[:8])
    print(' sa uniq steps', np.unique(np.round(np.diff(np.unique(np.round(sa,4))),4))[:8])
    te4=D['t_e4']; print(' e4 dt median', np.median(np.diff(te4)), len(te4), 'cs dt', np.median(np.diff(S['t'])))
    e4=D['e4_cmd']; de=np.diff(e4); print(' |de4| pct', np.percentile(np.abs(de),[50,90,99,99.9,100]), 'frac>=120', np.mean(np.abs(de)>=120))
    print(' e4/out fit', np.polyfit(S['out'][u], S['e4'][u],1))
    yaw=D['cs_yaw']; print(' yaw steps', np.unique(np.round(np.diff(np.unique(np.round(yaw,6))),6))[:5])
    # carState vs cs clock rates
    print(' cst dt', np.median(np.diff(D['t_cst'])), 'frac repeated sr', np.mean(np.diff(D['sr_deg'])==0), 'sa rep', np.mean(np.diff(D['sa_deg'])==0))
    del S,D
