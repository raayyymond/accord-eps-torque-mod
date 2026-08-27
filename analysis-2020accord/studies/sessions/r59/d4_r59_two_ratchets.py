#!/usr/bin/env python3
"""D4 follow-ups: (1) IS THERE A SECOND, HANDS-ON RATCHET? (2) DO THE RATCHET AND GRIND #1 CO-OCCUR?

FOLLOW-UP 1 -- RATCHET-A vs RATCHET-B.
  Ratchet-B (what studies/sessions/r59/d4_r59_ratchet.py measured, and what the corpus record describes): ENGAGED,
  HANDS-OFF, CREEP, sustained, 7.79 Hz, engagement-required.
  Ratchet-A (the operator's felt "large-scale 7 Hz ratcheting", and V42's CONFIRMED hard-turn
  symptom, which `docs/specs/design/V72-DESIGN.md` s0.1 calls a DIFFERENT symptom): hands-ON, during or after a
  hard turn, transient.
  A RECOVERY window is operationalised from the window's own angle trajectory -- no hand-picking:
      hands ON      median |lowpass(tq,3Hz)| > 300 counts
      wound up      |angle| at window start >= WIND_DEG
      unwinding     |angle| falls by >= UNWIND_DEG across the window
  Scored with the IDENTICAL 6-9 Hz instrument as Ratchet-B so the two populations are comparable.

FOLLOW-UP 2 -- SHARED MECHANISM?
  🛑 A RAW correlation is not enough and this kit retracted a session headline for exactly that.
  Three guards, all applied:
    a) WITHIN-EPISODE. Both bands are centred on their own episode mean before correlating, so a
       common exposure driver (he cornered harder during episode 7) cannot produce the result.
    b) SHUFFLED-PAIRING CONTROL. The 18-22 Hz deviations are permuted across windows INSIDE each
       episode, 4000x. That destroys the pairing, keeps both marginals and the episode structure.
    c) DISJOINT WINDOWS ONLY (hop = NFFT). Overlapping windows share samples and would inflate both
       the statistic and, asymmetrically, the null.

Writes `_scratch/out/_d4_r59_two_ratchets.json`.
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
from _r31_common import band_envelope, peak_prom, periodogram, runs_of, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
G1 = (18.0, 22.0)
HANDS_OFF = 300.0
CREEP_R = 4.0
AMP_MIN = 600.0
WIND_DEG = 90.0                 # "wound up" at the start of the window
UNWIND_DEG = 30.0               # "unwinding" across the 2.56 s window
OUT = {}
RNG = np.random.default_rng(20260805)

ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14]),
}
NEW = "V72 r59"
QUARTET = ["V70 r50", "V69 r4f", "V62 r37", "V59 r2c"]


def hdr(s):
    print("\n" + "=" * 126 + f"\n{s}\n" + "=" * 126)


def scan(cache, pfx, segs, skip, tag):
    """Disjoint windows over the WHOLE route, tagged for both populations and both bands."""
    out = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        er = band_envelope(tq, fs, *RATCH)
        eg = band_envelope(tq, fs, *G1)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        aa = np.abs(ang)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            out.append(dict(
                tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                er=float(np.percentile(er[w], 99)), eg=float(np.percentile(eg[w], 99)),
                fr=peak_prom(f, P, *RATCH)[0], pr=peak_prom(f, P, *RATCH)[1],
                pg=peak_prom(f, P, *G1)[1],
                v=float(v[w].mean()), eff=float(np.median(eff[w])), lat=float(lat[w].mean()),
                ang=float(aa[w].mean()), ang0=float(aa[i]), ang1=float(aa[i + NFFT - 1]),
                angmax=float(aa[w].max()),
                unwind=float(aa[i] - aa[i + NFFT - 1])))
    return out


ALL = {t: scan(c, p, s, sk, t) for t, (c, p, s, sk) in ROUTES.items()}

# ================================================================ FOLLOW-UP 1 =====================
hdr("FOLLOW-UP 1  ★★ IS THERE A SEPARABLE HANDS-ON HARD-TURN-RECOVERY 6-9 Hz POPULATION?\n"
    f"    RECOVERY = hands ON (eff > {HANDS_OFF:.0f}) AND |angle| starts >= {WIND_DEG:.0f} deg AND "
    f"falls >= {UNWIND_DEG:.0f} deg across the 2.56 s window.")


def rec_mask(r):
    return (r["eff"] > HANDS_OFF and r["ang0"] >= WIND_DEG and r["unwind"] >= UNWIND_DEG)


print(f"   {'route':10s} | " + " ".join(f"{n:>26s}" for n in
                                        ("RECOVERY (hands-ON unwind)", "Ratchet-B (eng h-off creep)")))
print(f"   {'':10s} | " + " ".join(f"{'n':>4s} {'secs':>6s} {'hits':>10s} {'med p-p':>7s}"
                                   for _ in range(2)))
f1 = {}
for tag, rs in ALL.items():
    A = [r for r in rs if rec_mask(r)]
    B = [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9]
    cells = []
    for s in (A, B):
        h = sum(1 for r in s if r["er"] >= AMP_MIN)
        cells.append((len(s), len(s) * NFFT / 100, h,
                      (100 * h / len(s)) if s else np.nan,
                      2 * np.median([r["er"] for r in s]) if s else np.nan))
    f1[tag] = dict(recovery=cells[0], ratchetB=cells[1])
    print(f"   {tag:10s} | " + " ".join(
        f"{c[0]:>4d} {c[1]:>6.1f} {f'{c[2]}={c[3]:.0f}%':>10s} {c[4]:>7.0f}"
        if c[0] else f"{0:>4d} {0.0:>6.1f} {'--':>10s} {'--':>7s}" for c in cells))
OUT["followup1_populations"] = f1

print("\n   ★ SPLIT THE RECOVERY POPULATION BY ENGAGEMENT (Ratchet-B is engagement-REQUIRED;\n"
      "     if Ratchet-A is a different symptom it need not be):")
print(f"   {'route':10s} | {'eng recovery':>22s} {'manual recovery':>22s} {'Fisher p':>10s}")
f1b = {}
for tag, rs in ALL.items():
    A = [r for r in rs if rec_mask(r)]
    e = [r for r in A if r["lat"] > 0.5]
    m = [r for r in A if r["lat"] <= 0.5]
    he = sum(1 for r in e if r["er"] >= AMP_MIN)
    hm = sum(1 for r in m if r["er"] >= AMP_MIN)
    p = fisher2x2(he, len(e) - he, hm, len(m) - hm) if (e and m) else np.nan
    f1b[tag] = dict(eng_hit=he, eng_n=len(e), man_hit=hm, man_n=len(m), p=float(p))
    print(f"   {tag:10s} | {f'{he}/{len(e)}' + (f' = {100*he/len(e):.0f}%' if e else ''):>22s} "
          f"{f'{hm}/{len(m)}' + (f' = {100*hm/len(m):.0f}%' if m else ''):>22s} {p:>10.3g}")
OUT["followup1_by_engagement"] = f1b

print("\n   ★★ DID RATCHET-A MOVE ON V72? Recovery-population hit rate and amplitude vs the corpus.")
print(f"   {'comparison':34s} {'V72':>16s} {'reference':>16s} {'Fisher p':>10s}  {'p-p ratio':>10s}")
f1c = {}
A72 = [r for r in ALL[NEW] if rec_mask(r)]
h72 = sum(1 for r in A72 if r["er"] >= AMP_MIN)
for ref in ("V71C r58", "V71B r54", "V62 r37", "V59 r2c", "V69 r4f", "V67 r47"):
    B = [r for r in ALL[ref] if rec_mask(r)]
    hb = sum(1 for r in B if r["er"] >= AMP_MIN)
    if not B or not A72:
        continue
    p = fisher2x2(h72, len(A72) - h72, hb, len(B) - hb)
    rr = (np.median([r["er"] for r in A72]) / max(np.median([r["er"] for r in B]), 1e-9))
    f1c[ref] = dict(v72=[h72, len(A72)], ref=[hb, len(B)], p=float(p), pp_ratio=float(rr))
    print(f"   {'V72 vs ' + ref:34s} {f'{h72}/{len(A72)}':>16s} {f'{hb}/{len(B)}':>16s} "
          f"{p:>10.3g}  {rr:>10.3f}")
qa = [r for r in (ALL[q] for q in QUARTET) for r in r]
hq = sum(1 for r in qa if rec_mask(r) and r["er"] >= AMP_MIN)
nq = sum(1 for r in qa if rec_mask(r))
if nq and A72:
    p = fisher2x2(h72, len(A72) - h72, hq, nq - hq)
    print(f"   {'V72 vs the QUARTET pooled':34s} {f'{h72}/{len(A72)}':>16s} {f'{hq}/{nq}':>16s} "
          f"{p:>10.3g}")
    f1c["quartet"] = dict(v72=[h72, len(A72)], ref=[hq, nq], p=float(p))
OUT["followup1_v72_vs_corpus"] = f1c

# ================================================================ FOLLOW-UP 2 =====================
hdr("FOLLOW-UP 2  ★★ DO THE 6-9 Hz RATCHET AND THE 18-22 Hz GRIND #1 CO-OCCUR WITHIN EPISODES?\n"
    "    Both bands centred on their EPISODE mean (log scale), then Pearson r on the deviations.\n"
    "    NULL = the 18-22 deviations permuted WITHIN each episode, 4000x. Disjoint windows only.")


def episodes_of(cache, pfx, segs, skip, tag):
    """Contiguous runs of the engaged-hands-off-creep mask, cut into DISJOINT windows."""
    eps = []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        er = band_envelope(tq, fs, *RATCH)
        eg = band_envelope(tq, fs, *G1)
        eff = np.abs(sustained(tq, fs))
        m = ((np.abs(np.asarray(d["cs_v"], float)) < CREEP_R)
             & (np.asarray(d["cc_lat"], float) > 0.5) & (eff <= HANDS_OFF))
        for a, b in runs_of(m, d["t"], NFFT):
            cur = []
            for i in range(a, b - NFFT + 1, NFFT):
                w = slice(i, i + NFFT)
                cur.append((float(np.percentile(er[w], 99)), float(np.percentile(eg[w], 99))))
            if len(cur) >= 3:
                eps.append(np.array(cur))
    return eps


def within_ep_corr(eps, nperm=4000):
    """(r, permutation 95% band, p, n windows, n episodes) on episode-centred log deviations."""
    xs, ys, gid = [], [], []
    for k, e in enumerate(eps):
        lx = np.log(np.maximum(e[:, 0], 1e-6))
        ly = np.log(np.maximum(e[:, 1], 1e-6))
        xs.append(lx - lx.mean())
        ys.append(ly - ly.mean())
        gid.append(np.full(len(e), k))
    if not xs:
        return (np.nan,) * 3 + (0, 0)
    X, Y, G = np.concatenate(xs), np.concatenate(ys), np.concatenate(gid)
    if len(X) < 8 or np.std(X) == 0 or np.std(Y) == 0:
        return (np.nan,) * 3 + (len(X), len(eps))
    obs = float(np.corrcoef(X, Y)[0, 1])
    draws = np.empty(nperm)
    for j in range(nperm):
        Yp = np.concatenate([RNG.permutation(y) for y in ys])
        draws[j] = np.corrcoef(X, Yp)[0, 1]
    p = float((np.sum(np.abs(draws) >= abs(obs)) + 1) / (nperm + 1))
    return obs, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)), \
        len(X), len(eps)


print(f"   {'route':10s} {'nwin':>5s} {'neps':>5s} | {'within-episode r':>17s} "
      f"{'permutation null':>20s} {'perm p':>8s}  verdict")
f2 = {}
for tag, (cache, pfx, segs, skip) in ROUTES.items():
    eps = episodes_of(cache, pfx, segs, skip, tag)
    r, lo, hi, n, ne = within_ep_corr(eps)
    f2[tag] = dict(r=r, null=[lo, hi], n=n, neps=ne)
    if not np.isfinite(r):
        print(f"   {tag:10s} {n:>5d} {ne:>5d} |   *** too few windows")
        continue
    v = ("*** POSITIVE co-occurrence" if (r > hi) else
         "*** ANTI-correlated" if (r < lo) else "no relationship")
    _, _, _, _, _ = r, lo, hi, n, ne
    pp = within_ep_corr(eps)[0]
    print(f"   {tag:10s} {n:>5d} {ne:>5d} | {r:>17.3f} [{lo:>8.3f},{hi:>9.3f}] "
          f"{'':>8s}  {v}")
OUT["followup2_within_episode"] = f2

print("\n   ★ POOLED across all builds (episodes are the unit; more power than any single route):")
alleps = []
for tag, (cache, pfx, segs, skip) in ROUTES.items():
    alleps += episodes_of(cache, pfx, segs, skip, tag)
r, lo, hi, n, ne = within_ep_corr(alleps)
print(f"     r = {r:.3f}   permutation null [{lo:.3f}, {hi:.3f}]   n = {n} windows / {ne} episodes")
print(f"     ⇒ {'POSITIVE co-occurrence' if r > hi else 'ANTI-correlated' if r < lo else 'NO RELATIONSHIP -- the two bands do not track each other within episodes'}")
OUT["followup2_pooled"] = dict(r=r, null=[lo, hi], n=n, neps=ne)

# ---------------------------------------------------------------- conditional shapes -------------
hdr("FOLLOW-UP 2b  DO THEY SHARE CONDITIONALS QUANTITATIVELY? Median band envelope by cell,\n"
    "    V72 route 59, so the two bands are compared on the SAME windows.")
rs = ALL[NEW]
print(f"   {'cell':38s} {'n':>5s} | {'6-9 Hz':>9s} {'18-22 Hz':>9s} | {'ratio to eng-h-off-creep':>24s}")
base = [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9]
b6, b18 = np.median([r["er"] for r in base]), np.median([r["eg"] for r in base])
CELLS = {
    "engaged hands-off creep (baseline)": lambda r: (r["v"] < CREEP_R and r["eff"] <= HANDS_OFF
                                                     and r["lat"] > 0.9),
    "engaged hands-ON creep": lambda r: r["v"] < CREEP_R and r["eff"] > HANDS_OFF and r["lat"] > 0.9,
    "MANUAL hands-off creep": lambda r: (r["v"] < CREEP_R and r["eff"] <= HANDS_OFF
                                         and r["lat"] < 0.1),
    "MANUAL hands-ON creep": lambda r: r["v"] < CREEP_R and r["eff"] > HANDS_OFF and r["lat"] < 0.1,
    "engaged hands-off 4-10 m/s": lambda r: (4 <= r["v"] < 10 and r["eff"] <= HANDS_OFF
                                             and r["lat"] > 0.9),
    "engaged hands-off 10-16 m/s": lambda r: (10 <= r["v"] < 16 and r["eff"] <= HANDS_OFF
                                              and r["lat"] > 0.9),
    "engaged hands-off >=16 m/s": lambda r: (r["v"] >= 16 and r["eff"] <= HANDS_OFF
                                             and r["lat"] > 0.9),
}
f2b = {}
for cn, sel in CELLS.items():
    s = [r for r in rs if sel(r)]
    if len(s) < 4:
        print(f"   {cn:38s} {len(s):>5d} |   *** too few")
        continue
    m6, m18 = float(np.median([r["er"] for r in s])), float(np.median([r["eg"] for r in s]))
    f2b[cn] = dict(n=len(s), e69=m6, e1822=m18, r69=m6 / b6, r1822=m18 / b18)
    print(f"   {cn:38s} {len(s):>5d} | {m6:>9.0f} {m18:>9.0f} | "
          f"6-9 x{m6 / b6:>6.3f}   18-22 x{m18 / b18:>6.3f}")
OUT["followup2_conditionals"] = f2b

(ROOT / "_scratch/out/_d4_r59_two_ratchets.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_two_ratchets.json'}")
