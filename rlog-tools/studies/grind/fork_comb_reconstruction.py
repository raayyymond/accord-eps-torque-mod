# -*- coding: utf-8 -*-
"""studies/grind/fork_comb_reconstruction.py -- THE LAG-FREE FORK-SIDE REMOVAL OF THE 20 Hz COMMAND COMB.

Subagent `combfix`, 2026-09-13.  ANALYSIS ONLY: builds no firmware, flashes nothing, sends nothing on
any bus.  It writes one patch into the openpilot fork's WORKING TREE (uncommitted) -- see
docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.md; this file is only the measurement behind it.

THE PROBLEM (established, not re-litigated here):
  `modelV2.action.desiredCurvature` publishes at 20 Hz; controlsd runs at 100 Hz and reads the LATEST
  message with no interpolation, so the plan reaches the PID as a PURE ZERO-ORDER HOLD -- rms in-hold
  deviation exactly 0.000e+00 on all six cached routes, and `clip_curvature`'s binding fraction is
  0.000, so nothing rounds the staircase off.  [MODELD-CADENCE-VS-RING-2026-09-10.md sections 2,3,5']
  The staircase's step discontinuities put a phase-locked comb on the 0xE4 wire at the camera clock
  (f_model = 19.9986-19.9997 Hz), measured on every build V112 -> V289.

THE CONSTRAINT (operator, 2026-09-10, memory/feedback/builds/feedback-no-openpilot-side-modifications.md):
  fork-side changes are in scope FOR THE GRINDING ISSUE ONLY and only if they do not limit the model's
  connection or steering authority.  A command LOW-PASS FILTER is forbidden BY NAME; so is added
  command lag, clipped output slew, reduced STEER_MAX, lowered STEER_DELTA_UP.

THE TWO CANDIDATES the record names:
  (A) SLOPE-CONTINUOUS EXTRAPOLATION -- at model frame k take v[k] and the inter-frame slope
      (v[k]-v[k-1])/T_model, and advance linearly over the 5 controlsd ticks until frame k+1.
  (B) TRAJECTORY-SHAPED RECONSTRUCTION -- advance along the model's OWN published future
      (modelV2.orientationRate.z / velocity.x on T_IDXS), anchored on v[k].

SECTIONS
  S1  TRANSFER FUNCTIONS   |H(f)| and GROUP DELAY of each reconstruction, f <= 5 Hz, measured by
                           sinusoid injection against the ideal continuous signal.  Plus the 18-22 Hz
                           image gain -- the comb itself.
  S2  BOUNDS               frame-instant fidelity (authority), the monotone/overshoot bound, and the
                           dropped-frame behaviour.
  S3  OFFLINE REPLAY       cached routes r39 (V282) and r63 (V289): the real 20 Hz plan stream pushed
                           through each reconstruction, then through the FORK'S OWN clip_curvature and
                           LatControlTorque setpoint path, and the resulting 0xE4 command.  Reports
                           18-22 Hz dB, the MODELD-CADENCE d2 model-phase fold R, and 1-5 Hz (must be nil).
  S4  MIRROR               r39 only (the one clean V282 mirror): the command delta through the
                           byte-exact 1 kHz chain, delivered in-band torque counts.

PRE-REGISTERED "THIS BUYS NOTHING" (written before the script was run -- see the doc's section 0):
  N1  18-22 Hz command content does not fall by at least 6 dB.
  N2  the d2 model-phase fold R does not fall from ~0.37 toward its own detuned null (~0.01-0.04).
  N3  |H| at 1-5 Hz departs from 1.000 by more than 0.1 dB, or group delay is positive anywhere there.
  N4  even on a clean pass: lock fraction 0.50 caps the RING benefit at ~29 % amplitude, and the kit
      has already judged x1.22 unreadable from one drive.  A pass licenses BUILDING, never a cure.

Run: python rlog-tools/studies/grind/fork_comb_reconstruction.py
Writes _scratch/fork_comb_reconstruction.txt beside it.
"""
import os
import sys
import types

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FORK = "C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
MDIR = os.path.join(HERE, "_scratch", "modeld")
OUTF = os.path.join(HERE, "_scratch", "fork_comb_reconstruction.txt")
OUT = []

FS = 100.0                 # controlsd tick rate
DT_CTRL = 0.01
DT_MDL = 0.05
NHOLD = 5                  # controlsd ticks per model frame, nominal
DET = np.r_[np.arange(-0.80, -0.099, 0.02), np.arange(0.10, 0.801, 0.02)]  # modelrate's detuned null


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ======================================================================================================
# the FORK's own clip_curvature, loaded from the fork's bytes with only DT_CTRL / gravity stubbed
# ======================================================================================================
def _load_fork_drive_helpers():
    """Import the fork's real drive_helpers.py.  Only common.realtime and common.constants are stubbed
    (both verified against the fork source: DT_CTRL=0.01, DT_MDL=0.05, g=9.81); every line of arithmetic
    executed below is the fork's own."""
    import importlib.util
    rt = types.ModuleType("openpilot.common.realtime")
    rt.DT_CTRL, DT = DT_CTRL, DT_MDL
    rt.DT_MDL = DT
    cs = types.ModuleType("openpilot.common.constants")
    cs.ACCELERATION_DUE_TO_GRAVITY = 9.81
    op = types.ModuleType("openpilot"); op.__path__ = [FORK]
    opc = types.ModuleType("openpilot.common"); opc.__path__ = [os.path.join(FORK, "common")]
    for n, m in (("openpilot", op), ("openpilot.common", opc),
                 ("openpilot.common.realtime", rt), ("openpilot.common.constants", cs)):
        sys.modules[n] = m
    p = os.path.join(FORK, "selfdrive", "controls", "lib", "drive_helpers.py")
    spec = importlib.util.spec_from_file_location("fork_drive_helpers", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DH = _load_fork_drive_helpers()


# ======================================================================================================
# the reconstructions
# ======================================================================================================
def recon_zoh(v_frame, tick_of_frame, n_ticks):
    """TODAY's behaviour: hold the newest published value."""
    out = np.empty(n_ticks)
    k = np.searchsorted(tick_of_frame, np.arange(n_ticks), side="right") - 1
    k = np.clip(k, 0, len(v_frame) - 1)
    out[:] = v_frame[k]
    return out, k


def recon_slope(v_frame, tick_of_frame, n_ticks, beta=1.0, horizon=DT_MDL):
    """(A) SLOPE-CONTINUOUS EXTRAPOLATION.
         s[k]  = v[k] - v[k-1]                       (the model's own most recent step)
         a(n)  = min(dt*(n - n_k)/horizon, 1.0)      (elapsed fraction of one frame interval, saturating)
         out(n)= v[k] + beta * s[k] * a(n)
       a(n_k) = 0 exactly, so the value AT EVERY MODEL-FRAME INSTANT is the model's own, untouched.
       a saturates at 1.0, so a dropped frame FREEZES instead of running away."""
    n = np.arange(n_ticks)
    k = np.searchsorted(tick_of_frame, n, side="right") - 1
    k = np.clip(k, 0, len(v_frame) - 1)
    s = np.diff(v_frame, prepend=v_frame[0])
    a = np.minimum((n - tick_of_frame[k]) * DT_CTRL / horizon, 1.0)
    return v_frame[k] + beta * s[k] * a, k


def recon_slope_ideal(v, beta=1.0, nh=NHOLD, order=1):
    """Same, on a perfectly regular grid (used by the sinusoid transfer-function test).
       order=1: s[k] = v[k]-v[k-1]              -- backward difference, estimates v' at t_k - T/2
       order=2: s[k] = (3v[k]-4v[k-1]+v[k-2])/2 -- 2nd-order backward, estimates v' at t_k (no bias)"""
    if order == 1:
        s = np.diff(v, prepend=v[0])
    else:
        vm1 = np.r_[v[0], v[:-1]]
        vm2 = np.r_[v[0], v[0], v[:-2]]
        s = 0.5 * (3 * v - 4 * vm1 + vm2)
    frac = np.arange(nh) / nh
    return (v[:, None] + beta * s[:, None] * frac[None, :]).ravel()


def recon_zoh_ideal(v, nh=NHOLD):
    return np.repeat(v, nh)


def recon_traj_ideal(v, kap_future, nh=NHOLD):
    """(B) TRAJECTORY-SHAPED.  kap_future[k, j] = the model's predicted curvature at tick offset j of
       frame k, on the model's own published future.  Anchored so offset 0 is exactly v[k]."""
    d = kap_future - kap_future[:, :1]
    return (v[:, None] + d).ravel()


# ======================================================================================================
# S1 -- TRANSFER FUNCTIONS
# ======================================================================================================
def measure_H(recon, f, n_frames=4000, nh=NHOLD, **kw):
    """Complex gain of `recon` at frequency f, referenced to the IDEAL CONTINUOUS signal on the same
    100 Hz grid.  The model samples the continuous signal at t_k = k*DT_MDL; the reconstruction fills
    the 100 Hz ticks between.  Returns H = <out, e^-j2pi f t> / <ideal, e^-j2pi f t>."""
    tk = np.arange(n_frames) * DT_MDL
    v = np.exp(2j * np.pi * f * tk).real
    out = recon(v, **kw) if kw else recon(v)
    t = np.arange(n_frames * nh) * DT_CTRL
    ideal = np.exp(2j * np.pi * f * t).real
    w = np.hanning(len(t))
    e = np.exp(-2j * np.pi * f * t) * w
    return (out * e).sum() / (ideal * e).sum()


def s1_transfer():
    pr("=" * 118)
    pr("S1  TRANSFER FUNCTIONS -- |H(f)| and GROUP DELAY, referenced to the IDEAL CONTINUOUS SIGNAL")
    pr("=" * 118)
    pr("Method: sample a unit sinusoid at exactly 20 Hz, reconstruct at 100 Hz, project both the output")
    pr("and the ideal continuous sinusoid onto exp(-j2pi f t) over 4000 model frames (200 s), Hann")
    pr("windowed.  Group delay tau_g = -dphi/d(2pi f), central difference over df = 0.05 Hz.")
    pr("POSITIVE group delay = LAG (forbidden).  NEGATIVE = LEAD.  The ZOH row is TODAY's behaviour.")
    pr()
    fs = np.array([0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0])
    df = 0.05
    rows = {}
    cands = [("ZOH (today)", recon_zoh_ideal)]
    for b in (0.25, 0.5, 0.75, 1.0):
        cands.append((f"SLOPE b={b:.2f} (A)", lambda v, b=b: recon_slope_ideal(v, beta=b)))
    cands.append(("SLOPE b=1 2nd-order", lambda v: recon_slope_ideal(v, beta=1.0, order=2)))
    for name, rc in cands:
        mag, gd = [], []
        for f in fs:
            Hm = measure_H(rc, f - df); Hp = measure_H(rc, f + df); H0 = measure_H(rc, f)
            mag.append(abs(H0))
            dphi = np.angle(Hp / Hm)
            gd.append(-dphi / (2 * np.pi * 2 * df))
        rows[name] = (np.array(mag), np.array(gd))
    pr("%-22s %10s %10s %10s %10s %10s %10s %10s %10s" % ("reconstruction", *[f"{f:g} Hz" for f in fs]))
    pr("-" * 118)
    for name, (mag, gd) in rows.items():
        pr("%-22s " % (name + "  |H|") + " ".join("%10.6f" % m for m in mag))
        pr("%-22s " % ("   tau_g [ms]") + " ".join("%10.3f" % (g * 1e3) for g in gd))
    pr()
    zg = rows["ZOH (today)"][1]
    pr("LEAD EACH RECONSTRUCTION BUYS vs TODAY (tau_g_ZOH - tau_g_X), ms.  POSITIVE = faster than today.")
    for name, (_, sg) in rows.items():
        if name.startswith("ZOH"):
            continue
        pr("%-22s " % name + " ".join("%10.3f" % ((z - s) * 1e3) for z, s in zip(zg, sg)))
    pr()

    # ---- the comb itself: the 18-22 Hz image of a baseband tone ----
    pr("IMAGE GAIN AT THE CAMERA CLOCK -- a baseband tone at f_b appears in the 100 Hz stream at")
    pr("20 +/- f_b Hz purely as a reconstruction artefact (the sampled sequence carries nothing above")
    pr("10 Hz).  THAT IMAGE IS THE COMB.  Amplitude of the image relative to the baseband tone:")
    pr()
    hdr = ["f_b [Hz]"] + [n for n, _ in cands]
    pr("  ".join("%-20s" % h if i == 0 else "%18s" % h for i, h in enumerate(hdr)))
    pr("-" * 140)
    img = {}
    for fb in (0.25, 0.5, 1.0, 2.0, 4.0):
        n_frames = 8000
        tk = np.arange(n_frames) * DT_MDL
        v = np.cos(2 * np.pi * fb * tk)
        t = np.arange(n_frames * NHOLD) * DT_CTRL
        w = np.hanning(len(t))
        line, tots = ["%-20.2f" % fb], []
        for name, rc in cands:
            o = rc(v)
            a = [2 * abs((o * w * np.exp(-2j * np.pi * fi * t)).sum()) / w.sum()
                 for fi in (20.0 - fb, 20.0 + fb)]
            tots.append(np.hypot(*a))
        for x in tots:
            line.append("%18.6f" % x)
        img[fb] = tots
        pr("  ".join(line))
    pr()
    pr("the same, in dB relative to TODAY's ZOH (negative = comb removed):")
    pr("  ".join("%-20s" % "f_b [Hz]" if i == 0 else "%18s" % h for i, h in enumerate(hdr)))
    pr("-" * 140)
    for fb, tots in img.items():
        pr("  ".join(["%-20.2f" % fb] + ["%18.2f" % (20 * np.log10(max(x, 1e-30) / max(tots[0], 1e-30)))
                                         for x in tots]))
    pr()
    return rows


# ======================================================================================================
# S2 -- BOUNDS
# ======================================================================================================
def s2_bounds():
    pr("=" * 118)
    pr("S2  BOUNDS -- authority at the frame instants, the overshoot bound, dropped frames, large steps")
    pr("=" * 118)
    rng = np.random.default_rng(20260913)
    v = np.cumsum(rng.standard_normal(2000)) * 1e-3
    v[900] += 0.05                                   # a large step
    tof = np.arange(2000) * NHOLD
    n = 2000 * NHOLD
    zo, _ = recon_zoh(v, tof, n)
    sl, _ = recon_slope(v, tof, n)
    pr("frame-instant fidelity (AUTHORITY): max |out[n_k] - v[k]| over 2000 frames")
    pr("    ZOH   %.3e" % np.max(np.abs(zo[tof] - v)))
    pr("    SLOPE %.3e   <- 0.0 exactly: the model's own value is delivered UNCHANGED at every publish"
       % np.max(np.abs(sl[tof] - v)))
    pr()
    s = np.diff(v, prepend=v[0])
    lo = np.minimum(v, v - s)[:, None] * np.ones(NHOLD)
    hi = np.maximum(v, v - s)[:, None] * np.ones(NHOLD)
    dev = sl.reshape(-1, NHOLD)
    excess = np.maximum(dev - np.maximum(hi, v[:, None] + np.abs(s)[:, None]), 0)
    pr("MONOTONE BOUND.  v_next is not available causally, so the bound is stated on the causal triple")
    pr("{v[k-1], v[k], v[k]+s[k]} (the extrapolation endpoint).  Enforced interval is therefore")
    pr("[v[k]-|s[k]|, v[k]+|s[k]|].  Max violation over 2000 frames incl. the injected 0.05 step:")
    band_lo = v[:, None] - np.abs(s)[:, None]
    band_hi = v[:, None] + np.abs(s)[:, None]
    viol = np.maximum(np.maximum(band_lo - dev, dev - band_hi), 0).max()
    pr("    %.3e   (0.0 => satisfied BY CONSTRUCTION for a one-frame horizon; the clamp only bites on"
       % viol)
    pr("            a dropped frame, where a(n) saturates at 1.0 and the output FREEZES)")
    pr()
    pr("MAXIMUM DEPARTURE within a hold is 0.8*|s[k]| (the 5th tick, a=0.8); the output reaches")
    pr("v[k]+s[k] only at the instant frame k+1 replaces it.  So the extrapolation never advances")
    pr("further than ONE MODEL STEP beyond the newest model value -- a self-scaling bound.")
    pr()
    # dropped frame
    tof2 = np.array([0, 5, 10, 25, 30])            # a 150 ms gap (2 frames dropped) between 10 and 25
    v2 = np.array([0.0, 0.01, 0.02, 0.03, 0.04])
    sl2, _ = recon_slope(v2, tof2, 35)
    pr("DROPPED FRAME.  frames at ticks %s, values %s (a 150 ms gap):" % (tof2.tolist(), v2.tolist()))
    pr("    ticks 10..24: " + " ".join("%.4f" % x for x in sl2[10:25]))
    pr("    -> ramps for 5 ticks then HOLDS at v[k]+s[k] = %.4f for the remaining 10 ticks."
       % (v2[2] + (v2[2] - v2[1])))
    pr("    ZOH on the same gap holds at %.4f.  The reconstruction's excursion over the whole 150 ms"
       % v2[2])
    pr("    is ONE model step (%.4f), not a runaway." % (v2[2] - v2[1]))
    pr()
    pr("PER-TICK RATE.  Within a hold the reconstruction spreads the step over five ticks (5x SMALLER")
    pr("per-tick delta).  But at the FRAME BOUNDARY the delta is s[k+1] - 0.8*s[k], so when consecutive")
    pr("model steps REVERSE SIGN the boundary delta can reach 1.8x a single step.  On white-noise steps:")
    pr("    max |per-tick delta|  ZOH %.5e   SLOPE %.5e   ratio %.3f"
       % (np.abs(np.diff(zo)).max(), np.abs(np.diff(sl)).max(),
          np.abs(np.diff(sl)).max() / max(np.abs(np.diff(zo)).max(), 1e-30)))
    pr("    THAT IS A WORST CASE ON UNCORRELATED STEPS.  The real plan is not white (modeld applies its")
    pr("    own 0.1 s smooth_value at the model rate, modeld.py:415), so S3 measures it on real data and")
    pr("    reports clip_curvature's binding fraction before and after -- the number that decides it.")
    pr()


# ======================================================================================================
# S3 -- OFFLINE REPLAY on the cached routes
# ======================================================================================================
def fold_stats(w, phase, nb=5):
    """VERBATIM from modeld_cadence_vs_ring.fold_stats (MODELD-CADENCE-VS-RING-2026-09-10)."""
    fr = phase - np.floor(phase)
    b = np.minimum((fr * nb).astype(int), nb - 1)
    mu = np.array([w[b == k].mean() if (b == k).any() else np.nan for k in range(nb)])
    C = np.nanmax(mu) / w.mean() if w.mean() > 0 else np.nan
    z = (w * np.exp(2j * np.pi * fr)).sum() / max(w.sum(), 1e-30)
    return float(C), float(np.abs(z))


def band_amp(x, lo, hi, fs=FS):
    """sqrt(2) * rms of the band-passed signal -- burst_echo_sizing's measure, used throughout."""
    b, a = signal.butter(4, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    y = signal.filtfilt(b, a, x)
    return float(np.sqrt(2.0) * np.std(y))


def load_route(tag):
    d = np.load(os.path.join(MDIR, f"{tag}_cad.npz"), allow_pickle=True)
    return {k: d[k] for k in d.files if d[k].ndim <= 1}


def bp(x, lo, hi, fs=FS, order=4):
    b, a = signal.butter(order, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return signal.filtfilt(b, a, x)


def fir_project(y, u, ntap=64):
    """Least-squares causal FIR projection of y onto u:  y ~= sum_j h[j] u[n-j].
    Returns (h, yhat, r2).  Both signals are assumed already band-limited.  This is a legitimate
    open-loop decomposition because u (the camera plan) is EXOGENOUS to the EPS: the record bounds
    the outer loop through openpilot at |L| = 0.026-0.165 (OUTER-LOOP-ID-2026-09-10.md)."""
    n = len(y)
    U = np.empty((n - ntap, ntap))
    for j in range(ntap):
        U[:, j] = u[ntap - 1 - j: n - 1 - j]
    yy = y[ntap:]
    h, *_ = np.linalg.lstsq(U, yy, rcond=None)
    yhat = U @ h
    r2 = 1.0 - np.var(yy - yhat) / max(np.var(yy), 1e-30)
    return h, yhat, float(r2)


def apply_fir(h, u):
    return np.convolve(u, h)[: len(u)]


BANDS = (("18-22 Hz", 18.0, 22.0), ("10-18 Hz", 10.0, 18.0), ("5-10 Hz", 5.0, 10.0),
         ("1-5 Hz", 1.0, 5.0), ("0.2-1 Hz", 0.2, 1.0))



def analytic(x, fs, lo, hi, ntap=257):
    """VERBATIM from modeld_phase_lock.analytic."""
    b = signal.firwin(ntap, [lo, hi], fs=fs, pass_zero=False)
    return signal.hilbert(signal.filtfilt(b, [1.0], np.asarray(x, float) - np.mean(x)))


def r2_at(z, t, ic, f, m):
    """VERBATIM from modeld_phase_lock.r2_at -- the SQUARE-LAW (mod pi) lock detector."""
    z2 = z[m] ** 2
    den = (np.abs(z[m]) ** 2).sum()
    th = 2 * np.pi * ((t[m] - ic) * f)
    return float(np.abs((z2 * np.exp(-2j * th)).sum()) / max(den, 1e-300))


def r2_deb(z, t, ic, fm, m):
    """R2_deb = sqrt(max(R2^2 - mean(R2^2 over detuned clocks), 0)) -- the DEBIASED estimator
    adjudicated 2026-09-11 (docs/STATE.md, THE ESTIMATOR CORRECTION).  R2 - floor is biased LOW
    by ~0.12 and must never be quoted as an estimate."""
    r0 = r2_at(z, t, ic, fm, m)
    rd = np.array([r2_at(z, t, ic, fm + d, m) for d in DET])
    return float(np.sqrt(max(r0 ** 2 - float(np.mean(rd ** 2)), 0.0))), r0, float(np.mean(rd ** 2)) ** 0.5


def welch_H(u, y, fs=FS, nper=2048):
    """Welch transfer estimate H(f) = S_yu / S_uu and the ordinary coherence gamma^2.
    Well conditioned where a narrow-band least-squares FIR is not.  Legitimate as an OPEN-LOOP
    decomposition because u (the camera plan) is EXOGENOUS to the EPS: the record bounds the outer
    loop through openpilot at |L| = 0.026-0.165 (OUTER-LOOP-ID-2026-09-10.md)."""
    f, Suu = signal.welch(u, fs=fs, nperseg=nper, noverlap=nper // 2)
    _, Syy = signal.welch(y, fs=fs, nperseg=nper, noverlap=nper // 2)
    _, Syu = signal.csd(u, y, fs=fs, nperseg=nper, noverlap=nper // 2)
    H = Syu / np.maximum(Suu, 1e-300)
    coh = np.abs(Syu) ** 2 / np.maximum(Suu * Syy, 1e-300)
    return f, H, coh, Syy


def apply_H(du, f_H, H, fs=FS, band=None):
    """Filter du with the measured transfer H(f), on the full-length rfft grid.  `band` restricts the
    correction to (lo, hi) Hz; outside it the correction is zero."""
    n = len(du)
    fr = np.fft.rfftfreq(n, 1.0 / fs)
    Hi = np.interp(fr, f_H, H.real) + 1j * np.interp(fr, f_H, H.imag)
    if band is not None:
        Hi = np.where((fr >= band[0]) & (fr <= band[1]), Hi, 0.0)
    return np.fft.irfft(np.fft.rfft(du) * Hi, n=n)


BANDS = (("18-22 Hz", 18.0, 22.0), ("12-26 Hz", 12.0, 26.0), ("10-18 Hz", 10.0, 18.0),
         ("5-10 Hz", 5.0, 10.0), ("1-5 Hz", 1.0, 5.0), ("0.2-1 Hz", 0.2, 1.0))


def s3_replay(tags=("r39", "r63_v289")):
    comb = np.load(os.path.join(HERE, "_scratch", "modeld_comb_for_combsize.npz"), allow_pickle=True)
    pr("=" * 134)
    pr("S3  OFFLINE REPLAY -- the real 20 Hz plan stream through each reconstruction")
    pr("=" * 134)
    pr("Candidates: ZOH (today) | SLOPE b=0.50 | b=0.75 | b=1.00 (the record's design A) | 2nd-order slope.")
    pr("Each runs through the FORK'S OWN clip_curvature (drive_helpers.py, loaded from the fork's bytes).")
    pr("12-26 Hz is STATE.md's design-law band: 'design against max Ms over the WHOLE 12-26 Hz band'.")
    pr()
    res = {}
    for tag in tags:
        M = load_route(tag)
        t = M["cs_t"]
        mt, mv, mf = M["mdl_t"], M["mdl_curv"], M["mdl_fid"]
        ok = np.isfinite(mt) & np.isfinite(mv) & np.isfinite(mf)
        mt, mv, mf = mt[ok], mv[ok], mf[ok]
        v_ego = np.interp(t, M["st_t"], M["st_v"])
        lat = np.interp(t, M["cc_t"], M["cc_latact"]) > 0.5
        eng = lat & (M["cs_active"] > 0.5)
        roll = np.zeros_like(t)

        k = np.searchsorted(mt, t, side="right") - 1
        good = k >= 2
        k = np.clip(k, 0, len(mv) - 1)
        first_tick = np.searchsorted(t, mt, side="left")
        n = np.arange(len(t))
        a_frac = np.clip((n - first_tick[k]) * DT_CTRL / DT_MDL, 0.0, 1.0)

        # the SHIPPED rule (ModelCurvatureLead.update): only two CONSECUTIVE camera frames carry a
        # usable one-frame slope; every other frame reverts to the zero-order hold.
        consec1 = np.r_[False, np.diff(mf) == 1]
        consec2 = np.r_[False, False, (np.diff(mf[:-1]) == 1) & (np.diff(mf[1:]) == 1)]
        s1 = np.where(consec1, np.diff(mv, prepend=mv[0]), 0.0)
        vm1 = np.r_[mv[0], mv[:-1]]
        vm2 = np.r_[mv[0], mv[0], mv[:-2]]
        s2 = np.where(consec2, 0.5 * (3 * mv - 4 * vm1 + vm2), 0.0)
        pr("  consecutive-frame fraction: 1-back %.4f   2-back %.4f"
           % (float(consec1.mean()), float(consec2.mean())))

        f_model = float(np.ravel(comb[tag + "_f_model"])[0])
        icept = float(np.ravel(comb[tag + "_model_icept"])[0])
        cpc = float(np.ravel(comb[tag + "_cnt_per_curv"])[0])

        CAND = [("ZOH (today)", mv[k]),
                ("SLOPE b=0.50", mv[k] + 0.50 * s1[k] * a_frac),
                ("SLOPE b=0.75", mv[k] + 0.75 * s1[k] * a_frac),
                ("SLOPE b=1.00", mv[k] + 1.00 * s1[k] * a_frac),
                ("2nd-order b=1", mv[k] + s2[k] * a_frac)]

        dc = M["cs_descurv"]
        m12 = eng & (v_ego < 12) & good & np.isfinite(dc)
        pt = float(np.mean(dc[m12] == CAND[0][1][m12]))
        pr("-" * 134)
        pr("ROUTE %s   f_model %.5f Hz   cnt_per_curv %.0f raw 0xE4 counts per 1/m   %d ticks"
           % (tag, f_model, cpc, len(t)))
        pr("  SANITY: controlsState.desiredCurvature == our ZOH reconstruction on %.3f of engaged v<12"
           " ticks (modelrate measured pass-through 0.60-0.71)" % pt)

        def run_clip(kap):
            outp = np.empty(len(t))
            prev = 0.0
            nb = 0
            ne = 0
            cc = M["cs_curv"]
            for i in range(len(t)):
                if not eng[i]:
                    prev = float(cc[i]) if np.isfinite(cc[i]) else prev
                    outp[i] = prev
                    continue
                ne += 1
                prev, _ = DH.clip_curvature(float(v_ego[i]), prev, float(kap[i]), float(roll[i]), 1.0)
                if abs(prev - kap[i]) > 1e-12:
                    nb += 1
                outp[i] = prev
            return outp, (nb / max(ne, 1))

        clipped, bindf = {}, {}
        for nm, kap in CAND:
            clipped[nm], bindf[nm] = run_clip(kap)

        mm = eng & good
        seg = np.flatnonzero(mm)
        runs = [r for r in np.split(seg, np.flatnonzero(np.diff(seg) != 1) + 1) if len(r) > 4000]
        pr("  contiguous engaged runs > 40 s: %d   total ticks %d"
           % (len(runs), sum(len(r) for r in runs)))
        pr()

        def spec(stream, lo, hi):
            return float(np.sqrt(np.mean([band_amp(stream[r], lo, hi) ** 2 for r in runs])))

        pr("  A. CURVATURE after clip_curvature (1/m rms over the long engaged runs), and dB vs ZOH:")
        pr("  %-16s %11s %11s %11s %11s %11s %11s %10s %11s"
           % (("candidate",) + tuple(b[0] for b in BANDS) + ("clip bind", "max|dtick|")))
        pr("  " + "-" * 132)
        base = {}
        basemx = 1.0
        for nm, _ in CAND:
            st = clipped[nm]
            vals = [spec(st, lo, hi) for _, lo, hi in BANDS]
            mx = max(np.abs(np.diff(st[r])).max() for r in runs)
            pr("  %-16s " % nm + " ".join("%11.4e" % v for v in vals)
               + " %10.4f %11.3e" % (bindf[nm], mx))
            if nm.startswith("ZOH"):
                base = dict(zip([b[0] for b in BANDS], vals))
                basemx = mx
            else:
                pr("  %-16s " % "      dB" + " ".join(
                    "%11.2f" % (20 * np.log10(v / max(base[b[0]], 1e-30)))
                    for v, b in zip(vals, BANDS)) + " %10s %11.2fx" % ("", mx / basemx))
        pr()

        cmd_rec = M["co_tqcan"].astype(float)
        cmd_rec = np.where(np.isfinite(cmd_rec), cmd_rec, 0.0)
        cmd_rec = np.interp(t, M["co_t"], cmd_rec)
        v2 = np.maximum(v_ego, 1.0) ** 2
        desla = np.where(np.isfinite(M["cs_desla"]), M["cs_desla"], 0.0)
        descurv = np.where(np.isfinite(M["cs_descurv"]), M["cs_descurv"], 0.0)
        pr("  B. THE 0xE4 COMMAND.  The setpoint->wire path carries GAIN *and* PHASE, so no scalar gain")
        pr("     can substitute one reconstruction for another.  H(f) is estimated by WELCH CROSS-")
        pr("     SPECTRUM (nperseg 2048 = 20.5 s) and the perturbation pushed through it; everything H")
        pr("     does not explain -- the FEEDBACK leg -- is carried through UNCHANGED.  This predicts")
        pr("     the COMMAND and says NOTHING about the plant's response to it.")
        pr()
        pr("     THE BASIS MUST BE THE QUANTITY WE PERTURB.  latcontrol_torque.py:277 forms")
        pr("     expected_lateral_accel from curvature_request_buffer[delay_frames], so")
        pr("     controlsState.desiredLateralAccel as logged is a DELAYED sample (measured lag +3 to")
        pr("     +7 ticks, peak xcorr 0.997-0.999).  Fitting H from that logged signal and applying it")
        pr("     to an UN-DELAYED perturbation puts the correction at the wrong phase: the fitted leg")
        pr("     comes out 18.19 counts against a coherent part of 15.14, and DELETING it makes the")
        pr("     band WORSE by +0.71 dB.  H is therefore fitted from kappa_ZOH * v_ego^2 -- exactly the")
        pr("     quantity the patch changes -- which reproduces the coherent magnitude to 0.3 %% and")
        pr("     whose deletion lands on the sqrt(1 - share) floor.  The CONTROL row below is that")
        pr("     check: 'delete plan' must equal the floor, or the machinery is wrong.")
        pr()
        pr("     'plan share' = power-weighted mean coherence in band = the share of the command's")
        pr("     in-band power this basis explains.  It CAPS what any plan-side fix can remove.")
        pr("     An UPPER BOUND on that share, using controlsState.desiredCurvature * v^2 (which also")
        pr("     carries the lane-centering / turn-hold shaping our reconstruction omits), is printed")
        pr("     alongside: the truth is between the two.")
        pr()
        Hs = {}
        for r in runs:
            Hs[id(r)] = welch_H(clipped["ZOH (today)"][r] * v2[r], cmd_rec[r])
        cmdres = {}
        pr("  %-11s %8s %8s %12s %10s %9s %9s %9s %9s"
           % ("band", "share", "sh.max", "cmd before", "del plan", "b=0.50", "b=0.75", "b=1.00", "2nd-ord"))
        pr("  " + "-" * 106)
        for lab, lo, hi in BANDS:
            shares, shmax, b0s, dels = [], [], [], []
            outs = {nm: [] for nm, _ in CAND[1:]}
            for r in runs:
                f_H, H, coh, Syy = Hs[id(r)]
                sel = (f_H >= lo) & (f_H <= hi)
                shares.append(float(np.sum(coh[sel] * Syy[sel]) / max(np.sum(Syy[sel]), 1e-300)))
                fu, Hu, cu, Su = welch_H(descurv[r] * v2[r], cmd_rec[r])
                su = (fu >= lo) & (fu <= hi)
                shmax.append(float(np.sum(cu[su] * Su[su]) / max(np.sum(Su[su]), 1e-300)))
                b0s.append(band_amp(cmd_rec[r], lo, hi) ** 2)
                plan = apply_H(clipped["ZOH (today)"][r] * v2[r], f_H, H, band=(lo, hi))
                dels.append(band_amp(cmd_rec[r] - plan, lo, hi) ** 2)
                for nm, _ in CAND[1:]:
                    du = (clipped[nm][r] - clipped["ZOH (today)"][r]) * v2[r]
                    ya = cmd_rec[r] + apply_H(du, f_H, H, band=(lo, hi))
                    outs[nm].append(band_amp(ya, lo, hi) ** 2)
            b0 = np.sqrt(np.mean(b0s))
            dl = np.sqrt(np.mean(dels))
            row = [np.sqrt(np.mean(outs[nm])) for nm, _ in CAND[1:]]
            sh = float(np.mean(shares))
            pr("  %-11s %8.3f %8.3f %12.4f %10.4f %9.4f %9.4f %9.4f %9.4f"
               % (lab, sh, float(np.mean(shmax)), b0, dl, *row))
            pr("  %-11s %8s %8s %12s %10.2f %9.2f %9.2f %9.2f %9.2f   dB vs before"
               % ("", "", "", "", *[20 * np.log10(x / max(b0, 1e-30)) for x in [dl] + row]))
            pr("  %-11s %8s %8s %12s %10.2f   <- CONTROL: the sqrt(1-share) floor"
               % ("", "", "", "", 10 * np.log10(max(1 - sh, 1e-12))))
            cmdres[lab] = (sh, b0, row, dl)
        pr()

        ph = (t - icept) * f_model
        phn = (t - icept) * (f_model + 0.37)
        pr("  C. d2 MODEL-PHASE FOLD (MODELD-CADENCE-VS-RING sections 2/3, fold_stats verbatim).")
        pr("     C = max bin mean / overall mean (1.0 uniform, 5.0 a perfect knot); R = amplitude-")
        pr("     weighted Rayleigh concentration; null = the same with the clock detuned +0.37 Hz.")
        pr("     The wire rows apply the measured H over the WHOLE spectrum (no band restriction).")
        pr("  %-30s %10s %8s %8s %9s %9s" % ("channel", "rms|d2|", "C", "C null", "R", "R null"))
        msk = mm & (v_ego < 12)
        fold = {}
        for nm, _ in CAND:
            st = clipped[nm]
            d2 = np.r_[0.0, 0.0, st[2:] - 2 * st[1:-1] + st[:-2]]
            mk = msk & np.isfinite(d2)
            C, R = fold_stats(np.abs(d2[mk]), ph[mk])
            Cn, Rn = fold_stats(np.abs(d2[mk]), phn[mk])
            fold[nm] = (float(np.sqrt(np.mean(d2[mk] ** 2))), C, R)
            pr("  %-30s %10.3e %8.3f %8.3f %9.4f %9.4f" % ("curvature " + nm, fold[nm][0], C, Cn, R, Rn))
        wirefold = {}
        for nm, _ in CAND:
            y = cmd_rec.copy()
            for r in runs:
                f_H, H, coh, Syy = Hs[id(r)]
                du = (clipped[nm][r] - clipped["ZOH (today)"][r]) * v2[r]
                y[r] = cmd_rec[r] + apply_H(du, f_H, H)
            d2 = np.r_[0.0, 0.0, y[2:] - 2 * y[1:-1] + y[:-2]]
            mk = msk & np.isfinite(d2)
            C, R = fold_stats(np.abs(d2[mk]), ph[mk])
            Cn, Rn = fold_stats(np.abs(d2[mk]), phn[mk])
            wirefold[nm] = (C, R)
            pr("  %-30s %10.3e %8.3f %8.3f %9.4f %9.4f"
               % ("0xE4 wire " + nm, float(np.sqrt(np.mean(d2[mk] ** 2))), C, Cn, R, Rn))
        pr()
        pr("  D. THE CAMERA-LOCK FRACTION OF THE 0xE4 COMMAND, before and after, with the record's own")
        pr("     square-law detector (modeld_phase_lock.r2_at) and the DEBIASED estimator R2_deb.")
        pr("     This is the quantity the record's '~29 %% ring benefit at lock 0.50' is a function of,")
        pr("     so it is the number that transfers.  Band 18-22 Hz; stratum = engaged, v < 12 m/s.")
        pr("  %-24s %10s %10s %10s %12s" % ("channel", "R2 raw", "floor", "R2_deb", "in-band E"))
        lo, hi = 18.0, 22.0
        mk = mm & (v_ego < 12)
        for nm, _ in CAND:
            y = cmd_rec.copy()
            if not nm.startswith("ZOH"):
                for r in runs:
                    f_H, H, coh, Syy = Hs[id(r)]
                    du = (clipped[nm][r] - clipped["ZOH (today)"][r]) * v2[r]
                    y[r] = cmd_rec[r] + apply_H(du, f_H, H, band=(lo, hi))
            z = analytic(y, FS, lo, hi)
            rd, r0, fl = r2_deb(z, t, icept, f_model, mk)
            E = float(np.mean(np.abs(z[mk]) ** 2))
            pr("  %-24s %10.4f %10.4f %10.4f %12.1f" % ("0xE4 " + nm, r0, fl, rd, E))
            if nm.startswith("ZOH"):
                E0, rd0 = E, rd
            else:
                pr("  %-24s locked energy R2_deb*E: %.1f -> %.1f  (%.0f %%%% of the locked leg removed);"
                   " total in-band E %.1f -> %.1f"
                   % ("", rd0 * E0, rd * E, 100 * (1 - (rd * E) / max(rd0 * E0, 1e-30)), E0, E))
        pr()
        res[tag] = dict(clipped=clipped, cmd_rec=cmd_rec, runs=runs, t=t, cpc=cpc, cmdres=cmdres,
                        fold=fold, wirefold=wirefold, bindf=bindf, Hs=Hs,
                        CAND=[c[0] for c in CAND], M=M, eng=eng, v_ego=v_ego)
    return res


def main():
    s1_transfer()
    s2_bounds()
    r = s3_replay()
    with open(OUTF, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr()
    pr("wrote %s" % OUTF)
    return r


if __name__ == "__main__":
    main()
