import sys
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip")
from ss_load import load_all
import numpy as np

EP, W, EX, VAL = load_all()
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); route = col('route'); aa_abs = col('abs_aa')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
m = TQ & (v>=2)&(v<8) & (aa_abs>=5)
print("n=", m.sum())
rk,cnt = np.unique(route[m], return_counts=True)
print(dict(zip(rk,cnt)))
