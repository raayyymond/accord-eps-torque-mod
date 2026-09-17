"""Permutation test: is the pooled coherence/phase for each group/band explainable by RANDOM relative
phase between runs (i.e. no real cross-run-consistent desired-vs-measured relationship), given each
run's own actual |Pxy| and Pxx/Pyy magnitude structure? Rotate each run's complex Pxy vector by an
independent random phase before pooling; if the REAL pooled coherence sits inside the null distribution,
the reported group-level phase/coherence is statistically indistinguishable from runs whose phase
relationship to each other is pure noise."""
import json, glob
import numpy as np

D = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__desiredcurva__confound/'
RUNS = []
for f in glob.glob(D + 'perrun_*.json'):
    j = json.load(open(f))
    RUNS.extend(j['runs'])

rng = np.random.default_rng(1)
groups = sorted(set(r['group'] for r in RUNS))


def band_arrays(runs, band):
    Pxx = Pyy = PxyRe = PxyIm = None
    for r in runs:
        b = r['bands'][band]
        pxx = np.array(b['Pxx']); pyy = np.array(b['Pyy'])
        pxyre = np.array(b['PxyRe']); pxyim = np.array(b['PxyIm'])
        Pxx = pxx if Pxx is None else Pxx + pxx
        Pyy = pyy if Pyy is None else Pyy + pyy
        PxyRe = pxyre if PxyRe is None else PxyRe + pxyre
        PxyIm = pxyim if PxyIm is None else PxyIm + pxyim
    return Pxx, Pyy, PxyRe, PxyIm


def per_run_pxy(r, band):
    b = r['bands'][band]
    return np.array(b['PxyRe']) + 1j * np.array(b['PxyIm'])


print("group    band       real_coh  real_phase  null_coh_median  null_coh_p95  pct(real>null)  verdict")
for band in ["1.0-2.0", "2.0-3.0"]:
    for g in groups:
        runs_g = [r for r in RUNS if r['group'] == g and r['lo'] == 2.5 and r['hi'] == 8.0]
        if len(runs_g) < 2:
            continue
        Pxx, Pyy, PxyRe, PxyIm = band_arrays(runs_g, band)
        Pxy_real = PxyRe + 1j * PxyIm
        coh_real = float(np.sum(np.abs(Pxy_real) ** 2) / max(np.sum(Pxx) * np.sum(Pyy), 1e-30))
        phase_real = float(np.degrees(np.angle(np.sum(Pxy_real))))
        per_run = [per_run_pxy(r, band) for r in runs_g]
        nboot = 2000
        null_coh = np.empty(nboot)
        for k in range(nboot):
            thetas = rng.uniform(0, 2 * np.pi, len(per_run))
            s = sum(p * np.exp(1j * th) for p, th in zip(per_run, thetas))
            null_coh[k] = np.sum(np.abs(s) ** 2) / max(np.sum(Pxx) * np.sum(Pyy), 1e-30)
        pct = float(np.mean(null_coh < coh_real) * 100)
        verdict = "SIG (real > 95th pct of null)" if coh_real > np.percentile(null_coh, 95) else "not distinguishable from random cross-run phase"
        print(f"{g:8s} {band:10s} {coh_real:8.3f}  {phase_real:+7.0f}     {np.median(null_coh):8.4f}     "
              f"{np.percentile(null_coh,95):8.4f}       {pct:5.1f}%      {verdict}")
