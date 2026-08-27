"""Decode the V31T passive telemetry piggybacked onto CAN 0x660, and correlate it with the
gentle-EME cut on CAN 399. Use this on rlog.zst captured while running the V31T firmware.

V31T overwrites CAN 0x660 (1632) payload bytes 0..5 with three little-endian RAM words
(see builds/v18_v49/build_v31t_tva.py). The EPS writes them with V850 st.h => LITTLE-ENDIAN on the wire:

  0x660 byte 0:1 = gp-0x6a62 (0xFEDF159E)  u16   THE gentle-EME gate signal (sensor-A voter MAX)
  0x660 byte 2:3 = gp-0x4f60 (0xFEDF30A0)  s16   sensor B = CAN STEER_TORQUE_SENSOR source (scale bridge)
  0x660 byte 4:5 = gp-0x6a5e (0xFEDF15A2)  s16   sensor A AVG / boost-curve axis
  0x660 byte 6   = 0 ;  byte 7 = rolling counter (hi nibble) + 4-bit checksum (lo nibble)

The gentle EME fires when gp-0x6a62 >= cal 0xC6312 (= 320) -> STEER_STATUS = no_torque_alert_2 (4)
on CAN 399. GOAL 1: confirm gp-0x6a62 crosses 320 exactly at the 399 STEER_STATUS->4 instant.
GOAL 2: read the legitimate-hard-turn / driver-grab PEAK of gp-0x6a62 and the gp-0x6a62 : |CAN tbar|
scale, to size a new 0xC6312.

Usage:  python studies/telemetry/analyze_telem_0x660.py <route>--rlog.zst [...]   [--src N] [--id 0xNNN]
"""
import io, sys
from pathlib import Path
import zstandard as zstd
import capnp

KIT = Path(__file__).resolve().parents[2].parent
CEREAL = KIT / "rlog-tools" / "cereal"
capnp.remove_import_hook()
log_capnp = capnp.load(str(CEREAL / "log.capnp"))

GATE_THRESHOLD = 320          # cal 0xC6312 (gp-0x6a62 >= this -> gentle EME)
TELEM_ID       = 0x660        # CAN 1632, V31T piggyback frame
SRC            = 1            # EPS TX src in the rlog (399 is src 1); override with --src

def be_bits(data, start, length):
    """DBC Motorola (@0) big-endian extraction, MSB-first (for the stock 399 signals)."""
    val = 0; bit = start
    for _ in range(length):
        byte, b_in = bit // 8, bit % 8
        val = (val << 1) | ((data[byte] >> b_in) & 1)
        bit = bit + 15 if b_in == 0 else bit - 1
    return val

def s16(u):
    return u - 0x10000 if u & 0x8000 else u

def le_u16(d, i):                      # V850 st.h little-endian on the wire
    return d[i] | (d[i + 1] << 8)

def dec660(d):
    """V31T telemetry: little-endian words at byte 0:1, 2:3, 4:5."""
    if len(d) < 6: return None
    return {
        "gate": le_u16(d, 0),          # gp-0x6a62, unsigned magnitude
        "senB": s16(le_u16(d, 2)),     # gp-0x4f60, signed (CAN torque source)
        "senA": s16(le_u16(d, 4)),     # gp-0x6a5e, signed
        "ctr":  (d[7] >> 4) & 0xf if len(d) >= 8 else None,
    }

def dec399(d):
    if len(d) < 7: return None
    return {
        "status": be_bits(d, 39, 4),
        "active": be_bits(d, 35, 1),
        "tbar":   -s16(be_bits(d, 7, 16)),         # CAN STEER_TORQUE_SENSOR, scale -1
    }

def events(path):
    raw = Path(path).read_bytes()
    data = zstd.ZstdDecompressor().stream_reader(io.BytesIO(raw)).read()
    it = log_capnp.Event.read_multiple_bytes(data)
    while True:
        try: yield next(it)
        except StopIteration: break
        except capnp.KjException: break

def analyze(path, src, telem_id):
    print("\n" + "=" * 100 + f"\n{Path(path).name}   (telem id 0x{telem_id:X}, src {src})\n" + "=" * 100)
    rows = []            # (ts, kind, data)
    t0 = None
    seen_660 = 0
    srcs_660 = {}
    last399 = {"status": None, "active": None, "tbar": None}
    for evt in events(path):
        t = evt.logMonoTime
        if t0 is None: t0 = t
        ts = (t - t0) / 1e9
        if evt.which() != "can":
            continue
        for c in evt.can:
            if c.address == telem_id:
                srcs_660[c.src] = srcs_660.get(c.src, 0) + 1
                if c.src == src:
                    dd = dec660(bytes(c.dat))
                    if dd:
                        seen_660 += 1
                        rows.append((ts, "telem", dict(dd, **last399)))
            elif c.address == 399 and c.src == src:
                d9 = dec399(bytes(c.dat))
                if d9:
                    last399 = d9

    if seen_660 == 0:
        print(f"  !! no 0x{telem_id:X} on src {src}. seen on srcs: {srcs_660 or 'NONE'}")
        print("     (re-run with --src N for the bus where the EPS TX appears)")
        return
    print(f"  {seen_660} telem frames on src {src} (all srcs seen: {srcs_660})")

    # ---- GOAL 1: gate vs threshold around each STEER_STATUS->4 ----
    cut_idxs = [i for i in range(1, len(rows))
                if rows[i][2]["status"] == 4 and rows[i - 1][2]["status"] not in (4, None)]
    if not cut_idxs:
        from collections import Counter
        print("  no STEER_STATUS->4 transition in telem stream. status histogram:",
              Counter(r[2]["status"] for r in rows))
    for ci in cut_idxs:
        tcut = rows[ci][0]
        print(f"\n  *** gentle-EME (STEER_STATUS->4) at t={tcut:.3f}s ***")
        print(f"  {'t_s':>8} {'gate':>6} {'>=320':>5} {'senB':>6} {'tbarCAN':>7} {'senA':>6} {'STAT':>4} {'ctrlA':>5}")
        print("  " + "-" * 60)
        for ts, kind, d in rows:
            if tcut - 0.6 <= ts <= tcut + 0.6:
                flag = "Y" if d["gate"] >= GATE_THRESHOLD else "."
                mark = " <==4" if d["status"] == 4 else ""
                tb = "   -" if d["tbar"] is None else f"{d['tbar']:7d}"
                stt = "-" if d["status"] is None else str(d["status"])
                act = "-" if d["active"] is None else str(d["active"])
                print(f"  {ts:8.3f} {d['gate']:6d} {flag:>5} {d['senB']:6d} {tb} {d['senA']:6d} {stt:>4} {act:>5}{mark}")

    # ---- GOAL 2: peaks + scale during normal (non-cut) driving ----
    normal = [d for _, _, d in rows if d["status"] != 4]
    gates = sorted(d["gate"] for d in normal)
    if gates:
        def pct(p): return gates[min(len(gates) - 1, int(p * len(gates)))]
        print(f"\n  gp-0x6a62 (gate) over {len(gates)} normal-status frames:")
        print(f"    median={pct(0.5)}  p90={pct(0.9)}  p95={pct(0.95)}  p99={pct(0.99)}  max={gates[-1]}")
        for thr in (320, 640, 960, 1600, 2400):
            n = sum(1 for g in gates if g > thr)
            print(f"    > {thr:5d}: {100.0 * n / len(gates):5.1f}%")
    # gate : |CAN tbar| scale (where both present and tbar nonzero)
    pairs = [(d["gate"], abs(d["tbar"])) for d in normal
             if d["tbar"] is not None and abs(d["tbar"]) > 50]
    if pairs:
        ratios = sorted(g / t for g, t in pairs)
        med = ratios[len(ratios) // 2]
        print(f"  gate : |CAN tbar| ratio over {len(pairs)} frames:  median={med:.3f}  "
              f"(min={ratios[0]:.3f} max={ratios[-1]:.3f})")
        print(f"    => CAN |tbar| ~ {1.0/med:.2f} x gp-0x6a62   (use to map road-data CAN peaks into gate units)")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src = SRC; telem_id = TELEM_ID
    av = sys.argv[1:]
    for i, a in enumerate(av):
        if a == "--src" and i + 1 < len(av): src = int(av[i + 1])
        if a == "--id" and i + 1 < len(av): telem_id = int(av[i + 1], 0)
    if not args:
        print(__doc__); return
    for p in args:
        analyze(p, src, telem_id)

if __name__ == "__main__":
    main()
