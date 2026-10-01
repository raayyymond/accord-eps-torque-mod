# -*- coding: utf-8 -*-
"""c2r2_report.py -- reads the sweep caches and prints every GATE-2 verdict for P2 / F2 (rev2-A) and D2a / B0r (rev2-B).
Bars (the brief): tier A = nominal + single corners, PM >= 45 and GM >= 6 dB; tier B = every combined member and every
member aged +h10, PM >= 30 and GM >= 6 dB; all gated: exact rho < 1, |Tc| and |Tref| 5-30 Hz <= +3 dB, L20 <= V295's.
A strict reading (single corners at the 45-deg bar ALSO with ages 11-20) is reported alongside.  ANALYSIS ONLY."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M  # noqa: E402
import c2r2_sweep as SW  # noqa: E402

OUT = SW.OUT
STOP = {"P2": (0.5, 5.5), "F2": (0.5, 5.5), "D2a": (0.8, 5.5), "B0r": (0.8, 5.5)}   # R3* (rev2-A) / R3 (rev2-B)


def load(dn):
    return json.load(open(OUT / f"sweep_{dn}.json"))


_L20 = {}


def v295_L20(m, v):
    key = (m, v)
    if key not in _L20:
        r, _ = M.lti_metrics(M.V295_REF, M.member(m, v), v)
        _L20[key] = r["L20"]
    return _L20[key]


def summarize(dn):
    rr = load(dn)
    print(f"\n================ {dn}  ({len(rr)} points) ================")
    by = defaultdict(list)
    for r in rr:
        by[r["m"]].append(r)
    fails = []
    print(f"{'member':24s} tier  minPM @v (fc, ring f/zeta)          minGMup  max rho   rho_x2>=1  rho_fade/noI>=1  max Tc/Tr 5-30")
    for m, lst in by.items():
        tier = lst[0]["tier"]
        fin = [x for x in lst if x["pm"] is not None and np.isfinite(x["pm"])]
        w = min(fin, key=lambda x: x["pm"])
        gmin = min(x["gm_up"] for x in lst)
        rmax = max(x["rho"] for x in lst)
        n2 = sum(1 for x in lst if x["rho_x2"] >= 1)
        nf = sum(1 for x in lst if x["rho_fade"] >= 1 or x["rho_noI"] >= 1)
        pk = max(max(x["Tc530"], x["Tr530"]) for x in lst)
        tag = "" if tier != "R" else " (report)"
        print(f"{m:24s} {tier:4s}  {w['pm']:5.1f} @{w['v']:5.2f} ({w['fc']:.2f} Hz, {w['fpole']:.2f}/{w['zeta']:.3f})"
              f"   {gmin:6.1f}  {rmax:.4f}   {n2:4d}       {nf:4d}           {pk:+.1f}{tag}")
        bar = 45.0 if tier == "A" else 30.0
        for x in lst:
            bad = []
            if tier in ("A", "B"):
                if x["pm"] is not None and np.isfinite(x["pm"]) and x["pm"] < bar:
                    bad.append(f"PM<{bar:.0f}")
                if x["gm_up"] < 6.0:
                    bad.append("GM<6")
                if x["rho"] >= 1:
                    bad.append("UNSTABLE")
                if x["rho_x2"] >= 1:
                    bad.append("exactGM<6")
                if max(x["Tc530"], x["Tr530"]) > 3.0:
                    bad.append("peak5-30")
            if bad:
                fails.append((m, tier, x["v"], bad, x["pm"], x["fpole"], x["zeta"]))
    print(f"-- {dn}: GATED fails (brief's tiers): {len(fails)}")
    for f in fails[:60]:
        print("   ", f)
    # strict reading: single corners +h10 at 45
    strict = []
    for m, lst in by.items():
        if m.endswith("+h10") and m[:-4] in SW.SINGLE:
            w = min((x for x in lst if np.isfinite(x["pm"])), key=lambda x: x["pm"])
            if w["pm"] < 45:
                strict.append((m, w["v"], round(w["pm"], 1), round(w["fpole"], 2), round(w["zeta"], 3)))
    print(f"-- {dn}: STRICT reading (single corners with ages 11-20 at the 45-deg bar): {len(strict)} members below 45")
    for s in strict:
        print("   ", s)
    # report members below 30 / unstable, with ring frequency vs this design's stop band
    lo, hi = STOP[dn]
    rep = []
    for m, lst in by.items():
        if lst[0]["tier"] != "R":
            continue
        for x in lst:
            if (np.isfinite(x["pm"]) and x["pm"] < 30) or x["rho"] >= 1:
                rep.append((m, x["v"], x["pm"], x["rho"], x["fpole"], x["zeta"]))
    print(f"-- {dn}: REPORT members with PM < 30 or rho >= 1: {len(rep)} points")
    agg = defaultdict(list)
    for m, v, pm, rho, fp, z in rep:
        agg[m].append((v, pm, rho, fp, z))
    for m, L in agg.items():
        vs = [a[0] for a in L]
        pmin = min(L, key=lambda a: a[1])
        fr = [a[3] for a in L]
        inband = all(lo <= f <= hi for f in fr)
        nun = sum(1 for a in L if a[2] >= 1)
        print(f"    {m:24s} v {min(vs):5.2f}..{max(vs):5.2f} ({len(L)} pts) minPM {pmin[1]:5.1f} @ {pmin[0]} "
              f"unstable {nun}  ring {min(fr):.2f}-{max(fr):.2f} Hz  inside stop band {lo}-{hi} Hz: {inband}")
    # L20 vs V295 on gated members (sampled every 1 m/s to bound runtime)
    worst = (0, None)
    for m, lst in by.items():
        if lst[0]["tier"] == "R":
            continue
        for x in lst:
            if abs(x["v"] - round(x["v"])) > 1e-6:
                continue
            ratio = x["L20"] / v295_L20(m, x["v"])
            if ratio > worst[0]:
                worst = (ratio, (m, x["v"]))
    print(f"-- {dn}: worst L20 / V295 L20 on gated members (1 m/s grid): {worst[0]:.3f} at {worst[1]}")
    return fails, strict, agg


if __name__ == "__main__":
    allres = {}
    for dn in (sys.argv[1:] or ["P2", "F2", "D2a", "B0r"]):
        allres[dn] = summarize(dn)
