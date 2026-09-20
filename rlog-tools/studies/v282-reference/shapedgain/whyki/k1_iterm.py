# -*- coding: utf-8 -*-
"""K1 -- IS THE INTEGRATOR CLAMP-LIMITED OR GAIN-LIMITED?  Measured, per route.

SOURCE (EVIDENCE, read at StarPilot HEAD):
  latcontrol_torque.py:339-348   low_speed_factor = (interp(v,[0,10,20,30],[12,10.5,8,5])/max(v,1))**2
                                 error          = setpoint - measurement
                                 error_with_lsf = error * (1 + lsf/max(kp,1e-3))
                                 error_with_lsf = accord_error_notch(error_with_lsf, mode_hz(v), Q)
                                 pid_log.error  = error_with_lsf          <-- cached as cs_err
  common/pid.py:46-62            i_k = i_{k-1} + k_i*dt*error             (error == pid_log.error)
                                 anti-windup: i clipped to +/-pos_limit unless p+i+d+f is ALREADY
                                 outside that limit, in which case i is held.
  latcontrol_torque.py:80,242    PIDController(..., rate=100); set_limits(lateral_accel_from_torque(+/-1))
                                 => pos_limit == +LAF (the Honda map is linear), i.e. the I clamp is
                                 the WHOLE command rail expressed in lat-accel units.
  latcontrol_torque.py:610-613   pid.reset() below minSteerSpeed; freeze_integrator on
                                 steer_limited_by_safety | steeringPressed | v<thr | unwind_detected
                                 unwind_detected = (d setpoint/dt < -1.0) and |setpoint| < 0.3   (:331)
  latcontrol_torque.py:292       on release of steeringPressed: i *= 0.8
  latcontrol_vehicle_tunes.py:2636, 393   ki = interp(v, [8,18], [AccordTorqueKi, AccordTorqueKiHigh]),
                                 flat AccordTorqueKi when AccordTorqueKiHigh <= 0.
  starpilot_variables.py:826,838 AccordTorqueKi in [0.05, 1.0] default 0.30;
                                 AccordTorqueKiHigh in [0.0, 6.0] default 2.5.

THE TEST.  Because pid_log.error is logged, the UNCLAMPED, UNFROZEN integrator can be re-synthesised
EXACTLY from the log (one line, the fork's own recursion) and differenced against the logged i.  If
they agree, no clamp and no freeze is costing the integrator anything and the limit is the GAIN.

out: K1-OUT.txt
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS, DT = 100.0, 0.01
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 1.0
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
EPS_INERTIA = 8e-5
KI_BP = [8.0, 18.0]

# flown config from each route's OWN initData (hsurface/surface/params_all.json), plus whether the
# flown commit contains HondaAccordErrorNotch (rev 4+: r74/r75 and the rev5/6.4 routes).
CFG = {
    "00000064--ce6b0b0ebb": dict(g="V282", kp=0.9,  laf=6.0,  ki=0.3,  kih=0.0, notch=False),
    "00000065--b9f78988bd": dict(g="V282", kp=0.9,  laf=6.0,  ki=0.3,  kih=0.0, notch=False),
    "0000006c--2bc842dbac": dict(g="V282", kp=0.9,  laf=6.0,  ki=0.3,  kih=0.0, notch=False),
    "00000071--f2c9d073a3": dict(g="T2",   kp=0.85, laf=14.0, ki=0.3,  kih=0.0, notch=False),
    "00000072--8001fc3048": dict(g="T3",   kp=0.85, laf=14.0, ki=0.6,  kih=0.0, notch=False),
    "00000073--79fd149dd8": dict(g="T3R",  kp=0.85, laf=14.0, ki=0.6,  kih=0.0, notch=False),
    "00000075--6c8687d5bd": dict(g="T4",   kp=0.85, laf=14.0, ki=0.6,  kih=2.5, notch=True),
    "0000006c--68c6e94b17": dict(g="T64",  kp=1.0,  laf=14.0, ki=0.3,  kih=0.0, notch=True),
    "0000006d--05e83bb04f": dict(g="T64",  kp=1.0,  laf=14.0, ki=0.3,  kih=0.0, notch=True),
    "0000006e--6ca3e014fd": dict(g="T64B", kp=1.0,  laf=14.0, ki=0.3,  kih=0.0, notch=True),
    "00000076--d0b7ea7e4d": dict(g="T5",   kp=1.0,  laf=14.0, ki=0.3,  kih=0.0, notch=True),
}
ORDER = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
         "00000076--d0b7ea7e4d", "00000071--f2c9d073a3", "00000072--8001fc3048",
         "00000073--79fd149dd8", "00000075--6c8687d5bd",
         "00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40), (1.80, 3.50)]
NPS = 2048


def lsf_of(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / EPS_INERTIA) / (2.0 * np.pi)


def ki_of(v, c):
    return np.full(np.shape(v), float(c["ki"])) if c["kih"] <= 0 else \
        np.interp(v, KI_BP, [float(c["ki"]), float(c["kih"])])


def notch_resp(f, f0, q=1.0):
    k = np.tan(np.pi * min(float(f0), 0.45 / DT) * DT)
    n = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * n
    b1 = 2.0 * (k * k - 1.0) * n
    a2 = (1.0 - k / q + k * k) * n
    z = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def integrate(err, ki_vec, i0=0.0):
    """The fork's exact recursion, UNFROZEN and UNCLAMPED: i_k = i_{k-1} + ki_k*dt*err_k."""
    return i0 + np.cumsum(ki_vec * DT * err)


def bandavg(f, H, W, a, b):
    s = (f >= a) & (f < b)
    return np.average(H[s], weights=np.maximum(W[s], 1e-300))


def main():
    print("=" * 124)
    print("K1  THE INTEGRATOR, MEASURED.  >=15 m/s, laterally engaged, hands off, contiguous runs >= 30 s.")
    print("=" * 124)

    # ---------- 1. the integrator is reproducible from the logged error, so nothing is hidden ----------
    print("\n1  POSITIVE CONTROL + CLAMP/FREEZE CENSUS.  i re-synthesised from the LOGGED pid error with the")
    print("   fork's own recursion, UNFROZEN and UNCLAMPED, re-anchored at the start of each run.")
    print("   'i err' = rms(i_resynth - i_logged) / rms(i_logged).  A clamp or a freeze shows up HERE.")
    print(f"   {'route':10s} {'grp':5s} {'runs':>4s} {'sec':>6s} {'v med':>6s} {'ki_eff':>7s} "
          f"{'rms i':>8s} {'i err':>7s} {'|i|/LAF p99':>11s} {'clamp%':>7s} {'unwind%':>8s} {'sat%':>6s}")
    ACC = {}
    for rk in ORDER:
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        c = CFG[rk]
        S = V.load(rk)
        m = V.usable(S, 15.0)
        segs = V.runs(m, S["t"], min_s=30.0)
        if not segs:
            del S
            continue
        err = np.nan_to_num(S["err"]) if "err" in S else None
        del err
        D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
        e_log = np.interp(S["t"], D["t_cs"], D["cs_err"])      # same clock, identity map
        iv, pv, fv, ov = (np.nan_to_num(S[k]) for k in ("i", "p", "f", "out"))
        with np.errstate(divide="ignore", invalid="ignore"):
            laf_fr = np.where(np.abs(ov) > 5e-3, -(pv + iv + fv) / ov, np.nan)
        laf = float(np.nanmedian(laf_fr[V.usable(S)]))
        sp = np.nan_to_num(S["setpoint"])
        dsp = np.gradient(sp) * FS
        unwind = (dsp < -1.0) & (np.abs(sp) < 0.3)
        num, den, n_cl, n_tot, n_uw, n_sat, ipk, secs, vmeds, kimeds = 0.0, 0.0, 0, 0, 0, 0, [], 0.0, [], []
        for a, b in segs:
            kv = ki_of(S["v"][a:b], c)
            ih = integrate(e_log[a:b], kv, i0=iv[a])
            num += float(np.sum((ih - iv[a:b]) ** 2))
            den += float(np.sum(iv[a:b] ** 2))
            ctl = pv[a:b] + iv[a:b] + fv[a:b]
            n_cl += int(np.sum(np.abs(ctl) >= laf * 0.999))
            n_uw += int(np.sum(unwind[a:b]))
            n_sat += int(np.sum(S["sat"][a:b]))
            n_tot += b - a
            ipk.append(np.abs(iv[a:b]) / laf)
            secs += (b - a) / FS
            vmeds.append(np.median(S["v"][a:b]))
            kimeds.append(np.median(kv))
        ierr = np.sqrt(num / max(den, 1e-30))
        print(f"   {rk[:8]:10s} {c['g']:5s} {len(segs):4d} {secs:6.0f} {np.median(vmeds):6.1f} "
              f"{np.median(kimeds):7.3f} {np.sqrt(den/n_tot):8.4f} {ierr:7.4f} "
              f"{np.percentile(np.concatenate(ipk), 99):11.4f} {100*n_cl/n_tot:7.3f} "
              f"{100*n_uw/n_tot:8.3f} {100*n_sat/n_tot:6.2f}")
        ACC[rk] = dict(S=None, laf=laf, segs=segs, secs=secs)
        del S, D

    # ---------- 2. the I transfer, measured and predicted ----------
    print("\n2  |C_P| and |C_I|: the P and I transfers from the RAW error E = setpoint - measurement to the")
    print("   logged p and i, H1 = S_Ep/S_EE and S_Ei/S_EE.  p and i are EXACT functions of E, so H1 is the")
    print("   filter itself, not a noisy estimate.  'pred' = the fork arithmetic at that route's flown gains.")
    print(f"   {'route':10s} {'grp':5s} {'ki_eff':>7s} " +
          " ".join(f"{('%.2f-%.2f' % bd):>25s}" for bd in BANDS[:4]))
    print(f"   {'':10s} {'':5s} {'':>7s} " + " ".join(f"{'|C_P| |C_I| I/P  pred':>25s}" for _ in BANDS[:4]))
    RES = {}
    for rk in ORDER:
        if rk not in ACC:
            continue
        c = CFG[rk]
        S = V.load(rk)
        D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
        e_log = np.interp(S["t"], D["t_cs"], D["cs_err"])
        E = np.nan_to_num(S["setpoint"]) - np.nan_to_num(S["la_act"])
        iv, pv, fv = (np.nan_to_num(S[k]) for k in ("i", "p", "f"))
        segs = ACC[rk]["segs"]
        Pee = Pep = Pei = Pff = Pii = Ppp = None
        vs, kis = [], []
        for a, b in segs:
            x = E[a:b]
            for key, y in (("p", pv[a:b]), ("i", iv[a:b])):
                xs_, ys_ = x - x.mean(), y - y.mean()
                f, pxx = signal.welch(xs_, FS, nperseg=NPS, noverlap=NPS // 2)
                _, pxy = signal.csd(xs_, ys_, FS, nperseg=NPS, noverlap=NPS // 2)
                w = b - a
                if key == "p":
                    Pee = pxx * w if Pee is None else Pee + pxx * w
                    Pep = pxy * w if Pep is None else Pep + pxy * w
                else:
                    Pei = pxy * w if Pei is None else Pei + pxy * w
            for key, y in (("f", fv[a:b]), ("i", iv[a:b]), ("p", pv[a:b])):
                _, pyy = signal.welch(y - y.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
                w = b - a
                if key == "f":
                    Pff = pyy * w if Pff is None else Pff + pyy * w
                elif key == "i":
                    Pii = pyy * w if Pii is None else Pii + pyy * w
                else:
                    Ppp = pyy * w if Ppp is None else Ppp + pyy * w
            vs.append(np.median(S["v"][a:b]))
            kis.append(np.median(ki_of(S["v"][a:b], c)))
        CP, CI = Pep / np.maximum(Pee, 1e-30), Pei / np.maximum(Pee, 1e-30)
        vm = float(np.median(vs)); kie = float(np.median(kis))
        lsf = float(lsf_of(vm)); Nf = notch_resp(f, mode_hz(vm)) if c["notch"] else np.ones_like(f, complex)
        z = np.exp(-2j * np.pi * f * DT)
        with np.errstate(divide="ignore", invalid="ignore"):
            CI_pred = kie * DT / (1 - z) * (1 + lsf / c["kp"]) * Nf
        line = f"   {rk[:8]:10s} {c['g']:5s} {kie:7.3f} "
        for (a_, b_) in BANDS[:4]:
            cp = abs(bandavg(f, CP, Pee, a_, b_)); ci = abs(bandavg(f, CI, Pee, a_, b_))
            cpd = abs(bandavg(f, CI_pred, Pee, a_, b_))
            line += f"{cp:6.3f}{ci:6.3f}{ci/max(cp,1e-9):5.2f}{cpd:8.3f} "
        print(line)
        RES[rk] = dict(f=f, CP=CP, CI=CI, W=Pee, Pff=Pff, Pii=Pii, Ppp=Ppp, v=vm, kie=kie,
                       lsf=lsf, laf=ACC[rk]["laf"])
        del S, D
    np.save(HERE / "k1_res.npy", RES, allow_pickle=True)

    # ---------- 3. command budget ----------
    print("\n3  COMMAND BUDGET by band: rms of each term in OUTPUT-TORQUE units (term / LAF).")
    print(f"   {'route':10s} {'grp':5s} " + " ".join(f"{('%.2f-%.2f' % bd):>28s}" for bd in BANDS))
    print(f"   {'':10s} {'':5s} " + " ".join(f"{'rms_p  rms_i  rms_f  i/(p+i)':>28s}" for _ in BANDS))
    for rk in ORDER:
        if rk not in RES:
            continue
        R = RES[rk]
        f, df, laf = R["f"], R["f"][1] - R["f"][0], R["laf"]
        line = f"   {rk[:8]:10s} {CFG[rk]['g']:5s} "
        for (a_, b_) in BANDS:
            s = (f >= a_) & (f < b_)
            rp = np.sqrt(np.sum(R["Ppp"][s]) * df); ri = np.sqrt(np.sum(R["Pii"][s]) * df)
            rf = np.sqrt(np.sum(R["Pff"][s]) * df)
            nrm = np.sqrt(np.sum(R["W"][s]) * df) * 0 + 1.0
            line += f"{rp/laf/nrm:7.4f}{ri/laf/nrm:7.4f}{rf/laf/nrm:7.4f}{ri/max(rp+ri,1e-12):8.2f} "
        print(line)
    print("\n   (rms values are not normalised across routes -- they carry each route's own road roughness;")
    print("    the i/(p+i) column is the within-route share and IS comparable.)")


if __name__ == "__main__":
    main()
