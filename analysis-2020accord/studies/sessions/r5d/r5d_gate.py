#!/usr/bin/env python3
"""Route `5d` -- the three things the flight gate still needs, and the V75 sizing anchor.

1. THE CREEP 5xf0 NUMBER, PROPERLY. `studies/sessions/r5d/r5d_falsifiers.py` found the engaged v<12.5 arm clear (2.23,
   CI [1.25, 5.29]) but the CREEP arm -- the arm the criterion was written for, since the registered
   0.80 baseline was measured on the pooled CREEP corpus -- read **5.84 at K = 2**. That is the one
   number that could stop V75, and it is quoted off two runs. Re-measure it at an NFFT that yields
   enough windows to bootstrap, on every build, so V74's creep value can be placed in the corpus's
   OWN creep distribution instead of against a single pooled scalar.

2. THE IDENTITY OF THE 42 Hz LINE. 🛑 On V74, f0 = 8.46 Hz so 5 x f0 = 42.3 Hz -- and the corpus
   already records an independent line at **42.19 Hz = 2 x the 21.09 Hz mode** (the parametric pump,
   `accord-v59-parametric-pump-marginal`). The two predictions are 0.1 Hz apart. A prominence at
   42.2 Hz therefore CANNOT be attributed to the relay without a discriminator, and the discriminator
   is whether the line tracks 5 x f0(6-9) or 2 x f0(18-22) window by window.
   ⊕ A second deflator: prominence is peak / local median floor, so it RISES when the floor falls.
   V74's floor is lower than V73's (24-28 ratio 0.849), which inflates every prominence on this route.

3. THE SIZING FLOOR. "Imperceptible" has one defensible anchor in this corpus: the MANUAL arm, which
   on V74 is byte-stock for levers E'/D' and which the operator does not complain about. The gap from
   engaged creep to manual creep, in the same units, is the attenuation V75 has to find.

Usage:  python studies/sessions/r5d/r5d_gate.py   ->  writes _scratch/out/_r5d_gate.json
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r5d_lib as L  # noqa: E402
import d6_events as D  # noqa: E402
from d6b_events_fixed import bursts  # noqa: E402

RNG = np.random.default_rng(424242)
OUT = {}
D.PARKED["V74/r5d"] = [2, 3, 9]
L.install_fs()
BUILDS = ["V59/r2c", "V58/r2b", "V62/r37", "V65/r3b", "V67/r47", "V69/r4f", "V71B/r54",
          "V71C/r58", "V72/r59", "V73/r5a", "V74/r5d"]
T_ABS = 600.0


def load_runs(build, vhi, engaged=True, minrun=512):
    out = []
    for _, s, a, b, d, fs in D.runs(build, 0.0, vhi, engaged, minrun):
        out.append(dict(run=(build, s, a), x=np.asarray(d["tq"][a:b], float), fs=fs,
                        v=float(np.mean(np.abs(d["cs_v"][a:b])))))
    return out


def run_boot(per, nb=3000, fn=np.median):
    ks = list(per)
    if len(ks) < 2:
        return np.nan, np.nan, np.nan
    allv = np.concatenate([per[k] for k in ks])
    dr = np.array([fn(np.concatenate([per[ks[j]] for j in RNG.integers(0, len(ks), len(ks))]))
                   for _ in range(nb)])
    return float(fn(allv)), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


# ================================================== 1. CREEP 5xf0, per window =====================
L.hdr("1. ★★ THE CREEP 5 x f0 PROMINENCE -- per-window (K-free), so it can be bootstrapped")
print("  NFFT 512 (5.12 s, 0.195 Hz bins). Engaged, v < 4 m/s. Windows are kept only if the 6-9 Hz")
print("  line itself is prominent (>= 3), so `5 x f0` is anchored to a line that exists.\n")
print(f"  {'build':<10} {'runs':>5} {'n win':>6} {'f0 med':>7} {'prom(5xf0)':>11} {'95% CI':>18}")
creep5 = {}
for b in BUILDS:
    rs = load_runs(b, 4.0)
    per, perf = {}, {}
    for r in rs:
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            f0, p0 = G.locate(f, P, 6, 9, R=R)
            if not np.isfinite(f0) or p0 < 3.0:
                continue
            j = int(np.argmin(np.abs(f - 5 * f0)))
            w = slice(max(0, j - 2), j + 3)
            k = int(np.argmax(np.where(np.isfinite(R[w]), R[w], -np.inf))) + w.start
            per.setdefault(r["run"], []).append(float(R[k]))
            perf.setdefault(r["run"], []).append(f0)
    n = sum(len(v) for v in per.values())
    if n < 8:
        print(f"  {b:<10} {len(rs):>5} {n:>6}   -- underpowered")
        continue
    m, lo, hi = run_boot(per)
    f0m = float(np.median(np.concatenate(list(perf.values()))))
    creep5[b] = dict(nrun=len(rs), n=n, f0=f0m, prom5=m, lo=lo, hi=hi)
    print(f"  {b:<10} {len(rs):>5} {n:>6} {f0m:>7.2f} {m:>11.2f} [{lo:>7.2f}, {hi:>7.2f}]")
OUT["creep_5xf0"] = creep5
if "V74/r5d" in creep5:
    others = [v["prom5"] for k, v in creep5.items() if k != "V74/r5d"]
    v = creep5["V74/r5d"]["prom5"]
    print(f"\n  corpus creep spread (excluding V74): {min(others):.2f} .. {max(others):.2f}, "
          f"median {np.median(others):.2f}")
    print(f"  V74 = {v:.2f}  ⇒ rank {1 + sum(o > v for o in others)} of {len(others) + 1} "
          f"(1 = highest)")

# ================================================== 2. THE 42 Hz IDENTITY ========================
L.hdr("2. ★★★ IS THE ~42 Hz LINE 5 x f0(RATCHET) OR 2 x f0(GRIND #1)? -- the discriminator")
print("  Per window, take the most prominent line in 36-46 Hz and regress its frequency on BOTH")
print("  predictors. A relay harmonic tracks 5 x f_ratchet; the recorded parametric pump tracks")
print("  2 x f_grind1. Theil-Sen slope; a genuine harmonic gives slope ~1 on its own predictor.")
print("  🛑 A RATIO IS NOT A TRACKING TEST (`feedback-a-ratio-is-not-a-tracking-test`), which is")
print("  exactly why this is a slope on the pairing and not a mean ratio.\n")


def theil_sen(x, y, nb=2000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 8:
        return np.nan, np.nan, np.nan, len(x)
    i, j = np.triu_indices(len(x), 1)
    dx = x[j] - x[i]
    ok = np.abs(dx) > 1e-9
    s = np.median((y[j] - y[i])[ok] / dx[ok])
    dr = np.full(nb, np.nan)
    for k in range(nb):
        idx = RNG.integers(0, len(x), len(x))
        xx, yy = x[idx], y[idx]
        a, bq = np.triu_indices(len(xx), 1)
        d2 = xx[bq] - xx[a]
        o2 = np.abs(d2) > 1e-9
        if o2.any():
            dr[k] = np.median((yy[bq] - yy[a])[o2] / d2[o2])
    return float(s), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), len(x)


ident = {}
for b in ("V74/r5d", "V73/r5a", "V72/r59"):
    rows = []
    for r in load_runs(b, 12.5):
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            fr_, pr_ = G.locate(f, P, 6, 9, R=R)
            fg, pg = G.locate(f, P, 18, 22, R=R)
            fh, ph = G.locate(f, P, 36, 46, R=R)
            if not all(np.isfinite(z) for z in (fr_, fg, fh)) or pr_ < 3 or pg < 3 or ph < 2:
                continue
            rows.append((5 * fr_, 2 * fg, fh))
    if len(rows) < 10:
        print(f"  {b:<10} only {len(rs) if False else len(rows)} usable windows -- underpowered")
        continue
    a = np.array(rows)
    s1 = theil_sen(a[:, 0], a[:, 2])
    s2 = theil_sen(a[:, 1], a[:, 2])
    r1 = np.corrcoef(a[:, 0], a[:, 2])[0, 1]
    r2 = np.corrcoef(a[:, 1], a[:, 2])[0, 1]
    ident[b] = dict(n=len(rows), slope_5f_ratchet=list(s1), slope_2f_grind=list(s2),
                    r_5f=float(r1), r_2f=float(r2),
                    med_line=float(np.median(a[:, 2])), med_5f=float(np.median(a[:, 0])),
                    med_2f=float(np.median(a[:, 1])))
    print(f"  {b:<10} n={len(rows):>4}  line median {np.median(a[:, 2]):.2f} Hz  "
          f"(5xf_ratchet {np.median(a[:, 0]):.2f}, 2xf_grind1 {np.median(a[:, 1]):.2f})")
    print(f"             vs 5 x f_ratchet: slope {s1[0]:+.3f} [{s1[1]:+.3f}, {s1[2]:+.3f}]  "
          f"r={r1:+.3f}")
    print(f"             vs 2 x f_grind1 : slope {s2[0]:+.3f} [{s2[1]:+.3f}, {s2[2]:+.3f}]  "
          f"r={r2:+.3f}")
OUT["line42_identity"] = ident

# ================================================== 3. Δf0 WITH A CI =============================
L.hdr("3. Δf0 WITH AN INTERVAL -- the |Δf0| <= 0.3 / > 0.5 criteria need one")
f0w = {}
for b in ("V74/r5d", "V73/r5a", "V72/r59"):
    per = {}
    for r in load_runs(b, 12.5):
        f = np.fft.rfftfreq(512, 1 / r["fs"])
        for i in range(0, len(r["x"]) - 512 + 1, 256):
            P = C.periodogram(r["x"][i:i + 512], r["fs"], 512, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            ff, pp = G.locate(f, P, 5, 12, R=R)
            if np.isfinite(ff) and pp >= 3.0:
                per.setdefault(r["run"], []).append(ff)
    f0w[b] = per
for b in ("V73/r5a", "V72/r59"):
    A, B = f0w["V74/r5d"], f0w[b]
    ka, kb = list(A), list(B)
    dr = np.array([np.median(np.concatenate([A[ka[j]] for j in RNG.integers(0, len(ka), len(ka))]))
                   - np.median(np.concatenate([B[kb[j]] for j in RNG.integers(0, len(kb), len(kb))]))
                   for _ in range(4000)])
    pt = (np.median(np.concatenate([A[k] for k in ka])) -
          np.median(np.concatenate([B[k] for k in kb])))
    lo, hi = np.nanpercentile(dr, [2.5, 97.5])
    print(f"  Δf0(V74 - {b}) = {pt:+.3f} Hz [{lo:+.3f}, {hi:+.3f}]   "
          f"width {hi - lo:.2f} Hz vs a 0.3 Hz criterion "
          f"⇒ {'RESOLVABLE' if (hi - lo) < 0.6 else 'UNDERPOWERED for +-0.3 Hz'}")
    OUT.setdefault("df0_ci", {})[b] = dict(d=float(pt), lo=float(lo), hi=float(hi))
allf = np.concatenate([np.concatenate(list(v.values())) for v in f0w.values()])
print(f"\n  ⚠ CONTEXT: across the 11 corpus builds the per-route median f0 spans 8.01 .. 9.79 Hz "
      f"(1.78 Hz).\n  A +-0.3 Hz criterion is a fifth of the route-to-route spread of the same "
      f"statistic.")

# ================================================== 4. THE SIZING FLOOR ==========================
L.hdr("4. ★★★ THE SIZING FLOOR -- how far is engaged creep from the byte-stock MANUAL arm?")
print("  On V74 the manual arm is genuinely byte-stock for LEVERS E'/D' (mode 24 untouched), and")
print("  the operator does not report a symptom in manual steering. So `manual creep` is this")
print("  route's own operational definition of 'imperceptible'.")
print("  ⚠ It is NOT a pure lever control: engagement also changes the plant, and the rate lane is")
print("  ungated so it dosed both arms. It is a FLOOR, not an effect estimate.\n")
size = {}
for lab, eng, vhi in (("engaged creep", True, 4.0), ("manual creep", False, 4.0),
                      ("engaged v<12.5", True, 12.5), ("manual v<12.5", False, 12.5)):
    rs = load_runs("V74/r5d", vhi, eng, minrun=256)
    if not rs:
        print(f"  {lab:<16} no qualifying run")
        continue
    pe, pd, pg = {}, {}, {}
    for r in rs:
        env = np.abs(D.analytic(D.bp(r["x"], r["fs"], *D.RATCHET)))
        g = np.abs(D.analytic(D.bp(r["x"], r["fs"], 18.0, 22.0)))
        pe.setdefault(r["run"], []).append(float(np.percentile(env, 99)))
        pd.setdefault(r["run"], []).append(float(np.mean(env >= T_ABS)))
        pg.setdefault(r["run"], []).append(float(np.percentile(g, 99)))
    e_, el, eh = run_boot(pe)
    d_, dl, dh = run_boot(pd)
    g_, gl, gh = run_boot(pg)
    size[lab] = dict(nrun=len(rs), sec=sum(len(r["x"]) / r["fs"] for r in rs),
                     env69=[e_, el, eh], duty69=[d_, dl, dh], env1822=[g_, gl, gh])
    print(f"  {lab:<16} runs={len(rs):>2} {sum(len(r['x']) / r['fs'] for r in rs):>6.1f} s   "
          f"6-9 env p99 {e_:>7.0f} [{el:>6.0f},{eh:>7.0f}]   duty(>=600) {d_:>6.3f}   "
          f"18-22 env p99 {g_:>7.0f}")
OUT["sizing"] = size
if "engaged creep" in size and "manual creep" in size:
    a, b = size["engaged creep"], size["manual creep"]
    print(f"\n  ⇒ THE GAP AT CREEP, V74 as flown:")
    print(f"      6-9 Hz  envelope: engaged {a['env69'][0]:.0f} vs manual {b['env69'][0]:.0f}  "
          f"⇒ **{a['env69'][0] / b['env69'][0]:.2f}x** to reach the manual floor")
    print(f"      18-22Hz envelope: engaged {a['env1822'][0]:.0f} vs manual {b['env1822'][0]:.0f} "
          f"⇒ **{a['env1822'][0] / b['env1822'][0]:.2f}x**")
    OUT["gap"] = dict(g69=a["env69"][0] / b["env69"][0],
                      g1822=a["env1822"][0] / b["env1822"][0])

with open(ROOT / "_scratch/out/_r5d_gate.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_r5d_gate.json")
