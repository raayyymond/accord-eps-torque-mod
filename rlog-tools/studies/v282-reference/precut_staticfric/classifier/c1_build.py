"""classifier stage 1: per torque route, rebuild the one-sided static-friction term's OWN outward test on the
same timebase the a_stickslip episodes are indexed on, and tabulate every classifier at the episode's own samples.

FRAME: +left steering angle, torque in [-1,1] output units (same as a_stickslip).

Quantities rebuilt (arithmetic copied from latcontrol_torque.py:630-670 and latcontrol_vehicle_tunes.py):
  angdes_A  = the a_stickslip / reach reconstruction:  -deg(setpoint/max(v,1)^2 * sR_live * WB * (1 - SF v^2))
              (NO latAccelOffset, NO roll compensation)   <- what every existing number in the study used
  angdes_B  = fork-faithful:  curv_des = (setpoint - lao_f*fade)/max(v^2,1);  fade = interp(v,[0.5,2.5],[0,1])
              angle = (-curv_des - rollcomp(roll*fade, v)) * sR_live * WB * (1 - SF v^2)   [rad -> deg]
              rollcomp(r,v) = g*r / (1/SF - v^2)      (opendbc VehicleModel.roll_compensation, SF = slip factor)
              the (1-chi) divisor is a POSITIVE scale and cannot change a sign, so it is omitted (noted).
  rate_des_{A,B} = FirstOrderFilter(RC 0.10 s) of d(angdes)/dt, d=0 on inactive frames, primed on the first
              active frame (exactly ss_extract.py's recipe, exactly the fork's reset in the inactive branch).
  CANDIDATE TERM (designed, not cut):
       s_a = tanh(angdes / 1.0);  s_r = tanh(rate_des / 2.0);  gate = max(0, s_a*s_r)
       z_out = LEVEL * g(v) * gate * s_a,   g(v) = interp(v, [8,12], [1,0]),  LEVEL = 0.020
Written per route: out/<rk>_cls.npz  (full-route z_out/gate/angdes/rate_des + the episode table).
"""
import sys, os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + '/out'
os.makedirs(OUT, exist_ok=True)
SS = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip'
sys.path.insert(0, SS)
from sslib import *            # noqa: F401,F403  (V, T, hold_torque, fo_filter, band, hyst_run, k_of_v, params)

LEVEL = 0.020
GATE_BP, GATE_V = [8.0, 12.0], [1.0, 0.0]
DZ_ANG, DZ_RATE = 1.0, 2.0
FADE_BP, FADE_V = [0.5, 2.5], [0.0, 1.0]
G_ACC = 9.81
PRE = 150
ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']


def rate_of(angdes, act):
    d = np.r_[0.0, np.diff(angdes)]
    d[~act] = 0.0
    d[np.r_[True, ~act[:-1]]] = 0.0          # first active frame primed -> no step
    return fo_filter(d / 0.01, FF_RATE_RC, reset=~act), d


def term(angdes, rate_des, v):
    s_a = np.tanh(angdes / DZ_ANG)
    s_r = np.tanh(rate_des / DZ_RATE)
    gate = np.maximum(0.0, s_a * s_r)
    gv = np.interp(v, GATE_BP, GATE_V)
    return LEVEL * gv * gate * s_a, gate, s_a, s_r, gv


rows = []
for rk in ROUTES:
    S = V.load(rk)
    p, fs = params(rk)
    t = S['t']; n = len(t)
    v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0)
    act = S['active']
    sR = np.nan_to_num(S['sR'], nan=16.33)
    sp = np.nan_to_num(S['setpoint'])
    aa = np.nan_to_num(S['sa']) - np.nan_to_num(S['aoff'])
    sr = np.nan_to_num(S['sr'])
    cmd = np.nan_to_num(S['out'])
    scale = sR * T.WB * (1.0 - T.SF * v ** 2)                 # rad of wheel per 1/m of curvature
    angdes_A = -np.degrees(sp / vv ** 2 * scale)
    # --- fork-faithful version ---
    D = np.load(f'{BASE}/../../../analysis-2020accord/_scratch/cache/v282ref/{rk}.npz', allow_pickle=True) \
        if False else np.load(V.CACHE / f'{rk}.npz', allow_pickle=True)
    lao = np.interp(t, D['t_lt'], D['lao_f']) if len(D['t_lt']) else np.zeros(n)
    roll = np.nan_to_num(S['roll'])
    fade = np.interp(v, FADE_BP, FADE_V)
    curv_des = (sp - lao * fade) / np.maximum(v ** 2, 1.0)
    rc = G_ACC * (roll * fade) / (1.0 / T.SF - v ** 2)
    angdes_B = np.degrees((-curv_des - rc) * scale)
    rdA, dA = rate_of(angdes_A, act)
    rdB, dB = rate_of(angdes_B, act)
    zA, gA, saA, srA, gv = term(angdes_A, rdA, v)
    zB, gB, saB, srB, _ = term(angdes_B, rdB, v)
    np.savez_compressed(f'{OUT}/{rk}_cls.npz', v=v.astype(np.float32), act=act, aa=aa.astype(np.float32),
                        sr=sr.astype(np.float32), cmd=cmd.astype(np.float32),
                        angdes_A=angdes_A.astype(np.float32), angdes_B=angdes_B.astype(np.float32),
                        rd_A=rdA.astype(np.float32), rd_B=rdB.astype(np.float32),
                        z_A=zA.astype(np.float32), z_B=zB.astype(np.float32),
                        gate_A=gA.astype(np.float32), gate_B=gB.astype(np.float32),
                        lao=lao.astype(np.float32), roll=roll.astype(np.float32))
    # --- episode table ---
    EP = list(np.load(f'{SS}/out/{rk}_ss.npz', allow_pickle=True)['EP'])
    for e in EP:
        i0, i1, bk = int(e['i0']), int(e['i1']), int(e['bk'])
        b3 = max(bk - 3, i0)                                  # the release sample the fits use (30 ms lead)
        sj = float(e['sjump']); sd = float(e['sdem'])
        aa_bk = float(e['aa'])
        dsl = slice(i0, b3 + 1)
        r = dict(route=rk, v=float(e['v']), dwell_s=float(e['dwell_s']), abs_aa=float(e['abs_aa']),
                 aa_bk=aa_bk, aa_i0=float(aa[i0]), sj=sj, sdem=sd, kind=str(e['kind']),
                 dem=float(e['dem']), slip=float(e['slip']), j30=float(e['j30']), pk_rate=float(e['pk_rate']),
                 i0=i0, i1=i1, bk=bk, b3=b3)
        for tag, ang, rd, z, gt in (('A', angdes_A, rdA, zA, gA), ('B', angdes_B, rdB, zB, gB)):
            r[f'angdes_bk_{tag}'] = float(ang[b3]); r[f'angdes_i0_{tag}'] = float(ang[i0])
            r[f'rd_bk_{tag}'] = float(rd[b3]); r[f'rd_i0_{tag}'] = float(rd[i0])
            r[f'rd_dwellmean_{tag}'] = float(np.mean(rd[dsl]))
            r[f'angdes_swing_{tag}'] = float(ang[b3] - ang[i0])
            r[f'gate_bk_{tag}'] = float(gt[b3])
            r[f'gate_frac_{tag}'] = float(np.mean(gt[dsl] > 1e-3))
            r[f'gate_frac10_{tag}'] = float(np.mean(gt[dsl] > 0.10))
            # dose PROJECTED ON THE JUMP DIRECTION (what a null control would be contaminated by)
            r[f'dose_bk_{tag}'] = float(sj * z[b3])
            r[f'dose_mean_{tag}'] = float(np.mean(sj * z[dsl]))
            r[f'dose_absmean_{tag}'] = float(np.mean(np.abs(z[dsl])))
            r[f'dose_swing_{tag}'] = float(sj * (z[b3] - z[i0]))
            # dose projected OUTWARD from the wheel's own centre-side (the physical direction the design means)
            r[f'dose_out_{tag}'] = float(np.sign(aa_bk) * z[b3]) if aa_bk != 0 else 0.0
            r[f'zc_{tag}'] = int(np.sum(np.sign(ang[dsl][1:]) * np.sign(ang[dsl][:-1]) < 0))
        rows.append(r)
    del S, D
    print('done', rk, len(EP), flush=True)

json.dump(rows, open(f'{OUT}/c1_rows.json', 'w'), indent=0, default=float)
print('rows', len(rows))
