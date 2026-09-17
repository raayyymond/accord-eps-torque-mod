"""s3_accel: large-angle / high-lateral-accel TURN events, V282 (rate servo) vs V293 torque mode.

Own module (does not edit v282cmp.py). Why a separate turn detector: V.accel_events keys on |model lat accel| >= 1.5 m/s^2
at v>=5, which finds 0-27 events per route; large steering angles live at 2.5-8 m/s where lateral accel is small but
CURVATURE is large. So events here key on the model's desired curvature expressed as an equivalent steering-wheel angle.

References (identical across groups, so fork-version differences in steerRatio/LAF/la_act cannot leak in):
  ad  = desired steering-wheel angle equivalent of the model curvature, fixed opendbc Accord bicycle model, sR 16.33, no roll.
  aa  = measured steering angle sa - liveParameters angleOffset                  (the wheel)
  ap  = livePose yaw-rate curvature (la_pose / v^2) mapped through the SAME model  (the car; independent of the steering sensor)
NOTE (EVIDENCE): carState.yawRate is identically 0 on every route -> V's la_yaw is unusable; la_pose is used instead.
"""
import sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

# ---- opendbc Accord bicycle model (opendbc_repo honda/values.py CarSpecs + car/__init__.py scaling) ----
M = 3279 * 0.45359237 + 136.0; WB = 2.83; AF = 0.39 * WB; AR = WB - AF; TSF = 0.8467
_M0, _WB0 = 1326. + 136., 2.70; _AF0 = _WB0 * 0.4; _AR0 = _WB0 - _AF0
CF = 192150 * TSF * M / _M0 * (AR / WB) / (_AR0 / _WB0)
CR = 202500 * TSF * M / _M0 * (AF / WB) / (_AF0 / _WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR_FIX = 16.33


def curv_to_angle(k, v):
    """deg of steering wheel; sign = angle sign (opendbc: curvature = -curvature_factor*angle/sR)."""
    return -np.degrees(k * SR_FIX * WB * (1.0 - SF * v ** 2))


HF_SOS = signal.butter(4, [2.0, 10.0], btype="band", fs=V.FS, output="sos")


def prep(rk):
    S = V.load(rk)
    v = np.nan_to_num(S["v"]); vv = np.maximum(v, 0.5)
    k_m = np.nan_to_num(S["model"]) / vv ** 2
    ad = curv_to_angle(k_m, v)
    aa = np.nan_to_num(S["sa"]) - np.nan_to_num(S["aoff"])
    k_p = np.nan_to_num(S["la_pose"]) / vv ** 2
    ap = curv_to_angle(k_p, v)
    ap = np.where(v >= 2.5, ap, np.nan)
    sr = np.nan_to_num(S["sr"])
    hf = signal.sosfiltfilt(HF_SOS, sr)
    R = dict(rk=rk, group=S["meta"]["group"], t=S["t"], v=v, ad=ad, aa=aa, ap=ap, sr=sr, hf=hf,
             out=np.nan_to_num(S["out"]), p=np.nan_to_num(S["p"]), i=np.nan_to_num(S["i"]), f=np.nan_to_num(S["f"]),
             active=S["active"], pressed=S["pressed"], d=float(np.nanmedian(S["lat_delay"])),
             model=np.nan_to_num(S["model"]), storque=np.nan_to_num(S["storque"]))
    del S
    return R


def find_turns(R, peak_min=25.0, vmin=2.5, vmax=15.0, lim_s=8.0, ret_s=3.0, pad=1.0):
    ad = R["ad"]; v = R["v"]; t = R["t"]; n = len(ad)
    adl = V.lowpass(ad, 1.0)
    a = np.abs(adl)
    pk, _ = signal.find_peaks(a, height=peak_min, prominence=0.6 * peak_min, distance=int(3 * V.FS))
    ok_mask = R["active"] & ~R["pressed"]
    evs = []
    rej = dict(candidates=0, edge=0, overlap=0, gap=0, pressed=0, disengaged=0, speed=0)
    last_end = -1
    for k in pk:
        P = a[k]; s = float(np.sign(adl[k]))
        if not (vmin <= v[k] < vmax):
            continue
        rej["candidates"] += 1
        thr_lo, thr_hi = max(0.1 * P, 3.0), 0.8 * P
        L = int(lim_s * V.FS)
        i = k
        while i > max(0, k - L) and s * adl[i] > thr_lo:
            i -= 1
        j = k
        while j < min(n - 1, k + L) and s * adl[j] > thr_lo:
            j += 1
        if s * adl[i] > thr_lo or s * adl[j] > thr_lo:
            rej["edge"] += 1; continue
        h0 = i
        while h0 < k and s * adl[h0] < thr_hi:
            h0 += 1
        h1 = j
        while h1 > k and s * adl[h1] < thr_hi:
            h1 -= 1
        w0, w1 = i - int(pad * V.FS), j + int((ret_s + pad) * V.FS)
        if w0 < 0 or w1 >= n:
            rej["edge"] += 1; continue
        if w0 <= last_end:
            rej["overlap"] += 1; continue
        if np.any(np.diff(t[w0:w1]) > 4.0 / V.FS):
            rej["gap"] += 1; continue
        if not R["active"][w0:w1].all():
            rej["disengaged"] += 1; continue
        vm = float(np.median(v[i:j]))
        if not (vmin <= vm < vmax) or v[i:j].min() < 1.0:
            rej["speed"] += 1; continue
        evs.append(dict(k=int(k), i=int(i), h0=int(h0), h1=int(h1), j=int(j), w0=w0, w1=w1, P=float(P), s=s, v=vm,
                        t=float(t[k]), press_frac=float(R["pressed"][i:j + int(ret_s * V.FS)].mean()), la_peak=float(np.max(np.abs(R["model"][i:j]))), hold_s=float((h1 - h0) / V.FS)))
        last_end = w1
    return evs, rej


def shift(x, d_samp):
    """x(t + d): achieved advanced by the route's learned lateral delay (desiredCurvature already leads by d)."""
    y = np.full(len(x), np.nan)
    if d_samp > 0:
        y[:-d_samp] = x[d_samp:]
    else:
        y[:] = x
    return y


def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 10 or np.std(x[m]) < 1e-6:
        return np.nan
    return float(np.polyfit(x[m], y[m], 1)[0])


def metrics(R, e, lag_s=None):
    d = R["d"] if lag_s is None else lag_s
    ds = int(round(d * V.FS))
    s, P = e["s"], e["P"]
    ad = s * R["ad"]
    out = dict(rk=R["rk"], group=R["group"], v=e["v"], P=P, press_frac=e["press_frac"], la_peak=e["la_peak"], hold_s=e["hold_s"], t=e["t"], lag=d)
    ph = dict(build=(e["i"], e["h0"]), hold=(e["h0"], e["h1"]), unwind=(e["h1"], e["j"]))
    for key in ("aa", "ap"):
        ach = s * shift(np.where(R["pressed"], np.nan, R[key]), ds)
        err = ach - ad
        for name, (a0, a1) in ph.items():
            if a1 - a0 < 5:
                out[f"{key}_{name}_err"] = np.nan; out[f"{key}_{name}_errdeg"] = np.nan; out[f"{key}_{name}_gain"] = np.nan
                continue
            out[f"{key}_{name}_err"] = float(np.nanmean(err[a0:a1]) / P)        # + = more turn than asked
            out[f"{key}_{name}_errdeg"] = float(np.nanmean(err[a0:a1]))
            out[f"{key}_{name}_gain"] = slope(ad[a0:a1], ach[a0:a1]) if name != "hold" else np.nan
        r0, r1 = e["j"], e["j"] + int(3 * V.FS)
        seg = ach[r0:r1]
        if np.isfinite(seg).any():
            ovd = np.nanmax(-ad[r0:r1])
            out[f"{key}_ret_overshoot_deg"] = float(max(0.0, np.nanmax(-seg)) - max(0.0, ovd))
            out[f"{key}_ret_err"] = float(np.nanmean(err[r0:r1]) / P)
        else:
            out[f"{key}_ret_overshoot_deg"] = np.nan; out[f"{key}_ret_err"] = np.nan
        out[f"{key}_ret_overshoot"] = out[f"{key}_ret_overshoot_deg"] / P
        tol = max(0.1 * P, 3.0)
        ee = err[e["h1"]:r1]
        bad = ~(np.abs(ee) < tol)
        idx = np.where(bad)[0]
        out[f"{key}_settle_s"] = float((idx[-1] + 1) / V.FS) if len(idx) else 0.0
        out[f"{key}_settle_trunc"] = bool(len(idx) and idx[-1] >= len(ee) - 50)
        out[f"{key}_peak_ratio"] = float(np.nanmax(ach[e["i"]:e["j"]]) / P) if np.isfinite(ach[e["i"]:e["j"]]).any() else np.nan
    adr = V.deriv(V.lowpass(R["ad"], 2.0))
    srl_all = V.lowpass(R["sr"], 10.0)
    for name, (a0, a1) in ph.items():
        if a1 - a0 < 20:
            out[f"hf_{name}"] = np.nan; out[f"hfn_{name}"] = np.nan; out[f"dwell_{name}"] = np.nan; continue
        hf = float(np.sqrt(np.mean(R["hf"][a0:a1] ** 2)))
        out[f"hf_{name}"] = hf
        out[f"hfn_{name}"] = hf / max(float(np.mean(np.abs(adr[a0:a1]))), 5.0)
        srl = srl_all[a0:a1] * s
        dem = np.abs(adr[a0:a1]) > 10.0
        if dem.sum() > 10:
            med = np.median(np.abs(srl[dem]))
            out[f"dwell_{name}"] = float(np.mean(np.abs(srl[dem]) < 0.25 * med))
        else:
            out[f"dwell_{name}"] = np.nan
    for name, (a0, a1) in dict(ph, ret=(e["j"], e["j"] + int(3 * V.FS))).items():
        if a1 - a0 >= 5:
            out[f"drv_{name}"] = float(np.mean(s * R["storque"][a0:a1]))     # + = driver adds turn, - = pushes toward centre
            out[f"press_{name}"] = float(R["pressed"][a0:a1].mean())
    h0, h1 = e["h0"], e["h1"]
    if h1 - h0 >= 5:
        tot = np.mean(np.abs(R["out"][h0:h1]))
        for k_ in "pif":
            out[f"hold_share_{k_}"] = float(np.mean(s * -R[k_][h0:h1]) / max(np.mean(np.abs(R["p"][h0:h1] + R["i"][h0:h1] + R["f"][h0:h1])), 1e-9))
        out["hold_out"] = float(np.mean(s * -R["out"][h0:h1]))
    return out


def strata(m):
    vb = 0 if m["v"] < 5 else (1 if m["v"] < 8 else 2)
    pb = 0 if m["P"] < 60 else (1 if m["P"] < 150 else 2)
    return vb, pb


VB = ["2.5-5", "5-8", "8-15"]
PB = ["25-60", "60-150", "150+"]
