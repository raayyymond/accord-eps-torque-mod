# -*- coding: utf-8 -*-
"""X2 -- (a) how much of the vector margin is NOISE, and (b) is the plant LTI over the probe's amplitude?

(a) The withdrawal of ARM-KP2 rests on VM ordering five flown anchors.  X1 showed the ordering is a
    property of the PLANT ESTIMATE, not the controller.  Here I put a window-bootstrap CI on it: if the
    anchors' CIs overlap, the ordering is not evidence of anything.

(b) A probe identifies the plant AT THE PROBE'S AMPLITUDE.  If |P| depends on amplitude, a small
    read-only probe certifies a loop the car does not have where the hazard lives (hard corners).
    Split each route's windows by demand amplitude and re-identify.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import advlib2 as A  # noqa: E402

OUT = HERE / "out"
RTS = ["00000071--f2c9d073a3", "00000072--8001fc3048", "00000073--79fd149dd8",
       "0000006c--68c6e94b17", "0000006d--05e83bb04f", "00000064--ce6b0b0ebb"]
NB = 400
BANDS = [("0.15-0.60", 0.15, 0.60), ("0.60-1.20", 0.60, 1.20), ("1.20-2.40", 1.20, 2.40),
         ("2.40-3.50", 2.40, 3.50), ("3.40-4.90", 3.40, 4.90)]


def main():
    rng = np.random.default_rng(20260920)
    print("=" * 122)
    print("(a) VECTOR MARGIN WITH A WINDOW BOOTSTRAP.  Same definition as the withdrawal: VM = min|1+L|")
    print("    over 2-6 Hz, L = P_IV * C_flown.  400 resamples of the windows inside each speed bin.")
    print(f"    {'route|bin':32s} {'n':>3s} {'VM point':>9s} {'2.5%':>7s} {'97.5%':>7s} {'width/pt':>9s}  note")
    res = {}
    for rt in RTS:
        L = A.load(rt)
        f, F, vm, am = A.spectra(L)
        p = A.FLOWN[rt]
        for nm, lo, hi in (("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)):
            idx = np.where((vm >= lo) & (vm < hi))[0]
            if len(idx) < 6:
                continue
            v = float(np.median(vm[idx]))
            C = A.C_fb(f, v, p["kp"], p["laf"], p["ki"], p["ki_hi"], p["q"] if p["notch"] else None)
            R = A.ident(F, idx, instr="r")
            pt, _ = A.vecmargin(f, R["P"] * C)
            bs = []
            for _ in range(NB):
                jj = idx[rng.integers(0, len(idx), len(idx))]
                Rb = A.ident(F, jj, instr="r")
                bs.append(A.vecmargin(f, Rb["P"] * C)[0])
            bs = np.array(bs)
            q1, q2 = np.percentile(bs, [2.5, 97.5])
            res[f"{rt}|{nm}"] = dict(pt=pt, lo=float(q1), hi=float(q2), n=int(len(idx)))
            print(f"    {rt[:10]+'|'+nm:32s} {len(idx):3d} {pt:9.3f} {q1:7.3f} {q2:7.3f} "
                  f"{(q2-q1)/max(pt,1e-9):9.2f}  {A.LBL.get(rt,'')}")
        del L, F
    print()
    r71 = [v for k, v in res.items() if k.startswith("00000071")]
    r72 = [v for k, v in res.items() if k.startswith("00000072")]
    print("    r71 (LIMIT-CYCLED) vs r72 (FLEW CLEAN) -- the pair the whole safety axis rests on:")
    for a in r71:
        for b in r72:
            ov = min(a["hi"], b["hi"]) - max(a["lo"], b["lo"])
            print(f"      r71 [{a['lo']:.3f},{a['hi']:.3f}]  vs  r72 [{b['lo']:.3f},{b['hi']:.3f}]  "
                  f"-> {'OVERLAP' if ov > 0 else 'separated'} ({ov:+.3f})")
    json.dump(res, open(OUT / "x2_vm_boot.json", "w"), indent=1)

    print()
    print("=" * 122)
    print("(b) IS THE PLANT LTI OVER AMPLITUDE?  Windows of the SAME route split at the median demand")
    print("    amplitude (std of the model's desired lateral accel in the window), >=15 m/s only.")
    print("    A probe is a SMALL signal.  If |P| moves with amplitude, the probe identifies the low row.")
    print(f"    {'route':12s} {'half':5s} {'n':>3s} {'|X|rms':>7s} " +
          " ".join(f"{b[0]:>10s}" for b in BANDS))
    amp = {}
    for rt in RTS:
        L = A.load(rt)
        f, F, vm, am = A.spectra(L)
        sel = np.where(vm >= 15.0)[0]
        if len(sel) < 10:
            del L, F
            continue
        med = np.median(am[sel])
        rows = {}
        for half, jj in (("low", sel[am[sel] <= med]), ("high", sel[am[sel] > med])):
            if len(jj) < 4:
                continue
            R = A.ident(F, jj, instr="r")
            rows[half] = [A.bandmean(f, R["P"], lo, hi) for _, lo, hi in BANDS]
            print(f"    {rt[:10]:12s} {half:5s} {len(jj):3d} {np.median(am[jj]):7.4f} " +
                  " ".join(f"{x:10.3f}" for x in rows[half]))
        if "low" in rows and "high" in rows:
            r = [h / l for l, h in zip(rows["low"], rows["high"])]
            amp[rt] = r
            print(f"    {'':12s} {'H/L':5s} {'':3s} {'':7s} " + " ".join(f"{x:10.2f}" for x in r))
        del L, F
    if amp:
        M = np.array(list(amp.values()))
        print()
        print("    POOLED high/low |P| ratio (geometric mean over routes):")
        print("      " + "  ".join(f"{b[0]} {np.exp(np.mean(np.log(M[:, i]))):.2f}x"
                                   for i, b in enumerate(BANDS)))
        print("    A ratio != 1 means the loop gain a dose delivers depends on how hard the car is")
        print("    being asked to turn -- and the hazard (r71's limit cycle) was ON HARD CURVES.")
    json.dump(amp, open(OUT / "x2_amp.json", "w"), indent=1)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    main()
