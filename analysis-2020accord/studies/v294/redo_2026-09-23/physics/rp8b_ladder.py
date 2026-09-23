import math, numpy as np
from rp3_wheel_mode import loop, closed_poles, mode
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
def k(v, lev): return float(np.interp(v, HOLD_V_BP, HOLD_K_V)) * (float(np.interp(v, [12.5, 17.5], [1.15, 1.45])) if lev else 1.0)
print("EXACT zeta ratio (light b 6e-4), d=1 m=3; K/J fixed by b = 567*(1-a/1024)/(1-1011/1024)*KJ")
print(" a    pole   K/J   lev |  " + "  ".join(f"{v:>5}" for v in (3, 5, 7, 8, 12.5, 19, 26)) + " | 20 Hz |Cr| vs shipped")
for a in (1011, 1015, 1018, 1020):
    for KJ in (0.5, 1.0):
        bb = 567 * (1 - a / 1024) / (1 - 1011 / 1024) * KJ
        for lev in (False, True):
            row = []
            for v in (3, 5, 7, 8, 12.5, 19, 26):
                Ln0, Ld0 = loop(8e-5, 6e-4, k(v, lev), gain=0.0); z0 = mode(closed_poles(Ln0, Ld0), 0.1, 8)
                Ln, Ld = loop(8e-5, 6e-4, k(v, lev), a=a, bb=bb); z1 = mode(closed_poles(Ln, Ld), 0.1, 8)
                row.append(z1[0] / z0[0])
            z = np.exp(-2j * np.pi * 20 * 1e-3)
            r20 = abs((bb / 1024) * (1 - z) / (1 - a / 1024 * z)) / abs((567 / 1024) * (1 - z) / (1 - 1011 / 1024 * z))
            print(f"{a}  {-math.log(a/1024)/(2*math.pi*1e-3):4.2f}  {KJ:3.1f}  {'L' if lev else 'M'}   |  " + "  ".join(f"{r:5.2f}" for r in row) + f" | x{r20:.2f}")
