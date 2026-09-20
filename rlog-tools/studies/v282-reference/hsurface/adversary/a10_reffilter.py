"""ADVERSARY A10 - the phase deficit attributed to torque mode is largely a FORK-SIDE REFERENCE PREFILTER.

Found by reading the two flown commits: `accord_ref_filter_1/2` - TWO cascaded first-order low-passes on the
setpoint that both the feedforward and the P/I error see - DOES NOT EXIST in latcontrol_torque.py at 0f98d8c7
(the commit all three V282 reference routes flew) and exists on every torque commit, flown at
AccordRefFilter = 0.06 s (T64, T64B) and 0.12 s (T5, T4).

Two cascaded poles at 1/(2*pi*tau) contribute phase -2*atan(w*tau) to the model -> achieved path. This script
(1) computes that prediction and (2) MEASURES the same thing without any model, by taking the transfer from the
logged model demand to the logged SHAPED setpoint (`torqueState.desiredLateralAccel`, which the fork's own comment
says is the shaped one). That stage contains no plant and no EPS at all, so whatever phase it holds cannot be
attributed to the EPS mode.

usage: python a10_reffilter.py
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import load_route, my_runs, windows, band_stats, GROUP, FS

NPS = 4096
f = np.fft.rfftfreq(NPS, 1 / FS)
BANDS = [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
TAU = {"V282": 0.0, "V282old": 0.0, "T64": 0.06, "T64B": 0.06, "T5": 0.12, "T4": 0.12}   # flown AccordRefFilter

acc = {}
for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    xm, xs, y = np.nan_to_num(S["x_model"]), np.nan_to_num(S["x_setpoint"]), np.nan_to_num(S["y_pose"])
    for a, b in my_runs(m, S["t"], 41.0):
        for key, (p, q) in dict(model_to_y=(xm, y), setp_to_y=(xs, y), model_to_setp=(xm, xs)).items():
            for pxx, pyy, pxy, _ in windows(p[a:b], q[a:b], NPS, NPS // 2):
                acc.setdefault((g, key), []).append(dict(pxx=pxx, pyy=pyy, pxy=pxy))
    del S

print("=== the reference-shaping stage ALONE: logged model demand -> logged shaped setpoint (no plant, no EPS) ===")
print(f"{'band':>12s} {'group':8s} {'tau_flown':>9s} {'|H|':>6s} {'coh':>5s} {'phase_meas':>10s} "
      f"{'phase_pred':>10s} {'mag_pred':>8s}")
for f1, f2 in BANDS:
    for g in GROUPS:
        st = band_stats(acc.get((g, "model_to_setp"), []), f, f1, f2)
        if not st:
            continue
        w = 2 * np.pi * st["fbar"]; t = TAU[g]
        ppred = -2 * np.degrees(np.arctan(w * t)); mpred = 1.0 / (1 + (w * t) ** 2)
        print(f"{f1:5.2f}-{f2:4.2f} {g:8s} {t:9.2f} {st['H_mag']:6.3f} {st['coh']:5.3f} "
              f"{st['phase_deg']:10.1f} {ppred:10.1f} {mpred:8.3f}")
    print()

print("=== what is left for the EPS: the same bands measured from the SHAPED SETPOINT instead of the raw demand ===")
print(f"{'band':>12s} {'group':8s} {'model->y H':>10s} {'ph':>7s} | {'setp->y H':>9s} {'ph':>7s} | "
      f"{'d_ph from shaping':>17s} {'NRMSE m->y':>10s} {'NRMSE s->y':>10s}")
tab = {}
for f1, f2 in BANDS:
    for g in GROUPS:
        a = band_stats(acc.get((g, "model_to_y"), []), f, f1, f2)
        b = band_stats(acc.get((g, "setp_to_y"), []), f, f1, f2)
        if not (a and b):
            continue
        tab[(f1, g)] = (a, b)
        print(f"{f1:5.2f}-{f2:4.2f} {g:8s} {a['H_mag']:10.3f} {a['phase_deg']:7.1f} | {b['H_mag']:9.3f} "
              f"{b['phase_deg']:7.1f} | {a['phase_deg']-b['phase_deg']:17.1f} {a['nrmse']:10.3f} {b['nrmse']:10.3f}")
    print()

print("=== the accounting that matters: how much of each torque rev's phase deficit vs V282 is fork-side shaping? ===")
print(f"{'band':>12s} {'group':8s} {'gap_model->y':>12s} {'gap_setp->y':>11s} {'shaping share':>13s} "
      f"{'gap_NRMSE_m':>11s} {'gap_NRMSE_s':>11s}")
for f1, f2 in BANDS:
    if (f1, "V282") not in tab:
        continue
    va, vb = tab[(f1, "V282")]
    for g in GROUPS[1:]:
        if (f1, g) not in tab:
            continue
        a, b = tab[(f1, g)]
        gm = a["phase_deg"] - va["phase_deg"]
        gs = b["phase_deg"] - vb["phase_deg"]
        share = 1 - gs / gm if abs(gm) > 1e-6 else float("nan")
        print(f"{f1:5.2f}-{f2:4.2f} {g:8s} {gm:12.1f} {gs:11.1f} {share*100:12.0f}% "
              f"{a['nrmse']-va['nrmse']:11.3f} {b['nrmse']-vb['nrmse']:11.3f}")
    print()
