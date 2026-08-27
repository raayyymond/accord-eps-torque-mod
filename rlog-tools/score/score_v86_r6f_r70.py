#!/usr/bin/env python3
"""SCORE THE V86 (route `6f`) AND V86B (route `70`) FLIGHTS -- creep-only, parking-lot routes.

🛑 THE INSTRUMENT IS THE CORPUS'S, NOT A NEW ONE.  Every band envelope, prominence, episode
bootstrap, split-half null and cell-stratified ratio below is `_grind2_lib`'s, reached through
`score_v85_r6e_bands` -> `score_v84_r6d` -> `compare_v75_v76_v80_grind` + `compare_r67_v81_grind`.
The reused functions, by name:
    _grind2_lib.wrecs / win_env / boot_cellwise / split_half_null / boot_median_ci / episodes
    score_v84_r6d.augment3 · compare_v75_v76_v80_grind.augment2 / frac_ci · _r47_lib.augment
    r67_v81_t2t3.gather / ratio_boot / split_half        (the impedance estimator, part C)
NOTHING numeric is redefined.  This file adds TWO routes to the build table.

🛑 THE OTHER BUILDS' WINDOW RECORDS ARE LOADED, NOT RECOMPUTED, from
`_scratch/cache/r6e/records_v85_score.pkl` -- read-only, never written here.  That guarantees the V67 /
V68 / V81 / V84 / V85 numbers are bit-identical to the ones already reported.

🛑 EXPOSURE CEILING ON BOTH NEW ROUTES.  0.0 s above 50 km/h, engaged AND manual, on `6f` and
`70` (v_max 5.38 / 5.97 m/s).  Therefore:
    * NO highway verdict.
    * NO grind-#1-at-speed verdict.
    * 26-31 Hz is UNSCOREABLE -- it was characterised above 80 km/h.  It is computed and printed
      so the number exists, and labelled UNSCOREABLE FOR EXPOSURE everywhere it appears.

🛑 TERMINOLOGY.  "grind #1", "grind #2", "the ring", "S1..S4" are KIT JARGON FOR FREQUENCY BANDS.
They are not symptoms the operator named.  Every heading carries HIS words -- grinding, vibrating,
micro-ratcheting, ratcheting, extra dampening -- and the band is cited only as the instrument.
A BAND MOVING IS NOT A SYMPTOM BEING FIXED.

Usage:
    python score/score_v86_r6f_r70.py records    # build V86 + V86B window records (slow)
    python score/score_v86_r6f_r70.py analyze    # A0-A7  the band scoring
    python score/score_v86_r6f_r70.py grind2     # B  the 40-49 Hz creep contradiction
    python score/score_v86_r6f_r70.py imped      # C  V86B's damping claim
    python score/score_v86_r6f_r70.py matched    # A4b the matched-theta_ddot engaged/manual contrast
    python score/score_v86_r6f_r70.py all
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

import score_v85_r6e_bands as S85  # noqa: E402  -- owns V85's registration + the read-only pickle
import score_v84_r6d as S  # noqa: E402
import compare_v75_v76_v80_grind as M  # noqa: E402
import _grind2_lib as G  # noqa: E402
import _r47_lib as R47  # noqa: E402

CACHE6F = ROOT / "_scratch/cache/r6f"
CACHE70 = ROOT / "_scratch/cache/r70"
MYPKL = CACHE6F / "records_v86_score.pkl"
CIRC = S.CIRC                                   # 2.0805 m -- wheel order n = n*v/CIRC Hz

# ---- the two new routes.  `parked` = segments with ZERO engaged seconds (route 68's convention,
# ---- used unchanged for 6d seg11 / 6e seg7).  6f: none.  70: seg 3 (eng_sec 0.0).
NEW = {
    "V86/r6f":  dict(cache=CACHE6F, pfx="r6fs", segs=list(range(4)), parked=[],  kd=9.86),
    "V86B/r70": dict(cache=CACHE70, pfx="r70s", segs=list(range(4)), parked=[3], kd=9.87),
}
LADDER = ["V67/r47", "V68/r4e", "V81/r67", "V83a/r68", "V84/r6d", "V85/r6e",
          "V86/r6f", "V86B/r70"]
LOADED = ["V76/r65", "V80/r66", "V67/r47", "V68/r4e", "V81/r67", "V83a/r68", "V84/r6d", "V85/r6e"]

# 🛑 ORDER MATTERS: the two PRIMARY, single-variable-against-V85 pairs first.
PAIRS = [("V86/r6f", "V85/r6e"),        # A1: 0xC40D4 alone
         ("V86B/r70", "V85/r6e"),       # A2': FactorC m26/m27 Y[0] alone
         ("V86B/r70", "V86/r6f"),       # A2 : TWO cells at once -- see A0
         ("V86/r6f", "V84/r6d"),
         ("V86B/r70", "V84/r6d"),
         ("V86/r6f", "V81/r67"),
         ("V86B/r70", "V81/r67"),
         ("V86/r6f", "V67/r47"),
         ("V86/r6f", "V68/r4e"),
         ("V86B/r70", "V67/r47"),
         ("V86B/r70", "V68/r4e")]
PRIMARY = PAIRS[:3]

BANDS = ["6-9", "18-22", "40-49", "32-38", "26-31", "1-4", "30-49"]
NEGCTRL = "32-38"
UNSCOREABLE = {"26-31"}          # characterised >80 km/h; these routes have 0.0 s there
BAND_TAG = {
    "6-9":   "operator's RATCHETING / MICRO-RATCHETING band (kit: 'the ratchet')",
    "18-22": "operator's GRINDING band (kit: 'grind #1')",
    "40-49": "operator's second GRINDING complaint (kit: 'grind #2')",
    "32-38": "🛑 PRE-DECLARED NEGATIVE CONTROL",
    "26-31": "🛑 UNSCOREABLE FOR EXPOSURE -- 0.0 s above 50 km/h on BOTH new routes",
    "1-4":   "VALIDITY CONTROL -- driver input; must NOT differ once cells are matched",
    "30-49": "HF floor (context)",
}
# The brief's usable speed bins.  Both routes are parking-lot: nothing above 5.97 m/s exists.
FINE = [("0.5-1.5 m/s", 0.5, 1.5), ("1.5-2.78 m/s", 1.5, 2.78), ("2.78-5.0 m/s", 2.78, 5.0)]
STRATA = M.STRATA
RNG = np.random.default_rng(86_6015)
OUT = {}


def register():
    S85.register()                                  # V76..V85 (which calls S.register())
    for b, cfg in NEW.items():
        G.BUILDS[b] = dict(cache=cfg["cache"], pfx=cfg["pfx"], segs=cfg["segs"], kd=cfg["kd"])
        S.PARKED[b] = cfg["parked"]
        S85.S.PARKED[b] = cfg["parked"]


def build_records(rebuild=False):
    """V86 + V86B computed here; every other build LOADED from V85's pickle, READ-ONLY."""
    register()
    if MYPKL.exists() and not rebuild:
        with open(MYPKL, "rb") as fh:
            st = pickle.load(fh)
        if st.get("__bands__") == sorted(M.BANDS_EXT) and all(b in st for b in LADDER):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    with open(S85.MYPKL, "rb") as fh:               # 🛑 READ-ONLY.  Never written by this file.
        base = pickle.load(fh)
    assert base.get("__bands__") == sorted(M.BANDS_EXT), \
        "🛑 V85's pickle was built with a different band set -- do not mix"
    st = {"__bands__": sorted(M.BANDS_EXT)}
    for b in LOADED:
        if b in base:
            st[b] = base[b]
            print(f"  {b}: {len(st[b])} windows (loaded from V85's pickle)", flush=True)
    for b in NEW:
        print(f"  wrecs {b} ...", flush=True)
        st[b] = S.augment3(M.augment2(R47.augment(G.wrecs(b))))
        print(f"    {len(st[b])} windows", flush=True)
    CACHE6F.mkdir(exist_ok=True)
    with open(MYPKL, "wb") as fh:
        pickle.dump(st, fh)
    return {k: v for k, v in st.items() if not k.startswith("__")}


def eng(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 1 and r["seg"] not in S.PARKED.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def man(rs, build, lo=None, hi=None, fwd_only=False):
    """Manual arm.  🛑 `fwd_only` drops REVERSE (cs_gear == 4).  Both new routes spend ~30 s in R,
    100% manual, essentially all below 2 m/s -- and `cs_v` is a MAGNITUDE, so reverse creep is
    invisible in speed alone and would silently pollute the manual arm below 2 m/s."""
    out = [r for r in rs if r["eng"] == 0 and r["seg"] not in S.PARKED.get(build, [])]
    if fwd_only:
        out = [r for r in out if not (np.isfinite(r.get("gear", np.nan)) and r["gear"] == 4)]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def nunits(rs, key=None):
    return len({r[key or G.EPKEY] for r in rs})


def order_clean(rs, band, circ=CIRC):
    """Drop windows whose wheel order 1/2/3 line lands INSIDE `band`.  Constraint 7: the kit
    retracted a 1.625 figure that was pure wheel-order artefact, so this runs even where the
    census says contamination is nil."""
    lo, hi = M.BANDS_EXT[band]
    out = []
    for r in rs:
        w = r["v"] / circ
        if any(lo <= n * w <= hi for n in (1, 2, 3)):
            continue
        out.append(r)
    return out


def loo(tab):
    """Leave-one-CELL-out on the pooled weighted log-ratio -- `score_v85_r6e_bands.loo`, verbatim
    in behaviour: answers 'is the pooled figure carried by ONE cell?', which a CI cannot."""
    return S85.loo(tab)


def verdict(ratio, lo, hi, nlo, nhi):
    """MOVED / NULL, on the corpus's own two-part rule: OUTSIDE the wider of the two builds' own
    split-half nulls AND a bootstrap CI excluding 1."""
    if not np.isfinite(ratio):
        return "NO SAMPLE"
    out = np.isfinite(nlo) and (ratio < nlo or ratio > nhi)
    ci = np.isfinite(lo) and (lo > 1 or hi < 1)
    if out and ci:
        return "MOVED"
    if out or ci:
        return "WEAK (one of two)"
    return "NULL"


def _san(o):
    if isinstance(o, dict):
        return {str(k): _san(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_san(x) for x in o]
    if isinstance(o, (np.floating, np.integer)):
        f = float(o)
        return None if not np.isfinite(f) else f
    if isinstance(o, float) and not np.isfinite(o):
        return None
    return o


def dump():
    CACHE6F.mkdir(exist_ok=True)
    CACHE70.mkdir(exist_ok=True)
    for p in (CACHE6F / "score_v86_bands.json", CACHE70 / "score_v86b_bands.json"):
        p.write_text(json.dumps(_san(OUT), indent=1))
        print(f"wrote {p}")


# =================================================================================================
#  A0  IDENTITY AND THE IMAGE DIFF -- read from the BUILT IMAGES, not from build scripts.
# =================================================================================================
FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMG = {"V85": "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin",
       "V86": "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin",
       "V86B": "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"}


def a0_identity():
    S.hdr("A0  ROUTE IDENTITY (parameter-free, from the on-bus build fingerprint) and the IMAGE\n"
          "    DIFF read from the BUILT IMAGES.  🛑 STATE.md's claim that V86 and V86B are\n"
          "    'single-variable against each other' is checked here, byte by byte.")
    OUT["identity"] = {}
    for rt, cache in (("6f", CACHE6F), ("70", CACHE70)):
        d = json.loads((cache / f"r{rt}_identity.json").read_text())
        print(f"    route {rt}: verdict = {d['verdict']}   "
              f"v86_violations={d['v86_violations']}  v86b_violations={d['v86b_violations']}  "
              f"outside_both={d['outside_both_alphabets']}")
        OUT["identity"][rt] = dict(verdict=d["verdict"], v86_viol=d["v86_violations"],
                                   v86b_viol=d["v86b_violations"])
    imgs = {}
    for k, nm in IMG.items():
        p = FW / nm
        if p.exists():
            imgs[k] = p.read_bytes()
    if len(imgs) == 3:
        def runs(idx):
            out = []
            for i in idx:
                if out and i == out[-1][1] + 1:
                    out[-1][1] = i
                else:
                    out.append([i, i])
            return out
        OUT["image_diff"] = {}
        for A, B in (("V86", "V86B"), ("V85", "V86"), ("V85", "V86B")):
            X, Y = imgs[A], imgs[B]
            idx = [i for i in range(len(X)) if X[i] != Y[i]]
            print(f"\n    {A} vs {B}: {len(idx)} differing bytes")
            rr = []
            for a, b in runs(idx):
                print(f"      0x{a:05X}-0x{b:05X}   {A}={X[a:b+1].hex()}   {B}={Y[a:b+1].hex()}")
                rr.append([f"0x{a:05X}", f"0x{b:05X}", X[a:b + 1].hex(), Y[a:b + 1].hex()])
            OUT["image_diff"][f"{A}|{B}"] = dict(nbytes=len(idx), runs=rr)
        print("\n    🛑 READ THE 16 BYTES.  V86 = V85 + `0xC40D4` 573->286.  V86B = V85 + FactorC\n"
              "    m26/m27 `Y[0]` 0 -> 908/875, with `0xC40D4` LEFT AT 573.  So V86 vs V86B is a\n"
              "    TWO-CELL contrast, not one: 0xC40D4 (286 vs 573) AND FactorC Y[0] (0 vs 908/875),\n"
              "    plus two probe-cave bytes (0xC4B3E/0xC4B4E, 0x44<->0x42) and the two block CRCs.\n"
              "    The SINGLE-VARIABLE pairs are V86-vs-V85 and V86B-vs-V85.")
    else:
        print("    (images not all present -- image diff skipped)")


# =================================================================================================
#  A1  EXPOSURE, SPEED CENSUS, WHEEL ORDER
# =================================================================================================
def a1_exposure(R):
    S.hdr("A1  EXPOSURE CENSUS -- engaged only, parked segments dropped.\n"
          "    🛑 BOTH NEW ROUTES ARE PARKING-LOT ONLY: 0.0 s above 50 km/h, engaged AND manual.")
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
            st[nm] = dict(n=len(s), blk=nunits(s, "blk"), sec=len(s) * 1.28)
        print("".join(row))
        OUT["exposure"][b] = dict(n=len(e), sec=len(e) * 1.28, blk=nunits(e, "blk"),
                                  run=nunits(e, "ep"), strata=st)

    print("\n  ENGAGED window counts in the brief's usable fine bins (the ONLY bins these routes"
          " can speak to):")
    print(f"{'build':10s} " + " ".join(f"{nm:>16s}" for nm, _, _ in FINE) + "     manual (FWD-only)")
    OUT["fine_exposure"] = {}
    for b in LADDER:
        cells, mc = [], []
        for nm, lo, hi in FINE:
            s = eng(R[b], b, lo, hi)
            mm = man(R[b], b, lo, hi, fwd_only=True)
            cells.append(f"{len(s):5d}w/{nunits(s,'blk'):2d}b")
            mc.append(f"{len(mm):4d}w")
            OUT["fine_exposure"].setdefault(b, {})[nm] = dict(
                eng=len(s), eng_blk=nunits(s, "blk"), man_fwd=len(mm),
                man_all=len(man(R[b], b, lo, hi)))
        print(f"{b:10s} " + " ".join(f"{c:>16s}" for c in cells) + "   " + " ".join(mc))

    print("\n  REVERSE-GEAR CENSUS on the manual arm (cs_gear == 4).  🛑 `cs_v` is a magnitude.")
    OUT["reverse"] = {}
    for b in ("V86/r6f", "V86B/r70", "V85/r6e", "V84/r6d"):
        mm = man(R[b], b)
        rev = [r for r in mm if np.isfinite(r.get("gear", np.nan)) and r["gear"] == 4]
        lo2 = [r for r in mm if r["v"] < 2.0]
        rev2 = [r for r in rev if r["v"] < 2.0]
        print(f"    {b:10s} manual {len(mm):4d}w   reverse {len(rev):4d}w ({len(rev)*1.28:5.1f} s)"
              f"   below 2 m/s: {len(rev2)}/{len(lo2)} = "
              f"{100*len(rev2)/max(len(lo2),1):5.1f}% of the manual creep arm")
        OUT["reverse"][b] = dict(man=len(mm), rev=len(rev), man_lt2=len(lo2), rev_lt2=len(rev2))

    S.hdr("A1b PER-WINDOW SPEED CENSUS -- 🛑 MANDATORY before any averaged comparison.\n"
          "    Wheel order 1 = v / 2.0805 Hz and MOVES WITH SPEED.")
    VB = [(0.0, 0.5), (0.5, 1.5), (1.5, 2.78), (2.78, 5.0), (5.0, 8.0), (8.0, 11.1),
          (11.1, 16.0), (16.0, 22.2), (22.2, 40.0)]
    print(f"{'build':10s} " + " ".join(f"{lo:.1f}-{hi:.1f}".rjust(9) for lo, hi in VB))
    OUT["speed_census"] = {}
    for b in LADDER:
        v = G.col(eng(R[b], b), "v")
        cnt = [int(((v >= lo) & (v < hi)).sum()) for lo, hi in VB]
        print(f"{b:10s} " + " ".join(f"{100 * c / max(len(v),1):8.1f}%" for c in cnt))
        OUT["speed_census"][b] = dict(frac=[c / max(len(v), 1) for c in cnt], n=len(v),
                                      counts=cnt)
    print("\n  wheel-order contamination: % of engaged windows whose order-1 / order-2 line lands"
          " INSIDE each band")
    print(f"{'build':10s} {'ord1 med':>9s} | " + " ".join(f"{bd:>12s}" for bd in BANDS[:5]))
    OUT["wheel_order"] = {}
    for b in LADDER:
        v = G.col(eng(R[b], b), "v")
        o1, o2 = v / CIRC, 2 * v / CIRC
        row = f"{b:10s} {np.median(o1):9.2f} | "
        wo = {}
        for bd in BANDS[:5]:
            lo, hi = M.BANDS_EXT[bd]
            f1, f2 = float(np.mean((o1 >= lo) & (o1 <= hi))), float(np.mean((o2 >= lo) & (o2 <= hi)))
            row += f" {100*f1:4.1f}/{100*f2:4.1f}%"
            wo[bd] = [f1, f2]
        print(row)
        OUT["wheel_order"][b] = dict(ord1_med=float(np.median(o1)), inband=wo)


# =================================================================================================
#  A2  THE RESAMPLING UNIT -- justified from the AUTOCORRELATION, not asserted.
# =================================================================================================
def a2_unit(R):
    S.hdr("A2  THE RESAMPLING UNIT.  🛑 CONSTRAINT 4: `6f` is ONE continuous 141.2 s engaged\n"
          "    episode ⇒ the whole-run unit `ep` has n = 1..4 and CANNOT carry a CI.  The kit's\n"
          "    standing scoring unit is the ~10.24 s BLOCK (`blk` = 8 windows at hop 128, nested\n"
          "    inside one engagement run) -- IDENTICAL to what V84 and V85 were scored with.\n"
          "    Its legitimacy rests on the band envelope decorrelating well inside 10.24 s.")
    print(f"\n  {'build':10s} {'ep (runs)':>10s} {'blk':>6s} | "
          "lag-1 (1.28 s) / lag-4 (5.1 s) / lag-8 (10.2 s) autocorrelation of e_18-22, e_6-9")
    OUT["unit"] = {}
    for b in LADDER:
        e = sorted(eng(R[b], b), key=lambda r: (r["seg"], r["t0"]))
        info = []
        for bd in ("18-22", "6-9"):
            acs = {1: [], 4: [], 8: []}
            byrun = {}
            for r in e:
                byrun.setdefault(r["ep"], []).append(r)
            for rs in byrun.values():
                x = np.log(np.maximum(G.col(rs, "e_" + bd), 1e-9))
                if len(x) < 12:
                    continue
                x = x - x.mean()
                den = float(np.dot(x, x))
                for L in acs:
                    if len(x) > L + 4 and den > 0:
                        acs[L].append(float(np.dot(x[:-L], x[L:]) / den) * len(x) / (len(x) - L))
            info.append("  " + bd + ": " + "/".join(
                f"{np.median(v):5.2f}" if v else "  n/a" for v in (acs[1], acs[4], acs[8])))
        print(f"  {b:10s} {nunits(e,'ep'):10d} {nunits(e,'blk'):6d} |" + "".join(info))
        OUT["unit"][b] = dict(ep=nunits(e, "ep"), blk=nunits(e, "blk"))
    print("\n  ⇒ The autocorrelation of the log band envelope is already near zero at lag 4-8\n"
          "    windows (5-10 s) on every build.  A ~10.24 s block is therefore LONGER than the\n"
          "    decorrelation length, which is the condition a block bootstrap needs.  🛑 It is\n"
          "    still NOT a whole-episode unit: on `6f` the 14 blocks all sit inside ONE engagement,\n"
          "    so anything that varies on the timescale of a whole drive (the parking lot, the\n"
          "    driver's mood, tyre temperature) is NOT resampled and its uncertainty is NOT in the\n"
          "    CI.  Every `6f` CI below is conditional on that.")


# =================================================================================================
#  A3  THE SPLIT-HALF NULL -- COMPUTED AND PRINTED BEFORE ANY RATIO.
# =================================================================================================
def a3_nulls(R):
    S.hdr("A3  SPLIT-HALF NULL -- 🛑 COMPUTED AND PRINTED BEFORE ANY CROSS-ROUTE RATIO.\n"
          "    Each route halved against ITSELF with the IDENTICAL estimator, 400 halvings.\n"
          "    A ratio inside the wider of the two builds' nulls is NOT a result.\n"
          "    The kit's recorded null is [0.63, 1.50] ⇒ a ratio must clear ~1.5 to mean anything.")
    OUT["null"] = {}
    print(f"{'band':8s} {'build':10s} {'null median':>12s} {'null 95% interval':>26s}")
    for bd in BANDS:
        for b in LADDER:
            n = G.split_half_null(eng(R[b], b), "e_" + bd, RNG, nrep=400, min_ep=2, min_win=4)
            print(f"{bd:8s} {b:10s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]")
            OUT["null"].setdefault(bd, {})[b] = list(n)
        print()

    S.hdr("A3b CREEP-ONLY SPLIT-HALF NULL (<10 km/h = <2.78 m/s, engaged).  🛑 THIS is the null\n"
          "    that governs every verdict below, because BOTH new routes are creep-only and every\n"
          "    symptom the operator scored on them is a creep symptom.")
    OUT["null_creep"] = {}
    nm0, lo0, hi0 = STRATA[0]
    for bd in BANDS:
        for b in LADDER:
            s = eng(R[b], b, lo0, hi0)
            if len(s) < 8:
                print(f"{bd:8s} {b:10s}  -- only {len(s)} creep windows, null undefined --")
                OUT["null_creep"].setdefault(bd, {})[b] = None
                continue
            n = G.split_half_null(s, "e_" + bd, RNG, nrep=400, min_ep=1, min_win=3)
            print(f"{bd:8s} {b:10s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]   "
                  f"({len(s)}w / {nunits(s,'blk')}blk)")
            OUT["null_creep"].setdefault(bd, {})[b] = list(n)
        print()


# =================================================================================================
#  A4  ROAD ROUGHNESS + THE ABSOLUTE BAND TABLE + THE RATIOS
# =================================================================================================
def a4_roughness(R):
    S.hdr("A4  ROAD-ROUGHNESS CONTROL -- chassis vertical IMU 20-49 Hz envelope, same cells.\n"
          "    🛑 On V85-vs-V84 the IMU said V85's road was 1.2x SMOOTHER, which moved AGAINST\n"
          "    the result.  A band ratio is only interpretable with this beside it.")
    for b in LADDER:
        S._add_imu2049(R[b])
    OUT["roughness"] = {}
    print(f"{'pair':24s} {'imu2049 A/B':>12s} {'95% CI':>20s} {'cells':>6s}")
    for A, B in PAIRS:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "imu2049", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"{A.split('/')[0]+' / '+B.split('/')[0]:24s} {res[0]:12.3f} "
              f"[{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d}")
        OUT["roughness"][f"{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    print("\n  absolute median imu2049 (m/s^2 envelope), engaged:")
    for b in LADDER:
        e = eng(R[b], b)
        v = G.col(e, "imu2049")
        print(f"    {b:10s} {np.nanmedian(v):8.4f}   (n finite {int(np.isfinite(v).sum())})")
        OUT.setdefault("roughness_abs", {})[b] = float(np.nanmedian(v))


def a5_bands(R):
    S.hdr("A5  ABSOLUTE BAND LEVELS, engaged, in the brief's usable fine speed bins.\n"
          "    e_band = p99 analytic band-envelope AMPLITUDE of the torsion bar, counts (p-p = 2x).\n"
          "    median [2.5%, 97.5%], ~10.24 s blocks resampled.")
    OUT["bands"] = {}
    for bd in BANDS[:5]:
        flag = "   🛑 UNSCOREABLE FOR EXPOSURE" if bd in UNSCOREABLE else ""
        print(f"\n---- [{bd} Hz]  {BAND_TAG[bd]}{flag} ----")
        print(f"{'bin':14s} {'build':10s} {'n':>4s} {'blk':>4s} | {'envelope e (counts)':>30s}")
        for nm, lo, hi in FINE:
            for b in LADDER:
                s = eng(R[b], b, lo, hi)
                if len(s) < 5:
                    print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                          f"{'-- no sample --':>30s}")
                    continue
                ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=1500)
                print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                      f"{ee[0]:10.1f} [{ee[1]:8.1f},{ee[2]:8.1f}]")
                OUT["bands"].setdefault(bd, {}).setdefault(nm, {})[b] = dict(
                    n=len(s), blk=nunits(s, "blk"), e=list(ee))
            print()


def _ratio_row(a, b_, bd, nulls, tag, clean=False):
    if clean:
        a, b_ = order_clean(a, bd), order_clean(b_, bd)
    if len(a) < 6 or len(b_) < 6:
        return None
    res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1500, min_ep=1, min_win=3)
    nlo, nhi = nulls
    L = loo(res[6])
    return dict(ratio=res[0], lo=res[1], hi=res[2], cells=res[3], nA=len(a), nB=len(b_),
                null=[nlo, nhi], loo=[L[1], L[2]] if L else None,
                verdict=verdict(res[0], res[1], res[2], nlo, nhi), tag=tag)


def _nullpair(bd, A, B, key="null_creep"):
    nA, nB = OUT[key].get(bd, {}).get(A), OUT[key].get(bd, {}).get(B)
    if nA and nB and np.isfinite(nA[1]) and np.isfinite(nB[1]):
        return min(nA[1], nB[1]), max(nA[2], nB[2])
    if nA and np.isfinite(nA[1]):
        return nA[1], nA[2]
    if nB and np.isfinite(nB[1]):
        return nB[1], nB[2]
    return np.nan, np.nan


def a6_ratios(R):
    nm0, lo0, hi0 = STRATA[0]
    S.hdr("A6  CROSS-ROUTE RATIOS, ENGAGED CREEP (<2.78 m/s) -- cell-stratified on\n"
          "    (speed x effort x |rate|) cells occupied by BOTH routes, ~10.24 s blocks resampled.\n"
          "    Every ratio carries its own null verdict, its leave-one-CELL-out range, and the\n"
          "    NEGATIVE CONTROL is printed as its own band below.\n"
          "    🛑 NONE of these pairs is single-variable at the ROUTE level: engagement duty, the\n"
          "    engaged/manual creep balance and the driver's own parking-lot manoeuvres all differ.")
    OUT["creep_ratio"] = {}
    for bd in BANDS:
        flag = "   🛑 UNSCOREABLE FOR EXPOSURE" if bd in UNSCOREABLE else ""
        print(f"\n---- {bd} Hz -- {BAND_TAG[bd]}{flag} ----")
        print(f"{'pair':22s} {'ratio':>8s} {'95% CI':>20s} {'cells':>6s} {'LOO range':>18s} "
              f"{'null':>16s}  verdict")
        for A, B in PAIRS:
            a, b_ = eng(R[A], A, lo0, hi0), eng(R[B], B, lo0, hi0)
            row = _ratio_row(a, b_, bd, _nullpair(bd, A, B), "raw")
            if row is None:
                print(f"{A.split('/')[0]+' / '+B.split('/')[0]:22s}  -- insufficient "
                      f"(nA={len(a)}, nB={len(b_)}) --")
                continue
            ls = f"[{row['loo'][0]:6.3f},{row['loo'][1]:6.3f}]" if row["loo"] else "        n/a"
            print(f"{A.split('/')[0]+' / '+B.split('/')[0]:22s} {row['ratio']:8.3f} "
                  f"[{row['lo']:8.3f},{row['hi']:8.3f}] {row['cells']:6d} {ls:>18s} "
                  f"[{row['null'][0]:6.2f},{row['null'][1]:6.2f}]  {row['verdict']}")
            OUT["creep_ratio"].setdefault(bd, {})[f"{A}|{B}"] = row

    S.hdr("A6b THE SAME RATIOS, WHEEL-ORDER CLEANED -- every window whose order-1/2/3 line lands\n"
          "    inside the band is DROPPED.  Constraint 7: the kit retracted a 1.625 figure that was\n"
          "    pure wheel-order artefact, so this runs even though the census says contamination is\n"
          "    nil on these routes (engaged order-1 median 1.2-1.3 Hz).")
    OUT["creep_ratio_clean"] = {}
    for bd in ("6-9", "18-22", "40-49", NEGCTRL):
        print(f"\n---- {bd} Hz, order-cleaned ----")
        for A, B in PRIMARY + [("V86/r6f", "V84/r6d"), ("V86/r6f", "V81/r67")]:
            a, b_ = eng(R[A], A, lo0, hi0), eng(R[B], B, lo0, hi0)
            row = _ratio_row(a, b_, bd, _nullpair(bd, A, B), "clean", clean=True)
            if row is None:
                print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  -- insufficient after clean --")
                continue
            raw = OUT["creep_ratio"].get(bd, {}).get(f"{A}|{B}", {}).get("ratio", np.nan)
            print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} raw {raw:7.3f} -> cleaned "
                  f"{row['ratio']:7.3f} [{row['lo']:6.3f},{row['hi']:6.3f}]  "
                  f"kept {row['nA']}/{row['nB']} w  {row['verdict']}")
            OUT["creep_ratio_clean"].setdefault(bd, {})[f"{A}|{B}"] = row

    S.hdr("A6c PER-FINE-BIN RATIOS for the two PRIMARY single-variable pairs plus the two-cell\n"
          "    V86B/V86 contrast.  Speed matched EXPLICITLY, not only through the cell key.")
    OUT["fine_ratio"] = {}
    for bd in ("6-9", "18-22", "40-49", NEGCTRL):
        print(f"\n---- {bd} Hz ----")
        for A, B in PRIMARY:
            for nm, lo, hi in FINE:
                a, b_ = eng(R[A], A, lo, hi), eng(R[B], B, lo, hi)
                if len(a) < 5 or len(b_) < 5:
                    print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} {nm:14s}"
                          f"  -- insufficient (nA={len(a)}, nB={len(b_)}) --")
                    continue
                res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1200, min_ep=1, min_win=3)
                ma, mb = (float(np.nanmedian(G.col(a, "e_" + bd))),
                          float(np.nanmedian(G.col(b_, "e_" + bd))))
                nlo, nhi = _nullpair(bd, A, B)
                print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} {nm:14s} "
                      f"nA={len(a):3d} nB={len(b_):3d}  medA {ma:7.1f} medB {mb:7.1f}  "
                      f"ratio {res[0]:7.3f} [{res[1]:6.3f},{res[2]:6.3f}] c={res[3]:2d}  "
                      f"{verdict(res[0], res[1], res[2], nlo, nhi)}")
                OUT["fine_ratio"].setdefault(bd, {}).setdefault(f"{A}|{B}", {})[nm] = dict(
                    ratio=res[0], lo=res[1], hi=res[2], cells=res[3], nA=len(a), nB=len(b_),
                    medA=ma, medB=mb, verdict=verdict(res[0], res[1], res[2], nlo, nhi))


# =================================================================================================
#  A7  ENGAGED vs MANUAL WITHIN EACH ROUTE -- the strongest design these routes can carry.
# =================================================================================================
def a7_engman(R):
    S.hdr("A7  ENGAGED vs MANUAL WITHIN THE SAME ROUTE -- the within-drive isolator, and the\n"
          "    strongest design available here because it needs NO cross-route matching.\n"
          "    Cells re-keyed on (speed x effort x |rate|) WITHOUT the engagement flag, exactly as\n"
          "    `score_v84_r6d.engman` does.  ratio > 1 = MORE band energy on the bar when engaged.\n"
          "    🛑 MANUAL ARM IS FORWARD-GEAR-ONLY (cs_gear != 4) -- see A1's reverse census.")
    OUT["eng_vs_man"] = {}
    for fwd in (True, False):
        print(f"\n  ---- manual arm: {'FORWARD ONLY' if fwd else 'ALL GEARS (sensitivity)'} ----")
        for b in LADDER:
            e, m_ = eng(R[b], b), man(R[b], b, fwd_only=fwd)
            for r in e + m_:
                r["cell"] = tuple(r["cell"])[-3:]
            if len(m_) < 10:
                print(f"  {b:10s}  -- only {len(m_)} manual windows --")
                continue
            row = f"  {b:10s} nE={len(e):4d} nM={len(m_):4d} | "
            for bd in ("6-9", "18-22", "40-49", NEGCTRL):
                res = G.boot_cellwise(e, m_, "e_" + bd, RNG, nboot=1200, min_ep=1, min_win=3)
                row += f"{bd}: {res[0]:6.2f} [{res[1]:5.2f},{res[2]:6.2f}] c={res[3]:2d}  "
                if fwd:
                    OUT["eng_vs_man"].setdefault(b, {})[bd] = [res[0], res[1], res[2], res[3]]
                else:
                    OUT.setdefault("eng_vs_man_allgear", {}).setdefault(b, {})[bd] = \
                        [res[0], res[1], res[2], res[3]]
            print(row)
        # restore the engagement flag in the cell key for anything downstream
        for b in LADDER:
            for r in R[b]:
                if len(tuple(r["cell"])) == 3:
                    r["cell"] = (r["eng"],) + tuple(r["cell"])

    S.hdr("A7b THE SAME CONTRAST RESTRICTED TO CREEP (<2.78 m/s), where both new routes live and\n"
          "    where the operator scored every symptom.")
    nm0, lo0, hi0 = STRATA[0]
    OUT["eng_vs_man_creep"] = {}
    for b in LADDER:
        e, m_ = eng(R[b], b, lo0, hi0), man(R[b], b, lo0, hi0, fwd_only=True)
        for r in e + m_:
            r["cell"] = tuple(r["cell"])[-3:]
        if len(m_) < 8 or len(e) < 8:
            print(f"  {b:10s}  -- nE={len(e)} nM={len(m_)}, insufficient --")
            continue
        row = f"  {b:10s} nE={len(e):4d} nM={len(m_):4d} | "
        for bd in ("6-9", "18-22", "40-49", NEGCTRL):
            res = G.boot_cellwise(e, m_, "e_" + bd, RNG, nboot=1200, min_ep=1, min_win=3)
            row += f"{bd}: {res[0]:6.2f} [{res[1]:5.2f},{res[2]:6.2f}] c={res[3]:2d}  "
            OUT["eng_vs_man_creep"].setdefault(b, {})[bd] = [res[0], res[1], res[2], res[3]]
        print(row)
    for b in LADDER:
        for r in R[b]:
            if len(tuple(r["cell"])) == 3:
                r["cell"] = (r["eng"],) + tuple(r["cell"])


# =================================================================================================
#  A4b / `matched` -- the matched-theta_ddot engaged/manual contrast, WITHIN each new route.
# =================================================================================================
def matched():
    """`selfint_transfer.s3_matched`'s estimator (OLS of log(bar) on log(theta_ddot), the engaged
    indicator and log1p(v), episode-clustered bootstrap) run WITHIN each new route.

    🛑 This is stronger than the recorded 2.77 [2.29, 3.32]: that figure pooled the manual arm over
    SIX caches from other drives.  Here both arms come from the SAME drive, minutes apart.
    """
    import selfint_lib as SL
    S.hdr("A4b ENGAGED vs MANUAL AT MATCHED theta_ddot AND MATCHED SPEED, WITHIN ROUTE.\n"
          "    Purely inertial coupling gives exp(c) = 1.00 in every band.  exp(c) > 1 means the\n"
          "    FIRMWARE is adding to the bar at the same column acceleration and the same speed.\n"
          "    Recorded (pooled manual arm, other routes): 2.77 [2.29,3.32] @6-9, 1.66 [1.29,2.06]\n"
          "    @17-23, control 1.04 @26-31.\n"
          "    🛑 DOCUMENTED DEVIATION.  `selfint_lib.LATTICE_GAP` is 0.015 s; routes 6f and 70\n"
          "    carry 2.6% / 2.0% of frames above that (single-frame CAN drops), which at the\n"
          "    5.12 s block length leaves ZERO episodes and makes the test structurally\n"
          "    unavailable.  It is therefore run at the BAND HARNESS's own tolerance\n"
          "    (`_r31_common.runs_of` max_gap = 0.05 s).  V84/r6d is carried as a POSITIVE\n"
          "    CONTROL at BOTH tolerances so the change of tolerance can be seen not to move the\n"
          "    answer by itself.")
    for lbl, spec in (("V86/r6f", ("_scratch/cache/r6f", "r6fs", 4)),
                      ("V86B/r70", ("_scratch/cache/r70", "r70s", 4)),
                      ("V85/r6e", ("_scratch/cache/r6e", "r6es", 8))):
        SL.ROUTES[lbl] = spec
    rng = np.random.default_rng(86_9022)
    OUT["matched"] = {}
    print(f"\n    {'route':10s} {'band':7s} {'K eng':>6s} {'K man':>6s} {'v eng':>7s} {'v man':>7s}"
          f" {'b (slope)':>18s} {'exp(c) ENG/MAN':>22s}")
    CONF = [("V84/r6d n512 g.015", "V84/r6d", 512, 0.015),   # the corpus's own settings
            ("V84/r6d n256 g.050", "V84/r6d", 256, 0.050),   # POSITIVE CONTROL for the change
            ("V85/r6e n256 g.050", "V85/r6e", 256, 0.050),
            ("V86/r6f n256 g.050", "V86/r6f", 256, 0.050),
            ("V86B/r70 n256 g.050", "V86B/r70", 256, 0.050)]
    for tag, rt, nps, gap in CONF:
        SL.LATTICE_GAP = gap
        try:
            e = SL.collect(rt, SL.mask_engaged, nperseg=nps, ep_max=4 * nps)
            m = SL.collect(rt, SL.mask_manual, nperseg=nps, ep_max=4 * nps)
        except Exception as ex:
            print(f"    ({tag} skipped: {ex})")
            continue
        for bn, (lo, hi) in (("6-9", (6, 9)), ("17-23", (17, 23)), ("26-31", (26, 31)),
                             ("32-38", (32, 38))):
            def rows(recs, cond):
                out = []
                for r in recs:
                    f = r["f"]
                    sel = (f >= lo) & (f <= hi) & (f > 0)
                    om = 2 * np.pi * f[sel]
                    add = float(np.sqrt(np.sum(r["Sxx"][sel] * om ** 2)))
                    bar = float(np.sqrt(np.sum(r["Syy"][sel])))
                    if add > 0 and bar > 0:
                        out.append(dict(add=add, bar=bar, v=r["v_mean"], cond=cond))
                return out
            E, Mn = rows(e, "engaged"), rows(m, "manual")
            if min(len(E), len(Mn)) < 4:
                print(f"    {tag:20s} {bn:7s} {len(E):6d} {len(Mn):6d}   "
                      f"(insufficient -- the manual arm has no usable episodes)")
                OUT["matched"].setdefault(tag, {})[bn] = None
                continue
            allr = E + Mn

            def fit(rs):
                X = np.stack([np.ones(len(rs)), np.log([r["add"] for r in rs]),
                              np.array([r["cond"] == "engaged" for r in rs], float),
                              np.log1p([r["v"] for r in rs])], axis=1)
                y = np.log([r["bar"] for r in rs])
                return np.linalg.lstsq(X, y, rcond=None)[0]
            b0 = fit(allr)
            bs = []
            for _ in range(2000):
                pick = [allr[i] for i in rng.integers(0, len(allr), len(allr))]
                if len({r["cond"] for r in pick}) < 2:
                    continue
                try:
                    bs.append(fit(pick))
                except Exception:
                    continue
            bs = np.array(bs)
            cb = (float(np.percentile(bs[:, 1], 2.5)), float(np.percentile(bs[:, 1], 97.5)))
            cc = (float(np.exp(np.percentile(bs[:, 2], 2.5))),
                  float(np.exp(np.percentile(bs[:, 2], 97.5))))
            flag = "  🛑 K_man < 8: point estimate only" if len(Mn) < 8 else ""
            print(f"    {tag:20s} {bn:7s} {len(E):6d} {len(Mn):6d} "
                  f"{np.median([r['v'] for r in E]):7.2f} {np.median([r['v'] for r in Mn]):7.2f} "
                  f"{b0[1]:7.3f} [{cb[0]:5.2f},{cb[1]:5.2f}] "
                  f"{float(np.exp(b0[2])):8.3f} [{cc[0]:6.3f},{cc[1]:6.3f}]{flag}")
            OUT["matched"].setdefault(tag, {})[bn] = dict(
                b=float(b0[1]), ci_b=list(cb), exp_c=float(np.exp(b0[2])), ci_c=list(cc),
                K_eng=len(E), K_man=len(Mn),
                v_eng=float(np.median([r["v"] for r in E])),
                v_man=float(np.median([r["v"] for r in Mn])))
        print()
    SL.LATTICE_GAP = 0.015
    print("\n    🛑 32-38 Hz is the NEGATIVE CONTROL for this test too.  If it moves with 6-9,\n"
          "    the contrast is a broadband arm difference, not a band effect.")
    dump()


# =================================================================================================
#  B  GRIND #2 -- the operator reports it on BOTH routes.  Score 40-49 Hz at creep.
# =================================================================================================
def grind2():
    G.EPKEY = "blk"
    R = build_records()
    nm0, lo0, hi0 = STRATA[0]
    S.hdr("B1  THE OPERATOR REPORTS HIS SECOND GRINDING COMPLAINT ON BOTH NEW ROUTES.\n"
          "    Lever B (`0x3AA96`=FB + `0xC6446`=5244) is ON the car on V84/V85/V86/V86B, and its\n"
          "    recorded result on V67/V68 was 'creep grind #2 -> 0 bursts'.  This section scores\n"
          "    the 40-49 Hz band at creep on both arms and compares to V67/V68's own numbers.")
    print(f"\n  ABSOLUTE 40-49 Hz envelope, ENGAGED creep (<2.78 m/s), median [2.5%,97.5%]:")
    print(f"  {'build':10s} {'n':>4s} {'blk':>4s} {'sec':>7s} | {'e_40-49 (counts)':>28s} "
          f"| {'p90':>8s} {'max':>8s}")
    OUT["g2_abs"] = {}
    for arm, sel in (("ENGAGED", lambda b: eng(R[b], b, lo0, hi0)),
                     ("MANUAL (fwd)", lambda b: man(R[b], b, lo0, hi0, fwd_only=True))):
        print(f"\n  ---- {arm} ----")
        for b in LADDER:
            s = sel(b)
            if len(s) < 5:
                print(f"  {b:10s} {len(s):4d}  -- too few --")
                continue
            ee = G.boot_median_ci(s, "e_40-49", RNG, nboot=1500)
            v = G.col(s, "e_40-49")
            print(f"  {b:10s} {len(s):4d} {nunits(s,'blk'):4d} {len(s)*1.28:7.1f} |"
                  f"{ee[0]:9.1f} [{ee[1]:8.1f},{ee[2]:8.1f}] |{np.nanpercentile(v,90):8.1f} "
                  f"{np.nanmax(v):8.1f}")
            OUT["g2_abs"].setdefault(arm, {})[b] = dict(
                n=len(s), blk=nunits(s, "blk"), sec=len(s) * 1.28, e=list(ee),
                p90=float(np.nanpercentile(v, 90)), max=float(np.nanmax(v)))

    S.hdr("B2  THE CORPUS'S OWN GRIND-#2 EVENT CRITERION, unchanged: e_40-49 > 500 ct, ENGAGED,\n"
          "    merged into events.  §7b in-regime exposure floor for an interpretable ZERO is\n"
          "    166 s (0.3-4 m/s, |ang| >= 100 deg).")
    print(f"  {'build':10s} {'in-regime s':>12s} {'floor?':>28s} | "
          f"{'strict events':>14s} {'any-speed events':>18s} {'creep hits':>11s}")
    OUT["g2_events"] = {}
    for b in LADDER:
        reg = [r for r in eng(R[b], b) if S.G2_VLO <= r["v"] < S.G2_VHI and r["ang"] >= S.G2_ANG]
        sec = len(reg) * 1.28
        strict = S._merge([r for r in reg if np.isfinite(r["e_40-49"])
                           and r["e_40-49"] > S.G2_THR])
        anysp = S._merge([r for r in eng(R[b], b) if np.isfinite(r["e_40-49"])
                          and r["e_40-49"] > S.G2_THR])
        creep_hits = [r for r in eng(R[b], b, lo0, hi0)
                      if np.isfinite(r["e_40-49"]) and r["e_40-49"] > S.G2_THR]
        flag = "MEETS 166 s floor" if sec >= S.G2_FLOOR else \
            f"{sec/S.G2_FLOOR:5.1%} of floor -- UNINTERPRETABLE ZERO"
        print(f"  {b:10s} {sec:12.1f} {flag:>28s} | {len(strict):14d} {len(anysp):18d} "
              f"{len(creep_hits):11d}")
        OUT["g2_events"][b] = dict(regime_sec=sec, meets_floor=bool(sec >= S.G2_FLOOR),
                                   strict=len(strict), anyspeed=len(anysp),
                                   creep_hits=len(creep_hits))

    S.hdr("B3  A THRESHOLD SWEEP, engaged creep -- because a bare '0 events at 500 ct' hides how\n"
          "    close the route came.  Fraction of engaged creep windows above each level.")
    OUT["g2_duty"] = {}
    for thr in (150.0, 250.0, 400.0, 500.0):
        print(f"\n  e_40-49 > {thr:.0f} ct, ENGAGED creep:")
        for b in LADDER:
            s = eng(R[b], b, lo0, hi0)
            if len(s) < 5:
                continue
            f = M.frac_ci(s, "e_40-49", thr, RNG, nboot=2000)
            print(f"    {b:10s} {100*f[0]:6.1f}% [{100*f[1]:5.1f},{100*f[2]:5.1f}] of {f[3]}w "
                  f"({f[3]*1.28:.0f} s)")
            OUT["g2_duty"].setdefault(f"{thr:.0f}", {})[b] = list(f)

    S.hdr("B4  THE TOP ENGAGED-CREEP 40-49 Hz WINDOWS on each new route, with the 26-31 Hz column\n"
          "    beside them.  🛑 fs ~ 100 Hz: the SECOND HARMONIC of a 26-31 Hz line folds to\n"
          "    38-48 Hz, i.e. straight into this band.  A large e_26-31 next to a large e_40-49\n"
          "    is a candidate fold, not necessarily a distinct line.  IMU column separates them:\n"
          "    grind #1 is a torsional COLUMN mode and never reaches the chassis; the 40-49 Hz\n"
          "    phenomenon does (coherence 0.82-0.88 on record).")
    OUT["g2_top"] = {}
    for b in ("V86/r6f", "V86B/r70"):
        print(f"\n  ---- {b} ----")
        e = sorted(eng(R[b], b, lo0, hi0),
                   key=lambda r: -(r["e_40-49"] if np.isfinite(r["e_40-49"]) else -1))
        print(f"    {'seg':>3s} {'t0':>7s} {'v':>6s} {'|ang|':>7s} {'rate':>6s} {'e40-49':>8s} "
              f"{'e26-31':>8s} {'e18-22':>8s} {'imu40':>8s} {'zig':>5s}")
        rows = []
        for r in e[:8]:
            print(f"    {r['seg']:3d} {r['t0']:7.1f} {r['v']:6.2f} {r['ang']:7.1f} "
                  f"{r['rate']:6.1f} {r['e_40-49']:8.1f} {r['e_26-31']:8.1f} "
                  f"{r['e_18-22']:8.1f} {r.get('imu40', np.nan):8.3f} {r.get('zig', 0):5d}")
            rows.append(dict(seg=int(r["seg"]), t0=float(r["t0"]), v=r["v"], ang=r["ang"],
                             e40=r["e_40-49"], e26=r["e_26-31"], e18=r["e_18-22"],
                             imu40=float(r.get("imu40", np.nan)), zig=int(r.get("zig", 0))))
        OUT["g2_top"][b] = rows

    S.hdr("B5  IS THE 40-49 Hz CONTENT ENGAGEMENT-CONDITIONAL AT CREEP?  If the operator's second\n"
          "    grinding complaint is this band, and it is LKAS-conditional as every other symptom\n"
          "    in this kit is, the engaged/manual ratio at creep must exceed 1.")
    for b in LADDER:
        e, m_ = eng(R[b], b, lo0, hi0), man(R[b], b, lo0, hi0, fwd_only=True)
        for r in e + m_:
            r["cell"] = tuple(r["cell"])[-3:]
        if len(e) < 8 or len(m_) < 8:
            print(f"  {b:10s}  nE={len(e)} nM={len(m_)} -- insufficient --")
            continue
        res = G.boot_cellwise(e, m_, "e_40-49", RNG, nboot=1500, min_ep=1, min_win=3)
        ctl = G.boot_cellwise(e, m_, "e_" + NEGCTRL, RNG, nboot=1500, min_ep=1, min_win=3)
        print(f"  {b:10s} nE={len(e):4d} nM={len(m_):4d}  40-49 eng/man {res[0]:6.2f} "
              f"[{res[1]:5.2f},{res[2]:6.2f}] c={res[3]:2d}   32-38 control {ctl[0]:6.2f} "
              f"[{ctl[1]:5.2f},{ctl[2]:6.2f}]")
        OUT.setdefault("g2_engman", {})[b] = dict(r40=[res[0], res[1], res[2], res[3]],
                                                  ctl=[ctl[0], ctl[1], ctl[2], ctl[3]])
    for b in LADDER:
        for r in R[b]:
            if len(tuple(r["cell"])) == 3:
                r["cell"] = (r["eng"],) + tuple(r["cell"])

    S.hdr("B6  🛑 THE CONTRADICTION, RESOLVED AS AN EXPOSURE PROBLEM.  Every earlier build's\n"
          "    'zero creep bursts' is compared to V86's burst RATE per second of in-regime\n"
          "    exposure.  If a build never spent time in the regime, its zero says nothing --\n"
          "    Poisson P(0) is printed so the reader can see how weak each zero is.")
    ref = OUT["g2_events"]["V86/r6f"]
    rate = ref["strict"] / max(ref["regime_sec"], 1e-9)
    print(f"\n  V86/r6f burst rate = {ref['strict']}/{ref['regime_sec']:.1f} s = "
          f"{rate:.4f} events/s in regime (0.3-4 m/s, |ang| >= 100 deg, engaged)")
    print(f"\n  {'build':10s} {'regime s':>9s} {'events':>7s} {'expected at V86 rate':>21s} "
          f"{'P(0) if V86 rate held':>22s}  reading")
    OUT["g2_poisson"] = {}
    for b in LADDER:
        d = OUT["g2_events"][b]
        exp = rate * d["regime_sec"]
        p0 = float(np.exp(-exp))
        rd = ("its zero is REAL evidence" if p0 < 0.05 else
              "🛑 its zero is UNINFORMATIVE" if d["strict"] == 0 else "burst present")
        print(f"  {b:10s} {d['regime_sec']:9.1f} {d['strict']:7d} {exp:21.2f} {p0:22.3f}  {rd}")
        OUT["g2_poisson"][b] = dict(regime_sec=d["regime_sec"], events=d["strict"],
                                    expected=exp, p0=p0)
    print("\n  MANUAL in-regime exposure and bursts on the same criterion (the engagement test):")
    for b in LADDER:
        mreg = [r for r in man(R[b], b, fwd_only=True)
                if S.G2_VLO <= r["v"] < S.G2_VHI and r["ang"] >= S.G2_ANG]
        hits = [r for r in mreg if np.isfinite(r["e_40-49"]) and r["e_40-49"] > S.G2_THR]
        mx = max((r["e_40-49"] for r in mreg if np.isfinite(r["e_40-49"])), default=float("nan"))
        print(f"    {b:10s} manual in-regime {len(mreg)*1.28:6.1f} s   bursts {len(hits)}   "
              f"max e_40-49 {mx:8.1f}")
        OUT.setdefault("g2_manual_regime", {})[b] = dict(sec=len(mreg) * 1.28, hits=len(hits),
                                                         max=float(mx))
    dump()


# =================================================================================================
#  C  V86B's MECHANISM -- "extra dampening on LKAS and in general at slow speed".
# =================================================================================================
def imped():
    """`r67_v81_t2t3`'s own impedance estimator with the two new routes added to its route table,
    so the numbers are directly commensurable with V81's recorded 1.471 and V84's 2.052.

    🛑 THE DECISIVE TEST IS THE MANUAL ARM.  V86B's cells are FactorC m26/m27 `Y[0]`, and modes
    24/25 (the manual columns) are BYTE-STOCK on both routes.  A damping difference in the MANUAL
    arm therefore CANNOT be V86B's cells and would mean something else differs between the drives.
    """
    import r67_v81_t2t3 as T23
    register()
    for b, cfg in NEW.items():
        T23.ROUTES[b] = (cfg["cache"], cfg["pfx"], cfg["segs"], cfg["parked"])
    T23.ROUTES.setdefault("V85/r6e", (ROOT / "_scratch/cache/r6e", "r6es", list(range(8)), [7]))
    T23.ROUTES.setdefault("V84/r6d", (ROOT / "_scratch/cache/r6d", "r6ds", list(range(12)), [11]))
    T23.ROUTES.setdefault("V83a/r68", (ROOT / "_scratch/cache/r68x", "r68xs", list(range(8)), [0, 7]))
    order = ["V81/r67", "V83a/r68", "V84/r6d", "V85/r6e", "V86/r6f", "V86B/r70"]
    D = {}
    for b in order:
        try:
            D[b] = T23.gather(b)
        except Exception as ex:
            print(f"  (skipped {b}: {ex})")
    S.hdr("C1  IMPEDANCE = |tq_lf| per deg/s of |rate_lf| -- how HEAVY the wheel is.\n"
          "    Frames restricted to the driver actually steering: |tq_lf| > 300 ct AND\n"
          "    |rate_lf| >= 2 deg/s.  ratio > 1 = HEAVIER engaged.  Every rate is d/dt of the\n"
          "    3 Hz-lowpassed column angle.\n"
          "    🛑 Both new routes are CREEP ONLY, so only the creep row exists for them.")
    OUT["imped"] = {}
    for b in order:
        if b not in D:
            continue
        d = D[b]
        act = (np.abs(d["tq_lf"]) > 300) & (np.abs(d["rate_lf"]) >= 2.0)
        imp = np.where(act, np.abs(d["tq_lf"]) / np.maximum(np.abs(d["rate_lf"]), 1e-9), np.nan)
        print(f"\n  ---- {b} ----   (sentinel frames dropped: {d['__sentinels__']})")
        print(f"     {'stratum':14s} {'nE':>7s} {'nM':>7s} | {'eng':>7s} {'man':>7s} | "
              f"{'ratio [95% CI]':>24s} | {'split-half null':>18s} | verdict")
        for nm, lo, hi in T23.STRATA:
            base = act & (d["v"] >= lo) & (d["v"] < hi)
            me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
            if me.sum() < 200 or mm.sum() < 200:
                print(f"     {nm:14s} {int(me.sum()):7d} {int(mm.sum()):7d} |  -- too few --")
                continue
            rr = T23.ratio_boot(imp[me], d["ep"][me], imp[mm], d["ep"][mm])
            nl = T23.split_half(imp[me], d["ep"][me])
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (rr[0] < nl[1] or rr[0] > nl[2]))
                 else "inside null")
            print(f"     {nm:14s} {int(me.sum()):7d} {int(mm.sum()):7d} | "
                  f"{np.nanmedian(imp[me]):7.1f} {np.nanmedian(imp[mm]):7.1f} | "
                  f"{rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:6.3f}] | [{nl[1]:6.3f},{nl[2]:6.3f}] | {v}")
            OUT["imped"].setdefault(b, {})[nm] = dict(
                ratio=list(rr), null=list(nl), nE=int(me.sum()), nM=int(mm.sum()),
                eng=float(np.nanmedian(imp[me])), man=float(np.nanmedian(imp[mm])))

    S.hdr("C2  🛑 THE DECISIVE TEST -- CROSS-ROUTE, ARM BY ARM.  V86B's cells are ENGAGED-ONLY by\n"
          "    construction (modes 24/25 byte-stock).  So:\n"
          "      ENGAGED arm  70 vs 6f  != 1  is consistent with V86B's cells acting.\n"
          "      MANUAL arm   70 vs 6f  != 1  CANNOT be V86B's cells -- it is a route/driver\n"
          "                                   difference, and it also invalidates the engaged read.")
    OUT["imped_cross"] = {}
    for A, B in (("V86B/r70", "V86/r6f"), ("V86/r6f", "V85/r6e"), ("V86B/r70", "V85/r6e")):
        if A not in D or B not in D:
            continue
        print(f"\n  ---- {A} / {B} ----")
        for arm, pick in (("ENGAGED", lambda d: d["lat"] > 0.5),
                          ("MANUAL ", lambda d: d["lat"] <= 0.5)):
            for nm, lo, hi in T23.STRATA:
                vals, eps = [], []
                for b in (A, B):
                    d = D[b]
                    act = (np.abs(d["tq_lf"]) > 300) & (np.abs(d["rate_lf"]) >= 2.0)
                    imp = np.where(act, np.abs(d["tq_lf"]) /
                                   np.maximum(np.abs(d["rate_lf"]), 1e-9), np.nan)
                    m = act & pick(d) & (d["v"] >= lo) & (d["v"] < hi)
                    vals.append(imp[m])
                    eps.append(d["ep"][m])
                if min(len(vals[0]), len(vals[1])) < 200:
                    continue
                rr = T23.ratio_boot(vals[0], eps[0], vals[1], eps[1])
                nl = T23.split_half(vals[0], eps[0])
                v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (rr[0] < nl[1] or rr[0] > nl[2]))
                     else "inside null")
                print(f"    {arm} {nm:14s} nA={len(vals[0]):6d} nB={len(vals[1]):6d} | "
                      f"{np.nanmedian(vals[0]):7.1f} / {np.nanmedian(vals[1]):7.1f} | "
                      f"{rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:6.3f}] | null "
                      f"[{nl[1]:6.3f},{nl[2]:6.3f}] | {v}")
                OUT["imped_cross"].setdefault(f"{A}|{B}", {})[f"{arm.strip()}|{nm}"] = dict(
                    ratio=list(rr), null=list(nl), nA=int(len(vals[0])), nB=int(len(vals[1])),
                    medA=float(np.nanmedian(vals[0])), medB=float(np.nanmedian(vals[1])))

    S.hdr("C3  THE TWO FACTORS SEPARATELY -- is the driver pushing harder, or moving the wheel\n"
          "    less, or both?  A damper raises |tq| at the same |rate|; a driver simply steering\n"
          "    less raises the ratio without any firmware change.")
    for b in order:
        if b not in D:
            continue
        d = D[b]
        print(f"\n  ---- {b} ----")
        for nm, lo, hi in T23.STRATA:
            base = (d["v"] >= lo) & (d["v"] < hi) & (np.abs(d["tq_lf"]) > 300) \
                & np.isfinite(d["rate_lf"])
            me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
            if me.sum() < 200 or mm.sum() < 200:
                continue
            te, tm = np.median(np.abs(d["tq_lf"][me])), np.median(np.abs(d["tq_lf"][mm]))
            re, rm = np.median(np.abs(d["rate_lf"][me])), np.median(np.abs(d["rate_lf"][mm]))
            print(f"     {nm:14s} |tq_lf| eng {te:6.0f} / man {tm:6.0f} ({te/tm:5.3f}x)   "
                  f"|rate_lf| eng {re:6.2f} / man {rm:6.2f} ({re/max(rm,1e-9):5.3f}x)   "
                  f"nE={int(me.sum())} nM={int(mm.sum())}")
            OUT.setdefault("imped_factors", {})[f"{b}|{nm}"] = dict(tq=[te, tm], rate=[re, rm])

    S.hdr("C4  🛑 IS THIS INSTRUMENT EVEN ABLE TO SEE V86B's DOSE?  Two facts decide it.\n"
          "    (a) RESOLUTION: the width of the engaged-arm cross-route CI is the smallest ratio\n"
          "        the estimator can call.  V86B's damper is on record at 0.11x V81's dose at\n"
          "        42 deg/s and 0.42x at 85 deg/s -- STATE.md's '10.1%' holds at ONE point only.\n"
          "    (b) PRIOR CALIBRATION: V84 DELETED the engaged-only damper outright and this same\n"
          "        estimator moved the WRONG WAY (V81 1.471 -> V84 2.052 at 10-40 km/h, recorded).\n"
          "        An estimator that did not track a 100% dose change cannot be trusted to detect\n"
          "        an 11-42% one.  A null here is WEAK evidence, not evidence of absence.")
    OUT["imped_power"] = {}
    for A, B in (("V86B/r70", "V86/r6f"),):
        for arm in ("ENGAGED", "MANUAL"):
            k = f"{arm}|creep <10 kph"
            d = OUT.get("imped_cross", {}).get(f"{A}|{B}", {}).get(k)
            if not d:
                continue
            lo, hi = d["ratio"][1], d["ratio"][2]
            print(f"\n    {A}/{B} {arm:8s} creep: ratio {d['ratio'][0]:.3f} [{lo:.3f},{hi:.3f}]"
                  f"  ⇒ resolvable effect size >= {max(hi/1.0, 1.0/max(lo,1e-9)):.2f}x")
            OUT["imped_power"][f"{A}|{B}|{arm}"] = dict(
                ratio=d["ratio"], resolvable=float(max(hi, 1.0 / max(lo, 1e-9))))
    dump()


def analyze():
    G.EPKEY = "blk"
    a0_identity()
    R = build_records()
    a1_exposure(R)
    a2_unit(R)
    a3_nulls(R)
    a4_roughness(R)
    a5_bands(R)
    a6_ratios(R)
    a7_engman(R)
    dump()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "records":
        r = build_records(rebuild="--rebuild" in sys.argv)
        for b in LADDER:
            print(f"  {b:10s} {len(r[b]):6d} windows, engaged {len(eng(r[b], b)):6d}")
    elif cmd == "grind2":
        grind2()
    elif cmd == "imped":
        imped()
    elif cmd == "matched":
        matched()
    elif cmd == "all":
        analyze()
        grind2()
        imped()
        matched()
    else:
        analyze()
