"""POWER lens verification of finding s1_goal/achieved-signal-crosscheck.

Loads the same _red/<route>.npz 'specs' arrays s1_analyze.py used, and for each
group x band x vb cell in {V282, T64, T64B, T5, T4} x {0.05-0.15,0.15-0.3,0.3-0.6} x all vb,
computes:
  - point H_pose, H_act, diff = H_pose - H_act  (power-weighted over available segments, same as s1_analyze)
  - a PAIRED route+segment bootstrap (routes w/ replacement, then segments-within-route w/ replacement) of diff,
    to get an empirical CI/SE on the DIFFERENCE itself (s1_analyze only ever bootstrapped H_pose alone, never
    H_act or the difference; and never flagged single-route cells where a route-level bootstrap cannot see
    between-route variance at all).
  - a same-shuffle "coherence at low DOF is biased toward 1" sanity check: nseg (Welch-averages) available.

Outputs a JSON + printed table with, per cell: nseg, nroutes, diff, boot SE(diff), 95% CI(diff), whether |diff|>0.1
is inside/outside that CI, and whether nroutes==1 (route variance unobservable -> CI is a floor, not the true
uncertainty).
"""
import sys, json, glob
from pathlib import Path
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

RED = Path('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal/_red')
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60)]
BANDIDX = {0: "0.05-0.15", 1: "0.15-0.3", 2: "0.3-0.6"}
VBNAME = {0: "2-8", 1: "8-15", 2: "15-22", 3: ">22"}
rng = np.random.default_rng(7)


def load_specs():
    files = sorted(glob.glob(str(RED / "*.npz")))
    specs = []; meta = {}
    for ri, f in enumerate(files):
        D = np.load(f, allow_pickle=True)
        M = json.loads(str(D["meta"]))
        meta[ri] = M
        g = GROUPS.index(M["group"])
        for sp in D["specs"]:
            specs.append(dict(sp, g=g, r=ri))
        del D
    return specs, meta


def est(Ls):
    """Same power-weighted H estimator as s1_analyze.est()."""
    Pxx = sum(s["Pxx"] * s["n"] for s in Ls)
    o = {}
    for nm in ("pose", "act"):
        Pxy = sum(s["Pxy_" + nm] * s["n"] for s in Ls)
        Pyy = sum(s["Pyy_" + nm] * s["n"] for s in Ls)
        H = np.abs(Pxy) / np.maximum(Pxx, 1e-30)
        coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
        o["H_" + nm] = float(np.average(H, weights=Pxx))
        o["coh_" + nm] = float(np.average(coh, weights=Pxx))
    o["diff"] = o["H_pose"] - o["H_act"]
    return o


def main():
    specs, meta = load_specs()
    out = []
    for b in range(3):
        for v in range(4):
            for g in range(len(GROUPS)):
                if GROUPS[g] == "V282old":
                    continue  # excluded from this claim (sR-confounded, finding says so explicitly)
                L = [s for s in specs if s["band"] == b and s["vb"] == v and s["g"] == g]
                if not L:
                    continue
                pt = est(L)
                rr = np.array([s["r"] for s in L]); ur = np.unique(rr)
                nroutes = len(ur); nseg = len(L)
                # paired route+segment bootstrap of the DIFFERENCE
                diffs = []
                for _ in range(1000):
                    pick = []
                    for ri in rng.choice(ur, len(ur)):
                        cand = [s for s in L if s["r"] == ri]
                        pick += [cand[i] for i in rng.integers(0, len(cand), len(cand))]
                    diffs.append(est(pick)["diff"])
                diffs = np.array(diffs)
                se = float(np.std(diffs))
                lo, hi = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
                # minimum detectable |diff| at 80% power, two-sided alpha=0.05 (rule of thumb 2.8*SE)
                mde80 = 2.8 * se
                sec = float(sum(s["n"] for s in L) / V.FS)
                out.append(dict(group=GROUPS[g], vb=VBNAME[v], band=BANDIDX[b], nseg=nseg, nroutes=nroutes,
                                 sec=round(sec, 1), H_pose=round(pt["H_pose"], 3), H_act=round(pt["H_act"], 3),
                                 diff=round(pt["diff"], 3), boot_se=round(se, 3), ci_lo=round(lo, 3), ci_hi=round(hi, 3),
                                 mde80=round(mde80, 3), route_var_observable=bool(nroutes > 1),
                                 within_pm0p1_but_ci_wider=bool(abs(pt["diff"]) < 0.1 and (hi - lo) / 2 > 0.15)))
    json.dump(out, open('power_check_out.json', 'w'), indent=1)
    # console table
    print(f"{'group':6s} {'vb':6s} {'band':9s} nseg nrt   sec  H_pose H_act   diff   SE(diff)   95%CI          MDE80  rtVarObs")
    for r in out:
        print(f"{r['group']:6s} {r['vb']:6s} {r['band']:9s} {r['nseg']:4d} {r['nroutes']:3d} {r['sec']:6.1f} "
              f"{r['H_pose']:6.3f} {r['H_act']:6.3f} {r['diff']:+.3f}  {r['boot_se']:.3f}   "
              f"[{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}]  {r['mde80']:.3f}  {r['route_var_observable']}")
    # summary counts
    n_total = len(out)
    n_single_route = sum(1 for r in out if r['nroutes'] == 1)
    n_ci_engulfs_0p1 = sum(1 for r in out if r['ci_lo'] <= -0.1 or r['ci_hi'] >= 0.1)
    n_mde_over_0p1 = sum(1 for r in out if r['mde80'] > 0.1)
    print(f"\ncells total {n_total}, single-route {n_single_route}, "
          f"95%CI(diff) includes |0.1| in {n_ci_engulfs_0p1}, MDE80(diff) > 0.1 in {n_mde_over_0p1}")


if __name__ == "__main__":
    main()
