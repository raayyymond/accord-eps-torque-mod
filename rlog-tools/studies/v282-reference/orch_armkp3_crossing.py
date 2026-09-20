# -*- coding: utf-8 -*-
"""ORCHESTRATOR HAND-DERIVATION: where does ARM-KP3 put the -180 deg crossing?

Three independent re-derivations put it in three different places (1.5-1.8 Hz / 3.72-4.05 Hz /
1.62-2.10 Hz), so the judge marked it BELIEF/contested and said it must not be quoted again until one
hand-checked derivation exists.  This is that derivation.  It is deliberately simple and every constant
is read from the fork source.

L(s) = [ (kp + lsf)*N(s)  +  ki*(1 + lsf/kp)*N(s)/s ] * alpha/(J s^2 + b s + k(v)) * exp(-s D)

  N(s)  = (s^2 + w0^2) / (s^2 + w0 s/Q + w0^2)      error notch, w0 = 2*pi*get_honda_accord_mode_hz(v)
  lsf   = (interp(v,[0,10,20,30],[12,10.5,8,5]) / max(v, MIN_SPEED))^2     torque.py:339
  P gain = kp + lsf, I gain = ki*(1 + lsf/kp)       from error_with_lsf = e*(1 + lsf/kp), torque.py:342
  k(v)  = HONDA_ACCORD_HOLD_K_V, J = HONDA_ACCORD_EPS_INERTIA = 8e-5      tunes, verified in source

alpha is a pure positive scalar: it scales |L| but CANNOT move a phase crossing.  So the crossing
FREQUENCY below is independent of the plant-gain anchor -- which is the part the study disputes.
b is the one genuinely open constant (the study's REPORT leaves it uncertain over ~70x), so it is swept.

Run:  python orch_armkp3_crossing.py
"""
import numpy as np

HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
J = 8e-5
LOW_X, LOW_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 0.1


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / J) / (2 * np.pi)


def lsf_of(v):
    return (np.interp(v, LOW_X, LOW_Y) / max(v, MIN_SPEED)) ** 2


def argL(f, v, kp, ki, Q, D, b):
    """Phase of L in degrees.  alpha omitted: a positive scalar cannot move a phase crossing."""
    s = 2j * np.pi * f
    w0 = 2 * np.pi * mode_hz(v)
    N = (s * s + w0 ** 2) / (s * s + s * w0 / max(Q, 1e-9), ) if False else \
        (s * s + w0 ** 2) / (s * s + s * w0 / max(Q, 1e-9) + w0 ** 2)
    lsf = lsf_of(v)
    C = (kp + lsf) * N + ki * (1.0 + lsf / kp) * N / s
    P = 1.0 / (J * s * s + b * s + np.interp(v, HOLD_V_BP, HOLD_K_V))
    return np.degrees(np.angle(C * P * np.exp(-s * D)))


def crossings(v, kp, ki, Q, D, b, fmax=8.0):
    f = np.arange(0.05, fmax, 0.0005)
    ph = np.unwrap(np.radians([argL(x, v, kp, ki, Q, D, b) for x in f]))
    ph = np.degrees(ph)
    out = []
    for i in range(1, len(f)):
        for tgt in (-180.0, -540.0):            # -180 and its next wrap
            if (ph[i - 1] - tgt) * (ph[i] - tgt) < 0:
                out.append(f[i])
    return sorted(set(np.round(out, 3)))


CFG = {"as flown  (kp 1.0, ki 0.30, Q 1.00)": (1.0, 0.30, 1.00),
       "ARM-KP3   (kp 3.0, ki 0.60, Q 0.30)": (3.0, 0.60, 0.30),
       "ARM-KP2   (kp 3.0, ki 0.30, Q 0.60)": (3.0, 0.30, 0.60)}

print("-180 deg CROSSING FREQUENCY (Hz).  alpha omitted -- it cannot move a phase crossing.\n")
for v in (15.0, 23.0, 28.0):
    print(f"=== v = {v:.0f} m/s   plant mode {mode_hz(v):.3f} Hz   lsf {lsf_of(v):.4f} ===")
    for b in (0.0006, 0.0018, 0.0060):
        zeta = b / (2 * np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) * J))
        print(f"  b = {b:.4f}  (zeta = {zeta:.3f})")
        for name, (kp, ki, Q) in CFG.items():
            row = []
            for D in (0.055, 0.065, 0.075):
                c = crossings(v, kp, ki, Q, D, b)
                row.append("none" if not c else "/".join(f"{x:.2f}" for x in c[:3]))
            print(f"     {name}   D=55ms {row[0]:<18s} 65ms {row[1]:<18s} 75ms {row[2]}")
    print()

print("""READ THIS OFF THE TABLE, NOT FROM A REMEMBERED NUMBER:
  * The crossing frequency is set by the notch's own phase plus the plant mode plus the delay.  alpha
    (the plant-gain anchor, the disputed quantity) does NOT enter it at all.
  * b IS load-bearing for the plant mode's sharpness and therefore for where the phase sweeps through
    -180.  The study leaves b open over ~70x; three settings are shown so the reader can see the spread
    rather than be handed one number.
  * WHATEVER this table says, it is a WHERE, not a HOW MUCH.  The gate that just failed showed this
    model mis-ranks its own clean anchors by up to an order of magnitude (it reads r73 riskiest of
    everything, and r73 flew without r71's object).  It retrodicts r71's 2.34 Hz to within ~5-15 %,
    so it is usable as a frequency predictor and is NOT calibrated as a risk or severity predictor.
    Do not quote a margin from it.""")
