"""fliprate stage 0: POSITIVE CONTROL on the reconstruction, IN THE BAND THE STREAM IS ABOUT.

The whole stream rests on the 1.8-3.5 Hz content of `angle_des_rate`, which is RECONSTRUCTED (the fork logs no
angle_des).  Control: the fork's own feedforward F_t = -pid.f/LAF is LOGGED, and on the torque routes
    F_t = hold(angle_des) + move(angle_des_rate) + z(hysteresis) + rate_loop + dob_left
(the decomposition a_stickslip/ss_extract.py verified).  Rebuild every term from the same angle_des and compare
F_hat with the logged F_t band by band.  If the 1.8-3.5 Hz content matches, the derivative path's HF is real.
Legs reported: |H| and coherence of logged-on-reconstructed per band, and the same with the MOVE term (the only
term carrying angle_des_rate) zeroed -- if zeroing it does not hurt the band, the band is not the derivative's.
Also: clock-gap census, and the sensitivity of the flip rate to (a) including roll compensation in angle_des and
(b) zeroing d_angle_des across clock gaps.
"""
import sys, json
import numpy as np
from fr_lib import *
sys.path.insert(0, BASE + '/lowspeed/a_stickslip')
import sslib as SL

BANDS = dict(dc=(0.02, 0.6), lo=(0.6, 1.8), shake=SHAKE, hi=(3.5, 8.0), vhi=(8.0, 25.0))


def one(rk):
    R = prep(rk)
    S = V.load(rk)
    p, fs = SL.params(rk)
    LAF = float(p.get('SteerLatAccel', 'nan'))
    t = R['t']; v = R['v']; n = len(t)
    F_t = -np.nan_to_num(S['f']) / LAF
    dtv = np.diff(t)
    gaps = int(np.sum(dtv > 1.5 / FS))
    torque = V.ROUTES[rk]['eps'] == 'V293'
    fric = float(p.get('AccordFrictionHyst', 0.0)) if torque else 0.0
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    level = p.get('AccordHoldLevel', '0') == '1'
    rlg0 = float(p.get('AccordRateLoopGain', 0.0)) if torque else 0.0
    ffrg = float(p.get('AccordFFRateGain', 0.5))
    angdes = R['angdes']; d_ang = R['d_ang']; rate_des = R['rate_des']
    z_h = SL.hyst_run(d_ang, fric, SL.band(v, sched), R['act'])
    dob_left = -np.interp(t, fs['t_s'], fs['dob']) if torque else np.zeros(n)
    if torque:
        hold_ff = SL.hold_torque(angdes, v, level)
        lim = np.interp(v, SL.MOVE_LIM_BP, SL.MOVE_LIM_V)
        move = np.clip(ffrg * rate_des / np.interp(v, SL.G_BP, SL.G_V), -lim, lim)
    else:
        hold_ff = np.zeros(n); move = np.zeros(n)
    rate_meas = fo_filter(R['sr'], 0.03 if R['group'] == 'T4' else 0.01)
    rl = rlg0 * np.minimum(1.0, 12.0 / np.maximum(v, 0.1)) * (rate_des - rate_meas)
    F_hat = hold_ff + move + z_h + rl + dob_left
    m = R['HO'] & (v < 15.0)
    sub = V.runs(m, t, min_s=2.56)
    out = dict(route=rk, group=R['group'], sec=round(sum(b - a for a, b in sub) / FS, 1),
               gaps_over_1p5dt=gaps, dt_p99=round(float(np.percentile(dtv, 99)), 4),
               corr_angdes_aa=round(R['corr_angdes_aa'], 4), bands={})
    for nm, (f1, f2) in BANDS.items():
        h = V.band_H([(F_hat[a:b], F_t[a:b]) for a, b in sub], f1, f2)
        h0 = V.band_H([((F_hat - move)[a:b], F_t[a:b]) for a, b in sub], f1, f2)
        rF = np.sqrt(sum(band_rms(F_t[a:b], f1, f2) ** 2 * (b - a) for a, b in sub) / sum(b - a for a, b in sub))
        rH = np.sqrt(sum(band_rms(F_hat[a:b], f1, f2) ** 2 * (b - a) for a, b in sub) / sum(b - a for a, b in sub))
        rM = np.sqrt(sum(band_rms(move[a:b], f1, f2) ** 2 * (b - a) for a, b in sub) / sum(b - a for a, b in sub))
        out['bands'][nm] = dict(H=round(h['H'], 3) if h else None, coh=round(h['coh'], 3) if h else None,
                                H_nomove=round(h0['H'], 3) if h0 else None,
                                coh_nomove=round(h0['coh'], 3) if h0 else None,
                                rms_Flog=round(float(rF), 6), rms_Fhat=round(float(rH), 6),
                                rms_move=round(float(rM), 6))
    # --- HOW BIG CAN THE UNSEEN DC OFFSET IN angle_des BE?  Scan a constant angle offset c into the hold
    # term and pick the c that best explains the LOGGED feedforward.  hold is ~k(v) torque/deg (0.005 at
    # 5 m/s), so the DC leg of F_t is a sharp instrument on c.  Also the naive aa - angdes gap. ---
    mlow = R['HO'] & (v >= 2.0) & (v < 12.0)
    best = None; scan = {}
    if torque and mlow.sum() > 500:
        for c in np.arange(-4.0, 4.01, 0.25):
            Fh = SL.hold_torque(angdes + c, v, level) + move + z_h + rl + dob_left
            e = float(np.sqrt(np.mean((F_t[mlow] - Fh[mlow]) ** 2)))
            scan[round(float(c), 2)] = round(e, 6)
            if best is None or e < best[1]:
                best = (float(c), e)
    out['ang_offset'] = dict(best_c_deg=best[0] if best else None, best_rms=round(best[1], 6) if best else None,
                             rms_at_0=scan.get(0.0), scan={k: sv for k, sv in scan.items() if abs(k) <= 2.01},
                             aa_minus_angdes_mean=round(float(np.mean(R['aa'][mlow] - angdes[mlow])), 3) if mlow.sum() else None,
                             aa_minus_angdes_p50=round(float(np.median(R['aa'][mlow] - angdes[mlow])), 3) if mlow.sum() else None,
                             roll_leg_p50_deg=round(float(np.median(-np.degrees(9.81 * np.nan_to_num(S['roll'][mlow]) * T.SF * 16.33 * T.WB))), 3),
                             roll_leg_p5_p95=[round(float(x), 3) for x in np.percentile(
                                 -np.degrees(9.81 * np.nan_to_num(S['roll'][mlow]) * T.SF * 16.33 * T.WB), [5, 95])])
    # --- sensitivity of the flip rate: roll comp in angle_des, and zeroing d_ang across clock gaps ---
    z0 = z_out_of(angdes, rate_des, v)
    O0 = (np.tanh(angdes / A_SCALE) * np.tanh(rate_des / R_SCALE)) > 0
    R2 = prep(rk, roll_comp=True)
    O2 = (np.tanh(R2['angdes'] / A_SCALE) * np.tanh(R2['rate_des'] / R_SCALE)) > 0
    z2 = z_out_of(R2['angdes'], R2['rate_des'], v)
    dg = d_ang.copy(); dg[np.r_[False, dtv > 1.5 / FS]] = 0.0
    rd3 = fo_filter(dg / DT, FF_RATE_RC, reset=~R['act'])
    O3 = (np.tanh(angdes / A_SCALE) * np.tanh(rd3 / R_SCALE)) > 0
    z3 = z_out_of(angdes, rd3, v)
    mm = m & (v < 12.0)
    sec = mm.sum() / FS

    def nflip(O):
        c = 0
        for a, b in V.runs(m, t, min_s=1.0):
            d = np.diff(O[a:b].astype(int)) != 0
            c += int(np.sum(d & (v[a + 1:b] < 12.0)))
        return c
    out['sens'] = dict(sec_under12=round(sec, 1),
                       flips_base=round(nflip(O0) / sec * 100, 2),
                       flips_rollcomp=round(nflip(O2) / sec * 100, 2),
                       flips_gapzero=round(nflip(O3) / sec * 100, 2),
                       z_rms_base=round(float(np.sqrt(np.mean(z0[mm] ** 2))), 5),
                       z_rms_rollcomp=round(float(np.sqrt(np.mean(z2[mm] ** 2))), 5),
                       z_rms_gapzero=round(float(np.sqrt(np.mean(z3[mm] ** 2))), 5))
    # flip rate / z_rms / band content vs a constant angle_des offset (the unseen-bias robustness leg)
    off = {}
    for c in (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0):
        Rc = prep(rk, ang_off=c)
        zc = z_out_of(Rc['angdes'], Rc['rate_des'], v)
        Oc = (np.tanh(Rc['angdes'] / A_SCALE) * np.tanh(Rc['rate_des'] / R_SCALE)) > 0
        sgn = np.sign(Rc['angdes'])
        off[c] = dict(flips=round(nflip(Oc) / sec * 100, 1), z_rms=round(float(np.sqrt(np.mean(zc[mm] ** 2))), 5),
                      z_mean_signed_left=round(float(np.mean(zc[mm])), 5),
                      z_shake=round(float(np.sqrt(np.mean([band_rms(zc[a:b], *SHAKE) ** 2 * (b - a) for a, b in sub])
                                                  / np.mean([b - a for a, b in sub]))), 6))
        del Rc
    out['ang_off_sweep'] = {str(k): sv for k, sv in off.items()}
    del S, R, R2
    return out


if __name__ == '__main__':
    res = {}
    for rk in (sys.argv[1:] or [k for k, mv in V.ROUTES.items()]):
        r = one(rk)
        res[rk] = r
        print(f"{rk} {r['group']} {r['sec']}s gaps {r['gaps_over_1p5dt']} dt_p99 {r['dt_p99']} corr {r['corr_angdes_aa']}")
        for nm, b in r['bands'].items():
            print(f"   {nm:6s} |H| {b['H']} coh {b['coh']} | no-move |H| {b['H_nomove']} coh {b['coh_nomove']} "
                  f"| rms log {b['rms_Flog']} hat {b['rms_Fhat']} move {b['rms_move']}")
        print('   sens', r['sens'])
        print('   ang_offset', {k: sv for k, sv in r.get('ang_offset', {}).items() if k != 'scan'})
        for c, row in r.get('ang_off_sweep', {}).items():
            print(f"   off {c:>5s} deg -> flips/100s {row['flips']:7.1f}  z_rms {row['z_rms']:.5f}  "
                  f"z_mean(+left) {row['z_mean_signed_left']:+.5f}  z_shake {row['z_shake']:.6f}")
        print(flush=True)
    with open(f'{OUT}/fr_valid.json', 'w') as f:
        json.dump(res, f, indent=1)
