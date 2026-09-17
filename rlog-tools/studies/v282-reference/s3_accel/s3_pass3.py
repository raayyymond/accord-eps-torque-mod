"""Pass 3: (a) is the 1.5-5 Hz steering-rate excess DEMANDED or self-generated? desired-angle-rate PSD in the same
hands-off turn windows + coherence desired-rate -> steer-rate; per-event dominant frequency 1.5-5 Hz (nperseg 512).
(b) build-up entry: peak steering rate / peak desired angle rate in the first 1.5 s, and early (0-1 s) angle error, from the ensemble."""
import sys, json, pickle
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
GM = {"V282": "V282", "V282old": "V282old"}
acc = {}
evrows = []
for rk in V.ROUTES:
    R = T.prep(rk)
    G = GM.get(R["group"], "TQ")
    evs, _ = T.find_turns(R)
    adr = V.deriv(R["ad"])
    n = len(R["t"])
    for e in evs:
        mask = np.zeros(n, bool); mask[e["w0"]:e["w1"]] = True; mask &= ~R["pressed"]
        best = None
        for a, b in V.runs(mask, R["t"], min_s=2.56):
            x = adr[a:b] - adr[a:b].mean(); y = R["sr"][a:b] - R["sr"][a:b].mean()
            f, pxx = signal.welch(x, V.FS, nperseg=256, noverlap=128)
            _, pyy = signal.welch(y, V.FS, nperseg=256, noverlap=128)
            _, pxy = signal.csd(x, y, V.FS, nperseg=256, noverlap=128)
            A = acc.setdefault(G, dict(f=f, xx=0 * pxx, yy=0 * pxx, xy=0 * pxy, sec=0.0))
            w = len(x); A["xx"] += pxx * w; A["yy"] += pyy * w; A["xy"] += pxy * w; A["sec"] += w / V.FS
            if b - a >= 512:
                f2, p2 = signal.welch(y, V.FS, nperseg=512, noverlap=256)
                m = (f2 >= 1.5) & (f2 <= 5.0)
                fpk = float(f2[m][np.argmax(p2[m])]); pw = float(np.sum(p2[m]) * (f2[1] - f2[0]))
                if best is None or pw > best[1]:
                    best = (fpk, pw)
        evrows.append(dict(rk=rk, G=G, v=e["v"], P=e["P"], fpk=best[0] if best else np.nan, pw=best[1] if best else np.nan))
    print(rk, G, len(evs), flush=True)
    del R
print("\nhands-off turn windows: rms in band of DESIRED angle rate vs MEASURED steering rate, and coherence")
res = {}
for G, A in acc.items():
    f = A["f"]; xx, yy, xy = A["xx"] / A["sec"] / V.FS, A["yy"] / A["sec"] / V.FS, A["xy"] / A["sec"] / V.FS
    df = f[1] - f[0]
    line = f"  {G:8s} {A['sec']:5.0f} s"
    res[G] = {}
    for lo, hi in [(0.2, 1.0), (1.5, 3.5), (3.5, 6.0)]:
        m = (f >= lo) & (f < hi)
        rx, ry = np.sqrt(np.sum(xx[m]) * df), np.sqrt(np.sum(yy[m]) * df)
        coh = float(np.sum(np.abs(xy[m]) ** 2) / max(np.sum(xx[m] * yy[m]), 1e-12))
        res[G][f"{lo}-{hi}"] = dict(des_rms=float(rx), meas_rms=float(ry), coh=coh)
        line += f" | {lo}-{hi} Hz des {rx:6.2f} meas {ry:6.2f} coh {coh:.2f}"
    print(line)
print("\nper-event dominant 1.5-5 Hz steering-rate frequency (hands-off runs >= 5.12 s)")
for G in ["V282", "V282old", "TQ"]:
    fp = np.array([r["fpk"] for r in evrows if r["G"] == G]); pw = np.array([r["pw"] for r in evrows if r["G"] == G])
    ok = np.isfinite(fp)
    print(f"  {G:8s} n={ok.sum()} median f {np.median(fp[ok]):.2f} Hz IQR [{np.percentile(fp[ok],25):.2f},{np.percentile(fp[ok],75):.2f}]  "
          f"median 1.5-5 Hz rms {np.sqrt(np.median(pw[ok])):.1f} deg/s")
    res[G]["fpk"] = dict(n=int(ok.sum()), median=float(np.median(fp[ok])), q=[float(np.percentile(fp[ok], 25)), float(np.percentile(fp[ok], 75))],
                         rms_med=float(np.sqrt(np.median(pw[ok]))))

E = pickle.load(open(OUT + 'ensemble.pkl', 'rb')); g = E["grid"]
rng = np.random.default_rng(3)
print("\nbuild-up entry (anchor = build start); route-cluster bootstrap")
for G in ["V282", "V282old", "TQ"]:
    ev = [e for e in E["ens"] if GM.get(e["group"], "TQ") == G]
    rows = []
    for e in ev:
        tr = e["tr"]["i"]; P = e["P"]
        m = (g >= 0) & (g < 1.5)
        adr = np.gradient(tr["ad"] * P) * 100
        rr = np.nanmax(tr["sr"][m]) / max(np.nanmax(V.lowpass(np.nan_to_num(adr), 2.0)[m]), 5.0)
        m1 = (g >= 0) & (g < 1.0)
        err_early = np.nanmean((tr["aa"] - tr["ad"])[m1])
        m2 = (g >= 2.0) & (g < 3.5)
        err_late = np.nanmean((tr["aa"] - tr["ad"])[m2])
        rows.append((e["rk"], rr, err_early, err_late))
    routes = sorted(set(r[0] for r in rows))
    for k, name in [(1, "peak rate / peak desired rate (0-1.5 s)"), (2, "angle err/P  0-1 s"), (3, "angle err/P  2-3.5 s")]:
        x = np.array([r[k] for r in rows], float)
        bs = []
        for _ in range(2000):
            pick = rng.choice(routes, len(routes))
            z = np.concatenate([np.array([r[k] for r in rows if r[0] == p])[rng.integers(0, sum(1 for r in rows if r[0] == p), sum(1 for r in rows if r[0] == p))] for p in pick])
            bs.append(np.nanmedian(z))
        est = float(np.nanmedian(x))
        res[G][name] = [est, float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5)), int(np.isfinite(x).sum())]
        print(f"  {G:8s} {name:40s} median {est:+.3f} [{np.nanpercentile(bs,2.5):+.3f},{np.nanpercentile(bs,97.5):+.3f}] n{np.isfinite(x).sum()}")
json.dump(res, open(OUT + 's3_pass3.json', 'w'), indent=1, default=float)
