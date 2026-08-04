#!/usr/bin/env python3
"""v70_parametric_gain_collapse.py -- why grind #1 came back AT CREEP on V69.

The operator reports grind #1 returned at CREEP / parking-lot speed (2026-08-04). That RULES OUT
the >=50 km/h reversion, because at creep V69's STATIC gain is 1.75x V62's and 1.96x V67's -- more
damping, not less. So the cause has to be something the static number cannot see.

It is this. The gain_B LERP is indexed on `gp-0x6ac0`, and the load at 0x3AAC4 is `ld.hu` --
UNSIGNED. So the index is |motor rate|, which during an oscillation sweeps 0 -> peak -> 0 TWICE PER
CYCLE. The damping gain is therefore MODULATED AT 2x THE MODE FREQUENCY, and V69 made that
modulation savage: Honda's stock rate rolloff is 2.00:1 across the axis; V69's is 8.00:1.

    X (gp-0x6ac0) = [0, 400, 1400, 3000]
    Y stock       = [3072, 3072, 2322, 1536]     rolloff 2.00x
    Y V69         = [12288, 12288, 2322, 1536]   rolloff 8.00x

The damper's gain is now MAXIMUM at the zero-crossing (|rate| = 0) and MINIMUM at peak velocity --
i.e. it is weakest exactly when a viscous damper is supposed to do its work. V62's `sar 0x9` and
V67's arm are both immune: V62 scales the whole surface (rolloff unchanged at 2.00x), and V67's arm
REPLACES the LERP with a scalar, so its gain is perfectly FLAT in rate -- rolloff 1.00x. That
linearisation is a virtue of V67's design that was never articulated at the time.

Instruction anchors (verified in Ghidra by the orchestrator):
    0x3AAC4  ld.hu -0x6ac0[gp],r11      <- UNSIGNED: the index is a MAGNITUDE
    0x3AAC8  addi -0x32c9,r11,r0        \\ zeroed at >= 13001
    0x3AACC  cmovc 0x0,r11,r13          /
    0x3ABBA-0x3ABF8                     the 4-point LERP on r13 -> r10
    0x3AC08  ld.hu 0x7446[tp],r10       the ARM, REPLACING r10 entirely (V67/V68 only)
    0x3AC18  mul r10,r8,r0 / 0x3AC20 sar 0xa,r8
"""
import os
import struct
from pathlib import Path

import numpy as np

_env = os.environ.get("ACCORD_FIRMWARE_ROOT")
_root = Path(_env) if _env else Path(__file__).resolve().parents[2] / "accord-firmwares"
ROOT = str(_root / "analysis-2020accord") + "/"
CPDS = 4.7121                      # gp-0x6ac0 counts per deg/s (STATE.md's settled value)

X = [0, 400, 1400, 3000]
Y_STOCK = [3072, 3072, 2322, 1536]
Y_V69 = [12288, 12288, 2322, 1536]


def lerp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for i in range(3):
        if x <= xs[i + 1]:
            return ys[i] + ((ys[i + 1] - ys[i]) * (x - xs[i])) // (xs[i + 1] - xs[i])
    return ys[3]


def verify_against_image():
    """Never trust a hard-coded table -- read it back from the shipped images."""
    stock = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
    v69 = open(ROOT + "_v69_plain_image.bin", "rb").read()
    p = struct.unpack_from("<I", stock, 0xCBF5C + 10 * 4)[0]      # mode 10, record 1 (0 km/h)
    xs = [struct.unpack_from("<h", stock, p + 2 + 2 * i)[0] for i in range(4)]
    ys = [struct.unpack_from("<h", stock, p + 10 + 2 * i)[0] for i in range(4)]
    yv = [struct.unpack_from("<h", v69, p + 10 + 2 * i)[0] for i in range(4)]
    assert (xs, ys, yv) == (X, Y_STOCK, Y_V69), (xs, ys, yv)
    return p


ptr = verify_against_image()
print(f"gain_B mode-10 0 km/h record @0x{ptr:05X} -- table verified against the shipped images.")
print(f"  X = {X}\n  Y stock = {Y_STOCK}  (rolloff {Y_STOCK[0]/Y_STOCK[3]:.2f}x)")
print(f"  Y V69   = {Y_V69}  (rolloff {Y_V69[0]/Y_V69[3]:.2f}x)")

# --------------------------------------------------------------------------------------------
# The four builds' gain as a function of the index. V67's arm REPLACES the LERP -> flat.
BUILDS = {
    "stock":            lambda rk: lerp(X, Y_STOCK, rk),
    "V62/V65 (sar 0x9)": lambda rk: 2 * lerp(X, Y_STOCK, rk),   # the shift doubles the OUTPUT
    "V67/V68 (arm)":    lambda rk: 5244,                        # scalar -> FLAT in rate
    "V69 (x4 surface)": lambda rk: lerp(X, Y_V69, rk),
}

print("\n" + "=" * 100)
print("PART 1 -- GAIN MODULATION WITHIN ONE OSCILLATION CYCLE, at creep")
print("|motor rate| sweeps 0 -> A_rk -> 0 twice per cycle (the index is UNSIGNED, ld.hu @0x3AAC4)")
print("=" * 100)
print(f"{'A_rk':>7}{'deg/s':>8}  " + "".join(f"{n:>22}" for n in BUILDS))
print(f"{'':>15}  " + "".join(f"{'min..max  (depth)':>22}" for _ in BUILDS))
for A in (400, 603, 900, 1206, 1400, 1927, 3000):
    row = f"{A:>7}{A/CPDS:>8.0f}  "
    for name, g in BUILDS.items():
        vals = [g(int(A * abs(np.sin(t)))) for t in np.linspace(0, np.pi, 400)]
        lo, hi = min(vals), max(vals)
        row += f"{f'{lo}..{hi} ({hi/lo:.2f}x)':>22}"
    print(row)

# --------------------------------------------------------------------------------------------
# PART 2 -- the describing function. What the mode actually feels is the FUNDAMENTAL component of
# the damping force, i.e. the cycle-average of gain weighted by the velocity waveform.
print("\n" + "=" * 100)
print("PART 2 -- EFFECTIVE (fundamental) DAMPING GAIN vs OSCILLATION AMPLITUDE, creep, x stock@0")
print("velocity ~ cos(t); index = A_rk*|cos t|; force ~ gain(index)*cos t; take the cos-component")
print("=" * 100)


def effective_gain(gfun, A_rk, n=4096):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    vel = np.cos(t)
    idx = np.abs(A_rk * vel)
    g = np.array([gfun(int(i)) for i in idx], float)
    return 2.0 * np.mean(g * vel * vel)          # fundamental (cos) coefficient of gain*vel


ref = effective_gain(BUILDS["stock"], 1)
print(f"{'A_rk':>7}{'deg/s':>8}" + "".join(f"{n:>20}" for n in BUILDS) + "   V69 vs best-prior")
for A in (100, 400, 603, 900, 1206, 1400, 1927, 2500, 3000):
    vals = {n: effective_gain(g, A) / ref for n, g in BUILDS.items()}
    best = max(vals["V62/V65 (sar 0x9)"], vals["V67/V68 (arm)"])
    row = f"{A:>7}{A/CPDS:>8.0f}" + "".join(f"{vals[n]:>20.2f}" for n in BUILDS)
    print(row + f"   {vals['V69 (x4 surface)']/best:>7.2f}x")

print("""
====================================================================================================
VERDICT -- THIS IS THE ONLY MECHANISM LEFT STANDING FOR A CREEP RETURN
====================================================================================================
* V67's arm is a SCALAR that REPLACES the LERP, so its gain is EXACTLY FLAT in rate: modulation
  depth 1.00x at every amplitude. V62's shift scales the whole surface, so it inherits Honda's mild
  2.00x rolloff and nothing worse. V69 modulates its own damping by up to 8.00x WITHIN each cycle,
  at 2x the mode frequency, and is weakest at peak velocity -- where a viscous damper must act.
* The static gain at grind #1's nominal operating point says V69 should be BETTER at creep
  (1.75x V62, 1.96x V67). The effective gain above says the opposite once the oscillation is large
  enough to sweep the index past the 400-count knee -- which route 4f demonstrably does
  (|rate| decile 10 runs 104-409 deg/s = 490-1927 counts).
* => V69 did not merely fail to help at creep. It converted a constant-gain damper into an
  amplitude-dependent one, and a damper whose gain FALLS with amplitude is the textbook
  describing-function condition for a STABLE LIMIT CYCLE. That is grind #1.

!! HONEST LIMITS, stated so this is not over-read:
   (a) The index gp-0x6ac0 is MOTOR rate, and I model it as in phase with column velocity. Through
       the torsion bar at 21 Hz that is an approximation; a phase shift moves the numbers, though
       not the direction (any phase still sweeps the index twice per cycle).
   (b) This is an open-loop gain argument. It shows the damper got worse in a specific,
       amplitude-dependent way; it does not prove the loop then limit-cycles at 21 Hz.
   (c) The 4.7121 counts/deg-s axis scale is used only for the deg/s labels; every count-domain
       conclusion is scale-free.
   (d) The operator's report is the primary evidence here. This arithmetic explains it; it did not
       predict it in advance, and it was written after the fact.
""")
