# -*- coding: utf-8 -*-
r"""e1_policies.py -- the E1 integral-policy implementations evaluated by this designer (PANEL 2, fewest bytes).

Each Policy is the integral section of the C2 rev2 P-skeleton (fresh-rate D Kd 34, 6-knot G, Kp 112, Ki 56) with ONE
change to the integral authority/bound.  Bytes are counted relative to the C2 rev2-A PRIMARY P2 (156-byte cave, 200 B
written) in the design doc; here only the DELTA bytes of the integral policy are stated.  ANALYSIS ONLY."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_lane as E1

OUT = E1.KIT / "_scratch" / "angle_loop" / "E1-integral-fewest-bytes"
_D = json.load(open(OUT / "icl_design.json")) if (OUT / "icl_design.json").exists() else {"sched_rows": []}

# the E1b speed-scheduled ICL table.  Hand-set from e1_design_icl (a_lat ~1.6 nominal), with:
#  - the 10-12.5 m/s dip kept BELOW the current 4096 (the lurch is worst there), so the lurch does not grow at its worst speed
#  - the 15-19 m/s peak raised to 6144 (covers a_lat 1.5 at 17 m/s = 5925), where turn-hold fails
#  - low speed (< 8 m/s, outside the goal) capped at 5120 to bound the low-speed lurch
#  rows: (X u16 = gp-0x6a5e counts 230.4/m/s, ICL u16)
ICL_SCHED = [(714, 5120), (1843, 5120), (2304, 3840), (2707, 3584), (3571, 6144), (4032, 6144), (6198, 3072),
             (0xFFFF, 3072)]
# a VARIANT with a linear-interp S column would cost more bytes; this walk uses the G-walk's own piecewise-linear form.


POLICIES = {
    # reference: the C2 rev2-A PRIMARY exactly (fails F1 by construction)
    "P2base": E1.Policy("P2base", icl_flat=4096, reset_firm=None, kp=112,
                        note="C2 rev2-A P2 as-is (ICL 4096): the F1 baseline"),
    # E1a: FLAT ICL raised + firm-hand RESET.  bytes: +0 code (ICL is a cal) + ~12 cave B for the reset.
    "E1a": E1.Policy("E1a", icl_flat=8192, reset_firm=1536, kp=112,
                     note="flat ICL 8192 (cal) + firm-hand reset I:=0 at |tq|>1536 (+~12 cave B): FEWEST BYTES"),
    "E1a_6k": E1.Policy("E1a_6k", icl_flat=6144, reset_firm=1536, kp=112,
                        note="flat ICL 6144 (lighter authority) + reset"),
    "E1a_noreset": E1.Policy("E1a_noreset", icl_flat=8192, reset_firm=None, kp=112,
                             note="flat ICL 8192, NO reset: shows the lurch cost of raising ICL alone"),
    # E1b: SPEED-SCHEDULED ICL (one more table column) + firm reset.  bytes: + table col + walk/inject code.
    "E1b": E1.Policy("E1b", icl_flat=None, icl_table=ICL_SCHED, reset_firm=1536, kp=112,
                     note="speed-scheduled ICL (low at the 10-12.5 lurch band, 6144 at 15-19) + reset"),
    "E1b_noreset": E1.Policy("E1b_noreset", icl_flat=None, icl_table=ICL_SCHED, reset_firm=None, kp=112,
                             note="speed-scheduled ICL, NO reset: does the schedule alone bound the lurch?"),
    # E1c: SPLIT AUTHORITY -- raise Kp, keep I small.  Shown to be forbidden by the credible set (GATE 2).
    "E1c": E1.Policy("E1c", icl_flat=3072, reset_firm=1536, kp=200,
                     note="split: Kp 200 (P carries the curve), ICL 3072 small -- GATE 2 check in e1_gate2"),
    # E1d: BLEED by |tq| band (soft reset) instead of a hard reset.
    "E1d": E1.Policy("E1d", icl_flat=8192, reset_firm=None, bleed_lo=256, bleed_sh=3, kp=112,
                     note="flat ICL 8192 + soft bleed I-=I>>3 while 256<|tq|<=512 (below freeze)"),
    # E1a with a LOWERED freeze threshold (same bytes: just a different cave immediate) to catch the light hand.
    "E1a_fz384": E1.Policy("E1a_fz384", icl_flat=8192, reset_firm=1536, freeze_thr=384, kp=112,
                           note="flat ICL 8192 + freeze at 384 (not 512) + firm reset: bound the light hand for free"),
    "E1a_fz320": E1.Policy("E1a_fz320", icl_flat=8192, reset_firm=1536, freeze_thr=320, kp=112,
                           note="flat ICL 8192 + freeze at 320 + firm reset"),
    # E1b with the firm reset but a shallower low-speed cap, for the robustness comparison
    "E1b_fz384": E1.Policy("E1b_fz384", icl_flat=None, icl_table=ICL_SCHED, reset_firm=1536, freeze_thr=384, kp=112,
                           note="scheduled ICL + freeze 384 + reset"),
}

# column structures: P (fresh-rate D) and F (held-rate D); both use the same integral policy
IMPLS = ("P2", "F2")
