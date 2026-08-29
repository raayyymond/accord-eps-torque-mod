# -*- coding: utf-8 -*-
"""GATE 1 for V172: who reads gp-0x6b86, and does anything watch it for plausibility?

V172 low-passes the assist map's output hard -- 21 Hz down 9.6x, 40 Hz down 3.3x.  The
aggregator consuming it is fine with that (it is a torque contribution).  The risk is a
MONITOR: a stuck-signal, rate-of-change or plausibility check that expects the value to
move.  Heavily low-passing a signal a watchdog samples can look like a frozen sensor.

Raw LE byte scan across BOTH gp encodings, since operand-text search undercounts and cannot
see register-indirect access at all.  gp = 0xFEDF8000.
"""
import os, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
a=np.fromfile(os.path.join(R,'stock_fw_dump/code.bin'),dtype=np.uint8); n=len(a)
GP=4
TARGETS={-0x6b86:'gp-0x6b86 the assist map output',
         -0x4cde:'gp-0x4cde its LOCKSTEP SHADOW',
         -0x6b82:'gp-0x6b82 sibling', -0x6b84:'gp-0x6b84 sibling',
         -0x6b7a:'gp-0x6b7a pre-clamp', -0x69a4:'gp-0x69a4 map Y value'}
def hw(i): return int(a[i])|(int(a[i+1])<<8)
def sx(v): return v-0x10000 if v&0x8000 else v
OPS={0x38:'ld.b',0x39:'ld.h',0x3A:'ld.w',0x3B:'st.h/st.w',0x3C:'st.b',0x3D:'ld.hu?',0x3E:'?',0x3F:'?'}
hits={}
for i in range(0,n-6,2):
    h1=hw(i)
    if (h1&0x1F)!=GP: continue
    t6=(h1>>5)&0x3F
    if t6 in OPS:
        d=sx(hw(i+2)&0xFFFE)
        if d in TARGETS:
            kind=OPS[t6]
            if t6==0x3B: kind = 'st.h' if (hw(i+2)&1)==0 else 'st.w'
            src=(h1>>11)&0x1F
            hits.setdefault(d,[]).append((i,kind,src))
    d2=(sx(hw(i+2))<<7)|((h1>>4)&0x7F)
    if d2 in TARGETS:
        hits.setdefault(d2,[]).append((i,'ext6(op=%03X)'%((h1>>5)&0x7FF),-1))
for d,name in TARGETS.items():
    hs=hits.get(d,[])
    print('%-34s %d access(es)' % (name, len(hs)))
    for addr,kind,src in sorted(hs)[:12]:
        s = '' if src<0 else ('  src r%d%s'%(src,' (STORE-ZERO)' if src==0 and kind.startswith('st') else ''))
        print('      0x%05X  %-14s%s' % (addr,kind,s))
    print()
