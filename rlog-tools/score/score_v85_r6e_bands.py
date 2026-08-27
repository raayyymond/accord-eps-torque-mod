#!/usr/bin/env python3
"""SCORE THE V85 FLIGHT (route `6e`) -- band ratios against V84/`6d` and V81/`67`.

🛑 THE INSTRUMENT IS THE CORPUS'S, NOT A NEW ONE.  Every band envelope, prominence, episode
bootstrap, split-half null and cell-stratified ratio is `_grind2_lib`'s, reached through
`score_v84_r6d` (which itself reaches `compare_v75_v76_v80_grind` + `compare_r67_v81_grind`).  This
file adds ONE route to the build table and ONE row to the ladder.  Nothing numeric is redefined.

🛑 THE OTHER BUILDS' WINDOW RECORDS ARE **LOADED, NOT RECOMPUTED**, from
`_scratch/cache/r6d/records_v84_score.pkl` -- read-only.  That pickle is a REPORTED artefact, so this file
never writes it; V85's records are merged in memory and saved to `_scratch/cache/r6e/records_v85_score.pkl`.
Loading rather than rebuilding also guarantees V84's numbers here are bit-identical to the ones
already reported for route `6d`.

METHOD RULES, each of which has already retracted a claim in this kit
  * Bootstrap over EPISODES, never windows (`memory/feedback/measurement/feedback-episodes-not-windows.md`).
  * The SPLIT-HALF NULL is computed and printed BEFORE any cross-build ratio.  A ratio inside the
    wider of the two builds' nulls is NOT a result.
  * A per-window SPEED CENSUS precedes every averaged comparison -- wheel order 1 sits at
    v / 2.0805 Hz and MOVES, so mismatched speed distributions manufacture an "only on route X" line.
  * `32-38` Hz is the PRE-DECLARED NEGATIVE CONTROL and is printed beside every claim.
  * `imu2049` (chassis vertical 20-49 Hz) is the ROAD-ROUGHNESS falsifier and is reported per pair.

🛑🛑 `26-31` Hz IS NOT SCORED ON THIS ROUTE.  Route `6e` supplies 22.4 s engaged above 80 km/h
against route `6d`'s 158.1 s.  That is V83a-class exposure, and STATE.md's own METHOD RULE
("a pre-registered falsifier only fires if the lever was IN FORCE and the exposure was adequate")
was written after exactly this mistake.  The band is COMPUTED and PRINTED so the number exists, and
it is labelled DO-NOT-SCORE everywhere it appears.

🛑 TERMINOLOGY.  "grind #1/#2", "the ring", "S1..S4" are KIT JARGON for frequency bands.  They are
not symptoms the operator named.  Headings carry HIS words; the band is cited as the instrument.

Usage:
    python score/score_v85_r6e_bands.py records   # build V85's window records (slow, ~2 min)
    python score/score_v85_r6e_bands.py analyze   # B0-B7
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import score_v84_r6d as S  # noqa: E402  -- THE scoring harness; its instrument is _grind2_lib's
import compare_v75_v76_v80_grind as M  # noqa: E402
import _grind2_lib as G  # noqa: E402
import _r47_lib as R47  # noqa: E402

CACHE6E = ROOT / "_scratch/cache/r6e"
MYPKL = CACHE6E / "records_v85_score.pkl"
CIRC = S.CIRC

# ---- the new route.  `parked` = segments with ZERO engaged seconds, the convention route 68 used
# ---- (its seg 0 and seg 7 both read eng_sec 0.0).  Route 6e: seg 7 only -- seg 0 has 7.24 s.
NEW85 = dict(cache=CACHE6E, pfx="r6es", segs=list(range(8)), parked=[7], kd=9.85)

LADDER = ["V76/r65", "V80/r66", "V67/r47", "V68/r4e", "V81/r67", "V83a/r68", "V84/r6d", "V85/r6e"]
# 🛑 V85's own comparisons come first; the rest are context already in the record.
PAIRS = [("V85/r6e", "V84/r6d"), ("V85/r6e", "V81/r67"), ("V85/r6e", "V67/r47"),
         ("V85/r6e", "V68/r4e"), ("V85/r6e", "V83a/r68"), ("V84/r6d", "V81/r67")]

BANDS = ["6-9", "18-22", "40-49", "32-38", "26-31", "30-49"]
NEGCTRL = "32-38"
DO_NOT_SCORE = {"26-31"}
BAND_TAG = {
    "6-9":   "MICRO-RATCHETING   (operator: 'barely, perceptibly better (somewhat unsure)')",
    "18-22": "GRINDING/VIBRATION (operator: 'a little bit better, still barely perceptible')",
    "40-49": "regression check only -- operator reports NONE from hard turning or highway",
    "32-38": "🛑 PRE-DECLARED NEGATIVE CONTROL",
    "26-31": "🛑 DO NOT SCORE -- 22.4 s engaged >80 km/h on this route",
    "30-49": "HF floor (context)",
}
STRATA = M.STRATA
RNG = np.random.default_rng(85_6014)
OUT = {}


def register():
    S.register()                                    # V76/V80/V67/V68/V81 + V83a/V84
    G.BUILDS["V85/r6e"] = dict(cache=NEW85["cache"], pfx=NEW85["pfx"], segs=NEW85["segs"],
                               kd=NEW85["kd"])
    S.PARKED["V85/r6e"] = NEW85["parked"]


def build_records(rebuild=False):
    """V85's records computed here; every other build's LOADED from V84's pickle, read-only."""
    register()
    if MYPKL.exists() and not rebuild:
        with open(MYPKL, "rb") as fh:
            st = pickle.load(fh)
        if st.get("__bands__") == sorted(M.BANDS_EXT) and all(b in st for b in LADDER):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    with open(S.MYPKL, "rb") as fh:                 # 🛑 READ-ONLY. Never written by this file.
        base = pickle.load(fh)
    assert base.get("__bands__") == sorted(M.BANDS_EXT), \
        "🛑 V84's pickle was built with a different band set -- do not mix"
    st = {"__bands__": sorted(M.BANDS_EXT)}
    for b in LADDER:
        if b in base:
            st[b] = base[b]
            print(f"  {b}: {len(st[b])} windows (loaded from V84's pickle)", flush=True)
            continue
        print(f"  wrecs {b} ...", flush=True)
        st[b] = S.augment3(M.augment2(R47.augment(G.wrecs(b))))
        print(f"    {len(st[b])} windows", flush=True)
    CACHE6E.mkdir(exist_ok=True)
    with open(MYPKL, "wb") as fh:
        pickle.dump(st, fh)
    return {k: v for k, v in st.items() if not k.startswith("__")}


def eng(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 1 and r["seg"] not in S.PARKED.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def man(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 0 and r["seg"] not in S.PARKED.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def nunits(rs, key=None):
    return len({r[key or G.EPKEY] for r in rs})


def loo(tab):
    """Leave-one-CELL-out on the pooled weighted log-ratio, recomputed from `boot_cellwise`'s table.

    `tab` rows are (cell, nA, nB, nepA, nepB, statA, statB, ratio, weight).  Exact, not resampled --
    this answers "is the pooled figure carried by ONE cell?", which a CI cannot.
    """
    if len(tab) < 2:
        return None
    w = np.array([r[8] for r in tab], float)
    lr = np.array([np.log(r[7]) for r in tab], float)
    full = np.exp((w * lr).sum() / w.sum())
    vals = []
    for i in range(len(tab)):
        k = np.ones(len(tab), bool)
        k[i] = False
        vals.append(np.exp((w[k] * lr[k]).sum() / w[k].sum()))
    return full, float(min(vals)), float(max(vals)), int(np.argmax(np.abs(np.log(vals) - np.log(full))))


def analyze():
    G.EPKEY = "blk"
    R = build_records()
    for b in LADDER:
        S._add_imu2049(R[b])

    # =============================================================== B0 EXPOSURE ==================
    S.hdr("B0  EXPOSURE CENSUS -- engaged only, parked segments dropped.\n"
          "    A stratum with < 5 windows is not scored; < ~8 blocks has no usable CI.")
    print(f"{'build':10s} {'wins':>5s} {'sec':>7s} {'blk':>4s} {'run':>4s} | "
          + " ".join(f"{nm:>13s}" for nm, _, _ in STRATA))
    OUT["exposure"] = {}
    for b in LADDER:
        e = eng(R[b], b)
        row = [f"{b:10s} {len(e):5d} {len(e) * 1.28:7.1f} {nunits(e,'blk'):4d} {nunits(e,'ep'):4d} |"]
        st = {}
        for nm, lo, hi in STRATA:
            s = eng(R[b], b, lo, hi)
            row.append(f"  {len(s):4d}w/{nunits(s,'blk'):2d}b ")
            st[nm] = dict(n=len(s), blk=nunits(s, "blk"), sec=len(s) * 1.28,
                          v_med=float(np.median(G.col(s, "v"))) if s else float("nan"),
                          eff_med=float(np.median(G.col(s, "eff"))) if s else float("nan"),
                          rate_med=float(np.median(G.col(s, "rate"))) if s else float("nan"))
        print("".join(row))
        OUT["exposure"][b] = dict(n=len(e), sec=len(e) * 1.28, strata=st)

    S.hdr("B0b PER-WINDOW SPEED CENSUS -- 🛑 MANDATORY before any averaged comparison.\n"
          "    Wheel order 1 = v / 2.0805 Hz and MOVES WITH SPEED.")
    VB = [(0.0, 0.5), (0.5, 1.5), (1.5, 2.78), (2.78, 5.0), (5.0, 8.0), (8.0, 11.1),
          (11.1, 16.0), (16.0, 22.2), (22.2, 40.0)]
    print(f"{'build':10s} " + " ".join(f"{lo:.1f}-{hi:.1f}".rjust(10) for lo, hi in VB))
    OUT["speed_census"] = {}
    for b in LADDER:
        v = G.col(eng(R[b], b), "v")
        cnt = [int(((v >= lo) & (v < hi)).sum()) for lo, hi in VB]
        print(f"{b:10s} " + " ".join(f"{100 * c / max(len(v),1):9.1f}%" for c in cnt))
        OUT["speed_census"][b] = dict(frac=[c / max(len(v), 1) for c in cnt], n=len(v))
    print("\n  wheel-order contamination: % of engaged windows whose order-1 / order-2 line lands "
          "INSIDE each band")
    print(f"{'build':10s} {'ord1 med':>9s} | " + " ".join(f"{bd:>12s}" for bd in BANDS))
    for b in LADDER:
        v = G.col(eng(R[b], b), "v")
        o1, o2 = v / CIRC, 2 * v / CIRC
        row = f"{b:10s} {np.median(o1):9.2f} | "
        for bd in BANDS:
            lo, hi = M.BANDS_EXT[bd]
            row += f" {100*np.mean((o1>=lo)&(o1<=hi)):4.1f}/{100*np.mean((o2>=lo)&(o2<=hi)):4.1f}%"
        print(row)

    # =============================================================== B1 NULLS (FIRST) =============
    S.hdr("B1  SPLIT-HALF NULL -- computed and printed BEFORE any cross-build ratio.\n"
          "    Each route halved against ITSELF with the IDENTICAL estimator, 300 halvings.\n"
          "    🛑 A ratio inside the wider of the two builds' nulls is NOT a result.")
    OUT["null"] = {}
    print(f"{'band':8s} {'build':10s} {'null median':>12s} {'null 95% interval':>26s}")
    for bd in BANDS:
        for b in LADDER:
            n = G.split_half_null(eng(R[b], b), "e_" + bd, RNG, nrep=300, min_ep=2, min_win=4)
            print(f"{bd:8s} {b:10s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]")
            OUT["null"].setdefault(bd, {})[b] = list(n)
        print()

    S.hdr("B1b CREEP-ONLY SPLIT-HALF NULL (<10 km/h, engaged) -- the null that governs the creep\n"
          "    verdicts, because both symptoms the operator scored are creep symptoms.")
    OUT["null_creep"] = {}
    nm0, lo0, hi0 = STRATA[0]
    for bd in ("6-9", "18-22", "40-49", NEGCTRL):
        for b in LADDER:
            s = eng(R[b], b, lo0, hi0)
            if len(s) < 8:
                print(f"{bd:8s} {b:10s}  -- only {len(s)} creep windows, null undefined --")
                OUT["null_creep"].setdefault(bd, {})[b] = None
                continue
            n = G.split_half_null(s, "e_" + bd, RNG, nrep=300, min_ep=1, min_win=3)
            print(f"{bd:8s} {b:10s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]   "
                  f"({len(s)}w / {nunits(s,'blk')}blk)")
            OUT["null_creep"].setdefault(bd, {})[b] = list(n)
        print()

    # =============================================================== B2 ROAD ROUGHNESS ============
    S.hdr("B2  ROAD-ROUGHNESS CONTROL -- chassis vertical IMU 20-49 Hz envelope, same cells.\n"
          "    🛑 V84's road was 1.2x rougher than V81's and that mattered.  A band ratio is only\n"
          "    interpretable once this is beside it.")
    OUT["roughness"] = {}
    print(f"{'pair':22s} {'imu2049 A/B':>12s} {'95% CI':>20s} {'cells':>6s}")
    for A, B in PAIRS:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "imu2049", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"{A.split('/')[0]+'/'+B.split('/')[0]:22s} {res[0]:12.3f} "
              f"[{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d}")
        OUT["roughness"][f"{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    print("\n  absolute median imu2049 (m/s^2 envelope), engaged:")
    for b in LADDER:
        e = eng(R[b], b)
        print(f"    {b:10s} {np.nanmedian(G.col(e, 'imu2049')):8.4f}   "
              f"(n finite {int(np.isfinite(G.col(e,'imu2049')).sum())})")

    # =============================================================== B3 BAND TABLE ================
    S.hdr("B3  SPEED-STRATIFIED BAND TABLE -- engaged only.  median [2.5%, 97.5%] block-bootstrap.\n"
          "    e_band = p99 analytic band-envelope AMPLITUDE of the torsion bar, counts (p-p = 2x).")
    OUT["bands"] = {}
    for bd in BANDS:
        print(f"\n---- [{bd} Hz]  {BAND_TAG[bd]} ----")
        print(f"{'stratum':14s} {'build':10s} {'n':>4s} {'blk':>4s} | {'envelope e (counts)':>30s}")
        for nm, lo, hi in STRATA:
            for b in LADDER:
                s = eng(R[b], b, lo, hi)
                if len(s) < 5:
                    print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |{'-- no sample --':>30s}")
                    continue
                ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=1500)
                print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                      f"{ee[0]:10.1f} [{ee[1]:8.1f},{ee[2]:8.1f}]")
                OUT["bands"].setdefault(bd, {}).setdefault(nm, {})[b] = dict(
                    n=len(s), blk=nunits(s, "blk"), e=list(ee))

    # =============================================================== B4 RATIOS ====================
    S.hdr("B4  CROSS-BUILD RATIOS, cell-stratified on (speed x effort x |rate|) cells occupied by\n"
          "    BOTH routes, episode-resampled.  Every ratio carries its own null verdict, its\n"
          "    leave-one-CELL-out range, and the NEGATIVE CONTROL beside it.")
    OUT["ratios"] = {}
    for bd in BANDS:
        flag = "  🛑 DO NOT SCORE (exposure)" if bd in DO_NOT_SCORE else ""
        print(f"\n---- {bd} Hz -- {BAND_TAG[bd]}{flag} ----")
        print(f"{'pair':20s} {'ratio':>8s} {'95% CI':>20s} {'cells':>6s} {'LOO range':>18s}"
              f"   verdict-vs-null")
        for A, B in PAIRS:
            res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_" + bd, RNG, nboot=1500,
                                  min_ep=2, min_win=4)
            nlA, nlB = OUT["null"][bd][A], OUT["null"][bd][B]
            lo, hi = min(nlA[1], nlB[1]), max(nlA[2], nlB[2])
            out = "OUTSIDE null" if (res[0] < lo or res[0] > hi) else "inside null "
            ci = "CI excl 1" if (np.isfinite(res[1]) and (res[1] > 1 or res[2] < 1)) else "CI incl 1"
            L = loo(res[6])
            ls = f"[{L[1]:6.3f},{L[2]:6.3f}]" if L else "        n/a"
            print(f"{A.split('/')[0]+'/'+B.split('/')[0]:20s} {res[0]:8.3f} "
                  f"[{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d} {ls:>18s}   "
                  f"{out}; {ci}  null[{lo:.2f},{hi:.2f}]")
            OUT["ratios"].setdefault(bd, {})[f"{A}|{B}"] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3], null=[lo, hi],
                outside=bool(res[0] < lo or res[0] > hi),
                loo=[L[1], L[2]] if L else None,
                per_cell=[[list(t[0]), t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8]]
                          for t in res[6]])

    S.hdr("B4b PER-CELL TABLE for the two PRIMARY pairs and the two PRIMARY bands, plus the\n"
          "    negative control.  cell = (eng, v-bin, effort-bin, |rate|-bin).")
    for bd in ("6-9", "18-22", NEGCTRL):
        for A, B in PAIRS[:2]:
            res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_" + bd, RNG, nboot=0,
                                  min_ep=2, min_win=4)
            print(f"\n  {bd} Hz   {A} / {B}   pooled {res[0]:.3f}   cells {res[3]}")
            print(f"    {'cell':>18s} {'nA':>5s} {'nB':>5s} {'epA':>4s} {'epB':>4s} "
                  f"{'eA':>9s} {'eB':>9s} {'ratio':>8s} {'w':>6s}")
            for c, na, nb, nea, neb, sa, sb, rr, w in res[6]:
                print(f"    {str(tuple(c)):>18s} {na:5d} {nb:5d} {nea:4d} {neb:4d} "
                      f"{sa:9.1f} {sb:9.1f} {rr:8.3f} {w:6.2f}")
            nabove = sum(1 for t in res[6] if t[7] > 1)
            print(f"    -> {nabove}/{len(res[6])} cells above 1")

    S.hdr("B5  CREEP-ONLY RATIOS (<10 km/h, engaged) -- the stratum both scored symptoms live in.")
    OUT["creep_ratio"] = {}
    for bd in BANDS:
        if bd in DO_NOT_SCORE:
            continue
        print(f"\n---- {bd} Hz, creep <10 km/h ----")
        for A, B in PAIRS:
            a, b_ = eng(R[A], A, lo0, hi0), eng(R[B], B, lo0, hi0)
            if len(a) < 8 or len(b_) < 8:
                print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  -- insufficient "
                      f"(nA={len(a)}, nB={len(b_)})")
                continue
            res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1500, min_ep=1, min_win=3)
            nA = OUT["null_creep"].get(bd, {}).get(A)
            nB = OUT["null_creep"].get(bd, {}).get(B)
            if nA and nB:
                nlo, nhi = min(nA[1], nB[1]), max(nA[2], nB[2])
                verdict = "OUTSIDE null" if (res[0] < nlo or res[0] > nhi) else "inside null "
                ns = f"null[{nlo:.2f},{nhi:.2f}]"
            else:
                verdict, ns = "null n/a    ", ""
            L = loo(res[6])
            ls = f"LOO[{L[1]:.3f},{L[2]:.3f}]" if L else ""
            print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  {res[0]:7.3f} "
                  f"[{res[1]:7.3f},{res[2]:7.3f}]  cells={res[3]:2d}  {verdict} {ns} {ls}")
            OUT["creep_ratio"].setdefault(bd, {})[f"{A}|{B}"] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3],
                loo=[L[1], L[2]] if L else None)

    S.hdr("B5b ABSOLUTE creep-stratum medians (counts).")
    print(f"{'build':10s} {'n':>4s} {'blk':>4s} | " + " ".join(f"{bd:>22s}" for bd in
                                                               ("6-9", "18-22", "40-49")))
    for b in LADDER:
        s = eng(R[b], b, lo0, hi0)
        if not s:
            print(f"{b:10s}    0    0 |  -- no creep sample --")
            continue
        cells = []
        for bd in ("6-9", "18-22", "40-49"):
            ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=1500)
            cells.append(f"{ee[0]:7.1f} [{ee[1]:6.1f},{ee[2]:6.1f}]")
        print(f"{b:10s} {len(s):4d} {nunits(s,'blk'):4d} | " + " ".join(cells))

    # =============================================================== B6 DUTY ======================
    S.hdr("B6  DUTY -- fraction of ENGAGED CREEP windows above a stated 18-22 Hz amplitude.")
    OUT["duty"] = {}
    for thr in (200.0, 400.0, 600.0):
        print(f"\n  creep <10 km/h, e_18-22 > {thr:.0f} counts (p-p >= {2*thr:.0f})")
        for b in LADDER:
            s = eng(R[b], b, lo0, hi0)
            if len(s) < 5:
                print(f"    {b:10s}  -- {len(s)} windows --")
                continue
            f = M.frac_ci(s, "e_18-22", thr, RNG, nboot=2000)
            print(f"    {b:10s} {100 * f[0]:6.1f}% [{100 * f[1]:5.1f}, {100 * f[2]:5.1f}]  "
                  f"of {f[3]} windows ({f[3] * 1.28:.0f} s)")
            OUT["duty"].setdefault(f"{thr:.0f}", {})[b] = list(f)

    # =============================================================== B7 VALIDITY ==================
    S.hdr("B7  VALIDITY.  (a) 1-4 Hz driver-input matching -- must NOT differ once cells are\n"
          "    matched.  (b) EPKEY sensitivity with the conservative whole-run unit.")
    for A, B in PAIRS[:4]:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_1-4", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"  1-4 Hz  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  {res[0]:6.3f} "
              f"[{res[1]:6.3f}, {res[2]:6.3f}]  cells={res[3]}")
        OUT.setdefault("validity", {})[f"1-4|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "ep"
    print()
    for bd in ("6-9", "18-22", "40-49", NEGCTRL):
        for A, B in PAIRS[:2]:
            res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_" + bd, RNG, nboot=1000,
                                  min_ep=2, min_win=4)
            print(f"  ep-key {bd:6s} {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  {res[0]:6.3f} "
                  f"[{res[1]:6.3f}, {res[2]:6.3f}]  cells={res[3]}  runs {res[4]}/{res[5]}")
            OUT.setdefault("validity", {})[f"ep|{bd}|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "blk"

    S.hdr("B7c MANUAL (DISENGAGED) CONTROL -- every symptom in this kit is LKAS-engaged-only, so\n"
          "    the manual arm of the SAME route is the within-drive isolator.")
    OUT["eng_vs_man"] = {}
    for b in LADDER:
        e, m_ = eng(R[b], b), man(R[b], b)
        for r in e + m_:                     # 🛑 cell[0] is the engagement flag -- drop it, or an
            r["cell"] = tuple(r["cell"])[1:]  #    engaged and a manual window never share a cell.
        if len(m_) < 10:
            print(f"  {b:10s}  -- only {len(m_)} manual windows --")
            continue
        row = f"  {b:10s} nE={len(e):4d} nM={len(m_):4d} | "
        for bd in ("6-9", "18-22", "40-49", NEGCTRL):
            res = G.boot_cellwise(e, m_, "e_" + bd, RNG, nboot=1000, min_ep=1, min_win=3)
            row += f"{bd}: {res[0]:6.2f} [{res[1]:5.2f},{res[2]:5.2f}]  "
            OUT["eng_vs_man"].setdefault(b, {})[bd] = [res[0], res[1], res[2], res[3]]
        print(row)

    def _san(o):
        if isinstance(o, dict):
            return {str(k): _san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_san(x) for x in o]
        if isinstance(o, (np.floating, np.integer)):
            return float(o)
        return o
    (CACHE6E / "score_v85_bands.json").write_text(json.dumps(_san(OUT), indent=1))
    print(f"\nwrote {CACHE6E / 'score_v85_bands.json'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "records":
        build_records(rebuild=True)
    else:
        analyze()
