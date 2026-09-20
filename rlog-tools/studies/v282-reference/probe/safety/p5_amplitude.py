# -*- coding: utf-8 -*-
"""p5 -- THE TWO NUMBERS SIDE BY SIDE, and the waveform that carries them.

THE AMPLITUDE LAW (derivation, all of it algebra on measured spectra):

  A probe line of RMS A (m/s^2, injected at the error sum) drives
        the measurement by  |T| A          with T = L/(1+L)
        the command     by  |C S| A = |T| A / |P|
  A burst of length Tb gives one analysis line of bandwidth 1/Tb; N bursts give N averages.
  The phase-standard-error of an IV transfer estimate with instrument w is

        sigma_phi^2 = (1-g2_wM)/(2 N g2_wM) + (1-g2_wU)/(2 N g2_wU)
                    = [ pM + |P|^2 pU ] / ( 2 * T_tot * (|T| A)^2 )          T_tot = N*Tb

  => |T| A  =  sqrt( (pM + |P|^2 pU) / (2 T_tot) ) / sigma_phi                     (*)

  (*) is the WHOLE ANSWER to the brief's honest question, and it has one remarkable property:
  the left side is the MOTION the probe causes (measurement = wheel angle x k_map) and the right
  side contains NO controller term.  Raising SteerKP, changing the notch, moving the injection
  point, changing LAF -- none of them change the motion you must pay for a given phase precision.
  The only three levers are: total exposure time, the phase precision demanded, and the number
  of frequencies covered.

  The AMPLITUDE you must command, A = (*) / |T|, DOES depend on the config -- which is the
  hazard: the same probe config flown on a higher SteerKP delivers proportionally more motion.
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
HOLE = (0.80, 1.80)            # where the three plant estimators disagree -> what the probe must cover
LINES = [0.85, 1.00, 1.15, 1.35, 1.55, 1.75]
TB = 20.0
CONFIGS = [("rev6.4 as flown", 1.0, 14.0, 0.3, 1.00), ("ARM-KP3", 3.0, 14.0, 0.6, 0.30),
           ("TierB kp8 Q.20", 8.0, 14.0, 0.6, 0.20)]


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def stack(routes, lo, hi):
    cols, vm = None, []
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = (D["vmed"] >= lo) & (D["vmed"] < hi)
        if sel.any():
            if cols is None:
                cols = {k: [] for k in ("Z", "M", "Y", "U", "SR", "UFF", "X")}
                f = D["f"]
            for k in cols:
                cols[k].append(D[k][sel])
            vm.append(D["vmed"][sel])
        D.close()
    if cols is None:
        return None
    return f, np.concatenate(vm), {k: np.concatenate(v) for k, v in cols.items()}


def bin_state(routes, lo, hi):
    r = stack(routes, lo, hi)
    if r is None or len(r[1]) < 4:
        return None
    f, vm, C = r
    jw = 2j * np.pi * np.maximum(f, 1e-9)
    Z, M, Y, U, SR, UFF, X = C["Z"], C["M"], C["Y"], C["U"], C["SR"], C["UFF"], C["X"]
    SRi = SR / jw[None, :]
    fit = (f >= 0.2) & (f <= 1.0)
    k_map = abs(np.sum(np.conj(SRi[:, fit]) * M[:, fit]) / np.sum(np.abs(SRi[:, fit]) ** 2))
    Suu = xs(U, U).real
    return dict(f=f, n=len(vm), v=float(np.median(vm)), k_map=k_map,
                P_ff=xs(UFF, M) / xs(UFF, U),               # IV, instrument = plant feedforward (best coh)
                P_iv=xs(Z, M) / xs(Z, U),                   # IV, instrument = shaped setpoint
                P_dir=xs(U, M) / np.maximum(Suu, 1e-300),   # direct
                V=xs(M, Y) / np.maximum(xs(M, M).real, 1e-300),
                pM=xs(M, M).real * PSD_SCALE, pU=Suu * PSD_SCALE,
                pA=xs(SRi, SRi).real * PSD_SCALE, pSR=xs(SR, SR).real * PSD_SCALE,
                pY=xs(Y, Y).real * PSD_SCALE, pX=xs(X, X).real * PSD_SCALE)


def at(f, arr, f0):
    i = int(np.argmin(np.abs(f - f0)))
    return arr[i], i


def main():
    fams = {}
    for r, g in LP.GROUPS.items():
        fams.setdefault(g, []).append(r)
    fams["ALL_T64"] = fams["T64"] + fams["T64B"]
    st = {}
    for fam in ("ALL_T64", "V282"):
        for bn, lo, hi in BINS:
            s = bin_state(fams[fam], lo, hi)
            if s:
                st[f"{fam}|{bn}"] = s

    print("=" * 126)
    print("1. THE MOTION COST OF IDENTIFICATION  (equation (*)) -- what the wheel MUST move, whatever the config")
    print(f"   lines: {LINES} Hz   burst {TB:.0f} s")
    print(f"   angle RMS added over all {len(LINES)} lines, deg, for a total usable exposure T_tot")
    hdr = f"   {'v m/s':>6s} {'sigma_phi':>10s} |"
    for T in (100, 200, 400, 800):
        hdr += f" {'T=' + str(T) + 's':>9s}"
    hdr += f" | {'ambient V282':>13s} {'ambient rev6.4':>15s}"
    print(hdr)
    band = None
    rows = {}
    for bn, _, _ in BINS:
        S = st[f"ALL_T64|{bn}"]
        SV = st.get(f"V282|{bn}")
        f = S["f"]
        if band is None:
            band = (f >= 0.6) & (f < 2.0)
            df = f[1] - f[0]
        ambA_T = float(np.sqrt(np.sum(S["pA"][band]) * df))
        ambA_V = float(np.sqrt(np.sum(SV["pA"][band]) * df)) if SV else np.nan
        for sig_deg in (5.0, 8.0, 12.0):
            sig = np.radians(sig_deg)
            line = f"   {S['v']:6.1f} {sig_deg:10.1f} |"
            for T in (100, 200, 400, 800):
                tot = 0.0
                for fl in LINES:
                    pM, i = at(f, S["pM"], fl)
                    pU, _ = at(f, S["pU"], fl)
                    P = abs(S["P_ff"][i])
                    mot = np.sqrt((pM + P ** 2 * pU) / (2 * T)) / sig      # m/s^2 of measurement
                    tot += (mot / S["k_map"]) ** 2
                line += f" {np.sqrt(tot):9.3f}"
            line += f" | {ambA_V:13.3f} {ambA_T:15.3f}"
            print(line)
            rows[f"{bn}|{sig_deg}"] = None

    print()
    print("=" * 126)
    print("2. THE SAME BUDGET IN EVERY QUANTITY HE PERCEIVES  (T_tot = 300 s, sigma_phi = 8 deg)")
    print("   per-line and total; 'peak' = Schroeder-phased multisine, crest factor 1.8 on the total")
    T_TOT, SIG = 300.0, np.radians(8.0)
    out = {}
    for bn, _, _ in BINS:
        S, SV = st[f"ALL_T64|{bn}"], st.get(f"V282|{bn}")
        f, v, km = S["f"], S["v"], S["k_map"]
        print(f"\n   --- v = {v:.1f} m/s   n={S['n']}   k_map = {km:.4f} (m/s2)/deg ---")
        print(f"   {'f Hz':>5s} {'|P_ff|':>7s} {'motion':>8s} {'angle':>7s} {'rate':>7s} {'latacc':>8s}"
              f" {'yaw':>7s} {'dev mm':>7s} | {'A_req m/s2, by config':>24s}")
        print(f"   {'':>5s} {'':>7s} {'m/s2':>8s} {'deg':>7s} {'deg/s':>7s} {'m/s2':>8s}"
              f" {'deg/s':>7s} {'':>7s} | " + " ".join(f"{c[0][:11]:>11s}" for c in CONFIGS))
        tot = dict(ang=0.0, rate=0.0, y=0.0, yaw=0.0, dev=0.0, mot=0.0)
        per_line = []
        for fl in LINES:
            pM, i = at(f, S["pM"], fl)
            pU, _ = at(f, S["pU"], fl)
            P = S["P_ff"][i]
            Vg = abs(S["V"][i])
            mot = np.sqrt((pM + abs(P) ** 2 * pU) / (2 * T_TOT)) / SIG
            ang = mot / km
            rate = 2 * np.pi * f[i] * ang
            y = Vg * mot
            yaw = np.degrees(y / v)
            dev = y / (2 * np.pi * f[i]) ** 2 * 1000.0      # mm, sinusoidal steady state
            As = []
            for label, kp, laf, ki, q in CONFIGS:
                C = LP.c_fb_analytic(f, kp, float(LP.ki_of(v, ki, 0.0)), laf,
                                     float(LP.low_speed_factor(v)), notch_f0=float(LP.mode_hz(v)), q=q)
                L = P * C[i]
                Tf = abs(L / (1 + L))
                As.append(mot / max(Tf, 1e-6))
            print(f"   {f[i]:5.2f} {abs(P):7.2f} {mot:8.4f} {ang:7.3f} {rate:7.3f} {y:8.4f}"
                  f" {yaw:7.3f} {dev:7.2f} | " + " ".join(f"{a:11.4f}" for a in As))
            per_line.append(dict(f=float(f[i]), mot=float(mot), ang=float(ang), rate=float(rate),
                                 y=float(y), yaw=float(yaw), dev_mm=float(dev),
                                 A_req={CONFIGS[k][0]: float(As[k]) for k in range(len(CONFIGS))}))
            for k, vv in (("ang", ang), ("rate", rate), ("y", y), ("yaw", yaw), ("dev", dev), ("mot", mot)):
                tot[k] += vv ** 2
        tot = {k: float(np.sqrt(vv)) for k, vv in tot.items()}
        ambient = {k: float(np.sqrt(np.sum(S[p][band]) * df)) for k, p in
                   (("ang", "pA"), ("rate", "pSR"), ("y", "pY"))}
        ambientV = {k: float(np.sqrt(np.sum(SV[p][band]) * df)) for k, p in
                    (("ang", "pA"), ("rate", "pSR"), ("y", "pY"))} if SV else {}
        print(f"   {'TOTAL':>5s} {'':7s} {tot['mot']:8.4f} {tot['ang']:7.3f} {tot['rate']:7.3f}"
              f" {tot['y']:8.4f} {tot['yaw']:7.3f} {tot['dev']:7.2f}   (RMS over lines)")
        print(f"   {'peak':>5s} {'':7s} {'':8s} {1.8*tot['ang']:7.3f} {1.8*tot['rate']:7.3f}"
              f" {1.8*tot['y']:8.4f} {1.8*tot['yaw']:7.3f} {1.8*tot['dev']:7.2f}   (crest 1.8)")
        print(f"   ambient rev6.4 0.6-2.0 Hz: angle {ambient['ang']:.3f} deg  rate {ambient['rate']:.3f} deg/s"
              f"  latacc {ambient['y']:.4f} m/s2  yaw {np.degrees(ambient['y']/v):.3f} deg/s")
        if ambientV:
            print(f"   ambient V282   0.6-2.0 Hz: angle {ambientV['ang']:.3f} deg  rate {ambientV['rate']:.3f} deg/s"
                  f"  latacc {ambientV['y']:.4f} m/s2  yaw {np.degrees(ambientV['y']/v):.3f} deg/s")
        print(f"   probe / rev6.4 ambient, in band:  angle x{np.sqrt(1+(tot['ang']/ambient['ang'])**2):.3f}"
              f"  rate x{np.sqrt(1+(tot['rate']/ambient['rate'])**2):.3f}"
              f"  latacc x{np.sqrt(1+(tot['y']/ambient['y'])**2):.3f}")
        out[bn] = dict(v=v, k_map=km, lines=per_line, total=tot, ambient=ambient, ambientV=ambientV,
                       n=S["n"])

    print()
    print("=" * 126)
    print("3. WHAT THE PROBE DOES TO THE GOAL METRIC ITSELF (J numerator), 0.15-2.4 Hz")
    for bn, _, _ in BINS:
        S = st[f"ALL_T64|{bn}"]
        f = S["f"]
        mb = (f >= 0.15) & (f < 2.4)
        dfm = f[1] - f[0]
        demand = float(np.sqrt(np.sum(S["pX"][mb]) * dfm))
        py = out[bn]["total"]["y"]
        print(f"   v={S['v']:4.1f}  in-band DEMAND rms {demand:.4f} m/s2   probe-driven Y rms {py:.4f} m/s2"
              f"   -> dJ = {(py/demand)**2:.4f}  (the probe's own contribution to J)")

    # ---- lane deviation, numerically, on the actual burst ----
    print()
    print("=" * 126)
    print("4. LANE DEVIATION over ONE 20 s burst -- numeric double integral of the probe-driven lateral accel")
    print("   waveform: Schroeder-phased multisine, phases referenced to the BURST CENTRE (even symmetry),")
    print("   raised-cosine 2 s taper.  Even symmetry forces both moments of a(t) to zero, so the burst")
    print("   leaves no net lateral velocity and no net lateral offset.")
    dt = 1 / FS
    tt = np.arange(0, TB, dt)
    N = len(LINES)
    for bn, _, _ in BINS:
        R = out[bn]
        env = np.ones_like(tt)
        nt = int(2.0 * FS)
        ramp = 0.5 * (1 - np.cos(np.pi * np.arange(nt) / nt))
        env[:nt] = ramp
        env[-nt:] = ramp[::-1]
        a = np.zeros_like(tt)
        for k, L in enumerate(R["lines"]):
            th = -np.pi * k * (k + 1) / N            # Schroeder
            a += np.sqrt(2) * L["y"] * np.cos(2 * np.pi * L["f"] * (tt - TB / 2) + th)
        a = a * env
        vlat = np.cumsum(a) * dt
        ylat = np.cumsum(vlat) * dt
        crest = float(np.max(np.abs(a)) / np.sqrt(np.mean(a ** 2)))
        print(f"   v={R['v']:4.1f}  a_lat rms {np.sqrt(np.mean(a**2)):.4f} peak {np.max(np.abs(a)):.4f} m/s2"
              f"  crest {crest:.2f} | peak lateral deviation {1000*np.max(np.abs(ylat)):6.1f} mm"
              f"  end offset {1000*ylat[-1]:+6.1f} mm  end v_lat {1000*vlat[-1]:+6.1f} mm/s")
        R["burst"] = dict(a_rms=float(np.sqrt(np.mean(a ** 2))), a_peak=float(np.max(np.abs(a))),
                          crest=crest, dev_peak_mm=float(1000 * np.max(np.abs(ylat))),
                          dev_end_mm=float(1000 * ylat[-1]))

    json.dump(out, open(HERE / "p5_out.json", "w"), indent=1)
    print("\nwrote p5_out.json")


if __name__ == "__main__":
    main()
