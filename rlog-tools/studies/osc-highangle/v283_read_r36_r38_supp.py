# -*- coding: utf-8 -*-
"""studies/osc-highangle/v283_read_r36_r38_supp.py -- supplement to v283_read_r36_r38.py (subagent v283read, 2026-09-03).

S1  WIND-UP measured on the wire: the tap's ramp rate in held-error windows, against the prediction 0.1565*excess*Ki
S2  the accumulator AFTER a disengage: the tap's decay time constant (adversary B predicted a 0.1-1.0 s clearing delay)
S3  THE DELIVERED-RATE RATIO -- the mechanism behind the operator's "consistently oversteers": what fraction of the
    map's rate reference the EPS actually delivers, by demand index, r34 / r35 (Ki 0) vs r36 / r37 / r38 (Ki 50)
S4  ROAD-TRUTH curvature tracking, independent of SteerRatio: achieved yaw/v against controlsState.desiredCurvature

Run: python v283_read_r36_r38_supp.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v283_read_r36_r38 as M  # noqa: E402  (registers r35-r38; no main)

V, ST, B = M.V, M.ST, M.B
FS, CPD = M.FS, M.CPD
ALL, NEW = M.ALL, M.NEW
LINES = []


def pr(s=""):
    print(s); LINES.append(s)


def main():
    routes = {t: V.Route(t) for t in ALL}
    sims = {t: M.sim(routes[t], M.KP_OF[t], M.KI_OF[t]) for t in ALL}

    # ------------------------------------------------------------------------------------------ S1
    pr("=" * 165)
    pr("S1 -- WIND-UP MEASURED ON THE WIRE.  In a held rate error the integral term gains excess*Ki/1024 per 1 ms tick,")
    pr("      so the delivered torque must RAMP at 0.1565 * |excess| * Ki tap counts/s.  Windows: >= 1.0 s, engaged,")
    pr("      hands-light (|tq_raw| < 512), the chain's excess same-signed throughout, tap unrailed, |excess| >= 8.")
    pr("      The measured ramp is the DIRECT reading of Ki -- no chain replay, no accumulator reconstruction.")
    pr("=" * 165)
    pr("      %-5s %-7s | %-38s | %-24s | %s" % ("route", "Ki fit", "measured d(signed T)/dt counts/s p50 [IQR]", "predicted at the fit", "n windows / |excess| p50"))
    for tag in ALL:
        r, R = routes[tag], sims[tag]
        ex = M.excess_of(R["E"])[r.i100]
        ok = (r.eng & (np.abs(r.tq_raw) < 512) & (np.abs(r.T_meas) < ST.CAP - 8) & (np.abs(ex) >= 8))
        n = int(1.0 * FS)
        meas, pred, exs = [], [], []
        for a in range(0, len(ok) - n, int(0.25 * FS)):
            sl = slice(a, a + n)
            if ok[sl].mean() < 0.98:
                continue
            s = np.sign(ex[sl])
            if abs(s.mean()) < 0.99:
                continue
            sg = np.sign(np.median(ex[sl]))
            t = np.arange(n) / FS
            meas.append(np.polyfit(t, -sg * r.T_meas[sl], 1)[0])
            e50 = float(np.median(np.abs(ex[sl])))
            pred.append(0.1565 * e50 * M.KI_OF[tag]); exs.append(e50)
        if len(meas) < 10:
            pr("      %-5s %-7d | only %d windows" % (tag, M.KI_OF[tag], len(meas))); continue
        meas, pred = np.array(meas), np.array(pred)
        pr("      %-5s %-7d | %8.0f  [%8.0f, %8.0f]                | %8.0f  [%6.0f,%6.0f] | n %4d, |excess| p50 %.0f"
           % (tag, M.KI_OF[tag], np.median(meas), np.percentile(meas, 25), np.percentile(meas, 75),
              np.median(pred), np.percentile(pred, 25), np.percentile(pred, 75), len(meas), np.median(exs)))

    # ------------------------------------------------------------------------------------------ S2
    pr("\n" + "=" * 165)
    pr("S2 -- THE ACCUMULATOR AFTER A DISENGAGE.  Adversary B (BELIEF) predicted the accumulator clears 0.1-1.0 s AFTER")
    pr("      the disengage because the clear is gated on the engagement ramp.  Tap |T| in 0.25 s bins around every")
    pr("      falling edge of (STEER_CONTROL_ACTIVE & STEER_REQUEST); a Ki-0 build must fall to the noise floor at once.")
    pr("=" * 165)
    bins = [(-0.5, -0.25), (-0.25, 0.0), (0.0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 4.0)]
    pr("      %-5s %-4s | %s" % ("route", "n", "  ".join("%6.2f..%-5.2f" % b for b in bins)))
    for tag in ALL:
        r = routes[tag]
        d = np.diff(np.r_[0, r.eng.astype(int), 0])
        offs = np.flatnonzero(d == -1)
        rows = []
        for k in offs:
            if k < int(1.0 * FS) or k + int(4.5 * FS) >= len(r.T_meas):
                continue
            rows.append([np.median(np.abs(r.T_meas[k + int(lo * FS):k + int(hi * FS)])) for lo, hi in bins])
        if not rows:
            pr("      %-5s   0 | --" % tag); continue
        m = np.median(np.array(rows), axis=0)
        pr("      %-5s %-4d | %s" % (tag, len(rows), "  ".join("%12.0f" % x for x in m)))

    # ------------------------------------------------------------------------------------------ S3
    pr("\n" + "=" * 165)
    pr("S3 -- THE DELIVERED-RATE RATIO: the EPS-side mechanism behind the operator's 'this firmware consistently oversteers'.")
    pr("      For every engaged hands-light frame, the achieved |0x18F rate| over the map's OWN rate reference for that demand")
    pr("      index.  1.00 = the EPS delivers exactly what the LKAS map asked for.  The SteerRatio 12.5 bias is UNCHANGED")
    pr("      across r35 / r36 / r37 / r38 (section 0), so any rise in this ratio lands straight on the road as more steering.")
    pr("=" * 165)
    IDX = ((1, 20), (20, 40), (40, 68), (68, 112), (112, 241))
    pr("      %-5s %-6s | %s" % ("route", "Ki", " | ".join("idx %3d-%3d" % b for b in IDX)))
    ratios = {}
    for tag in ALL:
        r, R = routes[tag], sims[tag]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        cells, row = [], {}
        for lo, hi in IDX:
            m = r.eng & (r.idx >= lo) & (r.idx < hi) & (np.abs(r.tq_raw) < 512) & (ref > 1)
            if m.sum() < 100:
                cells.append("  -- (%4.0f s)" % (m.sum() / FS)); continue
            q = w[m] / ref[m]
            row["%d-%d" % (lo, hi)] = float(np.median(q))
            cells.append("%.2f (%4.0f s)" % (np.median(q), m.sum() / FS))
        ratios[tag] = row
        pr("      %-5s %-6d | %s" % (tag, M.KI_OF[tag], " | ".join("%-12s" % c for c in cells)))
    pr()
    pr("      CHANGE vs r35 (the like-for-like Ki-0 baseline, same tune):")
    for tag in NEW:
        cells = []
        for k in ratios["r35"]:
            if k in ratios[tag]:
                cells.append("idx %-8s %+.2f (x%.2f)" % (k, ratios[tag][k] - ratios["r35"][k], ratios[tag][k] / ratios["r35"][k]))
        pr("        %-5s %s" % (tag, " | ".join(cells)))

    # ------------------------------------------------------------------------------------------ S4
    pr("\n" + "=" * 165)
    pr("S4 -- ROAD-TRUTH CURVATURE TRACKING, INDEPENDENT OF SteerRatio.  achieved = calibrated yaw rate / vEgo (livePose,")
    pr("      torqued's own instrument); asked = controlsState.desiredCurvature.  ratio > 1 = the car turns MORE than asked.")
    pr("      The controller's OWN instrument (controlsState.curvature) is computed through the vehicle model at SteerRatio")
    pr("      12.5, so it over-reads the achieved curvature; both are printed.")
    pr("=" * 165)
    grids = {}
    for tag in ALL:
        try:
            grids[tag] = B.grid(B.load(tag))
        except Exception as e:                                    # noqa: BLE001
            pr("      %s: no backcalc grid (%s)" % (tag, str(e)[:60]))
    pr("      %-5s | %-46s | %-30s | %s" % ("route", "ROAD achieved/asked  p50 [p25, p75]  (secs)", "controller curv/descurv p50", "|asked| p50 1/m"))
    for tag in ALL:
        if tag not in grids:
            continue
        g = grids[tag]
        road = np.where(np.abs(g["v"]) > 1, g["yaw_cal"] / np.maximum(g["v"], 0.1), np.nan)
        ok = ((g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > 5)
              & (np.abs(g["descurv"]) > 0.002) & np.isfinite(road))
        if ok.sum() < 200:
            pr("      %-5s | too few frames (%d)" % (tag, ok.sum())); continue
        q = road[ok] / g["descurv"][ok]
        qc = g["curv"][ok] / g["descurv"][ok]
        q = q[np.isfinite(q)]; qc = qc[np.isfinite(qc)]
        pr("      %-5s | %8.3f  [%7.3f, %7.3f]   (%5.0f s)          | %8.3f                     | %.4f"
           % (tag, np.median(q), np.percentile(q, 25), np.percentile(q, 75), ok.sum() / FS, np.median(qc), np.median(np.abs(g["descurv"][ok]))))
    pr()
    pr("      Same, split by |asked| curvature (the operator drives the road, not the median):")
    for tag in ALL:
        if tag not in grids:
            continue
        g = grids[tag]
        road = np.where(np.abs(g["v"]) > 1, g["yaw_cal"] / np.maximum(g["v"], 0.1), np.nan)
        base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > 5) & np.isfinite(road)
        cells = []
        for lo, hi in ((0.002, 0.005), (0.005, 0.01), (0.01, 0.02), (0.02, 1)):
            m = base & (np.abs(g["descurv"]) >= lo) & (np.abs(g["descurv"]) < hi)
            if m.sum() < 100:
                cells.append("%.3f-%-5.3f   --   " % (lo, hi)); continue
            q = road[m] / g["descurv"][m]
            q = q[np.isfinite(q)]
            cells.append("%.3f-%-5.3f %5.2f (%3.0fs)" % (lo, hi, np.median(q), m.sum() / FS))
        pr("      %-5s | %s" % (tag, " | ".join(cells)))
    out = os.path.join(HERE, "_scratch", "v283_read_r36_r38_supp.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
