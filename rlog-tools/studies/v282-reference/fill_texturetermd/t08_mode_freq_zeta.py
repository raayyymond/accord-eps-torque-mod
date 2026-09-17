"""t08: (A) POSITIVE CONTROL for any damping number, then (B) the measured wheel-mode frequency per speed bin.

(A) Synthetic closed loop, sampled like the logs: plant J th'' + b th' + k th = u(t - 50 ms) + w, u = r - K th(t-d) - g om(t-d),
    (k, b) solved so the DOMINANT closed-loop pole (exact discrete eigenvalues, delay states included) sits at 2.8 Hz with
    zeta 0.10 / 0.20 / 0.40.  Inputs: r = exogenous "feedforward" (white noise low-passed at 1 Hz + a 10 % white floor),
    w = white road torque.  Measurement: rate quantised to 1 deg/s (the carState LSB).  24 runs x 30 s.
    Estimators tried:
      E1  PSD fit: pooled Welch (nperseg 1024, df 0.098 Hz) of rate, 1.2-6 Hz, model A w^2/((w0^2-w^2)^2+(2 z w0 w)^2) + c
      E4  IV closed-loop FRF r -> rate (nperseg 256), fit K jw e^{-jw tau} (1 + jw c1) / (w0^2 - w^2 + 2j z w0 w)
    Pass: recovered zeta within +-30 % of truth AND f0 within +-0.15 Hz, for all three truths.
(B) Data: rate PSD per speed bin from runs >= 10.24 s (usable, >= 3 m/s), f0 by E1 AND by the raw peak of the PSD divided
    by a smooth (1/f) background; bootstrap over runs; per route group too.  zeta quoted ONLY if its estimator passed (A).
"""
import sys, json, math
import numpy as np
from scipy import signal, optimize, linalg
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
V = ttd.V
DT = 0.01; FS = 100.0
D_FR = 5


def sys_matrix(J, b, k, K, g, d=D_FR):
    Ac = np.array([[0, 1], [-k / J, -b / J]]); Bc = np.array([[0], [1 / J]])
    M = linalg.expm(np.block([[Ac, Bc], [np.zeros((1, 3))]]) * DT)
    Ad, Bd = M[:2, :2], M[:2, 2]
    N = 2 + d
    A = np.zeros((N, N))
    # u_now = -K th - g om  (enters the delay line tail); plant uses head
    A[:2, :2] = Ad; A[:2, 2] = Bd
    for i in range(d - 1):
        A[2 + i, 3 + i] = 1.0
    A[2 + d - 1, 0] = -K; A[2 + d - 1, 1] = -g
    Bin = np.zeros(N); Bin[2 + d - 1] = 1.0       # exogenous r enters with the command
    Bw = np.zeros(N); Bw[:2] = Bd                    # road torque enters the plant directly
    return A, Bin, Bw


def dominant(A):
    z = np.linalg.eigvals(A)
    best = None
    for zz in z:
        if np.imag(zz) <= 1e-9:
            continue
        s = np.log(zz) / DT
        f = np.imag(s) / (2 * np.pi); zeta = -np.real(s) / abs(s)
        if 1.0 < f < 6 and (best is None or zeta < best[1]):
            best = (f, zeta)
    return best


def design(f_t, z_t, J=1e-4, K=0.004, g=4e-4):
    def res(p):
        k, b = math.exp(p[0]), p[1]
        m = dominant(sys_matrix(J, b, k, K, g)[0])
        if m is None:
            return [10, 10]
        return [(m[0] - f_t) * 3, (m[1] - z_t) * 10]
    best = None
    for k0 in (0.01, 0.02, 0.03):
        for b0 in (1e-4, 5e-4, 1e-3):
            r = optimize.least_squares(res, [math.log(k0), b0])
            if best is None or r.cost < best.cost:
                best = r
    k, b = math.exp(best.x[0]), best.x[1]
    return k, b, dominant(sys_matrix(J, b, k, K, g)[0])


def simulate(A, Bin, Bw, n, rng):
    r = signal.sosfilt(signal.butter(2, 1.0, fs=FS, output='sos'), rng.standard_normal(n)) * 0.05 + 0.005 * rng.standard_normal(n)
    w = 0.01 * rng.standard_normal(n)
    x = np.zeros(A.shape[0]); om = np.zeros(n)
    for j in range(n):
        om[j] = x[1]
        x = A @ x + Bin * r[j] + Bw * w[j]
    return r, np.round(om)          # 1 deg/s LSB


def psd_model(f, A, f0, z, c):
    w = 2 * np.pi * f; w0 = 2 * np.pi * f0
    return A * w ** 2 / ((w0 ** 2 - w ** 2) ** 2 + (2 * z * w0 * w) ** 2) + c


def E1(segs, f1=1.2, f2=6.0):
    nps = 1024
    P = None; n = 0
    for x in segs:
        if len(x) < nps:
            continue
        f, p = signal.welch(x - x.mean(), FS, nperseg=nps, noverlap=nps // 2)
        P = p * len(x) if P is None else P + p * len(x); n += len(x)
    if P is None:
        return None
    P /= n
    m = (f >= f1) & (f <= f2)
    fm, pm = f[m], P[m]

    def res(p):
        return np.log(psd_model(fm, math.exp(p[0]), p[1], abs(p[2]), math.exp(p[3]))) - np.log(pm)
    best = None
    for f0 in np.arange(1.5, 4.6, 0.5):
        for z0 in (0.1, 0.3, 0.6):
            p0 = [math.log(np.max(pm) * (2 * z0 * (2 * np.pi * f0) ** 2) ** 2 / (2 * np.pi * f0) ** 2), f0, z0, math.log(np.min(pm) + 1e-9)]
            try:
                r = optimize.least_squares(res, p0, bounds=([-80, f1, 0.01, -60], [80, f2, 2.0, 20]))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    ipk = np.argmax(pm * fm)   # f-weighted raw peak (removes the 1/f tilt)
    return dict(f0=float(best.x[1]), zeta=float(abs(best.x[2])), f=f.tolist(), P=P.tolist(), raw_peak=float(fm[ipk]))


def E4(pairs, f1=0.8, f2=5.2):
    nps = 256
    Srr = Sry = None
    for r, y in pairs:
        if len(r) < nps:
            continue
        f, s_rr = signal.welch(r, FS, nperseg=nps, noverlap=nps // 2, detrend='linear')
        _, s_ry = signal.csd(r, y, FS, nperseg=nps, noverlap=nps // 2, detrend='linear')
        _, s_yy = signal.welch(y, FS, nperseg=nps, noverlap=nps // 2, detrend='linear')
        w = len(r)
        if Srr is None:
            Srr, Sry, Syy = s_rr * w, s_ry * w, s_yy * w
        else:
            Srr += s_rr * w; Sry += s_ry * w; Syy += s_yy * w
    return fit_E4(f, Sry / Srr, np.abs(Sry) ** 2 / (Srr * Syy), f1, f2)


def fit_E4(f, H, coh, f1=0.8, f2=5.2):
    m = (f >= f1) & (f <= f2)
    fm, Hm, wm = f[m], H[m], np.sqrt(np.clip(coh[m], 0, 1))
    om = 2 * np.pi * fm

    def model(p):
        K, tau, c1, f0, z = p
        w0 = 2 * np.pi * f0
        return K * 1j * om * np.exp(-1j * om * tau) * (1 + 1j * om * c1) / (w0 ** 2 - om ** 2 + 2j * z * w0 * om)

    def res(p):
        e = np.log(Hm / model(p))
        return np.concatenate([np.real(e) * wm, np.imag(e) * wm])
    best = None
    for f0 in (1.2, 2.0, 2.8, 3.6):
        for z in (0.1, 0.3, 0.7):
            p0 = [abs(Hm[len(Hm) // 2]) * (2 * np.pi * f0) ** 2 / (2 * np.pi * f0), 0.05, 0.0, f0, z]
            try:
                r = optimize.least_squares(res, p0, bounds=([0, 0, -0.2, 0.5, 0.01], [1e9, 0.3, 0.2, 6.0, 2.0]))
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    return dict(f0=float(best.x[3]), zeta=float(best.x[4]), tau=float(best.x[1]), c1=float(best.x[2]))


if __name__ == '__main__':
    OUT = {}
    rng = np.random.default_rng(11)
    ctrl = {}
    for zt in (0.10, 0.20, 0.40):
        k, b, dom = design(2.8, zt)
        A, Bin, Bw = sys_matrix(1e-4, b, k, 0.004, 4e-4)
        segs = []; pairs = []
        for _ in range(24):
            r, om = simulate(A, Bin, Bw, 3000, rng)
            segs.append(om); pairs.append((r, om))
        e1 = E1(segs); e4 = E4(pairs)
        ctrl[zt] = dict(k=k, b=b, true_f=dom[0], true_zeta=dom[1], E1_f=e1['f0'], E1_zeta=e1['zeta'], E1_rawpeak=e1['raw_peak'],
                        E4_f=e4['f0'], E4_zeta=e4['zeta'])
        c = ctrl[zt]
        print(f"CONTROL zeta_true {c['true_zeta']:.3f} f_true {c['true_f']:.2f} | E1 f {c['E1_f']:.2f} zeta {c['E1_zeta']:.3f} rawpk {c['E1_rawpeak']:.2f} | "
              f"E4 f {c['E4_f']:.2f} zeta {c['E4_zeta']:.3f}", flush=True)
    passE1 = all(abs(c['E1_zeta'] / c['true_zeta'] - 1) <= 0.3 and abs(c['E1_f'] - c['true_f']) <= 0.15 for c in ctrl.values())
    passE4 = all(abs(c['E4_zeta'] / c['true_zeta'] - 1) <= 0.3 and abs(c['E4_f'] - c['true_f']) <= 0.15 for c in ctrl.values())
    passE1f = all(abs(c['E1_f'] - c['true_f']) <= 0.15 for c in ctrl.values())
    print('E1 zeta PASS' if passE1 else 'E1 zeta FAIL', '| E1 freq', 'PASS' if passE1f else 'FAIL', '| E4', 'PASS' if passE4 else 'FAIL')
    OUT['control'] = dict(cases=ctrl, E1_pass=passE1, E1_freq_pass=passE1f, E4_pass=passE4)

    # (B) data
    bins = [(3, 8), (8, 15), (15, 22), (22, 40)]
    segs = {bn: [] for bn in bins}
    for ri, (rk, g) in enumerate(ttd.TORQUE.items()):
        R = ttd.red(rk)
        m = R['usable'].astype(bool) & np.isfinite(R['sr']) & np.isfinite(R['v'])
        for lo, hi in bins:
            mm = m & (R['v'] >= lo) & (R['v'] < hi)
            for a, b_ in V.runs(mm, R['t'], min_s=10.24):
                segs[(lo, hi)].append((ri, R['sr'][a:b_].astype(float), float(np.median(np.abs(R['ang'][a:b_])))))
        del R
    OUT['data'] = {}
    for bn, S in segs.items():
        if len(S) < 3:
            continue
        e = E1([s[1] for s in S])
        B = []
        rngb = np.random.default_rng(2)
        for _ in range(120):
            pick = [S[i][1] for i in rngb.integers(0, len(S), len(S))]
            q = E1(pick)
            if q:
                B.append((q['f0'], q['raw_peak'], q['zeta']))
        B = np.array(B)
        per = {}
        for gname, rr in (('T64', [0, 1]), ('T64B', [2]), ('T5', [3]), ('T4', [4])):
            ss = [s[1] for s in S if s[0] in rr]
            if len(ss) >= 2:
                q = E1(ss)
                if q:
                    per[gname] = dict(f0=q['f0'], raw_peak=q['raw_peak'], n=len(ss))
        OUT['data'][f'{bn[0]}-{bn[1]}'] = dict(n_runs=len(S), sec=sum(len(s[1]) for s in S) / 100, f0=e['f0'], raw_peak=e['raw_peak'],
                                              f0_ci=[float(np.percentile(B[:, 0], 2.5)), float(np.percentile(B[:, 0], 97.5))],
                                              raw_ci=[float(np.percentile(B[:, 1], 2.5)), float(np.percentile(B[:, 1], 97.5))],
                                              zeta_E1=e['zeta'], zeta_ci=[float(np.percentile(B[:, 2], 2.5)), float(np.percentile(B[:, 2], 97.5))],
                                              per_group=per, f=e['f'], P=e['P'])
        d = OUT['data'][f'{bn[0]}-{bn[1]}']
        print(f"DATA {bn} runs {d['n_runs']} {d['sec']:.0f}s  E1 f0 {d['f0']:.2f} [{d['f0_ci'][0]:.2f},{d['f0_ci'][1]:.2f}]  raw peak {d['raw_peak']:.2f} "
              f"[{d['raw_ci'][0]:.2f},{d['raw_ci'][1]:.2f}]  zeta(E1) {d['zeta_E1']:.2f}  per group " +
              ' '.join(f"{k}:{v['f0']:.2f}/{v['raw_peak']:.2f}(n{v['n']})" for k, v in per.items()))
    # E4 on data: instrument = FF, from t03 windows
    W = np.load(ttd.OUT + 't03_win.npz')
    f = W['f']; v = W['L_v']; aa = W['L_absang']; tu = W['L_turn']
    E4d = {}
    for sn, sm in (('v3_8', (v >= 3) & (v < 8)), ('lt15_large', (v < 15) & (aa >= 15)), ('turns_s3', tu), ('v8_15', (v >= 8) & (v < 15)), ('ge15', v >= 15)):
        idx = np.where(sm)[0]
        Szr = np.sum(np.conj(W['X_ff'][idx]) * W['X_r'][idx], 0); Szz = np.sum(np.abs(W['X_ff'][idx]) ** 2, 0); Srr = np.sum(np.abs(W['X_r'][idx]) ** 2, 0)
        H = Szr / Szz; coh = np.abs(Szr) ** 2 / (Szz * Srr)
        q = fit_E4(f, H, coh, 0.7, 5.2)
        runs = W['L_run'][idx]; ur = np.unique(runs); bym = {u: idx[runs == u] for u in ur}
        rb = np.random.default_rng(4); BB = []
        for _ in range(100):
            ii = np.concatenate([bym[u] for u in rb.choice(ur, len(ur))])
            Szr = np.sum(np.conj(W['X_ff'][ii]) * W['X_r'][ii], 0); Szz = np.sum(np.abs(W['X_ff'][ii]) ** 2, 0); Srr = np.sum(np.abs(W['X_r'][ii]) ** 2, 0)
            qq = fit_E4(f, Szr / Szz, np.abs(Szr) ** 2 / (Szz * Srr), 0.7, 5.2)
            BB.append((qq['f0'], qq['zeta']))
        BB = np.array(BB)
        E4d[sn] = dict(q, coh_band=float(np.mean(coh[(f >= 1.5) & (f <= 3.55)])), f0_ci=[float(np.percentile(BB[:, 0], 2.5)), float(np.percentile(BB[:, 0], 97.5))],
                       zeta_ci=[float(np.percentile(BB[:, 1], 2.5)), float(np.percentile(BB[:, 1], 97.5))])
        print(f"E4 DATA {sn:10s} f0 {q['f0']:.2f} [{E4d[sn]['f0_ci'][0]:.2f},{E4d[sn]['f0_ci'][1]:.2f}] zeta {q['zeta']:.2f} [{E4d[sn]['zeta_ci'][0]:.2f},{E4d[sn]['zeta_ci'][1]:.2f}] tau {q['tau']*1000:.0f} ms  coh(ff,rate) band {E4d[sn]['coh_band']:.2f}")
    OUT['E4_data'] = E4d
    json.dump(OUT, open(ttd.OUT + 't08_mode_freq_zeta.json', 'w'), indent=1)
