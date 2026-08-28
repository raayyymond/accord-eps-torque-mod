# -*- coding: utf-8 -*-
"""Hunt grind-#1 levers with the IMU instrument, on ALL routes including creep-free ones.

The IMU is validated (recovers Lever B at 1.139x, CI [1.005, 1.338]) but diluted ~10x, so
ONLY A POSITIVE RESULT IS INFORMATIVE -- a null here means nothing. Pre-registered on that
basis: I will report a hit only if its route-bootstrap CI excludes 1.0, and I will NOT
report any null as evidence of absence.

Outcome: IMU-vertical 18-22 Hz share of 1-45 Hz, p90, engaged vs manual WITHIN each drive.
Lever B is held constant by restricting to the routes that carry it, so the largest known
effect does not swamp everything else.
"""
import numpy as np, glob, os
from scipy import signal

FS, NW = 100.0, 256
FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
# Lever-B-ON routes only
ON = {'21': ('V111', '_v111_'), '22': ('V112', '_v112_'), '23': ('V112', '_v112_'),
      '77': ('V90', '_v90_'), '78': ('V91', '_v91_'), '79': ('V92', '_v92_'),
      '7e': ('V96', '_v96_'), '7f': ('V96', '_v96_'), '85': ('V100', '_v100_'),
      'a4': ('V104', '_v104_'), 'a5': ('V105', '_v105_'), 'a6': ('V106', '_v106_'),
      '1e': ('V107', '_v107_')}
CAL = {'knee_C40BC': (0xC40BC, 2), 'K1_C40D2': (0xC40D2, 2), 'a2_C40DC': (0xC40DC, 2),
       'gain_C6CD0': (0xC6CD0, 2), 'biq_C649B': (0xC649B, 1), 'fric_D7A5C': (0xD7A5C, 2),
       'fricY2_D7A6C': (0xD7A6C, 2), 'clamp_C407E': (0xC407E, 2)}


def cals(tag):
    g = [x for x in glob.glob(os.path.join(FR, tag + '*plain_image.bin')) if 'SUPERSEDED' not in x]
    if not g:
        return None
    d = open(g[0], 'rb').read()
    return {n: (d[a] if w == 1 else int.from_bytes(d[a:a + w], 'little')) for n, (a, w) in CAL.items()}


def stat(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('imu_vert', 'cc_lat', 'cs_v')):
        return None
    iv, lat, v = [np.asarray(z[k]).astype(float) for k in ('imu_vert', 'cc_lat', 'cs_v')]
    eng, man = [], []
    for a in range(0, len(iv) - NW, NW // 2):
        b = a + NW
        if not np.isfinite(iv[a:b]).all() or v[a:b].mean() < 1.0:
            continue
        f, P = signal.welch(iv[a:b] - iv[a:b].mean(), FS, nperseg=NW, noverlap=NW // 2)
        tot = P[(f >= 1) & (f <= 45)].sum()
        if tot <= 0:
            continue
        (eng if lat[a:b].mean() > 0.5 else man).append(P[(f >= 18) & (f <= 22)].sum() / tot)
    if len(eng) < 25 or len(man) < 25:
        return None
    return np.percentile(eng, 90) / np.percentile(man, 90)


rows = []
for r in sorted(ON):
    y = stat(r)
    c = cals(ON[r][1])
    if y and c:
        rows.append((r, ON[r][0], y, c))
print("  %d Lever-B-ON routes with usable IMU.  Outcome = IMU 18-22 Hz eng/man ratio.\n" % len(rows))
print("  route build   IMU eng/man")
for r, b, y, c in sorted(rows, key=lambda x: x[2]):
    print("   r%-4s %-6s   %6.3f" % (r, b, y))

y = np.array([x[2] for x in rows])
rng = np.random.default_rng(0)
print("\n  predictor        levels  values                    ratio hi/lo   CI            VERDICT")
for n in CAL:
    v = np.array([float(x[3][n]) for x in rows])
    u = sorted(set(v))
    if len(u) < 2:
        print("   %-16s %4d   %-24s  CONSTANT -- untestable" % (n, 1, '%g' % u[0]))
        continue
    lo = y[v <= u[0]]
    hi = y[v >= u[-1]]
    if len(lo) < 3 or len(hi) < 3:
        print("   %-16s %4d   %-24s  too few routes per arm (%d/%d)"
              % (n, len(u), ','.join('%g' % x for x in u[:4]), len(lo), len(hi)))
        continue
    bs = [np.median(rng.choice(hi, len(hi))) / np.median(rng.choice(lo, len(lo))) for _ in range(4000)]
    lo_ci, hi_ci = np.percentile(bs, 2.5), np.percentile(bs, 97.5)
    hit = (lo_ci > 1.0) or (hi_ci < 1.0)
    print("   %-16s %4d   %-24s  %6.3f        [%.2f, %.2f]  %s"
          % (n, len(u), ','.join('%g' % x for x in u[:4]), np.median(hi) / np.median(lo),
             lo_ci, hi_ci, '<== HIT' if hit else 'not resolved'))
print("\n  \U0001f6d1 A 'not resolved' row is NOT evidence of absence -- the IMU is ~10x diluted.")
