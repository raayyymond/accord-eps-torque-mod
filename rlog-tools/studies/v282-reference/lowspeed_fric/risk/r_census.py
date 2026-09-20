"""risk stream, stage 1: per-route census of what a RAISED low-speed friction-hysteresis term would do.

Rebuilds the fork's z operator (honda_accord_friction_hysteresis, verbatim arithmetic via sslib.hyst_run)
under a set of candidate (friction, band) SCHEDULES, on every engaged hands-off frame of every route, and
measures -- against the FLOWN z -- where the extra torque lands:

  * highway leak      : any frame at v >= 10 m/s where z_cand != z_flown  (the term is a zero-phase spring
                        above ~0.5 Hz, so a leak at speed is a real cost)
  * over-delivery     : on frames where the wheel is already MOVING (|sr_lp| >= 2 deg/s, i.e. friction is
                        already broken), the extra torque s*dz has nowhere to go but extra angle:
                        d_angle_settled = s*dz / k'(v), k' = the MEASURED breakaway stiffness
                        (a_stickslip breakaway_fit), not the fork's map.
  * ceiling vs slope  : fraction of time |z| is clipped at the ceiling (if it rarely clips, the CEILING is
                        not the binding constraint and only the SLOPE friction/band can change the reach)
  * chatter           : 1.8-3.5 Hz rms of z itself (the drive's own shake band) and z zero-crossing rate
  * transition slew   : d(z)/dt forced by the schedule while accelerating through the knot region

Everything is EVIDENCE about the term's own arithmetic on logged demand.  Nothing here predicts a
closed-loop outcome.
"""
import sys, os, json
import numpy as np
from scipy import ndimage, signal

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip')
sys.path.insert(0, BASE)
from sslib import *            # noqa: F403  (V, T, fork constants, hyst_run, fo_filter, params, band, hold_torque, k_of_v)

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
os.makedirs(OUT, exist_ok=True)

# MEASURED breakaway stiffness and Coulomb friction, a_stickslip/out/ss_analyze.json -> breakaway_fit.at_breakaway
KP_MEAS = {'2-5': 0.004767, '5-8': 0.008010, '8-15': 0.006603}
F_MEAS = {'2-5': 0.029784, '5-8': 0.032092, '8-15': 0.018195}
VBINS = [('2-5', 2.0, 5.0), ('5-8', 5.0, 8.0), ('8-15', 8.0, 15.0), ('15-22', 15.0, 22.0), ('22+', 22.0, 99.0)]

# ---------------------------------------------------------------------------------------------------
# candidate schedules.  (friction breakpoints, friction values, band breakpoints, band values)
# flown = AccordFrictionHyst 0.015 flat + AccordFrictionHystBand on.
FLOWN = dict(fbp=[0.0, 99.0], fv=[0.015, 0.015], bbp=BAND_BP, bv=BAND_V)
CAND = {
    'C0_flown':      FLOWN,
    # pure Galaxy toggle: AccordFrictionHyst 0.015 -> 0.030.  No code change, and no way to keep it low-speed.
    'C1_toggle_030': dict(fbp=[0.0, 99.0], fv=[0.030, 0.030], bbp=BAND_BP, bv=BAND_V),
    # ceiling only, knot at 8->12 (needs code: the level is not scheduled today)
    'C2_lvl033_k12': dict(fbp=[8.0, 12.0], fv=[0.033, 0.015], bbp=BAND_BP, bv=BAND_V),
    # slope only: narrow the low-speed band, ceiling unchanged (under-reaches by construction)
    'C3_band110':    dict(fbp=[0.0, 99.0], fv=[0.015, 0.015], bbp=BAND_BP, bv=[1.10, 2.10, 0.96, 0.60]),
    # the one that actually reaches the measured 0.033 inside a 2.4 deg dwell: slope 0.0138, ceiling 0.033
    'C4_reach_k12':  dict(fbp=[8.0, 12.0], fv=[0.033, 0.015], bbp=BAND_BP, bv=[2.40, 2.10, 0.96, 0.60]),
    # half of C4
    'C5_half_k12':   dict(fbp=[8.0, 12.0], fv=[0.024, 0.015], bbp=BAND_BP, bv=[2.70, 2.10, 0.96, 0.60]),
    # C4 with the knots moved BELOW 8 m/s: byte-identical to flown at every v >= 8
    'C6_reach_k68':  dict(fbp=[6.0, 8.0], fv=[0.033, 0.015], bbp=[6.0, 8.0, 12.0, 19.0, 26.0],
                          bv=[2.40, 3.00, 2.10, 0.96, 0.60]),
}


def sched(c, v):
    f = np.interp(v, c['fbp'], c['fv'])
    b = np.interp(v, c['bbp'], c['bv'])
    return f, b


def hyst_run_v(d_ang, fricv, bandv, active):
    """honda_accord_friction_hysteresis with PER-FRAME friction and band (speed-scheduled level)."""
    z = np.zeros(len(d_ang)); zz = 0.0
    for n in range(len(d_ang)):
        f = fricv[n]
        if not active[n] or f <= 0:
            zz = 0.0
        else:
            zz = float(np.clip(zz + d_ang[n] * f / max(bandv[n], 1e-3), -f, f))
        z[n] = zz
    return z


def bp_rms(x, f0, f1, fs=100.0):
    b, a = signal.butter(2, [f0 / (fs / 2), f1 / (fs / 2)], btype='band')
    y = signal.filtfilt(b, a, x)
    return y


def route(rk):
    S = V.load(rk); meta = S['meta']; grp = meta['group']
    p, fs = params(rk)
    LAF = float(p.get('SteerLatAccel', 'nan'))
    t = S['t']; n = len(t)
    v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0)
    act = S['active']
    HO = act & ~ndimage.binary_dilation(S['pressed'], iterations=50)
    aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    sr = np.nan_to_num(S['sr']); srl = V.lowpass(sr, 5.0)
    cmd = np.nan_to_num(S['out'])
    sR = np.nan_to_num(S['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    d_ang = np.r_[0.0, np.diff(angdes)]
    d_ang[~act] = 0.0
    d_ang[np.r_[True, ~act[:-1]]] = 0.0
    torque = meta['eps'] == 'V293'
    fric_flown = float(p.get('AccordFrictionHyst', 0.0)) if torque else 0.0
    sched_flown = p.get('AccordFrictionHystBand', '0') == '1'

    Z = {}
    for cn, c in CAND.items():
        fv, bv = sched(c, v)
        Z[cn] = hyst_run_v(d_ang, fv, bv, act)
    # the z the car ACTUALLY ran (params as flown), for the validation column
    z_flownreal = hyst_run(d_ang, fric_flown, band(v, sched_flown), act)

    R = dict(route=rk, group=grp, eps=meta['eps'], fric_flown=fric_flown, band_sched=sched_flown,
             z_c0_vs_real_rms=float(np.sqrt(np.mean((Z['C0_flown'] - z_flownreal) ** 2))) if torque else None,
             bins={})
    # per-frame band-passed z, once per candidate (whole route; masks applied after)
    ZH = {cn: bp_rms(Z[cn], 1.8, 3.5) for cn in CAND}

    for bn, v0, v1 in VBINS:
        m = HO & (v >= v0) & (v < v1)
        if m.sum() < 200:
            continue
        kp = KP_MEAS.get(bn, KP_MEAS['8-15']); Fm = F_MEAS.get(bn, F_MEAS['8-15'])
        mov = m & (np.abs(srl) >= 2.0)          # wheel already sliding -> friction is broken, extra torque -> extra angle
        s_mov = np.sign(srl[mov])
        d = dict(sec=float(m.sum() / 100.0), sec_moving=float(mov.sum() / 100.0), kprime=kp, F_meas=Fm, cand={})
        z0 = Z['C0_flown']
        for cn in CAND:
            z = Z[cn]; dz = z - z0
            fv, bv = sched(CAND[cn], v)
            e = dict(
                slope=float(np.median(fv[m] / bv[m])), ceil=float(np.median(fv[m])),
                z_rms=float(np.sqrt(np.mean(z[m] ** 2))),
                frac_at_ceiling=float(np.mean(np.abs(z[m]) >= 0.98 * fv[m])),
                dz_rms=float(np.sqrt(np.mean(dz[m] ** 2))), dz_absmax=float(np.max(np.abs(dz[m]))),
                dz_frac_nonzero=float(np.mean(np.abs(dz[m]) > 1e-6)),
                hf_rms=float(np.sqrt(np.mean(ZH[cn][m] ** 2))),
                zcross_per100s=float(np.sum(np.diff(np.sign(z[m])) != 0) / (m.sum() / 100.0)),
            )
            if mov.sum() > 50:
                over = s_mov * dz[mov]                       # extra torque in the direction the wheel is going
                ang = over / kp                              # extra settled angle, deg (measured stiffness)
                e.update(over_p50=float(np.percentile(over, 50)), over_p90=float(np.percentile(over, 90)),
                         over_frac_gt_halfF=float(np.mean(over > 0.5 * Fm)),
                         over_frac_gt_F=float(np.mean(over > Fm)),
                         dangle_p50=float(np.percentile(ang, 50)), dangle_p90=float(np.percentile(ang, 90)),
                         dangle_p99=float(np.percentile(ang, 99)))
            d['cand'][cn] = e
        R['bins'][bn] = d

    # transition slew: how fast does a scheduled ceiling drag z down while accelerating through the knots
    acc = np.gradient(v, 0.01)
    tr = HO & (v >= 5.0) & (v < 13.0)
    R['transition'] = dict(sec=float(tr.sum() / 100.0),
                           dvdt_p95=float(np.percentile(np.abs(acc[tr]), 95)) if tr.sum() > 100 else None)
    for cn in CAND:
        dzdt = np.gradient(Z[cn] - Z['C0_flown'], 0.01)
        R['transition'][cn] = float(np.percentile(np.abs(dzdt[tr]), 99)) if tr.sum() > 100 else None
    np.savez_compressed(f'{OUT}/{rk}_z.npz', **{cn: Z[cn].astype(np.float32) for cn in CAND},
                        v=v.astype(np.float32), HO=HO, aa=aa.astype(np.float32), srl=srl.astype(np.float32),
                        cmd=cmd.astype(np.float32), angdes=angdes.astype(np.float32))
    return R


if __name__ == '__main__':
    allR = {}
    fn = f'{OUT}/r_census.json'
    if os.path.exists(fn):
        allR = json.load(open(fn))
    for rk in sys.argv[1:]:
        allR[rk] = route(rk)
        json.dump(allR, open(fn, 'w'), indent=1)
        print(rk, 'done', flush=True)
