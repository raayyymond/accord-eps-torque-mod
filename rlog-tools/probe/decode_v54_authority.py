#!/usr/bin/env python3
"""probe/decode_v54_authority.py -- read V54's 5-bit gp-0x6966 AUTHORITY probe out of an rlog.

V54 packs  wire = min((gp-0x6966 >> 7) + 1, 31)  into CAN 330 (0x14A) byte4 bits 7:3, at 100 Hz.
Bits 2:0 are the stock STEER_SENSOR_STATUS_1/2/3 flags and are preserved by the cave.

    wire = (byte4 >> 3) & 0x1F          authority ~ (wire-1) * 128   (>= 3840 when wire == 31)

🛑 wire == 0 means THE CAVE DID NOT FIRE. The +1 bias exists precisely so this tool can say that.
Stock leaves those bits at zero, so without the bias a dead probe would decode as "authority 0..127,
lane at full bound" -- plausible, actionable, and wrong. Treat an all-zero drive as VOID, not as data.

What the wire values mean, against the stock 0xC6AF0 LERP that gates the FUN_0003a382 lane's output
bound (X = 0/3277/3604/19661/32768, Y = 32768/32768/0/0/0):

    == 0    -- no probe --      🛑 cave did not fire; the drive proves nothing
    1..25   authority <= 3199   Q15 gain 32768   lane at FULL bound
    == 26   3200..3327          straddles the 3277 knee
    27-28   3328..3583          inside the ramp
    == 29   3584..3711          straddles the 3604 knee
    >= 30   authority >= 3712   Q15 gain 0       lane MUTED

The decision this measures: if authority sits BELOW the knee during the vibration the lane is live and
V55 should mute it; if ABOVE, the lane is already clamped to zero and cannot be the driver; if it
CROSSES in step with the bursts, the crossing itself is the trigger and the ramp should be flattened.

Cross-tabulates against STEER_CONTROL_ACTIVE and the 21 Hz band power in STEER_TORQUE_SENSOR
(raw CAN 399 bytes 0-1) so the answer is a correlation, not just a histogram.

Usage:  python probe/decode_v54_authority.py RLOG [RLOG ...]
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

SHIFT, BIAS, MAXW = 7, 1, 31
KNEE_LO, KNEE_HI = 3277, 3604


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def auth_range(wire):
    """Authority range a wire value stands for. None for wire 0 (probe absent)."""
    if wire == 0:
        return None
    lo = (wire - BIAS) << SHIFT
    return (lo, None) if wire == MAXW else (lo, lo + (1 << SHIFT) - 1)


def regime(wire):
    """FULL / KNEE / MUTED / DEAD -- which side of the 0xC6AF0 knees this wire value proves."""
    r = auth_range(wire)
    if r is None:
        return "DEAD"
    lo, hi = r
    if hi is None:
        return "MUTED"
    if hi < KNEE_LO:
        return "FULL"
    if lo > KNEE_HI:
        return "MUTED"
    return "KNEE"


def meaning(wire):
    r = auth_range(wire)
    if r is None:
        return "🛑 CAVE DID NOT FIRE -- void"
    lo, hi = r
    if hi is None:
        return "lane MUTED (saturated, >= 3840)"
    if hi < KNEE_LO:
        return "lane at FULL bound"
    if lo <= KNEE_LO <= hi:
        return "<< straddles the 3277 knee"
    if lo <= KNEE_HI <= hi:
        return "<< straddles the 3604 knee"
    if lo > KNEE_HI:
        return "lane MUTED"
    return "inside the ramp"


def main(paths):
    buckets, sca_buckets = Counter(), {0: Counter(), 1: Counter()}
    series_t, series_b = [], []
    tq_t, tq_v = [], []
    n330 = n399 = 0

    for path in paths:
        for evt in read_messages(path):
            try:
                w = evt.which()
            except Exception:
                continue
            if w != "can":
                continue
            for c in evt.can:
                if c.src != 1:
                    continue
                d = bytes(c.dat)
                if c.address == 0x14A and len(d) >= 5:
                    n330 += 1
                    b = (d[4] >> 3) & 0x1F
                    buckets[b] += 1
                    series_t.append(evt.logMonoTime)
                    series_b.append(b)
                elif c.address == 0x18F and len(d) >= 5:
                    n399 += 1
                    tq_t.append(evt.logMonoTime)
                    tq_v.append(i16be(d, 0))

    if not n330:
        print("no CAN 330 frames on bus 1 -- wrong rlog?")
        return 1
    print(f"CAN 330 frames: {n330}   CAN 399 frames: {n399}")

    dead = buckets.get(0, 0)
    live = sum(v for b, v in buckets.items() if regime(b) == "FULL")
    muted = sum(v for b, v in buckets.items() if regime(b) == "MUTED")
    knee = sum(v for b, v in buckets.items() if regime(b) == "KNEE")
    print(f"\n{'wire':>5s} {'authority':>13s} {'frames':>8s} {'%':>6s}   meaning")
    for b in sorted(buckets):
        r = auth_range(b)
        rng = "-- none --" if r is None else (f">= {r[0]}" if r[1] is None else f"{r[0]}-{r[1]}")
        print(f"{b:5d} {rng:>13s} {buckets[b]:8d} {100 * buckets[b] / n330:5.1f}%   {meaning(b)}")

    if dead:
        print(f"\n  🛑 {dead} frames ({100*dead/n330:.1f}%) carry wire == 0 -- the probe did not fire in")
        print(f"     them. A live V54 cave can never emit 0. Do NOT read this as low authority.")
        if dead == n330:
            print(f"     ENTIRE DRIVE IS VOID. Either this is not a V54 image, or the cave never ran.")
            return 1

    print(f"\n  FULL-bound frames: {live} ({100*live/n330:.1f}%)   "
          f"MUTED frames: {muted} ({100*muted/n330:.1f}%)   "
          f"in/at the knee: {knee} ({100*knee/n330:.1f}%)")

    if live and muted:
        print("  ** authority CROSSES the knee during this drive -- the strongest possible outcome.")
        print("     Correlate the crossings against the 21 Hz bursts before choosing a 0xC6AF0 edit.")
    elif live:
        print("  => lane ran at FULL bound throughout: it CAN be the driver. V55 candidate = mute (Y->0).")
    elif muted:
        print("  => lane was CLAMPED TO ZERO throughout: it cannot be injecting. Hypothesis falsified;")
        print("     the keep-live reading (4x muted a damper) becomes the candidate.")

    # 21 Hz band power in the torque sensor, split by bucket regime.
    if len(tq_v) > 512:
        x = np.asarray(tq_v, float)
        x -= x.mean()
        nfft, hop = 128, 64
        fs = 100.0
        k = int(round(21.09 / (fs / nfft)))
        win = np.hanning(nfft)
        tb = np.asarray(series_t, float)
        bb = np.asarray(series_b, float)
        rows = {"FULL": [], "KNEE": [], "MUTED": []}
        for s in range(0, len(x) - nfft, hop):
            seg = x[s:s + nfft] * win
            p = abs(np.fft.rfft(seg)[k]) ** 2
            t0, t1 = tq_t[s], tq_t[s + nfft - 1]
            m = (tb >= t0) & (tb <= t1)
            if not m.any():
                continue
            key = regime(int(round(bb[m].mean())))
            if key == "DEAD":
                continue
            rows[key].append(p)
        print(f"\n  21.09 Hz power in STEER_TORQUE_SENSOR, split by authority regime:")
        for key in ("FULL", "KNEE", "MUTED"):
            v = rows[key]
            if v:
                print(f"    {key:6s} K={len(v):4d}  median P(21.09) = {np.median(v):.3e}")
            else:
                print(f"    {key:6s} K=   0  (empty cell)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
