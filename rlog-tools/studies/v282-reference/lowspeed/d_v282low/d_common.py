import sys, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
from d_extract import BLK_COLS, EV_COLS, HERE
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
def load_all():
    R = {}
    for rk, m in V.ROUTES.items():
        D = np.load(f'{HERE}/data/{rk}.npz')
        R[rk] = dict(group=m['group'], BLK=D['BLK'], EV=D['EV'], DJ=D['DJ'], RUNS=D['RUNS'], RUNLEN=D['RUNLEN'], ld=float(D['ld']))
    return R
def split_runs(r):
    out, o = [], 0
    for n in r['RUNLEN']:
        out.append(r['RUNS'][:, o:o + n]); o += n
    return out
B = {c: i for i, c in enumerate(BLK_COLS)}
E = {c: i for i, c in enumerate(EV_COLS)}
