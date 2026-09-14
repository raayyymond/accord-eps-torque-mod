# -*- coding: utf-8 -*-
"""v293r2_simlib.py -- closed-loop 100 Hz simulation of the fork's Accord torque controller on the
identified V293 plant.  Started 2026-09-14 from the rev-2 adversary's adv_lib.py + a4_sim.py (job tmp,
2026-09-13), which transcribed latcontrol_torque.update()'s Accord branch line for line, common/pid.py's
anti-windup, honda/carcontroller.py's +-0.03/frame limiter and the steer_limited_by_safety freeze.

The fork tables are PARSED from the committed fork file at import, so the simulation always runs the
tables the device would run.  Extended here with: an optional inertia term, an explicit loop delay
split (openpilot round trip vs plant), and the candidate inner loop (see Cfg fields prefixed `il_`).
"""
import math
import re
import numpy as np

FORK = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
TUNES = FORK + "/selfdrive/controls/lib/latcontrol_vehicle_tunes.py"

DT = 0.01


# ---------------------------------------------------------------- fork tables, parsed from source
def _tbl(name, src):
    m = re.search(r"^%s\s*=\s*\[([^\]]*)\]" % re.escape(name), src, re.M)
    assert m, name
    return [float(x) for x in m.group(1).split(",")]


def _scalar(name, src):
    m = re.search(r"^%s\s*=\s*([0-9.]+)" % re.escape(name), src, re.M)
    assert m, name
    return float(m.group(1))


_SRC = open(TUNES, encoding="utf-8").read()
G_BP = _tbl("HONDA_ACCORD_EPS_G_BP", _SRC)
G_V = _tbl("HONDA_ACCORD_EPS_G_V", _SRC)
K_BP = _tbl("HONDA_ACCORD_EPS_K_BP", _SRC)
K_V = _tbl("HONDA_ACCORD_EPS_K_V", _SRC)
MOVE_BP = _tbl("HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_BP", _SRC)
MOVE_V = _tbl("HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_V", _SRC)
FF_ANGLE_LIMIT = _scalar("HONDA_ACCORD_FF_ANGLE_LIMIT_DEG", _SRC)
FF_RATE_RC = _scalar("HONDA_ACCORD_FF_RATE_RC", _SRC)
SR_ANGLE_BP = _tbl("HONDA_ACCORD_STEER_RATIO_ANGLE_BP", _SRC)
SR_V = _tbl("HONDA_ACCORD_STEER_RATIO_V", _SRC)
SR_NOMINAL = _scalar("HONDA_ACCORD_STEER_RATIO_NOMINAL", _SRC)

# the OLD (pre-9622aee9f) tables, quoted verbatim in the new file's comment block
G_V_OLD = [120.0, 95.0, 85.0, 70.0]
K_V_OLD = [0.17, 0.28, 0.35, 0.45, 0.50]


def plant_ff(angle_deg, angle_rate_dps, v, rate_gain=0.5, gain_scale=1.0, spring_scale=1.0,
             g_v=None, k_v=None):
    """byte-for-byte re-implementation of get_honda_accord_rate_plant_ff."""
    g_v = G_V if g_v is None else g_v
    k_v = K_V if k_v is None else k_v
    angle_deg = float(np.clip(angle_deg, -FF_ANGLE_LIMIT, FF_ANGLE_LIMIT))
    gain = float(np.interp(v, G_BP, g_v)) * max(float(gain_scale), 0.1)
    spring = float(np.interp(v, K_BP, k_v)) * float(spring_scale)
    hold = spring * angle_deg / gain
    lim = float(np.interp(v, MOVE_BP, MOVE_V))
    move = float(np.clip(rate_gain * angle_rate_dps / gain, -lim, lim))
    return hold + move


def fork_hold_per_deg(v, spring_scale=1.0, gain_scale=1.0, g_v=None, k_v=None):
    g_v = G_V if g_v is None else g_v
    k_v = K_V if k_v is None else k_v
    return (float(np.interp(v, K_BP, k_v)) * spring_scale) / (float(np.interp(v, G_BP, g_v)) * max(gain_scale, 0.1))


def fork_move_per_dps(v, rate_gain, gain_scale=1.0, g_v=None):
    g_v = G_V if g_v is None else g_v
    return rate_gain / (float(np.interp(v, G_BP, g_v)) * max(gain_scale, 0.1))


def steer_ratio(angle_deg, level=None):
    shape = float(np.interp(abs(angle_deg), SR_ANGLE_BP, SR_V))
    if level is None:
        return shape
    return shape * (level / SR_NOMINAL)


# ---------------------------------------------------------------- vehicle model (opendbc algebra)
STD_CARGO_KG = 136.0          # opendbc/car/__init__.py; CarSpecs.mass is CURB weight, cargo is NOT added
MASS = 3279 * 0.453592
WHEELBASE = 2.83
CTF_RATIO = 0.39
TSF = 0.8467
CHI = 0.0

_VD_MASS = 1326.0 + STD_CARGO_KG
_VD_WB = 2.70
_VD_CTF = _VD_WB * 0.4
_VD_CTR = _VD_WB - _VD_CTF
_TSF_F, _TSF_R = 192150.0, 202500.0

aF = WHEELBASE * CTF_RATIO
aR = WHEELBASE - aF
cF = (_TSF_F * TSF) * MASS / _VD_MASS * (aR / WHEELBASE) / (_VD_CTR / _VD_WB)
cR = (_TSF_R * TSF) * MASS / _VD_MASS * (aF / WHEELBASE) / (_VD_CTF / _VD_WB)
SLIP = MASS * (cF * aF - cR * aR) / (WHEELBASE ** 2 * cF * cR)


def curvature_factor(v):
    return (1.0 - CHI) / (1.0 - SLIP * v ** 2) / WHEELBASE


def lat_accel_per_deg(v, sr):
    """m/s^2 of lateral acceleration per degree of steering wheel angle, roll = 0."""
    return curvature_factor(v) * math.radians(1.0) / sr * v ** 2


# ---------------------------------------------------------------- the identified plant (report F1)
# u = a*theta + b*theta_dot + F*sign(theta_dot) + u0        [openpilot torque units]
BANDS = {
    "1-8":   dict(v=4.93,  a=0.00228, a_lo=0.00089, a_hi=0.00657,
                  b=0.00180, b_lo=0.0007, b_hi=0.0024, F=0.0120, LAF=3.19, LAF_m1=4.03, dead=0.134),
    "8-15":  dict(v=11.96, a=0.00764, a_lo=0.00617, a_hi=0.01063,
                  b=0.00366, b_lo=0.0023, b_hi=0.0044, F=0.0119, LAF=5.32, LAF_m1=5.32, dead=0.045),
    "15-22": dict(v=18.94, a=0.01149, a_lo=0.01007, a_hi=0.01329,
                  b=0.00409, b_lo=0.0017, b_hi=0.0061, F=0.0112, LAF=5.39, LAF_m1=5.39, dead=0.237),
    ">22":   dict(v=22.80, a=0.01539, a_lo=0.01475, a_hi=0.01809,
                  b=0.00489, b_lo=0.0034, b_hi=0.0130, F=0.0098, LAF=6.37, LAF_m1=6.37, dead=0.201),
}
# the table-chosen hold (report I1 "chosen" column) -- what the tables were built from
CHOSEN_A = {"1-8": 0.00168, "8-15": 0.00764, "15-22": 0.01149, ">22": 0.01539}


def band_for(v):
    if v < 8:
        return "1-8"
    if v < 15:
        return "8-15"
    if v < 22:
        return "15-22"
    return ">22"


def plant_at(v, key="a"):
    """linear interpolation of the identified coefficient across band medians (flat outside)."""
    vs = [BANDS[k]["v"] for k in ("1-8", "8-15", "15-22", ">22")]
    ys = [BANDS[k][key] for k in ("1-8", "8-15", "15-22", ">22")]
    return float(np.interp(v, vs, ys))


# ---------------------------------------------------------------- controller pieces (fork source)
LOW_SPEED_X = [0, 10, 20, 30]
LOW_SPEED_Y = [12, 10.5, 8, 5]
MIN_SPEED = 1.0
FRICTION_THRESHOLD = 0.3
JERK_GAIN = 0.22
MAX_LAT_JERK_UP = 2.5
LP_FILTER_CUTOFF_HZ = 1.2
JERK_LOOKAHEAD_SECONDS = 0.19
CC_JERK_DZ_SPEED_BP = [0.0, 5.0, 12.0, 25.0]
CC_JERK_DZ_SPEED_V = [0.08, 0.12, 0.18, 0.18]
CC_JERK_DZ_LA_BP = [0.0, 0.18, 0.35]
CC_JERK_DZ_LA_V = [1.0, 1.0, 0.0]
STEER_DELTA_PER_FRAME = 3.0 * DT          # honda values.py STEER_DELTA_UP/DOWN = 3, * DT_CTRL


def lsf(v):
    return (float(np.interp(v, LOW_SPEED_X, LOW_SPEED_Y)) / max(v, MIN_SPEED)) ** 2


def jerk_deadzone(v, setpoint):
    sd = float(np.interp(max(v, 0.0), CC_JERK_DZ_SPEED_BP, CC_JERK_DZ_SPEED_V))
    cw = float(np.interp(abs(setpoint), CC_JERK_DZ_LA_BP, CC_JERK_DZ_LA_V))
    return float(sd * cw)


class FOF:
    """openpilot common.filter_simple.FirstOrderFilter (alpha = dt/(rc+dt))."""

    def __init__(self, x0, rc, dt):
        self.x = float(x0)
        self.alpha = dt / (rc + dt)

    def update(self, x):
        self.x = (1.0 - self.alpha) * self.x + self.alpha * float(x)
        return self.x


class Cfg:
    def __init__(self, name, laf, kp, ki, friction, rate_gain=1.0, spring_scale=1.0,
                 gain_scale=1.0, plant_ff_on=True, g_v=None, k_v=None, lat_delay=0.30,
                 il_ka=None, il_kd=None, il_tau=0.03, il_rate_src="wire",
                 err_tau=0.0, fric_ff=0.0, fric_ff_w0=8.0, fric_hyst=0.0, fric_band=3.0,
                 hold_fn=None, ref_tau=0.0, notch_q=0.0, notch_fn=None, kv_taper=None):
        """notch_q > 0: a 2nd-order notch at notch_fn(v) Hz (Q = notch_q) on the lsf-inflated error before P and I.
        kv_taper(v): multiplier on il_kd (rate-loop gain) by speed."""
        self.notch_q, self.notch_fn, self.kv_taper = notch_q, notch_fn, kv_taper
        """ref_tau: two cascaded first-order LPFs (s each) on the setpoint in the Accord branch (reference shaping)."""
        self.ref_tau = ref_tau
        """fric_hyst: static-friction feedforward via a hysteresis operator on angle_des (torque), band in deg.
        hold_fn(angle_des_deg, v) -> signed hold torque, replaces the fork's spring*angle/gain when given."""
        self.fric_hyst, self.fric_band, self.hold_fn = fric_hyst, fric_band, hold_fn
        """err_tau: first-order LPF (s) on the lsf-inflated error before P and I (0 = none).
        fric_ff: feedforward Coulomb term F_ff * tanh(angle_des_rate / fric_ff_w0), torque units."""
        self.err_tau, self.fric_ff, self.fric_ff_w0 = err_tau, fric_ff, fric_ff_w0
        """il_ka(v) -> torque per degree of (angle_des - angle); il_kd(v) -> torque per deg/s of
        (angle_des_rate - wheel rate) through a first-order filter il_tau; None = no inner loop."""
        self.il_ka, self.il_kd, self.il_tau, self.il_rate_src = il_ka, il_kd, il_tau, il_rate_src
        self.name, self.LAF, self.KP, self.KI = name, laf, kp, ki
        self.friction, self.rate_gain = friction, rate_gain
        self.spring_scale, self.gain_scale = spring_scale, gain_scale
        self.plant_ff_on = plant_ff_on
        self.g_v, self.k_v = g_v, k_v
        self.lat_delay = lat_delay

    def __repr__(self):
        return ("%-10s LAF %4.1f  KP %.2f  Ki %.2f  fric %.4f  rg %.2f  ss %.2f  ffPF %d"
                % (self.name, self.LAF, self.KP, self.KI, self.friction, self.rate_gain,
                   self.spring_scale, self.plant_ff_on))


# the three configs under test
# configs of record
C0 = Cfg("C0-flown", 6.0, 0.30, 0.15, 0.000, rate_gain=0.5, plant_ff_on=False, lat_delay=0.30)
BRIEF = Cfg("brief", 12.0, 0.70, 0.20, 0.012, rate_gain=1.0, lat_delay=0.30)
FILE = Cfg("file-r2", 14.0, 0.85, 0.30, 0.011, rate_gain=1.0, lat_delay=0.30)


# ---------------------------------------------------------------- closed-loop simulation
MAX_LAT_JERK = 3.0 + 9.81 * 0.06     # clip_curvature's ISO limit with the road-roll allowance
MAX_LAT_ACCEL = 3.0 + 9.81 * 0.06


class Sim:
    def __init__(self, cfg, v, band=None, dead=None, a=None, b=None, F=None, sr_level=16.88,
                 plant_F_scale=1.0, dt=DT, J=0.0, meas_delay=0.0, spring_fn=None):
        """J: inertia (torque per deg/s^2); meas_delay: extra delay on the angle/rate MEASUREMENT (s);
        spring_fn(theta_deg, v) -> spring torque (signed), replaces a*theta when given."""
        self.J, self.meas_delay, self.spring_fn = J, meas_delay, spring_fn
        self.c, self.v, self.dt = cfg, v, dt
        k = band or band_for(v)
        B = BANDS[k]
        self.a = B["a"] if a is None else a
        self.b = B["b"] if b is None else b
        self.F = (B["F"] if F is None else F) * plant_F_scale
        self.dead = B["dead"] if dead is None else dead
        self.nd = max(int(round(self.dead / dt)), 1)
        self.sr_level = sr_level
        self.Adeg = lat_accel_per_deg(v, steer_ratio(10.0, sr_level))
        self.reset()

    def reset(self, phi0=0.0):
        c = self.c
        n = int(1.0 / self.dt)
        self.buf = [0.0] * n
        self.jerk_f = FOF(0.0, 1 / (2 * np.pi * LP_FILTER_CUTOFF_HZ), self.dt)
        self.mrate_f = FOF(0.0, 1 / (2 * np.pi * (MAX_LAT_JERK_UP - 0.5)), self.dt)
        self.rate_f = FOF(0.0, FF_RATE_RC, self.dt)
        self.prev_ang_des = 0.0
        self.prev_meas = self.Adeg * phi0
        self.prev_des = 0.0
        self.i = 0.0
        self.phi = phi0
        self.phidot = 0.0
        self.uhist = [0.0] * self.nd
        self.last_tq = 0.0
        self.limited = False
        self.curv = 0.0
        self.il_f = FOF(0.0, self.c.il_tau, self.dt)
        self.err_f = FOF(0.0, max(self.c.err_tau, 1e-6), self.dt)
        self.z_hyst = 0.0
        self.nz = None
        self.ref_f1 = FOF(0.0, max(self.c.ref_tau, 1e-6), self.dt); self.ref_f2 = FOF(0.0, max(self.c.ref_tau, 1e-6), self.dt)
        nm = max(int(round(self.meas_delay / self.dt)), 0)
        self.phihist = [phi0] * (nm + 1)
        self.ratehist = [0.0] * (nm + 1)
        self.dist = 0.0
        self.il_t = 0.0
        self.rel_t = 0.0
        self.pf_t = 0.0

    def _angle_des(self, setpoint):
        curv_des = setpoint / max(self.v ** 2, 1.0)
        sr = steer_ratio(self.phi, self.sr_level)      # controlsd uses the MEASURED angle
        return np.degrees(-curv_des * sr / curvature_factor(max(self.v, 0.1))), sr

    def step(self, curv_cmd, active=True, pressed=False):
        c, dt = self.c, self.dt
        # --- planner rate limit (clip_curvature)
        mx = MAX_LAT_JERK / max(self.v, MIN_SPEED) ** 2 * dt
        self.curv = float(np.clip(curv_cmd, self.curv - mx, self.curv + mx))
        mc = MAX_LAT_ACCEL / max(self.v, MIN_SPEED) ** 2
        self.curv = float(np.clip(self.curv, -mc, mc))
        des_curv = self.curv
        phi_m = self.phihist[0]; rate_m = self.ratehist[0]
        meas = self.Adeg * phi_m
        fut = des_curv * self.v ** 2
        if not active:
            self.i = 0.0
            self.buf.append(des_curv); self.buf.pop(0)
            self.prev_meas = meas
            self.mrate_f.x = 0.0; self.jerk_f.x = 0.0
            self.prev_des = fut
            self.rate_f.x = 0.0
            self.prev_ang_des = self._angle_des(fut)[0]
            self.ref_f1.x = fut; self.ref_f2.x = fut
            u = 0.0
            self.last_tq = 0.0
        else:
            nd = int(np.clip(c.lat_delay / dt, 1, len(self.buf)))
            exp_la = self.buf[-nd] * self.v ** 2
            self.buf.append(des_curv); self.buf.pop(0)
            raw_j = np.clip((fut - exp_la) / max(c.lat_delay, dt), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
            des_j = float(np.clip(self.jerk_f.update(raw_j), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP))
            setpoint = exp_la + des_j * c.lat_delay
            if c.ref_tau > 0:
                setpoint = self.ref_f2.update(self.ref_f1.update(setpoint))
            d_des = (setpoint - self.prev_des) / dt
            unwind = (d_des < -1.0) and (abs(setpoint) < 0.3)
            self.prev_des = setpoint
            mrate = float(np.clip(self.mrate_f.update((meas - self.prev_meas) / dt),
                                  -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP))
            self.prev_meas = meas
            L = lsf(self.v)
            err = setpoint - meas
            e_lsf = err * (1.0 + L / max(c.KP, 1e-3))
            if c.err_tau > 0:
                e_lsf = self.err_f.update(e_lsf)
            if c.notch_q > 0 and c.notch_fn is not None:
                # bilinear 2nd-order notch, coefficients recomputed each frame (speed-scheduled), state kept
                w0 = 2 * math.pi * c.notch_fn(self.v); K = math.tan(w0 * dt / 2.0); q = c.notch_q
                norm = 1.0 / (1.0 + K / q + K * K)
                b0 = (1 + K * K) * norm; b1 = 2 * (K * K - 1) * norm; b2 = b0
                a1 = b1; a2 = (1 - K / q + K * K) * norm
                if self.nz is None:
                    self.nz = [e_lsf, e_lsf, e_lsf, e_lsf]   # x1, x2, y1, y2
                x1, x2, y1, y2 = self.nz
                y = b0 * e_lsf + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
                self.nz = [e_lsf, x1, y, y1]
                e_lsf = y
            # friction relay
            dz = jerk_deadzone(self.v, setpoint)
            fj = math.copysign(max(abs(des_j) - dz, 0.0), des_j)
            x = e_lsf + JERK_GAIN * fj
            fr_t = c.friction * float(np.clip(x / FRICTION_THRESHOLD, -1, 1))
            if c.plant_ff_on:
                ang_des, _ = self._angle_des(setpoint)
                r = self.rate_f.update((ang_des - self.prev_ang_des) / dt)
                self.prev_ang_des = ang_des
                if c.hold_fn is not None:
                    lim = float(np.interp(self.v, MOVE_BP, MOVE_V))
                    pf = -(c.hold_fn(ang_des, self.v) + float(np.clip(c.rate_gain * r / (float(np.interp(self.v, G_BP, G_V)) * max(c.gain_scale, 0.1)), -lim, lim)))
                else:
                    pf = -plant_ff(ang_des, r, self.v, c.rate_gain, c.gain_scale, c.spring_scale)
                il = 0.0
                if c.fric_hyst > 0.0:
                    # hysteresis operator driven by the desired angle: z follows d(angle_des) inside a +-fric_hyst band
                    self.z_hyst = float(np.clip(self.z_hyst + (r * dt) * c.fric_hyst / c.fric_band, -c.fric_hyst, c.fric_hyst))
                    il += -self.z_hyst
                if c.fric_ff > 0.0:
                    il += -c.fric_ff * math.tanh(r / c.fric_ff_w0)   # steering frame -> controller frame
                if c.il_ka is not None or c.il_kd is not None:
                    # inner loop in the steering-angle frame (+left): ang_des vs the measured angle (kit frame = -phi)
                    e_a = ang_des - (-phi_m)
                    e_r = r - (-rate_m)
                    kdv = (c.il_kd(self.v) if c.il_kd else 0.0) * (c.kv_taper(self.v) if c.kv_taper else 1.0)
                    il_raw = (c.il_ka(self.v) if c.il_ka else 0.0) * e_a + kdv * e_r
                    il = -self.il_f.update(il_raw) if c.il_tau > 0 else -il_raw
                self.il_t = il; self.pf_t = pf; self.rel_t = fr_t
                ff_t = pf + fr_t + il
            else:
                ff_t = fut / c.LAF + fr_t
            f = ff_t * c.LAF
            kp, ki = c.KP, c.KI
            p = kp * e_lsf
            freeze = self.limited or pressed or (self.v < 0.3) or unwind
            if not freeze:
                i_new = self.i + ki * dt * e_lsf
                test = p + i_new + f
                hi = self.i if test > c.LAF else c.LAF
                lo = self.i if test < -c.LAF else -c.LAF
                self.i = float(np.clip(i_new, lo, hi))
            out = float(np.clip(p + self.i + f, -c.LAF, c.LAF))
            u = out / c.LAF
            self.p, self.f, self.e = p, f, err
        # honda rate limiter, applied to actuators.torque = -u
        at = -u
        at_l = float(np.clip(at, self.last_tq - STEER_DELTA_PER_FRAME, self.last_tq + STEER_DELTA_PER_FRAME))
        self.limited = abs(at - at_l) > 1e-2
        self.last_tq = at_l
        u_app = -at_l
        # plant, dead time then spring + coulomb + viscous (+ inertia if J > 0) + disturbance torque
        self.uhist.append(u_app)
        ud = self.uhist.pop(0) + self.dist
        spring = self.spring_fn(self.phi, self.v) if self.spring_fn is not None else self.a * self.phi
        if self.J <= 0.0:
            D = ud - spring
            if abs(D) <= self.F:
                self.phidot = 0.0
            else:
                self.phidot = (D - math.copysign(self.F, D)) / self.b
            self.phi += self.phidot * dt
        else:
            # J*phidd + b*phid + a*phi + F*sign(phid) = u ; semi-implicit Euler with a stiction test
            D = ud - spring - self.b * self.phidot
            if abs(self.phidot) < 1e-6 and abs(D) <= self.F:
                self.phidot = 0.0
            else:
                fr = math.copysign(self.F, self.phidot if abs(self.phidot) >= 1e-6 else D)
                self.phidot += (D - fr) / self.J * dt
            self.phi += self.phidot * dt
        self.phihist.append(self.phi); self.phihist.pop(0)
        self.ratehist.append(self.phidot); self.ratehist.pop(0)
        return u_app, self.phi, meas


def run(cfg, v, curv_fn, T=40.0, band=None, phi0=0.0, active_fn=None, dist_fn=None, **kw):
    """columns: t, u, phi, meas, i, phidot, plant_ff, relay, inner, p"""
    s = Sim(cfg, v, band=band, **kw)
    s.reset(phi0)
    n = int(T / DT)
    out = np.zeros((n, 10))
    for j in range(n):
        t = j * DT
        act = True if active_fn is None else active_fn(t)
        s.dist = dist_fn(t) if dist_fn is not None else 0.0
        u, phi, meas = s.step(curv_fn(t), active=act)
        out[j] = (t, u, phi, meas, s.i if act else 0.0, s.phidot, s.pf_t, s.rel_t, s.il_t, getattr(s, "p", 0.0))
    return out


