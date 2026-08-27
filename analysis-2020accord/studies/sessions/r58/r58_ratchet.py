#!/usr/bin/env python3
"""ROUTES 54 (V71B) and 58 (V71C) -- THE RATCHET, and the verdict on `0x454FE`.

🛑🛑 THE POINT OF THIS FILE. Both V71B and V71C carry `0x454FE` RESTORED -- V42's state-4 governor
kill, the kit's last standing ratchet candidate, which has been OFF THE CAR since V53. The operator
reports the ratchet UNCHANGED on both. These two routes are also the longest in the recent corpus
(1101.8 s and 713.3 s of driving), so this is the best-powered ratchet measurement the kit has.
If the numbers agree with the operator, `0x454FE` is FALSIFIED for the current ratchet.

INSTRUMENT is `studies/sessions/r50/r50_ratchet.py` / `studies/sessions/r4f/r4f_ratchet_inventory.py`, unchanged in every numeric respect:
  * DISJOINT 2.56 s windows (NFFT 256, 0.39 Hz bins) -- window counts are sample counts.
  * PROMINENCE argmax over a FREE 5-12 Hz range, never the raw-power argmax.
  * Every prominence beside a PHYSICAL amplitude (6-9 Hz analytic envelope p99; p-p = 2x).
  * AMP_MIN = 600 counts envelope = 1200 counts p-p -- the record's own criterion.
  * fs = `_r4f_lib.fs_lattice`, the kit's standing estimator.
  * ENGAGEMENT is `carControl.latActive`; HANDS-OFF is sustained |lowpass(tq,3Hz)| <= 300.

Writes `_scratch/out/_r58_ratchet.json`.  Usage: python studies/sessions/r58/r58_ratchet.py
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
from _r31_common import band_envelope, peak_prom, periodogram, q_of, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
FREE = (5.0, 12.0)
CTRL_A = (10.5, 13.5)
CTRL_B = (24.0, 27.0)
HANDS_OFF = 300.0
CREEP_R = 4.0               # m/s -- the ratchet's own creep cell
AMP_MIN = 600.0             # envelope p99; p-p = 1200
CIRC_LO = 2.073
OUT = {}

# ★ `has454` marks whether the flown image carries V42's state-4 governor kill at 0x454FE.
ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], [], False),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), [], False),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), [], False),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), [], False),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0], False),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11], True),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15], True),
}
NEW = ["V71B r54", "V71C r58"]


def hdr(s):
    print("\n" + "=" * 118 + f"\n{s}\n" + "=" * 118)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def bp(x, fs, lo, hi):
    z = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(z)
    f = np.fft.rfftfreq(len(z), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(z))


def zcross(x, fs, lo, hi):
    """Upward-zero-crossing rate of the band-passed signal -- an f0 estimate with NO FFT bin in it."""
    b = bp(x, fs, lo, hi)
    sg = np.signbit(b)
    idx = np.flatnonzero(sg[:-1] & ~sg[1:])
    return float(fs / np.mean(np.diff(idx))) if len(idx) >= 3 else np.nan


def scan(cache, pfx, segs, skip, tag):
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
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fr, pr = peak_prom(f, P, *FREE)
            fb, pbv = peak_prom(f, P, *RATCH)
            _, pca = peak_prom(f, P, *CTRL_A)
            _, pcb = peak_prom(f, P, *CTRL_B)
            recs.append(dict(tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs, cache=cache,
                             pfx=pfx, fr=fr, pr=pr, fb=fb, pb=pbv, pca=pca, pcb=pcb,
                             env99=float(np.percentile(env[w], 99)),
                             Q=q_of(f, P, fb, *RATCH) if np.isfinite(fb) else np.nan,
                             zc=zcross(tq[w], fs, *RATCH),
                             v=float(v[w].mean()), vmin=float(v[w].min()), vmax=float(v[w].max()),
                             ang=float(np.mean(np.abs(d["ang"][w]))),
                             rate90=float(np.percentile(np.abs(d["rate_c"][w]), 90)),
                             eff=float(np.median(eff[w])), lat=float(lat[w].mean()),
                             e4=float(np.percentile(np.abs(d["e4tq"][w]), 99))))
    return recs


ALL = {tag: scan(c, p, s, sk, tag) for tag, (c, p, s, sk, _) in ROUTES.items()}

# =============================================================== §1 the null ======================
hdr("§1  THE NULL FIRST -- two control bands, per route. The LARGER (conservative) floor is used.")
print(f"   {'route':10s} {'wins':>6s} {'route s':>8s} | {'NULL-A 10.5-13.5':>18s} "
      f"{'NULL-B 24-27':>14s} | {'floor':>7s}")
floors = {}
for tag, rs in ALL.items():
    a, b = col(rs, "pca"), col(rs, "pcb")
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    fa = float(np.percentile(a, 95)) if len(a) else np.nan
    fbv = float(np.percentile(b, 95)) if len(b) else np.nan
    floors[tag] = float(np.nanmax([fa, fbv]))
    print(f"   {tag:10s} {len(rs):>6d} {len(rs) * NFFT / 100:>8.1f} | p95 {fa:>13.2f} "
          f"p95 {fbv:>9.2f} | {floors[tag]:>7.2f}")
OUT["floors"] = floors

# =============================================================== §2 amplitude inventory ===========
hdr(f"§2  ★★ AMPLITUDE INVENTORY -- 6-9 Hz envelope p99 >= {AMP_MIN:.0f} counts "
    f"(p-p >= {2 * AMP_MIN:.0f}). The record's own criterion.")
print(f"   record (route 4f): 46 windows / 118 s, peak 6,065 counts p-p, median f0 7.79 Hz, "
      f"44/46 engaged.\n")
print(f"   {'route':10s} {'0x454FE':>8s} {'wins':>6s} {'route s':>8s} | {'>=1200 pp':>10s} "
      f"{'secs':>7s} {'% route':>8s} | {'max pp':>8s} {'f0 spec':>8s} {'f0 zc':>7s} {'Q med':>6s} "
      f"{'eng':>4s} {'man':>4s} {'Fisher p':>10s}")
inv = {}
for tag, rs in ALL.items():
    h = [r for r in rs if r["env99"] >= AMP_MIN]
    z = col(h, "zc") if h else np.array([])
    z = z[np.isfinite(z)]
    fbv = col(h, "fb") if h else np.array([])
    fbv = fbv[np.isfinite(fbv)]
    qv = col(h, "Q") if h else np.array([])
    qv = qv[np.isfinite(qv)]
    lt = col(h, "lat") if h else np.array([])
    lat_all = col(rs, "lat") > 0.5
    hit_all = col(rs, "env99") >= AMP_MIN
    a11, a10 = int((hit_all & lat_all).sum()), int((~hit_all & lat_all).sum())
    a01, a00 = int((hit_all & ~lat_all).sum()), int((~hit_all & ~lat_all).sum())
    p = fisher2x2(a11, a10, a01, a00) if (a11 + a01) else np.nan
    inv[tag] = dict(has454=ROUTES[tag][4], nwin=len(rs), route_s=len(rs) * NFFT / 100,
                    nhit=len(h), hit_s=len(h) * NFFT / 100, frac=len(h) / max(len(rs), 1),
                    maxpp=float(2 * max(col(rs, "env99"))) if rs else np.nan,
                    f0=float(np.median(fbv)) if len(fbv) else np.nan,
                    zc=float(np.median(z)) if len(z) else np.nan,
                    Q=float(np.median(qv)) if len(qv) else np.nan,
                    eng=int((lt > 0.9).sum()) if len(lt) else 0,
                    man=int((lt < 0.1).sum()) if len(lt) else 0, fisher=float(p))
    x = inv[tag]
    print(f"   {tag:10s} {('YES' if x['has454'] else 'no'):>8s} {x['nwin']:>6d} "
          f"{x['route_s']:>8.1f} | {x['nhit']:>10d} {x['hit_s']:>7.1f} {100 * x['frac']:>7.2f}% | "
          f"{x['maxpp']:>8.0f} {x['f0']:>8.2f} {x['zc']:>7.2f} {x['Q']:>6.1f} {x['eng']:>4d} "
          f"{x['man']:>4d} {x['fisher']:>10.3g}")
OUT["inventory"] = inv

# =============================================================== §3 THE HEADLINE 2x2 ==============
hdr("§3  ★★★ THE HEADLINE TEST -- engaged hands-off creep vs manual hands-off creep")
print(f"   Both arms |lowpass(tq,3Hz)| <= {HANDS_OFF:.0f}, creep < {CREEP_R:.0f} m/s. This removes the")
print("   hand-on-the-wheel confound entirely. POOLED PRIOR across four builds: 73/88 = 83% engaged")
print("   vs 0/118 = 0% manual, BUILD-INDEPENDENT.\n")
print(f"   {'route':10s} {'0x454FE':>8s} | {'eng hands-off':>18s} {'man hands-off':>18s} "
      f"{'Fisher p':>10s}   verdict")
cx = {}
for tag, rs in ALL.items():
    cr = [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF]
    a = [r for r in cr if r["lat"] > 0.9]
    b = [r for r in cr if r["lat"] < 0.1]
    a11 = sum(1 for r in a if r["env99"] >= AMP_MIN)
    a01 = sum(1 for r in b if r["env99"] >= AMP_MIN)
    if not a or not b:
        print(f"   {tag:10s} {('YES' if ROUTES[tag][4] else 'no'):>8s} | "
              f"{f'{a11}/{len(a)}':>18s} {f'{a01}/{len(b)}':>18s} {'--':>10s}   one arm EMPTY")
        cx[tag] = dict(has454=ROUTES[tag][4], eng_hit=a11, eng_n=len(a), man_hit=a01, man_n=len(b),
                       p=None)
        continue
    p = fisher2x2(a11, len(a) - a11, a01, len(b) - a01)
    cx[tag] = dict(has454=ROUTES[tag][4], eng_hit=a11, eng_n=len(a), man_hit=a01, man_n=len(b),
                   p=float(p), eng_rate=a11 / len(a), man_rate=a01 / len(b))
    print(f"   {tag:10s} {('YES' if ROUTES[tag][4] else 'no'):>8s} | "
          f"{f'{a11}/{len(a)} = {100 * a11 / len(a):.0f}%':>18s} "
          f"{f'{a01}/{len(b)} = {100 * a01 / len(b):.0f}%':>18s} {p:>10.3g}   "
          f"{'ENGAGEMENT REQUIRED' if p < 0.05 else 'not separable at this n'}")
OUT["headline_2x2"] = cx

print("\n   ★★ THE 0x454FE VERDICT -- pooled by whether the flown image carries the edit")
grp = {}
for has in (False, True):
    ks = [k for k in cx if cx[k]["has454"] == has]
    ea = sum(cx[k]["eng_hit"] for k in ks)
    en = sum(cx[k]["eng_n"] for k in ks)
    ma = sum(cx[k]["man_hit"] for k in ks)
    mn = sum(cx[k]["man_n"] for k in ks)
    grp[has] = (ea, en, ma, mn, ks)
    print(f"     0x454FE {'RESTORED' if has else 'ABSENT  '}  ({', '.join(ks)})")
    print(f"       engaged hands-off {ea}/{en} = {100 * ea / max(en, 1):5.1f}%    "
          f"manual hands-off {ma}/{mn} = {100 * ma / max(mn, 1):5.1f}%")
ea0, en0, _, _, _ = grp[False]
ea1, en1, _, _, _ = grp[True]
pv = fisher2x2(ea1, en1 - ea1, ea0, en0 - ea0)
print(f"\n     ⇒ ENGAGED HANDS-OFF CREEP HIT RATE, restored vs absent: "
      f"{100 * ea1 / max(en1, 1):.1f}% vs {100 * ea0 / max(en0, 1):.1f}%   Fisher p = {pv:.4g}")
print(f"       {'0x454FE DID NOT REMOVE THE RATCHET -- FALSIFIED' if pv > 0.05 or ea1 / max(en1, 1) >= ea0 / max(en0, 1) else 'the edit reduced the rate; investigate'}")
OUT["v454fe_verdict"] = dict(restored=[ea1, en1], absent=[ea0, en0], fisher=float(pv))

# =============================================================== §4 grip direction ================
hdr("§4  THE OTHER DIRECTION -- does a HAND ON THE WHEEL kill it while engaged?")
print(f"   {'route':10s} {'eng hands-OFF':>19s} {'eng hands-ON':>19s} {'Fisher p':>10s}")
gx = {}
for tag, rs in ALL.items():
    cr = [r for r in rs if r["v"] < CREEP_R and r["lat"] > 0.9]
    a = [r for r in cr if r["eff"] <= HANDS_OFF]
    b = [r for r in cr if r["eff"] > HANDS_OFF]
    if not a or not b:
        print(f"   {tag:10s}   *** one arm EMPTY (off n={len(a)}, on n={len(b)})")
        continue
    a11 = sum(1 for r in a if r["env99"] >= AMP_MIN)
    a01 = sum(1 for r in b if r["env99"] >= AMP_MIN)
    p = fisher2x2(a11, len(a) - a11, a01, len(b) - a01)
    gx[tag] = dict(off_hit=a11, off_n=len(a), on_hit=a01, on_n=len(b), p=float(p))
    print(f"   {tag:10s} {f'{a11}/{len(a)} = {100 * a11 / len(a):.0f}%':>19s} "
          f"{f'{a01}/{len(b)} = {100 * a01 / len(b):.0f}%':>19s} {p:>10.3g}")
OUT["grip"] = gx

# =============================================================== §5 speed slope ===================
hdr("§5  SPEED DEPENDENCE -- Theil-Sen slope of f0 on speed over the amplitude hits")
print(f"   Wheel order 1 would give {1 / CIRC_LO:.3f} Hz per m/s. The record's ratchet slope is "
      f"+0.0358 (speed-invariant).\n")


def theilsen(x, y, nboot=3000, rng=np.random.default_rng(20260804)):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 3:
        return np.nan, np.nan, np.nan, len(x)

    def sl(xx, yy):
        i, j = np.triu_indices(len(xx), 1)
        dx = xx[j] - xx[i]
        k = np.abs(dx) > 1e-9
        return float(np.median((yy[j] - yy[i])[k] / dx[k])) if k.any() else np.nan
    pt = sl(x, y)
    dr = np.empty(nboot)
    for bi in range(nboot):
        k = rng.integers(0, len(x), len(x))
        dr[bi] = sl(x[k], y[k])
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), len(x)


sp = {}
for tag, rs in ALL.items():
    h = [r for r in rs if r["env99"] >= AMP_MIN]
    for lbl, key in (("zero-crossing", "zc"), ("spectral", "fb")):
        s, lo, hi, n = theilsen(col(h, "v"), col(h, key))
        sp[f"{tag}|{lbl}"] = dict(slope=s, lo=lo, hi=hi, n=n)
        print(f"   {tag:10s} {lbl:14s} slope {s:+8.4f} Hz per m/s  [{lo:+7.4f}, {hi:+7.4f}]  "
              f"n={n:3d}   {'⇒ SPEED-INVARIANT (wheel-1 excluded)' if np.isfinite(hi) and hi < 0.2 else ''}")
OUT["speed_slope"] = sp

# =============================================================== §6 Q, with the cap test ==========
hdr("§6  ★ Q -- longest contiguous amplitude episodes re-cut at NFFT 256/512/1024/2048")
print("   THE WINDOW-CAP INVARIANCE TEST: the Hann main lobe caps a measurable Q at f0/(1.44*fs/nfft).")
print("   A window-limited estimate DOUBLES when the cap doubles; a real one does not.\n")


def runs_of_hits(rs):
    eps, cur = [], []
    for r in rs:
        if r["env99"] >= AMP_MIN and (not cur or (r["seg"] == cur[-1]["seg"]
                                                  and r["i0"] == cur[-1]["i0"] + NFFT)):
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r] if r["env99"] >= AMP_MIN else []
    if cur:
        eps.append(cur)
    return eps


qtab, epout = [], []
for tag in NEW:
    rs = ALL[tag]
    eps = sorted(runs_of_hits(rs), key=lambda e: -len(e))
    print(f"   --- {tag}: {len(runs_of_hits(rs))} contiguous amplitude episodes; "
          f"the {min(6, len(eps))} longest:")
    cache = {}
    for k, e in enumerate(eps[:6]):
        s = e[0]["seg"]
        if s not in cache:
            cache[s] = C.load(s, ROOT / e[0]["cache"], e[0]["pfx"])
        d = cache[s]
        fs, i0 = e[0]["fs"], e[0]["i0"]
        n_avail = len(d["t"]) - i0
        print(f"     episode {k}: seg {s}, t {e[0]['t0']:.1f}-{e[-1]['t0'] + NFFT / fs:.1f} s, "
              f"{len(e) * NFFT / fs:.2f} s, pp max {2 * max(col(e, 'env99')):.0f}, "
              f"|v| {min(col(e, 'vmin')):.2f}-{max(col(e, 'vmax')):.2f}, "
              f"lat {np.mean(col(e, 'lat')):.2f}, eff {np.median(col(e, 'eff')):.0f}")
        epout.append(dict(tag=tag, k=k, seg=int(s), t0=float(e[0]["t0"]),
                          dur=float(len(e) * NFFT / fs), nwin=len(e),
                          pp=float(2 * max(col(e, "env99"))), lat=float(np.mean(col(e, "lat"))),
                          v=float(np.mean(col(e, "v"))), eff=float(np.median(col(e, "eff")))))
        for nf in (256, 512, 1024, 2048):
            if nf > n_avail:
                continue
            P = periodogram(np.asarray(d["tq"], float)[i0:i0 + nf], fs, nf)
            if P is None:
                continue
            f = np.fft.rfftfreq(nf, 1 / fs)
            f0, pr = peak_prom(f, P, *RATCH)
            Q = q_of(f, P, f0, *RATCH)
            cap = f0 / (1.44 * fs / nf) if np.isfinite(f0) else np.nan
            z = zcross(np.asarray(d["tq"], float)[i0:i0 + nf], fs, *RATCH)
            flag = ("AT THE CAP -- window-limited" if (np.isfinite(Q) and Q >= 0.85 * cap)
                    else "resolved (below the cap)")
            print(f"         NFFT {nf:>4d} ({nf / fs:5.2f} s)  f0 {f0:6.3f}  prom {pr:8.1f}  "
                  f"zc {z:5.2f}  Q {Q:6.1f}  cap {cap:6.1f}   {flag}")
            qtab.append(dict(tag=tag, ep=k, nfft=nf, f0=float(f0), prom=float(pr), Q=float(Q),
                             cap=float(cap), zc=float(z)))
    print()
OUT["episodes"] = epout
OUT["Q"] = qtab

# =============================================================== §7 which channel =================
hdr("§7  WHICH CHANNEL CARRIES THE LINE? bar torque vs angle-rate vs angle vs openpilot's command")
print("   Record (route 4f): bar YES, angle-rate YES, angle YES, command NO (prominence 2.7 vs a")
print("   > 10 criterion) ⇒ the loop closes inside the EPS + plant, not through openpilot.\n")
print(f"   {'route':10s} {'n hits':>7s} | " + " ".join(f"{n:>16s}" for n in
                                                       ("tq prom med", "rate_c prom med",
                                                        "ang prom med", "e4tq prom med")))
ch = {}
for tag in NEW + ["V69 r4f", "V70 r50"]:
    rs = ALL[tag]
    hits = [r for r in rs if r["env99"] >= AMP_MIN]
    if not hits:
        print(f"   {tag:10s} {0:>7d} |  (no amplitude hits)")
        continue
    cache, rows = {}, []
    for r in hits:
        key = (r["seg"], r["cache"])
        if key not in cache:
            cache[key] = C.load(r["seg"], ROOT / r["cache"], r["pfx"])
        d = cache[key]
        fs = r["fs"]
        w = slice(r["i0"], r["i0"] + NFFT)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        row = {}
        for nm, k in (("tq", "tq"), ("rate", "rate_c"), ("ang", "ang"), ("e4", "e4tq")):
            P = periodogram(np.asarray(d[k], float)[w], fs, NFFT)
            row[nm] = peak_prom(f, P, *RATCH)[1] if P is not None else np.nan
        rows.append(row)
    ch[tag] = {nm: float(np.nanmedian([x[nm] for x in rows]))
               for nm in ("tq", "rate", "ang", "e4")}
    print(f"   {tag:10s} {len(hits):>7d} | " +
          " ".join(f"{ch[tag][nm]:>16.2f}" for nm in ("tq", "rate", "ang", "e4")))
print("\n   criterion: prominence > 10 = the line is present in that channel.")
OUT["channels"] = ch

(ROOT / "_scratch/out/_r58_ratchet.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_r58_ratchet.json'}")
