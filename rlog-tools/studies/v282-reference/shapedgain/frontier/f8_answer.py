# -*- coding: utf-8 -*-
"""f8 -- the answer: the class ceiling, the tiered frontier, and the two requested configs."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP                                  # noqa: E402
from f5_frontier import Engine, C_of, FLOWN          # noqa: E402
from f7_crux import run_with, margins                # noqa: E402

REF = 0.442
FLOWN_M = 1.3512


def row(eng, kp, laf, kih, q):
    r = run_with(eng, kp, laf, kih, q)
    wc, pm, ms, fms = margins(eng, r["L1"])
    return dict(kp=kp, laf=laf, ki_hi=kih, q=q, kp_laf=kp / laf, metric=r["metric"],
                closure=r["closure"], shake_cmd=r["shake_cmd"], shake_L=r["shake_L"],
                Ms=ms, f_Ms=fms, wc=wc, pm=pm, bands=r["bands"],
                lsg=[(kp + LP.low_speed_factor(v)) / laf / ((1.0 + LP.low_speed_factor(v)) / 14.0)
                     for v in (2.0, 4.0, 8.0, 12.0, 20.0, 28.0)])


if __name__ == "__main__":
    eng = Engine()
    S = json.load(open(OUT / "f3_ident.json"))
    eng.Ltot = np.empty_like(eng.L0)
    for tag, lo, hi in (("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)):
        D = S[f"T64|{tag}"]
        eng.Ltot[(eng.v >= lo) & (eng.v < hi)] = np.array(D["L_tot"][0]) + 1j * np.array(D["L_tot"][1])

    A = eng.E - eng.V * eng.D
    m_inf = float(np.sum(np.abs(A[:, eng.b]) ** 2)) / eng.px
    print("=" * 108)
    print("0. THE CEILING OF THE WHOLE LOOP-GAIN CLASS")
    print("   rho -> 0 at infinite loop gain, so E -> A = E - V*D, the part of the goal error the loop")
    print("   cannot reach (setpoint chain + the out-of-loop wheel-angle -> yaw leg + road/measurement).")
    print(f"   metric at infinite gain {m_inf:.3f}   =>  max closure of the class "
          f"{(FLOWN_M - m_inf)/(FLOWN_M - REF)*100:.0f} %   (V282 reference {REF}, as flown {FLOWN_M})")
    Ab = [float(np.sum(np.abs(A[:, s]) ** 2)) / eng.px for s in eng.sb]
    Eb = [float(np.sum(np.abs(eng.E[:, s]) ** 2)) / eng.px for s in eng.sb]
    print(f"   per band  as flown {['%.3f' % x for x in Eb]}   at infinite gain {['%.3f' % x for x in Ab]}")
    print()

    KPS = [1.0, 1.5, 2.0, 2.5, 2.75, 3.0]
    LAFS = [14.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0, 7.0]
    QS = [0.0, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
    KIH = [0.0, 1.0, 2.5, 4.0, 6.0]
    rows = [row(eng, kp, laf, kih, q) for kp, laf, q, kih in itertools.product(KPS, LAFS, QS, KIH)]
    json.dump(rows, open(OUT / "f8_grid.json", "w"))
    print(f"grid {len(rows)} configs (SteerKP x SteerLatAccel x AccordErrorNotchQ x AccordTorqueKiHigh)")
    print()

    def best(ceil, key="shake_L", tierA=True, extra=lambda r: True):
        ok = [r for r in rows if r[key] <= ceil and extra(r)
              and (not tierA or (np.isnan(r["wc"]) or r["wc"] <= 0.50))]
        return min(ok, key=lambda r: r["metric"]) if ok else None

    def show(tag, r):
        if r is None:
            print(f"{tag:14s}  (none)")
            return
        print(f"{tag:14s} {r['metric']:6.3f} {r['closure']*100:6.1f} {r['shake_cmd']:7.3f} {r['shake_L']:6.3f} "
              f"{r['Ms']:5.2f} {str(round(r['wc'],3)) if not np.isnan(r['wc']) else '  <1  ':>6s} "
              f"{r['pm'] if not np.isnan(r['pm']) else float('nan'):4.0f} {r['kp_laf']:7.4f} | "
              f"SteerKP {r['kp']:.2f}  SteerLatAccel {r['laf']:.0f}  NotchQ {r['q']:.2f}  KiHigh {r['ki_hi']:.1f}"
              f" | lowsp x {r['lsg'][0]:.2f}/{r['lsg'][2]:.2f}/{r['lsg'][4]:.2f}")

    hdr = (f"{'ceiling':14s} {'metric':>6s} {'clos%':>6s} {'shkCmd':>7s} {'shkL':>6s} {'Ms':>5s} {'wc':>6s} "
           f"{'PM':>4s} {'kp/LAF':>7s} | config | P-gain x at 2/8/20 m/s")
    print("=" * 108)
    print("1. TIER A FRONTIER -- crossover kept <= 0.50 Hz, i.e. inside the band where the logs can")
    print("   still see loop phase (coh(Z,U) 0.79-0.91, coh(Z,M) 0.84-0.96 up to 0.5 Hz; the 55-75 ms")
    print("   delay is <= 12 deg of phase there).  These are DEFENSIBLE from the measurement.")
    print(hdr)
    for c in (0.085, 0.10, 0.12, 0.15, 0.19, 0.22, 0.25, 0.30, 0.46):
        show(f"|L|shake<={c:.3f}", best(c))
    print()
    print("   same, with the COMMAND-SHAKE ratio as the ceiling")
    print(hdr)
    for c in (0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.50):
        show(f"shake x<={c:.2f}", best(c, key="shake_cmd"))
    print()
    print("=" * 108)
    print("2. TIER A, TOGGLE-CHEAP: SteerLatAccel held at its flown 14 (SteerKP + NotchQ only)")
    print(hdr)
    for c in (0.085, 0.10, 0.12, 0.15, 0.19, 0.25, 0.30):
        show(f"|L|shake<={c:.3f}", best(c, extra=lambda r: r["laf"] == 14.0))
    print()
    print("=" * 108)
    print("3. TIER B -- crossover allowed up to 1.2 Hz.  REPORTED, NOT DEFENDED: above ~0.5 Hz the")
    print("   measured phase of L is not trustworthy (coh(Z,e) 0.19-0.42 at 1 Hz), and this is exactly")
    print("   the regime where the 55-75 ms delay starts to bind.")
    print(hdr)
    for c in (0.15, 0.19, 0.25, 0.30):
        show(f"|L|shake<={c:.3f}", best(c, tierA=False))
    print()
    print("=" * 108)
    print("4. THE TWO REQUESTED ANSWERS")
    for c, lbl in ((0.19, "at r72's proven-safe shake-band |L| = 0.19"),
                   (0.25, "at a deliberately conservative |L| = 0.25")):
        print(f"\n   {lbl}")
        for tag, ex, ta in (("toggle-cheap (LAF 14)", lambda r: r["laf"] == 14.0, True),
                            ("Tier A (LAF free)    ", lambda r: True, True),
                            ("Tier B (wc <= 1.2 Hz)", lambda r: True, False)):
            b = best(c, tierA=ta, extra=ex)
            if b is None:
                continue
            print(f"     {tag}: metric {b['metric']:.3f}  closure {b['closure']*100:.1f}%  "
                  f"cmd-shake x{b['shake_cmd']:.3f}  |L|shake {b['shake_L']:.3f}  Ms {b['Ms']:.2f}  "
                  f"wc {b['wc']:.3f} Hz PM {b['pm']:.0f}")
            print(f"        SteerKP {b['kp']:.2f} | SteerLatAccel {b['laf']:.0f} | AccordErrorNotchQ {b['q']:.2f} | "
                  f"AccordTorqueKiHigh {b['ki_hi']:.1f}   bands " + " ".join(f"{x:.3f}" for x in b["bands"]))
            print(f"        P-gain vs flown at 2/4/8/12/20/28 m/s: " + " ".join(f"{x:.2f}" for x in b["lsg"]))
    print()
    print("=" * 108)
    print("5. WHICH ELEMENT DOES THE WORK -- one at a time, then together, at |L|shake ~0.19")
    print(f"{'config':44s} {'metric':>7s} {'clos%':>6s} {'shkCmd':>7s} {'shkL':>6s} {'wc':>6s}")
    for lbl, kp, laf, kih, q in (("as flown", 1.0, 14.0, 0.0, 1.0),
                                 ("NotchQ alone 0.50", 1.0, 14.0, 0.0, 0.5),
                                 ("KiHigh alone 2.5", 1.0, 14.0, 2.5, 1.0),
                                 ("SteerKP alone 2.0 (=ARM-KP)", 2.0, 14.0, 0.0, 1.0),
                                 ("SteerKP alone 3.0 (toggle ceiling)", 3.0, 14.0, 0.0, 1.0),
                                 ("SteerLatAccel alone 8", 1.0, 8.0, 0.0, 1.0),
                                 ("SteerKP 3.0 + NotchQ 0.70", 3.0, 14.0, 0.0, 0.7),
                                 ("SteerKP 3.0 + NotchQ 0.50", 3.0, 14.0, 0.0, 0.5),
                                 ("SteerKP 3.0 + NotchQ 0.35", 3.0, 14.0, 0.0, 0.35),
                                 ("SteerKP 3.0 + LAF 10 + NotchQ 0.45", 3.0, 10.0, 0.0, 0.45),
                                 ("SteerKP 3.0 + LAF 8 + NotchQ 0.40", 3.0, 8.0, 0.0, 0.4)):
        r = row(eng, kp, laf, kih, q)
        print(f"{lbl:44s} {r['metric']:7.3f} {r['closure']*100:6.1f} {r['shake_cmd']:7.3f} {r['shake_L']:6.3f} "
              + (f"{r['wc']:6.3f}" if not np.isnan(r['wc']) else "  <1  "))
