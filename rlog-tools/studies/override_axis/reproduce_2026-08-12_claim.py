#!/usr/bin/env python3
r"""studies/override_axis/reproduce_2026-08-12_claim.py

Reproduce the 2026-08-12 citation "median override torque = 2235 against a 2240 knot" and
"33-70 % of override time above 2560", so the two can be compared like for like with
`driver_torque_axis_census.py`.

The prior claim used a DIFFERENT definition from the census file:
  * override = openpilot `steeringPressed` = |STEER_TORQUE_SENSOR| > 1200, NOT |torque| >= 2240;
  * the statistic was taken on WIRE counts (`|tq|`), and compared against knots that are in
    RAW `gp-0x4f60` counts.  The two differ by 128/125 (see the census file's scale section).

RESULT (this file, 33 route groups, engaged & pressed & moving):
  * "2235" is EXACTLY route r75's median, not the corpus median.  Corpus median is 2434 wire.
  * "33-70 %" is the per-route spread of `frac(|wire| > 2560)` over the v95 subset; over the
    full corpus here the spread is 0.00-0.66, pooled 0.43.
  * 🛑 In RAW counts r75's median override torque is 2235 * 1.024 = 2289 -- ABOVE the 2240 knot,
    not "one count below" it.  The unit conversion was never applied.

Usage:  python rlog-tools/studies/override_axis/reproduce_2026-08-12_claim.py
        (read-only; sends nothing anywhere)
"""
import hashlib
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / "_scratch" / "cache"
NEED = {"t", "cc_lat", "cs_v", "tq", "cs_press"}
WIRE_TO_RAW = 128.0 / 125.0


def whole_of(d):
    return [p for p in sorted(d.glob("*.npz"))
            if not re.search(r"s\d+$", p.stem)
            and not p.stem.endswith(("_imu", "_snd", "_rpm"))
            and p.stem in (d.name, d.name.rstrip("x"))][:1]


def main():
    print(__doc__)
    dirs = [p for p in sorted(CACHE.iterdir()) if p.is_dir()]
    have = {d.name for d in dirs if whole_of(d)} | {d.name.rstrip("x") for d in dirs if whole_of(d)}
    rows, pooled, seen = [], [], set()
    for d in dirs:
        if not whole_of(d) and re.sub(r"(_sym|_seg)$", "", d.name).rstrip("x") in have:
            continue
        paths = whole_of(d) or [p for p in sorted(d.glob("*.npz"))
                                if not p.stem.endswith(("_imu", "_snd", "_rpm"))]
        seg = []
        for p in paths:
            try:
                z = np.load(p, allow_pickle=True)
            except Exception:
                continue
            if not NEED <= set(z.files):
                continue
            h = hashlib.sha256(np.asarray(z["t"], float).tobytes()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            tq = np.abs(np.asarray(z["tq"], float))
            m = ((np.asarray(z["cc_lat"], float) > 0.5)
                 & (np.asarray(z["cs_press"], float) > 0.5)
                 & (np.abs(np.asarray(z["cs_v"], float)) > 0.5))
            if m.sum():
                seg.append(tq[m])
        if not seg:
            continue
        a = np.concatenate(seg)
        pooled.append(a)
        rows.append((d.name, len(a), float(np.percentile(a, 50)), float(np.mean(a > 2560)),
                     float(np.mean(a * WIRE_TO_RAW >= 2240))))
    rows.sort(key=lambda r: -r[1])
    print(f"{'route':12s} {'n':>8s} {'p50 WIRE':>9s} {'p50 RAW':>9s} "
          f"{'frac wire>2560':>15s} {'frac raw>=2240':>15s}")
    for r in rows:
        print(f"{r[0]:12s} {r[1]:8d} {r[2]:9.0f} {r[2]*WIRE_TO_RAW:9.0f} {r[3]:15.3f} {r[4]:15.3f}")
    A = np.concatenate(pooled)
    print(f"{'POOLED':12s} {len(A):8d} {np.percentile(A,50):9.0f} "
          f"{np.percentile(A,50)*WIRE_TO_RAW:9.0f} {np.mean(A>2560):15.3f} "
          f"{np.mean(A*WIRE_TO_RAW>=2240):15.3f}")
    print(f"\nfrac(wire>2560) spread across routes: "
          f"{min(r[3] for r in rows):.3f} .. {max(r[3] for r in rows):.3f}")


if __name__ == "__main__":
    main()
