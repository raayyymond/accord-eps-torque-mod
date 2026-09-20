"""fliprate stage 1: flip rate, dwell-between-flips, realised z_out trace, its slew, and the added command.

MASK: engaged & hands-off (pressed dilated 0.5 s) & v < 15, contiguous runs >= 1.0 s (V.runs enforces no clock gap).
Flips are counted INSIDE a run only; each flip is assigned the speed bin of its own frame.

DEFINITIONS
  O(t)  = 1 while s_a*s_r > 0 (the term's own OUTWARD test), 0 otherwise.  A FLIP is a change of O.
  An O-INTERVAL is a maximal stretch of constant O inside a run; its duration is the dwell between flips.
  EFFECTIVE FLIP: a flip whose adjacent OUTWARD interval reaches |z_out| >= 0.005 (= level/4).  Flips whose
  outward side never gets off the floor move no torque (s_a^2 kills them near centre) and are not excitation.
  CHATTER-ABOUT-ZERO: an outward interval shorter than 0.3 s that still reaches |z_out| >= 0.005.
"""
import sys, json
import numpy as np
from fr_lib import *

VB = [(0, 2), (2, 5), (5, 8), (8, 12), (12, 15)]
EFF = LEVEL / 4.0          # 0.005 torque
ROUTES = list(V.ROUTES.keys())


def pct(x, q):
    return float(np.percentile(x, q)) if len(x) else float('nan')


def route(rk, a_scale=A_SCALE, r_scale=R_SCALE, rc=FF_RATE_RC, save=True):
    R = prep(rk)
    v = R['v']; t = R['t']
    if rc != FF_RATE_RC:
        R['rate_des'] = fo_filter(R['d_ang'] / DT, rc, reset=~R['act'])
    ad = R['angdes']; rd = R['rate_des']
    z = z_out_of(ad, rd, v, a_scale=a_scale, r_scale=r_scale)
    du, dw = dob_perturbation(z, v)
    O = (np.tanh(ad / a_scale) * np.tanh(rd / r_scale)) > 0
    cmd = R['cmd']
    mask = R['HO'] & (v < 15.0) & np.isfinite(v)
    rl = V.runs(mask, t, min_s=1.0)

    res = dict(route=rk, group=R['group'], corr_angdes_aa=R['corr_angdes_aa'],
               n_runs=len(rl), sec=float(sum(b - a for a, b in rl) / FS), bins={})
    ivs = []          # (O, dur_s, vmid, peak_absz, max_absad, at_flip_absad)
    flips = []        # (t, v, |ad|, |rd|, new_O)
    for a, b in rl:
        Or = O[a:b]
        edges = np.r_[0, np.flatnonzero(np.diff(Or.astype(int)) != 0) + 1, b - a]
        for k in range(len(edges) - 1):
            i0, i1 = a + edges[k], a + edges[k + 1]
            ivs.append((bool(Or[edges[k]]), (i1 - i0) / FS, float(np.median(v[i0:i1])),
                        float(np.max(np.abs(z[i0:i1]))), float(np.max(np.abs(ad[i0:i1]))),
                        float(abs(ad[i0]))))
            if k > 0:
                flips.append((float(t[i0]), float(v[i0]), float(abs(ad[i0])), float(abs(rd[i0])), bool(Or[edges[k]])))
    ivs = np.array(ivs, dtype=object) if ivs else np.zeros((0, 6), dtype=object)
    fl = np.array(flips, dtype=float).reshape(-1, 5)

    dz = np.full(len(z), np.nan)                     # slew inside runs only
    ddu = np.full(len(z), np.nan)
    for a, b in rl:
        dz[a + 1:b] = np.diff(z[a:b]) * FS
        ddu[a + 1:b] = np.diff(du[a:b]) * FS

    for v0, v1 in VB:
        m = np.zeros(len(v), bool)
        for a, b in rl:
            m[a:b] = True
        m &= (v >= v0) & (v < v1)
        sec = m.sum() / FS
        if sec < 5.0:
            res['bins'][f'{v0}-{v1}'] = dict(sec=round(sec, 1), skip=True)
            continue
        fm = (fl[:, 1] >= v0) & (fl[:, 1] < v1) if len(fl) else np.zeros(0, bool)
        ivm = np.array([(r[2] >= v0) and (r[2] < v1) for r in ivs], bool) if len(ivs) else np.zeros(0, bool)
        iv_out = np.array([bool(r[0]) for r in ivs], bool) if len(ivs) else np.zeros(0, bool)
        durs = np.array([float(r[1]) for r in ivs]) if len(ivs) else np.zeros(0)
        peaks = np.array([float(r[3]) for r in ivs]) if len(ivs) else np.zeros(0)
        sel_out = ivm & iv_out
        eff = sel_out & (peaks >= EFF)
        chat = eff & (durs < 0.30)
        nz = m & (np.abs(z) > 1e-9)
        azd = np.abs(dz[m & np.isfinite(dz)]); adu = np.abs(ddu[m & np.isfinite(ddu)])
        zb = z.copy(); zb[~m] = 0.0
        sub = V.runs(m, t, min_s=2.56)               # contiguous stretches INSIDE this speed bin
        segs_z = [z[a:b] for a, b in sub]
        segs_u = [du[a:b] for a, b in sub]
        segs_c = [cmd[a:b] for a, b in sub]
        segs_cz = [(cmd + z)[a:b] for a, b in sub]
        segs_cu = [(cmd + du)[a:b] for a, b in sub]
        row = dict(
            sec=round(sec, 1),
            # --- flip rate ---
            flips_per_100s=round(fm.sum() / sec * 100, 2),
            out_intervals_per_100s=round(sel_out.sum() / sec * 100, 2),
            eff_flips_per_100s=round(eff.sum() / sec * 100, 2),
            chatter_per_100s=round(chat.sum() / sec * 100, 2),
            # --- dwell between flips (OUTWARD intervals: the ones that carry torque) ---
            out_dur_p10=round(pct(durs[sel_out], 10), 3), out_dur_p50=round(pct(durs[sel_out], 50), 3),
            out_dur_p90=round(pct(durs[sel_out], 90), 3),
            out_dur_p50_eff=round(pct(durs[eff], 50), 3), out_dur_p10_eff=round(pct(durs[eff], 10), 3),
            frac_out_under_0p2s=round(float(np.mean(durs[sel_out] < 0.2)) if sel_out.sum() else float('nan'), 3),
            frac_eff_under_0p3s=round(float(np.mean(durs[eff] < 0.3)) if eff.sum() else float('nan'), 3),
            # where the flips sit in angle
            flip_absad_p50=round(pct(fl[fm, 2], 50), 3) if fm.sum() else None,
            flip_near_centre_frac=round(float(np.mean(fl[fm, 2] < 0.5)), 3) if fm.sum() else None,
            flip_absrd_p50=round(pct(fl[fm, 3], 50), 3) if fm.sum() else None,
            # --- realised z_out ---
            frac_time_active=round(float(nz.sum() / m.sum()), 3),
            z_rms=round(float(np.sqrt(np.mean(z[m] ** 2))), 5),
            z_absmean_when_on=round(float(np.mean(np.abs(z[nz]))), 5) if nz.sum() else None,
            z_p50_when_on=round(pct(np.abs(z[nz]), 50), 5) if nz.sum() else None,
            z_p99=round(pct(np.abs(z[m]), 99), 5), z_max=round(float(np.max(np.abs(z[m]))), 5),
            frac_time_ge_half_level=round(float(np.mean(np.abs(z[m]) >= LEVEL / 2)), 3),
            # --- slew ---
            dz_p50_on=round(pct(np.abs(dz[nz & np.isfinite(dz)]), 50), 4),
            dz_p99=round(pct(azd, 99), 4), dz_max=round(float(np.max(azd)) if len(azd) else float('nan'), 4),
            dz_frac_over_cmd_p99_slew=round(float(np.mean(azd > CMD_SLEW_P99)), 4),
            dz_frac_over_honda_lim=round(float(np.mean(azd > HONDA_RATE_LIM)), 6),
            du_p99=round(pct(adu, 99), 4), du_max=round(float(np.max(adu)) if len(adu) else float('nan'), 4),
            # --- added command magnitude ---
            cmd_p99=round(pct(np.abs(cmd[m]), 99), 4), cmd_max=round(float(np.max(np.abs(cmd[m]))), 4),
            cmdz_p99=round(pct(np.abs(cmd[m] + z[m]), 99), 4),
            cmdz_max=round(float(np.max(np.abs(cmd[m] + z[m]))), 4),
            frac_cmdz_over_rail=round(float(np.mean(np.abs(cmd[m] + z[m]) >= 1.0)), 6),
            frac_cmd_over_rail=round(float(np.mean(np.abs(cmd[m]) >= 1.0)), 6),
            # --- observer bookkeeping (algebra on the code, motion held fixed) ---
            du_rms=round(float(np.sqrt(np.mean(du[m] ** 2))), 5),
            du_over_z_dc=round(float(np.mean(du[m] * np.sign(z[m] + 1e-30)) / max(np.mean(np.abs(z[m])), 1e-12)), 3),
        )
        fr, Pz, psec = psd_sum(segs_z)
        fr2, Pu, _ = psd_sum(segs_u)
        fr3, Pc, _ = psd_sum(segs_c)
        row['psd_sec'] = round(psec, 1)
        BANDS = dict(shake=SHAKE, dc=(0.02, 0.6), lo=(0.6, 1.8), hi=(3.5, 8.0), vhi=(8.0, 25.0), all=(0.02, 25.0))
        for nm, (f1, f2) in BANDS.items():
            if fr is None:
                row[f'z_{nm}_rms'] = row[f'du_{nm}_rms'] = row[f'cmd_{nm}_rms'] = None
                continue
            row[f'z_{nm}_rms'] = round(float(np.sqrt(band_power(fr, Pz, f1, f2))), 6)
            row[f'du_{nm}_rms'] = round(float(np.sqrt(band_power(fr2, Pu, f1, f2))), 6)
            row[f'cmd_{nm}_rms'] = round(float(np.sqrt(band_power(fr3, Pc, f1, f2))), 6)
        frz, Pcz, _ = psd_sum(segs_cz)
        fru, Pcu, _ = psd_sum(segs_cu)
        if fr is not None:
            for nm, (f1, f2) in BANDS.items():
                row[f'cmdz_{nm}_rms'] = round(float(np.sqrt(band_power(frz, Pcz, f1, f2))), 6)
                row[f'cmddu_{nm}_rms'] = round(float(np.sqrt(band_power(fru, Pcu, f1, f2))), 6)
            # what the band ACTUALLY does on the command once phase is respected
            row['band_ratio_cmdz'] = round(row['cmdz_shake_rms'] / max(row['cmd_shake_rms'], 1e-12), 4)
            row['band_ratio_cmddu'] = round(row['cmddu_shake_rms'] / max(row['cmd_shake_rms'], 1e-12), 4)
            bh = V.band_H([(c, zz) for c, zz in zip(segs_c, segs_z)], *SHAKE)
            if bh:
                row['coh_cmd_z_shake'] = round(bh['coh'], 3); row['phase_cmd_z_shake'] = round(bh['phase'], 1)
        if row.get('z_shake_rms') is not None and row.get('cmd_shake_rms'):
            row['z_shake_over_cmd_shake'] = round(row['z_shake_rms'] / max(row['cmd_shake_rms'], 1e-12), 4)
            row['du_shake_over_cmd_shake'] = round(row['du_shake_rms'] / max(row['cmd_shake_rms'], 1e-12), 4)
            row['z_frac_var_in_shake'] = round((row['z_shake_rms'] / max(row['z_all_rms'], 1e-12)) ** 2, 4)
            row['du_frac_var_in_shake'] = round((row['du_shake_rms'] / max(row['du_all_rms'], 1e-12)) ** 2, 4)
        res['bins'][f'{v0}-{v1}'] = row
    if save:
        np.savez_compressed(f'{OUT}/{rk}_fr.npz', z=z.astype(np.float32), du=du.astype(np.float32),
                            dw=dw.astype(np.float32), ad=ad.astype(np.float32), rd=rd.astype(np.float32),
                            v=v.astype(np.float32), cmd=cmd.astype(np.float32), t=t,
                            mask=np.array([[a, b] for a, b in rl]), O=O, aa=R['aa'].astype(np.float32),
                            sr=R['sr'].astype(np.float32))
    del R
    return res


if __name__ == '__main__':
    rks = sys.argv[1:] or ROUTES
    allr = {}
    for rk in rks:
        r = route(rk)
        allr[rk] = r
        print(rk, r['group'], f"sec {r['sec']:.0f} corr(angdes,aa) {r['corr_angdes_aa']:.3f}", flush=True)
        for bn, row in r['bins'].items():
            if row.get('skip'):
                continue
            print(f"   {bn:6s} {row['sec']:7.1f}s flips/100s {row['flips_per_100s']:7.2f} eff {row['eff_flips_per_100s']:7.2f} "
                  f"chat {row['chatter_per_100s']:6.2f} | outdur p50 {row['out_dur_p50']:5.2f} p10 {row['out_dur_p10']:5.2f} "
                  f"| z rms {row['z_rms']:.5f} p99 {row['z_p99']:.5f} | shake z {row.get('z_shake_rms')} du {row.get('du_shake_rms')} "
                  f"cmd {row.get('cmd_shake_rms')} ratio {row.get('z_shake_over_cmd_shake')} "
                  f"bandx {row.get('band_ratio_cmdz')}/{row.get('band_ratio_cmddu')}", flush=True)
    with open(f'{OUT}/fr_flip.json', 'w') as f:
        json.dump(allr, f, indent=1)
