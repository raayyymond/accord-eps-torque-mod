#!/usr/bin/env python3
"""probe/decode_v66_gateprobe.py -- read V66's three-gate probe out of an rlog.

V66 packs three plain `!= 0` tests on gp-relative BYTE cells into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                  LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x6806 != 0     gate candidate A -- LKAS active, per FUN_00028ea6   (EVEN disp 0x97FA)
    bit 5 = gp-0x67f5 != 0     gate candidate B -- 🛑 THREE-VALUED {0,1,0xFF}      (ODD  disp 0x980B)
    bit 4 = gp-0x67fe != 0     gate candidate C -- DISPUTED SEMANTICS, see below   (EVEN disp 0x9802)
    bit 3 = 0                  UNUSED on V66. A set bit3 means the build on the car is NOT V66.
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

🛑 THIS HEADER WAS STALE FOR ONE REVISION AND SAID bit4 = gp-0x683c ("the control"). IT IS NOT.
The built image reads `ld.bu -0x67fe[gp],r6` @0xC4B50 (bytes `84 37 03 98`, verified from the
artifact). gp-0x683c is NOT measured by V66 -- only three rungs fit the 68-byte extent, and all three
slots went to GATE CANDIDATES. Confirm against the image before trusting any decoder header; this file
is the exact class of trap it warns about two paragraphs down.

WHAT THIS DRIVE DECIDES -- pre-committed in builds/v50_v79/build_v66_tva.py, before the drive
------------------------------------------------------------------------------
V66 is the pre-flight for V67, which repoints ONE BYTE at 0x3AA96 so that the dead
`ld.bu -0x683c[gp],r15` @0x3AA94 reads a chosen gate cell instead, turning cal `0xC6446` into a
CONDITIONAL gain override for r24. **V66's job is to pick which cell.**

  bit5 or bit6 or bit4 TOGGLING in 15-60 Hz => that candidate is DEAD. A gain switching near the mode
       frequency is a PARAMETRIC PUMP -- the exact failure mode V58/V59/V60 chased for three builds,
       and worse than the symptom it would fix.
  bit4 DUTY ~= 100%  => gp-0x67fe is the golden model's `assist_substate` (BASE assist), not an LKAS
       flag, and it is worthless as a gate. Duty tracking engagement => it is the best candidate found.
       This single number settles a dispute between a trace and the golden model.
  bit6 DUTY vs latActive => confirms gp-0x6806 really is the engagement flag `STEER_CONTROL_ACTIVE`
       is sourced from, on a long drive rather than the single 180 s route on record.

The HEADLINE for each of bits 6, 5 and 4 is therefore, in this order: DUTY CYCLE, TRANSITIONS PER
SECOND, and the DOMINANT TOGGLE FREQUENCY. Everything else in this tool is supporting evidence.

⚠ gp-0x683c's deadness -- the premise of the repoint -- is NOT measured on this drive. It rests on two
independent static methods (a raw byte scan in both encodings at every offset, and a 3-method
cross-check). Static clearance has failed this kit before (`gp-0x1500`), so this is a real residual;
the mitigation is that if gp-0x683c were live, V65's r24 gain would already be taking the 512 arm today.
⚠ gp-0x671d, the MASKING RISK that outranks the LKAS arm in r24's priority chain, is also NOT measured
(dropped by the final spec). V64 read it 0 across 14,980 frames of ONE route. Neither absence is a pass.

🛑 bit5's CELL IS THREE-VALUED AND THE PROBE IS ONE BIT -- and its "driver-torque" label is not
   supported by the code
--------------------------------------------------------------------------------------------------
`FUN_00041eec` (body 0x41EEC-0x42375) is gp-0x67f5's SOLE writer and stores THREE distinct values:

    0xFF @0x4222A   the INVALID / not-evaluated sentinel, taken while gp-0x67f4 == 0
       1 @0x42258   latched, after a debounce
       0 @0x42288   cleared, after a debounce

So `!= 0` CONFLATES the latch with the sentinel. Disambiguation rule, stated as a HYPOTHESIS: 0xFF is
entered only under a persistent condition, so bit5 HIGH from frame 0 and never toggling reads as the
sentinel, while bit5 debouncing up and down reads as the latch.

And FUN_00041eec reads NO TORQUE CELL. It reads the voted vehicle speed `gp-0x6a5e` into r7, loops
four slots out of the halfwords gp-0x6a38/-0x6a3c/-0x6a40/-0x6a44 (plus gp-0x6a46) computing
|speed - |slot||, reduces them to a max deviation r28 clamped to 0x7D00, and latches when

    r28 >= cal tp+0x731e (0xC631E = 640 counts ~ 10 km/h) for cal tp+0x74e7 (0xC64E7 = 10) ticks.

That reads as a DEBOUNCED WHEEL-SPEED-vs-VEHICLE-SPEED PLAUSIBILITY LATCH -- a fault flag near-
constant 0 in normal driving -- not a hands-on gate. If so its toggle rate is trivially ~0 and a
quiet bit5 is an UNEXERCISED gate, not a good one. Do not read silence as a pass.

🛑 NYQUIST. The probe is 100 Hz, so the kill band 15-60 Hz is NOT fully observable: a true 58 Hz
toggle aliases to 42 Hz and a true 51 Hz toggle to 49 Hz. This tool reports the observed peak and
says explicitly that anything at or near 50 Hz is unresolved -- it never prints a number that looks
settled when it is not. This is the same alias `docs/specs/design/V66-V67-DESIGN.md` states up front for the
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

Usage:  python probe/decode_v66_gateprobe.py RLOG [RLOG ...]
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

BIT_LIVE = 0x80
BIT_6806, BIT_67F5, BIT_67FE = 0x40, 0x20, 0x10
BIT_UNUSED = 0x08
PROBE_MASK = 0xF8

# (bit, short name, gp cell, what it decides)
GATES = ((BIT_6806, "bit6 gp-0x6806", 0x6806, "gate candidate A -- V67's currently drawn gate"),
         (BIT_67F5, "bit5 gp-0x67f5", 0x67f5, "gate candidate B -- THREE-VALUED {0,1,0xFF}"),
         (BIT_67FE, "bit4 gp-0x67fe", 0x67fe, "gate candidate C -- semantics DISPUTED"))

# The kill band for a gate that switches a control gain. Below this a gain step is quasi-static;
# inside it the switching itself pumps the mode.
KILL_LO_HZ, KILL_HI_HZ = 15.0, 60.0

# Exactly eight payloads are reachable (probe bits only; bits 2:0 are the live status field).
LEGAL = {BIT_LIVE | a | b | c
         for a in (0, BIT_6806) for b in (0, BIT_67F5) for c in (0, BIT_67FE)}

RWD_NAME = ("39990-TVA,A160-V66-LKAS-4x-mss0-decouple0xC646C-ratelane-STOCK-gateprobe3-"
            "can330byte4-0x13000-0x100000.rwd")

# V67's repoint site: `ld.bu -0x683c[gp],r15` @0x3AA94, bytes 84 7f c5 97.
REPOINT_ADDR = 0x3AA94
REPOINT_CURRENT = bytes.fromhex("847fc597")


def ldbu_bytes(disp, reg2, reg1=4):
    """Encode `ld.bu -disp[reg1],reg2` -- V850E puts the displacement's bit 0 in hw1 BIT 5.

    hw1 = (reg2 << 11) | (opcode << 5) | reg1, opcode = 0x3C | (d & 1)
    hw2 = (d & 0xFFFE) | 1     <- the trailing 1 is the ld.bu/ld.hu WIDTH selector, not a disp bit
    """
    d = (0x10000 - disp) & 0xFFFF
    return bytes([((reg2 << 11) | ((0x3C | (d & 1)) << 5) | reg1) & 0xFF,
                  (((reg2 << 11) | ((0x3C | (d & 1)) << 5) | reg1) >> 8) & 0xFF,
                  (d & 0xFE) | 1, (d >> 8) & 0xFF])


def repoint_edit(cell, reg2=15):
    """The exact byte edit that repoints REPOINT_ADDR to `cell`, and how many bytes it costs.

    🛑 Derived, never hand-written. The design note's "ONE BYTE at 0x3AA96" holds only for an EVEN
    target whose high displacement byte already matches; it is wrong for gp-0x67f5 and incomplete for
    gp-0x67fe, and a wrong answer here silently reads the neighbouring cell.
    """
    want = ldbu_bytes(cell, reg2)
    diff = [i for i in range(4) if want[i] != REPOINT_CURRENT[i]]
    where = " ".join(f"0x{REPOINT_ADDR + i:05X}:{REPOINT_CURRENT[i]:02x}->{want[i]:02x}" for i in diff)
    halfwords = sorted({i // 2 for i in diff})
    return (f"gp-0x{cell:04x}: {want.hex(' ')}  ({len(diff)} byte(s), "
            f"hw{'+'.join(str(h + 1) for h in halfwords)})  {where}")


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
    g67fe = (d["b4"] & BIT_67FE) != 0
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

    # ---- 2. WHAT THIS BUILD DOES **NOT** MEASURE ---------------------------------------------------
    print("\n-- 2. NOT MEASURED BY V66 -- read before drawing any conclusion --")
    print("   gp-0x683c (the CONTROL, V67's repoint site) -- the bit was cut for cave budget. Its")
    print("     dead-cell claim rests on STATIC evidence only: 1 reader, 0 writers, 0 extended-form")
    print("     candidates, reproduced by two independent decoders on every build. That cannot rule")
    print("     out a non-zero RAM-init value or a write through a computed pointer.")
    print("   gp-0x671d (the MASKING RISK) -- dropped by the final spec. V64 measured it 0 across")
    print("     14,980 frames of ONE route. If V67 behaves as if its arm never applied, start here.")
    print("   Neither absence may be read as a pass.")

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
    print(f"   ANY candidate that toggles inside {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz is DISQUALIFIED "
          "as a gate. If it is bit6, V67 as drawn is CANCELLED.")
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
    for bit, name, cell, why in GATES:
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
    for bit, name, cell, why in GATES:
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
            elif bit == BIT_67F5 and eng.sum() and (~eng).sum():
                print(f"         => consistent with the reading that gp-0x67f5 is a DEBOUNCED "
                      f"WHEEL-SPEED")
                print("            PLAUSIBILITY LATCH (r28 >= cal 0xC631E = 640 counts ~ 10 km/h for")
                print("            10 ticks, in FUN_00041eec), i.e. a fault flag that is 0 in normal")
                print("            driving. A quiet gate is NOT the same as a good gate: it has not")
                print("            been shown to switch with anything. RETIRE candidate B.")
            elif bit == BIT_67FE and eng.sum() and (~eng).sum():
                print("         => gp-0x67fe never moved across engagement. It is not the LKAS engage")
                print("            state. RETIRE candidate C.")
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
                print(f"      => gp-0x{cell:04x} is UNUSABLE as an alternative gate. Do not substitute it.")
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
        print("   🛑 POLARITY. `docs/specs/design/V66-V67-DESIGN.md` records the kit's own account as AMBIGUOUS --")
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

    # ---- 7. bit5 -- and the {0, 1, 0xFF} ambiguity the `!= 0` test cannot resolve --------------------
    print(f"\n{'-' * 100}\n-- 7. bit5 = gp-0x67f5 != 0  🛑 A THREE-VALUED CELL SEEN THROUGH ONE BIT --")
    print("   FUN_00041eec is the SOLE writer and it stores THREE distinct values:")
    print("     0xFF @0x4222A  the INVALID / not-evaluated sentinel, taken while gp-0x67f4 == 0")
    print("        1 @0x42258  latched, after a debounce")
    print("        0 @0x42288  cleared, after a debounce")
    print("   `!= 0` therefore CONFLATES the latched state with the sentinel. Disambiguation rule,")
    print("   stated as a HYPOTHESIS: 0xFF is entered only under a persistent condition, so bit5 HIGH")
    print("   continuously from the first frame reads as the sentinel, while bit5 debouncing up and")
    print("   down reads as the latch. This tool cannot prove which; it reports the shape.")
    first_run_high = bool(g67f5[0]) and (transitions(g67f5)[0] + transitions(g67f5)[1] == 0)
    print(f"   bit5 high on frame 0: {bool(g67f5[0])};  never toggles: {first_run_high}")
    if first_run_high and g67f5[0]:
        print("   ⚠ HIGH FROM FRAME 0 AND NEVER TOGGLING => most consistent with the 0xFF SENTINEL,")
        print("     i.e. gp-0x67f4 == 0 for the whole drive. NOT evidence of a latched gate.")
    if eng.sum() and (~eng).sum():
        print(f"   duty ENGAGED {100 * g67f5[eng].mean():6.2f}%   MANUAL {100 * g67f5[~eng].mean():6.2f}%")
    sus_hi = sus > 200
    if sus_hi.any() and (~sus_hi).any():
        print(f"   duty with SUSTAINED driver effort > 200 : {100 * g67f5[sus_hi].mean():6.2f}%")
        print(f"   duty hands-off (sustained <= 200)       : {100 * g67f5[~sus_hi].mean():6.2f}%")
        print("   => a large gap would support the 'driver-torque hands-on gate' reading. NO gap")
        print("      supports the code reading instead: FUN_00041eec reads NO torque cell -- it reads")
        print("      the voted vehicle speed gp-0x6a5e and four wheel-speed-like halfwords, and")
        print("      latches when their max deviation exceeds cal 0xC631E = 640 counts (~10 km/h) for")
        print("      cal 0xC64E7 = 10 consecutive ticks. That is a PLAUSIBILITY FAULT LATCH.")

    # ---- 8. bit4 -- THE DISPUTE THIS BUILD EXISTS TO SETTLE ------------------------------------------
    print(f"\n{'-' * 100}\n-- 8. *** bit4 = gp-0x67fe != 0 -- THE DISPUTED CELL *** --")
    print(f"   duty over the whole log : {100 * g67fe.mean():6.2f}%")
    if eng.sum() and (~eng).sum():
        de, dm = g67fe[eng].mean(), g67fe[~eng].mean()
        print(f"   duty ENGAGED {100 * de:6.2f}%   MANUAL {100 * dm:6.2f}%   "
              f"agreement with SCA {100 * (g67fe == eng).mean():.2f}%")
    print("   THE TWO READINGS, and what separates them:")
    print("     (a) subagent : the LKAS engage state machine's own state byte, ==0 means assist DOWN,")
    print("                    in {1,2} gates assist up. Sole live writer FUN_0003bd7c.")
    print("     (b) golden model : `assist_substate` -- BASE ASSIST, valid only in {1,2}. If so the")
    print("                    cell is non-zero whenever the car is running.")
    if g67fe.mean() > 0.99:
        print("   *** DUTY ~= 100% ==> READING (b). gp-0x67fe is the base-assist substate and is")
        print("       WORTHLESS as an LKAS gate. RETIRE candidate C. The golden model was right.")
    elif eng.sum() and (~eng).sum() and abs(g67fe[eng].mean() - g67fe[~eng].mean()) > 0.5:
        print("   *** DUTY TRACKS ENGAGEMENT ==> READING (a). gp-0x67fe is the best gate candidate")
        print("       available AND its displacement 0x9802 is EVEN, so hw1 is untouched by the")
        print("       repoint. Prefer it over gp-0x6806 if its toggle rate above is also clear of the")
        print(f"       kill band.   {repoint_edit(0x67fe)}")
    else:
        print("   *** NEITHER. The duty is neither ~100% nor engagement-tracking, so the cell is")
        print("       something else again. Do NOT gate on it until it is identified.")
    print("   ⚠ gp-0x67fe is LOCKSTEP-SHADOWED (pair gp-0x4c3a, mismatch -> FUN_0006b9fa). Read-only")
    print("     probing is unaffected; any future WRITE or cal edit on this cell is not.")

    # ---- 9. BY SPEED --------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- 9. BY SPEED --")
    print(f"   {'band':>12s} {'n':>7s} {'b6 duty':>9s} {'b6 t/s':>8s} {'b5 duty':>9s} {'b5 t/s':>8s} "
          f"{'b4 duty':>9s} {'b4 t/s':>8s}")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 25), (25, 99)):
        sel = (d["v"] >= lo) & (d["v"] < hi)
        if sel.sum() < 2:
            continue
        s6 = gate_stats(g6806, sel, fs, "")
        s5 = gate_stats(g67f5, sel, fs, "")
        s4 = gate_stats(g67fe, sel, fs, "")
        print(f"   {f'{lo}-{hi} m/s':>12s} {int(sel.sum()):7d} {100 * s6['duty']:8.2f}% "
              f"{s6['tps']:8.3f} {100 * s5['duty']:8.2f}% {s5['tps']:8.3f} "
              f"{100 * s4['duty']:8.2f}% {s4['tps']:8.3f}")

    # ---- THE VERDICT --------------------------------------------------------------------------------
    print(f"\n{'-' * 100}\n-- THE VERDICT (pre-committed in builds/v50_v79/build_v66_tva.py, before the drive) --")
    for bit, name, cell, _why in GATES:
        s = headline.get(bit)
        if s:
            print(f"   {name} : duty {100 * s['duty']:6.2f}%, {s['rise'] + s['fall']:5d} transitions "
                  f"in {s['span']:.1f}s = {s['tps']:.3f}/s")
    if verdict_ok:
        print("\n   *** V67'S GATE IS CLEARED ON EVERY CRITERION THIS DRIVE CAN TEST. ***")
        print("   THE REPOINT EDIT AT 0x3AA94, DERIVED not hand-written -- see repoint_edit():")
        print("     current: 84 7f c5 97  =  ld.bu -0x683c[gp],r15")
        for _bit, _nm, cell, _why in GATES:
            print("     " + repoint_edit(cell))
        print("   🛑 It is NOT always 'one byte at 0x3AA96'. For `ld.bu` the displacement's bit 0 lives")
        print("      in hw1 BIT 5 (opcode 0x3C vs 0x3D) and hw2's own LSB is the width selector. An ODD")
        print("      target needs hw1 changed too; writing only hw2 lands on the NEIGHBOURING cell, and")
        print("      gp-0x67f6 is a real cell with a real reader @0x4276C.")
        print("   ARM VALUE 0xC6446 -- and it depends on whether V62's `sar 0x9` is KEPT:")
        print("     KEEP sar 0x9 (the recommended shape): 512 -> 1188.  The arm divides by 512, and")
        print("       1188 reproduces STOCK AT THE POINT THE ARM IS TAKEN (7.2 km/h, 256 deg/s,")
        print("       where the LERP is 2377). Sizing it against the creep-and-ZERO-rate 3072 gives")
        print("       1536 and lands 1.29x HIGH in the very regime it exists to neutralise. Gate")
        print("       false =>")
        print("       LERP x2 (grind #1 stays fixed); gate true => stock (grind #2's regime removed).")
        print("       This requires the gate to be TRUE in grind #2's regime -- i.e. a HANDS-ON /")
        print("       driver-torque cell. With an LKAS-active cell the polarity is inverted and this")
        print("       value is WRONG.")
        print("     REVERT sar to 0xa: 512 -> 6144 (= 2x the creep default 3072), with the gate TRUE")
        print("       where the boost is WANTED. Flat across motor rate, so it does not track the")
        print("       LERP's own rolloff -- more aggressive than V62 at high steering rate.")
        print("   🛑 Pick the arm value AFTER the gate, never before: the two must agree on polarity.")
    else:
        print("\n   *** V67 IS NOT CLEARED. *** See the failing criterion above. Do not flash the")
        print("   repoint until it is explained.")
    print("\n   ⚠ OUTSTANDING, and NOT testable from this log -- neither absence is a pass:")
    print("      gp-0x683c, the CONTROL and V67's repoint site. Static evidence only (1 reader,")
    print("        0 writers, 0 extended-form hits, two decoders). Its bit was cut for cave budget:")
    print("        a rung costs 12 bytes and only 8 of the proven 68 were spare.")
    print("      gp-0x671d, the MASKING RISK. It OUTRANKS the LKAS arm in r24's priority chain, so if")
    print("        it latches non-zero V67's arm never applies. V64 measured it 0 across 14,980")
    print("        frames of ONE route. A null V67 must be read against that gap.")
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
