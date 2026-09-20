"""A7 - what the model's failure does to ARM-KP3's safety case.

ARM-KP3 = rev 6.4 as flown + SteerKP 1.0->3.0, AccordErrorNotchQ 1.0->0.30, AccordTorqueKi 0.30->0.60.
It is defended on "a bounded x1.46 step with the -180 crossing moved to 1.5-1.8 Hz" -- i.e. on the
SAME physical model.  Here: the step, where it lands, and how it moves with b and with the plant
anchor actually used.
"""
import math
import json
import os
import numpy as np
import a4_repaired_statistic as R

OUT = os.path.dirname(__file__)
A3 = json.load(open(os.path.join(OUT, "a3_plant_transfer.json")))

R.CTRL["ARM-KP3 (proposed)"] = dict(kp=3.00, laf=14.0, ki=0.60, F=0.0, notchQ=0.30, rate=0.0010, sr=16.84)

print("=== ARM-KP3 vs rev 6.4 as flown, on every identified plant, at every delay ===")
print(f"{'plant':6} {'D ms':>5} {'rev6.4 |L| @f':>20} {'ARM-KP3 |L| @f':>20} {'step':>7} {'vs r71 controller':>20}")
for pn, key in R.PLANTS.items():
    T = A3[key]["T02"]
    for D in (0.055, 0.065, 0.075):
        rows = {}
        for cn in ("rev6.4(clean,flying)", "ARM-KP3 (proposed)", "r71   (LIMIT CYCLE)"):
            w, L = R.loop(R.CTRL[cn], T, 25.0, D, 0.20)
            rows[cn] = R.crossing(w, L)
        f0, m0 = rows["rev6.4(clean,flying)"]
        f1, m1 = rows["ARM-KP3 (proposed)"]
        f2, m2 = rows["r71   (LIMIT CYCLE)"]
        print(f"{pn:6} {D*1000:5.0f} {m0:12.3f} @{f0:5.2f}Hz {m1:12.3f} @{f1:5.2f}Hz {m1/m0:7.2f} "
              f"{'x'+format(m1/m2,'.2f')+' of r71':>20}")

print("\n=== the same step under the damping b the study's own REPORT leaves open ===")
print(f"{'b':>10} {'zeta':>6} {'rev6.4':>9} {'ARM-KP3':>9} {'step':>7} {'ARM-KP3 f':>10} {'r71':>8} {'ARM/r71':>8}")
T = A3["0000006d--05e83bb04f"]["T02"]
for b in (7e-5, 3e-4, 6e-4, 1.2e-3, 1.8e-3, 4.9e-3):
    out = {}
    for cn in ("rev6.4(clean,flying)", "ARM-KP3 (proposed)", "r71   (LIMIT CYCLE)"):
        w, L = R.loop(R.CTRL[cn], T, 25.0, 0.065, 0.20, b=b)
        out[cn] = R.crossing(w, L)
    z = b / (2 * math.sqrt(R.J * R.k_of_v(25.0)))
    m0 = out["rev6.4(clean,flying)"][1]
    f1, m1 = out["ARM-KP3 (proposed)"]
    m2 = out["r71   (LIMIT CYCLE)"][1]
    print(f"{b:10.1e} {z:6.3f} {m0:9.3f} {m1:9.3f} {m1/m0:7.2f} {f1:10.2f} {m2:8.3f} {m1/m2:8.2f}")

print("\n=== and if the measured extrapolation ratio is used instead of the model's ===")
print("model |P(2.34)|/|P(0.20)| at b=6e-4, 25 m/s = "
      f"{abs(1/(R.J*(1j*2*math.pi*2.34)**2 + 6e-4*(1j*2*math.pi*2.34) + R.k_of_v(25.)))/abs(1/(R.J*(1j*2*math.pi*0.2)**2 + 6e-4*(1j*2*math.pi*0.2) + R.k_of_v(25.))):.3f}")
for pn, key in R.PLANTS.items():
    f = np.array(A3[key]["f"])
    i = int(np.argmin(np.abs(f - 2.34)))
    print(f"   measured on {pn:5}: {A3[key]['ratio'][i]:.3f}")
