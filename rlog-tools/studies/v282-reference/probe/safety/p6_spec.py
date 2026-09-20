# -*- coding: utf-8 -*-
"""p6 -- the SPEC, with the waveform actually built and every interlock priced against it.

Design rules this script enforces, each of which came out of p1-p5:
  R1  lines sit where the plant estimators DISAGREE (0.85-1.60 Hz) -- that is the hole.
  R2  no line within 0.25 Hz of the error notch centre get_honda_accord_mode_hz(v), which sweeps
      1.79 Hz (17 m/s) -> 2.01 (22) -> 2.25 (28).  A line there costs 3-7x the amplitude for the
      same information, because the notch removes it before it reaches the motor.
  R3  a HARD per-line amplitude cap.  Without it the SNR solver chases the plant anti-resonance
      near 1.17 Hz at 17 m/s (|P| = 0.31) and asks for 0.31 m/s^2 -- 10x the useful dose, at the
      one frequency where the loop has no authority anyway.
  R4  phases optimised for crest factor, with the residual lateral offset of the finished burst
      MEASURED (not asserted), because Schroeder phases break the even symmetry that would
      otherwise force it to zero.
  R5  the amplitude is solved on the config that will FLY it.  A fixed amplitude carried from
      rev 6.4 to a Tier B gain delivers 1.7-3.4x the motion (the |T| ratio, table below).

!!! AMPLITUDES SUPERSEDED BY p7_ff_corrected.py / p8 (same folder), 2026-09-20 -- they are ~4-6x
too large, for the reason in p2_price.py's header (the plant feedforward reads `setpoint`).
The MOTION budget, the interlock numbers, the crest optimiser and the line-placement rules R1/R2/R3
all stand unchanged: equation (*) is about the motion, which is invariant to the injection gain.
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
W = np.hanning(NPS + 1)[:NPS]
PSD_SCALE = 2.0 / (FS * np.sum(W ** 2))
BINS = [("15", 13.0, 18.0), ("22", 18.0, 25.0), ("28", 25.0, 99.0)]
TB = 20.0
LINES = [0.85, 1.00, 1.15, 1.30, 1.45, 1.60]
A_CAP = 0.080                     # m/s^2 RMS per line, hard
T_TOT = 300.0
SIG = np.radians(8.0)
RATE_LIMIT = 0.03                 # per frame
CONFIGS = [("rev6.4 as flown", 1.0, 14.0, 0.3, 1.00), ("ARM-KP3", 3.0, 14.0, 0.6, 0.30),
           ("TierB kp8 Q.20", 8.0, 14.0, 0.6, 0.20), ("TierB kp16 Q.20", 16.0, 14.0, 0.6, 0.20)]
# worst torque-mode p99.9 headroom, from p4
U_P999, DU_P999 = 0.259, 0.00829


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def bin_state(routes, lo, hi):
    cols, vm = None, []
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = (D["vmed"] >= lo) & (D["vmed"] < hi)
        if sel.any():
            if cols is None:
                cols = {k: [] for k in ("Z", "M", "Y", "U", "SR", "UFF")}
                f = D["f"]
            for k in cols:
                cols[k].append(D[k][sel])
            vm.append(D["vmed"][sel])
        D.close()
    if cols is None:
        return None
    C = {k: np.concatenate(v) for k, v in cols.items()}
    vm = np.concatenate(vm)
    jw = 2j * np.pi * np.maximum(f, 1e-9)
    SRi = C["SR"] / jw[None, :]
    fit = (f >= 0.2) & (f <= 1.0)
    k_map = abs(np.sum(np.conj(SRi[:, fit]) * C["M"][:, fit]) / np.sum(np.abs(SRi[:, fit]) ** 2))
    Suu = xs(C["U"], C["U"]).real
    return dict(f=f, n=len(vm), v=float(np.median(vm)), k_map=k_map,
                P_ff=xs(C["UFF"], C["M"]) / xs(C["UFF"], C["U"]),
                P_iv=xs(C["Z"], C["M"]) / xs(C["Z"], C["U"]),
                P_dir=xs(C["U"], C["M"]) / np.maximum(Suu, 1e-300),
                V=xs(C["M"], C["Y"]) / np.maximum(xs(C["M"], C["M"]).real, 1e-300),
                pM=xs(C["M"], C["M"]).real * PSD_SCALE, pU=Suu * PSD_SCALE,
                pA=xs(SRi, SRi).real * PSD_SCALE, pSR=xs(C["SR"], C["SR"]).real * PSD_SCALE,
                pY=xs(C["Y"], C["Y"]).real * PSD_SCALE)


def crest_opt(freqs, amps_rms, tb, iters=400, seed=0):
    """Minimise crest by iterative time-clip / spectrum-restore, keeping every line's amplitude exact.
    Phases referenced to the burst CENTRE so the starting point is even-symmetric."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, tb, 1 / FS) - tb / 2
    ph = np.array([-np.pi * k * (k + 1) / len(freqs) for k in range(len(freqs))])
    best, bestc = ph.copy(), np.inf
    for trial in range(6):
        p = ph if trial == 0 else rng.uniform(-np.pi, np.pi, len(freqs))
        for _ in range(iters):
            x = sum(np.sqrt(2) * a * np.cos(2 * np.pi * f * t + q)
                    for f, a, q in zip(freqs, amps_rms, p))
            c = np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2))
            xc = np.clip(x, -1.25 * np.sqrt(np.mean(x ** 2)), 1.25 * np.sqrt(np.mean(x ** 2)))
            p = np.array([np.angle(np.sum(xc * np.exp(-2j * np.pi * f * t))) for f in freqs])
        x = sum(np.sqrt(2) * a * np.cos(2 * np.pi * f * t + q) for f, a, q in zip(freqs, amps_rms, p))
        c = np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2))
        if c < bestc:
            bestc, best = c, p.copy()
    return best, bestc


def main():
    fams = {}
    for r, g in LP.GROUPS.items():
        fams.setdefault(g, []).append(r)
    fams["ALL_T64"] = fams["T64"] + fams["T64B"]
    st, stV = {}, {}
    for bn, lo, hi in BINS:
        st[bn] = bin_state(fams["ALL_T64"], lo, hi)
        stV[bn] = bin_state(fams["V282"], lo, hi)

    print("=" * 124)
    print("R2 CHECK -- the error notch centre vs the line set")
    for bn, _, _ in BINS:
        v = st[bn]["v"]
        print(f"   v={v:5.1f} m/s   notch f0 = {LP.mode_hz(v):.3f} Hz   "
              f"closest line {min(LINES, key=lambda L: abs(L-LP.mode_hz(v))):.2f} Hz  "
              f"separation {min(abs(L-LP.mode_hz(v)) for L in LINES):.3f} Hz")

    print()
    print("=" * 124)
    print("R5 -- |T| at each line, per config.  A_req scales as 1/|T|, so the LAST column is the")
    print("      factor by which a FIXED amplitude over-delivers if it is carried to that config.")
    fac = {}
    for bn, _, _ in BINS:
        S = st[bn]
        f, v = S["f"], S["v"]
        print(f"\n   v={v:.1f} m/s")
        print(f"   {'f':>5s} " + " ".join(f"{c[0][:15]:>15s}" for c in CONFIGS) + "   x vs rev6.4")
        for fl in LINES:
            i = int(np.argmin(np.abs(f - fl)))
            Ts = []
            for label, kp, laf, ki, qq in CONFIGS:
                C = LP.c_fb_analytic(f, kp, float(LP.ki_of(v, ki, 0.0)), laf,
                                     float(LP.low_speed_factor(v)), notch_f0=float(LP.mode_hz(v)), q=qq)
                L = S["P_ff"][i] * C[i]
                Ts.append(abs(L / (1 + L)))
            print(f"   {f[i]:5.2f} " + " ".join(f"{x:15.3f}" for x in Ts)
                  + f"   {Ts[-2]/max(Ts[0],1e-9):6.2f} (kp8) {Ts[-1]/max(Ts[0],1e-9):6.2f} (kp16)")
            fac.setdefault(bn, []).append([float(x) for x in Ts])

    print()
    print("=" * 124)
    print(f"THE SPEC -- solved per speed bin on rev 6.4 as flown, T_tot={T_TOT:.0f} s, "
          f"sigma_phi={np.degrees(SIG):.0f} deg, cap {A_CAP} m/s2/line")
    spec = {}
    for bn, _, _ in BINS:
        S, SV = st[bn], stV[bn]
        f, v, km = S["f"], S["v"], S["k_map"]
        C = LP.c_fb_analytic(f, 1.0, float(LP.ki_of(v, 0.3, 0.0)), 14.0,
                             float(LP.low_speed_factor(v)), notch_f0=float(LP.mode_hz(v)), q=1.0)
        amps, mots, keep, info = [], [], [], []
        for fl in LINES:
            i = int(np.argmin(np.abs(f - fl)))
            P = S["P_ff"][i]
            L = P * C[i]
            Tm = abs(L / (1 + L))
            mot = np.sqrt((S["pM"][i] + abs(P) ** 2 * S["pU"][i]) / (2 * T_TOT)) / SIG
            A = mot / max(Tm, 1e-9)
            capped = A > A_CAP
            A = min(A, A_CAP)
            mot_eff = A * Tm
            sig_eff = np.degrees(np.sqrt((S["pM"][i] + abs(P) ** 2 * S["pU"][i]) / (2 * T_TOT)) / max(mot_eff, 1e-12))
            amps.append(A)
            mots.append(mot_eff)
            keep.append(f[i])
            info.append(dict(f=float(f[i]), A=float(A), capped=bool(capped), Tm=float(Tm),
                             P=float(abs(P)), sigma_deg=float(sig_eff),
                             dU=float(A * abs(C[i] / (1 + L))),
                             ang=float(mot_eff / km), rate=float(2 * np.pi * f[i] * mot_eff / km),
                             y=float(abs(S["V"][i]) * mot_eff),
                             yaw=float(np.degrees(abs(S["V"][i]) * mot_eff / v))))
        ph, crest = crest_opt(keep, amps, TB)
        # build the burst and measure everything on it
        t = np.arange(0, TB, 1 / FS)
        tc = t - TB / 2
        env = np.ones_like(t)
        nt = int(2.0 * FS)
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(nt) / nt))
        env[:nt], env[-nt:] = ramp, ramp[::-1]
        probe = env * sum(np.sqrt(2) * a * np.cos(2 * np.pi * fl * tc + q)
                          for fl, a, q in zip(keep, amps, ph))
        # its image in each perceived quantity (per-line complex gains, measured)
        def synth(gain_of_line):
            return env * sum(np.sqrt(2) * a * g * np.cos(2 * np.pi * fl * tc + q0 + p0)
                             for fl, a, q0, (g, p0) in zip(keep, amps, ph, gain_of_line))
        gY, gA = [], []
        for fl in keep:
            i = int(np.argmin(np.abs(f - fl)))
            L = S["P_ff"][i] * C[i]
            Tc = L / (1 + L)
            gY.append((abs(S["V"][i] * Tc), np.angle(S["V"][i] * Tc)))
            gA.append((abs(Tc) / km, np.angle(Tc)))
        ylat_acc = synth(gY)
        ang = synth(gA)
        vlat = np.cumsum(ylat_acc) / FS
        dev = np.cumsum(vlat) / FS
        dcmd = np.max(np.abs(np.diff(np.array([i["dU"] for i in info]).sum() * 0 + probe) * 0)) if False else None
        # command trace and its slew
        gU = []
        for fl in keep:
            i = int(np.argmin(np.abs(f - fl)))
            L = S["P_ff"][i] * C[i]
            Su = C[i] / (1 + L)
            gU.append((abs(Su), np.angle(Su)))
        ucmd = synth(gU)
        slew = np.max(np.abs(np.diff(ucmd)))
        ambA = float(np.sqrt(np.sum(S["pA"][(f >= 0.6) & (f < 2.0)]) * (f[1] - f[0])))
        ambA_V = float(np.sqrt(np.sum(SV["pA"][(f >= 0.6) & (f < 2.0)]) * (f[1] - f[0])))
        ambY = float(np.sqrt(np.sum(S["pY"][(f >= 0.6) & (f < 2.0)]) * (f[1] - f[0])))
        print(f"\n   --- v = {v:.1f} m/s  (n={S['n']} windows) ---")
        print(f"   {'f Hz':>5s} {'A rms':>7s} {'cap':>4s} {'|T|':>6s} {'sigma':>6s} {'dU':>7s}"
              f" {'angle':>7s} {'rate':>7s} {'latacc':>8s} {'yaw':>7s}")
        for I in info:
            print(f"   {I['f']:5.2f} {I['A']:7.4f} {'CAP' if I['capped'] else '':>4s} {I['Tm']:6.3f}"
                  f" {I['sigma_deg']:6.1f} {I['dU']:7.4f} {I['ang']:7.3f} {I['rate']:7.3f}"
                  f" {I['y']:8.4f} {I['yaw']:7.3f}")
        print(f"   BURST ({TB:.0f} s, crest {crest:.2f}):  probe  rms {np.sqrt(np.mean(probe**2)):.4f}"
              f"  peak {np.max(np.abs(probe)):.4f} m/s2")
        print(f"     command   rms {np.sqrt(np.mean(ucmd**2)):.5f}  peak {np.max(np.abs(ucmd)):.5f}"
              f"   -> rail margin {1.0-U_P999-np.max(np.abs(ucmd)):.3f}"
              f"   slew {slew:.5f}/frame = {100*slew/RATE_LIMIT:.1f}% of 0.03,"
              f" with ambient p99.9 {100*(DU_P999+slew)/RATE_LIMIT:.1f}%")
        print(f"     wheel     rms {np.sqrt(np.mean(ang**2)):.3f}  peak {np.max(np.abs(ang)):.3f} deg"
              f"   (ambient rev6.4 {ambA:.3f}, V282 {ambA_V:.3f})  -> in-band x"
              f"{np.sqrt(1+(np.sqrt(np.mean(ang**2))/ambA)**2):.3f}")
        print(f"     lat accel rms {np.sqrt(np.mean(ylat_acc**2)):.4f}  peak {np.max(np.abs(ylat_acc)):.4f} m/s2"
              f"   (ambient {ambY:.4f})")
        print(f"     yaw rate  rms {np.degrees(np.sqrt(np.mean(ylat_acc**2))/v):.4f}"
              f"  peak {np.degrees(np.max(np.abs(ylat_acc))/v):.4f} deg/s")
        print(f"     LANE      peak deviation {1000*np.max(np.abs(dev)):.1f} mm,"
              f"  net offset at burst end {1000*dev[-1]:+.1f} mm,"
              f"  net lateral velocity {1000*vlat[-1]:+.2f} mm/s")
        spec[bn] = dict(v=v, k_map=km, lines=info, phases_rad=[float(x) for x in ph], crest=float(crest),
                        burst_s=TB, probe_rms=float(np.sqrt(np.mean(probe ** 2))),
                        probe_peak=float(np.max(np.abs(probe))),
                        cmd_peak=float(np.max(np.abs(ucmd))), slew_per_frame=float(slew),
                        wheel_rms_deg=float(np.sqrt(np.mean(ang ** 2))),
                        wheel_peak_deg=float(np.max(np.abs(ang))),
                        y_rms=float(np.sqrt(np.mean(ylat_acc ** 2))),
                        y_peak=float(np.max(np.abs(ylat_acc))),
                        dev_peak_mm=float(1000 * np.max(np.abs(dev))),
                        dev_end_mm=float(1000 * dev[-1]),
                        ambient_wheel_rev64=ambA, ambient_wheel_v282=ambA_V, ambient_y=ambY)
    json.dump(spec, open(HERE / "p6_spec.json", "w"), indent=1)
    print("\nwrote p6_spec.json")


if __name__ == "__main__":
    main()
