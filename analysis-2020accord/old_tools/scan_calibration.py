#!/usr/bin/env python
"""
Exhaustive calibration-region scan for 2020 Accord EPS firmware (code.bin, V850E2 LE).

Scope:
  Calibration region 0xC4000 - 0xFD0B8 only. Do not scan outside this range.

Patterns scanned (with disambiguation between int16-axis and float interpretations
of the same byte range — denormal/tiny floats are rejected as misinterpretation):

  1) Monotonic int16 axes (strictly increasing, length >= MIN_AXIS_LEN, calibration-shaped:
     first value near zero, last value > 100, sane magnitudes).
  2) Paired int16 curves (two adjacent same-length monotonic curves; C4A42/C4A6E archetype).
  3) 2D maps with repeated identical int16 rows (>= 3 contiguous identical rows; E417E archetype).
  4) IEEE-754 float blocks: monotonic non-zero arrays and zero-interleaved axes (C4784 archetype).
     All floats must be finite, non-denormal (|x| >= 1e-6 unless exactly 0.0), |x| < 1e6.

Output:
  scan_calibration.json with full inventory.
  Pipe-delimited summary to stdout.

Notes on protected blocks (per §5b of CODE_BIN_FIRMWARE_MAP.md):
  CRC-32-protected 4KB blocks intersecting calibration scope:
    0xC5000, 0xC6000, 0xCD000..0xF8000 (44 blocks, every 0x1000).
  NOT protected (patches there don't need CRC recomputation):
    0xC4000, 0xC7000..0xCC000, 0xF9000..0xFC000.
"""

import json
import math
import os
import struct
import sys

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import STOCK_FW_DUMP

CODE_BIN = STOCK_FW_DUMP / "code.bin"
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_calibration.json")

SCAN_START = 0xC4000
SCAN_END   = 0xFD0B8

BLOCK_SIZE = 0x1000

PROTECTED_BLOCKS = set()
PROTECTED_BLOCKS.add(0xC5000)
PROTECTED_BLOCKS.add(0xC6000)
for b in range(0xCD000, 0xF9000, BLOCK_SIZE):
    PROTECTED_BLOCKS.add(b)

# ---- thresholds ------------------------------------------------------------

MIN_AXIS_LEN          = 5
MIN_FLOAT_AXIS_LEN    = 5
MIN_2D_ROW_LEN        = 4
MIN_2D_ROWS           = 3

# int16 axis shape: must start near zero, end at a non-trivial value, and have
# magnitudes in the calibration range.
AXIS_FIRST_MAX_ABS    = 200      # |first| must be <= this
AXIS_LAST_MIN         = 50       # last value must be >= this
AXIS_MIN_SPAN         = 50
INT16_SANE_MIN        = -8000    # axes rarely negative; clamps/coeffs may be
INT16_SANE_MAX        = 32700

# float sanity
FLOAT_MIN_ABS_NONZERO = 1e-6     # below this is denormal/junk
FLOAT_MAX_ABS         = 1e6
FLOAT_AXIS_MIN_NONZERO = 4

# ---- helpers ---------------------------------------------------------------

def block_start(addr):
    return addr & ~(BLOCK_SIZE - 1)

def is_protected(addr):
    return block_start(addr) in PROTECTED_BLOCKS

def looks_like_real_float(v):
    if not math.isfinite(v):
        return False
    if v == 0.0:
        return True   # 0.0 explicitly allowed as placeholder
    av = abs(v)
    if av < FLOAT_MIN_ABS_NONZERO:
        return False
    if av > FLOAT_MAX_ABS:
        return False
    return True

def looks_like_real_float_nonzero(v):
    return looks_like_real_float(v) and v != 0.0

def axis_shape_ok(run):
    """Calibration-axis shape heuristic. Returns True if `run` looks like a real
    breakpoint axis (starts near 0, ends meaningfully positive, sane magnitudes)."""
    if len(run) < MIN_AXIS_LEN:
        return False
    if not all(INT16_SANE_MIN <= v <= INT16_SANE_MAX for v in run):
        return False
    if abs(run[0]) > AXIS_FIRST_MAX_ABS:
        return False
    if run[-1] < AXIS_LAST_MIN:
        return False
    if (run[-1] - run[0]) < AXIS_MIN_SPAN:
        return False
    return True

def axis_shape_loose_ok(run):
    """Looser: monotonic, sane, span >= 8 — used for paired-curve candidates that
    don't individually look like a clean axis but still form coherent rows."""
    if len(run) < MIN_AXIS_LEN:
        return False
    if not all(INT16_SANE_MIN <= v <= INT16_SANE_MAX for v in run):
        return False
    if (run[-1] - run[0]) < 8:
        return False
    return True

# ---- scanners --------------------------------------------------------------

def scan_int16_axes(data, strict=True):
    """Strict (default): tight calibration-axis shape. Loose: span-only."""
    out = []
    off = SCAN_START
    while off + 2 * MIN_AXIS_LEN <= SCAN_END:
        if off % 2 != 0:
            off += 1
            continue
        try:
            first = struct.unpack_from("<h", data, off)[0]
        except struct.error:
            break
        if not (INT16_SANE_MIN <= first <= INT16_SANE_MAX):
            off += 2; continue
        run = [first]
        cur = off + 2
        prev = first
        while cur + 2 <= SCAN_END:
            v = struct.unpack_from("<h", data, cur)[0]
            if v <= prev or not (INT16_SANE_MIN <= v <= INT16_SANE_MAX):
                break
            run.append(v); prev = v; cur += 2
        accept = axis_shape_ok(run) if strict else axis_shape_loose_ok(run)
        if accept:
            out.append({
                "address": off,
                "type": "int16_monotonic_axis",
                "length_bytes": len(run) * 2,
                "count": len(run),
                "sample": run[:16],
                "span": run[-1] - run[0],
            })
            off = cur
            continue
        off += 2
    return out

def scan_paired_curves(data):
    """Find pairs of same-length, near-identical-shape monotonic int16 curves.

    Two flavors are recognized:
      (a) Adjacent (end_a == start_b) — clean 2D row layout.
      (b) Near-adjacent (gap <= 32 bytes) AND same-length AND first values match
          within 20 (the C4A42/C4A6E archetype: both start at 0, count=12, similar
          shapes, separated by a 20-byte intervening curve).

    LOOSE axis criteria — paired curves may have first values outside the strict
    axis-shape test.
    """
    loose = scan_int16_axes(data, strict=False)
    by_addr = {a["address"]: a for a in loose}
    addrs = sorted(by_addr)
    out = []
    used = set()
    # Adjacent first
    for i in range(len(addrs) - 1):
        a = by_addr[addrs[i]]
        end_a = a["address"] + a["length_bytes"]
        b = by_addr.get(end_a)
        if not b or a["count"] != b["count"]:
            continue
        if a["address"] in used or b["address"] in used:
            continue
        used.add(a["address"]); used.add(b["address"])
        out.append({
            "address": a["address"],
            "type": "paired_int16_curves",
            "length_bytes": a["length_bytes"] + b["length_bytes"],
            "rows": 2,
            "cols": a["count"],
            "adjacency": "adjacent",
            "sample_row0": a["sample"][:12],
            "sample_row1": b["sample"][:12],
            "components": [a["address"], b["address"]],
        })
    # Near-adjacent (gap > 0 but <= 32 bytes), same-shape signature
    for i in range(len(addrs) - 1):
        a = by_addr[addrs[i]]
        if a["address"] in used:
            continue
        end_a = a["address"] + a["length_bytes"]
        # Search next few candidates for a same-count partner within 32 bytes
        for j in range(i + 1, min(i + 6, len(addrs))):
            b = by_addr[addrs[j]]
            if b["address"] in used:
                continue
            gap = b["address"] - end_a
            if gap < 1 or gap > 32:
                continue
            if a["count"] != b["count"]:
                continue
            # Shape similarity: same first value (or both near zero), same span order
            if abs(a["sample"][0] - b["sample"][0]) > 20:
                continue
            if a["sample"][-1] == 0 or b["sample"][-1] == 0:
                continue
            ratio = a["sample"][-1] / b["sample"][-1]
            if not (0.5 <= ratio <= 2.0):
                continue
            used.add(a["address"]); used.add(b["address"])
            out.append({
                "address": a["address"],
                "type": "paired_int16_curves",
                "length_bytes": (b["address"] + b["length_bytes"]) - a["address"],
                "rows": 2,
                "cols": a["count"],
                "adjacency": f"near_adjacent_gap_{gap}",
                "sample_row0": a["sample"][:12],
                "sample_row1": b["sample"][:12],
                "components": [a["address"], b["address"]],
            })
            break
    return out

def scan_clustered_axes_as_2d(data, strict_axes):
    """Detect clusters of >=3 short int16 axes (count 5..8) at constant stride
    with identical first/last values — these almost certainly represent a 2D
    map whose rows aren't byte-identical (so scan_2d_repeated_rows misses them)
    but whose first column is consistent.

    Example (C4A9A): 6 axes [0,4,700,1000,2000,3000] spaced every 20 bytes.
    """
    out = []
    by_addr = sorted(strict_axes, key=lambda a: a["address"])
    used = set()
    for i, a in enumerate(by_addr):
        if a["address"] in used:
            continue
        if a["count"] > 12:
            continue
        # Look for consecutive same-shape axes at constant stride
        group = [a]
        stride = None
        for j in range(i + 1, len(by_addr)):
            b = by_addr[j]
            if b["address"] in used:
                break
            if b["count"] != a["count"]:
                break
            if b["sample"][0] != a["sample"][0] or b["sample"][-1] != a["sample"][-1]:
                break
            cur_stride = b["address"] - group[-1]["address"]
            if stride is None:
                stride = cur_stride
                if stride < a["length_bytes"] or stride > a["length_bytes"] + 16:
                    break
            elif cur_stride != stride:
                break
            group.append(b)
            if len(group) >= 8:
                break
        if len(group) >= 3:
            for g in group:
                used.add(g["address"])
            start = group[0]["address"]
            end = group[-1]["address"] + group[-1]["length_bytes"]
            out.append({
                "address": start,
                "type": "2d_clustered_int16",
                "length_bytes": end - start,
                "rows": len(group),
                "cols_per_row": a["count"],
                "stride": stride,
                "first_value": a["sample"][0],
                "last_value": a["sample"][-1],
                "sample_row0": a["sample"][:12],
                "row_addresses": [g["address"] for g in group],
            })
    return out, used

def scan_2d_repeated_rows(data):
    """Find runs of >=3 identical int16 rows (cols in 4..32)."""
    out = []
    for cols in range(MIN_2D_ROW_LEN, 33):
        row_bytes = cols * 2
        off = SCAN_START
        while off + row_bytes * MIN_2D_ROWS <= SCAN_END:
            if off % 2 != 0:
                off += 1; continue
            row0 = data[off:off + row_bytes]
            try:
                vals = struct.unpack("<" + "h" * cols, row0)
            except struct.error:
                off += 2; continue
            if not all(INT16_SANE_MIN <= v <= INT16_SANE_MAX for v in vals):
                off += 2; continue
            if max(vals) - min(vals) < 8:
                off += 2; continue
            n_rows = 1
            cur = off + row_bytes
            while cur + row_bytes <= SCAN_END and data[cur:cur + row_bytes] == row0:
                n_rows += 1; cur += row_bytes
            if n_rows >= MIN_2D_ROWS:
                out.append({
                    "address": off,
                    "type": "2d_repeated_rows_int16",
                    "length_bytes": n_rows * row_bytes,
                    "rows": n_rows,
                    "cols": cols,
                    "sample_row": list(vals)[:12],
                })
                off = off + n_rows * row_bytes
                continue
            off += 2
    # Dedupe overlapping: prefer longer (more rows), then wider (more cols)
    out.sort(key=lambda c: (c["address"], -c["rows"], -c["cols"]))
    dedup = []
    used = []
    for c in out:
        s = c["address"]; e = s + c["length_bytes"]
        if any(not (e <= us or s >= ue) for us, ue in used):
            continue
        dedup.append(c); used.append((s, e))
    return dedup

def scan_float_arrays(data):
    """Monotonic non-zero float runs AND zero-interleaved axes (C4784 style)."""
    out_axis = []
    out_mono = []

    # Pass 1: strictly-monotonic non-zero finite (non-denormal) float runs
    off = SCAN_START
    while off + 4 * MIN_FLOAT_AXIS_LEN <= SCAN_END:
        if off % 4 != 0:
            off += 1; continue
        first = struct.unpack_from("<f", data, off)[0]
        if not looks_like_real_float_nonzero(first):
            off += 4; continue
        run = [first]; cur = off + 4; prev = first
        while cur + 4 <= SCAN_END:
            v = struct.unpack_from("<f", data, cur)[0]
            if not looks_like_real_float_nonzero(v) or v <= prev:
                break
            run.append(v); prev = v; cur += 4
        if len(run) >= MIN_FLOAT_AXIS_LEN:
            out_mono.append({
                "address": off,
                "type": "float_monotonic_array",
                "length_bytes": len(run) * 4,
                "count": len(run),
                "sample": [round(x, 6) for x in run[:12]],
            })
            off = cur; continue
        off += 4

    # Pass 2: zero-interleaved float axes. Run is "all words pass looks_like_real_float
    # (i.e. 0.0 OR clean float), with the non-zero subsequence monotone, and >= 4
    # nonzero entries within a >=8-word window."
    off = SCAN_START
    last_end = SCAN_START
    while off + 4 * 8 <= SCAN_END:
        if off % 4 != 0 or off < last_end:
            off += 4; continue
        run = []; nz = []; cur = off
        while cur + 4 <= SCAN_END:
            v = struct.unpack_from("<f", data, cur)[0]
            if not looks_like_real_float(v):
                break
            if v != 0.0:
                if nz and v <= nz[-1]:
                    break
                nz.append(v)
            run.append(v)
            cur += 4
        if len(nz) >= FLOAT_AXIS_MIN_NONZERO and len(run) >= 8 and (nz[-1] - nz[0]) >= 0.5:
            out_axis.append({
                "address": off,
                "type": "float_interleaved_axis",
                "length_bytes": len(run) * 4,
                "word_count": len(run),
                "nonzero_count": len(nz),
                "sample": [round(x, 6) for x in run[:16]],
                "nonzero_sample": [round(x, 6) for x in nz[:12]],
            })
            last_end = off + len(run) * 4
            off = last_end
            continue
        off += 4

    return out_axis, out_mono

# ---- disambiguation: drop float-as-int16 ghosts ----------------------------

def disambiguate(candidates):
    """Where the same byte range has been classified as both int16-axis and a
    valid float interpretation, the float interpretation wins ONLY IF the float
    interpretation is itself clean (no denormals — already guaranteed by
    looks_like_real_float).

    Conversely, drop float candidates whose ALL bytes are also a perfectly clean
    int16-axis interpretation (this is exceedingly rare but handle it).

    For now: where addresses overlap, prefer floats since the float detector is
    already strict (denormals rejected).
    """
    # Build interval map by type
    intervals = []  # (start, end, type, idx)
    for i, c in enumerate(candidates):
        intervals.append((c["address"], c["address"] + c["length_bytes"], c["type"], i))
    # For every int16 axis candidate, check if it overlaps any float candidate.
    drop = set()
    floats = [iv for iv in intervals if iv[2] in ("float_monotonic_array", "float_interleaved_axis")]
    for s, e, t, i in intervals:
        if t != "int16_monotonic_axis":
            continue
        for fs, fe, ft, fi in floats:
            # Overlap?
            if not (e <= fs or s >= fe):
                # If the float candidate fully contains the int16 candidate, drop int16.
                if fs <= s and e <= fe:
                    drop.add(i)
                    break
                # If the int16 is largely covered by the float (>=80%), drop int16.
                overlap = max(0, min(e, fe) - max(s, fs))
                if overlap >= 0.8 * (e - s):
                    drop.add(i)
                    break
    return [c for i, c in enumerate(candidates) if i not in drop]

# ---- enrichment ------------------------------------------------------------

def enrich(c):
    bs = block_start(c["address"])
    c["block_start"] = bs
    c["block_start_hex"] = f"0x{bs:05X}"
    c["address_hex"] = f"0x{c['address']:05X}"
    c["crc_protected"] = is_protected(c["address"])
    c["guess"] = guess_meaning(c)
    return c

def guess_meaning(c):
    t = c["type"]
    if t == "int16_monotonic_axis":
        s = c.get("sample", [])
        n = c["count"]
        if s and s[0] == 0 and s[-1] > 1500 and n in (8, 10, 12, 13, 16):
            if max(s) > 4000:
                return "candidate breakpoint axis (wide span; torque or speed)"
            return "candidate breakpoint axis"
        if s and abs(s[0]) <= 50 and s[-1] >= 500:
            return "monotonic int16 — likely breakpoint axis"
        return "monotonic int16 — possibly axis or coefficient table"
    if t == "paired_int16_curves":
        adj = c.get("adjacency", "adjacent")
        if adj == "adjacent":
            return "paired Y-rows for 2-input map (byte-adjacent)"
        return f"paired near-identical curves ({adj}; C4A42/C4A6E archetype)"
    if t == "2d_clustered_int16":
        return (f"clustered int16 axes — likely 2D map (rows={c['rows']}, "
                f"cols={c['cols_per_row']}, stride={c['stride']}); first col consistent")
    if t == "2d_repeated_rows_int16":
        if c["rows"] >= 4 and c["cols"] >= 8:
            return "2D map placeholder / uniform-output region (E417E archetype)"
        return "2D map with repeated rows"
    if t == "float_monotonic_array":
        return "monotonic float array — coefficients or float-axis"
    if t == "float_interleaved_axis":
        return "interleaved-zero float axis (C4784 archetype)"
    return "unclassified"

# ---- main ------------------------------------------------------------------

def main():
    with open(CODE_BIN, "rb") as f:
        data = f.read()
    assert len(data) == 0x100000

    axes = scan_int16_axes(data, strict=True)
    pairs_raw = scan_paired_curves(data)
    clusters, clustered_addrs = scan_clustered_axes_as_2d(data, axes)
    maps2d = scan_2d_repeated_rows(data)
    float_axes, float_mono = scan_float_arrays(data)

    # Aggregation precedence (most-aggregating wins):
    #   clusters > 2d_repeated_rows > pairs > standalone-axis
    # Suppress lower-priority candidates whose address falls inside a
    # higher-priority candidate's byte range.

    def inside_any(addr, items):
        for c in items:
            if c["address"] <= addr < c["address"] + c["length_bytes"]:
                return True
        return False

    pairs = [p for p in pairs_raw
             if not inside_any(p["address"], clusters)
             and not inside_any(p["address"], maps2d)]

    paired_addrs = set()
    for p in pairs:
        for a in p["components"]:
            paired_addrs.add(a)

    axes_standalone = [a for a in axes
                       if a["address"] not in paired_addrs
                       and a["address"] not in clustered_addrs
                       and not inside_any(a["address"], pairs)
                       and not inside_any(a["address"], clusters)
                       and not inside_any(a["address"], maps2d)]

    all_cands = []
    for c in axes_standalone: all_cands.append(enrich(c))
    for c in pairs:           all_cands.append(enrich(c))
    for c in clusters:        all_cands.append(enrich(c))
    for c in maps2d:          all_cands.append(enrich(c))
    for c in float_axes:      all_cands.append(enrich(c))
    for c in float_mono:      all_cands.append(enrich(c))

    # Disambiguate float vs int16 ghosts
    all_cands = disambiguate(all_cands)

    all_cands.sort(key=lambda c: (c["address"], c["type"]))

    # Tag verified-map seed candidates
    seed_addrs = {0xC6B66, 0xC4A42, 0xC4A6E, 0xE417E, 0xE41A6, 0xE41CE, 0xE41F6, 0xC4784}
    seed_hit = set()
    for c in all_cands:
        if c["address"] in seed_addrs:
            c["verified_seed"] = True
            seed_hit.add(c["address"])
        # Also flag pair components
        if c["type"] == "paired_int16_curves":
            for a in c.get("components", []):
                if a in seed_addrs:
                    c["verified_seed"] = True
                    seed_hit.add(a)
        if c["type"] == "2d_repeated_rows_int16":
            # E417E pattern spans 4 rows; mark if address range covers seed addrs
            s = c["address"]; e = s + c["length_bytes"]
            for sa in (0xE417E, 0xE41A6, 0xE41CE, 0xE41F6):
                if s <= sa < e:
                    c["verified_seed"] = True
                    seed_hit.add(sa)
        c.setdefault("verified_seed", False)

    stats = {
        "scan_range": [SCAN_START, SCAN_END],
        "scan_range_hex": [f"0x{SCAN_START:05X}", f"0x{SCAN_END:05X}"],
        "int16_axes_standalone": sum(1 for c in all_cands if c["type"] == "int16_monotonic_axis"),
        "paired_int16_curves": sum(1 for c in all_cands if c["type"] == "paired_int16_curves"),
        "two_d_clustered_int16_maps": sum(1 for c in all_cands if c["type"] == "2d_clustered_int16"),
        "two_d_repeated_rows_maps": sum(1 for c in all_cands if c["type"] == "2d_repeated_rows_int16"),
        "float_interleaved_axes": sum(1 for c in all_cands if c["type"] == "float_interleaved_axis"),
        "float_monotonic_arrays": sum(1 for c in all_cands if c["type"] == "float_monotonic_array"),
        "candidates_total": len(all_cands),
        "candidates_in_protected_blocks": sum(1 for c in all_cands if c["crc_protected"]),
        "candidates_in_unprotected_blocks": sum(1 for c in all_cands if not c["crc_protected"]),
        "seed_candidates_total": len(seed_addrs),
        "seed_candidates_hit": len(seed_hit),
        "seed_candidates_missed": sorted(f"0x{a:05X}" for a in (seed_addrs - seed_hit)),
    }

    out = {
        "stats": stats,
        "protected_blocks_in_scope": sorted(f"0x{b:05X}" for b in PROTECTED_BLOCKS),
        "candidates": all_cands,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2)

    print("# Calibration scan summary")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()
    print("addr|type|len|prot|seed|guess")
    for c in all_cands:
        print(f"{c['address_hex']}|{c['type']}|{c['length_bytes']}|"
              f"{'Y' if c['crc_protected'] else 'N'}|"
              f"{'Y' if c['verified_seed'] else 'N'}|{c['guess']}")

    print(f"\nWrote: {OUT_JSON}", file=sys.stderr)

if __name__ == "__main__":
    main()
