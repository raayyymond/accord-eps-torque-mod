# -*- coding: utf-8 -*-
"""i11 -- CHECK THE CONTROLLER MODEL AGAINST THE LOG: measure K(f) = d(command)/d(wheel angle).

This is the one transfer these logs determine EXACTLY.  The controller is noise-free: the command is
a deterministic function of the measured angle and the reference,
        U(f) = K(f) * SA(f) + Kr(f) * Z(f)
so a per-bin TWO-INPUT least squares of U on (SA, Z) recovers K with no closed-loop bias and no
instrument needed.  (A one-input regression of U on SA alone is contaminated by the reference; both
are printed so the difference is visible.)

Why it is the crux: K is where the SteerFriction relay lives.  If the relay ran on route 73 at
friction 0.2120, LAF 14, kp 0.85 -- 11.6x the P gain -- then r73's measured |K| must be about an
order of magnitude above the P-only prediction.  If it is not, the relay reading is wrong and every
conclusion built on it falls.  VERIFY THE CRUX YOURSELF.

ANALYSIS ONLY.  python i11_kcheck.py <route> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(HERE))
import v282cmp as V   # noqa: E402
import i9_loop as M   # noqa: E402

FS = 100.0
NPS, HOP = 1024, 512
FREQS = [0.20, 0.39, 0.59, 0.78, 0.98, 1.27, 1.56, 1.76, 1.95, 2.15, 2.34, 2.64, 2.93, 3.52, 4.30]
BYROUTE = {c["route"]: t for t, c in M.CTRL.items()}


def kmeas(route, vlo=15.0, vhi=99.0):
    S = V.load(route)
    m = (S["active"] & ~S["pressed"] & ~S["sat"] & (S["v"] >= vlo) & (S["v"] < vhi)
         & np.isfinite(S["sa"]) & np.isfinite(S["out"]) & np.isfinite(S["setpoint"]))
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, 1.0 / FS)
    U, SA, Z = [], [], []
    vm = []
    src = dict(U=np.nan_to_num(S["out"]), SA=np.nan_to_num(S["sa"] - S["aoff"]),
               Z=np.nan_to_num(S["setpoint"]))
    for a, b in V.runs(m, S["t"], min_s=NPS / FS):
        for s in range(a, b - NPS + 1, HOP):
            e = s + NPS
            if not np.isfinite(S["v"][s:e]).all():
                continue
            U.append(np.fft.rfft(signal.detrend(src["U"][s:e]) * w))
            SA.append(np.fft.rfft(signal.detrend(src["SA"][s:e]) * w))
            Z.append(np.fft.rfft(signal.detrend(src["Z"][s:e]) * w))
            vm.append(float(np.median(S["v"][s:e])))
    v = float(np.median(vm)) if vm else float("nan")
    del S, src
    if len(U) < 6:
        return None
    U, SA, Z = np.array(U), np.array(SA), np.array(Z)
    xs = lambda A, B: np.mean(np.conj(A) * B, axis=0)
    Saa, Szz, Saz = xs(SA, SA).real, xs(Z, Z).real, xs(SA, Z)
    Sau, Szu = xs(SA, U), xs(Z, U)
    det = Saa * Szz - np.abs(Saz) ** 2
    K2 = (Szz * Sau - np.conj(Saz) * Szu) / np.maximum(det, 1e-300)   # two-input solution
    K1 = Sau / np.maximum(Saa, 1e-300)                                # one-input (contaminated)
    Suu = xs(U, U).real
    coh = np.abs(Sau) ** 2 / np.maximum(Saa * Suu, 1e-300)
    # residual of the 2-input fit -> how completely (SA, Z) explain U
    Kr = (Saa * Szu - Saz * Sau) / np.maximum(det, 1e-300)
    res = Suu - 2 * np.real(np.conj(K2) * Sau + np.conj(Kr) * Szu) + \
        (np.abs(K2) ** 2 * Saa + np.abs(Kr) ** 2 * Szz + 2 * np.real(np.conj(K2) * Kr * Saz))
    r2 = 1.0 - res / np.maximum(Suu, 1e-300)
    return dict(f=f, K2=K2, K1=K1, coh=coh, r2=r2, v=v, n=len(U), Saa=Saa, Suu=Suu)


if __name__ == "__main__":
    out = {}
    for route in sys.argv[1:]:
        R = kmeas(route)
        if R is None:
            print(f"{route}: too few windows")
            continue
        tag = BYROUTE.get(route, route)
        c = M.CTRL[tag]
        # analytic K needs g; take it from the i5 measurement
        g = -json.load(open(HERE / "out_i5_plant.json"))[route]["15+"]["g"]
        nd = json.load(open(HERE / "out_i8_relay.json"))[route]["15+"]
        ndf = nd["df_band"] if np.isfinite(nd["df_band"]) else nd["frac_linear"]
        fa = np.array(FREQS)
        Kan = M.K_of(fa, c, R["v"], g, ndf=ndf)
        Kpo = M.K_of(fa, c, R["v"], g, use_relay=False, use_rate=False, use_notch=False)
        print(f"\n=== {tag} ({route})  v {R['v']:.1f}  {R['n']} windows  g {g:.5f} "
              f"| relay_live {c['relay_live']} fric {c['fric']:.4f} DF {ndf:.3f} "
              f"notch {c['notch']} grate {c['grate']}")
        print(f"   small-signal relay/P = {c['fric']*c['laf']/(0.30*c['kp']):.3f}, "
              f"derated = {c['fric']*c['laf']/(0.30*c['kp'])*ndf:.3f}")
        print(f"   {'f':>5s} {'|K|meas':>9s} {'ph meas':>8s} {'|K|model':>9s} {'ph model':>9s} "
              f"{'|K|P-only':>10s} {'meas/Ponly':>11s} {'model/Ponly':>12s} {'coh':>5s} {'R2':>5s}")
        rows = []
        for i, q in enumerate(fa):
            j = int(np.argmin(np.abs(R["f"] - q)))
            km, ka, kp_ = R["K2"][j], Kan[i], Kpo[i]
            rows.append(dict(f=float(R["f"][j]), Kmeas_abs=float(abs(km)),
                             Kmeas_ph=float(np.degrees(np.angle(km))),
                             Kmod_abs=float(abs(ka)), Kmod_ph=float(np.degrees(np.angle(ka))),
                             Kponly=float(abs(kp_)), coh=float(R["coh"][j]), r2=float(R["r2"][j])))
            print(f"   {R['f'][j]:5.2f} {abs(km):9.5f} {np.degrees(np.angle(km)):8.1f} "
                  f"{abs(ka):9.5f} {np.degrees(np.angle(ka)):9.1f} {abs(kp_):10.5f} "
                  f"{abs(km)/abs(kp_):11.3f} {abs(ka)/abs(kp_):12.3f} "
                  f"{R['coh'][j]:5.2f} {R['r2'][j]:5.2f}")
        out[tag] = dict(route=route, v=R["v"], n=R["n"], g=g, ndf=ndf, rows=rows)
        del R
    json.dump(out, open(HERE / "out_i11_kcheck.json", "w"), indent=1)
