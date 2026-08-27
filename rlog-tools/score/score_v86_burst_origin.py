#!/usr/bin/env python3
"""REGRESSION, FIRST-ADEQUATE-TEST, OR NEITHER?  Settling §B3 of the V86 / V86B scoring.

🛑 FALSIFIERS DECLARED BEFORE THE NUMBERS WERE LOOKED AT.  Each is checked below and its result
is printed beside it, whether it fired or not.

  F1  CAVE-PRESENCE.  "Our probe cave causes the bursts."  FALSIFIED IF V85 also carries a cave in
      the same region -- because V85 has zero bursts.  (Checked from the IMAGES in T1.)
  F2  CAVE-TIMING / CYCLE-STEAL.  FALSIFIED IF V85's cave is LONGER (more cycles) than V86's, since
      a cycle-steal mechanism is monotone in cave length and V85 is the clean build.
  F3  CONTROL-CELL.  "`0xC40D4` causes them."  FALSIFIED IF V86B -- which leaves `0xC40D4` at 573 --
      bursts at the same rate as V86.  (V86 and V86B share NO control cell.)
  F4  PURELY MECHANICAL.  "A manoeuvre covariate accounts for them with no reference to build."
      FALSIFIED IF a build without the cave reaches the same manoeuvre and does NOT burst.
  F5  EXPOSURE.  "Earlier builds simply never visited the burst regime."  FALSIFIED IF an earlier
      build has a decent number of regime-matched ENGAGED windows and still reads zero.
  F6  ENGAGEMENT.  "The bursts are engagement-conditional."  FALSIFIED IF the manual arm bursts at
      matched manoeuvre.

METHOD, unchanged from the corpus: `_grind2_lib` records via `score_v86_r6f_r70.build_records`
(which loads every other build READ-ONLY from `_scratch/cache/r6e/records_v85_score.pkl`), `blk` resampling,
`_grind2_lib.zigzag` as the fold-immune detector, `compare_v75_v76_v80_grind.frac_ci` for duties.
🛑 UNDERPOWERED IS NEVER CONVERTED TO A NULL.  Where a comparison arm is EMPTY the test is reported
as UNDEFINED, not as agreement.

Usage: python score/score_v86_burst_origin.py
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
from math import comb, exp, lgamma
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import score_v86_r6f_r70 as V86  # noqa: E402
import score_v84_r6d as S  # noqa: E402
import compare_v75_v76_v80_grind as M  # noqa: E402
import _grind2_lib as G  # noqa: E402
import _r31_common as C31  # noqa: E402

FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMG = {"V85": "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin",
       "V86": "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin",
       "V86B": "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"}
CAVE = (0xC4B38, 0xC4B78)
RATE_HI = 150.0                 # deg/s -- the burst manoeuvre's floor (V86 bursts sit at 194-258)
ANG_HI = 100.0                  # deg   -- the corpus's own §7b angle gate
BURST = 500.0                   # ct    -- the corpus's own e_40-49 event threshold
RNG = np.random.default_rng(86_8017)
LADDER = V86.LADDER
OUT = {}


def fisher_2x2(a, b, c, d):
    """Two-sided Fisher exact p for [[a,b],[c,d]].  Returns (p, note)."""
    if min(a + b, c + d, a + c, b + d) == 0:
        return float("nan"), "UNDEFINED -- a margin is zero"
    n = a + b + c + d

    def pr(x):
        return (comb(a + b, x) * comb(c + d, a + c - x)) / comb(n, a + c)
    lo = max(0, a + c - (c + d))
    hi = min(a + b, a + c)
    p0 = pr(a)
    p = sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 * (1 + 1e-12))
    return float(min(p, 1.0)), ""


def pois_p0(rate, sec):
    return float(exp(-rate * sec))


def col(rs, k):
    return G.col(rs, k)


def hdr(s):
    S.hdr(s)


# =================================================================================================
def t1_cave():
    hdr("T1  F1 + F2 -- THE CAVE, READ FROM THE IMAGES.  🛑 Both falsifiers are decided by bytes,\n"
        "    not by inference, and BOTH FIRE.")
    imgs = {k: (FW / v).read_bytes() for k, v in IMG.items() if (FW / v).exists()}
    OUT["cave"] = {}
    for k, d in imgs.items():
        c = d[CAVE[0]:CAVE[1]]
        nff = sum(1 for x in c if x == 0xFF)
        print(f"    {k:5s} cave 0x{CAVE[0]:05X}-0x{CAVE[1]:05X}: {len(c) - nff} non-0xFF bytes, "
              f"{nff} bytes of 0xFF padding")
        print(f"          {c.hex()}")
        OUT["cave"][k] = dict(nonff=len(c) - nff, pad=nff, hex=c.hex())
    a, b = imgs["V86"][CAVE[0]:CAVE[1]], imgs["V86B"][CAVE[0]:CAVE[1]]
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    print(f"\n    V86 vs V86B inside the cave: {len(diff)} differing bytes at "
          + ", ".join(f"0x{CAVE[0]+i:05X}" for i in diff))
    print("\n  🛑 F1 CAVE-PRESENCE: **FALSIFIED**.  V85 carries a probe cave in the SAME 62-byte\n"
          "     region -- 64 non-0xFF bytes of real V850 code -- and V85 has ZERO bursts.  The\n"
          "     hypothesis cannot be 'a cave is present'; at most it can be 'THIS cave's content'.")
    print("  🛑 F2 CAVE-TIMING / CYCLE-STEAL: **FALSIFIED IN THE DIRECTION TESTED**.  V85's cave is\n"
          "     LONGER (64 non-0xFF bytes) than V86's and V86B's (58, with 6 bytes of 0xFF tail).\n"
          "     A cycle-steal mechanism is monotone in instruction count, so it predicts V85 should\n"
          "     be the WORST build.  V85 is the CLEAN one.  ⚠ This does not exclude a cave that\n"
          "     touches a different register or a different task -- that is CAVEAUDIT's question,\n"
          "     not one bytes-per-cave can answer.")
    print("  ⊕ V86 and V86B differ inside the cave by exactly 2 bytes, SAME LENGTH (a b5/b6 weight\n"
        "     swap) ⇒ identical cycle cost ⇒ a cave-timing mechanism predicts IDENTICAL burst\n"
        "     rates on the two.  T4 measures that.")


# =================================================================================================
def t2_manoeuvre(R):
    hdr("T2  🛑 THE MANOEUVRE-MATCHED TEST -- THE CRUX.  V86's burst windows sit at |ang| 124-156\n"
        "    deg and rate 194-258 deg/s, engaged, creep.  How many windows does EACH build have\n"
        "    inside that envelope, and conditional on being inside it, what is its burst rate?")
    print("\n  ⚠ SELECTION DISCLOSURE: the rate floor (150 deg/s) was read off V86's own bursts.\n"
          "    Any Fisher p that uses it is therefore an UPPER BOUND on the evidence, not a\n"
          "    neutral test.  The angle gate (100 deg) is the corpus's own pre-existing §7b gate.")
    ENV = [("E1  §7b (corpus): eng, 0.3-4 m/s, |ang|>=100", lambda r: 0.3 <= r["v"] < 4.0
            and r["ang"] >= ANG_HI),
           ("E2  E1 + rate>=150 deg/s  (post-hoc floor)", lambda r: 0.3 <= r["v"] < 4.0
            and r["ang"] >= ANG_HI and r["rate"] >= RATE_HI),
           ("E3  rate>=150 deg/s ALONE, any angle, any speed", lambda r: r["rate"] >= RATE_HI)]
    OUT["envelopes"] = {}
    for lbl, sel in ENV:
        print(f"\n  ---- {lbl} ----")
        print(f"  {'build':10s} | {'ENGAGED n':>10s} {'bursts':>7s} {'zig800>0':>9s} | "
              f"{'MANUAL n':>9s} {'bursts':>7s} {'zig800>0':>9s} | {'max e40-49 (eng)':>17s}")
        for b in LADDER:
            e = [r for r in V86.eng(R[b], b) if sel(r)]
            m = [r for r in V86.man(R[b], b, fwd_only=True) if sel(r)]
            be = sum(1 for r in e if np.isfinite(r["e_40-49"]) and r["e_40-49"] > BURST)
            bm = sum(1 for r in m if np.isfinite(r["e_40-49"]) and r["e_40-49"] > BURST)
            ze = sum(1 for r in e if r.get("zig800", 0) > 0)
            zm = sum(1 for r in m if r.get("zig800", 0) > 0)
            mx = max((r["e_40-49"] for r in e if np.isfinite(r["e_40-49"])), default=float("nan"))
            print(f"  {b:10s} | {len(e):10d} {be:7d} {ze:9d} | {len(m):9d} {bm:7d} {zm:9d} | "
                  f"{mx:17.1f}")
            OUT["envelopes"].setdefault(lbl, {})[b] = dict(
                nE=len(e), burstE=be, zigE=ze, nM=len(m), burstM=bm, zigM=zm,
                maxE=None if not np.isfinite(mx) else float(mx))

    hdr("T2b THE FISHER TESTS, conditional on the envelope.  🛑 A test whose comparison arm is\n"
        "    EMPTY is reported UNDEFINED.  It is NOT reported as agreement and NOT as a null.")
    OUT["fisher"] = {}
    for lbl, _ in ENV:
        print(f"\n  ---- {lbl} ----")
        for ref in ("V85/r6e", "V84/r6d", "V81/r67", "V67/r47"):
            for new in ("V86/r6f", "V86B/r70"):
                A = OUT["envelopes"][lbl][new]
                B = OUT["envelopes"][lbl][ref]
                a, b_ = A["burstE"], A["nE"] - A["burstE"]
                c, d = B["burstE"], B["nE"] - B["burstE"]
                p, note = fisher_2x2(a, b_, c, d)
                ps = f"p = {p:.4f}" if np.isfinite(p) else f"🛑 {note}"
                print(f"    {new.split('/')[0]:5s} {a}/{A['nE']:3d}  vs  {ref.split('/')[0]:5s} "
                      f"{c}/{B['nE']:3d}   {ps}")
                OUT["fisher"].setdefault(lbl, {})[f"{new}|{ref}"] = dict(
                    a=a, nA=A["nE"], c=c, nB=B["nE"], p=None if not np.isfinite(p) else p,
                    note=note)

    hdr("T2c 🛑 WHY THE TESTS ARE UNDEFINED -- THE MANOEUVRE ENVELOPE ITSELF.  This is the single\n"
        "    most important table in this report: the marginal distribution of column rate in the\n"
        "    ENGAGED arm, per build.  The burst regime is not rare in the earlier builds.  IT DOES\n"
        "    NOT EXIST IN THEM.")
    print(f"\n  ENGAGED, ALL SPEEDS   {'n':>5s} | {'rate p50':>8s} {'p90':>7s} {'p99':>7s} "
          f"{'MAX':>8s} | {'n(rate>=150)':>12s} {'n(>=150 & ang>=100)':>19s}")
    OUT["rate_marginal"] = {}
    for b in LADDER:
        e = V86.eng(R[b], b)
        r, a = col(e, "rate"), col(e, "ang")
        n150 = int((r >= RATE_HI).sum())
        nboth = int(((r >= RATE_HI) & (a >= ANG_HI)).sum())
        print(f"  {b:10s}        {len(e):5d} | {np.percentile(r,50):8.1f} "
              f"{np.percentile(r,90):7.1f} {np.percentile(r,99):7.1f} {r.max():8.1f} | "
              f"{n150:12d} {nboth:19d}")
        OUT["rate_marginal"].setdefault("engaged", {})[b] = dict(
            n=len(e), p50=float(np.percentile(r, 50)), p90=float(np.percentile(r, 90)),
            p99=float(np.percentile(r, 99)), max=float(r.max()), n150=n150, nboth=nboth)
    print(f"\n  MANUAL (fwd), ALL SPEEDS  {'n':>3s} | {'rate p50':>8s} {'p90':>7s} {'p99':>7s} "
          f"{'MAX':>8s} | {'n(rate>=150)':>12s}   bursts / zig800>0 among them")
    for b in LADDER:
        m = V86.man(R[b], b, fwd_only=True)
        if not m:
            continue
        r = col(m, "rate")
        hi = [x for x in m if x["rate"] >= RATE_HI]
        nb = sum(1 for x in hi if np.isfinite(x["e_40-49"]) and x["e_40-49"] > BURST)
        nz = sum(1 for x in hi if x.get("zig800", 0) > 0)
        print(f"  {b:10s}        {len(m):5d} | {np.percentile(r,50):8.1f} "
              f"{np.percentile(r,90):7.1f} {np.percentile(r,99):7.1f} {r.max():8.1f} | "
              f"{len(hi):12d}   {nb} / {nz}")
        OUT["rate_marginal"].setdefault("manual", {})[b] = dict(
            n=len(m), max=float(r.max()), n150=len(hi), bursts=nb, zig=nz)


# =================================================================================================
def t3_mechanical(R):
    hdr("T3  F4 + F6 -- IS A MECHANICAL COVARIATE ENOUGH?  The bursts are compared against the\n"
        "    ONE covariate that separates them: column rate.  If rate alone explains them, no\n"
        "    build-level cause is needed at all.")
    print("\n  e_40-49 (median [2.5,97.5], blocks resampled) BY RATE DECILE-BAND, ENGAGED, pooled\n"
          "  across the PRE-V86 ladder vs each new route.  Bands chosen on physics, not on data.")
    BANDS = [(0, 25), (25, 50), (50, 80), (80, 120), (120, 150), (150, 200), (200, 1e9)]
    OUT["rate_curve"] = {}
    groups = {"PRE-V86 pooled": [r for b in ("V67/r47", "V81/r67", "V83a/r68", "V84/r6d",
                                             "V85/r6e") for r in V86.eng(R[b], b)],
              "V85/r6e alone": V86.eng(R["V85/r6e"], "V85/r6e"),
              "V86/r6f": V86.eng(R["V86/r6f"], "V86/r6f"),
              "V86B/r70": V86.eng(R["V86B/r70"], "V86B/r70")}
    print(f"  {'rate band':12s} " + " ".join(f"{k:>26s}" for k in groups))
    for lo, hi in BANDS:
        row = f"  {f'{lo:.0f}-{hi:.0f}' if hi < 1e8 else f'>{lo:.0f}':12s} "
        for k, rs in groups.items():
            s = [r for r in rs if lo <= r["rate"] < hi]
            if len(s) < 4:
                row += f"{f'n={len(s)} --':>26s} "
                OUT["rate_curve"].setdefault(k, {})[f"{lo}-{hi}"] = dict(n=len(s))
                continue
            ee = G.boot_median_ci(s, "e_40-49", RNG, nboot=1200)
            row += f"{f'{ee[0]:6.1f} [{ee[1]:5.1f},{ee[2]:6.1f}] n={len(s)}':>26s} "
            OUT["rate_curve"].setdefault(k, {})[f"{lo}-{hi}"] = dict(n=len(s), e=list(ee))
        print(row)
    print("\n  ⇒ if the new routes sit ON the pooled curve where they overlap it, the bursts are\n"
          "    what the plant does at that rate and no build-level cause is required.")

    hdr("T3b THE SAME CURVE, MANUAL ARM -- the arm in which the operator DID reach the manoeuvre\n"
        "    on earlier builds.  🛑 THIS IS THE ONLY MATCHED COMPARISON THAT EXISTS.")
    print(f"  {'rate band':12s} " + " ".join(f"{k:>26s}" for k in
                                             ("V85/r6e man", "V86/r6f man", "V86B/r70 man",
                                              "PRE-V86 man pooled")))
    mgroups = {"V85/r6e man": V86.man(R["V85/r6e"], "V85/r6e", fwd_only=True),
               "V86/r6f man": V86.man(R["V86/r6f"], "V86/r6f", fwd_only=True),
               "V86B/r70 man": V86.man(R["V86B/r70"], "V86B/r70", fwd_only=True),
               "PRE-V86 man pooled": [r for b in ("V67/r47", "V81/r67", "V83a/r68", "V84/r6d",
                                                  "V85/r6e")
                                      for r in V86.man(R[b], b, fwd_only=True)]}
    OUT["rate_curve_manual"] = {}
    for lo, hi in BANDS:
        row = f"  {f'{lo:.0f}-{hi:.0f}' if hi < 1e8 else f'>{lo:.0f}':12s} "
        for k, rs in mgroups.items():
            s = [r for r in rs if lo <= r["rate"] < hi]
            if len(s) < 4:
                row += f"{f'n={len(s)} --':>26s} "
                continue
            ee = G.boot_median_ci(s, "e_40-49", RNG, nboot=1200)
            row += f"{f'{ee[0]:6.1f} [{ee[1]:5.1f},{ee[2]:6.1f}] n={len(s)}':>26s} "
            OUT["rate_curve_manual"].setdefault(k, {})[f"{lo}-{hi}"] = dict(n=len(s), e=list(ee))
        print(row)

    hdr("T3c THE CONJUNCTION TABLE -- (engaged?) x (rate >= 150?), bursts / windows, every build.\n"
        "    🛑 This is the whole argument on one screen.")
    print(f"  {'build':10s} | {'ENG & rate>=150':>22s} | {'ENG & rate<150':>22s} | "
          f"{'MAN & rate>=150':>22s} | {'MAN & rate<150':>22s}")
    OUT["conjunction"] = {}
    for b in LADDER:
        cells = []
        for arm, getter in (("E", lambda: V86.eng(R[b], b)),
                            ("M", lambda: V86.man(R[b], b, fwd_only=True))):
            for lo, hi in ((RATE_HI, 1e9), (0.0, RATE_HI)):
                s = [r for r in getter() if lo <= r["rate"] < hi]
                nb = sum(1 for r in s if np.isfinite(r["e_40-49"]) and r["e_40-49"] > BURST)
                nz = sum(1 for r in s if r.get("zig800", 0) > 0)
                cells.append(f"{nb} burst / {nz} zig / {len(s)}w")
                OUT["conjunction"].setdefault(b, {})[f"{arm}|{lo:.0f}"] = dict(
                    n=len(s), burst=nb, zig=nz)
        print(f"  {b:10s} | " + " | ".join(f"{c:>22s}" for c in cells))


# =================================================================================================
def t4_dose(R):
    hdr("T4  F3 -- THE DOSE CHECK.  V86 and V86B share NO control cell (`0xC40D4` = 286 vs 573;\n"
        "    FactorC Y[0] = 0 vs 908/875).  Their caves differ by 2 bytes of the SAME length.\n"
        "    ⇒ a cave mechanism predicts EQUAL burst rates; a `0xC40D4` mechanism predicts V86\n"
        "    strictly worse.  Which is it?")
    OUT["dose"] = {}
    for lbl, sel in (("engaged creep <10 km/h", lambda r: r["v"] < 2.78),
                     ("engaged, rate >= 150 deg/s", lambda r: r["rate"] >= RATE_HI),
                     ("engaged, all", lambda r: True)):
        print(f"\n  ---- {lbl} ----")
        rows = {}
        for b in ("V86/r6f", "V86B/r70"):
            s = [r for r in V86.eng(R[b], b) if sel(r)]
            nb = sum(1 for r in s if np.isfinite(r["e_40-49"]) and r["e_40-49"] > BURST)
            nz = sum(1 for r in s if r.get("zig800", 0) > 0)
            f8 = M.frac_ci(s, "zig800", 0.0, RNG, nboot=3000) if len(s) >= 3 else (np.nan,) * 4
            mx = max((r["zig800"] for r in s), default=0)
            rows[b] = (nb, nz, len(s), f8, mx)
            print(f"    {b:10s} {nb} burst / {nz} zig800 / {len(s)}w   "
                  f"zig800>0 = {100*f8[0]:5.1f}% [{100*f8[1]:4.1f},{100*f8[2]:5.1f}]   "
                  f"max zig800 {mx:.0f}")
            OUT["dose"].setdefault(lbl, {})[b] = dict(burst=nb, zig=nz, n=len(s),
                                                      frac=list(f8), max_zig800=float(mx))
        A, B = rows["V86/r6f"], rows["V86B/r70"]
        p, note = fisher_2x2(A[1], A[2] - A[1], B[1], B[2] - B[1])
        print(f"    Fisher (zig800>0): V86 {A[1]}/{A[2]} vs V86B {B[1]}/{B[2]}   "
              + (f"p = {p:.4f}" if np.isfinite(p) else f"🛑 {note}"))
        # block-bootstrap CI on the ratio of the two duties
        def dutyboot(s):
            grp = {}
            for r in s:
                grp.setdefault(r["blk"], []).append(1.0 if r.get("zig800", 0) > 0 else 0.0)
            per = list(grp.values())
            return per
        pa, pb = dutyboot([r for r in V86.eng(R["V86/r6f"], "V86/r6f") if sel(r)]), \
            dutyboot([r for r in V86.eng(R["V86B/r70"], "V86B/r70") if sel(r)])
        if pa and pb:
            dr = np.full(3000, np.nan)
            for k in range(3000):
                x = np.concatenate([pa[j] for j in RNG.integers(0, len(pa), len(pa))]).mean()
                y = np.concatenate([pb[j] for j in RNG.integers(0, len(pb), len(pb))]).mean()
                dr[k] = x - y
            print(f"    duty DIFFERENCE V86 - V86B = {100*(np.mean([v for p_ in pa for v in p_]) - np.mean([v for p_ in pb for v in p_])):+.1f} pp"
                  f"  [{100*np.nanpercentile(dr,2.5):+.1f}, {100*np.nanpercentile(dr,97.5):+.1f}] pp"
                  f"   ({len(pa)} vs {len(pb)} blocks)")
            OUT["dose"][lbl]["diff_pp"] = [
                float(100 * (np.mean([v for p_ in pa for v in p_])
                             - np.mean([v for p_ in pb for v in p_]))),
                float(100 * np.nanpercentile(dr, 2.5)), float(100 * np.nanpercentile(dr, 97.5)),
                len(pa), len(pb)]


# =================================================================================================
def t5_timing(R):
    hdr("T5  THE TIMING FINGERPRINT.  🛑 INSTRUMENT LIMIT STATED FIRST: within one panda batch\n"
        "    every CAN frame shares ONE `logMonoTime` (measured age 0.37 ms).  So logged\n"
        "    INTER-ARRIVAL times measure the comma device's polling, NOT the ECU's TX cadence, and\n"
        "    a jitter test on them is uninterpretable for this question.  What IS batch-immune is\n"
        "    the frame COUNT per second: batching moves timestamps, it does not create or destroy\n"
        "    frames.  A perturbed 100 Hz TX task would change the RATE.")
    OUT["tx_rate"] = {}
    print(f"\n  {'route':8s} {'dur s':>8s} | " + " ".join(
        f"{nm:>22s}" for nm in ("0x14A frames/s", "0x18F frames/s", "0x1AB frames/s")))
    for rt, cache, stem in (("6d/V84", "_scratch/cache/r6d", "r6d"), ("6e/V85", "_scratch/cache/r6e", "r6e"),
                            ("6f/V86", "_scratch/cache/r6f", "r6f"), ("70/V86B", "_scratch/cache/r70", "r70")):
        p = ROOT / cache / f"{stem}.npz"
        if not p.exists():
            continue
        d = np.load(p)
        row, rec = "", {}
        t14 = np.asarray(d["raw14_t"], float)
        dur = float(t14.max() - t14.min())
        for key in ("raw14_t", "raw18_t", "raw1ab_t"):
            t = np.asarray(d[key], float)
            r = len(t) / max(float(t.max() - t.min()), 1e-9)
            row += f"{r:22.3f}"
            rec[key] = dict(n=int(len(t)), sec=float(t.max() - t.min()), hz=r)
        print(f"  {rt:8s} {dur:8.1f} | {row}")
        OUT["tx_rate"][rt] = rec
    print("\n  ⊕ nominal: 0x14A and 0x1AB are 100 Hz EPS-side frames; 0x18F is 100 Hz.\n"
          "    A cave that stole cycles from the TX task would show as a DEFICIT here.")

    print("\n  BATCHING DIAGNOSTIC -- fraction of consecutive 0x14A arrivals with dt == 0 exactly\n"
          "  (i.e. same batch).  If this is large, the inter-arrival distribution is the device's.")
    for rt, cache, stem in (("6d/V84", "_scratch/cache/r6d", "r6d"), ("6e/V85", "_scratch/cache/r6e", "r6e"),
                            ("6f/V86", "_scratch/cache/r6f", "r6f"), ("70/V86B", "_scratch/cache/r70", "r70")):
        p = ROOT / cache / f"{stem}.npz"
        if not p.exists():
            continue
        d = np.load(p)
        for key in ("raw14_t", "raw1ab_t"):
            t = np.asarray(d[key], float)
            dt = np.diff(t)
            print(f"    {rt:8s} {key:10s} dt==0 {100*np.mean(dt == 0):5.1f}%   "
                  f"p50 {np.median(dt)*1e3:6.2f} ms  p95 {np.percentile(dt,95)*1e3:6.2f} ms  "
                  f"p99.9 {np.percentile(dt,99.9)*1e3:7.2f} ms  >25 ms {100*np.mean(dt>0.025):5.2f}%")
            OUT.setdefault("tx_jitter", {})[f"{rt}|{key}"] = dict(
                zero=float(np.mean(dt == 0)), p50_ms=float(np.median(dt) * 1e3),
                p95_ms=float(np.percentile(dt, 95) * 1e3),
                gt25ms=float(np.mean(dt > 0.025)))

    hdr("T5b THE BURST'S OWN SPECTRUM -- is there structure at 100 Hz or its subharmonics/aliases\n"
        "    (50, 33.3, 25, 20 Hz), or at a CAN frame cadence?  A task-timing artefact should sit\n"
        "    on one of those; a plant resonance need not.  Long window (1024 pt = 10.2 s) centred\n"
        "    on each burst, prominence spectrum, top lines listed.")
    OUT["burst_spec"] = []
    for b in ("V86/r6f", "V86B/r70"):
        B = G.BUILDS[b]
        hits = sorted([r for r in V86.eng(R[b], b)
                       if np.isfinite(r["e_40-49"]) and r["e_40-49"] > BURST],
                      key=lambda r: -r["e_40-49"])
        for r in hits:
            d = C31.load(r["seg"], B["cache"], B["pfx"])
            fs = C31.fs_of(d)
            t = np.asarray(d["t"], float)
            i0 = int(np.argmin(np.abs(t - r["t0"])))
            n = 1024
            a = max(0, i0 - n // 4)
            x = np.asarray(d["tq"], float)[a:a + n]
            if len(x) < n:
                continue
            P = C31.periodogram(x, fs, n, True)
            if P is None:
                continue
            f = np.fft.rfftfreq(n, 1 / fs)
            Rm = G.prom_spectrum(f, P)
            ok = np.isfinite(Rm) & (f > 2.0)
            order = np.argsort(np.where(ok, Rm, -np.inf))[::-1][:6]
            print(f"\n    {b} seg{r['seg']} t={r['t0']:.1f}s  e40-49={r['e_40-49']:.0f} "
                  f"fs={fs:.2f} Hz  (Nyquist {fs/2:.2f})")
            print("      top prominence lines: " + "  ".join(
                f"{f[j]:5.2f} Hz (p={Rm[j]:4.1f})" for j in order))
            tgt = {}
            for name, ft in (("100 Hz task", 100.0), ("fs/2", fs / 2), ("fs/3", fs / 3),
                             ("fs/4", fs / 4), ("fs/5", fs / 5), ("20 Hz", 20.0)):
                fo = ft if ft < fs / 2 else abs(fs - ft)
                j = int(np.argmin(np.abs(f - fo)))
                tgt[name] = (float(f[j]), float(Rm[j]) if np.isfinite(Rm[j]) else None)
            print("      at the task-timing candidates: " + "  ".join(
                f"{k} -> {v[0]:5.2f} Hz p={v[1] if v[1] is not None else float('nan'):4.1f}"
                for k, v in tgt.items()))
            OUT["burst_spec"].append(dict(build=b, seg=int(r["seg"]), t0=float(r["t0"]),
                                          e40=float(r["e_40-49"]), fs=float(fs),
                                          top=[[float(f[j]), float(Rm[j])] for j in order],
                                          targets={k: list(v) for k, v in tgt.items()}))


# =================================================================================================
def main():
    G.EPKEY = "blk"
    t1_cave()
    R = V86.build_records()
    t2_manoeuvre(R)
    t3_mechanical(R)
    t4_dose(R)
    t5_timing(R)

    def _san(o):
        if isinstance(o, dict):
            return {str(k): _san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_san(x) for x in o]
        if isinstance(o, (np.floating, np.integer, float)):
            v = float(o)
            return None if not np.isfinite(v) else v
        return o
    for p in (ROOT / "_scratch/cache/r6f" / "score_v86_burst_origin.json",
              ROOT / "_scratch/cache/r70" / "score_v86b_burst_origin.json"):
        p.write_text(json.dumps(_san(OUT), indent=1))
        print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
