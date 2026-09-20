# -*- coding: utf-8 -*-
"""L1 -- identify the L34 loop per route x speed bin x window length, and bootstrap its margins.

One route in memory at a time.  For each (route, speed bin, nperseg):
  * P (instrumental-variable, instrument = the shaped setpoint r), with coherence
  * C_fb  measured  AND  analytic from the MEASURED kp/ki/LAF, the low-speed factor and the notch
  * L_pid = P * C_fb          -- the PID's own loop
  * K_y   = the TOTAL map from measured state to command (PID + inner rate loop + observer),
    from the reference-projected residuals;  L_tot = -P * K_y
  * S = 1/(1+L), T, margins, and a run-cluster bootstrap of every margin
  * the static wheel-angle gain  Kvm = d(la_act)/d(steering angle)  so P can be read in deg/torque
"""
import json
import sys
from pathlib import Path

import numpy as np

import lp_lib as LP

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
NBOOT = 400
NPSS = (1024, 2048, 4096)


def run_labels(L, wins, nps):
    edges = [(a, b) for a, b in LP.V.runs(LP.runs_mask(L), L["t"], min_s=nps / LP.FS)]
    return np.array([next((k for k, (a, b) in enumerate(edges) if a <= s < b), -1) for s, e, _ in wins])


def summarise(f, Lc, lo=0.10, hi=4.0):
    m = LP.margins(f, Lc, lo, hi)
    out = {k: m[k] for k in ("wc", "pm", "gm", "gm_f", "Ms", "f_Ms", "f_S1", "magmax", "f_magmax")}
    mag, ph = np.abs(Lc), np.degrees(np.angle(Lc))
    Sm = np.abs(1.0 / (1.0 + Lc))
    for fq in (0.15, 0.2, 0.3, 0.45, 0.6, 0.9, 1.2, 1.8, 2.4, 3.0):
        j = int(np.argmin(np.abs(f - fq)))
        out[f"magL_{fq}"] = float(mag[j])
        out[f"phL_{fq}"] = float(ph[j])
        out[f"magS_{fq}"] = float(Sm[j])
    return out


def do_route(route):
    L = LP.load_loop(route)
    fl = LP.FLOWN[route]
    ident = {r["route"]: r for r in json.load(open(OUT / "L0_ident.json"))}[route]
    kp, laf = ident["kp_med"], ident["laf_med"]
    res = dict(route=route, group=LP.GROUPS[route], eps=fl["eps"], kp=kp, laf=laf,
               kp_over_laf=kp / laf, flown=dict(fl), bins={})
    for nps in NPSS:
        hop = nps // 2
        for tag, vlo, vhi in LP.BINS:
            wins = LP.windows(L, vlo, vhi, nps, hop)
            if len(wins) < 6:
                continue
            f, F, vmed = LP.win_fft(L, wins, nps)
            lab = run_labels(L, wins, nps)
            uniq = np.unique(lab)
            if len(uniq) < 2:
                continue
            R = LP.loop_from_F(F, instr="r")
            TT = LP.total_loop(F)
            Ltot = -R["P"] * TT["Ky"]
            vb = float(np.median(vmed))
            lsf = float(LP.low_speed_factor(vb))
            kib = float(LP.ki_of(vb, fl["ki"], fl["ki_hi"]))
            f0 = float(LP.mode_hz(vb)) if fl["notch"] else None
            Can = LP.c_fb_analytic(f, kp, kib, laf, lsf, f0, 1.0)
            Lan = R["P"] * Can
            # static angle gain (m/s^2 of la_act per degree of steering angle), measured
            msk = LP.runs_mask(L) & (L["v"] >= vlo) & (L["v"] < vhi)
            sa = np.nan_to_num(L["sa"])[msk]
            yy = np.nan_to_num(L["y"])[msk]
            kvm = float(np.dot(sa, yy) / max(np.dot(sa, sa), 1e-9))
            # bootstrap over RUNS
            rng = np.random.default_rng(1234)
            keys = ("wc", "pm", "gm", "Ms", "f_Ms", "f_S1", "magmax", "f_magmax",
                    "magL_0.15", "magL_0.3", "magL_0.6", "magL_0.9", "magL_1.2", "magL_1.8",
                    "magS_0.3", "magS_0.6", "magS_0.9", "magS_1.2", "magS_1.8")
            bs = {f"{w}_{k}": [] for w in ("pid", "tot") for k in keys}
            for _ in range(NBOOT):
                pick = rng.choice(uniq, size=len(uniq), replace=True)
                idx = np.concatenate([np.where(lab == q)[0] for q in pick])
                Rb = LP.loop_from_F(F, idx=idx, instr="r")
                Tb = LP.total_loop(F, idx=idx)
                for w, Lb in (("pid", Rb["L"]), ("tot", -Rb["P"] * Tb["Ky"])):
                    sm = summarise(f, Lb)
                    for k in keys:
                        bs[f"{w}_{k}"].append(sm[k])
            ci = {}
            for k, v in bs.items():
                a = np.array(v, float)
                a = a[np.isfinite(a)]
                ci[k] = [float(np.percentile(a, 5)), float(np.percentile(a, 95)), float(len(a)) / NBOOT] if len(a) >= 20 else None
            res["bins"][f"{tag}|{nps}"] = dict(
                tag=tag, nps=nps, n_win=len(wins), n_run=int(len(uniq)), v_med=vb, lsf=lsf,
                ki_bin=kib, notch_hz=f0, kvm=kvm, df=float(f[1] - f[0]),
                f=f.tolist(),
                coh_ru=R["coh_wu"].tolist(), coh_yu=TT["coh_yu"].tolist(),
                P_re=R["P"].real.tolist(), P_im=R["P"].imag.tolist(),
                Pdir_re=R["P_dir"].real.tolist(), Pdir_im=R["P_dir"].imag.tolist(),
                C_re=R["Cfb"].real.tolist(), C_im=R["Cfb"].imag.tolist(),
                Can_re=Can.real.tolist(), Can_im=Can.imag.tolist(),
                Ky_re=TT["Ky"].real.tolist(), Ky_im=TT["Ky"].imag.tolist(),
                Lpid_re=R["L"].real.tolist(), Lpid_im=R["L"].imag.tolist(),
                Ltot_re=Ltot.real.tolist(), Ltot_im=Ltot.imag.tolist(),
                Lan_re=Lan.real.tolist(), Lan_im=Lan.imag.tolist(),
                Try_re=R["Try"].real.tolist(), Try_im=R["Try"].imag.tolist(),
                m_pid=summarise(f, R["L"]), m_tot=summarise(f, Ltot), m_an=summarise(f, Lan),
                ci=ci)
    del L
    return res


if __name__ == "__main__":
    for route in (sys.argv[1:] or list(LP.FLOWN)):
        if not (LP.V.CACHE / f"{route}.npz").exists():
            continue
        r = do_route(route)
        json.dump(r, open(OUT / f"L1_{route}.json", "w"))
        print(f"{route} {r['group']:7s} kp/LAF {r['kp_over_laf']:.4f}  bins: "
              + ", ".join(f"{k}:{v['n_win']}w/{v['n_run']}r" for k, v in r["bins"].items()), flush=True)
