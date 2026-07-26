#!/usr/bin/env python3
r"""
Follow-up consistency check on rlog 5's CAN 330 decode.

The V50P pack writes gp-0x1500's low 5 bits into byte4[7:3] AND its low 2 bits into byte7[7:6],
preserving byte4[2:0] (stock, should stay constant == STOCK drive's byte4 low 3 bits) and
byte7[5:0] (stock counter/checksum).

Checks:
  1. byte4 & 0x07 histogram in rlog5 -- should be a constant matching stock's byte4 low 3 bits (0x07),
     proving the packer is ORing into the byte rather than corrupting/replacing it.
  2. Per-frame consistency: (byte4[7:3] & 0x3) == byte7[7:6] -- both fields derive from the SAME low
     bits of gp-0x1500, so if this holds at high rate it is strong evidence of a real single source
     value being packed twice (not noise / misdecoding), i.e. the probe cave is genuinely live.
  3. A short time-ordered sample of the packed 5-bit value to eyeball whether it looks like a
     structured signal (ramps/oscillates) vs pure noise.
"""
import sys, glob, os
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOG5_GLOB = str(HERE / "rlogs" / "75604b0a432fdc89_00000005--2ae04b9ba2--*--rlog.zst")


def main():
    paths = sorted(glob.glob(RLOG5_GLOB))
    low3 = Counter()
    match = 0
    mismatch = 0
    mismatch_examples = []
    samples = []  # (t, p1_5bit)
    n = 0

    for path in paths:
        t0 = None
        for evt in read_messages(path):
            try:
                if evt.which() != "can":
                    continue
            except Exception:
                continue
            for fr in evt.can:
                if fr.address != 330 or fr.src != 1:
                    continue
                d = bytes(fr.dat)
                if len(d) != 8:
                    continue
                n += 1
                low3[d[4] & 0x07] += 1
                p1 = (d[4] >> 3) & 0x1F
                p2 = (d[7] >> 6) & 0x03
                if (p1 & 0x3) == p2:
                    match += 1
                else:
                    mismatch += 1
                    if len(mismatch_examples) < 10:
                        mismatch_examples.append((d[4], d[7], p1, p2))
                if len(samples) < 60:
                    samples.append(p1)

    print(f"total bus-1 330 frames examined: {n}")
    print(f"byte4 & 0x07 (kept-stock low 3 bits) histogram: {dict(low3)}")
    print(f"low-2-bit consistency  (byte4[7:3]&0x3 == byte7[7:6]): match={match} mismatch={mismatch} "
          f"({100*match/(match+mismatch):.2f}% match)")
    if mismatch_examples:
        print("mismatch examples (byte4,byte7,p1_5bit,p2_2bit):")
        for ex in mismatch_examples:
            print("   ", ex)
    print(f"\nfirst 60 packed 5-bit values (time order, first segment): {samples}")


if __name__ == "__main__":
    main()
