#!/usr/bin/env python3
"""v69_surface_math.py -- the mode-10 gain_B surface rebuilt FROM IMAGE BYTES, and every design
that can be cut out of it with 1-3 calibration halfwords.

🛑 WHAT SHIPPED IS **x4**, NOT THE x2 THIS FILE SCORES. Operator instruction, 2026-08-04: V69 was
re-cut in place to 3072->12288 and 2561->10244. The design named `V62_MATCHED` below (6144/5122) is
the x2 cut and is kept as the SELECTION RECORD -- it is how Design A was rejected and how the
Pareto front was chosen, and those arguments are about SHAPE, which x4 does not change (still
scale-invariant on both axis candidates, still no hump, still exactly 1.000x at and above 50 km/h).
What x4 DOES change is dose-dependent and is NOT re-derived here:
  - max multiplier 2.000x -> 4.000x, which BREAKS the flown `[stock 1.00x, V62/V65 2.00x]` bracket;
  - `saturating_dtorque(12288)` = 683 vs the recorded max |dtorque| 839 => margin 0.81x, i.e. the
    r24 lane CAN rail (at 6144 it rails at 1366 and could not).
To score the shipped design here, use
    `edit(r0Y=(12288, 12288, None, None), r1Y=(10244, 10244, None, None))`.
Authoritative: `build_v69_tva.py` (the SCALE constant), `docs/V69-DESIGN.md` §0.

Successor to `v68_design_math.py`. That file hard-coded the records as literals; this one READS
them, resolves the pointer arrays, and re-derives every number it prints. Run it and every figure
quoted in the report comes back out.

WHAT THIS FILE ADDS OVER v68_design_math.py
  1. Every record is byte-read through its pointer array (no literals). T1.
  2. 🛑 THE AXIS SCALE IS TREATED AS OPEN. `v68_design_math.py` prints 4.7121 counts/deg-s as
     settled. It is NOT: its own docstring records that the derivation chain
     (`gp-0x6ac0 = |gp-0x6abe|`, `bus = (gp-0x6abe*48*1159)>>15`) has ONE WRONG PREMISE and that
     "which one is still OPEN". 4.7121 survives only as a physical-plausibility inference. The
     arithmetically-surviving alternative from the same chain is 0.58901 counts/deg-s. EVERY
     design here is scored under BOTH. This changes the verdict on Design A.
  3. 🛑 THE ARM BYPASSES THE LERP. On V67/V68 the LKAS gate arm at `0x3AC08` REPLACES the surface
     (`0x3ABFA-0x3AC16` priority chain). So a mode-10 cal edit is INERT while engaged unless
     the gate repoint at `0x3AA96` is reverted first. Design A is not a drop-in on V68.
  4. The grind #1 population is scored as a REGION (2-5 mph x 16-128 deg/s), not one point --
     because V62's measured fix was largest at |rate| 16-32 deg/s, a band where Design A's
     boost has barely started.
  5. A directed search over 1-3 halfword edits, with the full multiplier surface for each.

Usage:  python v69_surface_math.py            (uses $ACCORD_FIRMWARE_ROOT or the default below)
"""
from __future__ import annotations

import os
import struct
import sys

import numpy as np

try:                                     # Windows consoles default to cp1252; this file is UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                        # pragma: no cover
    pass

# =====================================================================================================
# 0. THE IMAGE
# =====================================================================================================
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = os.path.join(ROOT, "analysis-2020accord", "_v68_plain_image.bin")
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_cache_v68")

with open(IMG, "rb") as f:
    B = f.read()

# The plain image is flat: file offset == V850 address. ANCHORED, not assumed -- V68's cave word
# `ld.bu -0x67df[gp],r6` = a4 37 21 98 sits at 0xC4B44 exactly (HANDOFF-2026-08-03 table).
assert len(B) == 0x100000
assert B[0xC4B44:0xC4B48] == bytes.fromhex("a4372198"), "image is not offset==address"
assert B[0xC4B34:0xC4B38] == bytes.fromhex("203e8800")


def u16(a: int) -> int:
    return struct.unpack_from("<H", B, a)[0]


def u32(a: int) -> int:
    return struct.unpack_from("<I", B, a)[0]


# =====================================================================================================
# 1. T1 -- THE SURFACE, READ FROM BYTES
# =====================================================================================================
# FUN_0003ad74 resolves r24's gain_B through FOUR pointer arrays, each indexed by mode*4. Array i
# holds the record for speed breakpoint CROSS_X[i].
PTR_ARRAYS = (0xCBF5C, 0xCC044, 0xCC12C, 0xCC214)
MODE = 10
CROSS_X_ADDR = 0xC6010                       # the outer (speed) axis, 4 halfwords
CROSS_X = tuple(u16(CROSS_X_ADDR + 2 * i) for i in range(4))
COUNTS_PER_KMH = 64.0625                     # 640 counts == 10 km/h; the .0625 is the repo's refinement


def read_record(addr: int):
    """20-byte record: u16 count=4, X[4], Y[4], pad. All little-endian."""
    n = u16(addr)
    xs = tuple(u16(addr + 2 + 2 * i) for i in range(4))
    ys = tuple(u16(addr + 10 + 2 * i) for i in range(4))
    pad = u16(addr + 18)
    return n, xs, ys, pad


def mode_records(mode: int):
    out = []
    for i, arr in enumerate(PTR_ARRAYS):
        pa = arr + mode * 4
        rec = u32(pa)
        n, xs, ys, pad = read_record(rec)
        out.append(dict(idx=i, ptr_addr=pa, rec=rec, count=n, xs=xs, ys=ys, pad=pad,
                        x_addr=rec + 2, y_addr=rec + 10,
                        kmh=CROSS_X[i] / COUNTS_PER_KMH))
    return out


RECS10 = mode_records(10)
RECS11 = mode_records(11)
STOCK = tuple((r["xs"], r["ys"]) for r in RECS10)

# =====================================================================================================
# 2. THE ARITHMETIC -- mirrored from the decompiled code, addresses annotated
# =====================================================================================================
DTORQUE_CLAMP = 5120     # aggregator input clamp on gp-0x4f62                       @0x3AAAC-0x3AAC0
LANE_CLAMP = 8192        # r24 output clamp                                          @0x3AC42-0x3AC54
DEADZONE = u16(0xC61F6)  # cal 0xC61F6, applied AFTER the gain, BEFORE the clamp      @0x3AC1C-0x3AC3C
FOLD = 13001             # idx >= 13001 folds to 0 (addi -0x32c9 / cmovc)             @0x3AAC8-0x3AACC
INT32_MAX = 2 ** 31 - 1

ARM_671D = u16(0xC6442)  # 1024, outranks everything                                  @0x3ABFA
ARM_GATE = u16(0xC6446)  # V67/V68: 5244, taken when gp-0x6806 != 0                   @0x3AC08
ARM_671A = u16(0xC6440)  # 2048, taken when gp-0x671a >= cal 0xC64FA                  @0x3AC10
GATE_BYTE = B[0x3AA96]   # 0xfb = repointed to gp-0x6806 (V67/V68); 0xc5 = dead gp-0x683c


def _dtz(n: int, d: int) -> int:
    """V850 `divq`: signed division TRUNCATING TOWARD ZERO.                            @0x3ABF4"""
    q = abs(n) // abs(d)
    return -q if (n < 0) != (d < 0) else q


def _lerp(x: int, xs, ys) -> int:
    """The firmware LERP idiom -- FLAT extrapolation outside the breakpoints.  @0x3ABB2-0x3ABF8"""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            return ys[i] + _dtz((ys[i + 1] - ys[i]) * (x - xs[i]), xs[i + 1] - xs[i])
    return ys[-1]


def gain_q10(speed_counts: int, axis_counts: int, recs=STOCK) -> int:
    """FUN_0003ad74: cross-interpolate X and Y element-by-element on SPEED, then LERP on RATE."""
    k = max(CROSS_X[0], min(int(speed_counts), CROSS_X[-1]))
    xs = tuple(_lerp(k, CROSS_X, tuple(r[0][i] for r in recs)) for i in range(4))
    ys = tuple(_lerp(k, CROSS_X, tuple(r[1][i] for r in recs)) for i in range(4))
    idx = int(axis_counts) if 0 <= axis_counts < FOLD else 0
    return _lerp(idx, xs, ys)


def r24_lane(dtorque: int, gain: int) -> int:
    """r24 after the gain, the +/-DEADZONE shaping and the +/-8192 clamp.      @0x3AC16-0x3AC54"""
    scaled = (dtorque * gain) >> 10                      # V850 `sar`: arithmetic, floors negatives
    if scaled > DEADZONE:
        shaped = scaled - DEADZONE
    elif scaled < -DEADZONE:
        shaped = scaled + DEADZONE
    else:
        shaped = 0
    return max(-LANE_CLAMP, min(LANE_CLAMP, shaped))


def saturating_dtorque(gain: int) -> int:
    """|dtorque| at which the lane first hits its own +/-8192 clamp, THROUGH the real lane."""
    for d in range(1, DTORQUE_CLAMP + 1):
        if abs(r24_lane(d, gain)) >= LANE_CLAMP:
            return d
    return DTORQUE_CLAMP + 1


def r24_gain_live(speed_counts, axis_counts, gate, mask_671d=0, state_671a=0,
                  recs=STOCK, arm_gate=None, gate_live=None):
    """The FULL priority chain as V67/V68 leave it.  Mirrors 0x3ABFA-0x3AC16.

    🛑 THE POINT OF THIS FUNCTION: when the gate arm is live and open, the SURFACE IS NOT READ.
    """
    arm_gate = ARM_GATE if arm_gate is None else arm_gate
    gate_live = (GATE_BYTE == 0xFB) if gate_live is None else gate_live
    if mask_671d != 0:
        return ARM_671D, "0xC6442 = 1024 (gp-0x671d mask -- BELOW stock)"
    if gate_live and gate != 0:
        return arm_gate, f"0xC6446 = {arm_gate} (the LKAS arm -- THE LERP IS BYPASSED)"
    if state_671a >= u16(0xC64FA) & 0xFF:
        return ARM_671A, "0xC6440 = 2048 (the third arm)"
    return gain_q10(speed_counts, axis_counts, recs), "the mode-10 LERP"


# =====================================================================================================
# 3. 🛑 THE AXIS SCALE -- OPEN, AND IT DECIDES EVERYTHING
# =====================================================================================================
# Two candidate scales for the inner axis gp-0x6ac0, both from the SAME broken derivation chain:
#
#   SCALE_A  4.71210813 = 2^18/(48*1159).  Requires `bus = 8 x deg/s`  -- a relation the repo
#            RETRACTED on 2026-08-02 after measuring `bus = 1 x deg/s`. It survives only because
#            it is the only scale under which Honda's 400/1500/3000 breakpoints land inside a real
#            steering wheel's slew range (85/318/637 deg/s).  ==> the repo's live assumption.
#   SCALE_B  0.58901 = 32768/(48*1159).  What `bus = (gp-0x6abe*48*1159)>>15` plus
#            `gp-0x6ac0 = |gp-0x6abe|` give DIRECTLY once the measured `bus = deg/s` is used.
#            Puts the breakpoints at 679/2547/5093 deg/s -- unreachable, so the whole rate axis
#            would be a single flat segment in every real drive.
#
# Nothing in this kit has ever OBSERVED gp-0x6ac0. The 2026-08-02 retraction says in terms:
# "One of those two premises is wrong; which one is still OPEN and needs a Ghidra trace."
SCALE_A = 2 ** 18 / (48 * 1159)
SCALE_B = 2 ** 15 / (48 * 1159)
SCALES = (("A 4.7121 c/deg-s (repo live, BELIEF)", SCALE_A),
          ("B 0.5890 c/deg-s (chain-direct, BELIEF)", SCALE_B))


def axis(degs: float, scale: float) -> int:
    return int(degs * scale)


def sc(kmh: float) -> int:
    return int(kmh * COUNTS_PER_KMH)


def G(kmh, degs, recs=STOCK, scale=SCALE_A) -> int:
    return gain_q10(sc(kmh), axis(degs, scale), recs)


def M(kmh, degs, recs, scale=SCALE_A) -> float:
    """Delivered multiplier vs STOCK at (speed, steering rate)."""
    return G(kmh, degs, recs, scale) / G(kmh, degs, STOCK, scale)


# =====================================================================================================
# 4. THE OPERATING POINTS
# =====================================================================================================
# grind #1: operator's "2-5 mph" = 3.22-8.05 km/h. V67 sized its arm at 7.2 km/h / 128 deg/s, but
# V62's MEASURED fix was largest at |rate| 16-32 deg/s -- so the population is a REGION.
G1_KMH = (3.2, 5.0, 7.2, 10.0, 14.4)         # 1-4 m/s covers 3.6-14.4; 2-5 mph covers 3.2-8.0
G1_DEGS = (16, 24, 32, 64, 128)
G1_POINT = (7.2, 128)                        # V67's own sizing point, kept for continuity

G2C_POINT = (5.0, 256)                       # creep grind #2, driver cranking
HW_POINT = (25.93 * 3.6, 38)                 # THE NEW ONE: lane change, 93.35 km/h, 38 deg/s peak
MC_KMH = (0.0, 3.2, 5.0, 7.2, 10.0, 14.4)    # manual creep / parking
MC_DEGS = (150, 200, 256, 350, 521)

RATE_MAX_MEASURED = 521                      # |rate| max over 407,617 frames (repo record)

POINTS = (
    ("grind #1        creep, hands-off", *G1_POINT),
    ("creep grind #2  driver cranking", *G2C_POINT),
    ("HIGHWAY LANE CHANGE (the new one)", *HW_POINT),
    ("manual creep    parking crank", 5.0, 256),
    ("highway cruise  straight", 110.0, 8),
)


# =====================================================================================================
# 5. DESIGNS
# =====================================================================================================
def edit(*, r0Y=None, r1Y=None, r0X=None, r1X=None):
    """Build a record set from STOCK with per-element overrides. None = keep stock."""
    out = []
    for i, (xs, ys) in enumerate(STOCK):
        oy = (r0Y, r1Y, None, None)[i]
        ox = (r0X, r1X, None, None)[i]
        if oy:
            ys = tuple(oy[j] if oy[j] is not None else ys[j] for j in range(4))
        if ox:
            xs = tuple(ox[j] if ox[j] is not None else xs[j] for j in range(4))
        out.append((xs, ys))
    return tuple(out)


# Address of each editable halfword, for the report.
ADDR = {
    ("r0", "Y", j): RECS10[0]["y_addr"] + 2 * j for j in range(4)}
ADDR.update({("r1", "Y", j): RECS10[1]["y_addr"] + 2 * j for j in range(4)})
ADDR.update({("r0", "X", j): RECS10[0]["x_addr"] + 2 * j for j in range(4)})
ADDR.update({("r1", "X", j): RECS10[1]["x_addr"] + 2 * j for j in range(4)})

DESIGN_A = edit(r1Y=(None, 7051, None, None))          # 0xD2ABC 2561 -> 7051, ONE halfword

# ★ THE V62-DOSE-MATCHED DESIGN. Not from the optimiser -- the optimiser maximises the grind #1
# multiplier against a 2.5x hump cap and therefore always pushes to 2.1-2.5x, which is MORE dose
# than anything this kit has ever driven. This one instead sets every edited halfword to EXACTLY
# TWICE the byte it replaces, which is the dose V62 flew and which measurably fixed grind #1:
#   0xD2A7E 3072 -> 6144   0xD2A80 3072 -> 6144   0xD2ABA 2561 -> 5122   0xD2ABC 2561 -> 5122
# Result: EXACTLY 2.000x at every speed <= 10 km/h below the first rate breakpoint, tapering
# linearly to EXACTLY 1.000x at 50 km/h, and byte-identical to stock above it. Zero hump.
V62_MATCHED = edit(r0Y=(6144, 6144, None, None), r1Y=(5122, 5122, None, None))
V62_MATCHED_2HW = edit(r1Y=(5122, 5122, None, None))

NOTES = {
    "V62x4": "★ EVERY EDITED HALFWORD IS EXACTLY 2x THE ONE IT REPLACES -- V62's flown, measured "
             "creep dose, re-delivered through Honda's own speed schedule instead of a flat "
             "scalar. Exactly 2.000x at creep, exactly 1.000x above 50 km/h, NO hump at all, and "
             "the same number on BOTH axis scales. 4 halfwords, one CRC block.",
    "V62x2": "The in-budget 2-halfword cut of the same idea: only the 10 km/h record doubles. "
             "Costs the 0-5 km/h end, where it decays to 1.00x -- and grind #1 is a 2-5 mph "
             "symptom, so that is the wrong end to give up.",
    "DA": "The recorded one-halfword design. Reproduces its three headline numbers on scale A "
          "and FAILS on scale B; its hump is 2.75x, not 2.45x; and its dose at 16-32 deg/s -- "
          "where V62's fix measured largest -- is only 1.1-1.5x.",
    "F1": "Design A's family, re-optimised under the hump cap instead of at one point.",
    "F2": "Raises the 10 km/h record's WHOLE flat low-rate segment. Scale-robust in shape "
          "(Y[0] and Y[1] move together, so nothing depends on where the 400-count breakpoint "
          "sits in deg/s), but anchored at 1.00x at 0 km/h because rec0 is untouched.",
    "F3": "Design A plus a matching rec0 raise, which flat-tops Y[1] and removes the 10 km/h "
          "peak. Still a bet on scale A: it moves only Y[1].",
    "F4": "The 0 km/h record alone. Cannot reach creep speeds without an enormous value, "
          "because 7.2 km/h is 72% of the way to rec1.",
    "F5": "3 halfwords: rec0's Y[1] plus rec1's whole low-rate segment. The best in-budget "
          "compromise between scale-robustness and hump.",
    "F6": "rec1's low-rate segment raised AND its 1500-count knee cut -- maximum separation "
          "between grind #1 and creep grind #2, and the most scale-dependent design here.",
    "F7": "Moves the breakpoint itself: rec1.X[1] down plus rec1.Y[1] up, so the boost starts "
          "at a lower rate than Honda's 400 counts.",
    "F8": "OVER BUDGET at 4 halfwords, and it is the answer anyway: rec0 and rec1 both raised "
          "flat across their whole low-rate segment. The only design whose grind #1 number "
          "survives BOTH axis scales, with no hump and an exact 1.000x above 50 km/h.",
}


def design_cells(recs):
    """Which halfwords differ from stock, with addresses."""
    out = []
    for i, tag in ((0, "r0"), (1, "r1")):
        for kind, key in (("X", 0), ("Y", 1)):
            for j in range(4):
                if recs[i][key][j] != STOCK[i][key][j]:
                    out.append((ADDR[(tag, kind, j)], STOCK[i][key][j], recs[i][key][j],
                                f"{tag}.{kind}[{j}]"))
    return out


# =====================================================================================================
# 6. SCORING
# =====================================================================================================
SWEEP_KMH = tuple(np.round(np.concatenate([np.arange(0, 20.01, 0.2),
                                           np.arange(21, 60.1, 1.0)]), 2))
SWEEP_DEGS = tuple(range(0, RATE_MAX_MEASURED + 1, 2))


def surface_max(recs, scale):
    """Max multiplier anywhere REACHABLE: 0-60 km/h x 0-521 deg/s. (>=50 km/h is stock by
    construction for any rec0/rec1 edit; the sweep proves it rather than assuming it.)"""
    best = (0.0, None, None)
    for k in SWEEP_KMH:
        for d in SWEEP_DEGS:
            m = M(k, d, recs, scale)
            if m > best[0]:
                best = (m, k, d)
    return best


def score(recs, scale):
    g1 = [M(k, d, recs, scale) for k in G1_KMH for d in G1_DEGS]
    mc = [M(k, d, recs, scale) for k in MC_KMH for d in MC_DEGS]
    hump, hk, hd = surface_max(recs, scale)
    return dict(
        g1_point=M(*G1_POINT, recs, scale),
        g1_min=min(g1), g1_med=float(np.median(g1)), g1_max=max(g1),
        g2c=M(*G2C_POINT, recs, scale),
        hw=M(*HW_POINT, recs, scale),
        mc_med=float(np.median(mc)), mc_max=max(mc),
        hump=hump, hump_kmh=hk, hump_degs=hd,
        gmax=max(G(k, d, recs, scale) for k in SWEEP_KMH for d in (0, 85, 128, 256, 400, 521)),
    )


def score_fast(recs, scale):
    """Cheap filter -- the scalar constraints only, no full sweep."""
    g1 = [M(k, d, recs, scale) for k in G1_KMH for d in G1_DEGS]
    return (min(g1), float(np.median(g1)), M(*G2C_POINT, recs, scale),
            M(*HW_POINT, recs, scale),
            max(M(k, d, recs, scale) for k in MC_KMH for d in MC_DEGS))


# =====================================================================================================
# 7. MEASURED DATA -- the saturation check against the real caches
# =====================================================================================================
def measured_dtorque():
    """gp-0x4f62 = (x[n] - x[n-4]) / 2 at 1 kHz  (2*(x[n]-x[n-4])/4, delay cal 0xC6C42 = 4).

    CAN gives the bar at 100.000 Hz exactly, so a 4 ms difference cannot be formed directly. What
    CAN *can* do exactly is apply the finite difference's TRANSFER FUNCTION in the frequency
    domain: |H(f)| = |sin(pi f * 0.004)|, which is exact for every component the 100 Hz grid can
    represent (0-50 Hz) and SILENT above it. So this is a LOWER BOUND on |dtorque|.
    """
    import glob
    rows = []
    for path in sorted(glob.glob(os.path.join(CACHE, "*.npz"))):
        base = os.path.basename(path)
        if "_rpm" in base or "_events" in base:
            continue
        d = np.load(path)
        tq = np.asarray(d["tq"], float)
        v = np.asarray(d["cs_v"], float)
        ok = np.isfinite(tq)
        if ok.sum() < 1024:
            continue
        x = np.where(ok, tq, 0.0)
        n = len(x)
        X = np.fft.rfft(x - x.mean())
        f = np.fft.rfftfreq(n, d=1 / 100.0)
        H = np.abs(np.sin(np.pi * f * 0.004))          # the 4-sample difference at 1 kHz
        dt = np.fft.irfft(X * H, n)                    # /2 already folded: |x[n]-x[n-4]|/2 = A*|sin|
        rows.append((base, float(np.nanmedian(v)), float(np.abs(dt).max()),
                     float(np.percentile(np.abs(dt), 99.9)), float(np.abs(tq).max())))
    return rows


def dtorque_from_burst(pp_counts: float, f_hz: float) -> float:
    """The lane-change burst, through the same transfer function. A = pp/2."""
    return (pp_counts / 2.0) * abs(np.sin(np.pi * f_hz * 0.004))


# =====================================================================================================
# 8. REPORT
# =====================================================================================================
def rule(t=""):
    print("\n" + "=" * 102)
    if t:
        print(t)


def main():
    print(__doc__.split("Usage:")[0].rstrip())

    # ---------------------------------------------------------------------------- T1
    rule("T1. THE MODE-10 gain_B SURFACE, READ FROM IMAGE BYTES  [EVIDENCE]")
    print(f"  image: {IMG}")
    print(f"  offset == address, anchored on 0xC4B44 = a4 37 21 98 (V68's cave word)")
    print(f"  outer (speed) axis @0x{CROSS_X_ADDR:05X} = {CROSS_X}  "
          f"= {tuple(round(x / COUNTS_PER_KMH, 1) for x in CROSS_X)} km/h "
          f"at {COUNTS_PER_KMH} counts/km/h")
    print()
    for r in RECS10:
        print(f"  rec{r['idx']}  ptr @0x{r['ptr_addr']:05X} -> 0x{r['rec']:05X}   "
              f"({r['kmh']:5.1f} km/h)   count={r['count']}  pad={r['pad']}")
        print(f"        raw 20 bytes: {B[r['rec']:r['rec'] + 20].hex(' ')}")
        print(f"        X @0x{r['x_addr']:05X} = {r['xs']}   "
              f"halfword addrs {[hex(r['x_addr'] + 2 * j) for j in range(4)]}")
        print(f"        Y @0x{r['y_addr']:05X} = {r['ys']}   "
              f"halfword addrs {[hex(r['y_addr'] + 2 * j) for j in range(4)]}")
    print()
    print("  CONFIRM/REFUTE the two claims under test:")
    ok1 = RECS10[1]["rec"] == 0xD2AB0 and abs(RECS10[1]["kmh"] - 10.0) < 0.02
    ok2 = RECS10[1]["y_addr"] + 2 == 0xD2ABC and RECS10[1]["ys"][1] == 2561
    print(f"    0xD2AB0 IS the 10 km/h record ............ {'CONFIRMED' if ok1 else 'REFUTED'}"
          f"   (ptr array 0xCC044[10*4] = 0x{RECS10[1]['rec']:05X}, "
          f"CROSS_X[1] = {CROSS_X[1]} = {RECS10[1]['kmh']:.3f} km/h)")
    print(f"    0xD2ABC IS its Y[1] and reads 2561 ....... {'CONFIRMED' if ok2 else 'REFUTED'}"
          f"   (Y base 0x{RECS10[1]['y_addr']:05X} + 2, bytes "
          f"{B[0xD2ABC:0xD2ABE].hex(' ')} LE = {u16(0xD2ABC)})")
    print()
    print("  mode 11 (the failover partner, interleaved at stride 0x14) -- NOT edited by anything")
    print("  here, but listed because FUN_00042746 reselects among {10,10,11,11} at runtime:")
    for r in RECS11:
        print(f"    rec{r['idx']} 0x{r['rec']:05X} ({r['kmh']:5.1f} km/h)  X{r['xs']}  Y{r['ys']}")
    print()
    print("  CROSS-BUILD: the four mode-10 records are byte-identical in every image on disk")
    print("  (checked below) => 'never edited in any build' is CONFIRMED.")
    _cross_build_check()

    # ---------------------------------------------------------------------------- the arithmetic
    rule("2. THE EXACT INTEGER ARITHMETIC  (mirrors the decompiled code; addresses inline)")
    print("""
    # --- FUN_0003ad74, the two-axis cross-interpolated surface -------------------------------
    k  = clamp(speed_counts, CROSS_X[0], CROSS_X[-1])
    xs = [ lerp(k, CROSS_X, [rec[i].X[j] for i in 0..3]) for j in 0..3 ]     # rebuilt per cycle
    ys = [ lerp(k, CROSS_X, [rec[i].Y[j] for i in 0..3]) for j in 0..3 ]
    idx = axis if 0 <= axis < 13001 else 0             # addi -0x32c9 / cmovc   @0x3AAC8-0x3AACC
    gain_q10 = lerp(idx, xs, ys)                       #                        @0x3ABB2-0x3ABF8

    # --- lerp(), the firmware idiom: FLAT outside, truncate-toward-zero inside ---------------
    if x <= xs[0]:  return ys[0]
    if x >= xs[-1]: return ys[-1]
    i = segment containing x
    return ys[i] + divq((ys[i+1]-ys[i]) * (x-xs[i]), xs[i+1]-xs[i])   # `divq` trunc-to-zero @0x3ABF4

    # --- the priority chain that SELECTS the gain --------------------- @0x3ABFA-0x3AC16 -----
    if gp-0x671d != 0:                 gain = 0xC6442 = 1024            # outranks everything
    elif <gate cell> != 0:             gain = 0xC6446 = %-5d           # 🛑 THE LERP IS BYPASSED
    elif gp-0x671a >= cal 0xC64FA:     gain = 0xC6440 = 2048
    else:                              gain = <the LERP above>

    # --- the lane ------------------------------------------------------ @0x3AC16-0x3AC54 ----
    scaled = (dtorque * gain) >> 10                    # `sar 0xa,r8`  @0x3AC20 (V68 byte %s)
    shaped = scaled -/+ %d if |scaled| > %d else 0     # cal 0xC61F6
    r24    = clamp(shaped, -8192, +8192)
    """ % (ARM_GATE, B[0x3AC20:0x3AC21].hex(), DEADZONE, DEADZONE))
    print(f"  cals read from the image: 0xC6440={ARM_671A}  0xC6442={ARM_671D}  "
          f"0xC6446={ARM_GATE}  0xC61F6={DEADZONE}  0x3AA96=0x{GATE_BYTE:02x}"
          f"  ({'gp-0x6806, LIVE' if GATE_BYTE == 0xFB else 'gp-0x683c, DEAD'})")

    rule("2b. 🛑 THE FINDING THAT REFRAMES THE WHOLE TASK  [EVIDENCE, from 0x3AA96 + the chain]")
    print("""
  On V67 and V68 the gate byte at 0x3AA96 is 0xfb, i.e. the arm is wired to gp-0x6806 = "LKAS is
  applying" (V62/V65 carry 0xc5 = the DEAD gp-0x683c). Route 4e measured that gate OPEN in
  100.000% of engaged frames. And the priority chain REPLACES the LERP with 0xC6446 when the gate
  is open -- it does not scale it, compose with it, or fall through to it.

  ==> A mode-10 gain_B calibration edit -- Design A included -- is INERT WHILE LKAS IS ENGAGED on
      a V68 base. It would change ONLY the manual/disengaged lane, which is the exact opposite of
      what the 28 Hz lane-change problem needs.

  ==> ANY of the designs below must be built as V68 MINUS the gate repoint:
        0x3AA96   fb -> c5     (one code byte, back to the dead gp-0x683c)
      Leaving 0xC6446 at 5244 is then harmless (nothing reaches it), and reverting it to 512 is
      also harmless. 🛑 DO NOT instead "neutralise" the arm by writing 0xC6446 = 512 while the
      gate stays repointed: 512 is 5x BELOW the stock LERP and would make engaged steering worse
      than stock everywhere. Verified from the priority chain, not assumed.""")
    for gate in (0, 1):
        g, why = r24_gain_live(sc(7.2), axis(128, SCALE_A), gate)
        print(f"    gate={gate}: gain={g:5d}  <- {why}")

    # ---------------------------------------------------------------------------- T2
    rule("T2. THE STOCK SURFACE AND THE V67/V68 ARM, ON ALL FOUR OPERATING POINTS")
    for lab, s in SCALES:
        print(f"\n  --- inner-axis scale {lab} ---")
        print(f"  breakpoints X = {STOCK[1][0]} counts = "
              f"{tuple(round(x / s, 0) for x in STOCK[1][0])} deg/s")
        print(f"  {'operating point':36} {'km/h':>7} {'deg/s':>6} {'axis':>6} "
              f"{'stock':>6} {'V67/V68':>8} {'mult':>6}")
        for lab2, k, d in POINTS:
            st = G(k, d, STOCK, s)
            print(f"  {lab2:36} {k:7.2f} {d:6.0f} {axis(d, s):6d} {st:6d} "
                  f"{ARM_GATE:8d} {ARM_GATE / st:6.2f}")
        print("  (the V67/V68 column is the ARM, taken whenever LKAS applies; disengaged it is"
              " the stock column and the multiplier is exactly 1.00)")

    rule("T2b. VERIFYING V67/V68's RECORDED 2.44x HIGHWAY / 2.00x CREEP  [EVIDENCE]")
    for lab, s in SCALES:
        st_g1 = G(*G1_POINT, STOCK, s)
        st_hw = G(*HW_POINT, STOCK, s)
        st_hw110 = G(110.0, 35, STOCK, s)
        print(f"  scale {lab[:1]}:  grind #1 LERP = {st_g1}  => arm/LERP = {ARM_GATE / st_g1:.3f}x"
              f"   |   lane-change LERP = {st_hw} => {ARM_GATE / st_hw:.3f}x"
              f"   |   110 km/h/35 deg-s LERP = {st_hw110} => {ARM_GATE / st_hw110:.3f}x")
    print("  => 2.44x at highway REPRODUCES on both scales (highway rates sit in the flat first")
    print("     segment either way, so the LERP there is just the speed-interpolated Y[0..1]).")
    print("  => 2.00x at creep reproduces ONLY on scale A. On scale B the creep LERP is the same")
    print("     flat value the highway one comes from, so the arm delivers ~1.94x -- close enough")
    print("     that no on-car observation can separate the two scales through V67's arm.")

    rule("T2c. THE V67/V68 DELIVERED MULTIPLIER vs SPEED (engaged), scale-independent")
    print(f"  {'km/h':>7} {'stock LERP':>11} {'arm':>6} {'mult':>6}   (at 38 deg/s, the lane-change rate)")
    for k in (0, 5, 7.2, 10, 20, 30, 50, 70, 93.35, 110, 130):
        st = G(k, 38, STOCK, SCALE_A)
        print(f"  {k:7.2f} {st:11d} {ARM_GATE:6d} {ARM_GATE / st:6.2f}"
              + ("   <-- THE LANE-CHANGE POINT" if abs(k - 93.35) < 0.01 else ""))
    print("  => CONFIRMED: V67/V68's multiplier RISES with speed, maximum at highway. The stock")
    print("     surface rolls off 3072 -> 2151 and the flat arm does not follow it.")

    # ---------------------------------------------------------------------------- T3
    rule("T3. DESIGN A  (0xD2ABC 2561 -> 7051, ONE halfword)")
    print(f"  cells: " + ", ".join(f"0x{a:05X} {o} -> {n} ({w})"
                                   for a, o, n, w in design_cells(DESIGN_A)))
    print(f"  CRC block: {crc_block_of(0xD2ABC)}")
    for lab, s in SCALES:
        sco = score(DESIGN_A, s)
        print(f"\n  --- scale {lab} ---")
        print(f"    grind #1 @ V67's own point (7.2 km/h, 128 deg/s) : {sco['g1_point']:5.2f}x"
              f"   [recorded: 2.00x]  {'REPRODUCES' if abs(sco['g1_point'] - 2.0) < 0.03 else '*** DOES NOT REPRODUCE ***'}")
        print(f"    creep grind #2 (5 km/h, 256 deg/s)               : {sco['g2c']:5.2f}x"
              f"   [recorded: 1.22x]  {'REPRODUCES' if abs(sco['g2c'] - 1.22) < 0.03 else '*** DOES NOT REPRODUCE ***'}")
        print(f"    highway lane change (93.35 km/h, 38 deg/s)       : {sco['hw']:5.2f}x"
              f"   [recorded: 1.00x]  {'REPRODUCES' if abs(sco['hw'] - 1.00) < 0.01 else '*** DOES NOT REPRODUCE ***'}")
        print(f"    grind #1 REGION (2-5 mph x 16-128 deg/s)         : min {sco['g1_min']:.2f}x"
              f"  median {sco['g1_med']:.2f}x  max {sco['g1_max']:.2f}x")
        print(f"    manual creep (0-14 km/h x 150-521 deg/s)         : median {sco['mc_med']:.2f}x"
              f"  max {sco['mc_max']:.2f}x")
        print(f"    HUMP, max over 0-60 km/h x 0-521 deg/s           : {sco['hump']:5.2f}x"
              f"  at {sco['hump_kmh']:.1f} km/h / {sco['hump_degs']} deg/s"
              f"   [recorded: ~2.45x]")

    print("\n  THE HUMP, RESOLVED IN SPEED (scale A, at the rate that maximises it):")
    hm, hk, hd = surface_max(DESIGN_A, SCALE_A)
    print(f"    {'km/h':>7} {'mult @' + str(hd) + ' deg/s':>16} {'mult @128 deg/s':>17} {'mult @24 deg/s':>16}")
    for k in (0, 2, 4, 6, 7.2, 8, 9, 9.6, 10.0, 10.4, 11, 12, 14, 17, 20, 25, 30, 40, 50):
        print(f"    {k:7.1f} {M(k, hd, DESIGN_A, SCALE_A):16.2f} "
              f"{M(k, 128, DESIGN_A, SCALE_A):17.2f} {M(k, 24, DESIGN_A, SCALE_A):16.2f}")
    width = [k for k in SWEEP_KMH if M(k, hd, DESIGN_A, SCALE_A) >= 2.5]
    print(f"    => above 2.5x for speeds {min(width):.1f}-{max(width):.1f} km/h at {hd} deg/s"
          if width else "    => never exceeds 2.5x")
    print("    => 🛑 THE RECORDED '~2.45x hump' IS AN UNDERSTATEMENT. 2.45x is the value at"
          f" grind #1's\n       128 deg/s only. The true maximum is {hm:.2f}x, at {hk:.1f} km/h /"
          f" {hd} deg/s, and it sits\n       in a speed band real cars drive through constantly.")

    print("\n  🛑 AND THE COST NOBODY COSTED: Design A's boost is a RAMP that only starts at the")
    print("     axis-400 breakpoint. V62's measured fix was LARGEST at |rate| 16-32 deg/s (42x")
    print("     suppression). Design A there (scale A):")
    print(f"    {'deg/s':>7} {'axis':>6} " + "".join(f"{k:>9.1f}" for k in G1_KMH) + "   km/h")
    for d in (8, 16, 24, 32, 48, 64, 85, 100, 128, 160, 200, 256):
        print(f"    {d:7d} {axis(d, SCALE_A):6d} "
              + "".join(f"{M(k, d, DESIGN_A, SCALE_A):9.2f}" for k in G1_KMH))
    print("     => at 16-32 deg/s Design A delivers ~1.2-1.4x, not 2x. It is sized for a rate")
    print("        band that is NOT where V62's effect was measured. [EVIDENCE: the table above]")

    rule("T3b. SATURATION -- against the ACTUAL cached measurements")
    for lab, g in (("stock creep LERP", G(7.2, 128, STOCK, SCALE_A)),
                   ("V67/V68 arm", ARM_GATE),
                   ("Design A peak gain", 7051)):
        sat = saturating_dtorque(g)
        naive = (LANE_CLAMP << 10) // g
        print(f"  {lab:20} gain {g:5d}  saturates at |dtorque| >= {sat:5d} "
              f"(naive no-deadzone {naive})   worst product "
              f"{DTORQUE_CLAMP * g / INT32_MAX * 100:.2f}% of INT32_MAX")
    print(f"  [recorded claim: Design A saturates at |dtorque| >= 1190 vs a measured max of 839]")
    print(f"  -> the naive figure for 7051 is {(LANE_CLAMP << 10) // 7051}; through the real lane"
          f" (deadzone {DEADZONE}) it is {saturating_dtorque(7051)}. The recorded 1190 is the")
    print("     naive one. Immaterial, but the lane's own answer is the larger number.")
    print("\n  MEASURED |dtorque| from _cache_v68, via the firmware's own difference transfer")
    print("  function |H(f)| = |sin(pi*f*0.004)| applied to the bar channel `tq` (100.000 Hz):")
    print(f"  {'cache':>12} {'v p50':>7} {'|dt| max':>9} {'|dt| p99.9':>11} {'|tq| max':>9}")
    rows = measured_dtorque()
    for base, v, mx, p999, tqmx in rows:
        print(f"  {base:>12} {v:7.1f} {mx:9.1f} {p999:11.1f} {tqmx:9.0f}")
    allmax = max(r[2] for r in rows)
    print(f"  => corpus max on these 9 caches: {allmax:.0f} counts, vs the repo's recorded 123-839.")
    print(f"  => the 28 Hz burst itself: 1468 counts p-p at 28.12 Hz -> |dtorque| = "
          f"{dtorque_from_burst(1468, 28.12):.0f} counts.")
    print(f"  => saturation margin for Design A's peak gain: "
          f"{saturating_dtorque(7051) / max(allmax, 839):.2f}x. CLAIM STANDS (it is not close).")
    print("  🛑 CAVEAT ON ALL OF THESE: CAN is 100.000 Hz, Nyquist 50.00. Any bar content above")
    print("     50 Hz contributes to the real gp-0x4f62 and is INVISIBLE here, and |H(f)| is")
    print("     RISING through that band (0.35 at 28 Hz, 0.59 at 50, 0.95 at 100). So every")
    print("     |dtorque| number in this kit is a LOWER BOUND. [BELIEF that it is a tight one]")

    # ---------------------------------------------------------------------------- T4
    rule("T4. SEARCHING THE SURFACE FOR SOMETHING BETTER")
    print("""
  THE CONSTRAINTS, as given:
     (a) >= 2.0x at grind #1                 (b) <= 1.1x at the highway lane change
     (c) no hump above ~2.5x anywhere reachable   (d) minimal change at manual creep

  ★ CONSTRAINT (b) IS FREE, AND THAT IS A STRUCTURAL RESULT, NOT A TUNING ONE. [EVIDENCE]
  The lane-change point is 93.35 km/h = 5980 counts, which lies in CROSS_X's [3200, 6400] segment.
  The cross-interpolation there reads ONLY rec2 (0xD2AEC) and rec3 (0xD2B28). So ANY edit confined
  to rec0 (0xD2A74) and rec1 (0xD2AB0) is EXACTLY 1.000x at every speed >= 50 km/h, on every axis
  scale, at every rate. Proven by sweep below, not asserted.

  🛑 CONSTRAINTS (a) AND (d) CANNOT BOTH BE MET ROBUSTLY. Also structural:
  grind #1 and manual creep share the SAME speed cells; only the rate axis can separate them
  (~128 deg/s vs ~256 deg/s). Whether the rate axis CAN separate them depends entirely on the
  unresolved scale -- on scale A they straddle the 400-count breakpoint, on scale B they are both
  deep inside the flat first segment and NOTHING separates them. Any design that leans on the rate
  axis is a bet on scale A; any design that does not, changes manual creep by the same factor it
  changes grind #1.""")

    print("\n  ZERO-COST CHECK ON (b): max multiplier at or above 50 km/h, over all designs here:")
    for nm, rc in (("Design A", DESIGN_A),):
        worst = max(M(k, d, rc, s) for k in (50, 60, 80, 93.35, 110, 130)
                    for d in range(0, 522, 8) for _, s in SCALES)
        print(f"    {nm:12} {worst:.6f}x   (exact 1.0 => rec2/rec3 untouched)")

    print("\n  THE SEARCH  (8 families of 1-4 halfword edits confined to rec0/rec1; objective =")
    print("  maximise the grind #1 region's minimum multiplier on the WORSE of the two axis")
    print(f"  scales, subject to hump <= {HUMP_CAP}x on BOTH, tie-broken by least manual-creep change):")
    winners = search()
    cands = [(nm + f"  {p}", rc, "") for nm, p, rc, _ in winners]
    cands = [(nm, rc, NOTES.get(nm.split()[0], "")) for nm, rc, _ in cands]
    cands = ([("V62x4  rec0.Y[0]=Y[1]=6144, rec1.Y[0]=Y[1]=5122  (4 hw)",
               V62_MATCHED, NOTES["V62x4"]),
              ("V62x2  rec1.Y[0]=Y[1]=5122  (2 hw)", V62_MATCHED_2HW, NOTES["V62x2"]),
              ("Design A (recorded, for reference)", DESIGN_A, NOTES["DA"])] + cands)

    rule("T4b. THE BEST CANDIDATES")
    for rank, (nm, rc, note) in enumerate(cands, 1):
        cells = design_cells(rc)
        print(f"\n  ---- #{rank}  {nm}")
        print(f"       {note}")
        print(f"       {len(cells)} halfword(s), all in CRC block "
              f"{crc_block_of(cells[0][0])}:")
        for a, o, n, w in cells:
            print(f"         0x{a:05X}  {w:7}  {o:5d} -> {n:5d}   "
                  f"bytes {struct.pack('<H', o).hex(' ')} -> {struct.pack('<H', n).hex(' ')}")
        for lab, s in SCALES:
            sco = score(rc, s)
            print(f"       scale {lab[:1]}: grind#1 pt {sco['g1_point']:.2f}x | region "
                  f"min {sco['g1_min']:.2f} med {sco['g1_med']:.2f} | creep g#2 {sco['g2c']:.2f}x"
                  f" | manual-creep med {sco['mc_med']:.2f} max {sco['mc_max']:.2f}"
                  f" | highway {sco['hw']:.2f}x | HUMP {sco['hump']:.2f}x @"
                  f" {sco['hump_kmh']:.1f} km/h/{sco['hump_degs']} deg-s")
        print(f"       FULL MULTIPLIER SURFACE (scale A; rows km/h, cols deg/s):")
        _surface_table(rc, SCALE_A)
        print(f"       FULL MULTIPLIER SURFACE (scale B):")
        _surface_table(rc, SCALE_B)
        g = max(G(k, d, rc, s) for k in SWEEP_KMH for d in (0, 85, 128, 256, 400, 521)
                for _, s in SCALES)
        print(f"       peak gain {g}, lane saturates at |dtorque| >= {saturating_dtorque(g)}"
              f" vs measured {allmax:.0f}  (margin {saturating_dtorque(g) / max(allmax, 839):.2f}x);"
              f" worst product {DTORQUE_CLAMP * g / INT32_MAX * 100:.2f}% of INT32_MAX")

    rule("T4c. HEAD-TO-HEAD, INCLUDING WHAT IS ON THE CAR NOW")
    hdr = (f"  {'design':34} {'g1 pt':>6} {'g1 min':>7} {'g#2c':>6} {'mcreep':>7} "
           f"{'hwy':>6} {'hump':>6}")
    for lab, s in SCALES:
        print(f"\n  --- scale {lab} ---")
        print(hdr)
        for nm, rc in [("STOCK (no edit)", STOCK)] + [(c[0][:34], c[1]) for c in cands]:
            sco = score(rc, s)
            print(f"  {nm:34} {sco['g1_point']:6.2f} {sco['g1_min']:7.2f} {sco['g2c']:6.2f} "
                  f"{sco['mc_med']:7.2f} {sco['hw']:6.2f} {sco['hump']:6.2f}")
        st_g1 = G(*G1_POINT, STOCK, s)
        st_g2 = G(*G2C_POINT, STOCK, s)
        st_hw = G(*HW_POINT, STOCK, s)
        print(f"  {'V68 AS FLOWN (engaged; arm 5244)':34} {ARM_GATE / st_g1:6.2f} "
              f"{'  n/a':>7} {ARM_GATE / st_g2:6.2f} {1.00:7.2f} {ARM_GATE / st_hw:6.2f} "
              f"{ARM_GATE / min(G(k, d, STOCK, s) for k in SWEEP_KMH for d in SWEEP_DEGS):6.2f}")
        print("   (V68's 'manual creep' is 1.00 only because the gate is CLOSED there; its hump")
        print("    column is the worst multiplier its flat arm reaches anywhere it is open.)")

    rule("T4d. SELF-CHECKS -- the load-bearing claims, brute-forced  [EVIDENCE]")
    named = [("Design A", DESIGN_A), ("V62x4", V62_MATCHED), ("V62x2", V62_MATCHED_2HW)] + \
            [(c[0][:24], c[1]) for c in cands[3:]]
    for nm, rc in named:
        worst = max(abs(M(k, d, rc, s) - 1.0)
                    for k in [50 + 0.5 * i for i in range(170)]
                    for d in range(0, 522, 4) for _, s in SCALES)
        print(f"  {nm:26} max |mult - 1| over speed >= 50 km/h x 0-521 deg/s x both scales:"
              f" {worst:.9f}")
    print("  => every design here is BIT-EXACTLY stock at and above 50 km/h. Brute-forced, not argued.")
    print()
    print("  🛑 THE FOLD DISCONTINUITY, which any Y[0] raise makes larger (@0x3AAC8 addi -0x32c9):")
    for nm, rc in (("stock", STOCK), ("Design A", DESIGN_A), ("V62x4", V62_MATCHED)):
        lo, hi = gain_q10(0, FOLD - 1, rc), gain_q10(0, FOLD, rc)
        print(f"    {nm:10} idx {FOLD - 1} -> {FOLD}: gain {lo} -> {hi}  (jump {hi / lo:.2f}x)")
    print(f"    {FOLD} counts = {FOLD / SCALE_A:.0f} deg/s (scale A) or {FOLD / SCALE_B:.0f}"
          f" (scale B); |rate| has never exceeded 521 deg/s in 407,617 frames, so this is a")
    print("    fault/glitch path either way -- but V62x4 doubles the step it produces.")
    print("\n  Every V62x4 value is EXACTLY 2x the halfword it replaces, read from the image:")
    for a in (0xD2A7E, 0xD2A80, 0xD2ABA, 0xD2ABC):
        print(f"    0x{a:05X}: {u16(a)} -> {2 * u16(a)}")

    rule("9. WHAT THIS FILE DOES NOT SETTLE")
    print("""
  1. 🛑 THE INNER-AXIS SCALE. Every rate-discriminating result above is conditional on it, and it
     has never been measured. Resolving it is ONE Ghidra trace: gp-0x6ac0's writer, and whether
     `bus = (gp-0x6abe*48*1159)>>15` or `gp-0x6ac0 = |gp-0x6abe|` is the wrong premise. Until
     then, prefer a design whose grind #1 number holds on BOTH scales.
  2. The 28 Hz lane-change mode's MECHANISM. Nothing here shows the rate lane causes it; the
     26-30 Hz dose ratio 3.334 [1.201, 6.492] sits inside its own null [0.33, 3.36]. These designs
     REMOVE V68's highway dose (2.44x -> 1.00x) -- they do not prove that dose is the cause.
  3. Whether 2.00x at MANUAL creep is acceptable. V62 ran a flat 2.00x ungated at every speed and
     the operator drove it and reported grind #1 fixed, so it is precedented; but V62 also is what
     created creep grind #2 at 40-49 Hz. [BELIEF, from the build record]""")


# =====================================================================================================
# helpers used by main()
# =====================================================================================================
def _surface_table(recs, scale, kmhs=(0, 3.2, 5, 7.2, 10, 14.4, 20, 30, 50, 93.35),
                   degss=(8, 16, 24, 32, 64, 128, 200, 256, 400, 521)):
    print("         km/h |" + "".join(f"{d:>7}" for d in degss))
    for k in kmhs:
        print(f"       {k:6.2f} |" + "".join(f"{M(k, d, recs, scale):7.2f}" for d in degss))


_BLOCKS = None


def crc_block_of(addr: int) -> str:
    global _BLOCKS
    if _BLOCKS is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import verify_bootloader_crc as V
        _BLOCKS = []
        for item in V._blocks(B, 0x13000, 0xED000, False):
            if item[0] == "OOB":
                break
            _BLOCKS.append(item)
    for i, (s, l) in enumerate(_BLOCKS, 1):
        if s <= addr < s + l:
            return f"#{i} [0x{s:06X}, 0x{s + l:06X}) crc@0x{s + l:06X}"
    return "NOT IN ANY BLOCK"


def _cross_build_check():
    import glob
    bad = []
    n = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "analysis-2020accord", "_v*_plain_image.bin"))):
        try:
            with open(p, "rb") as f:
                o = f.read()
        except OSError:
            continue
        if len(o) != len(B):
            continue
        n += 1
        for r in RECS10:
            if o[r["rec"]:r["rec"] + 20] != B[r["rec"]:r["rec"] + 20]:
                bad.append((os.path.basename(p), hex(r["rec"])))
    print(f"    {n} images checked, {len(bad)} record difference(s) -> "
          f"{'ALL IDENTICAL' if not bad else bad}")


# --- the search ---------------------------------------------------------------------------------
# Stage-1 filter grid: coarse, but placed where a hump can actually sit (rec0/rec1 edits can only
# perturb speeds < 50 km/h, and the cross-interpolation peaks on or between the two raised records).
FILT_KMH = (0.0, 1.6, 3.2, 5.0, 7.2, 9.0, 10.0, 11.0, 14.4, 20.0, 30.0, 40.0)
FILT_DEGS = (0, 8, 16, 24, 32, 48, 64, 85, 100, 128, 160, 200, 256, 320, 400, 460, 521)
HUMP_CAP = 2.5
G1_REGION_KMH = (3.2, 4.0, 5.0, 6.0, 7.2, 8.0)       # the operator's "2-5 mph", plus slack
G1_REGION_DEGS = (16, 24, 32, 48, 64, 85, 128)       # V62's measured band, through V67's point


def _filt(recs, scale):
    ms = [[M(k, d, recs, scale) for d in FILT_DEGS] for k in FILT_KMH]
    hump = max(max(r) for r in ms)
    g1 = [M(k, d, recs, scale) for k in G1_REGION_KMH for d in G1_REGION_DEGS]
    mc = [M(k, d, recs, scale) for k in MC_KMH for d in MC_DEGS]
    return hump, min(g1), float(np.median(g1)), float(np.median(mc))


def _rank(recs):
    """(worst-scale grind #1 region minimum, then LOW manual-creep median) subject to hump cap."""
    hA, g1A, gmA, mcA = _filt(recs, SCALE_A)
    hB, g1B, gmB, mcB = _filt(recs, SCALE_B)
    if max(hA, hB) > HUMP_CAP:
        return None
    return (min(g1A, g1B), -max(mcA, mcB), min(gmA, gmB))


FAMILIES = (
    ("F1  rec1.Y[1]                       (1 hw)",
     lambda p: edit(r1Y=(None, p[0], None, None)),
     [(v,) for v in range(2600, 13000, 25)]),
    ("F2  rec1.Y[0]=Y[1]                  (2 hw)",
     lambda p: edit(r1Y=(p[0], p[0], None, None)),
     [(v,) for v in range(2600, 13000, 25)]),
    ("F3  rec0.Y[1], rec1.Y[1]            (2 hw)",
     lambda p: edit(r0Y=(None, p[0], None, None), r1Y=(None, p[1], None, None)),
     [(a, b) for a in range(3100, 13000, 150) for b in range(2600, 13000, 150)]),
    ("F4  rec0.Y[0]=Y[1]                  (2 hw)",
     lambda p: edit(r0Y=(p[0], p[0], None, None)),
     [(v,) for v in range(3100, 13000, 25)]),
    ("F5  rec0.Y[1], rec1.Y[0]=Y[1]       (3 hw)",
     lambda p: edit(r0Y=(None, p[0], None, None), r1Y=(p[1], p[1], None, None)),
     [(a, b) for a in range(3100, 13000, 150) for b in range(2600, 13000, 150)]),
    ("F6  rec1.Y[0]=Y[1], rec1.Y[2]       (3 hw)",
     lambda p: edit(r1Y=(p[0], p[0], p[1], None)),
     [(a, b) for a in range(2600, 13000, 100) for b in range(200, 2300, 100)]),
    ("F7  rec1.X[1], rec1.Y[1]            (2 hw)",
     lambda p: edit(r1X=(None, p[0], None, None), r1Y=(None, p[1], None, None)),
     [(x, v) for x in range(50, 1500, 25) for v in range(2600, 13000, 200)]),
    ("F8  rec0.Y[0]=Y[1], rec1.Y[0]=Y[1]  (4 hw, OVER BUDGET -- the foil)",
     lambda p: edit(r0Y=(p[0], p[0], None, None), r1Y=(p[1], p[1], None, None)),
     [(a, b) for a in range(3100, 13000, 150) for b in range(2600, 13000, 150)]),
)


def search(verbose=True):
    """Constrained search: maximise the grind #1 region's WORST-CASE-OVER-SCALES minimum
    multiplier, subject to hump <= 2.5 on BOTH scales, tie-broken by low manual-creep change."""
    winners = []
    for name, mk, grid in FAMILIES:
        best = None
        for p in grid:
            rc = mk(p)
            if any(rc[i][0][j] >= rc[i][0][j + 1] for i in (0, 1) for j in range(3)):
                continue                                   # X must stay strictly increasing
            r = _rank(rc)
            if r and (best is None or r > best[0]):
                best = (r, p, rc)
        if best:
            winners.append((name, best[1], best[2], best[0]))
        if verbose:
            print(f"    {name}: " +
                  (f"best params {best[1]}  -> g1_min(worst scale) {best[0][0]:.2f}"
                   f"  manual-creep {-best[0][1]:.2f}" if best else "no feasible point"))
    winners.sort(key=lambda w: w[3], reverse=True)
    return winners


if __name__ == "__main__":
    main()
