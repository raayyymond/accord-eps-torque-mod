# -*- coding: utf-8 -*-
"""Stage 1 of the |H| surface: turn every laterally-engaged route into a store of PER-WINDOW spectra.

What is stored, per window, per window-length scale:
  X(f) = model desired lateral accel  (cs_des_curv * v^2)      -- the GOAL's reference
  Y(f) = achieved lateral accel       (livePose yaw_z * v)      -- independent of the EPS mode
  Z(f) = the controller's shaped setpoint (cs_la_des)           -- to split reference shaping from plant
  U(f) = the wire command (pid_log.output, [-1,1])              -- to see where the command rails
plus per-window metadata (speed, |model| operating point, |angle|, rail fraction, seconds).

Everything downstream (cells, strata, coherence and noise floors, route-cluster CIs, exposure) is
arithmetic on this store, so one definition of a window is used everywhere and both EPS modes get the
IDENTICAL window length and taper inside a cell (unequal df/leakage between builds would fake a gap).

Windows never cross a clock gap, a disengagement or a steeringPressed frame (v282cmp.runs + usable).

MEASUREMENT, not a model: input and output are both logged.  ANALYSIS ONLY, read-only.
usage: python extract.py
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

FS = V.FS
FMAX = 5.0                      # store bins to 5 Hz; the shake band tops out at 4
SCALES = [40.96, 20.48, 10.24, 5.12]
OVERLAP = 0.5                   # 50% window overlap: more windows, but only ~half are independent
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
GROUPS = {  # route -> group.  Group from each route's OWN initData (params_all.json), not from a label.
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
    "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4", "00000074--2bf17ca67d": "T4",
    "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
    "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2",
}


def win_spectra(x, y, z, u, nb):
    """Hann-tapered, mean-removed rfft of one window, truncated to nb bins. Pxy convention conj(X)*Y:
    for y(t) = g*x(t-tau) the cross-phase is -2*pi*f*tau, i.e. NEGATIVE phase = output LAGS."""
    w = np.hanning(len(x))
    out = []
    for s in (x, y, z, u):
        s = np.nan_to_num(s)
        out.append(np.fft.rfft((s - s.mean()) * w)[:nb])
    return out


def main():
    store = {s: dict(X=[], Y=[], Z=[], U=[], meta=[]) for s in SCALES}
    for rk, grp in sorted(GROUPS.items()):
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            print(f"  {rk}: NO CACHE, skipped", flush=True)
            continue
        S = V.load(rk)
        ok = np.isfinite(S["model"]) & np.isfinite(S["la_pose"]) & np.isfinite(S["v"])
        u_all = V.usable(S) & ok
        nw = {s: 0 for s in SCALES}
        for W in SCALES:
            n = int(round(W * FS))
            hop = int(round(n * (1 - OVERLAP)))
            nb = int(np.floor(FMAX * W)) + 1
            for a, b in V.runs(u_all, S["t"], min_s=W):
                for k in range(a, b - n + 1, hop):
                    sl = slice(k, k + n)
                    vv = S["v"][sl]
                    vm = float(np.median(vv))
                    si = next((i for i, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
                    if si is None:
                        continue
                    lo, hi = SPD[si]
                    if float(np.mean((vv >= lo) & (vv < hi))) < 0.80:   # window must live in its bin
                        continue
                    X, Y, Z, U = win_spectra(S["model"][sl], S["la_pose"][sl], S["setpoint"][sl], S["out"][sl], nb)
                    store[W]["X"].append(X); store[W]["Y"].append(Y)
                    store[W]["Z"].append(Z); store[W]["U"].append(U)
                    am = np.abs(np.nan_to_num(S["model"][sl])); asa = np.abs(np.nan_to_num(S["sa"][sl]))
                    store[W]["meta"].append((rk, grp, si, vm, float(np.median(am)), float(np.percentile(am, 95)),
                                             float(np.median(asa)), float(np.percentile(asa, 95)),
                                             float(np.mean(np.abs(np.nan_to_num(S["out"][sl])) >= 0.995)),
                                             float(np.mean(S["sat"][sl])), W))
                    nw[W] += 1
        print(f"  {rk} {grp:8s} windows " + " ".join(f"{W}:{nw[W]}" for W in SCALES), flush=True)
        del S

    HERE.mkdir(parents=True, exist_ok=True)
    for W in SCALES:
        d = store[W]
        if not d["X"]:
            print(f"  W={W}: no windows"); continue
        np.savez_compressed(HERE / f"spec_{W:.2f}.npz",
                            X=np.asarray(d["X"]), Y=np.asarray(d["Y"]),
                            Z=np.asarray(d["Z"]), U=np.asarray(d["U"]),
                            route=np.array([m[0] for m in d["meta"]]),
                            group=np.array([m[1] for m in d["meta"]]),
                            sbin=np.array([m[2] for m in d["meta"]], dtype=int),
                            v=np.array([m[3] for m in d["meta"]]),
                            am_med=np.array([m[4] for m in d["meta"]]),
                            am_p95=np.array([m[5] for m in d["meta"]]),
                            sa_med=np.array([m[6] for m in d["meta"]]),
                            sa_p95=np.array([m[7] for m in d["meta"]]),
                            rail=np.array([m[8] for m in d["meta"]]),
                            sat=np.array([m[9] for m in d["meta"]]),
                            W=np.array([W]))
        print(f"  wrote spec_{W:.2f}.npz  {len(d['X'])} windows, {np.asarray(d['X']).shape[1]} bins")


def self_test():
    """Positive control: a known gain 0.8 and lag 0.25 s must come back out of the same window machinery,
    and the band |H| must agree with v282cmp.band_H (which uses scipy welch/csd) to <2%."""
    rng = np.random.default_rng(0)
    t = np.arange(0, 600, 1 / FS)
    x = V.lowpass(rng.standard_normal(len(t)), 0.8) * 3
    lagN = 25
    y = 0.8 * np.concatenate([np.zeros(lagN), x[:-lagN]])
    W = 10.24; n = int(W * FS); nb = int(np.floor(FMAX * W)) + 1
    fr = np.arange(nb) / W
    Pxx = np.zeros(nb); Pxy = np.zeros(nb, complex); Pyy = np.zeros(nb)
    for k in range(0, len(t) - n + 1, n // 2):
        Xw, Yw, _, _ = win_spectra(x[k:k + n], y[k:k + n], y[k:k + n], y[k:k + n], nb)
        Pxx += np.abs(Xw) ** 2; Pyy += np.abs(Yw) ** 2; Pxy += np.conj(Xw) * Yw
    s = (fr >= 0.1) & (fr < 0.6)
    H = float(np.average(np.abs(Pxy[s]) / Pxx[s], weights=Pxx[s]))
    ph = np.unwrap(np.angle(Pxy[s]))
    tau = float(-np.polyfit(2 * np.pi * fr[s], ph, 1)[0])
    ref = V.band_H([(x, y)], 0.1, 0.6)
    assert abs(H - 0.8) < 0.02, H
    assert abs(tau - 0.25) < 0.01, tau
    assert abs(H - ref["H"]) < 0.02, (H, ref["H"])
    print(f"self-test OK: |H| {H:.4f} (band_H {ref['H']:.4f}), group delay {tau*1000:.1f} ms for a true 250 ms, "
          f"phase sign = negative when the output lags")


if __name__ == "__main__":
    self_test()
    main()
