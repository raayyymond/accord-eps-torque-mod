"""Positive control for the lane-derived instruments: do y (offset) and psi (heading) obey the kinematics of the
independently measured yaw (la_pose)?  y'' = a - v^2 k_road ; psi' = a/v - v k_road.  Band 0.08-0.25 Hz, per-bin
cross-spectra pooled over straight runs. Expected, if the signs in fsr_reduce are right:
  H(apose->y)*w^2 : |.| ~ 1, phase ~ +-180 ;  H(apose->psi)*w*v : |.| ~ 1, phase ~ -90 ;  H(psi->y)*w/v : phase -90."""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); import v282cmp as V
FS2 = 10.0; tier = sys.argv[1] if len(sys.argv) > 1 else "S1"; NPS = 256
acc = {}
for route, meta in V.ROUTES.items():
    Z = np.load(HERE / "reduced" / f"{route}.npz", allow_pickle=True)
    for r in Z["runs"][0][tier]:
        s = r["sig"]
        if len(s["ad"]) < NPS or r["lane_ok"] < 0.8: continue
        g = "V282" if meta["group"].startswith("V282") else "TORQUE"
        A = acc.setdefault(g, dict(sec=0.0))
        v = np.mean(s["v"])
        for x, y, scale in (("apose", "y", "w2"), ("apose", "psi", "wv"), ("psi", "y", "w/v"), ("ad", "y", "w2"), ("apose", "py10", "w2")):
            f, pxy = signal.csd(s[x], s[y], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
            _, pxx = signal.welch(s[x], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
            _, pyy = signal.welch(s[y], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
            w = 2 * np.pi * f
            k = {"w2": w ** 2, "wv": w * v, "w/v": w / v}[scale]
            key = f"{x}>{y}"
            A.setdefault(key, [0, 0, 0]); A[key][0] = A[key][0] + pxy * k * r["sec"]; A[key][1] = A[key][1] + pxx * r["sec"]; A[key][2] = A[key][2] + pyy * k ** 2 * r["sec"]
        A["sec"] += r["sec"]
    del Z
for g, A in acc.items():
    print(g, "sec", round(A["sec"]))
    for key, val in A.items():
        if key == "sec": continue
        pxy, pxx, pyy = val
        s = (f >= 0.08) & (f < 0.25)
        H = np.abs(pxy[s]) / pxx[s]; coh = np.abs(pxy[s]) ** 2 / (pxx[s] * pyy[s])
        print(f"   {key:12s} |H|(scaled) {np.average(H, weights=pxx[s]):.2f} coh {np.average(coh, weights=pxx[s]):.2f} "
              f"phase {np.degrees(np.angle(pxy[s].sum())):+.0f}  per-bin phase {np.round(np.degrees(np.angle(pxy[s]))).astype(int).tolist()}")
