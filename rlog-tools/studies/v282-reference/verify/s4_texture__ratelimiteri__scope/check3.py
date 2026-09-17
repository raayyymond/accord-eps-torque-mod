import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
GROUPS = ['V282', 'T64', 'T64B', 'T5', 'T4']
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}
RB = [(0,5),(5,15),(15,30),(30,60),(60,999)]

for g in GROUPS:
    FR = []
    for rk in routes[g]:
        D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
        FR.append(D['FR'])
    F = np.concatenate(FR, axis=1)
    v, ang, de4, sra = F[0], F[1], F[2], F[4]
    m0 = v < 15
    for r0,r1 in RB:
        m = m0 & (sra>=r0)&(sra<r1)
        n = int(m.sum())
        if n<100: continue
        print(g, f'v0-15 rate{r0}-{r1}deg/s', 'n=', n, 'pct>=120', round(100*np.mean(de4[m]>=120),3))
