"""Independent re-derivation of F1's breakaway-band fit, from the cached per-route ss npz files.
Does NOT import ss_centring_fit.py or ss_load.py's load_all; re-implements from scratch to cross-check.
"""
import glob, numpy as np

OUTDIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip/out'
CH = ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'ad', 'angdes', 'sr', 'v')
PRE = 150

EP = []
W = {k: [] for k in CH}
for f in sorted(glob.glob(OUTDIR + '/*_ss.npz')):
    D = np.load(f, allow_pickle=True)
    ep = list(D['EP'])
    EP += ep
    for k in CH:
        if len(ep):
            W[k].append(D[k])
W = {k: np.concatenate(v) for k, v in W.items()}
N = len(EP)
ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route')
d0 = np.maximum(col('w_d0'), 0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])

# independent redefinition of 'toward' — using sign at breakaway frame (index PRE)
aa_bk = W['aa'][ar, PRE]
toward = (sj == -np.sign(aa_bk)).astype(float)

BKIDX = PRE - 3  # 30 ms before breakaway


def fit_ols(m, idx):
    X = np.column_stack([W['aa'][ar, idx][m], sj[m], (sj * toward)[m], np.ones(m.sum())])
    y = W['cmd'][ar, idx][m]
    # normal-equations solve, independent of np.linalg.lstsq path
    XtX = X.T @ X
    Xty = X.T @ y
    c = np.linalg.solve(XtX, Xty)
    resid = y - X @ c
    return c, resid


def cluster_bootstrap(m, idx, nb=3000, seed=12345):
    u = np.unique(route[m])
    rng = np.random.default_rng(seed)
    ests = []
    for _ in range(nb):
        pick = rng.choice(u, len(u), replace=True)
        mm = np.zeros(N, bool)
        for cl in pick:
            mm |= m & (route == cl)
        c, _ = fit_ols(mm, idx)
        away = c[1]; tow = c[1] + c[2]; hw = c[1] + c[2] / 2; cen = -c[2] / 2
        ests.append([away, tow, hw, cen])
    return np.array(ests)


print(f"{'bin':16s} {'when':12s} {'n':>4s} {'away':>8s} {'toward':>8s} {'halfwidth':>10s} {'centring':>9s}")
for lo, hi in [(2, 8), (8, 15)]:
    for when, idx in (('breakaway', np.full(N, BKIDX)), ('dwell_start', d0)):
        m = TQ & (v >= lo) & (v < hi)
        c, resid = fit_ols(m, idx)
        away = c[1]; tow = c[1] + c[2]; hw = c[1] + c[2] / 2; cen = -c[2] / 2
        bs = cluster_bootstrap(m, idx)
        cis = np.percentile(bs, [2.5, 97.5], axis=0)
        print(f"{lo}-{hi:<12} {when:12s} {int(m.sum()):4d} "
              f"{away:8.4f} {tow:8.4f} {hw:10.4f} {cen:9.4f}")
        print(f"   CIs: away={cis[:,0].round(4).tolist()} toward={cis[:,1].round(4).tolist()} "
              f"halfwidth={cis[:,2].round(4).tolist()} centring={cis[:,3].round(4).tolist()}")
        print(f"   n_toward={int(toward[m].sum())}  resid_rms={np.sqrt(np.mean(resid**2)):.4f}")

# net_swing check for reversal episodes (independent recompute)
print()
print("--- net_swing (reversal-kind, cmd*sj change from dwell start to 30ms-before-breakaway) ---")
kind = col('kind')
A = lambda k, idx: W[k][ar, idx] * sj
d1 = col('w_d1')
for lo, hi in [(2, 8), (8, 15)]:
    m = TQ & (v >= lo) & (v < hi) & (kind == 'rev')
    net0 = (A('cmd', d0) - A('hold_aa', d0))[m]
    net1 = (A('cmd', np.full(N, BKIDX)) - A('hold_aa', np.full(N, BKIDX)))[m]
    swing = net1 - net0
    u = np.unique(route[m])
    rng = np.random.default_rng(777)
    bs = []
    for _ in range(3000):
        pick = rng.choice(u, len(u), replace=True)
        mm = np.concatenate([np.where(route[m] == c)[0] for c in pick])
        bs.append(np.median(swing[mm]))
    ci = np.percentile(bs, [2.5, 97.5])
    print(f"{lo}-{hi}: n={m.sum()} median={np.median(swing):.4f} CI=[{ci[0]:.4f},{ci[1]:.4f}]")
