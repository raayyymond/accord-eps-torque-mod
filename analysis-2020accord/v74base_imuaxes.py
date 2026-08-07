#!/usr/bin/env python3
"""Which IMU axis is VERTICAL on this route? Determined empirically, not assumed.

The brief asks for "|az| excursions". On this device `az` has mean -0.08 m/s^2 and `ax` has mean
+9.70 -- gravity is on `ax`. Assigning axes by name would measure the wrong thing, so each axis is
tested against an independent witness:
  vertical    -> carries ~g and correlates with NOTHING on the CAN bus (road input only)
  longitudinal-> correlates with d(vEgo)/dt
  lateral     -> correlates with gz * vEgo  (yaw rate x speed)
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CACHE, PFX = "_cache_r5d", "r5ds"


def seg(s):
    return dict(np.load(f"{CACHE}/{PFX}{s}_imu.npz")), dict(np.load(f"{CACHE}/{PFX}{s}.npz"))


print(f"{'seg':>4} {'mean ax':>9} {'mean ay':>9} {'mean az':>9} | "
      f"{'r(ax,dv)':>9} {'r(ay,dv)':>9} {'r(az,dv)':>9} | "
      f"{'r(ax,yv)':>9} {'r(ay,yv)':>9} {'r(az,yv)':>9}")
for s in (0, 5, 6, 7, 13, 14, 16):
    im, cn = seg(s)
    t = im["at"]
    v = np.interp(t, cn["t"], cn["cs_v"])
    dv = np.gradient(v, t)
    gz = np.interp(t, im["gt"], im["gz"])
    yv = gz * v
    row = [f"{s:>4}"]
    for k in ("ax", "ay", "az"):
        row.append(f"{im[k].mean():>9.3f}")
    row.append("|")
    for k in ("ax", "ay", "az"):
        row.append(f"{np.corrcoef(im[k], dv)[0,1]:>9.3f}")
    row.append("|")
    for k in ("ax", "ay", "az"):
        row.append(f"{np.corrcoef(im[k], yv)[0,1]:>9.3f}")
    print(" ".join(row))
