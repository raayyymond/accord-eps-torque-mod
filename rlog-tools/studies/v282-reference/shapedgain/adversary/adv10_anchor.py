# -*- coding: utf-8 -*-
"""ADV10: put the SAFETY ANCHOR on the same footing as the dose.

ADV8 priced the dose on high-demand windows because that is where r71's limit cycle lived ('hard
curves above 20 m/s').  But the 0.46 anchor the programme quotes for r71 is a POOLED number.  Comparing
a high-amplitude dose against a pooled anchor is the same pooling error this stream is objecting to,
so r71 (and r72, the 'flew fine' anchor) are re-identified here on THEIR OWN high-amplitude windows,
and at the limit cycle's own frequency, 2.34 Hz.
"""
import sys

import numpy as np

import advlib as A
from adv4_loop import C_of, NPS, SHAKE
from adv7_verdict import pack

ANCH = {"00000071--f2c9d073a3": "r71  LIMIT-CYCLED at 2.34 Hz",
        "00000072--8001fc3048": "r72  flew, no shake complaint",
        "0000006c--68c6e94b17": "r6c  rev 6.4 as flown",
        "0000006d--05e83bb04f": "r6d  rev 6.4 as flown"}
LC = (2.0, 2.7)          # around the 2.34 Hz limit cycle


def main():
    print("SHAKE-BAND AND LIMIT-CYCLE-BAND LOOP GAIN, POOLED vs HIGH-DEMAND, PER FLOWN ANCHOR")
    print(f"  {'route':>36s} {'n':>4s} {'|L|shk pool':>12s} {'|L|shk hi':>10s} {'|L|@2.0-2.7 pool':>17s} "
          f"{'hi':>7s} {'Ms pool':>8s} {'Ms hi':>7s}")
    res = {}
    for rk, lab in ANCH.items():
        fr, sp, vs, rkl, am = pack([rk], NPS)
        X, M, U = sp["X"], sp["M"], sp["U"]
        sel = A.bandsel(fr)
        ssh = (fr >= SHAKE[0]) & (fr < SHAKE[1])
        slc = (fr >= LC[0]) & (fr < LC[1])
        hi = am > np.percentile(am, 66.7)
        meta = A.FLOWN[rk]
        vals = []
        for nm, msk in (("pool", np.ones(len(am), bool)), ("hi", hi)):
            P = np.sum(np.conj(X[msk]) * M[msk], 0) / np.sum(np.conj(X[msk]) * U[msk], 0)
            Cw = np.array([C_of(fr, v, meta) for v in vs[msk]])
            L = P[None, :] * Cw
            w = np.abs(X[msk]) ** 2
            vals.append((float(np.average(np.abs(L[:, ssh]), weights=w[:, ssh])),
                         float(np.average(np.abs(L[:, slc]), weights=w[:, slc])),
                         float(np.max(np.abs(1 / (1 + L))[:, sel]))))
        (lsp, lcp, msp), (lsh, lch, msh) = vals
        res[rk] = dict(lsp=lsp, lsh=lsh, lcp=lcp, lch=lch, msp=msp, msh=msh)
        print(f"  {lab:>36s} {len(vs):4d} {lsp:12.3f} {lsh:10.3f} {lcp:17.3f} {lch:7.3f} {msp:8.2f} {msh:7.2f}")
        del sp, X, M, U

    r71, r72 = res["00000071--f2c9d073a3"], res["00000072--8001fc3048"]
    t64 = np.mean([[res[k]["lsh"], res[k]["lch"], res[k]["msh"]] for k in
                   ("0000006c--68c6e94b17", "0000006d--05e83bb04f")], axis=0)
    print("\n  APPLES TO APPLES, high-demand windows only:")
    print(f"    r71 (limit-cycled): shake |L| {r71['lsh']:.3f}, 2.0-2.7 Hz |L| {r71['lch']:.3f}, Ms {r71['msh']:.2f}")
    print(f"    r72 (flew fine)   : shake |L| {r72['lsh']:.3f}, 2.0-2.7 Hz |L| {r72['lch']:.3f}, Ms {r72['msh']:.2f}")
    print(f"    rev 6.4 as flown  : shake |L| {t64[0]:.3f}, 2.0-2.7 Hz |L| {t64[1]:.3f}, Ms {t64[2]:.2f}")
    if r72["lsh"] > r71["lsh"]:
        print("\n  *** THE ANCHORS INVERT.  On this stream's own identification the route that FLEW FINE (r72)")
        print("     carries the HIGHER shake-band loop gain, and the route that LIMIT-CYCLED carries the lower.")
        print("     Whatever separated r71 from r72 on the car, band-averaged |L| is not it -- so an envelope")
        print("     argument of the form 'the new dose lands between r71 and r72' is not measuring the hazard.")
    print(f"\n  scale of the dose multiplier needed to take rev 6.4 to each anchor (high-demand, shake band):")
    for nm, v in (("r71", r71["lsh"]), ("r72", r72["lsh"])):
        print(f"    to {nm}: x{v/t64[0]:.2f} on the P path  -> SteerKP {v/t64[0]:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
