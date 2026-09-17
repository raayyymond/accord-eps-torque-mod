import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
D = json.load(open(OUT + 's3_pass2.json'))
rows = D["rows"]
GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
for r in rows:
    r["vb"], r["pb"] = T.strata(r); r["G"] = GM[r["group"]]
rng = np.random.default_rng(2)


def cl_boot(sub, k, stat=np.nanmean, NB=2000):
    x = np.array([r[k] for r in sub], float)
    routes = sorted(set(r["rk"] for r in sub))
    byr = {q: np.array([r[k] for r in sub if r["rk"] == q], float) for q in routes}
    bs = []
    for _ in range(NB):
        pick = rng.choice(routes, len(routes))
        z = np.concatenate([byr[p][rng.integers(0, len(byr[p]), len(byr[p]))] for p in pick])
        bs.append(stat(z))
    return float(stat(x)), float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5)), int(np.isfinite(x).sum())


def strat(A, B, k, NB=2000):
    cells = {}
    for r in A:
        cells.setdefault((r["vb"], r["pb"]), [[], []])[0].append(r[k])
    for r in B:
        cells.setdefault((r["vb"], r["pb"]), [[], []])[1].append(r[k])
    use = {c: (np.array(a, float), np.array(b, float)) for c, (a, b) in cells.items()}
    use = {c: (a[np.isfinite(a)], b[np.isfinite(b)]) for c, (a, b) in use.items()}
    use = {c: ab for c, ab in use.items() if len(ab[0]) >= 2 and len(ab[1]) >= 2}
    w = {c: min(len(a), len(b)) for c, (a, b) in use.items()}; W = sum(w.values())
    f = lambda smp: sum(w[c] * (np.mean(smp(b)) - np.mean(smp(a))) for c, (a, b) in use.items()) / W
    e0 = f(lambda x: x)
    bs = [f(lambda x: x[rng.integers(0, len(x), len(x))]) for _ in range(NB)]
    return float(e0), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), W


res = {}
print("best lag (s), mean [route-cluster CI] n")
for G in ["V282", "V282old", "TQ"]:
    sub = [r for r in rows if r["G"] == G]
    for key in ("aa", "ap"):
        e = cl_boot(sub, f"{key}_bestlag")
        res[f"{G}_{key}_bestlag"] = e
        print(f"  {G:8s} {key}: {e[0]:.3f} [{e[1]:.3f},{e[2]:.3f}] n{e[3]}")
A = [r for r in rows if r["G"] == "V282"]; B = [r for r in rows if r["G"] == "TQ"]
for key in ("aa", "ap"):
    e = strat(A, B, f"{key}_bestlag"); res[f"strat_TQ-V282_{key}_bestlag"] = e
    print(f"  strat TQ-V282 {key} bestlag {e[0]:+.3f} [{e[1]:+.3f},{e[2]:+.3f}] matched {e[3]}")
print("\nlag sweep: group means [route CI] of sym (restoring bias; + = more turn than asked) and hold, and TQ-V282 stratified")
for key in ("aa", "ap"):
    for L in D["lags"]:
        line = f"  {key} L={L:.2f}"
        for G in ["V282", "V282old", "TQ"]:
            sub = [r for r in rows if r["G"] == G]
            e = cl_boot(sub, f"{key}_L{L}_sym", NB=500)
            line += f" | {G} sym {e[0]:+.3f}[{e[1]:+.2f},{e[2]:+.2f}]"
            res[f"{G}_{key}_L{L}_sym"] = e
        for comp in ("sym", "anti", "hold", "unwind", "build"):
            e = strat(A, B, f"{key}_L{L}_{comp}", NB=500); res[f"strat_TQ-V282_{key}_L{L}_{comp}"] = e
            line += f" | d{comp} {e[0]:+.3f}[{e[1]:+.3f},{e[2]:+.3f}]"
        print(line)
print("\nerror profile vs |desired|/P (common lag 0.25 s), group mean over events; bins", D["fbins"])
for key in ("aa", "ap"):
    for ph in ("build", "unwind"):
        for G in ["V282", "V282old", "TQ"]:
            sub = np.array([r[f"{key}_c25_prof_{ph}"] for r in rows if r["G"] == G], float)
            mu = np.nanmean(sub, 0); nn = np.isfinite(sub).sum(0)
            res[f"prof_{key}_{ph}_{G}"] = dict(mean=mu.tolist(), n=nn.tolist())
            print(f"  {key} {ph:6s} {G:8s} " + " ".join(f"{m:+.3f}" for m in mu) + "   n " + ",".join(str(x) for x in nn))
print("\nHF 2-10 Hz steer-rate rms on NON-pressed frames (deg/s): median [route CI]")
for ph in ("build", "hold", "unwind", "ret"):
    line = f"  {ph:6s}"
    for G in ["V282", "V282old", "TQ"]:
        sub = [r for r in rows if r["G"] == G]
        e = cl_boot(sub, f"hfnp_{ph}", stat=np.nanmedian, NB=1000); res[f"{G}_hfnp_{ph}"] = e
        line += f" | {G} {e[0]:6.2f} [{e[1]:.2f},{e[2]:.2f}] n{e[3]}"
    e = strat(A, B, f"hfnp_{ph}", NB=1000); res[f"strat_TQ-V282_hfnp_{ph}"] = e
    line += f" | strat TQ-V282 {e[0]:+.2f} [{e[1]:+.2f},{e[2]:+.2f}]"
    print(line)
print("\nsteer-rate PSD in turn windows (non-pressed): peak and band power")
for G, a in D["psd"].items():
    f = np.array(a["f"]); p = np.array(a["p"]); po = np.array(a["pout"])
    m = (f >= 1.0) & (f <= 8)
    bands = {b: float(np.sum(p[(f >= b[0]) & (f < b[1])]) * (f[1] - f[0])) for b in [(0.5, 1.5), (1.5, 3.5), (3.5, 6), (6, 10), (10, 20)]}
    print(f"  {G:8s} sec {a['sec']:6.0f} peak(1-8 Hz) {f[m][np.argmax(p[m])]:.2f} Hz  cmd peak {f[m][np.argmax(po[m])]:.2f} Hz  "
          + " ".join(f"{b[0]}-{b[1]}:{np.sqrt(v):.1f}" for b, v in bands.items()))
json.dump(res, open(OUT + 's3_pass2_stats.json', 'w'), indent=1)
