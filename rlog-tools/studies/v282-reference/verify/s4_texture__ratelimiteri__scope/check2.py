import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
GROUPS = ['V282', 'T64', 'T64B', 'T5', 'T4']
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}

for g in GROUPS:
    FR = []
    for rk in routes[g]:
        D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
        FR.append(D['FR'])
    F = np.concatenate(FR, axis=1)
    v, ang, de4 = F[0], F[1], F[2]
    # pooled v0-15, split angle finely at the top end
    m0 = (v < 15)
    for a0,a1 in [(45,90),(90,180),(180,999)]:
        m = m0 & (ang>=a0)&(ang<a1)
        n = int(m.sum())
        if n==0:
            print(g, f'a{a0}-{a1}', 'n=0'); continue
        print(g, f'v0-15 a{a0}-{a1}', 'n=', n, 'pct>=120', round(100*np.mean(de4[m]>=120),3), 'max_ang', round(float(ang[m].max()),1))
    # combined 45+ check vs original
    m = m0 & (ang>=45)
    print(g, 'v0-15 a45+ COMBINED n=', int(m.sum()), 'pct>=120', round(100*np.mean(de4[m]>=120),4))
