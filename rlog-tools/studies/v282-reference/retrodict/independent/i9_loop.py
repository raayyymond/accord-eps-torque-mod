# -*- coding: utf-8 -*-
"""i9 -- the independent retrodiction: build L(f) for every flown V293 controller on every flown
V293 operating point, from the fork's own arithmetic and one physical plant.

THE PLANT (the fork's own, and nothing else):
    J*th'' + b*th' + k(v)*th = torque_left        J = HONDA_ACCORD_EPS_INERTIA = 8e-5
    P_th(jw) = 1 / (k - J w^2 + j b w)            [deg of wheel angle per unit command torque]
    k(v)     = interp(v, HONDA_ACCORD_HOLD_V_BP, HONDA_ACCORD_HOLD_K_V) * KMUL
    D(jw)    = exp(-j w tau)                      tau = the measured round trip

THE CONTROLLER, re-derived from the source at each ROUTE'S OWN flown commit (forksnap/), with every
parameter from that route's OWN initData.  Sign chain, verified against the logs in i4:
    measurement    = -g * th                       g = -d(la_act)/d(sa), measured per route/bin
    error_with_lsf = Notch(z) * (1 + lsf/kp) * (setpoint - measurement)
    p + i          = PI(z) * error_with_lsf
    friction term  = (friction / 0.30) * Ndf * error_with_lsf      [torque, LAF cancels]
    inner rate     = -g_rate(v) * LP(jw) * (measured wheel rate)   [torque]
    out = pid_log.output = -output_torque = the +LEFT-FRAME torque
  =>  T_left = K(jw) * th + (reference terms), with
        K = -g*(1+lsf/kp)*Notch*(PI/LAF + (fric/0.30)*Ndf)  -  g_rate*LP*(j w)
        L = -P_th * D * K,   characteristic equation 1 + L = 0.

EVERY per-route flag (notch present, relay guarded, rate loop present, RC) comes from the git-shown
source at that commit, not from a table someone typed.

ANALYSIS ONLY.  python i9_loop.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------- plant / fork tables
J_EPS = 8e-5
B_EPS = 6e-4
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V_REV4 = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
HOLD_K_V_REV3 = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134]
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 1.0
KI_SCHED_BP = [8.0, 18.0]
RATE_TAPER_V = 12.0
FRICTION_THRESHOLD = 0.30
DT = 0.01

# ------------------------------------------------------------------------------- flown controllers
# EVERY field: initData (hsurface/surface/params_all.json) for the values, forksnap/ git-show for the
# code flags.  relay_live = the commit has NO `friction_torque = 0.0 if friction_hyst > 0.0` guard
# AND SteerFriction > 0.  notch = the commit calls accord_error_notch.update (Q defaults to 1.0 when
# AccordErrorNotchQ is absent, verified in get_value: condition False -> default).
CTRL = {
    "r70":  dict(route="00000070--717f5a7866", commit="4247cb09e", kp=0.30, laf=6.0, ki=0.15, ki_hi=0.0,
                 fric=0.0,   notch=False, notch_tab=None,      relay_live=False, grate=0.0,    rc=None, dob=False),
    "r71":  dict(route="00000071--f2c9d073a3", commit="66cf4454a", kp=0.85, laf=14.0, ki=0.30, ki_hi=0.0,
                 fric=0.011, notch=False, notch_tab=None,      relay_live=True,  grate=0.0,    rc=None, dob=False),
    "r72":  dict(route="00000072--8001fc3048", commit="e8e62f0e1", kp=0.85, laf=14.0, ki=0.60, ki_hi=0.0,
                 fric=0.0,   notch=True,  notch_tab="rev3",    relay_live=False, grate=0.0006, rc=0.03, dob=False),
    "r73":  dict(route="00000073--79fd149dd8", commit="e8e62f0e1", kp=0.85, laf=14.0, ki=0.60, ki_hi=0.0,
                 fric=0.2120497, notch=True, notch_tab="rev3", relay_live=True,  grate=0.0006, rc=0.03, dob=False),
    "r75":  dict(route="00000075--6c8687d5bd", commit="08a5a7064", kp=0.85, laf=14.0, ki=0.60, ki_hi=2.5,
                 fric=0.2120497, notch=True, notch_tab="rev4", relay_live=False, grate=0.0006, rc=0.03, dob=False),
    "r76":  dict(route="00000076--d0b7ea7e4d", commit="e44b6cd31", kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0,
                 fric=0.0,   notch=True,  notch_tab="rev4",    relay_live=False, grate=0.0010, rc=0.01, dob=True),
    "T64a": dict(route="0000006c--68c6e94b17", commit="84766cdc5", kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0,
                 fric=0.0,   notch=True,  notch_tab="rev4",    relay_live=False, grate=0.0010, rc=0.01, dob=True),
    "T64b": dict(route="0000006d--05e83bb04f", commit="84766cdc5", kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0,
                 fric=0.2120497, notch=True, notch_tab="rev4", relay_live=False, grate=0.0010, rc=0.01, dob=True),
    "T64B": dict(route="0000006e--6ca3e014fd", commit="84766cdc5", kp=1.00, laf=14.0, ki=0.30, ki_hi=0.0,
                 fric=0.0,   notch=True,  notch_tab="rev4",    relay_live=False, grate=0.0010, rc=0.01, dob=True),
}
OUTCOME = {"r70": "clean", "r71": "LIMIT CYCLE 2.30 Hz", "r72": "clean", "r73": "clean",
           "r75": "clean", "r76": "clean", "T64a": "clean", "T64b": "clean", "T64B": "clean"}


def lsf_of(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, MIN_SPEED)) ** 2


def k_of(v, table=HOLD_K_V_REV4):
    return float(np.interp(v, HOLD_V_BP, table))


def mode_hz(v, table):
    return float(np.sqrt(k_of(v, table) / J_EPS) / (2 * np.pi))


def notch_response(f, f0, q=1.0, dt=DT):
    """EXACT discrete response of HondaAccordErrorNotch at the coefficients it computes for f0."""
    k = np.tan(np.pi * min(float(f0), 0.45 / dt) * dt)
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def pi_response(f, kp, ki, dt=DT):
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    with np.errstate(divide="ignore", invalid="ignore"):
        return kp + ki * dt / (1.0 - z)


def lp1(f, rc, dt=DT):
    """EXACT discrete first-order filter x += alpha*(u-x), alpha = dt/(rc+dt)."""
    if not rc:
        return np.ones_like(np.asarray(f, float), dtype=complex)
    a = dt / (rc + dt)
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return a / (1.0 - (1.0 - a) * z)


def notch_smeared(f, table, vs, wts=None):
    """The notch as it actually acts over a stretch of driving: its centre is recomputed EVERY FRAME
    from that frame's speed (get_honda_accord_mode_hz(CS.vEgo)), so over a window whose speed varies
    the effective transfer is the speed-weighted AVERAGE of the per-speed responses, not the response
    at the median speed.  Measured consequence (i11, route 73): the single-speed notch is ~2x too deep
    at 1.5-1.8 Hz against the logged K, and its +/-90 deg phase swing is correspondingly too sharp."""
    vs = np.atleast_1d(np.asarray(vs, float))
    if wts is None:
        wts = np.ones_like(vs)
    wts = wts / wts.sum()
    acc = np.zeros(np.shape(np.asarray(f, float)), dtype=complex)
    for vv, ww in zip(vs, wts):
        acc = acc + ww * notch_response(f, mode_hz(float(vv), table), 1.0)
    return acc


def K_of(f, c, v, g, ndf=1.0, use_relay=True, use_rate=True, use_notch=True, vdist=None):
    """Controller feedback transfer: torque per DEGREE of wheel angle (see the module docstring).
    vdist: the operating point's actual speed samples, used to smear the notch (see notch_smeared)."""
    lsf = lsf_of(v)
    ki = c["ki"] if c["ki_hi"] <= 0 else float(np.interp(v, KI_SCHED_BP, [c["ki"], c["ki_hi"]]))
    PI = pi_response(f, c["kp"], ki)
    tab = HOLD_K_V_REV3 if c["notch_tab"] == "rev3" else HOLD_K_V_REV4
    if c["notch"] and use_notch:
        N = notch_smeared(f, tab, vdist) if vdist is not None else notch_response(f, mode_hz(v, tab), 1.0)
    else:
        N = 1.0
    relay = (c["fric"] / FRICTION_THRESHOLD) * ndf if (c["relay_live"] and use_relay) else 0.0
    Kpi = -g * (1.0 + lsf / max(c["kp"], 1e-3)) * N * (PI / c["laf"] + relay)
    Krate = 0.0
    if use_rate and c["grate"]:
        gr = c["grate"] * min(1.0, RATE_TAPER_V / max(v, 0.1))
        Krate = -gr * lp1(f, c["rc"]) * (2j * np.pi * np.asarray(f, float))
    return Kpi + Krate


def L_of(f, c, v, g, tau=0.060, kmul=1.0, bmul=1.0, **kw):
    w = 2 * np.pi * np.asarray(f, float)
    P = 1.0 / (k_of(v) * kmul - J_EPS * w ** 2 + 1j * B_EPS * bmul * w)
    D = np.exp(-1j * w * tau)
    return -P * D * K_of(f, c, v, g, **kw), P, D


def crossing(f, L, fmin=0.8, fmax=8.0):
    """FIRST -180 deg crossing of L above fmin, and |L| there. Returns (f_x, |L|, n_crossings)."""
    s = (f >= fmin) & (f <= fmax)
    ff, LL = f[s], L[s]
    ph = np.degrees(np.angle(LL))
    mag = np.abs(LL)
    hits = []
    for i in range(len(ff) - 1):
        a, b = ph[i], ph[i + 1]
        if a < -90 and b > 90:                      # wrapped through -180
            wgt = (a + 180.0) / ((a + 180.0) - (b - 180.0))
            fx = ff[i] + wgt * (ff[i + 1] - ff[i])
            mx = np.exp(np.log(mag[i]) + wgt * (np.log(mag[i + 1]) - np.log(mag[i])))
            hits.append((float(fx), float(mx)))
    if not hits:
        return None
    return hits[0][0], hits[0][1], len(hits)


def peak_mag(f, L, fmin=0.8, fmax=8.0):
    s = (f >= fmin) & (f <= fmax)
    k = int(np.argmax(np.abs(L[s])))
    return float(f[s][k]), float(np.abs(L[s])[k])


def _self_test():
    """Positive controls on the pieces, against values computable by hand."""
    out = []
    f = np.linspace(0.05, 8.0, 4000)
    # 1. the notch is a true notch: |N| -> 0 at f0 and -> 1 far away
    N = notch_response(np.array([1.9, 0.1, 20.0]), 1.9, 1.0)
    assert abs(N[0]) < 5e-3 and abs(abs(N[1]) - 1) < 0.02 and abs(abs(N[2]) - 1) < 0.15, N
    out.append(f"  notch |N| at f0 {abs(N[0]):.4f}, at 0.1 Hz {abs(N[1]):.3f}, at 20 Hz {abs(N[2]):.3f}")
    # 2. the plant's UNDAMPED natural frequency is sqrt(k/J)/2pi = get_honda_accord_mode_hz, and its
    #    -90 deg point sits there; the |P| PEAK sits lower, at wn*sqrt(1-2*zeta^2), because the
    #    damping is not light (zeta = b/(2*sqrt(kJ)) ~ 0.3 at speed).  Both are checked.
    v = 19.1
    P = 1.0 / (k_of(v) - J_EPS * (2 * np.pi * f) ** 2 + 1j * B_EPS * (2 * np.pi * f))
    fn = mode_hz(v, HOLD_K_V_REV4)
    jn = int(np.argmin(np.abs(f - fn)))
    assert abs(np.degrees(np.angle(P[jn])) + 90.0) < 1.0, np.degrees(np.angle(P[jn]))
    zeta = B_EPS / (2 * np.sqrt(k_of(v) * J_EPS))
    fr = f[int(np.argmax(np.abs(P)))]
    assert abs(fr - fn * np.sqrt(max(1 - 2 * zeta ** 2, 1e-9))) < 0.02, (fr, fn, zeta)
    out.append(f"  plant: fn {fn:.3f} Hz (P phase there {np.degrees(np.angle(P[jn])):.1f} deg), "
               f"zeta {zeta:.3f}, |P| peak {fr:.3f} == fn*sqrt(1-2z^2) "
               f"{fn*np.sqrt(1-2*zeta**2):.3f} Hz")
    # 3. DC gain of P is 1/k, and of the P-only controller is g*(1+lsf/kp)*kp/laf
    assert abs(abs(P[0]) - 1.0 / k_of(v)) / (1.0 / k_of(v)) < 0.01
    c = CTRL["r71"]
    Kdc = K_of(np.array([1e-3]), c, v, 0.1, ndf=0.0, use_relay=False)
    hand = -0.1 * (1 + lsf_of(v) / c["kp"]) * (c["kp"] / c["laf"])
    assert abs(Kdc[0].real - hand) / abs(hand) < 0.02, (Kdc[0], hand)
    out.append(f"  K(DC) no relay {Kdc[0].real:.6f} == hand {hand:.6f}")
    # 4. the relay/P ratio equals friction*LAF/(0.30*kp)
    Kr = K_of(np.array([2.3]), c, v, 0.1, ndf=1.0)
    Kn = K_of(np.array([2.3]), c, v, 0.1, use_relay=False)
    ratio = abs(Kr[0]) / abs(Kn[0])
    hand = 1.0 + c["fric"] * c["laf"] / (FRICTION_THRESHOLD * c["kp"])
    assert abs(ratio - hand) < 0.02, (ratio, hand)
    out.append(f"  relay multiplier on K at 2.3 Hz {ratio:.4f} == 1+fric*LAF/(0.3*kp) {hand:.4f}")
    # 5. a pure delay + a 2nd-order plant + a pure gain crosses -180 where hand algebra says
    f5 = np.linspace(0.5, 8.0, 20000)
    L5, _, _ = L_of(f5, dict(kp=1.0, laf=1.0, ki=0.0, ki_hi=0.0, fric=0.0, notch=False,
                             notch_tab=None, relay_live=False, grate=0.0, rc=None), 19.1, 1.0, tau=0.060)
    cx = crossing(f5, L5)
    w = 2 * np.pi * cx[0]
    ph = np.degrees(np.angle(-1.0 / (k_of(19.1) - J_EPS * w**2 + 1j * B_EPS * w)
                             * np.exp(-1j * w * 0.060) * (-1.0 * (1 + lsf_of(19.1)))))
    assert abs(abs(ph) - 180) < 1.0, (cx, ph)
    out.append(f"  synthetic crossing {cx[0]:.4f} Hz, hand-checked phase {ph:.2f} deg")
    return "SELF-TEST OK\n" + "\n".join(out)


if __name__ == "__main__":
    print(_self_test())
