"""fliprate stage 2: does any (A, R, filter) setting move the flip-driven energy out of 1.8-3.5 Hz
WITHOUT destroying the term's reach at the dwell?

REACH is measured where the design needs it: the DEPART dwells a_stickslip already extracted
(out/<rk>_ss.npz EP; depart = sign(aa)==sign(demand change) or |aa|<0.5, r_episodes.py's rule).
  reach_dwell = mean over the dwell [i0, i1] of sign(aa_bk) * z_out          (target: +0.020)
  reach_bk    = sign(aa_bk) * z_out at the breakaway frame
COST is measured on the same routes: the 1.8-3.5 Hz RMS of z_out, the band ratio of (cmd + z) over cmd,
effective-flip and chatter rates, and dz/dt.

THREE filter placements, and they are NOT equivalent:
  'shared'  : change HONDA_ACCORD_FF_RATE_RC.  ⚠ NOT LOCAL -- the same filtered rate feeds the plant-FF
              MOVE term (get_honda_accord_rate_plant_ff) and the rate loop, so this changes the flown
              feedforward as well as the candidate.  Reported for completeness, not as a free knob.
  'srate'   : an EXTRA first-order filter on angle_des_rate used only by s_r (candidate-local).
  'zout'    : an EXTRA first-order filter on z_out itself (candidate-local, and the only one that also
              bounds dz/dt directly).
Rate-of-change note: a first-order post-filter with RC bounds |dz/dt| at level/RC in the worst case.
"""
import sys, json, itertools
import numpy as np
from fr_lib import *

SS = BASE + '/lowspeed/a_stickslip/out'
TORQUE = [k for k, mv in V.ROUTES.items() if mv['eps'] == 'V293']
VBINS = [(2, 8), (8, 12)]


def episodes(rk):
    D = np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)
    EP = list(D['EP'])
    out = []
    for e in EP:
        s = float(e['sdem']); aa = float(e['aa'])
        depart = (np.sign(aa) == s) or abs(aa) < 0.5
        out.append(dict(i0=int(e['i0']), i1=int(e['i1']), bk=int(e['bk']), v=float(e['v']),
                        depart=bool(depart), sgn=float(np.sign(aa) if abs(aa) >= 0.05 else s),
                        abs_aa=float(e['abs_aa']), dwell_s=float(e['dwell_s'])))
    return out


def variant(R, v, cmd, sub, eps, a_scale, r_scale, place, rc, mask12):
    rd = R['rate_des']
    if place == 'shared':
        rd = fo_filter(R['d_ang'] / DT, rc, reset=~R['act'])
    elif place == 'srate' and rc > 0:
        rd = fo_filter(rd, rc, reset=~R['act'])
    z = z_out_of(R['angdes'], rd, v, a_scale=a_scale, r_scale=r_scale)
    if place == 'zout' and rc > 0:
        z = fo_filter(z, rc, reset=~R['act'])
    O = (np.tanh(R['angdes'] / a_scale) * np.tanh(rd / r_scale)) > 0
    row = dict()
    # cost
    dz = []
    for a, b in sub:
        dz.append(np.abs(np.diff(z[a:b])) * FS)
    dz = np.concatenate(dz) if dz else np.zeros(1)
    w = np.array([b - a for a, b in sub], float)
    row['z_shake'] = round(float(np.sqrt(np.average([band_rms(z[a:b], *SHAKE) ** 2 for a, b in sub], weights=w))), 6)
    row['z_rms'] = round(float(np.sqrt(np.average([np.mean(z[a:b] ** 2) for a, b in sub], weights=w))), 6)
    fr, Pz, _ = psd_sum([z[a:b] for a, b in sub])
    frc, Pc, _ = psd_sum([cmd[a:b] for a, b in sub])
    frz, Pcz, _ = psd_sum([(cmd + z)[a:b] for a, b in sub])
    row['bandx'] = round(float(np.sqrt(band_power(frz, Pcz, *SHAKE) / max(band_power(frc, Pc, *SHAKE), 1e-30))), 4)
    row['z_hi'] = round(float(np.sqrt(band_power(fr, Pz, 3.5, 8.0))), 6)
    row['dz_p99'] = round(float(np.percentile(dz, 99)), 4)
    row['dz_max'] = round(float(np.max(dz)), 4)
    nf = 0; nchat = 0; sec = 0.0
    for a, b in sub:
        d = np.flatnonzero(np.diff(O[a:b].astype(int)) != 0) + 1
        nf += len(d)
        edges = np.r_[0, d, b - a]
        for k in range(len(edges) - 1):
            if O[a + edges[k]] and (edges[k + 1] - edges[k]) < 30 and np.max(np.abs(z[a + edges[k]:a + edges[k + 1]])) >= LEVEL / 4:
                nchat += 1
        sec += (b - a) / FS
    row['flips_100s'] = round(nf / max(sec, 1e-9) * 100, 1)
    row['chat_100s'] = round(nchat / max(sec, 1e-9) * 100, 1)
    row['sec'] = round(sec, 1)
    # reach
    for lo, hi in VBINS:
        rd_, rb_ = [], []
        for e in eps:
            if not (lo <= e['v'] < hi) or not e['depart']:
                continue
            rd_.append(e['sgn'] * float(np.mean(z[e['i0']:e['i1'] + 1])))
            rb_.append(e['sgn'] * float(z[e['bk']]))
        row[f'reach_dwell_{lo}_{hi}'] = round(float(np.median(rd_)), 5) if rd_ else None
        row[f'reach_bk_{lo}_{hi}'] = round(float(np.median(rb_)), 5) if rb_ else None
        row[f'n_depart_{lo}_{hi}'] = len(rd_)
    return row


def main(rks, grid):
    acc = {}
    for rk in rks:
        R = prep(rk)
        v = R['v']; t = R['t']; cmd = R['cmd']
        m = R['HO'] & (v < 12.0)
        sub = V.runs(m, t, min_s=2.56)
        eps = episodes(rk)
        for key, (a_s, r_s, place, rc) in grid.items():
            row = variant(R, v, cmd, sub, eps, a_s, r_s, place, rc, m)
            acc.setdefault(key, {})[rk] = row
        print('done', rk, flush=True)
        del R
    # pool across routes: length-weighted for cost, pooled median for reach
    pooled = {}
    for key, per in acc.items():
        w = np.array([r['sec'] for r in per.values()], float)
        pooled[key] = dict(
            z_shake=round(float(np.sqrt(np.average([r['z_shake'] ** 2 for r in per.values()], weights=w))), 6),
            z_rms=round(float(np.sqrt(np.average([r['z_rms'] ** 2 for r in per.values()], weights=w))), 6),
            bandx_min=round(min(r['bandx'] for r in per.values()), 3),
            bandx_med=round(float(np.median([r['bandx'] for r in per.values()])), 3),
            bandx_max=round(max(r['bandx'] for r in per.values()), 3),
            dz_p99=round(float(np.average([r['dz_p99'] for r in per.values()], weights=w)), 4),
            dz_max=round(max(r['dz_max'] for r in per.values()), 4),
            flips_100s=round(float(np.average([r['flips_100s'] for r in per.values()], weights=w)), 1),
            chat_100s=round(float(np.average([r['chat_100s'] for r in per.values()], weights=w)), 1),
            reach_dwell_2_8=round(float(np.median([r['reach_dwell_2_8'] for r in per.values() if r['reach_dwell_2_8'] is not None])), 5),
            reach_bk_2_8=round(float(np.median([r['reach_bk_2_8'] for r in per.values() if r['reach_bk_2_8'] is not None])), 5),
            reach_dwell_8_12=round(float(np.median([r['reach_dwell_8_12'] for r in per.values() if r['reach_dwell_8_12'] is not None])), 5),
        )
    return acc, pooled


if __name__ == '__main__':
    grid = {}
    # leg 1: the two tanh scales at the flown filter
    for a_s in (0.5, 1.0, 2.0, 4.0, 8.0):
        for r_s in (1.0, 2.0, 4.0, 8.0):
            grid[f'A{a_s}_R{r_s}'] = (a_s, r_s, 'none', 0.0)
    # leg 2: filter placement at the design point and at a wider rate scale
    for place in ('srate', 'zout'):
        for rc in (0.05, 0.10, 0.20, 0.40):
            grid[f'A1.0_R2.0_{place}{rc}'] = (1.0, 2.0, place, rc)
            grid[f'A4.0_R4.0_{place}{rc}'] = (4.0, 4.0, place, rc)
    # leg 3: the SHARED filter (not a free knob -- also moves the flown move term)
    for rc in (0.05, 0.20, 0.40):
        grid[f'A1.0_R2.0_shared{rc}'] = (1.0, 2.0, 'shared', rc)
    acc, pooled = main(sys.argv[1:] or TORQUE, grid)
    with open(f'{OUT}/fr_sweep.json', 'w') as f:
        json.dump(dict(per_route=acc, pooled=pooled), f, indent=1)
    print(f"\n{'variant':26s} {'z_shake':>8s} {'bandx med[min,max]':>20s} {'dz_p99':>7s} {'dz_max':>7s} "
          f"{'flip/100':>8s} {'chat':>6s} {'reach_dwell':>11s} {'reach_bk':>9s} {'r/cost':>7s}")
    for k, p in pooled.items():
        fom = p['reach_dwell_2_8'] / max(p['z_shake'], 1e-9)
        print(f"{k:26s} {p['z_shake']:8.5f} {p['bandx_med']:6.3f}[{p['bandx_min']:.2f},{p['bandx_max']:.2f}]  "
              f"{p['dz_p99']:7.4f} {p['dz_max']:7.4f} {p['flips_100s']:8.1f} {p['chat_100s']:6.1f} "
              f"{p['reach_dwell_2_8']:11.5f} {p['reach_bk_2_8']:9.5f} {fom:7.2f}")
