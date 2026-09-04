# -*- coding: utf-8 -*-
"""studies/grind/v282_read_r39.py -- the FIRST DRIVE OF V282 PROPER (route r39, 2026-09-04).

V282 = V281 rev 3 (Kp LERP flat 248, Ki 0, map linear to x6, fb clamp 46080, CAN-427 delivered-torque tap)
+ four read-only ld.h displacements in the V105 cave: CAN 0x14A byte 4
    bit 7 = sign(gp-0x6b4c)      bit 6 = |r24| >= |T|      bit 5 = |r24| >= |aggregator|
    bit 4 = sign(r24)            bit 3 = sign(gp-0x3680)
r39 is the FIRST read of those bits on the Ki-0 base they were designed for (r36/r37/r38 carried them on V283's Ki 50).

Q1  the two userBookmark episodes, characterised against the r35 23:48:21 incident (GRIND-INCIDENT-r35-2026-09-03.md)
Q2  UNSUPERVISED census of the 18-22 Hz creep line, r39 vs r38/r37/r36 (V283), r35 (V281r3), r34 (V280r2),
    computed identically to v283_grind_census.py section 1/2 (which is grind_incident_r35.py section 3, unchanged)
Q3  PREREG-V282-READ.md (A)-(E), decision rule and FAIL conditions, scored as written

CONFOUND, stated up front and carried into every comparison: r39 = V282 firmware + TWO openpilot-side authority
increases vs r35 (variable steer-ratio map, effective SR 12.5 -> 16.00 near centre, +28 %; SteerKP 0.6 -> 0.8, +33 %),
i.e. ~1.70x more OUTER-loop authority.  Grinding is an INNER-loop symptom but the inner loop is now driven harder,
so exposure is NOT matched.  Handled by (i) reporting the demand-index and wheel-rate distributions alongside every
band number, (ii) idx-binned census rows, and (iii) an idx-matched reweighting of the headline duty onto r35's own
creep idx distribution.

Run: python v282_read_r39.py     (writes _scratch/v282_read_r39.txt beside it)
Caches: analysis-2020accord/_scratch/cache/v280/r3{4..9}.npz and r3{4..9}_b4.npz  (r39 built by extract_r39_v280cache.py)
Subagent grind39, 2026-09-04.  Analysis only: builds nothing, sends nothing, flashes nothing.
"""
import json
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
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import _grind2_lib as G2                      # noqa: E402
import grind_incident_r35 as GI               # noqa: E402  (read_cells / demand_live / simulate / eval_window, verbatim)
from v282_r24_tap_read import r24_series, Pool, GAINS, GLBL   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K, FST = 100.0, 1000.0, 50.0
CACHE = C20.CACHE
W, STEP = 200, 50                     # 2 s census windows, 0.5 s step -- r35's census, unchanged
ALL = ("r39", "r38", "r37", "r36", "r35", "r34")
GRP = {"r39": "V282", "r38": "V283", "r37": "V283", "r36": "V283", "r35": "V281r3", "r34": "V280r2"}
BUILD = {"r39": "V282 (Ki 0, Kp flat 248, r24 tap) NEW TUNE SR-map + KP 0.8",
         "r38": "V283 (Ki 50, Kp flat 248)", "r37": "V283 (Ki 50, Kp flat 248)", "r36": "V283 (Ki 50, Kp flat 248)",
         "r35": "V281r3 (Ki 0, Kp flat 248, OLD cave decode)", "r34": "V280r2 (stock Kp LERP, OLD cave decode)"}
IMG = {"V282": LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V283": LG.FW + "_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V280r2": LG.FW + LG.IMAGES["V280r2"]}
CELL_OF = {"r39": "V282", "r38": "V283", "r37": "V283", "r36": "V283", "r35": "V281r3", "r34": "V280r2"}
MARKS = (689.659, 927.699)             # route-relative userBookmark times, from extract_r39_v280cache.py
PRE, POST = 20.0, 5.0                  # bookmark search window: he presses a LITTLE BIT AFTER the episode
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def band(x, lo, hi, fs=FS):
    return C20.bamp(x, lo, hi, fs)


def line_of(x, fs, lo=15.0, hi=26.0, nfft=4096):
    x = np.asarray(x, float)
    if len(x) < 32:
        return np.nan, np.nan
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    return G2.locate(f, P, lo, hi, R=Rp)


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


# ====================================================================================================== load
def load_all():
    cells = {k: GI.read_cells(p) for k, p in IMG.items()}
    G = {}
    for tag in ALL:
        print("loading %s ..." % tag, flush=True)
        g = C20.load(tag)
        g["tr"] = g["t"] - g["t"][0]
        c = cells[CELL_OF[tag]]
        g["idx"], g["sgn"] = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
        B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
        k14, P14, tn14, res14 = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        g["b4_n"] = len(b4)
        for bit in (3, 4, 5, 6, 7):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
            g["s%d" % bit] = 1.0 - 2.0 * g["bit%d" % bit]
        g["s_T"] = np.sign(g["T100"])
        g["cells"] = c
        G[tag] = g
    return cells, G


# ====================================================================================================== main
def main():
    cells, G = load_all()

    pr("=" * 172)
    pr("V282, THE FIRST DRIVE OF THE Ki-0 BASE -- route r39 (75604b0a432fdc89_00000039--f56039af87, 16 seg, 2026-09-04)")
    pr("  subagent grind39.  Analysis only.  Comparators r36/r37/r38 (V283, Ki 50), r35 (V281 rev 3), r34 (V280 rev 2).")
    pr("=" * 172)
    pr("\nCELLS READ FROM THE IMAGES (variant slot %d) -- V282 vs its neighbours" % LG.SEL)
    pr("  %-8s %-5s %-34s %-8s %-9s %-10s %s" % ("image", "Ki", "Kp Y", "Kd Y0", "fb clamp", "0xC6446", "map Y (slot 7)"))
    for k in ("V282", "V283", "V281r3", "V280r2"):
        c = cells[k]
        b = open(IMG[k], "rb").read()
        ki = int.from_bytes(b[0xC63E6:0xC63E8], "little"); lb = int.from_bytes(b[0xC6446:0xC6448], "little")
        pr("  %-8s %-5d %-34s %-8d %-9d %-10d %s" % (k, ki, c["kp_Y"].astype(int).tolist(), int(c["kd_Y"][0]),
                                                     int(c["fb_clamp"]), lb, c["map_Y"].astype(int).tolist()))
    pr("  [EVIDENCE, read from the four images] V282 and V281 rev 3 differ in NO calibration cell (V282's four edits")
    pr("  are ld.h displacements inside the cave); V282 -> V283 is Ki 0 -> 50 and nothing else.  0xC6446 = 5244 on all.")

    pr("\nROUTES")
    pr("  %-5s %-46s %9s %11s %10s %s" % ("route", "build", "length s", "eng-lat s", "0x14A b4", "0x18F resid p50/p90 ms"))
    for tag in ALL:
        g = G[tag]
        pr("  %-5s %-46s %9.1f %11.1f %10d      %.1f / %.1f" % (
            tag, BUILD[tag], g["tr"][-1], g["eng"].sum() / FS, g["b4_n"], 1e3 * g["res"]["f18"][0], 1e3 * g["res"]["f18"][1]))
    pr("  'engaged' = LATERALLY engaged everywhere in this file: 0xE4 STEER_REQUEST AND 0x18F STEER_CONTROL_ACTIVE.")

    # --------------------------------------------------------------------------- 0. attribution
    pr("\n" + "=" * 172)
    pr("0. BUILD ATTRIBUTION FROM THE TAP, not from the label")
    pr("=" * 172)
    pr("  a) the 0x1AB (427) delivered-torque tap field.  dec39's cache descriptor (r39_1ab.json) labels it")
    pr("     'gp-0x6B38 sar0, 0.2000 counts per LSB'.  The wire structure says otherwise:")
    for tag in ("r39", "r38", "r35"):
        D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
        b0, b1 = D["b0"].astype(int), D["b1"].astype(int)
        fld = ((b0 & 3) << 8) | b1
        pr("     %-5s 0x1AB b0 values %-18s field max %4d ; magnitude (field & 511) max %4d ; sar-3 (x8) decode |T| max %5d counts"
           % (tag, str(np.unique(b0).tolist()), fld.max(), (fld & 511).max(), 8 * (fld & 511).max()))
    pr("     [EVIDENCE] b0 takes only {128,129,130} on r35/r38/r39 alike -- bit 9 is the SIGN, the low 8 bits the")
    pr("     magnitude, identical structure on all three.  A sar-0 decode would cap |T| on r39 at ~207 counts, but")
    pr("     the chain and every prior route put |T| at 400-2500 counts.  The kit's sar-3 (x8) decode is the one that")
    pr("     matches, and it is what every number below uses.  ==> dec39's 'sar0 / 0.2 per LSB' descriptor line is")
    pr("     REPORTED as a defect in that cache's metadata; not acted on, and no number here depends on it.")

    pr("\n  b) Ki on the wire (V282 claims Ki = 0; V283 measured 51.9-52.1 on r36-r38) and Kp: BOTH are fitted in the")
    pr("     companion script v282_read_r39_stall_ring.py, which calls v283_read_r36_r38.ki_fit directly.")
    pr("     Summarised here so this file stands alone; the numbers live in _scratch/v282_read_r39_stall_ring.txt.")
    pr("\n  c) the V282 cave itself.  Bits 5 and 6 were REPOINTED by V282; on the OLD decode (r34/r35) bit 6 is dead.")
    pr("     Route-wide bit-6 duty is the liveness instrument; it is in the Q3 FAIL-gate table below.")

    # =========================================================================== Q1
    pr("\n" + "=" * 172)
    pr("Q1. THE TWO BOOKMARKED EPISODES.  userBookmark at route t = %.2f s (segment 11) and t = %.2f s (segment 15)." % MARKS)
    pr("    The operator presses a LITTLE BIT AFTER the grinding, so the search window is mark -%.0f s .. +%.0f s." % (PRE, POST))
    pr("    Window justified below by where the 18-22 Hz and 6-8.5 Hz envelope peaks actually land relative to the mark.")
    pr("=" * 172)
    g = G["r39"]; c = g["cells"]
    ep_out = []
    for mk in MARKS:
        a0 = int((mk - PRE) * FS); b0 = int(min(len(g["t"]) - 1, (mk + POST) * FS))
        pr("\n" + "-" * 172)
        pr("BOOKMARK at t = %.2f s -- window %.1f .. %.1f s" % (mk, mk - PRE, mk + POST))
        pr("-" * 172)
        pr("  per-second trace (bar band amps RAW counts; rate deg/s; T = the 427 tap):")
        pr("   %7s %5s %6s %7s %5s %6s %7s | %9s %8s | %9s %8s | %8s %5s %11s" % (
            "t", "v", "ang", "cmd", "idx", "|tq|", "T", "bar18-22", "bar6-10", "rate18-22", "rate6-10", "tap18-22", "eng", "b6/b5/b4"))
        for s in range(a0, b0 - 100, 100):
            e = s + 100
            sel = (g["T_t"] >= g["t"][s]) & (g["T_t"] < g["t"][e])
            tp = band(g["T"][sel], 18, 22, FST) if sel.sum() > 40 else np.nan
            pr("   %7.1f %5.1f %6.0f %7.0f %5.0f %6.0f %7.0f | %9.0f %8.0f | %9.2f %8.2f | %8.0f %5.2f %.2f/%.2f/%.2f" % (
                g["tr"][s], g["vego"][s:e].mean(), np.median(g["ang"][s:e]), np.median(g["cmd"][s:e]),
                np.median(g["idx"][s:e]), np.median(np.abs(g["bar"][s:e])), np.median(g["T100"][s:e]),
                band(g["bar"][s:e], 18, 22), band(g["bar"][s:e], 6, 10),
                band(g["wire"][s:e], 18, 22) / V.CPD, band(g["wire"][s:e], 6, 10) / V.CPD,
                tp, g["eng"][s:e].mean(), g["bit6"][s:e].mean(), g["bit5"][s:e].mean(), g["bit4"][s:e].mean()))
        env20 = GI.envelope(g["bar"][a0:b0], 20.1, FS, bw=2.0)
        env7 = GI.envelope(g["bar"][a0:b0], 7.3, FS, bw=1.5)
        k20 = int(np.argmax(env20)); k7 = int(np.argmax(env7))
        pr("\n  envelope peaks in the window: 18-22 Hz %5.0f raw at t %.2f s (mark %+.2f s) ; 6-8.5 Hz %5.0f raw at t %.2f s (mark %+.2f s)"
           % (env20[k20], g["tr"][a0 + k20], g["tr"][a0 + k20] - mk, env7[k7], g["tr"][a0 + k7], g["tr"][a0 + k7] - mk))
        for lab, kk, envx in (("20 Hz", k20, env20), ("7.3 Hz", k7, env7)):
            a = max(a0, a0 + kk - 100); b = min(b0, a0 + kk + 100)
            f_line, prom = line_of(g["bar"][a:b], FS)
            fq, pq = line_of(g["bar"][a:b], FS, 5, 12)
            sel = (g["T_t"] >= g["t"][a]) & (g["T_t"] <= g["t"][b - 1])
            o = GI.eval_window(g, a, b, c, lo=18.0, hi=22.0) if lab == "20 Hz" else GI.eval_window(g, a, b, c, lo=6.0, hi=8.5)
            ee = envx[a - a0:b - a0]
            # envelope SHAPE is fitted on a wider +-3 s window so the rise and the collapse are both inside it
            wa = max(a0, a0 + kk - 300); wb = min(b0, a0 + kk + 300)
            ew = envx[wa - a0:wb - a0]
            gu, du, gd, dd = GI.growth_fit(g["tr"][wa:wb], ew)
            pr("\n  CORE around the %s peak, t %.2f .. %.2f s (2.0 s):" % (lab, g["tr"][a], g["tr"][b - 1]))
            pr("    lines: most prominent 15-26 Hz peak %.2f Hz x%.0f ; 5-12 Hz peak %.2f Hz x%.0f" % (f_line, prom, fq, pq))
            pr("    bands (raw / deg/s): bar 6-10 %4.0f | 10-15 %4.0f | 15-18 %4.0f | 18-22 %4.0f | 22-26 %4.0f | 24-28 %4.0f (control)"
               % (band(g["bar"][a:b], 6, 10), band(g["bar"][a:b], 10, 15), band(g["bar"][a:b], 15, 18),
                  band(g["bar"][a:b], 18, 22), band(g["bar"][a:b], 22, 26), band(g["bar"][a:b], 24, 28)))
            pr("                         rate 6-10 %.2f | 18-22 %.2f | 24-28 %.2f deg/s ; tap 18-22 %.0f ; |T| p50 %.0f"
               % (band(g["wire"][a:b], 6, 10) / V.CPD, band(g["wire"][a:b], 18, 22) / V.CPD,
                  band(g["wire"][a:b], 24, 28) / V.CPD,
                  band(g["T"][sel], 18, 22, FST) if sel.sum() > 40 else np.nan, med(np.abs(g["T100"][a:b]))))
            pr("    operating point: v %.2f m/s | angle p50 %+.0f (%+.0f .. %+.0f) | cmd p50 %.0f | idx p50/p90 %.0f/%.0f | |tq| p50/p90 %.0f/%.0f raw"
               % (g["vego"][a:b].mean(), np.median(g["ang"][a:b]), g["ang"][a:b].min(), g["ang"][a:b].max(),
                  np.median(g["cmd"][a:b]), np.median(g["idx"][a:b]), np.percentile(g["idx"][a:b], 90),
                  np.median(np.abs(g["bar"][a:b])), np.percentile(np.abs(g["bar"][a:b]), 90)))
            pr("                     |rate| p50/p90 %.1f/%.1f deg/s | engaged %.2f" % (
                med(np.abs(g["wire"][a:b]) / V.CPD), np.percentile(np.abs(g["wire"][a:b]) / V.CPD, 90), g["eng"][a:b].mean()))
            pr("    RAILS (1 kHz mirror, V282 cells, live fade): P %.3f  D %.3f  sum %.3f  T cap %.3f  fb clamp %.3f  fade p50/min %.2f/%.2f"
               % (o["prail"], o["drail"], o["srail"], o["tcap"], o["fbclp"], o["fade"], o["fademin"]))
            pr("    mirror in band: T_sim %.0f vs tap %.0f (P %.0f, D %.0f) ; corr %.2f ; band corr %.2f ; coh %.2f ; phase %+.0f deg ; Kp %.0f idx %.0f"
               % (o["amp_sim"], o["amp_meas"], o["amp_P"], o["amp_D"], o["corr"], o["corr_band"], o["coh"], o["phase"], o["kp"], o["idx"]))
            pr("    envelope shape (fitted over t %.2f .. %.2f s): rise %+.2f /s over %.2f s, decay %+.2f /s over %.2f s, peak %.0f raw"
               % (g["tr"][wa], g["tr"][wb - 1], gu, du, gd, dd, ew.max()))
            pr("                    within the 2 s core: sd/mean %.2f, fraction within 50%% of peak %.2f  (r35's incident: 0.78 / 0.32)"
               % (ee.std() / max(ee.mean(), 1e-9), float(np.mean(ee >= 0.5 * ee.max()))))
            pr("    cave bits over the core: b7 %.2f  b6 %.2f  b5 %.2f  b4 %.2f  b3 %.2f"
               % (g["bit7"][a:b].mean(), g["bit6"][a:b].mean(), g["bit5"][a:b].mean(), g["bit4"][a:b].mean(), g["bit3"][a:b].mean()))
            ep_out.append(dict(mark=mk, kind=lab, t0=float(g["tr"][a]), f=float(f_line), prom=float(prom),
                               amp=float(band(g["bar"][a:b], 18, 22)), amp7=float(band(g["bar"][a:b], 6, 10)),
                               rise=float(gu), decay=float(gd), peak=float(ee.max()),
                               idx=float(np.median(g["idx"][a:b])), v=float(g["vego"][a:b].mean()),
                               tq=float(np.median(np.abs(g["bar"][a:b]))), rate=float(med(np.abs(g["wire"][a:b]) / V.CPD)),
                               ang=float(np.median(g["ang"][a:b])), T=float(med(np.abs(g["T100"][a:b]))),
                               prail=float(o["prail"]), drail=float(o["drail"]), tcap=float(o["tcap"]),
                               ampP=float(o["amp_P"]), ampD=float(o["amp_D"])))
        pr("\n  20 Hz envelope at 0.25 s steps through the window (bar raw):")
        row = []
        for kk in range(0, len(env20) - 25, 25):
            row.append("%.0f" % env20[kk])
        pr("    t %.1f -> %.1f : %s" % (g["tr"][a0], g["tr"][b0 - 1], " ".join(row)))
        pr("  6-8.5 Hz envelope at 0.25 s steps through the same window (bar raw):")
        row = []
        for kk in range(0, len(env7) - 25, 25):
            row.append("%.0f" % env7[kk])
        pr("    %s" % " ".join(row))

    # =========================================================================== Q2
    pr("\n" + "=" * 172)
    pr("Q2. UNSUPERVISED CENSUS of the 18-22 Hz creep line -- r35's method, unchanged (v283_grind_census.py sec 1/2):")
    pr("    2 s windows, step 0.5 s, engaged LATERAL, v < 6 m/s; 'present' = most prominent 15-26 Hz peak with")
    pr("    prominence >= 8 AND bar 18-22 >= 40 raw.  BANDS ONLY -- nothing here declares a symptom fixed or unfixed.")
    pr("=" * 172)
    rows = []
    for tag in ALL:
        gg = G[tag]
        msk = gg["eng"] & (gg["vego"] < 6.0)
        for aa, bb in C20.runs(msk, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw = line_of(gg["bar"][s:e], FS)
                fq, pq = line_of(gg["bar"][s:e], FS, 5, 12)
                rows.append(dict(tag=tag, t=gg["tr"][s], f0=f0w, prom=promw, f610=fq, p610=pq,
                                 amp=band(gg["bar"][s:e], 18, 22), amp610=band(gg["bar"][s:e], 6, 10),
                                 ramp=band(gg["wire"][s:e], 18, 22) / V.CPD,
                                 rate=float(np.mean(np.abs(gg["wire"][s:e])) / V.CPD),
                                 v=float(gg["vego"][s:e].mean()), ang=float(np.median(np.abs(gg["ang"][s:e]))),
                                 T=float(np.median(np.abs(gg["T100"][s:e]))), idx=float(np.median(gg["idx"][s:e])),
                                 tq=float(np.median(np.abs(gg["bar"][s:e]))), b6=float(gg["bit6"][s:e].mean()),
                                 creep=bool(1.0 <= gg["vego"][s:e].mean() < 3.0),
                                 hoff=bool(np.median(np.abs(gg["bar"][s:e])) < 400)))
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)

    pr("\n  2a. ALL engaged v < 6 windows")
    pr("  %-5s %-8s %6s %6s %6s | %-24s | %-18s | %s" % ("route", "build", "n", "pres", "%", "f mean sd p10/p90",
                                                          "amp p50/p90/max", "by idx bin: present % (amp p50, n)"))
    for tag in ALL:
        sel = R["tag"] == tag; ps = sel & pres
        if not sel.any():
            continue
        bins = []
        for lab, bs in (("0-20", R["idx"] <= 20), ("20-60", (R["idx"] > 20) & (R["idx"] <= 60)),
                        ("60-120", (R["idx"] > 60) & (R["idx"] <= 120)), (">120", R["idx"] > 120)):
            b = sel & bs
            bins.append("%s: %.0f%% (%.0f, n%d)" % (lab, 100 * pres[b].mean() if b.any() else np.nan,
                                                    np.median(R["amp"][b]) if b.any() else np.nan, b.sum()))
        pr("  %-5s %-8s %6d %6d %6.0f | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f | %s" % (
            tag, GRP[tag], sel.sum(), ps.sum(), 100 * pres[sel].mean(),
            R["f0"][ps].mean(), R["f0"][ps].std(), *np.percentile(R["f0"][ps], (10, 90)),
            *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max(), " ; ".join(bins)))
    for grp in ("V282", "V283", "V281r3", "V280r2"):
        sel = np.isin(R["tag"], [t for t in ALL if GRP[t] == grp]); ps = sel & pres
        if not sel.any():
            continue
        pr("  %-5s %-8s %6d %6d %6.0f | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f | (pooled)" % (
            "POOL", grp, sel.sum(), ps.sum(), 100 * pres[sel].mean(), R["f0"][ps].mean(), R["f0"][ps].std(),
            *np.percentile(R["f0"][ps], (10, 90)), *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max()))

    pr("\n  2b. THE OPERATOR'S OWN STRATUM -- engaged LATERAL, HANDS-OFF (|bar| < 400 raw), CREEP 1-3 m/s")
    pr("  %-5s %-8s %7s %7s %7s %9s %9s %9s %10s %8s %8s" % ("route", "build", "n win", "pres", "%", "amp p50",
                                                              "amp p90", "amp max", "rate18-22", "idx p50", "v p50"))
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            pr("  %-5s %-8s %7d   (too thin)" % (tag, GRP[tag], sel.sum())); continue
        pr("  %-5s %-8s %7d %7d %7.0f %9.0f %9.0f %9.0f %10.2f %8.0f %8.2f" % (
            tag, GRP[tag], sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
            np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max(),
            np.median(R["ramp"][sel]), np.median(R["idx"][sel]), np.median(R["v"][sel])))
    for grp in ("V282", "V283", "V281r3", "V280r2"):
        sel = np.isin(R["tag"], [t for t in ALL if GRP[t] == grp]) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            continue
        pr("  %-5s %-8s %7d %7d %7.0f %9.0f %9.0f %9.0f %10.2f %8.0f %8.2f   (pooled)" % (
            "POOL", grp, sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
            np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max(),
            np.median(R["ramp"][sel]), np.median(R["idx"][sel]), np.median(R["v"][sel])))

    pr("\n  2c. THE CONFOUND, MADE EXPLICIT -- idx-MATCHED presence and amplitude in the same stratum.")
    pr("      r39's outer loop is ~1.70x r35's, so it spends its creep time at a different demand index;")
    pr("      these rows hold idx fixed, and the last block reweights each route onto r35's own idx mass.")
    pr("  %-5s %-8s | %s" % ("route", "build", "idx bin: present % (amp p50 raw, n windows)"))
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        cc = []
        for lab, bs in (("0-20", R["idx"] <= 20), ("20-60", (R["idx"] > 20) & (R["idx"] <= 60)),
                        ("60-120", (R["idx"] > 60) & (R["idx"] <= 120)), (">120", R["idx"] > 120)):
            b = sel & bs
            cc.append("%-6s %3.0f%% (%3.0f, n%3d)" % (lab, 100 * pres[b].mean() if b.any() else np.nan,
                                                      np.median(R["amp"][b]) if b.any() else np.nan, b.sum()))
        pr("  %-5s %-8s | %s" % (tag, GRP[tag], "  ".join(cc)))
    ref = (R["tag"] == "r35") & R["creep"] & R["hoff"]
    edges = np.array([0, 20, 60, 120, 1e9])
    wref = np.array([((R["idx"][ref] >= edges[i]) & (R["idx"][ref] < edges[i + 1])).mean() for i in range(4)])
    pr("\n      reweighted onto r35's own creep idx distribution %s:" % np.round(wref, 3).tolist())
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        p, amps, wts = 0.0, 0.0, 0.0
        for i in range(4):
            b = sel & (R["idx"] >= edges[i]) & (R["idx"] < edges[i + 1])
            if b.sum() >= 3 and wref[i] > 0:
                p += wref[i] * pres[b].mean(); amps += wref[i] * np.median(R["amp"][b]); wts += wref[i]
        pr("      %-5s %-8s reweighted present %5.1f %%   amp p50 %5.0f raw   (coverage %.2f of r35's idx mass)"
           % (tag, GRP[tag], 100 * p / max(wts, 1e-9), amps / max(wts, 1e-9), wts))

    pr("\n  2d. RATE OF OCCURRENCE -- contiguous line-present EPISODES per 100 s of engaged hands-off creep,")
    pr("      and per ENGAGED MINUTE of the whole route (the operator's 'various grinding moments').")
    pr("  %-5s %-8s %10s %9s %11s %10s %10s %10s %12s" % (
        "route", "build", "creep s", "episodes", "per 100 s", "ep s p50", "ep amp p50", "ep amp max", "per eng min"))
    epi_all = {}
    for tag in ALL:
        gg = G[tag]
        m = gg["eng"] & (gg["vego"] >= 1.0) & (gg["vego"] < 3.0) & (np.abs(gg["bar"]) < 400)
        secs = m.sum() / FS
        sel = np.flatnonzero(R["tag"] == tag)
        if len(sel) == 0 or secs < 5:
            pr("  %-5s %-8s %10.1f   (too thin)" % (tag, GRP[tag], secs)); continue
        wt, wp = R["t"][sel], pres[sel]
        j = np.clip(np.searchsorted(wt, gg["tr"] - 1.0), 0, len(wt) - 1)
        near = np.abs(wt[j] + 1.0 - gg["tr"]) < 1.5
        hot = m & near & wp[j]
        eps = C20.runs(hot, int(1.0 * FS))
        durs = np.array([(b - a) / FS for a, b in eps]) if eps else np.array([])
        amps = np.array([band(gg["bar"][a:b], 18, 22) for a, b in eps]) if eps else np.array([])
        engmin = gg["eng"].sum() / FS / 60.0
        epi_all[tag] = (eps, durs, amps, secs, engmin)
        pr("  %-5s %-8s %10.1f %9d %11.2f %10.2f %10.0f %10.0f %12.3f" % (
            tag, GRP[tag], secs, len(eps), 100 * len(eps) / max(secs, 1e-9),
            med(durs), med(amps), amps.max() if len(amps) else np.nan, len(eps) / max(engmin, 1e-9)))
    for grp in ("V282", "V283", "V281r3", "V280r2"):
        ts = [t for t in ALL if GRP[t] == grp and t in epi_all]
        if not ts:
            continue
        ne = sum(len(epi_all[t][0]) for t in ts); ss = sum(epi_all[t][3] for t in ts); em = sum(epi_all[t][4] for t in ts)
        aa = np.concatenate([epi_all[t][2] for t in ts if len(epi_all[t][2])]) if any(len(epi_all[t][2]) for t in ts) else np.array([np.nan])
        pr("  %-5s %-8s %10.1f %9d %11.2f %10s %10.0f %10.0f %12.3f  (pooled)" % (
            "POOL", grp, ss, ne, 100 * ne / max(ss, 1e-9), "", np.nanmedian(aa), np.nanmax(aa), ne / max(em, 1e-9)))

    pr("\n  2e. r39's OWN loudest line-present stretches (engaged, v < 6, >= 1.0 s), ranked by 18-22 envelope peak.")
    gg = G["r39"]
    sel = np.flatnonzero(R["tag"] == "r39")
    wt, wp = R["t"][sel], pres[sel]
    j = np.clip(np.searchsorted(wt, gg["tr"] - 1.0), 0, len(wt) - 1)
    near = np.abs(wt[j] + 1.0 - gg["tr"]) < 1.5
    hot = gg["eng"] & (gg["vego"] < 6.0) & near & wp[j]
    eps39 = C20.runs(hot, int(1.0 * FS))
    pr("      %d stretches; %.1f s of engaged v < 6 on the route in total"
       % (len(eps39), (gg["eng"] & (gg["vego"] < 6.0)).sum() / FS))
    top = []
    for a, b in eps39:
        env = GI.envelope(gg["bar"][a:b], 20.1, FS, bw=2.0)
        top.append((float(env.max()), float(gg["tr"][a]), (b - a) / FS, band(gg["bar"][a:b], 18, 22),
                    band(gg["bar"][a:b], 6, 10), float(np.median(gg["idx"][a:b])), float(gg["vego"][a:b].mean()),
                    float(np.median(np.abs(gg["bar"][a:b]))), float(med(np.abs(gg["wire"][a:b]) / V.CPD)),
                    float(np.median(np.abs(gg["ang"][a:b])))))
    top.sort(reverse=True)
    pr("      %8s %8s %6s %9s %9s %7s %6s %8s %9s %7s %12s" % ("env peak", "t0", "dur", "bar18-22", "bar6-10", "idx", "v", "|tq|", "|rate|", "|ang|", "vs bookmark"))
    for x in top[:20]:
        near_m = MARKS[0] if abs(x[1] - MARKS[0]) < abs(x[1] - MARKS[1]) else MARKS[1]
        d = x[1] - near_m
        pr("      %8.0f %8.1f %6.1f %9.0f %9.0f %7.0f %6.1f %8.0f %9.1f %7.0f %12s" % (
            x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], ("%+.1f s" % d) if abs(d) < 30 else "-"))

    pr("\n  2f. THE OTHER BAND.  Both bookmarks are dominated by a 5-12 Hz line, not by 18-22 Hz, so the same census")
    pr("      windows are reported at 6-10 Hz as well.  NO new presence gate is invented -- these are band")
    pr("      AMPLITUDES on identical windows, plus the 5-12 Hz peak's own prominence.")
    pr("  %-5s %-8s | %-42s | %s" % ("route", "build", "engaged v<6: bar 6-10 p50/p90/max raw", "creep hands-off 1-3: p50/p90/max ; 5-12 prom p50"))
    for tag in ALL:
        sel = R["tag"] == tag
        cr = sel & R["creep"] & R["hoff"]
        if not sel.any():
            continue
        pr("  %-5s %-8s | %10.0f %10.0f %10.0f  (n%4d)    | %8.0f %8.0f %8.0f  (n%4d)  %6.1f" % (
            tag, GRP[tag], *np.percentile(R["amp610"][sel], (50, 90)), R["amp610"][sel].max(), sel.sum(),
            *(np.percentile(R["amp610"][cr], (50, 90)) if cr.sum() > 3 else (np.nan, np.nan)),
            R["amp610"][cr].max() if cr.sum() else np.nan, cr.sum(),
            np.median(R["p610"][cr]) if cr.sum() else np.nan))
    pr("\n      and in the LOADED-TURN stratum the two bookmarks actually sit in (engaged, |ang| >= 30, idx >= 68,")
    pr("      any speed) -- 2 s windows, 0.5 s step, same band estimator:")
    pr("  %-5s %-8s %9s | %-34s | %-34s | %s" % ("route", "build", "seconds", "bar 6-10 p50/p90/max", "bar 18-22 p50/p90/max", "rate 6-10 p50 deg/s"))
    for tag in ALL:
        gg = G[tag]
        m = gg["eng"] & (np.abs(gg["ang"]) >= 30) & (gg["idx"] >= 68)
        a6, a20, r6 = [], [], []
        for aa, bb in C20.runs(m, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                a6.append(band(gg["bar"][s:e], 6, 10)); a20.append(band(gg["bar"][s:e], 18, 22))
                r6.append(band(gg["wire"][s:e], 6, 10) / V.CPD)
        if len(a6) < 5:
            pr("  %-5s %-8s %9.1f | (n %d windows -- too thin)" % (tag, GRP[tag], m.sum() / FS, len(a6))); continue
        pr("  %-5s %-8s %9.1f | %10.0f %10.0f %10.0f   | %10.0f %10.0f %10.0f   | %8.2f  (n %d)" % (
            tag, GRP[tag], m.sum() / FS, *np.percentile(a6, (50, 90)), max(a6),
            *np.percentile(a20, (50, 90)), max(a20), np.median(r6), len(a6)))

    # =========================================================================== Q3
    pr("\n" + "=" * 172)
    pr("Q3. PREREG-V282-READ.md, SCORED AS WRITTEN.  No threshold moved after the log landed.")
    pr("=" * 172)
    STRATA = [
        ("(A/B) creep engaged hands-off  v 1-3, |bar|<400",
         lambda x: x["eng"] & (x["vego"] >= 1.0) & (x["vego"] < 3.0) & (np.abs(x["bar"]) < 400)),
        ("      creep engaged hands-off  v 1-6, |bar|<400",
         lambda x: x["eng"] & (x["vego"] >= 1.0) & (x["vego"] < 6.0) & (np.abs(x["bar"]) < 400)),
        ("(D)   loaded high-angle engaged  v 2-9, |ang|>30, idx>=68",
         lambda x: x["eng"] & (x["vego"] >= 2.0) & (x["vego"] < 9.0) & (np.abs(x["ang"]) > 30) & (x["idx"] >= 68)),
        ("      loaded high-angle engaged  v 2-9, |ang|>30 (any idx)",
         lambda x: x["eng"] & (x["vego"] >= 2.0) & (x["vego"] < 9.0) & (np.abs(x["ang"]) > 30)),
        ("      highway engaged  v > 15", lambda x: x["eng"] & (x["vego"] > 15.0)),
        ("      all engaged lateral", lambda x: x["eng"]),
    ]
    pr("\n  FAIL GATE, checked BEFORE any duty is interpreted:")
    pr("  '(A) or (B) reading 0.000 or 1.000 over >= 20 s of engaged creep' -> do not act on any r24 number.")
    pr("  %-5s %-8s %8s %8s %8s %8s %8s %9s   %s" % ("route", "build", "bit7", "bit6", "bit5", "bit4", "bit3", "creep s", "verdict on the gate"))
    fails = {}
    for tag in ALL:
        gg = G[tag]; m = STRATA[0][1](gg); secs = m.sum() / FS
        d6 = gg["bit6"][m].mean() if m.any() else np.nan
        d5 = gg["bit5"][m].mean() if m.any() else np.nan
        deg = (secs >= 20.0) and (d6 <= 1e-6 or d6 >= 1 - 1e-6 or d5 <= 1e-6 or d5 >= 1 - 1e-6)
        fails[tag] = bool(deg)
        pr("  %-5s %-8s %8.4f %8.4f %8.4f %8.4f %8.4f %9.1f   creep bit6 %.4f bit5 %.4f -> %s" % (
            tag, GRP[tag], gg["bit7"].mean(), gg["bit6"].mean(), gg["bit5"].mean(), gg["bit4"].mean(), gg["bit3"].mean(),
            secs, d6, d5, "DEGENERATE = FAIL" if deg else "non-degenerate = PASS"))
    pr("  (the five columns are ROUTE-WIDE duties over every logged frame; the gate reads the creep-stratified pair)")
    pr("  r34/r35 carry the OLD cave decode on which bit 6 was recorded dead -- they are the NEGATIVE CONTROL.")

    pr("\n  (A)/(B)/(D) COMPARATOR DUTIES BY STRATUM.  bit6 = P(|r24| >= |T|) ; bit5 = P(|r24| >= |aggregator|)")
    A_by = {}
    D_by = {}
    for name, fn in STRATA:
        pr("\n  %s" % name)
        pr("    %-5s %-8s %8s %8s %9s %8s %8s %8s %8s" % ("route", "build", "bit6", "bit5", "seconds", "|T| p50", "idx p50", "|bar|p50", "v p50"))
        pool6, pool5 = {}, {}
        for tag in ALL:
            gg = G[tag]; m = fn(gg)
            if m.sum() < 100:
                pr("    %-5s %-8s     (n %d frames -- too thin)" % (tag, GRP[tag], m.sum())); continue
            pool6.setdefault(GRP[tag], []).append(gg["bit6"][m]); pool5.setdefault(GRP[tag], []).append(gg["bit5"][m])
            if name.startswith("(A/B)"):
                A_by[tag] = (float(gg["bit6"][m].mean()), float(gg["bit5"][m].mean()), float(m.sum() / FS))
            if name.startswith("(D)"):
                D_by[tag] = (float(gg["bit6"][m].mean()), float(m.sum() / FS), float(np.median(np.abs(gg["T100"][m]))))
            pr("    %-5s %-8s %8.4f %8.4f %9.1f %8.0f %8.0f %8.0f %8.2f" % (
                tag, GRP[tag], gg["bit6"][m].mean(), gg["bit5"][m].mean(), m.sum() / FS,
                np.median(np.abs(gg["T100"][m])), np.median(gg["idx"][m]), np.median(np.abs(gg["bar"][m])), np.median(gg["vego"][m])))
        for grp in ("V282", "V283", "V281r3", "V280r2"):
            if grp in pool6:
                a = np.concatenate(pool6[grp]); b = np.concatenate(pool5[grp])
                se = np.sqrt(a.mean() * (1 - a.mean()) / max(1, len(a) / 25.0))
                pr("    %-5s %-8s %8.4f %8.4f %9.1f      (pooled; bit6 +-%.3f at 1 sd, blocks of 0.25 s)"
                   % ("POOL", grp, a.mean(), b.mean(), len(a) / FS, se))

    pr("\n  bit-6 duty vs |T| -- the AC-vs-(DC+AC) bias that made (D) uninformative on r36-r38 (§0.6 of")
    pr("  V282-R24-TAP-READ-r36-r38).  Re-checked on the Ki-0 base:")
    pr("    %-5s %-8s %s" % ("route", "build", "bit6 by |T| band: <300 | 300-600 | >=600  (n frames)"))
    for tag in ("r39", "r38", "r37", "r36"):
        gg = G[tag]; m = gg["eng"]
        cc = []
        for lab, sel_ in (("<300", np.abs(gg["T100"]) < 300), ("300-600", (np.abs(gg["T100"]) >= 300) & (np.abs(gg["T100"]) < 600)),
                          (">=600", np.abs(gg["T100"]) >= 600)):
            b = m & sel_
            cc.append("%-8s %.4f (n%6d)" % (lab, gg["bit6"][b].mean() if b.any() else np.nan, b.sum()))
        pr("    %-5s %-8s %s" % (tag, GRP[tag], "  ".join(cc)))

    pr("\n  CLOSED-FORM REPLAY on r39's OWN torsion-bar data (v282_prereg_duty.py's r24_series, verbatim):")
    pr("  what bit 6 WOULD read at each candidate 0xC6446 arm.  This is the prereg's own calibration ladder.")
    for name, fn in (STRATA[0], STRATA[2]):
        pr("\n    %s" % name)
        pr("      %-28s %10s %10s %12s %12s %10s" % ("0xC6446 arm", "bit6 pred", "bit5 pred*", "|r24| p50", "|T| p50", "n frames"))
        gg = G["r39"]; m = fn(gg)
        if m.sum() < 200:
            pr("      (too thin)"); continue
        for gain in GAINS:
            r = r24_series(gg["bar"], gain); T = gg["T100"]
            b6 = (np.abs(r) >= np.abs(T))[m]; b5 = (np.abs(r) >= np.abs(T + r))[m]
            pr("      %-28s %10.4f %10.4f %12.0f %12.0f %10d" % (
                GLBL[gain], b6.mean(), b5.mean(), np.median(np.abs(r)[m]), np.median(np.abs(T)[m]), m.sum()))
        meas = float(gg["bit6"][m].mean())
        pr("      %-28s %10.4f    <== MEASURED ON THE WIRE (r39, V282, Ki 0)" % ("V282 as flown", meas))
        base = r24_series(gg["bar"], 5244.0)
        best = None
        for s in np.linspace(0.05, 1.5, 291):
            d = float((np.abs(s * base) >= np.abs(gg["T100"]))[m].mean())
            e = abs(d - meas)
            if best is None or e < best[0]:
                best = (e, s, d)
        pr("      INVERSION: |r24|_wire / |r24|_closed-form = s = %.2f reproduces the measured duty (%.4f vs %.4f measured)."
           % (best[1], best[2], meas))
        pr("      (* bit5 pred uses |T + r24| as a LOWER bound on the aggregator, so it is an UPPER bound on that duty)")

    pr("\n  (C) PHASE OF bit 4 = sign(r24) AGAINST THE WHEEL RATE, 18-22 Hz, creep.  PREREG: -6 +- 25 deg.")
    pr("      Convention: tf(rate_x -> s4), rate_x = -wire/CPD (the sign the PID sees); s = +1 when the cell is >= 0.")
    pr("      This is the convention in which the r36-r38 read got V283 -2 deg, r35 -13 deg, r34 -6 deg.")
    SHOW = [3.9, 5.5, 7.0, 8.6, 10.9, 13.3, 15.6, 18.0, 19.5, 21.1, 22.7]
    NPS = 128
    Cres = {}
    for name, fn in (STRATA[0], STRATA[1], STRATA[3]):
        for grp, tags in (("r39 V282 (Ki 0)", ("r39",)), ("V283 (r36+r37+r38)", ("r36", "r37", "r38")),
                          ("r35 V281r3", ("r35",)), ("r34 V280r2", ("r34",))):
            P = Pool(FS, NPS); secs = 0.0
            for tag in tags:
                gg = G[tag]
                for a, b in C20.runs(fn(gg), NPS):
                    if P.add({"rate": gg["rate_x"][a:b], "bar": gg["bar"][a:b], "T": gg["T100"][a:b],
                              "sT": gg["s_T"][a:b], "sR": gg["s4"][a:b], "sB": gg["s7"][a:b]}):
                        secs += (b - a) / FS
            if P.n == 0:
                continue
            f = P.f; ii = [int(np.argmin(np.abs(f - x))) for x in SHOW]
            HsR = P.tf("rate", "sR"); co = P.coh("rate", "sR")
            pr("\n    %-22s %s   (%.1f s, %d Welch windows)" % (grp, name.strip(), secs, P.n))
            pr("      f Hz              :" + "".join("%8.1f" % f[i] for i in ii))
            pr("      ph(bit4=sign r24) :" + "".join("%8.0f" % np.degrees(np.angle(HsR[i])) for i in ii))
            pr("      coherence         :" + "".join("%8.2f" % co[i] for i in ii))
            j20 = int(np.argmin(np.abs(f - 20.0)))
            ph = float(np.degrees(np.angle(HsR[j20])))
            if "1-3" in name:
                Cres.setdefault(grp, {})["creep_1_3"] = ph
            pr("      -> at %.1f Hz: %+.0f deg (coherence %.2f).  cos > 0 = DAMP, cos < 0 = PUMP." % (f[j20], ph, co[j20]))
            j7 = int(np.argmin(np.abs(f - 7.0)))
            pr("      -> at %.1f Hz: %+.0f deg (coherence %.2f)." % (f[j7], np.degrees(np.angle(HsR[j7])), co[j7]))

    pr("\n" + "-" * 172)
    pr("  DECISION RULE, applied verbatim to r39 (V282, Ki 0):")
    a39 = A_by.get("r39", (np.nan, np.nan, 0.0))
    d39 = D_by.get("r39", (np.nan, 0.0, np.nan))
    pr("    (A) bit-6 duty = %.4f over %.1f s of engaged-lateral hands-off creep 1-3 m/s." % (a39[0], a39[2]))
    if a39[0] >= 0.22:
        pr("        (A) >= 0.22  ==> FIRES: 'r24 is the dominant 20 Hz lane at the 5244 arm; 0xC6446 must NOT be cut")
        pr("        for grinding.  The grind lever is then a loop shape that keeps r24.'")
    elif a39[0] <= 0.10:
        pr("        (A) <= 0.10  ==> FIRES: 'the 1024 arm is live: r24 is ~148 counts, the SERVO is the 7 Hz pump")
        pr("        after all, creep20's ranking governs the grind, and the next trace is gp-0x671d.'")
    else:
        pr("        0.10 < (A) < 0.22 ==> FIRES: 'licenses nothing about grinding; trace gp-0x671d and re-read the")
        pr("        chain's dt factor.'")
    pr("    (B) bit-5 duty = %.4f -- prereg asked for > 0 and < 1 (the positive control).  %s"
       % (a39[1], "PASS" if 0 < a39[1] < 1 else "FAIL"))
    pr("    (D) bit-6 duty in the 7 Hz strong-turn stratum = %.4f over %.1f s (|T| p50 %.0f counts)." % d39)
    if d39[0] >= 0.5:
        pr("        (D) >= 0.5 ==> 'the r24 pump reading is confirmed on the wire'.")
    elif d39[0] < 0.2:
        pr("        (D) < 0.2 with the 7 Hz episodes present ==> literal reading is 'the SERVO is the pump'.")
    pr("    FAIL conditions: %s" % ("NONE fired on r39" if not fails.get("r39") else "FIRED on r39 -- see the gate table"))

    os.makedirs(SCR, exist_ok=True)
    json.dump(dict(marks=MARKS, episodes=ep_out, A=A_by, D=D_by, C=Cres, fail=fails),
              open(os.path.join(SCR, "v282_read_r39.json"), "w"), indent=1,
              default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else str(o)))
    with open(os.path.join(SCR, "v282_read_r39.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("wrote", os.path.join(SCR, "v282_read_r39.txt"))


if __name__ == "__main__":
    main()
