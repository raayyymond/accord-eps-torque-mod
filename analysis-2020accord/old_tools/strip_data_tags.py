#!/usr/bin/env python3
"""
strip_data_tags.py — remove the per-word tag from a tagged data.bin dump.

The 2020 Accord (TVA / V850) `data.bin` dump covers 0x02000000-0x02007FFF
(0x8000 = 32 KiB of real flash) but lands on disk at 0x10000 = 64 KiB: it is
*doubled* because the dumper emits every 4-byte data word paired with a 4-byte
"tag" word (a status/erased flag that reads uniformly 0x00000000 when the word
is written or 0xFFFFFFFF when it is erased).

This script auto-detects that interleave, strips the tag, and writes the
de-tagged image (expected: half the input size, == 0x8000).

Auto-detection (rather than a hardcoded 4+4) so the same tool survives a
different dumper granularity: it splits the file into units of size 2*c for
each candidate chunk size c, and picks the layout where the trailing c bytes
of (nearly) every unit are a single repeated byte — the signature of a tag.

Lightweight raw-.bin inspection per the project's
feedback_lightweight_inspection_over_ghidra rule.

Usage:
    python strip_data_tags.py [input] [-o OUTPUT] [--base 0x02000000]
                              [--no-write] [--data-first | --tag-first]

Defaults:
    input  = the configured stock_fw_dump/data.bin
    output = <input_dir>/<input_stem>_stripped.bin
"""

import argparse
import os
import sys
from collections import Counter

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import STOCK_FW_DUMP

# Candidate data-chunk sizes to try (a unit is 2*c bytes: c data + c tag).
CANDIDATE_CHUNKS = (1, 2, 4, 8, 16, 32)


def is_uniform(b: bytes) -> bool:
    """True if every byte in b is identical (the tag-word signature)."""
    return len(b) > 0 and b.count(b[0]) == len(b)


def score_layout(data: bytes, c: int, tag_first: bool) -> float:
    """
    Fraction of 2c-byte units whose tag-half is a single repeated byte.
    tag_first=False -> [data c][tag c];  tag_first=True -> [tag c][data c].
    Returns -1 if the file isn't a whole number of units.
    """
    unit = 2 * c
    if len(data) % unit != 0:
        return -1.0
    n_units = len(data) // unit
    if n_units == 0:
        return -1.0
    uniform = 0
    for off in range(0, len(data), unit):
        tag = data[off:off + c] if tag_first else data[off + c:off + unit]
        if is_uniform(tag):
            uniform += 1
    return uniform / n_units


def detect_layout(data: bytes):
    """
    Return (chunk_size, tag_first, score) for the best-scoring interleave.
    Prefers larger chunk sizes on ties (a 4-byte tag word is more meaningful
    than a coincidental 1-byte uniform run).
    """
    best = None  # (score, chunk, tag_first)
    for c in CANDIDATE_CHUNKS:
        for tag_first in (False, True):
            s = score_layout(data, c, tag_first)
            if s < 0:
                continue
            key = (round(s, 6), c)  # higher score, then larger chunk
            if best is None or key > (round(best[0], 6), best[1]):
                best = (s, c, tag_first)
    if best is None:
        return None
    return best[1], best[2], best[0]


def strip(data: bytes, c: int, tag_first: bool):
    """Strip the tag half from each 2c-byte unit. Returns (out, tag_byte_hist,
    list of anomalous unit offsets where data side looks like a tag too)."""
    unit = 2 * c
    out = bytearray()
    tag_hist = Counter()
    anomalies = []
    for off in range(0, len(data), unit):
        if tag_first:
            tag = data[off:off + c]
            real = data[off + c:off + unit]
        else:
            real = data[off:off + c]
            tag = data[off + c:off + unit]
        out += real
        if is_uniform(tag):
            tag_hist[tag[0]] += 1
        else:
            tag_hist[None] += 1
            anomalies.append((off, tag.hex()))
    return bytes(out), tag_hist, anomalies


def main(argv=None):
    default_in = str(STOCK_FW_DUMP / "data.bin")

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", default=default_in,
                    help="tagged data.bin (default: configured stock_fw_dump/data.bin)")
    ap.add_argument("-o", "--output", default=None,
                    help="output path (default: <input>_stripped.bin)")
    ap.add_argument("--base", default="0x02000000",
                    help="flash base address for the coverage report (default 0x02000000)")
    ap.add_argument("--no-write", action="store_true",
                    help="analyze and report only; do not write output")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--data-first", dest="force_tag_first", action="store_const", const=False,
                     help="force layout [data][tag] (skip auto-detect)")
    grp.add_argument("--tag-first", dest="force_tag_first", action="store_const", const=True,
                     help="force layout [tag][data] (skip auto-detect)")
    ap.set_defaults(force_tag_first=None)
    args = ap.parse_args(argv)

    if not os.path.isfile(args.input):
        ap.error(f"input not found: {args.input}")
    data = open(args.input, "rb").read()
    base = int(args.base, 0)

    print(f"input : {args.input}")
    print(f"size  : {len(data)} bytes (0x{len(data):X})")

    # --- detect (or honor forced) layout ---
    if args.force_tag_first is None:
        det = detect_layout(data)
        if det is None:
            sys.exit("ERROR: could not split file into tag/data units (odd size?)")
        chunk, tag_first, score = det
        print(f"detect: chunk={chunk}B  layout={'[tag][data]' if tag_first else '[data][tag]'}  "
              f"tag-uniform={score:.4%} of units")
        if score < 0.999:
            print("WARNING: tag side is not uniform in every unit — inspect anomalies below "
                  "before trusting the output.")
    else:
        # Forced: pick the largest chunk size that divides the file evenly.
        chunk = next((c for c in reversed(CANDIDATE_CHUNKS) if len(data) % (2 * c) == 0), 1)
        tag_first = args.force_tag_first
        print(f"forced: chunk={chunk}B  layout={'[tag][data]' if tag_first else '[data][tag]'}")

    out, tag_hist, anomalies = strip(data, chunk, tag_first)

    # --- report ---
    halved_ok = (len(out) * 2 == len(data))
    print(f"output: {len(out)} bytes (0x{len(out):X})  "
          + ("= input/2 [OK]" if halved_ok else "(UNEXPECTED: not exactly half of input)"))
    hist_str = ", ".join(
        ("non-uniform" if k is None else f"0x{k:02X}") + f" x{v}"
        for k, v in sorted(tag_hist.items(), key=lambda kv: (kv[0] is None, kv[0]))
    )
    print(f"tags  : {hist_str}")
    print(f"cover : 0x{base:08X}-0x{base + len(out) - 1:08X}  ({len(out)} bytes)")
    if anomalies:
        print(f"!! {len(anomalies)} unit(s) with a NON-uniform tag side (first 10):")
        for off, h in anomalies[:10]:
            print(f"     unit @0x{off:X}: tag={h}")

    if args.no_write:
        print("(--no-write: nothing written)")
        return 0

    out_path = args.output or os.path.join(
        os.path.dirname(args.input),
        os.path.splitext(os.path.basename(args.input))[0] + "_stripped.bin",
    )
    with open(out_path, "wb") as f:
        f.write(out)
    print(f"wrote : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
