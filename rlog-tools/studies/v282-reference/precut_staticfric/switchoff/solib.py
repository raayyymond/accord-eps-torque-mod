"""switchoff stream: shared recomputation of the candidate term z_out on logged signals.

FRAME.  Everything in the +left steering-angle frame, torque in [-1,1] output units, exactly as
lowspeed/a_stickslip (cmd = cs_out = -(p+i+f)/LAF ; F_t = hold + move + z + rl + dob_left).

WHY z_out ADDS POSITIVELY IN THIS FRAME (verified against the fork, not assumed):
  latcontrol_torque.py: inner_torque = -(self.accord_friction_z + rate_loop_gain*(angle_des_rate - rate_meas))
  ff_torque = plant_ff_torque + friction_torque + inner_torque ;  cmd = -(p+i+f)/LAF  ~  -ff_torque + (P+I)/LAF
  so the +left command carries +z and +rate_loop_gain*(rate_des-rate_meas), which is what sslib's F_t
  decomposition uses and validates.  The candidate adds z_out INSIDE the same bracket as z, therefore
  +left contribution = +z_out, with z_out built from the +left angle_des.

CANDIDATE (as briefed):
  s_a = tanh(angle_des / 1.0 deg) ; s_r = tanh(angle_des_rate / 2.0 deg/s)
  z_out = level * g(v) * max(0, s_a*s_r) * s_a       # g: 1.0 at v<=8, linear to 0.0 at v>=12
  -> magnitude level*g*s_a^2*|s_r|, sign = sign(angle_des) = sign(angle_des_rate); ZERO unless the
  desired angle is moving AWAY from centre.  Stateless.
"""
import sys, os, json
import numpy as np
from scipy import ndimage

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
MINE = BASE + '/precut_staticfric/switchoff'
OUT = MINE + '/out'
sys.path.insert(0, BASE)
sys.path.insert(0, BASE + '/s3_accel')
sys.path.insert(0, BASE + '/lowspeed/a_stickslip')
import v282cmp as V
import s3turns as T
from sslib import (k_of_v, hold_torque, band, hyst_run, fo_filter, params, HOLD_V_BP, HOLD_K_V,
                   MOVE_LIM_BP, MOVE_LIM_V, G_BP, G_V, FF_RATE_RC, RATE_LOOP_RC, RATE_LOOP_TAPER_V)

LEVEL = 0.020          # AccordStaticFricOut, the briefed dose
A_SCALE = 1.0          # deg   (tanh scale on angle_des)
R_SCALE = 2.0          # deg/s (tanh scale on angle_des_rate)
G_BP_V = [8.0, 12.0]   # speed gate
G_V_V = [1.0, 0.0]
TORQUE_GROUPS = ['T64', 'T64B', 'T5', 'T4']


def g_of_v(v):
    return np.interp(v, G_BP_V, G_V_V)


def z_out_of(angdes, rate_des, v, level=LEVEL):
    s_a = np.tanh(angdes / A_SCALE)
    s_r = np.tanh(rate_des / R_SCALE)
    return level * g_of_v(v) * np.maximum(0.0, s_a * s_r) * s_a


def route_signals(rk):
    """Recompute, for a whole route, everything the candidate and the release model need.
    Mirrors ss_extract.route() arithmetic line for line (same reconstruction, same filters)."""
    S = V.load(rk)
    meta = S['meta']
    p, fs = params(rk)
    LAF = float(p.get('SteerLatAccel', 'nan'))
    t = S['t']; n = len(t)
    v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0)
    act = S['active']
    press_d = ndimage.binary_dilation(S['pressed'], iterations=50)
    HO = act & ~press_d
    aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    sr = np.nan_to_num(S['sr'])
    cmd = np.nan_to_num(S['out'])
    sR = np.nan_to_num(S['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    torque = meta['eps'] == 'V293'
    d_ang = np.r_[0.0, np.diff(angdes)]
    d_ang[~act] = 0.0
    d_ang[np.r_[True, ~act[:-1]]] = 0.0
    rate_des = fo_filter(d_ang / 0.01, FF_RATE_RC, reset=~act)
    fric = float(p.get('AccordFrictionHyst', 0.0)) if torque else 0.0
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    z = hyst_run(d_ang, fric, band(v, sched), act)
    zo = z_out_of(angdes, rate_des, v)
    zo[~act] = 0.0                      # the term only exists while the Accord plant-FF branch runs
    hold_aa = hold_torque(aa, v, False)  # spring torque at the ACTUAL angle, unlevelled (v<12.5 anyway)
    return dict(rk=rk, group=meta['group'], t=t, v=v, act=act, HO=HO, aa=aa, sr=sr, cmd=cmd,
                angdes=angdes, rate_des=rate_des, z=z, z_out=zo, hold_aa=hold_aa, LAF=LAF,
                torque=torque, params=p)


def episodes(rk):
    """The a_stickslip episode table for this route (primary DWMIN=20 output)."""
    D = np.load(f'{BASE}/lowspeed/a_stickslip/out/{rk}_ss.npz', allow_pickle=True)
    return list(D['EP'])


def boot_ci(vals, clusters, fn=np.median, nb=2000, seed=0):
    vals = np.asarray(vals, float); clusters = np.asarray(clusters)
    u = np.unique(clusters); rng = np.random.default_rng(seed)
    idx = {c: np.where(clusters == c)[0] for c in u}
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[c] for c in pick])
        bs.append(fn(vals[ii]))
    return [float(fn(vals)), [float(x) for x in np.percentile(bs, [2.5, 97.5])]]
