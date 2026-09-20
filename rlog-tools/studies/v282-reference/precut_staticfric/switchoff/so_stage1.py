"""Stage 1, one route at a time: compute the candidate z_out on the logged angle_des / angle_des_rate over
the WHOLE route, then extract, per a_stickslip episode, the realised switch-off / switch-on shape and the
logged release-band margin at those instants.  -> out/<rk>_so.npz

Validation built in: my recomputed z, cmd, aa, angdes are compared against the a_stickslip window channels at
the same absolute indices (they must agree to float32 rounding -- same arithmetic, independently re-run).

RELEASE VARIABLE (outward-signed; s = sign(aa at breakaway), so +u_s = pushing further from centre):
    u_s(t) = (cmd(t) - k*aa(t) - c) * s  -  off
    stuck while -hw <= u_s <= +hw ; outward release at +hw ; inward release at -hw
k, c, off, hw re-derived in so_band.json (breakaway sample, the episode's own speed band).
COUNTERFACTUAL: u_s'(t) = u_s(t) + zo_s(t),  zo_s = z_out * s.
  NOTE zo_s >= 0 whenever sign(angle_des) == s, which is the normal case; it is recorded either way.

ANCHOR for the switch-off: t_on = the LAST index in [i0-LOOK, bk] at which zo_s >= ON_FRAC*LEVEL
("substantially on").  Everything after that is the realised switch-off, whatever shape it has.
"""
import sys, os, json
import numpy as np
from solib import (route_signals, episodes, OUT, BASE, LEVEL, g_of_v)

LOOK = 300          # frames of lookback (3.0 s)
WPRE, WPOST = 250, 250   # stored window around the dwell start
D_LOOP = 6          # frames: 65 ms, the resolved loop-delay point estimate (55-75 ms bracket)
ON_FRAC = 0.5       # "substantially on" = >= 50 % of the full dose
BAND = json.load(open(OUT + '/so_band.json'))


def edges(v):
    b = BAND['2-8|breakaway' if v < 8 else '8-15|breakaway']
    return b['k'][0], b['c'][0], b['off'][0], b['hw'][0]


def run(rk):
    R = route_signals(rk)
    if not R['torque']:
        print(rk, 'not a torque route, skipped'); return
    EP = episodes(rk)
    n = len(R['t'])
    aa, cmd, zo, angdes, rd, v, HO, act = (R['aa'], R['cmd'], R['z_out'], R['angdes'], R['rate_des'],
                                           R['v'], R['HO'], R['act'])
    duty = {}
    for nm, m in (('HO_v2_8', HO & (v >= 2) & (v < 8)), ('HO_v8_12', HO & (v >= 8) & (v < 12)),
                  ('HO_v2_12', HO & (v >= 2) & (v < 12)), ('act_v2_12', act & (v >= 2) & (v < 12))):
        if m.sum() == 0:
            continue
        z_ = np.abs(zo[m])
        duty[nm] = dict(sec=float(m.sum() / 100), frac_gt0=float(np.mean(z_ > 1e-6)),
                        frac_gt_25pct=float(np.mean(z_ > 0.25 * LEVEL)), frac_gt_50pct=float(np.mean(z_ > 0.5 * LEVEL)),
                        frac_gt_75pct=float(np.mean(z_ > 0.75 * LEVEL)),
                        p50=float(np.median(z_)), p90=float(np.percentile(z_, 90)), mean=float(np.mean(z_)))
    rows, WZ, WU = [], [], []
    for e in EP:
        i0, i1, bk = e['i0'], e['i1'], e['bk']
        s = float(np.sign(aa[bk])) or 1.0
        sj = e['sjump']
        ret = bool(sj == -s)
        vv = e['v']
        k_, c_, off_, hw_ = edges(vv)
        us = (cmd - k_ * aa - c_) * s - off_
        zos = zo * s
        usp = us + zos
        lo = max(0, i0 - LOOK)
        seg = zos[lo:bk + 1]
        pk = float(np.max(seg)) if len(seg) else 0.0
        # LAST contiguous "on" run (zo_s >= ON_FRAC*LEVEL) ending at or before bk; z_hold = its own plateau,
        # so dz is the realised drop of THAT transition, not a threshold-crossing artefact.
        on = np.where(seg >= ON_FRAC * LEVEL)[0]
        if len(on):
            end = int(on[-1])
            k2 = end
            while k2 - 1 >= 0 and seg[k2 - 1] >= ON_FRAC * LEVEL:
                k2 -= 1
            run0, run1 = lo + k2, lo + end
            z_hold = float(np.max(zos[run0:run1 + 1]))
            t90 = run1
            while t90 > run0 and zos[t90] < 0.9 * z_hold:
                t90 -= 1
            j = run1
            thr = 0.1 * z_hold
            while j < min(n - 1, bk + 80) and zos[j] > thr:
                j += 1
            t_on, t_off = run1, j
            dz = z_hold - float(zos[min(j, n - 1)])
            fall_s = (j - t90) / 100.0
            dz100 = float(zos[t90] - zos[min(t90 + 10, n - 1)])
            dz200 = float(zos[t90] - zos[min(t90 + 20, n - 1)])
            t_hi = t90
        else:
            t_on = t_off = t_hi = -1
            z_hold = dz = dz100 = dz200 = 0.0
            fall_s = np.nan
        marg = lambda idx: float(us[int(np.clip(idx, 0, n - 1))] + hw_)
        # inward command travel logged between t_on and bk (positive = moved inward)
        trav_log = float(us[t_hi] - us[bk]) if t_hi >= 0 else np.nan
        # did the command cross the inward edge between the START OF THE FALL and bk, logged vs counterfactual?
        a_, b_ = (t_hi if t_hi >= 0 else i0), bk + 1
        logged_cross = bool(np.any(us[a_:b_] <= -hw_)) if b_ > a_ else False
        cf_cross = bool(np.any(usp[a_:b_] <= -hw_)) if b_ > a_ else False
        # ---- switch-ON side ----
        hi2 = min(n - 1, bk + 40)
        seg2 = zos[i0:hi2 + 1]
        pk2 = float(np.max(seg2)) if len(seg2) else 0.0
        on50 = i0 + int(np.argmax(seg2 >= 0.5 * pk2)) if pk2 > 1e-9 else -1
        cf_out = lg_out = -1
        if bk >= i0:
            s3 = usp[i0:bk + 1]; s4 = us[i0:bk + 1]
            if np.any(s3 >= hw_):
                cf_out = i0 + int(np.argmax(s3 >= hw_))
            if np.any(s4 >= hw_):
                lg_out = i0 + int(np.argmax(s4 >= hw_))
        rows.append(dict(route=rk, group=R['group'], v=vv, aa=float(aa[bk]), abs_aa=float(abs(aa[bk])),
                         s=s, sj=float(sj), ret=ret, kind=e['kind'], dwell_s=e['dwell_s'],
                         slip=e['slip'], slip_s=e['slip_s'], j30=e['j30'], dem=e['dem'], dem_rate=e['dem_rate'],
                         i0=int(i0), i1=int(i1), bk=int(bk), g=float(g_of_v(vv)),
                         k=k_, c=c_, off=off_, hw=hw_,
                         zo_peak=pk, z_hold=z_hold, dz100=dz100, dz200=dz200, t_hi=int(t_hi),
                         t_on=int(t_on), t_off=int(t_off), dz=dz, fall_s=float(fall_s),
                         on_lead_i0_s=((i0 - t_on) / 100.0) if t_on >= 0 else np.nan,
                         on_lead_bk_s=((bk - t_on) / 100.0) if t_on >= 0 else np.nan,
                         off_lead_i0_s=((i0 - t_off) / 100.0) if t_off >= 0 else np.nan,
                         off_lead_bk_s=((bk - t_off) / 100.0) if t_off >= 0 else np.nan,
                         zo_i0=float(zos[i0]), zo_i1=float(zos[i1]), zo_bk=float(zos[bk]),
                         zo_bk_delayed=float(zos[max(0, bk - D_LOOP)]), zo_bk3=float(zos[max(0, bk - 3)]),
                         zo_max_in_dwell=float(np.max(zos[i0:i1 + 1])),
                         zo_min_in_dwell=float(np.min(zos[i0:i1 + 1])),
                         zo_min_i0_bk=float(np.min(zos[i0:bk + 1])),
                         zo_min_i0_slipend=float(np.min(zos[i0:min(n, bk + int(round(e['slip_s'] * 100)) + 1)])),
                         zo_max_i0_slipend=float(np.max(zos[i0:min(n, bk + int(round(e['slip_s'] * 100)) + 1)])),
                         zo_at_slipend=float(zos[min(n - 1, bk + int(round(e['slip_s'] * 100)))]),
                         marg_on=marg(t_on) if t_on >= 0 else np.nan, marg_hi=marg(t_hi) if t_hi >= 0 else np.nan, marg_off=marg(t_off) if t_off >= 0 else np.nan,
                         marg_i0=marg(i0), marg_i1=marg(i1), marg_bk=marg(bk), marg_bkd=marg(bk - D_LOOP),
                         us_on=float(us[t_on]) if t_on >= 0 else np.nan, us_hi=float(us[t_hi]) if t_hi >= 0 else np.nan, us_i0=float(us[i0]), us_bk=float(us[bk]),
                         us_bkd=float(us[max(0, bk - D_LOOP)]), trav_log=trav_log,
                         logged_cross_in=logged_cross, cf_cross_in=cf_cross,
                         zo_pk_i0bk=pk2, on50_rel_bk_s=((on50 - bk) / 100.0) if on50 >= 0 else np.nan,
                         cf_out_rel_bk_s=((cf_out - bk) / 100.0) if cf_out >= 0 else np.nan,
                         lg_out_rel_bk_s=((lg_out - bk) / 100.0) if lg_out >= 0 else np.nan,
                         sign_angdes_bk=float(np.sign(angdes[bk])), angdes_bk=float(angdes[bk]), rd_bk=float(rd[bk]),
                         angdes_i0=float(angdes[i0]), rd_i0=float(rd[i0]),
                         ))
        a2, b2 = i0 - WPRE, i0 + WPOST
        pad = lambda x: np.pad(x[max(0, a2):min(n, b2)].astype(np.float32),
                               (max(0, -a2), max(0, b2 - n)), constant_values=np.nan)
        WZ.append(pad(zos)); WU.append(pad(us))
    # slip-end census: where does u_s sit when the post-breakaway slip stops, and is zo_s still on?
    slipend = []
    for e, r in zip(EP, rows):
        bk = e['bk']; s = r['s']
        us = (cmd - r['k'] * aa - r['c']) * s - r['off']
        j = min(bk + int(round(e['slip_s'] * 100)), n - 1)
        slipend.append(dict(route=rk, ret=r['ret'], v=r['v'], sj=r['sj'], hw=r['hw'], kind=r['kind'],
                            us_bk=float(us[bk]), us_end=float(us[j]), zo_end=float(zo[j] * s),
                            zo_bk=float(zo[bk] * s), slip=e['slip'], slip_s=e['slip_s']))
    D = np.load(f'{BASE}/lowspeed/a_stickslip/out/{rk}_ss.npz', allow_pickle=True)
    val = {}
    if len(EP):
        idx = np.array([e['bk'] for e in EP])
        for ch, mine in (('z', R['z']), ('cmd', cmd), ('aa', aa), ('angdes', angdes)):
            val[ch] = float(np.max(np.abs(D[ch][:, 150] - mine[idx])))
    np.savez_compressed(f'{OUT}/{rk}_so.npz', rows=np.array(rows, dtype=object),
                        slipend=np.array(slipend, dtype=object), duty=np.array(duty, dtype=object),
                        val=np.array(val, dtype=object), wz=np.array(WZ), wu=np.array(WU))
    print(rk, R['group'], 'eps', len(rows), 'returns', sum(r['ret'] for r in rows),
          'val_maxabs', {k: round(x, 6) for k, x in val.items()}, flush=True)


if __name__ == '__main__':
    for rk in sys.argv[1:]:
        run(rk)
