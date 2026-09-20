# -*- coding: utf-8 -*-
"""Stage 2: the |H| SURFACE. speed x frequency x demand amplitude, V282 (rate-servo EPS) vs torque mode.

MEASUREMENT of a closed-loop transfer from a logged input and a logged output. No model, no simulator.
  input  X = the MODEL's desired lateral accel  (controlsState.desiredCurvature * v^2)
  output Y = achieved lateral accel             (livePose angularVelocityDevice.z * v)
  extra  Z = the controller's own shaped setpoint (controlsState...torqueState.desiredLateralAccel)
Both X and Y are defined identically for the two EPS modes, which is why |H| is comparable between them
even though V282's wire command is a RATE request and torque mode's is a TORQUE request.

Per cell (group x speed bin x frequency band x demand-amplitude stratum), with the seconds and window
count behind every number:
  |H|        power-weighted mean of the per-bin MAGNITUDE |Pxy|/Pxx (never a phasor average)
  lag_ms     from the band cross-phase at the band centre (robust); gdelay_ms from a phase-slope fit
             (printed only where the band holds >=4 bins)
  M_coh      sqrt( sum |H_bin - 1|^2 Pxx / sum Pxx ): the COHERENT tracking misfit, in units of the
             demand's own in-band RMS.  This is the goal's own metric.  Split exactly into
             M_gain (|H|-1) and M_phase (2|H|(1-cos phi)), and bias-corrected for estimator variance.
  M_al       what M_coh would be if the whole cell's lag were perfectly compensated (best common delay
             removed): the part of the miss that is NOT timing.
  M_inc      the part of the output the demand does not explain (road, roll, sensor, nonlinearity).
             M^2 = M_coh^2 + M_inc^2 exactly.
  H_xz/H_zy  the fork's own reference shaping (model -> its setpoint) and the rest of the loop
             (setpoint -> achieved): says whether a gain excess is the fork's shaping or the car.
  floors     coherence + its 95% null floor; SPLIT-HALF |H|; SURROGATE |H| (each window's input against
             a different window's output). |H| not clear of the surrogate => the cell is noise.
  CI         route-cluster bootstrap (resample the group's routes with replacement).

ANALYSIS ONLY, read-only.  usage: python surface.py > SURFACE-OUT.txt
"""
import json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
SPDN = ["0-8", "8-15", "15-22", "22+"]
ACUT = [(0.0, 0.3), (0.3, 1.0), (1.0, 99.0)]
ACUTN = ["A1 <0.3", "A2 .3-1", "A3 >=1"]
BANDS = [(0.06, 0.15, 40.96), (0.15, 0.30, 20.48), (0.30, 0.60, 10.24),
         (0.60, 1.20, 10.24), (1.20, 2.40, 5.12), (2.40, 4.00, 5.12)]
XCHECK = [(0.15, 0.30, 40.96), (0.30, 0.60, 20.48), (1.20, 2.40, 10.24), (0.60, 1.20, 5.12)]
BASE = ["V282", "V282old", "T64", "T64B", "T5", "T4", "T3", "T2"]
TORQUE_REVS = ["T64", "T64B", "T5", "T4", "T3", "T2"]
# pooled comparators: mixing fork revs is a confound, but single revs give n=1-3 windows in most cells
POOL = {"TORQ": TORQUE_REVS, "T64F": ["T64", "T64B"]}
GRPS = BASE + list(POOL)
rng = np.random.default_rng(7)
MINWIN = 6


def cellstats(Pxx, Pyy, Pxy, fr, n_ind, Pzz=None, Pxz=None, Pzy=None, fast=False):
    w = Pxx
    Hb = Pxy / np.maximum(Pxx, 1e-300)
    aH = np.abs(Hb); phb = np.angle(Hb)
    coh = np.clip(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-300), 1e-6, 1.0)
    H = float(np.average(aH, weights=w))
    mg2 = float(np.average((aH - 1.0) ** 2, weights=w))
    mp2 = float(np.average(2 * aH * (1 - np.cos(phb)), weights=w))
    mc2 = mg2 + mp2
    var = float(np.average(aH ** 2 * (1 - coh) / np.maximum(coh * 2 * n_ind, 1e-9), weights=w))
    inc = float(np.average(np.maximum(Pyy - np.abs(Pxy) ** 2 / np.maximum(Pxx, 1e-300), 0.0) /
                           np.maximum(Pxx, 1e-300), weights=w))
    # best common delay removed: the part of the miss that is not timing
    if fast:
        best = (mc2, 0.0)
    else:
        taus = np.arange(-0.10, 0.901, 0.005)
        R = aH[None, :] * np.exp(1j * (phb[None, :] + 2 * np.pi * taus[:, None] * fr[None, :])) - 1.0
        mm = (np.abs(R) ** 2 * w[None, :]).sum(1) / w.sum()
        k = int(np.argmin(mm)); best = (float(mm[k]), float(taus[k]))
    fc = float(np.average(fr, weights=w))
    phc = float(np.angle((Pxy * w).sum()))
    gd = float("nan")
    if len(fr) >= 4 and not fast:
        ww = w * coh
        A = np.vstack([2 * np.pi * fr, np.ones_like(fr)]).T
        sol = np.linalg.lstsq(A * ww[:, None] ** 0.5, np.unwrap(phb) * ww ** 0.5, rcond=None)[0]
        gd = -sol[0] * 1000.0
    d = dict(H=H, coh=float(np.average(coh, weights=w)),
             M_gain=math.sqrt(max(mg2, 0)), M_phase=math.sqrt(max(mp2, 0)),
             M_coh=math.sqrt(max(mc2, 0)), M_coh_bc=math.sqrt(max(mc2 - var, 0.0)),
             bias=math.sqrt(max(var, 0)), M_inc=math.sqrt(max(inc, 0)),
             M=math.sqrt(max(mc2 + inc, 0)), M_al=math.sqrt(max(best[0], 0)), tau_al_ms=best[1] * 1000,
             phase=math.degrees(phc), fc=fc, lag_ms=-math.degrees(phc) / 360.0 / max(fc, 1e-9) * 1000.0,
             gdelay_ms=gd, nbins=len(fr))
    if Pxz is not None:
        d["H_xz"] = float(np.average(np.abs(Pxz) / np.maximum(Pxx, 1e-300), weights=w))
        d["H_zy"] = float(np.average(np.abs(Pzy) / np.maximum(Pzz, 1e-300), weights=Pzz))
    return d


def main():
    inv = {r["route"]: r for r in json.load(open(HERE / "inv.json"))}
    rgrp = {r: inv[r]["group"] for r in inv}
    out, exposure = {}, {}

    D = np.load(HERE / "spec_10.24.npz", allow_pickle=True)
    grp_all, sb_all, ap_all = D["group"], D["sbin"], D["am_p95"]
    for g in GRPS:
        mem = POOL.get(g, [g])
        eng = [sum(inv[r]["per_spd"][i] for r in inv if inv[r]["group"] in mem) for i in range(4)]
        for i in range(4):
            m = np.isin(grp_all, mem) & (sb_all == i)
            tot = int(m.sum())
            for j, (lo, hi) in enumerate(ACUT):
                n = int((m & (ap_all >= lo) & (ap_all < hi)).sum())
                exposure[(g, i, j)] = dict(sec=eng[i] * (n / tot if tot else 0.0), nwin=n, nwin_tot=tot)
    del D

    print("=" * 152)
    print("EXPOSURE: laterally-engaged seconds per speed bin x demand-amplitude stratum")
    print("  amplitude stratum = p95 |model desired lateral accel| over a 10.24 s window, FIXED cuts so the")
    print("  exposure fractions mean something (terciles would make every stratum 1/3 by construction).")
    print("=" * 152)
    print(f"{'group':9s} {'eng_s':>7s} " + " ".join(f"{SPDN[i]+'/'+ACUTN[j][:2]:>11s}" for i in range(4) for j in range(3)))
    for g in BASE + ["TORQ"]:
        tot = sum(exposure[(g, i, j)]["sec"] for i in range(4) for j in range(3))
        if tot < 1:
            continue
        print(f"{g:9s} {tot:7.0f} " + " ".join(f"{exposure[(g,i,j)]['sec']:6.0f}({exposure[(g,i,j)]['sec']/tot*100:3.0f}%)"
                                              for i in range(4) for j in range(3)))
    torq_tot = sum(exposure[("TORQ", i, j)]["sec"] for i in range(4) for j in range(3))
    print(f"\n  TORQUE pooled {torq_tot:.0f} s laterally engaged; V282 reference "
          f"{sum(exposure[('V282',i,j)]['sec'] for i in range(4) for j in range(3)):.0f} s")
    print("  where the TORQUE-mode car actually is (its own exposure fractions):")
    for i in range(4):
        print(f"    v {SPDN[i]:6s} " + "   ".join(f"{ACUTN[j]}: {exposure[('TORQ',i,j)]['sec']:6.0f}s "
              f"{exposure[('TORQ',i,j)]['sec']/torq_tot*100:4.1f}%" for j in range(3)))

    # ---------- the surface ----------
    for f1, f2, W in BANDS + XCHECK:
        tag = f"{f1:.2f}-{f2:.2f}Hz@{W:.2f}s"
        D = np.load(HERE / f"spec_{W:.2f}.npz", allow_pickle=True)
        fr = np.arange(D["X"].shape[1]) / W
        sel = (fr >= f1) & (fr < f2)
        if sel.sum() < 1:
            continue
        fb = fr[sel]
        Xb, Yb, Zb = D["X"][:, sel], D["Y"][:, sel], D["Z"][:, sel]
        g_, sb_, ap_, rt_, rail_, sap_ = D["group"], D["sbin"], D["am_p95"], D["route"], D["rail"], D["sa_p95"]
        for i in range(4):
            for j, (alo, ahi) in enumerate(ACUT):
                base = (sb_ == i) & (ap_ >= alo) & (ap_ < ahi)
                for g in GRPS:
                    idx = np.flatnonzero(base & np.isin(g_, POOL.get(g, [g])))
                    if len(idx) == 0:
                        continue
                    n_ind = max(2, int(math.ceil(len(idx) / 2)))
                    P = lambda A, B, k=idx: (np.conj(A[k]) * B[k]).sum(0)
                    Pxx = (np.abs(Xb[idx]) ** 2).sum(0)
                    Pyy = (np.abs(Yb[idx]) ** 2).sum(0); Pzz = (np.abs(Zb[idx]) ** 2).sum(0)
                    st = cellstats(Pxx, Pyy, P(Xb, Yb), fb, n_ind, Pzz, P(Xb, Zb), P(Zb, Yb))
                    hh = []
                    for par in (0, 1):
                        k = idx[par::2]
                        if len(k) >= 2:
                            hh.append(cellstats((np.abs(Xb[k]) ** 2).sum(0), (np.abs(Yb[k]) ** 2).sum(0),
                                                P(Xb, Yb, k), fb, max(2, len(k) // 2), fast=True)["H"])
                    st["H_sh"] = abs(hh[0] - hh[1]) / 2 if len(hh) == 2 else float("nan")
                    if len(idx) >= 4:
                        rot = np.roll(idx, len(idx) // 2)
                        st["H_surr"] = cellstats(Pxx, (np.abs(Yb[rot]) ** 2).sum(0),
                                                 (np.conj(Xb[idx]) * Yb[rot]).sum(0), fb, n_ind, fast=True)["H"]
                    else:
                        st["H_surr"] = float("nan")
                    rs = sorted(set(rt_[idx]))
                    if len(rs) >= 2:
                        per = {r: np.flatnonzero(base & (rt_ == r)) for r in rs}
                        bs, bm = [], []
                        for _ in range(400):
                            kk = np.concatenate([per[r] for r in rng.choice(rs, len(rs))])
                            c = cellstats((np.abs(Xb[kk]) ** 2).sum(0), (np.abs(Yb[kk]) ** 2).sum(0),
                                          P(Xb, Yb, kk), fb, max(2, len(kk) // 2), fast=True)
                            bs.append(c["H"]); bm.append(c["M_coh"])
                        st["H_lo"], st["H_hi"] = [float(x) for x in np.percentile(bs, [2.5, 97.5])]
                        st["M_lo"], st["M_hi"] = [float(x) for x in np.percentile(bm, [2.5, 97.5])]
                    else:
                        st["H_lo"] = st["H_hi"] = st["M_lo"] = st["M_hi"] = float("nan")
                    # Hann one-sided band-RMS scale, verified against a known sine to 0.06%:
                    # rms^2 = sum|X|^2 * 16/(3 N^2 nwin)
                    nrm = 16.0 / (3.0 * (W * 100.0) ** 2 * len(idx))
                    st.update(nwin=len(idx), n_ind=n_ind, nroutes=len(rs), routes=list(rs),
                              sec=len(idx) * W * 0.5, coh_floor=1 - 0.05 ** (1 / max(n_ind - 1, 1)),
                              rail=float(rail_[idx].mean()), sa_p95=float(np.median(sap_[idx])),
                              in_rms=float(math.sqrt(Pxx.sum() * nrm)),
                              out_rms=float(math.sqrt(Pyy.sum() * nrm)))
                    out[f"{tag}|{SPDN[i]}|{ACUTN[j]}|{g}"] = st
        del D, Xb, Yb, Zb

    json.dump(out, open(HERE / "surface.json", "w"), indent=1, default=float)

    # Band-level causality, decided by the UNWRAPPED time-domain direction test in extras.py (EVIDENCE):
    # band-passed model demand vs achieved lateral accel, cross-correlation peak searched over +-800 ms,
    # pooled over routes.  0.15-1.20 Hz peaks at +300..+480 ms (car follows plan).  1.20-2.40 Hz peaks at
    # +60..+90 ms, consistent with the measured 55-75 ms loop delay.  2.40-4.00 Hz peaks at 0/+10 ms with
    # corr 0.52 -- a ZERO-LAG common component, i.e. the planner echoing the car (desiredCurvature is
    # computed from the measured state), NOT the car tracking the plan.  So |H| there is not a tracking
    # number and that band is reported as output power instead (extras.py section C).
    NONCAUSAL_BANDS = {(2.40, 4.00)}

    def causal(s, band=None):
        return band not in NONCAUSAL_BANDS


    def adm(s, band=None):
        return bool(s and s["nwin"] >= MINWIN and s["coh"] > max(s["coh_floor"], 0.20)
                    and (not np.isfinite(s["H_surr"]) or s["H"] > 2.0 * s["H_surr"])
                    and s["bias"] ** 2 < 0.4 * max(s["M_coh"] ** 2, 1e-9)
                    and causal(s, band))

    SHOW = ["V282", "V282old", "TORQ", "T64F", "T64", "T64B", "T5", "T4", "T3", "T2"]
    for f1, f2, W in BANDS:
        tag = f"{f1:.2f}-{f2:.2f}Hz@{W:.2f}s"
        print("\n" + "=" * 152)
        print(f"BAND {f1:.2f}-{f2:.2f} Hz   (window {W:.2f} s, df {1/W:.4f} Hz, "
              f"{int(((np.arange(int(5*W)+1)/W>=f1)&(np.arange(int(5*W)+1)/W<f2)).sum())} bins)")
        print("=" * 152)
        print(f"{'speed':6s} {'amp':8s} {'group':8s} {'n':>3s} {'sec':>5s} {'|H|':>5s} {'[95%CI]':>13s} {'coh':>4s} "
              f"{'flr':>4s} {'sur':>4s} {'sh':>4s} {'Mcoh':>5s} {'bc':>5s} {'Mgai':>5s} {'Mpha':>5s} {'M_al':>5s} "
              f"{'Minc':>5s} {'lag':>6s} {'gd':>6s} {'Hxz':>5s} {'Hzy':>5s} {'inRMS':>6s} {'ouRMS':>6s} {'rail':>6s} {'sa95':>5s} a  why")
        for i in range(4):
            for j in range(3):
                any_row = False
                for g in SHOW:
                    s = out.get(f"{tag}|{SPDN[i]}|{ACUTN[j]}|{g}")
                    if not s:
                        continue
                    any_row = True
                    ci = f"[{s['H_lo']:.2f},{s['H_hi']:.2f}]" if np.isfinite(s["H_lo"]) else "[1 route]"
                    print(f"{SPDN[i]:6s} {ACUTN[j]:8s} {g:8s} {s['nwin']:3d} {s['sec']:5.0f} {s['H']:5.3f} {ci:>13s} "
                          f"{s['coh']:4.2f} {s['coh_floor']:4.2f} {s['H_surr']:4.2f} {s['H_sh']:4.2f} "
                          f"{s['M_coh']:5.3f} {s['M_coh_bc']:5.3f} {s['M_gain']:5.3f} {s['M_phase']:5.3f} "
                          f"{s['M_al']:5.3f} {s['M_inc']:5.3f} {s['lag_ms']:6.0f} {s['gdelay_ms']:6.0f} "
                          f"{s['H_xz']:5.2f} {s['H_zy']:5.2f} {s['in_rms']:6.4f} {s['out_rms']:6.4f} "
                          f"{s['rail']:6.4f} {s['sa_p95']:5.1f} {'Y' if adm(s, (f1, f2)) else '.'}  "
                          + ("" if adm(s, (f1, f2)) else ",".join(
                              (["n<6"] if s['nwin'] < MINWIN else []) +
                              (["coh"] if not s["coh"] > max(s["coh_floor"], 0.20) else []) +
                              (["surr"] if (np.isfinite(s["H_surr"]) and not s["H"] > 2 * s["H_surr"]) else []) +
                              (["bias"] if not s["bias"] ** 2 < 0.4 * max(s["M_coh"] ** 2, 1e-9) else []) +
                              (["NONCAUSAL-BAND"] if not causal(s, (f1, f2)) else []) +
                              (["phase-wrap-risk"] if abs(s["phase"]) > 150 else []))))
                if any_row:
                    print("")

    print("\n" + "=" * 152)
    print("CROSS-SCALE CONSISTENCY: the same band read at two window lengths (leakage / df control)")
    print("=" * 152)
    for f1, f2, W in XCHECK:
        prim = next((b for b in BANDS if abs(b[0] - f1) < 1e-9 and abs(b[1] - f2) < 1e-9), None)
        if not prim:
            continue
        for i in range(4):
            for j in range(3):
                for g in ("V282", "TORQ", "T64F"):
                    a = out.get(f"{f1:.2f}-{f2:.2f}Hz@{prim[2]:.2f}s|{SPDN[i]}|{ACUTN[j]}|{g}")
                    b = out.get(f"{f1:.2f}-{f2:.2f}Hz@{W:.2f}s|{SPDN[i]}|{ACUTN[j]}|{g}")
                    if a and b and adm(a, (f1, f2)) and adm(b, (f1, f2)):
                        print(f"   {f1:.2f}-{f2:.2f} {SPDN[i]:6s} {ACUTN[j]:8s} {g:6s} |H| {a['H']:.3f}@{prim[2]:.0f}s "
                              f"vs {b['H']:.3f}@{W:.0f}s ({100*abs(a['H']-b['H'])/max(a['H'],1e-9):4.1f}%)  "
                              f"Mcoh {a['M_coh_bc']:.3f} vs {b['M_coh_bc']:.3f}  lag {a['lag_ms']:.0f} vs {b['lag_ms']:.0f} ms")

    # ---------- ranked miss table ----------
    for comp in ("TORQ", "T64F"):
        print("\n" + "=" * 152)
        print(f"RANKED: where {comp} misses V282 most, weighted by the torque routes' own laterally-engaged exposure")
        print("  dM = M_coh(bias-corrected, torque) - M_coh(V282). score = dM x exposure fraction of that speed x amp cell.")
        print("=" * 152)
        rows = []
        for f1, f2, W in BANDS:
            tag = f"{f1:.2f}-{f2:.2f}Hz@{W:.2f}s"
            for i in range(4):
                for j in range(3):
                    ref = out.get(f"{tag}|{SPDN[i]}|{ACUTN[j]}|V282")
                    tq = out.get(f"{tag}|{SPDN[i]}|{ACUTN[j]}|{comp}")
                    exp = exposure[("TORQ", i, j)]["sec"] / max(torq_tot, 1e-9)
                    r = dict(band=f"{f1:.2f}-{f2:.2f}", spd=SPDN[i], amp=ACUTN[j], exp=exp)
                    if not (ref and tq) or not (adm(ref, (f1, f2)) and adm(tq, (f1, f2))):
                        why = []
                        for nm, s in (("V282", ref), (comp, tq)):
                            if not s:
                                why.append(f"{nm} no windows")
                            elif not adm(s, (f1, f2)):
                                why.append(f"{nm} n{s['nwin']} coh{s['coh']:.2f}/flr{s['coh_floor']:.2f} "
                                           f"surr{s['H_surr']:.2f} bias{s['bias']:.2f} lag{s['lag_ms']:.0f}ms"
                                           f"{' NONCAUSAL-BAND' if not causal(s, (f1, f2)) else ''}"
                                           f"{' phase-wrap-risk' if abs(s['phase']) > 150 else ''}")
                        r["why"] = "; ".join(why) or "ok"
                    else:
                        r.update(dM=tq["M_coh_bc"] - ref["M_coh_bc"], H_v=ref["H"], H_t=tq["H"],
                                 Mv=ref["M_coh_bc"], Mt=tq["M_coh_bc"], MGv=ref["M_gain"], MGt=tq["M_gain"],
                                 MPv=ref["M_phase"], MPt=tq["M_phase"], MAv=ref["M_al"], MAt=tq["M_al"],
                                 lv=ref["lag_ms"], lt=tq["lag_ms"], iv=ref["M_inc"], it=tq["M_inc"],
                                 nv=ref["nwin"], nt=tq["nwin"], Hxzv=ref["H_xz"], Hxzt=tq["H_xz"],
                                 Hzyv=ref["H_zy"], Hzyt=tq["H_zy"])
                        r["score"] = r["dM"] * exp
                    rows.append(r)
        good = sorted([r for r in rows if "score" in r], key=lambda r: -r["score"])
        print(f"{'#':3s} {'band Hz':10s} {'speed':6s} {'amp':8s} {'exp%':>5s} {'|H|V':>5s} {'|H|T':>5s} {'M_V':>5s} "
              f"{'M_T':>5s} {'dM':>6s} {'score':>7s} {'Mgain V/T':>11s} {'Mpha V/T':>11s} {'M_al V/T':>11s} "
              f"{'lag V/T ms':>12s} {'Minc V/T':>10s} {'Hxz V/T':>10s} {'Hzy V/T':>10s} {'n V/T':>8s}")
        for k, r in enumerate(good):
            print(f"{k+1:3d} {r['band']:10s} {r['spd']:6s} {r['amp']:8s} {r['exp']*100:5.1f} {r['H_v']:5.2f} "
                  f"{r['H_t']:5.2f} {r['Mv']:5.3f} {r['Mt']:5.3f} {r['dM']:+6.3f} {r['score']:+7.4f} "
                  f"{r['MGv']:5.2f}/{r['MGt']:5.2f} {r['MPv']:5.2f}/{r['MPt']:5.2f} {r['MAv']:5.2f}/{r['MAt']:5.2f} "
                  f"{r['lv']:5.0f}/{r['lt']:5.0f} {r['iv']:4.2f}/{r['it']:4.2f} {r['Hxzv']:4.2f}/{r['Hxzt']:4.2f} "
                  f"{r['Hzyv']:4.2f}/{r['Hzyt']:4.2f} {r['nv']:3d}/{r['nt']:3d}")
        cov = {}
        for r in good:
            cov[(r["spd"], r["amp"])] = r["exp"]
        print(f"\n  {len(good)} of {len(rows)} cells readable in BOTH builds. Distinct speed x amp cells covered: "
              f"{len(cov)} of 12, = {100*sum(cov.values()):.1f}% of torque-mode laterally-engaged time.")
        print("  CELLS THAT COULD NOT BE READ (printed, not silently dropped):")
        for r in sorted([r for r in rows if "why" in r], key=lambda r: -r["exp"]):
            print(f"    {r['band']:10s} {r['spd']:6s} {r['amp']:8s} exp {r['exp']*100:5.1f}%  {r['why']}")
        if comp == "TORQ":
            json.dump(dict(rows=rows, exposure={f"{k[0]}|{k[1]}|{k[2]}": v for k, v in exposure.items()}),
                      open(HERE / "ranked.json", "w"), indent=1, default=float)

    print("\nwrote surface.json, ranked.json")


if __name__ == "__main__":
    main()
