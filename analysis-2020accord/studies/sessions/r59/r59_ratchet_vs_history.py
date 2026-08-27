#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §2 IS THE 7.6 Hz LINE THE 7.79 Hz RATCHET, ATTENUATED?

The operator reports the RATCHET FIXED on V72 and a MICRO-RATCHET still present at creep. The
leading hypothesis is that the micro-ratchet IS the ratchet, attenuated but not eliminated. This
file measures the attenuation factor against every prior route, episode-bootstrapped.

INSTRUMENT is `studies/sessions/r58/r58_ratchet.py`, unchanged in every numeric respect (6-9 Hz analytic envelope p99,
AMP_MIN = 600 counts envelope = 1200 p-p, prominence argmax over a FREE 5-12 Hz range, fs from
`_r4f_lib.fs_lattice`, engagement `cc_lat`, hands-off sustained |lowpass(tq,3Hz)| <= 300).

🛑 EPISODES, NOT WINDOWS. An episode is a maximal contiguous run of the cell's own mask inside one
segment. Every CI here resamples EPISODES. A window bootstrap shrinks CIs by ~sqrt(n_per_episode).
🛑 SPLIT-HALF NULL FIRST. No cross-route ratio is quoted before route 59's own within-route
episode-level split-half null is on the page.

Writes `_scratch/out/_r59_ratchet_hist.json`.
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
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
FREE = (5.0, 12.0)
GRIND = (18.0, 22.0)
HANDS_OFF = 300.0
CREEP = 4.0
AMP_MIN = 600.0
RNG = np.random.default_rng(20260805)
OUT = {}

# (cache, prefix, segs, skip)  -- skip = parked/stationary segments, per each route's own record
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


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def scan(tag):
    cache, pfx, segs, skip = ROUTES[tag]
    recs = []
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
        env = band_envelope(tq, fs, *RATCH)
        eng = band_envelope(tq, fs, *GRIND)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fr, pr = peak_prom(f, P, *FREE)
            fb, pb = peak_prom(f, P, *RATCH)
            fg, pg = peak_prom(f, P, *GRIND)
            recs.append(dict(tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                             fr=fr, pr=pr, fb=fb, pb=pb, fg=fg, pg=pg,
                             env99=float(np.percentile(env[w], 99)),
                             eng99=float(np.percentile(eng[w], 99)),
                             v=float(v[w].mean()), lat=float(lat[w].mean()),
                             eff=float(np.median(eff[w])),
                             ang=float(np.median(np.asarray(d["ang"], float)[w]))))
    return recs


ALL = {t: scan(t) for t in ROUTES}


def episodes(rs):
    """Contiguous window runs inside one segment -- the physical event, the bootstrap unit."""
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


def cell(rs, eng=True, hands="off", vhi=CREEP):
    out = [r for r in rs if r["v"] < vhi]
    if eng is True:
        out = [r for r in out if r["lat"] > 0.9]
    elif eng is False:
        out = [r for r in out if r["lat"] < 0.1]
    if hands == "off":
        out = [r for r in out if r["eff"] <= HANDS_OFF]
    elif hands == "on":
        out = [r for r in out if r["eff"] > HANDS_OFF]
    return out


def epboot(rs, key="env99", stat=np.median, nb=4000):
    """Episode-clustered bootstrap of `stat` over window values. Returns (point, lo, hi, neps, nw)."""
    eps = episodes(rs)
    if not eps:
        return np.nan, np.nan, np.nan, 0, 0
    vals = np.array([r[key] for r in rs], float)
    pt = float(stat(vals[np.isfinite(vals)])) if np.isfinite(vals).any() else np.nan
    draws = np.empty(nb)
    for b in range(nb):
        k = RNG.integers(0, len(eps), len(eps))
        v = np.concatenate([[r[key] for r in eps[j]] for j in k])
        v = v[np.isfinite(v)]
        draws[b] = stat(v) if len(v) else np.nan
    return pt, float(np.nanpercentile(draws, 2.5)), float(np.nanpercentile(draws, 97.5)), \
        len(eps), len(rs)


# ================================================================= §1 exposure, matched cells =====
hdr("§1  THE CELL, AND ITS EXPOSURE PER ROUTE -- engaged hands-off creep (<4 m/s)")
print("   🛑 MATCHED SPEED is checked, not assumed: the per-cell speed census is printed. A moving")
print("   wheel order concentrates in a narrow-speed route and smears in a wide one.\n")
print(f"   {'route':10s} {'eps':>4s} {'wins':>5s} {'secs':>7s} | {'v med':>6s} {'v p10':>6s} "
      f"{'v p90':>6s} | {'6-9 env p99 med':>16s} {'p-p med':>8s} {'p-p max':>8s} | "
      f"{'>=1200pp':>9s} {'f0 med':>7s}")
cells, cens = {}, {}
for tag in ROUTES:
    rs = cell(ALL[tag])
    cells[tag] = rs
    if not rs:
        print(f"   {tag:10s} {'--':>4s} {0:>5d}   EMPTY CELL")
        cens[tag] = dict(n=0)
        continue
    v, e = col(rs, "v"), col(rs, "env99")
    fb = col(rs, "fb")
    fb = fb[np.isfinite(fb)]
    nh = int((e >= AMP_MIN).sum())
    cens[tag] = dict(neps=len(episodes(rs)), n=len(rs), secs=len(rs) * NFFT / 100,
                     vmed=float(np.median(v)), v10=float(np.percentile(v, 10)),
                     v90=float(np.percentile(v, 90)), envmed=float(np.median(e)),
                     ppmed=float(2 * np.median(e)), ppmax=float(2 * e.max()),
                     nhit=nh, hitfrac=nh / len(rs),
                     f0=float(np.median(fb)) if len(fb) else np.nan)
    x = cens[tag]
    print(f"   {tag:10s} {x['neps']:>4d} {x['n']:>5d} {x['secs']:>7.1f} | {x['vmed']:>6.2f} "
          f"{x['v10']:>6.2f} {x['v90']:>6.2f} | {x['envmed']:>16.0f} {x['ppmed']:>8.0f} "
          f"{x['ppmax']:>8.0f} | {f'{nh}/{len(rs)}':>9s} {x['f0']:>7.2f}")
OUT["cell_census"] = cens

# ================================================================= §2 THE NULL FIRST ==============
hdr("§2  🛑 THE SPLIT-HALF NULL, WITHIN ROUTE 59 -- the noise floor a cross-route ratio must clear")
print("   Episodes are split at random into two halves; the ratio of their medians is the statistic.")
print("   2,000 random splits. Any cross-route ratio inside this interval is NOT a result.\n")


def splithalf(rs, key="env99", nb=2000):
    eps = episodes(rs)
    if len(eps) < 4:
        return None
    out = []
    for _ in range(nb):
        k = RNG.permutation(len(eps))
        a = np.concatenate([[r[key] for r in eps[j]] for j in k[:len(eps) // 2]])
        b = np.concatenate([[r[key] for r in eps[j]] for j in k[len(eps) // 2:]])
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and np.median(b) > 0:
            out.append(np.median(a) / np.median(b))
    return np.array(out)


nulls = {}
for tag in ("V72 r59", "V71C r58", "V69 r4f", "V67 r47"):
    for lbl, key in (("6-9 Hz env", "env99"), ("18-22 Hz env", "eng99")):
        sh = splithalf(cells[tag], key)
        if sh is None:
            print(f"   {tag:10s} {lbl:14s}  < 4 episodes -- no null available")
            continue
        lo, hi = np.percentile(sh, [2.5, 97.5])
        nulls[f"{tag}|{lbl}"] = dict(lo=float(lo), hi=float(hi), med=float(np.median(sh)))
        print(f"   {tag:10s} {lbl:14s}  split-half ratio  median {np.median(sh):.3f}  "
              f"95% [{lo:.3f}, {hi:.3f}]   (n_eps={len(episodes(cells[tag]))})")
OUT["split_half_null"] = nulls

# ================================================================= §3 the attenuation =============
hdr("§3  ★★ THE ATTENUATION -- route 59's 6-9 Hz amplitude vs every prior route, episode-bootstrapped")
print("   Statistic: median 6-9 Hz analytic-envelope p99 (counts) in engaged hands-off creep.")
print("   Ratio < 1 = V72 is QUIETER. The ratio's CI resamples EPISODES in BOTH arms.\n")
print(f"   {'route':10s} {'eps':>4s} {'median env':>11s} {'95% CI':>20s} | "
      f"{'r59 / route':>12s} {'95% CI':>20s}   verdict")


def ratio_boot(a, b, key="env99", nb=4000):
    ea, eb = episodes(a), episodes(b)
    if not ea or not eb:
        return np.nan, np.nan, np.nan
    va = np.array([r[key] for r in a], float)
    vb = np.array([r[key] for r in b], float)
    pt = float(np.median(va[np.isfinite(va)]) / np.median(vb[np.isfinite(vb)]))
    dr = np.empty(nb)
    for i in range(nb):
        ka = RNG.integers(0, len(ea), len(ea))
        kb = RNG.integers(0, len(eb), len(eb))
        xa = np.concatenate([[r[key] for r in ea[j]] for j in ka])
        xb = np.concatenate([[r[key] for r in eb[j]] for j in kb])
        xa, xb = xa[np.isfinite(xa)], xb[np.isfinite(xb)]
        dr[i] = np.median(xa) / np.median(xb) if len(xa) and len(xb) and np.median(xb) > 0 else np.nan
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


att = {}
r59 = cells["V72 r59"]
p59, l59, h59, ne59, nw59 = epboot(r59)
n59 = nulls.get("V72 r59|6-9 Hz env", {})
for tag in ROUTES:
    rs = cells[tag]
    if not rs:
        continue
    pt, lo, hi, ne, nw = epboot(rs)
    if tag == "V72 r59":
        print(f"   {tag:10s} {ne:>4d} {pt:>11.0f} {f'[{lo:.0f}, {hi:.0f}]':>20s} | "
              f"{'--':>12s} {'(reference)':>20s}")
        continue
    rp, rl, rh = ratio_boot(r59, rs)
    att[tag] = dict(med=pt, lo=lo, hi=hi, neps=ne, ratio=rp, rlo=rl, rhi=rh)
    inside = (n59 and n59["lo"] <= rp <= n59["hi"])
    vd = ("INSIDE route 59's own split-half null -- NOT a result" if inside
          else ("V72 QUIETER" if rh < 1 else ("V72 LOUDER" if rl > 1 else "CI spans 1 -- null")))
    print(f"   {tag:10s} {ne:>4d} {pt:>11.0f} {f'[{lo:.0f}, {hi:.0f}]':>20s} | "
          f"{rp:>12.3f} {f'[{rl:.3f}, {rh:.3f}]':>20s}   {vd}")
OUT["attenuation_6_9"] = att
OUT["r59_ref"] = dict(med=p59, lo=l59, hi=h59, neps=ne59, nwin=nw59)

# ================================================================= §4 the hit-rate view ===========
hdr("§4  THE RECORD'S OWN CRITERION -- fraction of engaged hands-off creep windows >= 1200 counts p-p")
print("   This is the criterion `studies/sessions/r58/r58_ratchet.py` used to call the ratchet PRESENT. Fisher vs route 59.\n")
print(f"   {'route':10s} {'hits/n':>10s} {'rate':>7s} {'secs over':>10s} | {'Fisher vs r59':>14s}")
hitrate = {}
a11 = sum(1 for r in r59 if r["env99"] >= AMP_MIN)
for tag in ROUTES:
    rs = cells[tag]
    if not rs:
        continue
    h = sum(1 for r in rs if r["env99"] >= AMP_MIN)
    p = (fisher2x2(a11, len(r59) - a11, h, len(rs) - h) if tag != "V72 r59" else np.nan)
    hitrate[tag] = dict(hit=h, n=len(rs), rate=h / len(rs), secs=h * NFFT / 100, fisher=float(p))
    print(f"   {tag:10s} {f'{h}/{len(rs)}':>10s} {100 * h / len(rs):>6.1f}% "
          f"{h * NFFT / 100:>10.1f} | {p:>14.3g}")
OUT["hitrate"] = hitrate

# ================================================================= §5 f0 identity =================
hdr("§5  IS IT THE SAME LINE? f0 of the 6-9 Hz peak, per route, over amplitude hits only")
print(f"   {'route':10s} {'n hits':>7s} {'f0 med':>7s} {'95% CI (episode)':>22s} {'f0 free 5-12':>13s}")
f0t = {}
for tag in ROUTES:
    h = [r for r in cells[tag] if r["env99"] >= AMP_MIN]
    if len(h) < 2:
        h2 = [r for r in ALL[tag] if r["env99"] >= AMP_MIN and r["v"] < CREEP]
        print(f"   {tag:10s} {len(h):>7d}   (cell too small; all-hands creep n={len(h2)})")
        if len(h2) >= 2:
            h = h2
        else:
            continue
    pt, lo, hi, ne, nw = epboot(h, "fb")
    ptf, _, _, _, _ = epboot(h, "fr")
    f0t[tag] = dict(n=len(h), f0=pt, lo=lo, hi=hi, free=ptf)
    print(f"   {tag:10s} {len(h):>7d} {pt:>7.3f} {f'[{lo:.3f}, {hi:.3f}]':>22s} {ptf:>13.3f}")
OUT["f0_by_route"] = f0t

json.dump(OUT, open(ROOT / "_scratch/out/_r59_ratchet_hist.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_scratch/out/_r59_ratchet_hist.json'}")
