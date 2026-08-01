import numpy as np, glob, os, json
# save the gate-validation numbers so the claim is reproducible, not just written down
out={}
for d in ('_cache_r29','_cache_r28'):
    n=0; agree=0; duty=0; trans=0; span=0.0
    for f in sorted(glob.glob(os.path.join(d,'*s*.npz'))):
        if '_imu' in f: continue
        z=np.load(f)
        if 'probe' not in z.files: continue
        p=z['probe'].astype(int); lat=z['cc_lat']>0.5; t=z['t']
        raw = p if p.max()>31 else (p<<3)|7
        cell = ~((raw>>6)&1).astype(bool)          # V57 bit6 = (gp-0x6806 == 0)
        n+=len(p); agree+=int((cell==lat).sum()); duty+=int(cell.sum())
        trans+=int((np.diff(cell.astype(int))!=0).sum())
        span+=float(t[-1]-t[0]) if len(t)>1 else 0.0
    out[d]=dict(frames=n, span_s=round(span,1), agreement_pct=round(100*agree/n,3),
                duty_pct=round(100*duty/n,2), transitions=trans,
                transitions_per_s=round(trans/span,4))
json.dump(out, open('analysis-2020accord/_gp6806_gate_validation.json','w'), indent=1)
print(json.dumps(out, indent=1))
