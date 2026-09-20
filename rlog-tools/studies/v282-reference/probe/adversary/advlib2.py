# -*- coding: utf-8 -*-
"""ADVERSARY (probe workflow) -- my own identification, sharing no estimator code with the streams.

I reuse only the CACHE READER (v282cmp.load) and the fork-source constants, because those are data and
source, not method.  Windowing, FFT, the IV estimator, the controller transfer and every margin statistic
below are written here from the fork source and from first principles.

POSITIVE CONTROLS are in _self_test(): a synthetic closed loop with a KNOWN plant, a KNOWN PI controller,
a narrow reference and an independent disturbance.  The estimator must recover P, L and the vector margin,
and must FAIL visibly where the instrument has no power -- that failure is the whole point of this stream.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
DT = 1.0 / FS

# ---- fork source, read at the flown commits (latcontrol_torque.py / latcontrol_vehicle_tunes.py) -------
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 1.0
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
EPS_INERTIA = 8e-5
KI_SCHED_BP = [8.0, 18.0]

# every route's flown lateral params, read from hsurface/surface/params_all.json (its OWN initData).
# 'notch' is True only where the flown commit CONTAINS HondaAccordErrorNotch.
FLOWN = {
    "00000064--ce6b0b0ebb": dict(kp=0.9,  laf=6.0,  ki=0.3,  ki_hi=0.0, notch=False, q=1.0, eps="V282"),
    "00000065--b9f78988bd": dict(kp=0.9,  laf=6.0,  ki=0.3,  ki_hi=0.0, notch=False, q=1.0, eps="V282"),
    "0000006c--2bc842dbac": dict(kp=0.9,  laf=6.0,  ki=0.3,  ki_hi=0.0, notch=False, q=1.0, eps="V282"),
    "0000006c--68c6e94b17": dict(kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True,  q=1.0, eps="V293"),
    "0000006d--05e83bb04f": dict(kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True,  q=1.0, eps="V293"),
    "0000006e--6ca3e014fd": dict(kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True,  q=1.0, eps="V293"),
    "00000076--d0b7ea7e4d": dict(kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True,  q=1.0, eps="V293"),
    "00000075--6c8687d5bd": dict(kp=0.85, laf=14.0, ki=0.6,  ki_hi=2.5, notch=True,  q=1.0, eps="V293"),
    "00000070--717f5a7866": dict(kp=0.3,  laf=6.0,  ki=0.15, ki_hi=0.0, notch=False, q=1.0, eps="V293"),
    "00000071--f2c9d073a3": dict(kp=0.85, laf=14.0, ki=0.3,  ki_hi=0.0, notch=False, q=1.0, eps="V293"),
    "00000072--8001fc3048": dict(kp=0.85, laf=14.0, ki=0.6,  ki_hi=0.0, notch=False, q=1.0, eps="V293"),
    "00000073--79fd149dd8": dict(kp=0.85, laf=14.0, ki=0.6,  ki_hi=0.0, notch=False, q=1.0, eps="V293"),
}
LBL = {"00000071--f2c9d073a3": "r71 LIMIT-CYCLED 2.34Hz", "00000072--8001fc3048": "r72 flew clean",
       "00000073--79fd149dd8": "r73 hidden relay", "0000006c--68c6e94b17": "T64 rev6.4",
       "0000006d--05e83bb04f": "T64 rev6.4", "00000064--ce6b0b0ebb": "V282 ref",
       "00000065--b9f78988bd": "V282 ref", "0000006c--2bc842dbac": "V282 ref",
       "00000070--717f5a7866": "r70 V293 open-loop", "00000075--6c8687d5bd": "r75 rev4",
       "00000076--d0b7ea7e4d": "r76 rev5", "0000006e--6ca3e014fd": "r6e rev6.4b"}


def lsf_of(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / EPS_INERTIA) / (2.0 * np.pi)


def ki_of(v, ki, ki_hi):
    return float(ki) if ki_hi <= 0 else float(np.interp(v, KI_SCHED_BP, [float(ki), float(ki_hi)]))


def notch_H(f, f0, q, dt=DT):
    k = np.tan(np.pi * min(float(f0), 0.45 / dt) * dt)
    n = 1.0 / (1.0 + k / q + k * k)
    b0, b1, a2 = (1 + k * k) * n, 2 * (k * k - 1) * n, (1 - k / q + k * k) * n
    z = np.exp(-2j * np.pi * np.asarray(f, float) * dt)
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def C_fb(f, v, kp, laf, ki, ki_hi=0.0, q=None, kd=0.0, kd_lp=2.0):
    """error(raw) -> logged output, exactly as latcontrol_torque.py computes it at speed v."""
    z = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    with np.errstate(divide="ignore", invalid="ignore"):
        I = ki_of(v, ki, ki_hi) * DT / (1.0 - z)
    num = (kp + I) * (1.0 + lsf_of(v) / max(kp, 1e-3))
    if kd:
        a = DT / (1.0 / (2 * np.pi * kd_lp) + DT)
        num = num + kd * (1.0 - z) / DT * (a / (1.0 - (1 - a) * z))
    C = -num / laf
    if q is not None and q > 0:
        C = C * notch_H(f, mode_hz(v), q)
    return C


# ---------------------------------------------------------------------------------------------------
def load(route):
    S = V.load(route)
    p, i, ff, out = S["p"], S["i"], S["f"], S["out"]
    with np.errstate(divide="ignore", invalid="ignore"):
        lf = np.where(np.abs(out) > 5e-3, -(p + i + ff) / out, np.nan)
    act = S["active"] & ~S["pressed"]
    laf = float(np.nanmedian(lf[act])) if act.any() else np.nan
    return dict(route=route, t=S["t"], v=S["v"], act=act, sat=S["sat"], sr=S["sr"], sa=S["sa"],
                r=S["setpoint"], x=S["model"], y=S["la_act"], p=p, i=i, f=ff, out=out, laf=laf)


def spectra(L, nps=1024, hop=512, min_s=30.0, drop_sat=True):
    """Windowed FFTs of every laterally-engaged hands-off window.  Returns f, dict of (nwin,nf), vmed."""
    m = L["act"] & np.isfinite(L["r"]) & np.isfinite(L["y"]) & np.isfinite(L["out"])
    w = signal.get_window("hann", nps)
    f = np.fft.rfftfreq(nps, DT)
    laf = L["laf"]
    sig = dict(r=np.nan_to_num(L["r"]), y=np.nan_to_num(L["y"]), u=np.nan_to_num(L["out"]),
               ufb=-(np.nan_to_num(L["p"]) + np.nan_to_num(L["i"])) / laf,
               uff=-np.nan_to_num(L["f"]) / laf, x=np.nan_to_num(L["x"]), sr=np.nan_to_num(L["sr"]))
    rows = {k: [] for k in sig}
    vm, am = [], []
    for a, b in V.runs(m, L["t"], min_s=min_s):
        for s in range(a, b - nps + 1, hop):
            e = s + nps
            if drop_sat and float(np.mean(L["sat"][s:e])) > 0.02:
                continue
            for k, arr in sig.items():
                rows[k].append(np.fft.rfft(signal.detrend(arr[s:e]) * w))
            vm.append(float(np.median(L["v"][s:e])))
            am.append(float(np.std(signal.detrend(np.nan_to_num(L["x"])[s:e]))))
    F = {k: (np.array(v) if v else np.zeros((0, len(f)), complex)) for k, v in rows.items()}
    return f, F, np.array(vm), np.array(am)


def ident(F, idx=None, instr="r"):
    """IV / joint-input-output identification.  P = S_wy/S_wu, Cfb = S_w,ufb/S_w,e, L = P*Cfb."""
    R = F if idx is None else {k: v[idx] for k, v in F.items()}
    X = lambda a, b: np.mean(np.conj(R[a]) * R[b], axis=0)
    Sww = X(instr, instr).real
    Swy, Swu, Swb, Swr = X(instr, "y"), X(instr, "u"), X(instr, "ufb"), X(instr, "r")
    Swe = Swr - Swy
    Suu, Syy, Srr = X("u", "u").real, X("y", "y").real, X("r", "r").real
    Sry = X("r", "y")
    See = np.maximum(Srr - 2 * Sry.real + Syy, 1e-300)
    P = Swy / Swu
    C = Swb / Swe
    return dict(P=P, C=C, L=P * C, n=R["r"].shape[0],
                coh_wu=np.abs(Swu) ** 2 / np.maximum(Sww * Suu, 1e-300),
                coh_wy=np.abs(Swy) ** 2 / np.maximum(Sww * Syy, 1e-300),
                coh_we=np.abs(Swe) ** 2 / np.maximum(Sww * See, 1e-300),
                Srr=Srr, Suu=Suu, Syy=Syy, See=See)


def vecmargin(f, L, lo=2.0, hi=6.0):
    s = (f >= lo) & (f <= hi)
    d = np.abs(1.0 + np.asarray(L)[s])
    k = int(np.argmin(d))
    return float(d[k]), float(f[s][k])


def Ms_of(f, L, lo=0.15, hi=12.0):
    s = (f >= lo) & (f <= hi)
    S = np.abs(1.0 / (1.0 + np.asarray(L)[s]))
    k = int(np.argmax(S))
    return float(S[k]), float(f[s][k])


def bandmean(f, A, lo, hi):
    s = (f >= lo) & (f <= hi)
    return float(np.mean(np.abs(np.asarray(A)[s])))


# ---------------------------------------------------------------------------------------------------
def _sim(n, rlp, dlp, g, fp, nd, kp, ki, laf, ffg, ffr, seed, fric=0.0):
    rng = np.random.default_rng(seed)
    a = DT / (1.0 / (2 * np.pi * fp) + DT)
    r = signal.sosfiltfilt(signal.butter(2, rlp, fs=FS, output="sos"), rng.standard_normal(n)) * 40
    d = signal.sosfiltfilt(signal.butter(2, dlp, fs=FS, output="sos"), rng.standard_normal(n)) * 20
    y = np.zeros(n); u = np.zeros(n); ufb = np.zeros(n); uff = np.zeros(n)
    ii = 0.0; st = 0.0; hist = [0.0] * (nd + 1); pr = r[0]
    for k in range(n):
        e = r[k] - y[k]
        ii += ki * DT * e
        ufb[k] = -(kp * e + ii) / laf
        uff[k] = -(ffg * r[k] + ffr * (r[k] - pr) / DT) / laf - fric * np.sign(e)
        pr = r[k]
        u[k] = ufb[k] + uff[k]
        hist.append(u[k]); hist.pop(0)
        st += a * (g * hist[0] - st)
        if k + 1 < n:
            y[k + 1] = st + d[k + 1]
    z = np.exp(-2j * np.pi * np.fft.rfftfreq(1024, DT) * DT)
    Pt = g * (a / (1 - (1 - a) * z)) * z ** (nd + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        Ct = -(kp + ki * DT / (1 - z)) / laf
    return dict(r=r, y=y, u=u, ufb=ufb, uff=uff, x=r, sr=y), Pt, Ct


def _F(arrs, nps=1024, hop=512):
    n = len(arrs["r"]); w = signal.get_window("hann", nps)
    out = {k: [] for k in arrs}
    for s in range(0, n - nps + 1, hop):
        for k, a in arrs.items():
            out[k].append(np.fft.rfft(signal.detrend(a[s:s + nps]) * w))
    return {k: np.array(v) for k, v in out.items()}


def _self_test():
    f = np.fft.rfftfreq(1024, DT)
    ln = []
    # C1 broadband reference: the estimator must recover P, L and the vector margin.
    A, Pt, Ct = _sim(400 * 100, 5.0, 3.0, -9.0, 1.6, 6, 1.0, 0.3, 6.0, 0.4, 0.05, 7)
    R = ident(_F(A))
    s = (f >= 0.2) & (f <= 6.0)
    eP = float(np.median(np.abs(R["P"][s] - Pt[s]) / np.abs(Pt[s])))
    eL = float(np.median(np.abs(R["L"][s] - Pt[s] * Ct[s]) / np.abs(Pt[s] * Ct[s])))
    v0, fv0 = vecmargin(f, Pt * Ct)
    v1, fv1 = vecmargin(f, R["L"])
    ln.append(f"  C1 broadband: P err {eP*100:.2f}%  L err {eL*100:.2f}%  VM truth {v0:.4f}@{fv0:.2f} "
              f"est {v1:.4f}@{fv1:.2f}")
    assert eP < 0.05 and eL < 0.05, ln[-1]
    assert abs(v1 - v0) < 0.05, ln[-1]
    # C2 narrow reference (0.45 Hz) + heavy 3 Hz disturbance: the estimate must be BAD above the
    # instrument's band.  This control exists to show the failure the probe claims to repair.
    A, Pt, Ct = _sim(400 * 100, 0.45, 3.0, -9.0, 1.6, 6, 1.0, 0.3, 6.0, 0.4, 0.05, 11)
    R = ident(_F(A))
    lo = (f >= 0.2) & (f <= 0.6)
    hi = (f >= 2.0) & (f <= 6.0)
    e_lo = float(np.median(np.abs(R["L"][lo] - (Pt * Ct)[lo]) / np.abs((Pt * Ct)[lo])))
    e_hi = float(np.median(np.abs(R["L"][hi] - (Pt * Ct)[hi]) / np.abs((Pt * Ct)[hi])))
    v0, _ = vecmargin(f, Pt * Ct)
    v1, _ = vecmargin(f, R["L"])
    ln.append(f"  C2 narrow r: L err {e_lo*100:5.1f}% in 0.2-0.6 Hz, {e_hi*100:7.1f}% in 2-6 Hz; "
              f"VM truth {v0:.4f} est {v1:.4f}  <- the failure the probe targets")
    assert e_hi > 3 * e_lo, ln[-1]
    # C3 the notch transfer against a brute-force time-domain run
    rng = np.random.default_rng(3)
    x = rng.standard_normal(60000); yn = np.empty_like(x)
    x1 = x2 = y1 = y2 = 0.0
    k = np.tan(np.pi * 1.9 * DT); n_ = 1 / (1 + k + k * k)
    b0, b1, a2 = (1 + k * k) * n_, 2 * (k * k - 1) * n_, (1 - k + k * k) * n_
    for j, xv in enumerate(x):
        yv = b0 * xv + b1 * x1 + b0 * x2 - b1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, xv, y1, yv
        yn[j] = yv
    fw, pxx = signal.welch(x, FS, nperseg=4096)
    _, pxy = signal.csd(x, yn, FS, nperseg=4096)
    m = (fw > 0.2) & (fw < 10)
    en = float(np.max(np.abs((pxy / pxx)[m] - notch_H(fw, 1.9, 1.0)[m])))
    ln.append(f"  C3 notch transfer: max |empirical - analytic| 0.2-10 Hz = {en:.2e}")
    assert en < 2e-2, ln[-1]
    return "ADVLIB2 SELF-TEST OK\n" + "\n".join(ln)


if __name__ == "__main__":
    print(_self_test())
