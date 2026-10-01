# -*- coding: utf-8 -*-
"""f4c: stage-3 spec -- the frontier between 'passes every gate' (flat Ki 0.5; Kp 0.75 + Ki 0.3/0.6) and 'wins but trips
G8' (KiHigh >= 1.0).  F 0.011 is kept (stage 2: F 0.005 / 0 fail G11, F 0.016 fails G6)."""
import json, itertools

forks = []
for kp, ki in ((0.9, 0.55), (0.9, 0.6), (0.9, 0.7), (0.8, 0.5), (0.8, 0.6)):
    forks.append(dict(name="L14_Kp%.2f_Ki%.2f_0.0" % (kp, ki), kp=kp, ki=ki, laf=14.0, fric=0.011))
for kp, (ki, kih) in itertools.product((0.9, 0.8, 0.75), ((0.4, 0.6), (0.4, 0.8), (0.3, 0.8), (0.5, 0.8))):
    forks.append(dict(name="L14_Kp%.2f_Ki%.2f_%.1f" % (kp, ki, kih), kp=kp, ki=ki, ki_high=kih, laf=14.0, fric=0.011))
forks += [dict(name="L14_Kp0.80_Ki0.40_0.8_F0.008", kp=0.8, ki=0.4, ki_high=0.8, fric=0.008),
          dict(name="L14_Kp0.90_Ki0.50_0.0_F0.008", kp=0.9, ki=0.5, fric=0.008),
          dict(name="L14_Kp0.75_Ki0.30_0.6_F0.008", kp=0.75, ki=0.3, ki_high=0.6, fric=0.008),
          dict(name="L13.5_Kp0.80_Ki0.50_0.0", kp=0.8, ki=0.5, laf=13.5),
          dict(name="L13.5_Kp0.80_Ki0.40_0.6", kp=0.8, ki=0.4, ki_high=0.6, laf=13.5)]
json.dump(dict(forks=forks, members=["nominal", "b_lo", "F_hi", "light_b"]), open("out/s3_spec.json", "w"), indent=1)
print(len(forks), "candidates")
