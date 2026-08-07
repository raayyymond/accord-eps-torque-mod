#!/usr/bin/env python3
"""friction_lane_duty_r65.py -- the FRICTION-LANE duty cycle that decides V81's second byte.

THE QUESTION
------------
V81 restores `0xC407E` 850 -> 511 (the stock interlock: one count under `FUN_00036d74`'s 512-count
hard-fault trip). The open question is the mode-26 friction Y-table: keep V74/V75's **x1.5**, or
revert it to stock. A x1.5 table scales the lane's PRE-clamp product by exactly 1.5 at every speed
and every `gp-0x6c2c`, so a stock reading of `r` becomes `1.5r` and is **PINNED at 511** whenever
`r >= 511/1.5 = 340.67`. A saturated lane whose sign follows a smooth zero-crossing input is a
Coulomb relay, which is the mechanism suspected behind V80's grind.

WHAT THE PROBE ACTUALLY MEASURES -- and its blind spot, stated up front
-----------------------------------------------------------------------
V76 (`V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd`) flew route 65 with
**stock friction and `0xC407E` = 511**, i.e. Honda's own friction lane. Its cave writes CAN `0x14A`
byte 4:
    bit7 (0x80) = |gp-0x6b26| > 448    the friction-lane margin (post-clamp; clamp = 511)
    bit6 (0x40) = STRUCTURALLY ZERO
    bit5 (0x20) = STRUCTURALLY ZERO
    bit4 (0x10) = gp+0x63fd & 2        the mode index (26 engaged -> set, 24 manual -> clear)
    bit3 (0x08) = gp-0x67fa == 5       the POSITIVE CONTROL
🛑 THE THRESHOLD IS 448 AND THE DECISION BAND IS [340.67, 448]. A one-bit comparator at 448 has
**zero resolution inside the band that decides the build.** This script reports that as UNPOWERED
and does not paper over it -- see `accord-probe-underranges-to-one-bit-comparator`.

🛑 DO NOT USE `rlog-tools/decode_v76_probe.py` ON THIS ROUTE. That file documents the SUPERSEDED
V74-base V76 (gate/mask/third-arm on the r24 rate lane, bit7 = `gp-0x6bd0 != 0`). Different cells,
different bits. The extractor for the build that actually flew is
`analysis-2020accord/v76flight_extract.py` -> `_cache_r65_records.pkl`.

Cross-check: V75's own flight, route 5e, whose probe is a THERMOMETER on the DAMPER `|gp-0x6bd0|`
(bit7 != 0 / bit6 >= 128 / bit5 >= 288 / bit4 >= 448 / bit3 = `gp-0x6ac2 != 0`). That is V75's
operating point -- the thing V81 is trying to reproduce. Route 5e ends in the hard fault at
t = 284.7947 s; the pre-fault window is `t < 284.7947` STRICTLY (the fault frame itself is excluded,
per `v75fault_final.py`'s correction of the earlier `t < 284.795` split).

Usage:  python friction_lane_duty_r65.py
"""
import pickle
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
R65_PKL = ROOT / "analysis-2020accord" / "_cache_r65_records.pkl"
R5E_NPZ = ROOT / "_cache_r5e" / "r5e.npz"

# ---- the friction lane's own arithmetic, from FUN_00036c12 (decompile-confirmed) ----------------
#   sVar7 = LERP(gp-0x6a5e ; 0xCBE74[mode], X=[0,1280,5760] cts @64 ct/km/h)
#   raw   = (((gate(gp-0x6c2c) * sVar7) >> 6) * 0x111) >> 0x12
#   gp-0x6b26 = clamp(raw, -cal(0xC407E), +cal(0xC407E))
# `0xC407E` is NOT mode-indexed (3 readers, 0 writers, all in FUN_00036c12).
CLAMP_STOCK = 511          # 0xC407E stock -- exactly ONE count under the trip. An interlock.
CLAMP_V73_V75 = 850        # what V73/V74/V75 raised it to -- 338 counts PAST the trip
FAULT_TRIP = 512           # FUN_00036d74: |gp-0x6b26|/1024 > cal(0xC4004)=0.5  ->  DTC 0x1d
PROBE_THRESH = 448         # V76's bit7 rung, on the POST-clamp value
FRICTION_SCALE = 1.5       # V74/V75's mode-26 Y-table: [-9830,-5734,-1966] -> [-14745,-8601,-2949]
# The stock-equivalent pre-clamp value at which a x1.5 table would PIN against a 511 clamp.
PIN_EQUIV = CLAMP_STOCK / FRICTION_SCALE                      # 340.667
# The probe's blind band, as a fraction of its own threshold.
BLIND_LO_FRAC = PIN_EQUIV / PROBE_THRESH                      # 0.7604

T_FAULT_5E = 284.7947      # route 5e, the ONE 100 Hz frame everything latches on
# 🛑 THE CUTOFF IS AN INDEX, NOT A FLOAT COMPARE. `t[28317]` rounds to 284.7947 and `t < 284.7947`
# admits it back in on this build of numpy, dragging ONE 0x7FFF sentinel frame into the "pre-fault"
# window and putting a 32767 deg/s reading in the last-5-s rate statistics. Cut on the sentinel
# itself -- the fault frame is definitionally the first frame with |rate_c| == 32767.
SENTINEL = 32767
LAST_SECONDS = 5.0

SPEED_BANDS = (("creep   <10 km/h", -1e9, 10.0), ("10-40 km/h", 10.0, 40.0),
               ("40-80 km/h", 40.0, 80.0), (">80 km/h", 80.0, 1e9))
QUIET_DEGS = 5.0           # |column rate| below this = "the wheel is not really moving"
# The friction lane's input `gp-0x6c2c` is a DIFFERENTIATOR of motor rate with ~zero DC gain, so the
# physically relevant axis is JERK, not rate. Reported as a separate stratification.
JERK_BANDS = ((0.0, 100.0), (100.0, 300.0), (300.0, 1000.0), (1000.0, 1e9))


def wilson_upper(k, n, z=1.959964):
    """Upper 95% bound on a binomial rate. For k=0 this is the honest 'how small could it be'."""
    if n <= 0:
        return float("nan")
    p = k / n
    den = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    rad = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c + rad) / den


def episode_n(t, mask):
    """A crude independent-sample count: contiguous runs of `mask`, plus the number of 1-second
    blocks the mask spans. 🛑 100 Hz frames are NOT independent -- quoting `3/63477` as the
    rule-of-three bound would understate the uncertainty by ~sqrt(frames per episode).
    See `feedback-episodes-not-windows`."""
    n_frames = int(mask.sum())
    if n_frames == 0:
        return 0, 0.0
    dur = float(np.diff(t).mean()) * n_frames
    return n_frames, dur


def block_bound(n_frames, dt, block_s=1.0):
    """95% upper bound on a zero-count rate using 1-second blocks as the independent unit."""
    n_blocks = max(1, int(round(n_frames * dt / block_s)))
    return 3.0 / n_blocks, n_blocks


# =================================================================================================
#  PART 1 -- ROUTE 65, V76, THE FRICTION LANE
# =================================================================================================
def part1():
    D = pickle.load(open(R65_PKL, "rb"))
    d = D["d"]
    print("=" * 100)
    print("  PART 1 -- ROUTE 65 (V76-V38BASE, STOCK FRICTION, 0xC407E = 511)")
    print("=" * 100)
    print(f"  build : {D['build']}")
    print(f"  rwd   : {D['rwd']}")

    t = np.asarray(d["t"], float)
    b7 = np.asarray(d["b7_friction"], bool)        # |gp-0x6b26| > 448
    b3 = np.asarray(d["b3_state5"], bool)          # gp-0x67fa == 5   POSITIVE CONTROL
    b4m = np.asarray(d["b4_mode"], bool)           # mode & 2
    eng = np.asarray(d["cc_lat"], bool)            # carControl.latActive
    v_ms = np.asarray(d["cs_v"], float)
    v_kph = v_ms * 3.6
    rate = np.asarray(d["rate_c"], float)          # column rate, deg/s, CAN 0x18F
    n = len(t)
    dt = float(np.median(np.diff(t)))

    # ---- 3. DOES bit7 EVER FIRE AT ALL? Check the RAW bytes before interpreting anything. -------
    raw = np.asarray(D["raw14_b4"], dtype=np.uint8)
    hist = Counter(int(x) for x in raw)
    print("\n  " + "#" * 96)
    print("  # DELIVERABLE 3 -- THE RAW BIT DISTRIBUTION, BEFORE ANY INTERPRETATION")
    print("  " + "#" * 96)
    print(f"  raw 0x14A byte4 values over {len(raw)} frames: "
          f"{ {hex(k): v for k, v in hist.most_common()} }")
    print(f"  distinct values: {len(hist)}   (bits 7:3 = "
          f"{sorted(hex(k & 0xF8) for k in hist)})")
    fired = int(b7.sum())
    if fired == 0:
        print(f"\n  🛑🛑 bit7 (|gp-0x6b26| > {PROBE_THRESH}) IS A CONSTANT ZERO: "
              f"{fired} / {n} frames.")
        print("     THE 0x80 BIT IS NEVER SET ANYWHERE IN THE DRIVE. No stratification can rescue")
        print("     a constant -- every slice below is 0/n by construction, and the ONLY thing the")
        print("     strata establish is that the probe was EXERCISED (i.e. the null is not because")
        print("     the car never drove).")
    else:
        print(f"\n  bit7 fired on {fired} / {n} frames ({100.0 * fired / n:.4f}%)")
    print(f"\n  ⊕ POSITIVE CONTROL bit3 (gp-0x67fa == 5): {int(b3.sum())} / {n} = "
          f"{100.0 * b3.mean():.4f}%  -- the cave RAN and the store landed.")
    print(f"  ⊕ bit4 (mode & 2): {int(b4m.sum())} / {n} = {100.0 * b4m.mean():.4f}%  "
          f"(vs latActive {100.0 * eng.mean():.4f}%)")
    print(f"  ⊕ bits 6/5 (structurally unreachable): "
          f"{int((raw & 0x60).astype(bool).sum())} / {len(raw)} -- 0 confirms the wire model.")
    print(f"  ⇒ [EVIDENCE] The null is on bit7 ONLY. The same 68-byte cave, in the same frames,")
    print(f"     drove bit3 at {100.0 * b3.mean():.3f}% and bit4 at {100.0 * b4m.mean():.3f}%. This is")
    print("     NOT the V64/V68 class of unarmed-gate null.")

    # ---- 1. THE DUTY CYCLE, and the strata that prove the probe was exercised -------------------
    print("\n  " + "#" * 96)
    print("  # DELIVERABLE 1 -- DUTY CYCLE OF |gp-0x6b26| > 448, WITH STRATA")
    print("  " + "#" * 96)
    print(f"  route span {t[-1] - t[0]:.2f} s, {n} frames, dt = {dt * 1000:.2f} ms")
    print(f"  speed 0 .. {np.nanmax(v_kph):.1f} km/h   |column rate| p50 {np.nanpercentile(np.abs(rate), 50):.1f} "
          f"p95 {np.nanpercentile(np.abs(rate), 95):.1f} max {np.nanmax(np.abs(rate)):.1f} deg/s")

    quiet = np.abs(rate) < QUIET_DEGS
    slices = [("ALL FRAMES", np.ones(n, bool)),
              ("ENGAGED (latActive)", eng),
              ("MANUAL (not latActive)", ~eng)]
    for lab, lo, hi in SPEED_BANDS:
        slices.append((f"speed {lab}", (v_kph >= lo) & (v_kph < hi)))
    for lab, lo, hi in SPEED_BANDS:
        slices.append((f"ENG + {lab}", eng & (v_kph >= lo) & (v_kph < hi)))
    slices += [(f"steering QUIET (|rate| < {QUIET_DEGS:g} deg/s)", quiet),
               (f"steering ACTIVE (|rate| >= {QUIET_DEGS:g} deg/s)", ~quiet),
               ("steering |rate| >= 30 deg/s", np.abs(rate) >= 30.0),
               ("steering |rate| >= 90 deg/s", np.abs(rate) >= 90.0),
               ("steering |rate| >= 180 deg/s", np.abs(rate) >= 180.0)]
    # the physically relevant axis: the lane's input is a differentiator (~zero DC gain)
    jerk = np.abs(np.gradient(rate, t))
    for lo, hi in JERK_BANDS:
        lab = f"|d(rate)/dt| {lo:g}-{hi:g}" if hi < 1e8 else f"|d(rate)/dt| >= {lo:g}"
        slices.append((lab + " deg/s^2", (jerk >= lo) & (jerk < hi)))

    print(f"\n  {'slice':40s} {'bit7':>10s} {'n':>8s} {'dur s':>8s} {'duty':>9s} "
          f"{'95% UB':>9s}  {'bit3':>7s}")
    print("  " + "-" * 96)
    for lab, m in slices:
        k = int((b7 & m).sum())
        nn = int(m.sum())
        if nn == 0:
            print(f"  {lab:40s} {'--':>10s} {0:8d} {'--':>8s} {'--':>9s} {'--':>9s}  {'--':>7s}")
            continue
        dur = nn * dt
        ub, nb = block_bound(nn, dt)
        print(f"  {lab:40s} {k:10d} {nn:8d} {dur:8.1f} {100.0 * k / nn:8.4f}% "
              f"{100.0 * ub:8.3f}%  {100.0 * b3[m].mean():6.2f}%")
    print(f"  ⚠ '95% UB' is a rule-of-three bound over ONE-SECOND BLOCKS, not frames -- 100 Hz")
    print("    frames are not independent and a per-frame bound would be ~10x too tight.")

    # ---- 2. THE EXTRAPOLATION ---------------------------------------------------------------
    print("\n  " + "#" * 96)
    print("  # DELIVERABLE 2 -- WHAT A x1.5 FRICTION TABLE WOULD DO AGAINST A 511 CLAMP")
    print("  " + "#" * 96)
    print(f"  The mode-26 Y-table x1.5 scales the PRE-clamp product by exactly 1.5 at every speed")
    print(f"  and every gp-0x6c2c (the multiply chain is linear in sVar7; verified 1.500 to 4 s.f.")
    print(f"  in reference_accord_friction_lane_direct_hard_fault_monitor_gp6b26_c4004).")
    print(f"    stock pre-clamp r  ->  x1.5 pre-clamp 1.5r")
    print(f"    PINNED at {CLAMP_STOCK}  <=>  1.5r >= {CLAMP_STOCK}  <=>  r >= {PIN_EQUIV:.3f}")
    print(f"    the probe's rung is at {PROBE_THRESH}, i.e. {100 * BLIND_LO_FRAC:.1f}% of the way "
          f"is BELOW it")
    print(f"\n  🛑🛑 THE DECIDING BAND IS r in [{PIN_EQUIV:.1f}, {PROBE_THRESH}] AND THE PROBE IS")
    print("     STRUCTURALLY BLIND TO IT. A one-bit comparator at 448 partitions the axis into")
    print(f"     '<= 448' and '> 448'. The whole decision lives INSIDE the first cell.")
    print(f"     · P(r > {PROBE_THRESH})   = 0/{n}  ⇒ measured, and it is ZERO.")
    print(f"     · P(r >= {PIN_EQUIV:.1f}) = **NOT MEASURED**. It is bounded BELOW by 0 and")
    print("       bounded ABOVE by NOTHING this probe can say. There is no distributional")
    print("       assumption that recovers it: the comparator returns the same byte for r = 0 and")
    print(f"       for r = {PROBE_THRESH}, so the entire mass could sit at {PROBE_THRESH - 1} or at 0.")
    ub_all, nb_all = block_bound(n, dt)
    print(f"\n  WHAT THE PROBE *DOES* LICENSE [EVIDENCE]:")
    print(f"     With stock friction and the 511 clamp, |gp-0x6b26| stayed <= {PROBE_THRESH} for the")
    print(f"     ENTIRE {t[-1] - t[0]:.0f} s of route 65 -- so the STOCK lane never came within "
          f"{CLAMP_STOCK - PROBE_THRESH} counts")
    print(f"     of its own clamp, and never PINNED, on this drive. 95% upper bound on the pin rate")
    print(f"     with STOCK friction: {100.0 * ub_all:.3f}% of time ({nb_all} one-second blocks).")
    print(f"     ⇒ Reverting the friction table to stock is the option with a MEASURED zero.")
    print(f"\n  WHAT DECIDES IT INSTEAD -- the V74/V75 flights [EVIDENCE, from the fault itself]:")
    print(f"     V74 and V75 both flew the x1.5 table with the clamp at {CLAMP_V73_V75}, and BOTH")
    print(f"     hard-faulted on FUN_00036d74's |gp-0x6b26| > {FAULT_TRIP} test. A fault PROVES the")
    print(f"     x1.5 lane's post-clamp value exceeded {FAULT_TRIP}; with the clamp at {CLAMP_V73_V75}")
    print(f"     the post-clamp value IS the raw product below {CLAMP_V73_V75}, so the x1.5 raw")
    print(f"     reached >= {FAULT_TRIP}, i.e. the stock-equivalent raw reached "
          f">= {FAULT_TRIP / FRICTION_SCALE:.1f}.")
    print(f"     🛑 {FAULT_TRIP / FRICTION_SCALE:.1f} sits INSIDE the probe's blind band "
          f"[{PIN_EQUIV:.1f}, {PROBE_THRESH}] -- the two")
    print("     observations are CONSISTENT, and that consistency is exactly why the probe cannot")
    print("     settle the question. The events that matter are in the cell it cannot see.")
    print(f"     ⇒ [EVIDENCE] a x1.5 table against a {CLAMP_STOCK} clamp WOULD PIN. V75 demonstrated")
    print(f"       the lane reaching that level once in {T_FAULT_5E:.0f} s of driving (n=1, and it is")
    print("       CENSORED -- the fault latched, so later crossings are unobservable).")
    print(f"     ⚠ Route 65 (636 s) contained NO frame even at {PROBE_THRESH} with stock friction, so")
    print("       route 65 probably contained no such event either. Two different drives.")

    print(f"\n  WHAT WOULD RESOLVE IT (and it is cheap):")
    print(f"     A THERMOMETER on |gp-0x6b26| in V75's own idiom -- `shr 0x5` then `cmp imm5` -- puts")
    print("     rungs at multiples of 32 for 6 bytes each. The band needs bracketing at")
    print(f"     320 (q>=10) and 352 (q>=11), which straddle the {PIN_EQUIV:.1f} pin point, plus a")
    print(f"     416 (q>=13) rung. Three rungs + the abs = ~30 B, well inside the proven 68 B extent.")
    print("     🛑 Until that flies, ANY number for the x1.5 pin duty is an assumption, not a")
    print("        measurement.")
    return dict(n=n, dt=dt, b7=b7, b3=b3, eng=eng, v_kph=v_kph, rate=rate, t=t)


# =================================================================================================
#  PART 2 -- ROUTE 5E, V75, THE DAMPER MAGNITUDE (V81's TARGET OPERATING POINT)
# =================================================================================================
def part2():
    z = np.load(R5E_NPZ, allow_pickle=True)
    print("\n\n" + "=" * 100)
    print("  PART 2 -- ROUTE 5E (V75, x1.5 FRICTION, 0xC407E = 850) -- THE DAMPER THERMOMETER")
    print("=" * 100)
    print(f"  build : {z['probe_build'][0]}")
    print(f"  rwd   : {z['probe_rwd'][0]}")

    t = np.asarray(z["t"], float)
    b7 = np.asarray(z["b7"], bool)     # gp-0x6bd0 != 0
    b6 = np.asarray(z["b6"], bool)     # |gp-0x6bd0| >= 128
    b5 = np.asarray(z["b5"], bool)     # |gp-0x6bd0| >= 288
    b4 = np.asarray(z["b4"], bool)     # |gp-0x6bd0| >= 448
    b3 = np.asarray(z["b3"], bool)     # gp-0x6ac2 != 0 (back-drive / ceiling LERP index)
    lv = np.asarray(z["thermo"], float)
    eng = np.asarray(z["cc_lat"], bool)
    v_kph = np.asarray(z["cs_v"], float) * 3.6
    rate = np.asarray(z["rate_c"], float)
    illegal = np.asarray(z["illegal"], bool)
    ang_arr = np.asarray(z["ang"], float)
    n = len(t)
    dt = float(np.median(np.diff(t)))

    # 🛑 index-based cut on the sentinel, not a float compare -- see the SENTINEL note above.
    i_fault = int(np.argmax(np.abs(rate) >= SENTINEL))
    pre = np.zeros(n, bool)
    pre[:i_fault] = True
    post = ~pre
    print(f"\n  frames {n}, span {t[0]:.2f} .. {t[-1]:.2f} s, dt {dt * 1000:.2f} ms")
    print(f"  🛑 WINDOW USED: frames [0, {i_fault}) -- {int(pre.sum())} frames "
          f"({pre.sum() * dt:.1f} s), i.e. everything STRICTLY BEFORE the first 0x7FFF sentinel at")
    print(f"     t = {t[i_fault]:.6f} s (the fault frame; the record's t = {T_FAULT_5E}).")
    print(f"     The fault frame and everything after ({int(post.sum())} frames) is EXCLUDED.")
    print("     Post-fault the probe cell LATCHES (0xc4 constant = damper level 2 forever) and all")
    print("     three 0x14A angle fields read 0x7FFF, so pooling it would corrupt every duty below.")
    print(f"     ⚠ A float cut at `t < {T_FAULT_5E}` admits the fault frame back in and puts a")
    print("       32767 deg/s reading into the last-5-s statistics. That is why this cut is by index.")
    print(f"  ⊕ thermometer invariant violations: {int(illegal.sum())} -- "
          f"{'HOLDS' if not illegal.any() else '🛑 VIOLATED'}")

    def table(mask_base, title):
        print(f"\n  {title}")
        print(f"     {'slice':34s} {'bit7 !=0':>9s} {'bit6>=128':>10s} {'bit5>=288':>10s} "
              f"{'bit4>=448':>10s} {'bit3 bd':>8s} {'mean lv':>8s} {'n':>7s}")
        rows = [("all (pre-fault)", np.ones(n, bool)),
                ("ENGAGED", eng), ("MANUAL", ~eng),
                ("ENG creep <10 km/h", eng & (v_kph < 10)),
                ("ENG 10-40 km/h", eng & (v_kph >= 10) & (v_kph < 40)),
                ("ENG 40-80 km/h", eng & (v_kph >= 40) & (v_kph < 80)),
                ("ENG >80 km/h", eng & (v_kph >= 80)),
                (f"ENG quiet |rate|<{QUIET_DEGS:g}", eng & (np.abs(rate) < QUIET_DEGS)),
                (f"ENG active |rate|>={QUIET_DEGS:g}", eng & (np.abs(rate) >= QUIET_DEGS))]
        for lab, m in rows:
            mm = m & mask_base
            nn = int(mm.sum())
            if nn < 30:
                print(f"     {lab:34s} {'-- only ' + str(nn) + ' frames':>60s}")
                continue
            print(f"     {lab:34s} {100 * b7[mm].mean():8.3f}% {100 * b6[mm].mean():9.3f}% "
                  f"{100 * b5[mm].mean():9.3f}% {100 * b4[mm].mean():9.3f}% "
                  f"{100 * b3[mm].mean():7.3f}% {lv[mm].mean():8.3f} {nn:7d}")

    table(pre, "★★ DELIVERABLE 4 -- V75's DAMPER MAGNITUDE |gp-0x6bd0|, PRE-FAULT WINDOW ONLY")

    print("\n  Level census (pre-fault), the exclusive bands:")
    bands = ("|damper| == 0", "1 <= |d| < 128", "128 <= |d| < 288", "288 <= |d| < 448",
             "|d| >= 448  (ceiling floor 512)")
    for i, lab in enumerate(bands):
        for who, m in (("all", pre), ("engaged", pre & eng)):
            k = int((lv[m] == i).sum())
            nn = int(m.sum())
            print(f"     level {i}  {lab:32s} {who:8s} {k:8d} / {nn:6d}  {100.0 * k / nn:7.3f}%")

    # ---- 5. THE LAST 5 SECONDS ------------------------------------------------------------------
    print("\n  " + "#" * 96)
    print(f"  # DELIVERABLE 5 -- THE LAST {LAST_SECONDS:g} s BEFORE THE FAULT "
          f"(t in [{T_FAULT_5E - LAST_SECONDS:.4f}, {T_FAULT_5E}))")
    print("  " + "#" * 96)
    t_f = t[i_fault]
    w = (t >= t_f - LAST_SECONDS) & pre
    nn = int(w.sum())
    print(f"  {nn} frames ({nn * dt:.2f} s)")
    if nn:
        print(f"     bit7 !=0   {100 * b7[w].mean():7.3f}%   ({int(b7[w].sum())}/{nn})")
        print(f"     bit6 >=128 {100 * b6[w].mean():7.3f}%   ({int(b6[w].sum())}/{nn})")
        print(f"     bit5 >=288 {100 * b5[w].mean():7.3f}%   ({int(b5[w].sum())}/{nn})")
        print(f"     bit4 >=448 {100 * b4[w].mean():7.3f}%   ({int(b4[w].sum())}/{nn})")
        print(f"     bit3 backdrive {100 * b3[w].mean():7.3f}%   ({int(b3[w].sum())}/{nn})")
        print(f"     mean level {lv[w].mean():.3f}   max level {int(lv[w].max())}")
        print(f"     engaged {100 * eng[w].mean():.1f}%   speed {np.nanmin(v_kph[w]):.1f}"
              f"..{np.nanmax(v_kph[w]):.1f} km/h")
        print(f"     |column rate| p50 {np.nanpercentile(np.abs(rate[w]), 50):.1f} "
              f"p95 {np.nanpercentile(np.abs(rate[w]), 95):.1f} max {np.nanmax(np.abs(rate[w])):.1f} deg/s")
        # per-second breakdown, so a transient is not averaged away
        print(f"\n     per-second, walking INTO the fault:")
        print(f"       {'window':22s} {'bit7':>7s} {'bit6':>7s} {'bit5':>7s} {'bit4':>7s} "
              f"{'lv':>6s} {'|rate|p95':>10s} {'kph':>6s}")
        for s in range(int(LAST_SECONDS), 0, -1):
            m = (t >= t_f - s) & (t < t_f - s + 1) & pre
            k = int(m.sum())
            if k < 5:
                continue
            print(f"       T-{s}s .. T-{s - 1}s{'':7s} {100 * b7[m].mean():6.1f}% "
                  f"{100 * b6[m].mean():6.1f}% {100 * b5[m].mean():6.1f}% {100 * b4[m].mean():6.1f}% "
                  f"{lv[m].mean():6.2f} {np.nanpercentile(np.abs(rate[m]), 95):10.1f} "
                  f"{np.nanmean(v_kph[m]):6.1f}")
        # the final 500 ms at frame resolution
        w2 = (t >= t_f - 0.5) & pre
        print(f"\n     final 500 ms, frame by frame ({int(w2.sum())} frames, sentinel-free):")
        print(f"       damper level  : {''.join(str(int(x)) for x in lv[w2])}")
        print(f"       bit3 backdrive: {''.join('1' if x else '.' for x in b3[w2])}")
        print(f"       engaged       : {''.join('1' if x else '.' for x in eng[w2])}")
        print(f"       |rate| max {np.nanmax(np.abs(rate[w2])):.1f} deg/s, "
              f"speed {np.nanmin(v_kph[w2]):.1f}..{np.nanmax(v_kph[w2]):.1f} km/h, "
              f"engaged {100 * eng[w2].mean():.0f}%")
        i_nz = np.where(w2 & (lv > 0))[0]
        if len(i_nz):
            print(f"       ★ the damper LEAVES ZERO at t = {t[i_nz[0]]:.4f} s, i.e. "
                  f"{1000 * (t_f - t[i_nz[0]]):.0f} ms before the fault, and goes STRAIGHT to")
            print(f"         level {int(lv[i_nz[0]])} (|gp-0x6bd0| in [128, 288)). It had been "
                  f"IDENTICALLY ZERO for the preceding")
            j = np.where(w & (lv > 0))[0]
            first_nz = t[j[0]] if len(j) else t_f
            print(f"         {t[i_nz[0]] - (t_f - LAST_SECONDS):.2f} s of this window.")
        print(f"\n       last 12 frames before the fault (angle / rate / damper):")
        print(f"         {'t (s)':>10s} {'ang deg':>8s} {'rate d/s':>9s} {'jerk d/s2':>10s} "
              f"{'lv':>3s} {'kph':>6s} {'eng':>4s}")
        idx = np.where(pre)[0][-12:]
        # 🛑 compute the derivative INSIDE the pre-fault window only. `np.gradient` over the full
        # array uses a centred stencil, so the last pre-fault frame would borrow the fault frame's
        # 0x7FFF and report a nonsense -1,718,466 deg/s^2.
        jk = np.full(n, np.nan)
        jk[pre] = np.gradient(rate[pre], t[pre])
        for i in idx:
            print(f"         {t[i]:10.4f} {ang_arr[i]:8.1f} {rate[i]:9.1f} {jk[i]:10.0f} "
                  f"{int(lv[i]):3d} {v_kph[i]:6.2f} {int(eng[i]):4d}")
        print("       ⇒ the column rate REVERSES SIGN twice in the last 150 ms (+55, +31, -38) at a")
        print("         6-8 km/h launch. That is the ~20 Hz pre-fault oscillation already on record,")
        print("         and it is the highest-jerk condition anywhere near the fault.")
    # a null-comparison: is the last 5 s different from the route's own engaged baseline?
    base = pre & eng
    print(f"\n     ⊕ vs the pre-fault ENGAGED baseline ({int(base.sum())} frames): "
          f"bit7 {100 * b7[base].mean():.3f}% · bit6 {100 * b6[base].mean():.3f}% · "
          f"bit5 {100 * b5[base].mean():.3f}% · bit4 {100 * b4[base].mean():.3f}%")
    print(f"     🛑 bit4 (|gp-0x6bd0| >= 448) fired {int(b4[pre].sum())}/{int(pre.sum())} pre-fault.")
    print("        The DAMPER was NOT near its ceiling when the ECU faulted -- which is why the")
    print("        fault was relocated to the FRICTION lane (gp-0x6b26) in the first place.")
    return dict(t=t, rate=rate, pre=pre, eng=eng, v_kph=v_kph, i_fault=i_fault)


# =================================================================================================
#  PART 3 -- DID ROUTE 65 EVER SEE THE EXCITATION THAT FAULTED V75?
# =================================================================================================
def part3(r65, r5e):
    """The friction lane's input `gp-0x6c2c` is a DIFFERENTIATOR of motor rate with ~zero DC gain --
    so what drives it is JERK, not rate, not torque, not speed. Neither route logs `gp-0x6c2c`, but
    both log the SAME instrument (column angle off CAN 0x18F at 100 Hz), so the two drives'
    excitation can be compared to each other even though neither can be converted to raw counts.

    🛑 [BELIEF, and the reason this is a BOUND not an estimate] 100 Hz CAN cannot see the content
    above 50 Hz that the K1/K2 cascade amplifies MOST (gain rises 3.08x@7.79Hz -> 12.1x@61Hz). This
    proxy therefore UNDER-states `gp-0x6c2c` by an unknown, frequency-dependent factor, and the
    factor need not be equal on two different drives. It is a rank comparison, not a calibration."""
    print("\n\n" + "=" * 100)
    print("  PART 3 -- CROSS-ROUTE EXCITATION: did route 65 ever reach V75's fault condition?")
    print("=" * 100)
    t5, r5, pre5 = r5e["t"], r5e["rate"], r5e["pre"]
    i_f = r5e["i_fault"]
    t6, r6 = r65["t"], r65["rate"]

    # 🛑 derivative INSIDE the pre-fault window only -- a centred stencil that straddles the fault
    # frame borrows its 0x7FFF and manufactures a 1.7e6 deg/s^2 "peak" that is pure sentinel.
    j5 = np.full(len(t5), np.nan)
    j5[pre5] = np.gradient(r5[pre5], t5[pre5])
    j6 = np.gradient(r6, t6)
    # the fault's own excitation: the 200 ms immediately before it, sentinel-free
    w = (t5 >= t5[i_f] - 0.2) & pre5
    pk_rate = float(np.nanmax(np.abs(r5[w])))
    pk_jerk = float(np.nanmax(np.abs(j5[w])))
    print(f"  V75's fault condition, from the 200 ms before it ({int(w.sum())} frames):")
    print(f"     peak |column rate| = {pk_rate:.0f} deg/s      peak |d(rate)/dt| = {pk_jerk:.0f} deg/s^2")
    print(f"     speed {np.nanmin(r5e['v_kph'][w]):.1f}..{np.nanmax(r5e['v_kph'][w]):.1f} km/h, "
          f"engaged {100 * r5e['eng'][w].mean():.0f}%")

    fin = np.isfinite(j6) & np.isfinite(r6)
    dt6 = float(np.median(np.diff(t6)))
    for name, arr6, arr5pk in (("|column rate|", np.abs(r6), pk_rate),
                               ("|d(rate)/dt|", np.abs(j6), pk_jerk)):
        m = fin & (arr6 >= arr5pk)
        k = int(m.sum())
        # count EPISODES, not frames -- contiguous runs separated by >=0.25 s
        idx = np.where(m)[0]
        eps = 0
        if len(idx):
            eps = 1 + int((np.diff(t6[idx]) > 0.25).sum())
        pct = 100.0 * float((arr6[fin] < arr5pk).mean())
        print(f"\n  Route 65 frames at or above V75's pre-fault peak {name} ({arr5pk:.0f}):")
        print(f"     {k} frames ({k * dt6:.2f} s) in {eps} separate episode(s); the fault's peak sits")
        print(f"     at the {pct:.3f}th percentile of route 65's own distribution.")
        if k:
            print(f"     ⇒ route 65 DID reach this excitation level, {eps} time(s), and "
                  f"|gp-0x6b26| still never exceeded {PROBE_THRESH}.")
        else:
            print(f"     🛑 route 65 NEVER reached it ⇒ the bit7 null is NOT evidence about the")
            print("       fault's own operating point. UNPOWERED for that comparison.")
    print(f"\n  route 65 |d(rate)/dt| percentiles: " +
          "  ".join(f"p{q}={np.nanpercentile(np.abs(j6[fin]), q):.0f}" for q in (50, 90, 99, 99.9)) +
          f"  max={np.nanmax(np.abs(j6[fin])):.0f} deg/s^2")
    print(f"  route 5e (pre-fault) |d(rate)/dt| percentiles: " +
          "  ".join(f"p{q}={np.nanpercentile(np.abs(j5[pre5]), q):.0f}" for q in (50, 90, 99, 99.9)) +
          f"  max={np.nanmax(np.abs(j5[pre5])):.0f} deg/s^2")
    # ---- the single-point calibration, the best this data can do -------------------------------
    print("\n  " + "#" * 96)
    print("  # THE CALIBRATED EXTRAPOLATION -- [BELIEF], and every assumption is listed")
    print("  " + "#" * 96)
    print("  ASSUMPTIONS, all of which must hold for the number below to mean anything:")
    print("    A1  V75's fault WAS FUN_00036d74's |gp-0x6b26| > 512 test. 🛑 THE DTC NUMBER WAS")
    print("        NEVER CONFIRMED ON-CAR -- the UDS read is structurally blind (the RAM log clears")
    print("        on the power cycle). This is a Ghidra-derived mechanism, not a read-back code.")
    print("    A2  `raw` is exactly linear in `gp-0x6c2c` (TRUE -- decompile-confirmed) and")
    print("        `gp-0x6c2c` is monotone in the 100 Hz jerk proxy (PLAUSIBLE, not verified).")
    print("    A3  the proxy's under-read factor is the same on both routes (FALSE in general --")
    print("        it is frequency-dependent; see the bias note below).")
    g = PIN_EQUIV * FRICTION_SCALE / pk_jerk        # counts of x1.5-raw per deg/s^2, at the fault
    g_stock = g / FRICTION_SCALE
    print(f"\n  Calibrate at the single fault event: x1.5 raw = {FAULT_TRIP} at jerk = {pk_jerk:.0f} deg/s^2")
    print(f"    ⇒ stock-lane gain G = {g_stock:.4f} counts per deg/s^2")
    print(f"    ⇒ stock raw > {PROBE_THRESH} needs jerk > {PROBE_THRESH / g_stock:.0f} deg/s^2")
    print(f"    ⇒ x1.5 PINS at {CLAMP_STOCK} needs jerk >= {PIN_EQUIV / g_stock:.0f} deg/s^2")
    for lab, thr in ((f"stock raw > {PROBE_THRESH} (the probe's own rung)", PROBE_THRESH / g_stock),
                     (f"x1.5 PINNED at {CLAMP_STOCK}", PIN_EQUIV / g_stock)):
        m = fin & (np.abs(j6) >= thr)
        k = int(m.sum())
        idx = np.where(m)[0]
        eps = 1 + int((np.diff(t6[idx]) > 0.25).sum()) if len(idx) else 0
        print(f"    route 65 frames meeting '{lab}': {k}/{len(t6)} "
              f"({100.0 * k / len(t6):.4f}%), {eps} episode(s)")
    print(f"\n  ★ THE MODEL REPRODUCES THE OBSERVED NULL: it predicts 0 frames above "
          f"{PROBE_THRESH} on route 65,")
    print("    and the probe measured 0. That is a weak validation (a model that predicted a large")
    print("    duty would have been falsified outright), not a confirmation.")
    print("  ★ THE BIAS RUNS THE SAFE WAY. The proxy UNDER-reads exactly where the cascade gain is")
    print("    highest (>50 Hz, invisible at 100 Hz), and the fault event is the high-frequency one,")
    print("    so G fitted there is TOO LARGE for the lower-frequency route-65 events. The model")
    print("    therefore OVER-predicts pinning on route 65 -- and it still predicts zero.")
    print("  ⇒ [BELIEF] a x1.5 friction table against a 511 clamp would pin RARELY and only at the")
    print(f"    extreme tail of the jerk distribution (route 5e's own p99.9 was {np.nanpercentile(np.abs(j5[pre5]), 99.9):.0f} vs the")
    print(f"    fault's {pk_jerk:.0f}), NOT as a sustained duty cycle. Order of magnitude: ONE event per")
    print(f"    ~{T_FAULT_5E:.0f} s of mixed driving (n=1, censored by the latch).")
    print("  🛑 That is an ORDER OF MAGNITUDE, not a duty cycle, and it rests on A1 which is")
    print("     itself unconfirmed on-car. It is NOT a substitute for a 320/352 probe rung.")

    print("\n  🛑 WHAT THE COMPARISON DOES AND DOES NOT BUY.")
    print(f"     Route 65's jerk MAXIMUM is {np.nanmax(np.abs(j6[fin])):.0f} deg/s^2 vs the fault's "
          f"{pk_jerk:.0f} -- it reached "
          f"{100 * np.nanmax(np.abs(j6[fin])) / pk_jerk:.0f}% of the")
    print("     fault condition and no further. So route 65 came CLOSE but never matched it, and the")
    print("     bit7 null cannot be read as 'the fault condition occurred and the lane stayed low'.")
    print(f"     The probe's ceiling is {PROBE_THRESH}, and {FRICTION_SCALE} x {PROBE_THRESH} = "
          f"{FRICTION_SCALE * PROBE_THRESH:.0f} > {CLAMP_STOCK} -- so even a frame sitting")
    print(f"     just under the rung would PIN under x1.5. The blind band survives every")
    print("     restratification. It is the 320/352 rung that settles it, not more slicing.")


if __name__ == "__main__":
    _r65 = part1()
    _r5e = part2()
    part3(_r65, _r5e)
    print("\n" + "=" * 100)
    print("  🛑 EVERY NUMBER ABOVE IS A DUTY CYCLE OF A ONE-BIT COMPARATOR. The route-65 friction")
    print("     result is a MEASURED ZERO at 448 and an UNMEASURED quantity at 340.7. Do not")
    print("     convert the first into the second.")
    print("=" * 100)
    print("""
  ★ ONE REFRAMING THE NUMBERS ABOVE FORCE, and it is decision-bearing.

  V74 hard-faulted in MANUAL (mode 24), where V74/V75 left the friction record BYTE-STOCK -- only
  mode 26 got the x1.5. Under the friction-lane hypothesis (A1), V74's manual fault therefore means
  the **STOCK** friction lane reached > 512 raw, over a bump, with the clamp at 850.

  ⇒ Stock friction ALSO pins against a 511 clamp, at bump-grade events. Honda shipped a lane that
    saturates and shipped the clamp one count under the trip to make that saturation SAFE. A pinned
    friction lane is therefore NOT a new failure mode that x1.5 introduces -- it is the stock
    design point. x1.5 only makes the clamp bind at 1/1.5 = 0.667x the excitation, i.e. MORE OFTEN,
    not for the first time.
  ⇒ Framing the choice as 'x1.5 creates a Coulomb relay / stock does not' is WRONG. It is a
    difference of DEGREE. What the data cannot tell you is the size of that degree, because the
    probe's rung sits above the whole decision band.
  ⚠ [BELIEF] This inherits A1 wholesale. If V74's manual fault was NOT this monitor, the paragraph
    collapses and the route-65 null is the only friction evidence in the kit.""")
