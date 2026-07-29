#!/usr/bin/env python3
"""decode_v57_deadband.py -- read V57's deadband-gate probe out of an rlog.

V57 packs FIVE bits into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                       LIVENESS  (constant; 0 => the cave did not fire)
    bit 6 = (gp-0x6806 == 0)        the deadband/sign-relay gate is ENABLED
    bit 5 = (gp-0x69b0 != 0)        the LKAS forward ramp gain is LIVE
    bit 4 = (gp-0x6b30 == 0)        the gate's output is EXACTLY ZERO
    bit 3 = (gp-0x6b30 <  0)        the gate's output is NEGATIVE
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

*** field = (byte4 >> 3) & 0x1F.  field == 0 means THE CAVE DID NOT FIRE -- a VOID reading, not
"everything false". Bit 7 is hard-wired 1 precisely so this tool can say that. V53's drive read
byte4 == 0x07 in 5,994/5,994 frames, i.e. stock leaves these bits clear.

THE QUESTION THIS ANSWERS
-------------------------------------------------------------------------------------------------------
The deadband + sign relay in FUN_00028ea6 (0x2a1ae-0x2a206) was eliminated on 2026-07-29 by measuring
STEER_CONTROL_ACTIVE (CAN 0x18F byte4 bit3), which the packer sources from gp-0x6806:

    0x55c76 ld.bu -0x6806,gp,r15 ; 0x55c7e andi 0x1,r15,r15 ; 0x55c82 shl 0x3,r15

*** But `andi 0x1` transmits PARITY, and the gate tests EXACT EQUALITY (`cmp r0,r12 ; bne` at
0x2a1ba/0x2a1bc). Four of the flag's eight live writers store a REGISTER, not a literal, so a value of
2 reads as bit0 = 0 while the gate is DISABLED -- and a 0<->2 toggle at 22 Hz would be invisible.

  bit 6 is the EXACT test and closes that hole.
  bits 4/3 give a 3-state view of the output {negative, zero, positive}. A chattering relay visits
    zero between sign flips, so bit4's spectrum carries a 20-25 Hz line if the mechanism is real.
  bit 5 separates "zero because the ramp gain is zero" from "zero because the gate fired".

READ IT AS:
  bit6 ~never set on engaged+hands-off frames        -> gate inert; the thread is CLOSED by
                                                        measurement, not by a parity argument.
  bit6 set in a meaningful fraction, or bit4 showing
  a 20-25 Hz line                                    -> the elimination was premature.

Prior expectation, recorded so a null is not re-litigated: NEGATIVE is expected.

⚠ 100 Hz sampling of a ~22 Hz phenomenon is below Nyquist but close to it; a 22 Hz line is
indistinguishable from 78 Hz aliased. Same limitation every probe in this kit has had.

Usage:  python decode_v57_deadband.py RLOG [RLOG ...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from rlog_parse import read_messages  # noqa: E402

FS = 100.0
BIT_LIVE, BIT_GATE, BIT_RAMP, BIT_ZERO, BIT_SIGN = 0x80, 0x40, 0x20, 0x10, 0x08


def collect(paths):
    b4, tq, t = [], [], []
    vego, engaged, tv = [], [], []
    last_tq = np.nan
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            if w == "can":
                for m in evt.can:
                    if m.src != 1:
                        continue
                    d = bytes(m.dat)
                    if m.address == 0x18F and len(d) >= 2:
                        v = (d[0] << 8) | d[1]
                        last_tq = (v - 0x10000 if v & 0x8000 else v) * -1.0
                    elif m.address == 0x14A and len(d) >= 5:
                        b4.append(d[4])
                        tq.append(last_tq)
                        t.append(evt.logMonoTime * 1e-9)
            elif w == "carState":
                vego.append(evt.carState.vEgo)
                engaged.append(bool(evt.carState.cruiseState.enabled))
                tv.append(evt.logMonoTime * 1e-9)
    d = dict(b4=np.array(b4, dtype=int), tq=np.array(tq), t=np.array(t))
    if tv:
        d["v"] = np.interp(d["t"], np.array(tv), np.array(vego))
        d["eng"] = np.interp(d["t"], np.array(tv), np.array(engaged, float)) > 0.5
    else:
        d["v"] = np.full_like(d["t"], np.nan)
        d["eng"] = np.zeros_like(d["t"], bool)
    return d


def spectrum(x, nfft=256):
    """Mean periodogram over NON-overlapping Hann segments. Returns (freqs, power, K)."""
    x = np.asarray(x, float)
    if len(x) < nfft:
        return None, None, 0
    f = np.fft.rfftfreq(nfft, 1 / FS)
    win = np.hanning(nfft)
    acc, k = np.zeros(len(f)), 0
    for i in range(0, len(x) - nfft + 1, nfft):
        seg = x[i:i + nfft]
        acc += np.abs(np.fft.rfft((seg - seg.mean()) * win)) ** 2
        k += 1
    return (f, acc / k, k) if k else (None, None, 0)


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    field = (d["b4"] >> 3) & 0x1F
    print(f"\n{'=' * 86}\n{tag}   {n} frames  {d['t'][-1] - d['t'][0]:.1f}s")

    void = field == 0
    print(f"\n-- LIVENESS --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {void.sum()} / {n}  ({100 * void.mean():.2f}%)")
    print(f"   bit7 set                       : {(d['b4'] & BIT_LIVE != 0).sum()} / {n}")
    if void.all():
        print("\n   *** THE CAVE NEVER FIRED. Every reading below is VOID. Stop here.")
        return
    if void.any():
        print("   *** partial void -- treat mixed segments with suspicion")

    print(f"\n   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"]).most_common(8)))

    gate = (d["b4"] & BIT_GATE) != 0
    ramp = (d["b4"] & BIT_RAMP) != 0
    zero = (d["b4"] & BIT_ZERO) != 0
    neg = (d["b4"] & BIT_SIGN) != 0

    conds = [
        ("ALL frames", np.ones(n, bool)),
        ("engaged", d["eng"]),
        ("engaged + hands-off (|tq|<=200)", d["eng"] & (np.abs(d["tq"]) <= 200)),
        ("engaged + driver torque >2240", d["eng"] & (np.abs(d["tq"]) > 2240)),
        ("disengaged", ~d["eng"]),
    ]
    print(f"\n-- THE FIVE BITS, by condition --")
    print(f"   {'condition':34s} {'n':>6s} {'gate ON':>9s} {'ramp':>8s} {'out==0':>8s} {'out<0':>8s}")
    for name, sel in conds:
        if sel.sum() == 0:
            print(f"   {name:34s} {0:6d}   (none)")
            continue
        print(f"   {name:34s} {sel.sum():6d} {100 * gate[sel].mean():8.2f}% "
              f"{100 * ramp[sel].mean():7.2f}% {100 * zero[sel].mean():7.2f}% "
              f"{100 * neg[sel].mean():7.2f}%")

    print(f"\n-- 🛑 THE DECISIVE NUMBER --")
    sel = d["eng"] & (np.abs(d["tq"]) <= 200)
    if sel.sum() < 50:
        print("   too few engaged+hands-off frames to judge")
    else:
        pct = 100 * gate[sel].mean()
        tr = int((np.diff(gate[sel].astype(int)) != 0).sum())
        print(f"   gate ENABLED (gp-0x6806 == 0) on engaged+hands-off: {pct:.2f}%  "
              f"({gate[sel].sum()}/{sel.sum()}), {tr} transitions")
        if pct < 1.0:
            print("   => INERT. The deadband/sign relay is bypassed where the grinding lives.")
            print("      The 2026-07-29 elimination STANDS, now on exact equality, not parity.")
        else:
            print("   => NOT INERT. The elimination was premature; the deadband returns to scope.")

    # the relay signature: does the output visit zero at 20-25 Hz?
    print(f"\n-- SPECTRUM of (output == 0), engaged + hands-off --")
    if sel.sum() >= 256:
        f, P, K = spectrum(zero[sel].astype(float))
        if K:
            band = (f >= 15) & (f <= 27)
            ref = (f >= 6) & (f <= 40) & ~band
            j = int(np.argmax(np.where(band, P, -np.inf)))
            prom = P[j] / np.median(P[ref])
            print(f"   K={K} segments, peak in 15-27 Hz at {f[j]:.2f} Hz, "
                  f"prominence over the 6-40 Hz floor = {prom:.2f}x")
            print("   (a relay chattering at the mode frequency shows a sharp, high-prominence line;")
            print("    prominence ~1-3 with a wandering peak is noise, not a mechanism)")
    else:
        print("   too few contiguous frames")


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
