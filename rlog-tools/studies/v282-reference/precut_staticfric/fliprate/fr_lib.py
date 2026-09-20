"""fliprate stream: is the one-sided outward static-friction feedforward its own excitation?

ARITHMETIC MIRRORED FROM THE FORK (read-only), latcontrol_torque.py Accord branch:
  curv_des      = (setpoint - latAccelOffset*fade) / max(v^2, 1)          (logged setpoint = cs_la_des, ALREADY
                  ref-shaped: two cascaded RC=AccordRefFilter first-order filters)
  angle_des     = deg(VM.get_steer_from_curvature(-curv_des, v, roll*fade))
  d_angle_des   = angle_des - prev                                        (reset while inactive)
  angle_des_rate= first-order RC=HONDA_ACCORD_FF_RATE_RC (0.10 s) on d_angle_des/dt   (reset while inactive)

THE CANDIDATE (designed, not cut):
  s_a  = tanh(angle_des / A)          A = 1.0 deg
  s_r  = tanh(angle_des_rate / R)     R = 2.0 deg/s
  z_out= level * g(v) * max(0, s_a*s_r) * s_a        g: 1.0 at v<=8 -> 0.0 at v>=12
  inner_torque = -(z + z_out + rate_loop_gain*(angle_des_rate - rate_meas))
So in the +LEFT steering-angle frame the command gains EXACTLY +z_out (F_t = -f/LAF = hold+move+z+rl+dob_left,
and inner_torque enters F_t with the sign flipped again -- see a_stickslip/ss_extract.py's verified decomposition).

NOTE on the algebra of z_out: max(0, s_a*s_r)*s_a == s_a^2 * s_r whenever s_a*s_r > 0, else 0.  s_a^2 >= 0, so the
sign of z_out is the sign of s_r, which in the live branch equals the sign of s_a.  The function is CONTINUOUS at
the flip (both one-sided limits are 0) -- the flip is a KINK, not a step.  dz/dt at the flip = level*g*s_a^2*ds_r/dt.
"""
import os, sys, json, math
import numpy as np
from scipy import signal, ndimage

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
HERE = BASE + '/precut_staticfric/fliprate'
OUT = HERE + '/out'
sys.path.insert(0, BASE)
sys.path.insert(0, BASE + '/s3_accel')
sys.path.insert(0, BASE + '/lowspeed/a_stickslip')
import v282cmp as V
import s3turns as T
os.makedirs(OUT, exist_ok=True)

FS = 100.0
DT = 0.01
FF_RATE_RC = 0.10                 # HONDA_ACCORD_FF_RATE_RC
LEVEL = 0.020                     # HONDA_ACCORD_HOLD_STATIC_FRICTION (declared, no reader -- verified)
A_SCALE = 1.0                     # deg
R_SCALE = 2.0                     # deg/s
GATE_BP = [8.0, 12.0]             # g(v): 1 -> 0
# observer (HondaAccordDisturbanceObserver + HONDA_ACCORD_DOB_*)
DOB_DELAY = 0.06
DOB_FADE_V_BP = [3.0, 6.0]
DOB_MAX = 0.3
# measured yardsticks handed down by the study (do NOT re-derive here, they are inputs)
CMD_SLEW_P99 = 0.25              # torque/s, measured p99 command slew
HONDA_RATE_LIM = 3.0             # torque/s, 0.03/frame
CMD_P99 = 0.4275                 # p99 |cmd|
SHAKE = (1.8, 3.5)               # the band the drive is scored on


def gate(v):
    return np.interp(v, GATE_BP, [1.0, 0.0])


def fo_filter(x, rc, dt=DT, reset=None):
    """First-order filter EXACTLY as FirstOrderFilter: s += a*(x-s), a = dt/(rc+dt)."""
    a = dt / (rc + dt)
    y = np.zeros(len(x)); s = 0.0
    for n in range(len(x)):
        if reset is not None and reset[n]:
            s = 0.0
        s = s + a * (x[n] - s)
        y[n] = s
    return y


def z_out_of(angdes, rate_des, v, level=LEVEL, a_scale=A_SCALE, r_scale=R_SCALE):
    """Vectorised candidate.  Verified against a per-frame scalar loop in _self_test()."""
    s_a = np.tanh(angdes / a_scale)
    s_r = np.tanh(rate_des / r_scale)
    return level * gate(v) * np.maximum(0.0, s_a * s_r) * s_a


def prep(rk, roll_comp=False, ang_off=0.0, lat_accel_offset=0.0):
    """Everything on the controlsState clock, +left steering-angle frame, torque in [-1,1] output units.

    angle_des exactly as VehicleModel.get_steer_from_curvature(-curv_des, v, roll*fade) with chi = 0:
        angle_des = -deg(curv_des * sR * WB * (1 - SF v^2))  -  deg(g * roll * fade * SF * sR * WB)
    The roll leg is SPEED-INDEPENDENT (roll_compensation = g*roll*SF/(1 - SF v^2), and the 1/(1-SF v^2)
    cancels): 0.182 deg per 0.01 rad of roll.  fade = interp(v, [0.5, 2.5], [0, 1]).
    `ang_off` is the robustness knob for everything this reconstruction cannot see (the learner's
    latAccelOffset, which the fork folds into curv_des as -latAccelOffset*fade/v^2, plus any angle bias).
    `lat_accel_offset` applies the fork's own form of that term instead (m/s^2)."""
    S = V.load(rk)
    meta = S['meta']
    t = S['t']; n = len(t)
    v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0)
    act = S['active']
    press_d = ndimage.binary_dilation(S['pressed'], iterations=50)
    HO = act & ~press_d
    aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    sR = np.nan_to_num(S['sR'], nan=16.33)
    fade = np.interp(v, [0.5, 2.5], [0.0, 1.0])
    curv = (np.nan_to_num(S['setpoint']) - lat_accel_offset * fade) / vv ** 2
    angdes = -np.degrees(curv * sR * T.WB * (1 - T.SF * v ** 2))
    if roll_comp:
        angdes = angdes - np.degrees(9.81 * np.nan_to_num(S['roll']) * fade * T.SF * sR * T.WB)
    angdes = np.clip(angdes + ang_off, -400.0, 400.0)      # HONDA_ACCORD_FF_ANGLE_LIMIT_DEG
    d_ang = np.r_[0.0, np.diff(angdes)]
    d_ang[~act] = 0.0
    d_ang[np.r_[True, ~act[:-1]]] = 0.0          # first active frame: primed, no step
    rate_des = fo_filter(d_ang / DT, FF_RATE_RC, reset=~act)
    R = dict(rk=rk, group=meta.get('group', '?'), t=t, v=v, HO=HO, act=act, aa=aa, sr=np.nan_to_num(S['sr']),
             angdes=angdes, d_ang=d_ang, rate_des=rate_des, cmd=np.nan_to_num(S['out']),
             corr_angdes_aa=float(np.corrcoef(angdes[HO], aa[HO])[0, 1]) if HO.sum() > 100 else float('nan'))
    del S
    return R


def dob_perturbation(z, v, f_hz=0.6, delay=DOB_DELAY, fade_bp=DOB_FADE_V_BP):
    """The observer is IN the path it observes: u_left carries z AND -w2, and residual = u_left(t-D) - model.
    Holding the car's measured motion fixed (so the model terms do not change), the perturbation algebra is
        du = z - fade*dw2 ;  dresid = du(t-D) ;  dw1 += a(dresid-dw1) ; dw2 += a(dw1-dw2)
    i.e. surviving/injected = 1/(1 + LP2(s) e^{-sD}) -- 0.5 at DC, ->1 above the 0.6 Hz corner.
    Returns (du = what the command actually gains, dw2 = what the observer takes back)."""
    nd = max(int(round(delay / DT)), 1)
    a = DT / (1.0 / (2.0 * math.pi * f_hz) + DT)
    fade = np.interp(v, fade_bp, [0.0, 1.0])
    du = np.zeros(len(z)); dw2v = np.zeros(len(z))
    hist = [0.0] * nd
    w1 = w2 = 0.0
    for n in range(len(z)):
        d = z[n] - fade[n] * w2
        du[n] = d
        resid = hist[0]
        hist.append(d); hist.pop(0)
        w1 += a * (resid - w1)
        w2 += a * (w1 - w2)
        dw2v[n] = fade[n] * w2
    return du, dw2v


def band_rms(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], btype='band', fs=FS, output='sos')
    return float(np.sqrt(np.mean(signal.sosfiltfilt(sos, x) ** 2)))


def psd_sum(segs, nps_max=1024):
    """Length-weighted PSD over a list of 1-D segments (no concatenation across gaps)."""
    segs = [s for s in segs if len(s) >= 256]
    if not segs:
        return None, None, 0.0
    nps = min(nps_max, int(2 ** np.floor(np.log2(min(len(s) for s in segs)))))
    P = None; fr = None; sec = 0.0
    for s in segs:
        f, p = signal.welch(s - s.mean(), FS, nperseg=nps, noverlap=nps // 2)
        w = len(s)
        P = p * w if P is None else P + p * w
        fr = f; sec += w / FS
    return fr, P / (sec * FS), sec


def band_power(fr, P, f1, f2):
    m = (fr >= f1) & (fr < f2)
    return float(np.sum(P[m]) * (fr[1] - fr[0]))


def _self_test():
    """Positive controls. (1) vectorised z_out == a per-frame scalar loop. (2) the one-sided shape is
    zero on every inward frame and equals level*g*s_a^2*s_r on every outward frame. (3) fo_filter matches
    a first-order step response. (4) the DOB perturbation algebra gives 0.5 at DC and ->1 well above 0.6 Hz."""
    rng = np.random.default_rng(1)
    ad = np.cumsum(rng.standard_normal(4000)) * 0.05
    rd = V.deriv(ad)
    vv = np.full(4000, 6.0)
    zv = z_out_of(ad, rd, vv)
    zs = np.empty(4000)
    for n in range(4000):
        sa = math.tanh(ad[n] / A_SCALE); sr = math.tanh(rd[n] / R_SCALE)
        zs[n] = LEVEL * float(gate(vv[n])) * max(0.0, sa * sr) * sa
    assert np.max(np.abs(zv - zs)) < 1e-15, np.max(np.abs(zv - zs))
    inward = (np.sign(ad) * np.sign(rd)) < 0
    assert np.all(zv[inward] == 0.0)
    outward = (np.sign(ad) * np.sign(rd)) > 0
    ref = LEVEL * np.tanh(ad / A_SCALE) ** 2 * np.tanh(rd / R_SCALE)
    assert np.max(np.abs(zv[outward] - ref[outward])) < 1e-15
    assert np.all(np.sign(zv[outward]) == np.sign(ad[outward]))     # always OUTWARD
    st = fo_filter(np.ones(200), 0.10)
    assert abs(st[9] - (1 - (1 - DT / 0.11) ** 10)) < 1e-12
    assert abs(st[10] - (1 - (1 - DT / 0.11) ** 11)) < 1e-12, st[10]   # discrete 0.6495 vs continuous 0.632
    # DOB algebra: DC step -> 0.5 survives; 3 Hz sine -> ~1 survives
    du, _ = dob_perturbation(np.ones(3000), np.full(3000, 10.0))
    assert abs(du[-1] - 0.5) < 0.01, du[-1]
    tt = np.arange(3000) * DT
    s3 = np.sin(2 * np.pi * 3.0 * tt)
    du3, _ = dob_perturbation(s3, np.full(3000, 10.0))
    g3 = np.sqrt(np.mean(du3[1000:] ** 2)) / np.sqrt(np.mean(s3[1000:] ** 2))
    assert 0.93 < g3 < 1.10, g3
    return (f'self-test OK: vectorised==scalar loop (max |d| 0; one-sided, always outward); fo_filter step '
            f'{st[10]:.4f}; DOB survival DC {du[-1]:.3f}, 3 Hz {g3:.3f}')


if __name__ == '__main__':
    print(_self_test())
