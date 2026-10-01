# -*- coding: utf-8 -*-
"""c1_lib.py -- DESIGN C1 (2026-09-30) of the angle-loop cave: the table, the integer G walk, and byte-exact lane
mirrors for BOTH time harnesses (harness_time.run via HT.LaneVec, and refute_friction/fric_lib.run via F.LaneC0).
ANALYSIS ONLY.  Nothing here builds, flashes or sends anything.

C1 differs from C0 (DESIGN-ANGLE-LOOP-C0-2026-09-30.md) in three places, each mirrored here EXACTLY as the C1 cave
listing computes it (docs/specs/design/DESIGN-ANGLE-LOOP-C1-2026-09-30.md, "The cave"):
  1. the table is RE-BASED (G x2, Kp_base 225, Ki_base 100) so that one angle LSB of error gives e5 = E'>>5 >= 1 at
     every speed (C0: e5 = 0 for a +1 LSB error below ~11.5 m/s -- refuter friction F2);
  2. the table KNOTS are re-sized (GATE 2 on a 0.25 m/s grid with the combined members);
  3. the I policy is a FREEZE, not a bleed: when |gp-0x4f68| > THR or (ramp & 0x8000) == 0 the cave returns to
     0x29D7E with r6 = 0 instead of to 0x29D7A, so Honda's own I code computes exc = 0 and I is unchanged.  The cave
     writes NO RAM (C0's st.w -0x6dd0 is gone).
Every other line is harness_time.LaneVec's byte-exact arithmetic (self-tested there against lane_mirror_v295)."""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
AL = HERE.parent                                   # .../studies/angle_loop
KIT = HERE.parents[3]                              # repo root
for _p in (str(AL), str(AL / "refute_friction"), str(AL / "refute_stability"), str(AL / "reconcile_c0"),
           str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import harness_time as HT                          # noqa: E402
import lane_mirror_v295 as LM                      # noqa: E402
from harness_time import s32, s32g, s16, vlerp     # noqa: E402

OUT = KIT / "_scratch" / "angle_loop" / "c1"
OUT.mkdir(parents=True, exist_ok=True)

# ====================================================================================================================
# C1 constants (the design's cal and cave immediates).  Kp_eff = KP_BASE * G / 256 ; Ki_eff = KI_BASE * G / 256.
# ====================================================================================================================
# ---- THE TABLE / Kd / Ki VARIANTS.  Selected by the env var C1_VARIANT BEFORE any def below binds a default, so every
# ---- default argument (LaneC1F, c1_row, stab_ctl, hf_ctl ...) carries the selected variant's Kd and Ki.
# ---- (rev 1 bound KD at def time from a constant 16 and set the variant at the bottom; harmless for kd16, wrong for kd22.)
# ----   "kd16" = C1 rev 1 (2026-09-30, REFUTED round 2: b_q x J_hi / b_q x J1.0 at highway)
# ----   "r2"   = C1 rev 2 (2026-10-01), the default: see DESIGN-ANGLE-LOOP-C1 rev 2 and c1r2_*.py
VARIANTS = {"kd16": dict(kd=16, ki=100, knots=[(3.1, 557), (8.0, 649), (12.0, 649), (17.0, 1925), (26.9, 2243)]),
            "kd16_6k": dict(kd=16, ki=100, knots=[(3.1, 557), (8.0, 649), (12.0, 649), (13.0, 947), (17.0, 1925),
                                                  (26.9, 2243)]),
            "kd22": dict(kd=22, ki=100, knots=[(3.1, 725), (8.0, 787), (12.0, 771), (13.0, 1079), (17.0, 2098),
                                               (26.9, 2460)]),
            # C1 rev 2: Kd 20 and Ki/Kp 0.5 (fI 0.622 Hz) in a base RE-BASED AGAIN (G x2, Kp_base 112, Ki_base 56) so the
            # table's lowest G (700, at 11.75-11.9 m/s) still gives e5 = 1 for a +1 LSB error.  The 7-knot table sits
            # >= 4.0 % under the envelope of the FULL FACTORIAL member set (c1r2_members: damping x inertia x delay x
            # hold age), built by c1r2_design_G.py 20 56 and the weighted knot search recorded in c1r2_table_compare.py
            "r2": dict(kp=112, kd=20, ki=56, knots=[(3.1, 940), (8.0, 1300), (10.0, 847), (11.75, 701), (15.5, 1046),
                                                    (17.5, 1353), (26.9, 2036)])}
_VAR = os.environ.get("C1_VARIANT", "r2")
KP_BASE = VARIANTS[_VAR].get("kp", 225)   # Kp record 0xE5384 Y x5 (flat)
KD = VARIANTS[_VAR]["kd"]           # Kd record 0xE5126 Y x4, D = clamp((-Kd * gp-0x6a56) >> 3, +-DCL) (edit E5)
KI_BASE = VARIANTS[_VAR]["ki"]      # Ki 0xC63E6
C1_KNOTS = VARIANTS[_VAR]["knots"]
DB = 0                 # 0xC62E4
ICL = 4096             # 0xC61BA
DCL = 10240            # 0xC61B6
FRZ_THR = 512          # cave immediate: freeze I when |gp-0x4f68| > 512 (= the fade-B LERP's first knot, key 16)
SPD_PER_MPS = 3.6 * 64  # gp-0x6a5e counts per m/s


def spd_counts(v):
    return int(round(v * SPD_PER_MPS))


def make_table(knots):
    """knots: [(v_mps or counts, G)] ascending.  Returns the cave rows (X u16, G u16, S s16 Q12) + the 0xFFFF row.
    S(i) = round((G(i+1) - G(i)) * 4096 / (X(i+1) - X(i))); the last real row and the sentinel carry S = 0."""
    X = [int(k[0]) if k[0] > 100 else spd_counts(k[0]) for k in knots]
    G = [int(k[1]) for k in knots]
    assert all(X[i] < X[i + 1] for i in range(len(X) - 1)), X
    rows = []
    for i in range(len(X)):
        S = int(round((G[i + 1] - G[i]) * 4096.0 / (X[i + 1] - X[i]))) if i + 1 < len(X) else 0
        assert -32768 <= S <= 32767 and 0 <= G[i] <= 0xFFFF and 0 <= X[i] <= 0xFFFE
        rows.append((X[i], G[i], S))
    rows.append((0xFFFF, G[-1], 0))
    return rows


def cave_G(v, tbl):
    """the cave's walk, exactly as listed (unsigned compares; mul keeps the low word; sar 12 floors)."""
    v &= 0xFFFF
    if not (v > tbl[0][0]):                        # cmp r13,r8 ; bh L1
        return tbl[0][1]                           # ld.hu 2[r9],r8
    i = 0
    while not (v <= tbl[i + 1][0]):                # L1: ld.hu 6[r9],r13 ; cmp r13,r8 ; bnh SEG ; addi 6,r9,r9 ; br L1
        i += 1
    X, G, S = tbl[i]
    dv = v - X                                     # SEG: ld.hu 0[r9],r13 ; sub r13,r8
    prod = int(LM.s32(dv * S))                     # ld.h 4[r9],r13 ; mul r13,r8,r0
    return G + (prod >> 12)                        # sar 12,r8 ; ld.hu 2[r9],r13 ; add r13,r8


def glut(tbl):
    return np.array([cave_G(v, tbl) for v in range(65536)], np.int64)


def G_at(v_mps, tbl):
    return cave_G(spd_counts(v_mps), tbl)


def kp_eff(v_mps, tbl, kp_base=KP_BASE):
    return kp_base * G_at(v_mps, tbl) / 256.0


# ====================================================================================================================
# the C1 lane core (vectorised), shared by both harness adapters
# ====================================================================================================================
class _C1Core:
    """per-column cave parameters:  gl (B, 65536) G LUT ; thr (|tq| freeze threshold, 0 = never) ; rampfrz (bool) ;
    pol: 'freeze' (C1) | 'bleed' (C0's 8I -= 8I>>bsh above bthr) | 'none' ; reset_thr (st.w r0 above it; 0 = off)."""

    def cave(self, E, tq, ramp, speed):
        G = self.gl[np.arange(self.B), speed & 0xFFFF]                      # the walk (LUT of cave_G)
        Ep = np.where(self.cave_on, s32g(E * G) >> 8, E)                    # mul r8,r16,r0 ; sar 8,r16
        atq = np.minimum(np.abs(tq), 0xFFFF)                                # gp-0x4f68 = |gp-0x4f60| (sat 0xFFFF)
        hand = (self.thr > 0) & (atq > self.thr)                            # ld.hu -0x4f68 ; movea THR ; cmp ; bh FRZ
        rampnf = self.rampfrz & ((ramp & 0x8000) == 0)                      # andi 0x8000,r14,r13 ; bne DONE
        frz = self.cave_on & (self.pol == 1) & (hand | rampnf)              # FRZ: mov 0,r6 ; jr 0x29D7E
        # optional comparison policies (NOT C1): C0's bleed, and a reset (st.w r0,-0x6dd0[gp]) above reset_thr
        bl = self.cave_on & (self.pol == 2) & (atq > self.bthr)
        self.I8 = np.where(bl, s32(self.I8 - (self.I8 >> self.bsh)), self.I8)
        rs = self.cave_on & (self.reset_thr > 0) & (atq > self.reset_thr)
        self.I8 = np.where(rs, 0, self.I8)
        return Ep, frz, G

    def setup_cave(self, B, rows_c1):
        self.B = B
        tabs = {}
        gl = []
        for c in rows_c1:
            key = tuple(c["tbl"])
            if key not in tabs:
                tabs[key] = glut(c["tbl"])
            gl.append(tabs[key])
        self.gl = np.stack(gl)
        self.cave_on = np.array([bool(c.get("cave", True)) for c in rows_c1])
        self.thr = np.array([int(c.get("thr", FRZ_THR)) for c in rows_c1], np.int64)
        self.rampfrz = np.array([bool(c.get("rampfrz", True)) for c in rows_c1])
        self.pol = np.array([{"none": 0, "freeze": 1, "bleed": 2}[c.get("pol", "freeze")] for c in rows_c1], np.int64)
        self.bthr = np.array([int(c.get("bleed_thr", 1024)) for c in rows_c1], np.int64)
        self.bsh = np.array([int(c.get("bleed_sh", 6)) for c in rows_c1], np.int64)
        self.reset_thr = np.array([int(c.get("reset_thr", 0)) for c in rows_c1], np.int64)


def i_update(I8, E, frz, DBv, Ki, ICLv):
    """0x29D7A..0x29DC2 with the freeze path: the cave returns to 0x29D7E with r6 = 0 (e5 := 0)."""
    e5 = np.where(frz, 0, E >> 5)                                           # 0x29D7A mov r16,r6 ; 0x29D7C sar 5,r6
    DBv = DBv & 0xFFFF
    exc = np.where(e5 > DBv, e5 - DBv, np.where(e5 < -DBv, e5 + DBv, 0))    # 0x29D7E..0x29D9A
    icl = ((ICLv & 0xFFFF) << 10) >> 3                                      # 0x29DA0 ld.hu ; shl 10 ; sar 3
    inc = s32g(exc * (Ki & 0xFFFF)) >> 3                                    # 0x29DA8 mul ; 0x29DB2 sar 3
    I = np.clip(s32g((I8 >> 3) + inc), -icl, icl)                           # 0x29DA4 ld.w ; sar 3 ; add ; clamp
    return I, s32g(I << 3)


# ====================================================================================================================
# adapter 1: harness_time.run()  (HT.LaneVec interface: tick(angle, rate, cmd, tq, i6830, speed, ramp, act, req))
# ====================================================================================================================
_LANEVEC_BASE = HT.LaneVec          # captured before install_ht() replaces the module attribute


class LaneC1(_LANEVEC_BASE, _C1Core):
    def __init__(self, cal, cfg):
        _LANEVEC_BASE.__init__(self, cal, cfg)
        self.setup_cave(cfg.B, [r.get("c1", dict(cave=False, tbl=C0_TABLE)) for r in cfg.rows])

    def tick(self, angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol=-1):
        c, g = self.c, self.cfg
        B = g.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        angle, rate, cmd, tq, i6830, speed = map(full, (angle, rate, cmd, tq, i6830, speed))
        ramp, act, req = full(ramp), full(act), full(req)
        x = s16(angle)                                                     # E1 0x28F4C ld.h -0x6a00[gp],r7
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        bx = s32g(x * (c["b"] & 0xFFFF))
        as_ = s32g(int(LM.s16(c["a"])) * s_old)
        s_new = s32((as_ >> 10) + (bx >> 10))
        r26 = s32(s_old + s_new)                                           # E2 0x28FA4 add r9,r26
        C = c["C"] & 0xFFFF
        r26 = np.clip(r26, -C, C)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                             # A2 + B2 (bVar2 true when inputs valid)
        sp = s16(cmd)                                                      # E4 0x29D6A ld.h -0x69ae[gp],r16
        E = s32g((sp << 2) - r26)                                          # cave: displaced shl 2 ; sub r26
        E, frz, G = self.cave(E, tq, ramp, speed)                          # cave: G walk, E' = (E*G)>>8, freeze
        I, I8_new = i_update(self.I8, E, frz, g.DB, g.Ki, g.ICL)
        kp = g.kpY[:, 0] & 0xFFFF                                          # Kp record flat (idx no longer matters)
        P = np.clip(s32g(E * kp) >> 8, -c["PCL"], c["PCL"])                # 0x29E36 mul ; 0x29E3E sar 8 ; PCL
        kd = s32(-(g.kdY[:, 0] & 0xFFFF))                                  # E5 0x29EDE subr r0,r7 (Kd record flat)
        D = np.clip(s32g(kd * s16(rate)) >> 3, -g.DCL, g.DCL)              # E5 0x29EE0 ld.h -0x6a56[gp],r8 ; DCL
        S = s32g((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        f = ((vlerp(*c["fadeA"], i6830) * vlerp(*c["fadeB"], i682f)) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8_new, 0)
        self.Eprev = np.where(run, E, 0x7FFFFFFF)
        t1 = s32g(Sc * (g.ob & 0xFFFF)) >> 10
        t2 = s32g(s16(g.oa) * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr_pass = s16(s32g(y * ramp) >> 15)
        if c["g74a3"] == 1:
            dz = c["dz"]
            block = ((s16(y) <= dz) & (y >= -(dz & 0xFFFF))) | (s32g(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & block, 0, yr_pass)
        else:
            yr = yr_pass
        k = int(LM.s32(LM.s16(pol) * LM.s16(c["fwd"])))
        r11 = s32g(yr * k) >> 15
        OCL = c["OCL"] & 0xFFFF
        T = np.where(r11 > OCL, LM.s16(c["OCL"]), np.where(r11 < -OCL, -OCL, r11))
        self.Tprev = yr
        self.log = dict(r26=r26, E=np.where(run, E, 0), I=np.where(run, I, 0), P=np.where(run, P, 0),
                        D=np.where(run, D, 0), Sc=Sc, y=y, yr=yr, run=run, frz=frz, G=G)
        return s16(T)


def c1_row(tbl=None, label="C1", kp_base=KP_BASE, ki_base=KI_BASE, kd=KD, db=DB, icl=ICL, **cave):
    """an HT.Cfg row carrying the C1 cave.  cave kwargs: thr, rampfrz, pol ('freeze'|'bleed'|'none'), bleed_thr,
    bleed_sh, reset_thr, cave (False = in-place edits only, G = 256 identity)."""
    tbl = c1_table() if tbl is None else tbl
    r = HT.row(kp_base, Ki=ki_base, ICL=icl, DB=db, Kd=kd, label=label)
    r.update(guard_and=True, c1=dict(tbl=[tuple(t) for t in tbl], **cave))
    return r


def install_ht():
    """make harness_time.run() use the C1 lane (it looks LaneVec up at call time)."""
    HT.LaneVec = LaneC1
    return HT


# ====================================================================================================================
# adapter 2: refute_friction/fric_lib.run()  (tick(angle, rate, cmd, tq, speed, ramp, act, req, i6830, pol))
# ====================================================================================================================
_FRIC_CAVE = {}          # the cave dict every LaneC1F column uses unless a column overrides (set by install_fric)


class LaneC1F(_C1Core):
    def __init__(self, B, cal=None, kp=KP_BASE, kd=KD, ki=KI_BASE, icl=ICL, db=DB, bleed=True, cave=True, gmul=1,
                 cols=None):
        self.c = HT.base_cal() if cal is None else cal
        self.B = B
        f = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        self.kp, self.kd, self.ki, self.icl, self.db = f(kp), f(kd), f(ki), f(icl), f(db)
        cs = cols if cols is not None else [dict(_FRIC_CAVE) for _ in range(B)]
        cv = np.broadcast_to(np.asarray(cave, bool), (B,))
        rows_c1 = []
        for j in range(B):
            d = dict(_FRIC_CAVE)
            d.update(cs[j] if j < len(cs) else {})
            d["cave"] = bool(cv[j]) and d.get("cave", True)
            d.setdefault("tbl", c1_table())
            rows_c1.append(d)
        self.setup_cave(B, rows_c1)
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.Eprev, self.olag, self.Tprev = z(), z(), z(), z(), z(), z()
        self.log = {}

    def tick(self, angle, rate, cmd, tq, speed, ramp, act, req, i6830=0, pol=-1):
        c, B = self.c, self.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        angle, rate, cmd, tq, speed, ramp, act, req, i6830 = map(full, (angle, rate, cmd, tq, speed, ramp, act, req, i6830))
        x = s16(angle)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        bx = s32g(x * (c["b"] & 0xFFFF))
        as_ = s32g(int(LM.s16(c["a"])) * s_old)
        s_new = s32((as_ >> 10) + (bx >> 10))
        r26 = s32(s_old + s_new)
        C = c["C"] & 0xFFFF
        r26 = np.clip(r26, -C, C)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(cmd)
        E = s32g((sp << 2) - r26)
        E, frz, G = self.cave(E, tq, ramp, speed)
        I, I8_new = i_update(self.I8, E, frz, self.db, self.ki, self.icl)
        P = np.clip(s32g(E * (self.kp & 0xFFFF)) >> 8, -c["PCL"], c["PCL"])
        kd = s32(-(self.kd & 0xFFFF))
        D = np.clip(s32g(kd * s16(rate)) >> 3, -DCL, DCL)
        S = s32g((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        f = ((vlerp(*c["fadeA"], i6830) * vlerp(*c["fadeB"], i682f)) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8_new, 0)
        self.Eprev = np.where(run, E, 0x7FFFFFFF)
        t1 = s32g(Sc * (c["ob"] & 0xFFFF)) >> 10
        t2 = s32g(int(LM.s16(c["oa"])) * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr_pass = s16(s32g(y * ramp) >> 15)
        if c["g74a3"] == 1:
            dz = c["dz"]
            block = ((s16(y) <= dz) & (y >= -(dz & 0xFFFF))) | (s32g(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & block, 0, yr_pass)
        else:
            yr = yr_pass
        k = int(LM.s32(LM.s16(pol) * LM.s16(c["fwd"])))
        r11 = s32g(yr * k) >> 15
        OCL = c["OCL"] & 0xFFFF
        T = np.where(r11 > OCL, LM.s16(c["OCL"]), np.where(r11 < -OCL, -OCL, r11))
        self.Tprev = yr
        self.log = dict(E=np.where(run, E, 0), I=np.where(run, I, 0), P=np.where(run, P, 0), D=np.where(run, D, 0),
                        S=np.where(run, S, 0), f=f, run=run, G=G, frz=frz)
        return s16(T)


def install_fric(**cave):
    """make refute_friction/fric_lib.run() use the C1 lane.  Returns the patched fric_lib module."""
    import fric_lib as F
    _FRIC_CAVE.clear()
    _FRIC_CAVE.update(dict(tbl=c1_table()))
    _FRIC_CAVE.update(cave)
    F.LaneC0 = LaneC1F
    F.KP_BASE, F.KI, F.KD, F.ICL, F.DB = KP_BASE, KI_BASE, KD, ICL, DB
    F.TBL = [tuple(t) for t in _FRIC_CAVE["tbl"]]
    F.GLUT = glut(F.TBL)
    F.kp_eff = lambda v: KP_BASE * cave_G(spd_counts(v), F.TBL) / 256.0  # noqa: E731
    return F


# ====================================================================================================================
# THE C1 TABLE (filled in by c1_design_G.py; the values below are the design's, see the design page)
# ====================================================================================================================
def c1_table():
    if C1_KNOTS is None:
        raise RuntimeError("C1_KNOTS not set")
    return make_table(C1_KNOTS)


# rebased C0 (G x2), for the controls: identical Kp_eff / Ki_eff to C0 at every speed, only the e5 quantiser differs
C0_KNOTS_X2 = [(691, 512), (1152, 568), (1843, 682), (2880, 1138), (4378, 2844), (5990, 3414)]
C0_TABLE = [(691, 256, 249), (1152, 284, 338), (1843, 341, 901), (2880, 569, 2332), (4378, 1422, 724),
            (5990, 1707, 0), (0xFFFF, 1707, 0)]


# ====================================================================================================================
# linear-model adapters
# ====================================================================================================================
def stab_ctl(v, tbl, d=2, extra_age=0, kp_base=KP_BASE, ki_base=KI_BASE, kd=KD, G=None):
    """the stability refuter's independent model (stab_lin.Ctl) at the C1 operating point."""
    import stab_lin as S
    return S.Ctl(v, kp=kp_base, ki=ki_base, kd=kd, d=d, extra_age=extra_age,
                 G=G_at(v, tbl) if G is None else G)


def hf_ctl(v, tbl, kp_base=KP_BASE, ki_base=KI_BASE, kd=KD, G=None, **kw):
    """the design's harness_freq.Ctl at the C1 operating point (Kp_eff, Ki_eff)."""
    import harness_freq as HF
    g = (G_at(v, tbl) if G is None else G) / 256.0
    return HF.Ctl(kp=kp_base * g, ki=ki_base * g, kd=float(kd), **kw)
