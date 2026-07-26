#!/usr/bin/env python3
r"""
decode_v49p_polarity.py -- read the V49P read-only polarity telemetry out of the manual rlog.

V49P (build_v49p_tva.py) flashed V38 + a READ-ONLY cave that packs two RAM bytes into CAN 330's
genuinely-spare bits (V31P technique):
    CAN 330 (0x14A) byte4 bits 7:3 = gp-0x6752 & 0x1F   (polarity1; +1 -> 0b00001, 0xFF -> 0b11111)
    CAN 330 (0x14A) byte7 bits 7:6 = gp-0x6762 & 0x03   (polarity2; +1 -> 0b01,    0xFF -> 0b11)

gp-0x6752 (abs 0xFEDF18AE) is the V49 flash GATE: +1 => the StageC sign-flip is DAMPING (fix);
-1 => it is ANTI-DAMPING (a V48B-class brick). This script reads it off the car so the gate resolves.

Manual export layout: rlogs/manual/<dongle>/00000000--<route>--<seg>/rlog.zst
"""
import sys, glob, os
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

GLOB = str(HERE / "rlogs" / "manual" / "*" / "*" / "rlog.zst")


def honda_checksum(address, d):
    s = 0; a = address
    while a:
        s += a & 0xF; a >>= 4
    for i, b in enumerate(d):
        if i == len(d) - 1:
            b >>= 4
        s += (b & 0xF) + (b >> 4)
    return (8 - s) & 0xF


def main():
    paths = sorted(glob.glob(GLOB))
    print(f"[load] {len(paths)} manual rlog segments")
    for p in paths:
        print("   ", os.path.relpath(p, HERE))

    # per-bus tallies of the raw spare-bit fields
    p1_by_bus = {}     # bus -> Counter of byte4[7:3]  (gp-0x6752 low-5)
    p2_by_bus = {}     # bus -> Counter of byte7[7:6]  (gp-0x6762 low-2)
    b4_full = {}       # bus -> Counter of full byte4
    b7_full = {}       # bus -> Counter of full byte7
    n330 = Counter()   # bus -> frame count
    chk_ok = Counter(); chk_bad = Counter()
    dlc = Counter()

    for path in paths:
        try:
            for evt in read_messages(path):
                try:
                    if evt.which() != "can":
                        continue
                except Exception:
                    continue
                for fr in evt.can:
                    if fr.address != 330:
                        continue
                    d = bytes(fr.dat)
                    bus = fr.src
                    dlc[len(d)] += 1
                    if len(d) != 8:
                        continue
                    n330[bus] += 1
                    # 330 uses byte6 lo-nibble checksum per Honda (counter byte6 hi). Validate.
                    if honda_checksum(330, d) == (d[6] & 0xF):
                        chk_ok[bus] += 1
                    else:
                        chk_bad[bus] += 1
                    p1 = (d[4] >> 3) & 0x1F
                    p2 = (d[7] >> 6) & 0x03
                    p1_by_bus.setdefault(bus, Counter())[p1] += 1
                    p2_by_bus.setdefault(bus, Counter())[p2] += 1
                    b4_full.setdefault(bus, Counter())[d[4]] += 1
                    b7_full.setdefault(bus, Counter())[d[7]] += 1
        except Exception as e:
            print(f"  !! {os.path.relpath(path, HERE)}: {e}")

    print(f"\n[dlc] CAN-330 frame length histogram: {dict(dlc)}")
    print(f"[330] frames per bus: {dict(n330)}")
    print(f"[330] checksum ok per bus:  {dict(chk_ok)}")
    print(f"[330] checksum bad per bus: {dict(chk_bad)}")

    def interp1(p1):
        if p1 == 0b00001:
            return "+1  (gp-0x6752 = +1  -> V49 StageC-flip is DAMPING = intended FIX)"
        if p1 == 0b11111:
            return "-1  (gp-0x6752 = 0xFF/-1 -> V49 StageC-flip is ANTI-DAMPING = BRICK)"
        return f"UNEXPECTED low-5 = 0b{p1:05b} ({p1})"

    def interp2(p2):
        if p2 == 0b01:
            return "+1  (gp-0x6762 low-2 = 0b01)"
        if p2 == 0b11:
            return "-1  (gp-0x6762 low-2 = 0b11 = 0xFF)"
        return f"UNEXPECTED low-2 = 0b{p2:02b} ({p2})"

    print("\n" + "=" * 78)
    print("POLARITY DECODE (the V49 flash gate)")
    print("=" * 78)
    for bus in sorted(n330):
        print(f"\n--- bus {bus}: {n330[bus]} CAN-330 frames ---")
        print(f"  byte4[7:3] gp-0x6752 low-5 histogram: "
              f"{ {f'0b{k:05b}': v for k, v in sorted(p1_by_bus[bus].items())} }")
        top1, c1 = p1_by_bus[bus].most_common(1)[0]
        print(f"    dominant = 0b{top1:05b} ({100*c1/n330[bus]:.1f}%) -> gp-0x6752 = {interp1(top1)}")
        print(f"  byte7[7:6] gp-0x6762 low-2 histogram: "
              f"{ {f'0b{k:02b}': v for k, v in sorted(p2_by_bus[bus].items())} }")
        top2, c2 = p2_by_bus[bus].most_common(1)[0]
        print(f"    dominant = 0b{top2:02b} ({100*c2/n330[bus]:.1f}%) -> gp-0x6762 = {interp2(top2)}")
        print(f"  (raw full byte4 top: { {f'0x{k:02X}': v for k, v in b4_full[bus].most_common(4)} })")
        print(f"  (raw full byte7 top: { {f'0x{k:02X}': v for k, v in b7_full[bus].most_common(4)} })")


if __name__ == "__main__":
    main()
