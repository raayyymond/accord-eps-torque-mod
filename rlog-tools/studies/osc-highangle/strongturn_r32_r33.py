# -*- coding: utf-8 -*-
"""studies/osc-highangle/strongturn_r32_r33.py -- the STRONG-TURN ripple on V278 rev 3 routes r32/r33
("a small signal riding on top of a large one" while turning hard), read the same way r31 was read.
Subagent strongturn, 2026-09-02.

Per high-angle episode (from highangle_stutter.py's HIGHANGLE-r32/r33.txt lists, |angle| >= 30 deg):
  frequency, rate ripple, T ripple/level (tap), signed driver-torque 6-8.5 Hz ring, speed, stalled vs moving
  (rate / the map's reference), and -- through the FUN_00028ea6 chain mirror (v280_map_profiles.py) on the
  MEASURED 0x18F rate, rev 3 cells -- which nonlinearity is active: P rail (+-15360), D rail (+-10240), sum clamp,
  fb clamp (15360 = 62.2 deg/s), output cap (+-3072 / tap 2472), override taper (|tq| >= 2240 raw).
Then: fixed-threshold episode census across r31/r32/r33; the pre-registered statistics (i) and (iv); and the
V280 rev 2 counterfactual (map 0,52,86,103,138,275,413,550,688,1032; clamp 46080) open loop on the same frames.

Run: python strongturn_r32_r33.py   (caches analysis-2020accord/_scratch/cache/v280/r32.npz, r33.npz)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
import v280_map_profiles as V  # noqa: E402
import servo_at_reference as S  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
V.ROUTE_PREFIX.update({"r32": "75604b0a432fdc89_00000032--33a5dbbcb3", "r33": "75604b0a432fdc89_00000033--1948a2c354"})
V.ROUTE_BUILD.update({"r32": "V278r3 (map x2)", "r33": "V278r3 (map x2)"})
V.ROUTE_K.update({"r32": 2.0, "r33": 2.0})
TAP_TAGS = {"r31", "r32", "r33"}

REV3 = (V.map_knots(V.profile(2, 240, 2)), 15360)
V280R2 = (np.array([0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], float), 46080)   # PREREG-V280-READ.md, rev 2
STOCK = (V.map_knots(V.profile(1, 240, 1)), 7680)
GAIN, CAP = 5346, 3072

# episodes at |angle| >= 30 from HIGHANGLE-r32.txt / HIGHANGLE-r33.txt (t0, dur, fdom); r31 from HIGHANGLE-r31-episodes.txt
EPIS = {
    "r31": [(158.1, 1.5, 6.54), (217.1, 2.4, 7.44), (221.5, 1.7, 7.47), (266.2, 2.8, 7.03), (303.7, 1.4, 7.14), (312.7, 2.3, 7.05),
            (381.9, 3.2, 7.03), (411.3, 3.0, 7.42), (537.0, 2.1, 7.58), (546.6, 2.0, 7.46),
            (144.1, 2.0, 2.93), (434.0, 1.3, 2.27), (474.0, 1.1, 2.83)],
    "r32": [(620.7, 3.8, 7.03), (692.8, 2.8, 6.64), (726.5, 1.7, 6.55)],
    "r33": [(30.3, 1.5, 2.61), (80.9, 1.7, 5.20), (87.9, 3.2, 3.12), (100.8, 1.6, 6.96), (212.5, 1.4, 7.35), (224.1, 1.1, 6.96),
            (805.8, 1.1, 1.90), (833.5, 3.6, 7.42)],
}
HIGH_ANG_S = {"r31": 101.7, "r32": 37.1, "r33": 93.8}    # engaged time at |angle| >= 30 per highangle_stutter.py


# ------------------------------------------------------------------------------------------------------
_orig_load = V.load


def load_with_tap(tag):
    g = _orig_load(tag)
    D = dict(np.load(os.path.join(V.CACHE, tag + ".npz")))
    t0 = D["t18"][0]
    if tag in TAP_TAGS and "T_meas" not in g:
        fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
        Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
        g["T_meas"] = np.interp(g["tg"], D["t1ab"] - t0, Tm)
        g["fld"] = fld
    g["ang"] = np.interp(g["tg"], D["t14"] - t0, D["ang"])
    return g


V.load = load_with_tap


def band_amp(x, lo=6.0, hi=8.5):
    return S.band_amp(x, lo, hi)


def fixed_thr_episodes(r, thr=103.0, band=(2.0, 8.0)):
    """highangle_stutter.py's episode detector at a FIXED threshold (its per-route threshold was 103/117/130)."""
    sos = signal.butter(4, band, btype="bandpass", fs=FS, output="sos")
    rb = signal.sosfiltfilt(sos, r.wire)
    env = signal.sosfiltfilt(signal.butter(2, 1.0, fs=FS, output="sos"), np.abs(signal.hilbert(rb)))
    on = (env > thr) & r.eng
    d = np.diff(np.r_[0, on.astype(int), 0])
    eps = [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= FS]
    merged = []
    for a, b in eps:
        if merged and a - merged[-1][1] < FS:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    out = []
    for a, b in merged:
        n = b - a
        f, P = signal.welch(rb[a:b], fs=FS, nperseg=min(256, n))
        out.append(dict(t0=a / FS, dur=n / FS, fdom=float(f[np.argmax(P)]), ang=float(np.median(np.abs(r.ang[a:b]))),
                        v=float(r.vego[a:b].mean()), ramp=float(np.sqrt(2) * rb[a:b].std())))
    return out


def sim(r, Y, clamp, kd=V.KD):
    V.GAIN, V.OUT_CAP = GAIN, CAP
    R = r.simulate(Y, fb_clamp=clamp, kd=kd)
    R["clamped"] = np.abs(r.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(R["sp"]) / V.FB_DC / V.CPD
    return R


def episode_row(r, R, t0, dur, fdom, Rkd0=None):
    s, e = int(round(t0 * FS)), int(round((t0 + dur) * FS))
    m100 = np.zeros_like(r.eng); m100[s:e] = True; m100 &= r.eng
    m1k = np.zeros_like(r.eng1k); m1k[int(t0 * FS1K):int((t0 + dur) * FS1K)] = True; m1k &= r.eng1k
    M = S.tick_metrics(r, R, m1k, m100, fdom)
    i = r.i100[m100]
    M["ang"] = float(np.median(np.abs(r.ang[m100]))); M["v"] = float(r.vego[m100].mean())
    M["idx50"] = float(np.median(r.idx[m100]))
    M["D_rail"] = float(np.mean(np.abs(R["D_raw"][m1k]) > V.D_CLAMP))
    M["S_rail"] = float(np.mean(np.abs(R["S_raw"][m1k]) >= V.SUM_CLAMP))
    M["out_cap_sim"] = float(np.mean(np.abs(R["T"][m1k]) >= CAP))
    Tm = r.T_meas[m100]
    M["sat_meas"] = float(np.mean(np.abs(Tm) >= V.SAT_THR))
    M["Tmeas_ripple_level"] = M["amp7_Tmeas"] / max(M["absT_meas_p50"], 1)
    M["Tsim_ripple_level"] = M["amp7_Tsim"] / max(M["absT_sim_p50"], 1)
    tq = r.tq_raw[m100]
    M["tq_mean"] = float(tq.mean()); M["tq_abs_p50"] = float(np.median(np.abs(tq)))
    M["tq_ring"] = band_amp(tq)
    M["cliff"] = float(np.mean(np.abs(tq) >= 2240)); M["taper_lt254"] = float(np.mean(np.abs(tq) // 32 > 70))
    M["rate_amp"] = band_amp(r.wire[m100]) / V.CPD
    M["amp7_D"] = band_amp(np.clip(R["D_raw"][i], -V.D_CLAMP, V.D_CLAMP))
    M["amp7_S"] = band_amp(np.clip(R["S_raw"][i], -V.SUM_CLAMP, V.SUM_CLAMP))
    M["brake_meas"] = float(np.mean(np.sign(Tm) == r.sgn[m100]))   # tap sign == sign(v) means the lane OPPOSES the setpoint (T = -lag*gain); stalled frames read ~0.05
    if Rkd0 is not None:
        M["amp7_Tsim_kd0"] = band_amp(Rkd0["T"][i])
    dA = np.gradient(np.abs(r.ang[m100])) * FS
    M["winding"] = float(np.mean(dA > 0))                       # |angle| increasing = turning IN; else returning
    M["dabs_ang"] = float(np.median(dA))
    M["cmd_toward_centre"] = float(np.mean(np.sign(r.cmd[m100]) != np.sign(r.ang[m100])))  # sign convention unverified
    M["tq_with_cmd"] = float(np.mean(np.sign(r.tq_raw[m100]) == r.sgn[m100]))
    # classification
    rr = M["rate_over_ref"]
    M["cls"] = "STALL" if rr < 0.6 else ("ATREF" if rr <= 1.25 else "ABOVE")
    return M, m1k, m100


HDR = ("%2s %6s %4s %5s %5s %4s %4s | %5s %5s %5s %-5s | %5s %5s %5s %5s %5s %5s %5s | %5s %5s %5s %5s | %5s %5s %5s %5s %5s %5s %5s | %5s %5s %5s"
       % ("#", "t0", "dur", "fdom", "ang", "v", "idx", "rate", "ref", "r/ref", "class", "Prail", "Drail", "Srail", "fbclp", "ocap", "satM", "cliff",
          "|E|50", "brake", "Eflp", "dampE", "rAmp", "a7fb", "a7P", "a7D", "a7S", "a7Ts", "a7Tm", "Tm50", "rip/L", "tqRng"))


def fmt(k, t0, dur, fdom, M):
    return ("%2d %6.1f %4.1f %5.2f %5.0f %4.1f %4.0f | %5.1f %5.1f %5.2f %-5s | %5.2f %5.2f %5.2f %5.2f %5.2f %5.2f %5.2f | %5.0f %5.2f %5.1f %5.2f | %5.0f %5.0f %5.0f %5.0f %5.0f %5.0f %5.0f | %5.0f %5.2f %5.0f"
            % (k, t0, dur, fdom, M["ang"], M["v"], M["idx50"], M["rate_p50"], M["ref_p50"], M["rate_over_ref"], M["cls"],
               M["P_rail"], M["D_rail"], M["S_rail"], M["clamped"], M["out_cap_sim"], M["sat_meas"], M["cliff"],
               M["absE_p50"], M["E_brake"], M["E_flips"], M["dampE"],
               M["rate_amp"], M["amp7_fb"], M["amp7_P"], M["amp7_D"], M["amp7_S"], M["amp7_Tsim"], M["amp7_Tmeas"],
               M["absT_meas_p50"], M["Tmeas_ripple_level"], M["tq_ring"]))


def stat_i(r, R=None):
    """(i) T_meas 6-8.5 Hz amplitude / |T_meas| p50 on |angle| >= 30, idx >= 200, engaged, runs >= 1 s."""
    m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 200)
    d = np.diff(np.r_[0, m.astype(int), 0])
    rows = []
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if b - a < FS:
            continue
        Tm = r.T_meas[a:b]
        row = dict(t0=a / FS, dur=(b - a) / FS, amp=band_amp(Tm), lvl=float(np.median(np.abs(Tm))), tq_ring=band_amp(r.tq_raw[a:b]),
                   rate=float(np.median(np.abs(r.wire[a:b])) / V.CPD), ang=float(np.median(np.abs(r.ang[a:b]))), v=float(r.vego[a:b].mean()))
        row["ratio"] = row["amp"] / max(row["lvl"], 1)
        if R is not None:
            i = r.i100[a:b]
            row["ref"] = float(np.median(R["ref_deg"][i]))
            row["Prail"] = float(np.mean(np.abs(R["P_raw"][i]) >= V.P_CLAMP))
        rows.append(row)
    return rows


def stat_iv(r):
    """(iv) sustained full demand (idx = 240 >= 0.3 s), wheel moving with the setpoint, |tq_raw| < thr."""
    w = np.abs(r.wire) / V.CPD
    base = r.eng & (np.sign(-r.wire) == r.sgn) & V.runs(r.idx >= 240, 30)
    out = {}
    for thr in (2240, 1000, 400, 200):
        m = base & (np.abs(r.tq_raw) < thr)
        out[thr] = (int(m.sum()), float(np.median(w[m])) if m.sum() else np.nan, float(np.percentile(w[m], 90)) if m.sum() else np.nan)
    m = base & (np.abs(r.tq_raw) < 400)
    dA = np.gradient(np.abs(r.ang)) * FS
    for lab, mm in (("wind", m & (dA > 0)), ("return", m & (dA <= 0))):
        out[lab] = (int(mm.sum()), float(np.median(w[mm])) if mm.sum() else np.nan, float(np.percentile(w[mm], 90)) if mm.sum() else np.nan,
                    float(np.median(np.abs(r.ang[mm]))) if mm.sum() else np.nan, float(np.median(r.vego[mm])) if mm.sum() else np.nan,
                    float(np.median(np.abs(r.T_meas[mm]))) if mm.sum() else np.nan)
    out["tap"] = (float(np.median(np.abs(r.T_meas[m]))) if m.sum() else np.nan,
                  float(np.percentile(np.abs(r.T_meas[m]), 90)) if m.sum() else np.nan,
                  float(np.mean(w[m] > V.ceiling_degs(V.MAP_Y * 2))) if m.sum() else np.nan)
    out["v"] = float(np.median(r.vego[m])) if m.sum() else np.nan
    return out


def main():
    L = []
    pr = lambda s="": (print(s), L.append(s))  # noqa: E731
    routes = {}
    for tag in ("r31", "r32", "r33"):
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
    pr("fb clamp 15360 / (30.89 * 8) = %.1f deg/s ; rev 3 map ceiling (idx 240) = %.1f deg/s ; V280r2 ceiling = %.1f deg/s"
       % (15360 / (V.FB_DC * V.CPD), V.ceiling_degs(REV3[0]), V.ceiling_degs(V280R2[0])))
    pr("P linear window at Kp 696: |E| < %.0f = %.1f deg/s of feedback" % (V.P_CLAMP * 256 / 696, V.P_CLAMP * 256 / 696 / V.FB_DC / V.CPD))

    pooled = {}
    for tag in ("r31", "r32", "r33"):
        r = routes[tag]
        R = sim(r, *REV3)
        Rkd0 = sim(r, *REV3, kd=0)
        pr("\n" + "=" * 160)
        pr("SECTION 1 -- %s (%s): high-angle episodes through the chain with rev 3's cells (map x2, fb clamp 15360, gain 5346, cap 3072); open loop" % (tag, V.ROUTE_BUILD[tag]))
        pr("  Prail/Drail/Srail/fbclp/ocap = duty of P clamp, D clamp, sum clamp, fb clamp, output cap (sim); satM = P(|T_meas| >= 2472); cliff = P(|tq| >= 2240 raw)")
        pr("  a7x = 6-8.5 Hz amplitude of fb, P, D, S (all clamped), T_sim, T_meas; rip/L = a7Tm / |T_meas| p50 = pre-registered stat (i) on the episode; tqRng = signed driver-torque 6-8.5 Hz amp (raw)")
        pr("=" * 160)
        pr(HDR)
        m1k_f7 = np.zeros_like(r.eng1k); m100_f7 = np.zeros_like(r.eng)
        rows = []
        for k, (t0, dur, fdom) in enumerate(EPIS[tag]):
            M, a, b = episode_row(r, R, t0, dur, fdom, Rkd0)
            rows.append((k, t0, dur, fdom, M, a, b))
            pr(fmt(k, t0, dur, fdom, M) + ("  F7" if fdom >= 6 else "  F2/other") + "  a7Tsim(kd=0)=%.0f brake_meas=%.2f" % (M["amp7_Tsim_kd0"], M["brake_meas"]))
            pr("      sim-vs-meas corr %.2f slope %.2f | T_meas flips/s %.1f T_sim flips/s %.1f | driver tq mean %+.0f |tq| p50 %.0f sign(tq)==sign(cmd) %.2f | winding %.2f (d|ang|/dt %+.0f deg/s) cmd toward centre %.2f"
               % (M.get("corr_T", np.nan), M.get("slope_T", np.nan), M["Tmeas_flips"], M["Tsim_flips"], M["tq_mean"], M["tq_abs_p50"], M["tq_with_cmd"], M["winding"], M["dabs_ang"], M["cmd_toward_centre"]))
            if fdom >= 6:
                m1k_f7 |= a; m100_f7 |= b
        pooled[tag] = (m1k_f7, m100_f7, [x for x in rows if x[3] >= 6])
        f7 = [x for x in rows if x[3] >= 6]
        if f7:
            cls = [x[4]["cls"] for x in f7]
            pr("  F7 episodes: %d ; STALL %d  ATREF %d  ABOVE %d ; P-rail duty median %.2f (range %.2f-%.2f) ; rip/L median %.2f ; tq ring median %.0f raw"
               % (len(f7), cls.count("STALL"), cls.count("ATREF"), cls.count("ABOVE"), np.median([x[4]["P_rail"] for x in f7]),
                  min(x[4]["P_rail"] for x in f7), max(x[4]["P_rail"] for x in f7), np.median([x[4]["Tmeas_ripple_level"] for x in f7]),
                  np.median([x[4]["tq_ring"] for x in f7])))

    pr("\n" + "=" * 160)
    pr("SECTION 2 -- fixed-threshold episode census (2-8 Hz rate envelope > 103 wire on ALL routes; highangle_stutter used 103/117/130), engaged, >= 1 s")
    pr("=" * 160)
    for tag in ("r31", "r32", "r33"):
        r = routes[tag]
        eps = fixed_thr_episodes(r)
        hi = [e for e in eps if e["ang"] >= 30]
        f7 = [e for e in hi if e["fdom"] >= 6]
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS)
        pr("%s: engaged %.0f s, high-angle %.1f s | episodes %d (%.1f s) ; at >=30 deg %d (%.1f s) ; F7 (fdom>=6) %d (%.1f s) = %.1f per 100 s high-angle ; F7 rate amp median %.0f wire ; fdom list %s"
           % (tag, r.eng.sum() / FS, hs, len(eps), sum(e["dur"] for e in eps), len(hi), sum(e["dur"] for e in hi), len(f7), sum(e["dur"] for e in f7),
              100 * len(f7) / hs, np.median([e["ramp"] for e in f7]) if f7 else np.nan, " ".join("%.1f" % e["fdom"] for e in hi)))
        # 7 Hz rate power in the strong-turn frames themselves, not only in episodes
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 200)
        runs = V.runs(m, 100)
        a7 = band_amp(r.wire[runs]) / V.CPD if runs.sum() > 100 else np.nan
        pr("   |angle|>=30 & idx>=200: %.1f s ; rate 6-8.5 Hz amp over >=1 s runs %.1f deg/s ; signed driver-torque 6-8.5 Hz amp %.0f raw" % (
            m.sum() / FS, a7, band_amp(r.tq_raw[runs]) if runs.sum() > 100 else np.nan))

    pr("\n" + "=" * 160)
    pr("SECTION 3 -- pre-registered statistic (i): T_meas 6-8.5 Hz amp / |T_meas| p50, per run of (engaged & |angle|>=30 & idx>=200, >= 1 s)")
    pr("=" * 160)
    for tag in ("r31", "r32", "r33"):
        r = routes[tag]
        R = sim(r, *REV3)
        rows = stat_i(r, R)
        pr("%s: %d runs, %.1f s ; ratio p50 %.2f (p10-p90 %.2f-%.2f) ; amp p50 %.0f ; |T| level p50 %.0f ; tq ring p50 %.0f raw ; rate p50 %.1f vs ref %.1f deg/s ; P-rail median %.2f"
           % (tag, len(rows), sum(x["dur"] for x in rows), np.median([x["ratio"] for x in rows]), np.percentile([x["ratio"] for x in rows], 10),
              np.percentile([x["ratio"] for x in rows], 90), np.median([x["amp"] for x in rows]), np.median([x["lvl"] for x in rows]),
              np.median([x["tq_ring"] for x in rows]), np.median([x["rate"] for x in rows]), np.median([x["ref"] for x in rows]), np.median([x["Prail"] for x in rows])))
        for x in rows:
            pr("    t0 %6.1f dur %4.1f ang %4.0f v %4.1f | amp %4.0f lvl %5.0f ratio %.2f | tq ring %5.0f | rate %5.1f ref %5.1f (%.2f) Prail %.2f%s"
               % (x["t0"], x["dur"], x["ang"], x["v"], x["amp"], x["lvl"], x["ratio"], x["tq_ring"], x["rate"], x["ref"], x["rate"] / max(x["ref"], 1), x["Prail"],
                  "  <-- >= 0.45 (prereg FAIL band)" if x["ratio"] >= 0.45 else ""))

    pr("\n" + "=" * 160)
    pr("SECTION 4 -- pre-registered statistic (iv): sustained full demand (idx = 240 >= 0.3 s), wheel with setpoint; n | rate p50/p90 deg/s by |tq_raw| ceiling")
    pr("=" * 160)
    for tag in ("r31", "r32", "r33"):
        o = stat_iv(routes[tag])
        pr("%s ceil %.1f | " % (tag, V.ceiling_degs(REV3[0])) + " | ".join("<%4d: n=%4d %5.1f/%5.1f" % (t, *o[t]) for t in (2240, 1000, 400, 200))
           + " | tap |T| p50/p90 %.0f/%.0f, rate>ceil %.2f (tq<400) ; v50 %.1f" % (*o["tap"], o["v"]))
        pr("      tq<400 split: WINDING in  n=%4d rate %5.1f/%5.1f |ang| %3.0f v %4.1f |T| %4.0f   |   RETURNING n=%4d rate %5.1f/%5.1f |ang| %3.0f v %4.1f |T| %4.0f" % (*o["wind"], *o["return"]))

    pr("\n" + "=" * 160)
    pr("SECTION 5 -- V280 rev 2 COUNTERFACTUAL, open loop on the same measured rate: pooled F7 ticks per route, and per episode")
    pr("=" * 160)
    for tag in ("r31", "r32", "r33"):
        r = routes[tag]
        m1k, m100, f7 = pooled[tag]
        if not f7:
            pr("%s: no F7 episodes" % tag); continue
        pr("%s pooled F7 (%.1f s): %-24s | %6s %6s %5s %6s %5s %5s | %5s %5s | %6s %6s %6s %5s %5s | %s" % (
            tag, m100.sum() / FS, "map / clamp", "|E|50", "|E|90", "brake", "Eflp/s", "clamp", "Prail", "ref", "r/ref", "a7E", "a7P", "a7Tsim", "Ts50", "Tsflp", "rip/L (sim)"))
        for name, (Y, clamp) in (("rev3 x2 / 15360", REV3), ("V280r2 line x6 / 46080", V280R2), ("stock x1 / 7680", STOCK)):
            Rc = sim(r, Y, clamp)
            M = S.tick_metrics(r, Rc, m1k, m100)
            a7E, a7P, a7T, tfl, rl = [], [], [], [], []
            for k, t0, dur, fd, _, a, b in f7:
                Me = S.tick_metrics(r, Rc, a, b, fd)
                a7E.append(Me["amp7_E"]); a7P.append(Me["amp7_P"]); a7T.append(Me["amp7_Tsim"]); tfl.append(Me["Tsim_flips"])
                rl.append(Me["amp7_Tsim"] / max(Me["absT_sim_p50"], 1))
            pr("    %-38s | %6.0f %6.0f %5.2f %6.1f %5.2f %5.2f | %5.1f %5.2f | %6.0f %6.0f %6.0f %5.0f %5.1f | %.2f (per-episode %s)" % (
                name, M["absE_p50"], M["absE_p90"], M["E_brake"], M["E_flips"], M["clamped"], M["P_rail"], M["ref_p50"], M["rate_over_ref"],
                np.median(a7E), np.median(a7P), np.median(a7T), M["absT_sim_p50"], np.median(tfl), np.median(a7T) / max(M["absT_sim_p50"], 1),
                " ".join("%.2f" % x for x in rl)))
        # per-episode V280 P-rail and class
        Rc = sim(r, *V280R2)
        for k, t0, dur, fd, M0, a, b in f7:
            Me = S.tick_metrics(r, Rc, a, b, fd)
            pr("    ep %d t0 %6.1f %s rev3: Prail %.2f rip/L_sim %.2f (meas %.2f) -> V280r2: Prail %.2f rip/L_sim %.2f |T|sim %.0f brake %.2f ; r/ref %.2f -> %.2f"
               % (k, t0, M0["cls"], M0["P_rail"], M0["Tsim_ripple_level"], M0["Tmeas_ripple_level"], Me["P_rail"],
                  Me["amp7_Tsim"] / max(Me["absT_sim_p50"], 1), Me["absT_sim_p50"], Me["E_brake"], M0["rate_over_ref"], Me["rate_over_ref"]))

    pr("\n" + "=" * 160)
    pr("SECTION 6 -- WHICH MAP IS ON THE CAR? chain T_sim vs the CAN-427 tap, engaged idx>0 frames: sign agreement / corr / LS slope; brake fraction meas/sim by rate at idx>=200")
    pr("  brake = P(sign(T) == sign(v)): the tap and the chain share the convention T = -lag*gain, so sign(T) == sign(v) is the lane OPPOSING the setpoint")
    pr("=" * 160)
    cands = {"rev3 x2 / 15360": REV3, "x3 / 23040": (V.map_knots(V.profile(3, 240, 3)), 23040), "x4 / 30720": (V.map_knots(V.profile(4, 240, 4)), 30720),
             "V280r2 line x6 / 46080": V280R2, "V276 x6 uniform / 46080": (V.map_knots(V.profile(6, 240, 6)), 46080),
             "V280r1 2@96->6 / 46080": (V.map_knots(V.profile(2, 96, 6)), 46080)}
    best = {}
    for tag in ("r31", "r32", "r33"):
        r = routes[tag]; e = r.eng & (r.idx > 0); w = np.abs(r.wire) / V.CPD; hi = e & (np.abs(r.ang) >= 30)
        base = r.eng & (np.sign(-r.wire) == r.sgn) & (r.idx >= 200)
        for name, (Y, cl) in cands.items():
            Rc = sim(r, Y, cl); Ts = Rc["T"][r.i100]; Tm = r.T_meas
            c = float(np.corrcoef(Ts[e], Tm[e])[0, 1])
            cells = []
            for lo, hi_ in ((40, 60), (60, 80), (80, 100), (100, 130), (130, 400)):
                m = base & (w >= lo) & (w < hi_)
                cells.append(("%.2f/%.2f" % (np.mean(np.sign(Tm[m]) == r.sgn[m]), np.mean(np.sign(Ts[m]) == r.sgn[m]))) if m.sum() >= 20 else "  --  ")
            pr("  %s %-26s all: agree %.3f corr %.3f slope %.2f | |ang|>=30: agree %.3f corr %.3f | brake meas/sim @ 40-60 60-80 80-100 100-130 130+ deg/s: %s" % (
                tag, name, np.mean(np.sign(Ts[e]) == np.sign(Tm[e])), c, np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2),
                np.mean(np.sign(Ts[hi]) == np.sign(Tm[hi])), np.corrcoef(Ts[hi], Tm[hi])[0, 1], "  ".join(cells)))
            best.setdefault(tag, []).append((c, name))
        pr("  %s best-fitting map: %s" % (tag, max(best[tag])[1]))

    pr("\n" + "=" * 160)
    pr("SECTION 7 -- r32/r33 high-angle episodes through the V280 rev 2 chain (line x6, clamp 46080) -- the map SECTION 6 says was on the car -- and two open-loop levers")
    pr("=" * 160)
    for tag in ("r32", "r33"):
        r = routes[tag]
        Rb = sim(r, *V280R2); Rkd0 = sim(r, *V280R2, kd=0)
        V.GAIN, V.OUT_CAP = GAIN, CAP
        Rkp = r.simulate(V280R2[0], kpY=V.KP_Y * 0.5, fb_clamp=V280R2[1]); Rkp["clamped"] = np.abs(r.fb_un) >= V280R2[1]; Rkp["ref_deg"] = 32 * np.abs(Rkp["sp"]) / V.FB_DC / V.CPD
        for (t0, dur, fd) in EPIS[tag]:
            M, a, b = episode_row(r, Rb, t0, dur, fd, Rkd0)
            Mk, _, _ = episode_row(r, Rkp, t0, dur, fd)
            pr("  %s t0 %6.1f dur %3.1f fdom %.2f %s ang %4.0f v %3.1f idx %3.0f | corr %.2f slope %.2f | rate %5.1f ref %5.1f r/ref %.2f | Prail %.2f Drail %.2f fbclp %.2f cliff %.2f | brake sim %.2f meas %.2f | rip/L sim %.2f meas %.2f (|T| %4.0f) | a7 P %5.0f D %5.0f | rip/L sim kd=0 %.2f, Kp x0.5 %.2f | tq ring %4.0f | T re rate %+.0f deg"
               % (tag, t0, dur, fd, "F7" if fd >= 6 else "F2", M["ang"], M["v"], M["idx50"], M.get("corr_T", np.nan), M.get("slope_T", np.nan), M["rate_p50"], M["ref_p50"], M["rate_over_ref"],
                  M["P_rail"], M["D_rail"], M["clamped"], M["cliff"], M["E_brake"], M["brake_meas"], M["Tsim_ripple_level"], M["Tmeas_ripple_level"], M["absT_meas_p50"],
                  M["amp7_P"], M["amp7_D"], M["amp7_Tsim_kd0"] / max(M["absT_sim_p50"], 1), Mk["Tsim_ripple_level"], M["tq_ring"], M["ph_Tmeas_re_rate"]))

    pr("\n" + "=" * 160)
    pr("SECTION 8 -- pre-registered (vi) low-command damping fraction P(sign(T) != sign(raw rate)), |cmd| < 1300 engaged; (viii) saturation P(|field| >= 309) engaged")
    pr("=" * 160)
    for tag in ("r31", "r32", "r33"):
        r = routes[tag]; m = r.eng & (np.abs(r.cmd) < 1300) & (r.T_meas != 0) & (r.wire != 0)
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz"))); t0 = D["t18"][0]
        e1 = np.interp(D["t1ab"] - t0, r.tg, r.eng.astype(float)) > 0.5
        pr("  %s (vi) %.3f (n=%d) | (viii) %.4f, max |field| %d" % (tag, np.mean(np.sign(r.T_meas[m]) != np.sign(r.wire[m])), m.sum(), np.mean((r.fld[e1] & 511) >= 309), (r.fld[e1] & 511).max()))

    out = os.path.join(HERE, "_scratch", "strongturn_r32_r33.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
