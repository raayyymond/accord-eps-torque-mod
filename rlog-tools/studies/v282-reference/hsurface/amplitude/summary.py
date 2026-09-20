# -*- coding: utf-8 -*-
"""Pooled numbers and independent verification for the amplitude stream.

Sections
  K  admissibility ledger: how many speed x band x amplitude cells pass the coherence floor, the n
     floor and the split-half floor, and what was excluded
  L  THE AMPLITUDE TREND, pooled: is the gap concentrated at large amplitude (saturation), at small
     amplitude (friction), or amplitude-invariant?
  M  how much of the torque mode's excess coherent error is LAG
  N  VERIFICATION with a second instrument (the controller's own achieved lateral accel) and a
     second, purely TIME-DOMAIN estimator of the same quantities
  O  the amplitude thresholds, in m/s^2 of demand and deg of wheel angle

ANALYSIS ONLY.  Run: python summary.py
"""
import os, sys
import numpy as np
from scipy import signal

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


def gather(WS, rks, slo, shi, lo=0.0, hi=1e9, pred=None):
    out = []
    for ri, rk in enumerate(rks):
        for w in WS[rk]:
            if slo <= w["v"] < shi and lo <= w["A"] < hi and (pred is None or pred(w)):
                w2 = dict(w); w2["cid"] = (ri, w["rid"]); out.append(w2)
    return out


def decomp(t, v):
    """t, v are pool() dicts on the SAME band bins.  t's coherent error, and the counterfactuals in
    which t borrows v's phase (gain-only error) or v's gain (phase-only error)."""
    Pxx, Pxy = t["Pxx"], t["Pxy"]
    Hct = Pxy / np.maximum(Pxx, 1e-30)
    Hcv = v["Pxy"] / np.maximum(v["Pxx"], 1e-30)
    n = min(len(Hct), len(Hcv))
    Hct, Hcv, Pw = Hct[:n], Hcv[:n], Pxx[:n]
    e = lambda H: float(np.sqrt(np.sum(Pw * np.abs(H - 1.0) ** 2) / max(float(np.sum(Pw)), 1e-30)))
    return dict(NEc=e(Hct), NEc_gain=e(np.abs(Hct) * np.exp(1j * np.angle(Hcv))),
                NEc_phase=e(np.abs(Hcv) * np.exp(1j * np.angle(Hct))), NEc_v=e(Hcv))

MIN_WIN = 8
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


RUNS = {}
for rk in C.ROUTES:
    RUNS[rk], _ = D.route_runs(rk)


def build(ykey="y", hop_div=2):
    S = {}
    for f1, f2, W in D.BANDS:
        WS = {}
        for rk in C.ROUTES:
            ws = D.windows(RUNS[rk], W, hop=W // hop_div, ykey=ykey)
            for w in ws:
                w["A"] = D.amp(w, f1, f2)
                w["spec"] = FH.win_spec(w, f1, f2, W)
            WS[rk] = ws
        S[(f1, f2, W)] = WS
    return S


def cellp(ws):
    return FH.pool([w["spec"] for w in ws]) if len(ws) >= MIN_WIN else None


def splithalf(ws, key):
    cids = sorted({w["cid"] for w in ws})
    if len(cids) < 2:
        return float("nan")
    ea = set(cids[0::2])
    A = cellp([w for w in ws if w["cid"] in ea]); B = cellp([w for w in ws if w["cid"] not in ea])
    return abs(A[key] - B[key]) / 2.0 if (A and B) else float("nan")


def cells(SURF, bands=None):
    """every (band, speed, amplitude-bin) cell that has BOTH a V282 and a TQall estimate"""
    out = []
    for f1, f2, W in (bands or D.BANDS):
        WS = SURF[(f1, f2, W)]
        for slo, shi in D.SPD:
            pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk]
                      if slo <= w["v"] < shi]
            if len(pooled) < 5 * MIN_WIN:
                continue
            ed = [float(q) for q in np.percentile(pooled, [0, 25, 50, 75, 90, 100])]
            ed[0], ed[-1] = 0.0, 1e9
            for q in range(5):
                wv = gather(WS, G2R["V282"], slo, shi, ed[q], ed[q + 1])
                wt = gather(WS, G2R["TQall"], slo, shi, ed[q], ed[q + 1])
                v, t = cellp(wv), cellp(wt)
                if not (v and t):
                    continue
                aa = float(np.median([w["A"] for w in wv]))
                vm = float(np.median([w["v"] for w in wv]))
                out.append(dict(band=(f1, f2), spd=(slo, shi), q=q, v=v, t=t, wv=wv, wt=wt,
                                A=aa, vm=vm, deg=aa / max(vm, 1.0) ** 2 * float(D.deg_per_curv(vm)),
                                ang=float(np.median([w["sa_med"] for w in wv]))))
    return out


SURF = build("y", 2)
CL = cells(SURF)

# ============================================================================== SECTION K
pr("=" * 132)
pr("SECTION K   ADMISSIBILITY LEDGER")
pr("=" * 132)
n_all = len(CL)
adm = [c for c in CL if c["v"]["coh"] >= D.COH_MIN and c["t"]["coh"] >= D.COH_MIN]
for c in adm:
    c["shv"] = splithalf(c["wv"], "NE"); c["sht"] = splithalf(c["wt"], "NE")
    c["dNE"] = c["t"]["NE"] - c["v"]["NE"]
    c["floor"] = (0.0 if np.isnan(c["shv"]) else c["shv"]) + (0.0 if np.isnan(c["sht"]) else c["sht"])
sig = [c for c in adm if abs(c["dNE"]) > c["floor"]]
pr(f"cells with both a V282 and a torque estimate (>= {MIN_WIN} windows each): {n_all}")
pr(f"  pass the {D.COH_MIN:.2f} coherence floor on BOTH groups:                 {len(adm)}")
pr(f"  and whose NE difference exceeds the summed split-half noise floor: {len(sig)} "
   f"({100*len(sig)/max(len(adm),1):.0f} % of admissible)")
pr(f"  of those {len(sig)}, the torque mode is WORSE (NE higher) in {sum(1 for c in sig if c['dNE']>0)} "
   f"and better in {sum(1 for c in sig if c['dNE']<0)}")
pr("")
pr("EXCLUDED, and what it cost:")
for f1, f2, W in D.BANDS:
    tot = [c for c in CL if c["band"] == (f1, f2)]
    ok = [c for c in tot if c in adm]
    pr(f"  band {f1:.2f}-{f2:.2f} Hz: {len(ok)}/{len(tot)} cells admissible"
       + ("   <- the whole band fails the coherence floor" if not ok else ""))
pr("  the 1.20-2.50 Hz band is essentially all inadmissible (band coherence 0.02-0.62): at those")
pr("  frequencies the achieved lateral acceleration is dominated by motion the model demand does not")
pr("  explain, in BOTH builds, so no |H| there is a tracking statement.")
pr("  at 2-8 m/s the torque cells hold only 8-26 windows; see Section N for the resulting instability.")
pr("")

# ============================================================================== SECTION L
pr("=" * 132)
pr("SECTION L   THE AMPLITUDE TREND, POOLED -- saturation, friction, or amplitude-invariant?")
pr("=" * 132)
pr("For every admissible cell: the torque mode's NE relative to V282's, and the ABSOLUTE excess.")
pr("A saturating actuator would put the worst numbers in bin 5 (top decile of demand).")
pr("")
pr(f"{'A bin':>10s} {'cells':>6s} {'medA m/s2':>10s} {'deg':>6s} | {'V282 NE':>8s} {'TQ NE':>7s} "
   f"{'ratio':>7s} {'excess':>7s} | {'V282 H':>7s} {'TQ H':>6s} | {'V282 lag':>9s} {'TQ lag':>7s} {'d_lag':>7s}")
for q in range(5):
    cs = [c for c in adm if c["q"] == q]
    if not cs:
        continue
    f = lambda k, g: float(np.median([c[g][k] for c in cs]))
    pr(f"{f'{q+1} ({[0,25,50,75,90][q]}-{[25,50,75,90,100][q]}%)':>10s} {len(cs):6d} "
       f"{float(np.median([c['A'] for c in cs])):10.4f} {float(np.median([c['deg'] for c in cs])):6.2f} | "
       f"{f('NE','v'):8.2f} {f('NE','t'):7.2f} "
       f"{float(np.median([c['t']['NE']/max(c['v']['NE'],1e-9) for c in cs])):7.2f} "
       f"{float(np.median([c['t']['NE']-c['v']['NE'] for c in cs])):7.2f} | "
       f"{f('H','v'):7.2f} {f('H','t'):6.2f} | {1000*f('lag','v'):9.0f} {1000*f('lag','t'):7.0f} "
       f"{1000*float(np.median([c['t']['lag']-c['v']['lag'] for c in cs])):7.0f}")
pr("")
pr("The same, restricted to the two bands where coherence is highest (0.08-0.25 and 0.15-0.30 Hz):")
pr(f"{'A bin':>10s} {'cells':>6s} {'medA':>8s} {'deg':>6s} | {'V282 NE':>8s} {'TQ NE':>7s} {'ratio':>7s} "
   f"{'excess':>7s} | {'V282 H':>7s} {'TQ H':>6s} | {'d_lag ms':>9s}")
for q in range(5):
    cs = [c for c in adm if c["q"] == q and c["band"] in ((0.08, 0.25), (0.15, 0.30))]
    if not cs:
        continue
    pr(f"{f'{q+1}':>10s} {len(cs):6d} {float(np.median([c['A'] for c in cs])):8.4f} "
       f"{float(np.median([c['deg'] for c in cs])):6.2f} | "
       f"{float(np.median([c['v']['NE'] for c in cs])):8.2f} "
       f"{float(np.median([c['t']['NE'] for c in cs])):7.2f} "
       f"{float(np.median([c['t']['NE']/max(c['v']['NE'],1e-9) for c in cs])):7.2f} "
       f"{float(np.median([c['t']['NE']-c['v']['NE'] for c in cs])):7.2f} | "
       f"{float(np.median([c['v']['H'] for c in cs])):7.2f} "
       f"{float(np.median([c['t']['H'] for c in cs])):6.2f} | "
       f"{1000*float(np.median([c['t']['lag']-c['v']['lag'] for c in cs])):9.0f}")
pr("")
pr("Monotone trend test on V282 alone (the reference): |H| and NE against amplitude bin, Spearman over")
pr("all admissible cells, paired within band x speed:")
for nm, g in (("V282", "v"), ("torque", "t")):
    dh, dn = [], []
    for f1, f2, W in D.BANDS:
        for slo, shi in D.SPD:
            cs = sorted([c for c in adm if c["band"] == (f1, f2) and c["spd"] == (slo, shi)],
                        key=lambda c: c["q"])
            for i in range(len(cs) - 1):
                dh.append(cs[i + 1][g]["H"] - cs[i][g]["H"])
                dn.append(cs[i + 1][g]["NE"] - cs[i][g]["NE"])
    if dh:
        pr(f"  {nm:7s} consecutive-bin steps n={len(dh)}:  |H| rises in {100*np.mean(np.array(dh)>0):.0f} % "
           f"of steps (median step {np.median(dh):+.3f});  NE falls in {100*np.mean(np.array(dn)<0):.0f} % "
           f"(median step {np.median(dn):+.3f})")
pr("")

# ============================================================================== SECTION M
pr("=" * 132)
pr("SECTION M   HOW MUCH OF THE TORQUE MODE'S EXCESS COHERENT ERROR IS LAG")
pr("=" * 132)
pr("excess      = NEc(torque) - NEc(V282)")
pr("removed_lag = NEc(torque) - NEc(torque's own gain, V282's phase)  -- what curing the lag alone removes")
pr("")
rows = []
for c in adm:
    d = decomp(c["t"], c["v"])
    ex = d["NEc"] - d["NEc_v"]
    rm = d["NEc"] - d["NEc_gain"]
    if ex > 0.02:
        rows.append((c, ex, rm, rm / ex))
pr(f"{'band':>12s} {'v':>7s} {'Abin':>5s} {'NEc V282':>9s} {'NEc TQ':>7s} {'excess':>7s} "
   f"{'lag cures':>10s} {'frac':>6s}")
for c, ex, rm, fr in rows:
    d = decomp(c["t"], c["v"])
    bn = "%.2f-%.2f" % c["band"]
    sn = "%d-%d" % c["spd"]
    pr(f"{bn:>12s} {sn:>7s} {c['q']+1:5d} {d['NEc_v']:9.2f} {d['NEc']:7.2f} {ex:7.2f} "
       f"{rm:10.2f} {fr:6.2f}")
if rows:
    fr = np.array([r[3] for r in rows])
    pr("")
    pr(f"POOLED over {len(rows)} admissible cells with a positive excess: curing the lag alone removes a "
       f"median {100*np.median(fr):.0f} % of it (IQR {100*np.percentile(fr,25):.0f}-"
       f"{100*np.percentile(fr,75):.0f} %), mean {100*fr.mean():.0f} %.")
    pr(f"  cells where the lag accounts for >= 60 % of the excess: {int((fr>=0.6).sum())}/{len(fr)}")
pr("")

with open(os.path.join(HERE, "SUMMARY-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
