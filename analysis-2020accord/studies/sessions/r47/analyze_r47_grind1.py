#!/usr/bin/env python3
"""V67 route `47` -- did the LKAS-GATED Kd=2 keep the grind #1 fix, and does the gate reproduce
the dose-response WITHIN one route?

V67 makes the rate-lane gain CONDITIONAL. The firmware's own LKAS gate `gp-0x6806` selects the arm:

    g6806 == 1  ->  cal 0xC6446 = 5244   ( = 2.00x the stock LERP at grind #1's operating point )
    g6806 == 0  ->  stock mode-10 LERP   ( Kd = 1 )

Every earlier dose comparison was BETWEEN routes, so it carried tyres, road, temperature and
alignment as confounds. Route 47 carries both doses inside one drive, which is why this route is
special -- and why its own confound has to be stated first:

  🛑 ON ROUTE 47 THE GATE IS LATERAL ENGAGEMENT. g6806 == carControl.latActive in 150,302 of
     150,327 frames (99.983%); the 25 disagreements are single-frame transition edges. So the
     within-route "dose A/B" is ALSO the LKAS engaged/disengaged contrast, and grind #1 is itself
     LKAS-gated (engaged/disengaged p99 6.63x on the Kd=1 record). The two effects are perfectly
     confounded and point in OPPOSITE directions. A raw within-route ratio therefore CANNOT
     attribute anything to Kd.
     ⇒ the within-route contrast is only interpretable as a DIFFERENCE IN DIFFERENCES against
     builds where Kd is the SAME in both arms (V59/V64 at Kd=1, V62/V65 at Kd=2). Those builds
     measure the pure LKAS-gating effect; V67 measures gating x dose. Section 3 does exactly that.

Sections
  S0  provenance and probe health -- byte4 payloads, arm ladder, gate-vs-latActive, ST==4, events
  S1  exposure: what each route actually visited, and the gate=1 / gate=0 covariate overlap
  S2  CROSS-ROUTE: V67 vs the Kd=1 pool and the Kd=2 pool, engaged creep, cell-stratified
      episode-clustered bootstrap of the 18-22 Hz analytic-envelope p99, every band reported,
      each ratio quoted against the split-half null of the same build with the same estimator.
      S2b replays V62's ORIGINAL headline estimator (band power, |v| 1-4, boot_ratio) unmodified.
  S3  WITHIN-ROUTE A/B + the difference-in-differences that makes it interpretable
  S4  ABSOLUTE PRESENCE -- is there a grind #1 line on V67 at all? prominence, pass fraction,
      peak frequency and its scatter, and absolute envelope amplitude in counts
  S5  the frequency law: is the ~20.9 Hz line still fixed?

Method rules (each has already retracted a claim in this kit):
  * bootstrap over EPISODES, never windows. Both episode definitions are run: "ep" (a whole
    contiguous engagement run, the conservative unit) and "blk" (~10.2 s nested block).
  * every ratio is printed beside the SPLIT-HALF NULL of a single build computed with the
    identical estimator. A ratio inside that spread is not a finding.
  * p99 of the analytic band envelope, never mean Welch power. MEAN and TAIL reported together.
  * engagement is carControl.latActive; on this route the firmware's g6806 is reported beside it.
  * a strict 18-22/18-26 band PRESENCE-tests a known line; it cannot LOCATE a shifted one, so the
    frequency work uses a free 12-30 Hz argmax of the PROMINENCE spectrum.

Usage:
    cd analysis-2020accord
    python studies/sessions/r47/analyze_r47_grind1.py            # everything (~2 min; records cached after first run)
    python studies/sessions/r47/analyze_r47_grind1.py s0 s3      # named sections only
    R47_FORCE=1 python studies/sessions/r47/analyze_r47_grind1.py    # rebuild the window-record cache
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
import os
import pickle
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:                                    # Windows consoles default to cp1252 and die on 🛑
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
from _r31_common import fs_of, load, runs_of, sustained  # noqa: E402
from route_build_registry import identify  # noqa: E402

RNG = np.random.default_rng(20260802)
RECS = ROOT / "_scratch/cache/r47" / "r47_grind1_records.pkl"
C47 = ROOT / "_scratch/cache/r47"
SEGS47 = list(range(26))

V67 = "V67/r47"
GATEKEY = "V67/r47@gate"          # same route, partitioned on the FIRMWARE gate instead of latActive
KD1 = ["V59/r2c", "V64/r35"]
KD2 = ["V62/r37", "V65/r3a", "V65/r3b"]
KD0 = ["V61/r31"]

CREEP = (0.3, 5.35)               # route 31's own max engaged speed -- the kit's matching cap
HEADLINE = "e_18-22"              # p99 analytic envelope of the grind #1 band
BANDORDER = ["1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49"]

# Coarse matched cells. G.V_BINS/E_BINS/R_BINS are tuned to the whole-route population; inside the
# creep arm they leave 12 cells holding 28 windows on V67, so no cell survives min_win. These are
# the same three covariates at a resolution the creep population can actually fill, applied
# IDENTICALLY to every build.
CV = [(0.0, 2.0), (2.0, 4.0), (4.0, 5.36)]              # speed, m/s
CE = [(0.0, 200.0), (200.0, 800.0), (800.0, 1e9)]       # sustained effort, counts
CR = [(0.0, 8.0), (8.0, 32.0), (32.0, 1e9)]             # |steer rate|, deg/s
CA = [(0.0, 15.0), (15.0, 90.0), (90.0, 1e9)]           # |steer angle|, deg


def bin3(x, bins):
    for i, (lo, hi) in enumerate(bins):
        if lo <= x < hi:
            return i
    return len(bins) - 1


def derive(rs):
    """Per-window BAND-SELECTIVITY keys: the grind #1 envelope divided by a control band's.

    🛑 Needed because the raw cross-route ratios move together across ALL bands -- V67's creep
    windows are broadly quieter than V59's, including in 1-4 Hz, which is pure driver input and
    cannot be a firmware effect. A common multiplicative offset (different road, different tyre
    state, different microphone-equivalent gain) divides out of these; a genuinely band-selective
    change does not.
    """
    for r in rs:
        for lab, ctl in (("sel2428", "e_24-28"), ("sel14", "e_1-4"), ("sel3040", "e_30-40")):
            r[lab] = r["e_18-22"] / r[ctl] if r[ctl] > 0 else np.nan
    return rs


def recell(rs, keys=("v", "eff", "rate")):
    """Copy records with `cell` replaced by the coarse creep cell over `keys`.

    Dropping `eng` from the cell is REQUIRED for the within-route A/B: G's cell leads with `eng`,
    so an engaged-vs-disengaged comparison would share zero cells and silently return NaN.
    """
    tbl = {"v": CV, "eff": CE, "rate": CR, "ang": CA}
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = tuple(bin3(r[k], tbl[k]) for k in keys)
        out.append(q)
    return out


# ------------------------------------------------------------------ record cache ----------------
def records():
    if RECS.exists() and not os.environ.get("R47_FORCE"):
        with open(RECS, "rb") as fh:
            st = pickle.load(fh)
        if all(b in st for b in G.ORDER) and GATEKEY in st and "e_30-40" in st[V67][0]:
            return st
    st = {b: G.wrecs(b) for b in G.ORDER}
    st[GATEKEY] = G.wrecs(V67, maskkey="g6806")
    with open(RECS, "wb") as fh:
        pickle.dump(st, fh)
    return st


def loaded():
    st = records()
    for v in st.values():
        derive(v)
    return st


def creep(rs, eng=1, vlo=CREEP[0], vhi=CREEP[1], effmax=None):
    out = [r for r in rs if r["eng"] == eng and vlo <= r["v"] <= vhi]
    if effmax is not None:
        out = [r for r in out if r["eff"] <= effmax]
    return out


def pool(st, builds, **kw):
    return [r for b in builds for r in creep(st[b], **kw)]


def nep(rs):
    return len({r[G.EPKEY] for r in rs})


def med(rs, key):
    v = G.col(rs, key)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if len(v) else np.nan


# ================================================================== S0 ==========================
def s0_provenance():
    G.hdr("S0.  PROVENANCE AND PROBE HEALTH -- route 47")
    cnt, st4, tot = Counter(), Counter(), 0
    arms, ill, void = Counter(), 0, 0
    dis = []
    for s in SEGS47:
        p = C47 / f"r47s{s}.npz"
        if not p.exists():
            continue
        d = load(s, C47, "r47s")
        tot += len(d["t"])
        cnt.update(d["probe"].astype(int).tolist())
        st4.update(d["sstat"].astype(int).tolist())
        arms.update(d["arm"].astype(int).tolist())
        ill += int(d["illegal"].sum())
        void += int((d["field"] == 0).sum())
        lat = d["cc_lat"] > 0.5
        g = d["g6806"] > 0.5
        if (lat != g).any():
            dis.append((s, int((g & ~lat).sum()), int((~g & lat).sum())))
    print(f"   frames {tot}   segments {len(SEGS47)}")
    print("   0x14A byte4 payloads: " + "  ".join(f"0x{k:02X}:{v} ({100 * v / tot:.2f}%)"
                                                  for k, v in sorted(cnt.items())))
    cands, notes = identify(list(cnt))
    print(f"   registry identify() -> {sorted(cands)}")
    for n in notes:
        print(f"      {n}")
    print("\n   ARM LADDER (0=stock LERP Kd1 | 1=V67 arm 0xC6446=5244 Kd2 | 2=mask 1024 | 3=2048):")
    print("      " + "  ".join(f"arm{k}:{v} ({100 * v / tot:.3f}%)" for k, v in sorted(arms.items())))
    print(f"   bit5 gp-0x671d (THE MASKING RISK, outranks the arm): "
          f"{arms.get(2, 0)} frames  -> {'CLEAR' if not arms.get(2) else '🛑 FIRED'}")
    print(f"   bit4 gp-0x671a (third arm): {arms.get(3, 0)} frames")
    print(f"   illegal (bit3 set or bit7 clear): {ill}   VOID (field==0): {void}")
    print(f"   ⇒ only two payloads exist, 0x87 and 0xC7, so the arm is a clean binary: "
          f"stock LERP vs 5244. Nothing masked it.")

    print("\n   STEER_STATUS (0x18F byte4 bits 7:4): "
          + "  ".join(f"ST={k}:{v}" for k, v in sorted(st4.items())))
    print(f"   *** ST==4 : {st4.get(4, 0)}"
          + ("   🛑 the V42 state-4 governor is back" if st4.get(4, 0) else "   (clean)"))

    print("\n   THE GATE vs openpilot's view of engagement:")
    print(f"      g6806 == cc_lat in {tot - sum(a + b for _, a, b in dis)}/{tot} frames "
          f"({100 * (tot - sum(a + b for _, a, b in dis)) / tot:.4f}%)")
    for s, a, b in dis:
        print(f"      seg{s}: g6806=1&lat=0 {a}   g6806=0&lat=1 {b}")
    print("   🛑 ⇒ THE FIRMWARE GATE IS LATERAL ENGAGEMENT. The within-route A/B in S3 is the")
    print("      LKAS engaged/disengaged contrast; it is NOT a randomised dose assignment.")

    ev = Counter()
    for s in SEGS47:
        p = C47 / f"r47s{s}_events.json"
        if p.exists():
            for e in json.loads(p.read_text()):
                ev[e["name"]] += 1
    watched = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
               "immediateDisable", "steerSaturated"]
    print("\n   watched onroadEvents: "
          + "  ".join(f"{f}={ev.get(f, 0)}" for f in watched))
    print("   all events: " + ", ".join(f"{k}={v}" for k, v in ev.most_common(12)))


# ================================================================== S1 ==========================
def s1_exposure(st):
    G.hdr("S1.  EXPOSURE -- what each route visited, and the gate=1 / gate=0 overlap on route 47")
    print("   Engaged creep is the population grind #1 lives in. 🛑 V67's is the THINNEST of any")
    print("   Kd>=1 route; every CI below inherits that.\n")
    print(f"   {'build':11s} {'dose':12s} {'win':>4s} {'ep':>3s} {'blk':>4s} {'v med':>6s} "
          f"{'eff med':>8s} {'rate med':>9s} {'ang med':>8s} {'e18-22 med':>11s}")
    for b in G.ORDER:
        r = creep(st[b])
        if not r:
            print(f"   {b:11s} (no engaged creep windows)")
            continue
        print(f"   {b:11s} {G.DOSE_LABEL[G.BUILDS[b]['kd']]:12s} {len(r):4d} "
              f"{len({x['ep'] for x in r}):3d} {len({x['blk'] for x in r}):4d} "
              f"{med(r, 'v'):6.2f} {med(r, 'eff'):8.0f} {med(r, 'rate'):9.1f} "
              f"{med(r, 'ang'):8.1f} {med(r, HEADLINE):11.1f}")

    print("\n   -- THE CONFOUND, quantified. Route 47 gate=1 vs gate=0 (partition on g6806) --")
    a1 = [r for r in st[GATEKEY] if r["eng"] == 1]
    a0 = [r for r in st[GATEKEY] if r["eng"] == 0]
    print(f"   {'population':26s} {'win':>5s} {'ep':>3s} {'blk':>4s} "
          + "".join(f"{q:>9s}" for q in ("v p10", "v med", "v p90", "eff med", "rate med",
                                         "ang med")))
    for lab, r in (("WHOLE ROUTE gate=1", a1), ("WHOLE ROUTE gate=0", a0),
                   ("CREEP 0.3-5.35 gate=1", creep(st[GATEKEY], 1)),
                   ("CREEP 0.3-5.35 gate=0", creep(st[GATEKEY], 0))):
        if not r:
            continue
        v = G.col(r, "v")
        print(f"   {lab:26s} {len(r):5d} {len({x['ep'] for x in r}):3d} "
              f"{len({x['blk'] for x in r}):4d} "
              f"{np.percentile(v, 10):9.2f}{np.median(v):9.2f}{np.percentile(v, 90):9.2f}"
              f"{med(r, 'eff'):9.0f}{med(r, 'rate'):9.1f}{med(r, 'ang'):9.1f}")
    print("   ⇒ gate=1 is HIGHWAY CRUISE, gate=0 is MANUAL MANOEUVRING. Un-matched, they are not")
    print("     the same driving. Everything in S3 is therefore run inside matched cells.")

    print("\n   -- matched-cell overlap on route 47, cells = (v, eff, rate) coarse bins --")
    for keys in (("v", "eff", "rate"), ("v", "eff", "rate", "ang")):
        c1 = Counter(r["cell"] for r in recell(creep(st[GATEKEY], 1), keys))
        c0 = Counter(r["cell"] for r in recell(creep(st[GATEKEY], 0), keys))
        sh = sorted(set(c1) & set(c0))
        n1 = sum(c1[c] for c in sh)
        n0 = sum(c0[c] for c in sh)
        print(f"   cells on {keys}: {len(sh)} shared of {len(set(c1) | set(c0))}   "
              f"windows inside shared cells: gate=1 {n1}/{sum(c1.values())} "
              f"({100 * n1 / max(sum(c1.values()), 1):.0f}%)  "
              f"gate=0 {n0}/{sum(c0.values())} ({100 * n0 / max(sum(c0.values()), 1):.0f}%)")
        for c in sh:
            print(f"       cell {c}   gate=1 {c1[c]:3d} win   gate=0 {c0[c]:3d} win")


# ================================================================== S2 ==========================
def _ratio_row(lab, ra, rb, key, min_ep, min_win, nboot=2000, want_tab=False):
    pt, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(ra, rb, key, RNG, nboot=nboot,
                                                     min_ep=min_ep, min_win=min_win)
    if not np.isfinite(pt):
        # 🛑 a bootstrap CI without a point estimate is not a result. Resamples occasionally find a
        # shared cell the real data does not have, so the interval prints while the estimate is
        # undefined. Suppress it rather than let a number stand in for an absent comparison.
        print(f"   {lab:34s}      --   NO SHARED CELL at min_ep={min_ep}, min_win={min_win}"
              f"   (ep {na}/{nb}, win {len(ra)}/{len(rb)})")
        return np.nan, np.nan, np.nan
    print(f"   {lab:34s} {pt:8.3f}  [{lo:7.3f}, {hi:7.3f}]  cells {nc:2d}  "
          f"ep {na:3d}/{nb:3d}  win {len(ra):4d}/{len(rb):4d}")
    if want_tab and tab:
        print(f"      {'cell':16s} {'nA':>4s} {'nB':>4s} {'epA':>4s} {'epB':>4s} "
              f"{'statA':>10s} {'statB':>10s} {'A/B':>8s} {'w':>6s}")
        for c, na_, nb_, nea, neb, sa, sb, rr, w in tab:
            print(f"      {str(c):16s} {na_:4d} {nb_:4d} {nea:4d} {neb:4d} "
                  f"{sa:10.2f} {sb:10.2f} {rr:8.3f} {w:6.2f}")
    return pt, lo, hi


def s2_cross_route(st):
    G.hdr("S2.  CROSS-ROUTE -- V67 vs the Kd=1 pool and the Kd=2 pool, ENGAGED CREEP")
    print("   Estimator: p99 analytic band envelope, cell-stratified (v, eff, rate) log-ratio,")
    print("   bootstrap over EPISODES. <1 = V67 quieter. Every ratio must be read against that")
    print("   build's OWN split-half null, printed underneath.\n")

    for epkey in ("ep", "blk"):
        G.EPKEY = epkey
        min_ep, min_win = (2, 3) if epkey == "ep" else (2, 4)
        print(f"   ================ episode unit = '{epkey}'  "
              f"(min_ep={min_ep}, min_win={min_win}) ================")
        v67 = recell(creep(st[V67]))
        p1 = recell(pool(st, KD1))
        p2 = recell(pool(st, KD2))
        p0 = recell(pool(st, KD0))
        for band in BANDORDER:
            key = "e_" + band
            tag = {"18-22": "  <== GRIND #1", "24-28": "  (pre-declared negative control)",
                   "1-4": "  (driver input -- matching validity check)",
                   "30-40": "  (was V62's control; on V65 it is part of grind #2)",
                   "40-49": "  (grind #2 core)"}.get(band, "")
            print(f"\n   ---- {band} Hz{tag} ----")
            _ratio_row("V67 / Kd=1 pool (V59+V64)", v67, p1, key, min_ep, min_win)
            _ratio_row("V67 / Kd=2 pool (V62+V65)", v67, p2, key, min_ep, min_win)
            _ratio_row("V67 / Kd=0 (V61)", v67, p0, key, min_ep, min_win)
            _ratio_row("Kd=2 pool / Kd=1 pool  [replicate]", p2, p1, key, min_ep, min_win)
            for lab, rs in (("V67/r47", v67), ("Kd=1 pool", p1), ("Kd=2 pool", p2)):
                n, nlo, nhi = G.split_half_null(rs, key, RNG, nrep=200,
                                                min_ep=min_ep, min_win=min_win)
                print(f"      split-half null inside {lab:12s} {n:7.3f}  "
                      f"[{nlo:7.3f}, {nhi:7.3f}]"
                      + ("   <- the noise floor for the rows above" if lab == "V67/r47" else ""))
        print()
    G.EPKEY = "ep"


def s2c_selectivity(st):
    G.hdr("S2c. BAND SELECTIVITY -- 18-22 Hz DIVIDED BY a control band, per window")
    print("   🛑 S2 shows every band moving together: V67/Kd=1 reads 0.44 in 1-4 Hz, which is the")
    print("   DRIVER'S OWN INPUT and cannot be a firmware effect. So part of the raw 18-22 Hz ratio")
    print("   is a broadband route offset. These rows divide it out inside each window. A firmware")
    print("   change that suppresses a MODE must survive here; a quieter route does not.\n")
    for epkey in ("ep", "blk"):
        G.EPKEY = epkey
        min_ep, min_win = (2, 3) if epkey == "ep" else (2, 4)
        print(f"   ---- episode unit '{epkey}' ----")
        v67 = recell(creep(st[V67]))
        p1 = recell(pool(st, KD1))
        p2 = recell(pool(st, KD2))
        for key, lab in (("sel2428", "18-22 / 24-28  (negative control)"),
                         ("sel14", "18-22 / 1-4    (driver input)"),
                         ("sel3040", "18-22 / 30-40  (grind #2 shoulder)")):
            print(f"\n   {lab}")
            _ratio_row("V67 / Kd=1 pool", v67, p1, key, min_ep, min_win)
            _ratio_row("V67 / Kd=2 pool", v67, p2, key, min_ep, min_win)
            _ratio_row("Kd=2 pool / Kd=1 pool", p2, p1, key, min_ep, min_win)
            n, nlo, nhi = G.split_half_null(v67, key, RNG, nrep=200,
                                            min_ep=min_ep, min_win=min_win)
            print(f"      split-half null inside V67/r47   {n:7.3f}  [{nlo:7.3f}, {nhi:7.3f}]")
        print()
    G.EPKEY = "ep"


def s2b_v62_headline(st):
    """Replay V62's ORIGINAL headline estimator, unmodified, with V67 added as a build."""
    G.hdr("S2b. V62's OWN HEADLINE ESTIMATOR, replayed with V67 added "
          "(band POWER, |v| 1-4, engaged)")
    print("   This is analyze_r37_v62_ci.boot_ratio / bp / arm imported unchanged -- the exact code")
    print("   that produced '0.124 [0.036, 0.387]'. Reported so V67 sits on the same ruler.\n")
    import analyze_r37_v62_creep as C62
    C62.BUILDS["V67 r47"] = dict(cache=C47, pfx="r47s", segs=SEGS47)
    import analyze_r37_v62_ci as CI
    order = ["V59 r2c", "V64 r35", "V61 r31", "V62 r37", "V67 r47"]
    for elab, eff in (("hands-off eff<=200", (0, 200)), ("UNGATED", None)):
        print(f"   ---- {elab}, |v| 1-4 m/s, engaged ----")
        arms = {b: CI.A(b, vsel=(1.0, 4.0), eff=eff) for b in order}
        for band, blab in ((CI.G1822, "18-22 Hz"), (CI.G1826, "18-26 Hz"), ((30.0, 40.0),
                                                                           "30-40 Hz")):
            print(f"     {blab}")
            for b in order:
                r = arms[b]
                if not r:
                    print(f"       {b:9s}  ep=0")
                    continue
                p, lo, hi = CI.boot_median(r, CI.bp(*band))
                print(f"       {b:9s} ep={len(CI.episodes(r)):3d} win={len(r):3d}  "
                      f"median power {p:10.4g}  [95% CI {lo:10.4g}, {hi:10.4g}]")
            for num in ("V62 r37", "V67 r47"):
                for ctl in ("V59 r2c", "V64 r35"):
                    if not arms[num] or not arms[ctl]:
                        continue
                    rr, rlo, rhi = CI.boot_ratio(arms[num], arms[ctl], CI.bp(*band))
                    print(f"       {num.split()[0]}/{ctl.split()[0]}  ratio {rr:8.4f}x  "
                          f"[{rlo:.4f}, {rhi:.4f}]  => {1 / rr if rr else np.nan:7.2f}x reduction")
            print()
        print()


# ================================================================== S3 ==========================
def _strat(ra, rb, key, min_ep, min_win):
    return G.boot_cellwise(ra, rb, key, RNG, nboot=0, min_ep=min_ep, min_win=min_win)[0]


def _did(pairs, key, min_ep, min_win, nboot=2000):
    """DiD over two (arm1, arm0) pairs: (A1/A0) / (B1/B0), resampling episodes in all four pools."""
    E = [G.episodes(x) for p in pairs for x in p]

    def pt(e):
        f = [[r for ep in x for r in ep] for x in e]
        a = _strat(f[0], f[1], key, min_ep, min_win)
        b = _strat(f[2], f[3], key, min_ep, min_win)
        if not (np.isfinite(a) and np.isfinite(b)) or b <= 0:
            return np.nan
        return a / b
    point = pt(E)
    draws = np.full(nboot, np.nan)
    for k in range(nboot):
        draws[k] = pt([[e[i] for i in RNG.integers(0, len(e), len(e))] for e in E])
    ok = np.isfinite(draws)
    if not ok.any():
        return point, np.nan, np.nan
    return point, float(np.nanpercentile(draws, 2.5)), float(np.nanpercentile(draws, 97.5))


def s3_within_route(st):
    G.hdr("S3.  ★ WITHIN-ROUTE A/B -- g6806==1 (Kd=2) vs g6806==0 (Kd=1) inside route 47 alone")
    print("   🛑 READ S0/S1 FIRST. The gate IS lateral engagement here (99.983% identical), so this")
    print("   contrast confounds the Kd dose with the LKAS-gating of grind #1, and the two act in")
    print("   OPPOSITE directions. The raw ratio is reported because it was asked for; the")
    print("   DIFFERENCE IN DIFFERENCES at the end is the only part that isolates the dose.\n")

    print("   🛑 CELL THRESHOLDS ARE RELAXED HERE to min_ep=1, min_win=2. The gate=0 creep arm is")
    print("   three engagement runs; at the cross-route thresholds NO cell survives and the section")
    print("   returns nothing. Relaxed thresholds buy cells at the cost of noisier per-cell medians,")
    print("   so the split-half null underneath is computed at the SAME thresholds.\n")
    for epkey in ("ep", "blk"):
        G.EPKEY = epkey
        min_ep, min_win = 1, 2
        print(f"   ================ episode unit = '{epkey}' ================")
        for keys in (("v", "eff", "rate"), ("v", "eff", "rate", "ang")):
            a1 = recell(creep(st[GATEKEY], 1), keys)
            a0 = recell(creep(st[GATEKEY], 0), keys)
            print(f"\n   ---- matched on {keys}, creep 0.3-5.35 m/s ----")
            print(f"   {'band':34s} {'gate1/gate0':>8s}  {'[95% CI]':>18s}  cells  ep      win")
            for band in BANDORDER:
                _ratio_row(f"{band} Hz", a1, a0, "e_" + band, min_ep, min_win,
                           want_tab=(band == "18-22" and keys == ("v", "eff", "rate")))
            for lab, rs in (("gate=1 arm", a1), ("gate=0 arm", a0)):
                n, nlo, nhi = G.split_half_null(rs, HEADLINE, RNG, nrep=200,
                                                min_ep=min_ep, min_win=min_win)
                print(f"      split-half null (18-22) inside {lab:12s} {n:7.3f} "
                      f"[{nlo:7.3f}, {nhi:7.3f}]")
            obs, p = G.perm_p(a1, a0, HEADLINE, RNG, nperm=600,
                              min_ep=min_ep, min_win=min_win)
            print(f"      permutation p (18-22, episode labels shuffled): obs {obs:.3f}  p={p:.4f}")
        print()
    G.EPKEY = "ep"

    # ---------------- the interpretable part ----------------------------------------------------
    G.hdr("S3b. DIFFERENCE IN DIFFERENCES -- the only construction that isolates the DOSE")
    print("   On a build where Kd is the SAME in both arms, engaged/disengaged measures the pure")
    print("   LKAS-gating of grind #1. On V67 it measures gating x dose. So")
    print("       DiD = (V67 eng/dis) / (control eng/dis)")
    print("   is the dose effect with the gating divided out, and with route, tyres, road and")
    print("   temperature differencing out INSIDE each build. DiD < 1 => the gated Kd=2 arm is")
    print("   quieter than a Kd=1 arm would have been under the same engagement.\n")
    print("   ⚠ The two control pools do NOT give the same DiD, and that is itself informative:")
    print("   their own engaged/disengaged contrasts differ (Kd=1 pool 8.8x, Kd=2 pool 2.6x), which")
    print("   means the Kd effect is not additive across the arms -- it is an INTERACTION, exactly")
    print("   what an LKAS-driven closed-loop mode predicts. Read the two DiDs as different")
    print("   quantities: vs Kd=1 = the dose effect in the ENGAGED arm; vs Kd=2 = the dose effect")
    print("   in the DISENGAGED arm (V67 reverts that arm to stock, the Kd=2 pool does not).\n")
    for epkey in ("ep", "blk"):
        G.EPKEY = epkey
        min_ep, min_win = 1, 2
        print(f"   ---- episode unit '{epkey}' (min_ep={min_ep}, min_win={min_win}) ----")
        v1 = recell(creep(st[GATEKEY], 1))
        v0 = recell(creep(st[GATEKEY], 0))
        print(f"   {'contrast':40s} {'ratio':>8s}  {'[95% CI]':>20s}")
        for lab, blds in (("Kd=1 pool (V59+V64)", KD1), ("Kd=2 pool (V62+V65)", KD2),
                          ("V59/r2c alone", ["V59/r2c"]), ("V62/r37 alone", ["V62/r37"]),
                          ("V65/r3b alone", ["V65/r3b"])):
            c1 = recell(pool(st, blds, eng=1))
            c0 = recell(pool(st, blds, eng=0))
            r67 = _strat(v1, v0, HEADLINE, min_ep, min_win)
            rc = _strat(c1, c0, HEADLINE, min_ep, min_win)
            d, dlo, dhi = _did([(v1, v0), (c1, c0)], HEADLINE, min_ep, min_win, nboot=1200)
            print(f"   V67 eng/dis {r67:7.3f}  /  {lab:24s} {rc:7.3f}  =>  DiD {d:7.3f}  "
                  f"[{dlo:7.3f}, {dhi:7.3f}]")
        print()
    G.EPKEY = "ep"


def s3c_arm_matched(st):
    G.hdr("S3c. ★★ THE ARM-MATCHED 2x2 -- the cleanest reading of the gated dose")
    print("   V67 runs Kd=2 in the ENGAGED arm and STOCK Kd=1 in the DISENGAGED arm. So the")
    print("   disengaged arm is a BUILT-IN PLACEBO: on that population V67 and the Kd=1 routes are")
    print("   running the same firmware, and any difference between them is pure route/exposure.")
    print("   That converts the confounded within-route contrast into two clean comparisons:\n")
    print("     (a) V67 engaged  vs Kd=1 engaged      -- Kd=2 vs Kd=1 : THE FIX")
    print("     (b) V67 engaged  vs Kd=2 engaged      -- Kd=2 vs Kd=2 : should be ~1")
    print("     (c) V67 disengaged vs Kd=1 disengaged -- Kd=1 vs Kd=1 : THE PLACEBO, must be ~1")
    print("     (d) V67 disengaged vs Kd=2 disengaged -- Kd=1 vs Kd=2 : the dose in manual\n")
    print("   🛑 If (c) lands where (a) does, route 47 is simply a quieter drive and (a) proves")
    print("   nothing. (c) is the load-bearing row of this whole report.\n")
    for epkey in ("ep", "blk"):
        G.EPKEY = epkey
        min_ep, min_win = 1, 2
        print(f"   ================ episode unit '{epkey}' (min_ep={min_ep}, min_win={min_win}) "
              f"================")
        for key, klab in ((HEADLINE, "18-22 Hz envelope p99"),
                          ("sel3040", "18-22 / 30-40 (band-selective)"),
                          ("sel2428", "18-22 / 24-28 (band-selective)"),
                          ("e_1-4", "1-4 Hz (driver input control)")):
            print(f"\n   ---- {klab} ----")
            for lab, eng, ctl in (("(a) V67 ENG / Kd=1 ENG   [Kd2 vs Kd1  = THE FIX]", 1, KD1),
                                  ("(b) V67 ENG / Kd=2 ENG   [Kd2 vs Kd2  ~ 1?]", 1, KD2),
                                  ("(c) V67 DIS / Kd=1 DIS   [Kd1 vs Kd1  = PLACEBO]", 0, KD1),
                                  ("(d) V67 DIS / Kd=2 DIS   [Kd1 vs Kd2]", 0, KD2)):
                a = recell(creep(st[GATEKEY], eng))
                b = recell(pool(st, ctl, eng=eng))
                _ratio_row(lab, a, b, key, min_ep, min_win)
            # (a)/(c) is the DiD done the RIGHT way round: each arm is matched to the SAME control
            # arm first, so cells are shared between routes rather than between engagement states,
            # and the route offset that (c) measures is divided straight out of (a).
            for clab, ctl in (("Kd=1 pool", KD1), ("Kd=2 pool", KD2)):
                d, dlo, dhi = _did([(recell(creep(st[GATEKEY], 1)), recell(pool(st, ctl, eng=1))),
                                    (recell(creep(st[GATEKEY], 0)), recell(pool(st, ctl, eng=0)))],
                                   key, min_ep, min_win, nboot=1200)
                print(f"   {'   => DiD = (V67 ENG/ctl ENG) / (V67 DIS/ctl DIS) vs ' + clab:56s}"
                      f"{d:8.3f}  [{dlo:7.3f}, {dhi:7.3f}]")
        print()
    G.EPKEY = "ep"


# ================================================================== S4 ==========================
def s4_presence(st):
    G.hdr("S4.  ABSOLUTE PRESENCE -- does a grind #1 line EXIST on V67 at all?")
    print("   Prominence = peak power / its own local +/-6 Hz median floor, so a driver cranking")
    print("   the wheel (broadband) cannot pass. Reported in the strict 18-26 Hz band, with the")
    print("   free 12-30 Hz locate beside it, plus ABSOLUTE envelope amplitude in counts.")
    print("   MEAN and TAIL together: median and p90 of every column.\n")
    for lab, kw in (("engaged creep 0.3-5.35", dict(eng=1)),
                    ("engaged creep, hands-off eff<=200", dict(eng=1, effmax=200)),
                    ("engaged 1-4 m/s", dict(eng=1, vlo=1.0, vhi=4.0)),
                    ("MANUAL creep 0.3-5.35", dict(eng=0))):
        print(f"   ---- {lab} ----")
        print(f"   {'build':11s} {'dose':12s} {'win':>4s} {'ep':>3s} "
              f"{'prom18-26 med':>13s} {'p90':>8s} {'pres>=10x':>10s} {'pres>=20x':>10s} "
              f"{'f0(18-26)':>10s} {'sd':>5s} {'f0(12-30)':>10s} {'sd':>5s} "
              f"{'env18-22 med':>12s} {'p90':>9s}")
        for b in G.ORDER:
            r = creep(st[b], **kw)
            if len(r) < 3:
                print(f"   {b:11s} {G.DOSE_LABEL[G.BUILDS[b]['kd']]:12s} {len(r):4d}  -- too few")
                continue
            pr = G.col(r, "p_18-26")
            ok = np.isfinite(pr)
            f26 = G.col(r, "f_18-26")
            f30 = G.col(r, "f_12-30")
            en = G.col(r, HEADLINE)
            print(f"   {b:11s} {G.DOSE_LABEL[G.BUILDS[b]['kd']]:12s} {len(r):4d} "
                  f"{len({x['ep'] for x in r}):3d} "
                  f"{np.nanmedian(pr):13.1f} {np.nanpercentile(pr, 90):8.1f} "
                  f"{100 * np.mean(pr[ok] >= 10):9.1f}% {100 * np.mean(pr[ok] >= 20):9.1f}% "
                  f"{np.nanmedian(f26):10.2f} {np.nanstd(f26, ddof=1):5.2f} "
                  f"{np.nanmedian(f30):10.2f} {np.nanstd(f30, ddof=1):5.2f} "
                  f"{np.nanmedian(en):12.1f} {np.nanpercentile(en, 90):9.1f}")
        print()

    print("   -- ABSOLUTE 18-22 Hz envelope p99, engaged creep, with episode-bootstrap CI --")
    print("      (counts on the torsion-bar channel; this is amplitude A, peak-to-peak is 2A)")
    for b in G.ORDER:
        r = creep(st[b])
        if len(r) < 3:
            continue
        p, lo, hi = G.boot_median_ci(r, HEADLINE, RNG, nboot=2000)
        pm, plo, phi = G.boot_median_ci(r, HEADLINE, RNG, nboot=2000, agg=np.mean)
        print(f"      {b:11s} median {p:8.1f} [{lo:8.1f}, {hi:8.1f}]   "
              f"mean {pm:8.1f} [{plo:8.1f}, {phi:8.1f}]   n={len(r)}")


# ================================================================== S5 ==========================
def s5_frequency(st):
    G.hdr("S5.  IS THE ~20.9 Hz LINE STILL FIXED?  free 12-30 Hz locate, engaged")
    print("   The law f = 0.177*v + 20.48 has been rejected twice; a=0 fits. Tested again on V67.")
    print("   Only windows whose 12-30 Hz prominence >= 10x contribute -- otherwise the argmax is")
    print("   locating noise and the scatter is meaningless.\n")
    print("   🛑 `in18-26%` is the load-bearing column: it is the fraction of located peaks that")
    print("   land in the grinding band at all. Above ~8 m/s it collapses and the free argmax moves")
    print("   to a 13-15 Hz highway line, so a slope fitted over the WHOLE speed range is a MIXTURE")
    print("   of two different peaks, not a moving one. That is the fake-negative-slope trap.\n")
    print(f"   {'build':11s} {'|v| bin':>10s} {'win':>4s} {'ep':>3s} {'f0 med':>7s} {'sd':>5s} "
          f"{'in18-26%':>9s} {'p90 prom':>9s}")
    for b in G.ORDER:
        for vlo, vhi in ((0.3, 2), (2, 4), (4, 8), (8, 14), (14, 22), (22, 34)):
            r = [x for x in st[b] if x["eng"] == 1 and vlo <= x["v"] < vhi
                 and np.isfinite(x["p_12-30"]) and x["p_12-30"] >= 10]
            if len(r) < 4:
                continue
            f0 = G.col(r, "f_12-30")
            print(f"   {b:11s} {vlo:4.1f}-{vhi:<5.1f} {len(r):4d} "
                  f"{len({x['ep'] for x in r}):3d} {np.median(f0):7.2f} "
                  f"{np.std(f0, ddof=1):5.2f} "
                  f"{100 * np.mean((f0 >= 18) & (f0 <= 26)):8.1f}% "
                  f"{np.percentile(G.col(r, 'p_12-30'), 90):9.1f}")
        print()

    print("   -- slope of f0 on |v|, engaged, prominence>=10x, episode-clustered bootstrap --")
    print("      CREEP-ONLY (|v| <= 5.35) is the honest test: it is the population grind #1 exists")
    print("      in. The whole-range row is printed underneath ONLY to show the mixture.")
    for vcap, vlab in ((5.35, "CREEP |v|<=5.35"), (8.0, "|v|<=8"), (99.0, "WHOLE RANGE (mixture)")):
        print(f"\n   {vlab}")
        print(f"   {'build':11s} {'n':>4s} {'ep':>3s} {'slope Hz/(m/s)':>15s} {'[95% CI]':>20s} "
              f"{'intercept':>10s}  a=0 inside CI?")
        for b in G.ORDER:
            _slope(st, b, vcap)


def _slope(st, b, vcap):
    r = [x for x in st[b] if x["eng"] == 1 and x["v"] <= vcap and np.isfinite(x["p_12-30"])
         and x["p_12-30"] >= 10 and np.isfinite(x["f_12-30"])]
    if len(r) < 8 or len(set(np.round(G.col(r, "v"), 2))) < 4:
        print(f"   {b:11s} {len(r):4d}  -- too few")
        return
    eps = G.episodes(r)
    v = G.col(r, "v")
    y = G.col(r, "f_12-30")
    a, c = np.polyfit(v, y, 1)
    draws = []
    for _ in range(2000):
        idx = RNG.integers(0, len(eps), len(eps))
        rr = [x for i in idx for x in eps[i]]
        vv, yy = G.col(rr, "v"), G.col(rr, "f_12-30")
        if len(set(np.round(vv, 3))) < 3:
            continue
        draws.append(np.polyfit(vv, yy, 1)[0])
    lo, hi = (np.percentile(draws, 2.5), np.percentile(draws, 97.5)) if draws else (np.nan,) * 2
    print(f"   {b:11s} {len(r):4d} {len(eps):3d} {a:15.4f} [{lo:8.4f}, {hi:8.4f}] "
          f"{c:10.2f}  {'YES (fixed)' if lo <= 0 <= hi else 'no'}"
          f"   in18-26 {100 * np.mean((y >= 18) & (y <= 26)):.0f}%")


# ================================================================== S6 ==========================
def _direct(build, lo=18.0, hi=22.0, eng=1, effmax=None):
    """p99 of the 18-22 Hz analytic envelope over a WHOLE contiguous run, no windowing at all.

    Second method for the headline amplitude. Shares no code with wrecs(): no hop, no Hann taper,
    no central-60% read-back, no cells, no episode bootstrap -- just a rectangular FFT bandpass of
    each run and the median over runs. If the build ordering here disagrees with S1/S4, the window
    machinery is producing it and the result is not real.
    """
    B = G.BUILDS[build]
    vals, nrun, nsamp = [], 0, 0
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        lat = d["cc_lat"] > 0.5
        v = np.abs(d["cs_v"])
        m = (lat if eng else ~lat) & (v >= CREEP[0]) & (v <= CREEP[1])
        if effmax is not None:
            m &= np.abs(sustained(d["tq"], fs)) <= effmax
        for a, b in runs_of(m, d["t"], 256):
            x = np.asarray(d["tq"][a:b], float)
            x = x - x.mean()
            X = np.fft.rfft(x)
            f = np.fft.rfftfreq(len(x), 1 / fs)
            H = np.zeros(len(f), complex)
            k = (f >= lo) & (f <= hi)
            H[k] = 2 * X[k]
            vals.append(float(np.percentile(np.abs(np.fft.irfft(H, n=len(x))), 99)))
            nrun += 1
            nsamp += len(x)
    return (float(np.median(vals)) if vals else np.nan), nrun, nsamp


def s6_second_method(st=None):
    G.hdr("S6.  SECOND METHOD -- whole-run bandpass, no windows, no cells, no bootstrap")
    print("   Median over RUNS of the p99 18-22 Hz analytic envelope. Absolute values differ from")
    print("   S4 because a longer record has a higher p99; only the ORDERING is being checked.\n")
    print(f"   {'build':11s} {'dose':12s} {'runs':>5s} {'sec':>7s} {'p99 env':>9s}  "
          f"{'hands-off':>10s} {'runs':>5s}  | {'MANUAL creep':>13s} {'runs':>5s}")
    for b in G.ORDER:
        e, n, ns = _direct(b)
        h, nh, _ = _direct(b, effmax=200)
        m, nm, _ = _direct(b, eng=0)
        print(f"   {b:11s} {G.DOSE_LABEL[G.BUILDS[b]['kd']]:12s} {n:5d} {ns / 100:7.1f} "
              f"{e:9.1f}  {h:10.1f} {nh:5d}  | {m:13.1f} {nm:5d}")
    print("\n   🛑 The MANUAL column is UNMATCHED on covariates and reads V67 well below the Kd=1")
    print("   routes, while the cell-matched placebo S3c(c) reads ~1.0. That gap is the size of the")
    print("   route/exposure offset the matching removes -- report the matched number, but know the")
    print("   raw one exists.")


# ================================================================== S7 ==========================
def s7_occupancy(st):
    G.hdr("S7.  ★ GRIND #1's OWN OPERATING POINT -- LKAS occupancy and the MEASURED driver torque")
    print("   Estimator mirrors studies/sessions/v68/v66_v67_explained.py SECTION 6: CREEP windows, TOP DECILE of the")
    print("   grind #1 statistic, then read the covariates off that decile. The record it is being")
    print("   compared against is `LKAS engaged 98.7%` and `driver torque median 1268` on V65.")
    print("   🛑 Driver torque is MEASURED here, never substituted by the hands-off DEFINITION")
    print("   (<=200). Reading a definition where a measurement belongs is what produced the")
    print("   withdrawn '>8x' separator; the same substitution would corrupt this table.\n")
    print("   ⚠ BASE RATE IS MANDATORY. Routes differ hugely in how much of their creep is engaged")
    print("   (route 47: 28 of 104 creep windows = 26.9%), so a raw occupancy % is not comparable")
    print("   across builds. LIFT = occupancy / base rate is.\n")

    for frac, flab in ((0.10, "TOP DECILE"), (0.25, "top quartile")):
        print(f"   ---- {flab} of e_18-22 among ALL creep windows (both arms pooled) ----")
        print(f"   {'build':11s} {'dose':12s} {'crp':>4s} {'n':>3s} {'base%':>6s} {'ENG%':>6s} "
              f"{'lift':>5s} {'g6806%':>7s} | driver torque p10/p50/p90 | "
              f"{'rate':>6s} {'|ang|':>6s} {'v':>5s} {'prom':>7s}")
        for b in G.ORDER:
            r = [x for x in st[b] if CREEP[0] <= x["v"] <= CREEP[1]]
            if len(r) < 10:
                print(f"   {b:11s} {len(r):4d} creep windows -- too few")
                continue
            e = G.col(r, HEADLINE)
            thr = np.nanpercentile(e, 100 * (1 - frac))
            top = [x for x, v in zip(r, e) if np.isfinite(v) and v >= thr]
            base = 100 * np.mean(G.col(r, "eng") > 0.5)
            occ = 100 * np.mean(G.col(top, "eng") > 0.5)
            gt = G.col(top, "gate")
            eff = G.col(top, "eff")
            print(f"   {b:11s} {G.DOSE_LABEL[G.BUILDS[b]['kd']]:12s} {len(r):4d} {len(top):3d} "
                  f"{base:6.1f} {occ:6.1f} {occ / max(base, 1e-9):5.2f} "
                  f"{(100 * np.nanmean(gt > 0.5) if np.isfinite(gt).any() else np.nan):7.1f} | "
                  f"{np.percentile(eff, 10):8.0f}{np.percentile(eff, 50):7.0f}"
                  f"{np.percentile(eff, 90):7.0f} | "
                  f"{med(top, 'rate'):6.1f} {med(top, 'ang'):6.1f} {med(top, 'v'):5.2f} "
                  f"{np.nanmedian(G.col(top, 'p_18-26')):7.1f}")
        print()

    print("   -- SECOND DEFINITION of 'grind #1 present': prominence >= 10x in 18-26 Hz, not the")
    print("      top decile of amplitude. A prominence test cannot be passed by a broadly loud")
    print("      window, so if the two definitions disagree the amplitude one is the suspect. --")
    print(f"   {'build':11s} {'dose':12s} {'crp':>4s} {'n':>3s} {'base%':>6s} {'ENG%':>6s} "
          f"{'lift':>5s} | driver torque p10/p50/p90 | {'rate':>6s} {'|ang|':>6s}")
    for b in G.ORDER:
        r = [x for x in st[b] if CREEP[0] <= x["v"] <= CREEP[1]]
        top = [x for x in r if np.isfinite(x["p_18-26"]) and x["p_18-26"] >= 10]
        if len(r) < 10 or len(top) < 4:
            print(f"   {b:11s} {len(r):4d} creep / {len(top)} present -- too few")
            continue
        base = 100 * np.mean(G.col(r, "eng") > 0.5)
        occ = 100 * np.mean(G.col(top, "eng") > 0.5)
        eff = G.col(top, "eff")
        print(f"   {b:11s} {G.DOSE_LABEL[G.BUILDS[b]['kd']]:12s} {len(r):4d} {len(top):3d} "
              f"{base:6.1f} {occ:6.1f} {occ / max(base, 1e-9):5.2f} | "
              f"{np.percentile(eff, 10):8.0f}{np.percentile(eff, 50):7.0f}"
              f"{np.percentile(eff, 90):7.0f} | {med(top, 'rate'):6.1f} {med(top, 'ang'):6.1f}")

    print("\n   🛑 LIFT IS CEILING-CAPPED at 1/base, so it is NOT comparable across these routes:")
    print("      V59's ceiling is 1.64 and it is AT it, V67's ceiling is 3.72 and it reads 3.38.")
    print("      Read the OCCUPANCY % against its own base rate; do not rank builds by lift.")

    print("\n   🛑🛑 THE TOP DECILE IS ROUTE-RELATIVE, so 'grind #1's driver torque' is BUILD-")
    print("   DEPENDENT and a single number cannot stand for it:")
    print("       Kd=1 builds (mode at FULL strength):  V59 median 109, V64 median 114  -> genuinely")
    print("                                             hands-off; this is the symptom as reported.")
    print("       Kd=2 builds (mode already damped):    V62 380, V65/r3b 513, V65/r3a 934, V67 1288")
    print("                                             -> the RESIDUE left after the fix.")
    print("   The V65-derived figure of record (1268) reproduces almost exactly on route 47 (1288),")
    print("   so the corrected separator arithmetic is sound -- but both describe the POST-FIX")
    print("   residue, not the full-strength symptom. On V67 the top decile's p10 is 376, i.e. >90%")
    print("   of the loudest grind #1 creep windows sit ABOVE the hands-off threshold of 200.")
    print("   ⇒ quoting either number without naming the build it was measured on is the same class")
    print("     of substitution that the '>8x' retraction was about.")

    print("\n   -- THE MIGRATION PREDICTION, and why it CANNOT be cleanly tested here --")
    print("   V67 damps only the engaged arm, so the loudest grind #1 windows should migrate toward")
    print("   the disengaged (stock) arm. Observed: 90.9% engaged in the decile vs 100% on every")
    print("   unconditional build, 80.8% vs 90.3-100% at the quartile. Directionally consistent,")
    print("   but V67 also has by far the most disengaged creep exposure (76 of 104 windows vs 39%")
    print("   on V59), so the migration and the exposure are confounded and n is 1-5 windows.")
    print("   ⇒ NOT evidence. The base-rate-free version of this question is S3b/S3c's DiD.")


# ================================================================== main ========================
SECTIONS = {"s0": s0_provenance, "s1": s1_exposure, "s2": s2_cross_route,
            "s2c": s2c_selectivity, "s2b": s2b_v62_headline,
            "s3": s3_within_route, "s3c": s3c_arm_matched,
            "s4": s4_presence, "s5": s5_frequency, "s6": s6_second_method,
            "s7": s7_occupancy}


def main():
    want = [a.lower() for a in sys.argv[1:]] or list(SECTIONS)
    st = loaded() if any(w != "s0" for w in want) else None
    for w in want:
        fn = SECTIONS.get(w)
        if fn is None:
            print(f"unknown section {w}; known: {list(SECTIONS)}")
            continue
        fn() if w == "s0" else fn(st)


if __name__ == "__main__":
    main()
