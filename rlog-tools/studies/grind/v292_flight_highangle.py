# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- deliverable 3: THE OPERATOR'S SYMPTOM.  He reports, after three routes on V292:
"grinding still present; STUTTERING IS WORSE, most visible as an OSCILLATION WHEN HOLDING THE WHEEL AT A
HIGH ANGLE."  This is the high-angle / strong-turn instrument, scored EXACTLY as the record scores it.

METHOD FIDELITY -- every threshold is the record's, not a new one:
  * F7 census: strongturn_r32_r33.fixed_thr_episodes(r, thr=103, band=(2,8)) -- the FIXED 103-wire detector
    used for r32/r33/r34/r35/r36-r38.  Episode = engaged run >= 1 s whose 2-8 Hz Hilbert rate envelope
    exceeds 103 raw wire counts, merged if < 1 s apart.  F7 = |angle| median >= 30 deg AND fdom >= 6 Hz.
    Rate = F7 per 100 s of ENGAGED HIGH-ANGLE time (|angle| >= 30).   REVERT THRESHOLD: F7 >= 2 /100 s.
  * tap ripple/level: 6-8.5 Hz amplitude of the 0x1AB delivered-torque tap divided by median |T|, over
    hands-light strong-turn 1 s windows (0.5 s step; engaged, |angle| >= 30, v <= 10 m/s, |bar| < 2240,
    idx >= 40) -- stutter_v283.py SECTION C.  REVERT THRESHOLD: >= 0.25.
    Record values: r32 0.36, r33 0.62, r34 0.37, r35 (V281r3) 0.18, V283 r36/r37/r38 0.08/0.15/0.18.
  * chain mirror: grind_incident_r35.simulate with CELLS READ FROM EACH BUILD'S OWN IMAGE, for the
    reference rate ref_deg = 32*|sp| / FB_DC / CPD (strongturn_r32_r33's formula) and the rail duties.
    FB_DC is computed PER BUILD from its own cells, 2b/(1024-a): V282 30.891, V292 30.903.
    🛑 The mirror's feedback lag uses ONE floor where the bytes have two, and does NOT model V292's cave
    (V292-REPLAY-PREDICTION defect A).  It is used here ONLY for sp / ref_deg and the rail duties, which
    are set by the command path and by E's magnitude, not by the cave's 1-LSB rounding.  Marked where used.
  * 427 tap: gp-0x6B38 sar 0 on BOTH V282 and V292 (read from the images), so T is directly comparable.

Routes: r6d_v292 / r6e_v292 / r6f_v292 (V292, 2026-09-13) vs r6c (V282, 2026-09-12) and r39 (V282),
plus r35 (V281 rev 3) as the record's "the 7 Hz cycle is gone" anchor.

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_highangle.py
"""
import io
import json
import os
import sys
import types

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "osc-highangle"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import strongturn_r32_r33 as ST               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
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


def band_amp(x, lo, hi, fs=FS):
    x = np.asarray(x, float)
    if len(x) < 30:
        return np.nan
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return float(np.sqrt(2.0) * signal.sosfiltfilt(sos, x - x.mean()).std())


def peak_in(x, lo, hi, fs=FS, nperseg=None):
    x = np.asarray(x, float)
    n = len(x)
    if n < 64:
        return np.nan, np.nan
    f, P = signal.welch(x - x.mean(), fs=fs, nperseg=min(nperseg or n, n))
    sl = (f >= lo) & (f <= hi)
    if not sl.any():
        return np.nan, np.nan
    j = np.argmax(P[sl])
    return float(f[sl][j]), float(np.sqrt(2.0 * P[sl][j] * (f[1] - f[0])))


def load(tag, cells_of):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    c = cells_of[tag]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    g["T"] = g["T100"]
    r = types.SimpleNamespace(tag=tag, wire=g["wire"], eng=g["eng"], ang=g["ang"], vego=g["vego"],
                              bar=g["bar"], cmd=g["cmd"], idx=g["idx"], T=g["T100"], t=g["tr"], g=g, c=c)
    return r


def fb_dc(c):
    return 2.0 * c["fb_b"] / (1024.0 - c["fb_a"])


def ref_deg_for(r, a, b):
    """reference rate in deg/s over [a,b) from the build's own chain mirror (sp path only)."""
    R = GI.simulate(r.g, a, b, r.c)
    sp = np.abs(R["sp"])
    ref = 32.0 * sp / fb_dc(r.c) / CPD
    # map the 1 kHz mirror back onto the 100 Hz frames of [a,b)
    off = (a - R["seg"].start) * 10
    n = (b - a) * 10
    seg = ref[off:off + n]
    return (float(np.median(seg)) if len(seg) else np.nan,
            R["prail"], R["drail"], R["fbclp"], R["tcap"])


def main():
    CEN.IMG["V292"] = V292_IMG
    for t in V292_ROUTES:
        CEN.CELL_OF[t] = "V292"
    CEN.CELL_OF["r6c"] = "V282"
    cells_by_build = {k: GI.read_cells(p) for k, p in CEN.IMG.items()
                      if k in ("V282", "V292", "V281r3")}
    cells_of = {t: cells_by_build[CEN.CELL_OF[t]] for t in ALL}

    pr("=" * 172)
    pr("V292 FLIGHT READ -- THE OPERATOR'S SYMPTOM: 'stuttering is WORSE, an oscillation when holding the")
    pr("wheel at a high angle'.  High-angle / strong-turn instrument, the record's own thresholds.")
    pr("=" * 172)
    for b_ in ("V282", "V292"):
        c = cells_by_build[b_]
        pr("  %-7s fb pole %d/%d  DC %.3f | kp_Y %s | map_Y[-1] %.0f | fb_clamp %d | gain %d"
           % (b_, c["fb_a"], c["fb_b"], fb_dc(c), np.round(c["kp_Y"], 0).tolist(), c["map_Y"][-1],
              c["fb_clamp"], c["gain"]))
    pr("  r24 arm 0xC6446: V282 5244 -> V292 4725 (read from the images directly; GI.read_cells does not")
    pr("  cover this cell, so it does not appear in the cell diff above).")
    pr("🛑 CONFOUND: the openpilot fork changed between r6c and these routes (GitCommit 57410c3b -> 305732c85,")
    pr("   DrivingModel tsfdo -> gyhu3, every Accord* param key wiped).  r6c is the nearest V282 reference in")
    pr("   TIME; r39 is the record's V282 grinding reference; r35 is V281 rev 3.  None is fork-matched.")

    R = {}
    for tag in ALL:
        try:
            R[tag] = load(tag, cells_of)
        except Exception as e:
            pr("  %-10s LOAD FAILED: %s" % (tag, str(e)[:90]))
            continue
        r = R[tag]
        hs30 = float((r.eng & (np.abs(r.ang) >= 30)).sum() / FS)
        hs15 = float((r.eng & (np.abs(r.ang) >= 15) & (np.abs(r.ang) < 30)).sum() / FS)
        pr("  loaded %-10s %7.1f s route | engaged %7.1f s | |ang|>=30 %6.1f s | 15-30 deg %6.1f s | build %s"
           % (tag, r.t[-1], r.eng.sum() / FS, hs30, hs15, CEN.CELL_OF.get(tag, "?")))

    # ------------------------------------------------------------------ A. the F7 census
    pr("")
    pr("=" * 172)
    pr("A.  F7 CENSUS -- the record's FIXED 103-wire detector.  REVERT THRESHOLD: F7 >= 2 per 100 s of")
    pr("    engaged high-angle time.  (r32 8.1, r33 4.3, r34 6.8-7.4, r35/V281r3 0.00, V283 0.00.)")
    pr("=" * 172)
    pr("  %-10s %-7s %9s %9s | %7s %7s %7s | %10s | %s" %
       ("route", "build", "eng s", "hi-ang s", "n_eps", "n>=30", "n F7", "F7 /100 s", "F7 fdom list"))
    f7tab = {}
    for tag in ALL:
        if tag not in R:
            continue
        r = R[tag]
        eps = ST.fixed_thr_episodes(r, thr=103.0)
        hi = [e for e in eps if e["ang"] >= 30]
        f7 = [e for e in hi if e["fdom"] >= 6]
        hs = float((r.eng & (np.abs(r.ang) >= 30)).sum() / FS)
        f7tab[tag] = dict(eps=eps, hi=hi, f7=f7, hs=hs)
        pr("  %-10s %-7s %9.1f %9.1f | %7d %7d %7d | %10.2f | %s" % (
            tag, CEN.CELL_OF.get(tag, "?"), r.eng.sum() / FS, hs, len(eps), len(hi), len(f7),
            100.0 * len(f7) / hs if hs > 1 else np.nan,
            " ".join("%.1f" % e["fdom"] for e in hi[:14]) or "-"))
    pr("")
    pr("  every |angle| >= 30 episode, all routes (t0, dur, fdom, angle, speed, 2-8 Hz rate amplitude):")
    for tag in ALL:
        if tag not in f7tab:
            continue
        for e in f7tab[tag]["hi"]:
            pr("    %-10s t0 %7.1f dur %4.1f fdom %5.2f Hz ang %4.0f deg v %4.1f m/s rate-amp %5.0f wire (%.1f deg/s)%s"
               % (tag, e["t0"], e["dur"], e["fdom"], e["ang"], e["v"], e["ramp"], e["ramp"] / CPD,
                  "   <-- F7" if e["fdom"] >= 6 else ""))
    pr("")
    pr("  detector-floor sensitivity (is the ripple just under 103?): F7 count at lower fixed thresholds")
    pr("  %-10s %s" % ("route", "  ".join("thr %3d" % t for t in (103, 80, 60, 40))))
    for tag in ALL:
        if tag not in R:
            continue
        r = R[tag]
        hs = f7tab[tag]["hs"]
        row = []
        for thr in (103, 80, 60, 40):
            eps = ST.fixed_thr_episodes(r, thr=float(thr))
            f7 = [e for e in eps if e["ang"] >= 30 and e["fdom"] >= 6]
            row.append("%2d (%4.2f)" % (len(f7), 100.0 * len(f7) / hs if hs > 1 else np.nan))
        pr("  %-10s %s" % (tag, "  ".join(row)))

    # ------------------------------------------------------------------ B. strong-turn windows
    pr("")
    pr("=" * 172)
    pr("B.  HANDS-LIGHT STRONG-TURN WINDOWS -- stutter_v283.py SECTION C's method, unchanged.")
    pr("    engaged AND |angle| >= 30 AND v <= 10 m/s AND |bar| < 2240 AND idx >= 40; 1 s windows, 0.5 s step.")
    pr("    f0 = rate peak in 5.5-9.5 Hz.  rip/L = tap 6-8.5 Hz amplitude / median |T|.  REVERT at >= 0.25.")
    pr("=" * 172)
    W, STEP = int(FS), int(FS / 2)
    winrows = {}
    for tag in ALL:
        if tag not in R:
            continue
        r = R[tag]
        m = r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.bar) < 2240) & (r.idx >= 40)
        rows = []
        for a, b in C20.runs(m, W):
            for s in range(a, b - W + 1, STEP):
                e = s + W
                f0, A0 = peak_in(r.wire[s:e], 5.5, 9.5)
                Tw = r.T[s:e]
                lvl = float(np.median(np.abs(Tw)))
                rip = band_amp(Tw, 6.0, 8.5)
                rows.append(dict(t0=r.t[s], f0=f0, rate_f0=A0 / CPD, rate68=band_amp(r.wire[s:e], 6.0, 8.5) / CPD,
                                 bar68=band_amp(r.bar[s:e], 6.0, 8.5), T=lvl, rip=rip,
                                 ripL=(rip / lvl if lvl > 1 else np.nan),
                                 tq50=float(np.median(np.abs(r.bar[s:e]))),
                                 idx=float(np.median(r.idx[s:e])), v=float(r.vego[s:e].mean()),
                                 ang=float(np.median(np.abs(r.ang[s:e]))),
                                 cmd68=band_amp(r.cmd[s:e], 6.0, 8.5)))
        winrows[tag] = rows
    pr("  %-10s %-7s %6s | %6s %6s %6s | %7s %7s | %7s %7s %7s | %6s %6s" %
       ("route", "build", "n_win", "f0 p50", "f0 p10", "f0 p90", "rate@f0", "rate6-8.5", "|T| p50",
        "rip/L p50", "rip/L p90", "bar68", "cmd68"))
    for lab, sub in (("ALL hands-light", lambda x: True),
                     ("hands LIGHT (|bar|<1216)", lambda x: x["tq50"] < 1216),
                     ("hands ON (|bar|>=1216)", lambda x: x["tq50"] >= 1216),
                     ("idx >= 68", lambda x: x["idx"] >= 68)):
        pr("  --- %s ---" % lab)
        for tag in ALL:
            rows = [x for x in winrows.get(tag, []) if sub(x)]
            if len(rows) < 3:
                pr("  %-10s %-7s %6d  -- too few windows --" % (tag, CEN.CELL_OF.get(tag, "?"), len(rows)))
                continue
            f0 = np.array([x["f0"] for x in rows], float)
            rf = np.array([x["rate_f0"] for x in rows], float)
            r68 = np.array([x["rate68"] for x in rows], float)
            rl = np.array([x["ripL"] for x in rows], float)
            pr("  %-10s %-7s %6d | %6.2f %6.2f %6.2f | %7.1f %7.1f | %7.0f %7.3f %7.3f | %6.0f %6.0f" % (
                tag, CEN.CELL_OF.get(tag, "?"), len(rows), np.nanmedian(f0), np.nanpercentile(f0, 10),
                np.nanpercentile(f0, 90), np.nanmedian(rf), np.nanmedian(r68),
                np.nanmedian([x["T"] for x in rows]), np.nanmedian(rl), np.nanpercentile(rl, 90),
                np.nanmedian([x["bar68"] for x in rows]), np.nanmedian([x["cmd68"] for x in rows])))
        pr("")

    # ------------------------------------------------------------------ C. the 15-30 deg band, and hands ON/OFF
    pr("=" * 172)
    pr("C.  THE OPERATOR'S ANGLE BANDS, WITH A HANDS SPLIT -- broadband, every engaged frame (no detector).")
    pr("    Reported as 6-9 Hz and 18-22 Hz amplitudes of the 0x18F rate and of the 0x1AB tap, per stratum.")
    pr("=" * 172)
    STRATA = [("|ang|>=30, hands OFF (|bar|<400)", lambda r: (np.abs(r.ang) >= 30) & (np.abs(r.bar) < 400)),
              ("|ang|>=30, hands LIGHT (400-1216)", lambda r: (np.abs(r.ang) >= 30) & (np.abs(r.bar) >= 400) & (np.abs(r.bar) < 1216)),
              ("|ang|>=30, hands ON (>=1216)", lambda r: (np.abs(r.ang) >= 30) & (np.abs(r.bar) >= 1216)),
              ("|ang| 15-30, hands OFF", lambda r: (np.abs(r.ang) >= 15) & (np.abs(r.ang) < 30) & (np.abs(r.bar) < 400)),
              ("|ang| 15-30, hands ON (>=1216)", lambda r: (np.abs(r.ang) >= 15) & (np.abs(r.ang) < 30) & (np.abs(r.bar) >= 1216)),
              ("|ang| < 15, hands OFF", lambda r: (np.abs(r.ang) < 15) & (np.abs(r.bar) < 400))]
    for lab, fn in STRATA:
        pr("  --- %s ---" % lab)
        pr("  %-10s %-7s %8s | %8s %8s | %8s %8s | %8s %8s" %
           ("route", "build", "time s", "rate6-9", "rate18-22", "T 6-9", "T 18-22", "|T| p50", "bar6-9"))
        for tag in ALL:
            if tag not in R:
                continue
            r = R[tag]
            m = r.eng & fn(r)
            segs = [(a, b) for a, b in C20.runs(m, 100)]
            if not segs or sum(b - a for a, b in segs) < 300:
                pr("  %-10s %-7s %8.1f  -- under 3 s of runs >= 1 s --" %
                   (tag, CEN.CELL_OF.get(tag, "?"), m.sum() / FS))
                continue
            r69 = np.nanmedian([band_amp(r.wire[a:b], 6, 9) / CPD for a, b in segs])
            r1822 = np.nanmedian([band_amp(r.wire[a:b], 18, 22) / CPD for a, b in segs])
            t69 = np.nanmedian([band_amp(r.T[a:b], 6, 9) for a, b in segs])
            t1822 = np.nanmedian([band_amp(r.T[a:b], 18, 22) for a, b in segs])
            tl = np.nanmedian([np.median(np.abs(r.T[a:b])) for a, b in segs])
            b69 = np.nanmedian([band_amp(r.bar[a:b], 6, 9) for a, b in segs])
            pr("  %-10s %-7s %8.1f | %8.2f %8.2f | %8.1f %8.1f | %8.0f %8.0f" % (
                tag, CEN.CELL_OF.get(tag, "?"), m.sum() / FS, r69, r1822, t69, t1822, tl, b69))
        pr("")

    # ------------------------------------------------------------------ D. the stall / reference test
    pr("=" * 172)
    pr("D.  IS THE WHEEL STALLED AGAINST THE REFERENCE?  ref_deg = 32*|sp| / FB_DC / CPD from each build's")
    pr("    own chain mirror (sp path only -- the mirror does NOT model V292's cave; see the header).")
    pr("    Evaluated on the |angle| >= 30 episodes above.")
    pr("=" * 172)
    pr("  %-10s %7s %5s %5s | %7s %7s %6s | %6s %6s %6s %6s" %
       ("route", "t0", "dur", "fdom", "rate50", "ref", "r/ref", "Prail", "Drail", "fbclp", "Tcap"))
    stall = {}
    for tag in ALL:
        if tag not in f7tab:
            continue
        r = R[tag]
        vals = []
        for e in f7tab[tag]["hi"][:20]:
            a = int(round(e["t0"] * FS)); b = a + int(round(e["dur"] * FS))
            if b >= len(r.t) - 20 or a < 60:
                continue
            try:
                ref, pra, dra, fbc, tcap = ref_deg_for(r, a, b)
            except Exception as ex:
                pr("    %-10s t0 %7.1f  sim failed: %s" % (tag, e["t0"], str(ex)[:60]))
                continue
            rate50 = float(np.median(np.abs(r.wire[a:b])) / CPD)
            vals.append(rate50 / ref if ref > 0.5 else np.nan)
            pr("  %-10s %7.1f %5.1f %5.2f | %7.1f %7.1f %6.2f | %6.2f %6.2f %6.2f %6.2f" %
               (tag, e["t0"], e["dur"], e["fdom"], rate50, ref, rate50 / ref if ref > 0.5 else np.nan,
                pra, dra, fbc, tcap))
        stall[tag] = vals
    pr("")
    pr("  rate/reference over the |angle|>=30 episodes (stalled class = < 0.5):")
    for tag in ALL:
        v = np.array(stall.get(tag, []), float)
        v = v[np.isfinite(v)]
        if len(v) < 1:
            pr("  %-10s  no episodes" % tag)
            continue
        pr("  %-10s n %2d  p50 %.2f  min %.2f  stalled (<0.5) %d of %d" %
           (tag, len(v), np.median(v), v.min(), int((v < 0.5).sum()), len(v)))

    with open(os.path.join(SCR, "v292_flight_highangle.json"), "w") as fh:
        json.dump({t: dict(n_f7=len(f7tab[t]["f7"]), n_hi=len(f7tab[t]["hi"]), hi_ang_s=f7tab[t]["hs"],
                           windows=len(winrows.get(t, []))) for t in f7tab}, fh, indent=1, default=float)
    io.open(os.path.join(SCR, "v292_flight_highangle.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_highangle.txt")


if __name__ == "__main__":
    main()
