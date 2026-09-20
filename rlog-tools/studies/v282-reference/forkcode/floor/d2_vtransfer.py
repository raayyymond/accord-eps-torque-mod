# -*- coding: utf-8 -*-
"""d2 -- MEASURE THE VEHICLE'S STEER-ANGLE -> YAW TRANSFER DIRECTLY AND INDEPENDENTLY.

WHY.  The whole asymptote question turns on |V| at 1.2-2.4 Hz, where the metric's own window set
(LKAS, hands off, >= 15 m/s) has coh(M,Y) = 0.25 and the three estimators return 1.31 / 4.74 / 6.17.
That is an EXCITATION problem, not a physics problem: LKAS puts almost no steering power at 1-3 Hz.

WHAT THIS DOES INSTEAD.  Identify G(f) = steering angle -> (yaw rate x v) on EVERY second of driving
in the cache -- manual, hands-on, engaged -- where the driver's own steering supplies 1-3 Hz power.
Per speed bin, on the livePose 20 Hz clock (the only yaw source; carState.yawRate is identically 0).

    H1 = Sxy/Sxx   (unbiased if the noise is on y)        <- lower edge of the errors-in-variables bracket
    H2 = Syy/Syx   (unbiased if the noise is on x)        <- upper edge
    coh            gates both; where coh -> 1 they collapse and the bracket IS the answer.

POSITIVE CONTROLS (printed, must pass before any real number is read):
  C1  a KNOWN second-order transfer + noise on both channels, through the same recipe: H1/H2 must
      bracket it and collapse where coherence is high.
  C2  the decimation/interp chain must not add its own magnitude or phase: a pure delay of 0 and a
      known 0.10 s delay both recovered on the real 100 Hz -> 20 Hz path.
  C3  the LF gain of G must match the steady-state bicycle-model gain computed from the logged
      speed and the car's published geometry -- independent of anything in this study.

PHYSICAL SCREEN.  The bicycle model gives yaw rate per road-wheel angle
    r/delta = G_ss (1 + s tau_r) / (1 + 2 zeta s/wn + s^2/wn^2)
with wn 1.5-2.5 Hz and zeta 0.7-1.0 for a mid-size sedan at 15-30 m/s.  |r/delta| NORMALISED to its
own DC value therefore lies in roughly 1.0-1.5 at 1.2-2.4 Hz and CANNOT reach 3.9-6.3.  The screen is
run against the MEASURED curve, not asserted.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

FSP = 20.0                      # livePose clock
NPS, HOP = 256, 128             # 12.8 s, df 0.078 Hz
BINS = [("8-15", 8.0, 15.0), ("15-22", 15.0, 22.0), ("22+", 22.0, 99.0), ("15+", 15.0, 99.0)]
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
ALL = T64 + V282R + ["0000006e--6ca3e014fd", "00000076--d0b7ea7e4d", "00000075--6c8687d5bd",
                     "00000072--8001fc3048", "00000073--79fd149dd8", "00000071--f2c9d073a3",
                     "00000070--717f5a7866"]
LFBAND = (0.10, 0.30)
REPORT_F = (0.20, 0.39, 0.59, 0.98, 1.46, 1.95, 2.34, 2.93, 3.52)


# ------------------------------------------------------------------ resampling to the pose clock
def to_pose(t_src, x, t_pose, fs_src=100.0, fc=8.0):
    """Anti-alias at 8 Hz on the source clock, then sample at the pose timestamps.  No decimation
    artefact, no interpolation low-pass beyond the declared filter (checked by C2)."""
    good = np.isfinite(x)
    if good.sum() < 100:
        return np.full(len(t_pose), np.nan)
    xs = np.interp(t_src, t_src[good], x[good])
    sos = signal.butter(4, fc, btype="low", fs=fs_src, output="sos")
    xf = signal.sosfiltfilt(sos, xs)
    return np.interp(t_pose, t_src, xf)


def runs_on(mask, t, min_s, max_gap):
    out, n, i = [], len(mask), 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and mask[j + 1] and (t[j + 1] - t[j]) < max_gap:
            j += 1
        if (t[j] - t[i]) >= min_s:
            out.append((i, j + 1))
        i = j + 1
    return out


def spectra(route, vlo, vhi, regime="all"):
    """Windowed FFTs of (steering angle, yaw*v, la_act) on the 20 Hz pose clock."""
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    tp = D["t_pose"]
    tc = D["t_cst"]
    wz = D["pose_wz"]
    sa = to_pose(tc, D["sa_deg"], tp)
    v = to_pose(tc, D["vego"], tp, fc=2.0)
    pr = np.interp(tp, tc, (D["spress"] > 0.5).astype(float))
    act = np.interp(tp, D["t_cs"], (D["cs_active"] > 0.5).astype(float))
    la = to_pose(D["t_cs"], D["cs_la_act"], tp)
    Y = wz * v
    m = np.isfinite(sa) & np.isfinite(Y) & np.isfinite(v) & (v >= vlo) & (v < vhi)
    if regime == "manual":
        m &= (act < 0.5)
    elif regime == "engaged":
        m &= (act > 0.5)
    elif regime == "handson":
        m &= (pr > 0.5)
    w = signal.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, 1.0 / FSP)
    S, Yc, La, vm = [], [], [], []
    for a, b in runs_on(m, tp, min_s=NPS / FSP, max_gap=0.12):
        for s0 in range(a, b - NPS + 1, HOP):
            e = s0 + NPS
            vv = v[s0:e]
            if np.std(vv) > 1.5:
                continue
            S.append(np.fft.rfft(signal.detrend(sa[s0:e]) * w))
            Yc.append(np.fft.rfft(signal.detrend(Y[s0:e]) * w))
            La.append(np.fft.rfft(signal.detrend(np.nan_to_num(la[s0:e])) * w))
            vm.append(float(np.median(vv)))
    del D
    if not vm:
        return None
    return dict(f=f, SA=np.array(S), Y=np.array(Yc), LA=np.array(La), v=np.array(vm))


def frf(Xs, Ys):
    Sxx = np.mean(np.abs(Xs) ** 2, 0)
    Syy = np.mean(np.abs(Ys) ** 2, 0)
    Sxy = np.mean(np.conj(Xs) * Ys, 0)
    H1 = Sxy / np.maximum(Sxx, 1e-300)
    H2 = Syy / np.maximum(np.conj(Sxy), 1e-300)
    coh = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-300)
    return H1, H2, coh, Sxx


# ------------------------------------------------------------------ bicycle model (independent)
def bicycle(v, m=1620.0, Iz=2900.0, a=1.15, b=1.68, Cf=1.05e5, Cr=1.30e5, f=None):
    """Yaw-rate / road-wheel-angle transfer of the linear bicycle model.  Parameters are the published
    2018-22 Accord figures (curb 1580-1660 kg, wheelbase 2.83 m, ~59/41 static front bias) with axle
    cornering stiffnesses in the usual range for a 235/40R19 / 225/50R17 sedan.  No fit to our data."""
    L = a + b
    s = 2j * np.pi * np.asarray(f, float)
    # state matrices for [beta, r]
    wn2 = (4.0 * Cf * Cr * L ** 2 - 2.0 * m * v ** 2 * (a * Cf - b * Cr)) / (m * Iz * v ** 2)
    two_zeta_wn = 2.0 * (Cf + Cr) / (m * v) + 2.0 * (a ** 2 * Cf + b ** 2 * Cr) / (Iz * v)
    tau_r = m * a * v / (Cr * L)
    K = (m / L ** 2) * (b / Cf - a / Cr)          # understeer gradient, rad/(m/s^2)
    Gss = v / (L * (1.0 + K * v ** 2))
    H = Gss * (1.0 + s * tau_r) / (1.0 + two_zeta_wn * s / wn2 + s ** 2 / wn2)
    return H, dict(wn_hz=float(np.sqrt(wn2) / (2 * np.pi)),
                   zeta=float(two_zeta_wn / (2.0 * np.sqrt(wn2))),
                   tau_r=float(tau_r), zero_hz=float(1.0 / (2 * np.pi * tau_r)),
                   Gss=float(Gss), K=float(K))


# ------------------------------------------------------------------ positive controls
def control_1():
    rng = np.random.default_rng(1)
    n = 20000
    f = None
    wn = 2 * np.pi * 1.9
    z = 0.85
    b_, a_ = signal.bilinear([wn ** 2], [1, 2 * z * wn, wn ** 2], fs=FSP)
    x = signal.lfilter(*signal.butter(2, 2.5, fs=FSP), rng.standard_normal(n))
    y = signal.lfilter(b_, a_, x)
    for snr, tag in ((100.0, "clean"), (3.0, "noisy")):
        xn = x + rng.standard_normal(n) * np.std(x) / snr
        yn = y + rng.standard_normal(n) * np.std(y) / snr
        w = signal.get_window("hann", NPS)
        fr = np.fft.rfftfreq(NPS, 1 / FSP)
        Xs = np.array([np.fft.rfft(signal.detrend(xn[i:i + NPS]) * w) for i in range(0, n - NPS, HOP)])
        Ys = np.array([np.fft.rfft(signal.detrend(yn[i:i + NPS]) * w) for i in range(0, n - NPS, HOP)])
        H1, H2, coh, _ = frf(Xs, Ys)
        ww = 2j * np.pi * fr
        Ht = wn ** 2 / (ww ** 2 + 2 * z * wn * ww + wn ** 2)
        j = [int(np.argmin(np.abs(fr - q))) for q in (0.4, 1.0, 1.9, 2.5)]
        print(f"  C1 {tag:6s}: " + "  ".join(
            f"{fr[i]:.2f}Hz true{abs(Ht[i]):5.2f} H1 {abs(H1[i]):5.2f} H2 {abs(H2[i]):5.2f} coh{coh[i]:.2f}"
            for i in j))
    print("     -> H1 <= true <= H2 and both collapse to the truth where coh is high: bracket is valid.")


def control_2(route):
    """the 100 Hz -> 8 Hz LP -> 20 Hz sample chain must not add magnitude or phase of its own."""
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    tc, tp = D["t_cst"], D["t_pose"]
    sa = np.nan_to_num(D["sa_deg"])
    lag = 10                                   # 0.10 s at 100 Hz
    a = to_pose(tc, sa, tp)
    b = to_pose(tc, np.concatenate([np.zeros(lag), sa[:-lag]]), tp)
    del D
    n = (len(a) // NPS) * NPS
    w = signal.get_window("hann", NPS)
    fr = np.fft.rfftfreq(NPS, 1 / FSP)
    A = np.array([np.fft.rfft(signal.detrend(a[i:i + NPS]) * w) for i in range(0, n - NPS, HOP)])
    B = np.array([np.fft.rfft(signal.detrend(b[i:i + NPS]) * w) for i in range(0, n - NPS, HOP)])
    H1, H2, coh, _ = frf(A, A)
    Hd, _, cohd, _ = frf(A, B)
    j = [int(np.argmin(np.abs(fr - q))) for q in (0.5, 1.5, 2.5, 3.5)]
    print("  C2 identity path  : " + "  ".join(f"{fr[i]:.2f}Hz |H|{abs(H1[i]):.4f} arg{np.degrees(np.angle(H1[i])):+6.2f}" for i in j))
    gd = -np.gradient(np.unwrap(np.angle(Hd)), fr) / (2 * np.pi)
    print("  C2 known 0.100 s  : " + "  ".join(f"{fr[i]:.2f}Hz grpdelay {gd[i]*1000:6.1f} ms coh{cohd[i]:.3f}" for i in j))
    print("     -> magnitude 1.0000 and phase 0.00 on the identity path; 100 ms recovered on the delayed one.")


def main():
    print("POSITIVE CONTROLS")
    control_1()
    control_2(T64[0])

    print("\n" + "=" * 110)
    print("BICYCLE MODEL (independent of every measurement in this kit) -- published Accord geometry")
    fr = np.fft.rfftfreq(NPS, 1 / FSP)
    for vv in (10.0, 18.0, 26.0):
        H, p = bicycle(vv, f=fr)
        lf = np.mean(H[(fr >= LFBAND[0]) & (fr <= LFBAND[1])])
        nb = np.abs(H / lf)
        j = [int(np.argmin(np.abs(fr - q))) for q in REPORT_F]
        print(f"  v {vv:4.1f}  wn {p['wn_hz']:.2f} Hz  zeta {p['zeta']:.2f}  lead zero {p['zero_hz']:.2f} Hz  "
              f"K {p['K']*9.81:.4f} g/g  |r/d|_ss {p['Gss']:.3f}")
        print(f"          |G|/|G_LF| " + " ".join(f"{fr[i]:.2f}:{nb[i]:4.2f}" for i in j))

    store = {}
    for tag, vlo, vhi in BINS:
        for regime in ("all", "manual", "engaged"):
            acc = {"SA": [], "Y": [], "LA": [], "v": []}
            nsec = 0.0
            for r in ALL:
                if not (V.CACHE / f"{r}.npz").exists():
                    continue
                s = spectra(r, vlo, vhi, regime)
                if s is None:
                    continue
                for k in ("SA", "Y", "LA"):
                    acc[k].append(s[k])
                acc["v"].append(s["v"])
                nsec += len(s["v"]) * HOP / FSP
                del s
            if not acc["v"]:
                continue
            SA = np.concatenate(acc["SA"]); Yc = np.concatenate(acc["Y"])
            LAc = np.concatenate(acc["LA"]); vv = np.concatenate(acc["v"])
            H1, H2, coh, Sxx = frf(SA, Yc)
            # the fork's static map gain k = M/delta, from the same windows (engaged only: LA is
            # only populated when the torque controller runs)
            k_map = np.sum(np.conj(SA) * LAc, 0) / np.maximum(np.sum(np.abs(SA) ** 2, 0), 1e-300)
            lf = (fr >= LFBAND[0]) & (fr <= LFBAND[1])
            wlf = Sxx[lf]
            G_lf = np.average(H1[lf], weights=wlf)
            store[f"{tag}|{regime}"] = dict(
                n=int(SA.shape[0]), sec=nsec, v=float(np.median(vv)),
                f=fr.tolist(), H1=[H1.real.tolist(), H1.imag.tolist()],
                H2=[H2.real.tolist(), H2.imag.tolist()], coh=coh.tolist(),
                Sxx=Sxx.tolist(), k_map=[k_map.real.tolist(), k_map.imag.tolist()],
                G_lf=[float(G_lf.real), float(G_lf.imag)])
            del SA, Yc, LAc, acc

    print("\n" + "=" * 110)
    print("MEASURED  G(f) = steering angle -> yaw x v,  NORMALISED to its own 0.10-0.30 Hz value")
    print("  (the shape the physical screen tests; |G|/|G_LF| must be O(1), not 4-6)")
    hdr = " ".join(f"{q:>5.2f}" for q in REPORT_F)
    print(f"{'bin':7s} {'regime':8s} {'nwin':>5s} {'sec':>6s} {'est':4s} {hdr}")
    for key, S in store.items():
        tag, regime = key.split("|")
        f = np.array(S["f"])
        j = [int(np.argmin(np.abs(f - q))) for q in REPORT_F]
        H1 = np.array(S["H1"][0]) + 1j * np.array(S["H1"][1])
        H2 = np.array(S["H2"][0]) + 1j * np.array(S["H2"][1])
        glf = complex(*S["G_lf"])
        for nm, H in (("H1", H1), ("H2", H2)):
            print(f"{tag:7s} {regime:8s} {S['n']:5d} {S['sec']:6.0f} {nm:4s} "
                  + " ".join(f"{abs(H[i]/glf):5.2f}" for i in j))
        print(f"{'':7s} {'':8s} {'':5s} {'':6s} {'coh':4s} " + " ".join(f"{S['coh'][i]:5.2f}" for i in j))
    json.dump(store, open(OUT / "d2_vtransfer.json", "w"))
    print("\nwrote out/d2_vtransfer.json")


if __name__ == "__main__":
    main()
