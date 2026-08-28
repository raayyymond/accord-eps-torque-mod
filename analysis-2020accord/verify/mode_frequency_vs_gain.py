# -*- coding: utf-8 -*-
"""Is the 7.8 Hz mode a CLOSED-LOOP POLE or a FIXED MECHANICAL RESONANCE?

This decides what firmware can do about it:
  - a closed-loop pole MOVES when loop gain changes  => firmware can relocate it
  - a fixed mechanical resonance does NOT            => firmware can only DAMP it,
                                                        and the damping route is closed

Precedent inside this kit: the ~23 Hz line MOVED 20.3 -> 23.0 Hz across three 4x routes,
which is what established it as a pole. Apply the same test to the 7-9 Hz mode across
every build in the corpus, whose forward gain 0xC6CD0 spans 3564 / 5346 / 7128 and whose
relay knee spans 300 / 600 / 1800.

f0 is estimated per route as the median 6-9 Hz spectral peak over that route's own
oscillating windows, so exposure differences do not move it.
"""
import numpy as np, glob, os
from scipy import signal

FS, NW = 100.0, 512
FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
B = {'97': ('STOCK', None), '77': ('V90', '_v90_'), '78': ('V91', '_v91_'), '79': ('V92', '_v92_'),
     '7e': ('V96', '_v96_'), '7f': ('V96', '_v96_'), '85': ('V100', '_v100_'),
     '95': ('V101', '_v101_'), '96': ('V102', '_v102_'), '9e': ('V103', '_v103_'),
     'a4': ('V104', '_v104_'), 'a5': ('V105', '_v105_'), 'a6': ('V106', '_v106_'),
     '1e': ('V107', '_v107_'), '21': ('V111', '_v111_'), '22': ('V112', '_v112_'),
     '23': ('V112', '_v112_')}


def cal(tag, addr):
    if tag is None:
        d = open(glob.glob(FR + '/**/code.bin', recursive=True)[0], 'rb').read()
    else:
        g = [x for x in glob.glob(os.path.join(FR, tag + '*plain_image.bin')) if 'SUPERSEDED' not in x]
        if not g:
            return None
        d = open(g[0], 'rb').read()
    return int.from_bytes(d[addr:addr + 2], 'little')


def f0_of(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    P_, F_ = [], None
    for a in range(0, len(rate) - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        f, P = signal.welch(rate[a:b] - np.mean(rate[a:b]), FS, nperseg=NW, noverlap=NW // 2)
        F_ = f
        P_.append(P)
    if len(P_) < 40:
        return None
    P_ = np.array(P_)
    bnd = (F_ >= 6) & (F_ <= 9)
    e = P_[:, bnd].sum(axis=1)
    top = np.argsort(e)[-max(int(0.05 * len(e)), 5):]
    f0s = [F_[bnd][np.argmax(P_[i, bnd])] for i in top]
    return np.median(f0s), np.percentile(f0s, 25), np.percentile(f0s, 75), len(top)


rows = []
for r in sorted(B):
    s = f0_of(r)
    if not s:
        continue
    tag = B[r][1]
    rows.append((r, B[r][0], cal(tag, 0xC6CD0), cal(tag, 0xC40BC), s[0], s[1], s[2], s[3]))

print("  route build   gain 0xC6CD0   knee   f0 median   IQR            n_win")
for r, b, g, k, f0, q1, q3, n in sorted(rows, key=lambda x: (x[2] or 0, x[3] or 0)):
    print("   r%-4s %-6s %8s      %5s   %6.2f Hz   [%.2f, %.2f]   %4d"
          % (r, b, g, k, f0, q1, q3, n))

f0 = np.array([x[4] for x in rows])
print("\n  f0 across %d routes: median %.3f Hz   range %.3f - %.3f Hz   spread %.1f %%"
      % (len(rows), np.median(f0), f0.min(), f0.max(), (f0.max() / f0.min() - 1) * 100))
print("  spectral resolution at NW=%d is %.3f Hz, i.e. +-%.1f %% at 7.8 Hz"
      % (NW, FS / NW, 100 * (FS / NW) / 2 / 7.8))

from scipy.stats import spearmanr
for nm, idx in (('gain 0xC6CD0', 2), ('knee 0xC40BC', 3)):
    v = np.array([x[idx] for x in rows], float)
    if len(set(v)) < 2:
        continue
    rho, p = spearmanr(v, f0)
    print("  Spearman(%s, f0) = %+.3f   p = %.3f" % (nm, rho, p))

grp = {}
for x in rows:
    grp.setdefault(x[2], []).append(x[4])
print("\n  f0 by forward gain:")
for g in sorted(k for k in grp if k is not None):
    print("    gain %-6d n=%d   median f0 %.3f Hz" % (g, len(grp[g]), np.median(grp[g])))
print("\n  ⇒ %s" % ("f0 MOVES with firmware => a CLOSED-LOOP POLE, relocatable in firmware"
                    if (f0.max() / f0.min() - 1) > 0.10 else
                    "f0 is FIXED across every build and gain => a MECHANICAL RESONANCE.\n"
                    "     Firmware can only DAMP it -- and that route is measured-closed."))
