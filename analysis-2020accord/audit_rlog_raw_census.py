#!/usr/bin/env python3
"""audit_rlog_raw_census.py -- SECOND, INDEPENDENT METHOD for the rlog service census.

`audit_rlog_channels.py` counts services through pycapnp's schema layer. That layer can only see
union members `rlog-tools/cereal/log.capnp` declares, and it silently drops anything it cannot name.
The load-bearing claims here are NULLS -- "no channel above 101 Hz", "zero raw-audio messages" -- and
a null obtained through a schema that might not know the field is worth nothing.

So this reads the capnp stream framing BY HAND: segment table -> root struct pointer -> the 16-bit
union discriminant at the Event struct's `discriminantOffset`. It never asks the schema what a field
means, only which discriminant is set. Every message in the file is therefore counted, including
services this cereal copy has never heard of.

Usage:  python audit_rlog_raw_census.py 4a 20 21
"""
import struct
import sys
from collections import Counter
from pathlib import Path

import capnp
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTES = {"4a": "75604b0a432fdc89_0000004a--346bf31d97",
          "47": "75604b0a432fdc89_00000047--3e0b6134c0"}

capnp.remove_import_hook()
LC = capnp.load(str(ROOT / "rlog-tools" / "cereal" / "log.capnp"))
NODE = LC.Event.schema.node
NAMES = {f.proto.discriminantValue: f.proto.name for f in LC.Event.schema.fields_list
         if f.proto.discriminantValue != 0xFFFF}
DOFF = NODE.struct.discriminantOffset


def census(path):
    data = zstd.ZstdDecompressor().stream_reader(open(path, "rb")).read()
    c, off, nroot = Counter(), 0, 0
    while off < len(data):
        nseg = struct.unpack_from("<I", data, off)[0] + 1
        hdr = 4 + 4 * nseg
        hdr += (8 - (hdr % 8)) % 8
        sizes = [struct.unpack_from("<I", data, off + 4 + 4 * i)[0] for i in range(nseg)]
        body = off + hdr
        ptr = struct.unpack_from("<Q", data, body)[0]
        if (ptr & 3) == 0:                                  # struct pointer
            offw = (ptr >> 2) & 0x3FFFFFFF
            if offw >= 0x20000000:
                offw -= 0x40000000
            dwords = (ptr >> 32) & 0xFFFF
            dstart = body + 8 + offw * 8
            if DOFF * 2 + 2 <= dwords * 8:
                c[struct.unpack_from("<H", data, dstart + DOFF * 2)[0]] += 1
                nroot += 1
        off = body + sum(sizes) * 8
    return c, nroot


def main(tag, segs):
    print(__doc__.split("Usage:")[0].rstrip())
    total, files = Counter(), 0
    for s in segs:
        p = RLOGDIR / f"{ROUTES[tag]}--{s}--rlog.zst"
        if not p.exists():
            continue
        c, n = census(p)
        total += c
        files += 1
        print(f"  {p.name}: {n} root structs, {len(c)} distinct discriminants")
    dur = 60.0 * files                                      # openpilot segments are 60 s
    print(f"\n=== route {tag}, {files} segments, {dur:.0f} s nominal ===")
    print(f"{'disc':>5s} {'service':30s} {'count':>8s} {'count/s':>9s}")
    for d, n in total.most_common():
        nm = NAMES.get(d, f"<<UNKNOWN #{d} -- not in this cereal copy>>")
        print(f"{d:5d} {nm:30s} {n:8d} {n / dur:9.3f}")
    top = max(total.items(), key=lambda kv: kv[1])
    print(f"\nHIGHEST COUNT/S: {NAMES.get(top[0], top[0])} at {top[1] / dur:.3f} msg/s")
    fast = [(NAMES.get(d, d), n / dur) for d, n in total.items() if n / dur > 101.5]
    print(f"ANY service above 101.5 msg/s: {fast if fast else 'NONE'}")
    for want in ("rawAudioData", "audioFeedback", "soundPressure", "accelerometer", "gyroscope",
                 "magnetometer", "lightSensor"):
        d = next((k for k, v in NAMES.items() if v == want), None)
        print(f"  {want:16s} discriminant {d}: {total.get(d, 0)} messages "
              f"({total.get(d, 0) / dur:.3f}/s)")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "4a"
    segs = [int(x) for x in sys.argv[2:]] or [20, 21, 22, 23, 24, 25]
    main(tag, segs)
