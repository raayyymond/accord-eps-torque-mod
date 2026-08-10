#!/usr/bin/env python3
"""v89_c1_full_corpus.py -- load EVERY usable route since V38, not just the 12 with a whole-route npz.

v89_a5/a6 used 12 caches and concluded the Lever-B x rate discriminator was exposure-limited.
That was WRONG, and the operator said so: most caches are PER-SEGMENT (`r<NN>s<K>.npz`) and were
skipped entirely by a glob that only matched `r<NN>.npz`. Across all `_cache_*` dirs there are
~2.5 M usable frames (~417 min) against the ~180 min that glob saw.

WHAT THIS FIXES
  * per-segment caches are concatenated, with a per-file segment id (episode blocking needs it)
  * a route present BOTH as a whole-route npz and as segments is loaded ONCE (whole-route wins)
  * `_cache_r66` / `_cache_r66x` are the same route -- deduped by ROUTE key, not by directory
  * `_cache_v68` holds routes 4c/4e under their own stems

ROUTE -> BUILD, and the trick that makes ambiguity harmless
  The discriminator's variable is the LEVER B flag, byte-derived from each build's own image:
      Lever B  <=>  0x3AA96 == 0xFB  AND  0xC6446 == 5244
  Lever B exists only from V67 on. So EVERY pre-V67 route is unambiguously Lever-B = no, whatever
  its exact build. A route is admitted when ALL of its candidate builds AGREE on the flag; routes
  whose candidates straddle it are DROPPED by name, and the drop is printed.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FWD = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
OUT = ROOT / "_cache_r73" / "v89_c1_corpus.npz"

FACTOR_C_PTRS = 0xC9E9C

# Documented build per route. Where the record is ambiguous, ALL plausible builds are listed and
# the route is admitted only if they agree on the Lever-B flag (which pre-V67 they always do).
ROUTE_CANDIDATES = {
    "r28": ["v57"], "r29": ["v57"], "r2b": ["v58"], "r2c": ["v59"],
    "r31": ["v59", "v60", "v61"], "r35": ["v64"], "r37": ["v62"],
    "r3a": ["v65"], "r3b": ["v65"],
    "r47": ["v67"], "4c": ["v68"], "4e": ["v68"],
    "r4a": ["v67", "v69", "v70"],          # straddles -> expected DROP
    "r4f": ["v69"], "r50": ["v70"],
    "r54": ["v70", "v71a", "v71b", "v71c"],  # straddles -> expected DROP
    "r58": ["v71c"], "r59": ["v72"], "r5a": ["v73", "v74"],
    "r5d": ["v74"], "r5e": ["v75"], "r61": ["v74"],
    "r65": ["v76"], "r66": ["v80"], "r67": ["v81"], "r68": ["v83a"],
    "r6d": ["v84"], "r6e": ["v85"], "r6f": ["v86"], "r70": ["v86b"],
    "r71": ["v87"], "r73": ["v88"],
}

NEED = {"t", "tq", "rate_c", "cc_lat", "cs_v", "sstat"}


def build_flags(tag):
    # 🛑 Two naming forms coexist: `_v67_plain_image.bin` (no description) and
    # `_v80_v79base_..._plain_image.bin`. A `_{tag}_*_plain_image.bin` glob silently misses
    # the first form -- it dropped 18 of 32 routes on the first run of this script.
    hits = (sorted(FWD.glob(f"_{tag}_plain_image.bin"))
            or sorted(FWD.glob(f"_{tag}_*_plain_image.bin")))
    if not hits:
        return None
    b = hits[0].read_bytes()
    lever_b = (b[0x3AA96] == 0xFB and struct.unpack_from("<H", b, 0xC6446)[0] == 5244)
    rec = struct.unpack_from("<I", b, FACTOR_C_PTRS + 26 * 4)[0]
    n = struct.unpack_from("<H", b, rec)[0]
    y0 = struct.unpack_from(f"<{n}h", b, rec + 2 + 2 * n)[0]
    return {"lever_b": bool(lever_b), "damper": bool(y0 != 0), "damper_y0": int(y0)}


def route_key(stem):
    """`r73` -> r73 ; `r73s4` -> r73 ; `4cs4` -> 4c ; `r5es0` -> r5e."""
    m = re.match(r"^(r?[0-9a-f]{2}[a-z]?)(?:s(\d+))?$", stem)
    if not m:
        return None, None
    return m.group(1), (int(m.group(2)) if m.group(2) is not None else None)


def collect():
    """route -> list of (path, seg_id). Whole-route file wins over the per-segment set."""
    by_route = {}
    for d in sorted(ROOT.glob("_cache_*")):
        if d.is_file():
            continue
        for f in sorted(d.glob("*.npz")):
            rk, seg = route_key(f.stem)
            if rk is None:
                continue
            by_route.setdefault(rk, {"whole": [], "segs": []})
            (by_route[rk]["whole"] if seg is None else by_route[rk]["segs"]).append((f, seg))
    out = {}
    for rk, v in by_route.items():
        out[rk] = v["whole"][:1] if v["whole"] else v["segs"]
    return out


def main():
    flags = {}
    for tag in {t for v in ROUTE_CANDIDATES.values() for t in v}:
        flags[tag] = build_flags(tag)

    admitted, dropped = {}, {}
    for rt, cands in ROUTE_CANDIDATES.items():
        fl = [flags.get(c) for c in cands]
        if any(f is None for f in fl):
            dropped[rt] = f"no image for {[c for c, f in zip(cands, fl) if f is None]}"
            continue
        lb = {f["lever_b"] for f in fl}
        if len(lb) > 1:
            dropped[rt] = f"candidates straddle Lever B: {cands}"
            continue
        dm = {f["damper"] for f in fl}
        admitted[rt] = {"lever_b": lb.pop(), "damper": (dm.pop() if len(dm) == 1 else None),
                        "builds": cands}

    files = collect()
    print("ROUTES ADMITTED")
    rows, kept = [], []
    for rt, meta in sorted(admitted.items()):
        if rt not in files:
            dropped[rt] = "no cache on disk"
            continue
        n = 0
        for f, seg in files[rt]:
            z = np.load(f, allow_pickle=True)
            if not NEED <= set(z.files):
                continue
            t = np.asarray(z["t"], float)
            fs = 1.0 / float(np.median(np.diff(t)))
            if not (80 < fs < 130):
                continue
            sid = seg if seg is not None else None
            segarr = (np.asarray(z["seg"], int) if (sid is None and "seg" in z.files)
                      else np.full(len(t), sid if sid is not None else 0, int))
            rows.append({
                "route": rt, "lever_b": meta["lever_b"], "damper": meta["damper"],
                "t": t, "tq": np.asarray(z["tq"], float),
                "rate": np.asarray(z["rate_c"], float), "v": np.asarray(z["cs_v"], float),
                "eng": np.asarray(z["cc_lat"], float) > 0.5,
                "sst": np.asarray(z["sstat"], float), "seg": segarr, "fs": fs,
            })
            n += len(t)
        kept.append((rt, meta, n))
        print(f"  {rt:5s} {'/'.join(meta['builds']):22s} LeverB={'YES' if meta['lever_b'] else ' no'} "
              f" damper={'armed' if meta['damper'] else ('Honda' if meta['damper'] is False else '?')} "
              f" {len(files[rt]):3d} npz  {n:7d} frames  {n/6000:5.1f} min")

    print("\nROUTES DROPPED")
    for rt, why in sorted(dropped.items()):
        print(f"  {rt:5s} {why}")

    tot = sum(n for _, _, n in kept)
    nlb = sum(n for _, m, n in kept if m["lever_b"])
    print(f"\nTOTAL {tot} frames = {tot/6000:.0f} min over {len(kept)} routes")
    print(f"  Lever B YES : {nlb/6000:6.1f} min   ({sum(1 for _,m,_ in kept if m['lever_b'])} routes)")
    print(f"  Lever B no  : {(tot-nlb)/6000:6.1f} min   "
          f"({sum(1 for _,m,_ in kept if not m['lever_b'])} routes)")

    np.save(OUT.with_suffix(".npy"), np.array(rows, dtype=object), allow_pickle=True)
    print(f"\nwrote {OUT.with_suffix('.npy')}")


if __name__ == "__main__":
    main()
