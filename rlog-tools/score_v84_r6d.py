#!/usr/bin/env python3
"""SCORE THE V84 FLIGHT (route `6d`) against its four PRE-REGISTERED predictions.

Predictions, fixed before the drive in `docs/HANDOFF-2026-08-08-v83a-flew-and-r24-is-the-actor.md`
§7a.  They are quoted here verbatim so the falsifier cannot be re-negotiated after the numbers land:

  S1  grind #1, 18-22 Hz engaged creep   "~ 0.40x V83A's level -- back toward V67/V68's median
      e_18-22 ~ 109.  🛑 IF IT DOES NOT IMPROVE, LEVER B IS FALSIFIED ON A THIRD INDEPENDENT
      FLIGHT AND THE RATE LANE SHOULD BE ABANDONED AS AN S1 LEVER."
  S2  micro-ratchet 6-9 Hz               "GENUINELY UNCERTAIN, and this is its FIRST REAL TEST."
  S3  macro ratchet <=30 mph             "improved."  No instrument -- operator is the arbiter.
  S4  impedance / friction               "engaged-vs-manual asymmetry STRUCTURALLY ZERO."
      V81 measured 1.471 [0.980, 1.812]; V84 deletes the Coulomb damper => predicted ~ 1.00.

🛑 WHY THIS FILE IS IN `rlog-tools/` AND NOT A SCRATCHPAD.  Route 68's scoring code and cache were
left in a session scratchpad and lost -- record defect 9.2 of the same handoff, and the reason every
route-68 number in it is currently irreproducible.  `extract_r6d_r68.py` + this file are that
promotion.  Route 5d is the older instance of the same defect.

🛑 THE INSTRUMENT IS THE CORPUS'S, NOT A NEW ONE.  Every band envelope, prominence, episode
bootstrap, split-half null and cell-stratified ratio below is `_grind2_lib`'s, reached through
`compare_v75_v76_v80_grind` (NFFT 256 / hop 128, p99 analytic band envelope, ~10.2 s `blk` units
nested inside engagement runs) and `compare_r67_v81_grind`.  The impedance section calls
`r67_v81_t2t3`'s own T3 estimator with this route added to its route table, so V84's number is
directly commensurable with V81's 1.471.

METHOD RULES THAT HAVE EACH ALREADY RETRACTED A CLAIM IN THIS KIT
  * Bootstrap over EPISODES, never windows (`memory/feedback-episodes-not-windows.md`).
  * The SPLIT-HALF NULL is computed and printed BEFORE any cross-build ratio.  A ratio inside its
    own null is not a result.
  * Averaged spectra compare two routes only if their SPEED DISTRIBUTIONS MATCH -- S0b is a
    per-window speed census, because wheel order 1 = v / 2.0805 m moves a line across the bands.
  * 32-38 Hz is the PRE-DECLARED NEGATIVE CONTROL.  If it moves with the others, the whole HF
    region moved and nothing band-specific was measured.

Usage:
    python score_v84_r6d.py records     # build/refresh the window records  (slow, ~10 min)
    python score_v84_r6d.py analyze     # S0-S7  the band scoring
    python score_v84_r6d.py grind2      # the grind-#2 event hunt + the §7b exposure accounting
    python score_v84_r6d.py ring        # the 26-31 Hz highway ring / limit cycle
    python score_v84_r6d.py imped       # S4: engaged-vs-manual impedance, V81's own estimator
    python score_v84_r6d.py all
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import compare_v75_v76_v80_grind as M  # noqa: E402  -- THE instrument
import _grind2_lib as G  # noqa: E402
import _r47_lib as R47  # noqa: E402
import _r31_common as C31  # noqa: E402

CACHE6D = ROOT / "_cache_r6d"
CACHE68 = ROOT / "_cache_r68x"
KMH = 1.0 / 3.6
CIRC = 2.0805                       # tyre circumference, m.  wheel order n line = n * v / CIRC Hz

# --------------------------------------------------------------------------------- the builds ----
# `kd` is a LABEL only; nothing here regresses on it.  PARKED = segments with no engaged driving.
NEW = {
    "V84/r6d":  dict(cache=CACHE6D, pfx="r6ds",  segs=list(range(12)), parked=[11], kd=9.84),
    "V83a/r68": dict(cache=CACHE68, pfx="r68xs", segs=list(range(8)),  parked=[0, 7], kd=9.83),
}
# Ordered oldest -> newest.  V67/V68 are the kit's BEST grind-#1 result (median e_18-22 ~ 109) and
# carry V84's Lever B bytes; V81/V83a are the immediate predecessors; V76/V80 anchor the ladder.
LADDER = ["V76/r65", "V80/r66", "V67/r47", "V68/r4e", "V81/r67", "V83a/r68", "V84/r6d"]
PARKED = dict(M.PARKED)
PARKED["V81/r67"] = [13]
for b, cfg in NEW.items():
    PARKED[b] = cfg["parked"]

BANDS = ["6-9", "18-22", "26-31", "40-49", "30-49", "32-38"]     # 32-38 = NEGATIVE CONTROL
NEGCTRL = "32-38"
STRATA = M.STRATA
MYPKL = CACHE6D / "records_v84_score.pkl"
RNG = np.random.default_rng(84_6013)
OUT = {}


def hdr(s):
    print("\n" + "=" * 112)
    print(s)
    print("=" * 112, flush=True)


def register():
    import compare_r67_v81_grind as C67            # owns the V81/r67 registration
    C67.register5()                                # calls M.register(): V80 + lattice fs, then V81
    for b, cfg in NEW.items():
        G.BUILDS[b] = dict(cache=cfg["cache"], pfx=cfg["pfx"], segs=cfg["segs"], kd=cfg["kd"])


def augment3(recs, nfft=None):
    """Add the two covariates the grind-#2 question needs and no prior augment carries:

      `imu40/imu18/imu6`  the CHASSIS vertical accelerometer's envelope in each band.  🛑 This is
            the discriminator between the two grinds: grind #1 is a torsional COLUMN mode and never
            reaches the chassis, grind #2 does (coherence 0.82-0.88 on record).  A 40-49 Hz burst on
            the torsion bar with no IMU excess is grind #1's band leaking, not grind #2.
      `lchg`  blinker up anywhere in the window -- the operator felt one instance on a LANE CHANGE.

    Same re-slice-at-`t0` pattern as `_r47_lib.augment` / `augment2`, so the slice cannot drift.
    Caches that predate these fields get NaN, never a silent zero.
    """
    nfft = nfft or G.NFFT
    by = {}
    for r in recs:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    for (build, seg), rs in by.items():
        B = G.BUILDS[build]
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            continue
        d = C31.load(seg, B["cache"], B["pfx"])
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        taper = np.hanning(nfft) + 1e-3
        cw = slice(int(0.2 * nfft), int(0.8 * nfft))
        imu = np.asarray(d["imu_vert"], float) if "imu_vert" in d else None
        lch = np.asarray(d["cs_lchg"], float) if "cs_lchg" in d else None
        for r in rs:
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            sl = slice(i0, i0 + nfft)
            for k in ("imu40", "imu18", "imu6"):
                r[k] = np.nan
            r["lchg"] = np.nan
            if imu is not None and len(imu[sl]) == nfft and np.all(np.isfinite(imu[sl])):
                x = imu[sl]
                r["imu40"] = G.win_env(x, fs, 40.0, 49.0, taper, cw)
                r["imu18"] = G.win_env(x, fs, 18.0, 22.0, taper, cw)
                r["imu6"] = G.win_env(x, fs, 6.0, 9.0, taper, cw)
            if lch is not None and len(lch[sl]) == nfft:
                r["lchg"] = float(np.nanmax(lch[sl]))
    return recs


def build_records(rebuild=False):
    register()
    if MYPKL.exists() and not rebuild:
        with open(MYPKL, "rb") as fh:
            st = pickle.load(fh)
        if st.get("__bands__") == sorted(M.BANDS_EXT) and all(b in st for b in LADDER):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    st = {"__bands__": sorted(M.BANDS_EXT)}
    for b in LADDER:
        print(f"  wrecs {b} ...", flush=True)
        rs = augment3(M.augment2(R47.augment(G.wrecs(b))))
        st[b] = rs
        print(f"    {len(rs)} windows", flush=True)
    CACHE6D.mkdir(exist_ok=True)
    with open(MYPKL, "wb") as fh:
        pickle.dump(st, fh)
    return {k: v for k, v in st.items() if not k.startswith("__")}


def eng(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 1 and r["seg"] not in PARKED.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def man(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 0 and r["seg"] not in PARKED.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def nunits(rs, key=None):
    return len({r[key or G.EPKEY] for r in rs})


# =================================================================================================
#  ANALYZE -- S0 exposure & speed census, S1 bands, S2 nulls, S3 ratios, S5 identity, S6 duty
# =================================================================================================
def analyze():
    G.EPKEY = "blk"
    R = build_records()

    hdr("S0  EXPOSURE CENSUS -- engaged only, parked segments dropped.\n"
        "    A stratum with < 5 windows is not scored; a stratum with < ~8 blocks has no usable CI.")
    print(f"{'build':10s} {'wins':>5s} {'sec':>7s} {'blk':>4s} {'run':>4s} | "
          + " ".join(f"{nm:>13s}" for nm, _, _ in STRATA))
    OUT["exposure"] = {}
    for b in LADDER:
        e = eng(R[b], b)
        row = [f"{b:10s} {len(e):5d} {len(e) * 1.28:7.1f} "
               f"{nunits(e,'blk'):4d} {nunits(e,'ep'):4d} |"]
        st = {}
        for nm, lo, hi in STRATA:
            s = eng(R[b], b, lo, hi)
            row.append(f"  {len(s):4d}w/{nunits(s,'blk'):2d}b ")
            st[nm] = dict(n=len(s), blk=nunits(s, "blk"), sec=len(s) * 1.28,
                          v_med=float(np.median(G.col(s, "v"))) if s else float("nan"),
                          eff_med=float(np.median(G.col(s, "eff"))) if s else float("nan"),
                          rate_med=float(np.median(G.col(s, "rate"))) if s else float("nan"),
                          ang_med=float(np.median(G.col(s, "ang"))) if s else float("nan"))
        print("".join(row))
        OUT["exposure"][b] = dict(n=len(e), sec=len(e) * 1.28, strata=st)
    print("\n  per-stratum MEDIAN speed v (m/s) / sustained EFFORT e (ct) / |rate| r / |angle| a:")
    for nm, _, _ in STRATA:
        print(f"  {nm:14s} " + "  ".join(
            "%s v=%5.2f e=%5.0f r=%5.1f a=%5.1f" % (
                b.split('/')[0], OUT['exposure'][b]['strata'][nm]['v_med'],
                OUT['exposure'][b]['strata'][nm]['eff_med'],
                OUT['exposure'][b]['strata'][nm]['rate_med'],
                OUT['exposure'][b]['strata'][nm]['ang_med']) for b in LADDER))

    # ---------------------------------------------------------------- S0b SPEED CENSUS ----------
    hdr("S0b  PER-WINDOW SPEED CENSUS -- 🛑 MANDATORY before any averaged-spectrum comparison.\n"
        "     Wheel order 1 sits at v / 2.0805 Hz and MOVES WITH SPEED, so mismatched speed\n"
        "     distributions manufacture an 'only on route X' line.  Order-2 = 2x that.")
    VB = [(0.0, 0.5), (0.5, 1.5), (1.5, 2.78), (2.78, 5.0), (5.0, 8.0), (8.0, 11.1),
          (11.1, 16.0), (16.0, 22.2), (22.2, 40.0)]
    print(f"{'build':10s} " + " ".join(f"{lo:.1f}-{hi:.1f}".rjust(10) for lo, hi in VB))
    OUT["speed_census"] = {}
    for b in LADDER:
        e = eng(R[b], b)
        v = G.col(e, "v")
        cnt = [int(((v >= lo) & (v < hi)).sum()) for lo, hi in VB]
        print(f"{b:10s} " + " ".join(f"{100 * c / max(len(v),1):9.1f}%" for c in cnt))
        OUT["speed_census"][b] = dict(bins=[list(x) for x in VB], frac=[c / max(len(v), 1)
                                                                        for c in cnt], n=len(v))
    print("\n  wheel-order-1 line (Hz) implied by each build's engaged speeds, and the fraction of\n"
          "  engaged windows whose order-1 or order-2 line lands INSIDE each scoring band:")
    print(f"{'build':10s} {'ord1 med':>9s} {'ord1 IQR':>16s} | "
          + " ".join(f"{bd:>12s}" for bd in BANDS))
    for b in LADDER:
        e = eng(R[b], b)
        v = G.col(e, "v")
        o1, o2 = v / CIRC, 2 * v / CIRC
        row = f"{b:10s} {np.median(o1):9.2f} [{np.percentile(o1,25):6.2f},{np.percentile(o1,75):6.2f}] | "
        for bd in BANDS:
            lo, hi = M.BANDS_EXT[bd]
            f1 = float(np.mean((o1 >= lo) & (o1 <= hi)))
            f2 = float(np.mean((o2 >= lo) & (o2 <= hi)))
            row += f" {100*f1:4.1f}/{100*f2:4.1f}%"
            OUT["speed_census"][b][f"order_in_{bd}"] = [f1, f2]
        print(row)
    print("  (read as  order1% / order2%  of engaged windows contaminated by a wheel line)")

    # ---------------------------------------------------------------- S2 NULL (FIRST) -----------
    hdr("S2  SPLIT-HALF NULL -- computed and printed BEFORE any cross-build ratio.\n"
        "    Each route halved against ITSELF with the IDENTICAL estimator, 300 halvings.\n"
        "    🛑 A ratio inside the wider of the two builds' nulls is NOT a result.")
    OUT["null"] = {}
    print(f"{'band':8s} {'build':10s} {'null median':>12s} {'null 95% interval':>26s}")
    for bd in BANDS:
        for b in LADDER:
            e = eng(R[b], b)
            n = G.split_half_null(e, "e_" + bd, RNG, nrep=300, min_ep=2, min_win=4)
            print(f"{bd:8s} {b:10s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]")
            OUT["null"].setdefault(bd, {})[b] = list(n)
        print()

    hdr("S2b  CREEP-ONLY SPLIT-HALF NULL (<10 km/h, engaged) -- the null that actually governs the\n"
        "     S1 verdict, because S1's prediction is about the CREEP stratum, not the route mean.")
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

    # ---------------------------------------------------------------- S1 BAND TABLE -------------
    hdr("S1  SPEED-STRATIFIED BAND TABLE -- engaged only.  median [2.5%, 97.5%] block-bootstrap.\n"
        "    e_band = p99 analytic band-envelope AMPLITUDE of the torsion bar, counts (p-p = 2x).")
    OUT["bands"] = {}
    for bd in BANDS:
        tag = {"18-22": "GRIND #1", "6-9": "micro-ratchet ~7.8 Hz", "26-31": "the RING ~28 Hz",
               "40-49": "GRIND #2", "30-49": "HF floor",
               NEGCTRL: "🛑 PRE-DECLARED NEGATIVE CONTROL"}[bd]
        print(f"\n---- {tag}   [{bd} Hz] ----")
        print(f"{'stratum':14s} {'build':10s} {'n':>4s} {'blk':>4s} | {'envelope e (counts)':>30s}")
        for nm, lo, hi in STRATA:
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

    # ---------------------------------------------------------------- S3 RATIOS -----------------
    hdr("S3  CROSS-BUILD RATIOS, cell-stratified on (speed x effort x |rate|) cells occupied by\n"
        "    BOTH routes, episode-resampled.  Every ratio carries its own null verdict.\n"
        "    🛑 V84/V83a IS THE PRE-REGISTERED S1 TEST.  Prediction: 0.40.")
    PAIRS = [("V84/r6d", "V83a/r68"), ("V84/r6d", "V81/r67"), ("V84/r6d", "V67/r47"),
             ("V84/r6d", "V68/r4e"), ("V84/r6d", "V76/r65"), ("V84/r6d", "V80/r66"),
             ("V83a/r68", "V81/r67"), ("V67/r47", "V81/r67")]
    OUT["ratios"] = {}
    for bd in BANDS:
        print(f"\n---- {bd} Hz ----")
        print(f"{'pair':20s} {'ratio':>8s} {'95% CI':>20s} {'cells':>6s} {'blkA':>5s} {'blkB':>5s}"
              f"   verdict-vs-null")
        for A, B in PAIRS:
            res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_" + bd, RNG, nboot=1500,
                                  min_ep=2, min_win=4)
            nlA, nlB = OUT["null"][bd][A], OUT["null"][bd][B]
            lo, hi = min(nlA[1], nlB[1]), max(nlA[2], nlB[2])
            out = "OUTSIDE null" if (res[0] < lo or res[0] > hi) else "inside null "
            ci = "CI excl 1" if (np.isfinite(res[1]) and (res[1] > 1 or res[2] < 1)) else "CI incl 1"
            print(f"{A.split('/')[0]+'/'+B.split('/')[0]:20s} {res[0]:8.3f} "
                  f"[{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d} {res[4]:5d} {res[5]:5d}   "
                  f"{out}; {ci}   null[{lo:.2f},{hi:.2f}]")
            OUT["ratios"].setdefault(bd, {})[f"{A}|{B}"] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3], null=[lo, hi],
                outside=bool(res[0] < lo or res[0] > hi))

    hdr("S3b  THE S1 TEST ITSELF -- CREEP ONLY (<10 km/h, engaged), 18-22 Hz, plus the other\n"
        "     bands in the same stratum.  This is the cell the pre-registration is about.")
    OUT["creep_ratio"] = {}
    for bd in BANDS:
        print(f"\n---- {bd} Hz, creep <10 km/h ----")
        for A, B in PAIRS:
            a = eng(R[A], A, lo0, hi0)
            b_ = eng(R[B], B, lo0, hi0)
            if len(a) < 8 or len(b_) < 8:
                print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  -- insufficient "
                      f"(nA={len(a)}, nB={len(b_)})")
                continue
            res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1500, min_ep=1, min_win=3)
            nA = OUT["null_creep"].get(bd, {}).get(A)
            nB = OUT["null_creep"].get(bd, {}).get(B)
            if nA and nB:
                nlo, nhi = min(nA[1], nB[1]), max(nA[2], nB[2])
                verdict = ("OUTSIDE null" if (res[0] < nlo or res[0] > nhi) else "inside null ")
                ns = f"null[{nlo:.2f},{nhi:.2f}]"
            else:
                verdict, ns = "null n/a    ", ""
            print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  {res[0]:7.3f} "
                  f"[{res[1]:7.3f},{res[2]:7.3f}]  cells={res[3]:2d}  blk {res[4]}/{res[5]}  "
                  f"{verdict} {ns}")
            OUT["creep_ratio"].setdefault(bd, {})[f"{A}|{B}"] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3])

    hdr("S3c  ABSOLUTE creep-stratum medians, against the pre-registered target e_18-22 ~ 109.")
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

    # ---------------------------------------------------------------- S5 IDENTITY ---------------
    hdr("S5  LINE IDENTITY -- f0 by a FREE 12-30 Hz prominence argmax, and its speed slope.\n"
        "    Wheel order 1 predicts d f0/d v = +0.481 Hz per m/s, order 2 +0.961.")
    OUT["identity"] = {}
    print(f"{'build':10s} {'n':>4s} | {'f0 12-30 Hz med [CI]':>28s} | {'sd':>5s} | "
          f"{'d f0/d v [CI]':>28s}")
    for b in LADDER:
        e = [r for r in eng(R[b], b) if np.isfinite(r["f_12-30"])]
        if len(e) < 10:
            print(f"{b:10s} {len(e):4d} |  -- too few --")
            continue
        f0 = G.boot_median_ci(e, "f_12-30", RNG, nboot=1500)
        sv = M.theil_sen_boot(e, "v", "f_12-30", RNG, nboot=800)
        print(f"{b:10s} {len(e):4d} | {f0[0]:8.3f} [{f0[1]:7.3f},{f0[2]:7.3f}] | "
              f"{float(np.std(G.col(e,'f_12-30'))):5.2f} | "
              f"{sv[0]:+8.4f} [{sv[1]:+7.4f},{sv[2]:+7.4f}]")
        OUT["identity"][b] = dict(f0=list(f0), slope_v=list(sv), n=len(e))

    print("\n  MEDIAN ENVELOPE amplitude (counts), all engaged windows:")
    print(f"{'build':10s} " + " ".join(f"{k:>10s}" for k in BANDS))
    OUT["medians"] = {}
    for b in LADDER:
        e = eng(R[b], b)
        print(f"{b:10s} " + " ".join(f"{np.nanmedian(G.col(e, 'e_' + k)):10.1f}" for k in BANDS))
        OUT["medians"][b] = {k: float(np.nanmedian(G.col(e, "e_" + k))) for k in BANDS}

    # ---------------------------------------------------------------- S6 DUTY -------------------
    hdr("S6  GRIND-#1 DUTY -- fraction of ENGAGED CREEP windows above a stated 18-22 Hz amplitude.")
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

    # ---------------------------------------------------------------- S7 VALIDITY ---------------
    hdr("S7  VALIDITY.  (a) 1-4 Hz driver-input matching -- must NOT differ once cells are matched;\n"
        "    a 1-4 Hz ratio far from 1 means the routes are not comparable at all.\n"
        "    (b) EPKEY sensitivity: the same ratios with the conservative whole-run unit.")
    for A, B in PAIRS[:4]:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_1-4", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"  1-4 Hz  {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  {res[0]:6.3f} "
              f"[{res[1]:6.3f}, {res[2]:6.3f}]  cells={res[3]}")
        OUT.setdefault("validity", {})[f"1-4|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "ep"
    print()
    for bd in ("6-9", "18-22", "40-49"):
        for A, B in PAIRS[:3]:
            res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_" + bd, RNG, nboot=1000,
                                  min_ep=2, min_win=4)
            print(f"  ep-key {bd:6s} {A.split('/')[0]:6s}/{B.split('/')[0]:6s}  {res[0]:6.3f} "
                  f"[{res[1]:6.3f}, {res[2]:6.3f}]  cells={res[3]}  runs {res[4]}/{res[5]}")
            OUT.setdefault("validity", {})[f"ep|{bd}|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "blk"

    hdr("S7c  MANUAL (DISENGAGED) CONTROL -- every symptom in this kit is LKAS-engaged-only, so the\n"
        "     manual arm of the SAME route is the within-drive isolator.  engaged/manual per band.")
    OUT["eng_vs_man"] = {}
    # 🛑 `_grind2_lib` puts the ENGAGEMENT FLAG in `cell[0]`, so an engaged and a manual window can
    # never share a cell and `boot_cellwise` returns NaN for every band.  The first cut of this
    # section did exactly that and printed a full table of NaN.  Re-key on (v, eff, rate) only.
    for b in LADDER:
        e, m_ = eng(R[b], b), man(R[b], b)
        for r in e + m_:
            r["cell"] = tuple(r["cell"])[1:]
        if len(m_) < 10:
            print(f"  {b:10s}  -- only {len(m_)} manual windows --")
            continue
        row = f"  {b:10s} nE={len(e):4d} nM={len(m_):4d} | "
        for bd in ("6-9", "18-22", "40-49", NEGCTRL):
            res = G.boot_cellwise(e, m_, "e_" + bd, RNG, nboot=1000, min_ep=1, min_win=3)
            row += f"{bd}: {res[0]:6.2f} [{res[1]:5.2f},{res[2]:5.2f}]  "
            OUT["eng_vs_man"].setdefault(b, {})[bd] = [res[0], res[1], res[2], res[3]]
        print(row)

    _dump("score_v84_bands.json")


def _add_imu2049(recs):
    """`imu2049` = the CHASSIS vertical 20-49 Hz envelope -- the ROAD-ROUGHNESS FALSIFIER.

    V80 read 1.07 [0.92, 1.33] here, which is what ruled out "V80 just drove a rougher road".
    Added in memory rather than in `augment3` so this section does not force a records rebuild.
    """
    by = {}
    for r in recs:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    for (build, seg), rs in by.items():
        B = G.BUILDS[build]
        p = B["cache"] / f"{B['pfx']}{seg}.npz"
        if not p.exists():
            continue
        d = C31.load(seg, B["cache"], B["pfx"])
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        n = G.NFFT
        taper = np.hanning(n) + 1e-3
        cw = slice(int(0.2 * n), int(0.8 * n))
        imu = np.asarray(d["imu_vert"], float) if "imu_vert" in d else None
        for r in rs:
            r["imu2049"] = np.nan
            if imu is None:
                continue
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            x = imu[i0:i0 + n]
            if len(x) == n and np.all(np.isfinite(x)):
                r["imu2049"] = G.win_env(x, fs, 20.0, 49.0, taper, cw)
    return recs


def hwy():
    """THE HIGHWAY RING on route 6d, scored exactly the way V80 and V81 were.

    The operator's V84 verdict included *"I did not notice any odd behavior at normal speed"* --
    a POSITIVE claim, and V84 is the first build in the lineage with NO engaged Coulomb damper in
    EITHER engaged column (V83a reverted mode 26 only and left mode 27 carrying V81's whole damper
    package).  🛑 A null here is only a result if the EXPOSURE supports it, so the exposure is
    printed first and the ratios afterwards -- the same order that made V80's creep numbers
    uninterpretable rather than reassuring.
    """
    G.EPKEY = "blk"
    R = build_records()
    for b in LADDER:
        _add_imu2049(R[b])
    F50, F80 = 50 * KMH, 80 * KMH

    hdr("H0  HIGHWAY EXPOSURE -- 🛑 FIRST, because 'no odd behaviour at normal speed' is only a\n"
        "    result if the drive actually visited that speed while engaged.")
    print(f"{'build':10s} {'eng >50 km/h':>16s} {'eng >80 km/h':>16s} {'blk50':>6s} {'blk80':>6s}")
    OUT["hwy_exposure"] = {}
    for b in LADDER:
        s50 = eng(R[b], b, F50, 1e9)
        s80 = eng(R[b], b, F80, 1e9)
        print(f"{b:10s} {len(s50) * 1.28:12.1f} s   {len(s80) * 1.28:12.1f} s   "
              f"{nunits(s50,'blk'):6d} {nunits(s80,'blk'):6d}")
        OUT["hwy_exposure"][b] = dict(sec50=len(s50) * 1.28, sec80=len(s80) * 1.28,
                                      n50=len(s50), n80=len(s80),
                                      blk50=nunits(s50, "blk"), blk80=nunits(s80, "blk"))

    hdr("H0b  SPEED CENSUS ABOVE 50 km/h -- 🛑 mandatory before any 6d-vs-67 / 6d-vs-68 highway\n"
        "     ratio.  Wheel order 1 = v/2.0805 Hz; at 90-110 km/h order 2 sits at 24-29 Hz, i.e.\n"
        "     INSIDE the 26-31 ring band, so a speed mismatch alone can manufacture a ring.")
    VB = [(13.9, 18.0), (18.0, 22.2), (22.2, 25.0), (25.0, 27.8), (27.8, 30.6), (30.6, 40.0)]
    print(f"{'build':10s} {'n>50':>5s} " + " ".join(f"{lo*3.6:.0f}-{hi*3.6:.0f}".rjust(9)
                                                    for lo, hi in VB)
          + f" | {'ord2 med':>9s} {'% ord2 in 26-31':>16s}")
    OUT["hwy_census"] = {}
    for b in LADDER:
        s = eng(R[b], b, F50, 1e9)
        if not s:
            print(f"{b:10s}     0  -- none --")
            continue
        v = G.col(s, "v")
        o2 = 2 * v / CIRC
        row = f"{b:10s} {len(s):5d} " + " ".join(
            f"{100 * ((v >= lo) & (v < hi)).mean():8.1f}%" for lo, hi in VB)
        f26 = float(np.mean((o2 >= 26.0) & (o2 <= 31.0)))
        print(row + f" | {np.median(o2):9.2f} {100 * f26:15.1f}%")
        OUT["hwy_census"][b] = dict(n=len(s), v_med=float(np.median(v)), ord2_med=float(np.median(o2)),
                                    ord2_in_ring=f26)

    hdr("H1  THE V80 CRITERION VERBATIM -- count and FRACTION of ENGAGED windows with a 26-31 Hz\n"
        "    envelope above 1000 counts.  On V80 that was 32 / 215 engaged windows.")
    OUT["ring_duty"] = {}
    for label, sel in (("ALL engaged", lambda r: True),
                       (">50 km/h engaged", lambda r: r["v"] >= F50),
                       (">80 km/h engaged", lambda r: r["v"] >= F80)):
        print(f"\n  ---- {label} ----")
        for b in LADDER:
            s = [r for r in eng(R[b], b) if sel(r)]
            if len(s) < 5:
                print(f"    {b:10s}  -- {len(s)} windows --")
                continue
            n1000 = sum(1 for r in s if np.isfinite(r["e_26-31"]) and r["e_26-31"] > 1000)
            f = M.frac_ci(s, "e_26-31", 1000.0, RNG, nboot=2000)
            print(f"    {b:10s} {n1000:3d}/{len(s):4d} = {100 * f[0]:5.1f}% "
                  f"[{100 * f[1]:5.1f},{100 * f[2]:5.1f}]  ({len(s) * 1.28:6.1f} s)   "
                  f"p95 {np.nanpercentile(G.col(s,'e_26-31'), 95):8.1f}  "
                  f"max {np.nanmax(G.col(s,'e_26-31')):8.1f}")
            OUT["ring_duty"].setdefault(label, {})[b] = dict(
                n=len(s), n1000=n1000, frac=list(f),
                p95=float(np.nanpercentile(G.col(s, "e_26-31"), 95)),
                max=float(np.nanmax(G.col(s, "e_26-31"))))

    hdr("H2  SPLIT-HALF NULL on the >50 km/h engaged pool (FIRST), then the ratios in the ring\n"
        "    band, the pre-declared 32-38 NEGATIVE CONTROL, and the IMU road-roughness falsifier.\n"
        "    🛑 If 26-31 and 32-38 move TOGETHER, the whole HF floor moved and there is no ring\n"
        "    result -- that is exactly what happened on V80 (2.017x at 40-49, 2.035x on 32-38).")
    HB = ["26-31", NEGCTRL, "18-22", "40-49", "6-9"]
    NL = {}
    pool = {b: eng(R[b], b, F50, 1e9) for b in LADDER}
    for bd in HB:
        for b in LADDER:
            if len(pool[b]) < 8:
                continue
            n = G.split_half_null(pool[b], "e_" + bd, RNG, nrep=300, min_ep=1, min_win=3)
            NL[(bd, b)] = n
            print(f"  {bd:8s} {b:10s} null {n[0]:7.3f} [{n[1]:7.3f}, {n[2]:7.3f}]  "
                  f"({len(pool[b])}w/{nunits(pool[b],'blk')}blk)")
        print()
    OUT["hwy_null"] = {f"{k[0]}|{k[1]}": list(v) for k, v in NL.items()}

    PAIRS = [("V84/r6d", "V81/r67"), ("V84/r6d", "V80/r66"), ("V84/r6d", "V76/r65"),
             ("V84/r6d", "V83a/r68"), ("V84/r6d", "V67/r47"), ("V80/r66", "V76/r65")]
    OUT["hwy_ratio"] = {}
    for bd in HB + ["imu2049"]:
        key = ("imu2049" if bd == "imu2049" else "e_" + bd)
        tag = ("🛑 IMU 20-49 Hz ROAD-ROUGHNESS FALSIFIER" if bd == "imu2049" else
               ("🛑 NEGATIVE CONTROL" if bd == NEGCTRL else bd + " Hz"))
        print(f"\n---- {tag}, engaged >50 km/h ----")
        for A, B in PAIRS:
            a, b_ = pool[A], pool[B]
            if len(a) < 6 or len(b_) < 6:
                print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} -- insufficient "
                      f"({len(a)}, {len(b_)})")
                continue
            res = G.boot_cellwise(a, b_, key, RNG, nboot=1500, min_ep=1, min_win=3)
            nA, nB = NL.get((bd, A)), NL.get((bd, B))
            if nA and nB and np.isfinite(nA[1]) and np.isfinite(nB[1]):
                nlo, nhi = min(nA[1], nB[1]), max(nA[2], nB[2])
                verd = "OUTSIDE null" if (res[0] < nlo or res[0] > nhi) else "inside null "
                ns = f"null[{nlo:.2f},{nhi:.2f}]"
            else:
                verd, ns = "null n/a   ", ""
            print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} {res[0]:7.3f} "
                  f"[{res[1]:7.3f},{res[2]:7.3f}] cells={res[3]:2d} blk {res[4]}/{res[5]}  "
                  f"{verd} {ns}")
            OUT["hwy_ratio"].setdefault(bd, {})[f"{A}|{B}"] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3])

    hdr("H3  PER-STRATUM ABSOLUTE 26-31 Hz ABOVE 50 km/h, and the IMU beside it in counts.")
    ST = [("50-80 km/h", F50, F80), (">80 km/h", F80, 1e9)]
    for nm, lo, hi in ST:
        print(f"\n  ---- {nm} ----")
        print(f"  {'build':10s} {'n':>4s} {'blk':>4s} | {'e_26-31 med [CI]':>28s} | "
              f"{'p95':>8s} {'max':>9s} | {'e_32-38':>8s} | {'imu2049':>8s}")
        for b in LADDER:
            s = eng(R[b], b, lo, hi)
            if len(s) < 5:
                print(f"  {b:10s} {len(s):4d}    - |  -- no sample --")
                continue
            ee = G.boot_median_ci(s, "e_26-31", RNG, nboot=1500)
            v = G.col(s, "e_26-31")
            print(f"  {b:10s} {len(s):4d} {nunits(s,'blk'):4d} | {ee[0]:8.1f} "
                  f"[{ee[1]:7.1f},{ee[2]:8.1f}] | {np.nanpercentile(v,95):8.1f} "
                  f"{np.nanmax(v):9.1f} | {np.nanmedian(G.col(s,'e_32-38')):8.1f} | "
                  f"{np.nanmedian(G.col(s,'imu2049')):8.3f}")
            OUT.setdefault("hwy_strat", {}).setdefault(nm, {})[b] = dict(
                n=len(s), e=list(ee), p95=float(np.nanpercentile(v, 95)),
                max=float(np.nanmax(v)), e3238=float(np.nanmedian(G.col(s, "e_32-38"))),
                imu=float(np.nanmedian(G.col(s, "imu2049"))))
    _dump("score_v84_hwy.json")


def engman():
    """The within-route engaged/manual contrast, and the spectra of V84's two grind-#2 events.

    🛑 THE ALIASING TRAP THIS SECTION EXISTS FOR.  fs ~ 100 Hz, so the SECOND HARMONIC of a
    26-31 Hz ring lands at 52-62 Hz and FOLDS to 38-48 Hz -- i.e. straight into the 40-49 Hz
    grind-#2 band.  A 40-49 Hz "event" that is accompanied by a large 26-31 Hz envelope is
    therefore a candidate ring harmonic, not necessarily grind #2.  The two are separated here by
    (a) the ratio e_26-31 / e_40-49 and (b) the free 30-49 Hz prominence argmax.
    """
    G.EPKEY = "blk"
    R = build_records()
    hdr("E1  ENGAGED vs MANUAL within the SAME route -- the within-drive isolator.  Every symptom\n"
        "    in this kit is claimed LKAS-engaged-only; this is that claim, per build, per band.\n"
        "    Cells re-keyed on (speed x effort x |rate|) WITHOUT the engagement flag.")
    OUT["eng_vs_man"] = {}
    for b in LADDER:
        e, m_ = eng(R[b], b), man(R[b], b)
        for r in e + m_:
            r["cell"] = tuple(r["cell"])[-3:]
        if len(m_) < 10:
            print(f"  {b:10s}  -- only {len(m_)} manual windows --")
            continue
        row = f"  {b:10s} nE={len(e):4d} nM={len(m_):4d} | "
        for bd in ("6-9", "18-22", "40-49", NEGCTRL):
            res = G.boot_cellwise(e, m_, "e_" + bd, RNG, nboot=1000, min_ep=1, min_win=3)
            row += f"{bd}: {res[0]:6.2f} [{res[1]:5.2f},{res[2]:6.2f}] c={res[3]}  "
            OUT["eng_vs_man"].setdefault(b, {})[bd] = [res[0], res[1], res[2], res[3]]
        print(row)

    hdr("E2  SPECTRUM OF V84's TWO GRIND-#2 EVENTS -- is the 40-49 Hz content its own line, or the\n"
        "    folded second harmonic of the 26-31 Hz ring?")
    import r67_v81_t4t5 as T45
    import r67_v81_t4f as T4F
    for b_, cfg in NEW.items():
        T45.ROUTES[b_] = (cfg["cache"], cfg["pfx"], cfg["segs"], cfg["parked"])
    b = "V84/r6d"
    hits = [r for r in eng(R[b], b) if np.isfinite(r["e_40-49"]) and r["e_40-49"] > G2_THR]
    OUT["g2_spec"] = []
    for grp in _merge(hits):
        pk = max(grp, key=lambda r: r["e_40-49"])
        cache, pfx, _, _ = T45.ROUTES[b]
        d = {k: v for k, v in np.load(cache / f"{pfx}{pk['seg']}.npz").items()}
        fs = C31.fs_of(d)
        i0 = int(np.argmin(np.abs(np.asarray(d["t"], float) - pk["t0"])))
        sp = T4F.event_spectrum(b, pk["seg"], i0, i0 + int(len(grp) * 1.28 * fs) + G.NFFT)
        f, P, Rm = sp["f"], sp["P"], sp["R"]
        top = []
        for lo, hi in ((5.0, 12.0), (18.0, 22.0), (26.0, 31.0), (32.0, 38.0), (40.0, 49.0)):
            f0, pr = G.locate(f, P, lo, hi, R=Rm)
            top.append((f"{lo:.0f}-{hi:.0f}", f0, pr))
        print(f"\n  seg{pk['seg']} t={pk['t0']:.1f}s  v={pk['v']:.2f} m/s  |ang|={pk['ang']:.1f} deg"
              f"  free 5-49 argmax f0={sp['f0']:.2f} Hz (prom {sp['prom']:.1f}, Q {sp['Q']:.1f})")
        print("    " + "   ".join(f"{nm}: {f0:5.2f} Hz p={pr:5.1f}" for nm, f0, pr in top))
        print(f"    e_26-31 = {pk['e_26-31']:7.1f}   e_40-49 = {pk['e_40-49']:7.1f}   "
              f"ratio 26-31/40-49 = {pk['e_26-31'] / max(pk['e_40-49'], 1e-9):5.2f}   "
              f"(2*f_26-31 folds to {2 * 100.5 - 2 * 27.9:.1f}..{100.5 - 2 * 27.9:.1f} Hz)")
        OUT["g2_spec"].append(dict(seg=int(pk["seg"]), t0=float(pk["t0"]), f0=float(sp["f0"]),
                                   Q=float(sp["Q"]), lines=[[nm, float(a), float(c)]
                                                            for nm, a, c in top],
                                   e26=pk["e_26-31"], e40=pk["e_40-49"]))
    _dump("score_v84_engman.json")


def creep535():
    """The S1 test ON THE CORPUS'S OWN CREEP RULER.

    🛑 RECORD ISSUE THIS SECTION EXISTS TO FIX.  The pre-registration names *"V67/V68's median
    `e_18-22` ~ 109, engaged creep"*.  That number was computed with `analyze_r47_grind1.CREEP =
    (0.3, 5.35)` m/s -- route 31's own max engaged speed, the kit's matching cap -- whereas
    `compare_v75_v76_v80_grind.STRATA[0]` is *"creep < 10 km/h"* = **< 2.78 m/s**.  The two rulers
    are NOT the same population, and scoring the prediction on the wrong one silently changes the
    target by a factor of several.  Both are printed here.
    """
    G.EPKEY = "blk"
    R = build_records()
    LO, HI = 0.3, 5.35
    hdr("C1  ENGAGED CREEP on the DOSE-TABLE RULER 0.3-5.35 m/s -- the population the pre-registered\n"
        "    target `e_18-22` ~ 109 was measured on.  Median [2.5%, 97.5%], episodes resampled.")
    print(f"{'build':10s} {'n':>4s} {'blk':>4s} {'v med':>6s} {'eff':>6s} {'rate':>6s} {'|ang|':>6s}"
          f" | " + " ".join(f"{bd:>24s}" for bd in ("6-9", "18-22", "40-49")))
    OUT["creep535"] = {}
    sel = {}
    for b in LADDER:
        s = [r for r in eng(R[b], b) if LO <= r["v"] <= HI]
        sel[b] = s
        if len(s) < 3:
            print(f"{b:10s} {len(s):4d}  -- too few --")
            continue
        cells = []
        for bd in ("6-9", "18-22", "40-49"):
            ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=1500)
            cells.append(f"{ee[0]:8.1f} [{ee[1]:6.1f},{ee[2]:7.1f}]")
            OUT["creep535"].setdefault(b, {})[bd] = list(ee)
        print(f"{b:10s} {len(s):4d} {nunits(s,'blk'):4d} {np.median(G.col(s,'v')):6.2f} "
              f"{np.median(G.col(s,'eff')):6.0f} {np.median(G.col(s,'rate')):6.1f} "
              f"{np.median(G.col(s,'ang')):6.1f} | " + " ".join(cells))
        OUT["creep535"][b]["n"] = len(s)
        OUT["creep535"][b]["blk"] = nunits(s, "blk")

    hdr("C2  SPLIT-HALF NULL on the same ruler (printed BEFORE the ratios), then the ratios.")
    NL = {}
    for bd in ("6-9", "18-22", "40-49", NEGCTRL):
        for b in LADDER:
            if len(sel[b]) < 8:
                continue
            n = G.split_half_null(sel[b], "e_" + bd, RNG, nrep=300, min_ep=1, min_win=3)
            NL[(bd, b)] = n
            print(f"  {bd:8s} {b:10s} null {n[0]:7.3f} [{n[1]:7.3f}, {n[2]:7.3f}]  "
                  f"({len(sel[b])}w/{nunits(sel[b],'blk')}blk)")
        print()
    PAIRS = [("V84/r6d", "V83a/r68"), ("V84/r6d", "V81/r67"), ("V84/r6d", "V67/r47"),
             ("V84/r6d", "V76/r65"), ("V83a/r68", "V81/r67")]
    OUT["creep535_ratio"] = {}
    for bd in ("6-9", "18-22", "40-49", NEGCTRL):
        print(f"\n---- {bd} Hz, engaged creep 0.3-5.35 m/s ----")
        for A, B in PAIRS:
            a, b_ = sel[A], sel[B]
            if len(a) < 6 or len(b_) < 6:
                print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} -- insufficient "
                      f"({len(a)}, {len(b_)})")
                continue
            res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1500, min_ep=1, min_win=3)
            nA, nB = NL.get((bd, A)), NL.get((bd, B))
            if nA and nB and np.isfinite(nA[1]) and np.isfinite(nB[1]):
                nlo, nhi = min(nA[1], nB[1]), max(nA[2], nB[2])
                verd = "OUTSIDE null" if (res[0] < nlo or res[0] > nhi) else "inside null "
                ns = f"null[{nlo:.2f},{nhi:.2f}]"
            else:
                verd, ns = "null n/a   ", ""
            print(f"  {A.split('/')[0]:6s}/{B.split('/')[0]:6s} {res[0]:7.3f} "
                  f"[{res[1]:7.3f},{res[2]:7.3f}] cells={res[3]:2d} blk {res[4]}/{res[5]}  "
                  f"{verd} {ns}")
            OUT["creep535_ratio"].setdefault(bd, {})[f"{A}|{B}"] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3])
    _dump("score_v84_creep535.json")


def _dump(name):
    def _san(o):
        try:
            return None if not np.isfinite(o) else float(o)
        except Exception:
            return str(o)
    CACHE6D.mkdir(exist_ok=True)
    (CACHE6D / name).write_text(json.dumps(OUT, indent=1, default=_san))
    print(f"\nwrote {CACHE6D / name}")


# =================================================================================================
#  GRIND #2 -- the event hunt, with the §7b exposure accounting that decides whether a low count
#  means anything at all.
# =================================================================================================
#  Scoring criterion FIXED IN ADVANCE by the corpus and restated in §7b of the V83a handoff:
#    1.28 s window spacing (NFFT 256 / hop 128), 40-49 Hz p99 analytic envelope > 500, ENGAGED,
#    0.3-4 m/s, |ang| >= 100 deg, merged into events.
#    "0 events in >= 166 s => Lever B does not produce grind #2 at P(0) <= 0.05."
G2_THR, G2_VLO, G2_VHI, G2_ANG = 500.0, 0.3, 4.0, 100.0
G2_FLOOR, G2_TARGET = 166.0, 255.0


def _route_global(build):
    """seg -> route-global start time, from the route-level extract when one exists."""
    cfg = NEW.get(build)
    if not cfg:
        return {}
    for p in cfg["cache"].glob("*.npz"):
        if p.name.startswith(cfg["pfx"]):
            continue
        d = np.load(p)
        if "seg_bounds" in d.files:
            return {int(s): float(a) for s, a, _ in d["seg_bounds"]}
    return {}


def grind2():
    G.EPKEY = "blk"
    R = build_records()
    hdr("G1  GRIND-#2 IN-REGIME EXPOSURE -- 🛑 THE NUMBER THAT DECIDES WHETHER A LOW EVENT COUNT\n"
        "    IS INTERPRETABLE.  Regime = engaged AND 0.3-4.0 m/s AND |angle| >= 100 deg.\n"
        "    §7b floor: >= 166 s for P(0) <= 0.05 against the V62/V65 burst rate; target 255 s.")
    print(f"{'build':10s} {'in-regime w':>12s} {'sec':>8s} {'blk':>5s}  {'vs 166 s floor':>16s}")
    OUT["g2_exposure"] = {}
    for b in LADDER:
        s = [r for r in eng(R[b], b) if G2_VLO <= r["v"] < G2_VHI and r["ang"] >= G2_ANG]
        sec = len(s) * 1.28
        flag = ("MEETS floor" if sec >= G2_FLOOR else
                f"{sec / G2_FLOOR:5.1%} of floor -- UNINTERPRETABLE")
        print(f"{b:10s} {len(s):12d} {sec:8.1f} {nunits(s,'blk'):5d}  {flag:>16s}")
        OUT["g2_exposure"][b] = dict(n=len(s), sec=sec, blk=nunits(s, "blk"),
                                     meets_floor=bool(sec >= G2_FLOOR))
    print("\n  A relaxed regime (engaged, 0.3-4 m/s, ANY angle) for context:")
    for b in LADDER:
        s = [r for r in eng(R[b], b) if G2_VLO <= r["v"] < G2_VHI]
        print(f"  {b:10s} {len(s):5d} w = {len(s) * 1.28:7.1f} s engaged creep at any angle")
        OUT["g2_exposure"][b]["creep_any_angle_sec"] = len(s) * 1.28

    hdr("G2  GRIND-#2 EVENTS -- e_40-49 > 500 ct, ENGAGED.  The strict §7b regime first, then the\n"
        "    SAME threshold with the speed/angle regime dropped, because the operator's two felt\n"
        "    instances were a LANE CHANGE and a CURVE -- neither is creep cornering.")
    OUT["g2_events"] = {}
    for label, sel in (("strict §7b regime (0.3-4 m/s, |ang|>=100)",
                        lambda r: G2_VLO <= r["v"] < G2_VHI and r["ang"] >= G2_ANG),
                       ("ANY speed, ANY angle, engaged", lambda r: True)):
        print(f"\n---- {label} ----")
        for b in LADDER:
            hits = [r for r in eng(R[b], b) if sel(r) and np.isfinite(r["e_40-49"])
                    and r["e_40-49"] > G2_THR]
            ev = _merge(hits)
            tot = len([r for r in eng(R[b], b) if sel(r)])
            print(f"  {b:10s} {len(hits):4d} hit-windows -> {len(ev):3d} events   "
                  f"({tot} windows = {tot * 1.28:.0f} s in regime)")
            OUT["g2_events"].setdefault(label, {})[b] = dict(nhit=len(hits), nev=len(ev),
                                                             nwin=tot)

    hdr("G3  V84's OWN GRIND-#2 EVENTS, one row each.  🛑 The operator felt TWO: one on a lane\n"
        "    change and one on a turn/curve.  IMU column = is the excess also in the CHASSIS?\n"
        "    (grind #1 is a torsional column mode and never reaches the IMU; grind #2 does,\n"
        "     coherence 0.82-0.88 on record.)")
    b = "V84/r6d"
    off = _route_global(b)
    hits = [r for r in eng(R[b], b) if np.isfinite(r["e_40-49"]) and r["e_40-49"] > G2_THR]
    ev = _merge(hits)
    base = np.nanmedian(G.col(eng(R[b], b), "e_40-49"))
    imu_base = np.nanmedian([r["imu40"] for r in eng(R[b], b) if np.isfinite(r.get("imu40", np.nan))]) \
        if any("imu40" in r for r in R[b]) else np.nan
    print(f"  route-median engaged e_40-49 = {base:.1f} ct;  threshold {G2_THR:.0f} ct "
          f"= {G2_THR / base:.1f}x the median")
    print(f"\n  {'#':>2s} {'seg':>3s} {'t_seg':>7s} {'t_route':>8s} {'dur':>5s} {'v m/s':>6s} "
          f"{'|ang|':>7s} {'rate':>6s} {'|cmd|':>7s} {'e40-49':>8s} {'e18-22':>8s} "
          f"{'imu40':>8s} {'imuX':>6s} {'lchg':>5s}")
    OUT["g2_v84"] = []
    for i, grp in enumerate(ev):
        pk = max(grp, key=lambda r: r["e_40-49"])
        t0 = pk["t0"]
        tg = off.get(pk["seg"], 0.0) + t0
        im = pk.get("imu40", np.nan)
        imx = (im / imu_base) if (np.isfinite(im) and np.isfinite(imu_base) and imu_base > 0) \
            else np.nan
        print(f"  {i+1:2d} {pk['seg']:3d} {t0:7.1f} {tg:8.1f} {len(grp)*1.28:5.1f} {pk['v']:6.2f} "
              f"{pk['ang']:7.1f} {pk['rate']:6.1f} {pk.get('e4', np.nan):7.0f} "
              f"{pk['e_40-49']:8.1f} {pk['e_18-22']:8.1f} {im:8.3f} {imx:6.2f} "
              f"{pk.get('lchg', np.nan):5.2f}")
        OUT["g2_v84"].append(dict(seg=int(pk["seg"]), t_seg=float(t0), t_route=float(tg),
                                  dur=len(grp) * 1.28, v=pk["v"], ang=pk["ang"], rate=pk["rate"],
                                  e4=float(pk.get("e4", np.nan)), e40=pk["e_40-49"],
                                  e18=pk["e_18-22"], imu40=float(im), imu_excess=float(imx)))
    if not ev:
        print("  -- NO window on route 6d exceeded 500 ct in 40-49 Hz while engaged --")

    hdr("G4  THE TOP 12 ENGAGED 40-49 Hz WINDOWS on V84 regardless of threshold -- so a NULL at\n"
        "    500 ct is reported with the actual maximum beside it, not as a bare zero.")
    e = sorted(eng(R[b], b), key=lambda r: -(r["e_40-49"] if np.isfinite(r["e_40-49"]) else -1))
    print(f"  {'seg':>3s} {'t_seg':>7s} {'t_route':>8s} {'v':>6s} {'|ang|':>7s} {'rate':>6s} "
          f"{'|cmd|':>7s} {'e40-49':>8s} {'e26-31':>8s} {'e18-22':>8s} {'imu40':>8s} {'lchg':>5s}")
    OUT["g2_top"] = []
    for r in e[:12]:
        tg = off.get(r["seg"], 0.0) + r["t0"]
        print(f"  {r['seg']:3d} {r['t0']:7.1f} {tg:8.1f} {r['v']:6.2f} {r['ang']:7.1f} "
              f"{r['rate']:6.1f} {r.get('e4', np.nan):7.0f} {r['e_40-49']:8.1f} "
              f"{r['e_26-31']:8.1f} {r['e_18-22']:8.1f} {r.get('imu40', np.nan):8.3f} "
              f"{r.get('lchg', np.nan):5.2f}")
        OUT["g2_top"].append(dict(seg=int(r["seg"]), t_seg=float(r["t0"]), t_route=float(tg),
                                  v=r["v"], ang=r["ang"], rate=r["rate"], e40=r["e_40-49"],
                                  e26=r["e_26-31"], e18=r["e_18-22"],
                                  imu40=float(r.get("imu40", np.nan)),
                                  lchg=float(r.get("lchg", np.nan))))

    hdr("G5  LANE-CHANGE WINDOWS on V84 (blinker up while engaged) vs engaged non-lane-change,\n"
        "    in every band.  The operator felt one of the two instances on a LANE CHANGE.")
    lc = [r for r in eng(R[b], b) if r.get("lchg", 0) > 0.5]
    nl = [r for r in eng(R[b], b) if not r.get("lchg", 0) > 0.5]
    print(f"  {len(lc)} lane-change windows ({len(lc)*1.28:.0f} s) vs {len(nl)} other")
    OUT["g2_lanechange"] = {}
    if len(lc) >= 8:
        for bd in BANDS:
            res = G.boot_cellwise(lc, nl, "e_" + bd, RNG, nboot=1200, min_ep=1, min_win=3)
            m1 = np.nanmedian(G.col(lc, "e_" + bd))
            m2 = np.nanmedian(G.col(nl, "e_" + bd))
            print(f"    {bd:8s} lc {m1:8.1f} / other {m2:8.1f} = raw {m1/max(m2,1e-9):5.2f}   "
                  f"cell-matched {res[0]:6.3f} [{res[1]:6.3f},{res[2]:6.3f}] cells={res[3]}")
            OUT["g2_lanechange"][bd] = dict(lc=float(m1), other=float(m2), ratio=res[0],
                                            lo=res[1], hi=res[2], cells=res[3])
    _dump("score_v84_grind2.json")


def _merge(hits, gap=2.0):
    """Merge threshold-crossing windows into EVENTS: same segment, t0 within `gap` seconds."""
    ev = []
    for r in sorted(hits, key=lambda x: (x["build"], x["seg"], x["t0"])):
        if ev and ev[-1][-1]["seg"] == r["seg"] and ev[-1][-1]["build"] == r["build"] \
                and r["t0"] - ev[-1][-1]["t0"] <= gap:
            ev[-1].append(r)
        else:
            ev.append([r])
    return ev


# =================================================================================================
#  THE RING -- 26-31 Hz at highway, and whether the 27.4-28.5 Hz limit cycle appears on V84.
# =================================================================================================
def ring():
    import r67_v81_t4t5 as T45
    import r67_v81_t4f as T4F
    for b, cfg in NEW.items():
        T45.ROUTES[b] = (cfg["cache"], cfg["pfx"], cfg["segs"], cfg["parked"])
    order = ["V76/r65", "V81/r67", "V80/r66", "V83a/r68", "V84/r6d"]

    hdr("R1  HIGHWAY BURST EVENTS -- smoothed 18-31 Hz torsion-bar envelope > 400 ct for >= 0.4 s.\n"
        "    `burst_events` / `event_spectrum` are `r67_v81_t4f`'s OWN functions, unmodified, so\n"
        "    V84's events are directly comparable with V81's 11.25 s / 27.75 Hz limit cycle.")
    OUT["ring"] = {}
    for b in order:
        try:
            ev = T4F.burst_events(b)
        except Exception as exc:                       # a cache that predates a field
            print(f"  {b:10s}  -- burst_events failed: {exc}")
            continue
        hw = [e for e in ev if e["v"] > 80 * KMH and e["lat"] > 0.5]
        print(f"\n  {b:10s} {len(ev):3d} bursts total, {len(hw):3d} at >80 km/h engaged")
        OUT["ring"][b] = []
        for e in sorted(hw, key=lambda x: -x["dur"])[:6]:
            sp = T4F.event_spectrum(b, e["seg"], e["i0"], e["i1"])
            f0 = sp["f0"] if sp else np.nan
            Q = sp["Q"] if sp else np.nan
            print(f"    seg{e['seg']:2d} t={e['t0']:7.1f}-{e['t1']:7.1f}s dur {e['dur']:5.2f}s  "
                  f"v {e['v'] * 3.6:5.1f} km/h  peak {e['peak']:7.1f} ct  f0 {f0:6.2f} Hz  "
                  f"Q {Q:5.1f}  lchg {e['lchg']:.0f}")
            OUT["ring"][b].append(dict(seg=int(e["seg"]), t0=e["t0"], t1=e["t1"], dur=e["dur"],
                                       v_kmh=e["v"] * 3.6, peak=e["peak"], f0=float(f0),
                                       Q=float(Q), lchg=float(e["lchg"])))
        if hw:
            longest = max(hw, key=lambda x: x["dur"])
            print(f"    => LONGEST {longest['dur']:.2f} s, peak {longest['peak']:.0f} ct")
        else:
            print("    => NO highway burst above 400 ct on this build")

    hdr("R2  26-31 Hz BAND at >80 km/h engaged -- the ring as a band statistic, so a build with no\n"
        "    discrete burst still gets a number.")
    G.EPKEY = "blk"
    R = build_records()
    lo, hi = 80 * KMH, 1e9
    print(f"{'build':10s} {'n':>4s} {'blk':>4s} | {'e_26-31 med [CI]':>28s} | "
          f"{'p95':>8s} {'max':>9s} | {'f0 12-30':>9s}")
    OUT["ring_band"] = {}
    for b in LADDER:
        s = eng(R[b], b, lo, hi)
        if len(s) < 5:
            print(f"{b:10s} {len(s):4d}    - |  -- no >80 km/h engaged sample --")
            continue
        ee = G.boot_median_ci(s, "e_26-31", RNG, nboot=1500)
        v = G.col(s, "e_26-31")
        f0 = np.nanmedian(G.col([r for r in s if np.isfinite(r["f_26-31"])], "f_26-31"))
        print(f"{b:10s} {len(s):4d} {nunits(s,'blk'):4d} | {ee[0]:8.1f} [{ee[1]:7.1f},{ee[2]:8.1f}]"
              f" | {np.nanpercentile(v,95):8.1f} {np.nanmax(v):9.1f} | {f0:9.2f}")
        OUT["ring_band"][b] = dict(n=len(s), e=list(ee), p95=float(np.nanpercentile(v, 95)),
                                   max=float(np.nanmax(v)), f0=float(f0))
    _dump("score_v84_ring.json")


# =================================================================================================
#  S4 -- IMPEDANCE.  V81's own T3 estimator, this route added to its route table.
# =================================================================================================
def imped():
    import r67_v81_t2t3 as T23
    for b, cfg in NEW.items():
        T23.ROUTES[b] = (cfg["cache"], cfg["pfx"], cfg["segs"], cfg["parked"])
    order = ["V81/r67", "V83a/r68", "V84/r6d"]
    D = {b: T23.gather(b) for b in order}

    hdr("S4  IMPEDANCE = |tq_lf| per deg/s of |rate_lf| -- how HEAVY the wheel is.  ENGAGED vs\n"
        "    MANUAL at MATCHED speed and |angle|.  Frames restricted to the driver actually\n"
        "    steering: |tq_lf| > 300 ct AND |rate_lf| >= 2 deg/s.  ratio > 1 = HEAVIER engaged.\n"
        "    🛑 V81 measured 1.471 [0.980, 1.812] at 10-40 km/h.  V84 deletes the Coulomb damper\n"
        "    => PRE-REGISTERED PREDICTION ~ 1.00 (structurally zero asymmetry).\n"
        "    Every rate is d/dt of the 3 Hz-lowpassed column angle -- the raw rate is dominated by\n"
        "    the oscillation itself and produced a 10x artefact the first time this was run.")
    ANG_BINS = [(0.0, 5.0), (5.0, 20.0), (20.0, 1e9)]
    OUT["s4"] = {}
    for b in order:
        d = D[b]
        act = (np.abs(d["tq_lf"]) > 300) & (np.abs(d["rate_lf"]) >= 2.0)
        imp = np.where(act, np.abs(d["tq_lf"]) / np.maximum(np.abs(d["rate_lf"]), 1e-9), np.nan)
        print(f"\n  ---- {b} ----   (sentinel frames dropped: {d['__sentinels__']})")
        print(f"     {'stratum':14s} {'|ang|':>8s} {'nE':>6s} {'nM':>6s} | {'eng':>7s} {'man':>7s}"
              f" | {'ratio [95% CI]':>24s} | {'split-half null':>18s} | verdict")
        for nm, lo, hi in T23.STRATA:
            for alo, ahi in ANG_BINS:
                base = act & (d["v"] >= lo) & (d["v"] < hi) & \
                    (np.abs(d["ang"]) >= alo) & (np.abs(d["ang"]) < ahi)
                me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
                if me.sum() < 200 or mm.sum() < 200:
                    continue
                rr = T23.ratio_boot(imp[me], d["ep"][me], imp[mm], d["ep"][mm])
                nl = T23.split_half(imp[me], d["ep"][me])
                v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (rr[0] < nl[1] or rr[0] > nl[2]))
                     else "inside null")
                tag = f"{alo:.0f}-{ahi:.0f}" if ahi < 1e8 else f">{alo:.0f}"
                print(f"     {nm:14s} {tag:>8s} {int(me.sum()):6d} {int(mm.sum()):6d} | "
                      f"{np.nanmedian(imp[me]):7.1f} {np.nanmedian(imp[mm]):7.1f} | "
                      f"{rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:6.3f}] | "
                      f"[{nl[1]:6.3f},{nl[2]:6.3f}] | {v}")
                OUT["s4"].setdefault(b, {})[f"{nm}|{tag}"] = dict(
                    ratio=list(rr), null=list(nl), nE=int(me.sum()), nM=int(mm.sum()),
                    eng=float(np.nanmedian(imp[me])), man=float(np.nanmedian(imp[mm])))

    hdr("S4b  ALL-|ANGLE| ROLL-UP, the form V81's 1.471 was quoted in: one number per speed\n"
        "     stratum, engaged vs manual, |angle| unrestricted.")
    OUT["s4b"] = {}
    print(f"     {'build':10s} {'stratum':14s} {'nE':>6s} {'nM':>6s} | {'eng':>7s} {'man':>7s} | "
          f"{'ratio [95% CI]':>24s} | {'null':>18s} | verdict")
    for b in order:
        d = D[b]
        act = (np.abs(d["tq_lf"]) > 300) & (np.abs(d["rate_lf"]) >= 2.0)
        imp = np.where(act, np.abs(d["tq_lf"]) / np.maximum(np.abs(d["rate_lf"]), 1e-9), np.nan)
        for nm, lo, hi in T23.STRATA:
            base = act & (d["v"] >= lo) & (d["v"] < hi)
            me, mm = base & (d["lat"] > 0.5), base & (d["lat"] <= 0.5)
            if me.sum() < 200 or mm.sum() < 200:
                print(f"     {b:10s} {nm:14s} {int(me.sum()):6d} {int(mm.sum()):6d} | "
                      f"-- too few --")
                continue
            rr = T23.ratio_boot(imp[me], d["ep"][me], imp[mm], d["ep"][mm])
            nl = T23.split_half(imp[me], d["ep"][me])
            v = ("OUTSIDE null" if (np.isfinite(nl[1]) and (rr[0] < nl[1] or rr[0] > nl[2]))
                 else "inside null")
            print(f"     {b:10s} {nm:14s} {int(me.sum()):6d} {int(mm.sum()):6d} | "
                  f"{np.nanmedian(imp[me]):7.1f} {np.nanmedian(imp[mm]):7.1f} | "
                  f"{rr[0]:7.3f} [{rr[1]:6.3f},{rr[2]:6.3f}] | "
                  f"[{nl[1]:6.3f},{nl[2]:6.3f}] | {v}")
            OUT["s4b"].setdefault(b, {})[nm] = dict(ratio=list(rr), null=list(nl),
                                                    nE=int(me.sum()), nM=int(mm.sum()),
                                                    eng=float(np.nanmedian(imp[me])),
                                                    man=float(np.nanmedian(imp[mm])))

    hdr("S4c  THE TWO FACTORS SEPARATELY -- is the driver pushing harder, or moving less, or both?")
    for b in order:
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
            OUT.setdefault("s4c", {})[f"{b}|{nm}"] = dict(tq=[te, tm], rate=[re, rm])
    _dump("score_v84_imped.json")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "records":
        r = build_records(rebuild="--rebuild" in sys.argv)
        for b in LADDER:
            print(f"  {b:10s} {len(r[b]):6d} windows, engaged {len(eng(r[b], b)):6d}")
    elif cmd == "grind2":
        grind2()
    elif cmd == "creep":
        creep535()
    elif cmd == "hwy":
        hwy()
    elif cmd == "engman":
        engman()
    elif cmd == "ring":
        ring()
    elif cmd == "imped":
        imped()
    elif cmd == "all":
        analyze()
        grind2()
        ring()
        imped()
    else:
        analyze()
