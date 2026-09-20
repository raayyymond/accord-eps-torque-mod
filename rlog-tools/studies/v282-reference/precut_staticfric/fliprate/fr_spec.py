"""fliprate stage 3: WHERE in frequency does z_out put its energy, and is there a LINE anywhere the kit
already has a mode?  Bands of record: 1.8-3.5 Hz (the shake the drive is scored on), 4.0-4.7 Hz (the
SteerFriction relay's route-73 chatter), 2.0-2.7 Hz (the closed-loop wheel mode), 15-22 Hz (the plant mode).
Also: the |angle_des| distribution, because s_a = tanh(angle_des / 1.0 deg) SATURATES and the design's
'soft near centre' s_a^2 factor only exists while |angle_des| is of order 1 deg.
"""
import sys, json
import numpy as np
from fr_lib import *

TORQUE = [k for k, mv in V.ROUTES.items() if mv['eps'] == 'V293']
LINES = dict(wheelmode=(2.0, 2.7), shake=(1.8, 3.5), relay=(4.0, 4.7), plant=(15.0, 22.0))


def one(rk):
    R = prep(rk)
    v = R['v']; t = R['t']
    z = z_out_of(R['angdes'], R['rate_des'], v)
    du, _ = dob_perturbation(z, v)
    out = dict(route=rk, group=R['group'], bins={})
    for lo, hi in [(0, 2), (2, 5), (5, 8), (8, 12)]:
        m = R['HO'] & (v >= lo) & (v < hi)
        sub = V.runs(m, t, min_s=5.12)
        if not sub:
            continue
        sec = sum(b - a for a, b in sub) / FS
        fr, Pz, _ = psd_sum([z[a:b] for a, b in sub], nps_max=2048)
        _, Pu, _ = psd_sum([du[a:b] for a, b in sub], nps_max=2048)
        _, Pc, _ = psd_sum([R['cmd'][a:b] for a, b in sub], nps_max=2048)
        tot = band_power(fr, Pz, 0.02, 40.0)
        row = dict(sec=round(sec, 1), df=round(float(fr[1] - fr[0]), 3))
        # octave-ish census of z_out's own energy
        for f1, f2 in [(0.02, 0.3), (0.3, 0.6), (0.6, 1.2), (1.2, 1.8), (1.8, 2.5), (2.5, 3.5),
                       (3.5, 5.0), (5.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 40.0)]:
            row[f'{f1}-{f2}'] = round(band_power(fr, Pz, f1, f2) / max(tot, 1e-30), 4)
        # is there a LINE?  peak-to-local-median ratio of z_out's PSD inside each band of record
        for nm, (f1, f2) in LINES.items():
            s = (fr >= f1) & (fr < f2)
            wide = (fr >= max(f1 - 3, 0.1)) & (fr < f2 + 3)
            row[f'line_{nm}'] = round(float(np.max(Pz[s]) / max(np.median(Pz[wide]), 1e-40)), 2)
            row[f'zrms_{nm}'] = round(float(np.sqrt(band_power(fr, Pz, f1, f2))), 6)
            row[f'durms_{nm}'] = round(float(np.sqrt(band_power(fr, Pu, f1, f2))), 6)
            row[f'cmdrms_{nm}'] = round(float(np.sqrt(band_power(fr, Pc, f1, f2))), 6)
            row[f'frac_{nm}'] = round(float(np.sqrt(band_power(fr, Pz, f1, f2) / max(band_power(fr, Pc, f1, f2), 1e-30))), 3)
        # slope: z_out rolls off like the demand rate; report the decade ratio
        row['roll_1to3Hz_dB'] = round(float(10 * np.log10(max(band_power(fr, Pz, 2.5, 3.5), 1e-40)
                                                         / max(band_power(fr, Pz, 0.8, 1.8), 1e-40))), 1)
        # --- angle_des distribution: how often is s_a saturated? ---
        ad = np.abs(R['angdes'][m])
        sa2 = np.tanh(R['angdes'][m] / A_SCALE) ** 2
        row['absad_p50'] = round(float(np.median(ad)), 2)
        row['absad_p90'] = round(float(np.percentile(ad, 90)), 2)
        row['absad_max'] = round(float(np.max(ad)), 1)
        row['frac_absad_ge2deg'] = round(float(np.mean(ad >= 2.0)), 3)
        row['frac_absad_ge10deg'] = round(float(np.mean(ad >= 10.0)), 3)
        row['sa2_p50'] = round(float(np.median(sa2)), 3)
        row['frac_sa2_ge0p95'] = round(float(np.mean(sa2 >= 0.95)), 3)
        out['bins'][f'{lo}-{hi}'] = row
    del R
    return out


if __name__ == '__main__':
    res = {}
    for rk in (sys.argv[1:] or TORQUE):
        r = one(rk)
        res[rk] = r
        print(f"--- {rk} {r['group']}")
        for bn, row in r['bins'].items():
            print(f"  {bn:5s} {row['sec']:6.1f}s  lines(pk/med): wheel {row['line_wheelmode']:5.2f} shake {row['line_shake']:5.2f} "
                  f"relay {row['line_relay']:5.2f} plant {row['line_plant']:5.2f} | z/cmd in band: shake {row['frac_shake']:.2f} "
                  f"relay {row['frac_relay']:.2f} plant {row['frac_plant']:.2f} | roll 1->3Hz {row['roll_1to3Hz_dB']:+.1f} dB")
            print(f"        |ad| p50 {row['absad_p50']:7.2f} p90 {row['absad_p90']:8.2f} max {row['absad_max']:7.1f} "
                  f"| frac>=2deg {row['frac_absad_ge2deg']:.3f} >=10deg {row['frac_absad_ge10deg']:.3f} "
                  f"| s_a^2 p50 {row['sa2_p50']:.3f} frac>=0.95 {row['frac_sa2_ge0p95']:.3f}")
        print(flush=True)
    with open(f'{OUT}/fr_spec.json', 'w') as f:
        json.dump(res, f, indent=1)
