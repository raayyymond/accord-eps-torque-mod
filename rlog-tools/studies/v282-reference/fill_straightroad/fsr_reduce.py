"""Straight-road weave: reduce each route to straight runs at 10 Hz and per-run spectra. One route at a time.

Uses v282cmp (load/usable/runs/lowpass) for every shared definition. Own pieces and why:
  * spectra at 10 Hz with nperseg 512 (df 0.0195 Hz): V.band_H hard-codes fs=100 and caps the window by the
    SHORTEST run, which on 30-60 s straights gives df 0.024; the weave band needs <= 0.02 Hz. Same estimator
    (per-bin |Pxy|/Pxx weighted by Pxx, coherence, summed-phasor phase) is applied later in fsr_analyze.py.
  * lane offset / heading come from modelV2 (not in the shared cache): fsr_extract.py.

STRAIGHT: usable(S,15) [lateral engaged, not pressed, v>=15], |lowpass_0.05Hz(desiredCurvature)| < KTH,
  +-5 s away from |lowpass_0.5Hz(model a_d)| >= 1.0 m/s^2 (lane-change-sized events), +-15 s away from a lane-centre
  jump > 0.9 m (lane-line swap = lane change), +-2 s away from steeringPressed, model message gap < 0.15 s,
  contiguous by V.runs (never concatenated), >= 30 s.
out: ./reduced/<route>.npz
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import v282cmp as V

FS = V.FS; DEC = 10; FS2 = FS / DEC; NPS = 512
KTH = 4e-4
BANDS = dict(L=(0.02, 0.08), W=(0.08, 0.25), M=(0.25, 0.60))
OUT = HERE / "reduced"; OUT.mkdir(exist_ok=True)


def dilate(bad, n):
    if n <= 0:
        return bad
    k = np.ones(2 * n + 1)
    return np.convolve(bad.astype(float), k, mode="same") > 0


def reduce_route(route, kth=KTH, ad_thr=1.0, ad_pad=5.0):
    S = V.load(route)
    Fx = np.load(HERE / "cache" / f"{route}_fsr.npz", allow_pickle=True)
    P = json.loads(str(Fx["params_json"]))
    LAF = float(P.get("SteerLatAccel", "nan"))
    t = S["t"]; v = S["v"]; n = len(t)
    kd = np.nan_to_num(S["model"]) / np.maximum(v * v, 1.0)
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    kd = D["cs_des_curv"].astype(float)
    del D
    # model signals onto the cs clock
    tm = Fx["t_m"]
    yc_dev = 0.5 * (Fx["lL0"] + Fx["lR0"])                  # lane centre, device +right
    y_left = np.interp(t, tm, -yc_dev)                      # car LEFT of lane centre
    psi = np.interp(t, tm, 0.5 * ((Fx["lL20"] + Fx["lR20"]) - (Fx["lL0"] + Fx["lR0"])) / 20.0)  # car heading LEFT of lane
    width = np.interp(t, tm, Fx["lR0"] - Fx["lL0"])
    pmin = np.interp(t, tm, np.minimum(Fx["pL"], Fx["pR"]))
    py10 = np.interp(t, tm, -np.nan_to_num(Fx["py10"]))     # plan path LEFT at x = 10 m
    k_i = np.clip(np.searchsorted(tm, t), 1, len(tm) - 1)
    mgap = np.minimum(np.abs(t - tm[k_i - 1]), np.abs(tm[k_i] - t))
    mgap = np.maximum(mgap, 0)
    # observer (rev 5 / 6.4); controller torque-frame term -> cs_out frame = -logged
    if len(Fx["t_s"]) > 10 and np.any(Fx["dob"] != 0):
        dob = -np.interp(t, Fx["t_s"], Fx["dob"])
    else:
        dob = np.full(n, np.nan)
    del Fx
    # la_pose sign from turns (all engaged, any speed >= 5)
    mt = V.usable(S, 5.0) & np.isfinite(S["la_pose"])
    s_pose = float(np.sign(np.corrcoef(S["la_pose"][mt], np.nan_to_num(S["model"][mt]))[0, 1]))
    apose = s_pose * S["la_pose"]
    mo = V.usable(S, 5.0)
    s_out_sa = float(np.corrcoef(S["out"][mo], np.nan_to_num(S["sa"][mo]))[0, 1])
    # masks
    base = V.usable(S, 15.0) & np.isfinite(apose)
    kd_lp = V.lowpass(np.nan_to_num(kd), 0.05)
    ad_lp = V.lowpass(np.nan_to_num(S["model"]), 0.5)
    yjump = np.zeros(n, bool); yjump[1:] = np.abs(np.diff(y_left)) > 0.9
    bad = dilate(np.abs(ad_lp) >= ad_thr, int(ad_pad * FS)) | dilate(yjump, int(15 * FS)) | dilate(S["pressed"], int(2 * FS))
    straight_curv = np.abs(kd_lp) < kth if kth is not None else np.ones(n, bool)
    m = base & straight_curv & ~bad & (mgap < 0.15)
    census = dict(route=route, group=S["meta"].get("group"), kth=kth,
                  usable15_s=float(base.sum() / FS),
                  curv_ok_s=float((base & straight_curv).sum() / FS),
                  straight_any_s=float(m.sum() / FS))
    R = V.runs(m, t, min_s=30.0)
    runs = []
    sos2 = signal.butter(4, 2.0, fs=FS, output="sos")
    for a, b in R:
        def dec(x):
            x = np.asarray(x[a:b], float)
            if not np.all(np.isfinite(x)):
                return None
            return signal.sosfiltfilt(sos2, x)[::DEC]
        sig = dict(v=dec(v), ad=dec(np.nan_to_num(S["model"])), apose=dec(apose), aact=dec(S["la_act"]),
                   y=dec(y_left), psi=dec(psi), py10=dec(py10), sa=dec(S["sa"] - np.nan_to_num(S["aoff"])),
                   out=dec(S["out"]), I=dec(-S["i"] / LAF), Pt=dec(-S["p"] / LAF), Ft=dec(-S["f"] / LAF),
                   dob=dec(dob) if np.all(np.isfinite(dob[a:b])) else None, width=dec(width), pmin=dec(pmin))
        sig["e"] = sig["apose"] - sig["ad"]
        lane_ok = float(np.mean(pmin[a:b] > 0.5))
        # dwell: fraction of 100 Hz time the measured angle sits on one value for >= 0.5 s
        sa = S["sa"][a:b]; ch = np.flatnonzero(np.diff(sa) != 0)
        edges = np.concatenate([[0], ch + 1, [len(sa)]]); L = np.diff(edges)
        dwell = float(L[L >= 50].sum() / len(sa))
        runs.append(dict(i0=int(a), i1=int(b), sec=float((b - a) / FS), vmed=float(np.median(v[a:b])),
                         lane_ok=lane_ok, dwell=dwell, sig={k: x for k, x in sig.items() if x is not None}))
    meta = dict(census=census, LAF=LAF, params=P, s_pose=s_pose, corr_out_sa=s_out_sa,
                n_runs=len(runs), run_sec=[r["sec"] for r in runs])
    return meta, runs


def spectra(runs):
    """Per-run PSD/CSD at 10 Hz for runs >= NPS samples."""
    names = ["ad", "apose", "aact", "y", "psi", "py10", "sa", "out", "I", "Pt", "Ft", "dob", "e"]
    out = []
    for r in runs:
        s = r["sig"]
        if len(s["ad"]) < NPS:
            continue
        rec = dict(sec=r["sec"], vmed=r["vmed"], lane_ok=r["lane_ok"], dwell=r["dwell"], psd={}, csd={})
        for k in names:
            if k in s:
                f, p = signal.welch(s[k], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
                rec["psd"][k] = p
        pairs = [("ad", "apose"), ("ad", "aact"), ("apose", "y"), ("y", "ad"), ("psi", "ad"), ("ad", "sa"),
                 ("y", "apose"), ("y", "sa"), ("y", "I"), ("y", "dob"), ("y", "e"), ("y", "psi"), ("y", "out"),
                 ("sa", "I"), ("sa", "dob"), ("sa", "out"), ("ad", "e"), ("ad", "I"), ("ad", "dob"), ("y", "py10")]
        for x, y in pairs:
            if x in s and y in s:
                f, c = signal.csd(s[x], s[y], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
                rec["csd"][f"{x}>{y}"] = c
        rec["f"] = f
        out.append(rec)
    return out


TIERS = dict(S1=dict(kth=4e-4), S2=dict(kth=1e-3), HW=dict(kth=None, ad_thr=99.0))

if __name__ == "__main__":
    for route in sys.argv[1:]:
        allm = {}; allr = {}
        for tier, kw in TIERS.items():
            meta, runs = reduce_route(route, **kw)
            meta["census"]["runs30_s"] = float(sum(r["sec"] for r in runs))
            meta["census"]["runs51_s"] = float(sum(r["sec"] for r in runs if r["sec"] >= NPS / FS2))
            allm[tier] = meta; allr[tier] = runs
            c = meta["census"]
            print(f"{route} {c['group']:8s} {tier} usable15 {c['usable15_s']:.0f}s curv_ok {c['curv_ok_s']:.0f}s "
                  f"straight {c['straight_any_s']:.0f}s runs>=30 {c['runs30_s']:.0f}s ({len(runs)}) runs>=51 {c['runs51_s']:.0f}s "
                  f"vmed {[round(r['vmed'],1) for r in runs]}", flush=True)
        m0 = allm["S1"]
        print(f"   LAF {m0['LAF']} s_pose {m0['s_pose']:+.0f} corr(out,sa) {m0['corr_out_sa']:+.2f}")
        np.savez_compressed(OUT / f"{route}.npz", meta=np.array(json.dumps(allm)),
                            runs=np.array([allr], dtype=object))
        del allr
