"""Adversarial verification of 'turn-texture-2hz-self-generated', CONFOUND lens.

Uses the already-computed per-event rows in s3_accel/out/s3_pass2.json (each row already carries
hfnp_build/hold/unwind/ret for one turn event on one route) -- no heavy npz reload needed for this part.

Checks:
 (1) Leave-one-route-out: does the TQ-V282 stratified (speed x peak-angle) hfnp difference survive
     dropping route 0000006c--2bc842dbac (the 207 s / 16-event route that dominates the V282 group)?
     Also drop each other route in turn.
 (2) Per-torque-fork-version breakdown (T64 / T64B / T5 / T4 kept separate, not pooled as 'TQ') --
     is the elevated texture present in EVERY torque fork build, or driven by one?
 (3) Fork-config confound within the SAME firmware: V282 (LAF 6.0) vs V282old (LAF 2.1-4.0) hfnp --
     if these two, on identical EPS firmware but different fork lateral config, already agree, that
     argues the texture tracks firmware/EPS architecture, not fork tuning.
 (4) Stricter exact speed x peak-angle bin matching (not weighted pooling): report per-cell (vb,pb)
     medians for V282 and TQ side by side, so a reader can see whether any single cell drives the result.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T

OUT_IN = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/s3_pass2.json'
OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__turntexture2__confound/'

D = json.load(open(OUT_IN))
rows = D["rows"]
for r in rows:
    r["vb"], r["pb"] = T.strata(r)

rng = np.random.default_rng(11)


def strat_diff(A, B, key, NB=2000):
    """Same stratified (speed x peak-angle) weighted mean-difference estimator as s3_pass2_stats.strat,
    reimplemented independently here (not imported) so a bug in the original isn't inherited silently."""
    cells = {}
    for r in A:
        cells.setdefault((r["vb"], r["pb"]), [[], []])[0].append(r[key])
    for r in B:
        cells.setdefault((r["vb"], r["pb"]), [[], []])[1].append(r[key])
    use = {}
    for c, (a, b) in cells.items():
        a = np.array(a, float); b = np.array(b, float)
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) >= 2 and len(b) >= 2:
            use[c] = (a, b)
    if not use:
        return None
    w = {c: min(len(a), len(b)) for c, (a, b) in use.items()}
    W = sum(w.values())
    f = lambda smp: sum(w[c] * (np.mean(smp(b)) - np.mean(smp(a))) for c, (a, b) in use.items()) / W
    e0 = f(lambda x: x)
    bs = [f(lambda x: x[rng.integers(0, len(x), len(x))]) for _ in range(NB)]
    return dict(diff=float(e0), lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5)),
                n=int(W), cells={f"{c}": (len(a), len(b)) for c, (a, b) in use.items()})


print("=== (1) leave-one-route-out: TQ-V282 stratified hfnp diff, phase=hold ===")
routes = sorted(set(r["rk"] for r in rows))
V282_routes = sorted(set(r["rk"] for r in rows if r["group"] == "V282"))
TQ_routes = sorted(set(r["rk"] for r in rows if r["group"] in ("T64", "T64B", "T5", "T4")))
results_loro = {}
for phase in ("build", "hold", "unwind", "ret"):
    key = f"hfnp_{phase}"
    print(f" -- phase {phase} --")
    full_A = [r for r in rows if r["group"] == "V282"]
    full_B = [r for r in rows if r["group"] in ("T64", "T64B", "T5", "T4")]
    e = strat_diff(full_A, full_B, key)
    print(f"   ALL ROUTES        n_events(A,B)={len(full_A)},{len(full_B)}  diff {e['diff']:+.2f} [{e['lo']:+.2f},{e['hi']:+.2f}] matched_pairs {e['n']}")
    results_loro[phase] = {"all": e}
    for rk in V282_routes:
        A = [r for r in rows if r["group"] == "V282" and r["rk"] != rk]
        e = strat_diff(A, full_B, key)
        if e is None:
            print(f"   drop {rk:24s} (V282)  -> no matched cells left")
            continue
        print(f"   drop {rk:24s} (V282)  diff {e['diff']:+.2f} [{e['lo']:+.2f},{e['hi']:+.2f}] n_A={len(A)} matched {e['n']}")
        results_loro[phase][f"drop_{rk}"] = e
    for rk in TQ_routes:
        B = [r for r in rows if r["group"] in ("T64", "T64B", "T5", "T4") and r["rk"] != rk]
        e = strat_diff(full_A, B, key)
        if e is None:
            print(f"   drop {rk:24s} (TQ)    -> no matched cells left")
            continue
        print(f"   drop {rk:24s} (TQ)    diff {e['diff']:+.2f} [{e['lo']:+.2f},{e['hi']:+.2f}] n_B={len(B)} matched {e['n']}")
        results_loro[phase][f"drop_{rk}"] = e

print("\n=== (2) per-torque-fork-version breakdown (NOT pooled), hfnp medians ===")
results_perbuild = {}
for phase in ("build", "hold", "unwind", "ret"):
    key = f"hfnp_{phase}"
    line = f"  {phase:6s}"
    results_perbuild[phase] = {}
    for g in ("V282", "V282old", "T64", "T64B", "T5", "T4"):
        x = np.array([r[key] for r in rows if r["group"] == g], float)
        x = x[np.isfinite(x)]
        med = float(np.median(x)) if len(x) else float("nan")
        results_perbuild[phase][g] = dict(median=med, n=int(len(x)))
        line += f" | {g:7s} med {med:6.2f} n{len(x):2d}"
    print(line)

print("\n=== (3) fork-config confound check: V282 (LAF 6.0) vs V282old (LAF 2.1-4.0), same firmware ===")
for phase in ("build", "hold", "unwind", "ret"):
    key = f"hfnp_{phase}"
    a = np.array([r[key] for r in rows if r["group"] == "V282"], float)
    b = np.array([r[key] for r in rows if r["group"] == "V282old"], float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    ma, mb = np.median(a), np.median(b)
    print(f"  {phase:6s} V282 med {ma:6.2f} (n{len(a)})  V282old med {mb:6.2f} (n{len(b)})  ratio old/new {mb/max(ma,1e-9):.2f}")
    # bootstrap on whether V282 vs V282old differ at all (route-cluster)
    def cl_boot_diff(A, B, key, NB=2000):
        aroutes = sorted(set(r["rk"] for r in A)); broutes = sorted(set(r["rk"] for r in B))
        abyr = {q: np.array([r[key] for r in A if r["rk"] == q], float) for q in aroutes}
        bbyr = {q: np.array([r[key] for r in B if r["rk"] == q], float) for q in broutes}
        bs = []
        for _ in range(NB):
            pa = rng.choice(aroutes, len(aroutes)); pb = rng.choice(broutes, len(broutes))
            za = np.concatenate([abyr[p][rng.integers(0, len(abyr[p]), len(abyr[p]))] for p in pa])
            zb = np.concatenate([bbyr[p][rng.integers(0, len(bbyr[p]), len(bbyr[p]))] for p in pb])
            bs.append(np.nanmedian(zb) - np.nanmedian(za))
        return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    A = [r for r in rows if r["group"] == "V282"]; B = [r for r in rows if r["group"] == "V282old"]
    lo, hi = cl_boot_diff(A, B, key)
    print(f"           route-cluster CI of (V282old - V282) median: [{lo:+.2f},{hi:+.2f}]  (contains 0? {'yes' if lo<=0<=hi else 'NO'})")

print("\n=== (4) exact per-cell (speed-bin x peak-angle-bin) medians, phase=hold ===")
key = "hfnp_hold"
cellsA = {}
cellsB = {}
for r in rows:
    if not np.isfinite(r.get(key, float('nan'))):
        continue
    c = (r["vb"], r["pb"])
    if r["group"] == "V282":
        cellsA.setdefault(c, []).append(r[key])
    elif r["group"] in ("T64", "T64B", "T5", "T4"):
        cellsB.setdefault(c, []).append(r[key])
cell_report = {}
for c in sorted(set(cellsA) | set(cellsB)):
    a = cellsA.get(c, []); b = cellsB.get(c, [])
    ma = np.median(a) if a else float('nan'); mb = np.median(b) if b else float('nan')
    cell_report[str(c)] = dict(V282_med=float(ma), V282_n=len(a), TQ_med=float(mb), TQ_n=len(b))
    print(f"  vb={T.VB[c[0]]:6s} pb={T.PB[c[1]]:7s}  V282 med {ma:6.2f} (n{len(a)})   TQ med {mb:6.2f} (n{len(b)})")

json.dump(dict(loro=results_loro, perbuild=results_perbuild, cells=cell_report), open(OUT + "v1_out.json", "w"), indent=1)
print("\nwrote", OUT + "v1_out.json")
