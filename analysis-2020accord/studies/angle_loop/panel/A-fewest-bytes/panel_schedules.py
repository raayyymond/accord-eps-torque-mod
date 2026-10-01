# -*- coding: utf-8 -*-
"""panel_schedules.py -- DESIGNER A (fewest bytes): the SPEED RE-KEY angle loop, two implementations.

ANALYSIS ONLY.  Nothing here builds, flashes or sends.  Every claim the design page draws from this file is reproduced
by running it.

THE RE-KEY (the fewest-bytes lever): with E4 (0x29D6A -> ld.h -0x69ae) the map LERP output r13 is dead for the setpoint,
so the map walk 0x29CFC..0x29D68 is free.  Replace
    0x29CFC  mov 0xc9a88,r16      (6 bytes)  ->  ld.bu -0x6a5d[gp],r7 ; br 0x29D10     (4 + 2 = 6 bytes)
    0x29D18  sld.hu 0x2,ep,r10    (2 bytes)  ->  br 0x29D6A                            (2 bytes)
so r7 = r22 = (gp-0x6a5e >> 8) = speed/256 counts (1.111 m/s per count), and the Kp LERP (key zxh r7, 0x29DE8) and the
Kd LERP (key r22 byte) are now SPEED-indexed.  The Kp record (0xE5378 X/Y x5) and the Kd record (0xE511C X/Y x4) carry
the schedule as calibration.  NO cave.

A1 = the re-key + a FLAT Ki (one cal 0xC63E6).  Kp(v), Kd(v); Ki constant.
A2 = A1 + the SMALLEST cave that adds a SPEED-SCHEDULED Ki (the one thing A1 structurally cannot do: the integrator
     corner cannot track speed with a single Ki cal).  The cave hooks the Ki load (0x29D9C ld.hu 0x73e6[tp],r6) and
     walks a small speed->Ki table, returning Ki in r6.  P and D stay scheduled by the re-key; only I gains a schedule.

The loop gain CEILING is the same as C1 rev 2's (the GATE-2 envelope of the credible set does not care how Kp_eff is
delivered -- a cave's base*G or the re-key's record).  So Kp(v) targets C1 rev 2's Kp_eff curve, delivered by a 5-knot
speed LERP; Ki(v) in A2 targets Ki/Kp = 0.5 (C1 rev 2's corner).  Kd is flat 20 unless a schedule is explored.

The controller maths matches stab_lin.Ctl / harness_freq.Ctl with G = 256 (g = 1): the re-key puts the schedule in the
record, there is no cave G multiply.  Ctheta = (Kp(v)/256 + Ki(v)/32768/(1-z^-1)) * 80 * (1+z^-1) * hold ; Comega =
Kd(v) * hold.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                                      # .../studies/angle_loop
for _p in (str(AL), str(AL / "c1"), str(AL / "refute_stability"), str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("C1_VARIANT", "r2")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import c1_lib as C                                        # noqa: E402  (C1 rev 2 default -> the Kp_eff target curve)

SPD_PER_MPS = 3.6 * 64                                    # gp-0x6a5e counts per m/s


def spd_idx(v):
    """the re-key's key byte: (gp-0x6a5e >> 8) = round(v*3.6*64) >> 8."""
    return int(round(v * SPD_PER_MPS)) >> 8


def idx_to_v(i):
    return (i << 8) / SPD_PER_MPS                          # the speed a key-byte value represents (lower edge)


# the C1 rev 2 Kp_eff target curve (the envelope ceiling), read from c1_lib so the two designs share one ceiling
_TBL = C.c1_table()


def kp_eff_target(v):
    return C.KP_BASE * C.G_at(v, _TBL) / 256.0


# ----- the Kp record: 5 knots keyed on speed>>8.  X in key-byte units; Y = Kp_eff at the speed each knot represents. --
# A1 keeps the full envelope (scale 1.0); A2's constant Ki corner needs a trimmed envelope to hold PM on the aged
# combined members (panel_explore: at scale 1.0, Ki/Kp 0.5 leaves b/1.9*J1.0*tau6+h10 at 19.3 deg; at 0.72 it is 38.6).
KP_SCALE = {"A1": 1.00, "A2": 0.72}
KP_X = (2, 7, 10, 15, 24)                                  # 3.1 / 8.0 / 11.1 / 16.7 / 26.7 m/s
KP_Y_BASE = tuple(int(round(kp_eff_target(idx_to_v(x) if x > 0 else 0.5))) for x in KP_X)
KP_Y = KP_Y_BASE                                           # A1's record (scale 1.0)
KP_Y_A2 = tuple(int(round(y * KP_SCALE["A2"])) for y in KP_Y_BASE)

# ----- the Kd record: 4 knots keyed on speed>>8.  Flat 20 is C1 rev 2's choice; the 4 knots let HF anti-damping be
#       trimmed at highway.  A1 default = flat 20.  'kd_sched' trims the top knot. ------------------------------------
KD_X = (2, 7, 15, 24)                                      # 3.1 / 8.0 / 16.7 / 26.7 m/s
# Kd schedules the 1 kHz D-on-rate (edit E5).  D damps the 1.6-3 Hz wheel mode (hard-turn jerk) but anti-damps 13-25 Hz
# through the output lag + delay (Re(T/w), the V291/V292 class).  So: MODERATE Kd at low-mid speed (hard turns happen
# <= 20 m/s, HF lines are absent there), LOW Kd at highway (where the record's 13-17 / 20 Hz lines live).  The RE-KEY
# gives Kd(v) for free (both LERPs re-keyed); A1 and A2 use it.  KD_SCHED is the default; KD_FLAT is a control.
KD_SCHED = (20, 18, 14, 10)
KD_FLAT = (16, 16, 16, 16)

# ----- Ki --------------------------------------------------------------------------------------------------------------
# A1: one flat Ki = 80 (panel_explore: keeps the WHOLE credible set stable with tier A >= 45, tier B >= 30; a higher
#     flat Ki goes unstable on the aged combined members, a lower one gives up low-frequency tracking).  A2: Ki(v) from
#     a small cave table, Ki/Kp = KI_OVER_KP, on the TRIMMED (A2) Kp.
A1_KI_FLAT = 80
KI_OVER_KP = 0.5                                           # A2 corner (constant PI corner, = C1 rev 2's Ki/Kp)
A2_KI_X = KP_X                                             # the cave's Ki table (5 knots), same key as Kp
A2_KI_Y = tuple(int(round(KI_OVER_KP * y)) for y in KP_Y_A2)


def _lerp_int(X, Y, u):
    """Honda's integer LERP (flat below X[0] / at-or-above X[-1]); u, X in key-byte units."""
    X = list(X); Y = list(Y)
    if u <= X[0]:
        return Y[0]
    if u >= X[-1]:
        return Y[-1]
    i = 0
    while not (u <= X[i + 1]):
        i += 1
    num = (Y[i + 1] - Y[i]) * (u - X[i])
    den = X[i + 1] - X[i]
    q = abs(num) // abs(den)
    return Y[i] + (q if (num < 0) == (den < 0) else -q)


def kp_of(v, impl="A1"):
    return _lerp_int(KP_X, KP_Y if impl == "A1" else KP_Y_A2, spd_idx(v))


def kd_of(v, sched=True):
    return _lerp_int(KD_X, KD_SCHED if sched else KD_FLAT, spd_idx(v))


def ki_of(v, impl, ki_flat=A1_KI_FLAT):
    if impl == "A1":
        return int(ki_flat)
    return _lerp_int(A2_KI_X, A2_KI_Y, spd_idx(v))


def stab_ctl(v, impl, d=2, extra_age=0, ki_flat=A1_KI_FLAT, kd_sched=False):
    """stab_lin.Ctl at the re-key operating point: G = 256 (no cave scaling), kp/ki/kd from the records."""
    import stab_lin as S
    return S.Ctl(v, kp=kp_of(v, impl), ki=ki_of(v, impl, ki_flat), kd=kd_of(v, kd_sched), d=d, extra_age=extra_age,
                 G=256)


def hf_ctl(v, impl, ki_flat=A1_KI_FLAT, kd_sched=False, **kw):
    """harness_freq.Ctl at the re-key operating point (angle op; G baked into kp/ki already, so pass raw record values)."""
    import harness_freq as HF
    return HF.Ctl(op="angle", a=0, b=8192, fb_op="sum", kp=float(kp_of(v, impl)), ki=float(ki_of(v, impl, ki_flat)),
                  kd=float(kd_of(v, kd_sched)), d_src="rate", **kw)


if __name__ == "__main__":
    print("RE-KEY SCHEDULES (Designer A -- fewest bytes)")
    print(f"  Kp record  X(key) {KP_X}  Y {KP_Y}")
    print(f"  Kd record  X(key) {KD_X}  Y flat {KD_FLAT} / sched {KD_SCHED}")
    print(f"  A2 Ki cave X(key) {A2_KI_X}  Y {A2_KI_Y}")
    print(f"{'v':>6} {'idx':>4} {'Kp(v)':>7} {'Kp_eff*':>8} {'Kd':>4} {'A1 Ki':>6} {'A2 Ki':>6}")
    for v in (3, 5, 8, 10, 11.9, 12.5, 15, 17, 19, 22, 26, 30):
        print(f"{v:6.1f} {spd_idx(v):4d} {kp_of(v):7d} {kp_eff_target(v):8.1f} {kd_of(v):4d} "
              f"{ki_of(v,'A1'):6d} {ki_of(v,'A2'):6d}")
