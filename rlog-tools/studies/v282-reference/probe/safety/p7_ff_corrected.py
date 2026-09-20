# -*- coding: utf-8 -*-
"""p7 -- CORRECTION to p2/p6, and the final spec.

p2 priced a setpoint injection as if the only route to the motor were C_fb.  That is WRONG on this
car.  `AccordRatePlantFF` is 1 on EVERY flown route (params_all.json, read per route), and the Accord
branch of latcontrol_torque.py builds its feedforward from `setpoint` -- the SHAPED one, after
AccordRefFilter -- not from the raw planner accel:

    curv_des        = (setpoint - latAccelOffset*fade) / max(v^2, 1)          :636
    angle_des       = deg(VM.get_steer_from_curvature(-curv_des, v, roll))    :637
    d_angle_des     = angle_des - prev                                        :638
    angle_des_rate  = FirstOrderFilter(RC = HONDA_ACCORD_FF_RATE_RC = 0.10 s) :640
    plant_ff_torque = -get_honda_accord_rate_plant_ff(angle_des, angle_des_rate, v, 0.5, ...)  :655
                      = hold k(v)*level(v)*sat*tanh(angle/sat)  +  clip(0.5*rate/G(v), +/-limit)
    accord_friction_z = honda_accord_friction_hysteresis(z, d_angle_des, 0.015, band(v))       :661
    inner_torque      = -(z + rate_loop_gain*(angle_des_rate - rate_meas))                      :666

So the setpoint reaches the motor through FOUR open-loop paths (hold, move, hysteresis, rate-loop
reference) plus C_fb.  Below, Kff is built from those constants and compared against the MEASURED
closed-loop Z -> M transfer.  If they agree, the measured transfer is explained and can be used.

CONSEQUENCE, and it reverses two of p2/p6's conclusions:
  * an injection on the reference path is NOT attenuated by the loop's |T| = 0.1-0.6.  It is
    delivered nearly one for one, |T_inj| = 1.4-2.0, because the feedforward is open loop.
  * so the AMPLITUDE needed is ~4-6x SMALLER than p6 says.  The COMMAND and the MOTION are
    unchanged (both are fixed by the plant: dU = dM/|P|), so every interlock number in p4/p6 stands.
  * and the probe must be kept inside the friction-hysteresis band, or a sign-like term rails at
    +/-AccordFrictionHyst at the probe frequency and corrupts the identification it is paying for.
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
LINES = [0.85, 1.00, 1.15, 1.30, 1.45, 1.60]
TB, T_TOT, SIG = 20.0, 300.0, np.radians(8.0)
U_P999, DU_P999, RATE_LIMIT = 0.259, 0.00829, 0.03

# fork constants, read from latcontrol_vehicle_tunes.py at the lines cited
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]       # :175-176 deg/s per torque
FF_RATE_GAIN, FF_RATE_RC = 0.5, 0.10                                     # :179, :184
HOLD_LEVEL_BP, HOLD_LEVEL_V = [12.5, 17.5], [1.15, 1.45]                 # :270-271
HOLD_SAT = (19.3, 546.0, 3.01)                                           # :272
HYST_BP, HYST_V = [8.0, 12.0, 19.0, 26.0], [3.0, 2.10, 0.96, 0.60]       # :319-320
FRICTION_HYST, RATE_LOOP_GAIN, RATE_LOOP_RC = 0.015, 0.001, 0.01
MOVE_LIMIT = 1.4


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def hold_slope(v):
    k = float(np.interp(v, LP.HOLD_V_BP, LP.HOLD_K_V)) * float(np.interp(v, HOLD_LEVEL_BP, HOLD_LEVEL_V))
    return k                       # torque per deg near small angle (sech^2 ~ 1 at |angle| << sat)


def hyst_band(v):
    return float(np.interp(v, HYST_BP, HYST_V))


def Kff(f, v, k_map, hyst_linear=True):
    """setpoint (m/s^2) -> output torque, the OPEN-LOOP feedforward, complex."""
    jw = 2j * np.pi * np.asarray(f, float)
    G = float(np.interp(v, G_BP, G_V))
    hold = hold_slope(v) / k_map                                   # torque per m/s^2
    hyst = (FRICTION_HYST / hyst_band(v)) / k_map if hyst_linear else 0.0
    rate_tf = jw / (1.0 + jw * FF_RATE_RC)                         # filtered derivative, deg/s per deg
    move = FF_RATE_GAIN * rate_tf / G / k_map
    inner = RATE_LOOP_GAIN * rate_tf / k_map                       # rate-loop reference leg
    return hold + hyst + move + inner


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
    C = {k: np.concatenate(v) for k, v in cols.items()}
    vm = np.concatenate(vm)
    jw = 2j * np.pi * np.maximum(f, 1e-9)
    SRi = C["SR"] / jw[None, :]
    fit = (f >= 0.2) & (f <= 1.0)
    k_map = abs(np.sum(np.conj(SRi[:, fit]) * C["M"][:, fit]) / np.sum(np.abs(SRi[:, fit]) ** 2))
    Suu = xs(C["U"], C["U"]).real
    Szz = xs(C["Z"], C["Z"]).real
    return dict(f=f, n=len(vm), v=float(np.median(vm)), k_map=k_map,
                P=xs(C["UFF"], C["M"]) / xs(C["UFF"], C["U"]),
                V=xs(C["M"], C["Y"]) / np.maximum(xs(C["M"], C["M"]).real, 1e-300),
                T_ZM=xs(C["Z"], C["M"]) / np.maximum(Szz, 1e-300),
                T_ZU=xs(C["Z"], C["U"]) / np.maximum(Szz, 1e-300),
                coh_ZM=np.abs(xs(C["Z"], C["M"])) ** 2 / np.maximum(Szz * xs(C["M"], C["M"]).real, 1e-300),
                pM=xs(C["M"], C["M"]).real * PSD_SCALE, pU=Suu * PSD_SCALE,
                pA=xs(SRi, SRi).real * PSD_SCALE, pY=xs(C["Y"], C["Y"]).real * PSD_SCALE)


def main():
    fams = {}
    for r, g in LP.GROUPS.items():
        fams.setdefault(g, []).append(r)
    fams["ALL_T64"] = fams["T64"] + fams["T64B"]
    st = {bn: bin_state(fams["ALL_T64"], lo, hi) for bn, lo, hi in BINS}
    stV = {bn: bin_state(fams["V282"], lo, hi) for bn, lo, hi in BINS}

    print("=" * 122)
    print("CONTROL: does the code-exact feedforward chain EXPLAIN the measured Z -> M transfer?")
    print("  T_pred = P*(Kff + C_fb)/(1 + P*C_fb)   vs   T_meas = S_ZM/S_ZZ   (H1, instrument = Z)")
    for bn, _, _ in BINS:
        S = st[bn]
        f, v, km = S["f"], S["v"], S["k_map"]
        C = LP.c_fb_analytic(f, 1.0, float(LP.ki_of(v, 0.3, 0.0)), 14.0, float(LP.low_speed_factor(v)),
                             notch_f0=float(LP.mode_hz(v)), q=1.0)
        K = Kff(f, v, km)
        L = S["P"] * C
        Tp = S["P"] * (K + C) / (1 + L)
        Tloop = L / (1 + L)
        print(f"\n   v={v:.1f} m/s  k_map={km:.4f}  hold {hold_slope(v):.5f} t/deg  "
              f"G {np.interp(v,G_BP,G_V):.0f} deg/s/t  hyst band {hyst_band(v):.2f} deg")
        print(f"   {'f':>5s} {'|Kff|':>7s} {'|Cfb|':>7s} {'Kff/Cfb':>8s} {'|T_pred|':>9s} {'|T_meas|':>9s}"
              f" {'ratio':>6s} {'coh':>5s} | {'|T_loop|':>9s}  x vs loop")
        for fl in LINES + [0.68, 1.76]:
            i = int(np.argmin(np.abs(f - fl)))
            print(f"   {f[i]:5.2f} {abs(K[i]):7.4f} {abs(C[i]):7.4f} {abs(K[i]/C[i]):8.2f}"
                  f" {abs(Tp[i]):9.3f} {abs(S['T_ZM'][i]):9.3f} {abs(S['T_ZM'][i]/Tp[i]):6.2f}"
                  f" {S['coh_ZM'][i]:5.2f} | {abs(Tloop[i]):9.3f} {abs(Tp[i]/Tloop[i]):6.2f}")

    print()
    print("=" * 122)
    print(f"FINAL SPEC -- injection on `setpoint`, T_tot={T_TOT:.0f} s, sigma_phi={np.degrees(SIG):.0f} deg,")
    print("             sized on the CODE-EXACT T_pred (the conservative of T_pred / T_meas is used)")
    spec = {}
    for bn, _, _ in BINS:
        S, SV = st[bn], stV[bn]
        f, v, km = S["f"], S["v"], S["k_map"]
        C = LP.c_fb_analytic(f, 1.0, float(LP.ki_of(v, 0.3, 0.0)), 14.0, float(LP.low_speed_factor(v)),
                             notch_f0=float(LP.mode_hz(v)), q=1.0)
        K = Kff(f, v, km)
        L = S["P"] * C
        Tp = S["P"] * (K + C) / (1 + L)
        Uinj = (K + C) / (1 + L)                      # setpoint -> command
        band = (f >= 0.6) & (f < 2.0)
        df = f[1] - f[0]
        rows, amps, freqs = [], [], []
        for fl in LINES:
            i = int(np.argmin(np.abs(f - fl)))
            mot = np.sqrt((S["pM"][i] + abs(S["P"][i]) ** 2 * S["pU"][i]) / (2 * T_TOT)) / SIG
            Tuse = min(abs(Tp[i]), abs(S["T_ZM"][i]))      # conservative: the SMALLER transfer -> bigger A
            A = mot / max(Tuse, 1e-6)
            rows.append(dict(f=float(f[i]), A=float(A), Tp=float(abs(Tp[i])), Tm=float(abs(S["T_ZM"][i])),
                             dU=float(A * abs(Uinj[i])), ang=float(mot / km),
                             angdes=float(A / km), y=float(abs(S["V"][i]) * mot),
                             yaw=float(np.degrees(abs(S["V"][i]) * mot / v))))
            amps.append(A)
            freqs.append(float(f[i]))
        # build the burst (Schroeder phases, centre-referenced, 2 s raised-cosine taper)
        t = np.arange(0, TB, 1 / FS)
        tc = t - TB / 2
        env = np.ones_like(t)
        nt = int(2.0 * FS)
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(nt) / nt))
        env[:nt], env[-nt:] = ramp, ramp[::-1]
        N = len(freqs)
        ph = [-np.pi * k * (k + 1) / N for k in range(N)]
        mk = lambda gains: env * sum(np.sqrt(2) * a * g * np.cos(2 * np.pi * fr * tc + p + pg)
                                     for fr, a, p, (g, pg) in zip(freqs, amps, ph, gains))
        idx = [int(np.argmin(np.abs(f - fr))) for fr in freqs]
        probe = mk([(1.0, 0.0)] * N)
        ucmd = mk([(abs(Uinj[i]), np.angle(Uinj[i])) for i in idx])
        angw = mk([(abs(Tp[i]) / km, np.angle(Tp[i])) for i in idx])
        ylat = mk([(abs(S["V"][i] * Tp[i]), np.angle(S["V"][i] * Tp[i])) for i in idx])
        dev = np.cumsum(np.cumsum(ylat) / FS) / FS
        angdes_pk = np.max(np.abs(probe)) / km
        ambA = float(np.sqrt(np.sum(S["pA"][band]) * df))
        ambA_V = float(np.sqrt(np.sum(SV["pA"][band]) * df))
        ambY = float(np.sqrt(np.sum(S["pY"][band]) * df))
        print(f"\n   --- v = {v:.1f} m/s  (n={S['n']}) ---")
        print(f"   {'f Hz':>5s} {'A rms':>7s} {'|T_pred|':>9s} {'|T_meas|':>9s} {'dU':>7s} {'wheel deg':>10s}"
              f" {'ang_des':>8s} {'latacc':>8s} {'yaw d/s':>8s}")
        for R in rows:
            print(f"   {R['f']:5.2f} {R['A']:7.4f} {R['Tp']:9.3f} {R['Tm']:9.3f} {R['dU']:7.4f}"
                  f" {R['ang']:10.3f} {R['angdes']:8.3f} {R['y']:8.4f} {R['yaw']:8.3f}")
        print(f"   BURST {TB:.0f} s: setpoint probe rms {np.sqrt(np.mean(probe**2)):.4f} peak "
              f"{np.max(np.abs(probe)):.4f} m/s2   (ambient in-band setpoint content ~0.020)")
        print(f"     angle_des excursion peak {angdes_pk:.3f} deg  vs hysteresis band {hyst_band(v):.2f} deg"
              f"  -> {'LINEAR, ok' if 2*angdes_pk < 0.6*hyst_band(v) else 'RAILS -- shrink or accept a sign-like term'}")
        print(f"     command  rms {np.sqrt(np.mean(ucmd**2)):.5f} peak {np.max(np.abs(ucmd)):.5f}"
              f"  = {100*np.max(np.abs(ucmd)):.2f}% of rail, {100*np.max(np.abs(ucmd))/U_P999:.1f}% of the flown p99.9")
        sl = float(np.max(np.abs(np.diff(ucmd))))
        print(f"     slew     {sl:.5f}/frame = {100*sl/RATE_LIMIT:.1f}% of 0.03; ambient p99.9 + probe = "
              f"{100*(DU_P999+sl)/RATE_LIMIT:.1f}%;  worst flown |u| + probe = {U_P999+np.max(np.abs(ucmd)):.3f}")
        wr = float(np.sqrt(np.mean(angw ** 2)))
        print(f"     wheel    rms {wr:.3f} peak {np.max(np.abs(angw)):.3f} deg  (ambient rev6.4 {ambA:.3f},"
              f" V282 {ambA_V:.3f})  -> in-band x{np.sqrt(1+(wr/ambA)**2):.3f}")
        yr = float(np.sqrt(np.mean(ylat ** 2)))
        print(f"     latacc   rms {yr:.4f} peak {np.max(np.abs(ylat)):.4f} m/s2 (ambient {ambY:.4f});"
              f"  yaw rms {np.degrees(yr/v):.4f} peak {np.degrees(np.max(np.abs(ylat))/v):.4f} deg/s")
        print(f"     LANE     peak {1000*np.max(np.abs(dev)):.1f} mm, net offset {1000*dev[-1]:+.1f} mm")
        spec[bn] = dict(v=v, k_map=km, lines=rows, freqs=freqs, amps=[float(a) for a in amps],
                        phases=[float(p) for p in ph], burst_s=TB, T_tot=T_TOT,
                        sigma_phi_deg=float(np.degrees(SIG)),
                        probe_rms=float(np.sqrt(np.mean(probe ** 2))), probe_peak=float(np.max(np.abs(probe))),
                        angdes_peak_deg=float(angdes_pk), hyst_band_deg=hyst_band(v),
                        cmd_rms=float(np.sqrt(np.mean(ucmd ** 2))), cmd_peak=float(np.max(np.abs(ucmd))),
                        slew=sl, wheel_rms=wr, wheel_peak=float(np.max(np.abs(angw))),
                        y_rms=yr, y_peak=float(np.max(np.abs(ylat))),
                        yaw_rms=float(np.degrees(yr / v)),
                        dev_peak_mm=float(1000 * np.max(np.abs(dev))), dev_end_mm=float(1000 * dev[-1]),
                        amb_wheel_t64=ambA, amb_wheel_v282=ambA_V, amb_y=ambY)
    json.dump(spec, open(HERE / "p7_spec.json", "w"), indent=1)
    print("\nwrote p7_spec.json")


if __name__ == "__main__":
    main()
