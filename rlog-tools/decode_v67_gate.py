#!/usr/bin/env python3
"""decode_v67_gate.py -- read V67's gate probe out of an rlog.

V67 = V66 (stock rate lane) PLUS the grind #1 fix, GATED ON LKAS:
    0x3AA96  c5 -> fb     repoints `ld.bu -0x683c[gp],r15` @0x3AA94 (a DEAD cell) to
                          `ld.bu -0x6806[gp],r15`, so `lp` -- which selects cal 0xC6446 for r24 at
                          0x3AC04 -- becomes an LKAS-conditional gain override.
    0xC6446  512 -> 5244  = 2.00x the LERP (2622) at grind #1's operating point.
    the two `sar` immediates stay STOCK 0xa, so GATE FALSE IS BYTE-FOR-BYTE STOCK.

V67 packs four bits into CAN 330 (0x14A) byte4 at ~100 Hz:

    bit 7 = 1                   LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x6806 != 0      *** THE GATE ITSELF ***                        (EVEN disp 0x97FA)
    bit 5 = gp-0x671d != 0      *** THE MASKING RISK -- outranks the arm ***   (ODD  disp 0x98E3)
    bit 4 = gp-0x671a >= 5      the THIRD arm (0xC6440), below the gate        (EVEN disp 0x98E7)
    bit 3 = 0                   UNUSED on V67
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

🛑🛑 V66 AND V67 EMIT THE SAME EIGHT PAYLOAD BYTES WITH DIFFERENT MEANINGS.
There is NO structural discriminator between them -- both use bits 7:4 and neither ever sets bit3.
V66's bit5/bit4 are gp-0x67f5 / gp-0x67fe; V67's are gp-0x671d / gp-0x671a. **Confirm the .rwd
filename on the car before reading any verdict below.** Reading one build's log with another
build's decoder has already cost this kit a session, and V66-vs-V67 is the tightest such pair yet.
The only (weak, non-structural) hint: under V66 bit4 is the base-assist substate and is expected
near 100% duty, while under V67 bit4 is a rare latch. This tool will NOT decide on that alone.

THE HEADLINE, in this order -- everything else is supporting evidence
---------------------------------------------------------------------
  1. bit6 DUTY vs carControl.latActive, and its TRANSITIONS/s + DOMINANT TOGGLE FREQUENCY.
     This is the whole build. If bit6's duty does not track lateral engagement, V67's arm is either
     never taken (inert) or taken in the wrong regime (grind #2's amplification moved, not removed).
     If bit6 toggles inside 15-60 Hz, the gain switches at the mode frequency: a PARAMETRIC PUMP,
     worse than the symptom. That is the abort criterion.
  2. bit5 OCCUPANCY. gp-0x671d strictly OUTRANKS the arm at 0x3ABFA, so whenever it is set r24's
     gain is pinned to 0xC6442 = 1024 -- BELOW the stock creep LERP of 3072. It does not merely mask
     V67, it cuts the lane to a third. V64 read it 0 across 14,980 frames of ONE 149.8 s creep
     route; a long mixed drive is the first real test.
  3. bit4 OCCUPANCY. The third arm (0xC6440 = 2048) sits below the gate in priority, so it only
     bites while bit6 is clear -- but it then replaces the LERP, and gp-0x671a is a ONE-WAY LATCH
     at CEIL with a ~5 s hold, so its tail outlives whatever set it.

THE PRIORITY CHAIN, and how the bits map onto it (0x3ABFA-0x3AC16)
-------------------------------------------------------------------
    bit5 set  ->  gain = 0xC6442 = 1024   BELOW stock. V67 is WORSE than V66 in this state.
    else bit6 ->  gain = 0xC6446 = 5244   V67's arm: 2.00x at grind #1's operating point.
    else bit4 ->  gain = 0xC6440 = 2048
    else      ->  the mode-10 LERP (3072 at creep, rolling off to 1536 at ~637 deg/s) = STOCK
The bits are therefore NOT independent in meaning: read them as a priority ladder, top down.

⚠ bit4 IS `>=`, NOT `>`. From the instructions at 0x3AA70-0x3AA88: `ld.bu -0x671a[gp],r12` /
`ld.bu 0x74fa[tp],r14` (CEIL, cal 0xC64FA = 5, a BYTE) / `cmp r14,r12` / `bc` (UNSIGNED <) /
`mov 0x1,r2`. So r2 = 1 exactly when state >= CEIL, and the probe says the same thing.
(`v66_v67_explained.py` mirrors this as `> CEIL`; the builder asserts the disagreement is confined
to state == 5 and does not silently patch that file.)

🛑 NYQUIST. The probe is ~100 Hz, so the 15-60 Hz kill band is NOT fully observable: a true 58 Hz
toggle aliases to 42 Hz and a true 51 Hz toggle to 49 Hz. This tool reports the observed peak and
says so explicitly rather than printing a number that looks settled. Same alias as the 41.64/58.86
Hz pair in docs/V66-V67-DESIGN.md.

🛑 CONVENTIONS THIS TOOL ENFORCES -- all established the hard way:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes
     while lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is unmeasurable.
  4. Statistics are computed PER CONTIGUOUS RUN and pooled -- never over a concatenated subset,
     which manufactures a transition at every join (V58's retracted 25 Hz coherence).

Usage:  python decode_v67_gate.py RLOG [RLOG ...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from rlog_parse import read_messages  # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v67_tva.assert_decoder_matches() fails the BUILD if
# this string is not byte-for-byte the cave in the built artifact. V66's decoder header was stale
# for one revision and claimed bit4 = gp-0x683c when the image read gp-0x67fe; this is the fix for
# that class of error. Do not edit by hand -- rebuild and copy.
CAVE_HEX = "203e80008437fb976132b605273e4000a437e3986132b605273e20008437e7986532b105273e10008437edeac636070007314437ecea2436e8ea7f00"  # noqa: E501
#
#   0xC4B34  203e8000  movea 0x80,r0,r7        bit7 LIVENESS
#   0xC4B38  8437fb97  ld.bu -0x6806[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e4000 movea 0x40
#   0xC4B44  a437e398  ld.bu -0x671d[gp],r6  | 6132 cmp 0x1,r6 | b605 blt +6 | 273e2000 movea 0x20
#   0xC4B50  8437e798  ld.bu -0x671a[gp],r6  | 6532 cmp 0x5,r6 | b105 bl  +6 | 273e1000 movea 0x10
#   0xC4B5C  8437edea  ld.bu -0x1514[gp],r6  | c6360700 andi 0x7,r6,r6 | 0731 or r7,r6
#   0xC4B66  4437ecea  st.b  r6,-0x1514[gp]     THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B6A  2436e8ea  movea -0x1518,gp,r6     the displaced hook instruction
#   0xC4B6E  7f00      jmp [lp]                -> 0x55C12
# ⚠ gp-0x671d's displacement 0x98E3 is ODD, so its opcode field reads 0x3D, not 0x3C. That is
# correct and is exactly the hw1-bit-5 trap that has produced false mismatches before.

BIT_LIVE = 0x80
BIT_GATE, BIT_MASK, BIT_ARM3 = 0x40, 0x20, 0x10
BIT_UNUSED = 0x08
PROBE_MASK = 0xF8

CEIL = 5                      # cal 0xC64FA, a BYTE. Reading it as u16 gives 517 -- the V63 trap.
ARM_VALUE = 5244              # cal 0xC6446 under V67
ARM_MASK_VALUE = 1024         # cal 0xC6442, taken when bit5 is set -- BELOW the stock creep LERP
ARM3_VALUE = 2048             # cal 0xC6440, taken when bit4 is set and bit6 is clear
LERP_AT_GRIND1 = 2622         # the mode-10 LERP at 7.2 km/h / 128 deg/s

# (bit, short name, gp cell, test text, what it decides)
GATES = (
    (BIT_GATE, "bit6 gp-0x6806", 0x6806, "!= 0",
     "*** THE GATE *** -- V67's arm is taken here and nowhere else"),
    (BIT_MASK, "bit5 gp-0x671d", 0x671d, "!= 0",
     "*** THE MASKING RISK *** -- outranks the arm; gain pinned to 1024, BELOW stock"),
    (BIT_ARM3, "bit4 gp-0x671a", 0x671a, f">= {CEIL}",
     "the THIRD arm (0xC6440 = 2048); below the gate in priority, one-way latch ~5 s"),
)

# The kill band for a gate that switches a control gain.
KILL_LO_HZ, KILL_HI_HZ = 15.0, 60.0

LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_GATE) for b in (0, BIT_MASK) for c in (0, BIT_ARM3)}

RWD_NAME = ("39990-TVA,A160-V67-LKAS-4x-mss0-decouple0xC646C-ratelane-LKASGATED-gateprobe4-"
            "can330byte4-0x13000-0x100000.rwd")
V66_RWD_NAME = ("39990-TVA,A160-V66-LKAS-4x-mss0-decouple0xC646C-ratelane-STOCK-gateprobe3-"
                "can330byte4-0x13000-0x100000.rwd")

REPOINT_ADDR = 0x3AA94
REPOINT_V67 = bytes.fromhex("847ffb97")     # ld.bu -0x6806[gp],r15  -- what V67 writes
REPOINT_V66 = bytes.fromhex("847fc597")     # ld.bu -0x683c[gp],r15  -- the dead cell, pre-V67

# The minimum duty gap between engaged and manual for bit6 to be called an engagement flag.
GATE_TRACKS_MIN = 0.5

# ★★ THE V57 BASELINE. gp-0x6806 was already validated on-car BEFORE V67 was flashed: V57's probe
# put `(gp-0x6806 == 0)` on this same bit6 and flew routes 28/29 in July. Inverting it gives
# `gp-0x6806 != 0`, which agreed with carControl.latActive at:
#     route 29   7,924 frames /  79.2 s   99.899%   duty 21.73%   4 transitions = 0.0505/s
#     route 28  29,990 frames / 299.9 s   99.943%   duty 49.88%   9 transitions = 0.0300/s
# Two very different duties => not one route's pattern; no dropout during steady engaged holding.
# 🛑 THIS DRIVE'S bit6 SHOULD REPRODUCE THAT. A materially lower agreement means either the gate
# is not behaving as it did on V57, or the build on the car is not V67. Reproduce it, do not
# assume it -- the whole point of putting the gate on a probe bit is that it is now LOAD-BEARING.
V57_BASELINE = ((29, 7924, 99.899, 21.73, 0.0505), (28, 29990, 99.943, 49.88, 0.0300))
V57_AGREEMENT_MIN = 99.0


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
                        # 🛑 Drop 0x14A frames arriving BEFORE the first 0x18F -- otherwise last_tq
                        # is NaN, and a SINGLE NaN propagates through the FFT to make every sample
                        # NaN, which reads as "0 hands-off frames": a plausible null, not an error.
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
    d["has_lat"] = bool(lat_t)
    d["v"] = np.interp(d["t"], v_t, v_v) if v_t else np.full_like(d["t"], np.nan)
    d["rev"] = (np.interp(d["t"], g_t, np.array(g_v, float)) > 0.5) if g_t \
        else np.zeros_like(d["t"], bool)
    d["has_gear"] = bool(g_t)
    return d


def sustained(x, fs, fc=3.0):
    """Zero-phase lowpass -> the DRIVER's actual push, with the oscillation removed."""
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
    m = np.asarray(mask, bool).astype(int)
    if len(m) < 2:
        return 0, 0
    dd = np.diff(m)
    return int((dd > 0).sum()), int((dd < 0).sum())


MIN_TOGGLES_FOR_SPECTRUM = 4


def runs_of(sel):
    """Contiguous [start, stop) index runs of a boolean selection mask."""
    s = np.asarray(sel, bool)
    if not s.any():
        return []
    edges = np.diff(np.concatenate(([0], s.view(np.int8), [0])))
    return list(zip(np.flatnonzero(edges > 0), np.flatnonzero(edges < 0)))


def dominant_hz(mask, fs, fmin=0.5):
    """(peak frequency, peak/median power ratio) of a boolean series' own spectrum."""
    m = np.asarray(mask, bool).astype(float)
    r, f_ = transitions(m)
    if len(m) < 64 or m.std() == 0 or (r + f_) < MIN_TOGGLES_FOR_SPECTRUM:
        return float("nan"), float("nan")
    w = np.hanning(len(m))
    P = np.abs(np.fft.rfft((m - m.mean()) * w)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / fs)
    band = f >= fmin
    if not band.any() or P[band].max() <= 0:
        return float("nan"), float("nan")
    pk = f[band][np.argmax(P[band])]
    med = np.median(P[band])
    return float(pk), (float(P[band].max() / med) if med > 0 else float("inf"))


def gate_stats(mask, sel, fs, name):
    """Duty, transitions/s, dominant toggle Hz -- the three numbers V67 lives or dies on.

    EXPOSURE is the selected sample count / fs, never t[-1]-t[0] over a discontiguous subset.
    """
    mask = np.asarray(mask, bool)
    rr = runs_of(sel)
    n = int(np.count_nonzero(sel))
    exposure = n / fs if fs > 0 else 0.0
    rise = fall = 0
    for a, b in rr:
        r, f_ = transitions(mask[a:b])
        rise += r
        fall += f_
    tps = (rise + fall) / exposure if exposure > 0 else 0.0
    pk, prom = float("nan"), float("nan")
    if rr:
        a, b = max(rr, key=lambda ab: ab[1] - ab[0])
        pk, prom = dominant_hz(mask[a:b], fs)
    return {"name": name, "n": n, "span": exposure, "runs": len(rr),
            "duty": float(mask[sel].mean()) if n else float("nan"),
            "rise": rise, "fall": fall, "tps": tps, "peak_hz": pk, "prom": prom}


def print_gate_row(s):
    if s["rise"] + s["fall"] == 0:
        pk, prom = "   never toggles", "      "
    elif not np.isfinite(s["peak_hz"]):
        pk, prom = f"  <{MIN_TOGGLES_FOR_SPECTRUM} toggles", "      "
    else:
        pk, prom = f"{s['peak_hz']:9.2f} Hz", f"{s['prom']:6.1f}x"
    print(f"   {s['name']:24s} {s['n']:7d} {s['span']:7.1f}s {s['runs']:4d}r  "
          f"duty {100 * s['duty']:6.2f}%  {s['rise']:5d}^/{s['fall']:5d}v  {s['tps']:8.3f} /s  "
          f"peak {pk} {prom}")


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    fs = 1.0 / np.median(np.diff(d["t"]))
    nyq = fs / 2.0
    field = (d["b4"] >> 3) & 0x1F
    dur = d["t"][-1] - d["t"][0]
    print(f"\n{'=' * 100}\n{tag}   {n} frames  {dur:.1f}s  fs={fs:.2f} Hz  (Nyquist {nyq:.1f} Hz)")

    # ---- 0. LIVENESS -- a HARD STOP ---------------------------------------------------------------
    void = field == 0
    print("\n-- 0. LIVENESS (HARD STOP) --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {int(void.sum())} / {n}  ({100 * void.mean():.4f}%)")
    print(f"   bit7 set                       : {int((d['b4'] & BIT_LIVE != 0).sum())} / {n}")
    print("   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"].tolist()).most_common(10)))
    if void.any():
        first = d["t"][void][0] - d["t"][0]
        print(f"\n   *** STOP. The cave failed to fire on {int(void.sum())} frame(s), first at "
              f"t+{first:.2f}s.")
        print("       Bit 7 is hard-wired to 1 by a `movea 0x80,r0,r7` that executes before any")
        print("       branch in the cave, so field == 0 cannot be a physical reading -- it means the")
        print("       hook did not run, or the frame was not produced by V67 at all.")
        print(f"       => No statistic below is trustworthy. Confirm the flashed .rwd:\n          {RWD_NAME}")
        return

    g6806 = (d["b4"] & BIT_GATE) != 0
    g671d = (d["b4"] & BIT_MASK) != 0
    g671a = (d["b4"] & BIT_ARM3) != 0
    bit3 = (d["b4"] & BIT_UNUSED) != 0

    # ---- 1. WHICH BUILD IS THIS? -- run BEFORE any verdict ----------------------------------------
    print("\n-- 1. BUILD IDENTIFICATION -- 🛑 V66 AND V67 ARE NOT STRUCTURALLY SEPARABLE --")
    illegal = np.array([(b & PROBE_MASK) not in LEGAL for b in d["b4"]])
    print(f"   bit3 SET (unused on BOTH V66 and V67) : {int(bit3.sum()):6d} / {n} "
          f"({100 * bit3.mean():.4f}%)")
    print(f"   payload not one of the 8 legal        : {int(illegal.sum()):6d} / {n} "
          f"({100 * illegal.mean():.4f}%)")
    if bit3.any() or illegal.any():
        print("\n   *** STOP. Bit 3 is never set by V67's cave and only eight payloads are reachable.")
        print("       V59's byte4 is a one-sided THERMOMETER and sets bit3 on essentially every")
        print("       frame. V64 sets it whenever gp-0x671d is non-zero. V65 sets it on the negative")
        print("       rail. All three look exactly like this. V67 arithmetically cannot.")
        print("       => CONFIRM WHICH .rwd IS FLASHED. No verdict is computed.")
        print(f"       byte4 values seen: {sorted(set(d['b4'].tolist()))}")
        print(f"       expected file: {RWD_NAME}")
        return
    print("   ⚠ THE PAYLOAD SHAPE ALONE CANNOT TELL V66 FROM V67. Same four bits, same eight bytes,")
    print("     different cells -- and the two CAVES differ by only FOUR BYTES:")
    print(f"       V66  bit6 gp-0x6806 !=0 | bit5 gp-0x67f5 !=0 | bit4 gp-0x67fe !=0")
    print(f"       V67  bit6 gp-0x6806 !=0 | bit5 gp-0x671d !=0 | bit4 gp-0x671a >={CEIL}")
    print(f"     Confirm the file on the car:\n       V67: {RWD_NAME}\n       V66: {V66_RWD_NAME}")
    print("     Weak, NON-structural hint only: V66's bit4 (base-assist substate) is expected near")
    print("     100% duty; V67's bit4 is a rare latch. This tool does not decide on that alone.")

    const87 = float((d["b4"] == 0x87).mean())
    if const87 > 0.99:
        print(f"\n   !! byte4 IS A CONSTANT 0x87 on {100 * const87:.2f}% of frames.")
        print("      *** AMBIGUOUS AND THE TOOL WILL NOT GUESS. *** Under V64 that was the NULL")
        print("      (detector never armed, 14,980 frames); under V65 the NEUTRAL bucket; under V66")
        print("      'all three gates zero'; under V67 'gate never true, no mask, no third arm'.")
        print("      For bit6 over a drive that included engagement that would itself be a")
        print("      contradiction, so the reading is suspect on its own terms.")
        print(f"      => CONFIRM THE FLASHED .rwd FILENAME first: {RWD_NAME}")

    # ---- 2. SUBSETS -------------------------------------------------------------------------------
    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    creep = d["v"] <= 5.0
    eng = d["sca"] == 1
    print("\n-- 2. ENGAGEMENT / SUBSETS (cruiseState is long+lat: NOT used) --")
    print(f"   carControl.latActive    : {int(d['lat'].sum()):6d} ({100 * d['lat'].mean():5.2f}%)"
          + ("" if d["has_lat"] else "   ⚠ ABSENT from the log -- this column is EMPTY, not zero"))
    print(f"   STEER_CONTROL_ACTIVE==1 : {int(eng.sum()):6d} ({100 * eng.mean():5.2f}%)")
    print(f"   agreement latActive vs SCA : {100 * (d['lat'] == eng).mean():.2f}%")
    print(f"   hands-off by SUSTAINED effort: {int(hands_off.sum())} "
          f"| by raw |tq|<=200: {int((np.abs(d['tq']) <= 200).sum())}  <- raw discards the oscillation")
    print(f"   creep (v <= 5 m/s)      : {int(creep.sum())}")
    if not d["has_gear"]:
        print("   ⚠ carState.gearShifter absent -- the reverse split is EMPTY, not zero.")

    verdict_ok = True
    if eng.sum() == 0 or (~eng).sum() == 0:
        print("\n   *** THE LOG HAS FRAMES IN ONLY ONE ENGAGEMENT STATE. bit6's transition structure")
        print("       cannot be measured and 'duty tracks engagement' is undefined. This is the")
        print("       'start the log before the first engagement' failure. RE-DRIVE.")
        verdict_ok = False

    # ---- 3. THE HEADLINE: bit6 DUTY vs latActive, TRANSITIONS/s, DOMINANT TOGGLE Hz ---------------
    print(f"\n{'-' * 100}\n-- 3. *** THE HEADLINE: bit6 = THE GATE *** --")
    print("   V67's arm is taken WHEN AND ONLY WHEN this bit is 1 (and bit5 is 0). Everything the")
    print("   build does rides on this row.")
    m6 = g6806
    if d["has_lat"] and d["lat"].any() and (~d["lat"]).any():
        de, dm = float(m6[d["lat"]].mean()), float(m6[~d["lat"]].mean())
        print(f"   duty vs carControl.latActive :  latActive {100 * de:6.2f}%   "
              f"manual {100 * dm:6.2f}%   gap {100 * (de - dm):+6.2f} pp")
        print(f"   agreement bit6 == latActive  : {100 * (m6 == d['lat']).mean():.2f}%")
        if de - dm < -GATE_TRACKS_MIN:
            print("   *** OBSERVED: duty is HIGHER WHEN MANUAL. THE POLARITY IS INVERTED relative to")
            print("       V67's design -- the arm would apply while the driver steers alone and NOT")
            print("       under LKAS. STOP: this is the opposite build. Do not drive on conclusions.")
            verdict_ok = False
        elif de - dm < GATE_TRACKS_MIN:
            print(f"   *** THE GATE DOES NOT TRACK LATERAL ENGAGEMENT (gap < {100*GATE_TRACKS_MIN:.0f} pp).")
            print("       Either gp-0x6806 is not the flag the kit believes, or the arm is being")
            print("       taken in a regime V67 did not intend. Treat V67 as UNVALIDATED.")
            verdict_ok = False
        else:
            print("   => the gate TRACKS lateral engagement, as designed.")
        # ---- against the V57 baseline, which validated this cell BEFORE V67 was built ------------
        agree = 100 * (m6 == d["lat"]).mean()
        print("\n   ★★ AGAINST V57's ON-CAR VALIDATION of the same cell (routes 29 / 28):")
        for rt, fr, ag, du, tps in V57_BASELINE:
            print(f"      route {rt:<3d} {fr:6d} frames   agreement {ag:.3f}%   duty {du:5.2f}%   "
                  f"{tps:.4f} transitions/s")
        s6 = gate_stats(m6, np.ones(n, bool), fs, "")
        print(f"      THIS DRIVE  {n:6d} frames   agreement {agree:.3f}%   duty "
              f"{100 * s6['duty']:5.2f}%   {s6['tps']:.4f} transitions/s")
        if agree < V57_AGREEMENT_MIN:
            print(f"      *** AGREEMENT IS BELOW {V57_AGREEMENT_MIN}%, AND V57 GOT 99.9% ON THE SAME")
            print("          CELL. Either gp-0x6806 is not behaving as it did on V57, or the build")
            print("          on the car is not V67. STOP and confirm the .rwd before interpreting.")
            verdict_ok = False
        else:
            print(f"      => reproduces V57's validation ({agree:.3f}% vs 99.90/99.94%).")
    else:
        print("   ⚠ carControl.latActive is absent or single-valued; falling back to")
        print("     STEER_CONTROL_ACTIVE for the duty comparison. Note the fallback in any writeup.")
        if eng.any() and (~eng).any():
            de, dm = float(m6[eng].mean()), float(m6[~eng].mean())
            print(f"   duty vs SCA : engaged {100 * de:6.2f}%   manual {100 * dm:6.2f}%   "
                  f"gap {100 * (de - dm):+6.2f} pp")
            if de - dm < GATE_TRACKS_MIN:
                verdict_ok = False

    print(f"\n   {'gate / subset':24s} {'n':>7s} {'expos':>8s} {'runs':>5s}  {'duty':>12s}  "
          f"{'transitions':>13s}  {'rate':>10s}  {'dominant':>17s}")
    print("   exposure = selected samples / fs;  'r' = contiguous runs. Transitions are counted")
    print("   WITHIN runs only, and the spectrum comes from the LONGEST run -- never a concatenation.")
    headline = {}
    subsets = [("ALL", np.ones(n, bool)),
               ("ENGAGED", eng),
               ("MANUAL", ~eng),
               ("ENGAGED+creep", eng & creep),
               ("MANUAL+creep", ~eng & creep)]
    for bit, name, cell, test, why in GATES:
        m = (d["b4"] & bit) != 0
        print(f"   -- {name} {test}   {why}")
        for sname, sel in subsets:
            if sel.sum() < 2:
                print(f"   {'  ' + sname:24s}   (fewer than 2 frames)")
                continue
            s = gate_stats(m, sel, fs, "  " + sname)
            print_gate_row(s)
            if sname == "ALL":
                headline[bit] = s

    # ---- 4. THE KILL CRITERION --------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 4. THE KILL CRITERION: a gain that switches near the mode frequency --")
    print(f"   ANY candidate toggling inside {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz is a PARAMETRIC")
    print("   PUMP -- the exact failure mode V58/V59/V60 chased for three builds. For bit6 that is")
    print("   an ABORT: it is the live gate on the flashed build, not a candidate.")
    for bit, name, cell, test, why in GATES:
        s = headline.get(bit)
        if s is None:
            continue
        toggles = s["rise"] + s["fall"]
        if toggles == 0:
            print(f"   {name}: NEVER TOGGLES over the whole log ({s['span']:.1f}s, duty "
                  f"{100 * s['duty']:.2f}%).")
            print("      🛑 That is NOT automatically a pass. A gate that never changes cannot be")
            print("         shown to be SLOW -- only to have not been EXERCISED.")
            if bit == BIT_GATE and eng.sum() and (~eng).sum():
                print("         *** AND THIS LOG HAS BOTH ENGAGED AND DISENGAGED FRAMES. gp-0x6806 is")
                print("             the LIVE gate on this build; if it did not move, V67's arm is")
                print("             either always or never applied. Treat V67 as UNVALIDATED.")
                verdict_ok = False
            elif bit == BIT_MASK:
                print("         => gp-0x671d stayed put. If it stayed at 0 that is the GOOD case (the")
                print("            arm was never masked); if it stayed non-zero, r24 ran at 1024 for")
                print("            the entire drive -- BELOW stock -- and V67 was worse than V66.")
                print(f"            duty says: {100 * s['duty']:.2f}% high.")
            continue
        pk_txt = (f"dominant {s['peak_hz']:.2f} Hz ({s['prom']:.1f}x median)"
                  if np.isfinite(s["peak_hz"])
                  else f"fewer than {MIN_TOGGLES_FOR_SPECTRUM} toggles in the longest run -- no "
                       "spectrum is estimated")
        print(f"   {name}: {toggles} transitions in {s['span']:.1f}s of exposure = {s['tps']:.3f}/s; "
              f"{pk_txt}")
        in_band = np.isfinite(s["peak_hz"]) and KILL_LO_HZ <= s["peak_hz"] <= min(KILL_HI_HZ, nyq)
        rate_implies_hz = s["tps"] / 2.0
        if in_band and s["prom"] >= 4.0:
            print(f"      *** INSIDE THE {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz KILL BAND. ***")
            if bit == BIT_GATE:
                print("      *** V67 IS PUMPING. Revert to V66 and do not re-flash the repoint. ***")
                verdict_ok = False
            else:
                print(f"      => gp-0x{cell:04x} is switching in the kill band. It does not switch")
                print("         V67's own arm, but it switches r24's gain between priority levels,")
                print("         which is the same mechanism. Treat as a FAIL until explained.")
                verdict_ok = False
        elif rate_implies_hz >= KILL_LO_HZ:
            print(f"      ⚠ the raw transition RATE alone implies ~{rate_implies_hz:.1f} Hz of")
            print("        switching, inside the kill band even though the spectral peak is at")
            print(f"        {s['peak_hz']:.2f} Hz. Treat as a FAIL until explained.")
            if bit == BIT_GATE:
                verdict_ok = False
        else:
            print(f"      => {s['tps']:.3f} transitions/s is {KILL_LO_HZ / max(s['tps'], 1e-9):.0f}x "
                  f"below the kill band. Quasi-static for a 21 Hz mode.")
        if np.isfinite(s["peak_hz"]) and s["peak_hz"] > 0.8 * nyq:
            print(f"      🛑 the peak sits at {s['peak_hz']:.1f} Hz, within 20% of Nyquist "
                  f"({nyq:.1f} Hz). 100 Hz sampling CANNOT distinguish it from an aliased higher")
            print("         rate -- a true 58 Hz toggle reads as 42 Hz here. UNRESOLVED, not settled.")

    # ---- 5. bit5 -- THE MASKING RISK --------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 5. *** bit5 = gp-0x671d != 0 -- THE MASKING RISK *** --")
    print("   It OUTRANKS the arm at 0x3ABFA: `cmp r0,r6 / be 0x3AC04`. When set, r24's gain is")
    print(f"   pinned to 0xC6442 = {ARM_MASK_VALUE}, which is BELOW the stock creep LERP of 3072.")
    print("   So a firing gp-0x671d does not merely mask V67's arm -- it cuts the lane to a third.")
    print(f"   duty over the whole log : {100 * g671d.mean():6.2f}%")
    if eng.sum() and (~eng).sum():
        print(f"   duty ENGAGED {100 * g671d[eng].mean():6.2f}%   MANUAL {100 * g671d[~eng].mean():6.2f}%")
    if creep.any() and (~creep).any():
        print(f"   duty CREEP   {100 * g671d[creep].mean():6.2f}%   ROAD   "
              f"{100 * g671d[~creep].mean():6.2f}%")
    both = g6806 & g671d
    print(f"   frames where the GATE WAS TRUE BUT MASKED (bit6 & bit5) : {int(both.sum())} "
          f"({100 * both.mean():.4f}% of all, "
          f"{100 * both.sum() / max(int(g6806.sum()), 1):.2f}% of gate-true frames)")
    print("   *** THAT LAST NUMBER IS THE DOSE V67 ACTUALLY FAILED TO DELIVER. ***")
    print("   V64 read this cell 0 across 14,980 frames of ONE 149.8 s creep route; its producer is")
    print("   a 3-state filter in the resolver/FOC domain, which is NOT immunity from firing during")
    print("   a 21 or 45 Hz mechanical oscillation. That is why it is on the car.")

    # ---- 6. bit4 -- the third arm -----------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 6. bit4 = gp-0x671a >= {CEIL} -- THE THIRD ARM --")
    print(f"   Selected at 0x3AC0E only when bit6 is CLEAR; it then replaces the LERP with")
    print(f"   0xC6440 = {ARM3_VALUE}. gp-0x671a is a ONE-WAY LATCH at CEIL with a ~5 s hold, so its")
    print("   tail outlives whatever set it -- a high duty here is not the same as a live event rate.")
    print(f"   duty over the whole log : {100 * g671a.mean():6.2f}%")
    if eng.sum() and (~eng).sum():
        print(f"   duty ENGAGED {100 * g671a[eng].mean():6.2f}%   MANUAL {100 * g671a[~eng].mean():6.2f}%")
    eff = g671a & ~g6806 & ~g671d
    print(f"   frames where the third arm ACTUALLY SELECTED (bit4 & !bit6 & !bit5) : "
          f"{int(eff.sum())} ({100 * eff.mean():.4f}%)")

    # ---- 7. WHAT GAIN r24 ACTUALLY RAN AT ---------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 7. WHICH ARM r24 RAN ON, resolved through the priority chain --")
    sel_mask = g671d
    sel_gate = g6806 & ~g671d
    sel_arm3 = g671a & ~g6806 & ~g671d
    sel_lerp = ~g671d & ~g6806 & ~g671a
    rows = ((f"0xC6442 = {ARM_MASK_VALUE}  MASKED, BELOW STOCK", sel_mask),
            (f"0xC6446 = {ARM_VALUE}  *** V67's ARM ***", sel_gate),
            (f"0xC6440 = {ARM3_VALUE}  third arm", sel_arm3),
            ("the mode-10 LERP        = STOCK", sel_lerp))
    for label, sel in rows:
        sub = f"  (engaged {100 * sel[eng].mean():5.2f}%)" if eng.sum() else ""
        print(f"   {label:42s} {int(sel.sum()):7d} frames  {100 * sel.mean():6.2f}%{sub}")
    assert int((sel_mask | sel_gate | sel_arm3 | sel_lerp).sum()) == n, "the four arms do not partition"
    print(f"   (the arms PARTITION the drive -- {n} frames, checked)")
    print(f"   At grind #1's operating point the stock LERP is {LERP_AT_GRIND1}, so V67's arm is")
    print(f"   {ARM_VALUE / LERP_AT_GRIND1:.2f}x there. A scalar arm cannot track the LERP's own")
    print("   rolloff, so elsewhere in the LKAS-on regime it runs roughly 1.7x-2.7x.")

    # ---- 8. BY SPEED ------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 8. BY SPEED --")
    print(f"   {'band':>12s} {'n':>7s} {'b6 duty':>9s} {'b6 t/s':>8s} {'b5 duty':>9s} {'b5 t/s':>8s} "
          f"{'b4 duty':>9s} {'b4 t/s':>8s}")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 25), (25, 99)):
        sel = (d["v"] >= lo) & (d["v"] < hi)
        if sel.sum() < 2:
            continue
        s6 = gate_stats(g6806, sel, fs, "")
        s5 = gate_stats(g671d, sel, fs, "")
        s4 = gate_stats(g671a, sel, fs, "")
        print(f"   {f'{lo}-{hi} m/s':>12s} {int(sel.sum()):7d} {100 * s6['duty']:8.2f}% "
              f"{s6['tps']:8.3f} {100 * s5['duty']:8.2f}% {s5['tps']:8.3f} "
              f"{100 * s4['duty']:8.2f}% {s4['tps']:8.3f}")

    # ---- THE VERDICT ------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- THE VERDICT --")
    for bit, name, cell, test, _why in GATES:
        s = headline.get(bit)
        if s:
            print(f"   {name} {test:6s}: duty {100 * s['duty']:6.2f}%, "
                  f"{s['rise'] + s['fall']:5d} transitions in {s['span']:.1f}s = {s['tps']:.3f}/s")
    if verdict_ok:
        print("\n   *** V67's GATE BEHAVED AS DESIGNED ON EVERY CRITERION THIS DRIVE CAN TEST. ***")
        print("   The arm was delivered on the gate-true frames counted in section 7. Read the ride")
        print("   report against THAT exposure, not against the whole drive.")
    else:
        print("\n   *** V67 IS NOT VALIDATED BY THIS DRIVE. *** See the failing criterion above.")
    print("\n   ⚠ OUTSTANDING, and NOT testable from this log:")
    print("      gp-0x683c is now UNREFERENCED image-wide (0 readers, 0 writers), so nothing can be")
    print("        measured about it and nothing needs to be -- the repoint removed its only reader.")
    print("      The r26 lane rides the SAME gate (cal 0xC6444, left at stock 512), so under LKAS")
    print("        r26's gain becomes 512 instead of its gain_A LERP. That is a REDUCTION, and it is")
    print("        harmless only because r26 is structurally inert (its average's cal base 0xC6564")
    print("        is 40 bytes of exact zero). If the ride reports LESS damping under LKAS rather")
    print("        than less grinding, this is the first place to look.")
    print("      Grind #2 SURVIVES under LKAS by design. V67 removes V62's amplification only where")
    print("        the gate is false. Judge grind #2 on the MANUAL rows, not the engaged ones.")
    if const87 > 0.99:
        print(f"\n   🛑 ...AND ALL OF THE ABOVE IS CONDITIONAL ON V67 ACTUALLY BEING FLASHED.")
        print(f"      Confirm the .rwd on the car: {RWD_NAME}")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
