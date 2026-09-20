"""Independent re-derivation of C1 (observer reach into low-speed stick-slip), one route at a time.
Reuses the ALREADY-VALIDATED reconstruction (cl_recon.reconstruct, corr>0.999 vs logged pid.f) but defines
dwell/jump/overshoot/build-share with a fresh, independently-coded method rather than importing cl_dwellpost.

Method (deliberately different from cl_dwellpost.py in a few respects, to stress-test):
  - "hands-off dwell": |steering rate| smoothed(10) < 1.0 deg/s (vs original 0.75) for >= 0.15 s (vs 0.12 s)
  - "release" = first frame after the dwell where |rate| > 3 deg/s (a distinct rate-threshold escape test,
    rather than reusing the low-rate boolean's rising edge)
  - "jump" size = |angle(release+0.3s) - angle(dwell_end)|
  - "overshoot" = max(0, s*(sa - angle_des)) over release..release+1.0s  (wheel PAST demand, s = jump sign)
  - "build share" of the observer = |dob(release)-dob(dwell_start)| / sum_x |term_x(release)-term_x(dwell_start)|
    over the same 8 terms, at the release frame (a ratio-of-magnitudes definition, vs the original's raw build)
Runs T64 (6c), T64B (6e), and T4 (75) only (skip 6d/76 to keep this quick and RAM-light).
"""
import sys, json, gc
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CL = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/c_levers')
sys.path.insert(0, str(CL))
import cl_recon as C

TERMS = ['P', 'I', 'hold', 'move', 'z', 'rate_t', 'dob']


def smooth(x, n=10):
    return np.convolve(x, np.ones(n) / n, 'same')


def analyse_route(rk):
    D = C.reconstruct(rk)
    t, v = D['t'], D['v']
    HO = D['active'] & D['csact'] & (~np.convolve(D['pressed'].astype(float), np.ones(101), 'same').astype(bool)) & (v >= 2.5) & (v < 15)
    rows = []
    for a, b in C.V.runs(HO, t, min_s=2.0):
        m_ = b - a
        rsm = smooth(np.abs(D['sr'][a:b]), 10)
        low = rsm < 1.0
        aa = D['sa'][a:b]
        i = 0
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i
            while j + 1 < m_ and low[j + 1]:
                j += 1
            dwell_s = (j - i + 1) / 100.0
            if dwell_s >= 0.15 and i - 20 >= 0:
                # find release: first frame after j where |rate| > 3 deg/s, within 1s
                k = j + 1
                rel = None
                while k < min(m_, j + 100):
                    if abs(D['sr'][a + k]) > 3.0:
                        rel = k; break
                    k += 1
                if rel is not None and rel + 100 < m_ and rel + 30 < m_:
                    jump = aa[min(rel + 30, m_ - 1)] - aa[rel]
                    if abs(jump) >= 0.5:
                        s = np.sign(jump)
                        gi, gr = a + i, a + rel
                        win = slice(gr, min(gr + 101, n_global))
                        err = s * (D['angle_des'][gr:gr + 101] - D['sa'][gr:gr + 101])
                        over = max(0.0, float(-err.min()))
                        builds = {x: abs(D[x][gr] - D[x][gi]) for x in TERMS}
                        tot = sum(builds.values()) + 1e-9
                        rows.append(dict(v=float(v[gr]), jump=float(abs(jump)), over=float(over),
                                          dob_share=float(builds['dob'] / tot),
                                          dob_build=float(s * (D['dob'][gr] - D['dob'][gi]))))
            i = j + 1
    del D; gc.collect()
    return rows


if __name__ == '__main__':
    n_global = 10 ** 9  # unused guard, angle_des/sa indexed safely within run bounds already
    ALL = {}
    for rk in ['0000006c--68c6e94b17', '0000006e--6ca3e014fd', '00000075--6c8687d5bd']:
        rows = analyse_route(rk)
        ALL[rk] = rows
        R6_15 = [r for r in rows if 6.0 <= r['v'] < 15.0]
        R6_8 = [r for r in rows if 6.0 <= r['v'] < 8.0]
        print(rk, 'n_total', len(rows), 'n(6-15)', len(R6_15), 'n(6-8)', len(R6_8))
        for lbl, R in [('6-15', R6_15), ('6-8', R6_8)]:
            if len(R) < 5:
                print('  ', lbl, 'too few', len(R)); continue
            ov1 = np.mean([r['over'] > 1.0 for r in R])
            print(f"   {lbl}: n={len(R)} overshoot>1deg={ov1:.2f} over_p50={np.median([r['over'] for r in R]):.2f} "
                  f"dob_share_p50={np.median([r['dob_share'] for r in R]):.2f} dob_build_p50={np.median([r['dob_build'] for r in R]):+.4f}")
        json.dump(rows, open(HERE / f'{rk}_rows.json', 'w'))
