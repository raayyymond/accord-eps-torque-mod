#!/usr/bin/env python3
"""probe/decode_v55_motorcmd.py -- read V55's dual probe out of an rlog.

V55 packs TWO signals into CAN 330 (0x14A) byte4 at 100 Hz:

    bit  7    = (damper variant INDEX >= 10)                    [static]
    bits 6:3  = clamp((gp-0x6b98 >> 9) + 8, 1, 15)              [motor command, 512 counts/level]
    bits 2:0  = stock STEER_SENSOR_STATUS_1/2/3, preserved

    field   = (byte4 >> 3) & 0x0F
    variant = (byte4 >> 7) & 1

*** field == 0 means THE CAVE DID NOT FIRE. The clamp to 1..15 exists precisely so this tool can say
that. Stock leaves those bits at 0 (V53's drive: byte4 == 0x07 in 5,994/5,994 frames), so an all-zero
field is VOID, not "command pinned low".

THE QUESTION THIS ANSWERS
-------------------------------------------------------------------------------------------------------
gp-0x6b98 is the final merged command -- the only path to FOC. Is the ~20 Hz mode present in it?

  present -> the oscillation is COMMANDED; the command path stays in scope.
  absent  -> every command-path lever this kit has flashed (V39/V41/V42ch2/V43/V45/V46/V48A/V52C, all
             null) was doomed by construction; the search moves to the plant.

A null BOUNDS the command's 20 Hz content to roughly <512 counts (one level) against the sensor's
~550 counts rms. It does not prove zero. And a 100 Hz probe cannot separate 20 Hz from 80 Hz -- it
inherits CAN 399's aliasing ambiguity.

Usage:  python probe/decode_v55_motorcmd.py RLOG [RLOG ...]
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

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0] if "\\" in __file__ else ".")
from rlog_parse import read_messages  # noqa: E402

SHIFT, OFFSET, LO, HI = 9, 8, 1, 15
FS = 100.0


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def cmd_range(field):
    """The gp-0x6b98 range a field value stands for. None for field 0 (probe absent)."""
    if field == 0:
        return None
    if field <= LO:
        return (None, (LO - OFFSET + 1) * (1 << SHIFT) - 1)
    if field >= HI:
        return ((HI - OFFSET) * (1 << SHIFT), None)
    lo = (field - OFFSET) * (1 << SHIFT)
    return (lo, lo + (1 << SHIFT) - 1)


def band_power(x, f0, nfft=256, hop=64):
    """Mean power in a narrow band around f0, over Hanning-windowed segments.

    *** hop = nfft//4 is 75% OVERLAP, so the returned `n` OVERSTATES the true degrees of freedom by
    roughly 4x. Coherence-significance and error bars must be computed from n/4, not n. Route 1c's
    engaged data is 2 contiguous runs = 23.6 s => K = 3 non-overlapping 512-pt segments (significance
    0.776), NOT the "9 independent segments / significance 0.312" the 2026-07-28 record claimed.
    """
    if len(x) < nfft:
        return None, 0
    freqs = np.fft.rfftfreq(nfft, 1 / FS)
    band = (freqs > f0 - 1.5) & (freqs < f0 + 1.5)
    win = np.hanning(nfft)
    acc, n = 0.0, 0
    for s in range(0, len(x) - nfft, hop):
        seg = x[s:s + nfft]
        P = np.abs(np.fft.rfft((seg - seg.mean()) * win)) ** 2
        acc += P[band].sum()
        n += 1
    return (acc / max(n, 1)), n


def main(paths):
    fields, variants = [], Counter()
    t330, f330 = [], []
    t399, tq399 = [], []
    tcc, lat = [], []
    n330 = 0

    for path in paths:
        for evt in read_messages(path):
            try:
                w = evt.which()
            except Exception:
                continue
            if w == "carControl":
                tcc.append(evt.logMonoTime)
                lat.append(1.0 if evt.carControl.latActive else 0.0)
                continue
            if w != "can":
                continue
            for c in evt.can:
                if c.src != 1:
                    continue
                d = bytes(c.dat)
                if c.address == 0x14A and len(d) >= 5:
                    n330 += 1
                    f = (d[4] >> 3) & 0x0F
                    fields.append(f)
                    variants[(d[4] >> 7) & 1] += 1
                    t330.append(evt.logMonoTime)
                    f330.append(f)
                elif c.address == 0x18F and len(d) >= 5:
                    t399.append(evt.logMonoTime)
                    tq399.append(i16be(d, 0))

    if not n330:
        print("no CAN 330 frames on bus 1 -- wrong rlog?")
        return 1
    print(f"CAN 330 frames: {n330}   CAN 399 frames: {len(t399)}")

    # ---- liveness FIRST, and nothing is interpreted until it passes ----
    #
    # Two independent ways this channel can lie, both learned the hard way:
    #
    #  (1) field == 0 everywhere -> the cave never ran. The clamp to 1..15 reserves 0 for exactly this.
    #
    #  (2) *** field CONSTANT but non-zero -> almost certainly a V54 image, NOT V55. V54 packs
    #      wire = min((gp-0x6966>>7)+1, 31) into bits 7:3 of this same byte, and on V54 the authority
    #      is pinned, so byte4 == 0x0F for the whole drive. Decoded as V55 that reads as
    #      field == 1, bit7 == 0 -- a perfectly plausible "command pinned low, variant index < 10",
    #      which is confident, actionable and entirely fabricated. The two builds share bits, so the
    #      ONLY thing that separates them is that a live V55 field MUST MOVE: gp-0x6b98 is the motor
    #      command on a driving car. A constant field over thousands of frames is not a measurement.
    fc = Counter(fields)
    dead = fc.get(0, 0)
    if dead == n330:
        print(f"\n  *** ALL {n330} frames carry field == 0 -- THE CAVE DID NOT FIRE.")
        print(f"      A live V55 cave can never emit 0. This drive is VOID, not 'low command'.")
        print(f"      Either this is not a V55 image, or the cave never ran.")
        return 1
    if dead:
        print(f"\n  *** {dead} frames ({100*dead/n330:.1f}%) carry field == 0 -- probe not live in them.")

    distinct = len(set(fields))
    if distinct == 1:
        only = fields[0]
        print(f"\n  *** byte4 is CONSTANT across all {n330} frames (field == {only}, "
              f"bit7 == {(1 if variants.get(1) else 0)}).")
        print(f"      A live V55 probe samples gp-0x6b98, the MOTOR COMMAND -- it cannot be constant")
        print(f"      on a driving car. This is almost certainly a **V54** image: V54 writes")
        print(f"      wire=1 into bits 7:3 of this same byte, giving byte4 == 0x0F, which decodes")
        print(f"      here as a plausible-looking field==1 / bit7==0.")
        print(f"      *** REFUSING TO INTERPRET. Confirm the flashed image SHA before re-running.")
        return 1
    if distinct == 2:
        print(f"\n  ** only {distinct} distinct field values seen -- unusually static for a motor")
        print(f"     command. Treat the spectral result below with suspicion and check the image SHA.")

    # ---- signal 2: the damper variant bit (static) ----
    print(f"\n=== DAMPER VARIANT BIT (bit 7) ===")
    for v, n in sorted(variants.items()):
        print(f"  bit7 = {v}: {n} frames ({100*n/n330:.1f}%)")
    if len(variants) > 1:
        print("  ** bit 7 is NOT constant -- unexpected; the variant index should not change in a drive.")
    else:
        v = next(iter(variants))
        if v:
            print("  => INDEX >= 10. V44/V47 edited the LIVE tables (0xD27BC/0xD27F8).")
            print("     The missing-damping hypothesis is GENUINELY FALSIFIED. Do not retest it.")
        else:
            print("  => INDEX < 10. V44/V47 edited an INERT table -- their nulls are UNINFORMATIVE.")
            print("     The damping hypothesis has NEVER been tested on this car.")
            print("     Retest against index 4: Factor C 0xD07BC, Factor E 0xD07F8.")

    # ---- signal 1: the motor command ----
    print(f"\n=== MOTOR COMMAND gp-0x6b98 (bits 6:3) ===")
    print(f"{'field':>5s} {'gp-0x6b98 range':>18s} {'frames':>8s} {'%':>6s}")
    for f in sorted(fc):
        r = cmd_range(f)
        rng = ("-- none --" if r is None else
               f"<= {r[1]}" if r[0] is None else
               f">= {r[0]}" if r[1] is None else f"{r[0]}..{r[1]}")
        print(f"{f:5d} {rng:>18s} {fc[f]:8d} {100*fc[f]/n330:5.1f}%")

    live = [f for f in fields if f > 0]
    if live:
        rail_lo = sum(1 for f in live if f == LO) / len(live)
        rail_hi = sum(1 for f in live if f == HI) / len(live)
        print(f"  saturating low {100*rail_lo:.1f}%   saturating high {100*rail_hi:.1f}%   "
              f"interior {100*(1-rail_lo-rail_hi):.1f}%")
        if rail_lo + rail_hi > 0.5:
            print("  ** over half the drive sits at a field endpoint -- the shift is too small;")
            print("     rebuild with CMD_SHIFT=10 before drawing spectral conclusions.")

        # *** 2026-07-29: the railing guard above was the WRONG WAY ROUND. On the road drive (route 24)
        # rails were 0.10% low / 0.00% high and field 15 never occurred in 943 s -- the probe does not
        # clip, it UNDER-RANGES. 99.2% of engaged+hands-off frames sat in TWO ADJACENT levels, i.e.
        # gp-0x6b98 lives inside +-512 while one LSB IS 512 counts => an effectively ~1.5-bit channel.
        # So the check below is the one that actually fires, and CMD_SHIFT must go DOWN, not up.
        counts = sorted(fc.items(), key=lambda kv: -kv[1])
        top2 = sum(n for _, n in counts[:2])
        if top2 / n330 > 0.80:
            lv = ", ".join(f"{f}:{100*n/n330:.1f}%" for f, n in counts[:3])
            print(f"\n  *** UNDER-RANGE: {100*top2/n330:.1f}% of frames sit in the top TWO levels "
                  f"({lv})")
            print(f"      One level is {1 << SHIFT} counts, so the command is not spanning the field.")
            print(f"      => AMPLITUDE figures from this field are NOT defensible; presence and")
            print(f"         frequency still are (a comparator preserves zero-crossing timing).")
            print(f"      => Rebuild with CMD_SHIFT=7 (128 counts/level, OFFSET=8). *** If you drop to")
            print(f"         CMD_SHIFT=6 you MUST also move OFFSET to 9: (x>>6)+8 == 0 for")
            print(f"         x in [-512,-449], which collides with the 'cave did not fire' sentinel.")

    # ---- THE PARTITION: is ~20 Hz in the command? ----
    x = np.asarray(f330, float)
    t = np.asarray(t330, float)
    if len(x) < 512:
        print("\n  too few 330 frames for a spectrum")
        return 0

    print(f"\n=== IS ~20 Hz IN THE MOTOR COMMAND? ===")
    lat_w = (np.interp(t, np.asarray(tcc, float), np.asarray(lat, float)) > 0.5
             if tcc else np.ones(len(t), bool))

    for label, mask in (("engaged", lat_w), ("NOT engaged", ~lat_w)):
        seg = x[mask]
        if len(seg) < 256:
            print(f"  {label:12s}: too few frames ({len(seg)})")
            continue
        p20, k20 = band_power(seg, 20.1)
        p5, _ = band_power(seg, 5.0)
        p40, _ = band_power(seg, 40.0)
        print(f"  {label:12s}: n={len(seg):5d} K={k20:3d}  "
              f"P(~20Hz)={p20:10.3e}   P(~5Hz)={p5:10.3e}   P(~40Hz)={p40:10.3e}")

    if tcc and lat_w.sum() > 256 and (~lat_w).sum() > 256:
        pe, _ = band_power(x[lat_w], 20.1)
        pd, _ = band_power(x[~lat_w], 20.1)
        ratio = pe / max(pd, 1e-30)
        print(f"\n  engaged / disengaged 20 Hz ratio in the COMMAND = {ratio:.1f}x")
        print(f"  (the SENSOR showed 771x on route 1b -- compare directly)")
        if ratio > 20:
            print("  => the ~20 Hz IS in the final motor command. The oscillation is COMMANDED;")
            print("     the command path stays in scope and the 0xC6AF0 mute becomes motivated.")
        else:
            print("  => the ~20 Hz is NOT meaningfully in the final motor command.")
            print("     Every command-path lever flashed so far was doomed by construction.")
            print("     ** Bounded, not proven zero: one level is 512 counts vs the sensor's ~550 rms.")

    # Cross-check against the sensor in the same rlog, so the comparison is like-for-like.
    if len(tq399) > 512:
        ps, _ = band_power(np.asarray(tq399, float), 20.1)
        print(f"\n  same-rlog SENSOR (raw 399) P(~20Hz) = {ps:.3e}   [reference scale]")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
