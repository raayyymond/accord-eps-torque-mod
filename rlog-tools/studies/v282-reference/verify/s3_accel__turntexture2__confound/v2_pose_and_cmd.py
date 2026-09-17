"""Two more CONFOUND checks, one route at a time (RAM discipline):

(A) Is the 2-10 Hz sr texture a CAN/sensor-encoding artifact of the V293 firmware's steering-rate
    message, or does it show up in an EPS-independent signal (livePose IMU yaw rate)? Convert la_pose
    to an angle-rate-equivalent via the SAME bicycle model as s3turns (curv_to_angle), band-pass 2-10 Hz,
    compare rms in turn-event hold phases, same events as s3turns.find_turns.
(B) Is the low-level actuator COMMAND (cs_out, independent of any EPS sensor -- it is openpilot's own
    output before the EPS ever sees it) itself concentrated at ~2.3 Hz in torque mode, or does the excess
    show up only in the realized wheel rate? (command vs realized ratio, same hold-phase windows.)
Skips 0000006c--2bc842dbac (28 MB dominant V282 route) to keep this pass light; route (1) in v1 already
showed LORO is robust without it.
"""
import sys, gc
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T
import v282cmp as V

HF_SOS = signal.butter(4, [2.0, 10.0], btype="band", fs=V.FS, output="sos")

ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd",
          "00000039--f56039af87", "0000003c--927965c2b4",
          "0000006c--68c6e94b17", "0000006d--05e83bb04f",
          "0000006e--6ca3e014fd", "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"]

rows = []
for rk in ROUTES:
    R = T.prep(rk)
    evs, _ = T.find_turns(R)
    ap_hf = signal.sosfiltfilt(HF_SOS, np.nan_to_num(R["ap"]))
    out_hf = signal.sosfiltfilt(HF_SOS, R["out"])
    for e in evs:
        h0, h1 = e["h0"], e["h1"]
        if h1 - h0 < 20:
            continue
        m = ~R["pressed"][h0:h1]
        if m.sum() < 20:
            continue
        sr_rms = float(np.sqrt(np.mean(R["hf"][h0:h1][m] ** 2)))         # EPS-CAN steering-rate sensor
        ap_rms = float(np.sqrt(np.nanmean(ap_hf[h0:h1][m] ** 2))) if np.isfinite(ap_hf[h0:h1][m]).any() else float("nan")  # IMU-derived, EPS-independent
        out_rms = float(np.sqrt(np.mean(out_hf[h0:h1][m] ** 2)))         # fork's own low-level command, pre-EPS
        rows.append(dict(rk=rk, group=R["group"], v=e["v"], P=e["P"], sr_rms=sr_rms, ap_rms=ap_rms, out_rms=out_rms))
    print(rk, R["group"], "events", len(evs), "with hold rows so far", len(rows), flush=True)
    del R, evs, ap_hf, out_hf
    gc.collect()

GM = {"V282": "V282", "V282old": "V282old"}
print("\n=== (A) 2-10 Hz HOLD-phase texture: EPS steering-rate sensor (sr) vs EPS-independent IMU-derived rate (ap) ===")
for g in ["V282", "V282old", "T64", "T64B", "T5", "T4"]:
    sub = [r for r in rows if r["group"] == g]
    if not sub:
        continue
    sr = np.array([r["sr_rms"] for r in sub])
    ap = np.array([r["ap_rms"] for r in sub])
    ok = np.isfinite(ap)
    print(f"  {g:8s} n={len(sub):2d}  sr median {np.median(sr):6.2f} deg/s | ap(IMU) median {np.nanmedian(ap[ok]) if ok.any() else float('nan'):6.2f} deg/s-equiv  n_ap_ok={ok.sum()}")

print("\n=== (B) low-level command (cs_out, pre-EPS) 2-10 Hz rms in the SAME hold windows, vs realized sr ===")
for g in ["V282", "V282old", "T64", "T64B", "T5", "T4"]:
    sub = [r for r in rows if r["group"] == g]
    if not sub:
        continue
    sr = np.array([r["sr_rms"] for r in sub]); out = np.array([r["out_rms"] for r in sub])
    ratio = sr / np.maximum(out, 1e-9)
    print(f"  {g:8s} n={len(sub):2d}  cmd(out) median {np.median(out):7.4f}  sr median {np.median(sr):6.2f}  sr/cmd ratio median {np.median(ratio):8.1f}")

import json
json.dump(rows, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__turntexture2__confound/v2_rows.json', 'w'), indent=1)
print("\nwrote v2_rows.json, n=", len(rows))
