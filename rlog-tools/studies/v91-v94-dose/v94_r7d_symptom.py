#!/usr/bin/env python3
r"""Route 7d (V94) symptom bands and Re(Z), against routes 77/78/79 — LOW-SPEED regime only.

🛑🛑 READ THIS BEFORE READING ANY NUMBER.
    The operator scores SYMPTOMS.  This file scores BANDS.  A band moving is NOT a symptom
    changing.  His words for route 7d are: **stuttering and grinding MUCH worse, enough to vibrate
    the entire car, unsafe — he stopped driving.**  That report is primary.  Nothing here overrules
    it; this file exists only to instrument it.

🛑 ROUTE 7d NEVER EXCEEDED 6.2 km/h.  It is a 141 s parking manoeuvre (park 36.5 s / drive 59.6 s /
   reverse 40.8 s), engaged 10.8 s in 3 episodes.  Consequences, stated rather than worked around:
     · every regime here is masked to **v < 6.2 km/h on EVERY route**, so the speed distributions
       are matched by construction (the standing "a moving wheel order manufactures a line" trap);
     · the kit's standard `NW_Z = 512` (5.12 s) window DOES NOT FIT — the longest engagement is
       4.6 s — so this file uses **NW = 256 (2.56 s), HOP = 128**, applied IDENTICALLY to all four
       routes.  🛑 That makes these numbers a NON-STANDARD estimator: they are NOT comparable to the
       published 77/78/79 placebo floor (6-9 Hz 1.37×, 18-22 Hz 1.31×, 26-31 Hz 1.99×, control
       32-38 Hz 1.54×), which was computed at 5.12 s on the full-speed drives.  A LOW-SPEED,
       SHORT-WINDOW placebo floor is therefore RECOMPUTED here from routes 77/78/79 and every
       route-7d ratio is quoted against THAT.
     · the SPLIT-HALF NULL runs BEFORE any cross-route ratio is printed (standing kit rule).

METHOD.  Windows are cut on a PHYSICAL, contiguous mask (engaged / manual, v < 6.2 km/h) and then
classified by their OWN median |wheel rate| — the same pattern `studies/v91-v94-dose/v92_symptom_bands.py` uses, so every
window is scoreable and the regimes partition the drive.  Band energy is normalised WITHIN each
window by that window's own 1-38 Hz total, so a window that saw more road cannot inflate a band.
Bootstrap resamples CONTIGUOUS MASK RUNS (a block bootstrap), never windows; a cell with fewer than
4 blocks is printed as NOT BOOTSTRAPPABLE rather than given a fake CI.

⚠ HANDS ARE ON.  steeringPressed duty is 29.3 % on route 7d — it is a parking manoeuvre.  The prior
routes' band work filtered to hands-off; that filter is NOT applied here (it would delete the
regime), and the press duty is reported per cell instead.

CHANNELS.  Column torque `tq` (0x18F, 100 Hz) is the kit's standard.  IMU vertical and lateral are
scored too, because the operator reports the whole CAR shaking, which need not appear in the column.

Usage:  python studies/v91-v94-dose/v94_r7d_symptom.py
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
CACHE = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(CACHE))

import decode_v90_probe as P          # noqa: E402  -- FROZEN estimator, imported read-only

RNG = np.random.default_rng(20260811)
DEG2RAD = np.pi / 180.0
NW, HOP = 256, 128                    # 2.56 s at 100 Hz.  🛑 NOT the kit's standard 512.
NBOOT = 3000
VMAX_KMH = 6.2                        # route 7d's own ceiling -> the common support
MIN_WIN = 5
MIN_BLOCK = 4

ROUTES = (("7d", "r7d", "V94"), ("77", "r77", "V90"), ("78", "r78", "V91"), ("79", "r79", "V92"))
BANDS = [("micro-ratchet 6-9", 6.0, 9.0), ("9-12", 9.0, 12.0), ("15-22", 15.0, 22.0),
         ("grind #1  18-22", 18.0, 22.0), ("grind #2  26-31", 26.0, 31.0),
         ("CONTROL   32-38", 32.0, 38.0)]
REGIMES = [("static  <1 °/s", 0.0, 1.0), ("MICRO   1-13 °/s", 1.0, 13.0),
           ("RATCHET 13-50 °/s", 13.0, 50.0), ("MACRO   >50 °/s", 50.0, 1e9)]
Z_BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
           ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0),
           ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0), ("31-38", 31.0, 38.0)]
COH_ABS, COH_REL = 0.10, 5.0          # the pre-declared trust gate from studies/impedance/v92_rez_extend.py


# ======================================================================================
def load(route, stem):
    z = np.load(CACHE / f"r{route}" / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    d = dict(t=t, tq=np.asarray(z["tq"], float),
             rate_f=np.asarray(z["rate_f"], float),
             imu_v=np.asarray(z["imu_vert"], float),
             imu_l=np.asarray(z["imu_lat"], float),
             v=np.abs(np.asarray(z["cs_v"], float)),
             lat=np.asarray(z["cc_lat"], float) > 0.5,
             press=np.asarray(z["cs_press"], float) > 0.5)
    d["fs"] = 1.0 / float(np.median(np.diff(t)))
    return d


def blocks_of(mask):
    """Contiguous-run id per True frame; -1 elsewhere.  The bootstrap unit."""
    bid = np.full(len(mask), -1, int)
    k, run = 0, False
    for i, x in enumerate(mask):
        if x:
            if not run:
                k += 1
                run = True
            bid[i] = k - 1
        else:
            run = False
    return bid, k


def windows(D, mask):
    """Windows on the physical mask, each carrying its own rate / speed / press / block id."""
    bid, _ = blocks_of(mask)
    idx = np.arange(len(D["t"]))
    W = P._wins(mask, D["t"], NW, HOP,
                (D["tq"], D["imu_v"], D["imu_l"], np.abs(D["rate_f"]), D["v"] * 3.6,
                 D["press"].astype(float), bid.astype(float), idx.astype(float)))
    return W


def band_shares(W, fs, chan, absolute=False):
    """Per-window band energy of one channel.

    `absolute=False` -> within-window share of the window's own 1-38 Hz total (spectral SHAPE).
    `absolute=True`  -> raw band power density (LEVEL).  🛑 BOTH are needed: a build that raises
    the whole 1-38 Hz band leaves every SHARE unchanged, and "the whole car vibrating" is a level
    claim, not a shape claim.
    """
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    tot_m = (f >= 1.0) & (f <= 38.0)
    hann = np.hanning(NW)
    norm = (hann ** 2).sum() * fs                 # PSD normalisation, so levels are comparable
    out = {nm: [] for nm, _, _ in BANDS}
    out["TOTAL 1-38"] = []
    meta = []
    ci = {"tq": 0, "imu_v": 1, "imu_l": 2}[chan]
    for w in W:
        y = w[ci]
        if not np.isfinite(y).all():
            continue
        y = y - y.mean()
        S = np.abs(np.fft.rfft(y * hann)) ** 2 / norm
        tot = S[tot_m].sum()
        if tot <= 0:
            continue
        for nm, lo, hi in BANDS:
            m = (f >= lo) & (f <= hi)
            out[nm].append(float(S[m].sum() / (1.0 if absolute else tot) / (hi - lo)))
        out["TOTAL 1-38"].append(float(tot))
        meta.append((float(np.median(w[3])), float(np.median(w[4])), float(np.mean(w[5])),
                     float(w[6][0]), float(np.median(w[7]))))
    return ({k: np.array(v, float) for k, v in out.items()},
            np.array(meta, float).reshape(-1, 5))


def block_boot_median(x, blk, nboot=NBOOT):
    """Median CI resampling BLOCKS, not windows."""
    ub = np.unique(blk)
    if len(x) < MIN_WIN or len(ub) < MIN_BLOCK:
        return float("nan"), float("nan"), len(ub)
    ix = {b: np.flatnonzero(blk == b) for b in ub}
    out = np.empty(nboot)
    for k in range(nboot):
        p = np.concatenate([ix[b] for b in RNG.choice(ub, len(ub), replace=True)])
        out[k] = np.median(x[p])
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(ub)


# ======================================================================================
def split_half_null(sel_cache, bandnames):
    """🛑 RUNS BEFORE ANY CROSS-ROUTE RATIO IS INTERPRETED.  WITHIN each route AND WITHIN the SAME
    regime cell, split that cell's windows in half by time and take the same band ratio.  Whatever
    this produces is noise BY CONSTRUCTION -- it is one firmware, one drive, one regime.

    🛑 It MUST be computed inside the regime cell.  A first version split each arm's windows as a
    whole; on route 7d that straddles parked and moving segments and returned a 38× 'null', which
    is a regime difference, not measurement noise.  Recorded so nobody re-derives it."""
    res = {}
    for bnm in bandnames:
        vals, per = [], {}
        for r, _s, _l in ROUTES:
            sh, meta, sel = sel_cache[r]
            if sel.sum() < 2 * MIN_WIN:
                per[r] = float("nan")
                continue
            x, tt = sh[bnm][sel], meta[sel, 4]
            order = np.argsort(tt)
            h = len(order) // 2
            a, b = np.median(x[order[:h]]), np.median(x[order[h:]])
            if a <= 0 or b <= 0:
                per[r] = float("nan")
                continue
            rr = max(a, b) / min(a, b)
            vals.append(rr)
            per[r] = float(rr)
        res[bnm] = dict(per_route=per, worst=float(max(vals)) if vals else float("nan"))
    return res


def band_table(data, chan, arm, rgnm, rlo, rhi, bandnames, fmt="{:.4f}"):
    print(f"\n  --- {chan.upper()}  ·  {arm}  ·  {rgnm}  ·  v < {VMAX_KMH} km/h on every route ---")
    hdr = (f"    {'band':<20}" + "".join(f"{l + ' r' + r:>24}" for r, _s, l in ROUTES) +
           f"{'7d/floor':>10}")
    print(hdr)
    rows, cens = {}, {}
    sel_cache = {}
    for r, _s, _l in ROUTES:
        sh, meta = data[r][chan][arm]
        sel = ((meta[:, 0] >= rlo) & (meta[:, 0] < rhi)) if len(meta) else np.zeros(0, bool)
        sel_cache[r] = (sh, meta, sel)
        if sel.sum():
            cens[r] = dict(n_windows=int(sel.sum()),
                           n_blocks=int(len(np.unique(meta[sel, 3]))),
                           v_median_kmh=float(np.median(meta[sel, 1])),
                           v_p90_kmh=float(np.percentile(meta[sel, 1], 90)),
                           rate_median_dps=float(np.median(meta[sel, 0])),
                           press_duty=float(np.mean(meta[sel, 2])))
        else:
            cens[r] = dict(n_windows=0, n_blocks=0)
    null = split_half_null(sel_cache, bandnames)     # 🛑 the null, inside this cell, computed first
    for bnm in bandnames:
        cells, meds = [], {}
        for r, _s, _l in ROUTES:
            sh, meta, sel = sel_cache[r]
            x = sh[bnm][sel] if len(sh[bnm]) else np.zeros(0)
            if len(x) < MIN_WIN:
                cells.append(f"{'n<' + str(MIN_WIN) + ', n/s':>24}")
                meds[r] = np.nan
                continue
            m = float(np.median(x))
            lo_, hi_, nb = block_boot_median(x, meta[sel, 3])
            meds[r] = m
            cells.append(((fmt + " [" + fmt + "," + fmt + "]").format(m, lo_, hi_)
                          if np.isfinite(lo_)
                          else (fmt + " (nb={}, no CI)").format(m, nb)).rjust(24))
        base = [meds[r] for r, _s, _l in ROUTES[1:] if np.isfinite(meds[r])]
        floor = (max(base) / min(base)) if len(base) >= 2 and min(base) > 0 else np.nan
        rows[bnm] = dict(medians={r: meds[r] for r, _s, _l in ROUTES},
                         placebo_floor_77_78_79=float(floor))
        print(f"    {bnm:<20}" + "".join(cells) + f"{floor:>9.2f}×")
    print(f"    {'windows':<20}" + "".join(f"{cens[r]['n_windows']:>24,}" for r, _s, _l in ROUTES))
    print(f"    {'blocks (boot units)':<20}" +
          "".join(f"{cens[r]['n_blocks']:>24,}" for r, _s, _l in ROUTES))
    print(f"    {'v median km/h':<20}" +
          "".join(f"{cens[r].get('v_median_kmh', float('nan')):>24.2f}" for r, _s, _l in ROUTES))
    print(f"    {'|rate| median °/s':<20}" +
          "".join(f"{cens[r].get('rate_median_dps', float('nan')):>24.2f}"
                  for r, _s, _l in ROUTES))
    print(f"    {'hands-on duty':<20}" +
          "".join(f"{cens[r].get('press_duty', float('nan')):>24.3f}" for r, _s, _l in ROUTES))
    # ---- the ratio that matters, against the LOW-SPEED placebo floor and the split-half null
    print(f"\n    {'band':<20}{'r7d / r77':>12}{'r7d / r78':>12}{'r7d / r79':>12}"
          f"{'placebo':>10}{'split-half':>12}  VERDICT")
    for bnm in bandnames:
        md = rows[bnm]["medians"]
        rr = []
        for r in ("77", "78", "79"):
            rr.append(md["7d"] / md[r] if np.isfinite(md["7d"]) and np.isfinite(md[r])
                      and md[r] > 0 else np.nan)
        floor = rows[bnm]["placebo_floor_77_78_79"]
        sh_null = null[bnm]["worst"] if bnm in null else np.nan
        beat = np.nanmax([floor, sh_null])
        obs = np.nanmax([x if np.isfinite(x) and x >= 1 else (1 / x if np.isfinite(x) else np.nan)
                         for x in rr]) if any(np.isfinite(rr)) else np.nan
        v = ("UNSCOREABLE" if not np.isfinite(obs) else
             "INSIDE THE NOISE" if not np.isfinite(beat) or obs <= beat else
             f"exceeds the floor by {obs / beat:.2f}×")
        rows[bnm]["ratios_vs_77_78_79"] = [float(x) for x in rr]
        rows[bnm]["split_half_worst"] = float(sh_null)
        rows[bnm]["verdict"] = v
        rows[bnm]["split_half_per_route"] = null[bnm]["per_route"]
        print(f"    {bnm:<20}" + "".join(f"{x:>12.3f}" if np.isfinite(x) else f"{'n/s':>12}"
                                         for x in rr) +
              f"{floor:>9.2f}×{sh_null:>11.2f}×  {v}")
    return dict(bands=rows, census=cens, split_half=null)


# ======================================================================================
def rez(D, mask, tag, route):
    """Re(Z) = Re(S_Tω / S_ωω) via the FROZEN estimator, with the shuffled-pairs control."""
    W = P._wins(mask, D["t"], NW, HOP, (D["rate_f"] * DEG2RAD, D["tq"]))
    out = dict(route=route, arm=tag, n_windows=len(W), window_s=NW / D["fs"])
    if len(W) < MIN_WIN:
        print(f"    r{route:<3} {tag:<28} {len(W):>4} windows  🛑 TOO FEW -- NOT SCOREABLE")
        out["scoreable"] = False
        return out
    r = P._band_transfer(W, D["fs"], NW, Z_BANDS)
    idx = RNG.permutation(len(W))
    Wsh = [(W[i][0], W[(idx[i] + 1) % len(W)][1]) for i in range(len(W))]
    rs = P._band_transfer(Wsh, D["fs"], NW, Z_BANDS)
    out["scoreable"] = True
    out["bands"] = {}
    flip = None
    prev = None
    for b, _lo, _hi in Z_BANDS:
        a_, s_ = r[b], rs[b]
        tr = bool(np.isfinite(a_["coh2"]) and a_["coh2"] >= COH_ABS
                  and a_["coh2"] >= COH_REL * max(s_["coh2"], 1e-9))
        out["bands"][b] = dict(re_z=a_["re_over_sxx"], mag=a_["gain"], phase=a_["phase_deg"],
                               coh2=a_["coh2"], coh2_shuf=s_["coh2"], trusted=tr)
        if tr:
            if prev is not None and prev[1] < 0 <= a_["re_over_sxx"] and flip is None:
                flip = f"{prev[0]} -> {b}"
            prev = (b, a_["re_over_sxx"])
    out["sign_flip_band"] = flip
    print(f"    r{route:<3} {tag:<28} {len(W):>4} windows   sign flip: {flip or 'none in 2-38 Hz'}")
    print(f"         {'band':8s}" + "".join(f"{b:>11}" for b, _l, _h in Z_BANDS))
    print(f"         {'Re(Z)':8s}" +
          "".join(f"{out['bands'][b]['re_z']:>11.0f}" for b, _l, _h in Z_BANDS))
    print(f"         {'coh²':8s}" +
          "".join(f"{out['bands'][b]['coh2']:>11.3f}" for b, _l, _h in Z_BANDS))
    print(f"         {'shuf':8s}" +
          "".join(f"{out['bands'][b]['coh2_shuf']:>11.3f}" for b, _l, _h in Z_BANDS))
    print(f"         {'TRUST':8s}" +
          "".join(f"{'yes' if out['bands'][b]['trusted'] else '--':>11}"
                  for b, _l, _h in Z_BANDS))
    return out


# ======================================================================================
def main():
    print("=" * 118)
    print(" ROUTE 7d (V94) SYMPTOM BANDS + Re(Z), LOW-SPEED regime (v < 6.2 km/h on every route)")
    print(" 🛑 NW = 256 (2.56 s), NOT the kit's standard 512.  These numbers are NOT comparable to")
    print("    the published 77/78/79 placebo floor; a low-speed short-window floor is recomputed.")
    print(" 🛑 The operator's report -- stuttering and grinding MUCH worse, whole car vibrating,")
    print("    unsafe -- is the primary result.  Nothing below overrules it.")
    print("=" * 118)

    D = {r: load(r, s) for r, s, _l in ROUTES}
    data, absdata, masks = {}, {}, {}
    for r, _s, _l in ROUTES:
        d = D[r]
        vk = d["v"] * 3.6
        masks[r] = {"ENGAGED": d["lat"] & (vk < VMAX_KMH),
                    "MANUAL": (~d["lat"]) & (vk < VMAX_KMH)}
        data[r], absdata[r] = {}, {}
        Ws = {a: windows(d, m) for a, m in masks[r].items()}
        for chan in ("tq", "imu_v", "imu_l"):
            data[r][chan] = {a: band_shares(Ws[a], d["fs"], chan, False) for a in Ws}
            absdata[r][chan] = {a: band_shares(Ws[a], d["fs"], chan, True) for a in Ws}
        print(f"  r{r} ({_l}): fs {d['fs']:.2f} Hz   windows  "
              + "  ".join(f"{a} {len(Ws[a])}" for a in Ws)
              + f"   mask sec  " + "  ".join(f"{a} {masks[r][a].sum()/d['fs']:.1f}" for a in Ws))

    OUT = {"window_samples": NW, "hop": HOP, "vmax_kmh": VMAX_KMH,
           "note": ("NON-STANDARD 2.56 s window; not comparable to the published 5.12 s "
                    "77/78/79 placebo floor. Low-speed floor recomputed inside each table.")}
    SHAPE = [b[0] for b in BANDS]
    LEVEL = SHAPE + ["TOTAL 1-38"]

    print("\n" + "#" * 118)
    print("#  PASS 1 of 2 — SPECTRAL SHAPE (within-window band share).  This is the kit's standard")
    print("#  statistic.  🛑 IT IS BLIND TO A BROADBAND LEVEL RISE: multiply the whole 1-38 Hz band")
    print("#  by any constant and every number below is unchanged.  PASS 2 is the level.")
    print("#" * 118)
    for chan in ("tq", "imu_v", "imu_l"):
        for arm in ("MANUAL", "ENGAGED"):
            for rgnm, rlo, rhi in REGIMES:
                OUT[f"{chan}/{arm}/{rgnm}"] = band_table(data, chan, arm, rgnm, rlo, rhi, SHAPE)

    print("\n" + "#" * 118)
    print("#  PASS 2 of 2 — ABSOLUTE LEVEL (band power density, un-normalised).  🛑 THIS is the one")
    print("#  that can see 'the whole car vibrating'.  tq in counts²/Hz, IMU in (m/s²)²/Hz.")
    print("#  Same windows, same regimes, same split-half null discipline.")
    print("#" * 118)
    for chan in ("tq", "imu_v", "imu_l"):
        for arm in ("MANUAL", "ENGAGED"):
            for rgnm, rlo, rhi in REGIMES:
                OUT[f"ABS/{chan}/{arm}/{rgnm}"] = band_table(absdata, chan, arm, rgnm, rlo, rhi,
                                                             LEVEL, "{:.4g}")

    print("\n" + "=" * 118)
    print(" Re(Z) — driving-point impedance, LOW-SPEED.  Negative Re(Z) == negative damping.")
    print(" Replication to beat (routes 77/78/79, 5.12 s windows, ALL speeds): 6-9 Hz")
    print(" −3375 / −3176 / −3073, coh² 0.71-0.77, flip to damped at ~24-26 Hz; MICRO −3480.")
    print(" 🛑 Those were whole-drive numbers.  These are v < 6.2 km/h at 2.56 s.  Different")
    print("    instrument AND different regime -- read them as a new measurement, not a delta.")
    print("=" * 118)
    OUT["rez"] = {}
    for r, _s, _l in ROUTES:
        d = D[r]
        vk = d["v"] * 3.6
        ang_rate = np.abs(d["rate_f"])
        for tag, m in (("MANUAL low-speed", (~d["lat"]) & (vk < VMAX_KMH)),
                       ("MANUAL low-sp MICRO 1-13", (~d["lat"]) & (vk < VMAX_KMH)
                        & (ang_rate >= 1) & (ang_rate < 13)),
                       ("ENGAGED low-speed", d["lat"] & (vk < VMAX_KMH))):
            OUT["rez"][f"r{r}/{tag}"] = rez(d, m, tag, r)
        print()

    (CACHE / "_scratch/cache/r7d" / "v94_symptom.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("  wrote analysis-2020accord/_scratch/cache/r7d/v94_symptom.json")


if __name__ == "__main__":
    main()
