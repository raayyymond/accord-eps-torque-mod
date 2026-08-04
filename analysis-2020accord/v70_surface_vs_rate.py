#!/usr/bin/env python3
"""v70_surface_vs_rate.py -- V69's delivered gain_B over BOTH axes, from the image bytes.

The V69 design record prices the surface along the SPEED axis only ("4.000x to 10 km/h -> exactly
1.000x at and above 50 km/h") and asserts "no hump anywhere". Both are true. What it does not price
is the MOTOR-RATE axis, and that is where the shape actually moved: V69 raised Y[0] and Y[1] -- the
FLAT [0,400] segment -- by 4x while leaving Y[2] and Y[3] at stock. Honda's mild 2x rolloff over the
rate axis therefore becomes an 8x rolloff, and the rate axis is swept WITHIN each oscillation cycle.

Mirrors the firmware exactly:
  FUN_0003ad74  @0x3AD74 -- rebuilds the runtime table each cycle:
      gp-0x67f4 == 1 ? sVar2 = gp-0x6a5e (VEHICLE SPEED) : tp+0x7314   [orchestrator-verified]
      breakpoints tp+0x7010 = 0xC6010 = [0, 640, 3200, 6400] counts = [0, 10, 50, 100] km/h
      records via FOUR pointer arrays 0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214, each indexed mode*4
      TWO-POINT interpolation between ADJACENT records only; below bp[0] copy R1, above bp[3] copy R4
      -> runtime X row gp-0x6e40, runtime Y row gp-0x6e38
  FUN_0003aa2c  @0x3AB9C-0x3ABF8 -- LERPs that runtime row on r13 = sxh(clamp(gp-0x6ac0, <13001))
"""
import os
import struct
from pathlib import Path

# The default in firmware_paths.py is stale; honour ACCORD_FIRMWARE_ROOT, then fall back to the
# sibling checkout regardless of which directory this is run from.
_env = os.environ.get("ACCORD_FIRMWARE_ROOT")
_root = Path(_env) if _env else Path(__file__).resolve().parents[2] / "accord-firmwares"
ROOT = str(_root / "analysis-2020accord") + "/"
MODE = 10                       # gp+0x63fd == 10 for our car
PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
BREAKPOINTS = 0xC6010
COUNTS_PER_KMH = 64.0
CPDS = 4.7121                   # gp-0x6ac0 counts per deg/s (the OPEN axis scale; see caveat below)


def h(b, a):
    return struct.unpack_from("<h", b, a)[0]


def records(img):
    out = []
    for base in PTR_ARRAYS:
        p = struct.unpack_from("<I", img, base + MODE * 4)[0]
        out.append(([h(img, p + 2 + 2 * i) for i in range(4)],
                    [h(img, p + 10 + 2 * i) for i in range(4)]))
    return out


def lerp(xs, ys, x):
    """The firmware's own 4-point LERP: clamp at both ends, integer divide inside."""
    if x <= xs[0]:
        return ys[0]
    for i in range(3):
        if x <= xs[i + 1]:
            return ys[i] + ((ys[i + 1] - ys[i]) * (x - xs[i])) // (xs[i + 1] - xs[i])
    return ys[3]


def gain_b(img, recs, bps, speed_counts, rate_counts):
    """Rebuild the runtime row for this speed (FUN_0003ad74), then LERP it on rate."""
    if speed_counts <= bps[0]:
        xs, ys = recs[0]
    elif speed_counts >= bps[3]:
        xs, ys = recs[3]
    else:
        k = next(i for i in range(3) if speed_counts <= bps[i + 1])
        (x0, y0), (x1, y1) = recs[k], recs[k + 1]
        num, den = speed_counts - bps[k], bps[k + 1] - bps[k]
        xs = [x0[i] + ((x1[i] - x0[i]) * num) // den for i in range(4)]
        ys = [y0[i] + ((y1[i] - y0[i]) * num) // den for i in range(4)]
    return lerp(xs, ys, rate_counts)


stock = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
v69 = open(ROOT + "_v69_plain_image.bin", "rb").read()
R_S, R_V = records(stock), records(v69)
BPS = [h(stock, BREAKPOINTS + 2 * i) for i in range(4)]

assert BPS == [0, 640, 3200, 6400], BPS
assert records(v69)[2] == records(stock)[2] and records(v69)[3] == records(stock)[3], \
    "R3/R4 must be untouched -- the whole >=50 km/h argument rests on it"

SPEEDS = [0, 5, 10, 20, 30, 40, 50, 60, 80, 100]
RATES = [0, 200, 400, 603, 800, 1206, 1400, 2000, 3000]

print("V69 / stock  delivered gain_B multiplier, over BOTH axes")
print("(rate axis = gp-0x6ac0 counts; ~4.7121 counts per deg/s -- see the caveat below)")
print()
hdr = f"{'km/h':>6} |" + "".join(f"{r:>8}" for r in RATES)
print(hdr)
print(f"{'':>6} |" + "".join(f"{r / CPDS:>7.0f}°" for r in RATES) + "   <- deg/s")
print("-" * len(hdr))
for kmh in SPEEDS:
    sc = int(round(kmh * COUNTS_PER_KMH))
    row = f"{kmh:>6} |"
    for rc in RATES:
        s = gain_b(stock, R_S, BPS, sc, rc)
        v = gain_b(v69, R_V, BPS, sc, rc)
        row += f"{v / s:>8.2f}"
    print(row)

print()
print("=" * 88)
print("WHAT THE SPEED-AXIS SUMMARY IN THE V69 RECORD MISSES")
print("=" * 88)
print("""
The record's "4.000x to 10 km/h -> exactly 1.000x at and above 50 km/h" is correct, and the
>=50 km/h 1.000x is EXACT (2-point interpolation reads only R3/R4, both byte-identical to stock).
But the 4.000x holds ONLY on the flat [0,400] segment of the RATE axis. V69 raised Y[0]/Y[1] and
left Y[2]/Y[3] alone, so along the rate axis at creep:
""")
xs_s, ys_s = R_S[0]
xs_v, ys_v = R_V[0]
print(f"    X  (gp-0x6ac0) = {xs_s}")
print(f"    Y  stock       = {ys_s}      rolloff {ys_s[0] / ys_s[3]:.2f}x across the axis")
print(f"    Y  V69         = {ys_v}      rolloff {ys_v[0] / ys_v[3]:.2f}x across the axis")
print(f"""
=> Honda's mild {ys_s[0] / ys_s[3]:.1f}x rate rolloff becomes a {ys_v[0] / ys_v[3]:.1f}x rolloff. The multiplier collapses from
   4.00x to 1.00x between gp-0x6ac0 = 400 and 1400 counts.

!! WHY THIS MATTERS, AND IT IS A MECHANISM THE V69 DESIGN NEVER PRICED: the rate axis is not a
   slowly-varying operating point. gp-0x6ac0 is the MOTOR RATE, which swings across its full range
   WITHIN EACH CYCLE of any oscillation. A mode whose motor rate excursion crosses the 400-1400
   band therefore sees its own damping gain modulated 4:1 AT TWICE THE MODE FREQUENCY (once per
   half-cycle) -- the textbook parametric-pump configuration, and the same class this kit already
   chased at 42.19 Hz = 2 x 21.09 Hz on V59. Stock's 2:1 modulation is far gentler.
   This is BELIEF, not measurement: it is a mechanism the arithmetic makes available, not one that
   has been observed. The probe bit that could see it is bit6 (gp-0x6ada, r24's own lane output).

!! CAVEAT ON THE RATE AXIS SCALE: 4.7121 counts/deg-s is the value this kit uses for gp-0x6ac0, but
   the axis scale is recorded [OPEN] (the alternative is 0.58901). The deg/s row above is therefore
   indicative. The COUNT-domain conclusions do not depend on it; only the deg/s labels do.
""")
print("reference points on the rate axis, from the golden model:")
print("    grind #1        ~128 deg/s -> gp-0x6ac0 ~ 603     ON the [400,1400] ramp")
print("    grind #2 creep  ~256 deg/s ->            ~1206     further along the ramp")
print("    grind #2 hwy   30-42 deg/s ->          ~141-198    on the FLAT [0,400] segment")
for nm, rc in [("grind #1 (603)", 603), ("grind #2 creep (1206)", 1206), ("grind #2 hwy (170)", 170)]:
    s = gain_b(stock, R_S, BPS, 0, rc)
    v = gain_b(v69, R_V, BPS, 0, rc)
    print(f"    at 0 km/h  {nm:<24} stock {s:>6}  V69 {v:>6}   = {v / s:.2f}x")
