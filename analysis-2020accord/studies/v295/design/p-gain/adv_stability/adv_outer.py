# -*- coding: utf-8 -*-
"""adv_outer.py -- MY OWN linearisation of the OUTER loop: the fork's generic torque controller (Dom 20d24ab79, r1 path,
read from latcontrol_torque.py lines 252-358/597-698 + common/pid.py + opendbc get_friction) around the EPS lane and the
plant, at an operating point (v, theta0, idx0), with the plant spring linearised at theta0 (the harness/designer use the
small-angle k; the plant simulator uses k*sat*tanh(th/sat), whose TANGENT at theta0 is k*sech^2(theta0/sat)).

  meas = -cf(v)/sR(theta)*rad(theta)*v^2 ; error = setpoint - meas (setpoint exogenous) ; e_lsf = error*(1 + lsf/kp)
  output_lataccel = kp*e_lsf + i + ff + relay(e_lsf) ; i += ki*0.01*e_lsf ; relay slope friction*LAF/0.30 in |e_lsf|<0.30
  wire = 4096*output_lataccel/LAF (100 Hz ZOH, pipe delay) ; T = lane FF slope(idx0) x output lag + trim(Kp(idx0))
  u = -T (tau) ; J th'' + b th' + k_loc th = u
L_out > 0 at DC = negative feedback (checked).
"""
import numpy as np

import adv_lin as AL

VM = dict(sf=-0.0006999872680281922, chi=0.0, l=2.8299999237060547)     # opendbc VehicleModel(fork CP) via harness
SR_BP = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0]
SR_V = [16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68, 14.45, 14.09, 14.25, 12.98, 12.31]
SR_SCALE = 16.84 / 16.88


def sat_prior(v):
    return 19.3 + 546.0 * np.exp(-v / 3.01)


def meas_of_theta(th, v):
    cf = (1.0 - VM["chi"]) / (1.0 - VM["sf"] * v ** 2) / VM["l"]
    sr = np.interp(np.abs(th), SR_BP, SR_V) * SR_SCALE
    return cf * np.radians(th) / sr * v ** 2


def kla(v, th0):
    h = 0.05
    return (meas_of_theta(th0 + h, v) - meas_of_theta(th0 - h, v)) / (2 * h)


def lsf(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2


LANE_BASE = dict(fb_a=1011, fb_b=567, fb_op="diff", kd=0.0, lag_a=992, lag_b=507, gain=5346)


def outer_L(f, v, th0, J, b, k, sat, kp_lane, slope_T_wire, fork, pipe_ms=22.0, tau=2, trim=True, relay=True,
            relay_df=None, k_loc=None, kappa=1.0):
    """fork: dict kp, ki, laf, fric.  relay_df overrides the relay slope (describing-function gain, per e_lsf unit).
    kappa: multiplies the angle the fork reads (wheel/rack ratio)."""
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    zi100 = np.exp(-s * 0.01)
    kpf, ki, laf, fric = fork["kp"], fork["ki"], fork["laf"], fork["fric"]
    rs = (fric * laf / 0.30) if relay else 0.0
    if relay_df is not None:
        rs = relay_df
    Kf = (kpf + ki * 0.01 / (1 - zi100) + rs) * (1 + lsf(v) / kpf)
    kl = kla(v, th0) * kappa
    if k_loc is None:
        k_loc = k / np.cosh(th0 / sat) ** 2
    Ac, Bc, cs, _ = AL.plant_cont(J, b, k_loc)
    Pth = AL.plant_frf(Ac, Bc, cs, f) * np.exp(-s * tau * AL.DT) * np.exp(-1j * np.pi * f * AL.DT) * np.sinc(f * AL.DT)
    if trim and kp_lane > 0:
        Lin = AL.inner_L(dict(LANE_BASE, kp=kp_lane), Ac, Bc, cs, f, tau=tau)
    else:
        Lin = 0.0 * f
    Pcl = Pth / (1 + Lin)
    zi = np.exp(-s * AL.DT)
    Hl = (507 / 1024.0) * (1 + zi) / (32.0 * (1 - (992 / 1024.0) * zi))
    Hl0 = (507 / 1024.0) * 2 / (32.0 * (1 - 992 / 1024.0))
    FF = slope_T_wire * Hl / Hl0
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    pipe = np.exp(-s * pipe_ms * 1e-3)
    return Kf * kl * (4096.0 / laf) * zoh100 * pipe * FF * Pcl


def slope_at(S, idx0, half=8, wire_per_idx=2 ** 22 / (4 * 65025)):
    i0, i1 = max(int(idx0) - half, 0), min(int(idx0) + half, 240)
    return (float(S[i1]) - float(S[i0])) / ((i1 - i0) * wire_per_idx)


def idx_for_torque(S, T):
    """the smallest idx whose static surface reaches T (the op point a candidate needs for the same hold torque)."""
    j = int(np.searchsorted(S, T))
    return min(max(j, 0), 240)
