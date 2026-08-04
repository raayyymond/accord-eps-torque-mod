#!/usr/bin/env python3
"""ROUTE 50 / V70 -- THE RATCHET, on the first route where it was DELIBERATELY PROVOKED.

The operator demonstrated the ratcheting with manoeuvres at the START of this drive. Every prior
characterisation (route 4f: 46 windows / 118 s at >= 1200 counts p-p, median 7.79 Hz, speed-
invariant slope +0.0358 Hz per m/s, 44/46 engaged) came from incidental episodes inside ordinary
driving. Provoked episodes are the first chance at (a) a clean f0 and (b) a Q that is not capped by
the analysis window.

INSTRUMENT is `r4f_ratchet_inventory.py`'s, unchanged in every numeric respect, so the counts and
frequencies here are comparable to the record:
  * DISJOINT 2.56 s windows (NFFT 256, 0.39 Hz bins) -- window counts are sample counts.
  * The locator is the PROMINENCE argmax over a FREE 5-12 Hz range (peak / local +/-6 Hz median
    floor excluding +/-1.5 Hz), never the raw-power argmax, which lands on the driver's 1-3 Hz push.
  * Every prominence beside a PHYSICAL amplitude (6-9 Hz analytic envelope p99, counts; p-p = 2x).
  * THE NULL FIRST, from two control bands, and the LARGER (conservative) floor is used.
  * EPISODES, never windows, are the unit of inference.
  * ENGAGEMENT is LATERAL (`carControl.latActive`). HANDS-OFF is sustained |lowpass(tq,3Hz)| < 300.
🛑 ONE DELIBERATE CHANGE: the sample rate is `_r4f_lib.fs_lattice`, the kit's standing estimator,
   not `(n-1)/(t[-1]-t[0])`. Both are printed; they agree to <0.05% on this route.

★ THE Q QUESTION. The record says Q is NOT measurable at NFFT 256 -- the Hann main lobe caps it at
f0/(1.44*fs/nfft) ~= 13.3 at 7.8 Hz. ss6 re-cuts the longest provoked episodes at NFFT 512/1024 and
states what Q can and cannot be resolved, with the cap printed beside every number.

Writes `_r50_ratchet.json`.  Usage: python r50_ratchet.py
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

from _r31_common import band_envelope, peak_prom, periodogram, q_of, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)          # presence band
FREE = (5.0, 12.0)          # free locator range
CTRL_A = (10.5, 13.5)       # control band 1 -- clear of 2*f0
CTRL_B = (24.0, 27.0)       # control band 2 -- between grind #1 and grind #2
GRIND1 = (18.0, 22.0)
HANDS_OFF = 300.0
AMP_MIN = 600.0             # 6-9 Hz envelope p99 counts; p-p = 1200, the record's criterion
CIRC = (2.073, 2.088)
OUT = {}

ROUTES = {"V70 r50": (ROOT / "_cache_r50", "r50s", [0, 1, 2]),
          "V69 r4f": (ROOT / "_cache_r4f", "r4fs", list(range(8))),
          "V62 r37": (ROOT / "_cache_r37", "r37s", list(range(15)))}


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def load(cache, pfx, seg):
    return {k: v for k, v in np.load(cache / f"{pfx}{seg}.npz").items()}


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


def scan(cache, pfx, segs, tag):
    recs = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = load(cache, pfx, s)
        fs = R4F.fs_lattice(d)
        t, tq = np.asarray(d["t"], float), np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = band_envelope(tq, fs, *RATCH)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        rp = cache / f"{pfx}{s}_rpm.npz"
        rpm = np.load(rp)["rpm"] if rp.exists() else None
        for i in range(0, len(t) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            fr, pr = peak_prom(f, P, *FREE)
            fb, pb = peak_prom(f, P, *RATCH)
            _, pca = peak_prom(f, P, *CTRL_A)
            _, pcb = peak_prom(f, P, *CTRL_B)
            fg, pg = peak_prom(f, P, *GRIND1)
            recs.append(dict(tag=tag, seg=int(s), i0=i, t0=float(t[i]), fs=fs,
                             fr=fr, pr=pr, fb=fb, pb=pb, pca=pca, pcb=pcb, fg=fg, pg=pg,
                             env99=float(np.percentile(env[w], 99)),
                             Q=q_of(f, P, fb, *RATCH) if np.isfinite(fb) else np.nan,
                             zc=zcross(tq[w], fs, *RATCH),
                             v=float(v[w].mean()), vmin=float(v[w].min()), vmax=float(v[w].max()),
                             ang=float(np.mean(np.abs(d["ang"][w]))),
                             rate90=float(np.percentile(np.abs(d["rate_c"][w]), 90)),
                             eff=float(np.median(eff[w])), effmax=float(eff[w].max()),
                             lat=float(lat[w].mean()),
                             sstat=sorted({int(x) for x in d["sstat"][w]}),
                             rpm=(float(np.median(rpm[w])) if rpm is not None else np.nan),
                             e4=float(np.percentile(np.abs(d["e4tq"][w]), 99))))
    return recs


ALL = {tag: scan(c, p, s, tag) for tag, (c, p, s) in ROUTES.items()}
R50 = ALL["V70 r50"]

# =============================================================== ss1 sample rate + null ===========
hdr("ss1  SAMPLE RATE, then THE NULL -- both computed before any detection is quoted")
for tag, (c, p, segs) in ROUTES.items():
    for s in segs[:3]:
        q = c / f"{p}{s}.npz"
        if not q.exists():
            continue
        d = load(c, p, s)
        t = np.asarray(d["t"], float)
        print(f"   {tag} seg {s}:  fs_lattice {R4F.fs_lattice(d):8.4f}   "
              f"(n-1)/span {(len(t) - 1) / (t[-1] - t[0]):8.4f}   1/median(dt) "
              f"{1 / np.median(np.diff(t)):8.4f}")
    if tag != "V70 r50":
        break

pca, pcb = col(R50, "pca"), col(R50, "pcb")
a, b = pca[np.isfinite(pca)], pcb[np.isfinite(pcb)]
fa, fb_ = float(np.percentile(a, 95)), float(np.percentile(b, 95))
FLOOR, LOOSE = max(fa, fb_), fb_
print(f"\n   NULL-A {CTRL_A[0]}-{CTRL_A[1]} Hz  n={len(a)}  median {np.median(a):6.2f}  "
      f"p95 {fa:7.2f}  max {a.max():8.2f}")
print(f"   NULL-B {CTRL_B[0]}-{CTRL_B[1]} Hz  n={len(b)}  median {np.median(b):6.2f}  "
      f"p95 {fb_:7.2f}  max {b.max():8.2f}")
print(f"   ⇒ CONSERVATIVE detection floor = {FLOOR:.2f}   permissive = {LOOSE:.2f}")
OUT["null"] = dict(floorA=fa, floorB=fb_, floor=FLOOR)

# =============================================================== ss2 route-wide scan ==============
hdr("ss2  ROUTE-WIDE 6-9 Hz SCAN -- disjoint 2.56 s windows, all 3 segments")
pb = col(R50, "pb")
det = pb >= FLOOR
lat = col(R50, "lat") > 0.5
v = col(R50, "v")
print(f"   windows {len(R50)}   detections {int(det.sum())} ({100 * det.mean():.1f}%) at the "
      f"conservative floor {FLOOR:.1f}; {int((pb >= LOOSE).sum())} at the permissive {LOOSE:.1f}")
print(f"   engaged {int((det & lat).sum())}/{int(lat.sum())}   "
      f"manual {int((det & ~lat).sum())}/{int((~lat).sum())}")
print("\n   per-window speed census (a moving wheel order would concentrate here):")
edges = [0, 1, 2, 4, 7, 11, 16, 30]
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (v >= lo) & (v < hi)
    if not m.sum():
        continue
    f0s = col(R50, "fb")[m & det]
    print(f"     {lo:2d}-{hi:2d} m/s  n={int(m.sum()):3d}  det {int((m & det).sum()):3d}  "
          f"f0 med {np.median(f0s) if len(f0s) else np.nan:5.2f}  "
          f"env99 med {np.median(col(R50, 'env99')[m]):6.0f}  "
          f"wheel-1 {np.mean([lo, hi]) / CIRC[0]:5.2f} Hz")
OUT["scan"] = dict(nwin=len(R50), ndet=int(det.sum()), neng=int(lat.sum()),
                   ndet_eng=int((det & lat).sum()), ndet_man=int((det & ~lat).sum()))

# =============================================================== ss3 amplitude inventory ==========
hdr(f"ss3  ★★ AMPLITUDE-FIRST INVENTORY -- 6-9 Hz envelope p99 >= {AMP_MIN:.0f} counts "
    f"(p-p >= {2 * AMP_MIN:.0f}). This is the criterion the record's 46-window/118 s figure uses.")
print("   zcHz = upward zero-crossing rate of the 6-9 Hz bandpass -- an f0 estimate with NO FFT bin")
print("   in it, so it is an INDEPENDENT confirmation of the line frequency.\n")
print(f"   {'seg':>3s} {'t0':>6s} {'f0':>5s} {'zcHz':>5s} {'prom':>7s} {'Q':>5s} {'pp cnt':>7s} "
      f"{'|v|':>5s} {'ang':>7s} {'|rt|90':>6s} {'eff':>5s} {'lat':>4s} {'|cmd|p99':>8s} {'ST':>8s}")
hits = [r for r in R50 if r["env99"] >= AMP_MIN]
for r in sorted(hits, key=lambda r: (r["seg"], r["t0"])):
    print(f"   {r['seg']:3d} {r['t0']:6.1f} {r['fb']:5.2f} {r['zc']:5.2f} {r['pb']:7.1f} "
          f"{r['Q']:5.1f} {2 * r['env99']:7.0f} {r['v']:5.2f} {r['ang']:7.1f} {r['rate90']:6.0f} "
          f"{r['eff']:5.0f} {r['lat']:4.2f} {r['e4']:8.0f} {str(r['sstat']):>8s}")
zc = col(hits, "zc")
zc = zc[np.isfinite(zc)]
lt = col(hits, "lat")
print(f"\n   {len(hits)} windows ({NFFT / 100 * len(hits):.0f} s) at or above {2 * AMP_MIN:.0f} "
      f"counts p-p.  ENGAGED {int((lt > 0.9).sum())}, MANUAL {int((lt < 0.1).sum())}, "
      f"mixed {int(((lt >= 0.1) & (lt <= 0.9)).sum())}")
if len(zc):
    print(f"   ZERO-CROSSING f0: median {np.median(zc):.2f} Hz, mean {zc.mean():.2f} "
          f"+/- {zc.std(ddof=1) if len(zc) > 1 else 0:.2f}, range [{zc.min():.2f}, {zc.max():.2f}]")
fbh = col(hits, "fb")
fbh = fbh[np.isfinite(fbh)]
if len(fbh):
    print(f"   SPECTRAL   f0: median {np.median(fbh):.2f} Hz, range [{fbh.min():.2f}, "
          f"{fbh.max():.2f}]   ⇒ record (route 4f): median 7.79 Hz")
print(f"   max p-p on this route: {2 * max(col(R50, 'env99')):.0f} counts   "
      f"⇒ record (route 4f) peak: 6,065")
OUT["amp_inventory"] = dict(n=len(hits), secs=float(NFFT / 100 * len(hits)),
                            eng=int((lt > 0.9).sum()), man=int((lt < 0.1).sum()),
                            zc_med=float(np.median(zc)) if len(zc) else np.nan,
                            f0_med=float(np.median(fbh)) if len(fbh) else np.nan,
                            max_pp=float(2 * max(col(R50, "env99"))),
                            rows=[{k: (list(r[k]) if k == "sstat" else r[k])
                                   for k in ("seg", "t0", "fb", "zc", "pb", "Q", "env99", "v",
                                             "ang", "rate90", "eff", "lat", "e4", "sstat")}
                                  for r in hits])

# =============================================================== ss4 comparison to the record =====
hdr("ss4  THE SAME INVENTORY ON THE COMPARISON ROUTES -- so 'provoked' can be priced")
print(f"   {'route':10s} {'wins':>6s} {'route s':>8s} | {'>=1200 p-p':>11s} {'secs':>7s} "
      f"{'% of route':>11s} | {'max p-p':>8s} {'f0 med':>7s} {'zc med':>7s} {'eng frac':>9s}")
cmp_ = {}
for tag, rs in ALL.items():
    h = [r for r in rs if r["env99"] >= AMP_MIN]
    z = col(h, "zc") if h else np.array([])
    z = z[np.isfinite(z)]
    fbv = col(h, "fb") if h else np.array([])
    fbv = fbv[np.isfinite(fbv)]
    lt = col(h, "lat") if h else np.array([])
    cmp_[tag] = dict(nwin=len(rs), route_s=len(rs) * NFFT / 100, nhit=len(h),
                     hit_s=len(h) * NFFT / 100, frac=len(h) / max(len(rs), 1),
                     maxpp=float(2 * max(col(rs, "env99"))) if rs else np.nan,
                     f0=float(np.median(fbv)) if len(fbv) else np.nan,
                     zc=float(np.median(z)) if len(z) else np.nan,
                     engfrac=float((lt > 0.9).mean()) if len(lt) else np.nan)
    c = cmp_[tag]
    print(f"   {tag:10s} {c['nwin']:>6d} {c['route_s']:>8.1f} | {c['nhit']:>11d} "
          f"{c['hit_s']:>7.1f} {100 * c['frac']:>10.1f}% | {c['maxpp']:>8.0f} {c['f0']:>7.2f} "
          f"{c['zc']:>7.2f} {c['engfrac']:>9.2f}")
OUT["route_comparison"] = cmp_

# =============================================================== ss5 speed slope + engagement =====
hdr("ss5  SPEED DEPENDENCE and ENGAGEMENT CONDITIONALITY")
print("   Theil-Sen slope of f0 (zero-crossing, FFT-free) on speed, over the amplitude hits.")
print(f"   Wheel order 1 would give {1 / CIRC[0]:.3f} Hz per m/s.  The record's ratchet slope is "
      f"+0.0358 (speed-invariant).\n")


def theilsen(x, y, nboot=4000, rng=np.random.default_rng(20260804)):
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
    p = sl(x, y)
    dr = np.empty(nboot)
    for b in range(nboot):
        k = rng.integers(0, len(x), len(x))
        dr[b] = sl(x[k], y[k])
    return p, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), len(x)


sp = {}
for tag, rs in ALL.items():
    h = [r for r in rs if r["env99"] >= AMP_MIN]
    for lbl, key in (("zero-crossing", "zc"), ("spectral", "fb")):
        s, lo, hi, n = theilsen(col(h, "v"), col(h, key))
        sp[f"{tag}|{lbl}"] = dict(slope=s, lo=lo, hi=hi, n=n)
        print(f"   {tag:10s} {lbl:14s} slope {s:+7.4f} Hz per m/s  [{lo:+7.4f}, {hi:+7.4f}]  "
              f"n={n:3d}   wheel-1 = {1 / CIRC[0]:+.3f}  "
              f"{'⇒ SPEED-INVARIANT' if np.isfinite(hi) and hi < 0.2 else ''}")
OUT["speed_slope"] = sp

print("\n   ENGAGEMENT CONDITIONALITY -- amplitude hits, engaged vs manual, against exposure")
from _r47_lib import fisher2x2  # noqa: E402
eng_cond = {}
for tag, rs in ALL.items():
    lt = col(rs, "lat") > 0.5
    hi_ = col(rs, "env99") >= AMP_MIN
    a11, a10 = int((hi_ & lt).sum()), int((~hi_ & lt).sum())
    a01, a00 = int((hi_ & ~lt).sum()), int((~hi_ & ~lt).sum())
    p = fisher2x2(a11, a10, a01, a00)
    eng_cond[tag] = dict(hit_eng=a11, eng=a11 + a10, hit_man=a01, man=a01 + a00, p=p)
    print(f"   {tag:10s} engaged {a11:3d}/{a11 + a10:4d} = {100 * a11 / max(a11 + a10, 1):5.1f}%   "
          f"manual {a01:3d}/{a01 + a00:4d} = {100 * a01 / max(a01 + a00, 1):5.1f}%   "
          f"Fisher p = {p:.3g}")
OUT["engagement"] = eng_cond

# =============================================================== ss6 Q at longer NFFT =============
hdr("ss6  ★ Q -- re-cut the longest amplitude episodes at NFFT 512 / 1024 / 2048")
print("   The Hann main lobe caps a measurable Q at f0/(1.44*fs/nfft). At 7.8 Hz and fs 100:")
for nf in (256, 512, 1024, 2048):
    print(f"      NFFT {nf:>4d} = {nf / 100:5.2f} s window  ⇒  Q cap {7.8 / (1.44 * 100 / nf):6.1f}")
print("   A Q AT the cap is a measurement of the WINDOW, not of the plant. Reported only when the")
print("   measured -3 dB width is comfortably wider than the lobe.\n")


def runs_of_hits(rs):
    """Contiguous runs of amplitude hits inside one segment."""
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


eps = runs_of_hits(R50)
print(f"   {len(eps)} contiguous amplitude episodes on route 50:")
qtab = []
cache = {}
for k, e in enumerate(eps):
    s = e[0]["seg"]
    if s not in cache:
        cache[s] = load(*ROUTES["V70 r50"][:2], s)
    d = cache[s]
    fs = e[0]["fs"]
    i0 = e[0]["i0"]
    n_avail = len(d["t"]) - i0
    dur = len(e) * NFFT / fs
    print(f"\n   --- episode {k}: seg {s}, t {e[0]['t0']:.1f}-{e[-1]['t0'] + NFFT / fs:.1f} s, "
          f"{dur:.2f} s, {len(e)} windows, p-p max {2 * max(col(e, 'env99')):.0f}, "
          f"|v| {min(col(e, 'vmin')):.2f}-{max(col(e, 'vmax')):.2f} m/s, lat {np.mean(col(e, 'lat')):.2f}")
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
        flag = "AT THE CAP -- window-limited, NOT a plant Q" if (np.isfinite(Q) and Q >= 0.85 * cap) \
            else "resolved (below the cap)"
        print(f"       NFFT {nf:>4d} ({nf / fs:5.2f} s)  f0 {f0:6.3f} Hz  prom {pr:8.1f}  "
              f"zc {z:5.2f}  Q {Q:6.1f}  cap {cap:6.1f}   {flag}")
        qtab.append(dict(ep=k, seg=int(s), nfft=nf, f0=float(f0), prom=float(pr), Q=float(Q),
                         cap=float(cap), zc=float(z)))
OUT["episodes"] = [dict(k=k, seg=int(e[0]["seg"]), t0=float(e[0]["t0"]),
                        dur=float(len(e) * NFFT / e[0]["fs"]), nwin=len(e),
                        pp=float(2 * max(col(e, "env99"))),
                        vlo=float(min(col(e, "vmin"))), vhi=float(max(col(e, "vmax"))),
                        lat=float(np.mean(col(e, "lat"))),
                        f0=float(np.median(col(e, "fb"))), zc=float(np.nanmedian(col(e, "zc"))))
                   for k, e in enumerate(eps)]
OUT["Q"] = qtab

# =============================================================== ss7 which channel carries it =====
hdr("ss7  ★ WHICH CHANNEL CARRIES THE LINE? bar torque vs angle-rate vs openpilot's command")
print("   On route 4f the line was in the BAR and the ANGLE-RATE but NOT in openpilot's command")
print("   (`e4tq` prominence median 2.7 against a >10 criterion) ⇒ the loop closes inside the EPS +")
print("   plant, not through openpilot. Re-tested here on the PROVOKED episodes.\n")
print(f"   {'seg':>3s} {'t0':>6s} | {'tq f0':>6s} {'tq prom':>8s} | {'rate f0':>7s} "
      f"{'rate prom':>9s} | {'ang f0':>7s} {'ang prom':>9s} | {'e4 f0':>6s} {'e4 prom':>8s}")
ch = []
for r in sorted(hits, key=lambda r: (r["seg"], r["t0"])):
    s = r["seg"]
    if s not in cache:
        cache[s] = load(*ROUTES["V70 r50"][:2], s)
    d = cache[s]
    fs = r["fs"]
    w = slice(r["i0"], r["i0"] + NFFT)
    f = np.fft.rfftfreq(NFFT, 1 / fs)
    row = dict(seg=int(s), t0=float(r["t0"]))
    for nm, key in (("tq", "tq"), ("rate", "rate_c"), ("ang", "ang"), ("e4", "e4tq")):
        P = periodogram(np.asarray(d[key], float)[w], fs, NFFT)
        if P is None:
            row[nm + "_f0"] = row[nm + "_pr"] = np.nan
            continue
        f0, pr = peak_prom(f, P, *RATCH)
        row[nm + "_f0"], row[nm + "_pr"] = float(f0), float(pr)
    ch.append(row)
    print(f"   {s:3d} {r['t0']:6.1f} | {row['tq_f0']:6.2f} {row['tq_pr']:8.1f} | "
          f"{row['rate_f0']:7.2f} {row['rate_pr']:9.1f} | {row['ang_f0']:7.2f} "
          f"{row['ang_pr']:9.1f} | {row['e4_f0']:6.2f} {row['e4_pr']:8.1f}")
if ch:
    print(f"\n   MEDIAN prominence over the {len(ch)} amplitude windows:  "
          + "   ".join(f"{nm} {np.nanmedian([c[nm + '_pr'] for c in ch]):.2f}"
                       for nm in ("tq", "rate", "ang", "e4")))
    print("   criterion: prominence > 10 = the line is present in that channel.  ⇒ record on 4f: "
          "bar YES, angle-rate YES, command NO (2.7).")
OUT["channels"] = ch

(HERE / "_r50_ratchet.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_r50_ratchet.json'}")
