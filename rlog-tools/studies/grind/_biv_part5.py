# -*- coding: utf-8 -*-
"""Part 5: SECOND METHOD for the headline.  Re-derive the implied arm with the comparator evaluated at
1 kHz (r24 at its native rate against |T| interpolated to 1 kHz) instead of on the 100 Hz frame axis,
and re-derive the deadband's contribution analytically from the measured v distribution."""
import numpy as np
from b_iv_kappa import pr, J, FS
import b_iv_kappa as M
import bof_v282 as BF
from _biv_part2 import SK, lane_d1k, lane_out

LAD = [1024., 1536., 2048., 2560., 3072., 4096., 5244., 6144., 8192.]
STR = ["creep_1_3med", "creep_1_6med", "loaded_idx68med", "loaded_any", "highway", "all_eng"]


def second_method(G):
    pr("\n" + "=" * 150)
    pr("8. SECOND METHOD -- the comparator evaluated at 1 kHz, not on the 100 Hz frame axis")
    pr("   The ECU compares |r24| >= |T| at 1 kHz.  bof's inversion (and mine in sec 5.3) decimates r24")
    pr("   to 100 Hz and interpolates T from 50 Hz.  If the 0.45 factor were a SAMPLING artefact, the")
    pr("   implied arm would move when the comparison moves to 1 kHz.  Same measured duty on both.")
    pr("=" * 150)
    pr("  %-6s %-17s | %10s | %10s %10s | %8s | %10s %10s"
       % ("route", "stratum", "measured", "arm @100Hz", "arm @1kHz", "ratio", "pred@5244 100", "pred@5244 1k"))
    pr("  " + "-" * 118)
    R = {}
    for t in BF.V282_ROUTES:
        g = G[t]
        n1 = len(g["bar"])
        d1k = lane_d1k(g["bar"])
        n1k = len(d1k)
        # |T| on the 1 kHz axis: the same linear interpolation, evaluated at the 1 kHz tick times
        t1k = np.interp(np.arange(n1k) / 10.0, np.arange(n1), g["t"])
        T1k = np.abs(np.interp(t1k, g["T_t"], g["T"]))
        T100 = np.abs(g["T100"])
        A100 = {gn: np.abs(lane_out(d1k, n1, gn, db=3.0)) for gn in LAD}
        A1k = {}
        for gn in LAD:
            s = np.trunc(d1k * gn / 1024.0)
            s = np.where(np.abs(s) <= 3, 0.0, s - np.sign(s) * 3)
            A1k[gn] = np.abs(np.clip(-s, -8192, 8192))
        gl = np.array(LAD)
        for key in STR:
            m = SK[key](g)
            if m.sum() < 200:
                continue
            m1k = np.repeat(m, 10)[:n1k]
            meas = float(g["bit6"][m].mean())
            p100 = np.array([np.mean((A100[gn] >= T100)[m]) for gn in LAD])
            p1k = np.array([np.mean((A1k[gn][m1k] >= T1k[m1k])) for gn in LAD])

            def inv(p):
                return (float(np.exp(np.interp(meas, p, np.log(gl))))
                        if p[0] <= meas <= p[-1] else float("nan"))
            a100, a1k = inv(p100), inv(p1k)
            i5 = LAD.index(5244.0)
            pr("  %-6s %-17s | %10.4f | %10.0f %10.0f | %8.3f | %13.4f %12.4f"
               % (t, key, meas, a100, a1k, a1k / a100, p100[i5], p1k[i5]))
            R["%s|%s" % (t, key)] = dict(meas=meas, arm100=a100, arm1k=a1k, ratio=float(a1k / a100),
                                         pred100=float(p100[i5]), pred1k=float(p1k[i5]))
    v100 = np.array([R[q]["arm100"] for q in R if np.isfinite(R[q]["arm100"])])
    v1k = np.array([R[q]["arm1k"] for q in R if np.isfinite(R[q]["arm1k"])])
    pr("")
    pr("  100 Hz comparator : implied arm min %.0f  median %.0f  max %.0f   (max/min %.2f)"
       % (v100.min(), np.median(v100), v100.max(), v100.max() / v100.min()))
    pr("  1 kHz  comparator : implied arm min %.0f  median %.0f  max %.0f   (max/min %.2f)"
       % (v1k.min(), np.median(v1k), v1k.max(), v1k.max() / v1k.min()))
    pr("  => kappa @100 Hz = %.4f ;  kappa @1 kHz = %.4f ;  they differ by %.1f %%"
       % (np.median(v100) / 5244, np.median(v1k) / 5244,
          100 * abs(np.median(v1k) / np.median(v100) - 1)))
    J["second_method"] = dict(cells=R, med100=float(np.median(v100)), med1k=float(np.median(v1k)),
                              kappa100=float(np.median(v100) / 5244), kappa1k=float(np.median(v1k) / 5244))

    pr("")
    pr("  8.1 THE DEADBAND's CONTRIBUTION, RE-DERIVED ANALYTICALLY FROM THE MEASURED v DISTRIBUTION")
    pr("      (no ladder, no inversion: just E[(v-3)/v | v>3] * P(v>3) over the measured 1 kHz sample)")
    pr("  %-6s %-17s | %10s %10s %12s | %s" % ("route", "stratum", "P(|v|>3)", "E[(v-3)/v]", "product", "advB needs"))
    for t in BF.V282_ROUTES:
        g = G[t]
        d1k = lane_d1k(g["bar"])
        for key in ("creep_1_3med", "loaded_idx68med", "all_eng"):
            m = SK[key](g)
            if m.sum() < 200:
                continue
            m1k = np.repeat(m, 10)[:len(d1k)]
            v = np.abs(np.trunc(d1k[m1k] * 5244.0 / 1024.0))
            keep = v > 3
            p = float(keep.mean())
            e = float(np.mean((v[keep] - 3.0) / v[keep])) if keep.any() else 0.0
            pr("  %-6s %-17s | %10.4f %10.4f %12.4f | %s"
               % (t, key, p, e, p * e, "0.449"))
    pr("      => the deadband's own multiplicative effect on the lane's DELIVERED magnitude is")
    pr("         0.72-0.93, not 0.449.  advB's mechanism needs the WHOLE 0.449 from this column.")
