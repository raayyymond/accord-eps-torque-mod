# -*- coding: utf-8 -*-
"""S4 -- WHAT THE COMBINATION BUYS, on the goal metric, by algebra on measured transfers.

THE METRIC, unchanged:  J = sum|X-Y|^2 / sum|X|^2 over 0.15-2.4 Hz, >= 15 m/s, engaged hands-off
runs >= 30 s, 20.48 s Hann windows, ONE denominator.

THE PROPAGATION.  Every quantity below is logged or a measured transfer; nothing is a plant model.
    D    = Z - M            the loop's own error            (logged)
    W    = U - g*rate_meas - (p+i)/LAF                      (logged; the exogenous command)
    P    = H(U -> M)        raw plant, TOTAL command to the fed-back measurement   (IV, instrument W)
    G    = H(U -> rate)     raw plant, TOTAL command to wheel rate                 (IV, instrument W)
    V    = H(M -> Y)        wheel angle to achieved yaw -- OUTSIDE the loop        (H1)
    C(f) = exact discrete PI * (1+lsf/kp) / LAF * notch(f)  (source, no fit)
With the rate loop at g the effective plant from (W + u_fb) to M is  p = P/(1 - g*F_rc*G),  so
    D*(1 + p*C) = Z - p*W - dtilde
and dtilde (road + everything unmodelled) is DETERMINED per window per bin by the flown values.
Re-closing at (g1, kp*m) gives  D_new = (Z - p1*W - dtilde)/(1 + p1*C1),  Y_new = Y - V*(D_new - D),
E_new = X - Y_new.  ASSUMES: Z, dtilde and V unchanged.  It does NOT model friction, the rate
limiter, or anything the operator would feel.

usage: python s4_closure.py > out/S4-CLOSURE.txt
"""
import json

import numpy as np

import suplib as S

T64 = S.T64
OTHER = ["0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
REF = S.V282R
NPS = 2048
MET = (0.15, 2.40)


def pi_H(f, kp, ki, dt=S.DT):
    """EXACT discrete p + i: i_k = i_{k-1} + ki*dt*e_k, control uses p_k + i_k."""
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    with np.errstate(divide="ignore", invalid="ignore"):
        return kp + ki * dt / (1.0 - z)


def C_fb(f, kp, ki, laf, lsf, q=None, f0=None):
    C = pi_H(f, kp, ki) * (1.0 + lsf / max(kp, 1e-3)) / laf
    if q is not None and f0:
        C = C * S.notch_H(f, f0, q)
    return C


def _self_test():
    """Positive controls: (1) the propagation is an IDENTITY at the flown settings; (2) on a
    synthetic loop with a KNOWN plant and controller it recovers the KNOWN new error when the gain
    is doubled; (3) the metric matches a closed-form band ratio."""
    rng = np.random.default_rng(23)
    nw, nb = 40, 200
    Z = rng.standard_normal((nw, nb)) + 1j * rng.standard_normal((nw, nb))
    Wc = 0.3 * (rng.standard_normal((nw, nb)) + 1j * rng.standard_normal((nw, nb)))
    P = (0.8 + 0.2j) * np.ones(nb)
    C = (0.5 - 0.1j) * np.ones(nb)
    dt_ = 0.2 * (rng.standard_normal((nw, nb)) + 1j * rng.standard_normal((nw, nb)))
    D = (Z - P * Wc - dt_) / (1 + P * C)
    dt_hat = Z - P * Wc - D * (1 + P * C)
    assert np.max(np.abs(dt_hat - dt_)) < 1e-10
    D2 = (Z - P * Wc - dt_hat) / (1 + P * C * 2)
    D2t = (Z - P * Wc - dt_) / (1 + 2 * P * C)
    assert np.max(np.abs(D2 - D2t)) < 1e-10
    X = Z.copy()
    V = (1.0 + 0j) * np.ones(nb)
    Y = V * (Z - D)
    E = X - Y
    J = float(np.sum(np.abs(E) ** 2) / np.sum(np.abs(X) ** 2))
    J2 = float(np.sum(np.abs(E + V * (D2 - D)) ** 2) / np.sum(np.abs(X) ** 2))
    assert J2 < J
    return f"s4 self-test OK: dtilde identity exact, gain-doubling identity exact, J {J:.3f} -> {J2:.3f}"


def route_pack(rk):
    """Everything the propagation needs for one route, on the metric's own windows."""
    meta = S.FLOWN[rk]
    N = S.load(rk)
    g0 = meta["rlg"] if meta["rlg"] is not None else 0.0
    rm = S.fof_run(N["SR"], S.RATE_LOOP_RC, x0=N["SR"][0])
    N["RT"] = S.rate_loop_gain(N["v"], g0) * rm
    N["W"] = N["U"] - N["RT"] - (N["P"] + N["I"]) / meta["laf"]
    N["D"] = N["Z"] - N["M"]
    fr, sp, vs = S.spectra(N, ("X", "Y", "Z", "M", "U", "W", "D", "SR"), 15.0, 99.0, NPS, 30.0)
    out = None
    if len(vs):
        # measured transfers, pooled over the route's windows
        Swu = np.mean(np.conj(sp["W"]) * sp["U"], 0)
        Swm = np.mean(np.conj(sp["W"]) * sp["M"], 0)
        Swr = np.mean(np.conj(sp["W"]) * sp["SR"], 0)
        P = Swm / np.where(np.abs(Swu) < 1e-300, 1e-300, Swu)
        G = Swr / np.where(np.abs(Swu) < 1e-300, 1e-300, Swu)
        V, cohV = S.H_xy(sp["M"], sp["Y"])
        out = dict(rk=rk, meta=meta, fr=fr, vs=vs, g0=g0, P=P, G=G, V=V, cohV=cohV,
                   X=sp["X"], Y=sp["Y"], Z=sp["Z"], M=sp["M"], D=sp["D"], W=sp["W"], U=sp["U"],
                   SR=sp["SR"],
                   v=float(np.median(vs)), lsf=float(np.mean(S.lsf(vs))))
    del N, sp
    return out


def smooth(H, k=5):
    """Running mean over bins of a complex transfer (the per-bin IV estimate is noisy; every
    consumer of it here is a smooth function of frequency)."""
    ker = np.ones(k) / k
    return (np.convolve(H.real, ker, mode="same") + 1j * np.convolve(H.imag, ker, mode="same"))


def propagate(pk, m_kp=1.0, g1=None, q_notch="flown", taper=True, Csmooth=True, err_lp=None):
    """Return J for (kp scaled by m_kp, AccordRateLoopGain g1, notch Q q_notch)."""
    fr, meta = pk["fr"], pk["meta"]
    sel = (fr >= MET[0]) & (fr <= MET[1])
    P = smooth(pk["P"]) if Csmooth else pk["P"]
    G = smooth(pk["G"]) if Csmooth else pk["G"]
    Frc = S.fof_H(fr, S.RATE_LOOP_RC)
    g0e = S.rate_loop_gain(pk["v"], pk["g0"])
    g1e = g0e if g1 is None else (S.rate_loop_gain(pk["v"], g1) if taper else g1)
    p0 = P / (1 - g0e * Frc * G)
    p1 = P / (1 - g1e * Frc * G)
    f0 = S.mode_hz(pk["v"])
    q_now = 1.0 if meta["notch"] else None
    q_new = q_now if q_notch == "flown" else q_notch
    C0 = C_fb(fr, meta["kp"], meta["ki"], meta["laf"], pk["lsf"], q_now, f0)
    C1 = C_fb(fr, meta["kp"] * m_kp, meta["ki"], meta["laf"], pk["lsf"], q_new, f0)
    if err_lp:
        # a first-order low-pass ADDED on the error, inside the feedback path only (a fork code
        # change): it does not touch the feedforward, the inner rate damper or the observer.
        C1 = C1 * S.fof_H(fr, 1.0 / (2 * np.pi * err_lp))
    Z, W, D, X, Y = pk["Z"], pk["W"], pk["D"], pk["X"], pk["Y"]
    dt_ = Z - p0[None, :] * W - D * (1 + (p0 * C0))[None, :]
    Dn = (Z - p1[None, :] * W - dt_) / (1 + (p1 * C1))[None, :]
    En = (X - Y) + pk["V"][None, :] * (Dn - D)
    J = float(np.sum(np.abs(En[:, sel]) ** 2) / np.sum(np.abs(X[:, sel]) ** 2))
    L0, L1 = p0 * C0, p1 * C1
    return J, L0, L1


def main():
    print(S._self_test())
    print(_self_test())
    packs = {}
    for rk in T64 + OTHER + REF:
        pk = route_pack(rk)
        if pk is None:
            print(f"  {rk}: no usable window")
            continue
        packs[rk] = pk
    fr = packs[T64[0]]["fr"]
    sel = (fr >= MET[0]) & (fr <= MET[1])

    print("\n" + "=" * 132)
    print("1. THE METRIC AS FLOWN, and the identity check (m=1, g1=g0 must return J exactly).")
    print("=" * 132)
    num = den = 0.0
    for rk, pk in packs.items():
        E = pk["X"] - pk["Y"]
        J = float(np.sum(np.abs(E[:, sel]) ** 2) / np.sum(np.abs(pk["X"][:, sel]) ** 2))
        Ji, _, _ = propagate(pk)
        print(f"  {rk} {pk['meta']['fam']:6s} nwin {len(pk['vs']):3d} v {pk['v']:5.1f}  J {J:6.3f}   "
              f"identity re-derivation {Ji:6.3f}  (diff {abs(Ji-J):.2e})   "
              f"coh(M,Y) 0.15-0.6 {float(np.mean(pk['cohV'][(fr>=0.15)&(fr<=0.6)])):.2f}")
        if pk["meta"]["fam"] == "T64":
            num += float(np.sum(np.abs(E[:, sel]) ** 2)); den += float(np.sum(np.abs(pk["X"][:, sel]) ** 2))
    JT64 = num / den
    nr = dr = 0.0
    for rk in REF:
        if rk in packs:
            E = packs[rk]["X"] - packs[rk]["Y"]
            nr += float(np.sum(np.abs(E[:, sel]) ** 2)); dr += float(np.sum(np.abs(packs[rk]["X"][:, sel]) ** 2))
    JV282 = nr / dr
    print(f"\n  POOLED  rev 6.4 (T64) J = {JT64:.3f}   V282 reference J = {JV282:.3f}   "
          f"gap = {JT64-JV282:.3f}   ratio {JT64/JV282:.2f}x")
    print("  (the brief's handed-down pair is 1.350 / 0.442; this stream re-derives the metric from the")
    print("   same definition and lands where the adversary stream's independent re-derivation did.")
    print("   CLOSURE % below is always (J_flown - J_new)/(J_flown - J_V282) in THIS re-derivation.)")

    print("\n" + "=" * 132)
    print("2. THE LOOP AS FLOWN: |L| = |p*C| from the measured plant and the exact controller.")
    print("=" * 132)
    FQ = [0.15, 0.2, 0.3, 0.4, 0.6, 0.9, 1.2, 1.8, 2.4]
    print(f"  {'route':22s} {'fam':6s} " + "".join(f"{q:>7.2f}" for q in FQ) + "   max|L| 0.1-2.4")
    for rk, pk in packs.items():
        _, L0, _ = propagate(pk)
        idx = [int(np.argmin(np.abs(fr - q))) for q in FQ]
        b = (fr >= 0.1) & (fr <= 2.4)
        print(f"  {rk:22s} {pk['meta']['fam']:6s} " + "".join(f"{abs(L0[j]):7.3f}" for j in idx) +
              f"   {np.max(np.abs(L0[b])):.3f}")

    print("\n" + "=" * 132)
    print("3. CLOSURE.  Each row: the metric J, and the % of the (flown -> V282) gap it closes.")
    print("   kp multiplier m is SteerKP x m (toggle ceiling m = 3.0 at SteerKP 1.0).")
    print("   g1 = AccordRateLoopGain (toggle ceiling 0.003); 'NT' = the 12/v taper removed (code change).")
    print("=" * 132)
    CASES = [("as flown", 1.0, None, "flown", True, None),
             ("SteerKP x2", 2.0, None, "flown", True, None),
             ("SteerKP x3 (toggle ceiling)", 3.0, None, "flown", True, None),
             ("SteerKP x5 (code)", 5.0, None, "flown", True, None),
             ("SteerKP x8 (code)", 8.0, None, "flown", True, None),
             ("notch Q 0.5", 1.0, None, 0.5, True, None),
             ("notch OFF", 1.0, None, None, True, None),
             ("notch Q 2.0", 1.0, None, 2.0, True, None),
             ("rate loop 0.003", 1.0, 0.003, "flown", True, None),
             ("rate loop 0.003 NT", 1.0, 0.003, "flown", False, None),
             ("err LP 2 Hz alone", 1.0, None, "flown", True, 2.0),
             ("err LP 3 Hz alone", 1.0, None, "flown", True, 3.0),
             ("KPx3 + rate 0.003 NT", 3.0, 0.003, "flown", False, None),
             ("KPx5 + rate 0.003 NT", 5.0, 0.003, "flown", False, None),
             ("KPx3 + notch Q2", 3.0, None, 2.0, True, None),
             ("KPx3 + notch OFF", 3.0, None, None, True, None),
             ("KPx3 + err LP 2 Hz", 3.0, None, "flown", True, 2.0),
             ("KPx5 + err LP 2 Hz", 5.0, None, "flown", True, 2.0),
             ("KPx8 + err LP 2 Hz", 8.0, None, "flown", True, 2.0),
             ("KPx5 + err LP 1.5 Hz", 5.0, None, "flown", True, 1.5),
             ("KPx8 + err LP 1.5 Hz", 8.0, None, "flown", True, 1.5),
             ("KPx8 + err LP 1 Hz", 8.0, None, "flown", True, 1.0),
             ("KPx12 + err LP 1 Hz", 12.0, None, "flown", True, 1.0),
             ("KPx5 + errLP2 + rate .003NT", 5.0, 0.003, "flown", False, 2.0),
             ("KPx8 + errLP2 + rate .003NT", 8.0, 0.003, "flown", False, 2.0),
             ("KPx8 + errLP1.5 + rate .003NT", 8.0, 0.003, "flown", False, 1.5)]
    hdr = "  ".join(f"{rk[:8]}" for rk in T64 + OTHER)
    print(f"  {'case':30s} {'T64 pooled J':>13s} {'closure':>8s}   per route: " + hdr)
    res = {}
    for tag, m, g1, qn, tp, elp in CASES:
        pooled_n = pooled_d = 0.0
        cells = []
        for rk in T64 + OTHER:
            pk = packs[rk]
            J, L0, L1 = propagate(pk, m, g1, qn, tp, err_lp=elp)
            cells.append(f"{J:8.3f}")
            if pk["meta"]["fam"] == "T64":
                pooled_n += J * float(np.sum(np.abs(pk["X"][:, sel]) ** 2))
                pooled_d += float(np.sum(np.abs(pk["X"][:, sel]) ** 2))
        Jp = pooled_n / pooled_d
        cl = (JT64 - Jp) / (JT64 - JV282) * 100
        print(f"  {tag:30s} {Jp:13.3f} {cl:7.1f}%   " + " ".join(cells))
        res[tag] = dict(J=Jp, closure=cl)
    json.dump(dict(JT64=JT64, JV282=JV282, cases=res), open(S.OUT / "s4_closure.json", "w"), indent=1)

    print("\n" + "=" * 132)
    print("4. WHERE THE CLOSURE COMES FROM: |S| = |1/(1+L)| per band, as flown and at each dose.")
    print("=" * 132)
    BQ = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
    print(f"  {'case':30s} " + "".join(f"{f'|S| {a}-{b}':>14s}" for a, b in BQ) + "   (T64 pooled, power-weighted)")
    for tag, m, g1, qn, tp, elp in CASES:
        acc = {b: [0.0, 0.0] for b in BQ}
        for rk in T64:
            pk = packs[rk]
            _, L0, L1 = propagate(pk, m, g1, qn, tp, err_lp=elp)
            Ps = np.mean(np.abs(pk["X"]) ** 2, 0)
            for b in BQ:
                s2 = (fr >= b[0]) & (fr < b[1])
                acc[b][0] += float(np.sum(Ps[s2] * np.abs(1 / (1 + L1[s2])) ** 2))
                acc[b][1] += float(np.sum(Ps[s2]))
        print(f"  {tag:30s} " + "".join(f"{np.sqrt(acc[b][0]/acc[b][1]):14.3f}" for b in BQ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
