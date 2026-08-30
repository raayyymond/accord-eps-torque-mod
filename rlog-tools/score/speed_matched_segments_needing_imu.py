import numpy as np, glob, os, sys, re, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SPD_BIN=5.0; MIN_S=20.0
have=set(os.path.basename(p).replace('_imu.npz','') for p in glob.glob('_scratch/cache/*/*_imu.npz'))
need=collections.defaultdict(list)
ok=[]
for c in sorted(glob.glob('_scratch/cache/*/*.npz')):
    b=os.path.basename(c).replace('.npz','')
    if b.endswith('_imu') or '_' in b: continue
    try: z=np.load(c,allow_pickle=True)
    except Exception: continue
    if not {'cc_lat','cs_v','t'} <= set(z.files): continue
    t=np.asarray(z['t'],float); e=np.asarray(z['cc_lat'],float)>0.5
    v=np.abs(np.asarray(z['cs_v'],float))*3.6
    n=min(len(t),len(e),len(v)); t,e,v=t[:n],e[:n],v[:n]
    if n<500: continue
    fs=1.0/np.median(np.diff(t))
    if e.sum()/fs<MIN_S or (~e).sum()/fs<MIN_S: continue
    bins=np.floor(v/SPD_BIN).astype(int)
    sh=np.intersect1d(np.unique(bins[e]),np.unique(bins[~e]))
    if len(sh)==0: continue
    keep=np.isin(bins,sh)
    ke,km=(e&keep).sum()/fs,((~e)&keep).sum()/fs
    if ke<MIN_S or km<MIN_S: continue
    ok.append((b, ke, km, b in have))
    if b not in have:
        m=re.match(r'^r([0-9a-f]+)s?\d*$', b)
        if m: need[m.group(1)].append(b)
print('SEGMENTS THAT SURVIVE SPEED MATCHING: %d' % len(ok))
print('  with IMU already: %d   WITHOUT: %d' % (sum(1 for x in ok if x[3]), sum(1 for x in ok if not x[3])))
print()
print('  %-12s %8s %8s %6s' % ('segment','eng s','man s','imu?'))
for b,ke,km,h in sorted(ok, key=lambda x:-min(x[1],x[2]))[:22]:
    print('  %-12s %8.1f %8.1f %6s' % (b,ke,km,'yes' if h else 'NO'))
print()
print('  routes needing IMU extraction: %s' % ' '.join(sorted(need)))
