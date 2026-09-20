"""ADVERSARY stream -- my OWN loader.  Does not import ss_load / sslib / orch_crux_check.
Reads out/*_ss.npz directly, carries the per-route flown params, and provides a
route-cluster bootstrap that concatenates indices (the defect in ss_centring_fit.py:24-26
is an OR of masks, which collapses a route drawn twice -- I do not reproduce it).
"""
import glob, os, numpy as np

OUT = ('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/'
       'v282-reference/lowspeed/a_stickslip/out' + os.environ.get('ADVOUT', ''))
CH = ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'ad',
      'angdes', 'sr', 'v')
PRE = 150
BK = PRE - 3

# fork constants, re-read by me from latcontrol_vehicle_tunes.py (see adv_forkcheck.py)
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_LEVEL_BP = [12.5, 17.5]
HOLD_LEVEL_V = [1.15, 1.45]
HOLD_SAT = (19.3, 546.0, 3.01)


def hold_map(angle, v, level):
    """The fork's get_honda_accord_hold_torque, honouring THIS route's flown AccordHoldLevel."""
    angle = np.clip(np.asarray(angle, float), -400, 400)
    v = np.asarray(v, float)
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    if level:
        k = k * np.interp(v, HOLD_LEVEL_BP, HOLD_LEVEL_V)
    sat = HOLD_SAT[0] + HOLD_SAT[1] * np.exp(-np.maximum(v, 0.0) / HOLD_SAT[2])
    return k * sat * np.tanh(angle / sat)


def load():
    EP, W, P = [], {k: [] for k in CH}, {}
    for f in sorted(glob.glob(OUT + '/*_ss.npz')):
        D = np.load(f, allow_pickle=True)
        rk = os.path.basename(f)[:-7]
        ep = list(D['EP'])
        P[rk] = D['params'].item()
        if not len(ep):
            continue
        EP += ep
        for k in CH:
            W[k].append(D[k])
    W = {k: np.concatenate(v).astype(float) for k, v in W.items()}
    return EP, W, P


def cols(EP):
    keys = set()
    for e in EP:
        keys |= set(e.keys())
    out = {}
    for k in sorted(keys):
        out[k] = np.array([e.get(k, np.nan) for e in EP])
    return out


def cluster_boot(fn, base, route, nb=4000, seed=7):
    """Route-cluster bootstrap.  `base` is the GLOBAL index array of the analysis set and
    `route` is its route label, aligned.  Resamples ROUTES with replacement and
    CONCATENATES the drawn routes' global indices, so a route drawn twice contributes
    twice (ss_centring_fit.py:24-26 ORs masks instead and collapses it).
    fn(global_indices, routes) -> scalar or array."""
    base = np.asarray(base)
    route = np.asarray(route)
    assert len(base) == len(route)
    u = np.unique(route)
    idx = {c: base[route == c] for c in u}
    rng = np.random.default_rng(seed)
    pt = np.atleast_1d(np.asarray(fn(base, route), float))
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[c] for c in pick])
        rr = np.concatenate([np.full(len(idx[c]), c) for c in pick])
        try:
            bs.append(np.atleast_1d(np.asarray(fn(ii, rr), float)))
        except Exception:
            bs.append(np.full(pt.shape, np.nan))
    bs = np.array(bs)
    lo = np.nanpercentile(bs, 2.5, axis=0)
    hi = np.nanpercentile(bs, 97.5, axis=0)
    return pt, lo, hi, bs
