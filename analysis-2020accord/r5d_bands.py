#!/usr/bin/env python3
"""Route `5d` (**V74**) -- MDE FIRST, then the band scorecard against the corpus.

🛑 THE ORDER IS DELIBERATE. Route 5d delivered 9 engagement episodes against the flight plan's ~40
and 101 s above 20 m/s against the 480 s asked for. A band ratio quoted without its own minimum
detectable effect invites the reader to treat "inside the null" as "no effect", which on this
exposure is not a distinction the data can make. So section 0 computes, per band and per comparison,
the smallest ratio this route could have resolved at 80% power -- BEFORE any result is printed.

Everything numeric is `_grind2_lib` unchanged (same NFFT 256 windows, same p99 analytic band
envelope, same (eng, v, eff, rate) stratification cells, same episode bootstrap, same split-half
null), so every ratio here is computed with the identical instrument as every prior route.

BANDS, per the standing rule that BOTH symptoms are scored on every build:
    6-9    the micro ratchet (median f0 7.79 Hz, speed-invariant, loop closes inside EPS + plant)
    18-22  grind #1 -- 🛑 a LIMIT CYCLE, so DUTY is the primary metric (see `r5d_duty.py`)
    24-28  the pre-declared negative control
    40-49  grind #2
    1-4    driver input -- the exposure-matching validity check

Usage:  python r5d_bands.py   ->  writes _r5d_bands.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r5d_lib as L  # noqa: E402

RNG = np.random.default_rng(5013)
# `ep` (default) resamples whole engagement RUNS -- 19 of them on this route once runs are cut per
# segment. `blk` resamples ~10.2 s blocks nested inside a run. 🛑 The split-half NULL uses whichever
# is selected, so a ratio is always quoted against a floor computed with the identical estimator.
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "ep"
OUT = {"epkey": G.EPKEY}
print(f"resampling unit: {G.EPKEY}")
KEYS = [("e_6-9", "MICRO RATCHET 6-9 Hz"), ("e_18-22", "GRIND #1   18-22 Hz"),
        ("e_24-28", "CONTROL    24-28 Hz"), ("e_40-49", "GRIND #2   40-49 Hz"),
        ("e_1-4", "DRIVER IN  1-4 Hz")]
CMP = ["V73/r5a", "V72/r59", "V71C/r58", "V71B/r54", "V70/r50", "V69/r4f", "V67/r47", "V68/r4e",
       "V62/r37", "V65/r3b", "V59/r2c", "V58/r2b", "V61/r31"]
CREEP_LO, CREEP = 0.5, 4.0     # 🛑 route 5a's cut exactly (`r5a_score.CREEP`), so the two compare

R = L.records()
CMP = [b for b in CMP if b in R]
# 🛑 `_r5d_lib.PARKED` inherits route 5a's dict and carries NO entry for this route, so the parked
# set is declared here, explicitly, from the per-segment census: segments 2/3/9 read v_max 0.00 /
# 0.00 / 2.15 m/s with 23-100% gear==park and 0% latActive. Segment 0 is KEPT -- it has no
# engagement but it is a real low-speed manoeuvre (40% of samples moving, max 2.90 m/s) and it is
# part of the manual creep control arm.
PARK_5D = [2, 3, 9]
v74 = [r for r in R["V74/r5d"] if r["seg"] not in PARK_5D]
print(f"builds loaded: {len(R)}   V74/r5d windows {len(R['V74/r5d'])} -> {len(v74)} after "
      f"dropping parked segments {PARK_5D}")


def sub(rs, eng=None, vlo=None, vhi=None):
    o = rs
    if eng is not None:
        o = [r for r in o if r["eng"] == eng]
    if vlo is not None:
        o = [r for r in o if r["v"] >= vlo]
    if vhi is not None:
        o = [r for r in o if r["v"] < vhi]
    return o


def nep(rs, key=None):
    return len({r[key or G.EPKEY] for r in rs})


# ================================================================== 0. EXPOSURE ===================
L.hdr("0a. THE EXPOSURE THIS ROUTE ACTUALLY HAS -- windows, episodes and blocks")
print("  `ep` = one contiguous run of the engagement mask (the conservative unit, 9 of them here).")
print("  `blk` = a ~10.2 s block nested inside a run -- more units, still >> the 1-3 s burst")
print("  autocorrelation. Both are reported; every CI below states which it used.\n")
cens = {}
ARMS = [("engaged, ALL speed", dict(eng=1)),
        ("engaged, CREEP < 4 m/s", dict(eng=1, vlo=CREEP_LO, vhi=CREEP)),
        ("engaged, 9.4-12.5 (tyre-CLEAN)", dict(eng=1, vlo=9.4, vhi=12.5)),
        ("engaged, 12.5-18.7 (order-1 DIRTY)", dict(eng=1, vlo=12.5, vhi=18.7)),
        ("engaged, >= 20 (tyre-CLEAN)", dict(eng=1, vlo=20.0)),
        ("manual,  ALL speed", dict(eng=0)),
        ("manual,  CREEP < 4 m/s", dict(eng=0, vlo=CREEP_LO, vhi=CREEP))]
for lab, kw in ARMS:
    rs = sub(v74, **kw)
    cens[lab] = dict(n=len(rs), sec=len(rs) * 1.28, ep=nep(rs, "ep"), blk=nep(rs, "blk"),
                     vmed=float(np.median([r["v"] for r in rs])) if rs else np.nan)
    print(f"  {lab:<36} n={len(rs):>4}  {len(rs) * 1.28:>7.1f} s  ep={nep(rs, 'ep'):>3}  "
          f"blk={nep(rs, 'blk'):>3}  v_med={cens[lab]['vmed']:.2f} m/s")
OUT["census"] = cens

L.hdr("0b. PER-WINDOW SPEED CENSUS -- the necessary-but-not-sufficient check on wheel orders")
print("  🛑 A band-centre test is NOT enough: a moving wheel order (0.489*v Hz) concentrates in a")
print("  narrow-speed route and smears in a wide one. So the per-window speed DISTRIBUTION of every")
print("  arm that enters a cross-route ratio is printed, and the ratios themselves are stratified.\n")
VE = [0, 1, 2, 4, 6.2, 9.4, 12.5, 18.7, 20, 25, 40]
spc = {}
for b in ["V74/r5d"] + CMP:
    rs = sub(R[b] if b != "V74/r5d" else v74, eng=1)
    v = np.array([r["v"] for r in rs], float)
    h = np.histogram(v, bins=VE)[0]
    spc[b] = dict(n=len(v), hist=[int(x) for x in h],
                  frac_order1=float(np.mean((v >= 12.5) & (v < 18.7))),
                  vmed=float(np.median(v)) if len(v) else np.nan)
    print(f"  {b:<10} n={len(v):>5} v_med={spc[b]['vmed']:>5.2f}  "
          f"order-1-dirty {100 * spc[b]['frac_order1']:>5.1f}%   " +
          " ".join(f"{x:>4d}" for x in h))
print("  " + " " * 46 + "bins " + " ".join(f"{e:>4g}" for e in VE[1:]))
OUT["speed_census"] = spc

# ================================================================== 1. MDE ========================
L.hdr("1. ★★ MINIMUM DETECTABLE EFFECT -- computed BEFORE any result, per band and comparison")
print("  Method: run the kit's own stratified log-ratio estimator (episode-resampled, cells =")
print("  (eng, v, eff, rate)) for V74 vs each comparison build, take the SD of the bootstrap draws")
print("  in LOG space, and report")
print("        MDE(80% power, alpha 0.05, two-sided) = exp(2.80 x sd_log).")
print("  🛑 A ratio must ALSO clear the build's own split-half null, so the reported MDE is the")
print("  LARGER of the two. Anything smaller than this is UNDERPOWERED, not null.\n")

mde = {}
for k, kl in KEYS:
    nullp, nlo, nhi = G.split_half_null(v74, k, RNG, nrep=200)
    nullhalf = max(nhi, 1.0 / max(nlo, 1e-9)) if np.isfinite(nlo) and np.isfinite(nhi) else np.nan
    print(f"--- {kl} ---   V74's own split-half null [{nlo:.3f}, {nhi:.3f}] "
          f"=> null-derived floor {nullhalf:.3f}x")
    print(f"    {'vs build':>10} {'sd_log':>7} {'MDE_boot':>9} {'MDE_used':>9} {'cells':>6} "
          f"{'epA':>4} {'epB':>4}")
    for b in CMP:
        pt, lo, hi, nc, na, nb, tab, draws = G.boot_cellwise(v74, R[b], k, RNG, nboot=800)
        if draws is None or not np.isfinite(draws).any():
            print(f"    {b:>10}       -- no shared cell")
            continue
        sd = float(np.nanstd(draws))
        m_b = float(np.exp(2.80 * sd))
        m_u = float(max(m_b, nullhalf)) if np.isfinite(nullhalf) else m_b
        mde[f"{k}|{b}"] = dict(sd_log=sd, mde_boot=m_b, mde_used=m_u, cells=nc, epA=na, epB=nb,
                               null_lo=nlo, null_hi=nhi, point=pt, lo=lo, hi=hi)
        print(f"    {b:>10} {sd:>7.3f} {m_b:>9.3f} {m_u:>9.3f} {nc:>6} {na:>4} {nb:>4}")
    print()
OUT["mde"] = mde

# ================================================================== 2. SCORECARD ==================
L.hdr("2. V74 BAND SCORECARD -- medians with EPISODE-resampled CIs")
sc = {}
for lab, kw in ARMS:
    rs = sub(v74, **kw)
    print(f"\n  {lab}:  n={len(rs)} windows ({len(rs) * 1.28:.0f} s), {nep(rs, 'ep')} episodes, "
          f"{nep(rs, 'blk')} blocks")
    if len(rs) < 12:
        print("     UNPOWERED (<12 windows) -- reported as EXPOSURE, not as a null")
        continue
    for k, kl in KEYS:
        p, lo, hi = G.boot_median_ci(rs, k, RNG, nboot=1200)
        print(f"     {kl:22s} median {p:9.1f}  [{lo:8.1f}, {hi:8.1f}]")
        sc[f"{lab}|{k}"] = [p, lo, hi, len(rs)]
    # the band-relative statement, which is what survives an amplitude-scale question
    for k, kl in (("e_6-9", "6-9"), ("e_18-22", "18-22")):
        v = np.array([r[k] / r["e_24-28"] for r in rs
                      if np.isfinite(r[k]) and r.get("e_24-28", 0) > 0], float)
        if len(v) > 8:
            print(f"     EXCESS over 24-28 control, {kl:>5s}: {np.median(v):.2f}x")
            sc[f"{lab}|excess_{kl}"] = float(np.median(v))
OUT["scorecard"] = sc

# ================================================================== 3. vs CORPUS ==================
L.hdr("3. V74 vs THE CORPUS -- stratified log-ratio, episode-resampled, null and MDE beside it")
print("  ratio > 1 means V74 is WORSE (more band energy). Verdict column:")
print("     BETTER / WORSE -- CI excludes the split-half null")
print("     null           -- inside the null AND |ratio| < MDE  => UNDERPOWERED, not 'no effect'")
print("     flat           -- inside the null but the MDE is cleared => a real absence of effect\n")
res = {}
for k, kl in KEYS:
    nullp, nlo, nhi = G.split_half_null(v74, k, RNG, nrep=250)
    print(f"--- {kl} ---   V74 split-half null [{nlo:.3f}, {nhi:.3f}]")
    print(f"    {'vs build':>10} {'ratio':>7} {'95% CI':>18} {'MDE':>7} {'cells':>6} {'verdict':>9}")
    for b in CMP:
        pt, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(v74, R[b], k, RNG, nboot=1000)
        if not np.isfinite(pt):
            print(f"    {b:>10}       -- no shared cell (UNPOWERED)")
            continue
        m = mde.get(f"{k}|{b}", {}).get("mde_used", np.nan)
        if lo > nhi:
            vd = "WORSE"
        elif hi < nlo:
            vd = "BETTER"
        elif np.isfinite(m) and max(pt, 1 / pt) < m:
            vd = "null"
        else:
            vd = "flat"
        print(f"    {b:>10} {pt:7.3f} [{lo:7.3f}, {hi:7.3f}] {m:>7.3f} {nc:>6} {vd:>9}")
        res[f"{k}|{b}"] = dict(ratio=pt, lo=lo, hi=hi, mde=m, cells=nc, verdict=vd,
                               null_lo=nlo, null_hi=nhi)
    print()
OUT["vs_corpus"] = res

# ================================================================== 4. ENGAGED vs MANUAL ==========
L.hdr("4. ★ THE WITHIN-ROUTE ARM CONTRAST -- and what it can and cannot mean on V74")
print("  ★ V74 writes the ENGAGED COLUMN of all 16 config rows and leaves the disengaged column")
print("  byte-stock, so the MANUAL arm is a genuine byte-stock control FOR LEVERS E'/D'.")
print("  🛑 But the rate lane is UNGATED and identical in both arms, and engagement itself changes")
print("  the plant. So an engaged/manual ratio is (LEVER effect x engagement effect), never a clean")
print("  lever test. It is reported for completeness and read against the SAME contrast on V73,")
print("  where the levers were provably inert -- that difference-in-differences is the usable form.\n")
arm = {}
for lab, base, name in (("V74/r5d", v74, "V74"), ("V73/r5a", R.get("V73/r5a", []), "V73"),
                        ("V72/r59", R.get("V72/r59", []), "V72")):
    if not base:
        continue
    for vlab, kw in (("creep<4", dict(vlo=CREEP_LO, vhi=CREEP)), ("all speed", {})):
        a = sub(base, eng=1, **kw)
        b = sub(base, eng=0, **kw)
        if len(a) < 12 or len(b) < 12:
            print(f"  {name} {vlab:<10} UNPOWERED  (eng n={len(a)}, man n={len(b)})")
            continue
        for k, kl in (("e_6-9", "6-9"), ("e_18-22", "18-22"), ("e_24-28", "24-28")):
            pa = G.boot_median_ci(a, k, RNG, nboot=800)
            pb = G.boot_median_ci(b, k, RNG, nboot=800)
            arm[f"{name}|{vlab}|{k}"] = dict(eng=pa, man=pb,
                                             ratio=float(pa[0] / pb[0]) if pb[0] else np.nan)
            print(f"  {name} {vlab:<10} {kl:>6s} Hz  engaged {pa[0]:8.1f} [{pa[1]:7.1f},{pa[2]:7.1f}]"
                  f"   manual {pb[0]:8.1f} [{pb[1]:7.1f},{pb[2]:7.1f}]   "
                  f"eng/man {pa[0] / max(pb[0], 1e-9):6.2f}x")
        print()
OUT["arms"] = arm

with open(ROOT / f"_r5d_bands_{G.EPKEY}.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _r5d_bands.json")
