"""s5_09: candidate fork-side 100 Hz structures, simulated closed loop on the calibrated V293 plant (s5_05 variant calC:
J 8e-5, b 7e-4, F 0.022, round trip 80 ms, hold level 1.0/1.28/1.44/1.25), driven by the logged exogenous inputs of T64 (6c, 6d)
and T4 (75, the richest low-speed set).  Every candidate is ALSO run on a stress plant (J 5e-5, d 90 ms) to expose fragility.

Candidates (all keep rev 6.4's setpoint path, hold/hysteresis/observer/P/I unless stated):
  C0  rev 6.4 as flown
  C1  + inertia feedforward J_model * d2(angle_des)/dt2 (RC 0.05 filtered) and FF rate gain 1.0 (full 1/G)
  C2a rate loop OFF                                   (AccordRateLoopGain 0)
  C2b rate loop 2e-4 (the robust-damping gain from s5_06)
  C3  V282 emulation: rate reference = d(angle_des)/dt + 4/s * (angle_des - theta), rate loop 2e-4 (fork taper 12/v kept)
  C4  C3 + Smith predictor: P/I measurement and rate-loop measurement use theta + (model(u now) - model(u delayed)),
      nominal internal model J 8e-5, b 7e-4, k level-scaled, no friction, delay 8 frames
Metrics on the SIMULATED wheel (same frames): event angle lag/gain/rms error vs the model's desired angle, 2-10 Hz rate RMS in
events, by speed stratum; band |H| model->lat accel >= 15 m/s (NOT validated -- s5_05 fails on revision differences there).
Validation status of these predictions: event lag/gain/angle-corr of C0 reproduce measured (calC); rate texture PARTIAL; band FAIL.
"""
import json, sys, math
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
import s5ctl as C  # noqa: E402
import s5sim as SIM  # noqa: E402

V = L.V
LEVEL_BP = [5.0, 11.5, 18.5, 26.0]; LEVEL_V = [1.0, 1.28, 1.44, 1.25]


class Cand(C.Ctl):
    def __init__(self, rev, rate0=0.0, angle_des0=0.0, extra=None, opts=None):
        super().__init__(rev, rate0, angle_des0, extra)
        self.o = opts or {}
        self.acc_des = 0.0; self.prev_adr = 0.0
        self.m_th = self.m_om = self.md_th = self.md_om = 0.0
        self.uq = [0.0] * 8
        self.ang_int = 0.0

    def step(self, sp, meas, th, rate, v, roll, sR, stiff, aoff, pressed=False, limited=False, u_left_logged=None):
        o = self.o
        th_meas, rate_meas = th, rate
        if o.get('smith'):
            th_meas = th + (self.m_th - self.md_th); rate_meas = rate + (self.m_om - self.md_om)
            meas = 1.05 * C.la_from_angle(th_meas, aoff, v, roll, sR, stiff)
        if o.get('k_theta') or o.get('inertia'):
            # need angle_des BEFORE the base step to shape the rate reference; recompute it identically
            ad = C.angle_from_la(sp, v, roll, sR, stiff)
        bias = o['k_theta'] * (ad - (th_meas - aoff)) if o.get('k_theta') else 0.0   # deg/s added to the rate-loop reference
        u, cp = super().step(sp, meas, th_meas, rate_meas, v, roll, sR, stiff, aoff, pressed, limited, rl_ref_bias=bias)
        extra_u = 0.0
        if o.get('inertia'):
            a2 = C.DT / (0.05 + C.DT)
            self.acc_des += a2 * ((self.adr - self.prev_adr) / C.DT - self.acc_des)
            self.prev_adr = self.adr
            extra_u = o['inertia'] * self.acc_des                       # +left torque
            if o.get('move_full'):
                G = float(np.interp(v, C.G_BP, C.G_V))
                lim = float(np.interp(v, C.MOVE_LIM_BP, C.MOVE_LIM_V))
                extra_u += min(max(0.5 * self.adr / G, -lim), lim)      # the other half of the 1/G move term
        u = min(max(u + extra_u, -1.0), 1.0)
        if o.get('smith'):
            k = float(np.interp(v, C.HOLD_V_BP, C.HOLD_K_V)) * float(np.interp(v, LEVEL_BP, LEVEL_V))
            self.uq.append(u); ud = self.uq.pop(0)
            for _ in range(5):
                h = C.DT / 5
                acc = (u - 7e-4 * self.m_om - k * (self.m_th - aoff)) / 8e-5
                self.m_om += acc * h; self.m_th += self.m_om * h
                accd = (ud - 7e-4 * self.md_om - k * (self.md_th - aoff)) / 8e-5
                self.md_om += accd * h; self.md_th += self.md_om * h
        return u, cp


CANDS = {
    'C0_rev64': (dict(), dict()),
    'C1_inertia_movefull': (dict(), dict(inertia=8e-5, move_full=True)),
    'C2a_rateloop_off': (dict(rl_gain=0.0), dict()),
    'C2b_rateloop_2e-4': (dict(rl_gain=2e-4), dict()),
    'C3_v282_emul': (dict(rl_gain=2e-4), dict(k_theta=4.0)),
    'C4_v282_emul_smith': (dict(rl_gain=2e-4), dict(k_theta=4.0, smith=True)),
    'C1a_inertia_only': (dict(), dict(inertia=8e-5)),
    'C1b_movefull_only': (dict(), dict(inertia=1e-12, move_full=True)),
    'C5_movefull_inertia_rl2e-4': (dict(rl_gain=2e-4), dict(inertia=8e-5, move_full=True)),
}
PLANTS = {'calC': dict(F=0.022, d=8), 'stress': dict(F=0.022, d=9, J=5e-5)}
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '00000075--6c8687d5bd']
sel = sys.argv[1:] or list(CANDS)
sos210 = signal.butter(4, [2.0, 10.0], btype='band', fs=100, output='sos')


def lag_gain(x, y, maxlag=80):
    n = len(x); best, lag = -np.inf, 0
    for kk in range(0, maxlag + 1):
        xa, ya = x[:n - kk] - x[:n - kk].mean(), y[kk:] - y[kk:].mean()
        c = float(np.dot(xa, ya)) / max(np.linalg.norm(xa) * np.linalg.norm(ya), 1e-9)
        if c > best:
            best, lag = c, kk
    xa, ya = x[:n - lag] - x[:n - lag].mean(), y[lag:] - y[lag:].mean()
    return lag / 100.0, float(np.dot(xa, ya) / max(np.dot(xa, xa), 1e-9))


try:
    RES = json.load(open(L.OUT + 's5_09_candidates.json'))
except Exception:
    RES = {}
for cn in sel:
    extra, opts = CANDS[cn]
    for pn, pv in PLANTS.items():
        P = dict(SIM.PLANT_NOMINAL); P.update(pv)
        rows = []; bandsegs = []; stable = True
        for rk in ROUTES:
            S = V.load(rk); g = L.ROUTES[rk]['group'] if hasattr(L, 'ROUTES') else V.ROUTES[rk]['group']
            D = np.load(V.CACHE / f'{rk}.npz'); stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
            mask = V.usable(S, 3.0) & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['model'])
            rev = C.GROUP_REV[g]

            def mk(S_, j0, rev=rev):
                ad0 = C.angle_from_la(float(S_['setpoint'][j0]), float(S_['v'][j0]), float(np.nan_to_num(S_['roll'][j0])),
                                      float(np.nan_to_num(S_['sR'][j0], nan=16.84)), float(stiff[j0]))
                return Cand(rev, rate0=float(S_['sr'][j0]), angle_des0=ad0, extra=extra, opts=opts)
            R = SIM.simulate(S, stiff, mk, P, mask)
            m2 = mask & np.isfinite(R['th'])
            if np.nanmax(np.abs(R['rate'][m2])) > 3000:
                stable = False
            roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84); aoff = np.nan_to_num(S['aoff'])
            ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
            for e in ev:
                i0, i1 = e['idx'] - 150, e['idx'] + 300
                if not m2[i0:i1].all():
                    continue
                model = np.nan_to_num(S['model'][i0:i1])
                ad = np.array([C.angle_from_la(model[q], float(S['v'][i0 + q]), roll[i0 + q], sR[i0 + q], stiff[i0 + q]) for q in range(i1 - i0)])
                th = R['th'][i0:i1] - aoff[i0:i1]
                lg, gn = lag_gain(V.lowpass(ad, 5), V.lowpass(th, 5))
                rows.append(dict(v=e['v'], ang_lag=lg, ang_gain=gn,
                                 err_deg=float(np.sqrt(np.mean((th - ad - np.mean(th - ad)) ** 2))),
                                 hf=float(np.sqrt(np.mean(signal.sosfiltfilt(sos210, R['rate'][i0:i1]) ** 2)))))
            for a, b in V.runs(m2 & (S['v'] >= 15), S['t'], min_s=30):
                bandsegs.append((np.nan_to_num(S['model'][a:b]), R['la'][a:b]))
            del S, R
        out = dict(stable=stable)
        for vb in ((3, 8), (8, 15), (15, 99)):
            sl = [r for r in rows if vb[0] <= r['v'] < vb[1]]
            if len(sl) < 3:
                continue
            out[f'v{vb[0]}-{vb[1]}'] = dict(n=len(sl), **{k: round(float(np.median([r[k] for r in sl])), 3) for k in ('ang_lag', 'ang_gain', 'err_deg', 'hf')})
        for nm, f1, f2 in (('b015', 0.15, 0.30), ('b030', 0.30, 0.60), ('b060', 0.60, 1.2)):
            h = V.band_H(bandsegs, f1, f2)
            out[nm] = h and round(h['H'], 3)
        RES.setdefault(cn, {})[pn] = out
        print(cn, pn, json.dumps(out), flush=True)
    json.dump(RES, open(L.OUT + 's5_09_candidates.json', 'w'), indent=1)
