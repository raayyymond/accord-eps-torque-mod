# -*- coding: utf-8 -*-
r"""cgf_design.py -- Designer C (goal-first) candidate definitions.  ANALYSIS ONLY.

Two candidates, both on C1 rev 2's proven cave STRUCTURE (byte-identical 96-byte cave code for CGF-1; CGF-2 adds a
friction feed-forward block), differing from C1 rev 2 in:
  * D is read from the FRESH 1 kHz rate gp-0x6abe (0 extra cave bytes: the E5 ld.h displacement), NOT the held gp-0x6a56.
    EVIDENCE (Ghidra FUN_0003f776, this session): gp-0x6a56 = pol*(gp-0x6abe*48*1159)>>15, pol=-1 => gp-0x6a56 =
    -1.698*gp-0x6abe.  Fresh D keeps +Kd (no subr at 0x29EDE) and reads gp-0x6abe; the cal Kd scales x1.698 to match.
  * Kd_eff 28 (vs rev 2's 20): fresh D has no 100 Hz hold, so the 5-25 Hz anti-damping that capped rev 2's Kd is gone;
    M20 stays <= V295 up to Kd_eff ~32 (cgf_freq sweep).  Higher Kd damps the 1-3 Hz ring -> higher highway gain.
  * Higher highway Kp_eff, bounded by the CREDIBLE member set at PM>=30 (not by the least-credible corner).  The
    J~1.0 x reduced-damping family is a PRE-DECLARED CONCESSION caught by R3 (the 1.0-5.5 Hz ring, zeta<0.10).
  * CGF-2 adds a friction feed-forward (dead-zone break) in the cave: FF = sat(E'*Gff, +-Fff) on P only (clean I).

Kp_eff = Kp_base * G(v) / 256 ; Ki_eff = Ki_base * G(v) / 256 ; Kd quoted on the gp-0x6a56 (8/deg/s) scale.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
for _p in (str(AL), str(AL / "c1")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import c1_lib as C                            # noqa: E402  (make_table, cave_G, spd_counts)

KP_BASE = 112                                 # Kp record 0xE5384 Y x5 (= C1 rev 2 base)
KI_BASE = 56                                  # Ki 0xC63E6 (Ki/Kp = 0.5, fI = 7.8125*56/(2pi*112) = 0.622 Hz)
KD_EFF = 28                                   # Kd on the gp-0x6a56 (8/deg/s) scale
MU = 48 * 1159 / 32768                        # 1.698046875 (gp-0x6a56 / gp-0x6abe magnitude)
KD_CAL = round(KD_EFF * MU)                   # the Kd record 0xE5126 cell = 48 (delivers Kd_eff 28 on gp-0x6abe)
DB = 0                                        # 0xC62E4
ICL = 4096                                    # 0xC61BA (I>>7 clamp; CGF-2 lowers this -- see below)
DCL = 10240                                   # 0xC61B6 D clamp
FRZ_THR = 512                                 # cave immediate: freeze I when |gp-0x4f68| > 512

# ---- the G(v) knot table.  7 knots, DP-free hand pick, each knot's Kp_eff kept under the CREDIBLE-set envelope found by
# ---- cgf_freq (Kd 28, fresh D, concession = J1.0 x reduced-damping).  (v_mps, G); G = Kp_eff*256/112.
# ----   envelope max Kp_eff: 3.1:600 8:750 10:550 11.9:500 12.5:550 15:650 17:800 19:900 22:1000 26.9:1150
# ---- schedule Kp_eff (~0.90-0.95 of the envelope, smoothed):
# ----   3.1:555 8:690 10:530 11.9:490 12.5:520 15:620 17:740 19:835 22:940 26.9:1080
KNOTS = [(3.1, 1268), (8.0, 1576), (10.0, 1211), (12.0, 1131), (15.5, 1486), (19.0, 1908), (26.9, 2468)]
#   G at the knots -> Kp_eff: 555, 690, 530, 495, 650, 835, 1080 ; interpolated 11.9~497, 12.5~520, 17~742, 22~940


def table():
    return C.make_table(KNOTS)


def G_at(v):
    return C.cave_G(C.spd_counts(v), table())


def kp_eff(v):
    return KP_BASE * G_at(v) / 256.0


def ki_eff(v):
    return KI_BASE * G_at(v) / 256.0


# ---------------------------------------------------------------------------------------------------------------------
# CGF-2 friction feed-forward (the dead-zone break).  FF rides P only.  Sized from the breakaway torque Fc(v) measured on
# drive 1 (tap at dwell ends minus k^*theta).  Gff = the near-zero slope (T counts of FF per count of E'); Fff(v) = the
# saturation (~Fc(v) in T counts).  These are the design PLACEHOLDERS; drive 1 sets them (section 6 of the page).
# Fc(v) prior (ident, UNDER-estimated x0.46-0.58 at speed): 76/13.5/15.8/7.9/4.4 T at 3.1/8/11.9/17/26.9 m/s; bias-corr
# (bc) x1.8 low speed -> ~137 T at 3 m/s.  The FF saturates at the SMALLER of a safety cap (400 T) and Fff(v).
FF_CAP = 400                                  # T counts, hard safety cap on FF (never exceeds ~16% of the 2461 rail)
# Fff(v) placeholder = round(1.3 * Fc_bc(v)); only active <= ~10 m/s (above, friction is small and the FF is ~0)
FFF_KNOTS = [(3.1, 170), (6.0, 120), (8.0, 60), (10.0, 30), (12.5, 0)]   # (v_mps, Fff T counts); 0 above 12.5 m/s
GFF = 64                                       # T counts of FF per count of E' near zero (slope); FF = sat(E'*64>>? ...)
#   implemented in the cave as FF = clamp((E' * GFF) >> 6, -Fff, +Fff) -- a ramp of unit slope near 0 that saturates at
#   Fff within |E'| ~ Fff counts.  GFF/64 = 1.0 count of FF per count of E'.


def fff_at(v):
    import numpy as np
    xs = [k[0] for k in FFF_KNOTS]
    ys = [k[1] for k in FFF_KNOTS]
    return float(np.interp(v, xs, ys))


if __name__ == "__main__":
    print(f"CGF Kp_base {KP_BASE} Ki_base {KI_BASE} Kd_eff {KD_EFF} (cal Kd {KD_CAL}) ICL {ICL} DCL {DCL}")
    print("table rows (X u16, G u16, S s16 Q12):")
    for r in table():
        print("  ", r)
    print(f"{'v':>6} {'G':>6} {'Kp_eff':>7} {'Ki_eff':>7} {'T/deg':>6} {'Fff(C2)':>8}")
    for v in (3.1, 5, 8, 10, 11.9, 12.5, 15, 17, 19, 22, 26.9, 30):
        print(f"{v:6.1f} {G_at(v):6d} {kp_eff(v):7.1f} {ki_eff(v):7.1f} {kp_eff(v)/10:6.1f} {fff_at(v):8.1f}")
