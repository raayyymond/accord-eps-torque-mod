# -*- coding: utf-8 -*-
# studies/grind/v289_marks_crux_psd.py -- the marks62 crux check for V289-MARKS-R62-R63-2026-09-09.md (independent of the
# per-bookmark code): pooled Welch PSD of the driver torque and the 0x18F wheel rate over every engaged run >= 4 s, per route,
# peak/floor at 13-17.5 / 18-22.5 / 22.5-25 Hz and the 13-17.5 : 18-22.5 band-power ratio.  Run: python v289_marks_crux_psd.py
# independent crux check (fast): pooled Welch PSD of driver torque (bar) and wheel rate over ENGAGED runs >= 4 s, per route.
import os, sys, numpy as np
from scipy import signal
sys.path.insert(0, '.')
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20
FS=100.0
rows=[]
for tag in ("r62_v289","r63_v289","r5e_v288","r39","r3a","r3c"):
    g=C20.load(tag); eng=g["eng"]
    acc={}; n=0
    for a,b in C20.runs(eng,400):
        for nm,x in (("bar",g["bar"][a:b]),("wire",g["wire"][a:b]/8.0)):
            f,P=signal.welch(x-x.mean(),fs=FS,nperseg=512,noverlap=384,nfft=2048)
            acc[nm]=acc.get(nm,0)+P*(b-a)
        n+=b-a
    for nm in acc: acc[nm]/=n
    def peak(P,lo,hi):
        m=(f>=lo)&(f<=hi); j=np.flatnonzero(m)[np.argmax(P[m])]; return f[j],P[j]
    out=[tag, eng.sum()/FS]
    for nm in ("bar","wire"):
        P=acc[nm]; fl=np.median(P[(f>=10)&(f<=30)])
        for lo,hi in ((13,17.5),(18,22.5),(22.5,25)):
            f0,p=peak(P,lo,hi); out+= [f0, p/fl]
        # band power ratio 13-17.5 / 18-22.5
        out.append(np.trapezoid(P[(f>=13)&(f<=17.5)],f[(f>=13)&(f<=17.5)])/np.trapezoid(P[(f>=18)&(f<=22.5)],f[(f>=18)&(f<=22.5)]))
    rows.append(out)
    print("%-9s engaged %5.0f s | BAR peak/floor 13-17.5: %.2f Hz x%.1f | 18-22.5: %.2f Hz x%.1f | 22.5-25: %.2f Hz x%.1f | power 13-17.5/18-22.5 %.2f || WIRE 13-17.5: %.2f Hz x%.1f | 18-22.5: %.2f Hz x%.1f | 22.5-25: %.2f Hz x%.1f | power ratio %.2f" % tuple(out), flush=True)
