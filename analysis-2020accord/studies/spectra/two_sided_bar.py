#!/usr/bin/env python3
"""studies/spectra/two_sided_bar.py -- is the ~8 Hz line the STEERING WHEEL RINGING AGAINST THE TORSION BAR?

Operator's model, 2026-08-23: "our issue is actual steering wheel inertia on the other side of the
torque sensor when LKAS drives the EPS motor on the other side."

Sized from first principles it lands where the line is: J_wheel 0.03-0.05 kg m^2 on a 1.5-2.5
N m/deg bar gives 7.4-8.5 Hz, vs a measured line window of 7.4-8.6 Hz.

THE TEST.  A torsion bar is a spring between two inertias.  Its torque is the integral of the
RELATIVE rate of its two ends:
        T_bar(t) = k * INTEGRAL( omega_column - omega_motor )   =>   d(T_bar)/dt  =  k * (w_col - w_mot)
So if the bus carries one rate from each side of the bar, d(tq)/dt must be coherent with the
DIFFERENCE of the two rate channels and much less coherent with either one alone.  That single test
simultaneously (a) identifies which channel is which side and (b) confirms or kills the two-mass
model -- and it cannot be faked by shared sensor quantisation, which is what defeats a naive
correlation against d(ang)/dt.

CHANNELS (decode from decode/extract_r29_cache.py, unchanged):
    ang     0x14A b0:2  STEER_ANGLE          deg     (0.1 deg LSB)
    rate_c  0x14A b2:4  STEER_ANGLE_RATE     deg/s   (1.0 deg/s LSB)
    rate_f  0x18F b2:4  STEER_ANGLE_RATE     deg/s   (0.1 deg/s LSB)
    tq      0x18F b0:2  STEER_TORQUE_SENSOR  counts  (the torsion bar itself)
 !! ang and wang are BYTE-IDENTICAL on route a6 (corr 1.000000, difference exactly 0) -- Honda
    duplicates one sensor into both fields.  There is no two-sided ANGLE pair.  Rates only.

OPERATOR'S GATING, applied verbatim -- "this only happens on low-medium speed where massive,
near-max or max LKAS demand is present on 4x or 6x drives + the steering column is moving + I am
not driving the steering wheel in one direction or another".
"""
import sys
import numpy as np
from scipy import signal as sg

FS = 100.0
ROUTES = [("r9e", "V103"), ("ra4", "V104"), ("ra5", "V105"), ("ra6", "V106")]
WIN = 256                      # 2.56 s, 0.391 Hz bins
HOP = 128


def load(tag):
    d = np.load(f"_cache_{tag}/{tag}.npz", allow_pickle=True)
    g = lambda k: np.nan_to_num(np.asarray(d[k], float))
    return dict(t=g("t"), ang=g("ang"), rc=g("rate_c"), rf=g("rate_f"), tq=g("tq"),
                v=g("cs_v") * 3.6, sca=g("sca") > 0.5, e4=np.abs(g("e4tq")), seg=g("seg"))


def windows(D, vlo, vhi, dem_pct, rate_min, bias_max):
    """Operator's gate. Returns list of index slices."""
    n = len(D["t"])
    dem_thr = np.percentile(D["e4"][D["sca"]], dem_pct) if D["sca"].any() else np.inf
    out, stats = [], dict(total=0, gate_speed=0, gate_dem=0, gate_move=0, gate_bias=0, kept=0)
    for i in range(0, n - WIN, HOP):
        s = slice(i, i + WIN)
        stats["total"] += 1
        if not D["sca"][s].all():
            continue
        if not (vlo <= np.median(D["v"][s]) < vhi):
            continue
        stats["gate_speed"] += 1
        if np.median(D["e4"][s]) < dem_thr:                      # near-max LKAS demand
            continue
        stats["gate_dem"] += 1
        if np.median(np.abs(D["rf"][s])) < rate_min:             # column is MOVING
            continue
        stats["gate_move"] += 1
        tqs = D["tq"][s]                                          # not steering one way
        if np.abs(np.mean(tqs)) > bias_max * (np.std(tqs) + 1e-9):
            continue
        stats["gate_bias"] += 1
        stats["kept"] += 1
        out.append(s)
    return out, stats, dem_thr


def csd_stack(D, sl, a, b):
    w = np.hanning(WIN)
    Sxy = np.zeros(WIN // 2 + 1, complex)
    Sxx = np.zeros(WIN // 2 + 1)
    Syy = np.zeros(WIN // 2 + 1)
    for s in sl:
        X = np.fft.rfft(sg.detrend(a[s]) * w)
        Y = np.fft.rfft(sg.detrend(b[s]) * w)
        Sxy += X * np.conj(Y)
        Sxx += np.abs(X) ** 2
        Syy += np.abs(Y) ** 2
    return Sxy, Sxx, Syy, np.fft.rfftfreq(WIN, 1 / FS)


def main(vlo=5.0, vhi=60.0, dem_pct=75.0, rate_min=5.0, bias_max=1.0):
    print(f"GATE: {vlo:.0f}-{vhi:.0f} km/h | LKAS demand >= p{dem_pct:.0f} of engaged | "
          f"|column rate| >= {rate_min:.0f} deg/s | |mean tq| <= {bias_max:.1f}*std(tq) | engaged whole window\n")
    for tag, build in ROUTES:
        try:
            D = load(tag)
        except Exception as e:
            print(f"{tag}: {e}")
            continue
        sl, st, thr = windows(D, vlo, vhi, dem_pct, rate_min, bias_max)
        print(f"=== {tag} = {build} ===")
        print(f"  windows {st['total']} -> speed {st['gate_speed']} -> demand {st['gate_dem']} "
              f"(thr {thr:.0f}) -> moving {st['gate_move']} -> unbiased {st['kept']}")
        if len(sl) < 8:
            print("  TOO FEW WINDOWS -- not scored\n")
            continue
        dtq = np.gradient(D["tq"], 1 / FS)
        diff = D["rf"] - D["rc"]
        cands = [("rate_f - rate_c", diff), ("rate_c - rate_f", -diff),
                 ("rate_f alone", D["rf"]), ("rate_c alone", D["rc"])]
        print(f"  {'d(tq)/dt vs':<16} " + "".join(f"{f'coh2@{f}Hz':>12}" for f in (4, 6, 8, 10, 14)))
        for nm, x in cands:
            Sxy, Sxx, Syy, fr = csd_stack(D, sl, dtq, x)
            coh = np.abs(Sxy) ** 2 / (Sxx * Syy + 1e-30)
            row = ""
            for f in (4, 6, 8, 10, 14):
                k = np.argmin(np.abs(fr - f))
                row += f"{coh[k]:12.3f}"
            print(f"  {nm:<16} {row}")
        # phase between the two rate channels
        Sxy, Sxx, Syy, fr = csd_stack(D, sl, D["rf"], D["rc"])
        coh = np.abs(Sxy) ** 2 / (Sxx * Syy + 1e-30)
        ph = np.degrees(np.angle(Sxy))
        print(f"  {'rf vs rc phase':<16} " + "".join(
            f"{ph[np.argmin(np.abs(fr-f))]:+8.0f}deg" for f in (4, 6, 8, 10, 14)))
        print(f"  {'  their coh2':<16} " + "".join(
            f"{coh[np.argmin(np.abs(fr-f))]:12.3f}" for f in (4, 6, 8, 10, 14)))
        print()


if __name__ == "__main__":
    a = [float(x) for x in sys.argv[1:]]
    main(*a) if a else main()
