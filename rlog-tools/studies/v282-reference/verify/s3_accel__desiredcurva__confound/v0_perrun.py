"""Per-run (per-segment) band quantities for the desired-vs-measured angle-rate cross spectrum, at 2.5-8 m/s.
Saves one JSON per route so downstream scripts can pool/bootstrap/match WITHOUT reloading the npz (RAM discipline:
one route in memory at a time, del before next).

Each run record carries enough to reconstruct pooled |H|/coh/phase for ANY subset of runs later:
  Pxx, Pyy, Pxy as per-band SUMS (already *w=len(seg) weighted, so summing across records = the original
  s3_refloop pooling), plus demand-amplitude proxies (rms of ad and of its 1Hz-lowpass) and mean speed,
  so later scripts can match on demand amplitude and speed sub-bin without recomputing spectra.
Bands: 0.3-1, 1-2, 2-3, 3-5 Hz (matches s3_refloop's set, at finer speed resolution).
Also carries 'ap' (livePose-derived equivalent wheel angle) cross-spectrum vs 'ad' rate, as an INDEPENDENT
measured-response channel (not the steering-column sensor), for the la_yaw-vs-la_act substitution: s3turns.py
already established carState.yawRate is identically 0 on every route (checked again below), so la_pose is the only
independent measured-response channel available; ap plays that role here.
"""
import sys, json
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import numpy as np
from scipy import signal
import v282cmp as V
import s3turns as T

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__desiredcurva__confound/'
BANDS = [(0.3, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 5.0)]
NPS = 512

ROUTES = list(V.ROUTES.keys())

for rk in ROUTES:
    meta = V.ROUTES[rk]
    S = V.load(rk)
    # independent sanity check: is carState.yawRate really identically zero on this route?
    yaw = np.nan_to_num(S['la_yaw'])  # la_yaw = cs_yaw(interp) * v ; if cs_yaw itself is 0 this is 0
    # recover raw cs_yaw pre-multiply by re-loading directly (cheap, same npz)
    import numpy as _np
    D = _np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    cs_yaw_raw = D['cs_yaw'] if 'cs_yaw' in D.files else _np.array([])
    yaw_allzero = bool(len(cs_yaw_raw) > 0 and _np.all(cs_yaw_raw == 0.0))
    yaw_nonzero_frac = float(_np.mean(cs_yaw_raw != 0.0)) if len(cs_yaw_raw) else None
    del D

    R = T.prep(rk)
    t = R['t']; v = R['v']; u = R['active'] & ~R['pressed']
    ad = R['ad']; sr = R['sr']; ap = R['ap']
    ad_lp1 = V.lowpass(np.nan_to_num(ad), 1.0)

    runs_out = []
    # fine speed sub-bins inside the 2.5-8 window used by the finding, plus the window itself
    for lo, hi in [(2.5, 4.0), (4.0, 6.0), (6.0, 8.0), (2.5, 8.0)]:
        m = u & (v >= lo) & (v < hi)
        for a, b in V.runs(m, t, min_s=5.12):
            x = V.deriv(ad[a:b])          # desired angle-rate
            y = sr[a:b]                    # measured steering rate (column sensor, fork-independent)
            yap = np.nan_to_num(ap[a:b])   # measured equivalent-angle from livePose (independent channel)
            if len(x) < NPS:
                continue
            nps = min(NPS, int(2 ** np.floor(np.log2(len(x)))))
            f, Pxx = signal.welch(x - x.mean(), 100, nperseg=nps)
            _, Pyy = signal.welch(y - y.mean(), 100, nperseg=nps)
            _, Pxy = signal.csd(x - x.mean(), y - y.mean(), 100, nperseg=nps)
            xap = V.deriv(yap)  # rate of the pose-derived equivalent angle, for a like-for-like rate comparison
            if np.any(np.isnan(xap)) or np.all(xap == 0):
                Pxy_ap = None; Pyy_ap = None
            else:
                _, Pyy_ap = signal.welch(xap - xap.mean(), 100, nperseg=nps)
                _, Pxy_ap = signal.csd(x - x.mean(), xap - xap.mean(), 100, nperseg=nps)
            w = float(len(x))
            rec = dict(rk=rk, group=meta['group'], lo=lo, hi=hi, t0=float(t[a]), t1=float(t[b]),
                       sec=w / 100.0, w=w, v_mean=float(np.mean(v[a:b])),
                       rms_ad=float(np.sqrt(np.mean(ad[a:b] ** 2))),
                       rms_ad_lp1=float(np.sqrt(np.mean(ad_lp1[a:b] ** 2))),
                       bands={})
            df = f[1] - f[0]
            for blo, bhi in BANDS:
                sel = (f >= blo) & (f < bhi)
                rec['bands'][f"{blo}-{bhi}"] = dict(
                    Pxx=(Pxx[sel] * w).tolist(), Pyy=(Pyy[sel] * w).tolist(),
                    PxyRe=(Pxy[sel].real * w).tolist(), PxyIm=(Pxy[sel].imag * w).tolist(),
                    Pyy_ap=(Pyy_ap[sel] * w).tolist() if Pyy_ap is not None else None,
                    PxyapRe=(Pxy_ap[sel].real * w).tolist() if Pxy_ap is not None else None,
                    PxyapIm=(Pxy_ap[sel].imag * w).tolist() if Pxy_ap is not None else None,
                    freqs=f[sel].tolist())
            runs_out.append(rec)
    out = dict(rk=rk, group=meta['group'], yaw_allzero=yaw_allzero, yaw_nonzero_frac=yaw_nonzero_frac,
               n_runs=len(runs_out), runs=runs_out)
    json.dump(out, open(OUT + f"perrun_{rk.replace('--','_')}.json", 'w'))
    print(f"{rk:24s} {meta['group']:8s} runs={len(runs_out):3d}  yaw_allzero={yaw_allzero}  "
          f"yaw_nonzero_frac={yaw_nonzero_frac}", flush=True)
    del S, R, cs_yaw_raw
