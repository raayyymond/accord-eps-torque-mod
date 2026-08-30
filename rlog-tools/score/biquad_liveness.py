# -*- coding: utf-8 -*-
"""IS THE BIQUAD LIVE ON THE CAR? The test that should have run before 56 notch builds.

The biquad is gated on the LKAS engagement flag (V103 repointed its arm source there), so it runs
ENGAGED-ONLY. And it was DORMANT before V103. That gives a difference-in-differences with each route as
its own control:

    per route:  R = (engaged 50-60 Hz audio) / (not-engaged 50-60 Hz audio)
    ARMED routes should have LOWER R than DORMANT ones -- Honda's notch cuts 159x at 55 Hz.

    ARMED   r9e (V103), ra4 (V104), r24 (V122)
    DORMANT r95 (V101), r96 (V102)

Speed AND gear matched inside each route, as everywhere else. Neighbouring bands act as controls: the
notch is narrow, so 15-22 Hz and 85-99 Hz should show NO arm difference.

POWER, STATED FIRST: 3 routes vs 2. The kit's own placebo floor -- two byte-identical builds on
different drives -- is 1.45x. Nothing below that is interpretable, and with 5 routes no CI will be
tight. This can only produce a strong NULL or a large signal; it cannot resolve a small one.
"""
import glob, os, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
RNG = np.random.default_rng(20260830)
ARMED = {'r9e':'V103','ra4':'V104','r24':'V122'}
DORM  = {'r95':'V101','r96':'V102'}
VB = np.arange(0, 36, 2.0)
BANDS = [(6,9),(9,12),(15,22),(22,30),(30,40),(40,50),(50,60),(60,72),(72,85),(85,99)]

def ratio(tag):
    ap='analysis-2020accord/_scratch/cache/%s/%s_grind.npz'%(tag,tag)
    cp='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not (os.path.exists(ap) and os.path.exists(cp)): return None,None
    g=np.load(ap,allow_pickle=True); c=np.load(cp,allow_pickle=True)
    if not {'cc_lat','cs_v','cs_gear','t'} <= set(c.files): return None,None
    f=np.asarray(g['sp_f']).astype(float); sp=np.asarray(g['sp']).astype(float)
    ts=np.asarray(g['t_sp']).astype(float); tc=np.asarray(c['t']).astype(float)
    eng=np.interp(ts,tc,(np.asarray(c['cc_lat']).astype(float)>0.5).astype(float))
    v=np.interp(ts,tc,np.abs(np.asarray(c['cs_v']).astype(float)))
    gr=np.round(np.interp(ts,tc,np.asarray(c['cs_gear']).astype(float)))
    A=(eng>0.95)&(v>0.3); B=(eng<0.05)&(v>0.3)
    num=np.zeros(len(f)); w=0.0
    for lo in VB:
        for gg in np.unique(gr[np.isfinite(gr)]):
            a=A&(v>=lo)&(v<lo+2)&(gr==gg); b=B&(v>=lo)&(v<lo+2)&(gr==gg)
            if a.sum()<10 or b.sum()<10: continue
            ww=float(min(a.sum(),b.sum()))
            num+=ww*np.log10(np.maximum(sp[a].mean(axis=0),1e-30)/np.maximum(sp[b].mean(axis=0),1e-30))
            w+=ww
    return (num/w, f) if w>=30 else (None,None)

print('='*98)
print('  IS THE BIQUAD LIVE? engaged/not audio ratio, ARMED vs DORMANT routes')
print('='*98)
print()
print('  POWER FIRST: 3 armed vs 2 dormant routes. The kit placebo floor (byte-identical builds,')
print('  different drives) is 1.45x. Only a strong null or a large signal is readable here.')
print()
rows={}
F=None
for grp,d in (('ARMED',ARMED),('DORMANT',DORM)):
    for tag,bld in sorted(d.items()):
        r,f=ratio(tag)
        if r is None:
            print('  %-8s %-5s (%s)  no matched cells'%(grp,tag,bld)); continue
        F=f; rows.setdefault(grp,[]).append((tag,bld,r))
        print('  %-8s %-5s (%s)  ok'%(grp,tag,bld))
if 'ARMED' not in rows or 'DORMANT' not in rows:
    print('\n  cannot form both arms.'); raise SystemExit
A=np.vstack([r for _,_,r in rows['ARMED']]); D=np.vstack([r for _,_,r in rows['DORMANT']])
print()
print('  %-12s %14s %14s %12s  %s' % ('band (Hz)','ARMED e/n','DORMANT e/n','armed/dorm','reading'))
for lo,hi in BANDS:
    b=(F>=lo)&(F<hi)
    if not b.any(): continue
    a=10**np.median(A[:,b].mean(axis=1)); d=10**np.median(D[:,b].mean(axis=1))
    rr=a/d
    note=''
    if (lo,hi)==(50,60): note='  <== THE NOTCH SITS HERE (Honda cuts 159x)'
    elif (lo,hi) in ((15,22),(85,99)): note='  (control band -- notch is narrow)'
    print('  %-12s %13.2fx %13.2fx %11.2fx%s' % ('%d-%d'%(lo,hi),a,d,rr,note))
print()
b=(F>=50)&(F<60)
pa=A[:,b].mean(axis=1); pd_=D[:,b].mean(axis=1)
obs=10**(np.median(pa)-np.median(pd_))
print('  50-60 Hz, ARMED/DORMANT = %.2fx' % obs)
print('  per-route engaged/not at 50-60 Hz:')
for grp,M in (('ARMED',rows['ARMED']),('DORMANT',rows['DORMANT'])):
    for (tag,bld,r) in M:
        print('    %-8s %-5s (%s)  %6.2fx' % (grp,tag,bld,10**r[b].mean()))
print()
print('  EXPECTED IF THE BIQUAD IS LIVE: armed/dormant well BELOW 1.0 at 50-60 Hz, and ~1.0 in the')
print('  control bands. A ratio near 1.0 at 50-60 Hz says arming a 159x notch changed nothing there.')
