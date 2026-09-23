"""
REDO-PHYSICS claim 5: the fork's outer loop (StarPilot torque controller, V294 toggle config) on the V293 plant and on
the V294 plant (V293 + the 1 kHz acceleration trim). Linear, small-signal.

Fork (source-read at Dom 54ff1ea39, latcontrol_torque.py generic path, AccordRatePlantFF off):
  measurement = v^2 * curvature(theta)  (VehicleModel from the STEERING ANGLE, static; no yaw dynamics in the loop)
  error_with_lsf = error * (1 + lsf/kp),  lsf = (interp(v,[0,10,20,30],[12,10.5,8,5]) / v)^2
  P + I (100 Hz):  kp * e_lsf + ki * integral(e_lsf)   kp = SteerKP 0.9 (flat, controlsd overwrite), ki 0.3 (AccordTorqueKi, KiHigh 0)
  friction relay:  friction*LAF/thr * clip(e_lsf + 0.22*jerk)  -> linear slope 0.011/0.30 u per m/s^2 inside +-0.30 (jerk term exogenous)
  torque = lat_accel / LAF, LAF = SteerLatAccel 14.0.  The jerk LPF and the delay compensation are REFERENCE-side (no loop gain).
Round trip (BELIEF, fork's own budget): 60 ms = CAN->carState 3 + controlsState->0xE4 13 + 0xE4->torque 30-45 (incl. the
5 Hz output lag's ~32 ms group delay, modelled explicitly here) + 100 Hz ZOH 5.  => pure delay tau + explicit output lag.
Plant (BELIEF): J s^2 + b s + k(v) (+ trim: K_alpha s^2 /((1+s/wp)(1+s/wo)) e^{-s Td}).
VehicleModel: Accord 2018 specs (mass 3279 lb + 136 kg cargo, L 2.83, aF 0.39 L, tire factor 0.8467, sR 16.33).
"""
import math
import numpy as np

J0 = 8e-5
K_ALPHA_U = 7.989e-5
WP = -math.log(1011 / 1024) / 1e-3
WO = -math.log(992 / 1024) / 1e-3
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
G_BP, G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]

# VehicleModel
m = 3279 * 0.453592 + 136.0
L = 2.83; aF = 0.39 * L; aR = L - aF
cF = 192150 * 0.8467 * m / (1326. + 136.) * (aR / L) / ((2.70 - 1.08) / 2.70)
cR = 202500 * 0.8467 * m / (1326. + 136.) * (aF / L) / (1.08 / 2.70)
sF = m * (cF * aF - cR * aR) / (L ** 2 * cF * cR)
SR = 16.33


def G_la(v):   # m/s^2 of measured lateral accel per steering-wheel degree
    return v ** 2 * math.radians(1.0) / SR / (1 - sF * v ** 2) / L


def lsf(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 0.3)) ** 2


def L_outer(f, v, trim, b, k, kp=0.9, ki=0.3, laf=14.0, fric=0.011, thr=0.30, tau=0.025, Td=0.003, J=J0, trim_gain=1.0):
    s = 2j * np.pi * f
    ls = lsf(v)
    C = ((kp + ls) + ki * (1 + ls / kp) / s) / laf + (fric / thr) * (1 + ls / kp)
    Hout = 1 / (1 + s / WO) * np.exp(-s * 0.0005)          # the 5 Hz output lag (+ its half-sample)
    zoh = np.exp(-s * 0.005)                                # 100 Hz fork output ZOH
    plant_den = J * s ** 2 + b * s + k
    if trim:
        plant_den = plant_den + trim_gain * K_ALPHA_U * s ** 2 / ((1 + s / WP) * (1 + s / WO)) * np.exp(-s * Td)
    return C * G_la(v) * Hout * zoh * np.exp(-s * tau) / plant_den


def margins(v, trim, b, k, **kw):
    f = np.logspace(-2.5, 1.5, 60000)
    Lf = L_outer(f, v, trim, b, k, **kw)
    mag, ph = abs(Lf), np.unwrap(np.angle(Lf))
    gc = np.where(np.diff(np.sign(mag - 1)) != 0)[0]
    pms = [(f[i], math.degrees(ph[i]) % 360 - 180 if True else 0) for i in gc]
    # phase margin = 180 + angle (wrapped to (-180, 180])
    pms = [(f[i], ((math.degrees(ph[i]) + 180) % 360) - 180 + 180) for i in gc]
    pms = [(fc, pm if pm <= 180 else pm - 360) for fc, pm in pms]
    # phase crossovers: angle = -180 mod 360
    kk = np.floor((ph + np.pi) / (2 * np.pi))
    pc = [(f[i], mag[i]) for i in np.where(np.diff(kk) != 0)[0]]
    # Nyquist: count encirclements of -1 over [0, inf) by the winding of 1 + L; with the integrator the full contour
    # needs the small indentation (a quarter turn); use the closed-loop pole route instead where it matters.
    return pms, pc, f, Lf


def enc(v, trim, b, k, **kw):
    f = np.concatenate([np.logspace(-4, 1.5, 200000), np.linspace(31.7, 500, 200000)])
    Lf = L_outer(f, v, trim, b, k, **kw)
    w = np.unwrap(np.angle(1 + Lf))
    return (w[-1] - w[0]) / (2 * np.pi)


if __name__ == "__main__":
    print(f"VehicleModel: m {m:.0f} kg, cF {cF:.0f}, cR {cR:.0f}, slip factor {sF:.3e}; G_la(v) m/s^2 per deg: "
          + ", ".join(f"{v}:{G_la(v):.4f}" for v in (3, 5, 8, 12.5, 19, 26)))
    print("lsf:", ", ".join(f"{v}:{lsf(v):.3f}" for v in (3, 5, 8, 12.5, 19, 26)))
    for world in ("light", "ident"):
        print(f"\n=== {world}-b world, tau 25 ms + output lag + ZOH (~62 ms), trim Td 3 ms, friction slope ON ===")
        print("  v     | V293 plant: gain crossovers (f, PM)            | V294 plant: gain crossovers (f, PM)             | dPM at first xover | phase xovers |L| V293 -> V294")
        for v in (3, 5, 8, 12.5, 19, 26):
            k = float(np.interp(v, HOLD_V_BP, HOLD_K_V)); b = 6e-4 if world == "light" else 1 / float(np.interp(v, G_BP, G_V))
            p3, c3, _, _ = margins(v, False, b, k)
            p4, c4, _, _ = margins(v, True, b, k)
            d = (p4[0][1] - p3[0][1]) if p3 and p4 else float('nan')
            s3 = "; ".join(f"{fc:.3f} Hz {pm:+.0f}" for fc, pm in p3[:3]); s4 = "; ".join(f"{fc:.3f} Hz {pm:+.0f}" for fc, pm in p4[:3])
            gc3 = ", ".join(f"{fc:.2f}Hz:{g:.2f}" for fc, g in c3 if fc > 0.05)[:60]
            gc4 = ", ".join(f"{fc:.2f}Hz:{g:.2f}" for fc, g in c4 if fc > 0.05)[:60]
            print(f"  {v:5.1f} | {s3:46s} | {s4:46s} | {d:+6.1f} deg | {gc3} -> {gc4}")
