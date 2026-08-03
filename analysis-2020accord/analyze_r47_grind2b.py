#!/usr/bin/env python3
"""Second pass on V67 / route 47: the three-dose HIGHWAY test, and what the highway symptom is.

Answers the orchestrator's five follow-ups. Companion to `analyze_r47_grind2.py`; the identity,
gating, low-speed and wheel-order results live there and are not repeated.

★ THE UNLOCK: V58 route `2b` segments 7-10 are 227 s of ENGAGED highway at Kd = 1.00x -- the
baseline three sessions recorded as "does not exist". It sat unused because BOTH route tables that
list 2b (`_r31_common.SEGS_2B` and `_r37_ratchet_lib.ROUTES`) enumerate [0,1,2,11,12,13], which
excludes exactly the highway segments. Registered here as `V58/r2b` with all 14 segments.

🛑 What still CANNOT be answered, and is not worked around anywhere below: no route in this kit has
a single LKAS-off window above 10 m/s. So "the boosted rate lane causes it" (H1) and "LKAS torque
itself causes it" (H2) cannot be separated by an engaged/manual contrast at highway speed. The only
available discriminator is the CROSS-BUILD DOSE ORDERING at matched speed and engagement, which H2
does not predict -- §A.

Sections:
  A  three-dose highway table, exposure-matched, episode-clustered, MEAN and TAIL, split-half null
  B  a severity-matched manoeuvre definition that transfers between routes -- or the finding that
     it cannot
  C  the 6-9 Hz RATCHET hypothesis: is the highway manoeuvre band the parking-lot ratchet?
  D  which band tracks manoeuvre SEVERITY -- the band the driver is feeling
  E  VEHICLE SPEED as a separator, reported separately for each population
  F  command magnitude after controlling for steering rate (H2's own prediction)

Usage:  python analyze_r47_grind2b.py            (all)
        python analyze_r47_grind2b.py A C        (named sections)
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402
import _r47_lib as R  # noqa: E402
from _r31_common import fs_of, load, periodogram, runs_of, sustained  # noqa: E402

OUTJSON = HERE / "_r47_grind2b.json"
RNG = np.random.default_rng(20260802)
FS_TRUE = 100.000
NF = G.NFFT
HWY = 20.0
CREEP = 4.0
BANDS7 = ("1-4", "6-9", "10-16", "18-22", "24-28", "30-40", "40-49")
OUT = {}

# Highway-appropriate matching cells. G's own bins are creep-scaled: its top v-bin is "14+", which
# lumps 20 and 33 m/s together, and its rate bins start at 0-4 deg/s, which swallows ~90% of highway
# windows into one cell. Matching on those would be matching on nothing.
V_H = [(20, 24), (24, 27), (27, 29.5), (29.5, 31.5), (31.5, 40)]
R_H = [(0, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 1e9)]
D_H = [(0, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 1e9)]     # angle excursion = manoeuvre severity


def hcell(r, with_dang=True):
    c = (G.binof(r["v"], V_H), G.binof(r["rate"], R_H))
    return c + ((G.binof(r["dang"], D_H),) if with_dang else ())


def tag_cells(rs, with_dang=True):
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = hcell(r, with_dang)
        out.append(q)
    return out


def hwy(store, build, eng=True):
    return [r for r in store[build] if r["v"] >= HWY and (r["eng"] == 1) == eng]


def pool(store, builds, eng=True):
    return [r for b in builds for r in hwy(store, b, eng)]


def sec_A(store):
    G.hdr("§A  THE THREE-DOSE HIGHWAY TABLE.  All three arms are ENGAGED highway, so LKAS reach is\n"
          "the same 4x on every build (V38 onward) and only the rate-lane dose differs. H2 (LKAS\n"
          "torque itself) predicts NO dose ordering here; H1 (the boosted rate lane) predicts one.")
    print(f"  {'dose':>6s} {'routes':22s} {'nwin':>5s} {'nblk':>5s} {'nruns':>6s} {'secs':>7s} "
          f"{'v p50':>6s} {'rate p90':>8s} {'dang p90':>8s}")
    expo = {}
    for k in sorted(R.DOSE_HWY):
        rs = pool(store, R.DOSE_HWY[k])
        if not rs:
            continue
        expo[k] = dict(n=len(rs), nblk=len({r["blk"] for r in rs}),
                       nrun=len({r["ep"] for r in rs}), secs=len({r["blk"] for r in rs}) * 10.24)
        print(f"  {k:6.2f} {','.join(R.DOSE_HWY[k]):22s} {len(rs):5d} "
              f"{len({r['blk'] for r in rs}):5d} {len({r['ep'] for r in rs}):6d} "
              f"{expo[k]['secs']:7.0f} {np.median(G.col(rs, 'v')):6.2f} "
              f"{np.percentile(G.col(rs, 'rate'), 90):8.2f} "
              f"{np.percentile(G.col(rs, 'dang'), 90):8.2f}")
    OUT["A_exposure"] = expo

    G.EPKEY = "blk"
    for lbl, sel, wd in (("ALL engaged highway windows", lambda r: True, True),
                         ("MANOEUVRE windows only (dang >= 2 deg)",
                          lambda r: r["dang"] >= 2.0, False)):
        print(f"\n  ---- {lbl} ----")
        print(f"  cells = speed x |steering rate|" + (" x angle excursion" if wd else "") +
              f";  CI = 1500 block-resampled draws;  null = split-half inside the Kd=1.00 pool")
        base = tag_cells([r for r in pool(store, R.DOSE_HWY[1.00]) if sel(r)], wd)
        for k in (2.00, 2.44):
            arm = tag_cells([r for r in pool(store, R.DOSE_HWY[k]) if sel(r)], wd)
            if len(arm) < 10 or len(base) < 10:
                print(f"  Kd={k}: too few windows ({len(arm)} vs {len(base)})")
                continue
            print(f"\n  Kd={k:.2f} / Kd=1.00   ({len(arm)} vs {len(base)} windows)")
            print(f"  {'band':8s} {'MEDIAN':>8s} {'95% CI':>17s} {'cells':>5s} | {'p95':>8s} "
                  f"{'95% CI':>17s} | {'split-half null':>17s} | {'verdict':>12s}")
            rows = {}
            for bd in BANDS7:
                key = "e_" + bd
                med = G.boot_cellwise(arm, base, key, RNG, nboot=1500, min_ep=2, min_win=4)
                p95 = G.boot_cellwise(arm, base, key, RNG, nboot=1500, min_ep=2, min_win=4,
                                      agg=lambda v: np.percentile(v, 95))
                nul = G.split_half_null(base, key, RNG, nrep=200, min_ep=2, min_win=4)
                ok = np.isfinite(med[0])
                inside = bool(ok and np.isfinite(nul[1]) and nul[1] <= med[0] <= nul[2])
                rows[bd] = dict(med=med[:3], p95=p95[:3], null=nul, inside=inside)
                print(f"  {bd:8s} {med[0]:8.3f} [{med[1]:6.3f},{med[2]:6.3f}] {med[3]:5d} | "
                      f"{p95[0]:8.3f} [{p95[1]:6.3f},{p95[2]:6.3f}] | "
                      f"[{nul[1]:7.3f},{nul[2]:7.3f}] | "
                      f"{('IN NULL' if inside else 'outside') if ok else 'n/a':>12s}")
            OUT[f"A_{lbl[:9]}_{k}"] = rows

    # the threshold-free statement: what did each dose's tail actually reach?
    print("\n  THRESHOLD-FREE TAIL.  A maximum scales with sample size, so blocks are reported too.")
    print(f"  {'dose':>6s} {'nwin':>5s} {'nblk':>5s} {'40-49 p50':>10s} {'p90':>7s} {'p99':>8s} "
          f"{'max':>8s} {'blk>200':>8s} {'blk>300':>8s} | {'30-49 max':>10s}")
    tail = {}
    for k in sorted(R.DOSE_HWY):
        rs = pool(store, R.DOSE_HWY[k])
        if not rs:
            continue
        e = G.col(rs, "e_40-49")
        a2, n2 = R.blockstat(rs, "e_40-49", 200.0)
        a3, n3 = R.blockstat(rs, "e_40-49", 300.0)
        tail[k] = dict(mx=float(e.max()), blk200=(a2, n2), blk300=(a3, n3))
        print(f"  {k:6.2f} {len(rs):5d} {n2:5d} {np.median(e):10.1f} "
              f"{np.percentile(e, 90):7.1f} {np.percentile(e, 99):8.1f} {e.max():8.1f} "
              f"{f'{a2}/{n2}':>8s} {f'{a3}/{n3}':>8s} | "
              f"{G.col(rs, 'e_30-49').max():10.1f}")
    print("\n  For scale: creep grind #2 bursts run 2,000-4,000 counts with prominence 25-1000x.")
    OUT["A_tail"] = tail


def sec_B(store):
    G.hdr("§B  CAN A MANOEUVRE DEFINITION TRANSFER BETWEEN ROUTES?  A within-route quantile cannot\n"
          "(a top-quintile threshold is 2-3 deg on one route and 27 deg on another). The only\n"
          "transferable definition is an ABSOLUTE one, so first: what severities does each route\n"
          "actually contain at highway speed?")
    print(f"  {'route':10s} {'dose':>5s} {'nwin':>5s} | " +
          " ".join(f"{f'dang>={t:g}':>10s}" for t in (1, 2, 4, 6, 10)) +
          f" | {'dang p50':>8s} {'p90':>7s} {'p99':>7s} {'max':>7s}")
    sev = {}
    for k in sorted(R.DOSE_HWY):
        for b in R.DOSE_HWY[k]:
            rs = hwy(store, b)
            if not rs:
                continue
            d = G.col(rs, "dang")
            cells = [f"{int((d >= t).sum()):10d}" for t in (1, 2, 4, 6, 10)]
            sev[b] = dict(n=len(rs), p90=float(np.percentile(d, 90)), mx=float(d.max()),
                          over={str(t): int((d >= t).sum()) for t in (1, 2, 4, 6, 10)})
            print(f"  {b:10s} {k:5.2f} {len(rs):5d} | " + " ".join(cells) +
                  f" | {np.median(d):8.2f} {np.percentile(d, 90):7.2f} "
                  f"{np.percentile(d, 99):7.2f} {d.max():7.2f}")
    OUT["B_severity"] = sev
    print("\n  ⇒ read the dang>=4 and >=6 columns: that is the population the operator described,")
    print("    and whether the Kd<=1 routes contain any of it decides whether §A's manoeuvre arm")
    print("    is a comparison or an extrapolation.")

    # the same question expressed as seconds, on raw frames, so short manoeuvres are not lost
    print("\n  SECONDS above each severity, RAW FRAMES (a 1 s swing never fills a 2.56 s window):")
    print(f"  {'route':10s} {'hwy s':>8s} " +
          " ".join(f"{f'|rate|>={t:g} deg/s':>16s}" for t in (4, 8, 15)))
    secs = {}
    for k in sorted(R.DOSE_HWY):
        for b in R.DOSE_HWY[k]:
            B = G.BUILDS[b]
            tot = np.zeros(4)
            for s in B["segs"]:
                p = B["cache"] / f"{B['pfx']}{s}.npz"
                if not p.exists():
                    continue
                d = load(s, B["cache"], B["pfx"])
                fs = fs_of(d)
                m = (np.abs(d["cs_v"]) >= HWY) & (d["cc_lat"] > 0.5)
                rt = np.abs(d["rate_c"])
                tot[0] += m.sum() / fs
                for i, t in enumerate((4, 8, 15)):
                    tot[i + 1] += (m & (rt >= t)).sum() / fs
            secs[b] = tot.tolist()
            print(f"  {b:10s} {tot[0]:8.1f} " + " ".join(f"{tot[i + 1]:16.1f}" for i in range(3)))
    OUT["B_seconds"] = secs


def sec_C(store):
    G.hdr("§C  IS THE HIGHWAY MANOEUVRE BAND THE RATCHET?  The parking-lot ratchet is ~7.4 Hz,\n"
          "Q ~ 36, with its 2nd harmonic LOCKED at ~15.0 Hz -- that harmonic lock is its signature\n"
          "and broadband roughness cannot fake it.")
    # locate the 5-12 Hz line and test for a 2f0 partner, on the true grid
    def probe(build, selfn, nmax=4000):
        Bb = G.BUILDS[build]
        got = []
        f = np.fft.rfftfreq(NF, 1 / FS_TRUE)
        for s in Bb["segs"]:
            p = Bb["cache"] / f"{Bb['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = load(s, Bb["cache"], Bb["pfx"])
            x = np.asarray(d["tq"], float)
            v = np.abs(d["cs_v"])
            le = d["cc_lat"] > 0.5
            rt = np.abs(d["rate_c"])
            for a, b in runs_of(le, d["t"], NF):
                for i in range(0, b - a - NF + 1, G.HOP):
                    sl = slice(a + i, a + i + NF)
                    if not selfn(float(np.mean(v[sl])), float(np.mean(rt[sl]))):
                        continue
                    P = periodogram(x[sl], FS_TRUE, NF, True)
                    if P is None:
                        continue
                    Rr = G.prom_spectrum(f, P)
                    f0, pr = G.locate(f, P, 5.0, 12.0, R=Rr)
                    if not np.isfinite(f0) or pr < 4:
                        continue
                    f2, p2 = G.locate(f, P, max(2 * f0 - 2.0, 12.5), 2 * f0 + 2.0, R=Rr)
                    got.append(dict(f0=f0, prom=pr, Q=G.q_of(f, P, f0), f2=f2, p2=p2,
                                    ratio=(f2 / f0 if np.isfinite(f2) else np.nan),
                                    rms=float(np.sqrt(np.sum(P[(f >= 6) & (f <= 9)])) / NF * 4)))
                    if len(got) >= nmax:
                        return got
        return got

    pops = [("PARKING-LOT ratchet (V62 r37, v<4, engaged)", "V62/r37",
             lambda v, rt: v < CREEP),
            ("PARKING-LOT ratchet (V65 r3a, v<4, engaged)", "V65/r3a",
             lambda v, rt: v < CREEP),
            ("r47 HIGHWAY manoeuvre (v>=20, |rate|>=4)", "V67/r47",
             lambda v, rt: v >= HWY and rt >= 4.0),
            ("r47 HIGHWAY cruise    (v>=20, |rate|<1.5)", "V67/r47",
             lambda v, rt: v >= HWY and rt < 1.5)]
    print(f"  {'population':44s} {'n':>5s} {'f0 med':>7s} {'sd':>6s} {'prom':>7s} {'Q':>6s} "
          f"{'2f0 lock':>9s} {'6-9 rms':>8s}")
    rat = {}
    for nm, b, fn in pops:
        got = probe(b, fn)
        if len(got) < 8:
            print(f"  {nm:44s} {len(got):5d}   (too few)")
            continue
        f0 = np.array([g["f0"] for g in got])
        rr = np.array([g["ratio"] for g in got])
        rr = rr[np.isfinite(rr)]
        lock = float(np.mean(np.abs(rr - 2.0) < 0.08)) if len(rr) else np.nan
        rat[nm] = dict(n=len(got), f0=float(np.median(f0)), sd=float(np.std(f0, ddof=1)),
                       prom=float(np.median([g["prom"] for g in got])),
                       Q=float(np.nanmedian([g["Q"] for g in got])), lock=lock)
        print(f"  {nm:44s} {len(got):5d} {np.median(f0):7.2f} {np.std(f0, ddof=1):6.2f} "
              f"{np.median([g['prom'] for g in got]):7.2f} "
              f"{np.nanmedian([g['Q'] for g in got]):6.1f} {lock:9.3f} "
              f"{np.median([g['rms'] for g in got]):8.1f}")
    print("\n  '2f0 lock' = fraction of windows whose strongest partner line sits within 4% of 2*f0.")
    OUT["C_ratchet"] = rat

    # cross-dose, manoeuvre-conditioned, 6-9 Hz specifically
    print("\n  6-9 Hz AT HIGHWAY, MANOEUVRE-CONDITIONED, ACROSS DOSES (same estimator as §A):")
    G.EPKEY = "blk"
    base = tag_cells([r for r in pool(store, R.DOSE_HWY[1.00]) if r["dang"] >= 2.0], False)
    print(f"  {'dose':>6s} {'nwin':>5s} {'6-9 ratio':>10s} {'95% CI':>17s} "
          f"{'split-half null':>17s} {'verdict':>10s}")
    for k in (2.00, 2.44):
        arm = tag_cells([r for r in pool(store, R.DOSE_HWY[k]) if r["dang"] >= 2.0], False)
        med = G.boot_cellwise(arm, base, "e_6-9", RNG, nboot=1500, min_ep=2, min_win=4)
        nul = G.split_half_null(base, "e_6-9", RNG, nrep=200, min_ep=2, min_win=4)
        ok = np.isfinite(med[0])
        inside = bool(ok and nul[1] <= med[0] <= nul[2])
        print(f"  {k:6.2f} {len(arm):5d} {med[0]:10.3f} [{med[1]:7.3f},{med[2]:7.3f}] "
              f"[{nul[1]:7.3f},{nul[2]:7.3f}] "
              f"{('IN NULL' if inside else 'outside') if ok else 'n/a':>10s}")


def sec_D(store):
    G.hdr("§D  WHICH BAND TRACKS MANOEUVRE SEVERITY?  The band the driver is feeling should scale\n"
          "with how big the manoeuvre is. 21 atlas manoeuvres, each with its own severity\n"
          "covariates; Spearman rho of the band envelope against each covariate, plus the\n"
          "manoeuvre/matched-control ratio for the same band.")
    ap = HERE.parent / "_cache_r47" / "r47_maneuvers.json"
    if not ap.exists():
        print("  no atlas file.")
        return
    atlas = json.loads(ap.read_text())
    NF8 = 128
    taper = np.hanning(NF8) + 1e-3
    cw = slice(int(0.2 * NF8), int(0.8 * NF8))
    cache = {}

    def bands_of(ep):
        out = {k: 0.0 for k in BANDS7}
        n = 0
        for sp in ep.get("spans", []):
            s = int(sp["seg"])
            d = cache.setdefault(s, load(s, G.BUILDS["V67/r47"]["cache"], "r47s"))
            x = np.asarray(d["tq"], float)[int(sp["i0"]):int(sp["i1"])]
            for i in range(0, max(len(x) - NF8 + 1, 0), NF8 // 2):
                for k in BANDS7:
                    lo, hi = G.BANDS[k]
                    out[k] = max(out[k], G.win_env(x[i:i + NF8], FS_TRUE, lo, hi, taper, cw))
                n += 1
        return (out if n else None)

    mans = [(e, bands_of(e)) for e in atlas.get("maneuvers", [])]
    mans = [(e, b) for e, b in mans if b]
    ctls = [b for b in (bands_of(e) for e in atlas.get("controls", [])) if b]
    if len(mans) < 8:
        print("  too few scorable manoeuvres.")
        return

    def spearman(a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() < 6:
            return np.nan
        ra = np.argsort(np.argsort(a[m])).astype(float)
        rb = np.argsort(np.argsort(b[m])).astype(float)
        return float(np.corrcoef(ra, rb)[0, 1])

    COV = ["dev_swing", "ang_peak", "rate_peak", "arate_peak", "tq_peak", "ccreq_peak",
           "e4tq_peak", "v_mean"]
    print(f"  {'band':8s} {'man/ctl':>8s} " + " ".join(f"{c[:10]:>11s}" for c in COV))
    dtab = {}
    for k in BANDS7:
        mv = np.array([b[k] for _, b in mans])
        cv = np.array([b[k] for b in ctls])
        ratio = np.median(mv) / max(np.median(cv), 1e-9)
        rhos = [spearman([e.get(c, np.nan) for e, _ in mans], mv) for c in COV]
        dtab[k] = dict(ratio=float(ratio), rho=dict(zip(COV, rhos)))
        print(f"  {k:8s} {ratio:8.2f} " + " ".join(f"{r:11.3f}" for r in rhos))
    print(f"\n  n = {len(mans)} manoeuvres / {len(ctls)} matched controls. |rho| > 0.43 is p < 0.05")
    print("  two-sided at n = 21; treat anything below that as no relationship.")
    OUT["D_severity"] = dtab


def sec_E(store):
    G.hdr("§E  VEHICLE SPEED AS A SEPARATOR.  Grind #1 is creep-only; the highway symptom is not.\n"
          "If speed separates them, the fix is a calibration edit on the damper LERP's own speed\n"
          "axis -- no code, no gate. Reported for each population SEPARATELY, because they may need\n"
          "different answers.")
    print("  Band envelope (p50 / p90) vs speed, on the Kd=2-family builds, ENGAGED only.")
    print(f"  {'v band':>10s} {'nwin':>5s} {'nblk':>5s} | {'18-22 (grind1)':>16s} "
          f"{'40-49 (grind2)':>16s} {'6-9 (ratchet)':>16s} | {'rate p50':>8s} {'eff p50':>8s}")
    pops = [r for b in ("V62/r37", "V65/r3a", "V65/r3b", "V67/r47") for r in store[b]
            if r["eng"] == 1]
    VB = [(0, 1), (1, 2), (2, 4), (4, 6), (6, 10), (10, 14), (14, 20), (20, 27), (27, 40)]
    erow = {}
    for lo, hi in VB:
        rs = [r for r in pops if lo <= r["v"] < hi]
        if len(rs) < 8:
            continue
        cells = []
        for k in ("18-22", "40-49", "6-9"):
            e = G.col(rs, "e_" + k)
            cells.append(f"{np.median(e):7.1f}/{np.percentile(e, 90):8.1f}")
        erow[f"{lo}-{hi}"] = dict(n=len(rs),
                                  **{k: float(np.percentile(G.col(rs, "e_" + k), 90))
                                     for k in ("18-22", "40-49", "6-9")})
        print(f"  {f'{lo:g}-{hi:g}':>10s} {len(rs):5d} {len({r['blk'] for r in rs}):5d} | " +
              " ".join(f"{c:>16s}" for c in cells) +
              f" | {np.median(G.col(rs, 'rate')):8.1f} {np.median(G.col(rs, 'eff')):8.0f}")
    OUT["E_speed"] = erow

    print("\n  SEPARATION POWER OF SPEED, population by population. AUC = P(speed higher in a burst")
    print("  block than a quiet block) computed WITHIN each population's own regime, so it measures")
    print("  whether speed selects the symptom rather than merely labelling the regime.")
    print(f"  {'population':40s} {'burst def':>18s} {'n blk':>6s} {'AUC(speed)':>11s} "
          f"{'burst v':>8s} {'quiet v':>8s}")
    import analyze_r47_grind2 as A1
    for nm, rs, key, thr in (
            ("grind #1, creep, Kd=2 builds", [r for b in ("V62/r37", "V65/r3a", "V65/r3b")
                                              for r in store[b] if r["v"] < CREEP],
             "e_18-22", 300.0),
            ("grind #2, creep, Kd=2 builds", [r for b in ("V62/r37", "V65/r3a", "V65/r3b")
                                              for r in store[b] if r["v"] < CREEP],
             "e_40-49", 400.0),
            ("highway symptom, r47, v>=20", hwy(store, "V67/r47"), "e_30-49", 300.0),
            ("highway symptom, all doses", pool(store, sum(R.DOSE_HWY.values(), [])),
             "e_30-49", 200.0)):
        a, p = A1.block_perm_p(rs, "v", key, thr, RNG, nperm=2000)
        blks = {}
        for r in rs:
            blks.setdefault(r["blk"], []).append(r)
        lab = {b: any(x[key] > thr for x in v) for b, v in blks.items()}
        bv = np.nanmedian([np.nanmean([x["v"] for x in v]) for b, v in blks.items() if lab[b]])
        qv = np.nanmedian([np.nanmean([x["v"] for x in v]) for b, v in blks.items() if not lab[b]])
        print(f"  {nm:40s} {key + '>' + str(int(thr)):>18s} {len(blks):6d} {a:11.3f} "
              f"{bv:8.2f} {qv:8.2f}   p={p:.4f}")

    print("\n  THE DIRECT QUESTION: do the three populations occupy DISJOINT speed ranges?")
    print(f"  {'population':34s} {'n':>5s} {'v p05':>7s} {'p50':>7s} {'p95':>7s} {'min':>7s} "
          f"{'max':>7s}")
    for nm, rs in (("grind #1 bursts (18-22 > 300)",
                    [r for b in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[b]
                     if r["e_18-22"] > 300]),
                   ("grind #2 creep bursts (40-49 > 400)",
                    [r for b in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[b]
                     if r["v"] < CREEP and r["e_40-49"] > 400]),
                   ("highway symptom (30-49 > 300, v>=20)",
                    [r for r in store["V67/r47"] if r["v"] >= HWY and r["e_30-49"] > 300])):
        if not rs:
            continue
        v = G.col(rs, "v")
        print(f"  {nm:34s} {len(rs):5d} {np.percentile(v, 5):7.2f} {np.median(v):7.2f} "
              f"{np.percentile(v, 95):7.2f} {v.min():7.2f} {v.max():7.2f}")


def sec_F(store):
    G.hdr("§F  H2's OWN PREDICTION: does the highway band track COMMAND MAGNITUDE once steering\n"
          "rate is held fixed?  Under H2 (LKAS torque causes it) it should; under H1 (the rate lane)\n"
          "it need not. Stratified on |steering rate| so the two cannot stand in for each other.")
    rs = hwy(store, "V67/r47")
    print(f"  {'|rate| stratum':>16s} {'nwin':>5s} {'nblk':>5s} | " +
          " ".join(f"{k:>22s}" for k in ("AUC |0x0E4| max", "AUC openpilot |trq|")))
    import analyze_r47_grind2 as A1
    for lo, hi in R_H:
        sub = [r for r in rs if lo <= r["rate"] < hi]
        if len(sub) < 30:
            print(f"  {f'{lo:g}-{hi:g}':>16s} {len(sub):5d}   (too few)")
            continue
        cells = []
        for k in ("e4max", "req"):
            a, p = A1.block_perm_p(sub, k, "e_30-49", 300.0, RNG, nperm=1500)
            cells.append(f"{a:8.3f} (p={p:.3f})" if np.isfinite(a) else f"{'.':>22s}")
        print(f"  {f'{lo:g}-{hi:g}':>16s} {len(sub):5d} {len({r['blk'] for r in sub}):5d} | " +
              " ".join(f"{c:>22s}" for c in cells))
    print("\n  and the reverse, as the control: steering rate stratified on command magnitude")
    print(f"  {'|0x0E4| max stratum':>20s} {'nwin':>5s} {'AUC |steering rate|':>22s}")
    for lo, hi in [(0, 300), (300, 600), (600, 1e9)]:
        sub = [r for r in rs if lo <= r["e4max"] < hi]
        if len(sub) < 30:
            print(f"  {f'{lo:g}-{hi:g}':>20s} {len(sub):5d}   (too few)")
            continue
        a, p = A1.block_perm_p(sub, "rate", "e_30-49", 300.0, RNG, nperm=1500)
        print(f"  {f'{lo:g}-{hi:g}':>20s} {len(sub):5d} "
              f"{(f'{a:.3f} (p={p:.3f})' if np.isfinite(a) else '.'):>22s}")

    print("\n  OPERATING POINTS IN BUS UNITS.  `rate_c` is 0x14A bytes 2:3 with factor -1; opendbc")
    print("  names it STEER_ANGLE_RATE and its unit is deg/s. Quoted here in deg/s only -- the")
    print("  gp-0x6ac0 LERP-axis scaling is a firmware question this agent cannot settle.")
    print(f"  {'population':38s} {'|rate| p50':>11s} {'p90':>8s} {'p99':>8s} {'max':>8s}")
    for nm, sub in (("r47 highway, all engaged", rs),
                    ("r47 highway BURST windows", [r for r in rs if r["e_30-49"] > 300]),
                    ("creep grind #2 bursts (Kd=2)",
                     [r for b in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[b]
                      if r["v"] < CREEP and r["e_40-49"] > 400]),
                    ("creep grind #1 bursts (Kd=2)",
                     [r for b in ("V62/r37", "V65/r3a", "V65/r3b") for r in store[b]
                      if r["v"] < CREEP and r["e_18-22"] > 300])):
        if not sub:
            continue
        r_ = G.col(sub, "ratep95")
        print(f"  {nm:38s} {np.median(G.col(sub, 'rate')):11.1f} "
              f"{np.percentile(r_, 90):8.1f} {np.percentile(r_, 99):8.1f} {r_.max():8.1f}")


def main():
    want = set(x.upper() for x in sys.argv[1:]) or {"A", "B", "C", "D", "E", "F"}
    store = R.records(order=R.ORDER_HWY)
    for k, fn in (("A", sec_A), ("B", sec_B), ("C", sec_C), ("D", sec_D), ("E", sec_E),
                  ("F", sec_F)):
        if k in want:
            fn(store)
    OUTJSON.write_text(json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
