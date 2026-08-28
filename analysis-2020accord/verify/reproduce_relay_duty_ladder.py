# -*- coding: utf-8 -*-
"""Reproduce the MEASURED relay-saturation duty ladder, then extend it to knee 3000.

The ladder in build_v112_tva.py is defined as: route 21 (the V111 drive), 5-10 mph,
engaged, hands-off, |cmd| >= 2048, n = 289 frames. Published values:

    600 -> 0.7439   1200 -> 0.4810   1800 -> 0.2353   2400 -> 0.0484   3600 -> 0.0000

I inserted 3000 -> 0.0370 into build_v121_tva.py by eyeballing that series. It was NEVER
measured, and the table it sits in is labelled "MEASURED". Reproduce the published values
first -- if the gate reconstruction is right they will come back exactly -- then compute
knee 3000 on the same gate.

The relay saturates when |gp-0x6abc| >= knee/12, and gp-0x6abc = 4.7121 ct/(deg/s), so on
the wire the condition is |rate| >= knee / (12 * 4.7121) deg/s. The 427 tap (raw14_b4) IS
gp-0x6abc at sar 3 on this build; cs_rate is the same quantity from `ang`. Try both.
"""
import numpy as np

CT = 4.7121
PUB = {600: 0.7439, 1200: 0.4810, 1800: 0.2353, 2400: 0.0484, 3600: 0.0000}
z = np.load('analysis-2020accord/_scratch/cache/r21/r21.npz', allow_pickle=True)
G = lambda k: np.asarray(z[k]).astype(float)
v, lat, press, rate = G('cs_v'), G('cc_lat'), G('cs_press'), G('cs_rate')
cmd = G('co_tqcan') if 'co_tqcan' in z.files else G('cc_req')

MPH = 0.44704
gate = (v >= 5 * MPH) & (v <= 10 * MPH) & (lat > 0.5) & (press < 0.5) & (np.abs(cmd) >= 2048)
print("gate: 5-10 mph, engaged, hands-off, |cmd| >= 2048   ->  n = %d frames  (published n = 289)"
      % gate.sum())

for src_name, src in (('cs_rate (from ang)', np.abs(rate)),
                      ('raw14_b4 tap, sar 3', np.abs(G('raw14_b4')) * 8 / CT if 'raw14_b4' in z.files else None)):
    if src is None:
        continue
    print("\n  source: %s" % src_name)
    print("    knee   sat rate     duty      published    delta")
    ok = 0
    for k in sorted(PUB):
        sat = k / (12 * CT)
        d = (src[gate] >= sat).mean() if gate.sum() else np.nan
        dd = d - PUB[k]
        ok += abs(dd) < 0.02
        print("    %5d   %7.1f    %.4f     %.4f     %+.4f%s"
              % (k, sat, d, PUB[k], dd, '   OK' if abs(dd) < 0.02 else ''))
    print("    reproduced %d/%d published values within 0.02" % (ok, len(PUB)))
    if ok >= 4:
        sat = 3000 / (12 * CT)
        d = (src[gate] >= sat).mean()
        print("\n    ==> knee 3000 (V121): sat rate %.1f deg/s   MEASURED duty %.4f" % (sat, d))
        n = gate.sum()
        rng = np.random.default_rng(0)
        bs = [(src[gate][rng.integers(0, n, n)] >= sat).mean() for _ in range(4000)]
        print("        bootstrap 95%% CI [%.4f, %.4f]   (n = %d)"
              % (np.percentile(bs, 2.5), np.percentile(bs, 97.5), n))
