#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/lanechange_r34.py -- r34 (V280 rev 2 firmware, NEW StarPilot lateral tune) read with the SAME
detector, thresholds and window definition as LANECHANGE-V278R3-2026-09-02.md (r32/r33, old tune).  Subagent lanechange34,
2026-09-03.  Nothing here moves a threshold: every statistic is lanechange_osc / lanechange_windows / lanechange_chain code
called on the r34 caches (`_scratch/_ha_<route>.npz`, `_scratch/_lc_r34.npz`; backcalc npz in studies/optune/_scratch).

  1. BUILD ATTRIBUTION from the CAN-427 tap: chain T_sim (lanechange_chain.chain_1k) under the V280 rev 2 line map / 46080,
     rev 3 (x2 / 15360) and stock (x1 / 7680) vs T_meas on engaged idx>0 frames (corr, LS slope, sign agreement); hands-light
     idx>=200 rate p90 and the push-vs-brake fraction of T above 60 deg/s.  Same numbers on r32/r33 as the reference.
  2. WHAT THE CONTROLLER USED (backcalc_laf_friction.live_values on the backcalc npz): liveTorqueParameters *Filtered,
     -(p+i+d+f)/output (= LAF), p/error (= kp), friction*LAF from the f regression, carParams.lateralTuning.torque, the
     vehicle-model lat-accel per (angle*v^2) (the 16.1-vs-14.0 steer-ratio change).
  3. THE LANE-CHANGE CENSUS exactly as lanechange_windows.py: laneChangeState windows (+2 s settle) with speed, ring, f_dom,
     rate amplitude, 4-8 Hz power, T amplitude, damping fraction, cmd coherence; the automatic OSC/EXC detector of
     lanechange_osc.py on r34 (LANECHANGE-r34.txt, merged into lanechange_events.json); the speed x |cmd| strata table vs
     r32/r33/r22; the plain-lane-keeping OSC episodes outside any window.
  4. TUNE SIDE EFFECTS on r32/r33/r34 (backcalc grids, engaged & v>=20 & hands off): torqueState.error RMS, des-act RMS,
     desiredCurvature-curvature RMS, steering-angle 0.1-0.5 / 0.5-2 Hz band power, torqueState.i p50/p90 and drift, the
     friction-term saturation fraction |error + 0.22*desiredLateralJerk| > 0.30, |output| and 0xE4 |cmd| percentiles.

Run:  python lanechange_r34.py    (writes LANECHANGE-r34.txt, LANECHANGE-r34-windows.txt, lanechange_r34.json beside itself)
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "optune"))
import highangle_stutter as H  # noqa: E402
import lanechange_osc as L  # noqa: E402
import lanechange_windows as W  # noqa: E402
import lanechange_chain as LC  # noqa: E402
import backcalc_laf_friction as B  # noqa: E402
import lanechange_loop as LL  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
NEW, OLD = "r34", ("r32", "r33")
LINES = []


def pr(s=""):
    print(s); LINES.append(s)


# ----------------------------------------------------------------------------------------------------------------------
# 1. build attribution from the tap
# ----------------------------------------------------------------------------------------------------------------------
def attribution(tag, G):
    C = L.chain(G, L.CHAIN_CFG[tag])
    sgn = np.sign(C["sp"]); e = G["eng"] & (C["idx"] > 0)
    out = {}
    for name, K, clamp, mapY in (("V280r2 line/46080", 6.0, 46080, L.MAP_Y_V280R2), ("rev3 x2/15360", 2.0, 15360, None), ("stock x1/7680", 1.0, 7680, None)):
        R = LC.chain_1k(G["rate"], G["cmd"], G["tq"], G["eng"], K, clamp, mapY)
        Ts, Tm = R["T"], G["T"]
        ok = e & (np.abs(Tm) > 0)
        corr = float(np.corrcoef(Ts[ok], Tm[ok])[0, 1]); slope = float(np.sum(Ts[ok] * Tm[ok]) / max(np.sum(Ts[ok] ** 2), 1))
        agree = float(np.mean(np.sign(Ts[ok]) == np.sign(Tm[ok])))
        out[name] = dict(corr=corr, slope=slope, agree=agree, n=int(ok.sum()))
    hl = G["eng"] & (np.abs(G["tq"]) < 1000) & (C["idx"] >= 200)
    w = np.abs(G["rate"]) / 8
    out["idx200_secs"] = float(hl.sum() / FS)
    out["idx200_rate_p90"] = float(np.percentile(w[hl], 90)) if hl.sum() > 20 else np.nan
    fast = hl & (w > 60) & (np.sign(-G["rate"]) == sgn) & (G["T"] != 0)
    out["push_frac_gt60"] = float(np.mean(np.sign(G["T"][fast]) == sgn[fast])) if fast.sum() >= 20 else np.nan
    out["n_gt60"] = int(fast.sum())
    fld = G["fld"][G["eng"]] & 0x1FF
    out["T_sat"] = float(np.mean(fld >= H.T_SAT_FIELD)); out["field_max"] = int(fld.max())
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 2. what the controller used
# ----------------------------------------------------------------------------------------------------------------------
def controller_used(tag):
    D = B.load(tag); g = B.grid(D)
    o = B.live_values(g)
    o["carParams"] = D["cp"]
    a = (g["active"] > 0.5) & (g["v"] > 15) & (np.abs(g["ang"]) > 2) & (np.abs(g["ang"]) < 30) & ~np.isnan(g["actualLateralAccel"])
    ratio = g["actualLateralAccel"][a] / (np.radians(g["ang"][a]) * g["v"][a] ** 2)
    o["vm_lat_per_ang_v2"] = float(np.nanmedian(ratio)); o["vm_n"] = int(a.sum())
    lp = g["ltpv_latAccelFactorFiltered"]
    o["liveSR_p50"] = float(np.nanmedian(D["lpar_sr"])) if "lpar_sr" in D else np.nan
    o["lag_p50"] = float(np.nanmedian(g["lag"][g["eng"] > 0.5]))
    return o, g


# ----------------------------------------------------------------------------------------------------------------------
# 3. the automatic detector, per route (lanechange_osc.main body, unchanged thresholds)
# ----------------------------------------------------------------------------------------------------------------------
def route_events(tag, G):
    lines = []
    p = lambda s="": lines.append(s)  # noqa: E731
    build = L.ROUTES[tag][1]
    p("=" * 130)
    p("ROUTE %s  %s  (%s)   engaged %.0f s   HIGHWAY (engaged, v>=%.0f, |ang|<%.0f) %.0f s" %
      (tag, L.ROUTES[tag][0], build, G["eng"].sum() / FS, L.V_HW, L.ANG_HW, G["hw"].sum() / FS))
    hw = G["hw"]
    p("  highway v p50/max %.1f/%.1f   |cmd| p50/p90/p99 %s   idx p50/p90/p99 %s   |tq_raw| p50/p90 %s" % (
        np.median(G["v"][hw]), G["v"][hw].max(), np.percentile(np.abs(G["cmd"][hw]), [50, 90, 99]).round(0),
        np.percentile(G["idx"][hw], [50, 90, 99]).round(0), np.percentile(np.abs(G["tq"][hw]), [50, 90]).round(0)))
    p("  2-12 Hz rate envelope on highway: p50/p95/p99/max %s wire (/8 = deg/s)   duty>%.0f: %.3f" % (
        np.percentile(G["env"][hw], [50, 95, 99, 100]).round(0), L.ENV_THR, np.mean(G["env"][hw] > L.ENV_THR)))
    P412, _ = H.band_power(G["rate"], hw, nperseg=256)
    p("  highway rate spectrum: 2-4 %.0f  4-8 %.0f  8-15 %.0f (Welch power, wire^2)" % (P412["2-4"], P412["4-8"], P412["8-15"]))
    C = L.chain(G, L.CHAIN_CFG[tag])
    cs = L.chain_stats(C, hw)
    p("  CHAIN [%s] on highway frames:" % L.CHAIN_CFG[tag]["name"])
    p("    P-rail duty %.4f  fb-clamp duty %.4f  |E| p50/p90/max %.0f/%.0f/%.0f  |P| p50/p90 %.0f/%.0f  |fb| p50/p90 %.0f/%.0f  32|sp| p50/p90 %.0f/%.0f  ref p50/p90 %.1f/%.1f deg/s  Kp p50 %.0f (window %.1f deg/s)  fb-dominant %.2f  |E| past P window %.4f" % (
        cs["p_rail"], cs["fb_clamped"], cs["absE_p50"], cs["absE_p90"], cs["absE_max"], cs["absP_p50"], cs["absP_p90"],
        cs["fb_p50"], cs["fb_p90"], cs["sp32_p50"], cs["sp32_p90"], cs["ref_p50"], cs["ref_p90"], cs["kp_p50"], cs["window_p50"], cs["fb_dom"], cs["E_over_window"]))
    exc = L.merge_runs(hw & (np.abs(G["cmd_lp"]) > L.CMD_EXC), int(0.5 * FS), int(0.5 * FS))
    exc = [(a, min(b + int(1.5 * FS), len(G["t"]))) for a, b in exc]
    eps = L.merge_runs(hw & (G["env"] > L.ENV_THR), int(0.6 * FS), int(0.5 * FS))
    eps = [(max(a - int(0.3 * FS), 0), min(b + int(0.3 * FS), len(G["t"]))) for a, b in eps]
    rows = [L.event_row(G, C, a, b, tag, "EXC") for a, b in exc] + [L.event_row(G, C, a, b, tag, "OSC") for a, b in eps]
    for r in rows:
        if r["kind"] == "EXC":
            r["osc_inside"] = any(not (e["t0"] + e["dur"] < r["t0"] or e["t0"] > r["t0"] + r["dur"]) for e in rows if e["kind"] == "OSC")
        else:
            r["in_exc"] = any(not (e["t0"] + e["dur"] < r["t0"] or e["t0"] > r["t0"] + r["dur"]) for e in rows if e["kind"] == "EXC")
    p("  COMMAND EXCURSIONS (|cmd|_1Hz > %.0f, +1.5 s): %d;   OSC EPISODES (env > %.0f wire, >= 0.6 s): %d, %.1f s" % (
        L.CMD_EXC, len(exc), L.ENV_THR, len(eps), sum(b - a for a, b in eps) / FS))
    p("  kind    t0    dur     v  ang50 swing | cmdpk cmd50 idx50 idxpk  tq50 | f_rate prom f_inst  f_T  f_cmd promc | envpk amp  amp412 (deg/s) | ampcmd cmd412 | coh_c ph_c cohband cohA | ampT |T|50 |T|90 Tsat damp cohT phT | des err err412 | ch_prail ch_fbcl |E|50 ref50 win")
    for r in sorted(rows, key=lambda r: r["t0"]):
        p("  %-4s%s %6.1f %4.1f %5.1f %6.1f %5.1f | %5.0f %5.0f %5.0f %5.0f %5.0f | %5.2f %4.0f %5.2f %5.2f %5.2f %4.0f | %5.0f %4.0f %5.0f (%4.1f) | %5.0f %5.0f | %4.2f %5.0f %5.2f %4.2f | %4.0f %5.0f %5.0f %4.2f %4.2f %4.2f %5.0f | %5.3f %5.3f %5.3f | %6.4f %6.4f %6.0f %5.1f %4.1f" % (
            r["kind"], "*" if r.get("osc_inside") or r.get("in_exc") else " ", r["t0"], r["dur"], r["v"], r["ang50"], r["ang_swing"],
            r["cmd_pk"], r["cmd50"], r["idx50"], r["idx_pk"], r["tq50"], r["f_rate"], r["prom_rate"], r["f_inst"], r["f_T"], r["f_cmd"], r["prom_cmd"],
            r["env_pk"], r["amp_rate"], r["amp_rate_412"], r["amp_rate_412"] / L.CPD, r["amp_cmd"], r["amp_cmd_412"], r["coh_cmd"], r["ph_cmd"], r["coh_cmd_band"], r["coh_ang_cmd"],
            r["amp_T"], r["absT50"], r["absT90"], r["T_sat"], r["damp"], r["coh_T"], r["ph_T"], r.get("des_amp", np.nan), r.get("err_amp", np.nan), r.get("err_amp_412", np.nan),
            r.get("ch_p_rail", np.nan), r.get("ch_fb_clamped", np.nan), r.get("ch_absE_p50", np.nan), r.get("ch_ref_p50", np.nan), r.get("ch_window_p50", np.nan)))
    st = L.strata_table(G, tag)
    p("  STRATA (highway; Welch 1.28 s runs):  v      |cmd|      secs  welch_s |  2-4    4-8   8-12   4-12 (wire^2) | fpk prom | env50 env95 env99 osc_duty | idx50 idx90 cmd50 tq50")
    for s in st:
        p("    %-8s %-12s %6.0f %6.0f | %6.0f %6.0f %6.0f %6.0f | %5.2f %4.0f | %4.0f %4.0f %4.0f %5.3f | %4.0f %4.0f %5.0f %5.0f" % (
            "%d-%d" % tuple(s["v"]), "%d-%s" % (s["cmd"][0], "inf" if s["cmd"][1] > 1e8 else "%d" % s["cmd"][1]), s["secs"], s["welch_s"],
            s["b24"], s["b48"], s["b812"], s["b412"], s["fpk"], s["prom"], s["env50"], s["env95"], s["env99"], s["osc_duty"], s["idx50"], s["idx90"], s["cmd50"], s["tq50"]))
    open(os.path.join(HERE, "LANECHANGE-%s.txt" % tag), "w", encoding="utf-8").write("\n".join(lines))
    return rows, st, dict(highway=cs, hw_secs=float(hw.sum() / FS), v50=float(np.median(G["v"][hw])), vmax=float(G["v"][hw].max()),
                          cmd_pct=np.percentile(np.abs(G["cmd"][hw]), [50, 90]).tolist(), idx_pct=np.percentile(G["idx"][hw], [50, 90, 99]).tolist(),
                          env_pct=np.percentile(G["env"][hw], [95, 99, 100]).tolist(), P=P412, n_osc=len(eps), osc_secs=float(sum(b - a for a, b in eps) / FS))


# ----------------------------------------------------------------------------------------------------------------------
# 3b. lane-change windows (lanechange_windows.py, no operator anchors on r34)
# ----------------------------------------------------------------------------------------------------------------------
def windows(tag, G, C, osc_rows):
    D = dict(np.load(os.path.join(L.ROUTES[tag][2], "_ha_%s.npz" % L.ROUTES[tag][0])))
    t0 = D["t18"][0]
    lc = dict(np.load(os.path.join(HERE, "_scratch", "_lc_%s.npz" % tag)))
    tl = lc["tm"] - t0
    code = np.array([{"off": 0, "preLaneChange": 1, "laneChangeStarting": 2, "laneChangeFinishing": 3}.get(s, 0) for s in lc["lcs"]])
    dcode = np.array([{"none": 0, "left": -1, "right": 1}.get(s, 0) for s in lc["lcd"]])
    idx = np.clip(np.searchsorted(tl, G["t"], side="right") - 1, 0, len(tl) - 1)
    lcs100 = code[idx]; lcd100 = dcode[idx]
    tb = lc["tb"] - t0
    ib = np.clip(np.searchsorted(tb, G["t"], side="right") - 1, 0, len(tb) - 1)
    blink = np.where(lc["lb"][ib] > 0, -1, 0) + np.where(lc["rb"][ib] > 0, 1, 0)
    runs = L.merge_runs(lcs100 > 0, 1, int(1.0 * FS))
    wins = [(a, min(b + int(2.0 * FS), len(G["t"]))) for a, b in runs]
    rows = []
    for i, (a, b) in enumerate(wins):
        s = W.stats_window(G, C, a, b, tag)
        dirs = lcd100[a:b]; d = "L" if (dirs < 0).sum() > (dirs > 0).sum() else ("R" if (dirs > 0).any() else "-")
        bl = blink[a:b]; bk = "L" if (bl < 0).sum() > (bl > 0).sum() else ("R" if (bl > 0).any() else "-")
        ta, tb_ = G["t"][a], G["t"][b - 1]
        hit = [e for e in osc_rows if not (e["t0"] + e["dur"] < ta or e["t0"] > tb_)]
        # ring, UNGATED: the OSC detector's own rule (env > ENV_THR for >= 0.6 s) inside the window, without the highway gate
        ring_runs = L.merge_runs(G["env"][a:b] > L.ENV_THR, int(0.6 * FS), int(0.5 * FS))
        # 4-8 Hz rate power inside the window (Welch, 1.28 s), same estimator as the strata table
        f, Pw = signal.welch(G["rate"][a:b] - G["rate"][a:b].mean(), fs=FS, nperseg=min(128, b - a))
        df = f[1] - f[0]
        s.update(t0=float(ta), dur=float((b - a) / FS), dir=d, blink=bk, osc_hit=[e["t0"] for e in hit], ring=bool(ring_runs),
                 ring_secs=float(sum(y - x for x, y in ring_runs) / FS), b48=float(Pw[(f >= 4) & (f < 8)].sum() * df),
                 b812=float(Pw[(f >= 8) & (f < 12)].sum() * df), b24=float(Pw[(f >= 2) & (f < 4)].sum() * df),
                 hands_light=bool(s["tq_pk"] < H.CLIFF_LO), i=i, tq50=float(np.median(np.abs(G["tq"][a:b]))), cliff_frac=float(np.mean(np.abs(G["tq"][a:b]) >= H.CLIFF_LO)))
        rows.append(s)
    return rows, lcs100, wins


def print_windows(tag, rows):
    pr("  LANE-CHANGE WINDOWS %s (laneChangeState != off, +2 s settle): %d" % (tag, len(rows)))
    pr("   #    t0   dur dir blk |    v ang50 swing | cmdpk idxpk tqpk | amp412 envpk f_rate prom f_inst  f_T |  ampT |T|90 Tsat damp |  coh  ph | P-rail fb-cl |E|50 |E|90 ref50 | eng  hw |  2-4   4-8  8-12 (wire^2) | tq50 cliff% | ring(ungated) OSC-hit(gated)")
    for s in rows:
        pr("  %2d %6.1f %5.1f  %s   %s  | %4.1f %5.1f %5.1f | %5.0f %5.0f %5.0f | %6.1f %5.0f %6.2f %4.0f %6.2f %5.2f | %5.0f %5.0f %4.2f %4.2f | %4.2f %4.0f | %6.4f %6.4f %5.0f %5.0f %5.1f | %4.2f %4.2f | %5.0f %5.0f %5.0f | %5.0f %4.2f | %s %s" % (
            s["i"], s["t0"], s["dur"], s["dir"], s["blink"], s["v"], s["ang50"], s["swing"], s["cmd_pk"], s["idx_pk"], s["tq_pk"], s["amp412"], s["env_pk"],
            s["f_rate"], s["prom"], s["f_inst"], s["f_T"], s["amp_T"], s["absT90"], s["T_sat"], s["damp"], s["coh"], s["ph"],
            s["p_rail"], s["fb_cl"], s["absE50"], s["absE90"], s["ref50"], s["eng"], s["hw"], s["b24"], s["b48"], s["b812"], s["tq50"], s["cliff_frac"],
            ("RING %.1fs" % s["ring_secs"]) if s["ring"] else "no-ring", ("OSC@" + ",".join("%.1f" % t for t in s["osc_hit"])) if s["osc_hit"] else "-"))


# ----------------------------------------------------------------------------------------------------------------------
# 4. tune side effects on the backcalc grids
# ----------------------------------------------------------------------------------------------------------------------
def side_effects(tag, g):
    m = (g["lat"] > 0.5) & (g["v"] >= 20) & (g["pressed"] < 0.5) & (g["active"] > 0.5)
    o = dict(secs=float(m.sum() / FS))
    err = g["error"][m]; da = (g["desiredLateralAccel"] - g["actualLateralAccel"])[m]
    o["err_rms"] = float(np.sqrt(np.nanmean(err ** 2))); o["err_p90"] = float(np.nanpercentile(np.abs(err), 90))
    o["desact_rms"] = float(np.sqrt(np.nanmean(da ** 2)))
    dc = (g["descurv"] - g["curv"])[m]
    o["curv_rms"] = float(np.sqrt(np.nanmean(dc ** 2))); o["curv_err_x_v2_rms"] = float(np.sqrt(np.nanmean((dc * g["v"][m] ** 2) ** 2)))
    ang = g["ang"]
    P, tot = H.band_power(ang, m, nperseg=1024)
    runs = H.runs_of(m, 1024); acc, n = None, 0
    for a, b in runs:
        f, Pw = signal.welch(ang[a:b] - ang[a:b].mean(), fs=FS, nperseg=1024)
        acc = Pw * (b - a) if acc is None else acc + Pw * (b - a); n += b - a
    if acc is not None:
        Pw = acc / n; df = f[1] - f[0]
        for lo, hi in ((0.1, 0.5), (0.5, 2.0), (2.0, 4.0), (4.0, 8.0)):
            o["ang_%g-%g" % (lo, hi)] = float(Pw[(f >= lo) & (f < hi)].sum() * df)
    o["ang_welch_s"] = float(n / FS)
    i = g["i"][m]
    o["i_p50"], o["i_p90"] = float(np.nanmedian(np.abs(i))), float(np.nanpercentile(np.abs(i), 90))
    o["i_signed_p50"] = float(np.nanmedian(i)); o["i_max"] = float(np.nanmax(np.abs(i)))
    # drift: i at the last 10 % of each engaged run vs the first 10 %
    x = g["error"][m] + 0.22 * g["desiredLateralJerk"][m]
    o["fric_sat_frac"] = float(np.nanmean(np.abs(x) > B.FRIC_THR)); o["fric_x_p50"] = float(np.nanmedian(np.abs(x)))
    o["out_p50"], o["out_p90"] = [float(v) for v in np.nanpercentile(np.abs(g["output"][m]), [50, 90])]
    o["cmd_p50"], o["cmd_p90"] = [float(v) for v in np.nanpercentile(np.abs(g["cmd"][m]), [50, 90])]
    o["p_p50"], o["f_p50"] = float(np.nanmedian(np.abs(g["p"][m]))), float(np.nanmedian(np.abs(g["f"][m])))
    # 4-8 Hz power of the command (counts^2) on the same frames
    Pc, _ = H.band_power(g["cmd"], m, nperseg=128)
    o["cmd_48"] = Pc["4-8"]
    des = np.abs(g["desiredLateralAccel"])
    for nm, sel in (("straight |des|<0.3", m & (des < 0.3)), ("curve |des| 0.3-1.5", m & (des >= 0.3) & (des < 1.5)), ("v 20-25", m & (g["v"] < 25)), ("v 25-33", m & (g["v"] >= 25))):
        if sel.sum() > 200:
            o["err_rms " + nm] = float(np.sqrt(np.nanmean(g["error"][sel] ** 2))); o["secs " + nm] = float(sel.sum() / FS)
            o["ang_p50 " + nm] = float(np.nanmedian(np.abs(g["ang"][sel])))
    # i drift: median i over the first / last third of the qualifying frames, and the run-to-run spread
    ii = np.where(m)[0]; k = len(ii) // 3
    o["i_first3"], o["i_last3"] = float(np.nanmedian(g["i"][ii[:k]])), float(np.nanmedian(g["i"][ii[-k:]]))
    ie = (g["lat"] > 0.5) & (g["active"] > 0.5)
    o["i_all_eng_p50_signed"], o["i_all_eng_p90"] = float(np.nanmedian(g["i"][ie])), float(np.nanpercentile(np.abs(g["i"][ie]), 90))
    return o


def main():
    out = {}
    # ---- 1. attribution
    pr("=" * 130); pr("1. BUILD ATTRIBUTION FROM THE TAP (engaged idx>0; chain T_sim vs T_meas; hands-light idx>=200)")
    Gs = {}
    for tag in OLD + (NEW,):
        Gs[tag] = L.load(tag)
        A = attribution(tag, Gs[tag]); out.setdefault("attribution", {})[tag] = A
        pr("  %s %-16s " % (tag, L.ROUTES[tag][1]) + " | ".join("%s: corr %.3f slope %.2f agree %.3f" % (k, v["corr"], v["slope"], v["agree"]) for k, v in A.items() if isinstance(v, dict))
           + " | idx>=200 hands-light %.1f s rate p90 %.1f deg/s, push frac >60 deg/s %.2f (n %d) | T sat %.4f field max %d" % (
               A["idx200_secs"], A["idx200_rate_p90"], A["push_frac_gt60"], A["n_gt60"], A["T_sat"], A["field_max"]))
    # ---- 2. controller
    pr(); pr("=" * 130); pr("2. WHAT THE CONTROLLER USED (backcalc grids; active frames |output|>0.05)")
    gs = {}
    for tag in OLD + (NEW,):
        o, gs[tag] = controller_used(tag); out.setdefault("controller", {})[tag] = o
        cp = o["carParams"]
        pr("  %s carParams: %s LAF %.4f friction %.4f offset %.3f steerRatio %.3f actDelay %.2f | liveDelay p50 %.3f" % (
            tag, cp.get("which"), cp.get("latAccelFactor", np.nan), cp.get("friction", np.nan), cp.get("latAccelOffset", np.nan), cp.get("steerRatio", np.nan), cp.get("steerActuatorDelay", np.nan), o["lag_p50"]))
        pr("     liveTorqueParameters Filtered LAF first/last %.3f/%.3f  friction %.3f/%.3f  offset %.3f/%.3f | Raw LAF %.3f fric %.3f | liveValid %.0f useParams %.0f buckets %.0f" % (
            o.get("latAccelFactorFiltered_first", np.nan), o.get("latAccelFactorFiltered_last", np.nan), o.get("frictionCoefficientFiltered_first", np.nan), o.get("frictionCoefficientFiltered_last", np.nan),
            o.get("latAccelOffsetFiltered_first", np.nan), o.get("latAccelOffsetFiltered_last", np.nan), o.get("latAccelFactorRaw_last", np.nan), o.get("frictionCoefficientRaw_last", np.nan),
            o.get("liveValid_p50", np.nan), o.get("useParams_p50", np.nan), o.get("totalBucketPoints_last", np.nan)))
        pr("     IDENTITY -(p+i+d+f)/output = LAF: p5/p50/p95 %.3f/%.3f/%.3f | p/error = kp p50 %.3f | f-regression friction*LAF %.3f -> friction %.3f (resid %.3f) | vehicle-model lat/(ang_rad*v^2) p50 %.4f (n %d) | liveParameters.steerRatio p50 %.2f" % (
            o.get("LAF_from_pid_p5", np.nan), o.get("LAF_from_pid_p50", np.nan), o.get("LAF_from_pid_p95", np.nan), o.get("kp_p50", np.nan), o.get("fricLAF_from_f", np.nan), o.get("friction_from_f", np.nan), o.get("f_fit_resid", np.nan),
            o["vm_lat_per_ang_v2"], o["vm_n"], o["liveSR_p50"]))
    # ---- 3. detector + windows on r34
    pr(); pr("=" * 130); pr("3. LANE-CHANGE CENSUS r34 (same detector / thresholds as r32/r33)")
    J = json.load(open(os.path.join(HERE, "lanechange_events.json")))
    rows, st, summ = route_events(NEW, Gs[NEW])
    J["events"][NEW] = rows; J["strata"][NEW] = st; J["chain"][NEW] = dict(highway=summ["highway"])
    json.dump(J, open(os.path.join(HERE, "lanechange_events.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else (list(o) if isinstance(o, tuple) else str(o))))
    out["summary_r34"] = summ
    pr("  r34 highway engaged %.0f s, v p50/max %.1f/%.1f, |cmd| p50/p90 %s, idx p50/p90/p99 %s, env p95/p99/max %s, rate 2-4/4-8/8-15 %.0f/%.0f/%.0f, OSC episodes %d (%.1f s)" % (
        summ["hw_secs"], summ["v50"], summ["vmax"], np.round(summ["cmd_pct"]), np.round(summ["idx_pct"]), np.round(summ["env_pct"]), summ["P"]["2-4"], summ["P"]["4-8"], summ["P"]["8-15"], summ["n_osc"], summ["osc_secs"]))
    osc = [r for r in rows if r["kind"] == "OSC"]
    C34 = L.chain(Gs[NEW], L.CHAIN_CFG[NEW])
    wrows, lcs100, wins = windows(NEW, Gs[NEW], C34, osc)
    print_windows(NEW, wrows)
    out["windows_r34"] = wrows
    orphan = [e for e in osc if not any(not (e["t0"] + e["dur"] < Gs[NEW]["t"][a] or e["t0"] > Gs[NEW]["t"][b - 1]) for a, b in wins)]
    pr("  OSC episodes outside any lane-change window (plain lane keeping): %d  -> %s" % (len(orphan), ["%.1f s v %.1f f %.2f amp %.1f" % (e["t0"], e["v"], e["f_rate"], e["amp_rate_412"] / 8) for e in orphan] or "none"))
    for tag in OLD:
        Co = L.chain(Gs[tag], L.CHAIN_CFG[tag])
        wo, _, _ = windows(tag, Gs[tag], Co, [e for e in J["events"][tag] if e["kind"] == "OSC"])
        print_windows(tag, wo); out["windows_" + tag] = wo
    names = {0: "off", 1: "pre", 2: "starting", 3: "finishing"}
    G = Gs[NEW]
    for wnum in (1, 2):
        a, b = wins[wnum]; a = max(a - 200, 0); b = min(b + 100, len(G["t"]))
        pr("  ---- r34 WINDOW %d, 0.5 s bins (v, angle, cmd, idx, 2-12 Hz env pk, |T|, |tq| raw, lcState) ----" % wnum)
        pr("     t     v   ang   cmd  idx  env |T|  |tq| lcState")
        for k in range(a, b, 50):
            w = slice(k, min(k + 50, b))
            pr("  %6.1f %5.1f %5.1f %5.0f %4.0f %4.0f %4.0f %5.0f %-9s" % (G["t"][k], G["v"][w].mean(), G["ang"][w].mean(), G["cmd"][w].mean(), G["idx"][w].mean(), G["env"][w].max(), np.abs(G["T"][w]).mean(), np.abs(G["tq"][w]).mean(), names[int(np.median(lcs100[w]))]))
    pr("  LOOP BLOCKS (lanechange_loop.loop_table) on r34 highway frames:")
    out["loop_r34"] = dict(hw_all=LL.loop_table(G, G["hw"], "HIGHWAY all frames", 7.5, pr),
                           hw_cmd100_300=LL.loop_table(G, G["hw"] & (np.abs(G["cmd_lp"]) >= 100) & (np.abs(G["cmd_lp"]) < 300), "HIGHWAY |cmd| 100-300", 7.5, pr))
    # the r32/r33 windows from the baseline json, for the side-by-side
    WJ = json.load(open(os.path.join(HERE, "lanechange_windows.json")))
    pr("  HANDS-LIGHT LANE CHANGES >= 17.7 m/s, ring census (baseline r32/r33 from lanechange_windows.json: ring = OSC-hit or the report's call; r34: ungated env>40 >=0.6 s):")
    for tag in OLD:
        ws = [w for w in WJ[tag]["windows"] if w["v"] >= 17.5 and w["tq_pk"] < H.CLIFF_LO]
        pr("    %s: %d windows: %s" % (tag, len(ws), "; ".join("t0 %.0f v %.1f amp412 %.1f f %.2f" % (w["t0"], w["v"], w["amp412"], w["f_rate"]) for w in ws)))
    ws34 = [w for w in wrows if w["v"] >= 17.5 and w["hands_light"]]
    pr("    r34: %d windows, %d ring: %s" % (len(ws34), sum(w["ring"] for w in ws34), "; ".join("t0 %.0f v %.1f amp412 %.1f f %.2f b48 %.0f %s" % (w["t0"], w["v"], w["amp412"], w["f_rate"], w["b48"], "RING" if w["ring"] else "no") for w in ws34)))
    # strata side by side
    pr("  STRATA 4-8 / 8-12 Hz rate power (wire^2), highway frames, Welch 1.28 s runs  [secs]:")
    pr("    %-22s %-22s %-22s %-22s %-22s" % ("stratum", "r34 NEW", "r32 old", "r33 old", "r22 V112"))
    for v_ in ((20, 25), (25, 32), (20, 32)):
        for c_ in ((0, 100), (100, 300), (300, 1000), (0, 1e9)):
            cells = []
            for tag in (NEW, "r32", "r33", "r22"):
                s = next((s for s in J["strata"].get(tag, []) if tuple(s["v"]) == v_ and tuple(s["cmd"]) == c_), None)
                cells.append("%5.0f / %5.0f [%4.0f]" % (s["b48"], s["b812"], s["secs"]) if s else "        --        ")
            pr("    %-22s %-22s %-22s %-22s %-22s" % ("%d-%d m/s, cmd %d-%s" % (v_[0], v_[1], c_[0], "inf" if c_[1] > 1e8 else "%d" % c_[1]), *cells))
    # ---- 4. side effects
    pr(); pr("=" * 130); pr("4. TUNE SIDE EFFECTS (backcalc grids; latActive & v>=20 & not pressed & active)")
    for tag in OLD + (NEW,):
        o = side_effects(tag, gs[tag]); out.setdefault("side", {})[tag] = o
        pr("  %s %-14s %5.0f s | error RMS %.4f p90 %.4f | des-act RMS %.4f | curv err RMS %.5f (x v^2: %.4f m/s^2) | angle power 0.1-0.5 %.3f  0.5-2 %.4f  2-4 %.5f  4-8 %.5f deg^2 (%.0f s) | i p50/p90/max %.4f/%.4f/%.4f signed p50 %+.4f | fric sat frac %.3f (|x| p50 %.3f) | |out| p50/p90 %.4f/%.4f  |cmd| p50/p90 %.0f/%.0f  |p| p50 %.4f |f| p50 %.4f | cmd 4-8 Hz %.0f" % (
            tag, L.ROUTES[tag][1], o["secs"], o["err_rms"], o["err_p90"], o["desact_rms"], o["curv_rms"], o["curv_err_x_v2_rms"], o.get("ang_0.1-0.5", np.nan), o.get("ang_0.5-2", np.nan), o.get("ang_2-4", np.nan), o.get("ang_4-8", np.nan), o["ang_welch_s"],
            o["i_p50"], o["i_p90"], o["i_max"], o["i_signed_p50"], o["fric_sat_frac"], o["fric_x_p50"], o["out_p50"], o["out_p90"], o["cmd_p50"], o["cmd_p90"], o["p_p50"], o["f_p50"], o["cmd_48"]))
        pr("      error RMS by stratum: " + " | ".join("%s %.4f (%.0f s, |ang| p50 %.1f)" % (k[8:], o[k], o["secs " + k[8:]], o["ang_p50 " + k[8:]]) for k in o if k.startswith("err_rms ")) +
           " | i first/last third %+.4f/%+.4f ; all-engaged i signed p50 %+.4f |i| p90 %.4f" % (o["i_first3"], o["i_last3"], o["i_all_eng_p50_signed"], o["i_all_eng_p90"]))
    open(os.path.join(HERE, "LANECHANGE-r34-windows.txt"), "w", encoding="utf-8").write("\n".join(LINES))
    json.dump(out, open(os.path.join(HERE, "lanechange_r34.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else str(o)))


if __name__ == "__main__":
    main()
