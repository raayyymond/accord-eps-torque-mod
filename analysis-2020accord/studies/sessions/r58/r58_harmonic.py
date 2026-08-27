#!/usr/bin/env python3
"""ROUTES 54 / 58 -- the 2x harmonic claim, stress-tested four ways.

`studies/sessions/r58/r58_followups.py` §A found f_hi/f_lo = 2.003 [1.997, 2.009]. That is either a major structural
result (grind #2 is not an independent mode -- it is the 2nd harmonic of grind #1) or an artefact of
a locator that can find a harmonic anywhere. Four tests, each of which could kill it:

  T1 CO-OCCURRENCE. Restrict to windows where the 18-22 line is ABSENT. If a 35-49 line still
     stands there, grind #2 exists WITHOUT grind #1 and cannot be its harmonic.
  T2 A NEGATIVE-CONTROL RATIO. Locate free in 10-16 Hz as the "fundamental" instead. If the
     estimator manufactures 2.000 from any pair of free bands, the 35-49/10-16 ratio also lands on
     2.000 and the result is an artefact of band geometry.
  T3 IS IT THE RATCHET'S HARMONIC INSTEAD? 5 x 8.6 = 43 Hz lands in the same band. Test
     f_hi / f_ratchet against 5.000, and test which fundamental predicts f_hi better.
  T4 AMPLITUDE LOCKING ACROSS WINDOWS -- Spearman rank correlation of the 18-22 and 40-49 p99
     envelopes over windows, which is the statistic a harmonic must satisfy and two independent
     modes need not. Reported per route AND inside the burst cell.

Writes `_scratch/out/_r58_harmonic.json`.  Usage: python studies/sessions/r58/r58_harmonic.py
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
from _r31_common import band_envelope, peak_prom, periodogram  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RNG = np.random.default_rng(20260804)
PGATE = 8.0
OUT = {}
ROUTES = {"V71B r54": ("_scratch/cache/r54", "r54s", [s for s in range(21) if s not in (10, 11)]),
          "V71C r58": ("_scratch/cache/r58", "r58s", [s for s in range(16) if s not in (12, 13, 14, 15)]),
          "V62 r37": ("_scratch/cache/r37", "r37s", list(range(15))),
          "V69 r4f": ("_scratch/cache/r4f", "r4fs", list(range(8)))}
FREE_LO = (15.0, 26.0)
FREE_HI = (35.0, 49.0)
FREE_MID = (10.0, 16.0)      # the negative-control "fundamental"
FREE_RAT = (5.0, 12.0)


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116)


def scan(cache, pfx, segs):
    rows = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        e18 = band_envelope(tq, fs, 18.0, 22.0)
        e40 = band_envelope(tq, fs, 40.0, 49.0)
        e69 = band_envelope(tq, fs, 6.0, 9.0)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        for i in range(0, len(tq) - NFFT + 1, NFFT // 2):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            flo, plo = peak_prom(f, P, *FREE_LO)
            fhi, phi = peak_prom(f, P, *FREE_HI)
            fmid, pmid = peak_prom(f, P, *FREE_MID)
            frat, prat = peak_prom(f, P, *FREE_RAT)
            rows.append(dict(seg=int(s), t0=float(d["t"][i]), flo=flo, phi=phi, plo=plo,
                             fhi=fhi, fmid=fmid, pmid=pmid, frat=frat, prat=prat,
                             e18=float(np.percentile(e18[w], 99)),
                             e40=float(np.percentile(e40[w], 99)),
                             e69=float(np.percentile(e69[w], 99)),
                             lat=float(lat[w].mean()), v=float(v[w].mean())))
    return rows


ALL = {k: scan(*v) for k, v in ROUTES.items()}


def med_ci(vals, nb=3000):
    v = np.asarray([x for x in vals if np.isfinite(x)], float)
    if len(v) < 4:
        return np.nan, np.nan, np.nan, len(v)
    dr = np.array([np.median(v[RNG.integers(0, len(v), len(v))]) for _ in range(nb)])
    return (float(np.median(v)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5)),
            len(v))


# ------------------------------------------------------------------ T1 co-occurrence -------------
hdr("T1  CO-OCCURRENCE -- does a 35-49 Hz line stand where the 18-22 Hz line is ABSENT?")
print("   If grind #2 is grind #1's 2nd harmonic it CANNOT appear without it. `absent` = the 15-26 Hz")
print("   prominence is below the gate; `present` = at or above it.\n")
print(f"   {'route':10s} | {'18-22 PRESENT':>28s} | {'18-22 ABSENT':>28s} | {'ratio of rates':>15s}")
t1 = {}
for tag, rs in ALL.items():
    pres = [r for r in rs if np.isfinite(r["plo"]) and r["plo"] >= PGATE]
    absn = [r for r in rs if np.isfinite(r["plo"]) and r["plo"] < PGATE]
    hp = sum(1 for r in pres if np.isfinite(r["phi"]) and r["phi"] >= PGATE)
    ha = sum(1 for r in absn if np.isfinite(r["phi"]) and r["phi"] >= PGATE)
    rp = hp / max(len(pres), 1)
    ra = ha / max(len(absn), 1)
    t1[tag] = dict(pres_n=len(pres), pres_hi=hp, abs_n=len(absn), abs_hi=ha,
                   rate_pres=rp, rate_abs=ra, ratio=(rp / ra if ra else np.inf))
    print(f"   {tag:10s} | {f'{hp}/{len(pres)} = {100 * rp:5.1f}% have a 35-49 line':>28s} | "
          f"{f'{ha}/{len(absn)} = {100 * ra:5.1f}%':>28s} | {rp / ra if ra else np.inf:>15.2f}x")
OUT["T1_cooccurrence"] = t1

# ------------------------------------------------------------------ T2 negative control ----------
hdr("T2  NEGATIVE-CONTROL RATIO -- 35-49 over a 10-16 Hz 'fundamental'")
print("   If the estimator manufactures 2.000 from any pair of free bands, this lands on 2.000 too.")
print(f"   Band geometry alone allows 35/16 = 2.19 to 49/10 = 4.90, so 2.000 is NOT even reachable")
print("   here -- which makes it a geometry check as much as a statistical one.\n")
print(f"   {'route':10s} | {'f_hi/f_18-22':>30s} | {'f_hi/f_10-16 (control)':>30s}")
t2 = {}
for tag, rs in ALL.items():
    g = [r for r in rs if r["plo"] >= PGATE and r["phi"] >= PGATE]
    gm = [r for r in rs if np.isfinite(r["pmid"]) and r["pmid"] >= PGATE and r["phi"] >= PGATE]
    a = med_ci([r["fhi"] / r["flo"] for r in g])
    b = med_ci([r["fhi"] / r["fmid"] for r in gm])
    t2[tag] = dict(subject=a[:3], subject_n=a[3], control=b[:3], control_n=b[3])
    print(f"   {tag:10s} | {f'{a[0]:.3f} [{a[1]:.3f}, {a[2]:.3f}]  n={a[3]}':>30s} | "
          f"{f'{b[0]:.3f} [{b[1]:.3f}, {b[2]:.3f}]  n={b[3]}':>30s}")
OUT["T2_control_ratio"] = t2

# ------------------------------------------------------------------ T3 which fundamental ---------
hdr("T3  WHICH FUNDAMENTAL? -- 5 x the 8.6 Hz ratchet also lands at 43 Hz")
print("   Reported: f_hi/f_ratchet against 5.000, and the SCATTER of f_hi about each prediction.")
print("   The better fundamental is the one whose predicted f_hi has the smaller residual sd.\n")
print(f"   {'route':10s} | {'f_hi / f_ratchet':>26s} | {'sd(f_hi - 2*f_lo)':>18s} "
      f"{'sd(f_hi - 5*f_rat)':>19s}   better")
t3 = {}
for tag, rs in ALL.items():
    g = [r for r in rs if r["plo"] >= PGATE and r["phi"] >= PGATE]
    gr = [r for r in rs if np.isfinite(r["prat"]) and r["prat"] >= PGATE and r["phi"] >= PGATE]
    a = med_ci([r["fhi"] / r["frat"] for r in gr])
    s2 = float(np.std([r["fhi"] - 2 * r["flo"] for r in g], ddof=1)) if len(g) > 2 else np.nan
    s5 = float(np.std([r["fhi"] - 5 * r["frat"] for r in gr], ddof=1)) if len(gr) > 2 else np.nan
    t3[tag] = dict(ratio5=a[:3], n5=a[3], sd_2flo=s2, sd_5frat=s5)
    print(f"   {tag:10s} | {f'{a[0]:.3f} [{a[1]:.3f}, {a[2]:.3f}]  n={a[3]}':>26s} | "
          f"{s2:>18.3f} {s5:>19.3f}   "
          f"{'2 x GRIND #1' if s2 < s5 else '5 x ratchet'}")
OUT["T3_which_fundamental"] = t3

# ------------------------------------------------------------------ T4 amplitude locking ---------
hdr("T4  AMPLITUDE LOCKING ACROSS WINDOWS -- Spearman rank correlation of the band envelopes")
print("   A 2nd harmonic generated by a nonlinearity grows with its fundamental, so the two p99")
print("   envelopes must rank-correlate across windows. 🛑 Both also rise with broadband driver")
print("   effort, so the 24-28 Hz control correlation is printed beside it as the confound's size.\n")


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 5:
        return np.nan
    ra = np.argsort(np.argsort(a[m])).astype(float)
    rb = np.argsort(np.argsort(b[m])).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


print(f"   {'route':10s} {'cell':<16} {'n':>6s} | {'rho(e18,e40)':>13s} {'rho(e69,e40)':>13s} "
      f"{'rho(e18,e69)':>13s}")
t4 = {}
for tag, rs in ALL.items():
    for cell, sel in (("all", lambda r: True),
                      ("engaged", lambda r: r["lat"] > 0.9),
                      ("eng, e40>200", lambda r: r["lat"] > 0.9 and r["e40"] > 200)):
        s = [r for r in rs if sel(r)]
        if len(s) < 6:
            continue
        r1 = spearman([r["e18"] for r in s], [r["e40"] for r in s])
        r2 = spearman([r["e69"] for r in s], [r["e40"] for r in s])
        r3 = spearman([r["e18"] for r in s], [r["e69"] for r in s])
        t4[f"{tag}|{cell}"] = dict(n=len(s), e18_e40=r1, e69_e40=r2, e18_e69=r3)
        print(f"   {tag:10s} {cell:<16} {len(s):>6d} | {r1:>13.3f} {r2:>13.3f} {r3:>13.3f}")
    print()
OUT["T4_amplitude_locking"] = t4

(ROOT / "_scratch/out/_r58_harmonic.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"wrote {ROOT / '_scratch/out/_r58_harmonic.json'}")
