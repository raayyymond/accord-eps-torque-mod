# -*- coding: utf-8 -*-
"""X3 -- HOW BIG MUST THE PROBE BE, AND DOES IT REACH THE BAND THAT ACTUALLY BINDS?

Two questions the probe proposal has to survive.

1. REACH.  The binding frequency of the vector margin -- the statistic that withdrew ARM-KP2 -- is
   3.4-4.9 Hz (X1 measures f* directly for every candidate).  The probe is proposed for ~0.6-2.4 Hz,
   where the closure lives.  If the probe does not carry power where the margin binds, it cannot
   certify Tier B's safety; if it does, it is a commanded oscillation at the hazard frequency and is
   not inert.

2. SIZE.  For an added exogenous reference z, with c0 = the present coh(r,u):
       new coh = (c0*Suu + |G|^2 Szz) / (Suu + |G|^2 Szz),   |G|^2 = c0*Suu/Srr
   =>  Szz / Srr = (c_target - c0) / ((1 - c_target) * c0)        [exact, instrument-free]
   That is how much reference power the probe must ADD, as a multiple of the reference power the
   planner already puts there.  Converted to m/s^2, to jerk against the fork's own MAX_LAT_JERK_UP
   clip, and to steering-rate deg/s through each route's own measured d(angle)/d(lataccel).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import advlib2 as A  # noqa: E402

OUT = HERE / "out"
RTS = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
CT = 0.7
BANDS = [("0.15-0.60", 0.15, 0.60), ("0.60-1.20", 0.60, 1.20), ("1.20-2.40", 1.20, 2.40),
         ("2.40-3.40", 2.40, 3.40), ("3.40-4.90", 3.40, 4.90), ("4.90-6.00", 4.90, 6.00)]
MAX_LAT_JERK_UP = 2.5     # latcontrol_torque.py:36, m/s^3
REF_RC = 0.06             # AccordRefFilter as flown on T64 (params_all.json), two cascaded stages


_WSQ = float(np.sum(np.hanning(1024) ** 2))


def brms(X, s, n=1024):
    """Band RMS of the underlying signal from Hann-windowed rFFTs (rows = windows)."""
    return float(np.sqrt(2.0 * np.mean(np.sum(np.abs(X[:, s]) ** 2, axis=1)) / (n * _WSQ)))


def refilter_mag(f, rc):
    a = A.DT / (rc + A.DT)
    z = np.exp(-2j * np.pi * np.asarray(f) * A.DT)
    return np.abs(a / (1.0 - (1 - a) * z)) ** 2


def main():
    print("=" * 126)
    print("1. WHERE THE MARGIN BINDS vs WHERE THE PROBE IS PROPOSED.")
    print("   f* = argmin |1+L| over 2-6 Hz, on the rev 6.4 plant, per candidate dose.")
    S = json.load(open(OUT / "x1_anchors.json"))
    f = np.array(S[list(S)[0]]["f"])
    cands = [("as flown  KP1.0 Q1.0", 1.0, 1.0), ("ARM-KP3   KP3.0 Q0.30", 3.0, 0.30),
             ("TIER B    KP5.0 Q0.20", 5.0, 0.20), ("TIER B    KP8.0 Q0.20", 8.0, 0.20),
             ("TIER B    KP12  Q0.20", 12.0, 0.20), ("TIER B    KP16  Q0.20", 16.0, 0.20)]
    print(f"   {'candidate':24s} " + " ".join(f"{k.split('--')[0][-2:]+'|'+k.split('|')[1]:>12s}"
                                              for k in S if k.startswith("0000006")))
    for lbl, kp, q in cands:
        line = f"   {lbl:24s} "
        for k in [k for k in S if k.startswith("0000006")]:
            D = S[k]
            P = np.array(D["P_r"][0]) + 1j * np.array(D["P_r"][1])
            C = A.C_fb(f, D["v"], kp, 14.0, 0.3, 0.0, q)
            vm, fs = A.vecmargin(f, P * C)
            line += f"{fs:9.2f} Hz"
        print(line)
    print("   ==> every candidate's margin binds ABOVE 3.4 Hz.  The probe band (0.6-2.4 Hz) does not")
    print("       contain the binding frequency of a single one of them.")

    print()
    print("=" * 126)
    print("2. HOW BIG THE PROBE HAS TO BE.  Szz/Srr = (c*-c0)/((1-c*)c0), c* = 0.70.")
    print("   Per band, on rev 6.4's metric windows (>=15 m/s, laterally engaged, hands off).")
    for rt in RTS:
        L = A.load(rt)
        f2, F, vm, am = A.spectra(L)
        idx = np.where(vm >= 15.0)[0]
        R = A.ident(F, idx, instr="r")
        # d(steering angle deg) / d(lateral accel) from this route's own logs, engaged frames
        m = L["act"] & np.isfinite(L["y"]) & np.isfinite(L["sa"]) & (L["v"] >= 15.0)
        k_sa = float(np.polyfit(L["y"][m], L["sa"][m], 1)[0])
        print(f"\n   --- {rt}  n {len(idx)} windows, v {np.median(vm[idx]):.1f} m/s, "
              f"d(angle)/d(lataccel) = {k_sa:.2f} deg per m/s^2")
        print(f"   {'band':11s} {'coh(r,u)':>9s} {'Szz/Srr':>9s} {'ref rms':>9s} {'PROBE rms':>10s} "
              f"{'probe pk':>9s} {'pk jerk':>9s} {'jerk lim':>9s} {'SR pk':>8s} {'today SR':>9s}")
        for nm, lo, hi in BANDS:
            s = (f2 >= lo) & (f2 <= hi)
            c0 = float(np.mean(R["coh_wu"][s]))
            ratio = (CT - c0) / ((1 - CT) * max(c0, 1e-6))
            if ratio <= 0:
                print(f"   {nm:11s} {c0:9.3f} {'already>=c*':>9s}")
                continue
            # band RMS from the Hann-windowed rFFT: Parseval with the window's power correction.
            # mean square of x over the window = 2 * sum_band |X_k|^2 / (N * sum(w^2))
            ref_rms = brms(F["r"][idx], s)
            probe_rms = ref_rms * np.sqrt(ratio)
            fc = 0.5 * (lo + hi)
            pk = probe_rms * np.sqrt(2)
            jerk = 2 * np.pi * fc * pk
            srpk = 2 * np.pi * fc * pk * abs(k_sa)
            # what the car already does in that band, in steering-rate deg/s RMS
            sr_now = brms(F["sr"][idx], s)
            print(f"   {nm:11s} {c0:9.3f} {ratio:9.2f} {ref_rms:9.4f} {probe_rms:10.4f} "
                  f"{pk:9.4f} {jerk:9.3f} {MAX_LAT_JERK_UP:9.2f} {srpk:8.2f} {sr_now:9.3f}")
        del L, F
    print()
    print("   ref rms / PROBE rms / probe pk are m/s^2 of commanded lateral acceleration;")
    print("   pk jerk m/s^3 against the fork's own MAX_LAT_JERK_UP; SR pk = the peak steering RATE")
    print("   in deg/s the probe alone commands; 'today SR' = the route's own in-band steering-rate RMS.")

    print()
    print("=" * 126)
    print("3. AND WHAT THE REFERENCE PATH DOES TO AN INJECTED SIGNAL (AccordRefFilter rc = 0.06 s,")
    print("   two cascaded first-order stages, latcontrol_torque.py:319-329).  Inject upstream and the")
    print("   probe is attenuated; inject downstream and it bypasses the shaping the build relies on.")
    for fq in (0.3, 0.6, 1.0, 1.5, 2.0, 2.4, 3.4, 4.2, 4.9, 6.0):
        print(f"      {fq:5.2f} Hz   |RefFilter|^2 = {refilter_mag(fq, REF_RC):.4f}   "
              f"amplitude needed upstream to land 1.0 downstream = {1/np.sqrt(refilter_mag(fq, REF_RC)):.2f}x")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    main()
