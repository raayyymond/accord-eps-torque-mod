# -*- coding: utf-8 -*-
"""ADV-A a4c: the 100 deg/s, 1-tick restart envelope with the polarity flag gp-0x6752 = -1 (the third writer's value;
T = (yr * pol*gain) >> 15 floors the other way), both output-lag ends + boot, V294 vs V295."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_vec as V  # noqa: E402
import a4_restart as R  # noqa: E402

J = R.J
NL = R.NL; li, lds, lrs = R.li, R.lds, R.lrs


def run(c, rate, end, pol, bail_len=1):
    VL = V.VecLane(c, NL)
    x = (lrs * int(round(8 * rate))).astype(np.int64)
    sp = lds * VL.map_tab[li]
    for _ in range(3000):
        VL.tick(x, sp, li, pol=pol)
    S = VL.last["S"].copy(); q = (S * VL.lb) >> 10
    if end in ("lo", "hi"):
        o_new = VL.o.copy()
        for j in range(NL):
            base = int(VL.o[j])
            fx = [o for o in range(base - 200, base + 200) if o == ((int(VL.la) * o) >> 10) + int(q[j])]
            o_new[j] = fx[0] if end == "lo" else fx[-1]
        VL.o = o_new
    for _ in range(300):
        T = VL.tick(x, sp, li, pol=pol)
    T_pre = T.copy()
    pk = np.zeros(NL, np.int64)
    for k in range(bail_len + 1500):
        T = VL.tick(x, sp, li, pol=pol, bail=np.full(NL, k < bail_len))
        pk = np.maximum(pk, np.abs(T - T_pre))
    return pk, T_pre


for pol in (1, -1):
    for nm in ("v294", "v295"):
        pks = [run(J[nm], 100.0, e, pol)[0] for e in ("lo", "hi", "boot")]
        pk = np.maximum.reduce(pks)
        j = int(np.argmax(pk))
        zc = [k for k, l in enumerate(R.lanes) if l[0] == 0]
        print("pol %+d %s: worst %d (idx %d ds %+d rs %+d) ; zero-cmd %d ; lanes > 288: %d"
              % (pol, nm, pk[j], R.lanes[j][0], R.lanes[j][1], R.lanes[j][2], max(pk[zc]), int(np.sum(pk > 288))))
