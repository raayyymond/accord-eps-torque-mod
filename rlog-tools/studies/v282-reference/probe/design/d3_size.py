# -*- coding: utf-8 -*-
"""d3 -- SIZE the probe from the logs, and price every tone in the four things it costs.

Sizing identity (derived in d1's docstring, algebra on the definition of coherence):
    coh(W, e)_new = rho / (1 + rho) ,   rho = g2_old(f) * r(f) ,   r = Sww/Szz per bin
so the required per-bin probe power is  Sww = Szz * rho_target / g2_old, with everything on the
right-hand side MEASURED on the metric's own windows.

Estimator variance (Bendat & Piersol, output-noise case, which is exactly this case because the
probe is deterministic and noise-free):
    sigma(|H|)/|H| = sigma_phase(rad) = sqrt((1 - g2) / (2 * n_eff * g2))
with n_eff = n / 1.125 for 50 % overlapped Hann (the periodogram overlap correlation).

Prices, per tone, all measured (H1, Z exogenous => unbiased; the coherence column is printed beside
every one so a number read off a low-coherence bin can be discounted):
    command    A * |Tzu|   unit torque          (rail + the Honda 0.03/frame slew limiter)
    wheel rate A * |Tzsr|  deg/s                (the shake axis the operator feels)
    wheel angle A*|Tzsr|/(2 pi f)  deg          (vs the measured backlash band 2F/k)
    path       A * |Tzy|   m/s^2                (achieved lateral accel -- the path wiggle)
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS, NPS = 100.0, 1024
DF = FS / NPS
FAM = "T64"                     # rev 6.4 as flown -- the config the probe would fly on
WIN_PER_SEC = None              # measured below


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def coh(A, B):
    return np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)


def pool(fam, vlo=15.0):
    routes = [r for r, g in LP.GROUPS.items() if g == fam]
    cols, vm, sec = None, [], 0.0
    meta = json.load(open(F1 / "f1_meta.json"))
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = D["vmed"] >= vlo
        if cols is None:
            cols = {k: [] for k in ("X", "Y", "Z", "M", "UFB", "UFF", "U", "SR")}
            f = D["f"]
        for k in cols:
            cols[k].append(D[k][sel])
        vm.append(D["vmed"][sel]); sec += meta[r]["sec"]
        del D
    return dict(f=f, sec=sec, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def hann_tone_gain():
    """NUMERIC check of the |rfft| gain for a unit-amplitude cosine exactly on a bin, Hann, detrended."""
    w = sg.get_window("hann", NPS)
    k = 10
    t = np.arange(NPS) / FS
    x = np.cos(2 * np.pi * k * DF * t)
    return float(np.abs(np.fft.rfft(sg.detrend(x) * w))[k])


if __name__ == "__main__":
    G = hann_tone_gain()
    print(f"NUMERIC normalisation check: a unit-amplitude cosine on a bin gives |rfft| = {G:.3f} "
          f"(analytic N/4 = {NPS/4:.0f}).  Amplitude = |X_k| / {G:.1f}.\n")

    W = pool(FAM)
    f = W["f"]
    Z, M, U, Y, SR, UFB = W["Z"], W["M"], W["U"], W["Y"], W["SR"], W["UFB"]
    E = Z - M
    n = Z.shape[0]
    Szz = xs(Z, Z).real
    g2_ze, g2_zu, g2_zm, g2_zy, g2_zsr = coh(Z, E), coh(Z, U), coh(Z, M), coh(Z, Y), coh(Z, SR)
    Tze = np.abs(xs(Z, E) / Szz); Tzu = np.abs(xs(Z, U) / Szz)
    Tzm = np.abs(xs(Z, M) / Szz); Tzy = np.abs(xs(Z, Y) / Szz); Tzsr = np.abs(xs(Z, SR) / Szz)
    WIN_PER_SEC = n / W["sec"]
    print(f"family {FAM}: n = {n} windows over {W['sec']:.0f} s of qualifying runs "
          f"=> {WIN_PER_SEC:.4f} windows/s (median speed {np.median(W['vmed']):.1f} m/s)\n")

    # ---- candidate tone sets on the 10.24 s grid
    SETS = {
        "A 4 tones 0.68-1.56 (3-bin)": [7, 10, 13, 16],
        "B 6 tones 0.68-2.05 (3-bin)": [7, 10, 13, 16, 19, 22],
        "C 5 tones 0.59-1.46 (3-bin)": [6, 9, 12, 15],
        "D 8 tones 0.68-2.05 (2-bin)": [7, 9, 11, 13, 15, 17, 19, 21],
    }
    RHO_T = {0.5: 1.0, 0.6: 1.5, 0.7: 7.0 / 3.0, 0.8: 4.0}

    for target, rho in [(0.5, 1.0), (0.7, 7.0 / 3.0)]:
        print(f"=== TARGET coherence {target:.1f}  (rho = {rho:.3f})")
        for name, ks in SETS.items():
            ks = np.array(ks)
            A = np.sqrt(Szz[ks] * rho / np.maximum(g2_ze[ks], 1e-6)) / G
            rms = float(np.sqrt(np.sum(A ** 2) / 2))
            print(f"\n  {name}:  probe rms {rms*1000:7.3f} mm/s^2   (peak = CF x rms)")
            print(f"  {'f Hz':>6s} {'g2_ze':>6s} {'r req':>7s} {'A mm/s2':>8s} | "
                  f"{'cmd':>8s} {'rate d/s':>9s} {'ang deg':>8s} {'path':>8s} | "
                  f"{'chZU':>5s} {'chZSR':>6s} {'chZY':>5s}")
            for k, a in zip(ks, A):
                r_req = rho / max(g2_ze[k], 1e-6)
                print(f"  {f[k]:6.3f} {g2_ze[k]:6.3f} {r_req:7.2f} {a*1000:8.3f} | "
                      f"{a*Tzu[k]:8.5f} {a*Tzsr[k]:9.4f} {a*Tzsr[k]/(2*np.pi*f[k]):8.4f} "
                      f"{a*Tzy[k]:8.4f} | {g2_zu[k]:5.2f} {g2_zsr[k]:6.2f} {g2_zy[k]:5.2f}")
            print(f"  {'TOTAL':>6s} {'':6s} {'':7s} {np.sum(A)*1000:8.3f} | "
                  f"{np.sum(A*Tzu[ks]):8.5f} {np.sum(A*Tzsr[ks]):9.4f} "
                  f"{np.sum(A*Tzsr[ks]/(2*np.pi*f[ks])):8.4f} {np.sum(A*Tzy[ks]):8.4f}   (sum of amplitudes)")
            rms_rate = float(np.sqrt(np.sum((A * Tzsr[ks]) ** 2) / 2))
            rms_path = float(np.sqrt(np.sum((A * Tzy[ks]) ** 2) / 2))
            rms_cmd = float(np.sqrt(np.sum((A * Tzu[ks]) ** 2) / 2))
            print(f"  {'RMS':>6s} {'':6s} {'':7s} {rms*1000:8.3f} | {rms_cmd:8.5f} {rms_rate:9.4f} "
                  f"{'':8s} {rms_path:8.4f}")
        print()

    # ---- duration
    print("=== DURATION: windows and seconds of qualifying (engaged, hands-off, >=15 m/s) driving")
    print(f"{'coh':>5s} {'sig_ph 10deg':>13s} {'15deg':>8s} {'20deg':>8s}   (n windows | seconds)")
    for c in (0.4, 0.5, 0.6, 0.7, 0.8):
        row = []
        for deg in (10, 15, 20):
            rad = np.radians(deg)
            n_eff = (1 - c) / (2 * rad ** 2 * c)
            nn = n_eff * 1.125
            row.append(f"{nn:5.1f}|{nn/WIN_PER_SEC:5.0f}s")
        print(f"{c:5.2f} {row[0]:>13s} {row[1]:>8s} {row[2]:>8s}")

    # ---- what the probe does to the goal metric
    print("\n=== METRIC CONTAMINATION: the probe sits INSIDE the 0.15-2.4 Hz metric band")
    mb = (f >= 0.15) & (f <= 2.4)
    Sxx = xs(W["X"], W["X"]).real
    See = xs(E, E).real
    Sxy = xs(W["X"] - Y, W["X"] - Y).real
    for name, ks in [("A 4 tones", [7, 10, 13, 16]), ("B 6 tones", [7, 10, 13, 16, 19, 22])]:
        ks = np.array(ks)
        skirt = np.unique(np.concatenate([ks - 1, ks, ks + 1]))
        fr_num = Sxy[skirt].sum() / Sxy[mb].sum()
        fr_den = Sxx[skirt].sum() / Sxx[mb].sum()
        print(f"  {name}: tone bins +/-1 carry {fr_num*100:5.1f} % of the metric NUMERATOR "
              f"(X-Y power) and {fr_den*100:5.1f} % of its DENOMINATOR today "
              f"=> excluding them costs {max(fr_num,fr_den)*100:.0f} % of the metric's support.")

    np.savez(OUT / "d3_size.npz", f=f, Szz=Szz, g2_ze=g2_ze, g2_zu=g2_zu, g2_zm=g2_zm,
             g2_zy=g2_zy, g2_zsr=g2_zsr, Tze=Tze, Tzu=Tzu, Tzm=Tzm, Tzy=Tzy, Tzsr=Tzsr,
             n=n, sec=W["sec"], win_per_sec=WIN_PER_SEC, G=G)
    print("\nwrote out/d3_size.npz")
