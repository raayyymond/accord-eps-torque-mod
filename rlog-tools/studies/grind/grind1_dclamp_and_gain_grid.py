# -*- coding: utf-8 -*-
"""studies/grind/grind1_dclamp_and_gain_grid.py -- two more lever classes priced with the same model.
Subagent `shape`, 2026-09-06.  ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

ITEM 3  the NONLINEAR levers: the D clamp (0xC61BA = 10240) and the P clamp (0xC61BC = 15360).
        They leave the small-signal loop shape untouched -- no waterbed, no gain-margin change -- and only
        limit the kick at a demand transient.  Priced on the 1 kHz chain mirror over the measured bursts.
ITEM 4  the (Kd, 0xC6446, Kp) grid with the LAG POLE HELD at 992/507, both gates at today's values.

Run: python grind1_dclamp_and_gain_grid.py   (writes _scratch/grind1_dclamp_and_gain_grid.txt)
"""
import os
import sys
import math
import cmath
import struct

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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


ROOT = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG = ROOT + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
B = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", B, a)[0]
LAG_A, LAG_B, FB_A, FB_B = u16(0xC63EC), u16(0xC63EE), u16(0xC63E8), u16(0xC63EA)
D_CLAMP, P_CLAMP = u16(0xC61BA), u16(0xC61BC)
FS, FST, T = 100.0, 50.0, 1e-3

z = lambda f: cmath.exp(2j * math.pi * f * T)
Hlag = lambda f, a2=LAG_A, b2=LAG_B: (b2 / 32768.0) * (1 + 1 / z(f)) / (1 - (a2 / 1024.0) / z(f))
Hfb = lambda f, a=FB_A, b=FB_B: (b / 1024.0) * (1 + 1 / z(f)) / (1 - (a / 1024.0) / z(f))
dg = lambda c: math.degrees(cmath.phase(c))
KP0, KD0, GAIN0 = 248.0, 128.0, 5244.0
Cc = lambda f, kp=KP0, kd=KD0: kp / 256.0 + (kd / 8.0) * (1 - 1 / z(f))
PH_G20 = 157.0 - dg(Cc(20, 295, 0)) - dg(Hlag(20)) - dg(Hfb(20)) - 360.0
SLOPE = -(73.0 - 28.0) / 12.0
KMAG = 0.37 / abs(Cc(20, 295, 0) * Hlag(20) * Hfb(20))


def Lc(f, kp=KP0, kd=KD0):
    ph = dg(Cc(f, kp, kd)) + dg(Hlag(f)) + dg(Hfb(f)) + PH_G20 + SLOPE * (f - 20)
    return KMAG * abs(Cc(f, kp, kd) * Hlag(f) * Hfb(f)) * cmath.exp(1j * math.radians(ph))


# ======================================================================================================
pr("=" * 150)
pr("ITEM 4 -- THE (Kd, 0xC6446, Kp) GRID, LAG POLE HELD AT 992/507, BOTH GATES AT TODAY'S VALUES")
pr("=" * 150)
pr("""
  🛑 A CORRECTION TO MY OWN sec6d FIRST, and it MATTERS for this grid.  In grind1_loop_shape_v287.py I
  applied the lag ratio to the ring's SERVO arm Ls and left the r24 arm Lr alone -- correct for a lag-pole
  edit, but it made every `0xC6446` row report a ring ratio of exactly 1.000, which is WRONG.  Lr IS the
  r24 arm (LOOP-MODEL-CONVENTION-DEFECT sec1: "a two-arm sum, a servo arm and the r24 arm"), so a
  `0xC6446` cut scales it directly.  Corrected here: Ls scales with C(7.3,Kp,Kd)/C(7.3,248,128) and Lr
  with gain/5244.  That is exactly the headroom `team-lead` is pointing at, and it is larger than my
  sec6d showed.

  GATES, both at TODAY'S values, so nothing is spent:  GM >= 1.77x on model (a)  AND  |L_tot|(7.3) <= 0.980.
  AUTHORITY: at DC the D term vanishes, so the delivered sub-rail torque scales with Kp/248.  The r24
  lane is engaged-only and carries no DC, so `0xC6446` costs no authority.  Kd costs no DC authority
  either, only transient kick.
""")
Ls_, Lr_ = 0.55 * cmath.exp(1j * math.radians(96)), 1.19 * cmath.exp(1j * math.radians(-27))
BASE_RING = abs(Ls_ + Lr_)
LANE = {20: dict(As=1.90, ps=-85.8, Ar=3.23, pr_=+5.0),      # ps = MEASURED, TAU-corrected (item 2)
        7: dict(As=2.50, ps=-63.2, Ar=3.37, pr_=+166.0)}
S_R24 = 0.43


def ring(kp, kd, gain):
    Rs = Cc(7.3, kp, kd) / Cc(7.3, KP0, KD0)
    return abs(Ls_ * Rs + Lr_ * (gain / GAIN0)) / BASE_RING


def budget(f, kp, kd, gain):
    d = LANE[f]
    R = Cc(f, kp, kd) / Cc(f, KP0, KD0)
    Ps = d["As"] * cmath.exp(1j * math.radians(d["ps"])) * R
    Pr = d["Ar"] * cmath.exp(1j * math.radians(d["pr_"])) * S_R24 * (gain / GAIN0)
    return Ps, Pr, Ps + Pr


def phL(f, kp=KP0, kd=KD0):
    return dg(Cc(f, kp, kd)) + dg(Hlag(f)) + dg(Hfb(f)) + PH_G20 + SLOPE * (f - 20)


def f180(kp, kd, lo=12.0, hi=300.0):
    g = lambda f: phL(f, kp, kd) + 180.0
    if g(lo) * g(hi) >= 0:
        return None
    for _ in range(90):
        m = (lo + hi) / 2.0
        if g(lo) * g(m) < 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2.0


msgrid = np.arange(12.0, 50.01, 0.05)


def metrics(kp, kd, gain):
    fx = f180(kp, kd)
    gm = (1.0 / (KMAG * abs(Cc(fx, kp, kd) * Hlag(fx) * Hfb(fx)))) if fx else float("inf")
    S = lambda f: 1.0 / abs(1.0 + Lc(f, kp, kd))
    sv = [S(f) for f in msgrid]
    ms, fms = max(sv), msgrid[int(np.argmax(sv))]
    return dict(gm=gm, f180=fx, S20=S(20.0), S18=S(18.0), ms=ms, fms=fms,
                Re20=budget(20, kp, kd, gain)[2].real, Re7=budget(7, kp, kd, gain)[2].real,
                ring=0.980 * ring(kp, kd, gain), auth=kp / KP0)


base = metrics(KP0, KD0, GAIN0)
pr("  BASE (V282 as built): GM %.2fx @ %.1f Hz | |S|@20 %.2f | Ms %.2f @ %.1f Hz | Re@20 %+.2f | Re@7 %+.2f | ring %.3f" % (
    base["gm"], base["f180"], base["S20"], base["ms"], base["fms"], base["Re20"], base["Re7"], base["ring"]))
pr("  (Re uses the item-2 CORRECTED, TAU-removed MEASURED lane phases: -85.8 deg at 20 Hz, -63.2 deg at 7 Hz.)")
pr("")
pr("  %-5s %-5s %-6s | %8s %8s %8s %8s %8s %8s %8s %7s  %s" % (
    "Kp", "Kd", "0xC6446", "GM", "f180", "|S|@20", "Ms", "@f", "Re@20", "Re@7", "ring", "verdict"))
adm = []
for kp in (248.0, 200.0, 160.0):
    for kd in (128.0, 112.0, 96.0, 80.0, 64.0):
        for gn in (5244.0, 4096.0, 3072.0, 2048.0):
            m = metrics(kp, kd, gn)
            ok = (m["gm"] >= base["gm"] - 1e-9) and (m["ring"] <= 0.980 + 1e-9)
            why = []
            if m["gm"] < base["gm"]:
                why.append("GM")
            if m["ring"] > 0.980:
                why.append("ring")
            if ok:
                adm.append((kp, kd, gn, m))
            pr("  %-5.0f %-5.0f %-6.0f | %7.2fx %7.1f %8.2f %8.2f %8.1f %+8.2f %+8.2f %7.3f  %s" % (
                kp, kd, gn, m["gm"], m["f180"], m["S20"], m["ms"], m["fms"], m["Re20"], m["Re7"], m["ring"],
                ("* ADMISSIBLE" if ok else "fails " + "+".join(why))))
    pr("")
pr("  ADMISSIBLE SET: %d of 60 points." % len(adm))
if adm:
    best = min(adm, key=lambda r: r[3]["S20"])
    kp, kd, gn, m = best
    pr("")
    pr("  BEST ADMISSIBLE POINT (lowest |S|@20): Kp %.0f, Kd %.0f, 0xC6446 %.0f" % (kp, kd, gn))
    pr("    |S|@20 %.2f (base %.2f, x%.2f)   Ms %.2f @ %.1f Hz (base %.2f @ %.1f)   GM %.2fx (base %.2fx)" % (
        m["S20"], base["S20"], m["S20"] / base["S20"], m["ms"], m["fms"], base["ms"], base["fms"], m["gm"], base["gm"]))
    pr("    Re@20 %+.2f (base %+.2f)   Re@7 %+.2f (base %+.2f)   ring %.3f (base %.3f)" % (
        m["Re20"], base["Re20"], m["Re7"], base["Re7"], m["ring"], base["ring"]))
    pr("    DELIVERED-SURFACE FACTOR (sub-rail torque per unit error, DC): x%.3f  -- the operator's SteerKP" % m["auth"])
    pr("    🛑 THE OUTER LOOP CANNOT GIVE THIS BACK.  SteerKP is 0.800 today (measured on all three routes,")
    pr("    STATE) and its ceiling is 0.900, i.e. only x1.125 of headroom.  Restoring a Kp %.0f cut needs" % kp)
    pr("    x%.3f.  So a Kp cut of this size is a REAL, unrecoverable authority loss, and the operator" % (1.0 / m["auth"]))
    pr("    currently reports 'amazing authority' -- which he would be giving up.")
    lag8 = 1.0 / abs(1.0 + KMAG * abs(Cc(20.0) * Hlag(20.0, 974, 792) * Hfb(20.0)) * cmath.exp(1j * math.radians(
        dg(Cc(20.0)) + dg(Hlag(20.0, 974, 792)) + dg(Hfb(20.0)) + PH_G20)))
    pr("")
    pr("    VS 974/792 (the lag-pole pick): |S|@20 1.21, Ms 6.56 @ 28.7 Hz, GM 1.19x, ring 0.822.")
    pr("    On 18-22 Hz reduction at EQUAL OR BETTER MARGIN, the comparison is: this point spends NO margin")
    pr("    at all by construction, so if its |S|@20 is below 1.61 it strictly dominates 974/792 on the")
    pr("    margin axis.  Read the two |S|@20 numbers above and below to decide.")
else:
    pr("  EMPTY.  Binding gate at each corner:")
    for kp in (248.0, 160.0):
        for kd in (128.0, 64.0):
            for gn in (5244.0, 2048.0):
                m = metrics(kp, kd, gn)
                pr("    Kp %3.0f Kd %3.0f gain %4.0f -> GM %.2fx (need %.2f), ring %.3f (need <= 0.980)" % (
                    kp, kd, gn, m["gm"], base["gm"], m["ring"]))

# ======================================================================================================
pr("")
pr("=" * 150)
pr("ITEM 3 -- THE NONLINEAR LEVERS: the D clamp 0xC61BA = %d and the P clamp 0xC61BC = %d" % (D_CLAMP, P_CLAMP))
pr("=" * 150)
pr("""
  WHY THEY ARE A DIFFERENT CLASS.  A clamp is invisible to the small-signal loop: below it the transfer
  function is unchanged, so there is NO waterbed, NO gain-margin change, NO sensitivity-peak relocation
  and NO blind-band gain rise.  It only limits the kick at a demand transient.  If the grind's D term
  actually reaches the clamp, lowering it is the one lever in this whole study with no small-signal cost.

  THE TEST.  Run the byte-exact 1 kHz chain mirror (`grind_incident_r35.simulate`, the same code the
  r35 incident analysis used) over the loudest measured episodes, and read the D term's own distribution.
  A clamp only does something if |dE * Kd/8| reaches it.
""")
cells = GI.read_cells(IMG)
ROUTES = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r35": "V281r3"}
G = {}
for tag in ROUTES:
    try:
        C20.BUILD[tag] = ROUTES[tag]
    except Exception:
        pass
    G[tag] = C20.load(tag)
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]

WINDOWS = [("r35", 1010.0, 1025.0, "the 23:48:21 GRIND INCIDENT (route t 1016.7)"),
           ("r39", 672.0, 692.0, "bookmark 1 episode"),
           ("r39", 910.0, 930.0, "bookmark 2 episode")]
# plus the loudest creep windows by 18-22 Hz amplitude
CREEP = lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)
cand = []
for tag in ("r39", "r3a", "r3c"):
    g = G[tag]
    m = CREEP(g)
    d = np.diff(np.r_[0, m.astype(int), 0])
    for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if b_ - a_ >= 200:
            cand.append((C20.bamp(g["rate_x"][a_:b_], 18.0, 22.0, FS), tag, g["tr"][a_], g["tr"][b_ - 1]))
cand.sort(reverse=True)
for amp, tag, t0, t1 in cand[:3]:
    WINDOWS.append((tag, t0, t1, "loudest creep window (rate 18-22 amp %.3f)" % amp))

DCLAMPS = [D_CLAMP, 5120, 2560, 1280]
pr("  %-5s %-9s %-42s %8s %10s %10s %10s | %s" % (
    "route", "window s", "what", "s", "p50 |D|", "p99 |D|", "max |D|",
    "".join("%14s" % ("bind %% @%d" % c) for c in DCLAMPS)))
SIMS = {}
for tag, t0, t1, what in WINDOWS:
    g = G[tag]
    a_ = int(np.searchsorted(g["tr"], t0))
    b_ = int(np.searchsorted(g["tr"], t1))
    if b_ - a_ < 100:
        continue
    try:
        s0 = GI.simulate(g, a_, b_, cells)
    except Exception as e:
        pr("  %-5s  simulate failed: %s" % (tag, e))
        continue
    dE = np.r_[0.0, np.diff(s0["E"])]
    Draw = np.abs(dE * 128.0 / 8.0)
    live = np.repeat(g["eng"][s0["seg"]], 10)
    Dl = Draw[live] if live.any() else Draw
    SIMS[(tag, t0)] = (s0, Dl, live, a_, b_, what)
    pr("  %-5s %5.0f-%-5.0f %-42s %8.1f %10.0f %10.0f %10.0f | %s" % (
        tag, t0, t1, what[:42], (b_ - a_) / FS, np.percentile(Dl, 50), np.percentile(Dl, 99), Dl.max(),
        "".join("%14.2f" % (100.0 * np.mean(Dl >= c)) for c in DCLAMPS)))

pr("")
pr("  THE SAME FOR THE P TERM (clamp 0xC61BC = %d):" % P_CLAMP)
pr("  %-5s %-9s %10s %10s %10s | %s" % ("route", "window s", "p50 |P|", "p99 |P|", "max |P|",
                                        "".join("%14s" % ("bind %% @%d" % c) for c in (P_CLAMP, 7680, 3840))))
for (tag, t0), (s0, Dl, live, a_, b_, what) in SIMS.items():
    Pr_ = np.abs(s0["E"] * 248.0 / 256.0)
    Pl = Pr_[live] if live.any() else Pr_
    pr("  %-5s %5.0f-%-5.0f %10.0f %10.0f %10.0f | %s" % (
        tag, t0, t0 + (b_ - a_) / FS, np.percentile(Pl, 50), np.percentile(Pl, 99), Pl.max(),
        "".join("%14.2f" % (100.0 * np.mean(Pl >= c)) for c in (P_CLAMP, 7680, 3840))))

pr("")
pr("  WHAT A LOWER D CLAMP DOES TO THE 18-22 Hz ENVELOPE OF T, on the mirror (open loop on the measured rate):")
pr("  %-5s %-9s | %s" % ("route", "window s", "".join("%16s" % ("T 18-22 @D=%d" % c) for c in DCLAMPS)))
for (tag, t0), (s0, Dl, live, a_, b_, what) in SIMS.items():
    g = G[tag]
    row = []
    for c in DCLAMPS:
        try:
            import v280_map_profiles as _V
            old = _V.D_CLAMP
            _V.D_CLAMP = c
            s = GI.simulate(g, a_, b_, cells)
            _V.D_CLAMP = old
        except Exception:
            _V.D_CLAMP = old
            row.append(float("nan"))
            continue
        row.append(C20.bamp(s["T"], 18.0, 22.0, 1000.0))
    b0 = row[0] if row and row[0] == row[0] else float("nan")
    pr("  %-5s %5.0f-%-5.0f | %s" % (tag, t0, t0 + (b_ - a_) / FS,
                                     "".join("%10.1f (x%.2f)" % (r, r / b0) for r in row)))

pr("")
pr("  AUTHORITY COST OF A D CLAMP, measured on ORDINARY engaged driving (not the bursts):")
pr("  the 0-3 Hz band of T is the command-following content -- if a clamp leaves it alone it costs no")
pr("  tracking authority.  Pooled over the first 8 long engaged runs on r39 that are NOT in any episode.")
pr("  %-5s %-9s %6s | %s" % ("route", "window s", "s", "".join("%26s" % ("D=%d: bind%%  T0-3  max|T|" % c) for c in DCLAMPS)))
eg = G["r39"]
d = np.diff(np.r_[0, eg["eng"].astype(int), 0])
long_runs = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 1500][:8]
for a_, b_ in long_runs:
    cells_row = []
    b0 = None
    for c in DCLAMPS:
        old = V.D_CLAMP
        V.D_CLAMP = c
        try:
            sN = GI.simulate(eg, a_, b_, cells)
        finally:
            V.D_CLAMP = old
        liveN = np.repeat(eg["eng"][sN["seg"]], 10)
        dEn = np.r_[0.0, np.diff(sN["E"])]
        bindpc = 100.0 * np.mean(np.abs(dEn * 128.0 / 8.0)[liveN] >= c) if liveN.any() else float("nan")
        t03 = C20.bamp(sN["T"], 0.2, 3.0, 1000.0)
        if b0 is None:
            b0 = (t03, np.abs(sN["T"]).max())
        cells_row.append("%7.2f %7.1f(x%.2f) %6.0f" % (bindpc, t03, t03 / b0[0], np.abs(sN["T"]).max()))
    pr("  %-5s %5.0f-%-5.0f %6.1f | %s" % ("r39", eg["tr"][a_], eg["tr"][b_ - 1], (b_ - a_) / FS,
                                           "".join("%26s" % c for c in cells_row)))
pr("""
  MAX-RATE AUTHORITY COST OF A D CLAMP.  The D term is the transient kick at a demand step: at a full
  step of the setpoint, dE is largest on the first tick and the D term is what fills the rate.  If the
  measured p99 of |D| in a burst is far below a candidate clamp, that clamp CANNOT be reached in normal
  driving either, so it costs nothing AND does nothing.  Read the bind-percentage columns above: a clamp
  with 0.00 %% binding in the loudest episodes in the corpus is a lever with no effect, and that CLOSES
  the class.  A clamp that binds only in the burst and not in ordinary steps is the interesting case.
""")

with open(os.path.join(SCR, "grind1_dclamp_and_gain_grid.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("[written to _scratch/grind1_dclamp_and_gain_grid.txt]")
