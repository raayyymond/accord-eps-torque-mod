import numpy as np
from rp5b_sensitivity import rows
ok = [r for r in rows if r[6][1] > 0 and r[6][2] < 1]
m4 = sorted(ok, key=lambda r: r[7][1])[:6]
print("V293-stable cases: lowest V294 worst-crossover PM:")
for r in m4: print(f"  V294 PM {r[7][1]:+.0f} GMinv {r[7][2]:.2f} (V293 PM {r[6][1]:+.0f}) | v {r[0]} {r[1]} {r[2]} Jx{r[3]} tau {r[4]*1e3:.0f} fric {r[5]}")
m3 = sorted(ok, key=lambda r: r[6][1])[:3]
print("lowest V293 PM among V293-stable:", [(round(r[6][1]), round(r[7][1]), r[:6]) for r in m3])
un4 = [r for r in rows if not (r[7][1] > 0 and r[7][2] < 1)]
print("V294-unstable cases (all V293-unstable too):", len(un4), sorted(set((r[0], r[1]) for r in un4)))
