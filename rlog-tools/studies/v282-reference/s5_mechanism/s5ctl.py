"""Replica of the fork's Accord torque-mode lateral controller (latcontrol_torque.py + latcontrol_vehicle_tunes.py at
84766cdc rev 6.4; parameterised for rev 5 e44b6cd3 and rev 4 08a5a706), plus a V293 plant, for closed-loop simulation.

Transcribed from the source, not imported (the tunes module drags in every car's values).  Validated OPEN LOOP against the
logged P / I / F / output in s5_03 before any closed-loop use.  Frames: the controller's TORQUE frame is right-positive
(setpoint, measurement, P, I, F all in it); the plant's +left frame torque is u = -output_torque = cs_out.
"""
import math
import sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot/opendbc_repo')
from opendbc.car import scale_tire_stiffness, scale_rot_inertia, STD_CARGO_KG  # noqa: E402
from opendbc.car.vehicle_model import VehicleModel  # noqa: E402

DT = 0.01


class _CP:
    mass = 3279 * 0.453592 + STD_CARGO_KG
    wheelbase = 2.83
    centerToFront = 2.83 * 0.39
    steerRatio = 16.33
    steerRatioRear = 0.0
    rotationalInertia = scale_rot_inertia(mass, wheelbase)
    tireStiffnessFront, tireStiffnessRear = scale_tire_stiffness(mass, wheelbase, centerToFront, 0.8467)


VM = VehicleModel(_CP())

# ---- constants (84766cdc) ----
LOW_SPEED_X = [0, 10, 20, 30]; LOW_SPEED_Y = [12, 10.5, 8, 5]
G_BP = [5.0, 12.5, 18.5, 28.5]; G_V = [550.0, 271.0, 246.0, 167.0]
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_LEVEL_BP = [12.5, 17.5]; HOLD_LEVEL_V = [1.15, 1.45]
SAT = (19.3, 546.0, 3.01)
J_MODEL = 8e-5
FF_RATE_RC = 0.10
MOVE_LIM_BP = [8.0, 10.0]; MOVE_LIM_V = [1.0, 1.4]
HYST_BAND_BP = [8.0, 12.0, 19.0, 26.0]; HYST_BAND_V = [3.0, 2.10, 0.96, 0.60]
RATE_LOOP_TAPER_V = 12.0
DOB_DELAY_N = 6; DOB_ACC_RC = 0.05; DOB_MAX = 0.3; DOB_FADE_BP = [3.0, 6.0]
KI_BP = [8.0, 18.0]

REV = {
    'rev64': dict(kp=1.0, ki=0.3, ki_high=0.0, laf=14.0, rate_gain=0.5, hyst=0.015, band_sched=True, hold_level=True,
                  rl_gain=0.001, rl_rc=0.01, dob_hz=0.6, notch_q=1.0),
    'rev64B': dict(kp=1.0, ki=0.3, ki_high=0.0, laf=14.0, rate_gain=0.5, hyst=0.015, band_sched=True, hold_level=False,
                   rl_gain=0.001, rl_rc=0.01, dob_hz=0.6, notch_q=1.0),
    'rev5': dict(kp=1.0, ki=0.3, ki_high=0.0, laf=14.0, rate_gain=0.5, hyst=0.015, band_sched=False, hold_level=False,
                 rl_gain=0.001, rl_rc=0.01, dob_hz=0.6, notch_q=1.0),
    'rev4': dict(kp=0.85, ki=0.6, ki_high=2.5, laf=14.0, rate_gain=0.5, hyst=0.015, band_sched=False, hold_level=False,
                 rl_gain=0.0006, rl_rc=0.03, dob_hz=0.0, notch_q=1.0),
}
GROUP_REV = {'T64': 'rev64', 'T64B': 'rev64B', 'T5': 'rev5', 'T4': 'rev4'}


def hold_torque(angle, v, level):
    angle = min(max(angle, -400.0), 400.0)
    k = float(np.interp(v, HOLD_V_BP, HOLD_K_V)) * (float(np.interp(v, HOLD_LEVEL_BP, HOLD_LEVEL_V)) if level else 1.0)
    sat = SAT[0] + SAT[1] * math.exp(-max(v, 0.0) / SAT[2])
    return k * sat * math.tanh(angle / sat)


def mode_hz(v):
    return math.sqrt(float(np.interp(v, HOLD_V_BP, HOLD_K_V)) / J_MODEL) / (2 * math.pi)


def angle_from_la(la_T, v, roll, sR, stiff):
    """desired angle (+left deg) for a torque-frame lateral accel, as the fork computes angle_des."""
    VM.update_params(stiff, sR)
    curv = la_T / max(v * v, 1.0)
    return math.degrees(VM.get_steer_from_curvature(-curv, v, roll))


def la_from_angle(theta_left, aoff, v, roll, sR, stiff):
    """measurement (torque frame) = -calc_curvature(theta - aoff) * v^2"""
    VM.update_params(stiff, sR)
    return -VM.calc_curvature(math.radians(theta_left - aoff), v, roll) * v * v


class Notch:
    def __init__(self):
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

    def update(self, x, f_hz, q):
        if q <= 0 or f_hz <= 0:
            self.x1 = self.x2 = self.y1 = self.y2 = x
            return x
        k = math.tan(math.pi * min(f_hz, 0.45 / DT) * DT)
        norm = 1.0 / (1.0 + k / q + k * k)
        b0 = (1.0 + k * k) * norm; b1 = 2.0 * (k * k - 1.0) * norm; a2 = (1.0 - k / q + k * k) * norm
        y = b0 * x + b1 * self.x1 + b0 * self.x2 - b1 * self.y1 - a2 * self.y2
        self.x2, self.x1, self.y2, self.y1 = self.x1, x, self.y1, y
        return y


class Ctl:
    """One instance per engaged stretch.  step() returns cs_out (+left torque) and the components (torque frame)."""

    def __init__(self, rev, rate0=0.0, angle_des0=0.0, extra=None):
        self.p = dict(REV[rev]) if isinstance(rev, str) else dict(rev)
        if extra:
            self.p.update(extra)
        self.i = 0.0
        self.notch = Notch()
        self.adr = 0.0
        self.prev_ad = angle_des0
        self.rm = rate0
        self.z = 0.0
        self.u_hist = [0.0] * DOB_DELAY_N
        self.w1 = self.w2 = 0.0
        self.prev_rate = rate0
        self.acc = 0.0
        self.dob = 0.0

    def step(self, sp, meas, theta_left, rate, v, roll, sR, stiff, aoff, pressed=False, limited=False, u_left_logged=None, rl_ref_bias=0.0):
        P_ = self.p
        dob_used = self.dob
        if getattr(self, 'prev_pressed', False) and not pressed:
            self.i *= 0.8
        self.prev_pressed = pressed
        lsf = (float(np.interp(v, LOW_SPEED_X, LOW_SPEED_Y)) / max(v, 1.0)) ** 2
        kp = P_['kp']
        e = (sp - meas) * (1 + lsf / max(kp, 1e-3))
        e = self.notch.update(e, mode_hz(v), P_['notch_q'])
        ad = angle_from_la(sp, v, roll, sR, stiff)
        dad = ad - self.prev_ad
        self.adr += (DT / (FF_RATE_RC + DT)) * (dad / DT - self.adr)
        self.prev_ad = ad
        G = float(np.interp(v, G_BP, G_V))
        hold = hold_torque(ad, v, P_['hold_level'])
        lim = float(np.interp(v, MOVE_LIM_BP, MOVE_LIM_V))
        move = min(max(P_['rate_gain'] * self.adr / G, -lim), lim)
        band = float(np.interp(v, HYST_BAND_BP, HYST_BAND_V)) if P_['band_sched'] else 3.0
        if P_['hyst'] > 0:
            self.z = min(max(self.z + dad * P_['hyst'] / max(band, 1e-3), -P_['hyst']), P_['hyst'])
        self.rm += (DT / (P_['rl_rc'] + DT)) * (rate - self.rm)
        rlg = P_['rl_gain'] * min(1.0, RATE_LOOP_TAPER_V / max(v, 0.1))
        rl = rlg * (self.adr + rl_ref_bias - self.rm)
        ff_torque = -(hold + move) - (self.z + rl) - self.dob
        laf = P_['laf']
        ff_la = ff_torque * laf
        Pt = kp * e
        ki = P_['ki'] if P_['ki_high'] <= 0 else float(np.interp(v, KI_BP, [P_['ki'], P_['ki_high']]))
        if not (pressed or limited or v < 0.3):
            i = self.i + ki * DT * e
            test = Pt + i + ff_la
            ub = self.i if test > laf else laf
            lb = self.i if test < -laf else -laf
            self.i = min(max(i, lb), ub)
        out_la = min(max(Pt + self.i + ff_la, -laf), laf)
        out_T = out_la / laf
        # observer (+left frame)
        if P_['dob_hz'] > 0:
            u_left_now = -out_T if u_left_logged is None else u_left_logged   # open-loop replay: the DOB->u->DOB path is a pure integrator without the plant
            u_del = self.u_hist[0]
            self.u_hist.append(u_left_now); self.u_hist.pop(0)
            spring = hold_torque(theta_left - aoff, v, P_['hold_level'])
            self.acc += (DT / (DOB_ACC_RC + DT)) * ((rate - self.prev_rate) / DT - self.acc)
            self.prev_rate = rate
            resid = u_del - (spring + rate / G + J_MODEL * self.acc)
            if not (pressed or limited):
                al = DT / (1.0 / (2 * math.pi * P_['dob_hz']) + DT)
                self.w1 += al * (resid - self.w1)
                self.w2 += al * (self.w1 - self.w2)
            fade = float(np.interp(v, DOB_FADE_BP, [0.0, 1.0]))
            self.dob = min(max(self.w2 * fade, -DOB_MAX), DOB_MAX)
        return -out_T, dict(p=Pt, i=self.i, f=ff_la, hold=-hold * laf, move=-move * laf, hyst=-self.z * laf,
                            rl=-rl * laf, dob=-dob_used * laf, ad=ad, err=e)
