# -*- coding: utf-8 -*-
"""|H| vs DEMAND AMPLITUDE at matched speed and frequency -- the describing function of the
model-desired -> achieved lateral-acceleration transfer, measured on logged drives.

This is MEASUREMENT: x = logged model reference, y = logged achieved lateral accel.  No plant model,
no simulation, no open-loop prediction.

Sections
  0  positive controls + admissibility settings
  1  the surface: speed x band x amplitude quartile, V282 vs V282old vs torque revs
  2  the SHAPE test: does |H|/|H|_V282 droop at LARGE amplitude (saturation) or SMALL (friction)?
  3  amplitude thresholds, in m/s^2 of demand AND deg of desired wheel angle
ANALYSIS ONLY.  Run: python surface.py
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
NQ = 4                      # amplitude quartiles
MIN_WIN = 8                 # a cell needs at least this many windows
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


# ---------------------------------------------------------------------------------- section 0
pr("=" * 126)
pr("SECTION 0   POSITIVE CONTROLS AND ADMISSIBILITY")
pr("=" * 126)
pr(C._self_test())
pr(D._self_test())
pr(f"coherence floor {D.COH_MIN:.2f} | split-half noise floor reported per cell (runs split by parity)")
pr(f"run-cluster bootstrap 95% CI (resample RUNS, not windows: 50%-overlapped windows in a run are "
   f"not independent) | min {MIN_WIN} windows per cell")
pr("")

# load every route's usable runs once (~tens of MB total)
RUNS = {}
LAF = {}
for rk in C.ROUTES:
    RUNS[rk], LAF[rk] = D.route_runs(rk)
pr("usable runs loaded (engaged AND latActive AND not steeringPressed, v >= 1.5 m/s):")
for rk, meta in C.ROUTES.items():
    tot = sum(len(r["x"]) for r in RUNS[rk]) / D.FS
    pr(f"   {rk:24s} {meta['group']:8s} runs {len(RUNS[rk]):4d}  {tot:7.0f} s   LAF(from log) {LAF[rk]:6.3f}")
pr("")

rng = np.random.default_rng(11)
RESULT = {}
EQ_CHECKED = False

for f1, f2, W in D.BANDS:
    # ---- windows + amplitude, per route
    WS = {}
    for rk in C.ROUTES:
        ws = D.windows(RUNS[rk], W)
        for w in ws:
            w["A"] = D.amp(w, f1, f2)
            w["spec"] = FH.win_spec(w, f1, f2, W)
        WS[rk] = ws
    if not EQ_CHECKED:
        sample = WS["0000006c--2bc842dbac"][:25]
        a, b, ca, cb = FH.assert_equivalent(sample, f1, f2, W)
        pr(f"fastH == shared band_H on 25 real windows: H {a:.10f} vs {b:.10f}, coh {ca:.10f} vs {cb:.10f}")
        pr("")
        EQ_CHECKED = True

    pr("=" * 126)
    pr(f"SECTION 1   BAND {f1:.2f}-{f2:.2f} Hz   (window {W/D.FS:.2f} s, hop 50%, "
       f"{int(np.floor(f2*W/D.FS)) - int(np.ceil(f1*W/D.FS)) + 1} Welch bins)")
    pr("=" * 126)

    for slo, shi in D.SPD:
        # pooled amplitude quartile edges across ALL groups in this speed cell -> matched bins
        pooled = []
        for gname, rks in GROUPS:
            if gname == "TQall":
                continue
            for rk in rks:
                pooled += [w["A"] for w in WS[rk] if slo <= w["v"] < shi]
        if len(pooled) < 4 * MIN_WIN:
            pr(f"--- v {slo}-{shi} m/s: only {len(pooled)} windows pooled -> SKIPPED (n too thin)")
            continue
        edges = [0.0] + [float(q) for q in np.percentile(pooled, [25, 50, 75])] + [1e9]
        pr(f"--- v {slo}-{shi} m/s   amplitude quartile edges (RMS of band-passed demand, m/s^2): "
           + "  ".join(f"{e:.4f}" for e in edges[1:-1]))
        hdr = f"{'A bin':>7s} {'medA':>7s} {'pkA':>6s} {'deg':>6s} {'|ang|':>6s}"
        for gname, _ in GROUPS:
            hdr += f" | {gname:>7s} {'coh':>4s} {'sh':>5s} {'n':>4s}"
        pr(hdr + "   ratio TQ64/V282 [CI]        TQall/V282 [CI]")
        for q in range(NQ):
            lo, hi = edges[q], edges[q + 1]
            row = {}
            for gname, rks in GROUPS:
                ws = [w for rk in rks for w in WS[rk] if slo <= w["v"] < shi and lo <= w["A"] < hi]
                # rid must be unique per (route, run) for the cluster bootstrap
                for rk in rks:
                    pass
                ws2 = []
                for ri, rk in enumerate(rks):
                    for w in WS[rk]:
                        if slo <= w["v"] < shi and lo <= w["A"] < hi:
                            w2 = dict(w); w2["cid"] = (ri, w["rid"]); ws2.append(w2)
                ws = ws2
                if len(ws) < MIN_WIN:
                    row[gname] = None
                    continue
                res = FH.pool([w["spec"] for w in ws])
                cids = sorted({w["cid"] for w in ws})
                ea = set(cids[0::2])
                A = FH.pool([w["spec"] for w in ws if w["cid"] in ea])
                B = FH.pool([w["spec"] for w in ws if w["cid"] not in ea])
                sh = abs(A["H"] - B["H"]) / 2.0 if (A and B and len(cids) > 1) else float("nan")
                by = {}
                for w in ws:
                    by.setdefault(w["cid"], []).append(w["spec"])
                bv = []
                if len(by) >= 2:
                    keys = list(by)
                    for _ in range(300):
                        pick = rng.choice(len(keys), len(keys), replace=True)
                        r = FH.pool([s for k in pick for s in by[keys[k]]])
                        if r:
                            bv.append(r["H"])
                ci = (float(np.percentile(bv, 2.5)), float(np.percentile(bv, 97.5))) if len(bv) > 50 \
                    else (float("nan"), float("nan"))
                row[gname] = dict(H=res["H"], coh=res["coh"], n=len(ws), sh=sh, ci=ci,
                                  A=float(np.median([w["A"] for w in ws])),
                                  Apk=float(np.percentile([w["A"] for w in ws], 95)),
                                  v=float(np.median([w["v"] for w in ws])),
                                  ang=float(np.median([w["sa_med"] for w in ws])),
                                  rail=float(np.mean([w["rail"] for w in ws])),
                                  bootv=bv)
            ref = row.get("V282")
            if ref is None:
                pr(f"{q+1:>7d}   -- no V282 reference in this cell --")
                continue
            degA = ref["A"] / max(ref["v"], 1.0) ** 2 * float(D.deg_per_curv(ref["v"]))
            line = f"{q+1:>7d} {ref['A']:7.4f} {ref['A']*1.414:6.3f} {degA:6.2f} {ref['ang']:6.1f}"
            for gname, _ in GROUPS:
                r = row.get(gname)
                line += (f" | {r['H']:7.3f} {r['coh']:4.2f} {r['sh']:5.3f} {r['n']:4d}" if r
                         else f" | {'--':>7s} {'':4s} {'':5s} {'':4s}")
            for gname in ("TQ64", "TQall"):
                r = row.get(gname)
                if r and ref and len(r["bootv"]) > 50 and len(ref["bootv"]) > 50:
                    rt = np.array(r["bootv"][:len(ref["bootv"])]) / np.array(ref["bootv"][:len(r["bootv"])])
                    line += f"   x{r['H']/ref['H']:5.2f}[{np.percentile(rt,2.5):4.2f},{np.percentile(rt,97.5):4.2f}]"
                else:
                    line += f"   {'--':>16s}"
            pr(line)
            RESULT[(f1, f2, slo, shi, q)] = {g: (None if row.get(g) is None else
                                                 {k: v for k, v in row[g].items() if k != "bootv"})
                                             for g, _ in GROUPS}
            RESULT[(f1, f2, slo, shi, q)]["edges"] = (lo, hi)
            RESULT[(f1, f2, slo, shi, q)]["degA"] = degA
        pr("")
    del WS

# ---------------------------------------------------------------------------------- section 2
pr("=" * 126)
pr("SECTION 2   THE SHAPE TEST -- saturation droops at LARGE amplitude, friction at SMALL")
pr("=" * 126)
pr("Per band x speed: |H| of each group across amplitude quartiles Q1..Q4, and the trend Q4/Q1.")
pr("A LARGE-amplitude saturation gives Q4/Q1 < 1; a friction/deadband gives Q4/Q1 > 1.")
pr("")
pr(f"{'band':>12s} {'v':>8s} " + " ".join(f"{g:>26s}" for g, _ in GROUPS))
for f1, f2, W in D.BANDS:
    for slo, shi in D.SPD:
        cells = [RESULT.get((f1, f2, slo, shi, q)) for q in range(NQ)]
        if not any(cells):
            continue
        line = f"{f'{f1:.2f}-{f2:.2f}':>12s} {f'{slo}-{shi}':>8s} "
        for g, _ in GROUPS:
            hs = [None if c is None or c.get(g) is None else c[g]["H"] for c in cells]
            s = " ".join(f"{h:5.2f}" if h is not None else "   . " for h in hs)
            t = (hs[3] / hs[0]) if (hs[0] and hs[3]) else float("nan")
            line += f" {s} Q4/Q1 {t:4.2f}"
        pr(line)
pr("")

with open(os.path.join(HERE, "SURFACE-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
with open(os.path.join(HERE, "surface.json"), "w") as fh:
    json.dump({f"{k}": v for k, v in RESULT.items()}, fh, indent=1, default=float)
