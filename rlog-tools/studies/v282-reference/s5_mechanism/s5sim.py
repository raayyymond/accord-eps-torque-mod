"""Closed-loop simulator: fork controller replica (s5ctl.Ctl, or a candidate structure with the same step() signature) on a
V293 plant, driven by the LOGGED exogenous inputs of a real route (setpoint = cs_la_des, which depends only on the model's
desired curvature and the learned delay, never on the measurement; v; liveParameters roll/sR/stiffness/angleOffset).

Plant (+left frame, torque in [-1,1] command units), 1 kHz substeps:
    J th'' + b th' + s(v) * hold0(th - aoff, v) + friction = u(t - d)
friction = Karnopp stick-slip with Coulomb level F.  u = the controller output after the Honda +-0.03/frame rate limit.
Every parameter is an argument so the closed-loop validation (s5_05) can bracket it.
"""
import math
import numpy as np
import s5ctl as C
import s5lib as L

PLANT_NOMINAL = dict(J=8e-5, b=0.0007, F=0.015, d=6, s_bp=[5.0, 11.5, 18.5, 26.0], s_v=[1.0, 1.28, 1.44, 1.25],
                     rate_lim=0.03, meas_scale=1.05)


def plant_step(state, u, v, aoff, P, n_sub=10):
    th, om = state
    h = 0.01 / n_sub
    s = float(np.interp(v, P['s_bp'], P['s_v']))
    F = P['F']
    for _ in range(n_sub):
        spring = s * C.hold_torque(th - aoff, v, False)
        net = u - spring - P['b'] * om
        if abs(om) < 0.05:
            if abs(net) <= F:        # stuck
                om = 0.0
                continue
            net -= F * math.copysign(1.0, net)
        else:
            net -= F * math.copysign(1.0, om)
        om_new = om + net / P['J'] * h
        if om != 0.0 and om * om_new < 0 and abs(u - spring) <= F:   # friction cannot reverse the motion
            om_new = 0.0
        om = om_new
        th += om * h
    return th, om


def simulate(S, stiff, make_ctl, P, mask, min_s=10.0):
    """make_ctl(S, j0) -> controller with step(sp, meas, th, rate, v, roll, sR, stiff, aoff, pressed) -> (u_left, comps)"""
    n = len(S['t'])
    th_s = np.full(n, np.nan); om_s = np.full(n, np.nan); u_s = np.full(n, np.nan); la_s = np.full(n, np.nan)
    comps = {}
    roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84); aoff = np.nan_to_num(S['aoff'])
    for a, b in L.V.runs(mask, S['t'], min_s=min_s):
        ctl = make_ctl(S, a)
        th, om = float(S['sa'][a]), float(S['sr'][a])
        ubuf = [float(S['out'][a])] * max(P['d'], 1)
        u_prev = float(S['out'][a])
        for j in range(a, b):
            v = float(S['v'][j])
            meas = P['meas_scale'] * C.la_from_angle(th, aoff[j], v, roll[j], sR[j], stiff[j])
            u, cp = ctl.step(float(S['setpoint'][j]), meas, th, om, v, roll[j], sR[j], stiff[j], aoff[j])
            u = min(max(u, u_prev - P['rate_lim']), u_prev + P['rate_lim'])
            u_prev = u
            ubuf.append(u)
            ud = ubuf.pop(0)
            th_s[j], om_s[j], u_s[j], la_s[j] = th, om, u, meas
            for k, x in cp.items():
                comps.setdefault(k, np.full(n, np.nan))[j] = x
            th, om = plant_step((th, om), ud, v, aoff[j], P)
    return dict(th=th_s, rate=om_s, out=u_s, la=la_s, **comps)
