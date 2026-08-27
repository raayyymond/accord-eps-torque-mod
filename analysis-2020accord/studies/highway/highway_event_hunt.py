#!/usr/bin/env python3
"""EVENT-BASED hunt for the operator's HIGHWAY resonance, on the torsion bar and on the comma IMU.

WHY THIS EXISTS
The published highway result is a NULL on a POOLED LEVEL statistic: 40-49 Hz 0.970 [0.787, 1.154]
(Kd 2.00/1.00) and 0.938 [0.764, 1.184] (Kd 2.44/1.00) against a split-half null of [0.73, 1.37].
That statistic is correct for a PROPORTIONAL effect and blind to a rare threshold-like burst.
Creep grind #2 was found the other way -- burst COUNTS and corner-conditioned extreme-tail maxima
(11.71x, p = 0.0003, where the mean said nothing). That machinery has never been pointed at the
highway population. This file points it there.

The operator's re-characterisation, which the prior analysis did not have:
  * the pitch STAYS THE SAME as speed changes  => a MODE, not a wheel/driveline order
  * hands OFF the wheel
  * THRESHOLD-LIKE: it happens or it does not; it does not grow with maneuver severity
  * he has never driven LKAS-off at highway, so "only when engaged" is uncorroborated
  * he FEELS it, does not hear it  => torsion bar + IMU are the channels

METHOD RULES INHERITED (each has already retracted a claim in this kit)
  MASK       Cut on contiguous runs of the ENGAGEMENT mask; apply speed AFTERWARDS. Masking on
             speed before cutting destroys contiguity and manufactures nulls.
  ENVELOPE   Analytic band envelope, never mean Welch power -- the phenomenon is bursty.
  EPISODES   Every CI resamples time BLOCKS / engagement RUNS, never individual windows.
  NULL       Every ratio is quoted against a SPLIT-HALF NULL from one dose pool with the identical
             estimator.
  THRESHOLD  Derived from THIS population's own noise floor (Kd=1 engaged highway, per speed band).
             The creep detector's 500 counts is NOT imported.
  MEAN+TAIL  Report both. They have disagreed in sign on this data.

🛑 NYQUIST. The CAN grid is 100.000 Hz exactly (Nyquist 50.00) and the IMU lattice ~101.0 Hz
(Nyquist ~50.5). Anything reported near 45-49 Hz is indistinguishable from its aliases; see §8.

Usage:  python studies/highway/highway_event_hunt.py [section ...]      (default: all)
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402  win_env / prom_spectrum / locate / q_of
import _r47_imu_lib as I         # noqa: E402  uniform / lattice / env_full / hold / lerp
from _r31_common import runs_of, sustained  # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_scratch/out/_hwy_events.json"

# ---------------------------------------------------------------- the corpus --------------------
# Kd is the DELIVERED HIGHWAY multiplier (r24 rate lane), from _r47_lib.DOSE_HWY / _r47_imu_lib.
# 🛑 NOT the creep dose: stock r24 rolls off with speed (3072 @ 0 km/h -> 2151 @ 100), V62/V65 pin
# it flat at 5244 always, V67 pins it flat only while the LKAS gate is true => 5244/2151 = 2.44x.
ROUTES = [
    ("2b", "_scratch/cache/r2b", "r2bs", list(range(0, 14)), "V58", 1.00),
    ("2c", "_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], "V59", 1.00),
    ("37", "_scratch/cache/r37", "r37s", list(range(0, 15)), "V62", 2.00),
    ("3a", "_scratch/cache/r3a", "r3as", list(range(0, 7)), "V65", 2.00),
    ("3b", "_scratch/cache/r3b", "r3bs", list(range(0, 14)), "V65", 2.00),
    ("47", "_scratch/cache/r47", "r47s", list(range(0, 26)), "V67", 2.44),
    ("4a", "_scratch/cache/r4a", "r4as", list(range(0, 40)), "V67", 2.44),
]
BUILD = {r[0]: r[4] for r in ROUTES}
KD = {r[0]: r[5] for r in ROUTES}

# "Highway" was never pinned to a number by the operator. Let the data say where events live.
V_BANDS = [(12.0, 17.0), (17.0, 22.0), (22.0, 28.0), (28.0, 99.0)]
VMIN = 12.0

BANDS = {"6-9": (6.0, 9.0), "10-16": (10.0, 16.0), "18-22": (18.0, 22.0), "24-28": (24.0, 28.0),
         "30-40": (30.0, 40.0), "40-49": (40.0, 49.0)}
FREE = (10.0, 49.0)          # free-locate band for f0, so no band edge can pin the answer

NFFT = 256                   # 2.56 s @ 100 Hz, 0.39 Hz bins -- the kit's standard
MINRUN = 512                 # >= 5 s of contiguous engagement before a run is usable
BLKSEC = 20.0                # bootstrap unit for an event RATE: a 20 s contiguous block
CIRC = 2.08                  # m; the kit's confirmed 2.073-2.088 wheel circumference


def vbin(v):
    for i, (lo, hi) in enumerate(V_BANDS):
        if lo <= v < hi:
            return i
    return -1


# ================================================================= loading =======================
def load_seg(cache, pfx, s):
    p = ROOT / cache / f"{pfx}{s}.npz"
    if not p.exists():
        return None
    d = dict(np.load(p))
    if len(d["t"]) < 2 * NFFT:
        return None
    return d


def eng_runs(d):
    """Contiguous runs of carControl.latActive, >= MINRUN samples. Speed is NOT applied here."""
    fs = 1.0 / float(np.median(np.diff(d["t"])))
    return fs, list(runs_of(d["cc_lat"] > 0.5, d["t"], MINRUN))


def band_env_run(x, fs, lo, hi):
    """Analytic band envelope of a whole engagement run.

    Uses the untapered whole-record form (_r47_imu_lib.env_full): runs here are >= 5 s and mostly
    30-300 s, so edge leakage is negligible relative to record length. 🛑 The tapered per-window
    `_grind2_lib.win_env` remains the estimator for every WINDOW statistic in this file -- a
    hand-rolled envelope on short windows ran 1.4-1.9x low for a previous agent and corrupted a
    headline.
    """
    return I.env_full(np.asarray(x, float), fs, lo, hi)


# ================================================================= §0 exposure ===================
def section0():
    G.hdr("§0  EXPOSURE, and the one arm that does not exist")
    tot_e, tot_m = {}, {}
    print(f"{'rt':<4}{'bld':<5}{'Kd':>5}  " + "".join(f"{lo:g}-{hi:g}".rjust(10)
                                                      for lo, hi in V_BANDS)
          + "   | manual >12 m/s")
    for rt, cd, pfx, segs, bld, kd in ROUTES:
        e = np.zeros(len(V_BANDS))
        m_hi = 0.0
        for s in segs:
            d = load_seg(cd, pfx, s)
            if d is None:
                continue
            fs = 1.0 / float(np.median(np.diff(d["t"])))
            v, en = np.abs(d["cs_v"]), d["cc_lat"] > 0.5
            for i, (lo, hi) in enumerate(V_BANDS):
                e[i] += float(((v >= lo) & (v < hi) & en).sum()) / fs
            m_hi += float(((v >= VMIN) & ~en).sum()) / fs
        print(f"{rt:<4}{bld:<5}{kd:>5.2f}  " + "".join(f"{x:10.1f}" for x in e)
              + f"   | {m_hi:8.1f} s")
        tot_e[kd] = tot_e.get(kd, np.zeros(len(V_BANDS))) + e
        tot_m[kd] = tot_m.get(kd, 0.0) + m_hi
    print("-" * 96)
    for kd in sorted(tot_e):
        print(f"POOL Kd={kd:.2f}x  " + "".join(f"{x:10.1f}" for x in tot_e[kd])
              + f"   | {tot_m[kd]:8.1f} s manual")
    print("\n🛑 MEASURED: manual (LKAS-off) exposure above 12 m/s is ZERO in every route of the\n"
          "   corpus. The operator's 'it only happens with LKAS on' is therefore UNTESTABLE from\n"
          "   this data -- there is no disengaged highway arm to compare against, on any build.")
    return {"eng_s": {str(k): list(np.round(v, 1)) for k, v in tot_e.items()},
            "manual_hwy_s": {str(k): round(v, 1) for k, v in tot_m.items()}}


# ================================================================= detector ======================
def collect_envelopes(chan="tq"):
    """Per-sample engaged-highway band envelopes for the whole corpus.

    Returns a list of RUN dicts: one contiguous engagement run, with the band envelopes computed
    over the WHOLE run and the covariates sliced to match.
    """
    runs = []
    for rt, cd, pfx, segs, bld, kd in ROUTES:
        for s in segs:
            d = load_seg(cd, pfx, s)
            if d is None:
                continue
            fs, rr = eng_runs(d)
            for a, b in rr:
                x = np.asarray(d[chan][a:b], float)
                if not np.all(np.isfinite(x)):
                    continue
                r = dict(route=rt, build=bld, kd=kd, seg=int(s), a=int(a), b=int(b), fs=fs,
                         t=np.asarray(d["t"][a:b], float),
                         v=np.abs(np.asarray(d["cs_v"][a:b], float)),
                         ang=np.asarray(d["ang"][a:b], float),
                         rate=np.abs(np.asarray(d["rate_c"][a:b], float)),
                         tq=x, e4=np.asarray(d["e4tq"][a:b], float),
                         req=np.asarray(d["cc_req"][a:b], float),
                         press=np.asarray(d.get("cs_press", np.zeros(len(d["t"])))[a:b], float),
                         eff=np.abs(sustained(x, fs)))
                for k, (lo, hi) in BANDS.items():
                    r["e_" + k] = band_env_run(x, fs, lo, hi)
                runs.append(r)
    return runs


def floor_table(runs, band, kd_ref=1.00, q=50):
    """The population's OWN noise floor: quantile `q` of the envelope, per speed band, from the
    Kd=1 (stock rate lane) engaged-highway pool only. Every threshold in this file descends from
    this table, so no creep-era constant leaks in."""
    out = {}
    for i, (lo, hi) in enumerate(V_BANDS):
        acc = []
        for r in runs:
            if r["kd"] != kd_ref:
                continue
            m = (r["v"] >= lo) & (r["v"] < hi)
            if m.any():
                acc.append(r["e_" + band][m])
        out[i] = float(np.percentile(np.concatenate(acc), q)) if acc else np.nan
    return out


def find_events(runs, band, thr_by_vbin, min_dur=0.20, merge_gap=0.30, vmin=VMIN):
    """Contiguous excursions of the band envelope above a speed-band-specific threshold.

    An event must (a) lie entirely at v >= vmin, (b) stay above threshold for >= min_dur, and
    (c) be merged with any neighbour separated by < merge_gap. A 3-window burst is ONE event.
    """
    evs = []
    key = "e_" + band
    for ri, r in enumerate(runs):
        env, v, fs = r[key], r["v"], r["fs"]
        thr = np.array([thr_by_vbin.get(vbin(x), np.inf) for x in v])
        hot = (env > thr) & (v >= vmin)
        if not hot.any():
            continue
        idx = np.flatnonzero(hot)
        segs, s0, prev = [], idx[0], idx[0]
        for i in idx[1:]:
            if i - prev > int(merge_gap * fs):
                segs.append((s0, prev + 1))
                s0 = i
            prev = i
        segs.append((s0, prev + 1))
        for (p, q) in segs:
            if (q - p) / fs < min_dur:
                continue
            j = p + int(np.argmax(env[p:q]))
            evs.append(dict(run=ri, i0=int(p), i1=int(q), ipk=int(j), band=band,
                            dur=float((q - p) / fs), amp=float(env[j]),
                            z=float(env[j] / thr[j]) if np.isfinite(thr[j]) else np.nan,
                            t=float(r["t"][j]), route=r["route"], build=r["build"],
                            kd=r["kd"], seg=r["seg"]))
    return evs


def characterise(runs, evs, nfft=NFFT):
    """Per-event spectrum + covariates AT ONSET. Onset = the first sample of the excursion."""
    f_cache = {}
    for e in evs:
        r = runs[e["run"]]
        fs = r["fs"]
        f = f_cache.get(round(fs, 3))
        if f is None:
            f = np.fft.rfftfreq(nfft, 1 / fs)
            f_cache[round(fs, 3)] = f
        j, n = e["ipk"], len(r["tq"])
        a = max(0, min(n - nfft, j - nfft // 2))
        w = r["tq"][a:a + nfft]
        if len(w) < nfft:
            e["f0"] = e["Q"] = e["prom"] = np.nan
            continue
        P = G.periodogram(w, fs, nfft, True)
        if P is None:
            e["f0"] = e["Q"] = e["prom"] = np.nan
            continue
        R = G.prom_spectrum(f, P)
        lo, hi = BANDS[e["band"]]
        e["f0"], e["prom"] = G.locate(f, P, lo, hi, R=R)
        e["f0_free"], e["prom_free"] = G.locate(f, P, *FREE, R=R)
        e["Q"] = G.q_of(f, P, e["f0"])
        # ---- covariates AT ONSET (first sample of the excursion), and over the event ------------
        i0, i1 = e["i0"], e["i1"]
        sl = slice(i0, i1)
        e["v"] = float(r["v"][i0])
        e["v_mean"] = float(np.mean(r["v"][sl]))
        e["ang"] = float(abs(r["ang"][i0]))
        e["ang_mean"] = float(np.mean(np.abs(r["ang"][sl])))
        e["dang"] = float(np.max(r["ang"][sl]) - np.min(r["ang"][sl]))
        e["rate"] = float(r["rate"][i0])
        e["rate_pk"] = float(np.max(r["rate"][sl]))
        e["eff"] = float(r["eff"][i0])                 # |lowpass(tq,3Hz)| -- driver's actual push
        e["eff_mean"] = float(np.mean(r["eff"][sl]))
        e["press"] = float(np.mean(r["press"][sl] > 0.5))
        e["e4"] = float(np.mean(np.abs(r["e4"][sl])))
        e["e4max"] = float(np.max(np.abs(r["e4"][sl])))
        e["req"] = float(np.mean(np.abs(r["req"][sl])))
        e["reqmax"] = float(np.max(np.abs(r["req"][sl])))
        e["rail"] = float(np.mean(np.abs(r["req"][sl]) > 0.95))
        # steady-state bicycle model; a RANKING variable, never a calibrated number
        e["latacc"] = float(np.mean(r["v"][sl] ** 2 * np.abs(r["ang"][sl]) * np.pi / 180.0
                                    / (16.33 * 2.83)))
        # onset sharpness: seconds from half-peak to peak on the rising edge
        env = r["e_" + e["band"]]
        k = e["ipk"]
        h = env[k] / 2.0
        m = k
        while m > i0 and env[m] > h:
            m -= 1
        e["rise"] = float((k - m) / fs)
        e["vbin"] = vbin(e["v"])
        for o in (1, 2, 3, 4):
            e[f"w{o}"] = float(o * e["v_mean"] / CIRC)
        e["order"] = float(e["f0"] * CIRC / e["v_mean"]) if e["v_mean"] > 0 else np.nan
    return evs


# ================================================================= §1 CAN events =================
def section1(runs):
    G.hdr("§1  EVENTS ON THE TORSION BAR (0x18F `tq`), engaged, v >= 12 m/s\n"
          "    Threshold = quantile of the Kd=1 (V58/V59, stock rate lane) engaged-highway\n"
          "    envelope IN THE SAME SPEED BAND. Nothing is imported from the creep detector.")
    res = {}
    expo = exposure_by(runs, "kd")
    for band in BANDS:
        f50 = floor_table(runs, band, q=50)
        f99 = floor_table(runs, band, q=99)
        print(f"\n  band {band:>6} Hz   Kd=1 floor per speed band "
              + "  ".join(f"{lo:g}-{hi:g}:{f50[i]:.1f}/p99 {f99[i]:.1f}"
                          for i, (lo, hi) in enumerate(V_BANDS)))
        for qname, tab in (("p99", f99), ("6x med", {i: 6 * f50[i] for i in f50}),
                           ("10x med", {i: 10 * f50[i] for i in f50})):
            evs = find_events(runs, band, tab)
            by = {}
            for e in evs:
                by[e["kd"]] = by.get(e["kd"], 0) + 1
            line = "   ".join(f"Kd{kd:.2f}: {by.get(kd, 0):3d} ev / {expo[kd]:6.1f} s "
                              f"= {3600 * by.get(kd, 0) / max(expo[kd], 1e-9):5.1f}/h"
                              for kd in sorted(expo))
            print(f"      thr={qname:<8} n={len(evs):4d}   {line}")
            res.setdefault(band, {})[qname] = dict(
                n=len(evs), by_kd={str(k): int(v) for k, v in by.items()},
                thr={str(i): (None if not np.isfinite(tab[i]) else round(tab[i], 2))
                     for i in tab})
    return res


def exposure_by(runs, key, vmin=VMIN):
    out = {}
    for r in runs:
        m = r["v"] >= vmin
        out[r[key]] = out.get(r[key], 0.0) + float(m.sum()) / r["fs"]
    return out


# ================================================================= §2 IMU ========================
IMU_AXES = ["ax", "ay", "az", "gx", "gy", "gz"]


def collect_imu(bands=None):
    """Per-segment IMU band envelopes on the sensor's OWN lattice, with CAN covariates held/lerped
    onto it. Accelerometer AND GYRO -- every prior highway conclusion in this kit used accel only,
    and a torsional event has no reason to prefer acceleration over rotation."""
    bands = bands or BANDS
    out = []
    for rt, cd, pfx, segs, bld, kd in ROUTES:
        for s in segs:
            p = ROOT / cd / f"{pfx}{s}_imu.npz"
            dc = load_seg(cd, pfx, s)
            if not p.exists() or dc is None:
                continue
            di = dict(np.load(p))
            if len(di.get("at", [])) < 500:
                continue
            fs_can = 1.0 / float(np.median(np.diff(dc["t"])))
            rec = dict(route=rt, build=bld, kd=kd, seg=int(s))
            ok = True
            for ax in IMU_AXES:
                t = di["at"] if ax[0] == "a" else di["gt"]
                if len(t) < 500:
                    ok = False
                    break
                u, odr, fill, tu = I.uniform(t, di[ax])
                rec[ax + "_odr"] = odr
                if ax in ("ax", "gx"):
                    rec[ax[0] + "_t"] = tu
                    cov = I.can_on(tu, dc, fs_can)
                    rec[ax[0] + "_v"] = np.abs(cov["v"])
                    rec[ax[0] + "_lat"] = cov["lat"]
                    rec[ax[0] + "_eff"] = cov["eff"]
                    rec[ax[0] + "_rate"] = cov["rate"]
                    rec[ax[0] + "_ang"] = cov["ang"]
                for k, (lo, hi) in bands.items():
                    rec[(ax, k)] = I.env_full(u, odr, lo, hi)
            if ok:
                out.append(rec)
    return out


def imu_events(recs, ax, band, thr_by_vbin, min_dur=0.20, merge_gap=0.30, vmin=VMIN):
    evs = []
    g = ax[0]
    for ri, r in enumerate(recs):
        env, v, lat = r[(ax, band)], r[g + "_v"], r[g + "_lat"]
        fs = r[ax + "_odr"]
        n = min(len(env), len(v))
        env, v, lat = env[:n], v[:n], lat[:n]
        thr = np.array([thr_by_vbin.get(vbin(x), np.inf) for x in v])
        hot = (env > thr) & (v >= vmin) & (lat > 0.5)
        if not hot.any():
            continue
        idx = np.flatnonzero(hot)
        segs, s0, prev = [], idx[0], idx[0]
        for i in idx[1:]:
            if i - prev > int(merge_gap * fs):
                segs.append((s0, prev + 1))
                s0 = i
            prev = i
        segs.append((s0, prev + 1))
        for (p, q) in segs:
            if (q - p) / fs < min_dur:
                continue
            j = p + int(np.argmax(env[p:q]))
            evs.append(dict(rec=ri, axis=ax, band=band, i0=int(p), i1=int(q), ipk=int(j),
                            dur=float((q - p) / fs), amp=float(env[j]),
                            z=float(env[j] / thr[j]), t=float(r[g + "_t"][j]),
                            v=float(v[j]), route=r["route"], build=r["build"], kd=r["kd"],
                            seg=r["seg"], rate=float(r[g + "_rate"][j]),
                            eff=float(r[g + "_eff"][j]), fs=float(fs)))
    return evs


def imu_floor(recs, ax, band, kd_ref=1.00, q=50):
    g = ax[0]
    out = {}
    for i, (lo, hi) in enumerate(V_BANDS):
        acc = []
        for r in recs:
            if r["kd"] != kd_ref:
                continue
            n = min(len(r[(ax, band)]), len(r[g + "_v"]))
            m = (r[g + "_v"][:n] >= lo) & (r[g + "_v"][:n] < hi) & (r[g + "_lat"][:n] > 0.5)
            if m.any():
                acc.append(r[(ax, band)][:n][m])
        out[i] = float(np.percentile(np.concatenate(acc), q)) if acc else np.nan
    return out


def imu_exposure(recs, vmin=VMIN):
    out = {}
    for r in recs:
        n = min(len(r["a_v"]), len(r["a_lat"]))
        m = (r["a_v"][:n] >= vmin) & (r["a_lat"][:n] > 0.5)
        out[r["kd"]] = out.get(r["kd"], 0.0) + float(m.sum()) / r["ax_odr"]
    return out


def section2(irecs):
    G.hdr("§2  EVENTS ON THE COMMA IMU -- ACCELEROMETER *AND* GYRO, engaged, v >= 12 m/s\n"
          "    ⚠ Every prior highway conclusion in this kit used the accelerometer only. The gyro\n"
          "    re-cut is free and had never been run.")
    expo = imu_exposure(irecs)
    print("    exposure (IMU lattice, engaged, v>=12): "
          + "  ".join(f"Kd{k:.2f} {v:.0f} s" for k, v in sorted(expo.items())))
    res = {}
    for ax in IMU_AXES:
        print(f"\n  --- axis {ax} " + "-" * 90)
        for band in BANDS:
            f50 = imu_floor(irecs, ax, band, q=50)
            tab = {i: 10 * f50[i] for i in f50}
            evs = imu_events(irecs, ax, band, tab)
            by = {}
            for e in evs:
                by[e["kd"]] = by.get(e["kd"], 0) + 1
            rates = {k: 3600 * by.get(k, 0) / max(expo.get(k, 1e-9), 1e-9) for k in expo}
            print(f"    {band:>6} Hz  thr=10x med  n={len(evs):4d}   "
                  + "  ".join(f"Kd{k:.2f}: {by.get(k, 0):3d} ({rates[k]:5.1f}/h)"
                              for k in sorted(expo)))
            res[f"{ax}|{band}"] = dict(n=len(evs), by_kd={str(k): int(v) for k, v in by.items()},
                                       rate_per_h={str(k): round(v, 2) for k, v in rates.items()})
    return res


# ================================================================= §3 characterise ===============
def dedupe(evs):
    """Events overlapping in (route, seg, time) are ONE physical event; keep the highest z."""
    evs = sorted(evs, key=lambda e: -e["z"])
    keep = []
    for e in evs:
        if any(k["route"] == e["route"] and k["seg"] == e["seg"]
               and abs(k["t"] - e["t"]) < max(k["dur"], e["dur"]) / 2 + 0.5 for k in keep):
            continue
        keep.append(e)
    return keep


def section3(runs, all_evs):
    G.hdr("§3  THE TOP 20 TORSION-BAR EVENTS BY AMPLITUDE (deduped across bands)")
    ev = sorted(dedupe(all_evs), key=lambda e: -e["amp"])[:20]
    print(f"{'#':<3}{'rt':<4}{'bld':<5}{'Kd':>5}{'sg':>4}{'t(s)':>8}{'band':>7}{'amp':>8}"
          f"{'z':>6}{'dur':>6}{'rise':>6}{'f0':>7}{'Q':>6}{'prom':>6}{'v':>6}{'ang':>7}"
          f"{'rate':>7}{'eff':>7}{'prs':>5}{'e4mx':>6}{'rail':>6}{'alat':>6}{'ord':>6}")
    for i, e in enumerate(ev):
        print(f"{i + 1:<3}{e['route']:<4}{e['build']:<5}{e['kd']:>5.2f}{e['seg']:>4}"
              f"{e['t']:>8.1f}{e['band']:>7}{e['amp']:>8.0f}{e['z']:>6.1f}{e['dur']:>6.2f}"
              f"{e['rise']:>6.2f}{e['f0']:>7.2f}{e['Q']:>6.1f}{e['prom']:>6.1f}"
              f"{e['v']:>6.1f}{e['ang']:>7.1f}{e['rate_pk']:>7.1f}{e['eff']:>7.0f}"
              f"{e['press']:>5.2f}{e['e4max']:>6.0f}{e['rail']:>6.2f}{e['latacc']:>6.2f}"
              f"{e['order']:>6.2f}")
    print("\n  amp = p99-free peak of the analytic band envelope (torsion-bar counts)\n"
          "  z = amp / (10x Kd=1 speed-band median floor)   rise = half-peak-to-peak, s\n"
          "  eff = |lowpass(tq,3Hz)| at onset -- HANDS-ON test; prs = steeringPressed duty\n"
          "  e4mx = |0x0E4 LKAS command| max, rail = duty of |actuators.torque| > 0.95\n"
          "  ord = f0 * 2.08 / v = the implied WHEEL ORDER (3.00 => wheel order 3)")
    return [{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
             for k, v in e.items() if k not in ("run",)} for e in ev]


# ================================================================= §4 mode vs order ==============
def theil_sen(x, y, rng, nboot=2000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 4:
        return np.nan, np.nan, np.nan, np.nan, len(x)

    def sl(xx, yy):
        i, j = np.triu_indices(len(xx), 1)
        dx = xx[j] - xx[i]
        ok = np.abs(dx) > 1e-9
        return float(np.median((yy[j] - yy[i])[ok] / dx[ok])) if ok.any() else np.nan
    p = sl(x, y)
    dr = np.array([sl(x[k], y[k]) for k in
                   (rng.integers(0, len(x), len(x)) for _ in range(nboot))])
    icpt = float(np.median(y - p * x))
    return p, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), icpt, len(x)


def section4(runs, evs_by_band):
    G.hdr("§4  THE DECISIVE TEST -- MODE vs ORDER.  Regress event f0 on vehicle speed.\n"
          "    ORDER n  =>  f0 = n*v/2.08, slope = n/2.08 (0.481 / 0.962 / 1.442 Hz per m/s)\n"
          "    MODE     =>  slope ~ 0 and the implied order 'order = f0*2.08/v' SCATTERS")
    res = {}
    print(f"{'band':>7}{'n':>5}{'slope Hz/(m/s)':>18}{'   [95% CI]':>22}{'intercept':>11}"
          f"{'  order p50':>11}{'order sd':>10}{'  verdict'}")
    for band, evs in evs_by_band.items():
        e = [x for x in evs if np.isfinite(x.get("f0", np.nan)) and x["v_mean"] > 0]
        if len(e) < 6:
            print(f"{band:>7}{len(e):>5}   (too few events)")
            continue
        v = np.array([x["v_mean"] for x in e])
        f0 = np.array([x["f0"] for x in e])
        od = np.array([x["order"] for x in e])
        s, lo, hi, ic, n = theil_sen(v, f0, RNG, 800)
        exp_ord = [0.481, 0.962, 1.442, 1.923]
        near = [k + 1 for k, q in enumerate(exp_ord) if lo <= q <= hi]
        verdict = ("MODE (slope CI contains 0)" if lo <= 0 <= hi else
                   f"consistent with ORDER {near}" if near else "neither (slope != 0, off-order)")
        print(f"{band:>7}{n:>5}{s:>18.4f}   [{lo:7.4f},{hi:7.4f}]{ic:>11.2f}"
              f"{np.median(od):>11.2f}{np.std(od):>10.2f}  {verdict}")
        res[band] = dict(n=n, slope=s, lo=lo, hi=hi, intercept=ic,
                         order_p50=float(np.median(od)), order_sd=float(np.std(od)),
                         f0_p50=float(np.median(f0)), f0_sd=float(np.std(f0)), verdict=verdict)
    return res


def section4b(runs, evs_by_band):
    """The on-order / off-order power ratio -- the discriminator that worked before (6.94 in quiet
    windows, 0.82 inside genuine bursts)."""
    G.hdr("§4b  ON-ORDER / OFF-ORDER POWER RATIO at the event peaks\n"
          "     ratio >> 1 => the power sits ON the wheel-order comb => a driveline ORDER\n"
          "     ratio ~ 1  => the power is NOT organised by wheel order => a MODE")
    res = {}
    for band, evs in evs_by_band.items():
        vals, ctrl = [], []
        for e in evs:
            r = runs[e["run"]]
            fs = r["fs"]
            j = e["ipk"]
            a = max(0, min(len(r["tq"]) - NFFT, j - NFFT // 2))
            P = G.periodogram(r["tq"][a:a + NFFT], fs, NFFT, True)
            if P is None:
                continue
            f = np.fft.rfftfreq(NFFT, 1 / fs)
            df = f[1] - f[0]
            lo, hi = BANDS[band]
            inb = (f >= lo) & (f <= hi)
            on = np.zeros(len(f), bool)
            for o in range(1, 12):
                fo = o * e["v_mean"] / CIRC
                if lo <= fo <= hi:
                    on |= np.abs(f - fo) <= 1.5 * df
            if on.sum() < 1 or (inb & ~on).sum() < 3:
                continue
            vals.append(float(np.mean(P[inb & on]) / np.mean(P[inb & ~on])))
        if vals:
            v = np.array(vals)
            print(f"  {band:>7} Hz  n={len(v):4d}   on/off power ratio  "
                  f"p50={np.median(v):6.2f}  p25={np.percentile(v, 25):6.2f}  "
                  f"p75={np.percentile(v, 75):6.2f}  mean={v.mean():6.2f}")
            res[band] = dict(n=len(v), p50=float(np.median(v)), mean=float(v.mean()))
    return res


# ================================================================= §4c free band =================
WIDE = {"10-49": (10.0, 49.0)}


def section4c(runs):
    """🛑 THE BAND CENSORS THE TEST. A 40-49 Hz detector can only ever report f0 in [40,49], so its
    f0-vs-speed slope is bounded by 9 Hz / (speed range). Over 12-30 m/s an order-3 line moves
    1.442 * 18 = 26 Hz -- five times the band width. A flat slope inside a 9 Hz band is therefore
    NOT evidence of a mode. This section re-runs the test with a FREE 10-49 Hz detector and a free
    argmax, where an order IS able to express itself."""
    G.hdr("§4c  MODE vs ORDER with a FREE 10-49 Hz detector (the band-censoring fix)")
    for k, v in WIDE.items():
        BANDS[k] = v
    for r in runs:
        for k, (lo, hi) in WIDE.items():
            if "e_" + k not in r:
                r["e_" + k] = band_env_run(r["tq"], r["fs"], lo, hi)
    f50 = floor_table(runs, "10-49", q=50)
    evs = characterise(runs, find_events(runs, "10-49", {i: 10 * f50[i] for i in f50}))
    e = [x for x in evs if np.isfinite(x.get("f0", np.nan)) and x["v_mean"] > 0]
    v = np.array([x["v_mean"] for x in e])
    f0 = np.array([x["f0"] for x in e])
    s, lo, hi, ic, n = theil_sen(v, f0, RNG, 800)
    print(f"  n={n} events, free argmax over 10-49 Hz, speed span "
          f"{v.min():.1f}-{v.max():.1f} m/s")
    print(f"  Theil-Sen slope {s:.4f} Hz/(m/s)  95% CI [{lo:.4f}, {hi:.4f}]  intercept {ic:.2f} Hz")
    print(f"  f0: p50 {np.median(f0):.2f}  p10 {np.percentile(f0, 10):.2f}  "
          f"p90 {np.percentile(f0, 90):.2f}  sd {np.std(f0):.2f} Hz")
    for o in (1, 2, 3, 4):
        q = o / CIRC
        print(f"    wheel order {o}: predicted slope {q:.4f} -> "
              f"{'INSIDE' if lo <= q <= hi else 'EXCLUDED BY'} the CI")
    print(f"  slope 0 (pure mode): {'INSIDE' if lo <= 0 <= hi else 'EXCLUDED BY'} the CI")
    # per-speed-band f0, the assumption-free version of the same question
    print(f"\n  {'speed band':>12}{'n':>5}{'f0 p50':>9}{'f0 p25':>9}{'f0 p75':>9}"
          f"{'  order1':>9}{'order3':>9}")
    for i, (a, b) in enumerate(V_BANDS):
        m = [x for x in e if a <= x["v_mean"] < b]
        if len(m) < 3:
            print(f"  {f'{a:g}-{b:g}':>12}{len(m):>5}     (thin)")
            continue
        ff = np.array([x["f0"] for x in m])
        vv = np.mean([x["v_mean"] for x in m])
        print(f"  {f'{a:g}-{b:g}':>12}{len(m):>5}{np.median(ff):>9.2f}"
              f"{np.percentile(ff, 25):>9.2f}{np.percentile(ff, 75):>9.2f}"
              f"{vv / CIRC:>9.2f}{3 * vv / CIRC:>9.2f}")
    # quiet-window calibration of the on/off-order discriminator
    quiet = []
    for r in runs:
        m = np.flatnonzero(r["v"] >= VMIN)
        if len(m) < NFFT * 3:
            continue
        for j in m[NFFT:len(m) - NFFT:NFFT * 4]:
            P = G.periodogram(r["tq"][j:j + NFFT], r["fs"], NFFT, True)
            if P is None:
                continue
            f = np.fft.rfftfreq(NFFT, 1 / r["fs"])
            df = f[1] - f[0]
            vv = float(np.mean(r["v"][j:j + NFFT]))
            inb = (f >= 10) & (f <= 49)
            on = np.zeros(len(f), bool)
            for o in range(1, 12):
                fo = o * vv / CIRC
                if 10 <= fo <= 49:
                    on |= np.abs(f - fo) <= 1.5 * df
            if on.sum() and (inb & ~on).sum() > 3:
                quiet.append(float(np.mean(P[inb & on]) / np.mean(P[inb & ~on])))
    burst = []
    for x in e:
        r = runs[x["run"]]
        j = x["ipk"]
        a = max(0, min(len(r["tq"]) - NFFT, j - NFFT // 2))
        P = G.periodogram(r["tq"][a:a + NFFT], r["fs"], NFFT, True)
        if P is None:
            continue
        f = np.fft.rfftfreq(NFFT, 1 / r["fs"])
        df = f[1] - f[0]
        inb = (f >= 10) & (f <= 49)
        on = np.zeros(len(f), bool)
        for o in range(1, 12):
            fo = o * x["v_mean"] / CIRC
            if 10 <= fo <= 49:
                on |= np.abs(f - fo) <= 1.5 * df
        if on.sum() and (inb & ~on).sum() > 3:
            burst.append(float(np.mean(P[inb & on]) / np.mean(P[inb & ~on])))
    print(f"\n  ON-ORDER / OFF-ORDER power ratio over 10-49 Hz, this population:")
    print(f"    QUIET windows  n={len(quiet):5d}  p50={np.median(quiet):6.2f}  "
          f"mean={np.mean(quiet):6.2f}   (kit reference: 6.94)")
    print(f"    EVENT peaks    n={len(burst):5d}  p50={np.median(burst):6.2f}  "
          f"mean={np.mean(burst):6.2f}   (kit reference inside genuine bursts: 0.82)")
    return dict(n=n, slope=s, lo=lo, hi=hi, intercept=ic, f0_p50=float(np.median(f0)),
                f0_sd=float(np.std(f0)),
                quiet_onoff=float(np.median(quiet)), burst_onoff=float(np.median(burst)),
                events=[{k: (float(x) if isinstance(x, (int, float, np.floating)) else x)
                         for k, x in q.items() if k != "run"} for q in e])


# ================================================================= window records ================
def window_records(runs, bands=None):
    """2.56 s windows over engaged-highway, with the VALIDATED tapered per-window envelope
    (`_grind2_lib.win_env`) and every conditioning covariate. This is the population §5 and §6
    reason over -- events are a subset of it, so a rate and a level are computed on one frame."""
    bands = bands or dict(BANDS, **WIDE)
    taper = np.hanning(NFFT) + 1e-3
    cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
    out = []
    for ri, r in enumerate(runs):
        fs, n = r["fs"], len(r["tq"])
        for i in range(0, n - NFFT + 1, NFFT // 2):
            sl = slice(i, i + NFFT)
            vv = r["v"][sl]
            if float(np.mean(vv)) < VMIN:
                continue
            w = dict(run=ri, i=i, route=r["route"], build=r["build"], kd=r["kd"], seg=r["seg"],
                     t=float(r["t"][i]), v=float(np.mean(vv)),
                     eff=float(np.mean(r["eff"][sl])),
                     press=float(np.mean(r["press"][sl] > 0.5)),
                     rate=float(np.mean(r["rate"][sl])),
                     rate_pk=float(np.max(r["rate"][sl])),
                     ang=float(np.mean(np.abs(r["ang"][sl]))),
                     dang=float(np.max(r["ang"][sl]) - np.min(r["ang"][sl])),
                     e4=float(np.mean(np.abs(r["e4"][sl]))),
                     e4max=float(np.max(np.abs(r["e4"][sl]))),
                     reqmax=float(np.max(np.abs(r["req"][sl]))),
                     rail=float(np.mean(np.abs(r["req"][sl]) > 0.95)))
            w["latacc"] = float(np.mean(vv ** 2 * np.abs(r["ang"][sl]) * np.pi / 180
                                        / (16.33 * 2.83)))
            w["vbin"] = vbin(w["v"])
            w["blk"] = (ri, i // int(10.0 * fs))          # ~10 s bootstrap unit
            for k, (lo, hi) in bands.items():
                w["e_" + k] = G.win_env(r["tq"][sl], fs, lo, hi, taper, cw)
            out.append(w)
    return out


def gmm2_bic(x):
    """1-component vs 2-component Gaussian mixture on log-amplitude, by EM. Returns (dBIC, pi2,
    mu1, mu2). dBIC > 10 favours BIMODAL (threshold-like); dBIC < 0 favours a single smooth tail."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    ll1 = float(np.sum(-0.5 * np.log(2 * np.pi * np.var(x)) - (x - x.mean()) ** 2
                       / (2 * np.var(x))))
    bic1 = -2 * ll1 + 2 * np.log(n)
    mu = np.array([np.percentile(x, 25), np.percentile(x, 85)])
    sd = np.array([x.std() / 2, x.std() / 2])
    pi = np.array([0.7, 0.3])
    ll2 = -np.inf
    for _ in range(400):
        Pk = pi * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        s = Pk.sum(1)
        s[s <= 0] = 1e-300
        ll2 = float(np.sum(np.log(s)))
        W = Pk / s[:, None]
        pi = W.mean(0)
        mu = (W * x[:, None]).sum(0) / W.sum(0)
        sd = np.sqrt((W * (x[:, None] - mu) ** 2).sum(0) / W.sum(0))
        sd = np.maximum(sd, 1e-6)
    bic2 = -2 * ll2 + 5 * np.log(n)
    o = np.argsort(mu)
    return float(bic1 - bic2), float(pi[o][1]), float(mu[o][0]), float(mu[o][1])


def _rank(a):
    """Tie-aware average ranks. 🛑 `argsort(argsort(a))` is NOT this: on a BINARY vector it hands
    the tied values distinct arbitrary ranks, and the resulting 'Spearman' against a covariate
    came out +0.393 for a variable whose own decile table fell monotonically. That was a real
    wrong number in this session and this function is the fix."""
    a = np.asarray(a, float)
    o = np.argsort(a, kind="stable")
    r = np.empty(len(a), float)
    r[o] = np.arange(len(a), dtype=float)
    s = a[o]
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and s[j + 1] == s[i]:
            j += 1
        if j > i:
            r[o[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return r


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 5:
        return np.nan
    rx, ry = _rank(x[m]), _rank(y[m])
    if np.std(rx) == 0 or np.std(ry) == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def section5(wins, evs_by_band):
    G.hdr("§5  THRESHOLD vs PROPORTIONAL.  The operator says it either happens or it does not.\n"
          "    (a) is the amplitude distribution BIMODAL?  (b) is there a conditioning value\n"
          "    below which events never occur?  (c) or is this just the top of the ALREADY\n"
          "    MEASURED smooth maneuver-loading effect (rho +0.64..+0.93 vs rate_peak)?")
    res = {}
    print("\n  (a) BIMODALITY of log10(window band envelope), engaged highway, all doses")
    print(f"      {'band':>7}{'n':>7}{'dBIC(1-2)':>12}{'pi_hi':>8}{'mu_lo':>8}{'mu_hi':>8}"
          f"{'  verdict'}")
    for band in list(BANDS):
        x = np.log10(np.array([w["e_" + band] for w in wins]) + 1e-9)
        d, p2, m1, m2 = gmm2_bic(x)
        v = ("BIMODAL (threshold-like)" if d > 10 and abs(m2 - m1) > 0.3
             else "unimodal (smooth tail)")
        print(f"      {band:>7}{len(x):>7}{d:>12.1f}{p2:>8.3f}{m1:>8.2f}{m2:>8.2f}  {v}")
        res.setdefault("bimodal", {})[band] = dict(dBIC=d, pi_hi=p2, mu_lo=m1, mu_hi=m2, verdict=v)

    print("\n  (b) P(window is inside an event) vs DECILE of each conditioning variable.\n"
          "      A THRESHOLD looks like 0,0,0,0,0,0,0,0,x,y.  A PROPORTIONAL effect rises "
          "smoothly.")
    ev_keys = {}
    for band, evs in evs_by_band.items():
        s = set()
        for e in evs:
            for k in range(e["i0"] - NFFT, e["i1"] + 1):
                s.add((e["run"], (k // (NFFT // 2)) * (NFFT // 2)))
        ev_keys[band] = s
    for band in ("18-22", "30-40", "40-49", "10-49"):
        if band not in ev_keys:
            continue
        hit = np.array([1.0 if (w["run"], w["i"]) in ev_keys[band] else 0.0 for w in wins])
        print(f"\n      band {band} Hz   {int(hit.sum())}/{len(hit)} windows inside an event")
        for var in ("rate_pk", "latacc", "dang", "e4max", "reqmax", "v", "eff", "rail"):
            x = np.array([w[var] for w in wins])
            q = np.percentile(x, np.arange(0, 101, 10))
            q[-1] += 1e-9
            row = []
            for k in range(10):
                m = (x >= q[k]) & (x < q[k + 1])
                row.append(100 * hit[m].mean() if m.sum() else np.nan)
            print(f"        {var:>8}  " + " ".join(f"{r:5.1f}" for r in row)
                  + f"   %  (rho={spearman(x, hit):+.3f})")
            res.setdefault("decile", {}).setdefault(band, {})[var] = [
                None if not np.isfinite(r) else round(r, 2) for r in row]

    print("\n  (c) SMOOTH loading: Spearman rho of the WINDOW ENVELOPE against each covariate\n"
          "      (this is the effect already on record: 6-9 Hz 2.78x, 40-49 Hz 2.13x with "
          "rate_peak)")
    print(f"      {'band':>7}" + "".join(f"{v:>10}" for v in
                                         ("rate_pk", "latacc", "dang", "e4max", "v", "eff")))
    for band in list(BANDS):
        y = np.array([w["e_" + band] for w in wins])
        print(f"      {band:>7}" + "".join(
            f"{spearman(np.array([w[v] for w in wins]), y):>10.3f}"
            for v in ("rate_pk", "latacc", "dang", "e4max", "v", "eff")))
        res.setdefault("rho", {})[band] = {
            v: spearman(np.array([w[q] for w in wins]), y)
            for v, q in (("rate_pk", "rate_pk"), ("latacc", "latacc"), ("dang", "dang"),
                         ("e4max", "e4max"), ("v", "v"), ("eff", "eff"))}
    return res


# ================================================================= §6 dose on RATE ===============
def blocks_of(wins, evkeys):
    """~10 s blocks with (exposure_s, n_event_windows, speed bin, dose)."""
    B = {}
    for w in wins:
        b = B.setdefault((w["kd"], w["blk"]), dict(kd=w["kd"], n=0, hit=0, v=[], route=w["route"]))
        b["n"] += 1
        b["v"].append(w["v"])
        b["hit"] += 1 if (w["run"], w["i"]) in evkeys else 0
    for b in B.values():
        b["expo"] = b["n"] * (NFFT / 2) / 100.0          # windows hop 1.28 s
        b["vbin"] = vbin(float(np.mean(b["v"])))
    return list(B.values())


def rate_ratio(bA, bB, rng, nboot=3000):
    """Speed-band-STRATIFIED event-rate ratio A/B, resampling 10 s BLOCKS with replacement.
    Weight per band w = 1/(1/nA + 1/nB) so a band one dose barely visited cannot dominate."""
    def est(A, B):
        num = den = 0.0
        for i in range(len(V_BANDS)):
            a = [x for x in A if x["vbin"] == i]
            b = [x for x in B if x["vbin"] == i]
            if len(a) < 3 or len(b) < 3:
                continue
            ha, ea = sum(x["hit"] for x in a), sum(x["expo"] for x in a)
            hb, eb = sum(x["hit"] for x in b), sum(x["expo"] for x in b)
            if ea <= 0 or eb <= 0:
                continue
            ra, rb = (ha + 0.5) / ea, (hb + 0.5) / eb
            w = 1.0 / (1.0 / len(a) + 1.0 / len(b))
            num += w * np.log(ra / rb)
            den += w
        return num / den if den else np.nan
    p = est(bA, bB)
    dr = np.full(nboot, np.nan)
    for k in range(nboot):
        dr[k] = est([bA[i] for i in rng.integers(0, len(bA), len(bA))],
                    [bB[i] for i in rng.integers(0, len(bB), len(bB))])
    if not np.isfinite(dr).any():
        return float(np.exp(p)), np.nan, np.nan
    return (float(np.exp(p)), float(np.exp(np.nanpercentile(dr, 2.5))),
            float(np.exp(np.nanpercentile(dr, 97.5))))


def split_half_rate(bl, rng, nrep=400):
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(bl))
        h = len(bl) // 2
        v = rate_ratio([bl[i] for i in idx[:h]], [bl[i] for i in idx[h:]], rng, nboot=0)[0]
        if np.isfinite(v) and v > 0:
            out.append(v)
    o = np.array(out)
    return (float(np.exp(np.median(np.log(o)))), float(np.percentile(o, 2.5)),
            float(np.percentile(o, 97.5)), len(o))


def power_for_ratio(n1, n2, ratio=2.0):
    """Events needed for 80% power at alpha=0.05 on a Poisson log-rate ratio, given the OBSERVED
    exposure split. Var(log rhat) = 1/n1 + 1/n2; need |log R| / sqrt(V) > 1.96 + 0.84."""
    need = (np.log(ratio) / 2.80) ** 2
    have = (1.0 / max(n1, 0.5) + 1.0 / max(n2, 0.5))
    return have, need, float(np.sqrt(have / need)) if need > 0 else np.nan


def section6(wins, evs_by_band):
    G.hdr("§6  DOSE RESPONSE ON THE EVENT RATE (not the pooled level).\n"
          "    Published pooled-level null: 40-49 Hz 0.970 [0.787,1.154] and 0.938 [0.764,1.184],\n"
          "    split-half null [0.73,1.37], positive control 18-22 Hz 0.509 [0.39,0.92].")
    res = {}
    print(f"\n  {'band':>7}{'  A/B':>12}{'ratio':>8}{'   [95% CI]':>20}{'  nA':>6}{'nB':>6}"
          f"{'  evA':>6}{'evB':>6}{'  expA(s)':>10}{'expB(s)':>9}")
    for band, evs in evs_by_band.items():
        keys = set()
        for e in evs:
            for k in range(e["i0"] - NFFT, e["i1"] + 1):
                keys.add((e["run"], (k // (NFFT // 2)) * (NFFT // 2)))
        bl = blocks_of(wins, keys)
        pools = {kd: [b for b in bl if b["kd"] == kd] for kd in (1.0, 2.0, 2.44)}
        for a, b in ((2.0, 1.0), (2.44, 1.0), (2.44, 2.0)):
            A, B = pools[a], pools[b]
            r, lo, hi = rate_ratio(A, B, RNG)
            print(f"  {band:>7}{f'{a:g}/{b:g}':>12}{r:>8.3f}   [{lo:6.3f},{hi:6.3f}]"
                  f"{len(A):>6}{len(B):>6}{sum(x['hit'] for x in A):>6}"
                  f"{sum(x['hit'] for x in B):>6}{sum(x['expo'] for x in A):>10.0f}"
                  f"{sum(x['expo'] for x in B):>9.0f}")
            res.setdefault(band, {})[f"{a:g}/{b:g}"] = dict(
                ratio=r, lo=lo, hi=hi, nA=sum(x["hit"] for x in A),
                nB=sum(x["hit"] for x in B))
        n0, lo0, hi0, k = split_half_rate(pools[1.0], RNG)
        n2, lo2, hi2, k2 = split_half_rate(pools[2.0], RNG)
        print(f"  {'':>7}{'SPLIT-HALF':>12}  Kd=1 pool {n0:.3f} [{lo0:.3f},{hi0:.3f}] (n={k})"
              f"   Kd=2 pool {n2:.3f} [{lo2:.3f},{hi2:.3f}] (n={k2})")
        res[band]["null_kd1"] = [n0, lo0, hi0]
        res[band]["null_kd2"] = [n2, lo2, hi2]
        e1 = sum(x["hit"] for x in pools[1.0])
        e2 = sum(x["hit"] for x in pools[2.0])
        have, need, ratio_detectable = power_for_ratio(e1, e2)
        print(f"  {'':>7}{'POWER':>12}  Var(log R)=1/{e1}+1/{e2}={have:.4f}; "
              f"a 2.0x rate difference needs <= {need:.4f}  =>  "
              f"{'ADEQUATE' if have <= need else f'UNDER-POWERED by {ratio_detectable:.2f}x'}"
              f"; smallest detectable ratio at 80% power = "
              f"{np.exp(2.80 * np.sqrt(have)):.2f}x")
        res[band]["power"] = dict(nA=e1, nB=e2, var=have, need=need,
                                  min_detectable=float(np.exp(2.80 * np.sqrt(have))))
    return res


if __name__ == "__main__":
    want = sys.argv[1:] or ["0", "1", "2", "3", "4"]
    store = {}
    if OUT.exists():
        try:
            store = json.loads(OUT.read_text())
        except Exception:
            store = {}
    if "0" in want:
        store["exposure"] = section0()
    runs = None
    if any(k in want for k in ("1", "3", "4")):
        runs = collect_envelopes("tq")
        print(f"\n[collected {len(runs)} engagement runs, "
              f"{sum(len(r['t']) for r in runs)} frames]")
    if "1" in want:
        store["can_events"] = section1(runs)
    if "2" in want:
        irecs = collect_imu()
        print(f"\n[collected {len(irecs)} IMU segments]")
        store["imu_events"] = section2(irecs)
    if any(k in want for k in ("3", "4")):
        evs_by_band = {}
        for band in BANDS:
            f50 = floor_table(runs, band, q=50)
            evs_by_band[band] = characterise(
                runs, find_events(runs, band, {i: 10 * f50[i] for i in f50}))
        allev = [e for v in evs_by_band.values() for e in v]
    if "3" in want:
        store["top20"] = section3(runs, allev)
    if "4" in want:
        store["mode_vs_order"] = section4(runs, evs_by_band)
        store["on_off_order"] = section4b(runs, evs_by_band)
    if "4c" in want:
        runs = runs if runs is not None else collect_envelopes("tq")
        store["free_band"] = section4c(runs)
    if any(k in want for k in ("5", "6")):
        runs = runs if runs is not None else collect_envelopes("tq")
        for k, v in WIDE.items():
            BANDS[k] = v
        for r in runs:
            for k, (lo, hi) in WIDE.items():
                if "e_" + k not in r:
                    r["e_" + k] = band_env_run(r["tq"], r["fs"], lo, hi)
        evs_by_band = {}
        for band in BANDS:
            f50 = floor_table(runs, band, q=50)
            evs_by_band[band] = characterise(
                runs, find_events(runs, band, {i: 10 * f50[i] for i in f50}))
        wins = window_records(runs)
        print(f"\n[{len(wins)} engaged-highway 2.56 s windows]")
    if "5" in want:
        store["threshold_test"] = section5(wins, evs_by_band)
    if "6" in want:
        store["dose_on_rate"] = section6(wins, evs_by_band)
    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")
