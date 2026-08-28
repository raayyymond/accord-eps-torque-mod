# -*- coding: utf-8 -*-
"""Does a RATE-scheduled Kd cut get the 6-9 Hz benefit without the 16-35 Hz cost?

STATE-ARCHIVE-2026-08-11 measured Re(Z) to 35 Hz and found the D term PUMPS 2-12 Hz
and DAMPS 16-35 Hz. A FLAT Kd cut therefore trades: it removes a +0.077 pump at 6-9 Hz
but costs -0.217 at 18-22 and -0.336 at 26-31 -- the operator's own grinding bands.
That is 3-4x against, and it is why the Kd lever was refused.

But a RATE-SCHEDULED cut only acts where the motor rate is high. So the trade only
holds if the grinding bands live at the SAME rate as the oscillation. Measure it.
"""
import numpy as np, glob, os
from scipy import signal

FS, NW = 100.0, 256
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e', 'a4', 'a5', 'a6', '1e']
BANDS = {'6-9 Hz  (oscillation)': (6, 9), '18-22 Hz (grind)': (18, 22), '26-31 Hz (grind)': (26, 31)}


def wins(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    o = []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        x = rate[sl] - np.mean(rate[sl])
        f, P = signal.welch(x, FS, nperseg=NW, noverlap=NW // 2)
        row = [np.sqrt(np.sum(P[(f >= lo) & (f <= hi)]) * (f[1] - f[0])) for lo, hi in BANDS.values()]
        row.append(np.percentile(np.abs(rate[sl]), 95))
        o.append(row)
    return np.array(o) if o else None


A = np.vstack([w for w in (wins(r) for r in ROUTES) if w is not None])
pk = A[:, -1]
print("%d engaged windows.\n" % len(A))
print("Where does each band's ENERGY sit on the motor-rate axis a scheduled Kd cut would act on?")
print("(band energy share captured above a knot at T deg/s -- higher = more affected by the cut)\n")
print("   band                     %s" % ''.join('  T=%-5d' % T for T in (20, 40, 60, 100, 140)))
share = {}
for i, nm in enumerate(BANDS):
    e = A[:, i] ** 2                      # power
    row = [e[pk >= T].sum() / e.sum() * 100 for T in (20, 40, 60, 100, 140)]
    share[nm] = row
    print("   %-24s %s" % (nm, ''.join('  %5.1f %%' % x for x in row)))

print("\n   ⇒ SELECTIVITY of the cut = (share of 6-9 Hz captured) / (share of grind captured)")
print("      a value > 1 means the scheduled cut removes MORE pump than damping\n")
print("   knot T    vs 18-22 Hz    vs 26-31 Hz")
for j, T in enumerate((20, 40, 60, 100, 140)):
    o = share['6-9 Hz  (oscillation)'][j]
    g1 = share['18-22 Hz (grind)'][j]
    g2 = share['26-31 Hz (grind)'][j]
    print("   %6d       %6.2fx       %6.2fx" % (T, o / max(g1, 1e-9), o / max(g2, 1e-9)))

print("\n   The FLAT cut the archive scored was 3-4x AGAINST (benefit +0.077 at 6-9,")
print("   cost -0.217 at 18-22 and -0.336 at 26-31). A scheduled cut beats it only if")
print("   the selectivity above exceeds those ratios: 0.217/0.077 = %.2fx and 0.336/0.077 = %.2fx."
      % (0.217 / 0.077, 0.336 / 0.077))
