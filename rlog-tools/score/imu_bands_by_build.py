import sys, os, importlib
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import ratchet_in_the_imu_pooled as P
BUILD = {"r5e":"V75","r61":"V74","r65":"V76","r66":"V80","r67":"V81","r68":"V83a",
         "r6d":"V84","r6e":"V85","r6f":"V86","r70":"V86B","r71":"V87","r73":"V88",
         "r75":"V89","r76":"V89"}
BANDS = {'ratchet 6.5-9.5':(6.5,9.5), 'grind 15-22':(15.0,22.0), 'mid 9.5-15':(9.5,15.0)}
out={}
for name,(lo,hi) in BANDS.items():
    P.F0_SEARCH=(lo,hi)
    importlib.reload  # no-op; F0_SEARCH is read at call time
    rows=P.collect()
    out[name]={r[0]:(r[5],r[6],r[7],r[2],r[3]) for r in rows}
routes=sorted(set().union(*[set(v) for v in out.values()]))
print('IMU BY BAND AND BUILD  (gyro excess / road control, speed-matched)\n')
hdr='  %-6s %-6s %7s %7s' % ('build','route','eng s','man s')
for n in BANDS: hdr += ' %16s' % n
print(hdr); print('  '+'-'*(len(hdr)-2))
rowsout=[]
for rt in routes:
    b=BUILD.get(rt,'?')
    any_=next((out[n][rt] for n in BANDS if rt in out[n]), None)
    if any_ is None: continue
    line='  %-6s %-6s %7.1f %7.1f' % (b, rt, any_[3], any_[4])
    vals={}
    for n in BANDS:
        v=out[n].get(rt)
        line += ' %16.3f' % (v[2] if v else float('nan'))
        vals[n]=v[2] if v else np.nan
    print(line); rowsout.append((b,rt,vals))
print('  '+'-'*(len(hdr)-2))
line='  %-6s %-6s %7s %7s' % ('MEDIAN','','','')
for n in BANDS:
    v=np.array([r[2][n] for r in rowsout],float)
    line += ' %16.3f' % np.nanmedian(v)
print(line)
print()
print('V88 is the kit\'s ONE measured grinding fix. If the grinding metric is real,')
print('V88 should sit LOW in the grind column and not in the ratchet column.')
for b,rt,vals in rowsout:
    if b=='V88':
        for n in BANDS:
            arr=np.array([r[2][n] for r in rowsout if r[0]!='V88'],float)
            pct=100.0*np.nanmean(arr<vals[n])
            print('   V88 %-16s %.3f   -> %.0f%% of other builds are BELOW it' % (n, vals[n], pct))
