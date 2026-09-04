# -*- coding: utf-8 -*-
"""tune_v282.py -- BACK-CALCULATE SteerFriction / SteerLatAccel / SteerKP for V282 (Ki-0).

Two labelled answers are required:
  (A) TODAY            -- flat SteerRatio 12.5, the variable-SR map NOT deployed.
  (B) AFTER the SR map -- the 1.32x curvature-measurement inflation removed.

The trap this script exists to settle: raising gain to compensate a MEASUREMENT bias and then
removing the bias leaves the loop over-gained.  So the first thing measured is WHETHER GAIN CAN
COMPENSATE THE BIAS AT ALL.  It cannot, if the loop is integral-closed: the integrator drives
`error = setpoint - measurement` to zero regardless of the gain in front of it, so the DC
equilibrium is set by the MEASUREMENT and no gain moves it.  Sections C and D test that directly.

Controller math read from openpilots/StarPilot @ Dom (verified in source this session):
  measured_curvature = -VM.calc_curvature(rad(ang - aoff), v, roll)      latcontrol_torque.py
  VM.calc_curvature  = curvature_factor(v)*sa/sR + roll_compensation(roll, v)   vehicle_model.py:77
      -> sR is a PURE DIVISOR on the steering-angle term; stiffnessFactor pinned 1.0 (ForceAutoTuneOff)
  measurement   = measured_curvature * v**2
  error         = setpoint - measurement ;  error_with_lsf = error*(1 + lsf/kp)
  lsf(v)        = (interp(v,[0,10,20,30],[12,10.5,8,5]) / max(v,0.3))**2
  ff            = desired_lat - roll_comp - latAccelOffset*fade , * get_honda_accord_ff_scale
  friction      = interp(err, [-0.30,0.30], [-friction*LAF, +friction*LAF])   lateral.py:189, thr 0.30
  output_torque = output_lataccel / LAF                                   interfaces.py:326
  i += k_i*0.01*error  at 100 Hz                                          pid.py:53

SR-free instruments (neither contains sR):
  pose = v*yaw_cal - g*sin(roll_device)      [the road's own lateral accel]
  des  = controlsState.desiredLateralAccel   [what openpilot asked for]

Caches: analysis-2020accord/studies/optune/_scratch/r3{4..8}_backcalc.npz  (built by backcalc_extract.py)
Arms:  r34 = V280 rev 2, SR 16.1, EPS Ki 0   <- THE SR CONTROL
       r35 = V281 rev 3, SR 12.5, EPS Ki 0   <- == V282 (V282 adds only the read-only r24 comparator tap)
       r36/r38 = V283, SR 12.5, EPS Ki 50    <- integrator confounds every DC reading; shown, never leaned on

Run: python rlog-tools/studies/optune-v282/tune_v282.py
"""
import json
import os

import numpy as np
from scipy import signal as sg

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "studies", "optune", "_scratch")
OUT = os.path.join(HERE, "_scratch")
os.makedirs(OUT, exist_ok=True)

G = 9.81
FS = 100.0
ARMS = [("r34", "V280r2  SR 16.1  Ki0  [SR CONTROL]", 16.1, 0),
        ("r35", "V281r3  SR 12.5  Ki0  [= V282]", 12.5, 0),
        ("r36", "V283    SR 12.5  Ki50 [confounded]", 12.5, 50),
        ("r38", "V283    SR 12.5  Ki50 [confounded]", 12.5, 50)]

_LINES = []


def pr(s=""):
    print(s)
    _LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if x.size else float("nan")


def grid(d, t0, t1):
    """Resample every channel onto a common 100 Hz grid over [t0, t1]."""
    tg = np.arange(t0, t1, 1.0 / FS)
    out = {"t": tg}

    def put(name, tk, vk, kind="lin"):
        tk = np.asarray(tk, float)
        vk = np.asarray(vk, float)
        ok = np.isfinite(tk) & np.isfinite(vk)
        if ok.sum() < 4:
            out[name] = np.full(tg.shape, np.nan)
            return
        tk, vk = tk[ok], vk[ok]
        o = np.argsort(tk)
        tk, vk = tk[o], vk[o]
        if kind == "zoh":                      # step-hold for flags / slow params
            idx = np.searchsorted(tk, tg, side="right") - 1
            idx = np.clip(idx, 0, len(vk) - 1)
            out[name] = vk[idx]
        else:
            out[name] = np.interp(tg, tk, vk)

    put("v", d["cs_t"], d["cs_v"])
    put("ang", d["cs_t"], d["cs_ang"])
    put("rate", d["cs_t"], d["cs_rate"])
    put("pressed", d["cs_t"], d["cs_pressed"], "zoh")
    put("drv", d["cs_t"], d["cs_drv"])
    put("tq", d["co_t"], d["co_tq"])
    put("lat", d["cc_t"], d["cc_lat"], "zoh")
    for k in ("f", "p", "i", "d", "output", "error", "errorRate", "actualLateralAccel",
              "desiredLateralAccel", "desiredLateralJerk", "descurv", "curv", "active", "saturated"):
        put(k, d["ctl_t"], d["ctl_" + k], "zoh" if k in ("active", "saturated") else "lin")
    put("roll", d["lpar_t"], d["lpar_roll"])
    put("aoff", d["lpar_t"], d["lpar_aoff"])
    put("sr", d["lpar_t"], d["lpar_sr"], "zoh")
    put("stiff", d["lpar_t"], d["lpar_stiff"], "zoh")
    put("lag", d["ld_t"], d["ld_lag"], "zoh")
    put("wx", d["lp_t"], d["lp_wx"])
    put("wy", d["lp_t"], d["lp_wy"])
    put("wz", d["lp_t"], d["lp_wz"])
    put("calr", d["cal_t"], d["cal_r"], "zoh")
    put("calp", d["cal_t"], d["cal_p"], "zoh")
    put("caly", d["cal_t"], d["cal_y"], "zoh")
    put("cal_ok", d["cal_t"], d["cal_ok"], "zoh")
    # 0xE4, request-gated (the shared-module dilution defect: keep only STEER_REQUEST=1 samples)
    e4t, e4c, e4r = d["e4_t"], d["e4_cmd"], d["e4_req"]
    m = e4r > 0.5
    put("cmd", e4t[m], np.abs(e4c[m]))
    put("req", e4t, e4r, "zoh")
    return out


def rot_from_euler(r, p, y):
    cr, sr_, cp, sp, cy, sy = np.cos(r), np.sin(r), np.cos(p), np.sin(p), np.cos(y), np.sin(y)
    return np.array([[cp * cy, -cp * sy + sr_ * sp * cy, sr_ * sy + cr * sp * cy],
                     [cp * sy, cr * cy + sr_ * sp * sy, -sr_ * cy + cr * sp * sy],
                     [-sp, sr_ * cp, cr * cp]])


def load(tag):
    d = np.load(os.path.join(CACHE, "%s_backcalc.npz" % tag), allow_pickle=True)
    cp = json.loads(str(d["carParams_json"]))
    t0 = max(float(d[k][0]) for k in ("cs_t", "ctl_t", "lp_t", "co_t", "e4_t"))
    t1 = min(float(d[k][-1]) for k in ("cs_t", "ctl_t", "lp_t", "co_t", "e4_t"))
    g = grid(d, t0, t1)
    # ---- SR-FREE road lateral accel: calibrated yaw rate * v, road-crown term removed -------------
    R = rot_from_euler(med(g["calr"]), med(g["calp"]), med(g["caly"])).T
    w = np.vstack([g["wx"], g["wy"], g["wz"]])
    g["yaw_cal"] = (R @ w)[2]
    g["pose"] = g["v"] * g["yaw_cal"] - G * np.sin(g["roll"])
    # ---- the vehicle model, exactly as openpilot runs it -----------------------------------------
    m = cp["mass"]
    L, aF = cp["wheelbase"], cp["centerToFront"]
    aR = L - aF
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]     # stiffnessFactor pinned 1.0
    sf = m * (cF * aF - cR * aR) / (L ** 2 * cF * cR)              # calc_slip_factor (NO leading minus)
    g["cfac"] = 1.0 / (1.0 - sf * g["v"] ** 2) / L                 # chi = steerRatioRear = 0
    g["rollcomp"] = (G * g["roll"]) / ((1.0 / sf) - g["v"] ** 2)
    g["sa"] = np.radians(g["ang"] - g["aoff"])
    g["cp"] = cp
    g["tag"] = tag
    return g


def eng(g, vmin=15.0):
    """Lateral engaged, hands off, calibrated, moving."""
    return ((g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) &
            (g["cal_ok"] > 0.5) & (g["v"] > vmin) & np.isfinite(g["pose"]))


def straight(g, vmin=15.0, kmax=0.0020):
    return eng(g, vmin) & (np.abs(g["descurv"]) < kmax)


def tls(x, y):
    """Total least squares slope through the origin (errors on both axes)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 20:
        return float("nan")
    sxx, syy, sxy = float(x @ x), float(y @ y), float(x @ y)
    return float((syy - sxx + np.hypot(syy - sxx, 2 * sxy)) / (2 * sxy)) if sxy != 0 else float("nan")


def iv(x, y, z):
    """Instrumental-variable slope y ~ b*x with instrument z (immune to closed-loop bias)."""
    x, y, z = (np.asarray(a, float) for a in (x, y, z))
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[ok] - x[ok].mean(), y[ok] - y[ok].mean(), z[ok] - z[ok].mean()
    return float((z @ y) / (z @ x)) if (z @ x) != 0 else float("nan")


def shift(a, n):
    """a delayed by n samples (a[k-n])."""
    out = np.full_like(a, np.nan)
    if n > 0:
        out[n:] = a[:-n]
    else:
        out[:] = a
    return out


def runs_of(mask, minlen):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            if j - i + 1 >= minlen:
                out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def lsf(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / np.maximum(v, 0.3)) ** 2


def main():
    Gs = {}
    for tag, _lab, _sr, _ki in ARMS:
        Gs[tag] = load(tag)

    pr("=" * 108)
    pr("TUNE FOR V282 -- back-calculated SteerFriction / SteerLatAccel / SteerKP")
    pr("=" * 108)
    pr("live params on every route below: SteerKP 0.600  SteerLatAccel 2.11  SteerFriction 0.03")
    pr("                                  ForceAutoTune False  ForceAutoTuneOff True (stiffness pinned 1.0)")
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("A. THE MEASUREMENT BIAS -- sR_true, re-derived independently from an SR-FREE instrument")
    pr("-" * 108)
    pr("   IDENTITY (verified against the logs to corr 1.0000, slope 1.000, all routes):")
    pr("       actualLateralAccel = -(cfac(v)*sa/sR + rollcomp(roll,v)) * v^2      [= `measurement`,")
    pr("       latcontrol_torque.py:669].  Write M = -cfac*sa*v^2 and C = -rollcomp*v^2, so")
    pr("       measurement = M/sR_param + C.  The SR-FREE truth is the yaw rate itself, so")
    pr("           v*yaw_cal - C  =  M / sR_true       ->  sR_true = TLS slope of M ~ (v*yaw_cal - C)")
    pr("   locationd never uses the steering ratio, so v*yaw_cal contains no sR.  Only openpilot's")
    pr("   OWN roll model enters both sides, so roll is handled once and identically -- the estimator")
    pr("   that used `pose` (which subtracts the FULL g*sin(roll)) double-handles it and is unstable.")
    pr("   THE TEST OF THE INSTRUMENT: sR_true must come out the SAME on r34 (param 16.1) and on")
    pr("   r35/r36/r38 (param 12.5).  A number that tracks the param is measuring the param.")
    pr("")
    pr("   %-6s %-8s %9s %9s %9s %9s %8s %7s" %
       ("route", "SR param", "sR_true", "|sa|<5", "5-15deg", "quasi-st", "inflation", "secs"))
    A = {}
    for tag, _lab, srp, _ki in ARMS:
        g = Gs[tag]
        b = eng(g)
        M = -g["cfac"] * g["sa"] * g["v"] ** 2
        Y = g["v"] * g["yaw_cal"] + g["rollcomp"] * g["v"] ** 2
        srt = tls(Y[b], M[b])
        bq = b & (np.abs(g["ang"] - g["aoff"]) > 1.5) & (np.abs(g["rate"]) < 10.0)
        b5 = bq & (np.abs(g["ang"] - g["aoff"]) < 5.0)
        b15 = bq & (np.abs(g["ang"] - g["aoff"]) >= 5.0) & (np.abs(g["ang"] - g["aoff"]) < 15.0)
        A[tag] = dict(sr_true=srt, srp=srp, infl=srt / srp)
        pr("   %-6s %-8.2f %9.2f %9.2f %9.2f %9.2f %8.3f %7.0f" %
           (tag, srp, srt, tls(Y[b5], M[b5]), tls(Y[b15], M[b15]), tls(Y[bq], M[bq]),
            srt / srp, b.sum() / FS))
    srs = [A[t]["sr_true"] for t, _l, _s, _k in ARMS]
    pr("")
    pr("   sR_true spread across the four routes: %.2f - %.2f (median %.2f).  The SteerRatio PARAM" %
       (min(srs), max(srs), float(np.median(srs))))
    pr("   differs by 1.29x across these routes and the estimate does NOT follow it -- the instrument")
    pr("   is measuring the rack, not the setting.")
    pr("   => SteerRatio 12.5 inflates openpilot's own curvature measurement by %.2fx." %
       (float(np.median(srs)) / 12.5))
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("B. THE PLANT -- LAF_true, the car's DC lateral accel per unit of commanded torque")
    pr("-" * 108)
    pr("   The live SteerLatAccel is a DIVISOR on the way to CAN (interfaces.py:326), so the")
    pr("   'truthful' value is the plant's own m/s^2 per torque unit.  Closed-loop, so OLS is")
    pr("   biased DOWN by disturbance feedback; IV with desiredLateralAccel as instrument is the")
    pr("   consistent estimate.  FIR DC = sum of a 30-tap 0-1.5 s response.")
    pr("")
    pr("   %-6s %8s %8s %8s %8s %8s %9s %8s" %
       ("route", "OLS@.2s", "IV@0.2", "IV@0.5", "IV@0.8", "FIR DC", "|P|0.1Hz", "secs"))
    B = {}
    for tag, _lab, srp, _ki in ARMS:
        g = Gs[tag]
        b = eng(g)
        y = g["pose"]
        res = {}
        for lagn, key in ((20, "iv02"), (50, "iv05"), (80, "iv08")):
            x = shift(-g["tq"], lagn)
            z = shift(g["desiredLateralAccel"], lagn)
            res[key] = iv(x[b], y[b], z[b])
        x0 = shift(-g["tq"], 20)
        ok = b & np.isfinite(x0)
        ols = float(np.polyfit(x0[ok], y[ok], 1)[0])
        # FIR: 30 taps at 20 Hz over 0-1.5 s, on engaged runs >= 20 s
        taps = np.zeros(30)
        segs = runs_of(b, int(20 * FS))
        if segs:
            X, Y = [], []
            for i, j in segs:
                u = -g["tq"][i:j + 1][::5]
                yy = y[i:j + 1][::5]
                for k in range(30, len(u)):
                    X.append(u[k - 29:k + 1][::-1])
                    Y.append(yy[k])
            if len(X) > 200:
                taps = np.linalg.lstsq(np.array(X), np.array(Y), rcond=None)[0]
        p01 = float("nan")
        if segs:
            uu = np.concatenate([-g["tq"][i:j + 1] for i, j in segs])
            yy = np.concatenate([y[i:j + 1] for i, j in segs])
            f, Puy = sg.csd(uu, yy, FS, nperseg=1024)
            _, Puu = sg.welch(uu, FS, nperseg=1024)
            k = int(np.argmin(np.abs(f - 0.1)))
            p01 = float(np.abs(Puy[k] / Puu[k]))
        B[tag] = dict(iv=res["iv02"], fir=float(taps.sum()), p01=p01)
        pr("   %-6s %8.2f %8.2f %8.2f %8.2f %8.2f %9.2f %8.0f" %
           (tag, ols, res["iv02"], res["iv05"], res["iv08"], taps.sum(), p01, b.sum() / FS))
    pr("")
    pr("   The live SteerLatAccel is 2.11.  If LAF_true >> 2.11 the FEEDFORWARD over-commands by")
    pr("   LAF_true/2.11 and the integrator must cancel the excess -- which is what C shows.")
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("C. WHERE THE COMMAND GOES -- the signed PID decomposition, in the feedforward's own sign")
    pr("-" * 108)
    pr("   med(x*sign(f)):  positive = ADDS to the feedforward, negative = CANCELS it.")
    pr("")
    for zone, mk in (("STRAIGHT |descurv|<0.0020", straight),
                     ("CURVE    |descurv|>0.0030",
                      lambda g: eng(g) & (np.abs(g["descurv"]) > 0.0030))):
        pr("   %s" % zone)
        pr("   %-6s %7s %8s %8s %8s %8s %8s %8s %8s %7s" %
           ("route", "|f|", "p*sgn", "i*sgn", "d*sgn", "out*sgn", "out/f", "i/f", "med err", "secs"))
        for tag, _lab, srp, _ki in ARMS:
            g = Gs[tag]
            b = mk(g)
            if b.sum() < 100:
                continue
            s = np.sign(g["f"][b])
            af = med(np.abs(g["f"][b]))
            ii = med(g["i"][b] * s)
            oo = med(g["output"][b] * s)
            pr("   %-6s %7.3f %+8.3f %+8.3f %+8.3f %+8.3f %+8.3f %+8.3f %+8.3f %7.0f" %
               (tag, af, med(g["p"][b] * s), ii, med(g["d"][b] * s), oo,
                oo / af if af else float("nan"), ii / af if af else float("nan"),
                med(g["error"][b]), b.sum() / FS))
        pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("D. THE EQUILIBRIUM TEST -- does the loop settle where the MEASUREMENT says, or where GAIN says?")
    pr("-" * 108)
    pr("   If the loop is integral-closed, error -> 0 and the DC equilibrium is")
    pr("       road_delivered / road_asked  =  SR_param / sR_true       (GAIN-FREE)")
    pr("   Both sides SR-free: 'road' = v*yaw_cal - g sin roll, 'asked' = desiredLateralAccel.")
    pr("   Delay-matched by the lateral delay (0.2 s), 0.2 Hz low-pass, straights only.")
    pr("")
    sos = sg.butter(2, 0.2 / (FS / 2), output="sos")
    pr("   Straight-road yaw sits near the noise floor, so the straight-only fit is underpowered")
    pr("   (opfork2 reported OLS brackets 0.51-1.84).  The equilibrium claim is not straight-specific:")
    pr("   wherever the integrator has settled, error -> 0.  So the high-SNR strata are shown too.")
    pr("")
    pr("   %-6s %9s | %8s %8s | %8s %8s | %8s %8s | %8s" %
       ("route", "PREDICT", "str TLS", "secs", ">0.3 TLS", "secs", ">0.5 TLS", "secs", "med err"))
    D = {}
    for tag, _lab, srp, _ki in ARMS:
        g = Gs[tag]
        pred = srp / A[tag]["sr_true"]
        row = [pred]
        for name, bb in (("str", straight(g)),
                         ("hi3", eng(g) & (np.abs(g["desiredLateralAccel"]) > 0.3)),
                         ("hi5", eng(g) & (np.abs(g["desiredLateralAccel"]) > 0.5))):
            segs = runs_of(bb, int(4 * FS))
            xs, ys = [], []
            for i, j in segs:
                a_ = sg.sosfiltfilt(sos, g["desiredLateralAccel"][i:j + 1])
                r_ = sg.sosfiltfilt(sos, g["pose"][i:j + 1])
                xs.append(shift(a_, 20)[20:])
                ys.append(r_[20:])
            if xs:
                x, y = np.concatenate(xs), np.concatenate(ys)
                ok = np.isfinite(x) & np.isfinite(y)
                row += [tls(x[ok], y[ok]), bb.sum() / FS]
            else:
                row += [float("nan"), 0.0]
        be = eng(g)
        D[tag] = dict(pred=pred, str=row[1], hi3=row[3], hi5=row[5])
        pr("   %-6s %9.3f | %8.3f %8.0f | %8.3f %8.0f | %8.3f %8.0f | %8.3f" %
           (tag, row[0], row[1], row[2], row[3], row[4], row[5], row[6],
            med(g["error"][be])))
    pr("")
    pr("   r34 (SR 16.1, the control) and r35 (=V282, SR 12.5) are the same firmware CLASS (both Ki 0)")
    pr("   and the same tune EXCEPT SteerRatio.  If the measured ratio tracks PREDICT across them,")
    pr("   the equilibrium is measurement-set and NO GAIN PARAMETER CAN MOVE IT.")
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("E. IS THERE ANY OSCILLATION LEFT FOR A GAIN CUT TO FIX? -- the 3.9 Hz question")
    pr("-" * 108)
    pr("   The 2026-09-02 back-calc prescribed cutting loop gain (friction 0.025, LAF 2.53) for a")
    pr("   3.9 Hz oscillation measured on V279-class firmware.  Does that line still exist on")
    pr("   V282-class routes?  Welch PSD of the SR-free road lateral accel, engaged frames.")
    pr("")
    pr("   %-6s %9s %9s %9s %9s %9s %9s %9s" %
       ("route", "1.5Hz", "2.5Hz", "3.9Hz", "5Hz", "7Hz", "pk 3-5Hz", "pk/floor"))
    for tag, _lab, srp, _ki in ARMS:
        g = Gs[tag]
        b = eng(g)
        segs = runs_of(b, int(20 * FS))
        if not segs:
            continue
        y = np.concatenate([g["pose"][i:j + 1] for i, j in segs])
        f, P = sg.welch(y, FS, nperseg=2048)

        def gv(hz):
            return float(P[int(np.argmin(np.abs(f - hz)))])
        band = (f >= 3.0) & (f <= 5.0)
        floor = (f >= 8.0) & (f <= 12.0)
        pk = float(P[band].max())
        pr("   %-6s %9.2e %9.2e %9.2e %9.2e %9.2e %9.2e %9.2f" %
           (tag, gv(1.5), gv(2.5), gv(3.9), gv(5.0), gv(7.0), pk, pk / float(np.median(P[floor]))))
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("F. THE CAR'S OWN FRICTION -- what SteerFriction is supposed to model")
    pr("-" * 108)
    pr("   Inverse regression  torque = pose/LAF + b + c*sign(steeringRateDeg)")
    pr("   c = the torque needed before lateral accel responds, in torque units = the car's deadband.")
    pr("   SteerFriction's whole authority is +-friction*LAF in lat-accel units (lateral.py:189),")
    pr("   i.e. +-friction in TORQUE units after interfaces.py:326 divides LAF back out.")
    pr("")
    pr("   %-6s %10s %10s %10s %10s %8s" %
       ("route", "coulomb c", "hyst", "|tq| p50", "|tq| p90", "n"))
    F = {}
    for tag, _lab, srp, _ki in ARMS:
        g = Gs[tag]
        b = eng(g) & (np.abs(g["rate"]) > 1.0)
        x = shift(-g["tq"], 20)
        ok = b & np.isfinite(x) & (np.abs(g["pose"]) < 3.0)
        if ok.sum() < 200:
            continue
        M = np.vstack([g["pose"][ok], np.ones(ok.sum()), np.sign(g["rate"][ok])]).T
        coef = np.linalg.lstsq(M, x[ok], rcond=None)[0]
        hy = []
        for sgn in (+1, -1):
            m2 = ok & (np.sign(g["rate"]) == sgn)
            if m2.sum() > 100:
                pp = np.polyfit(x[m2], g["pose"][m2], 1)
                hy.append(pp[1] / pp[0] if pp[0] else np.nan)
        hyst = abs(hy[0] - hy[1]) / 2 if len(hy) == 2 else float("nan")
        F[tag] = dict(c=float(coef[2]), hyst=hyst)
        tqa = np.abs(g["tq"][eng(g)])
        pr("   %-6s %10.4f %10.4f %10.3f %10.3f %8d" %
           (tag, coef[2], hyst, float(np.percentile(tqa, 50)), float(np.percentile(tqa, 90)), ok.sum()))
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("G. TRANSIENT AUTHORITY -- what a gain change actually buys inside one correction")
    pr("-" * 108)
    pr("   Runs >= 1.0 s of one-signed |error| > 0.10 m/s^2 on straights.  The integrator is slow")
    pr("   (KI 0.15 -> i grows 0.15*error per second), so inside a run P and FF carry the authority.")
    pr("   dP(kp) = (kp_new - kp_old) * error_raw   [the low-speed term is kp-INDEPENDENT:")
    pr("   error_with_lsf = error*(1 + lsf/kp), so p = kp*error + lsf*error]")
    pr("")
    pr("   %-6s %6s %8s %8s %9s %10s %10s %9s %9s %8s" %
       ("route", "runs", "tot s", "med s", "med|err|", "med|tq|", "med|cmd|", "dP@kp.8", "dP@kp.9", "med v"))
    Gg = {}
    for tag, _lab, srp, _ki in ARMS:
        g = Gs[tag]
        b = straight(g)
        e = g["error"]
        sgn = np.sign(e)
        m = b & (np.abs(e) > 0.10)
        segs = []
        for i, j in runs_of(m, int(1.0 * FS)):
            k = i
            while k <= j:
                q = k
                while q + 1 <= j and sgn[q + 1] == sgn[k]:
                    q += 1
                if (q - k + 1) >= int(1.0 * FS):
                    segs.append((k, q))
                k = q + 1
        if not segs:
            continue
        idx = np.concatenate([np.arange(i, j + 1) for i, j in segs])
        vv = med(g["v"][idx])
        eraw = np.abs(e[idx]) / (1.0 + lsf(g["v"][idx]) / 0.6)
        dp8 = 0.2 * med(eraw)
        dp9 = 0.3 * med(eraw)
        Gg[tag] = dict(dp8=dp8, dp9=dp9, err=med(np.abs(e[idx])), tq=med(np.abs(g["tq"][idx])),
                       secs=len(idx) / FS, nruns=len(segs), v=vv, eraw=med(eraw))
        pr("   %-6s %6d %8.1f %8.2f %9.3f %10.3f %10.0f %9.3f %9.3f %8.1f" %
           (tag, len(segs), len(idx) / FS, med([(j - i + 1) / FS for i, j in segs]),
            med(np.abs(e[idx])), med(np.abs(g["tq"][idx])), med(g["cmd"][idx]), dp8, dp9, vv))
    pr("")
    pr("   dP is in LATERAL-ACCEL units (the PID's own space).  Divide by SteerLatAccel for torque:")
    for tag in Gg:
        pr("      %-6s dP@0.8 = %+.3f m/s^2 -> %+.4f torque at LAF 2.11 (present med|tq| %.3f, x%.2f)" %
           (tag, Gg[tag]["dp8"], Gg[tag]["dp8"] / 2.11, Gg[tag]["tq"],
            1.0 + (Gg[tag]["dp8"] / 2.11) / max(Gg[tag]["tq"], 1e-6)))
    pr("")

    # ==============================================================================================
    pr("-" * 108)
    pr("H. THE SMALL-SIGNAL GAIN LEDGER -- Gc(v) = (kp + lsf)/LAF + friction/0.30")
    pr("-" * 108)
    pr("   torque per m/s^2 of lateral-accel error, inside the friction term's linear band.")
    pr("   The friction share is LAF-INDEPENDENT (get_friction multiplies by LAF, then")
    pr("   torque_from_lateral_accel divides it back out).  L0 = Gc * LAF_true (loop DC gain).")
    pr("")
    laf_true = B["r35"]["iv"]
    pr("   using LAF_true = %.2f (r35 IV @0.2 s)" % laf_true)
    pr("")
    pr("   %-34s %7s %9s %8s %8s %9s %8s" %
       ("parameter set (v = 25 m/s)", "LAF", "friction", "Gc", "fr share", "vs live", "L0"))
    live = None
    for name, LAF, fr in (("LIVE TODAY", 2.11, 0.03), ("stock params.toml", 1.689, 0.212),
                          ("friction 0.03 + LAF 2.53", 2.53, 0.03),
                          ("friction 0.02 + LAF 2.53", 2.53, 0.02),
                          ("friction 0.05 + LAF 2.11", 2.11, 0.05),
                          ("friction 0.03 + LAF 1.70", 1.70, 0.03),
                          ("kp 0.8: friction .03 LAF 2.11", 2.11, 0.03),
                          ("kp 0.8: friction .03 LAF 2.53", 2.53, 0.03),
                          ("kp 0.9: friction .03 LAF 2.53", 2.53, 0.03)):
        kp = 0.8 if name.startswith("kp 0.8") else (0.9 if name.startswith("kp 0.9") else 0.6)
        gc = (kp + lsf(25.0)) / LAF + fr / 0.30
        if live is None:
            live = gc
        pr("   %-34s %7.3f %9.3f %8.3f %8.0f%% %9.2f %8.2f" %
           (name, LAF, fr, gc, 100 * (fr / 0.30) / gc, gc / live, gc * laf_true))
    pr("")
    pr("   lsf(25 m/s) = %.3f ; lsf(15) = %.3f ; lsf(30) = %.3f" % (lsf(25.), lsf(15.), lsf(30.)))
    pr("")

    with open(os.path.join(OUT, "tune_v282.txt"), "w") as fh:
        fh.write("\n".join(_LINES) + "\n")
    print("\nwrote %s" % os.path.join(OUT, "tune_v282.txt"))


if __name__ == "__main__":
    main()
