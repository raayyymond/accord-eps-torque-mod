# -*- coding: utf-8 -*-
"""r2 -- THE REPAIRED STATISTIC and the PRE-REGISTERED GATE.

STATISTIC  R = |L| at the first -180 deg crossing of the open loop in 1-8 Hz.  R >= 1 predicts a
           limit cycle there.  (The failed engine's VM = min|1+L| over 2-6 Hz is struck.)

PLANT (per route, identified):  P_th(s) = alpha / (J s^2 + b s + k(v)) * exp(-s D)
       J = HONDA_ACCORD_EPS_INERTIA = 8e-5, b = 0.0006, k(v) = HONDA_ACCORD_HOLD_K_V  (fork source),
       alpha = |H_iv|(0.15-0.30 Hz) * k(v), H_iv = S_wy/S_wu with the logged setpoint w as instrument.

CONTROLLER (per route, from ITS OWN initData and ITS OWN flown commit):
       C_e(f) = notch(f) * (1+lsf/kp) * [ (kp + ki_eff I(z))/LAF + friction * N_DF(A) ]
       L = C_e * c(v) * P_th   +   g_eff * H_rc(f) * j w * P_th

REPAIR TERMS, exactly two: (1) the SteerFriction relay's describing function, (2) the
AccordRateLoopGain inner loop.  The disturbance observer is NOT modelled (that would be a third).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PARAMS = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/hsurface/surface/params_all.json")
DT = 0.01
NBOOT = 2000

J = 8e-5
B_PLANT = 0.0006
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
LOW_SPEED_X = [0, 10, 20, 30]
LOW_SPEED_Y = [12, 10.5, 8, 5]
FRIC_THR = 0.30
RATE_RC = 0.01
RATE_TAPER_V = 12.0
STOCK_FRIC = 0.2120497022936265
STOCK_LAF = 1.6893333799149202
STOCK_KI = 0.35

# commit -> (has notch, has rate loop, has the friction_hyst guard, has dob), by grep on each flown commit
COMMIT = {
    "8a28dcef8199bc5d33246d1ce6d646e4bd407839": (0, 0, 0, 0),
    "ffe28378f139a820bcd17b4ae0be9e0ab07cf0d5": (0, 0, 0, 0),
    "0f98d8c7573e0aa": (0, 0, 0, 0), "57410c3b40c2aff": (0, 0, 0, 0),
    "4247cb09ef57223": (0, 0, 0, 0), "66cf4454abe8c61": (0, 0, 0, 0),
    "e8e62f0e194bd5f": (1, 1, 0, 0), "08a5a7064984796": (1, 1, 1, 0),
    "e44b6cd31807340": (1, 1, 1, 1), "84766cdc523face": (1, 1, 1, 1),
}
LBL = {"00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old",
       "0000003c--927965c2b4": "V282old", "00000064--ce6b0b0ebb": "V282",
       "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "0000006c--68c6e94b17": "T64 rev6.4", "0000006d--05e83bb04f": "T64 rev6.4",
       "0000006e--6ca3e014fd": "T64B rev6.4", "00000070--717f5a7866": "V293 r1",
       "00000071--f2c9d073a3": "r71 *LIMIT CYCLE 2.34 Hz*", "00000072--8001fc3048": "r72 clean",
       "00000073--79fd149dd8": "r73 clean", "00000075--6c8687d5bd": "T4 rev4",
       "00000076--d0b7ea7e4d": "T5 rev5"}


def fnum(x, dflt):
    return dflt if x in (None, "ABSENT") else float(x)


def read_controllers():
    P = json.load(open(PARAMS))
    out = {}
    for rt, d in P.items():
        cm = d["GitCommit"]
        key = [k for k in COMMIT if k.startswith(cm[:15]) or cm.startswith(k[:15])]
        notch_c, rate_c, guard_c, dob_c = COMMIT[key[0]]
        fric = fnum(d.get("SteerFriction"), STOCK_FRIC)
        hyst = fnum(d.get("AccordFrictionHyst"), 0.015) if notch_c else None   # key only exists from e8e62f0e1
        # use_custom_friction is DERIVED: round(toggle,2) != round(stock,2).  When it is False the
        # controller runs CP's own friction, which is the same 0.21205 number.  Either way -> fric.
        relay_live = fric > 0.0 and not (guard_c and hyst is not None and hyst > 0.0)
        out[rt] = dict(
            kp=fnum(d.get("SteerKP"), 1.0), laf=fnum(d.get("SteerLatAccel"), STOCK_LAF),
            ki=fnum(d.get("AccordTorqueKi"), 0.30), ki_hi=fnum(d.get("AccordTorqueKiHigh"), 0.0),
            notch=(fnum(d.get("AccordErrorNotchQ"), 1.0) if notch_c else None),
            fric_param=fric, hyst=hyst, relay=relay_live,
            fric=(fric if relay_live else 0.0),
            rate=(fnum(d.get("AccordRateLoopGain"), 0.0006) if rate_c else 0.0),
            dob=(fnum(d.get("AccordDobHz"), 0.0) if dob_c else 0.0),
            commit=cm[:9], lbl=LBL.get(rt, ""))
    return out


def k_of(v):
    return float(np.interp(v, HOLD_V_BP, HOLD_K_V))


def mode_hz(v):
    return float(np.sqrt(k_of(v) / J) / (2 * np.pi))


def lsf_of(v):
    return float((np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, 1.0)) ** 2)


def notch_H(f, f0, q):
    z = np.exp(-2j * np.pi * np.asarray(f) * DT)
    k = np.tan(np.pi * min(f0, 0.45 / DT) * DT)
    n = 1.0 / (1.0 + k / q + k * k)
    b0, b1, a2 = (1.0 + k * k) * n, 2.0 * (k * k - 1.0) * n, (1.0 - k / q + k * k) * n
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def df_ramp(A, thr=FRIC_THR):
    """Describing function of the fork's own get_friction shape clip(x/thr) (deadzone 0, Honda).
    A <= thr -> exactly 1/thr.   A >> thr -> 4/(pi A), i.e. the relay gain 4F/(pi A)."""
    A = float(A)
    if A <= thr:
        return 1.0 / thr
    r = thr / A
    return (2.0 / (np.pi * thr)) * (np.arcsin(r) + r * np.sqrt(1.0 - r * r))


def C_e(f, v, p, A):
    z = np.exp(-2j * np.pi * np.asarray(f) * DT)
    lsf = lsf_of(v)
    ki = p["ki"] if p["ki_hi"] <= 0 else float(np.interp(v, [15.0, 25.0], [p["ki"], p["ki_hi"]]))
    I = ki * DT / (1.0 - z)
    C = (1.0 + lsf / max(p["kp"], 1e-3)) * ((p["kp"] + I) / p["laf"] + p["fric"] * df_ramp(A))
    if p["notch"]:
        C = C * notch_H(f, mode_hz(v), p["notch"])
    return C


def L_of(f, v, alpha, c, p, A, D):
    s = 2j * np.pi * np.asarray(f)
    P = alpha * np.exp(-s * D) / (J * s ** 2 + B_PLANT * s + k_of(v))
    a = DT / (RATE_RC + DT)
    Hrc = a / (1.0 - (1.0 - a) * np.exp(-s * DT))
    g = p["rate"] * min(1.0, RATE_TAPER_V / max(v, 0.1))
    return C_e(f, v, p, A) * c * P + g * Hrc * s * P


def crossing(f, L):
    ph = np.unwrap(np.angle(L))
    mag = np.abs(L)
    sel = (f >= 1.0) & (f <= 8.0)
    ff, pp, mm = f[sel], ph[sel], mag[sel]
    pp = pp - 2 * np.pi * np.round(pp[0] / (2 * np.pi))
    idx = np.where((pp[:-1] > -np.pi) & (pp[1:] <= -np.pi))[0]
    if not len(idx):
        return np.nan, np.nan
    i = idx[0]
    w = (pp[i] + np.pi) / (pp[i] - pp[i + 1])
    fx = float(ff[i] + w * (ff[i + 1] - ff[i]))
    return float(np.exp(np.interp(fx, ff, np.log(mm)))), fx


def load_plants(binname):
    S = json.load(open(OUT / "r1_ident.json"))
    cells = {k: v for k, v in S["cells"].items() if v["bin"] == binname}
    P = {}
    for key, D in cells.items():
        wu = np.array(D["wSwu_re"]) + 1j * np.array(D["wSwu_im"])
        wy = np.array(D["wSwy_re"]) + 1j * np.array(D["wSwy_im"])
        rid = np.array(D["rid"])
        P[D["route"]] = dict(v=D["v"], c=D["c"], A=np.sqrt(2) * D["A_rms"], coh=D["coh"], ph=D["anchor_ph"],
                             n_run=D["n_run"], n_win=D["n_win"], secs=D["secs"],
                             wu=wu, wy=wy, rid=rid, A_rms=D["A_rms"], sat=D["sat_frac"],
                             alpha=abs(np.mean(wy.mean(0) / wu.mean(0))) * k_of(D["v"]))
    return P


def alpha_boot(pl, rng, nboot=NBOOT):
    rid, wu, wy = pl["rid"], pl["wu"], pl["wy"]
    runs = np.unique(rid)
    out = np.empty(nboot)
    for b in range(nboot):
        if len(runs) >= 3:
            pick = rng.choice(runs, size=len(runs), replace=True)
            sel = np.concatenate([np.where(rid == r)[0] for r in pick])
        else:
            sel = rng.choice(len(rid), size=len(rid), replace=True)
        out[b] = abs(np.mean(wy[sel].mean(0) / wu[sel].mean(0))) * k_of(pl["v"])
    return out
