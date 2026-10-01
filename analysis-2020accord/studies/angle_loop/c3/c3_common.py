# -*- coding: utf-8 -*-
r"""c3_common.py -- DESIGN C3 (angle-loop synthesis, 2026-10-01): the ONE source of truth for the C3 implementations.

ANALYSIS ONLY.  Builds no image file, no .rwd, flashes nothing, sends nothing, touches no fork file.

C3 = the round-2 panel's consensus graft: designer G's re-sized loop (fresh guarded D, Kd 48, G's speed table fitted under
the round-2 R2 box) carrying designer E2's integral policy (ICL 8192 + the angle-referenced I bound, two slopes, low-speed
cap = "A3").  The policy block is E2's assembled code; the table is G's data; the in-place set is rev2-A P2's (E1 E2 B2
A2 E4 HOOK V1 OPH) or, for the held-D fallback, rev2-A F2's (E1 E2 B2 A2 E4 HOOK V1 E5a E5b).

Every implementation below is scored ONLY by the panel-2 common scorers (panel2/score_freq.py, panel2/score_time.py),
imported unchanged by c3_score_freq.py / c3_score_time.py.  Nothing here grades itself.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

HERE = Path(__file__).resolve().parent                        # .../studies/angle_loop/c3
AL = HERE.parent                                              # .../studies/angle_loop
KIT = AL.parents[2]                                           # repo root
P2D = AL / "panel2"
E2D = P2D / "E2-integral-most-margin"
GD = P2D / "G-d-operand-and-margins"
SCR = KIT / "_scratch" / "angle_loop" / "c3-synthesis"
SCR.mkdir(parents=True, exist_ok=True)
for _q in (str(E2D), str(GD), str(AL / "panel" / "D-structure"), str(AL / "refute_c2r2_nonlinear"), str(AL)):
    if _q not in sys.path:
        sys.path.insert(0, _q)

V295 = Path(os.environ["ACCORD_FIRMWARE_ROOT"]) / "analysis-2020accord" / (
    "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
    "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V295_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"

GJ = json.loads((GD / "g_impls_frozen.json").read_text())
GROWS = {k: tuple(tuple(r) for r in v["rows"]) for k, v in GJ.items()}

# E2's policy dicts (e2_asm.IMPL), restated so a reader sees the constants without opening E2's file
POL_A3 = dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096)
POL_A2 = dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250)

# the implementations.  role: PRIMARY / FALLBACK / variant (scored, not offered as a build unless a ruling picks it)
IMPLS = {
    "C3-P": dict(src="G-P48", dop="fresh", kd=48, pol=POL_A3, icl=8192, role="PRIMARY",
                 note="G-P48 loop (fresh guarded D Kd 48, G-P48 table) + E2-A3 policy, ICL 8192"),
    "C3-F": dict(src="G-F24", dop="held", kd=24, pol=POL_A3, icl=8192, role="FALLBACK",
                 note="G-F24 loop (HELD D Kd 24 via E5, pol-free, no fresh-rate read) + E2-A3 policy, ICL 8192"),
    "C3-PA2": dict(src="G-P48", dop="fresh", kd=48, pol=POL_A2, icl=8192, role="variant (no low-speed cap, -18 B)",
                   note="C3-P without E2's low-speed cap (A2 policy)"),
    "C3-Pd": dict(src="G-P48d", dop="fresh", kd=48, pol=POL_A3, icl=8192, role="variant (table swap, ruling)",
                  note="C3-P code with G-P48d's table (b_q x ms_free declared, R3*)"),
    "C3-P44": dict(src="G-P44", dop="fresh", kd=44, pol=POL_A3, icl=8192, role="variant (table + Kd swap, ruling)",
                   note="C3-P code with G-P44's table and Kd 44 (10 % more 20 Hz margin)"),
}
CTRL = ["P2", "E2-A3", "G-P48", "G-F24"]          # same-batch controls whose SCORE-TIME cells must reproduce


def hexpath(cid):
    return HERE / f"c3_cave_{cid}.hex"


def v295_bytes():
    b = V295.read_bytes()
    assert hashlib.sha256(b).hexdigest() == V295_SHA, "not the V295 image"
    return b
