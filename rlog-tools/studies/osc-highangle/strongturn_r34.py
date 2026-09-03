# -*- coding: utf-8 -*-
"""studies/osc-highangle/strongturn_r34.py -- the STRONG-TURN / high-angle picture on r34 (V280 rev 2, NEW StarPilot
tune: SteerFriction 0.212->0.03, SteerLatAccel 1.689->2.11, SteerRatio 16.1, ForceAutoTune off), scored EXACTLY as
r32/r33 were in strongturn_r32_r33.py (same thresholds, same chain, same episode lists from highangle_stutter.py).
Subagent highangle34, 2026-09-03.

Sections:
  A  build attribution from the CAN-427 tap: chain T_sim vs tap per candidate map; push->brake crossover by rate
  B  fixed-threshold (103 wire) F7 census r32/r33/r34 + the per-route-threshold census highangle_stutter.py printed
  C  per-episode table (|angle| >= 30, engaged) through the V280 rev 2 chain (line x6, clamp 46080), open loop on the
     MEASURED 0x18F rate: f_dom, rate/ref, class, P/D rail, fb clamp, cliff duty, brake sim/meas, rate ripple, T
     ripple/level sim/meas, driver-torque ring, COMMAND 6-8.5 Hz amplitude (the outer loop's footprint), corr
  D  pre-registered statistics (i)-(vi), (viii) on r32/r33/r34  ((vii) is stat_vii_2to4.py, house cache)
  E  authority: hands-light full-demand rate p50/p90, winding vs returning; manual exposure by speed

Run: python strongturn_r34.py   (needs analysis-2020accord/_scratch/cache/v280/r32,r33,r34.npz)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strongturn_r32_r33 as ST  # noqa: E402  (registers r32/r33, patches V.load with the tap)
V, S = ST.V, ST.S
FS = ST.FS

V.ROUTE_PREFIX["r34"] = "75604b0a432fdc89_00000034--e2d2d5381f"
V.ROUTE_BUILD["r34"] = "V280r2 line x6 (new tune)"
V.ROUTE_K["r34"] = 6.0
V.ROUTE_BUILD["r32"] = V.ROUTE_BUILD["r33"] = "V280r2 line x6 (old tune)"     # tap-attributed in HIGHANGLE-r32-r33
V.ROUTE_K["r32"] = V.ROUTE_K["r33"] = 6.0
ST.TAP_TAGS.add("r34")

# HIGHANGLE-r34.txt episodes (highangle_stutter.py, thr 100 wire = its low-angle floor), |angle| >= 30 only (#7 at 0.8 deg dropped)
ST.EPIS["r34"] = [(31.0, 3.3, 1.95), (35.5, 1.5, 7.43), (77.7, 1.2, 6.84), (133.1, 2.1, 7.28), (172.2, 1.3, 2.36), (182.4, 4.1, 7.81),
                  (188.2, 1.1, 7.48), (227.9, 1.1, 2.78), (297.5, 2.0, 2.49), (343.7, 1.6, 7.41), (372.9, 1.6, 6.92), (475.7, 3.5, 7.03),
                  (480.9, 3.8, 6.64), (664.8, 1.3, 3.76), (667.7, 1.7, 7.06), (747.8, 1.1, 2.75), (985.7, 2.0, 2.44), (1003.6, 1.0, 7.77)]
ST.HIGH_ANG_S["r34"] = 148.1
ROUTES = ("r32", "r33", "r34")
V280R2 = ST.V280R2


def sim(r, Y, clamp, kd=V.KD):
    return ST.sim(r, Y, clamp, kd)


def main():
    L = []
    pr = lambda s="": (print(s), L.append(s))  # noqa: E731
    routes = {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)

    # ---------------------------------------------------------------------------------------------- A
    pr("=" * 160)
    pr("SECTION A -- BUILD ATTRIBUTION from the tap: chain T_sim vs CAN-427 T_meas, engaged idx>0 frames; brake = P(sign T == sign v) meas/sim by rate, idx>=200")
    pr("=" * 160)
    cands = {"rev3 x2 / 15360": ST.REV3, "x4 / 30720": (V.map_knots(V.profile(4, 240, 4)), 30720),
             "V280r2 line x6 / 46080": V280R2, "V276 x6 uniform / 46080": (V.map_knots(V.profile(6, 240, 6)), 46080),
             "V280r1 2@96->6 / 46080": (V.map_knots(V.profile(2, 96, 6)), 46080)}
    for tag in ROUTES:
        r = routes[tag]; e = r.eng & (r.idx > 0); w = np.abs(r.wire) / V.CPD; hi = e & (np.abs(r.ang) >= 30)
        base = r.eng & (np.sign(-r.wire) == r.sgn) & (r.idx >= 200)
        best = []
        for name, (Y, cl) in cands.items():
            Rc = sim(r, Y, cl); Ts = Rc["T"][r.i100]; Tm = r.T_meas
            c = float(np.corrcoef(Ts[e], Tm[e])[0, 1])
            cells = []
            for lo, hi_ in ((40, 60), (60, 80), (80, 100), (100, 130), (130, 400)):
                m = base & (w >= lo) & (w < hi_)
                cells.append(("%.2f/%.2f (n%4d)" % (np.mean(np.sign(Tm[m]) == r.sgn[m]), np.mean(np.sign(Ts[m]) == r.sgn[m]), m.sum())) if m.sum() >= 20 else "  --  (n%4d)" % m.sum())
            pr("  %s %-26s all: agree %.3f corr %.3f slope %.2f | |ang|>=30: agree %.3f corr %.3f | brake meas/sim @ 40-60 60-80 80-100 100-130 130+: %s" % (
                tag, name, np.mean(np.sign(Ts[e]) == np.sign(Tm[e])), c, np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2),
                np.mean(np.sign(Ts[hi]) == np.sign(Tm[hi])), np.corrcoef(Ts[hi], Tm[hi])[0, 1], "  ".join(cells)))
            best.append((c, name))
        pr("  %s best-fitting map: %s" % (tag, max(best)[1]))
        # crossover: rate at which measured brake fraction crosses 0.5 (idx >= 200)
        edges = np.arange(20, 200, 10)
        fr = []
        for lo in edges:
            m = base & (w >= lo) & (w < lo + 10)
            fr.append(np.mean(np.sign(r.T_meas[m]) == r.sgn[m]) if m.sum() >= 20 else np.nan)
        pr("  %s measured brake fraction by 10 deg/s bin from 20: %s" % (tag, " ".join("--" if np.isnan(x) else "%.2f" % x for x in fr)))

    # ---------------------------------------------------------------------------------------------- B
    pr("\n" + "=" * 160)
    pr("SECTION B -- F7 census. (1) FIXED threshold 103 wire (the r32/r33 report's census); (2) highangle_stutter.py's own per-route threshold (r32 103, r33 130, r34 100)")
    pr("=" * 160)
    for tag in ROUTES:
        r = routes[tag]
        eps = ST.fixed_thr_episodes(r)
        hi = [e for e in eps if e["ang"] >= 30]
        f7 = [e for e in hi if e["fdom"] >= 6]
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS)
        pr("%s: engaged %.0f s, high-angle %.1f s | FIXED-103: episodes %d (%.1f s); >=30 deg %d (%.1f s); F7 %d (%.1f s) = %.1f per 100 s high-angle; F7 rate amp median %.0f wire; fdom %s"
           % (tag, r.eng.sum() / FS, hs, len(eps), sum(e["dur"] for e in eps), len(hi), sum(e["dur"] for e in hi), len(f7), sum(e["dur"] for e in f7),
              100 * len(f7) / hs, np.median([e["ramp"] for e in f7]) if f7 else np.nan, " ".join("%.1f" % e["fdom"] for e in hi)))
        own = ST.EPIS[tag]; f7o = [x for x in own if x[2] >= 6]
        pr("     highangle_stutter own-threshold list: %d at >=30 deg, F7 %d (%.1f s) = %.1f per 100 s" % (len(own), len(f7o), sum(x[1] for x in f7o), 100 * len(f7o) / ST.HIGH_ANG_S[tag]))
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 200)
        runs = V.runs(m, 100)
        a7 = ST.band_amp(r.wire[runs]) / V.CPD if runs.sum() > 100 else np.nan
        pr("     |angle|>=30 & idx>=200: %.1f s; rate 6-8.5 Hz amp over >=1 s runs %.1f deg/s; driver-torque ring %.0f raw; cmd 6-8.5 Hz amp %.0f"
           % (m.sum() / FS, a7, ST.band_amp(r.tq_raw[runs]) if runs.sum() > 100 else np.nan, ST.band_amp(r.cmd[runs]) if runs.sum() > 100 else np.nan))
        for lo, hi_ in ((0, 3), (3, 6), (6, 10), (10, 99)):
            mm = r.eng & (np.abs(r.ang) >= 30) & (r.vego >= lo) & (r.vego < hi_)
            pr("       high-angle time at v %2d-%2d m/s: %5.1f s" % (lo, hi_, mm.sum() / FS))

    # ---------------------------------------------------------------------------------------------- C
    pr("\n" + "=" * 160)
    pr("SECTION C -- episodes (|angle|>=30, engaged) through the V280 rev 2 chain (line x6, clamp 46080, gain 5346, cap 3072), open loop on the measured rate")
    pr("  cols: corr = sim-vs-tap; Prail/Drail/fbclp/cliff = duty; brake sim/meas; rAmp = rate 6-8.5 Hz amp deg/s; rip/L = T 6-8.5 Hz amp / |T| p50; cAmp7 = 0xE4 cmd 6-8.5 Hz amp; tqRng = driver torque 6-8.5 Hz amp raw")
    pr("=" * 160)
    pooled = {}
    for tag in ROUTES:
        r = routes[tag]
        Rb = sim(r, *V280R2); Rkd0 = sim(r, *V280R2, kd=0)
        rows = []
        for (t0, dur, fd) in ST.EPIS[tag]:
            M, a, b = ST.episode_row(r, Rb, t0, dur, fd, Rkd0)
            M["cmd_amp7"] = ST.band_amp(r.cmd[b]); M["cmd_p50"] = float(np.median(np.abs(r.cmd[b])))
            M["cmd_amp_band"] = ST.band_amp(r.cmd[b], 2.0, 8.0)
            rows.append((t0, dur, fd, M))
            pr("  %s t0 %6.1f dur %3.1f fdom %.2f %s ang %4.0f v %3.1f idx %3.0f | corr %.2f | rate %5.1f ref %5.1f r/ref %.2f %-5s | Prail %.2f Drail %.2f fbclp %.2f ocap %.2f cliff %.2f | brake sim %.2f meas %.2f | rAmp %4.1f | rip/L sim %.2f meas %.2f (|T| %4.0f) | rip/L kd=0 %.2f | tqRng %4.0f | cAmp7 %4.0f (2-8 Hz %4.0f, |cmd| %4.0f) | T re rate %+.0f deg | wind %.2f"
               % (tag, t0, dur, fd, "F7" if fd >= 6 else "F2", M["ang"], M["v"], M["idx50"], M.get("corr_T", np.nan), M["rate_p50"], M["ref_p50"], M["rate_over_ref"], M["cls"],
                  M["P_rail"], M["D_rail"], M["clamped"], M["out_cap_sim"], M["cliff"], M["E_brake"], M["brake_meas"], M["rate_amp"], M["Tsim_ripple_level"], M["Tmeas_ripple_level"], M["absT_meas_p50"],
                  M["amp7_Tsim_kd0"] / max(M["absT_sim_p50"], 1), M["tq_ring"], M["cmd_amp7"], M["cmd_amp_band"], M["cmd_p50"], M["ph_Tmeas_re_rate"], M["winding"]))
        f7 = [x for x in rows if x[2] >= 6]
        pooled[tag] = f7
        if f7:
            med = lambda k: np.median([x[3][k] for x in f7])  # noqa: E731
            rng = lambda k: (min(x[3][k] for x in f7), max(x[3][k] for x in f7))  # noqa: E731
            cls = [x[3]["cls"] for x in f7]
            pr("  %s F7 SUMMARY: n %d (%.1f s) STALL %d ATREF %d ABOVE %d | fdom med %.2f | rate/ref med %.2f (%.2f-%.2f) | Prail med %.2f (%.2f-%.2f) | rAmp med %.1f (%.1f-%.1f) | rip/L meas med %.2f (%.2f-%.2f) | |T| med %.0f | tqRng med %.0f (%.0f-%.0f) | cAmp7 med %.0f (%.0f-%.0f) | cliff med %.2f | corr med %.2f | idx med %.0f (%.0f-%.0f)"
               % (tag, len(f7), sum(x[1] for x in f7), cls.count("STALL"), cls.count("ATREF"), cls.count("ABOVE"), np.median([x[2] for x in f7]),
                  med("rate_over_ref"), *rng("rate_over_ref"), med("P_rail"), *rng("P_rail"), med("rate_amp"), *rng("rate_amp"), med("Tmeas_ripple_level"), *rng("Tmeas_ripple_level"),
                  med("absT_meas_p50"), med("tq_ring"), *rng("tq_ring"), med("cmd_amp7"), *rng("cmd_amp7"), med("cliff"), med("corr_T"), med("idx50"), *rng("idx50")))

    # ---------------------------------------------------------------------------------------------- D
    pr("\n" + "=" * 160)
    pr("SECTION D -- pre-registered statistics on r32/r33/r34 (V280 rev 2 chain for ref / P-rail)")
    pr("=" * 160)
    for tag in ROUTES:
        r = routes[tag]; R = sim(r, *V280R2)
        rows = ST.stat_i(r, R)
        if rows:
            pr("%s (i): %d runs, %.1f s; ratio p50 %.2f (p10-p90 %.2f-%.2f); amp p50 %.0f; |T| level p50 %.0f; tq ring p50 %.0f raw; rate p50 %.1f vs ref %.1f; P-rail med %.2f; runs >= 0.45: %d"
               % (tag, len(rows), sum(x["dur"] for x in rows), np.median([x["ratio"] for x in rows]), np.percentile([x["ratio"] for x in rows], 10),
                  np.percentile([x["ratio"] for x in rows], 90), np.median([x["amp"] for x in rows]), np.median([x["lvl"] for x in rows]),
                  np.median([x["tq_ring"] for x in rows]), np.median([x["rate"] for x in rows]), np.median([x["ref"] for x in rows]), np.median([x["Prail"] for x in rows]),
                  sum(1 for x in rows if x["ratio"] >= 0.45)))
            for x in rows:
                pr("    t0 %6.1f dur %4.1f ang %4.0f v %4.1f | amp %4.0f lvl %5.0f ratio %.2f | tq ring %5.0f | rate %5.1f ref %5.1f (%.2f) Prail %.2f%s"
                   % (x["t0"], x["dur"], x["ang"], x["v"], x["amp"], x["lvl"], x["ratio"], x["tq_ring"], x["rate"], x["ref"], x["rate"] / max(x["ref"], 1), x["Prail"],
                      "  <-- >= 0.45" if x["ratio"] >= 0.45 else ""))
        else:
            pr("%s (i): no runs" % tag)
        # (ii) over the same frame set
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 200); runs = V.runs(m, 100)
        pr("%s (ii): driver-torque 6-8.5 Hz amp over (i)'s frame set %.0f raw" % (tag, ST.band_amp(r.tq_raw[runs]) if runs.sum() > 100 else np.nan))
        # (iv)/(v)
        o = ST.stat_iv(r)
        pr("%s (iv) ceil %.1f | " % (tag, V.ceiling_degs(V280R2[0])) + " | ".join("<%4d: n=%4d %5.1f/%5.1f" % (t, *o[t]) for t in (2240, 1000, 400, 200))
           + " | (v) tap |T| p50/p90 %.0f/%.0f (tq<400); v50 %.1f" % (o["tap"][0], o["tap"][1], o["v"]))
        pr("      tq<400 split: WINDING in  n=%4d rate %5.1f/%5.1f |ang| %3.0f v %4.1f |T| %4.0f   |   RETURNING n=%4d rate %5.1f/%5.1f |ang| %3.0f v %4.1f |T| %4.0f" % (*o["wind"], *o["return"]))
        # (vi), (viii)
        m = r.eng & (np.abs(r.cmd) < 1300) & (r.T_meas != 0) & (r.wire != 0)
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz"))); t0 = D["t18"][0]
        e1 = np.interp(D["t1ab"] - t0, r.tg, r.eng.astype(float)) > 0.5
        pr("%s (vi) %.3f (n=%d) | (viii) %.4f, max |field| %d, field==313 anywhere: %d" % (
            tag, np.mean(np.sign(r.T_meas[m]) != np.sign(r.wire[m])), m.sum(), np.mean((r.fld[e1] & 511) >= 309), (r.fld[e1] & 511).max(), int(np.sum(r.fld == 313))))
        # 3.9 Hz / low-frequency sanity on the tap: 2-5 Hz rate amp on straight roads engaged, >= 8 m/s
        st = r.eng & (np.abs(r.ang) < 5) & (r.vego >= 8); runs = V.runs(st, 512)
        pr("%s straight >=8 m/s engaged %.0f s: rate 2-4 Hz amp %.1f deg/s, 3.5-4.3 Hz %.1f, 6-8.5 Hz %.1f; cmd 2-4 Hz amp %.0f" % (
            tag, st.sum() / FS, ST.band_amp(r.wire[runs], 2, 4) / V.CPD, ST.band_amp(r.wire[runs], 3.5, 4.3) / V.CPD, ST.band_amp(r.wire[runs]) / V.CPD, ST.band_amp(r.cmd[runs], 2, 4)) if runs.sum() > 512 else "%s: no straight runs" % tag)

    # ---------------------------------------------------------------------------------------------- E
    pr("\n" + "=" * 160)
    pr("SECTION E -- exposure: engaged / manual time by speed; manual = NOT (0x18F b4.3 AND 0xE4 b2.7); grinding proxy = 15-22 Hz rate band amp manual vs engaged at matched speed")
    pr("=" * 160)
    for tag in ROUTES:
        r = routes[tag]
        man = ~r.eng
        pr("%s engaged %.0f s, manual %.0f s (SCA only %.0f s, REQ only %.0f s)" % (tag, r.eng.sum() / FS, man.sum() / FS, (r.sca & ~r.req).sum() / FS, (r.req & ~r.sca).sum() / FS))
        for lo, hi_ in ((1, 8), (8, 18), (18, 99)):
            vb = (r.vego >= lo) & (r.vego < hi_)
            me, mm = r.eng & vb, man & vb & (np.abs(r.tq_raw) > 0)
            re_, rm = V.runs(me, 256), V.runs(mm, 256)
            ae = ST.band_amp(r.wire[re_], 15, 22) / V.CPD if re_.sum() > 512 else np.nan
            am = ST.band_amp(r.wire[rm], 15, 22) / V.CPD if rm.sum() > 512 else np.nan
            a6e = ST.band_amp(r.wire[re_], 6, 9) / V.CPD if re_.sum() > 512 else np.nan
            a6m = ST.band_amp(r.wire[rm], 6, 9) / V.CPD if rm.sum() > 512 else np.nan
            pr("   v %2d-%2d: engaged %5.1f s (runs %5.1f s) manual %5.1f s (runs %5.1f s) | rate 15-22 Hz amp eng %.2f man %.2f deg/s | 6-9 Hz eng %.2f man %.2f"
               % (lo, hi_, me.sum() / FS, re_.sum() / FS, mm.sum() / FS, rm.sum() / FS, ae, am, a6e, a6m))

    out = os.path.join(HERE, "_scratch", "strongturn_r34.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
