"""risk stream, stage 3: the SAME candidates on the real logged dwell episodes.

STRUCTURAL REACH only: how much of the MEASURED shortfall (0.033 of torque still missing at release,
<8 m/s) each candidate's z would have supplied during that episode's own dwell -- nothing about the
resulting band gain or dwell length.

Episode indices come from lowspeed/a_stickslip/out/<route>_ss.npz (EP: i0 dwell start, i1 dwell end,
bk breakaway), on the same V.load timebase as risk/out/<route>_z.npz, so z_cand can be indexed directly.
"""
import os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip/out'
CAND = ['C0_flown', 'C1_toggle_030', 'C2_lvl033_k12', 'C3_band110', 'C4_reach_k12', 'C5_half_k12', 'C6_reach_k68']
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
SHORTFALL = 0.033          # measured, <8 m/s: the command sits this far short of release when the wheel stops

rows = []
for rk in ROUTES:
    E = np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)['EP']
    D = np.load(f'{OUT}/{rk}_z.npz')
    Z = {c: D[c] for c in CAND}
    aa_all = D['aa']
    for ep in E:
        i0, i1, bk = ep['i0'], ep['i1'], ep['bk']
        s = ep['sdem']                                    # sign of the demand's motion through the dwell
        depart = (np.sign(ep['aa']) == s) or abs(ep['aa']) < 0.5
        r = dict(route=rk, v=ep['v'], dwell_s=ep['dwell_s'], abs_aa=ep['abs_aa'], kind=ep['kind'],
                 depart=bool(depart), dem=ep['dem'], j30=ep['j30'], slip=ep['slip'], pk_rate=ep['pk_rate'])
        for c in CAND:
            z = Z[c]
            r[f'{c}_z0'] = float(s * z[i0]); r[f'{c}_zbk'] = float(s * z[bk])
            r[f'{c}_dz'] = float(s * (z[bk] - z[i0]))
        rows.append(r)
    del D, Z

res = {}
print(f'{"grp":10s}{"cand":15s}{"n":>5s}{"z_at_bk_p50":>12s}{"dz_dwell_p50":>13s}{"reach%":>8s}{"reach%_p90":>11s}')
for gname, sel in [('2-8 depart', lambda r: r['v'] < 8 and r['depart']),
                   ('2-8 return', lambda r: r['v'] < 8 and not r['depart']),
                   ('2-8 all', lambda r: r['v'] < 8),
                   ('8-15 all', lambda r: 8 <= r['v'] < 15)]:
    R = [r for r in rows if sel(r)]
    if len(R) < 5:
        continue
    for c in CAND:
        zbk = np.array([r[f'{c}_zbk'] for r in R]); dz = np.array([r[f'{c}_dz'] for r in R])
        row = dict(n=len(R), zbk_p50=float(np.median(zbk)), dz_p50=float(np.median(dz)),
                   reach_p50=float(100 * np.median(dz) / SHORTFALL), reach_p90=float(100 * np.percentile(dz, 90) / SHORTFALL),
                   zbk_p90=float(np.percentile(zbk, 90)))
        res[f'{gname}|{c}'] = row
        print(f'{gname:10s}{c:15s}{row["n"]:5d}{row["zbk_p50"]:12.4f}{row["dz_p50"]:13.4f}'
              f'{row["reach_p50"]:8.0f}{row["reach_p90"]:11.0f}')
    print()
json.dump(dict(res=res, n_rows=len(rows)), open(f'{OUT}/r_episodes.json', 'w'), indent=1)
