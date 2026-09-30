# -*- coding: utf-8 -*-
"""accel_tracking_compare.py -- cross-route tables and figures for accel_tracking_metric.py.

Reads ONLY what accel_tracking_metric.py saved (out/metric_<tag>.json + out/tf_<tag>.npz), so the tables and the
figures can be regenerated without re-running the analysis:
    python accel_tracking_compare.py            # -> out/compare_out.txt + out/fig_*.png
Subagent `metric`, 2026-09-30.  ANALYSIS ONLY.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
VB = ["0-5", "5-10", "10-15", "15-22", "22+"]
FB = ["0.3-1", "1-3", "3-8", "0.3-8"]
FC = {"0.3-1": np.sqrt(0.3), "1-3": np.sqrt(3.0), "3-8": np.sqrt(24.0), "0.3-8": np.sqrt(2.4)}
ORDER = ["r71b_v294", "r70_v293", "r75_v293r4", "r76_v293r5", "r6c", "r39", "r6d_v292"]
# categorical slots in FIXED order (dataviz reference palette, light mode): V294 blue, V293 orange, V282 aqua, V292 violet
COL = {"V294": "#2a78d6", "V293": "#eb6834", "V282": "#1baf7a", "V292": "#4a3aa7"}
LS = {"r71b_v294": "-", "r70_v293": "-", "r75_v293r4": "--", "r76_v293r5": ":", "r6c": "-", "r39": "--", "r6d_v292": "-"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load_saved(tags=None):
    ALL = {}
    for tag in (tags or ORDER):
        jp = os.path.join(OUT, "metric_%s.json" % tag)
        if not os.path.exists(jp):
            continue
        j = json.load(open(jp))
        z = np.load(os.path.join(OUT, "tf_%s.npz" % tag))
        j["_z"] = {k: z[k] for k in z.files}
        ALL[tag] = j
    return ALL


def _get(res, key):
    """TF array from a live result (res['_TF']) or a saved one (res['_z'])."""
    if "_z" in res:
        return res["_z"].get(key)
    gname, k, part = key.split("|")
    return res["_TF"].get(gname, {}).get(k, {}).get(part)


def _f(res):
    return res["_z"]["f"] if "_z" in res else res["_f"]


def _agree(res, k):
    return res["_z"]["agree|" + k] if "_z" in res else np.asarray(res["agreement"][k])


def ii(f, x):
    return int(np.argmin(np.abs(np.asarray(f) - x)))


def runs1(mask):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def m1_band(res, lo_g, hi_g):
    f = _f(res)
    coh, gain, ph = _agree(res, "coh"), _agree(res, "gain"), _agree(res, "ph")
    ok = (coh >= 0.9) & (gain >= lo_g) & (gain <= hi_g) & (np.abs(ph) <= 15) & (f > 0.15)
    for a, b in runs1(ok):
        if f[a] <= 1.0 <= f[b - 1]:
            return (round(float(f[a]), 2), round(float(f[b - 1]), 2))
    return None


def compare(ALL, pr=print):
    tags = [t for t in ORDER if t in ALL]
    pr("")
    pr("#" * 130)
    pr("CROSS-ROUTE COMPARISON  (%s)" % ", ".join("%s=%s" % (t, ALL[t]["build"]) for t in tags))
    pr("#" * 130)
    # ---------------- M1
    pr("M1 -- where the angle-derived alpha is measurable (coh >= 0.9 with the rate-derived alpha, phase +-15 deg)")
    pr("   %-11s %-5s  %-16s %-16s %-16s  kappa(0-20 deg) kappa(>80 deg)  coh@2Hz coh@3Hz coh@4Hz coh@5Hz" %
       ("route", "EPS", "as written", "adj (kappa+-10%)", "adj2 (envelope)"))
    for t in tags:
        r = ALL[t]
        ag = r["agreement"]
        kb = ag["kappa_by_angle"]
        k_c = np.mean([k["ratio"] for k in kb if k["hi"] <= 20])
        k_l = np.mean([k["ratio"] for k in kb if k["lo"] >= 80])
        f = _f(r)
        coh = _agree(r, "coh")
        pr("   %-11s %-5s  %-16s %-16s %-16s  %.3f           %.3f           %.2f    %.2f    %.2f    %.2f"
           % (t, r["build"], ag["band_as_written"], ag["band_adjudicated"],
              m1_band(r, min(k_l, k_c) - 0.03, max(k_l, k_c) + 0.03), k_c, k_l,
              coh[ii(f, 2)], coh[ii(f, 3)], coh[ii(f, 4)], coh[ii(f, 5)]))
    # ---------------- controls
    pr("M2/M3 -- NULL and POSITIVE controls over every (band x speed) row")
    for t in tags:
        r = ALL[t]
        nmax, fails1, fails2, n = 0.0, [], [], 0
        for bn, rows in r["band_scores"].items():
            for vn, row in rows.items():
                n += 1
                nmax = max(nmax, row["null_shuffle"]["R2"], row["null_shuffle"]["gp"]["R2"], row["null_reverse"]["R2"],
                           row["null_reverse"]["gp"]["R2"])
                for key, fl in (("posctl", fails1), ("posctl2", fails2)):
                    pc = row[key]
                    okG = abs(pc["G"] / pc["G_true"] - 1) <= 0.05
                    okL = abs(pc["lag_ms"] - pc["tau_true_ms"]) <= 10
                    okR = abs(pc["R2"] - pc["R2_ceiling"]) <= 0.05
                    if not (okG and okL and okR):
                        fl.append("%s/%s(G%+.0f%% lag%+.0f R2%+.2f)" % (bn, vn, 100 * (pc["G"] / pc["G_true"] - 1),
                                                                       pc["lag_ms"] - pc["tau_true_ms"],
                                                                       pc["R2"] - pc["R2_ceiling"]))
        pr("   %-11s rows %2d | max null R2 %.3f (%s) | PC1 fails %d %s | PC2 fails %d %s"
           % (t, n, nmax, "PASS" if nmax <= 0.02 else ("WARN" if nmax <= 0.05 else "FAIL"), len(fails1),
              " ".join(fails1[:4]), len(fails2), " ".join(fails2[:4])))
    # ---------------- literal metric
    for bn in FB:
        pr("THE LITERAL METRIC, band %s Hz: gain-phase fit R2 (|G| deg/s^2 per count, phase deg; + = alpha LEADS) | lag-scan R2 @lag" % bn)
        for t in tags:
            cells = []
            for vn in ["all"] + VB:
                row = ALL[t]["band_scores"].get(bn, {}).get(vn)
                if row is None:
                    cells.append("%-26s" % (vn + ": --"))
                    continue
                a = row["u>alpha_th"]
                cells.append("%s:%s%.2f(%.2f,%+.0f)|%.2f@%+.0f" % (vn, "VOID " if row.get("void") else "", a["gp"]["R2"],
                                                                  a["gp"]["gain"], a["gp"]["phase_deg"], a["R2"], a["lag_ms"]))
            pr("   %-11s %s" % (t, "  ".join(cells)))
    # ---------------- closed loop
    pr("CLOSED-LOOP DIAGNOSTIC -- is H1 the inverse of the fork's angle feedback?  u_B ~ -K theta_B(t-d) implies H1 = (2 pi fc)^2/K")
    for bn in ("1-3", "3-8"):
        for t in tags:
            cells = []
            for vn in ["all"] + VB:
                d_ = ALL[t]["decomposition"].get(bn, {}).get(vn)
                row = ALL[t]["band_scores"].get(bn, {}).get(vn)
                if not d_ or not row or "theta" not in d_:
                    continue
                cells.append("%s: K %.0f@%+dms R2 %.2f -> %.2f vs GP |G| %.2f" % (
                    vn, -d_["theta"]["slope"], d_["theta"]["lag_ms"], d_["theta"]["R2"], d_["implied_H_if_feedback"],
                    row["u>alpha_th"]["gp"]["gain"]))
            pr("   %s %-11s %s" % (bn, t, " | ".join(cells)))
    pr("COMMAND DECOMPOSITION (all speeds): R2 of u_B on the fork P term / desiredLateralAccel / wheel angle, best lag")
    for t in tags:
        cells = []
        for bn in FB[:3]:
            d_ = ALL[t]["decomposition"].get(bn, {}).get("all", {})
            cells.append("%s: P %.2f la_des %.2f theta %.2f" % (bn, d_.get("cs_p", {}).get("R2", np.nan),
                                                              d_.get("cs_la_des", {}).get("R2", np.nan),
                                                              d_.get("theta", {}).get("R2", np.nan)))
        pr("   %-11s %s" % (t, " | ".join(cells)))
    # ---------------- shape vs the ideal alpha = G u (slope 0, phase 0)
    pr("SHAPE vs the ideal alpha = G*cmd (|H| ~ f^0, phase 0): fitted exponent n in |H1| ~ f^n and median phase, per range")
    for vn in ["all"] + VB:
        cells = []
        for t in tags:
            r = ALL[t]
            f = _f(r)
            g = "all" if vn == "all" else "v" + vn
            H = _get(r, "%s|u>alpha_w|H" % g)
            if H is None:
                continue
            out = []
            for lo, hi in ((0.35, 1.0), (1.4, 4.0), (4.0, 8.0)):
                m = (f >= lo) & (f <= hi)
                n = np.polyfit(np.log(f[m]), np.log(np.abs(H[m])), 1)[0]
                out.append("%.1f-%.0f Hz n %.1f ph %+.0f" % (lo, hi, n, np.degrees(np.median(np.angle(H[m])))))
            cells.append("%s: %s" % (t, ", ".join(out)))
        pr("   %-5s %s" % (vn, " | ".join(cells)))
    # ---------------- H1 and IV at fixed frequencies
    pr("cmd -> alpha_w  H1 |H| and phase, and the IV (actuator branch; only where coh(la_des,u) >= 0.3), per speed band")
    for vn in ["all"] + VB:
        for t in tags:
            r = ALL[t]
            f = _f(r)
            g = "all" if vn == "all" else "v" + vn
            H = _get(r, "%s|u>alpha_w|H" % g)
            if H is None:
                continue
            Hiv = _get(r, "%s|iv_u>alpha_w|H" % g)
            ci = _get(r, "%s|iv_u>alpha_w|coh_ri" % g)
            cells = []
            for x in (0.4, 0.6, 1.0, 2.0, 3.0, 5.0):
                i = ii(f, x)
                s = "%.1f:%.2f%+.0f" % (f[i], abs(H[i]), np.degrees(np.angle(H[i])))
                if Hiv is not None and ci[i] >= 0.3:
                    s += "/IV %.2f%+.0f" % (abs(Hiv[i]), np.degrees(np.angle(Hiv[i])))
                cells.append("%-24s" % s)
            pr("   %-5s %-11s %s" % (vn, t, " ".join(cells)))
    # ---------------- M4
    pr("M4 -- closed-loop bias: at every bin 0.3-8 Hz with coh(la_des,u) >= 0.3, is the IV |H| inside the H1 CI x/÷1.25?")
    for t in tags:
        r = ALL[t]
        f = _f(r)
        cells = []
        for g in ["all"] + ["v" + v for v in VB]:
            Hiv = _get(r, "%s|iv_u>alpha_w|H" % g)
            if Hiv is None:
                continue
            ci = _get(r, "%s|iv_u>alpha_w|coh_ri" % g)
            lo, hi = _get(r, "%s|u>alpha_w|lo" % g), _get(r, "%s|u>alpha_w|hi" % g)
            m = (f >= 0.3) & (f <= 8) & (ci >= 0.3)
            ok = (np.abs(Hiv) >= lo / 1.25) & (np.abs(Hiv) <= hi * 1.25)
            nb, nlow = int((m & ~ok).sum()), int((m & ~ok & (f < 1)).sum())
            cells.append("%s %d/%d biased (%d below 1 Hz)" % (g, nb, int(m.sum()), nlow))
        pr("   %-11s %s" % (t, " | ".join(cells)))
    # ---------------- the firmware's own footprint
    pr("TRIM FOOTPRINT -- delivered torque (427 tap) = FF(cmd) + K*alpha_w, per band (hands-off): |K| counts per deg/s^2 "
       "[CI] phase; design = -0.21 x (2.03 Hz pole)(5.05 Hz pole) at the band centre; rms of the FF part vs the alpha part")
    for t in tags:
        cells = []
        for bn in FB[:3]:
            row = ALL[t]["band_scores"].get(bn, {}).get("all")
            if not row or "trim" not in row:
                continue
            tr = row["trim"]
            cells.append("%s: |K| %.3f[%.3f,%.3f]%+.0f (design %.3f%+.0f) FF %.1f alpha %.1f T %.1f" % (
                bn, tr["K_mag"], tr["K_ci"][0], tr["K_ci"][1], tr["K_phase_deg"], tr["design"]["mag"],
                tr["design"]["phase_deg"], tr["rms_ff"], tr["rms_trim"], tr["rms_T"]))
        pr("   %-11s %s" % (t, " | ".join(cells)))
    # ---------------- joint regression
    pr("SPRING LEAK -- share of command variance by term (broadband joint regression, hands-off)")
    for t in tags:
        cells = []
        for vn in ["all"] + VB:
            J = ALL[t]["joint"].get(vn)
            if J:
                s = J["share"]
                cells.append("%s: Ja %.3f bw %.3f kth %.2f F %.3f R2 %.2f k %.0f" % (vn, s["J"], s["b"], s["k"], s["F"], J["R2"],
                                                                                 J["coef"]["k"]))
        pr("   %-11s %s" % (t, " | ".join(cells)))
    # ---------------- nonlinearity
    pr("STATIC NONLINEARITY (0.3-8 Hz, all speeds): slopes deg/s^2 per count; wheel-stuck share (|omega|<2) by |u_B|")
    for t in tags:
        N = ALL[t]["nonlinearity"].get("all")
        if not N:
            continue
        s = N["slopes"]
        pr("   %-11s left %.3f right %.3f | |u|<100 %.3f 100-300 %.3f >=300 %.3f | stuck %s | raw R2 %.3f"
           % (t, s["pos"], s["neg"], s["small"], s["mid"], s["large"],
              " ".join("%d-%d:%.2f" % (x["lo"], x["hi"], x["frac"]) for x in N["stuck"]), N["raw_r2"]))
    # ---------------- V294 vs V293 on the ACTUATOR branch (IV), at bins where both have coh(la_des,u) >= 0.3
    if "r71b_v294" in ALL:
        v3 = [t for t in tags if ALL[t]["build"] == "V293"]
        a = ALL["r71b_v294"]
        f = _f(a)
        rows = []
        for g in ["all"] + ["v" + v for v in VB]:
            H, lo, hi, c = (_get(a, "%s|iv_u>alpha_w|%s" % (g, k)) for k in ("H", "lo", "hi", "coh_ri"))
            if H is None:
                continue
            for t in v3:
                b = ALL[t]
                Hb, lob, hib, cb = (_get(b, "%s|iv_u>alpha_w|%s" % (g, k)) for k in ("H", "lo", "hi", "coh_ri"))
                if Hb is None:
                    continue
                for i in np.flatnonzero((f >= 0.3) & (f <= 8) & (c >= 0.3) & (cb >= 0.3)):
                    cls = "lower" if hi[i] < lob[i] else ("higher" if lo[i] > hib[i] else "overlap")
                    rows.append((g, t, float(f[i]), float(abs(H[i]) / abs(Hb[i])), cls))
        pr("V294 vs V293 on the ACTUATOR branch (IV |alpha_w/cmd|), every bin where both routes have coh(la_des,u) >= 0.3:")
        for lab, lo_, hi_ in (("0.3-1 Hz", 0.3, 1.0), ("1-3 Hz", 1.0, 3.0), ("3-8 Hz", 3.0, 8.01)):
            sub = [r for r in rows if lo_ <= r[2] < hi_]
            if not sub:
                continue
            rat = np.array([r[3] for r in sub])
            pr("   %-8s n %3d bin-pairs | median V294/V293 %.2f (IQR %.2f-%.2f) | CI-separated: lower %d, higher %d, overlap %d"
               % (lab, len(sub), np.median(rat), np.percentile(rat, 25), np.percentile(rat, 75),
                  sum(r[4] == "lower" for r in sub), sum(r[4] == "higher" for r in sub), sum(r[4] == "overlap" for r in sub)))
        sep = [r for r in rows if r[4] != "overlap"]
        pr("   separated bins: " + "; ".join("%s %s %.2f Hz x%.2f %s" % r for r in sep))
    # ---------------- V294 vs V293
    if "r71b_v294" in ALL:
        v3 = [t for t in tags if ALL[t]["build"] == "V293"]
        pr("V294 (r71b) vs the V293 routes (%s): literal-metric GP R2 / |G|, per band x speed; '*' = V294 outside the V293 range"
           % ", ".join(v3))
        for bn in FB:
            cells = []
            for vn in ["all"] + VB:
                a = ALL["r71b_v294"]["band_scores"].get(bn, {}).get(vn)
                bs = [ALL[t]["band_scores"].get(bn, {}).get(vn) for t in v3]
                bs = [b for b in bs if b and not b.get("void")]
                if not a or not bs or a.get("void"):
                    continue
                r2s = [b["u>alpha_th"]["gp"]["R2"] for b in bs]
                gs = [b["u>alpha_th"]["gp"]["gain"] for b in bs]
                ra, ga = a["u>alpha_th"]["gp"]["R2"], a["u>alpha_th"]["gp"]["gain"]
                cells.append("%s: R2 %.2f%s [%.2f..%.2f] |G| %.2f%s [%.2f..%.2f]" % (
                    vn, ra, "*" if (ra < min(r2s) or ra > max(r2s)) else " ", min(r2s), max(r2s),
                    ga, "*" if (ga < min(gs) or ga > max(gs)) else " ", min(gs), max(gs)))
            pr("   %-6s %s" % (bn, " | ".join(cells)))


# ======================================================================================================================
# FIGURES
# ======================================================================================================================
def _style(ax):
    ax.set_facecolor(SURF)
    ax.grid(True, color=GRID, lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=8)


def figures(ALL, outdir=OUT):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sys.path.insert(0, HERE)
    import accel_tracking_metric as M
    tags = [t for t in ORDER if t in ALL]
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelcolor": INK2, "text.color": INK})
    # ---- FIG 1: signal engineering (r71b) + kappa(angle) on every route
    r = ALL.get("r71b_v294") or ALL[tags[0]]
    f = _f(r)
    fig, axs = plt.subplots(2, 2, figsize=(12, 8), facecolor=SURF)
    ax = axs[0, 0]
    ff = np.linspace(0.05, 30, 600)
    ax.plot(ff, M.sg_response(M.SG_TH[0], M.SG_TH[1], 2, ff)[0], color=COL["V294"], lw=2, label="alpha_th: SG(21,5) d2/dt2 of 0x14A angle")
    ax.plot(ff, M.sg_response(M.SG_W[0], M.SG_W[1], 1, ff)[0], color=COL["V293"], lw=2, label="alpha_w: SG(9,3) d/dt of 0x18F rate")
    ax.axhline(1, color=INK2, lw=1, ls="--")
    ax.set_xscale("log"); ax.set_ylim(-0.2, 1.1); ax.set_xlim(0.1, 30)
    ax.set_title("differentiator response / ideal derivative (passband)"); ax.set_xlabel("Hz"); ax.legend(fontsize=7, frameon=False)
    _style(ax)
    ax = axs[0, 1]
    for t in tags:
        rr = ALL[t]
        fx = _f(rr)
        ax.plot(fx, _agree(rr, "coh"), color=COL[rr["group"]], ls=LS[t], lw=1.6, label="%s (%s)" % (t, rr["build"]))
    ax.axhline(0.9, color=INK2, lw=1, ls="--")
    ax.set_xscale("log"); ax.set_xlim(0.2, 20); ax.set_ylim(0, 1.02)
    ax.set_title("coherence alpha_th vs alpha_w, hands-off engaged (M1: >= 0.9)"); ax.set_xlabel("Hz"); ax.legend(fontsize=7, frameon=False)
    _style(ax)
    ax = axs[1, 0]
    for t in tags:
        rr = ALL[t]
        kb = rr["agreement"]["kappa_by_angle"]
        x = [np.sqrt(max(k["lo"], 1) * k["hi"]) for k in kb]
        ax.plot(x, [k["ratio"] for k in kb], color=COL[rr["group"]], ls=LS[t], lw=1.6, marker="o", ms=4, label=t)
    ax.set_xscale("log"); ax.set_xlabel("|steering-wheel angle| deg"); ax.set_ylabel("d(angle) / integral(0x18F rate)")
    ax.set_title("kappa: wheel angle moves 16 % more than the motor-side rate near centre (every build)")
    ax.legend(fontsize=7, frameon=False); _style(ax)
    ax = axs[1, 1]
    ax.loglog(f, _agree(r, "S_th"), color=COL["V294"], lw=1.6, label="PSD alpha_th (r71b)")
    ax.loglog(f, _agree(r, "S_w"), color=COL["V293"], lw=1.6, label="PSD alpha_w (r71b)")
    ax.loglog(f, _agree(r, "N_th"), color=COL["V294"], lw=1.2, ls="--", label="alpha_th incoherent with alpha_w (noise bound)")
    ax.loglog(f, _agree(r, "N_th_model"), color=INK2, lw=1, ls=":", label="0.1 deg quantiser, white model")
    ax.loglog(f, _agree(r, "N_w_model"), color=INK2, lw=1, ls="-.", label="0.125 deg/s quantiser, white model")
    ax.set_xlim(0.2, 30); ax.set_ylim(1e0, 1e9); ax.set_xlabel("Hz"); ax.set_title("noise floors (window power units)")
    ax.legend(fontsize=7, frameon=False); _style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig1_signal_engineering.png"), dpi=130, facecolor=SURF)
    plt.close(fig)
    # ---- FIG 2: cmd -> alpha Bode by speed band, H1 + IV + implied-feedback curve + ideal
    fig, axs = plt.subplots(3, 5, figsize=(20, 10.5), facecolor=SURF, sharex=True)
    for j, vn in enumerate(VB):
        g = "v" + vn
        for t in tags:
            rr = ALL[t]
            H = _get(rr, "%s|u>alpha_w|H" % g)
            if H is None:
                continue
            fx = _f(rr)
            m = (fx >= 0.3) & (fx <= 12)
            c = COL[rr["group"]]
            axs[0, j].loglog(fx[m], np.abs(H[m]), color=c, ls=LS[t], lw=1.5, label=t)
            axs[1, j].semilogx(fx[m], np.degrees(np.angle(H[m])), color=c, ls=LS[t], lw=1.5)
            coh = _get(rr, "%s|u>alpha_w|coh" % g)
            axs[2, j].semilogx(fx[m], coh[m], color=c, ls=LS[t], lw=1.5)
            Hiv = _get(rr, "%s|iv_u>alpha_w|H" % g)
            ci = _get(rr, "%s|iv_u>alpha_w|coh_ri" % g)
            if Hiv is not None:
                k = m & (ci >= 0.3)
                axs[0, j].scatter(fx[k], np.abs(Hiv[k]), s=18, color=c, edgecolor=SURF, zorder=5)
                axs[1, j].scatter(fx[k], np.degrees(np.angle(Hiv[k])), s=18, color=c, edgecolor=SURF, zorder=5)
        rr = ALL.get("r71b_v294")
        if rr:
            d_ = rr["decomposition"].get("1-3", {}).get(vn, {})
            if "theta" in d_:
                K = abs(d_["theta"]["slope"])
                fx = np.linspace(0.3, 12, 200)
                axs[0, j].loglog(fx, (2 * np.pi * fx) ** 2 / K, color=INK2, lw=1, ls=":", label="(2 pi f)^2/K: fork reacting to the wheel (r71b)")
            row = rr["band_scores"].get("1-3", {}).get(vn)
            if row:
                axs[0, j].axhline(row["u>alpha_th"]["gp"]["gain"], color=INK2, lw=1, ls="--", label="ideal alpha = G u (flat, 0 deg)")
                axs[1, j].axhline(0, color=INK2, lw=1, ls="--")
        pn = rr["band_scores"]["0.3-8"].get("all") if rr else None
        axs[0, j].set_title("%s m/s" % vn)
        axs[2, j].axhline(0.3, color=GRID, lw=1)
        axs[2, j].set_xlabel("Hz")
        axs[1, j].set_ylim(-190, 190)
        axs[2, j].set_ylim(0, 1)
        for i in range(3):
            _style(axs[i, j])
    axs[0, 0].set_ylabel("|alpha/cmd| deg/s^2 per 0xE4 count")
    axs[1, 0].set_ylabel("phase deg (+ = alpha leads)")
    axs[2, 0].set_ylabel("coherence")
    axs[0, 0].legend(fontsize=6.5, frameon=False, loc="upper left")
    fig.suptitle("cmd -> wheel angular acceleration (hands-off, laterally engaged). Lines: H1 (the literal metric). Dots: IV via "
                 "desiredLateralAccel (the actuator branch), where coh >= 0.3.", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig2_cmd_to_alpha_bode.png"), dpi=120, facecolor=SURF)
    plt.close(fig)
    # ---- FIG 3: band scores (GP R2) small multiples: one panel per frequency band, x = speed band, one line per route
    fig, axs = plt.subplots(1, 4, figsize=(18, 4.2), facecolor=SURF, sharey=True)
    for j, bn in enumerate(FB):
        ax = axs[j]
        for t in tags:
            rr = ALL[t]
            y = [np.nan if rr["band_scores"].get(bn, {}).get(vn, {}).get("void", True) else
                 rr["band_scores"][bn][vn]["u>alpha_th"]["gp"]["R2"] for vn in VB]
            lo = [rr["band_scores"].get(bn, {}).get(vn, {}).get("u>alpha_th", {}).get("gp", {}).get("R2_ci", [np.nan, np.nan])[0] for vn in VB]
            hi = [rr["band_scores"].get(bn, {}).get(vn, {}).get("u>alpha_th", {}).get("gp", {}).get("R2_ci", [np.nan, np.nan])[1] for vn in VB]
            x = np.arange(len(VB)) + (ORDER.index(t) - 3) * 0.06
            ax.errorbar(x, y, yerr=[np.array(y) - np.array(lo), np.array(hi) - np.array(y)], color=COL[rr["group"]],
                        ls=LS[t], lw=1.5, marker="o", ms=4, capsize=2, label=t)
        ax.set_xticks(range(len(VB))); ax.set_xticklabels(VB); ax.set_xlabel("speed band m/s")
        ax.set_title("%s Hz" % bn); ax.set_ylim(0, 1); _style(ax)
    axs[0].set_ylabel("R2 of alpha explained by the command (gain-phase fit)")
    axs[0].legend(fontsize=7, frameon=False)
    nmax = max(row.get("null_max", 0) for t in tags for rows in ALL[t]["band_scores"].values() for row in rows.values()
               if not row.get("void"))
    fig.suptitle("The literal tracking score, hands-off; 95 %% block-bootstrap CIs; VOID rows (< 30 s or null > 0.05) omitted.  "
                 "Largest null (shuffled / reversed command) on a plotted row: R2 %.3f" % nmax, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig3_band_scores.png"), dpi=130, facecolor=SURF)
    plt.close(fig)
    # ---- FIG 4: static nonlinearity + stuck share
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), facecolor=SURF)
    for t in tags:
        rr = ALL[t]
        N = rr["nonlinearity"].get("all")
        if not N:
            continue
        x = [b["u_med"] for b in N["bins"]]
        axs[0].plot(x, [b["a_med"] for b in N["bins"]], color=COL[rr["group"]], ls=LS[t], lw=1.5, marker="o", ms=3, label=t)
        axs[1].plot([np.sqrt(max(s["lo"], 5) * min(s["hi"], 600)) for s in N["stuck"]], [s["frac"] for s in N["stuck"]],
                    color=COL[rr["group"]], ls=LS[t], lw=1.5, marker="o", ms=3, label=t)
    axs[0].set_xscale("symlog", linthresh=50); axs[0].set_yscale("symlog", linthresh=20)
    axs[0].set_xlabel("band-passed command u_B (0.3-8 Hz, counts, + = left)"); axs[0].set_ylabel("median alpha_B deg/s^2")
    axs[0].set_title("binned alpha vs command at the best lag (all speeds, hands-off)")
    axs[1].set_xscale("log"); axs[1].set_xlabel("|u_B| counts"); axs[1].set_ylabel("share of frames with |omega| < 2 deg/s")
    axs[1].set_title("wheel at rest vs dynamic command amplitude"); axs[1].set_ylim(0, 1)
    for a in axs:
        _style(a)
    axs[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig4_nonlinearity.png"), dpi=130, facecolor=SURF)
    plt.close(fig)
    # ---- FIG 5: spring leak: share of command variance per term, per speed band (small multiples per route)
    fig, axs = plt.subplots(1, len(tags), figsize=(3.0 * max(len(tags), 2), 4.2), facecolor=SURF, sharey=True, squeeze=False)
    axs = axs[0]
    tc = {"J": "#2a78d6", "b": "#eb6834", "k": "#1baf7a", "F": "#eda100"}
    names = {"J": "J*alpha (inertia)", "b": "b*omega (damping)", "k": "k*theta (spring/hold)", "F": "F*sign(omega) (friction)"}
    for j, t in enumerate(tags):
        ax = axs[j]
        rr = ALL[t]
        for q, term in enumerate(("J", "b", "k", "F")):
            y = [rr["joint"].get(vn, {}).get("unique", {}).get(term, np.nan) for vn in VB]
            ax.bar(np.arange(len(VB)) + (q - 1.5) * 0.2, y, width=0.18, color=tc[term], label=names[term] if j == 0 else None)
        ax.set_xticks(range(len(VB))); ax.set_xticklabels(VB, fontsize=7); ax.set_title("%s (%s)" % (t, rr["build"]), fontsize=9)
        _style(ax)
    axs[0].set_ylabel("unique share of command variance (drop-one R2)")
    axs[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Where the command goes: u = J alpha + b omega + k theta + F sign(omega) + c (hands-off, 8 Hz LP)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig5_spring_leak.png"), dpi=130, facecolor=SURF)
    plt.close(fig)
    # ---- FIG 6: command decomposition: R2 of u_B on the fork P term, the wheel angle, desiredLateralAccel
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), facecolor=SURF, sharey=True)
    for j, bn in enumerate(FB[:3]):
        ax = axs[j]
        for q, (c, lab, col) in enumerate((("cs_p", "fork P term", "#2a78d6"), ("theta", "wheel angle", "#eb6834"),
                                            ("cs_la_des", "desiredLateralAccel", "#1baf7a"))):
            y = [ALL[t]["decomposition"].get(bn, {}).get("all", {}).get(c, {}).get("R2", np.nan) for t in tags]
            ax.bar(np.arange(len(tags)) + (q - 1) * 0.27, y, width=0.25, color=col, label=lab if j == 0 else None)
        ax.set_xticks(range(len(tags))); ax.set_xticklabels(tags, rotation=30, fontsize=7); ax.set_title("%s Hz" % bn)
        ax.set_ylim(0, 1); _style(ax)
    axs[0].set_ylabel("R2 of the band-passed command on x(t - lag)")
    axs[0].legend(fontsize=7, frameon=False)
    fig.suptitle("What the command IS in each band (hands-off): mostly the fork's P term reacting to the wheel", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig6_command_decomposition.png"), dpi=130, facecolor=SURF)
    plt.close(fig)
    # ---- FIG 7: the firmware's footprint on the metric axis: K = d(delivered torque)/d(alpha_w), per band and speed
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.3), facecolor=SURF)
    for t in tags:
        rr = ALL[t]
        xs, ks, ps, lo, hi = [], [], [], [], []
        for q, bn in enumerate(FB[:3]):
            for w, vn in enumerate(["all"] + VB):
                row = rr["band_scores"].get(bn, {}).get(vn)
                if not row or "trim" not in row or row.get("void"):
                    continue
                xs.append(q * 7 + w + (ORDER.index(t) - 3) * 0.08)
                ks.append(row["trim"]["K_mag"]); ps.append(row["trim"]["K_phase_deg"])
                lo.append(row["trim"]["K_ci"][0]); hi.append(row["trim"]["K_ci"][1])
        ks, lo, hi = np.array(ks), np.array(lo), np.array(hi)
        axs[0].errorbar(xs, ks, yerr=[np.maximum(ks - lo, 0), np.maximum(hi - ks, 0)], color=COL[rr["group"]], ls="none",
                        marker="o", ms=4, capsize=2, label="%s (%s)" % (t, rr["build"]))
        axs[1].plot(xs, ps, color=COL[rr["group"]], ls="none", marker="o", ms=4)
    for q, bn in enumerate(FB[:3]):
        fc = FC[bn]
        L = 1.0 / (1 + 1j * fc / 2.033) / (1 + 1j * fc / 5.05)
        axs[0].hlines(0.21 * abs(L), q * 7 - 0.4, q * 7 + 5.4, color=INK2, ls="--", lw=1.2, label="V294 design" if q == 0 else None)
        axs[1].hlines(np.degrees(np.angle(-0.21 * L)), q * 7 - 0.4, q * 7 + 5.4, color=INK2, ls="--", lw=1.2)
    for a in axs:
        a.set_xticks([q * 7 + w for q in range(3) for w in range(6)])
        a.set_xticklabels([(bn + " Hz\n" if w == 0 else "\n") + v for bn in FB[:3] for w, v in enumerate(["all"] + VB)],
                          fontsize=6)
        _style(a)
    axs[0].set_ylabel("|K| tap counts per deg/s^2 of wheel accel"); axs[0].set_title("magnitude of the acceleration term in the delivered torque")
    axs[1].set_ylabel("phase of K, deg"); axs[1].set_ylim(-190, 190); axs[1].set_title("phase (design: opposes acceleration through two lags)")
    axs[0].legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "fig7_trim_footprint.png"), dpi=130, facecolor=SURF)
    plt.close(fig)


if __name__ == "__main__":
    ALL = load_saved()
    buf = []

    def p(s=""):
        print(s)
        buf.append(s)
    compare(ALL, p)
    figures(ALL)
    open(os.path.join(OUT, "compare_out.txt"), "w", encoding="utf-8").write("\n".join(buf) + "\n")
