#!/usr/bin/env python3
"""v72_lane_model.py -- the r24 / r26 aggregator lanes, mirroring the DECOMPILED arithmetic exactly.

Orchestrator-written 2026-08-04 from `mcp__ghidra__decompile_function(0x3aa2c)` on stock `code.bin`,
then cross-checked against the images byte by byte. Every constant below is READ FROM THE IMAGE,
never quoted from prose, and every line carries its instruction address.

🛑 WHAT THIS FILE EXISTS TO CORRECT
The kit has priced every rate-lane build since V62 as a single scalar "dose" (x1 / x2 / x4). That is
wrong in two independent ways, both visible in the decompile:

  1. THE GAIN IS A 2-D SURFACE, and the builds edited DIFFERENT PARTS OF IT.
     Records are selected by VEHICLE SPEED; the four Y values inside a record are a curve over the
     RATE index `gp-0x6ac0`, with breakpoints X = [0, 400, 1400, 3000] (gain_B) / [0, 400, 1600,
     3000] (gain_A). V69 and V70 edited **Y[0] and Y[1] only** -- the flat [0,400] plateau -- and
     left Y[2]/Y[3] at stock, so they deliver EXACTLY 1.000x anywhere the rate index exceeds ~1400.
     V62's `sar` and V67/V68's flat arm dose the WHOLE axis. Those are not the same experiment.

  2. THE TWO LANES DO NOT SHARE AN INPUT SCALING.
     r24 = deadband(r1 * gain_B >> 10)           -- one multiply
     r26 = ((avg(gp-0x69a4) * r1) >> 10) * gain_A >> 10   -- TWO multiplies, the extra one being
     the live LERP slope `a = gp-0x69a4/1024` from 0x355C6. So r26/r24 carries a factor `a` that
     nobody has measured, and a "2x on both lanes" edit is only equal-ratio, never equal-magnitude.

★ AND THE LANE INPUT IS NOT A VELOCITY. Both lanes are driven by `pcVar10 = clamp(gp-0x4f62,
  +/-5120)`, the TORSION-BAR TORQUE RATE -- d(driver torque)/dt -- not motor or column velocity.
  These lanes are derivative feedback on the torque sensor, i.e. phase lead in the torque loop. The
  gain-scheduling index `gp-0x6ac0` is a DIFFERENT signal (a motor/resolver rate magnitude, loaded
  `ld.hu` UNSIGNED @0x3AAC4), so the gain sweeps 0 -> peak -> 0 TWICE per oscillation cycle while
  the input swings once. That asymmetry is structural and is the natural home of a 2f companion to
  an f-mode.

USAGE
    python v72_lane_model.py                 # stock surfaces + the flown ladder + V72 candidates
    python v72_lane_model.py --image PATH    # evaluate one image
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

FW_ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
STOCK = FW_ROOT / "stock_fw_dump" / "code.bin"

TP = 0xBF000

# --- calibration addresses, all verified against the decompile of FUN_0003aa2c ------------------
C_DEADBAND_R24 = TP + 0x71F6   # 0xC61F6  = 3      r24's deadband; r26 has NONE
C_ARM3_R24     = TP + 0x7440   # 0xC6440  = 2048   taken when gp-0x671a >= 0xC64FA(=5) and gate OFF
C_MASK_R24     = TP + 0x7442   # 0xC6442  = 1024   taken when gp-0x671d != 0 -- OUTRANKS ALL
C_GATED_R24    = TP + 0x7446   # 0xC6446  = 512    taken when the gate is ON  (V67/V68/V71C: 5244)
C_ARM2_R26     = TP + 0x743E   # 0xC643E  = 1536   taken when gp-0x671a >= 5 and gate OFF
C_GATED_R26    = TP + 0x7444   # 0xC6444  = 512    taken when the gate is ON  (V71C: 3072)
C_XAXIS_SPEED  = TP + 0x7010   # 0xC6010  = [0, 640, 3200, 6400] counts = [0, 10, 50, 100] km/h
GATE_BYTE      = 0x3AA96       # 0xC5 -> ld.bu gp-0x683c (0 writers => gate DEAD)
                               # 0xFB -> ld.bu gp-0x6806 ("LKAS is applying") => engaged-only
SAR_R26        = 0x3AB76       # `sar 0xa,r6` immediate nibble; 0x9 doubles the r26 lane
SAR_R24        = 0x3AC20       # `sar 0xa,r6` immediate nibble; 0x9 doubles the r24 lane
RATE_FOLD      = 0x32C9        # @0x3AABx: rate index is FORCED TO ZERO at >= 13001

# gain_A (r26) records -- NOT mode-indexed, four hardcoded pointers formed at 0x3AECC..0x3AEE0
GAIN_A_RECS = [0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4]
# gain_B (r24) records -- MODE-INDEXED. These are the mode-10 entries, resolved by the orchestrator
# from the four ROM pointer arrays (u32, stride 4) at index m = 10.
GAIN_B_PTR_ARRAYS = [0xCBF5C, 0xCC044, 0xCC12C, 0xCC214]
MODE_DEFAULT = 10


def u16(b: bytes, a: int) -> int:
    return struct.unpack_from("<H", b, a)[0]


def u32(b: bytes, a: int) -> int:
    return struct.unpack_from("<I", b, a)[0]


def read_record(b: bytes, base: int):
    """count @+0x00, X[0..3] @+0x02, Y[0..3] @+0x0A, stride 0x14. [EVIDENCE: byte-read]"""
    n = u16(b, base)
    xs = [u16(b, base + 0x02 + 2 * j) for j in range(4)]
    ys = [u16(b, base + 0x0A + 2 * j) for j in range(4)]
    return n, xs, ys


def gain_b_records(b: bytes, mode: int = MODE_DEFAULT):
    return [u32(b, arr + mode * 4) for arr in GAIN_B_PTR_ARRAYS]


def lerp_int(x: int, xs, ys) -> int:
    """The integer LERP the aggregator performs inline (0x3AB80.. / 0x3AC28..).

    Below the first breakpoint it CLAMPS to ys[0]; above the last it CLAMPS to ys[-1]; between, it
    is the decompile's `((y[j+1]-y[j]) * (x - x[j])) / (x[j+1] - x[j]) + y[j]` -- C integer division,
    which truncates toward zero. All operands here are non-negative so `//` matches.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for j in range(len(xs) - 1):
        if xs[j] <= x <= xs[j + 1]:
            span = xs[j + 1] - xs[j]
            if span == 0:
                return ys[j]
            return ((ys[j + 1] - ys[j]) * (x - xs[j])) // span + ys[j]
    return ys[-1]


def surface(b: bytes, recs, v_counts: int, rate: int) -> int:
    """Two-stage: SPEED picks/interpolates between ADJACENT records (FUN_0003ad74), then the RATE
    index indexes within the resulting curve. `>= 3200 counts` reads only rec2/rec3 -- that is the
    structural highway guarantee V69/V70 relied on, and it is a property of the cross-axis."""
    cross = [u16(b, C_XAXIS_SPEED + 2 * j) for j in range(4)]
    curves = [read_record(b, r) for r in recs]
    if v_counts <= cross[0]:
        xs, ys = curves[0][1], curves[0][2]
    elif v_counts >= cross[-1]:
        xs, ys = curves[-1][1], curves[-1][2]
    else:
        for j in range(3):
            if cross[j] <= v_counts <= cross[j + 1]:
                w = v_counts - cross[j]
                span = cross[j + 1] - cross[j]
                xs = [curves[j][1][k] + ((curves[j + 1][1][k] - curves[j][1][k]) * w) // span
                      for k in range(4)]
                ys = [curves[j][2][k] + ((curves[j + 1][2][k] - curves[j][2][k]) * w) // span
                      for k in range(4)]
                break
    return lerp_int(rate, xs, ys)


def gain_r24(b: bytes, v_counts: int, rate: int, engaged: bool,
             mask_671d: bool = False, arm3_671a: bool = False) -> int:
    """The r24 selector, in the decompile's own priority order (0x3ABFA / 0x3AC04 / 0x3AC0E)."""
    if mask_671d:                                     # 0x3ABFE  gp-0x671d != 0 -- outranks all
        return u16(b, C_MASK_R24)
    gate_on = (b[GATE_BYTE] == 0xFB) and engaged      # 0xC5 => gp-0x683c, 0 writers => never
    if gate_on:                                       # 0x3AC08
        return u16(b, C_GATED_R24)
    if arm3_671a:                                     # 0x3AC12  gp-0x671a >= 5 (measured 0.000%)
        return u16(b, C_ARM3_R24)
    return surface(b, gain_b_records(b), v_counts, rate)


def gain_r26(b: bytes, v_counts: int, rate: int, engaged: bool,
             arm2_671a: bool = False) -> int:
    """The r26 selector (0x3AB5C / 0x3AB68). NOTE: no `gp-0x671d` mask arm exists on this side --
    gain_A is 2 arms + default, not 3."""
    gate_on = (b[GATE_BYTE] == 0xFB) and engaged
    if gate_on:                                       # 0x3AB5E
        return u16(b, C_GATED_R26)
    if arm2_671a:                                     # 0x3AB68
        return u16(b, C_ARM2_R26)
    return surface(b, GAIN_A_RECS, v_counts, rate)


def sar_shift(b: bytes, which: str) -> int:
    """V62's edit: the post-multiply `sar 0xa` immediate -> 0x9, i.e. one fewer right shift = x2.
    The immediate is the low nibble of the first byte of the 2-byte `sar imm5,reg` form."""
    addr = SAR_R26 if which == "r26" else SAR_R24
    return b[addr] & 0x1F


def lane_r24(b: bytes, r1: int, v_counts: int, rate: int, engaged: bool) -> int:
    """r24 = clamp( deadband( (clamp(gp-0x4f62,+/-5120) * gain_B) >> sar ), +/-0x2000 ) * polarity

    0x3AC20  sar 0xa,r6           <- V62 makes this 0x9
    0x3AC2x  deadband on 0xC61F6 = 3   (out-of-band contributes ZERO, in-band is shifted toward 0)
    0x3AC3E  ld.b -0x6752[gp]     polarity, shared with r26
    0x3AC42  clamp +/-0x2000      HARD saturating clip (not a zero gate)
    0x3AD5A  st.h r24 -> gp-0x6ada     0 readers / 1 writer image-wide == free telemetry
    """
    rate = rate if rate < RATE_FOLD else 0
    g = gain_r24(b, v_counts, rate, engaged)
    v = (r1 * g) >> sar_shift(b, "r24")
    dz = u16(b, C_DEADBAND_R24)
    if v > dz:
        v -= dz
    elif v < -dz:
        v += dz
    else:
        v = 0
    return max(-0x2000, min(0x2000, v))


def lane_r26(b: bytes, r1: int, v_counts: int, rate: int, engaged: bool, a_q10: int = 1024) -> int:
    """r26 = clamp( ((a * clamp(gp-0x4f62,+/-5120)) >> 10) * gain_A >> sar, +/-0x2000 ) * polarity

    `a` is avg(gp-0x69a4, previous) -- a live 10-segment LERP slope produced at 0x355C6 in
    FUN_000352b4. Its runtime magnitude has NEVER been measured; `a_q10` is therefore a FREE
    PARAMETER and every r26 number in this kit is conditional on it.
    0x3AB72  mul r8,r6            <- the INT32 headroom site: ((5120*65535)>>10) * gain_A
    0x3AB76  sar 0xa,r6           <- V62 makes this 0x9
    0x3AD4E  st.h r26 -> gp-0x6adc     0 readers / 1 writer image-wide
    ⚠ r26 is FORCED TO ZERO when gp-0x6b5e != 0 (because 0xC6138 == 1 makes that test always true).
    """
    rate = rate if rate < RATE_FOLD else 0
    g = gain_r26(b, v_counts, rate, engaged)
    v = (((a_q10 * r1) >> 10) * g) >> sar_shift(b, "r26")
    return max(-0x2000, min(0x2000, v))


# ------------------------------------------------------------------------------------------------
KMH = {0: 0, 5: 320, 10: 640, 15: 960, 20: 1280, 30: 1920, 50: 3200, 70: 4480, 100: 6400}
RATES = [0, 200, 400, 800, 1400, 2000, 3000, 6000]


def effective(b: bytes, lane: str, v_counts: int, rate: int, engaged: bool) -> float:
    """The lane's DELIVERED small-signal multiplier: the selected gain times the `sar` factor.

    🛑 Report THIS, not the lane output. Both lanes clip HARD at +/-0x2000, so a ratio taken on the
    output silently reads 1.000 for every build once the clip binds -- which is exactly the class of
    mistake that produced the kit's "r24 is near-inert" conclusion.
    """
    rate = rate if rate < RATE_FOLD else 0
    g = (gain_r26 if lane == "r26" else gain_r24)(b, v_counts, rate, engaged)
    return g * (2.0 ** (10 - sar_shift(b, lane)))


def report(tag: str, b: bytes, stock: bytes) -> None:
    print(f"\n=== {tag} ===  gate@0x3AA96={b[GATE_BYTE]:02X}  "
          f"sar_r26={sar_shift(b,'r26'):#x} sar_r24={sar_shift(b,'r24'):#x}  "
          f"C6444={u16(b,C_GATED_R26)} C6446={u16(b,C_GATED_R24)}")
    for arm_name, engaged in (("ENGAGED", True), ("MANUAL ", False)):
        for lane in ("r24", "r26"):
            row = []
            for kmh in (0, 10, 20, 50, 100):
                vc = KMH[kmh]
                cells = []
                for rt in (0, 400, 1400, 3000):
                    num = effective(b, lane, vc, rt, engaged)
                    den = effective(stock, lane, vc, rt, engaged)
                    cells.append(f"{(num/den if den else float('nan')):5.3f}")
                row.append(f"{kmh:>3}km/h[" + " ".join(cells) + "]")
            print(f"  {arm_name} {lane} x-vs-stock @rate 0/400/1400/3000: " + "  ".join(row))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, default=None)
    args = ap.parse_args()
    stock = STOCK.read_bytes()

    print("STOCK SURFACES  [EVIDENCE -- byte-read]")
    print("  gain_A (r26) records, X = RATE breakpoints, Y = gain:")
    for kmh, base in zip((0, 10, 50, 100), GAIN_A_RECS):
        _, xs, ys = read_record(stock, base)
        print(f"    {kmh:>3} km/h  0x{base:05X}  X{xs}  Y{ys}")
    print("  gain_B (r24) mode-10 records:")
    for kmh, base in zip((0, 10, 50, 100), gain_b_records(stock)):
        _, xs, ys = read_record(stock, base)
        print(f"    {kmh:>3} km/h  0x{base:05X}  X{xs}  Y{ys}")

    if args.image:
        report(args.image.name, args.image.read_bytes(), stock)
        return
    for name in ("stock", "62", "67", "69", "70", "71a", "71b", "71c"):
        p = STOCK if name == "stock" else FW_ROOT / f"_v{name}_plain_image.bin"
        report(name, p.read_bytes(), stock)


if __name__ == "__main__":
    main()
