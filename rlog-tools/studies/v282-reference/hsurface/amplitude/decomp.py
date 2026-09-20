# -*- coding: utf-8 -*-
"""What KIND of gap is it?  Split the torque-mode tracking error into GAIN, PHASE and INCOHERENT parts,
per amplitude bin, and run a properly matched rail contrast.

The decomposition is arithmetic on the measured cross spectra, per frequency bin, inside a cell:
    Hc = Pxy/Pxx            the measured complex closed-loop transfer, demand -> achieved
    NEc^2 = sum Pxx |Hc-1|^2 / sum Pxx            coherent error (gain AND phase together)
  counterfactual A: give the torque mode V282's PHASE, keep its own gain  -> NEc_gainonly
  counterfactual B: give the torque mode V282's GAIN,  keep its own phase -> NEc_phaseonly
Both counterfactuals are bin-by-bin, on the SAME band bins, so the two cells are directly comparable.
This is bookkeeping on measured spectra, NOT a model or a prediction of what a re-tuned drive would do.

Sections
  G  gain / phase / incoherent decomposition by amplitude bin
  H  V282old as the FORK-ONLY control: how much lag can a fork change alone move?
  I  matched rail contrast (amplitude AND wheel angle matched, 1:1 nearest neighbour)
  J  low-speed 2-8 m/s at finer amplitude resolution (75 % window overlap to lift n)

ANALYSIS ONLY.  Run: python decomp.py
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
LOG = []
rng = np.random.default_rng(3)


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


def decomp(t, v):
    """t, v are pool() dicts on the SAME band bins.  Returns t's coherent error, and the two
    counterfactuals in which t borrows v's phase (gain-only error) or v's gain (phase-only error)."""
    Pxx, Pxy = t["Pxx"], t["Pxy"]
    Hct = Pxy / np.maximum(Pxx, 1e-30)
    Hcv = v["Pxy"] / np.maximum(v["Pxx"], 1e-30)
    den = float(np.sum(Pxx))
    n = min(len(Hct), len(Hcv))
    Hct, Hcv, Pw = Hct[:n], Hcv[:n], Pxx[:n]
    e = lambda H: float(np.sqrt(np.sum(Pw * np.abs(H - 1.0) ** 2) / max(float(np.sum(Pw)), 1e-30)))
    gain_only = np.abs(Hct) * np.exp(1j * np.angle(Hcv))    # t's gain, v's phase
    phase_only = np.abs(Hcv) * np.exp(1j * np.angle(Hct))   # v's gain, t's phase
    return dict(NEc=e(Hct), NEc_gain=e(gain_only), NEc_phase=e(phase_only), NEc_v=e(Hcv))


def gather(WS, rks, slo, shi, lo=0.0, hi=1e9, pred=None):
    out = []
    for ri, rk in enumerate(rks):
        for w in WS[rk]:
            if slo <= w["v"] < shi and lo <= w["A"] < hi and (pred is None or pred(w)):
                w2 = dict(w); w2["cid"] = (ri, w["rid"]); out.append(w2)
    return out


def cellp(ws):
    return FH.pool([w["spec"] for w in ws]) if len(ws) >= MIN_WIN else None


RUNS = {}
for rk in C.ROUTES:
    RUNS[rk], _ = D.route_runs(rk)

SURF, SURF4 = {}, {}
for f1, f2, W in D.BANDS:
    for hop, store in ((W // 2, SURF), (W // 4, SURF4)):
        WS = {}
        for rk in C.ROUTES:
            ws = D.windows(RUNS[rk], W, hop=hop)
            for w in ws:
                w["A"] = D.amp(w, f1, f2)
                w["spec"] = FH.win_spec(w, f1, f2, W)
            WS[rk] = ws
        store[(f1, f2, W)] = WS

# ============================================================================== SECTION G
pr("=" * 146)
pr("SECTION G   GAIN vs PHASE vs INCOHERENT -- what the torque mode's extra tracking error is MADE OF")
pr("=" * 146)
pr("NE  = total normalised in-band tracking error, sqrt(sum|achieved-desired|^2 / sum|desired|^2)")
pr("NEc = its coherent part (the measured transfer being the wrong gain and/or phase)")
pr("NEi = its incoherent part (achieved motion the demand does not explain);  NE^2 = NEc^2 + NEi^2")
pr("NEc(gain only)  = the torque mode's own GAIN but V282's PHASE, bin by bin -> what would remain if")
pr("                  the lag were cured and nothing else changed")
pr("NEc(phase only) = V282's GAIN but the torque mode's own PHASE -> what the lag alone costs")
pr("Cells below the 0.50 coherence floor are marked ! and are not admissible.")
pr("")
for f1, f2, W in D.BANDS[:4]:
    WS = SURF[(f1, f2, W)]
    for slo, shi in D.SPD:
        pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk]
                  if slo <= w["v"] < shi]
        if len(pooled) < 5 * MIN_WIN:
            continue
        ed = [float(q) for q in np.percentile(pooled, [0, 25, 50, 75, 90, 100])]
        ed[0], ed[-1] = 0.0, 1e9
        head = False
        for q in range(5):
            lo, hi = ed[q], ed[q + 1]
            vv = cellp(gather(WS, G2R["V282"], slo, shi, lo, hi))
            tt = cellp(gather(WS, G2R["TQall"], slo, shi, lo, hi))
            if not (vv and tt):
                continue
            dd = decomp(tt, vv)
            if not head:
                pr(f"BAND {f1:.2f}-{f2:.2f} Hz   v {slo}-{shi} m/s")
                pr(f"  {'Abin':>6s} {'medA':>7s} {'deg':>6s} | {'V282':>26s} | {'TQall':>26s} | "
                   f"{'TQ if lag cured':>15s} {'lag alone costs':>15s}")
                pr(f"  {'':>6s} {'':>7s} {'':>6s} | {'H':>5s}{'NE':>6s}{'NEc':>6s}{'NEi':>5s}{'lag':>7s} | "
                   f"{'H':>5s}{'NE':>6s}{'NEc':>6s}{'NEi':>5s}{'lag':>7s} | {'NEc':>15s} {'NEc':>15s}")
                head = True
            a = float(np.median([w["A"] for w in gather(WS, G2R["V282"], slo, shi, lo, hi)]))
            vm = float(np.median([w["v"] for w in gather(WS, G2R["V282"], slo, shi, lo, hi)]))
            degA = a / max(vm, 1.0) ** 2 * float(D.deg_per_curv(vm))
            mk = lambda r: (f"{r['H']:5.2f}{r['NE']:6.2f}{r['NEc']:6.2f}{r['NEi']:5.2f}"
                            f"{1000*r['lag']:+7.0f}" + ("!" if r["coh"] < D.COH_MIN else " "))
            pr(f"  {f'{q+1}':>6s} {a:7.4f} {degA:6.2f} | {mk(vv):>26s} | {mk(tt):>26s} | "
               f"{dd['NEc_gain']:15.2f} {dd['NEc_phase']:15.2f}")
        if head:
            pr("")

# ============================================================================== SECTION H
pr("=" * 146)
pr("SECTION H   THE FORK-ONLY CONTROL -- V282old is the SAME EPS with an older fork")
pr("=" * 146)
pr("If a fork change alone can move the in-band lag by as much as the torque build does, the lag cannot")
pr("be attributed to the EPS mode.  Lag, ms, pooled over all amplitudes in the cell.")
pr("")
pr(f"{'band':>12s} {'v':>8s} | {'V282':>8s} {'V282old':>8s} {'d(fork only)':>13s} | "
   f"{'TQ64':>8s} {'TQall':>8s} {'d(torque)':>10s} | {'torque / fork-only':>19s}")
for f1, f2, W in D.BANDS[:4]:
    WS = SURF[(f1, f2, W)]
    for slo, shi in D.SPD:
        rows = {g: cellp(gather(WS, rks, slo, shi)) for g, rks in GROUPS}
        if not (rows["V282"] and rows["V282old"] and rows["TQall"]):
            continue
        L = {g: (1000 * rows[g]["lag"] if rows[g] else float("nan")) for g in rows}
        dfork = L["V282old"] - L["V282"]
        dtq = L["TQall"] - L["V282"]
        pr(f"{f'{f1:.2f}-{f2:.2f}':>12s} {f'{slo}-{shi}':>8s} | {L['V282']:+8.0f} {L['V282old']:+8.0f} "
           f"{dfork:+13.0f} | {L['TQ64']:+8.0f} {L['TQall']:+8.0f} {dtq:+10.0f} | "
           f"{(dtq/dfork if abs(dfork) > 5 else float('nan')):19.1f}")
pr("")

# ============================================================================== SECTION I
pr("=" * 146)
pr("SECTION I   THE RAIL CONTRAST, PROPERLY MATCHED (1:1 nearest neighbour on amplitude AND wheel angle)")
pr("=" * 146)
pr("The earlier crude contrast was confounded: railed windows sit at |wheel angle| 16-85 deg and 2-4x the")
pr("demand amplitude of the clean pool, so any difference was an amplitude effect.  Here each railed")
pr("window is paired with the nearest unrailed window of the SAME group with |log A| and |log |ang|| both")
pr("within 0.35 (i.e. within ~x1.42), each clean window used once.")
pr("")
for f1, f2, W in D.BANDS:
    WS = SURF[(f1, f2, W)]
    for gname in ("V282", "V282old", "TQall"):
        base = gather(WS, G2R[gname], 2.0, 8.0)
        rail = [w for w in base if w["rail"] > 0]
        clean = [w for w in base if w["rail"] == 0]
        if len(rail) < MIN_WIN:
            continue
        used, pa, pb = set(), [], []
        for w in rail:
            best, bd = None, 9e9
            for j, c in enumerate(clean):
                if j in used or c["A"] <= 0 or w["A"] <= 0:
                    continue
                d1 = abs(np.log(max(c["A"], 1e-9) / max(w["A"], 1e-9)))
                d2 = abs(np.log(max(c["sa_med"], 0.05) / max(w["sa_med"], 0.05)))
                if d1 < 0.35 and d2 < 0.35 and d1 + d2 < bd:
                    best, bd = j, d1 + d2
            if best is not None:
                used.add(best); pa.append(w); pb.append(clean[best])
        if len(pa) < MIN_WIN:
            pr(f"  {f1:.2f}-{f2:.2f} Hz {gname:8s}: {len(rail)} railed windows, only {len(pa)} could be "
               f"matched -> NOT POWERED")
            continue
        a, b = cellp(pa), cellp(pb)
        pr(f"  {f1:.2f}-{f2:.2f} Hz {gname:8s} n={len(pa)} pairs  RAILED H {a['H']:.2f} coh {a['coh']:.2f} "
           f"NE {a['NE']:.2f} lag {1000*a['lag']:+.0f} | MATCHED-CLEAN H {b['H']:.2f} coh {b['coh']:.2f} "
           f"NE {b['NE']:.2f} lag {1000*b['lag']:+.0f} | medA {np.median([w['A'] for w in pa]):.4f} vs "
           f"{np.median([w['A'] for w in pb]):.4f}  |ang| {np.median([w['sa_med'] for w in pa]):.1f} vs "
           f"{np.median([w['sa_med'] for w in pb]):.1f}  -> NE x{a['NE']/max(b['NE'],1e-9):.2f}, "
           f"H x{a['H']/max(b['H'],1e-9):.2f}")
pr("")

# ============================================================================== SECTION J
pr("=" * 146)
pr("SECTION J   2-8 m/s AT FINER AMPLITUDE RESOLUTION (75 % window overlap; clusters are still RUNS)")
pr("=" * 146)
pr("This is the low-speed friction regime: the +0.0231 hold shortfall, the dwell-then-jump, and the")
pr("operator's 'ratchety / snapping'.  A friction/deadband mechanism must show a droop at SMALL amplitude.")
pr("")
for f1, f2, W in D.BANDS:
    WS = SURF4[(f1, f2, W)]
    pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk] if 2 <= w["v"] < 8]
    if len(pooled) < 3 * MIN_WIN:
        continue
    ed = [float(q) for q in np.percentile(pooled, [0, 33, 67, 90, 100])]
    ed[0], ed[-1] = 0.0, 1e9
    pr(f"BAND {f1:.2f}-{f2:.2f} Hz, 2-8 m/s")
    pr(f"  {'bin':>7s} {'medA':>7s} {'deg':>6s} {'|ang|':>6s} |" +
       "|".join(f"{g:^30s}" for g, _ in GROUPS))
    pr(f"  {'':>7s} {'':>7s} {'':>6s} {'':>6s} |" +
       "|".join(f"{'H':>6s}{'coh':>5s}{'NE':>6s}{'lag':>7s}{'n':>5s} " for _ in GROUPS))
    for q in range(len(ed) - 1):
        lo, hi = ed[q], ed[q + 1]
        row = {g: cellp(gather(WS, rks, 2.0, 8.0, lo, hi)) for g, rks in GROUPS}
        ws0 = gather(WS, G2R["V282"], 2.0, 8.0, lo, hi)
        if not row["V282"] or not ws0:
            continue
        a = float(np.median([w["A"] for w in ws0])); vm = float(np.median([w["v"] for w in ws0]))
        degA = a / max(vm, 1.0) ** 2 * float(D.deg_per_curv(vm))
        line = f"  {f'{q+1}':>7s} {a:7.4f} {degA:6.2f} {float(np.median([w['sa_med'] for w in ws0])):6.1f} |"
        for g, _ in GROUPS:
            r = row[g]
            line += ((f"{r['H']:6.2f}{r['coh']:5.2f}{'!' if r['coh'] < D.COH_MIN else ' '}"
                      f"{r['NE']:5.2f}{1000*r['lag']:+7.0f}{r['n']:5d} ") if r else f"{'--':^30s}") + "|"
        pr(line)
    pr("")

with open(os.path.join(HERE, "DECOMP-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
