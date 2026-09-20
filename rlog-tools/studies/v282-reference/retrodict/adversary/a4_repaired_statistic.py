"""A4 - rebuild the REPAIRED statistic from the brief's own recipe, then attack it.

Recipe as pre-registered:
  plant   J*th'' + b*th' + k(v)*th = torque,  J = 8e-5, b ~ 6e-4, k(v) = HONDA_ACCORD_HOLD_K_V
  anchor  gain+phase on each route's MEASURED complex plant at 0.20 Hz
  repair  (1) SteerFriction relay as a describing-function gain on error_with_lsf
          (2) AccordRateLoopGain inner loop on measured steeringRateDeg
  delay   55 / 65 / 75 ms
  verdict |L| at the -180 deg crossing

Everything here is re-derived from the fork source at each route's OWN flown commit and from
params_all.json; nothing is taken from the failed engine.
"""
import json
import math
import os
import numpy as np

OUT = os.path.dirname(__file__)

# ---- fork constants, read at commit 84766cdc523f -------------------------------------------
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
J = 8e-5
B_NOM = 6e-4
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
FRICTION_THRESHOLD = 0.30
RATE_RC = 0.01
RATE_TAPER_V = 12.0
DT = 0.01
WHEELBASE = 2.83


def k_of_v(v):
    return float(np.interp(v, HOLD_V_BP, HOLD_K_V))


def mode_hz(v):
    return math.sqrt(k_of_v(v) / J) / (2 * math.pi)


def lsf(v):
    return (float(np.interp(v, LOW_SPEED_X, LOW_SPEED_Y)) / max(v, 1.0)) ** 2


def M_lat_per_deg(v, sr):
    """static zero-lag map: m/s^2 of lateral accel per deg of wheel angle."""
    return math.radians(1.0) * v * v / (sr * WHEELBASE)


def notch_H(w, f_hz, q, dt=DT):
    """the fork's HondaAccordErrorNotch, evaluated as the digital biquad it is."""
    if q <= 0 or f_hz <= 0:
        return np.ones_like(w, dtype=complex)
    k = math.tan(math.pi * min(f_hz, 0.45 / dt) * dt)
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    z = np.exp(1j * w * dt)
    return (b0 + b1 / z + b0 / z ** 2) / (1.0 + b1 / z + a2 / z ** 2)


def df_sat(F, A, thr=FRICTION_THRESHOLD):
    """describing function of  F*clip(x/thr,-1,1)  at input amplitude A (torque per m/s^2)."""
    s = F / thr
    if A <= thr:
        return s
    d = thr / A
    return s * (2.0 / math.pi) * (math.asin(d) + d * math.sqrt(max(1.0 - d * d, 0.0)))


# ---- controllers, from each route's own initData and its own flown commit -------------------
CTRL = {
    "r71   (LIMIT CYCLE)": dict(kp=0.85, laf=14.0, ki=0.30, F=0.011,   notchQ=0.0, rate=0.0,    sr=16.88),
    "r72   (clean)":       dict(kp=0.85, laf=14.0, ki=0.60, F=0.0,     notchQ=1.0, rate=0.0006, sr=16.88),
    "r73   (clean)":       dict(kp=0.85, laf=14.0, ki=0.60, F=0.21205, notchQ=1.0, rate=0.0006, sr=16.88),
    "rev6.4(clean,flying)":dict(kp=1.00, laf=14.0, ki=0.30, F=0.0,     notchQ=1.0, rate=0.0010, sr=16.84),
    "V282  (clean,ref)":   dict(kp=0.90, laf=6.0,  ki=0.30, F=0.01,    notchQ=0.0, rate=0.0,    sr=16.84),
}

# ---- plants: measured |T| and phase at the 0.20 Hz anchor (a3) ------------------------------
A3 = json.load(open(os.path.join(OUT, "a3_plant_transfer.json")))
PLANTS = {"r71": "00000071--f2c9d073a3", "r72": "00000072--8001fc3048",
          "r73": "00000073--79fd149dd8", "T64": "0000006d--05e83bb04f",
          "V282": "0000006c--2bc842dbac"}


def loop(ctrl, Tanchor, v, D, A, b=B_NOM, w=None):
    """open-loop L(jw): lat-accel error -> torque -> wheel angle -> lat-accel."""
    if w is None:
        w = 2 * math.pi * np.linspace(0.5, 8.0, 6001)
    s = 1j * w
    k = k_of_v(v)
    P = 1.0 / (J * s ** 2 + b * s + k)                       # deg per torque
    P = P * (Tanchor / (1.0 / (J * (1j * 2 * math.pi * 0.2) ** 2 + b * (1j * 2 * math.pi * 0.2) + k)))
    g = ctrl["rate"] * min(1.0, RATE_TAPER_V / v)
    if g > 0:
        P = P / (1.0 + g * s * P / (1.0 + s * RATE_RC) * np.exp(-s * D))
    kp_eff = ctrl["kp"] + lsf(v)
    ki_eff = ctrl["ki"] * (1.0 + lsf(v) / ctrl["kp"])
    C = (kp_eff / ctrl["laf"]) + (ki_eff / ctrl["laf"]) / s + df_sat(ctrl["F"], A)
    C = C * notch_H(w, mode_hz(v), ctrl["notchQ"])
    L = C * P * M_lat_per_deg(v, ctrl["sr"]) * np.exp(-s * D)
    return w, L


def crossing(w, L):
    ph = np.unwrap(np.angle(L))
    tgt = -math.pi
    for i in range(len(w) - 1):
        if (ph[i] - tgt) * (ph[i + 1] - tgt) < 0:
            fr = (tgt - ph[i]) / (ph[i + 1] - ph[i])
            return (w[i] + fr * (w[i + 1] - w[i])) / (2 * math.pi), abs(L[i]) + fr * (abs(L[i + 1]) - abs(L[i]))
    return math.nan, math.nan


def run(v=22.0, D=0.065, A=0.20, b=B_NOM, verbose=True):
    tab = {}
    for pn, key in PLANTS.items():
        Tanchor = A3[key]["T02"]
        tab[pn] = {}
        for cn, c in CTRL.items():
            w, L = loop(c, Tanchor, v, D, A, b)
            f, m = crossing(w, L)
            tab[pn][cn] = (f, m)
    if verbose:
        print(f"\n===  |L| at the -180 deg crossing   (v={v} m/s, D={D*1000:.0f} ms, A={A} m/s^2, b={b:.1e})")
        print(f"{'plant \\ controller':22}" + "".join(f"{c:>22}" for c in CTRL))
        for pn in PLANTS:
            row = f"{pn:22}"
            for cn in CTRL:
                f, m = tab[pn][cn]
                row += f"{m:12.3f} @{f:5.2f}Hz" if np.isfinite(m) else f"{'no -180 xing':>22}"
            print(row)
        print("   riskiest per plant: " + ", ".join(
            f"{pn}:{max(tab[pn], key=lambda c: (tab[pn][c][1] if np.isfinite(tab[pn][c][1]) else -1)).split()[0]}"
            for pn in PLANTS))
    return tab


if __name__ == "__main__":
    print("mode_hz(v):", {v: round(mode_hz(v), 3) for v in (8, 15, 20, 22, 25, 28)})
    print("small-signal controller gain, torque per m/s^2 of error (lsf at 22 m/s):")
    for cn, c in CTRL.items():
        kpe = (c["kp"] + lsf(22.0)) / c["laf"]
        print(f"   {cn:22} P {kpe:.4f}  relay-slope {c['F']/FRICTION_THRESHOLD:.4f}  "
              f"sum {kpe + c['F']/FRICTION_THRESHOLD:.4f}  (x r71 = {(kpe + c['F']/FRICTION_THRESHOLD)/0.1038:.2f})")
    for D in (0.055, 0.065, 0.075):
        run(v=22.0, D=D, A=0.20)
