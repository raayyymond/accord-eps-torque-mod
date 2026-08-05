#!/usr/bin/env python3
"""D4 -- AUDIT OF FIX 2: did V72 actually move the ~7.79 Hz RATCHET?

THE PRIOR, which this file must reproduce before it may quote a V72 number:
  "THE RATCHET IS ENGAGEMENT-REQUIRED, AND NO BUILD IN THIS KIT HAS EVER MOVED IT" -- engaged
  hands-off 73/88 = 83.0% vs manual hands-off 0/118 = 0.0%, Fisher p = 3.8e-41, per-build rate
  80/81/79/94% across V70/V69/V62/V59 => build-independent. Median 7.79 Hz, speed-invariant,
  peak p-p up to 8,521 counts (V71C).

INSTRUMENT: `r58_ratchet.py` COPIED, not re-derived -- DISJOINT 2.56 s windows (NFFT 256),
PROMINENCE argmax over a FREE 5-12 Hz range, physical amplitude = 6-9 Hz analytic envelope p99
(p-p = 2x), AMP_MIN = 600 counts envelope, fs = `_r4f_lib.fs_lattice`, engagement `cc_lat`,
hands-off = median |lowpass(tq,3Hz)| <= 300. Route 59 is added; nothing numeric is changed, so the
V72 number is computed with the identical instrument as the four baseline builds.

ADDED here, and only here: an EPISODE-BOOTSTRAPPED attenuation factor with a split-half null, which
`r58_ratchet.py` does not compute (it reports a binary hit rate only). D3-microratchet needs the
factor, not the binary.

Writes `_d4_r59_ratchet.json`.
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
from _r31_common import band_envelope, peak_prom, periodogram, q_of, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
FREE = (5.0, 12.0)
CTRL_A = (10.5, 13.5)
CTRL_B = (24.0, 27.0)
HANDS_OFF = 300.0
CREEP_R = 4.0
AMP_MIN = 600.0
OUT = {}

# (cache, prefix, segments, skip, carries 0x454FE)
ROUTES = {
    "V59 r2c":  ("_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], [], False),
    "V62 r37":  ("_cache_r37", "r37s", list(range(15)), [], False),
    "V67 r47":  ("_cache_r47", "r47s", list(range(26)), [], False),
    "V69 r4f":  ("_cache_r4f", "r4fs", list(range(8)), [], False),
    "V70 r50":  ("_cache_r50", "r50s", [0, 1, 2], [0], False),
    "V71B r54": ("_cache_r54", "r54s", list(range(21)), [10, 11], True),
    "V71C r58": ("_cache_r58", "r58s", list(range(16)), [12, 13, 14, 15], True),
    "V72 r59":  ("_cache_r59", "r59s", list(range(15)), [12, 13, 14], True),
}
NEW = "V72 r59"
BASELINE4 = ["V70 r50", "V69 r4f", "V62 r37", "V59 r2c"]     # the recorded 80/81/79/94% quartet


def hdr(s):
    print("\n" + "=" * 122 + f"\n{s}\n" + "=" * 122)


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def bp(x, fs, lo, hi):
    z = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(z)
    f = np.fft.rfftfreq(len(z), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(z))


def zcross(x, fs, lo, hi):
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
                             ratemax=float(np.abs(d["rate_c"][w]).max()),
                             eff=float(np.median(eff[w])), lat=float(lat[w].mean()),
                             e4=float(np.percentile(np.abs(d["e4tq"][w]), 99)),
                             # ~10 s episode block for the bootstrap: 4 disjoint windows
                             ep=(tag, int(s), i // (NFFT * 4))))
    return recs


ALL = {tag: scan(c, p, s, sk, tag) for tag, (c, p, s, sk, _) in ROUTES.items()}

# =============================================================== §1 the null ======================
hdr("§1  THE NULL FIRST -- two control bands per route; the LARGER (conservative) floor is used.")
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
hdr(f"§2  AMPLITUDE INVENTORY -- 6-9 Hz envelope p99 >= {AMP_MIN:.0f} counts (p-p >= "
    f"{2 * AMP_MIN:.0f}). The record's own criterion.")
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
hdr("§3  ★★★ THE HEADLINE -- engaged hands-off creep vs manual hands-off creep. THE RECORDED "
    "CONDITIONAL.")
print(f"   Both arms median |lowpass(tq,3Hz)| <= {HANDS_OFF:.0f}, creep < {CREEP_R:.0f} m/s.")
print("   POOLED PRIOR across four builds: 73/88 = 83% engaged vs 0/118 = 0% manual.\n")
print(f"   {'route':10s} | {'eng hands-off':>18s} {'man hands-off':>18s} {'Fisher p':>10s}   "
      f"{'eng secs':>9s} {'man secs':>9s}")
cx = {}
for tag, rs in ALL.items():
    cr = [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF]
    a = [r for r in cr if r["lat"] > 0.9]
    b = [r for r in cr if r["lat"] < 0.1]
    a11 = sum(1 for r in a if r["env99"] >= AMP_MIN)
    a01 = sum(1 for r in b if r["env99"] >= AMP_MIN)
    cx[tag] = dict(eng_hit=a11, eng_n=len(a), man_hit=a01, man_n=len(b),
                   eng_s=len(a) * NFFT / 100, man_s=len(b) * NFFT / 100)
    if not a or not b:
        print(f"   {tag:10s} | {f'{a11}/{len(a)}':>18s} {f'{a01}/{len(b)}':>18s} {'--':>10s}"
              f"   {len(a) * NFFT / 100:>9.1f} {len(b) * NFFT / 100:>9.1f}   one arm EMPTY")
        continue
    p = fisher2x2(a11, len(a) - a11, a01, len(b) - a01)
    cx[tag].update(p=float(p), eng_rate=a11 / len(a), man_rate=a01 / len(b))
    print(f"   {tag:10s} | {f'{a11}/{len(a)} = {100 * a11 / len(a):.0f}%':>18s} "
          f"{f'{a01}/{len(b)} = {100 * a01 / len(b):.0f}%':>18s} {p:>10.3g}"
          f"   {len(a) * NFFT / 100:>9.1f} {len(b) * NFFT / 100:>9.1f}")
OUT["headline_2x2"] = cx

print("\n   ★ THE BASELINE REPRODUCTION -- the recorded 80/81/79/94% quartet, recomputed here:")
ea = sum(cx[k]["eng_hit"] for k in BASELINE4)
en = sum(cx[k]["eng_n"] for k in BASELINE4)
ma = sum(cx[k]["man_hit"] for k in BASELINE4)
mn = sum(cx[k]["man_n"] for k in BASELINE4)
print(f"     pooled V70/V69/V62/V59: engaged {ea}/{en} = {100 * ea / max(en, 1):.1f}%  "
      f"manual {ma}/{mn} = {100 * ma / max(mn, 1):.1f}%   (record: 73/88 = 83.0% vs 0/118 = 0.0%)")
n72 = cx[NEW]
pv = fisher2x2(n72["eng_hit"], n72["eng_n"] - n72["eng_hit"], ea, en - ea) \
    if n72["eng_n"] else np.nan
print(f"     V72 engaged hands-off creep {n72['eng_hit']}/{n72['eng_n']} = "
      f"{100 * n72['eng_hit'] / max(n72['eng_n'], 1):.1f}%   vs the quartet   Fisher p = {pv:.4g}")
OUT["baseline_pool"] = dict(eng_hit=ea, eng_n=en, man_hit=ma, man_n=mn, v72_vs_quartet=float(pv))

# =============================================================== §4 ATTENUATION FACTOR ============
hdr("§4  ★★★ THE ATTENUATION FACTOR (for D3-microratchet) -- 6-9 Hz envelope p99, engaged\n"
    "    hands-off creep, ratio V72 / reference. EPISODE bootstrap (~10 s blocks), against a\n"
    "    SPLIT-HALF NULL computed inside the pooled pair with the identical estimator.")


def eps_of(rs):
    e = {}
    for r in rs:
        e.setdefault(r["ep"], []).append(r)
    return list(e.values())


def boot_ratio(A, B, key="env99", stat=np.median, nb=4000, rng=None):
    rng = rng or np.random.default_rng(20260805)
    ea, eb = eps_of(A), eps_of(B)
    if len(ea) < 2 or len(eb) < 2:
        return np.nan, np.nan, np.nan
    pa = [col(e, key) for e in ea]
    pb = [col(e, key) for e in eb]
    pt = stat(col(A, key)) / max(stat(col(B, key)), 1e-9)
    dr = np.empty(nb)
    for i in range(nb):
        sa = np.concatenate([pa[k] for k in rng.integers(0, len(pa), len(pa))])
        sb = np.concatenate([pb[k] for k in rng.integers(0, len(pb), len(pb))])
        dr[i] = stat(sa) / max(stat(sb), 1e-9)
    return float(pt), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


def split_null(rs, key="env99", stat=np.median, nb=800, rng=None):
    rng = rng or np.random.default_rng(20260806)
    e = eps_of(rs)
    if len(e) < 4:
        return np.nan, np.nan
    out = []
    for _ in range(nb):
        p = rng.permutation(len(e))
        h = len(e) // 2
        s1 = np.concatenate([col(e[i], key) for i in p[:h]])
        s2 = np.concatenate([col(e[i], key) for i in p[h:2 * h]])
        out.append(stat(s1) / max(stat(s2), 1e-9))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


CELLS = {
    "engaged hands-off creep": lambda r: (r["v"] < CREEP_R and r["eff"] <= HANDS_OFF
                                          and r["lat"] > 0.9),
    "engaged creep (any grip)": lambda r: r["v"] < CREEP_R and r["lat"] > 0.9,
    "manual creep": lambda r: r["v"] < CREEP_R and r["lat"] < 0.1,
    "engaged all speeds": lambda r: r["lat"] > 0.9,
}
att = {}
for cn, sel in CELLS.items():
    print(f"\n   --- cell: {cn}")
    A = [r for r in ALL[NEW] if sel(r)]
    print(f"   {'reference':12s} {'nA':>4s} {'nB':>4s} | {'med p-p A':>10s} {'med p-p B':>10s} "
          f"{'ratio(med)':>10s} {'95% CI':>19s} {'null':>17s} | {'ratio(p90)':>10s} "
          f"{'95% CI':>19s}")
    for ref in ["V71C r58", "V71B r54", "V70 r50", "V69 r4f", "V62 r37", "V59 r2c", "V67 r47"]:
        B = [r for r in ALL[ref] if sel(r)]
        if len(A) < 4 or len(B) < 4:
            print(f"   {ref:12s} {len(A):>4d} {len(B):>4d} |  *** too few")
            continue
        m = boot_ratio(A, B)
        p9 = boot_ratio(A, B, stat=lambda v: np.percentile(v, 90))
        nl = split_null(A + B)
        att[f"{cn}|{ref}"] = dict(nA=len(A), nB=len(B), med=m, p90=p9, null=list(nl),
                                  ppA=float(2 * np.median(col(A, "env99"))),
                                  ppB=float(2 * np.median(col(B, "env99"))))
        tag = ("" if not np.isfinite(nl[0]) else
               ("inside null" if nl[0] <= m[0] <= nl[1] else "*** OUTSIDE NULL"))
        print(f"   {ref:12s} {len(A):>4d} {len(B):>4d} | "
              f"{2 * np.median(col(A, 'env99')):>10.0f} {2 * np.median(col(B, 'env99')):>10.0f} "
              f"{m[0]:>10.3f} [{m[1]:>7.3f},{m[2]:>8.3f}] [{nl[0]:>6.2f},{nl[1]:>7.2f}] | "
              f"{p9[0]:>10.3f} [{p9[1]:>7.3f},{p9[2]:>8.3f}]  {tag}")
OUT["attenuation"] = att

# =============================================================== §5 amplitude distribution ========
hdr("§5  THE AMPLITUDE DISTRIBUTION in engaged hands-off creep -- eliminated or attenuated?")
print(f"   {'route':10s} {'n':>4s} {'secs':>6s} | " +
      " ".join(f"{f'p{q}':>8s}" for q in (50, 75, 90, 99)) +
      f" {'max':>8s} | " + " ".join(f"{'>=' + str(c):>7s}" for c in (300, 600, 900, 1200)))
dist = {}
for tag, rs in ALL.items():
    s = [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9]
    if not s:
        print(f"   {tag:10s} {0:>4d}  (empty)")
        continue
    e = 2 * col(s, "env99")           # peak-to-peak counts
    dist[tag] = dict(n=len(s), secs=len(s) * NFFT / 100,
                     pct={q: float(np.percentile(e, q)) for q in (50, 75, 90, 99)},
                     mx=float(e.max()),
                     ex={c: float(np.mean(e >= 2 * c)) for c in (300, 600, 900, 1200)})
    print(f"   {tag:10s} {len(s):>4d} {len(s) * NFFT / 100:>6.1f} | " +
          " ".join(f"{np.percentile(e, q):>8.0f}" for q in (50, 75, 90, 99)) +
          f" {e.max():>8.0f} | " +
          " ".join(f"{100 * np.mean(e >= 2 * c):>6.1f}%" for c in (300, 600, 900, 1200)))
OUT["dist"] = dist

# =============================================================== §6 f0 and channels ===============
hdr("§6  IS WHAT REMAINS THE SAME LINE? f0 of the strongest 5-12 Hz line in engaged hands-off "
    "creep.")
print(f"   {'route':10s} {'n':>4s} | {'f0 spec med':>12s} {'f0 zc med':>10s} {'prom med':>9s} "
      f"{'prom p90':>9s} {'floor':>7s}  above floor?")
f0t = {}
for tag, rs in ALL.items():
    s = [r for r in rs if r["v"] < CREEP_R and r["eff"] <= HANDS_OFF and r["lat"] > 0.9]
    if len(s) < 4:
        continue
    fb = col(s, "fb")
    fb = fb[np.isfinite(fb)]
    zc = col(s, "zc")
    zc = zc[np.isfinite(zc)]
    pb = col(s, "pb")
    pb = pb[np.isfinite(pb)]
    f0t[tag] = dict(n=len(s), f0=float(np.median(fb)), zc=float(np.median(zc)),
                    prom=float(np.median(pb)), prom90=float(np.percentile(pb, 90)),
                    floor=floors[tag])
    print(f"   {tag:10s} {len(s):>4d} | {np.median(fb):>12.2f} {np.median(zc):>10.2f} "
          f"{np.median(pb):>9.2f} {np.percentile(pb, 90):>9.2f} {floors[tag]:>7.2f}  "
          f"{'YES' if np.percentile(pb, 90) > floors[tag] else 'no'}")
OUT["f0"] = f0t

(ROOT / "_d4_r59_ratchet.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_d4_r59_ratchet.json'}")
