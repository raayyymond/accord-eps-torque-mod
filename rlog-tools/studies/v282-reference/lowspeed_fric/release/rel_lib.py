"""release stream shared loader.

Reuses lowspeed/a_stickslip/out/*_ss.npz (episodes + 230-frame windows around breakaway,
PRE=150 lead, POST=80).  Adds, for the V282 group, a window-local reconstruction of the
plant-FF sub-terms (hold, move) that the extractor zeroed because it only decomposed the
torque routes -- V282 routes ALSO ran AccordRatePlantFF=1 (params: AccordRatePlantFF '1',
AccordFFRateGain '0.5', SteerLatAccel 6.0, SteerKP 0.9, SteerFriction 0.01).

FRAME: +left steering-angle frame, torque in [-1,1] output units, then sign-aligned by sj
(the sign of the jump) so + = "pushing the way the wheel then went".
"""
import os, sys, glob, json
import numpy as np

SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
sys.path.insert(0, SS)
from sslib import (hold_torque, band, hyst_run, fo_filter, k_of_v, G_BP, G_V, MOVE_LIM_BP, MOVE_LIM_V,
                   FF_RATE_RC, RATE_LOOP_RC, RATE_LOOP_TAPER_V, BASE)  # noqa
from ss_load import CH, PRE, boot_ci  # noqa

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
POST = 80
TQG = ('T64', 'T64B', 'T5', 'T4')


def load():
    EP, W, P = [], {k: [] for k in CH}, {}
    for f in sorted(glob.glob(SS + '/out/*_ss.npz')):
        D = np.load(f, allow_pickle=True)
        ep = list(D['EP'])
        if not ep:
            continue
        rk = os.path.basename(f)[:-7]
        P[rk] = D['params'].item()
        EP += ep
        for k in CH:
            W[k].append(D[k])
    W = {k: np.concatenate(v).astype(np.float64) for k, v in W.items()}
    return EP, W, P


def rebuild_v282_ff(W, EP, P):
    """Window-local hold/move for every episode, from angdes and v inside the window.
    FF_RATE_RC = 0.10 s (10 frames) and the window carries PRE=150 frames of lead-in, so the
    filter is settled long before breakaway.  Returns (hold, move, resid) arrays, shape of W.
    resid = F - hold - move  (torque: z+rl+dob; V282: the SteerFriction relay + anything else)."""
    N, L = W['angdes'].shape
    ang = W['angdes']; v = W['v']
    lev = np.array([P[e['route']].get('AccordHoldLevel', '0') == '1' for e in EP])
    hold = np.empty((N, L)); move = np.empty((N, L))
    d = np.diff(ang, axis=1, prepend=ang[:, :1])
    a = 0.01 / (FF_RATE_RC + 0.01)
    s = np.zeros(N)
    rate = np.empty((N, L))
    for j in range(L):
        s = s + a * (d[:, j] / 0.01 - s)
        rate[:, j] = s
    ffrg = np.array([float(P[e['route']].get('AccordFFRateGain', 0.5)) for e in EP])[:, None]
    for i in range(N):
        hold[i] = hold_torque(ang[i], v[i], bool(lev[i]))
    lim = np.interp(v, MOVE_LIM_BP, MOVE_LIM_V)
    move = np.clip(ffrg * rate / np.interp(v, G_BP, G_V), -lim, lim)
    resid = W['F'] - hold - move
    return hold, move, resid
