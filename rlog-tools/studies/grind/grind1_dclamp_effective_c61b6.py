# -*- coding: utf-8 -*-
"""studies/grind/grind1_dclamp_effective_c61b6.py -- Appendix B corrections, 2026-09-06.  Subagent `shape`.
ANALYSIS ONLY.  Builds nothing, sends nothing, flashes nothing.

1. THE CELL IS 0xC61B6, not 0xC61BA.  Re-verified from the decompile of FUN_00028ea6 here.
2. THE CLAMP ORDER in the mirror is checked against the bytes.
3. THE EFFECTIVE BIND FRACTION: on ticks where the SUM clamp 0xC61BE also binds, a D dose is INERT.
4. THE POST-LAG DEADBAND 0xC61B8 = 102: does it touch the small-signal 20 Hz ripple?

Run: python grind1_dclamp_effective_c61b6.py   (writes _scratch/grind1_dclamp_effective_c61b6.txt)
"""
import os
import sys
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
BS = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
D_CELL, D_VAL = 0xC61B6, u16(B, 0xC61B6)
DB = u16(B, 0xC61B8)
SUM_CL = u16(B, 0xC61BE)
P_CL = u16(B, 0xC61BC)
LAG_A, LAG_B = u16(B, 0xC63EC), u16(B, 0xC63EE)
FS, FS1K, KD = 100.0, 1000.0, 128.0
DOSES = [D_VAL, 5120, 2560, 1280]

pr("=" * 150)
pr("APPENDIX B CORRECTIONS -- the D clamp is 0xC61B6, the effective bind fraction, and the 102 deadband")
pr("=" * 150)
pr("""
  1. THE CELL.  `team-lead`'s tracer census is CORRECT and my Appendix B named the wrong address.
     Re-verified by me on the decompile of FUN_00028ea6 (GhidraMCP, stock program, byte-identical to
     V282 over this extent except the x6 repoint):

        line 1036-1051   clamp against  tp+0x71bc  = 0xC61BC = %5d   -> the P CLAMP
        line 1079-1091   clamp against  tp+0x71b6  = 0xC61B6 = %5d   -> the D CLAMP        <-- THE CELL
        line  992        tp+0x71ba as ((u16) << 10) >> 3   = 0xC61BA = %5d -> the INTEGRATOR anti-windup
        line 1191-1204   clamp against  tp+0x71be  = 0xC61BE = %5d   -> the PID-SUM clamp

     0xC61B6 and 0xC61BA BOTH HOLD 10240, so a spot check cannot tell them apart -- exactly the trap the
     record already recorded for the P-clamp pair (0xC61BC vs 0xC61BE, both 15360).  Nothing numeric in
     Appendix B changes: the mirror clamps at the VALUE 10240 via `v280_map_profiles.D_CLAMP`, which is
     the D clamp's value.  **Only the address was wrong, and it is corrected to 0xC61B6 everywhere.**
     At Ki = 0 the 0xC61BA anti-windup ceiling is inert, so it is not a lever either way.

  2. THE CLAMP ORDER, checked against the bytes [EVIDENCE, decompile line numbers above]:
        P = clip(E*Kp>>8, +-0xC61BC)                                  (line 1036)
        D = clip(dE*Kd>>3, +-0xC61B6)                                 (line 1079)   rails at |dE| = %d
        S = clip( fade * (P + D) >> 8 , +-0xC61BE )                   (line 1183 fade, 1191 clamp)
        lag_out = ((D_lag_prev + D_lag_new) >> 5)                     (0x2A1AC)
        deadband: if |sxh(lag_out)| <= 0xC61B8 AND lag_out*prev <= 0 -> 0   (0x2A1BE-E4)
        v = sxh((lag_out * G_fb) >> 15) ; T = clip(-K6*v>>15, +-0xC61B4)
     The mirror (`grind_incident_r35.simulate`) applies P clamp, D clamp, fade, sum clamp, lag, gain,
     out cap IN THAT ORDER.  **It matches the bytes.**  ⚠ It does NOT implement the 0xC61B8 deadband --
     section 4 below is where that is priced.
""" % (P_CL, D_VAL, u16(B, 0xC61BA), SUM_CL, D_VAL * 8 // int(KD)))
pr("     D rails at |dE| = %d today; %d at 5120, %d at 2560, %d at 1280." % tuple(
    int(c * 8 / KD) for c in DOSES))

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
           ("r39", 672.0, 692.0, "r39 bookmark 1"),
           ("r39", 910.0, 930.0, "r39 bookmark 2")]
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
    WINDOWS.append((tag, t0, t1, "loudest creep (rate 18-22 %.2f)" % amp))
# and a long ordinary engaged run for the authority side
eg = G["r39"]
d = np.diff(np.r_[0, eg["eng"].astype(int), 0])
lr = [(a_, b_) for a_, b_ in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b_ - a_ >= 1500][:2]
for a_, b_ in lr:
    WINDOWS.append(("r39", eg["tr"][a_], eg["tr"][b_ - 1], "ordinary engaged run"))

SIM = {}
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
    SIM[(tag, round(t0, 1))] = dict(s=s0, live=live, what=what, g=g, a=a_, b=b_)

pr("")
pr("=" * 150)
pr("3. THE EFFECTIVE BIND FRACTION -- where the SUM clamp also binds, a D dose is INERT")
pr("=" * 150)
pr("   A tick counts only if D binds AND the sum clamp does NOT.  S_raw = fade*(P+D)>>8; on ticks where")
pr("   |S_raw| >= %d the output is railed and the D value is discarded, so lowering the D clamp there" % SUM_CL)
pr("   changes nothing.  Reported per candidate clamp: raw bind %, the share of those ticks on which the")
pr("   sum ALSO rails (wasted), and the EFFECTIVE bind % -- which is the number I now quote.")
pr("")
for c in DOSES:
    pr("   D clamp = %5d" % c)
    pr("   %-32s %10s %14s %14s %14s" % ("window", "raw bind %", "sum also rails %", "EFFECTIVE %", "P alone rails %"))
    for k, d in SIM.items():
        s0, live = d["s"], d["live"]
        dE = np.r_[0.0, np.diff(s0["E"])]
        Draw = np.floor(dE * KD / 8.0)
        Dc = np.clip(Draw, -c, c)
        Pc = s0["P"]
        Sraw = np.floor(s0["m"] * (Pc + Dc) / 256.0)
        Sraw_P = np.floor(s0["m"] * Pc / 256.0)
        bind = (np.abs(Draw) >= c) & live
        if bind.sum() == 0:
            pr("   %-32s %10.2f %14s %14.2f %14.2f" % (
                d["what"][:32], 0.0, "-", 0.0, 100.0 * np.mean(np.abs(Sraw_P)[live] >= SUM_CL)))
            continue
        wasted = np.abs(Sraw)[bind] >= SUM_CL
        pr("   %-32s %10.2f %14.1f %14.2f %14.2f" % (
            d["what"][:32], 100.0 * bind.sum() / live.sum(), 100.0 * wasted.mean(),
            100.0 * (bind & (np.abs(Sraw) < SUM_CL)).sum() / live.sum(),
            100.0 * np.mean(np.abs(Sraw_P)[live] >= SUM_CL)))
    pr("")
pr("   ⚠ The T envelopes in Appendix B sec3 ALREADY account for this: the mirror applies the sum clamp")
pr("   after the D clamp in byte order, so the wasted ticks are already inside those numbers.  The table")
pr("   above is diagnostic -- it says how much of each dose is spent on ticks that were railed anyway.")

pr("")
pr("=" * 150)
pr("4. THE POST-LAG DEADBAND 0xC61B8 = %d -- does it touch the small-signal 20 Hz ripple?" % DB)
pr("=" * 150)
pr("""
   The rung (0x2A1BE-0x2A1E4) zeroes the output when |sxh(lag_out)| <= %d AND lag_out * previous_output
   <= 0.  The second condition is a SIGN CHANGE, so this fires on small, sign-alternating outputs --
   which is exactly the shape of a small ripple about zero.  If the 20 Hz ripple's lag output stayed
   under %d counts the deadband would chop it, and the mirror (which does not implement the rung) would
   be over-estimating T.  Measured on the mirror's own lag output:
""" % (DB, DB))
pr("   %-32s %10s %10s %10s %12s %12s %12s" % (
    "window", "p50|lag|", "p90|lag|", "max|lag|", "lag 18-22", "P(|lag|<=102)", "deadband fires %"))
for k, d in SIM.items():
    s0, live = d["s"], d["live"]
    Sr = np.clip(np.floor(s0["m"] * (s0["P"] + s0["D"]) / 256.0), -SUM_CL, SUM_CL)
    Sr = np.where(live, Sr, 0.0)
    st = signal.lfilter([LAG_B / 1024.0], [1.0, -LAG_A / 1024.0], Sr)
    lag = (np.r_[0.0, st[:-1]] + st) / 32.0
    prev = np.r_[0.0, lag[:-1]]
    fires = (np.abs(lag) <= DB) & (lag * prev <= 0)
    lv = live
    pr("   %-32s %10.0f %10.0f %10.0f %12.0f %12.4f %12.4f" % (
        d["what"][:32], np.percentile(np.abs(lag)[lv], 50), np.percentile(np.abs(lag)[lv], 90),
        np.abs(lag)[lv].max(), C20.bamp(lag, 18.0, 22.0, FS1K),
        np.mean(np.abs(lag)[lv] <= DB), np.mean(fires[lv])))
pr("")
pr("   READ IT AS: the deadband can only matter where |lag_out| is comparable to %d.  Compare the" % DB)
pr("   'lag 18-22' column (the ripple's own amplitude in lag-output counts) with %d, and the" % DB)
pr("   'deadband fires' column with the D-clamp bind fractions above.")

with open(os.path.join(SCR, "grind1_dclamp_effective_c61b6.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(OUT) + "\n")
pr("")
pr("[written to _scratch/grind1_dclamp_effective_c61b6.txt]")
