#!/usr/bin/env python3
"""probe/decode_v65_saturation.py -- read V65's 4-level aggregator-saturation ladder out of an rlog.

V65 packs a SYMMETRIC FOUR-LEVEL LADDER on `gp-0x6b94` (the ten-lane aggregator output, hard-clipped
to +/-10240) into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                       LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x6b94 >= +8192      *** POSITIVE RAIL ***  (80% of the +10240 clip)
    bit 5 = gp-0x6b94 >= +4096      positive, large        (40%)
    bit 4 = gp-0x6b94 <= -4097      negative, large        (40%)
    bit 3 = gp-0x6b94 <= -8193      *** NEGATIVE RAIL ***  (80%)
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

*** field = (byte4 >> 3) & 0x1F.  field == 0 means THE CAVE DID NOT FIRE -- a VOID reading, not
"everything false". Bit 7 is hard-wired 1 precisely so this tool can say that.

EXACTLY FIVE PAYLOADS ARE REACHABLE. Anything else is a decode error, never a reading:

    0xE7  +RAIL    sum in [ +8192, +10240]
    0xA7  +HALF    sum in [ +4096,  +8191]
    0x87  NEUTRAL  sum in [ -4096,  +4095]
    0x97  -HALF    sum in [ -8192,  -4097]
    0x9F  -RAIL    sum in [-10240,  -8193]
(low three bits vary with the live STEER_SENSOR_STATUS field; mask with 0xF8 to compare.)

THE HEADLINE STATISTIC IS THE POSITIVE <-> NEGATIVE ALTERNATION RATE
-------------------------------------------------------------------------------------------------------
The hypothesis V65 exists to test: during the ~7 Hz ratchet the aggregator is bouncing RAIL-TO-RAIL,
+10240 to -10240 and back. If so the lever is LOOP GAIN UPSTREAM (r24's gain_B breakpoints at 0xD2AEC),
not any damper downstream -- and every null since V39 was aimed past the clip. One full cycle = TWO
alternations, so a 7 Hz limit cycle reads as ~14 alternations/s.

The ladder splits that question in two, which a bare rail probe cannot:
  * RAIL alternation  (bit6 <-> bit3)  -- the sum is CLIPPING. Hard nonlinearity in the loop.
  * SIDE alternation  (bit6|bit5 <-> bit4|bit3) -- the sum is merely swinging LARGE.
Both are reported. RAIL alternation is the headline; SIDE alternation without it means a large but
UNCLIPPED oscillation, which is a linear-regime problem and calls for a different next move.

🛑 THIS TOOL REJECTS V59 AND V64 SEMANTICS EXPLICITLY -- byte4 MEANS DIFFERENT THINGS PER BUILD
-------------------------------------------------------------------------------------------------------
The same five bits have carried three different meanings, and reading one build's log with another
build's decoder has already cost this kit a session:

    V59 : bit6 = fault sentinel, bits 5/4/3 = a THERMOMETER  index<512 => <1024 => <2048
    V64 : bit6 = gp-0x671a >= 5, bit5 = gp-0x671a != 0, bit4 = FSM != 0, bit3 = gp-0x671d != 0
    V65 : the four-level ladder above -- and NOTHING is a one-sided thermometer

Three structural invariants separate V65 from both, all guaranteed by the cave's arithmetic on ONE
register in ONE tick:
    (a) bit6 => bit5                          >= +8192 implies >= +4096
    (b) bit3 => bit4                          <= -8193 implies <= -4097
    (c) NOT ((bit6|bit5) AND (bit4|bit3))     *** THE DISCRIMINATOR *** -- one value cannot be both
        positive and negative. Under V59 bits from "both sides" fire together on every frame with
        index < 512; under V64 whenever the counter is latched with the FSM out of neutral. Under V65
        that combination is arithmetically impossible.
On top of that, only five payload values are legal at all, which is checked directly.

⚠ AND THE ONE CASE STRUCTURE CANNOT SETTLE: a CONSTANT 0x87.
  V64's drive read 0x87 for all 14,980 frames and that was its null. Under V65, 0x87 is the NEUTRAL
  bucket -- "cave fired, sum never past +/-4096" -- a legitimate and informative reading, and the
  "all four quiet" branch of the pre-committed interpretation. The payload alone cannot tell them
  apart. This tool STOPS and asks which .rwd is on the car rather than guessing.

⚠ ONE-COUNT ENCODING ASYMMETRY, stated so it is never mistaken for a physical skew.
  `sar` is floor division, so the thresholds are +8192 / -8193 and the +RAIL bucket is ONE count wider
  than -RAIL (2049 vs 2048 of the 20,481 reachable sums). That is 0.049% -- orders of magnitude below
  any skew a drive can resolve -- but it is the reason a perfectly symmetric signal would show a rail
  skew of about +0.0002 rather than exactly 0. The HALF buckets are exactly equal (4096 each).

🛑 CONVENTIONS THIS TOOL ENFORCES -- all three established the hard way on the V57/V58 drives:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes while
     lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. Bursty limit cycle => report ENVELOPE p99/max, never mean Welch power.

⚠ The grinding is CREEP-ONLY (prominence 141x/138x/518x at 1-4 m/s vs 7-11x above 6 m/s), so the
headline is conditioned on v <= 5 m/s. ⚠ 100 Hz sampling of a ~21 Hz phenomenon: every frequency is
indistinguishable from its alias. The ~7 Hz ratchet is well inside Nyquist; the 21 Hz mode is NOT, so
an alternation rate above ~50/s must be read as "faster than this probe can resolve", not as a number.

Usage:  python probe/decode_v65_saturation.py RLOG [RLOG ...]
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

BIT_LIVE = 0x80
BIT_POS_RAIL, BIT_POS_HALF, BIT_NEG_HALF, BIT_NEG_RAIL = 0x40, 0x20, 0x10, 0x08
PROBE_MASK = 0xF8

SUM_CLAMP = 10240       # 0x2800, Ghidra-confirmed at 0x3ACF6 / 0x3AD0E in FUN_0003aa2c
RATCHET_HZ = 7.0        # the reported ratchet rate; one rail-to-rail cycle is TWO alternations

# The five legal payloads, probe bits only (bits 2:0 are the live status field and are masked off).
BUCKETS = (("+RAIL", 0xE0, (8192, SUM_CLAMP)),
           ("+HALF", 0xA0, (4096, 8191)),
           ("NEUTRAL", 0x80, (-4096, 4095)),
           ("-HALF", 0x90, (-8192, -4097)),
           ("-RAIL", 0x98, (-SUM_CLAMP, -8193)))
LEGAL = {b for _, b, _ in BUCKETS}


def bucket_of(b4):
    """Bucket name for a byte4, or None if the probe field is not one of the five legal payloads."""
    probe = b4 & PROBE_MASK
    for name, val, _rng in BUCKETS:
        if probe == val:
            return name
    return None


def collect(paths):
    """Pair each 0x14A probe frame with the most recent 0x18F frame (both ~100 Hz on src 1)."""
    b4, rate, tq, sca, t = [], [], [], [], []
    last_rate, last_tq, last_sca = np.nan, np.nan, -1
    lat_t, lat_v, v_t, v_v, g_t, g_v = [], [], [], [], [], []
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            ts = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    if m.src != 1:
                        continue
                    d = bytes(m.dat)
                    if m.address == 0x18F and len(d) >= 5:
                        a = (d[0] << 8) | d[1]
                        last_tq = (a - 0x10000 if a & 0x8000 else a) * -1.0
                        r = (d[2] << 8) | d[3]
                        last_rate = (r - 0x10000 if r & 0x8000 else r) * -0.1
                        last_sca = (d[4] >> 3) & 1
                    elif m.address == 0x14A and len(d) >= 5:
                        # 🛑 Drop 0x14A frames arriving BEFORE the first 0x18F -- otherwise last_tq is
                        # NaN, and a SINGLE NaN propagates through the FFT to make every sample NaN,
                        # which reads as "0 hands-off frames": a plausible null rather than an error.
                        if last_sca < 0:
                            continue
                        b4.append(d[4]); rate.append(last_rate); tq.append(last_tq)
                        sca.append(last_sca); t.append(ts)
            elif w == "carControl":
                lat_t.append(ts); lat_v.append(bool(evt.carControl.latActive))
            elif w == "carState":
                v_t.append(ts); v_v.append(evt.carState.vEgo)
                try:
                    g_t.append(ts); g_v.append(str(evt.carState.gearShifter) == "reverse")
                except Exception:
                    pass
    d = dict(b4=np.array(b4, int), rate=np.array(rate), tq=np.array(tq),
             sca=np.array(sca, int), t=np.array(t))
    d["lat"] = (np.interp(d["t"], lat_t, np.array(lat_v, float)) > 0.5) if lat_t \
        else np.zeros_like(d["t"], bool)
    d["v"] = np.interp(d["t"], v_t, v_v) if v_t else np.full_like(d["t"], np.nan)
    d["rev"] = (np.interp(d["t"], g_t, np.array(g_v, float)) > 0.5) if g_t \
        else np.zeros_like(d["t"], bool)
    d["has_gear"] = bool(g_t)
    return d


def sustained(x, fs, fc=3.0):
    """Zero-phase lowpass -> the DRIVER's actual push, with the oscillation removed.

    ⚠ Compute over the SUBSET you intend to analyse, and guard the input: it is NaN-fragile by
    construction (one NaN in, all NaN out).
    """
    x = np.asarray(x, float)
    bad = ~np.isfinite(x)
    if bad.all():
        return np.full_like(x, np.inf)
    if bad.any():
        good = ~bad
        x = x.copy()
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(good), x[good])
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    out = np.abs(np.fft.irfft(X, n=len(x)) + x.mean())
    assert np.isfinite(out).all(), "sustained() produced non-finite output"
    return out


def transitions(mask):
    """(rising, falling) counts for a boolean series."""
    m = np.asarray(mask, bool).astype(int)
    if len(m) < 2:
        return 0, 0
    dd = np.diff(m)
    return int((dd > 0).sum()), int((dd < 0).sum())


def alternations(pos, neg):
    """Count pos <-> neg sign flips, SKIPPING the neutral frames in between.

    Neutral frames are skipped rather than treated as a state: the probe samples at 100 Hz and a
    rail-to-rail swing at 7 Hz spends real time in between, so counting neutral as a state would
    report 4 transitions per cycle instead of 2 and double the apparent frequency.

    Returns (n_alternations, n_visits).
    """
    seq = []
    for p, n in zip(np.asarray(pos, bool), np.asarray(neg, bool)):
        s = 1 if p else (-1 if n else 0)
        if s == 0:
            continue
        if not seq or seq[-1] != s:
            seq.append(s)
    return max(0, len(seq) - 1), len(seq)


def rate_of(sel, pos, neg, t):
    """(alternations/s, cycle Hz, visits) over a boolean selection mask."""
    if sel.sum() < 2:
        return None
    alt, visits = alternations(pos[sel], neg[sel])
    span = t[sel][-1] - t[sel][0]
    r = alt / span if span > 0 else 0.0
    return r, r / 2.0, visits, alt, span


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    fs = 1.0 / np.median(np.diff(d["t"]))
    field = (d["b4"] >> 3) & 0x1F
    dur = d["t"][-1] - d["t"][0]
    print(f"\n{'=' * 92}\n{tag}   {n} frames  {dur:.1f}s  fs={fs:.2f} Hz")

    # ---- LIVENESS ---------------------------------------------------------------------------------
    void = field == 0
    print("\n-- LIVENESS --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {void.sum()} / {n}  ({100 * void.mean():.2f}%)")
    print(f"   bit7 set                       : {(d['b4'] & BIT_LIVE != 0).sum()} / {n}")
    if void.all():
        print("\n   *** THE CAVE NEVER FIRED. Every reading below is VOID. Stop here.")
        return
    print("   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"].tolist()).most_common(8)))

    p_rail = (d["b4"] & BIT_POS_RAIL) != 0
    p_half = (d["b4"] & BIT_POS_HALF) != 0
    n_half = (d["b4"] & BIT_NEG_HALF) != 0
    n_rail = (d["b4"] & BIT_NEG_RAIL) != 0
    pos_side = p_rail | p_half
    neg_side = n_half | n_rail

    # ---- WHICH BUILD IS THIS? -- run BEFORE any verdict --------------------------------------------
    print("\n-- BUILD IDENTIFICATION (byte4 means different things on V59 / V64 / V65) --")
    both_sides = pos_side & neg_side
    bad_pos = p_rail & ~p_half
    bad_neg = n_rail & ~n_half
    illegal = np.array([(b & PROBE_MASK) not in LEGAL for b in d["b4"]])
    print(f"   (a) bit6 & ~bit5            IMPOSSIBLE : {bad_pos.sum():6d} / {n} "
          f"({100 * bad_pos.mean():.3f}%)")
    print(f"   (b) bit3 & ~bit4            IMPOSSIBLE : {bad_neg.sum():6d} / {n} "
          f"({100 * bad_neg.mean():.3f}%)")
    print(f"   (c) positive AND negative   IMPOSSIBLE : {both_sides.sum():6d} / {n} "
          f"({100 * both_sides.mean():.3f}%)   <- THE DISCRIMINATOR")
    print(f"       payload not one of the 5 legal    : {illegal.sum():6d} / {n} "
          f"({100 * illegal.mean():.3f}%)")
    # 🛑 HARD STOP, not a filter. A few stray frames are bus noise; a large fraction means these are
    # not V65 readings at all, and the surviving subset would still decode into plausible numbers.
    worst = max(bad_pos.mean(), bad_neg.mean(), both_sides.mean(), illegal.mean())
    if worst > 0.01:
        print("\n   *** STOP. Above 1% structurally impossible, these are NOT V65 readings.")
        print("       V59's byte4 is a one-sided THERMOMETER (bit5 => bit4 => bit3) and lights bits")
        print("       from both of V65's sides together on every frame with index < 512. V64 does the")
        print("       same whenever its reversal counter is latched with the FSM out of neutral.")
        print("       Both look exactly like this. V65 arithmetically cannot.")
        print("       => CONFIRM WHICH .rwd IS FLASHED. No verdict is computed: the surviving subset")
        print("          would still look plausible, which is exactly how this trap works.")
        print(f"       byte4 values seen: {sorted(set(d['b4'].tolist()))}")
        return
    ok = ~(both_sides | bad_pos | bad_neg | illegal)
    if (~ok).any():
        print(f"   ({(~ok).sum()} structurally impossible frames excluded rather than averaged in)")

    # ⚠ the one ambiguity structure cannot settle
    const87 = (d["b4"] == 0x87).mean()
    if const87 > 0.99:
        print(f"\n   !! byte4 IS A CONSTANT 0x87 on {100 * const87:.2f}% of frames.")
        print("      *** THIS IS AMBIGUOUS AND THE TOOL WILL NOT GUESS. ***")
        print("      Under V64 that was the NULL: the oscillation detector never armed (14,980 frames).")
        print("      Under V65 it is the NEUTRAL bucket -- cave fired, sum never past +/-4096 -- i.e.")
        print("      the 'all four quiet' branch of the pre-committed interpretation.")
        print("      => CONFIRM THE FLASHED .rwd FILENAME before reading the verdict below. If V64 is")
        print("         still on the car, everything after this line is meaningless.")

    # ---- SUBSETS ----------------------------------------------------------------------------------
    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    creep = d["v"] <= 5.0
    eng = d["sca"] == 1
    print("\n-- ENGAGEMENT / SUBSET (cruiseState is long+lat: NOT used) --")
    print(f"   latActive               : {d['lat'].sum():6d} ({100 * d['lat'].mean():5.2f}%)")
    print(f"   STEER_CONTROL_ACTIVE==1 : {eng.sum():6d} ({100 * eng.mean():5.2f}%)  <- the subset")
    print(f"   agreement latActive vs SCA : {100 * (d['lat'] == eng).mean():.2f}%")
    print(f"   hands-off by SUSTAINED effort: {hands_off.sum()} "
          f"| by raw |tq|<=200: {(np.abs(d['tq']) <= 200).sum()}  <- raw discards the oscillation")
    print(f"   creep (v <= 5 m/s)      : {creep.sum()}")
    if d["has_gear"]:
        print(f"   REVERSE gear            : {d['rev'].sum()}")
    else:
        print("   REVERSE gear            : carState.gearShifter absent from this log -- the reverse")
        print("                             split below is EMPTY, not zero. Do not read it as a null.")

    conds = [("ALL frames", ok),
             ("ENGAGED (SCA==1)", ok & eng),
             ("ENGAGED + creep", ok & eng & creep),
             ("ENGAGED + creep + hands-off", ok & eng & creep & hands_off),
             ("MANUAL (SCA!=1)", ok & ~eng),
             ("MANUAL + creep", ok & ~eng & creep),
             ("REVERSE", ok & d["rev"]),
             ("REVERSE + manual", ok & d["rev"] & ~eng)]

    # ---- 1. FOUR-LEVEL OCCUPANCY HISTOGRAM ---------------------------------------------------------
    print(f"\n-- 1. LADDER OCCUPANCY (clamp +/-{SUM_CLAMP}) --")
    names = [b[0] for b in BUCKETS]
    bkt = np.array([bucket_of(b) or "?" for b in d["b4"]])
    print(f"   {'condition':32s} {'n':>7s} " + " ".join(f"{nm:>8s}" for nm in names))
    for name, sel in conds:
        if sel.sum() == 0:
            print(f"   {name:32s} {0:7d}   (none)")
            continue
        row = " ".join(f"{100 * (bkt[sel] == nm).mean():7.2f}%" for nm in names)
        print(f"   {name:32s} {sel.sum():7d} {row}")
    print("   RAIL fraction = +RAIL + -RAIL (CLIPPED);  LARGE-but-unclipped = +HALF + -HALF")
    for name, sel in conds[:4]:
        if sel.sum() == 0:
            continue
        rail = ((bkt[sel] == "+RAIL") | (bkt[sel] == "-RAIL")).mean()
        large = ((bkt[sel] == "+HALF") | (bkt[sel] == "-HALF")).mean()
        print(f"     {name:32s} rail {100 * rail:6.2f}%   large-unclipped {100 * large:6.2f}%")
    # a DC bias in the sum shows up as a rail/side skew; the thresholds are symmetric to one count
    sel = ok & eng & creep
    if sel.sum():
        p, q = p_rail[sel].mean(), n_rail[sel].mean()
        if max(p, q) > 0.01:
            print(f"   rail SKEW on engaged-creep frames: {(p - q) / (p + q):+.3f}  "
                  f"(+1 = only the positive rail, -1 = only the negative)")
            print("      the +RAIL bucket is 1 count wider than -RAIL (2049 vs 2048 of 20,481), a")
            print("      0.049% encoding artefact. A skew above ~0.01 is physical, not the encoding.")

    # ---- 2. THE HEADLINE: ALTERNATION RATES --------------------------------------------------------
    print(f"\n{'-' * 92}\n-- 2. *** THE HEADLINE: ALTERNATION RATE *** --")
    print(f"   A rail-to-rail limit cycle at {RATCHET_HZ:.0f} Hz = {2 * RATCHET_HZ:.0f} alternations/s.")
    print(f"   {'condition':32s} {'n':>6s} {'span':>7s} | {'RAIL alt/s':>10s} {'~Hz':>6s} | "
          f"{'SIDE alt/s':>10s} {'~Hz':>6s}")
    alt_rail = alt_side = 0.0
    for name, sel in [("ENGAGED + creep", ok & eng & creep),
                      ("ENGAGED + creep + hands-off", ok & eng & creep & hands_off),
                      ("MANUAL + creep", ok & ~eng & creep),
                      ("REVERSE + manual", ok & d["rev"] & ~eng),
                      ("ALL frames", ok)]:
        r_rail = rate_of(sel, p_rail, n_rail, d["t"])
        r_side = rate_of(sel, pos_side, neg_side, d["t"])
        if r_rail is None or r_side is None:
            print(f"   {name:32s}  (fewer than 2 frames)")
            continue
        print(f"   {name:32s} {sel.sum():6d} {r_rail[4]:6.1f}s | {r_rail[0]:10.2f} {r_rail[1]:6.2f} | "
              f"{r_side[0]:10.2f} {r_side[1]:6.2f}")
        if name == "ENGAGED + creep":
            alt_rail, alt_side = r_rail[0], r_side[0]
    if max(alt_rail, alt_side) > fs / 2:
        print(f"   ⚠ {max(alt_rail, alt_side):.1f} alternations/s exceeds Nyquist for this 100 Hz")
        print("     probe. Read it as 'faster than the probe resolves', NOT as a frequency.")

    # ---- 3. PER-BIT TRANSITIONS --------------------------------------------------------------------
    print("\n-- 3. PER-BIT DUTY AND TRANSITIONS --")
    for nm, m in (("bit6 +RAIL", p_rail), ("bit5 +HALF", p_half),
                  ("bit4 -HALF", n_half), ("bit3 -RAIL", n_rail)):
        r, f_ = transitions(m[ok])
        print(f"   {nm:12s} duty {100 * m[ok].mean():6.2f}%   {r:5d} rising / {f_:5d} falling")

    # ---- BY SPEED ----------------------------------------------------------------------------------
    print("\n-- BY SPEED (engaged frames) --")
    print(f"   {'band':>14s} {'n':>7s} {'rail%':>8s} {'large%':>8s} {'RAIL alt/s':>11s} "
          f"{'SIDE alt/s':>11s}")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 99)):
        sel = ok & eng & (d["v"] >= lo) & (d["v"] < hi)
        if sel.sum() < 2:
            continue
        rail = ((bkt[sel] == "+RAIL") | (bkt[sel] == "-RAIL")).mean()
        large = ((bkt[sel] == "+HALF") | (bkt[sel] == "-HALF")).mean()
        rr = rate_of(sel, p_rail, n_rail, d["t"])
        rs = rate_of(sel, pos_side, neg_side, d["t"])
        print(f"   {f'{lo}-{hi} m/s':>14s} {sel.sum():7d} {100 * rail:7.2f}% {100 * large:7.2f}% "
              f"{rr[0]:11.2f} {rs[0]:11.2f}")

    # ---- THE VERDICT -------------------------------------------------------------------------------
    sel = ok & eng & creep
    print(f"\n{'-' * 92}\n-- THE VERDICT (pre-committed in builds/v50_v79/build_v65_tva.py, before the drive) --")
    if sel.sum() == 0:
        print("   no engaged creep frames. Cannot call it. Re-drive the parking-lot route.")
        return
    rail_frac = ((bkt[sel] == "+RAIL") | (bkt[sel] == "-RAIL")).mean()
    large_frac = ((bkt[sel] == "+HALF") | (bkt[sel] == "-HALF")).mean()
    print(f"   engaged-creep frames: {sel.sum()};  clipped {100 * rail_frac:.2f}%;  "
          f"large-unclipped {100 * large_frac:.2f}%;  RAIL alt {alt_rail:.2f}/s;  "
          f"SIDE alt {alt_side:.2f}/s")

    if alt_rail >= 2.0 and rail_frac > 0.02:
        print(f"\n   *** THE AGGREGATOR IS RAIL-TO-RAIL AND CLIPPED. *** {100 * rail_frac:.2f}% of")
        print(f"   engaged-creep frames sit at a rail and the sign flips {alt_rail:.2f} times/s")
        print(f"   (~{alt_rail / 2:.2f} Hz cycle).")
        print("   => THE LEVER IS LOOP GAIN UPSTREAM, not damping downstream. Next: r24's gain_B")
        print("      breakpoints at 0xD2AEC (the MODE-10 record; 0xD6AEC is mode 22's byte-identical")
        print("      but SEPARATE record -- not a redundancy mirror, see builds/v50_v79/build_v62_tva.py).")
        print("   ⚠ AND IT EXPLAINS THE NULL RUN: a saturating sum makes every downstream damper")
        print("      lever describing-function-irrelevant, which is where V39/V42/V44/V47/V56/V64 all")
        print("      aimed. Re-read those nulls as 'aimed past the clip', not as 'lane not involved'.")
    elif alt_side >= 2.0 and (rail_frac + large_frac) > 0.02:
        print(f"\n   *** A LARGE OSCILLATION THAT IS NOT CLIPPING. *** The sum swings past +/-4096 and")
        print(f"   changes sign {alt_side:.2f} times/s (~{alt_side / 2:.2f} Hz), but reaches a rail on")
        print(f"   only {100 * rail_frac:.2f}% of frames.")
        print("   => LINEAR-REGIME PROBLEM. The damper lanes are still in play and a gain change will")
        print("      behave predictably. Do NOT jump to the gain_B breakpoints -- that lever is for a")
        print("      clipped loop. Size the change against the measured swing instead.")
    elif rail_frac + large_frac > 0.02:
        print(f"\n   LARGE ({100 * (rail_frac + large_frac):.2f}% past +/-4096) but only "
              f"{alt_side:.2f} side-alternations/s.")
        print("   That is a SUSTAINED OFFSET, not an oscillation -- the sum is pinned, probably on one")
        print("   side (check the rail SKEW above). A pinned aggregator still destroys every")
        print("   downstream lever's authority, but the ratchet's ~7 Hz comes from somewhere else.")
        print("   => Establish WHICH side and under what steering input before choosing a lever.")
    else:
        print(f"\n   THE AGGREGATOR NEVER LEAVES THE NEUTRAL BUCKET ({100 * (rail_frac + large_frac):.2f}%")
        print(f"   of engaged-creep frames past +/-4096, of a +/-{SUM_CLAMP} clamp).")
        print("   => THE NONLINEARITY IS DOWNSTREAM OF THE AGGREGATOR, in the motor/FOC path. Every")
        print("      lane lever inside FUN_0003aa2c is aimed at the wrong side of the clip, and the")
        print("      run of nulls from V39 onward is consistent with exactly that.")
        print("      Next target: gp-0x6b98 (the merged motor command, V55's probe) and the FOC")
        print("      current loop past it -- NOT another lane gain.")
    if const87 > 0.99:
        print("\n   🛑 ...AND ALL OF THE ABOVE IS CONDITIONAL ON V65 ACTUALLY BEING FLASHED. byte4 was")
        print("      a constant 0x87, byte-identical to V64's null. Confirm the .rwd on the car.")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
