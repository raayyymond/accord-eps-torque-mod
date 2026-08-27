#!/usr/bin/env python3
r"""AUDIT: the `z["t"]` vs `z["raw14_b4"]` off-by-one, found by `r73-extract` 2026-08-09.

THE DEFECT
    `decode_v84_probe_r6d.extract()` appends to `raw14_t` / `raw14_b4` on EVERY 0x14A frame, but only
    appends a ROW (`t`, `probe`, ...) once a 0x18F has been seen.  The first 0x14A arrives before the
    first 0x18F, so the row arrays are exactly ONE SAMPLE SHORTER:

        z["t"]     == z["raw14_t"][1:]
        z["probe"] == z["raw14_b4"][1:]

    Any analysis that computes indices on `t` and then indexes `raw14_b4` with them reads every byte
    one 0x14A frame (~10 ms) EARLY.  Measured cost on the V88 identity test: 0.9437 instead of 0.9654.

WHAT THIS SCRIPT DOES
    1. Confirms the invariant on every cache on disk, so the defect's extent is EVIDENCE not belief.
    2. Flags source files that mention `raw14_b4` AND derive an index from `t` -- candidates for the
       same mistake, for human review.  A mention alone is NOT a defect: the extractors legitimately
       WRITE the array, and pairing `raw14_t` with `raw14_b4` is correct.
"""
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")

print("=" * 78)
print("1. THE INVARIANT, on every cache on disk")
print("=" * 78)
bad = ok = 0
for d in sorted(ROOT.glob("_cache_r*")):
    for f in sorted(d.glob("r*.npz")):
        if re.search(r"s\d+\.npz$", f.name) or "_1ab" in f.name:
            continue                                    # per-segment / tap files, not row caches
        try:
            z = np.load(f, allow_pickle=True)
            k = set(z.keys())
            if not {"t", "raw14_t", "raw14_b4", "probe"} <= k:
                continue
            t, rt = z["t"], z["raw14_t"]
            pr, rb = z["probe"], z["raw14_b4"]
            off = len(rt) - len(t)
            shifted = (off == 1 and len(pr) == len(rb) - 1
                       and np.array_equal(pr, rb[1:]) and np.allclose(t, rt[1:]))
            if shifted:
                bad += 1
                print(f"  {f.parent.name}/{f.name:14s} rows {len(t):>6,}  raw {len(rt):>6,}  "
                      f"offset +{off}  ⇒ t==raw14_t[1:] and probe==raw14_b4[1:]  CONFIRMED")
            else:
                ok += 1
                print(f"  {f.parent.name}/{f.name:14s} rows {len(t):>6,}  raw {len(rt):>6,}  "
                      f"offset +{off}  ⇒ NOT the standard shift — inspect")
        except Exception as exc:
            print(f"  {f.parent.name}/{f.name:14s} unreadable: {exc}")
print(f"\n  caches showing the +1 shift: {bad}   caches not matching the pattern: {ok}")

print("\n" + "=" * 78)
print("2. SOURCE FILES THAT MENTION raw14_b4 AND ALSO DERIVE AN INDEX FROM t")
print("   (a mention alone is not a defect -- extractors WRITE it, and raw14_t+raw14_b4 is correct)")
print("=" * 78)
IDX = re.compile(r"searchsorted|np\.interp|\[\s*idx\s*\]|\[\s*pick\s*\]|digitize")
hits = 0
for f in sorted(ROOT.rglob("*.py")):
    try:
        src = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "raw14_b4" not in src:
        continue
    uses_t = re.search(r'\[\s*["\']t["\']\s*\]', src) is not None
    uses_idx = IDX.search(src) is not None
    writes_only = 'raw14_b4"] =' in src or "raw14_b4=" in src or "raw14_b4\"]=" in src
    if uses_t and uses_idx:
        hits += 1
        tag = "  (also writes the array -- likely the extractor itself)" if writes_only else ""
        print(f"  ⚠ REVIEW  {f.relative_to(ROOT)}{tag}")
print(f"\n  files to review: {hits}")
print("\n🛑 The safe pairings are  (t, probe)  and  (raw14_t, raw14_b4).  Never cross the families.")
