#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §9 THE RELAY PREDICTIONS, D1's CANDIDATE LINE, AND D1's MOVEMENT FRAME.

Three things, all handed to me by teammates, all directly load-bearing on my question.

 §1 D1's CANDIDATE LINE. D1 finds a second engagement-conditional line on the arms with real
    exposure -- 14.45 Hz (V62+V65, K=354) and 14.84 Hz (V71B, K=160, == EXACTLY 2 x that route's
    own 7.42 Hz ratchet centre), at 68-78 counts p-p. 🛑 That is BELOW my prominence-2.0 cut with
    the default 6 Hz floor, because the ratchet raises the floor from 2 to 14 Hz. Re-swept here
    with D1's NARROW floor (halfwin 2.5, exclude 0.8) so a weak neighbour cannot be masked.

 §2 D1's MOVEMENT FRAME -- THE INDEPENDENT CONDITIONAL. D1 reports grind #1 is BAND-PASS in wheel
    MOVEMENT: peak at 25-75 deg p-p excursion per window, collapsing 15-30x below 8 deg and above
    200 deg, and 2-4x stronger within 15 deg of the sensor zero at matched movement. If the 7.8 Hz
    line does NOT share that band-pass, the two modes have different loop closures -- independent
    of everything in §1-§8. `span` = p-p excursion of `ang` in the window; `mid` = its midpoint,
    re-centred on -4.40 deg.

 §3 THE LEAD'S RELAY PREDICTIONS. `FUN_00036388` latches after 20 ms of |gp-0x6b64| inside +/-1024
    and emits +/-1024 x sgn(motor rate) -- a FIXED, signal-independent injection.
      P1  a relay limit cycle has a CHARACTERISTIC amplitude ⇒ in-burst amplitude should be
          NARROWLY distributed and BUILD-INDEPENDENT, not dose-tracking. Tested as the coefficient
          of variation of in-burst amplitude within build, and the spread of medians across builds.
      P3  if grind #1 and the micro-ratchet are the same relay latching and unlatching, there
          should be TWO amplitude modes AT THE SAME CENTRE FREQUENCY, with transitions.
          🛑 Tested with the f0 of each mode reported separately -- "bimodal" is worth nothing if
          the two modes sit at different frequencies, which is the whole question.
      ⊕ A dwell of 20 ms sets a relay half-period of ~20 ms ⇒ ~25 Hz. 7.8 Hz needs a 64 ms
          half-period, 3.2x the dwell. Stated as arithmetic, tested as data.

Episode-clustered CIs throughout. Writes `_scratch/out/_r59_relay.json`.
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
from _r31_common import band_envelope, periodogram  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
import _r37_ratchet_lib as R37  # noqa: E402

NFFT = 256
RATCH, GRIND = (6.0, 9.0), (18.0, 22.0)
ANG0 = -4.40
RNG = np.random.default_rng(20260805)
OUT = {}
ROUTES = {"V59 r2c": ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
          "V62 r37": ("_scratch/cache/r37", "r37s", list(range(15)), []),
          "V67 r47": ("_scratch/cache/r47", "r47s", list(range(26)), []),
          "V69 r4f": ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
          "V70 r50": ("_scratch/cache/r50", "r50s", [0, 1, 2], [0]),
          "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
          "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
          "V72 r59": ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14])}


def hdr(s):
    print("\n" + "=" * 120 + f"\n{s}\n" + "=" * 120)


def scan(tag, vhi=4.0, eng=True):
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
        er, eg = band_envelope(tq, fs, *RATCH), band_envelope(tq, fs, *GRIND)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.asarray(d["ang"], float)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            vm = float(v[w].mean())
            lm = float(lat[w].mean())
            if not (0.3 <= vm < vhi):
                continue
            if eng is True and lm <= 0.9:
                continue
            if eng is False and lm >= 0.1:
                continue
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            a = ang[w]
            recs.append(dict(tag=tag, seg=int(s), i0=i, fs=fs, P=P, f=f, v=vm, lat=lm,
                             span=float(a.max() - a.min()),
                             mid=float((a.max() + a.min()) / 2 - ANG0),
                             ppr=float(2 * np.percentile(er[w], 99)),
                             ppg=float(2 * np.percentile(eg[w], 99)),
                             fr=R37.locate(f, P, 5, 12)[0], fg=R37.locate(f, P, 17, 26)[0]))
    return recs


ENG = {t: scan(t) for t in ROUTES}
MAN = {t: scan(t, eng=False) for t in ROUTES}


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


# ================================================================= §1 D1's candidate line =========
hdr("§1  ★ D1's CANDIDATE -- presence-test ~14.5-15.0 Hz on route 59 with D1's NARROW FLOOR")
print("   Narrow floor: halfwin 2.5 Hz, exclude 0.8 Hz. With the default 6 Hz floor the 7.8 Hz")
print("   ratchet is 20-30x its own floor and lifts the floor across 2-14 Hz, which would mask a")
print("   ~75 counts p-p neighbour. Averaged periodogram FIRST, peak-find after.\n")


def narrow_inventory(rs, lo=2.0, hi=18.0, minprom=1.3):
    if not rs:
        return []
    P = np.mean(np.array([r["P"] for r in rs]), axis=0)
    f = rs[0]["f"]
    R = R37.prom_spectrum(f, P, halfwin=2.5, exclude=0.8)
    rows = []
    for j in range(1, len(f) - 1):
        if not (lo <= f[j] <= hi) or not np.isfinite(R[j]):
            continue
        if R[j] < minprom or R[j] < R[j - 1] or R[j] < R[j + 1]:
            continue
        rows.append(dict(f0=float(f[j]), prom=float(R[j]), P=float(P[j])))
    rows.sort(key=lambda r: -r["prom"])
    return rows


def band_pp(rs, f0, half=0.8):
    """Median p-p of the analytic envelope in [f0-half, f0+half], counts."""
    vals = []
    cache = {}
    for r in rs:
        key = (r["tag"], r["seg"])
        if key not in cache:
            c, p, _, _ = ROUTES[r["tag"]]
            d = C.load(r["seg"], ROOT / c, p)
            cache[key] = (np.asarray(d["tq"], float), R4F.fs_lattice(d))
        tq, fs = cache[key]
        e = band_envelope(tq, fs, max(f0 - half, 0.5), f0 + half)
        vals.append(2 * float(np.percentile(e[r["i0"]:r["i0"] + NFFT], 99)))
    return float(np.median(vals)) if vals else np.nan


r59e = ENG["V72 r59"]
rows = narrow_inventory(r59e)
print(f"   route 59 engaged creep, K={len(r59e)} windows, narrow floor, 2-18 Hz:")
print(f"   {'f0 Hz':>7s} {'narrow prom':>12s} {'p-p counts':>11s} | note")
inv = []
for r in rows[:12]:
    pp = band_pp(r59e, r["f0"])
    r["pp"] = pp
    inv.append(r)
    note = ""
    if 6.0 <= r["f0"] <= 9.0:
        note = "the ratchet"
    if 13.5 <= r["f0"] <= 16.0:
        note = "<<< D1's CANDIDATE BAND"
    print(f"   {r['f0']:>7.2f} {r['prom']:>12.2f} {pp:>11.0f} | {note}")
OUT["narrow_inventory_r59"] = inv
cand = [r for r in rows if 13.5 <= r["f0"] <= 16.0]
print(f"\n   ⇒ lines in 13.5-16.0 Hz clearing narrow prominence 1.3: "
      f"{len(cand)}  {'-- ' + ', '.join(f'{c[chr(102) + chr(48)]:.2f} Hz (prom {c[chr(112) + chr(114) + chr(111) + chr(109)]:.2f}, {c[chr(112) + chr(112)]:.0f} p-p)' for c in cand) if cand else '(NONE)'}")
# the 2nd-harmonic test proper: is there power at exactly 2 x this route's ratchet centre?
f_r = float(np.nanmedian([r["fr"] for r in r59e]))
P = np.mean(np.array([r["P"] for r in r59e]), axis=0)
f = r59e[0]["f"]
Rn = R37.prom_spectrum(f, P, halfwin=2.5, exclude=0.8)
j2 = int(np.argmin(np.abs(f - 2 * f_r)))
print(f"   route 59 ratchet centre {f_r:.2f} Hz ⇒ 2nd harmonic expected at {2 * f_r:.2f} Hz; "
      f"nearest bin {f[j2]:.2f} Hz has narrow prominence {Rn[j2]:.2f}, "
      f"{band_pp(r59e, float(f[j2])):.0f} counts p-p")
OUT["second_harmonic"] = dict(f_ratchet=f_r, f2=float(f[j2]), prom=float(Rn[j2]))

# ================================================================= §2 D1's movement frame =========
hdr("§2  ★★ D1's MOVEMENT FRAME -- does the 7.8 Hz line share grind #1's band-pass in MOVEMENT?")
print("   D1: grind #1 peaks at a 25-75 deg p-p excursion per window and collapses 15-30x below")
print("   8 deg and above 200 deg. If the ratchet does NOT share that, the loop closures differ.")
print("   Pooled across ALL routes for power; per-route counts in the census column.\n")
POOL = [r for t in ROUTES for r in ENG[t]]
SPANS = [(0, 8), (8, 25), (25, 75), (75, 200), (200, 1e9)]
print(f"   {'span (deg p-p)':16s} {'n':>5s} {'eps':>4s} | {'6-9 p-p med':>12s} {'rel':>6s} | "
      f"{'18-22 p-p med':>14s} {'rel':>6s}")
mv = {}
base_r = base_g = None
for lo_s, hi_s in SPANS:
    sub = [r for r in POOL if lo_s <= r["span"] < hi_s]
    if len(sub) < 5:
        print(f"   {f'{lo_s}-{hi_s}':16s} {len(sub):>5d}   too few")
        continue
    mr = float(np.median([r["ppr"] for r in sub]))
    mg = float(np.median([r["ppg"] for r in sub]))
    if base_r is None or (25 <= lo_s < 75):
        pass
    mv[f"{lo_s}-{hi_s}"] = dict(n=len(sub), neps=len(episodes(sub)), r=mr, g=mg)
peak_r = max(v["r"] for v in mv.values())
peak_g = max(v["g"] for v in mv.values())
for k, v in mv.items():
    print(f"   {k:16s} {v['n']:>5d} {v['neps']:>4d} | {v['r']:>12.0f} {v['r'] / peak_r:>6.2f} | "
          f"{v['g']:>14.0f} {v['g'] / peak_g:>6.2f}")
OUT["movement_bandpass"] = mv
print("\n   collapse ratio (peak cell / lowest cell), each band -- D1 reports 15-30x for grind #1:")
print(f"     6-9 Hz   {peak_r / min(v['r'] for v in mv.values()):.1f}x")
print(f"     18-22 Hz {peak_g / min(v['g'] for v in mv.values()):.1f}x")

print("\n   --- AND THE NEAR-ZERO PREFERENCE AT MATCHED MOVEMENT (span 25-75 deg only)")
sub = [r for r in POOL if 25 <= r["span"] < 75]
print(f"   {'|mid - zero|':16s} {'n':>5s} | {'6-9 p-p med':>12s} | {'18-22 p-p med':>14s}")
nz = {}
for lo_m, hi_m in ((0, 15), (15, 60), (60, 1e9)):
    s2 = [r for r in sub if lo_m <= abs(r["mid"]) < hi_m]
    if len(s2) < 4:
        print(f"   {f'{lo_m}-{hi_m}':16s} {len(s2):>5d}   too few")
        continue
    nz[f"{lo_m}-{hi_m}"] = dict(n=len(s2), r=float(np.median([r["ppr"] for r in s2])),
                                g=float(np.median([r["ppg"] for r in s2])))
    print(f"   {f'{lo_m}-{hi_m}':16s} {len(s2):>5d} | {nz[f'{lo_m}-{hi_m}']['r']:>12.0f} | "
          f"{nz[f'{lo_m}-{hi_m}']['g']:>14.0f}")
OUT["near_zero_matched"] = nz

# ================================================================= §3 relay predictions ===========
hdr("§3  ★★★ THE RELAY PREDICTIONS -- P1 characteristic amplitude, P3 bimodality AT A SHARED f0")
print("   P1: a relay limit cycle injects a FIXED +/-1024 ⇒ in-burst amplitude should be NARROW")
print("   within a build and the SAME across builds, regardless of rate-lane dose.\n")
print(f"   {'route':10s} {'n burst':>8s} | {'18-22 in-burst p-p':>19s} {'CV':>6s} | "
      f"{'6-9 in-burst p-p':>17s} {'CV':>6s}")
p1 = {}
for t in ROUTES:
    bg = [r["ppg"] for r in ENG[t] if r["ppg"] >= 1200]
    br = [r["ppr"] for r in ENG[t] if r["ppr"] >= 1200]
    if len(bg) < 3:
        print(f"   {t:10s} {len(bg):>8d} |  too few bursts")
        continue
    cvg = float(np.std(bg, ddof=1) / np.mean(bg))
    cvr = float(np.std(br, ddof=1) / np.mean(br)) if len(br) > 2 else np.nan
    p1[t] = dict(n=len(bg), g=float(np.median(bg)), cvg=cvg,
                 r=float(np.median(br)) if br else np.nan, cvr=cvr)
    print(f"   {t:10s} {len(bg):>8d} | {np.median(bg):>19.0f} {cvg:>6.2f} | "
          f"{np.median(br) if br else np.nan:>17.0f} {cvr:>6.2f}")
meds = [v["g"] for v in p1.values()]
print(f"\n   across-build spread of the 18-22 in-burst median: "
      f"{min(meds):.0f} - {max(meds):.0f} counts, ratio {max(meds) / min(meds):.2f}x; "
      f"within-build CV {min(v['cvg'] for v in p1.values()):.2f}-"
      f"{max(v['cvg'] for v in p1.values()):.2f}")
OUT["P1_characteristic_amplitude"] = p1

print("\n   P3: TWO AMPLITUDE MODES AT THE SAME CENTRE FREQUENCY? Pooled engaged creep, all routes.")
print("   🛑 The f0 of each mode is reported SEPARATELY. Bimodality at two DIFFERENT frequencies")
print("      is two phenomena, not one relay latching and unlatching.\n")


def mixfit(y):
    n = len(y)
    ll1 = -0.5 * n * (np.log(2 * np.pi * y.var()) + 1)
    bic1 = -2 * ll1 + 2 * np.log(n)
    mu = np.array([np.percentile(y, 25), np.percentile(y, 75)])
    sd = np.array([y.std() / 2, y.std() / 2])
    w = np.array([0.5, 0.5])
    for _ in range(500):
        p = np.array([w[k] * np.exp(-0.5 * ((y - mu[k]) / sd[k]) ** 2)
                      / (sd[k] * np.sqrt(2 * np.pi)) for k in range(2)])
        s = np.maximum(p.sum(0), 1e-300)
        g = p / s
        w = g.mean(1)
        mu = (g * y).sum(1) / g.sum(1)
        sd = np.sqrt(np.maximum((g * (y - mu[:, None]) ** 2).sum(1) / g.sum(1), 1e-6))
    p = np.array([w[k] * np.exp(-0.5 * ((y - mu[k]) / sd[k]) ** 2)
                  / (sd[k] * np.sqrt(2 * np.pi)) for k in range(2)])
    ll2 = float(np.log(np.maximum(p.sum(0), 1e-300)).sum())
    bic2 = -2 * ll2 + 5 * np.log(n)
    return bic1, bic2, np.exp(mu), w, (p / np.maximum(p.sum(0), 1e-300))[1]


p3 = {}
for lbl, ak, fk in (("18-22 Hz (grind #1)", "ppg", "fg"), ("6-9 Hz (the ratchet)", "ppr", "fr")):
    y = np.array([r[ak] for r in POOL if r[ak] > 0], float)
    f0 = np.array([r[fk] for r in POOL if r[ak] > 0], float)
    ok = np.isfinite(f0)
    y, f0 = np.log(y[ok]), f0[ok]
    b1, b2, m2, w2, resp = mixfit(y)
    hi = resp > 0.5
    f_lo = float(np.median(f0[~hi]))
    f_hi = float(np.median(f0[hi]))
    dr = np.empty(3000)
    for b in range(3000):
        k = RNG.integers(0, len(f0), len(f0))
        dr[b] = np.median(f0[k][hi[k]]) - np.median(f0[k][~hi[k]]) if hi[k].any() and (~hi[k]).any() else np.nan
    p3[lbl] = dict(bic1=b1, bic2=b2, m=list(m2), w=list(w2), f_lo=f_lo, f_hi=f_hi,
                   df=f_hi - f_lo, dlo=float(np.nanpercentile(dr, 2.5)),
                   dhi=float(np.nanpercentile(dr, 97.5)), n=int(len(y)))
    x = p3[lbl]
    print(f"   {lbl}  n={len(y)}")
    print(f"     dBIC (1 vs 2 components) = {b1 - b2:+.1f} ⇒ "
          f"{'TWO modes' if b2 < b1 - 2 else 'ONE mode'}")
    print(f"     mode amplitudes {m2[0]:.0f} and {m2[1]:.0f} counts p-p, weights "
          f"{w2[0]:.2f}/{w2[1]:.2f}, separation {m2[1] / m2[0]:.2f}x")
    print(f"     ★ CENTRE FREQUENCY OF EACH MODE: low mode {f_lo:.3f} Hz, high mode {f_hi:.3f} Hz, "
          f"difference {f_hi - f_lo:+.3f} [{x['dlo']:+.3f}, {x['dhi']:+.3f}] Hz")
    print(f"       ⇒ {'SHARED centre frequency (relay-compatible)' if x['dlo'] <= 0 <= x['dhi'] else 'the two modes sit at DIFFERENT frequencies'}\n")
OUT["P3_bimodality"] = p3

print(f"   ⊕ ARITHMETIC: a 20 ms dwell sets a relay half-period ~20 ms ⇒ ~25 Hz. Grind #1 at "
      f"{np.nanmedian([r['fg'] for r in POOL]):.1f} Hz has a half-period of "
      f"{500 / np.nanmedian([r['fg'] for r in POOL]):.1f} ms (fits). The ratchet at "
      f"{np.nanmedian([r['fr'] for r in POOL]):.1f} Hz needs "
      f"{500 / np.nanmedian([r['fr'] for r in POOL]):.1f} ms, "
      f"{(500 / np.nanmedian([r['fr'] for r in POOL])) / 20:.1f}x the dwell.")

json.dump(OUT, open(ROOT / "_scratch/out/_r59_relay.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_scratch/out/_r59_relay.json'}")
