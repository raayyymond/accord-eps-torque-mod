#!/usr/bin/env python3
r"""
studies/probes/decode_v50p_gate1.py -- read V50P (gp-0x1500 -> CAN 330 spare bits) telemetry out of rlog 5,
and compare against a STOCK (non-probe) manual drive to determine whether the probe was
provably live, per the packing in builds/v50_v79/build_v50probe_tva.py:

    CAN 330 (0x14A) byte4 bits 7:3 = gp-0x1500 & 0x1F   (low 5 bits)
    CAN 330 (0x14A) byte7 bits 7:6 = gp-0x1500 & 0x03   (low 2 bits)

Mirrors studies/probes/decode_v49p_polarity.py's parsing/checksum logic but globs TWO drives:
  - RLOG5_GLOB: the new V50P on-car drive (flat files, not nested in a route dir)
  - STOCK_GLOB: a baseline/reference manual drive (aa5b3e0c01) for a null-identifiability check
"""
import sys, glob, os
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOG5_GLOB = str(HERE / "rlogs" / "75604b0a432fdc89_00000005--2ae04b9ba2--*--rlog.zst")
STOCK_GLOB = str(HERE / "rlogs" / "manual" / "aa5b3e0c01" / "*" / "rlog.zst")


def honda_checksum(address, d):
    s = 0; a = address
    while a:
        s += a & 0xF; a >>= 4
    for i, b in enumerate(d):
        if i == len(d) - 1:
            b >>= 4
        s += (b & 0xF) + (b >> 4)
    return (8 - s) & 0xF


def analyze(paths, label):
    p1_by_bus = {}     # bus -> Counter of byte4[7:3]  (gp-0x1500 low-5)
    p2_by_bus = {}     # bus -> Counter of byte7[7:6]  (gp-0x1500 low-2)
    b4_full = {}       # bus -> Counter of full byte4
    b7_full = {}       # bus -> Counter of full byte7
    n330 = Counter()
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

    print(f"\n{'='*78}\n[{label}] CAN-330 decode\n{'='*78}")
    print(f"[dlc] frame length histogram: {dict(dlc)}")
    print(f"[330] frames per bus: {dict(n330)}")
    print(f"[330] checksum ok per bus:  {dict(chk_ok)}")
    print(f"[330] checksum bad per bus: {dict(chk_bad)}")

    for bus in sorted(n330):
        print(f"\n--- {label} bus {bus}: {n330[bus]} CAN-330 frames ---")
        print(f"  byte4[7:3] (gp-0x1500 low-5) histogram: "
              f"{ {f'0b{k:05b}': v for k, v in sorted(p1_by_bus[bus].items())} }")
        print(f"  byte7[7:6] (gp-0x1500 low-2) histogram: "
              f"{ {f'0b{k:02b}': v for k, v in sorted(p2_by_bus[bus].items())} }")
        print(f"  (raw full byte4 top: { {f'0x{k:02X}': v for k, v in b4_full[bus].most_common(6)} })")
        print(f"  (raw full byte7 top: { {f'0x{k:02X}': v for k, v in b7_full[bus].most_common(6)} })")

    return dict(n330=n330, p1=p1_by_bus, p2=p2_by_bus, b4=b4_full, b7=b7_full,
                chk_ok=chk_ok, chk_bad=chk_bad, dlc=dlc)


def main():
    rlog5_paths = sorted(glob.glob(RLOG5_GLOB))
    stock_paths = sorted(glob.glob(STOCK_GLOB))
    print(f"[load] rlog5 (V50P drive): {len(rlog5_paths)} segments")
    for p in rlog5_paths:
        print("   ", os.path.relpath(p, HERE))
    print(f"[load] stock (baseline manual/aa5b3e0c01): {len(stock_paths)} segments")
    for p in stock_paths:
        print("   ", os.path.relpath(p, HERE))

    r5 = analyze(rlog5_paths, "RLOG5 (V50P candidate drive)")
    st = analyze(stock_paths, "STOCK (aa5b3e0c01 baseline, non-probe)")

    print(f"\n{'='*78}\nVERDICT INPUTS\n{'='*78}")
    for label, res in (("RLOG5", r5), ("STOCK", st)):
        for bus in sorted(res["n330"]):
            nonzero_p1 = sum(v for k, v in res["p1"][bus].items() if k != 0)
            nonzero_p2 = sum(v for k, v in res["p2"][bus].items() if k != 0)
            total = res["n330"][bus]
            print(f"  {label} bus {bus}: total={total}  byte4[7:3]!=0 count={nonzero_p1} "
                  f"({100*nonzero_p1/total:.2f}%)  byte7[7:6]!=0 count={nonzero_p2} "
                  f"({100*nonzero_p2/total:.2f}%)")


if __name__ == "__main__":
    main()
