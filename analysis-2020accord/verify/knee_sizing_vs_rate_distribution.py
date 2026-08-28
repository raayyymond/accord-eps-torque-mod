# -*- coding: utf-8 -*-
"""How large must `knee` be for the relay to stop being a signum where the symptom lives?

  fVar13 = clamp(POL * gp-0x6abc * 12 / knee, +-1)      saturates at |gp-0x6abc| >= knee/12
  gp-0x6abc = 4.7121 ct/(deg/s)   (V111's tap, independently confirmed)
  => saturation rate = knee / (12 * 4.7121) deg/s

Small-signal gain (K1/1024)(12/knee) must be held at V112's 0.0039844, so K1 = 0.34 * knee.
Both are 16-bit, so the arithmetic ceiling is knee 65535 / K1 22282.

The point of a larger knee is NOT more damping. With the gain held, the friction is
IDENTICAL at low rate and LARGER at high rate -- and more modelled friction means MORE
assist (accord-friction-polarity-more-assist), so it moves the operator's constraint the
right way while removing the signum that radiates harmonics.
"""
import numpy as np, os

CT = 4.7121                       # counts per deg/s on gp-0x6abc
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e', 'a4', 'a5', 'a6', '1e']

R = []
for r in ROUTES:
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        continue
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        continue
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    R.append(np.abs(rate[(lat > 0.5) & (v > 1.0)]))
A = np.concatenate(R)
print("|steering rate| over %d engaged frames, %d routes:\n" % (len(A), len(R)))
for q in (50, 90, 99, 99.5, 99.9, 99.99):
    print("   p%-6s %7.2f deg/s   = %6.0f counts" % (q, np.percentile(A, q), np.percentile(A, q) * CT))
print("   max     %7.2f deg/s   = %6.0f counts" % (A.max(), A.max() * CT))

print("\n\nRELAY SATURATION vs knee  -- 'linear' = the relay is NOT clipped, i.e. no signum")
print("   knee     K1     sat rate    %% of engaged frames SATURATED   sat vs osc median p95 (47.06)")
for knee in (600, 1800, 2400, 3000, 4000, 5654, 8482, 12000, 20000, 65535):
    k1 = round(0.0039844 * 1024 * knee / 12)
    sat = knee / (12 * CT)
    frac = (A >= sat).mean() * 100
    tag = ''
    if knee == 600:
        tag = '  stock'
    elif knee == 1800:
        tag = '  V112 ON CAR'
    elif knee == 2400:
        tag = '  V116 built'
    ok = 'CLEARS' if sat >= 47.06 else 'still clipped'
    print("   %6d  %6d   %7.1f     %8.3f %%                    %-14s%s" % (knee, k1, sat, frac, ok, tag))

print("\n   (K1 chosen so the small-signal gain stays EXACTLY V112's 0.0039844; both fit 16-bit)")
print("\n   friction delivered = |model| * (K1/1024) * clamp(rate*CT*12/knee, +-1)")
print("   sanity check at three rates, V112 vs a knee-5654 build:")
for dps in (10, 30, 50, 100, 200):
    ct = dps * CT
    f112 = 612 / 1024 * min(ct * 12 / 1800, 1.0)
    k1n = round(0.0039844 * 1024 * 5654 / 12)
    fnew = k1n / 1024 * min(ct * 12 / 5654, 1.0)
    print("     %4d deg/s :  V112 %.4f   knee5654 %.4f   ratio %.3fx" % (dps, f112, fnew, fnew / f112))
