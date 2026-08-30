#!/usr/bin/env python3
r"""`0xC63AC` -- Path-2's shared one-pole IIR, both directions, mirrored from the integer update form.

WHY THIS EXISTS
    The ratchet is a lightly-damped mode with zeta = 0.017-0.036 => phase margin ~= 100*zeta =
    1.7-3.6 deg IF it is a closed-loop pole.  `0xC63AC` is the only never-written, cal-only pole on
    that loop.  Lowering its corner ADDS lag (destabilising if Path 2 is the pole); raising it
    REMOVES lag (stabilising) at the cost of passing more HF from the 6-lane sum.
    This file quantifies both directions so the trade is a number, not an argument.

THE ARITHMETIC, as the firmware does it (integer, Q10, `/1024` NOT `/4096`)
    `FUN_00038148`, outer EMA.  Cal read `ld.hu 0x73ac[tp],rN`, tp = 0xBF000 => tp+0x73AC = 0xC63AC.
    Same idiom the kit hand-decoded one function over at `FUN_00036682` (0x367F6-0x36820):

        y += ((x << 10) - y) * a >> 10          # y is the Q10 state
        out = y >> 10

    which is the standard one-pole EMA with alpha = a/1024, i.e.

        H(z) = alpha / (1 - (1-alpha) z^-1)

    Control tick is 1 kHz (`control-task-tick-confirmed-1khz`: the ON-CAR STEER_STATUS=4 dwell ALONE -- the OSTM0 route is REFUTED, PCLK is 40 MHz).

🛑 The integer mirror below is run against the float transfer function as its own control -- if the
   quantised recursion and the analytic H(z) disagree, the table is wrong and says so.
"""
import cmath
import math
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 1000.0
STOCK = 102
FREQS = [1.0, 3.0, 7.79, 12.8, 15.0, 21.09, 27.4]
ALPHAS = [26, 51, 102, 204, 410, 820]


def corner(a):
    """-3 dB corner of the one-pole EMA, exact (not the alpha*fs/2pi approximation)."""
    al = a / 1024.0
    # |H(w)|^2 = al^2 / (1 - 2(1-al)cos w + (1-al)^2); solve |H|^2 = 1/2 * |H(0)|^2 = 1/2
    b = 1.0 - al
    # cos w = (1 + b^2 - 2*al^2) / (2b)   from setting |H|^2 = 1/2
    c = (1.0 + b * b - 2.0 * al * al) / (2.0 * b)
    if not -1.0 <= c <= 1.0:
        return float("nan")
    return math.acos(c) * FS / (2.0 * math.pi)


def H(a, f):
    al = a / 1024.0
    z = cmath.exp(2j * math.pi * f / FS)
    return al / (1.0 - (1.0 - al) / z)


def integer_probe(a, f, n=200000, amp=4096):
    """Drive the REAL integer recursion with a sinusoid; recover gain and phase by correlation."""
    y = 0
    xs, ys = [], []
    w = 2.0 * math.pi * f / FS
    for k in range(n):
        x = int(round(amp * math.sin(w * k)))
        y += ((x << 10) - y) * a >> 10
        if k > n // 2:                                     # discard the transient
            xs.append(x)
            ys.append(y >> 10)
    m = len(xs)
    ref_s = [math.sin(w * (k + n // 2 + 1)) for k in range(m)]
    ref_c = [math.cos(w * (k + n // 2 + 1)) for k in range(m)]
    si = sum(ys[k] * ref_s[k] for k in range(m)) * 2.0 / m
    co = sum(ys[k] * ref_c[k] for k in range(m)) * 2.0 / m
    return abs(complex(si, co)) / amp, math.degrees(math.atan2(co, si))


print(f"`0xC63AC` one-pole EMA, fs = {FS:.0f} Hz, stock = {STOCK} (alpha = {STOCK/1024:.5f})\n")
print(f"{'a':>5} {'alpha':>8} {'corner Hz':>10}   " +
      "  ".join(f"{f:>6.2f}Hz" for f in FREQS))
print("-" * (28 + 10 * len(FREQS)))
for a in ALPHAS:
    tag = "  <- STOCK" if a == STOCK else ""
    mags = []
    phs = []
    for f in FREQS:
        h = H(a, f)
        mags.append(20 * math.log10(abs(h)))
        phs.append(math.degrees(cmath.phase(h)))
    print(f"{a:>5} {a/1024.0:>8.5f} {corner(a):>10.2f}   " +
          "  ".join(f"{m:>+6.2f}dB" for m in mags) + tag)
    print(f"{'':>5} {'':>8} {'':>10}   " +
          "  ".join(f"{p:>+6.2f}°" for p in phs))

print("\nCONTROL -- integer recursion vs analytic H(z) at 7.79 Hz "
      "(mag ratio and phase delta must be ~1.000 / ~0.00°):")
for a in (51, 102, 204, 410):
    gi, pi_ = integer_probe(a, 7.79)
    h = H(a, 7.79)
    ga, pa = abs(h), math.degrees(cmath.phase(h))
    print(f"  a={a:>4}  integer {gi:.5f} @ {pi_:+7.3f}°   analytic {ga:.5f} @ {pa:+7.3f}°"
          f"   ratio {gi/ga:.4f}  dphase {pi_-pa:+.3f}°")

print("\nWHAT THE DIRECTIONS COST, at 7.79 Hz relative to stock a=102:")
h0 = H(STOCK, 7.79)
for a in ALPHAS:
    h = H(a, 7.79)
    dlag = math.degrees(cmath.phase(h)) - math.degrees(cmath.phase(h0))
    dgain = 20 * math.log10(abs(h) / abs(h0))
    arrow = "MORE lag (destabilising if Path 2 IS the pole)" if dlag < 0 else \
            "LESS lag (restores phase margin)" if dlag > 0 else "stock"
    print(f"  a={a:>4}  d_phase {dlag:+7.2f}°  d_gain {dgain:+6.2f} dB   {arrow}")

print("\nAnd what raising alpha costs in HF pass-through (the trade):")
for a in ALPHAS:
    print(f"  a={a:>4}  |H| at 21.09 Hz = {abs(H(a, 21.09)):.4f}   "
          f"at 27.4 Hz = {abs(H(a, 27.4)):.4f}   "
          f"(stock {abs(H(STOCK, 21.09)):.4f} / {abs(H(STOCK, 27.4)):.4f})")
