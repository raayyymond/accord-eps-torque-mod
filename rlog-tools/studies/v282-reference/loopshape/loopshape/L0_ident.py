# -*- coding: utf-8 -*-
"""L0 -- validate the controller reconstruction on every route BEFORE any loop number is reported.

Nothing downstream is trusted unless, per route:
  (a) LAF   = -(p+i+f)/out   is constant to <0.1% across engaged frames and equals the flown SteerLatAccel
  (b) kp    = p / pid_log.error   is constant and equals the flown SteerKP
  (c) ki    from the integrator increments equals the flown AccordTorqueKi (or its speed schedule)
  (d) the logged command is reproduced from p,i,f with corr >= 0.9990  (the bar ffrecon.py meets)
  (e) the transfer from the RAW error (setpoint - measurement) to pid_log.error is the analytic
      low-speed-factor gain, times the HondaAccordErrorNotch response where the flown commit has it.
      This is the empirical test of whether the notch ran -- it does not rely on reading a default.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

import lp_lib as LP

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
CACHE = LP.V.CACHE


def ident(route):
    D = np.load(CACHE / f"{route}.npz", allow_pickle=True)
    L = LP.load_loop(route)
    fl = LP.FLOWN[route]
    t = L["t"]
    err = np.interp(t, D["t_cs"], D["cs_err"])      # same clock; interp is the identity here
    m = LP.runs_mask(L) & ~L["sat"] & (np.abs(L["out"]) > 0.02)
    mv = LP.runs_mask(L)
    R = dict(route=route, group=LP.GROUPS[route], eps=fl["eps"], flown=dict(fl),
             engaged_s=float(mv.sum() / LP.FS),
             s15_s=float((mv & (L["v"] >= 15)).sum() / LP.FS),
             s815_s=float((mv & (L["v"] >= 8) & (L["v"] < 15)).sum() / LP.FS))

    # (a) LAF
    lf = L["laf_frame"][m]
    lf = lf[np.isfinite(lf)]
    R["laf_med"] = float(np.median(lf))
    R["laf_iqr_frac"] = float((np.percentile(lf, 75) - np.percentile(lf, 25)) / np.median(lf))
    R["laf_flown"] = fl["laf"]

    # (b) kp
    me = m & (np.abs(err) > 0.02)
    kpf = L["p"][me] / err[me]
    R["kp_med"] = float(np.median(kpf))
    R["kp_iqr_frac"] = float((np.percentile(kpf, 75) - np.percentile(kpf, 25)) / np.median(kpf))
    R["kp_flown"] = fl["kp"]

    # (c) ki, from di = ki*dt*err on frames where the integrator is not frozen or clipped
    di = np.diff(L["i"])
    ok = me[1:] & me[:-1] & (np.abs(err[1:]) > 0.05) & (np.abs(di) > 1e-9)
    kif = di[ok] / (LP.DT * err[1:][ok])
    R["ki_med"] = float(np.median(kif))
    R["ki_flown"] = fl["ki"]
    if fl["ki_hi"] > 0:
        vv = L["v"][1:][ok]
        R["ki_lo_speed"] = float(np.median(kif[vv < 9])) if (vv < 9).sum() > 50 else None
        R["ki_hi_speed"] = float(np.median(kif[vv > 19])) if (vv > 19).sum() > 50 else None
        R["ki_hi_flown"] = fl["ki_hi"]

    # (d) command reconstruction
    rec = -np.clip(L["p"] + L["i"] + L["f"], -R["laf_med"], R["laf_med"]) / R["laf_med"]
    mm = mv & np.isfinite(rec) & np.isfinite(L["out"])
    R["recon_corr"] = float(np.corrcoef(rec[mm], L["out"][mm])[0, 1])
    R["recon_maxabs"] = float(np.max(np.abs(rec[mm] - L["out"][mm])))
    R["sat_frac_15"] = float(np.mean(L["sat"][mv & (L["v"] >= 15)])) if (mv & (L["v"] >= 15)).any() else np.nan
    R["sat_frac_815"] = float(np.mean(L["sat"][mv & (L["v"] >= 8) & (L["v"] < 15)])) if (mv & (L["v"] >= 8) & (L["v"] < 15)).any() else np.nan

    # (e) raw error -> logged error: the lsf gain, and the notch if it ran
    e_raw = L["r"] - L["y"]
    lsf = LP.low_speed_factor(L["v"])
    e_lsf = e_raw * (1.0 + lsf / max(fl["kp"], 1e-3))
    for tag, vlo, vhi in (("15-22", 15.0, 22.0), ("8-15", 8.0, 15.0)):
        wins = LP.windows(L, vlo, vhi)
        if len(wins) < 6:
            R[f"notch_{tag}"] = None
            continue
        w = LP.hann(1024)
        f = np.fft.rfftfreq(1024, LP.DT)
        Sxx = np.zeros(len(f)); Sxy = np.zeros(len(f), complex); vs = []
        for s, e, _ in wins:
            X = np.fft.rfft(signal.detrend(np.nan_to_num(e_lsf[s:e])) * w)
            Y = np.fft.rfft(signal.detrend(np.nan_to_num(err[s:e])) * w)
            Sxx += np.abs(X) ** 2; Sxy += np.conj(X) * Y
            vs.append(float(np.median(L["v"][s:e])))
        H = Sxy / np.maximum(Sxx, 1e-300)
        f0 = float(LP.mode_hz(np.median(vs)))
        Han = LP.notch_response(f, f0, 1.0)
        b = (f >= 0.3) & (f <= 6.0)
        R[f"notch_{tag}"] = dict(
            n_win=len(wins), v_med=float(np.median(vs)), mode_hz=f0,
            H_at_mode=float(np.abs(H[int(np.argmin(np.abs(f - f0)))])),
            H_at_1hz=float(np.abs(H[int(np.argmin(np.abs(f - 1.0)))])),
            ph_at_1hz=float(np.degrees(np.angle(H[int(np.argmin(np.abs(f - 1.0)))]))),
            H_at_02hz=float(np.abs(H[int(np.argmin(np.abs(f - 0.2)))])),
            err_vs_notch=float(np.median(np.abs(H[b] - Han[b]))),
            err_vs_unity=float(np.median(np.abs(H[b] - 1.0))))
    return R


if __name__ == "__main__":
    rows = []
    for route in LP.FLOWN:
        if not (CACHE / f"{route}.npz").exists():
            print(f"{route}: no cache"); continue
        try:
            R = ident(route)
        except Exception as ex:
            print(f"{route}: FAILED {ex}"); continue
        rows.append(R)
        print(f"{route} {R['group']:7s} {R['eps']:5s} eng {R['engaged_s']:6.0f}s (>=15 {R['s15_s']:5.0f}, 8-15 {R['s815_s']:5.0f})")
        print(f"   LAF {R['laf_med']:7.3f} (flown {R['laf_flown']}) iqr {R['laf_iqr_frac']*100:.3f}%"
              f" | kp {R['kp_med']:.4f} (flown {R['kp_flown']}) iqr {R['kp_iqr_frac']*100:.3f}%"
              f" | ki {R['ki_med']:.3f} (flown {R['ki_flown']})"
              + (f" [lo {R.get('ki_lo_speed')} hi {R.get('ki_hi_speed')} sched->{R.get('ki_hi_flown')}]" if R['flown']['ki_hi'] > 0 else ""))
        print(f"   recon corr {R['recon_corr']:.6f} maxabs {R['recon_maxabs']:.2e}"
              f" | sat frac >=15 {R['sat_frac_15']*100:.4f}%  8-15 {R['sat_frac_815']*100:.4f}%"
              f" | kp/LAF {R['kp_med']/R['laf_med']:.4f}")
        for tag in ("15-22", "8-15"):
            nd = R.get(f"notch_{tag}")
            if nd:
                print(f"   err-path {tag}: mode {nd['mode_hz']:.2f} Hz  |H| at mode {nd['H_at_mode']:.3f}"
                      f"  at 1 Hz {nd['H_at_1hz']:.3f} @ {nd['ph_at_1hz']:+6.1f} deg  at 0.2 Hz {nd['H_at_02hz']:.3f}"
                      f"  || dev vs NOTCH {nd['err_vs_notch']:.4f}  vs UNITY {nd['err_vs_unity']:.4f}"
                      f"  => {'NOTCH ran' if nd['err_vs_notch'] < nd['err_vs_unity'] else 'NO notch'}")
        print()
    json.dump(rows, open(OUT / "L0_ident.json", "w"), indent=1)
    print(f"wrote {OUT/'L0_ident.json'}")
