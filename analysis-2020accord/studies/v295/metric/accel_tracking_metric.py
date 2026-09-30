# -*- coding: utf-8 -*-
"""accel_tracking_metric.py -- THE OPERATOR'S GOAL METRIC AS AN INSTRUMENT:
   "comma LKAS command output vs second derivative of steering angle sensor output".

Subagent `metric`, 2026-09-30.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus, edits no
build script, writes no firmware artifact.  Reads the kit's v280-format CAN caches (the decode every census uses) and
the control-path caches; writes a table (.txt), a json and png figures under ./out/.

    python accel_tracking_metric.py                      # V294 + every registered reference route, full report
    python accel_tracking_metric.py r71b_v294 r70_v293   # a subset (the first is the subject; compared to V293 refs)
    python accel_tracking_metric.py --route 75604b0a432fdc89_00000071--a7b8ba5d9d   # a route id -> its tag
    (a new route needs its v280 cache first: v293_flight_read.extract(prefix, tag) + build_cs_cache(tag, prefix),
     see _build_r76_cache.py; then add it to ROUTES.)

======================================================================================================================
PRE-REGISTERED FAIL / SURPRISE CRITERIA -- written BEFORE any number below was computed (2026-09-30), kept verbatim
======================================================================================================================
 M1 MEASURABLE BAND.  alpha_th (Savitzky-Golay d2/dt2 of the 0x14A angle, 0.1 deg LSB) and alpha_w (SG d/dt of the
    0x18F rate, 0.125 deg/s LSB) are two independent quantisation/differentiation paths to the same quantity.  The
    metric is declared MEASURABLE at frequency f only where, on laterally-engaged hands-off windows, their coherence
    >= 0.90 AND their SG-compensated gain ratio is within 1.00 +- 0.10 AND phase within +-15 deg.  If that band does not
    reach 3 Hz, the 3-8 Hz score is reported on alpha_w ONLY and flagged; if it does not reach 1 Hz: FAIL -- the goal
    metric is not measurable from the angle sensor and the report says so first.
 M2 NULL CONTROL.  The block-shuffled command (5 s blocks permuted inside the same mask) and the time-reversed command
    must give band R2 <= 0.02 (max over the lag scan) and a Welch coherence no larger than 3/n_windows.  A null above
    R2 0.05 = the scorer is biased: FAIL, nothing else is reported until fixed.
 M3 POSITIVE CONTROL.  Synthetic alpha_syn = G*u(t - tau) + n(t), with n = alpha_th - alpha_w (a REAL measured noise
    series from the same route), must return G within 5 %, tau within 10 ms, and R2 within 0.05 of the analytic ceiling
    var(G u_B)/(var(G u_B)+var(n_B)).  Else FAIL.
 M4 CLOSED-LOOP BIAS.  cmd -> alpha measured by H1 is biased if disturbances on the wheel feed back into the command
    through the fork.  Cross-check with the instrument-variable estimate (reference = controlsState desiredLateralAccel):
    where coh(r,u) >= 0.3 the IV |H| must lie within the H1 bootstrap CI x/÷ 1.25.  If it does not, the H1 number at
    that frequency is reported as BIASED and the IV one is carried instead.
 M5 SURPRISE (not FAIL): the torque->alpha plant (427 tap -> alpha, via the command as instrument) should be the SAME car
    on V293 and V294 (the tap is the actual lane torque on both).  A >x1.5 disagreement in 1-5 Hz is a surprise to explain
    (another torque source, a wrong tap scale, or the trim not being what the tap reports).
 PREDICTION (BELIEF, written before): the V294 trim resists wheel acceleration (T_trim = -0.21 counts per deg/s^2 through
    a 2.03 Hz + 5.05 Hz lag, measured by the extract agent), so V294's cmd -> alpha GAIN should be LOWER than V293's by
    1/|1 + 0.21 L(f) P(f)| (P = measured tap->alpha plant), most at 0.5-2 Hz, with the wheel-mode peak flattened.  A
    HIGHER gain on V294 would contradict the trim's measured sign.

======================================================================================================================
DECLARED AFTER THE FIRST RUN (post-hoc; each change is a correction forced by a measurement, and is reported as such)
======================================================================================================================
 P1 HANDS-OFF MASK.  The kit's |bar| < 400 hands-off mask is NOT used for the metric: hands-off, the 0x18F driver-torque
    sensor reads the wheel's own inertia (bar ~ 0.4-0.55 counts per deg/s^2), so the mask removes exactly the high-
    acceleration frames (|alpha| p90 75 vs 716 deg/s^2 on r71b).  Hands-off = openpilot's own steeringPressed is FALSE
    (dilated +-0.5 s).  The |bar| mask is printed as a sensitivity row.
 P2 KAPPA.  d(0x14A angle)/dt vs the 0x18F rate is NOT 1: it is 1.16 within +-20 deg of centre and 0.965 beyond 80 deg on
    every route (a variable-ratio rack signature: the rate is motor-side).  M1 is scored AS WRITTEN and ADJUDICATED
    (gain flat within +-10 % of the low-frequency kappa).  The positive control's noise is n = alpha_th - kappa*alpha_w.
 P3 CLOSED LOOP.  The command's 1-8 Hz content is mostly the fork's P term (R2 0.86-0.96 on V293/V294 routes), and the
    best lag in 1-8 Hz is NEGATIVE (the wheel's acceleration LEADS the command).  So the literal metric (H1 and the
    lag-scan R2) mixes "the wheel follows the command" with "the command follows the wheel".  The firmware-attributable
    ACTUATOR branch is estimated by IV (instrument = desiredLateralAccel, exogenous to the wheel's 1-8 Hz motion --
    BELIEF) wherever coh(r,u) >= 0.3 (M4's threshold), and the command decomposition is printed.
 P4 BAND FITS.  A single scaled-and-delayed command cannot represent a +90..+120 deg phase (the spring band): the lag scan
    runs into its edge there.  A GAIN-PHASE fit (u and its Hilbert quadrature) is carried beside the lag scan.
 P5 JOINT REGRESSION.  Only the broadband (0-8 Hz) form is reported: inside one narrow band alpha ~ -(2 pi f)^2 theta, so J
    and k are not separately identifiable there (the per-band fits returned sign-flipping J and k).
 PC2.  A second positive control uses the measured noise BLOCK-SHUFFLED (same spectrum, independent of u); PC1's measured
    noise is partly correlated with u through the angle-dependent kappa.

SIGN CONVENTION (everything + = LEFT, deg):  u = -0xE4 STEER_TORQUE (the command, counts; +cmd = steer right);
    theta = 0x14A STEER_ANGLE (x-0.1, + left); omega = -0x18F raw rate / 8 (deg/s, + left; x = 8 counts per deg/s);
    T = -tap (0x1AB, sign(tap) = +sign(cmd)); sp = map(cmd) with the sign of u; alpha = d omega/dt = d2 theta/dt2.
    The ideal of the goal: alpha = G * u with G > 0, flat gain, zero phase.
TIMING: every stream is put back on its own nominal frame counter (creep20_loop_id.dejitter, as every census does);
    the command is sampled ZERO-ORDER-HOLD at the 0x18F frame instants (the ECU holds a command between frames).  Check:
    on V293 (r70) the 427 tap lags the command by +30 ms at r 0.986 in 1-8 Hz = the 5 Hz output lag -- the time base is
    causal and consistent.  Residual TX-echo vs RX latency offset: BELIEF < 5 ms.
BOOTSTRAP: 60 s blocks of route time (the rlog segment size) resampled with replacement.
"""
import json
import os
import sys
import time

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
OUT = os.path.join(HERE, "out")
V280 = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
CSC = os.path.join(KIT, "rlog-tools", "studies", "grind", "_scratch")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import io, contextlib  # noqa: E401,E402
with contextlib.redirect_stdout(io.StringIO()):
    import creep20_loop_id as C20          # noqa: E402  dejitter()
    import grind_incident_r35 as GI        # noqa: E402  demand_live()
    import v293_flight_read as FR          # noqa: E402  cells_for(), fade_multiplier(), L.surface()

FS = 100.0
DT = 1.0 / FS
SG_TH = (21, 5)          # alpha_th: SG deriv 2 on the angle   (flat within 1 % to 2 Hz, -1.7 % at 3 Hz, -3 dB 6.8 Hz)
SG_W = (9, 3)            # alpha_w : SG deriv 1 on the rate    (flat within 1 % to 5 Hz, -3.7 % at 8 Hz, -3 dB 14.6 Hz)
VBANDS = [("0-5", 0.0, 5.0), ("5-10", 5.0, 10.0), ("10-15", 10.0, 15.0), ("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)]
FBANDS = [("0.3-1", 0.3, 1.0), ("1-3", 1.0, 3.0), ("3-8", 3.0, 8.0)]
BROAD = ("0.3-8", 0.3, 8.0)
NPS = 512                # Welch window 5.12 s (df 0.195 Hz)
STEP = 256
BAR_OFF = 400.0
HANDS_DILATE_S = 0.5
LAGS_MS = np.arange(-100, 310, 10)
NBOOT = 300
SEED = 20260930
IV_COH = 0.3

ROUTES = {
    "r71b_v294": dict(route="75604b0a432fdc89_00000071--a7b8ba5d9d", build="V294", cells="V293", group="V294",
                      fork="Dom 20d24ab79 r1: generic torque ctl, Kp 0.9 Ki 0.3 LAF 14 fric 0.011, VSR map"),
    "r70_v293": dict(route="75604b0a432fdc89_00000070--717f5a7866", build="V293", cells="V293", group="V293",
                     fork="4247cb09e rev 1: generic torque, Kp 0.3 Ki 0.15 LAF 6, fric 0"),
    "r75_v293r4": dict(route="75604b0a432fdc89_00000075--6c8687d5bd", build="V293", cells="V293", group="V293",
                       fork="08a5a7064 rev 4: plant FF + hold map, Kp 0.85 Ki 0.6/2.5 LAF 14, rate loop, notch"),
    "r76_v293r5": dict(route="75604b0a432fdc89_00000076--d0b7ea7e4d", build="V293", cells="V293", group="V293",
                       fork="e44b6cd31 rev 5: plant FF + DOB 0.6, Kp 1.0 Ki 0.3 LAF 14"),
    "r6c": dict(route="75604b0a432fdc89_0000006c--2bc842dbac", build="V282", cells="V282", group="V282",
                fork="57410c3b: rate-plant FF, Kp 0.9 LAF 6 (rate-servo EPS)"),
    "r39": dict(route="75604b0a432fdc89_00000039--f56039af87", build="V282", cells="V282", group="V282",
                fork="8a28dcef: Kp 0.8 LAF 2.11 (rate-servo EPS)"),
    "r6d_v292": dict(route="75604b0a432fdc89_0000006d--5e7b4d2ceb", build="V292", cells="V292", group="V292",
                     fork="V292 flight (rate-servo class + error-feedback cave)"),
}
DEFAULT = ["r71b_v294", "r70_v293", "r75_v293r4", "r76_v293r5", "r6c", "r39", "r6d_v292"]
OUTBUF = []


def pr(s=""):
    print(s)
    OUTBUF.append(s)


# ======================================================================================================================
# 1. THE GRID -- identical for every route
# ======================================================================================================================
def _fill(k, x, K):
    g = np.full(K + 1, np.nan)
    g[k] = x
    have = ~np.isnan(g)
    g[~have] = np.interp(np.flatnonzero(~have), np.flatnonzero(have), g[have])
    return g, have


def build_grid(tag):
    R = ROUTES[tag]
    D = dict(np.load(os.path.join(V280, tag + ".npz")))
    k18, P18, tn18, _ = C20.dejitter(D["t18"], 0.01, 100)
    K = int(k18[-1])
    t = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18
    g = dict(tag=tag, t=t, tr=t - t[0])
    wire, have = _fill(k18, D["rate"].astype(float), K)
    g["have"] = have
    g["omega"] = -wire / 8.0                                   # deg/s, + left  (x = -wire, 8 counts per deg/s)
    g["bar"], _ = _fill(k18, D["tq"].astype(float) * 1.024, K)
    sca, _ = _fill(k18, D["sca"].astype(float), K)
    # angle on its OWN frame counter, then the nearest nominal sample (keeps the 0.1 deg quantisation intact)
    k14, P14, tn14, _ = C20.dejitter(D["t14"], 0.01, 100)
    a14, _ = _fill(k14, D["ang"].astype(float), int(k14[-1]))
    t14n = np.interp(np.arange(int(k14[-1]) + 1), k14, tn14)
    j = np.clip(np.searchsorted(t14n, t), 1, len(t14n) - 1)
    j = np.where(np.abs(t14n[j - 1] - t) < np.abs(t14n[j] - t), j - 1, j)
    g["theta"] = a14[j]
    g["theta_dt_ms"] = float(np.median(np.abs(t14n[j] - t)) * 1e3)
    # command: panda TX-echo on its own counter, ZERO-ORDER HOLD at the 0x18F instants
    ke4, Pe4, tne4, _ = C20.dejitter(D["te4"], 0.01, 100)
    je = np.searchsorted(tne4, t, side="right") - 1
    ok = je >= 0
    je = np.clip(je, 0, len(tne4) - 1)
    cmd = np.where(ok, D["cmd"].astype(float)[je], 0.0)
    g["cmd"] = cmd
    g["u"] = -cmd                                              # + left
    g["req"] = np.where(ok, D["req"][je], 0) > 0
    g["vego"] = np.interp(t, D["tcs"], D["vego"])
    if "cs_press" in D:
        jc = np.clip(np.searchsorted(D["tcs"], t, side="right") - 1, 0, len(D["tcs"]) - 1)
        g["pressed"] = D["cs_press"][jc] > 0
        g["pressed_src"] = "v280 cache carState.steeringPressed"
    else:   # older v280 caches carry no carState flags; the v282ref cache has steeringPressed on the same mono clock
        rp = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v282ref", R["route"].split("_")[1] + ".npz")
        Z = np.load(rp)
        jj = np.clip(np.searchsorted(Z["t_cst"], t, side="right") - 1, 0, len(Z["t_cst"]) - 1)
        g["pressed"] = Z["spress"][jj] > 0.5
        g["pressed_src"] = "v282ref cache carState.steeringPressed"
    # 427 tap (50 Hz) on its own counter, linearly interpolated (spectra: <= 10 Hz, cos^2 up-sampling roll-off undone)
    k1, P1, tn1, _ = C20.dejitter(D["t1ab"], 0.02, 50)
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8.0
    g["T"] = -np.interp(t, tn1, Tm)                            # + left
    g["eng"] = (sca > 0.5) & g["req"] & have
    # setpoint and FF torque from the IMAGE cells (map, fade) -- the delivered surface with zero feedback
    c = FR.cells_for(R["cells"])
    idx, sgn = GI.demand_live(np.round(cmd), g["bar"], c)
    idx = np.round(idx)
    g["sp"] = sgn * np.interp(idx, c["map_X"], c["map_Y"])     # sgn = +1 for a LEFT command (cmd < 0)
    m = FR.fade_multiplier(c, g["bar"], g["vego"], "bar")
    S = FR.L.surface(c, idx, fb=0.0, fade=m)
    g["Tff"] = sgn * np.abs(S["T"]) * g["eng"]
    # control path (instrument + decomposition): desiredLateralAccel, actualLateralAccel, P term, output
    csp = os.path.join(CSC, "cs_%s.npz" % tag)
    if os.path.exists(csp):
        C = np.load(csp)
        tc = C["t_cs"]
        for nm in ("la_des", "la_act", "p", "i", "f", "out", "err"):
            g["cs_" + nm] = np.interp(t, tc, np.nan_to_num(C[nm]))
        ok_ = (np.abs(C["err"]) > 0.05) & (C["active"] > 0.5)
        g["kp_read"] = float(np.median(C["p"][ok_] / C["err"][ok_])) if ok_.sum() > 100 else float("nan")
        g["la_des"] = g["cs_la_des"]
    # differentiators
    g["alpha_th"] = signal.savgol_filter(g["theta"], SG_TH[0], SG_TH[1], deriv=2, delta=DT)
    g["alpha_w"] = signal.savgol_filter(g["omega"], SG_W[0], SG_W[1], deriv=1, delta=DT)
    g["omega_th"] = signal.savgol_filter(g["theta"], SG_TH[0], SG_TH[1], deriv=1, delta=DT)
    # HANDS-OFF = openpilot's own steeringPressed FALSE (dilated +-0.5 s) -- see P1
    nd = int(HANDS_DILATE_S * FS)
    hon_d = np.convolve(g["pressed"].astype(float), np.ones(2 * nd + 1), "same") > 0
    g["HO"] = g["eng"] & ~hon_d
    g["HN"] = g["eng"] & g["pressed"]
    barhi = np.convolve((np.abs(g["bar"]) >= BAR_OFF).astype(float), np.ones(2 * nd + 1), "same") > 0
    g["HObar"] = g["HO"] & ~barhi
    g["blk"] = (g["tr"] // 60.0).astype(int)
    return g


# ======================================================================================================================
# 2. DIFFERENTIATOR RESPONSES
# ======================================================================================================================
def sg_response(L, p, d, f):
    h = signal.savgol_coeffs(L, p, deriv=d, delta=DT, use="conv")
    n = np.arange(L) - (L - 1) // 2
    w = 2 * np.pi * np.asarray(f, float)
    H = np.array([np.sum(h * np.exp(-1j * wi * n * DT)) for wi in w])
    ideal = (1j * w) ** d
    with np.errstate(invalid="ignore", divide="ignore"):
        R = np.real(H / ideal)
    R[w == 0] = 1.0
    return R, float(np.sqrt(np.sum(h ** 2)))


def comp_factor(f, which):
    if which == "alpha_th":
        return sg_response(SG_TH[0], SG_TH[1], 2, f)[0]
    if which in ("alpha_w", "alpha_syn"):
        return sg_response(SG_W[0], SG_W[1], 1, f)[0]
    if which == "T":
        return np.cos(np.pi * np.asarray(f) / 100.0) ** 2         # the 50 Hz tap's linear up-sampling
    return np.ones(len(f))


# ======================================================================================================================
# 3. WINDOWS and cross-spectra
# ======================================================================================================================
def runs(mask, min_len):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= min_len]


def bp(x, f1, f2, order=4):
    sos = signal.butter(order, [f1, f2], "bandpass", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def lp(x, fc=8.0, order=4):
    sos = signal.butter(order, fc, "lowpass", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x)


def shift(x, k):
    """x(t - k samples), zero-filled."""
    out = np.zeros_like(x)
    if k > 0:
        out[k:] = x[:-k]
    elif k < 0:
        out[:k] = x[-k:]
    else:
        out[:] = x
    return out


def windows(g):
    W = []
    ub = np.zeros(len(g["t"]))
    for a, b in runs(g["eng"], 3 * NPS // 2):
        ub[a:b] = bp(g["u"][a:b], BROAD[1], BROAD[2])
    for a, b in runs(g["HO"], NPS):
        for s in range(a, b - NPS + 1, STEP):
            sl = slice(s, s + NPS)
            W.append(dict(s=s, v=float(g["vego"][sl].mean()), amp=float(np.sqrt(np.mean(ub[sl] ** 2))),
                          absu=float(np.median(np.abs(g["u"][sl]))), blk=int(g["blk"][s + NPS // 2]),
                          tr=float(g["tr"][s])))
    return W


def window_ffts(g, W, chans):
    win = signal.windows.hann(NPS, sym=False)
    f = np.fft.rfftfreq(NPS, DT)
    F = {}
    for c in chans:
        if c not in g:
            continue
        x = g[c]
        A = np.empty((len(W), len(f)), complex)
        for i, w in enumerate(W):
            A[i] = np.fft.rfft(signal.detrend(x[w["s"]:w["s"] + NPS], type="linear") * win)
        F[c] = A
    return f, F


def xspec(F, sel, a, b):
    Sab = np.mean(np.conj(F[a][sel]) * F[b][sel], axis=0)
    Saa = np.mean(np.abs(F[a][sel]) ** 2, axis=0)
    Sbb = np.mean(np.abs(F[b][sel]) ** 2, axis=0)
    return Sab, Saa, Sbb


def tf(F, sel, a, b):
    Sab, Saa, Sbb = xspec(F, sel, a, b)
    return Sab / Saa, np.abs(Sab) ** 2 / (Saa * Sbb)


def tf_boot(F, W, sel_idx, a, b, rng, nboot=NBOOT, iv=None):
    """H1 (or the IV estimate S_rb / S_ra) with 60 s block-bootstrap percentiles on |H| and on the phase."""
    sel_idx = np.asarray(sel_idx)
    blks = np.array([W[i]["blk"] for i in sel_idx])
    ub = np.unique(blks)
    by = {k: sel_idx[blks == k] for k in ub}

    def est(ix):
        if iv is None:
            return tf(F, ix, a, b)[0]
        return np.mean(np.conj(F[iv][ix]) * F[b][ix], 0) / np.mean(np.conj(F[iv][ix]) * F[a][ix], 0)

    H0 = est(sel_idx)
    Hb = [est(np.concatenate([by[k] for k in rng.choice(ub, len(ub), replace=True)])) for _ in range(nboot)] \
        if (len(ub) >= 2 and nboot > 0) else [H0]
    Hb = np.array(Hb)
    ph = np.angle(Hb * np.conj(H0)[None, :])
    return dict(H=H0, lo=np.percentile(np.abs(Hb), 2.5, 0), hi=np.percentile(np.abs(Hb), 97.5, 0),
                ph_lo=np.angle(H0) + np.percentile(ph, 2.5, 0), ph_hi=np.angle(H0) + np.percentile(ph, 97.5, 0),
                nblk=len(ub))


# ======================================================================================================================
# 4. TIME-DOMAIN BAND SCORES
# ======================================================================================================================
def band_signals(g, f1, f2, chans, hilb=()):
    """band-pass each channel inside every laterally-engaged run; Hilbert quadrature for `hilb`; edges trimmed."""
    edge = int(max(2.0, 1.5 / f1) * FS)
    out = {c: np.zeros(len(g["t"])) for c in chans}
    for c in hilb:
        out["H" + c] = np.zeros(len(g["t"]))
    valid = np.zeros(len(g["t"]), bool)
    for a, b in runs(g["eng"], 2 * edge + NPS):
        for c in chans:
            out[c][a:b] = bp(g[c][a:b], f1, f2)
        for c in hilb:
            out["H" + c][a:b] = np.imag(signal.hilbert(out[c][a:b]))
        valid[a + edge:b - edge] = True
    return out, valid


def lag_stats(y, x, sel, blk, lags_ms=LAGS_MS):
    n = len(y)
    ub = np.unique(blk[sel])
    bi = np.searchsorted(ub, np.clip(blk, ub[0], ub[-1]))
    S = np.zeros((3, len(lags_ms), len(ub)))
    for li, lm in enumerate(lags_ms):
        k = int(round(lm / 10.0))
        xs = shift(x, k)
        ok = sel & shift(sel.astype(float), k).astype(bool)
        S[0, li] = np.bincount(bi[ok], weights=(xs * y)[ok], minlength=len(ub))
        S[1, li] = np.bincount(bi[ok], weights=(xs * xs)[ok], minlength=len(ub))
        S[2, li] = np.bincount(bi[ok], weights=(y * y)[ok], minlength=len(ub))
    return S, ub


def lag_score(S, cols=None, lags_ms=LAGS_MS):
    if cols is not None:
        S = S[:, :, cols]
    sxy, sxx, syy = S.sum(2)
    with np.errstate(invalid="ignore", divide="ignore"):
        G = sxy / sxx
        R2 = sxy ** 2 / (sxx * syy)
    i = int(np.nanargmax(R2))
    return dict(R2=float(R2[i]), G=float(G[i]), lag_ms=float(lags_ms[i]),
                edge=bool(i == 0 or i == len(lags_ms) - 1))


def gp_stats(y, x, hx, sel, blk):
    ub = np.unique(blk[sel])
    bi = np.searchsorted(ub, np.clip(blk, ub[0], ub[-1]))
    terms = (x * x, hx * hx, x * hx, y * x, y * hx, y * y)
    S = np.array([np.bincount(bi[sel], weights=t_[sel], minlength=len(ub)) for t_ in terms])
    return S, ub


def gp_score(S, fc, cols=None):
    if cols is not None:
        S = S[:, cols]
    uu, hh, uh, au, ah, aa = S.sum(1)
    M_ = np.array([[uu, uh], [uh, hh]])
    a, b = np.linalg.solve(M_, [au, ah])
    R2 = (a * au + b * ah) / aa
    A = float(np.hypot(a, b))
    ph = float(np.degrees(np.arctan2(-b, a)))              # + = alpha LEADS u
    return dict(R2=float(R2), gain=A, phase_deg=ph, eq_delay_ms=float(-ph / 360.0 / fc * 1e3))


TRIM_BETA = 0.21          # T counts per deg/s^2 of the lagged operand, the extract agent's pooled E3 on r71b (EVIDENCE there)
TRIM_POLES = (2.033, 5.05)  # the fb-lag pole (0xC63E8 = 1011) and the output lag (992/507), Hz, from the V294 image


def trim_design(fc):
    L = 1.0 / (1 + 1j * fc / TRIM_POLES[0]) / (1 + 1j * fc / TRIM_POLES[1])
    K = -TRIM_BETA * L                        # + left convention: the trim OPPOSES the wheel's acceleration
    return dict(mag=float(abs(K)), phase_deg=float(np.degrees(np.angle(K))))


def trim_footprint(T, Tff, HTff, a, Ha, sel, blk, rng, nboot=200):
    """T_B = c1 Tff_B + c2 H[Tff_B] + k1 alpha_B + k2 H[alpha_B]: the delivered torque split into the byte-exact
    feedforward of the command and a term in the wheel's acceleration (the V294 trim; exactly zero on V293)."""
    X = np.column_stack([Tff, HTff, a, Ha])
    ub = np.unique(blk[sel])
    bi = np.searchsorted(ub, np.clip(blk, ub[0], ub[-1]))
    XX = np.zeros((len(ub), 4, 4))
    Xy = np.zeros((len(ub), 4))
    yy = np.zeros(len(ub))
    for j in range(4):
        Xy[:, j] = np.bincount(bi[sel], weights=(X[:, j] * T)[sel], minlength=len(ub))
        for k in range(4):
            XX[:, j, k] = np.bincount(bi[sel], weights=(X[:, j] * X[:, k])[sel], minlength=len(ub))
    yy[:] = np.bincount(bi[sel], weights=(T * T)[sel], minlength=len(ub))

    def solve(cols):
        c = np.linalg.solve(XX[cols].sum(0), Xy[cols].sum(0))
        return c
    c = solve(np.arange(len(ub)))
    Km = float(np.hypot(c[2], c[3]))
    Kp = float(np.degrees(np.arctan2(-c[3], c[2])))
    trim_part = (X[:, 2:] @ c[2:])[sel]
    ff_part = (X[:, :2] @ c[:2])[sel]
    resid = T[sel] - ff_part - trim_part
    boots = []
    if len(ub) >= 2:
        for _ in range(nboot):
            cc = solve(rng.choice(len(ub), len(ub), replace=True))
            boots.append((np.hypot(cc[2], cc[3]), np.degrees(np.arctan2(-cc[3], cc[2]))))
    boots = np.array(boots) if boots else np.array([(Km, Kp)])
    ffm = float(np.hypot(c[0], c[1]))
    return dict(K_mag=Km, K_phase_deg=Kp, K_ci=[float(np.percentile(boots[:, 0], 2.5)), float(np.percentile(boots[:, 0], 97.5))],
                ff_gain=ffm, ff_phase_deg=float(np.degrees(np.arctan2(-c[1], c[0]))),
                rms_T=float(np.std(T[sel])), rms_ff=float(np.std(ff_part)), rms_trim=float(np.std(trim_part)),
                rms_resid=float(np.std(resid)), R2=float(1 - np.var(resid) / np.var(T[sel])), sec=float(sel.sum() / FS))


def band_score(y, x, hx, sel, blk, rng, fc, nboot=NBOOT):
    S, ub = lag_stats(y, x, sel, blk)
    s0 = lag_score(S)
    Sg, _ = gp_stats(y, x, hx, sel, blk)
    s0["gp"] = gp_score(Sg, fc)
    bs, bg = [], []
    if len(ub) >= 2:
        for _ in range(nboot):
            cols = rng.choice(len(ub), len(ub), replace=True)
            b = lag_score(S, cols)
            bs.append((b["R2"], b["G"], b["lag_ms"]))
            q = gp_score(Sg, fc, cols)
            bg.append((q["R2"], q["gain"], q["phase_deg"]))
    if bs:
        bs, bg = np.array(bs), np.array(bg)
        pc = lambda a_: [float(np.percentile(a_, 2.5)), float(np.percentile(a_, 97.5))]  # noqa: E731
        s0.update(R2_ci=pc(bs[:, 0]), G_ci=pc(bs[:, 1]), lag_ci=pc(bs[:, 2]))
        s0["gp"].update(R2_ci=pc(bg[:, 0]), gain_ci=pc(bg[:, 1]), phase_ci=pc(bg[:, 2]))
    s0.update(n=int(sel.sum()), sec=float(sel.sum() / FS), nblk=len(ub))
    return s0


def block_shuffle_idx(sel, rng, L=500):
    idx = np.flatnonzero(sel)
    nb = len(idx) // L
    if nb < 2:
        return None
    blocks = [idx[i * L:(i + 1) * L] for i in range(nb)]
    perm = rng.permutation(nb)
    for i in range(nb):
        if perm[i] == i:
            j_ = (i + 1) % nb
            perm[i], perm[j_] = perm[j_], perm[i]
    return blocks, perm


def apply_shuffle(x, bp_):
    out = np.zeros_like(x)
    if bp_ is None:
        return out
    blocks, perm = bp_
    for i in range(len(blocks)):
        out[blocks[i]] = x[blocks[perm[i]]]
    return out


def reverse_in_runs(x, mask):
    out = x.copy()
    for a, b in runs(mask, 2):
        out[a:b] = x[a:b][::-1]
    return out


# ======================================================================================================================
# 5. JOINT REGRESSION (broadband): u(t) ~ J alpha + b omega + k theta + F tanh(omega/2) + c
# ======================================================================================================================
def joint_regression(u, al, om, th, sel, blk, rng, lag_ms, nboot=200, fric_w=2.0):
    k = int(round(lag_ms / 10.0))
    n = len(u)
    A, O, Th = al[k:], om[k:], th[k:]
    U, S, B = u[:n - k], sel[:n - k] & sel[k:], blk[:n - k]
    X = np.column_stack([A, O, Th, np.tanh(O / fric_w), np.ones(len(A))])[S]
    y = U[S]
    Bs = B[S]
    fit = lambda ix: np.linalg.lstsq(X[ix], y[ix], rcond=None)[0]  # noqa: E731
    cf = fit(np.arange(len(y)))
    vu = np.var(y)
    terms = dict(J=X[:, 0] * cf[0], b=X[:, 1] * cf[1], k=X[:, 2] * cf[2], F=X[:, 3] * cf[3])
    share = {nm: float(np.var(v) / vu) for nm, v in terms.items()}
    R2 = float(1 - np.var(y - X @ cf) / vu)
    uniq = {}
    for j, nm in enumerate(("J", "b", "k", "F")):
        cols = [c for c in range(5) if c != j]
        c2 = np.linalg.lstsq(X[:, cols], y, rcond=None)[0]
        uniq[nm] = float(R2 - (1 - np.var(y - X[:, cols] @ c2) / vu))
    ub = np.unique(Bs)
    by = {b_: np.flatnonzero(Bs == b_) for b_ in ub}
    boots = [fit(np.concatenate([by[b_] for b_ in rng.choice(ub, len(ub), replace=True)])) for _ in range(nboot)] \
        if len(ub) >= 2 and nboot else [cf]
    ci = np.percentile(np.array(boots), [2.5, 97.5], axis=0)
    return dict(coef=dict(J=cf[0], b=cf[1], k=cf[2], F=cf[3], c=cf[4]),
                ci={nm: [float(ci[0, j]), float(ci[1, j])] for j, nm in enumerate(("J", "b", "k", "F", "c"))},
                share=share, unique=uniq, R2=R2, n=int(len(y)), sec=float(len(y) / FS), nblk=len(ub),
                std=dict(u=float(np.std(y)), alpha=float(np.std(X[:, 0])), omega=float(np.std(X[:, 1])),
                         theta=float(np.std(X[:, 2]))))


# ======================================================================================================================
# 6. PER-ROUTE PIPELINE
# ======================================================================================================================
def fsel(f, lo, hi):
    return (f >= lo) & (f <= hi)


def analyse_route(tag, rng):
    t0 = time.time()
    g = build_grid(tag)
    R = ROUTES[tag]
    res = dict(tag=tag, route=R["route"], build=R["build"], group=R["group"], fork=R["fork"],
               kp_read=g.get("kp_read"), has_cs="la_des" in g)
    res["exposure"] = dict(route_s=float(g["tr"][-1]), eng_s=float(g["eng"].sum() / FS), HO_s=float(g["HO"].sum() / FS),
                           HN_s=float(g["HN"].sum() / FS), HObar_s=float(g["HObar"].sum() / FS),
                           pressed_src=g["pressed_src"],
                           HO_by_v={nm: float((g["HO"] & (g["vego"] >= lo) & (g["vego"] < hi)).sum() / FS)
                                    for nm, lo, hi in VBANDS},
                           theta_nearest_dt_ms=g["theta_dt_ms"])
    W = windows(g)
    for w in W:
        w["vb"] = next((nm for nm, lo, hi in VBANDS if lo <= w["v"] < hi), None)
    for nm, lo, hi in VBANDS:
        ix = [i for i, w in enumerate(W) if w["vb"] == nm]
        if len(ix) >= 6:
            q1, q2 = np.percentile([W[i]["amp"] for i in ix], [100 / 3, 200 / 3])
            for i in ix:
                W[i]["ter"] = 0 if W[i]["amp"] < q1 else (1 if W[i]["amp"] < q2 else 2)
        else:
            for i in ix:
                W[i]["ter"] = -1
    res["n_windows_HO"] = len(W)
    groups = {"all": list(range(len(W)))}
    for nm, lo, hi in VBANDS:
        groups["v" + nm] = [i for i, w in enumerate(W) if w["vb"] == nm]
        for tt in range(3):
            groups["v%s/t%d" % (nm, tt)] = [i for i, w in enumerate(W) if w["vb"] == nm and w.get("ter") == tt]
    f, F = window_ffts(g, W, ("u", "sp", "T", "Tff", "theta", "alpha_th", "alpha_w", "la_des", "cs_p"))
    # ---------------- M1: instrument agreement alpha_th vs alpha_w
    ag = {}
    sel = np.array(groups["all"])
    H, coh = tf(F, sel, "alpha_w", "alpha_th")
    with np.errstate(invalid="ignore", divide="ignore"):
        Hc = H * comp_factor(f, "alpha_w") / comp_factor(f, "alpha_th")
    Sab, Saa, Sbb = xspec(F, sel, "alpha_w", "alpha_th")
    win_pow = np.mean(signal.windows.hann(NPS, sym=False) ** 2) * NPS
    ag.update(f=f, gain=np.abs(Hc), ph=np.degrees(np.angle(Hc)), coh=coh, S_th=Sbb, S_w=Saa, N_th=Sbb * (1 - coh),
              N_w_model=(0.125 ** 2 / 12.0) * win_pow * np.abs(sg_response(SG_W[0], SG_W[1], 1, f)[0] * 2 * np.pi * f) ** 2,
              N_th_model=(0.1 ** 2 / 12.0) * win_pow * np.abs(sg_response(SG_TH[0], SG_TH[1], 2, f)[0] *
                                                            (2 * np.pi * f) ** 2) ** 2)
    kappa = float(np.median(np.abs(Hc[fsel(f, 0.35, 1.05)])))
    ag["kappa"] = kappa
    for nm, gref in (("band_as_written", 1.0), ("band_adjudicated", kappa)):
        ok = (coh >= 0.90) & (np.abs(np.abs(Hc) / gref - 1) <= 0.10) & (np.abs(np.degrees(np.angle(Hc))) <= 15) & (f > 0.15)
        band = None
        okr = runs(ok, 1)
        for a, b in okr:
            if f[a] <= 1.0 <= f[b - 1]:
                band = (float(f[a]), float(f[b - 1]))
        ag[nm] = band
    L = 50
    cwi = np.cumsum(g["omega"]) * DT
    da, di = g["theta"][L:] - g["theta"][:-L], cwi[L:] - cwi[:-L]
    thm = np.abs(0.5 * (g["theta"][L:] + g["theta"][:-L]))
    ag["kappa_by_angle"] = [dict(lo=lo, hi=hi, n=int(m.sum()), ratio=float(np.sum(da[m] * di[m]) / np.sum(di[m] ** 2)))
                            for lo, hi in [(0, 5), (5, 10), (10, 20), (20, 40), (40, 80), (80, 160), (160, 320), (320, 700)]
                            for m in [(thm >= lo) & (thm < hi) & (np.abs(di) > 0.2)] if m.sum() > 200]
    g["n_meas"] = g["alpha_th"] - kappa * g["alpha_w"]
    ag["alpha_rms_HO"] = dict(alpha_th=float(np.std(g["alpha_th"][g["HO"]])), alpha_w=float(np.std(g["alpha_w"][g["HO"]])),
                              diff=float(np.std(g["n_meas"][g["HO"]])))
    m = g["HO"]
    X = np.column_stack([lp(g["alpha_w"]), g["omega"], g["theta"], g["u"], np.ones(len(g["u"]))])[m]
    cf = np.linalg.lstsq(X, g["bar"][m], rcond=None)[0]
    al_ = np.abs(lp(g["alpha_w"]))
    hi_ = m & (np.abs(g["bar"]) >= 400)
    ag["bar_on_alpha"] = dict(coef_alpha=float(cf[0]), R2=float(1 - np.var(g["bar"][m] - X @ cf) / np.var(g["bar"][m])),
                              alpha_p90_bar_lt400=float(np.percentile(al_[m & (np.abs(g["bar"]) < 400)], 90)),
                              alpha_p90_bar_ge400=float(np.percentile(al_[hi_], 90)) if hi_.sum() > 50 else float("nan"),
                              frac_bar_ge400=float(np.mean(np.abs(g["bar"][m]) >= 400)))
    res["agreement"] = ag
    # spectral positive control: alpha_syn = Gc u(t - 80 ms) + block-shuffled measured noise
    Hu, _ = tf(F, sel, "u", "alpha_th")
    Gc = float(np.median(np.abs(Hu[fsel(f, 1.0, 3.0)])))
    shuf = block_shuffle_idx(g["HO"], rng)
    g["n_shuf"] = apply_shuffle(g["n_meas"], shuf)
    g["alpha_syn"] = Gc * shift(g["u"], 8) + g["n_shuf"]
    _, Fs = window_ffts(g, W, ("u", "alpha_syn"))
    Hs, cs_ = tf(Fs, sel, "u", "alpha_syn")
    res["spec_posctl"] = dict(Gc=Gc, f=f, ratio=np.abs(Hs) / Gc, ph_err=np.degrees(np.angle(Hs)) + 360 * f * 0.08, coh=cs_)
    # ---------------- transfer functions
    TF = {}
    for gname, ix in groups.items():
        if len(ix) < 4:
            continue
        ixa = np.array(ix)
        row = dict(n=len(ix), sec=float(len(ix) * STEP / FS))
        pairs = [("u", "alpha_th"), ("u", "alpha_w")] + ([("u", "T"), ("sp", "alpha_w")] if "/" not in gname else [])
        for inp, out_ in pairs:
            T_ = tf_boot(F, W, ixa, inp, out_, rng, nboot=(NBOOT if inp == "u" and "/" not in gname else 60))
            comp = comp_factor(f, out_) / comp_factor(f, inp)
            _, coh = tf(F, ixa, inp, out_)
            row["%s>%s" % (inp, out_)] = dict(H=T_["H"] / comp, lo=T_["lo"] / np.abs(comp), hi=T_["hi"] / np.abs(comp),
                                               ph_lo=T_["ph_lo"], ph_hi=T_["ph_hi"], coh=coh, nblk=T_["nblk"])
        Hth, _ = tf(F, ixa, "u", "theta")
        row["u>theta_x_w2"] = dict(H=Hth * (1j * 2 * np.pi * f) ** 2)
        perm = ixa.copy()
        rng.shuffle(perm)
        Sab = np.mean(np.conj(F["u"][perm]) * F["alpha_th"][ixa], axis=0)
        row["null_perm_coh"] = np.abs(Sab) ** 2 / (np.mean(np.abs(F["u"][perm]) ** 2, 0) *
                                                   np.mean(np.abs(F["alpha_th"][ixa]) ** 2, 0))
        if "la_des" in F:
            for inp, out_ in (("u", "alpha_w"), ("u", "alpha_th"), ("T", "alpha_w"), ("u", "T")):
                T_ = tf_boot(F, W, ixa, inp, out_, rng, nboot=(100 if "/" not in gname else 0), iv="la_des")
                comp = comp_factor(f, out_) / comp_factor(f, inp)
                _, cri = tf(F, ixa, "la_des", inp)
                row["iv_%s>%s" % (inp, out_)] = dict(H=T_["H"] / comp, lo=T_["lo"] / np.abs(comp),
                                                     hi=T_["hi"] / np.abs(comp), coh_ri=cri)
        if "cs_p" in F:
            _, row["coh_u_p"] = tf(F, ixa, "cs_p", "u")
        TF[gname] = row
    win = signal.windows.hann(NPS, sym=False)
    urev = reverse_in_runs(g["u"], g["HO"])
    Ur = np.array([np.fft.rfft(signal.detrend(urev[w["s"]:w["s"] + NPS]) * win) for w in W])
    Sab = np.mean(np.conj(Ur) * F["alpha_th"], 0)
    TF["all"]["null_rev_coh"] = np.abs(Sab) ** 2 / (np.mean(np.abs(Ur) ** 2, 0) * np.mean(np.abs(F["alpha_th"]) ** 2, 0))
    res["_f"] = f
    res["_TF"] = TF
    # ---------------- time-domain band scores
    BS = {}
    DEC = {}
    blk = g["blk"]
    Bu, _ = band_signals(g, BROAD[1], BROAD[2], ["u"])
    g["amp_loc"] = np.sqrt(np.convolve(Bu["u"] ** 2, np.ones(NPS) / NPS, "same"))
    dec_ch = [c for c in ("cs_p", "cs_la_des", "cs_la_act", "theta") if c in g]
    for bnm, f1, f2_ in FBANDS + [BROAD]:
        fc = float(np.sqrt(f1 * f2_))
        B, valid = band_signals(g, f1, f2_, ["u", "sp", "T", "Tff", "alpha_th", "alpha_w", "n_meas", "n_shuf"] + dec_ch,
                                hilb=("u", "sp", "T", "Tff", "alpha_w"))
        BS[bnm] = {}
        DEC[bnm] = {}
        for vnm, lo, hi in [("all", 0.0, 99.0)] + VBANDS:
            sel = valid & g["HO"] & (g["vego"] >= lo) & (g["vego"] < hi)
            if sel.sum() < 20 * FS:
                continue
            row = {}
            for out_ in ("alpha_th", "alpha_w"):
                row["u>" + out_] = band_score(B[out_], B["u"], B["Hu"], sel, blk, rng, fc)
            row["sp>alpha_th"] = band_score(B["alpha_th"], B["sp"], B["Hsp"], sel, blk, rng, fc, nboot=0)
            row["T>alpha_th"] = band_score(B["alpha_th"], B["T"], B["HT"], sel, blk, rng, fc, nboot=0)
            sh = block_shuffle_idx(sel, rng)
            row["null_shuffle"] = band_score(B["alpha_th"], apply_shuffle(B["u"], sh), apply_shuffle(B["Hu"], sh),
                                             sel, blk, rng, fc, nboot=0)
            row["null_reverse"] = band_score(B["alpha_th"], reverse_in_runs(B["u"], valid),
                                             -reverse_in_runs(B["Hu"], valid), sel, blk, rng, fc, nboot=0)
            Gm = row["u>alpha_th"]["gp"]["gain"] * np.sign(row["u>alpha_th"]["G"])
            usft = shift(B["u"], 8)
            for pcn, nk in (("posctl", "n_meas"), ("posctl2", "n_shuf")):
                syn = Gm * usft + B[nk]
                pc = band_score(syn, B["u"], B["Hu"], sel, blk, rng, fc, nboot=0)
                s_sig, s_n = np.var((Gm * usft)[sel]), np.var(B[nk][sel])
                pc.update(G_true=float(Gm), tau_true_ms=80.0, R2_ceiling=float(s_sig / (s_sig + s_n)),
                          noise_rms=float(np.sqrt(s_n)))
                row[pcn] = pc
            # the firmware's own footprint on this axis: delivered torque = FF(cmd) + K_alpha * alpha_w (V294 trim)
            row["trim"] = trim_footprint(B["T"], B["Tff"], B["HTff"], B["alpha_w"], B["Halpha_w"], sel, blk, rng)
            row["trim"]["design"] = trim_design(fc)
            # VOID rows (declared post-hoc after the first run): too little exposure, or a null above M2's FAIL line
            nmax = max(row["null_shuffle"]["R2"], row["null_shuffle"]["gp"]["R2"], row["null_reverse"]["R2"],
                       row["null_reverse"]["gp"]["R2"])
            row["null_max"] = float(nmax)
            row["void"] = bool(sel.sum() < 30 * FS or nmax > 0.05)
            row["null_warn"] = bool(0.02 < nmax <= 0.05)
            row["alpha_rms"] = float(np.std(B["alpha_th"][sel]))
            row["alpha_w_rms"] = float(np.std(B["alpha_w"][sel]))
            row["u_rms"] = float(np.std(B["u"][sel]))
            if vnm != "all":
                qs = np.percentile(g["amp_loc"][sel], [100 / 3, 200 / 3])
                row["tercile_edges"] = [float(q) for q in qs]
                for tt in range(3):
                    lo_a = -np.inf if tt == 0 else qs[tt - 1]
                    hi_a = np.inf if tt == 2 else qs[tt]
                    s2 = sel & (g["amp_loc"] >= lo_a) & (g["amp_loc"] < hi_a)
                    if s2.sum() >= 10 * FS:
                        row["t%d" % tt] = band_score(B["alpha_th"], B["u"], B["Hu"], s2, blk, rng, fc, nboot=100)
                        row["t%d_w" % tt] = band_score(B["alpha_w"], B["u"], B["Hu"], s2, blk, rng, fc, nboot=0)
            else:
                sb = valid & g["HObar"]
                if sb.sum() >= 20 * FS:
                    row["HObar_u>alpha_th"] = band_score(B["alpha_th"], B["u"], B["Hu"], sb, blk, rng, fc, nboot=50)
            selN = valid & g["HN"] & (g["vego"] >= lo) & (g["vego"] < hi)
            if selN.sum() >= 10 * FS:
                row["handson_u>alpha_th"] = band_score(B["alpha_th"], B["u"], B["Hu"], selN, blk, rng, fc, nboot=100)
            BS[bnm][vnm] = row
            # command decomposition: how much of u_B is the fork's P term / the reference / the measured angle
            d_ = {}
            for c in dec_ch:
                best = (-1.0, 0)
                for lm in range(-100, 210, 10):
                    k = lm // 10
                    xs = shift(B[c], k)
                    ok = sel & shift(sel.astype(float), k).astype(bool)
                    r = np.corrcoef(B["u"][ok], xs[ok])[0, 1] ** 2
                    if r > best[0]:
                        best = (float(r), lm)
                k = best[1] // 10
                xs = shift(B[c], k)
                ok = sel & shift(sel.astype(float), k).astype(bool)
                d_[c] = dict(R2=best[0], lag_ms=best[1],
                             slope=float(np.sum(B["u"][ok] * xs[ok]) / np.sum(xs[ok] ** 2)))
            if "theta" in d_:
                # if u_B = -K theta_B(t - d) (the fork reacting to the wheel), H1 would read (2 pi f)^2 / K, phase +360 f d
                d_["implied_H_if_feedback"] = float((2 * np.pi * fc) ** 2 / max(abs(d_["theta"]["slope"]), 1e-9))
            DEC[bnm][vnm] = d_
        if bnm == BROAD[0]:
            g["_B_broad"], g["_valid_broad"] = B, valid
    res["band_scores"] = BS
    res["decomposition"] = DEC
    # ---------------- static nonlinearity (0.3-8 Hz band, at the band's best lag)
    NL = {}
    B, valid = g["_B_broad"], g["_valid_broad"]
    edges = np.array([-1600, -800, -500, -300, -200, -120, -60, -25, 25, 60, 120, 200, 300, 500, 800, 1600], float)
    alr = lp(g["alpha_w"])
    for vnm, lo, hi in [("all", 0.0, 99.0)] + VBANDS:
        if vnm not in BS[BROAD[0]]:
            continue
        sel = valid & g["HO"] & (g["vego"] >= lo) & (g["vego"] < hi)
        lag = int(round(BS[BROAD[0]][vnm]["u>alpha_th"]["lag_ms"] / 10))
        us = shift(B["u"], lag)
        ok2 = sel & shift(sel.astype(float), lag).astype(bool)
        rows = []
        for a, b in zip(edges[:-1], edges[1:]):
            mm = ok2 & (us >= a) & (us < b)
            if mm.sum() >= 50:
                al = B["alpha_th"][mm]
                rows.append(dict(lo=float(a), hi=float(b), n=int(mm.sum()), u_med=float(np.median(us[mm])),
                                 a_med=float(np.median(al)), a_q25=float(np.percentile(al, 25)),
                                 a_q75=float(np.percentile(al, 75)), aw_med=float(np.median(B["alpha_w"][mm]))))

        def slope(mm):
            return float(np.sum(us[mm] * B["alpha_w"][mm]) / np.sum(us[mm] ** 2)) if mm.sum() > 50 else float("nan")
        sl = dict(pos=slope(ok2 & (us > 0)), neg=slope(ok2 & (us < 0)), small=slope(ok2 & (np.abs(us) < 100)),
                  mid=slope(ok2 & (np.abs(us) >= 100) & (np.abs(us) < 300)), large=slope(ok2 & (np.abs(us) >= 300)))
        m_raw = g["HO"] & (g["vego"] >= lo) & (g["vego"] < hi)
        ur = shift(g["u"], lag)
        NL[vnm] = dict(lag_ms=lag * 10.0, bins=rows, slopes=sl,
                       raw_slope=float(np.polyfit(ur[m_raw], alr[m_raw], 1)[0]) if m_raw.sum() > 100 else float("nan"),
                       raw_r2=float(np.corrcoef(ur[m_raw], alr[m_raw])[0, 1] ** 2) if m_raw.sum() > 100 else float("nan"),
                       stuck=[dict(lo=a, hi=b, frac=float(np.mean(np.abs(g["omega"][mm]) < 2.0)), n=int(mm.sum()))
                              for a, b in [(0, 25), (25, 60), (60, 120), (120, 250), (250, 5000)]
                              for mm in [ok2 & (np.abs(us) >= a) & (np.abs(us) < b)] if mm.sum() > 50])
    res["nonlinearity"] = NL
    # ---------------- broadband joint regression (spring leak)
    JR = {}
    omp, thp = lp(g["omega"]), lp(g["theta"])
    for vnm, lo, hi in [("all", 0.0, 99.0)] + VBANDS:
        sel = g["HO"] & (g["vego"] >= lo) & (g["vego"] < hi)
        if sel.sum() < 20 * FS:
            continue
        best = max(((lm, joint_regression(g["u"], alr, omp, thp, sel, blk, rng, lm, nboot=0)["R2"])
                    for lm in range(0, 310, 20)), key=lambda z: z[1])
        r = joint_regression(g["u"], alr, omp, thp, sel, blk, rng, best[0], nboot=200)
        r["lag_ms"] = best[0]
        JR[vnm] = r
    res["joint"] = JR
    res["_elapsed_s"] = time.time() - t0
    return res


# ======================================================================================================================
# 7. REPORTING
# ======================================================================================================================
def idx_at(f, f0):
    return int(np.argmin(np.abs(f - f0)))


def print_route(res):
    pr("=" * 130)
    pr("%s  (%s)  EPS %s  |  fork: %s  |  Kp read p/err %.3f" % (res["tag"], res["route"], res["build"], res["fork"],
                                                                 res["kp_read"] if res["kp_read"] else float("nan")))
    e = res["exposure"]
    pr("  exposure: route %.0f s | laterally engaged %.0f s | HANDS-OFF engaged (not steeringPressed +-0.5 s) %.0f s | "
       "hands-on %.0f s | kit |bar|<400 mask %.0f s   [pressed: %s]"
       % (e["route_s"], e["eng_s"], e["HO_s"], e["HN_s"], e["HObar_s"], e["pressed_src"]))
    pr("  hands-off by speed band: " + "  ".join("%s %.0f s" % (k, v) for k, v in e["HO_by_v"].items()))
    ag = res["agreement"]
    f = np.asarray(ag["f"])
    pr("  M1 INSTRUMENT AGREEMENT alpha_th (angle d2/dt2) vs alpha_w (0x18F rate d/dt), SG-compensated, %d hands-off windows:"
       % res["n_windows_HO"])
    for f0 in (0.4, 0.6, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 15):
        i = idx_at(f, f0)
        snr = ag["coh"][i] / max(1 - ag["coh"][i], 1e-9)
        pr("     f %5.2f Hz  coh %.3f  gain %.3f  phase %+5.1f   PSD alpha_th %8.3g  incoherent %8.3g (quantiser model %8.3g)"
           "  alpha_w %8.3g (quantiser model %8.3g)  SNR_th %5.1f dB"
           % (f[i], ag["coh"][i], ag["gain"][i], ag["ph"][i], ag["S_th"][i], ag["N_th"][i], ag["N_th_model"][i],
              ag["S_w"][i], ag["N_w_model"][i], 10 * np.log10(max(snr, 1e-9))))
    pr("     kappa (0.35-1.05 Hz) %.3f | M1 AS WRITTEN band %s Hz | ADJUDICATED (gain kappa +-10 %%) %s Hz"
       % (ag["kappa"], ag["band_as_written"], ag["band_adjudicated"]))
    pr("     d(angle)/int(rate) by |wheel angle| (0.5 s spans, whole route): " + "  ".join(
        "%d-%d:%.3f" % (k["lo"], k["hi"], k["ratio"]) for k in ag["kappa_by_angle"]))
    pr("     rms hands-off: alpha_th %.1f  alpha_w %.1f  alpha_th-kappa*alpha_w %.1f deg/s^2"
       % (ag["alpha_rms_HO"]["alpha_th"], ag["alpha_rms_HO"]["alpha_w"], ag["alpha_rms_HO"]["diff"]))
    b = ag["bar_on_alpha"]
    pr("     P1: hands-off driver-torque sensor bar = %.3f*alpha + ... (R2 %.3f); |alpha| p90 %.0f at |bar|<400 vs %.0f at "
       ">=400 deg/s^2; %.3f of hands-off frames |bar|>=400" % (b["coef_alpha"], b["R2"], b["alpha_p90_bar_lt400"],
                                                               b["alpha_p90_bar_ge400"], b["frac_bar_ge400"]))
    sp = res["spec_posctl"]
    pr("     spectral PC (alpha_syn = %.3f u(t-80 ms) + shuffled noise): |H|/G " % sp["Gc"] + " ".join(
        "%.1f:%.3f/%+.0fdeg/coh%.2f" % (f[i], sp["ratio"][i], sp["ph_err"][i], sp["coh"][i])
        for i in [idx_at(f, x) for x in (0.4, 1, 2, 3, 5, 8)]))
    TFr = res["_TF"]
    pr("  cmd -> alpha TRANSFER, H1 (the literal metric) and IV (instrument = desiredLateralAccel; the actuator branch)")
    pr("     |H| deg/s^2 per 0xE4 count [95 %% CI] phase(deg) coh ; IV shown only where coh(la_des,u) >= %.1f" % IV_COH)
    for gname in ["all"] + ["v" + nm for nm, _, _ in VBANDS]:
        row = TFr.get(gname)
        if row is None:
            continue
        pr("   [%s] %d windows (%.0f s, %d blocks)" % (gname, row["n"], row["sec"], row["u>alpha_th"]["nblk"]))
        for key in ("u>alpha_th", "u>alpha_w"):
            T_ = row[key]
            pr("     H1 %-9s " % key + " ".join(
                "%.1f:%.2f[%.2f,%.2f]%+.0f/%.2f" % (f[i], abs(T_["H"][i]), T_["lo"][i], T_["hi"][i],
                                                  np.degrees(np.angle(T_["H"][i])), T_["coh"][i])
                for i in [idx_at(f, x) for x in (0.4, 0.6, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)]))
        if "iv_u>alpha_w" in row:
            T_ = row["iv_u>alpha_w"]
            cells = []
            for x in (0.4, 0.6, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
                i = idx_at(f, x)
                cells.append(("%.1f:%.2f[%.2f,%.2f]%+.0f/c%.2f" % (f[i], abs(T_["H"][i]), T_["lo"][i], T_["hi"][i],
                                                                np.degrees(np.angle(T_["H"][i])), T_["coh_ri"][i]))
                             if T_["coh_ri"][i] >= IV_COH else "%.1f:  --(c%.2f)" % (f[i], T_["coh_ri"][i]))
            pr("     IV u>alpha_w  " + " ".join(cells))
        if "coh_u_p" in row:
            pr("     coh(u, fork P term): " + " ".join("%.1f:%.2f" % (f[i], row["coh_u_p"][i])
                                                    for i in [idx_at(f, x) for x in (0.4, 1, 2, 3, 5, 8)]))
        nc = row["null_perm_coh"]
        pr("     null (window-permuted cmd) coherence median %.3f p95 %.3f over 0.3-10 Hz (3/n = %.3f)"
           % (np.median(nc[fsel(f, 0.3, 10)]), np.percentile(nc[fsel(f, 0.3, 10)], 95), 3.0 / row["n"]))
    nr = TFr["all"]["null_rev_coh"]
    pr("     null (time-reversed cmd, all) coherence median %.3f p95 %.3f over 0.3-10 Hz"
       % (np.median(nr[fsel(f, 0.3, 10)]), np.percentile(nr[fsel(f, 0.3, 10)], 95)))
    pr("  TIME-DOMAIN TRACKING SCORE (hands-off): lag scan alpha_B = G u_B(t-lag) [lag + = alpha lags the command] and the "
       "GAIN-PHASE fit alpha_B = a u_B + b H[u_B] [phase + = alpha LEADS]")
    for bnm in [b_[0] for b_ in FBANDS] + [BROAD[0]]:
        for vnm in ["all"] + [v[0] for v in VBANDS]:
            r = res["band_scores"].get(bnm, {}).get(vnm)
            if r is None:
                continue
            a, w_ = r["u>alpha_th"], r["u>alpha_w"]
            tr_ = r["trim"]
            pr("   %-6s %-6s %s trim footprint: T = FF(cmd) [%.2f, %+.0f deg] + K*alpha_w, |K| %.3f [%.3f,%.3f] counts per deg/s^2 "
               "phase %+.0f (design %.3f %+.0f) | rms T %.1f, FF part %.1f, alpha part %.1f, resid %.1f | R2 %.3f"
               % (bnm, vnm, "VOID" if r["void"] else ("warn" if r["null_warn"] else "    "), tr_["ff_gain"], tr_["ff_phase_deg"],
                  tr_["K_mag"], tr_["K_ci"][0], tr_["K_ci"][1], tr_["K_phase_deg"], tr_["design"]["mag"],
                  tr_["design"]["phase_deg"], tr_["rms_T"], tr_["rms_ff"], tr_["rms_trim"], tr_["rms_resid"], tr_["R2"]))
            pr("   %-6s %-6s %4.0fs | LAG: R2 %.3f[%.3f,%.3f] G %+.3f lag %+4.0f%s | GP: R2 %.3f[%.3f,%.3f] |G| %.3f ph %+4.0f"
               "[%+.0f,%+.0f] | alpha_w LAG R2 %.3f GP R2 %.3f | sp %.3f T %.3f | nulls %.3f/%.3f | PC1 %.3f/%.3f PC2 %.3f/%.3f "
               "G %.3f/%.3f lag %.0f" % (
                   bnm, vnm, a["sec"], a["R2"], a["R2_ci"][0], a["R2_ci"][1], a["G"], a["lag_ms"], "E" if a["edge"] else " ",
                   a["gp"]["R2"], a["gp"]["R2_ci"][0], a["gp"]["R2_ci"][1], a["gp"]["gain"], a["gp"]["phase_deg"],
                   a["gp"]["phase_ci"][0], a["gp"]["phase_ci"][1], w_["R2"], w_["gp"]["R2"],
                   r["sp>alpha_th"]["gp"]["R2"], r["T>alpha_th"]["gp"]["R2"],
                   max(r["null_shuffle"]["R2"], r["null_shuffle"]["gp"]["R2"]),
                   max(r["null_reverse"]["R2"], r["null_reverse"]["gp"]["R2"]),
                   r["posctl"]["R2"], r["posctl"]["R2_ceiling"], r["posctl2"]["R2"], r["posctl2"]["R2_ceiling"],
                   r["posctl2"]["G"], r["posctl2"]["G_true"], r["posctl2"]["lag_ms"]))
            ter = [r.get("t%d" % k) for k in range(3)]
            if any(ter):
                pr("        terciles of dynamic |u| (edges %s counts rms): " % [round(x) for x in r["tercile_edges"]] +
                   " | ".join("t%d GP R2 %.3f |G| %.3f ph %+.0f" % (k, t_["gp"]["R2"], t_["gp"]["gain"], t_["gp"]["phase_deg"])
                              for k, t_ in enumerate(ter) if t_))
            if "handson_u>alpha_th" in r:
                h = r["handson_u>alpha_th"]
                pr("        hands-ON %.0f s: GP R2 %.3f |G| %.3f ph %+.0f  (LAG R2 %.3f lag %+.0f)"
                   % (h["sec"], h["gp"]["R2"], h["gp"]["gain"], h["gp"]["phase_deg"], h["R2"], h["lag_ms"]))
            if "HObar_u>alpha_th" in r:
                h = r["HObar_u>alpha_th"]
                pr("        P1 sensitivity, kit |bar|<400 mask %.0f s: GP R2 %.3f |G| %.3f ph %+.0f"
                   % (h["sec"], h["gp"]["R2"], h["gp"]["gain"], h["gp"]["phase_deg"]))
            d_ = res["decomposition"][bnm].get(vnm)
            if d_:
                pr("        command decomposition u_B ~ x(t-lag): " + "  ".join(
                    "%s R2 %.2f@%+dms(slope %.3g)" % (k.replace("cs_", ""), v["R2"], v["lag_ms"], v["slope"])
                    for k, v in d_.items() if isinstance(v, dict)) +
                   ("  | if u=-K*theta: H1 would read %.2f at %.1f Hz" % (d_["implied_H_if_feedback"], np.sqrt(
                       [b_ for b_ in FBANDS + [BROAD] if b_[0] == bnm][0][1] * [b_ for b_ in FBANDS + [BROAD] if b_[0] == bnm][0][2]))
                    if "implied_H_if_feedback" in d_ else ""))
    pr("  STATIC NONLINEARITY (0.3-8 Hz band, best lag): median alpha_th per command bin; slopes on alpha_w (deg/s^2 per count)")
    for vnm, N in res["nonlinearity"].items():
        s_ = N["slopes"]
        pr("   [%s] lag %+.0f ms  slope left %.3f right %.3f | |u|<100 %.3f 100-300 %.3f >=300 %.3f | RAW (no high-pass, "
           "8 Hz LP alpha vs u) slope %.4f R2 %.3f" % (vnm, N["lag_ms"], s_["pos"], s_["neg"], s_["small"], s_["mid"],
                                                       s_["large"], N["raw_slope"], N["raw_r2"]))
        pr("        bins: " + " ".join("[%+.0f..%+.0f]%.0f(n%d)" % (b_["lo"], b_["hi"], b_["a_med"], b_["n"]) for b_ in N["bins"]))
        pr("        wheel stuck (|omega|<2 deg/s) share by |u_B|: " + " ".join(
            "%d-%d:%.2f" % (x["lo"], x["hi"], x["frac"]) for x in N["stuck"]))
    pr("  JOINT REGRESSION (broadband, 8 Hz LP): u = J*alpha + b*omega + k*theta + F*tanh(omega/2) + c, response advanced by lag")
    for k, J in res["joint"].items():
        c = J["coef"]
        pr("   [%-5s] lag %3d ms R2 %.3f | J %.3f[%.3f,%.3f] b %.2f[%.2f,%.2f] k %.1f[%.1f,%.1f] F %.0f[%.0f,%.0f] | share of "
           "var(u): J.alpha %.3f b.omega %.3f k.theta %.3f F %.3f | unique J %.3f b %.3f k %.3f F %.3f | %.0f s"
           % (k, J["lag_ms"], J["R2"], c["J"], J["ci"]["J"][0], J["ci"]["J"][1], c["b"], J["ci"]["b"][0], J["ci"]["b"][1],
              c["k"], J["ci"]["k"][0], J["ci"]["k"][1], c["F"], J["ci"]["F"][0], J["ci"]["F"][1], J["share"]["J"],
              J["share"]["b"], J["share"]["k"], J["share"]["F"], J["unique"]["J"], J["unique"]["b"], J["unique"]["k"],
              J["unique"]["F"], J["sec"]))


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        if np.iscomplexobj(o):
            return dict(mag=np.round(np.abs(o), 6).tolist(), ph_deg=np.round(np.degrees(np.angle(o)), 3).tolist())
        return np.round(o.astype(float), 6).tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return o


def tf_summary(res, fpts=(0.4, 0.6, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)):
    f = res["_f"]
    out = {}
    for gname, row in res["_TF"].items():
        o = {}
        for key, T_ in row.items():
            if not isinstance(T_, dict) or "H" not in T_:
                continue
            o[key] = [dict(f=float(f[i]), mag=float(abs(T_["H"][i])), ph=float(np.degrees(np.angle(T_["H"][i]))),
                           lo=float(T_["lo"][i]) if "lo" in T_ else None, hi=float(T_["hi"][i]) if "hi" in T_ else None,
                           coh=float(T_["coh"][i]) if "coh" in T_ else None,
                           coh_ri=float(T_["coh_ri"][i]) if "coh_ri" in T_ else None)
                      for i in [idx_at(f, x) for x in fpts]]
        out[gname] = o
    return out


def save_route(res):
    os.makedirs(OUT, exist_ok=True)
    arrs = {"f": res["_f"]}
    for gn, row in res["_TF"].items():
        for k, v in row.items():
            if isinstance(v, dict):
                for part, a in v.items():
                    if isinstance(a, np.ndarray):
                        arrs["%s|%s|%s" % (gn, k, part)] = a
            elif isinstance(v, np.ndarray):
                arrs["%s|%s" % (gn, k)] = v
    for k in ("gain", "ph", "coh", "S_th", "S_w", "N_th", "N_w_model", "N_th_model"):
        arrs["agree|" + k] = np.asarray(res["agreement"][k])
    for k in ("ratio", "ph_err", "coh"):
        arrs["specpc|" + k] = np.asarray(res["spec_posctl"][k])
    np.savez_compressed(os.path.join(OUT, "tf_%s.npz" % res["tag"]), **arrs)
    js = jsonable({k: v for k, v in res.items() if k not in ("agreement", "spec_posctl")})
    js["agreement"] = jsonable({k: v for k, v in res["agreement"].items()
                                if k not in ("f", "gain", "ph", "coh", "S_th", "S_w", "N_th", "N_w_model", "N_th_model")})
    js["agreement_at"] = [dict(f=float(res["_f"][i]), coh=float(res["agreement"]["coh"][i]),
                               gain=float(res["agreement"]["gain"][i]), ph=float(res["agreement"]["ph"][i]))
                          for i in [idx_at(res["_f"], x) for x in (0.4, 1, 2, 3, 4, 5, 6, 8, 10, 15)]]
    js["tf_summary"] = tf_summary(res)
    json.dump(js, open(os.path.join(OUT, "metric_%s.json" % res["tag"]), "w"), indent=1)


def main(tags):
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    ALL = {}
    for tag in tags:
        res = analyse_route(tag, rng)
        ALL[tag] = res
        print_route(res)
        save_route(res)
        pr("  [%s done in %.0f s]" % (tag, res["_elapsed_s"]))
    name = "metric_out.txt" if set(tags) == set(DEFAULT) else "metric_out_%s.txt" % "_".join(tags)
    open(os.path.join(OUT, name), "w", encoding="utf-8").write("\n".join(OUTBUF) + "\n")
    import accel_tracking_compare as CMP       # tables + figures from the files just written (identical to a rerun)
    n0 = len(OUTBUF)
    CMP.compare(CMP.load_saved(tags), pr)
    figdir = OUT if set(tags) == set(DEFAULT) else os.path.join(OUT, "subset_" + "_".join(tags))
    os.makedirs(figdir, exist_ok=True)
    CMP.figures(CMP.load_saved(tags), figdir)
    open(os.path.join(OUT, "compare_out.txt" if set(tags) == set(DEFAULT) else "compare_out_%s.txt" % "_".join(tags)),
         "w", encoding="utf-8").write("\n".join(OUTBUF[n0:]) + "\n")
    return ALL


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--route" in sys.argv:
        rid = sys.argv[sys.argv.index("--route") + 1]
        args = [k for k, v in ROUTES.items() if v["route"] == rid]
        if not args:
            raise SystemExit("route %s is not registered in ROUTES (build its v280 cache, then add it)" % rid)
        args += [t for t in DEFAULT if ROUTES[t]["group"] != "V294" and t not in args]
    main(args or DEFAULT)
