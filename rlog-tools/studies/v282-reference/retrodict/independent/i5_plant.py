# -*- coding: utf-8 -*-
"""i5 -- measure each route's plant ANCHOR: the complex transfer command -> WHEEL ANGLE at low frequency.

WHY AN ANCHOR AND NOT A FULL IDENTIFICATION.  On these builds the controller is noise-free -- the
command u is an exact deterministic function of the measured signals -- so wherever the exogenous
reference has no power, every closed-loop estimator of the plant degenerates towards 1/C (the
controller's inverse), not P.  The reference (the shaped setpoint Z) has power below ~0.6 Hz and
essentially none at 2-3 Hz, so the plant is IDENTIFIABLE AT LOW FREQUENCY ONLY.  Above that it has
to come from a model.  That is the honest split, and it is why this stream anchors a physical model
at 0.20 Hz instead of reading a "measured" plant in the shake band.

At 0.20 Hz the physical model  J*th'' + b*th' + k(v)*th = torque  is dominated by k: |J w^2| = 1.3e-4
and |b w| = 7.5e-4 against k ~ 0.005-0.016, i.e. <= 3 %.  So the anchor measures 1/k(v) DIRECTLY, and
comparing it with the fork's HOLD_K_V table is a real test of the table (the fork's own rev-6 note
says the table reads 1.15-1.45x LOW at speed).

Estimator: instrumental variable with the shaped setpoint Z as the instrument,
    P_th(f) = S_{Z,SA} / S_{Z,U}          [deg of wheel angle per unit command]
U is torqueState.output = pid_log.output = -output_torque, which is the +LEFT-FRAME torque (see
the fork: plant_ff_torque = -get_honda_accord_rate_plant_ff(...)), so P_th is already in the plant's
own frame and must come out POSITIVE real at DC.  Coherences are printed as the gate.

ANALYSIS ONLY.  python i5_plant.py <route> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
NPS, HOP = 2048, 1024      # 20.48 s -> df 0.0488 Hz, so 0.20 Hz is bin 4
BINS = [("5-15", 5.0, 15.0), ("15-22", 15.0, 22.0), ("22+", 22.0, 99.0), ("15+", 15.0, 99.0),
        ("all", 3.0, 99.0)]
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]


def ffts(route):
    S = V.load(route)
    m = (S["active"] & ~S["pressed"] & ~S["sat"] & np.isfinite(S["setpoint"])
         & np.isfinite(S["sa"]) & np.isfinite(S["out"]) & np.isfinite(S["la_act"]))
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, 1.0 / FS)
    cols = {k: [] for k in ("Z", "SA", "U", "M")}
    vmed, gloc = [], []
    src = dict(Z=np.nan_to_num(S["setpoint"]), SA=np.nan_to_num(S["sa"] - S["aoff"]),
               U=np.nan_to_num(S["out"]), M=np.nan_to_num(S["la_act"]))
    for a, b in V.runs(m, S["t"], min_s=NPS / FS):
        for s in range(a, b - NPS + 1, HOP):
            e = s + NPS
            vv = S["v"][s:e]
            if not np.isfinite(vv).all():
                continue
            for k, arr in src.items():
                cols[k].append(np.fft.rfft(signal.detrend(arr[s:e]) * w))
            vmed.append(float(np.median(vv)))
            x = signal.detrend(src["SA"][s:e])
            y = signal.detrend(src["M"][s:e])
            gloc.append(float(np.dot(x, y) / max(np.dot(x, x), 1e-12)))
    del S, src
    if not vmed:
        return None
    return dict(f=f, vmed=np.array(vmed), gloc=np.array(gloc),
                **{k: np.array(v) for k, v in cols.items()})


def anchor(F, sel, f_anchor=0.20):
    f = F["f"]
    j = int(np.argmin(np.abs(f - f_anchor)))
    Z, SA, U, M = F["Z"][sel], F["SA"][sel], F["U"][sel], F["M"][sel]
    xs = lambda A, B: np.mean(np.conj(A) * B, axis=0)
    Szz = xs(Z, Z).real
    Pth = xs(Z, SA) / xs(Z, U)
    Pm = xs(Z, M) / xs(Z, U)
    coh = lambda A, B: np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)
    return dict(j=j, f=float(f[j]), Pth=complex(Pth[j]), Pm=complex(Pm[j]),
                coh_zu=float(coh(Z, U)[j]), coh_zsa=float(coh(Z, SA)[j]),
                coh_zm=float(coh(Z, M)[j]), Szz=float(Szz[j]), n=int(sel.sum()))


if __name__ == "__main__":
    out = {}
    for route in sys.argv[1:]:
        F = ffts(route)
        if F is None:
            print(f"{route}: no windows")
            continue
        print(f"\n=== {route}  {F['Z'].shape[0]} windows of {NPS/FS:.1f} s ===")
        print(f"{'bin':7s} {'n':>4s} {'v':>5s} {'g(loc)':>8s} {'|P_th| 0.2':>11s} {'ph':>7s} "
              f"{'1/k_table':>10s} {'k_meas/k_tab':>13s} {'coh ZU':>7s} {'coh ZSA':>8s}")
        out[route] = {}
        for tag, lo, hi in BINS:
            sel = (F["vmed"] >= lo) & (F["vmed"] < hi)
            if sel.sum() < 4:
                continue
            A = anchor(F, sel)
            v = float(np.median(F["vmed"][sel]))
            g = float(np.median(F["gloc"][sel]))
            ktab = float(np.interp(v, HOLD_V_BP, HOLD_K_V))
            kmeas = 1.0 / abs(A["Pth"])
            A.update(v=v, g=g, k_table=ktab, k_meas=kmeas, tag=tag)
            out[route][tag] = {k: (dict(re=x.real, im=x.imag) if isinstance(x, complex) else x)
                               for k, x in A.items()}
            print(f"{tag:7s} {sel.sum():4d} {v:5.1f} {g:8.5f} {abs(A['Pth']):11.2f} "
                  f"{np.degrees(np.angle(A['Pth'])):7.1f} {1.0/ktab:10.1f} "
                  f"{kmeas/ktab:13.3f} {A['coh_zu']:7.2f} {A['coh_zsa']:8.2f}")
        del F
    json.dump(out, open(HERE / "out_i5_plant.json", "w"), indent=1)
    print("\nwrote out_i5_plant.json")
