"""risk stream, stage 2: the ASYMMETRY.  The measured stuck band is NOT centred on the hold map --
it sits ~+0.020 toward the ANGLE's own sign (a_stickslip: release needs +0.053 away from centre,
only +0.014 back toward it, <8 m/s).  The fork's z is odd in the DESIRED-MOTION sign and carries no
angle-signed part, so a symmetric raise buys departures and pays on returns.

Measured here, per candidate, on every engaged hands-off frame where the wheel is sliding:
  AWAY   (sign(sr) == sign(angle))  requirement R_away = 0.053   ->  under-delivery = R - z
  TOWARD (sign(sr) != sign(angle))  requirement R_tow  = 0.014   ->  over-delivery  = z - R
and the extra settled angle that over-delivery buys, deg = over / k'(v) (MEASURED breakaway stiffness).

Also: the candidate's added 1.8-3.5 Hz content as a fraction of the command's own content in that band
(the band the drive is scored on), and the same split for the 8-15 m/s leak.
"""
import sys, os, json
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
CAND = ['C0_flown', 'C1_toggle_030', 'C2_lvl033_k12', 'C3_band110', 'C4_reach_k12', 'C5_half_k12', 'C6_reach_k68']
KP = {'2-5': 0.004767, '5-8': 0.008010, '8-15': 0.006603, '15-22': 0.006603, '22+': 0.006603}
R_AWAY, R_TOW = 0.053, 0.014          # measured, <8 m/s (a_stickslip release asymmetry)
BINS = [('2-5', 2.0, 5.0), ('5-8', 5.0, 8.0), ('2-8', 2.0, 8.0), ('8-15', 8.0, 15.0), ('15-22', 15.0, 22.0)]
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']


def bp(x, f0=1.8, f1=3.5, fs=100.0):
    b, a = signal.butter(2, [f0 / (fs / 2), f1 / (fs / 2)], btype='band')
    return signal.filtfilt(b, a, x)


acc = {}
for rk in ROUTES:
    D = np.load(f'{OUT}/{rk}_z.npz')
    v, HO, aa, srl, cmd = D['v'], D['HO'], D['aa'], D['srl'], D['cmd']
    Z = {c: D[c] for c in CAND}
    ZH = {c: bp(Z[c]) for c in CAND}
    cmdH = bp(np.nan_to_num(cmd))
    for bn, v0, v1 in BINS:
        m = HO & (v >= v0) & (v < v1)
        mov = m & (np.abs(srl) >= 2.0) & (np.abs(aa) >= 0.3)
        if mov.sum() < 50:
            continue
        s = np.sign(srl[mov]); sa = np.sign(aa[mov])
        away = s == sa
        A = acc.setdefault(bn, {c: dict(n_away=0, n_tow=0, und=[], ovr=[], ang=[], zh=[], ch=[]) for c in CAND})
        for c in CAND:
            zs = s * Z[c][mov]                   # z projected on the direction of travel
            e = A[c]
            e['n_away'] += int(away.sum()); e['n_tow'] += int((~away).sum())
            e['und'].append(R_AWAY - zs[away])
            e['ovr'].append(zs[~away] - R_TOW)
            e['ang'].append((zs[~away] - R_TOW) / KP[bn if bn in KP else '8-15'])
            e['zh'].append(ZH[c][m]); e['ch'].append(cmdH[m])
    del D, Z, ZH

print(f'{"bin":6s}{"cand":15s}{"n_away":>7s}{"n_tow":>7s}{"%tow":>6s}'
      f'{"under_away_p50":>15s}{"over_tow_p50":>13s}{"over_tow_p90":>13s}{"extra_ang_p50":>14s}{"extra_ang_p90":>14s}'
      f'{"zHF":>9s}{"cmdHF":>9s}{"zHF/cmdHF":>10s}')
res = {}
for bn, A in acc.items():
    for c in CAND:
        e = A[c]
        und = np.concatenate(e['und']); ovr = np.concatenate(e['ovr']); ang = np.concatenate(e['ang'])
        zh = np.concatenate(e['zh']); ch = np.concatenate(e['ch'])
        row = dict(n_away=e['n_away'], n_tow=e['n_tow'], pct_tow=100 * e['n_tow'] / (e['n_away'] + e['n_tow']),
                   under_away_p50=float(np.median(und)), over_tow_p50=float(np.median(ovr)),
                   over_tow_p90=float(np.percentile(ovr, 90)),
                   over_tow_frac_pos=float(np.mean(ovr > 0)),
                   extra_ang_p50=float(np.median(ang)), extra_ang_p90=float(np.percentile(ang, 90)),
                   zHF=float(np.sqrt(np.mean(zh ** 2))), cmdHF=float(np.sqrt(np.mean(ch ** 2))))
        row['zHF_over_cmdHF'] = row['zHF'] / row['cmdHF']
        res[f'{bn}|{c}'] = row
        print(f'{bn:6s}{c:15s}{row["n_away"]:7d}{row["n_tow"]:7d}{row["pct_tow"]:6.0f}'
              f'{row["under_away_p50"]:15.4f}{row["over_tow_p50"]:13.4f}{row["over_tow_p90"]:13.4f}'
              f'{row["extra_ang_p50"]:14.2f}{row["extra_ang_p90"]:14.2f}'
              f'{row["zHF"]:9.5f}{row["cmdHF"]:9.5f}{row["zHF_over_cmdHF"]:10.3f}')
    print()
json.dump(res, open(f'{OUT}/r_direction.json', 'w'), indent=1)
