"""Pool the per-run JSONs from v0_perrun.py and re-test the finding under: fine speed matching,
demand-amplitude matching, leave-one-route-out (drop 2bc842dbac), bootstrap CIs over runs, and the
independent livePose channel (la_yaw is confirmed dead -- yaw_allzero=True on all 11 routes)."""
import json, glob
import numpy as np

D = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__desiredcurva__confound/'
RUNS = []
for f in glob.glob(D + 'perrun_*.json'):
    j = json.load(open(f))
    RUNS.extend(j['runs'])
print(f"loaded {len(RUNS)} runs total")

BANDS = ["0.3-1.0", "1.0-2.0", "2.0-3.0", "3.0-5.0"]
rng = np.random.default_rng(0)


def pool(runs, band, use_ap=False):
    """Reconstruct pooled Pxx/Pyy/Pxy (already w-weighted in each run) -> H, coh, phase, sec, in_rms."""
    Pxx = Pyy = PxyRe = PxyIm = None
    n = 0.0
    for r in runs:
        b = r['bands'][band]
        if use_ap and b['Pyy_ap'] is None:
            continue
        pxx = np.array(b['Pxx']); pyy = np.array(b['Pyy_ap'] if use_ap else b['Pyy'])
        pxyre = np.array(b['PxyapRe'] if use_ap else b['PxyRe']); pxyim = np.array(b['PxyapIm'] if use_ap else b['PxyIm'])
        Pxx = pxx if Pxx is None else Pxx + pxx
        Pyy = pyy if Pyy is None else Pyy + pyy
        PxyRe = pxyre if PxyRe is None else PxyRe + pxyre
        PxyIm = pxyim if PxyIm is None else PxyIm + pxyim
        n += r['w']
    if Pxx is None or n == 0:
        return None
    Pxy = PxyRe + 1j * PxyIm
    H = float(np.sum(np.abs(Pxy)) / max(np.sum(Pxx), 1e-30))
    coh = float(np.sum(np.abs(Pxy) ** 2) / max(np.sum(Pxx) * np.sum(Pyy), 1e-30))
    phase = float(np.degrees(np.angle(np.sum(Pxy))))
    des_rms = float(np.sqrt(np.sum(Pxx) / n * (len(Pxx))))  # not physically normalized rms, relative only
    return dict(H=H, coh=coh, phase=phase, sec=n / 100.0, nruns=len(runs), des_pow=float(np.sum(Pxx)),
                meas_pow=float(np.sum(Pyy)))


def bootstrap(runs, band, nboot=1000, use_ap=False):
    """Resample RUNS with replacement (unit = one contiguous run), rebuild pooled coh/phase each time."""
    if len(runs) < 2:
        return None
    phases, cohs, Hs = [], [], []
    for _ in range(nboot):
        idx = rng.integers(0, len(runs), len(runs))
        rs = [runs[i] for i in idx]
        p = pool(rs, band, use_ap=use_ap)
        if p is None:
            continue
        phases.append(p['phase']); cohs.append(p['coh']); Hs.append(p['H'])
    if not phases:
        return None
    def ci(a):
        a = np.array(a)
        return dict(median=float(np.median(a)), lo=float(np.percentile(a, 5)), hi=float(np.percentile(a, 95)))
    return dict(phase=ci(phases), coh=ci(cohs), H=ci(Hs), n=len(phases))


print("\n=== 1. BASELINE REPRO: pooled 2.5-8 m/s per group, matches s3_refloop.py's window ===")
groups = sorted(set(r['group'] for r in RUNS))
for band in ["1.0-2.0", "2.0-3.0"]:
    print(f"-- band {band} --")
    for g in groups:
        runs_g = [r for r in RUNS if r['group'] == g and r['lo'] == 2.5 and r['hi'] == 8.0]
        p = pool(runs_g, band)
        if p:
            print(f"   {g:8s} sec={p['sec']:6.0f} nruns={p['nruns']:3d} coh={p['coh']:.3f} phase={p['phase']:+6.0f} "
                  f"H={p['H']:.2f} des_pow={p['des_pow']:.2e} meas_pow={p['meas_pow']:.2e}")

print("\n=== 2. FINE SPEED-MATCHED BINS (2.5-4 / 4-6 / 6-8 m/s separately) ===")
for band in ["1.0-2.0", "2.0-3.0"]:
    print(f"-- band {band} --")
    for lo, hi in [(2.5, 4.0), (4.0, 6.0), (6.0, 8.0)]:
        print(f"  speed {lo}-{hi}:")
        for g in groups:
            runs_g = [r for r in RUNS if r['group'] == g and r['lo'] == lo and r['hi'] == hi]
            p = pool(runs_g, band)
            if p and p['sec'] >= 3:
                print(f"     {g:8s} sec={p['sec']:6.0f} nruns={p['nruns']:3d} coh={p['coh']:.3f} "
                      f"phase={p['phase']:+6.0f} H={p['H']:.2f}")

print("\n=== 3. LEAVE-ONE-ROUTE-OUT: V282 with vs without 0000006c--2bc842dbac (2.5-8 m/s) ===")
for band in ["1.0-2.0", "2.0-3.0"]:
    all_v282 = [r for r in RUNS if r['group'] == 'V282' and r['lo'] == 2.5 and r['hi'] == 8.0]
    no_6c = [r for r in all_v282 if r['rk'] != '0000006c--2bc842dbac']
    only_6c = [r for r in all_v282 if r['rk'] == '0000006c--2bc842dbac']
    for label, rs in [("V282 all 3 routes", all_v282), ("V282 minus r6c(2bc8)", no_6c), ("V282 ONLY r6c(2bc8)", only_6c)]:
        p = pool(rs, band)
        if p:
            print(f"   band {band:8s} {label:24s} sec={p['sec']:6.0f} nruns={p['nruns']:3d} coh={p['coh']:.3f} "
                  f"phase={p['phase']:+6.0f} H={p['H']:.2f}")

print("\n=== 4. BOOTSTRAP CI over runs (resample runs w/ replacement within group), 2.5-8 m/s ===")
for band in ["1.0-2.0", "2.0-3.0"]:
    print(f"-- band {band} --")
    for g in groups:
        runs_g = [r for r in RUNS if r['group'] == g and r['lo'] == 2.5 and r['hi'] == 8.0]
        bs = bootstrap(runs_g, band, nboot=1500)
        if bs:
            print(f"   {g:8s} n={len(runs_g):3d}  phase median {bs['phase']['median']:+6.0f} "
                  f"[{bs['phase']['lo']:+6.0f},{bs['phase']['hi']:+6.0f}]  "
                  f"coh median {bs['coh']['median']:.3f} [{bs['coh']['lo']:.3f},{bs['coh']['hi']:.3f}]")

print("\n=== 5. DEMAND-AMPLITUDE MATCHING: bin all runs (both groups) by pooled tercile of rms_ad_lp1 ===")
allr = [r for r in RUNS if r['lo'] == 2.5 and r['hi'] == 8.0]
amps = np.array([r['rms_ad_lp1'] for r in allr])
t1, t2 = np.percentile(amps, [33.3, 66.7])
print(f"  tercile cuts (deg, 1Hz-lowpassed desired-angle rms): {t1:.2f}, {t2:.2f}")
for band in ["1.0-2.0", "2.0-3.0"]:
    print(f"-- band {band} --")
    for lo_a, hi_a, name in [(-1e9, t1, 'low-demand'), (t1, t2, 'mid-demand'), (t2, 1e9, 'high-demand')]:
        for g in groups:
            runs_g = [r for r in allr if r['group'] == g and lo_a <= r['rms_ad_lp1'] < hi_a]
            p = pool(runs_g, band)
            if p and p['sec'] >= 3:
                print(f"   {name:10s} {g:8s} sec={p['sec']:6.0f} nruns={p['nruns']:3d} coh={p['coh']:.3f} "
                      f"phase={p['phase']:+6.0f} H={p['H']:.2f} mean_rms_ad_lp1={np.mean([r['rms_ad_lp1'] for r in runs_g]) if runs_g else float('nan'):.2f}")

print("\n=== 6. INDEPENDENT CHANNEL: livePose-derived equivalent-angle RATE vs desired-angle rate (la_yaw is dead: "
      "yaw_allzero=True on all 11 routes, confirmed) ===")
for band in ["1.0-2.0", "2.0-3.0"]:
    print(f"-- band {band} --")
    for g in groups:
        runs_g = [r for r in RUNS if r['group'] == g and r['lo'] == 2.5 and r['hi'] == 8.0]
        p = pool(runs_g, band, use_ap=True)
        if p:
            print(f"   {g:8s} sec={p['sec']:6.0f} nruns={p['nruns']:3d} coh={p['coh']:.3f} phase={p['phase']:+6.0f} H={p['H']:.2f}")

print("\n=== 7. RAW COHERENCE DISTRIBUTION (are the 'leading phase' bands ones where coherence is noise-floor?) ===")
for g in groups:
    runs_g = [r for r in RUNS if r['group'] == g and r['lo'] == 2.5 and r['hi'] == 8.0]
    for band in ["1.0-2.0", "2.0-3.0"]:
        cohs = []
        for r in runs_g:
            p = pool([r], band)
            if p:
                cohs.append(p['coh'])
        if cohs:
            print(f"   {g:8s} band {band:8s} per-run coh: n={len(cohs):3d} median={np.median(cohs):.3f} "
                  f"[{np.percentile(cohs,10):.3f},{np.percentile(cohs,90):.3f}]")
