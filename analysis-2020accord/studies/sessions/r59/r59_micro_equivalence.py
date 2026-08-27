#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §5 THE EQUIVALENCE TEST: is the micro-ratchet grind #1 at lower amplitude?

THE OPERATOR'S QUESTION, in his words: "A micro-ratcheting effect is still present at creep speed,
though it is not audible or mechanically heavy and is only felt in the steering column and wheel.
I suspect this micro-ratcheting is a lower-amplitude continuation of Grind Number 1."

Route 59's engaged creep carries TWO strong lines, ~7.7 Hz and ~20.3 Hz. This file asks whether
they are one phenomenon or two. Claiming they are the same needs more than "both exist at creep":

  §1  SAME CENTRE FREQUENCY?      free locators, episode-bootstrapped CIs, and the joint histogram.
  §2  DO THEY TRACK?              🛑 A RATIO IS NOT A TRACKING TEST (memory:
                                  feedback-a-ratio-is-not-a-tracking-test). Theil-Sen SLOPE of
                                  f_hi on f_lo, WITH the shuffled-pairing control that killed the
                                  kit's retracted harmonic claim. The ratio is printed beside its
                                  own shuffle so the failure mode is visible on the page.
  §3  DO THEY CO-OCCUR?           within-episode envelope correlation at 0.32 s resolution, with
                                  TWO controls: shuffled episode pairing, and CONTROL BANDS. If
                                  r(6-9, 18-22) is no higher than r(6-9, 10.5-13.5), the
                                  co-occurrence is "everything rises together", not a mechanism.
  §4  ONE MODE OR TWO?            lognormal mixture BIC on each band's amplitude, and the JOINT
                                  amplitude plane -- windows loud in one band and quiet in the
                                  other are the decisive observation.

Every CI resamples EPISODES (memory: feedback-episodes-not-windows). Writes `_scratch/out/_r59_equivalence.json`.
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
from _r31_common import band_envelope, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r37_ratchet_lib as R37  # noqa: E402

NFFT = 256
RATCH, GRIND = (6.0, 9.0), (18.0, 22.0)
FREE_R, FREE_G = (5.0, 12.0), (17.0, 26.0)
CTRL_A, CTRL_B = (10.5, 13.5), (24.0, 27.0)
CREEP, VMIN = 4.0, 0.3
ANG0 = -4.40                    # route 59's own straight-ahead, median `ang` over v>20 engaged
RNG = np.random.default_rng(20260805)
CACHE, PFX, SEGS = ROOT / "_scratch/cache/r59", "r59s", list(range(12))
OUT = {}


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


# ---------------------------------------------------------------- the scan -----------------------
def scan():
    recs = []
    for s in SEGS:
        p = CACHE / f"{PFX}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, CACHE, PFX)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        ev = {k: band_envelope(tq, fs, *b) for k, b in
              (("r", RATCH), ("g", GRIND), ("ca", CTRL_A), ("cb", CTRL_B))}
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fr, pr = R37.locate(f, P, *FREE_R)
            fg, pg = R37.locate(f, P, *FREE_G)
            r = dict(seg=int(s), i0=i, t0=float(t[i]), fs=fs, fr=fr, pr=pr, fg=fg, pg=pg,
                     v=float(v[w].mean()), lat=float(lat[w].mean()),
                     eff=float(np.median(eff[w])),
                     ang=float(np.median(ang[w])), angc=float(np.median(ang[w]) - ANG0),
                     absangc=float(np.median(np.abs(ang[w] - ANG0))),
                     rate90=float(np.percentile(np.abs(d["rate_c"][w]), 90)),
                     rpm=float(np.nanmean(d["rpm"][w])),
                     e4=float(np.percentile(np.abs(d["e4tq"][w]), 90)))
            for k in ev:
                r["pp_" + k] = float(2 * np.percentile(ev[k][w], 99))
            recs.append(r)
    return recs


ALL = scan()
CELL = [r for r in ALL if r["lat"] > 0.9 and VMIN <= r["v"] < CREEP]
MAN = [r for r in ALL if r["lat"] < 0.1 and VMIN <= r["v"] < CREEP]


def episodes(rs):
    eps, cur = [], []
    for r in sorted(rs, key=lambda r: (r["seg"], r["i0"])):
        if cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT:
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r]
    if cur:
        eps.append(cur)
    return eps


EPS = episodes(CELL)
print(f"ENGAGED MOVING CREEP CELL ({VMIN} <= |v| < {CREEP} m/s, cc_lat > 0.9): "
      f"{len(CELL)} disjoint windows = {len(CELL) * NFFT / 100:.1f} s in {len(EPS)} episodes")
print(f"  episode lengths (windows): {sorted((len(e) for e in EPS), reverse=True)}")
print(f"MANUAL moving creep control: {len(MAN)} windows = {len(MAN) * NFFT / 100:.1f} s in "
      f"{len(episodes(MAN))} episodes")
OUT["cell"] = dict(n=len(CELL), secs=len(CELL) * NFFT / 100, neps=len(EPS),
                   man_n=len(MAN), man_secs=len(MAN) * NFFT / 100)


def epboot(rs, key, stat=np.median, nb=4000):
    eps = episodes(rs)
    v = np.array([r[key] for r in rs], float)
    v = v[np.isfinite(v)]
    if not len(v) or not eps:
        return np.nan, np.nan, np.nan
    dr = np.empty(nb)
    for b in range(nb):
        k = RNG.integers(0, len(eps), len(eps))
        x = np.concatenate([[r[key] for r in eps[j]] for j in k])
        x = x[np.isfinite(x)]
        dr[b] = stat(x) if len(x) else np.nan
    return float(stat(v)), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


# ================================================================= §1 centre frequencies ==========
hdr("§1  SAME CENTRE FREQUENCY?  free locators (5-12 Hz and 17-26 Hz), episode-bootstrapped")
f1 = {}
for lbl, key in (("low  line (free 5-12 Hz)", "fr"), ("high line (free 17-26 Hz)", "fg")):
    m, lo, hi = epboot(CELL, key)
    vals = np.array([r[key] for r in CELL], float)
    vals = vals[np.isfinite(vals)]
    f1[key] = dict(med=m, lo=lo, hi=hi, p10=float(np.percentile(vals, 10)),
                   p90=float(np.percentile(vals, 90)), n=len(vals))
    print(f"   {lbl:28s} median {m:6.3f} Hz   95% CI [{lo:.3f}, {hi:.3f}]   "
          f"p10-p90 {np.percentile(vals, 10):.2f}-{np.percentile(vals, 90):.2f}   n={len(vals)}")
print("\n   The joint histogram of every located line, 2-60 Hz, engaged creep (0.5 Hz bins):")
allf = np.concatenate([[r["fr"] for r in CELL], [r["fg"] for r in CELL]])
h, e = np.histogram(allf[np.isfinite(allf)], bins=np.arange(2, 60.5, 0.5))
for j in range(len(h)):
    if h[j]:
        print(f"      {e[j]:5.1f}-{e[j + 1]:5.1f} Hz  {'#' * h[j]} ({h[j]})")
OUT["f0"] = f1

# ================================================================= §2 the tracking test ===========
hdr("§2  🛑 DO THEY TRACK?  Theil-Sen SLOPE of f_high on f_low -- WITH the shuffled-pairing control")
print("   If the high line is a harmonic/multiple of the low one, f_high must MOVE WITH f_low:")
print("   a SLOPE, not a ratio. The ratio is printed beside its own shuffle to show that a ratio")
print("   survives destruction of the pairing and therefore carries no pairing information.\n")


def theilsen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 3:
        return np.nan
    i, j = np.triu_indices(len(x), 1)
    dx = x[j] - x[i]
    k = np.abs(dx) > 1e-9
    return float(np.median((y[j] - y[i])[k] / dx[k])) if k.any() else np.nan


def slope_boot(rs, nb=3000):
    eps = episodes(rs)
    pt = theilsen([r["fr"] for r in rs], [r["fg"] for r in rs])
    dr = np.empty(nb)
    for b in range(nb):
        k = RNG.integers(0, len(eps), len(eps))
        w = [r for j in k for r in eps[j]]
        dr[b] = theilsen([r["fr"] for r in w], [r["fg"] for r in w])
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def shuffle_stats(rs, nb=3000):
    fr = np.array([r["fr"] for r in rs], float)
    fg = np.array([r["fg"] for r in rs], float)
    sl, ra = np.empty(nb), np.empty(nb)
    for b in range(nb):
        p = RNG.permutation(len(fg))
        sl[b] = theilsen(fr, fg[p])
        ra[b] = np.median(fg[p] / fr)
    return sl, ra


s_pt, s_lo, s_hi = slope_boot(CELL)
sh_sl, sh_ra = shuffle_stats(CELL)
obs_ratio = float(np.median(np.array([r["fg"] for r in CELL]) / np.array([r["fr"] for r in CELL])))
print(f"   OBSERVED  slope  d(f_high)/d(f_low) = {s_pt:+.4f}   95% CI [{s_lo:+.4f}, {s_hi:+.4f}]  "
      f"(episode bootstrap)")
print(f"   SHUFFLED  slope                      = {np.median(sh_sl):+.4f}   95% "
      f"[{np.percentile(sh_sl, 2.5):+.4f}, {np.percentile(sh_sl, 97.5):+.4f}]")
print(f"   OBSERVED  ratio  f_high / f_low      = {obs_ratio:.4f}")
print(f"   SHUFFLED  ratio                      = {np.median(sh_ra):.4f}   95% "
      f"[{np.percentile(sh_ra, 2.5):.4f}, {np.percentile(sh_ra, 97.5):.4f}]")
print(f"\n   ⇒ the RATIO survives shuffling ({obs_ratio:.3f} vs {np.median(sh_ra):.3f}) -- it is a")
print("     property of the two MARGINALS and carries no information about a shared mechanism.")
harm = (s_lo <= 2.0 <= s_hi)
zero = (s_lo <= 0.0 <= s_hi)
print(f"   ⇒ the SLOPE: 2.0 {'INSIDE' if harm else 'EXCLUDED from'} the CI; "
      f"0.0 {'INSIDE' if zero else 'EXCLUDED from'} the CI.")
OUT["tracking"] = dict(slope=s_pt, lo=s_lo, hi=s_hi, sh_slope=float(np.median(sh_sl)),
                       sh_lo=float(np.percentile(sh_sl, 2.5)),
                       sh_hi=float(np.percentile(sh_sl, 97.5)),
                       ratio=obs_ratio, sh_ratio=float(np.median(sh_ra)))

# ================================================================= §3 co-occurrence ===============
hdr("§3  ★★ DO THEIR ENVELOPES RISE AND FALL TOGETHER, WITHIN EPISODES?")
print("   0.32 s envelope bins inside each episode, Spearman per episode, Fisher-z averaged.")
print("   TWO controls: (a) SHUFFLED PAIRING across episodes, (b) CONTROL BANDS 10.5-13.5 and")
print("   24-27 Hz. If r(6-9, 18-22) is no bigger than r(6-9, control), everything just rises")
print("   together and there is no shared mechanism to speak of.\n")
BIN = 32                        # samples = 0.32 s


def ep_env(ep):
    """Per-episode binned envelopes for all four bands, as {band: array}."""
    d = C.load(ep[0]["seg"], CACHE, PFX)
    fs = R4F.fs_lattice(d)
    tq = np.asarray(d["tq"], float)
    a, b = ep[0]["i0"], ep[-1]["i0"] + NFFT
    out = {}
    for k, bd in (("r", RATCH), ("g", GRIND), ("ca", CTRL_A), ("cb", CTRL_B)):
        e = band_envelope(tq[a:b], fs, *bd)
        n = len(e) // BIN
        out[k] = np.array([e[i * BIN:(i + 1) * BIN].mean() for i in range(n)])
    return out


def spearman(x, y):
    if len(x) < 5:
        return np.nan
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def fisher_mean(rs):
    rs = np.array([r for r in rs if np.isfinite(r)])
    if not len(rs):
        return np.nan
    z = np.arctanh(np.clip(rs, -0.999, 0.999))
    return float(np.tanh(np.mean(z)))


ENVS = [ep_env(e) for e in EPS if len(e) >= 2]
print(f"   {len(ENVS)} episodes with >= 2 windows; "
      f"{sum(len(e['r']) for e in ENVS)} envelope bins total\n")
pairs = {"6-9 vs 18-22 (THE TEST)": ("r", "g"), "6-9 vs 10.5-13.5 (control)": ("r", "ca"),
         "6-9 vs 24-27 (control)": ("r", "cb"), "18-22 vs 24-27 (control)": ("g", "cb"),
         "18-22 vs 10.5-13.5 (control)": ("g", "ca")}
print(f"   {'pair':30s} {'per-episode r (Fisher mean)':>28s} {'95% CI (episode boot)':>24s} "
      f"{'SHUFFLED PAIRING':>20s}")
cooc = {}
for lbl, (ka, kb) in pairs.items():
    per = [spearman(e[ka], e[kb]) for e in ENVS]
    pt = fisher_mean(per)
    dr = np.empty(3000)
    for b in range(3000):
        k = RNG.integers(0, len(per), len(per))
        dr[b] = fisher_mean([per[j] for j in k])
    # shuffled pairing: episode i's band-a envelope against episode j's band-b envelope
    sh = np.empty(2000)
    for b in range(2000):
        vals = []
        for i in range(len(ENVS)):
            j = RNG.integers(0, len(ENVS))
            if j == i:
                j = (j + 1) % len(ENVS)
            x, y = ENVS[i][ka], ENVS[j][kb]
            n = min(len(x), len(y))
            if n >= 5:
                vals.append(spearman(x[:n], y[:n]))
        sh[b] = fisher_mean(vals)
    cooc[lbl] = dict(r=pt, lo=float(np.nanpercentile(dr, 2.5)),
                     hi=float(np.nanpercentile(dr, 97.5)), sh=float(np.nanmedian(sh)),
                     sh_lo=float(np.nanpercentile(sh, 2.5)), sh_hi=float(np.nanpercentile(sh, 97.5)))
    x = cooc[lbl]
    print(f"   {lbl:30s} {pt:>28.4f} {f'[{x[chr(108) + chr(111)]:+.3f}, {x[chr(104) + chr(105)]:+.3f}]':>24s} "
          f"{f'{x[chr(115) + chr(104)]:+.3f} [{x[chr(115) + chr(104) + chr(95) + chr(108) + chr(111)]:+.3f},{x[chr(115) + chr(104) + chr(95) + chr(104) + chr(105)]:+.3f}]':>20s}")
OUT["cooccurrence"] = cooc

# ================================================================= §4 one mode or two =============
hdr("§4  ★★ ONE MODE OR TWO?  the joint amplitude plane, engaged creep")
print("   If the micro-ratchet were grind #1 at low amplitude, the two bands would be ONE quantity")
print("   at two levels: every window loud in one would be loud in the other. Count the corners.\n")
ppr = np.array([r["pp_r"] for r in CELL])
ppg = np.array([r["pp_g"] for r in CELL])
mr, mg = 1200.0, 1200.0
q = {"both LOUD": int(((ppr >= mr) & (ppg >= mg)).sum()),
     "6-9 loud, 18-22 quiet": int(((ppr >= mr) & (ppg < mg)).sum()),
     "6-9 quiet, 18-22 loud": int(((ppr < mr) & (ppg >= mg)).sum()),
     "both quiet": int(((ppr < mr) & (ppg < mg)).sum())}
for k, n in q.items():
    print(f"   {k:26s} {n:>4d} windows ({100 * n / len(CELL):5.1f}%)  = {n * 2.56:5.1f} s")
print(f"\n   Spearman(pp 6-9, pp 18-22) over windows = "
      f"{spearman(ppr, ppg):+.4f}   (n={len(CELL)})")
r_pt = spearman(ppr, ppg)
dr = np.empty(3000)
for b in range(3000):
    k = RNG.integers(0, len(EPS), len(EPS))
    w = [r for j in k for r in EPS[j]]
    dr[b] = spearman(np.array([r["pp_r"] for r in w]), np.array([r["pp_g"] for r in w]))
print(f"   episode-bootstrap 95% CI [{np.nanpercentile(dr, 2.5):+.4f}, "
      f"{np.nanpercentile(dr, 97.5):+.4f}]")
OUT["joint_amp"] = dict(quadrants=q, spearman=r_pt, lo=float(np.nanpercentile(dr, 2.5)),
                        hi=float(np.nanpercentile(dr, 97.5)))

print("\n   --- MIXTURE BIC: is each band's amplitude ONE lognormal population or TWO?")


def lognorm_bic(x):
    x = np.asarray([v for v in x if v > 0], float)
    y = np.log(x)
    n = len(y)
    ll1 = -0.5 * n * (np.log(2 * np.pi * y.var()) + 1)
    bic1 = -2 * ll1 + 2 * np.log(n)
    # 2-component EM
    mu = np.array([np.percentile(y, 25), np.percentile(y, 75)])
    sd = np.array([y.std() / 2, y.std() / 2])
    w = np.array([0.5, 0.5])
    for _ in range(400):
        p = np.array([w[k] * np.exp(-0.5 * ((y - mu[k]) / sd[k]) ** 2) / (sd[k] * np.sqrt(2 * np.pi))
                      for k in range(2)])
        s = p.sum(0)
        s[s <= 0] = 1e-300
        g = p / s
        w = g.mean(1)
        mu = (g * y).sum(1) / g.sum(1)
        sd = np.sqrt(np.maximum((g * (y - mu[:, None]) ** 2).sum(1) / g.sum(1), 1e-6))
    p = np.array([w[k] * np.exp(-0.5 * ((y - mu[k]) / sd[k]) ** 2) / (sd[k] * np.sqrt(2 * np.pi))
                  for k in range(2)])
    ll2 = float(np.log(np.maximum(p.sum(0), 1e-300)).sum())
    bic2 = -2 * ll2 + 5 * np.log(n)
    return bic1, bic2, np.exp(mu), w, n


mix = {}
for lbl, x in (("6-9 Hz p-p", ppr), ("18-22 Hz p-p", ppg)):
    b1, b2, m2, w2, n = lognorm_bic(x)
    mix[lbl] = dict(bic1=b1, bic2=b2, means=list(m2), weights=list(w2), n=n)
    better = "TWO components" if b2 < b1 - 2 else "ONE component"
    print(f"   {lbl:14s} n={n:3d}  BIC(1)={b1:8.2f}  BIC(2)={b2:8.2f}  dBIC={b1 - b2:+8.2f}  "
          f"⇒ {better}")
    if b2 < b1 - 2:
        print(f"                  components at {m2[0]:.0f} and {m2[1]:.0f} counts p-p, "
              f"weights {w2[0]:.2f}/{w2[1]:.2f}")
OUT["mixture"] = mix

json.dump(OUT, open(ROOT / "_scratch/out/_r59_equivalence.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_scratch/out/_r59_equivalence.json'}")
