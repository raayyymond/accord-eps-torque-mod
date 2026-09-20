# -*- coding: utf-8 -*-
"""ADV4: the loop, re-identified from the logs by this stream alone, and what it does to the asymptote.

C is not estimated -- it is written out from the fork source at the flown commit (84766cdc) and each
route's own flown params, so only the PLANT is measured:

  p        = (kp + lsf(v)) * N(s) * error                       latcontrol_torque.py:339-348
  i       += ki(v) * (1 + lsf(v)/kp) * N(s) * error * dt
  U        = (p + i + f) / LAF                                  (output_torque, +demand polarity)
  C(s)     = N(s) * [ (kp+lsf) + ki*(1+lsf/kp)/s ] / LAF        torque per m/s^2
  N        = HondaAccordErrorNotch, bilinear, centre get_honda_accord_mode_hz(v), Q from the toggle
  P(f)     = M / U, instrument X (exogenous to road disturbance and pose noise)
  L        = P*C ,  S = 1/(1+L)

THEN, the attacks:
  (a) J(k) for the whole gain sweep with the COMPLEX sensitivity ratio (1+L)/(1+kL), which is what the
      identity requires, and with its MAGNITUDE, which is what a magnitude-per-bin budget would use.
      J(1) must return the flown J exactly -- that is the built-in positive control.
  (b) Is J(k) monotone?  'Asymptote at infinite gain' is only meaningful if it is.
  (c) Where does |S| exceed 1 (the waterbed), and how much of the metric band is on the wrong side?
  (d) The STABILITY ceiling: k at which the shake band's |L| reaches r71's flown limit-cycle anchor.
  (e) The NOTCH CEILING: an error-path notch cannot push |S| below 1, so the most any notch can remove
      is the error power the loop is currently ADDING.  That is computed here as a hard upper bound.
"""
import json
import sys

import numpy as np

import advlib as A

T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
NPS = 1024
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
SHAKE = (1.8, 3.5)
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
EPS_INERTIA = 8e-5


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / EPS_INERTIA) / (2 * np.pi)


def notch_H(fr, f0, q, fs=A.FS):
    """Exact transfer of HondaAccordErrorNotch at the logged sample rate (latcontrol_vehicle_tunes.py:2668)."""
    if q <= 0 or f0 <= 0:
        return np.ones(len(fr), complex)
    dt = 1.0 / fs
    k = np.tan(np.pi * min(f0, 0.45 / dt) * dt)
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    z = np.exp(-2j * np.pi * fr / fs)
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def C_of(fr, v, meta, q=1.0):
    """Controller transfer, torque per m/s^2, at one window's speed."""
    ls = A.lsf(v)
    kp, laf, ki = meta["kp"], meta["laf"], meta["ki"]
    if meta["ki_hi"] > 0:                        # HONDA_ACCORD_KI_SCHEDULE, rev 4 only
        ki = float(np.interp(v, [8.0, 18.0], [meta["ki"], meta["ki_hi"]]))
    s = 2j * np.pi * np.maximum(fr, 1e-6)
    N = notch_H(fr, mode_hz(v), q) if meta["notch"] else np.ones(len(fr), complex)
    return N * ((kp + ls) + ki * (1 + ls / max(kp, 1e-3)) / s) / laf


def gather(rks):
    sp = {k: [] for k in ("X", "Z", "M", "Y", "U")}
    vs, rkl = [], []
    fr = None
    for rk in rks:
        N = A.load_nodes(rk)
        f, s, v = A.windows(N, nperseg=NPS, overlap=0.5, minrun=30.0)
        fr = f
        for k in sp:
            sp[k].append(s[k])
        vs.append(v); rkl += [rk] * len(v)
        del N, s
    return fr, {k: np.concatenate(v_) for k, v_ in sp.items()}, np.concatenate(vs), np.array(rkl)


def main():
    fr, sp, vs, rkl = gather(T64)
    sel = A.bandsel(fr)
    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    E, D = X - Y, Z - M
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    J0 = float(np.sum(np.abs(E[:, sel]) ** 2) / den)
    print(f"T64: {len(vs)} windows, median v {np.median(vs):.1f} m/s, J as flown {J0:.3f}")

    # ---- plant, two brackets --------------------------------------------------------------
    P_iv = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    P_dir = np.sum(np.conj(U) * M, 0) / np.sum(np.conj(U) * U, 0)
    coh_XU = np.abs(np.sum(np.conj(X) * U, 0)) ** 2 / (np.sum(np.abs(X) ** 2, 0) * np.sum(np.abs(U) ** 2, 0))
    print("\nPLANT U->M and the coherence that licenses it:")
    print(f"  {'band':>12s} {'|P| IV':>8s} {'|P| dir':>8s} {'ph IV':>7s} {'coh(X,U)':>9s}")
    for b1, b2 in BANDS + [SHAKE]:
        s = (fr >= b1) & (fr < b2)
        w = np.sum(np.abs(X[:, s]) ** 2, 0)
        print(f"  {b1:5.2f}-{b2:4.2f} {np.average(np.abs(P_iv[s]), weights=w):8.2f} "
              f"{np.average(np.abs(P_dir[s]), weights=w):8.2f} "
              f"{np.degrees(np.angle(np.sum(np.conj(X[:, s])*M[:, s])/np.sum(np.conj(X[:, s])*U[:, s]))):7.0f} "
              f"{np.average(coh_XU[s], weights=w):9.3f}")

    # ---- loop, per window (speed enters through lsf, the ki schedule and the notch centre) --
    metas = {rk: A.FLOWN[rk] for rk in T64}
    Cw = np.array([C_of(fr, v, metas[rk]) for v, rk in zip(vs, rkl)])
    L = P_iv[None, :] * Cw
    S = 1.0 / (1.0 + L)
    print("\nLOOP, per band (power-weighted over windows):")
    print(f"  {'band':>12s} {'|L|':>7s} {'ph L':>7s} {'|S|':>7s} {'frac |S|>1':>11s}")
    wl = np.abs(X) ** 2
    for b1, b2 in BANDS + [SHAKE]:
        s = (fr >= b1) & (fr < b2)
        w = wl[:, s]
        print(f"  {b1:5.2f}-{b2:4.2f} {np.average(np.abs(L[:, s]), weights=w):7.3f} "
              f"{np.degrees(np.angle(np.average(L[:, s], weights=w))):7.0f} "
              f"{np.average(np.abs(S[:, s]), weights=w):7.3f} "
              f"{float(np.mean(np.abs(S[:, s]) > 1.0)):11.3f}")

    # ---- the residual leg, exact identity -------------------------------------------------
    Vh = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)     # LS wheel-angle -> achieved
    Ares = E - Vh[None, :] * D
    assert np.max(np.abs(Ares + Vh[None, :] * D - E)) < 1e-9 * np.max(np.abs(E)), "identity broken"

    def J_at(k, complex_scale=True):
        r = (1.0 + L) / (1.0 + k * L)
        if not complex_scale:
            r = np.abs(r).astype(complex)
        Ek = Ares + Vh[None, :] * (D * r)
        return float(np.sum(np.abs(Ek[:, sel]) ** 2) / den)

    print("\n(a)+(b) J(k) ALONG THE WHOLE SWEEP.  k = SteerKP multiplier (kp 1.0 -> k, LAF fixed 14).")
    print("    positive control: J(1) must equal the flown J exactly.")
    ks = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 10.0, 30.0, 100.0, 1e4]
    JV = 0.444
    print(f"  {'k':>7s} {'SteerKP':>8s} {'J complex':>10s} {'clos %':>7s} {'J |.|':>8s} {'clos %':>7s} "
          f"{'|L| 1.8-3.5':>12s} {'max|S| band':>12s}")
    rows = []
    ssh = (fr >= SHAKE[0]) & (fr < SHAKE[1])
    for k in ks:
        jc, jm = J_at(k, True), J_at(k, False)
        lsh = float(np.average(np.abs(k * L[:, ssh]), weights=wl[:, ssh]))
        Sk = 1.0 / (1.0 + k * L)
        mx = float(np.max(np.abs(Sk[:, sel])))
        rows.append(dict(k=k, J=jc, Jmag=jm, Lshake=lsh, maxS=mx))
        print(f"  {k:7.2f} {k:8.2f} {jc:10.3f} {100*(J0-jc)/(J0-JV):7.1f} {jm:8.3f} "
              f"{100*(J0-jm)/(J0-JV):7.1f} {lsh:12.3f} {mx:12.2f}")
    jj = [r["J"] for r in rows]
    kmin = rows[int(np.argmin(jj))]["k"]
    print(f"  => J(k) minimum inside the sweep at k = {kmin:g}; monotone to infinity: {bool(np.argmin(jj) == len(jj)-1)}")

    # ---- (d) the stability ceiling from the flown anchors ----------------------------------
    l1 = float(np.average(np.abs(L[:, ssh]), weights=wl[:, ssh]))
    print(f"\n(d) STABILITY CEILING FROM FLOWN ANCHORS.  shake-band |L| as flown = {l1:.3f}.")
    for anchor, note in ((0.46, "r71 LIMIT-CYCLED at 2.34 Hz"), (0.19, "r72 flew with no shake complaint")):
        print(f"    reaching |L| = {anchor:.2f} ({note}) needs k = {anchor/l1:.2f}  -> SteerKP {anchor/l1:.2f}")
    kc = 0.46 / l1
    jc = J_at(kc)
    print(f"    at that k the metric is {jc:.3f} = {100*(J0-jc)/(J0-JV):.1f} % closure "
          f"-- the largest closure this class reaches before the one flown instability anchor.")

    # ---- (e) the notch ceiling -------------------------------------------------------------
    print("\n(e) NOTCH CEILING.  An error-path notch removes feedback; it cannot make |S| < 1, so the most")
    print("    it can remove is the error power the loop is currently ADDING (|S|>1 bins).")
    tot = float(np.sum(np.abs(E[:, sel]) ** 2))
    for b1, b2 in [(1.2, 2.4), (0.6, 2.4), (0.15, 2.4)]:
        s = (fr >= b1) & (fr < b2)
        Sm = np.abs(S[:, s])
        red = np.abs(E[:, s]) ** 2 * np.maximum(0.0, 1.0 - 1.0 / np.maximum(Sm, 1e-9) ** 2) * (Sm > 1)
        print(f"    notch spanning {b1:.2f}-{b2:.2f} Hz: bins with |S|>1 = {100*np.mean(Sm>1):5.1f} %, "
              f"max |S| = {Sm.max():.2f}, best-case power removed = {100*red.sum()/tot:5.2f} % of the error "
              f"=> J {J0:.3f} -> {(tot-red.sum())/den:.3f}, closure {100*(J0-(tot-red.sum())/den)/(J0-JV):5.1f} %")

    json.dump(dict(J0=J0, sweep=rows, Lshake=l1), open(A.OUT / "adv4_loop.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
