"""SPEED / TORQUE CENSUS of every route the V104 dose derivation rests on.

The dose chain is:
    (c, A0, G0)   <- routes r85 (V100 4x) and r95 (V101 8x)      [the 4x/8x gain step]
    a_filt        <- routes r96 (V102 disarmed) and r9e (V103 armed-engaged)
    Z(1)          <- route r9e
If any of those routes' ENGAGED speed distribution is far from the highway, the identification
is a low-speed identification and the highway dose inherits an extrapolation.

Also prints the ENGAGED |tq| distribution, because the ROM assist-map slope depends far more
strongly on the driver-torque operating point than on speed (v104_speed_schedule_of_a.py sec 2).

🛑 GUARDS OBSERVED
  - `x6b94` is a byte-identical ALIAS of the LANE in r96/r97/r9e -- this file never reads it there.
  - safe time pairs only; no (t, raw14_b4) pairing anywhere.
  - `v_rear` is m/s (livePose / wheel-speed derived), NOT the firmware's 64 ct/km/h count.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROUTES = [('r85', 'V100 4x   (c, A0, G0)'),
          ('r95', 'V101 8x   (c, A0, G0)'),
          ('r96', 'V102 disarmed (a_filt)'),
          ('r97', 'V102 stock-1x baseline'),
          ('r9e', 'V103 armed   (a_filt, Z(1))')]
KPH = 3.6

print("=" * 112)
print("1. ENGAGED SPEED DISTRIBUTION (km/h) -- v_rear")
print("=" * 112)
print("%6s %-26s %7s %7s %7s %7s %7s %7s %8s %8s %8s" %
      ('route', 'role', 'eng s', 'p5', 'p25', 'p50', 'p75', 'p95', '>=50', '>=80', '>=90'))
D = {}
for t, role in ROUTES:
    d = L.load(t)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    ve = v[eng]
    D[t] = dict(d=d, eng=eng, v=v)
    print("%6s %-26s %7.1f %7.1f %7.1f %7.1f %7.1f %7.1f %8.3f %8.3f %8.3f" %
          (t, role, eng.sum() / L.FS, *[np.percentile(ve, q) for q in (5, 25, 50, 75, 95)],
           (ve >= 50).mean(), (ve >= 80).mean(), (ve >= 90).mean()))

print()
print("  ENGAGED SECONDS in each speed band:")
BANDS_V = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 130)]
print("%6s" % 'route' + "".join("%13s" % ("%d-%d" % b) for b in BANDS_V))
for t, _ in ROUTES:
    ve = D[t]['v'][D[t]['eng']]
    print("%6s" % t + "".join("%13.1f" % (((ve >= a) & (ve < b)).sum() / L.FS) for a, b in BANDS_V))

print()
print("=" * 112)
print("2. ENGAGED |tq| DISTRIBUTION (CAN counts) -- the assist-map OPERATING POINT")
print("=" * 112)
print("%6s %9s %9s %9s %9s %9s %9s" % ('route', 'p10', 'p25', 'p50', 'p75', 'p90', 'p99'))
for t, _ in ROUTES:
    a = np.abs(D[t]['d']['tq'].astype(float))[D[t]['eng']]
    print("%6s %9.0f %9.0f %9.0f %9.0f %9.0f %9.0f"
          % (t, *[np.percentile(a, q) for q in (10, 25, 50, 75, 90, 99)]))

print()
print("  |tq| p50 within each ENGAGED speed band (does the operating point move with speed?):")
print("%6s" % 'route' + "".join("%13s" % ("%d-%d" % b) for b in BANDS_V))
for t, _ in ROUTES:
    a = np.abs(D[t]['d']['tq'].astype(float))
    v, e = D[t]['v'], D[t]['eng']
    row = []
    for lo, hi in BANDS_V:
        m = e & (v >= lo) & (v < hi)
        row.append(np.percentile(a[m], 50) if m.sum() > 200 else np.nan)
    print("%6s" % t + "".join(("%13.0f" % r) if np.isfinite(r) else "%13s" % '-' for r in row))

print()
print("=" * 112)
print("3. THE MATCHED WINDOW THAT PRODUCED a_filt -- v in [5,25] m/s = [18, 90] km/h")
print("=" * 112)
for t in ('r96', 'r9e'):
    v = D[t]['v']
    ra = np.abs(D[t]['d']['rate_f'].astype(float))
    keep = (v >= 5 * KPH) & (v <= 25 * KPH) & (ra <= 60.0) & D[t]['eng']
    print("  %s: %6.1f s inside the matched window, v p50 %.1f km/h, p90 %.1f, "
          "fraction of that window at >=80 km/h: %.4f"
          % (t, keep.sum() / L.FS, np.percentile(v[keep], 50), np.percentile(v[keep], 90),
             (v[keep] >= 80).mean()))
print()
print("  ⇒ `a_filt` is a duty-weighted average over ~18-90 km/h.  Its effective centre is the")
print("    MEDIAN of that window, not the highway.")

print()
print("=" * 112)
print("4. 427 CHANNEL QUALITY on the identification routes (r85 / r95 only -- genuine SUM)")
print("=" * 112)
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
for t in ('r85', 'r95'):
    d = D[t]['d']
    eng = D[t]['eng']
    u = d['x6b94'].astype(float)
    eps = L.episodes(eng)
    sp = L.episode_specs(d['tq'].astype(float), u, eps, NPER)
    for lo, hi in ((6, 9), (21, 22.5)):
        H, coh = L.band_H(sp, f, lo, hi)
        sel = (f >= lo) & (f < hi)
        Syy = sum(s[1] for s in sp)
        nw = sum(s[3] for s in sp)
        rms = np.sqrt(Syy[sel].sum() / nw * (f[1] - f[0]))
        print("  %s %4.1f-%-4.1f Hz: |G| %.4f  argG %+7.1f  coh2 %.3f   band-RMS of u = %.1f ct "
              "= %.2f LSB (LSB = 12.8 ct)" % (t, lo, hi, abs(H), np.angle(H, deg=True), coh,
                                              rms, rms / 12.8))
print("  ⚠ 427 is a 10-bit code at 12.8 counts/LSB.  A band-RMS below ~1 LSB means the transfer")
print("    rests on dither, not on resolved signal -- quantisation noise is uncorrelated with tq")
print("    so |G| stays UNBIASED, but the episode bootstrap must carry the variance.")
