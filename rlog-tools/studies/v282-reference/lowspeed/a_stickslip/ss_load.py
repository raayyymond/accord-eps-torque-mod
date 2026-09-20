"""Load the per-route episode tables and windows (out/<rk>_ss.npz) into one frame."""
import glob, numpy as np
from sslib import BASE, V
import os
OUT = BASE + '/lowspeed/a_stickslip/out' + os.environ.get('SSOUT', '')
CH = ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'ad', 'angdes', 'sr', 'v')
PRE = 150


def load_all():
    EP, W, EX, VAL = [], {k: [] for k in CH}, {}, {}
    for f in sorted(glob.glob(OUT + '/*_ss.npz')):
        D = np.load(f, allow_pickle=True)
        ep = list(D['EP']); rk = f.split('\\')[-1].split('/')[-1][:-7]
        EX[rk] = D['ex'].item(); VAL[rk] = D['val'].item()
        EP += ep
        for k in CH:
            if len(ep):
                W[k].append(D[k])
    W = {k: np.concatenate(v) for k, v in W.items()}
    return EP, W, EX, VAL


def boot_ci(vals, clusters, fn=np.median, nb=2000, seed=0):
    """Route-cluster bootstrap CI of fn(vals)."""
    vals = np.asarray(vals, float); clusters = np.asarray(clusters)
    u = np.unique(clusters); rng = np.random.default_rng(seed)
    idx = {c: np.where(clusters == c)[0] for c in u}
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[c] for c in pick])
        bs.append(fn(vals[ii]))
    return float(fn(vals)), tuple(np.percentile(bs, [2.5, 97.5]).tolist())


def boot_ci_ev(vals, fn=np.median, nb=2000, seed=0):
    vals = np.asarray(vals, float); rng = np.random.default_rng(seed)
    bs = [fn(vals[rng.integers(0, len(vals), len(vals))]) for _ in range(nb)]
    return float(fn(vals)), tuple(np.percentile(bs, [2.5, 97.5]).tolist())
