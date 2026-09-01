#!/usr/bin/env python3
r"""studies/override_axis/driver_torque_axis_census.py
================================================================================================
THE DISTRIBUTION OF DRIVER TORQUE ON THE OVERRIDE-TAPER'S OWN X AXIS -- re-derived from scratch.

WHY THIS FILE EXISTS.  A prior session reported "median override torque 2235 against a 2240 knot"
and "33-70 % of override time above 2560", and the script behind it could not be found by a later
session.  (It IS in the tree -- `studies/v95-override/v95_override_exposure.py` -- but its cache
autodiscovery globs `<repo>/_cache_r*`, a PRE-2026-08-26-reorg path that no longer exists, so it
now finds ZERO routes and silently prints empty tables.  That is why it read as missing.)  This
file is self-contained: it discovers caches at their CURRENT location and states its own scale.

================================================================================================
THE SCALE CHAIN, end to end.  [EVIDENCE -- re-derived from the image this session, not inherited]
================================================================================================
The taper's X axis is the raw signed firmware cell `gp-0x4f60`.  The EPS transmits that same cell,
scaled, as `STEER_TORQUE_SENSOR` in CAN frame 0x18F/399.  Ghidra, program `code.bin`
(= stock `39990-TVA-A160`), decompiled this session:

    FUN_00055c42 (the 0x18F builder), at 0x55c42:
        FUN_000218be( -(*(short *)(gp + -0x4f60) * 0x7d >> 7) & 0xffff );      // 0x7d = 125
    FUN_000218be, at 0x218be:
        *(ushort *)(gp + -0x1420) = byteswap16(param_1);                      // pure BE store

    => wire_i16be(0x18F bytes 0-1)  =  -( gp_0x4f60 * 125 >> 7 )              [arithmetic shift]

opendbc gives `STEER_TORQUE_SENSOR` factor -1 (`honda_civic_hatchback_ex_2017_can_generated.dbc`,
the DBC `CAR.HONDA_ACCORD` actually maps to), so `carState.steeringTorque` -- and the kit's own `tq`
column, which is `i16be * -1.0` -- carries `+(gp_0x4f60 * 125 >> 7)`.  Inverting:

    ⭐ raw_gp4f60  =  wire_counts * 128 / 125  =  wire_counts * 1.024          (+0/-1 count of floor)

**The wire counts are NOT the firmware's raw counts.  They are 2.34 % SMALL.**  Every threshold in
this file is therefore applied to `raw = tq * 1.024`, and the raw-domain knots are used verbatim.
A study that compares `STEER_TORQUE_SENSOR` directly against a 2240 knot is reading the knot 2.4 %
too far out -- i.e. it under-reports override exposure slightly.

⚠ SENSOR QUANTISATION, reported not swept under the rug.  WITHIN one route the wire signal does not
take every integer -- on r75 its level set is spaced ~9.1 counts (steps of 8/9/10).  But the level
sets of different routes do NOT coincide: pooled over the whole corpus the union is much denser
(median spacing 6, minimum 1).  So this is NOT a fixed sensor quantum; it looks like a per-route
gain/offset on a coarser underlying ADC.  Either way it is not the packing arithmetic above (the
`*125>>7` map alone would make almost every integer reachable), and it is not decision-bearing for
the scale.  What it DOES bound is the resolution of any single-count statement about a knot:
roughly +-5 raw counts, ~0.2 taper-X units.  Section 5 measures this rather than asserting it.

================================================================================================
THE TAPER'S X KNOTS (raw `gp-0x4f60` counts; stored in the image as units of 32)
================================================================================================
    32 -> 1024   48 -> 1536   64 -> 2048   70 -> 2240 (stock knee)   112 -> 3584
    and the V277 candidate 2.5x knee: 175 -> 5600

CHANNEL AND MASK CHOICES, stated
    torque   `tq`  = 0x18F bytes 0-1, i16be * -1.0, INTEGER wire counts.  Chosen over `cs_tq`
             because `cs_tq` is openpilot's carState value RESAMPLED onto the 100 Hz row grid and
             is therefore non-integer (interpolated), which would smear the level set.
    engaged  `cc_lat > 0.5`.  NEVER `cs_eng` (cruiseState) -- see `v95_rez_lib` docstring.
    moving   `|cs_v| > 0.5` m/s.  Reported as a SECOND arm; the primary arm is engaged-only, as
             the brief asks.
    time     each row weighted by the block's median dt (~10 ms).  `tq` rides a ~100 Hz frame on a
             ~100 Hz row grid, so ZOH duplication is negligible; it is NOT corrected for.

CORPUS.  Every cache dir under `_scratch/cache/` carrying the schema.  Where a dir has a
whole-route npz it is used and its per-segment npz are skipped (they are the same samples).  Dirs
with only segments contribute the concatenated segments, kept as separate contiguous blocks so
override runs never bridge a segment boundary.  Exact duplicates (r66/r66.npz vs r66x/r66.npz) are
dropped by content hash.

Usage:  python rlog-tools/studies/override_axis/driver_torque_axis_census.py
        (read-only on every cache; sends nothing anywhere)
"""
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
CACHE = REPO / "_scratch" / "cache"

WIRE_TO_RAW = 128.0 / 125.0          # <- the whole point of this file
NEED = {"t", "cc_lat", "cs_v", "tq", "rate_f"}

KNOTS = [0, 1024, 1536, 2048, 2240, 2560, 3584, 5600]     # band edges, raw counts
OVR = 2240.0                                              # stock taper knee, raw counts
PCTS = [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]

# route -> build, for reporting only.  From `v95_rez_lib.BUILD`, extended with the older segment
# corpora only where the kit records it unambiguously; unknown is printed as "?".
BUILD = {"r5e": "V75", "r61": "V74", "r65": "V76-V38base", "r66": "V80", "r67": "V81",
         "r68": "V83a", "r6d": "V84", "r6e": "V85", "r6f": "V86", "r70": "V86B", "r71": "V87",
         "r73": "V88", "r75": "V89", "r76": "V89"}


# ---------------------------------------------------------------- corpus discovery
def discover():
    """[(route_name, [npz_path, ...]), ...] -- whole-route npz preferred over its own segments."""
    dirs = [p for p in sorted(CACHE.iterdir()) if p.is_dir()]

    def whole_of(d):
        w = [p for p in sorted(d.glob("*.npz"))
             if not re.search(r"s\d+$", p.stem)
             and not p.stem.endswith(("_imu", "_snd", "_rpm"))
             and p.stem in (d.name, d.name.rstrip("x"))]
        return w[:1]

    # A segment-only dir whose base route already has a WHOLE-route npz elsewhere is the same
    # drive sampled twice (r5e_sym vs r5e).  Content hashing does not catch it -- the segment
    # files are genuinely different arrays, just a subset of the same route -- so drop by name.
    have_whole = {d.name for d in dirs if whole_of(d)}
    have_whole |= {d.name.rstrip("x") for d in dirs if whole_of(d)}

    out = []
    for d in dirs:
        npzs = sorted(d.glob("*.npz"))
        if not npzs:
            continue
        if not whole_of(d):
            base = re.sub(r"(_sym|_seg)$", "", d.name).rstrip("x")
            if base in have_whole:
                continue
        # a "whole-route" npz is named exactly <route>.npz with no sNN segment suffix
        whole = whole_of(d)
        if whole:
            out.append((d.name, whole[:1]))
            continue
        # else: segment-only dir.  Group by the non-numeric prefix so v68's 4c*/4e* split.
        groups = defaultdict(list)
        for p in npzs:
            if p.stem.endswith(("_imu", "_snd", "_rpm")):
                continue
            m = re.fullmatch(r"(.*?)s?(\d+)", p.stem)
            groups[m.group(1) if m else p.stem].append(p)
        for g, ps in sorted(groups.items()):
            out.append((f"{d.name}:{g}", sorted(ps, key=lambda x: (len(x.stem), x.stem))))
    return out


def blocks(paths):
    """[(t, tq_wire, engaged, moving)] per contiguous file; skips files missing the schema."""
    got = []
    for p in paths:
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not NEED <= set(z.files):
            continue
        t = np.asarray(z["t"], float)
        if len(t) < 200:
            continue
        got.append((p, t, np.asarray(z["tq"], float),
                    np.asarray(z["cc_lat"], float) > 0.5,
                    np.abs(np.asarray(z["cs_v"], float)),
                    np.asarray(z["rate_f"], float)))
    return got


def runs(mask):
    """[(start, stop_exclusive), ...] of contiguous True."""
    m = mask.astype(np.int8)
    e = np.diff(np.concatenate(([0], m, [0])))
    return list(zip(np.flatnonzero(e == 1), np.flatnonzero(e == -1)))


# ---------------------------------------------------------------- collection
def collect():
    per_route = {}
    seen = set()
    for name, paths in discover():
        bl = blocks(paths)
        if not bl:
            continue
        acc = dict(raw=[], dt=[], mov=[], seg=[], n_files=0, dup=0, nonint=0,
                   raw_blocks=[], src=[])
        for p, t, tq, lat, v, rate in bl:
            h = hashlib.sha256(np.ascontiguousarray(t).tobytes()
                               + np.ascontiguousarray(tq).tobytes()).hexdigest()
            if h in seen:
                acc["dup"] += 1
                continue
            seen.add(h)
            acc["n_files"] += 1
            acc["src"].append(str(p.relative_to(REPO)).replace("\\", "/"))
            if not np.all(tq == np.round(tq)):
                acc["nonint"] += 1
            dt = float(np.median(np.diff(t))) if len(t) > 1 else 0.01
            raw = np.abs(tq) * WIRE_TO_RAW
            for a, b in runs(lat):
                if b - a < 50:
                    continue
                acc["raw_blocks"].append((raw[a:b], v[a:b], dt, rate[a:b]))
        if not acc["raw_blocks"]:
            continue
        per_route[name] = acc
    return per_route


def stats(raw, dt, label, tag=""):
    n = len(raw)
    if n == 0:
        return None
    secs = n * dt
    pc = {p: float(np.percentile(raw, p)) for p in PCTS}
    bands = []
    edges = KNOTS + [np.inf]
    for lo, hi in zip(edges[:-1], edges[1:]):
        bands.append(float(np.mean((raw >= lo) & (raw < hi))))
    return dict(label=label, tag=tag, n=n, secs=secs, pct=pc, max=float(raw.max()),
                bands=bands, mean=float(raw.mean()))


def band_hdr():
    edges = KNOTS + ["inf"]
    return [f"{a}-{b}" for a, b in zip(KNOTS, edges[1:])]


def main():
    print(__doc__.split("Usage:")[0])
    per = collect()
    print(f"\nCORPUS: {len(per)} route groups discovered under {CACHE}\n")

    # ---------------- 1. schema / integrality sanity
    print("=" * 100)
    print("1.  CORPUS AND CHANNEL SANITY")
    print("=" * 100)
    print(f"  {'route':14s} {'build':13s} {'files':>5s} {'dup':>4s} {'noninteger tq':>14s} "
          f"{'engaged blocks':>15s}")
    for name, a in sorted(per.items()):
        b = BUILD.get(name.split(":")[0].rstrip("x"), "?")
        print(f"  {name:14s} {b:13s} {a['n_files']:5d} {a['dup']:4d} {a['nonint']:14d} "
              f"{len(a['raw_blocks']):15d}")

    # ---------------- 2. distribution, engaged
    for armname, movefilter in (("ENGAGED (all)", False), ("ENGAGED + MOVING (|v|>0.5 m/s)", True)):
        print()
        print("=" * 100)
        print(f"2.  |DRIVER TORQUE| IN RAW gp-0x4f60 COUNTS -- {armname}")
        print("=" * 100)
        rows = []
        pooled = []
        pooled_dt = None
        for name, a in sorted(per.items()):
            parts, dt = [], None
            for raw, v, d, _rt in a["raw_blocks"]:
                m = (v > 0.5) if movefilter else np.ones(len(raw), bool)
                if m.sum():
                    parts.append(raw[m])
                    dt = d
            if not parts:
                continue
            r = np.concatenate(parts)
            pooled.append((r, dt))
            s = stats(r, dt, name)
            rows.append(s)
        print(f"  {'route':14s} {'secs':>8s} {'n':>8s} | " +
              " ".join(f"{p:>7s}" for p in ["p1", "p5", "p10", "p25", "p50", "p75", "p90",
                                            "p95", "p99", "p99.9", "max"]))
        for s in rows:
            print(f"  {s['label']:14s} {s['secs']:8.1f} {s['n']:8d} | " +
                  " ".join(f"{s['pct'][p]:7.0f}" for p in PCTS) + f" {s['max']:7.0f}")
        allr = np.concatenate([r for r, _ in pooled])
        alldt = float(np.mean([d for _, d in pooled]))
        S = stats(allr, alldt, "POOLED")
        tot_secs = sum(len(r) * d for r, d in pooled)
        print(f"  {'POOLED':14s} {tot_secs:8.1f} {S['n']:8d} | " +
              " ".join(f"{S['pct'][p]:7.0f}" for p in PCTS) + f" {S['max']:7.0f}")
        print(f"\n  n routes {len(rows)}   total {armname.lower()} seconds {tot_secs:.1f}   "
              f"mean |raw| {S['mean']:.0f}")

        print(f"\n  FRACTION OF {armname} TIME PER TAPER BAND (raw counts):")
        print(f"  {'route':14s} " + " ".join(f"{h:>11s}" for h in band_hdr()))
        for s in rows:
            print(f"  {s['label']:14s} " + " ".join(f"{b:11.4f}" for b in s["bands"]))
        print(f"  {'POOLED':14s} " + " ".join(f"{b:11.4f}" for b in S["bands"]))
        if movefilter:
            pooled_move = (allr, alldt)
        else:
            pooled_eng = (allr, alldt)

    # ---------------- 3. override runs (|raw| >= 2240)
    print()
    print("=" * 100)
    print(f"3.  OVERRIDE = contiguous engaged run with |raw| >= {OVR:.0f}  (the stock taper knee)")
    print("=" * 100)
    print(f"  {'route':14s} {'runs':>6s} {'secs':>8s} {'median s':>9s} {'p90 s':>7s} "
          f"{'max s':>7s} {'frac of eng':>12s}")
    tot_runs, tot_secs, all_len, ovr_samples = 0, 0.0, [], []
    eng_secs_total = 0.0
    for name, a in sorted(per.items()):
        lens, nsamp, esec = [], 0, 0.0
        for raw, v, d, _rt in a["raw_blocks"]:
            esec += len(raw) * d
            m = raw >= OVR
            for s, e in runs(m):
                lens.append((e - s) * d)
                nsamp += e - s
                ovr_samples.append(raw[s:e])
        eng_secs_total += esec
        if not lens:
            continue
        L = np.array(lens)
        tot_runs += len(L)
        tot_secs += L.sum()
        all_len += lens
        print(f"  {name:14s} {len(L):6d} {L.sum():8.1f} {np.median(L):9.3f} "
              f"{np.percentile(L,90):7.3f} {L.max():7.3f} {L.sum()/esec:12.4f}")
    AL = np.array(all_len)
    print(f"  {'TOTAL':14s} {tot_runs:6d} {tot_secs:8.1f} {np.median(AL):9.3f} "
          f"{np.percentile(AL,90):7.3f} {AL.max():7.3f} {tot_secs/eng_secs_total:12.4f}")

    OS = np.concatenate(ovr_samples)
    print(f"\n  WITHIN OVERRIDE TIME ({tot_secs:.1f} s, {len(OS)} frames):")
    print("  " + " ".join(f"{p:>8s}" for p in ["p1", "p5", "p10", "p25", "p50", "p75", "p90",
                                               "p95", "p99", "p99.9", "max"]))
    print("  " + " ".join(f"{np.percentile(OS,p):8.0f}" for p in PCTS)
          + f" {OS.max():8.0f}")
    print(f"\n  FRACTION OF OVERRIDE TIME PER TAPER BAND:")
    edges = KNOTS + [np.inf]
    print("  " + " ".join(f"{h:>11s}" for h in band_hdr()))
    print("  " + " ".join(f"{np.mean((OS>=lo)&(OS<hi)):11.4f}"
                          for lo, hi in zip(edges[:-1], edges[1:])))

    # ---------------- 4. the ceiling
    print()
    print("=" * 100)
    print("4.  THE CEILING -- how far out does driver torque actually GO?")
    print("=" * 100)
    print(f"  {'route':14s} {'max raw':>9s} {'max taperX':>11s} {'p99.99':>8s} "
          f"{'n>=3584':>8s} {'n>=5600':>8s} {'s>=5600':>8s} {'n@top':>6s} {'n@2nd':>6s} "
          f"{'2nd level':>10s} {'rail?':>6s}")
    globmax = 0.0
    for name, a in sorted(per.items()):
        r = np.concatenate([raw for raw, _, _, _ in a["raw_blocks"]])
        u, c = np.unique(np.round(r, 3), return_counts=True)
        top, ntop = u[-1], c[-1]
        sec, nsec = (u[-2], c[-2]) if len(u) > 1 else (np.nan, 0)
        # a rail shows as MANY samples pinned at the extreme value
        rail = ntop >= 20 and ntop > 3 * max(nsec, 1)
        globmax = max(globmax, float(top))
        dtm = float(np.mean([d for _, _, d, _ in a["raw_blocks"]]))
        n36, n56 = int((r >= 3584).sum()), int((r >= 5600).sum())
        print(f"  {name:14s} {top:9.0f} {top/32.0:11.1f} {np.percentile(r,99.99):8.0f} "
              f"{n36:8d} {n56:8d} {n56*dtm:8.2f} {ntop:6d} {nsec:6d} "
              f"{sec:10.0f} {str(bool(rail)):>6s}")
    print(f"\n  ⇒ CORPUS MAX |raw gp-0x4f60| = {globmax:.0f} counts = {globmax/32.0:.1f} taper-X units")
    print(f"    stock knee 2240 (X=70) · V277 candidate 2.5x knee 5600 (X=175)")
    print(f"    fraction of pooled ENGAGED time above 5600: "
          f"{np.mean(pooled_eng[0] >= 5600):.6f}")
    print(f"    fraction of pooled OVERRIDE time above 5600: {np.mean(OS >= 5600):.6f}")

    # ---------------- 5. the sensor level set (resolution of any knot claim)
    print()
    print("=" * 100)
    print("5.  SENSOR LEVEL SET -- the resolution limit on any statement about a knot")
    print("=" * 100)
    r = pooled_eng[0]
    wire = np.unique(np.round(r / WIRE_TO_RAW).astype(np.int64))
    wire = wire[(wire >= 0)]
    d = np.diff(wire)
    print(f"  distinct wire levels (engaged, |tq|): {len(wire)}   "
          f"spacing: min {d.min()} median {np.median(d):.1f} mean {d.mean():.2f} max {d.max()}")
    print(f"  ⇒ raw-count resolution ~ {np.median(d)*WIRE_TO_RAW:.1f} counts "
          f"= {np.median(d)*WIRE_TO_RAW/32:.2f} taper-X units")
    near = wire[(wire * WIRE_TO_RAW > 2100) & (wire * WIRE_TO_RAW < 2400)]
    print(f"  levels bracketing the 2240 knot (raw): "
          f"{[int(round(w*WIRE_TO_RAW)) for w in near]}")

    # ---------------- 6. band-energy proxy for 'symptomatic'
    print()
    print("=" * 100)
    print("6.  BAND-ENERGY PROXY FOR 'SYMPTOMATIC'  [BELIEF -- a band, not an operator score]")
    print("=" * 100)
    print("  The kit has no per-route operator symptom label on disk.  Standing rule: score BANDS,")
    print("  let the OPERATOR score symptoms.  This is a PROXY: engaged 5.12 s windows are ranked by")
    print("  6-9 Hz energy (the ratchet band) and the top/bottom quartiles compared.  It tests the")
    print("  SHAPE of 'applying torque kills the buzz'; it does NOT identify episodes the operator")
    print("  actually complained about.")
    print("")
    print("  THE RANKING CHANNEL MATTERS AND THE OBVIOUS CHOICE IS CIRCULAR.  Ranking windows by")
    print("     6-9 Hz energy OF THE TORSION BAR and then measuring the bar's own amplitude is a")
    print("     self-selection: a window with more torque has more broadband torque energy, so a")
    print("     positive result is guaranteed and means nothing.  Same class as the kit's standing")
    print("     rule 'score the MOTION, never the lever's own output'.  So the PRIMARY ranking here")
    print("     is 6-9 Hz energy of WHEEL RATE (`rate_f`), a different channel.  The circular")
    print("     torque-ranked version is printed too, labelled, purely to show the size of the")
    print("     artifact -- it is NOT evidence.")
    NW = 512
    for chan, tag, note in (("rate", "WHEEL RATE rate_f", "PRIMARY -- not circular"),
                            ("tq", "TORSION BAR |tq|", "CIRCULAR -- artifact demo, not evidence")):
        wins = []
        for name, a_ in sorted(per.items()):
            for raw, v, d, rt in a_["raw_blocks"]:
                sig = rt if chan == "rate" else raw
                for i in range(0, len(raw) - NW + 1, NW // 2):
                    seg = np.asarray(sig[i:i + NW], float)
                    x = seg - seg.mean()
                    X = np.fft.rfft(x * np.hanning(NW))
                    f = np.fft.rfftfreq(NW, d)
                    wins.append((float(np.sum(np.abs(X[(f >= 6) & (f < 9)]) ** 2)),
                                 raw[i:i + NW]))
        if not wins:
            continue
        E = np.array([w[0] for w in wins])
        hi = np.concatenate([w[1] for w in wins if w[0] >= np.percentile(E, 75)])
        lo = np.concatenate([w[1] for w in wins if w[0] <= np.percentile(E, 25)])
        print("")
        print(f"  --- ranked by 6-9 Hz energy of {tag}  [{note}] ---")
        print(f"      {'quartile':10s} {'n':>9s} {'p50':>7s} {'p75':>7s} {'p90':>7s} "
              f"{'p99':>7s} {'max':>7s} {'>=2240':>8s} {'>=5600':>9s}")
        for q, arr in (("TOP 25%", hi), ("BOTTOM 25%", lo)):
            print(f"      {q:10s} {len(arr):9d} " +
                  " ".join(f"{np.percentile(arr,pp):7.0f}" for pp in (50, 75, 90, 99)) +
                  f" {arr.max():7.0f} {np.mean(arr >= OVR):8.4f} {np.mean(arr >= 5600):9.6f}")
        print(f"      windows: {len(wins)}")

    print("\nDONE.  Read-only; nothing was transmitted.")


if __name__ == "__main__":
    main()
