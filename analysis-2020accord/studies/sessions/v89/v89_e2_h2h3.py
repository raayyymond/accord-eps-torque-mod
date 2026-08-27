#!/usr/bin/env python3
r"""V89 flight -- H2 (THE LEVER) and H3 (THE OPERATOR'S CONSTRAINT), routes 75/76 vs route 73 (V88).

🛑 THE INSTRUMENT IS THE CORPUS'S, NOT A NEW ONE.  `_grind2_lib.wrecs` at NFFT 256 / hop 128, p99
analytic band envelope, ~10.2 s `blk` units nested in engagement runs, `boot_cellwise` cell-stratified
log-ratios over (eng, SPEED bin, EFFORT bin, RATE bin) -- i.e. speed- AND rate-matching is built into
the estimator -- and `split_half_null` printed BEFORE every ratio.  Bands are `compare_v75_v76_v80_
grind.BANDS_EXT`, which is what installs the 32-38 Hz negative control.

H2  engaged 6-9 Hz column energy (`e_6-9`, ratchet) must FALL vs V88, CI excluding 1.00, with the
    32-38 Hz control NOT falling as much.  Wheel-order veto (orders 1-6, circumference 2.073-2.088 m,
    0.8 Hz guard) on every 6-9 Hz claim, with a per-window speed census.
H3  0.5-3 Hz LKAS command content must NOT FALL.  Channel is the 427 packer's
    `wire = clamp((|gp-0x6b98|*5)>>3, 0, 0x3FF)` at ~50 Hz -- V87 edit #6, unchanged on V88 and V89.
    🛑 V88's b7 SIGN bit is NOT available on V89 (the cave was repointed to the friction term), so
    this is the RECTIFIED magnitude, exactly the channel V88's own H1 0.5-3 Hz row used.

🛑 CONTROLS RUN FIRST.  Every ratio is preceded by both arms' own split-half nulls; a ratio inside
   either null is reported as NOT RESOLVABLE, never as an effect.
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
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "_scratch/cache/r73"))

import _grind2_lib as G          # noqa: E402
import _r31_common as C31        # noqa: E402
import _r47_lib as R47           # noqa: E402
import _r4f_lib as R4F           # noqa: E402
import compare_v75_v76_v80_grind as M   # noqa: E402  -- installs BANDS_EXT incl. the 32-38 control
from v88_d1_exposure import grid  # noqa: E402  -- THE 50 Hz command grid, verbatim

RNG = np.random.default_rng(89_2233)
PKL = ROOT / "_scratch/cache/r75" / "records_v89_score.pkl"
OUTJ = ROOT / "_scratch/cache/r75" / "v89_e2_h2h3.json"

BUILDS = {
    "V88/r73": dict(cache=ROOT / "_scratch/cache/r73", pfx="r73s", segs=list(range(11)), parked=[10],
                    stem="r73", kd=9.88),
    "V89/r75": dict(cache=ROOT / "_scratch/cache/r75", pfx="r75s", segs=list(range(16)), parked=[14, 15],
                    stem="r75", kd=9.89),
    "V89/r76": dict(cache=ROOT / "_scratch/cache/r76", pfx="r76s", segs=list(range(13)), parked=[],
                    stem="r76", kd=9.89),
}
ARMS = ["V88/r73", "V89/r75", "V89/r76"]
CIRC, CIRC_LO, CIRC_HI, ORDERS, GUARD = 2.0805, 2.073, 2.088, (1, 2, 3, 4, 5, 6), 0.8
SPEED = [("creep <10 km/h", 0.0, 2.78), ("10-40", 2.78, 11.11), ("40-80", 11.11, 22.22),
         (">80 km/h", 22.22, 1e9)]
OUT = {}


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def order_hit(f0, v):
    """True if ANY wheel order, over the circumference UNCERTAINTY, lands within GUARD of f0."""
    if not (np.isfinite(f0) and np.isfinite(v)):
        return False
    return any(abs(k * v / c - f0) < GUARD
               for k in ORDERS for c in (CIRC_LO, CIRC, CIRC_HI))


def build_records(rebuild=False):
    R4F.install_fs()                    # the lattice fs estimator, for EVERY arm or none
    for b, cfg in BUILDS.items():
        G.BUILDS[b] = dict(cache=cfg["cache"], pfx=cfg["pfx"], segs=cfg["segs"], kd=cfg["kd"])
    if PKL.exists() and not rebuild:
        st = pickle.load(open(PKL, "rb"))
        if st.get("__bands__") == sorted(M.BANDS_EXT) and all(b in st for b in ARMS):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    st = {"__bands__": sorted(M.BANDS_EXT)}
    for b in ARMS:
        print(f"  wrecs {b} ...", flush=True)
        st[b] = M.augment2(R47.augment(G.wrecs(b)))
        print(f"    {len(st[b])} windows", flush=True)
    pickle.dump(st, open(PKL, "wb"))
    return {k: v for k, v in st.items() if not k.startswith("__")}


def eng(rs, b):
    return [r for r in rs if r["eng"] == 1 and r["seg"] not in BUILDS[b]["parked"]]


def nblk(rs):
    return len({r["blk"] for r in rs})


def census(rs, label):
    v = G.col(rs, "v")
    rt = G.col(rs, "rate")
    print(f"      census {label}: n={len(rs)} blk={nblk(rs)}  " +
          " ".join(f"{nm} {int(np.sum((v>=lo)&(v<hi)))}" for nm, lo, hi in SPEED) +
          f"  | v med {np.median(v):.2f} m/s  rate med {np.median(rt):.1f}")
    return {nm: int(np.sum((v >= lo) & (v < hi))) for nm, lo, hi in SPEED}


def ratio_row(A, B, key, tag, nboot=2000):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=nboot)
    print(f"    {tag:34s} {key:8s}  {r:6.3f} [{lo:6.3f},{hi:6.3f}]  cells {nc:2d}  "
          f"ep {na}/{nb}")
    return dict(ratio=r, lo=lo, hi=hi, cells=nc, epA=na, epB=nb)


# =================================================================================================
def h2(R):
    hdr("H2  THE LEVER -- engaged 6-9 Hz COLUMN energy, V89 vs V88, speed- AND rate-matched\n"
        "    boot_cellwise stratifies on (eng, v-bin, effort-bin, rate-bin); CONTROLS FIRST.")
    E = {b: eng(R[b], b) for b in ARMS}
    for b in ARMS:
        census(E[b], b)

    sub("CONTROL 1 -- each arm's OWN split-half null.  Any ratio inside these is NOT resolvable.")
    OUT["split_half"] = {}
    for b in ARMS:
        for key in ("e_6-9", "e_32-38", "e_1-4"):
            md, lo, hi = G.split_half_null(E[b], key, RNG, nrep=300)
            OUT["split_half"][f"{b}/{key}"] = [md, lo, hi]
            print(f"    {b:10s} {key:8s} split-half null [{lo:6.3f}, {hi:6.3f}]")

    sub("H2 -- the ratio.  e_6-9 is the claim; e_32-38 is the pre-declared NEGATIVE CONTROL; "
        "e_1-4 is the matching VALIDITY check (driver input: must be ~1.00 if matching worked).")
    OUT["h2"] = {}
    for a in ("V89/r75", "V89/r76"):
        for key in ("e_1-4", "e_6-9", "e_18-22", "e_32-38"):
            OUT["h2"][f"{a}÷V88/r73/{key}"] = ratio_row(E[a], E["V88/r73"], key,
                                                        f"{a} / V88/r73")
    pooled = E["V89/r75"] + E["V89/r76"]
    print()
    for key in ("e_1-4", "e_6-9", "e_18-22", "e_26-31", "e_32-38", "e_40-49"):
        OUT["h2"][f"V89 pooled÷V88/r73/{key}"] = ratio_row(pooled, E["V88/r73"], key,
                                                           "V89 POOLED (r75+r76) / V88/r73")

    sub("H2 with the WHEEL-ORDER VETO applied to the 6-9 Hz claim (orders 1-6, guard 0.8 Hz, "
        "circumference swept 2.073-2.088 m).  A window is dropped if an order lands on the line "
        "THAT WINDOW measured.")
    OUT["h2_veto"] = {}
    Vt = {}
    for b in ARMS:
        keep = [r for r in E[b] if not order_hit(r["f_6-9"], r["v"])]
        print(f"    {b:10s} {len(keep)}/{len(E[b])} windows survive the veto "
              f"({len(E[b]) - len(keep)} dropped)")
        Vt[b] = keep
        census(keep, b + " vetoed")
    for b in ARMS:
        md, lo, hi = G.split_half_null(Vt[b], "e_6-9", RNG, nrep=300)
        OUT["h2_veto"][f"split_half/{b}"] = [md, lo, hi]
        print(f"    {b:10s} e_6-9 VETOED split-half null [{lo:6.3f}, {hi:6.3f}]")
    for a in ("V89/r75", "V89/r76"):
        OUT["h2_veto"][f"{a}"] = ratio_row(Vt[a], Vt["V88/r73"], "e_6-9", f"{a} / V88/r73 VETOED")
    OUT["h2_veto"]["pooled"] = ratio_row(Vt["V89/r75"] + Vt["V89/r76"], Vt["V88/r73"], "e_6-9",
                                         "V89 POOLED / V88/r73 VETOED")

    sub("the ratchet LINE itself -- f0 and prominence, order-vetoed, per arm")
    OUT["line"] = {}
    for b in ARMS:
        ss = [r for r in Vt[b] if np.isfinite(r["f_6-9"])]
        if len(ss) < 5:
            continue
        f0 = G.boot_median_ci(ss, "f_6-9", RNG, nboot=1500)
        pr = G.boot_median_ci(ss, "p_6-9", RNG, nboot=1500)
        ee = G.boot_median_ci(ss, "e_6-9", RNG, nboot=1500)
        print(f"    {b:10s} n={len(ss):4d} blk={nblk(ss):3d}  f0 {f0[0]:5.2f} "
              f"[{f0[1]:5.2f},{f0[2]:5.2f}] Hz   prom {pr[0]:5.2f} [{pr[1]:5.2f},{pr[2]:5.2f}]   "
              f"e_6-9 {ee[0]:7.1f} [{ee[1]:6.1f},{ee[2]:7.1f}]")
        OUT["line"][b] = dict(n=len(ss), f0=list(f0), prom=list(pr), env=list(ee))

    sub("★ THE OPERATOR'S OWN REGIMES -- e_6-9 by WHEEL RATE, engaged, order-vetoed")
    OUT["rate_regime"] = {}
    for nm, lo, hi in (("micro 1-13 deg/s", 1.0, 13.0), ("ratchet 13-50", 13.0, 50.0),
                       ("macro >50", 50.0, 1e9)):
        row = {}
        for b in ARMS:
            ss = [r for r in Vt[b] if lo <= r["rate"] < hi]
            if len(ss) < 8:
                row[b] = None
                print(f"    {nm:18s} {b:10s} n={len(ss)} -- too few, NOT SCOREABLE")
                continue
            ee = G.boot_median_ci(ss, "e_6-9", RNG, nboot=1500)
            row[b] = dict(n=len(ss), env=list(ee))
            print(f"    {nm:18s} {b:10s} n={len(ss):4d} blk={nblk(ss):3d}  "
                  f"e_6-9 {ee[0]:7.1f} [{ee[1]:6.1f},{ee[2]:7.1f}]")
        A = [r for r in Vt["V89/r75"] + Vt["V89/r76"] if lo <= r["rate"] < hi]
        B = [r for r in Vt["V88/r73"] if lo <= r["rate"] < hi]
        if len(A) >= 8 and len(B) >= 8:
            row["ratio"] = ratio_row(A, B, "e_6-9", f"  {nm} V89pool/V88")
        OUT["rate_regime"][nm] = row


# =================================================================================================
BANDS3 = [(0.5, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 12.0), (15.0, 22.0)]
NW, HOP = 256, 128


def band_rms(x, fs, lo, hi):
    b = butter(2, [lo, hi], btype="band", fs=fs)
    return float(np.std(filtfilt(*b, np.asarray(x, float))))


def cmd_records(g, vlo=None, vhi=None):
    """Per-window band rms of the 427 delivered-command magnitude, engaged runs only."""
    fs = g["fs"]
    out = []
    for a, b in C31.runs_of(g["lat"], g["t"], NW, max_gap=0.10):
        x = np.asarray(g["cts"][a:b], float)
        if not np.all(np.isfinite(x)):
            continue
        yb = {f"{lo}-{hi}": filtfilt(*butter(2, [lo, hi], btype="band", fs=fs), x)
              for lo, hi in BANDS3}
        nwin = 0
        for j0 in range(0, (b - a) - NW + 1, HOP):
            sl, loc = slice(a + j0, a + j0 + NW), slice(j0, j0 + NW)
            vv = np.abs(g["v"][sl])
            vmed = float(np.median(vv))
            r = dict(v=vmed, clip=float(np.mean(g["clip"][sl])),
                     eff=float(np.mean(np.abs(C31.sustained(g["tq"][sl], fs)))),
                     rate=float(np.mean(np.abs(g["rate_c"][sl]))),
                     dc=float(np.median(g["cts"][sl])),
                     blk=(int(np.median(g["seg"][sl])), a, nwin // 8))
            for k, y in yb.items():
                r["b_" + k] = float(np.std(y[loc]))
            r["cell"] = (1, G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                         G.binof(r["rate"], G.R_BINS))
            r["ep"] = r["blk"]
            nwin += 1
            if vlo is not None and not (vlo <= vmed < vhi):
                continue
            out.append(r)
    return out


def h3(GR):
    hdr("H3  THE OPERATOR'S CONSTRAINT -- 0.5-3 Hz LKAS COMMAND CONTENT MUST NOT FALL.\n"
        "    §6b's verified sign chain says V89 ADDS assist, so a small RISE is the prediction.\n"
        "    🛑 A FALL means the sign chain is inverted somewhere, and that is the headline.")
    W = {b: cmd_records(GR[b]) for b in ARMS}
    Wc = {b: [r for r in W[b] if r["clip"] == 0.0] for b in ARMS}
    for b in ARMS:
        print(f"    {b:10s} {len(W[b])} engaged 5.14 s windows, {len(Wc[b])} with ZERO railed "
              f"samples ({len({r['blk'] for r in Wc[b]})} blocks)  median |cmd| DC "
              f"{np.median([r['dc'] for r in Wc[b]]):.0f} ct")

    sub("CONTROL FIRST -- each arm's own split-half null on the 0.5-3 Hz command rms")
    OUT["h3_split_half"] = {}
    for b in ARMS:
        md, lo, hi = G.split_half_null(Wc[b], "b_0.5-3.0", RNG, nrep=300)
        OUT["h3_split_half"][b] = [md, lo, hi]
        print(f"    {b:10s} [{lo:6.3f}, {hi:6.3f}]")

    sub("H3 -- cell-stratified (speed x effort x rate) ratio of the delivered command's band rms")
    OUT["h3"] = {}
    pooled = Wc["V89/r75"] + Wc["V89/r76"]
    for lo, hi in BANDS3:
        k = f"b_{lo}-{hi}"
        for a in ("V89/r75", "V89/r76"):
            OUT["h3"][f"{a}/{k}"] = ratio_row(Wc[a], Wc["V88/r73"], k, f"{a} / V88/r73")
        OUT["h3"][f"pooled/{k}"] = ratio_row(pooled, Wc["V88/r73"], k, "V89 POOLED / V88/r73")
        print()

    sub("the same on the UPSTREAM openpilot request (0x0E4) -- if THAT moved, the change is not "
        "the EPS's")
    OUT["h3_e4"] = {}
    for b in ARMS:
        g = GR[b]
        m = g["lat"]
        OUT["h3_e4"][b] = dict(rms=float(np.std(g["e4tq"][m])),
                               absmed=float(np.median(np.abs(g["e4tq"][m]))))
        print(f"    {b:10s} 0x0E4 engaged: rms {OUT['h3_e4'][b]['rms']:.1f}   "
              f"median |req| {OUT['h3_e4'][b]['absmed']:.1f}")


# =================================================================================================
if __name__ == "__main__":
    rebuild = "rebuild" in sys.argv
    R = build_records(rebuild)
    GR = {b: grid(BUILDS[b]["cache"], BUILDS[b]["stem"]) for b in ARMS}
    h2(R)
    h3(GR)
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
