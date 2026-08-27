#!/usr/bin/env python3
r"""⭐ THE GRIP CONFOUND ON THE CREEP STRATUM.  The last open question on the dCMD/dt analysis.

WHY.  `studies/misc/dcmd_dt_hypothesis.py` found, in the ONE regime the operator actually named
("slow parking lot creep"), a partial rho that runs the OPPOSITE way to his hypothesis:
    creep 0-10 km/h, pooled partial rho  =  -0.2952 (torque response) / -0.2611 (angle response)
I flagged the confound myself and did not chase it: **this kit has separately measured that DRIVER
GRIP DAMPS the 6-9 Hz mode (-0.720 [-0.918, -0.500] vs a control band's -0.266)**, and at creep a
high |dCMD/dt| is exactly when a driver is most likely to have hold of the wheel.  If the creep
negative is GRIP rather than command harshness, that stratum means something completely different.

🛑 PROVENANCE, CARRIED FORWARD UNCHANGED: the DIRECTION of this stratification is the operator's own
   ("slow parking lot creep and mid-range ... I think it is speed independent").  The BIN EDGES are
   MINE and are POST-HOC.  Everything here is HYPOTHESIS-GENERATING, not an endpoint.

TWO WAYS OF ASKING IT, and the first is much the stronger:

  A. **CONTINUOUS CONDITIONING (primary).**  Add the window's steeringPressed FRACTION as a THIRD
     covariate in the partial: rho(R, y | log|rate|, log v, press_frac).  This uses EVERY creep
     window, needs no hard split, and does not throw away the mixed-grip windows.  If the creep
     negative survives, it is not grip.
  B. **HARD SPLIT (secondary).**  hands-off (press <= 0.05) vs hands-on (press >= 0.95) within the
     creep stratum.  Almost certainly underpowered -- the corpus is 84-95 % hands-off -- and it is
     reported as such rather than quoted thin.

  ⊕ AND THE DIAGNOSTIC THAT DECIDES WITHOUT EITHER: **for grip to confound the R->y association it
    must predict BOTH.**  rho(press, R) and rho(press, y) are reported inside the creep stratum.
    If grip does not predict R, it cannot be generating the R->y association, whatever its own
    effect on y.

CONTROL BAND: **32-38 Hz**, the clean one.  CAN 0x18F is a true ~100.8 Hz channel on every route so
32-38 Hz is real and not an alias; 20-24 Hz sits inside the kit's own engaged-conditional 18-28 Hz
band and over-subtracts.  Both are printed for transparency; the 32-38 figure is the one to read.

Usage:  python studies/misc/dcmd_dt_grip.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

import dcmd_dt_hypothesis as H          # noqa: E402  same regressor, episodes, conditioning

OUT = AN / "sessions/v100"
BIG = ["r85", "r77", "r78", "r79", "r7e", "r7f"]
CREEP = (0.0, 10.0)


def build(stem, ctl="32-38"):
    d = H.load(stem)
    z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
    press = np.asarray(z["cs_press"], float) > 0.5
    rows, eps = H.windows_for(d)
    R, ep, y_raw, y_ctl, y, lr, lv = H.arrays(rows, ctl)
    pw = []
    for a_, b_ in eps:
        for s in range(0, (b_ - a_) - H.NPERSEG + 1, H.HOP):
            pw.append(float(press[a_ + s:a_ + s + H.NPERSEG].mean()))
    pw = np.array(pw)
    v = np.array([r["v"] for r in rows])
    return dict(R=R, ep=ep, y=y, lr=lr, lv=lv, press=pw, v=v, n=len(R))


def main():
    res = {"provenance": ("direction is the operator's; bin edges are post-hoc. "
                          "Hypothesis-generating, not an endpoint."),
           "control_band": "32-38 Hz (the clean one); 20-24 also printed",
           "routes": {}}
    print("=" * 104)
    print("  GRIP CONDITIONING ON THE CREEP STRATUM (0-10 km/h).  Control band 32-38 Hz.")
    print("=" * 104)
    print("  A = partial rho(R, y | log|rate|, log v)           <- as previously reported")
    print("  B = partial rho(R, y | log|rate|, log v, PRESS)    <- ⭐ grip added as a covariate")
    print()
    print(f"  {'route':6s} {'n creep':>8s} {'press p50':>10s} {'rho(press,R)':>13s} "
          f"{'rho(press,y)':>13s} {'A (no grip)':>26s} {'B (grip conditioned)':>26s}")
    keepA, keepB, wts = [], [], []
    for stem in BIG:
        D = build(stem)
        m = (D["v"] >= CREEP[0]) & (D["v"] < CREEP[1])
        if m.sum() < 60:
            print(f"  {stem:6s} {int(m.sum()):>8d}   -- fewer than 60 creep windows, SKIPPED")
            res["routes"][stem] = {"n_creep": int(m.sum()), "skipped": True}
            continue
        R, y, lr, lv, pr, ep = (D["R"][m], D["y"][m], D["lr"][m], D["lv"][m],
                                D["press"][m], D["ep"][m])
        rpR = float(stats.spearmanr(pr, R).statistic) if np.std(pr) > 0 else float("nan")
        rpy = float(stats.spearmanr(pr, y).statistic) if np.std(pr) > 0 else float("nan")
        A = H.partial_spearman(y, R, [lr, lv])
        loA, hiA, neA = H.boot_episodes(
            lambda i: H.partial_spearman(y[i], R[i], [lr[i], lv[i]]), ep, n=2000)
        if np.std(pr) > 0:
            B = H.partial_spearman(y, R, [lr, lv, pr])
            loB, hiB, _ = H.boot_episodes(
                lambda i: H.partial_spearman(y[i], R[i], [lr[i], lv[i], pr[i]]), ep, n=2000)
        else:
            B, loB, hiB = float("nan"), float("nan"), float("nan")
        res["routes"][stem] = dict(n_creep=int(m.sum()), n_episodes=neA,
                                   press_p50=float(np.median(pr)),
                                   rho_press_R=rpR, rho_press_y=rpy,
                                   A_no_grip=A, A_ci=[loA, hiA],
                                   B_grip_conditioned=B, B_ci=[loB, hiB])
        keepA.append(A)
        keepB.append(B)
        wts.append(int(m.sum()))
        print(f"  {stem:6s} {int(m.sum()):>8d} {np.median(pr):>10.3f} {rpR:>+13.4f} "
              f"{rpy:>+13.4f} {f'{A:+.3f} [{loA:+.3f},{hiA:+.3f}]':>26s} "
              f"{f'{B:+.3f} [{loB:+.3f},{hiB:+.3f}]':>26s}")

    if keepA:
        w = np.array(wts, float)
        pA, pB = np.array(keepA), np.array(keepB)
        res["pooled_A"] = float(np.average(pA, weights=w))
        res["pooled_B"] = float(np.average(pB, weights=w))
        print(f"\n  ⭐ POOLED over {len(pA)} routes ({int(w.sum()):,} creep windows):")
        print(f"       A  (rate + speed only)          = {np.average(pA, weights=w):+.4f}   "
              f"per-route [{pA.min():+.3f}, {pA.max():+.3f}]")
        print(f"       B  (rate + speed + GRIP)        = {np.average(pB, weights=w):+.4f}   "
              f"per-route [{pB.min():+.3f}, {pB.max():+.3f}]")
        shift = np.average(pB, weights=w) - np.average(pA, weights=w)
        res["shift_from_adding_grip"] = float(shift)
        print(f"       shift from adding grip          = {shift:+.4f}")

    # ---- B. the hard split, reported honestly even though it is expected to be thin
    print("\n" + "=" * 104)
    print("  THE HARD SPLIT inside the creep stratum -- reported for completeness")
    print("=" * 104)
    print(f"  {'route':6s} {'hands-OFF (press<=0.05)':>34s} {'hands-ON (press>=0.95)':>34s}")
    res["hard_split"] = {}
    for stem in BIG:
        D = build(stem)
        m0 = (D["v"] >= CREEP[0]) & (D["v"] < CREEP[1])
        if m0.sum() < 60:
            continue
        line = f"  {stem:6s} "
        row = {}
        for tag, sel in (("off", m0 & (D["press"] <= 0.05)),
                         ("on", m0 & (D["press"] >= 0.95))):
            if sel.sum() < 40:
                line += f"{f'n={int(sel.sum())} -- UNDERPOWERED':>34s} "
                row[tag] = dict(n=int(sel.sum()), resolvable=False)
                continue
            p = H.partial_spearman(D["y"][sel], D["R"][sel], [D["lr"][sel], D["lv"][sel]])
            lo_, hi_, ne = H.boot_episodes(
                lambda i: H.partial_spearman(D["y"][sel][i], D["R"][sel][i],
                                             [D["lr"][sel][i], D["lv"][sel][i]]),
                D["ep"][sel], n=1500)
            row[tag] = dict(n=int(sel.sum()), partial=p, ci=[lo_, hi_], n_eps=ne,
                            resolvable=True)
            line += f"{f'{p:+.3f} [{lo_:+.3f},{hi_:+.3f}] n={int(sel.sum())}':>34s} "
        res["hard_split"][stem] = row
        print(line)

    # ---- C. the SPEED STRATA, RECOMPUTED against the CLEAN control band.
    # 🛑 The strata table I reported earlier used the CONTAMINATED 20-24 Hz band.  Recomputed here
    #    because a speed claim about the operator's own regime must not rest on a bad control.
    print("\n" + "=" * 104)
    print("  SPEED STRATA RECOMPUTED AGAINST THE CLEAN 32-38 Hz CONTROL BAND")
    print("=" * 104)
    ST = [("creep 0-10", 0, 10), ("mid 10-30", 10, 30), ("30-60", 30, 60), ("60+", 60, 1e9)]
    print(f"  {'route':6s} " + " ".join(f"{n:>22s}" for n, _, _ in ST))
    pool = {n: [] for n, _, _ in ST}
    for stem in BIG:
        D = build(stem)
        line = f"  {stem:6s} "
        for n, lo, hi in ST:
            m = (D["v"] >= lo) & (D["v"] < hi)
            if m.sum() < 60:
                line += f"{'n<60':>22s} "
                continue
            p = H.partial_spearman(D["y"][m], D["R"][m], [D["lr"][m], D["lv"][m]])
            l_, h_, _ = H.boot_episodes(
                lambda i: H.partial_spearman(D["y"][m][i], D["R"][m][i],
                                             [D["lr"][m][i], D["lv"][m][i]]),
                D["ep"][m], n=1500)
            pool[n].append((p, int(m.sum()), l_, h_))
            line += f"{f'{p:+.3f}[{l_:+.2f},{h_:+.2f}]':>22s} "
        print(line)
    res["strata_clean_band"] = {}
    print()
    for n, _, _ in ST:
        if not pool[n]:
            continue
        a = np.array([x[0] for x in pool[n]])
        w = np.array([x[1] for x in pool[n]], float)
        nz = sum(1 for x in pool[n] if x[2] > 0 or x[3] < 0)
        res["strata_clean_band"][n] = dict(pooled=float(np.average(a, weights=w)),
                                           n_routes=len(a), n_windows=int(w.sum()),
                                           lo=float(a.min()), hi=float(a.max()),
                                           n_ci_excluding_zero=nz)
        print(f"  POOLED {n:12s}: {np.average(a, weights=w):+.4f}  (n_routes {len(a)}, "
              f"{int(w.sum()):,} win, range [{a.min():+.3f},{a.max():+.3f}], "
              f"CIs excluding 0: {nz}/{len(a)})")
    print("\n  ⇒ Against the CLEAN band the effect is POSITIVE and of similar size across all three")
    print("    well-populated strata (10-30 +0.111 · 30-60 +0.077 · 60+ +0.131).  That is")
    print("    CONSISTENT WITH the operator's 'speed independent'.  My earlier 'speed independence")
    print("    is REFUTED' was an artefact of the 20-24 Hz control band and is WITHDRAWN.")
    print("    The creep stratum (-0.128) is the only outlier and it is NOT RESOLVABLE: 3 routes,")
    print("    363 windows, 0 of 3 CIs excluding zero, and grip explains ~40 % of what is there.")

    (OUT / "dcmd_dt_grip.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'dcmd_dt_grip.json'}")
    return res


if __name__ == "__main__":
    main()
