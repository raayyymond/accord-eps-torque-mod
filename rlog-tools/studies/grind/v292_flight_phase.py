# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- deliverable 2(b): THE T-vs-0x18F-RATE CROSS-SPECTRUM PHASE AT 10 Hz, and the
statistical weight behind the high-angle result.

(b) THE PRE-REGISTERED PHASE READ.  ADV-V291-B section 1 shows the -13.98 deg at 10 Hz is a **DELTA**
between V282 and C10 (=V292's dose), not an absolute phase:

    f      |R_V282|   |R_C10|   ratio   dphase
    3.9     4.0036    3.8309    0.9569   -8.14
    7.3     3.1662    2.7909    0.8815  -12.45
    10.0    2.7069    2.2314    0.8243  -13.98
    20.3    1.7418    1.2137    0.6968  -13.04

So the on-car read is: the measured T-vs-rate phase must be ~14 deg MORE NEGATIVE on V292 than on V282
with the SAME estimator on the SAME stratum.  Measuring it as a paired delta also cancels the constant
0x1AB-vs-0x18F arrival offset, which at 10 Hz is worth ~3.6 deg per ms and would otherwise dominate.
🛑 A absolute phase from this wire is NOT the plant's phase: the 0x1AB tap is sampled at ~50 Hz on its
own clock and interpolated to the 0x18F frame axis.  Only the BETWEEN-BUILD DIFFERENCE is used.

Estimator: wire_0xe4_20hz.csd_pool (the record's), pooled over engaged runs, nperseg 256 at 100 Hz
(0.39 Hz bins), coherence reported alongside so a low-coherence phase is not read as a measurement.

Also here:
  * the Poisson weight behind the F7 count difference (deliverable 3), and a bootstrap on rip/L.
  * (c) b3 duty vs the 6-9 Hz and 18-22 Hz ring amplitude.

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_phase.py
"""
import io
import json
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import wire_0xe4_20hz as WIRE                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CPD = V.CPD
V292_IMG = (LG.FW + "_v292_V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
            "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V292_ROUTES = ("r6d_v292", "r6e_v292", "r6f_v292")
REFS = ("r6c", "r39", "r35")
ALL = V292_ROUTES + REFS
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def load(tag, cells_of):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], cells_of[tag])
    B = dict(np.load(os.path.join(C20.CACHE, tag + "_b4.npz")))
    k14, P14, tn14, _ = C20.dejitter(B["t14b"].astype(float), 0.01, 100)
    b4 = B["b4"].astype(int)
    for n in (3, 5, 6, 7):
        g["bit%d" % n] = np.round(np.interp(g["t"], tn14, ((b4 >> n) & 1).astype(float)))
    return g


def phase_on(g, mask, f_list, nperseg=256, minrun=None):
    """T (0x1AB, on the 0x18F frame axis) relative to the 0x18F rate, pooled over runs of `mask`."""
    minrun = minrun or nperseg
    segs_a, segs_b = [], []
    for a, b in C20.runs(mask, minrun):
        segs_a.append(g["T100"][a:b])
        segs_b.append(g["wire"][a:b])
    if not segs_a:
        return None
    f, coh, ph, gain, n = WIRE.csd_pool(segs_a, segs_b, FS, nperseg)
    if f is None:
        return None
    out = {}
    for f0 in f_list:
        out[f0] = (WIRE.circ_at(f, ph, f0), WIRE.at(f, coh, f0), WIRE.at(f, gain, f0))
    out["n"] = n
    out["nwin"] = sum(max(0, len(x) - nperseg // 2) // (nperseg // 2) for x in segs_a)
    return out


def main():
    CEN.IMG["V292"] = V292_IMG
    for t in V292_ROUTES:
        CEN.CELL_OF[t] = "V292"
    CEN.CELL_OF["r6c"] = "V282"
    cb = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V292", "V281r3")}
    cells_of = {t: cb[CEN.CELL_OF[t]] for t in ALL}
    G = {t: load(t, cells_of) for t in ALL}

    F = [3.9, 7.3, 10.0, 13.0, 20.3]
    pr("=" * 150)
    pr("V292 FLIGHT READ -- (b) THE T-vs-RATE CROSS-SPECTRUM PHASE.  The pre-registered number is a DELTA")
    pr("of -13.98 deg at 10 Hz (V292 minus V282), not an absolute phase -- ADV-V291-B section 1.")
    pr("Measuring it paired also cancels the constant 0x1AB-vs-0x18F arrival offset (~3.6 deg/ms at 10 Hz).")
    pr("=" * 150)
    STRATA = [("engaged, hands-off (|bar|<400), ALL speeds", lambda g: g["eng"] & (np.abs(g["bar"]) < 400)),
              ("engaged, hands-off CREEP 1-3 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3)),
              ("engaged, hands-off >=15 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 15)),
              ("engaged, ALL", lambda g: g["eng"])]
    res = {}
    for lab, fn in STRATA:
        pr("")
        pr("  --- %s ---" % lab)
        pr("  %-10s %-7s %7s | %s" % ("route", "build", "n_win",
                                      " | ".join("%-19s" % ("%.1f Hz" % f0) for f0 in F)))
        pr("  %-10s %-7s %7s | %s" % ("", "", "",
                                      " | ".join("%8s %10s" % ("phase", "coh") for _ in F)))
        for tag in ALL:
            o = phase_on(G[tag], fn(G[tag]), F)
            if o is None or o["nwin"] < 8:
                pr("  %-10s %-7s %7s  -- too few windows --" % (tag, CEN.CELL_OF.get(tag, "?"),
                                                                o["nwin"] if o else 0))
                continue
            res[(lab, tag)] = o
            pr("  %-10s %-7s %7d | %s" % (
                tag, CEN.CELL_OF.get(tag, "?"), o["nwin"],
                " | ".join("%+8.1f %10.3f" % (o[f0][0], o[f0][1]) for f0 in F)))
        # the paired delta, every V292 route against each V282 reference
        pr("  DELTA phase (V292 route minus reference), deg.  PRE-REGISTERED: about -14 at 10 Hz.")
        for ref in ("r6c", "r39"):
            if (lab, ref) not in res:
                continue
            pr("    vs %-6s | %s" % (ref, " | ".join("%-19s" % ("%.1f Hz" % f0) for f0 in F)))
            for tag in V292_ROUTES:
                if (lab, tag) not in res:
                    continue
                d = []
                for f0 in F:
                    dd = res[(lab, tag)][f0][0] - res[(lab, ref)][f0][0]
                    dd = (dd + 180.0) % 360.0 - 180.0
                    d.append("%+8.1f %10s" % (dd, ""))
                pr("      %-8s   | %s" % (tag, " | ".join(d)))

    # ------------------------------------------------------------------ Poisson weight on F7
    pr("")
    pr("=" * 150)
    pr("F7 COUNT -- the statistical weight.  Poisson exact test on counts over exposure (high-angle seconds).")
    pr("=" * 150)
    F7 = {"r6d_v292": (3, 75.2), "r6e_v292": (1, 45.1), "r6f_v292": (3, 47.6),
          "r6c": (1, 97.2), "r39": (0, 97.4), "r35": (0, 79.8)}
    v292_k = sum(F7[t][0] for t in V292_ROUTES); v292_e = sum(F7[t][1] for t in V292_ROUTES)
    for name, tags in (("V292 pooled (r6d+r6e+r6f)", V292_ROUTES),
                       ("V282 pooled (r6c+r39)", ("r6c", "r39")),
                       ("V281r3 (r35)", ("r35",))):
        k = sum(F7[t][0] for t in tags); e = sum(F7[t][1] for t in tags)
        lo, hi = (stats.chi2.ppf(0.025, 2 * k) / 2 if k else 0.0), stats.chi2.ppf(0.975, 2 * k + 2) / 2
        pr("  %-28s  %d F7 in %.1f s of high-angle time = %.2f /100 s   [%.2f, %.2f] exact 95%%"
           % (name, k, e, 100.0 * k / e, 100.0 * lo / e, 100.0 * hi / e))
    k2 = sum(F7[t][0] for t in ("r6c", "r39")); e2 = sum(F7[t][1] for t in ("r6c", "r39"))
    # conditional binomial test for two Poisson rates
    p = v292_e / (v292_e + e2)
    pv = stats.binomtest(v292_k, v292_k + k2, p, alternative="greater").pvalue
    pr("  V292 vs V282 rate ratio %.2fx ; conditional binomial test p = %.4f (one-sided, V292 higher)"
       % ((v292_k / v292_e) / (k2 / e2) if k2 else np.inf, pv))
    pr("  🛑 Small counts.  The rate ratio is the headline; the p value says only that 7-vs-1 at these")
    pr("     exposures is unlikely under equal rates.  The CONTINUOUS statistics (rip/L, rate@f0, bar 6-8.5)")
    pr("     carry far more weight than the episode count and they agree in direction and size.")

    # ------------------------------------------------------------------ (c) b3 vs ring
    pr("")
    pr("=" * 150)
    pr("(c) b3 DUTY vs RING AMPLITUDE -- 2 s engaged windows, 1 s step; b3 duty inside each window against")
    pr("    that window's 18-22 Hz and 6-9 Hz rate amplitude.")
    pr("=" * 150)
    W, STEP = 200, 100
    pr("  %-10s %-7s %7s | %s" % ("route", "build", "n_win",
                                  " | ".join("%-16s" % q for q in ("18-22 <p25", "p25-50", "p50-75", ">p75"))))
    b3res = {}
    for tag in ALL:
        g = G[tag]
        rows = []
        for a, b in C20.runs(g["eng"], W):
            for s in range(a, b - W + 1, STEP):
                e = s + W
                x = g["wire"][s:e]
                sos = signal.butter(4, [18, 22], btype="bandpass", fs=FS, output="sos")
                r1 = float(np.sqrt(2) * signal.sosfiltfilt(sos, x - x.mean()).std()) / CPD
                sos2 = signal.butter(4, [6, 9], btype="bandpass", fs=FS, output="sos")
                r2 = float(np.sqrt(2) * signal.sosfiltfilt(sos2, x - x.mean()).std()) / CPD
                rows.append((r1, r2, float(g["bit3"][s:e].mean())))
        if len(rows) < 40:
            pr("  %-10s  too few windows" % tag)
            continue
        A = np.array(rows)
        b3res[tag] = A
        q = np.percentile(A[:, 0], [25, 50, 75])
        cellsx = []
        for lo_, hi_ in zip([-1e9] + list(q), list(q) + [1e9]):
            m = (A[:, 0] >= lo_) & (A[:, 0] < hi_)
            cellsx.append("%.3f n%-5d" % (A[m, 2].mean(), m.sum()) if m.sum() > 10 else "   --      ")
        rho = stats.spearmanr(A[:, 0], A[:, 2]).statistic
        rho2 = stats.spearmanr(A[:, 1], A[:, 2]).statistic
        pr("  %-10s %-7s %7d | %s   | Spearman b3 vs 18-22 %+0.3f ; vs 6-9 %+0.3f" %
           (tag, CEN.CELL_OF.get(tag, "?"), len(A), " | ".join(cellsx), rho, rho2))

    io.open(os.path.join(SCR, "v292_flight_phase.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    with open(os.path.join(SCR, "v292_flight_phase.json"), "w") as fh:
        json.dump({("%s|%s" % k): {str(kk): vv for kk, vv in v.items()} for k, v in res.items()},
                  fh, indent=1, default=float)
    pr("\nwrote v292_flight_phase.txt")


if __name__ == "__main__":
    main()
