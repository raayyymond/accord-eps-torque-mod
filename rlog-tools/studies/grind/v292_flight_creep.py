# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- the DETECTOR-FREE band read for (a), (d), (e), (f), on the hands-off strata that
the pre-registration names, plus a presence rate computed with the record's own predicate.

Why this exists alongside v292_flight_census.py: the full V282 episode census (window_census +
extract_episodes over r6c's 3136 engaged seconds) is expensive, and the BAND answer does not need it.
Everything here is a pooled spectrum over a fixed stratum with NO episode selection anywhere, so a
change in presence rate cannot leak into an amplitude, and vice versa.

  (a)  18-22 Hz on the 0x18F STEER_ANGLE_RATE, hands-off creep and the other hands-off speed bands:
       pooled amplitude with a segment-bootstrap CI, plus the record's presence predicate
       (2 s windows, 0.5 s step; 18-22 Hz prominence >= 8 on the DRIVER-TORQUE bar AND bar amp >= 40 --
       grind1_census_v282.py W/STEP = 200/50 and its `pres`).
       The replay predicted ring x0.55 of V282 pooled, x0.71 against r6c specifically.
  (d)  the 9-18 Hz shoulder, split 9-13 / 13-17, against V282.  Predicted x1.33-1.70 byte-exact.
  (e)  any 22-30 Hz line.
  (f)  where the 18-22 Hz object sits in frequency (V289 moved it to 15-17 Hz).

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_creep.py
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
W, STEP = CEN.W, CEN.STEP          # 200 / 50 -- the kit standard
V292_IMG = (LG.FW + "_v292_V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
            "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V292_ROUTES = ("r6d_v292", "r6e_v292", "r6f_v292")
ALL = V292_ROUTES + ("r6c", "r39", "r35")
BANDS = (("5-9", 5, 9), ("9-13", 9, 13), ("13-17", 13, 17), ("18-22", 18, 22),
         ("22-26", 22, 26), ("26-30", 26, 30))
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    CEN.IMG["V292"] = V292_IMG
    for t in V292_ROUTES:
        CEN.CELL_OF[t] = "V292"
    CEN.CELL_OF["r6c"] = "V282"
    cb = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V292", "V281r3")}
    rng = np.random.default_rng(20260913)
    G = {}
    for t in ALL:
        g = C20.load(t)
        g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], cb[CEN.CELL_OF[t]])
        G[t] = g

    STRATA = [("hands-off (|bar|<400) CREEP 1-3 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3)),
              ("hands-off 3-8 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 3) & (g["vego"] < 8)),
              ("hands-off 8-15 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 8) & (g["vego"] < 15)),
              ("hands-off >=15 m/s (motorway)", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 15)),
              ("hands-off ALL speeds", lambda g: g["eng"] & (np.abs(g["bar"]) < 400)),
              ("ALL engaged", lambda g: g["eng"]),
              ("DISENGAGED (rate loop OPEN)", lambda g: ~g["eng"])]

    pr("=" * 160)
    pr("V292 FLIGHT READ -- DETECTOR-FREE BAND READ, (a) (d) (e) (f).  Pooled Welch on the 0x18F")
    pr("STEER_ANGLE_RATE, nperseg 256 (2.56 s, 0.39 Hz bins, 50 %% overlap), NO episode selection.")
    pr("Amplitudes are deg/s.  Ratios are to r6c (V282, 2026-09-12) with a segment bootstrap 95 %% CI.")
    pr("=" * 160)
    pr("🛑 The openpilot fork and the DRIVING MODEL changed between r6c and these routes.  r39 (V282) and")
    pr("   r35 (V281 rev 3) are carried as second and third references so the route-to-route spread among")
    pr("   NON-V292 builds is visible next to the V292 effect.")

    SPEC = {}
    for lab, fn in STRATA:
        pr("")
        pr("=" * 160)
        pr("  STRATUM: %s" % lab)
        pr("=" * 160)
        pr("  %-10s %-7s %8s %6s | %s" % ("route", "build", "t s", "n_seg",
                                          " | ".join("%-11s" % b[0] for b in BANDS)))
        ok = []
        for t in ALL:
            g = G[t]
            m = fn(g)
            runs = [g["wire"][a:b] for a, b in C20.runs(m, 256)]
            f, P = C88.seg_psds(runs, FS, 256)
            if P.shape[0] < 5:
                pr("  %-10s %-7s %8.1f %6d  -- too few segments --" %
                   (t, CEN.CELL_OF.get(t, "?"), m.sum() / FS, P.shape[0]))
                continue
            SPEC[(lab, t)] = (f, P)
            ok.append(t)
            Pm = P.mean(0)
            amps = []
            for _, lo, hi in BANDS:
                sl = (f >= lo) & (f <= hi)
                amps.append("%11.3f" % np.sqrt(2.0 * Pm[sl].sum() * (f[1] - f[0])) if True else "")
            pr("  %-10s %-7s %8.1f %6d | %s" % (t, CEN.CELL_OF.get(t, "?"), m.sum() / FS, P.shape[0],
                                                " | ".join(a.replace("  ", " ") for a in
                                                           ["%11.3f" % (np.sqrt(2.0 * P.mean(0)[(f >= lo) & (f <= hi)].sum() * (f[1] - f[0])) / CPD)
                                                            for _, lo, hi in BANDS])))
        if (lab, "r6c") not in SPEC:
            continue
        f6, P6 = SPEC[(lab, "r6c")]
        pr("  amplitude RATIO to r6c (segment bootstrap 95 %% CI):")
        for t in ok:
            if t == "r6c":
                continue
            f_, P_ = SPEC[(lab, t)]
            row = []
            for _, lo, hi in BANDS:
                sl = (f_ >= lo) & (f_ <= hi)
                a = P_[:, sl].mean(1); b = P6[:, sl].mean(1)
                rr = np.array([a[rng.integers(0, len(a), len(a))].mean() / b[rng.integers(0, len(b), len(b))].mean()
                               for _ in range(2000)])
                row.append("x%.2f[%.2f,%.2f]" % (np.sqrt(a.mean() / b.mean()),
                                                 np.sqrt(np.percentile(rr, 2.5)), np.sqrt(np.percentile(rr, 97.5))))
            pr("    %-10s %s" % (t, "  ".join("%-19s" % x for x in row)))
        pr("  (f) LINE LOCATION -- peak of the EXCESS-dB spectrum in each search band:")
        pr("    %-10s %-22s %-22s %-22s %-22s" % ("route", "10-17 Hz", "17-24 Hz", "22-30 Hz", "5-9.5 Hz"))
        for t in ok:
            f_, P_ = SPEC[(lab, t)]
            ex = C88.excess_db(f_, P_.mean(0), half_hz=2.0)
            cells = []
            for lo, hi in ((10, 17), (17, 24), (22, 30), (5, 9.5)):
                sl = (f_ >= lo) & (f_ <= hi)
                j = np.argmax(ex[sl])
                cells.append("%6.2f Hz %+6.2f dB" % (f_[sl][j], ex[sl][j]))
            pr("    %-10s %s" % (t, " ".join("%-22s" % c for c in cells)))

    # ------------------------------------------------------------------ presence rate, the record's predicate
    pr("")
    pr("=" * 160)
    pr("  (a cont.) PRESENCE RATE -- the record's own predicate, unchanged: 2 s windows, 0.5 s step,")
    pr("  present = 18-22 Hz prominence >= 8 on the DRIVER-TORQUE bar AND 18-22 Hz bar amplitude >= 40.")
    pr("  Reported per hands-off stratum, with the 18-22 Hz RATE amplitude of the present windows.")
    pr("=" * 160)
    PRES = [("hands-off creep 1-3 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3)),
            ("hands-off 3-8 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 3) & (g["vego"] < 8)),
            ("hands-off >=15 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 15)),
            ("ALL engaged", lambda g: g["eng"])]
    for lab, fn in PRES:
        pr("")
        pr("  --- %s ---" % lab)
        pr("  %-10s %-7s %8s %8s %8s | %10s %10s | %9s" %
           ("route", "build", "n_win", "n_pres", "pres %", "rate p50", "rate p90", "ratio p50"))
        base = None
        rows = {}
        for t in ALL:
            g = G[t]
            m = fn(g)
            ra, pr_, n = [], 0, 0
            for a, b in C20.runs(m, W):
                for s in range(a, b - W + 1, STEP):
                    e = s + W
                    f0, prom = CEN.line_of(g["bar"][s:e], FS)
                    amp = CEN.band(g["bar"][s:e], 18, 22)
                    n += 1
                    if prom >= 8 and amp >= 40:
                        pr_ += 1
                        ra.append(CEN.band(g["wire"][s:e], 18, 22) / CPD)
            rows[t] = (n, pr_, np.array(ra, float))
        if "r6c" in rows and len(rows["r6c"][2]) > 3:
            base = rows["r6c"][2]
        for t in ALL:
            n, p_, ra = rows[t]
            if n < 10:
                pr("  %-10s %-7s %8d  -- too few windows --" % (t, CEN.CELL_OF.get(t, "?"), n))
                continue
            rat = ""
            if base is not None and len(ra) > 3 and t != "r6c":
                r_ = np.median(ra) / np.median(base)
                bb = np.array([np.median(ra[rng.integers(0, len(ra), len(ra))]) /
                               np.median(base[rng.integers(0, len(base), len(base))]) for _ in range(3000)])
                rat = "x%.2f [%.2f,%.2f]" % (r_, np.percentile(bb, 2.5), np.percentile(bb, 97.5))
            pr("  %-10s %-7s %8d %8d %7.1f%% | %10.3f %10.3f | %s" % (
                t, CEN.CELL_OF.get(t, "?"), n, p_, 100.0 * p_ / n,
                np.median(ra) if len(ra) else np.nan, np.percentile(ra, 90) if len(ra) else np.nan, rat))

    io.open(os.path.join(SCR, "v292_flight_creep.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_creep.txt")


if __name__ == "__main__":
    main()
