# -*- coding: utf-8 -*-
"""p2 -- the CODE-EXACT price of an injection at the ERROR SUM, on the configs that could carry it.

Two independent prices, deliberately kept apart:

  PRICE-A  "ambient ratio"    |T_ZG| from p1 (H1 with the shaped setpoint as instrument).
           Unbiased ONLY if Z is exogenous.  Z is not fully exogenous above ~1.2 Hz -- the driving
           model sees the car's own yaw, and desired_curvature is a 20 Hz signal held to 100 Hz --
           so this reads HIGH there.  Used as the CEILING.

  PRICE-B  "P measured, C from the code"      T = P*C / (1 + P*C)
           P = command -> the controller's own measurement, DIRECT estimator (the command HAS power
           in 0.6-2.0 Hz, and |L| is small there, so the direct estimator's bias toward -1/C is
           second order).  C = c_fb_analytic, the EXACT discrete fork controller at each config's
           own flown SteerKP / LAF / ki / low-speed factor / notch.  This is the POINT estimate.

INJECTION POINT (this is a design choice the safety stream is making, and it is the cheap one):
    error = (setpoint + probe) - measurement          <-- AFTER accord_ref_filter, BEFORE the notch
  so the probe
    * does NOT pass the reference filter (rev 6.4 flew rc 0.06 -> -3.9 dB and -74 deg at 2 Hz;
      r72/r73/r75/r76 flew 0.12 -> -10.2 dB and -112 deg).  Full amplitude where we need coherence.
    * does NOT reach the FEEDFORWARD (ff = gravity_adjusted_future_lateral_accel, latcontrol_torque.py
      :316,:330 -- the ff is built from the RAW planner accel, not from `setpoint`).  So the probe's
      only route to the motor is C_fb, whose gain is a closed-form number, not an identified one.
    * DOES pass the error notch, which is where the excitation should be shaped anyway.

!!! SUPERSEDED IN PART BY p7_ff_corrected.py (same folder), 2026-09-20.
p2's PRICE-B is WRONG for a reference-path injection on this car: it counts only C_fb, but
AccordRatePlantFF == 1 on every flown route and the Accord feedforward is built from `setpoint`
(latcontrol_torque.py :636-666).  The true setpoint->motor gain is Kff + C_fb, and Kff is 3.7-18x
C_fb across 0.68-1.76 Hz.  p7 rebuilds it from the fork constants and reproduces the MEASURED
S_ZM/S_ZZ to 0.76-1.27x.  Use p7/p8 for amplitudes.  p2's P(f) identification and its ambient
spectra are unaffected and still good.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS, NPS = 100.0, 1024
BINS = [("15", 13.0, 18.0), ("22", 18.0, 25.0), ("28", 25.0, 99.0)]
BAND = (0.6, 2.0)
KFIT = (0.2, 1.0)
W = np.hanning(NPS + 1)[:NPS]
PSD_SCALE = 2.0 / (FS * np.sum(W ** 2))

# configs to price.  (label, kp, laf, ki, ki_hi, notch_Q or None)
CONFIGS = [
    ("rev6.4 as flown", 1.0, 14.0, 0.3, 0.0, 1.00),
    ("ARM-KP3",         3.0, 14.0, 0.6, 0.0, 0.30),
    ("TierB kp8  Q.20", 8.0, 14.0, 0.6, 0.0, 0.20),
    ("TierB kp16 Q.20", 16.0, 14.0, 0.6, 0.0, 0.20),
    ("V282 reference",  0.9, 6.0, 0.3, 0.0, None),
]
FAM_OF = {"rev6.4 as flown": "ALL_T64", "ARM-KP3": "ALL_T64", "TierB kp8  Q.20": "ALL_T64",
          "TierB kp16 Q.20": "ALL_T64", "V282 reference": "V282"}


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def stack(routes, vlo, vhi):
    cols, vm = None, []
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = (D["vmed"] >= vlo) & (D["vmed"] < vhi)
        if sel.any():
            if cols is None:
                cols = {k: [] for k in ("Z", "M", "Y", "U", "SR")}
                f = D["f"]
            for k in cols:
                cols[k].append(D[k][sel])
            vm.append(D["vmed"][sel])
        D.close()
    if cols is None:
        return None
    return dict(f=f, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def measure(routes, vlo, vhi):
    W_ = stack(routes, vlo, vhi)
    if W_ is None or len(W_["vmed"]) < 4:
        return None
    f = W_["f"]
    jw = 2j * np.pi * np.maximum(f, 1e-9)
    Z, M, Y, U, SR = W_["Z"], W_["M"], W_["Y"], W_["U"], W_["SR"]
    SRi = SR / jw[None, :]
    fit = (f >= KFIT[0]) & (f <= KFIT[1])
    k_map = np.sum(np.conj(SRi[:, fit]) * M[:, fit]) / np.sum(np.abs(SRi[:, fit]) ** 2)
    Suu = xs(U, U).real
    P_dir = xs(U, M) / np.maximum(Suu, 1e-300)                    # command -> measurement, direct
    P_dirSR = k_map * xs(U, SRi) / np.maximum(Suu, 1e-300)        # same, via the rate channel
    coh_um = np.abs(xs(U, M)) ** 2 / np.maximum(Suu * xs(M, M).real, 1e-300)
    coh_usr = np.abs(xs(U, SRi)) ** 2 / np.maximum(Suu * xs(SRi, SRi).real, 1e-300)
    V = xs(M, Y) / np.maximum(xs(M, M).real, 1e-300)              # measurement -> achieved yaw*v
    coh_my = np.abs(xs(M, Y)) ** 2 / np.maximum(xs(M, M).real * xs(Y, Y).real, 1e-300)
    Szz = xs(Z, Z).real
    return dict(f=f, n=len(W_["vmed"]), v=float(np.median(W_["vmed"])), k_map=abs(k_map),
                P=P_dir, P_sr=P_dirSR, coh_um=coh_um, coh_usr=coh_usr, V=V, coh_my=coh_my,
                T_ZM=xs(Z, M) / np.maximum(Szz, 1e-300),
                psd=dict(A=xs(SRi, SRi).real * PSD_SCALE, SR=xs(SR, SR).real * PSD_SCALE,
                         Y=xs(Y, Y).real * PSD_SCALE, U=Suu * PSD_SCALE, Z=Szz * PSD_SCALE,
                         M=xs(M, M).real * PSD_SCALE))


def C_of(f, v, kp, laf, ki, ki_hi, q):
    lsf = float(LP.low_speed_factor(v))
    kie = float(LP.ki_of(v, ki, ki_hi))
    f0 = float(LP.mode_hz(v)) if q is not None else None
    return LP.c_fb_analytic(f, kp, kie, laf, lsf, notch_f0=f0, q=(q if q else 1.0))


def main():
    fams = {}
    for r, g in LP.GROUPS.items():
        fams.setdefault(g, []).append(r)
    fams["ALL_T64"] = fams["T64"] + fams["T64B"]
    meas = {}
    for fam in ("ALL_T64", "V282"):
        for bn, lo, hi in BINS:
            R = measure(fams[fam], lo, hi)
            if R:
                meas[f"{fam}|{bn}"] = R

    f = meas["ALL_T64|22"]["f"]
    band = (f >= BAND[0]) & (f < BAND[1])
    out = {}

    print("=" * 118)
    print("P(f) -- command -> the controller's measurement, DIRECT estimator, two channels + coherence")
    for key in sorted(meas):
        R = meas[key]
        print(f"\n  {key}  n={R['n']}  v={R['v']:.1f}  |k_map|={R['k_map']:.4f}")
        print(f"  {'f':>5s} {'|P_dir|':>8s} {'|P_sr|':>8s} {'ratio':>6s} {'coh_um':>7s} {'coh_usr':>8s}"
              f" {'phP':>7s} {'|V|':>6s} {'coh_my':>7s} {'|T_ZM|':>7s}")
        for i in np.where(band)[0]:
            print(f"  {f[i]:5.2f} {abs(R['P'][i]):8.2f} {abs(R['P_sr'][i]):8.2f}"
                  f" {abs(R['P_sr'][i])/max(abs(R['P'][i]),1e-9):6.2f} {R['coh_um'][i]:7.3f}"
                  f" {R['coh_usr'][i]:8.3f} {np.degrees(np.angle(R['P'][i])):7.1f}"
                  f" {abs(R['V'][i]):6.3f} {R['coh_my'][i]:7.3f} {abs(R['T_ZM'][i]):7.2f}")

    print()
    print("=" * 118)
    print("THE PRICE, per 1.000 m/s^2 of probe injected at the ERROR SUM")
    print("  dU = C/(1+L) ; dM = L/(1+L) ; dAngle = dM/k_map ; dRate = 2*pi*f*dAngle ; dY = V*dM ; dYaw = dY/v")
    for label, kp, laf, ki, ki_hi, q in CONFIGS:
        fam = FAM_OF[label]
        for bn, _, _ in BINS:
            key = f"{fam}|{bn}"
            if key not in meas:
                continue
            R = meas[key]
            v = R["v"]
            C = C_of(f, v, kp, laf, ki, ki_hi, q)
            L = R["P"] * C
            T = L / (1.0 + L)
            dU = C / (1.0 + L)
            dA = T / R["k_map"]
            dSR = 2 * np.pi * f * np.abs(dA)
            dY = R["V"] * T
            print(f"\n  --- {label:16s}  {key}  v={v:.1f} m/s  n={R['n']} ---")
            print(f"  {'f':>5s} {'|L|':>6s} {'|T|':>6s} {'dU':>7s} {'dAngle deg':>10s} {'dRate d/s':>9s}"
                  f" {'dY m/s2':>8s} {'dYaw d/s':>8s} {'|S|':>6s}")
            for i in np.where(band)[0]:
                print(f"  {f[i]:5.2f} {abs(L[i]):6.3f} {abs(T[i]):6.3f} {abs(dU[i]):7.4f}"
                      f" {abs(dA[i]):10.3f} {dSR[i]:9.3f} {abs(dY[i]):8.3f}"
                      f" {np.degrees(abs(dY[i])/v):8.3f} {abs(1/(1+L[i])):6.3f}")
            out[f"{label}|{bn}"] = dict(
                f=f[band].tolist(), L=np.abs(L[band]).tolist(), T=np.abs(T[band]).tolist(),
                dU=np.abs(dU[band]).tolist(), dAngle=np.abs(dA[band]).tolist(),
                dRate=dSR[band].tolist(), dY=np.abs(dY[band]).tolist(),
                dYaw=np.degrees(np.abs(dY[band]) / v).tolist(), v=v, n=R["n"], k_map=R["k_map"])

    # ambient, for the ruler
    amb = {}
    for key, R in meas.items():
        df = f[1] - f[0]
        amb[key] = {k: float(np.sqrt(np.sum(P[band]) * df)) for k, P in R["psd"].items()}
        amb[key]["v"] = R["v"]
        amb[key]["n"] = R["n"]
        amb[key]["k_map"] = R["k_map"]
        amb[key]["psd"] = {k: P[band].tolist() for k, P in R["psd"].items()}
        amb[key]["T_ZM"] = np.abs(R["T_ZM"][band]).tolist()
        amb[key]["V"] = np.abs(R["V"][band]).tolist()
    json.dump(dict(band_f=f[band].tolist(), price=out, ambient=amb),
              open(HERE / "p2_out.json", "w"), indent=1)
    print("\nwrote p2_out.json")


if __name__ == "__main__":
    main()
