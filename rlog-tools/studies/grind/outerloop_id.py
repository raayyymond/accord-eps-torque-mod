# -*- coding: utf-8 -*-
"""outerloop_id.py -- IS THE GRINDING A LIMIT CYCLE OF THE OUTER (openpilot) LOOP?
Subagent `echoloop`, 2026-09-10.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

THE LOOP, AS THE FORK ACTUALLY WRITES IT (read from
openpilots/raayyymond-StarPilot/StarPilot/selfdrive/controls/lib/latcontrol_torque.py:236-297,597-601,720-726):
    measured_curvature = -VM.calc_curvature(radians(CS.steeringAngleDeg - angleOffset), vEgo, roll)
    measurement        = measured_curvature * vEgo**2          <- logged as torqueState.actualLateralAccel
    error              = (setpoint - measurement) * (1 + lsf/kp_sched)   <- logged as torqueState.error
    output_torque      = torque_from_lateral_accel(kp*error + i + f)     <- logged as -torqueState.output
*** THE MEASUREMENT IS THE STEERING ANGLE, NOT THE YAW RATE.  There is no camera, no model and no IMU in
the feedback branch.  The model only writes the SETPOINT. ***

Sections
  1  CHANNEL      publish rates of every signal in the loop; verify measurement == f(steeringAngleDeg);
                  quantisation; what 20 Hz folds to on each sampler (livePose is 20 Hz -> Nyquist 10 Hz)
  2  SPECTRA      12-26 Hz content of measurement / setpoint / error / output / wire, grinding vs quiet
  3  K_FB         the feedback branch gain dU/dm, measured PER FRAME from the log (exact, no estimation)
  4  PLANT+L      P = S_mr/S_ur (setpoint-instrumented, closed-loop-unbiased); L = P*K; |L|, angle, coh
  5  ECHO         is the command's own ring the fed-back measurement?  amplitude + phase test
  6  DELAY        cross-phase slope measurement->command over 13-25 Hz; compare to the pipeline budget
  7  OPENLOOP     lateral-disengaged vs engaged at matched speed (states its own power)
  8  LPF          what the colleagues' first-order tau would do to |L| and the margins
Run: python rlog-tools/studies/grind/outerloop_id.py [section...]
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402   dejitter / grid_from / runs / Pool
import v280_map_profiles as V                 # noqa: E402   demand()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
ROUTES = ("r39", "r5e", "r62", "r63", "r35")
BUILD = {"r39": "V282", "r5e": "V288 r2", "r62": "V289 r1", "r63": "V289 r1", "r35": "V281 r3"}
CSC = ["active", "error", "p", "i", "d", "f", "output", "saturated", "errorRate",
       "meas", "setp", "djerk", "desCurv"]
STC = ["vEgo", "angDeg", "rateDeg", "dTorque", "pressed", "torqueEps"]
CCC = ["latActive", "torque", "curv", "curCurv"]
COC = ["torqueOut", "torqueCan"]
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def save(name):
    with open(os.path.join(SCR, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


# ----------------------------------------------------------------------------------------------------------------
def load(tag):
    """Put every openpilot stream on ONE dejittered 100 Hz controlsd frame axis, and the CAN wire beside it."""
    D = dict(np.load(os.path.join(SCR, "outer_%s.npz" % tag)))
    k, P, tn, res = C20.dejitter(D["cs_t"], 0.01, 100)
    K = int(k[-1])
    g = dict(tag=tag, P=P, n=K + 1,
             jit=(float(np.percentile(res, 50)), float(np.percentile(res, 90)),
                  float(np.mean(np.abs(res) > 0.003))))
    g["t"] = np.interp(np.arange(K + 1), k, tn - k * P) + np.arange(K + 1) * P
    have = None
    for j, nm in enumerate(CSC):
        g[nm], hv = C20.grid_from(k, D["cs"][:, j], K)
        if have is None:
            have = hv
    g["have"] = have
    for cols, kt, ka in ((STC, "st_t", "st"), (CCC, "cc_t", "cc"), (COC, "co_t", "co")):
        for j, nm in enumerate(cols):
            g[nm] = np.interp(g["t"], D[kt], D[ka][:, j])
    g["yaw"] = np.interp(g["t"], D["lp_t"], D["lp"][:, 2]) if len(D["lp_t"]) else np.zeros(K + 1)
    g["lp_t"], g["lp"] = D["lp_t"], D["lp"]
    for j, nm in enumerate(["angOff", "roll", "steerRatio", "stiff"]):
        g[nm] = np.interp(g["t"], D["par_t"], D["par"][:, j]) if len(D["par_t"]) else np.zeros(K + 1)
    g["latDelay"] = np.interp(g["t"], D["dly_t"], D["dly"]) if len(D["dly_t"]) else np.full(K + 1, 0.2)
    k18, P18, tn18, r18 = C20.dejitter(D["t18"], 0.01, 100)
    ke4, Pe4, tne4, re4 = C20.dejitter(D["te4"], 0.01, 100)
    k14, P14, tn14, r14 = C20.dejitter(D["t14"], 0.01, 100)
    g["wire_rate"] = np.interp(g["t"], tn18, D["rate18"])
    g["wire_bar"] = np.interp(g["t"], tn18, D["tq18"] * 1.024)
    g["sca"] = np.interp(g["t"], tn18, D["sca"].astype(float)) > 0.5
    g["cmd"] = np.interp(g["t"], tne4, D["cmd"])
    g["req"] = np.interp(g["t"], tne4, D["req"].astype(float)) > 0.5
    g["wire_ang"] = np.interp(g["t"], tn14, D["ang"])
    g["b4"] = np.interp(g["t"], tn14, D["b4"].astype(float))
    g["wire_jit"] = dict(f18=float(np.percentile(r18, 90)), fe4=float(np.percentile(re4, 90)),
                         f14=float(np.percentile(r14, 90)))
    g["eng"] = (g["active"] > 0.5) & (g["latActive"] > 0.5) & g["sca"] & g["req"] & g["have"]
    g["idx"], g["sgn"] = V.demand(np.round(g["cmd"]), g["wire_bar"])
    g["marks"] = D["marks"]
    g["cs_t0"] = float(D["cs_t"][0])
    return g


CACHE = {}


def G(tag):
    if tag not in CACHE:
        CACHE[tag] = load(tag)
    return CACHE[tag]


# ================================================================================================================
def sec1():
    pr("=" * 112)
    pr("SECTION 1 -- THE CHANNEL openpilot ACTUALLY DIFFERENTIATES INTO `measurement`")
    pr("=" * 112)
    pr("FORK SOURCE [EVIDENCE, read from the files]:")
    pr("  latcontrol_torque.py:236  measured_curvature = -VM.calc_curvature(radians(CS.steeringAngleDeg")
    pr("                                                  - params.angleOffsetDeg), CS.vEgo, params.roll)")
    pr("  latcontrol_torque.py:237  measurement = measured_curvature * CS.vEgo**2")
    pr("  latcontrol_torque.py:296  error = setpoint - measurement    (then * (1 + lsf/current_kp), :297)")
    pr("  => the feedback branch is the STEERING ANGLE off CAN.  No yaw rate, no IMU, no camera, no model.")
    pr("  carstate.py:187           ret.steeringAngleDeg = cp.vl['STEERING_SENSORS']['STEER_ANGLE']")
    pr("  honda_accord_2017_can_ext_generated.dbc:368  BO_ 342 STEERING_SENSORS, STEER_ANGLE scale -0.1 deg")
    pr("  common/pid.py:47-49       p = k_p*error ; d = k_d*error_rate ; k_d = 0 for this car (log: d == -0)")
    pr("                            => at 13-26 Hz the OUTER controller is a PURE GAIN.  No lead anywhere.")
    pr("  carcontroller.py:286      the torque LPF is gated to CAR.HONDA_CIVIC_BOSCH + EPS_MODIFIED")
    pr("                            -> NOT ACTIVE on the Accord.  The only output shaping is")
    pr("  carcontroller.py:306      rate_limit(+-STEER_DELTA*DT_CTRL) = +-0.03 of full scale/frame")
    pr()
    for tag in ROUTES:
        g = G(tag)
        n = g["n"]
        dur = n * g["P"]
        pr("-" * 104)
        pr("%s (%-8s)  %d controlsd frames, %.1f s, fitted period %.6f s" % (tag, BUILD[tag], n, dur, g["P"]))
        pr("  controlsd publish jitter (t - nominal): p50 %.4f s  p90 %.4f s  frac > 3 ms %.4f" % g["jit"])
        pr("  CAN dejitter residual p90: 0x18F %.4f  0xE4 %.4f  0x14A %.4f s"
           % (g["wire_jit"]["f18"], g["wire_jit"]["fe4"], g["wire_jit"]["f14"]))
        pr("  livePose %d samples / %.1f s = %.2f Hz   *** NYQUIST %.2f Hz ***"
           % (len(g["lp_t"]), dur, len(g["lp_t"]) / dur, 0.5 * len(g["lp_t"]) / dur))
        m, ang, v = g["meas"], g["angDeg"], g["vEgo"]
        ok = g["eng"] & (v > 0.5)
        den = -(np.radians(ang - g["angOff"])) * v ** 2
        r = np.where(np.abs(den) > 1e-6, m / np.where(np.abs(den) < 1e-9, np.nan, den), np.nan)[ok]
        pr("  measurement / [-(angDeg-offset)_rad * v^2]  ->  should be 1/(SR*L*(1+K v^2)), a slow fn of v")
        pr("    p1 %.5f  p50 %.5f  p99 %.5f   (n=%d finite)"
           % (np.nanpercentile(r, 1), np.nanpercentile(r, 50), np.nanpercentile(r, 99),
              int(np.sum(np.isfinite(r)))))
        dm, da = np.diff(m[ok]), np.diff(ang[ok])
        msk = np.isfinite(dm) & np.isfinite(da)
        pr("    corr( d(measurement), d(steeringAngleDeg) ) = %.6f  over %d engaged frames"
           % (np.corrcoef(dm[msk], da[msk])[0, 1], int(msk.sum())))
        pr("    steeringAngleDeg is a clean multiple of 0.1 deg: %s ; LSB 0.1 deg"
           % bool(np.all(np.abs(ang * 10 - np.round(ang * 10)) < 1e-6)))
        pr("    carState angDeg vs CAN 0x14A byte0-1 * -0.1: corr %.6f, rms diff %.4f deg"
           % (np.corrcoef(ang[ok], g["wire_ang"][ok])[0, 1],
              float(np.sqrt(np.mean((ang[ok] - g["wire_ang"][ok]) ** 2)))))
    pr()
    pr("ALIASING -- what a ring folds to on each sampler [EVIDENCE, arithmetic]:")
    for name, fs in (("CAN 0x14A / carState angle", 100.0), ("controlsd tick", 100.0),
                     ("livePose", 20.0), ("modelV2 / cameraOdometry", 20.0), ("device gyroscope", 89.0)):
        for f0 in (16.5, 20.0):
            fold = abs(((f0 + fs / 2) % fs) - fs / 2)
            pr("    %-28s fs %5.1f Hz  f0 %5.2f Hz -> %6.2f Hz   %s"
               % (name, fs, f0, fold, "(below Nyquist, NOT aliased)" if f0 < fs / 2 else "*** ALIASED ***"))



# ================================================================================================================
# window census -- band-agnostic (the V282 18-22 Hz gate is blind to V289's relocated line)
# ================================================================================================================
W, STEP = 200, 50
FLO, FHI = 12.0, 26.0
import grind_incident_r35 as GI          # noqa: E402  line_of / band / envelope



def line_of(x, lo=FLO, hi=FHI, nfft=1024):
    """GI.line_of's estimator, restricted to 4-34 Hz at nfft=1024 so prom_spectrum's O(n^2)
    neighbourhood median is tractable per window.  Identical result on 12-26 Hz."""
    import _grind2_lib as G2
    f, P = signal.periodogram(x - x.mean(), fs=FS, window="hann", nfft=nfft)
    sl = (f >= 4.0) & (f <= 34.0)
    fs_, Ps_ = f[sl], P[sl]
    R = G2.prom_spectrum(fs_, Ps_, 6.0, 1.5)
    return G2.locate(fs_, Ps_, lo, hi, R=R)


def census(tag):
    g = G(tag)
    rows = []
    eng = g["eng"]
    for a in range(0, g["n"] - W, STEP):
        b = a + W
        if not eng[a:b].all():
            continue
        bar = g["wire_bar"][a:b]
        f0, prom = line_of(bar - bar.mean())
        if not np.isfinite(f0):
            continue
        lo, hi = f0 - 2.0, f0 + 2.0
        r = dict(a=a, b=b, f0=f0, prom=prom,
                 v=float(np.median(g["vEgo"][a:b])), idx=float(np.median(g["idx"][a:b])),
                 sat=float(np.mean(g["saturated"][a:b])))
        for nm in ("wire_bar", "wire_rate", "cmd", "meas", "setp", "error", "output", "wire_ang"):
            x = g[nm][a:b]
            r["A_" + nm] = float(GI.band(x - x.mean(), lo, hi, FS))
        r["present"] = bool(prom >= 8.0 and r["A_wire_bar"] >= 40.0)
        rows.append(r)
    return rows


CEN = {}


def cen(tag):
    if tag in CEN:
        return CEN[tag]
    import pickle
    fp = os.path.join(SCR, "outerloop_cen_%s.pkl" % tag)
    if os.path.exists(fp):
        CEN[tag] = pickle.load(open(fp, "rb"))
    else:
        CEN[tag] = census(tag)
        pickle.dump(CEN[tag], open(fp, "wb"))
    return CEN[tag]


def sec2():
    pr("=" * 112)
    pr("SECTION 2 -- IS THE RING PRESENT IN openpilot's MEASUREMENT, AND IN ITS COMMAND?")
    pr("=" * 112)
    pr("Band-agnostic census: 2 s windows / 0.5 s step, LATERAL-engaged only (controlsState.active AND")
    pr("carControl.latActive AND 0x18F SCA AND 0xE4 STEER_REQUEST); f0 = most prominent 12-26 Hz peak of the")
    pr("driver-torque bar; PRESENT = prominence >= 8 AND bar band amplitude (f0 +- 2 Hz) >= 40 raw.")
    pr("Amplitudes are band amplitudes at f0 +- 2 Hz.  meas/setp/error/output are openpilot's OWN numbers,")
    pr("straight off controlsState -- no interpolation, no cross-stream alignment.")
    pr()
    hdr = ("%-5s %-9s %5s %6s | %7s %7s %7s %8s %8s %8s %8s" %
           ("route", "build", "n", "f0", "bar", "rate", "cmd", "meas", "setp", "error", "output"))
    for label, want in (("PRESENT (grinding)", True), ("ABSENT  (quiet)", False)):
        pr(label)
        pr("  " + hdr)
        for tag in ROUTES:
            rs = [r for r in cen(tag) if r["present"] == want]
            if not rs:
                continue
            med = lambda k: float(np.median([r[k] for r in rs]))                      # noqa: E731
            pr("  %-5s %-9s %5d %6.2f | %7.1f %7.1f %7.2f %8.2e %8.2e %8.2e %8.2e"
               % (tag, BUILD[tag], len(rs), med("f0"), med("A_wire_bar"), med("A_wire_rate"),
                  med("A_cmd"), med("A_meas"), med("A_setp"), med("A_error"), med("A_output")))
        pr()
    pr("RATIOS, present / absent (median over windows, same route) -- which channels carry the ring:")
    pr("  %-5s %-9s %7s %7s %7s %8s %8s %8s %8s" %
       ("route", "build", "bar", "rate", "cmd", "meas", "setp", "error", "output"))
    for tag in ROUTES:
        A = [r for r in cen(tag) if r["present"]]
        B = [r for r in cen(tag) if not r["present"]]
        if not A or not B:
            continue
        f = lambda k: float(np.median([r[k] for r in A]) / np.median([r[k] for r in B]))   # noqa: E731
        pr("  %-5s %-9s %7.2f %7.2f %7.2f %8.2f %8.2f %8.2f %8.2f"
           % (tag, BUILD[tag], f("A_wire_bar"), f("A_wire_rate"), f("A_cmd"),
              f("A_meas"), f("A_setp"), f("A_error"), f("A_output")))
    pr()
    pr("SANITY -- error must equal (setp - meas) * lsf_gain; and meas must be the angle:")
    for tag in ROUTES:
        g = G(tag)
        ok = g["eng"] & (np.abs(g["setp"] - g["meas"]) > 1e-6)
        lg = g["error"][ok] / (g["setp"][ok] - g["meas"][ok])
        pr("  %-5s lsf_gain = error/(setp-meas): p5 %.3f  p50 %.3f  p95 %.3f  (always > 0: %s)"
           % (tag, np.percentile(lg, 5), np.percentile(lg, 50), np.percentile(lg, 95),
              bool(np.all(lg > 0))))


def sec3():
    pr("=" * 112)
    pr("SECTION 3 -- K, THE OUTER FEEDBACK GAIN  -d(output torque)/d(measurement)   [EXACT, per frame]")
    pr("=" * 112)
    pr("interfaces.py:327-329  torque_from_lateral_accel_linear = lateral_acceleration / latAccelFactor")
    pr("latcontrol_torque.py:725  pid_log.output = -output_torque ;  pid.update returns clip(p+i+d+f, +-lim)")
    pr("=> output = -(p+i+d+f, clipped)/LAF exactly, so  T' = d(output)/d(p+i+d+f) = -1/LAF.")
    pr("   p = kp*error ; error = (setp-meas)*lsf_gain  (lsf_gain = 1 + low_speed_factor/current_kp, :297)")
    pr("=> at 13-26 Hz, where i and f are slow and d == 0:   K = -T'*kp*lsf_gain = kp*lsf_gain/LAF")
    pr("Every number below is read off the log; none is assumed.  The +-1.000 rail OPENS the loop on the")
    pr("frames it binds (K = 0 there), so the saturation duty is quoted next to K.")
    pr()
    for tag in ROUTES:
        g = G(tag)
        ok = g["eng"]
        kp = kfit(tag)
        lg = kp["lsf"][ok]
        Kall = -kp["Tp"] * kp["kp"] * lg
        pr("  %-5s %-9s latAccelFactor = %.4f EXACTLY  (-(p+i+d+f)/output is %.4f at p5 and %.4f at p95)"
           % (tag, BUILD[tag], kp["LAF"], kp["ratio_p5"], kp["ratio_p95"]))
        pr("        kp = d(p)/d(error) = %.4f   lsf_gain p50 %.3f [p5 %.3f, p95 %.3f]"
           % (kp["kp"], np.percentile(lg, 50), np.percentile(lg, 5), np.percentile(lg, 95)))
        pr("        K = kp*lsf_gain/LAF : p5 %.4f  p50 %.4f  p95 %.4f  [torque units per (m/s^2)]"
           % (np.percentile(Kall, 5), np.percentile(Kall, 50), np.percentile(Kall, 95)))
        pr("        |output| railed at 1.000 on %.4f of engaged frames -- the loop is OPEN there"
           % kp["satduty"])
        w = ok & (np.abs(g["torqueOut"]) > 1e-3)
        cw = np.polyfit(g["torqueOut"][w], g["torqueCan"][w], 1)
        pr("        wire: d(0xE4 counts)/d(limited torque) = %+.1f (R2 %.5f); rate limit +-0.03/frame = "
           "+-%.0f counts/frame"
           % (cw[0], 1 - np.var(g["torqueCan"][w] - np.polyval(cw, g["torqueOut"][w]))
              / np.var(g["torqueCan"][w]), abs(cw[0]) * 0.03))


# ================================================================================================================
# pooled cross-spectra over census windows
# ================================================================================================================
def xspec(g, rows, keys):
    """Hann-windowed cross-spectra accumulated over the given census windows, on the controlsd frame axis."""
    n = W
    win = np.hanning(n)
    f = np.fft.rfftfreq(n, 1.0 / FS)
    Xs = {k: [] for k in keys}
    for r in rows:
        a, b = r["a"], r["b"]
        for k in keys:
            x = signal.detrend(g[k][a:b].astype(float), type="linear")
            Xs[k].append(np.fft.rfft(x * win))
    for k in keys:
        Xs[k] = np.array(Xs[k]) if Xs[k] else np.zeros((0, len(f)), complex)
    return f, Xs


def pool(Xs, keys, sel=None):
    S = {}
    for i, a in enumerate(keys):
        for b in keys[i:]:
            A = Xs[a] if sel is None else Xs[a][sel]
            B = Xs[b] if sel is None else Xs[b][sel]
            S[(a, b)] = (A * np.conj(B)).mean(axis=0)
            S[(b, a)] = np.conj(S[(a, b)])
    return S


def atf(f, X, f0):
    return np.interp(f0, f, X.real) + 1j * np.interp(f0, f, X.imag)


KFB = {}
KPARTS = {}


def kfit(tag):
    """The EXACT linear decomposition of `output`.  output = -(p+i+d+f, clipped to +-steer_max*LAF)/LAF,
    so T' = -1/latAccelFactor exactly; it is read as the median of d(output)/d(p+i+d+f) over UNSATURATED
    frames (an OLS fit is corrupted by the +-1.000 rail, which the routes hit on ~1% of frames)."""
    if tag in KPARTS:
        return KPARTS[tag]
    g = G(tag)
    ok = g["eng"]
    sat = np.abs(g["output"]) >= 0.999
    pid = g["p"] + g["i"] + g["d"] + g["f"]
    d1, d2 = np.diff(g["output"]), np.diff(pid)
    m = ok[1:] & ~sat[1:] & ~sat[:-1] & (np.abs(d2) > 1e-4)
    Tp = float(np.median(d1[m] / d2[m]))
    LAF = -1.0 / Tp
    e = g["error"][ok]
    mm = np.abs(e) > 1e-4
    kp = float(np.polyfit(e[mm], g["p"][ok][mm], 1)[0])
    er = g["setp"] - g["meas"]
    with np.errstate(invalid="ignore", divide="ignore"):
        lsf = np.where(np.abs(er) > 1e-6, g["error"] / np.where(np.abs(er) < 1e-9, np.nan, er), np.nan)
    good = np.isfinite(lsf)
    lsf = np.interp(np.arange(len(lsf)), np.flatnonzero(good), lsf[good])
    KPARTS[tag] = dict(Tp=Tp, T0=0.0, kp=kp, lsf=lsf, LAF=LAF,
                       satduty=float(np.mean(sat[ok])),
                       ratio_p5=float(np.nanpercentile((-pid / np.where(np.abs(g["output"]) < 1e-6,
                                                                       np.nan, g["output"]))[ok & ~sat], 5)),
                       ratio_p95=float(np.nanpercentile((-pid / np.where(np.abs(g["output"]) < 1e-6,
                                                                         np.nan, g["output"]))[ok & ~sat], 95)))
    KFB[tag] = float(-Tp * kp * np.median(lsf[ok]))
    return KPARTS[tag]


def Kwin(tag, rows):
    """median per-window K over the given census windows -- K varies with speed through lsf."""
    kp = kfit(tag)
    return float(np.median([-kp["Tp"] * kp["kp"] * np.median(kp["lsf"][r["a"]:r["b"]]) for r in rows]))


def sec4():
    pr("=" * 112)
    pr("SECTION 4 -- THE OUTER LOOP'S RETURN RATIO L = P*K AT THE RING")
    pr("=" * 112)
    pr("Model:  m = P*u + d ;  u = -K*m + w    (m = measurement, u = output torque, w = setpoint-driven and")
    pr("        integrator terms, d = plant-side disturbance).  Closed loop 1/(1+L) with L = P*K.")
    pr("        A LIMIT CYCLE needs L ~ -1 : |L| ~ 1 AND angle(L) ~ +-180 deg, i.e. |1+L| ~ 0.")
    pr("K is SECTION 3's per-frame number (exact, not estimated).  P must be estimated in CLOSED LOOP, so:")
    pr("  P_IV  = S(m,r)/S(u,r), the SETPOINT r as instrument.  r drives BOTH the feedback and the")
    pr("          feedforward branches through the same 1/(1+L) factor, so that factor cancels and the")
    pr("          feedforward path does not have to be separated.  Unbiased iff r is uncorrelated with d.")
    pr("  P_dir = S(m,u)/S(u,u), the naive estimate.  IN CLOSED LOOP IT IS BIASED TOWARDS -1/K, i.e. it")
    pr("          MANUFACTURES |L| = 1.  It is printed only so the size of that bias is visible.")
    pr()
    for tag in ROUTES:
        g = G(tag)
        rows = cen(tag)
        A = [r for r in rows if r["present"]]
        B = [r for r in rows if not r["present"]]
        keys = ["meas", "setp", "output"]
        pr("-" * 104)
        pr("%s (%s)   present windows %d, quiet %d   K(grind) %.4f  K(quiet) %.4f"
           % (tag, BUILD[tag], len(A), len(B),
              Kwin(tag, A) if A else float("nan"), Kwin(tag, B) if B else float("nan")))
        for label, rs in (("GRINDING", A), ("QUIET", B)):
            if len(rs) < 12:
                pr("   %-9s too few windows (%d) -- skipped" % (label, len(rs)))
                continue
            K = Kwin(tag, rs)
            f, Xs = xspec(g, rs, keys)
            S = pool(Xs, keys)
            f0 = float(np.median([r["f0"] for r in rs]))
            Piv = S[("meas", "setp")] / S[("output", "setp")]
            Pdir = S[("meas", "output")] / S[("output", "output")].real
            coh = lambda a, b: np.abs(S[(a, b)]) ** 2 / (S[(a, a)].real * S[(b, b)].real)   # noqa: E731
            rng = np.random.default_rng(7)
            bs = []
            for _ in range(400):
                sel = rng.integers(0, len(rs), len(rs))
                Sb = pool(Xs, keys, sel)
                bs.append(atf(f, Sb[("meas", "setp")] / Sb[("output", "setp")], f0) * K)
            bs = np.array(bs)
            L = atf(f, Piv, f0) * K
            Ld = atf(f, Pdir, f0) * K
            pr("   %-9s f0 %5.2f Hz   |L_IV| %8.5f  [%.5f, %.5f]   angle %+7.1f deg  [%+.0f, %+.0f]"
               % (label, f0, abs(L), np.percentile(np.abs(bs), 2.5), np.percentile(np.abs(bs), 97.5),
                  np.degrees(np.angle(L)),
                  np.percentile(np.degrees(np.angle(bs)), 2.5), np.percentile(np.degrees(np.angle(bs)), 97.5)))
            pr("             |L_direct(biased)| %8.5f  angle %+7.1f    coh(r,u) %.3f  coh(r,m) %.3f  coh(u,m) %.3f"
               % (abs(Ld), np.degrees(np.angle(Ld)), float(np.interp(f0, f, coh("setp", "output"))),
                  float(np.interp(f0, f, coh("setp", "meas"))),
                  float(np.interp(f0, f, coh("output", "meas")))))
            pr("             |L_IV| across the band:  " +
               "  ".join("%.1fHz %.4f" % (fx, abs(atf(f, Piv, fx) * K)) for fx in (13, 15, 16.5, 18, 20, 22, 25)))
            pr("             |1 + L| = %.4f   (a limit cycle needs ~0)" % abs(1 + L))


def sec5():
    pr("=" * 112)
    pr("SECTION 5 -- ECHO vs FORCING:  WHICH TERM OF THE COMMAND CARRIES THE RING?")
    pr("=" * 112)
    pr("`output` is EXACTLY  T'*(p + i + d + f) + T0  and  p = kp*lsf*(setp - meas),  so per frame")
    pr("    output = u_meas + u_setp + u_rest      with")
    pr("    u_meas = -T'*kp*lsf*meas   (the FED-BACK measurement -- the ECHO term)")
    pr("    u_setp = +T'*kp*lsf*setp   (the setpoint through the same P gain -- forcing through P)")
    pr("    u_rest =  T'*(i + d + f) + T0   (integrator + feedforward -- forcing through FF)")
    pr("No spectral estimation and no causality assumption: an algebraic identity, checked below.")
    pr()
    for tag in ROUTES:
        g = G(tag)
        kp = kfit(tag)
        lsf = kp["lsf"]
        u_meas = -kp["Tp"] * kp["kp"] * lsf * g["meas"]
        u_setp = +kp["Tp"] * kp["kp"] * lsf * g["setp"]
        u_rest = kp["Tp"] * (g["i"] + g["d"] + g["f"])
        recon = u_meas + u_setp + u_rest
        ok = g["eng"]
        pr("-" * 104)
        pr("%s (%s)  identity check: rms(output - recon) %.3e  vs rms(output) %.3e"
           % (tag, BUILD[tag], float(np.sqrt(np.mean((g["output"][ok] - recon[ok]) ** 2))),
              float(np.sqrt(np.mean(g["output"][ok] ** 2)))))
        railed = np.abs(g["output"]) >= 0.999
        for label, want in (("GRINDING", True), ("QUIET", False)):
            all_rs = [r for r in cen(tag) if r["present"] == want]
            rs = [r for r in all_rs if not railed[r["a"]:r["b"]].any()]
            if len(rs) < 12:
                pr("   %-9s only %d of %d windows are rail-free -- skipped" % (label, len(rs), len(all_rs)))
                continue
            res = g["output"] - recon
            pr("   %-9s rail-free windows %d of %d; identity residual on them rms %.3e vs output rms %.3e"
               % (label, len(rs), len(all_rs),
                  float(np.sqrt(np.mean([np.mean(res[r["a"]:r["b"]] ** 2) for r in rs]))),
                  float(np.sqrt(np.mean([np.mean(g["output"][r["a"]:r["b"]] ** 2) for r in rs])))))
            acc = {k: [] for k in ("output", "u_meas", "u_setp", "u_rest")}
            for r in rs:
                a, b, f0 = r["a"], r["b"], r["f0"]
                for k, x in (("output", g["output"]), ("u_meas", u_meas), ("u_setp", u_setp),
                             ("u_rest", u_rest)):
                    xx = x[a:b]
                    acc[k].append(GI.band(xx - xx.mean(), f0 - 2, f0 + 2, FS))
            md = {k: float(np.median(v)) for k, v in acc.items()}
            pr("   %-9s f0 %5.2f Hz  band amplitude at f0+-2 Hz (median over %d windows):"
               % (label, float(np.median([r["f0"] for r in rs])), len(rs)))
            pr("      output %.3e | u_meas(ECHO) %.3e (%5.1f%%) | u_setp %.3e (%5.1f%%) | u_rest(FF+I) %.3e (%5.1f%%)"
               % (md["output"], md["u_meas"], 100 * md["u_meas"] / md["output"],
                  md["u_setp"], 100 * md["u_setp"] / md["output"],
                  md["u_rest"], 100 * md["u_rest"] / md["output"]))


def sec6():
    pr("=" * 112)
    pr("SECTION 6 -- THE TRANSPORT DELAY AROUND THE OUTER LOOP, IN THREE LEGS")
    pr("=" * 112)
    pr("leg1  wire angle 0x14A    -> controlsState.actualLateralAccel  (CAN rx -> carState -> controlsd)")
    pr("leg2  controlsState.output-> wire 0xE4 command                 (controlsd -> sendcan -> panda)")
    pr("leg3  wire 0xE4           -> wire angle 0x14A                  (the EPS + the mechanical plant)")
    pr("internal  meas -> output: the SAME controlsd frame, so it is a STRUCTURAL ZERO -- printed as the check")
    pr("that the estimator returns zero when the true delay is zero.")
    pr("Group delay = -d(phase)/d(omega), coherence-weighted fit over 13-25 Hz on the pooled cross-spectrum of")
    pr("the grinding windows.  CAVEAT: legs 1-3 use two DIFFERENT CAN streams (0x14A src=1, 0xE4 src=129) and")
    pr("carry whatever rx-latency difference they have -- the kit's '3.9 ms / +28 deg' trap.  The sum")
    pr("leg1+leg2+leg3 is a CLOSED cycle, so that offset cancels in the SUM even though it biases each leg.")
    pr()
    FLO_D, FHI_D = 13.0, 25.0
    for tag in ROUTES:
        g = G(tag)
        rs = [r for r in cen(tag) if r["present"]]
        if len(rs) < 12:
            pr("  %-5s too few grinding windows (%d)" % (tag, len(rs))); continue
        keys = ["wire_ang", "meas", "output", "cmd", "error"]
        f, Xs = xspec(g, rs, keys)
        S = pool(Xs, keys)
        sel = (f >= FLO_D) & (f <= FHI_D)
        f0 = float(np.median([r["f0"] for r in rs]))
        pr("-" * 104)
        pr("%s (%s)  %d grinding windows, f0 %.2f Hz" % (tag, BUILD[tag], len(rs), f0))
        tot = 0.0
        rt = 0.0
        for lab, a, b, add in (("leg1 0x14A -> meas   ", "wire_ang", "meas", 1),
                               ("leg2 output -> 0xE4  ", "output", "cmd", 1),
                               ("leg3 0xE4 -> 0x14A   ", "cmd", "wire_ang", 2),
                               ("CONTROL meas->error  ", "meas", "error", 0),
                               ("internal meas->output", "meas", "output", 0)):
            X = S[(b, a)][sel]
            ph = np.unwrap(np.angle(X))
            co = (np.abs(S[(a, b)]) ** 2 / (S[(a, a)].real * S[(b, b)].real))[sel]
            A = np.polyfit(2 * np.pi * f[sel], ph, 1, w=co)
            tau = -A[0]
            if add:
                tot += tau
            if add == 1:
                rt += tau
            pr("   %-22s group delay %+8.2f ms   mean coherence %.3f   phase at f0 %+7.1f deg"
               % (lab, tau * 1e3, float(co.mean()), np.degrees(np.angle(atf(f, S[(b, a)], f0)))))
        pr("   %-22s %+8.2f ms  <- WHEEL -> COMMAND: what an ECHO through openpilot costs"
           % ("ROUND TRIP legs 1+2", rt * 1e3))
        pr("   %-22s %+8.2f ms  <- the full cycle wheel->command->wheel (leg3's coherence is poor)"
           % ("FULL CYCLE legs 1+2+3", tot * 1e3))
        pr("   CONTROL note: error = lsf*(setp - meas), so meas->error is an EXACT zero-delay, 180 deg")
        pr("   path -- if the estimator does not return ~0 ms and ~180 deg there, do not trust legs 1-3.")


def sec7():
    pr("=" * 112)
    pr("SECTION 7 -- DOES THE RING EXIST WITH THE OUTER LOOP OPEN?")
    pr("=" * 112)
    pr("'Lateral engaged' = controlsState.active AND carControl.latActive AND 0x18F SCA AND 0xE4 STEER_REQUEST")
    pr("(the kit's own definition -- memory feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference).")
    pr("'Lateral OFF' = that conjunction false.  *** THIS OPENS BOTH LOOPS, not just the outer one: with")
    pr("STEER_REQUEST = 0 the EPS gets no LKAS command at all, so its own rate loop is open too.  A null here")
    pr("CANNOT separate inner from outer -- it only says the ring needs LKAS torque to exist. ***")
    pr("Speed-matched, because of the engaged/manual speed confound already quantified in memory/.")
    pr()
    BINS = ((0, 4), (4, 8), (8, 13), (13, 18), (18, 25), (25, 40))
    for tag in ROUTES:
        g = G(tag)
        off = (~g["eng"]) & g["have"]
        rows_off = []
        for a in range(0, g["n"] - W, STEP):
            b = a + W
            if not off[a:b].all():
                continue
            bar = g["wire_bar"][a:b]
            f0, prom = line_of(bar - bar.mean())
            if not np.isfinite(f0):
                continue
            Amp = GI.band(bar - bar.mean(), f0 - 2, f0 + 2, FS)
            rows_off.append(dict(v=float(np.median(g["vEgo"][a:b])), f0=f0, prom=prom, A=Amp,
                                 present=bool(prom >= 8.0 and Amp >= 40.0)))
        on = cen(tag)
        pr("-" * 104)
        pr("%s (%s)" % (tag, BUILD[tag]))
        pr("   %-10s | %-31s | %-31s" % ("speed m/s", "LATERAL ENGAGED", "LATERAL OFF"))
        pr("   %-10s | %6s %8s %7s %6s | %6s %8s %7s %6s"
           % ("", "n", "present", "rate", "f0", "n", "present", "rate", "f0"))
        for lo, hi in BINS:
            A1 = [r for r in on if lo <= r["v"] < hi]
            A0 = [r for r in rows_off if lo <= r["v"] < hi]
            p1 = [r for r in A1 if r["present"]]
            p0 = [r for r in A0 if r["present"]]
            pr("   %4.0f-%-5.0f | %6d %8d %7.3f %6.1f | %6d %8d %7.3f %6.1f"
               % (lo, hi, len(A1), len(p1), len(p1) / max(1, len(A1)),
                  float(np.median([r["f0"] for r in p1])) if p1 else float("nan"),
                  len(A0), len(p0), len(p0) / max(1, len(A0)),
                  float(np.median([r["f0"] for r in p0])) if p0 else float("nan")))
        nz = [(lo, hi, len([r for r in rows_off if lo <= r["v"] < hi])) for lo, hi in BINS]
        pr("   power, LATERAL OFF: with k = 0 present in n windows the 95%% upper bound on the rate is 3/n:")
        pr("     " + "  ".join("%d-%d: %s" % (lo, hi, ("%.3f" % (3.0 / n)) if n else "no exposure")
                               for lo, hi, n in nz))


def sec8():
    pr("=" * 112)
    pr("SECTION 8 -- WHAT THE COLLEAGUES' OUTPUT LPF WOULD DO TO THIS LOOP")
    pr("=" * 112)
    pr("carcontroller.py:27-66 get_civic_bosch_modified_torque_lpf_tau returns tau in 0.10-0.28 s, applied at")
    pr("carcontroller.py:294-298 as  alpha = DT_CTRL/(tau+DT_CTRL) ; lpf = alpha*cmd + (1-alpha)*lpf")
    pr("i.e. a one-pole discrete LPF at 100 Hz.  carcontroller.py:286 gates the whole block on")
    pr("  self.CP.carFingerprint == CAR.HONDA_CIVIC_BOSCH and CP.flags & HondaFlags.EPS_MODIFIED")
    pr("*** IT IS NOT ACTIVE ON THE ACCORD.  Nothing is filtering the operator's command today. ***")
    pr()
    pr("  tau(s)  fc(Hz)   |H|@13Hz  |H|@16.5Hz  |H|@20Hz  phase@16.5Hz   |H|@1Hz  phase@1Hz  |H|@0.3Hz")
    for tau in (0.02, 0.05, 0.10, 0.12, 0.16, 0.22, 0.28):
        al = 0.01 / (tau + 0.01)
        H = lambda fx: al / (1 - (1 - al) * np.exp(-2j * np.pi * fx / FS))    # noqa: E731
        pr("  %6.3f  %6.2f   %8.4f  %10.4f  %8.4f  %+12.1f  %8.4f %+10.1f  %9.4f"
           % (tau, 1 / (2 * np.pi * tau), abs(H(13)), abs(H(16.5)), abs(H(20)),
              np.degrees(np.angle(H(16.5))), abs(H(1.0)), np.degrees(np.angle(H(1.0))), abs(H(0.3))))
    pr()
    pr("Applied to the MEASURED outer-loop return ratio of section 4, at the ring:")
    for tag in ROUTES:
        rs = [r for r in cen(tag) if r["present"]]
        if len(rs) < 12:
            continue
        g = G(tag)
        keys = ["meas", "setp", "output"]
        f, Xs = xspec(g, rs, keys)
        S = pool(Xs, keys)
        f0 = float(np.median([r["f0"] for r in rs]))
        L = atf(f, S[("meas", "setp")] / S[("output", "setp")], f0) * Kwin(tag, rs)
        row = ["tau %.2f -> |L| %.5f" % (tau, abs(L * (0.01 / (tau + 0.01))
               / (1 - (1 - 0.01 / (tau + 0.01)) * np.exp(-2j * np.pi * f0 / FS))))
               for tau in (0.05, 0.10, 0.16, 0.22, 0.28)]
        pr("  %-5s f0 %5.2f Hz  |L| %.5f  |1+L| %.4f   %s"
           % (tag, f0, abs(L), abs(1 + L), " | ".join(row)))


def sec9():
    pr("=" * 112)
    pr("SECTION 9 -- (a) IS THE MEASUREMENT CHANNEL QUANTISATION-LIMITED AT THE RING?")
    pr("             (b) OPEN-LOOP TEST WITH A SHAPE-ONLY GATE AND THE OPERATING POINT SHOWN")
    pr("=" * 112)
    pr("(a) STEER_ANGLE is a 0.1 deg LSB channel (dbc scale -0.1).  A ring whose wheel-angle amplitude is")
    pr("    well below 0.1 deg cannot be measured by openpilot at all -- it would be quantisation noise, and")
    pr("    the 'echo' would be dither, not signal.  Amplitudes below are band amplitudes at f0 +- 2 Hz.")
    pr()
    pr("  %-5s %-9s %8s %9s %11s %11s %10s" %
       ("route", "build", "f0", "n_grind", "A_ang(deg)", "A_ang/LSB", "A_ang quiet"))
    for tag in ROUTES:
        rs = [r for r in cen(tag) if r["present"]]
        qs = [r for r in cen(tag) if not r["present"]]
        if len(rs) < 12:
            continue
        pr("  %-5s %-9s %8.2f %9d %11.4f %11.2f %10.4f"
           % (tag, BUILD[tag], float(np.median([r["f0"] for r in rs])), len(rs),
              float(np.median([r["A_wire_ang"] for r in rs])),
              float(np.median([r["A_wire_ang"] for r in rs])) / 0.1,
              float(np.median([r["A_wire_ang"] for r in qs]))))
    pr()
    pr("(b) The kit's record on the engaged/manual confound says: stratify on speed AND prefer a SHAPE")
    pr("    statistic to a level, because 'manual' and 'engaged' differ in how much the wheel is moving at")
    pr("    all.  So the same open-loop comparison as section 7 is repeated with the LEVEL gate removed")
    pr("    (prominence >= 8 only), and the operating point (driver-torque rms, wheel-rate rms) printed")
    pr("    so an unmatched stratum is visible rather than hidden.")
    pr()
    BINS = ((0, 4), (4, 8), (8, 13), (13, 18), (18, 25), (25, 40))
    for tag in ROUTES:
        g = G(tag)
        off = (~g["eng"]) & g["have"]
        rows_off = []
        for a in range(0, g["n"] - W, STEP):
            b = a + W
            if not off[a:b].all():
                continue
            bar = g["wire_bar"][a:b]
            f0, prom = line_of(bar - bar.mean())
            if not np.isfinite(f0):
                continue
            rows_off.append(dict(v=float(np.median(g["vEgo"][a:b])), f0=f0, prom=prom,
                                 A=GI.band(bar - bar.mean(), f0 - 2, f0 + 2, FS),
                                 bar_rms=float(np.std(bar)),
                                 rate_rms=float(np.std(g["wire_rate"][a:b]))))
        on = []
        for r in cen(tag):
            a, b = r["a"], r["b"]
            on.append(dict(r, bar_rms=float(np.std(g["wire_bar"][a:b])),
                           rate_rms=float(np.std(g["wire_rate"][a:b]))))
        pr("-" * 104)
        pr("%s (%s)   SHAPE-ONLY gate: prominence >= 8, no amplitude threshold" % (tag, BUILD[tag]))
        pr("   %-10s | %-40s | %-40s" % ("speed m/s", "LATERAL ENGAGED", "LATERAL OFF"))
        pr("   %-10s | %5s %6s %6s %7s %7s | %5s %6s %6s %7s %7s"
           % ("", "n", "rate", "f0", "barRMS", "rateRMS", "n", "rate", "f0", "barRMS", "rateRMS"))
        for lo, hi in BINS:
            A1 = [r for r in on if lo <= r["v"] < hi]
            A0 = [r for r in rows_off if lo <= r["v"] < hi]
            p1 = [r for r in A1 if r["prom"] >= 8.0]
            p0 = [r for r in A0 if r["prom"] >= 8.0]
            md = lambda L, k: (float(np.median([r[k] for r in L])) if L else float("nan"))   # noqa: E731
            pr("   %4.0f-%-5.0f | %5d %6.3f %6.1f %7.1f %7.1f | %5d %6.3f %6.1f %7.1f %7.1f"
               % (lo, hi, len(A1), len(p1) / max(1, len(A1)), md(p1, "f0"),
                  md(A1, "bar_rms"), md(A1, "rate_rms"),
                  len(A0), len(p0) / max(1, len(A0)), md(p0, "f0"),
                  md(A0, "bar_rms"), md(A0, "rate_rms")))


IDX_HI = 20.0


def sec10():
    pr("=" * 112)
    pr("SECTION 10 -- THE SAME TEST ON THE HIGH-DEMAND STRATUM (the grinding mode, not the road line)")
    pr("=" * 112)
    pr("docs/STATE.md, two-object picture: 12-26 Hz holds TWO lines, separable on LKAS DEMAND.  The")
    pr("low-demand (idx < 5) 12.4-13.8 Hz line sits at the same frequency on V282, V288, V289 and the")
    pr("Kp-LERP builds -- a road/plant line, NOT the grinding mode.  The HIGH-demand (idx >= 20) line is")
    pr("20.0 Hz on V282/V288 and 16.2-16.7 Hz on V289, and that is the grinding mode.  Sections 2/4/5 pool")
    pr("both and land near the spurious ~14.8 Hz median the record warns about; this section gates on")
    pr("median window demand index >= %.0f." % IDX_HI)
    pr()
    keys = ["meas", "setp", "output"]
    for tag in ROUTES:
        g = G(tag)
        rows = [r for r in cen(tag) if r["idx"] >= IDX_HI]
        A = [r for r in rows if r["present"]]
        B = [r for r in cen(tag) if r["idx"] >= IDX_HI and not r["present"]]
        K = KFB[tag]
        pr("-" * 104)
        pr("%s (%s)  high-demand windows %d, of which grinding-present %d   K = %.4f"
           % (tag, BUILD[tag], len(rows), len(A), K))
        if len(A) < 12:
            pr("   too few high-demand grinding windows -- skipped")
            continue
        f, Xs = xspec(g, A, keys)
        S = pool(Xs, keys)
        f0 = float(np.median([r["f0"] for r in A]))
        Piv = S[("meas", "setp")] / S[("output", "setp")]
        coh = lambda a, b: np.abs(S[(a, b)]) ** 2 / (S[(a, a)].real * S[(b, b)].real)   # noqa: E731
        rng = np.random.default_rng(11)
        bs = []
        for _ in range(400):
            sel = rng.integers(0, len(A), len(A))
            Sb = pool(Xs, keys, sel)
            bs.append(atf(f, Sb[("meas", "setp")] / Sb[("output", "setp")], f0) * K)
        bs = np.array(bs)
        L = atf(f, Piv, f0) * K
        pr("   f0 %5.2f Hz   |L_IV| %8.5f  [%.5f, %.5f]   angle %+7.1f deg   |1+L| %.4f"
           % (f0, abs(L), np.percentile(np.abs(bs), 2.5), np.percentile(np.abs(bs), 97.5),
              np.degrees(np.angle(L)), abs(1 + L)))
        pr("   coh(setp,output) %.3f  coh(setp,meas) %.3f  coh(output,meas) %.3f"
           % (float(np.interp(f0, f, coh("setp", "output"))),
              float(np.interp(f0, f, coh("setp", "meas"))),
              float(np.interp(f0, f, coh("output", "meas")))))
        pr("   |L_IV| across the band:  " +
           "  ".join("%.1fHz %.4f" % (fx, abs(atf(f, Piv, fx) * K))
                     for fx in (13, 15, 16.5, 18, 20, 22, 25)))
        # echo / forcing split on the same windows
        kp = kfit(tag)
        lsf = kp["lsf"]
        u_meas = -kp["Tp"] * kp["kp"] * lsf * g["meas"]
        u_setp = +kp["Tp"] * kp["kp"] * lsf * g["setp"]
        u_rest = kp["Tp"] * (g["i"] + g["d"] + g["f"]) + kp["T0"]
        acc = {k: [] for k in ("output", "u_meas", "u_setp", "u_rest", "ang")}
        for r in A:
            a, b, ff = r["a"], r["b"], r["f0"]
            for k, x in (("output", g["output"]), ("u_meas", u_meas), ("u_setp", u_setp),
                         ("u_rest", u_rest), ("ang", g["wire_ang"])):
                xx = x[a:b]
                acc[k].append(GI.band(xx - xx.mean(), ff - 2, ff + 2, FS))
        md = {k: float(np.median(v)) for k, v in acc.items()}
        pr("   band amplitude at f0+-2 Hz:  output %.3e | u_meas(ECHO) %.3e (%5.1f%%) | u_setp %.3e (%5.1f%%)"
           " | u_rest %.3e (%5.1f%%)"
           % (md["output"], md["u_meas"], 100 * md["u_meas"] / md["output"],
              md["u_setp"], 100 * md["u_setp"] / md["output"],
              md["u_rest"], 100 * md["u_rest"] / md["output"]))
        pr("   wheel-angle ring amplitude %.4f deg = %.2f x the 0.1 deg STEER_ANGLE LSB"
           % (md["ang"], md["ang"] / 0.1))


def sec11():
    pr("=" * 112)
    pr("SECTION 11 -- A SECOND METHOD: AN ASSUMPTION-FREE UPPER BOUND ON |L|, AND A CONTROL FOR THE IV")
    pr("=" * 112)
    pr("(a) POSITIVE CONTROL FOR THE ESTIMATOR.  The transfer from `output` to the 0xE4 wire command is")
    pr("    KNOWN exactly: carcontroller.py:306+321 give a static gain of d(0xE4)/d(torque) = -4095.2 with a")
    pr("    rate limit and about one frame of transport.  Run the SAME setpoint-instrumented estimator on it.")
    pr("    If it does not return ~-4095 with ~0-15 ms of delay, the machinery is broken and section 4 is void.")
    pr()
    for tag in ROUTES:
        g = G(tag)
        rs = [r for r in cen(tag) if r["present"]]
        if len(rs) < 12:
            continue
        keys = ["setp", "output", "cmd", "meas"]
        f, Xs = xspec(g, rs, keys)
        S = pool(Xs, keys)
        f0 = float(np.median([r["f0"] for r in rs]))
        Hiv = S[("cmd", "setp")] / S[("output", "setp")]
        h = atf(f, Hiv, f0)
        sel = (f >= 13) & (f <= 25)
        ph = np.unwrap(np.angle(Hiv[sel] * -1))     # remove the known sign inversion first
        co = (np.abs(S[("setp", "cmd")]) ** 2 / (S[("setp", "setp")].real * S[("cmd", "cmd")].real))[sel]
        A = np.polyfit(2 * np.pi * f[sel], ph, 1, w=co)
        pr("  %-5s IV estimate of d(0xE4)/d(output) at %.2f Hz: %+9.1f counts  (truth -4095.2, error %+.1f%%)"
           "   group delay %+6.2f ms"
           % (tag, f0, -abs(h) if h.real < 0 or True else abs(h), 100 * (abs(h) - 4095.2) / 4095.2,
              -A[0] * 1e3))
    pr()
    pr("(b) UPPER BOUND ON |L| WITH NO CAUSALITY ASSUMPTION AT ALL.")
    pr("    L = P*K with P = d(measurement)/d(output torque).  Factor P through the wire:")
    pr("      d(0xE4)/d(output)      = -4095.2 counts            [carcontroller.py, confirmed in section 3]")
    pr("      d(angle)/d(0xE4)       <= A_ang / A_cmd            at the ring -- this is the BOUND: the wheel's")
    pr("                                                         ring is NOT all caused by the command, so the")
    pr("                                                         ratio of the two measured ring amplitudes is")
    pr("                                                         an upper bound on the causal gain")
    pr("      d(measurement)/d(angle) = -(pi/180) * v^2 / (SR*L_wb*(1+K_us v^2))   [latcontrol_torque.py:236-237]")
    pr("    so   |L| <= K * 4095.2 * (A_ang/A_cmd) * (pi/180) * v^2 / (SR*L_wb).")
    pr("    Tyre-stiffness and roll terms only SHRINK the last factor, so dropping them keeps it a bound.")
    pr()
    SRL = 16.33 * 2.83
    pr("  %-5s %-9s %6s %7s %9s %9s %9s %8s %10s" %
       ("route", "build", "f0", "v(m/s)", "A_ang(deg)", "A_cmd", "dAng/dCmd", "K", "|L| bound"))
    for tag in ROUTES:
        rs = [r for r in cen(tag) if r["present"]]
        if len(rs) < 12:
            continue
        K = Kwin(tag, rs)
        f0 = float(np.median([r["f0"] for r in rs]))
        v = float(np.median([r["v"] for r in rs]))
        Aa = float(np.median([r["A_wire_ang"] for r in rs]))
        Ac = float(np.median([r["A_cmd"] for r in rs]))
        dmda = (np.pi / 180.0) * v ** 2 / SRL
        bound = K * 4095.2 * (Aa / Ac) * dmda
        pr("  %-5s %-9s %6.2f %7.2f %9.4f %9.2f %9.2e %8.4f %10.4f"
           % (tag, BUILD[tag], f0, v, Aa, Ac, Aa / Ac, K, bound))
    pr()
    pr("  Same bound on the HIGH-DEMAND stratum (idx >= %.0f), where the grinding mode lives:" % IDX_HI)
    pr("  %-5s %-9s %6s %7s %9s %9s %8s %10s" %
       ("route", "build", "f0", "v(m/s)", "A_ang(deg)", "A_cmd", "K", "|L| bound"))
    for tag in ROUTES:
        rs = [r for r in cen(tag) if r["present"] and r["idx"] >= IDX_HI]
        if len(rs) < 12:
            continue
        K = Kwin(tag, rs)
        f0 = float(np.median([r["f0"] for r in rs]))
        v = float(np.median([r["v"] for r in rs]))
        Aa = float(np.median([r["A_wire_ang"] for r in rs]))
        Ac = float(np.median([r["A_cmd"] for r in rs]))
        bound = K * 4095.2 * (Aa / Ac) * (np.pi / 180.0) * v ** 2 / SRL
        pr("  %-5s %-9s %6.2f %7.2f %9.4f %9.2f %8.4f %10.4f"
           % (tag, BUILD[tag], f0, v, Aa, Ac, K, bound))


def bp(x, lo=12.0, hi=26.0):
    sos = signal.butter(4, (lo, hi), btype="bandpass", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x - np.mean(x))


def sec12():
    pr("=" * 112)
    pr("SECTION 12 -- THE SECOND FEEDBACK PATH: THE FRICTION TERM INSIDE THE FEEDFORWARD")
    pr("=" * 112)
    pr("latcontrol_torque.py:547  ff += friction_scale * get_friction(error_with_lsf + 0.22*friction_jerk,")
    pr("                                lateral_accel_deadzone, friction_threshold, torque_params)")
    pr("get_friction (opendbc/car/lateral.py:190-198) is a saturating interp of that first argument, and")
    pr("the argument CONTAINS error_with_lsf.  So `f` carries a SECOND feedback branch in parallel with P,")
    pr("and section 3's K understates the loop.  friction_threshold = 0.30 everywhere for this car")
    pr("(vehicle_tunes.py:15, 1330-1335) and friction_scale = 1.0 (latcontrol_torque.py:381).")
    pr()
    pr("MEASURED, not assumed: band-pass every signal to 12-26 Hz (4th-order Butterworth, zero phase) over")
    pr("the GRINDING windows and regress f_bp on [meas, setp, desiredCurvature, desiredLateralJerk,")
    pr("setp/v^2]_bp.  `a` is the meas coefficient = d(f)/d(measurement) at the ring, the describing-function")
    pr("gain of the friction nonlinearity.  The other four control for the Accord rate-plant feedforward")
    pr(":575-586, which is setpoint-driven through a NONLINEAR map (curv_des = setp/v^2 then")
    pr("get_steer_from_curvature), so `setp` alone does not span it and `a` absorbs the residue -- which is")
    pr("why the estimate below RUNS ABOVE its own theoretical ceiling on two routes.  Treat it as an")
    pr("UPPER-biased cross-check on the ceiling, not as a point estimate.")
    pr()
    pr("Then   K_total = lsf*(kp + |a|)/LAF   against section 3's   K_P = lsf*kp/LAF.")
    pr()
    hdr = ("  %-5s %-9s %7s %8s %8s %8s %8s %9s %9s %9s" %
           ("route", "build", "f0", "a", "R2", "kp", "LAF", "K_P", "K_total", "ratio"))
    for stratum, gate in (("ALL grinding windows", lambda r: r["present"]),
                          ("HIGH-DEMAND (idx>=20)", lambda r: r["present"] and r["idx"] >= IDX_HI)):
        pr(stratum)
        pr(hdr)
        for tag in ROUTES:
            g = G(tag)
            rs = [r for r in cen(tag) if gate(r)]
            if len(rs) < 12:
                continue
            kp = kfit(tag)
            X, Y = [], []
            for r in rs:
                a0, b0 = r["a"], r["b"]
                X.append(np.c_[bp(g["meas"][a0:b0]), bp(g["setp"][a0:b0]),
                               bp(g["desCurv"][a0:b0]), bp(g["djerk"][a0:b0]),
                               bp(g["setp"][a0:b0] / np.maximum(g["vEgo"][a0:b0], 1.0) ** 2)])
                Y.append(bp(g["f"][a0:b0]))
            X = np.vstack(X)
            Y = np.concatenate(Y)
            coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
            resid = Y - X @ coef
            R2 = 1 - np.var(resid) / np.var(Y)
            lsf = float(np.median([np.median(kp["lsf"][r["a"]:r["b"]]) for r in rs]))
            K_P = lsf * kp["kp"] / kp["LAF"]
            K_tot = lsf * (kp["kp"] + abs(coef[0])) / kp["LAF"]
            pr("  %-5s %-9s %7.2f %8.4f %8.4f %8.4f %8.4f %9.4f %9.4f %9.2f"
               % (tag, BUILD[tag], float(np.median([r["f0"] for r in rs])), coef[0], R2,
                  kp["kp"], kp["LAF"], K_P, K_tot, K_tot / K_P))
        pr()
    pr("Theoretical ceiling on that slope, for comparison: |a| <= friction*LAF/0.30.  carParams ships")
    pr("friction = 0.21205 and latAccelFactor = 1.68933 for HONDA_ACCORD, but the LIVE latAccelFactor")
    pr("measured in section 3 is 2.1100 (r39/r35) and 6.0000 (r5e/r62/r63), so the live friction is not")
    pr("carParams' either and the ceiling is quoted for a RANGE of friction:")
    for LAF in (2.11, 6.00):
        pr("   LAF %.2f:  " % LAF + "   ".join("friction %.2f -> |a| <= %.3f" % (fr, fr * LAF / 0.30)
                                               for fr in (0.03, 0.085, 0.147, 0.212)))
    pr()
    pr("CORRECTED |L| -- section 4's IV plant estimate rescaled by K_total/K_P, high-demand stratum:")
    keys = ["meas", "setp", "output"]
    for tag in ROUTES:
        g = G(tag)
        rs = [r for r in cen(tag) if r["present"] and r["idx"] >= IDX_HI]
        if len(rs) < 12:
            continue
        kp = kfit(tag)
        X, Y = [], []
        for r in rs:
            a0, b0 = r["a"], r["b"]
            X.append(np.c_[bp(g["meas"][a0:b0]), bp(g["setp"][a0:b0]),
                           bp(g["desCurv"][a0:b0]), bp(g["djerk"][a0:b0]),
                           bp(g["setp"][a0:b0] / np.maximum(g["vEgo"][a0:b0], 1.0) ** 2)])
            Y.append(bp(g["f"][a0:b0]))
        coef, *_ = np.linalg.lstsq(np.vstack(X), np.concatenate(Y), rcond=None)
        lsf = float(np.median([np.median(kp["lsf"][r["a"]:r["b"]]) for r in rs]))
        K_tot = lsf * (kp["kp"] + abs(coef[0])) / kp["LAF"]
        f, Xs = xspec(g, rs, keys)
        S = pool(Xs, keys)
        f0 = float(np.median([r["f0"] for r in rs]))
        P = atf(f, S[("meas", "setp")] / S[("output", "setp")], f0)
        v = float(np.median([r["v"] for r in rs]))
        Aa = float(np.median([r["A_wire_ang"] for r in rs]))
        Ac = float(np.median([r["A_cmd"] for r in rs]))
        bound = K_tot * 4095.2 * (Aa / Ac) * (np.pi / 180.0) * v ** 2 / (16.33 * 2.83)
        pr("  %-5s f0 %5.2f Hz   K_total %.4f   |L_IV| %.5f   |1+L| %.4f   |L| UPPER BOUND %.4f"
           % (tag, f0, K_tot, abs(P * K_tot), abs(1 + P * K_tot), bound))


if __name__ == "__main__":
    args = sys.argv[1:] or ["1"]
    for tag in ROUTES:
        kfit(tag)
    for s in args:
        globals()["sec%s" % s]()
    save("outerloop_id.txt")
