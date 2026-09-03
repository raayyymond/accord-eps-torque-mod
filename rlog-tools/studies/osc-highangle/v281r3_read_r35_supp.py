# -*- coding: utf-8 -*-
"""studies/osc-highangle/v281r3_read_r35_supp.py -- supplement to v281r3_read_r35.py (subagent v281read, 2026-09-03):
  S1  statistic (k) SPEED-MATCHED (the r35 dead frames sit at 11.7 m/s, r34's at 7.4): dead fraction by speed x idx cell
  S2  the stalled-wheel census of section 2 (e) on r31 (V278 rev 3, the stutter build) for scale, same code
  S3  on curves: frames where the controller is UNDER by its OWN instrument (dir*(des - m) > 0.1) -- the only frames where an
      EPS deadband can limit lat accel -- their share, dead fraction and tap |T|, r34 vs r35; and each r35 stall run against
      the controller's state at that moment
  S4  lane-change windows on r35 at any speed
Run: python v281r3_read_r35_supp.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v281r3_read_r35 as M  # noqa: E402  (registers r35 everywhere; no main)

V, ST, B, L, CO = M.V, M.ST, M.B, M.L, M.CO
FS, CPD = M.FS, M.CPD
LINES = []


def pr(s=""):
    print(s); LINES.append(s)


def main():
    routes = {t: V.Route(t) for t in ("r31", "r32", "r33", "r34", "r35")}
    grids = {t: B.grid(B.load(t)) for t in ("r32", "r33", "r34", "r35")}
    # ------------------------------------------------------------------------------------------ S1
    pr("=" * 150)
    pr("S1 -- statistic (k) SPEED-MATCHED: engaged & |angle| > 10 & hands-light |tq| < 400 ; dead = |0x18F rate| < 1 deg/s ; cells = speed x demand index")
    pr("=" * 150)
    for tag in ("r32", "r33", "r34", "r35"):
        r = routes[tag]; R = M.sim(r, *M.V280R2, kp=M.KP_OF[tag])
        ref = R["ref_deg"][r.i100]
        for vlo, vhi in ((3, 8), (8, 12), (12, 20), (20, 40)):
            cells = []
            for lo, hi in ((10, 20), (20, 40), (40, 80)):
                s = r.eng & (np.abs(r.ang) > 10) & (np.abs(r.tq_raw) < 400) & (r.idx >= lo) & (r.idx < hi) & (r.vego >= vlo) & (r.vego < vhi)
                if s.sum() < 50:
                    cells.append("idx %2d-%2d: -- (%.1f s)" % (lo, hi, s.sum() / FS)); continue
                dead = np.abs(r.wire[s]) < CPD
                cells.append("idx %2d-%2d: %5.1f s dead %.3f |T| dead/moving %4.0f/%4.0f ref %4.1f rate %4.1f" % (
                    lo, hi, s.sum() / FS, dead.mean(), np.median(np.abs(r.T_meas[s][dead])) if dead.any() else np.nan, np.median(np.abs(r.T_meas[s][~dead])) if (~dead).any() else np.nan,
                    np.median(ref[s]), np.median(np.abs(r.wire[s]) / CPD)))
            pr("  %s v %2d-%2d | %s" % (tag, vlo, vhi, " | ".join(cells)))
    # ------------------------------------------------------------------------------------------ S2
    pr("\n" + "=" * 150)
    pr("S2 -- stalled-wheel runs (|angle| >= 30, idx 40-240, rate/ref < 0.5, |tq| p50 < 1000, >= 1 s) on r31 (V278 rev 3: map x2 / clamp 15360 for the reference) with the same code as section 2 (e)")
    pr("=" * 150)
    r = routes["r31"]; R = M.sim(r, *ST.REV3, kp=M.KP_STOCK)
    st_all = M.moving_runs(r, R, 40)
    stalls = [x for x in st_all if (not x["moving"]) and x["tq50"] < 1000]
    pr("  r31: %d stalled runs, %.1f s ; stutter signature (6-8.5 Hz rate amp >= 10 deg/s) %d ; |T| p50 %.0f ; idx p50 %.0f ; rate amp median %.1f ; v median %.1f" % (
        len(stalls), sum(x["dur"] for x in stalls), sum(1 for x in stalls if x["rate_amp"] >= 10), M.med([x["lvl"] for x in stalls]), M.med([x["idx"] for x in stalls]),
        M.med([x["rate_amp"] for x in stalls]), M.med([x["v"] for x in stalls])))
    for x in sorted(stalls, key=lambda x: -x["dur"])[:10]:
        pr("     t0 %6.1f dur %4.1f idx %3.0f ang %4.0f v %4.1f | rate %5.1f ref %5.1f r/ref %.2f | |T| %5.0f | tq50 %4.0f | rAmp %4.1f Prail %.2f" % (
            x["t0"], x["dur"], x["idx"], x["ang"], x["v"], x["rate"], x["ref"], x["rr"], x["lvl"], x["tq50"], x["rate_amp"], x["Prail"]))
    # ------------------------------------------------------------------------------------------ S3
    pr("\n" + "=" * 150)
    pr("S3 -- on curves (as section 3): frames where the CONTROLLER IS UNDER by its own instrument, dir*(des - m) > 0.1 (it wants MORE lat accel) vs over/satisfied")
    pr("=" * 150)
    for tag in ("r32", "r33", "r34", "r35"):
        g = grids[tag]
        des = g["desiredLateralAccel"]; m = g["actualLateralAccel"]; pose = g["lat_torqued"]
        ok = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & ~np.isnan(des)
        curve = ok & (np.abs(des) > CO.DES_THR)
        runs = CO.merge_runs(curve, int(1.5 * FS), int(0.3 * FS))
        dirf = np.zeros(len(des)); cm = np.zeros(len(des), bool)
        for a, b in runs:
            d = np.sign(np.median(des[a:b])) or 1.0
            dirf[a:b] = d; cm[a:b] = True
        idx, _ = V.demand(g["cmd"], g["drv18"] * 1.024)
        rate = np.abs(g["rate18"]) / CPD
        em = dirf * (m - des); ep = dirf * (pose - des)
        under = cm & (em < -0.1); over = cm & (em > 0.1); sat = cm & ~under & ~over
        # tap on the backcalc grid: align by logMonoTime (V cache t0 = first 0x18F ; backcalc grid t0 = first carOutput)
        r = routes[tag]
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz"))); Db = B.load(tag)
        off = Db["co_t"][0] - D["t18"][0]
        T_on_grid = np.interp(g["t"] + off, r.tg, np.abs(r.T_meas))
        for lab, s in (("UNDER (wants more)", under), ("satisfied |err_m|<=0.1", sat), ("OVER (wants less)", over)):
            if s.sum() < 50:
                pr("  %s %-24s: %.1f s" % (tag, lab, s.sum() / FS)); continue
            pr("  %s %-24s: %5.1f s (%.2f of curve frames) | err_pose p50 %+.3f err_m %+.3f | idx p50/p90 %3.0f/%3.0f | dead %.3f (idx 20-40: %.3f, idx>=40: %.3f) | tap |T| p50 %4.0f (dead %4.0f / moving %4.0f) | rate p50 %4.1f | v %4.1f | i*dir %+.3f p*dir %+.3f f*dir %+.3f"
               % (tag, lab, s.sum() / FS, s.sum() / max(cm.sum(), 1), M.med(ep[s]), M.med(em[s]), np.median(idx[s]), np.percentile(idx[s], 90), float(np.mean(rate[s] < 1)),
                  float(np.mean(rate[s & (idx >= 20) & (idx < 40)] < 1)) if (s & (idx >= 20) & (idx < 40)).sum() > 20 else np.nan, float(np.mean(rate[s & (idx >= 40)] < 1)) if (s & (idx >= 40)).sum() > 20 else np.nan,
                  M.med(T_on_grid[s]), M.med(T_on_grid[s & (rate < 1)]), M.med(T_on_grid[s & (rate >= 1)]), M.med(rate[s]), M.med(g["v"][s]), M.med(g["i"][s] * dirf[s]), M.med(g["p"][s] * dirf[s]), M.med(g["f"][s] * dirf[s])))
        if tag == "r35":
            pr("  r35 stall runs of section 2 (e) against the controller's state (backcalc grid, aligned):")
            Rr = M.sim(r, *M.V280R2, kp=M.KP_FLAT)
            for x in [y for y in M.moving_runs(r, Rr, 40) if (not y["moving"]) and y["tq50"] < 1000]:
                s = (g["t"] + off >= x["t0"]) & (g["t"] + off < x["t0"] + x["dur"])
                if s.sum() < 10:
                    continue
                d = np.sign(np.median(des[s])) or 1.0
                pr("     t0 %6.1f dur %.1f idx %3.0f v %4.1f | des*dir %+.2f m*dir %+.2f pose*dir %+.2f -> err_m %+.3f err_pose %+.3f | p %+.3f i %+.3f f %+.3f output*dir %+.3f | latActive %.2f pressed %.2f | tap |T| %4.0f rate %4.1f ref %4.1f"
                   % (x["t0"], x["dur"], x["idx"], x["v"], M.med(des[s] * d), M.med(m[s] * d), M.med(pose[s] * d), M.med(d * (m[s] - des[s])), M.med(d * (pose[s] - des[s])),
                      M.med(g["p"][s] * d), M.med(g["i"][s] * d), M.med(g["f"][s] * d), M.med(g["output"][s] * d), float(np.mean(g["lat"][s] > 0.5)), float(np.mean(g["pressed"][s] > 0.5)), x["lvl"], x["rate"], x["ref"]))
    # ------------------------------------------------------------------------------------------ S4
    pr("\n" + "=" * 150)
    pr("S4 -- lane-change windows on r35 at ANY speed (laneChangeState != off, +2 s settle)")
    pr("=" * 150)
    lc = dict(np.load(os.path.join(HERE, "_scratch", "_lc_r35.npz"), allow_pickle=True))
    G = L.load("r35")
    t0 = np.load(os.path.join(HERE, "_scratch", "_ha_%s.npz" % M.PREFIX35))["t18"][0]
    code = np.array([{"off": 0, "preLaneChange": 1, "laneChangeStarting": 2, "laneChangeFinishing": 3}.get(s, 0) for s in lc["lcs"]])
    pr("  laneChangeState census: %s" % dict(zip(*np.unique(lc["lcs"], return_counts=True))))
    on = np.interp(G["t"], lc["tm"] - t0, code) > 0.5
    wins = L.merge_runs(on, 1, int(1.0 * FS))
    for a, b in wins:
        b2 = min(b + int(2 * FS), len(G["t"]))
        ring_runs = L.merge_runs(G["env"][a:b2] > L.ENV_THR, int(0.6 * FS), int(0.5 * FS))
        pr("  t0 %6.1f dur %.1f v %.1f eng %.2f | env pk %.0f amp48 %.1f deg/s %s | tq50 %.0f cmdpk %.0f" % (
            a / FS, (b2 - a) / FS, G["v"][a:b2].mean(), G["eng"][a:b2].mean(), G["env"][a:b2].max(), M.band_amp(G["rate"][a:b2], 4, 8) / CPD, "RING %.1fs" % (sum(y - x for x, y in ring_runs) / FS) if ring_runs else "no-ring",
            np.median(np.abs(G["tq"][a:b2])), np.abs(G["cmd"][a:b2]).max()))
    out = os.path.join(HERE, "_scratch", "v281r3_read_r35_supp.txt")
    open(out, "w", encoding="utf-8").write("\n".join(LINES) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
