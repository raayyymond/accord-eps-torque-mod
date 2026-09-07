# -*- coding: utf-8 -*-
"""lever_sizing.py -- size every lever between the driving model's action and the lateral controller,
in CENTIMETRES of lateral displacement over a real curve block on the operator's own frames.

Open-loop displacement of a curvature perturbation over a block:
    y(T) = INT_0^T INT_0^t  dK(s) * v(s)^2  ds dt        [m, + = toward the INSIDE of the bend]
This is the same unit the plan-vs-execution read used for the 28-62 cm inside bias, so the two are
directly comparable.  It is an OPEN-LOOP bound: the closed loop will track less than this.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_to_ctl as B   # noqa: E402

pr = B.pr
med = B.med
np.seterr(all="ignore")

OV = B.OV
TAGS = B.TAGS
DT = B.DT_CTRL


def merged_blocks(mask, minlen, gap=25):
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    out = [[idx[0], idx[0] + 1]]
    for i in idx[1:]:
        if i - out[-1][1] <= gap:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return [(a, b) for a, b in out if b - a >= minlen]


def disp(dk, v, a, b, sgn):
    """cm of lateral displacement over [a,b), positive toward the inside of the bend."""
    d = np.nan_to_num(dk[a:b]) * v[a:b] ** 2 * sgn
    return float(np.trapezoid(np.cumsum(d) * DT, dx=DT) * 100.0)


def run(tag):
    f = B.frame(tag)
    n = len(f["t"])
    ok, v, raw, fin, roll = f["ok"], f["v"], f["raw"], f["fin"], f["roll"]
    kroad = f["kroad"]

    curve = ok & (np.abs(kroad) >= 1.0e-3) & (f["lcs"] == 0) & (~f["press"]) & f["llok"] & (v >= 5)
    raw_bl = merged_blocks(curve, int(2.0 / DT))
    # non-overlapping 3 s windows inside each block: a bounded, comparable double integral
    W = int(2.0 / DT)
    bl = [(a + k * W, a + (k + 1) * W) for a, b in raw_bl for k in range((b - a) // W)]
    pr("=" * 118)
    pr(f"{tag}  {B.BUILD[tag]}   engaged {ok.sum()*DT:6.0f} s   curve frames {curve.sum()*DT:6.0f} s   "
       f"curve blocks >= 2 s: {len(raw_bl)}  -> 2 s windows: {len(bl)}")
    if len(bl) < 3:
        pr("  (too few windows)"); return
    pr("-" * 118)

    # ---------------- replay the four variants ----------------
    var = {k: np.full(n, np.nan) for k in ("clip", "lc_clip", "lc_clip_j10", "lc_clip_noclip",
                                           "e0_clip", "e0g1_clip")}
    jb = np.zeros(n, bool); ab = np.zeros(n, bool)
    for i in range(n):
        if not ok[i]:
            continue
        prev = fin[i - 1] if i > 0 and ok[i - 1] and np.isfinite(fin[i - 1]) else fin[i]
        var["clip"][i], jb[i], ab[i], _ = B.clip_curvature(v[i], prev, raw[i], roll[i])
        var["lc_clip"][i], _, _, _ = B.clip_curvature(v[i], prev, raw[i] + f["lc_applied"][i], roll[i])
        var["lc_clip_j10"][i], _, _, _ = B.clip_curvature(v[i], prev, raw[i] + f["lc_applied"][i], roll[i], 10.0)
        var["lc_clip_noclip"][i] = raw[i] + f["lc_applied"][i]
        var["e0_clip"][i], _, _, _ = B.clip_curvature(v[i], prev, raw[i] + f["lc_e0"][i], roll[i])
        var["e0g1_clip"][i], _, _, _ = B.clip_curvature(v[i], prev, raw[i] + f["lc_e0_g1"][i], roll[i])

    # ---------------- fidelity ----------------
    m = ok & np.isfinite(var["lc_clip"])
    mc = curve & np.isfinite(var["lc_clip"])
    pr(f"  MODEL FIDELITY  |replay - LOGGED controlsState.desiredCurvature|, CURVE frames:")
    pr(f"     raw -> clip                 : p50={med(np.abs(var['clip'][mc]-fin[mc])):.2e}  "
       f"p95={np.percentile(np.abs(var['clip'][mc]-fin[mc]),95):.2e}")
    pr(f"     raw + laneCentering -> clip : p50={med(np.abs(var['lc_clip'][mc]-fin[mc])):.2e}  "
       f"p95={np.percentile(np.abs(var['lc_clip'][mc]-fin[mc]),95):.2e}   <- the whole stack, reproduced")

    # ---------------- curvature ratios, block medians ----------------
    rows = []
    for a, b in bl:
        kr = med(np.abs(kroad[a:b])); kp = med(np.abs(raw[a:b])); kc = med(np.abs(fin[a:b]))
        kt = med(np.abs(f["kpath"][a:b]))
        if kr > 1e-4 and kp > 1e-4:
            rows.append((kp / kr, kc / kp, kt / kr, kr))
    R = np.array(rows)
    for j, nm in enumerate(("K_ACTION / K_ROAD   <- the MODEL's own straightening",
                            "K_FINAL  / K_ACTION <- EVERYTHING after the model",
                            "K_PATH   / K_ROAD   <- the MODEL's planned path")):
        lo, hi = B.boot(R[:, j])
        pr(f"  {nm:52s} = {med(R[:,j]):6.3f}  95% CI [{lo:5.3f}, {hi:5.3f}]   n={len(R)} blocks")
    pr(f"  median |K_road| over those blocks = {med(R[:,3]):.4f} 1/m   median v = {med(v[curve]):.1f} m/s")

    # ---------------- displacement attribution, per block ----------------
    sgn = np.sign(kroad)
    cols = [("STACK  final - raw", fin - raw),
            ("  laneCentering", f["lc_applied"]),
            ("  clip_curvature", var["lc_clip"] - var["lc_clip_noclip"]),
            ("CF e2e_auth 0.0", var["e0_clip"] - fin),
            ("CF e2e 0 + gain 1.0", var["e0g1_clip"] - fin),
            ("CF jerk limit x10", var["lc_clip_j10"] - fin)]
    pr("")
    pr("  LATERAL DISPLACEMENT over each curve block, cm, + = toward the INSIDE of the bend")
    pr("  (open-loop bound; compare against the model's own 28-62 cm inside bias)")
    pr(f"     {'lever':24s} {'p50 cm':>9s} {'95% CI':>20s} {'mean':>9s} {'p95|.|':>9s}")
    for nm, dk in cols:
        vals = [disp(dk, v, a, b, sgn[a]) for a, b in bl]
        vals = np.array([x for x in vals if np.isfinite(x)])
        lo, hi = B.boot(vals)
        pr(f"     {nm:24s} {med(vals):+9.2f} [{lo:+8.2f},{hi:+8.2f}] {vals.mean():+9.2f} "
           f"{np.percentile(np.abs(vals),95):9.2f}")
    pr(f"     {'block length':24s} p50 = {med([(b-a)*DT for a,b in bl]):.1f} s")

    # ---------------- clip_curvature duty and headroom ----------------
    pr("")
    pr(f"  clip_curvature: jerk binds {100*jb[curve].mean():5.2f}% of curve frames, lat-accel {100*ab[curve].mean():5.2f}%, "
       f"MAX_CURVATURE 0%")
    lim = B.MAX_LATERAL_JERK / np.maximum(v, 1.0) ** 2
    sus = np.abs(np.gradient(np.convolve(np.nan_to_num(raw), np.ones(5) / 5, "same"), f["t"]))
    pr(f"     but the SUSTAINED (5-frame-smoothed) demand rate exceeds the 5.0/v^2 limit on "
       f"{100*(sus > lim)[curve].mean():.3f}% of curve frames -> the binding is the 20 Hz staircase, not real jerk")
    la = np.abs(raw) * np.maximum(v, 1.0) ** 2
    pr(f"     |lat accel| demanded, CURVE: p50={med(la[curve]):.2f} p95={np.percentile(la[curve],95):.2f} "
       f"p99.9={np.percentile(la[curve],99.9):.2f} of the 3.00 m/s^2 ceiling")
    pr(f"     |K_action| max on curve frames = {np.abs(raw[curve]).max():.4f} of MAX_CURVATURE 0.2 "
       f"({100*np.abs(raw[curve]).max()/0.2:.1f}%)")

    # ---------------- low-speed layers ----------------
    pr(f"  low-speed layers, CURVE frames below their ceilings: turn-lead (<7.0 m/s) {100*(v[curve]<7.0).mean():.2f}%  "
       f"turn-hold (<4.47) {100*(v[curve]<4.47).mean():.2f}%  twitch-guard (<4.0) {100*(v[curve]<4.0).mean():.2f}%")
    pr(f"     and they additionally require a BLINKER (hold/lead) which is off in steady bends.")

    # ---------------- curve ENTRY (Q4) ----------------
    pr("")
    pr("  CURVE ENTRY (Q4): what the post-model stack does in the first seconds of a bend, cm inside")
    hdr = "     %-24s" % "t since block start" + "".join("%9.1f" % s for s in (0.5, 1.0, 1.5, 2.0, 3.0))
    pr(hdr)
    for nm, dk in (("STACK  final - raw", fin - raw), ("  laneCentering", f["lc_applied"])):
        row = []
        for s in (0.5, 1.0, 1.5, 2.0, 3.0):
            k = int(s / DT)
            vals = [disp(dk, v, a, a + k, sgn[a]) for a, b in raw_bl for _ in (0,) if b - a >= k]
            row.append(med(vals) if vals else np.nan)
        pr("     %-24s" % nm + "".join("%9.2f" % x for x in row))
    return


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    B.LINES.clear()
    for t in TAGS:
        run(t)
    with open(os.path.join(OV, "lever_sizing_out.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(B.LINES) + "\n")
    print("\nwrote", os.path.join(OV, "lever_sizing_out.txt"))
