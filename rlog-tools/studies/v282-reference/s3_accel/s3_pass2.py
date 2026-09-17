"""Pass 2 on the same turn events (deterministic re-detection):
 (a) lag sweep with a COMMON lag for every group -> build/unwind errors, and the lag-robust split
     sym = (build_err + unwind_err)/2  (a restoring/under-turn bias that does not flip with direction: the caster/hold signature)
     anti = (unwind_err - build_err)/2 (the lag signature: lagging flips sign between build and unwind)
 (b) per-event best lag (angle and pose) by cross-correlation over [i, j]
 (c) error vs normalised desired angle |ad|/P, separately for build and unwind, non-pressed frames only
 (d) steering-rate PSD inside turn windows (non-pressed runs >= 2.56 s), per group
 (e) HF 2-10 Hz steer-rate texture on non-pressed frames only
"""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
LAGS = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5]
FB = np.linspace(0.1, 1.0, 10)
ev_rows = []
psd = {}
for rk in V.ROUTES:
    R = T.prep(rk)
    evs, _ = T.find_turns(R)
    G = R["group"]
    n = len(R["t"])
    for e in evs:
        s, P = e["s"], e["P"]
        ad = s * R["ad"]
        row = dict(rk=rk, group=G, v=e["v"], P=P, d=R["d"])
        for key in ("aa", "ap"):
            src = np.where(R["pressed"], np.nan, R[key])
            for L in LAGS:
                ach = s * T.shift(src, int(round(L * V.FS)))
                err = ach - ad
                b = np.nanmean(err[e["i"]:e["h0"]]) / P if e["h0"] - e["i"] >= 5 else np.nan
                u = np.nanmean(err[e["h1"]:e["j"]]) / P if e["j"] - e["h1"] >= 5 else np.nan
                h = np.nanmean(err[e["h0"]:e["h1"]]) / P if e["h1"] - e["h0"] >= 5 else np.nan
                row[f"{key}_L{L}_build"] = float(b); row[f"{key}_L{L}_unwind"] = float(u); row[f"{key}_L{L}_hold"] = float(h)
                row[f"{key}_L{L}_sym"] = float((b + u) / 2); row[f"{key}_L{L}_anti"] = float((u - b) / 2)
            # best lag
            x = ad[e["i"]:e["j"]]; best, bl = -np.inf, np.nan
            for k in range(0, 81):
                y = s * T.shift(R[key], k)[e["i"]:e["j"]]
                m = np.isfinite(y) & ~R["pressed"][e["i"]:e["j"]]
                if m.sum() < 30:
                    continue
                c = np.corrcoef(x[m], y[m])[0, 1]
                if c > best:
                    best, bl = c, k / V.FS
            row[f"{key}_bestlag"] = float(bl)
            # error vs normalised desired angle, at the route's learned lag and at a common 0.25 s
            for L, tag in ((R["d"], "dl"), (0.25, "c25")):
                ach = s * T.shift(src, int(round(L * V.FS)))
                err = (ach - ad) / P
                fr = ad / P
                for ph, (a0, a1) in (("build", (e["i"], e["h0"])), ("unwind", (e["h1"], e["j"]))):
                    prof = []
                    for lo, hi in zip(FB[:-1], FB[1:]):
                        m = (fr[a0:a1] >= lo) & (fr[a0:a1] < hi) & np.isfinite(err[a0:a1])
                        prof.append(float(np.mean(err[a0:a1][m])) if m.sum() >= 3 else np.nan)
                    row[f"{key}_{tag}_prof_{ph}"] = prof
        # HF on non-pressed frames
        for ph, (a0, a1) in (("build", (e["i"], e["h0"])), ("hold", (e["h0"], e["h1"])), ("unwind", (e["h1"], e["j"])),
                             ("ret", (e["j"], e["j"] + 300))):
            m = ~R["pressed"][a0:a1]
            row[f"hfnp_{ph}"] = float(np.sqrt(np.mean(R["hf"][a0:a1][m] ** 2))) if m.sum() >= 20 else np.nan
        ev_rows.append(row)
        # PSD over non-pressed runs within [i-1 s, j+3 s]
        w0, w1 = e["w0"], e["w1"]
        mask = np.zeros(n, bool); mask[w0:w1] = True; mask &= ~R["pressed"]
        for a, b in V.runs(mask, R["t"], min_s=2.56):
            x = R["sr"][a:b] - np.mean(R["sr"][a:b])
            f, p = signal.welch(x, V.FS, nperseg=256, noverlap=128)
            acc = psd.setdefault(G, dict(f=f.tolist(), p=np.zeros_like(p), sec=0.0, pout=np.zeros_like(p)))
            acc["p"] += p * len(x); acc["sec"] += len(x) / V.FS
            _, po = signal.welch(R["out"][a:b] - np.mean(R["out"][a:b]), V.FS, nperseg=256, noverlap=128)
            acc["pout"] += po * len(x)
    print(rk, G, len(evs), flush=True)
    del R
for G, a in psd.items():
    a["p"] = (a["p"] / (a["sec"] * V.FS)).tolist(); a["pout"] = (a["pout"] / (a["sec"] * V.FS)).tolist()
json.dump(dict(rows=ev_rows, psd=psd, lags=LAGS, fbins=FB.tolist()), open(OUT + 's3_pass2.json', 'w'), indent=1)
print("done", len(ev_rows))
