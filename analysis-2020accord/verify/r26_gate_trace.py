# -*- coding: utf-8 -*-
"""What writes gp-0x6b5e, the gate that admits r26 into the loop?

After V173 the assist map is ~54 % of |L| and the engagement-conditional terms are ~46 %.
The census lists r26 (gp-0x6adc) at 0.098-1.17 -- potentially the largest of those -- and
notes it is LIVE ONLY WHILE gp-0x6b5e == 0.  That is a GATE, not a gain, and a gate that
could be held closed would remove the whole term rather than scaling it.

0xC6444 (r26's magnitude) is already FALSIFIED on-car as V71c, but that was a MAGNITUDE cut
with the gate still open.  The gate itself has never been examined.

Raw LE byte scan, both gp encodings, since operand-text search undercounts.
"""
import os, sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
a=np.fromfile(os.path.join(R,'stock_fw_dump/code.bin'),dtype=np.uint8); n=len(a)
GP=4
TARGETS={-0x6b5e:'gp-0x6b5e  the r26 admission gate',
         -0x6adc:'gp-0x6adc  r26 lane mirror',
         -0x6ada:'gp-0x6ada  r24 lane mirror'}
def hw(i): return int(a[i])|(int(a[i+1])<<8)
def sx(v): return v-0x10000 if v&0x8000 else v
OPS={0x38:'ld.b',0x39:'ld.h',0x3A:'ld.w',0x3B:'st.h/st.w',0x3C:'st.b',0x3D:'ld.hu?'}
hits={}
for i in range(0,n-6,2):
    h1=hw(i)
    if (h1&0x1F)!=GP: continue
    t6=(h1>>5)&0x3F
    if t6 in OPS:
        d=sx(hw(i+2)&0xFFFE)
        if d in TARGETS:
            kind=OPS[t6]
            if t6==0x3B: kind='st.h' if (hw(i+2)&1)==0 else 'st.w'
            hits.setdefault(d,[]).append((i,kind,(h1>>11)&0x1F))
    d2=(sx(hw(i+2))<<7)|((h1>>4)&0x7F)
    if d2 in TARGETS:
        hits.setdefault(d2,[]).append((i,'ext6',-1))
for d,nm in TARGETS.items():
    hs=sorted(hits.get(d,[]))
    print('%-38s %d access(es)'%(nm,len(hs)))
    for addr,kind,src in hs[:14]:
        s='' if src<0 else '  src r%d%s'%(src,' (STORE-ZERO)' if src==0 and kind.startswith('st') else '')
        print('      0x%05X  %-10s%s'%(addr,kind,s))
    print()
