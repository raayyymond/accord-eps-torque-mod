# -*- coding: utf-8 -*-
"""Do the ANGLE-indexed levers reach where the 7-9 Hz oscillation actually lives?

The kit killed both on statistics taken over ALL engaged driving:
  FactorD table (a)  -- inert below ~35 km/h (FactorC's Y[0]=0 multiplies in first)
  table (b) 0xC6B66/0xC6B80 -- "88.6 % of engaged driving sits in its flat first segment"

But the symptom is ANGLE-GATED: it lives in the tail those statistics average away.
Ask the question restricted to oscillating windows.
"""
import numpy as np, glob, os
from scipy import signal

FS, NW = 100.0, 256
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e', 'a4', 'a5', 'a6', '1e']
FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
TP = 0xBF000

st = open(glob.glob(FR + '/**/code.bin', recursive=True)[0], 'rb').read()
v112 = open([x for x in glob.glob(FR + '/_v112_*plain_image.bin') if 'SUPER' not in x][0], 'rb').read()
u16 = lambda d, a: int.from_bytes(d[a:a + 2], 'little')

print("TABLE (b) -- 0xC6B66 (X) / 0xC6B80 (Y), 13 points, inline in FUN_0003b8f6, indexed on")
print("gp-0x6a10 = ABSOLUTE STEERING ANGLE.\n")
X = [u16(st, 0xC6B66 + 2 * i) for i in range(13)]
Ys = [u16(st, 0xC6B80 + 2 * i) for i in range(13)]
Yv = [u16(v112, 0xC6B80 + 2 * i) for i in range(13)]
print("  X (stock) = %s" % X)
print("  Y (stock) = %s" % Ys)
print("  Y (V112 ) = %s   identical: %s" % (Yv, Ys == Yv))

# gp-0x6a10 scaling: V84's b4 rung == |angle| >= 0.85 deg, and the step sat exactly on the
# threshold's own numeric value. Anchor the axis on that.
SCALE = None
for cand in (X[1], X[0]):
    if cand:
        SCALE = 0.85 / cand
        break
print("\n  anchor: |angle| >= 0.85 deg == the first non-zero knot (%d) => %.5f deg/count" % (X[1], SCALE))
print("  X in DEGREES = %s" % [round(x * SCALE, 2) for x in X])
flat_end = 0
for i in range(1, 13):
    if Ys[i] != Ys[0]:
        flat_end = i
        break
print("  flat first segment ends at knot %d = %.2f deg  (Y goes %d -> %d)"
      % (flat_end, X[flat_end] * SCALE, Ys[0], Ys[flat_end]))


def wins(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')):
        return None
    rate, lat, v, ang = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')]
    m = (lat > 0.5) & (v > 1.0)
    o = []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        x = rate[sl] - np.mean(rate[sl])
        f, P = signal.welch(x, FS, nperseg=NW, noverlap=NW // 2)
        b = (f >= 6) & (f <= 9)
        o.append((np.sqrt(np.sum(P[b]) * (f[1] - f[0])),
                  np.percentile(np.abs(ang[sl]), 95),
                  np.mean(v[sl]) * 3.6))
    return np.array(o) if o else None


A = np.vstack([w for w in (wins(r) for r in ROUTES) if w is not None])
osc, a95, kph = A[:, 0], A[:, 1], A[:, 2]
OSC = osc >= np.percentile(osc, 95)
print("\n\n%d engaged windows; %d OSCILLATING (6-9 Hz top 5 %%)\n" % (len(A), OSC.sum()))

print("  DOES FactorD (table a) REACH? -- it is INERT below ~35 km/h (FactorC Y[0]=0)")
print("     all engaged windows above 35 km/h : %5.1f %%" % ((kph > 35).mean() * 100))
print("     OSCILLATING windows above 35 km/h : %5.1f %%" % ((kph[OSC] > 35).mean() * 100))
print("     median speed, oscillating         : %5.1f km/h   (all: %.1f)"
      % (np.median(kph[OSC]), np.median(kph)))

thr = X[flat_end] * SCALE
print("\n  DOES TABLE (b) REACH? -- the kit killed it because 88.6 %% of engaged driving")
print("  sits in its FLAT first segment (|angle| < %.2f deg). But the symptom is angle-gated:" % thr)
print("     all engaged windows with p95|ang| > %5.2f deg : %5.1f %%" % (thr, (a95 > thr).mean() * 100))
print("     OSCILLATING windows with p95|ang| > %5.2f deg : %5.1f %%" % (thr, (a95[OSC] > thr).mean() * 100))
print("     median p95|ang|, oscillating : %6.2f deg   (all: %.2f)" % (np.median(a95[OSC]), np.median(a95)))
lift = (a95[OSC] > thr).mean() / max((a95 > thr).mean(), 1e-9)
print("\n  ⇒ enrichment of the shaped region among oscillating windows: %.2fx" % lift)
both = ((kph[OSC] > 35) & (a95[OSC] > thr)).mean() * 100
print("  ⇒ OSCILLATING windows that are BOTH >35 km/h AND in the shaped region: %5.1f %%" % both)
