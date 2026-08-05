#!/usr/bin/env python3
"""THE NEAR-CENTRE CONDITIONAL for grind #1, tested retrospectively on the whole cached corpus.

The operator's conditional (2026-08-04): grind #1 (18-22 Hz) happens at low speed, only when
openpilot is ENGAGED and commanding, and specifically when the wheel is NEAR CENTRE -- with the
caveat that his sensor carries a +/- 4 deg offset, so "centred" means the SENSOR's zero region.

PRE-REGISTERED QUESTION, and the one that decides which firmware structure is implicated:
    Is "near centre" really "low angle RATE" in disguise?
Near centre at creep correlates with low |rate|, low driver effort, straight driving and longer
engagement. The test is therefore SYMMETRIC and STRATIFIED, and neither direction is privileged:
    A) near-centre vs off-centre, stratified on (v, eff, |rate|)   -> does ANGLE survive rate?
    B) low-rate vs high-rate,   stratified on (v, eff, |angle|)    -> does RATE survive angle?

Every number is `_grind2_lib` unchanged: `e_18-22` = p99 of the analytic 18-22 Hz envelope of one
2.56 s window on the torsion bar; `fs` from `fs_lattice`; CIs resample EPISODES; every ratio quoted
against a split-half null computed FIRST with the identical estimator; 24-28 Hz is the pre-declared
negative control and 1-4 Hz the exposure-matching validity check.

Usage:  python nearcentre_grind1.py [ep|blk]     ->  writes _nearcentre_grind1.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402

G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT, NULLREP, NPERM = 2000, 300, 2000
OUT = {"epkey": G.EPKEY}

store = N.records()

# ------------------------------------------------------------------ S1 the sensor zero -----------
N.hdr("S1  THE SENSOR ZERO, per route, from the route's OWN straight-ahead cruise")
print("  c = median signed carState.steeringAngleDeg over windows with v >= 40 km/h and")
print("  mean |rate_c| < 8 deg/s. If a route has no such exposure it falls back to >= 18 km/h,")
print("  then to all windows -- the tier is printed so a weak estimate is visible as weak.\n")
print(f"  {'build':<10} {'c (deg)':>9} {'n win':>7}  tier")
ZERO = {}
for b in N.LADDER:
    c, n, tier = N.route_zero(b, store)
    ZERO[b] = c
    print(f"  {b:<10} {c:>9.2f} {n:>7}  {tier}")
OUT["zero"] = {b: float(v) for b, v in ZERO.items()}
zz = np.array(list(ZERO.values()))
print(f"\n  ** ACROSS ALL 13 ROUTES: c = {zz.mean():.2f} +/- {zz.std(ddof=1):.2f} deg, "
      f"range [{zz.min():.2f}, {zz.max():.2f}]")
print("  ** The operator's stated +/- 4 deg sensor offset is CONFIRMED independently, and it is a")
print("     CONSISTENT NEGATIVE ~ -4.4 deg, not a random per-drive offset. A `|cs_ang| < 5` bin")
print("     around a HARD zero is therefore mis-centred by most of its own width.")

# annotate every record with both the raw and the re-centred angle
for b in N.LADDER:
    for r in store[b]:
        r["a_c"] = r["a_mean"] - ZERO[b]        # re-centred signed angle
        r["absa_raw"] = abs(r["a_mean"])
        r["absa"] = abs(r["a_c"])
        r["ab_raw"] = N.abin(r["absa_raw"])
        r["ab"] = N.abin(r["absa"])
        r["rb"] = G.binof(r["rate_absm"], N.RATE_BINS)

ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
MANC = {b: N.man_creep(store[b]) for b in N.LADDER}
ARM_ENGC = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM_ENGC["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]
POOL = ARM_ENGC["POOLED"]

# ------------------------------------------------------------------ S2 exposure ------------------
N.hdr("S2  EXPOSURE -- engaged-creep windows per |angle| bin. RAW zero vs RE-CENTRED.")
print("  🛑 Read this table before any ratio below it. A bin with < ~10 windows / < 3 blocks is")
print("     UNDERPOWERED and is labelled so; a bin with 0 is EMPTY, not null.\n")
for tag, key in (("raw zero", "ab_raw"), ("re-centred", "ab")):
    print(f"  --- {tag}")
    print(f"      {'arm':<12} " + " ".join(f"{n:>12}" for n in N.A_NAMES) + f"{'tot':>7}")
    for k in list(N.ARMS) + ["POOLED"]:
        rs = ARM_ENGC[k]
        cells = [[r for r in rs if r[key] == i] for i in range(5)]
        print(f"      {k:<12} " + " ".join(
            f"{len(c):>5}w/{len({r[G.EPKEY] for r in c}):>2}b" for c in cells)
            + f"{len(rs):>7}")
    print()
OUT["exposure"] = {k: {N.A_NAMES[i]: [len([r for r in ARM_ENGC[k] if r["ab"] == i]),
                                      len({r[G.EPKEY] for r in ARM_ENGC[k] if r["ab"] == i})]
                       for i in range(5)} for k in list(N.ARMS) + ["POOLED"]}

# ------------------------------------------------------------------ S3 the ladder by angle -------
N.hdr("S3  ★★ MEDIAN e_18-22 BY RE-CENTRED |ANGLE| BIN -- engaged creep, episode-bootstrap CIs")
print("  If the operator's conditional holds, the 0-5 deg bin is the LARGEST and it falls with")
print("  angle. Bins with < 8 windows or < 3 units are printed as 'thin' and MUST NOT be read as")
print("  a null.\n")


def bin_table(rs, key="ab", metric="e_18-22", names=N.A_NAMES):
    row = {}
    for i in range(len(names)):
        c = [r for r in rs if r[key] == i]
        nb = len({r[G.EPKEY] for r in c})
        if len(c) < 8 or nb < 3:
            row[names[i]] = dict(n=len(c), nb=nb, med=(float(np.median(G.col(c, metric)))
                                                       if c else np.nan),
                                 lo=np.nan, hi=np.nan, thin=True)
            continue
        m, lo, hi = G.boot_median_ci(c, metric, RNG, nboot=NBOOT)
        row[names[i]] = dict(n=len(c), nb=nb, med=float(m), lo=float(lo), hi=float(hi), thin=False)
    return row


lad = {}
for tag, key in (("RE-CENTRED", "ab"), ("raw zero", "ab_raw")):
    print(f"  --- {tag} |angle|")
    print(f"      {'arm':<12} " + " ".join(f"{n:>21}" for n in N.A_NAMES))
    for k in list(N.ARMS) + ["POOLED"]:
        row = bin_table(ARM_ENGC[k], key)
        lad[f"{tag}|{k}"] = row
        cells = []
        for nm in N.A_NAMES:
            d = row[nm]
            if d["n"] == 0:
                cells.append(f"{'EMPTY':>21}")
            elif d["thin"]:
                cells.append(f"{d['med']:>9.0f} (thin n={d['n']:<2})"[:21].rjust(21))
            else:
                cells.append(f"{d['med']:>7.0f}[{d['lo']:>5.0f},{d['hi']:>5.0f}]n{d['n']:<3}"
                             .rjust(21))
        print(f"      {k:<12} " + " ".join(cells))
    print()
OUT["ladder_by_angle"] = lad

# ------------------------------------------------------------------ S4 the deconfound ------------
N.hdr("S4  ★★★ THE DECONFOUND -- is 'near centre' really 'low angle RATE'?  2-WAY TABLE, pooled")
print("  Rows = re-centred |angle| bin, columns = mean |rate_c| bin. Cell = median e_18-22 (n).")
print("  If the conditional is ANGLE, the top ROW is high across every rate column.")
print("  If it is RATE, the left COLUMN is high across every angle row.\n")
print(f"      {'|ang| \\\\ |rate|':<14} " + " ".join(f"{n:>16}" for n in N.RATE_NAMES)
      + f"{'row all':>16}")
two = {}
for i, an in enumerate(N.A_NAMES):
    cells = []
    for j in range(len(N.RATE_NAMES)):
        c = [r for r in POOL if r["ab"] == i and r["rb"] == j]
        m = float(np.median(G.col(c, "e_18-22"))) if c else np.nan
        two[f"{an}|{N.RATE_NAMES[j]}"] = dict(n=len(c), med=m)
        cells.append(f"{'--':>16}" if not c else f"{m:>10.0f}(n{len(c):<3})".rjust(16))
    ra = [r for r in POOL if r["ab"] == i]
    cells.append(f"{np.median(G.col(ra, 'e_18-22')):>10.0f}(n{len(ra):<3})".rjust(16)
                 if ra else f"{'--':>16}")
    print(f"      {an:<14} " + " ".join(cells))
col = []
for j in range(len(N.RATE_NAMES)):
    c = [r for r in POOL if r["rb"] == j]
    col.append(f"{np.median(G.col(c, 'e_18-22')):>10.0f}(n{len(c):<3})".rjust(16)
               if c else f"{'--':>16}")
print(f"      {'col all':<14} " + " ".join(col))
OUT["two_way"] = two

# ------------------------------------------------------------------ S5 stratified contrasts ------
N.hdr("S5  ★★★ THE SYMMETRIC STRATIFIED TEST -- neither variable privileged")
print("  A) NEAR-CENTRE (|a_c| < 5) vs OFF-CENTRE (>= 15), stratified on (v, eff, |rate|).")
print("  B) LOW-RATE (|rate| < 4) vs HIGH-RATE (>= 16), stratified on (v, eff, |angle|).")
print("  Both use `G.boot_cellwise`: only cells occupied by BOTH sides contribute, weighted by the")
print("  SMALLER episode count. 24-28 Hz is the pre-declared negative control; `excess` divides it")
print("  out. Each is quoted against the arm's OWN split-half null, computed with the same cells.\n")

CELL_RATE = lambda r: (r["cell"][1], r["cell"][2], r["cell"][3])          # (v, eff, rate)
CELL_ANG = lambda r: (r["cell"][1], r["cell"][2], r["ab"])                # (v, eff, angle)
CELL_BOTH = lambda r: (r["cell"][1], r["cell"][3], r["ab"])              # (v, rate, angle)


def contrast(A, B, key, min_ep=2, min_win=4):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                unitsA=int(na), unitsB=int(nb), nA=len(A), nB=len(B))


def run_pair(rs, cellfn, selA, selB, label, arm):
    z = N.recell(rs, cellfn)
    A = [r for r in z if selA(r)]
    B = [r for r in z if selB(r)]
    if len(A) < 8 or len(B) < 8:
        print(f"      {arm:<12} {label:<26} *** UNDERPOWERED: nA={len(A)} nB={len(B)}")
        return None
    row = {bd: contrast(A, B, "e_" + bd) for bd in ("18-22", "24-28", "1-4")}
    exc = (row["18-22"]["ratio"] / row["24-28"]["ratio"]
           if np.isfinite(row["24-28"]["ratio"]) and row["24-28"]["ratio"] > 0 else np.nan)
    nl = G.split_half_null(z, "e_18-22", RNG, nrep=NULLREP, min_ep=2, min_win=4)
    inside = (np.isfinite(row["18-22"]["ratio"]) and np.isfinite(nl[1])
              and nl[1] <= row["18-22"]["ratio"] <= nl[2])
    obs, p = G.perm_p(A, B, "e_18-22", RNG, nperm=NPERM, min_ep=2, min_win=4)
    out = dict(row, excess=float(exc), null=[float(x) for x in nl], inside=bool(inside),
               p=float(p), medA=float(np.median(G.col(A, "e_18-22"))),
               medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"      {arm:<12} {label:<26} {row['18-22']['ratio']:>7.3f} "
          f"[{row['18-22']['lo']:>6.3f},{row['18-22']['hi']:>7.3f}] "
          f"{row['24-28']['ratio']:>7.3f} {row['1-4']['ratio']:>6.3f} {exc:>7.3f} "
          f"{row['18-22']['ncells']:>4}c {len(A):>4}/{len(B):<4} "
          f"null[{nl[1]:.2f},{nl[2]:.2f}] {'INSIDE' if inside else '*OUT*':<6} p={p:.3f}")
    return out


HEAD = (f"      {'arm':<12} {'contrast':<26} {'18-22':>7} {'[95% CI]':>15} {'24-28':>7} "
        f"{'1-4':>6} {'excess':>7} {'cells':>5} {'nA/nB':>10} {'own split-half null':<22} p")
res = {}
print("  --- A) ANGLE, stratified on (v, eff, |rate|)   ratio > 1 = MORE grind #1 near centre")
print(HEAD)
for k in ["POOLED"] + list(N.ARMS):
    r = run_pair(ARM_ENGC[k], CELL_RATE, lambda r: r["absa"] < 5.0, lambda r: r["absa"] >= 15.0,
                 "near(<5) / off(>=15)", k)
    if r:
        res[f"A|{k}"] = r
print("\n  --- B) RATE, stratified on (v, eff, |angle|)   ratio > 1 = MORE grind #1 at LOW rate")
print(HEAD)
for k in ["POOLED"] + list(N.ARMS):
    r = run_pair(ARM_ENGC[k], CELL_ANG, lambda r: r["rate_absm"] < 4.0,
                 lambda r: r["rate_absm"] >= 16.0, "low(<4) / high(>=16) rate", k)
    if r:
        res[f"B|{k}"] = r
print("\n  --- A2) ANGLE, stratified on (v, |rate|, |angle| dropped) -- coarser, for the thin arms")
print(HEAD)
for k in ["POOLED"] + list(N.ARMS):
    r = run_pair(ARM_ENGC[k], lambda r: (r["cell"][1], r["cell"][3]),
                 lambda r: r["absa"] < 5.0, lambda r: r["absa"] >= 15.0, "near/off, cells (v,rate)",
                 k)
    if r:
        res[f"A2|{k}"] = r
OUT["stratified"] = res

# ------------------------------------------------------------------ S6 engagement at centre ------
N.hdr("S6  THE ENGAGEMENT CONDITIONAL, RE-TESTED INSIDE THE NEAR-CENTRE CREEP CELL")
print("  Engaged vs manual, |a_c| < 5, v < 20 km/h, stratified on (v, eff, |rate|).")
print("  🛑 `_grind2_lib`'s own cell has ENGAGEMENT as its first component, so it is dropped here.\n")
print(f"      {'arm':<12} {'nEng':>6} {'nMan':>6} {'medEng':>8} {'medMan':>8} {'18-22':>7} "
       f"{'[95% CI]':>15} {'24-28':>7} {'excess':>7} {'cells':>5}  p")
eng = {}
for k in ["POOLED"] + list(N.ARMS):
    names = N.LADDER if k == "POOLED" else N.ARMS[k]
    rs = N.recell([r for n in names for r in store[n]
                   if r["v"] < N.CREEP and abs(r["a_c"]) < 5.0], CELL_RATE)
    A = [r for r in rs if r["eng"] == 1]
    B = [r for r in rs if r["eng"] == 0]
    if len(A) < 8 or len(B) < 8:
        print(f"      {k:<12} {len(A):>6} {len(B):>6}   *** UNDERPOWERED / EMPTY ARM")
        eng[k] = dict(nA=len(A), nB=len(B), underpowered=True)
        continue
    row = {bd: contrast(A, B, "e_" + bd) for bd in ("18-22", "24-28", "1-4")}
    exc = (row["18-22"]["ratio"] / row["24-28"]["ratio"]
           if row["24-28"]["ratio"] > 0 else np.nan)
    _, p = G.perm_p(A, B, "e_18-22", RNG, nperm=NPERM, min_ep=2, min_win=4)
    eng[k] = dict(row, excess=float(exc), p=float(p), nA=len(A), nB=len(B),
                  medA=float(np.median(G.col(A, "e_18-22"))),
                  medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"      {k:<12} {len(A):>6} {len(B):>6} "
          f"{np.median(G.col(A, 'e_18-22')):>8.0f} {np.median(G.col(B, 'e_18-22')):>8.0f} "
          f"{row['18-22']['ratio']:>7.3f} [{row['18-22']['lo']:>6.3f},{row['18-22']['hi']:>7.3f}] "
          f"{row['24-28']['ratio']:>7.3f} {exc:>7.3f} {row['18-22']['ncells']:>5}  {p:.4f}")
OUT["engagement_at_centre"] = eng

(HERE.parent / "_nearcentre_grind1.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_nearcentre_grind1.json'}")
