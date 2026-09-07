# -*- coding: utf-8 -*-
"""studies/grind/grind1_dclamp_decompose.py -- is the D clamp an EXCITATION limiter or a Kd cut?
Subagent `shape`, 2026-09-06.  ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

The describing-function objection to lowering 0xC61BA only applies if the clamp binds on the RIPPLE's own
D.  E = 32*sp - fb, so  dE = 32*d(sp) - d(fb)  and the D term splits EXACTLY into

    D_sp = floor( 32*d(sp) * Kd / 8 )      the SETPOINT / feedforward kick
    D_fb = floor( -d(fb)  * Kd / 8 )       the FEEDBACK, small-signal loop term

If the binding ticks are D_sp ticks, the clamp leaves |S|, Ms, GM and the ring EXACTLY as-built and only
limits the excitation that rings the mode.  If they are D_fb ticks, it is a local Kd cut and A4's grid
applies.  This file decides that, with no plant.

Run: python grind1_dclamp_decompose.py    (writes _scratch/grind1_dclamp_decompose.txt)
"""
import os
import sys
import math
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
D_CLAMP = u16(0xC61B6)   # FIXED 2026-09-06: was 0xC61BA (the integrator anti-windup); both hold 10240
FS, FS1K = 100.0, 1000.0
KD = 128.0
DOSES = [D_CLAMP, 5120, 2560, 1280]

cells = GI.read_cells(IMG)
BUILDS = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r35": "V281r3"}
G = {}
for tag in BUILDS:
    try:
        C20.BUILD[tag] = BUILDS[tag]
    except Exception:
        pass
    G[tag] = C20.load(tag)
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]

CREEP = lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)
WINDOWS = [("r35", 1010.0, 1025.0, "r35 23:48:21 GRIND INCIDENT"),
           ("r39", 672.0, 692.0, "r39 bookmark 1 episode"),
           ("r39", 910.0, 930.0, "r39 bookmark 2 episode")]
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
    WINDOWS.append((tag, t0, t1, "loudest creep window (rate 18-22 %.2f)" % amp))

pr("=" * 150)
pr("APPENDIX B -- IS THE D CLAMP AN EXCITATION LIMITER OR A LOCAL Kd CUT?")
pr("=" * 150)
pr("  E = 32*sp - fb  =>  dE = 32*d(sp) - d(fb).  Exact split, no approximation:")
pr("      D_sp = floor(32*d(sp)*Kd/8)   the setpoint / feedforward kick")
pr("      D_fb = floor(-d(fb)*Kd/8)     the feedback, small-signal loop term")
pr("  0xC61BA = %d today.  Ladder: %s" % (D_CLAMP, " / ".join(str(d) for d in DOSES[1:])))
pr("")

SIM = {}
for tag, t0, t1, what in WINDOWS:
    g = G[tag]
    a_ = int(np.searchsorted(g["tr"], t0))
    b_ = int(np.searchsorted(g["tr"], t1))
    if b_ - a_ < 100:
        continue
    s0 = GI.simulate(g, a_, b_, cells)
    live = np.repeat(g["eng"][s0["seg"]], 10)
    sp32 = 32.0 * s0["sp"]
    dsp = np.r_[0.0, np.diff(sp32)]
    dfb = np.r_[0.0, np.diff(s0["fb"])]
    Dsp = np.floor(dsp * KD / 8.0)
    Dfb = np.floor(-dfb * KD / 8.0)
    Dtot = np.floor((dsp - dfb) * KD / 8.0)
    SIM[(tag, t0)] = dict(s=s0, live=live, Dsp=Dsp, Dfb=Dfb, Dtot=Dtot, what=what, a=a_, b=b_, g=g)

pr("  1. THE DECOMPOSITION.  Which part carries the magnitude, and which part carries the 18-22 Hz ripple?")
pr("  %-34s %7s | %9s %9s %9s | %9s %9s %9s | %10s %10s" % (
    "window", "s", "p50|Dsp|", "p99|Dsp|", "max|Dsp|", "p50|Dfb|", "p99|Dfb|", "max|Dfb|",
    "Dsp 18-22", "Dfb 18-22"))
for k, d in SIM.items():
    lv = d["live"]
    if not lv.any():
        lv = np.ones(len(d["Dsp"]), bool)
    a_sp, a_fb = np.abs(d["Dsp"])[lv], np.abs(d["Dfb"])[lv]
    pr("  %-34s %7.1f | %9.0f %9.0f %9.0f | %9.0f %9.0f %9.0f | %10.0f %10.0f" % (
        d["what"][:34], lv.sum() / FS1K,
        np.percentile(a_sp, 50), np.percentile(a_sp, 99), a_sp.max(),
        np.percentile(a_fb, 50), np.percentile(a_fb, 99), a_fb.max(),
        C20.bamp(d["Dsp"], 18.0, 22.0, FS1K), C20.bamp(d["Dfb"], 18.0, 22.0, FS1K)))

pr("")
pr("  2. WHICH TICKS ACTUALLY BIND, AND WHY.  A tick binds when |D_total| >= clamp.  For each clamp value")
pr("     the binding ticks are classified by which part dominates them (|Dsp| vs |Dfb| at that tick),")
pr("     and by whether the command's own 100 Hz staircase stepped on that tick (d(sp) != 0).")
for c in DOSES:
    pr("     clamp = %5d" % c)
    pr("     %-34s %9s %10s %10s %10s %10s" % (
        "window", "bind %", "Dsp-dom %", "Dfb-dom %", "on a sp step %", "p99|Dfb| / clamp"))
    for k, d in SIM.items():
        lv = d["live"]
        if not lv.any():
            lv = np.ones(len(d["Dsp"]), bool)
        bind = (np.abs(d["Dtot"]) >= c) & lv
        if bind.sum() == 0:
            pr("     %-34s %9.2f %10s %10s %10s %10.3f" % (
                d["what"][:34], 0.0, "-", "-", "-",
                np.percentile(np.abs(d["Dfb"])[lv], 99) / c))
            continue
        spd = np.abs(d["Dsp"])[bind] >= np.abs(d["Dfb"])[bind]
        stepped = np.abs(np.r_[0.0, np.diff(32.0 * d["s"]["sp"])])[bind] > 0
        pr("     %-34s %9.2f %10.1f %10.1f %10.1f %10.3f" % (
            d["what"][:34], 100.0 * bind.sum() / lv.sum(), 100.0 * spd.mean(),
            100.0 * (~spd).mean(), 100.0 * stepped.mean(),
            np.percentile(np.abs(d["Dfb"])[lv], 99) / c))
    pr("")

pr("  3. THE DISCRIMINATING NUMBER: the FEEDBACK part's own 18-22 Hz amplitude and its p99, against each clamp.")
pr("     If p99|D_fb| stays well under the clamp, the small-signal loop NEVER sees the nonlinearity and")
pr("     |S|@20, Ms, GM and the 7.3 Hz ring are EXACTLY as-built -- the two frames do not disagree at all.")
pr("  %-34s %12s %12s | %s" % ("window", "Dfb 18-22", "p99|Dfb|", "".join("%16s" % ("p99/%d" % c) for c in DOSES)))
allsafe = {c: True for c in DOSES}
for k, d in SIM.items():
    lv = d["live"]
    if not lv.any():
        lv = np.ones(len(d["Dsp"]), bool)
    p99 = np.percentile(np.abs(d["Dfb"])[lv], 99)
    for c in DOSES:
        if p99 >= c:
            allsafe[c] = False
    pr("  %-34s %12.0f %12.0f | %s" % (
        d["what"][:34], C20.bamp(d["Dfb"], 18.0, 22.0, FS1K), p99,
        "".join("%16.3f" % (p99 / c) for c in DOSES)))
pr("")
for c in DOSES:
    pr("     clamp %5d : p99|D_fb| below it in EVERY window?  %s" % (c, "YES" if allsafe[c] else "NO"))

pr("")
pr("  4. (a) THE DISCRIMINATING PREDICTION -- onsets versus steady creep.")
pr("     If the clamp is an EXCITATION limiter it must move the envelope at TRANSIENT ONSETS and leave")
pr("     STEADY creep alone.  Onset = the first 0.5 s after a tick where |d(sp)| is in its top 1 %;")
pr("     steady = ticks with no sp step in the preceding 0.3 s.")
pr("  %-34s | %s" % ("window", "".join("%26s" % ("D=%d  onset / steady" % c) for c in DOSES)))
for k, d in SIM.items():
    g, a_, b_ = d["g"], d["a"], d["b"]
    row = []
    base = None
    for c in DOSES:
        old = V.D_CLAMP
        V.D_CLAMP = c
        try:
            sN = GI.simulate(g, a_, b_, cells)
        finally:
            V.D_CLAMP = old
        dsp = np.abs(np.r_[0.0, np.diff(32.0 * sN["sp"])])
        # the command is a 100 Hz staircase, so d(sp) != 0 on 1 tick in 10 ALWAYS.  "Onset" therefore
        # means a LARGE step, not any step.  Big = top 1 % of the non-zero step sizes.
        nz = dsp[dsp > 0]
        thr = np.percentile(nz, 99) if len(nz) else np.inf
        small = np.percentile(nz, 50) if len(nz) else 0.0
        onset = np.zeros(len(dsp), bool)
        for i in np.flatnonzero(dsp >= thr):
            onset[i:i + 500] = True
        big = np.convolve((dsp > small).astype(float), np.ones(300), mode="same") > 0
        steady = (~onset) & (~big)
        if steady.sum() < 500:
            steady = ~onset
        eo = C20.bamp(sN["T"][onset], 18.0, 22.0, FS1K) if onset.sum() > 500 else float("nan")
        es = C20.bamp(sN["T"][steady], 18.0, 22.0, FS1K) if steady.sum() > 500 else float("nan")
        if base is None:
            base = (eo if eo == eo and eo > 0 else 1.0, es if es == es and es > 0 else 1.0)
        row.append("%9.1f(x%.2f)%8.1f(x%.2f)" % (eo, eo / base[0], es, es / base[1]))
    pr("  %-34s | %s" % (d["what"][:34], "".join("%26s" % r for r in row)))

pr("""
  5. (b) THE MAX-RATE COST, on MEASURED hands-light full-demand steps.  I do not synthesise a step: the
     forward path multiplies by |q32(H_fb*rate)|, which is zero at zero rate, so a synthetic step from
     rest is not a valid model of this chain.  Instead I take the real steps out of the logs -- engaged,
     hands-light (|bar| < 300 raw), where the demand index jumps into its top decile -- and read the
     delivered torque and the achieved wheel rate over the first 200 ms at each clamp.
""")
steps = []
for tag in ("r39", "r3c"):
    g = G[tag]
    idx, sgn = V.demand(np.round(g["cmd"]), g["bar"])
    didx = np.r_[0.0, np.diff(idx)]
    hot = g["eng"] & (np.abs(g["bar"]) < 300) & (didx >= max(8.0, np.percentile(didx[didx > 0], 97) if (didx > 0).any() else 8.0))
    for i in np.flatnonzero(hot):
        if i > 60 and i < len(g["t"]) - 60 and g["eng"][i - 30:i + 40].all():
            steps.append((tag, i))
    if len(steps) >= 40:
        break
pr("     found %d qualifying hands-light demand steps" % len(steps))
if steps:
    pr("     %-6s | %s" % ("clamp", "%14s %14s %14s %14s" % ("|T| p50 0-50ms", "0-100ms", "0-200ms", "peak rate 200ms")))
    for c in DOSES:
        Ts50, Ts100, Ts200, pk = [], [], [], []
        old = V.D_CLAMP
        V.D_CLAMP = c
        try:
            for tag, i in steps[:24]:
                g = G[tag]
                a_, b_ = i - 30, i + 40
                sN = GI.simulate(g, a_, b_, cells)
                j = int((i - sN["seg"].start) * 10)
                Tt = np.abs(sN["T"])
                Ts50.append(np.median(Tt[j:j + 50]))
                Ts100.append(np.median(Tt[j:j + 100]))
                Ts200.append(np.median(Tt[j:j + 200]))
                pk.append(np.max(np.abs(g["rate_x"][i:i + 20])))
        finally:
            V.D_CLAMP = old
        pr("     %-6d | %14.1f %14.1f %14.1f %14.1f" % (
            c, np.median(Ts50), np.median(Ts100), np.median(Ts200), np.median(pk)))
    pr("     (the peak-rate column is the MEASURED wheel rate on those same steps and is identical by")
    pr("      construction -- it is printed only to show the steps really are full-demand ones.)")

with open(os.path.join(SCR, "grind1_dclamp_decompose.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("")
pr("[written to _scratch/grind1_dclamp_decompose.txt]")
