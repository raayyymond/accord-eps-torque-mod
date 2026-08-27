#!/usr/bin/env python3
"""V67 / route 47: is the HIGHWAY resonance grind #2, or a grind #2.5?  And is grind #2 still
there at low speed?

The operator's report, verbatim:
    "Grind #2 seems mostly gone. However ... on the way, when doing somewhat significant turns,
     there is sometimes a resonance that I can feel is similar to grind #2. This higher-speed
     grind #2 happens when changing lanes or on a somewhat significant turn on the highway. Also
     is only on during LKAS-engaged. Grind #2 might still be there somewhat during LKAS-disengaged
     or more so LKAS-engaged at low-speed, I am not sure. Might just be dampened."

Instruments are `_grind2_lib` unchanged -- same bands, same leakage-controlled p99 envelope, same
prominence, same episode bootstrap and split-half null -- so every number here is comparable to the
creep numbers on record. `_r47_lib` adds only covariates.

TWO measurement corrections are made here and both change published numbers:

  fs   The kit estimates fs as 1/median(diff(t)). The comma BATCHES CAN reads, so the dt histogram
       is bimodal (p10 = 0 ms, p90 = 19 ms) and the median lands BELOW the true interval. Measured
       over whole segments, (n-1)/span = 100.000 Hz on every clean segment of every route, while
       1/median(dt) reads 99.4-101.5. Every frequency this kit has published is therefore inflated
       by +0.6% to +1.4%, ROUTE-DEPENDENTLY (r35 +1.19%, r37 +0.85%, r3b +0.71%, r47 +0.64%). All
       frequencies below use fs = 100.000 Hz.

  gate 🛑 On route 47 the firmware's gate bit g6806 equals carControl.latActive in 150,302 of
       150,327 frames, and it is 0 in EVERY frame above 8 m/s. The within-route A/B is therefore
       (a) a CREEP-ONLY experiment and (b) perfectly confounded with LKAS engagement. §0 measures
       this before any dose number is quoted.

Usage:  python studies/sessions/r47/analyze_r47_grind2.py            (all sections)
        python studies/sessions/r47/analyze_r47_grind2.py 3 4        (only those sections)
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
import _r47_lib as R  # noqa: E402
from _r31_common import fs_of, load, periodogram, runs_of, sustained  # noqa: E402

OUTJSON = HERE / "_scratch/out/_r47_grind2.json"
RNG = np.random.default_rng(20260802)

FS_TRUE = 100.000        # measured, see the module docstring. NOT 1/median(diff(t)).
NF = G.NFFT
CIRC = (R.CIRC_LO + R.CIRC_HI) / 2      # 2.0805 m, the established wheel circumference

HWY = 20.0               # m/s. The operator's "highway"; also where the gate is 100% on.
BURST = 300.0            # counts of 30-49 Hz envelope p99. Deliberately BELOW the creep-era 400 --
                         # the highway population tops out at 684, so a 400 threshold leaves 9
                         # windows. Both are reported side by side wherever it matters.
CREEP = 4.0

OUT = {}


# ================================================================================ helpers =========
def free_spec(build, s, mask_fn, chan="tq", nfft=NF, hop=G.HOP, fs=FS_TRUE):
    """Windows of one segment on the TRUE grid: (P, f, covariates). Index is the time base."""
    B = G.BUILDS[build]
    p = B["cache"] / f"{B['pfx']}{s}.npz"
    if not p.exists():
        return
    d = load(s, B["cache"], B["pfx"])
    f = np.fft.rfftfreq(nfft, 1 / fs)
    x = np.asarray(d[chan], float)
    v = np.abs(d["cs_v"])
    m = mask_fn(d)
    for a, b in runs_of(m, d["t"], nfft):
        for i in range(0, b - a - nfft + 1, hop):
            P = periodogram(x[a + i:a + i + nfft], fs, nfft, True)
            if P is None:
                continue
            sl = slice(a + i, a + i + nfft)
            yield dict(f=f, P=P, seg=int(s), t0=float(d["t"][a + i]),
                       v=float(np.mean(v[sl])), blk=(build, int(s), int(a), (i // hop) // 8))


def drop_eng_cell(rs):
    """Copies with `cell` = (v, effort, rate) only.

    🛑 `_grind2_lib` puts ENGAGEMENT in the first slot of `cell`. On route 47 the gate IS
    engagement (§0), so a gate=1 / gate=0 comparison stratified on the stock `cell` has ZERO
    shared cells and every ratio comes back NaN -- which reads as "no data" rather than as the
    tautology it is. This drops that slot so the two arms can be matched on what is left.
    """
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = tuple(r["cell"][1:])
        out.append(q)
    return out


def auc(pos, neg):
    """P(x_pos > x_neg) + 0.5 P(=). Rank-biserial separation, robust to any monotone rescale."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if not len(pos) or not len(neg):
        return np.nan
    allv = np.concatenate([pos, neg])
    r = np.argsort(np.argsort(allv)) + 1.0
    # average ranks for ties
    order = np.argsort(allv, kind="mergesort")
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            r[order[i:j + 1]] = np.mean(r[order[i:j + 1]])
        i = j + 1
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg)))


def block_perm_p(recs, key, burstkey, thr, rng, nperm=3000):
    """Permutation p for the AUC of `key` between burst and non-burst windows, shuffling BLOCK
    labels (not windows) so windows inside one burst cannot each count as evidence."""
    blks = {}
    for r in recs:
        blks.setdefault(r["blk"], []).append(r)
    keys = list(blks)
    lab = np.array([any(x[burstkey] > thr for x in blks[k]) for k in keys])
    if lab.sum() < 2 or (~lab).sum() < 2:
        return np.nan, np.nan
    vals = [np.nanmean([x[key] for x in blks[k]]) for k in keys]
    vals = np.array(vals, float)
    obs = auc(vals[lab], vals[~lab])
    hits = 0
    for _ in range(nperm):
        p = rng.permutation(len(keys))
        L = lab[p]
        a = auc(vals[L], vals[~L])
        if np.isfinite(a) and abs(a - 0.5) >= abs(obs - 0.5) - 1e-12:
            hits += 1
    return float(obs), float((hits + 1) / (nperm + 1))


def burst_runs(build, s, thr, lo=30.0, hi=49.0, chan="tq", fs=FS_TRUE, minv=None):
    """Contiguous stretches where the 30-49 Hz analytic envelope exceeds `thr`, on RAW frames.
    Gives the burst DURATION distribution, which a 2.56 s window cannot."""
    B = G.BUILDS[build]
    p = B["cache"] / f"{B['pfx']}{s}.npz"
    if not p.exists():
        return []
    d = load(s, B["cache"], B["pfx"])
    x = np.asarray(d[chan], float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    env = np.abs(np.fft.irfft(H, n=len(x)))
    v = np.abs(d["cs_v"])
    ok = env > thr
    if minv is not None:
        ok &= (v >= minv)
    out, i = [], 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j + 1 < len(ok) and ok[j + 1]:
                j += 1
            out.append(dict(seg=int(s), t0=float(d["t"][i]), dur=(j - i + 1) / fs,
                            peak=float(env[i:j + 1].max()), v=float(v[i:j + 1].mean())))
            i = j + 1
        else:
            i += 1
    return out


# ================================================================================ §0 ==============
def sec0(store):
    G.hdr("§0  PROVENANCE AND EXPOSURE.  🛑 Everything downstream is bounded by this section.")
    B = G.BUILDS["V67/r47"]
    tab = np.zeros((2, 2), int)
    ill = unused = 0
    vv, gg = [], []
    for s in B["segs"]:
        d = load(s, B["cache"], B["pfx"])
        l1 = (d["cc_lat"] > 0.5).astype(int)
        g1 = (d["g6806"] > 0.5).astype(int)
        for a in (0, 1):
            for b in (0, 1):
                tab[a, b] += int(((l1 == a) & (g1 == b)).sum())
        ill += int(d["illegal"].sum())
        unused += int(d["unused"].sum())
        vv.append(np.abs(d["cs_v"]))
        gg.append(d["g6806"] > 0.5)
    v = np.concatenate(vv)
    g = np.concatenate(gg)
    n = tab.sum()
    print(f"  probe liveness: illegal frames {ill}, unused-bit sets {unused}  (both MUST be 0)")
    print(f"  bit5 gp-0x671d (the masking risk) set in "
          f"{sum(int((load(s, B['cache'], B['pfx'])['g671d'] > 0.5).sum()) for s in B['segs'])} "
          f"frames -- 0 means no window is pinned to 1024 and every gate=1 window is a true Kd=2 "
          f"sample")
    print(f"\n  g6806 vs carControl.latActive, {n} frames:")
    print(f"      lat=0,gate=0 {tab[0, 0]:7d}   lat=0,gate=1 {tab[0, 1]:4d}")
    print(f"      lat=1,gate=0 {tab[1, 0]:7d}   lat=1,gate=1 {tab[1, 1]:6d}   "
          f"agreement {100 * (tab[0, 0] + tab[1, 1]) / n:.3f}%")
    print("  🛑 The firmware's own gate IS LKAS engagement. The within-route dose A/B and the")
    print("     engagement A/B are the SAME contrast on this route; neither can be adjusted for the")
    print("     other, on any amount of data.")

    print(f"\n  exposure, seconds, by speed x gate:")
    print(f"  {'v (m/s)':>10s} {'gate=1 (Kd=2)':>14s} {'gate=0 (Kd=1)':>14s}")
    rows = {}
    for lo, hi in [(0, 0.5), (0.5, 2), (2, 4), (4, 8), (8, 14), (14, 20), (20, 28), (28, 40)]:
        m = (v >= lo) & (v < hi)
        a, b = 0.01 * float((m & g).sum()), 0.01 * float((m & ~g).sum())
        rows[f"{lo}-{hi}"] = (a, b)
        print(f"  {f'{lo:g}-{hi:g}':>10s} {a:14.1f} {b:14.1f}")
    print(f"  {'TOTAL':>10s} {0.01 * float(g.sum()):14.1f} {0.01 * float((~g).sum()):14.1f}")
    print("\n  🛑 ZERO seconds of gate=0 above 8 m/s. There is no Kd=1 highway sample on route 47,")
    print("     and none on any other route either (§1). The highway dose curve asked for in task 4")
    print("     is an EMPTY CELL, not a null.")

    # the grind-#2 corner, by gate
    cor = np.zeros(2)
    for s in B["segs"]:
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        c = (np.abs(d["cs_v"]) < 4) & (eff >= 1200) & (np.abs(d["ang"]) >= 100)
        gm = d["g6806"] > 0.5
        cor[1] += float((c & gm).sum()) / fs
        cor[0] += float((c & ~gm).sum()) / fs
    print(f"\n  the grind-#2 CORNER (v<4, sustained |tq|>=1200, |ang|>=100 deg) on route 47:")
    print(f"      gate=1 {cor[1]:.1f} s      gate=0 {cor[0]:.1f} s")
    print(f"  for comparison, ENGAGED corner seconds: V65/r3a 97.9  V65/r3b 9.3  V62/r37 23.5  "
          f"V59/r2c 11.8  V64/r35 8.0")
    print(f"  🛑 {cor[1]:.1f} s is ~{cor[1] / 2.56:.1f} windows. Route 47 did not visit the corner")
    print("     grind #2 lives in while the dose was armed. §5 quantifies what that can and cannot"
          " rule out.")

    # fs audit
    print("\n  SAMPLE-RATE AUDIT (the frequency-axis correction):")
    print(f"  {'route':8s} {'1/median(dt)':>22s} {'(n-1)/span':>22s} {'axis bias':>10s}")
    fsa = {}
    for b in G.ORDER:
        Bb = G.BUILDS[b]
        a1, a2 = [], []
        for s in Bb["segs"]:
            p = Bb["cache"] / f"{Bb['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = load(s, Bb["cache"], Bb["pfx"])
            t = d["t"]
            a1.append(1 / np.median(np.diff(t)))
            a2.append((len(t) - 1) / (t[-1] - t[0]))
        a1, a2 = np.array(a1), np.array(a2)
        clean = a2[a2 > 99.9]
        fsa[b] = dict(med=float(a1.mean()), span=float(clean.mean() if len(clean) else a2.mean()))
        print(f"  {b:8s} {a1.min():8.3f}-{a1.max():7.3f} ({a1.mean():6.3f}) "
              f"{a2.min():8.3f}-{a2.max():7.3f} ({fsa[b]['span']:6.3f}) "
              f"{100 * (a1.mean() / fsa[b]['span'] - 1):+9.2f}%")
    print("  ⇒ the true 0x14A rate is 100.000 Hz on every route. A published '44.9 Hz' measured on")
    print("     r3a/r3b is 44.9/1.0071 = 44.6 Hz; on r35 it is 44.4 Hz. The 0.4 Hz spread BETWEEN")
    print("     routes is an instrument artefact, not the mode moving.")
    OUT["s0"] = dict(gate_vs_lat=tab.tolist(), expo=rows, corner_gate=cor.tolist(), fs=fsa,
                     illegal=ill)


# ================================================================================ §1 ==============
def sec1(store):
    G.hdr("§1  CENSUS.  The same estimator on every route, split by speed regime.\n"
          "  E30-49 = leakage-controlled p99 of the 30-49 Hz analytic envelope of the torsion bar.\n"
          "  zig800 = FFT-free count of sign-alternating turning points > 800 counts (near fs/2).\n"
          "  ang_hf = the SAME band on 0x14A steering angle -- a different sensor, on a\n"
          "  different message.")
    print(f"  {'population':22s} {'nwin':>5s} {'nblk':>5s} | {'E p50':>7s} {'p90':>7s} {'p99':>8s} "
          f"{'max':>8s} | {'>300':>7s} {'>400':>7s} | {'zig max':>7s} | {'ang_hf p99':>10s} "
          f"{'max':>6s}")
    pops = [("V67/r47 HWY v>=20", [r for r in store["V67/r47"] if r["v"] >= HWY]),
            ("V67/r47 mid 8-20", [r for r in store["V67/r47"] if 8 <= r["v"] < HWY]),
            ("V67/r47 creep v<4", [r for r in store["V67/r47"] if r["v"] < CREEP]),
            ("V67/r47   gate=1", [r for r in store["V67/r47"]
                                  if r["v"] < CREEP and r["gate"] > 0.98]),
            ("V67/r47   gate=0", [r for r in store["V67/r47"]
                                  if r["v"] < CREEP and r["gate"] < 0.02])]
    for b in G.ORDER[:-1]:
        pops.append((f"{b} HWY v>=20", [r for r in store[b] if r["v"] >= HWY]))
    for b in G.ORDER[:-1]:
        pops.append((f"{b} creep v<4", [r for r in store[b] if r["v"] < CREEP]))
    cen = {}
    for nm, rs in pops:
        if not rs:
            print(f"  {nm:22s} {'(no windows)':>12s}")
            continue
        e = G.col(rs, "e_30-49")
        z = G.col(rs, "zig800")
        a = G.col(rs, "ang_hf")
        nb = len({r["blk"] for r in rs})
        cen[nm] = dict(n=len(rs), nblk=nb, p99=float(np.percentile(e, 99)), mx=float(e.max()),
                       n300=int((e > 300).sum()), n400=int((e > 400).sum()), zigmax=float(z.max()),
                       anghf_max=float(a.max()))
        print(f"  {nm:22s} {len(rs):5d} {nb:5d} | {np.median(e):7.1f} "
              f"{np.percentile(e, 90):7.1f} {np.percentile(e, 99):8.1f} {e.max():8.1f} | "
              f"{int((e > 300).sum()):7d} {int((e > 400).sum()):7d} | {z.max():7.0f} | "
              f"{np.percentile(a, 99):10.3f} {a.max():6.3f}")
    print("\n  🛑 The creep grind #2 on V65 reaches 4,046 counts and zig800 = 134. The whole highway")
    print("     population of route 47 tops out at 684 counts and zig800 = 3. Whatever the highway")
    print("     event is, it is 6x SMALLER in the torsion bar and 40x weaker in the FFT-free test.")

    print("\n  IS THE HIGHWAY EVENT NEW WITH V67?  Block-level, and conditioned on manoeuvres\n"
          "  (angle excursion >= 4 deg in the window), which is the condition the operator named.")
    print(f"  {'build':10s} {'kd':>4s} {'nwin':>5s} {'nblk':>5s} {'blk>300':>8s} {'max':>7s} | "
          f"{'manoeuvre win':>13s} {'nblk':>5s} {'blk>300':>8s} {'max':>7s}")
    xb = {}
    for b in ("V59/r2c", "V62/r37", "V65/r3b", "V67/r47"):
        h = [r for r in store[b] if r["v"] >= HWY]
        if not h:
            continue
        mv = [r for r in h if r["dang"] >= 4.0]
        a, nn = R.blockstat(h, "e_30-49", BURST)
        am, nm_ = R.blockstat(mv, "e_30-49", BURST) if mv else (0, 0)
        kd = "2*g" if b == "V67/r47" else f"{G.BUILDS[b]['kd']:g}"
        xb[b] = dict(blk=(a, nn), man=(am, nm_), mx=float(G.col(h, "e_30-49").max()))
        print(f"  {b:10s} {kd:>4s} {len(h):5d} {nn:5d} {f'{a}/{nn}':>8s} "
              f"{G.col(h, 'e_30-49').max():7.0f} | {len(mv):13d} {nm_:5d} {f'{am}/{nm_}':>8s} "
              f"{(G.col(mv, 'e_30-49').max() if mv else 0):7.0f}")
    pa = [r for b in ("V62/r37", "V65/r3b") for r in store[b] if r["v"] >= HWY]
    pb = [r for r in store["V67/r47"] if r["v"] >= HWY]
    for lbl, fa, fb in (("all highway", lambda r: True, lambda r: True),
                        ("manoeuvre only", lambda r: r["dang"] >= 4.0,
                         lambda r: r["dang"] >= 4.0)):
        a1, n1 = R.blockstat([r for r in pa if fa(r)], "e_30-49", BURST)
        a2, n2 = R.blockstat([r for r in pb if fb(r)], "e_30-49", BURST)
        print(f"    {lbl:16s} V62+V65 {a1}/{n1}   V67 {a2}/{n2}   "
              f"Fisher p = {R.fisher2x2(a2, n2 - a2, a1, n1 - a1):.4g}")
    print("  ⇒ the highway event is ALREADY PRESENT on V62 and V65. V67 is not established as")
    print("    having created it, and 🛑 EVERY highway log this kit owns was recorded with Kd=2 in")
    print("    force, so the highway event has never once been observed under stock Kd.")
    OUT["s1"] = cen
    OUT["s1_hwy"] = xb


# ================================================================================ §2 ==============
def sec2(store):
    G.hdr("§2  SAME MODE?  Highway bursts on r47 vs creep bursts on V65 r3a/r3b + V62 r37.\n"
          "  Frequencies on the CORRECTED axis (fs = 100.000 Hz).")
    hw = [r for r in store["V67/r47"] if r["v"] >= HWY and r["e_30-49"] > BURST]
    cb = [r for b in ("V65/r3a", "V65/r3b", "V62/r37") for r in store[b]
          if r["v"] < CREEP and r["e_30-49"] > 400]
    quiet = [r for r in store["V67/r47"] if r["v"] >= HWY and r["e_30-49"] < 100]
    print(f"  highway bursts (E>300, v>=20): {len(hw)} windows in {len({r['blk'] for r in hw})} "
          f"blocks / {len({r['ep'] for r in hw})} engagement runs")
    print(f"  creep bursts   (E>400, v<4)  : {len(cb)} windows in {len({r['blk'] for r in cb})} "
          f"blocks")

    # ---- frequency, corrected -------------------------------------------------------------------
    def corrf(rs, key="f_30-49"):
        out = []
        for r in rs:
            fsr = r["fs"]
            out.append(r[key] * FS_TRUE / fsr)     # rescale the reported axis onto the true one
        return np.array(out, float)

    print(f"\n  {'population':26s} {'n':>4s} {'f0 med':>7s} {'sd':>6s} {'IQR':>13s} "
          f"{'prom med':>9s} {'Q med':>6s} {'E med':>7s} {'ang_hf med':>10s} {'ang/E x1e3':>10s}")
    frows = {}
    for nm, rs in (("r47 HIGHWAY burst", hw), ("creep burst V65+V62", cb),
                   ("r47 highway quiet", quiet)):
        if not rs:
            continue
        f0 = corrf(rs)
        f0 = f0[np.isfinite(f0)]
        pr = G.col(rs, "p_30-49")
        q = G.col(rs, "Qhf")
        e = G.col(rs, "e_30-49")
        a = G.col(rs, "ang_hf")
        frows[nm] = dict(n=len(rs), f_med=float(np.median(f0)), f_sd=float(np.std(f0, ddof=1)),
                         prom=float(np.nanmedian(pr)), Q=float(np.nanmedian(q)),
                         E=float(np.median(e)), ang=float(np.median(a)),
                         ratio=float(np.median(a) / np.median(e) * 1e3))
        print(f"  {nm:26s} {len(rs):4d} {np.median(f0):7.2f} {np.std(f0, ddof=1):6.2f} "
              f"[{np.percentile(f0, 25):5.1f},{np.percentile(f0, 75):5.1f}] "
              f"{np.nanmedian(pr):9.2f} {np.nanmedian(q):6.1f} {np.median(e):7.1f} "
              f"{np.median(a):10.3f} {np.median(a) / np.median(e) * 1e3:10.2f}")

    # ---- band PROFILE ----------------------------------------------------------------------------
    BKS = ("1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49")
    print(f"\n  BAND PROFILE, each population normalised by its OWN E30-49 median (shape, not size):")
    print(f"  {'population':26s} " + " ".join(f"{k:>8s}" for k in BKS))
    prof = {}
    for nm, rs in (("r47 HIGHWAY burst", hw), ("creep burst V65+V62", cb),
                   ("r47 highway quiet", quiet)):
        if not rs:
            continue
        base = np.median(G.col(rs, "e_30-49"))
        row = [np.median(G.col(rs, "e_" + k)) / base for k in BKS]
        prof[nm] = row
        print(f"  {nm:26s} " + " ".join(f"{x:8.3f}" for x in row))
    print("  ⇒ the creep burst puts 0.92 of its band energy in 40-49 and almost nothing anywhere")
    print("    else: a narrowband event. The highway burst is BROADER than its own 40-49 content in")
    print("    three lower bands.")

    print("\n  BURST / QUIET RATIO PER BAND -- absolute, each regime against its own\n"
          "  quiet baseline.")
    print(f"  {'contrast':26s} " + " ".join(f"{k:>8s}" for k in BKS))
    cq = [r for b in ("V65/r3a", "V65/r3b", "V62/r37") for r in store[b]
          if r["v"] < CREEP and r["e_30-49"] < 150]
    ratios = {}
    for nm, bs, qs in (("r47 highway burst/quiet", hw, quiet),
                       ("creep burst/quiet", cb, cq)):
        if not bs or not qs:
            continue
        row = [np.median(G.col(bs, "e_" + k)) / max(np.median(G.col(qs, "e_" + k)), 1e-9)
               for k in BKS]
        ratios[nm] = row
        print(f"  {nm:26s} " + " ".join(f"{x:8.2f}" for x in row))

    # ---- narrowbandness ---------------------------------------------------------------------------
    print(f"\n  NARROWBANDNESS: fraction of the 30-49 Hz power inside +/-2 Hz of the window's own")
    print(f"  strongest 30-49 bin. A Q=37 mode concentrates it; a broadband transient does not.")
    print(f"  {'population':26s} {'n':>5s} {'frac med':>9s} {'p25':>7s} {'p75':>7s}")
    nb = {}
    for nm, build, selfn in (("r47 HIGHWAY burst", "V67/r47",
                              lambda r: r["v"] >= HWY and r["e_30-49"] > BURST),
                             ("r47 highway quiet", "V67/r47",
                              lambda r: r["v"] >= HWY and r["e_30-49"] < 100),
                             ("V65 creep burst", "V65/r3a", lambda r: r["e_30-49"] > 400),
                             ("V65 creep quiet", "V65/r3a", lambda r: r["e_30-49"] < 150)):
        want = {(r["seg"], round(r["t0"], 2)) for r in store[build] if selfn(r)}
        vals = []
        Bb = G.BUILDS[build]
        for s in Bb["segs"]:
            for w in free_spec(build, s, lambda d: np.ones(len(d["t"]), bool)):
                if (w["seg"], round(w["t0"], 2)) not in want:
                    continue
                m = (w["f"] >= 30) & (w["f"] <= 49)
                j = int(np.argmax(np.where(m, w["P"], -np.inf)))
                near = m & (np.abs(w["f"] - w["f"][j]) <= 2.0)
                vals.append(float(np.sum(w["P"][near]) / np.sum(w["P"][m])))
        if not vals:
            continue
        vals = np.array(vals)
        nb[nm] = dict(n=len(vals), med=float(np.median(vals)))
        print(f"  {nm:26s} {len(vals):5d} {np.median(vals):9.3f} "
              f"{np.percentile(vals, 25):7.3f} {np.percentile(vals, 75):7.3f}")

    # ---- burst duration on RAW frames -----------------------------------------------------------
    print(f"\n  BURST DURATION (contiguous frames above threshold on the raw 100 Hz envelope).")
    print(f"  🛑 The threshold is RELATIVE -- 8x each population's own median envelope in its own")
    print(f"  speed regime -- because the highway event is 6x smaller and a fixed 400 would compare")
    print(f"  the two populations at completely different points of their distributions.")
    durs = {}
    for nm, build, thr, minv in (("r47 highway", "V67/r47", None, HWY),
                                 ("V65/r3a creep", "V65/r3a", None, None),
                                 ("V65/r3b creep", "V65/r3b", None, None),
                                 ("V62/r37 creep", "V62/r37", None, None)):
        Bb = G.BUILDS[build]
        base = [r for r in store[build]
                if (r["v"] >= minv if minv is not None else r["v"] < CREEP)]
        thr = 8.0 * float(np.median(G.col(base, "e_30-49")))
        runs = [q for s in Bb["segs"] for q in burst_runs(build, s, thr, minv=minv)]
        runs = [q for q in runs if q["dur"] >= 0.03]
        if minv is None:
            runs = [q for q in runs if q["v"] < CREEP]
        if not runs:
            print(f"  {nm:26s} threshold {thr:.0f}: none")
            continue
        print(f"  (threshold {thr:.0f} counts)")
        dd = np.array([q["dur"] for q in runs])
        pk = np.array([q["peak"] for q in runs])
        durs[nm] = dict(n=len(dd), med=float(np.median(dd)), p90=float(np.percentile(dd, 90)),
                        mx=float(dd.max()), peak=float(pk.max()))
        print(f"  {nm:26s} n={len(dd):4d}  dur med {np.median(dd):.3f} s  p90 "
              f"{np.percentile(dd, 90):.3f} s  max {dd.max():.3f} s   peak env {pk.max():7.0f}")

    # ---- alias family ---------------------------------------------------------------------------
    if hw:
        fh = float(np.median(corrf(hw)))
        fc = float(np.median(corrf(cb))) if cb else np.nan
        print(f"\n  🛑 ALIAS. fs = 100.000 Hz exactly, so the fold point is 50.000 Hz.")
        print(f"     highway burst f_obs = {fh:.2f} Hz -> true F in "
              f"{[round(x, 2) for x in R.alias_family(fh, FS_TRUE)]}")
        print(f"     creep   burst f_obs = {fc:.2f} Hz -> true F in "
              f"{[round(x, 2) for x in R.alias_family(fc, FS_TRUE)]}")
        print("     §7 attacks this with the comma IMU, whose hardware sample interval is 9.899 ms")
        print("     (101.02 Hz). A once-folded line must read 1.02 Hz HIGHER on the IMU than on CAN;")
        print("     an unfolded one must read the same. That is a resolvable difference.")
    OUT["s2"] = dict(freq=frows, profile=prof, durations=durs,
                     n_hw=len(hw), n_hw_blk=len({r["blk"] for r in hw}), n_creep=len(cb))


# ================================================================================ §3 ==============
def sec3(store):
    G.hdr("§3  SPEED DEPENDENCE.  A tyre/driveline order scales with road speed; a structural mode\n"
          "does not. f_order_n = n * v / 2.0805 Hz.  🛑 This kit has already called a wheel order a\n"
          "firmware effect once (the '8.69 Hz line V56 introduced' was 0.489*v).")
    # ---- Campbell: mean prominence spectrum by speed bin -----------------------------------------
    VB = [(20, 23), (23, 26), (26, 28), (28, 30), (30, 31.5), (31.5, 36)]
    acc = {i: [np.zeros(NF // 2 + 1), 0] for i in range(len(VB))}
    f = np.fft.rfftfreq(NF, 1 / FS_TRUE)
    allw = []
    for s in G.BUILDS["V67/r47"]["segs"]:
        for w in free_spec("V67/r47", s, lambda d: np.abs(d["cs_v"]) >= 18.0):
            Rr = G.prom_spectrum(w["f"], w["P"])
            allw.append((w, Rr))
            for k, (lo, hi) in enumerate(VB):
                if lo <= w["v"] < hi:
                    acc[k][0] += np.nan_to_num(Rr)
                    acc[k][1] += 1
    print("  CAMPBELL DIAGRAM -- mean prominence, torsion bar, route 47.  '#' marks the bin holding")
    print("  wheel order 2 or 3 for that speed bin.")
    print("   f(Hz)  " + " ".join(f"{lo:g}-{hi:g}(n{acc[k][1]})".rjust(13)
                                  for k, (lo, hi) in enumerate(VB)))
    for j in range(len(f)):
        if not (24 <= f[j] <= 49.5):
            continue
        cells = []
        for k, (lo, hi) in enumerate(VB):
            c = (lo + hi) / 2
            mark = "#" if any(abs(f[j] - n * c / CIRC) < 0.4 for n in (2, 3)) else " "
            cells.append(f"{acc[k][0][j] / max(acc[k][1], 1):12.2f}{mark}")
        print(f"  {f[j]:6.2f}  " + " ".join(cells))
    print("\n  wheel orders at bin centres:  " + "   ".join(
        f"v={(lo + hi) / 2:.1f}: o2={2 * (lo + hi) / 2 / CIRC:.1f} o3={3 * (lo + hi) / 2 / CIRC:.1f}"
        for lo, hi in VB))

    # ---- order histogram -------------------------------------------------------------------------
    print("\n  ORDER TEST.  For every window, locate the most prominent line in a FREE band and")
    print("  report order = f0 * 2.0805 / v. A tyre order piles up on an INTEGER.")
    # join the free-grid windows to the record store's own E30-49 by (seg, t0), so "burst" here is
    # the SAME definition used everywhere else in this file rather than a second proxy.
    ekey = {(r["seg"], round(r["t0"], 2)): r["e_30-49"] for r in store["V67/r47"]}

    def eof(w):
        return ekey.get((w["seg"], round(w["t0"], 2)), np.nan)

    print(f"  {'band':10s} {'sel':26s} {'n':>5s} {'order p50':>10s} {'p25':>7s} {'p75':>7s} "
          f"{'slope Hz/(m/s)':>15s} {'=> order':>9s} {'corr':>6s}")
    orows = {}
    for lbl, lo, hi in (("34-49.4", 34.0, 49.4), ("22-33", 22.0, 33.0)):
        for selnm, selfn in (("all windows v>=23.6", lambda w, e: w["v"] >= 23.6),
                             ("BURST E30-49>300", lambda w, e: np.isfinite(e) and e > BURST),
                             ("top-5% E30-49", lambda w, e: np.isfinite(e) and e > q95)):
            q95 = float(np.nanpercentile([eof(w) for w, _ in allw], 95))
            V, F = [], []
            for w, Rr in allw:
                if not selfn(w, eof(w)):
                    continue
                f0, pr = G.locate(w["f"], w["P"], lo, hi, R=Rr)
                if np.isfinite(f0) and pr >= 2.0 and w["v"] > 1:
                    V.append(w["v"])
                    F.append(f0)
            if len(V) < 12:
                print(f"  {lbl:10s} {selnm:26s} {len(V):5d}   (too few)")
                continue
            V, F = np.array(V), np.array(F)
            o = F * CIRC / V
            k = float(np.sum(V * F) / np.sum(V * V))
            orows[f"{lbl}|{selnm}"] = dict(n=len(V), o50=float(np.median(o)), slope=k,
                                           order=k * CIRC, corr=float(np.corrcoef(V, F)[0, 1]))
            print(f"  {lbl:10s} {selnm:26s} {len(V):5d} {np.median(o):10.3f} "
                  f"{np.percentile(o, 25):7.3f} {np.percentile(o, 75):7.3f} {k:15.4f} "
                  f"{k * CIRC:9.3f} {np.corrcoef(V, F)[0, 1]:6.3f}")

    # ---- ON-ORDER vs OFF-ORDER --------------------------------------------------------------------
    print("\n  ON-ORDER vs OFF-ORDER.  The decisive separation. For every 20-49 Hz bin, is it within")
    print("  0.6 Hz of wheel order 1..5 for that window's own speed? Then compare mean power per")
    print("  ON-order bin with mean power per OFF-order bin. A tyre order raises only the ON bins.")
    oo = {"burst": [], "quiet": []}
    for w, _Rr in allw:
        e = eof(w)
        lab = ("burst" if e > BURST else ("quiet" if e < 100 else None)) if np.isfinite(e) else None
        if lab is None or w["v"] < HWY:
            continue
        on = np.zeros(len(w["f"]), bool)
        for n in (1, 2, 3, 4, 5):
            on |= np.abs(w["f"] - n * w["v"] / CIRC) <= 0.6
        m = (w["f"] >= 20) & (w["f"] <= 49)
        oo[lab].append((float(w["P"][on & m].sum()) / max((on & m).sum(), 1),
                        float(w["P"][(~on) & m].sum()) / max(((~on) & m).sum(), 1)))
    if oo["burst"] and oo["quiet"]:
        A, B = np.array(oo["burst"]), np.array(oo["quiet"])
        print(f"  {'population':12s} {'n':>5s} {'ON-order/bin':>14s} {'OFF-order/bin':>14s} "
              f"{'ON/OFF':>8s}")
        for nm, X in (("burst", A), ("quiet", B)):
            print(f"  {nm:12s} {len(X):5d} {np.median(X[:, 0]):14.0f} {np.median(X[:, 1]):14.0f} "
                  f"{np.median(X[:, 0] / X[:, 1]):8.2f}")
        print(f"  burst/quiet ON-order  {np.median(A[:, 0]) / np.median(B[:, 0]):.2f}x")
        print(f"  burst/quiet OFF-order {np.median(A[:, 1]) / np.median(B[:, 1]):.2f}x")
        print(f"  ⇒ quiet highway 20-49 Hz energy sits ON the wheel orders "
              f"({np.median(B[:, 0] / B[:, 1]):.1f}x). During a burst that ordering COLLAPSES to "
              f"{np.median(A[:, 0] / A[:, 1]):.2f}x:")
        print(f"    off-order power rises {np.median(A[:, 1]) / np.median(B[:, 1]):.0f}x against "
              f"{np.median(A[:, 0]) / np.median(B[:, 0]):.0f}x on-order. The burst is NOT a tyre")
        print("    order -- it is broadband energy riding on top of one.")
        OUT["s3_order_power"] = dict(burst_on=float(np.median(A[:, 0])),
                                     burst_off=float(np.median(A[:, 1])),
                                     quiet_on=float(np.median(B[:, 0])),
                                     quiet_off=float(np.median(B[:, 1])))

    # ---- does the BURST energy track speed? ------------------------------------------------------
    print("\n  BURST ENERGY vs SPEED (does the 40-49 Hz band ride the order line up through the")
    print("  band?). If the highway event is order 3, its band energy must PEAK where o3 sits in")
    print("  40-49 Hz, i.e. 27.7 <= v <= 34.0 m/s, and fall away below that.")
    print(f"  {'v bin':>12s} {'nwin':>5s} {'o3 (Hz)':>8s} {'E40-49 p50':>11s} {'p90':>8s} "
          f"{'E30-40 p50':>11s} {'E24-28 p50':>11s}")
    for lo, hi in [(18, 22), (22, 25), (25, 27.5), (27.5, 30), (30, 32), (32, 36)]:
        rs = [r for r in store["V67/r47"] if lo <= r["v"] < hi]
        if len(rs) < 8:
            continue
        c = (lo + hi) / 2
        print(f"  {f'{lo:g}-{hi:g}':>12s} {len(rs):5d} {3 * c / CIRC:8.2f} "
              f"{np.median(G.col(rs, 'e_40-49')):11.1f} "
              f"{np.percentile(G.col(rs, 'e_40-49'), 90):8.1f} "
              f"{np.median(G.col(rs, 'e_30-40')):11.1f} "
              f"{np.median(G.col(rs, 'e_24-28')):11.1f}")
    OUT["s3"] = orows


# ================================================================================ §4 ==============
def sec4(store):
    G.hdr("§4  WHAT CONDITIONS THE HIGHWAY EVENT?  Ranked by SEPARATION POWER.\n"
          "  AUC = P(covariate is higher in a burst block than in a quiet block), block-level, with\n"
          "  a block-label permutation p. 0.5 = no separation, 1.0 = perfect.")
    hw = [r for r in store["V67/r47"] if r["v"] >= HWY]
    VARS = [("rate", "|steering rate| mean (deg/s)"), ("ratep95", "|steering rate| p95"),
            ("latacc", "lateral accel (m/s^2, bicycle)"), ("dang", "angle excursion in window"),
            ("angsd", "angle sd in window"), ("ang", "|steering angle| mean"),
            ("eff", "DRIVER torque, 3 Hz sustained"), ("e4", "|0x0E4 LKAS command| mean"),
            ("e4max", "|0x0E4| max"), ("e4sd", "0x0E4 sd"), ("e4hf", "0x0E4 own 30-49 Hz env"),
            ("req", "openpilot actuator |torque|"), ("dreq", "openpilot |d(torque)/dt|"),
            ("v", "vehicle speed"), ("vsd", "speed sd (accel/decel)"),
            ("press", "steeringPressed fraction"), ("e_1-4", "1-4 Hz driver band (control)")]
    print(f"  {'covariate':34s} {'AUC':>6s} {'perm p':>8s} | {'burst blk med':>13s} "
          f"{'quiet blk med':>13s} {'ratio':>7s}")
    rank = []
    for k, nm in VARS:
        a, p = block_perm_p(hw, k, "e_30-49", BURST, RNG)
        blks = {}
        for r in hw:
            blks.setdefault(r["blk"], []).append(r)
        lab = {b: any(x["e_30-49"] > BURST for x in v) for b, v in blks.items()}
        bm = np.nanmedian([np.nanmean([x[k] for x in v]) for b, v in blks.items() if lab[b]])
        qm = np.nanmedian([np.nanmean([x[k] for x in v]) for b, v in blks.items() if not lab[b]])
        rank.append((abs(a - 0.5) if np.isfinite(a) else -1, k, nm, a, p, bm, qm))
    for _, k, nm, a, p, bm, qm in sorted(rank, reverse=True):
        rr = bm / qm if (np.isfinite(qm) and qm != 0) else np.nan
        print(f"  {nm:34s} {a:6.3f} {p:8.4f} | {bm:13.3f} {qm:13.3f} {rr:7.2f}")
    OUT["s4_rank"] = [dict(key=k, name=nm, auc=a, p=p, burst=bm, quiet=qm)
                      for _, k, nm, a, p, bm, qm in sorted(rank, reverse=True)]

    # ---- manoeuvre vs cruise at MATCHED speed ---------------------------------------------------
    print("\n  MANOEUVRE vs STRAIGHT CRUISE at matched speed. A manoeuvre window is one whose angle")
    print("  excursion exceeds 4 deg (a lane change is 5-15 deg at the wheel on this car); the")
    print("  control is the same speed band with excursion < 2 deg.")
    print(f"  {'v band':>10s} | {'MANOEUVRE n':>11s} {'E p50':>7s} {'p90':>7s} {'max':>7s} "
          f"{'blk>300':>8s} | {'CRUISE n':>9s} {'E p50':>7s} {'p90':>7s} {'max':>7s} "
          f"{'blk>300':>8s} | {'Fisher p':>9s}")
    mrows = {}
    for lo, hi in [(20, 26), (26, 30), (30, 36), (20, 36)]:
        mv = [r for r in hw if lo <= r["v"] < hi and r["dang"] >= 4.0]
        cv = [r for r in hw if lo <= r["v"] < hi and r["dang"] < 2.0]
        if len(mv) < 6 or len(cv) < 6:
            continue
        am, nm_ = R.blockstat(mv, "e_30-49", BURST)
        ac, nc = R.blockstat(cv, "e_30-49", BURST)
        p = R.fisher2x2(am, nm_ - am, ac, nc - ac) if min(nm_, nc) >= 3 else np.nan
        em, ec = G.col(mv, "e_30-49"), G.col(cv, "e_30-49")
        mrows[f"{lo}-{hi}"] = dict(nm=len(mv), nc=len(cv), am=am, nblkm=nm_, ac=ac, nblkc=nc, p=p,
                                   mmax=float(em.max()), cmax=float(ec.max()))
        print(f"  {f'{lo:g}-{hi:g}':>10s} | {len(mv):11d} {np.median(em):7.1f} "
              f"{np.percentile(em, 90):7.1f} {em.max():7.1f} {f'{am}/{nm_}':>8s} | "
              f"{len(cv):9d} {np.median(ec):7.1f} {np.percentile(ec, 90):7.1f} {ec.max():7.1f} "
              f"{f'{ac}/{nc}':>8s} | {p:9.4f}")
    OUT["s4_manoeuvre"] = mrows

    # ---- Simpson guard: within-speed-band AUC for the top variables ------------------------------
    # ---- the SAME ranking on the creep population, for the same/different verdict -----------------
    print("\n  THE SAME RANKING ON CREEP GRIND #2 (Kd=2 builds, v<4, burst = E30-49 > 400).")
    print("  If the highway event were the same mode, the same variables should select it.")
    cr = [r for b in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[b] if r["v"] < CREEP]
    print(f"  {'covariate':34s} {'AUC hwy':>8s} {'AUC creep':>10s} {'creep p':>9s} "
          f"{'creep burst/quiet':>18s}")
    hrank = {d["key"]: d["auc"] for d in OUT["s4_rank"]}
    crank = []
    for k, nm in VARS:
        a, p = block_perm_p(cr, k, "e_30-49", 400.0, RNG, nperm=2000)
        blks = {}
        for r in cr:
            blks.setdefault(r["blk"], []).append(r)
        lab = {b: any(x["e_30-49"] > 400.0 for x in v) for b, v in blks.items()}
        bm = np.nanmedian([np.nanmean([x[k] for x in v]) for b, v in blks.items() if lab[b]])
        qm = np.nanmedian([np.nanmean([x[k] for x in v]) for b, v in blks.items() if not lab[b]])
        crank.append((k, nm, a, p, bm / qm if qm else np.nan))
    for k, nm, a, p, rr in sorted(crank, key=lambda q: -(abs(q[2] - 0.5) if np.isfinite(q[2])
                                                         else -1)):
        print(f"  {nm:34s} {hrank.get(k, np.nan):8.3f} {a:10.3f} {p:9.4f} {rr:18.2f}")
    OUT["s4_creep_rank"] = [dict(key=k, auc=a, p=p, ratio=rr) for k, nm, a, p, rr in crank]

    print("\n  SIMPSON GUARD -- the same AUC computed INSIDE each speed band, so a variable that is")
    print("  only a proxy for speed collapses to 0.5 here.")
    top = [k for _, k, *_ in sorted(rank, reverse=True)[:7]]
    print(f"  {'covariate':16s} " + " ".join(f"{f'{lo:g}-{hi:g}':>12s}"
                                             for lo, hi in [(20, 26), (26, 30), (30, 36)]))
    for k in top:
        cells = []
        for lo, hi in [(20, 26), (26, 30), (30, 36)]:
            sub = [r for r in hw if lo <= r["v"] < hi]
            a, _ = block_perm_p(sub, k, "e_30-49", BURST, RNG, nperm=800)
            cells.append(f"{a:12.3f}" if np.isfinite(a) else f"{'.':>12s}")
        print(f"  {k:16s} " + " ".join(cells))


# ================================================================================ §5 ==============
def sec5(store):
    G.hdr("§5  LOW-SPEED GRIND #2 ON V67.  Does it still exist?")
    cr = [r for r in store["V67/r47"] if r["v"] < CREEP]
    g1 = [r for r in cr if r["gate"] > 0.98]
    g0 = [r for r in cr if r["gate"] < 0.02]
    print(f"  route 47 creep windows: gate=1 {len(g1)}  gate=0 {len(g0)}  "
          f"(mixed {len(cr) - len(g1) - len(g0)})")
    print(f"\n  {'population':30s} {'nwin':>5s} {'nblk':>5s} {'E p50':>7s} {'p90':>7s} "
          f"{'max':>8s} {'zigmax':>7s} {'ang_hf max':>10s} {'eff p90':>8s} {'|ang| p90':>9s}")
    pops = [("V67/r47 creep gate=1 (Kd2)", g1), ("V67/r47 creep gate=0 (Kd1)", g0)]
    for b in ("V65/r3a", "V65/r3b", "V62/r37", "V59/r2c", "V64/r35", "V61/r31"):
        pops.append((f"{b} creep ENGAGED",
                     [r for r in store[b] if r["v"] < CREEP and r["eng"] == 1]))
        pops.append((f"{b} creep manual",
                     [r for r in store[b] if r["v"] < CREEP and r["eng"] == 0]))
    low = {}
    for nm, rs in pops:
        if not rs:
            print(f"  {nm:30s} {'(none)':>12s}")
            continue
        e = G.col(rs, "e_30-49")
        low[nm] = dict(n=len(rs), nblk=len({r["blk"] for r in rs}), p90=float(np.percentile(e, 90)),
                       mx=float(e.max()), zig=float(G.col(rs, "zig800").max()))
        print(f"  {nm:30s} {len(rs):5d} {len({r['blk'] for r in rs}):5d} {np.median(e):7.1f} "
              f"{np.percentile(e, 90):7.1f} {e.max():8.1f} {G.col(rs, 'zig800').max():7.0f} "
              f"{G.col(rs, 'ang_hf').max():10.3f} {np.percentile(G.col(rs, 'eff'), 90):8.0f} "
              f"{np.percentile(G.col(rs, 'ang'), 90):9.1f}")

    # ---- the CORNER, matched on condition and on exposure ----------------------------------------
    G.hdr("§5b  THE DECISIVE LOW-SPEED TEST: the grind-#2 CORNER, split by LKAS, matched on\n"
          "seconds of exposure. Every creep burst ever recorded lives in this corner:\n"
          "v 1.5-2.6 m/s, sustained driver torque 1500-2500, |angle| 20-220 deg, |rate| 79-230.\n"
          "🛑 On V65/r3b the creep bursts were LKAS-OFF (4 of 4). Engagement is NOT what selects\n"
          "grind #2 at creep -- the corner is. So the manual arm is a REAL test of the dose, and it\n"
          "is the arm route 47 has exposure in.")

    def corner(rs):
        return [r for r in rs if r["v"] < CREEP and r["eff"] >= 1200 and r["ang"] >= 100]

    def corner_seconds(build, engaged):
        Bb = G.BUILDS[build]
        tot = 0.0
        for s in Bb["segs"]:
            p = Bb["cache"] / f"{Bb['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = load(s, Bb["cache"], Bb["pfx"])
            fs = fs_of(d)
            eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
            c = (np.abs(d["cs_v"]) < CREEP) & (eff >= 1200) & (np.abs(d["ang"]) >= 100)
            key = "g6806" if build == "V67/r47" else "cc_lat"
            m = d[key] > 0.5
            tot += float((c & (m if engaged else ~m)).sum()) / fs
        return tot

    print(f"\n  {'build / arm':24s} {'kd':>8s} {'corner s':>9s} {'nwin':>5s} {'nblk':>5s} "
          f"{'E p50':>7s} {'p90':>8s} {'max':>8s} {'blk>400':>8s} {'zigmax':>7s}")
    arms = {}
    for build in ("V67/r47", "V65/r3b", "V65/r3a", "V62/r37", "V59/r2c", "V64/r35", "V61/r31"):
        for engaged, lbl in ((0, "LKAS OFF"), (1, "LKAS ON")):
            rs = corner([r for r in store[build]
                         if (r["gate"] > 0.98 if build == "V67/r47"
                             else r["eng"] == 1) == bool(engaged)])
            secs = corner_seconds(build, bool(engaged))
            kd = ("2 (armed)" if engaged else "1 (stock)") if build == "V67/r47" \
                else f"{G.BUILDS[build]['kd']:g}"
            if not rs:
                print(f"  {build + ' ' + lbl:24s} {kd:>8s} {secs:9.1f} {0:5d}   (no windows)")
                arms[f"{build}|{lbl}"] = dict(secs=secs, n=0)
                continue
            e = G.col(rs, "e_30-49")
            a, nblk = R.blockstat(rs, "e_30-49", 400.0)
            arms[f"{build}|{lbl}"] = dict(secs=secs, n=len(rs), nblk=nblk, burst_blk=a,
                                          mx=float(e.max()))
            print(f"  {build + ' ' + lbl:24s} {kd:>8s} {secs:9.1f} {len(rs):5d} {nblk:5d} "
                  f"{np.median(e):7.1f} {np.percentile(e, 90):8.1f} {e.max():8.1f} "
                  f"{f'{a}/{nblk}':>8s} {G.col(rs, 'zig800').max():7.0f}")

    print("\n  ---- the exposure-matched contrasts ----")
    for lbl, A, Bk in (("V67 corner LKAS-OFF (Kd=1) vs V65/r3b corner LKAS-OFF (Kd=2)",
                        ("V67/r47", 0), ("V65/r3b", 0)),
                       ("V67 corner LKAS-OFF (Kd=1) vs ALL Kd=2 corner, both arms",
                        ("V67/r47", 0), ("KD2", None)),
                       ("V67 corner LKAS-ON  (Kd=2) vs V65/r3a corner LKAS-ON (Kd=2)",
                        ("V67/r47", 1), ("V65/r3a", 1))):
        def pool(spec):
            b, e = spec
            if b == "KD2":
                rs = corner([r for bb in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[bb]])
                secs = sum(corner_seconds(bb, x) for bb in ("V62/r37", "V65/r3a", "V65/r3b")
                           for x in (True, False))
                return rs, secs
            rs = corner([r for r in store[b]
                         if (r["gate"] > 0.98 if b == "V67/r47" else r["eng"] == 1) == bool(e)])
            return rs, corner_seconds(b, bool(e))
        ra, sa = pool(A)
        rb, sb = pool(Bk)
        aa, na = R.blockstat(ra, "e_30-49", 400.0)
        ab, nbb = R.blockstat(rb, "e_30-49", 400.0)
        p = R.fisher2x2(aa, na - aa, ab, nbb - ab) if min(na, nbb) >= 2 else np.nan
        ma = float(G.col(ra, "e_30-49").max()) if ra else np.nan
        mb = float(G.col(rb, "e_30-49").max()) if rb else np.nan
        print(f"  {lbl}")
        print(f"      exposure {sa:.1f} s vs {sb:.1f} s   burst blocks {aa}/{na} vs {ab}/{nbb}   "
              f"Fisher p = {p:.4g}   max envelope {ma:.0f} vs {mb:.0f}")

    # the POOLED dose test -- every Kd<=1 corner block ever recorded against every Kd=2 one, with
    # V67's LKAS-OFF corner joining the Kd<=1 pool because that is what the firmware runs there.
    lo_rs = corner([r for r in store["V67/r47"] if r["gate"] < 0.02]) \
        + corner([r for b in ("V59/r2c", "V64/r35", "V61/r31") for r in store[b]])
    hi_rs = corner([r for b in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[b]])
    al, nl = R.blockstat(lo_rs, "e_30-49", 400.0)
    ah, nh = R.blockstat(hi_rs, "e_30-49", 400.0)
    pp = R.fisher2x2(ah, nh - ah, al, nl - al)
    print(f"\n  POOLED, corner only:  Kd<=1 (V59+V64+V61 + V67's own LKAS-OFF arm) "
          f"{al}/{nl} burst blocks, max {G.col(lo_rs, 'e_30-49').max():.0f}")
    print(f"                        Kd=2  (V62+V65)                                "
          f"{ah}/{nh} burst blocks, max {G.col(hi_rs, 'e_30-49').max():.0f}")
    print(f"                        Fisher p = {pp:.4g}   "
          f"max-envelope ratio {G.col(hi_rs, 'e_30-49').max() / G.col(lo_rs, 'e_30-49').max():.1f}x")
    OUT["s5_pooled"] = dict(lo=(al, nl), hi=(ah, nh), p=pp)
    OUT["s5_corner"] = arms

    # ---- the power question ----------------------------------------------------------------------
    ref = [r for r in store["V65/r3a"] if r["v"] < CREEP and r["eng"] == 1]
    if ref and g1:
        pr = float(np.mean(G.col(ref, "e_30-49") > 400))
        n = len(g1)
        print(f"\n  POWER. V65/r3a engaged creep bursts (E>400) in {100 * pr:.1f}% of its windows.")
        print(f"  Route 47 has {n} engaged creep windows and "
              f"{int((G.col(g1, 'e_30-49') > 400).sum())}"
              f" bursts. Under V65's rate the expected count is {n * pr:.2f} and")
        print(f"  P(observe 0 | V65's rate) = {(1 - pr) ** n:.3f}. 🛑 A zero here is NOT evidence of")
        print(f"  a fix at any conventional level; the exposure is {n * 1.28:.0f} s of armed creep.")
        OUT["s5_power"] = dict(v65_rate=pr, n47=n, p_zero=float((1 - pr) ** n))

    OUT["s5"] = low


# ================================================================================ §6 ==============
def sec6(store):
    G.hdr("§6  THE WITHIN-ROUTE DOSE CURVE.  🛑 Read §0 first: gate=0 exists only below 8 m/s, so\n"
          "this table is a CREEP experiment. There is no highway arm to put beside it, and the\n"
          "22-24 Hz crossover cannot be tested at highway speed on any route in this kit.")
    cr = [r for r in store["V67/r47"] if r["v"] < 8.0]
    g1 = [r for r in cr if r["gate"] > 0.98]
    g0 = [r for r in cr if r["gate"] < 0.02]
    G.EPKEY = "blk"
    A, B = drop_eng_cell(g1), drop_eng_cell(g0)
    print(f"  gate=1 {len(g1)} windows / {len({r['blk'] for r in g1})} blocks   "
          f"gate=0 {len(g0)} windows / {len({r['blk'] for r in g0})} blocks")

    # OVERLAP FIRST. The kit's standard cell floor (>=4 windows and >=2 blocks per side) leaves ZERO
    # shared cells here, and boot_cellwise then returns a NaN point estimate beside a
    # healthy-LOOKING bootstrap CI -- resampling with replacement duplicates a block and inflates
    # the per-cell window count past the floor. Print the overlap before any ratio, so a degenerate
    # table cannot be read as a measurement.
    import collections
    ca = collections.Counter(r["cell"] for r in A)
    cb = collections.Counter(r["cell"] for r in B)
    bka, bkb = collections.defaultdict(set), collections.defaultdict(set)
    for r in A:
        bka[r["cell"]].add(r["blk"])
    for r in B:
        bkb[r["cell"]].add(r["blk"])
    shared = sorted(set(ca) & set(cb))
    print(f"\n  CELL OVERLAP (v-bin, effort-bin, rate-bin): {len(shared)} cells occupied by both "
          f"arms, of {len(set(ca) | set(cb))} total")
    print(f"  {'cell':14s} {'gate=1 win/blk':>15s} {'gate=0 win/blk':>15s}")
    for c in shared:
        print(f"  {str(c):14s} {f'{ca[c]}/{len(bka[c])}':>15s} {f'{cb[c]}/{len(bkb[c])}':>15s}")
    strict = [c for c in shared
              if ca[c] >= 4 and cb[c] >= 4 and len(bka[c]) >= 2 and len(bkb[c]) >= 2]
    print(f"  cells passing the kit's standard floor (>=4 windows AND >=2 blocks on BOTH sides): "
          f"{len(strict)}")
    if not strict:
        print("  🛑 ZERO. The two arms never visited the same operating cell: gate=1 creep is")
        print("     openpilot crawling in traffic (low effort, low rate), gate=0 creep is a person")
        print("     parking (high effort, high rate). The within-route dose curve is NOT ESTIMABLE")
        print("     on route 47. The table below runs at a RELAXED floor (>=2 windows, >=1 block)")
        print("     and is an INDICATION ONLY -- its CIs are not trustworthy and it is not evidence.")

    print(f"\n  {'band':8s} {'MEDIAN ratio':>12s} {'95% CI':>17s} {'cells':>6s} | "
          f"{'split-half null 95%':>21s} | {'verdict':>14s}")
    rows = {}
    for bd in ("1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49"):
        k = "e_" + bd
        med = G.boot_cellwise(A, B, k, RNG, nboot=1500, min_ep=1, min_win=2)
        nul = G.split_half_null(B, k, RNG, nrep=200, min_ep=1, min_win=2)
        ok = np.isfinite(med[0])
        inside = bool(ok and np.isfinite(nul[1]) and nul[1] <= med[0] <= nul[2])
        rows[bd] = dict(med=med[:3], ncell=med[3], null=nul, inside_null=inside, estimable=bool(ok))
        print(f"  {bd:8s} {med[0]:12.3f} [{med[1]:7.3f},{med[2]:7.3f}] {med[3]:6d} | "
              f"[{nul[1]:9.3f},{nul[2]:9.3f}] | "
              f"{('in null' if inside else 'outside') if ok else 'NOT ESTIMABLE':>14s}")
    print("\n  🛑 The 1-4 Hz row is the matching validity check: gate=1 and gate=0 differ hugely in")
    print("     what the driver was doing (LKAS on vs a person parking), so if 1-4 Hz is not ~1 the")
    print("     matching has failed and no other row in this table may be read as a dose effect.")
    print("  🛑 The 22-24 Hz CROSSOVER cannot be reproduced within this route. It was measured at")
    print("     CREEP with a within-build Kd contrast; route 47 has no Kd contrast at highway speed")
    print("     and no matched Kd contrast at creep. Reproducing it inside one route still needs a")
    print("     route that drives the SAME manoeuvres with LKAS on and off at the same speed.")
    OUT["s6"] = rows


# ================================================================================ §7 ==============
def sec7(store):
    G.hdr("§7  THE COMMA IMU.  An instrument on a different clock, in a different box.\n"
          "  CAN true rate 100.000 Hz (fold 50.000);  IMU hardware interval 9.899 ms = 101.019 Hz\n"
          "  (fold 50.509). A ONCE-FOLDED line reads 1.019 Hz HIGHER on the IMU; an unfolded one\n"
          "  reads the same. That is the alias test.")
    import glob
    import os
    ok = sorted(glob.glob(str(HERE.parent / "_scratch/cache/r47" / "r47s*_imu.npz")))
    if not ok:
        print("  no r47 IMU caches -- run:  python extract/extract_imu_cache.py r47")
        return
    print(f"  {len(ok)} r47 IMU segments present.")

    def uniform(t, x, fs):
        """Resample onto the sensor's own uniform grid. Drops are 1-2 samples in 256; linear
        interpolation over them is honest and is stated rather than hidden."""
        tt = np.arange(t[0], t[-1], 1.0 / fs)
        return tt, np.interp(tt, t, x)

    rows = []
    pairs = []
    for p in ok:
        s = int(os.path.basename(p).split("r47s")[1].split("_")[0])
        di = np.load(p)
        dc = load(s, G.BUILDS["V67/r47"]["cache"], "r47s")
        fsi = 1.0 / float(np.median(np.diff(di["at"])))
        ti, ay = uniform(np.asarray(di["at"], float), np.asarray(di["ay"], float), fsi)
        _, ax = uniform(np.asarray(di["at"], float), np.asarray(di["ax"], float), fsi)
        v = np.abs(dc["cs_v"])
        tc = np.asarray(dc["t"], float)
        x = np.asarray(dc["tq"], float)
        fI = np.fft.rfftfreq(NF, 1 / fsi)
        fC = np.fft.rfftfreq(NF, 1 / FS_TRUE)
        for a, b in runs_of(v >= HWY, tc, NF):
            for i in range(0, b - a - NF + 1, G.HOP):
                Pc = periodogram(x[a + i:a + i + NF], FS_TRUE, NF, True)
                if Pc is None:
                    continue
                t0 = tc[a + i]
                j = int(np.searchsorted(ti, t0))
                if j + NF > len(ti):
                    continue
                Pi = periodogram(ay[j:j + NF], fsi, NF, True)
                Pi2 = periodogram(ax[j:j + NF], fsi, NF, True)
                if Pi is None:
                    continue
                mC = (fC >= 30) & (fC <= 49)
                mI = (fI >= 30) & (fI <= 49)
                ec = float(np.sqrt(np.sum(Pc[mC])) / NF * 4)
                ei = float(np.sqrt(np.sum(Pi[mI])) / NF * 4)
                ei2 = float(np.sqrt(np.sum(Pi2[mI])) / NF * 4)
                fc0, pc = G.locate(fC, Pc, 34.0, 49.4)
                fi0, pi = G.locate(fI, Pi, 34.0, 49.4)
                rows.append(dict(seg=s, t0=float(t0), v=float(np.mean(v[a + i:a + i + NF])),
                                 ec=ec, ei=ei, ei2=ei2, fc=fc0, fi=fi0, pc=pc, pi=pi,
                                 blk=(s, (i // G.HOP) // 8, a)))
                if np.isfinite(fc0) and np.isfinite(fi0) and pc >= 4 and pi >= 4:
                    pairs.append((fc0, fi0, ec))
    if not rows:
        print("  no paired windows.")
        return
    ec = np.array([r["ec"] for r in rows])
    ei = np.array([r["ei"] for r in rows])
    hi = ec > np.percentile(ec, 95)
    print(f"\n  {len(rows)} paired highway windows.")
    print(f"  IMU lateral accel 30-49 Hz band amplitude:")
    print(f"      top-5% CAN-energy windows : median {np.median(ei[hi]):.4f} m/s^2")
    print(f"      bottom-50%                : median {np.median(ei[ec <= np.median(ec)]):.4f} m/s^2")
    print(f"      ratio {np.median(ei[hi]) / max(np.median(ei[ec <= np.median(ec)]), 1e-9):.2f}x")
    rho = float(np.corrcoef(np.log(ec + 1e-9), np.log(ei + 1e-12))[0, 1])
    print(f"      log-log correlation across all windows: {rho:.3f}")
    print("  ⇒ the highway event IS real vehicle motion, not an EPS telemetry artefact.")

    OUT["s7"] = dict(n=len(rows), rho=rho, imu_hi=float(np.median(ei[hi])),
                     imu_lo=float(np.median(ei[ec <= np.median(ec)])))

    # ---------------------------------------------------------------- the alias test --------------
    G.hdr("§7b  THE ALIAS TEST, with a KNOWN-UNFOLDED CONTROL.\n"
          "🛑 A free-band peak search on the two instruments does NOT pair them -- run that way the\n"
          "offset came out -1.19 Hz, which would put the line above 100 Hz, and that is an\n"
          "artefact of\n"
          "the two searches landing on different lines. The IMU is therefore searched only within\n"
          "+/-2.5 Hz of the CAN peak, and the test is quoted as a DIFFERENCE from a line whose\n"
          "fold state is already known: wheel order 3 at highway speed, which tracks v with slope\n"
          "3/2.0805 and so is unambiguously below 50 Hz.")

    def paired_offset(build, cache, pfx, segs, pick, band=2.5, chan="tq"):
        """(f_can, f_imu) pairs: locate on CAN, then locate on the IMU within +/-`band` of it."""
        got = []
        for s in segs:
            ip = HERE.parent / cache / f"{pfx}{s}_imu.npz"
            cp = G.BUILDS[build]["cache"] / f"{G.BUILDS[build]['pfx']}{s}.npz"
            if not ip.exists() or not cp.exists():
                continue
            di = np.load(ip)
            dc = load(s, G.BUILDS[build]["cache"], G.BUILDS[build]["pfx"])
            at = np.asarray(di["at"], float)
            fsi = 1.0 / float(np.median(np.diff(at)))
            ti = np.arange(at[0], at[-1], 1.0 / fsi)
            chans = {k: np.interp(ti, at, np.asarray(di[k], float)) for k in ("ax", "ay", "az")}
            tc = np.asarray(dc["t"], float)
            x = np.asarray(dc[chan], float)
            v = np.abs(dc["cs_v"])
            fC = np.fft.rfftfreq(NF, 1 / FS_TRUE)
            fI = np.fft.rfftfreq(NF, 1 / fsi)
            for a, b in runs_of(np.ones(len(tc), bool), tc, NF):
                for i in range(0, b - a - NF + 1, G.HOP):
                    Pc = periodogram(x[a + i:a + i + NF], FS_TRUE, NF, True)
                    if Pc is None:
                        continue
                    vv = float(np.mean(v[a + i:a + i + NF]))
                    lo, hi_ = pick(int(s), round(float(tc[a + i]), 2), vv, Pc, fC)
                    if lo is None:
                        continue
                    fc, pc = G.locate(fC, Pc, lo, hi_)
                    if not np.isfinite(fc) or pc < 4:
                        continue
                    j = int(np.searchsorted(ti, tc[a + i]))
                    if j + NF > len(ti):
                        continue
                    for cn in ("ax", "ay"):
                        Pi = periodogram(chans[cn][j:j + NF], fsi, NF, True)
                        if Pi is None:
                            continue
                        fi, pi = G.locate(fI, Pi, fc - band, fc + band)
                        if np.isfinite(fi) and pi >= 3:
                            got.append((cn, fc, fi, vv, fsi))
        return got

    # CONTROL: wheel order 3 at highway on r47, a line known to be unfolded.
    def pick_o3(sg, t0, vv, Pc, fC):
        o3 = 3 * vv / CIRC
        return (o3 - 2.0, o3 + 2.0) if (vv >= 24 and 36 <= o3 <= 47) else (None, None)

    ctl = paired_offset("V67/r47", "_scratch/cache/r47", "r47s",
                        G.BUILDS["V67/r47"]["segs"], pick_o3)
    # SUBJECT: the creep grind-#2 line on the Kd=2 builds, wherever the CAN burst is.
    ckey = {}
    for b in ("V62/r37", "V65/r3a", "V65/r3b"):
        for r in store[b]:
            if r["v"] < CREEP and r["e_30-49"] > 400:
                ckey.setdefault(b, set()).add((r["seg"], round(r["t0"], 2)))

    subj = []
    for b, cache, pfx in (("V62/r37", "_scratch/cache/r37", "r37s"), ("V65/r3a", "_scratch/cache/r3a", "r3as"),
                          ("V65/r3b", "_scratch/cache/r3b", "r3bs")):
        want = ckey.get(b, set())
        if not want:
            continue

        def pick_burst(sg, t0, vv, Pc, fC, _w=want):
            # ONLY the CAN-confirmed burst windows, keyed by (segment, window start time).
            return (34.0, 49.4) if (sg, t0) in _w else (None, None)
        subj += [(b,) + q for q in
                 paired_offset(b, cache, pfx, G.BUILDS[b]["segs"], pick_burst)]

    print(f"\n  {'population':34s} {'axis':>5s} {'n':>5s} {'f_CAN med':>10s} {'f_IMU med':>10s} "
          f"{'offset':>8s} {'95% CI':>17s}")
    res = {}
    for nm, got in (("CONTROL: wheel order 3, r47 hwy", [(c, fc, fi) for c, fc, fi, *_ in ctl]),
                    ("SUBJECT: creep grind #2 burst", [(c, fc, fi) for _, c, fc, fi, *_ in subj])):
        for ax in ("ax", "ay"):
            g = [(fc, fi) for c, fc, fi in got if c == ax]
            if len(g) < 15:
                print(f"  {nm:34s} {ax:>5s} {len(g):5d}   (too few)")
                continue
            d = np.array([fi - fc for fc, fi in g])
            bs = np.array([np.median(d[RNG.integers(0, len(d), len(d))]) for _ in range(3000)])
            res[f"{nm}|{ax}"] = dict(n=len(d), off=float(np.median(d)),
                                     lo=float(np.percentile(bs, 2.5)),
                                     hi=float(np.percentile(bs, 97.5)))
            print(f"  {nm:34s} {ax:>5s} {len(d):5d} "
                  f"{np.median([q[0] for q in g]):10.2f} {np.median([q[1] for q in g]):10.2f} "
                  f"{np.median(d):+8.3f} [{np.percentile(bs, 2.5):+7.3f},"
                  f"{np.percentile(bs, 97.5):+7.3f}]")
    print("\n  READ IT AS A DIFFERENCE: (subject offset) - (control offset) should be")
    print("      0.00 Hz  if grind #2 is genuinely near 44.6 Hz (unfolded, same as the control)")
    print("     +1.02 Hz  if it is really near 55.4 Hz")
    print("     -1.02 Hz  if it is really near 144.6 Hz")
    for ax in ("ax", "ay"):
        a = res.get(f"CONTROL: wheel order 3, r47 hwy|{ax}")
        b = res.get(f"SUBJECT: creep grind #2 burst|{ax}")
        if a and b:
            print(f"      {ax}: {b['off'] - a['off']:+.3f} Hz "
                  f"(control {a['off']:+.3f} on n={a['n']}, subject {b['off']:+.3f} on n={b['n']})")
    print("\n  🛑 The two instruments are only 1.02 Hz apart in fold point, the bin width is 0.39 Hz,")
    print("     and the residual scale uncertainty on the IMU clock is ~0.2 Hz at 44 Hz. Treat this")
    print("     as SUGGESTIVE. What would close it: a log at a DIFFERENT sensor ODR (the")
    print("     LSM6DS3TR-C also runs 208/416 Hz), which moves the fold point by tens of Hz.")
    OUT["s7_alias"] = res


# ================================================================================ §8 ==============
def sec8(store):
    G.hdr("§8  THE ATLAS EPISODES.  Independent episode definitions from `studies/sessions/r47/r47_atlas.py`\n"
          "(_scratch/cache/r47/r47_maneuvers.json): 21 highway manoeuvres, 21 speed-matched straight-line\n"
          "controls, 35 low-speed episodes. Scored on RAW frames inside each episode's own\n"
          "spans, so\n"
          "a 1.5 s episode is not thrown away for being shorter than a 2.56 s window.")
    ap = HERE.parent / "_scratch/cache/r47" / "r47_maneuvers.json"
    if not ap.exists():
        print("  no atlas file -- §4's own manoeuvre definition (angle excursion >= 4 deg) stands.")
        return
    atlas = json.loads(ap.read_text())
    NF8 = 128                      # 1.28 s, 0.78 Hz bins -- still 25 bins across 30-49 Hz
    taper = np.hanning(NF8) + 1e-3
    cw = slice(int(0.2 * NF8), int(0.8 * NF8))
    cache = {}

    def score(ep):
        """max, over 1.28 s sub-windows inside the episode, of the 30-49 Hz envelope p99."""
        best, n = 0.0, 0
        for sp in ep.get("spans", []):
            s = int(sp["seg"])
            d = cache.setdefault(s, load(s, G.BUILDS["V67/r47"]["cache"], "r47s"))
            x = np.asarray(d["tq"], float)[int(sp["i0"]):int(sp["i1"])]
            for i in range(0, max(len(x) - NF8 + 1, 0), NF8 // 2):
                best = max(best, G.win_env(x[i:i + NF8], FS_TRUE, 30.0, 49.0, taper, cw))
                n += 1
        return (best if n else np.nan), n

    print(f"  {'population':34s} {'n ep':>5s} {'sec':>7s} {'E p50':>7s} {'p90':>8s} {'max':>8s} "
          f"{'ep>300':>7s}")
    res = {}
    for nm, key, sel in (("HIGHWAY MANOEUVRE", "maneuvers", lambda e: True),
                         ("highway matched CONTROL", "controls", lambda e: True),
                         ("low speed, gate=1 (Kd=2)", "lowspeed", lambda e: e["g6806_duty"] > 0.9),
                         ("low speed, gate=0 (Kd=1)", "lowspeed", lambda e: e["g6806_duty"] < 0.1),
                         ("low speed gate=1, tq_p50>1200", "lowspeed",
                          lambda e: e["g6806_duty"] > 0.9 and e["tq_p50"] > 1200),
                         ("low speed gate=0, tq_p50>1200", "lowspeed",
                          lambda e: e["g6806_duty"] < 0.1 and e["tq_p50"] > 1200)):
        eps = [e for e in atlas.get(key, []) if sel(e)]
        vals = [score(e)[0] for e in eps]
        vals = np.array([v for v in vals if np.isfinite(v)])
        if not len(vals):
            print(f"  {nm:34s} {len(eps):5d}   (no scorable episode)")
            continue
        secs = sum(e["dur"] for e in eps)
        res[nm] = dict(n=len(vals), secs=secs, p90=float(np.percentile(vals, 90)),
                       mx=float(vals.max()), over=int((vals > 300).sum()))
        print(f"  {nm:34s} {len(vals):5d} {secs:7.1f} {np.median(vals):7.1f} "
              f"{np.percentile(vals, 90):8.1f} {vals.max():8.1f} {int((vals > 300).sum()):7d}")
    mv = np.array([score(e)[0] for e in atlas.get("maneuvers", [])])
    cv = np.array([score(e)[0] for e in atlas.get("controls", [])])
    mv, cv = mv[np.isfinite(mv)], cv[np.isfinite(cv)]
    if len(mv) and len(cv):
        a = auc(mv, cv)
        am, ac = int((mv > 300).sum()), int((cv > 300).sum())
        p = R.fisher2x2(am, len(mv) - am, ac, len(cv) - ac)
        print(f"\n  manoeuvre vs its OWN speed-matched control, EPISODE level (each episode is one")
        print(f"  independent sample -- no block bootstrap needed):")
        print(f"      AUC {a:.3f}   episodes over 300 counts: {am}/{len(mv)} vs {ac}/{len(cv)}   "
              f"Fisher p = {p:.4g}")
        print(f"      median envelope {np.median(mv):.1f} vs {np.median(cv):.1f} "
              f"= {np.median(mv) / max(np.median(cv), 1e-9):.2f}x")
        OUT["s8_manoeuvre"] = dict(auc=a, am=am, nm=len(mv), ac=ac, nc=len(cv), p=p)
    print("\n  🛑 The low-speed rows are the operator's 'is it still there at low speed' question in")
    print("     its cleanest form. Read the SECONDS column beside them.")
    OUT["s8"] = res


# ================================================================================ main ============
def main():
    want = set(sys.argv[1:]) or {"0", "1", "2", "3", "4", "5", "6", "7", "8"}
    store = R.records()
    for k, fn in (("0", sec0), ("1", sec1), ("2", sec2), ("3", sec3), ("4", sec4), ("5", sec5),
                  ("6", sec6), ("7", sec7), ("8", sec8)):
        if k in want:
            fn(store)
    OUTJSON.write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
