"""classifier stage 6: READ the episodes.  (a) who carries R:return's os30_p90 = 3.203, and which cell of the
E/R/T confusion they sit in; (b) trace dumps for the four disagreement classes."""
import os, json, glob
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
PRE = 150
LEVEL = 0.020
rows = json.load(open(f'{OUT}/c1_rows.json'))
key = {(r['route'], r['i0'], r['bk']): q for q, r in enumerate(rows)}
N = len(rows)
os30 = np.full(N, np.nan)
WIN = {}
for f in sorted(glob.glob(f'{SS}/out/*_ss.npz')):
    D = np.load(f, allow_pickle=True); EP = list(D['EP'])
    if not EP:
        continue
    for q, e in enumerate(EP):
        kk = (e['route'], int(e['i0']), int(e['bk']))
        if kk in key:
            i = key[kk]
            os30[i] = float(e['sjump']) * (D['aa'][q, PRE + 30] - D['ad'][q, PRE + 30])
            WIN[i] = dict(aa=D['aa'][q].copy(), ad=D['ad'][q].copy(), angdes=D['angdes'][q].copy(),
                          cmd=D['cmd'][q].copy(), sr=D['sr'][q].copy(), holdaa=D['hold_aa'][q].copy())
    del D

col = lambda k: np.array([r[k] for r in rows])
colf = lambda k: col(k).astype(float)
v = colf('v'); aa_bk = colf('aa_bk'); sj = colf('sj'); sdem = colf('sdem'); dwell = colf('dwell_s')
route = col('route'); kind = col('kind'); slip = colf('slip')
ang_bk = colf('angdes_bk_A'); gate = colf('gate_bk_A') > 1e-3; dose = colf('dose_bk_A')
dose_out = colf('dose_out_A'); zc = colf('zc_A'); rd = colf('rd_bk_A')
sgn_aa = np.sign(aa_bk)
depE = sj == sgn_aa; depR = (sgn_aa == sdem) | (np.abs(aa_bk) < 0.5)
LOW = (v >= 2) & (v < 8)
cell = np.array(['%s%s|%s' % ('E' if depE[i] else 'e', 'R' if depR[i] else 'r', 'T' if gate[i] else 't')
                 for i in range(N)])   # UPPER = depart / fires

m = LOW & ~depR
ii = np.where(m)[0]
o = os30[ii]
thr = np.percentile(o, 90)
top = ii[o >= thr]
print(f'=== (a) R:return, n={len(ii)}, os30_p90 = {thr:.3f}.  The {len(top)} episodes at/above it ===')
print(f'{"route":10s}{"idx":>6s}{"v":>6s}{"aa_bk":>8s}{"angdes":>8s}{"sj":>4s}{"sdem":>6s}{"kind":>6s}'
      f'{"dwell":>7s}{"os30":>8s}{"slip":>7s}{"dose":>8s}{"cell":>8s}')
for i in top[np.argsort(-os30[top])]:
    print(f'{rows[i]["route"][-10:]:10s}{i:6d}{v[i]:6.2f}{aa_bk[i]:8.2f}{ang_bk[i]:8.2f}{sj[i]:4.0f}{sdem[i]:6.0f}'
          f'{kind[i]:>6s}{dwell[i]:7.2f}{os30[i]:8.2f}{slip[i]:7.2f}{dose[i]:8.4f}{cell[i]:>8s}')
from collections import Counter
print('cell census of the top decile:', Counter(cell[top]))
print('cell census of the whole R:return class:', Counter(cell[ii]))

CLS = {'Eret_Tfires (demand crossed centre)': LOW & ~depE & gate,
       'Edep_Tsilent (wheel departed, demand did not)': LOW & depE & ~gate,
       'Eret_Rdep (R near-centre override)': LOW & ~depE & depR,
       'Edep_Rret (wheel out, demand in)': LOW & depE & ~depR}
print('\n=== (b) TRACES.  columns are frames relative to breakaway; all in deg / torque, NOT sign-aligned ===')
for nm, mm in CLS.items():
    idxs = np.where(mm)[0]
    order = idxs[np.argsort(-np.abs(os30[idxs]))][:3]
    print(f'\n--- {nm}   n={len(idxs)} ---')
    for i in order:
        W = WIN[i]; r = rows[i]
        d0 = max(r['w_d0'] if 'w_d0' in r else 0, 0)
        print(f'  {r["route"][-10:]} v={v[i]:.1f} aa_bk={aa_bk[i]:+.2f} angdes_bk={ang_bk[i]:+.2f} '
              f'sj={sj[i]:+.0f} sdem={sdem[i]:+.0f} kind={kind[i]} dwell={dwell[i]:.2f}s os30={os30[i]:+.2f} '
              f'dose={dose[i]:+.4f} dose_out={dose_out[i]:+.4f} zc={zc[i]:.0f} rd={rd[i]:+.2f}')
        for off in (-100, -60, -30, -10, 0, 10, 20, 30, 50, 70):
            j = PRE + off
            print(f'      t{off:+5d}  aa {W["aa"][j]:+7.2f}  angdes {W["angdes"][j]:+7.2f}  ad {W["ad"][j]:+7.2f}'
                  f'  cmd {W["cmd"][j]:+7.4f}  hold(aa) {W["holdaa"][j]:+7.4f}  sr {W["sr"][j]:+7.1f}')
