"""liveDelay stream per route: lateralDelay, status, validBlocks, estimate, std, calPerc (all segments)."""
import sys, glob, os, json, time
import numpy as np
sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib')
from rlog_parse import read_messages
R='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/rlogs/'
OUT='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_lagbudgetand/_ld'
os.makedirs(OUT, exist_ok=True)
routes=sys.argv[1:]
for r in routes:
    if os.path.exists(f'{OUT}/{r}.npz'): print('skip',r); continue
    segs=sorted(glob.glob(R+f'75604b0a432fdc89_{r}--*--rlog.zst'), key=lambda p:int(os.path.basename(p).split('--')[2]))
    A={k:[] for k in ('t','ld','st','vb','est','std','cal','valid')}
    t0=time.time()
    for p in segs:
        for e in read_messages(p):
            try:
                if e.which()!='liveDelay': continue
            except Exception: continue
            d=e.liveDelay
            A['t'].append(e.logMonoTime/1e9); A['ld'].append(d.lateralDelay); A['st'].append(int(d.status)) if isinstance(d.status,int) else A['st'].append(['unestimated','estimated','invalid'].index(str(d.status)))
            A['vb'].append(d.validBlocks); A['est'].append(d.lateralDelayEstimate); A['std'].append(d.lateralDelayEstimateStd); A['cal'].append(d.calPerc); A['valid'].append(float(e.valid))
    np.savez(f'{OUT}/{r}.npz', **{k:np.asarray(v,float) for k,v in A.items()})
    ld=np.asarray(A['ld']); st=np.asarray(A['st'])
    print(r, len(segs), 'segs', f'{time.time()-t0:.0f}s', 'n',len(ld), 'ld uniq',np.unique(np.round(ld,3))[:8], 'status counts',np.bincount(st.astype(int),minlength=3), 'est med',np.median(A['est']), flush=True)
