# -*- coding: utf-8 -*-
r"""e2_lane.py -- designer E2 (integral policy, most margin then fewest bytes), 2026-10-01.  ANALYSIS ONLY: builds no
image, flashes nothing, sends nothing.

E2Lane = ds_lane.DSLane (the integer-exact edited lane FUN_00028ea6 every C2/panel cave column runs on; ds_selftest
CHECK 1 proves it == c1_lib.LaneC1F) with the INTEGRAL POLICY made a switch.  Only the angle kind is carried (the
cascade and lead options of DSLane raise).  With every new key at its default the tick is DSLane's tick, bit for bit
(selftest() below, CONTROL E2-0, on P2 and F2 columns in four scenarios).

THE I PATH (Honda's, unchanged; the cave only chooses r6 = e5 and where to return):
    normal  : the cave returns to 0x29D7A, Honda computes e5 = E' >> 5           (0x29D7A mov r16,r6 ; 0x29D7C sar 5,r6)
    freeze  : the cave sets r6 = 0 and jr 0x29D7E                                 -> exc = 0 -> I unchanged
    leak    : the cave sets r6 = -(I8 >> leak_s) and jr 0x29D7E                    -> inc = (r6 * Ki) >> 3 (DB 0)
    I       = clamp((I8 >> 3) + inc, +-(ICL << 10) >> 3) ; I8 := I << 3 ; S = (I >> 7) + P + D   (0x29D7E..0x29DC2)

NEW COLUMN KEYS (all default OFF = DSLane / P2 behaviour):
  ramp_frz  True    freeze the I while the ramp gp-0x69b0 is not full (C1/P2's andi 0x8000 test); False = no test
  sgn_thr   0       OPPOSING-HAND freeze: freeze when the hand torque opposes E' and |hand| > sgn_thr (words of
                    gp-0x4f60).  sign(gp-0x4f60) = the direction the hand pushes in the gp-0x6a00 frame (EVIDENCE:
                    e2_data_r71b.py (0)+(1)), so OPPOSING <=> sign(hand) != sign(E').
  sgn_src   'raw'   'raw' = gp-0x4f60 (1 kHz, unfiltered) | 'lp' = gp-0x3d34 (Honda's own 5.05 Hz IIR of gp-0x4f60,
                    s = ((s*31)>>5) + ((tq*634)>>5), cals 0xC63E2 = 31 / 0xC63E4 = 634, written every lane tick at
                    the function head; DC gain 634 -> the cave compares s against sgn_thr * 634)
  leak_s    0       LEAK: when the leak condition holds, r6 = -(I8 >> leak_s) instead of e5 (I decays by ~Ki*8/2^leak_s
                    per tick: Ki 56, leak_s 13 -> tau 146 ms; 14 -> 293 ms)
  leak_thr  512     leak condition |gp-0x4f68| > leak_thr (replaces the hard freeze above leak_thr when leak_s > 0)
  leak_opp  False   with sgn_thr > 0 and leak_s > 0: an OPPOSING hand leaks the I instead of freezing it
  leak_hard (leak_s>0 and not leak_opp)  the hard |tq| > leak_thr test leaks (True) or freezes at thr (False)
  opp_first False   evaluate the opposing-hand test BEFORE the hard test (a firm opposing hand then takes the
                    opposing branch)
  arb_sh    0       ANGLE-REFERENCED I BOUND (ARB): freeze when t = sgn(E') * (I8 >> 10) >= bound_S, with
                    bound_S = (|gp-0x6a00| << arb_sh) + arb_B (S units; I8 >> 10 = I >> 7 = the I's share of S; the
                    held angle the P sees, 0.1 deg counts).  (legacy key arb_k = arb_sh + 6.)  arb_sh 6 = 64 S per 0.1 deg =
                    640 S/deg = ~102 T/deg (x 0.160 T per S); 5 = ~51 T/deg; arb_B in S (1250 S = ~200 T)
  arb_sh_lo -1      TWO-LEVEL ARB: the slope shift is arb_sh_lo while gp-0x6a5e <= arb_vth (unsigned), arb_sh above
  arb_vth   0       (e.g. sh_lo 4 = ~26 T/deg up to 2880 counts = 12.5 m/s, sh 6 = ~102 T/deg above)
  arb_vcap  -1      LOW-SPEED CAP: while gp-0x6a5e <= arb_vcap the bound is min(bound, arb_cap) (S units) -- P2's
  arb_cap   0       ICL 4096 at parking speed, where the post-release windup (M-b) is the whole lurch
  fade2     False   the gp-0x6803 == 2 post-PID fade arm (0xCBAE4 -> 0xE54FC) instead of 0xCBBC4 (r25 = 1)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "c2" / "rev2A"))
import r2a_common as R  # noqa: E402,F401  (paths, members, tables)
import ds_lane as DL  # noqa: E402
import harness_time as HT  # noqa: E402
import lane_mirror_v295 as LM  # noqa: E402
from harness_time import s32, s32g, s16, vlerp  # noqa: E402

SENT = DL.SENT
_col = DL._col


class E2Lane(DL.DSLane):
    def __init__(self, cal, cfgs):
        for c in cfgs:
            if c.get("kind", "angle") != "angle" or c.get("lead", ""):
                raise ValueError("E2Lane carries the angle kind without lead only")
        super().__init__(cal, cfgs)
        B = self.B
        self.ramp_frz = np.array([bool(c.get("ramp_frz", True)) for c in cfgs])
        self.sgn_thr = _col(cfgs, "sgn_thr", 0)
        self.sgn_lp = np.array([c.get("sgn_src", "raw") == "lp" for c in cfgs])
        self.leak_s = _col(cfgs, "leak_s", 0)
        self.leak_thr = _col(cfgs, "leak_thr", 512)
        self.leak_opp = np.array([bool(c.get("leak_opp", False)) for c in cfgs])
        self.leak_hard = np.array([bool(c.get("leak_hard", int(c.get("leak_s", 0)) > 0 and not c.get("leak_opp", False)))
                                   for c in cfgs])
        self.opp_first = np.array([bool(c.get("opp_first", False)) for c in cfgs])
        self.arb_on = np.array([int(c.get("arb_k", 0)) > 0 or int(c.get("arb_sh", 0)) > 0 for c in cfgs])
        self.arb_sh = np.array([int(c["arb_sh"]) if "arb_sh" in c else max(int(c.get("arb_k", 6)) - 6, 0)
                                for c in cfgs], np.int64)
        self.arb_B = _col(cfgs, "arb_B", 0)
        self.arb_sh_lo = np.array([int(c.get("arb_sh_lo", -1)) for c in cfgs], np.int64)   # -1 = single level
        self.arb_vth = _col(cfgs, "arb_vth", 0)                                              # gp-0x6a5e counts
        self.arb_vcap = _col(cfgs, "arb_vcap", -1)                                           # low-speed cap knee
        self.arb_cap = _col(cfgs, "arb_cap", 0)                                              # cap, S units
        self.fade2 = np.array([bool(c.get("fade2", False)) for c in cfgs])
        self.s3d34 = np.zeros(B, np.int64)          # gp-0x3d34 (Honda's IIR of gp-0x4f60; runs every lane tick)
        self.n_frz = np.zeros(B, np.int64)
        self.n_run = np.zeros(B, np.int64)

    def tick(self, angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol=-1):
        c, B = self.c, self.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        angle, rate, cmd, tq, i6830, speed, ramp, act, req = map(full, (angle, rate, cmd, tq, i6830, speed, ramp, act,
                                                                         req))
        # ---------------- Honda's driver-torque IIR at the function head (0xC63E2 = 31, 0xC63E4 = 634) ----------------
        self.s3d34 = s32((s32(self.s3d34 * 31) >> 5) + (s32(s16(tq) * 634) >> 5))
        # ---------------- fb filter 0x28F4C..0x28FBE (E1 x := gp-0x6a00, a = 0, b = 8192, C = 65535) ----------------
        x = s16(angle)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        bx = s32g(x * 8192)
        s_new = s32((0 >> 10) + (bx >> 10))
        r26 = s32(s_old + s_new)
        r26 = np.clip(r26, -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                              # A2 + B2
        sp = s16(cmd)                                                       # E4 0x29D6A ld.h -0x69ae[gp],r16
        first = self.Eprev == SENT
        G = self.gl[np.arange(B), speed & 0xFFFF]
        atq = np.minimum(np.abs(tq), 0xFFFF)                                # gp-0x4f68
        # ================= THE CAVE =================
        E = s32g((sp << 2) - r26)                                           # displaced shl 2 ; sub r26
        Ep = s32g(E * G) >> 8                                               # mul ; sar 8
        op = np.zeros(B, np.int64)
        dd = s32(self.dacc - self.dprev)
        op = np.where(self.dop == 1, s32(dd << self.op_sh), op)
        dS = s32((s_new << 1) - r26)
        lp_new = s32(self.lp + ((s32(dS << self.op_sh) - self.lp) >> self.lp_m))
        lp_new = np.where(first, 0, lp_new)
        op = np.where(self.dop == 2, s32(-lp_new), op)
        ab = s16(self.abe)
        abv = ((ab + 13000) & 0xFFFFFFFF) <= 26000
        op = np.where(self.dop == 3, np.where(abv, ab, 0), op)
        # ---- the integral policy: the cave's ORDERED decision of r6 and of the return address (cave-exact) ----
        #  1. |gp-0x4f68| > THR (unsigned)                          -> LEAK if leak_s else FREEZE
        #  2. sgn_thr: |hand| > sgn_thr and sign(hand) != sign(E')   -> LEAK if leak_opp else FREEZE
        #  3. ARB: t = sgn(E') * (I8 >> 10) >= (|gp-0x6a00| << arb_sh) + arb_B           -> FREEZE
        #  4. ramp_frz and (ramp & 0x8000) == 0                      -> FREEZE
        #  5. otherwise NORMAL (return to 0x29D7A: e5 = E' >> 5)
        leak_on = self.leak_s > 0
        lh = leak_on & self.leak_hard                                        # the hard test leaks instead of freezing
        c1 = atq > np.where(lh, self.leak_thr, self.thr)
        hsrc = np.where(self.sgn_lp, self.s3d34, s16(tq))
        hthr = np.where(self.sgn_lp, self.sgn_thr * 634, self.sgn_thr)
        c2 = (self.sgn_thr > 0) & (np.abs(hsrc) > hthr) & ((hsrc ^ Ep) < 0)     # xor ; blt (signs differ)
        I8 = self.I8
        I_S = I8 >> 10                                                       # ld.w -0x6dd0 ; sar 10 (= I >> 7)
        t = np.where(Ep >= 0, I_S, -I_S)                                     # cmp r0,r16 ; bge ; subr r0
        sh = np.where((self.arb_sh_lo >= 0) & ((speed & 0xFFFF) <= self.arb_vth), self.arb_sh_lo, self.arb_sh)
        bound = s32((np.abs(x) << np.where(self.arb_on, sh, 0)) + self.arb_B)   # ld.h -0x6a00 ; |.| ; [v test] shl ; addi
        capon = (self.arb_vcap >= 0) & ((speed & 0xFFFF) <= self.arb_vcap)
        bound = np.where(capon & (bound > self.arb_cap), self.arb_cap, bound)  # movea CAP ; cmp ; cmovh (unsigned)
        c3 = self.arb_on & (t >= bound)                                      # cmp ; bge FRZ (signed)
        c4 = self.ramp_frz & ((ramp & 0x8000) == 0)
        lo = leak_on & self.leak_opp                                         # the opposing test leaks instead
        first_hard = ~self.opp_first
        hit_h = c1 & (first_hard | ~c2)                                      # the hard test decides
        hit_o = c2 & (~first_hard | ~c1)                                     # the opposing test decides
        leak_c = (hit_h & lh) | (hit_o & lo)
        frz = (hit_h & ~lh) | (hit_o & ~lo) | (~c1 & ~c2 & (c3 | c4))
        e5_leak = s32(-(I8 >> np.where(leak_on, self.leak_s, 31)))
        e5 = np.where(leak_c, e5_leak, np.where(frz, 0, Ep >> 5))
        # ================= Honda's I (0x29D7E..0x29DC2) =================
        DBv = self.db & 0xFFFF
        exc = np.where(e5 > DBv, e5 - DBv, np.where(e5 < -DBv, e5 + DBv, 0))
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        inc = s32g(exc * (self.ki & 0xFFFF)) >> 3
        I = np.clip(s32g((self.I8 >> 3) + inc), -icl, icl)
        I8_new = s32g(I << 3)
        r16 = Ep
        P = np.clip(s32g(r16 * (self.kp & 0xFFFF)) >> 8, -c["PCL"], c["PCL"])
        r27 = np.where((self.Eprev >= -768000) & (self.Eprev <= 768000), self.Eprev, r16)
        kdv = self.kd & 0xFFFF
        D_E = s32g(kdv * s32(r16 - r27)) >> 3
        D_rh = s32g(s32(-kdv) * s16(rate)) >> 3
        D_op = s32g(kdv * op) >> 3
        D = np.where(self.dsrc == 1, D_rh, np.where(self.dsrc == 2, D_E, np.where(self.dsrc == 3, D_op, 0)))
        D = np.clip(D, -self.dcl, self.dcl)
        S = s32g((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fB = np.where(self.fade2, vlerp(*c["fadeB2"], i682f), vlerp(*c["fadeB"], i682f))
        fA = np.where(self.fade2, vlerp(*c["fadeA2"], i6830), vlerp(*c["fadeA"], i6830))
        f = ((fA * fB) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.n_run += run
        self.n_frz += run & (frz | leak_c)
        self.I8 = np.where(run, I8_new, 0)
        self.Eprev = np.where(run, r16, SENT)
        self.dprev = np.where(run & (self.dop == 1), self.dacc, self.dprev)
        self.lp = np.where(run & (self.dop == 2), lp_new, self.lp)
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
        self.log = dict(E=np.where(run, r16, 0), I=np.where(run, I, 0), P=np.where(run, P, 0), D=np.where(run, D, 0),
                        S=np.where(run, S, 0), f=f, run=run, G=G, frz=frz, op=op)
        return s16(T)


def selftest():
    """CONTROL E2-0: E2Lane with every new key at its default == DSLane bit for bit (P2 and F2 columns, and P2 with ICL
    8192), through score_time.run's own engine (lane_cls hook) in four scenarios on two members."""
    from e2_common import ST
    tabs = R.tables()
    cfgs = [R.lane_cfg("P2", tabs["P2"]), R.lane_cfg("F2", tabs["F2"]), dict(R.lane_cfg("P2", tabs["P2"]), icl=8192)]
    lines = []
    ok = True
    for nm, v, mem in (("rh", 11.9, "nominal"), ("ov_light400", 8.0, "b_lo*J_hi"), ("eng_load", 10.0, "bc"),
                       ("s02", 17.0, "F_hi")):
        scn = ST.scenario(nm, v)
        r1 = ST.run(scn, cfgs, [], mem, v)
        r2 = ST.run(scn, cfgs, [], mem, v, lane_cls=E2Lane)
        d = int(np.abs(r1["T"].astype(int) - r2["T"].astype(int)).max())
        dth = float(np.abs(r1["th"] - r2["th"]).max())
        ok &= d == 0 and dth == 0
        lines.append(f"CONTROL E2-0 {nm}@{v} {mem}: E2Lane (defaults) vs DSLane, P2/F2/P2-ICL8192: max|dT| {d}, "
                     f"max|dtheta| {dth:.2e}  {'OK' if d == 0 and dth == 0 else 'FAIL'}")
    out = "\n".join(lines)
    print(out)
    (HERE / "e2_lane_selftest.txt").write_text(out + "\n", encoding="utf-8")
    return ok


if __name__ == "__main__":
    selftest()
