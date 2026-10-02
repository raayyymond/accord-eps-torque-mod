# -*- coding: utf-8 -*-
r"""gate2_fork.py -- D2 (FORK-FIRST) GATE 2 on the panel-2 COMMON frequency scorer's own loop model (imported unchanged).

ANALYSIS ONLY.  Writes _scratch/v299_D2/gate2_fork.{txt,json}.

1. INNER LOOP (the EPS lane, V298 bytes = C3B-P: GB-P read from the IMAGE, Kp 112, Ki 40, fresh D Kd 48): PM / GM /
   max|S| at theta = 0, every speed knot, members nominal + the brief's tier-A singles and two combined.  D2 changes NO
   firmware byte, so these are V298's own numbers (a reproduction, not a new gate).
2. THE FORK LOOPS D2 TOUCHES (each closes around the inner closed loop Tin = theta / theta_sp):
   O1 (override): theta_sp = theta(t - Trt) + L * omega(t - Trt), sampled at 100 Hz (ZOH), I frozen (|word| > 512) ->
      the PD inner loop, fade 1.0 (a twist or light hand) and 0.297 (a firm hand).  The loop is POSITIVE feedback with
      DC gain 1 (the deliberate neutral pole: the setpoint follows the wheel), so the gate is the peak over f >= 0.05 Hz
      of |Tin e^{-s Trt} (1 + s L)| (< 1 = no growing mode beyond the neutral one) and the peak sensitivity
      |1 / (1 - Tin e^{-s Trt}(1 + s L))| there.  L = 0.06 (V298), 0.03, 0 (D2).
   ERROR CLIP while binding: the same loop with L = 0 and the PID inner loop (I not frozen).
   LEAD (SteerDelay / the (b) lead): FEED-FORWARD on the plan, no measured quantity enters it -> no new loop.  Its only
      loop is the vision / path loop; it is checked here on the scorer's own outer-loop model (E2-K0's fork angle
      integral, tau_o = 1 s, 60 ms) with the lead as a prediction e^{+s Delta} on the setpoint, Delta 0 / 0.1 / 0.2 s
      (BELIEF model of the planner).
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
import time
from dataclasses import replace

import numpy as np

import d2_common as C

T0 = time.perf_counter()
name = "p2_sf_d2"
for p in (C.AL / "panel", C.AL / "c1", C.AL / "c3" / "rev2B"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
spec = importlib.util.spec_from_file_location(name, C.AL / "panel2" / "score_freq.py")
SF = importlib.util.module_from_spec(spec)
sys.modules[name] = SF
spec.loader.exec_module(SF)
DM, CL = SF.DM, SF.C
F = SF.F
ROWS = [tuple(r) for r in C.ROWS]
V298 = SF.Spec("V298", "D2", ROWS, 48, ki=40.0, dkind="fresh", src="V298 image 0xC4C00+218", note="flown")
SPEEDS = (3.1, 5.0, 8.0, 10.0, 11.75, 14.0, 17.5, 22.0, 26.9)
MEMBERS = ("nominal", "J_hi", "b_lo", "tau6", "mode20", "b_lo*J_hi", "b_q")
zo = np.exp(-2j * np.pi * F * 0.01)
ZOH = (1 - zo) / (2j * np.pi * F * 0.01 + 1e-30)            # 100 Hz zero-order hold of the fork's setpoint
L_ = []
R = {}


def pr(s=""):
    L_.append(s)
    print(s, flush=True)


def inner(member, v, ki=None, fade=1.0):
    pl, d, ea, jbk = SF.member_plant(member, v)
    Pt, Pw = DM.plant_frf(pl, F)
    G = float(CL.cave_G(CL.spd_counts(v), ROWS))
    cs = SF.ctl_split(F, V298, G, ea, ki=ki)
    (tth, tw, tref), (mth, mw, mref) = cs["t"], cs["m"]
    K = SF.K_out(F, d)
    Lp = -fade * K * ((tth + mth) * Pt + (tw + mw) * Pw)
    S = 1.0 / (1.0 + Lp)
    Tin = fade * K * (tref + mref) * Pt * S
    return Lp, S, Tin, G


pr("1. INNER LOOP (V298 bytes, unchanged by D2): PM deg / GM up dB / max|S| at theta = 0")
pr("   v    | " + " | ".join("%-17s" % m for m in MEMBERS))
inn = {}
for v in SPEEDS:
    cells = []
    for m in MEMBERS:
        Lp, S, Tin, G = inner(m, v)
        PM, FC, PMR, gmu, gmd = SF.pm_gm(Lp)
        ms = float(np.abs(S).max())
        inn[(m, v)] = (PM, gmu, ms)
        cells.append("%5.1f %5.1f %4.2f" % (PM, gmu, ms))
    pr("   %5.2f | " % v + " | ".join("%-17s" % c for c in cells))
R["inner"] = {f"{m}@{v}": inn[(m, v)] for (m, v) in inn}
pmin = min(x[0] for x in inn.values())
pr("   min PM over the set %.1f deg; min GM %.1f dB; max |S| %.2f" % (pmin, min(x[1] for x in inn.values()),
                                                                   max(x[2] for x in inn.values())))

pr("\n2a. O1 LOOP (positive, DC gain 1): peak |Tin e^{-sTrt}(1+sL) ZOH| over 0.05-30 Hz, and peak |S_o| (I frozen = PD)")
band = (F >= 0.05) & (F <= 30.0)
o1 = {}
pr("   fade | Trt s | L s | worst over speeds x members: peak |loop| (at Hz)  peak |S_o| at >= 0.3 Hz | count(|loop| > 1)")
for fade in (1.0, 0.297):
    for Trt in (0.03, 0.06):
        for Ld in (0.06, 0.03, 0.0):
            worst = (0, 0, 0, None)
            nbad = 0
            for v in SPEEDS:
                for m in MEMBERS:
                    _, _, Tin, _ = inner(m, v, ki=0.0, fade=fade)
                    lo = Tin * np.exp(-2j * np.pi * F * Trt) * (1 + 2j * np.pi * F * Ld) * ZOH
                    mag = np.abs(lo[band])
                    So = np.abs(1.0 / (1.0 - lo[band]))
                    So = np.where(F[band] >= 0.3, So, 0.0)          # the oscillatory band (>= 0.3 Hz); below = the neutral drift
                    k = int(np.argmax(mag))
                    if mag[k] > 1.0:
                        nbad += 1
                    if mag[k] > worst[0]:
                        worst = (float(mag[k]), float(F[band][k]), float(So.max()), (m, v))
            o1[f"f{fade}_T{Trt}_L{Ld}"] = dict(peak=worst[0], at_hz=worst[1], So=worst[2], where=worst[3], n_gt1=nbad)
            pr("   %5.3f | %4.2f | %4.2f | %5.3f @ %5.2f Hz  |S_o| %6.2f  (%s @ %s) | %d of %d"
               % (fade, Trt, Ld, worst[0], worst[1], worst[2], worst[3][0], worst[3][1], nbad,
                  len(SPEEDS) * len(MEMBERS)))
R["o1"] = o1

pr("\n2b. ERROR-CLIP LOOP while binding (L = 0, the PID inner loop, fade 1): same metric")
clip = {}
for Trt in (0.03, 0.06):
    worst = (0, 0, 0, None)
    nbad = 0
    for v in SPEEDS:
        for m in MEMBERS:
            _, _, Tin, _ = inner(m, v)
            lo = Tin * np.exp(-2j * np.pi * F * Trt) * ZOH
            mag = np.abs(lo[band])
            k = int(np.argmax(mag))
            nbad += int(mag[k] > 1.0)
            if mag[k] > worst[0]:
                worst = (float(mag[k]), float(F[band][k]), float(np.abs(1.0 / (1.0 - lo[band])).max()), (m, v))
    clip[f"T{Trt}"] = dict(peak=worst[0], at_hz=worst[1], So=worst[2], where=worst[3], n_gt1=nbad)
    pr("   Trt %.2f: peak %5.3f @ %5.2f Hz, |S_o| %.2f (%s @ %s), %d > 1" % (Trt, *worst[:3], *worst[3], nbad))
R["clip"] = clip

pr("\n2d. POSITIVE-FEEDBACK MARGINS (Nyquist about +1 = SF.pm_gm on -L_o): min PM / min GM over speeds x members, and the"
   " least-margin point.  O1 = PD inner loop; CLIP = PID inner loop.  PM < 0 or GM < 0 = a growing mode.")
pfm = {}
for nm, ki, fades, Ls in (("O1", 0.0, (1.0, 0.297), (0.06, 0.03, 0.0)), ("CLIP", None, (1.0,), (0.0,))):
    for fade in fades:
        for Ld in Ls:
            for Trt in (0.03, 0.06):
                worst = (float("inf"), float("inf"), ("none", 0.0, float("nan")))
                gmin = float("inf")
                for v in SPEEDS:
                    for m in MEMBERS:
                        _, _, Tin, _ = inner(m, v, ki=ki, fade=fade)
                        lo = Tin * np.exp(-2j * np.pi * F * Trt) * (1 + 2j * np.pi * F * Ld) * ZOH
                        PM, FC, PMR, gmu, gmd = SF.pm_gm(-lo)
                        gmin = min(gmin, gmu)
                        if PM < worst[0]:
                            worst = (PM, gmu, (m, v, FC))
                worst = (worst[0], gmin, worst[2])
                pfm[f"{nm}_f{fade}_L{Ld}_T{Trt}"] = worst
                pr("   %-4s fade %.3f L %.2f Trt %.2f: min PM %6.1f deg (at %s @ %.2f m/s, crossing %.2f Hz)  GM %.1f dB"
                   % (nm, fade, Ld, Trt, worst[0], worst[2][0], worst[2][1], worst[2][2], worst[1]))
R["posfb"] = {k: [v[0], v[1], list(map(str, v[2]))] for k, v in pfm.items()}

pr("\n2c. LEAD as a planner prediction inside the path loop (E2-K0 outer model, tau_o 1 s, 60 ms): PM / GM, nominal")
lead = {}
for Dl in (0.0, 0.1, 0.2, 0.3):
    rowc = []
    for v in SPEEDS:
        _, _, Tin, _ = inner("nominal", v)
        Io = (0.01 / 1.0) / (1 - zo)
        Lo = Io * np.exp(-2j * np.pi * F * 0.06) * np.exp(2j * np.pi * F * Dl) * Tin
        PM, FC, PMR, gmu, gmd = SF.pm_gm(Lo)
        rowc.append((PM, gmu))
    lead[str(Dl)] = rowc
    pr("   Delta %.1f s: min PM %.1f deg, min GM %.1f dB over speeds  (per speed PM: %s)"
       % (Dl, min(x[0] for x in rowc), min(x[1] for x in rowc), " ".join("%.0f" % x[0] for x in rowc)))
R["lead"] = lead

pr("\n3. Tin (theta / theta_sp) of the inner loop, nominal: |Tin| and group delay at 0.1 / 0.25 / 0.5 Hz -> the lead the "
   "fork needs to cancel the LINEAR lag (BELIEF: the car's small-signal lag is friction-shaped, M6)")
gd = {}
for v in SPEEDS:
    _, _, Tin, _ = inner("nominal", v)
    ph = np.unwrap(np.angle(Tin))
    out = []
    for f0 in (0.1, 0.25, 0.5):
        i = int(np.argmin(abs(F - f0)))
        out.append((float(abs(Tin[i])), float(-ph[i] / (2 * np.pi * F[i]))))
    gd[v] = out
    pr("   %5.2f m/s: " % v + "  ".join("%.2f Hz |T| %.2f lag %3.0f ms" % (f0, a, 1000 * b)
                                       for f0, (a, b) in zip((0.1, 0.25, 0.5), out)))
R["tin"] = {str(k): v for k, v in gd.items()}
R["wall_s"] = time.perf_counter() - T0
pr("\nwall %.1f s" % R["wall_s"])
(C.OUT / "gate2_fork.txt").write_text("\n".join(L_) + "\n", encoding="utf-8")
(C.OUT / "gate2_fork.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
