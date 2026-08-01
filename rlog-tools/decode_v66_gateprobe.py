#!/usr/bin/env python3
"""decode_v66_gateprobe.py -- read V66's three-gate probe out of an rlog.

V66 packs three plain `!= 0` tests on gp-relative BYTE cells into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                  LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x6806 != 0     *** V67's PROPOSED GATE ***  (LKAS active, per FUN_00028ea6)
    bit 5 = gp-0x67f5 != 0     driver-torque hands-on gate candidate
    bit 4 = gp-0x683c != 0     *** THE CONTROL *** -- zero writers image-wide, MUST be 0 always
    bit 3 = 0                  UNUSED on V66. A set bit3 means the build on the car is NOT V66.
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

WHAT THIS DRIVE DECIDES -- pre-committed in build_v66_tva.py, before the drive
------------------------------------------------------------------------------
V66 is the pre-flight for V67, which repoints ONE BYTE at 0x3AA96 (`c5` -> `fb`) so that the dead
`ld.bu -0x683c[gp],r15` @0x3AA94 reads `gp-0x6806` instead, turning cal `0xC6446` into an LKAS-only
gain override for r24. Three things can kill that design, and each has a bit:

  bit4 EVER 1  => gp-0x683c is NOT dead. The repoint is not a clean substitution. *** V67 CANCELLED. ***
  bit6 TOGGLE RATE in 15-60 Hz => a gain switching near the mode frequency is a PARAMETRIC PUMP,
       the exact failure mode V58/V59/V60 chased for three builds. *** V67 CANCELLED. ***
  bit5 TOGGLE RATE in 15-60 Hz => gp-0x67f5 is unusable as an alternative gate, for the same reason.

The HEADLINE for each of bits 6 and 5 is therefore, in this order: DUTY CYCLE, TRANSITIONS PER
SECOND, and the DOMINANT TOGGLE FREQUENCY. Everything else in this tool is supporting evidence.

🛑 NYQUIST. The probe is 100 Hz, so the kill band 15-60 Hz is NOT fully observable: a true 58 Hz
toggle aliases to 42 Hz and a true 51 Hz toggle to 49 Hz. This tool reports the observed peak and
says explicitly that anything at or near 50 Hz is unresolved -- it never prints a number that looks
settled when it is not. This is the same alias `docs/V66-V67-DESIGN.md` states up front for the
41.64 / 58.86 Hz pair.

🛑 THIS TOOL REJECTS V59, V64 AND V65 SEMANTICS EXPLICITLY
-----------------------------------------------------------
The same five bits have now carried FOUR different meanings, and reading one build's log with
another build's decoder has already cost this kit a session:

    V59 : bit6 = fault sentinel, bits 5/4/3 = a one-sided THERMOMETER (index<512 => <1024 => <2048)
    V64 : bit6 = gp-0x671a >= 5, bit5 = gp-0x671a != 0, bit4 = FSM != 0, bit3 = gp-0x671d != 0
    V65 : a symmetric four-level saturation ladder on gp-0x6b94; bit3 = the NEGATIVE rail
    V66 : the three independent gate booleans above; *** bit3 is NEVER SET ***

V66's discriminator is structural and cheap: bit3 is unused, so ANY frame with bit3 set is not a V66
frame. V59 sets bit3 on essentially every frame; V64 sets it whenever gp-0x671d is non-zero; V65
sets it on the negative rail. Conversely, a V66 frame with bit6 set and bit5 clear (0xC7) is
STRUCTURALLY IMPOSSIBLE under V65 (bit6 => bit5 there), so the two builds are mutually detectable.

⚠ AND THE ONE CASE STRUCTURE CANNOT SETTLE: a CONSTANT 0x87.
  Under V66 that is a legitimate reading -- "cave fired, all three gates zero for the whole drive".
  It is byte-identical to V64's null (detector never armed, 14,980 frames) and to V65's NEUTRAL
  bucket. This tool STOPS and asks which .rwd is on the car rather than guessing.

🛑 CONVENTIONS THIS TOOL ENFORCES -- all established the hard way on the V57/V58 drives:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes
     while lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. START THE LOG BEFORE THE FIRST ENGAGEMENT, or bit6's transition structure is unmeasurable --
     a log that begins mid-engagement can show 100% duty and zero transitions and mean nothing.

Usage:  python decode_v66_gateprobe.py RLOG [RLOG ...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from rlog_parse import read_messages  # noqa: E402

BIT_LIVE = 0x80
BIT_6806, BIT_67F5, BIT_683C = 0x40, 0x20, 0x10
BIT_UNUSED = 0x08
PROBE_MASK = 0xF8

# (bit, short name, gp cell, what it decides)
GATES = ((BIT_6806, "bit6 gp-0x6806", 0x6806, "V67's PROPOSED GATE (LKAS active)"),
         (BIT_67F5, "bit5 gp-0x67f5", 0x67f5, "driver-torque hands-on gate candidate"),
         (BIT_683C, "bit4 gp-0x683c", 0x683c, "THE CONTROL -- must be 0 in 100% of frames"))

# The kill band for a gate that switches a control gain. Below this a gain step is quasi-static;
# inside it the switching itself pumps the mode.
KILL_LO_HZ, KILL_HI_HZ = 15.0, 60.0

# Exactly eight payloads are reachable (probe bits only; bits 2:0 are the live status field).
LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_6806) for b in (0, BIT_67F5) for c in (0, BIT_683C)}

RWD_NAME = ("39990-TVA,A160-V66-LKAS-4x-mss0-decouple0xC646C-ratelane-STOCK-gateprobe3-"
            "can330byte4-0x13000-0x100000.rwd")


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
    d["v"] = np.interp(d["t"], v_t, v_v) if v_t else np.full_like(d["t"], np.nan)
    d["rev"] = (np.interp(d["t"], g_t, np.array(g_v, float)) > 0.5) if g_t \
        else np.zeros_like(d["t"], bool)
    d["has_gear"] = bool(g_t)
    return d


def sustained(x, fs, fc=3.0):
    """Zero-phase lowpass -> the DRIVER's actual push, with the oscillation removed.

    ⚠ NaN-fragile by construction (one NaN in, all NaN out), so the input is repaired first.
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


MIN_TOGGLES_FOR_SPECTRUM = 4


def runs_of(sel):
    """Contiguous [start, stop) index runs of a boolean selection mask.

    🛑 Every statistic below is computed PER RUN and then pooled. Concatenating a discontiguous
    subset and treating it as one series manufactures a transition at every join -- V58's pooled
    coherence of ~0.5 at 25 Hz turned out to be exactly that, and the retraction is on record.
    """
    s = np.asarray(sel, bool)
    if not s.any():
        return []
    edges = np.diff(np.concatenate(([0], s.view(np.int8), [0])))
    return list(zip(np.flatnonzero(edges > 0), np.flatnonzero(edges < 0)))


def dominant_hz(mask, fs, fmin=0.5):
    """(peak frequency, peak/median power ratio) of a boolean series' own spectrum.

    Mean-removed so a constant-duty signal has no DC line. Returns (nan, nan) when the bit toggles
    fewer than MIN_TOGGLES_FOR_SPECTRUM times -- a two-transition series has no spectrum worth the
    name, and reporting its argmax as "the dominant frequency" is how a step edge becomes a finding.
    """
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

    `mask` is the FULL-LENGTH bit series and `sel` the FULL-LENGTH subset mask, so runs can be found
    before either is sliced. EXPOSURE is the selected sample count / fs, never t[-1]-t[0] over a
    discontiguous subset: a 60-s-on / 60-s-off engagement pattern spans the whole log but is exposed
    for half of it, and dividing by the span would halve every rate.
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
    # the spectrum comes from the LONGEST contiguous run only -- see runs_of()
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

    # ---- 0. LIVENESS -- a HARD STOP, per the build note -------------------------------------------
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
        print("       hook did not run, or the frame was not produced by V66 at all.")
        print("       => No gate statistic below is trustworthy. Confirm the flashed .rwd:")
        print(f"          {RWD_NAME}")
        return

    g6806 = (d["b4"] & BIT_6806) != 0
    g67f5 = (d["b4"] & BIT_67F5) != 0
    g683c = (d["b4"] & BIT_683C) != 0
    bit3 = (d["b4"] & BIT_UNUSED) != 0

    # ---- 1. WHICH BUILD IS THIS? -- run BEFORE any verdict -----------------------------------------
    print("\n-- 1. BUILD IDENTIFICATION (byte4 means different things on V59 / V64 / V65 / V66) --")
    illegal = np.array([(b & PROBE_MASK) not in LEGAL for b in d["b4"]])
    print(f"   bit3 SET (unused on V66)          : {int(bit3.sum()):6d} / {n} "
          f"({100 * bit3.mean():.4f}%)   <- THE DISCRIMINATOR")
    print(f"   payload not one of the 8 legal    : {int(illegal.sum()):6d} / {n} "
          f"({100 * illegal.mean():.4f}%)")
    if bit3.any() or illegal.any():
        print("\n   *** STOP. Bit 3 is never set by V66's cave and only eight payloads are reachable.")
        print("       V59's byte4 is a one-sided THERMOMETER and sets bit3 on essentially every frame.")
        print("       V64 sets bit3 whenever gp-0x671d is non-zero. V65 sets it on the negative rail.")
        print("       All three look exactly like this. V66 arithmetically cannot.")
        print("       => CONFIRM WHICH .rwd IS FLASHED. No verdict is computed: the surviving subset")
        print("          would still look plausible, which is exactly how this trap works.")
        print(f"       byte4 values seen: {sorted(set(d['b4'].tolist()))}")
        print(f"       expected file: {RWD_NAME}")
        return

    # ⚠ the one ambiguity structure cannot settle
    const87 = float((d["b4"] == 0x87).mean())
    if const87 > 0.99:
        print(f"\n   !! byte4 IS A CONSTANT 0x87 on {100 * const87:.2f}% of frames.")
        print("      *** THIS IS AMBIGUOUS AND THE TOOL WILL NOT GUESS. ***")
        print("      Under V64 that was the NULL: the oscillation detector never armed (14,980 frames).")
        print("      Under V65 it is the NEUTRAL bucket -- cave fired, sum never past +/-4096.")
        print("      Under V66 it is 'cave fired, all three gates zero for the entire drive' -- which")
        print("      for bit6 (LKAS active) over a drive that included engagement would itself be a")
        print("      contradiction, so this reading is suspect on its own terms.")
        print("      => CONFIRM THE FLASHED .rwd FILENAME before reading anything below:")
        print(f"         {RWD_NAME}")

    # ---- 2. THE CONTROL -- a HARD STOP, per the build note -----------------------------------------
    print("\n-- 2. *** THE CONTROL: bit4 = gp-0x683c != 0 *** --")
    print(f"   frames with bit4 SET : {int(g683c.sum())} / {n}  ({100 * g683c.mean():.4f}%)")
    if g683c.any():
        first = d["t"][g683c][0] - d["t"][0]
        print(f"\n   *** STOP. gp-0x683c is NOT DEAD. First non-zero at t+{first:.2f}s, "
              f"{int(g683c.sum())} frames.")
        print("       The byte scan finds exactly ONE access to this cell image-wide -- the very")
        print("       `ld.bu -0x683c[gp],r15` @0x3AA94 that V67 proposes to repoint -- and ZERO")
        print("       writers, in both the Format-VII and the 48-bit extended form. A non-zero value")
        print("       therefore means either the RAM init leaves it non-zero, or something writes it")
        print("       through a computed pointer that no displacement scan can see.")
        print("       Either way the repoint is NOT a clean substitution: 0xC6446 = 512 is currently")
        print("       LIVE for r24, and V67's arm value was sized on the assumption that it is not.")
        print("       *** V67 IS CANCELLED AS DESIGNED. *** Re-derive the r24 gain arm actually in")
        print("       force before proposing anything else on this lane.")
        return
    print("   => gp-0x683c reads 0 in 100% of frames. The dead-cell claim SURVIVES this drive, and")
    print("      V67's repoint remains a clean substitution on this criterion.")

    # ---- 3. THE HEADLINE: DUTY, TRANSITIONS/s, DOMINANT TOGGLE Hz ----------------------------------
    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    creep = d["v"] <= 5.0
    eng = d["sca"] == 1
    print("\n-- 3. ENGAGEMENT / SUBSETS (cruiseState is long+lat: NOT used) --")
    print(f"   latActive               : {int(d['lat'].sum()):6d} ({100 * d['lat'].mean():5.2f}%)")
    print(f"   STEER_CONTROL_ACTIVE==1 : {int(eng.sum()):6d} ({100 * eng.mean():5.2f}%)")
    print(f"   agreement latActive vs SCA : {100 * (d['lat'] == eng).mean():.2f}%")
    print(f"   hands-off by SUSTAINED effort: {int(hands_off.sum())} "
          f"| by raw |tq|<=200: {int((np.abs(d['tq']) <= 200).sum())}  <- raw discards the oscillation")
    print(f"   creep (v <= 5 m/s)      : {int(creep.sum())}")
    if not d["has_gear"]:
        print("   ⚠ carState.gearShifter absent -- the reverse split is EMPTY, not zero.")
    if eng.sum() == 0:
        print("\n   ⚠ NO ENGAGED FRAMES AT ALL. bit6's transition structure cannot be measured from a")
        print("     drive with no engagement, and 'bit6 duty 0%' below is then trivially true.")

    print(f"\n{'-' * 100}\n-- 4. *** THE HEADLINE: DUTY, TRANSITIONS/s, DOMINANT TOGGLE Hz *** --")
    print(f"   V67 is CANCELLED if bit6 (or bit5, as an alternative gate) toggles inside "
          f"{KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz.")
    print("   exposure = selected samples / fs;  'r' = contiguous runs. Transitions are counted")
    print("   WITHIN runs only, and the spectrum comes from the LONGEST run -- never a concatenation.")
    print(f"   {'gate / subset':24s} {'n':>7s} {'expos':>8s} {'runs':>5s}  {'duty':>12s}  "
          f"{'transitions':>13s}  {'rate':>10s}  {'dominant':>17s}")
    headline = {}
    subsets = [("ALL", np.ones(n, bool)),
               ("ENGAGED", eng),
               ("MANUAL", ~eng),
               ("ENGAGED+creep", eng & creep),
               ("MANUAL+creep", ~eng & creep)]
    for bit, name, cell, why in GATES[:2]:
        m = (d["b4"] & bit) != 0
        print(f"   -- {name}   {why}")
        for sname, sel in subsets:
            if sel.sum() < 2:
                print(f"   {'  ' + sname:24s}   (fewer than 2 frames)")
                continue
            s = gate_stats(m, sel, fs, "  " + sname)
            print_gate_row(s)
            if sname == "ALL":
                headline[bit] = s

    # ---- 5. THE KILL CRITERION ---------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 5. THE KILL CRITERION --")
    verdict_ok = True
    for bit, name, cell, why in GATES[:2]:
        s = headline.get(bit)
        if s is None:
            continue
        m = (d["b4"] & bit) != 0
        toggles = s["rise"] + s["fall"]
        if toggles == 0:
            print(f"   {name}: NEVER TOGGLES over the whole log ({s['span']:.1f}s, duty "
                  f"{100 * s['duty']:.2f}%).")
            print("      🛑 That is NOT automatically a pass. A gate that never changes cannot be")
            print("         shown to be SLOW -- it can only be shown not to have been EXERCISED.")
            if bit == BIT_6806 and eng.sum() and (~eng).sum():
                print("         *** AND THIS LOG HAS BOTH ENGAGED AND DISENGAGED FRAMES. If gp-0x6806")
                print("             were the LKAS-active flag it would have moved. Treat it as NOT")
                print("             CONFIRMED and DO NOT FLASH V67.")
                verdict_ok = False
            elif bit == BIT_67F5 and (sus > 200).any() and (sus <= 200).any():
                print("         *** AND THIS LOG HAS BOTH HANDS-ON AND HANDS-OFF FRAMES. gp-0x67f5 is")
                print("             then not the driver-torque gate this kit reads it as -- which does")
                print("             not block V67, but retires it as an alternative gate.")
            continue
        pk_txt = (f"dominant {s['peak_hz']:.2f} Hz ({s['prom']:.1f}x median)"
                  if np.isfinite(s["peak_hz"])
                  else f"fewer than {MIN_TOGGLES_FOR_SPECTRUM} toggles in the longest run -- no "
                       "spectrum is estimated")
        print(f"   {name}: {toggles} transitions in {s['span']:.1f}s of exposure = {s['tps']:.3f}/s; "
              f"{pk_txt}")
        in_band = np.isfinite(s["peak_hz"]) and KILL_LO_HZ <= s["peak_hz"] <= min(KILL_HI_HZ, nyq)
        # a toggle RATE argument that does not depend on the spectrum at all
        rate_implies_hz = s["tps"] / 2.0
        if in_band and s["prom"] >= 4.0:
            print(f"      *** INSIDE THE {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz KILL BAND. ***")
            print("      A gain that switches at the mode frequency is a PARAMETRIC PUMP -- the exact")
            print("      failure mode V58/V59/V60 chased for three builds.")
            if bit == BIT_6806:
                print("      *** V67 IS CANCELLED. *** Do not flash the repoint.")
                verdict_ok = False
            else:
                print("      => gp-0x67f5 is UNUSABLE as an alternative gate. Do not substitute it.")
        elif rate_implies_hz >= KILL_LO_HZ:
            print(f"      ⚠ the raw transition RATE alone implies ~{rate_implies_hz:.1f} Hz of")
            print("        switching, which is inside the kill band even though the spectral peak is")
            print(f"        at {s['peak_hz']:.2f} Hz. Treat as a FAIL until explained.")
            if bit == BIT_6806:
                verdict_ok = False
        else:
            print(f"      => {s['tps']:.3f} transitions/s is {KILL_LO_HZ / max(s['tps'], 1e-9):.0f}x "
                  f"below the kill band. Quasi-static for a 20.9 Hz mode.")
        if np.isfinite(s["peak_hz"]) and s["peak_hz"] > 0.8 * nyq:
            print(f"      🛑 the peak sits at {s['peak_hz']:.1f} Hz, within 20% of Nyquist "
                  f"({nyq:.1f} Hz).")
            print("         100 Hz sampling CANNOT distinguish it from an aliased higher rate --")
            print("         a true 58 Hz toggle reads as 42 Hz here. UNRESOLVED, not settled.")

    # ---- 6. bit6 vs ENGAGEMENT -- is gp-0x6806 the flag the kit thinks it is? ----------------------
    print(f"\n{'-' * 100}\n-- 6. IS gp-0x6806 REALLY THE LKAS-ACTIVE FLAG? --")
    if eng.sum() and (~eng).sum():
        agree = float((g6806 == eng).mean())
        print(f"   agreement bit6 vs STEER_CONTROL_ACTIVE : {100 * agree:.2f}%")
        print(f"   agreement bit6 vs carControl.latActive : {100 * (g6806 == d['lat']).mean():.2f}%")
        print(f"   bit6 duty ENGAGED {100 * g6806[eng].mean():6.2f}%   "
              f"MANUAL {100 * g6806[~eng].mean():6.2f}%")
        print("   🛑 POLARITY. `docs/V66-V67-DESIGN.md` records the kit's own account as AMBIGUOUS --")
        print("      one note has the deadband gate enabled when gp-0x6806 == 0, another has == 1 in")
        print("      96.26% of an engaged route. THIS LINE RESOLVES IT: if the duty is high when")
        print("      ENGAGED, then `!= 0` means LKAS-ACTIVE and V67's 6144 arm applies under LKAS as")
        print("      designed. If it is high when MANUAL, THE WHOLE DESIGN INVERTS and the arm value")
        print("      changes meaning entirely -- do not flash V67 without re-deriving it.")
        if g6806[eng].mean() < g6806[~eng].mean():
            print("      *** OBSERVED: duty is HIGHER WHEN MANUAL. The polarity is INVERTED relative")
            print("          to V67's design. STOP and re-derive before flashing.")
            verdict_ok = False
    else:
        print("   the log has frames in only ONE engagement state, so the correlation is undefined.")
        print("   ⚠ This is the 'start the log before the first engagement' failure. Re-drive.")
        verdict_ok = False

    # ---- 7. bit5, in its own right ------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 7. bit5 = gp-0x67f5 != 0, AS A SIGNAL --")
    if eng.sum() and (~eng).sum():
        print(f"   duty ENGAGED {100 * g67f5[eng].mean():6.2f}%   MANUAL {100 * g67f5[~eng].mean():6.2f}%")
    sus_hi = sus > 200
    if sus_hi.any() and (~sus_hi).any():
        print(f"   duty with SUSTAINED driver effort > 200 : {100 * g67f5[sus_hi].mean():6.2f}%")
        print(f"   duty hands-off (sustained <= 200)       : {100 * g67f5[~sus_hi].mean():6.2f}%")
        print("   => a large gap is what a hands-on/driver-torque gate should look like; no gap means")
        print("      the 'driver-torque' reading of this cell is not supported by the drive.")

    # ---- 8. BY SPEED --------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 8. BY SPEED --")
    print(f"   {'band':>14s} {'n':>7s} {'bit6 duty':>11s} {'bit6 t/s':>10s} {'bit5 duty':>11s} "
          f"{'bit5 t/s':>10s}")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 25), (25, 99)):
        sel = (d["v"] >= lo) & (d["v"] < hi)
        if sel.sum() < 2:
            continue
        s6 = gate_stats(g6806, sel, fs, "")
        s5 = gate_stats(g67f5, sel, fs, "")
        print(f"   {f'{lo}-{hi} m/s':>14s} {int(sel.sum()):7d} {100 * s6['duty']:10.2f}% "
              f"{s6['tps']:10.3f} {100 * s5['duty']:10.2f}% {s5['tps']:10.3f}")

    # ---- THE VERDICT --------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- THE VERDICT (pre-committed in build_v66_tva.py, before the drive) --")
    print(f"   bit4 (the control) : 0 on all {n} frames  => the dead-cell claim survives")
    s6 = headline.get(BIT_6806)
    if s6:
        print(f"   bit6 (the gate)    : duty {100 * s6['duty']:.2f}%, {s6['rise'] + s6['fall']} "
              f"transitions in {s6['span']:.1f}s = {s6['tps']:.3f}/s")
    if verdict_ok:
        print("\n   *** V67 IS CLEARED ON EVERY CRITERION THIS DRIVE CAN TEST. ***")
        print("   Next: 0x3AA96 c5 -> fb (repoint the dead gate to gp-0x6806) and 0xC6446 512 -> 6144.")
        print("   ⚠ Still OUTSTANDING and NOT tested by this build: gp-0x671d, the masking risk. It")
        print("      OUTRANKS the LKAS arm in r24's priority chain, so if it latches non-zero V67's")
        print("      arm never applies. It did not fit in the 68-byte cave (a fourth rung needs 12")
        print("      bytes and 8 were spare -- build_v66_tva.py carries the arithmetic). V64 measured")
        print("      it 0 across 14,980 frames of route 35; that is the ONLY evidence, and it is one")
        print("      route. A null V67 must be read against that gap, not as a falsified lever.")
    else:
        print("\n   *** V67 IS NOT CLEARED. *** See the failing criterion above. Do not flash the")
        print("   repoint until it is explained.")
    if const87 > 0.99:
        print("\n   🛑 ...AND ALL OF THE ABOVE IS CONDITIONAL ON V66 ACTUALLY BEING FLASHED. byte4 was")
        print("      a constant 0x87, byte-identical to V64's null and V65's NEUTRAL bucket.")
        print(f"      Confirm the .rwd on the car: {RWD_NAME}")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
