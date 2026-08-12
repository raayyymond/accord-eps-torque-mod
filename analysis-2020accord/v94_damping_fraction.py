#!/usr/bin/env python3
r"""V94 — why cutting `0xCBE74` made the car shake: the lane is a DAMPER, not pure inertia.

🛑🛑 SUPERSEDED BY MEASUREMENT, 2026-08-12 — THE NUMBERS BELOW ARE WRONG. DO NOT CITE THEM.
    This file computes the PRODUCER's filter phase against MOTOR rate and gets +75 deg / 26 %
    dissipative at 7.8 Hz.  The DELIVERED lane, measured against WHEEL rate on two independent
    drives (omega-partialled, shuffled control, r77/V90 and r78/V91), sits at **+137 deg / +139 deg
    => |cos| = 0.73**, contributing **+518 / +565 counts of POSITIVE Re(Z)** at 6-9 Hz.
    `gp-0x6b26` is a REAL 6-9 Hz damper, not a 26 % one.

    The gap is the PLANT: this file's chain stops at the firmware lane; the measurement includes the
    torsion bar and column between motor and wheel.  A producer's transfer function is NOT the lane's
    contribution to impedance at the wheel, and no amount of care with the image's filter coefficients
    closes that gap.

    WHAT SURVIVES: the two pole coefficients read from the image (`0xC643C`=37>>7, `0xC40DC`=22>>6,
    both frozen across every build), the integer mirror of `FUN_00036c12`'s delivered-cell arithmetic
    in `b26()`, the cross-build gain table, and the qualitative conclusion that the lane is
    DISSIPATIVE rather than purely inertial -- which the measurement strengthens, not weakens.
    WHAT DOES NOT: every number in the "DISSIPATIVE FRACTION" table, and the claim that the lane
    "structurally cannot damp 6-9 Hz".  It can, and it does.
    See `memory/feedback-reducing-a-gain-is-not-a-safety-class.md` for why this matters as a rule:
    the lesson is not "do the arithmetic", it is "measure the delivered lane".
    🛑 The task rate this file sweeps over is ALSO unresolved -- the task-5 = 100 Hz derivation was
    RETRACTED on 2026-08-12.  Task 1 = 1 kHz stands (two independent methods).


Standing operator instruction (CLAUDE.md, 2026-07-28): mirror the decompiled arithmetic EXACTLY —
integer `>>`, the real Q-format, the real branch conditions, constants byte-read LITTLE-ENDIAN,
each line annotated with its instruction address.  Hz/dB interpretation comes AFTER the code.

THE CLAIM THIS FILE TESTS
    `docs/STATE.md` and `memory/accord-gp6b26-is-inertia-not-damping.md` say `gp-0x6b26 = -K*alpha`
    is "(J+K)*alpha: apparent inertia RISES, nothing is dissipated", and V93/V94 LOWERED the gain on
    that basis.  On-car, V94 made grinding/vibration dramatically worse.

    The claim is wrong, and this file shows why: `gp-0x6c2c` is a first difference **sandwiched
    between two low-pass poles**.  A first difference leads rate by +90 deg; each pole subtracts
    phase.  So `-K*gp-0x6c2c` has a component IN PHASE WITH RATE — genuinely dissipative viscous
    damping — equal to cos(net_phase) of the term's magnitude, and that fraction GROWS with
    frequency.  The lane is a high-frequency damper that is nearly invisible at steering-feel
    frequencies.  Cutting it 2-4x removes the damper.

🛑 THE ANSWER SCALES WITH THE TASK RATE, WHICH THE KIT HAS NOT RESOLVED.
    `memory/control-task-tick-confirmed-1khz` confirms ~1000 Hz for the CONTROL task and explicitly
    leaves the ASSIST-SHAPING task rate open.  Every number here is therefore printed as a SWEEP
    over plausible rates, not as a single value.  Pin the rate and the sweep collapses to one row.
"""
import math
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
STOCK = (FW / "stock_fw_dump" / "code.bin").read_bytes()
V92 = (FW / "_v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4"
            "_plain_image.bin").read_bytes()
V94 = (FW / "_v94_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75-427.SAR1"
            "_plain_image.bin").read_bytes()
TP = 0xBF000
FRICTION_PTR_ARRAY = 0xCBE74
CNT_PER_KMH = 64.0

# The two poles, byte-read little-endian from the image.  Shift amounts are the REAL ones.
A_RATE_ADDR, A_RATE_SHIFT = TP + 0x743C, 7   # 0xC643C  0x415E0 mul / 0x415E6 sar 0x7
A_EMA_ADDR, A_EMA_SHIFT = TP + 0x50DC, 6     # 0xC40DC  0x41632 mul / 0x4163A sar 0x6

BANDS = (2.0, 4.0, 6.0, 7.8, 9.0, 12.0, 15.0, 18.0, 21.0, 26.0, 31.0, 38.0)
RATES = (1000.0, 500.0, 250.0, 200.0, 100.0)


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def pole_a(img, addr, shift):
    """`y += ((x - y) * alpha) >> shift`  =>  one-pole IIR with coefficient alpha / 2**shift."""
    return u16(img, addr) / float(1 << shift)


def pole_phase_deg(a, f, fs):
    """Phase of `y += a*(x-y)` at f.  Exact for the discrete pole at (1-a)."""
    w = 2.0 * math.pi * f / fs
    num_i = a * math.sin(w)                       # H = a / (1 - (1-a)e^-jw)
    den_r = 1.0 - (1.0 - a) * math.cos(w)
    den_i = (1.0 - a) * math.sin(w)
    return math.degrees(math.atan2(-(den_i * a), a * den_r)) if False else \
        -math.degrees(math.atan2(den_i, den_r)) + 0.0 * num_i


def diff_phase_deg(f, fs):
    """`d = new - old` is (1 - z^-1): magnitude 2 sin(pi f/fs), phase +90 - 180 f/fs degrees."""
    return 90.0 - 180.0 * f / fs


def net_phase_vs_rate(img, f, fs):
    """Phase of gp-0x6c2c relative to motor RATE.  +90 = pure acceleration, 0 = pure rate."""
    a1 = pole_a(img, A_RATE_ADDR, A_RATE_SHIFT)
    a2 = pole_a(img, A_EMA_ADDR, A_EMA_SHIFT)
    return diff_phase_deg(f, fs) + pole_phase_deg(a1, f, fs) + pole_phase_deg(a2, f, fs)


def friction_gain(img, mode, speed_counts):
    """FUN_00036c12 0x36C4A..0x36CB0 — the LERP, nominal path (both gates passing)."""
    rec = struct.unpack_from("<I", img, FRICTION_PTR_ARRAY + mode * 4)[0]
    n = s16(img, rec)
    X = [s16(img, rec + 2 + 2 * i) for i in range(n)]
    Y = [s16(img, rec + 8 + 2 * i) for i in range(n)]
    v = speed_counts
    if v <= X[0]:
        return Y[0]
    if v >= X[-1]:
        return Y[-1]
    for i in range(1, n):
        if v < X[i]:
            return (Y[i] - Y[i - 1]) * (v - X[i - 1]) // (X[i] - X[i - 1]) + Y[i - 1]
    return Y[-1]


def b26(img, accel, gain):
    """FUN_00036c12 0x36CBE..0x36CE4 — the delivered cell, integer-exact."""
    r14 = (accel + 0x7D00) & 0xFFFFFFFF                 # 0x36C26  addi 0x7d00,r9,r14
    r13 = 0 if r14 >= 0xFA01 else accel                 # 0x36C2C  cmovnc  -> +-32000 window
    r13 = (r13 * gain) >> 6                             # 0x36CBE mulh / 0x36CC4 sar 0x6
    prod = r13 * 0x111                                  # 0x36CC6  mul (HIGH DISCARDED)
    prod &= 0xFFFFFFFF
    prod = prod - (1 << 32) if prod & 0x80000000 else prod
    r6 = prod >> 0x12                                   # 0x36CCA  sar 0x12,r6
    clamp = s16(img, TP + 0x507E)                       # 0x36C34 ld.h -> 0xC407E = 511
    return max(-clamp, min(clamp, r6))


if __name__ == "__main__":
    a1 = pole_a(STOCK, A_RATE_ADDR, A_RATE_SHIFT)
    a2 = pole_a(STOCK, A_EMA_ADDR, A_EMA_SHIFT)
    print("=" * 100)
    print("  THE TWO POLES, byte-read little-endian from the STOCK image")
    print("=" * 100)
    print(f"    0xC643C alpha_rate = {u16(STOCK, A_RATE_ADDR):5d}  >>{A_RATE_SHIFT}  =>  a = {a1:.5f}")
    print(f"    0xC40DC alpha_ema  = {u16(STOCK, A_EMA_ADDR):5d}  >>{A_EMA_SHIFT}  =>  a = {a2:.5f}")
    print("    (identical in stock / V92 / V94 -- no build has ever moved either)")

    print("\n" + "=" * 100)
    print("  DISSIPATIVE FRACTION of -K*gp-0x6c2c = cos(phase vs RATE).")
    print("  100 % = pure viscous damper.  0 % = pure virtual inertia.")
    print("=" * 100)
    hdr = "    " + f"{'f (Hz)':>7}" + "".join(f"{int(fs):>10} Hz" for fs in RATES)
    print(hdr)
    for f in BANDS:
        row = f"    {f:7.1f}"
        for fs in RATES:
            frac = math.cos(math.radians(net_phase_vs_rate(STOCK, f, fs)))
            row += f"{frac * 100:11.1f}%"
        print(row)
    print("\n    🛑 The assist-shaping task rate is UNRESOLVED.  At 1000 Hz the lane is mostly")
    print("       inertia with a real ~26 % damper at 7.8 Hz; at 200 Hz it is almost a PURE")
    print("       damper.  Every row above says the same thing qualitatively: the dissipative")
    print("       fraction is NON-ZERO and RISES WITH FREQUENCY.  'Nothing is dissipated' is")
    print("       false at every plausible rate.")

    print("\n" + "=" * 100)
    print("  WHAT V94 REMOVED — the gain, vs speed, on the record each build moved")
    print("=" * 100)
    print(f"    {'km/h':>5} | {'m24 stock':>10} {'m24 V94':>9} {'ratio':>6} | "
          f"{'m26 stock':>10} {'m26 V92':>9} {'m26 V94':>9} {'V94/V92':>8}")
    for k in (0, 20, 40, 60, 80, 100):
        vc = int(k * CNT_PER_KMH)
        s24, n24 = friction_gain(STOCK, 24, vc), friction_gain(V94, 24, vc)
        s26 = friction_gain(STOCK, 26, vc)
        v26_92, v26_94 = friction_gain(V92, 26, vc), friction_gain(V94, 26, vc)
        print(f"    {k:>5} | {s24:>10} {n24:>9} {n24 / s24:>6.2f} | "
              f"{s26:>10} {v26_92:>9} {v26_94:>9} {v26_94 / v26_92:>8.3f}")

    print("\n" + "=" * 100)
    print("  DELIVERED |gp-0x6b26| at 50 km/h -- the damper the wheel actually feels")
    print("=" * 100)
    vc = int(50 * CNT_PER_KMH)
    g24s, g24n = friction_gain(STOCK, 24, vc), friction_gain(V94, 24, vc)
    g26_92, g26_94 = friction_gain(V92, 26, vc), friction_gain(V94, 26, vc)
    print(f"    {'gp-0x6c2c':>10} {'m24 stock':>10} {'m24 V94':>9} | "
          f"{'m26 V92':>9} {'m26 V94':>9}")
    for accel in (250, 500, 1000, 2000, 4000, 8000, 16000, 32000):
        print(f"    {accel:>10} {b26(STOCK, accel, g24s):>10} {b26(V94, accel, g24n):>9} | "
              f"{b26(V92, accel, g26_92):>9} {b26(V94, accel, g26_94):>9}")
    print("\n    Route 77 measured max |gp-0x6b26| = 319.1 with clamp duty 0.000000 in EVERY")
    print("    stratum, so the +-511 clamp at 0xC407E was never entered and cannot explain the")
    print("    x1.5 null.  The realised acceleration range is therefore the LOW rows above.")
