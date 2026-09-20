"""asym stream: INDEPENDENT re-derivation of the release-band centre-offset claim.

Loads only the episode windows (out/<rk>_ss.npz from ss_extract.py).  Every fit, every
bootstrap and every hold-map evaluation here is written from scratch; no ss_* fitting code
and no design-stream JSON is imported.

FRAME (re-verified against latcontrol_torque.py:638-676):
  cmd = -(p+i+f)/LAF = -output_torque  -> +left torque frame, same frame as steering angle aa.
  outward = +sign(aa).  A positive z_out in latcontrol_torque.py:667's `-(z + z_out + ...)`
  becomes a NEGATIVE inner_torque, i.e. -(+left) ... and the caller's plant_ff_torque is also
  negated, so the +left convention holds: z_out>0 pushes the wheel further from centre when
  angle_des>0.  Verified by the same negation on plant_ff_torque (line 2592 hold_torque is
  +left and line 664 negates it).
"""
import glob, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
SS = BASE + '/lowspeed/a_stickslip/out'
CH = ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'ad', 'angdes', 'sr', 'v')
PRE = 150      # window index of the breakaway frame

# fork constants, re-copied from latcontrol_vehicle_tunes.py (lines 268-275, 2606-2627)
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_LEVEL_BP, HOLD_LEVEL_V = [12.5, 17.5], [1.15, 1.45]
SAT_A, SAT_B, SAT_C = 19.3, 546.0, 3.01


def hold_map(angle, v, level=True):
    """get_honda_accord_hold_torque, vectorised.  level=True -> x1.15 below 12.5 m/s."""
    angle = np.clip(np.asarray(angle, float), -400.0, 400.0)
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    if level:
        k = k * np.interp(v, HOLD_LEVEL_BP, HOLD_LEVEL_V)
    sat = SAT_A + SAT_B * np.exp(-np.maximum(np.asarray(v, float), 0.0) / SAT_C)
    return k * sat * np.tanh(angle / sat)


def load():
    EP, W = [], {k: [] for k in CH}
    PR = {}
    for f in sorted(glob.glob(SS + '/*_ss.npz')):
        D = np.load(f, allow_pickle=True)
        ep = list(D['EP'])
        rk = f.replace('\\', '/').split('/')[-1][:-7]
        PR[rk] = D['params'].item()
        if not len(ep):
            continue
        EP += ep
        for k in CH:
            W[k].append(D[k])
    W = {k: np.concatenate(v) for k, v in W.items()}
    return EP, W, PR


def cols(EP):
    c = lambda k: np.array([e[k] for e in EP])
    return c


def boot_routes(fn, routes, mask, nb=2000, seed=7):
    """PROPER route-cluster bootstrap: resample routes WITH multiplicity and concatenate their
    episode indices (the study's own ss_* bootstrap ORs boolean masks instead, which silently
    collapses a duplicated route to one copy -- a random-subset jackknife, not a bootstrap).
    fn(idx_array) -> vector of statistics."""
    idx0 = np.where(mask)[0]
    est = np.atleast_1d(np.asarray(fn(idx0), float))
    u = np.unique(routes[mask])
    per = {c: np.where(mask & (routes == c))[0] for c in u}
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([per[c] for c in pick])
        try:
            bs.append(np.atleast_1d(np.asarray(fn(ii), float)))
        except Exception:
            pass
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return est, lo, hi, bs
