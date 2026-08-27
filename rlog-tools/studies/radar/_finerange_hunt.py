"""Hunt the FUN_B718C sub-10m fine-range field in the rlogs (bead eps-ejq).
Fingerprint: a u16 (big-endian) on an ARM bus (0/1) that PINS at ~2000 (the firmware clamp = 10.0m at
5mm/LSB) most of the time and DIPS below only when a close lead is present -- correlating with the coarse
0x2C8 range (bus 2). Phase 1: scan every u16 field on buses 0/1 for the pin-at-2000 signature.
"""
import io, sys, struct
from pathlib import Path
import zstandard as zstd
import capnp

CEREAL_DIR = Path(__file__).parents[2] / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))

SAT = 2000          # firmware clamp (FUN_B718C max=0x44FA0000=2000.0)
CAND_IDS = {0x1EF, 0x30C, 0x39F, 0x1FA, 0x1DB, 0x33D, 0xE4}  # trace's ARM TX candidates (highlight)

def load(p, cap=150000):
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
    frames = []   # (t, bus, addr, dat)
    n = 0
    try:
        for evt in log_capnp.Event.read_multiple_bytes(data):
            if evt.which() == "can":
                t = evt.logMonoTime
                for c in evt.can:
                    frames.append((t, int(c.src), int(c.address), bytes(c.dat)))
            n += 1
            if n >= cap:
                break
    except Exception as e:
        sys.stderr.write(f"  [parse-end {Path(p).name}: {e}]\n")
    return frames

def main(paths):
    # accumulate per (bus,addr,pos) u16 BE stats across all segments
    from collections import defaultdict
    vals = defaultdict(list)        # (bus,addr,pos) -> list of u16
    present = defaultdict(int)      # (bus,addr) -> count
    for p in paths:
        fr = load(p)
        print(f"  {Path(p).parent.name}: {len(fr)} can frames")
        for t, bus, addr, dat in fr:
            if bus not in (0, 1):     # ARM-managed buses (DSP object data is bus 2)
                continue
            present[(bus, addr)] += 1
            for pos in range(0, len(dat) - 1):
                vals[(bus, addr, pos)].append((dat[pos] << 8) | dat[pos + 1])

    print(f"\n=== IDs present on bus 0/1: {len(present)} ===")
    cand_present = sorted([(b, a, c) for (b, a), c in present.items() if a in CAND_IDS])
    print("  trace-candidate IDs present (bus,id,count):",
          [(b, hex(a), c) for b, a, c in cand_present] or "NONE of the 5")

    # fingerprint scan: u16 fields whose MAX pins near 2000 and that VARY (dip below)
    print(f"\n=== u16 fields PINNING near {SAT} (the FUN_B718C clamp) ===")
    hits = []
    for (bus, addr, pos), vv in vals.items():
        if len(vv) < 50:
            continue
        mx = max(vv); mn = min(vv)
        if not (1990 <= mx <= 2010):     # clamp ceiling near 2000
            continue
        frac_at_mx = sum(1 for x in vv if x >= mx - 1) / len(vv)
        ndist = len(set(vv))
        if frac_at_mx < 0.10 or ndist < 8 or mn > mx * 0.9:   # must pin AND resolve down AND vary
            continue
        hits.append((frac_at_mx, bus, addr, pos, mx, mn, ndist, len(vv)))
    hits.sort(reverse=True)
    if not hits:
        print("  NONE -- no u16 on bus 0/1 pins at ~2000 and dips. (fine-range field may be LE, on bus 2,")
        print("  saturate at a different value, or not broadcast. Phase-2 correlation skipped.)")
    for frac, bus, addr, pos, mx, mn, ndist, n in hits[:25]:
        star = " <-- TRACE CANDIDATE" if addr in CAND_IDS else ""
        print(f"  bus{bus} 0x{addr:03X} B{pos}:B{pos+1}  pin@{mx} {frac*100:4.1f}%  min={mn}  "
              f"ndistinct={ndist}  n={n}{star}")
    return hits, vals

if __name__ == "__main__":
    main(sys.argv[1:])
