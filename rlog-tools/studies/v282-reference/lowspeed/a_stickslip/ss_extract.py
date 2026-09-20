"""a_stickslip stage 1: per route, dwell-then-jump episodes with the command decomposed through each dwell.

FRAME: everything in the +left steering-angle frame, torque in [-1,1] output units.
  cmd = cs_out = -(p+i+f)/LAF  (verified: resid rms 0.0008 on 6c, lstsq coef -0.0714 = -1/14)
  P_t=-p/LAF, I_t=-i/LAF, F_t=-f/LAF.  On the torque routes F_t = hold(angle_des) + move + z + rate_loop + dob_left,
  dob_left = -accordObserverTorque(logged)  (latcontrol_torque.py: inner_torque += -accord_dob_torque, logged = -accord_dob_torque).
  angle_des(+left) = -deg(setpoint/v^2 * sR_live * WB * (1 - SF v^2))  (sign verified: corr with measured angle +0.967).
DEMAND (group-identical, for matching): ad = s3turns.curv_to_angle(model curvature), sR 16.33.
DWELL: run of >= 0.20 s where |sr 5 Hz lp| < 1.0 deg/s AND the measured angle span <= 0.3 deg (sa LSB 0.1, sr LSB 1 deg/s),
  hands-off (active & ~pressed dilated 0.5 s), gap-free, while the DEMAND moves: |ad_lp2(end) - ad_lp2(start)| >= 0.5 deg.
BREAKAWAY index bk: first frame after the dwell where |aa - aa_dwell_end| >= 0.3 deg (within 0.5 s, else no jump).
JUMP: j30 = |aa[g1+30]-aa[g1]| (g1 = dwell end, the s4 definition), slip = travel until |sr lp| < 1 or reversal (<= 1.5 s).
"""
import sys, numpy as np
from scipy import ndimage
from sslib import *

import os
DWMIN = int(os.environ.get('DWMIN', '20'))   # frames; 20 = 0.20 s (primary), 12 = the s4 0.12 s sensitivity
OUT = BASE + '/lowspeed/a_stickslip/out' + ('' if DWMIN == 20 else f'_dw{DWMIN}')
os.makedirs(OUT, exist_ok=True)
PRE, POST = 150, 80           # window frames around breakaway
CH = ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'ad', 'angdes', 'sr', 'v')


def route(rk):
    S = V.load(rk); meta = S['meta']; grp = meta['group']
    p, fs = params(rk)
    LAF = float(p.get('SteerLatAccel', 'nan'))
    t = S['t']; n = len(t)
    v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0)
    act = S['active']
    press_d = ndimage.binary_dilation(S['pressed'], iterations=50)
    HO = act & ~press_d
    aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    sr = np.nan_to_num(S['sr'])
    ad = T.curv_to_angle(np.nan_to_num(S['model']) / vv ** 2, v)
    cmd = np.nan_to_num(S['out'])
    P_t = -np.nan_to_num(S['p']) / LAF; I_t = -np.nan_to_num(S['i']) / LAF; F_t = -np.nan_to_num(S['f']) / LAF
    sR = np.nan_to_num(S['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    torque = meta['eps'] == 'V293'
    dob_logged = np.interp(t, fs['t_s'], fs['dob']) if torque else np.zeros(n)
    dob_left = -dob_logged
    fric = float(p.get('AccordFrictionHyst', 0.0)) if torque else 0.0
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    level = p.get('AccordHoldLevel', '0') == '1'   # absent on rev 4/5 forks = no level (the key did not exist)
    rlg0 = float(p.get('AccordRateLoopGain', 0.0)) if torque else 0.0
    ffrg = float(p.get('AccordFFRateGain', 0.5))
    d_ang = np.r_[0.0, np.diff(angdes)]
    d_ang[~act] = 0.0
    d_ang[np.r_[True, ~act[:-1]]] = 0.0            # first active frame: primed, no step
    z = hyst_run(d_ang, fric, band(v, sched), act)
    rate_des = fo_filter(d_ang / 0.01, FF_RATE_RC, reset=~act)
    if torque:
        hold_ff = hold_torque(angdes, v, level)
        lim = np.interp(v, MOVE_LIM_BP, MOVE_LIM_V)
        move_ff = np.clip(ffrg * rate_des / np.interp(v, G_BP, G_V), -lim, lim)
    else:
        hold_ff = np.zeros(n); move_ff = np.zeros(n)
    rate_meas = fo_filter(sr, 0.03 if meta['group'] == 'T4' else RATE_LOOP_RC)   # rev 5 changed 0.03 -> 0.01
    rl = rlg0 * np.minimum(1.0, RATE_LOOP_TAPER_V / np.maximum(v, 0.1)) * (rate_des - rate_meas)
    z_resid = F_t - hold_ff - move_ff - rl - dob_left     # what the log says z must be
    hold_at_aa = hold_torque(aa, v, False)                 # spring torque at the ACTUAL angle (level 1 below 12.5)
    val = {}
    if torque:
        mm = HO & (v >= 2) & (v < 15)
        e = z_resid[mm] - z[mm]
        val = dict(z_rms=float(np.sqrt(np.mean(z[mm] ** 2))), zres_rms=float(np.sqrt(np.mean(z_resid[mm] ** 2))),
                   err_rms=float(np.sqrt(np.mean(e ** 2))), err_p95=float(np.percentile(np.abs(e), 95)),
                   corr=float(np.corrcoef(z[mm], z_resid[mm])[0, 1]))
    srl = V.lowpass(sr, 5.0)
    adl = V.lowpass(ad, 2.0)
    arrs = dict(cmd=cmd, P=P_t, I=I_t, F=F_t, hold_ff=hold_ff, move=move_ff, z=z, rl=rl, dob=dob_left, hold_aa=hold_at_aa,
                aa=aa, ad=ad, angdes=angdes, sr=sr, v=v)
    EP = []; W = {k: [] for k in CH}
    for a, b in V.runs(HO & (v >= 2.0) & (v < 15.0), t, min_s=1.0):
        low = np.abs(srl[a:b]) < 1.0
        i = 0; m_ = b - a
        while i < m_:
            if not low[i]:
                i += 1; continue
            j = i; lo_, hi_ = aa[a + i], aa[a + i]
            while j + 1 < m_ and low[j + 1]:
                x = aa[a + j + 1]
                if max(hi_, x) - min(lo_, x) > 0.3:
                    break
                lo_, hi_ = min(lo_, x), max(hi_, x); j += 1
            L = j - i + 1
            g0, g1 = a + i, a + j
            if L >= DWMIN and g0 - PRE >= a and g1 + POST + 150 < b:
                dem = adl[g1] - adl[g0]
                if abs(dem) >= 0.5:
                    s = np.sign(dem); base = aa[g1]
                    k = g1 + 1
                    while k < g1 + 50 and abs(aa[k] - base) < 0.3:
                        k += 1
                    if abs(aa[k] - base) >= 0.3 and k + POST < b:
                        bk = k; sj = np.sign(aa[bk] - base)
                        e_ = bk
                        while e_ < min(bk + 150, b - 1) and abs(srl[e_]) >= 1.0 and np.sign(srl[e_]) == sj:
                            e_ += 1
                        prev = aa[g0] - aa[g0 - 50]
                        kind = 'rest' if abs(prev) < 0.5 else ('cont' if np.sign(prev) == sj else 'rev')
                        EP.append(dict(route=rk, group=grp, i0=int(g0), i1=int(g1), bk=int(bk), v=float(v[bk]), dwell_s=L / 100.0,
                                       aa=float(aa[bk]), abs_aa=float(abs(aa[bk])), dem=float(dem), dem_rate=float(abs(dem) / (L / 100.0)),
                                       sdem=float(s), sjump=float(sj), with_demand=bool(sj == s), kind=kind,
                                       j30=float(abs(aa[g1 + 30] - aa[g1])), slip=float(abs(aa[e_] - base)),
                                       slip_s=float((e_ - bk) / 100.0), pk_rate=float(np.max(np.abs(srl[bk:bk + 60]))),
                                       gap_bk=float(s * (ad[bk] - aa[bk])), gap_g0=float(s * (ad[g0] - aa[g0])),
                                       gapdes_bk=float(s * (angdes[bk] - aa[bk])),
                                       k=float(k_of_v(v[bk])), band=float(band(v[bk], sched)), fric=fric, LAF=LAF,
                                       w_d0=int(g0 - (bk - PRE)), w_d1=int(g1 - (bk - PRE))))
                        sl = slice(bk - PRE, bk + POST)
                        for kk in CH:
                            W[kk].append(arrs[kk][sl].astype(np.float32))
            i = j + 1
    adr = V.deriv(adl)
    ex = {}
    for vb, (v0, v1) in enumerate([(2, 5), (5, 8), (8, 15)]):
        for abn, (a0_, a1_) in enumerate([(0, 15), (15, 45), (45, 90), (90, 1e9)]):
            mm = HO & (v >= v0) & (v < v1) & (np.abs(aa) >= a0_) & (np.abs(aa) < a1_)
            ex[f'{vb}_{abn}'] = dict(sec=float(mm.sum() / 100), moving_sec=float((mm & (np.abs(adr) >= 2)).sum() / 100),
                                     travel=float(np.abs(adr[mm]).sum() / 100))
    np.savez_compressed(f'{OUT}/{rk}_ss.npz', EP=np.array(EP, dtype=object), **{k: np.array(v_) for k, v_ in W.items()},
                        val=np.array(val, dtype=object), ex=np.array(ex, dtype=object), params=np.array(p, dtype=object))
    print(rk, grp, 'episodes', len(EP), 'val', {k: round(x, 4) for k, x in val.items()}, flush=True)


if __name__ == '__main__':
    for rk in sys.argv[1:]:
        route(rk)
