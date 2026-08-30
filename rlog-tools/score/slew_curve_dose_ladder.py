import sys, os, glob
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import clip_duty_and_v238_dose as C
import slope_cap_band_size as S
import numpy as np, assist_map_mirror as AM
from assist_map_mirror import u16, TP, _lerp_u16

CX=[u16(TP+0x7936+2*i) for i in range(4)]; CY=[u16(TP+0x793E+2*i) for i in range(4)]
def mk(scale):
    Y=[min(4096,int(y*scale)) for y in CY]
    return (lambda sc: min(4096, _lerp_u16(int(sc), CX, Y))), Y

caches=[]
for c in sorted(glob.glob('_scratch/cache/*/*.npz')):
    try: z=np.load(c, allow_pickle=True)
    except Exception: continue
    if not all(k in z.files for k in C.REQUIRED) or 't' not in z.files: continue
    e=np.asarray(z['cc_lat'],float)>0.5
    if e.sum() < 1500: continue
    caches.append(c)
    if len(caches)>=14: break

print('LOOSENING gp-0x69a0 -- removing the relay. Curve C Y = %s\n' % CY)
print('  %8s %10s %10s %11s %11s %11s' % ('scale','Y[0]','gate%','band 6-9','assist p50','assist p95'))
print('  '+'-'*66)
base={}
for scale in (1.0, 0.85, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2):
    fn, Y = mk(scale)
    C.g69a0_of = fn; S.g69a0_of = fn
    g,b,a50,a95 = [],[],[],[]
    for c in caches:
        z=np.load(c, allow_pickle=True); t=np.asarray(z['t'],float); fs=1.0/np.median(np.diff(t))
        b82,b84,e = S.lane_series(z, 2048); AM.CAL_7384=2048
        if c not in base:
            base[c]=(S.band_power(b82[e],b84[e],fs,20), np.percentile(np.abs(b82[e]),50),
                     np.percentile(np.abs(b82[e]),95))
        b0,m50,m95 = base[c]
        g.append(100.0*(b84[e]!=0).mean())
        bp=S.band_power(b82[e],b84[e],fs,20)
        if b0>0: b.append(bp/b0)
        if m50>0: a50.append(np.percentile(np.abs(b82[e]),50)/m50)
        if m95>0: a95.append(np.percentile(np.abs(b82[e]),95)/m95)
    print('  %8.1f %10d %9.2f%% %11.4f %11.4f %11.4f'
          % (scale, Y[0], np.median(g), np.median(b), np.median(a50), np.median(a95)))
print()
print('  band < 1  = less lane gain at the ratchet.  assist < 1 = LESS assist = more effort.')
print('  scale 11.5 puts Y[0] at 4096, the LERP_A clamp -- the relay is fully gone.')
