#!/usr/bin/env python3
r"""SCORE ROUTE 81 = THE V98 FLIGHT.  The first COMPARATOR probe in the kit.

Deliverables, in the orchestrator's priority order:
  D0  health + identity                      (done in `decode/extract_r81.py`; re-asserted here)
  D1  the (b6,b5) comparator, joint duty table, with the pre-registered 427==1023 exclusion
  D2  the CONTROL bits -- b4's `arg(B') - arg(rate)` must reproduce V96's +78.6/+78.0 deg
  D3  b3 = sign(gp-0x6752)
  D4  the SYMPTOM: 6-9 Hz column-torque band power, engaged vs disengaged, matched creep
  D5  what a null licenses -- pre-registered per statistic, in the scoring doc

🛑 SIGN CONVENTION: `angle(scipy.signal.csd(x, y)) = arg(Y) - arg(X)`; positive => y LEADS x.
   Self-checked with a known lag before any phase number is produced (`_phase_selfcheck`).
🛑 raw14 off-by-one: every bit series is `raw14_b4[row2raw14]`, asserted == `probe` at extraction.
   NEVER `(t, raw14_b4)`.
🛑 CONTROLS BEFORE MEASUREMENTS: the split-half-by-episode null is computed and PRINTED FIRST;
   every ratio is judged against THAT, not against 1.0.
🛑 The `steeringPressed` mask is `|STEER_TORQUE_SENSOR| > 1200` and it EXCLUDES the symptom regime
   (the operator produces the symptom by OVERRIDING).  So the symptom arm here is ENGAGED+HANDS-ON
   scored on BAND POWER, and windows are 1.28 s, not 5.12 s.  Stated, per
   `memory/reference/measurement/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`.
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
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1].parent
AN = ROOT / "analysis-2020accord"
OUT = AN / "sessions/v99"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v97_r80_vs_v96 import _phase_selfcheck, band_rms, episodes  # noqa: E402

KMH = 3.6
FS = 100.0
RNG = np.random.default_rng(20260813)

# V98 byte-4 map, read off builds/v80_v107/build_v98_tva.py's PAYLOAD.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08
# V96/V97 byte-4 map (routes 7e/7f/80) -- for the b4 control's cross-build reference.
V96_SIGN_6B70, V96_SIGN_374C = 0x80, 0x40

ROUTES = {"81": ("_scratch/cache/r81", "r81", "V98"),
          "80": ("_scratch/cache/r80", "r80", "V97"),
          "7e": ("_scratch/cache/r7e", "r7e", "V96"),
          "7f": ("_scratch/cache/r7f", "r7f", "V96")}

BANDS = {"0.5-3": (0.5, 3.0), "6-9": (6.0, 9.0), "15-22": (15.0, 22.0),
         "26-31": (26.0, 31.0), "35-45": (35.0, 45.0)}
NPERSEG = 128            # 1.28 s @ 100 Hz -- override runs cannot support 5.12 s
HOP = 64


def load(r):
    cdir, stem, build = ROUTES[r]
    f = AN / cdir / f"{stem}.npz"
    if not f.exists():
        return None
    z = np.load(f, allow_pickle=True)
    t = np.asarray(z["t"], float)
    idx = np.asarray(z["row2raw14"], int)
    b4 = (np.asarray(z["raw14_b4"], int) & 0xFF)[idx]
    b7b = (np.asarray(z["raw14_b7"], int) & 0xFF)[idx]
    assert np.all(b4 == (np.asarray(z["probe"], int) & 0xFF)), "raw14 map broken"
    d = dict(t=t, b4=b4, b7byte=b7b, build=build, route=r,
             eng=np.asarray(z["cc_lat"], float) > 0.5,
             v=np.asarray(z["cs_v"], float) * KMH,
             rate=np.asarray(z["cs_rate"], float),
             ang=np.asarray(z["cs_ang"], float),
             cs_ang=np.asarray(z["cs_ang"], float),
             co_req=np.asarray(z["co_req"], float),
             cc_req=np.asarray(z["cc_req"], float),
             tq=np.asarray(z["tq"], float),
             cs_tq=np.asarray(z["cs_tq"], float),
             press=np.asarray(z["cs_press"], float) > 0.5,
             seg=np.asarray(z["seg"], int),
             ab_t=np.asarray(z["ab_t1ab"], float),
             ab_mt=np.asarray(z["ab_mt"], int))
    if r == "81":
        d["sign_6b70"] = (b4 & M_B7) != 0
        d["sign_374c"] = (b4 & M_B4) != 0
        d["b6_model_ge"] = (b4 & M_B6) != 0
        d["b5_req_ge"] = (b4 & M_B5) != 0
        d["b3_pol"] = (b4 & M_B3) != 0
        d["ident"] = (b7b & 0xC0) >> 6
    else:
        d["sign_6b70"] = (b4 & V96_SIGN_6B70) != 0
        d["sign_374c"] = (b4 & V96_SIGN_374C) != 0
        d["ident"] = (b7b & 0xC0) >> 6
    # ZOH the 50 Hz 427 magnitude onto the 100 Hz row grid (last sample at or before t)
    j = np.clip(np.searchsorted(d["ab_t"], t, side="right") - 1, 0, len(d["ab_mt"]) - 1)
    d["mt_row"] = d["ab_mt"][j]
    return d


# ==================================================================================================
def welch_phase(x, y, fs, nperseg, lo, hi):
    """Coherence-weighted mean phase and mean coherence over [lo, hi].  arg(Y) - arg(X)."""
    x = np.asarray(x, float) - np.mean(x)
    y = np.asarray(y, float) - np.mean(y)
    if len(x) < nperseg or np.std(x) == 0 or np.std(y) == 0:
        return float("nan"), float("nan")
    f, Pxy = signal.csd(x, y, fs=fs, nperseg=nperseg)
    _, Cxy = signal.coherence(x, y, fs=fs, nperseg=nperseg)
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return float("nan"), float("nan")
    w = Cxy[m]
    z = np.sum(w * Pxy[m] / np.abs(Pxy[m] + 1e-30))
    return float(np.degrees(np.angle(z))), float(np.mean(Cxy[m]))


def circ_mean(deg):
    deg = np.asarray(deg, float)
    deg = deg[np.isfinite(deg)]
    if not len(deg):
        return float("nan")
    return float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(deg))))))


def boot_circ_by_episode(deg, epi, n=4000):
    deg = np.asarray(deg, float)
    epi = np.asarray(epi, int)
    ok = np.isfinite(deg)
    deg, epi = deg[ok], epi[ok]
    ue = np.unique(epi)
    if len(ue) < 2:
        return float("nan"), float("nan"), len(ue)
    b = []
    for _ in range(n):
        pick = RNG.choice(ue, len(ue), replace=True)
        vals = np.concatenate([deg[epi == e] for e in pick])
        b.append(circ_mean(vals))
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), len(ue)


def acf_tau(x, fs=FS, maxlag=400):
    """Correlation time: integral of the ACF to its first zero crossing, in seconds."""
    x = np.asarray(x, float)
    x = x - x.mean()
    if np.std(x) == 0:
        return float("nan")
    n = min(maxlag, len(x) - 1)
    ac = np.array([np.dot(x[:len(x) - k], x[k:]) / np.dot(x, x) for k in range(n)])
    zc = np.where(ac <= 0)[0]
    k0 = int(zc[0]) if len(zc) else n
    return float(np.sum(ac[:k0]) / fs)


# ==================================================================================================
#  WINDOWED BAND POWER  --  1.28 s, 50 % overlap, condition must hold on EVERY frame of the window
# ==================================================================================================
def windows(d, sel, min_s=1.28):
    """(episode_index, slice) for every 1.28 s window entirely inside a >=1.28 s run of `sel`."""
    out = []
    for ei, (a, b) in enumerate(episodes(sel, d["t"], min_s)):
        for s in range(a, b - NPERSEG + 1, HOP):
            out.append((ei, slice(s, s + NPERSEG)))
    return out


def band_table(d, sel, tag):
    w = windows(d, sel)
    rows = []
    for ei, sl in w:
        r = dict(ep=ei, v=float(np.median(d["v"][sl])),
                 rate=float(np.median(np.abs(d["rate"][sl]))))
        for k, (lo, hi) in BANDS.items():
            r[k] = band_rms(d["tq"][sl], FS, lo, hi, NPERSEG)
        rows.append(r)
    return dict(tag=tag, n_windows=len(rows), n_episodes=len(set(r["ep"] for r in rows)),
                rows=rows)


def geo_median(vals):
    v = np.asarray([x for x in vals if np.isfinite(x) and x > 0], float)
    return float(np.exp(np.median(np.log(v)))) if len(v) else float("nan")


V_EDGES = (0, 2, 5, 8, 12, 20)
R_EDGES = (0, 5, 25, 60, 1e9)


def _bin(r):
    """(speed bin, |rate| bin) -- the standardisation cell."""
    v, rt = max(r["v"], 0.0), max(r["rate"], 0.0)
    iv = max(i for i, e in enumerate(V_EDGES[:-1]) if v >= e)
    ir = max(i for i, e in enumerate(R_EDGES[:-1]) if rt >= e)
    return iv, ir


def standardised_ratio(rowsA, rowsB, band, min_n=3):
    """Weighted geometric mean of the per-(speed x |rate|) cell A/B median ratio.
    Weight = min(nA, nB) -- cells with no counterpart in the other arm are DROPPED, so the
    contrast is never carried by a regime only one arm visited."""
    cells = {}
    for tag, rows in (("A", rowsA), ("B", rowsB)):
        for r in rows:
            if np.isfinite(r[band]) and r[band] > 0:
                cells.setdefault(_bin(r), {"A": [], "B": []})[tag].append(r[band])
    num, den, detail = 0.0, 0.0, {}
    for k, v in sorted(cells.items()):
        if len(v["A"]) < min_n or len(v["B"]) < min_n:
            detail[str(k)] = dict(nA=len(v["A"]), nB=len(v["B"]), ratio=None)
            continue
        ra = geo_median(v["A"]) / geo_median(v["B"])
        w = min(len(v["A"]), len(v["B"]))
        detail[str(k)] = dict(nA=len(v["A"]), nB=len(v["B"]), ratio=float(ra),
                              medA=geo_median(v["A"]), medB=geo_median(v["B"]))
        num += w * np.log(ra)
        den += w
    return (float(np.exp(num / den)) if den else float("nan")), detail


# --------------------------------------------------------------------------------------------
#  RESAMPLING UNIT.  🛑 The episode bootstrap the kit mandates is IMPOSSIBLE on this route --
#  3 engaged episodes and, in the LKAS-off demo, exactly ONE 59.9 s manual run.  So the unit is
#  a contiguous BLOCK of `BLOCK_S` seconds of windows, which is WEAKER than an episode bootstrap
#  and is labelled as such everywhere it is used.  The split-half null uses the SAME unit, so
#  the floor and the contrast are like-for-like.
# --------------------------------------------------------------------------------------------
BLOCK_S = 5.12


def blockify(T):
    """Tag every window with (episode, block) -- blocks are BLOCK_S-second runs inside an episode."""
    per = int(round(BLOCK_S / (HOP / FS)))          # windows per block
    out = []
    for ei in sorted(set(r["ep"] for r in T["rows"])):
        rows = [r for r in T["rows"] if r["ep"] == ei]
        for i, r in enumerate(rows):
            r = dict(r)
            r["blk"] = (ei, i // per)
            out.append(r)
    return out


def split_half_null(rows, band, n=2000):
    """🛑 CONTROL FIRST.  Split the arm's OWN blocks in half at random; the distribution of the
    half-vs-half fold-ratio IS the resolution floor.  Judge every contrast against THAT, not 1.0."""
    blks = sorted(set(r["blk"] for r in rows))
    if len(blks) < 4:
        return dict(n_blocks=len(blks), floor_p50=None,
                    note=f"only {len(blks)} blocks -- no usable split-half null")
    out = []
    for _ in range(n):
        p = list(RNG.permutation(len(blks)))
        h1 = set(blks[i] for i in p[:len(p) // 2])
        a = geo_median([r[band] for r in rows if r["blk"] in h1])
        b = geo_median([r[band] for r in rows if r["blk"] not in h1])
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            out.append(a / b)
    o = np.array(out)
    o = np.where(o < 1, 1 / o, o)
    return dict(n_blocks=len(blks), floor_p50=float(np.percentile(o, 50)),
                floor_p95=float(np.percentile(o, 95)))


def boot_ratio(rowsA, rowsB, band, n=2000):
    """Block bootstrap of the SAME standardised statistic that is reported as the point estimate."""
    ba = sorted(set(r["blk"] for r in rowsA))
    bb = sorted(set(r["blk"] for r in rowsB))
    if len(ba) < 3 or len(bb) < 3:
        return None, None, len(ba), len(bb)
    ia = {k: [r for r in rowsA if r["blk"] == k] for k in ba}
    ib = {k: [r for r in rowsB if r["blk"] == k] for k in bb}
    out = []
    for _ in range(n):
        A = [r for k in RNG.choice(len(ba), len(ba), True) for r in ia[ba[k]]]
        B = [r for k in RNG.choice(len(bb), len(bb), True) for r in ib[bb[k]]]
        v, _ = standardised_ratio(A, B, band)
        if np.isfinite(v):
            out.append(v)
    if len(out) < 50:
        return None, None, len(ba), len(bb)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)),
            len(ba), len(bb))


# ==================================================================================================
def main():
    res = {"sign_convention": "angle(csd(x,y)) = arg(Y) - arg(X); positive => y LEADS x"}
    print("=" * 96)
    print("  ROUTE 81 = THE V98 FLIGHT.  CONTROLS RUN BEFORE MEASUREMENTS.")
    print("=" * 96)
    res["selfcheck"] = _phase_selfcheck()

    D = {r: load(r) for r in ROUTES}
    D = {k: v for k, v in D.items() if v is not None}
    d = D["81"]
    n = len(d["t"])

    # ============================== D0 =========================================================
    print("\n=== D0  IDENTITY + HEALTH ===")
    ih = {int(a): int(b) for a, b in zip(*np.unique(d["ident"], return_counts=True))}
    res["D0"] = dict(frames=n, ident_hist=ih, ident2_duty=float((d["ident"] == 2).mean()),
                     mt_max=int(d["ab_mt"].max()), mt_distinct=int(len(np.unique(d["ab_mt"]))),
                     mt_eq1023_frames_1ab=int((d["ab_mt"] == 1023).sum()),
                     mt_eq1023_frames_row=int((d["mt_row"] == 1023).sum()))
    print(f"  byte7[7:6] hist {ih}   duty(==2) = {res['D0']['ident2_duty']:.6f}  "
          f"-> {'V98 CONFIRMED' if res['D0']['ident2_duty'] >= 0.999 else 'POS-1 FAIL'}")
    print(f"  427: {res['D0']['mt_distinct']} distinct codes, max {res['D0']['mt_max']}, "
          f"==1023 on {res['D0']['mt_eq1023_frames_1ab']} of {len(d['ab_mt']):,} 0x1AB frames "
          f"=> 🛑 PRE-REGISTERED b6 EXCLUSION removes "
          f"{res['D0']['mt_eq1023_frames_row']} of {n:,} rows")

    # ============================== D1 =========================================================
    print("\n=== D1  THE COMPARATOR ===")
    keep = d["mt_row"] != 1023                        # the pre-registered latch exclusion
    strata = {
        "ALL": np.ones(n, bool), "ENGAGED": d["eng"], "MANUAL": ~d["eng"],
        "ENG+override": d["eng"] & d["press"], "ENG+handsoff": d["eng"] & ~d["press"],
        "MAN+handson": (~d["eng"]) & d["press"], "MAN+handsoff": (~d["eng"]) & ~d["press"],
        "seg1_ENGAGED": (d["seg"] == 1) & d["eng"],
        "seg2_MANUAL(LKASoff demo)": (d["seg"] == 2) & ~d["eng"],
    }
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 20)):
        strata[f"ENG v{lo}-{hi}"] = d["eng"] & (d["v"] >= lo) & (d["v"] < hi)
        strata[f"MAN v{lo}-{hi}"] = (~d["eng"]) & (d["v"] >= lo) & (d["v"] < hi)
    for lo, hi in ((0, 5), (5, 25), (25, 60), (60, 1e9)):
        strata[f"ENG |rate|{lo}-{hi}"] = (d["eng"] & (np.abs(d["rate"]) >= lo)
                                          & (np.abs(d["rate"]) < hi))
    res["D1"] = {}
    print(f"  {'stratum':30s} {'n':>6s} {'b6':>7s} {'b5':>7s} {'b7':>7s} {'b4':>7s} {'b3':>7s}"
          f"   {'(0,0)':>7s} {'(1,0)':>7s} {'(0,1)':>7s} {'(1,1)':>7s}")
    for nm, s in strata.items():
        s = s & keep
        if not s.sum():
            continue
        b6, b5 = d["b6_model_ge"][s], d["b5_req_ge"][s]
        r = dict(n=int(s.sum()), b6=float(b6.mean()), b5=float(b5.mean()),
                 b7=float(d["sign_6b70"][s].mean()), b4=float(d["sign_374c"][s].mean()),
                 b3=float(d["b3_pol"][s].mean()),
                 joint={"0,0": float((~b6 & ~b5).mean()), "1,0": float((b6 & ~b5).mean()),
                        "0,1": float((~b6 & b5).mean()), "1,1": float((b6 & b5).mean())})
        res["D1"][nm] = r
        print(f"  {nm:30s} {r['n']:6d} {r['b6']:7.4f} {r['b5']:7.4f} {r['b7']:7.4f} "
              f"{r['b4']:7.4f} {r['b3']:7.4f}   " +
              " ".join(f"{r['joint'][k]:7.4f}" for k in ("0,0", "1,0", "0,1", "1,1")))

    # ---- correlation time -> the pre-registered SE(p) for the primary endpoint
    print("\n  -- SE of the comparator duties, from the bits' OWN measured correlation time")
    tt = {}
    for nm, arr in (("b6", d["b6_model_ge"]), ("b4", d["sign_374c"]),
                    ("b7", d["sign_6b70"])):
        tau = acf_tau(arr[d["eng"]].astype(float))
        tt[nm] = tau
        p = float(arr[d["eng"] & keep].mean())
        T = float(d["eng"].sum()) / FS
        neff = T / tau if tau and tau > 0 else float("nan")
        se = np.sqrt(p * (1 - p) / neff) if np.isfinite(neff) and neff > 0 else float("nan")
        res["D1"][f"SE_{nm}"] = dict(tau_s=tau, T_engaged_s=T, n_eff=neff, p=p, se=se)
        print(f"     {nm}: tau {tau:.3f} s   T {T:.1f} s   n_eff {neff:.0f}   "
              f"p {p:.4f}   SE {se:.4f}   95% CI [{p-1.96*se:.4f}, {p+1.96*se:.4f}]")

    # ---- the FREEZE detector, pre-registered in builds/v80_v107/build_v98_tva.py's VAL section
    b4s = d["sign_374c"].astype(int)
    chg = np.diff(b4s) != 0
    runlen = np.zeros(len(b4s), int)
    c = 1
    for i in range(1, len(b4s)):
        c = 1 if chg[i - 1] else c + 1
        runlen[i] = c
    frozen = runlen >= 20
    mt_changing = np.zeros(len(b4s), bool)
    for i in np.where(frozen)[0]:
        a = max(0, i - 19)
        mt_changing[i] = len(np.unique(d["mt_row"][a:i + 1])) > 1
    res["D1"]["freeze_detector"] = dict(
        frames_b4_frozen_ge20=int(frozen.sum()),
        duty_b4_frozen_and_427_changing=float((frozen & mt_changing).mean()),
        duty_engaged=float((frozen & mt_changing)[d["eng"]].mean()))
    fz = res["D1"]["freeze_detector"]
    print(f"\n  -- FREEZE DETECTOR (pre-registered): b4 constant >=20 frames AND 427 changing: "
          f"duty {fz['duty_b4_frozen_and_427_changing']:.4f} all / "
          f"{fz['duty_engaged']:.4f} engaged   ({fz['frames_b4_frozen_ge20']:,} frozen frames)")

    # ============================== D2 =========================================================
    print("\n=== D2  THE CONVERSE POSITIVE CONTROL -- arg(B') - arg(rate) must reproduce +78 deg ===")
    print("    V96 measured +78.6 / +78.0 deg on routes 7e/7f;  arg(V)-arg(rate) = -97.3 / -101.8;")
    print("    arg(V)-arg(B') = -178.1 on BOTH.  Same rung, byte-identical, on V98's b4/b7.")
    print("    METHOD A = Welch over the WHOLE engaged set (V96's stated method), nperseg 1024.")
    print("    METHOD B = 5.12 s windows, nperseg 128 (8 Welch segments => a REAL coherence),")
    print("               circular mean, block-bootstrapped.")
    res["D2"] = {}
    for r, dd in D.items():
        sel = dd["eng"]
        rr_a, Bp_a, V_a = dd["rate"][sel], dd["sign_374c"][sel].astype(float), \
            dd["sign_6b70"][sel].astype(float)
        entry = dict(build=dd["build"], engaged_frames=int(sel.sum()), A={}, B={})
        for k, (x, y) in (("Bp_vs_rate", (rr_a, Bp_a)), ("V_vs_rate", (rr_a, V_a)),
                          ("V_vs_Bp", (Bp_a, V_a))):
            p, c_ = welch_phase(x, y, FS, 1024, 6.0, 9.0)
            entry["A"][k] = dict(phase_deg=p, coherence=c_)
        print(f"  r{r} ({dd['build']:3s}) A: " + "   ".join(
            f"{k} {entry['A'][k]['phase_deg']:+7.2f} (coh {entry['A'][k]['coherence']:.3f})"
            for k in ("Bp_vs_rate", "V_vs_rate", "V_vs_Bp")))
        # ---- METHOD B
        WIN = 512
        rows = {k: [] for k in ("Bp_vs_rate", "V_vs_rate", "V_vs_Bp")}
        co = {k: [] for k in rows}
        blk = {k: [] for k in rows}
        for ei, (a, b) in enumerate(episodes(sel, dd["t"], WIN / FS)):
            for bi, s in enumerate(range(a, b - WIN + 1, WIN // 2)):
                sl = slice(s, s + WIN)
                rr = dd["rate"][sl]
                Bp = dd["sign_374c"][sl].astype(float)
                V = dd["sign_6b70"][sl].astype(float)
                for k, (x, y) in (("Bp_vs_rate", (rr, Bp)), ("V_vs_rate", (rr, V)),
                                  ("V_vs_Bp", (Bp, V))):
                    p, c_ = welch_phase(x, y, FS, 128, 6.0, 9.0)
                    if np.isfinite(p):
                        rows[k].append(p); co[k].append(c_); blk[k].append((ei, bi))
        for k in rows:
            if not rows[k]:
                continue
            m = circ_mean(rows[k])
            u = sorted(set(blk[k]))
            lo, hi, nb = boot_circ_by_episode(
                rows[k], np.array([u.index(x) for x in blk[k]]))
            entry["B"][k] = dict(phase_deg=m, ci=[lo, hi], windows=len(rows[k]),
                                 blocks=nb, coherence=float(np.mean(co[k])))
        if entry["B"]:
            print(f"  r{r} ({dd['build']:3s}) B: " + "   ".join(
                f"{k} {entry['B'][k]['phase_deg']:+7.2f} "
                f"[{entry['B'][k]['ci'][0]:+6.1f},{entry['B'][k]['ci'][1]:+6.1f}] "
                f"n={entry['B'][k]['windows']}"
                for k in rows if k in entry["B"]))
        res["D2"][r] = entry

    # ============================== D3 =========================================================
    print("\n=== D3  b3 = (gp-0x6752 >= 0) ===")
    b3 = d["b3_pol"]
    res["D3"] = dict(duty=float(b3.mean()), n=int(len(b3)), n_true=int(b3.sum()),
                     transitions=int((np.diff(b3.astype(int)) != 0).sum()),
                     duty_engaged=float(b3[d["eng"]].mean()),
                     duty_manual=float(b3[~d["eng"]].mean()))
    print(f"  duty {res['D3']['duty']:.6f} over {res['D3']['n']:,} frames, "
          f"{res['D3']['transitions']} transitions.  "
          f"=> gp-0x6752 is CONSTANT and {'NEGATIVE' if res['D3']['duty'] == 0 else 'see duty'}.")
    print("  => sign(gp-0x374c>>4) = -sign(sum6)  =>  b4 == 1  <=>  the six-lane sum is POSITIVE.")

    # ============================== D4 =========================================================
    print("\n=== D4  THE SYMPTOM: 6-9 Hz column torque (0x18F STEER_TORQUE_SENSOR), 1.28 s windows")
    print("    🛑 CONTROL FIRST -- split-half-by-EPISODE null inside each arm.")
    arms = {
        "ENG_all": d["eng"],
        "MAN_all": ~d["eng"],
        "ENG_handson": d["eng"] & d["press"],
        "MAN_handson": (~d["eng"]) & d["press"],
        "ENG_handsoff": d["eng"] & ~d["press"],
        "MAN_handsoff": (~d["eng"]) & ~d["press"],
        "seg1_ENG": (d["seg"] == 1) & d["eng"],
        "seg2_MAN": (d["seg"] == 2) & ~d["eng"],
        "seg2_MAN_handson": (d["seg"] == 2) & (~d["eng"]) & d["press"],
        "seg1_ENG_handson": (d["seg"] == 1) & d["eng"] & d["press"],
    }
    T = {k: band_table(d, s, k) for k, s in arms.items()}
    R = {k: blockify(v) for k, v in T.items()}
    res["D4"] = {"exposure": {k: dict(windows=v["n_windows"], episodes=v["n_episodes"],
                                      blocks=len(set(r["blk"] for r in R[k])))
                              for k, v in T.items()}}
    print(f"\n  {'arm':22s} {'win':>5s} {'eps':>4s} {'blk':>4s}  " +
          "  ".join(f"{b:>9s}" for b in BANDS))
    for k, v in T.items():
        if not v["n_windows"]:
            print(f"  {k:22s} {0:5d} {0:4d} {0:4d}   (no windows)")
            continue
        med = {b: geo_median([r[b] for r in v["rows"]]) for b in BANDS}
        res["D4"].setdefault("medians", {})[k] = med
        print(f"  {k:22s} {v['n_windows']:5d} {v['n_episodes']:4d} "
              f"{len(set(r['blk'] for r in R[k])):4d}  " +
              "  ".join(f"{med[b]:9.2f}" for b in BANDS))

    # ---- the mask diagnostic: how many engaged windows does a pure hands-on/off split throw away?
    e_all, e_on, e_off = T["ENG_all"]["n_windows"], T["ENG_handson"]["n_windows"], \
        T["ENG_handsoff"]["n_windows"]
    res["D4"]["mask_diagnostic"] = dict(
        engaged_windows=e_all, pure_handson=e_on, pure_handsoff=e_off,
        dropped_by_pure_split=e_all - e_on - e_off,
        dropped_frac=float((e_all - e_on - e_off) / e_all) if e_all else float("nan"))
    md = res["D4"]["mask_diagnostic"]
    print(f"\n  -- 🛑 MASK DIAGNOSTIC: a PURE hands-on / hands-off split keeps only "
          f"{e_on}+{e_off} of {e_all} engaged windows; it DISCARDS {md['dropped_frac']*100:.1f} % "
          f"of them (windows where |cs_tq| crosses 1200 inside the window).\n"
          f"     Those discarded windows are exactly where the 6-9 Hz oscillation IS -- "
          f"the mask removes the symptom.  The UNMASKED arm is the one to read.")

    print("\n  -- 🛑 SPLIT-HALF NOISE FLOOR (block resampling; judge every ratio against THIS)")
    print("     ⚠ The kit's mandated EPISODE bootstrap is IMPOSSIBLE here: 3 engaged episodes,")
    print("       and the LKAS-off demo is ONE 59.9 s run.  Unit = 5.12 s contiguous BLOCK.")
    res["D4"]["null"] = {}
    for k in ("ENG_all", "MAN_all", "seg1_ENG", "seg2_MAN"):
        if not T[k]["n_windows"]:
            continue
        for b in ("6-9", "0.5-3", "35-45"):
            nl = split_half_null(R[k], b)
            res["D4"]["null"][f"{k}_{b}"] = nl
            if nl.get("floor_p50") is None:
                print(f"     {k:12s} {b:6s}: {nl['note']}")
            else:
                print(f"     {k:12s} {b:6s}: blocks {nl['n_blocks']:2d}  "
                      f"floor p50 {nl['floor_p50']:.2f}x  p95 {nl['floor_p95']:.2f}x")

    print("\n  -- CONTRASTS: geometric mean of per-(speed x |rate|)-cell ratios, block-bootstrapped")
    res["D4"]["contrasts"] = {}
    PAIRS = [("ENG_all", "MAN_all"), ("seg1_ENG", "seg2_MAN"),
             ("ENG_handson", "MAN_handson"), ("ENG_handsoff", "MAN_handsoff"),
             ("seg1_ENG_handson", "seg2_MAN_handson")]
    for A, B in PAIRS:
        if not (T[A]["n_windows"] and T[B]["n_windows"]):
            continue
        print(f"     {A} / {B}:")
        for b in BANDS:
            ra, det = standardised_ratio(R[A], R[B], b)
            lo, hi, na, nb = boot_ratio(R[A], R[B], b)
            if not np.isfinite(ra):
                # 🛑 no (speed x |rate|) cell has >=3 windows in BOTH arms => the contrast is
                # UNDEFINED, and a bootstrap CI would be an artefact of resampling.  Suppressed.
                lo = hi = None
            res["D4"]["contrasts"][f"{A}_vs_{B}_{b}"] = dict(
                ratio_standardised=ra, ci_block_boot=[lo, hi], blocksA=na, blocksB=nb,
                per_cell=det)
            ci = (f"[{lo:6.2f}, {hi:6.2f}]" if lo is not None
                  else "[UNDEFINED -- no matched speed x rate cell]")
            star = " <<<" if b == "6-9" else ("  (negative control)" if b == "35-45" else "")
            print(f"        {b:6s} ratio {ra:7.3f}   block-boot CI {ci}"
                  f"  (blk {na}/{nb}){star}")

    # ---------------- D4b: is the 6-9 Hz excess in the ANGLE too, and is it COMMANDED? ----------
    print("\n=== D4b  CROSS-SIGNAL CONTROL -- the same contrast on four signals ===")
    SIG = {"tq_0x18F_column": d["tq"], "angle_deg": d["cs_ang"],
           "op_cmd_torque": d["co_req"],
           "mt427_gp6b70": d["mt_row"].astype(float) * (64.0 / 5.0)}
    res["D4b"] = {}
    for sname, x in SIG.items():
        dd = dict(d); dd["tq"] = np.asarray(x, float)
        tabs = {}
        for an, sel in (("ENG_all", d["eng"]), ("MAN_all", ~d["eng"]),
                        ("seg1_ENG", (d["seg"] == 1) & d["eng"]),
                        ("seg2_MAN", (d["seg"] == 2) & ~d["eng"])):
            tabs[an] = blockify(band_table(dd, sel, an))
        res["D4b"][sname] = {}
        for an in tabs:
            res["D4b"][sname][f"median_{an}"] = {
                b: geo_median([r[b] for r in tabs[an]]) for b in BANDS}
        for A, B in (("ENG_all", "MAN_all"), ("seg1_ENG", "seg2_MAN")):
            line = f"  {sname:20s} {A:9s}/{B:9s}:"
            for b in ("0.5-3", "6-9", "15-22", "35-45"):
                ra, _ = standardised_ratio(tabs[A], tabs[B], b)
                lo, hi, _, _ = boot_ratio(tabs[A], tabs[B], b)
                res["D4b"][sname][f"{A}_vs_{B}_{b}"] = dict(ratio=ra, ci=[lo, hi])
                ci = (f"[{lo:.2f},{hi:.2f}]" if lo is not None and np.isfinite(ra) else "[--]")
                line += f"  {b} {ra:6.2f} {ci}"
            print(line)

    # ---------------- D4c: WITHIN-EPISODE -- does the comparator move WITH the symptom? --------
    print("\n=== D4c  WITHIN-EPISODE DECOMPOSITION -- comparator duty vs 6-9 Hz, engaged only ===")
    print("    Partial Spearman controlling for speed, |wheel rate| and press; the null is a")
    print("    BLOCK PERMUTATION (5.12 s blocks), so within-episode correlation cannot fake it.")
    W = []
    for ei, sl in windows(d, d["eng"]):
        W.append(dict(ep=ei, b69=band_rms(d["tq"][sl], FS, 6.0, 9.0, NPERSEG),
                      b6=float(d["b6_model_ge"][sl].mean()),
                      b4=float(d["sign_374c"][sl].mean()),
                      b7=float(d["sign_6b70"][sl].mean()),
                      v=float(np.median(d["v"][sl])),
                      rate=float(np.median(np.abs(d["rate"][sl]))),
                      press=float(d["press"][sl].mean())))
    per = int(round(BLOCK_S / (HOP / FS)))
    for ei in sorted(set(r["ep"] for r in W)):
        for j, i in enumerate([i for i, r in enumerate(W) if r["ep"] == ei]):
            W[i]["blk"] = (ei, j // per)
    from scipy import stats as st

    def _presid(a, ctrl):
        A = np.column_stack([np.ones(len(a))] + [st.rankdata(c) for c in ctrl])
        ra = st.rankdata(a)
        return ra - A @ np.linalg.lstsq(A, ra, rcond=None)[0]

    y = np.log(np.array([r["b69"] for r in W]))
    ctrl = [np.array([r[k] for r in W]) for k in ("v", "rate", "press")]
    bl = sorted(set(r["blk"] for r in W))
    pos = {b: [i for i, r in enumerate(W) if r["blk"] == b] for b in bl}
    res["D4c"] = {"n_windows": len(W), "n_blocks": len(bl)}
    q = np.percentile([r["b69"] for r in W], [33, 67])
    for nm, lo, hi in (("LOW", -1, q[0]), ("MID", q[0], q[1]), ("HIGH", q[1], 1e18)):
        s = [r for r in W if lo <= r["b69"] < hi]
        res["D4c"][f"tercile_{nm}"] = dict(
            n=len(s), b69_median=float(np.median([r["b69"] for r in s])),
            **{k: float(np.mean([r[k] for r in s])) for k in ("b6", "b4", "b7", "v", "rate",
                                                              "press")})
        t = res["D4c"][f"tercile_{nm}"]
        print(f"    {nm:4s} 6-9 Hz tercile  n={t['n']:3d}  band RMS {t['b69_median']:7.1f}  "
              f"b6 {t['b6']:.4f}  b4 {t['b4']:.4f}  b7 {t['b7']:.4f}  "
              f"v {t['v']:.2f}  |rate| {t['rate']:.1f}  press {t['press']:.3f}")
    for k in ("b6", "b4", "b7"):
        x = np.array([r[k] for r in W])
        rr = float(st.pearsonr(_presid(x, ctrl), _presid(y, ctrl))[0])
        null = []
        for _ in range(5000):
            p = RNG.permutation(len(bl))
            xs = np.empty_like(x)
            for s_, t_ in zip([pos[bl[i]] for i in p], [pos[b] for b in bl]):
                n_ = min(len(s_), len(t_))
                xs[t_[:n_]] = x[s_[:n_]]
                if len(t_) > n_:
                    xs[t_[n_:]] = x[s_[0]]
            null.append(st.pearsonr(_presid(xs, ctrl), _presid(y, ctrl))[0])
        null = np.abs(np.array(null))
        res["D4c"][k] = dict(partial_r=rr, block_perm_p=float(np.mean(null >= abs(rr))),
                             null_p95=float(np.percentile(null, 95)))
        z = res["D4c"][k]
        print(f"    {k}: partial r {rr:+.3f}   block-perm p {z['block_perm_p']:.4f}   "
              f"null 95% |r| <= {z['null_p95']:.3f}   "
              f"{'SURVIVES' if z['block_perm_p'] < 0.05 else 'NULL'}")

    (OUT / "v98_r81_score.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT/'v98_r81_score.json'}")
    return res


if __name__ == "__main__":
    main()
