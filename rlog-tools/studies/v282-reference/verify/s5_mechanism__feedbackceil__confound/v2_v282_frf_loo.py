"""Adversarial re-test: is the s5_01 V282 servo identification (fc 11-16 Hz, d=0.000 -> 'no ceiling, no delay')
dominated by the one route (2bc842dbac, 72% of V282 usable time)? Re-fit the servo model with that route dropped
(routes 64+65 only), per stratum. Loads ONE route at a time (RAM discipline).
"""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
from s5_01_actuator_frf import fit, NPS  # reuse the exact fit() and window size

LOO_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd']  # V282 group minus 2bc842dbac

accs = {st: {} for st in L.STRATA}
for rk in LOO_ROUTES:
    S = L.V.load(rk)
    th = S['sa'] - np.nan_to_num(S['aoff'])
    for st in L.STRATA:
        for a, b in L.stretches(S, st[0], st[1], min_s=2 * NPS / L.FS):
            r = np.nan_to_num(S['model'][a:b]); u = S['out'][a:b]
            L.frf_accumulate(accs[st], r, u, dict(th=th[a:b], rate=S['sr'][a:b]), NPS)
    del S
    print('loaded', rk, flush=True)

out = {}
for st, acc in accs.items():
    if acc.get('sec', 0) < 20:
        out[f'{st[0]:.0f}-{st[1]:.0f}'] = dict(sec=acc.get('sec', 0), note='too short')
        print(st, 'too short', acc.get('sec', 0))
        continue
    R = L.frf_result(acc, 'th')
    f = R['f']; sel = (f >= 0.3) & (f <= 4.0)
    w = (R['coh_ry'] * R['coh_ru'])[sel]
    p, rel = fit(f[sel], R['H_iv'][sel], w, 'servo')
    ps, prel = fit(f[sel], R['H_iv'][sel], w, 'spring')
    out[f'{st[0]:.0f}-{st[1]:.0f}'] = dict(sec=round(acc['sec']), servo=dict(G=p[0], a=p[1], fc=p[2], d=p[3], rel_err=rel),
                                            spring=dict(k=ps[0], b=ps[1], J=ps[2], d=ps[3], rel_err=prel))
    print(f"{st}: sec={acc['sec']:.0f} servo fc={p[2]:.2f} d={p[3]:.3f} a={p[1]:.3f} rel={rel:.3f}  |  spring k={ps[0]:.4f} b={ps[1]:.4f} J={ps[2]:.2e} d={ps[3]:.3f} rel={prel:.3f}")

json.dump(out, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__feedbackceil__confound/v2_v282_frf_loo.json', 'w'), indent=1)
print("\nFOR COMPARISON, the full-V282-group (with 2bc842dbac) fit from s5_01_actuator_frf.json:")
d = json.load(open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/s5_01_actuator_frf.json'))
for st, v in d['V282'].items():
    if 'servo' in v:
        p = v['servo']['p']
        print(f"  {st}: sec={v['sec']} servo fc={p[2]:.2f} d={p[3]:.3f} a={p[1]:.3f} rel={v['servo']['rel_err']:.3f}")
