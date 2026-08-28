# -*- coding: utf-8 -*-
"""POSITIVE CONTROL for the grind-#1 pipeline, using Lever B's accidental natural experiment.

V101/V102/V103 dropped Lever B; V90-V100 and V104+ carry it. Lever B's measured on-car
effect on grind #1 is 0.40 [0.27, 0.58] -- roughly a 2.5x difference. So the three
Lever-B-OFF routes (r95, r96, r9e) should be measurably WORSE than the thirteen ON routes.

This is a control on the INSTRUMENT, not a new claim:
  - if the pipeline recovers a ~2.5x difference, it is sensitive enough to hunt new levers
    and its recent nulls (knee vs grind #1) mean something;
  - if it recovers nothing, the pipeline is too weak and every grind-#1 null this session
    is uninformative.

Statistic: ABSOLUTE 18-22 Hz rms (not share -- share is normalised by broadband power and is
not severity), with each route's own low-rate windows as its exposure control, then a
route-level bootstrap.
"""
import numpy as np, os
from scipy import signal

FS, NW = 100.0, 256
LEVER_B = {'21': ('V111', 1), '22': ('V112', 1), '23': ('V112', 1), '77': ('V90', 1),
           '78': ('V91', 1), '79': ('V92', 1), '7e': ('V96', 1), '7f': ('V96', 1),
           '85': ('V100', 1), '95': ('V101', 0), '96': ('V102', 0), '9e': ('V103', 0),
           'a4': ('V104', 1), 'a5': ('V105', 1), 'a6': ('V106', 1), '1e': ('V107', 1)}


def route_stat(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    hi, lo = [], []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        f, P = signal.welch(rate[sl] - np.mean(rate[sl]), FS, nperseg=NW, noverlap=NW // 2)
        g = np.sqrt(np.sum(P[(f >= 18) & (f <= 22)]) * (f[1] - f[0]))
        pk = np.percentile(np.abs(rate[sl]), 95)
        (hi if pk >= 20 else lo).append(g)
    if len(hi) < 15 or len(lo) < 15:
        return None
    return np.percentile(hi, 90), np.percentile(lo, 90), len(hi), len(lo)


rows = []
for r in sorted(LEVER_B):
    s = route_stat(r)
    if s:
        rows.append((r, LEVER_B[r][0], LEVER_B[r][1], s[0], s[1], s[2], s[3]))

print("  ABSOLUTE 18-22 Hz rms p90, split by each route's OWN rate exposure\n")
print("  route build  LeverB   hi-rate p90   lo-rate p90    ratio    n_hi n_lo")
for r, b, lb, h, l, nh, nl in sorted(rows, key=lambda x: (x[2], x[1])):
    print("   r%-4s %-6s %s      %8.4f      %8.4f    %6.2f   %4d %4d"
          % (r, b, 'OFF' if lb == 0 else ' ON', h, l, h / l, nh, nl))

off = np.array([x[3] for x in rows if x[2] == 0])
on = np.array([x[3] for x in rows if x[2] == 1])
offr = np.array([x[3] / x[4] for x in rows if x[2] == 0])
onr = np.array([x[3] / x[4] for x in rows if x[2] == 1])
print("\n  Lever B OFF (n=%d routes): hi-rate p90 median %.4f   exposure-ratio median %.2f"
      % (len(off), np.median(off), np.median(offr)))
print("  Lever B ON  (n=%d routes): hi-rate p90 median %.4f   exposure-ratio median %.2f"
      % (len(on), np.median(on), np.median(onr)))
rng = np.random.default_rng(0)
for nm, a, b in (('absolute hi-rate p90', off, on), ('exposure-controlled ratio', offr, onr)):
    bs = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(4000)]
    pt = np.median(a) / np.median(b)
    print("    %-26s OFF/ON = %.2fx   route-bootstrap CI [%.2f, %.2f]"
          % (nm, pt, np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
print("\n  Lever B's measured on-car effect is 0.40 [0.27, 0.58] => OFF/ON should be about 2.5x.")
print("  ⇒ %s" % ("PIPELINE IS SENSITIVE -- it recovers the known effect"
                  if np.median(offr) / np.median(onr) > 1.5 else
                  "PIPELINE CANNOT SEE A KNOWN 2.5x EFFECT -- every grind-#1 null this session is uninformative"))
