#!/usr/bin/env python3
r"""
decode_v51p_gate1.py -- read V51P (gp-0x1300 "B" + gp-0x1100 "D" -> CAN 330 spare bits) telemetry
out of rlog 7 (V51P drive), and compare against a STOCK (non-probe) manual drive to determine
whether B and/or D are RAM-clean, per the packing in build_v51probe_tva.py (lines 47-59):

    beacon    = (d[4] >> 7) & 0x1   -- forced 1 on every packed probe frame (liveness)
    B_nonzero = (d[4] >> 6) & 0x1   -- gp-0x1300 ("B") full-16-bit != 0
    B_low3    = (d[4] >> 3) & 0x7   -- B low 3 bits (value richness)
    D_nonzero = (d[7] >> 7) & 0x1   -- gp-0x1100 ("D") full-16-bit != 0
    D_low1    = (d[7] >> 6) & 0x1   -- D low bit
    stock-preserved: d[4] & 0x07 (bits 2:0) and d[7] & 0x3F (bits 5:0, Honda counter/checksum)

Mirrors decode_v50p_gate1.py's parsing/checksum/bus-split structure but:
  - RLOG7_GLOB: the V51P on-car drive, 4 flat segments (...--00000007--0a8e7099b8--N--rlog.zst)
  - STOCK_GLOB: the same aa5b3e0c01 baseline used for V50P's null-identifiability check
  - decodes the NEW beacon/B_nonzero/B_low3/D_nonzero/D_low1 fields instead of the old gp-0x1500
    low-5/low-2 sample fields
  - adds a first-nonzero timeline pass (segment + event index + logMonoTime delta from segment
    start) for any cell whose flag ever reads 1, mirroring the V50P "~1.15s after ignition" check
"""
import sys, glob, os
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOG7_GLOB = str(HERE / "rlogs" / "75604b0a432fdc89_00000007--0a8e7099b8--*--rlog.zst")
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


def analyze(paths, label, per_segment_timeline=False):
    beacon_by_bus = Counter()      # bus -> count beacon==1
    bnz_by_bus = Counter()         # bus -> count B_nonzero==1
    dnz_by_bus = Counter()         # bus -> count D_nonzero==1
    blow3_by_bus = {}              # bus -> Counter of B_low3
    dlow1_by_bus = {}              # bus -> Counter of D_low1
    b4bit7_by_bus = {}             # bus -> Counter of d[4] bit7 (raw, for null check)
    b4bit6_by_bus = {}             # bus -> Counter of d[4] bit6 (raw, for null check)
    b7bit7_by_bus = {}             # bus -> Counter of d[7] bit7 (raw, for null check)
    n330 = Counter()
    chk_ok = Counter(); chk_bad = Counter()
    dlc = Counter()

    # timeline: bus -> list of (seg_idx, event_idx, logMonoTime, B_nz, D_nz, beacon)
    timeline = {}

    for seg_idx, path in enumerate(paths):
        seg_t0 = None
        try:
            for evt_idx, evt in enumerate(read_messages(path)):
                try:
                    if evt.which() != "can":
                        continue
                except Exception:
                    continue
                t = getattr(evt, "logMonoTime", None)
                if seg_t0 is None and t is not None:
                    seg_t0 = t
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

                    beacon = (d[4] >> 7) & 0x1
                    b_nz = (d[4] >> 6) & 0x1
                    b_low3 = (d[4] >> 3) & 0x7
                    d_nz = (d[7] >> 7) & 0x1
                    d_low1 = (d[7] >> 6) & 0x1
                    raw_b4bit7 = (d[4] >> 7) & 0x1
                    raw_b4bit6 = (d[4] >> 6) & 0x1
                    raw_b7bit7 = (d[7] >> 7) & 0x1

                    if beacon:
                        beacon_by_bus[bus] += 1
                    if b_nz:
                        bnz_by_bus[bus] += 1
                    if d_nz:
                        dnz_by_bus[bus] += 1
                    blow3_by_bus.setdefault(bus, Counter())[b_low3] += 1
                    dlow1_by_bus.setdefault(bus, Counter())[d_low1] += 1
                    b4bit7_by_bus.setdefault(bus, Counter())[raw_b4bit7] += 1
                    b4bit6_by_bus.setdefault(bus, Counter())[raw_b4bit6] += 1
                    b7bit7_by_bus.setdefault(bus, Counter())[raw_b7bit7] += 1

                    if per_segment_timeline and (b_nz or d_nz or True):
                        dt = (t - seg_t0) / 1e9 if (t is not None and seg_t0 is not None) else None
                        timeline.setdefault(bus, []).append(
                            (seg_idx, evt_idx, dt, b_nz, d_nz, beacon))
        except Exception as e:
            print(f"  !! {os.path.relpath(path, HERE)}: {e}")

    print(f"\n{'='*78}\n[{label}] CAN-330 decode\n{'='*78}")
    print(f"[dlc] frame length histogram: {dict(dlc)}")
    print(f"[330] frames per bus: {dict(n330)}")
    print(f"[330] checksum ok per bus:  {dict(chk_ok)}")
    print(f"[330] checksum bad per bus: {dict(chk_bad)}")

    for bus in sorted(n330):
        total = n330[bus]
        print(f"\n--- {label} bus {bus}: {total} CAN-330 frames ---")
        print(f"  beacon==1:      {beacon_by_bus[bus]:>7} ({100*beacon_by_bus[bus]/total:.3f}%)")
        print(f"  B_nonzero==1:   {bnz_by_bus[bus]:>7} ({100*bnz_by_bus[bus]/total:.3f}%)")
        print(f"  D_nonzero==1:   {dnz_by_bus[bus]:>7} ({100*dnz_by_bus[bus]/total:.3f}%)")
        print(f"  B_low3 histogram: { {k: v for k, v in sorted(blow3_by_bus[bus].items())} }")
        print(f"  D_low1 histogram: { {k: v for k, v in sorted(dlow1_by_bus[bus].items())} }")
        print(f"  (raw d[4] bit7 histogram: { dict(sorted(b4bit7_by_bus[bus].items())) })")
        print(f"  (raw d[4] bit6 histogram: { dict(sorted(b4bit6_by_bus[bus].items())) })")
        print(f"  (raw d[7] bit7 histogram: { dict(sorted(b7bit7_by_bus[bus].items())) })")

    return dict(n330=n330, beacon=beacon_by_bus, bnz=bnz_by_bus, dnz=dnz_by_bus,
                blow3=blow3_by_bus, dlow1=dlow1_by_bus,
                b4bit7=b4bit7_by_bus, b4bit6=b4bit6_by_bus, b7bit7=b7bit7_by_bus,
                chk_ok=chk_ok, chk_bad=chk_bad, dlc=dlc, timeline=timeline)


def print_timeline(res, probe_bus, label):
    tl = res["timeline"].get(probe_bus, [])
    if not tl:
        print(f"  [timeline] no frames recorded for bus {probe_bus}")
        return
    print(f"\n{'='*78}\n[{label}] first-nonzero timeline on probe bus {probe_bus}\n{'='*78}")
    for name, idx in (("B_nonzero", 3), ("D_nonzero", 4)):
        first = None
        for row in tl:
            if row[idx]:
                first = row
                break
        if first is None:
            print(f"  {name}: NEVER nonzero across {len(tl)} frames on bus {probe_bus} -- CLEAN")
        else:
            seg_idx, evt_idx, dt, b_nz, d_nz, beacon = first
            dt_s = f"{dt:.3f}s" if dt is not None else "n/a"
            print(f"  {name}: FIRST nonzero at segment #{seg_idx} (0-indexed), event #{evt_idx}, "
                  f"~{dt_s} from that segment's first CAN event, beacon={beacon}")
    # also report beacon dropouts on this bus
    beacon_zero = [row for row in tl if not row[5]]
    print(f"  beacon==0 frames on bus {probe_bus}: {len(beacon_zero)} / {len(tl)}")
    if beacon_zero:
        seg_idx, evt_idx, dt, b_nz, d_nz, beacon = beacon_zero[0]
        dt_s = f"{dt:.3f}s" if dt is not None else "n/a"
        print(f"    first beacon==0 at segment #{seg_idx}, event #{evt_idx}, ~{dt_s}")


def main():
    rlog7_paths = sorted(glob.glob(RLOG7_GLOB))
    stock_paths = sorted(glob.glob(STOCK_GLOB))
    print(f"[load] rlog7 (V51P drive): {len(rlog7_paths)} segments")
    for p in rlog7_paths:
        print("   ", os.path.relpath(p, HERE))
    print(f"[load] stock (baseline manual/aa5b3e0c01): {len(stock_paths)} segments")
    for p in stock_paths:
        print("   ", os.path.relpath(p, HERE))

    r7 = analyze(rlog7_paths, "RLOG7 (V51P candidate drive)", per_segment_timeline=True)
    st = analyze(stock_paths, "STOCK (aa5b3e0c01 baseline, non-probe)")

    print(f"\n{'='*78}\nPROBE-BUS IDENTIFICATION\n{'='*78}")
    probe_bus = None
    best_frac = -1.0
    for bus in sorted(r7["n330"]):
        total = r7["n330"][bus]
        frac = r7["beacon"][bus] / total if total else 0.0
        print(f"  RLOG7 bus {bus}: total={total}  beacon==1 count={r7['beacon'][bus]} ({100*frac:.3f}%)")
        if frac > best_frac:
            best_frac = frac
            probe_bus = bus
    print(f"\n  => identified PROBE BUS = {probe_bus} (highest beacon==1 fraction, {100*best_frac:.3f}%)")

    print(f"\n{'='*78}\nLOAD-BEARING VERDICT (probe bus {probe_bus}, full V51P drive, all segments)\n{'='*78}")
    if probe_bus is not None:
        total = r7["n330"][probe_bus]
        beacon_n = r7["beacon"][probe_bus]
        b_n = r7["bnz"][probe_bus]
        d_n = r7["dnz"][probe_bus]
        print(f"  total CAN-330 frames on probe bus: {total}")
        print(f"  beacon==1: {beacon_n} ({100*beacon_n/total:.3f}%)  "
              f"{'-- CONFIRMED LIVE' if beacon_n == total else '-- ** NOT 100%, drive may be inconclusive for gaps **'}")
        print(f"  Cell B (gp-0x1300): B_nonzero==1 count={b_n} ({100*b_n/total:.4f}%)  "
              f"=> {'CLEAN (0 on ALL frames)' if b_n == 0 else 'DIRTY -- disqualified, has a live writer'}")
        print(f"  Cell D (gp-0x1100): D_nonzero==1 count={d_n} ({100*d_n/total:.4f}%)  "
              f"=> {'CLEAN (0 on ALL frames)' if d_n == 0 else 'DIRTY -- disqualified, has a live writer'}")

        print_timeline(r7, probe_bus, "RLOG7 (V51P candidate drive)")
    else:
        print("  !! no CAN-330 frames found in V51P drive -- cannot render a verdict")

    print(f"\n{'='*78}\nNULL CHECK (stock aa5b3e0c01 baseline, per bus)\n{'='*78}")
    for bus in sorted(st["n330"]):
        total = st["n330"][bus]
        print(f"  STOCK bus {bus}: total={total}")
        print(f"    d[4] bit7 (beacon position) histogram: {dict(sorted(st['b4bit7'][bus].items()))} "
              f"-- pinned-1 would mimic a beacon; expect NOT pinned on stock")
        print(f"    d[4] bit6 (B_nonzero position) histogram: {dict(sorted(st['b4bit6'][bus].items()))}")
        print(f"    d[7] bit7 (D_nonzero position) histogram: {dict(sorted(st['b7bit7'][bus].items()))}")
        beacon_frac = st['b4bit7'][bus].get(1, 0) / total if total else 0.0
        print(f"    stock d[4] bit7==1 fraction: {100*beacon_frac:.3f}% "
              f"{'-- ⚠ AMBIGUOUS WITH BEACON, investigate' if beacon_frac > 0.95 else '-- distinguishable from a pinned beacon'}")


if __name__ == "__main__":
    main()
