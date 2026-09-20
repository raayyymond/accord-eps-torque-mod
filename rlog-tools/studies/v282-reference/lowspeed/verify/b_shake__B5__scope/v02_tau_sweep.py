"""B5 SCOPE addendum: fine tau sweep (0-100ms, 10ms steps) for hyst below 8 m/s, pooled across
torque routes -- the original finding only sampled tau in {0,30,60} ms; check no untested lag hides
a strong feed for hyst (the term closest to plausibly zero in the original table)."""
import sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/b_shake')
import bs

OUTDIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/b_shake__B5__scope/'
TAUS = list(range(0, 11))  # samples, 0..100ms step 10ms

num = {t: 0.0 for t in TAUS}
den_total = 0.0

for rk, g in bs.TORQUE.items():
    D = bs.load_torque(rk)
    fin = np.isfinite(D['hyst']) & np.isfinite(D['sr']) & np.isfinite(D['v'])
    m = (D['usable'] > 0.5) & fin & (D['v'] < 8)
    for a, b in bs.V.runs(m, D['t'], min_s=4.0):
        Bh = bs.bp(D['hyst'][a:b])
        Bsr = bs.bp(D['sr'][a:b])
        n = b - a
        sel = np.arange(100, n - 100)
        if len(sel) < 200:
            continue
        for t in TAUS:
            idx = sel - t
            ok = (idx >= 0)
            num[t] += float(Bh[idx[ok]] @ Bsr[sel[ok]])
        den_total += float(Bsr[sel] @ Bsr[sel])
    del D

print('tau_ms  beq(x1e-4)')
for t in TAUS:
    beq = -1e4 * num[t] / max(den_total, 1e-9)
    print(f'{t*10:5d}   {beq:+.3f}')
