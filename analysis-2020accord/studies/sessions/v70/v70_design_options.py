#!/usr/bin/env python3
"""studies/sessions/v70/v70_design_options.py -- price every V70 candidate against the SAME two operating points.

The whole post-V62 record reduces to one trade-off on ONE knob (r24's gain_B), read at two
frequencies. From the V65 corner-conditioned band table, Kd=1x vs Kd=2x, 219 blocks:

    1-4 Hz 1.01 | 6-9 1.20 | 10-16 0.80 | 18-22 (GRIND #1) 0.35 | 24-28 2.66 | 30-40 2.98
    40-49 Hz (GRIND #2) 11.71   (p = 0.0003)

Monotone, crossover at 22-24 Hz, driver band flat as a control. MORE Kd damps grind #1 and pumps
grind #2. So a build wins only by putting the dose where grind #1 lives and NOT where grind #2 does.

There are exactly THREE discriminators available, and this script prices all three:

  1. ENGAGEMENT  -- the gate at 0x3AA96. Measured separation (V65 creep windows):
                    LKAS active 98.7% (grind #1) vs 15.7% (grind #2). THE STRONGEST.
                    Costs: a scalar arm REPLACES the whole LERP, destroying Honda's rate rolloff.
  2. VEHICLE SPEED -- which gain_B record is read. Breakpoints 0xC6010 = [0,10,50,100] km/h,
                    2-point interpolation between ADJACENT records only (FUN_0003ad74).
                    Weak: both grinds live at creep.
  3. MOTOR RATE  -- the LERP's own X axis, X = [0, 400, 1400, 3000] counts of gp-0x6ac0.
                    grind #1 ~603 ; grind #2 creep ~1206 ; grind #2 highway ~141-198.
                    ** A 2x separation that NO BUILD HAS EVER TARGETED DELIBERATELY -- V69 hit it
                    by accident, and that is very likely why grind #2 stayed away on route 4f. **
"""
import os
import struct
from pathlib import Path

_env = os.environ.get("ACCORD_FIRMWARE_ROOT")
_root = Path(_env) if _env else Path(__file__).resolve().parents[5] / "accord-firmwares"
ROOT = str(_root / "analysis-2020accord") + "/"

MODE, PTRS, BPS_ADDR = 10, (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214), 0xC6010
OUT_CLAMP, DEADZONE = 0x2000, 3

# operating points, from the golden model (rate in gp-0x6ac0 counts, speed in km/h)
OPS = {
    "grind #1      (creep, engaged, hands-off)": (0, 603),
    "grind #1      (road 60 km/h, engaged)":     (60, 603),
    "grind #2 creep(manual, big torque+angle)":  (0, 1206),
    "grind #2 hwy  (100 km/h manoeuvre)":        (100, 170),
    "ratchet ~7.4Hz(creep, engaged, hands-off)": (0, 300),
}


def h(b, a):
    return struct.unpack_from("<h", b, a)[0]


def recs(img):
    out = []
    for base in PTRS:
        p = struct.unpack_from("<I", img, base + MODE * 4)[0]
        out.append((p, [h(img, p + 2 + 2 * i) for i in range(4)],
                    [h(img, p + 10 + 2 * i) for i in range(4)]))
    return out


def lerp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    for i in range(3):
        if x <= xs[i + 1]:
            return ys[i] + ((ys[i + 1] - ys[i]) * (x - xs[i])) // (xs[i + 1] - xs[i])
    return ys[3]


def surface(rs, bps, kmh, rate):
    sc = int(round(kmh * 64.0))
    if sc <= bps[0]:
        _, xs, ys = rs[0]
    elif sc >= bps[3]:
        _, xs, ys = rs[3]
    else:
        k = next(i for i in range(3) if sc <= bps[i + 1])
        _, x0, y0 = rs[k]
        _, x1, y1 = rs[k + 1]
        n, d = sc - bps[k], bps[k + 1] - bps[k]
        xs = [x0[i] + ((x1[i] - x0[i]) * n) // d for i in range(4)]
        ys = [y0[i] + ((y1[i] - y0[i]) * n) // d for i in range(4)]
    return lerp(xs, ys, rate)


stock_img = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
R_STOCK = recs(stock_img)
BPS = [h(stock_img, BPS_ADDR + 2 * i) for i in range(4)]


def scaled(scale_by_record):
    """Return a record set with Y[0],Y[1] of each record scaled (V69's edit family)."""
    out = []
    for i, (p, xs, ys) in enumerate(R_STOCK):
        s = scale_by_record[i]
        out.append((p, xs, [ys[0] * s, ys[1] * s, ys[2], ys[3]]))
    return out


def gain(cand, kmh, rate, engaged):
    """Delivered gain_q10 on r24. The arm REPLACES the LERP when the gate fires (0x3AC08)."""
    if cand["arm"] is not None and engaged:
        return cand["arm"]
    return surface(cand["recs"], BPS, kmh, rate)


CANDS = {
    "stock":                 dict(arm=None, recs=R_STOCK),
    "V62/V65  sar 0x9 (x2)": dict(arm=None, recs=R_STOCK, sar9=True),
    "V67/V68  gate+arm5244": dict(arm=5244, recs=R_STOCK),
    "V69      surface x4":   dict(arm=None, recs=scaled([4, 4, 1, 1])),
    "V70-A  = restore V67":  dict(arm=5244, recs=R_STOCK),
    "V70-B  V67 arm + x4 lo": dict(arm=5244, recs=scaled([4, 4, 1, 1])),
    "V70-C  gateless x4 ALL": dict(arm=None, recs=scaled([4, 4, 4, 4])),
    "V70-D  gateless x2 ALL": dict(arm=None, recs=scaled([2, 2, 2, 2])),
}

print("DELIVERED r24 GAIN as a multiple of STOCK, at each operating point")
print("(ENGAGED column first, then MANUAL -- they differ only when a gate is present)")
print()
for op, (kmh, rate) in OPS.items():
    s = surface(R_STOCK, BPS, kmh, rate)
    print(f"  {op}   [{kmh} km/h, rate {rate}]   stock gain_q10 = {s}")
    for nm, c in CANDS.items():
        mult = 2.0 if c.get("sar9") else 1.0
        e = gain(c, kmh, rate, True) * mult / s
        m = gain(c, kmh, rate, False) * mult / s
        rail = (OUT_CLAMP + DEADZONE) * 1024 / (gain(c, kmh, rate, True) * mult)
        print(f"      {nm:<24} engaged {e:>5.2f}x   manual {m:>5.2f}x   "
              f"rails at |dtorque| {rail:>6.0f}")
    print()

print("=" * 96)
print("THE DISCRIMINATION RATIO -- grind #1's dose divided by grind #2's dose.")
print("Higher is strictly better: it is damping delivered where it helps, per unit delivered")
print("where it hurts. This is the single number a V70 candidate should be judged on.")
print("=" * 96)
g1_k, g1_r = OPS["grind #1      (creep, engaged, hands-off)"]
g2_k, g2_r = OPS["grind #2 creep(manual, big torque+angle)"]
s1 = surface(R_STOCK, BPS, g1_k, g1_r)
s2 = surface(R_STOCK, BPS, g2_k, g2_r)
print(f"{'candidate':<26}{'g#1 dose':>10}{'g#2 dose':>10}{'ratio':>9}   note")
for nm, c in CANDS.items():
    mult = 2.0 if c.get("sar9") else 1.0
    d1 = gain(c, g1_k, g1_r, True) * mult / s1        # grind #1 is 98.7% ENGAGED
    d2 = gain(c, g2_k, g2_r, False) * mult / s2       # grind #2 is 84.5% MANUAL
    note = ""
    if nm.startswith("V67"):
        note = "measured best: g#1 0.524 [0.337,0.804], g#2 0 bursts"
    elif nm.startswith("V62"):
        note = "g#1 0.35x but g#2 11.71x -- the trade in one build"
    elif nm.startswith("V69"):
        note = "on the car now; g#1 BACK (stock >=50 km/h)"
    print(f"{nm:<26}{d1:>10.2f}{d2:>10.2f}{d1 / d2:>9.2f}   {note}")

print("""
!! THE RATIO IS THE WRONG OBJECTIVE -- stated here because this script's first draft used it and
   reached the wrong answer. V69 scores 2.04 against V67's 1.80, yet V67 is the build that measured
   grind #2 at ZERO bursts and V69 is the build on the car with grind #1 back. The ratio rewards
   V69 for holding grind #2's dose at 1.72x instead of 2.00x, but 1.72x is still an AMPLIFICATION,
   and the V65 dose-response says grind #2 grows explosively (11.71x at a dose of 2.00x). A ratio
   cannot see the difference between "amplified slightly less" and "not amplified at all".

   THE CORRECT OBJECTIVE IS CONSTRAINED, NOT A RATIO:
       maximise  grind #1's dose        subject to   grind #2's dose <= 1.00x (stock)
   Under that objective the gate is not merely better, it is categorically different: it pins
   grind #2's arm to BYTE-IDENTICAL STOCK, so the constraint is satisfied EXACTLY and for free, at
   any arm value. Every gateless candidate violates it by construction, because the surface is
   shared by both arms.
""")

print("=" * 96)
print("THE CONSEQUENCE: WITH THE GATE ON, THE ARM IS A FREE KNOB FOR GRIND #1")
print("Grind #2's dose stays exactly 1.00x however high the arm goes, because the arm is only")
print("reachable when LKAS is applying. The only cost is in the ENGAGED arm -- which is where")
print("route 4a measured engaged-creep grind #2 at 0 bursts over 158.7 s, P(0) = 0.0005.")
print("=" * 96)
print(f"{'arm':>7}{'g#1 creep':>11}{'g#1 60km/h':>12}{'g#2 manual':>12}"
      f"{'rails at':>10}{'margin vs 839':>15}   status")
for arm in (5244, 6144, 6500, 7000, 8192, 10240):
    c = dict(arm=arm, recs=R_STOCK)
    d1c = gain(c, 0, 603, True) / s1
    d1h = gain(c, 60, 603, True) / surface(R_STOCK, BPS, 60, 603)
    d2 = gain(c, g2_k, g2_r, False) / s2
    rail = (OUT_CLAMP + DEADZONE) * 1024 / arm
    tag = "V67/V68 -- FLOWN, the measured best" if arm == 5244 else \
          "extrapolation beyond any flown engaged dose"
    print(f"{arm:>7}{d1c:>11.2f}{d1h:>12.2f}{d2:>12.2f}{rail:>10.0f}"
          f"{rail / 839:>15.2f}x   {tag}")

print("""
!! WHAT THIS TABLE DOES NOT SETTLE, and must not be read as settling: it prices DOSE, not outcome.
   The mapping from dose to symptom is the V65 band table, measured at ONE dose ratio (1x vs 2x) at
   CREEP. Extrapolating it to 4x, or to highway, is exactly the extrapolation the V69 spec flagged
   and the drive then punished. Treat every number here as a design comparator, not a prediction.
!! AND RAISING THE ARM IS NOT FREE OF RISK, only free of GRIND #2 risk in the manual arm: it also
   raises 24-28 Hz and 30-40 Hz in the engaged arm (2.66x and 2.98x per 2x of dose, V65 table), and
   V68's captured lane-change transient sits at ~28 Hz. An arm raise trades against THAT symptom,
   not against grind #2. Price it against the 4f data before choosing a value.
""")
