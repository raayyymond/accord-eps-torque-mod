# -*- coding: utf-8 -*-
"""D2 -- how far up in frequency the identification is actually trustworthy, and what K_tot is made of.

(a) coherence profile of the IV estimate per group  -> the honest upper edge of the measurable band
(b) plant per unit TORQUE (not per unit output-lataccel), which is the frame the two EPS firmwares
    are comparable in, since the fork changed SteerLatAccel 6 -> 14 at the same time
(c) the decomposition of K_tot into PID / rate loop / observer, at the flown settings
"""
import json
import numpy as np
import dlib as D
from d1_ident import k_tot, mode_hz

FQ = np.array([0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0])


def main():
    res = json.load(open(D.OUT / "d1_hi.json"))
    print("(a) IV coherence vs frequency (reference -> output), >=15 m/s")
    print(f"{'route':22s} {'grp':8s} " + " ".join(f"{x:>6.2f}" for x in FQ))
    for rt, v in res.items():
        f = np.array(v["f"]); c = D.smooth_c(np.array(v["coh_ry"]))
        print(f"{rt:22s} {v['cfg']['g']:8s} " + " ".join(f"{np.interp(x, f, c):6.2f}" for x in FQ))

    print("\n(b) PLANT per unit TORQUE  |P_tq| = |P_la| * LAF   [m/s^2 measured per unit command torque]")
    print(f"{'route':22s} {'grp':8s} {'LAF':>5s} " + " ".join(f"{x:>6.2f}" for x in FQ[:8])
          + "   phase at 0.2/0.4/0.8/1.2 Hz")
    fam = {}
    for rt, v in res.items():
        f = np.array(v["f"]); P = np.array(v["P_re"]) + 1j * np.array(v["P_im"])
        laf = v["cfg"]["laf"]
        mag = [float(np.interp(x, f, np.abs(P))) * laf for x in FQ[:8]]
        ph = [float(np.degrees(np.interp(x, f, np.unwrap(np.angle(P))))) for x in (0.2, 0.4, 0.8, 1.2)]
        print(f"{rt:22s} {v['cfg']['g']:8s} {laf:5.1f} " + " ".join(f"{x:6.2f}" for x in mag)
              + "   " + " ".join(f"{x:6.0f}" for x in ph))
        key = "V282" if v["cfg"]["g"].startswith("V282") else "TORQUE"
        fam.setdefault(key, []).append(mag)
    print()
    for k, rows in fam.items():
        a = np.array(rows)
        print(f"  {k:8s} median " + " ".join(f"{x:6.2f}" for x in np.median(a, axis=0))
              + "   (n={})".format(len(rows)))
    if "V282" in fam and "TORQUE" in fam:
        r = np.median(np.array(fam["TORQUE"]), axis=0) / np.median(np.array(fam["V282"]), axis=0)
        print(f"  {'ratio T/V':8s}        " + " ".join(f"{x:6.2f}" for x in r))

    print("\n(c) K_tot = -dU/dM, decomposed, at each route's own flown settings and median speed")
    print(f"{'route':22s} {'grp':8s} {'v':>5s} " + " ".join(
        f"{x:>7s}" for x in ("|K|0.3", "|Kp|", "|Kr|", "|Kd|", "|K|0.9", "|Kp|", "|Kr|", "|Kd|",
                             "|K|2.5", "|Kp|", "|Kr|", "|Kd|")))
    for rt, v in res.items():
        cfg = v["cfg"]
        f = np.array([0.3, 0.9, 2.5])
        K, Cp, Cr, num, den = k_tot(f, cfg, v["v"], v["k_m"], parts=True)
        row = []
        for i in range(3):
            row += [abs(K[i]), abs(Cp[i]), abs(Cr[i]), abs(num[i] / den[i])]
        print(f"{rt:22s} {cfg['g']:8s} {v['v']:5.1f} " + " ".join(f"{x:7.3f}" for x in row))

    print("\n(d) |L| and |S| per exposure band at the FLOWN settings (coherence-gated, <=1.5 Hz)")
    print(f"{'route':22s} {'grp':8s} " + " ".join(f"{x:>9s}" for x in
          ("L.15-.3", "L.3-.6", "L.6-1.2", "S.15-.3", "S.3-.6", "S.6-1.2", "Ms")))
    for rt, v in res.items():
        f = np.array(v["f"]); P = np.array(v["P_re"]) + 1j * np.array(v["P_im"])
        valid = np.array(v["valid"]) & (D.smooth_c(np.array(v["coh_ry"])) > 0.5)
        K = k_tot(f, v["cfg"], v["v"], v["k_m"])
        m = D.loop_metrics(f, K * P, valid, fmax=1.5)
        if m is None:
            print(f"{rt:22s} {v['cfg']['g']:8s}  (no valid band)"); continue
        print(f"{rt:22s} {v['cfg']['g']:8s} " + " ".join(f"{m[k]:9.3f}" for k in
              ("L0.15_0.3", "L0.3_0.6", "L0.6_1.2", "S0.15_0.3", "S0.3_0.6", "S0.6_1.2", "Ms")))


if __name__ == "__main__":
    main()
