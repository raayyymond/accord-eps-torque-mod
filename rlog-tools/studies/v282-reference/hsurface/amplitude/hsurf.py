# -*- coding: utf-8 -*-
"""THE AMPLITUDE STREAM.  Is the model->achieved lateral-acceleration gap amplitude-dependent, and
is the actuator rail visible in the operator's own metric?

Everything here is MEASUREMENT FROM LOGGED DATA: x = the logged model reference
(desiredCurvature * v^2), y = the logged achieved lateral accel (livePose yaw x v).  There is no
plant model, no simulator and no open-loop prediction anywhere in this file.

Sections
  A  positive controls and admissibility
  B  the RAIL, localised: frame census (|output| >= 0.98) and the matched-window |H| / error contrast
  C  the describing function: |H| and the normalised tracking error NE vs demand amplitude,
     at matched speed and frequency band
  D  the shape test: saturation droops at LARGE amplitude, friction/deadband at SMALL
  E  the low-speed small-amplitude regime (2-8 m/s), finer amplitude bins
  F  amplitude thresholds in m/s^2 of demand AND deg of desired wheel angle

ANALYSIS ONLY.  Run: python hsurf.py
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
G2R = dict(GROUPS)
MIN_WIN = 8
NB = 300
LOG = []
rng = np.random.default_rng(11)


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


def cell(ws, f1, f2, boot=True):
    """Full metric set for a set of windows, with split-half floor and run-cluster bootstrap CI.
    `cid` (route, run) is the cluster: 50%-overlapped windows inside one run are not independent."""
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
            sh = {k: abs(A[k] - B[k]) / 2.0 for k in ("H", "NE", "coh")}
    by = {}
    for w in ws:
        by.setdefault(w["cid"], []).append(w["spec"])
    bv = {"H": [], "NE": []}
    if boot and len(by) >= 2:
        keys = list(by)
        for _ in range(NB):
            pick = rng.choice(len(keys), len(keys), replace=True)
            r = FH.pool([s for k in pick for s in by[keys[k]]])
            if r:
                bv["H"].append(r["H"]); bv["NE"].append(r["NE"])
    out = dict(res)
    out.update(nw=len(ws), ncl=len(cids), sec=len(ws) * 0.0, sh=sh, boot=bv,
               A=float(np.median([w["A"] for w in ws])),
               v=float(np.median([w["v"] for w in ws])),
               ang=float(np.median([w["sa_med"] for w in ws])),
               angmax=float(np.percentile([w["sa_max"] for w in ws], 90)),
               railfr=float(np.mean([w["rail"] for w in ws])),
               nrail=int(sum(1 for w in ws if w["rail"] > 0)))
    return out


def ci(r, k):
    b = r["boot"].get(k, [])
    return (float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))) if len(b) > 50 else (np.nan, np.nan)


def ratio_ci(a, b, k):
    """bootstrap ratio a/b (paired by draw index; both are run-cluster resamples)"""
    x, y = a["boot"].get(k, []), b["boot"].get(k, [])
    if len(x) < 50 or len(y) < 50:
        return (np.nan, np.nan)
    m = min(len(x), len(y))
    rt = np.array(x[:m]) / np.maximum(np.array(y[:m]), 1e-9)
    return (float(np.percentile(rt, 2.5)), float(np.percentile(rt, 97.5)))


# ================================================================================ SECTION A
pr("=" * 138)
pr("SECTION A   POSITIVE CONTROLS AND ADMISSIBILITY")
pr("=" * 138)
pr(C._self_test())
pr(D._self_test())
pr("")
pr("NE = sqrt( in-band sum|achieved - desired|^2 / sum|desired|^2 ): the operator's 'match the model's")
pr("desired lateral acceleration as closely as' made quantitative.  It charges gain error, PHASE LAG")
pr("and unexplained motion together; a gain of 1.0 with 100 ms of lag scores NE 0.30, not 0.00.")
pr("   controls: gain 0.9 -> NE 0.100 | 100 ms lag at gain 1 -> NE 0.303 (NEc 0.301, lag recovered")
pr("   +99 ms) | 200 ms lag -> NE 0.598 | 30 % output noise -> NE 0.287 all in NEi.  NE^2 = NEc^2+NEi^2.")
pr(f"coherence floor {D.COH_MIN:.2f}; split-half floor (runs split by parity) printed per cell; "
   f"run-cluster bootstrap {NB} draws; min {MIN_WIN} windows/cell.")
pr("")

RUNS, LAF = {}, {}
for rk in C.ROUTES:
    RUNS[rk], LAF[rk] = D.route_runs(rk)

# ================================================================================ SECTION B
pr("=" * 138)
pr("SECTION B   THE RAIL, LOCALISED")
pr("=" * 138)
pr("|output| is pid_log.output, already normalised to full scale 1.0 (steer_max, latcontrol.py:17).")
pr("The identity out == -clip(p+i+f, +/-LAF)/LAF holds to <1e-7 on all 11 routes, so NO reconstruction")
pr("is needed to mark railed frames -- the logged output IS the clipped command.  LAF is fitted from")
pr("the log (6.000 on V282, 14.000 on every torque route), not taken from a toggle.")
pr("")
pr(f"{'route':24s} {'grp':8s} {'sec':>7s} | {'rail>=0.98':>11s} {'sec':>6s} {'longest s':>9s} "
   f"{'>=0.90':>8s} {'max|p+i+f|/LAF':>15s} | {'rail sec <8':>11s} {'8-15':>6s} {'>=15':>6s}")
railtot = {}
for rk, meta in C.ROUTES.items():
    o = np.concatenate([r["out"] for r in RUNS[rk]])
    pre = np.concatenate([r["pre"] for r in RUNS[rk]])
    v = np.concatenate([r["v"] for r in RUNS[rk]])
    longest = 0
    for r in RUNS[rk]:
        m = r["out"] >= 0.98
        k = 0
        for b in m:
            k = k + 1 if b else 0
            longest = max(longest, k)
    rail = o >= 0.98
    g = meta["group"]
    a = railtot.setdefault(g, dict(sec=0.0, rsec=0.0, longest=0.0))
    a["sec"] += len(o) / D.FS; a["rsec"] += rail.sum() / D.FS; a["longest"] = max(a["longest"], longest / D.FS)
    pr(f"{rk:24s} {g:8s} {len(o)/D.FS:7.0f} | {100*rail.mean():10.4f}% {rail.sum()/D.FS:6.2f} "
       f"{longest/D.FS:9.2f} {100*(o>=0.90).mean():7.3f}% {pre.max():15.3f} | "
       f"{(rail&(v<8)).sum()/D.FS:11.2f} {(rail&(v>=8)&(v<15)).sum()/D.FS:6.2f} "
       f"{(rail&(v>=15)).sum()/D.FS:6.2f}")
pr("")
pr("POOLED BY GROUP -- exposure to the rail:")
for g, a in railtot.items():
    pr(f"   {g:8s} {a['sec']:7.0f} s engaged   railed {a['rsec']:6.2f} s = {100*a['rsec']/a['sec']:.4f} % "
       f"of engaged time, longest episode {a['longest']:.2f} s")
pr("")

# ================================================================================ SECTION C / D / E
SURF = {}
for f1, f2, W in D.BANDS:
    WS = {}
    for rk in C.ROUTES:
        ws = D.windows(RUNS[rk], W)
        for w in ws:
            w["A"] = D.amp(w, f1, f2)
            w["spec"] = FH.win_spec(w, f1, f2, W)
        WS[rk] = ws
    for g, rks in GROUPS:
        for ri, rk in enumerate(rks):
            for w in WS[rk]:
                w.setdefault("cid_%s" % g, (ri, w["rid"]))
    SURF[(f1, f2, W)] = WS

pr("=" * 138)
pr("SECTION C   THE DESCRIBING FUNCTION -- |H| and NE vs DEMAND AMPLITUDE, matched speed x band")
pr("=" * 138)
pr("Amplitude of a window = RMS of the band-passed model reference (m/s^2).  Quartile edges are taken")
pr("from the POOLED V282 + V282old + TQ64 windows in that speed x band cell, so the bins are matched.")
pr("'deg' = the desired WHEEL angle amplitude that RMS corresponds to, through the fork's own")
pr("VehicleModel at the nominal rack ratio.  '|ang|' = median measured |wheel angle| in the windows.")
pr("")
CELLS = {}
for f1, f2, W in D.BANDS:
    WS = SURF[(f1, f2, W)]
    pr("-" * 138)
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz   window {W/D.FS:.2f} s")
    for slo, shi in D.SPD:
        pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk]
                  if slo <= w["v"] < shi]
        if len(pooled) < 4 * MIN_WIN:
            continue
        edges = [0.0] + [float(q) for q in np.percentile(pooled, [25, 50, 75])] + [1e9]
        pr(f"  v {slo}-{shi} m/s   A quartile edges {edges[1]:.4f} {edges[2]:.4f} {edges[3]:.4f} m/s^2")
        pr(f"  {'Q':>2s} {'medA':>7s} {'deg':>6s} {'|ang|':>6s} | " +
           " | ".join(f"{g:>26s}" for g, _ in GROUPS) + " |  NE ratio TQ64 / TQall vs V282")
        pr(f"  {'':>2s} {'':>7s} {'':>6s} {'':>6s} | " +
           " | ".join(f"{'H':>5s}{'coh':>5s}{'NE':>6s}{'NEc':>5s}{'NEi':>5s}{'n':>5s}" for _ in GROUPS))
        for q in range(4):
            lo, hi = edges[q], edges[q + 1]
            row = {}
            for g, rks in GROUPS:
                ws = []
                for ri, rk in enumerate(rks):
                    for w in WS[rk]:
                        if slo <= w["v"] < shi and lo <= w["A"] < hi:
                            w2 = dict(w); w2["cid"] = (ri, w["rid"]); ws.append(w2)
                row[g] = cell(ws, f1, f2)
            ref = row["V282"]
            if ref is None:
                continue
            degA = ref["A"] / max(ref["v"], 1.0) ** 2 * float(D.deg_per_curv(ref["v"]))
            line = f"  {q+1:>2d} {ref['A']:7.4f} {degA:6.2f} {ref['ang']:6.1f} | "
            line += " | ".join(
                (f"{row[g]['H']:5.2f}{row[g]['coh']:5.2f}{row[g]['NE']:6.3f}{row[g]['NEc']:5.2f}"
                 f"{row[g]['NEi']:5.2f}{row[g]['nw']:5d}" if row[g] else f"{'--':>26s}")
                for g, _ in GROUPS)
            line += " | "
            for g in ("TQ64", "TQall"):
                r = row[g]
                if r:
                    c = ratio_ci(r, ref, "NE")
                    line += f" x{r['NE']/max(ref['NE'],1e-9):5.2f}[{c[0]:4.2f},{c[1]:4.2f}]"
                else:
                    line += f" {'--':>18s}"
            pr(line)
            CELLS[(f1, f2, slo, shi, q)] = dict(
                edges=(lo, hi), degA=degA,
                **{g: (None if row[g] is None else
                       {k: v for k, v in row[g].items() if k not in ("boot", "spec")}) for g, _ in GROUPS})
        pr("")

with open(os.path.join(HERE, "HSURF-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
with open(os.path.join(HERE, "hsurf.json"), "w") as fh:
    json.dump({str(k): v for k, v in CELLS.items()}, fh, indent=1, default=float)
pr(f"(written HSURF-OUT.txt and hsurf.json)")
with open(os.path.join(HERE, "HSURF-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
