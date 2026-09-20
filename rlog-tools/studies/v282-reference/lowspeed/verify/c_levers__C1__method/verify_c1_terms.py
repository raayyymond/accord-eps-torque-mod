"""Which term is really the largest builder of release torque, faithful-method dwells, T64 6-15 m/s only (RAM: 1 route)."""
import sys, gc
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CL = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/c_levers')
sys.path.insert(0, str(CL))
import cl_recon as C
TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob']


def smooth(x, n=10):
    return np.convolve(x, np.ones(n) / n, 'same')


def analyse(rk):
    D = C.reconstruct(rk)
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & ~D['pressed'] & (v >= 2.5) & (v < 15)
    rows = []
    for a, b in C.V.runs(HO, t, min_s=2.0):
        m_ = b - a
        rsm = smooth(np.abs(D['sr'][a:b]), 10)
        low = rsm < 0.75
        aa = D['sa'][a:b]
        i = 0
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            if j - i + 1 >= 12 and i - 50 >= 0 and j + 100 < m_:
                pre = aa[i] - aa[i - 50]; post = aa[j + 50] - aa[j]
                if abs(pre) >= 0.5 and abs(post) >= 0.5 and np.sign(pre) == np.sign(post):
                    s = np.sign(post); g = a + j; gi = a + i
                    r = dict(v=float(v[g]))
                    for x in TERMS:
                        r['b_' + x] = float(s * (D[x][g] - D[x][gi]))
                    rows.append(r)
            i = j + 1
    del D; gc.collect()
    return rows


rows = analyse('0000006c--68c6e94b17')
R = [r for r in rows if 6.0 <= r['v'] < 15.0]
print('n', len(R))
for x in TERMS:
    vals = np.array([r['b_' + x] for r in R])
    print(f"{x:8s} median(build) {np.median(vals):+.4f}  median(|build|) {np.median(np.abs(vals)):.4f}  frac largest-magnitude "
          f"{np.mean([abs(r['b_'+x]) == max(abs(r['b_'+y]) for y in TERMS) for r in R]):.2f}")
