# -*- coding: utf-8 -*-
"""v294_plant.py -- THE PLANT FAMILY the V294 LKAS lane acts on, identified from route
75604b0a432fdc89_00000071--a7b8ba5d9d (r71b_v294), as discrete 1 kHz simulators in FIRMWARE UNITS.

    import sys; sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
    import v294_plant as VP
    fam = VP.family()                           # {"nominal": ..., "J_lo": ..., "J_hi": ..., ..., "light_b": ...}
    p = fam["nominal"].at(v=12.0)               # PlantParams at one speed (every field a float)
    sim = VP.simulate_closed(cmd_frames, fam["nominal"], cells=VP.v294_cells())       # command -> byte-exact PID -> plant
    python v294_plant.py --selftest             # PID mirror == golden model; plant sanity; family printed

UNITS (the PID's own).  T = delivered lane torque gp-0x6b38 in T counts (+ = steer RIGHT; the 427 tap's unit; rail 2461).
x = the wheel-rate operand gp-0x6a56 in COUNTS, 8.00 counts per deg/s (EVIDENCE in the record: 0x55B48 bytes, V292 wire).
th = steering angle (deg, + LEFT), om = th' (deg/s, + LEFT).  The plant input is u = -T(t - tau) (+ LEFT).

    J*om' + b*om + k*sat*tanh(th/sat) + Ffric = u + d            (T counts;  J per deg/s^2, b per deg/s, k per deg)
    Ffric = Fc*sgn(om) sliding; stuck (om == 0) while |u + d - spring| <= Fs  (Karnopp)
    x[n] = round(8 * (th_m[n] - th_m[n-w]) / (w ms))              the rate former (w = 3 ms; BELIEF, record)
    To the PID's x unit: J_x = J/8 T counts per (count/s), b_x = b/8 T counts per count.

Optional (off by default): a collocated TWO-MASS flexible mode (f2 Hz, zeta2, wheel share r2) -- the prior's
"20 Hz plant mode" family (redo physics, rp4: f 12-40 Hz, r2 0.2-0.8, zeta 0.02-0.05).  NOT identified from this drive
(see V294-PLANT-IDENT-r71b.md section 3: with the 427 tap at 50 Hz and the loop's weak HF content, nothing above
~8 Hz is identifiable here) -- it is a design stress case, not a measurement.

WHICH NUMBERS ARE WHAT (full detail, CIs and the held-out scores in V294-PLANT-IDENT-r71b.md; family() docstring):
  the members are read from _scratch/p5c.json (J profile) and _scratch/p5b_ms.json (multiple-shooting fit) when present,
  else from the printed fallback.  They are OUTPUT-ERROR FITS on this drive, scored on HELD-OUT data (p7_validate_out.txt):
  20 s free-run replays from the command alone give angle R2 0.66-0.93 and rate R2 0.76/0.54/0.41/0.24/0.22 by band
  (0-5 ... 22+); the prior light-b world gives rate R2 -0.73..-1.88 above 10 m/s.  On 1 s windows the RATE detail is
  NOT reproduced above 5 m/s (pre-registered F4 FIRES at 5-10 and 10-15 m/s: the plant is NOT READY there).  J is
  identified only at 0-5 m/s (0.1-0.3, best 0.2); above 10 m/s the drive does not constrain it (p5c).
  "light_b" is the PRIOR world converted at 2625.4 T counts per u -- BELIEF carried for comparison.

ANALYSIS ONLY.  Sends nothing, flashes nothing.
"""
import json
import math
import os
import sys
from dataclasses import dataclass, field, replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
for _p in (os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"),
           os.path.join(KIT, "rlog-tools", "studies", "grind"),
           os.path.join(KIT, "analysis-2020accord", "model"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

T_PER_U = 2625.4                       # T counts per openpilot torque unit (V293/V294 surface slope; redo physics)
V_CENTRES = np.array([3.1, 8.0, 11.9, 17.0, 26.9])     # schedule KNOTS, m/s: the mean speed of each band's FIT windows
#   (0-5, 5-10, 10-15, 15-22, 22+), where each band's fit applies.  A first version used the band centres 2.5/7.5/12.5/
#   18.5/25: at 0-5 m/s the friction falls steeply with speed (76 -> 13.5 counts between the first two knots) and the
#   held-out 1 s rate R2 of the interpolated family dropped from 0.75 (band-constant) to 0.03 -- fixed 2026-09-30.
BAND_NAMES = ("0-5", "5-10", "10-15", "15-22", "22+")


def sat_prior(v):
    """spring saturation angle, deg: the prior hold map's sat(v) = 19.3 + 546 exp(-v/3.01) (BELIEF, route 70/71 fit)."""
    return 19.3 + 546.0 * np.exp(-np.asarray(v, float) / 3.01)


# ======================================================================================================================
# parameters
# ======================================================================================================================
@dataclass
class PlantParams:
    J: float                  # T counts per deg/s^2
    b: float                  # T counts per deg/s
    k: float                  # T counts per deg (small-angle slope of the spring)
    Fc: float                 # Coulomb (kinetic) friction, T counts
    Fs: float                 # static (breakaway) friction, T counts, >= Fc
    sat: float = 1e9          # deg; spring = k*sat*tanh(th/sat)
    tau_ms: int = 2           # transport delay T -> motor torque, ms
    rate_win_ms: int = 3      # rate-former window, ms
    f2: float = 0.0           # Hz; 0 = rigid (no flexible mode)
    zeta2: float = 0.05
    r2: float = 0.2           # wheel-side share of J in the two-mass option


@dataclass
class PlantFamilyMember:
    """a speed-scheduled plant: per-band values at V_CENTRES, linearly interpolated in speed (flat outside)."""
    name: str
    J: np.ndarray
    b: np.ndarray
    k: np.ndarray
    Fc: np.ndarray
    Fs: np.ndarray
    tau_ms: int = 2
    rate_win_ms: int = 3
    use_sat: bool = True
    f2: float = 0.0
    zeta2: float = 0.05
    r2: float = 0.2
    note: str = ""

    def arrays_at(self, v):
        v = np.asarray(v, float)
        f = lambda a: np.interp(v, V_CENTRES, np.asarray(a, float))  # noqa: E731
        sat = sat_prior(v) if self.use_sat else np.full(v.shape, 1e9)
        return dict(J=f(self.J), b=f(self.b), k=f(self.k), Fc=f(self.Fc), Fs=f(self.Fs), sat=sat)

    def at(self, v):
        a = self.arrays_at(np.array([v]))
        return PlantParams(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), Fc=float(a["Fc"][0]),
                           Fs=float(a["Fs"][0]), sat=float(a["sat"][0]), tau_ms=self.tau_ms, rate_win_ms=self.rate_win_ms,
                           f2=self.f2, zeta2=self.zeta2, r2=self.r2)

    def with_mode20(self, f2=20.0, zeta2=0.05, r2=0.2):
        return replace(self, name=self.name + "+mode%.0fHz" % f2, f2=f2, zeta2=zeta2, r2=r2)


def _prior_light_b():
    """the PRIOR 'light-b' world, converted to T counts (BELIEF; memory accord-steering-mode-2hz-inertia...)."""
    kv = [2, 4, 6, 8, 10, 12.5, 15, 17.5, 20, 23, 28]
    ku = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134]
    k = np.interp(V_CENTRES, kv, ku) * T_PER_U
    n = len(V_CENTRES)
    return PlantFamilyMember("light_b", J=np.full(n, 8e-5 * T_PER_U), b=np.full(n, 6e-4 * T_PER_U), k=k,
                             Fc=np.full(n, 0.012 * T_PER_U), Fs=np.full(n, 0.020 * T_PER_U), tau_ms=2,
                             note="PRIOR (BELIEF): fork tunes @54ff1ea39 / route 70-71 ident; J 8e-5 u, b 6e-4 u, hold-map k,"
                                  " Coulomb 0.012 u, static 0.020 u, x 2625.4 T/u")


# fallback constants = the p5c J-profile rows at J = 0.2 as printed (used only if _scratch/p5c.json is absent)
_FALLBACK = dict(J=[0.2] * 5, b=[4.94, 5.24, 9.76, 20.65, 26.41], k=[6.5, 20.2, 24.3, 79.7, 55.8],
                 Fc=[76.2, 13.5, 15.8, 7.9, 4.4], Fs=[94.7, 18.9, 18.6, 10.0, 5.6], tau_ms=2)


def _profile_rows(path):
    """{J: (b, k, Fc, Fs) arrays over the five bands} from p5c.json (the J profile: b/k/F refitted at each fixed J)."""
    rows = json.load(open(path))
    out = {}
    for r in rows:
        out.setdefault(r["J"], [None] * 5)[r["band"]] = (r["b"], r["k"], r["Fc"], r["Fs"])
    return {J: tuple(np.array([v[i] for v in vals], float) for i in range(4)) for J, vals in out.items() if all(vals)}


def family(path=None):
    """THE DELIVERED FAMILY (speed-scheduled; per-band values at V_CENTRES, linear in speed).  Every member except the
    prior and the stress variants is a MULTIPLE-SHOOTING OUTPUT-ERROR FIT on this drive (p5b/p5c), refitted as a whole at
    its J, so each corner is self-consistent (a J corner is not the nominal with J swapped):

      nominal     J 0.20 (the J profile's held-out optimum at 0-5 m/s, the only band where J is identified; = the prior's
                  8e-5 u = 0.21) with b/k/Fc/Fs refitted per band at that J                            (p5c)
      J_lo / J_hi / J_hi2   J 0.1 / 0.5 / 0.8, each with its own refitted b/k/F                        (p5c)
      b_lo        nominal b / 1.8 at >= 10 m/s (the G3a bias of this estimator at speed: b x1.7-1.9), x0.7 below
      b_hi        nominal b x 1.5
      F_hi        nominal Fc, Fs x 2 (the G3a bias at speed: Fc x0.46-0.58), F_lo  x 0.5
      tau0 / tau6 nominal with 0 / 6 ms transport delay (the 6-20 Hz / 4-15 Hz cross-correlation peaks were 2 / 6 ms)
      ms_free     the p5b fit with J FREE per band (J 0.27 / 0.48 / 2.1 / 1.7 / 0.48: J unidentified above 10 m/s)
      light_b     the PRIOR world (BELIEF): fork tunes @54ff1ea39, J 8e-5 u, b 6e-4 u, hold-map k, Coulomb 0.012 u
    Two-mass stress variants are made with member.with_mode20(f2, zeta2, r2) (not identified here; see the report)."""
    pc = path or os.path.join(HERE, "_scratch", "p5c.json")
    pb = os.path.join(HERE, "_scratch", "p5b_ms.json")
    fam = {}
    n = len(V_CENTRES)
    if os.path.exists(pc):
        rows = _profile_rows(pc)
        J0 = min(rows, key=lambda J: abs(J - 0.2))
        b0, k0, F0, Fs0 = rows[J0]
        fam["nominal"] = PlantFamilyMember("nominal", J=np.full(n, J0), b=b0, k=k0, Fc=F0, Fs=Fs0, tau_ms=2,
                                           note="MS output-error fit, J %.2f (p5c profile row)" % J0)
        for nm, Jt in (("J_lo", 0.1), ("J_hi", 0.5), ("J_hi2", 0.8)):
            Jc = min(rows, key=lambda J: abs(J - Jt))
            bb, kk, FF, FFs = rows[Jc]
            fam[nm] = PlantFamilyMember(nm, J=np.full(n, Jc), b=bb, k=kk, Fc=FF, Fs=FFs, tau_ms=2,
                                        note="MS fit refitted at J %.2f (p5c)" % Jc)
    else:
        B = _FALLBACK
        fam["nominal"] = PlantFamilyMember("nominal", *(np.array(B[k], float) for k in ("J", "b", "k", "Fc", "Fs")),
                                           tau_ms=B["tau_ms"], note="FALLBACK constants (p5c.json absent)")
    nom = fam["nominal"]
    hi_speed = V_CENTRES >= 10.0
    fam["b_lo"] = replace(nom, name="b_lo", b=nom.b / np.where(hi_speed, 1.8, 1 / 0.7), note="nominal b /1.8 (>=10 m/s), x0.7 below")
    fam["b_hi"] = replace(nom, name="b_hi", b=nom.b * 1.5, note="nominal b x1.5")
    fam["F_hi"] = replace(nom, name="F_hi", Fc=nom.Fc * 2, Fs=nom.Fs * 2, note="nominal friction x2 (G3a bias at speed)")
    fam["F_lo"] = replace(nom, name="F_lo", Fc=nom.Fc * 0.5, Fs=nom.Fs * 0.5, note="nominal friction x0.5")
    fam["tau0"] = replace(nom, name="tau0", tau_ms=0, note="nominal, transport delay 0 ms")
    fam["tau6"] = replace(nom, name="tau6", tau_ms=6, note="nominal, transport delay 6 ms")
    if os.path.exists(pb):
        src = json.load(open(pb))["nominal"]
        arr = lambda key: np.array([src[bn][key]["val"] for bn in BAND_NAMES], float)  # noqa: E731
        fam["ms_free"] = PlantFamilyMember("ms_free", J=arr("J"), b=arr("b"), k=arr("k"), Fc=arr("Fc"), Fs=arr("Fs"),
                                           tau_ms=2, note="p5b MS fit, J free per band (unidentified above 10 m/s)")
    fam["light_b"] = _prior_light_b()
    return fam


# ======================================================================================================================
# the V294 lane, byte-exact, vectorised over a batch (int64 numpy; >> floors like the V850's sar)
# ======================================================================================================================
def v294_cells():
    import r71b_cache as RC
    return RC.v294_cells()


class Lane294:
    """byte-exact integer mirror of the V294 LKAS lane (fb lag -> error former -> P -> taper/fade -> sum clamp ->
    output lag -> forward gain -> output clamp), Ki = Kd = 0, for a BATCH of independent lanes.  Overrides let a design
    agent move the fb pole/gain/clamp, the flat Kp and the error shift without touching the rest.  The self-test checks
    it tick for tick against the golden model's lkas_fb_lag + lkas_rate_pid_tick."""

    def __init__(self, cells, n, fb_a=None, fb_b=None, fb_clamp=None, kp=None, e_shift=None):
        c = cells
        self.LERP = np.array([int(np.interp(i, c["map_X"], c["map_Y"])) for i in range(241)], np.int64)
        self.kp = int(c["kp_Y"][0]) if kp is None else int(kp)
        self.sh = int(c["e_shift"]) if e_shift is None else int(e_shift)
        self.fa = int(c["fb_a"]) if fb_a is None else int(fb_a)
        self.fb = int(c["fb_b"]) if fb_b is None else int(fb_b)
        self.fcl = int(c["fb_clamp"]) if fb_clamp is None else int(fb_clamp)
        self.pcl, self.scl, self.tcl = int(c["p_clamp"]), int(c["sum_clamp"]), int(c["t_clamp"])
        self.la, self.lb, self.gain = int(c["lag_a"]), int(c["lag_b"]), int(c["gain"])
        assert c["fb_op"] == "diff" and int(c["ki"]) == 0 and all(int(y) == 0 for y in c["kd_Y"])
        self.s = np.zeros(n, np.int64)
        self.o = np.zeros(n, np.int64)

    def init_state(self, x0, T0):
        """fixed point of the fb lag at constant x0; output-lag state that delivers ~T0."""
        x0 = np.asarray(x0, np.int64)
        self.s = (self.fb * x0) // max(1024 - self.fa, 1)
        self.o = (np.asarray(T0, float) * 32768.0 / self.gain * 16.0).astype(np.int64)

    def tick(self, x, sp, m):
        """x: int64 batch of wheel-rate counts; sp: signed setpoint (map output); m: taper/fade factor (254 at rest)."""
        s_new = ((self.fa * self.s) >> 10) + ((self.fb * x) >> 10)
        r26 = np.clip(s_new - self.s, -self.fcl, self.fcl)
        self.s = s_new
        P = np.clip((((sp << self.sh) - r26) * self.kp) >> 8, -self.pcl, self.pcl)
        S = np.clip((m * P) >> 8, -self.scl, self.scl)
        o2 = ((self.la * self.o) >> 10) + ((S * self.lb) >> 10)
        y = (self.o + o2) >> 5
        self.o = o2
        return np.clip((y * self.gain) >> 15, -self.tcl, self.tcl), r26


# ======================================================================================================================
# the plant, 1 kHz, batch
# ======================================================================================================================
def _plant_arrays(member, v1k):
    a = member.arrays_at(v1k)
    return a


def simulate(member, n_ticks, v, th0, om0, T_open=None, lane=None, sp=None, m=None, c0=None, d=None, x_noise=None,
             seed=0, record_every=1, x_sign=-1):
    """1 kHz simulation of a batch of B plants.

    member   PlantFamilyMember (speed-scheduled); constant_member(PlantParams) for a fixed plant
    v        (B, n_frames) speed at 100 Hz (ZOH to 1 kHz) -- schedules J/b/k/F
    th0, om0 (B,) initial angle (deg) and rate (deg/s)
    OPEN LOOP:   T_open (B, n_ticks) delivered torque in T counts (tap sign, + = right)
    CLOSED LOOP: lane (Lane294), sp (B, n_frames) signed setpoint (sgn * LERP(map, idx), the attribution march's sign
                 convention), m (B, n_frames) fade factor -> T from the lane at every tick, fed back through x.
                 x_sign = -1: the lane is fed -x (= +wire, the raw 0x18F field), exactly as the calibrated march
                 (r71b_attribution.march, sign-controlled on the drive) -- its output T is then in the TAP's sign.
    c0 (B,) constant torque offset (T counts, + = LEFT; crown / bank / sensor offset), d (B, n_ticks) disturbance
    x_noise  rms counts of white noise added to x before the lane (the rate sensor's noise floor)
    Returns dict of (B, n_ticks // record_every) arrays: th, om (deg, deg/s, + LEFT), x (counts, = +8*om), T (tap sign),
    r26 (the lane's operand).
    """
    B = len(th0)
    nf = v.shape[1]
    tau = int(member.tau_ms)
    w = max(int(member.rate_win_ms), 1)
    th = np.asarray(th0, float).copy()
    om = np.asarray(om0, float).copy()
    two = member.f2 > 0
    thw = th.copy()
    omw = om.copy()
    # ring: hist[:, hp] = the angle w ticks ago (rate former); back-filled along om0 so x starts at 8*om0, not 0
    hist = th[:, None] - om[:, None] * (w - np.arange(w))[None, :] * 1e-3
    hp = 0
    Tbuf = np.zeros((B, tau + 1))
    tp = 0
    rec = n_ticks // record_every
    out = {k: np.zeros((B, rec)) for k in ("th", "om", "x", "T", "r26")}
    rng = np.random.default_rng(seed)
    c0 = np.zeros(B) if c0 is None else np.asarray(c0, float)
    dt = 1e-3
    fr_prev = -1
    zB = np.zeros(B)
    for n in range(n_ticks):
        fr = min(n // 10, nf - 1)
        if fr != fr_prev:
            a = member.arrays_at(v[:, fr])
            J, bb, kk, Fc, Fs, sat = a["J"], a["b"], a["k"], a["Fc"], a["Fs"], a["sat"]
            ksat = kk * sat
            if two:
                Jw = J * member.r2
                Jm = J - Jw
                mu = Jm * Jw / J
                Ktb = (2 * np.pi * member.f2) ** 2 * mu
                ctb = 2 * member.zeta2 * np.sqrt(Ktb * mu)
            else:
                Jm = J
            if lane is not None and T_open is None:
                sp_f = sp[:, fr].astype(np.int64)
                m_f = m[:, fr].astype(np.int64)
            fr_prev = fr
        # --- sensor: rate former on the motor-side angle, window w ms
        xr = 8.0 * (th - hist[:, hp]) / (w * dt)
        if x_noise:
            xr = xr + rng.normal(0.0, x_noise, B)
        x = np.clip(np.round(xr), -12000, 12000).astype(np.int64)
        # --- controller
        if T_open is not None:
            T = T_open[:, n]
            r26 = zB
        else:
            T, r26 = lane.tick(x_sign * x, sp_f, m_f)
            T = T.astype(float)
        Tbuf[:, tp] = T
        tp = (tp + 1) % (tau + 1)
        u = -Tbuf[:, tp] + c0                       # the torque written tau ticks ago
        if d is not None:
            u = u + d[:, n]
        # --- plant (motor side), semi-implicit Euler with Karnopp stick-slip
        fnet = u - ksat * np.tanh(th / sat) - bb * om
        if two:
            fnet = fnet - Ktb * (th - thw) - ctb * (om - omw)
        stuck = (om == 0.0) & (np.abs(fnet) <= Fs)
        fdir = np.where(om != 0.0, np.sign(om), np.sign(fnet))
        om_new = om + np.where(stuck, 0.0, (fnet - Fc * fdir) / Jm) * dt
        om_new[stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om)))] = 0.0
        if two:
            omw = omw + (Ktb * (th - thw) + ctb * (om - omw)) / Jw * dt
            thw = thw + omw * dt
        # ring: store the angle BEFORE this tick's update as the oldest-next sample
        hist[:, hp] = th
        hp = (hp + 1) % w
        om = om_new
        th = th + om * dt
        if n % record_every == 0:
            j = n // record_every
            if j < rec:
                out["th"][:, j] = thw if two else th
                out["om"][:, j] = om
                out["x"][:, j] = x
                out["T"][:, j] = T
                out["r26"][:, j] = r26
    return out


def constant_member(p: PlantParams, name="const"):
    n = len(V_CENTRES)
    return PlantFamilyMember(name, J=np.full(n, p.J), b=np.full(n, p.b), k=np.full(n, p.k), Fc=np.full(n, p.Fc),
                             Fs=np.full(n, p.Fs), tau_ms=p.tau_ms, rate_win_ms=p.rate_win_ms, use_sat=(p.sat < 1e8),
                             f2=p.f2, zeta2=p.zeta2, r2=p.r2)


def linear_frf(p: PlantParams, f):
    """om/u (deg/s per T count) of the LINEARISED plant (friction off) incl. the transport delay: s e^{-s tau}/(J s^2+b s+k),
    with the optional collocated two-mass mode.  For loop design at small signal while SLIDING; stuck = zero motion."""
    s = 2j * np.pi * np.asarray(f, float)
    if p.f2 > 0:
        Jw = p.J * p.r2
        Jm = p.J - Jw
        mu = Jm * Jw / p.J
        K = (2 * np.pi * p.f2) ** 2 * mu
        c = 2 * p.zeta2 * np.sqrt(K * mu)
        Zw = (c * s + K) * Jw * s * s / (Jw * s * s + c * s + K)          # wheel side reflected to the motor side
        G = s / (Jm * s * s + p.b * s + p.k + Zw)
    else:
        G = s / (p.J * s * s + p.b * s + p.k)
    return G * np.exp(-s * p.tau_ms * 1e-3)


# ======================================================================================================================
# exact LINEAR closed inner loop at 1 kHz (friction off, integer floors off): the wheel mode with and without the lane
# ======================================================================================================================
def linear_poles(p: PlantParams, cells=None, lane_kw=None, m=254, lane_on=True):
    """eigenvalues of the 1 kHz linear map z[n+1] = A z[n] of plant (the simulator's semi-implicit Euler, rigid or two-mass)
    + rate former (w ticks) + the V294 lane linearised (fb lag, P, taper m/256, output lag, forward gain) + tau ticks of
    transport delay, at sp = 0.  Returns (poles_z, modes) with modes = list of (f Hz, zeta) of the complex pairs, and the
    real poles as (0, 1) entries, sorted by frequency.  lane_on=False gives the OPEN plant (T = 0)."""
    c = cells if cells is not None else v294_cells()
    kw = lane_kw or {}
    pa = (kw.get("fb_a", c["fb_a"])) / 1024.0
    ga = (kw.get("fb_b", c["fb_b"])) / 1024.0
    kp = kw.get("kp", c["kp_Y"][0])
    esh_unused = kw.get("e_shift", c["e_shift"])  # noqa: F841  (sp = 0: the error shift does not act on the trim)
    pl, gl = c["lag_a"] / 1024.0, c["lag_b"] / 1024.0
    G = c["gain"] / 32768.0
    w = max(int(p.rate_win_ms), 1)
    tau = int(p.tau_ms)
    dt = 1e-3
    two = p.f2 > 0
    if two:
        Jw = p.J * p.r2
        Jm = p.J - Jw
        mu = Jm * Jw / p.J
        K = (2 * np.pi * p.f2) ** 2 * mu
        cc = 2 * p.zeta2 * np.sqrt(K * mu)
    else:
        Jm = p.J
    # state: th, om, [thw, omw], hist th_{n-1..n-w}, s, o, Tq_{n-1..n-tau}
    nh = w
    idx = {"th": 0, "om": 1}
    k0 = 2
    if two:
        idx["thw"], idx["omw"] = 2, 3
        k0 = 4
    idx["h"] = k0
    idx["s"] = k0 + nh
    idx["o"] = k0 + nh + 1
    idx["T"] = k0 + nh + 2
    N = idx["T"] + tau

    def step(z):
        th, om = z[0], z[1]
        hist = z[idx["h"]:idx["h"] + nh]            # hist[0] = th_{n-1}, ..., hist[w-1] = th_{n-w}
        th_old = hist[w - 1]
        x = 8.0 * (th - th_old) / (w * dt)
        s, o = z[idx["s"]], z[idx["o"]]
        if lane_on:
            xl = -x
            s_new = pa * s + ga * xl
            r26 = s_new - s
            P_ = -(kp / 256.0) * r26
            S = (m / 256.0) * P_
            o_new = pl * o + gl * S
            T = G * (o + o_new) / 32.0
        else:
            s_new, o_new, T = s, o, 0.0
        Tq = z[idx["T"]:idx["T"] + tau]
        T_app = Tq[tau - 1] if tau > 0 else T
        u = -T_app
        fnet = u - p.b * om - p.k * th
        if two:
            thw, omw = z[idx["thw"]], z[idx["omw"]]
            fnet = fnet - K * (th - thw) - cc * (om - omw)
            omw_new = omw + dt * (K * (th - thw) + cc * (om - omw)) / Jw
            thw_new = thw + dt * omw_new
        om_new = om + dt * fnet / Jm
        th_new = th + dt * om_new
        zn = np.zeros(N)
        zn[0], zn[1] = th_new, om_new
        if two:
            zn[idx["thw"]], zn[idx["omw"]] = thw_new, omw_new
        zn[idx["h"]] = th
        zn[idx["h"] + 1:idx["h"] + nh] = hist[:nh - 1]
        zn[idx["s"]], zn[idx["o"]] = s_new, o_new
        if tau > 0:
            zn[idx["T"]] = T
            zn[idx["T"] + 1:idx["T"] + tau] = Tq[:tau - 1]
        return zn

    A = np.column_stack([step(e) for e in np.eye(N)])
    ev = np.linalg.eigvals(A)
    modes = []
    for zp in ev:
        if abs(zp) < 1e-9:
            continue
        s_ = np.log(zp) / dt
        f = abs(s_.imag) / (2 * np.pi)
        zeta = -s_.real / abs(s_) if abs(s_) > 0 else 1.0
        if s_.imag >= 0:
            modes.append((float(f), float(zeta), complex(zp)))
    modes.sort(key=lambda t: t[0])
    return ev, modes


def wheel_mode(p: PlantParams, cells=None, lane_kw=None, lane_on=True):
    """the least-damped oscillatory pair below 8 Hz (the wheel mode): (f Hz, zeta); (nan, nan) if none."""
    _, modes = linear_poles(p, cells, lane_kw, lane_on=lane_on)
    osc = [(f, z) for f, z, _ in modes if 0.05 < f < 8.0]
    if not osc:
        return float("nan"), float("nan")
    return min(osc, key=lambda t: t[1])


# ======================================================================================================================
# self-test
# ======================================================================================================================
def _selftest():
    ok = True
    c = v294_cells()
    # 1. the batch lane == the golden model, tick for tick, on random x / command sequences
    import eps_lkas_chain_model as M
    base = M.Calibration()
    cal = replace(base, fb_clamp=int(c["fb_clamp"]), fb_lag_a=int(c["fb_a"]), fb_lag_b=int(c["fb_b"]),
                  kp_x=tuple(int(x) for x in c["kp_X"]), kp_y=tuple(int(y) for y in c["kp_Y"]),
                  kd_x=tuple(int(x) for x in c["kd_X"]), kd_y=tuple(int(y) for y in c["kd_Y"]),
                  pid_d_clamp=int(c["d_clamp"]), pid_p_clamp=int(c["p_clamp"]), sum_clamp=int(c["sum_clamp"]),
                  out_clamp=int(c["t_clamp"]), out_lag_a=int(c["lag_a"]), out_lag_b=int(c["lag_b"]),
                  lkas_forward_gain=int(c["gain"]), pid_ki=int(c["ki"]),
                  assist_map_x=tuple(int(x) for x in c["map_X"]), assist_map_y=tuple(int(y) for y in c["map_Y"]),
                  e_shift=int(c["e_shift"]), fb_op=c["fb_op"])
    rng = np.random.default_rng(3)
    B, N = 4, 3000
    lane = Lane294(c, B)
    sts = [M.EpsState() for _ in range(B)]
    idx = rng.integers(0, 241, (B, N // 10))
    sgn = rng.choice([-1, 1], (B, N // 10))
    x = np.cumsum(rng.integers(-40, 41, (B, N)), axis=1).clip(-12000, 12000)
    mism = 0
    for n in range(N):
        fr = n // 10
        sp = sgn[:, fr] * lane.LERP[idx[:, fr]]
        T, _ = lane.tick(x[:, n].astype(np.int64), sp.astype(np.int64), np.full(B, 254, np.int64))
        for bi in range(B):
            fb = M.lkas_fb_lag(int(x[bi, n]), sts[bi], cal)
            r = M.lkas_rate_pid_tick(int(sp[bi]), fb, int(idx[bi, fr]), sts[bi], cal, pol=1, taper=254)
            mism += int(r["T"] != T[bi])
    print("  Lane294 vs golden lkas_fb_lag + lkas_rate_pid_tick: %d mismatching ticks of %d  %s" % (
        mism, B * N, "PASS" if mism == 0 else "FAIL"))
    ok &= mism == 0
    # 2. plant sanity: a linear rigid plant, open loop step -> static angle u/k and the mode frequency
    p = PlantParams(J=0.2, b=0.2, k=20.0, Fc=0.0, Fs=0.0, tau_ms=0, rate_win_ms=1)
    mem = constant_member(p)
    n = 20000
    out = simulate(mem, n, np.full((1, n // 10), 10.0), np.zeros(1), np.zeros(1), T_open=np.full((1, n), -100.0))
    th_end = out["th"][0, -1]
    om = out["om"][0]
    seg = om[5:4000]
    nz = np.flatnonzero(seg != 0.0)                     # the Karnopp crossing parks om at exactly 0 for one tick
    zc = nz[np.flatnonzero(np.diff(np.sign(seg[nz])) != 0)]
    fd = 1000.0 / (2 * np.mean(np.diff(zc))) if len(zc) > 2 else np.nan
    fth = math.sqrt(20 / 0.2) / (2 * math.pi) * math.sqrt(1 - (0.2 / (2 * math.sqrt(20 * 0.2))) ** 2)
    print("  linear step: th_end %.3f deg (want 5.000); damped frequency %.3f Hz (want %.3f)  %s" % (
        th_end, fd, fth, "PASS" if abs(th_end - 5) < 0.05 and abs(fd - fth) < 0.05 else "FAIL"))
    ok &= abs(fd - fth) < 0.05
    # 3. friction: a torque below Fs never moves a stuck plant; above it, it does
    p = PlantParams(J=0.2, b=2.0, k=20.0, Fc=30.0, Fs=40.0, tau_ms=0, rate_win_ms=1)
    mem = constant_member(p)
    out = simulate(mem, 2000, np.full((2, 200), 10.0), np.zeros(2), np.zeros(2),
                   T_open=np.vstack([np.full(2000, -39.0), np.full(2000, -41.0)]))
    moved = np.max(np.abs(out["th"]), axis=1)
    print("  friction: |u| 39 < Fs 40 -> max |th| %.4f (want 0) ; |u| 41 -> %.4f (want > 0)  %s" % (
        moved[0], moved[1], "PASS" if moved[0] == 0 and moved[1] > 0 else "FAIL"))
    ok &= moved[0] == 0 and moved[1] > 0
    # 4. the rate former reads the true rate on a constant-rate ramp (w = 3): x == 8 * om exactly
    p = PlantParams(J=0.2, b=0.0, k=0.0, Fc=0.0, Fs=0.0, tau_ms=0, rate_win_ms=3)
    out = simulate(constant_member(p), 50, np.full((1, 5), 10.0), np.zeros(1), np.full(1, 10.0), T_open=np.zeros((1, 50)))
    xr = out["x"][0, 10:]
    x0 = out["x"][0, :3]
    print("  rate former at a constant 10 deg/s: x = %s (want 80), first ticks %s (want 80: history back-filled)  %s" % (
        np.unique(xr), x0, "PASS" if np.all(xr == 80) and np.all(x0 == 80) else "FAIL"))
    ok &= bool(np.all(xr == 80)) and bool(np.all(x0 == 80))
    fam = family()
    for nm, mbr in fam.items():
        print("  %-10s J %s b %s k %s Fc %s Fs %s tau %d  %s" % (nm, np.round(mbr.J, 3), np.round(mbr.b, 2), np.round(mbr.k, 1),
                                                                np.round(mbr.Fc, 1), np.round(mbr.Fs, 1), mbr.tau_ms, mbr.note[:60]))
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
