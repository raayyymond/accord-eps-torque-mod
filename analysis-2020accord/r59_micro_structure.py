#!/usr/bin/env python3
"""ROUTE 59 (V72) -- §3 WHAT THE 6-9 Hz AND 18-22 Hz EVENTS ACTUALLY LOOK LIKE.

§2 found route 59's 6-9 Hz band UNATTENUATED in the engaged hands-off creep cell (median 3,647
counts p-p, 63% hit rate at the record's own >=1200 criterion). That sits badly with the operator's
"the ratchet is FIXED". Before any equivalence test, this file asks what CHANGED in shape:

  * the amplitude DISTRIBUTION (is the route-59 population the low tail of the historical one, or
    the same distribution?),
  * the EPISODE DURATION at high amplitude (a "heavy, audible" ratchet is a SUSTAINED event; a
    "felt-only micro" one may be the same line in short bursts),
  * the exceedance ladder (>=1200, 2400, 4000, 6000, 8000 counts p-p).

Every count is over DISJOINT windows and every CI resamples EPISODES.
Writes `_r59_structure.json`.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RATCH, GRIND = (6.0, 9.0), (18.0, 22.0)
HANDS_OFF, CREEP = 300.0, 4.0
OUT = {}
ROUTES = {
    "V59 r2c":  ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_cache_r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_cache_r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_cache_r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_cache_r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_cache_r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_cache_r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_cache_r59", "r59s", list(range(15)), [12, 13, 14]),
}


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


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
        er, eg = band_envelope(tq, fs, *RATCH), band_envelope(tq, fs, *GRIND)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            recs.append(dict(tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                             ppr=float(2 * np.percentile(er[w], 99)),
                             ppg=float(2 * np.percentile(eg[w], 99)),
                             fr=peak_prom(f, P, *RATCH)[0], pr=peak_prom(f, P, *RATCH)[1],
                             fg=peak_prom(f, P, *GRIND)[0], pg=peak_prom(f, P, *GRIND)[1],
                             v=float(v[w].mean()), lat=float(lat[w].mean()),
                             eff=float(np.median(eff[w]))))
    return recs


ALL = {t: scan(t) for t in ROUTES}


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


# ================================================================= §1 exceedance ladder ===========
hdr("§1  ★★ THE EXCEEDANCE LADDER -- 6-9 Hz p-p, engaged hands-off creep. Where does route 59 stop?")
print("   A 'heavy, audible' ratchet and a 'felt-only micro' one should differ at the TOP of the")
print("   distribution, not at its median. Cell seconds in brackets.\n")
LAD = [1200, 2400, 4000, 6000, 8000]
print(f"   {'route':10s} {'n(s)':>10s} | " + " ".join(f"{'>=' + str(x):>11s}" for x in LAD) +
      f" | {'p50':>6s} {'p90':>6s} {'max':>6s}")
lad = {}
for tag in ROUTES:
    rs = cell(ALL[tag])
    if not rs:
        continue
    pp = np.array([r["ppr"] for r in rs])
    row = {f"ge{x}": int((pp >= x).sum()) for x in LAD}
    row.update(n=len(rs), p50=float(np.median(pp)), p90=float(np.percentile(pp, 90)),
               max=float(pp.max()))
    lad[tag] = row
    cells_s = " ".join(f"{f'{(pp >= x).sum()} ({100 * (pp >= x).mean():.0f}%)':>11s}" for x in LAD)
    print(f"   {tag:10s} {f'{len(rs)} ({len(rs) * 2.56:.0f}s)':>10s} | {cells_s} | "
          f"{np.median(pp):>6.0f} {np.percentile(pp, 90):>6.0f} {pp.max():>6.0f}")
OUT["ladder_6_9"] = lad

hdr("§1b  THE SAME LADDER FOR 18-22 Hz (grind #1) -- the operator says grind #1 is STILL PRESENT")
print(f"   {'route':10s} {'n(s)':>10s} | " + " ".join(f"{'>=' + str(x):>11s}" for x in LAD) +
      f" | {'p50':>6s} {'p90':>6s} {'max':>6s}")
ladg = {}
for tag in ROUTES:
    rs = cell(ALL[tag])
    if not rs:
        continue
    pp = np.array([r["ppg"] for r in rs])
    ladg[tag] = {f"ge{x}": int((pp >= x).sum()) for x in LAD}
    ladg[tag].update(n=len(rs), p50=float(np.median(pp)), max=float(pp.max()))
    cells_s = " ".join(f"{f'{(pp >= x).sum()} ({100 * (pp >= x).mean():.0f}%)':>11s}" for x in LAD)
    print(f"   {tag:10s} {f'{len(rs)} ({len(rs) * 2.56:.0f}s)':>10s} | {cells_s} | "
          f"{np.median(pp):>6.0f} {np.percentile(pp, 90):>6.0f} {pp.max():>6.0f}")
OUT["ladder_18_22"] = ladg

# ================================================================= §2 sustained episodes ==========
hdr("§2  ★★ SUSTAINED EVENTS -- contiguous runs of windows above 1200 / 2400 / 4000 counts p-p")
print("   Runs are contiguous DISJOINT windows in one segment, ANY hands/engagement state, creep")
print("   only. Duration is the physical thing an operator calls 'heavy' or 'a burst'.\n")


def runs_above(rs, thr, key="ppr"):
    rs = sorted([r for r in rs if r["v"] < CREEP], key=lambda r: (r["seg"], r["i0"]))
    eps, cur = [], []
    for r in rs:
        hit = r[key] >= thr
        cont = cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT
        if hit and (cont or not cur):
            cur.append(r)
        elif hit:
            eps.append(cur)
            cur = [r]
        else:
            if cur:
                eps.append(cur)
            cur = []
    if cur:
        eps.append(cur)
    return eps


print(f"   {'route':10s} | " + " ".join(f"{'>=' + str(x) + ' Hz-run':>26s}" for x in (1200, 4000)))
print(f"   {'':10s} | " + " ".join(f"{'n / longest s / total s':>26s}" for _ in (1, 2)))
sus = {}
for tag in ROUTES:
    row = []
    d = {}
    for thr in (1200, 4000):
        eps = runs_above(ALL[tag], thr)
        longest = max((len(e) for e in eps), default=0) * NFFT / 100
        tot = sum(len(e) for e in eps) * NFFT / 100
        d[thr] = dict(n=len(eps), longest=longest, total=tot)
        row.append(f"{f'{len(eps)} / {longest:.1f} / {tot:.1f}':>26s}")
    sus[tag] = d
    print(f"   {tag:10s} | " + " ".join(row))
OUT["sustained"] = sus

# ================================================================= §3 route-59 event log ==========
hdr("§3  ROUTE 59 -- every creep window with 6-9 Hz >= 1200 counts p-p, in time order")
print(f"   {'seg':>3s} {'t0 s':>7s} {'6-9 pp':>7s} {'f 6-9':>6s} {'18-22 pp':>9s} {'f18-22':>7s} "
      f"{'v':>5s} {'lat':>4s} {'eff':>6s}")
evs = []
for r in sorted([x for x in ALL["V72 r59"] if x["v"] < CREEP and x["ppr"] >= 1200],
                key=lambda r: (r["seg"], r["i0"])):
    evs.append({k: r[k] for k in ("seg", "t0", "ppr", "fr", "ppg", "fg", "v", "lat", "eff")})
    print(f"   {r['seg']:>3d} {r['t0']:>7.1f} {r['ppr']:>7.0f} {r['fr']:>6.2f} {r['ppg']:>9.0f} "
          f"{r['fg']:>7.2f} {r['v']:>5.2f} {r['lat']:>4.1f} {r['eff']:>6.0f}")
OUT["r59_events"] = evs
print(f"\n   TOTAL {len(evs)} windows = {len(evs) * 2.56:.1f} s of route 59's "
      f"{len([x for x in ALL['V72 r59'] if x['v'] < CREEP]) * 2.56:.1f} s of creep")

json.dump(OUT, open(ROOT / "_r59_structure.json", "w"), indent=1, default=float)
print(f"\nwrote {ROOT / '_r59_structure.json'}")
