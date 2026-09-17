"""Independent re-derivation of the s3_accel turn-texture-2hz finding.

Does NOT import s3turns.py (the finding's own detector). Uses only v282cmp.py (shared lib) plus a
DELIBERATELY DIFFERENT, simpler turn-window definition:
  window = active & ~pressed & (2.5 <= v < 15) & |ad_lowpassed| >= 25 deg, dilated by +/-0.3s, runs >= 1.0 s
This checks whether the magnitude claim (2-10 Hz steering-rate texture 2.5-3x higher on torque mode, dominant
~2.3 Hz, low coherence with desired rate) survives a totally independently built event mask, not just a
re-read of the same JSON.
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

# same opendbc bicycle model as s3turns.py (re-typed independently, not imported)
M = 3279 * 0.45359237 + 136.0; WB = 2.83; AF = 0.39 * WB; AR = WB - AF; TSF = 0.8467
_M0, _WB0 = 1326. + 136., 2.70; _AF0 = _WB0 * 0.4; _AR0 = _WB0 - _AF0
CF = 192150 * TSF * M / _M0 * (AR / WB) / (_AR0 / _WB0)
CR = 202500 * TSF * M / _M0 * (AF / WB) / (_AF0 / _WB0)
SF = M * (CF * AF - CR * AR) / (WB ** 2 * CF * CR)
SR_FIX = 16.33


def curv_to_angle(k, v):
    return -np.degrees(k * SR_FIX * WB * (1.0 - SF * v ** 2))


GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
HF_SOS = signal.butter(4, [2.0, 10.0], btype="band", fs=V.FS, output="sos")

hf_by_group = {"V282": [], "V282old": [], "TQ": []}
coh_by_group = {"V282": [], "V282old": [], "TQ": []}
fpk_by_group = {"V282": [], "V282old": [], "TQ": []}
sec_by_group = {"V282": [], "V282old": [], "TQ": []}

for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    v = np.nan_to_num(S["v"]); vv = np.maximum(v, 0.5)
    k_m = np.nan_to_num(S["model"]) / vv ** 2
    ad = curv_to_angle(k_m, v)
    adl = V.lowpass(ad, 1.0)
    mask = S["active"] & ~S["pressed"] & (v >= 2.5) & (v < 15) & (np.abs(adl) >= 25.0)
    # dilate 0.3 s each side (independent choice, not h0/h1 build/hold/unwind split)
    dil = int(0.3 * V.FS)
    if dil > 0 and mask.any():
        k = np.ones(2 * dil + 1, bool)
        mask = np.convolve(mask, k, mode="same") > 0
    mask = mask & S["active"] & ~S["pressed"]
    hf = signal.sosfiltfilt(HF_SOS, np.nan_to_num(S["sr"]))
    adr = V.deriv(ad)
    sr = np.nan_to_num(S["sr"])
    G = GM[meta["group"]]
    n_win = 0
    for a, b in V.runs(mask, S["t"], min_s=1.0):
        seg = hf[a:b]
        hf_by_group[G].append(float(np.sqrt(np.mean(seg ** 2))))
        n_win += (b - a)
        if b - a >= 256:
            x = adr[a:b] - np.mean(adr[a:b]); y = sr[a:b] - np.mean(sr[a:b])
            f, pxx = signal.welch(x, V.FS, nperseg=256, noverlap=128)
            _, pyy = signal.welch(y, V.FS, nperseg=256, noverlap=128)
            _, pxy = signal.csd(x, y, V.FS, nperseg=256, noverlap=128)
            # store raw per-window spectra for length-weighted pooling below (avoids phasor-averaging bias)
            coh_by_group[G].append((f, pxx, pyy, pxy, b - a))
    sec_by_group[G].append(n_win / V.FS)
    print(rk, meta["group"], "->", G, f"{n_win/V.FS:.0f}s in-window, {len(hf_by_group[G])} runs so far", flush=True)
    del S

print("\n=== independent event mask (broad |ad|>=25deg dilated runs, NOT the build/hold/unwind detector) ===")
print("total in-window seconds per group:", {g: sum(s) for g, s in sec_by_group.items()})
print("\n2-10 Hz steering-rate texture rms (deg/s), median over windows:")
for g in ("V282", "V282old", "TQ"):
    x = np.array(hf_by_group[g])
    print(f"  {g:8s} n_windows={len(x):3d}  median={np.median(x):6.2f}  mean={np.mean(x):6.2f}  [{np.percentile(x,25):.2f},{np.percentile(x,75):.2f}]")

# pooled coherence 1.5-3.5 Hz (weighted by window length, same formula as s3_pass3.py)
print("\npooled coherence(desired-angle-rate, measured steer-rate) 1.5-3.5 Hz, independent window mask:")
for g in ("V282", "V282old", "TQ"):
    segs = coh_by_group[g]
    if not segs:
        print(f"  {g:8s} no runs>=2.56s"); continue
    f0 = segs[0][0]
    Pxx = np.zeros_like(f0); Pyy = np.zeros_like(f0); Pxy = np.zeros_like(f0).astype(complex); sec = 0.0
    for f, pxx, pyy, pxy, w in segs:
        Pxx += pxx * w; Pyy += pyy * w; Pxy += pxy * w; sec += w
    m = (f0 >= 1.5) & (f0 < 3.5)
    coh = float(np.abs(Pxy[m].sum()) ** 2 / max(Pxx[m].sum() * Pyy[m].sum(), 1e-12))
    print(f"  {g:8s} windows(>=2.56s)={len(segs):3d} sec={sec/V.FS:6.0f}  coh(1.5-3.5Hz)={coh:.3f}")

print("\nratio TQ/V282 median texture (independent mask):",
      np.median(hf_by_group["TQ"]) / max(np.median(hf_by_group["V282"]), 1e-9))
