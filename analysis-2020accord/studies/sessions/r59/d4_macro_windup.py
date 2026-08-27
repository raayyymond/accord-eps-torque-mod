#!/usr/bin/env python3
"""D4 -- MACRO, second instrument: the WIND-UP phase, not the return.

WHY. `studies/sessions/r59/d4_macro_ratchet.py` measured the UNWIND and returned 45/45 comparisons inside null. Before
concluding "macro did not move", test the phase that matches the KNOWN mechanism. V42 -- the build
CONFIRMED on-car against the hard-turn ratchet -- killed the STATE-4 GOVERNOR, whose recorded
behaviour is *"gp-0x67fa == 4 forbids command magnitude INCREASE, cumulative"*. A governor that
cannot let assist rise bites while the driver is winding INTO a hard turn, not while the wheel
returns. "Hard-turn recovery" plausibly means recovering FROM the turn's effort, not the unwind.

THE SIGNATURE a magnitude-capping governor must leave on the bus, stated before measuring:
    EFFORT RAMP   median |bar torque| in the LAST third of the wind-up / the FIRST third.
                  Capped assist => the driver must push progressively harder.  > 1 and rising.
    RATE DECAY    median |column rate| last third / first third. Capped assist => the wheel slows
                  even though the driver pushes harder.  < 1.
    STIFFNESS RISE  (|tq| / |rate|) last third / first third -- the two above combined, and the
                  quantity that most directly expresses "the wheel got heavier as I turned".
    STEPS/s       the same stall detector, applied to the winding velocity.

🛑 A pre-declared FALSIFIER: if V72 is indistinguishable on all four, then either macro is not a
wind-up phenomenon or route 59 did not contain it -- and the EXPOSURE column decides which.

Writes `_scratch/out/_d4_macro_windup.json`.
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
from _r31_common import sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

PEAK_DEG, LO_DEG = 120.0, 30.0
MIN_S, MAX_S = 0.8, 15.0
OUT = {}
RNG = np.random.default_rng(20260805)
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
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


def find_windups(aa, fs):
    """|angle| rising from <= LO_DEG to >= PEAK_DEG. Returns (i_start, i_peak)."""
    hi = aa >= PEAK_DEG
    cross = np.flatnonzero((~hi[:-1]) & hi[1:]) + 1
    out, last = [], -1
    for c in cross:
        j = c
        while j > 0 and aa[j - 1] <= aa[j]:
            j -= 1
        k, best = j, aa[j]
        while k > 0 and (c - k) / fs < MAX_S:
            if aa[k - 1] <= best:
                best, j = aa[k - 1], k - 1
            elif aa[k - 1] - best > 25.0:
                break
            k -= 1
        dur = (c - j) / fs
        if aa[j] <= LO_DEG and MIN_S <= dur <= MAX_S and j > last:
            out.append((j, c))
            last = c
    return out


def steps_of(x, fs, sign=+1):
    v = sign * np.gradient(x) * fs
    v = np.convolve(v, np.ones(5) / 5.0, mode="same")
    vmax = float(np.max(v))
    if vmax <= 1e-6 or len(v) < 12:
        return np.nan
    lo_thr, hi_thr = 0.25 * vmax, 0.50 * vmax
    n, armed = 0, False
    for y in v:
        if y < lo_thr:
            armed = True
        elif armed and y > hi_thr:
            n += 1
            armed = False
    return n / (len(x) / fs)


def thirds(v):
    n = len(v) // 3
    if n < 4:
        return np.nan, np.nan
    return float(np.median(np.abs(v[:n]))), float(np.median(np.abs(v[-n:])))


def scan(cache, pfx, segs, skip, tag):
    out = []
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
        rc = np.abs(np.asarray(d["rate_c"], float))
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        eff = np.abs(sustained(tq, fs))
        for i0, i1 in find_windups(aa, fs):
            w = slice(i0, i1)
            t_a, t_b = thirds(eff[w])
            r_a, r_b = thirds(rc[w])
            if not all(np.isfinite(x) and x > 1e-6 for x in (t_a, t_b, r_a, r_b)):
                continue
            out.append(dict(tag=tag, seg=int(s), dur=(i1 - i0) / fs,
                            eramp=t_b / t_a, rdecay=r_b / r_a,
                            stiff=(t_b / r_b) / (t_a / r_a),
                            steps=steps_of(aa[w], fs, +1),
                            peak=float(aa[i1 - 1]), v=float(v[w].mean()),
                            lat=float(lat[w].mean()), eff=float(np.median(eff[w])),
                            ep=(tag, int(s), i0 // 6000)))
    return out


EV = {t: scan(c, p, s, sk, t) for t, (c, p, s, sk, _) in ROUTES.items()}

hdr("1.  EXPOSURE -- WIND-UP events (|angle| 0->120+ deg). 🛑 Empty is not null.")
print(f"   {'route':10s} {'r26x':>5s} | {'events':>7s} {'secs':>7s} {'med dur':>8s} {'eng':>5s} "
      f"{'man':>5s} {'med v':>6s} {'med eff':>8s}")
for tag in ROUTES:
    e = EV[tag]
    if not e:
        print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} | {0:>7d}  (none)")
        continue
    print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} | {len(e):>7d} "
          f"{sum(r['dur'] for r in e):>7.1f} {np.median([r['dur'] for r in e]):>8.2f} "
          f"{sum(1 for r in e if r['lat'] > 0.5):>5d} {sum(1 for r in e if r['lat'] <= 0.5):>5d} "
          f"{np.median([r['v'] for r in e]):>6.2f} {np.median([r['eff'] for r in e]):>8.0f}")
OUT["exposure"] = {t: dict(n=len(EV[t]), secs=float(sum(r["dur"] for r in EV[t]))) for t in ROUTES}

hdr("2.  ★★★ THE MAGNITUDE-CAP SIGNATURE. A governor forbidding assist INCREASE must show\n"
    "    EFFORT RAMP > 1 (driver pushes harder), RATE DECAY < 1 (wheel slows anyway),\n"
    "    STIFFNESS RISE > 1. Medians over events, per build.")
print(f"   {'route':10s} {'r26x':>5s} {'n':>4s} | {'EFFORT RAMP':>12s} {'RATE DECAY':>11s} "
      f"{'STIFFNESS':>10s} {'STEPS/s':>9s}")
tab = {}
for tag in ROUTES:
    e = EV[tag]
    if len(e) < 3:
        print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} {len(e):>4d} |  *** too few")
        continue
    tab[tag] = {k: float(np.nanmedian([r[k] for r in e]))
                for k in ("eramp", "rdecay", "stiff", "steps")}
    print(f"   {tag:10s} {ROUTES[tag][4]:>5.3f} {len(e):>4d} | {tab[tag]['eramp']:>12.3f} "
          f"{tab[tag]['rdecay']:>11.3f} {tab[tag]['stiff']:>10.3f} {tab[tag]['steps']:>9.3f}")
OUT["windup_stats"] = tab


def bootratio(A, B, key, nb=4000):
    a = np.array([r[key] for r in A], float)
    b = np.array([r[key] for r in B], float)
    ea = np.array([str(r["ep"]) for r in A])
    eb = np.array([str(r["ep"]) for r in B])
    m, n = np.isfinite(a), np.isfinite(b)
    a, ea, b, eb = a[m], ea[m], b[n], eb[n]
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
    m = np.isfinite(v)
    v, e = v[m], e[m]
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


hdr("3.  DID IT MOVE ON V72? Ratio V72 / reference, event bootstrap, split-half null.\n"
    "    The 'min detectable' column is the null band -- what this exposure could have seen.")
qa = [r for q in QUARTET for r in EV[q]]
res = {}
for key, lbl in (("eramp", "EFFORT RAMP"), ("rdecay", "RATE DECAY"), ("stiff", "STIFFNESS RISE"),
                 ("steps", "STEPS/s")):
    print(f"\n   --- {lbl}")
    print(f"   {'reference':18s} {'ratio':>8s} {'95% CI':>19s} {'null (min detectable)':>23s}  "
          f"verdict")
    for rn, B in (("V71C r58", EV["V71C r58"]), ("V71B r54", EV["V71B r54"]),
                  ("V62 r37", EV["V62 r37"]), ("V67 r47", EV["V67 r47"]),
                  ("QUARTET pooled", qa)):
        if len(B) < 3 or len(EV[NEW]) < 3:
            continue
        pt, lo, hi = bootratio(EV[NEW], B, key)
        nl = splitnull(EV[NEW] + B, key)
        res[f"{key}|{rn}"] = dict(ratio=pt, lo=lo, hi=hi, null=list(nl))
        v = ("" if not np.isfinite(nl[0]) else
             ("*** OUTSIDE NULL" if not (nl[0] <= pt <= nl[1]) else "inside null"))
        print(f"   {rn:18s} {pt:>8.3f} [{lo:>8.3f},{hi:>8.3f}] "
              f"[{nl[0]:>9.2f},{nl[1]:>10.2f}]  {v}")
OUT["v72_vs_corpus"] = res

hdr("4.  DOSE-RESPONSE on the r26 (gain_A) axis -- would 'Lever A fixed macro' show an ordering?")
print(f"   {'r26x':>6s} {'builds':22s} {'n':>4s} | {'EFFORT RAMP':>12s} {'RATE DECAY':>11s} "
      f"{'STIFFNESS':>10s} {'STEPS/s':>9s}")
dose = {}
for dv in (0.250, 1.000, 1.500, 2.000):
    bs = [t for t in ROUTES if ROUTES[t][4] == dv]
    e = [r for t in bs for r in EV[t]]
    if len(e) < 3:
        continue
    dose[dv] = dict(builds=bs, n=len(e), **{k: float(np.nanmedian([r[k] for r in e]))
                                            for k in ("eramp", "rdecay", "stiff", "steps")})
    print(f"   {dv:>6.3f} {','.join(b.split()[0] for b in bs):22s} {len(e):>4d} | "
          + " ".join(f"{dose[dv][k]:>12.3f}" if i == 0 else f"{dose[dv][k]:>11.3f}"
                     for i, k in enumerate(("eramp", "rdecay", "stiff", "steps"))))
OUT["dose"] = dose

(ROOT / "_scratch/out/_d4_macro_windup.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_macro_windup.json'}")
