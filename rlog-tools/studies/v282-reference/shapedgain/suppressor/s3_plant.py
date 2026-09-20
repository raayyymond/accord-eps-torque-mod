# -*- coding: utf-8 -*-
"""S3 -- (a) WHO IS THE 1.8-3.5 Hz COMMAND?  The inner rate damper's reply to the wheel, or a
demand?  (b) the measured command -> wheel-rate plant G(f), with its PHASE; (c) what changing the
inner rate-loop gain does, by algebra on G alone -- including where it stops damping.

The inner rate loop, from source (latcontrol_torque.py:663-667, tunes :2644-2646):
    rate_meas    = FirstOrderFilter(steeringRateDeg, rc = 0.01)
    inner_torque = -(friction_z + g(v) * (angle_des_rate - rate_meas)),   g(v) = G0*min(1, 12/v)
    ff_torque   += inner_torque ;  U = (p + i + f)/LAF  with  f = ff_torque * LAF
so the part of U that answers the MEASURED wheel is exactly  + g(v) * rate_meas.  It is
reconstructible from the log with no free parameter.

G(f) = command -> steeringRateDeg INCLUDING the whole round-trip delay and the firmware, so no delay
model enters.  The logged command CONTAINS the rate loop's own reply, so the naive S_ur/S_uu is
biased; the instrument W = U - g*rate_meas - (p+i)/LAF (every known feedback path removed, all of
them exactly reconstructible) restores it.  The self-test demonstrates both.

With the rate loop closed at g0 and re-closed at g1, for the SAME exogenous command and the SAME
road disturbance:
    sr = G*(u_ext + g*F_rc*sr)   =>   sr/u_ext = G/(1 - g*F_rc*G)
    ratio(g1 vs g0) = |1 - g0*F_rc*G| / |1 - g1*F_rc*G|
< 1 attenuates, > 1 de-damps.  ALGEBRA ON A MEASURED TRANSFER, per band.

usage: python s3_plant.py > out/S3-PLANT.txt
"""
import json

import numpy as np
from scipy import signal as sg

import suplib as S

ROUTES = S.T64 + ["0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"] + S.V282R
BINS = [("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)]
BANDS = [(0.15, 0.60), (0.60, 1.20), (1.20, 1.80), (1.80, 2.50), (2.50, 3.50), (3.50, 5.00), (5.00, 8.00)]
DOSES = [(0.0, True), (0.0006, True), (0.001, True), (0.002, True), (0.003, True),
         (0.001, False), (0.002, False), (0.003, False)]


def fftw(x, n, nps=2048):
    w = np.hanning(nps)
    return np.array([np.fft.rfft((x[k:k + nps] - x[k:k + nps].mean()) * w)
                     for k in range(0, n - nps, nps // 2)])


def band_iv(Sw_r, Sw_u, sel, w=None):
    """Band IV: PER-BIN ratios, magnitudes averaged with power weights (never a phasor average --
    the plant's delay rotates the phase across a band and a phasor average would read the magnitude
    low), and the phase from the power-weighted phasor mean of the per-bin unit vectors."""
    g = Sw_r[sel] / np.where(np.abs(Sw_u[sel]) < 1e-300, 1e-300, Sw_u[sel])
    ww = np.abs(Sw_u[sel]) if w is None else w[sel]
    mag = float(np.sum(ww * np.abs(g)) / max(np.sum(ww), 1e-300))
    ph = float(np.angle(np.sum(ww * g / np.maximum(np.abs(g), 1e-300))))
    return mag * np.exp(1j * ph)


def _self_test():
    """Positive control: a KNOWN plant with a KNOWN delay, an exogenous command, a road disturbance
    3x the plant's own contribution, and a KNOWN inner rate loop closed on the measured rate.
      - the band IV must recover the known gain and delay,
      - the naive S_ur/S_uu must NOT (it is biased by the rate loop's own reply),
      - the dose formula must predict the simulated change in shake-band wheel-rate rms."""
    rng = np.random.default_rng(17)
    n = 900 * 100
    g_plant, nd = 200.0, 6                      # deg/s per unit command, 60 ms round trip
    g0, g1 = 0.0008, 0.0016
    d = sg.sosfiltfilt(sg.butter(2, [1.5, 4.0], btype="band", fs=S.FS, output="sos"),
                       rng.standard_normal(n)) * 4.0
    ue = sg.sosfiltfilt(sg.butter(2, [0.1, 3.0], btype="band", fs=S.FS, output="sos"),
                        rng.standard_normal(n)) * 0.01
    a = S.DT / (S.RATE_LOOP_RC + S.DT)
    out = {}
    for gg in (g0, g1):
        # the frame order the fork runs: this frame's rate_meas is filtered from THIS frame's
        # carState, and the command that answers it only reaches the wheel nd frames later.
        sr = np.zeros(n); u = np.zeros(n); rm = 0.0
        for k in range(n):
            sr[k] = g_plant * (u[k - nd] if k >= nd else 0.0) + d[k]
            rm += a * (sr[k] - rm)
            u[k] = ue[k] + gg * rm
        out[gg] = (u.copy(), sr.copy())
    nps = 2048
    f = np.fft.rfftfreq(nps, S.DT)
    U0, R0 = fftw(out[g0][0], n, nps), fftw(out[g0][1], n, nps)
    W0 = fftw(out[g0][0] - g0 * S.fof_run(out[g0][1], S.RATE_LOOP_RC, x0=0.0), n, nps)
    Swr, Swu = np.mean(np.conj(W0) * R0, 0), np.mean(np.conj(W0) * U0, 0)
    Sur, Suu = np.mean(np.conj(U0) * R0, 0), np.mean(np.abs(U0) ** 2, 0)
    sel = (f >= 1.8) & (f <= 3.5)
    Giv = band_iv(Swr, Swu, sel)
    Gdir = band_iv(Sur, Suu.astype(complex), sel)
    tru = g_plant * np.exp(-2j * np.pi * 2.6 * nd * S.DT)      # band-centre phase, for reference
    assert abs(abs(Giv) / g_plant - 1) < 0.10, (abs(Giv), abs(Gdir))
    assert abs(abs(Gdir) / g_plant - 1) > 0.25, (abs(Giv), abs(Gdir))
    # the dose formula, per bin, against the simulated re-run
    Frc = S.fof_H(f, S.RATE_LOOP_RC)
    Gf = Swr / Swu
    pred = np.abs(1 - g0 * Frc * Gf) / np.abs(1 - g1 * Frc * Gf)
    Psr = np.mean(np.abs(R0) ** 2, 0)
    pr = float(np.sqrt(np.sum(Psr[sel] * pred[sel] ** 2) / np.sum(Psr[sel])))
    act = S.bandrms(out[g1][1], 1.8, 3.5) / S.bandrms(out[g0][1], 1.8, 3.5)
    assert abs(pr / act - 1) < 0.10, (pr, act)
    return (f"s3 self-test OK: band IV recovers |G| {abs(Giv):.0f} vs known {g_plant:.0f} "
            f"(phase {np.degrees(np.angle(Giv)):+.0f} deg vs {np.degrees(np.angle(tru)):+.0f}); the naive "
            f"estimator reads {abs(Gdir):.0f}; the dose formula predicts {pr:.3f} vs simulated {act:.3f}")


def main():
    print(S._self_test())
    print(_self_test())
    res = {}
    for rk in ROUTES:
        meta = S.FLOWN[rk]
        N = S.load(rk)
        g0_tog = meta["rlg"] if meta["rlg"] is not None else 0.0
        rm = S.fof_run(N["SR"], S.RATE_LOOP_RC, x0=N["SR"][0])
        rterm = S.rate_loop_gain(N["v"], g0_tog) * rm            # the +g*rate_meas part of U
        runs = S.runs_of(N, 15.0, 99.0, 30.0)
        if not runs:
            del N
            continue
        m = np.zeros(len(N["t"]), bool)
        for a, b in runs:
            m[a:b] = True
        uff = N["F"] / meta["laf"]
        ufb = (N["P"] + N["I"]) / meta["laf"]
        N["W"] = N["U"] - rterm - ufb
        print("\n" + "=" * 140)
        print(f"{rk}  fam {meta['fam']}  AccordRateLoopGain flown {g0_tog}  DOB {meta['dob']}  "
              f"{m.sum()/S.FS:.0f} s >= 15 m/s   median v {np.median(N['v'][m]):.1f}")
        sh = {k: S.bandrms(x[m], *S.SHAKE) for k, x in
              (("U", N["U"]), ("u_ff", uff), ("u_fb", ufb), ("g*rate_meas", rterm), ("W=exog", N["W"]))}
        gp = {k: S.bandrms(x[m], *S.GAP) for k, x in
              (("U", N["U"]), ("u_ff", uff), ("u_fb", ufb), ("g*rate_meas", rterm), ("W=exog", N["W"]))}
        print(f"  WHEEL RATE (time domain, 4th-order band-pass): 1.8-3.5 Hz rms "
              f"{S.bandrms(N['SR'][m], *S.SHAKE):.3f} deg/s    0.15-0.60 Hz rms "
              f"{S.bandrms(N['SR'][m], *S.GAP):.3f} deg/s")
        print("  COMMAND DECOMPOSITION (band rms, torque units; the parts do not add in rms, they are phased)")
        print(f"    1.8-3.5 Hz  " + "   ".join(f"{k} {v:.5f} ({v/max(sh['U'],1e-12):.2f}xU)" for k, v in sh.items()))
        print(f"    0.15-0.60Hz " + "   ".join(f"{k} {v:.5f} ({v/max(gp['U'],1e-12):.2f}xU)" for k, v in gp.items()))
        row = dict(fam=meta["fam"], g0=g0_tog, sh={k: float(v) for k, v in sh.items()},
                   gp={k: float(v) for k, v in gp.items()}, bins={})
        for tag, v0, v1 in BINS:
            fr, sp, vs = S.spectra(N, ("U", "SR", "X", "W"), v0, v1, 2048, 30.0)
            if len(vs) < 4:
                del sp
                continue
            Swr = np.mean(np.conj(sp["W"]) * sp["SR"], 0)
            Swu = np.mean(np.conj(sp["W"]) * sp["U"], 0)
            Sww = np.mean(np.abs(sp["W"]) ** 2, 0)
            Suu = np.mean(np.abs(sp["U"]) ** 2, 0)
            Sur = np.mean(np.conj(sp["U"]) * sp["SR"], 0)
            Srr = np.mean(np.abs(sp["SR"]) ** 2, 0)
            Sxu = np.mean(np.conj(sp["X"]) * sp["U"], 0)
            Sxr = np.mean(np.conj(sp["X"]) * sp["SR"], 0)
            vmed = float(np.median(vs))
            g0e = S.rate_loop_gain(vmed, g0_tog)
            Frc = S.fof_H(fr, S.RATE_LOOP_RC)
            Gf = Swr / np.where(np.abs(Swu) < 1e-300, 1e-300, Swu)     # per-bin IV (noisy; used band-wise)
            print(f"\n  --- speed bin {tag}: {len(vs)} windows, median v {vmed:.1f} m/s, "
                  f"g_eff {g0e:.5f} (toggle {g0_tog} x min(1,12/v)) ---")
            print(f"    {'band Hz':>11s} {'|G| IV':>8s} {'argG':>6s} {'coh(W,U)':>9s} {'|G| dir':>8s} "
                  f"{'argdir':>7s} {'coh(U,sr)':>10s} {'|G| X-IV':>9s} {'sr rms':>8s} {'g0*|G|':>7s}")
            bb = {}
            for f1, f2 in BANDS:
                sel = (fr >= f1) & (fr < f2)
                if sel.sum() < 1:
                    continue
                Giv = band_iv(Swr, Swu, sel)
                Gd = band_iv(Sur, Suu.astype(complex), sel)
                Gx = band_iv(Sxr, Sxu, sel)
                cwu = float(np.sum(np.abs(Swu[sel])) ** 2 / max(np.sum(Sww[sel]) * np.sum(Suu[sel]), 1e-300))
                cus = float(np.sum(np.abs(Sur[sel])) ** 2 / max(np.sum(Suu[sel]) * np.sum(Srr[sel]), 1e-300))
                srrms = float(np.sqrt(np.sum(Srr[sel]) / len(vs) * 2 / (np.sum(np.hanning(2048) ** 2) * 2048)
                                      * 2048 ** 2 / 2048))
                print(f"    {f1:5.2f}-{f2:4.2f} {abs(Giv):8.0f} {np.degrees(np.angle(Giv)):6.0f} {cwu:9.2f} "
                      f"{abs(Gd):8.0f} {np.degrees(np.angle(Gd)):7.0f} {cus:10.2f} {abs(Gx):9.0f} "
                      f"{srrms:8.3f} {g0e*abs(Giv):7.2f}")
                bb[f"{f1}-{f2}"] = dict(G=[float(abs(Giv)), float(np.degrees(np.angle(Giv)))],
                                        Gdir=[float(abs(Gd)), float(np.degrees(np.angle(Gd)))],
                                        Gx=float(abs(Gx)), cohWU=cwu, cohUSR=cus, srrms=srrms)
            print(f"    INNER-LOOP MARGIN: min |1 - g1 F G| over 0.10-8.0 Hz (a value below 1 is AMPLIFICATION at"
                  f" that frequency; below ~0.5 is a resonance).  Above 8 Hz nothing is measurable here.")
            sel8 = (fr >= 0.10) & (fr <= 8.0)
            for g1t, taper in DOSES:
                g1e = S.rate_loop_gain(vmed, g1t) if taper else g1t
                den = np.abs(1 - g1e * Frc * Gf)[sel8]
                j = int(np.argmin(den))
                print(f"      g1 {g1t}{'' if taper else ' no-taper':>9s}  min|1-gFG| {den[j]:.3f} at "
                      f"{fr[sel8][j]:.2f} Hz   max|gFG| {np.max(np.abs(g1e*Frc*Gf)[sel8]):.2f}")
            print(f"    RATE-LOOP DOSE, ratio = |1-g0 F G| / |1-g1 F G| per band ( <1 attenuates, >1 de-damps ),")
            print(f"    G from the IV estimate, power-weighted inside each band by the measured wheel-rate spectrum:")
            print(f"    {'g1':>16s} {'g1_eff':>8s} " + "".join(f"{f'{a}-{b}':>10s}" for a, b in BANDS))
            dd = []
            for g1t, taper in DOSES:
                g1e = S.rate_loop_gain(vmed, g1t) if taper else g1t
                rat = np.abs(1 - g0e * Frc * Gf) / np.abs(1 - g1e * Frc * Gf)
                cells, per = [], {}
                for f1, f2 in BANDS:
                    sel = (fr >= f1) & (fr < f2)
                    w = Srr[sel]
                    r = float(np.sqrt(np.sum(w * rat[sel] ** 2) / max(np.sum(w), 1e-300)))
                    cells.append(f"{r:10.3f}")
                    per[f"{f1}-{f2}"] = r
                lbl = f"{g1t}{'' if taper else ' no-taper'}"
                print(f"    {lbl:>16s} {g1e:8.5f} " + "".join(cells))
                # the same ratio computed from the BAND-AVERAGED G (robust to per-bin noise)
                cells2, per2 = [], {}
                for f1, f2 in BANDS:
                    Gb = np.exp(1j * np.radians(bb[f"{f1}-{f2}"]["G"][1])) * bb[f"{f1}-{f2}"]["G"][0]
                    Fb = S.fof_H(0.5 * (f1 + f2), S.RATE_LOOP_RC)
                    r2 = float(abs(1 - g0e * Fb * Gb) / abs(1 - g1e * Fb * Gb))
                    cells2.append(f"{r2:10.3f}")
                    per2[f"{f1}-{f2}"] = r2
                print(f"    {'  (band-avg G)':>16s} {'':8s} " + "".join(cells2))
                dd.append(dict(g1=g1t, taper=taper, g1e=g1e, bands=per, bands_bandavg=per2))
            row["bins"][tag] = dict(nwin=len(vs), v=vmed, g0e=g0e, bands=bb, doses=dd)
            del sp
        res[rk] = row
        del N
    json.dump(dict(bands=BANDS, res=res), open(S.OUT / "s3_plant.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
