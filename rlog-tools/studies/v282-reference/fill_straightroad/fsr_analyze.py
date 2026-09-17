"""Straight-road weave: weave-band table, mechanism discriminators, bootstrap CIs, figures.
Reads ./reduced/<route>.npz (fsr_reduce.py). One tier at a time: python fsr_analyze.py S1
Estimator for transfer functions = the v282cmp.band_H definition (per-bin |Pxy|/Pxx weighted by Pxx, coherence,
phase of the summed Pxy), re-implemented at fs = 10 Hz because band_H hard-codes fs = 100.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import v282cmp as V

FS2 = 10.0
W = (0.08, 0.25)
VB = [(15.0, 22.0), (22.0, 29.0)]
TIER = sys.argv[1] if len(sys.argv) > 1 else "S1"
NPS = int(sys.argv[2]) if len(sys.argv) > 2 else 256
SIGS = ["y", "psi", "py10", "sa", "ad", "apose", "aact", "e", "out", "I", "Pt", "Ft", "dob"]
PAIRS = [("apose", "ad"), ("apose", "e"), ("apose", "sa"), ("apose", "psi"), ("apose", "I"), ("apose", "dob"),
         ("apose", "Ft"), ("apose", "out"), ("apose", "Pt"), ("apose", "y"), ("psi", "sa"), ("ad", "psi"), ("ad", "apose"), ("ad", "aact"), ("apose", "y"), ("y", "ad"), ("psi", "ad"), ("y", "apose"), ("y", "sa"),
         ("y", "I"), ("y", "dob"), ("y", "e"), ("y", "psi"), ("y", "out"), ("sa", "I"), ("sa", "dob"), ("sa", "out"),
         ("ad", "e"), ("ad", "I"), ("ad", "dob"), ("ad", "sa"), ("y", "Ft"), ("sa", "Ft")]
rng = np.random.default_rng(7)


def band_rms(x, f1, f2, trim=5.0):
    sos = signal.butter(4, [f1, f2], btype="band", fs=FS2, output="sos")
    yb = signal.sosfiltfilt(sos, x - np.mean(x))
    k = int(trim * FS2)
    return float(np.sqrt(np.mean(yb[k:-k] ** 2)))


def load_runs():
    R = []
    for route, meta in V.ROUTES.items():
        f = HERE / "reduced" / f"{route}.npz"
        if not f.exists():
            continue
        Z = np.load(f, allow_pickle=True)
        M = json.loads(str(Z["meta"]))[TIER]
        runs = Z["runs"][0][TIER]
        for r in runs:
            s = dict(r["sig"])
            if len(s["ad"]) < NPS:
                continue
            # FRAME (fixed by the kinematic positive control, fsr_kinecheck.py, and by ad>sa phase ~ +170):
            # desiredCurvature*v^2, la_pose and la_act are +RIGHT in these logs; steeringAngleDeg, cs_out, I, F,
            # the observer term and the lane-derived y/psi are +LEFT. Put everything +LEFT.
            for k in ("ad", "apose", "aact", "e"):
                s[k] = -s[k]
            vb = next((i for i, (a, b) in enumerate(VB) if a <= r["vmed"] < b), None)
            rec = dict(route=route, group=meta["group"], sec=r["sec"], vmed=r["vmed"], vbin=vb, lane_ok=r["lane_ok"],
                       dwell=r["dwell"], rms={}, psd={}, csd={})
            for k in SIGS:
                if k in s:
                    rec["rms"][k] = band_rms(s[k], *W)
                    f_, p = signal.welch(s[k], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
                    rec["psd"][k] = p * r["sec"]
            for x, y in PAIRS:
                if x in s and y in s:
                    f_, c = signal.csd(s[x], s[y], FS2, nperseg=NPS, noverlap=NPS // 2, detrend="linear")
                    rec["csd"][f"{x}>{y}"] = c * r["sec"]
            rec["f"] = f_
            R.append(rec)
        del Z
    return R


def pooled_rms(runs, key, weights):
    """speed-bin-matched rms: sqrt(sum_b w_b * (sum P sec / sum sec)_b)."""
    tot = 0.0; wsum = 0.0
    for b, w in enumerate(weights):
        rr = [r for r in runs if r["vbin"] == b and key in r["rms"]]
        if not rr or w == 0:
            continue
        s = sum(r["sec"] for r in rr)
        tot += w * sum(r["rms"][key] ** 2 * r["sec"] for r in rr) / s; wsum += w
    return float(np.sqrt(tot / wsum)) if wsum > 0 else float("nan")


def pooled_H(runs, x, y):
    k = f"{x}>{y}"
    rr = [r for r in runs if k in r["csd"] and x in r["psd"] and y in r["psd"]]
    if not rr:
        return None
    f = rr[0]["f"]; s = (f >= W[0]) & (f < W[1])
    Pxy = sum(r["csd"][k] for r in rr); Pxx = sum(r["psd"][x] for r in rr); Pyy = sum(r["psd"][y] for r in rr)
    w = Pxx[s]
    H = np.abs(Pxy[s]) / np.maximum(Pxx[s], 1e-30)
    coh = np.abs(Pxy[s]) ** 2 / np.maximum(Pxx[s] * Pyy[s], 1e-30)
    om2 = (2 * np.pi * f[s]) ** 2
    return dict(H=float(np.average(H, weights=w)), coh=float(np.average(coh, weights=w)),
                phase=float(np.degrees(np.angle(Pxy[s].sum()))),
                Hw2=float(np.average(H * om2, weights=w)),
                incoh_rms_y=float(np.sqrt(np.sum((1 - coh) * Pyy[s]) * (f[1] - f[0]) / sum(r["sec"] for r in rr))),
                per_bin=dict(f=f[s].tolist(), H=H.tolist(), coh=coh.tolist(),
                             ph=np.degrees(np.angle(Pxy[s])).tolist()))


def boot(runs, stat, B=400):
    """two-level cluster bootstrap: routes with replacement, then runs within route."""
    by = {}
    for r in runs:
        by.setdefault(r["route"], []).append(r)
    keys = list(by)
    out = []
    for _ in range(B):
        rs = rng.choice(len(keys), len(keys)) if len(keys) > 1 else [0]
        smp = []
        for i in rs:
            L = by[keys[i]]
            smp += [L[j] for j in rng.choice(len(L), len(L))]
        try:
            out.append(stat(smp))
        except Exception:
            pass
    return np.array([o for o in out if o is not None and np.isfinite(o)])


def main():
    R = load_runs()
    groups = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
    G = {g: [r for r in R if r["group"] == g] for g in groups}
    G["TORQUE"] = [r for r in R if r["group"] in ("T64", "T64B", "T5", "T4")]
    G["V282all"] = G["V282"] + G["V282old"]
    # census
    census = {}
    for g in groups + ["TORQUE"]:
        rr = G[g]
        census[g] = dict(n_runs=len(rr), sec=round(sum(r["sec"] for r in rr), 1),
                         sec_by_vbin=[round(sum(r["sec"] for r in rr if r["vbin"] == b), 1) for b in range(len(VB))],
                         sec_unbinned=round(sum(r["sec"] for r in rr if r["vbin"] is None), 1),
                         routes={rt: round(sum(r["sec"] for r in rr if r["route"] == rt), 1) for rt in sorted({r["route"] for r in rr})})
    # speed-bin weights: bins where BOTH V282 and TORQUE have data, weighted by TORQUE seconds (the complaint's regime)
    wts = []
    for b in range(len(VB)):
        tv = sum(r["sec"] for r in G["TORQUE"] if r["vbin"] == b); vv = sum(r["sec"] for r in G["V282"] if r["vbin"] == b)
        wts.append(tv if (tv > 0 and vv > 0) else 0.0)
    wts = np.array(wts) / max(sum(wts), 1e-9)
    # band table
    table = {}
    for g in groups + ["TORQUE", "V282all"]:
        rr = [r for r in G[g] if r["vbin"] is not None]
        table[g] = {k: pooled_rms(rr, k, wts) for k in SIGS}
    ratios = {}
    ref = [r for r in G["V282"] if r["vbin"] is not None]
    for g in ["T64", "TORQUE", "T5", "T64B", "V282old"]:
        tr = [r for r in G[g] if r["vbin"] is not None]
        if not tr:
            continue
        ratios[g] = {}
        for k in ["y", "psi", "sa", "ad", "apose", "e"]:
            pt = pooled_rms(tr, k, wts); pv = pooled_rms(ref, k, wts)
            bt = boot(tr, lambda s: pooled_rms(s, k, wts)); bv = boot(ref, lambda s: pooled_rms(s, k, wts))
            n = min(len(bt), len(bv))
            lr = np.log(bt[:n] / bv[:n])
            se = float(np.std(lr))
            ratios[g][k] = dict(ratio=pt / pv, ci=[float(np.exp(np.percentile(lr, 2.5))), float(np.exp(np.percentile(lr, 97.5)))],
                                mde_factor=float(np.exp(2.8 * se)), n_routes_t=len({r['route'] for r in tr}))
    # transfer functions / phases
    TF = {}
    for g in ["V282", "V282old", "T64", "TORQUE", "T5", "T64B"]:
        rr = [r for r in G[g] if r["vbin"] is not None]
        rl = [r for r in rr if r["lane_ok"] >= 0.8]
        if not rr:
            continue
        TF[g] = {}
        for x, y in PAIRS:
            use = rl if ("y" in (x, y) or "psi" in (x, y)) else rr
            h = pooled_H(use, x, y)
            if h:
                if (x, y) == ("ad", "apose") or (x, y) == ("y", "ad"):
                    bs = boot(use, lambda s, x=x, y=y: pooled_H(s, x, y)["H"] if pooled_H(s, x, y) else np.nan, B=300)
                    h["H_ci"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))] if len(bs) else None
                    bp = boot(use, lambda s, x=x, y=y: pooled_H(s, x, y)["phase"] if pooled_H(s, x, y) else np.nan, B=300)
                    h["phase_ci"] = [float(np.percentile(bp, 2.5)), float(np.percentile(bp, 97.5))] if len(bp) else None
                TF[g][f"{x}>{y}"] = h
        TF[g]["_lane_ok_sec"] = round(sum(r["sec"] for r in rl), 1)
    # limit-cycle discriminators per run
    percase = []
    for r in R:
        if r["vbin"] is None:
            continue
        f = r["f"]; s = (f >= W[0]) & (f < W[1])
        pxx = r["psd"]["ad"][s]; pyy = r["psd"]["apose"][s]; pxy = r["csd"]["ad>apose"][s]
        coh = float(np.sum(np.abs(pxy)) ** 2 / max(np.sum(pxx) * np.sum(pyy), 1e-30))
        py = r["psd"]["y"] / r["sec"]; sw = (f >= 0.04) & (f < 0.4)
        line = float(np.max(py[sw]) / np.median(py[sw]))
        fpk = float(f[sw][np.argmax(py[sw])])
        percase.append(dict(route=r["route"], group=r["group"], sec=r["sec"], v=r["vmed"], lane_ok=r["lane_ok"],
                            dwell=r["dwell"], rms={k: r["rms"].get(k) for k in SIGS}, coh_ad_apose=coh,
                            y_line_index=line, y_peak_hz=fpk))
    res = dict(tier=TIER, nperseg=NPS, df=float(FS2 / NPS), band=W, vbins=VB, vbin_weights=wts.tolist(), census=census,
               table=table, ratios=ratios, TF=TF, runs=percase)
    (HERE / "results").mkdir(exist_ok=True)
    json.dump(res, open(HERE / "results" / f"fsr_{TIER}_n{NPS}.json", "w"), indent=1)
    # print summary
    print(f"TIER {TIER} nperseg {NPS} df {FS2/NPS:.4f} Hz  vbin weights {np.round(wts,2)}")
    for g, c in census.items():
        print(f"  census {g:8s} runs {c['n_runs']:2d} sec {c['sec']:7.1f} by vbin {c['sec_by_vbin']} unbinned {c['sec_unbinned']}")
    print("  band rms 0.08-0.25 Hz (speed matched):  y[m] psi[mrad] sa[deg] ad apose e [m/s2] out I Ft dob [torque]")
    for g, t in table.items():
        print(f"   {g:8s} y {t['y']:.4f} psi {1e3*t['psi']:.2f} sa {t['sa']:.3f} ad {t['ad']:.4f} apose {t['apose']:.4f} "
              f"e {t['e']:.4f} out {t['out']:.4f} I {t['I']:.4f} Ft {t['Ft']:.4f} dob {t['dob']:.4f}")
    for g, d in ratios.items():
        print("   ratio " + g + "/V282: " + "  ".join(f"{k} {v['ratio']:.2f} [{v['ci'][0]:.2f},{v['ci'][1]:.2f}] MDE x{v['mde_factor']:.2f}" for k, v in d.items()))
    for g, d in TF.items():
        print(f"  TF {g} (lane_ok sec {d['_lane_ok_sec']})")
        for k, h in d.items():
            if k.startswith("_"):
                continue
            extra = f" Hci {np.round(h['H_ci'],2).tolist()} phci {np.round(h['phase_ci'],0).tolist()}" if h.get("H_ci") else ""
            print(f"     {k:10s} |H| {h['H']:.4g} coh {h['coh']:.2f} phase {h['phase']:+.0f} |H|w2 {h['Hw2']:.3g}{extra}")


if __name__ == "__main__":
    main()
