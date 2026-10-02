# -*- coding: utf-8 -*-
r"""m4_relay.py -- M4 mechanism (7): the fork's O1 override as a RELAY.  Event-locked averages around every O1 ONSET
on route 79 (V298), on the 100 Hz grid, sign-normalised by the turn direction (sign of the 0.5 s mean wheel rate):
the 0x18F wheel rate, its acceleration, the 0x18F torque bar (wire counts, /1.024 = steeringTorque), the setpoint
error theta_sp - theta, and the 0x1AB tap (LSB, T/8; motor torque on the wheel u = -T, tap sign = +sign(raw)).

    python m4_relay.py            (~3 s)

Question: is the cycle  STALL (wheel slows) -> error grows at the fork's rate limit -> motor torque -> SURGE (wheel
accelerates; the bar spikes) -> O1 (|steeringTorque| > 600) -> setpoint := theta + 0.06 w (the error collapses) ->
torque collapses -> STALL ?   The averages show the ORDER of those events; the bar at onset is compared with the
hands-off inertia+friction fit (bar = J alpha + c w + F sgn w + c0, fitted on engaged |bar| < 450 frames).
"""
from __future__ import annotations

import json

import numpy as np
from scipy import signal

import m4_common as C


def main():
    tm = C.timer()
    G = C.build_grid(C.TAG79)
    F = C.fork_cache()
    L = C.limiter_reconstruct(F)
    t = G["t"]
    stg = C.zoh(L["t"], L["stage"], t, fill=0)
    o1 = (stg == 3) & G["eng"]
    on = np.flatnonzero(o1[1:] & ~o1[:-1]) + 1
    w = G["w18"]
    mbar = np.convolve(w, np.ones(50) / 50, "same")
    sg = np.sign(mbar)
    a = np.gradient(signal.sosfiltfilt(signal.butter(2, 8, fs=C.FS, output="sos"), w)) * C.FS
    m = G["eng"] & (np.abs(G["bar"]) < 450)
    X = np.c_[a, w, np.sign(w), np.ones(len(w))]
    beta = np.linalg.lstsq(X[m], G["bar"][m], rcond=None)[0]
    lags = np.arange(-25, 26)
    res = {}
    for nm, sel in (("all_onsets", np.ones(len(on), bool)),
                    ("turning_onsets(|mbar|>=10)", np.abs(mbar[on]) >= 10),
                    ("v<10", G["vego"][on] < 10), ("v>=10", G["vego"][on] >= 10)):
        oo = on[sel & (on > 30) & (on < len(t) - 30)]
        if len(oo) < 5:
            continue
        idx = oo[:, None] + lags[None, :]
        s = sg[oo][:, None]
        prof = {}
        for key, x in (("w18", w), ("alpha", a), ("bar", G["bar"]), ("err", G["err"]), ("tap", G["tap"]),
                       ("pred_bar", X @ beta)):
            prof[key] = (np.mean(x[idx] * s, 0)).round(2).tolist()
        prof["n"] = int(len(oo))
        prof["o1_frac"] = np.mean(o1[idx], 0).round(2).tolist()
        res[nm] = prof
    res["lags_s"] = (lags / C.FS).tolist()
    res["bar_fit"] = beta.tolist()
    # at each onset: bar vs predicted, sign agreement of bar with motor torque direction (-tap) and with alpha
    oo = on[(on > 5) & (on < len(t) - 5)]
    pk = np.array([G["bar"][i - 2:i + 3][np.argmax(np.abs(G["bar"][i - 2:i + 3]))] for i in oo])
    pr = (X @ beta)[oo]
    res["onset_bar_over_pred_p50"] = float(np.median(np.abs(pk) / np.maximum(np.abs(pr), 50)))
    res["onset_sign_bar_eq_alpha"] = float(np.mean(np.sign(pk) == np.sign(a[oo])))
    res["onset_sign_bar_eq_motor"] = float(np.mean(np.sign(pk) == np.sign(-G["tap"][oo])))
    res["onset_sign_bar_eq_turn"] = float(np.mean(np.sign(pk) == sg[oo]))
    res["onset_sign_bar_eq_rate"] = float(np.mean(np.sign(pk) == np.sign(w[oo])))
    res["n_onsets"] = int(len(on))
    res["wall_s"] = tm()
    with open(C.OUT / "m4_relay.json", "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    print("M4 O1 RELAY, event-locked on O1 onsets (wall %.1f s); bar fit %s" % (res["wall_s"], np.round(beta, 3)))
    sel_l = [-20, -15, -10, -6, -4, -2, 0, 2, 4, 6, 10, 15, 20]
    print("  lag (s):" + "".join("%7.2f" % (q / 100) for q in sel_l))
    for nm, prof in res.items():
        if not isinstance(prof, dict):
            continue
        print(" [%s] n %d" % (nm, prof["n"]))
        for key in ("w18", "alpha", "bar", "pred_bar", "err", "tap", "o1_frac"):
            print("  %-8s" % key + "".join("%7.1f" % prof[key][q + 25] for q in sel_l))
    print("  onset |bar| / hands-off prediction p50 %.2f ; sign(bar)=sign(alpha) %.2f  =sign(-tap, motor) %.2f  =turn dir %.2f  =sign(rate) %.2f" % (
        res["onset_bar_over_pred_p50"], res["onset_sign_bar_eq_alpha"], res["onset_sign_bar_eq_motor"],
        res["onset_sign_bar_eq_turn"], res["onset_sign_bar_eq_rate"]))


if __name__ == "__main__":
    main()
