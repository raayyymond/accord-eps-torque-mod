# -*- coding: utf-8 -*-
"""adv_core -- ADVERSARY's OWN extraction + loop algebra, written from the fork source and the
caches, sharing no code with shapedgain/frontier beyond v282cmp.load (the raw cache reader).

Deliberate differences from the frontier engine, so that agreement means something:
  * window length is a free parameter (512 / 1024 / 2048), hop = nperseg // 2
  * the plant instrument is X (the MODEL's desired lateral accel, upstream of the whole controller),
    not Z (the controller's own shaped setpoint)
  * the wheel-angle -> yaw leg V is computed four ways
  * the saturation-window filter is a switch, not a constant
  * the controller transfer C(z) is re-derived here from latcontrol_torque.py lines 336-345 + 683-684
    and cross-checked against the logged p / error ratio per route.

METRIC (the brief's, unchanged): sum |X-Y|^2 over 0.15-2.4 Hz / sum |X|^2 over the same band,
laterally engaged, hands off, v >= 15 m/s, contiguous runs >= 30 s.
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
BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
SHAKE = (1.8, 3.5)
SHAKE_PTS = (1.95, 2.54, 3.03)

T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]

# fork constants, re-read from latcontrol_vehicle_tunes.py / latcontrol_torque.py
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 1.0
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
EPS_INERTIA = 8e-5


def lsf_of(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def mode_hz(v):
    return np.sqrt(np.interp(v, HOLD_V_BP, HOLD_K_V) / EPS_INERTIA) / (2.0 * np.pi)


def notch_H(f, f0, q):
    """HondaAccordErrorNotch: biquad from tan-prewarped f0, exactly as the fork builds it."""
    k = np.tan(np.pi * np.minimum(np.asarray(f0, float), 0.45 / DT) * DT)
    k = np.atleast_1d(k)[:, None]
    norm = 1.0 / (1.0 + k / q + k * k)
    b0 = (1.0 + k * k) * norm
    b1 = 2.0 * (k * k - 1.0) * norm
    a2 = (1.0 - k / q + k * k) * norm
    z = np.exp(-2j * np.pi * np.asarray(f, float)[None, :] * DT)
    return (b0 + b1 * z + b0 * z ** 2) / (1.0 + b1 * z + a2 * z ** 2)


def C_fb(f, v, kp, laf, ki, q):
    """raw error (Z - M) -> logged U_FB = -(p+i)/LAF.  (nwin, nf)."""
    v = np.asarray(v, float)
    lsf = lsf_of(v)[:, None]
    z = np.exp(-2j * np.pi * np.asarray(f, float)[None, :] * DT)
    with np.errstate(divide="ignore", invalid="ignore"):
        pi = kp + ki * DT / (1.0 - z)
    C = -pi * (1.0 + lsf / max(kp, 1e-3)) / laf
    if q is not None and q > 0:
        C = C * notch_H(f, mode_hz(v), q)
    return C


def extract(route, nps=1024, vmin=15.0, run_s=30.0, satfilt=0.02, detrend="linear"):
    """Per-window rffts of every signal the algebra needs.  One route at a time (RAM)."""
    S = V.load(route)
    with np.errstate(divide="ignore", invalid="ignore"):
        laff = np.where(np.abs(S["out"]) > 5e-3, -(S["p"] + S["i"] + S["f"]) / S["out"], np.nan)
    act = S["active"]
    laf = float(np.nanmedian(laff[act]))
    m = (act & ~S["pressed"] & (S["v"] >= vmin)
         & np.isfinite(S["setpoint"]) & np.isfinite(S["la_act"]) & np.isfinite(S["la_pose"])
         & np.isfinite(S["model"]) & np.isfinite(S["out"]))
    sig = dict(X=np.nan_to_num(S["model"]), Y=np.nan_to_num(S["la_pose"]),
               Z=np.nan_to_num(S["setpoint"]), M=np.nan_to_num(S["la_act"]),
               UFB=-(np.nan_to_num(S["p"]) + np.nan_to_num(S["i"])) / laf,
               UFF=-np.nan_to_num(S["f"]) / laf, U=np.nan_to_num(S["out"]),
               SR=np.nan_to_num(S["sr"]), SA=np.nan_to_num(S["sa"]))
    hop = nps // 2
    w = signal.get_window("hann", nps)
    f = np.fft.rfftfreq(nps, DT)
    cols = {k: [] for k in sig}
    vmed, amp, satf, secs = [], [], [], 0.0
    for a, b in V.runs(m, S["t"], min_s=run_s):
        secs += (S["t"][b - 1] - S["t"][a])
        for s in range(a, b - nps + 1, hop):
            e = s + nps
            sf = float(np.mean(S["sat"][s:e]))
            if satfilt is not None and sf > satfilt:
                continue
            vv = S["v"][s:e]
            if not np.isfinite(vv).all():
                continue
            for k, arr in sig.items():
                cols[k].append(np.fft.rfft(signal.detrend(arr[s:e], type=detrend) * w))
            vmed.append(float(np.median(vv)))
            amp.append(float(np.std(sig["X"][s:e])))
            satf.append(sf)
    out = dict(route=route, f=f, laf=laf, sec=secs,
               v=np.array(vmed), amp=np.array(amp), sat=np.array(satf),
               **{k: np.array(v) for k, v in cols.items()})
    del S, sig, cols
    return out


def cat(ds):
    keys = ("X", "Y", "Z", "M", "UFB", "UFF", "U", "SR", "SA")
    o = dict(f=ds[0]["f"], laf=ds[0]["laf"],
             v=np.concatenate([d["v"] for d in ds]),
             amp=np.concatenate([d["amp"] for d in ds]),
             sat=np.concatenate([d["sat"] for d in ds]),
             sec=sum(d["sec"] for d in ds))
    for k in keys:
        o[k] = np.concatenate([d[k] for d in ds], axis=0)
    return o


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def coh(A, B):
    return np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)


def metric(W, band=BAND):
    f = W["f"]
    b = (f >= band[0]) & (f <= band[1])
    E = W["X"] - W["Y"]
    return float(np.sum(np.abs(E[:, b]) ** 2) / np.sum(np.abs(W["X"][:, b]) ** 2))


def bands_of(W, E=None):
    f = W["f"]
    b = (f >= BAND[0]) & (f <= BAND[1])
    px = float(np.sum(np.abs(W["X"][:, b]) ** 2))
    E = (W["X"] - W["Y"]) if E is None else E
    return [float(np.sum(np.abs(E[:, (f >= a) & (f < c)]) ** 2)) / px for a, c in SUB]


def identify(W, inst="X", vsel=None):
    """P (U -> M) and V (M -> Y) on a window subset, by instrumental variables."""
    sel = np.ones(len(W["v"]), bool) if vsel is None else vsel
    I = W[inst][sel]
    U, M, Y, Z = W["U"][sel], W["M"][sel], W["Y"][sel], W["Z"][sel]
    P = xs(I, M) / xs(I, U)
    V_iv = xs(I, Y) / xs(I, M)
    V_h1 = xs(M, Y) / np.maximum(xs(M, M).real, 1e-300)
    return dict(P=P, P_h1=xs(U, M) / np.maximum(xs(U, U).real, 1e-300),
                V_iv=V_iv, V_h1=V_h1, n=int(sel.sum()),
                coh_iu=coh(I, U), coh_im=coh(I, M), coh_my=coh(M, Y), coh_iy=coh(I, Y))
