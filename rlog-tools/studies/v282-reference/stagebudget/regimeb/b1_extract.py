# -*- coding: utf-8 -*-
"""REGIME B stage 1: per-window multi-channel spectra, with DISENGAGED and HANDS-ON control classes.

Regime B is 0.60-1.20 Hz, large demand, 8-22 m/s, where the surface stream measured |H| 1.10 -> 2.50
(8-15 m/s) and 1.23 -> 1.98 (15-22) against V282, with the TIMING better and ~45% of the excess error
power incoherent with the demand.  To NAME it I need channels the surface store does not carry, so that
the object can be located IN THE CHAIN and compared against a natural control:

  X  model desired lateral accel     cs_des_curv * v^2            the demand
  Z  the controller's shaped setpoint cs_la_des                   post delay-canceller + ref filter
  U  the wire command                cs_out  ([-1,1] torque/rate request)
  A  WHEEL ANGLE                     sa_deg                       is the object in the wheel?
  R  steering RATE                   sr_deg (deg/s)               the shake channel of the kit
  Y  achieved lateral accel          livePose yaw_z * v           is it in the yaw?
  M  the controller's own measured lateral accel  cs_la_act        = wheel angle in lat-accel units

Window CLASSES, so the loop can be opened as a natural control:
  E  laterally engaged, hands OFF   (active & ~pressed)   -- the regime under study
  P  laterally engaged, hands ON    (active &  pressed)   -- driver in the loop
  D  NOT laterally engaged          (~active)             -- loop open (driver steers)

MEASUREMENT of logged input against logged output.  No model, no simulator, no prediction.
ANALYSIS ONLY, read-only.  usage: python b1_extract.py
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

FS = V.FS
FMAX = 5.0
W = 10.24                      # 1024 samples, df 0.0977 Hz -> 6 bins in 0.60-1.20 Hz (same as the surface)
OVERLAP = 0.5
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
GROUPS = {
    "00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
    "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
    "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
    "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4", "00000074--2bf17ca67d": "T4",
    "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
    "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2",
}
CH = ["X", "Z", "U", "A", "R", "Y", "M"]


def win_spectra(sigs, nb):
    w = np.hanning(len(sigs[0]))
    return [np.fft.rfft((np.nan_to_num(s) - np.nan_to_num(s).mean()) * w)[:nb] for s in sigs]


def main():
    n = int(round(W * FS)); hop = int(round(n * (1 - OVERLAP))); nb = int(np.floor(FMAX * W)) + 1
    store = {c: [] for c in CH}; meta = []
    for rk, grp in sorted(GROUPS.items()):
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            print(f"  {rk}: NO CACHE, skipped", flush=True); continue
        S = V.load(rk)
        ok = np.isfinite(S["model"]) & np.isfinite(S["la_pose"]) & np.isfinite(S["v"]) & np.isfinite(S["sa"])
        classes = dict(E=S["active"] & ~S["pressed"] & ok,
                       P=S["active"] & S["pressed"] & ok,
                       D=(~S["active"]) & ok)
        sig = [S["model"], S["setpoint"], S["out"], S["sa"], S["sr"], S["la_pose"], S["la_act"]]
        cnt = {}
        for cl, m in classes.items():
            c = 0
            for a, b in V.runs(m, S["t"], min_s=W):
                for k in range(a, b - n + 1, hop):
                    sl = slice(k, k + n)
                    vv = S["v"][sl]; vm = float(np.median(vv))
                    si = next((i for i, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
                    if si is None:
                        continue
                    lo, hi = SPD[si]
                    if float(np.mean((vv >= lo) & (vv < hi))) < 0.80:
                        continue
                    sp = win_spectra([s[sl] for s in sig], nb)
                    for cc, ss in zip(CH, sp):
                        store[cc].append(ss)
                    am = np.abs(np.nan_to_num(S["model"][sl])); asa = np.abs(np.nan_to_num(S["sa"][sl]))
                    meta.append((rk, grp, cl, si, vm,
                                 float(np.percentile(am, 95)), float(np.median(am)),
                                 float(np.percentile(asa, 95)), float(np.median(asa)),
                                 float(np.mean(np.abs(np.nan_to_num(S["out"][sl])) >= 0.995)),
                                 float(np.nanmedian(np.abs(np.nan_to_num(S["storque"][sl])))),
                                 float(S["t"][k])))
                    c += 1
            cnt[cl] = c
        print(f"  {rk} {grp:8s} " + " ".join(f"{cl}:{cnt[cl]}" for cl in ("E", "P", "D")), flush=True)
        del S
    md = np.array(meta, dtype=object)
    np.savez_compressed(HERE / "b1_spec.npz",
                        **{c: np.asarray(store[c]) for c in CH},
                        route=np.array([m[0] for m in meta]), group=np.array([m[1] for m in meta]),
                        cls=np.array([m[2] for m in meta]), sbin=np.array([m[3] for m in meta], dtype=int),
                        v=np.array([m[4] for m in meta], dtype=float),
                        am_p95=np.array([m[5] for m in meta], dtype=float),
                        am_med=np.array([m[6] for m in meta], dtype=float),
                        sa_p95=np.array([m[7] for m in meta], dtype=float),
                        sa_med=np.array([m[8] for m in meta], dtype=float),
                        rail=np.array([m[9] for m in meta], dtype=float),
                        dtq=np.array([m[10] for m in meta], dtype=float),
                        t0=np.array([m[11] for m in meta], dtype=float),
                        W=np.array([W]))
    print(f"  wrote b1_spec.npz  {len(meta)} windows x {len(CH)} channels x {nb} bins")
    del md


def self_test():
    """Positive control on the SAME window machinery: a known gain 0.8 and lag 0.25 s must come back,
    and the 0.60-1.20 Hz band |H| of a known second-order resonance must recover its known peak."""
    rng = np.random.default_rng(0)
    t = np.arange(0, 900, 1 / FS)
    x = V.lowpass(rng.standard_normal(len(t)), 1.5) * 3
    lagN = 25
    y = 0.8 * np.concatenate([np.zeros(lagN), x[:-lagN]])
    n = int(W * FS); nb = int(np.floor(FMAX * W)) + 1
    fr = np.arange(nb) / W
    Pxx = np.zeros(nb); Pxy = np.zeros(nb, complex)
    for k in range(0, len(t) - n + 1, n // 2):
        Xw, Yw = win_spectra([x[k:k + n], y[k:k + n]], nb)
        Pxx += np.abs(Xw) ** 2; Pxy += np.conj(Xw) * Yw
    s = (fr >= 0.3) & (fr < 1.2)
    H = float(np.average(np.abs(Pxy[s]) / Pxx[s], weights=Pxx[s]))
    tau = float(-np.polyfit(2 * np.pi * fr[s], np.unwrap(np.angle(Pxy[s])), 1)[0])
    assert abs(H - 0.8) < 0.02, H
    assert abs(tau - 0.25) < 0.01, tau
    # known resonance: 2nd-order, f0 = 0.90 Hz, zeta = 0.15 -> peak |H| ~= 1/(2z) = 3.33 at ~0.88 Hz
    from scipy import signal as sg
    f0, z = 0.90, 0.15
    b, a = sg.bilinear([(2 * np.pi * f0) ** 2], [1, 2 * z * 2 * np.pi * f0, (2 * np.pi * f0) ** 2], fs=FS)
    yr = sg.lfilter(b, a, x)
    Pxx = np.zeros(nb); Pxy = np.zeros(nb, complex)
    for k in range(0, len(t) - n + 1, n // 2):
        Xw, Yw = win_spectra([x[k:k + n], yr[k:k + n]], nb)
        Pxx += np.abs(Xw) ** 2; Pxy += np.conj(Xw) * Yw
    Hb = np.abs(Pxy) / np.maximum(Pxx, 1e-300)
    kpk = int(np.argmax(np.where((fr > 0.3) & (fr < 2.0), Hb, 0)))
    assert abs(fr[kpk] - 0.88) < 0.12, (fr[kpk], Hb[kpk])
    assert abs(Hb[kpk] - 3.33) / 3.33 < 0.15, Hb[kpk]
    print(f"self-test OK: gain {H:.4f}/0.8, lag {tau*1000:.1f}/250 ms; known 0.90 Hz zeta 0.15 resonance "
          f"recovered at {fr[kpk]:.3f} Hz peak {Hb[kpk]:.2f} (true 3.33)")


if __name__ == "__main__":
    self_test()
    main()
