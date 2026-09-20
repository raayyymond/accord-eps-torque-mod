# -*- coding: utf-8 -*-
"""D7 -- the TRADE CURVE: tracking vs shake-band gain, over (SteerKP, AccordErrorNotchQ).

Two axes, both plain float toggles:
  SteerKP            raises the P path at EVERY frequency, including 1.8-3.5 Hz
  AccordErrorNotchQ  the notch already sitting on the steering mode (1.9-2.1 Hz at >=15 m/s).
                     LOWER Q = WIDER notch = more of the shake band removed from the P path --
                     but it also eats into 0.6-1.2 Hz, which is the band carrying 64 % of the gap.

The shake-band currency is |K_P| at 1.8-3.5 Hz, which d6 MEASURED on every route and which matched
SteerKP*(1+lsf)*|notch| on all 15 (0.43 measured vs 0.43 predicted at kp 0.30; 0.965 vs 0.98 at kp
0.85 no notch; 0.37-0.59 vs 0.54 at kp 1.0 with the notch).  So this axis is calibrated, not modelled.

The tracking currency is |S| in the study's exposure bands, from d1's identified plant.
"""
import json
import numpy as np
import dlib as D
from d1_ident import k_tot, mode_hz

FMAX, COH = 1.2, 0.50
SHK = np.linspace(1.8, 3.5, 40)


def notch(f, fn, q):
    if q <= 0 or fn <= 0:
        return np.ones_like(np.asarray(f, float), dtype=complex)
    s = 1j * 2 * np.pi * np.asarray(f, float)
    wn = 2 * np.pi * fn
    return (s ** 2 + wn ** 2) / (s ** 2 + (wn / q) * s + wn ** 2)


def main():
    res = json.load(open(D.OUT / "d1_hi.json"))
    meas = {r["rt"]: r for r in json.load(open(D.OUT / "d6_shakeloop.json"))}
    routes = [k for k, v in res.items() if v["cfg"]["g"] in ("T5", "T64", "T64B")]
    tgt = {}
    for k in ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2"):
        tgt[k] = float(np.median([D.loop_metrics(np.array(v["f"]),
                        k_tot(np.array(v["f"]), v["cfg"], v["v"], v["k_m"])
                        * (np.array(v["P_re"]) + 1j * np.array(v["P_im"])),
                        np.array(v["valid"]) & (D.smooth_c(np.array(v["coh_ry"])) > COH),
                        fmax=FMAX)[k] for vv, v in res.items() if v["cfg"]["g"] == "V282"]))
    print("V282's measured |S|:  0.15-0.30 {:.3f}   0.30-0.60 {:.3f}   0.60-1.20 {:.3f}"
          .format(*[tgt[k] for k in ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2")]))
    print("\nFLOWN shake-band |K_P| (1.8-3.5 Hz), MEASURED per route, rev 5 / rev 6.4:")
    base_kp = []
    for rt in routes:
        print(f"   {rt}  measured |K_P| {meas[rt]['KP']:.3f}   total measured |K| {meas[rt]['K']:.3f}"
              f"   K_P share {meas[rt]['KP']/meas[rt]['K']:.2f}")
        base_kp.append(meas[rt]["KP"])
    base = float(np.median(base_kp))
    print(f"   -> baseline |K_P| = {base:.3f} (median).  A dose must not raise this if the shake"
          f" constraint is to be respected as flown.")

    print("\nTRADE TABLE. Each cell: |S| 0.15-0.30 / 0.30-0.60 / 0.60-1.20  ||  shake-band |K_P|"
          f" (x flown)")
    qs = [0.0, 0.35, 0.5, 0.7, 1.0, 1.5, 3.0]
    kps = [1.0, 1.5, 2.0, 2.5, 3.0]
    print(f"{'':>6s} " + "".join(f"{('Q=off' if q==0 else f'Q={q:g}'):>34s}" for q in qs))
    grid = {}
    for kpm in kps:
        cells = []
        for q in qs:
            S1 = S2 = S3 = []
            rows, kpshk = [], []
            for rt in routes:
                v = res[rt]
                f = np.array(v["f"])
                P = np.array(v["P_re"]) + 1j * np.array(v["P_im"])
                valid = np.array(v["valid"]) & (D.smooth_c(np.array(v["coh_ry"])) > COH)
                cfg = dict(v["cfg"]); cfg["nq"] = q
                K = k_tot(f, cfg, v["v"], v["k_m"], kp_mult=kpm)
                m = D.loop_metrics(f, K * P, valid, fmax=FMAX)
                if m:
                    rows.append(m)
                fn = mode_hz(v["v"])
                lsf = D.low_speed_factor(v["v"])
                kpshk.append((cfg["kp"] * kpm + lsf) * np.mean(np.abs(notch(SHK, fn, q)))
                             / ((cfg["kp"] + lsf) * np.mean(np.abs(notch(SHK, fn, v["cfg"]["nq"])))))
            g = lambda k: float(np.median([r[k] for r in rows]))
            cells.append((g("S0.15_0.3"), g("S0.3_0.6"), g("S0.6_1.2"), float(np.median(kpshk))))
            grid[(kpm, q)] = cells[-1]
        print(f"kp x{kpm:<4g} " + "".join(
            f"  {a:.3f}/{b:.3f}/{c:.3f} ||{d:6.2f}x   " for a, b, c, d in cells))

    print("\nWHICH CELLS MEET BOTH CONSTRAINTS")
    print("  constraint 1: |S| at least as good as V282 in the band being fixed")
    print("  constraint 2: shake-band |K_P| NOT above what has already flown (<= 1.00x)")
    ok = []
    for (kpm, q), (s1, s2, s3, kx) in sorted(grid.items()):
        c1 = s1 <= tgt["S0.15_0.3"]
        c2 = s2 <= tgt["S0.3_0.6"]
        c3 = s3 <= tgt["S0.6_1.2"]
        if kx <= 1.001 and (c1 or c2 or c3):
            ok.append((kpm, q, s1, s2, s3, kx, c1 + c2 + c3))
    if not ok:
        print("  NONE.")
    for kpm, q, s1, s2, s3, kx, n in sorted(ok, key=lambda x: -x[6]):
        print(f"  SteerKP x{kpm:<4g} Q={q:<4g}  |S| {s1:.3f}/{s2:.3f}/{s3:.3f}"
              f"  shake |K_P| {kx:.2f}x  -> beats V282 in {n}/3 bands")

    print("\nNOTCH COST, for reference: |notch(f)| at each Q, at the 1.9-2.1 Hz mode")
    fn = float(np.median([mode_hz(res[r]["v"]) for r in routes]))
    print(f"  mode {fn:.2f} Hz")
    print(f"{'Q':>6s} " + " ".join(f"{x:>8s}" for x in
          ("0.2 Hz", "0.45", "0.9", "1.2", "1.9", "2.5", "3.5")))
    for q in qs:
        vals = [abs(notch(np.array([x]), fn, q)[0]) for x in (0.2, 0.45, 0.9, 1.2, 1.9, 2.5, 3.5)]
        print(f"{('off' if q==0 else f'{q:g}'):>6s} " + " ".join(f"{x:8.3f}" for x in vals))
    json.dump({f"{k[0]}_{k[1]}": v for k, v in grid.items()}, open(D.OUT / "d7_trade.json", "w"),
              indent=1)


if __name__ == "__main__":
    main()
