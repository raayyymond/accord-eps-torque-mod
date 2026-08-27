#!/usr/bin/env python3
r"""SCORE ROUTE 82 = THE V99 FLIGHT.  Adapted from `score/v98_r81_score.py`; the statistics are the
pre-registered ones from `builds/v80_v107/build_v99_tva.py` and are NOT re-invented here.

🛑 EVERYTHING IS GATED ON THE PRE-REGISTERED IDENTITY RULE:
       b5 duty >= 0.999 over the whole route  AND  byte7[7:6] == 2 at duty 1.0000.
   IF IT FAILS THIS SCRIPT REFUSES TO PRINT THE READOUT.

Endpoints, verbatim from `builds/v80_v107/build_v99_tva.py`:
  E1   PRIMARY -- `b6` duty stratified by |wheel rate| in {0-5, 5-25, 25-60, 60+} deg/s.
       LEVER bands 0-5 and 5-25 must move; CONTROL bands 25-60 and 60+ must not.
       A change in ALL FOUR bins is an operating-point / route artefact, NOT the lever.
  E2   the within-symptom slope: partial Spearman( log(6-9 Hz band RMS), b6 window duty
       | speed, |wheel rate|, press ), 1.28 s windows, 5.12 s block-permutation null, 5,000 perms.
       V98 route 81: b6 r = -0.321 p = 0.0050, null 95 % |r| <= 0.221; b4 +0.087 and b7 +0.037 NULL.
  E3   overall engaged `b6` duty vs V98's 0.4235 [0.363, 0.484].
  POS-1 identity · POS-2 427 non-degenerate · POS-3 b3 constant · R5b arg(V) - arg(B') = +-180 deg.

⭐ PLUS the operator's OWN claim, which is NOT in the pre-registration and is labelled as such:
   *"I think it helped with the audible aspect of the grinding, though I'm not sure."*
   Scored on the higher bands 12-16 / 15-22 / 18-22 / 20-24 / 26-31 Hz.

🛑 SIGN CONVENTION: `angle(scipy.signal.csd(x, y)) = arg(Y) - arg(X)`; positive => y LEADS x.
   Self-checked against a known lag before any phase number is produced (`_phase_selfcheck`).
🛑 raw14 off-by-one: every bit series is `raw14_b4[row2raw14]`, asserted == `probe` at load.
   NEVER `(t, raw14_b4)`.
🛑 427's ZOH: 0x1AB is transmitted at 49.8 Hz, so a ZOH onto the 100 Hz row grid IMAGES 5-15 Hz
   onto 35-45 Hz.  **35-45 Hz IS VOID AS A CONTROL BAND ON 427.**  The negative control is 20-24 Hz.
🛑 CONTROLS BEFORE MEASUREMENTS: the split-half-by-block null is computed and PRINTED FIRST;
   every ratio is judged against THAT, not against 1.0.
🛑 The `steeringPressed` mask is `|STEER_TORQUE_SENSOR| > 1200` and it EXCLUDES the symptom regime
   (the operator produces the symptom by OVERRIDING).  Windows are 1.28 s, not 5.12 s.
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
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy import stats as st

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

# V99 byte-4 map, read off builds/v80_v107/build_v99_tva.py's PAYLOAD.  b5 is a HARD-WIRED 1.
M_B7, M_B6, M_B5, M_B4, M_B3 = 0x80, 0x40, 0x20, 0x10, 0x08

ROUTES = {"82": ("_scratch/cache/r82", "r82", "V99"),
          "81": ("_scratch/cache/r81", "r81", "V98"),
          "80": ("_scratch/cache/r80", "r80", "V97"),
          "7e": ("_scratch/cache/r7e", "r7e", "V96"),
          "7f": ("_scratch/cache/r7f", "r7f", "V96")}

# 6-9 Hz  = the felt micro-ratchet band (the pre-registered symptom band).
# 12-16 .. 26-31 = the operator's AUDIBLE claim.  20-24 is ALSO the stated negative control.
# 0.5-3 = the LKAS command band (must not move -- V88's null).
BANDS = {"0.5-3": (0.5, 3.0), "6-9": (6.0, 9.0), "12-16": (12.0, 16.0), "15-22": (15.0, 22.0),
         "18-22": (18.0, 22.0), "20-24": (20.0, 24.0), "26-31": (26.0, 31.0)}
AUDIBLE = ("12-16", "15-22", "18-22", "20-24", "26-31")
CONTROL_BAND = "20-24"
NPERSEG = 128            # 1.28 s @ 100 Hz -- override runs cannot support 5.12 s
HOP = 64
BLOCK_S = 5.12

# E1's PRE-REGISTERED |wheel rate| strata, deg/s.  LEVER vs CONTROL is fixed by the ARITHMETIC of
# 0xC40BC (600 -> 300 differ by 2.00x below 5.31 deg/s motor-referred, and by 1.000x above 10.61).
E1_BINS = [("0-5", 0.0, 5.0, "LEVER (full 2.00x dose)"),
           ("5-25", 5.0, 25.0, "LEVER (partial dose)"),
           ("25-60", 25.0, 60.0, "CONTROL (dose ratio == 1.000)"),
           ("60+", 60.0, 1e9, "CONTROL (dose ratio == 1.000)")]
V98_E1 = {"0-5": (894, 0.4911), "5-25": (2469, 0.3556),
          "25-60": (1781, 0.3268), "60+": (1447, 0.6164)}
V98_E3 = (0.4235, 0.363, 0.484)
V98_E2 = {"b6": -0.321, "b4": +0.087, "b7": +0.037, "null95": 0.221, "p": 0.0050}


# ==================================================================================================
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
    # 🛑 the off-by-one assertion.  If this fails the whole readout is 28 deg out at 7.79 Hz.
    assert np.all(b4 == (np.asarray(z["probe"], int) & 0xFF)), "raw14 map broken"
    d = dict(t=t, b4=b4, b7byte=b7b, build=build, route=r,
             eng=np.asarray(z["cc_lat"], float) > 0.5,
             v=np.asarray(z["cs_v"], float) * KMH,
             rate=np.asarray(z["cs_rate"], float),
             cs_ang=np.asarray(z["cs_ang"], float),
             co_req=np.asarray(z["co_req"], float),
             tq=np.asarray(z["tq"], float),
             cs_tq=np.asarray(z["cs_tq"], float),
             press=np.asarray(z["cs_press"], float) > 0.5,
             seg=np.asarray(z["seg"], int),
             ab_t=np.asarray(z["ab_t1ab"], float),
             ab_mt=np.asarray(z["ab_mt"], int))
    # 🛑 THE BIT MAP MOVED AT V98.  On V96/V97 (routes 7e/7f/80) `sign(gp-0x374c>>4)` is byte4 b6
    #    (0x40); on V98/V99 it is byte4 b4 (0x10) because b6/b5 were taken by the comparators.
    #    Using one mask for all routes silently reads a CONSTANT bit on the V96 routes and
    #    returns NaN phases -- which is exactly what a first pass of this script did.
    d["sign_6b70"] = (b4 & M_B7) != 0            # b7 -- byte-identical rung since V96
    d["b6_model_ge"] = (b4 & M_B6) != 0          # b6 -- byte-identical V98 -> V99
    d["b5"] = (b4 & M_B5) != 0                   # b5 -- V99: constant 1 · V98: REQUEST comparator
    d["sign_374c"] = (b4 & (M_B4 if r in ("82", "81") else 0x40)) != 0
    d["b3_pol"] = (b4 & M_B3) != 0
    d["ident"] = (b7b & 0xC0) >> 6
    # ZOH the 50 Hz 427 magnitude onto the 100 Hz row grid (last sample at or before t)
    j = np.clip(np.searchsorted(d["ab_t"], t, side="right") - 1, 0, len(d["ab_mt"]) - 1)
    d["mt_row"] = d["ab_mt"][j]
    # motor-accel proxy: 2nd difference of the column angle (NOT a motor signal; labelled as such)
    d["ang_accel"] = np.gradient(np.gradient(d["cs_ang"], d["t"]), d["t"])
    return d


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


def boot_circ_by_block(deg, blk, n=4000):
    deg, blk = np.asarray(deg, float), np.asarray(blk, int)
    ok = np.isfinite(deg)
    deg, blk = deg[ok], blk[ok]
    ub = np.unique(blk)
    if len(ub) < 2:
        return float("nan"), float("nan"), len(ub)
    b = [circ_mean(np.concatenate([deg[blk == e] for e in RNG.choice(ub, len(ub), True)]))
         for _ in range(n)]
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5)), len(ub)


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


def duty_ci(bits, sel, tau):
    """95 % CI on a duty, using the bit's OWN measured correlation time for n_eff.
    This is the pre-registered SE -- NOT a naive binomial, which would be ~5x too tight."""
    p = float(bits[sel].mean())
    T = float(sel.sum()) / FS
    if not (tau and tau > 0):
        return p, float("nan"), float("nan"), float("nan"), float("nan")
    neff = T / tau
    se = np.sqrt(max(p * (1 - p), 0.0) / neff) if neff > 0 else float("nan")
    return p, se, neff, p - 1.96 * se, p + 1.96 * se


# ==================================================================================================
#  WINDOWED BAND POWER  --  1.28 s, 50 % overlap, condition true on EVERY frame of the window
# ==================================================================================================
def windows(d, sel, min_s=1.28):
    out = []
    for ei, (a, b) in enumerate(episodes(sel, d["t"], min_s)):
        for s in range(a, b - NPERSEG + 1, HOP):
            out.append((ei, slice(s, s + NPERSEG)))
    return out


def band_table(d, sel, tag, sigkey="tq"):
    rows = []
    for ei, sl in windows(d, sel):
        r = dict(ep=ei, v=float(np.median(d["v"][sl])),
                 rate=float(np.median(np.abs(d["rate"][sl]))))
        for k, (lo, hi) in BANDS.items():
            r[k] = band_rms(d[sigkey][sl], FS, lo, hi, NPERSEG)
        rows.append(r)
    return dict(tag=tag, n_windows=len(rows),
                n_episodes=len(set(r["ep"] for r in rows)), rows=rows)


def geo_median(vals):
    v = np.asarray([x for x in vals if np.isfinite(x) and x > 0], float)
    return float(np.exp(np.median(np.log(v)))) if len(v) else float("nan")


V_EDGES = (0, 2, 5, 8, 12, 20)
R_EDGES = (0, 5, 25, 60, 1e9)


def _bin(r):
    v, rt = max(r["v"], 0.0), max(r["rate"], 0.0)
    iv = max(i for i, e in enumerate(V_EDGES[:-1]) if v >= e)
    ir = max(i for i, e in enumerate(R_EDGES[:-1]) if rt >= e)
    return iv, ir


def standardised_ratio(rowsA, rowsB, band, min_n=3):
    """Weighted geometric mean of the per-(speed x |rate|) cell A/B median ratio.
    Cells with no counterpart in the other arm are DROPPED, so the contrast is never carried
    by a regime only one arm visited."""
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
        detail[str(k)] = dict(nA=len(v["A"]), nB=len(v["B"]), ratio=float(ra))
        num += w * np.log(ra)
        den += w
    return (float(np.exp(num / den)) if den else float("nan")), detail


def blockify(T):
    per = int(round(BLOCK_S / (HOP / FS)))
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
    half-vs-half fold-ratio IS the resolution floor.  Judge every ratio against THAT, not 1.0."""
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
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(ba), len(bb)


def _presid(a, ctrl):
    A = np.column_stack([np.ones(len(a))] + [st.rankdata(c) for c in ctrl])
    ra = st.rankdata(a)
    return ra - A @ np.linalg.lstsq(A, ra, rcond=None)[0]


# ==================================================================================================
def main():
    res = {"sign_convention": "angle(csd(x,y)) = arg(Y) - arg(X); positive => y LEADS x",
           "raw14_pairing": "bits = raw14_b4[row2raw14], asserted == probe; SAFE pair (t, probe)"}
    print("=" * 98)
    print("  ROUTE 82 = THE V99 FLIGHT.   CONTROLS RUN BEFORE MEASUREMENTS.")
    print("=" * 98)
    res["selfcheck"] = _phase_selfcheck()

    D = {r: v for r, v in ((r, load(r)) for r in ROUTES) if v is not None}
    d = D["82"]
    n = len(d["t"])

    # ============================== GATE: IDENTITY =============================================
    print("\n=== POS-1  THE PRE-REGISTERED IDENTITY RULE (everything below is gated on it) ===")
    ih = {int(a): int(b) for a, b in zip(*np.unique(d["ident"], return_counts=True))}
    duty2, b5d = float((d["ident"] == 2).mean()), float(d["b5"].mean())
    ok = (duty2 >= 0.9999) and (b5d >= 0.999)
    res["POS1"] = dict(frames=n, ident_hist=ih, ident2_duty=duty2, b5_duty=b5d,
                       rule="b5 duty >= 0.999 AND byte7[7:6] == 2 at duty 1.0000", passes=bool(ok))
    print(f"  byte7[7:6] hist {ih}   duty(==2) = {duty2:.6f}")
    print(f"  b5 duty = {b5d:.6f}   (V98 measured 0.0022 on the byte-identical rung)")
    print(f"  ⇒ {'✅ IDENTITY PASSES -- V99 IS ON THE CAR' if ok else '🛑 IDENTITY FAILS'}")
    if not ok:
        print("  🛑 IF THE IDENTITY RULE FAILS, NOTHING IN THE READOUT MAY BE REPORTED.  STOPPING.")
        (OUT / "v99_r82_score.json").write_text(json.dumps(res, indent=1, default=float))
        return res

    # ============================== POS-2 / POS-3 ==============================================
    keep = d["mt_row"] != 1023                     # the pre-registered b6 latch exclusion
    res["POS2"] = dict(distinct=int(len(np.unique(d["ab_mt"]))), p99=float(np.percentile(d["ab_mt"], 99)),
                       max=int(d["ab_mt"].max()), frames=int(len(d["ab_mt"])),
                       eq1023_1ab=int((d["ab_mt"] == 1023).sum()),
                       excluded_rows=int((~keep).sum()),
                       passes=bool(len(np.unique(d["ab_mt"])) >= 20
                                   and np.percentile(d["ab_mt"], 99) >= 8))
    print(f"\n=== POS-2  427 non-degenerate: {res['POS2']['distinct']} distinct codes (>=20), "
          f"p99 {res['POS2']['p99']:.0f} (>=8), max {res['POS2']['max']}, "
          f"==1023 on {res['POS2']['eq1023_1ab']} frames ⇒ b6 exclusion removes "
          f"{res['POS2']['excluded_rows']} of {n:,} rows  ⇒ "
          f"{'✅ PASS' if res['POS2']['passes'] else '🛑 FAIL'}")
    b3 = d["b3_pol"]
    res["POS3"] = dict(duty=float(b3.mean()), transitions=int((np.diff(b3.astype(int)) != 0).sum()),
                       duty_engaged=float(b3[d["eng"]].mean()),
                       duty_manual=float(b3[~d["eng"]].mean()))
    print(f"=== POS-3  b3 duty {res['POS3']['duty']:.6f}, {res['POS3']['transitions']} transitions "
          f"⇒ gp-0x6752 CONSTANT and "
          f"{'NEGATIVE  ✅ (reproduces V98)' if res['POS3']['duty'] == 0 else 'see duty'}")

    # ============================== R5b ========================================================
    print("\n=== R5b  THE CONVERSE POSITIVE CONTROL -- arg(V) - arg(B') must be +-180 deg ===")
    print("    Reproduced to within 1 deg on routes 7e / 7f / 80 / 81.  b4 and b7 are byte-identical")
    print("    on V99, so this MUST reproduce a FIFTH time or the readout is VOID.")
    res["R5b"] = {}
    for r in ("82", "81", "80", "7e", "7f"):
        if r not in D:
            continue
        dd = D[r]
        sel = dd["eng"]
        if sel.sum() < 1024:
            continue
        rr = dd["rate"][sel]
        Bp = dd["sign_374c"][sel].astype(float)
        V = dd["sign_6b70"][sel].astype(float)
        e = {}
        for k, (x, y) in (("Bp_vs_rate", (rr, Bp)), ("V_vs_rate", (rr, V)), ("V_vs_Bp", (Bp, V))):
            p, c_ = welch_phase(x, y, FS, 1024, 6.0, 9.0)
            e[k] = dict(phase_deg=p, coherence=c_)
        res["R5b"][r] = dict(build=dd["build"], engaged_frames=int(sel.sum()), **e)
        print(f"  r{r} ({dd['build']:4s}) " + "   ".join(
            f"{k} {e[k]['phase_deg']:+7.2f} (coh {e[k]['coherence']:.3f})"
            for k in ("Bp_vs_rate", "V_vs_rate", "V_vs_Bp")))
    # 🛑 A POINT ESTIMATE CANNOT PASS OR FAIL A +-180 TEST WITHOUT A CI.  The prior routes were
    #    quoted as "within 1 deg" from single whole-engaged Welch estimates with NO error bar, so
    #    an invented tolerance would decide this on the analyst's arbitrary choice.  The verdict
    #    below is: does the BLOCK-BOOTSTRAP CI of arg(V)-arg(B') COVER +-180?
    print("\n  -- R5b with an ERROR BAR: 5.12 s windows, nperseg 128, circular mean, "
          "block-bootstrapped")
    for r in ("82", "81"):
        if r not in D:
            continue
        dd, sel, WIN = D[r], D[r]["eng"], 512
        ph, blks = [], []
        for ei, (a, b) in enumerate(episodes(sel, dd["t"], WIN / FS)):
            for bi, s in enumerate(range(a, b - WIN + 1, WIN // 2)):
                sl = slice(s, s + WIN)
                p, _c = welch_phase(dd["sign_374c"][sl].astype(float),
                                    dd["sign_6b70"][sl].astype(float), FS, 128, 6.0, 9.0)
                if np.isfinite(p):
                    ph.append(p); blks.append(ei * 1000 + bi)
        if not ph:
            continue
        m = circ_mean(ph)
        lo, hi, nb = boot_circ_by_block(ph, np.array(blks))
        # |180| coverage, handled on the circle: distance of the CI endpoints from +-180
        covers = bool(min(abs(abs(lo) - 180.0), abs(abs(hi) - 180.0)) <= 0
                      or (abs(lo) <= 180 <= abs(hi)) or (abs(hi) <= 180 <= abs(lo))
                      or abs(abs(m) - 180.0) <= max(abs(m - lo), abs(hi - m)))
        res["R5b"][f"{r}_windowed"] = dict(phase_deg=m, ci=[lo, hi], windows=len(ph),
                                           blocks=nb, covers_180=covers)
        print(f"     r{r} ({D[r]['build']:4s}) arg(V)-arg(B') = {m:+7.2f} deg "
              f"[{lo:+7.2f}, {hi:+7.2f}]  n={len(ph)} windows / {nb} blocks  "
              f"⇒ CI {'COVERS' if covers else 'EXCLUDES'} +-180")
    vb = res["R5b"]["82"]["V_vs_Bp"]["phase_deg"]
    wcov = res["R5b"].get("82_windowed", {}).get("covers_180", False)
    res["R5b"]["r82_pass"] = bool(wcov)
    res["R5b"]["prior_routes_point_estimates_deg"] = {
        "7e": -178.1, "7f": -178.1, "81": res["R5b"].get("81", {}).get(
            "V_vs_Bp", {}).get("phase_deg")}
    print(f"  ⇒ route 82 whole-engaged point estimate {vb:+.2f} deg; "
          f"windowed CI {'COVERS' if wcov else 'EXCLUDES'} +-180  ⇒ "
          f"{'✅ R5b REPRODUCES (5th route)' if wcov else '🛑 R5b DOES NOT REPRODUCE'}")

    # ============================== E3 =========================================================
    print("\n=== E3  OVERALL ENGAGED b6 DUTY  (CI from the bit's OWN measured correlation time) ===")
    res["E3"] = {}
    for nm, arr in (("b6", d["b6_model_ge"]), ("b4", d["sign_374c"]), ("b7", d["sign_6b70"])):
        tau = acf_tau(arr[d["eng"]].astype(float))
        p, se, neff, lo, hi = duty_ci(arr, d["eng"] & keep, tau)
        res["E3"][nm] = dict(tau_s=tau, n_eff=neff, duty=p, se=se, ci=[lo, hi])
        print(f"    {nm}: tau {tau:.3f} s   n_eff {neff:.0f}   duty {p:.4f}   SE {se:.4f}   "
              f"95% CI [{lo:.4f}, {hi:.4f}]")
    e3 = res["E3"]["b6"]
    res["E3"]["v98_reference"] = list(V98_E3)
    res["E3"]["overlaps_v98"] = bool(e3["ci"][0] <= V98_E3[2] and e3["ci"][1] >= V98_E3[1])
    print(f"    V98 route 81 reference: {V98_E3[0]:.4f} [{V98_E3[1]:.3f}, {V98_E3[2]:.3f}]"
          f"   ⇒ CIs {'OVERLAP' if res['E3']['overlaps_v98'] else 'DO NOT OVERLAP'}")

    # ---- engaged / manual contrast (V98: 0.4235 engaged vs 0.8041 manual)
    for nm, s in (("ENGAGED", d["eng"]), ("MANUAL", ~d["eng"]),
                  ("ENG+override", d["eng"] & d["press"]),
                  ("ENG+handsoff", d["eng"] & ~d["press"]),
                  ("MAN+handson", (~d["eng"]) & d["press"]),
                  ("MAN+handsoff", (~d["eng"]) & ~d["press"])):
        s = s & keep
        if not s.sum():
            continue
        res["E3"][f"duty_{nm}"] = dict(n=int(s.sum()), b6=float(d["b6_model_ge"][s].mean()),
                                       b7=float(d["sign_6b70"][s].mean()),
                                       b4=float(d["sign_374c"][s].mean()))
        z = res["E3"][f"duty_{nm}"]
        print(f"    {nm:14s} n={z['n']:6d}  b6 {z['b6']:.4f}  b7 {z['b7']:.4f}  b4 {z['b4']:.4f}")

    # ============================== E1  (PRIMARY) ==============================================
    print("\n" + "=" * 98)
    print("=== ⭐ E1  PRIMARY -- b6 duty by |wheel rate|.  THE LEVER'S OWN NULL-BY-CONSTRUCTION"
          " CONTROL")
    print("=" * 98)
    print("    LEVER bands (0-5, 5-25 deg/s) must MOVE.  CONTROL bands (25-60, 60+) must NOT.")
    print("    🛑 A change in ALL FOUR bins is an OPERATING-POINT / ROUTE ARTEFACT, not the lever.")
    print("    Prediction is ORDINAL, not bin-exact (gp-0x6abc is MOTOR rate; bins are COLUMN rate);")
    print("    expect ~10 % leak into the control bands from the 0xC40D0 EMA.")
    tau_b6 = acf_tau(d["b6_model_ge"][d["eng"]].astype(float))
    res["E1"] = dict(tau_b6_s=tau_b6, bins={})
    print(f"\n    (all CIs use the b6 bit's OWN measured tau = {tau_b6:.3f} s inside each stratum)")
    print(f"    {'bin deg/s':10s} {'role':30s} {'n':>6s} {'V98 n':>6s} {'V99 b6':>8s} "
          f"{'95% CI':>18s} {'V98 b6':>8s} {'delta':>8s}")
    for nm, lo, hi, role in E1_BINS:
        sel = d["eng"] & keep & (np.abs(d["rate"]) >= lo) & (np.abs(d["rate"]) < hi)
        if sel.sum() < 20:
            print(f"    {nm:10s} {role:30s} {int(sel.sum()):6d}   -- too few frames to score --")
            res["E1"]["bins"][nm] = dict(n=int(sel.sum()), role=role, duty=None)
            continue
        tau_l = acf_tau(d["b6_model_ge"][sel].astype(float))
        tau_use = tau_l if (tau_l and tau_l > 0) else tau_b6
        p, se, neff, clo, chi = duty_ci(d["b6_model_ge"], sel, tau_use)
        v98n, v98p = V98_E1[nm]
        res["E1"]["bins"][nm] = dict(n=int(sel.sum()), role=role, duty=p, se=se, ci=[clo, chi],
                                     tau_s=tau_use, n_eff=neff, v98_n=v98n, v98_duty=v98p,
                                     delta=p - v98p,
                                     v98_inside_ci=bool(clo <= v98p <= chi))
        print(f"    {nm:10s} {role:30s} {int(sel.sum()):6d} {v98n:6d} {p:8.4f} "
              f"[{clo:7.4f},{chi:7.4f}] {v98p:8.4f} {p - v98p:+8.4f}"
              f"  {'(V98 inside CI ⇒ NO MOVE)' if res['E1']['bins'][nm]['v98_inside_ci'] else '⇒ MOVED'}")

    moved = {k: (v.get("duty") is not None and not v["v98_inside_ci"])
             for k, v in res["E1"]["bins"].items()}
    lever_moved = [k for k in ("0-5", "5-25") if moved.get(k)]
    ctrl_moved = [k for k in ("25-60", "60+") if moved.get(k)]
    res["E1"]["moved"] = moved
    if len(ctrl_moved) == 2 and len(lever_moved) == 2:
        v = ("🛑 ALL FOUR BINS MOVED ⇒ OPERATING-POINT / ROUTE ARTEFACT, NOT THE LEVER. "
             "Reported as such, per the pre-registration.")
    elif lever_moved and not ctrl_moved:
        v = ("⭐ LEVER BANDS MOVED, CONTROL BANDS DID NOT ⇒ the pre-registered E1 signature.")
    elif not lever_moved and not ctrl_moved:
        v = ("NULL ON E1 -- no bin moved beyond its own sampling error.")
    else:
        v = (f"MIXED -- lever bands moved: {lever_moved or 'none'}; "
             f"control bands moved: {ctrl_moved or 'none'}.")
    res["E1"]["verdict"] = v
    print(f"\n    VERDICT: {v}")

    # ---- direct route-82-internal ordinal check: is b6 duty monotone decreasing in |rate|?
    print("\n    -- ORDINAL CHECK, WITHIN ROUTE 82 ONLY (no cross-build assumption):")
    print(f"       V99 b6 by bin: " + "  ".join(
        f"{k}:{res['E1']['bins'][k]['duty']:.4f}" for k, *_ in E1_BINS
        if res["E1"]["bins"][k]["duty"] is not None))
    print(f"       V98 b6 by bin: " + "  ".join(f"{k}:{V98_E1[k][1]:.4f}" for k, *_ in E1_BINS))

    # ------------------------------------------------------------------------------------------
    # ⭐ THE DIFFERENCE-IN-DIFFERENCES, and it is the statistic that MATTERS for E1.
    # All four raw deltas came out NEGATIVE, which is the signature of a ROUTE-WIDE OFFSET (a
    # different drive, a different operating point) sitting on top of any lever effect.  The
    # LEVER / CONTROL duty RATIO **within a route** cancels any such offset exactly, so it can be
    # compared across builds without assuming the two drives are matched.  Both arms are
    # bootstrapped over their OWN 5.12 s engaged blocks -- the same resampling unit used everywhere
    # else in this script.
    # ------------------------------------------------------------------------------------------
    print("\n    -- ⭐ DIFFERENCE-IN-DIFFERENCES (LEVER duty / CONTROL duty, WITHIN each route).")
    print("       All four raw deltas are NEGATIVE ⇒ a route-wide offset is present.  This ratio")
    print("       CANCELS it exactly, so it is the only E1 comparison that survives the offset.")

    def _e1_did(dd, kp, n=4000):
        sel_e = dd["eng"] & kp
        idx = np.where(sel_e)[0]
        # 5.12 s contiguous blocks inside engaged episodes
        blk = np.zeros(len(dd["t"]), int) - 1
        bid = 0
        for a, b in episodes(dd["eng"], dd["t"], 1.28):
            per = int(round(BLOCK_S * FS))
            for s in range(a, b, per):
                blk[s:min(s + per, b)] = bid
                bid += 1
        ub = np.unique(blk[idx])
        ub = ub[ub >= 0]
        rate = np.abs(dd["rate"])
        bits = dd["b6_model_ge"]

        def _duties(ii):
            o = {}
            for nm, lo_, hi_, _r in E1_BINS:
                m = ii[(rate[ii] >= lo_) & (rate[ii] < hi_)]
                o[nm] = float(bits[m].mean()) if len(m) >= 10 else np.nan
            return o

        pt = _duties(idx)
        boots = {k: [] for k in ("lever0_5_over_ctrl25_60", "lever5_25_over_ctrl25_60",
                                 "lever_pooled_over_ctrl_pooled")}
        for _ in range(n):
            pick = RNG.choice(ub, len(ub), True)
            ii = np.concatenate([idx[blk[idx] == b_] for b_ in pick])
            q = _duties(ii)
            lp = np.nanmean([q["0-5"], q["5-25"]])
            cp = np.nanmean([q["25-60"], q["60+"]])
            boots["lever0_5_over_ctrl25_60"].append(q["0-5"] / q["25-60"])
            boots["lever5_25_over_ctrl25_60"].append(q["5-25"] / q["25-60"])
            boots["lever_pooled_over_ctrl_pooled"].append(lp / cp)
        o = dict(point={}, ci={}, bins=pt)
        o["point"]["lever0_5_over_ctrl25_60"] = pt["0-5"] / pt["25-60"]
        o["point"]["lever5_25_over_ctrl25_60"] = pt["5-25"] / pt["25-60"]
        o["point"]["lever_pooled_over_ctrl_pooled"] = (
            np.nanmean([pt["0-5"], pt["5-25"]]) / np.nanmean([pt["25-60"], pt["60+"]]))
        for k, v in boots.items():
            v = np.array([x for x in v if np.isfinite(x)])
            o["ci"][k] = [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
        o["n_blocks"] = int(len(ub))
        return o

    res["E1"]["DiD"] = {}
    for r in ("82", "81"):
        if r not in D:
            continue
        dd = D[r]
        kp = dd["mt_row"] != 1023
        res["E1"]["DiD"][r] = _e1_did(dd, kp)
        z = res["E1"]["DiD"][r]
        print(f"       r{r} ({dd['build']:4s}, {z['n_blocks']} engaged blocks): " + "   ".join(
            f"{k.replace('_over_', '/')} {z['point'][k]:.3f} "
            f"[{z['ci'][k][0]:.3f},{z['ci'][k][1]:.3f}]" for k in z["point"]))
    if "82" in res["E1"]["DiD"] and "81" in res["E1"]["DiD"]:
        A, B = res["E1"]["DiD"]["82"], res["E1"]["DiD"]["81"]
        did_ok = {}
        for k in A["point"]:
            disj = (A["ci"][k][1] < B["ci"][k][0]) or (B["ci"][k][1] < A["ci"][k][0])
            did_ok[k] = bool(disj)
            print(f"       ⇒ {k}: V99 {A['point'][k]:.3f} vs V98 {B['point'][k]:.3f}  "
                  f"CIs {'DISJOINT ⇒ the lever/control balance MOVED' if disj else 'OVERLAP ⇒ NOT distinguishable'}")
        res["E1"]["DiD"]["verdict"] = did_ok

    # ============================== E2 =========================================================
    print("\n" + "=" * 98)
    print("=== ⭐ E2  THE WITHIN-SYMPTOM SLOPE.  Byte-identical rung to the one that produced")
    print("    V98's b6 r = -0.321, p = 0.0050, null 95 % |r| <= 0.221.")
    print("=" * 98)
    print("    Partial Spearman( log(6-9 Hz column-torque band RMS), bit window duty "
          "| speed, |wheel rate|, press )")
    print("    1.28 s windows (override runs cannot support 5.12 s), 5.12 s BLOCK-PERMUTATION null,")
    print("    5,000 permutations.  b4 and b7 are the CONTROLS and must stay NULL.")
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
    y = np.log(np.array([r["b69"] for r in W]))
    ctrl = [np.array([r[k] for r in W]) for k in ("v", "rate", "press")]
    bl = sorted(set(r["blk"] for r in W))
    pos = {b: [i for i, r in enumerate(W) if r["blk"] == b] for b in bl}
    res["E2"] = {"n_windows": len(W), "n_blocks": len(bl),
                 "n_episodes": len(set(r["ep"] for r in W))}
    print(f"\n    exposure: {len(W)} windows, {len(bl)} blocks, {res['E2']['n_episodes']} episodes"
          f"   (V98 route 81 had 6,591 engaged frames)")
    q = np.percentile([r["b69"] for r in W], [33, 67])
    for nm, lo, hi in (("LOW", -1, q[0]), ("MID", q[0], q[1]), ("HIGH", q[1], 1e18)):
        s = [r for r in W if lo <= r["b69"] < hi]
        res["E2"][f"tercile_{nm}"] = dict(
            n=len(s), b69_median=float(np.median([r["b69"] for r in s])),
            **{k: float(np.mean([r[k] for r in s])) for k in ("b6", "b4", "b7", "v", "rate",
                                                              "press")})
        t = res["E2"][f"tercile_{nm}"]
        print(f"    {nm:4s} 6-9 Hz tercile  n={t['n']:3d}  band RMS {t['b69_median']:7.1f}  "
              f"b6 {t['b6']:.4f}  b4 {t['b4']:.4f}  b7 {t['b7']:.4f}  "
              f"v {t['v']:.2f}  |rate| {t['rate']:.1f}  press {t['press']:.3f}")
    print()
    for k in ("b6", "b4", "b7"):
        x = np.array([r[k] for r in W])
        if np.std(x) == 0:
            res["E2"][k] = dict(partial_r=None, note="bit is constant on this route")
            print(f"    {k}: CONSTANT on this route -- no slope defined")
            continue
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
        res["E2"][k] = dict(partial_r=rr, block_perm_p=float(np.mean(null >= abs(rr))),
                            null_p95=float(np.percentile(null, 95)),
                            v98_r=V98_E2[k],
                            survives=bool(np.mean(null >= abs(rr)) < 0.05))
        z = res["E2"][k]
        print(f"    {k}: partial r {rr:+.3f}   block-perm p {z['block_perm_p']:.4f}   "
              f"null 95% |r| <= {z['null_p95']:.3f}   "
              f"{'SURVIVES' if z['survives'] else 'NULL'}"
              f"      [V98 r {V98_E2[k]:+.3f}]")

    # ============================== THE OPERATOR'S AUDIBLE CLAIM ===============================
    print("\n" + "=" * 98)
    print("=== ⭐ THE OPERATOR'S OWN CLAIM (NOT PRE-REGISTERED, labelled as such):")
    print("    \"I think it helped with the audible aspect of the grinding, though I'm not sure.\"")
    print("=" * 98)
    print("    🛑 CONTROL FIRST: the WITHIN-ROUTE split-half noise floor of the SAME statistic is")
    print("       printed BEFORE any ratio.  Any ratio inside its own floor CANNOT be distinguished")
    print("       from noise and is NOT headlined.")
    SIG = {"tq_0x18F_column": "tq", "angle_deg": "cs_ang",
           "ang_accel_proxy": "ang_accel", "mt427_gp6b70": "mt427"}
    # 🛑 SIGN DEFECT, FOUND AND FIXED 2026-08-13.  427 carries the MAGNITUDE of `gp-0x6b70`; its
    # SIGN is byte4 b7 (`d["sign_6b70"]`), computed at :118 and applied elsewhere in this file but
    # NOT here.  Rectifying a signed oscillation folds every negative half-cycle up, doubling the
    # apparent frequency and inflating the 6-9 Hz band RMS.  MEASURED cost on the row that scores
    # the operator's audible report: within-route ENG/MAN 3.361 -> 19.431 on r82 (5.78x) and
    # 3.933 -> 18.509 on r81 (4.71x).  Regression introduced at V98 (`score/v98_r81_score.py:541`) and
    # inherited here; six earlier scorers handled the sign correctly, so it is NOT a replicating
    # class.  ⇒ this is the design law's "sign bit paired with a magnitude channel" with a price
    # tag, and it makes V100's b7 MANDATORY rather than stylistic.
    d["mt427"] = d["mt_row"].astype(float) * (64.0 / 5.0) * np.where(d["sign_6b70"], -1.0, 1.0)
    res["AUDIBLE"] = {}

    # ---- the within-drive LKAS-off arm on route 82 itself (PREFERRED over anything cross-build)
    arms82 = {"ENG_all": d["eng"], "MAN_all": ~d["eng"],
              "ENG_handson": d["eng"] & d["press"], "MAN_handson": (~d["eng"]) & d["press"]}
    for sname, key in SIG.items():
        res["AUDIBLE"][sname] = {}
        Tb = {k: blockify(band_table(d, s, k, key)) for k, s in arms82.items()}
        print(f"\n  ---- {sname}  |  WITHIN-DRIVE route 82 ENGAGED vs LKAS-OFF (the preferred arm)")
        for k, rows in Tb.items():
            if rows:
                print(f"       {k:12s} win {len(rows):4d} blk {len(set(r['blk'] for r in rows)):3d}"
                      f"   " + "  ".join(f"{b} {geo_median([r[b] for r in rows]):8.2f}"
                                         for b in AUDIBLE))
        for b in BANDS:
            fl = split_half_null(Tb["ENG_all"], b)
            ra, _ = standardised_ratio(Tb["ENG_all"], Tb["MAN_all"], b)
            lo, hi, na, nb = boot_ratio(Tb["ENG_all"], Tb["MAN_all"], b)
            res["AUDIBLE"][sname][f"within82_ENG_over_MAN_{b}"] = dict(
                ratio=ra, ci=[lo, hi], floor_p50=fl.get("floor_p50"), floor_p95=fl.get("floor_p95"))
        print(f"       {'band':8s} {'ENG/MAN':>9s} {'block-boot CI':>18s} "
              f"{'split-half floor p50/p95':>26s}  verdict")
        for b in BANDS:
            z = res["AUDIBLE"][sname][f"within82_ENG_over_MAN_{b}"]
            ra, lo, hi = z["ratio"], z["ci"][0], z["ci"][1]
            f50, f95 = z["floor_p50"], z["floor_p95"]
            fold = ra if (np.isfinite(ra) and ra >= 1) else (1 / ra if np.isfinite(ra) and ra > 0
                                                             else float("nan"))
            vd = "--"
            if np.isfinite(fold) and f95:
                vd = ("cannot be distinguished from noise" if fold <= f95
                      else "exceeds its own within-route floor")
            ci = f"[{lo:6.2f},{hi:6.2f}]" if lo is not None else "[UNDEFINED]"
            tag = "  <-- NEGATIVE CONTROL" if b == CONTROL_BAND else ""
            print(f"       {b:8s} {ra:9.3f} {ci:>18s} "
                  f"{(f'{f50:.2f}x / {f95:.2f}x' if f95 else 'n/a'):>26s}  {vd}{tag}")

    # ---- the CROSS-BUILD ratio the operator asked for.  UNBUILDABLE endpoint; reported WITH
    #      the within-route split-half noise floor of the SAME statistic beside it.
    if "81" in D:
        print("\n  ---- 🛑 CROSS-BUILD route 82 (V99) / route 81 (V98), ENGAGED.")
        print("       `builds/v80_v107/build_v99_tva.py` lists cross-build band ratios as an UNBUILDABLE ENDPOINT")
        print("       at this exposure.  Computed because the operator asked.  Judge EVERY number")
        print("       against the within-route split-half floor printed beside it, NOT against 1.0.")
        d81 = D["81"]
        # 🛑 same sign fix as above -- route 81's arm of the CROSS-BUILD comparison.
        d81["mt427"] = (d81["mt_row"].astype(float) * (64.0 / 5.0)
                        * np.where(d81["sign_6b70"], -1.0, 1.0))
        d81["ang_accel"] = np.gradient(np.gradient(d81["cs_ang"], d81["t"]), d81["t"])
        res["CROSSBUILD"] = {}
        for sname, key in SIG.items():
            A = blockify(band_table(d, d["eng"], "r82_ENG", key))
            B = blockify(band_table(d81, d81["eng"], "r81_ENG", key))
            res["CROSSBUILD"][sname] = {}
            print(f"\n       {sname}   (r82 win {len(A)} / r81 win {len(B)})")
            print(f"       {'band':8s} {'r82/r81':>9s} {'block-boot CI':>18s} "
                  f"{'r82 floor p95':>14s} {'r81 floor p95':>14s}  verdict")
            for b in BANDS:
                ra, _ = standardised_ratio(A, B, b)
                lo, hi, na, nb = boot_ratio(A, B, b)
                fa, fb = split_half_null(A, b), split_half_null(B, b)
                f95 = max(x for x in (fa.get("floor_p95") or 0, fb.get("floor_p95") or 0))
                fold = (ra if (np.isfinite(ra) and ra >= 1)
                        else (1 / ra if np.isfinite(ra) and ra > 0 else float("nan")))
                vd = "--"
                if np.isfinite(fold) and f95:
                    vd = ("cannot be distinguished from noise" if fold <= f95
                          else "exceeds both within-route floors")
                res["CROSSBUILD"][sname][b] = dict(ratio=ra, ci=[lo, hi],
                                                   floor95_r82=fa.get("floor_p95"),
                                                   floor95_r81=fb.get("floor_p95"), verdict=vd)
                ci = f"[{lo:6.2f},{hi:6.2f}]" if lo is not None else "[UNDEFINED]"
                print(f"       {b:8s} {ra:9.3f} {ci:>18s} "
                      f"{(fa.get('floor_p95') or float('nan')):14.2f} "
                      f"{(fb.get('floor_p95') or float('nan')):14.2f}  {vd}")

    # ============================== ⭐ THE ACOUSTIC CHANNEL ====================================
    # The operator's claim is about the AUDIBLE aspect.  The rlog carries a 16 kHz microphone
    # (`rawAudioData`) that this kit has never used.  A cabin mic cannot hear 8 Hz, so the audible
    # signature of a mechanical ratchet is a 6-31 Hz AMPLITUDE MODULATION of a broadband rasp.
    # `decode/extract_r82_audio.py` builds the per-band envelope on the SAME 100 Hz grid, so every band
    # statistic above applies to it unchanged.
    print("\n" + "=" * 98)
    print("=== ⭐ THE ACOUSTIC CHANNEL -- 16 kHz cabin microphone (rawAudioData).  NEW INSTRUMENT.")
    print("=" * 98)
    res["ACOUSTIC"] = {}
    audio = {}
    for r in ("82", "81"):
        f = AN / ROUTES[r][0] / f"{ROUTES[r][1]}_audio.npz"
        if f.exists():
            audio[r] = np.load(f, allow_pickle=True)
    if "82" not in audio:
        print("    (no audio cache -- run `python decode/extract_r82_audio.py 82 81` first)")
    else:
        print("    ⚠ CONFOUNDS, stated and NOT argued away: cabin mic, so road / wind / HVAC /")
        print("      chime noise and possible AGC.  Speed-matching is mandatory; the WITHIN-DRIVE")
        print("      LKAS-off arm is the only clean comparison this instrument supports.")
        AB = [k for k in audio["82"].files if k.startswith("a") and k[1].isdigit()]
        for r, z in audio.items():
            dd = D[r]
            ta = np.asarray(z["t"], float)
            j = np.clip(np.searchsorted(ta, dd["t"], side="right") - 1, 0, len(ta) - 1)
            for k in AB:
                dd["AU_" + k] = np.asarray(z[k], float)[j]
            dd["AU_valid"] = np.isfinite(dd["AU_" + AB[0]])
            print(f"    r{r} ({dd['build']}): audio grid {len(ta):,} @ 100 Hz, coverage "
                  f"{100*float(z['coverage'][0]):.1f} %, rows with valid audio "
                  f"{100*dd['AU_valid'].mean():.1f} %, soundPressureWeightedDb p50 "
                  f"{np.nanmedian(z['sp_db']):.1f}")

        MB = ("6-9", "12-16", "18-22", "20-24", "26-31")

        print("\n    ---- (1) ⭐ MODULATION SPECTRUM of the acoustic envelope, WITHIN-DRIVE")
        print("         route 82 ENGAGED vs LKAS-OFF.  A ~8 Hz ratchet MODULATES a broadband rasp;")
        print("         it does not radiate at 8 Hz.  fl = within-arm split-half floor p95.")
        for k in AB:
            dd = dict(d)
            dd[k] = d["AU_" + k]
            va = d["AU_valid"]
            TA = blockify(band_table(dd, d["eng"] & va, "ENG", k))
            TM = blockify(band_table(dd, (~d["eng"]) & va, "MAN", k))
            if not (TA and TM):
                continue
            res["ACOUSTIC"].setdefault(k, {})
            line = f"       {k:9s} ENG/MAN:"
            for b in MB:
                ra, _ = standardised_ratio(TA, TM, b)
                lo, hi, _, _ = boot_ratio(TA, TM, b)
                f95 = split_half_null(TA, b).get("floor_p95")
                fold = (ra if (np.isfinite(ra) and ra >= 1)
                        else (1 / ra if np.isfinite(ra) and ra > 0 else float("nan")))
                vd = ("noise" if (np.isfinite(fold) and f95 and fold <= f95) else "EXCEEDS")
                res["ACOUSTIC"][k][f"within82_ENG_over_MAN_{b}"] = dict(
                    ratio=ra, ci=[lo, hi], floor_p95=f95, verdict=vd)
                line += f"  {b} {ra:5.2f}(fl {f95 if f95 else float('nan'):.2f},{vd})"
            print(line)

        if "81" in audio:
            print("\n    ---- (2) 🛑 CROSS-BUILD acoustic, r82 (V99) / r81 (V98), ENGAGED.")
            print("         UNBUILDABLE endpoint per builds/v80_v107/build_v99_tva.py.  Mic gain / AGC / HVAC /")
            print("         windows are NOT controlled across drives.  Judge against the floors.")
            d81 = D["81"]
            for k in AB:
                da, db_ = dict(d), dict(d81)
                da[k], db_[k] = d["AU_" + k], d81["AU_" + k]
                A = blockify(band_table(da, d["eng"] & d["AU_valid"], "A", k))
                B = blockify(band_table(db_, d81["eng"] & d81["AU_valid"], "B", k))
                if not (A and B):
                    continue
                res["ACOUSTIC"].setdefault(k, {})
                line = f"       {k:9s} r82/r81:"
                for b in MB:
                    ra, _ = standardised_ratio(A, B, b)
                    lo, hi, _, _ = boot_ratio(A, B, b)
                    fa, fb = split_half_null(A, b), split_half_null(B, b)
                    f95 = max(x for x in (fa.get("floor_p95") or 0, fb.get("floor_p95") or 0))
                    fold = (ra if (np.isfinite(ra) and ra >= 1)
                            else (1 / ra if np.isfinite(ra) and ra > 0 else float("nan")))
                    vd = ("noise" if (np.isfinite(fold) and f95 and fold <= f95) else "EXCEEDS")
                    res["ACOUSTIC"][k][f"cross_r82_over_r81_{b}"] = dict(
                        ratio=ra, ci=[lo, hi], floor95=f95, verdict=vd)
                    line += f"  {b} {ra:5.2f}(fl {f95:.2f},{vd})"
                print(line)

            print("\n    ---- (3) RAW acoustic LEVEL (envelope median), the bluntest read")
            print(f"       {'band':9s} {'r82 ENG':>10s} {'r81 ENG':>10s} {'r82 MAN':>10s} "
                  f"{'r81 MAN':>10s} {'ENG r82/r81':>13s} {'ENG/MAN r82':>12s} "
                  f"{'ENG/MAN r81':>12s}")
            for k in AB:
                vals = {}
                for r in ("82", "81"):
                    dd = D[r]
                    for nm, sel in (("ENG", dd["eng"]), ("MAN", ~dd["eng"])):
                        m = sel & dd["AU_valid"]
                        vals[(r, nm)] = (float(np.nanmedian(dd["AU_" + k][m])) if m.sum()
                                         else float("nan"))
                rr = vals[("82", "ENG")] / vals[("81", "ENG")]
                res["ACOUSTIC"].setdefault(k, {})["level_medians"] = {
                    f"{r}_{nm}": vals[(r, nm)] for r, nm in vals}
                res["ACOUSTIC"][k]["level_ratio_ENG_r82_over_r81"] = rr
                print(f"       {k:9s} {vals[('82','ENG')]:10.2f} {vals[('81','ENG')]:10.2f} "
                      f"{vals[('82','MAN')]:10.2f} {vals[('81','MAN')]:10.2f} {rr:13.3f} "
                      f"{vals[('82','ENG')]/vals[('82','MAN')]:12.3f} "
                      f"{vals[('81','ENG')]/vals[('81','MAN')]:12.3f}")

        # ---- (4) 🛑 THE INSTRUMENT'S OWN POSITIVE CONTROLS.  A cross-build NULL on a channel
        #      with no demonstrated positive control is UNINTERPRETABLE (V64 / V68 / V92).  Two
        #      controls are run, both WITHIN route 82.
        print("\n    ---- (4) 🛑 POSITIVE CONTROLS FOR THE MICROPHONE ITSELF")
        print("         (a) LIVENESS: does the envelope track vehicle speed?  Road noise must.")
        res["ACOUSTIC"]["controls"] = {}
        for k in AB:
            m = d["AU_valid"] & (d["v"] > 0.5)
            rho = float(st.spearmanr(d["v"][m], d["AU_" + k][m])[0])
            res["ACOUSTIC"]["controls"][f"speed_rho_{k}"] = rho
            print(f"         {k:9s} Spearman(speed, envelope) = {rho:+.3f}")
        print("         (b) ⭐ COUPLING TO THE MECHANICAL SYMPTOM: does the audible modulation")
        print("             co-vary with the 6-9 Hz COLUMN-TORQUE band during engagement?")
        print("             Partial Spearman | speed, |rate|, press; 5.12 s block-permutation null.")
        va = d["AU_valid"]
        WA = []
        for ei, sl in windows(d, d["eng"] & va):
            row = dict(ep=ei, b69=band_rms(d["tq"][sl], FS, 6.0, 9.0, NPERSEG),
                       v=float(np.median(d["v"][sl])),
                       rate=float(np.median(np.abs(d["rate"][sl]))),
                       press=float(d["press"][sl].mean()))
            for k in AB:
                for bn in ("6-9", "12-16", "18-22"):
                    lo_, hi_ = BANDS[bn]
                    row[f"{k}|{bn}"] = band_rms(d["AU_" + k][sl], FS, lo_, hi_, NPERSEG)
            WA.append(row)
        per = int(round(BLOCK_S / (HOP / FS)))
        for ei in sorted(set(r["ep"] for r in WA)):
            for j, i in enumerate([i for i, r in enumerate(WA) if r["ep"] == ei]):
                WA[i]["blk"] = (ei, j // per)
        if len(WA) >= 20:
            ya = np.log(np.array([r["b69"] for r in WA]))
            ca = [np.array([r[k] for r in WA]) for k in ("v", "rate", "press")]
            bla = sorted(set(r["blk"] for r in WA))
            posa = {b: [i for i, r in enumerate(WA) if r["blk"] == b] for b in bla}
            print(f"         ({len(WA)} engaged windows with valid audio, {len(bla)} blocks)")
            for k in AB:
                line = f"         {k:9s}"
                for bn in ("6-9", "12-16", "18-22"):
                    x = np.array([r[f"{k}|{bn}"] for r in WA])
                    if not np.all(np.isfinite(x)) or np.std(x) == 0:
                        line += f"  {bn} n/a"
                        continue
                    x = np.log(np.maximum(x, 1e-9))
                    rr = float(st.pearsonr(_presid(x, ca), _presid(ya, ca))[0])
                    null = []
                    for _ in range(2000):
                        p = RNG.permutation(len(bla))
                        xs = np.empty_like(x)
                        for s_, t_ in zip([posa[bla[i]] for i in p], [posa[b] for b in bla]):
                            n_ = min(len(s_), len(t_))
                            xs[t_[:n_]] = x[s_[:n_]]
                            if len(t_) > n_:
                                xs[t_[n_:]] = x[s_[0]]
                        null.append(st.pearsonr(_presid(xs, ca), _presid(ya, ca))[0])
                    null = np.abs(np.array(null))
                    pv = float(np.mean(null >= abs(rr)))
                    res["ACOUSTIC"]["controls"][f"coupling_{k}_{bn}"] = dict(
                        partial_r=rr, p=pv, null_p95=float(np.percentile(null, 95)))
                    line += (f"  {bn} r{rr:+.3f} p{pv:.3f}"
                             f"{'*' if pv < 0.05 else ' '}")
                print(line)

    (OUT / "v99_r82_score.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT/'v99_r82_score.json'}")
    return res


if __name__ == "__main__":
    main()
