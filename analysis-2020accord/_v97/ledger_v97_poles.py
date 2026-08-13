#!/usr/bin/env python3
"""V97 POLE LEDGER — phase margin vs return-trajectory speed for every IIR pole in the engaged
low-speed torque path.  Mirrors the DECOMPILED INTEGER ARITHMETIC exactly; dB/Hz interpretation comes
after the code, never instead of it.

The two clauses of the operator's crux pull opposite ways:
  (1) the engaged return should be as SMOOTH as manual  -> more damping helps
  (2) the engaged return should be FASTER than manual    -> more damping hurts
A PURE DISSIPATION lever buys (1) and costs (2).  A PURE LAG-REMOVAL lever buys BOTH, because it
takes phase back without changing DC gain.  This script prices which is which.
"""
import math

FS = 1000.0            # control task rate, Hz  (task 1 = 1 kHz, established)
BAND = [6.0, 7.79, 9.0]            # the ratchet band
RETURN_BAND = [0.5, 1.0, 2.0]      # the return-to-centre trajectory


def onepole(alpha_num, f, den=1024):
    """EXACT discrete one-pole matching  y += ((x - y) * A) >> 10   (0xC63AC = A).

        y[n] = (1-a).y[n-1] + a.x[n]        a = A/1024
        H(z) = a / (1 - (1-a) z^-1)         z = e^{j.2.pi.f/fs}

    DC gain is a/(1-(1-a)) = 1 for ANY a in (0,1] -> a is a PURE POLE-POSITION knob, NOT a gain.
    """
    a = alpha_num / den
    w = 2 * math.pi * f / FS
    re = 1 - (1 - a) * math.cos(w)
    im = (1 - a) * math.sin(w)
    mag = a / math.hypot(re, im)
    phase = -math.atan2(im, re)
    return mag, math.degrees(phase)


def corner(alpha_num, den=1024):
    """-3 dB corner, solved numerically against the exact discrete response."""
    lo, hi = 0.01, FS / 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if onepole(alpha_num, mid, den)[0] > 1 / math.sqrt(2):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def deadzone(alpha_num, den=1024):
    """THE NONLINEARITY A LINEAR ANALYSIS MISSES.

    The firmware line is    gp-0x374c += ((target - gp-0x374c) * A) >> 10
    `>>` on V850 is an ARITHMETIC shift (floor, toward -inf), not truncation toward zero.  So:
      * a POSITIVE error e with e*A < 1024 floors to 0   -> the accumulator STALLS
      * a NEGATIVE error e with |e|*A < 1024 floors to -1 -> it still creeps
    The filter is therefore ASYMMETRIC at small error: it can always walk down, but cannot walk up
    until the error exceeds ceil(1024/A).  That is a rectifying stiction, and it shrinks as A rises.
    """
    stall_up = math.ceil(den / alpha_num)          # smallest +error that still moves the state
    return stall_up


def step_settle(alpha_num, frac=0.90, den=1024):
    """Ticks to reach `frac` of a unit step — the return-trajectory speed proxy."""
    a = alpha_num / den
    return math.log(1 - frac) / math.log(1 - a)


def main():
    print("=" * 78)
    print("0xC63AC — the Path-2 accumulator pole.  gp-0x374c += ((target-gp-0x374c) * A) >> 10")
    print("=" * 78)
    print(f"{'A':>6}{'alpha':>9}{'corner':>9}  | {'phase @6/7.79/9 Hz':^28} | "
          f"{'phase @0.5/1/2 Hz':^24}")
    print("-" * 78)
    for A in (102, 154, 205, 256, 307, 410, 512):
        ph = "/".join(f"{onepole(A, f)[1]:6.1f}" for f in BAND)
        rt = "/".join(f"{onepole(A, f)[1]:5.1f}" for f in RETURN_BAND)
        tag = "  <== STOCK, and VIRGIN on all 89 images" if A == 102 else ""
        print(f"{A:>6}{A/1024:>9.4f}{corner(A):>8.2f}Hz  | {ph:^28} | {rt:^24}{tag}")

    print()
    print("DC gain check (must be 1.000 for every A, or it is a gain lever not a pole lever):")
    print("   " + "  ".join(f"A={A}: {onepole(A, 1e-6)[0]:.6f}" for A in (102, 205, 410)))

    print()
    print("Return-trajectory speed — ticks to 90% of a step (lower = FASTER return):")
    for A in (102, 205, 410):
        t = step_settle(A)
        print(f"   A={A:>4}  {t:6.1f} ticks = {t/FS*1000:6.1f} ms   "
              f"({step_settle(102)/t:.2f}x faster than stock)")

    print()
    print("ASYMMETRIC INTEGER DEAD ZONE (arithmetic >> floors toward -inf):")
    for A in (102, 205, 410):
        print(f"   A={A:>4}  smallest POSITIVE error that moves the accumulator: "
              f"{deadzone(A):>3} counts   (negative errors always creep at -1)")

    print()
    print("=" * 78)
    print("0xC644A — the D-path IIR.  NOT virgin: V43 -> 32, V44 revert, V49 -> 64, V49p revert.")
    print("=" * 78)
    print(f"{'A':>6}{'alpha':>9}{'corner':>9}  | {'phase @6/7.79/9 Hz':^28}")
    print("-" * 78)
    for A, note in ((1024, "STOCK = UNITY = NO FILTER AT ALL (pole at z=0)"),
                    (64, "V49 flew this"), (32, "V43 flew this")):
        ph = "/".join(f"{onepole(A, f)[1]:6.1f}" for f in BAND)
        print(f"{A:>6}{A/1024:>9.4f}{corner(A):>8.2f}Hz  | {ph:^28}  {note}")
    print()
    print("  ^ NOTE THE DIRECTION.  At A=1024 the D-path IIR is a pass-through: alpha=1 means")
    print("    y[n] = x[n], zero lag.  V43/V49 LOWERED it, which ADDS lag to the derivative —")
    print("    the WRONG WAY for phase margin.  There is no headroom to raise it: 1024 is the max.")


if __name__ == "__main__":
    main()
