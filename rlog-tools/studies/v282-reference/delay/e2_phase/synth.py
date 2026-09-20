"""Synthetic plant for the MANDATORY positive control.

    J*acc = u(t - D) - b*rate - k(v)*angle - F*sign(rate)      (+ optional disturbance torque d(t))

u = the ACTUAL logged 0xE4 command of a torque route (in +angle torque units, -e4/4089), zero-order held from each
sendcan logMonoTime, delayed by a known D. Integrated at 1 kHz with stick-slip Coulomb friction. Sampled at the
route's ACTUAL carState logMonoTime stamps, quantised angle 0.1 deg / rate 1 deg/s, then put on the grid with the
same linear interpolation as the real data. k(v) = the fork's HONDA_ACCORD_HOLD_K_V at the logged speed.

closed=True adds a feedback controller run at each send stamp on the measurement sampled D_ctl = 11 ms earlier
(the message chain's measured value): u = u_exo - Kr*min(1,12/v)*rate_f - Ka*angle_q, rate_f = 10 ms first-order
filter -- a stand-in for the fork's rate loop / P / observer -- plus a band-limited disturbance torque. That variant
is the closed-loop BIAS test (direct vs IV), not part of the mandated control.
"""
import numpy as np
from scipy import signal
import common as C

V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]


def simulate(R, mask, D, J=8e-5, b=0.003, F=0.02, closed=False, Kr=0.0006, Ka=0.0, dist_rms=0.0, D_ctl=0.011,
             seed=0, dt=0.001, pre=2.0):
    rng = np.random.default_rng(seed)
    t_e4 = R["t_e4"]; u_exo_all = -R["e4"] / C.E4_SCALE
    t_cst = R["t_cst"]
    sa_s = np.full(len(t_cst), np.nan); sr_s = np.full(len(t_cst), np.nan)
    u_app_all = u_exo_all.copy()
    tg = R["t"]; v_g = R["v"]
    for i0, i1, _ in C.chunks(mask, R["v"]):
        ta, tb = tg[i0] - pre, tg[i1 - 1] + 0.05
        ka = np.searchsorted(t_e4, ta); kb = np.searchsorted(t_e4, tb)
        if kb - ka < 100:
            continue
        ts = t_e4[ka:kb]; ue = u_exo_all[ka:kb].copy(); ua = ue.copy()
        n = int((tb - ta) / dt) + 1
        tt = ta + dt * np.arange(n)
        kk = np.interp(np.interp(tt, tg, v_g), V_BP, K_V)
        vv = np.interp(tt, tg, v_g)
        if dist_rms > 0:
            sos = signal.butter(2, [0.5, 8.0], btype="band", fs=1 / dt, output="sos")
            d = signal.sosfilt(sos, rng.standard_normal(n)); d *= dist_rms / max(np.std(d), 1e-12)
        else:
            d = np.zeros(n)
        k0 = kk[0]
        ang = float(np.clip(ue[0] / k0, -30, 30)); rate = 0.0
        A = np.empty(n); Rt = np.empty(n)
        # time at which each command becomes active at the plant, and in closed loop when it is computed
        t_act = ts + D
        j = 0          # index of the active command
        jc = 0         # index of the next command to compute (closed loop)
        rate_f = 0.0
        u_now = ua[0]
        for s in range(n):
            t = tt[s]
            if closed:
                while jc < len(ts) and ts[jc] <= t:
                    # measurement from D_ctl before the send, quantised
                    sidx = int((ts[jc] - D_ctl - ta) / dt)
                    if sidx >= 0:
                        rq = round(Rt[sidx]); aq = round(A[sidx] * 10) / 10
                    else:
                        rq = 0.0; aq = 0.0
                    rate_f += (rq - rate_f) * (0.01 / (0.01 + 0.01))
                    g = Kr * min(1.0, 12.0 / max(vv[s], 0.1))
                    ua[jc] = ue[jc] - g * rate_f - Ka * aq
                    jc += 1
            while j + 1 < len(ts) and t_act[j + 1] <= t:
                j += 1
            u_now = ua[j] if t_act[j] <= t else ua[0]
            k = kk[s]
            net = u_now + d[s] - k * ang
            if rate != 0.0:
                acc = (net - b * rate - F * np.sign(rate)) / J
                nr = rate + dt * acc
                if nr * rate < 0:
                    nr = 0.0
            else:
                if abs(net) <= F:
                    nr = 0.0
                else:
                    nr = dt * (net - F * np.sign(net)) / J
            rate = nr
            ang += dt * rate
            A[s] = ang; Rt[s] = rate
        c0 = np.searchsorted(t_cst, ta + pre * 0.5); c1 = np.searchsorted(t_cst, tb)
        sa_s[c0:c1] = np.round(np.interp(t_cst[c0:c1], tt, A) * 10) / 10
        sr_s[c0:c1] = np.round(np.interp(t_cst[c0:c1], tt, Rt))
        u_app_all[ka:kb] = ua
    ok = np.isfinite(sa_s)
    S = dict(R)
    S["sa"] = np.interp(tg, t_cst[ok], sa_s[ok]); S["sr"] = np.interp(tg, t_cst[ok], sr_s[ok])
    S["u"] = np.interp(tg, t_e4, -u_app_all)          # keep the cache convention u = +e4/4089 (sign applied in fit)
    S["zexo"] = np.interp(tg, t_e4, -u_exo_all)
    return S
