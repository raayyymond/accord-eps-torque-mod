# -*- coding: utf-8 -*-
r"""ds_lane.py -- the INTEGER-EXACT edited lane FUN_00028ea6 for every D-structure implementation, vectorised over a batch
of configurations (one column per implementation), for the 1 kHz time harness.  ANALYSIS ONLY.

Every line is the byte-exact arithmetic of lane_mirror_v295.lane_tick / harness_time.LaneVec / c1_lib.LaneC1 (whose
self-tests prove them equal to the scalar mirror tick for tick) with the in-place edits and the cave of each
implementation inserted EXACTLY as its listing computes them (the listings and their bytes are in ds_asm.py; the
interpreter there executes the assembled bytes against cave_* below).

Column config keys (cfg dict per column):
  kind     'angle' | 'cascade'
  tbl      the cave's G table rows (X u16, G u16, S s16 Q12) incl. the 0xFFFF row        (c1_lib.make_table)
  kp, ki, kd, db, icl, dcl                                       Kp record (flat), Ki 0xC63E6, Kd record (flat),
                                                                 DB 0xC62E4, ICL 0xC61BA, DCL 0xC61B6
  thr      the freeze threshold on |gp-0x4f68| (cave immediate; C1's 512)
  dsrc     'rate_held' (C1 E5) | 'E' (stock D on r16 - E_prev) | 'op' (0x29EE0 -> mov r26,r8 ; nop) | 'none'
  dop      'fine' | 'held_lp' | 'fresh'          (the operand the cave leaves in r26)
  op_sh    left shift applied to the operand in the cave (fine: Delta d << op_sh ; held_lp: Delta s << op_sh)
  lp_m     held_lp: lp += ((Delta s << op_sh) - lp) >> lp_m
  lead     '' | 'fwd' | 'fb' ;  lead_m (w += (X - w) >> lead_m) ; lead_kh (1 | 2 | 3: X + kh (X - w))
  cascade: a, b, C (fb filter cals), cop 'held' | 'fresh' (E1' = ld.h -0x6abe at 0x28F4C), ka_sh (sp_r = (e4 G) >> ka_sh)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as Mdl  # noqa: E402,F401  (paths)
import c1_lib as C  # noqa: E402
import harness_time as HT  # noqa: E402
import lane_mirror_v295 as LM  # noqa: E402
from harness_time import s32, s32g, s16, vlerp  # noqa: E402

SENT = 0x7FFFFFFF


def _col(cfgs, k, d=0):
    return np.array([c.get(k, d) for c in cfgs], np.int64)


class DSLane:
    def __init__(self, cal, cfgs):
        self.c = cal
        self.cfgs = cfgs
        B = self.B = len(cfgs)
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.Eprev, self.olag, self.Tprev = z(), z(), z(), z(), z(), z()
        self.Eprev[:] = SENT
        self.dprev, self.lp, self.w = z(), z(), z()          # cave RAM words (one per implementation that needs it)
        tabs = {}
        gl = []
        for c in cfgs:
            key = tuple(c["tbl"])
            if key not in tabs:
                tabs[key] = C.glut(c["tbl"])
            gl.append(tabs[key])
        self.gl = np.stack(gl)
        self.kind_c = np.array([c.get("kind", "angle") == "cascade" for c in cfgs])
        self.kp, self.ki, self.kd = _col(cfgs, "kp"), _col(cfgs, "ki"), _col(cfgs, "kd")
        self.db, self.icl, self.dcl = _col(cfgs, "db", 0), _col(cfgs, "icl", 4096), _col(cfgs, "dcl", 10240)
        self.thr = _col(cfgs, "thr", 512)
        self.dsrc = np.array([{"none": 0, "rate_held": 1, "E": 2, "op": 3}[c.get("dsrc", "rate_held")] for c in cfgs])
        self.dop = np.array([{"": 0, "fine": 1, "held_lp": 2, "fresh": 3}[c.get("dop", "")] for c in cfgs])
        self.op_sh, self.lp_m = _col(cfgs, "op_sh", 0), _col(cfgs, "lp_m", 3)
        self.lead = np.array([{"": 0, "fwd": 1, "fb": 2}[c.get("lead", "")] for c in cfgs])
        self.lead_m, self.lead_kh = _col(cfgs, "lead_m", 4), _col(cfgs, "lead_kh", 1)
        self.fa, self.fb_, self.fC = _col(cfgs, "a", 0), _col(cfgs, "b", 8192), _col(cfgs, "C", 65535)
        self.cop_f = np.array([c.get("cop", "held") == "fresh" for c in cfgs])
        self.ka_sh = _col(cfgs, "ka_sh", 6)
        self.log = {}
        # fresh sensors, set by the runner before every tick
        self.abe = z()          # gp-0x6abe (1 kHz motor-rate EMA)
        self.dacc = z()         # gp-0x6cc4 (1 kHz motor-position accumulator)

    def tick(self, angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol=-1):
        c, B = self.c, self.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        angle, rate, cmd, tq, i6830, speed, ramp, act, req = map(full, (angle, rate, cmd, tq, i6830, speed, ramp, act,
                                                                         req))
        kc = self.kind_c
        # ---------------- fb filter 0x28F4C..0x28FBE ----------------
        # angle kind: E1 x := gp-0x6a00 ; cascade: x := gp-0x6a56 (held) or gp-0x6abe (E1', fresh)
        x = np.where(kc, np.where(self.cop_f, s16(self.abe), s16(rate)), s16(angle))
        valid = (x >= -12000) & (x <= 12000)                               # 0x28F50..0x28F58 (the +-12000 bail)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        a = np.where(kc, self.fa, 0)
        b = np.where(kc, self.fb_, 8192)
        bx = s32g(x * (b & 0xFFFF))                                         # 0x28F8E mul
        as_ = s32g(s16(a) * s_old)                                          # 0x28F92 mul
        s_new = s32((as_ >> 10) + (bx >> 10))                               # two floors ; add
        r26 = s32(s_old + s_new)                                            # E2 0x28FA4 add r9,r26
        Cc = np.where(kc, self.fC, 65535) & 0xFFFF
        r26 = np.clip(r26, -Cc, Cc)
        self.s = np.where(valid, s_new, self.s)                             # 0x28FA8 st.w r9,-0x3d30 (valid path)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                              # A2 + B2
        sp = s16(cmd)                                                       # E4 0x29D6A ld.h -0x69ae[gp],r16
        first = self.Eprev == SENT                                          # Honda's first-tick sentinel gp-0x6cf8
        G = self.gl[np.arange(B), speed & 0xFFFF]                           # the cave's walk (LUT of c1_lib.cave_G)
        atq = np.minimum(np.abs(tq), 0xFFFF)
        frz = (atq > self.thr) | ((ramp & 0x8000) == 0)
        # ================= THE CAVE (angle kind) =================
        r26a = r26
        fbl = (~kc) & (self.lead == 2)
        w_fb = s32(self.w + ((r26 - self.w) >> self.lead_m))               # w += (r26 - w) >> m
        w_fb = np.where(first, r26, w_fb)                                   # engage init (first tick): w := r26
        r26L = s32(r26 + self.lead_kh * s32(r26 - w_fb))
        r26a = np.where(fbl, r26L, r26a)
        E = s32g((sp << 2) - r26a)                                          # displaced shl 2 ; sub r26
        Ep = s32g(E * G) >> 8                                               # mul r8,r16,r0 ; sar 8
        fwl = (~kc) & (self.lead == 1)
        w_fw = s32(self.w + ((Ep - self.w) >> self.lead_m))
        w_fw = np.where(first, Ep, w_fw)                                    # engage init (first tick): w := E'
        EL = s32(Ep + self.lead_kh * s32(Ep - w_fw))
        r16_a = np.where(fwl, EL, Ep)                                       # the r16 P (and stock D) see
        e5src_a = Ep                                                        # the I always integrates E'
        # D operands left in r26 by the cave
        op = np.zeros(B, np.int64)
        dd = s32(self.dacc - self.dprev)                                    # fine: ld.w -0x6cc4 ; ld.w d_prev ; sub
        #  (no first-tick guard: a stale d_prev after skip ticks gives ONE tick of D, bounded by DCL and x ramp)
        op = np.where(self.dop == 1, s32(dd << self.op_sh), op)
        dS = s32((s_new << 1) - r26)                                        # held_lp: s_new - s_old = 2 s_new - r26
        lp_new = s32(self.lp + ((s32(dS << self.op_sh) - self.lp) >> self.lp_m))
        lp_new = np.where(first, 0, lp_new)
        op = np.where(self.dop == 2, s32(-lp_new), op)
        ab = s16(self.abe)
        abv = ((ab + 13000) & 0xFFFFFFFF) <= 26000                         # Honda's own validity form, unsigned
        op = np.where(self.dop == 3, np.where(abv, ab, 0), op)
        # ================= THE CAVE (cascade kind) =================
        th = s16(angle)                                                     # ld.h -0x6a00[gp] in the cave
        thv = (th >= -12000) & (th <= 12000)
        e4 = np.where(thv, s32(sp - (th << 2)), 0)                          # gp-0x69ae - 4 th_h (0 if invalid)
        spr = s32g(e4 * G) >> self.ka_sh                                    # (e4 G) >> ka_sh
        Ec = np.where(self.cop_f, s32g((spr << 2) + r26), s32g((spr << 2) - r26))
        r16 = np.where(kc, Ec, r16_a)
        e5src = np.where(kc, Ec, e5src_a)
        # ================= Honda's I (0x29D7A..0x29DC2), the freeze path returns to 0x29D7E with r6 = 0 =========
        e5 = np.where(frz, 0, e5src >> 5)
        DBv = self.db & 0xFFFF
        exc = np.where(e5 > DBv, e5 - DBv, np.where(e5 < -DBv, e5 + DBv, 0))
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        inc = s32g(exc * (self.ki & 0xFFFF)) >> 3
        I = np.clip(s32g((self.I8 >> 3) + inc), -icl, icl)
        I8_new = s32g(I << 3)
        # ================= P (0x29E34..0x29E5C), Kp record flat =================
        P = np.clip(s32g(r16 * (self.kp & 0xFFFF)) >> 8, -c["PCL"], c["PCL"])
        # ================= D (0x29E5E..0x29F06) =================
        r27 = np.where((self.Eprev >= -768000) & (self.Eprev <= 768000), self.Eprev, r16)   # cmovnc
        kdv = self.kd & 0xFFFF                                               # zxh r7
        D_E = s32g(kdv * s32(r16 - r27)) >> 3                                # mov r16,r8 ; sub r27,r8 ; mul ; sar 3
        D_rh = s32g(s32(-kdv) * s16(rate)) >> 3                              # E5: subr r0,r7 ; ld.h -0x6a56,r8
        D_op = s32g(kdv * op) >> 3                                           # 0x29EE0 mov r26,r8 ; nop
        D = np.where(self.dsrc == 1, D_rh, np.where(self.dsrc == 2, D_E, np.where(self.dsrc == 3, D_op, 0)))
        D = np.clip(D, -self.dcl, self.dcl)
        # ================= sum, fade, sum clamp, epilogue =================
        S = s32g((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        f = ((vlerp(*c["fadeA"], i6830) * vlerp(*c["fadeB"], i682f)) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8_new, 0)
        self.Eprev = np.where(run, r16, SENT)                                # 0x2A18C st.w r16 (0x7FFFFFFF on skip)
        # cave RAM words: written only on PID ticks (the cave is not on the skip path)
        self.dprev = np.where(run & (self.dop == 1), self.dacc, self.dprev)
        self.lp = np.where(run & (self.dop == 2), lp_new, self.lp)
        self.w = np.where(run & fbl, w_fb, np.where(run & fwl, w_fw, self.w))
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
