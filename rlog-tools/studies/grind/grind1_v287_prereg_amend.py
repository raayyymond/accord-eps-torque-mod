# -*- coding: utf-8 -*-
"""studies/grind/grind1_v287_prereg_amend.py -- the three PREREG amendments from adversaries A and D.
Subagent `shape`, 2026-09-06.  ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

A1  Q1 CONDITIONING: with Ki 0 the sum is P+D and the 15360 sum clamp binds at |sum| >= 15481 when the
    fade g ~ 1.  On a rising command-step tick where P is railed AND sign(D) = sign(P), the D edit is
    EXACTLY invisible at the output.  What fraction of 2560-binding ticks survive
        (|P| < 15360)  OR  (sign(D) != sign(P))
    and are therefore genuinely observable on T?
A2  BIT-6 duty on onset ticks: T's onset kick shrinks under V287, so P(|r24| >= |T|) RISES mechanically.
    Predicted onset-tick shift, for differential scoring only.

Run: python grind1_v287_prereg_amend.py   (writes _scratch/grind1_v287_prereg_amend.txt)
"""
import os
import sys
import math
import struct

import numpy as np
from scipy import stats as st

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
P_CL, SUM_CL, D_VAL = u16(0xC61BC), u16(0xC61BE), u16(0xC61B6)
FS, FS1K, KD = 100.0, 1000.0, 128.0
DOSE = 2560

cells = GI.read_cells(IMG)
BUILDS = {"r39": "V282", "r35": "V281r3", "r3c": "V282"}
G = {}
for tag in BUILDS:
    try:
        C20.BUILD[tag] = BUILDS[tag]
    except Exception:
        pass
    G[tag] = C20.load(tag)
    G[tag]["tr"] = G[tag]["t"] - G[tag]["t"][0]
    bp = os.path.join(C20.CACHE, tag + "_b4.npz")
    if os.path.exists(bp):
        Bb = np.load(bp)
        k14, P14, tn14, res14 = C20.dejitter(Bb["t14b"], 0.01, 100)
        b4 = Bb["b4"].astype(int)
        G[tag]["bit6"] = np.round(np.interp(G[tag]["t"], tn14, ((b4 >> 6) & 1).astype(float)))

pr("=" * 150)
pr("V287 PREREG AMENDMENTS -- adversaries A and D")
pr("=" * 150)
pr("  cells read from the image: P clamp 0xC61BC = %d, sum clamp 0xC61BE = %d, D clamp 0xC61B6 = %d" % (
    P_CL, SUM_CL, D_VAL))

# ---------------------------------------------------------------- A1
pr("")
pr("A1. Q1 CONDITIONING -- which 2560-binding ticks are actually OBSERVABLE on T")
pr("""
   With Ki = 0 the PID sum is P + D.  The sum clamp is applied to floor(fade*(P+D)/256) against
   +-%d, so with the fade g ~ 1 it binds at |P+D| >= %d.  On a tick where P is ALREADY railed at
   +-%d and sign(D) = sign(P), the sum is clamped with or without the D edit and the delivered torque
   is IDENTICAL: V287 == V282 at the output.  Counting such a tick as a Q1 miss would read as a
   falsified lever when it is only masking.  Q1's binding-tick set must therefore be conditioned on
        (|P| < %d)  OR  (sign(D) != sign(P))
""" % (SUM_CL, int(SUM_CL * 256 / 254.0) + 1, P_CL, P_CL))
CREEP = lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)
WINDOWS = [("r35", 1010.0, 1025.0, "r35 23:48:21 GRIND INCIDENT"),
           ("r39", 672.0, 692.0, "r39 bookmark 1"),
           ("r39", 910.0, 930.0, "r39 bookmark 2")]
for tag in ("r39", "r35"):
    g = G[tag]
    d = np.diff(np.r_[0, g["eng"].astype(int), 0])
    lr = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 1500][:2]
    for a_, b_ in lr:
        WINDOWS.append((tag, g["tr"][a_], g["tr"][b_ - 1], "%s ordinary engaged run" % tag))
cand = []
for tag in ("r39", "r3c"):
    g = G[tag]
    m = CREEP(g)
    d = np.diff(np.r_[0, m.astype(int), 0])
    for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if b_ - a_ >= 200:
            cand.append((C20.bamp(g["rate_x"][a_:b_], 18.0, 22.0, FS), tag, g["tr"][a_], g["tr"][b_ - 1]))
cand.sort(reverse=True)
for amp, tag, t0, t1 in cand[:2]:
    WINDOWS.append((tag, t0, t1, "%s loudest creep" % tag))

pr("   %-34s %9s %12s %12s %14s %14s" % (
    "window", "bind %", "P railed %", "same sign %", "MASKED %", "OBSERVABLE %"))
SIM = {}
surv = []
for tag, t0, t1, what in WINDOWS:
    g = G[tag]
    a_ = int(np.searchsorted(g["tr"], t0))
    b_ = int(np.searchsorted(g["tr"], t1))
    if b_ - a_ < 100:
        continue
    s0 = GI.simulate(g, a_, b_, cells)
    live = np.repeat(g["eng"][s0["seg"]], 10)
    if not live.any():
        live = np.ones(len(s0["E"]), bool)
    dE = np.r_[0.0, np.diff(s0["E"])]
    Draw = np.floor(dE * KD / 8.0)
    Pc = s0["P"]
    bind = (np.abs(Draw) >= DOSE) & live
    SIM[(tag, round(t0, 1))] = dict(s=s0, live=live, what=what, g=g, a=a_, b=b_, bind=bind, P=Pc, D=Draw)
    if bind.sum() == 0:
        pr("   %-34s %9.2f %12s %12s %14s %14s" % (what[:34], 0.0, "-", "-", "-", "-"))
        continue
    prail = np.abs(Pc)[bind] >= P_CL
    same = np.sign(Draw)[bind] == np.sign(Pc)[bind]
    masked = prail & same
    obs = ~masked
    surv.append(obs.mean())
    pr("   %-34s %9.2f %12.1f %12.1f %14.1f %14.1f" % (
        what[:34], 100.0 * bind.sum() / live.sum(), 100.0 * prail.mean(), 100.0 * same.mean(),
        100.0 * masked.mean(), 100.0 * obs.mean()))
if surv:
    pr("")
    pr("   ⇒ EXPECTED FRACTION OF 2560-BINDING TICKS THAT SURVIVE THE CONDITION: %.1f %% - %.1f %% (median %.1f %%)." % (
        100 * min(surv), 100 * max(surv), 100 * float(np.median(surv))))

# ---------------------------------------------------------------- A2
pr("")
pr("A2. BIT-6 DUTY ON ONSET TICKS -- it RISES mechanically, so score it DIFFERENTIALLY")
pr("""
   bit 6 = (|r24| >= |T|).  r24 is untouched by a D-clamp edit; T's ONSET kick shrinks by the B3 factor.
   So the duty on onset ticks must RISE, purely because the comparator's right-hand side got smaller.
   That is NOT evidence about r24 and V282's absolute 0.22 / 0.10 thresholds DO NOT TRANSFER.
   Predicted with the lognormal quantile calibrated in section 6c (sd(ln |r24|/|T|) = 1.68, fitted to
   r39's own gain-ladder replay): duty_new = 1 - Phi( Phi^-1(1 - duty) + ln(k) / sd ), k = T ratio.
""")
SD = 1.68


def duty_shift(duty, k):
    if not (0 < duty < 1):
        return float("nan")
    z0 = st.norm.ppf(1 - duty)
    return 1 - st.norm.cdf(z0 + math.log(k) / SD)


pr("   %-34s %10s %12s %12s %12s" % ("window", "k (T ratio)", "duty today", "duty pred", "x"))
for k_, d in SIM.items():
    g, a_, b_ = d["g"], d["a"], d["b"]
    if "bit6" not in g:
        continue
    s0 = d["s"]
    dsp = np.abs(np.r_[0.0, np.diff(32.0 * s0["sp"])])
    nz = dsp[dsp > 0]
    if len(nz) == 0:
        continue
    thr = np.percentile(nz, 99)
    onset1k = np.zeros(len(dsp), bool)
    for i in np.flatnonzero(dsp >= thr):
        onset1k[i:i + 500] = True
    old = V.D_CLAMP
    V.D_CLAMP = DOSE
    try:
        sN = GI.simulate(g, a_, b_, cells)
    finally:
        V.D_CLAMP = old
    T0 = np.abs(s0["T"])[onset1k]
    T1 = np.abs(sN["T"])[onset1k]
    if T0.sum() <= 0:
        continue
    kk = float(np.mean(T1) / np.mean(T0))
    # bit-6 duty on the same onset frames, 100 Hz
    fr = np.arange(s0["seg"].start, s0["seg"].stop)
    on100 = onset1k[::10][:len(fr)]
    idx = fr[:len(on100)][on100]
    idx = idx[(idx >= 0) & (idx < len(g["bit6"]))]
    if len(idx) < 50:
        continue
    duty = float(g["bit6"][idx].mean())
    pr("   %-34s %10.3f %12.4f %12.4f %12.3f" % (
        d["what"][:34], kk, duty, duty_shift(duty, kk), duty_shift(duty, kk) / duty if duty else float("nan")))
pr("   (k < 1 means T fell, so the duty RISES.  Report bit 6 as ONSET-minus-STEADY on the same drive;")
pr("    a rise on onset ticks with steady unchanged is the EXPECTED signature of the edit working, not")
pr("    a statement about r24.)")

with open(os.path.join(SCR, "grind1_v287_prereg_amend.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("")
pr("[written to _scratch/grind1_v287_prereg_amend.txt]")
