# -*- coding: utf-8 -*-
"""v293_symptom_instruments.py -- THE OPERATOR'S FOUR SYMPTOMS, as pre-registered instruments.

    "I did not experience any classic grinding or stuttering."
    "steering felt RATCHETY, like the wheel did not move smoothly but only SNAPPED BETWEEN ANGLES
     rather than smoothly moving between them"
    "Sometimes steering felt LOOSE and then sometimes there was OVERSTEER and other times on hard
     transients, it would OVERSHOOT THEN CORRECT slightly"
                                      -- route 70 (V293 rev 1), reported 2026-09-13 evening, verbatim

PURE FUNCTIONS ONLY.  No file I/O, no rlog reading, no globals but the frozen constants below.  Every
function takes numpy arrays already resampled onto ONE 100 Hz grid with previous-value (ZOH) semantics
and returns a plain dict, so `v293_flight_read.py` can run the SAME code on this drive and on every
cached reference route and the comparison cannot drift.  🛑 That is the point of this file existing:
the reference numbers in section 7 are RE-DERIVED at run time by this code, never copied from
`V293-PLANT-IDENT-2026-09-13.md`.

PROVENANCE.  Every definition is ported from the identification subagent's scripts, named per function:
  ratchet          v293_ident_k.py  (dwells, the smoothed detector, the threshold sweep)
  concentration    v293_ident_h2.py (the scale-free, activity-matched "snappiness" measure)
  wander           v293_ident_i.py  I2
  stiffness        v293_ident_i.py  I2
  turn hold        v293_ident_i.py  I3
  tracking gain    v293_ident_c.py  C1
  step overshoot   v293_ident_i.py  I4
  prominence       v293_ident_i2.py (the SHOULDER-FITTED baseline; the flat-baseline version is a
                                     documented artefact that returns 16-21 dB on every route)
  pid shares       v293_ident_c.py  C2
  straight deliver v293_ident_c.py  C4

🛑 TWO INSTRUMENT FACTS, settled by the identification and binding here:
  * The 0x14A ANGLE quantises at 0.1 deg, so ANY angle-based smoothness measure reads 1.000 below
    about 10 deg/s whatever the plant does.  Every rate statistic below is read from the 0x18F RATE
    field (0.125 deg/s LSB).  The angle is used only for snap amplitude and wander, where 0.1 deg is
    fine.
  * The 0x18F DRIVER-TORQUE BAR CANNOT stand in for `steeringPressed` on this car -- it reads EPS
    twist.  At |bar| < 800 it catches 98.2 % of hands-off frames and 0.1 % of hands-on ones.  So the
    cross-route stratum is ALL LATERALLY ENGAGED on every route, with a hands-off stratum reported
    beside it only where `steeringPressed` exists.

ANALYSIS ONLY.  Nothing here flashes, sends or builds anything.
"""
import numpy as np
from scipy import signal

FS = 100.0
DT = 1.0 / FS
CPD = 8.0                     # raw 0x18F counts per deg/s
STEER_MAX = 4096.0            # 0xE4 counts at openpilot torque 1.0 (opendbc honda interface.py)

# the speed bands the operator's symptoms are scored in -- the scorer's own SPEED_BANDS
SYMPTOM_BANDS = ((0.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 99.0))
SBNAME = ("0-5", "5-10", "10-20", ">20")
# the identification's bands.  ⚠ DIFFERENT, and deliberately kept: the tracking-gain reference
# (0.884 / 1.020 / 1.123) exists only on this grid, so scoring it on the other one would have no
# reference at all.  Every table below says which grid it is on.
IDENT_BANDS = ((0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0))
IBNAME = ("<8", "8-15", "15-22", ">22")

# --- frozen calibration constants ------------------------------------------------------------------
# The concentration measure bins windows by their OWN rms wheel rate, because route 70's rms rate is
# 2-3x the references' in the same speed band (roundabouts) and a raw comparison is not like-for-like.
# v293_ident_h2.py took the bin edges from the percentiles of the POOLED four-route window set, which
# makes the edges depend on which routes are in the run.  🛑 FROZEN HERE so the instrument is
# per-route and cacheable: these are the 25/50/75/90th percentiles of the 4648 windows pooled over
# r70_v293 + r6c + r39 + r35, recomputed 2026-09-13 and reproducible with `conc_edges_from_pool`.
CONC_EDGES = (0.0, 1.357833, 2.194506, 3.964775, 10.099284, 1e9)
CONC_LABELS = ("q0-25", "q25-50", "q50-75", "q75-90", "q90+")
CONC_NPER, CONC_STEP = 400, 100                 # 4 s windows, 1 s hop
CONC_MIN_WIN = 8                                # a bin under this many windows is not reported

DWELL_THS = (0.25, 0.50, 1.00, 2.00)            # deg/s
DWELL_SMOOTH = 10                               # frames: the 0.10 s moving mean
DWELL_MIN = 20                                  # frames: >= 0.20 s below threshold
DWELL_RUN = 200                                 # frames: the stratum run must be >= 2 s


# ======================================================================================================
# helpers
# ======================================================================================================
def runs_of(mask, minlen):
    """contiguous True runs of at least `minlen` frames."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def band_masks(v, mask, bands=SYMPTOM_BANDS):
    return [mask & (v >= lo) & (v < hi) for lo, hi in bands]


def _lstsq(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float)
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    yh = X @ b
    ss = np.sum((y - y.mean()) ** 2)
    return b, (float(1.0 - np.sum((y - yh) ** 2) / ss) if ss > 0 else np.nan)


def _p(a, q):
    a = np.asarray(a, float)
    return float(np.percentile(a, q)) if len(a) else float("nan")


# ======================================================================================================
# 1.  RATCHET -- "snapped between angles rather than smoothly moving between them"
# ======================================================================================================
def dwells(rate_dps, ang, v, mask, ths=DWELL_THS, bands=SYMPTOM_BANDS, names=SBNAME):
    """DWELLS PER MINUTE -- the decisive ratchet statistic (v293_ident_k.py K1b/H2).

    dwell = the 0.10 s MOVING MEAN of |wheel rate| below a threshold for >= 0.20 s, inside a run of
    the stratum at least 2 s long.  snap = the ANGLE CHANGE from the end of one dwell to the start of
    the next.  Reported per minute of that stratum's own time, at four thresholds.

    🛑 THE SMOOTHING IS NOT COSMETIC.  A hard threshold on the raw 100 Hz rate field is crossed by
    noise every few frames: it finds 13 dwells on r70 and ZERO on r6c, which is a property of the
    detector, not of the car.  The smoothed detector is applied identically to every route.
    """
    rate_dps = np.asarray(rate_dps, float)
    ker = np.ones(DWELL_SMOOTH) / float(DWELL_SMOOTH)
    out = {}
    for nm, m in zip(names, band_masks(v, mask, bands)):
        segs = runs_of(m, DWELL_RUN)
        tot = sum(b - a for a, b in segs)
        if tot < 500:                                   # under 5 s: not a stratum
            out[nm] = dict(sec=tot * DT, n=0, scored=False)
            continue
        sweep, dl, sn = {}, [], []
        for th in ths:
            n = 0
            for a, b in segs:
                rs = np.convolve(np.abs(rate_dps[a:b]), ker, "same")
                dws = runs_of(rs < th, DWELL_MIN)
                n += len(dws)
                if th != 0.50:
                    continue
                for q in range(len(dws)):
                    i0, j0 = dws[q]
                    dl.append((j0 - i0) * DT)
                    if q + 1 < len(dws) and dws[q + 1][0] > j0:
                        i1 = dws[q + 1][0]
                        sn.append(abs(ang[a:b][i1] - ang[a:b][j0 - 1]))
            sweep["%.2f" % th] = 60.0 * n / (tot * DT)
        out[nm] = dict(sec=tot * DT, scored=True, n=len(dl), sweep=sweep,
                       per_min_025=sweep["0.25"], per_min_050=sweep["0.50"],
                       dwell_p50=_p(dl, 50), dwell_p90=_p(dl, 90),
                       snap_p50=_p(sn, 50), snap_p90=_p(sn, 90))
    return out


def conc_mag(a, frac=0.10):
    """fraction of the total of |a| carried by the largest `frac` of frames.  Read on the RATE itself,
    so it is NOT limited by the 0.1 deg angle quantiser (v293_ident_h2.py `conc_mag`)."""
    a = np.abs(np.asarray(a, float))
    tot = a.sum()
    if tot <= 0 or len(a) < 20:
        return float("nan")
    k = max(1, int(round(frac * len(a))))
    return float(np.sort(a)[-k:].sum() / tot)


def concentration(x, frac=0.10):
    """the same, on the INCREMENTS of a signal (used for the 0xE4 command channel)."""
    a = np.abs(np.diff(np.asarray(x, float)))
    tot = a.sum()
    if tot <= 0 or len(a) < 20:
        return float("nan")
    k = max(1, int(round(frac * len(a))))
    return float(np.sort(a)[-k:].sum() / tot)


def conc_calibration(seed=7):
    """RE-DERIVE the scale of the concentration measure instead of asserting it: a pure sine, 0-2 Hz
    band-limited noise and a 10-step staircase, at this window length and sample rate.  Printed on the
    scorecard so the reader can see what 0.33 and 0.47 mean."""
    t = np.arange(CONC_NPER) * DT
    rng = np.random.default_rng(seed)
    bl = signal.sosfiltfilt(signal.butter(4, 2.0, "lowpass", fs=FS, output="sos"),
                            rng.standard_normal(CONC_NPER))
    stair = np.repeat(np.arange(10, dtype=float), CONC_NPER // 10)[:CONC_NPER]
    return dict(sine=conc_mag(np.diff(np.sin(2 * np.pi * 1.0 * t))),
                noise=conc_mag(np.diff(bl)), staircase=conc_mag(np.diff(stair)))


def conc_edges_from_pool(rms_pool):
    """the provenance of CONC_EDGES: the 25/50/75/90th percentiles of a pooled window set."""
    return (0.0,) + tuple(float(np.percentile(rms_pool, q)) for q in (25, 50, 75, 90)) + (1e9,)


def rate_concentration(rate_dps, cmd, v, mask, edges=CONC_EDGES, bands=SYMPTOM_BANDS):
    """THE SCALE-FREE RATCHET MEASURE (v293_ident_h2.py H8/H9).

    "Of all the wheel travel in a 4 s window, what fraction is delivered in the fastest 10 % of its
    frames?"  Windows are binned by their OWN rms wheel rate so the comparison is between windows
    doing the same amount of steering.  The q75-90 bin is the headline: it is where the V293-vs-V282
    gap was widest (0.468 against 0.325-0.351).

    The same measure on the 0xE4 COMMAND is the control that says whether the snappiness is INHERITED
    from openpilot or GENERATED by the car.  On r70 the command got *smoother* while the wheel got
    snappier, which is what makes the car the culprit.
    """
    W = []
    for m in band_masks(v, mask, bands):
        for a, b in runs_of(m, CONC_NPER):
            for s0 in range(a, b - CONC_NPER + 1, CONC_STEP):
                sl = slice(s0, s0 + CONC_NPER)
                W.append((float(np.sqrt(np.mean(rate_dps[sl] ** 2))),
                          conc_mag(rate_dps[sl]), concentration(cmd[sl])))
    out = dict(n_win=len(W), rate={}, cmd={})
    A = np.asarray(W, float) if W else np.zeros((0, 3))
    for i, lab in enumerate(CONC_LABELS):
        sel = (A[:, 0] >= edges[i]) & (A[:, 0] < edges[i + 1]) if len(A) else np.zeros(0, bool)
        r = A[sel, 1]; c = A[sel, 2]
        r = r[np.isfinite(r)]; c = c[np.isfinite(c)]
        out["rate"][lab] = dict(n=int(len(r)),
                                med=(float(np.median(r)) if len(r) >= CONC_MIN_WIN else None))
        out["cmd"][lab] = dict(n=int(len(c)),
                               med=(float(np.median(c)) if len(c) >= CONC_MIN_WIN else None))
    return out


# ======================================================================================================
# 2.  LOOSE -- "sometimes steering felt loose"
# ======================================================================================================
def angle_wander(ang, rate_dps, v, mask, bands=SYMPTOM_BANDS, names=SBNAME):
    """rms of the 0.1-1 Hz band-passed steering angle on straight-ish stretches (v293_ident_i.py I2).

    "Straight-ish" is defined from CAN alone -- |angle| < 5 deg and |rate| < 5 deg/s -- because the
    reference routes carry no control path in the v280 cache.  A weaker definition than the demand-
    based one, but LIKE-FOR-LIKE across every route, which is what a reference has to be.
    ⚠ This was a NULL on r70 (0.137-0.229 deg against r6c's 0.207-0.209): "loose" is NOT excess
    wander.  It is reported, not gated.
    """
    sos = signal.butter(4, [0.1, 1.0], btype="bandpass", fs=FS, output="sos")
    base = mask & (np.abs(ang) < 5) & (np.abs(rate_dps) < 5)
    out = {}
    for nm, m in zip(names, band_masks(v, base, bands)):
        segs = runs_of(m, int(5 * FS))
        if not segs:
            out[nm] = dict(sec=float(m.sum()) * DT, rms=None)
            continue
        vals = [float(np.std(signal.sosfiltfilt(sos, ang[a:b]))) for a, b in segs]
        w = [b - a for a, b in segs]
        out[nm] = dict(sec=sum(w) * DT, n_run=len(segs), rms=float(np.average(vals, weights=w)))
    return out


def loop_stiffness(cmd, ang, la_des, la_act, op_torque, v, mask,
                   bands=SYMPTOM_BANDS, names=SBNAME):
    """THE OUTER LOOP'S STIFFNESS, in openpilot torque units per degree of angle (v293_ident_i.py I2).

    On straights, how much command does the loop put up per degree the wheel is off?  Read as the
    slope of the 0xE4 command on the negated angle over straight runs >= 5 s, divided by STEER_MAX.
    Compare it with the PLANT's own return spring (0.0023 / ~0.006 / 0.0115 / 0.0154 torque per deg,
    identification F1/D1): a loop barely stiffer than the spring cannot hold the wheel against it, and
    on a straight the feedforward is nearly zero, so almost nothing else is.  THAT is "loose".

    🛑 The demand's derivative is a 0.30 s BACKWARD DIFFERENCE, not `np.gradient`: gradient of a 100 Hz
    demand fragments every mask into sub-0.1 s pieces (measured: 49.9 s of turn-hold at 10-20 m/s
    containing ZERO runs >= 1.5 s).  Same quantity, 30x less variance.
    """
    W3 = 30
    dD = np.zeros(len(la_des))
    dD[W3:] = (la_des[W3:] - la_des[:-W3]) / (W3 * DT)
    straight = mask & (np.abs(la_des) < 0.3) & (np.abs(dD) < 0.3)
    err = la_des - la_act
    u = -np.asarray(op_torque, float)             # openpilot torque in the actualLateralAccel frame
    out = {}
    for nm, m in zip(names, band_masks(v, straight, bands)):
        segs = runs_of(m, int(5 * FS))
        if not segs or m.sum() < 500:
            out[nm] = dict(sec=float(m.sum()) * DT, n_run=len(segs), tq_per_deg=None)
            continue
        A = np.concatenate([cmd[a:b] for a, b in segs])
        B = np.concatenate([-ang[a:b] for a, b in segs])
        E = np.concatenate([err[a:b] for a, b in segs])
        U = np.concatenate([u[a:b] for a, b in segs])
        b1, r1 = _lstsq(np.vstack([B, np.ones(len(B))]).T, A)
        b2, r2_ = _lstsq(np.vstack([E, np.ones(len(E))]).T, U)
        out[nm] = dict(sec=len(A) * DT, n_run=len(segs), cnt_per_deg=float(b1[0]),
                       tq_per_deg=float(b1[0]) / STEER_MAX, r2_deg=r1,
                       tq_per_ms2=float(b2[0]), r2_ms2=r2_,
                       err_rms=float(np.sqrt(np.mean(E ** 2))))
    return out


# the plant's own return spring, in the same unit, from the identification's JOINT fit (F1 / D1).
# ⚠ BELIEF that it transfers to the next drive: it was fitted on r70, and the fork config changes on
# the next drive do not move the car.  The firmware does not change, so the spring should not either.
PLANT_SPRING_TQ_PER_DEG = {"0-5": 0.00228, "5-10": 0.0060, "10-20": 0.01149, ">20": 0.01539}


# ======================================================================================================
# 3.  OVERSTEER -- "sometimes there was oversteer"
# ======================================================================================================
def turn_hold(la_des, la_act, v, mask, bands=SYMPTOM_BANDS, names=SBNAME):
    """OVER-DELIVERY IN QUASI-STEADY TURNS (v293_ident_i.py I3 / report G3).

    turn hold = |desiredLateralAccel| > 0.5 with |dD/dt| < 0.3, runs >= 1.5 s.  The statistic is
    mean|actual| / mean|desired| per run, median over runs.  Above 1 the car turns MORE than the
    planner asked.  r70 read 0.937 at 10-20 m/s and 1.093 at >20 -- the same over-command the
    identification found in the feedforward (x1.9-2.1 above 15 m/s, section F4).
    """
    W3 = 30
    dD = np.zeros(len(la_des))
    dD[W3:] = (la_des[W3:] - la_des[:-W3]) / (W3 * DT)
    hold = mask & (np.abs(la_des) > 0.5) & (np.abs(dD) < 0.3)
    out = {"bands": {}, "demand": {}}
    for nm, m in zip(names, band_masks(v, hold, bands)):
        segs = runs_of(m, int(1.5 * FS))
        if len(segs) < 4:
            out["bands"][nm] = dict(sec=float(m.sum()) * DT, n_run=len(segs), ratio=None)
            continue
        ad = [float(np.mean(np.abs(la_act[a:b])) / max(np.mean(np.abs(la_des[a:b])), 1e-6))
              for a, b in segs]
        out["bands"][nm] = dict(sec=sum(b - a for a, b in segs) * DT, n_run=len(segs),
                                ratio=float(np.median(ad)))
    for lo, hi in ((0.5, 0.8), (0.8, 1.2), (1.2, 1.8), (1.8, 9.0)):
        m = mask & (np.abs(la_des) >= lo) & (np.abs(la_des) < hi) & (np.abs(dD) < 0.3)
        segs = runs_of(m, int(1.5 * FS))
        lab = "%.1f-%.1f" % (lo, hi)
        if len(segs) < 4:
            out["demand"][lab] = dict(n_run=len(segs), ratio=None)
            continue
        ad = [float(np.mean(np.abs(la_act[a:b])) / max(np.mean(np.abs(la_des[a:b])), 1e-6))
              for a, b in segs]
        out["demand"][lab] = dict(n_run=len(segs), ratio=float(np.median(ad)),
                                  sec=sum(b - a for a, b in segs) * DT)
    return out


def tracking_gain(la_des, la_act, v, mask, bands=IDENT_BANDS, names=IBNAME):
    """THE GAIN OF ACTUAL ON DESIRED (v293_ident_c.py C1 / report C1).

    Slope of `actualLateralAccel` on `desiredLateralAccel`, both low-passed at 0.5 Hz, over engaged
    runs >= 10 s, per speed band.  On r70 it rose monotonically 0.884 -> 1.020 -> 1.123 with speed:
    UNDER-turning below 15 m/s, OVER-turning above 22.  That is the feedforward's missing speed law
    showing up directly in the closed loop, and it is the cleanest single number a feedforward fix has
    to flatten.  🛑 ON THE IDENTIFICATION'S BAND GRID, not the scorer's -- that is where the reference
    lives.
    """
    sos = signal.butter(4, 0.5, "lowpass", fs=FS, output="sos")
    out = {}
    for nm, m in zip(names, band_masks(v, mask, bands)):
        segs = runs_of(m, int(10 * FS))
        if not segs:
            out[nm] = dict(sec=float(m.sum()) * DT, n_run=0, slope=None)
            continue
        X = np.concatenate([signal.sosfiltfilt(sos, la_des[a:b]) for a, b in segs])
        Y = np.concatenate([signal.sosfiltfilt(sos, la_act[a:b]) for a, b in segs])
        b, r2_ = _lstsq(np.vstack([X, np.ones(len(X))]).T, Y)
        out[nm] = dict(sec=len(X) * DT, n_run=len(segs), slope=float(b[0]),
                       intercept=float(b[1]), r2=r2_)
    return out


# ======================================================================================================
# 4.  OVERSHOOT-THEN-CORRECT -- "on hard transients it would overshoot then correct slightly"
# ======================================================================================================
def step_overshoot(la_des, la_act, i_term, v, mask, bands=SYMPTOM_BANDS, names=SBNAME):
    """THE STEP RESPONSE (v293_ident_i.py I4 / report G4).

    A step is |la_des(t) - la_des(t-0.5 s)| >= 0.30 m/s^2 on a hands-off frame, at least 2.5 s from
    the last one, with |dD/dt| <= 1.2 over the next 1.2 s and the stratum held for 2.0 s.  Then
    overshoot = (peak|actual| - |final desired|)/|final desired| over the following 2 s.

    THE DISCRIMINATOR, carried with it: regress the ABSOLUTE overshoot on the step size.  A linear
    under-damped loop gives a positive slope and ~0 intercept; a stiction release or a fixed
    feedforward offset gives slope ~ 0 and a positive intercept.  r70 measured slope -0.456,
    intercept +0.571, R2 0.027 -- i.e. a roughly FIXED ~0.4-0.5 m/s^2 excursion that does not scale,
    which RULES OUT an under-damped linear loop.  Correlation with the integrator at the peak is
    +0.172, too weak for wind-up.
    """
    n = len(la_des)
    w6 = int(0.5 * FS)
    dstep = np.zeros(n)
    dstep[w6:] = la_des[w6:] - la_des[:-w6]
    W3 = 30
    dD = np.zeros(n)
    dD[W3:] = (la_des[W3:] - la_des[:-W3]) / (W3 * DT)
    rows, last = [], -10 ** 9
    for i in np.flatnonzero((np.abs(dstep) >= 0.30) & mask):
        if i - last < int(2.5 * FS) or i + int(2.5 * FS) >= n:
            continue
        if np.max(np.abs(dD[i:i + int(1.2 * FS)])) > 1.2:
            continue
        if not mask[i:i + int(2.0 * FS)].all():
            continue
        last = i
        post = slice(i, i + int(2.0 * FS))
        Dfin = float(np.median(la_des[i + int(0.8 * FS):i + int(1.5 * FS)]))
        if abs(Dfin) < 0.25:
            continue
        a_ = la_act[post] * np.sign(Dfin)
        pk = float(np.max(a_))
        tpk = float(np.argmax(a_) * DT)
        it_ = i + int(tpk * FS)
        rows.append(dict(v=float(v[i]), step=float(abs(dstep[i])), Dfin=abs(Dfin),
                         ov=(pk - abs(Dfin)) / abs(Dfin), ov_abs=pk - abs(Dfin), tpk=tpk,
                         i_term=(float(abs(i_term[it_])) if it_ < n and np.isfinite(i_term[it_])
                                 else float("nan"))))
    out = {"n": len(rows), "bands": {}}
    for nm, (lo, hi) in zip(names, bands):
        Q = [r for r in rows if lo <= r["v"] < hi]
        if len(Q) < 3:
            out["bands"][nm] = dict(n=len(Q), ov=None)
            continue
        out["bands"][nm] = dict(n=len(Q), step_p50=_p([q["step"] for q in Q], 50),
                                ov=_p([q["ov"] for q in Q], 50),
                                ov_abs=_p([q["ov_abs"] for q in Q], 50),
                                tpk=_p([q["tpk"] for q in Q], 50))
    if len(rows) >= 5:
        st = np.array([r["step"] for r in rows]); ab = np.array([r["ov_abs"] for r in rows])
        b, r2_ = _lstsq(np.vstack([st, np.ones(len(st))]).T, ab)
        it_ = np.array([r["i_term"] for r in rows]); ov = np.array([r["ov"] for r in rows])
        ok = np.isfinite(it_) & np.isfinite(ov)
        out["discriminator"] = dict(slope=float(b[0]), intercept=float(b[1]), r2=r2_, n=len(rows),
                                    corr_i=(float(np.corrcoef(it_[ok], ov[ok])[0, 1])
                                            if ok.sum() > 3 else None))
    return out


# ======================================================================================================
# 5.  THE REPORT ROWS
# ======================================================================================================
def prominence_1_4(ang, cmd, rate_dps, v, mask, bands=SYMPTOM_BANDS, names=SBNAME):
    """IS THE 1-4 Hz OBJECT A LINE?  (v293_ident_i2.py; the SHOULDER-FITTED estimator.)

    Prominence = the 1-4 Hz peak above a straight line fitted IN LOG-LOG to the 0.6-0.9 Hz and
    4-7 Hz shoulders.  🛑 A FLAT baseline over 0.5-8 Hz scores the steering spectrum's own 1/f slope
    as a peak and returns 16-21 dB on EVERY route; that estimator is wrong and is not used here.
    Under about 3 dB there is no line, only the tail of the road spectrum.

    The rate channel is carried beside it because the 0.1 deg angle quantiser cannot reach the band at
    low speed; on r70 the 1-4 Hz RATE content was 4.8x to 11.6x every reference in every band, which
    is the strongest form of this finding.
    """
    out = {}
    for nm, m in zip(names, band_masks(v, mask, bands)):
        segs = runs_of(m, 512)
        if not segs:
            out[nm] = dict(sec=float(m.sum()) * DT, prom=None)
            continue
        Pa = Pc = Pr = None
        nn = 0
        for a, b in segs:
            f_, p1 = signal.welch(signal.detrend(ang[a:b]), fs=FS, nperseg=512, noverlap=256)
            _, p2 = signal.welch(signal.detrend(cmd[a:b]), fs=FS, nperseg=512, noverlap=256)
            _, p3 = signal.welch(signal.detrend(rate_dps[a:b]), fs=FS, nperseg=512, noverlap=256)
            w = b - a
            Pa = p1 * w if Pa is None else Pa + p1 * w
            Pc = p2 * w if Pc is None else Pc + p2 * w
            Pr = p3 * w if Pr is None else Pr + p3 * w
            nn += w
        Pa, Pc, Pr = Pa / nn, Pc / nn, Pr / nn
        sel = (f_ >= 1.0) & (f_ < 4.0)
        sh = ((f_ >= 0.6) & (f_ <= 0.9)) | ((f_ >= 4.0) & (f_ <= 7.0))
        A_ = np.vstack([np.log10(f_[sh]), np.ones(int(sh.sum()))]).T
        cf = np.linalg.lstsq(A_, 10 * np.log10(Pa[sh] + 1e-30), rcond=None)[0]
        fpk = float(f_[sel][int(np.argmax(Pa[sel]))])
        df = f_[1] - f_[0]
        out[nm] = dict(sec=nn * DT, n_run=len(segs), f_peak=fpk,
                       prom=float(10 * np.log10(Pa[sel].max() + 1e-30)
                                  - (cf[0] * np.log10(fpk) + cf[1])),
                       ang=float(np.sqrt(np.sum(Pa[sel]) * df)),
                       cmd=float(np.sqrt(np.sum(Pc[sel]) * df)),
                       rate=float(np.sqrt(np.sum(Pr[sel]) * df)))
    return out


def pid_shares(f, p, i, v, mask, bands=IDENT_BANDS, names=IBNAME):
    """WHERE THE COMMANDED TORQUE COMES FROM (v293_ident_c.py C2).

    Shares of |f| / |p| / |i| in |f|+|p|+|i|, per band.  The integrator carried 0.35-0.38 of the
    command everywhere on r70, with |i| > 0.4 for 55.7 s: a feedforward that is persistently wrong,
    not noise.  A correct feedforward should drive this a long way down, and that is the cleanest
    non-symptom read of whether a feedforward change worked.  🛑 ON THE IDENTIFICATION'S BAND GRID.
    """
    out = {}
    for nm, m in zip(names, band_masks(v, mask, bands)):
        s = m & np.isfinite(f) & np.isfinite(p) & np.isfinite(i)
        if s.sum() < 500:
            out[nm] = dict(sec=float(s.sum()) * DT, i=None)
            continue
        tot = np.abs(f[s]) + np.abs(p[s]) + np.abs(i[s])
        ok = tot > 1e-6
        out[nm] = dict(sec=float(s.sum()) * DT,
                       f=float(np.mean(np.abs(f[s][ok]) / tot[ok])),
                       p=float(np.mean(np.abs(p[s][ok]) / tot[ok])),
                       i=float(np.mean(np.abs(i[s][ok]) / tot[ok])),
                       abs_i_p50=float(np.percentile(np.abs(i[s]), 50)))
    return out


def regime_delivery(la_des, la_act, v, mask):
    """THE REGIME BREAKDOWN (v293_ident_c.py C4), demand-defined.

    ⚠ `dD/dt` here is `np.gradient`, NOT the 0.3 s backward difference the other instruments use --
    that is what C4 used and what the 80.0 % straight-line reference was measured with.  The two are
    not interchangeable and the difference is stated rather than silently reconciled.

    "deliver" is mean|actual| / mean|desired|.  On r70: straights 80.0 % (UNDER, the friction error),
    turn hold 107.4 % and exit 113.2 % (OVER, the lat-accel-model error).  One scalar cannot fix both,
    which is the whole argument for changing the feedforward's SHAPE.
    """
    dD = np.gradient(la_des, DT)
    sgn = np.sign(la_des)
    REG = {"straight": mask & (np.abs(la_des) < 0.3) & (np.abs(dD) < 0.3),
           "turn entry": mask & (dD * sgn > 0.5) & (np.abs(la_des) > 0.3),
           "turn hold": mask & (np.abs(la_des) > 0.8) & (np.abs(dD) < 0.3),
           "turn exit": mask & (dD * sgn < -0.5) & (np.abs(la_des) > 0.3),
           "low-speed manoeuvre": mask & (v < 8) & (np.abs(la_des) > 1.0)}
    out = {}
    for nm, s in REG.items():
        if s.sum() < 200:
            out[nm] = dict(sec=float(s.sum()) * DT, deliver=None)
            continue
        out[nm] = dict(sec=float(s.sum()) * DT,
                       deliver=float(np.mean(np.abs(la_act[s]))
                                     / max(np.mean(np.abs(la_des[s])), 1e-9)),
                       signed_bias=float(np.mean((la_des[s] - la_act[s]) * sgn[s])),
                       rms_err=float(np.sqrt(np.mean((la_des[s] - la_act[s]) ** 2))))
    return out


# ======================================================================================================
# 6.  THE BRANCH IDENTITY -- which feedforward arm actually executed
# ======================================================================================================
def laf_identity(p, i, f, out, active):
    """🛑 THE SECOND EXACT 100 Hz ATTRIBUTION IDENTITY, and the one that works in BOTH ARMS.

        output_torque   = output_lataccel / latAccelFactor
        output_lataccel = f + p + i + d,   and d is structurally 0 on this car
        torqueState.output = -output_torque

    so  -(p + i + f) / output == SteerLatAccel  on every active frame, exactly, whichever
    feedforward arm ran -- because `pid_log.f = pid.f` in each of them.  That makes it a wire read
    of the authority scalar that survives a mid-route toggle change, exactly as the Kp read does for
    SteerKP, and it is the only gate on `SteerLatAccel` that is not just a params-store echo.

    VERIFIED by the adversarial pass on r70_v293: median 6.0000, IQR [6.0000, 6.0000], 99.2 % of
    active frames within 1 %.  [EVIDENCE]

    Frames with a near-zero `output` are excluded: the ratio is 0/0 there and its noise would swamp
    the median.  The guard is on the DENOMINATOR only, so it cannot bias the estimate.
    """
    act = (np.asarray(active, float) > 0.5)
    o = np.asarray(out, float)
    s = act & np.isfinite(p) & np.isfinite(i) & np.isfinite(f) & np.isfinite(o) & (np.abs(o) >= 1e-3)
    d = dict(n_active=int(act.sum()), n=int(s.sum()))
    if s.sum() < 200:
        d.update(laf=None)
        return d
    r = -(np.asarray(p)[s] + np.asarray(i)[s] + np.asarray(f)[s]) / o[s]
    med = float(np.median(r))
    d.update(laf=med, iqr=[float(np.percentile(r, 25)), float(np.percentile(r, 75))],
             within1=float(np.mean(np.abs(r - med) <= 0.01 * abs(med))) if med else None,
             within5=float(np.mean(np.abs(r - med) <= 0.05 * abs(med))) if med else None)
    return d


def branch_identity(f, sp_ff, la_des, des_curv, vego, roll, active):
    """🛑 THE REPLACEMENT FOR THE BROKEN `f/desiredLateralAccel` GATE.

    WHY THE OLD GATE WAS WRONG.  It asserted "friction 0 => f = desiredLateralAccel exactly".  It
    cannot be.  The fork sets

        pid_log.desiredLateralAccel = setpoint = expected_lateral_accel + jerk * lat_delay
        pid_log.f                   = ff       = D_future - roll*9.81*fade - latAccelOffset*fade

    with `D_future = desiredCurvature * vEgo**2`.  Two DIFFERENT quantities -- one is the 0.30 s
    DELAYED reference plus a jerk lead, the other is the CURRENT command minus a constant.  So

        f / D = 1 - c/|D|   BY CONSTRUCTION,

    and the whole 0.56 -> 0.87 ramp the old gate reported across |D| bins is that one constant c,
    measured at +0.343 m/s^2 on r70.  A ratio that rises with magnitude is the signature of an
    ADDITIVE offset; a branch change would be MULTIPLICATIVE and would show a flat ratio.  The gate
    was measuring a stale learned offset and calling it a mis-attribution.

    WHAT REPLACES IT -- two independent reads, neither of which uses the delayed setpoint:

    (a) `torqueState.f` vs `starpilotLateralState.feedforward`, both published in the same
        `Controls.publish` call so they align index-for-index.  In the else-arm (rate-plant FF OFF)
        they are the same number.  With the plant-FF branch live, `f` becomes
        `latAccelFactor * (plant_ff_torque + friction_torque)` and they part company.  The statistic
        is the median |f - feedforward|, normalised by the median |f| so it does not depend on how
        hard the drive was steering.

    (b) THE f-SLOPE.  Regress f on `desiredCurvature * vEgo**2` (and, when roll is available, on the
        roll term too).  In the else-arm the coefficient on D_future is EXACTLY 1.000 and the
        intercept is -(latAccelOffset * fade); under the plant-FF branch f is a spring term in the
        ANGLE domain scaled by LAF and has no such identity.  The intercept is the EFFECTIVE learned
        offset that actually entered the feedforward -- which is the number the
        `KeepLearnedLatAccelOffset` gate needs, NOT the published `latAccelOffsetFiltered` (torqued
        publishes that whatever the toggle says; the toggle decides whether controlsd TAKES it).
    """
    act = (np.asarray(active, float) > 0.5)
    D_fut = np.asarray(des_curv, float) * np.asarray(vego, float) ** 2
    fade = np.interp(np.asarray(vego, float), [0.5, 2.5], [0.0, 1.0])
    out = dict(n_active=int(act.sum()))

    s = act & np.isfinite(f) & np.isfinite(sp_ff)
    if s.sum() >= 200:
        d = np.abs(f[s] - sp_ff[s])
        lvl = float(np.median(np.abs(f[s])))
        out.update(n_ff=int(s.sum()), d_ff_p50=float(np.median(d)),
                   d_ff_p90=float(np.percentile(d, 90)), f_level=lvl,
                   d_ff_rel=(float(np.median(d)) / lvl if lvl > 1e-9 else float("nan")),
                   sp_ff_level=float(np.median(np.abs(sp_ff[s]))))
    else:
        out.update(n_ff=int(s.sum()), d_ff_p50=None, d_ff_rel=None)

    s2 = act & np.isfinite(f) & np.isfinite(D_fut)
    if s2.sum() >= 200:
        b, r2_ = _lstsq(np.vstack([D_fut[s2], np.ones(int(s2.sum()))]).T, f[s2])
        out.update(n_fit=int(s2.sum()), slope=float(b[0]), intercept=float(b[1]), r2=r2_,
                   offset_p50=float(np.median(D_fut[s2] - f[s2])))
        r = np.asarray(roll, float)
        s3 = s2 & np.isfinite(r)
        if s3.sum() >= 200 and np.nanstd(r[s3]) > 1e-6:
            X = np.vstack([D_fut[s3], r[s3] * fade[s3], fade[s3]]).T
            b3, r2b = _lstsq(X, f[s3])
            out.update(slope_roll=float(b3[0]), coef_roll=float(b3[1]),
                       offset_roll=float(-b3[2]), r2_roll=r2b, n_roll=int(s3.sum()))
        # the old, broken statistic -- printed so the change is visible, never gated on
        s4 = s2 & (np.abs(la_des) >= 0.3)
        if s4.sum() >= 50:
            out["fD_p50_OLD"] = float(np.median(f[s4] / la_des[s4]))
    return out
