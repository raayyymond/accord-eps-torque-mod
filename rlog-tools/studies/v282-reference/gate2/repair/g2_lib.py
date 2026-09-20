# -*- coding: utf-8 -*-
"""GATE #2 -- the JERK-LEAD repair.  Built on retrodict/repair/r2_stat.py, constants RE-VERIFIED.

ONE NEW TERM vs gate #1, and only one: the jerk content of the relay's own argument.

  fork source, latcontrol_torque.py @ every flown commit:
      line  40:  JERK_GAIN = 0.22
      line 553:  ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, ...)
      line  38:  LP_FILTER_CUTOFF_HZ = 1.2      (the filter on the jerk, RC = 1/(2*pi*1.2) = 0.13263 s)

  => Kj = 0.22 FROM SOURCE, not fitted.

Gate #1's controller model:
      C_e = notch*(1+lsf/kp)*[ (kp + I)/LAF + fric*N ]
Gate #2's:
      C_e = notch*(1+lsf/kp)*[ (kp + I)/LAF + fric*N ]  +  fric*N*Kj*s/(1 + s*RCj)
                                                          ^^^^^^^^^^^^^^^^^^^^^^^^ THE ONE NEW TERM

CONSTANT CORRECTIONS found while re-verifying gate #1 (each read from the flown commit):
  * HONDA_ACCORD_RATE_LOOP_RC is 0.03 s at e8e62f0e1/08a5a7064 (r72,r73,r74,r75) and 0.01 s only from
    e44b6cd31 (rev 5).  r2_stat used 0.01 everywhere.
  * HONDA_ACCORD_HOLD_K_V[-1] (28 m/s knot) is 0.0134 at e8e62f0e1 and 0.0160 from 08a5a7064.  That
    table sets the NOTCH CENTRE the controller flew (get_honda_accord_mode_hz), so r72/r73 notched at
    2.06 Hz, not 2.21 Hz.  r2_stat used 0.0160 for every route.
  The PLANT's k(v) is a physical property of the car, so one table (the later one) is used for the
  plant on every route, and swept separately.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
R1 = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/retrodict/repair/out/r1_ident.json")
PARAMS = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/hsurface/surface/params_all.json")

DT = 0.01
J = 8e-5
KJ = 0.22                      # JERK_GAIN, fork source line 40.  NOT FITTED.
RC_JERK = 1.0 / (2 * np.pi * 1.2)   # LP_FILTER_CUTOFF_HZ = 1.2, fork source line 38
JERK_CLIP = 2.5                # MAX_LAT_JERK_UP, m/s^3 (reported, not used in the DF)
FRIC_THR = 0.30                # get_standard_friction_threshold on this car
RATE_TAPER_V = 12.0            # HONDA_ACCORD_RATE_LOOP_TAPER_V
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
K_LATE = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
K_EARLY = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134]
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
STOCK_FRIC = 0.2120497022936265
STOCK_LAF = 1.6893333799149202

# commit -> (notch, rateloop, guard, dob, rate_RC, k_table_for_the_notch_centre)
# every field re-verified by `git show <commit>:selfdrive/controls/lib/...` on 2026-09-20.
COMMIT = {
    "8a28dcef8199bc5d33246d1ce6d646e4bd407839": (0, 0, 0, 0, 0.03, K_EARLY),
    "ffe28378f139a820bcd17b4ae0be9e0ab07cf0d5": (0, 0, 0, 0, 0.03, K_EARLY),
    "0f98d8c7573e0aa": (0, 0, 0, 0, 0.03, K_EARLY), "57410c3b40c2aff": (0, 0, 0, 0, 0.03, K_EARLY),
    "4247cb09ef57223": (0, 0, 0, 0, 0.03, K_EARLY), "66cf4454abe8c61": (0, 0, 0, 0, 0.03, K_EARLY),
    "e8e62f0e194bd5f": (1, 1, 0, 0, 0.03, K_EARLY),   # <-- RC 0.03, notch centre from the EARLY table
    "08a5a7064984796": (1, 1, 1, 0, 0.03, K_LATE),
    "e44b6cd31807340": (1, 1, 1, 1, 0.01, K_LATE),
    "84766cdc523face": (1, 1, 1, 1, 0.01, K_LATE),
}
LBL = {"00000039--f56039af87": "V282old CLEAN", "0000003a--283a39a1d6": "V282old CLEAN",
       "0000003c--927965c2b4": "V282old CLEAN", "00000064--ce6b0b0ebb": "V282 CLEAN",
       "00000065--b9f78988bd": "V282 CLEAN", "0000006c--2bc842dbac": "V282 CLEAN",
       "0000006c--68c6e94b17": "T64 rev6.4 CLEAN", "0000006d--05e83bb04f": "T64 rev6.4 CLEAN",
       "0000006e--6ca3e014fd": "T64B rev6.4 CLEAN", "00000070--717f5a7866": "V293 r1 (unlabelled)",
       "00000071--f2c9d073a3": "r71 POSITIVE 2.34Hz", "00000072--8001fc3048": "r72 CLEAN",
       "00000073--79fd149dd8": "r73 POSITIVE 4-6.5Hz", "00000075--6c8687d5bd": "T4 rev4 (unlabelled)",
       "00000076--d0b7ea7e4d": "T5 rev5 (unlabelled)"}

R71 = "00000071--f2c9d073a3"
R73 = "00000073--79fd149dd8"
R72 = "00000072--8001fc3048"
POSITIVES = [R71, R73]
# the prereg's clean anchors.  V282 = the three 0.010 routes; V282old = the three 0.030 routes.
CLEAN_T64 = ["0000006c--68c6e94b17", "0000006e--6ca3e014fd"]          # the prereg's "2 routes"
CLEAN_T64_ALL = CLEAN_T64 + ["0000006d--05e83bb04f"]
CLEAN_V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
CLEAN_V282_OLD = ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"]
CLEANS5 = [R72] + CLEAN_T64 + CLEAN_V282                              # the prereg's table, 6 rows
V282_ERA = CLEAN_V282 + CLEAN_V282_OLD
# plants not taken from either positive's own log, in the V293 model domain, with enough data
PREREG_PLANTS = [R72, "0000006c--68c6e94b17", "0000006e--6ca3e014fd"]


def fnum(x, dflt):
    return dflt if x in (None, "ABSENT") else float(x)


def k_of(v, tbl=None):
    return float(np.interp(v, HOLD_V_BP, K_LATE if tbl is None else tbl))


def mode_hz(v, tbl=None):
    return float(np.sqrt(k_of(v, tbl) / J) / (2 * np.pi))


def lsf_of(v):
    return float((np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, 1.0)) ** 2)


def read_controllers():
    P = json.load(open(PARAMS))
    out = {}
    for rt, d in P.items():
        cm = d["GitCommit"]
        key = [k for k in COMMIT if k.startswith(cm[:15]) or cm.startswith(k[:15])][0]
        notch_c, rate_c, guard_c, dob_c, rc, ktbl = COMMIT[key]
        fric = fnum(d.get("SteerFriction"), STOCK_FRIC)
        hyst = fnum(d.get("AccordFrictionHyst"), 0.015) if notch_c else None
        relay_live = fric > 0.0 and not (guard_c and hyst is not None and hyst > 0.0)
        out[rt] = dict(
            kp=fnum(d.get("SteerKP"), 1.0), laf=fnum(d.get("SteerLatAccel"), STOCK_LAF),
            ki=fnum(d.get("AccordTorqueKi"), 0.30), ki_hi=fnum(d.get("AccordTorqueKiHigh"), 0.0),
            notch=(fnum(d.get("AccordErrorNotchQ"), 1.0) if notch_c else None),
            fric_param=fric, hyst=hyst, relay=relay_live,
            fric=(fric if relay_live else 0.0),
            rate=(fnum(d.get("AccordRateLoopGain"), 0.0006) if rate_c else 0.0),
            rate_rc=rc, ktbl=ktbl, guard=guard_c,
            dob=(fnum(d.get("AccordDobHz"), 0.0) if dob_c else 0.0),
            commit=cm[:9], lbl=LBL.get(rt, ""))
    return out


def notch_H(f, f0, q):
    """Byte-for-byte the fork's HondaAccordErrorNotch.update (bilinear notch)."""
    z = np.exp(-2j * np.pi * np.asarray(f) * DT)
    k = np.tan(np.pi * min(f0, 0.45 / DT) * DT)
    n = 1.0 / (1.0 + k / q + k * k)
    b0, b1, a2 = (1.0 + k * k) * n, 2.0 * (k * k - 1.0) * n, (1.0 - k / q + k * k) * n
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def df_ramp(A, thr=FRIC_THR):
    """DF of the fork's get_friction shape, clip(x/thr).  A <= thr -> exactly 1/thr."""
    A = float(A)
    if A <= thr:
        return 1.0 / thr
    r = thr / A
    return (2.0 / (np.pi * thr)) * (np.arcsin(r) + r * np.sqrt(1.0 - r * r))


def C_e(f, v, p, A, jerk=True):
    """Controller, error -> torque.  `jerk=False` reproduces gate #1 exactly."""
    f = np.asarray(f, dtype=float)
    z = np.exp(-2j * np.pi * f * DT)
    s = 2j * np.pi * f
    lsf = lsf_of(v)
    ki = p["ki"] if p["ki_hi"] <= 0 else float(np.interp(v, [15.0, 25.0], [p["ki"], p["ki_hi"]]))
    I = ki * DT / (1.0 - z)
    N = df_ramp(A)
    err_branch = (1.0 + lsf / max(p["kp"], 1e-3)) * ((p["kp"] + I) / p["laf"] + p["fric"] * N)
    if p["notch"]:
        err_branch = err_branch * notch_H(f, mode_hz(v, p["ktbl"]), p["notch"])
    if not jerk:
        return err_branch
    # ---- THE ONE NEW TERM: Kj * (jerk of the relay's own argument), LP-filtered at 1.2 Hz ----
    return err_branch + p["fric"] * N * KJ * s / (1.0 + s * RC_JERK)


def L_of(f, v, alpha, c, p, A, D, b, jerk=True, ktbl_plant=None):
    f = np.asarray(f, dtype=float)
    s = 2j * np.pi * f
    P = alpha * np.exp(-s * D) / (J * s ** 2 + b * s + k_of(v, ktbl_plant))
    a = DT / (p["rate_rc"] + DT)
    Hrc = a / (1.0 - (1.0 - a) * np.exp(-s * DT))
    g = p["rate"] * min(1.0, RATE_TAPER_V / max(v, 0.1))
    return C_e(f, v, p, A, jerk) * c * P + g * Hrc * s * P


def crossings(f, L, flo=1.0, fhi=8.0):
    """EVERY -180 deg crossing in [flo, fhi], as (|L|, f) pairs, lowest first."""
    ph = np.unwrap(np.angle(L))
    mag = np.abs(L)
    sel = (f >= flo) & (f <= fhi)
    ff, pp, mm = f[sel], ph[sel], mag[sel]
    pp = pp - 2 * np.pi * np.round(pp[0] / (2 * np.pi))
    idx = np.where((pp[:-1] > -np.pi) & (pp[1:] <= -np.pi))[0]
    out = []
    for i in idx:
        w = (pp[i] + np.pi) / (pp[i] - pp[i + 1])
        fx = float(ff[i] + w * (ff[i + 1] - ff[i]))
        out.append((float(np.exp(np.interp(fx, ff, np.log(mm)))), fx))
    return out


def first_crossing(f, L, flo=1.0, fhi=8.0):
    cr = crossings(f, L, flo, fhi)
    return cr[0] if cr else (np.nan, np.nan)


def worst_crossing(f, L, flo=1.0, fhi=8.0):
    cr = crossings(f, L, flo, fhi)
    return max(cr, key=lambda t: t[0]) if cr else (np.nan, np.nan)


def load_plants(binname="22+"):
    S = json.load(open(R1))
    P = {}
    for _, D in S["cells"].items():
        if D["bin"] != binname:
            continue
        wu = np.array(D["wSwu_re"]) + 1j * np.array(D["wSwu_im"])
        wy = np.array(D["wSwy_re"]) + 1j * np.array(D["wSwy_im"])
        P[D["route"]] = dict(v=D["v"], c=D["c"], A=np.sqrt(2) * D["A_rms"], coh=D["coh"],
                             ph=D["anchor_ph"], n_run=D["n_run"], n_win=D["n_win"], secs=D["secs"],
                             rid=np.array(D["rid"]), wu=wu, wy=wy, sat=D["sat_frac"],
                             alpha=abs(np.mean(wy.mean(0) / wu.mean(0))) * k_of(D["v"]))
    return P


def alpha_boot(pl, rng, nboot=2000):
    rid, wu, wy = pl["rid"], pl["wu"], pl["wy"]
    runs = np.unique(rid)
    out = np.empty(nboot)
    for i in range(nboot):
        if len(runs) >= 3:
            pick = rng.choice(runs, size=len(runs), replace=True)
            sel = np.concatenate([np.where(rid == r)[0] for r in pick])
        else:
            sel = rng.choice(len(rid), size=len(rid), replace=True)
        out[i] = abs(np.mean(wy[sel].mean(0) / wu[sel].mean(0))) * k_of(pl["v"])
    return out
