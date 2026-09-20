"""Faithful (but independently re-typed, not imported) reimplementation of cl_dwellpost.py's dwell/release/overshoot
definition, to check whether the ORIGINAL reported numbers (overshoot>1deg 0.57 T64 vs 0.18 T4, 6-15 m/s) reproduce
from the validated reconstruction, i.e. rule out a bug in cl_dwellpost.py itself (separate from the method-choice
sensitivity test in verify_c1.py, which used deliberately different thresholds and found a much weaker pattern)."""
import sys, json, gc
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CL = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/c_levers')
sys.path.insert(0, str(CL))
import cl_recon as C


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
                    s = np.sign(post); g = a + j
                    e = s * (D['angle_des'][g:g + 101] - D['sa'][g:g + 101])
                    over = float(max(0.0, -e.min()))
                    rows.append(dict(v=float(v[g]), over=over, jump=float(abs(aa[j + 30] - aa[j])),
                                      dob_build=float(s * (D['dob'][g] - D['dob'][a + i]))))
            i = j + 1
    del D; gc.collect()
    return rows


if __name__ == '__main__':
    for rk, tag in [('0000006c--68c6e94b17', 'T64-6c'), ('0000006d--05e83bb04f', 'T64-6d'),
                     ('0000006e--6ca3e014fd', 'T64B-6e'), ('00000076--d0b7ea7e4d', 'T5-76'),
                     ('00000075--6c8687d5bd', 'T4-75')]:
        rows = analyse(rk)
        for lo, hi, lbl in [(6.0, 15.0, '6-15'), (6.0, 8.0, '6-8')]:
            R = [r for r in rows if lo <= r['v'] < hi]
            if len(R) < 5:
                print(tag, lbl, 'n', len(R)); continue
            ov1 = np.mean([r['over'] > 1.0 for r in R])
            print(f"{tag:10s} {lbl:5s} n={len(R):3d} overshoot>1deg={ov1:.2f} over_p50={np.median([r['over'] for r in R]):.2f}")
        gc.collect()
