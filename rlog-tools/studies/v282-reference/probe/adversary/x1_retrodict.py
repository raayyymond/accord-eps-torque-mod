# -*- coding: utf-8 -*-
"""X1 -- CAN THE ENGINE RETRODICT r71?  The single most important test in this workflow.

The Tier B safety claim is made by taking rev 6.4's identified plant, substituting a hypothetical
controller C1, and reading margin statistics off L1 = P*C1.  That operation is only trustworthy if,
performed on a plant identified from a NEIGHBOURING route, it flags the one configuration that is
KNOWN to have gone unstable: r71, which limit-cycled at 2.34 Hz on hard curves at speed.

So:
  (a) reproduce each anchor's vector margin from ITS OWN data and ITS OWN flown controller;
  (b) CROSS-EVALUATE -- put r71's controller on r72's/r73's/T64's plant, and vice versa.  r71 and r72
      flew the SAME SteerKP (0.85) and the SAME SteerLatAccel (14.0) on the SAME EPS build;
  (c) ask whether the anchor ordering is a property of the CONTROLLER (predictive) or of the PLANT
      ESTIMATE taken from each route's own log (bookkeeping);
  (d) test whether VM is simply a re-reading of how much 2-6 Hz disturbance each log contained.

Every number is re-derived here (advlib2, own estimator, own positive controls).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import advlib2 as A  # noqa: E402

OUT = HERE / "out"
BINS = [("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)]
ANCH = ["00000071--f2c9d073a3", "00000072--8001fc3048", "00000073--79fd149dd8",
        "0000006c--68c6e94b17", "0000006d--05e83bb04f",
        "00000064--ce6b0b0ebb", "00000065--b9f78988bd"]


def main():
    print(A._self_test())
    print()
    store = {}
    for rt in ANCH:
        L = A.load(rt)
        f, F, vm, am = A.spectra(L)
        for nm, lo, hi in BINS:
            idx = np.where((vm >= lo) & (vm < hi))[0]
            if len(idx) < 4:
                continue
            R = A.ident(F, idx, instr="r")
            Rf = A.ident(F, idx, instr="uff")
            v = float(np.median(vm[idx]))
            p = A.FLOWN[rt]
            C = A.C_fb(f, v, p["kp"], p["laf"], p["ki"], p["ki_hi"], p["q"] if p["notch"] else None)
            shk = (f >= 1.8) & (f <= 3.5)
            store[f"{rt}|{nm}"] = dict(
                f=f.tolist(), P_r=[R["P"].real.tolist(), R["P"].imag.tolist()],
                P_ff=[Rf["P"].real.tolist(), Rf["P"].imag.tolist()],
                C=[C.real.tolist(), C.imag.tolist()], v=v, n=int(len(idx)),
                coh_r=R["coh_wu"].tolist(), coh_ff=Rf["coh_wu"].tolist(),
                Suu=R["Suu"].tolist(), Srr=R["Srr"].tolist(),
                ushk=float(np.mean(np.sum(np.abs(F["u"][idx][:, shk]) ** 2, axis=1))),
                amp=float(np.median(am[idx])), kp=p["kp"], laf=p["laf"], ki=p["ki"],
                ki_hi=p["ki_hi"], notch=p["notch"])
        del L, F
    json.dump(store, open(OUT / "x1_anchors.json", "w"))

    f = np.array(store[list(store)[0]]["f"])
    print("=" * 118)
    print("1. THE ANCHORS, each from ITS OWN plant and ITS OWN flown controller (what the withdrawal used).")
    print(f"{'route|bin':34s} {'n':>3s} {'v':>5s} {'kp':>5s} {'ki':>4s} {'ntch':>5s} "
          f"{'VM 2-6 (r)':>11s} {'f*':>5s} {'VM (uff)':>9s} {'Ms':>6s} {'coh(r,u) 2-6':>13s} "
          f"{'cmd shake':>10s}   note")
    rows = []
    for k, D in store.items():
        rt = k.split("|")[0]
        P = np.array(D["P_r"][0]) + 1j * np.array(D["P_r"][1])
        Pf = np.array(D["P_ff"][0]) + 1j * np.array(D["P_ff"][1])
        C = np.array(D["C"][0]) + 1j * np.array(D["C"][1])
        vmr, fs = A.vecmargin(f, P * C)
        vmf, _ = A.vecmargin(f, Pf * C)
        ms, _ = A.Ms_of(f, P * C)
        ch = A.bandmean(f, np.array(D["coh_r"]), 2.0, 6.0)
        print(f"{k:34s} {D['n']:3d} {D['v']:5.1f} {D['kp']:5.2f} {D['ki']:4.1f} "
              f"{str(D['notch']):>5s} {vmr:11.3f} {fs:5.2f} {vmf:9.3f} {ms:6.2f} {ch:13.3f} "
              f"{D['ushk']:10.4f}   {A.LBL.get(rt,'')}")
        rows.append(dict(k=k, rt=rt, vm=vmr, vmf=vmf, ms=ms, shake=D["ushk"], coh=ch))
    print()
    print("   ==> Is VM a MARGIN, or a re-reading of how much 2-6 Hz junk was in the log?")
    sh = np.array([r["shake"] for r in rows])
    vv = np.array([r["vm"] for r in rows])
    cc = np.array([r["coh"] for r in rows])
    lr = np.corrcoef(np.log(sh), np.log(vv))[0, 1]
    lc = np.corrcoef(np.log(cc), np.log(vv))[0, 1]
    print(f"   corr(log cmd-shake power, log VM) = {lr:+.3f}    corr(log coh(r,u) 2-6, log VM) = {lc:+.3f}")
    print("   (advlib2 CONTROL C2: with a narrow reference and a heavy in-band disturbance the SAME")
    print("    estimator reports VM 0.004 for a plant whose true VM is 0.505 -- low coherence biases VM")
    print("    DOWN, i.e. toward 'dangerous'.  A route that shook hard therefore reads marginal by")
    print("    construction, whether or not it was.)")

    print()
    print("=" * 118)
    print("2. THE CROSS TEST.  Controller of route A evaluated on the plant of route B.")
    print("   r71 and r72 flew the SAME SteerKP 0.85 / SteerLatAccel 14.0 on the SAME EPS.  In the")
    print("   engine's own parameterisation they differ ONLY in AccordTorqueKi (0.3 vs 0.6).")
    keys = [k for k in store if k.endswith("22+")]
    print(f"   {'plant \\ controller':30s}" + "".join(f"{k.split('--')[0][-2:]:>9s}" for k in keys))
    grid = {}
    for kb in keys:
        Db = store[kb]
        P = np.array(Db["P_r"][0]) + 1j * np.array(Db["P_r"][1])
        line = f"   {kb.split('|')[0][-10:] + ' ' + A.LBL.get(kb.split('|')[0],'')[:14]:30s}"
        for ka in keys:
            Da = store[ka]
            p = A.FLOWN[ka.split("|")[0]]
            C = A.C_fb(f, Db["v"], p["kp"], p["laf"], p["ki"], p["ki_hi"], p["q"] if p["notch"] else None)
            vmx, _ = A.vecmargin(f, P * C)
            grid[(kb, ka)] = vmx
            line += f"{vmx:9.3f}"
        print(line)
    print("   (row = whose plant, column = whose controller.  If the anchor ordering were a property")
    print("    of the CONTROLLER, each column would be ordered the same way on every row.)")
    print()
    for kb in keys:
        vals = [grid[(kb, ka)] for ka in keys]
        o = np.argsort(vals)
        print(f"   on {A.LBL.get(kb.split('|')[0],''):24s} the WORST controller is "
              f"{A.LBL.get(keys[o[0]].split('|')[0],''):24s} (VM {vals[o[0]]:.3f}), the best "
              f"{A.LBL.get(keys[o[-1]].split('|')[0],'')} (VM {vals[o[-1]]:.3f})")

    print()
    print("=" * 118)
    print("3. THE DECISIVE QUESTION.  Score r71's OWN flown controller on the rev 6.4 plant -- exactly")
    print("   the operation Tier B performs -- and compare with the as-flown rev 6.4 controller and")
    print("   with the Tier B doses.  If r71's config does NOT read as the most dangerous thing on")
    print("   this plant, the engine cannot retrodict the one instability we have.")
    cands = [("rev 6.4 AS FLOWN      KP1.0 Q1.0", 1.0, 14.0, 0.3, 0.0, 1.0, False),
             ("r71 AS FLOWN          KP0.85 no notch", 0.85, 14.0, 0.3, 0.0, None, True),
             ("r72 AS FLOWN (clean)  KP0.85 no notch", 0.85, 14.0, 0.6, 0.0, None, True),
             ("ARM-KP3               KP3.0 Q0.30", 3.0, 14.0, 0.6, 0.0, 0.30, False),
             ("TIER B                KP8  Q0.20", 8.0, 14.0, 0.3, 0.0, 0.20, False),
             ("TIER B                KP12 Q0.20", 12.0, 14.0, 0.3, 0.0, 0.20, False),
             ("TIER B                KP16 Q0.20", 16.0, 14.0, 0.3, 0.0, 0.20, False)]
    for kb in [k for k in store if k.startswith("0000006c--68") or k.startswith("0000006d--05")]:
        Db = store[kb]
        P = np.array(Db["P_r"][0]) + 1j * np.array(Db["P_r"][1])
        Pf = np.array(Db["P_ff"][0]) + 1j * np.array(Db["P_ff"][1])
        print(f"\n   --- plant from {kb}  (n {Db['n']} windows, v {Db['v']:.1f} m/s)")
        print(f"   {'config':40s} {'VM(r)':>7s} {'f*':>5s} {'VM(uff)':>8s} {'Ms':>7s} "
              f"{'|L|@2.34':>9s} {'|L|@4.2':>8s}  verdict")
        for lbl, kp, laf, ki, kih, q, _f in cands:
            C = A.C_fb(f, Db["v"], kp, laf, ki, kih, q)
            vmr, fs = A.vecmargin(f, P * C)
            vmf, _ = A.vecmargin(f, Pf * C)
            ms, _ = A.Ms_of(f, P * C)
            j234 = int(np.argmin(np.abs(f - 2.34)))
            j42 = int(np.argmin(np.abs(f - 4.22)))
            L = P * C
            verdict = "UNSTABLE" if vmr < 0.05 else ("marginal" if vmr < 0.33 else "ok by VM")
            print(f"   {lbl:40s} {vmr:7.3f} {fs:5.2f} {vmf:8.3f} {ms:7.2f} "
                  f"{abs(L[j234]):9.3f} {abs(L[j42]):8.3f}  {verdict}")
        print("   (r71's flown anchor on its OWN data was 0.322 / 0.079 -- 'below every other anchor'.)")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    main()
