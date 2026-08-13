#!/usr/bin/env python3
r"""THE RETURN-TO-CENTRE INSTRUMENT — the operator's own scoring criterion, made computable.

His words, 2026-08-12, after seeing the time-domain captures:

  > "notice how in capture 1 and 3 (same event), there is ringing in the driver torque, and a
  >  wiggle in the steering angle as it returns to center.  Notice how normally, without LKAS
  >  engaged, there is no ringing in driver torque sensor and no wiggle in the steering angle as
  >  it returns to center.  The 2nd case is how the LKAS return to center should look, AND it
  >  should be faster than with LKAS disengaged.  THIS is the crux of micro-ratcheting and
  >  grinding."

So the target is a **TRAJECTORY**, not a band.  Two claims to test, and they are separable:

  CLAIM A  engaged returns RING (torque) and WIGGLE (angle); LKAS-off returns do not.
  CLAIM B  the engaged return is currently SLOWER than the LKAS-off return.
           (He asserts it *should* be faster.  This file measures what it *is*.)

🛑 "grinding" / "micro-ratcheting" / "stuttering" are HIS words for symptoms.  "4-12 Hz" is an
INSTRUMENT.  Nothing here scores a symptom; it scores a trajectory, and he scores the symptom.

--------------------------------------------------------------------------------------------------
THE EVENT DEFINITION (stated once; the pre-registration cites these constants by name)

  ang            0x14A STEER_ANGLE, deg, LSB 0.1, 100 Hz.  `ang == wang == cs_ang` bit-for-bit.
  ang2           `ang` low-passed at PEAK_LP = 2.0 Hz.  Used ONLY to locate peaks and to test
                 monotonicity, so that the >4 Hz wiggle we are trying to MEASURE can never create
                 or destroy an event.  Every reported quantity is computed on the RAW signals.

  PEAK           a local maximum of |ang2| with |ang2| >= A_MIN (10 deg) and >= PEAK_SEP (0.30 s)
                 from the previous peak.
  RETURN         from the peak forward to the first sample with |ang2| <= FRAC (0.10) x |peak|.
                 Aborted (and the event discarded) if |ang2| first exceeds OVER_TOL (1.02) x |peak|
                 -- i.e. he wound FURTHER instead of returning -- or if the return has not
                 completed within T_MAX (8.0 s).  Discarded if shorter than T_MIN (0.20 s).
  ARM            ENGAGED if latActive is true on >= 0.95 of the return window AND for GUARD (0.5 s)
                 either side; LKAS-OFF if <= 0.05.  Anything between is a TRANSITION and is dropped
                 -- an event straddling an edge belongs to neither arm.
  HOLD           from |tq| (0x18F STEER_TORQUE_SENSOR, counts) over the return window:
                   HANDS-OFF  p90|tq| <  HOLD_OFF  (300)
                   LIGHT      otherwise
                   HOLDING    p50|tq| >= HOLD_ON   (1200, the kit's `steeringPressed` threshold)
                 🛑 An event where he is holding is NOT comparable to one where he let go, so HOLD
                 is a matching key, not a covariate.

DEFENCE OF THE DEFINITION, and what it deliberately does NOT do
  * It does not require monotonicity of the RAW angle.  A wiggle IS a non-monotonicity; requiring
    monotonicity would delete the phenomenon under test.  Monotonicity is enforced only on the
    2 Hz-smoothed signal, which is blind to 4-12 Hz.
  * It anchors on ANGLE, not on driver torque or on a `steeringPressed` mask.  The kit's standing
    mask is a threshold on driver torque and it is exactly what excluded the symptom regime once
    already (`memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`).
  * FRAC = 10 % of peak, not an absolute angle, so a 300 deg parking return and a 15 deg highway
    return are scored on the same fractional criterion.  |ang| <= 5 deg is reported alongside as an
    absolute-criterion cross-check.
  * All band-limited quantities are filtered ONCE over the whole route and then sliced.  Filtering
    per-window would put a filter transient inside every short return -- the exact failure recorded
    in `memory/accord-ringdown-q-needs-a-step-control.md`.

--------------------------------------------------------------------------------------------------
CONTROLS THAT RUN BEFORE ANY RATIO IS QUOTED (`feedback-run-the-control-before-the-measurement`)
  1. NEGATIVE BANDS   15-22 Hz and 25-40 Hz, carried through every statistic beside the 4-12 Hz
                      wiggle band.  A broadband level difference must not read as a wiggle result.
  2. PLACEBO          arm labels permuted WITHIN each matching cell, PERM times.  Gives the null
                      distribution of the pooled ratio and a two-sided p.
  3. SPLIT-HALF       engaged events split at random into two halves; the half/half ratio is the
                      RESOLUTION FLOOR.  No effect smaller than that floor is quotable.
  4. STEP CONTROL     for the ring-down zeta only: a synthetic oscillation that stops DEAD is passed
                      through the identical filter, at four bandwidths.  A real decay separates from
                      the control as the band widens; a filter artefact does not.

BOOTSTRAP IS OVER EPISODES (`feedback-episodes-not-windows`).  An episode = one contiguous run of
constant latActive state within a route.  Events inside one episode share a driver, a surface and a
manoeuvre and are NOT independent.

CAN-JOIN UNCERTAINTY, stated once and applied everywhere a phase is quoted:
  `ang`/`rate_c` come from 0x14A; `tq` from 0x18F (whose payload is one frame stale --
  `memory/accord-0x18f-payload-one-frame-stale`); `e4tq` from 0x0E4.  The join is worth ~+-10 ms,
  which at 7.8 Hz is ~+-28 deg.  🛑 Only a LARGE phase difference is interpretable.

--------------------------------------------------------------------------------------------------
Usage:
    python v97_return_to_centre.py                 # routes 7e 7f (V96), writes JSON + PNGs
    python v97_return_to_centre.py 80 81           # score a future flight the same way
    python v97_return_to_centre.py --no-plots
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert, find_peaks

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTD = ROOT / "analysis-2020accord" / "_v97"
PLOTD = OUTD / "plots_rtc"

# ---------------------------------------------------------------- frozen constants (cited by the
# pre-registration; changing any of these changes the estimand)
FS = 100.0
PEAK_LP = 2.0          # Hz, smoothing used ONLY for peak location / monotonicity
A_MIN = 10.0           # deg, minimum peak |angle| for an event
PEAK_SEP = 0.30        # s, minimum separation between peaks
FRAC = 0.10            # return ends at 10 % of peak
ABS_END = 5.0          # deg, the absolute-criterion cross-check
OVER_TOL = 1.02        # abort if |ang| climbs 2 % above the peak
T_MIN, T_MAX = 0.20, 8.0
GUARD = 0.50           # s of constant arm state required either side
HOLD_OFF, HOLD_ON = 300.0, 1200.0
# 🛑 BAND CHOICE IS MEASURED, NOT ASSUMED.  A first pass used 4-12 Hz with a 15-22 Hz "control";
# the average return spectrum then showed (a) the ring peaks at 8.00 Hz on BOTH routes, so 4-12
# diluted it with two nearly-null flanks, and (b) 15-22 Hz moves WITH the ring (3.5-4.1x) while
# 30-45 Hz does not (1.4-2.9x) => 15-22 carries the 2nd harmonic of a non-sinusoidal ring and is
# NOT a control.  It is kept, relabelled, as a harmonic diagnostic.
WIG = (6.0, 9.0)                       # the ring band, centred on the measured 8.00 Hz peak
SPEC_DEN = "30-45 Hz (control)"        # denominator of the band-specificity ratio
CTRL = {"30-45 Hz (control)": (30.0, 45.0),
        "4-6 Hz (control)": (4.0, 6.0),
        "15-22 Hz (2nd harmonic)": (15.0, 22.0)}
MIN_SPEC = 0.40        # s, shorter returns get NaN for frequency-domain quantities
PERM = 4000
NBOOT = 20000
SEED = 97

RNG = np.random.default_rng(SEED)

# matching strata -- coarse on purpose; the exposure will not support finer
PK_BINS = [(10, 20), (20, 40), (40, 80), (80, 160), (160, 1e9)]
V_BINS = [(0, 5), (5, 20), (20, 50), (50, 1e9)]


# ---------------------------------------------------------------- signal helpers
def _sos_lp(f):
    return butter(4, f / (FS / 2), btype="low", output="sos")


def _sos_bp(lo, hi):
    return butter(4, [lo / (FS / 2), hi / (FS / 2)], btype="band", output="sos")


def lowpass(x, f):
    return sosfiltfilt(_sos_lp(f), np.asarray(x, float))


def bandpass(x, lo, hi):
    x = np.asarray(x, float)
    return sosfiltfilt(_sos_bp(lo, hi), x - np.mean(x))


def load(route):
    """Cache loader.  Same field names as every cache since `_cache_r6d`."""
    p = ROOT / "analysis-2020accord" / f"_cache_r{route}" / f"r{route}.npz"
    if not p.exists():
        p = ROOT / f"_cache_r{route}" / f"r{route}.npz"
    z = np.load(p, allow_pickle=True)
    t = np.asarray(z["t"], float)
    D = dict(route=route, t=t,
             ang=np.asarray(z["ang"], float),
             rate=np.asarray(z["rate_c"], float),      # 0x14A; slope 0.971 vs d(ang)/dt
             tq=np.asarray(z["tq"], float),
             cmd=np.asarray(z["e4tq"], float),
             req=np.asarray(z["e4req"], float),
             lat=np.asarray(z["cc_lat"], float) > 0.5,
             v=np.abs(np.asarray(z["cs_v"], float)) * 3.6,
             sstat=np.asarray(z["sstat"], float),
             build=str(z["probe_build"][0]) if "probe_build" in z.files else "?")
    D["ang2"] = lowpass(D["ang"], PEAK_LP)
    D["rate2"] = lowpass(D["rate"], PEAK_LP)
    # filter ONCE over the whole route, then slice -- never per-window
    for nm, (lo, hi) in [("wig", WIG)] + [(k, v) for k, v in CTRL.items()]:
        for sig in ("ang", "rate", "tq", "cmd"):
            D[f"{sig}|{nm}"] = bandpass(D[sig], lo, hi)
    an = hilbert(D["ang|wig"])
    D["env_ang"] = np.abs(an)
    D["env_tq"] = np.abs(hilbert(D["tq|wig"]))
    ph = np.unwrap(np.angle(an))
    D["ifreq_ang"] = np.gradient(ph) * FS / (2 * np.pi)
    return D


def quant_floor(lsb, lo, hi):
    """RMS a uniform-quantiser noise floor contributes to a band -- the honest detection limit."""
    return lsb / np.sqrt(12.0) * np.sqrt((hi - lo) / (FS / 2.0))


# ---------------------------------------------------------------- event detection
def detect(D):
    t, a2, lat = D["t"], D["ang2"], D["lat"]
    n = len(t)
    pk, _ = find_peaks(np.abs(a2), height=A_MIN, distance=int(PEAK_SEP * FS))
    g = int(GUARD * FS)
    ev = []
    for k in pk:
        s = np.sign(a2[k])
        pv = abs(a2[k])
        lim = min(n, k + int(T_MAX * FS))
        end = None
        j = k + 1
        while j < lim:
            if abs(a2[j]) > OVER_TOL * pv:
                break                                    # wound further -- not a return
            if abs(a2[j]) <= FRAC * pv:
                end = j
                break
            j += 1
        if end is None or t[end] - t[k] < T_MIN:
            continue
        sl = slice(k, end + 1)
        f = float(lat[sl].mean())
        lo_g, hi_g = max(0, k - g), min(n, end + 1 + g)
        fg = float(lat[lo_g:hi_g].mean())
        if f >= 0.95 and fg >= 0.95:
            arm = "engaged"
        elif f <= 0.05 and fg <= 0.05:
            arm = "off"
        else:
            arm = "transition"
        ev.append(measure(D, k, end, s, pv, arm))
    return ev


def _bandq(D, sig, nm, sl, dur):
    x = D[f"{sig}|{nm}"][sl]
    if dur < MIN_SPEC or len(x) < 8:
        return float("nan"), float("nan")
    return float(np.sqrt(np.mean(x ** 2))), float(np.max(np.abs(x)))


def measure(D, k, end, s, pv, arm):
    t = D["t"]
    sl = slice(k, end + 1)
    dur = float(t[end] - t[k])
    ang, rate, tq, cmd = D["ang"][sl], D["rate"][sl], D["tq"][sl], D["cmd"][sl]
    pv_raw = float(abs(D["ang"][k]))

    # --- absolute-criterion end: first |ang2| <= ABS_END (may be beyond `end` if peak is small)
    j = k
    lim = min(len(t), k + int(T_MAX * FS))
    t5 = float("nan")
    while j < lim:
        if abs(D["ang2"][j]) <= ABS_END:
            t5 = float(t[j] - t[k])
            break
        j += 1

    # --- rate
    kk = int(np.argmax(np.abs(rate)))
    rate_pk = float(abs(rate[kk]))
    rate_mean = float((pv - FRAC * pv) / dur) if dur > 0 else float("nan")
    where_pk = float(kk / max(1, len(rate) - 1))

    # --- overshoot past centre, measured out to +1 s beyond the return
    e2 = min(len(t) - 1, end + int(1.0 * FS))
    past = -s * D["ang2"][end:e2 + 1]
    over = float(max(0.0, past.max())) if len(past) else 0.0

    # --- reversals of the 2 Hz-smoothed rate inside the return (macro non-monotonicity)
    r2 = D["rate2"][sl]
    sg = np.sign(r2[np.abs(r2) > 1.0])
    rev = int(np.sum(np.diff(sg) != 0)) if len(sg) > 1 else 0

    rec = dict(route=D["route"], build=D["build"], arm=arm,
               t_peak=float(t[k]), t_end=float(t[end]), dur=dur, dur_abs5=t5,
               peak_deg=float(pv), peak_deg_raw=pv_raw, sign=float(s),
               rate_peak=rate_pk, rate_mean=rate_mean, rate_peak_at=where_pk,
               overshoot_deg=over, overshoot_frac=float(over / pv) if pv else float("nan"),
               reversals=rev,
               v=float(D["v"][sl].mean()), v_sd=float(D["v"][sl].std()),
               tq_absmed=float(np.median(np.abs(tq))), tq_absp90=float(np.percentile(np.abs(tq), 90)),
               tq_sd=float(np.std(tq)),
               cmd_absmed=float(np.median(np.abs(cmd))), cmd_absmax=float(np.max(np.abs(cmd))),
               cmd_rail=float(np.mean(np.abs(cmd) >= 4090)),
               req_duty=float(np.mean(D["req"][sl] > 0.5)),
               n=int(end - k + 1))

    rec["hold"] = ("HOLDING" if rec["tq_absmed"] >= HOLD_ON else
                   "HANDS-OFF" if rec["tq_absp90"] < HOLD_OFF else "LIGHT")

    for nm in ["wig"] + list(CTRL):
        for sig in ("ang", "rate", "tq", "cmd"):
            r, p = _bandq(D, sig, nm, sl, dur)
            rec[f"{sig}_rms[{nm}]"] = r
            rec[f"{sig}_pk[{nm}]"] = p

    # --- DERIVED, and these are the ones that carry the argument -------------------------------
    # BAND SPECIFICITY: if the engaged/off difference is BROADBAND (a level offset), these ratios
    # are identical in both arms and their contrast collapses to 1.  Only a genuinely 4-12 Hz
    # phenomenon moves them.  This is the test the raw band RMS cannot do.
    for sig in ("ang", "rate", "tq"):
        d = rec[f"{sig}_rms[{SPEC_DEN}]"]
        rec[f"spec_{sig}"] = float(rec[f"{sig}_rms[wig]"] / d) if d and d > 0 else float("nan")
    # SIZE-NORMALISED: a bigger or faster return carries more of everything.  Divide it out.
    rec["wig_per_deg"] = float(rec["ang_rms[wig]"] / pv) if pv > 0 else float("nan")
    rec["rough"] = (float(rec["rate_rms[wig]"] / rec["rate_mean"])
                    if rec["rate_mean"] > 0 else float("nan"))
    rec["ring_per_tq"] = float(rec["tq_rms[wig]"] / max(rec["tq_absmed"], 1.0))

    # --- dominant wiggle frequency: envelope-weighted median instantaneous frequency.
    # Robust on windows too short for Welch, and drift-tolerant.
    if dur >= MIN_SPEC:
        w = D["env_ang"][sl]
        f = D["ifreq_ang"][sl]
        m = np.isfinite(f) & (f > WIG[0]) & (f < WIG[1]) & (w > np.percentile(w, 50))
        rec["f_dom_ang"] = float(np.average(f[m], weights=w[m])) if m.sum() >= 5 else float("nan")
    else:
        rec["f_dom_ang"] = float("nan")
    return rec


def episode_ids(D, ev):
    """Episode = one contiguous run of constant latActive.  Bootstrap unit."""
    lat = D["lat"]
    eid = np.cumsum(np.r_[0, np.diff(lat.astype(np.int8)) != 0])
    idx = np.searchsorted(D["t"], [e["t_peak"] for e in ev])
    for e, i in zip(ev, np.clip(idx, 0, len(eid) - 1)):
        e["episode"] = f"{D['route']}:{int(eid[i])}"
    return ev


# ---------------------------------------------------------------- matched contrast
def cell_of(e):
    pk = next(i for i, (lo, hi) in enumerate(PK_BINS) if lo <= e["peak_deg"] < hi)
    vb = next(i for i, (lo, hi) in enumerate(V_BINS) if lo <= e["v"] < hi)
    return f"pk{pk}/v{vb}/{e['hold']}"


def stratified_ratio(E, M, key, min_cell=2):
    """Weighted geometric mean of per-cell (engaged median / off median).

    Weight = n_e*n_m/(n_e+n_m) -- the effective sample size of the cell contrast.
    Returns (ratio, per-cell table).  NaN if no cell is populated in both arms.
    """
    cells = sorted({e["cell"] for e in E} & {m["cell"] for m in M})
    num, den, tab = 0.0, 0.0, []
    for c in cells:
        a = np.array([e[key] for e in E if e["cell"] == c], float)
        b = np.array([m[key] for m in M if m["cell"] == c], float)
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) < min_cell or len(b) < min_cell:
            continue
        ma, mb = float(np.median(a)), float(np.median(b))
        if not (ma > 0 and mb > 0):
            continue
        w = len(a) * len(b) / (len(a) + len(b))
        num += w * np.log(ma / mb)
        den += w
        tab.append(dict(cell=c, n_eng=len(a), n_off=len(b), med_eng=ma, med_off=mb,
                        ratio=ma / mb, w=w))
    if den == 0:
        return float("nan"), tab
    return float(np.exp(num / den)), tab


def boot_stratified(E, M, key, nboot=NBOOT, seed=SEED):
    """Episode bootstrap of the stratified ratio."""
    rng = np.random.default_rng(seed)
    eps_e = sorted({e["episode"] for e in E})
    eps_m = sorted({m["episode"] for m in M})
    if len(eps_e) < 2 or len(eps_m) < 2:
        return float("nan"), (float("nan"), float("nan")), len(eps_e), len(eps_m)
    by_e = {p: [e for e in E if e["episode"] == p] for p in eps_e}
    by_m = {p: [m for m in M if m["episode"] == p] for p in eps_m}
    pt, _ = stratified_ratio(E, M, key)
    out = []
    for _ in range(nboot):
        se = [x for p in rng.choice(eps_e, len(eps_e)) for x in by_e[p]]
        sm = [x for p in rng.choice(eps_m, len(eps_m)) for x in by_m[p]]
        r, _ = stratified_ratio(se, sm, key)
        if np.isfinite(r):
            out.append(r)
    if len(out) < 100:
        return pt, (float("nan"), float("nan")), len(eps_e), len(eps_m)
    return pt, (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))), \
        len(eps_e), len(eps_m)


def placebo(E, M, key, nperm=PERM, seed=SEED + 1):
    """Permute the ARM LABEL within each matching cell.  Two-sided p and the placebo floor."""
    rng = np.random.default_rng(seed)
    obs, _ = stratified_ratio(E, M, key)
    pool = E + M
    cells = {}
    for x in pool:
        cells.setdefault(x["cell"], []).append(x)
    ne = {c: sum(1 for x in v if x["arm"] == "engaged") for c, v in cells.items()}
    null = []
    for _ in range(nperm):
        se, sm = [], []
        for c, v in cells.items():
            idx = rng.permutation(len(v))
            for j, i in enumerate(idx):
                (se if j < ne[c] else sm).append(v[i])
        r, _ = stratified_ratio(se, sm, key)
        if np.isfinite(r):
            null.append(r)
    null = np.array(null)
    if len(null) < 100 or not np.isfinite(obs):
        return obs, float("nan"), float("nan"), len(null)
    p = float(np.mean(np.abs(np.log(null)) >= abs(np.log(obs))))
    floor = float(np.exp(np.percentile(np.abs(np.log(null)), 95)))
    return obs, p, floor, len(null)


def nn_pairs(E, M, caliper_pk=1.5, caliper_v=6.0, max_dt=None):
    """Nearest-neighbour matched PAIRS -- a robustness check on the coarse strata.

    Each engaged return is paired with the LKAS-off return closest in (log peak angle, speed),
    within a caliper, same HOLD class, and optionally within `max_dt` seconds on the same route
    (which additionally matches the driver, the surface and the manoeuvre).  Sampling WITHOUT
    replacement so one off-event cannot carry the whole result.
    """
    used, pairs = set(), []
    for e in sorted(E, key=lambda x: x["peak_deg"]):
        best, bd = None, 1e18
        for i, m in enumerate(M):
            if i in used or m["hold"] != e["hold"]:
                continue
            if max_dt is not None and (m["route"] != e["route"] or
                                       abs(m["t_peak"] - e["t_peak"]) > max_dt):
                continue
            rp = e["peak_deg"] / m["peak_deg"]
            if not (1 / caliper_pk <= rp <= caliper_pk):
                continue
            if abs(e["v"] - m["v"]) > caliper_v:
                continue
            d = abs(np.log(rp)) + abs(e["v"] - m["v"]) / caliper_v
            if d < bd:
                best, bd = i, d
        if best is not None:
            used.add(best)
            pairs.append((e, M[best]))
    return pairs


def paired_ratio(pairs, key, nboot=NBOOT, seed=SEED + 5):
    """Median of the within-pair ratio, bootstrapped over the ENGAGED member's episode."""
    r = np.array([e[key] / m[key] for e, m in pairs
                  if np.isfinite(e[key]) and np.isfinite(m[key]) and m[key] > 0 and e[key] > 0],
                 float)
    eps = np.array([e["episode"] for e, m in pairs
                    if np.isfinite(e[key]) and np.isfinite(m[key]) and m[key] > 0 and e[key] > 0])
    if len(r) < 4:
        return float("nan"), (float("nan"), float("nan")), len(r)
    rng = np.random.default_rng(seed)
    ue = sorted(set(eps))
    by = {p: r[eps == p] for p in ue}
    out = []
    for _ in range(nboot):
        s = np.concatenate([by[p] for p in rng.choice(ue, len(ue))])
        out.append(np.median(s))
    return float(np.median(r)), (float(np.percentile(out, 2.5)),
                                 float(np.percentile(out, 97.5))), len(r)


def ancova(ALL, key, nboot=4000, seed=SEED + 6, log=True):
    """log(y) ~ b0 + b1 log(peak_deg) + b2 log(v+1) + b3 |cmd| flag + bA [arm==engaged].

    Uses EVERY event rather than only the matched cells, so it is the higher-power estimate; it
    buys that with a functional-form assumption the stratified estimate does not make.  CI by
    CLUSTER bootstrap over episodes.  Reported ALONGSIDE the stratified ratio, never instead of it.
    """
    rows = [e for e in ALL if e["arm"] in ("engaged", "off") and np.isfinite(e.get(key, np.nan))]
    if log:
        rows = [e for e in rows if e[key] > 0]
    if len(rows) < 12:
        return dict(n=len(rows), ratio=float("nan"), ci=[float("nan")] * 2)
    y = np.array([np.log(e[key]) if log else e[key] for e in rows])
    X = np.column_stack([np.ones(len(rows)),
                         np.log([e["peak_deg"] for e in rows]),
                         np.log([e["v"] + 1 for e in rows]),
                         [1.0 if e["hold"] == "HOLDING" else 0.0 for e in rows],
                         [1.0 if e["arm"] == "engaged" else 0.0 for e in rows]])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    eps = np.array([e["episode"] for e in rows])
    ue = sorted(set(eps))
    idx = {p: np.where(eps == p)[0] for p in ue}
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(nboot):
        take = np.concatenate([idx[p] for p in rng.choice(ue, len(ue))])
        try:
            bb = np.linalg.lstsq(X[take], y[take], rcond=None)[0]
            bs.append(bb[-1])
        except np.linalg.LinAlgError:
            pass
    if len(bs) < 100:
        return dict(n=len(rows), ratio=float(np.exp(b[-1])), ci=[float("nan")] * 2)
    return dict(n=len(rows), n_ep=len(ue),
                ratio=float(np.exp(b[-1])),
                ci=[float(np.exp(np.percentile(bs, 2.5))), float(np.exp(np.percentile(bs, 97.5)))],
                b_peak=float(b[1]), b_speed=float(b[2]), b_hold=float(b[3]))


PROFILE_BANDS = [(2, 4), (4, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 22), (22, 30), (30, 45)]


def band_profile(Ds, pairs, sig, nboot=4000, seed=SEED + 4):
    """Engaged/off band profile computed on the NN-MATCHED PAIRS only.

    🛑 The unmatched pooled version of this is CONFOUNDED and says something different: the
    LKAS-off returns in this corpus are ~10x larger in peak angle (304 deg vs 31 deg) and slower,
    which loads their low-frequency angle content and drags the 4-6 Hz flank.  Only the matched
    profile is interpretable.  Bootstrap is over the engaged member's EPISODE.
    """
    # Same method as every other statistic in this file: filter the WHOLE route once, then slice.
    # (An earlier version ran Welch per window; on a ~1.4 s return that is 1-2 segments at 1 Hz
    #  resolution -- 3 bins across the signal band -- and it disagreed with the filtered-rms
    #  estimator by 3x on the same pairs.  The per-window spectrum is the unreliable one.)
    filt = {}
    for r_, D in Ds.items():
        filt[r_] = {b: bandpass(D[sig], b[0], b[1]) for b in PROFILE_BANDS}
    rows, eps = [], []
    for e, m in pairs:
        r = []
        ok = True
        for x in (e, m):
            D = Ds[x["route"]]
            k = int(np.searchsorted(D["t"], x["t_peak"]))
            j = int(np.searchsorted(D["t"], x["t_end"]))
            if j - k < 40:
                ok = False
                break
            r.append([float(np.sqrt(np.mean(filt[x["route"]][b][k:j] ** 2)))
                      for b in PROFILE_BANDS])
        if ok:
            rows.append((np.array(r[0]), np.array(r[1])))
            eps.append(e["episode"])
    if len(rows) < 4:
        return None
    eps = np.array(eps)
    ue = sorted(set(eps))
    idx = {p: np.where(eps == p)[0] for p in ue}
    rng = np.random.default_rng(seed)
    lr = np.array([np.log(np.maximum(a, 1e-9) / np.maximum(b, 1e-9)) for a, b in rows])
    bs = []
    for _ in range(nboot):
        take = np.concatenate([idx[p] for p in rng.choice(ue, len(ue))])
        bs.append(np.median(lr[take], axis=0))
    bs = np.array(bs)
    return dict(signal=sig, n_pairs=len(rows), n_ep=len(ue),
                bands=[list(b) for b in PROFILE_BANDS],
                ratio=np.exp(np.median(lr, axis=0)).tolist(),
                lo=np.exp(np.percentile(bs, 2.5, axis=0)).tolist(),
                hi=np.exp(np.percentile(bs, 97.5, axis=0)).tolist(),
                eng_med=np.median([a for a, b in rows], axis=0).tolist(),
                off_med=np.median([b for a, b in rows], axis=0).tolist())


def split_half(E, key, nrep=2000, seed=SEED + 2):
    """Resolution floor: engaged vs engaged, split by EPISODE."""
    rng = np.random.default_rng(seed)
    eps = sorted({e["episode"] for e in E})
    if len(eps) < 4:
        return float("nan")
    by = {p: [e for e in E if e["episode"] == p] for p in eps}
    rs = []
    for _ in range(nrep):
        pm = rng.permutation(eps)
        h = len(eps) // 2
        a = [x[key] for p in pm[:h] for x in by[p]]
        b = [x[key] for p in pm[h:] for x in by[p]]
        a = np.array(a, float)[np.isfinite(a)]
        b = np.array(b, float)[np.isfinite(b)]
        if len(a) >= 3 and len(b) >= 3 and np.median(b) > 0:
            rs.append(np.median(a) / np.median(b))
    if len(rs) < 100:
        return float("nan")
    return float(np.exp(np.percentile(np.abs(np.log(np.array(rs))), 95)))


# ---------------------------------------------------------------- ring-down zeta + step control
def ringdown(D, ev, half_widths=(1.5, 3.0, 5.0, 8.0), f0=None, tag="engaged"):
    """Envelope decay of the wiggle after the ANGLE peak, with the mandatory STEP CONTROL.

    🛑 `memory/accord-ringdown-q-needs-a-step-control.md`: two agents independently fitted a
    bandpass filter's own step response and read it as plant damping.  A filter's step response IS
    a clean exponential, so R^2 proves nothing.  The control below bandpasses a synthetic
    oscillation that stops DEAD; a real decay separates from it as the band widens.
    """
    f0s = [e["f_dom_ang"] for e in ev if np.isfinite(e.get("f_dom_ang", np.nan))]
    fc = float(np.median(f0s)) if f0s else 7.8
    if f0:
        fc = f0
    out = dict(tag=tag, f0_used=fc, n_events=len(ev), per_width=[])
    for hw in half_widths:
        lo, hi = max(0.5, fc - hw), min(FS / 2 - 1, fc + hw)
        # --- DATA
        taus, r2s = [], []
        y = np.abs(hilbert(bandpass(D["ang"], lo, hi)))
        for e in ev:
            k = int(np.searchsorted(D["t"], e["t_peak"]))
            n0 = int(0.15 * FS)                       # start >= 0.15 s after the peak
            n1 = int(min(1.2, max(e["dur"], 0.5)) * FS)
            if k + n1 >= len(y) or n1 - n0 < int(0.25 * FS):
                continue
            seg = y[k + n0:k + n1]
            if seg.min() <= 0 or seg.max() / max(seg.min(), 1e-9) < 3.0:
                continue                              # need a real decay, not noise
            tt = np.arange(len(seg)) / FS
            b, a0 = np.polyfit(tt, np.log(seg), 1)
            if b >= 0:
                continue
            pred = a0 + b * tt
            ss = 1 - np.sum((np.log(seg) - pred) ** 2) / max(
                np.sum((np.log(seg) - np.mean(np.log(seg))) ** 2), 1e-12)
            if ss < 0.90:
                continue
            taus.append(-1.0 / b)
            r2s.append(ss)
        # --- STEP CONTROL: a sine at fc that stops dead, zero plant decay
        n = int(6 * FS)
        tt = np.arange(n) / FS
        syn = np.sin(2 * np.pi * fc * tt)
        syn[n // 2:] = 0.0
        ys = np.abs(hilbert(sosfiltfilt(_sos_bp(lo, hi), syn)))
        s0 = n // 2 + int(0.15 * FS)
        s1 = s0 + int(0.85 * FS)
        seg = np.clip(ys[s0:s1], 1e-12, None)
        bs, _ = np.polyfit(np.arange(len(seg)) / FS, np.log(seg), 1)
        tau_step = float(-1.0 / bs) if bs < 0 else float("nan")
        row = dict(half_width=hw, band=[lo, hi], n_fit=len(taus),
                   tau_step=tau_step,
                   tau_data=float(np.median(taus)) if taus else float("nan"),
                   tau_data_ci=(float(np.percentile(taus, 2.5)), float(np.percentile(taus, 97.5)))
                   if len(taus) >= 8 else (float("nan"), float("nan")),
                   r2_med=float(np.median(r2s)) if r2s else float("nan"))
        row["ratio_data_over_step"] = (row["tau_data"] / tau_step
                                       if np.isfinite(row["tau_data"]) and tau_step else float("nan"))
        if np.isfinite(row["tau_data"]):
            row["zeta_data"] = float(1.0 / (2 * np.pi * fc * row["tau_data"]))
            row["Q_data"] = float(np.pi * fc * row["tau_data"])
        out["per_width"].append(row)
    return out


# ---------------------------------------------------------------- does the COMMAND wiggle?
def command_coupling(D, ev, nperm=2000, seed=SEED + 3):
    """Complex demodulation at each event's own f_dom: is the LKAS command wiggling too?

    Vector-average the normalised cross-product across events => a coherence-like magnitude and a
    phase.  Control: pair event i's COMMAND with event j's ANGLE (i != j) -- destroys any true
    coupling while preserving every marginal.
    🛑 CAN join is ~+-10 ms == ~+-28 deg at 7.8 Hz.  Only a LARGE phase is interpretable.
    """
    rng = np.random.default_rng(seed)
    A, C, W, f0s = [], [], [], []
    for e in ev:
        if not np.isfinite(e.get("f_dom_ang", np.nan)) or e["dur"] < 0.6:
            continue
        k = int(np.searchsorted(D["t"], e["t_peak"]))
        j = int(np.searchsorted(D["t"], e["t_end"]))
        if j - k < int(0.6 * FS):
            continue
        f = e["f_dom_ang"]
        tt = D["t"][k:j] - D["t"][k]
        car = np.exp(-2j * np.pi * f * tt)
        wa = np.sum(D["ang|wig"][k:j] * car)
        wc = np.sum(D["cmd|wig"][k:j] * car)
        if abs(wa) == 0 or abs(wc) == 0:
            continue
        A.append(wa / abs(wa))
        C.append(wc / abs(wc))
        W.append(j - k)
        f0s.append(f)
    if len(A) < 5:
        return dict(n=len(A), note="too few events")
    A, C, W = np.array(A), np.array(C), np.array(W, float)
    x = (A * np.conj(C))
    x /= np.abs(x)
    v = np.average(x, weights=W)
    # the |R| a random-phase vector average would give with this n -- the honest floor
    floor = float(np.sqrt(np.pi) / (2 * np.sqrt(len(A))))
    nullv = []
    for _ in range(nperm):
        p = rng.permutation(len(A))
        y = A * np.conj(C[p])
        y /= np.abs(y)
        nullv.append(abs(np.average(y, weights=W)))
    nullv = np.array(nullv)
    # magnitude of the command wiggle relative to the command's own control-band level
    cw = np.array([e["cmd_rms[wig]"] for e in ev], float)
    cc = np.array([e[f"cmd_rms[{SPEC_DEN}]"] for e in ev], float)
    m = np.isfinite(cw) & np.isfinite(cc) & (cc > 0)
    return dict(n=int(len(A)), f0_med=float(np.median(f0s)),
                R=float(abs(v)), phase_deg=float(np.degrees(np.angle(v))),
                random_floor=floor,
                shuffled_R_med=float(np.median(nullv)),
                shuffled_R_p95=float(np.percentile(nullv, 95)),
                p_vs_shuffled=float(np.mean(nullv >= abs(v))),
                cmd_wig_over_ctrl=float(np.median(cw[m] / cc[m])) if m.sum() else float("nan"),
                can_join_deg=float(360 * 0.010 * float(np.median(f0s))))


# ---------------------------------------------------------------- plots
def plots(Ds, evs):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as ex:                                     # pragma: no cover
        print(f"  [plots skipped: {ex}]")
        return []
    PLOTD.mkdir(parents=True, exist_ok=True)
    C_ANG, C_TQ, C_CMD, C_HP = "#1baf7a", "#2a78d6", "#eb6834", "#4a3aa7"
    SURF, GRID, INK, MUT = "#fcfcfb", "#e6e5e2", "#0b0b0b", "#52514e"

    def style(a):
        a.set_facecolor(SURF)
        a.grid(True, color=GRID, lw=0.8)
        a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        a.tick_params(colors=MUT, labelsize=8)

    written = []

    def one(D, e, path, title):
        k = int(np.searchsorted(D["t"], e["t_peak"]))
        j = int(np.searchsorted(D["t"], e["t_end"]))
        a = max(0, k - int(1.5 * FS))
        b = min(len(D["t"]), j + int(2.0 * FS))
        tt = D["t"][a:b] - e["t_peak"]
        fig, ax = plt.subplots(4, 1, figsize=(9, 8.2), sharex=True,
                               gridspec_kw=dict(hspace=0.14))
        fig.patch.set_facecolor(SURF)
        for x in ax:
            style(x)
            x.axvspan(0, e["dur"], color="#ffd9a8", alpha=0.45, lw=0)
            x.axvline(0, color=MUT, lw=0.8, ls="--")
        ax[0].plot(tt, D["ang"][a:b], color=C_ANG, lw=1.3)
        ax[0].axhline(0, color=MUT, lw=0.7)
        ax[0].axhline(FRAC * e["peak_deg"] * e["sign"], color=MUT, lw=0.7, ls=":")
        ax[0].set_ylabel("steer angle  deg", color=INK, fontsize=9)
        ax[1].plot(tt, D["ang|wig"][a:b], color=C_HP, lw=1.1)
        ax[1].set_ylabel(f"angle {WIG[0]:.0f}-{WIG[1]:.0f} Hz  deg", color=INK, fontsize=9)
        ax[2].plot(tt, D["tq"][a:b], color=C_TQ, lw=1.1)
        ax[2].set_ylabel("driver torque  ct", color=INK, fontsize=9)
        ax[3].plot(tt, D["tq|wig"][a:b], color=C_TQ, lw=1.1, label="torque, band")
        ax[3].plot(tt, D["cmd|wig"][a:b], color=C_CMD, lw=1.0, alpha=0.8, label="LKAS cmd, band")
        ax[3].legend(fontsize=7, frameon=False, loc="upper right")
        ax[3].set_ylabel(f"{WIG[0]:.0f}-{WIG[1]:.0f} Hz  ct", color=INK, fontsize=9)
        ax[3].set_xlabel("time from peak |angle|   s", color=INK, fontsize=9)
        fig.suptitle(title, color=INK, fontsize=10, y=0.955)
        fig.savefig(path, dpi=125, facecolor=SURF, bbox_inches="tight")
        plt.close(fig)
        written.append(str(path))

    # a matched quartet: pick the cells with both arms, take the median-peak event of each
    byc = {}
    for r, ev in evs.items():
        for e in ev:
            if e["arm"] in ("engaged", "off"):
                byc.setdefault((e["cell"], e["arm"]), []).append((r, e))
    both = sorted({c for (c, arm) in byc if (c, "engaged") in byc and (c, "off") in byc})
    n = 0
    for c in both:
        for arm in ("engaged", "off"):
            lst = sorted(byc[(c, arm)], key=lambda x: x[1]["peak_deg"])
            r, e = lst[len(lst) // 2]
            one(Ds[r], e, PLOTD / f"matched_{c.replace('/','_')}_{arm}.png",
                f"r{r}  {arm.upper()}  cell {c}   peak {e['peak_deg']:.0f} deg  "
                f"{e['v']:.0f} km/h  {e['hold']}   dur {e['dur']:.2f} s  "
                f"wiggle {e['ang_rms[wig]']:.3f} deg rms")
            n += 1
        if n >= 12:
            break

    # the extremes, so the detector can be eyeballed against the operator's own captures
    allev = [(r, e) for r, ev in evs.items() for e in ev if e["arm"] == "engaged"]
    allev = [x for x in allev if np.isfinite(x[1]["ang_rms[wig]"])]
    allev.sort(key=lambda x: -x[1]["ang_rms[wig]"])
    for i, (r, e) in enumerate(allev[:4]):
        one(Ds[r], e, PLOTD / f"worst_wiggle_{i}_r{r}.png",
            f"r{r}  ENGAGED, LARGEST WIGGLE #{i+1}   t={e['t_peak']:.1f}s  "
            f"peak {e['peak_deg']:.0f} deg  {e['v']:.0f} km/h  {e['hold']}  "
            f"wiggle {e['ang_rms[wig]']:.3f} deg rms @ {e['f_dom_ang']:.1f} Hz")
    offev = [(r, e) for r, ev in evs.items() for e in ev if e["arm"] == "off"]
    offev = [x for x in offev if np.isfinite(x[1]["ang_rms[wig]"])]
    offev.sort(key=lambda x: -x[1]["ang_rms[wig]"])
    for i, (r, e) in enumerate(offev[:2]):
        one(Ds[r], e, PLOTD / f"lkasoff_largest_wiggle_{i}_r{r}.png",
            f"r{r}  LKAS OFF, LARGEST WIGGLE #{i+1}   t={e['t_peak']:.1f}s  "
            f"peak {e['peak_deg']:.0f} deg  {e['v']:.0f} km/h  {e['hold']}  "
            f"wiggle {e['ang_rms[wig]']:.3f} deg rms")

    # detector overview: every event marked on the angle trace
    for r, ev in evs.items():
        D = Ds[r]
        fig, ax = plt.subplots(figsize=(13, 3.6))
        style(ax)
        fig.patch.set_facecolor(SURF)
        ax.plot(D["t"], D["ang"], color="#9a9a97", lw=0.5)
        ax.plot(D["t"][D["lat"]], D["ang"][D["lat"]], ".", color=C_ANG, ms=0.7)
        for e in ev:
            col = {"engaged": "#d13b3b", "off": "#2a78d6"}.get(e["arm"], "#bdbdbd")
            ax.plot([e["t_peak"], e["t_end"]], [e["peak_deg"] * e["sign"]] * 2, color=col, lw=2.0)
            ax.plot(e["t_peak"], e["peak_deg"] * e["sign"], "o", color=col, ms=3)
        ax.set_title(f"route {r} ({D['build']}) — every detected return.  green = latActive.  "
                     f"red bar = ENGAGED return, blue = LKAS-OFF, grey = transition (dropped)",
                     color=INK, fontsize=9)
        ax.set_xlabel("route time  s", color=INK, fontsize=9)
        ax.set_ylabel("steer angle  deg", color=INK, fontsize=9)
        p = PLOTD / f"detector_overview_r{r}.png"
        fig.savefig(p, dpi=125, facecolor=SURF, bbox_inches="tight")
        plt.close(fig)
        written.append(str(p))
    return written


# ---------------------------------------------------------------- main
W = f"{WIG[0]:.0f}-{WIG[1]:.0f} Hz"
KEYS_A = [("ang_rms[wig]", f"WIGGLE  angle {W} rms (deg)"),
          ("ang_pk[wig]", f"WIGGLE  angle {W} peak (deg)"),
          ("rate_rms[wig]", f"WIGGLE  angle-rate {W} rms (deg/s)"),
          ("tq_rms[wig]", f"RINGING driver torque {W} rms (ct)"),
          ("tq_pk[wig]", f"RINGING driver torque {W} peak (ct)")]
KEYS_CTRL = [(f"ang_rms[{c}]", f"CONTROL angle {c}") for c in CTRL] + \
            [(f"tq_rms[{c}]", f"CONTROL torque {c}") for c in CTRL]
KEYS_SPEC = [("spec_ang", f"SPECIFICITY angle  6-9 / {SPEC_DEN[:5]}"),
             ("spec_rate", f"SPECIFICITY rate   6-9 / {SPEC_DEN[:5]}"),
             ("spec_tq", f"SPECIFICITY torque 6-9 / {SPEC_DEN[:5]}"),
             ("wig_per_deg", "SIZE-NORM wiggle rms / peak angle"),
             ("rough", "SIZE-NORM rate roughness (6-9 rms / mean rate)"),
             ("ring_per_tq", "SIZE-NORM torque ring / |tq| median")]
KEYS_B = [("dur", "RETURN DURATION peak -> 10 % of peak (s)"),
          ("dur_abs5", "RETURN DURATION peak -> |ang| <= 5 deg (s)"),
          ("rate_peak", "peak return rate (deg/s)"),
          ("rate_mean", "mean return rate (deg/s)"),
          ("overshoot_frac", "overshoot past centre / peak"),
          ("reversals", "macro reversals in the return")]


def main(routes, do_plots=True):
    OUTD.mkdir(parents=True, exist_ok=True)
    Ds, evs = {}, {}
    print("=" * 100)
    print("V97 RETURN-TO-CENTRE INSTRUMENT")
    print(f"  event: peak |ang2| >= {A_MIN:.0f} deg  ->  |ang2| <= {FRAC:.0%} of peak, "
          f"{T_MIN}-{T_MAX} s, abort if |ang| > {OVER_TOL:.2f}x peak")
    print(f"  ang2 = ang low-passed at {PEAK_LP:.1f} Hz (peak location + monotonicity ONLY)")
    print(f"  wiggle band {WIG[0]:.0f}-{WIG[1]:.0f} Hz; controls " + ", ".join(CTRL))
    fl_a = quant_floor(0.1, *WIG)
    fl_r = quant_floor(1.0, *WIG)
    print(f"  quantiser noise floor in-band: angle {fl_a:.4f} deg rms (LSB 0.1), "
          f"rate {fl_r:.4f} deg/s rms (LSB 1)")
    print("=" * 100)

    for r in routes:
        D = load(r)
        ev = episode_ids(D, detect(D))
        for e in ev:
            e["cell"] = cell_of(e)
        Ds[r], evs[r] = D, ev
        c = {a: sum(1 for e in ev if e["arm"] == a) for a in ("engaged", "off", "transition")}
        print(f"\nroute {r}  build {D['build']}  {D['t'][-1]-D['t'][0]:.0f} s   "
              f"engaged {D['lat'].sum()/FS:.0f} s / off {(~D['lat']).sum()/FS:.0f} s")
        print(f"   returns detected: ENGAGED {c['engaged']}   LKAS-OFF {c['off']}   "
              f"transition (dropped) {c['transition']}")
        for arm in ("engaged", "off"):
            s = [e for e in ev if e["arm"] == arm]
            if not s:
                continue
            print(f"     {arm:8s} peak|ang| med {np.median([e['peak_deg'] for e in s]):6.1f} deg  "
                  f"v med {np.median([e['v'] for e in s]):5.1f} km/h  "
                  f"dur med {np.median([e['dur'] for e in s]):5.2f} s  "
                  f"hold " + " ".join(f"{h}:{sum(1 for e in s if e['hold']==h)}"
                                      for h in ("HANDS-OFF", "LIGHT", "HOLDING")))

    ALL = [e for r in routes for e in evs[r]]
    E = [e for e in ALL if e["arm"] == "engaged"]
    M = [e for e in ALL if e["arm"] == "off"]
    print(f"\nPOOLED: {len(E)} engaged returns / {len(M)} LKAS-off returns "
          f"({len({e['episode'] for e in E})} / {len({e['episode'] for e in M})} episodes)")

    # ---- matching census
    print("\n--- MATCHING CELLS (peak-angle bin / speed bin / hold state) ---")
    cells = sorted({e["cell"] for e in ALL if e["arm"] in ("engaged", "off")})
    census = []
    for c in cells:
        ne = sum(1 for e in E if e["cell"] == c)
        nm = sum(1 for e in M if e["cell"] == c)
        census.append(dict(cell=c, n_eng=ne, n_off=nm, matched=bool(ne >= 2 and nm >= 2)))
        if ne or nm:
            print(f"   {c:34s} eng {ne:3d}  off {nm:3d}   "
                  f"{'<= MATCHED' if ne >= 2 and nm >= 2 else ''}")
    nmat_e = sum(1 for e in E if any(x["matched"] and x["cell"] == e["cell"] for x in census))
    nmat_m = sum(1 for m in M if any(x["matched"] and x["cell"] == m["cell"] for x in census))
    print(f"   => {sum(1 for x in census if x['matched'])} matched cells, "
          f"carrying {nmat_e} engaged / {nmat_m} LKAS-off returns")

    res = dict(config=dict(FS=FS, PEAK_LP=PEAK_LP, A_MIN=A_MIN, PEAK_SEP=PEAK_SEP, FRAC=FRAC,
                           ABS_END=ABS_END, OVER_TOL=OVER_TOL, T_MIN=T_MIN, T_MAX=T_MAX,
                           GUARD=GUARD, HOLD_OFF=HOLD_OFF, HOLD_ON=HOLD_ON, WIG=list(WIG),
                           CTRL={k: list(v) for k, v in CTRL.items()}, MIN_SPEC=MIN_SPEC,
                           PK_BINS=PK_BINS, V_BINS=[list(b) for b in V_BINS],
                           PERM=PERM, NBOOT=NBOOT, SEED=SEED,
                           quant_floor_ang_deg=fl_a, quant_floor_rate_dps=fl_r),
               routes=list(routes), events=ALL, census=census,
               n=dict(engaged=len(E), off=len(M),
                      ep_engaged=len({e["episode"] for e in E}),
                      ep_off=len({e["episode"] for e in M}),
                      matched_engaged=nmat_e, matched_off=nmat_m),
               contrasts={}, ringdown={}, command={})

    def run(key, label):
        pt, ci, ne, nm = boot_stratified(E, M, key)
        obs, p, floor, _ = placebo(E, M, key)
        sh = split_half(E, key)
        _, tab = stratified_ratio(E, M, key)
        res["contrasts"][key] = dict(label=label, ratio=pt, ci=list(ci), p_placebo=p,
                                     placebo_floor=floor, splithalf_floor=sh,
                                     n_ep_eng=ne, n_ep_off=nm, cells=tab,
                                     med_eng=float(np.nanmedian([e[key] for e in E])),
                                     med_off=float(np.nanmedian([m[key] for m in M])))
        star = ""
        if np.isfinite(pt) and np.isfinite(floor):
            star = " ***" if (ci[0] > floor or ci[1] < 1 / floor) else ""
        print(f"   {label:46s} {np.nanmedian([e[key] for e in E]):9.3f} "
              f"{np.nanmedian([m[key] for m in M]):9.3f} {pt:7.2f}x "
              f"[{ci[0]:5.2f},{ci[1]:6.2f}]  p={p:.3f}  placebo {floor:4.2f}x  "
              f"split-half {sh:4.2f}x{star}")

    print("\n=== CLAIM A — do engaged returns RING and WIGGLE? (stratified engaged/off) ===")
    print(f"   {'statistic':46s} {'ENG med':>9s} {'OFF med':>9s} {'ratio':>8s}  95% CI (episode boot)")
    for k, lab in KEYS_A:
        run(k, lab)
    print("   --- negative-band controls (the mechanism should NOT move these) ---")
    for k, lab in KEYS_CTRL:
        run(k, lab)
    print("   --- 🛑 SPECIFICITY: does the difference survive dividing out the control band / size? ---")
    for k, lab in KEYS_SPEC:
        run(k, lab)

    print("\n=== CLAIM B — is the engaged return SLOWER? (ratio > 1 on duration = SLOWER) ===")
    print(f"   {'statistic':46s} {'ENG med':>9s} {'OFF med':>9s} {'ratio':>8s}  95% CI (episode boot)")
    for k, lab in KEYS_B:
        if k == "reversals":
            for e in ALL:
                e["_rev1"] = e["reversals"] + 1.0
            run("_rev1", "macro reversals + 1")
            continue
        run(k, lab)

    # ---------------- two independent estimators of the same contrasts ----------------
    HEAD = [k for k, _ in KEYS_A] + [k for k, _ in KEYS_SPEC] + \
           [f"{s}_rms[{c}]" for c in CTRL for s in ("ang", "tq")] + \
           ["dur", "dur_abs5", "rate_peak", "rate_mean"]
    print("\n=== ROBUSTNESS — the same contrasts by two other estimators ===")
    for tag, kw in (("NN pairs, any time", dict()),
                    ("NN pairs, same route within 120 s", dict(max_dt=120.0))):
        pr = nn_pairs(E, M, **kw)
        print(f"\n   --- {tag}: {len(pr)} pairs "
              f"({len({p[0]['episode'] for p in pr})} engaged episodes) ---")
        if len(pr) >= 4:
            for k in HEAD:
                r, ci, n = paired_ratio(pr, k)
                res["contrasts"].setdefault(k, {}).setdefault("pairs", {})[tag] = \
                    dict(ratio=r, ci=list(ci), n=n)
                print(f"      {k:46s} {r:7.2f}x [{ci[0]:5.2f},{ci[1]:6.2f}]  n={n}")
        res.setdefault("pair_census", {})[tag] = dict(
            n_pairs=len(pr),
            pairs=[dict(route=e["route"], t_eng=e["t_peak"], t_off=m["t_peak"],
                        peak_eng=e["peak_deg"], peak_off=m["peak_deg"],
                        v_eng=e["v"], v_off=m["v"], hold=e["hold"]) for e, m in pr])

    print("\n=== 🛑 MATCHED BAND PROFILE — WHERE the engaged/off difference lives ===")
    print("   NN-matched pairs only (the unmatched pooled spectrum is confounded by return size)")
    prof = {}
    pr_all = nn_pairs(E, M)
    for sig, unit in (("tq", "ct"), ("ang", "deg"), ("rate", "deg/s")):
        p = band_profile(Ds, pr_all, sig)
        if p is None:
            continue
        prof[sig] = p
        print(f"   {sig} ({unit}), {p['n_pairs']} pairs / {p['n_ep']} episodes  — "
              f"quantiser floor per band shown where relevant")
        print(f"      {'band':>10s} {'ENGAGED':>10s} {'LKAS-off':>10s} {'ratio':>8s}  95% CI")
        for i, (a, b) in enumerate(PROFILE_BANDS):
            fl = quant_floor(0.1 if sig == "ang" else 1.0, a, b)
            mark = "  <- SIGNAL" if (a, b) == tuple(int(x) for x in WIG) else ""
            if p["eng_med"][i] < 3 * fl and p["off_med"][i] < 3 * fl:
                mark += "  (both at quantiser floor)"
            print(f"      {a:4d}-{b:2d} Hz {p['eng_med'][i]:10.4f} {p['off_med'][i]:10.4f} "
                  f"{p['ratio'][i]:8.2f}x [{p['lo'][i]:5.2f},{p['hi'][i]:6.2f}]{mark}")
    res["band_profile"] = prof

    print("\n   --- ANCOVA: log(y) ~ log(peak) + log(v+1) + HOLDING + [ENGAGED] ---")
    print(f"      {'statistic':46s} {'exp(bA)':>9s}  95% CI (episode cluster boot)   n")
    for k in HEAD:
        a = ancova(ALL, k)
        res["contrasts"].setdefault(k, {})["ancova"] = a
        print(f"      {k:46s} {a['ratio']:9.2f}x [{a['ci'][0]:5.2f},{a['ci'][1]:6.2f}]  "
              f"n={a['n']:3d}  b_peak={a.get('b_peak', float('nan')):+.2f} "
              f"b_speed={a.get('b_speed', float('nan')):+.2f}")

    print("\n=== DEFINITION SENSITIVITY — does the answer depend on the thresholds? ===")
    print(f"      {'A_MIN':>6s} {'FRAC':>6s} {'n eng':>6s} {'n off':>6s} "
          f"{'wiggle':>9s} {'ring':>9s} {'dur':>9s}")
    base = (A_MIN, FRAC)
    sens = []
    for amin, frac in ((10.0, 0.10), (10.0, 0.20), (20.0, 0.10), (20.0, 0.20), (40.0, 0.10)):
        globals()["A_MIN"], globals()["FRAC"] = amin, frac
        e2, m2 = [], []
        for r in routes:
            ev2 = episode_ids(Ds[r], detect(Ds[r]))
            for x in ev2:
                x["cell"] = cell_of(x)
            e2 += [x for x in ev2 if x["arm"] == "engaged"]
            m2 += [x for x in ev2 if x["arm"] == "off"]
        row = dict(A_MIN=amin, FRAC=frac, n_eng=len(e2), n_off=len(m2))
        for k, nm in (("ang_rms[wig]", "wiggle"), ("tq_rms[wig]", "ring"), ("dur", "dur")):
            row[nm] = stratified_ratio(e2, m2, k)[0]
        sens.append(row)
        print(f"      {amin:6.0f} {frac:6.2f} {len(e2):6d} {len(m2):6d} "
              f"{row['wiggle']:9.2f} {row['ring']:9.2f} {row['dur']:9.2f}")
    globals()["A_MIN"], globals()["FRAC"] = base
    res["sensitivity"] = sens

    print("\n=== RING-DOWN zeta ON THE ENGAGED RETURNS — with the mandatory STEP CONTROL ===")
    for r in routes:
        ev = [e for e in evs[r] if e["arm"] == "engaged"]
        if len(ev) < 5:
            continue
        rd = ringdown(Ds[r], ev, tag=f"r{r}/engaged")
        res["ringdown"][r] = rd
        print(f"   route {r}: f0 = {rd['f0_used']:.2f} Hz, {rd['n_events']} engaged returns")
        print(f"      {'half-width':>10s} {'n fit':>6s} {'tau DATA':>9s} {'tau STEP':>9s} "
              f"{'ratio':>7s} {'zeta':>7s} {'Q':>7s}  R2")
        for w in rd["per_width"]:
            print(f"      {w['half_width']:10.1f} {w['n_fit']:6d} "
                  f"{w['tau_data']:9.4f} {w['tau_step']:9.4f} "
                  f"{w.get('ratio_data_over_step', float('nan')):7.2f} "
                  f"{w.get('zeta_data', float('nan')):7.3f} {w.get('Q_data', float('nan')):7.1f}  "
                  f"{w['r2_med']:.3f}")

    print("\n=== DOES THE LKAS COMMAND ITSELF WIGGLE? (complex demodulation at each event's f_dom) ===")
    for r in routes:
        ev = [e for e in evs[r] if e["arm"] == "engaged"]
        cc = command_coupling(Ds[r], ev)
        res["command"][r] = cc
        if "note" in cc:
            print(f"   route {r}: {cc['note']} (n={cc['n']})")
            continue
        print(f"   route {r}: n={cc['n']} events, f0 med {cc['f0_med']:.2f} Hz")
        print(f"      |R| angle vs command  {cc['R']:.3f}   phase {cc['phase_deg']:+7.1f} deg  "
              f"(CAN join +-{cc['can_join_deg']:.0f} deg)")
        print(f"      shuffled-pair control  med {cc['shuffled_R_med']:.3f}  p95 "
              f"{cc['shuffled_R_p95']:.3f}   p = {cc['p_vs_shuffled']:.4f}   "
              f"random floor {cc['random_floor']:.3f}")
        print(f"      command band ratio  wiggle-band / 15-22 Hz control = "
              f"{cc['cmd_wig_over_ctrl']:.2f}")

    print("\n=== EXPOSURE / POWER — how many episodes does an informative CI need? ===")
    print("   subsample EPISODES, recompute the primary statistics, report the CI half-width")
    print(f"      {'n_ep eng':>9s} {'n_ep off':>9s} {'n eng':>6s} {'n off':>6s}  " +
          "  ".join(f"{k[:22]:>26s}" for k in ("ring_per_tq", "dur")))
    rng = np.random.default_rng(SEED + 7)
    eps_e = sorted({e["episode"] for e in E})
    eps_m = sorted({m["episode"] for m in M})
    power = []
    for ke in (3, 5, 7, 9, len(eps_e)):
        km = max(2, min(len(eps_m), int(round(ke * len(eps_m) / len(eps_e)))))
        if ke > len(eps_e):
            continue
        hw = {k: [] for k in ("ring_per_tq", "dur")}
        ns = []
        for _ in range(12):
            se = set(rng.choice(eps_e, ke, replace=False))
            sm = set(rng.choice(eps_m, km, replace=False))
            Es = [e for e in E if e["episode"] in se]
            Ms = [m for m in M if m["episode"] in sm]
            ns.append((len(Es), len(Ms)))
            for k in hw:
                _, ci, _, _ = boot_stratified(Es, Ms, k, nboot=1500, seed=int(rng.integers(1e6)))
                if np.all(np.isfinite(ci)) and ci[0] > 0:
                    hw[k].append(np.log(ci[1] / ci[0]) / 2)
        row = dict(n_ep_eng=ke, n_ep_off=km,
                   n_eng=int(np.median([a for a, b in ns])),
                   n_off=int(np.median([b for a, b in ns])))
        for k in hw:
            row[f"ci_halfwidth_log_{k}"] = float(np.median(hw[k])) if hw[k] else float("nan")
            row[f"ci_fold_{k}"] = float(np.exp(np.median(hw[k]))) if hw[k] else float("nan")
        power.append(row)
        print(f"      {ke:9d} {km:9d} {row['n_eng']:6d} {row['n_off']:6d}  " +
              "  ".join(f"+-{row[f'ci_fold_{k}']:5.2f}x (log {row[f'ci_halfwidth_log_{k}']:.2f})"
                        f"{'':>4s}" for k in ("ring_per_tq", "dur")))
    res["power"] = power

    print("\n=== ABSOLUTE MAGNITUDES — is the LKAS command's own wiggle even above its floor? ===")
    for arm, S in (("engaged", E), ("LKAS-off", M)):
        for k in ("cmd_rms[wig]", f"cmd_rms[{SPEC_DEN}]", "cmd_absmed"):
            v = np.array([e[k] for e in S], float)
            v = v[np.isfinite(v)]
            if len(v):
                print(f"   {arm:9s} {k:32s} med {np.median(v):9.2f} ct  p90 "
                      f"{np.percentile(v, 90):9.2f}")
    fd = {a: [e["f_dom_ang"] for e in (E if a == "engaged" else M)
              if np.isfinite(e["f_dom_ang"])] for a in ("engaged", "off")}
    for a, v in fd.items():
        if v:
            print(f"   dominant wiggle frequency, {a:8s}: median {np.median(v):5.2f} Hz  "
                  f"IQR [{np.percentile(v,25):.2f}, {np.percentile(v,75):.2f}]  n={len(v)}")
    res["f_dom"] = {a: dict(median=float(np.median(v)) if v else float("nan"), n=len(v))
                    for a, v in fd.items()}

    if do_plots:
        print("\n--- plots ---")
        w = plots(Ds, evs)
        res["plots"] = w
        print(f"   {len(w)} figures -> {PLOTD}")

    p = OUTD / "rtc_measure.json"
    p.write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {p}")
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args or ["7e", "7f"], do_plots="--no-plots" not in sys.argv)
