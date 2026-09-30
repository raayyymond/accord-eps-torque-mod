# -*- coding: utf-8 -*-
"""ADV-A a10: the trim CAP through my mirror (not the golden fb= override): drive a constant wheel ACCELERATION
(x ramps +-40 counts/tick from -+12000; r26's linear target b*40/(1024-a) exceeds 1024 on both builds) and read the
settled trim = T - T(no motion) at idx 0 / 120 / 238, both demand signs, V294 vs V295."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_vec as V  # noqa: E402

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
idxs = [0, 120, 238]
lanes = [(i, ds, sl) for i in idxs for ds in (1, -1) for sl in (40, -40)]
B = len(lanes)
li = np.array([l[0] for l in lanes]); ds = np.array([l[1] for l in lanes]); sl = np.array([l[2] for l in lanes])
for nm in ("v294", "v295"):
    c = J[nm]
    VL = V.VecLane(c, B); V0 = V.VecLane(c, B)
    sp = ds * VL.map_tab[li]
    x0 = np.where(sl > 0, -12000, 12000).astype(np.int64)
    for _ in range(3000):
        VL.tick(x0, sp, li); T0 = V0.tick(np.zeros(B, np.int64), sp, li)
    trims = []
    for k in range(600):
        x = x0 + sl * k
        T = VL.tick(x, sp, li)
        if k >= 400:
            trims.append(T - T0)
    trims = np.array(trims)
    print("%s: r26 at the end %s" % (nm, VL.last["r26"].tolist()))
    for j, l in enumerate(lanes):
        print("   idx %3d demand %+d accel %+d: trim settled %d (min %d max %d over ticks 400-599)"
              % (l[0], l[1], l[2], trims[-1, j], trims[:, j].min(), trims[:, j].max()))
