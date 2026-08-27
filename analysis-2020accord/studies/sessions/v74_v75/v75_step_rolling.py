#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_step_rolling.py -- rolling-window duty of RELAY-PLATEAU OCCUPANCY (a PROXY, never fault duty),
against Monitor 2's (FUN_00043e44) leaky-integrator arithmetic.

🛑 EVERY number here is PLATEAU-OCCUPANCY duty, not Monitor-2 fault duty. Monitor 2's real condition
   is a corridor mismatch on the delivered command gp-0x6b98 vs an independently re-derived edge; no
   one has shown the relay makes that exceed +-5/1024. Read every "duty" below as "duty of the proxy".

★ THE SAMPLE-RATE MAPPING IS EXACT, NOT AN APPROXIMATION.
  `FUN_00034350`'s sole caller is `FUN_00022ca0` = the task-5 / 100 Hz entry point, so `gp-0x6bd0` is
  RECOMPUTED AT 100 Hz AND HELD. Monitor 2 runs at 1 kHz, so it observes the SAME held value for
  exactly 10 consecutive cycles. One 100 Hz sample in this cache == 10 Monitor-2 cycles, identically
  valued. The logger's own lattice is fs = 100.0009 Hz (the 0x14A arrival grid, the extractor's
  estimator), so the log grid and the damper's recompute grid are the same grid.
  => window lengths 10/20/30/40/100 ms == 1/2/3/4/10 samples, and a run of k samples == 10k cycles.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import v75_step_lib as L  # noqa: E402

RNG = np.random.default_rng(20260806)
W = 1.0 / 100.0009
CYC = 10                      # Monitor-2 cycles per 100 Hz sample
CHARGE, LEAK, TRIP = 0.001, 0.0005, 0.01
BREAKEVEN = LEAK / (CHARGE + LEAK)          # == 1/3
WINDOWS_MS = [10, 20, 30, 40, 100]


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


D = L.load_route()
n = len(D["t"])
r_signed = np.trunc(np.rint(D["rate_f"] * 10.0) * 2048.0 / 3477.0).astype(np.int64)
r_cts = np.abs(r_signed)
sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
in26, in24, amb = L.mode_masks(D["cc_lat"], D["t"])

hdr("0.  SAMPLE-RATE SANITY CHECK against Monitor 2's 1 kHz")
dt = np.diff(D["t"])
dt = dt[(dt > 0) & (dt < 1)]
print(f"  logger lattice: median dt {np.median(dt)*1e3:.3f} ms   fs {1/np.median(dt):.3f} Hz  "
      f"(extractor's fs_lattice 100.0009 Hz)")
print(f"  gp-0x6bd0 recompute: 100 Hz (FUN_00034350 <- FUN_00022ca0, task 5) and HELD between ticks")
print(f"  => 1 sample = {CYC} Monitor-2 cycles, IDENTICALLY VALUED. Mapping is exact.")
print(f"  break-even duty = leak/(charge+leak) = {LEAK}/({CHARGE}+{LEAK}) = {BREAKEVEN:.4f}")
print(f"  trip needs accumulator >= {TRIP} => {int(TRIP/CHARGE)} consecutive faulted cycles = "
      f"{TRIP/CHARGE/CYC:.0f} of OUR samples.")
print("  🛑 NOTHING BELOW IS FAULT DUTY. It is relay-plateau occupancy, a proxy.")

STRATA = [("ENGAGED overall", in26),
          ("ENGAGED 0-35 km/h", in26 & (sp_cts < 2240)),
          ("ENGAGED creep < 4 m/s", in26 & (D["cs_v"] < 4.0))]
BUILDS = [("V74 (entry 400)", 400), ("V75 (entry 200)", 200)]


def blocks(mask):
    """Contiguous runs of `mask` that do not cross a segment join -- windows must live inside one."""
    m = mask & np.r_[True, np.diff(D["seg"]) == 0]
    idx = np.flatnonzero(m)
    if not len(idx):
        return []
    brk = np.flatnonzero(np.diff(idx) > 1)
    return [r for r in np.split(idx, brk + 1) if len(r)]


def rolling_duty(occ_blocks, k):
    """All length-k rolling windows' duty, pooled, plus each window's block id."""
    out, bid = [], []
    for b, occ in enumerate(occ_blocks):
        if len(occ) < k:
            continue
        c = np.cumsum(np.r_[0, occ.astype(np.int64)])
        d = (c[k:] - c[:-k]) / float(k)
        out.append(d)
        bid.append(np.full(len(d), b))
    if not out:
        return np.array([]), np.array([])
    return np.concatenate(out), np.concatenate(bid)


# ---------------------------------------------------------------------------------------------------
hdr("1-3.  ROLLING-WINDOW DUTY OF PLATEAU OCCUPANCY  [PROXY]  -- and the >1/3 discriminator")
res = {}
for sname, smask in STRATA:
    blks = blocks(smask)
    tot_s = sum(len(b) for b in blks) * W
    print(f"\n  --- {sname}   ({sum(len(b) for b in blks)} frames, {tot_s:.1f} s, "
          f"{len(blks)} contiguous blocks) ---")
    print(f"  {'win':>5s} {'build':>16s} {'nwin':>7s} {'p50':>6s} {'p90':>6s} {'p99':>6s} {'max':>6s}"
          f" | {'>1/3':>7s} {'/s':>7s} | {'>2/3':>7s} {'/s':>7s}")
    for ms in WINDOWS_MS:
        k = int(round(ms / 10.0))
        for bname, entry in BUILDS:
            ob = [(r_cts[b] >= entry) for b in blks]
            d, bid = rolling_duty(ob, k)
            if not len(d):
                continue
            n13 = int((d > BREAKEVEN).sum())
            n23 = int((d > 2 * BREAKEVEN).sum())
            res[(sname, ms, bname)] = dict(n=len(d), p50=float(np.percentile(d, 50)),
                                           p90=float(np.percentile(d, 90)),
                                           p99=float(np.percentile(d, 99)), max=float(d.max()),
                                           n13=n13, n23=n23, per_s_13=n13 / tot_s,
                                           per_s_23=n23 / tot_s)
            print(f"  {ms:5d} {bname:>16s} {len(d):7d} {np.percentile(d,50):6.3f} "
                  f"{np.percentile(d,90):6.3f} {np.percentile(d,99):6.3f} {d.max():6.3f} | "
                  f"{n13:7d} {n13/tot_s:7.3f} | {n23:7d} {n23/tot_s:7.3f}")

print("\n  ⚠ QUANTISATION: with k samples per window the duty can only take k+1 values. At 10 ms")
print("     (k=1) duty is 0 or 1, so '>1/3' and '>2/3' both degenerate to 'occupied'. At 30 ms")
print("     (k=3) '>1/3' means >=2/3. Read the 100 ms row for a graded statistic.")

# ---------------------------------------------------------------------------------------------------
hdr("4.  RUN LENGTHS IN 1 kHz-EQUIVALENT CYCLES -- the DWELL-vs-TRANSITION discriminator")
print(f"  Trip requires {int(TRIP/CHARGE)} consecutive faulted cycles = {int(TRIP/CHARGE/CYC)} sample.")
print("  So EVERY plateau entry lasting >= 1 sample already meets the consecutive-cycle requirement.")
print(f"\n  {'stratum':24s} {'build':>16s} {'runs':>6s} {'med cyc':>8s} {'p90 cyc':>8s} "
      f"{'MAX cyc':>8s} {'runs>=10cyc':>12s} {'total s':>8s}")
runinfo = {}
for sname, smask in STRATA:
    for bname, entry in BUILDS:
        rr = []
        for b in blocks(smask):
            occ = r_cts[b] >= entry
            i = np.flatnonzero(occ)
            if not len(i):
                continue
            br = np.flatnonzero(np.diff(i) > 1)
            rr += [len(x) for x in np.split(i, br + 1)]
        if not rr:
            continue
        rr = np.array(rr) * CYC
        runinfo[(sname, bname)] = rr
        print(f"  {sname:24s} {bname:>16s} {len(rr):6d} {np.median(rr):8.0f} "
              f"{np.percentile(rr,90):8.0f} {rr.max():8.0f} {int((rr>=10).sum()):12d} "
              f"{rr.sum()/CYC*W:8.2f}")

print("\n  ★ THE DISCRIMINATOR, stated explicitly:")
a = runinfo[("ENGAGED overall", "V74 (entry 400)")]
b = runinfo[("ENGAGED overall", "V75 (entry 200)")]
print(f"    V74 engaged: {len(a)} plateau runs, ALL {int((a>=10).sum())} of them >= 10 cycles, "
      f"median {np.median(a):.0f} cycles = {np.median(a)/10:.0f}x the trip requirement, "
      f"max {a.max():.0f} cycles.")
print(f"    V75 engaged: {len(b)} plateau runs, ALL {int((b>=10).sum())} of them >= 10 cycles, "
      f"median {np.median(b):.0f} cycles, max {b.max():.0f} cycles.")
print("    V74 FLEW 1,011 s AND NEVER TRIPPED. If plateau DWELL were the faulted condition, V74")
print(f"    would have tripped on all {len(a)} of its engaged runs (and {int((a>=100).sum())} of them")
print("    exceed the requirement 10-fold). It tripped zero times.")
print("    ⇒ THE DATA POINTS AT THE TRANSITION, NOT THE DWELL. Plateau dwell alone cannot be the")
print("      faulted condition, for either build. [EVIDENCE, conditional on the proxy]")

# ---------------------------------------------------------------------------------------------------
hdr("5.  TRANSITION RATE, and duty in windows CENTRED on each transition")
print(f"  {'stratum':24s} {'build':>16s} {'entries':>8s} {'exits':>7s} {'trans/s':>8s} "
      f"| {'centred 40ms duty p50':>21s} {'p90':>6s} {'>1/3':>7s}")
trans = {}
for sname, smask in STRATA:
    blks = blocks(smask)
    tot_s = sum(len(x) for x in blks) * W
    for bname, entry in BUILDS:
        ents = exs = 0
        cd = []
        for bl in blks:
            occ = (r_cts[bl] >= entry).astype(np.int8)
            d = np.diff(occ)
            ei = np.flatnonzero(d == 1) + 1
            xi = np.flatnonzero(d == -1) + 1
            ents += len(ei)
            exs += len(xi)
            for c in np.r_[ei, xi]:
                lo, hi = c - 2, c + 2          # +-20 ms = a 40 ms window centred on the transition
                if lo < 0 or hi > len(occ):
                    continue
                cd.append(occ[lo:hi].mean())
        cd = np.array(cd) if cd else np.array([0.0])
        trans[(sname, bname)] = dict(ent=ents, ex=exs, per_s=(ents + exs) / tot_s,
                                     cd_p50=float(np.percentile(cd, 50)),
                                     cd_p90=float(np.percentile(cd, 90)),
                                     cd_13=int((cd > BREAKEVEN).sum()))
        print(f"  {sname:24s} {bname:>16s} {ents:8d} {exs:7d} {(ents+exs)/tot_s:8.4f} | "
              f"{np.percentile(cd,50):21.3f} {np.percentile(cd,90):6.3f} "
              f"{int((cd>BREAKEVEN).sum()):7d}")

# ---------------------------------------------------------------------------------------------------
hdr("6.  EPISODE BOOTSTRAP + SPLIT-HALF NULL on the headline ratio (30 ms windows >1/3, engaged)")
eps = L.episodes(D["cc_lat"], D["t"])
print(f"  n episodes = {len(eps)}  (extractor's definition)")
per_ep = []
for e in eps:
    m = np.zeros(n, bool)
    m[e] = True
    m &= in26
    bl = blocks(m)
    c = {}
    for bname, entry in BUILDS:
        ob = [(r_cts[x] >= entry) for x in bl]
        d, _ = rolling_duty(ob, 3)
        c[bname] = int((d > BREAKEVEN).sum()) if len(d) else 0
    per_ep.append((c["V75 (entry 200)"], c["V74 (entry 400)"]))
print(f"  per-episode (V75 n>1/3, V74 n>1/3): {per_ep}")
num = sum(a for a, _ in per_ep)
den = sum(b for _, b in per_ep)
pt = num / den if den else float("inf")
boot = []
for _ in range(20000):
    p = RNG.integers(0, len(eps), len(eps))
    a = sum(per_ep[i][0] for i in p)
    b = sum(per_ep[i][1] for i in p)
    if b:
        boot.append(a / b)
boot = np.array(boot)
print(f"\n  V75/V74 ratio of 30 ms windows >1/3 duty: POINT {pt:.3f}   "
      f"episode bootstrap 95% CI [{np.percentile(boot,2.5):.3f}, {np.percentile(boot,97.5):.3f}]  "
      f"({len(boot)}/20000 draws had V74>0)")
nulls = []
for _ in range(20000):
    perm = RNG.permutation(len(eps))
    h1, h2 = perm[: len(eps) // 2], perm[len(eps) // 2:]
    a1 = sum(per_ep[i][0] for i in h1)
    a2 = sum(per_ep[i][0] for i in h2)
    if a2:
        nulls.append(a1 / a2)
nulls = np.array(nulls)
print(f"  SPLIT-HALF NULL (V75 vs V75, random 4/5 episode split): median {np.median(nulls):.3f}  "
      f"[{np.percentile(nulls,2.5):.3f}, {np.percentile(nulls,97.5):.3f}]")
print(f"  n episodes with V74 > 0: {sum(1 for _,b in per_ep if b)} of {len(eps)}  <- the power limit")
