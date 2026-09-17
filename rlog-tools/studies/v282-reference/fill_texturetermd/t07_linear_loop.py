"""t07: LINEARISED closed loop of the flown fork feedback terms on an identified plant, as an exact 100 Hz discrete
state-space map (every state the replica carries: plant, delay line, rate-loop filter, error notch, integrator, observer).
Eigenvalues -> the closed-loop wheel mode frequency and damping per speed, and per term ablation (which feedback term moves
the mode).  This is a MODEL (BELIEF-grade until t08's measured frequencies agree with it).

Linear pieces, +left torque frame (from s5ctl / latcontrol_torque 84766cdc):
  u_p   = -(kp/laf) * notch_v( (1 + lsf/kp) * cf(v) v^2 (pi/180)/sR * theta )          (P on the measurement)
  u_i   = -(1/laf) * I,  I += ki*dt*(same notched error)                               (I)
  u_rl  = -g(v) * rm,  rm += dt/(rc+dt) (omega - rm)                                   (rate loop, measured part)
  u_dob = fade(v) * w2_prev;  resid = u(t-60ms) - (kh(v) theta + omega/G(v) + Jm acc);  two poles at dob_hz   (observer)
  plant: J th'' + b th' + k th = u(t - d)      (ZOH, exact)
"""
import sys, json, math
import numpy as np
from scipy import linalg
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
import s5ctl as C  # noqa: E402

DT = 0.01
WB = 2.83; SR = 16.84
_M = 3279 * 0.453592 + 136.0; _AF = 0.39 * WB; _AR = WB - _AF


def curv_factor(v):
    VM = C.VM
    VM.update_params(1.0, SR)
    return float(VM.curvature_factor(v))


def build(v, J, b, kpl, d, rev='rev64', drop=(), rl_gain=None, dob_hz=None):
    P = dict(C.REV[rev])
    if rl_gain is not None:
        P['rl_gain'] = rl_gain
    if dob_hz is not None:
        P['dob_hz'] = dob_hz
    laf, kp = P['laf'], P['kp']
    ki = P['ki'] if P['ki_high'] <= 0 else float(np.interp(v, C.KI_BP, [P['ki'], P['ki_high']]))
    lsf = (float(np.interp(v, C.LOW_SPEED_X, C.LOW_SPEED_Y)) / max(v, 1.0)) ** 2
    Kth = (1 + lsf / kp) * curv_factor(v) * v * v * math.pi / 180.0 / SR
    g = P['rl_gain'] * min(1.0, C.RATE_LOOP_TAPER_V / max(v, 0.1))
    a_rl = DT / (P['rl_rc'] + DT)
    G = float(np.interp(v, C.G_BP, C.G_V))
    kh = float(np.interp(v, C.HOLD_V_BP, C.HOLD_K_V)) * (float(np.interp(v, C.HOLD_LEVEL_BP, C.HOLD_LEVEL_V)) if P['hold_level'] else 1.0)
    fade = float(np.interp(v, C.DOB_FADE_BP, [0.0, 1.0]))
    # notch coefficients
    fq, q = C.mode_hz(v), P['notch_q']
    kk = math.tan(math.pi * min(fq, 0.45 / DT) * DT); norm = 1 / (1 + kk / q + kk * kk)
    b0 = (1 + kk * kk) * norm; b1 = 2 * (kk * kk - 1) * norm; a2 = (1 - kk / q + kk * kk) * norm
    notch_on = q > 0
    # plant ZOH
    Ac = np.array([[0, 1], [-kpl / J, -b / J]]); Bc = np.array([[0], [1 / J]])
    M = linalg.expm(np.block([[Ac, Bc], [np.zeros((1, 3))]]) * DT)
    Ad, Bd = M[:2, :2], M[:2, 2]
    nd = max(d, 1); ndob = C.DOB_DELAY_N
    names = ['th', 'om'] + [f'ub{i}' for i in range(nd)] + ['rm', 'nx1', 'nx2', 'ny1', 'ny2', 'I'] + [f'uh{i}' for i in range(ndob)] + ['acc', 'prev_om', 'w1', 'w2', 'dob']
    ix = {n: i for i, n in enumerate(names)}
    N = len(names)

    def step(x):
        y = np.zeros(N)
        th, om = x[ix['th']], x[ix['om']]
        # rate loop
        rm = x[ix['rm']] + a_rl * (om - x[ix['rm']])
        u_rl = -g * rm if 'rl_fb' not in drop else 0.0
        # P / I on notched error
        e = Kth * th
        if notch_on:
            en = b0 * e + b1 * x[ix['nx1']] + b0 * x[ix['nx2']] - b1 * x[ix['ny1']] - a2 * x[ix['ny2']]
        else:
            en = e
        u_p = -(kp * en) / laf if 'p_meas' not in drop else 0.0
        I = x[ix['I']] + ki * DT * en
        u_i = -I / laf if 'i' not in drop else 0.0
        u_dob = x[ix['dob']] if ('dob' not in drop and P['dob_hz'] > 0) else 0.0
        u = u_p + u_i + u_rl + u_dob
        # observer update with this frame's u
        if P['dob_hz'] > 0 and 'dob' not in drop:
            u_del = x[ix['uh0']]
            acc = x[ix['acc']] + (DT / (C.DOB_ACC_RC + DT)) * ((om - x[ix['prev_om']]) / DT - x[ix['acc']])
            resid = u_del - (kh * th + om / G + C.J_MODEL * acc)
            al = DT / (1 / (2 * math.pi * P['dob_hz']) + DT)
            w1 = x[ix['w1']] + al * (resid - x[ix['w1']]); w2 = x[ix['w2']] + al * (w1 - x[ix['w2']])
            y[ix['acc']] = acc; y[ix['prev_om']] = om; y[ix['w1']] = w1; y[ix['w2']] = w2; y[ix['dob']] = fade * w2
            for i in range(ndob - 1):
                y[ix[f'uh{i}']] = x[ix[f'uh{i+1}']]
            y[ix[f'uh{ndob-1}']] = u
        # plant with delayed u
        ua = x[ix['ub0']]
        p = Ad @ np.array([th, om]) + Bd * ua
        y[ix['th']], y[ix['om']] = p
        for i in range(nd - 1):
            y[ix[f'ub{i}']] = x[ix[f'ub{i+1}']]
        y[ix[f'ub{nd-1}']] = u
        y[ix['rm']] = rm
        y[ix['nx2']] = x[ix['nx1']]; y[ix['nx1']] = e; y[ix['ny2']] = x[ix['ny1']]; y[ix['ny1']] = en
        y[ix['I']] = I
        return y
    A = np.column_stack([step(np.eye(N)[:, i]) for i in range(N)])
    return A, ix


def modes(A, fmin=0.3, fmax=8.0):
    z = np.linalg.eigvals(A)
    out = []
    for zz in z:
        if abs(zz) < 1e-9 or np.imag(zz) <= 0:
            continue
        s = np.log(zz) / DT
        wn = abs(s); f = wn / (2 * np.pi); zeta = -np.real(s) / wn
        if fmin <= np.imag(s) / (2 * np.pi) <= fmax:
            out.append((float(np.imag(s) / (2 * np.pi)), float(zeta), float(f)))
    return sorted(out, key=lambda m: m[1])


if __name__ == '__main__':
    S5 = json.load(open(ttd.BASE + 's5_mechanism/s5_02_plant_ident.json'))

    def s5s(v):
        key = '3-8' if v < 8 else '8-15' if v < 15 else '15-22' if v < 22 else '22-40'
        return S5[key]
    RES = {}
    for plant_name in ('IV_bhi', 'IV_blo', 'S5'):
        RES[plant_name] = {}
        for v in (4, 6, 8, 10, 12.5, 15, 18, 22, 26):
            s = s5s(v)
            kpl = float(np.interp(v, C.HOLD_V_BP, C.HOLD_K_V)) * s['s']
            if plant_name == 'IV_bhi':
                J, b, d = 1.03e-4, 1.2e-3, 5
            elif plant_name == 'IV_blo':
                J, b, d = 1.03e-4, 5e-4, 5
            else:
                J, b, d = s['J'], max(s['b'], 1e-5), int(round(s['d'] * 100))
            row = {}
            for label, kw in (('flown', {}), ('no_dob', dict(drop=('dob',))), ('no_rl', dict(drop=('rl_fb',))), ('no_p', dict(drop=('p_meas', 'i'))),
                              ('rl0006', dict(rl_gain=0.0006)), ('rl002', dict(rl_gain=0.002)), ('dob03', dict(dob_hz=0.3)), ('open', dict(drop=('dob', 'rl_fb', 'p_meas', 'i')))):
                A, _ = build(v, J, b, kpl, d, **kw)
                ms = [m for m in modes(A) if m[0] >= 0.8]
                row[label] = ms[:3]
            RES[plant_name][v] = row
            fl = row['flown'][:2]
            print(f"{plant_name:7s} v {v:5.1f}  J {J:.1e} b {b:.1e} k {kpl:.4f} d {d}  " + ' | '.join(
                f"{lab}: " + ','.join(f"{m[0]:.2f}Hz z{m[1]:+.2f}" for m in row[lab][:2]) for lab in ('flown', 'no_dob', 'no_rl', 'no_p', 'rl0006', 'rl002', 'open')))
    json.dump(RES, open(ttd.OUT + 't07_linear_loop.json', 'w'), indent=1)
