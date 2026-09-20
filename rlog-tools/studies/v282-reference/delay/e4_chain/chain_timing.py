"""Sub-batch timing of the chain, on ONE clock (the can-batch clock), so pandad's read->publish offset cancels.

  e14   0x14A arrival (fitted EPS transmit clock, eps_clock.fit_clock)
  eAB   0x1AB (torque tap) arrival, fitted the same way (50 Hz)
  TX    0xE4 on-bus time = sendcan + lambda', lambda' measured from the ORDER of the TX echo relative to
        EPS frames inside the same batch (panda puts TX-complete echoes and RX frames in one FIFO)
        P(echo before frame | x = e_frame - sendcan) = P(lambda' < x)  -> CDF of lambda'
  Chain:  sample age   = carState(consumed) - e14 of the frame it carries      (includes -d, see below)
          A: e14(consumed sample) -> TX of the command computed from it   = (sendcan - e14) + lambda'   [d cancels]
          B: TX -> tap response   (fit tap = G * LPF_fc(cmd)(t - dd) + c,  tap sampled at eAB)       [d cancels]
Usage: python chain_timing.py <counter--hash> [--notap]
"""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eps_clock as C

pct = lambda x, p=(5, 25, 50, 75, 95): np.percentile(x, p).round(3).tolist()


def lpf_grid(u, fc, dt=0.001):
    if not np.isfinite(fc):
        return u.copy()
    a = np.exp(-2 * np.pi * fc * dt)
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], u)


def tap_fit(tx_t, cmd, eng, tab, tap, dd_ms=np.arange(-10, 81, 1), fcs=(1.5, 2, 3, 4, 5, 6, 8, 10, 15, 25, np.inf),
            tap_rail=2100, diff=False):
    """tx_t: on-bus time of each command (batch clock). Build 1 kHz ZOH cmd per contiguous engaged run, filter,
    sample at tab - dd, regress. Returns table of R2 and best (dd, fc)."""
    runs = []
    i, n = 0, len(tx_t)
    while i < n:
        if not eng[i]:
            i += 1; continue
        j = i
        while j + 1 < n and eng[j + 1] and tx_t[j + 1] - tx_t[j] < 0.03:
            j += 1
        if tx_t[j] - tx_t[i] > 5.0:
            runs.append((i, j + 1))
        i = j + 1
    res = {}
    rows = []
    for fc in fcs:
        Ys, Xs = {dd: [] for dd in dd_ms}, {dd: [] for dd in dd_ms}
        for a, b in runs:
            t0 = tx_t[a]
            grid = np.arange(t0, tx_t[b - 1], 0.001)
            idx = np.searchsorted(tx_t[a:b], grid, side="right") - 1
            u = cmd[a:b][np.clip(idx, 0, None)].astype(float)
            y = lpf_grid(u, fc)
            ka = np.searchsorted(tab, t0 + 1.0), np.searchsorted(tab, tx_t[b - 1] - 0.1)
            tt = tab[ka[0]:ka[1]]; T = tap[ka[0]:ka[1]]
            ok = np.isfinite(tt) & (np.abs(T) < tap_rail)
            tt, T = tt[ok], T[ok]
            if diff:
                good = np.diff(tt) < 0.025          # consecutive 50 Hz tap frames only
            for dd in dd_ms:
                g = np.clip(np.round((tt - dd * 1e-3 - t0) / 0.001).astype(int), 0, len(y) - 1)
                if diff:
                    Xs[dd].append(np.diff(y[g])[good]); Ys[dd].append(np.diff(T)[good])
                else:
                    Xs[dd].append(y[g]); Ys[dd].append(T)
        for dd in dd_ms:
            if not Xs[dd]:
                continue
            X = np.concatenate(Xs[dd]); Y = np.concatenate(Ys[dd])
            A = np.stack([X, np.ones_like(X)], 1)
            coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
            r = Y - A @ coef
            r2 = 1 - r.var() / Y.var()
            rows.append((fc, int(dd), float(r2), float(coef[0]), len(Y)))
    rows.sort(key=lambda r: -r[2])
    res["best"] = rows[0] if rows else None
    res["top10"] = rows[:10]
    # best dd per fc
    per = {}
    for fc, dd, r2, g, n in rows:
        k = "inf" if not np.isfinite(fc) else fc
        if k not in per or r2 > per[k][1]:
            per[k] = (dd, r2, g)
    res["best_dd_per_fc"] = per
    res["n_runs"] = len(runs)
    return res


def analyse(route, do_tap=True):
    D = dict(np.load(HERE / "cache" / f"{route}.npz"))
    CH = dict(np.load(HERE / "cache" / f"{route}_chain.npz"))
    R = {"route": route}
    cb = D["cb_t"]
    e14, w14, T14 = C.fit_clock(D["f14_t"], D["f14_bi"], cb, win=3000, T_nom=0.010)
    e18, w18, _ = C.fit_clock(D["f18_t"], D["f18_bi"], cb, win=3000, T_nom=0.010)
    eab, wab, Tab = C.fit_clock(D["fab_t"], D["fab_bi"], cb, win=1500, T_nom=0.020)
    for nm, e, w, t in (("14A", e14, w14, D["f14_t"]), ("18F", e18, w18, D["f18_t"]), ("1AB", eab, wab, D["fab_t"])):
        ok = np.isfinite(e)
        R[f"clock_{nm}"] = dict(fitted_frac=float(ok.mean()), width_ms=pct(w[ok] * 1e3, (5, 50, 95)),
                                batch_minus_arrival_ms=pct((t[ok] - e[ok]) * 1e3))
    R["clock_14A_ppm"] = pct((T14[np.isfinite(T14)] / 0.01 - 1) * 1e6, (5, 50, 95))
    # relative EPS schedule: 0x18F and 0x1AB arrival phase vs 0x14A
    j18 = np.clip(np.searchsorted(e14, e18) - 1, 0, len(e14) - 1)
    ok = np.isfinite(e18) & np.isfinite(e14[j18])
    R["e18_minus_prev_e14_ms"] = pct((e18[ok] - e14[j18[ok]]) * 1e3)
    j = np.searchsorted(e14, eab)
    okab = np.isfinite(eab) & (j > 0) & (j < len(e14))
    dph = (eab[okab] - e14[np.clip(j[okab] - 1, 0, None)]) * 1e3
    R["eAB_minus_prev_e14_ms"] = pct(dph[np.isfinite(dph)])
    # --- TX latency lambda' from in-batch ordering of the matched echo vs 0x14A / 0x18F / 0x1AB frames
    sc_t, sc_raw = D["sc_t"], D["sc_raw"]
    fe_t, fe_raw, fe_bi, fe_pos = D["fe4_t"], D["fe4_raw"], D["fe4_bi"], D["fe4_pos"]
    je = np.searchsorted(fe_t, sc_t - 0.0005, side="left")
    ematch = np.full(len(sc_t), -1)
    for i in range(len(sc_t)):
        k = je[i]
        while k < len(fe_t) and fe_t[k] < sc_t[i] + 0.08:
            if fe_raw[k] == sc_raw[i]:
                ematch[i] = k; break
            k += 1
    # For EVERY EPS frame whose fitted arrival lies within [-5, +25] ms of a send, the TX happened before it iff
    # the echo's batch is earlier, or the same batch with the echo earlier in the FIFO.  P(before | x) = P(lambda' < x).
    xs, before = [], []
    okm = np.where(ematch >= 0)[0]
    ebi = fe_bi[ematch[okm]]; epos = fe_pos[ematch[okm]]; st = sc_t[okm]
    for nm, bi_f, pos_f, e_f in (("14A", D["f14_bi"], D["f14_pos"], e14), ("18F", D["f18_bi"], D["f18_pos"], e18),
                                 ("1AB", D["fab_bi"], D["fab_pos"], eab)):
        fin = np.isfinite(e_f)
        ef, bf_, pf = e_f[fin], bi_f[fin], pos_f[fin]
        lo_i = np.searchsorted(ef, st - 0.005); hi_i = np.searchsorted(ef, st + 0.025)
        for kk in range(4):
            fi = lo_i + kk
            g = fi < hi_i
            fi = fi[g]
            x = ef[fi] - st[g]
            bef = (ebi[g] < bf_[fi]) | ((ebi[g] == bf_[fi]) & (epos[g] < pf[fi]))
            xs.append(x); before.append(bef)
    x = np.concatenate(xs); bf = np.concatenate(before)
    edges = np.arange(-0.005, 0.0255, 0.0005)
    cdf = []
    for lo_, hi_ in zip(edges[:-1], edges[1:]):
        m = (x >= lo_) & (x < hi_)
        if m.sum() >= 30:
            cdf.append((round((lo_ + hi_) / 2 * 1e3, 2), float(bf[m].mean()), int(m.sum())))
    R["lambda_prime_cdf_ms_P_n"] = cdf
    # lambda' median = x where P crosses 0.5 (interpolate)
    xc = np.array([c[0] for c in cdf]); pc = np.array([c[1] for c in cdf])
    def cross(p):
        k = np.where(pc >= p)[0]
        if len(k) == 0 or k[0] == 0:
            return None
        k = k[0]
        return float(xc[k - 1] + (p - pc[k - 1]) / (pc[k] - pc[k - 1] + 1e-12) * (xc[k] - xc[k - 1]))
    lam = {p: cross(p) for p in (0.05, 0.25, 0.5, 0.75, 0.95)}
    # mean of lambda' from the CDF (sum (1-P) dx over x>=0, minus sum P dx over x<0)
    dx = 0.5
    lam_mean = float(-5.0 + np.sum([(1 - p) * dx for xx, p, _ in cdf]))   # E = x0 + integral of (1 - CDF), CDF ~0 at -5 ms
    R["lambda_prime_quantiles_ms"] = lam
    R["lambda_prime_mean_ms"] = lam_mean
    # --- A: consumed 0x14A arrival -> TX of the command computed from it
    m = CH["mask"].astype(bool)
    j14 = np.searchsorted(D["f14_t"], CH["cs_used_t"], side="right") - 1
    j14 = np.clip(j14, 0, len(e14) - 1)
    e_used = e14[j14]
    age = (CH["cs_used_t"] - e_used) * 1e3          # carState - arrival (arrival on batch clock => includes +d)
    A = (sc_t - e_used) * 1e3 + lam_mean            # arrival -> on-bus TX, d cancels
    v = CH["v"]
    okA = m & np.isfinite(A)
    R["sample_age_at_carState_ms_pct(+d)"] = pct(age[okA])
    R["sample_age_mean_ms(+d)"] = float(np.mean(age[okA]))
    R["A_arrival14A_to_TX_ms_pct"] = pct(A[okA])
    R["A_mean_ms"] = float(np.mean(A[okA]))
    bins = {"<8": v < 8, "8-15": (v >= 8) & (v < 15), ">=15": v >= 15}
    # block bootstrap (60 s blocks) CI for mean A per speed bin
    rng = np.random.default_rng(0)
    blk = np.floor((sc_t - sc_t[0]) / 60.0).astype(int)
    R["A_by_speed"] = {}
    for k, b in bins.items():
        mm = okA & b
        if mm.sum() < 100:
            R["A_by_speed"][k] = None; continue
        ub = np.unique(blk[mm]); means = {u: (A[mm & (blk == u)].sum(), (mm & (blk == u)).sum()) for u in ub}
        bs = []
        for _ in range(500):
            pick = rng.choice(ub, len(ub))
            s_ = sum(means[u][0] for u in pick); n_ = sum(means[u][1] for u in pick)
            bs.append(s_ / n_)
        R["A_by_speed"][k] = dict(n=int(mm.sum()), mean=float(A[mm].mean()), ci95=np.percentile(bs, [2.5, 97.5]).round(3).tolist())
    # --- B: TX -> tap
    if do_tap:
        tx_t = sc_t + lam_mean * 1e-3
        cmd = D["sc_cmd"].astype(float)
        # engaged & hands-off from the chain mask (identity + req + not pressed)
        tab = eab
        res_all = tap_fit(tx_t, cmd, m, tab, D["tap"].astype(float))
        R["B_tap_fit_all"] = res_all
        fcs_fine = (2, 3, 4, 4.5, 5, 5.5, 6, 7, 8, 10, 15, np.inf)
        res_d = tap_fit(tx_t, cmd, m, tab, D["tap"].astype(float), fcs=fcs_fine, diff=True)
        R["B_tap_fit_diff"] = res_d
        res_all = res_d
        R["B_tap_fit_by_speed"] = {}
        for k, b in bins.items():
            mm = m & b
            if mm.sum() < 3000:
                continue
            rr = tap_fit(tx_t, cmd, mm, tab, D["tap"].astype(float), fcs=(res_all["best"][0],) if res_all["best"] else (5,))
            R["B_tap_fit_by_speed"][k] = dict(best=rr["best"], n_runs=rr["n_runs"])
        # batch-clock-only cross-check (no clock fit): tap batch time vs echo batch time
        res_b = tap_fit(np.where(np.isfinite(CH["echo_t"]), CH["echo_t"], np.nan), cmd, m & np.isfinite(CH["echo_t"]),
                        D["fab_t"], D["tap"].astype(float), fcs=(res_all["best"][0],) if res_all["best"] else (5,))
        R["B_crosscheck_batch_times_only"] = res_b["best"]
    np.savez_compressed(HERE / "cache" / f"{route}_clock.npz", e14=e14, e18=e18, eab=eab, lam_mean=lam_mean)
    return R


if __name__ == "__main__":
    route = sys.argv[1]
    R = analyse(route, do_tap="--notap" not in sys.argv)
    (HERE / "out").mkdir(exist_ok=True)
    json.dump(R, open(HERE / "out" / f"timing_{route}.json", "w"), indent=1, default=float)
    print(json.dumps(R, indent=1, default=float))
