# -*- coding: utf-8 -*-
r"""g_lane.py -- the integer-exact lane for designer G's implementations (panel 2).  ANALYSIS ONLY.

EXTENDS ds_lane.DSLane (the D designer's integer lane, == c1_lib.LaneC1F 0 / 40 000 ticks by ds_selftest CHECK 1) by
subclassing -- nothing re-implemented.  Implementations (i) fresh-rate D and (ii) held-rate D are DSLane's own 'op fresh'
and 'rate_held' paths with a different Kd and table (no new arithmetic).  Implementation (iii), the angle-own D 'box10',
is the one new operand, computed here EXACTLY as g_cave.py's listing does, and handed to DSLane through its 'fine' path
(op = dacc - dprev with op_sh 0: dacc is set to op + dprev for those columns, so DSLane's own D multiply, DCL clamp and
everything downstream are reused unchanged):

    first = (gp-0x6cf8 == 0x7FFFFFFF)                    Honda's first-tick sentinel (written on every skip tick)
    C, W  = (th, 0) if first else (RAM_A, RAM_B)          RAM_A = last seen th_h, RAM_B = (-Delta << 8) + countdown
    if th != C:  W = ((C - th) << 8) + 10                 a refresh changed th_h: hold -Delta for 10 ticks
    elif W & 0xFF:  W -= 1 ; W = 0 if (W & 0xFF) == 0     countdown; at 0 the difference expires (a zero-change refresh)
    RAM_A, RAM_B = th, W                                   only on PID ticks (the cave is not on the skip path)
    op = (W >> 8) << sh                                    = -(th_h[n] - th_h[n-10]) << sh   (the D operand in r26)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402,F401  (paths)
import ds_lane as DL  # noqa: E402
from harness_time import s32, s16  # noqa: E402

SENT = DL.SENT


class GLane(DL.DSLane):
    def __init__(self, cal, cfgs):
        self.bx = np.array([c.get("dop") == "box10" for c in cfgs])
        base = []
        for c in cfgs:
            if c.get("dop") == "box10":
                c = dict(c, dop="fine", op_sh=0)
            base.append(c)
        super().__init__(cal, base)
        B = len(cfgs)
        self.bx_sh = np.array([c.get("bx_sh", 6) for c in cfgs], np.int64)
        self.bxC = np.zeros(B, np.int64)
        self.bxW = np.zeros(B, np.int64)

    def box_op(self, angle, ramp, req):
        """the box10 cave arithmetic for every column (used only where self.bx); returns (op, C_new, W_new, run)."""
        th = s16(np.broadcast_to(np.asarray(angle, np.int64), (self.B,)).copy())
        valid = (th >= -12000) & (th <= 12000)
        run = valid & (np.asarray(ramp) != 0) & (np.asarray(req) == 1)
        first = self.Eprev == SENT
        C = np.where(first, th, self.bxC)
        W = np.where(first, 0, self.bxW)
        chg = C != th
        Wc = s32(s32((C - th) << 8) + 10)
        Wd = s32(W - 1)
        Wd = np.where((Wd & 0xFF) == 0, 0, Wd)
        Wn = np.where(chg, Wc, np.where((W & 0xFF) != 0, Wd, W))
        op = s32((Wn >> 8) << self.bx_sh)
        return op, th, Wn, run

    def tick(self, angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol=-1):
        if self.bx.any():
            op, Cn, Wn, run = self.box_op(angle, ramp, req)
            self.dacc = np.where(self.bx, s32(op + self.dprev), self.dacc)
            self.bxC = np.where(self.bx & run, Cn, self.bxC)
            self.bxW = np.where(self.bx & run, Wn, self.bxW)
        return super().tick(angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol)
