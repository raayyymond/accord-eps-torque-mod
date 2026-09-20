"""Per dwell-jump (usable mask, 2.5-15 m/s): what each term does during the dwell AND after release -- overshoot past the
demand, the observer's hang-over, and which term's build tracks the jump size (Spearman over events).  T4 (no observer,
Kv 0.0006, Ki 0.6) is the in-kind control for the observer's role."""
import sys, json, gc
from pathlib import Path
import numpy as np
from scipy import stats
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import cl_recon as C
import cl_reach as RCH
TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob', 'out']
rows = []
for rk in C.CFG:
    D = C.reconstruct(rk)
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & ~D['pressed'] & (v >= 2.5) & (v < 15)
    for a, b in C.V.runs(HO, t, min_s=2.0):
        m_ = b - a; rsm = RCH.smooth(np.abs(D['sr'][a:b]), 10); low = rsm < 0.75; aa = D['sa'][a:b]; i = 0
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            if j - i + 1 >= 12 and i - 50 >= 0 and j + 100 < m_:
                pre = aa[i] - aa[i - 50]; post = aa[j + 50] - aa[j]
                if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                    s = np.sign(post); gi, g = a + i, a + j
                    e = s * (D['angle_des'][g:g + 101] - D['sa'][g:g + 101])       # + = wheel behind demand
                    r = dict(g=D['g'], v=float(v[g]), jump=float(abs(aa[j + 30] - aa[j])), dwell=(j - i + 1) / 100,
                             ang=float(abs(aa[j])), err0=float(e[0]), over=float(max(0.0, -e.min())), err60=float(e[60]),
                             dem_rate=float(np.mean(np.abs(D['rate_des'][gi:g + 1]))))
                    for x in TERMS:
                        r['b_' + x] = float(s * (D[x][g] - D[x][gi]))
                        r['post_' + x] = float(s * (D[x][g + 30] - D[x][g]))    # change over the jump itself
                        r['hang_' + x] = float(s * (D[x][g + 60]))               # level 0.6 s after release
                    rows.append(r)
            i = j + 1
    del D; gc.collect()
json.dump(rows, open(C.OUT / 'dwellpost.json', 'w'))
for g in ['T64', 'T64B', 'T5', 'T4']:
    for lo, hi in ((2.5, 6.0), (6.0, 8.0), (8.0, 15.0)):
        R = [r for r in rows if r['g'] == g and lo <= r['v'] < hi]
        if len(R) < 6:
            print(g, lo, hi, 'n', len(R)); continue
        J = np.array([r['jump'] for r in R])
        cor = {x: stats.spearmanr(J, [r['b_' + x] for r in R])[0] for x in TERMS}
        print(f"{g} {lo}-{hi} n={len(R)} jump p50 {np.median(J):.2f} p90 {np.percentile(J,90):.2f}  err_at_release p50 {np.median([r['err0'] for r in R]):+.2f} "
              f"overshoot p50 {np.median([r['over'] for r in R]):.2f} p90 {np.percentile([r['over'] for r in R],90):.2f} deg  over>1deg {np.mean([r['over']>1 for r in R]):.0%}")
        print('    spearman(jump, build): ' + ' '.join(f"{x} {cor[x]:+.2f}" for x in TERMS))
        print('    change over the jump (0-0.3 s) p50: ' + ' '.join(f"{x} {np.median([r['post_'+x] for r in R]):+.4f}" for x in TERMS))
        big = [r for r in R if r['jump'] >= 3]
        if big:
            print(f'    jump>=3 (n={len(big)}): over p50 {np.median([r["over"] for r in big]):.2f}  build ' + ' '.join(f"{x} {np.median([r['b_'+x] for r in big]):+.4f}" for x in TERMS)
                  + ' | over-the-jump ' + ' '.join(f"{x} {np.median([r['post_'+x] for r in big]):+.4f}" for x in ('P', 'dob', 'rate_t', 'move', 'hold')))
