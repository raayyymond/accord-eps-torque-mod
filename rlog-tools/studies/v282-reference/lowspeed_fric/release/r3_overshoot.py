"""Stage 3: the overshoot, measured (logged angle + logged desired angle only).

sign-aligned by sj.  t=0 = breakaway frame (PRE=150).
  gap0     = angdes - aa at t=0                          (how far behind the wheel is)
  catch(t) = aa(t) - aa(0)
  need(t)  = gap0 + (angdes(t) - angdes(0))              (travel to be ON the desired angle at t)
  over(t)  = catch(t) - need(t)                          (>0: past the desired angle)
  pk_rate  = max |5 Hz-lp steering rate| over 0..t,  and WHEN it happens (reachability: anything
             before t = D_loop was committed by the command already in flight)
-> out/r3_overshoot.json
"""
import numpy as np, json
from rel_lib import *

EP, W, P = load()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); rt = col('route'); aa_abs = col('abs_aa'); dr = col('dem_rate')
TQ = np.isin(g, TQG); V2 = g == 'V282'
aa = W['aa'] * sj[:, None]; ad = W['angdes'] * sj[:, None]; sr = W['sr'] * sj[:, None]
import scipy.signal as ss
b_, a_ = ss.butter(2, 5.0 / 50.0)
srl = ss.filtfilt(b_, a_, W['sr'], axis=1) * sj[:, None]

gap0 = ad[:, PRE] - aa[:, PRE]
def catch(L): return aa[:, PRE + L] - aa[:, PRE]
def need(L): return gap0 + (ad[:, PRE + L] - ad[:, PRE])
def over(L): return catch(L) - need(L)
# excursion past the desired angle over the whole 0.8 s post-window
exc_pk = np.max(aa[:, PRE:PRE + POST] - ad[:, PRE:PRE + POST], axis=1)
pk_rate = {L: np.max(np.abs(srl[:, PRE:PRE + L + 1]), 1) for L in (30, 50, 80)}
pk_t = np.argmax(np.abs(srl[:, PRE:PRE + 51]), 1) * 0.01
adl = ss.filtfilt(b_, a_, W['angdes'], axis=1) * sj[:, None]     # 5 Hz lp: the raw angdes carries
dem_rate_lp = np.diff(adl, axis=1, prepend=adl[:, :1]) / 0.01    # model-refresh steps that make a raw
pk_dem_rate = np.max(np.abs(dem_rate_lp[:, PRE:PRE + 51]), 1)    # per-frame rate meaningless (V282 read 0.097 flat)
mean_dem_rate = (ad[:, PRE + 30] - ad[:, PRE]) / 0.30
mean_wheel_rate = (aa[:, PRE + 30] - aa[:, PRE]) / 0.30
# overshoot accrued in the first 65 ms (the measured D_loop floor) as a share of the 0.5 s total
o50 = over(50); o65 = over(7); o110 = over(11)

def d(x, cl, f=np.median):
    m, ci = boot_ci(x, cl, f)
    return dict(p50=round(float(m), 4), ci=[round(c, 4) for c in ci])


def match(tmask, rmask):
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]; pairs = []
    for i in ti:
        dv = np.abs(v[ri] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = int(np.argmin(dist))
        if dist[j] <= 1.5:
            pairs.append((i, ri[j]))
    return pairs


R = {'note': 'degrees at the wheel; + = the direction the wheel jumped; D_loop 55-75 ms => 6-8 frames'}
R['matched'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for aname, am in (('all', np.ones(N, bool)), ('aa<5', aa_abs < 5), ('aa>=5', aa_abs >= 5)):
        pr = match(TQ & (v >= lo) & (v < hi) & am, V2 & (v >= lo - 1) & (v < hi + 1) & am)
        if len(pr) < 6:
            continue
        ti = np.array([p[0] for p in pr]); ri = np.array([p[1] for p in pr])
        row = dict(n_pairs=len(pr))
        for nm, ii in (('torque', ti), ('v282', ri)):
            row[nm] = dict(
                gap0=d(gap0[ii], rt[ii]),
                catch300=d(catch(30)[ii], rt[ii]), catch500=d(catch(50)[ii], rt[ii]),
                need300=d(need(30)[ii], rt[ii]),
                over300=d(over(30)[ii], rt[ii]), over500=d(o50[ii], rt[ii]),
                over300_p90=round(float(np.percentile(over(30)[ii], 90)), 3),
                over500_p90=round(float(np.percentile(o50[ii], 90)), 3),
                frac_past_desired_300=round(float(np.mean(over(30)[ii] > 0)), 3),
                excursion_peak=d(exc_pk[ii], rt[ii]), excursion_peak_p90=round(float(np.percentile(exc_pk[ii], 90)), 3),
                pk_rate300=d(pk_rate[30][ii], rt[ii]), pk_rate300_p90=round(float(np.percentile(pk_rate[30][ii], 90)), 2),
                pk_rate_over_demand_rate=d(pk_rate[30][ii] / np.maximum(pk_dem_rate[ii], 0.5), rt[ii]),
                pk_dem_rate=d(pk_dem_rate[ii], rt[ii]),
                mean_dem_rate=d(mean_dem_rate[ii], rt[ii]), mean_wheel_rate=d(mean_wheel_rate[ii], rt[ii]),
                pk_rate_minus_pk_dem=d(pk_rate[30][ii] - pk_dem_rate[ii], rt[ii]),
                pk_rate_time_s=d(pk_t[ii], rt[ii]),
                frac_peak_before_65ms=round(float(np.mean(pk_t[ii] <= 0.065)), 3),
                frac_peak_before_110ms=round(float(np.mean(pk_t[ii] <= 0.110)), 3),
                over_share_first65ms=d(np.clip(o65[ii] / np.where(np.abs(o50[ii]) > 0.2, o50[ii], np.nan), -2, 2)[~np.isnan(o65[ii] / np.where(np.abs(o50[ii]) > 0.2, o50[ii], np.nan))], np.array(['x'])),
                over_share_first110ms=d(np.clip(o110[ii] / np.where(np.abs(o50[ii]) > 0.2, o50[ii], np.nan), -2, 2)[~np.isnan(o110[ii] / np.where(np.abs(o50[ii]) > 0.2, o50[ii], np.nan))], np.array(['x'])))
        for k in ('catch300', 'catch500', 'over300', 'over500', 'pk_rate300', 'excursion_peak'):
            row.setdefault('ratio', {})[k] = round(float(row['torque'][k]['p50'] / row['v282'][k]['p50']), 3) if abs(row['v282'][k]['p50']) > 1e-6 else None
        R['matched'][f'{lo}-{hi}|{aname}'] = row

# unmatched per-group, and the recovery time after the excursion
R['per_group'] = {}
for lo, hi in [(2, 8), (8, 15)]:
    for gname, gm in (('V282', V2), ('TORQUE', TQ), ('T64', g == 'T64'), ('T64B', g == 'T64B'), ('T4', g == 'T4'), ('T5', g == 'T5')):
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 8:
            continue
        R['per_group'][f'{gname}|{lo}-{hi}'] = dict(
            n=int(m.sum()), gap0=d(gap0[m], rt[m]), catch300=d(catch(30)[m], rt[m]), over300=d(over(30)[m], rt[m]),
            over500=d(o50[m], rt[m]), excursion_peak=d(exc_pk[m], rt[m]),
            pk_rate300=d(pk_rate[30][m], rt[m]), pk_rate_time_s=d(pk_t[m], rt[m]),
            frac_peak_before_65ms=round(float(np.mean(pk_t[m] <= 0.065)), 3),
            frac_past_desired_300=round(float(np.mean(over(30)[m] > 0)), 3))
json.dump(R, open(OUT + '/r3_overshoot.json', 'w'), indent=1, default=float)
for k, row in R['matched'].items():
    print('==', k, 'n_pairs', row['n_pairs'])
    for f in ('gap0', 'catch300', 'need300', 'over300', 'over500', 'excursion_peak', 'pk_rate300', 'pk_dem_rate', 'pk_rate_over_demand_rate', 'pk_rate_minus_pk_dem', 'mean_wheel_rate', 'mean_dem_rate', 'pk_rate_time_s'):
        print(f"   {f:<26} T {row['torque'][f]['p50']:>8.3f} {str(row['torque'][f]['ci']):>18}   V {row['v282'][f]['p50']:>8.3f} {str(row['v282'][f]['ci']):>18}")
    for f in ('over300_p90', 'over500_p90', 'excursion_peak_p90', 'pk_rate300_p90', 'frac_past_desired_300', 'frac_peak_before_65ms', 'frac_peak_before_110ms'):
        print(f"   {f:<26} T {row['torque'][f]:>8}   V {row['v282'][f]:>8}")
    for f in ('over_share_first65ms', 'over_share_first110ms'):
        print(f"   {f:<26} T {row['torque'][f]['p50']:>8.3f}   V {row['v282'][f]['p50']:>8.3f}")
    print('   ratio', row['ratio'])
