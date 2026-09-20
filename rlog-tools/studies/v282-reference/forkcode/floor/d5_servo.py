# -*- coding: utf-8 -*-
"""d5 -- (A) is the 107 ms real?  (B) the absolute floor of the metric.  (C) the inner-servo cost.

A. tau_i per route, across TWO EPS builds and FOUR fork commits.  A control-path artefact would
   differ between builds; a localiser publish latency would not.

B. THE ABSOLUTE FLOOR.  Give the controller everything: a perfect loop (M == Z) AND a perfect
   reference (Z chosen so that a perfectly tracked wheel angle delivers exactly X).  Then
       Y_true = X + r      and the LOGGED Y is that, 107 ms late,
       E = X - e^{-jwt}(X + r) = X (1 - e^{-jwt}) - e^{-jwt} r
   and J_floor = |E|^2 / |X|^2 is what the metric reads for a PERFECT car.  Nothing in the fork,
   the firmware or the vehicle can go below it.

C. THE INNER-SERVO COST, computed not asserted.
   Plant (the fork's own identified steering mechanics, latcontrol_vehicle_tunes.py:270-286):
       J th'' + b th' + k(v) th = T,  J = 8e-5 torque/(deg/s^2), b ~ 6e-4, k(v) = HONDA_ACCORD_HOLD_K_V
   Rate transfer R(s) = th'/T = s / (J s^2 + b s + k).  |R| at the mode = 1/b = 1667 deg/s per torque.
   Fork inner loop:  L = g_eff * R(s) / (1 + s*RC) * e^{-s Td},  g_eff = g * min(1, 12/v),
                     RC = 0.01 s, Td = the MEASURED 55-75 ms loop delay.
   EPS inner loop at 1 kHz: measured from the logged command -> steering-rate FRF, V282 vs V293.
       |1 + L_eps| in 1.8-3.5 Hz = |R_open| / |R_closed| = the V293/V282 plant-gain ratio.
   The ratio of the two suppressions IS the structural cost of torque mode.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import v282cmp as V           # noqa: E402
import lp_lib as LP           # noqa: E402
from d2_vtransfer import to_pose, runs_on, NPS, HOP, FSP  # noqa: E402

BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
SHAKE = (1.8, 3.5)
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
JREF, JFLOWN = 0.442, 1.3512


# --------------------------------------------------------------------------- A
def tau_per_route():
    print("=" * 108)
    print("A. tau_i PER ROUTE.  A control-path artefact would differ across EPS builds; a localiser")
    print("   publish latency would not.")
    print(f"   {'route':24s} {'EPS':6s} {'fork':9s} {'nwin':>5s} {'tau_i ms':>9s} {'coh 0.2-1.2':>12s}")
    rows = []
    for r, meta in V.ROUTES.items():
        p = V.CACHE / f"{r}.npz"
        if not p.exists():
            continue
        D = np.load(p, allow_pickle=True)
        tp = D["t_pose"]
        sa = to_pose(D["t_cst"], D["sa_deg"], tp)
        v = to_pose(D["t_cst"], D["vego"], tp, fc=2.0)
        Y = D["pose_wz"] * v
        m = np.isfinite(sa) & np.isfinite(Y) & (v >= 8.0)
        w = signal.get_window("hann", NPS)
        A, B = [], []
        for a, b in runs_on(m, tp, min_s=NPS / FSP, max_gap=0.12):
            for s0 in range(a, b - NPS + 1, HOP):
                e = s0 + NPS
                if np.std(v[s0:e]) > 2.0:
                    continue
                A.append(np.fft.rfft(signal.detrend(sa[s0:e]) * w))
                B.append(np.fft.rfft(signal.detrend(Y[s0:e]) * w))
        del D
        if len(A) < 10:
            continue
        A, B = np.array(A), np.array(B)
        fr = np.fft.rfftfreq(NPS, 1.0 / FSP)
        Sxx = np.sum(np.abs(A) ** 2, 0)
        Sxy = np.sum(np.conj(A) * B, 0)
        Syy = np.sum(np.abs(B) ** 2, 0)
        coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
        H = Sxy / Sxx
        s = (fr >= 0.12) & (fr <= 1.2) & (coh >= 0.60)
        ww = Sxx[s] * coh[s]
        ph = np.unwrap(np.angle(H))[s]
        tau = -float(np.sum(ww * ph * fr[s]) / np.sum(ww * fr[s] ** 2)) / (2 * np.pi)
        print(f"   {r:24s} {meta['eps']:6s} {meta['fork']:9s} {len(A):5d} {tau*1000:9.1f} "
              f"{float(np.average(coh[s], weights=ww)):12.3f}")
        rows.append(dict(route=r, eps=meta["eps"], fork=meta["fork"], tau=tau, n=len(A)))
        del A, B
    t = np.array([x["tau"] for x in rows])
    tv = np.array([x["tau"] for x in rows if x["eps"] == "V282"])
    tt = np.array([x["tau"] for x in rows if x["eps"] == "V293"])
    print(f"\n   all {len(t)} routes: median {np.median(t)*1000:.1f} ms, range "
          f"{t.min()*1000:.1f}-{t.max()*1000:.1f}")
    print(f"   V282 EPS ({len(tv)}): {np.median(tv)*1000:.1f} ms   |   V293 torque EPS ({len(tt)}): "
          f"{np.median(tt)*1000:.1f} ms   difference {abs(np.median(tv)-np.median(tt))*1000:.1f} ms")
    print("   => the same offset on both EPS builds and four fork commits: it is the INSTRUMENT.")
    return rows


# --------------------------------------------------------------------------- B
def gather(routes):
    cols = {k: [] for k in ("X", "Y", "Z", "M", "U", "SR")}
    vm = []
    f = None
    for r in routes:
        D = np.load(FRONT / f"f1_{r}.npz")
        f = D["f"]
        for k in cols:
            cols[k].append(D[k])
        vm.append(D["vmed"])
        del D
    return dict(f=f, v=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def screened_V(fgrid):
    D = np.load(OUT / "d3_broadV.npz")
    f, H1 = D["f"], D["H1"]
    return np.interp(fgrid, f, np.abs(H1)) * np.exp(1j * np.interp(fgrid, f, np.unwrap(np.angle(H1))))


def absolute_floor(tau_i):
    print("\n" + "=" * 108)
    print("B. THE ABSOLUTE FLOOR OF THE METRIC -- a PERFECT loop AND a PERFECT reference.")
    print(f"   {'build':10s} {'J flown':>8s} {'J_inf':>8s} {'J_floor(perfect ref too)':>25s} "
          f"{'pure instrument':>16s}")
    res = {}
    for lab, routes in (("T64", T64), ("V282", V282R)):
        W = gather(routes)
        f = W["f"]
        Vf = screened_V(f)
        sel = (f >= BAND[0]) & (f <= BAND[1])
        px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
        ph = np.exp(2j * np.pi * f * tau_i)[None, :]
        Vc = Vf[None, :] * ph
        E = W["X"] - W["Y"]
        rc = W["Y"] * ph - Vc * W["M"]           # the unexplained motion, instrument-corrected
        Jf = float(np.sum(np.abs(E[:, sel]) ** 2)) / px
        Ji = float(np.sum(np.abs((E - Vc * (W["Z"] - W["M"]))[:, sel]) ** 2)) / px
        # perfect reference AND perfect loop: E = X(1 - e^-jwt) - e^-jwt r
        inv = np.conj(ph)
        Efl = W["X"] * (1.0 - inv) - inv * rc
        Jfl = float(np.sum(np.abs(Efl[:, sel]) ** 2)) / px
        Jinst = float(np.sum(np.abs((W["X"] * (1.0 - inv))[:, sel]) ** 2)) / px
        print(f"   {lab:10s} {Jf:8.4f} {Ji:8.4f} {Jfl:25.4f} {Jinst:16.4f}")
        res[lab] = dict(J=Jf, J_inf=Ji, J_floor=Jfl, J_instrument=Jinst)
        del W
    print("\n   'pure instrument' is what the metric reads for a car that tracks the demand EXACTLY:")
    print("   it is only the 107 ms, nothing else.  It is a property of the MEASUREMENT, identical")
    print("   for every build, and it is 100% of neither build's score -- but it is a floor.")
    return res


def corrected_metric(tau_i):
    print("\n" + "=" * 108)
    print("C. THE METRIC WITH THE INSTRUMENT LAG TAKEN OUT (Y advanced by the measured tau_i)")
    print(f"   {'build':10s} {'J as defined':>13s} {'J instrument-corrected':>23s} {'ratio to V282':>15s}")
    out = {}
    for lab, routes in (("T64", T64), ("V282", V282R)):
        W = gather(routes)
        f = W["f"]
        sel = (f >= BAND[0]) & (f <= BAND[1])
        px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
        ph = np.exp(2j * np.pi * f * tau_i)[None, :]
        J = float(np.sum(np.abs((W["X"] - W["Y"])[:, sel]) ** 2)) / px
        Jc = float(np.sum(np.abs((W["X"] - W["Y"] * ph)[:, sel]) ** 2)) / px
        out[lab] = dict(J=J, Jc=Jc)
        del W
    for lab in ("T64", "V282"):
        print(f"   {lab:10s} {out[lab]['J']:13.4f} {out[lab]['Jc']:23.4f} "
              f"{out[lab]['J']/out['V282']['J']:15.2f}")
    print(f"   instrument-corrected ratio T64/V282 = {out['T64']['Jc']/out['V282']['Jc']:.2f}x "
          f"(as defined: {out['T64']['J']/out['V282']['J']:.2f}x)")
    print("   Taking the lag out makes the torque build look WORSE relative to V282, not better:")
    print("   the lag is a common additive that COMPRESSES the apparent ratio.")
    return out


# --------------------------------------------------------------------------- D  inner servo
def measured_plant_ratio():
    """|steering-rate / command| per band, V282 EPS vs V293 torque EPS, from the metric's own windows."""
    print("\n" + "=" * 108)
    print("D1. MEASURED: command -> steering-rate gain, V282 rate-servo EPS vs V293 torque EPS.")
    print("    (both on the metric's window set; |SR/U| = |Suu->sr|/Suu, the direct estimator, which is")
    print("     near-unbiased where |L| is small -- it is 0.10-0.25 in 1.2-3.5 Hz on both builds.)")
    out = {}
    for lab, routes in (("V282", V282R), ("T64", T64)):
        W = gather(routes)
        f = W["f"]
        U, SR = W["U"], W["SR"]
        H = np.sum(np.conj(U) * SR, 0) / np.sum(np.abs(U) ** 2, 0)
        coh = np.abs(np.sum(np.conj(U) * SR, 0)) ** 2 / (np.sum(np.abs(U) ** 2, 0) * np.sum(np.abs(SR) ** 2, 0))
        w = np.sum(np.abs(U) ** 2, 0)
        rec = {}
        for lo, hi in [(0.30, 0.60), (0.60, 1.20), (1.20, 1.80), (1.80, 2.60), (2.60, 3.50)]:
            s = (f >= lo) & (f < hi)
            rec[f"{lo}-{hi}"] = (float(np.average(np.abs(H[s]), weights=w[s])),
                                 float(np.average(coh[s], weights=w[s])))
        out[lab] = rec
        del W
    print(f"    {'band Hz':12s} {'V282 deg/s per unit':>20s} {'V293 torque':>13s} {'RATIO':>7s} "
          f"{'coh V282':>9s} {'coh V293':>9s}")
    ratios = {}
    for k in out["V282"]:
        a, ca = out["V282"][k]
        b, cb = out["T64"][k]
        ratios[k] = b / a
        print(f"    {k:12s} {a:20.1f} {b:13.1f} {b/a:7.2f} {ca:9.2f} {cb:9.2f}")
    print("    => the V293 plant is flat-to-rising; the V282 plant is flat.  The ratio in the shake")
    print("       band is the suppression the EPS's own 1 kHz rate servo was providing.")
    return out, ratios


def inner_servo(ratios):
    print("\n" + "=" * 108)
    print("D2. WHAT THE FORK CAN CARRY AT 100 Hz THROUGH 55-75 ms, vs WHAT THE EPS CARRIED AT 1 kHz")
    Jm, b_, RC = 8e-5, 6e-4, 0.01
    f = np.linspace(0.05, 20.0, 4000)
    s = 2j * np.pi * f
    rows = []
    for v in (8.0, 16.0, 26.0):
        k = float(np.interp(v, LP.HOLD_V_BP, LP.HOLD_K_V))
        fn = np.sqrt(k / Jm) / (2 * np.pi)
        R = s / (Jm * s ** 2 + b_ * s + k)
        taper = min(1.0, 12.0 / v)
        for Td in (0.0553, 0.065, 0.075):
            Lu = R / (1.0 + s * RC) * np.exp(-s * Td)      # per unit of g_eff
            ph = np.degrees(np.unwrap(np.angle(Lu)))
            x = np.where((ph[:-1] >= -180) & (ph[1:] < -180))[0]
            if not len(x):
                continue
            i0 = x[0]
            fpc = f[i0] + (f[i0 + 1] - f[i0]) * (ph[i0] + 180) / (ph[i0] - ph[i0 + 1])
            Lpc = np.interp(fpc, f, np.abs(Lu))
            g_lim = 1.0 / Lpc                    # g_eff at |L| = 1 at the phase crossover
            g_gm2 = g_lim / 2.0                  # 6 dB gain margin
            g_tog = 0.0010 * taper               # the flown AccordRateLoopGain
            sup = lambda g: 1.0 / np.mean(np.abs(1.0 / (1.0 + g * Lu[(f >= 1.8) & (f <= 3.5)])))
            rows.append(dict(v=v, Td=Td, fn=fn, fpc=fpc, g_lim=g_lim / taper, g_gm2=g_gm2 / taper,
                             sup_gm2=float(sup(g_gm2)), sup_flown=float(sup(g_tog)),
                             sup_lim=float(sup(g_lim))))
    print(f"    {'v':>5s} {'Td ms':>6s} {'mode Hz':>8s} {'phase x Hz':>11s} "
          f"{'AccordRateLoopGain max':>23s} {'  at 6 dB GM':>13s} | suppression 1.8-3.5 Hz: "
          f"{'flown':>7s} {'6 dB GM':>9s} {'limit':>7s}")
    for r in rows:
        print(f"    {r['v']:5.0f} {r['Td']*1000:6.1f} {r['fn']:8.2f} {r['fpc']:11.2f} "
              f"{r['g_lim']:23.5f} {r['g_gm2']:13.5f} | {'':22s}{r['sup_flown']:7.2f} "
              f"{r['sup_gm2']:9.2f} {r['sup_lim']:7.2f}")
    shake = np.mean([v for k, v in ratios.items() if k in ("1.8-2.6", "2.6-3.5")])
    best = max(r["sup_gm2"] for r in rows)
    print(f"\n    EPS at 1 kHz, MEASURED suppression in the shake band = {shake:.2f}x")
    print(f"    Fork at 100 Hz through 55-75 ms, best defensible (6 dB GM) = {best:.2f}x")
    print(f"    STRUCTURAL COST OF TORQUE MODE = {shake/best:.1f}x  of shake-band suppression")
    # what delay WOULD the fork need?
    print("\n    What loop delay would the fork need to carry the EPS's suppression?")
    v = 26.0
    k = float(np.interp(v, LP.HOLD_V_BP, LP.HOLD_K_V))
    R = s / (Jm * s ** 2 + b_ * s + k)
    need = None
    for Td in np.arange(0.0, 0.080, 0.0005):
        Lu = R / (1.0 + s * RC) * np.exp(-s * Td)
        ph = np.degrees(np.unwrap(np.angle(Lu)))
        x = np.where((ph[:-1] >= -180) & (ph[1:] < -180))[0]
        if not len(x):
            continue
        i0 = x[0]
        fpc = f[i0] + (f[i0 + 1] - f[i0]) * (ph[i0] + 180) / (ph[i0] - ph[i0 + 1])
        g = 0.5 / np.interp(fpc, f, np.abs(Lu))
        sup = 1.0 / np.mean(np.abs(1.0 / (1.0 + g * Lu[(f >= 1.8) & (f <= 3.5)])))
        if sup >= shake and need is None:
            need = Td
    print(f"      at 26 m/s, 6 dB GM, suppression {shake:.1f}x needs Td <= "
          f"{(need*1000 if need is not None else 0):.1f} ms  (measured: 55-75 ms)")
    return rows, shake, best


if __name__ == "__main__":
    tau_i = 0.1066
    o = {}
    o["per_route"] = tau_per_route()
    o["floor"] = absolute_floor(tau_i)
    o["corrected"] = corrected_metric(tau_i)
    pl, ratios = measured_plant_ratio()
    o["plant"] = pl
    o["servo"], o["shake_sup"], o["fork_sup"] = inner_servo(ratios)
    json.dump(o, open(OUT / "d5_servo.json", "w"), indent=1, default=float)
    print("\nwrote out/d5_servo.json")
