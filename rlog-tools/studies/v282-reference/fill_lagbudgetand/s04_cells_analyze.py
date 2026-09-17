"""Step 3/4 (cells): lag budget per group x speed bin x band x demand tercile, logged and common lead, with hierarchical
bootstrap CIs (routes with replacement, then 60-s chunks within route; each group resampled independently), and the
shaping lag PREDICTED by the code-exact transfer function (lagmod.chain_H) at the cell's power-weighted frequency.
out: s04_cells.json, s04_cells.txt"""
import sys, json, glob
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lagmod import chain_H, phase_lag, ROUTE_CFG, COMMITS

HERE = Path(__file__).resolve().parent
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
NB = 500
rng = np.random.default_rng(7)
D = {}
for f in sorted(glob.glob(str(HERE / "_cells" / "*.npz"))):
    z = np.load(f); M = json.loads(str(z["meta"]))
    D[M["route"]] = dict(keys=z["keys"], vals=z["vals"], meta=M)
PAIRS = [tuple(p) for p in next(iter(D.values()))["meta"]["pairs"]]
BANDS = next(iter(D.values()))["meta"]["bands"]; VBN = next(iter(D.values()))["meta"]["vb"]
PI = {p: i for i, p in enumerate(PAIRS)}


def lag_from(vec, p):
    i = PI[p]
    S, W, Wf = vec[..., 1 + 3 * i], vec[..., 2 + 3 * i].real, vec[..., 3 + 3 * i].real
    fbar = Wf / np.maximum(W, 1e-30)
    return -np.angle(S) / (2 * np.pi * np.maximum(fbar, 1e-6)), fbar


def cell_vecs(group, b, k, terc):
    """list per route of (chunk vec array)"""
    out = []
    for r, d in D.items():
        if d["meta"]["group"] != group:
            continue
        s = (d["keys"][:, 0] == b) & (d["keys"][:, 1] == k) & ((d["keys"][:, 2] == terc) if terc >= 0 else True)
        if not s.any():
            continue
        kk = d["keys"][s]; vv = d["vals"][s]
        # merge terciles within the same chunk (so 'all' resamples chunks, not tercile rows)
        ch = kk[:, 3]; uc, inv = np.unique(ch, return_inverse=True)
        agg = np.zeros((len(uc), vv.shape[1]), complex)
        np.add.at(agg, inv, vv)
        out.append((r, agg))
    return out


def boot(vecs):
    tot = np.zeros((NB, vecs[0][1].shape[1]), complex)
    for bI in range(NB):
        for ri in rng.integers(0, len(vecs), len(vecs)):
            a = vecs[ri][1]
            tot[bI] += a[rng.integers(0, len(a), len(a))].sum(0)
    return tot


def pred_lag(group_routes, fbar):
    """shaping lag predicted by the transfer function, sample-weighted over the group's routes (each route: its flown ld/fc/rc)."""
    L = []; w = []
    for r, n in group_routes:
        c = ROUTE_CFG[r]; H = chain_H([fbar], D[r]["meta"]["ld"], COMMITS[c["commit"]]["jerk_fc"], c["ref_rc"])
        L.append(float(phase_lag(H, [fbar])[0])); w.append(n)
    return float(np.average(L, weights=w))


SEGS = [("x", "sp", "model->setpoint"), ("sp", "act", "setpoint->la_act"), ("act", "pose", "la_act->la_pose"),
        ("x", "pose", "model->la_pose"), ("x", "act", "model->la_act"), ("xc", "sp", "COMMON model->setpoint"),
        ("xc", "pose", "COMMON model->la_pose"), ("xc", "act", "COMMON model->la_act"), ("x", "ctl", "CONTROL (0.300)")]
res = []
cache = {}
for b in range(len(BANDS)):
    for k in range(len(VBN)):
        for terc in (0, 1, 2, -1):
            base = {}
            for g in GROUPS:
                vecs = cell_vecs(g, b, k, terc)
                if not vecs:
                    continue
                pt = sum(a.sum(0) for _, a in vecs)
                n = pt[0].real
                if n * 1 / 100 < 20:     # < 20 s in cell (samples at 100 Hz)
                    continue
                bt = boot(vecs)
                cell = dict(group=g, band=f"{BANDS[b][0]}-{BANDS[b][1]}", vb=VBN[k], terc=["lo", "mid", "hi", "all"][terc],
                            sec=float(n / 100), nroutes=len(vecs))
                for a_, b_, nm in SEGS:
                    L, fb = lag_from(pt, (a_, b_)); Lb, _ = lag_from(bt, (a_, b_))
                    cell[nm] = float(L); cell[nm + "_ci"] = [float(np.percentile(Lb, 2.5)), float(np.percentile(Lb, 97.5))]
                    cell[nm + "_boot"] = Lb
                    if (a_, b_) == ("x", "sp"):
                        cell["fbar"] = float(fb)
                cell["pred_shaping"] = pred_lag([(r, a[:, 0].real.sum()) for r, a in vecs], cell["fbar"])
                base[g] = cell
            if "V282" not in base:
                continue
            for g, c in base.items():
                for a_, b_, nm in SEGS:
                    if g != "V282":
                        dB = c[nm + "_boot"] - base["V282"][nm + "_boot"]
                        c[nm + "_gap"] = c[nm] - base["V282"][nm]
                        c[nm + "_gap_ci"] = [float(np.percentile(dB, 2.5)), float(np.percentile(dB, 97.5))]
                c["pred_shaping_gap"] = c["pred_shaping"] - base["V282"]["pred_shaping"]
            for g, c in base.items():
                res.append({kk: vv for kk, vv in c.items() if not kk.endswith("_boot")})
        print("band", BANDS[b], "vb", VBN[k], "done", flush=True)
json.dump(res, open(HERE / "s04_cells.json", "w"), indent=1)

# ---- text table
L = []
def f3(x): return f"{x:+.3f}" if x is not None and np.isfinite(x) else "  n/a "
for g in GROUPS[1:]:
    L.append(f"\n##### {g} minus V282  (lags in s; gap [95% CI]; pred = transfer-function shaping gap)")
    L.append(f"{'vb':6s}{'band':10s}{'terc':5s}{'sec V/T':>10s} | {'x->sp':>22s} {'pred':>7s} | {'sp->act':>22s} | {'act->pose':>22s} | {'x->pose':>22s} | {'COMMON x->pose':>22s} | ctlV/T")
    for c in res:
        if c["group"] != g:
            continue
        ref = next(r for r in res if r["group"] == "V282" and r["band"] == c["band"] and r["vb"] == c["vb"] and r["terc"] == c["terc"])
        def s(nm):
            return f"{c[nm+'_gap']:+.3f}[{c[nm+'_gap_ci'][0]:+.2f},{c[nm+'_gap_ci'][1]:+.2f}]"
        L.append(f"{c['vb']:6s}{c['band']:10s}{c['terc']:5s}{ref['sec']:5.0f}/{c['sec']:<4.0f} | {s('model->setpoint'):>22s} {c['pred_shaping_gap']:+.3f} | {s('setpoint->la_act'):>22s} | "
                 f"{s('la_act->la_pose'):>22s} | {s('model->la_pose'):>22s} | {s('COMMON model->la_pose'):>22s} | {ref['CONTROL (0.300)']:.3f}/{c['CONTROL (0.300)']:.3f}")
L.append("\n##### absolute lags, V282 (x->sp, sp->act, act->pose, x->pose; pred shaping)")
for c in res:
    if c["group"] == "V282":
        L.append(f"{c['vb']:6s}{c['band']:10s}{c['terc']:5s}{c['sec']:6.0f}s  x->sp {c['model->setpoint']:+.3f} (pred {c['pred_shaping']:+.3f})  sp->act {c['setpoint->la_act']:+.3f}  act->pose {c['la_act->la_pose']:+.3f}  x->pose {c['model->la_pose']:+.3f}")
open(HERE / "s04_cells.txt", "w").write("\n".join(L))
print("\n".join(L[:80]))
