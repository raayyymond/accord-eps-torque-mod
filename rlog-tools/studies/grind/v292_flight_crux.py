# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- CRUX VERIFICATION of the high-angle result, by methods that do NOT share the
episode detector.  The F7 census is a THRESHOLD detector on small counts; before that result is relayed
as decision-bearing it has to survive instruments that cannot inherit its threshold.

Four independent checks:
  1  DETECTOR-FREE POOLED SPECTRUM of the 0x18F rate over the whole |angle| >= 30 hands-light stratum,
     as EXCESS dB over a running-median baseline.  If the 7 Hz cycle is back, there is a LINE at ~7 Hz
     in the pooled spectrum with no episode selection anywhere.
  2  THE EXPOSURE CONTROL: speed, angle, demand index and |bar| distributions in that stratum, so a
     "V292 is worse" reading cannot be a different-driving artefact.
  3  THE EXCITATION CONTROL: the same band in the 0xE4 COMMAND.  The openpilot fork and the driving
     model CHANGED between r6c and these routes, so if the command's own 6-9 Hz content is up, the
     result is confounded.  If it is not up, the ripple is EPS-internal.
  4  PAIRED BOOTSTRAP on the continuous statistics (rate@f0, tap rip/L, bar 6-8.5) with CIs.

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_crux.py
"""
import io
import os
import sys

import numpy as np
from scipy import signal

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
import grind1_census_v288_r5e as C88          # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CPD = V.CPD
V292_IMG = (LG.FW + "_v292_V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
            "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V292_ROUTES = ("r6d_v292", "r6e_v292", "r6f_v292")
ALL = V292_ROUTES + ("r6c", "r39", "r35")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def band_amp(x, lo, hi, fs=FS):
    x = np.asarray(x, float)
    if len(x) < 40:
        return np.nan
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return float(np.sqrt(2.0) * signal.sosfiltfilt(sos, x - x.mean()).std())


def main():
    CEN.IMG["V292"] = V292_IMG
    for t in V292_ROUTES:
        CEN.CELL_OF[t] = "V292"
    CEN.CELL_OF["r6c"] = "V282"
    cb = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V292", "V281r3")}
    G = {}
    for t in ALL:
        g = C20.load(t)
        g["tr"] = g["t"] - g["t"][0]
        g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], cb[CEN.CELL_OF[t]])
        G[t] = g
    rng = np.random.default_rng(20260913)

    # the stratum, identical for every route and detector-free
    def strat(g):
        return g["eng"] & (np.abs(g["ang"]) >= 30) & (g["vego"] <= 10) & (np.abs(g["bar"]) < 2240) & (g["idx"] >= 40)

    pr("=" * 150)
    pr("CRUX VERIFICATION -- the high-angle 7 Hz result by methods that do NOT share the F7 detector.")
    pr("Stratum, identical everywhere: engaged AND |angle| >= 30 AND v <= 10 m/s AND |bar| < 2240 AND idx >= 40.")
    pr("=" * 150)

    # ---------------------------------------------------------------- 1. detector-free pooled spectrum
    pr("")
    pr("1.  DETECTOR-FREE POOLED SPECTRUM of the 0x18F rate over the whole stratum (Welch, nperseg 256,")
    pr("    0.39 Hz bins, 50 %% overlap), as EXCESS dB over a +-2 Hz running-median baseline.")
    pr("    No episode selection anywhere.  A returning 7 Hz cycle must show as a LINE near 7 Hz.")
    pr("")
    pr("  %-10s %-7s %7s %7s | %-24s | %-24s | %-24s" %
       ("route", "build", "t s", "n_seg", "peak 5.5-9.5 Hz", "peak 9-13 Hz", "peak 18-22 Hz"))
    pr("  %-10s %-7s %7s %7s | %7s %7s %8s | %7s %7s %8s | %7s %7s %8s" %
       ("", "", "", "", "f", "exc dB", "amp d/s", "f", "exc dB", "amp d/s", "f", "exc dB", "amp d/s"))
    SPEC = {}
    for t in ALL:
        g = G[t]
        m = strat(g)
        runs = [g["wire"][a:b] for a, b in C20.runs(m, 256)]
        f, P = C88.seg_psds(runs, FS, 256)
        if P.shape[0] < 4:
            pr("  %-10s %-7s %7.1f %7d  -- too few segments --" % (t, CEN.CELL_OF.get(t, "?"), m.sum() / FS, P.shape[0]))
            continue
        Pm = P.mean(0)
        ex = C88.excess_db(f, Pm, half_hz=2.0)
        SPEC[t] = (f, P, Pm, ex)
        cells = []
        for lo_, hi_ in ((5.5, 9.5), (9.0, 13.0), (18.0, 22.0)):
            sl = (f >= lo_) & (f <= hi_)
            j = np.argmax(ex[sl])
            amp = np.sqrt(2.0 * Pm[sl][j] * (f[1] - f[0])) / CPD
            cells.append("%7.2f %+7.2f %8.2f" % (f[sl][j], ex[sl][j], amp))
        pr("  %-10s %-7s %7.1f %7d | %s" % (t, CEN.CELL_OF.get(t, "?"), m.sum() / FS, P.shape[0],
                                            " | ".join(cells)))
    pr("")
    pr("  BAND AMPLITUDE RATIOS vs r6c in the same stratum (deg/s; segment bootstrap 95 %% CI):")
    if "r6c" in SPEC:
        f6, P6, _, _ = SPEC["r6c"]
        pr("  %-10s %s" % ("route", "  ".join("%-22s" % ("%s Hz" % b) for b in ("6-9", "9-13", "13-17", "18-22"))))
        for t in ALL:
            if t == "r6c" or t not in SPEC:
                continue
            f_, P_, _, _ = SPEC[t]
            row = []
            for lo_, hi_ in ((6, 9), (9, 13), (13, 17), (18, 22)):
                sl = (f_ >= lo_) & (f_ <= hi_)
                a = P_[:, sl].mean(1); b = P6[:, sl].mean(1)
                rr = np.array([a[rng.integers(0, len(a), len(a))].mean() / b[rng.integers(0, len(b), len(b))].mean()
                               for _ in range(2000)])
                row.append("x%.2f [%.2f,%.2f]" % (np.sqrt(a.mean() / b.mean()),
                                                  np.sqrt(np.percentile(rr, 2.5)), np.sqrt(np.percentile(rr, 97.5))))
            pr("  %-10s %s" % (t, "  ".join("%-22s" % x for x in row)))

    # ---------------------------------------------------------------- 2. exposure control
    pr("")
    pr("=" * 150)
    pr("2.  EXPOSURE CONTROL -- is the stratum the SAME KIND of driving on every route?")
    pr("=" * 150)
    pr("  %-10s %-7s %7s | %14s | %16s | %16s | %16s" %
       ("route", "build", "t s", "speed p10/50/90", "|angle| p10/50/90", "idx p10/50/90", "|bar| p10/50/90"))
    for t in ALL:
        g = G[t]
        m = strat(g)
        if m.sum() < 200:
            pr("  %-10s  too little" % t)
            continue
        q = lambda x: "%.0f/%.0f/%.0f" % tuple(np.percentile(x[m], [10, 50, 90]))  # noqa: E731
        pr("  %-10s %-7s %7.1f | %14s | %16s | %16s | %16s" % (
            t, CEN.CELL_OF.get(t, "?"), m.sum() / FS,
            "%.1f/%.1f/%.1f" % tuple(np.percentile(g["vego"][m], [10, 50, 90])),
            q(np.abs(g["ang"])), q(g["idx"]), q(np.abs(g["bar"]))))

    # ---------------------------------------------------------------- 3. excitation control
    pr("")
    pr("=" * 150)
    pr("3.  EXCITATION CONTROL -- the 0xE4 COMMAND's own content in the same stratum and the same bands.")
    pr("    The fork commit and the DRIVING MODEL changed between r6c and these routes.  If the command's")
    pr("    6-9 Hz content is UP on V292, the high-angle result is confounded by openpilot; if it is NOT,")
    pr("    the extra ripple is EPS-internal.")
    pr("=" * 150)
    pr("  %-10s %-7s %7s | %9s %9s %9s | %9s %9s | %9s" %
       ("route", "build", "n_seg", "cmd 6-9", "cmd 9-13", "cmd 18-22", "cmd rms", "|cmd| p50", "cmd d/frame"))
    for t in ALL:
        g = G[t]
        m = strat(g)
        segs = [(a, b) for a, b in C20.runs(m, 100)]
        if len(segs) < 3:
            pr("  %-10s  too few runs" % t)
            continue
        c69 = np.nanmedian([band_amp(g["cmd"][a:b], 6, 9) for a, b in segs])
        c913 = np.nanmedian([band_amp(g["cmd"][a:b], 9, 13) for a, b in segs])
        c1822 = np.nanmedian([band_amp(g["cmd"][a:b], 18, 22) for a, b in segs])
        rms = np.nanmedian([np.std(g["cmd"][a:b]) for a, b in segs])
        lvl = np.nanmedian([np.median(np.abs(g["cmd"][a:b])) for a, b in segs])
        dpf = np.nanmedian([np.median(np.abs(np.diff(g["cmd"][a:b]))) for a, b in segs])
        pr("  %-10s %-7s %7d | %9.1f %9.1f %9.1f | %9.1f %9.1f | %9.2f" %
           (t, CEN.CELL_OF.get(t, "?"), len(segs), c69, c913, c1822, rms, lvl, dpf))

    # ---------------------------------------------------------------- 4. paired bootstrap on the continuous stats
    pr("")
    pr("=" * 150)
    pr("4.  THE CONTINUOUS STATISTICS with CIs -- 1 s windows, 0.5 s step, same stratum.  These do not")
    pr("    use the F7 detector at all, and they are the weight behind the small episode counts.")
    pr("=" * 150)
    W, STEP = 100, 50
    stats_by = {}
    for t in ALL:
        g = G[t]
        m = strat(g)
        rows = []
        for a, b in C20.runs(m, W):
            for s in range(a, b - W + 1, STEP):
                e = s + W
                x = g["wire"][s:e]
                f, P = signal.welch(x - x.mean(), fs=FS, nperseg=W)
                sl = (f >= 5.5) & (f <= 9.5)
                j = np.argmax(P[sl])
                Tw = g["T100"][s:e]
                lvl = float(np.median(np.abs(Tw)))
                rows.append(dict(f0=float(f[sl][j]),
                                 rate_f0=float(np.sqrt(2 * P[sl][j] * (f[1] - f[0]))) / CPD,
                                 rate69=band_amp(x, 6, 9) / CPD,
                                 bar68=band_amp(g["bar"][s:e], 6, 8.5),
                                 ripL=(band_amp(Tw, 6, 8.5) / lvl if lvl > 1 else np.nan)))
        stats_by[t] = rows
    pr("  %-10s %-7s %6s | %-24s | %-24s | %-24s" %
       ("route", "build", "n_win", "rate 6-9 Hz deg/s", "tap rip/L", "bar 6-8.5 Hz raw"))
    def bci(v, fn=np.median, n=4000):
        v = np.asarray([x for x in v if np.isfinite(x)], float)
        if len(v) < 5:
            return np.nan, np.nan, np.nan
        b = np.array([fn(v[rng.integers(0, len(v), len(v))]) for _ in range(n)])
        return float(fn(v)), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))
    for t in ALL:
        rows = stats_by[t]
        if len(rows) < 6:
            pr("  %-10s  too few windows (%d)" % (t, len(rows)))
            continue
        a1 = bci([x["rate69"] for x in rows])
        a2 = bci([x["ripL"] for x in rows])
        a3 = bci([x["bar68"] for x in rows])
        pr("  %-10s %-7s %6d | %6.2f [%5.2f,%5.2f]      | %6.3f [%5.3f,%5.3f]      | %6.0f [%5.0f,%5.0f]" %
           (t, CEN.CELL_OF.get(t, "?"), len(rows), a1[0], a1[1], a1[2], a2[0], a2[1], a2[2], a3[0], a3[1], a3[2]))
    pr("")
    pr("  RATIO to r6c (median-of-window ratios, independent bootstrap of both arms):")
    base = stats_by.get("r6c", [])
    for key, lab in (("rate69", "rate 6-9 Hz"), ("ripL", "tap rip/L"), ("bar68", "bar 6-8.5 Hz")):
        pr("    %-16s %s" % (lab, "  ".join("%-26s" % t for t in V292_ROUTES + ("r39", "r35"))))
        bvals = np.array([x[key] for x in base if np.isfinite(x[key])], float)
        cellsx = []
        for t in V292_ROUTES + ("r39", "r35"):
            av = np.array([x[key] for x in stats_by[t] if np.isfinite(x[key])], float)
            if len(av) < 5 or len(bvals) < 5:
                cellsx.append("--")
                continue
            rr = np.array([np.median(av[rng.integers(0, len(av), len(av))]) /
                           np.median(bvals[rng.integers(0, len(bvals), len(bvals))]) for _ in range(4000)])
            cellsx.append("x%.2f [%.2f, %.2f]" % (np.median(av) / np.median(bvals),
                                                  np.percentile(rr, 2.5), np.percentile(rr, 97.5)))
        pr("    %-16s %s" % ("", "  ".join("%-26s" % c for c in cellsx)))

    io.open(os.path.join(SCR, "v292_flight_crux.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_crux.txt")


if __name__ == "__main__":
    main()
