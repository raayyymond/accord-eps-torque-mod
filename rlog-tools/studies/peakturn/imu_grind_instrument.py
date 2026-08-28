# -*- coding: utf-8 -*-
"""Can the IMU serve as a GRIND #1 instrument?  Validate it on Lever B, as before.

The IMU logs at 100 Hz on every route (verified: length ratio 1.00 against cs_rate), so
Nyquist is 50 Hz and the 18-22 Hz grind band is genuinely visible rather than aliased.
Crucially it measures CHASSIS VIBRATION, so unlike every steering-rate measure it does
NOT need creep exposure -- which is what made grind #1 unmeasurable on the recent routes.

Validation, same design as before: V101/V102/V103 accidentally dropped Lever B, whose
measured on-car effect on grind #1 is 0.40 [0.27, 0.58], i.e. OFF should be ~2.5x worse.
If the IMU recovers that, it is a usable instrument on ALL routes.

Exposure control: each route's own low-speed windows are the reference, and the outcome is
the ratio, so road-surface and speed differences between drives largely cancel.
"""
import numpy as np, os
from scipy import signal

FS, NW = 100.0, 256
LB = {'21': ('V111', 1), '22': ('V112', 1), '23': ('V112', 1), '77': ('V90', 1),
      '78': ('V91', 1), '79': ('V92', 1), '7e': ('V96', 1), '7f': ('V96', 1),
      '85': ('V100', 1), '95': ('V101', 0), '96': ('V102', 0), '9e': ('V103', 0),
      'a4': ('V104', 1), 'a5': ('V105', 1), 'a6': ('V106', 1), '1e': ('V107', 1)}


def stat(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    need = ('imu_vert', 'cc_lat', 'cs_v')
    if any(k not in z.files for k in need):
        return None
    iv, lat, v = [np.asarray(z[k]).astype(float) for k in need]
    eng, man = [], []
    for a in range(0, len(iv) - NW, NW // 2):
        b = a + NW
        if not np.isfinite(iv[a:b]).all() or v[a:b].mean() < 1.0:
            continue
        f, P = signal.welch(iv[a:b] - iv[a:b].mean(), FS, nperseg=NW, noverlap=NW // 2)
        g = np.sqrt(P[(f >= 18) & (f <= 22)].sum() * (f[1] - f[0]))
        tot = np.sqrt(P[(f >= 1) & (f <= 45)].sum() * (f[1] - f[0]))
        if tot <= 0:
            continue
        (eng if lat[a:b].mean() > 0.5 else man).append(g / tot)
    if len(eng) < 25 or len(man) < 25:
        return None
    return np.percentile(eng, 90), np.percentile(man, 90), len(eng), len(man)


rows = []
for r in sorted(LB):
    s = stat(r)
    if s:
        rows.append((r, LB[r][0], LB[r][1], s[0], s[1], s[0] / s[1], s[2], s[3]))

print("  IMU vertical, 18-22 Hz as a share of 1-45 Hz, p90.  Engaged vs MANUAL, same drive.\n")
print("  route build  LeverB   eng share   man share   eng/man   n_eng n_man")
for r, b, lb, e, m, rt, ne, nm in sorted(rows, key=lambda x: (x[2], x[1])):
    print("   r%-4s %-6s %s     %8.4f    %8.4f   %6.3f   %5d %5d"
          % (r, b, 'OFF' if lb == 0 else ' ON', e, m, rt, ne, nm))

off = np.array([x[5] for x in rows if x[2] == 0])
on = np.array([x[5] for x in rows if x[2] == 1])
print("\n  Lever B OFF (n=%d routes): median eng/man = %.4f" % (len(off), np.median(off) if len(off) else np.nan))
print("  Lever B ON  (n=%d routes): median eng/man = %.4f" % (len(on), np.median(on) if len(on) else np.nan))
if len(off) and len(on):
    rng = np.random.default_rng(0)
    bs = [np.median(rng.choice(off, len(off))) / np.median(rng.choice(on, len(on))) for _ in range(4000)]
    pt = np.median(off) / np.median(on)
    print("    OFF/ON = %.3f   route-bootstrap CI [%.3f, %.3f]    (expected ~2.5x if the IMU sees grind #1)"
          % (pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    print("\n  => %s" % ("IMU IS A VALID GRIND-#1 INSTRUMENT -- and it needs no creep exposure"
                         if np.percentile(bs, 2.5) > 1.0 else
                         "IMU does NOT recover the known Lever B effect -- not validated as an instrument"))
