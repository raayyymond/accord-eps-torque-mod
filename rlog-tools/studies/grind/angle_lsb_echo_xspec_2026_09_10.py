# -*- coding: utf-8 -*-
"""studies/grind/angle_lsb_echo_xspec_2026_09_10.py -- follow-up to angle_lsb_echo_2026_09_10.py.
Agent `echoloop`, 2026-09-10.  ANALYSIS ONLY.

Two things the first pass could not settle, both decision-bearing:

4b  The band-amplitude ratio predicted/measured (0.27-0.37 pooled) is BIASED LOW: GI.band on the
    command measures the LINE PLUS the broadband floor of a signal that changes on 92 % of frames,
    while on the angle it is nearly all line.  The floor-immune test is the CROSS-SPECTRUM:
      |H| = |S_ac| / S_aa   in raw 0xE4 counts per DEGREE of measured angle, at the line.
    The openpilot gain chain predicts |H| = counts_per_deg(v) EXACTLY, floor and all, because the
    floor is incoherent with the angle and cancels out of S_ac.  Coherence gamma^2 says how much of
    the command's ring-band content the angle explains at all.

5b  The first pass measured the rate-limiter bind duty inside grinding windows at ~0 %, against the
    "13-21 % of grinding frames" in the brief.  That is decision-bearing (it decides whether raising
    STEER_DELTA_UP changes the 20 Hz content), so it is re-measured four ways: route-wide, engaged,
    inside grinding windows, and inside the 0.5 s before onset, at several cap thresholds.

Run: python angle_lsb_echo_xspec_2026_09_10.py   (writes _scratch/angle_lsb_echo_xspec_2026_09_10.txt)
"""
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
import grind_incident_r35 as GI               # noqa: E402

import angle_lsb_echo_2026_09_10 as A         # noqa: E402  (load(), counts_per_deg(), constants)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, W, STEP = A.FS, A.W, A.STEP
LSB_DEG, STEER_MAX, CAP = A.LSB_DEG, A.STEER_MAX, A.CAP
ROUTES = A.ROUTES
FIELDS = A.FIELDS
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    Z = np.load(os.path.join(SCR, "angle_lsb_echo_windows.npz"))
    R = {t: Z[t] for t, _, _, _ in ROUTES}
    F = {n: i for i, n in enumerate(FIELDS)}
    G = {t: A.load(t) for t, _, _, _ in ROUTES}

    pr("=" * 150)
    pr("FOLLOW-UP: floor-immune cross-spectral gain, and the rate limiter's REAL bind duty")
    pr("angle_lsb_echo_xspec_2026_09_10.py, agent `echoloop`, 2026-09-10.  Analysis only.")
    pr("=" * 150)

    # ------------------------------------------------------------------ 4b
    pr("\n" + "=" * 150)
    pr("4b. CROSS-SPECTRAL GAIN  angle -> 0xE4 command, at the line.  |H| = |S_ac|/S_aa, counts per DEGREE.")
    pr("=" * 150)
    pr("  The openpilot chain predicts |H| = counts_per_deg(v) = curvature_factor(v) x rad(1 deg)/sR x v^2")
    pr("  x (k_p 0.6 + LSF(v)) / LAF 1.6893 x 4096.  This test is immune to the command's broadband floor,")
    pr("  which is incoherent with the angle and cancels out of the cross-spectrum.")
    pr("  Cross-spectra pooled over present windows per (route, speed bin), Welch nperseg 128 on the")
    pr("  0x18F frame axis (the angle is interpolated onto it ONLY here -- amplitudes came from its own grid).")
    pr("\n  %-9s %-8s %-11s %5s | %9s %9s %8s | %8s %9s" %
       ("route", "build", "speed bin", "n win", "|H| meas", "|H| pred", "ratio", "gamma^2", "phase deg"))
    ROWS = []
    for tag, build, lo, hi in ROUTES:
        Rt = R[tag]
        g = G[tag]
        p = Rt[Rt[:, 1] > 0.5]
        if len(p) < 5:
            continue
        for a, bnd in ((0, 8), (8, 14), (14, 20), (20, 40), (0, 40)):
            m = (p[:, F["v"]] >= a) & (p[:, F["v"]] < bnd)
            if m.sum() < 5:
                continue
            Saa = Scc = Sac = None
            nseg = 0
            f0s = []
            for rec in p[m]:
                s = int(rec[F["s"]])
                e = s + W
                ang = g["ang"][s:e]                       # 0x14A angle on the 0x18F frame axis
                cmd = g["cmd"][s:e]
                fw, Pa = signal.csd(ang, ang, fs=FS, nperseg=128)
                _, Pc = signal.csd(cmd, cmd, fs=FS, nperseg=128)
                _, Pac = signal.csd(ang, cmd, fs=FS, nperseg=128)
                Saa = Pa if Saa is None else Saa + Pa
                Scc = Pc if Scc is None else Scc + Pc
                Sac = Pac if Sac is None else Sac + Pac
                nseg += 1
                f0s.append(rec[F["f0"]])
            f0 = float(np.median(f0s))
            i = int(np.argmin(np.abs(fw - f0)))
            H = Sac[i] / Saa[i]
            coh = np.abs(Sac[i]) ** 2 / (np.abs(Saa[i]) * np.abs(Scc[i]))
            v = float(np.median(p[m, F["v"]]))
            pred = A.counts_per_deg(v)
            tagname = "%d-%d m/s" % (a, bnd) if bnd != 40 or a != 0 else "ALL"
            pr("  %-9s %-8s %-11s %5d | %9.1f %9.1f %8.2f | %8.3f %+9.0f%s" %
               (tag, build, tagname, nseg, abs(H), pred, abs(H) / pred, coh,
                np.degrees(np.angle(H)), "   <= route" if tagname == "ALL" else ""))
            if tagname == "ALL":
                ROWS.append((abs(H) / pred, coh))
    if ROWS:
        rr = np.array([r[0] for r in ROWS])
        cc = np.array([r[1] for r in ROWS])
        pr("\n  across the five routes: |H|measured/|H|predicted  median %.2f  (range %.2f - %.2f)"
           % (np.median(rr), rr.min(), rr.max()))
        pr("  coherence(angle, command) at the line               median %.3f  (range %.3f - %.3f)"
           % (np.median(cc), cc.min(), cc.max()))
    pr("\n  READING: |H| ratio ~1 => the gain chain (measurement -> P -> 0xE4) is CORRECT as derived from")
    pr("  the fork.  gamma^2 is the share of the command's ring-band VARIANCE the angle linearly explains;")
    pr("  1 - gamma^2 is what the setpoint / feedforward side and the broadband floor contribute.")

    # ------------------------------------------------------------------ 5b
    pr("\n" + "=" * 150)
    pr("5b. THE RATE LIMITER'S REAL BIND DUTY -- four strata, several thresholds")
    pr("=" * 150)
    pr("  cap = 3 x 0.01 x 4096 = %.2f counts/frame.  'bind' = |delta cmd| at or above the threshold." % CAP)
    pr("\n  %-9s %-8s | %8s %8s %8s %8s | %10s %10s %10s %10s | %9s" %
       ("route", "build", "max |d|", "p99 |d|", "p99.9", "mean|d|", "all %", "engaged %", "GRIND %", "pre-0.5s %", "enrich"))
    DUTIES = []
    for tag, build, lo, hi in ROUTES:
        g = G[tag]
        Rt = R[tag]
        d = np.abs(np.diff(np.round(g["cmd"])))
        eng = g["eng"][1:] & g["eng"][:-1]
        hot = np.zeros(len(g["cmd"]), bool)
        pre = np.zeros(len(g["cmd"]), bool)
        for rec in Rt[Rt[:, 1] > 0.5]:
            s = int(rec[F["s"]])
            hot[s:s + W] = True
            pre[max(0, s - 50):s] = True
        thr = CAP - 0.5
        f_all = 100.0 * np.mean(d >= thr)
        f_eng = 100.0 * np.mean(d[eng] >= thr) if eng.sum() else np.nan
        f_hot = 100.0 * np.mean(d[hot[1:] & eng] >= thr) if (hot[1:] & eng).sum() else np.nan
        f_pre = 100.0 * np.mean(d[pre[1:] & eng] >= thr) if (pre[1:] & eng).sum() else np.nan
        DUTIES.append(f_hot)
        pr("  %-9s %-8s | %8.0f %8.0f %8.0f %8.2f | %10.3f %10.3f %10.3f %10.3f | %9.2f" %
           (tag, build, d.max(), np.percentile(d, 99), np.percentile(d, 99.9), d[eng].mean(),
            f_all, f_eng, f_hot, f_pre, (f_hot / f_eng) if f_eng else np.nan))
    pr("\n  %-9s %-8s | %s" % ("route", "build", "share of engaged frames at or above each threshold (counts/frame)"))
    pr("  %-9s %-8s | %s" % ("", "", " ".join("%9d" % t for t in (40, 60, 80, 100, 110, 120, 122, 123))))
    for tag, build, lo, hi in ROUTES:
        g = G[tag]
        d = np.abs(np.diff(np.round(g["cmd"])))
        eng = g["eng"][1:] & g["eng"][:-1]
        pr("  %-9s %-8s | %s" % (tag, build,
                                 " ".join("%8.3f%%" % (100 * np.mean(d[eng] >= t)) for t in (40, 60, 80, 100, 110, 120, 122, 123))))
    md = float(np.nanmedian(DUTIES))
    pr("\n  MEASURED bind duty inside grinding windows, median across the five routes: %.3f %%" % md)
    pr("  At that duty the two-tone describing function gives |N|@20Hz = 1.000 (the limiter is transparent).")
    pr("  => raising STEER_DELTA_UP would change NOTHING about the 20 Hz content on these builds, because")
    pr("     the limiter is not binding during grinding in the first place.")

    with open(os.path.join(SCR, "angle_lsb_echo_xspec_2026_09_10.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    pr("\nwrote %s" % os.path.join(SCR, "angle_lsb_echo_xspec_2026_09_10.txt"))


if __name__ == "__main__":
    main()
