import numpy as np, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SPD_BIN=5.0; MIN_S=20.0
tot=both=matched=0; fr=[]
for c in sorted(glob.glob('_scratch/cache/*/*.npz')):
    b=os.path.basename(c)
    if b.endswith('_imu.npz') or '_' in b.replace('.npz',''): continue
    try: z=np.load(c,allow_pickle=True)
    except Exception: continue
    if not {'cc_lat','cs_v','t'} <= set(z.files): continue
    t=np.asarray(z['t'],float); e=np.asarray(z['cc_lat'],float)>0.5
    v=np.abs(np.asarray(z['cs_v'],float))*3.6
    n=min(len(t),len(e),len(v)); t,e,v=t[:n],e[:n],v[:n]
    if n<500: continue
    fs=1.0/np.median(np.diff(t)); tot+=1
    if e.sum()/fs<MIN_S or (~e).sum()/fs<MIN_S: continue
    both+=1
    bins=np.floor(v/SPD_BIN).astype(int)
    sh=np.intersect1d(np.unique(bins[e]),np.unique(bins[~e]))
    if len(sh)==0: fr.append(0.0); continue
    keep=np.isin(bins,sh)
    ke,km=(e&keep).sum()/fs,((~e)&keep).sum()/fs
    fr.append(min(ke,km)/max(min(e.sum()/fs,(~e).sum()/fs),1e-9))
    if ke>=MIN_S and km>=MIN_S: matched+=1
fr=np.array(fr)
print('ENGAGED/MANUAL SPEED OVERLAP ACROSS THE CORPUS  (bin %.0f km/h, need %.0f s per arm)\n' % (SPD_BIN,MIN_S))
print('  route caches inspected                    %4d' % tot)
print('  with >=%.0f s in BOTH arms                   %4d' % (MIN_S, both))
print('  ...that SURVIVE speed matching            %4d   (%.0f %%)' % (matched, 100.0*matched/max(both,1)))
if len(fr):
    print()
    print('  fraction of the smaller arm that is speed-matched:')
    print('    p10 %.2f   p50 %.2f   p90 %.2f   zero-overlap segments: %d' %
          (np.percentile(fr,10), np.median(fr), np.percentile(fr,90), int((fr==0).sum())))
print()
print('  \U0001f6d1 every engaged-vs-manual claim in the record rests on arms that mostly do NOT')
print('     overlap in speed. The operator engages LKAS where he does not drive manually.')
