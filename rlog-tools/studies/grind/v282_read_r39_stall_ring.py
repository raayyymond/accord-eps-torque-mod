# -*- coding: utf-8 -*-
"""studies/grind/v282_read_r39_stall_ring.py -- Q4 (the P-only DEADBAND / stall census) and Q5 (the 7.3 Hz
strong-turn ring's |L_tot| by the per-episode complex ACF) on r39 (V282, Ki 0), against r35 (V281 rev 3, the
like-for-like Ki-0 baseline), r36/r37/r38 (V283, Ki 50) and r34 (V280 rev 2, stock Kp LERP).

BOTH METRICS ARE THE EXISTING ONES, CALLED DIRECTLY -- nothing invented, no threshold moved:
  Q4  v281r3_read_r35.moving_runs(r, R, idx_lo=40): ENGAGED & |angle| >= 30 & idx >= 40 cut into runs >= 1.0 s;
      a run is STALLED if its MEDIAN rate/ref < 0.5 AND its median |driver torque| < 1000 raw (hands-light).
      This is the function that produced "r35 = 7 stall runs / 14.8 s at idx 54-79" and V283's "1 run / 1.4 s".
      Also reported: prereg (b), the idx 40-80 hands-light wheel rate as a fraction of the map reference, and
      the DELIVERED FRACTION -- the tap's |T| on the stalled frames against the chain's own T under the stock
      Kp LERP on the SAME frames (i.e. "what V280 rev 2's Kp would have delivered here").
  Q5  stutter_v283_ltot_tracked.acf_alpha / episodes_for: |rho(tau)| = exp(-alpha|tau|), Q = pi f0 / alpha,
      |1 - L(j f0)| ~ 1/Q, |L_tot| = 1 - 1/Q on the flat-248 side.  Qualifying: episode >= 0.8 s, >= 6 usable
      lags, ACF fit r2 >= 0.80.  The measured flat-248 pool was |L| = 0.976 [0.944-0.990] over 5 episodes.

CONFOUND: r39 carries the same firmware Kp/Kd/Ki as r35 EXCEPT nothing (V282 = V281r3 + read-only cave bytes),
but a ~1.70x stronger OUTER loop (SR map + SteerKP 0.8).  A stronger outer loop pushes HARDER on a stalled
wheel, so a fall in the stall count is NOT by itself evidence the firmware deadband is gone.  Both the raw
count and the rate/ref distribution it is cut from are reported so the two readings can be separated.

Run: python v282_read_r39_stall_ring.py    Subagent grind39, 2026-09-04.  Analysis only.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OSC = os.path.join(KIT, "rlog-tools", "studies", "osc-highangle")
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, OSC)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import strongturn_r32_r33 as ST          # noqa: E402
import strongturn_r35 as S35             # noqa: E402
import stutter_v283 as SV                # noqa: E402  (registers r36/r37/r38; sim_ki)
import stutter_v283_ltot_tracked as LT   # noqa: E402  (acf_alpha, refine_f0, episodes_for, boot_ci)
import v281r3_read_r35 as R35            # noqa: E402  (registers r35; moving_runs -- the published definition)
import v283_read_r36_r38 as R38          # noqa: E402  (ki_fit -- the CALIBRATED Ki-from-the-tap estimator)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

V = ST.V
FS = ST.FS
CPD = V.CPD
V280R2 = ST.V280R2
KP_FLAT = S35.KP_FLAT["flat 248"]
KP_STOCK = V.KP_Y                     # stock Kp LERP Y knots 248,512,645,696,696 (V280 rev 2 image)

# --------------------------------------------------------------------------------------------- register r39
V.ROUTE_PREFIX["r39"] = "75604b0a432fdc89_00000039--f56039af87"
V.ROUTE_BUILD["r39"] = "V282 Kp flat 248, Ki 0 (new tune: SR map + SteerKP 0.8)"
V.ROUTE_K["r39"] = 6.0
ST.TAP_TAGS.add("r39")

ROUTES = ("r39", "r38", "r37", "r36", "r35", "r34")
GRP = {"r39": "V282", "r38": "V283", "r37": "V283", "r36": "V283", "r35": "V281r3", "r34": "V280r2"}
KI = {"r39": 0, "r38": 50, "r37": 50, "r36": 50, "r35": 0, "r34": 0}
KPY = {t: (KP_STOCK if t == "r34" else KP_FLAT) for t in ROUTES}
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else float("nan")


def main():
    routes, sims = {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        r = V.Route(tag)
        routes[tag] = r
        sims[tag] = SV.sim_ki(r, *V280R2, kpY=KPY[tag], ki=KI[tag])

    pr("=" * 168)
    pr("Q4 (the P-only DEADBAND) and Q5 (the 7.3 Hz ring) on r39 = V282, the Ki-0 base.  Subagent grind39, 2026-09-04.")
    pr("=" * 168)
    pr("  %-5s %-8s %4s %-14s %9s %11s" % ("route", "build", "Ki", "Kp table", "length s", "eng-lat s"))
    for tag in ROUTES:
        r = routes[tag]
        pr("  %-5s %-8s %4d %-14s %9.1f %11.1f" % (
            tag, GRP[tag], KI[tag], "stock LERP" if tag == "r34" else "flat 248",
            len(r.tg) / FS, r.eng.sum() / FS))

    # ================================================================================= Ki attribution
    pr("\n" + "=" * 168)
    pr("0. BUILD ATTRIBUTION -- Ki FITTED FROM THE 427 TAP, by v283_read_r36_r38.ki_fit CALLED DIRECTLY.")
    pr("   T_meas - T_sim(Ki=0) = Ki * [-(254/256)(5346/32768) * lag(J)], J = the Ki=1 accumulator; the slope IS Ki.")
    pr("   r34/r35 ship Ki = 0 and are the NEGATIVE CONTROLS -- they calibrate the method's floor (registered 1.2-1.9).")
    pr("   %-5s %-8s %-9s | %-44s | %s" % ("route", "build", "Ki claimed", "Ki_hat window-median [95% CI] (2 s windows)", "pooled / n"))
    KPT = {t: (V.KP_X, np.asarray(KPY[t], float)) for t in ROUTES}
    for tag in ROUTES:
        f = R38.ki_fit(routes[tag], KPT[tag], 2.0)
        pr("   %-5s %-8s %-9d | %8.2f  [%7.2f - %7.2f]                   | %8.2f / %d" % (
            tag, GRP[tag], KI[tag], f["median"], f["lo"], f["hi"], f["pooled"], f["n"]))

    pr("\n   Kp FITTED FROM THE TAP, by the SAME window-local construction as ki_fit above -- so it inherits its")
    pr("   validation.  With Ki = 0 and no rail, T = -(254/256)(5346/32768) * lag(S), S = P + D and P = E*Kp/256;")
    pr("   so regressing (T_meas - T_sim(Kp = 0, Kd = 128)) on du = -GK*lag(E/256) gives a slope that IS Kp.")
    pr("   Reported BY DEMAND-INDEX BIN, because that is where the stock LERP (248 -> 696) and flat 248 diverge.")
    GK = (V.SUM_MULT / 256.0) * (ST.GAIN / 32768.0)
    KZERO = np.zeros(5)
    pr("   %-5s %-8s %-16s | %s" % ("route", "build", "expected", "Kp_hat window-median by idx bin: 0-40 | 40-90 | 90-140 | 140+"))
    for tag in ROUTES:
        r = routes[tag]
        R0 = SV.sim_ki(r, *V280R2, kpY=KZERO, ki=KI[tag])
        du = (-GK * V.output_lag(R0["E"] / 256.0))[r.i100]
        resid = r.T_meas - R0["T"][r.i100]
        ok = (r.eng & (np.abs(r.tq_raw) < 512) & (np.abs(r.T_meas) < ST.CAP - 8) & (np.abs(R0["D_raw"][r.i100]) < V.D_CLAMP))
        n, stp = 200, 25
        rows = {k: [] for k in ("0-40", "40-90", "90-140", "140+")}
        for a in range(0, len(ok) - n, stp):
            if ok[a:a + n].mean() < 0.98:
                continue
            x, y = du[a:a + n], resid[a:a + n]
            x = x - x.mean(); y = y - y.mean()
            if x.std() < 0.3 or np.sum(x * x) < 1e-6:
                continue
            i50 = float(np.median(r.idx[a:a + n]))
            k = "0-40" if i50 < 40 else ("40-90" if i50 < 90 else ("90-140" if i50 < 140 else "140+"))
            rows[k].append(np.sum(x * y) / np.sum(x * x))
        cells = []
        for k in ("0-40", "40-90", "90-140", "140+"):
            cells.append("%7.0f (n%4d)" % (med(rows[k]), len(rows[k])) if len(rows[k]) >= 8 else "   -- (n%4d)" % len(rows[k]))
        pr("   %-5s %-8s %-16s | %s" % (tag, GRP[tag], "stock 248..696" if tag == "r34" else "flat 248", "  ".join(cells)))
    pr("   [the stock LERP's Y knots are 248 (idx 0), 512 (68), 645 (112), 696 (136+) -- so a stock-Kp route must")
    pr("    RISE across the bins and a flat-248 route must not.  This is the discriminator; the previous naive")
    pr("    whole-route correlation form was tried first and DISCARDED because it preferred 'flat 512' on r34,")
    pr("    whose Kp table is known to be the stock LERP -- a check that condemns a known-truth route is broken.]")

    # ================================================================================= Q4
    pr("\n" + "=" * 168)
    pr("Q4. THE STALL / P-ONLY DEADBAND CENSUS.  v281r3_read_r35.moving_runs(idx_lo = 40), called directly.")
    pr("    STALLED run = engaged & |angle| >= 30 & idx 40-240, >= 1.0 s, MEDIAN rate/ref < 0.5, median |tq| < 1000 raw.")
    pr("    Registered baselines this reproduces: r35 7 runs / 14.8 s ; V283 pooled 1 run / 1.4 s.")
    pr("=" * 168)
    pr("  %-5s %-8s %4s %8s %9s %9s %10s %9s %9s %9s %10s" % (
        "route", "build", "Ki", "ctx runs", "hands-lt", "hl secs", "STALL runs", "stall s", "longest", "idx p50", "|T| p50"))
    STALLS = {}
    for tag in ROUTES:
        r, R = routes[tag], sims[tag]
        runs = R35.moving_runs(r, R, 40)
        light = [x for x in runs if x["tq50"] < 1000]
        st = [x for x in light if not x["moving"]]
        STALLS[tag] = (runs, light, st)
        pr("  %-5s %-8s %4d %8d %9d %9.1f %10d %9.1f %9.1f %9.0f %10.0f" % (
            tag, GRP[tag], KI[tag], len(runs), len(light), sum(x["dur"] for x in light),
            len(st), sum(x["dur"] for x in st), max([x["dur"] for x in st] or [0.0]),
            med([x["idx"] for x in st]), med([x["lvl"] for x in st])))
    pr("\n  the rate/ref distribution the stall gate cuts (hands-light context runs) -- this is what a stronger")
    pr("  OUTER loop moves, and it must be read alongside the count:")
    pr("  %-5s %-8s %6s | %s" % ("route", "build", "n", "median rate/ref: p10  p25  p50  p75  p90"))
    for tag in ROUTES:
        light = STALLS[tag][1]
        rr = np.array([x["rr"] for x in light], float)
        rr = rr[np.isfinite(rr)]
        if len(rr) < 3:
            pr("  %-5s %-8s %6d | (too thin)" % (tag, GRP[tag], len(rr))); continue
        pr("  %-5s %-8s %6d | %s" % (tag, GRP[tag], len(rr),
                                     "  ".join("%.2f" % np.percentile(rr, q) for q in (10, 25, 50, 75, 90))))

    pr("\n  per-stall detail (longest 8 per route):")
    for tag in ROUTES:
        st = sorted(STALLS[tag][2], key=lambda x: -x["dur"])[:8]
        if not st:
            pr("    %-5s %-8s -- no stall runs" % (tag, GRP[tag])); continue
        pr("    %-5s %-8s" % (tag, GRP[tag]))
        for x in st:
            pr("       t0 %7.1f dur %4.1f idx %3.0f ang %4.0f v %4.1f | rate %5.1f ref %5.1f r/ref %.2f | |T| %5.0f | tq50 %4.0f | rAmp %4.1f Prail %.2f"
               % (x["t0"], x["dur"], x["idx"], x["ang"], x["v"], x["rate"], x["ref"], x["rr"], x["lvl"], x["tq50"], x["rate_amp"], x["Prail"]))

    pr("\n  PREREG (b) -- idx 40-80 hands-light wheel rate as a fraction of the map reference (V283's read: r35 36 %, V283 87 %):")
    pr("  %-5s %-8s %9s %9s %9s %9s" % ("route", "build", "rate p50", "ref p50", "fraction", "n runs"))
    for tag in ROUTES:
        light = [x for x in STALLS[tag][1] if 40 <= x["idx"] < 80]
        if len(light) < 2:
            pr("  %-5s %-8s   (n %d -- too thin)" % (tag, GRP[tag], len(light))); continue
        a, b = med([x["rate"] for x in light]), med([x["ref"] for x in light])
        pr("  %-5s %-8s %9.1f %9.1f %8.0f %% %9d" % (tag, GRP[tag], a, b, 100 * a / max(b, 1e-9), len(light)))

    pr("\n  DELIVERED FRACTION on the stalled frames -- the tap's own |T| against the chain's T under the STOCK Kp")
    pr("  LERP (V280 rev 2's Kp) on the SAME frames.  'What V280's Kp would have delivered here.'")
    pr("  %-5s %-8s %10s %12s %10s %9s" % ("route", "build", "|T| meas", "|T| stockKp", "fraction", "frames"))
    for tag in ROUTES:
        r = routes[tag]
        st = STALLS[tag][2]
        if not st:
            pr("  %-5s %-8s   (no stall runs)" % (tag, GRP[tag])); continue
        Rst = SV.sim_ki(r, *V280R2, kpY=KP_STOCK, ki=0)
        m = np.zeros(len(r.tg), bool)
        for x in st:
            m[int(x["t0"] * FS):int((x["t0"] + x["dur"]) * FS)] = True
        Tm = np.abs(r.T_meas[m]); Ts = np.abs(Rst["T"][r.i100][m])
        pr("  %-5s %-8s %10.0f %12.0f %10.2f %9d" % (tag, GRP[tag], med(Tm), med(Ts), med(Tm) / max(med(Ts), 1e-9), m.sum()))

    pr("\n  THE SAME DELIVERED FRACTION over ALL hands-light context runs (not only the stalled ones), so the")
    pr("  number is not conditioned on the very gate it is meant to explain:")
    pr("  %-5s %-8s %10s %12s %10s %9s" % ("route", "build", "|T| meas", "|T| stockKp", "fraction", "frames"))
    for tag in ROUTES:
        r = routes[tag]
        light = STALLS[tag][1]
        if not light:
            continue
        Rst = SV.sim_ki(r, *V280R2, kpY=KP_STOCK, ki=0)
        m = np.zeros(len(r.tg), bool)
        for x in light:
            m[int(x["t0"] * FS):int((x["t0"] + x["dur"]) * FS)] = True
        Tm = np.abs(r.T_meas[m]); Ts = np.abs(Rst["T"][r.i100][m])
        pr("  %-5s %-8s %10.0f %12.0f %10.2f %9d" % (tag, GRP[tag], med(Tm), med(Ts), med(Tm) / max(med(Ts), 1e-9), m.sum()))

    # ================================================================================= Q5
    pr("\n" + "=" * 168)
    pr("Q5. THE 7.3 Hz STRONG-TURN RING -- per-episode complex-ACF fit (STUTTER-7HZ-V283 A14.3), unchanged.")
    pr("    |rho(tau)| = exp(-alpha|tau|) ; Q = pi f0 / alpha ; |1 - L(j f0)| ~ 1/Q ; |L_tot| = 1 - 1/Q on the")
    pr("    flat-248 side (alpha > 0 = decaying), 1 + 1/Q on the stock-Kp side.  Detector: fixed-threshold")
    pr("    episodes at |angle| >= 30 and fdom >= 6 -- threshold 103 on stock-Kp routes, 60 on flat-248 routes.")
    pr("    Registered flat-248 pool: |L| = 0.976 [0.944-0.990] over 5 episodes / ~8 s.")
    pr("=" * 168)
    STOCKT = ("r34",)
    FLATT = ("r39", "r38", "r37", "r36", "r35")
    EPS = {}
    pr("\n  T1 -- per-episode f0 (refined FFT peak on that episode alone, 5-10 Hz search):")
    for tag in STOCKT + FLATT:
        r = routes[tag]
        thr = 103 if tag in STOCKT else 60
        eps = [e for e in ST.fixed_thr_episodes(r, thr=thr) if e["ang"] >= 30 and e["fdom"] >= 6]
        rows = []
        for e in eps:
            a, b = int(e["t0"] * FS), int((e["t0"] + e["dur"]) * FS)
            if b - a < 80:
                continue
            e["a"], e["b"] = a, b
            e["f0"] = LT.refine_f0(r.wire[a:b], 5.0, 10.0)
            rows.append(e)
        EPS[tag] = rows
        pr("    %-5s %-8s thr %3d : %2d episodes, %5.1f s | f0 %s"
           % (tag, GRP[tag], thr, len(rows), sum(x["dur"] for x in rows),
              " ".join("%.2f" % x["f0"] for x in rows) if rows else "--"))

    pr("\n  T2/T3 -- per-episode alpha and Q; QUALIFYING = >= 0.8 s, >= 6 usable ACF lags, fit r2 >= 0.80.")
    pr("  %-5s %-8s %8s %5s %5s | %-20s | %-24s | %s" % (
        "route", "build", "qual s", "eps", "qual", "f0 median (p10-p90)", "Q median [90% CI]", "|L_tot| [90% CI]"))
    RES = {}
    QALL = {}          # every qualifying episode's Q, kept per route EVEN when the route cannot carry its own
    for tag in STOCKT + FLATT:                                    # estimate -- this is what the registered pool used
        r = routes[tag]
        qs, Qs, f0s = 0.0, [], []
        for x in EPS[tag]:
            if x["dur"] < 0.8:
                continue
            al, Q, nl, r2 = LT.acf_alpha(r.wire[x["a"]:x["b"]], x["f0"])
            x["alpha"], x["Q"], x["r2"], x["nlag"] = al, Q, r2, nl
            if not np.isfinite(al) or not np.isfinite(r2) or r2 < 0.80 or nl < 6:
                continue
            qs += x["dur"]; f0s.append(x["f0"])
            if np.isfinite(Q):
                Qs.append(Q)
        QALL[tag] = list(Qs)
        side = +1 if tag in STOCKT else -1
        if len(Qs) >= 2:
            qlo, qhi, nq = LT.boot_ci(Qs)
            Qm = float(np.median(Qs))
            Lm = 1 + side / Qm; Llo, Lhi = 1 + side / qhi, 1 + side / qlo
            RES[tag] = dict(Q=Qm, L=Lm, Llo=min(Llo, Lhi), Lhi=max(Llo, Lhi), n=nq, s=qs, Qs=Qs)
            pr("  %-5s %-8s %8.1f %5d %5d | %5.2f (%4.2f-%4.2f)    | %6.1f [%6.1f-%6.1f]     | %5.3f [%5.3f-%5.3f]" % (
                tag, GRP[tag], qs, len(EPS[tag]), nq, np.median(f0s), np.percentile(f0s, 10), np.percentile(f0s, 90),
                Qm, qlo, qhi, Lm, min(Llo, Lhi), max(Llo, Lhi)))
        else:
            RES[tag] = None
            pr("  %-5s %-8s %8.1f %5d %5d | -- TOO FEW QUALIFYING EPISODES TO CARRY AN ESTIMATE --" % (
                tag, GRP[tag], qs, len(EPS[tag]), len(Qs)))
    for grp, nm, side in ((STOCKT, "STOCK Kp (r34)", +1), (FLATT, "FLAT 248 (r35+r36+r37+r38+r39)", -1),
                          (("r39",), "r39 ALONE (V282, Ki 0)", -1),
                          (("r36", "r37", "r38"), "V283 pool (r36+r37+r38)", -1),
                          (("r35", "r36", "r37", "r38"), "the REGISTERED flat-248 pool (r35-r38, no r39)", -1)):
        pool = [q for t in grp for q in QALL.get(t, [])]
        if len(pool) < 2:
            pr("  POOLED %-34s: too few qualifying episodes (%d)" % (nm, len(pool)))
            continue
        qlo, qhi, nq = LT.boot_ci(pool)
        Qm = float(np.median(pool))
        pr("  POOLED %-34s n %2d : Q %6.1f [%6.1f-%6.1f]  =>  |L_tot| %5.3f [%5.3f-%5.3f]" % (
            nm, nq, Qm, qlo, qhi, 1 + side / Qm, min(1 + side / qhi, 1 + side / qlo), max(1 + side / qhi, 1 + side / qlo)))

    pr("\n  per-episode detail on r39 (every detected episode, qualifying or not):")
    pr("    %8s %6s %6s %6s %6s %6s %8s %6s %6s %6s" % ("t0", "dur", "f0", "alpha", "Q", "r2", "nlag", "ang", "v", "ramp"))
    for x in EPS["r39"]:
        pr("    %8.1f %6.1f %6.2f %6.2f %6.1f %6.2f %8d %6.0f %6.1f %6.0f" % (
            x["t0"], x["dur"], x["f0"], x.get("alpha", np.nan), x.get("Q", np.nan), x.get("r2", np.nan),
            x.get("nlag", 0), x["ang"], x["v"], x["ramp"]))

    pr("\n  T4 -- SENSITIVITY of r39's own number to the two knobs that broke the pooled estimator")
    pr("       (peak-selection band; ACF max-lag).  Registered sensitivity on the r35-r38 pool: <= 0.004.")
    for lo, hi in ((5.0, 10.0), (6.0, 8.5), (5.5, 9.5), (6.0, 10.0)):
        cells = []
        for ml in (0.4, 0.6, 0.9):
            pool = []
            r = routes["r39"]
            for e in EPS["r39"]:
                if e["dur"] < 0.8:
                    continue
                f0 = LT.refine_f0(r.wire[e["a"]:e["b"]], lo, hi)
                al, Q, nl, r2 = LT.acf_alpha(r.wire[e["a"]:e["b"]], f0, max_lag_s=ml)
                if np.isfinite(al) and np.isfinite(r2) and r2 >= 0.80 and nl >= 6 and np.isfinite(Q):
                    pool.append(Q)
            cells.append("maxlag %.1f: %s" % (ml, ("|L| %.3f (n%d)" % (1 - 1 / np.median(pool), len(pool))) if len(pool) >= 2 else "n%d --" % len(pool)))
        pr("    band %.1f-%.1f Hz : %s" % (lo, hi, "  ".join(cells)))

    os.makedirs(SCR, exist_ok=True)
    with open(os.path.join(SCR, "v282_read_r39_stall_ring.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote", os.path.join(SCR, "v282_read_r39_stall_ring.txt"))


if __name__ == "__main__":
    main()
