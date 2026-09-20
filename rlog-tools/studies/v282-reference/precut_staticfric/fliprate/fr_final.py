"""fliprate stage 4: the recommended variant, scored PER SPEED BIN (the pooled v<12 number in fr_sweep is
dominated by the 8-12 exposure and hides the 2-5 m/s cost), plus absolute band RMS in every band of record
and the DOB-surviving version of each.  Variants: the design point, three z_out post-filter RCs, and the
best stateless alternative.
"""
import sys, json
import numpy as np
from fr_lib import *

TORQUE = [k for k, mv in V.ROUTES.items() if mv['eps'] == 'V293']
VB = [(0, 2), (2, 5), (5, 8), (8, 12)]
VAR = {'design A1 R2': (1.0, 2.0, 0.0),
       'A1 R2 + zout 0.10': (1.0, 2.0, 0.10),
       'A1 R2 + zout 0.15': (1.0, 2.0, 0.15),
       'A1 R2 + zout 0.20': (1.0, 2.0, 0.20),
       'A1 R2 + zout 0.30': (1.0, 2.0, 0.30),
       'A2 R4 stateless': (2.0, 4.0, 0.0)}
BANDS = dict(shake=(1.8, 3.5), relay=(4.0, 4.7), plant=(15.0, 22.0))


def main(rks):
    acc = {}
    for rk in rks:
        R = prep(rk)
        v = R['v']; t = R['t']; cmd = R['cmd']
        for nm, (a_s, r_s, zrc) in VAR.items():
            z = z_out_of(R['angdes'], R['rate_des'], v, a_scale=a_s, r_scale=r_s)
            if zrc > 0:
                z = fo_filter(z, zrc, reset=~R['act'])
            du, _ = dob_perturbation(z, v)
            for lo, hi in VB:
                m = R['HO'] & (v >= lo) & (v < hi)
                sub = V.runs(m, t, min_s=2.56)
                if not sub:
                    continue
                w = np.array([b - a for a, b in sub], float)
                fr, Pz, _ = psd_sum([z[a:b] for a, b in sub])
                _, Pu, _ = psd_sum([du[a:b] for a, b in sub])
                _, Pc, _ = psd_sum([cmd[a:b] for a, b in sub])
                _, Pcz, _ = psd_sum([(cmd + z)[a:b] for a, b in sub])
                _, Pcu, _ = psd_sum([(cmd + du)[a:b] for a, b in sub])
                dz = np.concatenate([np.abs(np.diff(z[a:b])) * FS for a, b in sub])
                row = dict(sec=round(float(w.sum() / FS), 1),
                           dz_p99=round(float(np.percentile(dz, 99)), 4), dz_max=round(float(np.max(dz)), 4),
                           z_absmean=round(float(np.average([np.mean(np.abs(z[a:b])) for a, b in sub], weights=w)), 5),
                           du_absmean=round(float(np.average([np.mean(np.abs(du[a:b])) for a, b in sub], weights=w)), 5))
                for bn, (f1, f2) in BANDS.items():
                    row[f'z_{bn}'] = round(float(np.sqrt(band_power(fr, Pz, f1, f2))), 6)
                    row[f'du_{bn}'] = round(float(np.sqrt(band_power(fr, Pu, f1, f2))), 6)
                    row[f'cmd_{bn}'] = round(float(np.sqrt(band_power(fr, Pc, f1, f2))), 6)
                    row[f'bandx_{bn}'] = round(float(np.sqrt(band_power(fr, Pcz, f1, f2)
                                                            / max(band_power(fr, Pc, f1, f2), 1e-30))), 4)
                    row[f'bandxdu_{bn}'] = round(float(np.sqrt(band_power(fr, Pcu, f1, f2)
                                                              / max(band_power(fr, Pc, f1, f2), 1e-30))), 4)
                acc.setdefault(nm, {}).setdefault(f'{lo}-{hi}', {})[rk] = row
        print('done', rk, flush=True)
        del R
    return acc


if __name__ == '__main__':
    acc = main(sys.argv[1:] or TORQUE)
    with open(f'{OUT}/fr_final.json', 'w') as f:
        json.dump(acc, f, indent=1)
    for nm, byb in acc.items():
        print(f"\n=== {nm}")
        print(f"  {'bin':6s} {'sec':>6s} {'z_shake':>8s} {'du_shake':>8s} {'cmd_shake':>9s} {'bandx_shake':>11s} "
              f"{'bandx(du)':>9s} {'bandx_relay':>11s} {'bandx_plant':>11s} {'dz_p99':>7s} {'dz_max':>7s} {'|z|mean':>8s} {'|du|mean':>8s}")
        for bn, per in byb.items():
            w = np.array([r['sec'] for r in per.values()], float)
            g = lambda k: float(np.average([r[k] for r in per.values()], weights=w))
            mn = lambda k: min(r[k] for r in per.values()); mx = lambda k: max(r[k] for r in per.values())
            print(f"  {bn:6s} {w.sum():6.0f} {g('z_shake'):8.5f} {g('du_shake'):8.5f} {g('cmd_shake'):9.5f} "
                  f"{g('bandx_shake'):6.3f}[{mn('bandx_shake'):.2f},{mx('bandx_shake'):.2f}] {g('bandxdu_shake'):9.3f} "
                  f"{g('bandx_relay'):11.3f} {g('bandx_plant'):11.3f} {g('dz_p99'):7.4f} {mx('dz_max'):7.4f} "
                  f"{g('z_absmean'):8.5f} {g('du_absmean'):8.5f}")
