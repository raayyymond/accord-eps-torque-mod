#!/usr/bin/env python3
"""THE RELAY SIGNATURE -- is grind #1's IN-BURST amplitude build-independent?

Two hard nonlinearities have been found in-loop at 1 kHz and are untouched by every build: a
bang-bang relay in the return-to-centre lane (+/-1024 * sgn(motor rate) after 20 ms of low rate)
and a saturating clamp on the friction lane (+/-511). A relay-driven limit cycle has a
CHARACTERISTIC AMPLITUDE set by the relay level and the loop phase at crossover, NOT by the linear
gain ahead of it. So the decisive decomposition is

    median e_18-22  =  DUTY (how often the loop is in limit cycle)  x  IN-BURST AMPLITUDE

  * relay        -> builds differ in DUTY, in-burst amplitude is ~constant across the dose ladder
  * linear gain  -> in-burst amplitude tracks the dose

🛑 The threshold that defines "in burst" must be FIXED across builds or the comparison is circular.
T = 600 counts amplitude (1200 p-p) is used, which is `D3-microratchet`'s own ratchet criterion, so
the two analyses share a cut. A second threshold (T = 1000) is reported as a sensitivity check.

ss3 also asks the bimodality question the lead raised: if the relay latches and unlatches, the
per-window amplitude distribution should be BIMODAL in log space at a shared centre frequency.

Usage: python studies/nearcentre/nearcentre_relay.py [ep|blk] -> writes _scratch/out/_nearcentre_relay.json
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

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402

G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260805)
NBOOT = 3000
OUT = {"epkey": G.EPKEY}

SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["amid"] = abs(0.5 * (r["a_max"] + r["a_min"]) - c)
        r["sb"] = G.binof(r["span"], SP)
ARMS = dict(N.ARMS)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]
# The GRIND-ACTIVE REGIME, from the corpus's own band-pass: the wheel must be moving 8-200 deg
# peak-to-peak inside the window. Outside it the loop is simply not being excited, and pooling that
# in turns a duty question into an exposure question.
ACTIVE = {k: [r for r in v if r["sb"] in (2, 3, 4)] for k, v in ARM.items()}

ORDER = ["POOLED", "V61 (kill)", "stock pool", "V72/r59", "V71C/r58", "V71B/r54", "V62+V65",
         "V69/r4f", "V70/r50", "V67+V68"]


def boot_units(rs, fn, nb=NBOOT):
    """(point, lo, hi) for fn(values), resampling EPISODES/blocks -- never windows."""
    ep = {}
    for r in rs:
        ep.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, "e_18-22") for v in ep.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return (np.nan,) * 3
    allv = np.concatenate(per)
    d = np.full(nb, np.nan)
    for i in range(nb):
        v = np.concatenate([per[j] for j in RNG.integers(0, len(per), len(per))])
        if len(v):
            d[i] = fn(v)
    return float(fn(allv)), float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5))


# ------------------------------------------------------------------ ss1 duty x amplitude ---------
N.hdr("ss1  ★★★ DUTY x IN-BURST AMPLITUDE -- engaged creep, GRIND-ACTIVE regime (span 8-200 deg)")
print("  T = 600 counts amplitude (1200 p-p), the same cut D3 uses for the ratchet. `duty` is the")
print("  fraction of windows above T; `in-burst` is the median AMONG those windows. A relay makes")
print("  duty move with the dose and leaves in-burst amplitude alone.\n")
print(f"  {'arm':<12} {'n':>5} {'blk':>4} {'median all':>11} | {'duty':>6} {'[95% CI]':>15} | "
      f"{'in-burst p50':>13} {'[95% CI]':>17} {'p90/p50':>8} {'IQR/p50':>8}")
res = {}
for T, tag in ((600.0, "T=600"), (1000.0, "T=1000")):
    if T != 600.0:
        print(f"\n  --- sensitivity: {tag}")
        print(f"  {'arm':<12} {'n':>5} {'blk':>4} {'median all':>11} | {'duty':>6} "
              f"{'[95% CI]':>15} | {'in-burst p50':>13} {'[95% CI]':>17} {'p90/p50':>8} "
              f"{'IQR/p50':>8}")
    for k in ORDER:
        rs = ACTIVE.get(k, [])
        nb = len({r[G.EPKEY] for r in rs})
        if len(rs) < 10 or nb < 3:
            print(f"  {k:<12} {len(rs):>5} {nb:>4}   *** UNDERPOWERED / EMPTY")
            res[f"{tag}|{k}"] = dict(n=len(rs), nb=nb, underpowered=True)
            continue
        v = G.col(rs, "e_18-22")
        v = v[np.isfinite(v)]
        burst = [r for r in rs if np.isfinite(r["e_18-22"]) and r["e_18-22"] >= T]
        duty, dlo, dhi = boot_units(rs, lambda x: float(np.mean(x >= T)))
        if len(burst) >= 5 and len({r[G.EPKEY] for r in burst}) >= 3:
            ib, ilo, ihi = boot_units(burst, np.median)
            bv = G.col(burst, "e_18-22")
            r9 = float(np.percentile(bv, 90) / np.median(bv))
            riq = float((np.percentile(bv, 75) - np.percentile(bv, 25)) / np.median(bv))
            istr = f"{ib:>13.0f} [{ilo:>7.0f},{ihi:>8.0f}] {r9:>8.2f} {riq:>8.2f}"
        else:
            ib = ilo = ihi = r9 = riq = np.nan
            istr = f"{'*** ' + str(len(burst)) + ' burst windows -- EMPTY':>50}"
        res[f"{tag}|{k}"] = dict(n=len(rs), nb=nb, med=float(np.median(v)), duty=duty,
                                 dlo=dlo, dhi=dhi, inburst=ib, ilo=ilo, ihi=ihi,
                                 nburst=len(burst), p90p50=r9, iqrp50=riq)
        print(f"  {k:<12} {len(rs):>5} {nb:>4} {np.median(v):>11.0f} | {duty:>6.3f} "
              f"[{dlo:>6.3f},{dhi:>7.3f}] | " + istr)
OUT["duty_amplitude"] = res

# ------------------------------------------------------------------ ss2 dose tracking ------------
N.hdr("ss2  ★★★ WHICH FACTOR TRACKS THE DOSE LADDER? duty vs in-burst amplitude")
print("  The lead's excess-over-control ladder, most-attenuated LAST: V61 12.42, stock 8.77,")
print("  V72 6.40, V71C 4.17, V62+V65 2.82, V67+V68 2.21. Spearman of each factor against it.")
print("  🛑 n = 6 arms, so this is a DIRECTION check, not a calibrated slope.\n")
LADDER_EXC = {"V61 (kill)": 12.42, "stock pool": 8.77, "V72/r59": 6.40, "V71C/r58": 4.17,
              "V62+V65": 2.82, "V67+V68": 2.21}
rows = [(k, LADDER_EXC[k], res.get(f"T=600|{k}", {})) for k in LADDER_EXC]
rows = [(k, e, d) for k, e, d in rows if d and not d.get("underpowered")]
print(f"  {'arm':<12} {'excess':>7} {'median all':>11} {'duty':>7} {'in-burst p50':>13} "
      f"{'n burst':>8}")
for k, e, d in rows:
    print(f"  {k:<12} {e:>7.2f} {d['med']:>11.0f} {d['duty']:>7.3f} "
          + (f"{d['inburst']:>13.0f}" if np.isfinite(d.get("inburst", np.nan))
             else f"{'EMPTY':>13}") + f" {d['nburst']:>8}")


def spear(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 4:
        return np.nan
    ra = np.argsort(np.argsort(a[m]))
    rb = np.argsort(np.argsort(b[m]))
    return float(np.corrcoef(ra, rb)[0, 1])


exc = [e for _, e, _ in rows]
print(f"\n  Spearman(excess, median all)   = {spear(exc, [d['med'] for _, _, d in rows]):>6.3f}")
print(f"  Spearman(excess, DUTY)         = {spear(exc, [d['duty'] for _, _, d in rows]):>6.3f}")
print(f"  Spearman(excess, IN-BURST amp) = "
      f"{spear(exc, [d.get('inburst', np.nan) for _, _, d in rows]):>6.3f}")
ib = np.array([d.get("inburst", np.nan) for _, _, d in rows], float)
ib = ib[np.isfinite(ib)]
if len(ib) >= 2:
    print(f"\n  ** IN-BURST AMPLITUDE ACROSS ARMS: {' / '.join(f'{x:.0f}' for x in ib)}")
    print(f"  ** spread = {ib.max() / ib.min():.2f}x   (the dose ladder itself spans "
          f"{max(exc) / min(exc):.2f}x on the same arms)")
OUT["dose_tracking"] = {k: dict(excess=e, **{kk: vv for kk, vv in d.items()}) for k, e, d in rows}

# ------------------------------------------------------------------ ss3 bimodality ---------------
N.hdr("ss3  ★★ IS THE PER-WINDOW AMPLITUDE DISTRIBUTION BIMODAL? (the latch/unlatch question)")
print("  log10 e_18-22 over engaged-creep GRIND-ACTIVE windows. A latching relay should give two")
print("  lumps; a linear resonance driven by a continuous input should give one.")
print("  Modes counted on a Gaussian KDE with Silverman bandwidth; `dip` = the deepest relative")
print("  trough between the two highest modes (0 = no separation, 1 = fully separated).\n")


def kde_modes(x, grid=400):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 20:
        return None
    h = 1.06 * x.std(ddof=1) * len(x) ** (-0.2)
    if h <= 0:
        return None
    g = np.linspace(x.min() - 3 * h, x.max() + 3 * h, grid)
    d = np.exp(-0.5 * ((g[:, None] - x[None, :]) / h) ** 2).sum(1) / (len(x) * h * np.sqrt(2 * np.pi))
    pk = [i for i in range(1, grid - 1) if d[i] > d[i - 1] and d[i] >= d[i + 1]]
    pk.sort(key=lambda i: -d[i])
    if len(pk) < 2:
        return dict(nmodes=len(pk), modes=[float(10 ** g[i]) for i in pk], dip=0.0)
    a, b = sorted(pk[:2])
    trough = d[a:b + 1].min()
    return dict(nmodes=len(pk), modes=[float(10 ** g[i]) for i in pk[:3]],
                dip=float(1 - trough / min(d[a], d[b])))


print(f"  {'arm':<12} {'n':>5} {'modes':>6} {'mode centres (counts amplitude)':<40} {'dip':>6}")
bim = {}
for k in ORDER:
    rs = ACTIVE.get(k, [])
    v = G.col(rs, "e_18-22")
    v = v[np.isfinite(v) & (v > 0)]
    m = kde_modes(np.log10(v))
    if m is None:
        print(f"  {k:<12} {len(v):>5}   *** UNDERPOWERED (n < 20)")
        continue
    bim[k] = m
    print(f"  {k:<12} {len(v):>5} {m['nmodes']:>6} "
          + ", ".join(f"{x:.0f}" for x in m["modes"]).ljust(40) + f" {m['dip']:>6.3f}")
OUT["bimodality"] = bim

print("\n  --- decile profile of e_18-22 in the grind-active regime (shape, not just centre)")
print(f"  {'arm':<12} " + " ".join(f"{'p' + str(p):>7}" for p in (10, 25, 50, 75, 90, 99)))
for k in ORDER:
    v = G.col(ACTIVE.get(k, []), "e_18-22")
    v = v[np.isfinite(v)]
    if len(v) < 10:
        continue
    print(f"  {k:<12} " + " ".join(f"{np.percentile(v, p):>7.0f}"
                                   for p in (10, 25, 50, 75, 90, 99)))

(HERE.parent / "_scratch/out/_nearcentre_relay.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_relay.json'}")
