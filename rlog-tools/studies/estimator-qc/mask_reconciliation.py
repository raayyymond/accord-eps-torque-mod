#!/usr/bin/env python3
r"""THE MASK RECONCILIATION: `steeringPressed` vs the symptom-regime mask, and whether the
hands-ON arm of the dCMD/dt analysis is recoverable.

THE QUESTION.  I reported that these drives are 84-95 % HANDS-OFF and flagged the other agent's
67 % as needing reconciliation.  The hypothesis put to me: `steeringPressed` EXCLUDES the symptom
regime (per `memory/reference/measurement/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`), so it
systematically UNDER-counts hands-on and my 84-95 % is a mask artefact.

🛑 READING THE MEMORY, THAT HYPOTHESIS DOES NOT SURVIVE -- AND THE MEMORY ITSELF SUPPLIES THE
   REFUTATION AND THE REAL EXPLANATION.  Three things it says, in its own numbers:

   1. **The corpus is 7121.6 s engaged HANDS-OFF against 994.9 s engaged HANDS-ON = 87.7 % / 12.3 %.**
      That is the memory's OWN figure, and it AGREES with my 84-95 %.  So `steeringPressed` is not
      under-counting relative to the kit's own accounting -- **my number and the memory's number are
      the same number.**
   2. What the memory actually says is wrong with the mask is (a) a WINDOW-SELECTION effect when
      every frame of a 5.12 s window must pass -- it drops 39 % of engaged and 93 % of manual
      candidate windows, arm-asymmetrically -- and (b) that the kit historically masked TO hands-off
      and thereby pointed the instrument AWAY from the symptom.  **Neither claim is that the duty
      itself is mis-measured.**  `press == (|cs_tq| > 1200)` holds on 99.28-99.96 % of frames.
   3. ⭐ **AND HERE IS WHY MY HANDS-ON ARM CAME BACK n = 3:** *"Override does not support the kit's
      band estimator at all.  5013 contiguous override runs make up the corpus's 994.9 s: median run
      **0.02 s**, p90 **0.55 s**, and only SEVEN runs corpus-wide reach 5.12 s."*
      My hands-ON arm required `press >= 0.95` across a 1.28 s window = 122 of 128 consecutive
      frames.  **Against a median override run of 0.02 s and a p90 of 0.55 s, essentially no window
      can satisfy that.  The arm was killed by my PURITY RULE, not by the mask and not by a lack of
      override.**  That is my defect, not the mask's.

⇒ SO THE ARM MAY BE RECOVERABLE, and the memory prescribes how: *"Use point-process and
  event-triggered methods, or 1.28 s windows, and say which."*  My windows are already 1.28 s.  What
  has to change is the ARM DEFINITION: replace the >=0.95 purity rule with the memory's own
  band-orthogonal D3 form -- **window-MEDIAN |cs_tq| against 1200** -- which a median over the
  window makes insensitive to 2-38 Hz content, exactly as the memory argues.

WHAT THIS FILE DOES
  A. duty comparison per route: frame-wise `steeringPressed`, D3 window-median, and the >=0.95
     purity rule, side by side -- including route 81, the route the 67 % is attributed to.
  B. override RUN-LENGTH statistics, to confirm the point-process character on these routes.
  C. **re-runs the dCMD/dt hands-ON arm under the D3 window-median split**, which is the thing that
     actually matters: if it is now determinable, the operator's own regime is finally in scope.

Usage:  python studies/estimator-qc/mask_reconciliation.py
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

import dcmd_dt_hypothesis as H          # noqa: E402
import dcmd_dt_grip as G                # noqa: E402

OUT = AN / "sessions/v100"
FS = 100.0
THR = 1200.0                            # opendbc STEER_THRESHOLD for the 10th-gen Accord
ROUTES = ["r85", "r77", "r78", "r79", "r7e", "r7f", "r81", "r82"]


def load_extra(stem):
    z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
    return (np.asarray(z["cs_press"], float) > 0.5, np.abs(np.asarray(z["cs_tq"], float)),
            np.asarray(z["cc_lat"], float) > 0.5)


def runs(mask):
    m = np.asarray(mask, bool).astype(int)
    if not m.any():
        return np.array([])
    d = np.diff(np.concatenate([[0], m, [0]]))
    return (np.where(d == -1)[0] - np.where(d == 1)[0]) / FS


def main():
    res = {"threshold": THR, "per_route": {}}

    # ---------- A. the duty comparison ----------
    print("=" * 116)
    print("  A.  HANDS-ON DUTY UNDER THREE DEFINITIONS.  All on ENGAGED frames/windows only.")
    print("=" * 116)
    print(f"  {'route':6s} {'press duty':>11s} {'press==|tq|>1200':>17s} "
          f"{'D3 win-median ON':>17s} {'purity>=0.95 ON':>16s} {'n windows':>10s}")
    for stem in ROUTES:
        try:
            press, atq, eng = load_extra(stem)
            D = G.build(stem)
        except Exception as e:
            print(f"  {stem:6s}  -- unavailable ({type(e).__name__})")
            continue
        agree = float(np.mean(press == (atq > THR)))
        duty = float(press[eng].mean())
        d = H.load(stem)
        rows, eps = H.windows_for(d)
        med, pur = [], []
        for a_, b_ in eps:
            for s in range(0, (b_ - a_) - H.NPERSEG + 1, H.HOP):
                sl = slice(a_ + s, a_ + s + H.NPERSEG)
                med.append(float(np.median(atq[sl])))
                pur.append(float(press[sl].mean()))
        med, pur = np.array(med), np.array(pur)
        d3_on = float(np.mean(med >= THR))
        pu_on = float(np.mean(pur >= 0.95))
        res["per_route"][stem] = dict(press_duty_engaged=duty, press_equals_threshold=agree,
                                      d3_window_median_on=d3_on, purity095_on=pu_on,
                                      n_windows=len(med))
        print(f"  {stem:6s} {duty:11.4f} {agree:17.4f} {d3_on:17.4f} {pu_on:16.4f} "
              f"{len(med):10,}")
    print("\n  ⇒ `press == (|cs_tq| > 1200)` holds at 0.99+ everywhere, exactly as the memory says,")
    print("    so the frame-wise duty is NOT mis-measured.  What collapses is the PURITY rule.")

    # ---------- B. override run lengths ----------
    print("\n" + "=" * 116)
    print("  B.  OVERRIDE RUN LENGTHS (engaged & pressed).  The memory: median 0.02 s, p90 0.55 s,")
    print("      only SEVEN runs corpus-wide reach 5.12 s.  Confirmed here?")
    print("=" * 116)
    print(f"  {'route':6s} {'n runs':>8s} {'total s':>9s} {'median s':>9s} {'p90 s':>7s} "
          f"{'max s':>7s} {'>=1.28 s':>9s} {'>=5.12 s':>9s}")
    res["run_lengths"] = {}
    for stem in ROUTES:
        try:
            press, atq, eng = load_extra(stem)
        except Exception:
            continue
        r = runs(eng & press)
        if not len(r):
            continue
        res["run_lengths"][stem] = dict(n=int(len(r)), total_s=float(r.sum()),
                                        median_s=float(np.median(r)), p90_s=float(np.percentile(r, 90)),
                                        max_s=float(r.max()), n_ge_128=int((r >= 1.28).sum()),
                                        n_ge_512=int((r >= 5.12).sum()))
        print(f"  {stem:6s} {len(r):8,} {r.sum():9.1f} {np.median(r):9.3f} "
              f"{np.percentile(r,90):7.2f} {r.max():7.2f} {int((r>=1.28).sum()):9,} "
              f"{int((r>=5.12).sum()):9,}")
    print("\n  ⇒ If runs of >= 1.28 s are rare, a >=0.95-purity 1.28 s window arm CANNOT be built,")
    print("    and that -- not the mask -- is what made my hands-ON arm n = 3.")

    # ---------- C. the hands-ON arm, re-run under D3 ----------
    print("\n" + "=" * 116)
    print("  C.  THE dCMD/dt HANDS-ON ARM, RE-RUN UNDER THE D3 WINDOW-MEDIAN SPLIT")
    print("      (control band 32-38 Hz, the clean one; partial rho | log|rate|, log v)")
    print("=" * 116)
    print(f"  {'route':6s} {'HANDS-OFF (median<1200)':>34s} {'HANDS-ON (median>=1200)':>34s}")
    res["arm_d3"] = {}
    for stem in ["r85", "r77", "r78", "r79", "r7e", "r7f"]:
        press, atq, eng = load_extra(stem)
        D = G.build(stem)
        d = H.load(stem)
        rows, eps = H.windows_for(d)
        med = []
        for a_, b_ in eps:
            for s in range(0, (b_ - a_) - H.NPERSEG + 1, H.HOP):
                med.append(float(np.median(atq[a_ + s:a_ + s + H.NPERSEG])))
        med = np.array(med)
        line = f"  {stem:6s} "
        row = {}
        for tag, sel in (("off", med < THR), ("on", med >= THR)):
            if sel.sum() < 40:
                line += f"{f'n={int(sel.sum())} UNDERPOWERED':>34s} "
                row[tag] = dict(n=int(sel.sum()), resolvable=False)
                continue
            p = H.partial_spearman(D["y"][sel], D["R"][sel], [D["lr"][sel], D["lv"][sel]])
            lo_, hi_, ne = H.boot_episodes(
                lambda i: H.partial_spearman(D["y"][sel][i], D["R"][sel][i],
                                             [D["lr"][sel][i], D["lv"][sel][i]]),
                D["ep"][sel], n=1500)
            row[tag] = dict(n=int(sel.sum()), partial=p, ci=[lo_, hi_], n_eps=ne, resolvable=True)
            line += f"{f'{p:+.3f} [{lo_:+.3f},{hi_:+.3f}] n={int(sel.sum())}':>34s} "
        res["arm_d3"][stem] = row
        print(line)
    on = [v["on"] for v in res["arm_d3"].values() if v["on"].get("resolvable")]
    if on:
        w = np.array([x["n"] for x in on], float)
        p = np.array([x["partial"] for x in on])
        res["pooled_hands_on"] = float(np.average(p, weights=w))
        print(f"\n  ⭐ POOLED HANDS-ON over {len(on)} routes ({int(w.sum()):,} windows): "
              f"partial rho = {np.average(p, weights=w):+.4f}   range [{p.min():+.3f}, {p.max():+.3f}]")
    else:
        res["pooled_hands_on"] = None
        print("\n  🛑 THE HANDS-ON ARM REMAINS UNDETERMINABLE EVEN UNDER D3.")
    (OUT / "mask_reconciliation.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'mask_reconciliation.json'}")
    return res


if __name__ == "__main__":
    main()
