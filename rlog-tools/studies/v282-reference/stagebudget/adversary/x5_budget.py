# -*- coding: utf-8 -*-
"""ATTACK 4 -- IS THE STAGE BUDGET ADMISSIBLE?  and the speed-matched wheel->yaw control.

The published regime-A budget is:  total lag gap (+140..+340 ms)  =  AccordRefFilter (~47-49%)
+ an UNNAMED downstream residual (+105..+158 ms at 0.15-0.30 Hz).  Three things can kill it:

  1. CLOSURE.  X->Z and Z->Y are measured separately and must sum to the separately measured X->Y.
     If they do not, the split between "ref filter" and "residual" is arithmetic on numbers that do
     not add up, and the residual is whatever the closure error happens to be.
  2. POOLING.  The torque side is nine routes flying THREE different AccordRefFilter values and four
     different (Ki, Kp, rate gain) sets.  A residual that is a property of the EPS build must appear
     in every family.  Here it is computed per family.
  3. The residual is defined against a V282 leg measured on a DIFFERENT ROAD MIX.
"""
import numpy as np
import adv_lib as L

CHI = {c: i for i, c in enumerate(["X", "Y", "Z", "W", "A", "C", "K"])}
FAM = {}
for r, d in L.ROUTES.items():
    FAM.setdefault(d["fam"], []).append(r)
ORDER = ["V282", "V282old", "RF00T", "RF06", "RF12"]


def leg(F, fr, ix, iy, f1, f2):
    return L.cell(F, CHI[ix], CHI[iy], f1, f2, fr)


def main():
    print("=" * 150)
    print("1. SPEED-MATCHED wheel -> yaw (2 m/s bins).  Pure vehicle: must be build-independent.")
    print("   Reported as H1 (biased down by wheel motion the yaw does not follow) and H2 (biased up by")
    print("   yaw the wheel does not explain).  Route-jackknife spread on H1 in brackets.")
    print("=" * 150)
    R = {r: np.load(L.OUT / f"spec_{r}_n1024.npz") for r in L.ROUTES}
    fr = R[L.V282[0]]["m_fr"]
    for f1, f2 in ((0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)):
        print(f"\n  band {f1:.2f}-{f2:.2f} Hz")
        for v0 in (6, 10, 12, 14, 16, 18, 20, 24, 28):
            v1 = v0 + 2
            out = {}
            for gn, rts in (("V282", L.V282), ("TORQ", L.TORQ)):
                Fs, per = [], []
                for r in rts:
                    m = (R[r]["m_v"] >= v0) & (R[r]["m_v"] < v1)
                    if m.sum():
                        Fs.append(R[r]["F_lin_hann"][m])
                        c1 = leg(R[r]["F_lin_hann"][m], fr, "W", "Y", f1, f2)
                        per.append(c1["H1"])
                if not Fs:
                    continue
                c = leg(np.concatenate(Fs, 0), fr, "W", "Y", f1, f2)
                out[gn] = (c, per)
            if len(out) == 2 and out["V282"][0]["nwin"] >= 5 and out["TORQ"][0]["nwin"] >= 5:
                cv, pv = out["V282"]; ct, pt = out["TORQ"]
                print(f"    v {v0}-{v1:2d}  V282 H1 {cv['H1']:7.4f} [{min(pv):.4f},{max(pv):.4f}] H2 {cv['H2']:7.4f} "
                      f"n{cv['nwin']:3d} g2 {cv['g2']:.2f} | TORQ H1 {ct['H1']:7.4f} [{min(pt):.4f},{max(pt):.4f}] "
                      f"H2 {ct['H2']:7.4f} n{ct['nwin']:3d} g2 {ct['g2']:.2f} | H1 ratio {ct['H1']/cv['H1']:5.2f}")

    print("\n" + "=" * 150)
    print("2. THE LAG BUDGET, per family, measured with a PHASE-SLOPE estimator (positive control:")
    print("   recovers a known 250 ms to 242 ms; the phase-at-band-centre construction reads 225).")
    print("   CLOSURE = (X->Z) + (Z->Y) - (X->Y).  It is zero iff the split is arithmetically legitimate.")
    print("=" * 150)
    for f1, f2, n in ((0.15, 0.30, 2048), (0.30, 0.60, 1024), (0.60, 1.20, 1024)):
        Rn = {r: np.load(L.OUT / f"spec_{r}_n{n}.npz") for r in L.ROUTES}
        frn = Rn[L.V282[0]]["m_fr"]
        print(f"\n  band {f1:.2f}-{f2:.2f} Hz, {n/100:.2f} s windows, speed 8-22 m/s")
        print(f"    {'family':8s} {'rf':>5s} {'ki':>5s} {'kp':>5s} {'n':>4s} {'X->Y':>8s} {'X->Z':>8s} "
              f"{'Z->Y':>8s} {'closure':>8s} {'2*RF':>6s} {'X->Z-2RF':>9s} {'resid vs V282':>14s}")
        base = None
        rows = []
        for fam in ORDER:
            if fam not in FAM:
                continue
            Fs = []
            for r in FAM[fam]:
                m = (Rn[r]["m_v"] >= 8) & (Rn[r]["m_v"] < 22)
                if m.sum():
                    Fs.append(Rn[r]["F_lin_hann"][m])
            if not Fs:
                continue
            F = np.concatenate(Fs, 0)
            xy = leg(F, frn, "X", "Y", f1, f2)
            xz = leg(F, frn, "X", "Z", f1, f2)
            zy = leg(F, frn, "Z", "Y", f1, f2)
            d = L.ROUTES[FAM[fam][0]]
            rows.append((fam, d, xy, xz, zy))
            if fam == "V282":
                base = (xy, xz, zy)
        for fam, d, xy, xz, zy in rows:
            clo = xz["lag_gd_ms"] + zy["lag_gd_ms"] - xy["lag_gd_ms"]
            rf2 = 2000.0 * (d["rf"] or 0.0)
            resid = (zy["lag_gd_ms"] - base[2]["lag_gd_ms"]) if base else float("nan")
            print(f"    {fam:8s} {d['rf']:5.2f} {str(d['ki']):>5s} {d['kp']:5.2f} {xy['nwin']:4d} "
                  f"{xy['lag_gd_ms']:8.0f} {xz['lag_gd_ms']:8.0f} {zy['lag_gd_ms']:8.0f} {clo:+8.0f} "
                  f"{rf2:6.0f} {xz['lag_gd_ms']-rf2:9.0f} {resid:+14.0f}")

    print("\n" + "=" * 150)
    print("3. PER-ROUTE downstream leg Z->Y at 0.15-0.30 Hz vs that route's own flown parameters.")
    print("   If the 'unnamed residual' is the EPS build it is the same on every torque route.")
    print("=" * 150)
    Rn = {r: np.load(L.OUT / f"spec_{r}_n2048.npz") for r in L.ROUTES}
    frn = Rn[L.V282[0]]["m_fr"]
    print(f"    {'route':24s} {'grp':7s} {'rf':>5s} {'ki':>5s} {'kp':>5s} {'n':>4s} {'X->Y':>8s} "
          f"{'X->Z':>8s} {'Z->Y':>8s} {'closure':>8s} {'g2(Z->Y)':>9s}")
    zy_ki = []
    for r in list(L.V282) + list(L.TORQ):
        m = (Rn[r]["m_v"] >= 8) & (Rn[r]["m_v"] < 22)
        if m.sum() < 4:
            print(f"    {r:24s} {L.ROUTES[r]['g']:7s} n<4 in 8-22 m/s")
            continue
        F = Rn[r]["F_lin_hann"][m]
        xy = leg(F, frn, "X", "Y", 0.15, 0.30)
        xz = leg(F, frn, "X", "Z", 0.15, 0.30)
        zy = leg(F, frn, "Z", "Y", 0.15, 0.30)
        d = L.ROUTES[r]
        print(f"    {r:24s} {d['g']:7s} {d['rf']:5.2f} {str(d['ki']):>5s} {d['kp']:5.2f} {xy['nwin']:4d} "
              f"{xy['lag_gd_ms']:8.0f} {xz['lag_gd_ms']:8.0f} {zy['lag_gd_ms']:8.0f} "
              f"{xz['lag_gd_ms']+zy['lag_gd_ms']-xy['lag_gd_ms']:+8.0f} {zy['g2']:9.2f}")
        if d["ki"] is not None:
            zy_ki.append((d["ki"], d["kp"], zy["lag_gd_ms"], xy["lag_gd_ms"], d["eps"]))
    if len(zy_ki) >= 6:
        a = np.array([[k, p, z, x] for k, p, z, x, e in zy_ki])
        tq = np.array([e == "V293" for *_, e in zy_ki])
        print(f"\n    corr(flown Ki, Z->Y lag) over all {len(a)} routes: {np.corrcoef(a[:,0], a[:,2])[0,1]:+.3f}")
        print(f"    corr(flown Ki, Z->Y lag) over the {tq.sum()} TORQUE routes only: "
              f"{np.corrcoef(a[tq,0], a[tq,2])[0,1]:+.3f}")
        print(f"    corr(flown Kp, Z->Y lag) over the {tq.sum()} TORQUE routes only: "
              f"{np.corrcoef(a[tq,1], a[tq,2])[0,1]:+.3f}")


if __name__ == "__main__":
    main()
