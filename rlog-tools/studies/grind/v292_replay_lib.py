# -*- coding: utf-8 -*-
"""v292_replay_lib.py -- byte-exact electronics + closed-loop replay machinery for the V292 prediction
on the operator's OWN recorded grinding episodes.  Agent `replay`, 2026-09-13.

ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing, edits no build script.

WHAT IS HERE
  Elec        the byte-exact LKAS rate-PID electronics as an explicit tick march.  The FEEDBACK LAG
              and the OUTPUT LAG are INTEGER (two separate `sar` floors each, as the listing shows);
              the forward path uses the record's own float-then-floor arithmetic so that the open-loop
              run is directly comparable to `grind_incident_r35.simulate`.
              `ef=True` adds the V292 cave's first-order error feedback on the two feedback-lag floors.
  plant_march the fitted plant as an explicit IIR recursion (the design290b family's ZOH discretisation
              plus its integer-tick delay), so the loop can be CLOSED tick by tick.
  invert_d    the residual disturbance that makes the V282 closed loop reproduce a recorded window
              EXACTLY.  It is a causal marching inversion, not a spectral division, so it is well posed
              at every frequency -- see the docstring.

🛑 A DEVIATION FROM THE RECORD'S MIRROR, FOUND HERE AND REPORTED
`grind_incident_r35.simulate` computes the feedback lag as  s' = floor((a*s + b*x)/1024)  -- ONE floor
of the SUM.  The listing (0x28F9A `sar 0xa,r7` and 0x28FA0 `sar 0xa,r9`, then 0x28FA2 `add r7,r9`)
computes  s' = (a*s >> 10) + (b*x >> 10)  -- TWO SEPARATE floors.  The V292 cave exists precisely to
repair those two floors, so the single-floor form CANNOT represent the edit.  Both forms are provided
(`two_floor=False` reproduces the record) and the difference is measured in section 1.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import creep20_loop_id as C20            # noqa: E402
import v280_map_profiles as V            # noqa: E402
import grind_incident_r35 as GI          # noqa: E402
import adv_v290_physics as A             # noqa: E402

FS, FS1K = 100.0, 1000.0
CPD = 8.0

# ------------------------------------------------------------------------------------------------
# cells, read from the images themselves (NOT from a build script's constants)
# ------------------------------------------------------------------------------------------------
V282_FB = (923, 1560)
V292_FB = (962, 958)
V282_R24ARM = 5244
V292_R24ARM = 4725
KAPPA = 2353.0 / 5244.0          # b_of_f_v282.GAIN_EFFECTIVE / GAIN_FLOWN -- the wire-settled arm
K_MOTOR = 5346.0 / 32768.0       # ADV-V292-B section 7.1: the r24 lane shares the motor gain


def sar(v, k):
    return int(v) >> int(k)


def clampi(v, lim):
    return -lim if v < -lim else (lim if v > lim else v)


# ------------------------------------------------------------------------------------------------
# 1.  THE ELECTRONICS -- one tick at a time
# ------------------------------------------------------------------------------------------------
class Elec:
    """byte-exact LKAS rate-PID electronics.

    x        internal rate operand, RAW counts, = -(0x18F wire rate).  INTEGER, as the ECU sees it.
    sp       setpoint counts (float; the record's LERP output)
    returns  T, the delivered torque counts at the 427 tap
    """

    def __init__(self, c, fb=V282_FB, ef=False, two_floor=True, kd=128.0):
        self.c = c
        self.fb_a, self.fb_b = int(fb[0]), int(fb[1])
        self.ef = bool(ef)
        self.two_floor = bool(two_floor)
        self.kd = float(kd)
        self.lag_a, self.lag_b = int(c["lag_a"]), int(c["lag_b"])
        self.gain = int(c["gain"])
        self.fb_clamp = int(c["fb_clamp"])
        self.reset()

    def reset(self):
        self.s_fb = 0
        self.rem_b = 0
        self.rem_a = 0
        self.s_lag = 0
        self.E_prev = 0.0
        self.first = True

    # -- the feedback lag, byte for byte -----------------------------------------------------
    def fb_tick(self, x):
        a, b = self.fb_a, self.fb_b
        s = self.s_fb
        if self.two_floor:
            t_b = b * x + self.rem_b
            step_b = t_b >> 10
            t_a = a * s + self.rem_a
            step_a = t_a >> 10
            if self.ef:
                self.rem_b = t_b & 0x3FF
                self.rem_a = t_a & 0x3FF
            s_new = step_a + step_b
        else:                                   # the record's mirror: ONE floor of the sum
            s_new = (a * s + b * x) >> 10
        out = s + s_new
        self.s_fb = s_new                       # stored UNCLAMPED (0x28FA8), per ADV-V292-B section 2
        return clampi(out, self.fb_clamp)

    # -- the whole chain ----------------------------------------------------------------------
    def run(self, x, sp, kp, m, eng, n=None):
        """march n ticks.  x int array, sp/kp/m float arrays, eng bool array."""
        n = len(x) if n is None else n
        c = self.c
        Pc, Dc, Sc, Tc = V.P_CLAMP, V.D_CLAMP, V.SUM_CLAMP, V.OUT_CAP
        la, lb, g = self.lag_a, self.lag_b, self.gain
        kd = self.kd
        T = np.empty(n)
        TP = np.empty(n)
        TD = np.empty(n)
        Earr = np.empty(n)
        fbarr = np.empty(n)
        # the P-only / D-only torques need their own output-lag states
        s_lag_P = 0
        s_lag_D = 0
        for i in range(n):
            fb = self.fb_tick(int(x[i]))
            E = 32.0 * sp[i] - fb
            dE = 0.0 if self.first else (E - self.E_prev)
            self.first = False
            self.E_prev = E
            P = clampi(int(np.floor(E * kp[i] / 256.0)), Pc)
            D = clampi(int(np.floor(dE * kd / 8.0)), Dc)
            mi = m[i]
            if eng[i]:
                S = clampi(int(np.floor(mi * (P + D) / 256.0)), Sc)
                SP_ = clampi(int(np.floor(mi * P / 256.0)), Sc)
                SD_ = clampi(int(np.floor(mi * D / 256.0)), Sc)
            else:
                S = SP_ = SD_ = 0
            s_new = ((la * self.s_lag) >> 10) + ((lb * S) >> 10)
            y = (self.s_lag + s_new) >> 5
            self.s_lag = s_new
            T[i] = clampi((-(y * g)) >> 15, Tc)
            sP = ((la * s_lag_P) >> 10) + ((lb * SP_) >> 10)
            TP[i] = clampi((-(((s_lag_P + sP) >> 5) * g)) >> 15, Tc)
            s_lag_P = sP
            sD = ((la * s_lag_D) >> 10) + ((lb * SD_) >> 10)
            TD[i] = clampi((-(((s_lag_D + sD) >> 5) * g)) >> 15, Tc)
            s_lag_D = sD
            Earr[i] = E
            fbarr[i] = fb
        return dict(T=T, TP=TP, TD=TD, E=Earr, fb=fbarr)


# ------------------------------------------------------------------------------------------------
# 2.  WINDOW PREPARATION -- the same slice, upsampling and arms the record's mirror uses
# ------------------------------------------------------------------------------------------------
def prep_window(g, a, b, c, cmd=None, wire=None):
    """reproduce grind_incident_r35.simulate's own framing: seg, 1 kHz axis, ZOH command, live arms."""
    seg = slice(max(0, a - 50), min(len(g["t"]), b + 10))
    n1 = (seg.stop - seg.start) * 10
    t1k = g["t"][seg.start] + np.arange(n1) * g["P18"] / 10
    w = (g["wire"] if wire is None else wire)[seg]
    wire1k = C20.up1k(np.asarray(w, float))
    cmd_s = (g["cmd"] if cmd is None else cmd)[seg]
    bar_s = g["bar"][seg]
    cmd1k = np.repeat(cmd_s, 10)
    bar1k = np.repeat(bar_s, 10)
    idx, sgn = GI.demand_live(cmd1k, bar1k, c)
    idx = np.round(idx)
    sp = sgn * GI.lerp(c["map_X"], c["map_Y"], idx)
    kp = GI.lerp(c["kp_X"], c["kp_Y"], idx)
    B_ = GI.lerp(c["fadeB"][0], c["fadeB"][1], np.abs(bar1k) // 32)
    m = ((255.0 * B_).astype(np.int64) & 0xFFFF) >> 8
    eng = np.repeat(g["eng"][seg], 10)
    return dict(seg=seg, n=n1, t1k=t1k, wire1k=wire1k, sp=sp, kp=kp, m=m.astype(float),
                eng=eng, idx=idx, bar1k=bar1k, cmd1k=cmd1k)


# ------------------------------------------------------------------------------------------------
# 3.  THE PLANT -- an explicit recursion so the loop can be closed
# ------------------------------------------------------------------------------------------------
class PlantIIR:
    """wheel rate in RAW counts per delivered torque count: wire = CPD * G(z) * T.

    num/den are the design290b family's own ZOH discretisation in w = z^-1, with the integer-tick
    transport delay already prepended to `num` (A.Plant).  den[0] == 1.
    """

    def __init__(self, pl):
        self.num = np.asarray(pl.num, float) * CPD
        self.den = np.asarray(pl.den, float)
        assert abs(self.den[0] - 1.0) < 1e-12
        self.nb = len(self.num)
        self.na = len(self.den)
        self.nd = pl.nd
        assert self.nd >= 1, "the plant must carry at least one tick of delay for the loop to march"
        self.reset()

    def reset(self):
        self.Tb = np.zeros(self.nb)          # Tb[k] = T[n-k]
        self.ub = np.zeros(max(self.na, 1))  # BEFORE step_pre: ub[k] = u[n-1-k]

    def step_pre(self):
        """u[n] = CPD*(G conv T)[n], in RAW WIRE COUNTS.

        num[0] == 0 because the plant carries at least one tick of transport delay, so u[n] does not
        depend on T[n] and can be evaluated BEFORE this tick's torque is known.  That is what makes the
        loop marchable, and it makes this recursion identical to `batch` sample for sample.
        """
        self.Tb[1:] = self.Tb[:-1]
        self.Tb[0] = 0.0                     # placeholder; num[0] == 0
        u = float(self.num @ self.Tb) - float(self.den[1:] @ self.ub[:self.na - 1])
        self.ub[1:] = self.ub[:-1]
        self.ub[0] = u
        return u

    def step_post(self, Tn):
        self.Tb[0] = Tn

    def batch(self, T):
        """offline: the same recursion, vectorised (used for the disturbance inversion)."""
        return signal.lfilter(self.num, self.den, np.asarray(T, float))


# ------------------------------------------------------------------------------------------------
# 4.  THE CLOSED LOOP
# ------------------------------------------------------------------------------------------------
def closed_run(el, pl, W, d, extra_T=None):
    """march the closed loop:  wire[n] = CPD*(G conv T)[n] + d[n] ;  x[n] = -round(wire[n]).

    `extra_T` (optional) is an additional torque injected at the plant input each tick -- used for the
    r24-arm delta branch, whose value for tick n is computed from the PREVIOUS outer iteration's wire.
    Returns dict with T, wire, and the electronics' internals.
    """
    n = W["n"]
    sp, kp, m, eng = W["sp"], W["kp"], W["m"], W["eng"]
    el.reset()
    pl.reset()
    c = el.c
    Pc, Dc, Sc, Tc = V.P_CLAMP, V.D_CLAMP, V.SUM_CLAMP, V.OUT_CAP
    la, lb, g = el.lag_a, el.lag_b, el.gain
    kd = el.kd
    T = np.empty(n)
    wire = np.empty(n)
    ex = np.zeros(n) if extra_T is None else np.asarray(extra_T, float)
    for i in range(n):
        wi = pl.step_pre() + d[i]
        wire[i] = wi
        fb = el.fb_tick(-int(round(wi)))
        E = 32.0 * sp[i] - fb
        dE = 0.0 if el.first else (E - el.E_prev)
        el.first = False
        el.E_prev = E
        P = clampi(int(np.floor(E * kp[i] / 256.0)), Pc)
        D = clampi(int(np.floor(dE * kd / 8.0)), Dc)
        S = clampi(int(np.floor(m[i] * (P + D) / 256.0)), Sc) if eng[i] else 0
        s_new = ((la * el.s_lag) >> 10) + ((lb * S) >> 10)
        y = (el.s_lag + s_new) >> 5
        el.s_lag = s_new
        Ti = clampi((-(y * g)) >> 15, Tc)
        T[i] = Ti
        pl.step_post(Ti + ex[i])
    return dict(T=T, wire=wire)


def invert_d(el, pl, W, wire1k):
    """the residual disturbance that makes the V282 closed loop reproduce this window EXACTLY.

    METHOD, and why it is well posed.  The plant carries nd >= 6 ticks of pure transport delay, so
    wire[n] depends on T[n-nd..] only.  Run the electronics OPEN loop on the recorded wire to get
    T_rec; filter T_rec through the plant to get the part of the wire the loop itself explains; the
    remainder is everything else (road, driver, plant mismatch, unmodelled lanes):

        d[n] = wire_rec[n] - CPD*(G conv T_rec)[n]

    Marching the closed loop with this d reproduces wire_rec and T_rec bit for bit -- it is a causal
    marching inversion, NOT a spectral division, so there is NO band in which it is ill posed and no
    regularisation anywhere.  The price is that d is not a physical disturbance: it absorbs plant
    mismatch, and to the extent the fitted plant is wrong the counterfactual is biased.  That is why
    the whole table is reported across the plant family, not on one fit.
    """
    el.reset()
    x = -np.round(np.asarray(wire1k, float)).astype(np.int64)
    S = el.run(x, W["sp"], W["kp"], W["m"], W["eng"])
    u = pl.batch(S["T"])
    d = np.asarray(wire1k, float) - u          # `u` is ALREADY in raw wire counts (CPD folded into num)
    return d, S


# ------------------------------------------------------------------------------------------------
# 5.  THE r24 ARM DELTA -- a parallel feedback branch, folded the way the record folds it
# ------------------------------------------------------------------------------------------------
def r24_delta_response(f, arm_from=V282_R24ARM, arm_to=V292_R24ARM, kappa=KAPPA,
                       with_motor_gain=True, stratum="loaded_any", source="fit"):
    """H(f) such that  dT_r24 = H(f) * wire  is the CHANGE in delivered r24-lane torque when 0xC6446
    moves arm_from -> arm_to.

    T_r24 = K * R_r24 * x  with  x = -wire  and  R_r24(f) = -(arm/1024) * D4(f) * B(f)
        =>  T_r24 = +K * (arm/1024) * D4 * B * wire
        =>  dT     = -K * ((arm_from - arm_to)/1024) * D4 * B * wire
    The arm is taken at the WIRE-SETTLED effective value (kappa 0.449): the cave's bit-6 duty says the
    lane delivers 0.43-0.52 of the closed form.  `with_motor_gain=False` drops K, which is how the
    record's inherited fold was written (ADV-V292-B section 7.1 shows that over-weights the lane x6.13).
    """
    import b_of_f_v282 as BOF
    f = np.asarray(f, float)
    B = BOF.B_fit(np.maximum(f, 1e-6), stratum=stratum) if source == "fit" else \
        BOF.B_table(np.clip(f, 3.0, 30.0), stratum=stratum)
    K = K_MOTOR if with_motor_gain else 1.0
    darm = (arm_from - arm_to) * kappa
    return -K * (darm / 1024.0) * BOF.D4(f) * B


def apply_fr(x, H_of_f, fs=FS1K):
    """apply a complex frequency response to a real signal over a whole window (FFT, exact, acausal).

    Used ONLY for the small r24-arm DELTA branch, inside an outer fixed-point iteration -- never for
    the main loop, which is marched causally.
    """
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    return np.fft.irfft(X * H_of_f(f), n=n)


# ------------------------------------------------------------------------------------------------
# 6.  MEASUREMENT
# ------------------------------------------------------------------------------------------------
def band_amp(x, lo, hi, fs=FS1K):
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return float(np.sqrt(2.0) * np.sqrt(np.mean(signal.sosfiltfilt(sos, np.asarray(x, float)) ** 2)))


def out_of_band_rms(x, bands, fs=FS1K):
    """rms of the signal with every listed band notched out -- the authority check."""
    y = np.asarray(x, float)
    for lo, hi in bands:
        y = signal.sosfiltfilt(signal.butter(4, [lo, hi], btype="bandstop", fs=fs, output="sos"), y)
    return float(np.sqrt(np.mean(y ** 2)))


def env_halflife(x, f0, fs=FS1K, bw=2.0, skip=500):
    """the record's half-peak decay metric: demodulate at f0, take the largest peak, fit the log
    envelope from the peak down to 10 % of it, return the HALF-LIFE in ms (ln2 / -slope)."""
    y = np.asarray(x, float)[skip:]
    if len(y) < 200:
        return np.nan
    env = GI.envelope(y, f0, fs, bw=bw)
    t = np.arange(len(env)) / fs
    k = int(np.argmax(env))
    pk = env[k]
    tail = env[k:]
    below = np.flatnonzero(tail <= 0.1 * pk)
    j = k + (below[0] if len(below) else len(tail) - 1)
    if j - k < int(0.02 * fs):
        return np.nan
    sl = np.polyfit(t[k:j], np.log(np.maximum(env[k:j], 1e-12)), 1)[0]
    if sl >= -1e-9:
        return np.inf
    return float(np.log(2.0) / (-sl) * 1e3)


# ------------------------------------------------------------------------------------------------
# 7.  THE MATCHED FREE RING-DOWN -- the ring-down time, measured the same way in both arms
# ------------------------------------------------------------------------------------------------
def kick_response(elec_kw, pl, W, d, k0, amp=64.0, extra_T=None):
    """the INCREMENTAL response to a one-tick wheel-rate kick at sample k0, taken as the difference of
    two closed byte-exact runs at the SAME operating point.

    Why this and not the envelope of the driven ring: the driven envelope is set by the disturbance's
    own envelope as much as by the loop, and the two arms' rings are different sizes, so a half-peak
    decay fitted on them is not a matched measurement.  The difference of two runs that share d, the
    command and the plant isolates the loop's OWN ring-down at the operating point the episode actually
    visits -- the clamps, the fade and the quantisers are all at their real states.
    """
    base = closed_run(Elec(**elec_kw), PlantIIR(pl), W, d, extra_T=extra_T)
    d2 = np.array(d, float)
    d2[k0] += amp
    pert = closed_run(Elec(**elec_kw), PlantIIR(pl), W, d2, extra_T=extra_T)
    return pert["T"] - base["T"], pert["wire"] - base["wire"]


def decay_halflife(y, k0, fs=FS1K, t_lo=0.040, t_hi=0.400, band=(12.0, 30.0), floor=0.05):
    """half-life (ms) of an incremental ring-down, fitted on the analytic envelope of the difference
    band-passed 12-30 Hz (zero phase, applied identically to both arms), from k0+t_lo to whichever
    comes first: k0+t_hi, or the point the envelope falls below `floor` x its peak.

    The band-pass is what makes this measurable at all: the raw difference of two INTEGER trajectories
    is a few counts and its Hilbert phase does not rotate, so an unfiltered fit returns nonsense (r2
    0.0-0.4, instantaneous frequency 0 Hz).  The kick must also be large enough that the incremental
    response clears the 1-count quantiser -- see `kick_linearity` in the driver.
    """
    y = np.asarray(y, float)
    sos = signal.butter(4, list(band), btype="bandpass", fs=fs, output="sos")
    yb = signal.sosfiltfilt(sos, y)
    env = np.abs(signal.hilbert(yb))
    a = int(k0 + t_lo * fs)
    b = int(min(len(y), k0 + t_hi * fs))
    if b - a < 60:
        return np.nan, np.nan, np.nan
    pk = float(env[k0:b].max())
    if pk <= 0:
        return np.nan, np.nan, np.nan
    seg = env[a:b]
    below = np.flatnonzero(seg < floor * pk)
    if len(below):
        b = a + max(int(0.060 * fs), int(below[0]))
        seg = env[a:b]
    if len(seg) < 60:
        return np.nan, np.nan, np.nan
    t = np.arange(len(seg)) / fs
    ly = np.log(np.maximum(seg, 1e-12))
    sl, ic = np.polyfit(t, ly, 1)
    r2 = float(1 - np.sum((ly - (ic + sl * t)) ** 2) / max(np.sum((ly - ly.mean()) ** 2), 1e-30))
    ph = np.unwrap(np.angle(signal.hilbert(yb)))[a:b]
    fi = float(np.median(np.gradient(ph) * fs / (2 * np.pi)))
    if sl >= -1e-9:
        return np.inf, fi, r2
    return float(np.log(2.0) / (-sl) * 1e3), fi, r2
