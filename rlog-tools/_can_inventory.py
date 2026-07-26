"""Inventory CAN (bus, address) seen in rlog.zst files + flag radar-relevant IDs.
Answers: which radar IDs (object/range/AEB/XCP/UDS) are present on which bus in the operator's drive logs?
Usage: python _can_inventory.py <rlog.zst> [<rlog.zst> ...]
"""
import io, sys
from pathlib import Path
import zstandard as zstd
import capnp

CEREAL_DIR = Path(__file__).parent / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL_DIR / "log.capnp"))

# radar-relevant IDs to flag
RADAR = {
    0x1DF: "AEB/ACC control (0x1DF)",
    0x2C8: "Bosch selected-lead 0 (0x2C8)", 0x2C9: "Bosch selected-lead 1 (0x2C9)",
    0x640: "XCP CRO (0x640)", 0x641: "XCP DTO/stream (0x641)",
    0x400: "Nidec radar state (0x400)",
    0x18DAB0F1: "UDS req -> radar (0x18DAB0F1)", 0x18DAF1B0: "UDS resp <- radar (0x18DAF1B0)",
}
for x in range(0xC7, 0xD9): RADAR[x] = f"object-track? (0x{x:X})"
for x in range(0x430, 0x446): RADAR[x] = f"Nidec radar track (0x{x:X})"
for x in range(0x280, 0x288): RADAR[x] = f"object/lead? (0x{x:X})"

def inventory(paths, max_events_per=200000):
    seen = {}   # (bus, addr) -> count
    for p in paths:
        try:
            data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(Path(p).read_bytes())).read()
        except Exception as e:
            print(f"  [skip {p}: {e}]"); continue
        n = 0
        try:
            for evt in log_capnp.Event.read_multiple_bytes(data):
                if evt.which() == "can":
                    for c in evt.can:
                        k = (int(c.src), int(c.address))
                        seen[k] = seen.get(k, 0) + 1
                n += 1
                if n >= max_events_per: break
        except Exception as e:
            print(f"  [parse-end {p}: {e}]")
    return seen

if __name__ == "__main__":
    seen = inventory(sys.argv[1:])
    buses = sorted({b for (b, a) in seen})
    print(f"=== buses present: {buses} ; total unique (bus,addr) pairs: {len(seen)} ===")
    # per-bus address ranges + count
    for b in buses:
        addrs = sorted(a for (bb, a) in seen if bb == b)
        print(f"  bus {b}: {len(addrs)} unique IDs, range 0x{min(addrs):X}-0x{max(addrs):X}")
    print("\n=== RADAR-RELEVANT IDs found (bus, id, count, meaning) ===")
    hits = sorted(((b, a, c) for (b, a), c in seen.items() if a in RADAR), key=lambda x: (x[0], x[1]))
    if not hits:
        print("  NONE of the flagged radar IDs present.")
    for b, a, c in hits:
        print(f"  bus {b}  0x{a:<8X}  x{c:<7d}  {RADAR[a]}")
    # also: any IDs in the 0x100-0x500 band on each bus (likely object/lead data)
    print("\n=== all IDs 0x100-0x500 per bus (candidate object/lead frames) ===")
    for b in buses:
        ids = sorted(a for (bb, a) in seen if bb == b and 0x100 <= a <= 0x500)
        print(f"  bus {b}: {[hex(x) for x in ids]}")
