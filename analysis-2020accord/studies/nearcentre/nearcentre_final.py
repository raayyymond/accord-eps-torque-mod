#!/usr/bin/env python3
"""THE THREE THINGS THE FIRST THREE SCRIPTS LEFT OPEN.

ss1  DOES THE NEAR-CENTRE CONTRAST DECOMPOSE?  `studies/nearcentre/nearcentre_deconfound.py` ss2 showed the angle
     ladder is FLAT over 0-45 deg inside every rate stratum and only collapses beyond ~45 deg. So
     the 4x "near vs off" ratio may be entirely the >45 deg arm. Split it:
        (a) 0-5 vs 15-45   -- the operator's conditional PROPER
        (b) 0-45 vs 45+    -- "not during a big turn"
     Both at matched manoeuvre rate, per arm, so replication is visible.

ss2  IS THE 25 mph CEILING REALLY A RATE CEILING?  Grind #1 needs a manoeuvre rate of ~4-32 deg/s.
     You do not steer at 20 deg/s on the highway. So the speed ladder must be re-read INSIDE a
     fixed rate stratum -- if it flattens, the "gone above 25 mph" report is a rate conditional
     wearing a speed costume, and no firmware speed breakpoint is implicated at all.

ss3  THE MICRO-RATCHET BAND, WITH A NARROW PROMINENCE FLOOR.  The 8 Hz ratchet is 20-30x its local
     floor, and `G.prom_spectrum`'s default 6 Hz half-window means the ratchet raises the floor for
     everything from 2 to 14 Hz -- a weak second line next to it would be hidden by construction.
     Re-swept with halfwin 2.5 Hz / exclude 0.8 Hz, plus the ENGAGED/MANUAL power ratio per bin,
     which is the kit's own engagement-conditional test.

Usage: python studies/nearcentre/nearcentre_final.py [ep|blk]  -> writes _scratch/out/_nearcentre_final.json
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
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
import _r58_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT = 2000
OUT = {"epkey": G.EPKEY}

RB2 = [(0.0, 4.0), (4.0, 16.0), (16.0, 32.0), (32.0, 64.0), (64.0, 128.0), (128.0, 1e9)]
store = N.records()
for b in N.LADDER:
    c = N.route_zero(b, store)[0]
    for r in store[b]:
        r["a_c"] = r["a_mean"] - c
        r["absa"] = abs(r["a_c"])
        r["ab"] = N.abin(r["absa"])
        r["rb2"] = G.binof(r["rate_lp"], RB2)
ENGC = {b: N.eng_creep(store[b]) for b in N.LADDER}
ARM = {k: [r for n in v for r in ENGC[n]] for k, v in N.ARMS.items()}
ARM["POOLED"] = [r for b in N.LADDER for r in ENGC[b]]

# ------------------------------------------------------------------ ss1 decomposition ------------
N.hdr("ss1  ★★★ DOES 'NEAR CENTRE' DECOMPOSE INTO 'NOT A BIG TURN'?")
print("  Both contrasts stratified on (v bin, eff bin, manoeuvre-rate bin) via `G.boot_cellwise`,")
print("  which contributes only cells occupied by BOTH sides and weights by the smaller episode")
print("  count. Each is quoted against the arm's own split-half null with the same cells.\n")


def contrast(rs, selA, selB, label, arm, cellfn):
    z = N.recell(rs, cellfn)
    A = [r for r in z if selA(r)]
    B = [r for r in z if selB(r)]
    ua, ub = len({r[G.EPKEY] for r in A}), len({r[G.EPKEY] for r in B})
    if len(A) < 6 or len(B) < 6:
        print(f"      {arm:<12} {label:<22} *** UNDERPOWERED nA={len(A)} nB={len(B)} "
              f"(units {ua}/{ub})")
        return dict(nA=len(A), nB=len(B), uA=ua, uB=ub, underpowered=True)
    r18 = G.boot_cellwise(A, B, "e_18-22", RNG, nboot=NBOOT, min_ep=2, min_win=4)
    r24 = G.boot_cellwise(A, B, "e_24-28", RNG, nboot=NBOOT, min_ep=2, min_win=4)
    nl = G.split_half_null(z, "e_18-22", RNG, nrep=200, min_ep=2, min_win=4)
    _, p = G.perm_p(A, B, "e_18-22", RNG, nperm=1500, min_ep=2, min_win=4)
    exc = r18[0] / r24[0] if np.isfinite(r24[0]) and r24[0] > 0 else np.nan
    inside = np.isfinite(nl[1]) and np.isfinite(r18[0]) and nl[1] <= r18[0] <= nl[2]
    print(f"      {arm:<12} {label:<22} {r18[0]:>7.3f} [{r18[1]:>6.3f},{r18[2]:>8.3f}] "
          f"{r24[0]:>7.3f} {exc:>7.3f} {r18[3]:>4}c {len(A):>4}/{len(B):<4} "
          f"[{nl[1]:.2f},{nl[2]:.2f}] {'INSIDE' if inside else '*OUT*':<6} p={p:.3f}")
    return dict(nA=len(A), nB=len(B), uA=ua, uB=ub, ratio=float(r18[0]), lo=float(r18[1]),
                hi=float(r18[2]), ncells=int(r18[3]), r2428=float(r24[0]), excess=float(exc),
                null=[float(x) for x in nl], inside=bool(inside), p=float(p),
                medA=float(np.median(G.col(A, "e_18-22"))),
                medB=float(np.median(G.col(B, "e_18-22"))))


CELL = lambda r: (r["cell"][1], r["cell"][2], r["rb2"])
HEAD = (f"      {'arm':<12} {'contrast':<22} {'18-22':>7} {'[95% CI]':>16} {'24-28':>7} "
        f"{'excess':>7} {'cells':>5} {'nA/nB':>10} {'own null':<14} p")
dec = {}
for lab, sa, sb in (("(a) 0-5 vs 15-45", lambda r: r["absa"] < 5, lambda r: 15 <= r["absa"] < 45),
                    ("(b) 0-45 vs 45+", lambda r: r["absa"] < 45, lambda r: r["absa"] >= 45),
                    ("(c) 0-15 vs 15-45", lambda r: r["absa"] < 15,
                     lambda r: 15 <= r["absa"] < 45)):
    print(f"  --- {lab}   ratio > 1 = MORE grind #1 in arm A")
    print(HEAD)
    for k in ["POOLED"] + list(N.ARMS):
        dec[f"{lab}|{k}"] = contrast(ARM[k], sa, sb, lab, k, CELL)
    print()
OUT["decompose"] = dec

# ------------------------------------------------------------------ ss2 speed inside rate --------
N.hdr("ss2  ★★★ IS THE SPEED CEILING A RATE CEILING? -- the speed ladder INSIDE a rate stratum")
print("  Pooled, ENGAGED, all angles. `all rates` is the marginal ladder (what ss1 of")
print("  `studies/nearcentre/nearcentre_speed_and_band.py` reported); the other rows hold the manoeuvre rate fixed.\n")
VE = [0, 2, 3.5, 5.556, 7.5, 9.72, 11.18, 14, 18, 1e9]
VN = ["0-2", "2-3.5", "3.5-5.6", "5.6-7.5", "7.5-9.7", "9.7-11.2", "11.2-14", "14-18", "18+"]
ALLENG = [r for b in N.LADDER for r in store[b] if r["eng"] == 1]
print(f"  {'rate stratum':<16} " + " ".join(f"{n:>13}" for n in VN))
sr = {}
for rlab, rlo, rhi in (("all rates", 0.0, 1e9), ("rate 0-4", 0.0, 4.0), ("rate 4-16", 4.0, 16.0),
                       ("rate 16-32", 16.0, 32.0), ("rate 32+", 32.0, 1e9)):
    rs = [r for r in ALLENG if rlo <= r["rate_lp"] < rhi]
    cells, row = [], []
    for i in range(len(VN)):
        c = [r for r in rs if VE[i] <= r["v"] < VE[i + 1]]
        nb = len({r[G.EPKEY] for r in c})
        v = G.col(c, "e_18-22")
        v = v[np.isfinite(v)]
        m = float(np.median(v)) if len(v) else np.nan
        row.append(dict(n=len(c), nb=nb, med=m))
        cells.append(f"{'EMPTY':>13}" if not len(v)
                     else (f"{m:>6.0f}~n{len(c):<3}" if len(c) < 8 or nb < 3
                           else f"{m:>7.0f}n{len(c):<3}").rjust(13))
    sr[rlab] = row
    print(f"  {rlab:<16} " + " ".join(cells))
print("\n  `~` marks a thin cell (< 8 windows or < 3 units) -- read as exposure, not as a null.")
OUT["speed_by_rate"] = sr

print("\n  --- and the converse: the RATE ladder inside a fixed SPEED stratum")
print(f"  {'speed stratum':<16} " + " ".join(f"{n:>13}"
                                             for n in ["0-4", "4-16", "16-32", "32-64", "64+"]))
RE = [0, 4, 16, 32, 64, 1e9]
rs2 = {}
for vlab, vlo, vhi in (("creep <5.6", 0.0, 5.556), ("5.6-11.2", 5.556, 11.18),
                       ("11.2-18", 11.18, 18.0), ("18+", 18.0, 1e9)):
    rs = [r for r in ALLENG if vlo <= r["v"] < vhi]
    cells, row = [], []
    for i in range(5):
        c = [r for r in rs if RE[i] <= r["rate_lp"] < RE[i + 1]]
        nb = len({r[G.EPKEY] for r in c})
        v = G.col(c, "e_18-22")
        v = v[np.isfinite(v)]
        m = float(np.median(v)) if len(v) else np.nan
        row.append(dict(n=len(c), nb=nb, med=m))
        cells.append(f"{'EMPTY':>13}" if not len(v)
                     else (f"{m:>6.0f}~n{len(c):<3}" if len(c) < 8 or nb < 3
                           else f"{m:>7.0f}n{len(c):<3}").rjust(13))
    rs2[vlab] = row
    print(f"  {vlab:<16} " + " ".join(cells))
OUT["rate_by_speed"] = rs2

# ------------------------------------------------------------------ ss3 narrow-floor band --------
N.hdr("ss3  ★★ THE MICRO-RATCHET BAND with a NARROW prominence floor (halfwin 2.5, exclude 0.8)")
print("  The 8 Hz ratchet is 20-30x its local floor, so the default 6 Hz half-window lets it raise")
print("  the floor for everything from 2 to 14 Hz. A narrow floor can see a weak line beside it.")
print("  `eng/man` is the engaged-to-manual power ratio at that bin -- the kit's own")
print("  engagement-conditional test. 🛑 The two arms' SPEED distributions differ (printed), so a")
print("  wheel order will move between them; that is a caveat on identification, not on presence.\n")

SPEC = {"V67+V68 (best)": ["V67/r47", "V68/r4e"], "stock pool": N.ARMS["stock pool"],
        "V62+V65": N.ARMS["V62+V65"], "V71B/r54": ["V71B/r54"], "V71C/r58": ["V71C/r58"]}


def arm_spec(names, mfn):
    accs, Ks, vs, fref = [], 0, [], None
    for n in names:
        segs = [s for s in G.BUILDS[n]["segs"] if s not in L.PARKED.get(n, [])]
        f, P, K, stack, meta = L.avg_periodogram(n, mask_fn=mfn, vlo=0.0, vhi=N.CREEP, segs=segs)
        if P is None or K == 0:
            continue
        fref, Ks = f, Ks + K
        accs.append(P * K)
        vs += [m["v"] for m in meta]
    if not accs:
        return None, None, 0, []
    return fref, np.sum(accs, axis=0) / Ks, Ks, vs


bandout = {}
for k, names in SPEC.items():
    f, Pe, Ke, ve = arm_spec(names, L.eng_mask)
    _, Pm, Km, vm = arm_spec(names, L.man_mask)
    if Pe is None:
        continue
    R = G.prom_spectrum(f, Pe, halfwin=2.5, exclude=0.8)
    print(f"  --- {k:<16} engaged K={Ke:<4} v={np.mean(ve):.2f}+/-{np.std(ve):.2f} | "
          f"manual K={Km:<4} v={np.mean(vm):.2f}+/-{np.std(vm):.2f}")
    m = (f >= 1.5) & (f <= 18.0) & np.isfinite(R)
    idx = [i for i in np.flatnonzero(m)
           if 0 < i < len(R) - 1 and R[i] >= R[i - 1] and R[i] >= R[i + 1] and R[i] > 1.3]
    idx.sort(key=lambda i: -R[i])
    rows = []
    for i in idx[:8]:
        amp = float(2 * np.sqrt(Pe[i]) / (0.5 * G.NFFT))
        em = (Pe[i] / Pm[i]) if (Pm is not None and Pm[i] > 0) else np.nan
        rows.append(dict(f=float(f[i]), prom=float(R[i]), pp=2 * amp, engman=float(em)))
        print(f"        f = {f[i]:>6.2f} Hz  prom(narrow) {R[i]:>6.2f}  "
              f"amp ~{amp:>7.1f} ({2 * amp:>7.1f} p-p)  eng/man = {em:>8.1f}x")
    if not rows:
        print("        (no local maximum above prominence 1.3 anywhere in 1.5-18 Hz)")
    bandout[k] = dict(Ke=Ke, Km=Km, ve=float(np.mean(ve)), vm=float(np.mean(vm)), peaks=rows)
    print()
OUT["band_narrow"] = bandout

(HERE.parent / "_scratch/out/_nearcentre_final.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_nearcentre_final.json'}")
