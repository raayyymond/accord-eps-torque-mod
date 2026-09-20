"""risk stream, stage 5: does the FLOWN config already over-turn on the RETURN half?

The raised-friction risk is that z is odd in the desired-motion sign while the plant's stuck band is
offset toward the ANGLE's sign, so the raise lands hardest on returns toward centre.  This checks the
measured outcome on the same episodes, split depart / return, under the flown config, for both EPS:

  overshoot30 = s * (aa - ad) at breakaway + 0.30 s   (>0 = past the demand, <0 = still behind)
  j30, slip, pk_rate                                  (a_stickslip definitions)

Windows: lowspeed/a_stickslip/out/<route>_ss.npz, breakaway at window index PRE = 150.
"""
import numpy as np, json, os

SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip/out'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
PRE = 150
GRP = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
       '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4',
       '00000064--ce6b0b0ebb': 'V282', '00000065--b9f78988bd': 'V282', '0000006c--2bc842dbac': 'V282'}

rows = []
for rk, g in GRP.items():
    D = np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)
    E = D['EP']; aa = D['aa']; ad = D['ad']
    for n, ep in enumerate(E):
        s = ep['sjump']
        depart = (np.sign(ep['aa']) == ep['sdem']) or abs(ep['aa']) < 0.5
        for dt_, lab in ((30, 'os30'), (70, 'os70')):
            pass
        rows.append(dict(grp=g, eps='V293' if g.startswith(('T4', 'T5', 'T64')) else 'V282', v=float(ep['v']),
                         depart=bool(depart), dwell_s=float(ep['dwell_s']), j30=float(ep['j30']),
                         slip=float(ep['slip']), pk_rate=float(ep['pk_rate']), gap_bk=float(ep['gap_bk']),
                         os30=float(s * (aa[n, PRE + 30] - ad[n, PRE + 30])),
                         os70=float(s * (aa[n, PRE + 70] - ad[n, PRE + 70]))))
    del D

res = {}
print(f'{"eps":6s}{"dir":8s}{"bin":6s}{"n":>5s}{"dwell":>7s}{"gap_bk":>8s}{"j30":>7s}{"slip":>7s}'
      f'{"pk_rate":>9s}{"os30_p50":>10s}{"os30_p90":>10s}{"os70_p50":>10s}{"%past_30":>9s}')
for eps in ('V282', 'V293'):
    for dep, lab in ((True, 'depart'), (False, 'return')):
        for bn, v0, v1 in (('2-8', 2, 8), ('8-15', 8, 15)):
            R = [r for r in rows if r['eps'] == eps and r['depart'] == dep and v0 <= r['v'] < v1]
            if len(R) < 8:
                continue
            g = lambda k: np.array([r[k] for r in R])
            row = dict(n=len(R), dwell=float(np.median(g('dwell_s'))), gap_bk=float(np.median(g('gap_bk'))),
                       j30=float(np.median(g('j30'))), slip=float(np.median(g('slip'))),
                       pk=float(np.median(g('pk_rate'))), os30_p50=float(np.median(g('os30'))),
                       os30_p90=float(np.percentile(g('os30'), 90)), os70_p50=float(np.median(g('os70'))),
                       past30=float(np.mean(g('os30') > 0)))
            res[f'{eps}|{lab}|{bn}'] = row
            print(f'{eps:6s}{lab:8s}{bn:6s}{row["n"]:5d}{row["dwell"]:7.2f}{row["gap_bk"]:8.2f}{row["j30"]:7.2f}'
                  f'{row["slip"]:7.2f}{row["pk"]:9.2f}{row["os30_p50"]:10.2f}{row["os30_p90"]:10.2f}'
                  f'{row["os70_p50"]:10.2f}{100*row["past30"]:9.0f}')
    print()
json.dump(res, open(f'{OUT}/r_overshoot.json', 'w'), indent=1)
