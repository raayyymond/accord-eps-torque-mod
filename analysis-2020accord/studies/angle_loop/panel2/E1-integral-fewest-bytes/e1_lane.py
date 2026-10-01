# -*- coding: utf-8 -*-
r"""e1_lane.py -- PANEL 2, designer E1 (INTEGRAL POLICY, FEWEST BYTES), 2026-10-01.

THE PROBLEM (nonlinear refuter F1, re-derived by me from the mirror arithmetic -- EVIDENCE):
  The integer I is clamped at icl = (ICL<<10)>>3 = ICL*128 (in the 8*I units of gp-0x6dd0 the clamp holds I itself,
  since the clamp is applied after (I8>>3)).  I contributes (I>>7) to the sum S, so the clamp on I at icl means the I
  branch of S is at most ICL.  Through the hands-off fade (254/256 = 0.9922), the output-lag DC gain (0.990) and the
  forward gain (5346/32768 = 0.16314), the DELIVERED torque from a saturated I is
        T_I = ICL * 0.9922 * 0.990 * 0.16314 = ICL * 0.16024    (T counts)
  At ICL 4096 that is 656.3 T.  The identified spring load k*sat*tanh(theta/sat) on ordinary 1.5-2.0 m/s^2 curves at
  15-19 m/s is 850-1170 T, so P must carry the rest with a steady error and turn-hold / tracking miss the goal.

THE AXIS: raise the integral authority so I can carry the curve, WITHOUT re-opening the override-release lurch (V283),
with the FEWEST firmware bytes.

This module is the byte-exact integer lane with the integral policy as switches, vectorised over columns.  It SUBCLASSES
the C2 rev2 nonlinear refuter's INDEPENDENT lane (refute_c2r2_nonlinear/nl_sim.Lane, written from my own Ghidra dry-run
of 0x29D60..0x29F80 and proved == the cave BYTES by the refuter's interpreter, 0/60000) and overrides ONLY the integral
section (0x29D7A..0x29DC2 + the cave freeze path).  CONTROL (e1_control.py): with the baseline policy (icl flat 4096, no
reset, no bleed) this lane == nl_sim.Lane bit for bit.  Every deviation below is one implementation's declared edit.

ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing, writes nothing outside _scratch/angle_loop/E1-*.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ANGLE = HERE.parents[1]                      # .../studies/angle_loop
STUDIES = HERE.parents[2]                    # .../studies
KIT = HERE.parents[4]                        # repo root
RC2 = ANGLE / "refute_c2r2_nonlinear"
sys.path.insert(0, str(RC2))
sys.path.insert(0, str(ANGLE))
sys.path.insert(0, str(STUDIES / "v295" / "plant"))

import nl_sim as NS          # the refuter's controlled engine (Lane, Plant, params, metrics)
import nl_cave as NC         # table parse / G walk (independent)
from nl_sim import s16, s32

# the shared C2 cal set (both revisions), from nl_sim
KP, KI, DB = NS.KP, NS.KI, NS.DB     # 112, 56, 0
DCL = NS.DCL                          # 10240
CAL = NS.CAL
FWD = CAL["fwd"]                      # 5346


# ---------------------------------------------------------------------------------------------------------------------
# the delivered-torque-from-I constant (EVIDENCE: arithmetic above, re-derived here so the design doc quotes it live)
# ---------------------------------------------------------------------------------------------------------------------
def T_per_ICL(fade=254):
    """delivered T counts per unit of ICL at a saturated I, hands-off (fade 254)."""
    return (fade / 256.0) * (CAL["ob"] + CAL["oa"]) / 1024.0 * 0  # placeholder; see note


def t_from_I(I_contrib, fade=254, pol=-1):
    """delivered |T| from an I-branch value I_contrib = (I>>7), through fade, output lag DC and forward gain.
    The output-lag DC gain is (oa+ob? no): y_dc = S * (ob/1024) / (1 - oa/1024); here oa 992, ob 507 -> no.
    Use the mirror's own steady-state: see t_from_I_exact."""
    raise NotImplementedError


# ---------------------------------------------------------------------------------------------------------------------
# implementations (each a concrete integral policy)
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Policy:
    name: str
    icl_flat: int | None = 4096          # flat ICL cal (None -> use icl_table)
    icl_table: tuple | None = None       # speed-scheduled ICL rows (X u16 counts, ICL u16) incl 0xFFFF
    reset_firm: int | None = None        # |tq| > reset_firm  ->  I := 0 (firm-hand reset)
    freeze_thr: int = 512                # |tq| > freeze_thr  ->  I unchanged (existing freeze)
    bleed_lo: int | None = None          # bleed band low threshold on |tq| (implementation iv)
    bleed_sh: int = 4                    # I -= I>>bleed_sh per tick while bleeding
    kp: int = 112                        # P gain (split-authority uses a higher Kp)
    note: str = ""


def _icl_walk(rows, v):
    """piecewise-linear ICL(v) by the same walk as G (v in gp-0x6a5e counts, 230.4 per m/s)."""
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


class E1Lane(NS.Lane):
    """nl_sim.Lane with the E1 integral policy, VECTORISED OVER COLUMNS: each column may carry a different policy, so one
    simulation scores every policy x impl at once.  Overrides tick() and re-uses every other stage verbatim.
    `policies` is either a single Policy (applied to all columns) or a list of one Policy per column."""

    def __init__(self, impls, speeds_word, policies):
        super().__init__(impls, speeds_word)
        B = self.B
        pols = policies if isinstance(policies, (list, tuple)) else [policies] * B
        assert len(pols) == B
        self.pols = pols
        sw = np.clip(np.asarray(speeds_word, np.int64), 0, 12000)
        iclv, kpv, resetv, bleed_lo_v, bleed_sh_v, freeze_v = [], [], [], [], [], []
        for p, s in zip(pols, sw):
            iclv.append(_icl_walk(p.icl_table, s) if p.icl_table is not None else p.icl_flat)
            kpv.append(p.kp)
            resetv.append(p.reset_firm if p.reset_firm is not None else (1 << 30))
            bleed_lo_v.append(p.bleed_lo if p.bleed_lo is not None else (1 << 30))
            bleed_sh_v.append(p.bleed_sh)
            freeze_v.append(p.freeze_thr)
        self.iclv = np.array(iclv, np.int64)
        self.kpv = np.array(kpv, np.int64)
        self.resetv = np.array(resetv, np.int64)
        self.bleed_lo_v = np.array(bleed_lo_v, np.int64)
        self.bleed_sh_v = np.array(bleed_sh_v, np.int64)
        self.freeze_v = np.array(freeze_v, np.int64)

    def tick(self, angle, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        c = CAL
        # ---- fb filter 0x28F4C..0x28FBE (E1 x:=angle, E2 add, a 0 b 8192 C 65535) -- verbatim from nl_sim.Lane ----
        x = s16(angle)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((0 * s_old >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(cmd)
        # ---- THE CAVE ----
        E = s32((sp << 2) - r26)
        prod = E * self.G
        self.wraps += int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8
        atq = np.minimum(np.abs(tq), 0xFFFF)
        frz = (atq > self.freeze_v) | ((np.int64(ramp) & 0x8000) == 0)
        ab = s16(abe)
        op = np.where(((ab + 13000) & 0xFFFFFFFF) <= 26000, ab, 0)
        # ---- Honda's I 0x29D7A..0x29DC2, with the E1 policy ----
        e5 = np.where(frz, 0, Ep >> 5)
        exc = np.where(e5 > DB, e5 - DB, np.where(e5 < -DB, e5 + DB, 0))
        I8 = self.I8
        # (R) firm-hand reset: the cave zeroes gp-0x6dd0 before the I-clamp reads it => I_old = 0
        reset = atq > self.resetv
        I8 = np.where(reset, 0, I8)
        icl = (self.iclv << 10) >> 3
        I = np.clip(s32((I8 >> 3) + (s32(exc * KI) >> 3)), -icl, icl)
        # (B) bleed by |tq| band (implementation iv): I -= I>>bleed_sh while bleeding (pre-clamp carry via I8)
        bleeding = (atq > self.bleed_lo_v) & (atq <= self.freeze_v)
        I = np.where(bleeding, s32(I - (I >> self.bleed_sh_v)), I)
        I8n = s32(I << 3)
        # ---- P 0x29E34..0x29E5C (split-authority raises kp) ----
        P = np.clip(s32(Ep * self.kpv) >> 8, -c["PCL"], c["PCL"])
        # ---- D 0x29EDE..0x29F06 ----
        Dfr = s32(self.kd * op) >> 3
        Dhe = s32(-self.kd * s16(xheld)) >> 3
        D = np.clip(np.where(self.fresh, Dfr, Dhe), -DCL, DCL)
        # ---- sum, fade, sum clamp ----
        S = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(np.asarray(tq, np.int64) >> 5), 255)
        from nl_sim import lerp_vec
        fA = lerp_vec(*c["fadeA"], np.zeros(self.B, np.int64))
        fB = lerp_vec(*c["fadeB"], i682f)
        f = ((fA * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        # ---- output lag ----
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t1 + t2)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        # ---- sign-hold gate ----
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1 and act == 0:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where(blk, 0, yr)
        k = pol * c["fwd"]
        r11 = s32(yr * k) >> 15
        T = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), P=np.where(run, P, 0), D=np.where(run, D, 0), E=np.where(run, E, 0),
                        Ifull=np.where(run, I, 0), frz=frz, f=f, run=run)
        return s16(T)


# ---------------------------------------------------------------------------------------------------------------------
# delivered-T-from-I, exact (steady-state of the output lag + fade + fwd), EVIDENCE for the design doc
# ---------------------------------------------------------------------------------------------------------------------
def t_from_I_contrib(I_contrib, fade=254):
    """steady delivered |T| for a constant I-branch value (I>>7) = I_contrib, P=D=0, hands off (fade 254), pol -1.
    output lag steady: o = (ob/1024) S / (1 - oa/1024) ; y = (o + o')>>5 ... use the mirror's DC gain 0.990."""
    S = I_contrib
    Sf = (S * fade) >> 8
    # output-lag DC: o_new = (ob*Sc + oa*o)/1024 ; steady o* = ob*Sc/(1024-oa) ; y = (o*+o_new)>>5 = 2 o*/32
    oa, ob = CAL["oa"], CAL["ob"]
    o_star = (ob * Sf) / (1024 - oa)
    y = (o_star + o_star) / 32.0
    T = abs(y * FWD / 32768.0)
    return T


# the policies (implementations)
ICL_NEEDS = None   # filled by e1_design_icl.py (per-band ICL from the spring load)

if __name__ == "__main__":
    for icl in (4096, 6144, 8192, 10240, 12288, 16383):
        print(f"ICL {icl:5d}: I-branch max {icl}, delivered T_I (fade 254) = {t_from_I_contrib(icl):.0f} T "
              f"(fade floor 0.297: {t_from_I_contrib(icl, int(0.297*254)):.0f} T)")
