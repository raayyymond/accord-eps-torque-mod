# -*- coding: utf-8 -*-
"""L3 -- pool windows ACROSS the routes of a build family and read the loop off the pool.

Pooling is valid inside a family because every estimator here is a ratio of window-averaged
cross-spectra and every route in a family flew the SAME kp, LAF and ki (checked, and asserted).
Bootstrap unit = the contiguous engaged run, resampled within its route, routes resampled too.

Prints, per family x speed bin:
   the plant |P| and its lag, coherence-gated
   |L_pid|, arg L, |S| across 0.1-4 Hz
   crossover (first and last downward crossing), phase margin, gain margin, Ms, f(|S|>1)
   and the GAIN-TO-CROSSOVER: the factor on kp/LAF that would put |L| = 1 at each frequency.
"""
import json
import sys
from pathlib import Path

import numpy as np

import lp_lib as LP

OUT = Path(__file__).resolve().parent / "out"
FAM = {
    "V282":    ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
    "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"],
    "T64":     ["0000006c--68c6e94b17", "0000006d--05e83bb04f"],
    "T64B":    ["0000006e--6ca3e014fd"],
    "T5":      ["00000076--d0b7ea7e4d"],
    "T4":      ["00000075--6c8687d5bd"],
    "RF00T":   ["00000070--717f5a7866"],
    "T2":      ["00000071--f2c9d073a3"],
    "T3":      ["00000072--8001fc3048"],
}
NBOOT = 600


def gather(routes, vlo, vhi, nps):
    """Per-window FFTs for every route in the family, with (route, run) cluster labels."""
    Fs, labs, vs = [], [], []
    for ri, route in enumerate(routes):
        L = LP.load_loop(route)
        wins = LP.windows(L, vlo, vhi, nps, nps // 2)
        if len(wins) < 3:
            del L
            continue
        f, F, vmed = LP.win_fft(L, wins, nps)
        edges = [(a, b) for a, b in LP.V.runs(LP.runs_mask(L), L["t"], min_s=nps / LP.FS)]
        lab = [(ri, next((k for k, (a, b) in enumerate(edges) if a <= s < b), -1)) for s, e, _ in wins]
        Fs.append(F); labs += lab; vs.append(vmed)
        del L
    if not Fs:
        return None, None, None, None
    F = {k: np.concatenate([g[k] for g in Fs], axis=0) for k in Fs[0]}
    return np.fft.rfftfreq(nps, LP.DT), F, np.array(labs, dtype=object), np.concatenate(vs)


def crossings(f, mag, lo, hi):
    s = (f >= lo) & (f <= hi)
    ff, mm = f[s], mag[s]
    k = np.where((mm[:-1] >= 1) & (mm[1:] < 1))[0]
    out = []
    for j in k:
        w = np.log(mm[j]) / (np.log(mm[j]) - np.log(mm[j + 1]))
        out.append(float(ff[j] + w * (ff[j + 1] - ff[j])))
    return out


def phase_at(f, Lc, fq):
    ph = np.unwrap(np.angle(Lc))
    return float(np.interp(fq, f, ph))


def metrics(f, Lc, lo=0.10, hi=4.0):
    mag = np.abs(Lc)
    xs = crossings(f, mag, lo, hi)
    out = dict(n_cross=len(xs), wc_first=xs[0] if xs else np.nan, wc_last=xs[-1] if xs else np.nan)
    for nm, fc in (("first", out["wc_first"]), ("last", out["wc_last"])):
        if np.isfinite(fc):
            p = np.degrees(np.angle(np.exp(1j * phase_at(f, Lc, fc))))
            out[f"pm_{nm}"] = float(180.0 + p)
        else:
            out[f"pm_{nm}"] = np.nan
    # gain margin: unwrapped phase reaching -180 above the first crossover (or above 0.1 Hz)
    s = (f >= lo) & (f <= hi)
    ff, LL = f[s], Lc[s]
    ph = np.unwrap(np.angle(LL))
    ph = ph - 2 * np.pi * np.round(ph[0] / (2 * np.pi))
    out["gm"], out["gm_f"] = np.nan, np.nan
    for k in range(len(ff) - 1):
        if ph[k] > -np.pi >= ph[k + 1]:
            w = (ph[k] + np.pi) / (ph[k] - ph[k + 1])
            out["gm_f"] = float(ff[k] + w * (ff[k + 1] - ff[k]))
            m = np.exp(np.log(np.abs(LL[k])) + w * (np.log(np.abs(LL[k + 1])) - np.log(np.abs(LL[k]))))
            out["gm"] = float(1.0 / m)
            break
    Sm = np.abs(1.0 / (1.0 + LL))
    k = int(np.argmax(Sm))
    out["Ms"], out["f_Ms"] = float(Sm[k]), float(ff[k])
    up = np.where(Sm > 1.0)[0]
    out["f_S1"] = float(ff[up[0]]) if len(up) else np.nan
    return out


def run_family(fam, routes, tag, vlo, vhi, nps):
    f, F, lab, vmed = gather(routes, vlo, vhi, nps)
    if F is None or len(lab) < 8:
        return None
    ident = {r["route"]: r for r in json.load(open(OUT / "L0_ident.json"))}
    kps = {ident[r]["kp_med"] for r in routes if r in ident}
    lafs = {ident[r]["laf_med"] for r in routes if r in ident}
    assert len(kps) == 1 and len(lafs) == 1, (fam, kps, lafs)
    kp, laf = kps.pop(), lafs.pop()
    R = LP.loop_from_F(F, instr="r")
    vb = float(np.median(vmed))
    fl = LP.FLOWN[routes[0]]
    Can = LP.c_fb_analytic(f, kp, float(LP.ki_of(vb, fl["ki"], fl["ki_hi"])), laf,
                           float(LP.low_speed_factor(vb)),
                           float(LP.mode_hz(vb)) if fl["notch"] else None, 1.0)
    keys = sorted({tuple(x) for x in lab})
    kidx = {k: np.where([tuple(x) == k for x in lab])[0] for k in keys}
    rng = np.random.default_rng(99)
    uniq_r = sorted({k[0] for k in keys})
    boot = []
    for _ in range(NBOOT):
        rr = rng.choice(uniq_r, size=len(uniq_r), replace=True) if len(uniq_r) > 1 else uniq_r
        idx = []
        for r0 in rr:
            ks = [k for k in keys if k[0] == r0]
            pick = rng.choice(len(ks), size=len(ks), replace=True)
            idx += [kidx[ks[q]] for q in pick]
        idx = np.concatenate(idx)
        Rb = LP.loop_from_F(F, idx=idx, instr="r")
        boot.append(Rb["L"])
    boot = np.array(boot)
    return dict(fam=fam, tag=tag, nps=nps, kp=kp, laf=laf, kp_laf=kp / laf, v=vb,
                n_win=len(lab), n_run=len(keys), n_route=len(uniq_r), f=f,
                P=R["P"], C=R["Cfb"], Can=Can, L=R["L"], Lan=R["P"] * Can,
                coh=R["coh_wu"], cohy=R["coh_wy"], Pdir=R["P_dir"], Try=R["Try"], boot=boot)


def show(res, fqs=(0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0)):
    f, L, P, C, coh = res["f"], res["L"], res["P"], res["C"], res["coh"]
    mB = np.abs(res["boot"])
    print(f"--- {res['fam']:8s} {res['tag']:6s} nps {res['nps']}  v {res['v']:.1f}  "
          f"{res['n_route']}rt/{res['n_run']}run/{res['n_win']}win  kp/LAF {res['kp_laf']:.4f}  df {f[1]-f[0]:.3f} Hz")
    print(f"{'f':>5} {'coh':>5} {'|P|':>6} {'Plag':>5} {'|C|':>7} {'C/Can':>6} {'|L|':>6} "
          f"{'[5,95]':>13} {'argL':>6} {'|S|':>5} {'x to |L|=1':>10}")
    for fq in fqs:
        j = int(np.argmin(np.abs(f - fq)))
        lag = (180.0 - np.degrees(np.angle(P[j])) + 180) % 360 - 180
        lo, hi = np.percentile(mB[:, j], [5, 95])
        S = abs(1.0 / (1.0 + L[j]))
        fl = " " if coh[j] >= LP.COH_GATE else ("~" if coh[j] >= LP.COH_SOFT else "?")
        print(f"{f[j]:5.2f}{fl}{coh[j]:5.2f} {abs(P[j]):6.2f} {lag:5.0f} {abs(C[j]):7.4f} "
              f"{abs(C[j])/abs(res['Can'][j]):6.3f} {abs(L[j]):6.3f} [{lo:5.2f},{hi:5.2f}] "
              f"{np.degrees(np.angle(L[j])):6.0f} {S:5.2f} {1.0/max(abs(L[j]),1e-9):10.2f}")
    m = metrics(f, L)
    bm = [metrics(f, b) for b in res["boot"]]

    def ci(k):
        a = np.array([x[k] for x in bm], float)
        a = a[np.isfinite(a)]
        return (f"[{np.percentile(a,5):.3g},{np.percentile(a,95):.3g}] ({len(a)*100//len(bm)}%)") if len(a) >= 30 else "[--]"
    print(f"   crossings {m['n_cross']}  wc_first {m['wc_first']:.3f} {ci('wc_first')}  PM {m['pm_first']:.0f} {ci('pm_first')}")
    print(f"   GM {m['gm']:.2f} {ci('gm')} at {m['gm_f']:.2f} Hz | Ms {m['Ms']:.2f} {ci('Ms')} at {m['f_Ms']:.2f} Hz"
          f" | f(|S|>1) {m['f_S1']:.2f} {ci('f_S1')}")
    print()
    return m


if __name__ == "__main__":
    bins = [("15-22", 15.0, 22.0), ("22+", 22.0, 99.0), ("8-15", 8.0, 15.0), ("15+", 15.0, 99.0)]
    want = sys.argv[1:] or ["15-22", "22+", "8-15"]
    store = {}
    for tag, vlo, vhi in bins:
        if tag not in want:
            continue
        for nps in (1024, 4096):
            print("=" * 110)
            print(f"SPEED BIN {tag} m/s   nperseg {nps} ({nps/LP.FS:.1f} s windows)")
            print("=" * 110)
            for fam, routes in FAM.items():
                try:
                    res = run_family(fam, routes, tag, vlo, vhi, nps)
                except AssertionError as ex:
                    print(f"  {fam}: heterogeneous gains {ex}"); continue
                if res is None:
                    continue
                m = show(res)
                store[f"{fam}|{tag}|{nps}"] = dict(
                    fam=fam, tag=tag, nps=nps, kp_laf=res["kp_laf"], v=res["v"],
                    n_win=res["n_win"], n_run=res["n_run"],
                    f=res["f"].tolist(), coh=res["coh"].tolist(),
                    P_re=res["P"].real.tolist(), P_im=res["P"].imag.tolist(),
                    L_re=res["L"].real.tolist(), L_im=res["L"].imag.tolist(),
                    C_re=res["C"].real.tolist(), C_im=res["C"].imag.tolist(),
                    Can_re=res["Can"].real.tolist(), Can_im=res["Can"].imag.tolist(),
                    Try_re=res["Try"].real.tolist(), Try_im=res["Try"].imag.tolist(),
                    Lb5=np.percentile(np.abs(res["boot"]), 5, axis=0).tolist(),
                    Lb95=np.percentile(np.abs(res["boot"]), 95, axis=0).tolist(),
                    m={k: (None if not np.isfinite(v) else float(v)) for k, v in m.items()})
    json.dump(store, open(OUT / "L3_pool.json", "w"))
    print(f"wrote {OUT/'L3_pool.json'}")
