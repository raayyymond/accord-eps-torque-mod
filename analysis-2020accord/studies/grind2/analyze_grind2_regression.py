#!/usr/bin/env python3
"""Is the 30-49 Hz band a V62/V65-INTRODUCED regression, or was it always there?

Deliverables A-E. Run extract/build_grind2_records.py first.

    A  matched-cell 30-49 Hz envelope p99 + prominence, Kd=2 vs Kd=1, episode-bootstrap CI,
       against each build's own split-half null
    B  the same for the pre-declared negative control 24-28 Hz and the matching-validity band 1-4 Hz
       (🛑 30-40 Hz was V62's own negative control for the 18-22 Hz claim; it is the SUBJECT here)
    C  grind #1: 18-22 Hz in the engaged creep arm, V62 vs V59, by this script's own method
    D  the manual/disengaged, near-stationary, high-effort arm
    E  dose-response over Kd = 0 / 1 / 2 -- the highest-value single result

Usage:  python studies/grind2/analyze_grind2_regression.py [ep|blk]
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
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_grind2_records.pkl"
OUTJSON = HERE / "_scratch/out/_grind2_regression.json"
RNG = np.random.default_rng(20260801)
NBOOT = 2000
NULLREP = 300

KEYS = [("e_" + b, f"env p99 {b} Hz") for b in G.BANDS] + \
       [("p_" + b, f"prom {b} Hz") for b in ("18-22", "24-28", "30-40", "40-49", "30-49")]


def pool(store, names):
    return [r for n in names for r in store.get(n, [])]


def fmt(x, w=8, p=3):
    return f"{x:{w}.{p}f}" if np.isfinite(x) else f"{'n/a':>{w}s}"


def line(label, ratio, lo, hi, ncell, na, nb, floor=None):
    s = (f"  {label:22s} {fmt(ratio, 7)}  [{fmt(lo, 6)}, {fmt(hi, 6)}]  "
         f"cells={ncell:2d}  units {na:3d}/{nb:3d}")
    if floor is not None and np.isfinite(floor[1]):
        inside = floor[1] <= ratio <= floor[2]
        s += f"   null [{floor[1]:.3f}, {floor[2]:.3f}]  {'INSIDE NULL' if inside else 'outside'}"
    return s


def main():
    G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
    out = {"epkey": G.EPKEY, "nboot": NBOOT}

    kd1 = pool(store, G.DOSE[1.0])
    kd2 = pool(store, G.DOSE[2.0])
    kd0 = pool(store, G.DOSE[0.0])

    # ============================================================ split-half nulls ===============
    G.hdr(f"NOISE FLOOR -- SPLIT-HALF NULL inside each dose pool (unit = '{G.EPKEY}', "
          f"{NULLREP} reps)\n"
          "Each build's own data is halved at the resampling-unit level and run through the "
          "IDENTICAL\nstratified matched-cell estimator. Nothing inside this interval is a finding.")
    nulls = {}
    print(f"  {'band':10s} {'pool':>10s} {'median':>8s} {'2.5%':>8s} {'97.5%':>8s} "
          f"{'floor (max dev)':>16s}")
    for key, lbl in [("e_" + b, b) for b in ("1-4", "18-22", "24-28", "30-49")]:
        for nm, rs in (("Kd=1", kd1), ("Kd=2", kd2)):
            m, lo, hi = G.split_half_null(rs, key, RNG, nrep=NULLREP)
            nulls[(key, nm)] = (m, lo, hi)
            dev = max(hi, 1 / lo) if np.isfinite(lo) and lo > 0 else np.nan
            print(f"  {lbl:10s} {nm:>10s} {fmt(m)} {fmt(lo)} {fmt(hi)} {fmt(dev, 16)}x")
    # the operative floor for a Kd1-vs-Kd2 comparison: the wider of the two
    floor = {}
    for key in [k for k, _ in KEYS]:
        pass
    for key in ["e_" + b for b in ("1-4", "18-22", "24-28", "30-49")]:
        a, b = nulls[(key, "Kd=1")], nulls[(key, "Kd=2")]
        floor[key] = (1.0, min(a[1], b[1]), max(a[2], b[2]))
    out["nulls"] = {f"{k}|{n}": v for (k, n), v in nulls.items()}

    # ============================================================ A + B ==========================
    G.hdr("A + B.  MATCHED-CELL RATIO  Kd=2 (V62 r37 + V65 r3a/r3b) / Kd=1 (V59 r2c + V64 r35)\n"
          ">1 means the doubled derivative gain made that band LOUDER.")
    print(f"  {'band':22s} {'ratio':>7s}  {'95% CI (units bootstrap)':>22s}")
    res = {}
    for key, lbl in KEYS:
        r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(kd2, kd1, key, RNG, nboot=NBOOT)
        res[key] = dict(ratio=r, lo=lo, hi=hi, ncell=nc, na=na, nb=nb)
        print(line(lbl, r, lo, hi, nc, na, nb, floor.get(key)))
    out["A_kd2_vs_kd1"] = res

    # the per-cell table for the headline band, so a single cell cannot be hiding the effect
    G.hdr("A.  PER-CELL DETAIL, 30-49 Hz envelope p99   (cell = eng, v-bin, eff-bin, rate-bin)")
    _, _, _, _, _, _, tab, _ = G.boot_cellwise(kd2, kd1, "e_30-49", RNG, nboot=0)
    print(f"  {'cell':20s} {'nwin2':>6s} {'nwin1':>6s} {'nU2':>4s} {'nU1':>4s} "
          f"{'Kd2':>8s} {'Kd1':>8s} {'ratio':>7s} {'weight':>7s}")
    for c, na, nb, nea, neb, sa, sb, rr, w in sorted(tab, key=lambda z: -z[8]):
        print(f"  {str(c):20s} {na:6d} {nb:6d} {nea:4d} {neb:4d} {sa:8.1f} {sb:8.1f} "
              f"{rr:7.3f} {w:7.2f}")

    # ============================================================ C ==============================
    G.hdr("C.  GRIND #1 CONTROL -- 18-22 Hz, ENGAGED CREEP arm (eng=1, v in 0.5-4 m/s)")
    ce2 = [r for r in pool(store, ["V62/r37"]) if r["eng"] == 1 and 0.5 <= r["v"] < 4.0]
    ce1 = [r for r in pool(store, ["V59/r2c", "V64/r35"])
           if r["eng"] == 1 and 0.5 <= r["v"] < 4.0]
    ce65 = [r for r in pool(store, ["V65/r3a", "V65/r3b"])
            if r["eng"] == 1 and 0.5 <= r["v"] < 4.0]
    ce0 = [r for r in pool(store, ["V61/r31"]) if r["eng"] == 1 and 0.5 <= r["v"] < 4.0]
    print(f"  windows: V59+V64={len(ce1)}  V61={len(ce0)}  V62={len(ce2)}  V65={len(ce65)}")
    cres = {}
    for nm, a, b in (("V62 / V59+V64", ce2, ce1), ("V65 / V59+V64", ce65, ce1),
                     ("V61 / V59+V64", ce0, ce1), ("V65 / V62", ce65, ce2)):
        for key, lbl in (("e_18-22", "env p99 18-22"), ("p_18-22", "prom 18-22"),
                         ("e_30-49", "env p99 30-49"), ("e_24-28", "env p99 24-28")):
            r, lo, hi, nc, na, nb, _, _ = G.boot_cellwise(a, b, key, RNG, nboot=NBOOT,
                                                          min_ep=2, min_win=5)
            cres[f"{nm}|{key}"] = dict(ratio=r, lo=lo, hi=hi, ncell=nc)
            print(line(f"{nm:14s} {lbl}", r, lo, hi, nc, na, nb))
    out["C_creep"] = cres
    # unmatched medians so the reader can see the raw level, not only a ratio
    print("\n  raw medians in this arm (no matching):")
    print(f"    {'build':14s} {'nwin':>5s} {'18-22':>8s} {'24-28':>8s} {'30-49':>8s} "
          f"{'eff med':>8s} {'v med':>6s} {'rate med':>8s}")
    for nm, rs in (("V61 Kd0", ce0), ("V59+V64 Kd1", ce1), ("V62 Kd2", ce2), ("V65 Kd2", ce65)):
        if not rs:
            continue
        print(f"    {nm:14s} {len(rs):5d} {np.median(G.col(rs, 'e_18-22')):8.1f} "
              f"{np.median(G.col(rs, 'e_24-28')):8.1f} {np.median(G.col(rs, 'e_30-49')):8.1f} "
              f"{np.median(G.col(rs, 'eff')):8.0f} {np.median(G.col(rs, 'v')):6.2f} "
              f"{np.median(G.col(rs, 'rate')):8.1f}")

    # ============================================================ D ==============================
    G.hdr("D.  MANUAL / DISENGAGED arm -- NEAR-STATIONARY, HIGH EFFORT (eng=0, v<2 m/s, eff>=800)\n"
          "🛑 The standing convention: a |v|>=0.3 'moving' gate or a missing effort gate each\n"
          "erases manual EPS instability on its own. Neither is applied here.")
    def marm(names):
        return [r for r in pool(store, names)
                if r["eng"] == 0 and r["v"] < 2.0 and r["eff"] >= 800]
    m0, m1, m2, m62, m65 = (marm(["V61/r31"]), marm(["V59/r2c", "V64/r35"]),
                            marm(G.DOSE[2.0]), marm(["V62/r37"]), marm(["V65/r3a", "V65/r3b"]))
    print(f"  windows: V61={len(m0)}  V59+V64={len(m1)}  V62={len(m62)}  V65={len(m65)}")
    print(f"\n  raw medians (and p90) of the envelope p99, counts:")
    print(f"    {'build':14s} {'nwin':>5s} {'nUnit':>6s} | " +
          " ".join(f"{b:>13s}" for b in ("1-4", "6-9", "18-22", "24-28", "30-49")))
    for nm, rs in (("V61 Kd0", m0), ("V59+V64 Kd1", m1), ("V62 Kd2", m62), ("V65 Kd2", m65)):
        if not rs:
            print(f"    {nm:14s} {0:5d}")
            continue
        cells = " ".join(f"{np.median(G.col(rs, 'e_' + b)):6.1f}/"
                         f"{np.percentile(G.col(rs, 'e_' + b), 90):6.1f}"
                         for b in ("1-4", "6-9", "18-22", "24-28", "30-49"))
        print(f"    {nm:14s} {len(rs):5d} {len({r[G.EPKEY] for r in rs}):6d} | {cells}")
    dres = {}
    print()
    for nm, a, b in (("Kd2 / Kd1", m2, m1), ("Kd0 / Kd1", m0, m1)):
        for key in ("e_30-49", "e_24-28", "e_18-22", "e_1-4", "p_30-49"):
            r, lo, hi, nc, na, nb, _, _ = G.boot_cellwise(a, b, key, RNG, nboot=NBOOT,
                                                          min_ep=2, min_win=5)
            dres[f"{nm}|{key}"] = dict(ratio=r, lo=lo, hi=hi, ncell=nc)
            print(line(f"{nm:10s} {key}", r, lo, hi, nc, na, nb))
    out["D_manual"] = dres

    # ============================================================ E ==============================
    G.hdr("E.  DOSE-RESPONSE over Kd = 0 (V61) / 1 (V59,V64) / 2 (V62,V65)\n"
          "🛑 Kd=0 exists ONLY on route 31, a parking-lot route. The three-dose comparison is\n"
          "therefore restricted to the cells route 31 actually occupies -- creep and stationary.")
    # cells occupied by all three doses
    def cellset(rs, minw=8):
        c = {}
        for r in rs:
            c[r["cell"]] = c.get(r["cell"], 0) + 1
        return {k for k, v in c.items() if v >= minw}
    shared3 = cellset(kd0) & cellset(kd1) & cellset(kd2)
    print(f"  cells occupied by all three doses (>=8 windows each): {sorted(shared3)}")
    eres = {}
    print(f"\n  {'band':10s} | " + " ".join(f"{d:>26s}" for d in ("Kd=0", "Kd=1", "Kd=2")) +
          "   monotone?")
    for b in G.BANDS:
        key = "e_" + b
        row, vals = [], []
        for dose in (0.0, 1.0, 2.0):
            rs = [r for r in pool(store, G.DOSE[dose]) if r["cell"] in shared3]
            pt, lo, hi = G.boot_median_ci(rs, key, RNG, nboot=NBOOT)
            row.append(f"{pt:8.1f} [{lo:6.1f},{hi:6.1f}]")
            vals.append(pt)
            eres[f"{b}|Kd{dose:g}"] = dict(point=pt, lo=lo, hi=hi, n=len(rs))
        mono = ("UP" if vals[0] < vals[1] < vals[2] else
                "DOWN" if vals[0] > vals[1] > vals[2] else "-")
        print(f"  {b:10s} | " + " ".join(f"{s:>26s}" for s in row) + f"   {mono}")
    out["E_dose"] = eres

    # the same, but as matched ratios against Kd=1 so exposure cannot drive the trend
    print(f"\n  matched-cell ratios against Kd=1 (same estimator as A):")
    print(f"  {'band':10s} {'Kd0/Kd1':>26s} {'Kd2/Kd1':>26s}")
    for b in G.BANDS:
        key = "e_" + b
        r0 = G.boot_cellwise(kd0, kd1, key, RNG, nboot=NBOOT, min_ep=2, min_win=5)
        r2 = G.boot_cellwise(kd2, kd1, key, RNG, nboot=NBOOT, min_ep=2, min_win=5)
        eres[f"{b}|ratio0"] = dict(ratio=r0[0], lo=r0[1], hi=r0[2], ncell=r0[3])
        eres[f"{b}|ratio2"] = dict(ratio=r2[0], lo=r2[1], hi=r2[2], ncell=r2[3])
        print(f"  {b:10s} {r0[0]:7.3f} [{r0[1]:6.3f},{r0[2]:6.3f}] c={r0[3]:2d} "
              f"{r2[0]:7.3f} [{r2[1]:6.3f},{r2[2]:6.3f}] c={r2[3]:2d}")

    # ============================================================ per-route sanity ===============
    G.hdr("PER-ROUTE (not per-dose): every route against V59/r2c, 30-49 Hz env p99.\n"
          "Two routes at the SAME Kd differing by more than the null is a route effect, and it\n"
          "bounds how much of any Kd effect is really firmware.")
    for b in G.ORDER:
        if b == "V59/r2c" or not store.get(b):
            continue
        r, lo, hi, nc, na, nb, _, _ = G.boot_cellwise(store[b], store["V59/r2c"], "e_30-49",
                                                      RNG, nboot=NBOOT, min_ep=2, min_win=5)
        print(line(f"{b} / V59/r2c", r, lo, hi, nc, na, nb))
    print("\n  same, 24-28 Hz negative control:")
    for b in G.ORDER:
        if b == "V59/r2c" or not store.get(b):
            continue
        r, lo, hi, nc, na, nb, _, _ = G.boot_cellwise(store[b], store["V59/r2c"], "e_24-28",
                                                      RNG, nboot=NBOOT, min_ep=2, min_win=5)
        print(line(f"{b} / V59/r2c", r, lo, hi, nc, na, nb))

    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
