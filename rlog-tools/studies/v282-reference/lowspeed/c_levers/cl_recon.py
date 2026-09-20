"""c_levers: reconstruct the fork's Accord torque-mode feedforward terms frame by frame from logged signals, validate the
reconstruction against the LOGGED pid.f, then measure each existing lever's quantity inside the low-speed stick-slip and
shake situations.  Nothing here predicts a dose: every number is a quantity AS LOGGED (or reconstructed and validated).

Frames (EVIDENCE, from latcontrol_torque.py @84766cdc):
  setpoint / measurement / p / i / f are in the TORQUE frame (= -angle frame): measurement = -calc_curvature(angle)*v^2.
  pid_log.output = -output_torque is in the ANGLE frame (+left).  So, in the angle frame:
     out = -(p + i + f)/LAF (unsaturated),   -f/LAF = hold + move + z + Kv*(rate_des - rate_meas) + dob_left,
     dob_left = -accordObserverTorque(logged)   (latcontrol_torque.py:850 logs -accord_dob_torque).
  angle_des = deg(VM.get_steer_from_curvature(-curv_des, v, roll*fade)), sR = accord map(|steeringAngleDeg|)*level/16.88.

usage: python cl_recon.py            (all torque routes, one at a time)
"""
import sys, json, math, gc
from pathlib import Path
import numpy as np
from scipy import signal, ndimage

BASE = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(BASE / 's3_accel'))
import v282cmp as V
import s3turns as T

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
FS = V.FS; DT = 0.01

# ---- fork constants (latcontrol_vehicle_tunes.py @84766cdc; rev-specific ones overridden per route) ----
SR_BP = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0]
SR_V = [16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68, 14.45, 14.09, 14.25, 12.98, 12.31]
G_BP = [5.0, 12.5, 18.5, 28.5]; G_V = [550.0, 271.0, 246.0, 167.0]
HOLD_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
SAT = (19.3, 546.0, 3.01)
MOVE_LIM_BP = [8.0, 10.0]; MOVE_LIM_V = [1.0, 1.4]
BAND_BP = [8.0, 12.0, 19.0, 26.0]; BAND_V = [3.0, 2.10, 0.96, 0.60]
FF_RATE_RC = 0.10
LOW_SPEED_X = [0, 10, 20, 30]; LOW_SPEED_Y = [12, 10.5, 8, 5]
DITHER_REF = 0.15
DOB_FADE = [3.0, 6.0]

# per-route flown config (EVIDENCE: initData census, fill_lagbudgetand/census_params.json) and code-version constants
CFG = {
    '0000006c--68c6e94b17': dict(g='T64', LAF=14.0, Kp=1.0, Ki=0.3, KiH=0.0, Kv=0.001, rate_rc=0.01, hyst=0.015, sched=True, level=(1.15, 1.45), ffr=0.5, dob=0.6),
    '0000006d--05e83bb04f': dict(g='T64', LAF=14.0, Kp=1.0, Ki=0.3, KiH=0.0, Kv=0.001, rate_rc=0.01, hyst=0.015, sched=True, level=(1.15, 1.45), ffr=0.5, dob=0.6),
    '0000006e--6ca3e014fd': dict(g='T64B', LAF=14.0, Kp=1.0, Ki=0.3, KiH=0.0, Kv=0.001, rate_rc=0.01, hyst=0.015, sched=True, level=None, ffr=0.5, dob=0.6),
    '00000076--d0b7ea7e4d': dict(g='T5', LAF=14.0, Kp=1.0, Ki=0.3, KiH=0.0, Kv=0.001, rate_rc=0.01, hyst=0.015, sched=False, level=None, ffr=0.5, dob=0.6),
    '00000075--6c8687d5bd': dict(g='T4', LAF=14.0, Kp=0.85, Ki=0.6, KiH=2.5, Kv=0.0006, rate_rc=0.03, hyst=0.015, sched=False, level=None, ffr=0.5, dob=0.0),
}
# chassis (opendbc Accord, s3turns)
L = T.WB; SF0 = T.SF; G_ACC = 9.81


def lp_run(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)


def bp_run(x, f1, f2, order=2):
    return signal.sosfiltfilt(signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos'), x)


def fo_filter(x, rc, x0):
    """openpilot FirstOrderFilter, alpha = dt/(rc+dt), causal."""
    a = DT / (rc + DT)
    return signal.lfilter([a], [1, -(1 - a)], x, zi=[(1 - a) * x0])[0]


def hyst_run(dang, fr, band):
    z = 0.0; out = np.empty(len(dang))
    for k in range(len(dang)):
        z = min(max(z + dang[k] * fr / max(band[k], 1e-3), -fr), fr)
        out[k] = z
    return out


def reconstruct(rk):
    c = CFG[rk]
    S = V.load(rk)
    R = np.load(V.CACHE / f'{rk}.npz')
    t = S['t']; n = len(t)
    csact = R['cs_active'] > 0.5
    v = np.nan_to_num(S['v']); sa = np.nan_to_num(S['sa']); aoff = np.nan_to_num(S['aoff']); srate = np.nan_to_num(S['sr'])
    roll = np.nan_to_num(S['roll']); stiff = np.interp(t, R['t_lp'], R['stiff'])
    Fz = np.load(BASE / 'fill_straightroad' / 'cache' / f'{rk}_fsr.npz', allow_pickle=True)
    dob_logged = np.interp(t, Fz['t_s'], Fz['dob']) if len(Fz['t_s']) else np.zeros(n)
    del Fz
    setp = R['cs_la_des']; p = R['cs_p']; i_ = R['cs_i']; f = R['cs_f']; out = R['cs_out']
    LAF = c['LAF']
    # angle_des (angle frame)
    sR = np.interp(np.abs(sa), SR_BP, SR_V) * 16.84 / 16.88
    sf = SF0 / np.maximum(stiff, 0.1)
    fade_roll = np.interp(v, [0.5, 2.5], [0.0, 1.0])
    rollc = G_ACC * roll * fade_roll / (1.0 / sf - v ** 2)
    curv_des = setp / np.maximum(v ** 2, 1.0)
    cf = 1.0 / ((1.0 - sf * v ** 2) * L)
    angle_des = np.degrees((-curv_des - rollc) * sR / cf)
    # terms, run by run (states reset at the inactive->active edge as the fork does)
    hold = np.zeros(n); move = np.zeros(n); z = np.zeros(n); rate_t = np.zeros(n); rate_des = np.zeros(n)
    runs = V.runs(csact, t, min_s=0.2)
    for a, b in runs:
        ad = angle_des[a:b]; vv = v[a:b]
        d_ang = np.diff(ad, prepend=ad[0])
        rd = fo_filter(d_ang / DT, FF_RATE_RC, 0.0)
        rate_des[a:b] = rd
        G = np.interp(vv, G_BP, G_V)
        lim = np.interp(vv, MOVE_LIM_BP, MOVE_LIM_V)
        move[a:b] = np.clip(c['ffr'] * rd / G, -lim, lim)
        k = np.interp(vv, HOLD_BP, HOLD_K)
        if c['level']:
            k = k * np.interp(vv, [12.5, 17.5], list(c['level']))
        sat = SAT[0] + SAT[1] * np.exp(-np.maximum(vv, 0) / SAT[2])
        hold[a:b] = k * sat * np.tanh(np.clip(ad, -400, 400) / sat)
        band = np.interp(vv, BAND_BP, BAND_V) if c['sched'] else np.full(len(vv), 3.0)
        z[a:b] = hyst_run(d_ang, c['hyst'], band)
        rm = fo_filter(srate[a:b], c['rate_rc'], srate[a])
        kv = c['Kv'] * np.minimum(1.0, 12.0 / np.maximum(vv, 0.1))
        rate_t[a:b] = kv * (rd - rm)
    dob_left = -dob_logged
    F_rec = hold + move + z + rate_t + dob_left
    F_log = -f / LAF
    lsf = (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, 0.01)) ** 2   # MIN_SPEED guard differs <0.01 only
    return dict(rk=rk, g=c['g'], cfg=c, t=t, v=v, sa=sa - aoff, sr=srate, csact=csact, active=S['active'], pressed=S['pressed'],
                model=np.nan_to_num(S['model']), angle_des=angle_des, rate_des=rate_des,
                hold=hold, move=move, z=z, rate_t=rate_t, dob=dob_left, F_rec=F_rec, F_log=F_log,
                P=-p / LAF, I=-i_ / LAF, out=out, lsf=lsf, storque=np.nan_to_num(S['storque']))


def validate(D, lo=0.0, hi=15.0):
    m = D['csact'] & (D['v'] >= lo) & (D['v'] < hi) & np.isfinite(D['F_log'])
    r = D['F_rec'][m] - D['F_log'][m]
    tot = D['P'][m] + D['I'][m] + D['F_log'][m]
    unsat = np.abs(D['out'][m]) < 0.99
    return dict(n=int(m.sum()), corr=float(np.corrcoef(D['F_rec'][m], D['F_log'][m])[0, 1]),
                rms_res=float(np.sqrt(np.mean(r ** 2))), rms_Flog=float(np.sqrt(np.mean(D['F_log'][m] ** 2))),
                p50_absres=float(np.median(np.abs(r))), p95_absres=float(np.percentile(np.abs(r), 95)),
                out_vs_sum_rms=float(np.sqrt(np.mean((D['out'][m][unsat] - tot[unsat]) ** 2))))


if __name__ == '__main__':
    res = {}
    for rk in CFG:
        D = reconstruct(rk)
        res[rk] = dict(g=D['g'], lt15=validate(D, 0, 15), lt8=validate(D, 0, 8), ge15=validate(D, 15, 99))
        print(rk, json.dumps(res[rk]), flush=True)
        del D; gc.collect()
    json.dump(res, open(OUT / 'validate.json', 'w'), indent=1)
