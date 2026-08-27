#!/usr/bin/env python3
"""D4 -- THE MACRO RATCHET: the first instrument in this kit built for it.

The operator has settled the naming: **MICRO == the 7.79 Hz line** (measured, still present,
unattenuated -- studies/sessions/r59/d4_r59_ratchet.py); **MACRO == a separate, larger, hard-turn-recovery symptom that
V72 fixed.** Nobody has measured MACRO because nobody knew to look for it separately. V42 was
CONFIRMED on-car against a ~10 s hard-turn recovery ratchet, flagged in `docs/specs/design/V72-DESIGN.md` s0.1 as
"a DIFFERENT symptom from the current 7.79 Hz one."

🛑 THREE DESIGN DECISIONS, EACH MADE TO AVOID A RECORDED ERROR.

1. EVENTS, NOT WINDOWS. A 2.56 s window cannot represent a ~10 s recovery. Events are detected on
   the ANGLE trajectory: a peak >= PEAK_DEG unwinding to <= LO_DEG within [MIN_S, MAX_S].

2. DO NOT ASSUME 7.8 Hz -- SWEEP. The band is swept 0.5-30 Hz on BOTH the torque and the column
   rate, and an APERIODIC family is measured beside it, because "ratcheting" may be stick-slip
   rather than a line. The literal reading of the word is the primary instrument:
       STEPS  -- during the unwind, how many times does the return velocity stall and resume?
                 A smooth return has 0; a ratchet has one per step. This is what the driver feels.
       ROUGHNESS -- total variation of the return velocity / its peak, per second.
   A spectral null with a STEPS effect would mean the symptom is aperiodic, and vice versa.

3. THE CONTROL POPULATION IS PRE-DECLARED. Every statistic is also computed on NON-recovery engaged
   windows from the same routes. If V72 differs from the corpus on the control too, the "fix" is a
   route/driver difference, not a lever.

⚠ EXPOSURE IS REPORTED FOR EVERY CELL. Empty is not null.

Writes `_scratch/out/_d4_macro.json`.
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

PEAK_DEG, LO_DEG = 120.0, 30.0
MIN_S, MAX_S = 0.8, 15.0
BANDS = {"0.5-1": (0.5, 1.0), "1-2": (1.0, 2.0), "2-4": (2.0, 4.0), "4-6": (4.0, 6.0),
         "6-9": (6.0, 9.0), "9-12": (9.0, 12.0), "12-18": (12.0, 18.0), "18-22": (18.0, 22.0),
         "24-28": (24.0, 28.0)}
OUT = {}
RNG = np.random.default_rng(20260805)

# `r26x` = the DELIVERED r26 (gain_A) high-rate multiplier at creep -- STATE.md's two-lane table.
# This is the axis Lever A moves and the one a dose-response must be read on.
ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], [], 1.000),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), [], 2.000),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), [], 0.250),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), [], 1.000),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0], 1.000),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11], 2.000),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15], 1.500),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14], 0.250),
}
NEW = "V72 r59"
QUARTET = ["V70 r50", "V69 r4f", "V62 r37", "V59 r2c"]


def hdr(s):
    print("\n" + "=" * 126 + f"\n{s}\n" + "=" * 126)


def find_events(aa, fs):
    """Unwind events: a peak >= PEAK_DEG falling to <= LO_DEG. Returns (i_peak, i_end) pairs."""
    lo = aa <= LO_DEG
    cross = np.flatnonzero((~lo[:-1]) & lo[1:]) + 1
    out, last = [], -1
    for c in cross:
        j = c
        # walk back to the local maximum that started this descent
        while j > 0 and aa[j - 1] >= aa[j]:
            j -= 1
        # tolerate small upward wiggles: keep climbing while the running max improves
        k, best = j, aa[j]
        while k > 0 and (c - k) / fs < MAX_S:
            if aa[k - 1] >= best:
                best, j = aa[k - 1], k - 1
            elif best - aa[k - 1] > 25.0:
                break
            k -= 1
        dur = (c - j) / fs
        if aa[j] >= PEAK_DEG and MIN_S <= dur <= MAX_S and j > last:
            out.append((j, c))
            last = c
    return out


def steps_and_roughness(aa, fs, i0, i1):
    """STEPS = stalls in the return velocity; ROUGHNESS = TV(v)/peak(v) per second."""
    seg = aa[i0:i1]
    if len(seg) < 12:
        return np.nan, np.nan, np.nan
    v = -np.gradient(seg) * fs                        # return velocity, deg/s, positive = unwinding
    # 5-sample smoothing so single-sample noise is not a step
    k = np.ones(5) / 5.0
    v = np.convolve(v, k, mode="same")
    vmax = float(np.max(v))
    if vmax <= 1e-6:
        return np.nan, np.nan, np.nan
    lo_thr, hi_thr = 0.25 * vmax, 0.50 * vmax
    steps, armed = 0, False
    for x in v:
        if x < lo_thr:
            armed = True
        elif armed and x > hi_thr:
            steps += 1
            armed = False
    dur = (i1 - i0) / fs
    tv = float(np.sum(np.abs(np.diff(v))))
    return steps / dur, tv / (vmax * dur), dur


def scan(cache, pfx, segs, skip, tag):
    ev, ctl = [], []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        aa = np.abs(np.asarray(d["ang"], float))
        rc = np.asarray(d["rate_c"], float)
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        eff = np.abs(sustained(tq, fs))
        envt = {k: band_envelope(tq, fs, *b) for k, b in BANDS.items()}
        envr = {k: band_envelope(rc, fs, *b) for k, b in BANDS.items()}
        for i0, i1 in find_events(aa, fs):
            st, rg, dur = steps_and_roughness(aa, fs, i0, i1)
            if not np.isfinite(st):
                continue
            w = slice(i0, i1)
            r = dict(tag=tag, seg=int(s), t0=float(d["t"][i0]), dur=dur, steps=st, rough=rg,
                     peak=float(aa[i0]), v=float(v[w].mean()), lat=float(lat[w].mean()),
                     eff=float(np.median(eff[w])), tqmax=float(np.abs(tq[w]).max()),
                     ep=(tag, int(s), i0 // 6000))
            for k in BANDS:
                r["t_" + k] = float(np.percentile(envt[k][w], 99))
                r["r_" + k] = float(np.percentile(envr[k][w], 99))
            ev.append(r)
        # pre-declared CONTROL: engaged windows that are NOT recoveries, same routes
        n = 256
        inev = np.zeros(len(aa), bool)
        for i0, i1 in find_events(aa, fs):
            inev[i0:i1] = True
        for i in range(0, len(aa) - n + 1, n):
            w = slice(i, i + n)
            if inev[w].any() or not lat[w].all():
                continue
            st, rg, _ = steps_and_roughness(aa, fs, i, i + n)
            c = dict(tag=tag, seg=int(s), steps=st, rough=rg, v=float(v[w].mean()))
            for k in BANDS:
                c["t_" + k] = float(np.percentile(envt[k][w], 99))
            ctl.append(c)
    return ev, ctl


EV, CTL = {}, {}
for t, (c, p, s, sk, _) in ROUTES.items():
    EV[t], CTL[t] = scan(c, p, s, sk, t)

# ================================================================ 1. exposure =====================
hdr("1.  EXPOSURE -- unwind events per route. 🛑 EMPTY IS NOT NULL: read this before any verdict.\n"
    f"    event = |angle| peak >= {PEAK_DEG:.0f} deg unwinding to <= {LO_DEG:.0f} deg in "
    f"{MIN_S}-{MAX_S} s.")
print(f"   {'route':10s} {'r26x':>5s} | {'events':>7s} {'secs':>7s} {'med dur':>8s} "
      f"{'med peak':>9s} {'eng':>6s} {'manual':>7s} {'med v':>6s} {'ctl win':>8s}")
for tag in ROUTES:
    e = EV[tag]
    if not e:
        print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} | {0:>7d}  (no events)")
        continue
    dur = np.array([r["dur"] for r in e])
    ne = sum(1 for r in e if r["lat"] > 0.5)
    print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} | {len(e):>7d} {dur.sum():>7.1f} "
          f"{np.median(dur):>8.2f} {np.median([r['peak'] for r in e]):>9.0f} {ne:>6d} "
          f"{len(e) - ne:>7d} {np.median([r['v'] for r in e]):>6.2f} {len(CTL[tag]):>8d}")
OUT["exposure"] = {t: dict(n=len(EV[t]), secs=float(sum(r["dur"] for r in EV[t])),
                           n_eng=int(sum(1 for r in EV[t] if r["lat"] > 0.5)),
                           n_ctl=len(CTL[t])) for t in ROUTES}

# ================================================================ 2. the aperiodic instrument =====
hdr("2.  ★★★ THE LITERAL INSTRUMENT -- does the wheel come back in STEPS?\n"
    "    STEPS/s = stalls in the return velocity (drops < 25% of peak, resumes > 50%).\n"
    "    ROUGHNESS = total variation of the return velocity / (peak x duration).")


def bootmed(vals, eps, nb=4000):
    vals, eps = np.asarray(vals, float), np.asarray(eps)
    m = np.isfinite(vals)
    vals, eps = vals[m], eps[m]
    if len(vals) < 3:
        return np.nan, np.nan, np.nan
    u = np.unique(eps)
    if len(u) < 2:
        return float(np.median(vals)), np.nan, np.nan
    per = [vals[eps == x] for x in u]
    dr = np.empty(nb)
    for i in range(nb):
        dr[i] = np.median(np.concatenate([per[k] for k in RNG.integers(0, len(per), len(per))]))
    return float(np.median(vals)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


print(f"   {'route':10s} {'r26x':>5s} {'n':>4s} | {'STEPS/s':>9s} {'95% CI':>19s} | "
      f"{'ROUGHNESS':>10s} {'95% CI':>19s} | {'control STEPS/s':>15s}")
st = {}
for tag in ROUTES:
    e = EV[tag]
    if len(e) < 3:
        print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} {len(e):>4d} |  *** too few events")
        continue
    ep = [str(r["ep"]) for r in e]
    a = bootmed([r["steps"] for r in e], ep)
    b = bootmed([r["rough"] for r in e], ep)
    cs = np.median([r["steps"] for r in CTL[tag]]) if len(CTL[tag]) > 3 else np.nan
    st[tag] = dict(n=len(e), steps=a, rough=b, ctl=float(cs))
    print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} {len(e):>4d} | {a[0]:>9.3f} "
          f"[{a[1]:>8.3f},{a[2]:>8.3f}] | {b[0]:>10.2f} [{b[1]:>8.2f},{b[2]:>8.2f}] | "
          f"{cs:>15.3f}")
OUT["steps"] = st

# ================================================================ 3. the band sweep ===============
hdr("3.  THE BAND SWEEP -- do NOT assume 7.8 Hz. Median band envelope p99 during unwind events,\n"
    "    torque (counts). The MACRO symptom, if spectral, must show up as a band where V72 is low.")
print(f"   {'route':10s} {'n':>4s} | " + " ".join(f"{k:>8s}" for k in BANDS))
sw = {}
for tag in ROUTES:
    e = EV[tag]
    if len(e) < 3:
        continue
    sw[tag] = {k: float(np.median([r["t_" + k] for r in e])) for k in BANDS}
    print(f"   {tag:10s} {len(e):>4d} | " + " ".join(f"{sw[tag][k]:>8.0f}" for k in BANDS))
print("\n   same sweep on the COLUMN RATE channel (deg/s) -- what the wheel physically did:")
print(f"   {'route':10s} {'n':>4s} | " + " ".join(f"{k:>8s}" for k in BANDS))
swr = {}
for tag in ROUTES:
    e = EV[tag]
    if len(e) < 3:
        continue
    swr[tag] = {k: float(np.median([r["r_" + k] for r in e])) for k in BANDS}
    print(f"   {tag:10s} {len(e):>4d} | " + " ".join(f"{swr[tag][k]:>8.2f}" for k in BANDS))
OUT["sweep_tq"], OUT["sweep_rate"] = sw, swr

# ================================================================ 4. V72 vs the corpus ============
hdr("4.  ★★ DID MACRO MOVE ON V72? Ratio V72 / reference, EVENT bootstrap, split-half null.")


def bootratio(A, B, key, nb=4000):
    a = np.array([r[key] for r in A], float)
    b = np.array([r[key] for r in B], float)
    ea = np.array([str(r["ep"]) for r in A])
    eb = np.array([str(r["ep"]) for r in B])
    ua, ub = np.unique(ea), np.unique(eb)
    if len(ua) < 2 or len(ub) < 2:
        return np.nan, np.nan, np.nan
    pa, pb = [a[ea == x] for x in ua], [b[eb == x] for x in ub]
    pt = np.median(a) / max(np.median(b), 1e-9)
    dr = np.empty(nb)
    for i in range(nb):
        sa = np.concatenate([pa[k] for k in RNG.integers(0, len(pa), len(pa))])
        sb = np.concatenate([pb[k] for k in RNG.integers(0, len(pb), len(pb))])
        dr[i] = np.median(sa) / max(np.median(sb), 1e-9)
    return float(pt), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


def splitnull(P, key, nb=600):
    v = np.array([r[key] for r in P], float)
    e = np.array([str(r["ep"]) for r in P])
    u = np.unique(e)
    if len(u) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nb):
        p = RNG.permutation(len(u))
        h = len(u) // 2
        s1 = np.concatenate([v[e == u[k]] for k in p[:h]])
        s2 = np.concatenate([v[e == u[k]] for k in p[h:2 * h]])
        out.append(np.median(s1) / max(np.median(s2), 1e-9))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


KEYS = ["steps", "rough", "t_1-2", "t_2-4", "t_4-6", "t_6-9", "t_18-22", "r_1-2", "r_2-4"]
qa = [r for q in QUARTET for r in EV[q]]
res = {}
for key in KEYS:
    print(f"\n   --- {key}")
    print(f"   {'reference':22s} {'ratio':>8s} {'95% CI':>19s} {'null':>17s}  verdict")
    for rn, B in (("V71C r58", EV["V71C r58"]), ("V71B r54", EV["V71B r54"]),
                  ("V62 r37", EV["V62 r37"]), ("V67 r47", EV["V67 r47"]),
                  ("QUARTET pooled", qa)):
        if len(B) < 3 or len(EV[NEW]) < 3:
            continue
        pt, lo, hi = bootratio(EV[NEW], B, key)
        nl = splitnull(EV[NEW] + B, key)
        res[f"{key}|{rn}"] = dict(ratio=pt, lo=lo, hi=hi, null=list(nl))
        tag = ("" if not np.isfinite(nl[0]) else
               ("*** OUTSIDE NULL" if not (nl[0] <= pt <= nl[1]) else "inside null"))
        print(f"   {rn:22s} {pt:>8.3f} [{lo:>8.3f},{hi:>8.3f}] [{nl[0]:>7.2f},{nl[1]:>7.2f}]  {tag}")
OUT["v72_vs_corpus"] = res

# ================================================================ 5. dose-response ================
hdr("5.  ★★★ WHAT FIXED IT? Dose-response on the r26 (gain_A) axis -- the axis Lever A moves.\n"
    "    If Lever A fixed MACRO, the statistic must ORDER on r26x: 0.25 (V67,V72) < 1.0 < 1.5 < 2.0.")
print(f"   {'r26x':>6s} {'builds':30s} {'n':>4s} | " +
      " ".join(f"{k:>10s}" for k in ("STEPS/s", "ROUGH", "t_2-4", "t_6-9")))
dose = {}
for dv in (0.250, 1.000, 1.500, 2.000):
    bs = [t for t in ROUTES if ROUTES[t][4] == dv]
    e = [r for t in bs for r in EV[t]]
    if len(e) < 3:
        continue
    dose[dv] = dict(builds=bs, n=len(e),
                    **{k: float(np.median([r[k] for r in e]))
                       for k in ("steps", "rough", "t_2-4", "t_6-9")})
    print(f"   {dv:>6.3f} {','.join(b.split()[0] for b in bs):30s} {len(e):>4d} | " +
          " ".join(f"{dose[dv][k]:>10.3f}" for k in ("steps", "rough", "t_2-4", "t_6-9")))
print("\n   ⚠ V67 and V72 share r26x = 0.250 but V67 is GATED (manual arm stock) and V72 is not;")
print("   and the pool mixes routes, so read this as an ORDERING check, not an effect size.")
OUT["dose"] = dose

(ROOT / "_scratch/out/_d4_macro.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_macro.json'}")
