"""reach stage 1: replay the EXACT fork hysteresis operator on the logged desired-angle trace, through every
detected dwell, for a grid of (ceiling, band, speed-gate) candidates.

Arithmetic only, on logged signals.  Nothing is re-simulated: the desired-angle trace angdes(t), the logged
command cmd(t) and the breakaway index are taken as they were flown.  The ONLY thing replayed is
    z_n = clip(z_{n-1} + d_angdes_n * f_eff(v)/b_eff(v), -f_eff(v), +f_eff(v))     (z=0 whenever inactive)
which is honda_accord_friction_hysteresis() stepped per frame, with f/b speed-gated.

Speed gate g(v): 0 below v_full (candidate fully active), 1 above v_zero (today's values), linear between.
    f_eff = f_c + g*(0.015 - f_c)      b_eff = b_c + g*(band_today(v) - b_c)
so every gated candidate is EXACTLY today's operator above v_zero -> the highway is untouched by construction.

Per episode, sign-aligned with the jump (sj), reported:
  z0   z at dwell start (i0)
  zbk  z at breakaway - 30 ms (bk-3, the index the measured shortfall was fitted at)
  dz   = zbk - z0                     accumulation through the dwell
  ex   = zbk - zbk_today              extra directional torque present at release
  dt_early / travel_early: the first frame in [i0, bk-3] at which cmd(t) + (z_cand(t) - z_today(t)) reaches
  the command level that actually released this wheel, cmd(bk-3); reported as seconds and as desired-angle
  travel back from bk-3.  (Arithmetic on the logged command.  The plant is NOT re-simulated.)
"""
import os, sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip')
sys.path.insert(0, BASE)
from sslib import V, T, params, band, hyst_run, k_of_v, hold_torque, BAND_BP, BAND_V   # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
os.makedirs(OUT, exist_ok=True)
SS = BASE + '/lowspeed/a_stickslip/out'
TQ_ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
             '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']

FC = [0.015, 0.020, 0.025, 0.030, 0.033, 0.036, 0.040, 0.045]        # ceilings
BC = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0]                        # bands, deg of desired-angle travel
GATES = {'g6_10': (6.0, 10.0), 'g8_12': (8.0, 12.0), 'g10_12': (10.0, 12.0), 'flat': (99.0, 99.1)}
CANDS = [(f, b, gn) for gn in GATES for f in FC for b in BC]
NC = len(CANDS)
CF = np.array([c[0] for c in CANDS])
CB = np.array([c[1] for c in CANDS])
CG = [c[2] for c in CANDS]
F_TODAY = 0.015


def gate(v, gn):
    v0, v1 = GATES[gn]
    return np.clip((v - v0) / max(v1 - v0, 1e-9), 0.0, 1.0)


def run_route(rk):
    S = V.load(rk)
    p, fs = params(rk)
    t = S['t']; n = len(t)
    v = np.nan_to_num(S['v']); vv = np.maximum(v, 1.0)
    act = S['active']
    sR = np.nan_to_num(S['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    cmd = np.nan_to_num(S['out'])
    d_ang = np.r_[0.0, np.diff(angdes)]
    d_ang[~act] = 0.0
    d_ang[np.r_[True, ~act[:-1]]] = 0.0
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    b_today = band(v, sched)                       # as flown on THIS route
    z_today = hyst_run(d_ang, F_TODAY, b_today, act)

    # per-frame effective f and b for every candidate: (n_frames) x (n_cand) built on the fly
    gvals = {gn: gate(v, gn) for gn in GATES}
    Gm = np.stack([gvals[gn] for gn in CG], 1).astype(np.float32)          # n x NC
    Fe = (CF[None, :] + Gm * (F_TODAY - CF[None, :])).astype(np.float32)
    Be = (CB[None, :] + Gm * (b_today[:, None] - CB[None, :])).astype(np.float32)
    del Gm
    slope = (d_ang[:, None].astype(np.float32) * Fe / np.maximum(Be, 1e-3)).astype(np.float32)
    del Be

    EPD = np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)
    EP = list(EPD['EP'])
    if not EP:
        return [], {}
    need = np.zeros(n, bool)
    for e in EP:
        need[int(e['i0']):int(e['bk']) + 1] = True
    idx_need = np.where(need)[0]
    pos = -np.ones(n, np.int64); pos[idx_need] = np.arange(len(idx_need))
    Zs = np.zeros((len(idx_need), NC), np.float32)

    zz = np.zeros(NC, np.float32)
    for m in range(n):
        if not act[m]:
            zz[:] = 0.0
        else:
            zz = np.clip(zz + slope[m], -Fe[m], Fe[m])
        j = pos[m]
        if j >= 0:
            Zs[j] = zz
    del slope, Fe

    rows = []
    for e in EP:
        i0 = int(e['i0']); bk = int(e['bk']); b3 = bk - 3; sj = float(e['sjump'])
        if b3 <= i0:
            b3 = bk
        a = pos[i0]; bidx = pos[b3]
        z0 = Zs[a] * sj
        zbk = Zs[bidx] * sj
        z0_t = z_today[i0] * sj
        zbk_t = z_today[b3] * sj
        thr = cmd[b3] * sj
        # earlier crossing: scan [i0, b3]
        sl = slice(pos[i0], pos[b3] + 1)
        zc = Zs[sl] * sj                                  # (L, NC)
        zt = (z_today[i0:b3 + 1] * sj)[:, None]
        cm = (cmd[i0:b3 + 1] * sj)[:, None]
        alt = cm + (zc - zt)
        hit = alt >= thr
        L = hit.shape[0]
        ever = hit.any(0)
        first = np.where(ever, hit.argmax(0), L - 1)
        ad = angdes[i0:b3 + 1] * sj
        rows.append(dict(route=rk, group=str(e['group']), v=float(e['v']), abs_aa=float(e['abs_aa']),
                         aa=float(e['aa']), kind=str(e['kind']), dwell_s=float(e['dwell_s']), sj=sj,
                         slip=float(e['slip']), j30=float(e['j30']),
                         cmd_bk=float(thr), cmd_i0=float(cmd[i0] * sj),
                         z0_today=float(z0_t), zbk_today=float(zbk_t),
                         z0=z0.astype(np.float32), zbk=zbk.astype(np.float32),
                         dt_early=((L - 1 - first) / 100.0).astype(np.float32),
                         tr_early=(ad[L - 1] - ad[first]).astype(np.float32),
                         ever=ever.astype(bool)))
    del Zs
    return rows, dict(sched=sched)


if __name__ == '__main__':
    allrows = []
    for rk in TQ_ROUTES:
        r, meta = run_route(rk)
        print(rk, len(r), meta, flush=True)
        allrows += r
    np.savez_compressed(OUT + '/reach_rows.npz', rows=np.array(allrows, dtype=object),
                        cands=np.array(CANDS, dtype=object))
    print('total episodes', len(allrows))
