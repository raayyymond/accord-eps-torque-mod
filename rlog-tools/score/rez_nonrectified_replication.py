#!/usr/bin/env python3
r"""Re(Z) AT THE RATCHET, ON NON-RECTIFIED INSTRUMENTS ONLY -- an independent replication.

WHY.  The claim "gp-0x6b86 damps at 6-9 Hz" (cos -0.918/-0.989/-0.629) is load-bearing: it condemns
V238 and V240 and it underwrites "the one band worth filtering is the one band that must not be
filtered".  But that phase was measured on CAN 427, and FUN_00055d80 rectifies 427, which DESTROYS
phase at f0.  So the sign needed an instrument that never passes through that clamp.

`tq` (torque sensor) and `cs_rate` (steering rate) are both such instruments.

    Z(f) = CSD(rate, tq) / PSD(rate)
    Re(Z) > 0 = DAMPING       (torque opposes motion)
    Re(Z) < 0 = ANTI-DAMPING  (torque feeds motion)

RESULT -- unanimous, and band-specific:

    ENGAGED  Re(Z) at 6-9 Hz: median -58.20   negative on 31 of 31 routes
    MANUAL   Re(Z) at 6-9 Hz: median  -0.81   negative on 13 of 25 (a coin flip)
    ENGAGED MINUS MANUAL:     median -56.38   more negative on 25 of 25, Wilcoxon p = 0.0000
    control band 22-30 Hz engaged: POSITIVE (+8 to +17) on nearly every route

Engagement injects anti-damping at 6-9 Hz while the 22-30 Hz control stays POSITIVE.  Band-specific,
so not a sign error or a broadband artefact.

🛑 WHAT THIS IS AND IS NOT.  It REPLICATES the record's own "the 6-9 Hz anti-damping is HONDA'S;
at 22-26 Hz we REVERSE the sign", now on instruments immune to the rectification doubt.  It does NOT
overturn "every tapped lane damps at 6-9 Hz", and it does NOT license a 6-10 Hz notch: system-level
Re(Z) and per-lane phase are DIFFERENT OBJECTS.  The record already holds both, and their coexistence
is exactly what forces the source to be NONLINEAR -- the command-proportional Coulomb relay -- since no
combination of damping linear lanes can produce an anti-damped system.

CAVEAT: the manual arm's coherence is LOW (0.06-0.23) against the engaged arm's 0.4-0.9, so the paired
contrast is carried by the engaged side.  Not speed-matched.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import numpy as np, glob, os, sys, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from scipy import signal
BAND=(6.0,9.5); CTL=(22.0,30.0); COH=0.20
print('='*90)
print('  DAMPS OR PUMPS AT THE RATCHET -- measured on NON-RECTIFIED instruments only')
print('='*90)
print('\n  Z(f) = CSD(rate,tq)/PSD(rate).  Re(Z) > 0 = DAMPING (torque opposes motion)')
print('                                  Re(Z) < 0 = ANTI-DAMPING (torque feeds motion)')
print('  tq = torque sensor, cs_rate = steering rate. NEITHER passes through FUN_00055d80,')
print('  so unlike the 427 phase this sign is actually measured.\n')
def rez(t,r,q,m,fs):
    if m.sum()<3000: return None
    r=r[m]-r[m].mean(); q=q[m]-q[m].mean()
    if r.std()<1e-9 or q.std()<1e-9: return None
    f,P=signal.welch(r,fs,nperseg=1024)
    _,C=signal.csd(r,q,fs,nperseg=1024)
    _,co=signal.coherence(r,q,fs,nperseg=1024)
    Z=C/np.maximum(P,1e-30)
    b=(f>=BAND[0])&(f<=BAND[1])&(co>=COH)
    c=(f>=CTL[0])&(f<=CTL[1])&(co>=COH)
    if b.sum()<2: return None
    return (float(np.median(Z.real[b])), float(np.median(co[(f>=BAND[0])&(f<=BAND[1])])),
            float(np.median(Z.real[c])) if c.sum()>=2 else float('nan'))
print('  %-7s %9s %11s %9s %11s %9s' % ('route','ENG Re(Z)','ENG coh','MAN Re(Z)','MAN coh','22-30 eng'))
print('  '+'-'*64)
rows=[]
seen=set()
for p in sorted(glob.glob('_scratch/cache/*/*.npz'))+sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    r=os.path.basename(p)[:-4]
    if r in seen or 's' in r[1:]: continue
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if not {'t','tq','cs_rate','cc_lat'} <= set(z.files): continue
    seen.add(r)
    t=np.asarray(z['t'],float); n=len(t)
    q=np.asarray(z['tq'],float)[:n]; ra=np.asarray(z['cs_rate'],float)[:n]
    e=(np.asarray(z['cc_lat'],float)>0.5)[:n]
    if len(q)<n or len(ra)<n: continue
    fs=1/np.median(np.diff(t))
    a=rez(t,ra,q,e,fs); b=rez(t,ra,q,~e,fs)
    if a is None: continue
    rows.append((r,a,b))
    print('  %-7s %9.2f %11.3f %9s %11s %9.2f' % (r,a[0],a[1],
        ('%.2f'%b[0]) if b else '--',('%.3f'%b[1]) if b else '--',a[2]))
print('  '+'-'*64)
if rows:
    ev=[a[0] for _,a,_ in rows]; mv=[b[0] for _,_,b in rows if b]
    print('\n  ENGAGED  Re(Z) at 6-9 Hz: median %+.2f   negative on %d of %d routes'
          %(np.median(ev),sum(1 for v in ev if v<0),len(ev)))
    if mv:
        print('  MANUAL   Re(Z) at 6-9 Hz: median %+.2f   negative on %d of %d routes'
              %(np.median(mv),sum(1 for v in mv if v<0),len(mv)))
        pair=[(a[0],b[0]) for _,a,b in rows if b]
        d=[x-y for x,y in pair]
        print('  ENGAGED MINUS MANUAL:     median %+.2f   more negative on %d of %d routes'
              %(np.median(d),sum(1 for v in d if v<0),len(d)))
        from scipy import stats
        try:
            w=stats.wilcoxon([x-y for x,y in pair])
            print('  Wilcoxon signed-rank on the paired difference: p = %.4f'%w.pvalue)
        except Exception as ex: print('  (wilcoxon skipped: %s)'%ex)
    print('\n  READING: Re(Z)<0 engaged AND more negative than manual => ENGAGEMENT ADDS')
    print('  ANTI-DAMPING at the ratchet, on instruments 427 rectification cannot touch.')
    print('  [!] This REPLICATES the known system-level result. It does NOT overturn the')
    print('      per-lane claim that every tapped lane damps at 6-9 Hz, and does NOT license')
    print('      a 6-10 Hz notch: system Re(Z) and per-lane phase are DIFFERENT OBJECTS.')
    print('      Their coexistence is what forces the source to be NONLINEAR -- no set of')
    print('      damping linear lanes gives an anti-damped system. That points at the')
    print('      command-proportional Coulomb relay.')
