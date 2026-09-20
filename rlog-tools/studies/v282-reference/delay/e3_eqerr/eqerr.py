"""e3_eqerr -- D_act by an equation-error delay sweep in the time domain.

MODEL (the fork's own plant, in openpilot output-torque units, +left, angles in deg):

    u(t - D)  =  J*acc(t)  +  b*rate(t)  +  g_k*hold(angle(t), v(t))  +  F*sign(rate(t))

  u      = -e4_cmd / 4096          (the 0xE4 STEERING_TORQUE integer back in controller output units;
                                    measured e4 = -4096 * controlsState.torqueState.output, see chain2.py)
  hold() = k(v)*sat(v)*tanh(angle/sat(v)), the fork's MEASURED V293 hold map with level=False
           (HONDA_ACCORD_HOLD_K_V / HONDA_ACCORD_HOLD_SAT_DEG), so g_k is dimensionless and g_k = 1
           means "the fork's spring map, unchanged".
  acc    = d/dt of the band-limited measured rate.

  Every term, u included, is passed through the SAME zero-phase band-pass L (sosfiltfilt), so the
  equality is preserved and the constant c drops out (no c is fitted).  D enters ONLY through u, which
  is resampled at t - D by linear interpolation of the logged 0xE4 stream -- 1 ms steps, sub-sample.

WHY THIS IS FAST ENOUGH TO BOOTSTRAP: the regressors do not depend on D.  Per 10 s block store
A_i = X'X (4x4) once, and per D store b_iD = X'u_D (4) and uu_iD = u_D'u_D.  Then for any set of blocks
SSE(D) = sum(uu) - b' A^-1 b with A = sum A_i, b = sum b_iD.  A bootstrap replicate is a re-sum.

OUTPUT: argmin SSE over D per (speed bin), route-cluster and 10 s-block bootstrap CIs, the curvature CI,
the fitted (J, b, g_k, F) at the optimum and +-15 ms either side, and the mandatory positive control.
"""
import sys, json, math, argparse
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V

FS = 100.0
E4_SCALE = -4096.0                      # u = e4_cmd / E4_SCALE
D_MS = np.arange(0, 121, 1)             # delay sweep, ms
BAND = (0.3, 8.0)
BLK_S = 10.0
# The 0xE4 command reaches the actuator as a ZERO-ORDER HOLD at the measured 9.91 ms send interval, but the
# estimator resamples the logged stream by LINEAR interpolation.  ZOH(s) = linear(s - T/2) EXACTLY in phase
# (sinc vs sinc^2 differ in magnitude only), so every raw D* is biased by +T/2 and this is subtracted.
# Verified in core_test.py: raw bias +4.89..+4.95 ms at true D = 0/30/60/90, residual after -T/2 < 0.15 ms.
T_SEND = 0.00991
ZOH_CORR_MS = T_SEND * 500.0            # 4.955 ms
SPRING = "hold"                          # "hold" = fork tanh map, "lin" = k(v)*angle
DWELL = 2.0                             # exclude |raw rate| < DWELL deg/s (static-friction frames)
EDGE_S = 1.0                            # discard this much at each end of a run (filter transient)
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0)]
TORQUE = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282 = ["0000006c--2bc842dbac", "00000064--ce6b0b0ebb"]

# ---- the fork's measured V293 plant constants (latcontrol_vehicle_tunes.py, read 2026-09-19) ----
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_SAT = (19.3, 546.0, 3.01)
FF_ANGLE_LIMIT_DEG = 90.0               # clip used by get_honda_accord_hold_torque


def hold_torque(angle_deg, v):
    a, b, c = HOLD_SAT
    sat = a + b * np.exp(-np.maximum(v, 0.0) / c)
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    th = np.clip(angle_deg, -FF_ANGLE_LIMIT_DEG, FF_ANGLE_LIMIT_DEG)
    return k * sat * np.tanh(th / sat)


def k_of_v(v):
    return np.interp(v, HOLD_V_BP, HOLD_K_V)


# --------------------------------------------------------------------------------------------------
def make_L(band=BAND, order=4):
    return signal.butter(order, list(band), btype="band", fs=FS, output="sos")


def spring_term(sa, v, spring=None):
    spring = spring or SPRING
    return k_of_v(v) * sa if spring == "lin" else hold_torque(sa, v)


def prep_run(t, sa, sr, v, sos, spring=None):
    """Filtered regressors on one contiguous uniform-grid run: [acc, rate, spring, sign(rate)]."""
    acc = np.gradient(signal.sosfiltfilt(sos, sr)) * FS       # band-limited rate -> acceleration
    X = np.column_stack([acc,
                         signal.sosfiltfilt(sos, sr),
                         signal.sosfiltfilt(sos, spring_term(sa, v, spring)),
                         signal.sosfiltfilt(sos, np.sign(sr))])
    return X


def route_blocks(rk, sos, dwell=DWELL, band=BAND, blk_s=BLK_S, dgrid=D_MS, synth=None, interp_cmd=True,
                 spring=None):
    """Per-10 s-block sufficient statistics for every D. synth=(sa, sr, t) overrides the measured
    kinematics (positive control), keeping the route's real command, speed and timestamps."""
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    t_cst = D["t_cst"]
    t_e4, e4 = D["t_e4"], D["e4_cmd"] / E4_SCALE
    # usable mask on the carState clock
    act = np.interp(t_cst, D["t_cs"], (D["cs_active"] > 0.5).astype(float)) > 0.5
    lat = np.interp(t_cst, D["t_cc"], (D["lat_active"] > 0.5).astype(float)) > 0.5 if "t_cc" in D.files else act
    ok = act & lat & (D["spress"] < 0.5)
    if synth is not None:                       # positive control: only where the synthetic plant exists
        ok &= (t_cst >= synth[2][0] + 0.05) & (t_cst <= synth[2][-1] - 0.05)
    out = []
    # contiguous usable stretches on the native clock
    n = len(t_cst); i = 0
    runs = []
    while i < n:
        if not ok[i]:
            i += 1; continue
        j = i
        while j + 1 < n and ok[j + 1] and (t_cst[j + 1] - t_cst[j]) < 0.04:
            j += 1
        if t_cst[j] - t_cst[i] >= 2 * EDGE_S + blk_s:
            # chunk long runs (RAM: the per-D filtered command array is 121 x N)
            CH = int(120.0 * FS)
            s = i
            while s < j + 1:
                e = min(s + CH, j + 1)
                if t_cst[e - 1] - t_cst[s] >= 2 * EDGE_S + blk_s:
                    runs.append((s, e))
                s = e
        i = j + 1
    for a, b in runs:
        t0, t1 = t_cst[a], t_cst[b - 1]
        g = np.arange(t0, t1, 1.0 / FS)
        if len(g) < int((2 * EDGE_S + blk_s) * FS):
            continue
        vv = np.interp(g, t_cst, D["vego"])
        if synth is None:
            sa = np.interp(g, t_cst, D["sa_deg"]); sr = np.interp(g, t_cst, D["sr_deg"])
        else:
            sa = np.interp(g, synth[2], synth[0]); sr = np.interp(g, synth[2], synth[1])
        X = prep_run(g, sa, sr, vv, sos, spring)
        keep = np.abs(sr) >= dwell
        # per-D filtered command on this grid
        UB = np.empty((len(dgrid), len(g)), dtype=np.float32)
        for q, dms in enumerate(dgrid):
            if interp_cmd:
                ud = np.interp(g - dms * 1e-3, t_e4, e4)
            else:                                   # zero-order hold (the CAN reality)
                idx = np.clip(np.searchsorted(t_e4, g - dms * 1e-3) - 1, 0, len(t_e4) - 1)
                ud = e4[idx]
            UB[q] = signal.sosfiltfilt(sos, ud)
        e = int(EDGE_S * FS); bs = int(blk_s * FS)
        for s in range(e, len(g) - e - bs + 1, bs):
            sl = slice(s, s + bs)
            m = keep[sl]
            if m.sum() < 0.25 * bs:
                continue
            Xb = X[sl][m]
            ub = UB[:, sl][:, m]
            out.append(dict(route=rk, v=float(np.median(vv[sl])), nrow=int(m.sum()),
                            A=Xb.T @ Xb, Bd=(ub @ Xb).astype(np.float64),
                            UU=np.einsum("dn,dn->d", ub, ub).astype(np.float64)))
        del UB, X
    del D
    return out


# --------------------------------------------------------------------------------------------------
def sse_curve(blocks, w=None, ridge=1e-12):
    """SSE(D) and beta(D) for a (weighted) set of blocks."""
    if not blocks:
        return None, None
    w = np.ones(len(blocks)) if w is None else np.asarray(w, float)
    A = sum(wi * bl["A"] for wi, bl in zip(w, blocks) if wi)
    Bd = sum(wi * bl["Bd"] for wi, bl in zip(w, blocks) if wi)
    UU = sum(wi * bl["UU"] for wi, bl in zip(w, blocks) if wi)
    A = A + ridge * np.trace(A) / 4.0 * np.eye(4)
    Ai = np.linalg.inv(A)
    beta = Bd @ Ai.T                              # (nD, 4)
    sse = UU - np.einsum("dj,dj->d", beta, Bd)
    return sse, beta


def argmin_sub(d, sse):
    """Parabolic sub-grid minimum of SSE(D) plus the local curvature."""
    i = int(np.argmin(sse))
    if 0 < i < len(sse) - 1:
        y0, y1, y2 = sse[i - 1], sse[i], sse[i + 1]
        den = (y0 - 2 * y1 + y2)
        sh = 0.5 * (y0 - y2) / den if den > 0 else 0.0
        return float(d[i] + sh * (d[1] - d[0])), float(den / (d[1] - d[0]) ** 2), i
    return float(d[i]), float("nan"), i


def fit_report(blocks, dgrid=D_MS, nboot=600, seed=7):
    sse, beta = sse_curve(blocks)
    if sse is None:
        return None
    Dstar, curv, i0 = argmin_sub(dgrid, sse)
    Dstar -= ZOH_CORR_MS
    nrow = sum(bl["nrow"] for bl in blocks)
    # curvature CI: SSE is a sum of squares; sigma^2 = SSE_min / (Neff - 4).  Neff from the residual
    # bandwidth: the band-pass keeps (f2-f1)/(fs/2) of the spectrum, so independent samples ~ nrow * that.
    frac = (BAND[1] - BAND[0]) / (FS / 2.0)
    neff = max(nrow * frac, 10.0)
    sig2 = sse[i0] / max(neff - 4, 1.0)
    var_d = 2.0 * sig2 / curv * (nrow / neff) if curv and curv > 0 else float("nan")
    ci_curv = (Dstar - 1.96 * math.sqrt(var_d), Dstar + 1.96 * math.sqrt(var_d)) if var_d == var_d and var_d > 0 else (float("nan"),) * 2
    rng = np.random.default_rng(seed)
    # block bootstrap (10 s blocks, multinomial weights)
    bb = []
    for _ in range(nboot):
        w = rng.multinomial(len(blocks), np.ones(len(blocks)) / len(blocks))
        s, _ = sse_curve(blocks, w)
        bb.append(argmin_sub(dgrid, s)[0] - ZOH_CORR_MS)
    # route-cluster bootstrap
    rts = sorted({bl["route"] for bl in blocks})
    rb = []
    if len(rts) > 1:
        for _ in range(nboot):
            pick = rng.choice(rts, len(rts))
            cnt = {r: int((pick == r).sum()) for r in rts}
            w = [cnt[bl["route"]] for bl in blocks]
            s, _ = sse_curve(blocks, w)
            rb.append(argmin_sub(dgrid, s)[0] - ZOH_CORR_MS)
    R2 = 1.0 - sse / np.maximum(sum(bl["UU"] for bl in blocks), 1e-30)
    def bat(dms):
        j = int(np.argmin(np.abs(dgrid - (dms + ZOH_CORR_MS))))
        return [float(x) for x in beta[j]]
    return dict(D=Dstar, i0=i0, n_blocks=len(blocks), n_rows=int(nrow), sse_min=float(sse[i0]),
                R2=float(R2[i0]), curv_ci=[float(x) for x in ci_curv],
                blk_ci=[float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))],
                blk_sd=float(np.std(bb)),
                route_ci=([float(np.percentile(rb, 2.5)), float(np.percentile(rb, 97.5))] if rb else None),
                beta=bat(Dstar), beta_m15=bat(Dstar - 15), beta_p15=bat(Dstar + 15),
                sse=[float(x) for x in sse], R2curve=[float(x) for x in R2])


# --------------------------------------------------------------------------------------------------
def simulate(rk, Dms, J, b, F, klevel=1.0, dt=0.001, stick=True, seed=1, noise=0.0,
             tmax=500.0, t_from=None, stop_deg=45.0, quant=True, spring="hold"):
    """POSITIVE CONTROL plant: J*acc = u(t-D) - b*rate - hold(angle,v) - F*sign(rate), Karnopp stick-slip,
    driven by the ROUTE'S OWN logged 0xE4 command (true ZOH), then sampled at the route's carState
    timestamps and quantised (angle 0.1 deg, rate 1 deg/s)."""
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    t_cst = np.array(D["t_cst"]); t_e4 = np.array(D["t_e4"]); e4 = np.array(D["e4_cmd"]) / E4_SCALE
    vego = np.array(D["vego"]); del D
    t0, t1 = max(t_cst[0], t_e4[0]) + 0.2, min(t_cst[-1], t_e4[-1]) - 0.2
    if t_from is not None:
        t0 = max(t0, t_from)
    t1 = min(t1, t0 + tmax)
    N = int((t1 - t0) / dt)
    tf = t0 + np.arange(N) * dt
    # ZOH command delayed by exactly Dms
    idx = np.clip(np.searchsorted(t_e4, tf - Dms * 1e-3) - 1, 0, len(t_e4) - 1)
    u = e4[idx]
    vf = np.interp(tf, t_cst, vego)
    rng = np.random.default_rng(seed)
    dn = rng.standard_normal(N) * noise if noise else None
    th = np.zeros(N); rt = np.zeros(N)
    x = 0.0; r = 0.0
    a, sb, sc = HOLD_SAT
    kv = np.interp(vf, HOLD_V_BP, HOLD_K_V) * klevel
    sv = a + sb * np.exp(-np.maximum(vf, 0.0) / sc)
    band = max(dt * F / J, 0.05)                   # Karnopp stick band (one step's worth of friction)
    nstick = nstop = 0
    for i in range(N):
        sp = kv[i] * x if spring == "lin" else kv[i] * sv[i] * math.tanh(x / sv[i])
        net = u[i] - sp - b * r + (dn[i] if dn is not None else 0.0)
        if stick and abs(r) < band and abs(net) <= F:          # stuck: static friction holds
            r = 0.0; nstick += 1
        else:
            fr = F * (1.0 if r > 0 else -1.0 if r < 0 else (1.0 if net > 0 else -1.0))
            r += dt * (net - fr) / J
        x += dt * r
        if x > stop_deg:
            x = stop_deg; r = min(r, 0.0); nstop += 1
        elif x < -stop_deg:
            x = -stop_deg; r = max(r, 0.0); nstop += 1
        th[i] = x; rt[i] = r
    ts = t_cst[(t_cst >= t0 + 0.5) & (t_cst <= t1 - 0.5)]
    sa = np.interp(ts, tf, th); sr = np.interp(ts, tf, rt)
    if quant:
        sa = np.round(sa / 0.1) * 0.1
        sr = np.round(sr / 1.0) * 1.0
    return sa, sr, ts, dict(stick_frac=nstick / N, stop_frac=nstop / N, max_deg=float(np.max(np.abs(th))),
                            rate_rms=float(np.sqrt(np.mean(rt ** 2))), sec=N * dt)


def engaged_start(rk, need=520.0):
    """Start time of the first window that holds `need` s with a lot of engaged hands-off driving."""
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    t_cst = D["t_cst"]
    act = np.interp(t_cst, D["t_cs"], (D["cs_active"] > 0.5).astype(float)) > 0.5
    ok = (act & (D["spress"] < 0.5)).astype(float)
    del D
    w = int(need * FS)
    if len(ok) <= w:
        return float(t_cst[0])
    c = np.concatenate([[0.0], np.cumsum(ok)])
    frac = (c[w:] - c[:-w]) / w
    return float(t_cst[int(np.argmax(frac))])


# --------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="pc", choices=["pc", "real", "v282"])
    ap.add_argument("--band", default="0.3,8.0")
    ap.add_argument("--dwell", type=float, default=DWELL)
    ap.add_argument("--zoh", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--spring", default="lin", choices=["lin", "hold"])
    ap.add_argument("--pcstop", type=float, default=300.0)
    a = ap.parse_args()
    band = tuple(float(x) for x in a.band.split(","))
    global PC_SPRING, PC_STOP, SPRING
    PC_SPRING, PC_STOP = a.spring, a.pcstop
    global BAND
    BAND = band
    sos = make_L(band)
    kw = dict(dwell=a.dwell, band=band, interp_cmd=not a.zoh)
    res = dict(band=list(band), dwell=a.dwell, zoh=bool(a.zoh), spring=a.spring,
               zoh_corr_ms=ZOH_CORR_MS)

    if a.what == "pc":
        print(f"POSITIVE CONTROL  band {band} dwell {a.dwell} cmd={'ZOH' if a.zoh else 'interp'}", flush=True)
        rk = "00000075--6c8687d5bd"
        t_from = engaged_start(rk)
        print(f"  route {rk}, synthetic plant driven by its logged 0xE4 from t={t_from:.0f} s, 500 s, dt 1 ms", flush=True)
        cases = [("fork J8e-5 b6e-4 k1", 8e-5, 6e-4, 0.020, 1.0),
                 ("fork k3 (3.3 Hz mode)", 8e-5, 6e-4, 0.020, 3.0),
                 ("heavy J1e-3 b3e-3 k3", 1e-3, 3e-3, 0.020, 3.0),
                 ("heavy J1e-3 b5e-3 k1", 1e-3, 5e-3, 0.020, 1.0),
                 ("fork k3 F0.011", 8e-5, 6e-4, 0.011, 3.0),
                 ("fork k2 F0.030", 8e-5, 6e-4, 0.030, 2.0)]
        res["pc"] = []
        for nm, J, b, F, kl in cases:
            for Dtrue in (30, 60):
                sa, sr, ts, info = simulate(rk, Dtrue, J, b, F, klevel=kl, t_from=t_from,
                                            spring=PC_SPRING, stop_deg=PC_STOP)
                bl = route_blocks(rk, sos, synth=(sa, sr, ts), spring=PC_SPRING, **kw)
                r = fit_report(bl, nboot=200)
                if r is None:
                    print(f"  {nm} D={Dtrue}: no blocks"); continue
                Jf, bf, gk, Ff = r["beta"]
                print(f"  {nm:22s} true D {Dtrue:3d} -> {r['D']:6.2f} ms  err {r['D']-Dtrue:+6.2f}  "
                      f"R2 {r['R2']:.3f}  blkCI[{r['blk_ci'][0]:.1f},{r['blk_ci'][1]:.1f}]  "
                      f"J {Jf:.2e}/{J:.0e}  b {bf:+.2e}/{b:.0e}  g_k {gk:+.3f}/{kl:.1f}  F {Ff:+.4f}/{F}  "
                      f"blk {r['n_blocks']:3d} | stick {info['stick_frac']*100:.0f}% stop {info['stop_frac']*100:.1f}% "
                      f"max {info['max_deg']:.0f} deg rateRMS {info['rate_rms']:.1f}", flush=True)
                res["pc"].append(dict(case=nm, J=J, b=b, F=F, klevel=kl, Dtrue=Dtrue, sim=info,
                                      **{k: v for k, v in r.items() if k not in ("sse", "R2curve")}))
                del bl
        (HERE / f"pc{a.tag}.json").write_text(json.dumps(res, indent=1, default=float))
        return

    rks = TORQUE if a.what == "real" else V282
    allb = []
    for rk in rks:
        bl = route_blocks(rk, sos, **kw)
        print(f"  {rk} {V.ROUTES[rk]['group']:6s} blocks {len(bl):4d}  rows {sum(x['nrow'] for x in bl):7d}", flush=True)
        allb += bl
    res["per_route"] = {}
    print(f"\n{a.what.upper()}  band {band} dwell {a.dwell} cmd={'ZOH' if a.zoh else 'interp'}")
    print("  bin        n_blk   rows     D*     blockCI        routeCI        curvCI       R2    "
          "J          b         g_k      F        | beta at D*-15 / D*+15")
    for lo, hi in SPD + [(0.0, 99.0)]:
        sel = [bl for bl in allb if lo <= bl["v"] < hi]
        r = fit_report(sel)
        if r is None:
            continue
        Jf, bf, gk, Ff = r["beta"]
        print(f"  v {lo:4.0f}-{hi:<4.0f} {r['n_blocks']:5d} {r['n_rows']:7d} {r['D']:6.2f} "
              f"[{r['blk_ci'][0]:5.1f},{r['blk_ci'][1]:5.1f}] "
              f"{'[%5.1f,%5.1f]'%tuple(r['route_ci']) if r['route_ci'] else '     --      '} "
              f"[{r['curv_ci'][0]:5.1f},{r['curv_ci'][1]:5.1f}] {r['R2']:.3f} "
              f"{Jf:9.2e} {bf:9.2e} {gk:+7.3f} {Ff:+8.4f} | "
              f"J {r['beta_m15'][0]:.1e}/{r['beta_p15'][0]:.1e} b {r['beta_m15'][1]:.1e}/{r['beta_p15'][1]:.1e} "
              f"gk {r['beta_m15'][2]:+.2f}/{r['beta_p15'][2]:+.2f} F {r['beta_m15'][3]:+.3f}/{r['beta_p15'][3]:+.3f}",
              flush=True)
        res[f"bin_{lo:.0f}_{hi:.0f}"] = r
    for rk in rks:
        sub = [bl for bl in allb if bl["route"] == rk]
        line = f"  {rk} {V.ROUTES[rk]['group']:5s}"
        res["per_route"][rk] = {}
        for lo, hi in SPD + [(0.0, 99.0)]:
            r = fit_report([bl for bl in sub if lo <= bl["v"] < hi], nboot=200)
            line += f"  {lo:.0f}-{hi:.0f}: " + (f"{r['D']:5.1f}[{r['blk_ci'][0]:.0f},{r['blk_ci'][1]:.0f}]n{r['n_blocks']}"
                                                if r else "  --  ")
            if r:
                res["per_route"][rk][f"bin_{lo:.0f}_{hi:.0f}"] = {k: v for k, v in r.items() if k not in ("sse", "R2curve")}
        print(line, flush=True)
    (HERE / f"{a.what}{a.tag}.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
