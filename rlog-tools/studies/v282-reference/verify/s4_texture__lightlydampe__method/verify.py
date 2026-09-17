"""Adversarial METHOD verification of s4_texture's "lightly-damped-3hz-closed-loop-mode" finding.

Two parts:
  (A) Re-derive the per-route AR(10) pole numbers straight from the cache with a fresh implementation
      (not importing s4_events.py), and check they match what s4_events.json / the finding's magnitude
      block report. Sanity-checks: fs alignment, decimate settings, pole->(f,zeta) formula, band gate.
  (B) The finding itself flags there is NO POSITIVE CONTROL, i.e. no check that AR(10) direct-lstsq on a
      250-sample (10 s @ 25 Hz) piece actually recovers the RIGHT zeta and does not fabricate spuriously
      low-zeta poles from finite-sample noise or from a merely-different SPECTRAL SHAPE (e.g. more power
      in-band, no genuine narrow resonance). We supply that positive control here: synthetic sr-like
      signals with a KNOWN ground-truth pole (or no pole at all), run through the EXACT pipeline
      (same p=10, same decimate-by-4 zero-phase, same 1000-sample/10s raw segments, same 1.5-4 Hz gate),
      across a matrix of true zeta and in-band SNR (power share) spanning what the real V282 (share
      ~4-6%) and torque (share ~12-27%) routes actually show (from e4/sr var-share numbers already in
      s4_events.json). If recovered zeta tracks ground truth regardless of SNR -> method survives. If
      recovered zeta is systematically pulled toward the SNR/power level rather than the true pole ->
      the V282-vs-torque zeta gap could be (partly or wholly) an estimator artifact of differing in-band
      power, not evidence of an actual damping-ratio difference.
"""
import sys, json
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s4_texture__lightlydampe__method'
rng = np.random.default_rng(1234)

GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}


# ---------- exact copy of the estimator under test (kept identical on purpose) ----------
def ar_poles(x, p=10, fs=25.0):
    x = x - x.mean()
    Y = x[p:]; X = np.column_stack([x[p - k - 1:len(x) - k - 1] for k in range(p)])
    a, *_ = np.linalg.lstsq(X, Y, rcond=None)
    z = np.roots(np.r_[1, -a])
    s = np.log(z.astype(complex)) * fs
    out = []
    for si in s:
        if si.imag > 0:
            wn = abs(si); out.append((wn / (2 * np.pi), -si.real / wn))
    return out


# ============================= PART A: re-derive real-data numbers =============================
def part_a():
    print('=== PART A: independent re-derivation from cache, fresh script ===')
    res = {}
    for g in GROUPS:
        for rk in routes[g]:
            S = V.load(rk); u = V.usable(S); t = S['t']
            e4 = np.nan_to_num(S['e4']); sr = np.nan_to_num(S['sr']); v = np.nan_to_num(S['v'])
            Pxx = Pyy = Pxy = None
            poles = {'lt15': [], 'ge15': []}
            n_segs_tot = 0; n_runs = 0
            for a, b in V.runs(u, t, min_s=10.24):
                n_runs += 1
                x = e4[a:b] - e4[a:b].mean(); y = sr[a:b] - sr[a:b].mean()
                f, pxx = signal.welch(x, 100, nperseg=512); _, pyy = signal.welch(y, 100, nperseg=512)
                _, pxy = signal.csd(x, y, 100, nperseg=512)
                w = b - a
                Pxx = pxx * w if Pxx is None else Pxx + pxx * w
                Pyy = pyy * w if Pyy is None else Pyy + pyy * w
                Pxy = pxy * w if Pxy is None else Pxy + pxy * w
                for k0 in range(0, b - a - 1000 + 1, 1000):
                    seg = sr[a + k0:a + k0 + 1000]
                    vv = np.median(v[a + k0:a + k0 + 1000])
                    ds = signal.decimate(seg, 4, zero_phase=True)
                    n_segs_tot += 1
                    for fh, z in ar_poles(ds):
                        if 1.5 <= fh <= 4.0:
                            poles['lt15' if vv < 15 else 'ge15'].append((fh, z))
            s1 = (f >= 1.8) & (f < 3.0); s2 = (f >= 1.5) & (f < 5.0)
            coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
            o = dict(group=g, n_runs=n_runs, n_10s_segs=n_segs_tot,
                     coh_e4_sr_1p8_3=float(np.mean(coh[s1])),
                     e4_var_share_1p5_5=float(Pxx[s2].sum() / Pxx[(f >= 0.05) & (f < 20)].sum()),
                     sr_var_share_1p5_5=float(Pyy[s2].sum() / Pyy[(f >= 0.05) & (f < 20)].sum()))
            for st, pl in poles.items():
                if len(pl) >= 5:
                    P = np.array(pl)
                    o[f'ar_{st}'] = dict(n=len(P), f_med=float(np.median(P[:, 0])),
                                          zeta_med=float(np.median(P[:, 1])),
                                          frac_zeta_lt_0p2=float(np.mean(P[:, 1] < 0.2)),
                                          poles_per_seg=len(P) / max(n_segs_tot, 1))
            res[rk] = o
            print(rk, g, 'n_segs', n_segs_tot, 'poles_found lt15/ge15', len(poles['lt15']), len(poles['ge15']),
                  'ar_lt15', o.get('ar_lt15', {}).get('zeta_med'), o.get('ar_lt15', {}).get('f_med'))
            del S

    # aggregate per group like the finding's magnitude block
    print()
    for band in ['ar_lt15', 'ar_ge15']:
        for g in GROUPS:
            zs = [res[rk][band]['zeta_med'] for rk in routes[g] if band in res.get(rk, {})]
            fs_ = [res[rk][band]['f_med'] for rk in routes[g] if band in res.get(rk, {})]
            shares = [res[rk][band]['frac_zeta_lt_0p2'] for rk in routes[g] if band in res.get(rk, {})]
            if zs:
                print(f'{g:8s} {band}: f {min(fs_):.2f}-{max(fs_):.2f}  zeta_med {min(zs):.3f}-{max(zs):.3f}  '
                      f'shareLt0.2 {min(shares):.3f}-{max(shares):.3f}  n_routes={len(zs)}')

    json.dump(res, open(f'{OUT}/part_a_real_data.json', 'w'), indent=1, default=float)
    return res


# ======================= PART B: synthetic positive control =======================
def gen_signal(n_100hz, true_f=None, true_zeta=None, band_power_share=0.0, lowfreq_amp=1.0, seed=0):
    """Build a 100 Hz signal shaped like sr: dominant sub-1 Hz content (steering maneuvers) +
    an optional true 2nd-order resonance at (true_f, true_zeta) excited by white noise, mixed to hit a
    target power SHARE in [1.5, 5) Hz relative to total [0.05, 20) Hz power (mirrors e4/sr_var_share_1p5_5
    in the real data, which ranged 0.4-27% across routes). Returns x(t) at 100 Hz."""
    r = np.random.default_rng(seed)
    fs = 100.0
    # low-frequency dominant component: lowpass white noise at ~0.3 Hz, this is the bulk of steering-rate power
    w = r.standard_normal(n_100hz)
    sos_lo = signal.butter(2, 0.4, btype='low', fs=fs, output='sos')
    lo = signal.sosfiltfilt(sos_lo, w) * lowfreq_amp
    # broadband floor across the whole spectrum (measurement-ish noise), small
    floor = r.standard_normal(n_100hz) * 0.02 * lowfreq_amp

    if band_power_share <= 0 or true_zeta is None:
        x = lo + floor
    else:
        # resonant component: 2nd-order continuous system driven by white noise, exact discretization
        wn = 2 * np.pi * true_f
        # state-space: xdot = A x + B u ; y = C x ; A = [[0,1],[-wn^2, -2*zeta*wn]]
        A = np.array([[0, 1], [-wn ** 2, -2 * true_zeta * wn]])
        Bc = np.array([0, 1.0])
        dt = 1 / fs
        # simple RK4 integration of the SDE driven by discrete white noise increments (Euler-Maruyama is fine here)
        u = r.standard_normal(n_100hz) / np.sqrt(dt)
        st = np.zeros(2)
        ys = np.zeros(n_100hz)
        for i in range(n_100hz):
            st = st + dt * (A @ st + Bc * u[i])
            ys[i] = st[0]
        ys = ys - ys.mean()
        # scale resonant component to hit target band-power SHARE via a bisection-free approach: measure
        # actual shares of lo+floor and ys separately via Welch, then mix by power.
        def welch_share(sig):
            f, p = signal.welch(sig - sig.mean(), fs, nperseg=min(4096, len(sig)))
            band = (f >= 1.5) & (f < 5.0); tot = (f >= 0.05) & (f < 20.0)
            return p[band].sum(), p[tot].sum(), f, p
        b_base, t_base, _, _ = welch_share(lo + floor)
        b_res, t_res, _, _ = welch_share(ys)
        base_share = b_base / t_base
        if base_share >= band_power_share:
            # base already exceeds target share; just return base (can't hit target by ADDING more band power
            # without also touching total... use small resonance amplitude anyway for a weak positive control)
            alpha = 0.3
        else:
            # solve for alpha (amplitude scale on ys) s.t. (b_base + alpha^2*b_res)/(t_base+alpha^2*t_res) = target
            tgt = band_power_share
            # (b_base - tgt*t_base) + alpha^2*(b_res - tgt*t_res) = 0
            num = tgt * t_base - b_base
            den = b_res - tgt * t_res
            alpha = np.sqrt(max(num / den, 0.0)) if den > 0 else 1.0
        x = lo + floor + alpha * ys
    return x


def run_ar_on_signal(x_100hz, seg=1000):
    """Chop into 1000-sample (10s) raw pieces, decimate x4 zero-phase, fit AR(10), collect poles in 1.5-4Hz."""
    poles = []
    n = len(x_100hz)
    for k0 in range(0, n - seg + 1, seg):
        piece = x_100hz[k0:k0 + seg]
        ds = signal.decimate(piece, 4, zero_phase=True)
        for fh, z in ar_poles(ds):
            if 1.5 <= fh <= 4.0:
                poles.append((fh, z))
    return np.array(poles) if poles else np.zeros((0, 2))


def part_b():
    print()
    print('=== PART B: synthetic positive control for the AR(10) estimator ===')
    n_100hz = 100 * 600  # 600 s -> 60 non-overlapping 10s pieces per draw, like a long route
    n_draws = 8  # independent noise draws per condition (like several routes)

    results = []
    # B1: NULL case -- no real resonance at all, just the low-freq-dominant + floor shape (mimics "no mode").
    # If the estimator is honest it should either find FEW poles in-band, or poles with NO consistent zeta,
    # NOT a spuriously tight, spuriously-low-zeta cluster.
    print('-- B1: no true resonance (null) --')
    null_all = []
    for d in range(n_draws):
        x = gen_signal(n_100hz, band_power_share=0.0, seed=1000 + d)
        P = run_ar_on_signal(x)
        null_all.append(P)
        if len(P):
            print(f'  draw {d}: n_poles={len(P)} f_med={np.median(P[:,0]):.2f} zeta_med={np.median(P[:,1]):.3f}')
        else:
            print(f'  draw {d}: n_poles=0')
    Pnull = np.concatenate([p for p in null_all if len(p)]) if any(len(p) for p in null_all) else np.zeros((0, 2))
    results.append(dict(cond='null_no_resonance', n=len(Pnull),
                         f_med=float(np.median(Pnull[:, 0])) if len(Pnull) else None,
                         zeta_med=float(np.median(Pnull[:, 1])) if len(Pnull) else None,
                         frac_zeta_lt_0p2=float(np.mean(Pnull[:, 1] < 0.2)) if len(Pnull) else None,
                         poles_per_10s=len(Pnull) / (n_draws * 60)))

    # B2: matrix of TRUE zeta x in-band power share, spanning the observed real-data range
    #     V282 share ~ 4-6% (e4) / 4-27%... actually sr_var_share for V282 0.04-0.06, torque 0.12-0.27
    true_zetas = [0.10, 0.20, 0.30, 0.40, 0.55]
    shares = [0.05, 0.15, 0.25]  # matches V282 (~0.04-0.06) and torque (~0.12-0.27) ranges
    true_f = 2.8
    print('-- B2: true_zeta x band-power-share matrix, true_f=2.8 Hz --')
    for tz in true_zetas:
        for sh in shares:
            allP = []
            for d in range(n_draws):
                x = gen_signal(n_100hz, true_f=true_f, true_zeta=tz, band_power_share=sh, seed=2000 + d)
                P = run_ar_on_signal(x)
                if len(P):
                    allP.append(P)
            P = np.concatenate(allP) if allP else np.zeros((0, 2))
            zmed = float(np.median(P[:, 1])) if len(P) else None
            fmed = float(np.median(P[:, 0])) if len(P) else None
            share_lt02 = float(np.mean(P[:, 1] < 0.2)) if len(P) else None
            print(f'  true_zeta={tz:.2f} share={sh:.2f}: n={len(P):4d} f_med={fmed} zeta_med={zmed} '
                  f'shareLt0.2={share_lt02} poles_per_10s={len(P)/(n_draws*60):.2f}')
            results.append(dict(cond='matrix', true_zeta=tz, band_share=sh, n=len(P), f_med=fmed, zeta_med=zmed,
                                 frac_zeta_lt_0p2=share_lt02, poles_per_10s=len(P) / (n_draws * 60)))

    json.dump(results, open(f'{OUT}/part_b_synthetic.json', 'w'), indent=1, default=float)
    return results


if __name__ == '__main__':
    ra = part_a()
    rb = part_b()
