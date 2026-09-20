# -*- coding: utf-8 -*-
"""Stage 5: the exposure-weighted bottom line, and the admissibility census.

1. Per band: the exposure-weighted mean miss (dM_coh), how much of the torque routes' engaged time is in
   cells where torque mode is WORSE than V282, and the same split into its gain / phase / incoherent parts.
2. Per speed bin, pooled over the tracking bands: the same, so "where the gap lives" is one table.
3. The admissibility census: how many cells exist, how many are readable, what each exclusion cost in
   seconds of driving.
4. The worst single regime, with its number.

ANALYSIS ONLY, read-only.  usage: python summary.py > SUMMARY-OUT.txt
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
R = json.load(open(HERE / "ranked.json"))
S = json.load(open(HERE / "surface.json"))
rows = R["rows"]
TRACK = ["0.06-0.15", "0.15-0.30", "0.30-0.60", "0.60-1.20"]
TEXT = ["1.20-2.40", "2.40-4.00"]
SPDN = ["0-8", "8-15", "15-22", "22+"]

print("=" * 128)
print("1. PER BAND, exposure-weighted (weights = torque-mode laterally-engaged seconds in that speed x amp cell)")
print("   dM = M_coh(torque) - M_coh(V282). The gain/phase/incoherent columns are each build's own component.")
print("=" * 128)
print(f"{'band Hz':10s} {'cells':>6s} {'exp cov':>8s} {'w.mean dM':>10s} {'exp% worse':>11s} "
      f"{'|H| V/T':>12s} {'Mgain V/T':>12s} {'Mphase V/T':>12s} {'Minc V/T':>12s} {'M_al V/T':>12s} {'lag V/T ms':>12s}")
for b in TRACK + TEXT:
    g = [r for r in rows if r["band"] == b and "score" in r]
    if not g:
        print(f"{b:10s} {'0':>6s}   no admissible cell"); continue
    w = np.array([r["exp"] for r in g])
    W = w.sum()
    f = lambda k: float(np.average([r[k] for r in g], weights=w))
    worse = sum(r["exp"] for r in g if r["dM"] > 0)
    print(f"{b:10s} {len(g):6d} {W*100:7.1f}% {f('dM'):+10.3f} {worse*100:10.1f}% "
          f"{f('H_v'):5.2f}/{f('H_t'):5.2f} {f('MGv'):5.2f}/{f('MGt'):5.2f} {f('MPv'):5.2f}/{f('MPt'):5.2f} "
          f"{f('iv'):5.2f}/{f('it'):5.2f} {f('MAv'):5.2f}/{f('MAt'):5.2f} {f('lv'):5.0f}/{f('lt'):5.0f}")

print("\n" + "=" * 128)
print("2. PER SPEED BIN, pooled over the TRACKING bands 0.06-1.20 Hz only (1.2-4 Hz excluded: the plan carries")
print("   almost no power there and the 2.4-4 Hz correlation is a zero-lag planner echo, not tracking)")
print("=" * 128)
print(f"{'speed':7s} {'cells':>6s} {'w.mean dM':>10s} {'|H| V/T':>12s} {'Mgain V/T':>12s} {'Mphase V/T':>12s} "
      f"{'M_al V/T':>12s} {'Minc V/T':>12s} {'lag V/T ms':>12s} {'dlag':>6s}")
for sp in SPDN:
    g = [r for r in rows if r["spd"] == sp and r["band"] in TRACK and "score" in r]
    if not g:
        print(f"{sp:7s} {'0':>6s}  no admissible cell in any tracking band"); continue
    w = np.array([r["exp"] for r in g])
    f = lambda k: float(np.average([r[k] for r in g], weights=w))
    print(f"{sp:7s} {len(g):6d} {f('dM'):+10.3f} {f('H_v'):5.2f}/{f('H_t'):5.2f} {f('MGv'):5.2f}/{f('MGt'):5.2f} "
          f"{f('MPv'):5.2f}/{f('MPt'):5.2f} {f('MAv'):5.2f}/{f('MAt'):5.2f} {f('iv'):5.2f}/{f('it'):5.2f} "
          f"{f('lv'):5.0f}/{f('lt'):5.0f} {f('lt')-f('lv'):+6.0f}")

print("\n" + "=" * 128)
print("3. PER AMPLITUDE STRATUM, tracking bands only")
print("=" * 128)
for am in ["A1 <0.3", "A2 .3-1", "A3 >=1"]:
    g = [r for r in rows if r["amp"] == am and r["band"] in TRACK and "score" in r]
    if not g:
        print(f"{am:9s} no admissible cell"); continue
    w = np.array([r["exp"] for r in g])
    f = lambda k: float(np.average([r[k] for r in g], weights=w))
    print(f"{am:9s} cells {len(g):3d}  dM {f('dM'):+.3f}   |H| {f('H_v'):.2f}/{f('H_t'):.2f}   "
          f"Mgain {f('MGv'):.2f}/{f('MGt'):.2f}   Mphase {f('MPv'):.2f}/{f('MPt'):.2f}   "
          f"M_al {f('MAv'):.2f}/{f('MAt'):.2f}   lag {f('lv'):.0f}/{f('lt'):.0f} ms")

print("\n" + "=" * 128)
print("4. ADMISSIBILITY CENSUS")
print("=" * 128)
tot = len(rows)
ok = [r for r in rows if "score" in r]
bad = [r for r in rows if "why" in r]
print(f"   {tot} cells attempted (6 bands x 4 speed bins x 3 amplitude strata). {len(ok)} readable in both builds.")
reason = {}
for r in bad:
    for tagname, key in (("V282 has NO windows at all", "no windows"),
                         ("too few windows (n<6)", "n"), ("below the coherence floor", "coh"),
                         ("not clear of the surrogate", "surr"),
                         ("estimator-variance bias too large", "bias"),
                         ("NON-CAUSAL band (planner echo)", "NONCAUSAL")):
        if key in r["why"]:
            reason.setdefault(tagname, []).append(r)
            break
for k, v in sorted(reason.items(), key=lambda kv: -sum(r["exp"] for r in kv[1])):
    print(f"   {len(v):3d} cells excluded: {k:38s}  (exposure they carry, summed over bands: "
          f"{sum(r['exp'] for r in v)*100:5.1f}%)")
print("\n   THE STRUCTURAL HOLES (no amount of re-analysis fixes these; they need a drive):")
for r in sorted(bad, key=lambda r: -r["exp"]):
    if "no windows" in r["why"] or "n<6" in r["why"] or " n1 " in r["why"] or " n2 " in r["why"]:
        print(f"      {r['band']:10s} {r['spd']:6s} {r['amp']:8s} exposure {r['exp']*100:4.1f}%   {r['why']}")

print("\n" + "=" * 128)
print("5. WORST SINGLE REGIME by exposure-weighted miss, tracking bands only")
print("=" * 128)
g = sorted([r for r in rows if r["band"] in TRACK and "score" in r], key=lambda r: -r["score"])
for r in g[:6]:
    print(f"   {r['band']:10s} {r['spd']:6s} {r['amp']:8s} exposure {r['exp']*100:4.1f}%  score {r['score']:+.4f}  "
          f"dM {r['dM']:+.3f}   |H| {r['H_v']:.2f}->{r['H_t']:.2f}   lag {r['lv']:.0f}->{r['lt']:.0f} ms "
          f"(+{r['lt']-r['lv']:.0f})   M_al {r['MAv']:.2f}->{r['MAt']:.2f}   Minc {r['iv']:.2f}->{r['it']:.2f}")
# collapse to speed x amp over tracking bands
agg = {}
for r in g:
    k = (r["spd"], r["amp"])
    agg.setdefault(k, []).append(r)
print("\n   collapsed to speed x amplitude (mean dM over the tracking bands present, with that cell's exposure):")
for k, v in sorted(agg.items(), key=lambda kv: -np.mean([r["dM"] for r in kv[1]]) * kv[1][0]["exp"]):
    print(f"      v {k[0]:6s} {k[1]:8s} exposure {v[0]['exp']*100:4.1f}%  mean dM {np.mean([r['dM'] for r in v]):+.3f} "
          f"over {len(v)} band(s)  mean dlag {np.mean([r['lt']-r['lv'] for r in v]):+.0f} ms")
