"""ADV-bytes 12: how much hands-off driving does the metric's |K|(0.3-1 Hz) read need before its pre-registered thresholds
stop misfiring?  Contiguous windows of 60 / 120 / 300 s; real V294 tap vs synthetic A1017 (same construction as advb6/7)."""
import contextlib, io, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(V295, "plant"), os.path.join(V295, "lib"), os.path.join(V295, "metric")):
    sys.path.insert(0, p)
import plib as P
d = P.load(); z = np.load(os.path.join(HERE, "_scratch", "advb6_march.npz"))
sg = d["sg"]; tt = d["tick_tap"]
dq = P.quant(sg * z["T1"][tt]) - P.quant(sg * z["T0"][tt])
with contextlib.redirect_stdout(io.StringIO()):
    import accel_tracking_metric as M
g = M.build_grid("r71b_v294"); gs = dict(g); gs["T"] = g["T"] - np.interp(g["t"], d["t_tap"], dq)
out = []
for nm, gg in (("V294 real", g), ("A1017 syn", gs)):
    B, valid = M.band_signals(gg, 0.3, 1.0, ["T", "Tff", "alpha_w"], hilb=("T", "Tff", "alpha_w"))
    sel = valid & gg["HO"]
    for Ws in (60, 120, 300):
        wid = (gg["tr"] // Ws).astype(int); Ks = []; Ps = []
        for k in np.unique(wid[sel]):
            s2 = sel & (wid == k)
            if s2.sum() < 0.5 * Ws * 100: continue
            X = np.column_stack([B["Tff"], B["HTff"], B["alpha_w"], B["Halpha_w"]])[s2]
            cc = np.linalg.lstsq(X, B["T"][s2], rcond=None)[0]
            Ks.append(np.hypot(cc[2], cc[3])); Ps.append(np.degrees(np.arctan2(-cc[3], cc[2])))
        Ks, Ps = np.array(Ks), np.array(Ps)
        s = ("%-10s %3d s windows n %2d: |K| min %.3f med %.3f max %.3f ; >=0.28 %.2f ; >0.45 %.2f ; phase-157 < -30: %.2f" % (
            nm, Ws, len(Ks), Ks.min(), np.median(Ks), Ks.max(), np.mean(Ks >= 0.28), np.mean(Ks > 0.45),
            np.mean(((Ps - 157 + 180) % 360 - 180) < -30)))
        print(s); out.append(s)
open(os.path.join(HERE, "advb12_K_duration_out.txt"), "w").write("\n".join(out) + "\n")
