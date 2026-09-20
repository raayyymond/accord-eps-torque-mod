"""a_stickslip shared helpers.  Fork functions COPIED VERBATIM (arithmetic) from
openpilots/raayyymond-StarPilot/StarPilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py
(the module imports opendbc/openpilot and cannot be imported here)."""
import sys, json, math
import numpy as np
BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE); sys.path.insert(0, BASE + '/s3_accel')
import v282cmp as V
import s3turns as T

# --- fork constants (latcontrol_vehicle_tunes.py) ---
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_LEVEL_BP = [12.5, 17.5]; HOLD_LEVEL_V = [1.15, 1.45]
HOLD_SAT = (19.3, 546.0, 3.01)
BAND_BP = [8.0, 12.0, 19.0, 26.0]; BAND_V = [3.0, 2.10, 0.96, 0.60]; BAND_FLAT = 3.0
G_BP = [5.0, 12.5, 18.5, 28.5]; G_V = [550.0, 271.0, 246.0, 167.0]
MOVE_LIM_BP = [8.0, 10.0]; MOVE_LIM_V = [1.0, 1.4]
FF_RATE_RC = 0.10; RATE_LOOP_RC = 0.01; RATE_LOOP_TAPER_V = 12.0


def k_of_v(v):
    return np.interp(v, HOLD_V_BP, HOLD_K_V)


def hold_torque(angle, v, level=True):
    angle = np.clip(angle, -400, 400)
    k = k_of_v(v) * (np.interp(v, HOLD_LEVEL_BP, HOLD_LEVEL_V) if level else 1.0)
    sat = HOLD_SAT[0] + HOLD_SAT[1] * np.exp(-np.maximum(v, 0.0) / HOLD_SAT[2])
    return k * sat * np.tanh(angle / sat)


def band(v, scheduled=True):
    return np.interp(v, BAND_BP, BAND_V) if scheduled else np.full_like(np.asarray(v, float), BAND_FLAT)


def hyst_run(d_ang, fric, bandv, active):
    """honda_accord_friction_hysteresis stepped per frame; z=0 whenever inactive (inactive branch resets it)."""
    z = np.zeros(len(d_ang)); zz = 0.0
    for n in range(len(d_ang)):
        if not active[n] or fric <= 0:
            zz = 0.0
        else:
            zz = float(np.clip(zz + d_ang[n] * fric / max(bandv[n], 1e-3), -fric, fric))
        z[n] = zz
    return z


def fo_filter(x, rc, dt=0.01, reset=None):
    a = dt / (rc + dt); y = np.zeros(len(x)); s = 0.0
    for n in range(len(x)):
        if reset is not None and reset[n]:
            s = 0.0
        s = s + a * (x[n] - s); y[n] = s
    return y


def params(rk):
    D = np.load(f'{BASE}/fill_straightroad/cache/{rk}_fsr.npz')
    p = json.loads(str(D['params_json']))
    fs = dict(t_s=D['t_s'], dob=D['dob'], dob_fz=D['dob_fz'], s_ff=D['s_ff'])
    return p, fs
