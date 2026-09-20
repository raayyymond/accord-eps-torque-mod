# -*- coding: utf-8 -*-
"""ADVERSARY stream, own library. Shares NO code with the other shapedgain streams by construction:
every estimator here is written from the node definitions, not imported from lp_lib / sb_lib / dlib.

Nodes (all logged on the controlsState clock, cache built by build_cache.py):
  X  model desired lateral accel        cs_des_curv * vEgo^2                       m/s^2
  Z  controller setpoint (shaped)       cs_la_des                                  m/s^2
  M  controller's fed-back measurement  cs_la_act  (= wheel angle through a static map)   m/s^2
  Y  achieved lateral accel             livePose wz * vEgo                         m/s^2
  U  command                            -cs_out  (= output_torque, +X polarity)    [-1,1]

THE GOAL METRIC (as handed down, used unchanged):
    J = sum_{0.15..2.4 Hz} |X - Y|^2  /  sum_{0.15..2.4 Hz} |X|^2
  over laterally-engaged hands-off runs >= 30 s at >= 15 m/s.  ONE denominator for all bands.

ANALYSIS ONLY.  Read-only on logs; writes only under this folder.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]          # .../studies/v282-reference
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402   (cache loader + run masking only; no estimator is reused)

FS = 100.0
OUT = HERE / "out"

# Flown lateral params, each from its OWN route's initData (hsurface/surface/params_all.json,
# transcribed independently here so a transcription error in one stream cannot propagate).
FLOWN = {
    "00000064--ce6b0b0ebb": dict(fam="V282", eps="V282", kp=0.9,  laf=6.0,  ki=0.3,  ki_hi=0.0, notch=False),
    "00000065--b9f78988bd": dict(fam="V282", eps="V282", kp=0.9,  laf=6.0,  ki=0.3,  ki_hi=0.0, notch=False),
    "0000006c--2bc842dbac": dict(fam="V282", eps="V282", kp=0.9,  laf=6.0,  ki=0.3,  ki_hi=0.0, notch=False),
    "00000039--f56039af87": dict(fam="V282old", eps="V282", kp=0.8, laf=2.11, ki=0.3, ki_hi=0.0, notch=False),
    "0000003a--283a39a1d6": dict(fam="V282old", eps="V282", kp=0.8, laf=4.0,  ki=0.3, ki_hi=0.0, notch=False),
    "0000003c--927965c2b4": dict(fam="V282old", eps="V282", kp=0.8, laf=3.6,  ki=0.3, ki_hi=0.0, notch=False),
    "0000006c--68c6e94b17": dict(fam="T64",  eps="V293", kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True),
    "0000006d--05e83bb04f": dict(fam="T64",  eps="V293", kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True),
    "0000006e--6ca3e014fd": dict(fam="T64B", eps="V293", kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True),
    "00000076--d0b7ea7e4d": dict(fam="T5",   eps="V293", kp=1.0,  laf=14.0, ki=0.3,  ki_hi=0.0, notch=True),
    "00000075--6c8687d5bd": dict(fam="T4",   eps="V293", kp=0.85, laf=14.0, ki=0.6,  ki_hi=2.5, notch=True),
    "00000070--717f5a7866": dict(fam="RF00T", eps="V293", kp=0.3, laf=6.0,  ki=0.15, ki_hi=0.0, notch=False),
    "00000071--f2c9d073a3": dict(fam="T2",   eps="V293", kp=0.85, laf=14.0, ki=0.3,  ki_hi=0.0, notch=False),
    "00000072--8001fc3048": dict(fam="T3",   eps="V293", kp=0.85, laf=14.0, ki=0.6,  ki_hi=0.0, notch=False),
    "00000073--79fd149dd8": dict(fam="T3R",  eps="V293", kp=0.85, laf=14.0, ki=0.6,  ki_hi=0.0, notch=False),
}
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0.0, 10.0, 20.0, 30.0], [12.0, 10.5, 8.0, 5.0], 1.0

F1, F2 = 0.15, 2.40          # the goal metric's band
NPERSEG = 2048               # 20.48 s -> df 0.0488 Hz, so 0.15 Hz is resolved (bin 3)
MINRUN = 30.0
VMIN = 15.0


def lsf(v):
    """(kp + lsf) is the effective P gain; latcontrol_torque.py:339."""
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def load_nodes(rk):
    """Return the five nodes + speed + usable mask, all on the controlsState clock."""
    S = V.load(rk)
    v = S["v"]
    return dict(rk=rk, t=S["t"], v=v,
                X=np.nan_to_num(S["model"]), Z=np.nan_to_num(S["setpoint"]),
                M=np.nan_to_num(S["la_act"]), Y=np.nan_to_num(S["la_pose"]),
                U=-np.nan_to_num(S["out"]),
                fin=np.isfinite(S["model"]) & np.isfinite(S["setpoint"]) & np.isfinite(S["la_act"])
                    & np.isfinite(S["la_pose"]) & np.isfinite(S["out"]),
                usable=V.usable(S))


def windows(N, vmin=VMIN, vmax=99.0, nperseg=NPERSEG, overlap=0.5, minrun=MINRUN, keys=("X", "Z", "M", "Y", "U")):
    """Hann-windowed rFFT of every node over overlapping windows inside contiguous engaged hands-off runs.
    Yields (freqs, dict of complex spectra, median speed). Nothing is concatenated across a run boundary."""
    m = N["usable"] & N["fin"] & (N["v"] >= vmin) & (N["v"] < vmax)
    hop = int(nperseg * (1 - overlap))
    w = np.hanning(nperseg)
    fr = np.fft.rfftfreq(nperseg, 1.0 / FS)
    out = {k: [] for k in keys}
    vs = []
    for a, b in V.runs(m, N["t"], min_s=minrun):
        for k0 in range(a, b - nperseg + 1, hop):
            sl = slice(k0, k0 + nperseg)
            for k in keys:
                s = N[k][sl]
                out[k].append(np.fft.rfft((s - s.mean()) * w))
            vs.append(float(np.median(N["v"][sl])))
    if not vs:
        return fr, {k: np.zeros((0, len(fr)), complex) for k in keys}, np.zeros(0)
    return fr, {k: np.asarray(out[k]) for k in keys}, np.asarray(vs)


def bandsel(fr, f1=F1, f2=F2):
    return (fr >= f1) & (fr <= f2)


def metric(Xw, Ew, sel):
    """J = sum|E|^2 / sum|X|^2 over the band, pooled over windows. ONE denominator."""
    num = float(np.sum(np.abs(Ew[:, sel]) ** 2))
    den = float(np.sum(np.abs(Xw[:, sel]) ** 2))
    return num / den, num, den


def _self_test():
    """Positive controls, all with closed-form answers.
    1. windows(): a pure tone of known amplitude lands in the right bin.
    2. metric(): a known first-order lag between X and Y gives the analytic band ratio.
    3. the residual identity E = A + V*D telescopes exactly for any V."""
    rng = np.random.default_rng(7)
    n = NPERSEG
    fr = np.fft.rfftfreq(n, 1 / FS)
    # (2) analytic check of the band ratio for Y = g*X with a known real gain
    X = rng.standard_normal((5, len(fr))) + 1j * rng.standard_normal((5, len(fr)))
    g = 0.8
    E = X * (1 - g)
    sel = bandsel(fr)
    J, _, _ = metric(X, E, sel)
    assert abs(J - (1 - g) ** 2) < 1e-12, J
    # (3) residual telescoping
    D = rng.standard_normal(X.shape) + 1j * rng.standard_normal(X.shape)
    Vh = rng.standard_normal(len(fr)) + 1j * rng.standard_normal(len(fr))
    A = E - Vh[None, :] * D
    assert np.allclose(A + Vh[None, :] * D, E, rtol=0, atol=1e-12)
    # (1) tone
    t = np.arange(n) / FS
    f0 = fr[40]
    N = dict(t=t, v=np.full(n, 20.0), X=np.sin(2 * np.pi * f0 * t), Z=np.zeros(n), M=np.zeros(n),
             Y=np.zeros(n), U=np.zeros(n), fin=np.ones(n, bool), usable=np.ones(n, bool))
    f2_, sp, _ = windows(N, minrun=0.0, nperseg=n, overlap=0.5)
    k = int(np.argmax(np.abs(sp["X"][0])))
    assert k == 40, k
    # lsf table spot values (latcontrol_torque.py:339)
    assert abs(lsf(20.0) - (8.0 / 20.0) ** 2) < 1e-12
    assert abs(lsf(15.0) - (9.25 / 15.0) ** 2) < 1e-12
    return "advlib self-test OK: band ratio, residual telescoping, tone bin, lsf table"


if __name__ == "__main__":
    print(_self_test())
