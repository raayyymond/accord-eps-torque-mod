"""attribution stream shared setup.

Loads the a_stickslip episode tables, RE-COMPUTES the hold-map channels honouring each route's
OWN flown AccordHoldLevel (the stored `hold_aa` channel is hard-coded level=False on every route
-- ss_extract.py:64 -- which is exactly the defect that makes the 6c/6d-vs-6e natural experiment
unrunnable off the stored channel), and exposes the LOW (torque, 2-8 m/s) mask plus the band
geometry used by orch_crux_check.py.

Fork arithmetic is taken from sslib.py, which copies latcontrol_vehicle_tunes.py verbatim; the
LEVEL branch is get_honda_accord_hold_level: interp(v, [12.5, 17.5], [1.15, 1.45]) so BELOW
12.5 m/s the levelled map is exactly x1.15.
"""
import sys, os
import numpy as np

AS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
sys.path.insert(0, AS)
from ss_load import load_all, boot_ci, boot_ci_ev, PRE, OUT     # noqa: E402
from sslib import hold_torque, k_of_v, HOLD_LEVEL_BP, HOLD_LEVEL_V, HOLD_SAT  # noqa: E402

BK = PRE - 3                      # the fit's breakaway sample (30 ms before breakaway)
CHAN = ('hold_ff', 'move', 'z', 'rl', 'dob', 'P', 'I')   # cmd = sum(CHAN)  (+left torque frame)


def build():
    EP, W, EX, VAL = load_all()
    N = len(EP); ar = np.arange(N)
    col = lambda k: np.array([e[k] for e in EP])
    D = dict(N=N, ar=ar, EP=EP, W=W, VAL=VAL)
    for k in ('group', 'v', 'sjump', 'route', 'kind', 'abs_aa', 'gap_bk', 'gapdes_bk', 'dwell_s', 'fric', 'LAF'):
        D[k] = col(k)
    D['d0'] = np.maximum(col('w_d0'), 0)
    D['TQ'] = np.isin(D['group'], ['T64', 'T64B', 'T5', 'T4'])
    D['aa_pre'] = W['aa'][:, PRE]
    D['toward'] = (D['sjump'] == -np.sign(D['aa_pre'])).astype(float)
    D['LOW'] = D['TQ'] & (D['v'] >= 2) & (D['v'] < 8)

    # ---- per-route flown params, read from the npz the extractor stored (which came from initData) ----
    import glob, json
    P = {}
    for f in sorted(glob.glob(OUT + '/*_ss.npz')):
        rk = os.path.basename(f)[:-7]
        P[rk] = np.load(f, allow_pickle=True)['params'].item()
    D['P'] = P
    lev = {rk: (p.get('AccordHoldLevel', '0') == '1') for rk, p in P.items()}
    dob_on = {rk: (float(p.get('AccordDobHz', 0.0)) > 0.0) for rk, p in P.items()}
    D['lev'], D['dob_on'] = lev, dob_on
    D['is_lev'] = np.array([lev[r] for r in D['route']])
    D['is_dob'] = np.array([dob_on[r] for r in D['route']])

    # ---- hold map at the ACTUAL angle, per-route level honoured (the fixed channel) ----
    vv = W['v']
    lv = np.array([1.15 if lev[r] else 1.0 for r in D['route']])[:, None]   # v < 12.5 everywhere in LOW
    kv = k_of_v(vv)
    sat = HOLD_SAT[0] + HOLD_SAT[1] * np.exp(-np.maximum(vv, 0.0) / HOLD_SAT[2])
    D['hold_aa_lev'] = kv * lv * sat * np.tanh(W['aa'] / sat)          # levelled, at actual angle
    D['hold_aa_unlev'] = kv * sat * np.tanh(W['aa'] / sat)             # unlevelled (== stored hold_aa)
    D['hold_ad_lev'] = kv * lv * sat * np.tanh(W['angdes'] / sat)      # levelled, at desired angle
    D['hold_ad_unlev'] = kv * sat * np.tanh(W['angdes'] / sat)
    return D


def fit_lin(D, m, idx, y=None):
    """The orch/ss_centring_fit band fit:  cmd = k*aa + Fa*sj + d*sj*toward + c."""
    W, ar, sj, tw = D['W'], D['ar'], D['sjump'], D['toward']
    y = W['cmd'][ar, idx] if y is None else y
    X = np.vstack([W['aa'][ar, idx], sj, sj * tw, np.ones(D['N'])]).T[m]
    c = np.linalg.lstsq(X, y[m], rcond=None)[0]
    return dict(away=c[1], toward=c[1] + c[2], halfwidth=c[1] + c[2] / 2,
                centring_offset=-c[2] / 2, k=c[0], const=c[3])


def fit_hold(D, m, idx, holdch='hold_aa_lev'):
    """Same band fit with the fork's NONLINEAR hold map in place of the linear k*aa regressor:
       cmd = G*hold(aa,v) + Fa*sj + d*sj*toward + c.   G is the free gain on the map."""
    W, ar, sj, tw = D['W'], D['ar'], D['sjump'], D['toward']
    X = np.vstack([D[holdch][ar, idx], sj, sj * tw, np.ones(D['N'])]).T[m]
    c = np.linalg.lstsq(X, W['cmd'][ar, idx][m], rcond=None)[0]
    return dict(away=c[1], toward=c[1] + c[2], halfwidth=c[1] + c[2] / 2,
                centring_offset=-c[2] / 2, G=c[0], const=c[3])


def quintiles(D, m=None):
    m = D['LOW'] if m is None else m
    a = np.abs(D['aa_pre'])
    return np.quantile(a[m], [0, .2, .4, .6, .8, 1.0]), a


def bins(D, m, qs, aabs):
    """yield (lo, hi, mask) for the 5 |angle| quintile cells."""
    for i in range(5):
        lo, hi = qs[i], qs[i + 1]
        yield lo, hi, m & (aabs >= lo) & ((aabs <= hi) if i == 4 else (aabs < hi))
