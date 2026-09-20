# -*- coding: utf-8 -*-
"""THE AMPLITUDE STREAM, part 2 -- the refined describing function.

Adds over hsurf.py:
  * amplitude bins that reach into the TAIL (0-25, 25-50, 50-75, 75-90, 90-100 percentiles), because a
    saturation signature would live in the top few percent of demand, not in the top quartile;
  * PHASE / effective lag per amplitude bin, so "the extra lag is on small corrections" can be tested
    against AMPLITUDE at fixed frequency rather than against frequency;
  * the RAIL-WINDOW CONTRAST, run where railing actually exists;
  * a fine (decile) amplitude sweep to locate the small-amplitude knee;
  * the 2-8 m/s low-speed cell with a median split so n survives.

MEASUREMENT FROM LOGGED DATA throughout.  ANALYSIS ONLY.  Run: python hsurf2.py
"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dflib as D            # noqa: E402
import fastH as FH           # noqa: E402
import v282cmp as C          # noqa: E402

GROUPS = [("V282", ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]),
          ("V282old", ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"]),
          ("TQ64", ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]),
          ("TQall", ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                     "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"])]
PCT = [0, 25, 50, 75, 90, 100]
MIN_WIN = 8
NB = 300
LOG = []
rng = np.random.default_rng(11)


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


def cell(ws, boot=True):
    if len(ws) < MIN_WIN:
        return None
    res = FH.pool([w["spec"] for w in ws])
    cids = sorted({w["cid"] for w in ws})
    sh = {}
    if len(cids) > 1:
        ea = set(cids[0::2])
        A = FH.pool([w["spec"] for w in ws if w["cid"] in ea])
        B = FH.pool([w["spec"] for w in ws if w["cid"] not in ea])
        if A and B:
            sh = {k: abs(A[k] - B[k]) / 2.0 for k in ("H", "NE", "lag")}
    by = {}
    for w in ws:
        by.setdefault(w["cid"], []).append(w["spec"])
    bv = {"H": [], "NE": [], "lag": []}
    if boot and len(by) >= 2:
        keys = list(by)
        for _ in range(NB):
            pick = rng.choice(len(keys), len(keys), replace=True)
            r = FH.pool([s for k in pick for s in by[keys[k]]])
            if r:
                for k in bv:
                    bv[k].append(r[k])
    out = dict(res)
    out.update(nw=len(ws), ncl=len(cids), sh=sh, boot=bv,
               A=float(np.median([w["A"] for w in ws])),
               Amin=float(min(w["A"] for w in ws)), Amax=float(max(w["A"] for w in ws)),
               v=float(np.median([w["v"] for w in ws])),
               ang=float(np.median([w["sa_med"] for w in ws])),
               nrail=int(sum(1 for w in ws if w["rail"] > 0)))
    return out


def rci(a, b, k):
    x, y = a["boot"].get(k, []), b["boot"].get(k, [])
    if len(x) < 50 or len(y) < 50:
        return (np.nan, np.nan)
    m = min(len(x), len(y))
    rt = np.array(x[:m]) / np.maximum(np.abs(np.array(y[:m])), 1e-9)
    return (float(np.percentile(rt, 2.5)), float(np.percentile(rt, 97.5)))


def dci(a, b, k, scale=1.0):
    x, y = a["boot"].get(k, []), b["boot"].get(k, [])
    if len(x) < 50 or len(y) < 50:
        return (np.nan, np.nan)
    m = min(len(x), len(y))
    d = (np.array(x[:m]) - np.array(y[:m])) * scale
    return (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


RUNS = {}
for rk in C.ROUTES:
    RUNS[rk], _ = D.route_runs(rk)

SURF = {}
for f1, f2, W in D.BANDS:
    WS = {}
    for rk in C.ROUTES:
        ws = D.windows(RUNS[rk], W)
        for w in ws:
            w["A"] = D.amp(w, f1, f2)
            w["spec"] = FH.win_spec(w, f1, f2, W)
        WS[rk] = ws
    SURF[(f1, f2, W)] = WS


def gather(WS, rks, slo, shi, lo=0.0, hi=1e9, extra=None):
    out = []
    for ri, rk in enumerate(rks):
        for w in WS[rk]:
            if slo <= w["v"] < shi and lo <= w["A"] < hi and (extra is None or extra(w)):
                w2 = dict(w); w2["cid"] = (ri, w["rid"]); out.append(w2)
    return out


# ============================================================================== SECTION C2
pr("=" * 150)
pr("SECTION C2   |H|, TRACKING ERROR NE AND EFFECTIVE LAG vs DEMAND AMPLITUDE (percentile bins incl. the tail)")
pr("=" * 150)
pr("Amplitude bins are percentiles 0-25 / 25-50 / 50-75 / 75-90 / 90-100 of the POOLED (V282 + V282old +")
pr("TQ64) windows in that speed x band cell, so the bins are matched AND the top decile is resolved --")
pr("a saturation signature would live there, not in the top quartile.")
pr("NE = normalised in-band |achieved - desired| / |desired|.  lag = -phase/(2 pi f_c), + = car behind.")
pr("Cells whose coherence is below the 0.50 floor are printed with a '!' and are NOT admissible as gains.")
pr("")
TAB = {}
for f1, f2, W in D.BANDS:
    WS = SURF[(f1, f2, W)]
    pr("-" * 150)
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz   window {W/D.FS:.2f} s")
    for slo, shi in D.SPD:
        pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk]
                  if slo <= w["v"] < shi]
        if len(pooled) < 5 * MIN_WIN:
            continue
        ed = [float(q) for q in np.percentile(pooled, PCT)]
        ed[0], ed[-1] = 0.0, 1e9
        pr(f"  v {slo}-{shi} m/s")
        pr(f"  {'bin':>7s} {'medA':>7s} {'deg':>6s} {'|ang|':>6s} |" +
           "|".join(f"{g:^38s}" for g, _ in GROUPS) + "|  NE ratio TQall/V282   d_lag ms")
        pr(f"  {'':>7s} {'':>7s} {'':>6s} {'':>6s} |" +
           "|".join(f"{'H':>6s}{'coh':>5s}{'NE':>6s}{'shNE':>6s}{'lag':>7s}{'n':>5s}   " for _ in GROUPS) + "|")
        for q in range(5):
            lo, hi = ed[q], ed[q + 1]
            row = {g: cell(gather(WS, rks, slo, shi, lo, hi)) for g, rks in GROUPS}
            ref = row["V282"]
            if ref is None:
                continue
            degA = ref["A"] / max(ref["v"], 1.0) ** 2 * float(D.deg_per_curv(ref["v"]))
            nm = f"{PCT[q]}-{PCT[q+1]}"
            line = f"  {nm:>7s} {ref['A']:7.4f} {degA:6.2f} {ref['ang']:6.1f} |"
            for g, _ in GROUPS:
                r = row[g]
                line += ((f"{r['H']:6.2f}{r['coh']:5.2f}{'!' if r['coh'] < D.COH_MIN else ' '}"
                          f"{r['NE']:5.2f}{r['sh'].get('NE', float('nan')):6.3f}"
                          f"{1000*r['lag']:+7.0f}{r['nw']:5d}  ") if r else f"{'--':^38s}") + "|"
            t = row["TQall"]
            if t:
                c = rci(t, ref, "NE"); dl = dci(t, ref, "lag", 1000.0)
                line += (f" x{t['NE']/max(ref['NE'],1e-9):5.2f}[{c[0]:4.2f},{c[1]:4.2f}]"
                         f" {1000*(t['lag']-ref['lag']):+6.0f}[{dl[0]:+5.0f},{dl[1]:+5.0f}]")
            pr(line)
            TAB[(f1, f2, slo, shi, q)] = {g: (None if row[g] is None else
                                              {k: v for k, v in row[g].items() if k != "boot"})
                                          for g, _ in GROUPS}
            TAB[(f1, f2, slo, shi, q)]["degA"] = degA
        pr("")

# ============================================================================== SECTION B2
pr("=" * 150)
pr("SECTION B2   THE RAIL-WINDOW CONTRAST -- run where railing actually exists")
pr("=" * 150)
pr("ALL railing on ALL ELEVEN ROUTES is below 8 m/s (Section B of hsurf.py: 0.00 s at 8-15 and 0.00 s")
pr("at >=15 m/s on every route).  Torque mode rails 0.09 s in 3566 s engaged; V282 4.98 s in 4011 s;")
pr("V282old 9.11 s in 1698 s.  So the contrast is only powered on V282/V282old, and only below 8 m/s.")
pr("")
for f1, f2, W in D.BANDS:
    WS = SURF[(f1, f2, W)]
    for gname in ("V282", "V282old"):
        rks = dict(GROUPS)[gname]
        base = gather(WS, rks, 2.0, 8.0)
        if not base:
            continue
        with_r = [w for w in base if w["rail"] > 0]
        if len(with_r) < MIN_WIN:
            pr(f"  {f1:.2f}-{f2:.2f} Hz {gname:8s} 2-8 m/s: only {len(with_r)} windows contain a railed "
               f"frame -> NOT POWERED")
            continue
        # match on amplitude: restrict the no-rail comparison to the amplitude range of the rail windows
        alo, ahi = min(w["A"] for w in with_r), max(w["A"] for w in with_r)
        no_r = [w for w in base if w["rail"] == 0 and alo <= w["A"] <= ahi]
        a, b = cell(with_r), cell(no_r)
        if not a or not b:
            pr(f"  {f1:.2f}-{f2:.2f} Hz {gname:8s}: n too thin after matching")
            continue
        c = rci(a, b, "NE")
        pr(f"  {f1:.2f}-{f2:.2f} Hz {gname:8s} 2-8 m/s  RAILED-window  H {a['H']:.2f} coh {a['coh']:.2f} "
           f"NE {a['NE']:.3f} n {a['nw']:3d} medA {a['A']:.4f} |ang| {a['ang']:5.1f}   "
           f"vs CLEAN  H {b['H']:.2f} coh {b['coh']:.2f} NE {b['NE']:.3f} n {b['nw']:3d} "
           f"medA {b['A']:.4f} |ang| {b['ang']:5.1f}   NE x{a['NE']/max(b['NE'],1e-9):.2f}"
           f"[{c[0]:.2f},{c[1]:.2f}]")
pr("")

# ============================================================================== SECTION F
pr("=" * 150)
pr("SECTION F   THE SMALL-AMPLITUDE KNEE, located -- deciles of demand amplitude, >=15 m/s pooled")
pr("=" * 150)
pr("Where does |H| stop rising with amplitude?  That amplitude is the deadband/friction scale in the")
pr("goal's own metric.  Pooled over 15-40 m/s so n is thick; bins are deciles of the pooled windows.")
pr("")
for f1, f2, W in D.BANDS[:3]:
    WS = SURF[(f1, f2, W)]
    pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk]
              if 15 <= w["v"] < 40]
    if len(pooled) < 100:
        continue
    ed = [float(q) for q in np.percentile(pooled, [0, 20, 40, 60, 80, 90, 95, 100])]
    ed[0], ed[-1] = 0.0, 1e9
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz, 15-40 m/s")
    pr(f"  {'bin':>9s} {'A m/s2':>8s} {'deg':>6s} |" + "|".join(f"{g:^30s}" for g, _ in GROUPS))
    pr(f"  {'':>9s} {'':>8s} {'':>6s} |" +
       "|".join(f"{'H':>6s}{'coh':>5s}{'NE':>6s}{'lag':>7s}{'n':>5s} " for _ in GROUPS))
    for q in range(len(ed) - 1):
        lo, hi = ed[q], ed[q + 1]
        row = {g: cell(gather(WS, rks, 15.0, 40.0, lo, hi), boot=False) for g, rks in GROUPS}
        ref = row["V282"]
        if ref is None:
            continue
        degA = ref["A"] / max(ref["v"], 1.0) ** 2 * float(D.deg_per_curv(ref["v"]))
        line = f"  {f'{lo:.4f}-{min(hi,9.9):.4f}'[:9]:>9s} {ref['A']:8.4f} {degA:6.2f} |"
        for g, _ in GROUPS:
            r = row[g]
            line += ((f"{r['H']:6.2f}{r['coh']:5.2f}{'!' if r['coh'] < D.COH_MIN else ' '}"
                      f"{r['NE']:5.2f}{1000*r['lag']:+7.0f}{r['nw']:5d} ") if r else f"{'--':^30s}") + "|"
        pr(line)
    pr("")

# ============================================================================== SECTION E
pr("=" * 150)
pr("SECTION E   THE LOW-SPEED SMALL-AMPLITUDE REGIME, 2-8 m/s -- median split (n is the binding limit)")
pr("=" * 150)
pr("This is where the +0.0231 hold shortfall and the dwell-then-jump live, and where the operator says")
pr("ratchety / snapping / jerky on large angles.")
pr("")
for f1, f2, W in D.BANDS:
    WS = SURF[(f1, f2, W)]
    pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk] if 2 <= w["v"] < 8]
    if len(pooled) < 2 * MIN_WIN:
        continue
    med = float(np.median(pooled))
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz, 2-8 m/s, split at A = {med:.4f} m/s^2")
    pr(f"  {'half':>6s} {'medA':>7s} {'deg':>6s} {'|ang|':>6s} |" + "|".join(f"{g:^32s}" for g, _ in GROUPS))
    for nm, lo, hi in (("small", 0.0, med), ("large", med, 1e9)):
        row = {g: cell(gather(WS, rks, 2.0, 8.0, lo, hi)) for g, rks in GROUPS}
        ref = row["V282"]
        if ref is None:
            continue
        degA = ref["A"] / max(ref["v"], 1.0) ** 2 * float(D.deg_per_curv(ref["v"]))
        line = f"  {nm:>6s} {ref['A']:7.4f} {degA:6.2f} {ref['ang']:6.1f} |"
        for g, _ in GROUPS:
            r = row[g]
            line += ((f"{r['H']:6.2f}{r['coh']:5.2f}{'!' if r['coh'] < D.COH_MIN else ' '}"
                      f"{r['NE']:5.2f}{1000*r['lag']:+7.0f}{r['nw']:5d}   ") if r else f"{'--':^32s}") + "|"
        t = row["TQall"]
        if t and ref:
            c = rci(t, ref, "NE")
            line += f"  NE x{t['NE']/max(ref['NE'],1e-9):.2f}[{c[0]:.2f},{c[1]:.2f}]"
        pr(line)
    pr("")

with open(os.path.join(HERE, "HSURF2-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
with open(os.path.join(HERE, "hsurf2.json"), "w") as fh:
    json.dump({str(k): v for k, v in TAB.items()}, fh, indent=1, default=float)
