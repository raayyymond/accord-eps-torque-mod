"""instr_common.py  -- shared conventions for the three missing instruments.  STREAM TAG: instr

WHY THIS FILE EXISTS
  The kit already scores band-passed in-band GAIN (rev64_03_goal.py / rev64_05_bandfix.py).  Three of
  the operator's five notes have no instrument at all.  The three new instruments MUST compose with the
  band metric, so every convention below is COPIED from those two scripts rather than re-invented:

    grid          the controlsState timestamp vector t_cs (~100.5 Hz, non-uniform); every carState /
                  liveParameters signal is np.interp'd onto it.  FS = 1/median(diff(t_cs)).
    engaged mask  cs_active & ~steeringPressed  (+ the speed bin).   NOT latActive-only: hands-on
                  frames are excluded because the operator's hand is a damper (handoff 2026-09-16 S2).
    runs          contiguous spans of the mask, broken when a sample gap exceeds 4/FS, then a
                  minimum-length filter.  Statistics are pooled ACROSS runs, never across a break.
    speed bins    the notes split at 15 m/s (notes 3/4/5 below, note 2 above); the finer bins here
                  are a superset so the two can be cross-read.

LANE CENTRING  (operator requirement: any model must account for lane centring being ON)
  EVIDENCE, route 76 initData: LaneCentering='1', LaneCenterOffset='0.0',
  LaneCenteringE2EAuthority='0.2', LaneCenteringPauseOnSignal='1'.
  The lane-centring stage runs in controlsd.py BEFORE controlsState is published
  (controlsd.py:766 `new_desired_curvature = self.lane_centering.update(...)`), so cs_des_curv /
  cs_la_des ALREADY CONTAIN it.  Every "desired" quantity in these instruments is therefore the
  post-lane-centring demand.  Nothing needs to be added; it must simply not be re-added.

THE ANGLE MAP  (needed by instruments 1 and 2; no vehicle model is assumed)
  The fork computes   la_act = -VM.calc_curvature(rad(sa - angleOffset), v, roll) * v**2
                      la_des =  desired_curvature * v**2
  calc_curvature is AFFINE in the steering angle:  la = S(v)*sa + c(v, roll, offset).  Differencing
  two frames kills c, so S(v) -- the only thing needed to turn a lateral-accel error into an ANGLE
  error -- is measurable from the wire alone:

        sa_des(t) = sa_act(t) + (la_des(t) - la_act(t)) / S(v)          [S(v) < 0]

  and the roll compensation and the learned angle offset CANCEL EXACTLY.  S(v) is fitted below to the
  model's own functional form S(v) = -(pi/180) * v^2 * K0 / (1 - sf*v^2) purely as a smoother; the
  raw per-bin slopes are printed beside the fit so the smoothing can be audited.
  ** This means instrument 1 is, at bottom, the lateral-accel error expressed in degrees.  Its value
  is the BINNING (by achieved |angle|) and the SIGN convention, not a new measurement channel. **

NOISE FLOOR
  Every headline statistic is reported with (a) a split-half value (odd runs vs even runs) and
  (b) a bootstrap 95% CI computed by RESAMPLING RUNS WITH REPLACEMENT (not frames -- frames inside a
  run are correlated over ~1 s and frame-bootstrap understates the CI by ~10x).

Python: /usr/local/bin/python3 (numpy+scipy).  NOT the fork's .venv.
"""
from __future__ import annotations

import json
import os
import numpy as np
from scipy import signal as sps

# ----------------------------------------------------------------------------- caches / loading

KIT = os.environ.get("KIT_ROOT", "/home/user/accord-eps-torque-mod")
# Build provenance VERIFIED BY ME from each route's own initData params (segment 0), not inherited:
#   0000006c / 0000006d  GitCommit 84766cdc523facec6a77107dc093f21a109695e8 = Dom rev 6.4
#                        LaneCentering=1  AccordRefFilter=0.06  AccordHoldLevel=1  AccordDither=0.0
#                        AccordFrictionHystBand=1
#   00000076             GitCommit e44b6cd31807340ea0b87dac94f9ba1eb94f9ca8 = Dom rev 5
#                        LaneCentering=1  AccordRefFilter=0.12
# So r6c/r6d numbers ARE on-car rev 6.4 measurements, not simulation or extrapolation.
CACHES = {
    # tag           relative path                                              build
    "r76_v293": "analysis-2020accord/_scratch/cache/tau/r76_v293_ident.npz",   # rev 5  (e44b6cd3)
    "r6c_rev64": "analysis-2020accord/_scratch/cache/tau/r6c_rev64_ident.npz",  # rev 6.4 (84766cdc)
    "r6d_rev64": "analysis-2020accord/_scratch/cache/tau/r6d_rev64_ident.npz",  # rev 6.4 (84766cdc)
}

SPEED_BINS = [(5.0, 10.0), (10.0, 15.0), (15.0, 20.0), (20.0, 25.0), (25.0, 32.0)]
NOTE_BINS = [(5.0, 15.0), (15.0, 34.0)]   # the split the operator's notes actually live on

MIN_BIN_N = 50          # a statistic on fewer frames than this is printed but flagged
GAP_SAMPLES = 4.0       # run-break rule, identical to rev64_03_goal.py


def resolve(tag_or_path: str) -> str:
    if tag_or_path in CACHES:
        return os.path.join(KIT, CACHES[tag_or_path])
    if os.path.isabs(tag_or_path):
        return tag_or_path
    return os.path.join(KIT, tag_or_path)


def load(tag_or_path: str) -> dict:
    """Load a *_ident.npz cache onto the t_cs grid.  Same resampling as rev64_03_goal.py."""
    path = resolve(tag_or_path)
    D = np.load(path, allow_pickle=True)
    t = np.asarray(D["t_cs"], dtype=float)
    FS = 1.0 / float(np.median(np.diff(t)))

    def on_grid(tk, vk):
        return np.interp(t, np.asarray(D[tk], float), np.asarray(D[vk], float))

    S = dict(
        tag=os.path.basename(path), t=t, FS=FS, n=len(t),
        act=np.asarray(D["cs_active"], float) > 0.5,
        # cs_la_des is LateralTorqueState.desiredLateralAccel = `setpoint` (latcontrol_torque.py:839),
        # i.e. AFTER delay compensation AND after the Accord reference filter.  It is what the
        # controller is actually tracking -- NOT the raw model demand.
        lad=np.asarray(D["cs_la_des"], float),          # tracked SETPOINT, m/s^2
        des_curv=np.asarray(D["cs_des_curv"], float),   # post-lane-centring MODEL demand, 1/m
        laa=np.asarray(D["cs_la_act"], float),          # from the measured steering angle, m/s^2
        out=np.asarray(D["cs_out"], float),             # commanded torque, units of the [-1,1] output
        v=on_grid("t_cst", "vego"),
        sa=on_grid("t_cst", "sa_deg"),                  # measured steering angle, deg (+left), 0.1 deg LSB
        sr_can=on_grid("t_cst", "sr_deg"),              # CAN steering rate, deg/s, 1 deg/s LSB
        pr=on_grid("t_cst", "spress") > 0.5,
    )
    # the raw model demand in lateral-accel units: desiredCurvature * v^2, post-lane-centring but
    # BEFORE the delay compensation and the reference filter.  Use this when the question is "does
    # the car match THE MODEL"; use lad when the question is "does the car match its own setpoint".
    S["lam"] = S["des_curv"] * S["v"] ** 2
    S["engaged_all"] = S["act"] & ~S["pr"]
    return S


# ----------------------------------------------------------------------------- runs

def runs(S: dict, vlo: float, vhi: float, minlen_s: float = 0.0, extra_mask=None):
    """Contiguous engaged spans inside a speed bin.  Returns [(i0, i1), ...] half-open."""
    t, FS = S["t"], S["FS"]
    m = S["engaged_all"] & (S["v"] >= vlo) & (S["v"] < vhi)
    if extra_mask is not None:
        m = m & extra_mask
    out, n, i = [], len(m), 0
    while i < n:
        if not m[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and m[j + 1] and (t[j + 1] - t[j]) < GAP_SAMPLES / FS:
            j += 1
        if (j + 1 - i) / FS >= minlen_s:
            out.append((i, j + 1))
        i = j + 1
    return out


def run_index(S, vlo, vhi, minlen_s=0.0, extra_mask=None):
    """Same as runs() but returns (idx, run_id) flat arrays -- convenient for binning + bootstrap."""
    rs = runs(S, vlo, vhi, minlen_s, extra_mask)
    idx = np.concatenate([np.arange(a, b) for a, b in rs]) if rs else np.zeros(0, int)
    rid = np.concatenate([np.full(b - a, k) for k, (a, b) in enumerate(rs)]) if rs else np.zeros(0, int)
    return idx, rid, rs


# ----------------------------------------------------------------------------- derivatives

def sg_deriv(x: np.ndarray, FS: float, win_s: float = 0.15, order: int = 2, deriv: int = 1):
    """Savitzky-Golay derivative.  Used instead of the CAN steering rate because sr_deg quantises at
    1 deg/s (sigma 0.29 deg/s) while a 15-point SG on the 0.1 deg angle gives sigma ~0.17 deg/s."""
    n = int(round(win_s * FS))
    n = max(n + (n + 1) % 2, order + 2 + (order % 2))      # odd, > order+1
    return sps.savgol_filter(x, n, order, deriv=deriv, delta=1.0 / FS, mode="interp")


def add_rates(S: dict, win_s: float = 0.15):
    """Attach achieved / desired steering angle and their rates.  Requires fit_S first."""
    FS = S["FS"]
    S["sa_rate"] = sg_deriv(S["sa"], FS, win_s)                 # achieved wheel rate, deg/s
    S["sa_des"] = S["sa"] + (S["lad"] - S["laa"]) / S["Sv"]     # SETPOINT wheel angle, deg (see header)
    S["sa_des_rate"] = sg_deriv(S["sa_des"], FS, win_s)         # setpoint wheel rate, deg/s
    if "lam" in S:
        S["sa_mod"] = S["sa"] + (S["lam"] - S["laa"]) / S["Sv"]  # MODEL-demand wheel angle, deg
        S["sa_mod_rate"] = sg_deriv(S["sa_mod"], FS, win_s)
        S["lam_rate"] = sg_deriv(S["lam"], FS, win_s)            # model-demanded lateral jerk
    S["out_rate"] = sg_deriv(S["out"], FS, win_s)               # d(torque)/dt, output units per s
    S["laa_rate"] = sg_deriv(S["laa"], FS, win_s)               # delivered lateral jerk, m/s^3
    S["lad_rate"] = sg_deriv(S["lad"], FS, win_s)               # demanded lateral jerk, m/s^3
    S["rate_win_s"] = win_s
    return S


# ----------------------------------------------------------------------------- the angle map S(v)

def _S_model(v, K0, sf):
    return -(np.pi / 180.0) * v ** 2 * K0 / (1.0 - sf * v ** 2)


def fit_S(S: dict, lag_s: float = 0.20, min_dsa: float = 0.3, verbose: bool = True):
    """Fit S(v) = d(la_act)/d(sa_deg) from differenced engaged frames.  Roll and angle offset cancel.

    Attenuation from angle quantisation is bounded by requiring |dsa| > min_dsa (0.1 deg LSB over two
    samples is sigma ~0.041 deg, so the bias is (0.041/0.3)^2 ~ 1.9% worst case); the reverse
    regression is printed so the bracket can be read directly.
    """
    L = int(round(lag_s * S["FS"]))
    eng = S["engaged_all"]
    ok = eng[:-L] & eng[L:] & (np.abs(S["t"][L:] - S["t"][:-L] - lag_s) < 0.25 * lag_s)
    dsa = S["sa"][L:] - S["sa"][:-L]
    dla = S["laa"][L:] - S["laa"][:-L]
    vm = 0.5 * (S["v"][L:] + S["v"][:-L])
    ok &= np.abs(dsa) > min_dsa

    rows = []
    for lo, hi in SPEED_BINS:
        m = ok & (vm >= lo) & (vm < hi)
        if m.sum() < 200:
            rows.append((lo, hi, int(m.sum()), np.nan, np.nan, np.nan))
            continue
        fwd = float(np.sum(dsa[m] * dla[m]) / np.sum(dsa[m] ** 2))              # la on sa
        rev = float(np.sum(dsa[m] * dla[m]) / np.sum(dla[m] ** 2))              # sa on la -> 1/slope
        rows.append((lo, hi, int(m.sum()), fwd, 1.0 / rev, float(np.mean(vm[m]))))

    good = [r for r in rows if np.isfinite(r[3])]
    vbar = np.array([r[5] for r in good])
    # forward regression is attenuated by angle quantisation, reverse is inflated: the truth is
    # bracketed.  Use the geometric mean and carry the bracket width as the systematic uncertainty.
    smid = -np.sqrt(np.array([abs(r[3]) for r in good]) * np.array([abs(r[4]) for r in good]))
    brack = np.array([abs(r[4] / r[3]) - 1.0 for r in good])
    from scipy.interpolate import PchipInterpolator
    interp = PchipInterpolator(vbar, smid, extrapolate=True)
    vq = np.clip(S["v"], vbar[0], vbar[-1])            # clamp: do not extrapolate the map
    S["Sv"] = interp(vq)
    S["S_rows"] = rows
    S["S_bracket_pct"] = float(np.mean(brack) * 100.0)
    S["S_nodes"] = (vbar.tolist(), smid.tolist())

    if verbose:
        print(f"  angle map S(v) = d(la_act)/d(sa_deg), from {lag_s*1000:.0f} ms differences, |dsa|>{min_dsa} deg")
        print(f"    {'v bin':>9} {'n':>7} {'S fwd':>10} {'S rev':>10} {'S used':>10}  (m/s^2 per deg)")
        k = 0
        for lo, hi, n, fwd, rev, vb in rows:
            if not np.isfinite(fwd):
                print(f"    {lo:4.0f}-{hi:<4.0f} {n:7d}   (too few)")
                continue
            print(f"    {lo:4.0f}-{hi:<4.0f} {n:7d} {fwd:10.5f} {rev:10.5f} {smid[k]:10.5f}")
            k += 1
        print(f"    PCHIP through the bracket mid-points, clamped outside {vbar[0]:.1f}-{vbar[-1]:.1f} m/s.")
        print(f"    fwd/rev bracket width {S['S_bracket_pct']:.1f}% -> that is the SYSTEMATIC "
              f"uncertainty on every degree-valued number below.")
    return S


# ----------------------------------------------------------------------------- statistics helpers

def boot_ci(values, groups, stat, n_boot=400, seed=0, alpha=0.05):
    """Bootstrap a statistic by resampling GROUPS (runs/episodes) with replacement.

    values : (N,) or (N, k) array of per-sample quantities
    groups : (N,) integer group id
    stat   : callable(values_subset) -> float
    Returns (point, lo, hi, half_width).
    """
    values = np.asarray(values)
    groups = np.asarray(groups)
    uniq = np.unique(groups)
    if len(uniq) == 0 or len(values) == 0:
        return (np.nan,) * 4
    point = float(stat(values))
    if len(uniq) < 3:
        return point, np.nan, np.nan, np.nan
    members = {g: np.flatnonzero(groups == g) for g in uniq}
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sel = np.concatenate([members[g] for g in pick])
        draws[b] = stat(values[sel])
    lo, hi = np.nanpercentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return point, float(lo), float(hi), float((hi - lo) / 2.0)


def split_half(values, groups, stat):
    """Odd-group vs even-group value of a statistic.  Returns (a, b, |a-b|)."""
    values, groups = np.asarray(values), np.asarray(groups)
    uniq = np.unique(groups)
    if len(uniq) < 2:
        return np.nan, np.nan, np.nan
    ga = np.isin(groups, uniq[0::2])
    gb = np.isin(groups, uniq[1::2])
    if ga.sum() == 0 or gb.sum() == 0:
        return np.nan, np.nan, np.nan
    a, b = float(stat(values[ga])), float(stat(values[gb]))
    return a, b, abs(a - b)


def p95(x):
    x = np.asarray(x)
    return float(np.percentile(np.abs(x), 95)) if len(x) else np.nan


def rms(x):
    x = np.asarray(x)
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else np.nan


# ----------------------------------------------------------------------------- synthetic harness

def synth(n=60000, FS=100.0, seed=1):
    """A synthetic S-dict with the same keys as load(), fully engaged, 25 m/s, for positive controls.
    The caller overwrites laa/sa to inject the defect it wants the instrument to find."""
    t = np.arange(n) / FS
    rng = np.random.default_rng(seed)
    S = dict(tag="SYNTH", t=t, FS=FS, n=n,
             act=np.ones(n, bool), pr=np.zeros(n, bool),
             v=np.full(n, 19.0), sr_can=np.zeros(n),
             out=np.zeros(n), lad=np.zeros(n), laa=np.zeros(n), sa=np.zeros(n))
    S["engaged_all"] = np.ones(n, bool)
    S["Sv"] = _S_model(S["v"], 1.0 / (2.83 * 16.88), -0.0012)
    S["_rng"] = rng
    return S


def banner(txt):
    print("\n" + "=" * 96)
    print(txt)
    print("=" * 96)


def dump_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=float)
    print(f"\n  [json] {path}")
