"""ADV-bytes (p-gain) step 5: is R-PLATEAU's baseline (a_base = 0.938 on r71b) a property of the INSTRUMENT, or of
r71b's command distribution?  The pre-registered read divides a NEW drive's plateau slope by r71b's baseline; if the
baseline moves drive to drive, the "1.00 +- 0.05" / "1.30 +- 0.05" bands do not transfer.

Test: the six V293 routes (r70 rev1, r71 rev2, r72/r73 rev3, r75 rev4, r76 rev5).  V293's FF is BIT-IDENTICAL to
V294's ((sp<<5)*120 >> 8 == (sp<<2)*960 >> 8 == 15*sp for every sp) and V293's trim is 0 (C = 0), so on V293 the tap
IS V294's FF regressor + the instrument's noise.  Their plateau slope is an independent draw of what V294's baseline
would be on another drive.  Also r71b with F alone vs F+R, and a quantiser-aware regressor (quant(F)) as a remedy."""
import contextlib, io, os, sys, json
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (HERE, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant"),
          os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"), os.path.join(KIT, "rlog-tools", "studies", "grind"),
          os.path.join(KIT, "analysis-2020accord", "model")):
    sys.path.insert(0, p)
import advp_lane as AL
with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR
import plib as P

K294 = AL.kp_table((0, 68, 112, 136, 208), (960,) * 5)
KC = AL.kp_table((0, 8, 54, 100, 208), (1248, 1248, 1104, 960, 960))
assert all(((sp << 5) * 120) >> 8 == ((sp << 2) * 960) >> 8 for sp in range(-1100, 1101))


def regress(yy, cols, mask):
    X = np.vstack([c[mask] for c in cols] + [np.ones(mask.sum())]).T
    co, *_ = np.linalg.lstsq(X, yy[mask], rcond=None)
    return co


def route_ff(tag):
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route(tag, "V293")
    g = r.g
    c = r.c
    n = len(g["t"])
    m100 = FR.fade_multiplier(c, g["bar"], g["vego"], "bar")[:n]
    idx100, sgn100 = FR.GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    idx = np.clip(np.round(idx100[:n]), 0, 240).astype(int)
    sgn = (-np.asarray(sgn100[:n])).astype(int)
    T = {}
    for nm, kt in (("V294", K294), ("CAND", KC)):
        T[nm] = np.array(AL.march(sgn, idx, m100, kt, trim=False), float)
    t100 = g["t"][:n]
    t_tap, T_tap = g["T_t"], g["T"].astype(float)
    keep = (t_tap > t100[0]) & (t_tap < t100[-1])
    t_tap, T_tap = t_tap[keep], T_tap[keep]
    j = np.clip(np.searchsorted(t100, t_tap, side="right") - 1, 0, n - 1)
    sub = np.clip(np.round((t_tap - t100[j]) * 1000).astype(int), 0, 9)
    eng = np.asarray(g["eng"][:n], bool)
    ho = eng[j] & (np.abs(g["bar"][:n][j]) < 400)
    best = None
    for dd in range(-40, 41):
        tk = np.clip(10 * j + sub + dd, 0, len(T["V294"]) - 1)
        for sg in (1, -1):
            v = np.var((T_tap - sg * AL.quant(T["V294"][tk]))[ho])
            if best is None or v < best[0]:
                best = (v, dd, sg)
    _, dd, sg = best
    tk = np.clip(10 * j + sub + dd, 0, len(T["V294"]) - 1)
    return dict(y=T_tap, F=sg * T["V294"][tk], Fc=sg * T["CAND"][tk], idx_t=idx[j], ho=ho, j=j, eng=eng, dms=dd, sg=sg,
                resid=float(np.sqrt(best[0])), dur=float(eng.sum() / 100))


rows = {}
for tag in ("r70_v293", "r71_v293r2", "r72_v293r3", "r73_v293r3", "r75_v293r4", "r76_v293r5"):
    R = route_ff(tag)
    ok = R["ho"] & (np.abs(R["y"]) < 2300)
    pl = ok & (R["idx_t"] < 9)
    a_all = regress(R["y"], (R["F"],), ok)[0]
    a_pl = regress(R["y"], (R["F"],), pl)[0]
    a_plq = regress(R["y"], (AL.quant(R["F"]),), pl)[0]
    # synthetic CAND flight on this route: quant(cand FF) + this route's own residual
    noise = R["y"] - AL.quant(R["F"])
    yc = AL.quant(R["Fc"]) + noise
    a_c = regress(yc, (R["F"],), pl & (np.abs(yc) < 2300))[0]
    a_cq = regress(yc, (AL.quant(R["F"]),), pl & (np.abs(yc) < 2300))[0]
    # 20 s engaged windows: the per-window plateau read against r71b's 0.938 and against this route's own baseline
    ef = np.flatnonzero(R["eng"])
    win = []
    for a0 in range(0, len(ef) - 2000 + 1, 2000):
        lo, hi = ef[a0], ef[a0 + 1999]
        mm = pl & (R["j"] >= lo) & (R["j"] <= hi)
        if mm.sum() >= 150:
            win.append((regress(R["y"], (R["F"],), mm)[0], regress(yc, (R["F"],), mm & (np.abs(yc) < 2300))[0]))
    win = np.array(win)
    rows[tag] = dict(eng_s=R["dur"], plateau_s=float(pl.sum() / 50), dms=R["dms"], sg=R["sg"], resid=R["resid"], a_all=float(a_all),
                     a_plateau=float(a_pl), a_plateau_quantF=float(a_plq), cand_a=float(a_c), cand_ratio_own=float(a_c / a_pl),
                     cand_ratio_vs_r71b=float(a_c / 0.9379), cand_a_quantF=float(a_cq), n_win=len(win),
                     null_vs_r71b=[float(np.percentile(win[:, 0] / 0.9379, q)) for q in (2.5, 50, 97.5)] if len(win) else None,
                     cand_vs_r71b=[float(np.percentile(win[:, 1] / 0.9379, q)) for q in (2.5, 50, 97.5)] if len(win) else None,
                     null_out_band=float(np.mean(np.abs(win[:, 0] / 0.9379 - 1) > 0.05)) if len(win) else None,
                     cand_out_band=float(np.mean(np.abs(win[:, 1] / 0.9379 - 1.30) > 0.05)) if len(win) else None)
    r = rows[tag]
    print("%-11s eng %4.0f s, plateau %4.0f s, tap dms %+d sg %+d resid %.2f | a_all %.4f  a_plateau %.4f (quant-aware %.4f) | synthetic CAND: a %.4f -> ratio own %.3f, vs r71b base %.3f (quant-aware %.3f) | 20 s windows %d: V294 read vs r71b base %s (out of 1+-0.05: %.0f %%) CAND %s (out of 1.30+-0.05: %.0f %%)"
          % (tag, r["eng_s"], r["plateau_s"], r["dms"], r["sg"], r["resid"], r["a_all"], r["a_plateau"], r["a_plateau_quantF"],
             r["cand_a"], r["cand_ratio_own"], r["cand_ratio_vs_r71b"], r["cand_a_quantF"] / r["a_plateau_quantF"], r["n_win"],
             np.round(r["null_vs_r71b"], 3) if r["n_win"] else None, 100 * (r["null_out_band"] or 0),
             np.round(r["cand_vs_r71b"], 3) if r["n_win"] else None, 100 * (r["cand_out_band"] or 0)))

# r71b, same F-only / quantiser-aware forms for comparison
d = P.load()
tk, j = d["tick_tap"], d["j100"]
y = d["T_tap"].astype(float)
F, R = d["T1k_null"][tk], d["T1k_live"][tk] - d["T1k_null"][tk]
ok = d["ho"][j] & (np.abs(y) < 2300)
pl = ok & (d["idx"][j] < 9)
print("r71b_v294   a_plateau F+R %.4f ; F only %.4f ; quant-aware (quant(F+R) split) %.4f"
      % (regress(y, (F, R), pl)[0], regress(y, (F,), pl)[0], regress(y, (AL.quant(F + R) - R, R), pl)[0]))
aps = np.array([rows[t]["a_plateau"] for t in rows])
print("V293 routes a_plateau: mean %.4f sd %.4f min %.4f max %.4f  -> as a ratio to r71b's 0.9379: %.3f .. %.3f"
      % (aps.mean(), aps.std(), aps.min(), aps.max(), aps.min() / 0.9379, aps.max() / 0.9379))
json.dump(rows, open(os.path.join(HERE, "out", "advp5_crossroute.json"), "w"), indent=1, default=float)
