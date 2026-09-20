"""A6 - is the per-route "measured complex plant" a PLANT at all?

A plant cannot know about the controller's notch.  If the identified u -> angle transfer peaks
at the notch centre get_honda_accord_mode_hz(v) on exactly the routes that flew the notch, the
identification is reading -1/C (closed-loop bias), not P.
"""
import json
import math
import os
import numpy as np
import a4_repaired_statistic as R

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
OUT = os.path.dirname(__file__)
A3 = json.load(open(os.path.join(OUT, "a3_plant_transfer.json")))

NOTCH = {"0000006c--2bc842dbac": False, "00000070--717f5a7866": False, "00000071--f2c9d073a3": False,
         "00000072--8001fc3048": True, "00000073--79fd149dd8": True, "0000006d--05e83bb04f": True,
         "00000076--d0b7ea7e4d": True}

print(f"{'route':22} {'notch flown':>12} {'med v':>7} {'mode_hz(v)':>11} {'peak f of |T|/|T(0.2)|':>24} {'peak val':>9} {'F=SteerFriction':>16}")
print("-" * 108)
for key, has in NOTCH.items():
    z = np.load(os.path.join(CACHE, key + ".npz"))
    t = z["t_cs"]
    ok = (z["cs_active"] > 0.5)
    v = np.interp(t, z["t_cst"], z["vego"])
    sp = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    med = float(np.median(v[ok & ~sp & (v >= 15.0)]))
    del z
    d = A3[key]
    f = np.array(d["f"])
    r = np.array(d["ratio"])
    band = (f >= 1.6) & (f <= 3.2)
    ip = int(np.argmax(r[band]))
    fp = f[band][ip]
    print(f"{key:22} {str(has):>12} {med:7.1f} {R.mode_hz(med):11.2f} {fp:24.2f} {r[band][ip]:9.3f}")

print()
print("A plant is a property of the car.  r72 and r73 flew the SAME COMMIT and the same tune except")
print("SteerFriction (0.0 vs 0.212).  Their 0.20 Hz anchors agree to 3.5 % "
      f"({A3['00000072--8001fc3048']['T02']:.2f} vs {A3['00000073--79fd149dd8']['T02']:.2f} deg/torque).")
i234 = int(np.argmin(np.abs(np.array(A3['00000072--8001fc3048']['f']) - 2.34)))
r72 = A3['00000072--8001fc3048']['ratio'][i234]
r73 = A3['00000073--79fd149dd8']['ratio'][i234]
print(f"Their extrapolation targets at 2.34 Hz differ by x{r72/r73:.1f} ({r72:.3f} vs {r73:.3f}).")
