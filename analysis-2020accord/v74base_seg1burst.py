#!/usr/bin/env python3
"""The ONE manual sub-35 km/h damper burst on route 5d: seg1 t=45.4..46.9 s. Context, in full."""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

d = dict(np.load("_cache_r5d/r5ds1.npz"))
t, lat, dmp, v = d["t"], d["cc_lat"] > 0.5, d["damp_nz"] > 0.5, d["cs_v"]

edges = np.flatnonzero(np.diff(lat.astype(int)) != 0)
print("seg1 latActive edges (t, direction):")
for e in edges:
    print(f"  t={t[e+1]:.3f}  {'RISE' if lat[e+1] else 'FALL'}")

burst = np.flatnonzero(dmp & ~lat & (v < 9.7222))
print(f"\nmanual sub-knee firing frames in seg1: {len(burst)}  "
      f"t={t[burst[0]]:.3f}..{t[burst[-1]]:.3f}")
prev_fall = max((t[e + 1] for e in edges if not lat[e + 1] and t[e + 1] <= t[burst[0]]),
                default=float("nan"))
next_rise = min((t[e + 1] for e in edges if lat[e + 1] and t[e + 1] >= t[burst[-1]]),
                default=float("nan"))
print(f"  previous FALL at t={prev_fall:.3f}  =>  burst starts {t[burst[0]]-prev_fall:.3f} s after "
      f"disengagement (V73 fall lag = 2.0798 s)")
print(f"  next RISE at t={next_rise:.3f}  =>  burst ends {next_rise-t[burst[-1]]:.3f} s before "
      f"re-engagement (V73 rise lag = 1.0209 s)")

i0, i1 = burst[0] - 40, burst[-1] + 40
print(f"\n{'t':>8} {'lat':>4} {'sca':>4} {'bit7':>5} {'v m/s':>7} {'tq':>8} {'ang':>8} "
      f"{'rate_c':>8} {'sstat':>6}")
for i in range(max(0, i0), min(len(t), i1)):
    mark = " *" if dmp[i] and not lat[i] else ""
    if i % 2:
        continue
    print(f"{t[i]:>8.3f} {int(lat[i]):>4} {int(d['sca'][i]):>4} {int(dmp[i]):>5} {v[i]:>7.2f} "
          f"{d['tq'][i]:>8.1f} {d['ang'][i]:>8.2f} {d['rate_c'][i]:>8.1f} "
          f"{int(d['sstat'][i]):>6}{mark}")
