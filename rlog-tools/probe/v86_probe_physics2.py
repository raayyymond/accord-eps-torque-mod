#!/usr/bin/env python3
"""probe/v86_probe_physics2.py -- the corrected pass. Fixes five defects in probe/v86_probe_physics.py:

  1  speed strata were binned in km/h with edges 1..4 -- almost every frame landed in one cell.
  2  the surrogate threshold bisection was run on channels that are THEMSELVES quantised
     (rate_c = 1 deg/s, ang/rate_f = 0.1), so the bisection hit the quantum and the 'match' was
     fictitious. Every surrogate now carries a `matched` flag and unmatched ones are EXCLUDED.
  3  the Schmitt (hysteresis) model had no offset while the static model had one ⇒ a rigged
     comparison. Both models now carry an offset; they are properly NESTED (static = Schmitt at h=0).
  4  no confidence interval on frac_disc.
  5  ★ THE TEST THAT MATTERED WAS MISSING: does the probe carry ANY information the CAN torque
     sensor does not already carry? Build a PREDICTED probe from CAN alone and diff the spectra.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from v86_probe_physics import (ROUTES, decode_route, gap_stats, match_thr,  # noqa: E402
                               run_order_surrogate, welch, zoh_uniform)

RNG = np.random.default_rng(20260808)
VBINS = (0.0, 2.0, 5.0, 8.0, 12.0, 40.0)          # km/h, chosen from the routes' own census


# ---------------------------------------------------------------------------------------------------
# 1.  RELAY vs LINEAR, done properly
# ---------------------------------------------------------------------------------------------------
def boot_frac_disc(gaps, block=25, n=2000):
    nb = len(gaps) // block
    if nb < 4:
        return None
    g = (gaps[:nb * block] == 0).reshape(nb, block)
    o = [g[RNG.integers(0, nb, nb)].mean() for _ in range(n)]
    return [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]


def synth_null(target_gap, n, fs=100.0, reps=6):
    """A CONTINUOUS Gaussian process family -- a null that borrows nothing from this log.

    ★ AND the relabel proof: f(u) = K*sign(u)*|u/s|**p for p in {1, 0.25, 0.05} is a MEMORYLESS
    monotone map, increasingly relay-shaped. At a matched mean gap every one of them returns the
    SAME frac_disc as p = 1, because {f(u) >= th} == {u >= f^-1(th)}. A single-threshold probe is
    therefore BLIND to memoryless shape. This is the structural limit of the whole b7/b6 design.
    """
    out = {}
    for fc in (2.0, 5.0, 10.0, 20.0):
        fd, mg = [], []
        for _ in range(reps):
            w = RNG.standard_normal(n + 2048)
            a = np.exp(-2 * np.pi * fc / fs)       # one-pole low-pass ⇒ a real continuous process
            u = np.empty_like(w)
            u[0] = w[0]
            for i in range(1, len(w)):
                u[i] = a * u[i - 1] + (1 - a) * w[i]
            u = u[2048:]
            th = match_thr(u, target_gap)
            s = gap_stats(u, th)
            if s["n_events"] > 30 and abs(s["mean_gap"] - target_gap) / target_gap < 0.2:
                fd.append(s["frac_disc"])
                mg.append(s["mean_gap"])
        if fd:
            out[f"lowpass_{fc:g}Hz"] = dict(frac_disc=float(np.mean(fd)),
                                            mean_gap=float(np.mean(mg)), reps=len(fd))
    # ---- the relabel proof, on one of those processes ----
    w = RNG.standard_normal(n + 2048)
    a = np.exp(-2 * np.pi * 5.0 / fs)
    u = np.empty_like(w)
    u[0] = w[0]
    for i in range(1, len(w)):
        u[i] = a * u[i - 1] + (1 - a) * w[i]
    u = u[2048:]
    su = np.std(u)
    rel = {}
    for p in (1.0, 0.25, 0.05):
        f = 1000.0 * np.sign(u) * np.abs(u / su) ** p
        th = match_thr(f, target_gap)
        s = gap_stats(f, th)
        rel[f"p={p}"] = dict(frac_disc=s["frac_disc"], mean_gap=s["mean_gap"],
                             thr=float(th), n_events=s["n_events"])
    out["_memoryless_relabel_proof"] = rel
    # ---- a HARD relay: the only shape that is NOT a relabelling, because |f| < th is unreachable ----
    hard = 1000.0 * np.sign(u)
    s = gap_stats(hard, 500.0)
    out["_hard_relay_Y0_ge_64"] = dict(frac_disc=s["frac_disc"], mean_gap=s["mean_gap"],
                                       n_events=s["n_events"], band_duty=s["band_duty"])
    return out


def relay2(tag, z, L):
    x = np.where(np.abs(L) == 2, np.sign(L) * 1000.0, np.sign(L) * 1.0)
    p = gap_stats(x, 500.0)
    out = {"probe": {k: v for k, v in p.items() if k != "gaps"},
           "probe_frac_disc_ci95": boot_frac_disc(p["gaps"])}
    tgt = p["mean_gap"]
    surr = {}
    for name in ("tq", "cs_tq", "rate_c", "rate_f", "ang", "cs_rate"):
        if name not in z.files:
            continue
        v = np.asarray(z[name], float)
        if not np.isfinite(v).all() or np.std(v) == 0:
            continue
        v = v - np.median(v)
        q = float(np.min(np.diff(np.unique(np.abs(v))))) if len(np.unique(v)) > 3 else 0.0
        th = match_thr(v, tgt)
        s = gap_stats(v, th)
        if s["n_events"] < 30:
            continue
        ok = abs(s["mean_gap"] - tgt) / tgt < 0.15 and th > 3 * q
        surr[name] = dict(thr=float(th), quantum=q, thr_over_rms=float(th / np.std(v)),
                          n_events=s["n_events"], frac_disc=s["frac_disc"],
                          frac_disc_ci95=boot_frac_disc(s["gaps"]),
                          mean_gap=s["mean_gap"], band_duty=s["band_duty"],
                          matched=bool(ok),
                          excluded_reason=None if ok else
                          ("gap not matched" if abs(s["mean_gap"] - tgt) / tgt >= 0.15
                           else f"threshold {th:.3g} is below 3x the channel quantum {q:.3g} "
                                "⇒ the surrogate is itself a quantiser, not a continuous signal"))
    out["null_same_log_continuous"] = surr
    out["null_synthetic"] = synth_null(tgt, len(L))
    return out


# ---------------------------------------------------------------------------------------------------
# 2.  what drives it -- full lag curve, nested hysteresis test, and the empirical transfer curve
# ---------------------------------------------------------------------------------------------------
def schmitt(x, c, h):
    o = np.empty(len(x), np.int8)
    cur = 1
    hi, lo = c + h, c - h
    for i, xi in enumerate(x):
        if xi > hi:
            cur = 1
        elif xi < lo:
            cur = -1
        o[i] = cur
    return o


def drivers2(z, L):
    s = np.sign(L).astype(int)
    live = s != 0
    out = {}
    for name in ("tq", "cs_tq", "rate_c", "rate_f", "ang", "cs_rate", "e4tq", "sc_tq", "cs_yaw"):
        if name not in z.files:
            continue
        x = np.asarray(z[name], float)
        if not np.isfinite(x).all() or np.std(x) == 0:
            continue
        x = x - np.median(x)
        curve = {}
        for lag in range(-6, 7):
            xs = np.roll(x, lag)
            m = live.copy()
            if lag > 0:
                m[:lag] = False
            elif lag < 0:
                m[lag:] = False
            a = float((np.sign(xs[m]) == s[m]).mean())
            curve[lag] = max(a, 1 - a)
        bl = max(curve, key=curve.get)
        out[name] = dict(best_lag_frames=int(bl), best_lag_ms=bl * 10.0,
                         sign_agreement=curve[bl],
                         lag_curve={str(k): round(v, 4) for k, v in curve.items()})
    drv = max((k for k in out), key=lambda k: out[k]["sign_agreement"])
    x = np.roll(np.asarray(z[drv], float) - np.median(z[drv]), out[drv]["best_lag_frames"])
    m = s != 0
    pol = 1 if (np.sign(x[m]) == s[m]).mean() >= 0.5 else -1
    xs, ys = pol * x[m], s[m]
    sd = float(np.std(xs))
    cs = np.linspace(-1.0 * sd, 1.0 * sd, 81)
    stat = min(((np.sign(xs - c) != ys).mean(), float(c)) for c in cs)
    hy = min(((schmitt(xs, c, h) != ys).mean(), float(c), float(h))
             for c in cs for h in np.linspace(0.0, 0.8 * sd, 33))
    out["_model_comparison"] = dict(
        driver=drv, polarity=int(pol), lag_frames=out[drv]["best_lag_frames"],
        static=dict(err=float(stat[0]), c=stat[1], params=1),
        schmitt=dict(err=float(hy[0]), c=hy[1], h=hy[2], h_over_sd=float(hy[2] / sd), params=2),
        nested=True,
        verdict=("HYSTERETIC: the Schmitt beats the nested static model by "
                 f"{100 * (stat[0] - hy[0]):.2f} pp of frames"
                 if hy[0] < stat[0] - 0.003 else
                 "NO hysteresis: the best Schmitt width is at or near h=0, i.e. the nested static "
                 "model is not beaten ⇒ gp-0x6b70's SIGN is a MEMORYLESS function of the torque "
                 "sensor to within the probe's resolution"))

    # ---- the EMPIRICAL TRANSFER CURVE: where, in torque-sensor units, does |gp-0x6b70| reach 64? ----
    d = pol * (np.asarray(z[drv], float) - np.median(z[drv]))
    d = np.roll(d, out[drv]["best_lag_frames"]) - out["_model_comparison"]["static"]["c"]
    big = (np.abs(L) == 2)
    edges = np.percentile(np.abs(d), np.linspace(0, 100, 41))
    edges = np.unique(edges)
    tc = []
    for i in range(len(edges) - 1):
        m = (np.abs(d) >= edges[i]) & (np.abs(d) < edges[i + 1])
        if m.sum() < 50:
            continue
        tc.append(dict(abs_tq_lo=float(edges[i]), abs_tq_hi=float(edges[i + 1]),
                       n=int(m.sum()), p_big=float(big[m].mean())))
    knee = next((r for r in tc if r["p_big"] >= 0.5), None)
    out["_transfer_curve"] = dict(
        driver=drv, offset_c=out["_model_comparison"]["static"]["c"],
        curve=tc, rms_driver=float(np.std(d)),
        knee_abs_tq_at_p_big_0p5=(0.5 * (knee["abs_tq_lo"] + knee["abs_tq_hi"]) if knee else None),
        knee_over_rms=((0.5 * (knee["abs_tq_lo"] + knee["abs_tq_hi"]) / np.std(d))
                       if knee else None),
        meaning="the |driver-torque residual| at which |gp-0x6b70| first exceeds 64 more often "
                "than not. A HARD relay with Y[0] >= 64 would put this knee AT ZERO.")
    return out


# ---------------------------------------------------------------------------------------------------
# 3.  ★ does the probe carry anything CAN did not already have?
# ---------------------------------------------------------------------------------------------------
def information_gain(z, L, drv, pol, lag, c, knee, fs=100.0):
    """Predict the probe FROM CAN ALONE with the fitted static model, then diff the spectra."""
    t = np.asarray(z["t"], float)
    d = pol * (np.asarray(z[drv], float) - np.median(z[drv]))
    d = np.roll(d, lag) - c
    pred = np.sign(d) * np.where(np.abs(d) >= knee, 2.0, 1.0)
    meas = L.astype(float)
    agree = float((np.sign(pred) == np.sign(meas)).mean())
    agree_lvl = float((pred == meas).mean())
    _, mg = zoh_uniform(t, meas, fs)
    _, pg = zoh_uniform(t, pred, fs)
    n = min(len(mg), len(pg))
    f, Pm = welch(mg[:n], fs, 1024)
    _, Pp = welch(pg[:n], fs, 1024)
    _, Pr = welch(mg[:n] - pg[:n], fs, 1024)          # the RESIDUAL the CAN model cannot explain
    bands = {"ratchet_7.79": (6.5, 9.5), "grind1_18_22": (18, 22),
             "limit_cycle_27.75": (26, 30), "lanechange_40_49": (40, 49)}
    bb = {}
    for name, (a, b) in bands.items():
        m = (f >= a) & (f <= b)
        bb[name] = dict(measured=float(Pm[m].mean()), predicted_from_CAN=float(Pp[m].mean()),
                        residual=float(Pr[m].mean()),
                        frac_unexplained=float(Pr[m].mean() / Pm[m].mean()))
    return dict(model=f"sign({'+' if pol > 0 else '-'}{drv}[t{lag:+d}] - {c:.1f}) x "
                       f"(|.| >= {knee:.1f} ? 2 : 1)",
                sign_agreement=agree, level_agreement=agree_lvl, bands=bb,
                meaning="`residual` is the part of the probe's spectrum that a model built ONLY "
                        "from the CAN torque sensor cannot reproduce. Small ⇒ the cave measured "
                        "something CAN already carried.")


# ---------------------------------------------------------------------------------------------------
def analyse2(tag):
    cdir, stem, MOD = ROUTES[tag]
    z, b4, L, gate = decode_route(tag)
    t = np.asarray(z["t"], float)
    lat = (np.asarray(z["cc_lat"], float) > 0.5).astype(int)
    v = np.asarray(z["cs_v"], float) * 3.6
    nz, mg = (L != 0), (np.abs(L) == 2)
    res = {"route": tag, "build": ("V86" if tag == "6f" else "V86B"), "frames": int(len(L))}
    res["relay_vs_linear"] = relay2(tag, z, L)
    dr = drivers2(z, L)
    res["sign_drivers"] = dr
    mc, tcv = dr["_model_comparison"], dr["_transfer_curve"]
    knee = tcv["knee_abs_tq_at_p_big_0p5"]
    if knee:
        res["information_gain"] = information_gain(
            z, L, mc["driver"], mc["polarity"], mc["lag_frames"], mc["static"]["c"], knee)

    # ---- speed-stratified engaged/manual, with sane bins ----
    cells = {}
    for e in (0, 1):
        for i in range(len(VBINS) - 1):
            m = (lat == e) & (v >= VBINS[i]) & (v < VBINS[i + 1])
            if m.sum() < 150:
                continue
            cells[f"eng{e}_{VBINS[i]:g}-{VBINS[i+1]:g}kph"] = dict(
                n=int(m.sum()), nonzero=float(nz[m].mean()),
                mag_over_nonzero=float(mg[m].sum() / nz[m].sum()),
                sign_neg=float((L[m] < 0).mean()),
                abs_tq_med=float(np.median(np.abs(np.asarray(z["tq"], float)[m]))))
    res["strata"] = cells
    res["speed_kmh"] = dict(mean=float(np.nanmean(v)), med=float(np.nanmedian(v)),
                            p25=float(np.nanpercentile(v, 25)), p75=float(np.nanpercentile(v, 75)))
    res["engaged_frac"] = float(lat.mean())
    res["mag_over_nonzero"] = float(mg.sum() / nz.sum())
    return res, cells


def main():
    A = {}
    for tag in ("6f", "70"):
        r, cells = analyse2(tag)
        cdir, stem, _ = ROUTES[tag]
        name = "probe_v86_physics2.json" if tag == "6f" else "probe_v86b_physics2.json"
        (ROOT / cdir / name).write_text(json.dumps(r, indent=1), encoding="utf-8")
        A[tag] = r
        print(f"wrote {cdir}/{name}")
    keys = sorted(set(A["6f"]["strata"]) & set(A["70"]["strata"]))
    w = {k: min(A["6f"]["strata"][k]["n"], A["70"]["strata"][k]["n"]) for k in keys}
    tot = sum(w.values()) or 1
    cross = {"common_cells": keys, "weights": w,
             "6f_raw": A["6f"]["mag_over_nonzero"], "70_raw": A["70"]["mag_over_nonzero"],
             "6f_std": sum(w[k] * A["6f"]["strata"][k]["mag_over_nonzero"] for k in keys) / tot,
             "70_std": sum(w[k] * A["70"]["strata"][k]["mag_over_nonzero"] for k in keys) / tot,
             "per_cell": {k: {"6f": A["6f"]["strata"][k]["mag_over_nonzero"],
                              "70": A["70"]["strata"][k]["mag_over_nonzero"],
                              "n6f": A["6f"]["strata"][k]["n"],
                              "n70": A["70"]["strata"][k]["n"],
                              "tq6f": A["6f"]["strata"][k]["abs_tq_med"],
                              "tq70": A["70"]["strata"][k]["abs_tq_med"]} for k in keys}}
    cross["raw_delta"] = cross["70_raw"] - cross["6f_raw"]
    cross["standardised_delta"] = cross["70_std"] - cross["6f_std"]
    (ROOT / "_scratch/cache/r6f" / "probe_v86_cross_route2.json").write_text(
        json.dumps(cross, indent=1), encoding="utf-8")
    print(json.dumps(cross, indent=1))
    return A


if __name__ == "__main__":
    main()
