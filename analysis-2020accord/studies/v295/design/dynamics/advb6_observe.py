"""ADV-bytes step 6: OBSERVABILITY of A1017 on the existing wire, re-derived independently of d3_attribution.py.

Byte-exact march with plib.march (the kit's third implementation, NOT the harness Lane the designer used) of V294 and
A1017 on r71b's own command and 1 kHz rate; synthetic A1017 flight = quant(T_A1017) + the REAL tap residual.

 (A) the exact-model regression (the design's read #1) on windows that a ONE-SHORT-DRIVE doctrine can supply:
     A1 the designer's windows (N consecutive HANDS-OFF engaged tap frames, N = 1500 / 750) + the route time they span
     A2 CONTIGUOUS route-time windows (30 s / 15 s), hands-off frames only, and ALL engaged frames (hands-on included)
     A3 SYMPTOMATIC windows: contiguous 15 / 30 s at 5-15 m/s ranked by 1.6-3 Hz wheel-rate energy (hard turns)
     each with a 1 s AND a 3 s block bootstrap; the decision rule as pre-registered (beta >= 0.5 live, <= 0.3 not)
 (B) the metric agent's trim-footprint |K| regression (its OWN code, accel_tracking_metric.trim_footprint on its OWN
     grid) run on the real tap and on the synthetic A1017 tap: pooled |K|/phase, and the per-window spread vs the
     pre-registered thresholds (|K|(0.3-1) >= 0.28 live; > 0.45 or dphase < -30 "arithmetic wrong").
"""
import contextlib, io, json, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(V295, "plant"), os.path.join(V295, "lib"), os.path.join(V295, "metric")):
    sys.path.insert(0, p)
import plib as P  # noqa: E402
import r71b_cache as RC  # noqa: E402
OUT = []
def pr(*a):
    s = " ".join(str(v) for v in a); print(s, flush=True); OUT.append(s)

d = P.load()
c = RC.v294_cells()
cache = os.path.join(HERE, "_scratch", "advb6_march.npz")
if os.path.exists(cache):
    z = np.load(cache); T0, T1 = z["T0"], z["T1"]
else:
    t0 = time.time()
    T0 = P.march(d["sgn"], d["idx"], d["m"], c, x1k=d["x1k"], trim=True)
    T1 = P.march(d["sgn"], d["idx"], d["m"], c, x1k=d["x1k"], trim=True, fb_a=1017)
    np.savez(cache, T0=T0, T1=T1)
    pr("marched 2 lanes x %d ticks in %.0f s" % (len(T0), time.time() - t0))
sg = d["sg"]
mm = int(np.sum(sg * T0 != d["T1k_live"]))
pr("POSITIVE CONTROL: plib.march(V294) * sg vs the cached T1k_live: %d mismatching ticks of %d (must be 0)" % (mm, len(T0)))
assert mm == 0
tt = d["tick_tap"]; tap = d["T_tap"].astype(float); j = d["j100"]
L0, L1 = sg * T0[tt], sg * T1[tt]
q0, q1 = P.quant(L0), P.quant(L1)
e = tap - q0
r = (L1 - L0).astype(float)
y_syn = q1 - q0 + e
y_null = e
eng = d["eng"][j].astype(bool)
pressed = d["pressed"][j]
ho = eng & (np.abs(d["bar"][j]) < 400) & ~pressed
hon = eng & ~ho
ttap = d["t_tap"] - d["t"][0]
v = d["v"][j]
pr("route %.0f s; engaged tap frames %.0f s; hands-off engaged %.0f s; hands-on engaged %.0f s" % (
    ttap[-1], eng.sum() / 50, ho.sum() / 50, hon.sum() / 50))
pr("real residual e rms: hands-off %.2f, hands-on %.2f counts; footprint |dT| rms hands-off %.2f (p99 %.1f), hands-on %.2f" % (
    np.sqrt(np.mean(e[ho] ** 2)), np.sqrt(np.mean(e[hon] ** 2)), np.sqrt(np.mean(r[ho] ** 2)), np.percentile(np.abs(r[ho]), 99),
    np.sqrt(np.mean(r[hon] ** 2)) if hon.any() else float("nan")))
rng = np.random.default_rng(20260930)

def beta_se(y, rr, blk):
    den = float(np.sum(rr * rr))
    if den <= 0 or len(y) < 3 * blk:
        return float("nan"), float("nan")
    b_ = float(np.sum(y * rr) / den)
    nb = len(y) // blk
    Y = y[:nb * blk].reshape(nb, blk); R = rr[:nb * blk].reshape(nb, blk)
    bs = []
    for _ in range(300):
        ii = rng.integers(0, nb, nb); dd = np.sum(R[ii] ** 2)
        bs.append(np.sum(Y[ii] * R[ii]) / dd if dd > 0 else np.nan)
    return b_, float(np.nanstd(bs))

def summarize(name, W, extra=""):
    rows = []
    for w in W:
        if len(w) < 150:
            continue
        b1, s1 = beta_se(y_syn[w], r[w], 50); bn1, sn1 = beta_se(y_null[w], r[w], 50)
        b3, s3 = beta_se(y_syn[w], r[w], 150); bn3, sn3 = beta_se(y_null[w], r[w], 150)
        rows.append((b1, s1, bn1, sn1, s3, sn3, np.sqrt(np.mean(r[w] ** 2)), len(w) / 50.0))
    if not rows:
        pr("  %-58s no windows" % name); return None
    A = np.array(rows)
    zs1, zn1 = A[:, 0] / A[:, 1], A[:, 2] / A[:, 3]
    zs3, zn3 = A[:, 0] / A[:, 4], A[:, 2] / A[:, 5]
    miss = np.mean(A[:, 0] < 0.5); amb = np.mean((A[:, 0] > 0.3) & (A[:, 0] < 0.5))
    fa = np.mean(A[:, 2] > 0.3); fa5 = np.mean(A[:, 2] >= 0.5)
    pr("  %-58s n %3d | syn beta med %.2f [p5 %.2f] z1 med %4.1f (frac>3 %.2f) z3 med %4.1f (frac>3 %.2f) | null beta med %+.3f "
       "[p5 %+.2f, p95 %+.2f] |z1|>3 %.2f |z3|>3 %.2f | RULE: syn<0.5 %.2f, null>0.3 %.2f, null>=0.5 %.2f | |dT| rms med %.1f %s" % (
           name, len(A), np.median(A[:, 0]), np.percentile(A[:, 0], 5), np.nanmedian(zs1), np.nanmean(zs1 > 3), np.nanmedian(zs3),
           np.nanmean(zs3 > 3), np.median(A[:, 2]), np.percentile(A[:, 2], 5), np.percentile(A[:, 2], 95), np.nanmean(np.abs(zn1) > 3),
           np.nanmean(np.abs(zn3) > 3), miss, fa, fa5, np.median(A[:, 6]), extra))
    return dict(n=len(A), syn_beta_med=float(np.median(A[:, 0])), syn_beta_p5=float(np.percentile(A[:, 0], 5)),
                z1_med=float(np.nanmedian(zs1)), frac_z1=float(np.nanmean(zs1 > 3)), z3_med=float(np.nanmedian(zs3)),
                frac_z3=float(np.nanmean(zs3 > 3)), null_beta_med=float(np.median(A[:, 2])),
                null_p95=float(np.percentile(A[:, 2], 95)), null_absz1_gt3=float(np.nanmean(np.abs(zn1) > 3)),
                null_absz3_gt3=float(np.nanmean(np.abs(zn3) > 3)), rule_miss=float(miss), rule_null_gt03=float(fa))

J = {}
pr("\n(A1) the designer's windows: N consecutive hands-off engaged tap frames")
idx_ho = np.flatnonzero(ho)
for N in (1500, 750):
    W = [idx_ho[k * N:(k + 1) * N] for k in range(len(idx_ho) // N)]
    spans = np.array([ttap[w[-1]] - ttap[w[0]] for w in W])
    J["A1_%d" % N] = summarize("%d hands-off frames (%.0f s of hands-off engaged)" % (N, N / 50), W,
                               "| route time spanned med %.0f s [min %.0f, max %.0f]" % (np.median(spans), spans.min(), spans.max()))
pr("\n(A2) CONTIGUOUS route-time windows")
for Ws in (30.0, 15.0):
    edges = np.arange(0, ttap[-1], Ws)
    wid = np.searchsorted(edges, ttap, side="right") - 1
    for lab, msk in (("hands-off frames only", ho), ("ALL engaged frames (hands-on incl.)", eng)):
        W = [np.flatnonzero((wid == k) & msk) for k in range(len(edges))]
        W = [w for w in W if len(w) >= 0.5 * Ws * 50]          # at least half the window usable
        J["A2_%d_%s" % (Ws, "ho" if msk is ho else "eng")] = summarize("contiguous %2.0f s, %s (>= 50 %% usable)" % (Ws, lab), W)
pr("\n(A3) SYMPTOMATIC windows: contiguous, mean speed 5-15 m/s, ranked by 1.6-3 Hz wheel-rate energy (hard turns)")
from scipy import signal as S  # noqa: E402
om = d["om"]
sos = S.butter(2, [1.6, 3.0], "bandpass", fs=100, output="sos")
e_band = S.sosfiltfilt(sos, np.nan_to_num(om)) ** 2
for Ws in (30.0, 15.0):
    n100 = int(Ws * 100)
    cand = []
    for s0 in range(0, len(om) - n100, int(n100 / 2)):
        sl = slice(s0, s0 + n100)
        if d["eng"][sl].mean() < 0.8:
            continue
        vm = d["v"][sl].mean()
        if 5.0 <= vm < 15.0:
            cand.append((float(e_band[sl].mean()), s0))
    cand.sort(reverse=True)
    chosen = []
    for en, s0 in cand:
        if all(abs(s0 - c0) >= n100 for c0 in chosen):
            chosen.append(s0)
        if len(chosen) >= 12:
            break
    for lab, msk in (("hands-off frames only", ho), ("ALL engaged frames", eng)):
        W = [np.flatnonzero((j >= s0) & (j < s0 + n100) & msk) for s0 in chosen]
        J["A3_%d_%s" % (Ws, "ho" if msk is ho else "eng")] = summarize("symptomatic %2.0f s x%d, %s" % (Ws, len(chosen), lab), W,
                                                                        "| hands-off share med %.2f" % np.median([
                                                                            ho[(j >= s0) & (j < s0 + n100)].mean() for s0 in chosen]))

# ---------------------------------------------------------------------------------------------------------------------
pr("\n(B) the metric agent's trim-footprint |K| on its OWN grid and code: real V294 tap vs synthetic A1017 tap")
with contextlib.redirect_stdout(io.StringIO()):
    import accel_tracking_metric as M
g = M.build_grid("r71b_v294")
# the synthetic delta tap (tap sign) mapped onto the metric's 100 Hz grid by time; metric T = -tap
dq = (q1 - q0)
tg = g["t"]
real_interp = -np.interp(tg, d["t_tap"], tap)
ok = g["eng"] & (tg > d["t_tap"][0]) & (tg < d["t_tap"][-1])
best = max(((np.corrcoef(g["T"][ok], np.roll(real_interp, k)[ok])[0, 1], k) for k in range(-5, 6)))
pr("  alignment check: corr(metric T, -interp(plib tap)) = %.5f at shift %+d frames (must be ~1 at 0)" % best)
g_syn = dict(g)
g_syn["T"] = g["T"] - np.interp(tg, d["t_tap"], dq)
res = {}
for nm, gg in (("real V294 tap", g), ("synthetic A1017", g_syn)):
    res[nm] = {}
    for bnm, f1, f2 in M.FBANDS:
        B, valid = M.band_signals(gg, f1, f2, ["T", "Tff", "alpha_w"], hilb=("T", "Tff", "alpha_w"))
        sel = valid & gg["HO"]
        tfp = M.trim_footprint(B["T"], B["Tff"], B["HTff"], B["alpha_w"], B["Halpha_w"], sel, gg["blk"], np.random.default_rng(7))
        # per-window point estimates on contiguous 30 s / 15 s windows (HO frames inside)
        win = {}
        for Ws in (30, 15):
            wid = (gg["tr"] // Ws).astype(int)
            Ks, Ps = [], []
            for k in np.unique(wid[sel]):
                s2 = sel & (wid == k)
                if s2.sum() < 0.5 * Ws * 100:
                    continue
                X = np.column_stack([B["Tff"], B["HTff"], B["alpha_w"], B["Halpha_w"]])[s2]
                cc = np.linalg.lstsq(X, B["T"][s2], rcond=None)[0]
                Ks.append(np.hypot(cc[2], cc[3])); Ps.append(np.degrees(np.arctan2(-cc[3], cc[2])))
            win[Ws] = (np.array(Ks), np.array(Ps))
        res[nm][bnm] = (tfp, win)
        pr("  %-16s %-6s pooled |K| %.3f [%.3f, %.3f] phase %+.0f deg (%.0f s) | 30 s windows n %d |K| med %.3f p5-p95 [%.3f, %.3f] "
           "| 15 s windows n %d |K| med %.3f p5-p95 [%.3f, %.3f]" % (
               nm, bnm, tfp["K_mag"], tfp["K_ci"][0], tfp["K_ci"][1], tfp["K_phase_deg"], tfp["sec"], len(win[30][0]),
               np.median(win[30][0]), np.percentile(win[30][0], 5), np.percentile(win[30][0], 95), len(win[15][0]),
               np.median(win[15][0]), np.percentile(win[15][0], 5), np.percentile(win[15][0], 95)))
pr("\n  pre-registered |K| sentences, per window (0.3-1 Hz):")
for Ws in (30, 15):
    Kr, Pr_ = res["real V294 tap"]["0.3-1"][1][Ws]
    Ks, Ps = res["synthetic A1017"]["0.3-1"][1][Ws]
    ph0 = res["real V294 tap"]["0.3-1"][0]["K_phase_deg"]
    pr("   %2d s: synthetic A1017: |K| >= 0.28 (LIVE) in %.2f of %d windows; |K| > 0.45 ('arithmetic wrong') in %.2f; "
       "dphase < -30 deg vs the V294 pooled phase in %.2f" % (Ws, np.mean(Ks >= 0.28), len(Ks), np.mean(Ks > 0.45),
                                                          np.mean(((Ps - ph0 + 180) % 360 - 180) < -30)))
    pr("         real V294 (the null): |K| >= 0.28 (false LIVE) in %.2f of %d windows; |K| > 0.45 in %.2f" % (
        np.mean(Kr >= 0.28), len(Kr), np.mean(Kr > 0.45)))
J["B"] = {nm: {b: dict(K=v[0]["K_mag"], ci=v[0]["K_ci"], ph=v[0]["K_phase_deg"],
                       w30=[float(np.median(v[1][30][0])), float(np.percentile(v[1][30][0], 5)), float(np.percentile(v[1][30][0], 95))],
                       w15=[float(np.median(v[1][15][0])), float(np.percentile(v[1][15][0], 5)), float(np.percentile(v[1][15][0], 95))])
               for b, v in res[nm].items()} for nm in res}
json.dump(J, open(os.path.join(HERE, "advb6_observe.json"), "w"), indent=1, default=float)
open(os.path.join(HERE, "advb6_observe_out.txt"), "w").write("\n".join(OUT) + "\n")
