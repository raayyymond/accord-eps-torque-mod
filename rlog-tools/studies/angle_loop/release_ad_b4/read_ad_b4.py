# -*- coding: utf-8 -*-
r"""read_ad_b4.py -- grinding hunt (C1/C2/C3/V1/V2) + max-angle bounds on routes ad..b4 (accord-PTM), refs 9c/9d/79.

    python rlog-tools/studies/angle_loop/release_ad_b4/read_ad_b4.py            # all routes, < 10 s per route cached
    python rlog-tools/studies/angle_loop/release_ad_b4/read_ad_b4.py --prep     # (re)build the compact caches only

ANALYSIS ONLY.  Reads the drive-read caches (angle_loop_drive_read.load_route + the r79_extract_fork fork cache, both
built once per route by angle_loop_drive_read.py).  Writes only a compact npz per route under
analysis-2020accord/_scratch/cache/release_ad_b4/ and the JSON/text under ./out.  Sends nothing, flashes nothing.

Sign/unit conventions (EVIDENCE, angle_loop_drive_read.py docstring): theta = 0x14A deg; theta_sp = -raw(0xE4)/10;
w18 = -0x18F rate/8 deg/s (sign of d theta/dt); bar = 0x18F torque sensor raw x 1.024 (wire units).  The bar's sign
relative to theta is MEASURED here (disengaged hands-on turning: sign of median bar*w18), not assumed.
"""
from __future__ import annotations

import contextlib
import glob
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T0 = time.time()
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
HERE = Path(__file__).resolve().parent
AL = HERE.parent
KIT = HERE.parents[3]
for q in (AL, KIT / "rlog-tools" / "studies" / "grind", KIT / "analysis-2020accord" / "studies" / "v280"):
    if str(q) not in sys.path:
        sys.path.insert(0, str(q))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "release_ad_b4"
V280 = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
OUT = HERE / "out"
FS = 100.0
DONGLE = "75604b0a432fdc89"
NEW = ["000000ad--5909e7772a", "000000ae--74557c6b94", "000000af--a4e305dfc5", "000000b0--26515d54d1",
       "000000b1--9038570540", "000000b2--b41c6320f8", "000000b3--7449208c37", "000000b4--008b967c94"]
REFS = {"r9c_7f2f4d_al": "0000009c--7f2f4d267c", "r9d_371ec9_al": "0000009d--371ec93849",
        "r79_a1f5d2_al": "00000079--a1f5d2a272"}
HANDS_ON = 600.0          # wire; lat-record §2.3 episode gate
PRESSED = 1200.0          # wire = the 1229 freeze = steeringPressed (lat-record §2.3)
RATE_MIN = 30.0           # deg/s
BANDS = dict(V2=(5.0, 9.0), C3=(15.0, 25.0), V1=(35.0, 50.0), C2=(8.0, 25.0))
CLIP_BP = [3.1, 8.0, 10.0, 11.75, 17.5, 26.9]
CLIP_V = [17.0, 15.5, 19.5, 17.0, 8.5, 4.5]
VBANDS = [("0-3", 0, 3), ("3-6", 3, 6), ("6-10", 6, 10), ("10-15", 10, 15), ("15-22", 15, 22), (">22", 22, 99)]


def tag_of(prefix):
    ctr = prefix.split("--")[0].lstrip("0") or "0"
    return "r%s_%s_al" % (ctr, prefix.split("--")[1][:6])


# ======================================================================================================================
# PREP: one compact npz per route from the drive-read caches (built once)
# ======================================================================================================================
def prep(tag, prefix, force=False):
    out = CACHE / (tag + ".npz")
    if out.exists() and not force:
        return out
    with contextlib.redirect_stdout(io.StringIO()):
        import angle_loop_drive_read as DR
    W = DR.load_route(tag if (V280 / (tag + ".npz")).exists() else DONGLE + "_" + prefix)
    fk = V280 / (tag + "_fork.npz")
    if not fk.exists() and tag.startswith("r79"):
        fk = V280 / "r79_fork.npz"
    F = np.load(fk, allow_pickle=False)
    m = W["meta"]
    meta = dict(tag=tag, prefix=prefix, carfw=m.get("carfw"), git=m.get("git"),
                params={k: (m.get("params") or {}).get(k) for k in ("GitCommit", "GitBranch", "SteerRatio",
                                                                    "ForceTorqueController", "AlwaysOnLateral")},
                fork_meta={k: json.loads(str(F["meta_json"])).get(k) for k in ("fork_commit_full", "route")},
                carparams=json.loads(str(F["carparams_json"])))
    keys_f = ["t_co", "co_ang", "t_cc", "cc_ang", "cc_latActive", "t_cs", "cs_ang", "cs_vegoraw", "cs_vego", "cs_press",
              "t_ctl", "ang_des", "ang_meas", "ang_sat", "ang_active", "ctl_dcurv", "t_sdalert", "sdalert_text"]
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez(out, t=W["t"], ang=W["ang"], raw=W["raw"], req=W["req"], sca=W["sca"], bar=W["bar"], wire=W["wire"],
             vego=W["vego"], have=W["have"], pressed=W["pressed"],
             **{"F_" + k: F[k] for k in keys_f if k in F.files}, meta=np.array(json.dumps(meta)))
    return out


# ======================================================================================================================
# helpers
# ======================================================================================================================
def runs(mask, minlen=1):
    d = np.diff(np.r_[0, np.asarray(mask, int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


_SOS_HP = signal.butter(4, 4.0, "highpass", fs=FS, output="sos")


def band_rms(x, lo, hi):
    f, P = signal.periodogram(x, fs=FS, window="hann")
    return float(np.sqrt(P[(f >= lo) & (f < hi)].sum()))


def emax(v):
    return np.interp(v, CLIP_BP, CLIP_V)


# V300 lane P chain (ceiling.py, integer mirror; constants read LE from the V300 image there).  G table lazy-loaded.
_IMG = {}


def lane_P_T(err_deg, v):
    """|P-only lane torque| (T) for an error and speed, the V300 integer chain without I and without the hand fade
    (an UPPER bound under a hand: BELIEF -- the fadeA2/fadeB2 hand fade is not modelled)."""
    if not _IMG:
        import struct
        img = open(glob.glob(os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/_v300_*plain_image.bin")[0],
                   "rb").read()
        u16 = lambda a: struct.unpack_from("<H", img, a)[0]  # noqa: E731
        s16 = lambda a: struct.unpack_from("<h", img, a)[0]  # noqa: E731
        _IMG.update(KP=u16(0xE5384), PCL=u16(0xC61BC), SCL=u16(0xC61BE), GAIN=u16(0xC6CD0), RAIL=u16(0xC61B4),
                    TAB=[(u16(0xC4CDA + 6 * i), u16(0xC4CDA + 6 * i + 2), s16(0xC4CDA + 6 * i + 4)) for i in range(7)])
    K = _IMG
    out = np.zeros(len(err_deg))
    for i, (e, vv) in enumerate(zip(err_deg, v)):
        vw = int(round(vv * 1382 / 6.0))
        tab = K["TAB"]
        if vw <= tab[0][0]:
            g = tab[0][1]
        else:
            k = 0
            while k + 1 < len(tab) and vw > tab[k + 1][0]:
                k += 1
            x, y, s = tab[k]
            g = ((vw - x) * s >> 12) + y
        E = 16 * int(round(abs(e) * 10))
        P = min(K["PCL"], ((E * g) >> 8) * K["KP"] >> 8)
        S = min(K["SCL"], (P * 254) >> 8)
        out[i] = min(K["RAIL"], K["GAIN"] * S * 0.990 / 32768)
    return out


RAIL_T = 2461.0


# ======================================================================================================================
# per-route analysis
# ======================================================================================================================
def load(tag):
    Z = np.load(CACHE / (tag + ".npz"), allow_pickle=False)
    D = {k: Z[k] for k in Z.files if k != "meta"}
    D["meta"] = json.loads(str(Z["meta"]))
    D["eng"] = (D["req"] > 0.5) & (D["sca"] > 0.5) & (D["have"] > 0.5)
    D["th"] = D["ang"]
    D["sp"] = -D["raw"] / 10.0
    D["w18"] = -D["wire"] / 8.0
    return D


def fw_of(meta):
    for f in meta.get("carfw") or []:
        s = str(f.get("fw", ""))
        if "39990-TVA" in s:
            return s.strip("\x00 ")
    return "?"


def bar_sign(D):
    """sign k such that k*bar has the sign of the driver's push direction in theta, measured where the driver alone moves
    the wheel: disengaged, |bar| > 600, |w18| > 30."""
    m = ~D["eng"] & (np.abs(D["bar"]) > HANDS_ON) & (np.abs(D["w18"]) > RATE_MIN)
    if m.sum() < 50:
        return 1.0, int(m.sum()), np.nan
    pr = np.sign(D["bar"][m] * D["w18"][m])
    return float(np.sign(np.median(pr)) or 1.0), int(m.sum()), float(np.mean(pr > 0))


def windows(D):
    """1-s windows (100 frames) on the wire grid -> rows of per-window features."""
    n = len(D["t"]) // 100
    bar_hp = signal.sosfiltfilt(_SOS_HP, np.nan_to_num(D["bar"]))
    w_hp = signal.sosfiltfilt(_SOS_HP, np.nan_to_num(D["w18"]))
    rows = []
    k, _, _ = bar_sign(D)
    for i in range(n):
        s = slice(i * 100, (i + 1) * 100)
        ef = D["eng"][s].mean()
        if not (ef > 0.95 or ef < 0.05):
            continue
        v = float(np.median(D["vego"][s]))
        if v >= 10:
            continue
        hb = float(np.median(np.abs(D["bar"][s])))
        wr = float(np.median(np.abs(D["w18"][s])))
        r = dict(i=i, t=float(D["t"][s][0] - D["t"][0]), eng=bool(ef > 0.95), v=v, bar=hb, rate=wr,
                 ang=float(np.median(D["th"][s])), angmax=float(np.max(np.abs(D["th"][s]))))
        for nm, (lo, hi) in BANDS.items():
            r["bar_" + nm] = band_rms(bar_hp[s], lo, hi)
            r["w_" + nm] = band_rms(w_hp[s], lo, hi)
        if r["eng"]:
            err = D["sp"][s] - D["th"][s]
            push = np.sign(k * D["bar"][s])
            opp = (np.sign(err) == -push) & (np.abs(err) > 1.0)
            cb = np.abs(err) >= emax(D["vego"][s]) - 0.15
            r["opp"] = float(opp.mean())
            r["opp_clip"] = float((opp & cb).mean())
            r["clip"] = float(cb.mean())
            r["err_med"] = float(np.median(np.abs(err)))
        rows.append(r)
    return rows


def vbin(v):
    return 0 if v < 3 else (1 if v < 6 else 2)


def rbin(r):
    return 0 if r < 60 else (1 if r < 120 else 2)


def compare(rows_e, rows_d, key, vmax):
    """engaged/disengaged ratio of medians per (speed, rate) bin, pooled as the engaged-count-weighted geometric mean
    over bins with >= 3 windows on each side.  -> (ratio, n_eng, n_dis, per-bin list)"""
    pb, wsum, lsum = [], 0, 0.0
    ne = nd = 0
    for vb in range(3):
        for rb in range(3):
            E = [r[key] for r in rows_e if vbin(r["v"]) == vb and rbin(r["rate"]) == rb and r["v"] < vmax]
            Dd = [r[key] for r in rows_d if vbin(r["v"]) == vb and rbin(r["rate"]) == rb and r["v"] < vmax]
            if len(E) >= 3 and len(Dd) >= 3:
                rt = np.median(E) / max(np.median(Dd), 1e-9)
                pb.append((vb, rb, len(E), len(Dd), float(rt)))
                wsum += len(E)
                lsum += len(E) * math.log(max(rt, 1e-9))
                ne += len(E)
                nd += len(Dd)
    return (math.exp(lsum / wsum) if wsum else float("nan")), ne, nd, pb


def handson_sets(rows, vmax):
    sel = lambda r: r["bar"] > HANDS_ON and r["rate"] > RATE_MIN and r["v"] < vmax  # noqa: E731
    return [r for r in rows if r["eng"] and sel(r)], [r for r in rows if not r["eng"] and sel(r)]


def c1_frames(D, vmax):
    """C1 on frames: engaged, |bar| > 600, v < vmax.  Fraction opposing (setpoint error against the hand) and at the
    clip; the P-only lane torque those errors demand (V300 integer chain, upper bound: no hand fade)."""
    k, nk, agree = bar_sign(D)
    m = D["eng"] & (np.abs(D["bar"]) > HANDS_ON) & (D["vego"] < vmax)
    if m.sum() == 0:
        return dict(n=0, k=k, k_n=nk, k_agree=agree)
    err = (D["sp"] - D["th"])[m]
    v = D["vego"][m]
    push = np.sign(k * D["bar"][m])
    opp = (np.sign(err) == -push) & (np.abs(err) > 1.0)
    aid = (np.sign(err) == push) & (np.abs(err) > 1.0)
    cb = np.abs(err) >= emax(v) - 0.15
    TP = lane_P_T(err[opp], v[opp]) if opp.any() else np.zeros(0)
    pressed = np.abs(D["bar"][m]) > PRESSED
    return dict(n=int(m.sum()), secs=float(m.sum() / FS), k=k, k_n=nk, k_agree=agree,
                opp=float(opp.mean()), aid=float(aid.mean()), opp_clip=float((opp & cb).mean()),
                clip=float(cb.mean()), err_p50=float(np.median(np.abs(err))),
                err_opp_p50=float(np.median(np.abs(err[opp]))) if opp.any() else np.nan,
                TP_opp_p50=float(np.median(TP)) if TP.size else np.nan,
                TP_opp_p90=float(np.percentile(TP, 90)) if TP.size else np.nan,
                TP_opp_rail_p50=float(np.median(TP) / RAIL_T) if TP.size else np.nan,
                opp_pressed=float((opp & pressed).mean()))


def c2_xcorr(D, vmax, only_clip=False):
    """C2: does the sent setpoint follow the measured wheel in hands-on engaged runs?  Pooled cross-correlation of the
    first differences d(theta_sp) vs d(theta) at lags -30..+30 frames (positive lag = setpoint LATER than the wheel),
    then the OLS gain of d(theta_sp)(t) on d(theta)(t - lag*)."""
    m = D["eng"] & (np.abs(D["bar"]) > HANDS_ON) & (D["vego"] < vmax)
    if only_clip:
        m = m & (np.abs(D["sp"] - D["th"]) >= emax(D["vego"]) - 0.15)
    L = np.arange(-30, 31)
    num = np.zeros(len(L))
    sxx = syy = 0.0
    segs = runs(m, 50)
    if not segs:
        return dict(n_runs=0)
    pairs = {l: [[], []] for l in L}
    for a, b in segs:
        ds = np.diff(D["sp"][a:b])
        dt = np.diff(D["th"][a:b])
        ds = ds - ds.mean()
        dt = dt - dt.mean()
        sxx += float(dt @ dt)
        syy += float(ds @ ds)
        for j, l in enumerate(L):
            if l >= 0:
                x, y = dt[:len(dt) - l], ds[l:]
            else:
                x, y = dt[-l:], ds[:len(ds) + l]
            num[j] += float(x @ y)
            pairs[l][0].append(x)
            pairs[l][1].append(y)
    r = num / math.sqrt(max(sxx * syy, 1e-12))
    j = int(np.argmax(r))
    lb = int(L[j])
    x = np.concatenate(pairs[lb][0])
    y = np.concatenate(pairs[lb][1])
    gain = float((x @ y) / max(x @ x, 1e-12))
    return dict(n_runs=len(segs), secs=float(sum(b - a for a, b in segs) / FS), lag_frames=lb, lag_s=lb / FS,
                r_peak=float(r[j]), r0=float(r[L == 0][0]), gain=gain)


def c2_phase(x_all, y_all, m, lo=0.5, hi=5.0, nper=64):
    """sub-frame delay of y behind x from the cross-spectrum phase over [lo, hi] Hz, pooled over runs of m (>= 0.64 s):
    tau = -angle(Sxy)/(2 pi f), coherence-weighted; and |Sxy|/Sxx = the gain.  Positive tau = y LATER than x."""
    Sxy = Sxx = Syy = None
    nseg = 0
    for a, b in runs(m, nper):
        x = x_all[a:b] - np.mean(x_all[a:b])
        y = y_all[a:b] - np.mean(y_all[a:b])
        f, pxy = signal.csd(x, y, fs=FS, nperseg=nper, detrend="linear")
        _, pxx = signal.welch(x, fs=FS, nperseg=nper, detrend="linear")
        _, pyy = signal.welch(y, fs=FS, nperseg=nper, detrend="linear")
        k = (b - a) // nper
        Sxy = pxy * k if Sxy is None else Sxy + pxy * k
        Sxx = pxx * k if Sxx is None else Sxx + pxx * k
        Syy = pyy * k if Syy is None else Syy + pyy * k
        nseg += k
    if not nseg:
        return dict(nseg=0)
    sel = (f >= lo) & (f <= hi)
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
    tau = -np.angle(Sxy[sel]) / (2 * np.pi * f[sel])
    w = coh[sel]
    gain = np.abs(Sxy[sel]) / Sxx[sel]
    return dict(nseg=nseg, tau_s=float(np.sum(w * tau) / np.sum(w)), gain=float(np.sum(w * gain) / np.sum(w)),
                coh=float(np.mean(w)), f=[float(v) for v in f[sel]], tau_f=[float(v) for v in tau],
                gain_f=[float(v) for v in gain])


def c2_fork(D, vmax):
    """the same question on the FORK's own rows: does the planner's desired angle (carControl actuators, before the
    limiter and clip) follow the measured wheel under a hand, or only the sent value (carOutput, after the clip)?"""
    t = D["F_t_cs"]
    bar = np.interp(t, D["t"], D["bar"])
    jc = np.clip(np.searchsorted(D["F_t_cc"], t, side="right") - 1, 0, len(D["F_t_cc"]) - 1)
    jo = np.clip(np.searchsorted(D["F_t_co"], t, side="right") - 1, 0, len(D["F_t_co"]) - 1)
    lat = D["F_cc_latActive"][jc].astype(bool)
    m = lat & (np.abs(bar) > HANDS_ON) & (D["F_cs_vegoraw"] < vmax)
    th = D["F_cs_ang"].astype(float)
    return dict(des=c2_phase(th, D["F_cc_ang"][jc].astype(float), m), sent=c2_phase(th, D["F_co_ang"][jo].astype(float), m),
                n=int(m.sum()))


def dwells(D):
    with contextlib.redirect_stdout(io.StringIO()):
        import v293_symptom_instruments as SI
    return SI.dwells(np.abs(D["wire"]) / 8.0, D["th"], D["vego"], D["eng"])


# ---------------------------------------------------------------- fork side: limiter reconstruction + saturation rules
def vm_consts(cp):
    m, l, aF = cp["mass"], cp["wheelbase"], cp["centerToFront"]
    aR = l - aF
    cF, cR = cp["tireStiffnessFront"], cp["tireStiffnessRear"]
    sf = m * (cF * aF - cR * aR) / (l ** 2 * cF * cR)
    return cp["steerRatio"], l, sf, cp.get("steerRatioRear", 0.0) or 0.0


def limiter(D):
    """Replay of carcontroller._update_angle + apply_steer_angle_limits_vm at 311c4cc0b7 (read in the fork) on the logged
    carControl actuators.steeringAngleDeg, per carOutput row; alignment as drive_read_v299.derive_status (carControl =
    the row before the latest at/before carOutput, carState = latest at/before).  The limiter state is UNclipped (the
    error clip is a pure bound).  -> per-row flags + agreement with the logged carOutput angle."""
    cp = D["meta"]["carparams"]
    sR, l, sf, chi = vm_consts(cp)
    t = D["F_t_co"]
    jc = np.clip(np.searchsorted(D["F_t_cc"], t, side="right") - 2, 0, len(D["F_t_cc"]) - 1)
    js = np.clip(np.searchsorted(D["F_t_cs"], t, side="right") - 1, 0, len(D["F_t_cs"]) - 1)
    lat = D["F_cc_latActive"][jc].astype(bool)
    des = D["F_cc_ang"][jc].astype(float)
    th = D["F_cs_ang"][js].astype(float)
    v = np.maximum(D["F_cs_vegoraw"][js].astype(float), 1.0)
    fac = sR * l * (1.0 - sf * v ** 2) / (1.0 - chi)
    jerk = 3.0 + 9.81 * 0.06
    dmax = np.minimum(np.degrees(jerk / v ** 2 * fac) * 0.01, 2.5)
    amax = np.degrees((3.0 + 9.81 * 0.06) / v ** 2 * fac)    # MAX_LATERAL_ACCEL = ISO 3.0 + g * 0.06 = 3.5886
    em = emax(D["F_cs_vegoraw"][js].astype(float))
    n = len(t)
    out = np.empty(n)
    fr, fv, fc = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool)
    s = None
    for i in range(n):
        last = th[i] if s is None else s
        r = min(max(des[i], last - dmax[i]), last + dmax[i])
        r2 = min(max(r, -amax[i]), amax[i])
        if not lat[i]:
            r2 = th[i]
        r2 = min(max(r2, -400.0), 400.0)
        s = r2
        o = min(max(r2, th[i] - em[i]), th[i] + em[i]) if lat[i] else r2
        out[i] = o
        if lat[i]:
            fr[i] = abs(r - des[i]) > 1e-6
            fv[i] = abs(r2) < abs(r) - 1e-6
            fc[i] = abs(o - r2) > 1e-6
    co = D["F_co_ang"].astype(float)
    agree = np.abs(out - co)[lat] < 0.011
    return dict(t=t, lat=lat, des=des, th=th, v=D["F_cs_vegoraw"][js].astype(float), out=out, co=co, rate=fr, vm=fv,
                clip=fc, amax=amax, em=em, agree=float(agree.mean()) if agree.size else np.nan)


def sat_rules(D):
    """saturation duty, OLD rule (|desired - measured| > 2.5 deg) and NEW rule 9b7ef55826 (|carControl angle - carOutput
    angle| > 2.5), each through LatControl._check_saturation (v > 5, not steeringPressed, timer steerLimitTimer), on the
    controlsState rows.  Validated against the logged angleState.saturated (old rule on 83fa2e68c8, new on 311c4cc0b7)."""
    tl = D["F_t_ctl"]
    act = D["F_ang_active"].astype(bool)
    js = np.clip(np.searchsorted(D["F_t_cs"], tl, side="right") - 1, 0, len(D["F_t_cs"]) - 1)
    v = D["F_cs_vego"][js]
    pr = D["F_cs_press"][js].astype(bool)
    old_x = np.abs(D["F_ang_des"] - D["F_ang_meas"]) > 2.5
    jc = np.clip(np.searchsorted(D["F_t_cc"], tl, side="left") - 1, 0, len(D["F_t_cc"]) - 1)
    jo = np.clip(np.searchsorted(D["F_t_co"], tl, side="left") - 1, 0, len(D["F_t_co"]) - 1)
    new_x = np.abs(D["F_cc_ang"][jc] - D["F_co_ang"][jo]) > 2.5
    lim = float(D["meta"]["carparams"].get("steerLimitTimer", 0.8))

    def run(x):
        st, tm = np.zeros(len(x), bool), 0.0
        for i in range(len(x)):
            if not act[i]:
                tm = 0.0
                continue
            tm = tm + 0.01 if (x[i] and v[i] > 5.0 and not pr[i]) else tm - 0.01
            tm = min(max(tm, 0.0), lim)
            st[i] = tm > lim - 1e-3
        return st

    so, sn = run(old_x), run(new_x)
    lg = D["F_ang_sat"].astype(bool)
    a = act
    eps = lambda s: len(runs(s & a, 1))  # noqa: E731
    return dict(n_act=int(a.sum()), logged=float(lg[a].mean()), old=float(so[a].mean()), new=float(sn[a].mean()),
                logged_eps=eps(lg), old_eps=eps(so), new_eps=eps(sn),
                agree_old=float((so == lg)[a].mean()), agree_new=float((sn == lg)[a].mean()))


def max_angle(D, L):
    lat = L["lat"]
    out = dict(sp_peak=float(np.max(np.abs(D["sp"][D["eng"]]))) if D["eng"].any() else np.nan,
               th_peak_eng=float(np.max(np.abs(D["th"][D["eng"]]))) if D["eng"].any() else np.nan,
               th_peak_all=float(np.max(np.abs(D["th"]))),
               des_peak=float(np.max(np.abs(L["des"][lat]))) if lat.any() else np.nan,
               co_peak=float(np.max(np.abs(L["co"][lat]))) if lat.any() else np.nan,
               agree=L["agree"])
    hi = lat & (np.abs(L["th"]) > 150)
    out["hi150_n"] = int(hi.sum())
    for k in ("clip", "vm", "rate"):
        out["hi150_" + k] = float(L[k][hi].mean()) if hi.any() else np.nan
    # the wheel short of the planner's desired angle: sign(des)*(des - theta) > 2 deg at |des| > 30 deg
    short = lat & (np.abs(L["des"]) > 30) & (np.sign(L["des"]) * (L["des"] - L["th"]) > 2.0)
    by = {}
    for nm, lo, hi_ in VBANDS:
        mb = short & (L["v"] >= lo) & (L["v"] < hi_)
        nb = int(mb.sum())
        if nb == 0:
            by[nm] = dict(n=0)
            continue
        vm_ = L["vm"][mb]
        cl = L["clip"][mb] & ~vm_
        rt = L["rate"][mb] & ~vm_ & ~L["clip"][mb]
        none = ~(vm_ | L["clip"][mb] | L["rate"][mb])
        sf = (np.sign(L["des"]) * (L["des"] - L["th"]))[mb]
        by[nm] = dict(n=nb, secs=nb / FS, vm=float(vm_.mean()), clip=float(cl.mean()), rate=float(rt.mean()),
                      none=float(none.mean()), short_p50=float(np.median(sf)), short_p90=float(np.percentile(sf, 90)),
                      th_p50=float(np.median(np.abs(L["th"][mb]))),
                      # in the 'none' class the setpoint went out at the desired value: the firmware/plant holds it short
                      none_short_p50=float(np.median(sf[none])) if none.any() else np.nan)
    out["short_by_band"] = by
    # HANDS-OFF (|bar| < 300 on this row and the preceding 0.5 s) and QUASI-STATIC (|d desired/dt| < 10 deg/s over the
    # preceding 0.5 s): what holds a hands-off sustained turn short of the planner
    bar = np.abs(np.interp(L["t"], D["t"], D["bar"]))
    k = 50
    hm = np.convolve((bar >= 300).astype(float), np.ones(k), "full")[:len(bar)] == 0
    dd = np.abs(np.r_[0, np.diff(L["des"])]) * FS
    qs = np.convolve((dd >= 10).astype(float), np.ones(k), "full")[:len(dd)] == 0
    out["ho_peak_th"] = float(np.max(np.abs(L["th"][lat & hm]))) if (lat & hm).any() else np.nan
    out["ho_peak_des"] = float(np.max(np.abs(L["des"][lat & hm]))) if (lat & hm).any() else np.nan
    byh = {}
    for nm, lo, hi_ in VBANDS:
        mb = short & hm & qs & (L["v"] >= lo) & (L["v"] < hi_)
        nb = int(mb.sum())
        if nb == 0:
            byh[nm] = dict(n=0)
            continue
        vm_ = L["vm"][mb]
        sf = (np.sign(L["des"]) * (L["des"] - L["th"]))[mb]
        none = ~(vm_ | L["clip"][mb] | L["rate"][mb])
        byh[nm] = dict(n=nb, vm=float(vm_.mean()), clip=float((L["clip"][mb] & ~vm_).mean()),
                       rate=float((L["rate"][mb] & ~vm_ & ~L["clip"][mb]).mean()), none=float(none.mean()),
                       short_p50=float(np.median(sf)), th_p50=float(np.median(np.abs(L["th"][mb]))),
                       th_max=float(np.max(np.abs(L["th"][mb]))), des_max=float(np.max(np.abs(L["des"][mb]))))
    out["short_ho_qs_by_band"] = byh
    # hands-off engaged time at |theta| > 150 and its clip duty
    mh = lat & hm & (np.abs(L["th"]) > 150)
    out["ho_hi150_s"] = float(mh.sum() / FS)
    out["ho_hi150_clip"] = float(L["clip"][mh].mean()) if mh.any() else np.nan
    # clip-bound duty by band and by angle (all latActive rows)
    cbb = {}
    for nm, lo, hi_ in VBANDS:
        mb = lat & (L["v"] >= lo) & (L["v"] < hi_)
        cbb[nm] = dict(n=int(mb.sum()), clip=float(L["clip"][mb].mean()) if mb.any() else np.nan,
                       vm=float(L["vm"][mb].mean()) if mb.any() else np.nan,
                       clip_hi150=float(L["clip"][mb & (np.abs(L["th"]) > 150)].mean())
                       if (mb & (np.abs(L["th"]) > 150)).any() else np.nan,
                       n_hi150=int((mb & (np.abs(L["th"]) > 150)).sum()))
    out["duty_by_band"] = cbb
    return out


def attribution(D):
    m = D["meta"]
    cp = m["carparams"]
    t, v, e = D["t"], D["vego"], D["eng"]
    exp = {}
    for nm, lo, hi in VBANDS:
        mb = e & (v >= lo) & (v < hi)
        exp[nm] = float(mb.sum() / FS / 60.0)
    hand = e & (np.abs(D["bar"]) > HANDS_ON)
    return dict(fw=fw_of(m), commit=(m.get("fork_meta") or {}).get("fork_commit_full") or (m.get("git") or {}).get(
        "commit"), branch=(m.get("params") or {}).get("GitBranch"), steerControlType=cp.get("steerControlType"),
                steerRatio=cp.get("steerRatio"), maxLateralAccel=cp.get("maxLateralAccel"),
                route_min=float((t[-1] - t[0]) / 60.0), eng_min=float(e.sum() / FS / 60.0), exp_min=exp,
                handson_eng_min_lt6=float((hand & (v < 6)).sum() / FS / 60.0),
                handson_eng_min_lt10=float((hand & (v < 10)).sum() / FS / 60.0),
                alerts=sorted(set(str(x) for x in D.get("F_sdalert_text", []))))


def analyse(tag):
    t0 = time.time()
    D = load(tag)
    rows = windows(D)
    A = dict(tag=tag, attrib=attribution(D))
    A["bar_sign"] = dict(zip(("k", "n", "agree"), bar_sign(D)))
    for vmax in (6.0, 10.0):
        E, Dd = handson_sets(rows, vmax)
        cmp_ = {}
        for key in ("bar_V2", "bar_C3", "bar_V1", "w_V2", "w_C3", "w_V1", "w_C2"):
            cmp_[key] = compare(E, Dd, key, vmax)[:3]
        A["grind_v%d" % vmax] = dict(n_eng=len(E), n_dis=len(Dd), cmp=cmp_,
                                     med_eng={k: float(np.median([r[k] for r in E])) if E else np.nan
                                              for k in ("bar_V2", "bar_C3", "bar_V1", "w_V2", "w_C3", "w_V1")},
                                     med_dis={k: float(np.median([r[k] for r in Dd])) if Dd else np.nan
                                              for k in ("bar_V2", "bar_C3", "bar_V1", "w_V2", "w_C3", "w_V1")})
        A["c1_v%d" % vmax] = c1_frames(D, vmax)
        A["c2_v%d" % vmax] = c2_xcorr(D, vmax)
        A["c2clip_v%d" % vmax] = c2_xcorr(D, vmax, only_clip=True)
        mh = D["eng"] & (np.abs(D["bar"]) > HANDS_ON) & (D["vego"] < vmax)
        A["c2ph_v%d" % vmax] = c2_phase(D["th"], D["sp"], mh)
        A["c2ph_ho_v%d" % vmax] = c2_phase(D["th"], D["sp"], D["eng"] & (np.abs(D["bar"]) < 300) & (D["vego"] < vmax))
        A["c2fork_v%d" % vmax] = c2_fork(D, vmax)
        # C1/C2 vs band energy inside the engaged hands-on windows: opposing-at-clip windows vs the rest
        oc = [r for r in E if r.get("opp_clip", 0) > 0.5]
        no = [r for r in E if r.get("opp_clip", 0) < 0.1]
        A["c1band_v%d" % vmax] = dict(n_oc=len(oc), n_no=len(no), **{
            k: (float(np.median([r[k] for r in oc])) if oc else np.nan,
                float(np.median([r[k] for r in no])) if no else np.nan)
            for k in ("bar_C3", "bar_V1", "bar_V2", "w_C2", "w_C3")})
    A["dwells"] = {k: dict(per_min_025=d.get("per_min_025"), per_min_050=d.get("per_min_050"), sec=d.get("sec"),
                           snap_p50=d.get("snap_p50")) for k, d in dwells(D).items()}
    L = limiter(D)
    A["maxang"] = max_angle(D, L)
    A["sat"] = sat_rules(D)
    A["rows"] = rows
    A["secs"] = time.time() - t0
    return A


def main():
    force = "--force" in sys.argv
    routes = [(tag_of(p), p) for p in NEW] + list((k, v) for k, v in REFS.items())
    for tag, p in routes:
        t0 = time.time()
        prep(tag, p, force=force)
        if time.time() - t0 > 1:
            print("prep %s %.1f s" % (tag, time.time() - t0))
    if "--prep" in sys.argv:
        return
    res = {}
    for tag, p in routes:
        A = analyse(tag)
        res[tag] = A
        print("%-16s %s %5.1f s" % (tag, A["attrib"]["fw"], A["secs"]))
    OUT.mkdir(exist_ok=True)

    def js(x):
        if isinstance(x, dict):
            return {str(k): js(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [js(v) for v in x]
        if isinstance(x, (np.floating, float)):
            return None if not np.isfinite(x) else float(x)
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, np.bool_):
            return bool(x)
        return x
    (OUT / "read_ad_b4.json").write_text(json.dumps(js(res), indent=1))
    print("total %.1f s" % (time.time() - T0))


if __name__ == "__main__":
    main()
