# -*- coding: utf-8 -*-
"""f4b: write the stage-2 candidate spec (out/s2_spec.json) for f4_sweep.py."""
import json, itertools

forks = []
for kp, (ki, kih), fr in itertools.product((0.9, 0.75, 0.6), ((0.3, 0.6), (0.3, 1.0), (0.4, 1.0), (0.3, 1.5), (0.45, 0.0)),
                                           (0.011, 0.005)):
    forks.append(dict(name="L14_Kp%.2f_Ki%.2f_%.1f_F%.3f" % (kp, ki, kih, fr), kp=kp, ki=ki, ki_high=kih, laf=14.0, fric=fr))
for kp, (ki, kih) in itertools.product((0.9, 0.8), ((0.3, 1.0), (0.4, 0.0))):
    forks.append(dict(name="L13.5_Kp%.2f_Ki%.2f_%.1f_F0.011" % (kp, ki, kih), kp=kp, ki=ki, ki_high=kih, laf=13.5, fric=0.011))
for fr in (0.0, 0.005, 0.016):
    forks.append(dict(name="r1_F%.3f" % fr, fric=fr))
forks.append(dict(name="L14_Kp0.90_Ki0.50_0.0_F0.011", ki=0.5))
json.dump(dict(forks=forks, members=["nominal", "b_lo", "F_hi", "light_b"]), open("out/s2_spec.json", "w"), indent=1)
print(len(forks), "candidates")
