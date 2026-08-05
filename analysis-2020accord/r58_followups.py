#!/usr/bin/env python3
"""ROUTES 54 / 58 -- the four follow-ups the headline numbers demand.

§A  THE 2x HARMONIC TEST. The operator reports the two grinds *feel like the same thing*. Estimate
    f0 FREE in 15-26 Hz and FREE in 35-49 Hz per window and test f_hi / f_lo against 2.000.
    🛑 A STRICT band would bound the ratio into [40/22, 49/18] = [1.82, 2.72] and manufacture the
    answer. Free bands, prominence-gated, with a phase-independent second method (does the 40-49
    envelope co-vary with the 18-22 envelope within a window?).

§B  IS THE 48% vs 80% RATCHET HIT-RATE DROP AN AMPLITUDE SHIFT OR A THRESHOLD ARTEFACT?
    Compare the whole p-p DISTRIBUTION in the engaged-hands-off-creep cell, not just the crossings.

§C  Q -- THE WINDOW-CAP INVARIANCE TEST, scored. Q(2N)/Q(N) per episode. A window-limited estimate
    doubles; a real one does not.

§D  ROUTE 58's GRIND #2 BURSTS -- when, how fast, how many DISTINCT events, and what the
    contemporaneous byte-stock manual arm was doing at the same time.

Writes `_r58_followups.json`.  Usage: python r58_followups.py
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

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r58_lib as L  # noqa: E402
import r47_orchestrator_checks as R47  # noqa: E402
from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402
import _r4f_lib as R4F  # noqa: E402
from _r47_lib import fisher2x2  # noqa: E402

L.install_fs()
NFFT = 256
RNG = np.random.default_rng(20260804)
OUT = {}
ROUTES = {"V71B r54": ("_cache_r54", "r54s", [s for s in range(21) if s not in (10, 11)]),
          "V71C r58": ("_cache_r58", "r58s", [s for s in range(16) if s not in (12, 13, 14, 15)]),
          "V62 r37": ("_cache_r37", "r37s", list(range(15))),
          "V65 r3b": ("_cache_r3b", "r3bs", list(range(14))),
          "V69 r4f": ("_cache_r4f", "r4fs", list(range(8)))}


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116)


# =================================================================== §A the 2x harmonic test ======
hdr("§A  ★★ THE 2x HARMONIC TEST -- is the 40-49 Hz line at exactly TWICE the 18-22 Hz line?")
print("   FREE locators: f_lo in 15-26 Hz, f_hi in 35-49 Hz, prominence argmax (never raw power).")
print("   Windows are kept only when BOTH lines clear a prominence gate, so the ratio is measured")
print("   where both lines EXIST. The band edges bound the ratio into [1.35, 3.27], which comfortably")
print("   contains 2.000 without pinning it.\n")
LO_FREE, HI_FREE = (15.0, 26.0), (35.0, 49.0)
PGATE = 8.0

har = {}
for tag, (cache, pfx, segs) in ROUTES.items():
    rows = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        elo = band_envelope(tq, fs, 18.0, 22.0)
        ehi = band_envelope(tq, fs, 40.0, 49.0)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        for i in range(0, len(tq) - NFFT + 1, NFFT // 2):
            w = slice(i, i + NFFT)
            P = periodogram(tq[w], fs, NFFT)
            if P is None:
                continue
            flo, plo = peak_prom(f, P, *LO_FREE)
            fhi, phi = peak_prom(f, P, *HI_FREE)
            if not (np.isfinite(flo) and np.isfinite(fhi)):
                continue
            a, b = elo[w], ehi[w]
            cc = (float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 0 and np.std(b) > 0 else np.nan)
            rows.append(dict(seg=int(s), t0=float(d["t"][i]), flo=flo, fhi=fhi, plo=plo, phi=phi,
                             ratio=fhi / flo, lat=float(lat[w].mean()), v=float(v[w].mean()),
                             elo=float(np.percentile(a, 99)), ehi=float(np.percentile(b, 99)),
                             env_corr=cc))
    sel = [r for r in rows if r["plo"] >= PGATE and r["phi"] >= PGATE]
    rr = np.array([r["ratio"] for r in sel], float)
    ec = np.array([r["env_corr"] for r in sel], float)
    ec = ec[np.isfinite(ec)]
    allec = np.array([r["env_corr"] for r in rows], float)
    allec = allec[np.isfinite(allec)]
    if len(rr) >= 4:
        # episode-free but block-resampled CI on the median ratio (blocks = 8 windows)
        blk = {}
        for j, r in enumerate(sel):
            blk.setdefault((r["seg"], j // 8), []).append(r["ratio"])
        per = [np.array(v, float) for v in blk.values()]
        dr = np.array([np.median(np.concatenate([per[k] for k in
                                                 RNG.integers(0, len(per), len(per))]))
                       for _ in range(3000)])
        lo, hi = float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))
    else:
        lo = hi = np.nan
    har[tag] = dict(nwin=len(rows), ngate=len(sel),
                    med=float(np.median(rr)) if len(rr) else np.nan, lo=lo, hi=hi,
                    flo=float(np.median([r["flo"] for r in sel])) if sel else np.nan,
                    fhi=float(np.median([r["fhi"] for r in sel])) if sel else np.nan,
                    env_corr=float(np.median(ec)) if len(ec) else np.nan,
                    env_corr_all=float(np.median(allec)) if len(allec) else np.nan)
    x = har[tag]
    print(f"   {tag:10s} windows {x['nwin']:>5d}  both-lines-prominent {x['ngate']:>5d}  | "
          f"f_lo med {x['flo']:6.2f}  f_hi med {x['fhi']:6.2f}  | RATIO med {x['med']:6.3f} "
          f"[{lo:6.3f}, {hi:6.3f}]  {'2.000 INSIDE' if np.isfinite(lo) and lo <= 2.0 <= hi else '*** 2.000 EXCLUDED'}")
print("\n   Second, PHASE-FREE method -- within-window correlation of the 18-22 and 40-49 envelopes.")
print("   A true 2nd harmonic is amplitude-locked to its fundamental, so a burst in one IS a burst")
print("   in the other. Independent modes give ~0.\n")
for tag, x in har.items():
    print(f"   {tag:10s} envelope corr: gated windows {x['env_corr']:+6.3f}   "
          f"ALL windows {x['env_corr_all']:+6.3f}")
OUT["harmonic"] = har

# =================================================================== §B ratchet amplitude shift ====
hdr("§B  IS THE RATCHET HIT-RATE DROP AN AMPLITUDE SHIFT? -- the whole p-p distribution in the "
    "engaged hands-off creep cell")
print("   The 48% vs 80% figure is a THRESHOLD crossing at 1200 counts p-p. If the distribution has")
print("   merely shifted down, the medians move too; if the cell composition changed (slower, more")
print("   highway, different provocation) the distribution can look similar with fewer crossings.\n")
print(f"   {'route':10s} {'0x454FE':>8s} {'n':>5s} {'hits':>5s} {'hit%':>6s} | "
      f"{'p-p p25':>8s} {'p-p p50':>8s} {'p-p p75':>8s} {'p-p p90':>8s} {'p-p max':>8s} | "
      f"{'v med':>6s} {'eff med':>8s} {'ang med':>8s}")
HAS454 = {"V71B r54": True, "V71C r58": True, "V62 r37": False, "V65 r3b": False, "V69 r4f": False}
amp = {}
for tag, (cache, pfx, segs) in ROUTES.items():
    rows = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        fs = R4F.fs_lattice(d)
        tq = np.asarray(d["tq"], float)
        env = band_envelope(tq, fs, 6.0, 9.0)
        eff = np.abs(sustained(tq, fs))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.abs(np.asarray(d["cs_v"], float))
        ang = np.abs(np.asarray(d["ang"], float))
        for i in range(0, len(tq) - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            if not (v[w].mean() < 4.0 and np.median(eff[w]) <= 300.0 and lat[w].mean() > 0.9):
                continue
            rows.append(dict(pp=2 * float(np.percentile(env[w], 99)), v=float(v[w].mean()),
                             eff=float(np.median(eff[w])), ang=float(np.mean(ang[w]))))
    if not rows:
        print(f"   {tag:10s} {'':>8s} {0:>5d}   *** empty cell")
        continue
    pp = np.array([r["pp"] for r in rows])
    h = int((pp >= 1200).sum())
    amp[tag] = dict(has454=HAS454[tag], n=len(rows), hits=h, rate=h / len(rows),
                    p25=float(np.percentile(pp, 25)), p50=float(np.percentile(pp, 50)),
                    p75=float(np.percentile(pp, 75)), p90=float(np.percentile(pp, 90)),
                    mx=float(pp.max()), v=float(np.median([r["v"] for r in rows])),
                    eff=float(np.median([r["eff"] for r in rows])),
                    ang=float(np.median([r["ang"] for r in rows])))
    x = amp[tag]
    print(f"   {tag:10s} {('YES' if x['has454'] else 'no'):>8s} {x['n']:>5d} {h:>5d} "
          f"{100 * x['rate']:>5.1f}% | {x['p25']:>8.0f} {x['p50']:>8.0f} {x['p75']:>8.0f} "
          f"{x['p90']:>8.0f} {x['mx']:>8.0f} | {x['v']:>6.2f} {x['eff']:>8.0f} {x['ang']:>8.1f}")
OUT["ratchet_amplitude"] = amp

# =================================================================== §C the Q cap-invariance ======
hdr("§C  Q -- THE WINDOW-CAP INVARIANCE TEST, SCORED.  Q(2N)/Q(N) per episode.")
print("   A window-limited estimate doubles when the window doubles (ratio ~2). A resolved plant Q")
print("   does not move (ratio ~1). Computed from `_r58_ratchet.json`'s own episode table.\n")
qp = ROOT / "_r58_ratchet.json"
if qp.exists():
    qt = json.loads(qp.read_text())["Q"]
    by = {}
    for r in qt:
        by.setdefault((r["tag"], r["ep"]), {})[r["nfft"]] = r
    print(f"   {'route':10s} {'ep':>3s} | " + " ".join(f"{f'Q@{n}':>8s}" for n in
                                                       (256, 512, 1024, 2048))
          + " | " + " ".join(f"{f'x{a}->{b}':>9s}" for a, b in
                             ((256, 512), (512, 1024), (1024, 2048))))
    ratios = []
    for (tag, ep), rr in sorted(by.items()):
        qs = [rr.get(n, {}).get("Q", np.nan) for n in (256, 512, 1024, 2048)]
        rs = []
        for a, b in ((0, 1), (1, 2), (2, 3)):
            rs.append(qs[b] / qs[a] if (np.isfinite(qs[a]) and np.isfinite(qs[b])
                                        and qs[a] > 0) else np.nan)
        ratios += [x for x in rs if np.isfinite(x)]
        print(f"   {tag:10s} {ep:>3d} | " + " ".join(f"{q:>8.1f}" for q in qs)
              + " | " + " ".join(f"{x:>9.2f}" for x in rs))
    ratios = np.array(ratios, float)
    print(f"\n   Median Q(2N)/Q(N) over {len(ratios)} doublings = {np.median(ratios):.2f}   "
          f"[p25 {np.percentile(ratios, 25):.2f}, p75 {np.percentile(ratios, 75):.2f}]")
    print("   ⇒ " + ("WINDOW-LIMITED at every rung: NO Q here is a plant Q."
                     if np.median(ratios) > 1.5 else
                     "the estimate is stabilising; a plant Q may be resolvable."))
    OUT["Q_cap_test"] = dict(median=float(np.median(ratios)), n=int(len(ratios)),
                             p25=float(np.percentile(ratios, 25)),
                             p75=float(np.percentile(ratios, 75)))

# =================================================================== §D route 58's grind #2 =======
hdr("§D  ROUTE 58's GRIND #2 BURSTS -- located in time, and the contemporaneous byte-stock manual arm")
rows = [r for r in R47._windows("_cache_r58", "r58", lambda v: True)
        if not any(s in str(r["ep"][0]) for s in ("r58s12", "r58s13", "r58s14", "r58s15"))]
bur = [r for r in rows if r["40-49"] > R47.BURST]
print(f"   {len(bur)} burst windows out of {len(rows)}.  40-49 Hz envelope p99 > {R47.BURST:.0f}\n")
print(f"   {'segment':<22} {'win i':>6} {'40-49':>8} {'24-28':>8} {'18-22':>8} {'6-9':>8} "
      f"{'v':>6} {'ang':>7} {'lat':>5}")
for r in sorted(bur, key=lambda r: (str(r["ep"][0]), r["ep"][1])):
    print(f"   {Path(r['ep'][0]).name:<22} {r['ep'][1]:>6} {r['40-49']:>8.0f} {r['24-28']:>8.0f} "
          f"{r['18-22']:>8.0f} {r['6-9']:>8.0f} {r['v']:>6.2f} {r['ang']:>7.1f} {r['lat']:>5.2f}")
nep = len({(r["ep"][0], r["ep"][1]) for r in bur})
print(f"\n   DISTINCT ~10 s blocks containing a burst: {nep}  (a burst spanning several overlapping")
print("   windows is ONE event; this is the honest event count).")
eng = [r for r in rows if r["lat"] > 0.5]
man = [r for r in rows if r["lat"] <= 0.5]
be, bm = sum(1 for r in eng if r["40-49"] > R47.BURST), sum(1 for r in man if r["40-49"] > R47.BURST)
p = fisher2x2(be, len(eng) - be, bm, len(man) - bm)
print(f"\n   ★ WITHIN-ROUTE, WITHIN-DRIVER, vs BYTE-STOCK MANUAL:")
print(f"     ENGAGED (V71C arms live) {be}/{len(eng)} windows burst, max 40-49 = "
      f"{max(r['40-49'] for r in eng):.0f} counts")
print(f"     manual  (byte-STOCK)     {bm}/{len(man)} windows burst, max 40-49 = "
      f"{max(r['40-49'] for r in man):.0f} counts")
print(f"     Fisher exact p = {p:.4g}   ratio of maxima = "
      f"{max(r['40-49'] for r in eng) / max(r['40-49'] for r in man):.1f}x")
OUT["r58_bursts"] = dict(n=len(bur), nwin=len(rows), nblocks=nep, eng=be, eng_n=len(eng),
                         man=bm, man_n=len(man), fisher=float(p),
                         eng_max=float(max(r["40-49"] for r in eng)),
                         man_max=float(max(r["40-49"] for r in man)),
                         rows=[dict(seg=Path(r["ep"][0]).name, i=int(r["ep"][1]),
                                    b4049=float(r["40-49"]), b2428=float(r["24-28"]),
                                    b1822=float(r["18-22"]), b69=float(r["6-9"]),
                                    v=float(r["v"]), ang=float(r["ang"]), lat=float(r["lat"]))
                               for r in bur])

(ROOT / "_r58_followups.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_r58_followups.json'}")
