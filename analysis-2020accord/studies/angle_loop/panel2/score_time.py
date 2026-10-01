# -*- coding: utf-8 -*-
r"""score_time.py -- PANEL 2 COMMON TIME-DOMAIN SCORER (2026-10-01).  ONE identical 1 kHz pipeline for every panel-2
candidate (E1, E2, G, H) and the four round-1 implementations (rev2-A P2 / F2, rev2-B D2a / B0r).  ANALYSIS ONLY: builds
no image, flashes nothing, sends nothing, touches no fork file.  Report: SCORE-TIME-2026-10-01.md (same folder).

ENGINE (what is reused, what is new; every reuse is controlled in `validate`):
  * plant + members + sensors + fork + metric helpers = the round-2 NONLINEAR refuter's independent engine
    (refute_c2r2_nonlinear/nl_sim.py: Karnopp plant on the r71b family, 10 kHz sub-steps, 2 ms transport; gp-0x6a00 =
    floor(10 th + 0.5) held at slot 4 AFTER the lane; gp-0x6abe = 1 kHz integer EMA (alpha 37/128) of gp-0x4f50 =
    s16(round(-4.712 * motor-frame deg/s + N(0, 2.8))); gp-0x6a56 = slot-4 hold of clamp(-((abe*48*1159)>>15), +-12000);
    0xE4 on tick % 10 == 0, raw = -round(10 th_sp), gp-0x69ae = clamp(-4 raw, +-16384); a stop holds the last value).
    nl_sim was proved bit-exact against rev2-A's score_time engine (ds_time / DSLane / PlantVec) by the refuter
    (ctl_vs_designers.py); `validate` re-runs that control.
  * THE LANE = CandLane below: nl_sim.Lane's instruction-by-instruction arithmetic (0x28F4C..0x2A20C with the C2 in-place
    set E1 E2 E4 A2 B2 OPH / E5), generalised so that EVERY candidate's cave arithmetic is a per-column switch:
      G(v) table (any rows, the cave's walk G(i) + ((v - X(i)) S(i)) >> 12), D operand fresh / held / box10, Kp, Ki, Kd,
      ICL (flat or E1-sched's walk), freeze threshold, E1 firm reset, E1 light bleed (the LISTED bytes: I8 -= I8 >> 3 in
      the non-freeze path), E2 opposing-hand freeze / leak / angle-referenced bound / low-speed cap (E2Lane's ordered
      decision), H freeze+bleed (I8 -= I8 >> bsh above THR), H-A's fresh motor-linear feedback gp-0x69ca, the
      gp-0x6803 == 2 arm (fade 0xCBAE4/0xCBB54, ramp-in 328, ramp-out 66).
    CONTROLS (`validate`): CandLane == nl_sim.Lane bit for bit on P2/F2/D2a/B0r; == E1Lane on the E1 policies; == E2Lane
    and GLane (DSLane subclasses) through rev2-A's engine; and every candidate's cave HEX is EXECUTED by an extension of
    the refuter's independent V850E2 interpreter (nl_cave.Cpu) against CandLane's own cave stage (`h1`).
  * NEW: the FRAME.  gp-0x6a00 = C(gp-0x69ca): the firmware's correction LERP (0xC6892/0xC68A2, angle_signal_mirror)
    makes the corrected angle 1.155x the motor-linear angle near centre (0.96-1.16 outward).  The plant is identified in
    the gp-0x6a00 frame (carState angle), so every MOTOR-frame quantity is mapped: motor rate = omega / kappa(theta)
    (gp-0x4f50 -> gp-0x6abe, gp-0x6a56) and gp-0x69ca = floor(10 C^-1(theta) + 0.5).  frame='vgr' (PRIMARY) applies it;
    frame='unity' is every previous scorer's convention (kappa = 1) and is run for the validation / attribution columns.
    H-A's fork SR fold is modelled as PERFECT (the fork sends C^-1(theta_sp) in the 69ca frame) -- BELIEF.

MEMBERS nominal, bc, F_hi, b_lo*J_hi (nl_sim.params).  SPEEDS 3.0 3.1 5.0 and 8.00..30.00 every 0.25 m/s + 11.9 26.9.
SCENARIOS (definitions in scenario()): r71b real paths clean / with r71b's own torque word replayed (tracking slope,
real-curve turn-hold, dwell-then-jump); synthetic turn-hold a_lat 1.0/1.5/2.0/2.5 m/s^2; +-0.3 and +-1 deg at 0.2/0.5 Hz;
step-and-hold; 30 s constant setpoint; 30 s with road noise 15 T counts rms (0.5-30 Hz); light-hand words 400/511/1000
and firm 2400 (1 s override, stiff hand, SIGNED word) then release; engage under load with the measured angle (ramp-in
per candidate); co-steer release; 510 ms timeout held and mid-motion; 0xE4 sentinel; request drop; dead band creep;
hard turn 1.6-3 Hz.

usage:  python score_time.py h1                 (cave HEX executed vs CandLane's cave stage, every hex-backed candidate)
        python score_time.py validate           (controls V1-V4; writes out/validate_out.txt)
        python score_time.py run [procs] [frame] [scn,scn,...]   (the grid; caches in _scratch/angle_loop/panel2-score-time)
        python score_time.py report             (out/score_time_tables.md + the summary json the .md quotes)"""
from __future__ import annotations

import json
import os
import struct
import sys
import time
from dataclasses import dataclass, field, replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import numpy as np

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
HERE = Path(__file__).resolve().parent                       # .../studies/angle_loop/panel2
AL = HERE.parent                                             # .../studies/angle_loop
KIT = AL.parents[2]                                          # repo root
RC2 = AL / "refute_c2r2_nonlinear"
for _q in (RC2, AL, AL.parent / "v295" / "plant"):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))

import nl_sim as NS                    # noqa: E402  the refuter's independent engine (plant, params, sensors, helpers)
import nl_cave as NC                   # noqa: E402  the refuter's independent V850E2 interpreter + table parse / walk
import angle_signal_mirror as AM       # noqa: E402  the byte-exact angle chain (the correction LERP)
from nl_sim import s16, s32, lerp_vec  # noqa: E402

OUT = KIT / "_scratch" / "angle_loop" / "panel2-score-time"
OUT.mkdir(parents=True, exist_ok=True)
TXT = HERE / "score_time_out"
TXT.mkdir(parents=True, exist_ok=True)
SENT32 = 0x7FFFFFFF
SENT = 0x7FFF
GP = 0xFEDF8000
ABE_PER = NS.ABE_PER
N4F50 = NS.N4F50
CAL = dict(NS.CAL)
R71B = KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz"


def _cal_extra():
    """the gp-0x6803 == 2 fade arm records (lane_mirror_v295.load_cal's addresses, selector 7), read here from the image."""
    img = NS.V295.read_bytes()
    u16 = lambda a: struct.unpack_from("<H", img, a)[0]  # noqa: E731
    u32 = lambda a: struct.unpack_from("<I", img, a)[0]  # noqa: E731

    def rec(bank, n):
        p = u32(bank + 4 * 7)
        assert u16(p) == n
        return (np.array([u16(p + 2 + 2 * i) for i in range(n)], np.int64),
                np.array([u16(p + 2 + 2 * n + 2 * i) for i in range(n)], np.int64))
    return dict(fadeA2=rec(0xCBB54, 6), fadeB2=rec(0xCBAE4, 6), fadeA_chk=rec(0xCBC34, 6), fadeB_chk=rec(0xCBBC4, 6))


_X = _cal_extra()
CAL.update(fadeA2=_X["fadeA2"], fadeB2=_X["fadeB2"])
assert all((a == b).all() for a, b in zip(_X["fadeB_chk"], CAL["fadeB"]))


# =====================================================================================================================
# THE FRAME: gp-0x6a00 = C(gp-0x69ca) (correction LERP 0xC6892 / 0xC68A2, read by angle_signal_mirror.Cal)
# =====================================================================================================================
class Frame:
    def __init__(self):
        c = AM.Cal("v295")
        k = 1159 * 900 / (8 * 256 * 16384)                    # 0.1-deg counts of gp-0x69ca per motor count
        lin = np.array([x * 512 / 45 * k / 10.0 for x in c.X])  # |phi| knots, deg (69ca frame)
        cor = np.array(c.Y, float) / 10.0                     # correction, deg (odd-symmetric LERP, clamped)
        self.phi = np.linspace(0.0, 450.0, 90001)
        self.th = self.phi + np.interp(self.phi, lin, cor)
        dcor = np.gradient(np.interp(self.phi, lin, cor), self.phi)
        self.kap = 1.0 + dcor
        assert np.all(np.diff(self.th) > 0)
        self.knots = (lin, cor)

    def cinv(self, th):
        th = np.asarray(th, float)
        return np.sign(th) * np.interp(np.abs(th), self.th, self.phi)

    def kappa(self, th):
        th = np.asarray(th, float)
        return np.interp(np.abs(th), self.th, self.kap)


FRAME = Frame()


# =====================================================================================================================
# CANDIDATES (every number from the candidate's own listing / hex; see the .md for the source of each)
# =====================================================================================================================
def _hex(p):
    p = Path(p)
    return bytes.fromhex(p.read_text().replace("\n", " "))


P2HEX = AL / "c2" / "rev2A" / "c2_cave_P2.hex"
F2HEX = AL / "c2" / "rev2A" / "c2_cave_F2.hex"
D2AHEX = AL / "panel" / "D-structure" / "ds_cave_D2a.hex"
B0RHEX = AL / "panel" / "D-structure" / "ds_cave_B0r.hex"
E2D = HERE / "E2-integral-most-margin"
GD = HERE / "G-d-operand-and-margins"
E1_ICL_SCHED = ((714, 5120), (1843, 5120), (2304, 3840), (2707, 3584), (3571, 6144), (4032, 6144), (6198, 3072),
                (0xFFFF, 3072))                              # e1_policies.ICL_SCHED (the designer's E1b rows)


def rows_of(p):
    return tuple(NC.parse_table(_hex(p))[1])


@dataclass
class Cand:
    id: str
    fam: str
    rows: tuple
    dop: str = "fresh"            # fresh (gp-0x6abe guarded, r26 -> OPH) | held (E5: -Kd * gp-0x6a56) | box10
    kd: int = 34
    kp: int = 112
    ki: int = 56
    icl: int = 4096
    icl_rows: tuple = None        # E1-sched only (designer's walk e1_lane._icl_walk)
    thr: int = 512                # the cave's hard freeze on |gp-0x4f68|
    ramp_frz: bool = True         # freeze while (ramp & 0x8000) == 0
    reset_firm: int = None        # E1: in the FRZ path, |tq| > reset_firm -> st.w r0,-0x6dd0[gp]
    eb_lo: int = None             # E1 bleed: in the non-freeze path, |tq| > eb_lo -> I8 -= I8 >> eb_sh (listed bytes)
    eb_sh: int = 3
    sgn_thr: int = 0              # E2-S: |hand| > sgn_thr and sign(gp-0x4f60) != sign(E') -> freeze
    leak_s: int = 0               # E2-L: |tq| > leak_thr -> r6 = -(I8 >> leak_s), jr 0x29D7E
    leak_thr: int = 512
    arb: tuple = None             # E2-A*: (sh, sh_lo, vth, B, vcap, cap)
    hb_sh: int = 0                # H: |tq| > thr -> I8 -= I8 >> hb_sh AND freeze
    fb69: bool = False            # H-A: feedback = gp-0x69ca (fresh 1 kHz motor-linear angle)
    fade2: bool = False           # gp-0x6803 == 2 fade arm
    ramp_in: int = 33             # 0xC63F8 (stock arm) | 0xC63FC 328 (6803 == 2)
    ramp_out: int = 16            # 0xC63F6 | 0xC63FA 66
    fork: str = "ff"              # ff | k0 (fork angle integral tau 1 s) | fold (H-A: setpoint pre-divided, 69ca frame)
    hexsrc: object = None         # Path | ('rows', base hex, rows) | ('e1', ...) | None (no listing: mirror only)
    cave_B: str = ""
    note: str = ""


ARB_A2 = (6, 4, 2880, 1250, -1, 0)
ARB_A3 = (6, 4, 2880, 1250, 1382, 4096)


def candidates():
    P2R, F2R, D2R, B0R = rows_of(P2HEX), rows_of(F2HEX), rows_of(D2AHEX), rows_of(B0RHEX)
    gj = json.loads((GD / "g_impls_frozen.json").read_text())
    gr = {k: tuple(tuple(r) for r in v["rows"]) for k, v in gj.items()}
    C = []
    a = C.append
    # ---- round 1 (references)
    a(Cand("P2", "R1", P2R, "fresh", 34, hexsrc=P2HEX, cave_B="156", note="rev2-A primary"))
    a(Cand("F2", "R1", F2R, "held", 20, hexsrc=F2HEX, cave_B="138", note="rev2-A fallback"))
    a(Cand("D2a", "R1", D2R, "fresh", 34, hexsrc=D2AHEX, cave_B="162", note="rev2-B primary"))
    a(Cand("B0r", "R1", B0R, "held", 20, hexsrc=B0RHEX, cave_B="144", note="rev2-B fallback"))
    # ---- E1 (P2 skeleton)
    a(Cand("E1-reset", "E1", P2R, icl=8192, reset_firm=1536, hexsrc=("e1", 512), cave_B="168", note="E1 PRIMARY"))
    a(Cand("E1-cal", "E1", P2R, icl=8192, hexsrc=P2HEX, cave_B="156", note="E1 fewest-bytes floor"))
    a(Cand("E1-bleed", "E1", P2R, icl=8192, reset_firm=1536, eb_lo=256, eb_sh=3, cave_B="190",
           note="E1 rejected; bleed = listed bytes I8 -= I8>>3 (no hex)"))
    a(Cand("E1-freeze", "E1", P2R, icl=8192, reset_firm=1536, thr=320, hexsrc=("e1", 320), cave_B="168",
           note="E1 dominated"))
    a(Cand("E1-sched", "E1", P2R, icl_rows=E1_ICL_SCHED, reset_firm=1536, cave_B="~200",
           note="E1 rejected; ICL(v) = the designer's walk (no hex)"))
    a(Cand("E1-splitP", "E1", P2R, kp=200, icl=3072, reset_firm=1536, hexsrc=("e1", 512), cave_B="168",
           note="E1 rejected"))
    # ---- E2 (P2 skeleton)
    a(Cand("E2-R1", "E2", P2R, icl=8192, hexsrc=E2D / "e2_cave_P2.hex", cave_B="156"))
    a(Cand("E2-S", "E2", P2R, icl=8192, sgn_thr=300, hexsrc=E2D / "e2_cave_S300.hex", cave_B="172"))
    a(Cand("E2-A2", "E2", P2R, icl=8192, arb=ARB_A2, hexsrc=E2D / "e2_cave_A2.hex", cave_B="204"))
    a(Cand("E2-A3", "E2", P2R, icl=8192, arb=ARB_A3, hexsrc=E2D / "e2_cave_A3.hex", cave_B="222"))
    a(Cand("E2-A3-12k", "E2", P2R, icl=12288, arb=ARB_A3, hexsrc=E2D / "e2_cave_A3.hex", cave_B="222"))
    a(Cand("E2-A2-X", "E2", P2R, icl=8192, arb=ARB_A2, fade2=True, ramp_in=328, ramp_out=66,
           hexsrc=E2D / "e2_cave_A2.hex", cave_B="204", note="fork sends gp-0x6803 == 2"))
    a(Cand("E2-L", "E2", P2R, icl=8192, leak_s=13, leak_thr=512, hexsrc=E2D / "e2_cave_L13.hex", cave_B="168"))
    a(Cand("E2-K0", "E2", P2R, ki=0, icl=10240, thr=1 << 20, ramp_frz=False, fork="k0",
           hexsrc=E2D / "e2_cave_K0.hex", cave_B="132", note="fork angle integral tau 1 s (fork code)"))
    # ---- G
    for gid, dop, kd, ki in (("G-P48d", "fresh", 48, 56), ("G-P44d", "fresh", 44, 56), ("G-P48", "fresh", 48, 56),
                             ("G-P44", "fresh", 44, 56), ("G-F24", "held", 24, 56), ("G-F24d", "held", 24, 56),
                             ("G-A22", "box10", 22, 56), ("G-A22d", "box10", 22, 56), ("G-P48L", "fresh", 48, 56),
                             ("G-P48k40", "fresh", 48, 40)):
        hp = GD / f"g_cave_{gid}.hex"
        if hp.exists():
            rows, hs = rows_of(hp), hp
            assert rows == gr[gid], (gid, rows, gr[gid])
        else:
            rows, hs = gr[gid], ("rows", GD / "g_cave_G-P48.hex", gr[gid])
        a(Cand(gid, "G", rows, dop, kd, ki=ki, hexsrc=hs,
               cave_B={"fresh": "156", "held": "138", "box10": "210"}[dop]))
    # ---- H (no assembled listing: BELIEF, mirror only)
    a(Cand("H-A", "H", D2R, "fresh", 34, icl=7500, hb_sh=7, fb69=True, fork="fold", cave_B="~190",
           note="fb gp-0x69ca fresh; perfect fork SR fold (BELIEF); D2a table"))
    a(Cand("H-B", "H", B0R, "held", 23, icl=7500, hb_sh=7, cave_B="~164", note="held D Kd 23; B0r table"))
    return C


CANDS = candidates()
CBYID = {c.id: c for c in CANDS}


# =====================================================================================================================
# THE LANE (vectorised over columns; every column carries its own candidate)
# =====================================================================================================================
_GLUT = {}


def glut(rows):
    key = tuple(rows)
    if key not in _GLUT:
        _GLUT[key] = np.array([NC.walk_G(list(rows), v) for v in range(0, 12001)], np.int64)
    return _GLUT[key]


def icl_walk(rows, v):
    """e1_lane._icl_walk (the designer's E1-sched mirror), verbatim."""
    v = int(v) & 0xFFFF
    if v <= rows[0][0]:
        return rows[0][1]
    i = 0
    while i + 1 < len(rows) and v > rows[i + 1][0]:
        i += 1
    if i + 1 >= len(rows):
        return rows[-1][1]
    X0, Y0 = rows[i]
    X1, Y1 = rows[i + 1]
    if X1 == 0xFFFF:
        return Y0
    return Y0 + ((Y1 - Y0) * (v - X0)) // (X1 - X0)


class CandLane:
    """nl_sim.Lane's arithmetic (0x28F4C..0x2A20C, C2 in-place set) with every candidate's cave as a column switch."""

    def __init__(self, cands, vw):
        B = self.B = len(cands)
        vw = np.clip(np.asarray(vw, np.int64), 0, 12000)
        self.vw = vw
        A = lambda f: np.array([f(c) for c in cands], np.int64)  # noqa: E731
        Bo = lambda f: np.array([bool(f(c)) for c in cands])      # noqa: E731
        self.G = np.array([glut(c.rows)[s] for c, s in zip(cands, vw)], np.int64)
        self.dop = A(lambda c: {"fresh": 0, "held": 1, "box10": 2}[c.dop])
        self.kd, self.kp, self.ki = A(lambda c: c.kd), A(lambda c: c.kp), A(lambda c: c.ki)
        self.icl = np.array([icl_walk(c.icl_rows, s) if c.icl_rows else c.icl for c, s in zip(cands, vw)], np.int64)
        self.thr = A(lambda c: c.thr)
        self.ramp_frz = Bo(lambda c: c.ramp_frz)
        self.reset = A(lambda c: c.reset_firm if c.reset_firm is not None else 1 << 30)
        self.eb_lo = A(lambda c: c.eb_lo if c.eb_lo is not None else 1 << 30)
        self.eb_sh = A(lambda c: c.eb_sh)
        self.sgn = A(lambda c: c.sgn_thr)
        self.leak_s = A(lambda c: c.leak_s)
        self.leak_thr = A(lambda c: c.leak_thr)
        self.arb_on = Bo(lambda c: c.arb is not None)
        ar = [c.arb if c.arb is not None else (0, -1, 0, 0, -1, 0) for c in cands]
        self.arb_sh, self.arb_sh_lo, self.arb_vth, self.arb_B, self.arb_vcap, self.arb_cap = (
            np.array([r[i] for r in ar], np.int64) for i in range(6))
        self.hb_sh = A(lambda c: c.hb_sh)
        self.fb69 = Bo(lambda c: c.fb69)
        self.fade2 = Bo(lambda c: c.fade2)
        self.DB, self.DCL = 0, 10240
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.olag, self.Tprev = z(), z(), z(), z(), z()
        self.Eprev = np.full(B, SENT32, np.int64)
        self.bxC, self.bxW = z(), z()
        self.wraps = 0
        self.n_frz = z()
        self.n_run = z()
        self.log = {}
        c = CAL
        self.fA1 = lerp_vec(*c["fadeA"], np.zeros(B, np.int64))
        self.fA2 = lerp_vec(*c["fadeA2"], np.zeros(B, np.int64))

    # ---------------------------------------------------------------- the cave stage (h1 tests THIS against the bytes)
    def cave_stage(self, sp, r26, ramp, a6a00, abe, tq, I8, Eprev, bxC, bxW):
        """returns dict(Ep = r16 out, leak, frz (exit 0x29D7E), r6 (e5 at the 0x29D7E exit), op = r26 out (fresh/box10),
        I8c = gp-0x6dd0 after the cave, bxC/bxW = gp-0x6c44/-0x6c40 after the cave, wraps)."""
        E = s32((sp << 2) - r26)                                       # displaced shl 2 ; sub r26,r16
        prod = E * self.G
        wr = int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8                                            # mul ; sar 8
        atq = np.minimum(np.abs(tq), 0xFFFF)                           # gp-0x4f68 = |gp-0x4f60| saturated
        # ---- the ordered integral-policy decision (E2Lane's order; P2's hard test first)
        lk_on = self.leak_s > 0
        c1 = atq > np.where(lk_on, self.leak_thr, self.thr)
        hs = s16(tq)                                                   # signed hand word gp-0x4f60
        c2 = (self.sgn > 0) & (np.abs(hs) > self.sgn) & ((hs ^ Ep) < 0)
        I_S = I8 >> 10
        t = np.where(Ep >= 0, I_S, -I_S)
        th6 = s16(a6a00)
        sh = np.where((self.arb_sh_lo >= 0) & ((self.vw & 0xFFFF) <= self.arb_vth), self.arb_sh_lo, self.arb_sh)
        bound = s32((np.abs(th6) << np.where(self.arb_on, sh, 0)) + self.arb_B)
        capon = (self.arb_vcap >= 0) & ((self.vw & 0xFFFF) <= self.arb_vcap)
        bound = np.where(capon & (bound > self.arb_cap), self.arb_cap, bound)
        c3 = self.arb_on & (t >= bound)
        c4 = self.ramp_frz & ((np.asarray(ramp, np.int64) & 0x8000) == 0)
        leak = c1 & lk_on
        frz = (c1 & ~lk_on) | (~c1 & c2) | (~c1 & ~c2 & (c3 | c4))
        # ---- RAM side effects on gp-0x6dd0 (the lane's own I8, read next at 0x29DA4)
        I8c = I8
        I8c = np.where(frz & (atq > self.reset), 0, I8c)                                       # E1 firm reset
        I8c = np.where(~frz & ~leak & (atq > self.eb_lo), s32(I8c - (I8c >> self.eb_sh)), I8c)  # E1 light bleed
        I8c = np.where((self.hb_sh > 0) & c1 & ~lk_on, s32(I8c - (I8c >> self.hb_sh)), I8c)     # H bleed (+ freeze)
        r6 = np.where(leak, s32(-(I8 >> np.where(lk_on, self.leak_s, 31))), 0)
        # ---- the D operand left in r26
        ab = s16(abe)
        abv = ((ab + 13000) & 0xFFFFFFFF) <= 26000
        op_f = np.where(abv, ab, 0)
        first = Eprev == SENT32
        Cc = np.where(first, th6, bxC)
        W = np.where(first, 0, bxW)
        chg = Cc != th6
        Wc = s32(s32((Cc - th6) << 8) + 10)
        Wd = s32(W - 1)
        Wd = np.where((Wd & 0xFF) == 0, 0, Wd)
        Wn = np.where(chg, Wc, np.where((W & 0xFF) != 0, Wd, W))
        op_b = s32((Wn >> 8) << 6)
        op = np.where(self.dop == 0, op_f, np.where(self.dop == 2, op_b, r26))
        return dict(Ep=Ep, leak=leak, frz=frz, r6=r6, op=op, I8c=I8c, bxC=np.where(self.dop == 2, th6, bxC),
                    bxW=np.where(self.dop == 2, Wn, bxW), wraps=wr)

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        c = CAL
        B = self.B
        ramp = np.broadcast_to(np.asarray(ramp, np.int64), (B,))
        act = np.broadcast_to(np.asarray(act, np.int64), (B,))
        req = np.broadcast_to(np.asarray(req, np.int64), (B,))
        tq = np.broadcast_to(np.asarray(tq, np.int64), (B,))
        # ---- fb filter 0x28F4C..0x28FBE (E1: x := gp-0x6a00 | H-A: x := gp-0x69ca ; E2 add ; a 0 b 8192 C 65535)
        x = np.where(self.fb69, s16(x69), s16(a6a00))
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((0 * s_old >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                         # A2 + B2 (bVar2 assumed true)
        sp = s16(cmd)                                                  # E4 ld.h -0x69ae[gp],r16
        # ---- THE CAVE
        cv = self.cave_stage(sp, r26, ramp, a6a00, abe, tq, self.I8, self.Eprev, self.bxC, self.bxW)
        self.wraps += cv["wraps"]
        Ep, frz, leak = cv["Ep"], cv["frz"], cv["leak"]
        # ---- Honda's I 0x29D7A..0x29DC2 (normal: e5 = E' >> 5 ; 0x29D7E exit: e5 = r6) ; DB 0
        e5 = np.where(frz | leak, cv["r6"], Ep >> 5)
        DB = self.DB
        exc = np.where(e5 > DB, e5 - DB, np.where(e5 < -DB, e5 + DB, 0))
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        acc = (cv["I8c"] >> 3) + (s32(exc * self.ki) >> 3)
        self.wraps += int(np.count_nonzero(s32(acc) != acc))
        I = np.clip(s32(acc), -icl, icl)
        I8n = s32(I << 3)
        # ---- P 0x29E34..0x29E5C
        P = np.clip(s32(Ep * self.kp) >> 8, -c["PCL"], c["PCL"])
        # ---- D 0x29EDE..0x29F06: OPH (mov r26,r8 ; zxh Kd) | E5 (subr r0,r7 ; ld.h -0x6a56,r8)
        Dop = s32(self.kd * cv["op"]) >> 3
        Dhe = s32(-self.kd * s16(xheld)) >> 3
        D = np.clip(np.where(self.dop == 1, Dhe, Dop), -self.DCL, self.DCL)
        # ---- sum, fade, sum clamp
        S = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fA = np.where(self.fade2, self.fA2, self.fA1)
        fB = np.where(self.fade2, lerp_vec(*c["fadeB2"], i682f), lerp_vec(*c["fadeB"], i682f))
        f = ((fA * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        self.Eprev = np.where(run, Ep, SENT32)                         # 0x2A18C st.w r16,-0x6cf8 (sentinel on skips)
        self.bxC = np.where(run, cv["bxC"], self.bxC)
        self.bxW = np.where(run, cv["bxW"], self.bxW)
        self.n_run += run
        self.n_frz += run & (frz | leak)
        # ---- output lag 0x2A174..0x2A1B0
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t1 + t2)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        # ---- sign-hold gate 0x2A198..0x2A1E4
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & blk, 0, yr)
        k = pol * c["fwd"]
        r11 = s32(yr * k) >> 15
        T = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), frz=frz | leak, run=run)
        return s16(T)


# =====================================================================================================================
# THE RUNNER (nl_sim.run, extended; with frame='unity', no road noise, no per-column fork, it IS nl_sim.run)
# =====================================================================================================================
@dataclass
class Scn:
    dur: float
    ref: object                      # f(t) -> (B,) deg, the fork's planned angle (gp-0x6a00 frame)
    tq: object = None                # f(t, th, om) -> (B,) SIGNED torque word gp-0x4f60
    hand: object = None              # f(t) -> None | (Kh (B,), Bh (B,), th_h (B,))
    uext: object = None              # f(t) -> (B,) external wheel torque (T counts, + left)
    events: tuple = ()               # ((t, kind), ...) kind in fault | dis | engage | stop
    mode0: str = "engaged"
    th0: object = None
    sp_hold_from: float = None
    sp_meas_until: float = None
    road: float = 0.0                # road noise, T counts rms, 0.5-30 Hz (independent generator, seed 5)
    rec_I: bool = False


class Plant(NS.Plant):
    _cache = {}

    def __init__(self, cols):
        P = []
        for c in cols:
            key = (c["member"], float(c["v"]))
            if key not in Plant._cache:
                Plant._cache[key] = NS.params(c["member"], c["v"])
            P.append(Plant._cache[key])
        P = np.array(P, float)
        self.J, self.b, self.k, self.sat, self.Fc, self.Fs = (P[:, i] for i in range(6))
        self.tau = P[:, 6].astype(int)
        B = len(cols)
        self.th = np.zeros(B)
        self.om = np.zeros(B)
        self.buf = np.zeros((int(self.tau.max()) + 1, B))
        self.n = 0


def _road(B, n, rms, seed=5):
    from scipy import signal
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 1.0, (n + 2000, B))
    sos = signal.butter(2, [0.5, 30.0], "bandpass", fs=1000.0, output="sos")
    y = signal.sosfilt(sos, w, axis=0)[2000:]
    return (y / y.std(0, keepdims=True) * rms).astype(np.float32)


def run(cols, scn: Scn, frame="vgr", seed=11, noise=None):
    """cols: list of dict(cand=Cand, member, v, ...).  Returns th, om (1 kHz float32), T (int16), sp (int16 cmd),
    wire (100 Hz 0x14A angle counts), I (int16, if rec_I), frz duty, wraps."""
    B = len(cols)
    cands = [c["cand"] for c in cols]
    vw = np.array([int(round(c["v"] * 3.6 * 64)) for c in cols], np.int64)
    lane = CandLane(cands, vw)
    pl = Plant(cols)
    if scn.th0 is not None:
        pl.th = np.asarray(scn.th0, float).copy()
    rng = np.random.default_rng(seed)
    noise = N4F50 if noise is None else noise
    nT = int(round(scn.dur * 1000))
    th_r = np.zeros((nT, B), np.float32)
    om_r = np.zeros((nT, B), np.float32)
    T_r = np.zeros((nT, B), np.int16)
    sp_r = np.zeros((nT, B), np.int16)
    I_r = np.zeros((nT, B), np.int16) if scn.rec_I else None
    wire = []
    vgr = frame == "vgr"
    fold = np.array([c.fork == "fold" for c in cands]) & vgr
    k0 = np.array([c.fork == "k0" for c in cands])
    rin = np.array([c.ramp_in for c in cands], np.int64)
    rout = np.array([c.ramp_out for c in cands], np.int64)
    k0acc = np.zeros(B)
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    mode = scn.mode0
    ramp = np.full(B, 0x8000 if mode == "engaged" else 0, np.int64)
    act = req = 1 if mode == "engaged" else 0
    ev = sorted(scn.events)
    ei = 0
    sen = stopped = False
    road = _road(B, nT, scn.road) if scn.road > 0 else None
    tqv = np.zeros(B, np.int64)
    plan_r = np.zeros((nT // 10 + 1, B), np.float32)              # the fork's PLANNED angle (gp-0x6a00 frame), 100 Hz
    plan_now = pl.th.copy()
    for n in range(nT):
        t = n * 1e-3
        while ei < len(ev) and t >= ev[ei][0] - 1e-9:
            kind = ev[ei][1]
            if kind == "fault":
                sen, mode = True, "fault"
            elif kind == "stop":
                stopped = True
            elif kind == "dis":
                mode = "dis"
            elif kind in ("relatch", "engage"):
                mode = "relatch"
            ei += 1
        if mode == "engaged":
            ramp[:] = 0x8000
            act, req = 1, 1
        elif mode in ("fault", "dis"):
            ramp = np.maximum(0, ramp - rout)
            act, req = 0, (0xFF if mode == "fault" else 0)
        elif mode == "relatch":
            ramp = np.minimum(0x8000, ramp + rin)
            act, req = 1, 1
        elif mode == "off":
            ramp = np.maximum(0, ramp - 16)
            act, req = 0, 0
        if n % 10 == 0 and not sen and not stopped:
            k6 = max(len(wire) - 6, 0)
            th_meas = wire[k6] / 10.0 if wire else pl.th.copy()
            if mode in ("dis", "off") or (scn.sp_meas_until is not None and t < scn.sp_meas_until):
                plan_now = th_meas * np.ones(B)
                thc = np.where(fold, FRAME.cinv(th_meas), th_meas)
                cmd = np.clip(-(s16(-np.floor(10.0 * thc + 0.5).astype(np.int64)) << 2), -0x4000, 0x4000)
            elif scn.sp_hold_from is not None and t >= scn.sp_hold_from:
                pass
            else:
                plan = np.asarray(scn.ref(t), float) * np.ones(B)
                plan_now = plan
                if k0.any():                                           # E2-K0: fork angle integral (E2's ForkInt)
                    fr = np.abs(tqv) * 125.0 / 128.0 <= 1200.0
                    k0acc = np.where(k0 & fr, k0acc + (plan - th_meas) * 0.01 / 1.0, k0acc)
                thc = np.where(k0, plan + k0acc, plan)
                thc = np.where(fold, FRAME.cinv(thc), thc)
                raw = s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))
                cmd = np.clip(s32(-(raw << 2)), -0x4000, 0x4000)
        cmd_in = np.full(B, SENT, np.int64) if sen else cmd
        tqv = np.zeros(B, np.int64) if scn.tq is None else np.round(
            np.asarray(scn.tq(t, pl.th, pl.om), float) * np.ones(B)).astype(np.int64)
        om_m = pl.om / FRAME.kappa(pl.th) if vgr else pl.om            # MOTOR-frame rate
        g4f50 = s16(np.round(ABE_PER * om_m + rng.normal(0.0, noise, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = s16(st >> 10)
        x69 = np.floor(10.0 * (FRAME.cinv(pl.th) if vgr else pl.th) + 0.5).astype(np.int64)
        T = lane.tick(held_th, x69, held_x, abe, cmd_in, tqv, ramp, act, req)
        q_now = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
        if n % 10 == 4:
            held_th = q_now
            held_x = np.clip(-((s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
            wire.append(q_now.copy())
        Tapp = pl.delay(T.astype(float))
        u = -Tapp
        if scn.uext is not None:
            u = u + np.asarray(scn.uext(t), float)
        if road is not None:
            u = u + road[n]
        hh = scn.hand(t) if scn.hand is not None else None
        if hh is None:
            pl.step(u)
        else:
            pl.step(u, *hh)
        th_r[n], om_r[n], T_r[n], sp_r[n] = pl.th, pl.om, T, cmd_in
        if n % 10 == 0:
            plan_r[n // 10] = plan_now
        if I_r is not None:
            I_r[n] = lane.log["I"]
    return dict(th=th_r, om=om_r, T=T_r, sp=sp_r, I=I_r, wire=np.array(wire), wraps=lane.wraps, plan=plan_r,
                frz_duty=lane.n_frz / np.maximum(lane.n_run, 1))


# =====================================================================================================================
# SCENARIOS (per-column arrays; amplitudes = the refuter's A_TURN, log-interpolated; Ah = 0.5 A)
# =====================================================================================================================
SPEEDS = tuple(sorted(set([3.0, 3.1, 5.0, 11.9, 26.9] + [round(8.0 + 0.25 * i, 2) for i in range(89)])))
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
ALATS = (1.0, 1.5, 2.0, 2.5)
_AT = {3.0: 90.0, 5.0: 50.0, 8.0: 30.0, 12.5: 12.0, 19.0: 5.0, 26.0: 3.0, 30.0: 2.5}
_AK = sorted(_AT)
L_WB, SR_C = 2.83, 16.0
SIN = {"s03_02": (0.3, 0.2), "s03_05": (0.3, 0.5), "s10_02": (1.0, 0.2), "s10_05": (1.0, 0.5)}
OVW = {"ov_lt400": 400.0, "ov_lt511": 511.0, "ov_lt1000": 1000.0, "ov_fm2400": 2400.0,
       "ov3_lt400": 400.0, "ov3_lt511": 511.0, "ov3_fm2400": 2400.0}   # ov3_* = the refuter's / E2's 3 s hold (bridge)
SCENS = ("rr", "rrq", "th", "s03_02", "s03_05", "s10_02", "s10_05", "st", "c30", "rn30", "ov_lt400", "ov_lt511",
         "ov_lt1000", "ov_fm2400", "eng", "cs", "tmo", "tmos", "sen", "dis", "db", "hard")
DUR = {"rr": 40.0, "rrq": 40.0, "th": 11.0, "s03_02": 20.0, "s03_05": 8.0, "s10_02": 20.0, "s10_05": 8.0, "st": 7.0,
       "c30": 31.5, "rn30": 31.5, "ov_lt400": 7.3, "ov_lt511": 7.3, "ov_lt1000": 7.3, "ov_fm2400": 7.3, "eng": 7.0,
       "cs": 9.0, "tmo": 5.5, "tmos": 7.5, "sen": 5.5, "dis": 5.5, "db": 13.0, "hard": 8.0,
       "ov3_lt400": 9.3, "ov3_lt511": 9.3, "ov3_fm2400": 9.3}


def A_turn(v):
    return float(np.exp(np.interp(v, _AK, [np.log(_AT[k]) for k in _AK])))


def tgt_alat(v, a):
    return float(np.degrees(a * L_WB * SR_C / v ** 2))


def load_at(member, v, A):
    J, b, k, sat, Fc, Fs, tau = NS.params(member, v)
    return k * sat * np.tanh(A / sat)


_R71B = None
BANDS_R = ((8.0, 15.0, "8-15"), (15.0, 22.0, "15-22"), (22.0, 99.0, ">22"))


def r71b_runs():
    """nl_realref.runs() form (engaged, steeringPressed false, runs >= 15 s per goal band) + the run's own torque word
    (carState torque x 128/125 = gp-0x4f60, E2's sign evidence) at 100 Hz."""
    global _R71B
    if _R71B is None:
        d = np.load(R71B)
        t, v, sa, sp, stq = d["t_cst"], d["vego"], d["sa_deg"], d["spress"], d["storque"]
        act = np.interp(t, d["t_cs"], d["cs_active"]) > 0.5
        fs = 1 / np.median(np.diff(t))
        out = []
        for lo, hi, nm in BANDS_R:
            m = act & (v >= lo) & (v < hi) & (sp < 0.5)
            e = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
            for a, b in zip(e[::2], e[1::2]):
                if b - a >= 15 * fs:
                    tr = t[a:b] - t[a]
                    fr = np.arange(0, tr[-1], 0.01)
                    out.append(dict(band=nm, v=float(np.median(v[a:b])), dur=float(tr[-1]),
                                    ref=np.interp(fr, tr, sa[a:b]), tq=np.interp(fr, tr, stq[a:b] * 128.0 / 125.0)))
        _R71B = out
    return _R71B


def columns(name, member, cands):
    if name in ("rr", "rrq"):
        R = r71b_runs()
        return [dict(cand=c, member=member, v=R[i]["v"], run=i) for i in range(len(R)) for c in cands]
    if name == "th":
        cols = []
        for v in SPEEDS:
            for a in (ALATS if v >= 8.0 else (0.0,)):
                for c in cands:
                    cols.append(dict(cand=c, member=member, v=v, alat=a))
        return cols
    return [dict(cand=c, member=member, v=v) for v in SPEEDS for c in cands]


def scenario(name, cols):
    B = len(cols)
    v = np.array([c["v"] for c in cols])
    A = np.array([A_turn(x) for x in v])
    Ah = 0.5 * A
    sg = np.sign(Ah)

    def hold_ref(t):
        return Ah * np.interp(t, [0, 0.5, 1.5, 999], [0, 0, 1, 1])
    if name in ("rr", "rrq"):
        R = r71b_runs()
        idx = [c["run"] for c in cols]
        nf = int(max(R[i]["dur"] for i in set(idx)) * 100) + 2
        REF = np.stack([np.pad(R[i]["ref"], (0, nf - len(R[i]["ref"])), mode="edge") for i in idx], 1)
        # torque word padded with ZEROS after a run ends (an 'edge' pad repeats the pressed word that ended the run
        # and freezes the I for the rest of the batch: harmless to every metric scored inside the run, but it
        # inflated the freeze-duty statistic of the first grid, which is therefore not reported)
        TQ = np.stack([np.pad(R[i]["tq"], (0, nf - len(R[i]["tq"])), mode="constant") for i in idx], 1)

        def ref(t):
            return REF[min(int(round(t * 100)), nf - 1)]
        tq = (lambda t, th, om: TQ[min(int(t * 100), nf - 1)]) if name == "rrq" else None
        dur = max(R[i]["dur"] for i in set(idx)) + 0.5
        return Scn(dur=dur, ref=ref, tq=tq, th0=REF[0].copy()), dict(idx=idx, lens=[len(R[i]["ref"]) for i in idx])
    if name == "th":
        tgt = np.array([tgt_alat(c["v"], c["alat"]) if c["alat"] > 0 else A_turn(c["v"]) for c in cols])
        return Scn(dur=11.0, ref=lambda t: tgt * np.interp(t, [0, 0.5, 2.0, 99], [0, 0, 1, 1])), dict(tgt=tgt)
    if name in SIN:
        amp, f = SIN[name]
        return Scn(dur=4.0 / f, ref=lambda t: amp * np.sin(2 * np.pi * f * t) * np.ones(B)), dict(f=f, t0=1.0 / f,
                                                                                                  amp=amp)
    if name == "st":
        return Scn(dur=7.0, ref=lambda t: np.where(t >= 0.5, Ah, 0.0 * Ah)), dict(t_step=0.5, step=Ah)
    if name in ("c30", "rn30"):
        return Scn(dur=31.5, ref=hold_ref, road=(15.0 if name == "rn30" else 0.0)), dict(Ah=Ah)
    if name in OVW:
        tg, tr, thold = 2.5, 0.3, (3.0 if name.startswith("ov3_") else 1.0)
        trel = tg + tr + thold
        w = OVW[name]

        def tq(t, th, om, w=w):
            if tg <= t < trel:
                return -sg * w * min(1.0, (t - tg) / tr)
            if trel <= t < trel + 0.03:
                return -sg * w * (1 - (t - trel) / 0.03)
            return 0.0 * sg

        def hand(t):
            if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
                return None
            fr = min(1.0, (t - tg) / tr)
            return (np.full(B, 2000.0), np.full(B, 30.0), Ah - fr * Ah)
        return Scn(dur=trel + 3.5, ref=hold_ref, tq=tq, hand=hand, rec_I=True), dict(t_rel=trel, Ah=Ah)
    if name == "eng":
        TE = 2.0
        th0 = Ah.copy()

        def hand(t):
            if t < TE + 0.3:
                return (np.full(B, 2000.0), np.full(B, 30.0), th0)
            fr = min(1.0, (t - TE - 0.3) / 0.2)
            if fr >= 1.0:
                return None
            return (np.full(B, 2000.0 * (1 - fr)), np.full(B, 30.0 * (1 - fr)), th0)
        return Scn(dur=TE + 5.0, ref=lambda t: 0 * A, hand=hand, events=((TE, "engage"),), mode0="off", th0=th0,
                   sp_meas_until=TE + 0.011, sp_hold_from=TE + 0.011), dict(t_eng=TE, th0=th0)
    if name == "cs":
        T1, T2 = 3.0, 5.0
        d = 0.5 * np.array([load_at(c["member"], c["v"], a) for c, a in zip(cols, Ah)]) * sg

        def uext(t):
            if T1 <= t < T2:
                return d * min(1.0, (t - T1) / 0.2)
            if T2 <= t < T2 + 0.05:
                return d * (1 - (t - T2) / 0.05)
            return 0.0 * d
        return Scn(dur=9.0, ref=hold_ref, uext=uext,
                   tq=lambda t, th, om: np.where((t >= T1) & (t < T2), 400.0 * sg, 0.0 * sg)), dict(t_push=T1, t_rel=T2)
    if name == "tmo":
        return Scn(dur=5.5, ref=hold_ref, events=((3.0, "stop"), (3.51, "fault"))), dict(t_stop=3.0, t_fault=3.51)
    if name == "tmos":
        return Scn(dur=7.5, ref=lambda t: 0.3 * A * np.sin(2 * np.pi * 0.2 * t),
                   events=((5.0, "stop"), (5.51, "fault"))), dict(t_stop=5.0, t_fault=5.51)
    if name == "sen":
        return Scn(dur=5.5, ref=hold_ref, events=((3.0, "fault"),)), dict(t_fault=3.0)
    if name == "dis":
        return Scn(dur=5.5, ref=hold_ref, events=((3.0, "dis"),)), dict(t_dis=3.0)
    if name == "db":
        return Scn(dur=13.0, ref=lambda t: np.clip(0.2 * (t - 1.0), 0, 2.0) * np.ones(B)), dict()
    if name == "hard":
        t1, t2 = 1.0, 3.3
        return Scn(dur=8.0, ref=lambda t: A * np.interp(t, [0, t1, t1 + 0.3, t2, t2 + 0.3, 99], [0, 0, 1, 1, 0, 0])), \
            dict(A=A)
    raise KeyError(name)


# =====================================================================================================================
# METRICS
# =====================================================================================================================
def _bp(x, lo, hi, fs=1000.0):
    from scipy import signal
    sos = signal.butter(2, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def _rev(om, thr=0.2):
    sg = np.sign(np.where(np.abs(om) > thr, om, 0.0))
    out = np.zeros(om.shape[1], int)
    for j in range(om.shape[1]):
        s_ = sg[:, j][sg[:, j] != 0]
        out[j] = int(np.count_nonzero(np.diff(s_) != 0)) if len(s_) > 1 else 0
    return out


def metrics(name, meta, r, cols):
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    n = th.shape[0]
    tt = np.arange(n) * 1e-3
    B = th.shape[1]
    plan = r["plan"].astype(float)                                   # 100 Hz, frame k at tick 10 k
    plan1k = np.repeat(plan, 10, axis=0)[:n]                          # ZOH of the plan at 1 kHz
    m = dict(wraps=np.full(B, r["wraps"], float), peakT=np.abs(T).max(0), frz_duty=r["frz_duty"].astype(float))
    idx = (np.arange(r["wire"].shape[0]) * 10 + 4).clip(0, n - 1)     # the 0x14A frames
    if name in ("rr", "rrq"):
        from scipy import signal
        sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
        th100 = th[::10]
        X, Y, holds, djn, djmax, dur = [], [], [], [], [], []
        for j in range(B):
            L = min(meta["lens"][j], th100.shape[0], plan.shape[0])
            x = signal.sosfiltfilt(sos, plan[:L, j])
            y = signal.sosfiltfilt(sos, th100[:L, j])
            X.append(x[400:].astype(np.float32))
            Y.append(y[400:].astype(np.float32))
            d = np.gradient(x) * 100.0
            msk = (np.abs(x) >= 3.0) & (np.abs(d) <= np.maximum(1.0, 0.05 * np.abs(x))) & (np.arange(L) >= 400)
            e = np.flatnonzero(np.diff(np.r_[0, msk.astype(int), 0]))
            hw = [(a, b) for a, b in zip(e[::2], e[1::2]) if b - a >= 150]
            holds.append([[float(y[a:b].mean() / x[a:b].mean()), float(x[a:b].mean())] for a, b in hw])
            ii = np.arange(400, L) * 10 + 4
            ii = ii[ii < n]
            ev, jm = NS.dwell_jump(om[ii, j:j + 1], th[ii, j:j + 1], plan1k[ii, j:j + 1])
            djn.append(int(ev[0])), djmax.append(float(jm[0])), dur.append(len(ii) / 100.0)
        Tb = _bp(T, 5.0, 30.0)
        m.update(XY=(X, Y), holds=holds, dj=np.array(djn, float), dj_max=np.array(djmax), dj_dur=np.array(dur),
                 T_hf=np.sqrt(np.mean(Tb[4000:] ** 2, 0)))
        return m
    if name == "th":
        w = (tt >= 9.0) & (tt < 11.0)
        m["hold"] = th[w].mean(0) / meta["tgt"]
        m["slips"] = NS.slips(th[tt >= 2.5], om[tt >= 2.5]).astype(float)
        m["ovs"] = np.max((th - meta["tgt"]) * np.sign(meta["tgt"]), 0)
        return m
    if name in SIN:
        f, t0 = meta["f"], meta["t0"]
        w = tt >= t0
        fw = idx * 1e-3 >= t0
        X = plan1k[idx][fw]
        Yw = r["wire"].astype(float)[fw] / 10.0
        xm = X - X.mean(0)
        m["gain"] = (xm * (Yw - Yw.mean(0))).sum(0) / np.maximum((xm ** 2).sum(0), 1e-12)
        s_ = np.sin(2 * np.pi * f * tt[w])[:, None]
        c_ = np.cos(2 * np.pi * f * tt[w])[:, None]
        ra, rb = 2 * np.mean(plan1k[w] * s_, 0), 2 * np.mean(plan1k[w] * c_, 0)
        ya, yb = 2 * np.mean(th[w] * s_, 0), 2 * np.mean(th[w] * c_, 0)
        m["fit_gain"] = np.hypot(ya, yb) / np.maximum(np.hypot(ra, rb), 1e-9)
        m["phase"] = np.degrees(np.angle((ya + 1j * yb) / (ra + 1j * rb)))
        ev, jm = NS.dwell_jump(om[idx][fw], th[idx][fw], plan1k[idx][fw])
        m["dj"], m["dj_max"] = ev.astype(float), jm
        mv = np.abs(np.gradient(plan1k[idx][fw], axis=0) * 100.0) > 0.05
        m["stick_pct"] = 100.0 * ((om[idx][fw] == 0.0) & mv).sum(0) / np.maximum(mv.sum(0), 1)
        m["T_hf"] = np.sqrt(np.mean(_bp(T, 5, 30)[w] ** 2, 0))
        return m
    if name == "st":
        A_ = meta["step"]
        w = tt >= 0.5
        band = np.maximum(0.05 * np.abs(A_), 0.2)
        bad = np.abs(th[w] - A_) > band
        last = np.where(bad.any(0), len(bad) - 1 - np.argmax(bad[::-1], axis=0), -1)
        m["settle"] = np.where(bad[-300:].any(0), 99.0, (last + 1) * 1e-3)
        m["ovs_pct"] = 100.0 * np.max((th[w] - A_) * np.sign(A_), 0) / np.abs(A_)
        wr = (tt >= 5.5) & (tt < 7.0)
        m["hold"] = (th[wr] / A_).mean(0)
        wl = tt >= 4.0
        m["slips"] = NS.slips(th[wl], om[wl]).astype(float)
        m["hunt_rev"] = _rev(om[wl]).astype(float)
        m["hunt_p2p"] = th[wl].max(0) - th[wl].min(0)
        m["T_hf"] = np.sqrt(np.mean(_bp(T, 5, 30)[(tt >= 2.0)] ** 2, 0))
        return m
    if name in ("c30", "rn30"):
        w = tt >= 11.5
        e = (plan1k - th)[w]
        m["e_mean"] = np.abs(e.mean(0))
        m["e_rms"] = e.std(0)
        m["hunt_rev"] = _rev(om[w]).astype(float)
        m["hunt_p2p"] = th[w].max(0) - th[w].min(0)
        m["slips"] = NS.slips(th[w], om[w]).astype(float)
        m["T_hf"] = np.sqrt(np.mean(_bp(T, 5, 30)[w] ** 2, 0))
        m["om_hf"] = np.sqrt(np.mean(_bp(om, 5, 30)[w] ** 2, 0))
        return m
    if name in OVW:
        trel = meta["t_rel"]
        Ah = meta["Ah"]
        w = tt >= trel
        i_r = int(trel * 1000)
        m["lurch"] = np.max((th[w] - Ah) * np.sign(Ah), 0)
        m["droop"] = np.max((Ah - th[tt >= trel + 1.0]) * np.sign(Ah), 0)
        m["swing"] = th[w].max(0) - th[w].min(0)
        m["th_rel"] = th[i_r - 1]
        m["I_rel"] = r["I"][i_r - 2].astype(float)
        return m
    if name == "eng":
        # NOTE: nl_lens.metrics('eng') labels these the other way round (its 'droop' = (th - sp) sg, the overshoot);
        # here droop = how far the wheel falls BEHIND the held command toward centre, ovs = past it.  Grid files
        # written before this fix carry the refuter's labels and are swapped back in load_grid (no 'eng_v2' key).
        w = tt >= meta["t_eng"]
        sgn = np.sign(meta["th0"])
        e = (plan1k - th)[w] * sgn
        m["droop"] = e.max(0)
        m["ovs"] = (-e).max(0)
        m["eng_v2"] = np.ones(B)
        return m
    if name == "cs":
        sgn = np.sign(plan1k[-1])
        w = tt >= meta["t_rel"]
        e = (plan1k - th)[w] * sgn
        m["droop"] = e.max(0)
        m["lurch"] = (-e).max(0)
        push = (tt >= meta["t_push"]) & (tt < meta["t_rel"])
        m["push_ovs"] = ((th - plan1k)[push] * sgn).max(0)
        m["slips"] = NS.slips(th[w], om[w]).astype(float)
        return m
    if name in ("tmo", "tmos"):
        i0 = int(meta["t_stop"] * 1000) - 1
        hold = (tt >= meta["t_stop"]) & (tt < meta["t_fault"])
        m["hold_dev"] = np.abs(th[hold] - th[i0]).max(0)
        m["exc"] = np.abs(th[tt >= meta["t_stop"]] - th[i0]).max(0)
        m["T_after"] = np.abs(T[tt >= meta["t_fault"] + 0.25]).max(0)
        m["T_peak_after"] = np.abs(T[tt >= meta["t_fault"]]).max(0)
        return m
    if name == "sen":
        i0 = int(meta["t_fault"] * 1000) - 1
        m["T_50ms"] = np.abs(T[tt >= meta["t_fault"] + 0.05]).max(0)
        m["T_peak_after"] = np.abs(T[tt >= meta["t_fault"]]).max(0)
        m["exc"] = np.abs(th[tt >= meta["t_fault"]] - th[i0]).max(0)
        return m
    if name == "dis":
        i0 = int(meta["t_dis"] * 1000) - 1
        m["exc"] = np.abs(th[tt >= meta["t_dis"]] - th[i0]).max(0)
        m["T_150ms"] = np.abs(T[tt >= meta["t_dis"] + 0.15]).max(0)
        return m
    if name == "db":
        w = tt >= 3.0
        m["lag"] = (plan1k - th)[w].max(0)
        m["slips"] = NS.slips(th[w], om[w]).astype(float)
        m["stuck_pct"] = 100.0 * (om[w] == 0.0).mean(0)
        return m
    if name == "hard":
        A_ = meta["A"]
        ref_om = np.gradient(plan1k, axis=0) * 1000.0
        h = _bp(om, 1.6, 3.0)[200:-200]
        hr = _bp(ref_om, 1.6, 3.0)[200:-200]
        m["hard16"] = np.sqrt(np.mean(h ** 2, 0))
        m["hard16_ref"] = np.sqrt(np.mean(hr ** 2, 0))
        m["hard_ratio"] = m["hard16"] / np.maximum(m["hard16_ref"], 1e-9)
        hw = (tt >= 1.3) & (tt < 3.3)
        m["ovs"] = np.max((th[hw] - A_) * np.sign(A_), 0)
        m["hold"] = (th[(tt >= 2.8) & (tt < 3.3)] / A_).mean(0)
        return m
    raise KeyError(name)


# =====================================================================================================================
# THE GRID (one batch per (scenario, member, column chunk); every column of a batch sees identical inputs)
# =====================================================================================================================
MAXCELL = 7_000_000                                                  # columns x ticks per job (memory bound)


def plan_jobs(scens, members, frame, cand_ids=None):
    cands = [c for c in CANDS if cand_ids is None or c.id in cand_ids]
    jobs = []
    for s in scens:
        for mb in members:
            cols = columns(s, mb, cands)
            nT = int((DUR[s] + 0.5) * 1000)
            per = max(len(cands), min(1600, MAXCELL // nT))
            per = max(len(cands), (per // len(cands)) * len(cands))
            for i in range(0, len(cols), per):
                jobs.append((s, mb, frame, i, per, tuple(c.id for c in cands)))
    return jobs


def job(args):
    s, mb, frame, i0, per, ids = args
    cands = [CBYID[k] for k in ids]
    cols = columns(s, mb, cands)[i0:i0 + per]
    scn, meta = scenario(s, cols)
    t0 = time.time()
    r = run(cols, scn, frame=frame)
    m = metrics(s, meta, r, cols)
    keys = [dict(id=c["cand"].id, v=c["v"], alat=c.get("alat"), run=c.get("run")) for c in cols]
    out = dict(scn=s, member=mb, frame=frame, keys=keys, sec=time.time() - t0)
    if s in ("rr", "rrq"):
        X, Y = m.pop("XY")
        out["X"] = [x.tolist() for x in X]
        out["Y"] = [y.tolist() for y in Y]
        out["holds"] = m.pop("holds")
    out["m"] = {k: np.asarray(x, float).tolist() for k, x in m.items()}
    return out


def run_grid(procs=10, frame="vgr", scens=SCENS, members=MEMBERS, tag=None, cand_ids=None):
    jobs = plan_jobs(scens, members, frame, cand_ids)
    jobs.sort(key=lambda j: -DUR[j[0]])
    tag = tag or frame
    t0 = time.time()
    res = []
    print(f"grid {tag}: {len(jobs)} jobs, {procs} procs", flush=True)
    with Pool(procs) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            if r["scn"] in ("rr", "rrq"):
                (OUT / f"grid_{tag}_{r['scn']}_{r['member'].replace('*', 'x')}_{i}.json").write_text(json.dumps(r))
            else:
                res.append(r)
            if (i + 1) % 10 == 0 or i + 1 == len(jobs):
                print(f"  {tag}: {i + 1}/{len(jobs)} jobs, {time.time() - t0:.0f} s", flush=True)
                (OUT / f"grid_{tag}.json").write_text(json.dumps(res))
    (OUT / f"grid_{tag}.json").write_text(json.dumps(res))
    print(f"grid {tag} done in {time.time() - t0:.0f} s", flush=True)


# =====================================================================================================================
# H1: every candidate's cave BYTES executed by the refuter's independent V850E2 interpreter (nl_cave.Cpu, extended here
# with the forms the panel-2 caves add) against CandLane.cave_stage -- the very function the time grid runs.
# =====================================================================================================================
class Cpu2(NC.Cpu):
    """nl_cave.Cpu + xor (Format I 0x09), subr (0x0C), add/cmp imm5 (Format II 0x12/0x13), ld.w (0x39, hw2 bit 0 = 1),
    st.h/st.w (0x3B, hw2 bit 0 = 0/1).  Field extraction written from the V850E2 ISA formats (as nl_cave's)."""

    def step(self, pc):
        hw = self.rd(pc, 2)
        reg2, op6, reg1 = hw >> 11, (hw >> 5) & 0x3F, hw & 0x1F
        r = self.r
        if (hw >> 7) & 0xF == 0xB or ((hw >> 6) & 0x1F == 0x1E and (op6 >> 1) == 0x1E):
            return super().step(pc)
        if op6 == 0x09:                                   # xor reg1,reg2
            res = (r[reg2] ^ r[reg1]) & NC.M32
            self.ov = 0
            self.z = int(res == 0)
            self.s = int(NC.s32(res) < 0)
            self.setr(reg2, res)
            return pc + 2
        if op6 == 0x0C:                                   # subr reg1,reg2 : reg2 = reg1 - reg2
            self.setr(reg2, self.flags_sub(r[reg1], r[reg2]))
            return pc + 2
        if op6 == 0x12:                                   # add imm5,reg2
            self.setr(reg2, self.flags_add(r[reg2], NC.sx(reg1, 5) & NC.M32))
            return pc + 2
        if op6 == 0x13:                                   # cmp imm5,reg2
            self.flags_sub(r[reg2], NC.sx(reg1, 5) & NC.M32)
            return pc + 2
        if op6 == 0x39:
            hw2 = self.rd(pc + 2, 2)
            if hw2 & 1:                                   # ld.w disp16[reg1],reg2
                a = (r[reg1] + NC.sx(hw2 & 0xFFFE, 16)) & NC.M32
                self.setr(reg2, self.rd(a, 4))
                return pc + 4
            return super().step(pc)
        if op6 == 0x3B:                                   # st.h / st.w reg2,disp16[reg1]
            hw2 = self.rd(pc + 2, 2)
            n = 4 if hw2 & 1 else 2
            a = (r[reg1] + NC.sx(hw2 & 0xFFFE, 16)) & NC.M32
            for i in range(n):
                self.mem[(a + i) & NC.M32] = (r[reg2] >> (8 * i)) & 0xFF
            self.trace.append((pc, "st"))
            return pc + 4
        return super().step(pc)


def e1_hex(thr):
    """E1-reset / E1-freeze bytes: P2's code with the listed 12-byte block (movea 1536,r0,r13 ; cmp r13,r8 ; bnh .noz ;
    st.w r0,-0x6dd0[gp]) inserted at P2's FRZ label 0xC4C6A, every displacement re-linked; the freeze immediate at
    0xC4C5C = movea thr.  Encodings: the designer's Ghidra-confirmed forms (20 6e 00 06 / ed 41 / 64 07 31 92); the
    re-linked branch/jump/table words are computed here (Format III / V / the 6-byte mov imm32)."""
    p2 = bytearray(_hex(P2HEX))
    code, tbl = p2[:0x72], p2[0x72:]
    assert code[0x5C:0x60] == bytes.fromhex("206e0002") and code[0x6A:0x70] == bytes.fromhex("0032b6071251")
    code[0x5C:0x60] = bytes([0x20, 0x6E]) + struct.pack("<H", thr)

    def b3(cond, disp):
        return struct.pack("<H", (((disp >> 4) & 0x1F) << 11) | (0xB << 7) | (((disp >> 1) & 7) << 4) | cond)
    blk = bytes.fromhex("206e0006") + bytes.fromhex("ed41") + b3(0x3, 6) + bytes.fromhex("64073192")
    new = bytearray(code[:0x6A]) + blk + bytearray(code[0x6A:])
    base = 0xC4C00
    jr_at = 0x6C + 12
    disp = (0x29D7E - (base + jr_at)) & 0x3FFFFF
    new[jr_at:jr_at + 2] = struct.pack("<H", (0x1E << 6) | ((disp >> 16) & 0x3F))
    new[jr_at + 2:jr_at + 4] = struct.pack("<H", disp & 0xFFFF)
    new[0x68:0x6A] = b3(0xA, 0x7C - 0x68)                           # bne DONE (DONE moved to 0xC4C7C)
    assert new[0x1A:0x1C] == bytes.fromhex("2906")
    new[0x1C:0x20] = struct.pack("<I", base + len(new))               # mov imm32 -> the moved table
    return bytes(new + tbl)


def hexbytes(c):
    hs = c.hexsrc
    if hs is None:
        return None
    if isinstance(hs, tuple) and hs[0] == "e1":
        return e1_hex(hs[1])
    if isinstance(hs, tuple) and hs[0] == "rows":
        base = bytearray(_hex(hs[1]))
        taddr, _ = NC.parse_table(bytes(base))
        t = taddr - 0xC4C00
        for i, (X, G, S_) in enumerate(hs[2]):
            base[t + 6 * i:t + 6 * i + 6] = struct.pack("<HHh", X, G, S_)
        return bytes(base)
    return _hex(hs)


CELLS = {"6abe": (-0x6ABE, 2), "6a5e": (-0x6A5E, 2), "4f68": (-0x4F68, 2), "4f60": (-0x4F60, 2), "6a00": (-0x6A00, 2),
         "6dd0": (-0x6DD0, 4), "6cf8": (-0x6CF8, 4), "6c44": (-0x6C44, 4), "6c40": (-0x6C40, 4), "6a56": (-0x6A56, 2)}
SCRATCH = (6, 8, 9, 13, 16, 26)


def h1(c, N=6000, seed=7):
    code = hexbytes(c)
    if code is None:
        return dict(id=c.id, n=0, bad=None, note="no listing")
    rng = np.random.default_rng(seed)
    knots = [r[0] for r in c.rows if r[0] < 0xFFFF]
    cases = []
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 40 else 32767
        r26 = int(rng.integers(-65535, 65536))
        v = int(rng.integers(0, 12001)) if k % 5 else int(np.clip(rng.choice(knots + [1382, 2880]) + rng.integers(-1, 2),
                                                                      0, 12000))
        tq = int(rng.choice([int(rng.integers(-3000, 3001)), int(rng.choice([-1537, -1536, -513, -512, -301, -300, 0,
                                                                                256, 257, 300, 301, 320, 321, 511,
                                                                                512, 513, 1536, 1537, -32768,
                                                                                32767]))]))
        ramp = int(rng.choice([0x8000, 0x8000, int(rng.integers(0, 0x8000)), 0xFFFF]))
        th = int(rng.choice([int(rng.integers(-4000, 4001)), int(rng.integers(-40, 41))]))
        I8 = int(rng.choice([int(rng.integers(-12288 * 1024, 12288 * 1024)), int(rng.integers(-2 ** 20, 2 ** 20)), 0]))
        abe = int(rng.choice([int(rng.integers(-32768, 32768)), 0x7FFF, 13000, 13001, -13000, -13001,
                              int(rng.integers(-500, 501))]))
        Ep6 = int(rng.choice([SENT32, int(rng.integers(-800000, 800000))]))
        C6 = th + int(rng.choice([0, 0, int(rng.integers(-60, 61))]))
        W6 = int(rng.choice([0, int(s32(np.int64((int(rng.integers(-120, 121)) << 8) + int(rng.integers(0, 11)))))]))
        cases.append((sp, r26, v, tq, ramp, th, I8, abe, Ep6, C6, W6))
    a = np.array(cases, np.int64)
    lane = CandLane([c] * N, a[:, 2])
    cv = lane.cave_stage(s16(a[:, 0]), a[:, 1], a[:, 4], a[:, 5], a[:, 7], s16(a[:, 3]), a[:, 6], a[:, 8], a[:, 9],
                         a[:, 10])
    bad = 0
    first_bad = None
    for i, (sp, r26, v, tq, ramp, th, I8, abe, Ep6, C6, W6) in enumerate(cases):
        ram = {(GP + off) & NC.M32: (val & ((1 << (8 * w)) - 1), w) for nm, (off, w) in CELLS.items()
               for val in [dict(abe=abe, v=v, a4f68=min(abs(tq), 0xFFFF), tq=tq, th=th, I8=I8, Ep6=Ep6, C6=C6,
                                W6=W6, x=0)[{"6abe": "abe", "6a5e": "v", "4f68": "a4f68", "4f60": "tq", "6a00": "th",
                                             "6dd0": "I8", "6cf8": "Ep6", "6c44": "C6", "6c40": "W6",
                                             "6a56": "x"}[nm]]]}
        regs = {16: sp, 26: r26, 14: ramp}
        junk = {k: int(rng.integers(0, 2 ** 32)) for k in range(1, 32) if k not in (4, 6, 14, 16, 26)}
        regs.update(junk)
        mem = {}
        for j, b in enumerate(code):
            mem[0xC4C00 + j] = b
        for ad, (val, w) in ram.items():
            for q in range(w):
                mem[(ad + q) & NC.M32] = (val >> (8 * q)) & 0xFF
        cpu = Cpu2(mem)
        for k_, v_ in regs.items():
            cpu.r[k_] = v_ & NC.M32
        cpu.r[4] = GP
        cpu.r[6] = NC.HOOK_RET
        pc = 0xC4C00
        for _ in range(600):
            if not (0xC4C00 <= pc < 0xC4C00 + len(code)):
                break
            pc = cpu.step(pc)
        rdw = lambda off, w: int.from_bytes(bytes(cpu.mem[(GP + off + q) & NC.M32] for q in range(w)), "little")  # noqa
        frz = bool(cv["frz"][i] | cv["leak"][i])
        ok = (NC.s32(cpu.r[16]) == int(cv["Ep"][i])
              and pc == (NC.FRZ_RET if frz else NC.HOOK_RET)
              and (not frz or NC.s32(cpu.r[6]) == int(cv["r6"][i]))
              and NC.s32(cpu.r[26]) == int(cv["op"][i])
              and NC.s32(rdw(-0x6DD0, 4)) == int(cv["I8c"][i])
              and NC.s32(rdw(-0x6C44, 4)) == int(cv["bxC"][i])
              and NC.s32(rdw(-0x6C40, 4)) == int(cv["bxW"][i])
              and all(cpu.r[k_] == (regs[k_] & NC.M32) for k_ in regs if k_ not in SCRATCH)
              and cpu.r[4] == GP)
        for nm in ("6abe", "6a5e", "4f68", "4f60", "6a00", "6cf8", "6a56"):
            off, w = CELLS[nm]
            ok = ok and rdw(off, w) == ram[(GP + off) & NC.M32][0]
        if not ok:
            bad += 1
            if first_bad is None:
                first_bad = dict(case=cases[i], cpu_r16=NC.s32(cpu.r[16]), Ep=int(cv["Ep"][i]), pc=hex(pc),
                                 frz=frz, r6=NC.s32(cpu.r[6]), cv_r6=int(cv["r6"][i]), r26=NC.s32(cpu.r[26]),
                                 op=int(cv["op"][i]), I8=NC.s32(rdw(-0x6DD0, 4)), I8c=int(cv["I8c"][i]))
    return dict(id=c.id, n=N, bad=bad, first_bad=first_bad, code_B=len(code))


def h1_all(N=6000):
    lines = ["# H1: cave BYTES executed by nl_cave.Cpu (+ Cpu2 forms) vs CandLane.cave_stage (the time grid's own cave)",
             f"# {N} cases per candidate: random + edges (validity +-13000/13001 and 0x7FFF, |tq| at every threshold "
             "+-1, signed hand words, ramp 0/partial/0x8000/0xFFFF, table knots +-1, 1382/2880 speed knees, Honda's "
             "first-tick sentinel, box10 RAM states); checks r16 = E', the exit (0x29D7A / 0x29D7E), r6 at the "
             "0x29D7E exit, r26 out, gp-0x6dd0 / -0x6c44 / -0x6c40 after, every other RAM cell and every non-scratch "
             "register unchanged"]
    allok = True
    for c in CANDS:
        r = h1(c, N=N)
        if r["bad"] is None:
            lines.append(f"{c.id:10s}  NO LISTING (mirror only: {c.note})")
            continue
        allok &= r["bad"] == 0
        lines.append(f"{c.id:10s}  bytes {r['code_B']:4d}  mismatches {r['bad']} / {r['n']}"
                     + (f"   FIRST {r['first_bad']}" if r["bad"] else ""))
        print(lines[-1], flush=True)
    lines.append("ALL HEX-BACKED CANDIDATES: " + ("0 mismatches" if allok else "MISMATCHES (see above)"))
    (TXT / "h1_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return allok


# =====================================================================================================================
# VALIDATION (V1 the refuter's own engine control; V2 CandLane+run == nl_sim; V3 == each designer's own lane; V4 the
# headline numbers of the refuter and the designers re-derived on this pipeline -- read from the unity grid by report)
# =====================================================================================================================
def _torque_program(Ah_sign=1.0):
    """a signed hand-word program that walks every policy threshold (freeze 512 / 320, reset 1536, bleed 256, opposing
    300, aiding) while an external torque holds the wheel back (so the angle-referenced bound binds)."""
    knots = [(0.0, 0), (2.0, -700), (3.0, -2000), (3.5, -400), (4.5, 400), (5.5, -280), (6.0, 0)]

    def tq(t):
        w = 0
        for a, val in knots:
            if t >= a:
                w = val
        return float(w) * Ah_sign
    return tq


def validate():
    import subprocess
    lines = ["# score_time.py validate -- controls of the panel-2 common time scorer (2026-10-01)"]

    def P(s):
        print(s, flush=True)
        lines.append(s)
    # ---- V1: the refuter's control (nl_sim vs rev2-A's score_time engine), re-run as is
    P("\n## V1 the refuter's own control, re-run unchanged: refute_c2r2_nonlinear/ctl_vs_designers.py "
      "(nl_sim vs c2/rev2A/score_time.run, sensor noise 0)")
    pr = subprocess.run([sys.executable, str(RC2 / "ctl_vs_designers.py")], capture_output=True, text=True, cwd=str(RC2))
    for ln in (pr.stdout + pr.stderr).strip().splitlines()[-8:]:
        P("  " + ln)
    # ---- V2: CandLane + run (frame unity) == nl_sim.run, bit for bit, noise ON (same seed)
    import nl_lens as LN
    P("\n## V2 this scorer (CandLane + run, frame 'unity') vs nl_sim.run on the refuter's own lens scenarios, "
      "P2 / F2 / D2a / B0r x 5 speeds, sensor noise ON (same seed)")
    for nm, mem in (("rh", "nominal"), ("ov_lt511", "b_lo*J_hi"), ("ov_firm", "bc"), ("eng", "bc"), ("tmos", "F_hi"),
                    ("mic05", "bc"), ("sen", "nominal")):
        colsN = [dict(impl=i, member=mem, v=v, age=0) for v in (3.1, 8.0, 11.75, 17.0, 26.9)
                 for i in ("P2", "F2", "D2a", "B0r")]
        scn, meta = LN.scenario(nm, colsN)
        rN = NS.run(colsN, scn)
        colsM = [dict(cand=CBYID[c["impl"]], member=mem, v=c["v"]) for c in colsN]
        rM = run(colsM, Scn(**{k: getattr(scn, k) for k in scn.__dataclass_fields__}), frame="unity")
        P(f"  {nm:9s} {mem:10s} max|dtheta| {np.abs(rN['th'] - rM['th']).max():.3e} deg  max|dT| "
          f"{np.abs(rN['T'].astype(int) - rM['T'].astype(int)).max()} counts")
    # ---- V3a: E1's own lane (e1_lane.E1Lane, a subclass of nl_sim.Lane) through nl_sim.run
    sys.path.insert(0, str(HERE / "E1-integral-fewest-bytes"))
    import e1_lane as E1L
    import e1_policies as E1P
    P("\n## V3a designer E1's own lane (e1_lane.E1Lane through nl_sim.run) vs this scorer, same columns, noise ON")
    pmap = {"E1-reset": E1P.POLICIES["E1a"], "E1-cal": E1P.POLICIES["E1a_noreset"],
            "E1-freeze": E1P.POLICIES["E1a_fz320"], "E1-sched": E1P.POLICIES["E1b"], "E1-splitP": E1P.POLICIES["E1c"],
            "E1-bleed": E1L.Policy("E1-bleed", icl_flat=8192, reset_firm=1536, bleed_lo=256, bleed_sh=3, kp=112)}
    orig = NS.Lane
    for nm, mem in (("rh", "nominal"), ("ov_lt400", "b_lo*J_hi"), ("ov_firm", "bc"), ("eng", "nominal")):
        ids = list(pmap)
        colsN = [dict(impl="P2", member=mem, v=v, age=0) for v in (8.0, 11.75, 17.0, 26.9) for _ in ids]
        pols = [pmap[k] for v in (8.0, 11.75, 17.0, 26.9) for k in ids]
        scn, meta = LN.scenario(nm, colsN)
        NS.Lane = lambda impls, vw, pols=pols: E1L.E1Lane(impls, vw, pols)  # noqa: E731
        try:
            rN = NS.run(colsN, scn)
        finally:
            NS.Lane = orig
        colsM = [dict(cand=CBYID[k], member=mem, v=v) for v in (8.0, 11.75, 17.0, 26.9) for k in ids]
        rM = run(colsM, Scn(**{k: getattr(scn, k) for k in scn.__dataclass_fields__}), frame="unity")
        dth = np.abs(rN["th"] - rM["th"]).max(0)
        dT = np.abs(rN["T"].astype(int) - rM["T"].astype(int)).max(0)
        per = {k: (float(dth[[i for i, kk in enumerate(ids * 4) if kk == k]].max()),
                   int(dT[[i for i, kk in enumerate(ids * 4) if kk == k]].max())) for k in ids}
        P(f"  {nm:9s} {mem:10s} " + "  ".join(f"{k} {a:.1e}/{b}" for k, (a, b) in per.items()))
    # ---- V3b / V3c: E2's E2Lane and G's GLane (DSLane subclasses) through rev2-A's engine, noise 0 in both
    sys.path.insert(0, str(HERE / "E2-integral-most-margin"))
    sys.path.insert(0, str(HERE / "G-d-operand-and-margins"))
    import e2_common as E2C
    import e2_exp as E2X
    import e2_lane as E2L
    import g_lane as GLN
    import ds_selftest as DST
    import ds_model as DMm
    import ds_time as DTm
    ST = E2C.ST
    DTm.N4F50 = 0.0
    e2cfg = {"E2-R1": dict(icl=8192), "E2-S": dict(icl=8192, sgn_thr=300),
             "E2-A2": dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250),
             "E2-A3": dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096),
             "E2-L": dict(icl=8192, leak_s=13, leak_thr=512),
             "E2-A2-X": dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, fade2=True)}
    gj = json.loads((GD / "g_impls_frozen.json").read_text())

    def gcfg(gid):
        im = gj[gid]
        rows = [tuple(r) for r in im["rows"]]
        if im["dkind"] == "fresh":
            cfg = DST.lane_cfg(DMm.Des(dsrc="op", dop="fresh_rate", kd=im["kd"]), rows)
        elif im["dkind"] == "held":
            cfg = DST.lane_cfg(DMm.Des(dsrc="rate_held", kd=im["kd"]), rows)
        else:
            cfg = dict(kind="angle", tbl=rows, kp=112, ki=int(im.get("ki", 56)), kd=int(im["kd"]), db=0, icl=4096,
                       dcl=10240, thr=512, dsrc="op", dop="box10", bx_sh=int(im.get("sh", 6)))
        cfg["ki"] = int(im.get("ki", 56))
        return cfg

    def stscn(kind, v):
        A = A_turn(v)
        Ah = 0.5 * A
        ref = lambda t: float(np.interp(t, [0, 0.5, 1.5, 99], [0, 0, Ah, Ah]))  # noqa: E731
        if kind == "prog":
            tqf = _torque_program()
            load = load_at("nominal", v, Ah)
            ue = lambda t: -0.6 * load if 2.0 <= t < 5.5 else 0.0  # noqa: E731
            d = dict(name="prog", v=v, dur=9.0, ref=lambda t: ref(float(t)), events=[], hand=None, c63f6=16,
                     inactive="meas", outer="ff", tq=lambda t: tqf(float(t)), u_ext=ue)
            mine = Scn(dur=9.0, ref=lambda t: ref(t), tq=lambda t, th, om: tqf(t), uext=ue)
        elif kind == "s02":
            d = dict(name="s02x", v=v, dur=15.0, ref=lambda t: 0.3 * A * float(np.sin(2 * np.pi * 0.2 * float(t))),
                     events=[], hand=None, c63f6=16, inactive="meas", outer="ff", tq=None)
            mine = Scn(dur=15.0, ref=lambda t: 0.3 * A * np.sin(2 * np.pi * 0.2 * t))
        else:                                                     # held turn, fork stops at 3.0, sentinel at 3.51
            d = dict(name="tmo", v=v, dur=5.5, ref=lambda t: ref(float(t)), events=[(3.51, "fault")], hand=None,
                     c63f6=16, inactive="meas", outer="ff", tq=None, t_stop=3.0)
            mine = Scn(dur=5.5, ref=lambda t: ref(t), events=((3.0, "stop"), (3.51, "fault")))
        return d, mine
    for fam, lane_cls, idmap in (("E2", E2L.E2Lane, {k: E2X.col(**kw) for k, kw in e2cfg.items()}),
                                 ("G", GLN.GLane, {k: gcfg(k) for k in ("G-P48", "G-P44d", "G-F24", "G-A22",
                                                                         "G-A22d", "G-P48k40")})):
        P(f"\n## V3{'b' if fam == 'E2' else 'c'} designer {fam}'s own lane ({lane_cls.__name__} through c2/rev2A/"
          f"score_time.run, the engine both designers scored on) vs this scorer, sensor noise 0 in both")
        for kind in ("prog", "s02", "tmo"):
            for v in (8.0, 11.75, 17.0, 26.9):
                d, mine = stscn(kind, v)
                ids = list(idmap)
                rD = ST.run(d, [idmap[k] for k in ids], [], "nominal", v, lane_cls=lane_cls)
                colsM = [dict(cand=CBYID[k], member="nominal", v=v) for k in ids]
                rM = run(colsM, mine, frame="unity", noise=0.0)
                dth = np.abs(rD["th"] - rM["th"]).max(0)
                dT = np.abs(rD["T"].astype(int) - rM["T"].astype(int)).max(0)
                P(f"  {kind:5s} v {v:5.2f}: " + "  ".join(f"{k} {a:.1e}/{b}" for k, a, b in zip(ids, dth, dT)))
    DTm.N4F50 = N4F50
    out = "\n".join(lines) + "\n"
    (TXT / "validate_out.txt").write_text(out, encoding="utf-8")
    return out


# =====================================================================================================================
# REPORT: aggregate the grid into per-candidate x band tables (worst over members and speeds), the goal-criteria fails
# =====================================================================================================================
SBANDS = (("<8", 0.0, 7.99), ("8-10", 8.0, 10.0), ("10-12.5", 10.01, 12.5), ("12.5-15", 12.51, 15.0),
          ("15-22", 15.01, 22.0), (">22", 22.01, 30.0))
DBAND = {"8-10": "8-15", "10-12.5": "8-15", "12.5-15": "8-15", "15-22": "15-22", ">22": ">22"}
LURCH_BAR = 8.0                                                       # rev2-B's pre-registered light/firm lurch bar
HF_LINE = 2.0                                                         # harness_time HF_LINE (T 5-30 Hz rms, counts)


def load_grid(tag):
    res = json.loads((OUT / f"grid_{tag}.json").read_text())
    for p in sorted(OUT.glob(f"grid_{tag}_rr*_*.json")):
        res.append(json.loads(p.read_text()))
    D = {}
    for r in res:
        k = (r["scn"], r["member"])
        d = D.setdefault(k, dict(id=[], v=[], alat=[], run=[], m={}, X=[], Y=[], holds=[]))
        d["id"] += [q["id"] for q in r["keys"]]
        d["v"] += [q["v"] for q in r["keys"]]
        d["alat"] += [q["alat"] for q in r["keys"]]
        d["run"] += [q["run"] for q in r["keys"]]
        mm = dict(r["m"])
        if r["scn"] == "eng" and "eng_v2" not in mm:               # pre-fix files: the refuter's swapped labels
            mm["droop"], mm["ovs"] = mm["ovs"], mm["droop"]
        for mk, mv in mm.items():
            d["m"].setdefault(mk, []).extend(mv)
        if "X" in r:
            d["X"] += r["X"]
            d["Y"] += r["Y"]
            d["holds"] += r["holds"]
    for d in D.values():
        d["id"] = np.array(d["id"])
        d["v"] = np.array(d["v"], float)
        d["m"] = {k: np.array(v, float) for k, v in d["m"].items()}
    return D


def _sel(d, cid, lo, hi, alat=None):
    s = (d["id"] == cid) & (d["v"] >= lo) & (d["v"] <= hi)
    if alat is not None:
        s &= np.array([a is not None and a > 0 and a <= alat + 1e-9 for a in d["alat"]])
    return s


def agg(D, scn, metric, cid, lo, hi, how="max", members=MEMBERS, alat=None):
    vals = []
    for mb in members:
        d = D.get((scn, mb))
        if d is None or metric not in d["m"]:
            continue
        s = _sel(d, cid, lo, hi, alat)
        if s.any():
            x = d["m"][metric][s]
            x = x[np.isfinite(x)]
            if len(x):
                vals.append({"max": x.max, "min": x.min, "sum": x.sum}[how]())
    if not vals:
        return np.nan
    return {"max": max, "min": min, "sum": sum}[how](vals)


def r71b_scores(D, scn):
    """goal tracking slope per (cand, data band, member) from the concatenated LPF paths; real-curve holds; dj."""
    R = r71b_runs()
    out = {}
    for mb in MEMBERS:
        d = D.get((scn, mb))
        if d is None:
            continue
        for cid in [c.id for c in CANDS]:
            for band in ("8-15", "15-22", ">22"):
                ii = [i for i, (k, rn) in enumerate(zip(d["id"], d["run"])) if k == cid and R[rn]["band"] == band]
                if not ii:
                    continue
                X = np.concatenate([np.asarray(d["X"][i]) for i in ii])
                Y = np.concatenate([np.asarray(d["Y"][i]) for i in ii])
                b = np.linalg.lstsq(np.vstack([X, np.ones_like(X)]).T, Y, rcond=None)[0][0]
                hold = [h[0] for i in ii for h in d["holds"][i]]
                dj = float(sum(d["m"]["dj"][i] for i in ii))
                djm = float(max(d["m"]["dj_max"][i] for i in ii))
                dur = float(sum(d["m"]["dj_dur"][i] for i in ii))
                out[(cid, band, mb)] = dict(slope=float(b), hold=(min(hold) if hold else np.nan),
                                            nhold=len(hold), dj=dj, djmax=djm, dur=dur,
                                            frz=float(np.mean([d["m"]["frz_duty"][i] for i in ii])),
                                            thf=float(max(d["m"]["T_hf"][i] for i in ii)))
    return out


def worst(rs, cid, band, key, how="min", members=MEMBERS):
    v = [rs[(cid, band, mb)][key] for mb in members if (cid, band, mb) in rs]
    v = [x for x in v if np.isfinite(x)]
    if not v:
        return np.nan
    return {"min": min, "max": max, "sum": sum}[how](v)


def worst_dev(rs, cid, band, members=MEMBERS):
    v = [rs[(cid, band, mb)]["slope"] for mb in members if (cid, band, mb) in rs]
    return max(v, key=lambda s: abs(s - 1.0)) if v else np.nan


def f(x, n=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "-"
    return f"{x:.{n}f}"


def summarize(tag="vgr"):
    D = load_grid(tag)
    rr = r71b_scores(D, "rr") if ("rr", "nominal") in D else {}
    rq = r71b_scores(D, "rrq") if ("rrq", "nominal") in D else {}
    S = {}
    for c in CANDS:
        cid = c.id
        row = dict(id=cid, fam=c.fam, cave=c.cave_B)
        for band in ("8-15", "15-22", ">22"):
            row[f"trk_{band}"] = worst_dev(rr, cid, band)
            row[f"trkq_{band}"] = worst_dev(rq, cid, band)
            row[f"rhold_{band}"] = worst(rr, cid, band, "hold")
            row[f"rdj_{band}"] = worst(rr, cid, band, "dj", "sum")
            row[f"rdjmax_{band}"] = worst(rr, cid, band, "djmax", "max")
            row[f"frzq_{band}"] = worst(rq, cid, band, "frz", "max")
        for nm, lo, hi in SBANDS:
            b = {}
            b["th20"] = agg(D, "th", "hold", cid, lo, hi, "min", alat=2.0) if lo >= 8 else \
                agg(D, "th", "hold", cid, lo, hi, "min")
            b["th25"] = agg(D, "th", "hold", cid, lo, hi, "min", alat=2.5) if lo >= 8 else np.nan
            b["th_slips"] = agg(D, "th", "slips", cid, lo, hi, "sum")
            for sn in SIN:
                b[f"g_{sn}"] = agg(D, sn, "gain", cid, lo, hi, "min")
                b[f"dj_{sn}"] = agg(D, sn, "dj", cid, lo, hi, "sum")
                b[f"djm_{sn}"] = agg(D, sn, "dj_max", cid, lo, hi, "max")
                b[f"stk_{sn}"] = agg(D, sn, "stick_pct", cid, lo, hi, "max")
                b[f"thf_{sn}"] = agg(D, sn, "T_hf", cid, lo, hi, "max")
            b["dj"] = np.nansum([b[f"dj_{sn}"] for sn in SIN])
            b["djmax"] = np.nanmax([b[f"djm_{sn}"] for sn in SIN])
            b["dj10"] = np.nansum([b["dj_s10_02"], b["dj_s10_05"]])
            b["dj10max"] = np.nanmax([b["djm_s10_02"], b["djm_s10_05"]])
            b["dj03"] = np.nansum([b["dj_s03_02"], b["dj_s03_05"]])
            b["dj03max"] = np.nanmax([b["djm_s03_02"], b["djm_s03_05"]])
            b["st_settle"] = agg(D, "st", "settle", cid, lo, hi, "max")
            b["st_ovs"] = agg(D, "st", "ovs_pct", cid, lo, hi, "max")
            b["st_hold"] = agg(D, "st", "hold", cid, lo, hi, "min")
            b["st_slips"] = agg(D, "st", "slips", cid, lo, hi, "sum")
            b["c30_rev"] = agg(D, "c30", "hunt_rev", cid, lo, hi, "max")
            b["c30_p2p"] = agg(D, "c30", "hunt_p2p", cid, lo, hi, "max")
            b["c30_slips"] = agg(D, "c30", "slips", cid, lo, hi, "sum")
            b["c30_thf"] = agg(D, "c30", "T_hf", cid, lo, hi, "max")
            b["c30_e"] = agg(D, "c30", "e_mean", cid, lo, hi, "max")
            hunt = 0
            for mb in MEMBERS:
                d = D.get(("c30", mb))
                if d is None:
                    continue
                s = _sel(d, cid, lo, hi)
                hunt += int(np.sum((d["m"]["hunt_rev"][s] >= 2) & (d["m"]["hunt_p2p"][s] >= 0.2)))
            b["hunt_n"] = hunt
            b["rn_thf"] = agg(D, "rn30", "T_hf", cid, lo, hi, "max")
            b["rn_omhf"] = agg(D, "rn30", "om_hf", cid, lo, hi, "max")
            b["rn_erms"] = agg(D, "rn30", "e_rms", cid, lo, hi, "max")
            b["rn_slips"] = agg(D, "rn30", "slips", cid, lo, hi, "sum")
            b["lurch_light"] = np.nanmax([agg(D, s_, "lurch", cid, lo, hi, "max") for s_ in
                                          ("ov_lt400", "ov_lt511", "ov_lt1000")])
            b["lurch_400"] = agg(D, "ov_lt400", "lurch", cid, lo, hi, "max")
            b["lurch_511"] = agg(D, "ov_lt511", "lurch", cid, lo, hi, "max")
            b["lurch_1000"] = agg(D, "ov_lt1000", "lurch", cid, lo, hi, "max")
            b["lurch_firm"] = agg(D, "ov_fm2400", "lurch", cid, lo, hi, "max")
            b["lurch_light_blj"] = np.nanmax([agg(D, s_, "lurch", cid, lo, hi, "max", members=("b_lo*J_hi",)) for s_
                                              in ("ov_lt400", "ov_lt511", "ov_lt1000")])
            b["lurch_firm_blj"] = agg(D, "ov_fm2400", "lurch", cid, lo, hi, "max", members=("b_lo*J_hi",))
            b["eng_droop"] = agg(D, "eng", "droop", cid, lo, hi, "max")
            b["eng_ovs"] = agg(D, "eng", "ovs", cid, lo, hi, "max")
            b["cs_droop"] = agg(D, "cs", "droop", cid, lo, hi, "max")
            b["cs_slips"] = agg(D, "cs", "slips", cid, lo, hi, "sum")
            b["tmo_dev"] = agg(D, "tmo", "hold_dev", cid, lo, hi, "max")
            b["tmos_dev"] = agg(D, "tmos", "hold_dev", cid, lo, hi, "max")
            b["tmo_Tafter"] = np.nanmax([agg(D, "tmo", "T_after", cid, lo, hi, "max"),
                                          agg(D, "tmos", "T_after", cid, lo, hi, "max")])
            b["tmo_Tpk"] = np.nanmax([agg(D, "tmo", "T_peak_after", cid, lo, hi, "max"),
                                       agg(D, "tmos", "T_peak_after", cid, lo, hi, "max")])
            b["sen_T50"] = agg(D, "sen", "T_50ms", cid, lo, hi, "max")
            b["sen_Tpk"] = agg(D, "sen", "T_peak_after", cid, lo, hi, "max")
            b["dis_T150"] = agg(D, "dis", "T_150ms", cid, lo, hi, "max")
            b["db_lag"] = agg(D, "db", "lag", cid, lo, hi, "max")
            b["db_slips"] = agg(D, "db", "slips", cid, lo, hi, "sum")
            b["hard"] = agg(D, "hard", "hard_ratio", cid, lo, hi, "max")
            b["hard_ovs"] = agg(D, "hard", "ovs", cid, lo, hi, "max")
            b["wraps"] = np.nanmax([agg(D, s_, "wraps", cid, lo, hi, "max") for s_ in SCENS if s_ not in ("rr", "rrq")]
                                    + [0.0])
            b["peakT"] = np.nanmax([agg(D, s_, "peakT", cid, lo, hi, "max") for s_ in SCENS if s_ not in ("rr", "rrq")])
            # ---- goal-criteria fails in this band (>= 8 m/s; < 8 m/s is outside the goal's tracking/hold bands)
            fails = []
            if lo >= 8:
                db_ = DBAND[nm]
                t = row[f"trk_{db_}"]
                if np.isfinite(t) and not (0.95 <= t <= 1.05):
                    fails.append(f"TRK {t:.3f}")
                tq_ = row[f"trkq_{db_}"]
                if np.isfinite(tq_) and not (0.95 <= tq_ <= 1.05):
                    fails.append(f"TRKq {tq_:.3f}")
                if b["th20"] < 0.90:
                    fails.append(f"HOLD {b['th20']:.3f}")
                rh_ = row[f"rhold_{db_}"]
                if np.isfinite(rh_) and rh_ < 0.90:
                    fails.append(f"RHOLD {rh_:.3f}")
                lm = np.nanmax([b["lurch_light"], b["lurch_firm"]])
                if lm > LURCH_BAR:
                    fails.append(f"LURCH {lm:.1f}")
                if b["hunt_n"] > 0:
                    fails.append(f"HUNT {b['hunt_n']}")
                if b["c30_thf"] > HF_LINE:
                    fails.append(f"TEX {b['c30_thf']:.2f}")
                if b["wraps"] > 0:
                    fails.append("WRAP")
            b["fails"] = fails
            row[nm] = b
        S[cid] = row
    return S


TRK_NOTE = ("tracking = the goal's metric: OLS slope (with intercept) of the 0.5 Hz zero-phase-LPF wheel angle on the "
            "LPF planned path, r71b's own engaged hands-not-pressed paths, runs concatenated per band, scored from 4 s; "
            "the cell shows the member whose slope is furthest from 1")


def tables(S, tag="vgr"):
    L = []
    P = L.append
    ids = [c.id for c in CANDS]
    P(f"## Main table ({tag} frame) -- worst over the four members; '>=8' = worst over every speed 8-30 m/s")
    P("")
    P("| cand | cave B | trk r71b 8-15 / 15-22 / >22 | trk replay 8-15 / 15-22 / >22 | real-curve hold min | "
      "turn-hold a<=2.0 min >=8 | a 2.5 min >=8 | in-phase gain +-1 deg 0.2 Hz min >=8 | dwell-jump +-1 deg >=8 "
      "(max snap) | dwell-jump +-0.3 deg >=8 (max snap) | light lurch max >=8 (b_lo*J_hi) | firm lurch max >=8 "
      "(b_lo*J_hi) | engage droop max >=8 | co-steer droop max >=8 |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    hi = [b for b in SBANDS if b[1] >= 8]
    for cid in ids:
        r = S[cid]
        mx = lambda k: np.nanmax([r[b[0]][k] for b in hi])  # noqa: E731
        mn = lambda k: np.nanmin([r[b[0]][k] for b in hi])  # noqa: E731
        dj10 = sum(r[b[0]]["dj10"] for b in hi)
        dj03 = sum(r[b[0]]["dj03"] for b in hi)
        rh = np.nanmin([r[f"rhold_{x}"] for x in ("8-15", "15-22", ">22")])
        P(f"| {cid} | {r['cave']} | {f(r['trk_8-15'], 3)} / {f(r['trk_15-22'], 3)} / {f(r['trk_>22'], 3)} | "
          f"{f(r['trkq_8-15'], 3)} / {f(r['trkq_15-22'], 3)} / {f(r['trkq_>22'], 3)} | {f(rh)} | {f(mn('th20'))} | "
          f"{f(mn('th25'))} | {f(mn('g_s10_02'))} | {int(dj10)} ({f(mx('dj10max'))}) | {int(dj03)} "
          f"({f(mx('dj03max'))}) | {f(mx('lurch_light'), 1)} "
          f"({f(mx('lurch_light_blj'), 1)}) | {f(mx('lurch_firm'), 1)} ({f(mx('lurch_firm_blj'), 1)}) | "
          f"{f(mx('eng_droop'), 1)} | {f(mx('cs_droop'), 1)} |")
    P("")
    P("## Goal-criteria fails per band (the goal's decidable time criteria; '<8' is outside the goal's bands)")
    P("TRK/TRKq = tracking outside 0.95-1.05 (clean / r71b's own torque word replayed; data band 8-15 serves 8-10, "
      "10-12.5 and 12.5-15); HOLD = synthetic turn-hold < 0.90 at a_lat <= 2.0; RHOLD = a real r71b curve held "
      "< 0.90; HUNT = a limit cycle (>= 2 reversals and >= 0.2 deg p2p in the last 20 s of a 30 s constant setpoint); "
      "TEX = T 5-30 Hz > 2.0 counts in that hold; LURCH = a light or firm release lurch > 8 deg (rev2-B's "
      "pre-registered bar; a time gate of the brief, not one of the goal's own criteria).  Dwell-then-jump is NOT in "
      "this table: the goal's criterion is relative to V282 (not simulable); its counts are in their own tables.")
    P("")
    P("| cand | " + " | ".join(b[0] for b in SBANDS) + " |")
    P("|---|" + "---|" * len(SBANDS))
    for cid in ids:
        P(f"| {cid} | " + " | ".join(("n/a" if b[1] < 8 else ("; ".join(S[cid][b[0]]["fails"]) or "pass"))
                                     for b in SBANDS) + " |")
    P("")

    def band_table(title, key, n=2, how=None):
        P(f"### {title}")
        P("")
        P("| cand | " + " | ".join(b[0] for b in SBANDS) + " |")
        P("|---|" + "---|" * len(SBANDS))
        for cid in ids:
            P(f"| {cid} | " + " | ".join(f(S[cid][b[0]][key], n) if isinstance(S[cid][b[0]][key], float) or
                                         isinstance(S[cid][b[0]][key], (int, np.floating, np.integer))
                                         else str(S[cid][b[0]][key]) for b in SBANDS) + " |")
        P("")
    P("## Per-band detail (worst over the four members and the band's speeds)")
    P("")
    band_table("Synthetic turn-hold, a_lat <= 2.0 m/s^2 (min hold ratio; < 8 m/s: the A_TURN hold)", "th20", 3)
    band_table("Synthetic turn-hold at a_lat 2.5 m/s^2 (r71b's sustained maximum at <= 18 m/s)", "th25", 3)
    band_table("In-phase wire gain, +-1 deg at 0.2 Hz (min)", "g_s10_02", 2)
    band_table("In-phase wire gain, +-0.3 deg at 0.2 Hz (min)", "g_s03_02", 2)
    band_table("In-phase wire gain, +-1 deg at 0.5 Hz (min)", "g_s10_05", 2)
    band_table("In-phase wire gain, +-0.3 deg at 0.5 Hz (min)", "g_s03_05", 2)
    band_table("Dwell-then-jump events, +-1 deg at 0.2 + 0.5 Hz, sum over members and speeds", "dj10", 0)
    band_table("Largest dwell-then-jump snap, +-1 deg sinusoids (deg)", "dj10max", 2)
    band_table("Dwell-then-jump events, +-0.3 deg at 0.2 + 0.5 Hz, sum over members and speeds", "dj03", 0)
    band_table("Largest dwell-then-jump snap, +-0.3 deg sinusoids (deg)", "dj03max", 2)
    band_table("Stuck while the setpoint moves, +-0.3 deg 0.2 Hz (max %)", "stk_s03_02", 0)
    band_table("Dead zone: creep lag, 0 -> 2 deg at 0.2 deg/s (max deg)", "db_lag", 2)
    band_table("Dead zone: slips during the creep (sum)", "db_slips", 0)
    band_table("Hunt: limit-cycle count in a 30 s constant setpoint (columns with >= 2 reversals and >= 0.2 deg)",
               "hunt_n", 0)
    band_table("30 s constant setpoint: mean |error| (max deg)", "c30_e", 3)
    band_table("Step-and-hold overshoot (max %)", "st_ovs", 1)
    band_table("Step-and-hold settle time to 5 % / 0.2 deg (max s; 99 = not settled)", "st_settle", 2)
    band_table("Release lurch, light hand (max over words 400 / 511 / 1000, deg)", "lurch_light", 1)
    band_table("Release lurch, light hand, b_lo*J_hi only (deg)", "lurch_light_blj", 1)
    band_table("Release lurch, firm hand 2400 (deg)", "lurch_firm", 1)
    band_table("Release lurch, firm hand 2400, b_lo*J_hi only (deg)", "lurch_firm_blj", 1)
    band_table("Engage under load with the measured angle sent: droop (max deg)", "eng_droop", 2)
    band_table("Co-steer release droop (max deg)", "cs_droop", 2)
    band_table("Texture: T 5-30 Hz rms under road noise 15 T counts (max counts)", "rn_thf", 2)
    band_table("Texture: wheel rate 5-30 Hz rms under road noise (max deg/s)", "rn_omhf", 2)
    band_table("Texture: T 5-30 Hz rms in the noise-free 30 s hold (max counts)", "c30_thf", 2)
    band_table("510 ms timeout mid-motion: wheel excursion during the hold (max deg)", "tmos_dev", 2)
    band_table("510 ms timeout in a held turn: excursion during the hold (max deg)", "tmo_dev", 2)
    band_table("Timeout / sentinel: peak |T| after the sentinel (max counts)", "tmo_Tpk", 0)
    band_table("0xE4 sentinel: |T| from 50 ms after (max counts)", "sen_T50", 0)
    band_table("Request drop: |T| from 150 ms after (max counts)", "dis_T150", 0)
    band_table("Hard turn: 1.6-3 Hz wheel-rate rms / the command's own (max)", "hard", 2)
    P("### r71b real paths: tracking slope per data band and member (clean | torque word replayed)")
    P("")
    return L


def r71b_detail(tag="vgr"):
    D = load_grid(tag)
    L = []
    for scn, lab in (("rr", "clean"), ("rrq", "r71b torque word replayed")):
        rs = r71b_scores(D, scn)
        L.append(f"#### {lab}")
        L.append("")
        L.append("| cand | " + " | ".join(f"{b} {m}" for b in ("8-15", "15-22", ">22") for m in
                                           ("nom", "bc", "F_hi", "blJ")) + " | real-curve hold min (n) | dj events "
                 "per 100 s (max snap) |")
        L.append("|---|" + "---|" * 14)
        for c in CANDS:
            cells = [f(rs.get((c.id, b, m), {}).get("slope", np.nan), 3) for b in ("8-15", "15-22", ">22")
                     for m in MEMBERS]
            hold = [rs[(c.id, b, m)]["hold"] for b in ("8-15", "15-22", ">22") for m in MEMBERS
                    if (c.id, b, m) in rs]
            nh = [rs[(c.id, b, m)]["nhold"] for b in ("8-15", "15-22", ">22") for m in MEMBERS[:1]
                  if (c.id, b, m) in rs]
            dj = sum(rs[(c.id, b, m)]["dj"] for b in ("8-15", "15-22", ">22") for m in MEMBERS if (c.id, b, m) in rs)
            dur = sum(rs[(c.id, b, m)]["dur"] for b in ("8-15", "15-22", ">22") for m in MEMBERS
                      if (c.id, b, m) in rs)
            djm = max([rs[(c.id, b, m)]["djmax"] for b in ("8-15", "15-22", ">22") for m in MEMBERS
                       if (c.id, b, m) in rs] + [0])
            frz = max([rs[(c.id, b, m)]["frz"] for b in ("8-15", "15-22", ">22") for m in MEMBERS
                       if (c.id, b, m) in rs] + [0])
            L.append(f"| {c.id} | " + " | ".join(cells) + f" | {f(np.nanmin(hold) if hold else np.nan, 3)} "
                     f"({sum(nh)}) | {f(100 * dj / max(dur, 1e-9), 2)} ({f(djm)}) |")
        L.append("")
    return L


def bridge_table():
    """the 3 s-hold override bridge (the refuter's / E2's hold length) in both frames: lurch max >= 8 m/s per member."""
    L = ["## Bridge: release lurch with the refuter's / E2's 3 s hold (ov3_*), max over 8-30 m/s, per member", "",
         "| cand | frame | word 400: nom / bc / F_hi / b_lo*J_hi | word 511: nom / bc / F_hi / b_lo*J_hi | "
         "firm 2400: nom / bc / F_hi / b_lo*J_hi |", "|---|---|---|---|---|"]
    for tag in ("vgr_ov3", "unity_ov3"):
        if not (OUT / f"grid_{tag}.json").exists():
            continue
        D = load_grid(tag)
        for c in CANDS:
            cells = []
            for sn in ("ov3_lt400", "ov3_lt511", "ov3_fm2400"):
                cells.append(" / ".join(f(agg(D, sn, "lurch", c.id, 8.0, 30.0, "max", members=(mb,)), 1)
                                        for mb in MEMBERS))
            L.append(f"| {c.id} | {tag.split('_')[0]} | " + " | ".join(cells) + " |")
    L.append("")
    return L


def report():
    out = []
    tags = [t for t in ("vgr", "unity") if (OUT / f"grid_{t}.json").exists()]
    summ = {}
    for t in tags:
        S = summarize(t)
        summ[t] = S
        out += tables(S, t)
        out += r71b_detail(t)
    if "unity" in summ and "vgr" in summ:
        out.append("## Frame attribution: 'vgr' (the measured gp-0x6a00 = C(gp-0x69ca) map) minus 'unity' (every "
                   "previous scorer's kappa = 1), >= 8 m/s worst cells")
        out.append("")
        out.append("| cand | trk 15-22 vgr / unity | turn-hold a<=2 vgr / unity | gain +-1 0.2 Hz vgr / unity | "
                   "dj events vgr / unity | light lurch vgr / unity | firm lurch vgr / unity |")
        out.append("|---|---|---|---|---|---|---|")
        hi = [b[0] for b in SBANDS if b[1] >= 8]
        for c in CANDS:
            a, u = summ["vgr"][c.id], summ["unity"][c.id]
            g = lambda S_, k, fn: fn([S_[b][k] for b in hi])  # noqa: E731
            out.append(f"| {c.id} | {f(a['trk_15-22'], 3)} / {f(u['trk_15-22'], 3)} | "
                       f"{f(g(a, 'th20', np.nanmin))} / {f(g(u, 'th20', np.nanmin))} | "
                       f"{f(g(a, 'g_s10_02', np.nanmin))} / {f(g(u, 'g_s10_02', np.nanmin))} | "
                       f"{int(g(a, 'dj', np.nansum))} / {int(g(u, 'dj', np.nansum))} | "
                       f"{f(g(a, 'lurch_light', np.nanmax), 1)} / {f(g(u, 'lurch_light', np.nanmax), 1)} | "
                       f"{f(g(a, 'lurch_firm', np.nanmax), 1)} / {f(g(u, 'lurch_firm', np.nanmax), 1)} |")
        out.append("")
    out += bridge_table()
    txt = "\n".join(out) + "\n"
    (TXT / "score_time_tables.md").write_text(txt, encoding="utf-8")

    def js(x):
        if isinstance(x, dict):
            return {k: js(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [js(v) for v in x]
        if isinstance(x, (np.floating, float)):
            return None if not np.isfinite(x) else round(float(x), 4)
        if isinstance(x, (np.integer,)):
            return int(x)
        return x
    keep_b = ("th20", "th25", "g_s10_02", "g_s03_02", "g_s10_05", "g_s03_05", "dj10", "dj10max", "dj03", "dj03max",
              "lurch_light", "lurch_light_blj", "lurch_firm", "lurch_firm_blj", "eng_droop", "cs_droop", "rn_thf",
              "c30_thf", "hunt_n", "db_lag", "tmos_dev", "tmo_dev", "tmo_Tpk", "sen_T50", "dis_T150", "hard",
              "st_ovs", "wraps", "fails")
    small = {t: {cid: {**{k: v for k, v in row.items() if not isinstance(v, dict)},
                       **{bn: {k: row[bn][k] for k in keep_b} for bn, _, _ in SBANDS}}
                 for cid, row in S_.items()} for t, S_ in summ.items()}
    (TXT / "score_time_summary.json").write_text(json.dumps(js(small)), encoding="utf-8")
    print(f"wrote {TXT / 'score_time_tables.md'} ({len(txt)} B)")


# =====================================================================================================================
# CLI
# =====================================================================================================================
if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "report"
    if w == "h1":
        h1_all()
    elif w == "run":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        frame = sys.argv[3] if len(sys.argv) > 3 else "vgr"
        sc = tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 else SCENS
        run_grid(procs, frame, sc, tag=(sys.argv[5] if len(sys.argv) > 5 else frame))
    elif w == "validate":
        validate()
    elif w == "report":
        report()
