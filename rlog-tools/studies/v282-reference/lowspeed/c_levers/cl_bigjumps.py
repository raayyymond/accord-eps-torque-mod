"""List the large (>= 3 deg) dwell-jumps below 15 m/s on the usable mask, with the distance to the nearest steeringPressed
frame, the driver column torque, and the term levels/builds -- to see what the p90 tail of the stick-slip is made of."""
import sys, json, gc
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import cl_recon as C
import cl_reach as RCH
RCH.MODE = 'us'; RCH.VB[:] = [0.3, 2.5, 5.0, 8.0, 15.0]
rows = []
for rk in C.CFG:
    D = C.reconstruct(rk)
    DW, _, _, _ = RCH.analyse(D)
    pr = np.where(D['pressed'])[0]
    for d in DW:
        if d['jump'] < 3.0:
            continue
        gj = int(np.argmin(np.abs(D['v'] - d['v']) + 0))  # placeholder, replaced below
    # recompute end index: match by v and levels is fragile -> redo detection positions here
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & ~D['pressed'] & (v >= 0.3) & (v < 15)
    for a, b in C.V.runs(HO, t, min_s=2.0):
        m_ = b - a; rsm = RCH.smooth(np.abs(D['sr'][a:b]), 10); low = rsm < 0.75; aa = D['sa'][a:b]; i = 0
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            if j - i + 1 >= 12 and i - 50 >= 0 and j + 50 < m_:
                pre = aa[i] - aa[i - 50]; post = aa[j + 50] - aa[j]
                if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                    jump = abs(aa[min(j + 30, m_ - 1)] - aa[j])
                    if jump >= 3.0:
                        g = a + j; s = np.sign(post)
                        dist = float(np.min(np.abs(pr - g)) / 100) if len(pr) else 99
                        rows.append(dict(g=D['g'], rk=rk[6:8], t=float(t[g] - t[0]), v=float(v[g]), jump=float(jump), ang=float(aa[j]),
                                         dwell=(j - i + 1) / 100, dist_pressed_s=dist,
                                         drv_tq_max=float(np.max(np.abs(D['storque'][a + i:a + j + 30]))),
                                         out=float(D['out'][g]), gate=float(np.clip(1 - abs(D['out'][g]) / 0.15, 0, 1)),
                                         err=float(s * (D['angle_des'][g] - D['sa'][g])), rate_des=float(s * D['rate_des'][g]),
                                         **{'b_' + x: float(s * (D[x][g] - D[x][a + i])) for x in ('P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob', 'out')}))
            i = j + 1
    del D; gc.collect()
json.dump(rows, open(C.OUT / 'bigjumps.json', 'w'), indent=1)
for r in rows:
    print(f"{r['g']:5s} r{r['rk']} t{r['t']:7.1f} v{r['v']:5.1f} jump {r['jump']:5.1f} ang {r['ang']:+7.1f} dwell {r['dwell']:.2f} "
          f"pressed@{r['dist_pressed_s']:5.2f}s drvTq {r['drv_tq_max']:5.0f} out {r['out']:+.3f} gate {r['gate']:.2f} err {r['err']:+5.1f} rdes {r['rate_des']:+6.1f} "
          f"build out {r['b_out']:+.3f} P {r['b_P']:+.3f} I {r['b_I']:+.3f} hold {r['b_hold']:+.3f} move {r['b_move']:+.3f} rate {r['b_rate_t']:+.3f} dob {r['b_dob']:+.3f}")
