#!/usr/bin/env python3
r"""Fix the V91 pre-registration's 26-31 Hz HARM threshold from route 77, BEFORE V91 exists.

🛑 WHY THIS IS NOT TAMPERING.  §10.5(b) of `docs/SCORING-2026-08-11-v90-flight.md` deliberately left
one number open: the threshold above which a sustained 26-31 Hz line counts as harm.  Fixing it from
the REFERENCE build's own frozen data, before the comparison build has flown, is exactly what
pre-registration means.  This file only READS `_cache_r77/records_v90_score.pkl`; it writes nothing
into the frozen cache and modifies no frozen script.

🛑 AND THE THRESHOLD IS CALIBRATED, NOT ASSERTED.  A detector with no measured false-positive rate on
the reference build is not a detector.  This file therefore reports, for every candidate threshold,
how often route 77 ITSELF trips it -- including the run-length distribution, since the criterion is
"N CONSECUTIVE windows above threshold", not "any window".

⚠ WINDOW GEOMETRY.  `_grind2_lib.wrecs` runs NFFT 256 / hop 128 on the ~100 Hz row grid => windows
are ~2.56 s with a ~1.28 s hop, NOT the 5.12 s windows D3/D4 used on the 50 Hz 427 grid.  The
pre-registration must state the criterion in THIS geometry or it is unimplementable.

⚠ WHEEL ORDER REACHES THIS BAND.  Order k lands in [25.2, 31.8] Hz for v in [52.2/k, 66.4/k] m/s:
k=3 -> [17.4, 22.1] m/s and k=4 -> [13.1, 16.6] m/s are both squarely in the driven range.  A
tyre-order line is not a limit cycle, so the detector is calibrated on the order-vetoed subset too.

Usage:  python v91_prereg_threshold.py
"""
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
sys.path.insert(0, str(ROOT / "_cache_r73"))

import decode_v90_probe as P          # noqa: E402  -- FROZEN, imported read-only
import _grind2_lib as G               # noqa: E402

BAND = "26-31"
EKEY, PKEY = f"e_{BAND}", f"p_{BAND}"
HOP_S = 1.28                          # wrecs hop on the ~100 Hz row grid
WIN_S = 2.56                          # wrecs window length


def runs_above(rows, key, thr):
    """Longest and count of runs of CONSECUTIVE windows above `thr`, within a segment.

    Consecutive means adjacent in time inside the same segment with a gap of about one hop.
    """
    by = {}
    for r in rows:
        by.setdefault(int(r["seg"]), []).append(r)
    lengths = []
    for s in sorted(by):
        rs = sorted(by[s], key=lambda r: r["t0"])
        cur = 0
        prev_t = None
        for r in rs:
            contiguous = prev_t is not None and (r["t0"] - prev_t) <= HOP_S * 1.6
            if r[key] > thr and (contiguous or cur == 0):
                cur += 1
            elif r[key] > thr:
                lengths.append(cur)
                cur = 1
            else:
                if cur:
                    lengths.append(cur)
                cur = 0
            prev_t = r["t0"]
        if cur:
            lengths.append(cur)
    lengths = [x for x in lengths if x > 0]
    return dict(n_runs=len(lengths), longest=max(lengths) if lengths else 0,
                n_ge_3=sum(1 for x in lengths if x >= 3),
                n_ge_6=sum(1 for x in lengths if x >= 6),
                span_longest_s=(WIN_S + HOP_S * (max(lengths) - 1)) if lengths else 0.0)


def table(rows, label):
    print(f"\n  === {label}: {len(rows)} engaged windows, {len({r['blk'] for r in rows})} blocks ===")
    out = {}
    for key, name in ((EKEY, "e_26-31 (band envelope, counts)"),
                      (PKEY, "p_26-31 (line PROMINENCE, dimensionless)")):
        v = np.array([r[key] for r in rows], float)
        v = v[np.isfinite(v)]
        q = {p: float(np.percentile(v, p)) for p in (50, 90, 95, 99, 99.9)}
        q["max"] = float(v.max())
        q["n"] = int(len(v))
        out[key] = q
        print(f"    {name}")
        print(f"      n {q['n']:5d}   p50 {q[50]:8.2f}   p90 {q[90]:8.2f}   p95 {q[95]:8.2f}   "
              f"p99 {q[99]:8.2f}   p99.9 {q[99.9]:8.2f}   max {q['max']:8.2f}")
        print(f"      max / p50 = {q['max']/q[50]:.1f}x     "
              f"(V80's event was x92 over the in-band median, sustained ~30 s)")
    return out


def calibrate(rows, key, qs=(99.0, 99.9)):
    print(f"\n    detector calibration on {key} -- how often ROUTE 77 ITSELF trips it")
    print(f"      {'threshold':>26s} {'value':>9s} {'wins above':>11s} {'runs':>6s} "
          f"{'longest':>8s} {'span':>9s} {'runs>=3':>8s}")
    v = np.array([r[key] for r in rows], float)
    res = {}
    for q in qs:
        thr = float(np.percentile(v[np.isfinite(v)], q))
        rr = runs_above(rows, key, thr)
        res[q] = dict(thr=thr, **rr, n_above=int(np.sum(v > thr)))
        print(f"      {'route 77 p'+str(q):>26s} {thr:9.2f} {int(np.sum(v>thr)):11d} "
              f"{rr['n_runs']:6d} {rr['longest']:8d} {rr['span_longest_s']:8.1f}s "
              f"{rr['n_ge_3']:8d}")
    return res


if __name__ == "__main__":
    P.BUILDS["V90/r77"] = P.R77
    rows = [r for r in P._records77() if r["eng"] == 1]
    vet = [r for r in rows if not P.order_hit_any(r, keys=["e_26-31", "e_32-38", "e_18-22"])]
    print("  🛑 READ-ONLY on the frozen `_cache_r77`. Nothing is written into it.")
    print(f"  wrecs geometry: window {WIN_S:.2f} s, hop {HOP_S:.2f} s "
          f"(NFFT 256 / hop 128 at ~100 Hz)")

    a = table(rows, "ROUTE 77, all engaged")
    ca = calibrate(rows, PKEY)
    cae = calibrate(rows, EKEY)

    print(f"\n  order-vetoed subset: {len(vet)}/{len(rows)} windows survive "
          f"(orders 1-6 reach 26-31 Hz at 13.1-16.6 and 17.4-22.1 m/s)")
    b = table(vet, "ROUTE 77, engaged + symmetric order veto")
    cb = calibrate(vet, PKEY)
    cbe = calibrate(vet, EKEY)

    print("\n  " + "=" * 100)
    print("  PRE-REGISTERED THRESHOLDS FOR §10.5(b), fixed 2026-08-11 from route 77 alone:")
    print(f"    prominence p99   = {ca[99.0]['thr']:.2f}   p99.9 = {ca[99.9]['thr']:.2f}   "
          f"(all engaged)")
    print(f"    prominence p99   = {cb[99.0]['thr']:.2f}   p99.9 = {cb[99.9]['thr']:.2f}   "
          f"(order-vetoed)")
    print(f"    envelope   p99   = {cae[99.0]['thr']:.2f}   p99.9 = {cae[99.9]['thr']:.2f}   "
          f"(all engaged)")
    print("  " + "=" * 100)
