# -*- coding: utf-8 -*-
"""model_to_ctl2.py -- ATTRIBUTION of every layer between modelV2.action and the lateral controller.

Layers replayed against the LOGGED controlsState.desiredCurvature (ground truth):
  raw   = modelV2.action.desiredCurvature, zero-order held onto the 100 Hz control clock
  +LC   = raw + the lane-centering correction, re-implemented from the cached modelV2 channels
  clip  = clip_curvature(prev = LOGGED previous frame, ...)          <- one-step, so errors do not accumulate
  fin   = controlsState.desiredCurvature (logged)
"""
import os
import sys

import numpy as np

OV = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/oversteer/_scratch"
OT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/optune/_scratch"
TAGS = ("r39", "r3a", "r3c")
BUILD = {"r39": "rdf43 / LAF 2.11", "r3a": "tsfdo / LAF 4.0", "r3c": "tsfdo / LAF 3.6"}

DT_CTRL = 0.01
DT_M = 0.05
MIN_SPEED = 1.0
MAX_CURVATURE = 0.2
MAX_LATERAL_JERK = 5.0
MAX_LATERAL_ACCEL_NO_ROLL = 3.0
G = 9.81
FIT_M = 50.0
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def hold(ts, vs, t):
    i = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(vs) - 1)
    out = np.asarray(vs, float)[i]
    out[t < ts[0]] = np.nan
    return out


def blocks(mask, n):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if i - s >= n:
                out.append((s, i))
            s = None
    if s is not None and len(mask) - s >= n:
        out.append((s, len(mask)))
    return out


def boot(v, n=4000, seed=7):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if len(v) < 3:
        return (np.nan, np.nan)
    rs = np.random.RandomState(seed)
    s = np.median(v[rs.randint(0, len(v), (n, len(v)))], 1)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


# ----------------------------------------------------- lane_centering.py, re-implemented verbatim
LC = dict(MIN_V=5.0, MIN_PROB=0.6, MAX_STD=0.3, MIN_W=2.6, MAX_W=4.8, MAX_OFF=0.3,
          MIN_C2L=1.1, MAX_RAW=0.004, MAX_GAIN=0.30, TAU=0.4, DEAD=0.08,
          E2E_MAX_STD=0.35, BI_START=0.15, BI_FULL=0.50)


def lc_raw_correction(x, ll1, ll2, px, py, pystd, prob, std, v, offset, e2e):
    """Vectorised over model frames.  Returns (valid, raw_correction) per frame."""
    n = len(v)
    ok = np.ones(n, bool)
    ok &= np.isfinite(prob[:, 1]) & np.isfinite(prob[:, 2]) & np.isfinite(std[:, 1]) & np.isfinite(std[:, 2])
    ok &= (prob[:, 1] >= LC["MIN_PROB"]) & (prob[:, 2] >= LC["MIN_PROB"])
    ok &= (prob[:, 1] <= 1.0) & (prob[:, 2] <= 1.0)
    ok &= (std[:, 1] >= 0) & (std[:, 2] >= 0) & (std[:, 1] <= LC["MAX_STD"]) & (std[:, 2] <= LC["MAX_STD"])
    look = np.clip(v, 8.0, 35.0)
    ok &= (look >= x[0]) & (look <= x[-1])
    li = np.array([np.interp(look[i], x, ll1[i]) for i in range(n)])
    ri = np.array([np.interp(look[i], x, ll2[i]) for i in range(n)])
    my = np.array([np.interp(look[i], px[i], py[i]) for i in range(n)])
    ys = np.array([np.interp(look[i], px[i], pystd[i]) for i in range(n)])
    w = ri - li
    ok &= (w >= LC["MIN_W"]) & (w <= LC["MAX_W"])
    max_safe = np.minimum(LC["MAX_OFF"], np.maximum(0.0, w * 0.5 - LC["MIN_C2L"]))
    target = 0.5 * (li + ri) + np.clip(offset, -max_safe, max_safe)
    err = target - my
    ea = np.abs(err)
    err = np.where(ea <= LC["DEAD"], 0.0, np.copysign(ea - LC["DEAD"], err))
    bi = np.clip((ea - LC["BI_START"]) / (LC["BI_FULL"] - LC["BI_START"]), 0.0, 1.0)
    use_bi = np.isfinite(ys) & (ys >= 0.0) & (ys <= LC["E2E_MAX_STD"])
    err = np.where(use_bi, err * (1.0 - e2e * bi), err)
    return ok & np.isfinite(err), 2.0 * err / look ** 2, ea


def lc_apply(valid, raw_corr, gate, gain=LC["MAX_GAIN"]):
    """The 0.4 s smoother on the 100 Hz control clock; gate = enabled & latActive & v>=5 & no LC."""
    a = 1.0 - np.exp(-DT_CTRL / LC["TAU"])
    a_rel = 1.0 - np.exp(-DT_CTRL / 0.20)
    c = 0.0
    out = np.zeros(len(gate))
    for i in range(len(gate)):
        if not gate[i]:
            c = 0.0
        elif valid[i]:
            tgt = float(np.clip(raw_corr[i], -LC["MAX_RAW"], LC["MAX_RAW"])) * gain
            c += a * (tgt - c)
        else:
            c += a_rel * (0.0 - c)
        out[i] = c
    return out


def clip_curvature(v_ego, prev, new, roll, jerk_factor=1.0):
    v = max(v_ego, MIN_SPEED)
    rate = (MAX_LATERAL_JERK * jerk_factor) / v ** 2
    c = min(max(new, prev - rate * DT_CTRL), prev + rate * DT_CTRL)
    jb = (c != new)
    rc = roll * G
    lo = (-MAX_LATERAL_ACCEL_NO_ROLL + rc) / v ** 2
    hi = (MAX_LATERAL_ACCEL_NO_ROLL + rc) / v ** 2
    c2 = min(max(c, lo), hi)
    ab = (c2 != c)
    c3 = min(max(c2, -MAX_CURVATURE), MAX_CURVATURE)
    return c3, jb, ab, (c3 != c2)


def frame(tag):
    M = np.load(os.path.join(OV, f"{tag}_modelv2.npz"), allow_pickle=True)
    B = np.load(os.path.join(OT, f"{tag}_backcalc.npz"), allow_pickle=True)
    ct = np.asarray(B["ctl_t"], float)
    f = dict(t=ct)
    f["fin"] = np.asarray(B["ctl_descurv"], float)
    f["meas"] = np.asarray(B["ctl_curv"], float)
    f["lat"] = hold(np.asarray(B["cc_t"], float), np.asarray(B["cc_lat"], float), ct) > 0.5
    f["v"] = np.interp(ct, np.asarray(B["cs_t"], float), np.asarray(B["cs_v"], float))
    f["roll"] = np.interp(ct, np.asarray(B["lpar_t"], float), np.asarray(B["lpar_roll"], float))
    f["press"] = hold(np.asarray(B["cs_t"], float), np.asarray(B["cs_pressed"], float), ct) > 0.5
    f["blink"] = np.zeros(len(ct), bool)

    mt = np.asarray(M["mdl_t"], float)
    # laneLines live on the FIXED X_IDXS grid; position.x is TIME-parameterised and varies per frame.
    x = np.asarray(M["mdl_ll1_x"], float)[0]
    f["raw"] = hold(mt, np.asarray(M["mdl_descurv"], float), ct)
    f["lcs"] = hold(mt, np.asarray(M["mdl_lcs"], float), ct)
    ll1 = np.asarray(M["mdl_ll1_y"], float); ll2 = np.asarray(M["mdl_ll2_y"], float)
    yc = 0.5 * (ll1 + ll2)
    m = np.isfinite(x) & (x >= 0) & (x <= FIT_M)
    xs = x[m]
    A = np.stack([np.ones_like(xs), xs, 0.5 * xs ** 2, xs ** 3 / 6.0], 1)
    Ys = np.where(np.isfinite(yc[:, m]), yc[:, m], 0.0)
    P, *_ = np.linalg.lstsq(A, Ys.T, rcond=None)
    kr = P[2].copy(); kr[~np.isfinite(yc[:, m]).all(1)] = np.nan
    f["kroad"] = hold(mt, kr, ct)
    px = np.asarray(M["mdl_pos_x"], float); py = np.asarray(M["mdl_pos_y"], float)
    kp = np.full(len(mt), np.nan)
    for i in range(len(mt)):
        o = np.isfinite(px[i]) & np.isfinite(py[i]) & (px[i] >= 0) & (px[i] <= FIT_M)
        if o.sum() < 6 or px[i][o].max() < 0.6 * FIT_M:
            continue
        q = px[i][o]
        Ai = np.stack([np.ones_like(q), q, 0.5 * q ** 2, q ** 3 / 6.0], 1)
        c, *_ = np.linalg.lstsq(Ai, py[i][o], rcond=None)
        kp[i] = c[2]
    f["kpath"] = hold(mt, kp, ct)
    llp = np.asarray(M["mdl_llprob"], float)
    lls = np.asarray(M["mdl_llstd"], float)
    lw = ll2[:, 0] - ll1[:, 0]
    ll_ok = ((llp[:, 1] > 0.5) & (llp[:, 2] > 0.5) & (lls[:, 1] < 0.5) & (lls[:, 2] < 0.5)
             & (lw > 2.6) & (lw < 4.8))
    f["llok"] = hold(mt, ll_ok.astype(float), ct) > 0.5

    # lane-centering, on the model clock then held
    vm = np.interp(mt, np.asarray(B["cs_t"], float), np.asarray(B["cs_v"], float))
    valid_m, rawc_m, ea_m = lc_raw_correction(
        x, ll1, ll2, px, py, np.asarray(M["mdl_pos_ystd"], float), llp, lls, vm, 0.0, 1.0)
    _, rawc0_m, _ = lc_raw_correction(
        x, ll1, ll2, px, py, np.asarray(M["mdl_pos_ystd"], float), llp, lls, vm, 0.0, 0.0)  # e2e=0
    f["lc_valid"] = hold(mt, valid_m.astype(float), ct) > 0.5
    f["lc_raw"] = hold(mt, rawc_m, ct)
    f["lc_raw_e0"] = hold(mt, rawc0_m, ct)
    f["lc_err"] = hold(mt, ea_m, ct)                    # |plan - lane centre| at the lookahead, m
    gate = f["lat"] & (f["v"] >= LC["MIN_V"]) & (f["lcs"] == 0) & (~f["press"])
    f["lc_applied"] = lc_apply(f["lc_valid"], f["lc_raw"], gate)
    f["lc_e0"] = lc_apply(f["lc_valid"], f["lc_raw_e0"], gate)
    f["lc_e0_g1"] = lc_apply(f["lc_valid"], f["lc_raw_e0"], gate, gain=1.0)

    ok = f["lat"] & np.isfinite(f["raw"]) & np.isfinite(f["fin"]) & np.isfinite(f["v"]) & np.isfinite(f["roll"])
    if tag == "r3a":
        rel = ct - np.asarray(B["co_t"], float)[0]
        ok &= ~((rel > 597.0) & (rel < 657.1))
    f["ok"] = ok
    f["curve"] = ok & (np.abs(f["kroad"]) >= 1.5e-3) & (f["lcs"] == 0) & (~f["press"]) & f["llok"] & (f["v"] >= 5)
    return f


def run(tag):
    f = frame(tag)
    n = len(f["t"])
    ok, curve = f["ok"], f["curve"]
    raw, fin, v, roll = f["raw"], f["fin"], f["v"], f["roll"]

    rep = np.full(n, np.nan); rep_lc = np.full(n, np.nan)
    jb = np.zeros(n, bool); ab = np.zeros(n, bool); mb = np.zeros(n, bool)
    for i in range(n):
        if not ok[i]:
            continue
        prev = fin[i - 1] if i > 0 and ok[i - 1] and np.isfinite(fin[i - 1]) else fin[i]
        c, j, a, mm = clip_curvature(v[i], prev, raw[i], roll[i])
        rep[i] = c; jb[i] = j; ab[i] = a; mb[i] = mm
        rep_lc[i], _, _, _ = clip_curvature(v[i], prev, raw[i] + f["lc_applied"][i], roll[i])

    pr("=" * 118)
    pr(f"{tag}   {BUILD[tag]}   engaged {ok.sum():6d} fr ({ok.sum()*DT_CTRL:6.0f} s)   "
       f"curve {curve.sum():6d} fr ({curve.sum()*DT_CTRL:5.0f} s)")
    pr("-" * 118)

    # -------- 1. ratio of block medians (matches the published pipeline's method) --------
    bl = blocks(curve, int(3.0 / DT_CTRL))
    rows = []
    for a, b in bl:
        kr = med(np.abs(f["kroad"][a:b])); kp = med(np.abs(raw[a:b])); kc = med(np.abs(fin[a:b]))
        kt = med(np.abs(f["kpath"][a:b]))
        if kr > 1e-4 and kp > 1e-4:
            rows.append((kp / kr, kc / kp, kt / kr))
    R = np.array(rows) if rows else np.zeros((0, 3))
    if len(R) >= 4:
        for j, nm in enumerate(("K_ACTION/K_ROAD  (the MODEL)", "K_FINAL/K_ACTION (the STACK)", "K_PATH/K_ROAD    (the MODEL)")):
            lo, hi = boot(R[:, j])
            pr(f"  {nm:32s} = {med(R[:,j]):6.3f}  95% CI [{lo:5.3f}, {hi:5.3f}]   ({len(R)} curve blocks >= 3 s)")

    # -------- 2. the stack's absolute contribution --------
    d = fin - raw
    s = np.sign(f["kroad"])
    for nm, m in (("ENGAGED", ok), ("CURVE", curve)):
        a = np.abs(d[m])
        pr(f"  |final-raw| {nm:8s}: p50={med(a):.2e} p90={np.percentile(a,90):.2e} p99={np.percentile(a,99):.2e} "
           f"max={a.max():.2e}   vs |raw| p50={med(np.abs(raw[m])):.2e}")
    b = (d * s)[curve]
    lo, hi = boot(b)
    pr(f"  (final-raw)*sign(K_road) CURVE: p50={med(b):+.2e} [95% CI {lo:+.2e},{hi:+.2e}]  mean={b.mean():+.2e}  "
       f"[<0 = the stack straightens]")
    pr(f"     as a fraction of |K_road|:  {med(b)/med(np.abs(f['kroad'][curve])):+.3%} (p50)   "
       f"mean {b.mean()/med(np.abs(f['kroad'][curve])):+.3%}")

    # -------- 3. attribution: clip_curvature vs the pre-clip layers --------
    m = ok & np.isfinite(rep)
    e_clip = rep - fin
    e_lc = rep_lc - fin
    pr(f"  residual |replay - logged|   raw->clip only : p50={med(np.abs(e_clip[m])):.2e}  "
       f"p99={np.percentile(np.abs(e_clip[m]),99):.2e}   frames >3e-5: {100*(np.abs(e_clip)>3e-5)[m].mean():5.2f}%")
    pr(f"  residual |replay - logged|   raw+LC->clip   : p50={med(np.abs(e_lc[m])):.2e}  "
       f"p99={np.percentile(np.abs(e_lc[m]),99):.2e}   frames >3e-5: {100*(np.abs(e_lc)>3e-5)[m].mean():5.2f}%")
    mc = curve & np.isfinite(rep)
    pr(f"     on CURVE frames             raw->clip     : p50={med(np.abs(e_clip[mc])):.2e}   "
       f"raw+LC->clip: p50={med(np.abs(e_lc[mc])):.2e}   -> LC explains "
       f"{100*(1 - med(np.abs(e_lc[mc]))/max(med(np.abs(e_clip[mc])),1e-12)):5.1f}% of it")

    # -------- 4. lane centering, sized --------
    lcv = f["lc_applied"][curve]
    pr(f"  lane-centering correction APPLIED, CURVE: p50|c|={med(np.abs(lcv)):.2e} p95={np.percentile(np.abs(lcv),95):.2e} "
       f"max={np.abs(lcv).max():.2e}  = {med(np.abs(lcv))/med(np.abs(raw[curve])):.2%} of |K_action| (p50)")
    ins = (f["lc_applied"] * s)[curve]
    pr(f"     signed*sign(K_road): p50={med(ins):+.2e} mean={ins.mean():+.2e}   valid duty {100*f['lc_valid'][curve].mean():5.1f}%")
    pr(f"     |plan - lane centre| at the LC lookahead, CURVE: p50={med(f['lc_err'][curve]):.3f} m  "
       f"p90={np.percentile(f['lc_err'][curve][np.isfinite(f['lc_err'][curve])],90):.3f} m  "
       f"frac >= 0.50 m (e2e break-in FULL, correction -> 0): {100*(f['lc_err'][curve]>=0.50).mean():4.1f}%")
    for nm, arr in (("e2e_authority 0.0 (gain .30)", f["lc_e0"]), ("e2e_authority 0.0 + MAX_GAIN 1.0", f["lc_e0_g1"])):
        q = (arr * s)[curve]
        pr(f"     COUNTERFACTUAL {nm:32s}: p50={med(np.abs(arr[curve])):.2e}  signed p50={med(q):+.2e} "
           f"= {med(q)/med(np.abs(raw[curve])):+.2%} of |K_action|")

    # -------- 5. clip_curvature duty, and whether it is real or the 20 Hz staircase --------
    pr(f"  clip_curvature binding ENGAGED: jerk {100*jb[ok].mean():6.3f}%  latacc {100*ab[ok].mean():6.3f}%  "
       f"maxcurv {100*mb[ok].mean():6.3f}%   | CURVE: jerk {100*jb[curve].mean():6.3f}%  latacc {100*ab[curve].mean():6.3f}%")
    mt_rate = np.abs(np.gradient(raw, f["t"]))               # held signal -> impulses at model steps
    # sustained rate: differentiate the model signal on its OWN clock (0.05 s), then hold
    lim = MAX_LATERAL_JERK / np.maximum(v, MIN_SPEED) ** 2
    sus = np.abs(np.gradient(np.convolve(np.nan_to_num(raw), np.ones(5) / 5, "same"), f["t"]))
    pr(f"     model-clock demand rate vs the 5.0/v^2 limit, CURVE: p50={med(sus[curve]):.4f}  p95={np.percentile(sus[curve],95):.4f}  "
       f"limit p50={med(lim[curve]):.4f}   frames with SUSTAINED rate > limit: {100*(sus>lim)[curve].mean():5.2f}%")
    # lag the stack adds
    lags = np.arange(-30, 31)
    sig_a = raw[curve]; sig_b = fin[curve]
    best, bl_ = None, None
    aa = raw - med(raw[ok]); bb = fin - med(fin[ok])
    idx = np.flatnonzero(curve)
    for L in lags:
        j = idx + L
        j = j[(j >= 0) & (j < n)]
        k = j - L
        c = np.corrcoef(aa[k], bb[j])[0, 1]
        if best is None or c > best:
            best, bl_ = c, L
    pr(f"     LAG the whole post-model stack adds (peak xcorr, CURVE): {bl_*DT_CTRL*1000:+.0f} ms  (r={best:.4f})")

    # -------- 6. low-speed layer reachability --------
    pr(f"  speed, CURVE frames: p05={np.percentile(v[curve],5):.1f} p50={med(v[curve]):.1f} p95={np.percentile(v[curve],95):.1f} m/s   "
       f"<7.0 (turn-lead): {100*(v[curve]<7.0).mean():.2f}%  <4.47 (turn-hold): {100*(v[curve]<4.47).mean():.2f}%  "
       f"<4.0 (twitch guard): {100*(v[curve]<4.0).mean():.2f}%")
    pr(f"  ENGAGED frames below those ceilings: <7.0 {100*(v[ok]<7.0).mean():.2f}%  <4.47 {100*(v[ok]<4.47).mean():.2f}%  "
       f"<4.0 {100*(v[ok]<4.0).mean():.2f}%   lane-change frames: {100*(f['lcs'][ok]!=0).mean():.2f}%")
    return f


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for t in TAGS:
        run(t)
    with open(os.path.join(OV, "model_to_ctl2_out.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("\nwrote", os.path.join(OV, "model_to_ctl2_out.txt"))
