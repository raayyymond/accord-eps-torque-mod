# -*- coding: utf-8 -*-
r"""s1_freq.py -- S1-frequency: THE COMMON FREQUENCY SCORER for the V299 judge-panel design round (2026-10-02).

ANALYSIS ONLY.  Builds nothing, flashes nothing, sends nothing, edits no fork / firmware / golden model.  Written by the
S1-frequency scorer (a subagent of the orchestrator).  Designers do not grade their own work here: every candidate of
every designer (D1..D5) goes through ONE code path -- the same engine, member set, frame box, hold ages, operating
points, friction states, metric extractor and bars.

ENGINE (imported UNCHANGED): refute_stability/c3r1/c3r1_model.py -- the independent C3-r1 stability model that cleared
V298 (rb_gate2) and that D1/D3/D4 used: exact sampled-data plant channels (modified-z, fractional delay), the 100 Hz
hold at offsets e, the gp-0x6abe EMA (37/128), the output lag (OA 992 / OB 507), FWD 5346, fade 254/256, the r71b
identified plant family (p5c.json J-profile, p5b_ms.json ms_free) = the same identification as harness_freq.py's
v294_plant family.  Its constants are read from the V295 image; this file RE-READS every one of them from the V298
image (sha 177abf04...) at the same addresses and asserts equality, and reads the V298 G(v) table, Ki, the Kp/Kd
record knots from the V298 image (little-endian) -- nothing from any build script.

ROUTE-79 UPDATES OF THE PLANT/CONTROLLER FAMILY (each an extra axis, not a replacement):
  (R1) the measured D fraction 0.55-0.88x design and P 0.93-0.96x (DRIVE-READ-V298-r79 sec.5): two extra frames
       R79.55 (D x0.55, P/I x0.93) and R79.88 (D x0.88, P/I x0.96), gated with the frame box.
  (R2) the measured Coulomb friction (Fc 156 T at 0-5 m/s, 73-94 T at speed; single method): a DESCRIBING-FUNCTION
       friction state.  Sliding at amplitude A deg, the fundamental of Fc sgn(w) is an equivalent viscous term
       b_eq(f) = 4 Fc / (pi A 2 pi f) T per deg/s (hysteretic: b_eq j w = j 4Fc/(pi A), frequency-flat).  It closes
       around the plant's own rate channel:  Pt' = Pt/(1 + b_eq Pw),  Pw' = Pw/(1 + b_eq Pw).  States: free (Fc 0),
       A = 5 deg, A = 1 deg (the small-correction regime).  Fc(v) = interp(v, [5, 8], [156, 85]).
  (R3) the measured closed loop (bandwidth 0.4-0.6 Hz at 8-25 m/s, 1.1 Hz > 25, |H| <= 0.96): a CONSISTENCY table of
       V298's modelled T_ref per member x friction state (which members / states reproduce route 79).
OPERATING POINTS: the spring softened by tyre saturation, k -> k sech^2(theta_op / sat(v)), sat = 19.3 + 546 e^(-v/3.01)
  (the refuter's F1 form, as D1/D3/D4 used), theta_op = theta(v, a_lat) for a_lat 0 / 1.5 / 2.5 m/s^2 (SR 16, L 2.83 m),
  capped at 360 deg.
LOOP STATES: PID (hands-off) and PD (I frozen / A3-bounded: every freeze, bound or clamp-saturated state), and PD at
  the hands-on fade floor 76/254 (report).
FORK-COUPLED LOOPS (what the fork-side candidates change in a FEEDBACK sense):
  O1 loop    setpoint := theta_fork + tau_O1 * rate  =>  sp = W theta, W = e^(-jw Trt) (1 + tau_O1 jw);  Trt 30/60/90 ms,
             fade 1 and 0.297, PID and PD.  tau_O1 = 0.06 s (V298, D1, D3, D4, D5) or 0 (D2).
  clip loop  error clip bound: sp = theta_fork +- c  =>  W = e^(-jw Trt)  (V298, and every lead placed BEFORE the clip);
             D3's K3 lead is added AFTER the clip on the rate of the post-clip setpoint, so in the clip-bound state it
             feeds the wheel's own rate back: W = e^(-jw Trt) (1 + 0.5 tau_D(v) jw LP30).
  path loop  the panel's outer model (integral tau_o 1 s, 60 ms) around T_ref x the candidate's reference lead (report).
BARS (rb_gate2 / panel R2): tier-A singles PM >= 45 (e <= 0) / 30 (aged e > 0); combined members 30; GM_up >= 6 dB;
  |T_c| 5-30 Hz <= +3 dB.  Brief flags: worst PM < 30 deg anywhere on the grid; 5-30 Hz loop gain > V298's.
usage:  python s1_freq.py            (all candidates, one Pool batch; wall printed)
        python s1_freq.py selftest   (vectorised extractor == c3r1 pm_gm; tables vs image; V298 control anchors)
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import struct
import sys
import time
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[2]                                   # .../studies/angle_loop
KIT = AL.parents[2]
sys.path.insert(0, str(AL / "refute_stability" / "c3r1"))
import c3r1_model as M  # noqa: E402

SCR = KIT / "_scratch" / "v299_S1"
SCR.mkdir(parents=True, exist_ok=True)
OUTD = HERE / "out"
OUTD.mkdir(parents=True, exist_ok=True)

# ======================================================================================================================
# 0. the V298 image: every constant the loop needs, little-endian, sha asserted
# ======================================================================================================================
V298_SHA = "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"


def v298_image():
    p = sorted(glob.glob(os.path.join(os.environ["ACCORD_FIRMWARE_ROOT"], "analysis-2020accord", "_v298_*_plain_image.bin")))
    assert len(p) == 1, p
    b = Path(p[0]).read_bytes()
    assert hashlib.sha256(b).hexdigest() == V298_SHA
    return b


IMG = v298_image()
u16 = lambda a: struct.unpack_from("<H", IMG, a)[0]  # noqa: E731
i16 = lambda a: struct.unpack_from("<h", IMG, a)[0]  # noqa: E731
TABLE = 0xC4CDA                                        # GB-P: 7 rows (X u16, G u16, S i16 Q12); knot-0 G at 0xC4CDC
GBP = tuple((u16(TABLE + 6 * k), u16(TABLE + 6 * k + 2), i16(TABLE + 6 * k + 4)) for k in range(7))
assert GBP[-1][0] == 0xFFFF
KI = u16(0xC63E6)                                      # Ki (I += ((E'>>5)*Ki)>>3)
KP = [u16(0xE5384 + 2 * j) for j in range(5)]          # Kp Y knots (selector-7 record)
KD = [u16(0xE5126 + 2 * j) for j in range(4)]          # Kd Y knots
assert KI == 40 and set(KP) == {112} and set(KD) == {48}, (KI, KP, KD)
# the engine's constants (read by c3r1_model from the V295 image) are the SAME bytes in the V298 image:
assert (i16(0xC63EC), u16(0xC63EE), i16(0xC6CD0), u16(0xC643C), u16(0xC613A)) == (M.OA, M.OB, M.FWD, 37, M.K1159)

# ======================================================================================================================
# 1. the unique LINEAR loops (each candidate maps onto one; a candidate whose bytes leave Kp/Ki/Kd/G/operands
#    unchanged has V298's loop by construction -- its freezes/bounds/clamps only switch PID <-> PD)
# ======================================================================================================================


def reslope(rows):
    """recompute every Q12 slope S(i) = round((G(i+1)-G(i)) 4096 / (X(i+1)-X(i))) (the rule D1/D3/D4 used)."""
    out = []
    for i in range(len(rows)):
        X, G = rows[i][0], rows[i][1]
        if i + 1 < len(rows) and rows[i + 1][0] != 0xFFFF:
            S = int(round((rows[i + 1][1] - G) * 4096 / (rows[i + 1][0] - X)))
        else:
            S = 0
        out.append((X, G, S))
    return tuple(out)


assert reslope(GBP) == GBP                             # control: the slope rule reproduces the image table
T_G0_1400 = tuple([(GBP[0][0], 1400, 236)] + list(GBP[1:]))          # D1 (a2): 0xC4CDC 9a04->7805, 0xC4CDE 1104->ec00
T_D3A = tuple([(GBP[0][0], 1414, 185)] + list(GBP[1:]))              # D3 (a): G0 1178->1414, S0 1041->185
T_GBS13 = reslope(tuple((X, int(round(G * 1.3)) if i in (2, 3, 4) else G, S) for i, (X, G, S) in enumerate(GBP)))
assert reslope(T_G0_1400) == T_G0_1400 and reslope(T_D3A) == T_D3A
# D4's page lists these halfwords (0xC4CE4 S1 -4238, 0xC4CE8 G2 988, 0xC4CEA S2 -2643, 0xC4CEE G3 728, 0xC4CF4 G4 1388)
assert (T_GBS13[1][2], T_GBS13[2][1], T_GBS13[2][2], T_GBS13[3][1], T_GBS13[4][1]) == (-4238, 988, -2643, 728, 1388)


@dataclass(frozen=True)
class Loop:
    name: str
    rows: tuple
    kp: float = 112.0
    ki: float = 40.0
    kd: float = 48.0
    wash: bool = False                                 # D5 (a): D on abe minus its 2^-9 EMA


LOOPS = (
    Loop("V298", GBP),
    Loop("G0-1400", T_G0_1400),
    Loop("D3a-tab", T_D3A),
    Loop("GB-S13", T_GBS13),
    Loop("D5a-small", GBP, kp=112.0 + 28.0, wash=True),   # friction comp clamp((E'Kf)>>8,+-Lf) small-signal = +28 on P
    Loop("D5a-sat", GBP, kp=112.0, wash=True),            # friction comp saturated (|E'Kf>>8| > Lf): P back to 112
)
LIDX = {l.name: i for i, l in enumerate(LOOPS)}
DES = [M.Design(l.name, "fresh", kp=l.kp, ki=l.ki, kd=l.kd, rows=l.rows) for l in LOOPS]
DES_V295 = M.Design("V295", "v295")

# ======================================================================================================================
# 2. the grid
# ======================================================================================================================
F = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 640),
                              [0.05, 0.1, 0.2, 0.5, 1, 2, 3, 5, 7, 10, 13, 15, 16, 17, 18, 20, 22, 25, 30]]))
W = 2 * np.pi * F
ZI = np.exp(-1j * W * M.TS)
B530 = (F >= 5) & (F <= 30)
B1517 = (F >= 13) & (F <= 17)
B1822 = (F >= 18) & (F <= 22)
BREF = (F >= 0.05) & (F <= 3.0)
SPEEDS = (2.0, 3.1, 4.0, 5.0, 6.5, 8.0, 9.0, 10.0, 11.0, 11.75, 13.0, 15.0, 17.5, 20.0, 26.9, 30.0)
SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free")
COMBINED = ("b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6", "b_lo*ms_free", "b_q*ms_free")
MEMBERS = SINGLE + COMBINED
S_C = 1.155
FRAMES = (("nom", 1.0, 1.0, 1.0), ("FA.83", 0.83, 1.0, 1.0), ("FA1.155", 1.155, 1.0, 1.0),
          ("FB.83", 0.83, 1 / S_C, 1.0), ("FB1.155", 1.155, 1 / S_C, 1.0),
          ("R79.55", 0.55, 1.0, 0.93), ("R79.88", 0.88, 1.0, 0.96))        # (name, kappa on D, J/b scale, P/I scale)
GATE_FR = (0, 1, 2, 3, 4)
ES = (-1, 0, 10)
A_OP = (0.0, 1.5, 2.5)
FRIC = (("free", 0.0), ("A5", 5.0), ("A1", 1.0))
SR, LWB = 16.0, 2.83
TRT = (0.03, 0.06, 0.09)
FADE_HON = 76.0 / 254.0                                # the hands-on fade floor x0.30 (relative to the 254/256 FADE)


def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)


def theta_op(v, a):
    return 0.0 if a == 0 else min(360.0, SR * LWB * a / (v * v) * 180.0 / math.pi)


def fc_of(v):
    return float(np.interp(v, [5.0, 8.0], [156.0, 85.0]))


def bar_of(mem, e):
    return (45.0 if e <= 0 else 30.0) if mem in SINGLE else 30.0


HPF = 1.0 - (2.0 ** -9) / (1.0 - (1.0 - 2.0 ** -9) * ZI)        # D5 (a) washout on the D operand
LP30 = 1.0 / (1.0 + 1j * W * 0.03)
ZF = np.exp(-1j * W * 0.01)                                       # the fork's 100 Hz frame
BX5 = (1 - ZF ** 5) / 0.05                                        # 5-frame boxcar slope (D5 lead)


def cP_TperDeg(G):                                     # D3's c_P(v) = 160 G 112/65536 x 0.16029 T/deg  (tau_D = 4.532/c_P)
    return 160.0 * G * 112.0 / 65536.0 * 0.16029


def tauD_D3(v):
    return 4.532 / cP_TperDeg(M.walk_G(T_D3A, M.spd(v)))


TAU_L_BP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])         # D5: tau_L = 89.5/G (image knots), dose 0.5
TAU_L_V = 89.5 / np.array([1178.0, 1465.0, 760.0, 560.0, 1068.0, 2188.0])
TAU_PLAN_BP = np.array([3.1, 8, 10, 11.75, 14, 17.5, 22, 26.9])  # D2 (b) plan-lead schedule
TAU_PLAN_V = np.array([0.05, 0.10, 0.15, 0.25, 0.32, 0.35, 0.22, 0.10])

# ======================================================================================================================
# 3. ONE vectorised metric extractor (== c3r1_model.pm_gm row by row; checked in selftest)
# ======================================================================================================================


def pm_gm_rows(L):
    """L (n, nf) -> PM, fc, GMu (each (n,)).  PM = min over |L| = 1 crossings of 180 - |wrap(phase)|."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L), axis=1) * 180.0 / np.pi
    m0, m1 = mag[:, :-1], mag[:, 1:]
    s0, s1 = m0 - 1.0, m1 - 1.0
    cr = (s0 * s1 <= 0) & (m0 != m1)
    den = np.where(m1 != m0, m1 - m0, 1.0)
    t = (1.0 - m0) / den
    p = ph[:, :-1] + t * (ph[:, 1:] - ph[:, :-1])
    pmv = 180.0 - np.abs(((p + 180.0) % 360.0) - 180.0)
    pmv = np.where(cr, pmv, np.inf)
    j = np.argmin(pmv, axis=1)
    r = np.arange(L.shape[0])
    PM = pmv[r, j]
    fcv = F[:-1] + t * (F[1:] - F[:-1])
    FC = np.where(np.isfinite(PM), fcv[r, j], np.nan)
    wr = np.floor((ph + 180.0) / 360.0)
    jx = wr[:, :-1] != wr[:, 1:]
    up = np.where(jx & (m0 < 1.0), m0, 0.0).max(axis=1)
    GMu = np.where(up > 0, -20.0 * np.log10(np.where(up > 0, up, 1.0)), np.inf)
    return PM, FC, GMu


def extras(L, Lref=None):
    Sx = 1.0 / (1.0 + L)
    Ms = np.abs(Sx).max(axis=1)
    Tc = 20 * np.log10(np.maximum(np.abs(L * Sx)[:, B530].max(axis=1), 1e-12))
    l1 = np.abs(L[:, B1517]).max(axis=1)
    l2 = np.abs(L[:, B1822]).max(axis=1)
    r530 = (np.abs(L[:, B530]) / np.abs(Lref[:, B530])).max(axis=1) if Lref is not None else np.ones(len(L))
    return Ms, Tc, l1, l2, r530


# ======================================================================================================================
# 4. the worker: one (member, speed) -> every loop x frame x e x PID/PD x operating point x friction state, plus the
#    fork-coupled loops (O1, clip) at theta_op 0 / free, plus V295's band gains
# ======================================================================================================================
COLS = ("loop", "mem", "v", "fr", "e", "noI", "aop", "fric", "fade", "PM", "fc", "GMu", "Ms", "Tc530", "L1517", "L1822",
        "r530", "bar", "V295_1517", "V295_1822")
FCOLS = ("kind", "loop", "mem", "v", "fr", "e", "noI", "tau", "trt", "fade", "PM", "fc", "GMu", "Ms")
KINDS = ("O1.06", "O1.00", "clip", "clipD3lead")


def ctl_pieces(d: M.Design, l: Loop, v, e, noI):
    Cth, Cw, Cref = M.controller(d, v, F, e, 1.0, noI=noI)
    if l.wash:
        Cw = Cw * HPF
    return Cth, Cw, Cref


# the evaluation BLOCKS: (theta_op index, friction index, frames, hold offsets) -- the core gate is the full frame box;
# the operating-point and friction axes use the frames that bind and the two route-79 frames (wall-time rule: < 30 s)
BLOCKS = (
    ("core", 0, 0, (0, 1, 2, 3, 4, 5, 6), (-1, 0, 10)),
    ("op1.5", 1, 0, (0, 1, 2, 3, 4), (0, 10)),
    ("op2.5", 2, 0, (0, 1, 2, 3, 4), (0, 10)),
    ("fricA5", 0, 1, (0, 3, 5, 6), (0, 10)),
    ("fricA1", 0, 2, (0, 3, 5, 6), (0, 10)),
)
FORK_FR = (0, 1, 4)                                    # nom, FA.83, FB1.155 for the fork-coupled loops
FORK_ES = (0, 10)


def _fric(Pt, Pw, v, A_amp):
    if A_amp <= 0:
        return Pt, Pw
    beq = 4.0 * fc_of(v) / (math.pi * A_amp * W)
    den = 1.0 + beq * Pw
    return Pt / den, Pw / den


def work(args):
    im, iv = args
    mem, v = MEMBERS[im], SPEEDS[iv]
    rows, frows, cons = [], [], []
    K1 = M.Kout(F, 1.0)
    Kh = M.Kout(F, FADE_HON)
    pieces = {(li, e, noI): ctl_pieces(DES[li], LOOPS[li], v, e, noI) for li in range(len(LOOPS))
              for e in ES for noI in (False, True)}
    v295 = {e: M.controller(DES_V295, v, F, e, 1.0)[1] for e in ES}
    chans_op = {}
    for ia, a in enumerate(A_OP):
        pl = M.member(mem, v)
        th = theta_op(v, a)
        if th:
            pl.k *= 1.0 - math.tanh(th / sat(v)) ** 2
        chans_op[ia] = {jb: M.plant_channels(pl, F, jb) for jb in (1.0, 1 / S_C)}
    for bname, ia, ifc, frs, es in BLOCKS:
        A_amp = FRIC[ifc][1]
        Lbuf, meta, Lref, v295b = [], [], [], []
        for ifr in frs:
            fn, kap, jb, ps = FRAMES[ifr]
            Pt, Pw = _fric(*chans_op[ia][jb], v, A_amp)
            for e in es:
                Lv295 = -K1 * (kap * v295[e] * Pw)
                for noI in (False, True):
                    Lv298 = None
                    for li in range(len(LOOPS)):
                        Cth, Cw, Cref = pieces[(li, e, noI)]
                        L = -K1 * (ps * Cth * Pt + kap * Cw * Pw)
                        if li == 0:
                            Lv298 = L
                        Lbuf.append(L)
                        Lref.append(Lv298)
                        v295b.append(Lv295)
                        meta.append((li, im, iv, ifr, e, int(noI), ia, ifc, 1.0))
                if bname == "core" and ifr == 0 and e == 0:      # hands-on fade floor, I frozen (report)
                    Lh0 = None
                    for li in range(len(LOOPS)):
                        Cth, Cw, Cref = pieces[(li, e, True)]
                        L = -Kh * (ps * Cth * Pt + kap * Cw * Pw)
                        if li == 0:
                            Lh0 = L
                        Lbuf.append(L)
                        Lref.append(Lh0)
                        v295b.append(Lv295)
                        meta.append((li, im, iv, ifr, e, 1, ia, ifc, FADE_HON))
        L = np.array(Lbuf)
        PM, FC, GMu = pm_gm_rows(L)
        Ms, Tc, l1, l2, r530 = extras(L, np.array(Lref))
        V = np.abs(np.array(v295b))
        v1, v2 = V[:, B1517].max(axis=1), V[:, B1822].max(axis=1)
        for k, mt in enumerate(meta):
            rows.append(mt + (PM[k], FC[k], GMu[k], Ms[k], Tc[k], l1[k], l2[k], r530[k], bar_of(mem, mt[4]),
                              v1[k], v2[k]))
    # ---- the r79 consistency: V298 PID, frames nom / R79.55, e 0, theta_op 0, each friction state ----
    for ifc, (A_name, A_amp) in enumerate(FRIC):
        for ifr in (0, 5):
            fn, kap, jb, ps = FRAMES[ifr]
            Pt, Pw = _fric(*chans_op[0][jb], v, A_amp)
            Cth, Cw, Cref = pieces[(0, 0, False)]
            Lx = -K1 * (ps * Cth * Pt + kap * Cw * Pw)
            Tr = K1 * ps * Cref * Pt / (1 + Lx)
            a_ = np.abs(Tr)
            below = np.where((a_ < 1 / math.sqrt(2)) & (F > 0.02))[0]
            bw = float(F[below[0]]) if len(below) else float("nan")
            i01 = int(np.argmin(abs(F - 0.1)))
            lag01 = float(-np.angle(Tr[i01]) / W[i01] * 1000)
            cons.append((im, iv, ifr, ifc, bw, float(a_[BREF].max()), lag01))
    # ---- fork-coupled loops: theta_op 0, free ----
    Lbuf, meta = [], []
    tD = tauD_D3(v)
    for ifr in FORK_FR:
        fn, kap, jb, ps = FRAMES[ifr]
        Pt, Pw = chans_op[0][jb]
        for e in FORK_ES:
            for noI in (False, True):
                for li in range(len(LOOPS)):
                    Cth, Cw, Cref = pieces[(li, e, noI)]
                    for trt in TRT:
                        dl = np.exp(-1j * W * trt)
                        for kind in KINDS:
                            if kind == "clipD3lead" and LOOPS[li].name not in ("V298", "D3a-tab"):
                                continue
                            if kind == "O1.00" and LOOPS[li].name != "V298":
                                continue
                            fades = (1.0, FADE_HON) if kind.startswith("O1") else (1.0,)
                            if kind == "O1.06":
                                Wf, tau = dl * (1 + 0.06 * 1j * W), 0.06
                            elif kind in ("O1.00", "clip"):
                                Wf, tau = dl, 0.0
                            else:
                                Wf, tau = dl * (1 + 0.5 * tD * 1j * W * LP30), 0.5 * tD
                            for fd in fades:
                                K = K1 if fd == 1.0 else Kh
                                Lbuf.append(-K * (Cth * Pt + kap * Cw * Pw + Cref * Wf * Pt))
                                meta.append((KINDS.index(kind), li, im, iv, ifr, e, int(noI), tau, trt, fd))
    L = np.array(Lbuf)
    PM, FC, GMu = pm_gm_rows(L)
    Ms = np.abs(1 / (1 + L)).max(axis=1)
    for k, mt in enumerate(meta):
        frows.append(mt + (PM[k], FC[k], GMu[k], Ms[k]))
    return rows, frows, cons


# ======================================================================================================================
# 5. path loop + reference metrics (nominal member, frame nom, e 0, free, theta_op 0, PID) per CANDIDATE reference lead
# ======================================================================================================================
def ref_lead(kind, v):
    if kind == "none":
        return np.ones_like(W, dtype=complex)
    if kind == "D3K3":
        return 1 + 0.5 * tauD_D3(v) * 1j * W * LP30
    if kind == "D5lead":
        return 1 + 0.5 * float(np.interp(v, TAU_L_BP, TAU_L_V)) * BX5 * LP30
    if kind == "D2aSD":                                  # SteerDelay +0.10 s as a first-order advance (BELIEF)
        return 1 + 0.10 * 1j * W
    if kind == "D2bPlan":                                # trajectory-sampled lead tau(v) as a first-order advance (BELIEF)
        return 1 + float(np.interp(v, TAU_PLAN_BP, TAU_PLAN_V)) * 1j * W
    raise KeyError(kind)


def path_table(loop_name, lead_kind, speeds=(3.1, 5.0, 8.0, 11.75, 17.5, 26.9)):
    li = LIDX[loop_name]
    out = []
    for v in speeds:
        pl = M.member("nominal", v)
        Pt, Pw = M.plant_channels(pl, F, 1.0)
        Cth, Cw, Cref = ctl_pieces(DES[li], LOOPS[li], v, 0, False)
        K = M.Kout(F, 1.0)
        L = -K * (Cth * Pt + Cw * Pw)
        Tr = K * Cref * Pt / (1 + L) * ref_lead(lead_kind, v)
        a_ = np.abs(Tr)
        below = np.where((a_ < 1 / math.sqrt(2)) & (F > 0.02))[0]
        bw = float(F[below[0]]) if len(below) else float("nan")

        def lag(f0):
            i = int(np.argmin(abs(F - f0)))
            return float(-np.angle(Tr[i]) / W[i] * 1000)
        Lo = (0.01 / 1.0) / (1 - ZF) * np.exp(-1j * W * 0.06) * Tr
        PMo, FCo, GMo = pm_gm_rows(Lo[None, :])
        i20 = int(np.argmin(abs(F - 20.0)))
        out.append(dict(v=v, Tpk=float(a_[BREF].max()), bw=bw, lag02=lag(0.2), lag05=lag(0.5), T20=float(a_[i20]),
                        T1517=float(a_[B1517].max()), T1822=float(a_[B1822].max()), PMo=float(PMo[0]),
                        GMo=float(GMo[0])))
    return out


# ======================================================================================================================
# 6. candidates -> (inner loop, fork terms)
# ======================================================================================================================
CANDS = [
    # id, designer, inner loop, O1 kind, O1 I-state under a 600-1229 hand ('PID' if fw freeze > O1 level), clip kind, ref lead
    ("D1c", "D1", "V298", "O1.06", "PID+PD", "clip", "none", "fw: freeze 1229, opposing clause removed, A3 asymmetric; fork bar"),
    ("D1a", "D1", "V298", "O1.06", "PID+PD", "clip", "none", "fw: both freeze immediates 1229 (NOT FOR FLIGHT)"),
    ("D1-a2 G0-1400", "D1", "G0-1400", "O1.06", "PID+PD", "clip", "none", "GB-P knot 0 G 1178->1400, S 1041->236"),
    ("D1 fork bar", "D1", "V298", "O1.06", "PD", "clip", "none", "bar from 0x1AB only (no loop term)"),
    ("D2a", "D2", "V298", "O1.00", "PD", "clip", "D2aSD", "fork only; O1 lead 0, SteerDelay 0.45"),
    ("D2b", "D2", "V298", "O1.00", "PD", "clip", "D2bPlan", "D2a + 1500 deg/s^2 limiter + plan lead"),
    ("D3-a", "D3", "D3a-tab", "O1.06", "PD", "clipD3lead", "D3K3", "G x1.2 @3.1 taper; freeze 1229/800; fork K1-K5"),
    ("D3-b", "D3", "D3a-tab", "O1.06", "PD", "clipD3lead", "D3K3", "D3-a + rail 3057 T (a clamp: linear = D3-a)"),
    ("D4b", "D4", "V298", "O1.06", "PID+PD", "clip", "none", "LP hand word + motion-gated freeze (policy only)"),
    ("D4a", "D4", "GB-S13", "O1.06", "PID+PD", "clip", "none", "GB-S13 knots 10/11.75/17.5 x1.3"),
    ("D4b+GBS13", "D4", "GB-S13", "O1.06", "PID+PD", "clip", "none", "D4b + GB-S13"),
    ("D5 V299-b", "D5", "V298", "O1.06", "PID+PD", "clip", "D5lead", "freeze 1229; fork O1 debounce, cap, clip, lead 0.5 D/P"),
    ("D5 V299-a", "D5", "D5a-small", "O1.06", "PID+PD", "clip", "none", "washout D + friction comp Kf 28 (also D5a-sat)"),
    ("V298 (control)", "-", "V298", "O1.06", "PD", "clip", "none", "the flown baseline"),
]


def selftest():
    t0 = time.time()
    # (1) the vectorised extractor equals c3r1_model.pm_gm on random rows of real loops
    pl = M.member("b_lo*J_hi", 8.0)
    Pt, Pw = M.plant_channels(pl, F, 1.0)
    Ls = []
    for li in range(len(LOOPS)):
        for e in ES:
            for noI in (False, True):
                Cth, Cw, _ = ctl_pieces(DES[li], LOOPS[li], 8.0, e, noI)
                Ls.append(-M.Kout(F) * (Cth * Pt + Cw * Pw))
    L = np.array(Ls)
    PM, FC, GM = pm_gm_rows(L)
    for k in range(len(L)):
        a, b, c = M.pm_gm(L[k], F)
        assert abs(a - PM[k]) < 1e-9 and (abs(b - FC[k]) < 1e-9 or (math.isnan(b) and math.isnan(FC[k]))) \
            and (abs(c - GM[k]) < 1e-9 or (math.isinf(c) and math.isinf(GM[k]))), (k, a, PM[k], c, GM[k])
    # (2) the engine's own loop() equals this file's assembly
    Lm, _, _, _ = M.loop(DES[0], pl, 8.0, f=F, e=10, kappa=0.83, jb=1 / S_C)
    Pt2, Pw2 = M.plant_channels(pl, F, 1 / S_C)
    Cth, Cw, _ = ctl_pieces(DES[0], LOOPS[0], 8.0, 10, False)
    assert np.max(np.abs(Lm - (-M.Kout(F) * (Cth * Pt2 + 0.83 * Cw * Pw2)))) < 1e-12
    # (3) G walk of the image table at the D3 knots (Kp_eff = 112 G/256 x ... ) and V298's design anchors
    G = [M.walk_G(GBP, M.spd(v)) for v in (3.1, 8.0, 10.0, 11.75, 17.5, 26.9)]
    print("selftest: extractor == c3r1 pm_gm on %d rows; engine loop() == assembly; V298 G walk %s; wall %.1f s"
          % (len(L), G, time.time() - t0))
    print("tables:", {l.name: l.rows[:5] for l in LOOPS[:4]})
    print("D3 tau_D(v):", {v: round(tauD_D3(v), 4) for v in (3.1, 5, 8, 10, 11.75, 17.5, 26.9)})


def main(procs=16):
    t0 = time.time()
    jobs = [(im, iv) for im in range(len(MEMBERS)) for iv in range(len(SPEEDS))]
    with Pool(procs) as P:
        res = P.map(work, jobs, chunksize=2)
    t1 = time.time()
    R = np.array([r for a, _, _ in res for r in a], float)
    FR = np.array([r for _, b, _ in res for r in b], float)
    CO = np.array([r for _, _, c in res for r in c], float)
    np.savez_compressed(SCR / "s1_rows.npz", R=R, FR=FR, CO=CO)
    paths = {}
    for kind in ("none", "D3K3", "D5lead", "D2aSD", "D2bPlan"):
        for ln in ("V298", "D3a-tab") if kind == "D3K3" else ("V298",):
            paths[(ln, kind)] = path_table(ln, kind)
    for ln in ("G0-1400", "GB-S13", "D5a-small"):
        paths[(ln, "none")] = path_table(ln, "none")
    json.dump({"%s|%s" % k: v for k, v in paths.items()}, open(SCR / "s1_paths.json", "w"), indent=1)
    print("loops: %d inner rows, %d fork rows, %d consistency rows; pool wall %.1f s, total %.1f s"
          % (len(R), len(FR), len(CO), t1 - t0, time.time() - t0))
    json.dump({"pool_wall_s": t1 - t0, "total_wall_s": time.time() - t0, "n_inner": len(R), "n_fork": len(FR),
               "unique_loops": len(LOOPS)}, open(SCR / "s1_wall.json", "w"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        selftest()
    else:
        main()
