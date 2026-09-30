"""ADV-D step 8: the low-speed cost and on-centre behaviour, custom metrics on the harness's mode-B closed loop (the real
fork law, byte-exact lanes, V295 cells from the IMAGE and V294 in the SAME batch):
  (a) 0.5-1 Hz lateral-acceleration error rms (plan - act, zero-phase band-pass) per speed band -- the cost the decision
      states as x1.04-1.4 at low speed;
  (b) on-centre (|plan| < 0.4 m/s^2 and |angle| < 10 deg): wheel-rate rms 0.2-1 Hz and 1-5 Hz, and the lateral error
      0.2-1 Hz -- hunting would show as a rise here;
  (c) the same metrics on the drive itself (r71b, same code) for scale.
Dists lp (the plant + slow residual; the loop's own motion) and full (r71b's disturbance replayed; counterfactual)."""
import sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
c5 = H.Cells.from_image(V295, "V295", "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed")
c4 = H.Cells.v294()
fam = H.family()
PL = ("nominal", "light_b", "b_lo", "F_hi", "J_hi")
members = [fam[p] for p in PL]
chunks = H.route_chunks()
cells = [c5, c4]
nM, nK = len(members), len(chunks)

def bp(x, lo, hi):
    b, a = signal.butter(2, [lo / 50.0, hi / 50.0], btype="band")
    return signal.filtfilt(b, a, x) if len(x) > 60 else np.zeros_like(x)

def metrics(series):
    """series: list of dicts per chunk with v, plan, act, rate, ang -> per band: e05_1, and on-centre numbers."""
    out = {}
    for nm, lo, hi in H.BANDS:
        acc = {k: [] for k in ("e05", "e021_c", "r021_c", "r15_c")}
        for s in series:
            n = len(s["v"])
            cut = np.zeros(n, bool); cut[100:-100] = True
            mk = (s["v"] >= lo) & (s["v"] < hi) & cut
            if mk.sum() < 50:
                continue
            e = s["plan"] - s["act"]
            acc["e05"].append(bp(e, 0.5, 1.0)[mk])
            cen = mk & (np.abs(s["plan"]) < 0.4) & (np.abs(s["ang"]) < 10)
            acc["e021_c"].append(bp(e, 0.2, 1.0)[cen])
            acc["r021_c"].append(bp(s["rate"], 0.2, 1.0)[cen])
            acc["r15_c"].append(bp(s["rate"], 1.0, 5.0)[cen])
        res = {}
        for k, v in acc.items():
            cat = np.concatenate(v) if v else np.zeros(0)
            res[k] = float(np.sqrt(np.mean(cat ** 2))) if len(cat) > 200 else float("nan")
            res[k + "_s"] = len(cat) / 100.0
        out[nm] = res
    return out

res = {}
for dist in ("lp", "full"):
    R = H.simulate(cells, members, chunks, H.SimOpts(mode="B", dist=dist))
    for ci, c in enumerate(cells):
        for mi, p in enumerate(PL):
            rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
            ser = []
            for j in rows:
                n = R["lens"][j]
                ser.append(dict(v=R["v"][j, :n], plan=R["la_plan"][j, :n], act=R["la_act"][j, :n], rate=R["rate18"][j, :n],
                                ang=R["ang"][j, :n]))
            res[(dist, c.name, p)] = metrics(ser)
    print("sim %s done, bails V295 %d V294 %d" % (dist, int(R["n_bail"][:nM * nK].sum()), int(R["n_bail"][nM * nK:].sum())))
# the drive itself (same code)
d = H.route()
ser = []
for a, b in chunks:
    ser.append(dict(v=d["v"][a:b], plan=d["ctl_des_curv_f"][a:b] * d["v"][a:b] ** 2, act=d["ctl_la_act_f"][a:b],
                    rate=d["x18_f"][a:b] / 8.0, ang=d["th"][a:b]))
res[("measured", "r71b", "-")] = metrics(ser)

print("\n(a) 0.5-1 Hz lateral-accel error rms, V295 / V294 (absolute V294 in brackets, m/s^2); measured r71b for scale")
hdr = "  %-5s %-8s" % ("dist", "plant") + "".join("%18s" % b for b, _, _ in H.BANDS)
print(hdr)
for dist in ("lp", "full"):
    for p in PL:
        a, b = res[(dist, "V295", p)], res[(dist, "V294", p)]
        print("  %-5s %-8s" % (dist, p) + "".join("%18s" % ("x%.3f (%.3f)" % (a[bn]["e05"] / b[bn]["e05"], b[bn]["e05"])
                                                          if np.isfinite(a[bn]["e05"]) else "n/t") for bn, _, _ in H.BANDS))
m = res[("measured", "r71b", "-")]
print("  %-5s %-8s" % ("drive", "r71b") + "".join("%18s" % ("(%.3f)" % m[bn]["e05"]) for bn, _, _ in H.BANDS))

print("\n(b) ON-CENTRE (|plan| < 0.4, |angle| < 10 deg): V295 / V294 of lateral error 0.2-1 Hz | wheel rate 0.2-1 Hz | wheel rate 1-5 Hz")
for dist in ("lp", "full"):
    for p in PL:
        a, b = res[(dist, "V295", p)], res[(dist, "V294", p)]
        cells_s = []
        for bn, _, _ in H.BANDS:
            if np.isfinite(a[bn]["r021_c"]):
                cells_s.append("%s: x%.3f x%.3f x%.3f (%.0fs)" % (bn, a[bn]["e021_c"] / b[bn]["e021_c"], a[bn]["r021_c"] / b[bn]["r021_c"],
                                                               a[bn]["r15_c"] / b[bn]["r15_c"], a[bn]["r021_c_s"]))
        print("  %-5s %-8s %s" % (dist, p, " | ".join(cells_s)))
json.dump({"|".join(k): v for k, v in res.items()}, open("d8_lowfreq.json", "w"), indent=1)
