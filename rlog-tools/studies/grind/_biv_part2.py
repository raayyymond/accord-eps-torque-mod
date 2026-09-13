# -*- coding: utf-8 -*-
"""Part 2 of b_iv_kappa: the Q1 tables, the instrument diagnostics, and the Q2 deadband test.
Imported and driven by b_iv_kappa.py; kept separate only to keep each file readable."""
import numpy as np

from b_iv_kappa import (FS, FREQS, KEYF, COH_MIN, FGRID, WinPool, ang, pr, J, NPS, NFFT)
import b_iv_kappa as M
import bof_v282 as BF
import creep20_loop_id as C20

SK = {k: fn for k, _, fn in BF.STRATA}
SN = {k: n for k, n, _ in BF.STRATA}
MAIN2 = ("creep_1_3med", "loaded_idx68med")
ALLK = ("bar", "wire", "cmd", "T100")


def build_pool(gs, tags, key, keys=ALLK):
    P = WinPool(keys)
    for t in tags:
        P.add_runs(gs[t], SK[key](gs[t]))
    return P.finish()


# ====================================================================================== 0. CONTROLS
def controls(gc):
    pr("\n" + "=" * 150)
    pr("0. CONTROLS")
    pr("=" * 150)
    Pb, _ = BF.pool_stratum(gc, BF.CTRL_ROUTES, SK["creep_1_3"], ("bar", "wire"), NPS, NFFT)
    Pm = build_pool(gc, BF.CTRL_ROUTES, "creep_1_3", keys=("bar", "wire"))
    dmag, dang, dcoh = [], [], []
    for f0 in FREQS:
        h1b, cb, _ = Pb.bavg("wire", "bar", f0)
        e = Pm.est(f0)
        dmag.append(abs(abs(e["H1"]) / abs(h1b) - 1.0))
        dang.append(abs(((ang(e["H1"]) - ang(h1b) + 180) % 360) - 180))
        dcoh.append(abs(e["coh_dir"] - cb))
    ok = max(dmag) < 1e-9 and max(dang) < 1e-6 and max(dcoh) < 1e-9
    pr("  C0  my per-window pooling vs bof's scipy.csd pooling (r31-r34 creep, 17 frequencies):")
    pr("      max rel |H1| diff %.2e   max angle diff %.2e deg   max coh diff %.2e   windows %d vs %d"
       % (max(dmag), max(dang), max(dcoh), Pm.n, Pb.n))
    pr("      C0 %s" % ("PASS -- same estimator to machine precision" if ok else "*** FAIL ***"))
    J["C0"] = dict(max_rel_mag=float(max(dmag)), max_ang=float(max(dang)), max_coh=float(max(dcoh)),
                   nwin=int(Pm.n), nwin_bof=int(Pb.n), passed=bool(ok))

    Pc = build_pool(gc, BF.CTRL_ROUTES, "creep_1_3")
    f20 = float(FGRID[int(np.argmin(np.abs(FGRID - 20.0)))])
    pr("")
    pr("  C1  POSITIVE CONTROL, record pool r31-r34 creep 1-3 (instantaneous |bar|<400), nearest bin %.2f Hz," % f20)
    pr("      no band average.  THE RECORD: +114 deg, coh 0.94, |B| 2.81.")
    e = Pc.est(f20, half=0.0)
    pr("      pool %.1f s / %d windows" % (Pc.secs, Pc.n))
    pr("      DIRECT   |B| %.2f   ang %+.0f deg   coh(rate,bar) %.2f" % (abs(e["H1"]), ang(e["H1"]), e["coh_dir"]))
    pr("      IV cmd   |B| %.2f   ang %+.0f deg   coh(cmd,bar) %.2f   coh(cmd,rate) %.2f"
       % (abs(e["iv_cmd"]), ang(e["iv_cmd"]), e["cohib_cmd"], e["cohir_cmd"]))
    pr("      IV T427  |B| %.2f   ang %+.0f deg   coh(T,bar)   %.2f   coh(T,rate)   %.2f"
       % (abs(e["iv_T"]), ang(e["iv_T"]), e["cohib_T"], e["cohir_T"]))
    okd = abs(((ang(e["H1"]) - 114 + 180) % 360) - 180) <= 10 and abs(abs(e["H1"]) - 2.8) <= 0.4
    oki = abs(((ang(e["iv_cmd"]) - 114 + 180) % 360) - 180) <= 10
    okt = abs(((ang(e["iv_T"]) - 114 + 180) % 360) - 180) <= 10
    pr("      C1 DIRECT %s | C1 IV(cmd) %s | C1 IV(T427) %s   [brief's gate: +114 +-10 deg, |B| ~ 2.8]"
       % ("PASS" if okd else "FAIL", "PASS" if oki else "FAIL", "PASS" if okt else "FAIL"))
    bt = Pc.boot(f20, ["H1", "iv_cmd", "iv_T"], nboot=600)
    for k, lab in (("H1", "direct"), ("iv_cmd", "iv cmd"), ("iv_T", "iv T427")):
        if k in bt:
            pr("        %-8s 95%% CI   |B| [%.2f, %.2f]   ang [%+.0f, %+.0f] deg"
               % (lab, bt[k]["mag_lo"], bt[k]["mag_hi"], bt[k]["ang_lo"], bt[k]["ang_hi"]))
    J["C1"] = dict(f=f20, secs=Pc.secs, nwin=Pc.n, boot=bt,
                   direct=dict(mag=abs(e["H1"]), ang=ang(e["H1"]), coh=e["coh_dir"], passed=bool(okd)),
                   iv_cmd=dict(mag=abs(e["iv_cmd"]), ang=ang(e["iv_cmd"]), cohb=e["cohib_cmd"],
                               cohr=e["cohir_cmd"], passed=bool(oki)),
                   iv_T=dict(mag=abs(e["iv_T"]), ang=ang(e["iv_T"]), cohb=e["cohib_T"],
                             cohr=e["cohir_T"], passed=bool(okt)))
    return okd


# ====================================================================================== 1. Q1 tables
def q1_tables(G):
    pr("\n" + "=" * 150)
    pr("1. Q1 -- B(f) DIRECT vs INSTRUMENTED, r39 + r6c pooled, on bof's de-biased strata")
    pr("   IV = S_cmd,bar / S_cmd,rate.  The instrument's OWN transfer cancels between numerator and")
    pr("   denominator, so the 0xE4 -> 0x18F-frame interpolation cannot bias the ratio.")
    pr("   IV USABLE requires BOTH coh(cmd,bar) and coh(cmd,rate) >= %.2f." % COH_MIN)
    pr("=" * 150)
    Q1, POOLS = {}, {}
    for key in MAIN2:
        P = build_pool(G, BF.V282_ROUTES, key)
        POOLS[key] = P
        pr("")
        pr("  %s   [%s]" % (SN[key], key))
        pr("  pooled %.1f s / %d Welch windows" % (P.secs, P.n))
        pr("  %6s | %8s %8s %7s | %8s %8s %7s %7s | %-26s | %s"
           % ("f(Hz)", "|B|dir", "ang dir", "coh", "|B|iv", "ang iv", "co i,b", "co i,r",
              "iv 95% CI |B| ; ang", "iv/dir"))
        pr("  " + "-" * 142)
        rows = []
        for f0 in FREQS:
            e = P.est(f0)
            bt = P.boot(f0, ["iv_cmd"], nboot=400)
            ci = bt.get("iv_cmd", {})
            uiv = min(e["cohib_cmd"], e["cohir_cmd"]) >= COH_MIN
            udir = e["coh_dir"] >= COH_MIN
            rat = abs(e["iv_cmd"]) / abs(e["Hv"])
            dph = ((ang(e["iv_cmd"]) - ang(e["H1"]) + 180) % 360) - 180
            pr("  %6.1f | %8.2f %8s %7.2f | %8.2f %8s %7.2f %7.2f | %-26s | x%.2f  %+.0f deg"
               % (f0, abs(e["Hv"]), ("%+.0f" % ang(e["H1"])) if udir else "n/a", e["coh_dir"],
                  abs(e["iv_cmd"]), ("%+.0f" % ang(e["iv_cmd"])) if uiv else "n/a",
                  e["cohib_cmd"], e["cohir_cmd"],
                  ("[%.2f, %.2f] ; [%+.0f, %+.0f]" % (ci["mag_lo"], ci["mag_hi"], ci["ang_lo"], ci["ang_hi"]))
                  if ci else "-", rat, dph))
            rows.append(dict(f=f0, mag_dir=abs(e["Hv"]), mag_dir_H1=abs(e["H1"]), ang_dir=ang(e["H1"]),
                             coh_dir=e["coh_dir"], mag_iv=abs(e["iv_cmd"]), ang_iv=ang(e["iv_cmd"]),
                             coh_iv_bar=e["cohib_cmd"], coh_iv_rate=e["cohir_cmd"], iv_usable=bool(uiv),
                             ratio=float(rat), dphase=float(dph), ci=ci,
                             mag_ivT=abs(e["iv_T"]), ang_ivT=ang(e["iv_T"]),
                             coh_ivT_bar=e["cohib_T"], coh_ivT_rate=e["cohir_T"]))
        Q1[key] = dict(secs=P.secs, nwin=P.n, rows=rows)
    J["Q1_pooled"] = Q1

    pr("")
    pr("  THE 427 T-TAP INSTRUMENT (reported because the brief asked; it is NOT a valid instrument --")
    pr("  T is the servo output, a FUNCTION of the rate, so it is correlated with the feedback by")
    pr("  construction.  It is carried as a NEGATIVE control: a pure function of rate must reproduce")
    pr("  the DIRECT estimate, not correct it.  It is also a 50 Hz stream -- unusable at or above 25 Hz.")
    pr("  %-16s %6s | %8s %8s | %8s %8s %7s %7s" % ("stratum", "f", "|B|dir", "ang dir", "|B|ivT", "ang ivT", "co T,b", "co T,r"))
    for key in MAIN2:
        for r in J["Q1_pooled"][key]["rows"]:
            if r["f"] in (5.0, 7.3, 10.0, 12.0, 14.0, 16.0, 20.3):
                pr("  %-16s %6.1f | %8.2f %+8.0f | %8.2f %+8.0f %7.2f %7.2f"
                   % (key, r["f"], r["mag_dir"], r["ang_dir"], r["mag_ivT"], r["ang_ivT"],
                      r["coh_ivT_bar"], r["coh_ivT_rate"]))

    pr("")
    pr("  PER-ROUTE SPLIT at the anchor frequencies (replication across two routes 1580 s apart)")
    pr("  %-17s %-5s %6s | %8s %8s %6s | %8s %8s %7s %7s"
       % ("stratum", "route", "f", "|B|dir", "ang dir", "coh", "|B|iv", "ang iv", "co i,b", "co i,r"))
    SP = {}
    for key in MAIN2:
        for t in BF.V282_ROUTES:
            P = build_pool(G, (t,), key)
            if P.n < 8:
                continue
            for f0 in KEYF + [12.0]:
                e = P.est(f0)
                pr("  %-17s %-5s %6.1f | %8.2f %+8.0f %6.2f | %8.2f %+8.0f %7.2f %7.2f"
                   % (key, t, f0, abs(e["Hv"]), ang(e["H1"]), e["coh_dir"],
                      abs(e["iv_cmd"]), ang(e["iv_cmd"]), e["cohib_cmd"], e["cohir_cmd"]))
                SP["%s|%s|%g" % (key, t, f0)] = dict(nwin=P.n, mag_dir=abs(e["Hv"]), ang_dir=ang(e["H1"]),
                                                     coh_dir=e["coh_dir"], mag_iv=abs(e["iv_cmd"]),
                                                     ang_iv=ang(e["iv_cmd"]), coh_iv_bar=e["cohib_cmd"],
                                                     coh_iv_rate=e["cohir_cmd"])
    J["Q1_split"] = SP
    return POOLS


# ====================================================================================== 2. instrument diagnostics
def instrument_diag(G, POOLS):
    pr("\n" + "=" * 150)
    pr("2. IS THE 0xE4 COMMAND A VALID INSTRUMENT?  (the record says its 20.03 Hz line is an ECHO)")
    pr("   ALGEBRA, pre-registered: if cmd were a PURE echo, cmd = E*rate, then")
    pr("      S_cmd,bar / S_cmd,rate = conj(E) S_rate,bar / conj(E) S_rate,rate = the DIRECT estimate.")
    pr("   So AGREEMENT between IV and direct is only informative where cmd carries power that rate")
    pr("   does NOT explain.  coh(rate,cmd) IS that echo share: 1.0 = pure echo = IV is degenerate.")
    pr("=" * 150)
    pr("  %-17s %6s | %10s %10s | %12s %12s | %s"
       % ("stratum", "f", "coh(rt,cmd)", "exog share", "tau cmd->rt", "tau rt->cmd", "reading"))
    pr("  " + "-" * 132)
    D = {}
    for key in MAIN2:
        P = POOLS[key]
        # group delay of the cmd -> rate transfer, from a local phase slope on the native grid
        for f0 in FREQS:
            e = P.est(f0)
            ec = P.cross("wire", "cmd", f0)
            cohrc = abs(ec) ** 2 / (P.cross("wire", "wire", f0).real * P.cross("cmd", "cmd", f0).real)
            # local phase slope of cmd->rate across f0 +- 1.0 Hz
            fs_ = [f for f in np.arange(f0 - 1.0, f0 + 1.01, 0.5)]
            ph = np.unwrap([np.angle(P.cross("cmd", "wire", f, half=0.30)) for f in fs_])
            sl = np.polyfit(fs_, ph, 1)[0]
            tau_cr = -sl / (2 * np.pi)            # s ; positive = rate LAGS cmd (forward drive)
            ph2 = np.unwrap([np.angle(P.cross("wire", "cmd", f, half=0.30)) for f in fs_])
            tau_rc = -np.polyfit(fs_, ph2, 1)[0] / (2 * np.pi)
            read = ("PURE ECHO -- IV degenerate" if cohrc >= 0.80 else
                    "mostly echo" if cohrc >= 0.50 else
                    "mixed" if cohrc >= 0.25 else "mostly exogenous")
            pr("  %-17s %6.1f | %10.2f %10.2f | %+10.1f ms %+10.1f ms | %s"
               % (key, f0, cohrc, 1.0 - cohrc, 1e3 * tau_cr, 1e3 * tau_rc, read))
            D["%s|%g" % (key, f0)] = dict(coh_rate_cmd=float(cohrc), exog=float(1 - cohrc),
                                          tau_cmd_rate_ms=float(1e3 * tau_cr), tau_rate_cmd_ms=float(1e3 * tau_rc),
                                          coh_iv_bar=float(e["cohib_cmd"]), coh_iv_rate=float(e["cohir_cmd"]))
        pr("  " + "-" * 132)
    J["instrument"] = D


# ====================================================================================== 3. Q2 -- the deadband
def lane_d1k(bar100):
    """the lane up to and including the pre-gain clamp, at 1 kHz -- computed ONCE per route.
    Verbatim first three statements of v282_r24_tap_read.r24_series."""
    from scipy import signal as sg
    x = sg.resample_poly(bar100 - bar100[0], 10, 1) + bar100[0]
    d = np.zeros_like(x)
    d[4:] = 0.5 * (x[4:] - x[:-4])
    return np.clip(d, -5120, 5120)


def lane_out(d1k, n100, gain, db=3.0, post=1.0):
    """gain -> deadband -> (optional post scale) -> negate -> clamp -> decimate to the 100 Hz frame axis.
    At db=3, post=1 this is byte-identical to r24_series (asserted numerically in 3.0)."""
    s = np.trunc(d1k * gain / 1024.0)
    if db > 0:
        s = np.where(np.abs(s) <= db, 0.0, s - np.sign(s) * db)
    if post != 1.0:
        s = s * post
    return np.clip(-s, -8192, 8192)[::10][:n100]


def deadband_lane(bar100, gain, db=3.0, post=1.0):
    return lane_out(lane_d1k(bar100), len(bar100), gain, db, post)


def q2_deadband(G):
    pr("\n" + "=" * 150)
    pr("3. Q2 -- DOES THE +-3 POST-GAIN DEADBAND EXPLAIN THE 2353-vs-5244 FACTOR?")
    pr("=" * 150)
    pr("  3.0  THE PREMISE, CHECKED FIRST.  ADV-V291-B sec 3.1 says GAIN_EFFECTIVE is 'an artifact of")
    pr("       NOT MODELLING THE DEADBAND'.  bof's ladder is R24 = r24_series(bar, gn), and")
    pr("       v282_r24_tap_read.r24_series line 126 is")
    pr("           s = np.where(np.abs(s) <= 3, 0.0, s - np.sign(s)*3)")
    pr("       -- the deadband IS in the replay, at EVERY rung of the ladder.  [EVIDENCE: source read")
    pr("       + the numerical identity below.]")
    b = G["r39"]["bar"][:200000]
    from v282_r24_tap_read import r24_series as RS
    a1, a2 = RS(b, 5244.0), deadband_lane(b, 5244.0, db=3.0)
    pr("       identity check  max|deadband_lane(db=3) - r24_series| = %.3e over %d frames  %s"
       % (np.max(np.abs(a1 - a2)), len(b), "PASS" if np.max(np.abs(a1 - a2)) < 1e-9 else "FAIL"))
    J["Q2_premise"] = dict(identity=float(np.max(np.abs(a1 - a2))),
                           deadband_in_replay=True)

    STR = ["creep_1_3", "creep_1_3med", "creep_1_6", "loaded_idx68", "loaded_idx68med",
           "loaded_any", "highway", "all_eng"]
    LAD = [256., 512., 768., 1024., 1536., 2048., 2560., 3072., 4096., 5244., 6144., 8192.]
    DBL = [0., 1., 2., 3., 4., 6., 8., 12., 16., 24., 32., 48., 64., 96., 128., 192., 256., 384., 512.]
    POST = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.85, 1.0, 1.3]

    pr("")
    pr("  3.1  THE LANE'S POST-GAIN MAGNITUDE v = |d*5244/1024| AT THE FLOWN ARM, per stratum.")
    pr("       (the quantity advB's mechanism needs to be ~5.4 counts for (v-3)/v = 0.449)")
    pr("  %-6s %-16s %8s | %7s %7s %7s %7s %7s | %8s %8s"
       % ("route", "stratum", "secs", "p50|v|", "p75", "p90", "mean", "p50>0", "frac v<=3", "med |T|"))
    pr("  " + "-" * 118)
    VD = {}
    D1K = {t: lane_d1k(G[t]["bar"]) for t in BF.V282_ROUTES}
    for t in BF.V282_ROUTES:
        g = G[t]
        # v = |post-gain, PRE-deadband| at the flown arm, on the 100 Hz frame axis
        v = np.abs(lane_out(D1K[t], len(g["bar"]), 5244.0, db=0.0))
        for key in STR:
            m = SK[key](g)
            if m.sum() < 200:
                continue
            vv = v[m]
            nz = vv[vv > 0]
            pr("  %-6s %-16s %8.1f | %7.2f %7.2f %7.2f %7.2f %7.2f | %8.3f %8.1f"
               % (t, key, m.sum() / FS, np.median(vv), np.percentile(vv, 75), np.percentile(vv, 90),
                  vv.mean(), np.median(nz) if len(nz) else 0.0, np.mean(vv <= 3.0),
                  np.median(np.abs(g["T100"][m]))))
            VD["%s|%s" % (t, key)] = dict(secs=float(m.sum() / FS), p50=float(np.median(vv)),
                                          p75=float(np.percentile(vv, 75)), p90=float(np.percentile(vv, 90)),
                                          mean=float(vv.mean()), frac_le3=float(np.mean(vv <= 3.0)),
                                          medT=float(np.median(np.abs(g["T100"][m]))))
    J["Q2_vdist"] = VD

    pr("")
    pr("  3.2  FOUR PARAMETERISATIONS OF THE SAME GAP, each inverted onto the MEASURED bit-6 duty.")
    pr("       (a) ARM     : arm free,      deadband 3   [bof's -- the deadband is already in it]")
    pr("       (b) ARM|db0 : arm free,      deadband 0   [how much of (a) the deadband itself buys]")
    pr("       (c) DB      : arm 5244,      deadband free -- advB's mechanism, solved for its own threshold")
    pr("       (d) POST    : arm 5244, db 3, post-deadband scale free  [a pure output scale]")
    pr("       (e) TSCALE  : arm 5244, db 3, |T| scaled -- the '427 tap is wrong' branch")
    pr("  %-6s %-16s %8s | %8s %8s | %8s | %8s | %8s | %8s"
       % ("route", "stratum", "measured", "(a) arm", "(b) arm db0", "(c) db", "(d) post", "(e) Tscale", "pred@5244"))
    pr("  " + "-" * 122)
    R = {}
    for t in BF.V282_ROUTES:
        g = G[t]
        dk, n1 = D1K[t], len(g["bar"])
        Aarm = {gn: lane_out(dk, n1, gn, db=3.0) for gn in LAD}
        Aarm0 = {gn: lane_out(dk, n1, gn, db=0.0) for gn in LAD}
        Adb = {d: lane_out(dk, n1, 5244.0, db=d) for d in DBL}
        Apo = {p: lane_out(dk, n1, 5244.0, db=3.0, post=p) for p in POST}
        for key in STR:
            m = SK[key](g)
            if m.sum() < 200:
                continue
            Tm = np.abs(g["T100"])
            meas = float(g["bit6"][m].mean())

            def inv(series, grid, logx=True):
                p = np.array([np.mean((np.abs(series[k]) >= Tm)[m]) for k in grid])
                gx = np.array(grid, float)
                o = np.argsort(p)
                if not (p.min() <= meas <= p.max()):
                    return float("nan"), p
                if logx:
                    return float(np.exp(np.interp(meas, p[o], np.log(np.maximum(gx[o], 1e-6))))), p
                return float(np.interp(meas, p[o], gx[o])), p

            arm, p_arm = inv(Aarm, LAD)
            arm0, _ = inv(Aarm0, LAD)
            db, _ = inv(Adb, DBL, logx=False)
            po, _ = inv(Apo, POST)
            # (e) |T| scale: duty(|r24@5244| >= s*|T|) = meas  ->  solve s
            r5 = np.abs(Aarm[5244.0])[m]; Tmm = Tm[m]
            sg_ = np.array([0.5, 0.8, 1.0, 1.3, 1.6, 2.0, 2.5, 3.0, 4.0, 6.0, 9.0])
            ps = np.array([np.mean(r5 >= s * Tmm) for s in sg_])
            o = np.argsort(ps)
            ts = float(np.exp(np.interp(meas, ps[o], np.log(sg_[o])))) if ps.min() <= meas <= ps.max() else float("nan")
            pred5244 = float(np.mean((np.abs(Aarm[5244.0]) >= Tm)[m]))
            pr("  %-6s %-16s %8.4f | %8.0f %8.0f | %8.1f | %8.3f | %8.2f | %8.4f"
               % (t, key, meas, arm, arm0, db, po, ts, pred5244))
            R["%s|%s" % (t, key)] = dict(meas=meas, arm=arm, arm_db0=arm0, db=db, post=po, tscale=ts,
                                         pred5244=pred5244)
    J["Q2_invert"] = R

    pr("")
    pr("  3.3  THE INVARIANCE TEST.  A CONSTANT SCALE must give a stratum-INVARIANT parameter; the")
    pr("       DEADBAND's effect depends on the lane amplitude v, which varies across strata, so a")
    pr("       deadband explanation must show a LARGER spread in (c) than in (a)/(d).")
    pr("       dispersion = max/min over the 8 strata x 2 routes, and sd of ln(parameter).")
    pr("  %-10s %10s %10s %10s %10s %8s" % ("param", "min", "median", "max", "max/min", "sd ln"))
    pr("  " + "-" * 66)
    DISP = {}
    for nm, k in (("(a) arm", "arm"), ("(b) arm db0", "arm_db0"), ("(c) deadband", "db"),
                  ("(d) post", "post"), ("(e) Tscale", "tscale")):
        v = np.array([R[q][k] for q in R if np.isfinite(R[q][k])])
        if len(v) < 4:
            continue
        pr("  %-10s %10.3f %10.3f %10.3f %10.2f %8.3f"
           % (nm, v.min(), np.median(v), v.max(), v.max() / max(v.min(), 1e-9), np.std(np.log(np.maximum(v, 1e-9)))))
        DISP[k] = dict(n=int(len(v)), min=float(v.min()), med=float(np.median(v)), max=float(v.max()),
                       ratio=float(v.max() / max(v.min(), 1e-9)), sdln=float(np.std(np.log(np.maximum(v, 1e-9)))))
    J["Q2_dispersion"] = DISP
    return R, VD


def q2_tscale(G):
    """(f) The third branch: is the 427 tap's SCALE right?  Measure |T|/|rate| off the wire and compare
    to r24_lane.servo(f), the byte-exact V282 servo arm."""
    pr("")
    pr("  3.4  THE THIRD BRANCH -- IS THE 427 T TAP's SCALE RIGHT?  If |T| is under-read, the comparator")
    pr("       is mis-scaled and the ARM is innocent.  Measured rate -> T transfer off the wire vs the")
    pr("       byte-exact V282 servo arm r24_lane.servo(f).  T is a 50 Hz stream: only f << 25 Hz is usable.")
    import r24_lane as RL
    pr("  %-17s %6s | %10s %10s %7s | %10s %10s | %8s"
       % ("stratum", "f", "|T/rate|", "ang", "coh", "|servo(f)|", "ang", "ratio"))
    pr("  " + "-" * 96)
    TS = {}
    for key in MAIN2:
        P = build_pool(G, BF.V282_ROUTES, key)
        for f0 in (5.0, 7.3, 10.0, 12.0, 14.0, 16.0, 18.0, 20.3):
            Sxy = P.cross("wire", "T100", f0)
            Sxx = P.cross("wire", "wire", f0).real
            Syy = P.cross("T100", "T100", f0).real
            H = Sxy / Sxx
            coh = abs(Sxy) ** 2 / (Sxx * Syy)
            sv = RL.servo(f0)
            pr("  %-17s %6.1f | %10.3f %+10.0f %7.2f | %10.3f %+10.0f | %8.2f"
               % (key, f0, abs(H), ang(H), coh, abs(sv), ang(sv), abs(H) / abs(sv)))
            TS["%s|%g" % (key, f0)] = dict(magH=float(abs(H)), angH=ang(H), coh=float(coh),
                                           mag_servo=float(abs(sv)), ang_servo=ang(sv),
                                           ratio=float(abs(H) / abs(sv)))
    J["Q2_tscale"] = TS
    return TS
