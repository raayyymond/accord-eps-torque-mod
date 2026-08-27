#!/usr/bin/env python3
"""D4 -- the ratchet is STILL PRESENT on V72 by the corpus instrument. So WHERE is it, and could
the operator's "fixed" report and this measurement both be true?

studies/sessions/r59/d4_r59_ratchet.py established: engaged hands-off creep 12/19 = 63% at >=1200 counts p-p (quartet
83%, V71B 50%, V71C 42%), median 3,647 counts p-p, f0 7.82 Hz, manual 0/29. That is NOT a fix.
Before concluding the operator is simply wrong, this file tests the ways both could be true:

  A  EPISODE STRUCTURE. A hit RATE over 2.56 s windows says nothing about how long a bout lasts.
     "Large-scale ratcheting" is a sustained sensation; 20 isolated windows and 4 long bouts have
     the same rate.
  B  GEAR / MANOEUVRE. Route 59 segments 0 and 11 contain REVERSE frames. A ratchet confined to
     reverse parking is not what the operator means by the driving symptom.
  C  TIME AND PLACE. Which segments, which speeds -- and is it in the part of the drive he was
     attending to?
  D  DUTY. Ratchet-seconds per engaged-creep second, episode-bootstrapped -- the exposure-normalised
     quantity the binary hit rate hides.

Writes `_scratch/out/_d4_r59_where.json`.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
HANDS_OFF = 300.0
CREEP_R = 4.0
AMP_MIN = 600.0
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]
OUT = {}

ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), []),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14]),
}
NEW = "V72 r59"


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


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
        gear = np.asarray(d["cs_gear"], float) if "cs_gear" in d else np.full(len(t), np.nan)
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fb, pbv = peak_prom(f, P, *RATCH)
            g = gear[w]
            recs.append(dict(tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                             env99=float(np.percentile(env[w], 99)), fb=fb, pb=pbv,
                             v=float(v[w].mean()), eff=float(np.median(eff[w])),
                             lat=float(lat[w].mean()),
                             gear=float(np.median(g)) if np.isfinite(g).all() else np.nan,
                             rev=float(np.mean(g == 4.0)) if np.isfinite(g).all() else np.nan,
                             ang=float(np.mean(np.abs(d["ang"][w]))),
                             ep=(tag, int(s), i // (NFFT * 4))))
    return recs


ALL = {t: scan(c, p, s, sk, t) for t, (c, p, s, sk) in ROUTES.items()}

# ================================================================ A  episode structure ============
hdr("A.  EPISODE STRUCTURE -- contiguous runs of >=1200 counts p-p, ANY condition. A hit RATE\n"
    "    hides whether the symptom is a long bout or a scatter of isolated windows.")


def bouts(rs):
    """Contiguous runs of amplitude hits within one segment (windows are disjoint, hop = NFFT)."""
    out, cur = [], []
    for r in sorted(rs, key=lambda x: (x["seg"], x["i0"])):
        hit = r["env99"] >= AMP_MIN
        if hit and cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT:
            cur.append(r)
        else:
            if cur:
                out.append(cur)
            cur = [r] if hit else []
    if cur:
        out.append(cur)
    return out


print(f"   {'route':10s} {'route s':>8s} {'bouts':>6s} {'wins':>5s} {'bout s':>7s} "
      f"{'longest':>8s} {'med len':>8s} {'>=5.1 s':>8s} {'>=10.2 s':>9s} {'% route':>8s}")
bt = {}
for tag, rs in ALL.items():
    bs = bouts(rs)
    ln = np.array([len(b) * NFFT / 100 for b in bs]) if bs else np.array([])
    rt = len(rs) * NFFT / 100
    bt[tag] = dict(nbout=len(bs), nwin=int(sum(len(b) for b in bs)),
                   secs=float(ln.sum()) if len(ln) else 0.0,
                   longest=float(ln.max()) if len(ln) else 0.0,
                   med=float(np.median(ln)) if len(ln) else 0.0,
                   n5=int((ln >= 5.1).sum()), n10=int((ln >= 10.2).sum()),
                   pct=float(ln.sum() / rt) if rt else 0.0)
    x = bt[tag]
    print(f"   {tag:10s} {rt:>8.1f} {x['nbout']:>6d} {x['nwin']:>5d} {x['secs']:>7.1f} "
          f"{x['longest']:>8.2f} {x['med']:>8.2f} {x['n5']:>8d} {x['n10']:>9d} "
          f"{100 * x['pct']:>7.2f}%")
OUT["bouts"] = bt

# ================================================================ B  gear ==========================
hdr("B.  GEAR -- is V72's remaining ratchet a REVERSE / parking artefact? Route 59 segments 0 and\n"
    "    11 contain reverse frames; the operator's symptom is a forward-driving one.")
print(f"   {'route':10s} | " + " ".join(f"{n:>22s}" for n in ("hits in DRIVE", "hits in REVERSE",
                                                             "hits other/mixed")))
gr = {}
for tag, rs in ALL.items():
    h = [r for r in rs if r["env99"] >= AMP_MIN]
    if not h:
        continue
    nd = sum(1 for r in h if r["gear"] == 2.0)
    nr = sum(1 for r in h if r["gear"] == 4.0)
    no = len(h) - nd - nr
    gr[tag] = dict(n=len(h), drive=nd, rev=nr, other=no)
    print(f"   {tag:10s} | {f'{nd}/{len(h)} = {100 * nd / len(h):.0f}%':>22s} "
          f"{f'{nr}/{len(h)} = {100 * nr / len(h):.0f}%':>22s} "
          f"{f'{no}/{len(h)} = {100 * no / len(h):.0f}%':>22s}")
OUT["gear"] = gr

print("\n   ★ V72's engaged hands-off creep cell, split by gear -- the headline cell itself:")
s = [r for r in ALL[NEW] if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9]
for g in sorted({r["gear"] for r in s if np.isfinite(r["gear"])}):
    t = [r for r in s if r["gear"] == g]
    hh = sum(1 for r in t if r["env99"] >= AMP_MIN)
    print(f"     gear {GEAR[int(g)]:8s} n={len(t):3d}  hits {hh:3d} = {100 * hh / len(t):5.1f}%  "
          f"median p-p {2 * np.median([r['env99'] for r in t]):7.0f}")

# ================================================================ C  time and place ================
hdr("C.  WHERE ON THE DRIVE. Every V72 amplitude hit, in order, with its covariates.")
print(f"   {'seg':>4s} {'t0':>7s} {'p-p':>7s} {'f0':>6s} {'prom':>8s} {'v m/s':>6s} {'eff':>7s} "
       f"{'lat':>5s} {'gear':>9s} {'|ang|':>7s}")
hits = [r for r in ALL[NEW] if r["env99"] >= AMP_MIN]
for r in sorted(hits, key=lambda x: (x["seg"], x["t0"])):
    g = GEAR[int(r["gear"])] if np.isfinite(r["gear"]) else "?"
    print(f"   {r['seg']:>4d} {r['t0']:>7.1f} {2 * r['env99']:>7.0f} {r['fb']:>6.2f} "
          f"{r['pb']:>8.1f} {r['v']:>6.2f} {r['eff']:>7.0f} {r['lat']:>5.2f} {g:>9s} "
          f"{r['ang']:>7.1f}")
OUT["v72_hits"] = [dict(seg=r["seg"], t0=r["t0"], pp=2 * r["env99"], f0=r["fb"], v=r["v"],
                        eff=r["eff"], lat=r["lat"], gear=r["gear"], ang=r["ang"]) for r in hits]

# ================================================================ D  duty ==========================
hdr("D.  DUTY -- ratchet-seconds per engaged-creep second, exposure-normalised, episode-bootstrap.")


def eps_of(rs):
    e = {}
    for r in rs:
        e.setdefault(r["ep"], []).append(r)
    return list(e.values())


def duty_ci(rs, nb=4000, rng=None):
    rng = rng or np.random.default_rng(20260805)
    ee = eps_of(rs)
    if len(ee) < 2:
        return np.nan, np.nan, np.nan
    pt = np.mean([r["env99"] >= AMP_MIN for r in rs])
    dr = np.empty(nb)
    for i in range(nb):
        s = [r for k in rng.integers(0, len(ee), len(ee)) for r in ee[k]]
        dr[i] = np.mean([r["env99"] >= AMP_MIN for r in s])
    return float(pt), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


print(f"   {'route':10s} | " + " ".join(f"{n:>34s}" for n in
                                        ("engaged hands-off creep", "engaged creep any grip",
                                         "engaged all speeds")))
dt = {}
for tag, rs in ALL.items():
    cells = [
        [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9],
        [r for r in rs if r["v"] < CREEP_R and r["lat"] > 0.9],
        [r for r in rs if r["lat"] > 0.9],
    ]
    vals = [duty_ci(c) for c in cells]
    dt[tag] = [list(v) for v in vals]
    print(f"   {tag:10s} | " + " ".join(
        f"{100 * v[0]:>10.1f}% [{100 * v[1]:>6.1f},{100 * v[2]:>6.1f}] n={len(c):<4d}"
        for v, c in zip(vals, cells)))
OUT["duty"] = dt

(ROOT / "_scratch/out/_d4_r59_where.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_where.json'}")
