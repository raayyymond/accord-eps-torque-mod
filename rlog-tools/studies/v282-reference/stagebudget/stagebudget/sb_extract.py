# -*- coding: utf-8 -*-
"""Stage 1: per-window spectra of EVERY NODE on the chain, so the budget is one arithmetic pass.

Nodes (all logged, or -- for Z0 only -- an exactly validated replay of a logged software stage):

  X   model desired lateral accel      controlsState.desiredCurvature * vEgo^2          m/s^2
  Z0  pre-ref-filter setpoint          replay of latcontrol_torque :303-317 (sb_lib)     m/s^2
  Z   logged setpoint                  controlsState...torqueState.desiredLateralAccel   m/s^2
  U   command                          -pid_log.output == output_torque, [-1,1]          torque
        SIGN, MEASURED: corr(X, pid_log.output) = -0.62..-0.88 and corr(X, e4) = +0.63..+0.88 on
        every route, and e4 = -4089 * pid_log.output, so output_torque = -pid_log.output is the
        node with the same polarity as the demand.  U is defined that way.
  M   wheel angle, in demand units     controlsState...torqueState.actualLateralAccel    m/s^2
        == -VM.calc_curvature(radians(steeringAngle-offset), v, roll) * v^2, i.e. the WHEEL ANGLE
        node expressed in lateral accel -- and it is exactly the signal the controller feeds back.
  W   wheel angle, raw                 -(steeringAngleDeg - angleOffsetDeg)              deg
        the same node without the roll compensation and the v^2 scaling (cross-check on M).
  Y   achieved lateral accel           livePose angularVelocityDevice.z * vEgo            m/s^2
  T   column torque sensor             carState.steeringTorque (raw counts)   EXPLORATORY ONLY

Windows: v282cmp.runs + usable, never crossing a clock gap / disengagement / steeringPressed frame,
>=50% of samples inside their own speed bin (the fraction is stored per window), 75% overlap, identical length and taper for both builds.

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python sb_extract.py
"""
import sys

import numpy as np

import sb_lib as L
import v282cmp as V

FMAX = 2.5
SCALES = [40.96, 20.48, 10.24]
OVERLAP = 0.75          # more cells; independence is accounted as n*(1-OVERLAP)
NODES = ["X", "Z0", "Z", "U", "M", "W", "Y", "T"]


def win_spectra(sig, nb):
    w = np.hanning(len(sig[0]))
    return [np.fft.rfft((np.nan_to_num(s) - np.nan_to_num(s).mean()) * w)[:nb] for s in sig]


def main():
    store = {s: {k: [] for k in NODES} for s in SCALES}
    for s in SCALES:
        store[s]["meta"] = []
    for rk, (grp, cm, rf) in sorted(L.ROUTES.items()):
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            print(f"  {rk}: NO CACHE"); continue
        S = L.load_route(rk)
        cfg = L.COMMIT[cm]
        Z0, Zh, okrep, cr, cf = L.replay_setpoint(S, cfg["jerk_hz"], rf if cfg["ref_block"] else None)
        sig = dict(X=S["model"], Z0=Z0, Z=S["setpoint"], U=-S["out"], M=S["la_act"],
                   W=-(S["sa"] - np.nan_to_num(S["aoff"])), Y=S["la_pose"], T=S["storque"])
        fin = np.ones(len(S["t"]), bool)
        for k in ("X", "Z", "U", "M", "W", "Y"):
            fin &= np.isfinite(sig[k])
        u_all = V.usable(S) & okrep & fin
        nw = {s: 0 for s in SCALES}
        for Wn in SCALES:
            n = int(round(Wn * L.FS))
            hop = int(round(n * (1 - OVERLAP)))
            nb = int(np.floor(FMAX * Wn)) + 1
            for a, b in V.runs(u_all, S["t"], min_s=Wn):
                for k in range(a, b - n + 1, hop):
                    sl = slice(k, k + n)
                    vv = S["v"][sl]
                    vm = float(np.median(vv))
                    si = next((i for i, (lo, hi) in enumerate(L.SPD) if lo <= vm < hi), None)
                    if si is None:
                        continue
                    lo, hi = L.SPD[si]
                    inbin = float(np.mean((vv >= lo) & (vv < hi)))
                    if inbin < 0.50:      # stored per window; gate at 0.80 downstream if wanted
                        continue
                    sp = win_spectra([sig[c][sl] for c in NODES], nb)
                    for c, v_ in zip(NODES, sp):
                        store[Wn][c].append(v_)
                    am = np.abs(np.nan_to_num(sig["X"][sl]))
                    aw = np.abs(np.nan_to_num(sig["W"][sl]))
                    store[Wn]["meta"].append(
                        (rk, grp, si, vm, float(np.median(am)), float(np.percentile(am, 95)),
                         float(np.median(aw)), float(np.percentile(aw, 95)),
                         float(np.mean(np.abs(np.nan_to_num(sig["U"][sl])) >= 0.995)),
                         float(np.mean(S["sat"][sl])), float(np.mean(cr[sl])),
                         float(np.median(S["lat_delay"][sl])), inbin))
                    nw[Wn] += 1
        print(f"  {rk} {grp:8s} windows " + " ".join(f"{s}:{nw[s]}" for s in SCALES), flush=True)
        del S, sig, Z0, Zh

    for Wn in SCALES:
        d = store[Wn]
        if not d["X"]:
            print(f"  W={Wn}: no windows"); continue
        kw = {c: np.asarray(d[c]) for c in NODES}
        m = d["meta"]
        np.savez_compressed(
            L.HERE / "out" / f"spec_{Wn:.2f}.npz",
            route=np.array([x[0] for x in m]), group=np.array([x[1] for x in m]),
            sbin=np.array([x[2] for x in m], dtype=int), v=np.array([x[3] for x in m]),
            am_med=np.array([x[4] for x in m]), am_p95=np.array([x[5] for x in m]),
            aw_med=np.array([x[6] for x in m]), aw_p95=np.array([x[7] for x in m]),
            rail=np.array([x[8] for x in m]), sat=np.array([x[9] for x in m]),
            clipraw=np.array([x[10] for x in m]), lagD=np.array([x[11] for x in m]),
            inbin=np.array([x[12] for x in m]),
            WIN=np.array([Wn]), **kw)
        print(f"  wrote spec_{Wn:.2f}.npz  {len(m)} windows x {kw['X'].shape[1]} bins x {len(NODES)} nodes")


def self_test():
    """Positive control on the window machinery: a known gain and a known lag must come back, and the
    3-leg CHAIN of two known stages must telescope exactly to the end-to-end transfer."""
    rng = np.random.default_rng(3)
    t = np.arange(0, 900, 1 / L.FS)
    x = V.lowpass(rng.standard_normal(len(t)), 0.9) * 2.0
    lag1, lag2 = 12, 25
    z = 0.7 * np.concatenate([np.zeros(lag1), x[:-lag1]])
    y = 1.3 * np.concatenate([np.zeros(lag2), z[:-lag2]]) + 0.05 * rng.standard_normal(len(t))
    Wn = 10.24; n = int(Wn * L.FS); nb = int(np.floor(FMAX * Wn)) + 1
    fr = np.arange(nb) / Wn
    Pxx = np.zeros(nb); Pxz = np.zeros(nb, complex); Pxy = np.zeros(nb, complex)
    for k in range(0, len(t) - n + 1, n // 2):
        Xw, Zw, Yw = win_spectra([x[k:k + n], z[k:k + n], y[k:k + n]], nb)
        Pxx += np.abs(Xw) ** 2; Pxz += np.conj(Xw) * Zw; Pxy += np.conj(Xw) * Yw
    s = (fr >= 0.15) & (fr < 0.6)
    Tz = Pxz[s] / Pxx[s]; Ty = Pxy[s] / Pxx[s]
    g1 = np.abs(Tz); g2 = np.abs(Ty / Tz)
    assert abs(float(np.average(g1, weights=Pxx[s])) - 0.7) < 0.02
    assert abs(float(np.average(g2, weights=Pxx[s])) - 1.3) < 0.03
    assert np.allclose(g1 * g2, np.abs(Ty), rtol=1e-12)          # the legs telescope exactly
    ph1 = np.unwrap(np.angle(Tz)); ph2 = np.unwrap(np.angle(Ty / Tz))
    tau1 = -np.polyfit(2 * np.pi * fr[s], ph1, 1)[0]
    tau2 = -np.polyfit(2 * np.pi * fr[s], ph2, 1)[0]
    assert abs(tau1 - 0.12) < 0.012, tau1
    assert abs(tau2 - 0.25) < 0.012, tau2
    print(f"sb_extract self-test OK: leg gains 0.70/1.30 and leg lags {tau1*1e3:.0f}/{tau2*1e3:.0f} ms "
          f"recovered for a true 120/250 ms; legs telescope to the end-to-end transfer exactly")


if __name__ == "__main__":
    self_test()
    sys.exit(main())
