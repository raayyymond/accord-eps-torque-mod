# -*- coding: utf-8 -*-
"""S5 -- THE TRADE, in one table: for each candidate, the goal metric AND the 1.8-3.5 Hz wheel shake,
from the SAME set of measured transfers, with the flown case as an exact identity check.

ONE linear system per window per frequency bin, every coefficient measured or read from source:
    U  = W + C*(Z - M) + g*F_rc*SR          (the command, from the fork's own structure)
    M  = P*U + dM                            (P = H(U->M) by IV; dM fixed by the flown log)
    SR = G*U + dSR                           (G = H(U->SR) by IV; dSR fixed by the flown log)
  =>  U = [W + C*Z - C*dM + g*F_rc*dSR] / (1 + C*P - g*F_rc*G)
Re-solving with (C1, g1) gives U, M, SR for the candidate.  W, Z, dM, dSR are held fixed: that is
the SAME invariance assumption the SteerKP closure algebra already rests on (the exogenous command,
the setpoint chain and the road are unchanged).  It is ALGEBRA ON MEASURED TRANSFERS, not a
simulator, and it predicts nothing about how the car feels.

WEAKEST LINK, stated up front: G above 1.8 Hz.  Instrument coherence there is 0.45-0.92 and the
route-to-route spread of the shake-band answer is reported, never averaged away.

usage: python s5_tradeoff.py > out/S5-TRADEOFF.txt
"""
import json

import numpy as np

import suplib as S
from s4_closure import C_fb, route_pack, smooth, T64, OTHER, REF, MET

SHAKE = S.SHAKE
CASES = [
    # tag,                          kp x,  g1,     notch Q,  taper, err-LP Hz
    ("as flown", 1.0, None, "flown", True, None),
    ("SteerKP x2", 2.0, None, "flown", True, None),
    ("SteerKP x3 (toggle ceiling)", 3.0, None, "flown", True, None),
    ("SteerKP x5 (code)", 5.0, None, "flown", True, None),
    ("SteerKP x8 (code)", 8.0, None, "flown", True, None),
    ("notch Q 0.5 alone", 1.0, None, 0.5, True, None),
    ("notch OFF alone", 1.0, None, None, True, None),
    ("err LP 2 Hz alone", 1.0, None, "flown", True, 2.0),
    ("rate 0.003 (toggle ceiling)", 1.0, 0.003, "flown", True, None),
    ("rate 0.003 no taper (code)", 1.0, 0.003, "flown", False, None),
    ("rate 0.002 no taper (code)", 1.0, 0.002, "flown", False, None),
    ("rate 0.0 (damper off)", 1.0, 0.0, "flown", True, None),
    ("KPx3 + rate .003NT", 3.0, 0.003, "flown", False, None),
    ("KPx3 + errLP2", 3.0, None, "flown", True, 2.0),
    ("KPx3 + errLP2 + rate .003NT", 3.0, 0.003, "flown", False, 2.0),
    ("KPx5 + errLP2", 5.0, None, "flown", True, 2.0),
    ("KPx5 + errLP2 + rate .003NT", 5.0, 0.003, "flown", False, 2.0),
    ("KPx8 + errLP2", 8.0, None, "flown", True, 2.0),
    ("KPx8 + errLP2 + rate .003NT", 8.0, 0.003, "flown", False, 2.0),
    ("KPx8 + errLP1.5 + rate .003NT", 8.0, 0.003, "flown", False, 1.5),
    ("KPx2 + rate .003NT", 2.0, 0.003, "flown", False, None),
    ("KPx5 + rate .003NT", 5.0, 0.003, "flown", False, None),
    ("KPx8 + rate .003NT", 8.0, 0.003, "flown", False, None),
    ("KPx3 + rate .003 (toggle only)", 3.0, 0.003, "flown", True, None),
    ("cmd notch 2.5 Hz Q1 (wrong lever)", 1.0, None, "flown", True, None, ("notch", 2.5, 1.0)),
    ("cmd LP 2 Hz (wrong lever)", 1.0, None, "flown", True, None, ("lp", 2.0, None)),
    ("KPx3 + cmd notch 2.5 Hz Q1", 3.0, None, "flown", True, None, ("notch", 2.5, 1.0)),
]
CASES = [c if len(c) == 7 else (c + (None,)) for c in CASES]


def solve(pk, m_kp=1.0, g1=None, q_notch="flown", taper=True, err_lp=None, flown=False, cmd=None):
    fr, meta = pk["fr"], pk["meta"]
    P, G = smooth(pk["P"]), smooth(pk["G"])
    Frc = S.fof_H(fr, S.RATE_LOOP_RC)
    g0e = S.rate_loop_gain(pk["v"], pk["g0"])
    g1e = g0e if (g1 is None or flown) else (S.rate_loop_gain(pk["v"], g1) if taper else g1)
    f0 = S.mode_hz(pk["v"])
    q_now = 1.0 if meta["notch"] else None
    q_new = q_now if (q_notch == "flown" or flown) else q_notch
    C0 = C_fb(fr, meta["kp"], meta["ki"], meta["laf"], pk["lsf"], q_now, f0)
    C1 = C_fb(fr, meta["kp"] * (1.0 if flown else m_kp), meta["ki"], meta["laf"], pk["lsf"], q_new, f0)
    if err_lp and not flown:
        C1 = C1 * S.fof_H(fr, 1.0 / (2 * np.pi * err_lp))
    Z, W, U, M, SRm = pk["Z"], pk["W"], pk["U"], pk["M"], pk["SR"]
    dM = M - P[None, :] * U
    dSR = SRm - G[None, :] * U
    # an added filter on the OUTPUT COMMAND filters everything the controller sends, the inner rate
    # damper's reply included: U = Fc*(W + C*D + g*F*SR).
    Fc = np.ones_like(fr, dtype=complex)
    if cmd and not flown:
        kind, a1, a2 = cmd
        Fc = S.fof_H(fr, 1.0 / (2 * np.pi * a1)) if kind == "lp" else S.notch_H(fr, a1, a2)
    den = (1 + Fc * C1 * P - Fc * g1e * Frc * G)[None, :]
    Un = (Fc[None, :] * (W + C1[None, :] * Z - C1[None, :] * dM + (g1e * Frc)[None, :] * dSR)) / den
    Mn = P[None, :] * Un + dM
    SRn = G[None, :] * Un + dSR
    Yn = pk["Y"] + pk["V"][None, :] * (Mn - M)      # Y = V*M + (outside-the-loop terms), held fixed
    L1 = Fc * C1 * P / (1 - Fc * g1e * Frc * G)
    return Un, Mn, SRn, Yn, L1


def bandpow(A, fr, f1, f2):
    s = (fr >= f1) & (fr <= f2)
    return float(np.sum(np.abs(A[:, s]) ** 2))


def main():
    print(S._self_test())
    packs = {}
    for rk in T64 + OTHER + REF:
        pk = route_pack(rk)
        if pk is not None:
            # SR spectra are needed here; route_pack already requests them
            packs[rk] = pk
    fr = packs[T64[0]]["fr"]
    sel = (fr >= MET[0]) & (fr <= MET[1])

    print("\n" + "=" * 150)
    print("0. IDENTITY CHECK: re-solving the system at the FLOWN settings must return the logged U, M and SR.")
    print("=" * 150)
    for rk, pk in packs.items():
        Un, Mn, SRn, Yn, _ = solve(pk, flown=True)
        bsel = (fr >= 0.10) & (fr <= 8.0)      # the DC bin carries the integrator's 1/0
        eu = np.max(np.abs((Un - pk["U"])[:, bsel])) / np.max(np.abs(pk["U"][:, bsel]))
        em = np.max(np.abs((Mn - pk["M"])[:, bsel])) / np.max(np.abs(pk["M"][:, bsel]))
        es = np.max(np.abs((SRn - pk["SR"])[:, bsel])) / np.max(np.abs(pk["SR"][:, bsel]))
        print(f"  {rk} {pk['meta']['fam']:6s} max rel err  U {eu:.2e}  M {em:.2e}  SR {es:.2e}")

    JT = num = den = 0.0
    for rk in T64:
        pk = packs[rk]
        num += bandpow(pk["X"] - pk["Y"], fr, *MET)
        den += bandpow(pk["X"], fr, *MET)
    JT = num / den
    nr = dr = 0.0
    for rk in REF:
        nr += bandpow(packs[rk]["X"] - packs[rk]["Y"], fr, *MET)
        dr += bandpow(packs[rk]["X"], fr, *MET)
    JV = nr / dr
    print(f"\n  flown J (T64 pooled) {JT:.3f}   V282 {JV:.3f}   gap {JT-JV:.3f}")

    print("\n" + "=" * 150)
    print("1. THE TRADE.  closure% = (J_flown - J)/(J_flown - J_V282) in this re-derivation.")
    print("   shake = 1.8-3.5 Hz WHEEL-RATE rms ratio to flown, from the same solve (1.00 = today).")
    print("   Per-route shake in brackets so the spread is visible, never averaged away.")
    print("   |S|1.2-2.4 is the sensitivity peak the metric's own top band sees (waterbed watch).")
    print("=" * 150)
    print(f"  {'case':32s} {'J':>7s} {'closure':>8s} {'shake':>7s} {'per-route shake':>34s} "
          f"{'|S|1.2-2.4':>10s} {'max|L|':>7s}")
    rows = {}
    for tag, m, g1, qn, tp, elp, cmdf in CASES:
        jn = jd = 0.0
        sh_n = {}
        sp_all = []
        Sp = []
        Lmax = []
        for rk in T64 + OTHER:
            pk = packs[rk]
            Un, Mn, SRn, Yn, L1 = solve(pk, m, g1, qn, tp, elp, cmd=cmdf)
            J = bandpow(pk["X"] - Yn, fr, *MET) / bandpow(pk["X"], fr, *MET)
            shr = np.sqrt(bandpow(SRn, fr, *SHAKE) / bandpow(pk["SR"], fr, *SHAKE))
            sh_n[rk] = shr
            if pk["meta"]["fam"] == "T64":
                jn += J * bandpow(pk["X"], fr, *MET)
                jd += bandpow(pk["X"], fr, *MET)
                b = (fr >= 1.2) & (fr <= 2.4)
                Ps = np.mean(np.abs(pk["X"]) ** 2, 0)
                Sp.append(np.sqrt(np.sum(Ps[b] * np.abs(1 / (1 + L1[b])) ** 2) / np.sum(Ps[b])))
                bl = (fr >= 0.1) & (fr <= 2.4)
                Lmax.append(np.max(np.abs(L1[bl])))
            sp_all.append(shr)
        Jp = jn / jd
        cl = (JT - Jp) / (JT - JV) * 100
        shp = float(np.sqrt(np.mean([sh_n[r] ** 2 for r in T64])))
        print(f"  {tag:32s} {Jp:7.3f} {cl:7.1f}% {shp:7.2f}  [" +
              " ".join(f"{x:4.2f}" for x in sp_all) + f"] {np.mean(Sp):10.3f} {np.mean(Lmax):7.2f}")
        rows[tag] = dict(J=Jp, closure=cl, shake=shp, per_route=[float(x) for x in sp_all],
                         S12_24=float(np.mean(Sp)), Lmax=float(np.mean(Lmax)))
    json.dump(dict(JT64=JT, JV282=JV, rows=rows), open(S.OUT / "s5_tradeoff.json", "w"), indent=1)

    print("\n" + "=" * 150)
    print("2. CROSS-CHECK of the shake column against the MODEL-FREE command re-synthesis (S2).")
    print("   S2 re-synthesised the COMMAND at the same settings straight from the logged p/i/f with no")
    print("   plant anywhere; if the two disagree in DIRECTION the shake column is not to be trusted.")
    print("=" * 150)
    try:
        s2 = json.load(open(S.OUT / "s2_resynth.json"))
        for rk in T64:
            v = s2.get(rk, {}).get("var", {})
            print(f"  {rk}: command 1.8-3.5 Hz ratio   KPx2 {v.get('KP x2 (notch as flown)', ['-'])[0]}, "
                  f"KPx3 {v.get('KP x3 (notch as flown)', ['-'])[0]}, notch Q0.5 {v.get('notch Q=0.5', ['-'])[0]}, "
                  f"notch OFF {v.get('notch OFF (Q=0), kp as flown', ['-'])[0]}")
    except FileNotFoundError:
        print("  (run s2_resynth.py first)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
