# adv2b_pgain.py -- |P/x| and |T/x| vs frequency by time-domain sinusoid march on the adversary mirror, small signal
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_mirror as AM
c294 = AM.load_cells(); c964 = dict(c294, b=964)
for A in (50, 200, 1000):
    for f in (2.5, 10, 20, 25):
        row = []
        for c in (c294, c964):
            L = AM.Lane(c); ps = []; ts = []; xs = []
            n = int(4000 + 4 * 1000 / f)
            for k in range(n):
                xv = int(round(A * math.sin(2 * math.pi * f * k / 1000)))
                t = L.tick(xv, 0, 60)
                if k >= n - int(round(20 * 1000 / f)) * 1:
                    pass
                if k >= 4000:
                    ps.append(L.P); ts.append(t); xs.append(xv)
            ps, ts, xs = (np.array(v, float) for v in (ps, ts, xs))
            ph = np.exp(-2j * math.pi * f * np.arange(len(ps)) / 1000)
            row.append((abs(np.sum(ps * ph)) / abs(np.sum(xs * ph)), abs(np.sum(ts * ph)) / abs(np.sum(xs * ph))))
        print("A %4d x-counts (%.0f deg/s) f %5.1f Hz: |P/x| b567 %.3f b964 %.3f ratio %.3f | |T/x| b567 %.4f b964 %.4f ratio %.3f"
              % (A, A / 8, f, row[0][0], row[1][0], row[1][0] / row[0][0], row[0][1], row[1][1], row[1][1] / row[0][1]))
