#!/usr/bin/env python3
r"""Does an ORDINARY return-to-centre reach the `0xC520C` adaptive-ceiling breakpoints?

THE TABLE (Honda stock, byte-confirmed V37-V74, keyed on motor electrical rate `gp-0x6ac0`):
    X = [1050, 1700, 2500, 3700, 4100]  counts
    Y = [5325, 3584, 2406, 1587,  512]  ceiling -- shared by return-centre (gp-0x6b62) and
                                        LKAS's own in-aggregator term (gp-0x6b4c)

THE QUESTION: if ordinary returns sit below X[0]=1050 the mechanism is real but INERT in the
operator's regime.  If they cross 1050-2500 routinely it explains his complaint.

🛑 THE SCALE IS NOT UNKNOWN -- THE KIT SETTLED IT ON-CAR, AND THE BRIEF UNDERSTATES THAT.
`memory/reference/measurement/reference-accord-rate-scale-4p7121-stands.md`: **`gp-0x6ac0` counts = |column deg/s| x 4.7121**,
arbitrated on-car through V74's bit7 (4.7121 beat 10.0 in 8 of 9 episodes; engaged agreement 84.74 %
vs 82.07 %).  [EVIDENCE] 10.0 disfavoured; [BELIEF] 4.7121 correct.  The same memory records that a
naive fit peaks near 5.8 [5.12, 8.27] but is UPPER-BIASED, because the estimator substitutes column
rate for motor rate.  ⇒ the sweep below runs 4.7121 (settled) .. 10.0 (the disfavoured extreme), and
reports the CRITICAL scale at which the conclusion would flip.

🛑 AND THE PRIOR CLAIM IS SELF-CONTRADICTORY -- checked, not inherited.
`docs/research/FEASIBILITY-8X-LKAS.md` says BOTH of these, in one document:
  Part 1: "measured on-car electrical rate at highway cruise (`gp-0x6ac0` peak 329.8, route 59) sits
           WELL BELOW the adaptive rate-cap's 1050-count onset"
  Part 2: "even at TODAY's 4x, moderately fast steering already clips here"
Part 2's supporting quote ("binds from z~3414") is about the COMMAND magnitude z being clipped once
the ceiling falls below it -- which still requires `gp-0x6ac0` to climb past ~2200.  Part 1 is the
half carrying a measurement.  This file measures the rate directly and settles which is right.

⚠ RATE CHANNEL.  Per the standing rule the `0x18F`-sourced `rate_f` is used.  Its absolute scale has
been described as "~25 % low", which MATTERS for a threshold-crossing question, so §1 cross-calibrates
both bus rate channels against the differentiated ANGLE (0x14A, 0.1 deg/count -- a solid LSB anchor)
before any threshold is applied.

Usage:  python studies/ratchet/v93_return_to_centre.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
sys.path.insert(0, str(ROOT / "_scratch/cache/r73"))

import decode_v90_probe as P          # noqa: E402  -- FROZEN, read-only

OUTJ = ROOT / "analysis-2020accord" / "_scratch/cache/r77" / "v93_return_to_centre.json"
XBP = np.array([1050, 1700, 2500, 3700, 4100], float)
YBP = np.array([5325, 3584, 2406, 1587, 512], float)
SCALES = [4.7121, 5.8, 8.27, 10.0]        # settled .. disfavoured extreme
ANG_MIN = 5.0                              # deg -- a real return, not noise about centre
RATE_MIN = 1.0                             # deg/s
MIN_RUN_S = 0.30
ROUTES = {"77": (ROOT / "analysis-2020accord" / "_scratch/cache/r77", "r77"),
          "73": (ROOT / "_scratch/cache/r73", "r73"),
          "75": (ROOT / "_scratch/cache/r75", "r75"),
          "76": (ROOT / "_scratch/cache/r76", "r76")}
SPEED = [("creep <10 km/h", 0.0, 2.78), ("10-40", 2.78, 11.11), ("40-80", 11.11, 22.22),
         (">=80 km/h", 22.22, 1e9)]


def load(cache, stem):
    z = np.load(cache / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    dt = np.gradient(t)
    dt[dt <= 0] = np.median(dt[dt > 0])
    return dict(t=t, dt=dt, ang=np.asarray(z["ang"], float),
                rate_f=np.asarray(z["rate_f"], float), rate_c=np.asarray(z["rate_c"], float),
                lat=np.asarray(z["cc_lat"], float) > 0.5,
                v=np.abs(np.asarray(z["cs_v"], float)),
                press=np.asarray(z["cs_press"], float) > 0.5)


def calibrate(d, tag):
    """Regress each bus rate channel on the differentiated ANGLE.  Slope 1.00 == same scale."""
    dang = np.gradient(d["ang"]) / d["dt"]
    m = np.abs(dang) > 5.0                       # away from the quantisation floor
    out = {}
    for k in ("rate_f", "rate_c"):
        x, y = dang[m], d[k][m]
        s = float(np.sum(x * y) / np.sum(x * x))
        r = float(np.corrcoef(x, y)[0, 1])
        out[k] = dict(slope=s, r=r, n=int(m.sum()))
        print(f"      {tag} {k:7s} vs d(angle)/dt : slope {s:6.3f}   r {r:6.4f}   n {int(m.sum()):,}")
    return out


RATE_MAG = "rate_c"   # see §1: rate_f reads ~24 % LOW; rate_c is within 4 % of d(angle)/dt


def returns(d, engaged=True):
    """Return-to-centre samples: |angle| large, rate signed OPPOSITE the angle, sustained."""
    sel = (d["lat"] if engaged else ~d["lat"])
    sgn = np.sign(d["ang"])
    ok = sel & (np.abs(d["ang"]) > ANG_MIN) & (sgn * d[RATE_MAG] < 0) & \
        (np.abs(d[RATE_MAG]) > RATE_MIN)
    # enforce a minimum sustained run
    out = np.zeros_like(ok)
    i, n = 0, len(ok)
    need = int(MIN_RUN_S / float(np.median(d["dt"])))
    while i < n:
        if ok[i]:
            j = i
            while j < n and ok[j]:
                j += 1
            if j - i >= need:
                out[i:j] = True
            i = j
        else:
            i += 1
    return out


def pct(x):
    if len(x) < 30:
        return None
    return {f"p{p}": float(np.percentile(x, p)) for p in (50, 75, 90, 99)} | \
        {"max": float(x.max()), "n": int(len(x))}


def seg_of(counts):
    """Which 0xC520C segment, and the ceiling delivered there."""
    return float(np.interp(counts, XBP, YBP, left=YBP[0], right=YBP[-1]))


if __name__ == "__main__":
    OUT = {"table": dict(X=XBP.tolist(), Y=YBP.tolist()), "scales": SCALES}
    print("  0xC520C  X =", XBP.tolist(), " Y =", YBP.tolist())
    print("  breakpoints expressed in COLUMN deg/s, per candidate scale:")
    print(f"      {'scale ct/(°/s)':>16s} " + "".join(f"{f'X{i}':>9s}" for i in range(5)))
    for s in SCALES:
        print(f"      {s:16.4f} " + "".join(f"{x/s:9.1f}" for x in XBP))
    OUT["breakpoints_dps"] = {str(s): (XBP / s).tolist() for s in SCALES}

    print("\n  === 1. RATE-CHANNEL CALIBRATION (settles the '~25 % low' question) ===")
    OUT["calibration"] = {}
    for r, (cache, stem) in ROUTES.items():
        if not (cache / f"{stem}.npz").exists():
            continue
        OUT["calibration"][r] = calibrate(load(cache, stem), f"r{r}")

    print("\n  === 2. RETURN-TO-CENTRE |wheel rate| DISTRIBUTION (deg/s) ===")
    print(f"      definition: |angle| > {ANG_MIN}°, rate signed OPPOSITE the angle, "
          f"|rate| > {RATE_MIN}°/s, sustained >= {MIN_RUN_S}s")
    OUT["returns"] = {}
    allret = {}
    for r, (cache, stem) in ROUTES.items():
        if not (cache / f"{stem}.npz").exists():
            continue
        d = load(cache, stem)
        for arm, eng in (("engaged", True), ("manual", False)):
            m = returns(d, eng)
            x = np.abs(d[RATE_MAG][m])
            q = pct(x)
            if q is None:
                print(f"      r{r} {arm:8s}: n={int(m.sum())} -- too few")
                continue
            OUT["returns"][f"r{r}/{arm}"] = q | {"seconds": float(m.sum() * np.median(d["dt"]))}
            print(f"      r{r} {arm:8s} n={q['n']:6,d} ({m.sum()*np.median(d['dt']):6.1f}s)  "
                  f"p50 {q['p50']:6.1f}  p75 {q['p75']:6.1f}  p90 {q['p90']:6.1f}  "
                  f"p99 {q['p99']:6.1f}  max {q['max']:7.1f}")
            if arm == "engaged":
                allret.setdefault("engaged", []).append(x)
            else:
                allret.setdefault("manual", []).append(x)
        # per speed stratum, engaged, route 77 only (the V90 flight)
        if r == "77":
            m = returns(d, True)
            print(f"      -- r77 engaged returns by speed --")
            for nm, lo, hi in SPEED:
                mm = m & (d["v"] >= lo) & (d["v"] < hi)
                q = pct(np.abs(d[RATE_MAG][mm]))
                if q is None:
                    print(f"         {nm:16s} n={int(mm.sum())} -- too few")
                    continue
                OUT["returns"][f"r77/engaged/{nm}"] = q
                print(f"         {nm:16s} n={q['n']:6,d}  p50 {q['p50']:6.1f}  p90 {q['p90']:6.1f}  "
                      f"p99 {q['p99']:6.1f}  max {q['max']:7.1f}")

    print("\n  === 3. WHOLE-ROUTE |wheel rate| (engaged), for the 'hard fast correction' case ===")
    OUT["allrate"] = {}
    for r, (cache, stem) in ROUTES.items():
        if not (cache / f"{stem}.npz").exists():
            continue
        d = load(cache, stem)
        q = pct(np.abs(d[RATE_MAG][d["lat"]]))
        OUT["allrate"][f"r{r}"] = q
        print(f"      r{r} engaged  p50 {q['p50']:6.1f}  p90 {q['p90']:6.1f}  p99 {q['p99']:6.1f}  "
              f"p99.9 {np.percentile(np.abs(d[RATE_MAG][d['lat']]),99.9):7.1f}  max {q['max']:7.1f}")

    print("\n  === 4. ★ DOES IT BIND?  fraction of ENGAGED RETURN time at or above each "
          "breakpoint ===")
    E = np.concatenate(allret["engaged"])
    print(f"      pooled engaged return samples: {len(E):,}")
    OUT["binding"] = {}
    for s in SCALES:
        counts = E * s
        row = {f"X{i}>={int(x)}ct": float(np.mean(counts >= x)) for i, x in enumerate(XBP)}
        ceil_med = seg_of(float(np.median(counts)))
        ceil_p99 = seg_of(float(np.percentile(counts, 99)))
        OUT["binding"][str(s)] = row | dict(median_counts=float(np.median(counts)),
                                            p99_counts=float(np.percentile(counts, 99)),
                                            ceiling_at_median=ceil_med, ceiling_at_p99=ceil_p99)
        print(f"      scale {s:7.4f}: median {np.median(counts):7.1f} ct -> ceiling {ceil_med:6.0f} "
              f"(full 5325) | p99 {np.percentile(counts,99):7.1f} ct -> ceiling {ceil_p99:6.0f}")
        print(f"                     duty above each X: " +
              "  ".join(f"{k.split('>=')[0]} {v:.5f}" for k, v in row.items()))

    print("\n  === 5. 🛑 THE CRITICAL SCALE — at what ct/(°/s) would the conclusion FLIP? ===")
    OUT["critical"] = {}
    for lbl, q in (("p50 (ordinary return)", 50), ("p90", 90), ("p99", 99),
                   ("max (hardest correction seen)", 100)):
        rate = float(np.max(E)) if q == 100 else float(np.percentile(E, q))
        crit = XBP[0] / rate if rate > 0 else np.inf
        OUT["critical"][lbl] = dict(rate_dps=rate, critical_scale=crit,
                                    factor_over_settled=crit / 4.7121)
        print(f"      {lbl:32s} {rate:7.1f} °/s  ⇒ needs scale >= {crit:8.2f} ct/(°/s) "
              f"= {crit/4.7121:6.2f}x the settled 4.7121")

    print("\n  === 6. 🛑 THE REAL BINDING TEST — a falling ceiling only BINDS once it drops BELOW")
    print("         the command it is capping.  Solving Y(counts) = command for the count, then °/s:")
    OUT["binding_onset"] = {}
    for lbl, cmd in (("LKAS alone at 4x (1782)", 1782.0),
                     ("LKAS + base assist in the aggregate (2229)", 2229.0),
                     ("full governor flat ceiling (4762)", 4762.0)):
        ct = float(np.interp(-cmd, -YBP, XBP))          # Y is DECREASING -> negate to interpolate
        row = {"command": cmd, "counts": ct}
        for s_ in SCALES:
            row[f"dps@{s_}"] = ct / s_
        OUT["binding_onset"][lbl] = row
        print(f"      {lbl:44s} ceiling==cmd at {ct:7.1f} ct  = " +
              "  ".join(f"{ct/s_:6.1f}°/s @{s_}" for s_ in SCALES))
    mx = float(np.max(E))
    print(f"\n      HARDEST return observed across 4 routes: {mx:.1f} °/s"
          f"  ⇒ {mx*4.7121:.0f} ct at the settled scale")
    for lbl, row in OUT["binding_onset"].items():
        need = row["dps@4.7121"]
        print(f"      vs {lbl:44s} needs {need:7.1f} °/s  ⇒ "
              f"{'REACHED' if mx >= need else f'NOT reached ({need/mx:.1f}x short)'}")

    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
