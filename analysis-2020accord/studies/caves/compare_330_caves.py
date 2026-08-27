#!/usr/bin/env python3
r"""
studies/caves/compare_330_caves.py -- is the V49P telemetry cave ACTIVE in the manual rlog?

Discriminator: compare CAN 330 byte4 / byte7 across three drives:
  * b9  (807a...b9)  = V38 baseline, NO telemetry cave  -> STOCK 330 content
  * 77  (807a...77)  = V31P/V31P-V2 gate-flag cave ACTIVE -> byte4[7:3] carries live flags
  * manual (aa5b3e0c01) = the drive the operator says was V49P
If stock byte4[7:3] VARIES and manual is pinned, the cave is overwriting it (active).
Also reports LKAS-engaged presence (399 STEER_CONTROL_ACTIVE) so we know it was a real assisted drive.
"""
import sys, glob, os
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

DRIVES = {
    "b9_V38_nocave":  sorted(glob.glob(str(HERE / "rlogs" / "807a3c21c9f405e8_000000b9--*--*--rlog.zst")))[:3],
    "77_V31P_cave":   sorted(glob.glob(str(HERE / "rlogs" / "807a3c21c9f405e8_00000077--*--*--rlog.zst")))[:3],
    "manual_V49P":    sorted(glob.glob(str(HERE / "rlogs" / "manual" / "*" / "*" / "rlog.zst")))[:4],
}


def scan(paths):
    b4 = Counter(); b7 = Counter()
    b4_hi = Counter(); b7_hi = Counter()      # byte4[7:3], byte7[7:6]
    n330 = Counter()                          # per bus
    active = Counter(); n399 = 0
    for p in paths:
        try:
            for evt in read_messages(p):
                try:
                    if evt.which() != "can":
                        continue
                except Exception:
                    continue
                for fr in evt.can:
                    if fr.address == 330 and len(fr.dat) == 8:
                        d = bytes(fr.dat)
                        n330[fr.src] += 1
                        if fr.src == 1:
                            b4[d[4]] += 1; b7[d[7]] += 1
                            b4_hi[(d[4] >> 3) & 0x1F] += 1
                            b7_hi[(d[7] >> 6) & 0x03] += 1
                    elif fr.address == 399 and fr.src == 1 and len(fr.dat) == 7:
                        d = bytes(fr.dat)
                        n399 += 1
                        active[(d[4] >> 3) & 1] += 1
        except Exception as e:
            print(f"    !! {os.path.basename(p)}: {e}")
    return b4, b7, b4_hi, b7_hi, n330, active, n399


for name, paths in DRIVES.items():
    print("\n" + "=" * 74)
    print(f"{name}  ({len(paths)} segments)")
    print("=" * 74)
    if not paths:
        print("  (no segments found)")
        continue
    b4, b7, b4_hi, b7_hi, n330, active, n399 = scan(paths)
    print(f"  330 frames per bus: {dict(n330)}")
    print(f"  byte4 full (top 6):   { {f'0x{k:02X}': v for k, v in b4.most_common(6)} }")
    print(f"  byte4[7:3] hist:      { {f'0b{k:05b}': v for k, v in sorted(b4_hi.items())} }")
    print(f"  byte7[7:6] hist:      { {f'0b{k:02b}': v for k, v in sorted(b7_hi.items())} }")
    print(f"  byte7 full (top 6):   { {f'0x{k:02X}': v for k, v in b7.most_common(6)} }")
    nvar_b4hi = len(b4_hi)
    print(f"  -> byte4[7:3] takes {nvar_b4hi} distinct value(s) "
          f"({'VARIES = stock signal' if nvar_b4hi > 1 else 'CONSTANT = pinned/reserved'})")
    print(f"  399 frames: {n399}, LKAS active(bit3) hist: {dict(active)}")
