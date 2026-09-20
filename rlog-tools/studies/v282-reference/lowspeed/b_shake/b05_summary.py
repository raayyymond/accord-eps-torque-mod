"""b05: summarise b04 per group x speed bin. Window-bootstrap CI (1000) on rate rms, planner rms, coherence, coherent and
incoherent rate rms; per-route values for route spread. Envelope / decay / episode statistics."""
import json
import numpy as np
import bs
GROUPS = {'rev64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd'],
          'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'], 'T64B': ['0000006e--6ca3e014fd'],
          'T5': ['00000076--d0b7ea7e4d'], 'T4': ['00000075--6c8687d5bd'],
          'V282': ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac'],
          'V282old': ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4']}
BINS = bs.BINS + [(0, 8, '<8')]
R = {rk: dict(np.load(bs.OUT + f'b04_rows_{rk}.npz')) for rks in GROUPS.values() for rk in rks}
f = R['0000006c--68c6e94b17']['f']; fs = f[(f >= 0.9) & (f <= 5.1)]
NORM = 1.0 / (np.sum(np.hanning(256) ** 2) * 100) * 2   # |FFT|^2 -> one-sided PSD; x df -> power
df = f[1] - f[0]


def wstats(P, A, C):
    Prr = P.sum(0); Paa = A.sum(0); Sra = C.sum(0); n = len(P)
    coh = np.abs(Sra) ** 2 / np.maximum(Prr * Paa, 1e-30)
    cohw = float(np.average(coh, weights=Prr))
    rr = np.sqrt(Prr.sum() * NORM * df / n); aa = np.sqrt(Paa.sum() * NORM * df / n)
    H = float(np.average(np.abs(Sra) / np.maximum(Paa, 1e-30), weights=Paa))
    return dict(rate=rr, plan=aa, coh=cohw, H=H, coh_rate=rr * np.sqrt(cohw), incoh_rate=rr * np.sqrt(max(1 - cohw, 0)))


rng = np.random.default_rng(0)
RES = {}; lines = []
for gname, rks in GROUPS.items():
    for lo, hi, lab in BINS:
        P, A, C, SP, rid = [], [], [], [], []
        for rk in rks:
            X = R[rk]
            if len(X['v']) == 0:
                continue
            s = (X['v'] >= lo) & (X['v'] < hi)
            P.append(X['Prr'][s]); A.append(X['Paa'][s]); C.append(X['Sra'][s]); SP.append(X['spec'][s]); rid += [rk] * int(s.sum())
        P = np.concatenate(P); A = np.concatenate(A); C = np.concatenate(C); SP = np.concatenate(SP); rid = np.array(rid)
        if len(P) < 5:
            continue
        st = wstats(P, A, C)
        B = [wstats(P[i], A[i], C[i]) for i in (rng.integers(0, len(P), len(P)) for _ in range(500))]
        ci = {k: [float(np.percentile([b[k] for b in B], 2.5)), float(np.percentile([b[k] for b in B], 97.5))] for k in st}
        pr = {rk[:8]: wstats(P[rid == rk], A[rid == rk], C[rid == rk])['rate'] for rk in rks if (rid == rk).sum() >= 8}
        spec = SP.sum(0); k = int(np.argmax(spec))
        if 0 < k < len(spec) - 1:
            y0, y1, y2 = np.log(spec[k - 1:k + 2]); off = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
        else:
            off = 0
        fpk = float(fs[k] + off * df)
        # envelope etc
        env = np.concatenate([R[rk]['E_env'][(R[rk]['E_v'] >= lo) & (R[rk]['E_v'] < hi)] for rk in rks])
        qt = np.concatenate([R[rk]['E_quiet'][(R[rk]['E_v'] >= lo) & (R[rk]['E_v'] < hi)] for rk in rks]) > 0.5
        ang = np.concatenate([R[rk]['E_angamp'][(R[rk]['E_v'] >= lo) & (R[rk]['E_v'] < hi)] for rk in rks])
        DEC = [R[rk]['DEC'] for rk in rks if len(R[rk]['DEC'])]
        DEC = np.concatenate(DEC) if DEC else np.zeros((0, 7))
        DEC = DEC[(DEC[:, 0] >= lo) & (DEC[:, 0] < hi)] if len(DEC) else DEC
        EP = [R[rk]['EP'] for rk in rks if len(R[rk]['EP'])]
        EP = np.concatenate(EP) if EP else np.zeros((0, 7))
        EP = EP[(EP[:, 0] >= lo) & (EP[:, 0] < hi)] if len(EP) else EP
        secs = len(env) / 100
        dq = DEC[DEC[:, 4] > 0.5] if len(DEC) else DEC
        r = dict(secs_env=secs, nwin=len(P), **{k: float(v) for k, v in st.items()}, ci=ci, per_route_rate=pr, fpk=fpk,
                 env_p50=float(np.median(env)) if secs else None, env_p90=float(np.percentile(env, 90)) if secs else None,
                 quiet_frac=float(qt.mean()) if secs else None,
                 env_quiet_p50=float(np.median(env[qt])) if qt.sum() > 100 else None,
                 env_quiet_p90=float(np.percentile(env[qt], 90)) if qt.sum() > 100 else None,
                 angamp_p50=float(np.median(ang)) if secs else None, angamp_p99=float(np.percentile(ang, 99)) if secs else None,
                 n_peaks=int(len(DEC)), peaks_per_100s=float(len(DEC) / max(secs, 1e-9) * 100),
                 dec04_all=float(np.median(DEC[:, 2])) if len(DEC) else None, dec08_all=float(np.median(DEC[:, 3])) if len(DEC) else None,
                 n_peaks_quiet=int(len(dq)), dec04_quiet=float(np.median(dq[:, 2])) if len(dq) >= 3 else None,
                 dec08_quiet=float(np.median(dq[:, 3])) if len(dq) >= 3 else None,
                 ep_n=int(len(EP)), ep_s_per_100s=float(EP[:, 1].sum() / max(secs, 1e-9) * 100) if len(EP) else 0.0,
                 ep_quiet_share=float(np.average(EP[:, 4], weights=EP[:, 1])) if len(EP) else None,
                 ep_cv=float(np.median(EP[:, 3])) if len(EP) else None, ep_dur_max=float(EP[:, 1].max()) if len(EP) else None,
                 ep_angamp=float(np.median(EP[:, 5])) if len(EP) else None, ep_plan_env=float(np.median(EP[:, 6])) if len(EP) else None)
        RES[f'{gname}|{lab}'] = r
        lines.append(f"{gname:7s} {lab:5s} {r['nwin']:4d}w {secs:5.0f}s | rate {st['rate']:5.2f} [{ci['rate'][0]:5.2f},{ci['rate'][1]:5.2f}] plan {st['plan']:5.2f} "
                     f"coh {st['coh']:.2f} [{ci['coh'][0]:.2f},{ci['coh'][1]:.2f}] H {st['H']:.2f} cohR {st['coh_rate']:5.2f} incohR {st['incoh_rate']:5.2f} [{ci['incoh_rate'][0]:5.2f},{ci['incoh_rate'][1]:5.2f}] "
                     f"fpk {fpk:.2f} | env p50/p90 {r['env_p50']:.2f}/{r['env_p90']:.2f} quiet {r['quiet_frac']:.2f} envQ {r['env_quiet_p50']}/{r['env_quiet_p90']} "
                     f"ang p50/p99 {r['angamp_p50']:.2f}/{r['angamp_p99']:.2f} | pk/100s {r['peaks_per_100s']:.1f} dec.4/.8 {r['dec04_all']}/{r['dec08_all']} "
                     f"quietpk {r['n_peaks_quiet']} dec {r['dec04_quiet']}/{r['dec08_quiet']} | ep {r['ep_n']} {r['ep_s_per_100s']:.1f}s/100s qshare {r['ep_quiet_share']} cv {r['ep_cv']} max {r['ep_dur_max']} pr {pr}")
json.dump(RES, open(bs.OUT + 'b05_summary.json', 'w'), indent=1)
open(bs.OUT + 'b05_summary.txt', 'w').write('\n'.join(lines))
print('\n'.join(lines))
