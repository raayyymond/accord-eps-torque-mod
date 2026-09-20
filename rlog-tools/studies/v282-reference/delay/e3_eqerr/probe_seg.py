import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/lib")
from rlog_parse import read_messages
p = sys.argv[1]
from collections import Counter
addr = Counter(); n=0; order=[]
for evt in read_messages(p):
    try:
        w = evt.which()
    except Exception:
        continue
    t = evt.logMonoTime
    if w in ('carState','carControl','sendcan','controlsState'):
        if len(order) < 60 and n>3000: order.append((w, t))
    if w == 'can':
        for m in evt.can:
            if m.address in (0xE4, 0x14A, 0x156, 0x18F): addr[(m.address, m.src)] += 1
        if len(order) < 60 and n>3000: order.append(('can', t, [ (hex(m.address), m.src) for m in evt.can if m.address in (0xE4,0x14A,0x156,0x18F)]))
    if w == 'sendcan':
        for m in evt.sendcan:
            addr[('send', m.address, m.src)] += 1
    n += 1
print(addr)
t0 = order[0][1]
for o in order: print(o[0], (o[1]-t0)/1e6, o[2] if len(o)>2 else '')
