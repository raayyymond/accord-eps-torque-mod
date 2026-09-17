"""t09: direction by prediction.  Bivariate VAR at 25 Hz, pooled over usable runs (>= 12 s, demeaned per run, high-passed
0.3 Hz BEFORE decimation), lag order by BIC (<= 20 lags = 0.8 s).  Geweke spectral Granger causality f_{x->y}(f) averaged
over 1.5-3.5 Hz, and the time-domain F statistic.  Bootstrap over runs.

Pairs (+left torque vs steeringRateDeg):
  rate <-> ff        NEGATIVE CONTROL for rate->ff: no wheel state enters the FF (code).  Must read ~0; if not, the test is
                     contaminated (e.g. by common planner content) and no direction claim below is made from it.
  rate <-> dob       POSITIVE CONTROL for rate->dob: the observer is built from the measured rate/angle.  Must read >> 0.
  rate <-> rl_fb     POSITIVE CONTROL (filtered rate x gain).
  rate <-> u_log     the question: which way does the command <-> wheel relation run in band.
  rate <-> p_meas, rate <-> fb
Strata: runs with median v < 15 m/s, and >= 15 m/s.
Fail criteria written before running: if the negative control rate->ff is not below 1/4 of the ff->rate value, or the
positive controls do not exceed 5x the negative control, the GC numbers are not used for a direction claim.
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/fill_texturetermd')
import ttd  # noqa: E402
V = ttd.V
FSd = 25.0
PAIRS = ['ff', 'dob', 'rl_fb', 'u_log', 'p_meas', 'fb', 'u_e4']
HP = signal.butter(2, 0.3, btype='high', fs=100, output='sos')
AA = signal.butter(6, 9.0, fs=100, output='sos')

segs = []
for ri, (rk, g) in enumerate(ttd.TORQUE.items()):
    R = ttd.red(rk)
    X = {k: np.nan_to_num(R[k].astype(float)) for k in ttd.TERMS}
    sigs = dict(r=R['sr'].astype(float), ff=sum(X[k] for k in ttd.TERMS_FF), fb=sum(X[k] for k in ttd.TERMS_FB), dob=X['dob'],
                rl_fb=X['rl_fb'], p_meas=X['p_meas'], u_log=R['u_log'].astype(float), u_e4=R['u_e4'].astype(float))
    m = R['usable'].astype(bool) & np.isfinite(R['v']) & (R['v'] >= 3) & np.isfinite(R['u_e4']) & np.isfinite(R['sr'])
    for a, b in V.runs(m, R['t'], min_s=12.0):
        seg = {}
        for k, x in sigs.items():
            y = signal.sosfiltfilt(AA, signal.sosfiltfilt(HP, x[a:b]))[::4]
            seg[k] = (y - y.mean()) / 1.0
        seg['v'] = float(np.median(R['v'][a:b])); seg['route'] = ri; seg['group'] = g
        segs.append(seg)
    del R, X
print('segments', len(segs))


def lagmat(x, p):
    n = len(x)
    return np.column_stack([x[p - i - 1:n - i - 1] for i in range(p)])


def fit_var(sel, a_key, b_key, p):
    """2-D VAR(p): z = [r, x].  Returns A (p,2,2), Sigma, n"""
    Y, Z = [], []
    for s in sel:
        z = np.column_stack([s[a_key], s[b_key]])
        n = len(z)
        if n <= p + 10:
            continue
        lag = np.hstack([z[p - i - 1:n - i - 1] for i in range(p)])
        Y.append(z[p:]); Z.append(lag)
    Y = np.vstack(Y); Z = np.vstack(Z)
    B, *_ = np.linalg.lstsq(Z, Y, rcond=None)
    E = Y - Z @ B
    Sig = E.T @ E / len(E)
    A = np.stack([B[2 * i:2 * i + 2].T for i in range(p)])     # A[i] maps lag i+1: z_t = sum A_i z_{t-i-1}
    return A, Sig, len(E), E, Y, Z


def restricted_var(sel, a_key, b_key, p, drop_to):
    """residual variance of series drop_to when the OTHER series' lags are excluded"""
    idx_keep = 0 if drop_to == 0 else 1
    Y, Z = [], []
    for s in sel:
        z = np.column_stack([s[a_key], s[b_key]])
        n = len(z)
        if n <= p + 10:
            continue
        own = z[:, idx_keep]
        Z.append(np.column_stack([own[p - i - 1:n - i - 1] for i in range(p)])); Y.append(own[p:])
    Y = np.concatenate(Y); Z = np.vstack(Z)
    B, *_ = np.linalg.lstsq(Z, Y, rcond=None)
    e = Y - Z @ B
    return float(e @ e / len(e))


def bic_order(sel, a_key, b_key, pmax=20):
    best = None
    for p in (2, 4, 6, 8, 10, 12, 15, 20):
        A, Sig, n, *_ = fit_var(sel, a_key, b_key, p)
        bic = np.log(np.linalg.det(Sig)) + (4 * p) * np.log(n) / n
        if best is None or bic < best[0]:
            best = (bic, p)
    return best[1]


def spectral_gc(A, Sig, freqs):
    """Geweke: f_{x->r}(w) and f_{r->x}(w) for z = [r, x]"""
    p = A.shape[0]
    out_x2r, out_r2x = [], []
    for f in freqs:
        w = 2 * np.pi * f / FSd
        Af = np.eye(2, dtype=complex)
        for i in range(p):
            Af -= A[i] * np.exp(-1j * w * (i + 1))
        H = np.linalg.inv(Af)
        S = H @ Sig @ H.conj().T
        s11, s22, s12 = Sig[0, 0], Sig[1, 1], Sig[0, 1]
        # x -> r (into component 0)
        tS = s22 - s12 ** 2 / s11
        out_x2r.append(np.log(np.real(S[0, 0]) / (np.real(S[0, 0]) - tS * abs(H[0, 1]) ** 2)))
        tS2 = s11 - s12 ** 2 / s22
        out_r2x.append(np.log(np.real(S[1, 1]) / (np.real(S[1, 1]) - tS2 * abs(H[1, 0]) ** 2)))
    return np.array(out_x2r), np.array(out_r2x)


freqs = np.linspace(1.5, 3.5, 11)
RES = {}
rng = np.random.default_rng(9)
for sn, cond in (('lt15', lambda s: s['v'] < 15), ('ge15', lambda s: s['v'] >= 15)):
    sel = [s for s in segs if cond(s)]
    RES[sn] = dict(n_seg=len(sel), sec=sum(len(s['r']) for s in sel) / FSd)
    for key in PAIRS:
        p = bic_order(sel, 'r', key)
        A, Sig, n, *_ = fit_var(sel, 'r', key, p)
        x2r, r2x = spectral_gc(A, Sig, freqs)
        # time-domain GC (log variance ratios)
        td_x2r = float(np.log(restricted_var(sel, 'r', key, p, 0) / Sig[0, 0]))
        td_r2x = float(np.log(restricted_var(sel, 'r', key, p, 1) / Sig[1, 1]))
        B = []
        for _ in range(100):
            pick = [sel[i] for i in rng.integers(0, len(sel), len(sel))]
            Ab, Sb, *_ = fit_var(pick, 'r', key, p)
            a1, a2 = spectral_gc(Ab, Sb, freqs)
            B.append((a1.mean(), a2.mean()))
        B = np.array(B)
        RES[sn][key] = dict(p=p, x2r_band=float(x2r.mean()), r2x_band=float(r2x.mean()), td_x2r=td_x2r, td_r2x=td_r2x,
                            ci_x2r=[float(np.percentile(B[:, 0], 2.5)), float(np.percentile(B[:, 0], 97.5))],
                            ci_r2x=[float(np.percentile(B[:, 1], 2.5)), float(np.percentile(B[:, 1], 97.5))],
                            x2r_spec=x2r.tolist(), r2x_spec=r2x.tolist(),
                            frac_rate_explained_by_x=float(1 - np.exp(-x2r.mean())), frac_x_explained_by_rate=float(1 - np.exp(-r2x.mean())))
        q = RES[sn][key]
        print(f"{sn} {key:7s} p {p:2d}  GC {key}->rate band {q['x2r_band']:.3f} [{q['ci_x2r'][0]:.3f},{q['ci_x2r'][1]:.3f}] (frac {q['frac_rate_explained_by_x']:.2f})   "
              f"rate->{key} {q['r2x_band']:.3f} [{q['ci_r2x'][0]:.3f},{q['ci_r2x'][1]:.3f}] (frac {q['frac_x_explained_by_rate']:.2f})   td {q['td_x2r']:.3f}/{q['td_r2x']:.3f}", flush=True)
neg = RES['lt15']['ff']['r2x_band']; pos = min(RES['lt15']['dob']['r2x_band'], RES['lt15']['rl_fb']['r2x_band'])
RES['controls'] = dict(neg_rate_to_ff=neg, ff_to_rate=RES['lt15']['ff']['x2r_band'], pos_min=pos,
                       pass_neg=bool(neg < 0.25 * RES['lt15']['ff']['x2r_band']), pass_pos=bool(pos > 5 * neg))
print('controls', RES['controls'])
json.dump(RES, open(ttd.OUT + 't09_granger.json', 'w'), indent=1)
