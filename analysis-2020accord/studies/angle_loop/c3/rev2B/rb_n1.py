# -*- coding: utf-8 -*-
r"""rb_n1.py -- C3 rev2-B, finding N1 (nonlinear): the A3 integral bound is one-sided (references |theta|, not the
setpoint), so an OUTWARD light hand winds the I up to 64|theta|+1250 or ICL and the release lurches 15.9-23.7 deg.

rev2-B fix: reference the bound to the SETPOINT (gp-0x69ae, = 4*theta_sp counts), not the held angle gp-0x6a00.
Two options, both tested here against the ORIGINAL (theta bound, Ki 56 = C3-P) on the common scorer's own convention:
  * 'sp'  : bound operand = gp-0x69ae; shl (sh-2) folds the x4 (0 extra cave bytes vs C3-P).
  * 'min' : bound operand = min(|theta|, |theta_sp|) (+~10 cave bytes).
Lower Ki (28) is also applied (F1).  CONTROL: Lane2('theta', ki=56) == c3nl_sim.Lane on C3-P bit for bit.

Scenarios (from c3nl_lens): outward light hold (2x Ah, word 400/511, 1/3 s), inward partial drag (0.5 Ah),
straight nudge (5 deg), all at 8..22 m/s, members nominal/bc/F_hi/b_lo*J_hi.  Metric: release lurch past the setpoint.
usage: python rb_n1.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
RC3 = AL / "refute_c3_nonlinear"
sys.path.insert(0, str(RC3))
sys.path.insert(0, str(AL / "panel"))
sys.path.insert(0, str(AL / "c1"))
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402
import c3nl_lens as LN  # noqa: E402
import rb_table as T  # noqa: E402

OUT = AL.parents[2] / "_scratch" / "angle_loop" / "c3-rev2B"
OUT.mkdir(parents=True, exist_ok=True)

# register the rev2-B impls (GB tables) in c3nl_sim.IMPL
S._impl("C3B-P", AL / "c3" / "c3_cave_C3-P.hex", "fresh", 48, 8192, S.A3)   # overwrite rows below
S._impl("C3B-F", AL / "c3" / "c3_cave_C3-F.hex", "held", 24, 8192, S.A3)
S.IMPL["C3B-P"]["rows"] = tuple(T.GB_P)
S.IMPL["C3B-P"]["glut"] = np.array([S.walk_G(tuple(T.GB_P), v) for v in range(0, 65536)], np.int64)
S.IMPL["C3B-F"]["rows"] = tuple(T.GB_F)
S.IMPL["C3B-F"]["glut"] = np.array([S.walk_G(tuple(T.GB_F), v) for v in range(0, 65536)], np.int64)

s16, s32 = S.s16, S.s32


class Lane2(S.Lane):
    """c3nl_sim.Lane with a configurable integral-bound operand (theta | sp | min) and a settable Ki."""

    def __init__(self, impls, bmode="theta", ki=56, sgn=0):
        super().__init__(impls)
        self.bmode = bmode
        self.ki = ki
        self.sgn = sgn                 # opposing-hand freeze threshold (0 = off)

    def tick(self, a6a00, abe, x6a56, sp69ae, tq, ramp, act, req, vw, pol=-1):
        c = S.CAL
        B = self.B
        bc = lambda a: np.broadcast_to(np.asarray(a, np.int64), (B,))  # noqa: E731
        ramp, act, req, tq, vw = bc(ramp), bc(act), bc(req), bc(tq), bc(vw) & 0xFFFF
        x = s16(a6a00)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((s32(0 * s_old) >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(sp69ae)
        E = s32(s32(sp << 2) - r26)
        ab = s16(abe)
        op = np.where(((ab + 13000) & 0xFFFFFFFF) <= 26000, ab, 0)
        G = self.gl[self.ar, vw]
        prod = E * G
        self.wraps += int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8
        atq = np.minimum(np.abs(tq), 0xFFFF)
        f_hard = atq > 512
        th = s16(a6a00)
        sh = np.where(vw > self.vth, self.sh_hi, self.sh_lo)
        # ---- THE BOUND OPERAND (rev2-B N1) ----
        if self.bmode == "theta":
            opnd = np.abs(th)
            bound = s32((opnd << sh) + self.Bb)
        elif self.bmode == "sp":
            opnd = np.abs(sp)                                   # = 4 * theta_sp counts
            bound = s32((opnd << np.maximum(sh - 2, 0)) + self.Bb)   # shl (sh-2) folds the x4
        elif self.bmode == "min":
            a = np.abs(th)
            b = np.abs(sp) >> 2                                 # theta_sp counts
            opnd = np.minimum(a, b)
            bound = s32((opnd << sh) + self.Bb)
        else:
            raise ValueError(self.bmode)
        capon = (self.vcap >= 0) & ~(vw > self.vcap)
        bound = np.where(capon & (bound > self.cap), self.cap, bound)
        Is = self.I8 >> 10
        t = np.where(Ep >= 0, Is, -Is)
        f_arb = self.arb_on & (t >= bound)
        f_ramp = (ramp & 0x8000) == 0
        hs = s16(tq)
        f_opp = (self.sgn > 0) & (np.abs(hs) > self.sgn) & ((hs ^ Ep) < 0)   # opposing-hand freeze (N1)
        frz = f_hard | (~f_hard & (f_opp | f_arb | f_ramp))
        e5 = np.where(frz, 0, Ep >> 5)
        inc = s32(e5 * self.ki) >> 3
        acc = (self.I8 >> 3) + inc
        self.wraps += int(np.count_nonzero(s32(acc) != acc))
        I = np.clip(s32(acc), -self.icl, self.icl)
        I8n = s32(I << 3)
        P = np.clip(s32(Ep * S.KP) >> 8, -c["PCL"], c["PCL"])
        Dp = s32(self.kd * op) >> 3
        Dh = s32(-self.kd * s16(x6a56)) >> 3
        D = np.clip(np.where(self.fresh, Dp, Dh), -S.DCL, S.DCL)
        Sx = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fB = S.lerp_vec(*c["fadeB"], i682f)
        f = ((S.FA0 * fB) & 0xFFFF) >> 8
        Sf = s32(Sx * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & blk, 0, yr)
        k = pol * c["fwd"]
        r11 = s32(yr * k) >> 15
        Tt = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), P=np.where(run, P, 0), D=np.where(run, D, 0),
                        frz=frz & run, farb=f_arb & ~f_hard & run, bound=bound, Ep=Ep, run=run)
        return s16(Tt)


def run_with(lanefac, cols, scn, **kw):
    orig = S.Lane
    S.Lane = lanefac
    try:
        return S.run(cols, scn, **kw)
    finally:
        S.Lane = orig


def control():
    """Lane2('theta', ki=56) must equal c3nl_sim.Lane on C3-P bit for bit."""
    cols = [dict(impl="C3-P", member=m, v=v, age=0) for m in ("nominal", "b_lo*J_hi") for v in (8.0, 12.75, 17.0)]
    scn, meta = LN.build("out_2_511_3", cols)
    rO = S.run(cols, scn)
    rN = run_with(lambda impls: Lane2(impls, "theta", 56), cols, scn)
    dth = np.abs(rO["th"] - rN["th"]).max()
    dT = np.abs(rO["T"].astype(int) - rN["T"].astype(int)).max()
    return dth, dT


SPEEDS = (8.0, 9.0, 10.0, 11.0, 12.0, 12.75, 14.0, 16.0, 18.0, 20.0, 22.0)
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
SCNS = ["out_2_511_3", "out_1.5_511_3", "out_2_400_1", "nudge_5_511_3", "part_0.5_511_3", "part_0.5_511_1"]
# (impl, bmode, ki) columns to compare
VARIANTS = [("C3-P", "theta", 56, 0), ("C3B-P", "theta", 44, 0), ("C3B-P", "sp", 44, 0),
            ("C3B-P", "theta", 44, 300), ("C3B-P", "sp", 44, 300), ("C3B-P", "min", 44, 300),
            ("P2", "theta", 56, 0)]


def lurch_for(scn_name, impl, bmode, ki, sgn=0):
    cols = [dict(impl=impl, member=m, v=v, age=0) for m in MEMBERS for v in SPEEDS]
    scn, meta = LN.build(scn_name, cols)
    r = run_with(lambda impls: Lane2(impls, bmode, ki, sgn), cols, scn)
    mt = LN.metrics(scn_name, meta, r, cols)
    # 'under' = overshoot toward centre past the setpoint; 'over' = past setpoint into turn (both are the lurch)
    under = np.array(mt.get("under", mt.get("over")))
    over = np.array(mt.get("over"))
    lur = np.maximum(under, over)
    bands = {"8-12.5": [i for i, c in enumerate(cols) if c["v"] < 12.5 and c["v"] >= 8],
             "12.5-22": [i for i, c in enumerate(cols) if c["v"] >= 12.5]}
    return {b: float(lur[idx].max()) for b, idx in bands.items()}


def main():
    out = ["== C3 rev2-B N1: release lurch (deg past setpoint), max over members, by band ==",
           "CONTROL Lane2('theta',56) vs c3nl_sim.Lane on C3-P: dth %.2e deg, dT %d counts" % control(), ""]
    for scn in SCNS:
        out.append(f"-- {scn} --")
        for impl, bmode, ki, sgn in VARIANTS:
            try:
                r = lurch_for(scn, impl, bmode, ki, sgn)
                out.append(f"   {impl:6s} b={bmode:5s} Ki{ki:2d} sgn{sgn:3d}:  8-12.5 {r['8-12.5']:5.1f}   12.5-22 {r['12.5-22']:5.1f}")
            except Exception as e:
                out.append(f"   {impl} {bmode} {ki} {sgn}: ERR {e}")
    (OUT / "n1_lurch.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
