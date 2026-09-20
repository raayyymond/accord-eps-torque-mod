"""Stage (4)/(5): the part of D_act the CAN chain cannot see (EPS power stage + mechanics + sensor), by a
plant-inversion regression that is POSITIVE-CONTROLLED before its real-data answer counts.

Estimator (no cross-correlation, so no plant-phase bias):
   acc_n  = gradient of the measured wheel rate at sample n  = mean of true acc over [t_{n-1}, t_{n+1}]
   model  = beta_u * mean_{[t_{n-1}, t_{n+1}]} u(t - D)  + rate, rate*v, angle, angle*v, angle*v^2, sign(rate), 1
   every column and acc zero-phase band-passed 0.3-8 Hz per run (a linear filter preserves the linear equation);
   D scanned on a 1 ms grid; D_hat = argmax R^2.  Block bootstrap (10 s blocks) on sufficient statistics for the CI.
Time base: u acts at the command's ON-BUS time (sendcan + lambda'), y is stamped at the FITTED ARRIVAL of the
0x14A frame carState carried (both on the can-batch clock, so pandad's read offset cancels).

u variants:
   raw : u = 0xE4 command (ZOH)                        -> D = TX -> sensor-frame arrival, as a pure delay
   tap : u = the measured EPS tap law applied to cmd  -> D = residual after the tap (post-tap + sensor), pure delay
         (first-order pole fc_tap at 1 kHz after dd_tap ms, both measured by chain_timing.py's tap fit)

Positive control: a synthetic plant J*acc = u(t-D) - b*rate - k(v)*angle - F*sign(rate), driven by the route's
ACTUAL command on its ACTUAL engaged hands-off time base, sampled at the actual 0x14A arrival times, quantised
angle 0.1 deg / rate 1 deg/s.  Must recover D within 5 ms.
Usage: python plant_delay.py <counter--hash> [--control-only] [--sensor 14A|18F]
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
from scipy.signal import lfilter
HERE = Path(__file__).resolve().parent

K_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
FS = 100.0
SOS = signal.butter(2, [0.3, 8.0], btype="band", fs=FS, output="sos")
D_GRID = np.arange(0, 121, 1)


def runs_of(mask, t, min_s=5.0, max_gap=0.025):
    out, n, i = [], len(mask), 0
    while i < n:
        if not mask[i]:
            i += 1; continue
        j = i
        while j + 1 < n and mask[j + 1] and (t[j + 1] - t[j]) < max_gap:
            j += 1
        if t[j] - t[i] >= min_s:
            out.append((i, j + 1))
        i = j + 1
    return out


def tap_law(u_grid, fc, dd_ms):
    y = u_grid
    if np.isfinite(fc):
        a = np.exp(-2 * np.pi * fc * 0.001)
        y = lfilter([1 - a], [1, -a], u_grid)
    if dd_ms > 0:
        y = np.concatenate([np.full(int(dd_ms), y[0]), y[:-int(dd_ms)]])
    return y


def build_stats(runs, ty, rate, ang, v, tu, u, u_mode=("raw", None, None), block_s=10.0, D_grid=D_GRID):
    """Per block and per D: X'X, X'y, y'y, n.  Returns dict with arrays and block ids/speeds."""
    ncol = 8
    XtX, Xty, yty, nn, bspeed = [], [], [], [], []
    for a, b in runs:
        t = ty[a:b]
        r = rate[a:b]; an = ang[a:b]; vv = v[a:b]
        acc = np.gradient(r, t)
        g0 = t[0] - 0.2
        grid = np.arange(g0, t[-1] + 0.02, 0.001)
        iu = np.searchsorted(tu, grid, side="right") - 1
        if iu[0] < 0:
            continue
        ug = u[iu].astype(float)
        if u_mode[0] == "tap":
            ug = tap_law(ug, u_mode[1], u_mode[2])
        cs = np.concatenate([[0.0], np.cumsum(ug)])
        # window mean over [t_{n-1}, t_{n+1}] (edges: one-sided like np.gradient)
        tl = np.concatenate([[t[0]], t[:-2], [t[-2]]]); tr = np.concatenate([[t[1]], t[2:], [t[-1]]])
        base = [r, r * vv, an, an * vv, an * vv * vv, np.sign(r), np.ones_like(r)]
        base = [signal.sosfiltfilt(SOS, c) if k < 6 else c for k, c in enumerate(base)]
        yf = signal.sosfiltfilt(SOS, acc)
        nblk = max(1, int((t[-1] - t[0]) // block_s))
        edges = np.linspace(0, len(t), nblk + 1).astype(int)
        for D in D_grid:
            il = np.clip(np.round((tl - D * 1e-3 - g0) / 0.001).astype(int), 0, len(ug) - 1)
            ir = np.clip(np.round((tr - D * 1e-3 - g0) / 0.001).astype(int), 0, len(ug))
            um = (cs[np.maximum(ir, il + 1)] - cs[il]) / np.maximum(ir - il, 1)
            X = np.stack([signal.sosfiltfilt(SOS, um)] + base, 1)
            if D == D_grid[0]:
                for e0, e1 in zip(edges[:-1], edges[1:]):
                    XtX.append(np.zeros((len(D_grid), ncol, ncol))); Xty.append(np.zeros((len(D_grid), ncol)))
                    yty.append(float(yf[e0:e1] @ yf[e0:e1])); nn.append(e1 - e0)
                    ysl = yf[e0:e1]; bspeed.append(float(np.median(vv[e0:e1])))
                first_blk = len(XtX) - nblk
            di = int(np.where(D_grid == D)[0][0])
            for bk, (e0, e1) in enumerate(zip(edges[:-1], edges[1:])):
                Xb = X[e0:e1]
                XtX[first_blk + bk][di] = Xb.T @ Xb
                Xty[first_blk + bk][di] = Xb.T @ yf[e0:e1]
    if not XtX:
        return None
    # y mean per block needed for R2: acc band-passed has ~0 mean; use uncentred R2 (consistent across D)
    return dict(XtX=np.array(XtX), Xty=np.array(Xty), yty=np.array(yty), n=np.array(nn), v=np.array(bspeed))


def solve_curve(S, sel=None):
    if sel is None:
        sel = np.arange(len(S["yty"]))
    XtX = S["XtX"][sel].sum(0); Xty = S["Xty"][sel].sum(0); yty = S["yty"][sel].sum()
    r2 = np.empty(XtX.shape[0]); bu = np.empty(XtX.shape[0])
    for d in range(XtX.shape[0]):
        A = XtX[d] + 1e-9 * np.eye(XtX.shape[1]) * np.trace(XtX[d])
        beta = np.linalg.solve(A, Xty[d])
        r2[d] = 1 - (yty - 2 * beta @ Xty[d] + beta @ XtX[d] @ beta) / yty
        bu[d] = beta[0]
    return r2, bu


def estimate(S, sel=None, nboot=300, seed=0, D_grid=D_GRID):
    if sel is None:
        sel = np.arange(len(S["yty"]))
    if len(sel) < 3:
        return None
    r2, bu = solve_curve(S, sel)
    i = int(np.argmax(r2))
    # parabolic sub-ms refinement
    Dh = float(D_grid[i])
    if 0 < i < len(r2) - 1:
        den = r2[i - 1] - 2 * r2[i] + r2[i + 1]
        if den < 0:
            Dh += 0.5 * (r2[i - 1] - r2[i + 1]) / den * (D_grid[1] - D_grid[0])
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nboot):
        pk = rng.choice(sel, len(sel))
        rr, _ = solve_curve(S, pk)
        bs.append(D_grid[int(np.argmax(rr))])
    return dict(D=round(Dh, 1), ci95=np.percentile(bs, [2.5, 97.5]).tolist(), r2=float(r2[i]),
                r2_at_0=float(r2[0]), r2_span=float(r2.max() - r2.min()), beta_u=float(bu[i]), n_blocks=int(len(sel)),
                n_samples=int(S["n"][sel].sum()))


def load_route(route, sensor="14A"):
    D = dict(np.load(HERE / "cache" / f"{route}.npz"))
    CH = dict(np.load(HERE / "cache" / f"{route}_chain.npz"))
    CL = dict(np.load(HERE / "cache" / f"{route}_clock.npz"))
    lam = float(CL["lam_mean"])
    cs_t = D["cs_t"]
    # carState-level mask: carStates consumed by a masked (engaged, hands-off, identity-verified) send
    used = CH["cs_used_t"][CH["mask"].astype(bool)]
    csm = np.zeros(len(cs_t), bool)
    csm[np.searchsorted(cs_t, used)] = True
    # the measurement stream is the EPS FRAME sequence itself (every 0x14A / 0x18F frame at its fitted arrival),
    # not carState (which repeats a frame when a batch is empty and skips one when a batch holds two)
    if sensor == "14A":
        ty = CL["e14"]; rate = D["rate14"].astype(float); ang = D["ang14"].astype(float); tb = D["f14_t"]
    else:
        ty = CL["e18"]; rate = D["rate18"].astype(float); tb = D["f18_t"]
        ang = D["ang14"][np.clip(np.searchsorted(D["f14_t"], tb, side="right") - 1, 0, None)].astype(float)
    jc = np.clip(np.searchsorted(cs_t, tb, side="left"), 0, len(cs_t) - 1)
    near = np.abs(cs_t[jc] - tb) < 0.006
    v = D["cs_v"][jc]
    ok = csm[jc] & near & np.isfinite(ty)
    ok[1:] &= np.diff(ty) > 0.005
    return dict(ty=ty, rate=rate, ang=ang, v=v, mask=ok, tu=D["sc_t"] + lam * 1e-3, u=D["sc_cmd"].astype(float),
                lam=lam)


def simulate(R, D_true, J, b=0.003, F=0.02, ku=1.0 / 4089, pole=None, rng=None, rate_lsb=1.0):
    """1 kHz semi-implicit Euler plant over each run, driven by the logged command at TX + D_true."""
    rate_q = np.full(len(R["ty"]), np.nan); ang_q = np.full(len(R["ty"]), np.nan)
    for a, b_ in runs_of(R["mask"], R["ty"]):
        t = R["ty"][a:b_]
        grid = np.arange(t[0] - 0.5, t[-1] + 0.01, 0.001)
        iu = np.searchsorted(R["tu"], grid - D_true * 1e-3, side="right") - 1
        u = R["u"][np.clip(iu, 0, None)] * ku
        if pole is not None:
            fc, dd = pole
            u = tap_law(u, fc, dd)
        vg = np.interp(grid, t, R["v"][a:b_])
        k = np.interp(vg, K_V_BP, K_V)
        th, w = 0.0, 0.0
        TH = np.empty(len(grid)); W = np.empty(len(grid))
        for n in range(len(grid)):
            acc = (u[n] - b * w - k[n] * th - F * np.tanh(w / 0.5)) / J
            w += acc * 0.001
            th += w * 0.001
            TH[n] = th; W[n] = w
        gi = np.clip(np.round((t - grid[0]) / 0.001).astype(int), 0, len(grid) - 1)
        ang_q[a:b_] = np.round(TH[gi] / 0.1) * 0.1
        rate_q[a:b_] = np.round(W[gi] / rate_lsb) * rate_lsb
    return rate_q, ang_q


def speed_sel(S, lo, hi):
    return np.where((S["v"] >= lo) & (S["v"] < hi))[0]


def main():
    route = sys.argv[1]
    sensor = "18F" if "--sensor" in sys.argv and sys.argv[sys.argv.index("--sensor") + 1] == "18F" else "14A"
    R = load_route(route, sensor)
    runs = runs_of(R["mask"], R["ty"])
    out = {"route": route, "sensor": sensor, "lambda_prime_mean_ms": R["lam"], "n_runs": len(runs),
           "seconds": float(sum(R["ty"][b - 1] - R["ty"][a] for a, b in runs))}
    tapj = json.load(open(HERE / "out" / f"timing_{route}.json"))
    bt = tapj.get("B_tap_fit_diff", {}).get("best")
    fc_tap, dd_tap = (bt[0], bt[1]) if bt else (5.05, 4)
    out["tap_law_used"] = dict(fc=fc_tap, dd_ms=dd_tap)
    ctrl = {}
    for J in (8e-5, 1e-3):
        for Dt in (30, 60):
            rq, aq = simulate(R, Dt, J)
            S = build_stats(runs, R["ty"], rq, aq, R["v"], R["tu"], R["u"])
            ctrl[f"raw J={J:g} D={Dt}"] = estimate(S, nboot=100)
            print("control", J, Dt, ctrl[f"raw J={J:g} D={Dt}"], flush=True)
        # structured: tap law + 10 ms residual, estimated with u_tap
        rq, aq = simulate(R, 10, J, pole=(fc_tap, dd_tap))
        S = build_stats(runs, R["ty"], rq, aq, R["v"], R["tu"], R["u"], u_mode=("tap", fc_tap, dd_tap))
        ctrl[f"tap J={J:g} Dres=10"] = estimate(S, nboot=100)
        print("control tap", J, ctrl[f"tap J={J:g} Dres=10"], flush=True)
    out["positive_control"] = ctrl
    if "--control-only" not in sys.argv:
        real = {}
        for mode in (("raw", None, None), ("tap", fc_tap, dd_tap)):
            S = build_stats(runs, R["ty"], R["rate"], R["ang"], R["v"], R["tu"], R["u"], u_mode=mode)
            real[mode[0]] = {"all": estimate(S)}
            for nm, lo, hi in (("<8", 0, 8), ("8-15", 8, 15), (">=15", 15, 99)):
                sel = speed_sel(S, lo, hi)
                real[mode[0]][nm] = estimate(S, sel) if len(sel) >= 6 else None
            print("real", mode[0], real[mode[0]], flush=True)
        out["real"] = real
    (HERE / "out").mkdir(exist_ok=True)
    json.dump(out, open(HERE / "out" / f"plant_{route}_{sensor}.json", "w"), indent=1, default=float)




# ======================================================================================================
# Estimator 2: HIGH-FREQUENCY PHASE SLOPE.  Above the wheel mode and the damping corner the plant is J*s^2, so
# acc = u(t - D)/J and the cross-spectral phase u -> acc is -2*pi*f*D plus a small damping lead.  Welch cross-
# spectra summed over runs; D from a coherence-weighted fit of unwrapped phase over [f1, f2].
# ======================================================================================================
def cross_spec(runs, ty, rate, tu, u, u_mode=("raw", None, None), nper=128, D_shift=0.0, sel_v=None, v=None):
    Sxy = None; Sxx = None; Syy = None; nseg = 0
    for a, b in runs:
        t = ty[a:b]
        if sel_v is not None:
            vm = np.median(v[a:b])
            if not (sel_v[0] <= vm < sel_v[1]):
                continue
        if len(t) < nper + 4:
            continue
        acc = np.gradient(rate[a:b], t)
        g0 = t[0] - 0.2
        grid = np.arange(g0, t[-1] + 0.02, 0.001)
        iu = np.searchsorted(tu, grid, side="right") - 1
        if iu[0] < 0:
            continue
        ug = u[iu].astype(float)
        if u_mode[0] == "tap":
            ug = tap_law(ug, u_mode[1], u_mode[2])
        cs = np.concatenate([[0.0], np.cumsum(ug)])
        tl = np.concatenate([[t[0]], t[:-2], [t[-2]]]); tr = np.concatenate([[t[1]], t[2:], [t[-1]]])
        il = np.clip(np.round((tl - D_shift * 1e-3 - g0) / 0.001).astype(int), 0, len(ug) - 1)
        ir = np.clip(np.round((tr - D_shift * 1e-3 - g0) / 0.001).astype(int), 0, len(ug))
        um = (cs[np.maximum(ir, il + 1)] - cs[il]) / np.maximum(ir - il, 1)
        f, pxy = signal.csd(um, acc, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pxx = signal.welch(um, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        _, pyy = signal.welch(acc, fs=FS, nperseg=nper, noverlap=nper // 2, detrend="linear")
        w = len(t)
        Sxy = pxy * w if Sxy is None else Sxy + pxy * w
        Sxx = pxx * w if Sxx is None else Sxx + pxx * w
        Syy = pyy * w if Syy is None else Syy + pyy * w
        nseg += 1
    if Sxy is None:
        return None
    return dict(f=f, Sxy=Sxy, Sxx=Sxx, Syy=Syy, n=nseg)


def phase_delay(CS, f1=8.0, f2=20.0, sign=None):
    f, Sxy = CS["f"], CS["Sxy"]
    coh = np.abs(Sxy) ** 2 / np.maximum(CS["Sxx"] * CS["Syy"], 1e-30)
    s = (f >= f1) & (f <= f2)
    ph = np.angle(Sxy)
    # sign of the gain: from the low band where the plant is not inverted?  use the mean phasor above f1
    if sign is None:
        sign = 1.0 if np.cos(np.angle(Sxy[s].sum())) >= 0 or True else -1.0
    phs = np.unwrap(ph[s])
    w = coh[s] / np.maximum(1 - coh[s], 1e-3)
    # through-origin fit is not valid if the gain sign is negative (pi offset) -> fit slope + intercept, report slope
    A = np.stack([2 * np.pi * f[s], np.ones(s.sum())], 1)
    W = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(A * W[:, None], phs * W, rcond=None)
    D = -beta[0] * 1e3
    return dict(D=float(D), intercept_deg=float(np.degrees(beta[1])), coh_mean=float(coh[s].mean()), n_runs=CS["n"],
                phase_deg=[(float(ff), round(float(np.degrees(p)), 1)) for ff, p in zip(f[s], phs)][::2])


def phase_boot(runs, ty, rate, tu, u, u_mode, f1, f2, nboot=100, seed=1, **kw):
    rng = np.random.default_rng(seed)
    CS = cross_spec(runs, ty, rate, tu, u, u_mode, **kw)
    if CS is None:
        return None
    est = phase_delay(CS, f1, f2)
    # run-cluster bootstrap: per-run spectra
    per = [cross_spec([r], ty, rate, tu, u, u_mode, **kw) for r in runs]
    per = [p for p in per if p is not None]
    bs = []
    for _ in range(nboot):
        pk = rng.integers(0, len(per), len(per))
        agg = dict(f=per[0]["f"], Sxy=sum(per[i]["Sxy"] for i in pk), Sxx=sum(per[i]["Sxx"] for i in pk),
                   Syy=sum(per[i]["Syy"] for i in pk), n=len(pk))
        bs.append(phase_delay(agg, f1, f2)["D"])
    est["ci95"] = np.percentile(bs, [2.5, 97.5]).round(2).tolist()
    est.pop("phase_deg", None)
    return est


def main2():
    route = sys.argv[1]
    sensor = "18F" if "--sensor" in sys.argv and sys.argv[sys.argv.index("--sensor") + 1] == "18F" else "14A"
    R = load_route(route, sensor)
    runs = runs_of(R["mask"], R["ty"])
    tapj = json.load(open(HERE / "out" / f"timing_{route}.json"))
    bt = tapj.get("B_tap_fit_diff", {}).get("best")
    fc_tap, dd_tap = (bt[0], bt[1]) if bt else (5.05, 4)
    out = {"route": route, "sensor": sensor, "lambda_prime_mean_ms": R["lam"], "n_runs": len(runs),
           "tap_law_used": dict(fc=fc_tap, dd_ms=dd_tap)}
    bands = [(6.0, 15.0), (8.0, 20.0), (10.0, 25.0)]
    lsb = 1.0 if sensor == "14A" else 0.125
    out["rate_lsb_in_control"] = lsb
    ctrl = {}
    for J, b in (() if "--real-only" in sys.argv else ((8e-5, 0.003), (8e-5, 0.0006), (1e-3, 0.003))):
        for Dt in (30, 60):
            rq, aq = simulate(R, Dt, J, b=b, rate_lsb=lsb)
            for f1, f2 in bands:
                e = phase_boot(runs, R["ty"], rq, R["tu"], R["u"], ("raw", None, None), f1, f2, nboot=50)
                ctrl[f"raw J={J:g} b={b:g} D={Dt} band={f1:g}-{f2:g}"] = e
                print("ctrl", J, b, Dt, f1, f2, round(e["D"], 1), e["ci95"], round(e["coh_mean"], 3), flush=True)
        rq, aq = simulate(R, 10, J, b=b, pole=(fc_tap, dd_tap), rate_lsb=lsb)
        for f1, f2 in bands:
            e = phase_boot(runs, R["ty"], rq, R["tu"], R["u"], ("tap", fc_tap, dd_tap), f1, f2, nboot=50)
            ctrl[f"tap J={J:g} b={b:g} Dres=10 band={f1:g}-{f2:g}"] = e
            print("ctrl tap(Dres=10)", J, b, f1, f2, round(e["D"], 1), e["ci95"], round(e["coh_mean"], 3), flush=True)
    out["positive_control_phase"] = ctrl
    if "--control-only" not in sys.argv:
        real = {}
        for mode in (("raw", None, None), ("tap", fc_tap, dd_tap)):
            for f1, f2 in bands:
                key = f"{mode[0]} band={f1:g}-{f2:g}"
                real[key] = {"all": phase_boot(runs, R["ty"], R["rate"], R["tu"], R["u"], mode, f1, f2)}
                for nm, lo, hi in (("<8", 0, 8), ("8-15", 8, 15), (">=15", 15, 99)):
                    real[key][nm] = phase_boot(runs, R["ty"], R["rate"], R["tu"], R["u"], mode, f1, f2,
                                               sel_v=(lo, hi), v=R["v"])
                print("real", key, {k: (v_["D"], v_["ci95"], round(v_["coh_mean"], 3)) if v_ else None
                                    for k, v_ in real[key].items()}, flush=True)
        out["real_phase"] = real
    fn = HERE / "out" / f"phase_{route}_{sensor}.json"
    if "--real-only" in sys.argv and fn.exists():
        old = json.load(open(fn)); old.update({k: v for k, v in out.items() if k != "positive_control_phase"}); out = old
    json.dump(out, open(fn, "w"), indent=1, default=float)


if __name__ == "__main__":
    if "--phase" in sys.argv:
        main2()
    else:
        main()
