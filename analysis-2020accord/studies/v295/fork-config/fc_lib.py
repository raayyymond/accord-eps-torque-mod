# -*- coding: utf-8 -*-
"""fc_lib -- the fork-config design library on top of the shared V295 harness (v295_harness.py, NOT edited).

What it adds:
  * Fork: one fork toggle set (Kp, Ki, KiHigh, LAF, friction, KeepLearnedLatAccelOffset, lat-delay offset).
  * VecPort: the harness's proven r1 port (ForkPort, gate H3b: == the real LatControlTorque @20d24ab79) with the
    parameters PER LANE, plus the fork's own Accord Ki schedule (get_honda_accord_torque_ki: ki_low below 8 m/s,
    ki_high from 18, linear between, ki_high <= 0 = flat).  get_friction's np.interp is evaluated per unique
    (friction x LAF) group, so an r1 row is bit-identical to the harness port (checked in f1_control.py).
  * sim(): H.simulate with a per-row fork (monkeypatched constructor; the harness module is untouched on disk).
  * metrics(): H.drive_metrics + straight-line (|plan| < 0.4) wheel-rate bands 0.3-1 / 1-3 / 1-5 Hz.
  * outer(): outer-loop margins (H.outer_frf with the candidate's toggles, Ki at the speed), incl. the relay
    small-signal slope, and a describing-function sweep of the relay gain k in [0, 2 x slope].
  * hunt(): a synthetic straight road (zero planner demand, constant crown torque, Karnopp plant, sensor noise,
    real fork port, byte-exact lane, Honda limiter, 22 ms pipe) at constant speed -> late-window oscillation.
ANALYSIS ONLY.  Sends nothing, flashes nothing, deploys nothing, edits no fork or firmware file.
"""
import os
import sys
import time
from dataclasses import dataclass, replace, asdict

import numpy as np
from scipy import signal

HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
if HARN not in sys.path:
    sys.path.insert(0, HARN)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v295_harness as H  # noqa: E402

V295_IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR."
            "SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V295_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"

KI_BP = (8.0, 18.0)          # HONDA_ACCORD_KI_SCHEDULE_V_BP @20d24ab79 (latcontrol_vehicle_tunes.py), asserted in VecPort


def cells_v295(name="V295"):
    c = H.Cells.from_image(V295_IMG, name, V295_SHA)
    assert not c.diff(H.Cells.v294().replace(fb_b=1050)), "V295 image cells != V294 + b 1050"
    return c


@dataclass(frozen=True)
class Fork:
    name: str = "r1"
    kp: float = 0.9              # SteerKP
    ki: float = 0.3              # AccordTorqueKi
    ki_high: float = 0.0         # AccordTorqueKiHigh (0 = flat)
    laf: float = 14.0            # SteerLatAccel
    fric: float = 0.011          # SteerFriction
    keep_off: bool = True        # KeepLearnedLatAccelOffset
    delay_add: float = 0.0       # lat_delay offset, s (sensitivity only; not a toggle)
    i_warm: str = "logged"       # warm start of the integrator: "logged" (r1's value) or "scaled" (x LAF/14: same torque)

    def ki_at(self, v):
        v = np.asarray(v, float)
        if self.ki_high <= 0:
            return np.full(v.shape, float(self.ki))
        return np.interp(v, KI_BP, [float(self.ki), float(self.ki_high)])

    def toggles(self, v):
        """the toggle dict H.outer_frf reads, with Ki at speed v."""
        return {"steerKp": [[0], [float(self.kp)]], "accord_torque_ki": float(self.ki_at(v)),
                "latAccelFactor": float(self.laf), "friction": float(self.fric)}

    def short(self):
        s = "Kp%.2f Ki%.2f" % (self.kp, self.ki)
        if self.ki_high > 0:
            s += "/%.2f" % self.ki_high
        s += " LAF%.1f F%.4f" % (self.laf, self.fric)
        if not self.keep_off:
            s += " off0"
        if self.delay_add:
            s += " dly%+.2f" % self.delay_add
        return s


R1 = Fork("r1")
_OrigPort = H.ForkPort


class VecPort(_OrigPort):
    """the harness port with per-row parameters.  rows: list of Fork, len B."""

    def __init__(self, B, toggles, rows):
        self._i = np.zeros(B)
        self._i_scale = np.ones(B)
        super().__init__(B, toggles)
        from openpilot.selfdrive.controls.lib import latcontrol_vehicle_tunes as VT
        assert tuple(VT.HONDA_ACCORD_KI_SCHEDULE_V_BP) == KI_BP, VT.HONDA_ACCORD_KI_SCHEDULE_V_BP
        # the fork's own schedule function must equal Fork.ki_at (checked on a grid)
        for lo, hi in ((0.3, 0.0), (0.3, 1.5), (0.45, 2.5)):
            f = Fork(ki=lo, ki_high=hi)
            for vv in (0.0, 5.0, 8.0, 12.3, 18.0, 30.0):
                assert VT.get_honda_accord_torque_ki(vv, lo, hi) == float(f.ki_at(vv)), (lo, hi, vv)
        assert len(rows) == B
        self.rows_cfg = rows
        self.kp = np.array([float(r.kp) for r in rows])
        self.ki_lo = np.array([float(r.ki) for r in rows])
        self.ki_hi = np.array([float(r.ki_high) for r in rows])
        self.laf = np.array([float(np.float32(r.laf)) for r in rows])
        self.fric = np.array([float(np.float32(r.fric)) for r in rows])
        self.keep = np.array([1.0 if r.keep_off else 0.0 for r in rows])
        self.delay_add = np.array([float(r.delay_add) for r in rows])
        self._i_scale = np.array([(float(np.float32(r.laf)) / float(np.float32(14.0))) if r.i_warm == "scaled" else 1.0
                                  for r in rows])
        fl = self.fric * self.laf
        self._fl_groups = [(val, np.flatnonzero(fl == val)) for val in np.unique(fl)]
        self.reset()

    # the integrator: simulate() writes fork.i = logged r1 value after the warm-up -> scaled here if asked
    @property
    def i(self):
        return self._i

    @i.setter
    def i(self, val):
        self._i = np.asarray(val, float) * self._i_scale

    def ki_now(self, v):
        sched = self.ki_hi > 0
        out = self.ki_lo.copy()
        if sched.any():
            out[sched] = np.array([float(np.interp(vv, KI_BP, [lo, hi])) for vv, lo, hi in
                                   zip(v[sched], self.ki_lo[sched], self.ki_hi[sched])])
        return out

    def step(self, active, v, angle, pressed, ang_off, roll, des_curv, lat_delay, laf_off, steer_limited):
        """== ForkPort.step (h3b-proven), line for line, with per-row Kp / Ki(v) / LAF / friction / offset / delay."""
        B = self.B
        dt = self.dt
        LT = self.LT
        active = np.asarray(active, bool) * np.ones(B, bool)
        v = np.asarray(v, float) * np.ones(B)
        lat_delay = np.asarray(lat_delay, float) * np.ones(B) + self.delay_add
        meas = self.curvature(np.asarray(angle, float) - ang_off, v, roll) * v ** 2
        fut = des_curv * v ** 2
        laf_off = np.asarray(laf_off, np.float32).astype(float) * np.ones(B) * self.keep
        rel = self.prev_pressed & ~np.asarray(pressed, bool)
        self._i = np.where(active & rel, self._i * 0.8, self._i)
        fade = np.interp(v, LT.FF_ROLL_OFFSET_FADE_BP, LT.FF_ROLL_OFFSET_FADE_V)
        roll_comp = roll * self.g_op * fade
        delay_frames = np.clip(lat_delay / dt, 1, self.buf_len).astype(int) * np.ones(B, int)
        expected = self.buf[np.arange(B), (self.head - delay_frames) % self.buf_len] * v ** 2
        self.buf[:, self.head] = des_curv
        self.head = (self.head + 1) % self.buf_len
        raw_jerk = np.clip((fut - expected) / np.maximum(lat_delay, dt), -LT.MAX_LAT_JERK_UP, LT.MAX_LAT_JERK_UP)
        jx = (1. - self.a_jerk) * self.jx + self.a_jerk * raw_jerk
        jerk = np.clip(jx, -LT.MAX_LAT_JERK_UP, LT.MAX_LAT_JERK_UP)
        grav = fut - roll_comp
        setpoint = expected + jerk * lat_delay
        des_rate = (setpoint - self.prev_des) / dt
        unwind = (des_rate < LT.UNWIND_D_DES_THRESHOLD) & (np.abs(setpoint) < LT.UNWIND_LAT_ACCEL_NEAR_ZERO)
        mx = (1. - self.a_mrate) * self.mx + self.a_mrate * ((meas - self.prev_meas) / dt)
        lsf = (np.interp(v, LT.LOW_SPEED_X, LT.LOW_SPEED_Y) / np.maximum(v, self.MIN_SPEED)) ** 2
        error = setpoint - meas
        err_lsf = error * (1 + lsf / np.maximum(self.kp, 1e-3))
        ff = grav
        ff = ff - laf_off * fade
        thr = self.thr
        sdz = np.interp(np.maximum(v, 0.0), LT.CENTER_CHATTER_JERK_DEADZONE_SPEED_BP, LT.CENTER_CHATTER_JERK_DEADZONE_SPEED_V)
        cw = np.interp(np.abs(setpoint), LT.CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_BP, LT.CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_V)
        fjdz = np.maximum(0.0, sdz * cw)
        fj = np.copysign(np.maximum(np.abs(jerk) - fjdz, 0.0), jerk)
        xf = err_lsf + LT.JERK_GAIN * fj
        fr = np.zeros(B)
        for fl, rows in self._fl_groups:                     # get_friction, exactly np.interp per friction*LAF value
            fr[rows] = np.interp(xf[rows], [-thr, thr], [-fl, fl])
        ff = ff + 1.0 * fr
        lowv = v < self.low_speed_reset
        i0 = np.where(lowv, 0.0, self._i)
        freeze = np.asarray(steer_limited, bool) | np.asarray(pressed, bool) | lowv | unwind
        e32 = err_lsf.astype(np.float32).astype(float)
        p = self.kp * e32
        pos, neg = 1.0 * self.laf, -1.0 * self.laf
        i_new = i0 + self.ki_now(v) * (1.0 / (1 / dt)) * e32
        test = p + i_new + 0.0 + ff
        ub = np.where(test > pos, i0, pos)
        lb = np.where(test < neg, i0, neg)
        i_upd = np.where(freeze, i0, np.clip(i_new, lb, ub))
        ctrl = np.clip(p + i_upd + 0.0 + ff, neg, pos)
        otq = ctrl / self.laf
        self._i = np.where(active, i_upd, 0.0)
        self.jx = np.where(active, jx, 0.0)
        self.mx = np.where(active, mx, 0.0)
        self.prev_meas = meas
        self.prev_des = np.where(active, setpoint, fut)
        self.p = np.where(active, p, 0.0)
        self.f = np.where(active, ff, 0.0)
        out = np.where(active, otq, 0.0)
        self.prev_pressed = np.asarray(pressed, bool) * np.ones(B, bool)
        return dict(torque=-out, p=self.p, i=self._i, f=self.f, output=-out, la_des=np.where(active, setpoint, 0.0),
                    la_act=meas, jerk=np.where(active, jerk, 0.0), error=np.where(active, err_lsf, 0.0),
                    fr=np.where(active, fr, 0.0))


def sim(pairs, members, chunks=None, dist="lp", null_shadow=False, record_1k=False, seed=0):
    """pairs: list of (Cells, Fork) -- one 'config'.  members: list of plant member names.  Returns (R, index) where
    index[(config_name, member)] = rows.  Config name = Fork.name (must be distinct)."""
    fam = H.family()
    chunks = chunks or H.route_chunks()
    names = [f.name for _, f in pairs]
    assert len(set(names)) == len(names), names
    cl = [c.replace(name="c_" + f.name) for c, f in pairs]
    mem = [fam[m] for m in members]
    nM, nK = len(mem), len(chunks)
    rows_cfg = [pairs[ci][1] for ci in range(len(pairs)) for _ in range(nM) for _ in range(nK)]
    H.ForkPort = lambda B, tg: VecPort(B, tg, rows_cfg)  # noqa: E731
    try:
        R = H.simulate(cl, mem, chunks, H.SimOpts(mode="B", dist=dist, null_shadow=null_shadow, seed=seed),
                       record_1k=record_1k)
    finally:
        H.ForkPort = _OrigPort
    index = {}
    for ci, (_, f) in enumerate(pairs):
        for mi, m in enumerate(members):
            index[(f.name, m)] = [ci * nM * nK + mi * nK + k for k in range(nK)]
    return R, index


BANDS_X = tuple(H.BANDS) + (("8-22", 8.0, 22.0),)     # + the pooled 8-22 m/s band the win condition is written on


def _bp(x, lo, hi):
    return H._bp(x, lo, hi)


def metrics(R, rows, skip_s=0.0):
    """H.drive_metrics on the rows, plus straight-line wheel-rate bands.  skip_s drops the first seconds of each chunk
    (the warm-start sensitivity)."""
    S = H.drive_series_sim(R, rows)
    if skip_s > 0:
        k = int(skip_s * 100)
        S = {kk: [a[k:] for a in vv] for kk, vv in S.items()}
    out = H.drive_metrics(S, band_list=BANDS_X)
    for nm, lo, hi in BANDS_X:
        if nm not in out:
            continue
        acc = {"s03": [], "s13": [], "s15": [], "fr": [], "cmd": []}
        for j in range(len(S["v"])):
            v = S["v"][j]
            mk = (v >= lo) & (v < hi)
            if mk.sum() < 100:
                continue
            cut = np.zeros(len(v), bool)
            cut[100:-100] = True
            st = mk & cut & (np.abs(S["la_plan"][j]) < 0.4)
            r = S["rate"][j]
            acc["s03"].append(_bp(r, 0.3, 1.0)[st])
            acc["s13"].append(_bp(r, 1.0, 3.0)[st])
            acc["s15"].append(_bp(r, 1.0, 5.0)[st])
            acc["cmd"].append(np.abs(S["cmd"][j][mk]))
        for key in ("s03", "s13", "s15"):
            a = np.concatenate(acc[key]) if acc[key] else np.zeros(0)
            out[nm][key] = float(np.sqrt(np.mean(a ** 2))) if len(a) > 300 else float("nan")
        c = np.concatenate(acc["cmd"]) if acc["cmd"] else np.zeros(0)
        out[nm]["sat4096"] = float(np.mean(c >= 4096)) if len(c) else float("nan")
    out["limit_cycle"] = H.limit_cycle_peak(R, rows)
    out["diverged"] = bool(np.any(~np.isfinite(R["ang"][rows])) or np.nanmax(np.abs(R["ang"][rows])) > 720)
    return out


# ------------------------------------------------------------------------------------------------ the outer loop
FG = np.logspace(-2, np.log10(20.0), 1200)
SPEEDS = (3.1, 4.0, 5.0, 8.0, 12.0, 17.0, 22.0, 26.9)
ID_MEMBERS = ("nominal", "b_lo", "b_hi", "F_lo", "F_hi", "J_lo", "J_hi", "tau0", "tau6")


def lsf_of(v):
    return (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2


def outer(cells, fork, member, v, relay_mult=(1.0,), fam=None):
    """outer-loop margins for one (member, speed): returns {mult: margins dict}.  relay_mult scales the SteerFriction
    small-signal slope (1.0 = the linearised relay, 0 = no relay).  L = K(f) * Cf with K from H.outer_frf (relay off)."""
    fam = fam or H.family()
    p = fam[member].at(v)
    tg = fork.toggles(v)
    L0 = H.outer_frf(cells, p, v, FG, relay=False, toggles=tg)
    kp, ki, laf, fric = fork.kp, float(fork.ki_at(v)), float(np.float32(fork.laf)), float(np.float32(fork.fric))
    z100 = np.exp(2j * np.pi * FG * 0.01)
    lsf = lsf_of(v)
    Cf0 = (kp + ki * 0.01 / (1 - 1 / z100)) * (1 + lsf / kp)
    K = L0 / Cf0
    out = {}
    for m in relay_mult:
        Cf = (kp + ki * 0.01 / (1 - 1 / z100) + m * fric * laf / 0.30) * (1 + lsf / kp)
        L = K * Cf
        mg = H.margins(FG, L)
        i02 = int(np.argmin(np.abs(FG - 0.2)))
        out[m] = dict(Ms=mg["Ms"], f_Ms=mg["f_Ms"], PM=mg["PM_min"], GM=mg["GM_min"], xover=mg["crossovers_hz"],
                      T02=float(abs(L[i02] / (1 + L[i02]))), S02=float(abs(1 / (1 + L[i02]))))
    return out


def relay_slope_torque(fork, v):
    """the SteerFriction relay's small-signal gain in TORQUE units per m/s^2 of (planner) error: F/0.30 * (1 + lsf/Kp)."""
    return float(np.float32(fork.fric)) / 0.30 * (1 + lsf_of(v) / fork.kp)


def p_gain_torque(fork, v):
    return (fork.kp + lsf_of(v)) / float(np.float32(fork.laf))


# ------------------------------------------------------------------------------------------------ synthetic straight
def hunt(pairs, members, speeds, crown=(0.0,), secs=60.0, seed=3, x_noise=1.93, pipe_ms=22, lat_delay=0.426,
         laf_off=-0.149):
    """zero planner demand on a straight road at constant speed; constant plant disturbance c0 = crown[k] * Fs(member, v)
    (T counts; a road crown / bias the plant must be held against).  Returns {(cfg, member, v, crown): dict}.
    The fork sees the quantised angle (0.1 deg), steeringPressed False, roll 0, angle offset 0, the r71b learned offset
    (-0.149 m/s^2 p50) scaled by KeepLearnedLatAccelOffset, lat_delay 0.426 s."""
    fam = H.family()
    combos = [(ci, m, v, c) for ci in range(len(pairs)) for m in members for v in speeds for c in crown]
    B = len(combos)
    rows_cfg = [pairs[ci][1] for ci, _, _, _ in combos]
    lane = H.Lane([pairs[ci][0] for ci, _, _, _ in combos])
    mem = [fam[m] for _, m, _, _ in combos]
    V = np.array([v for _, _, v, _ in combos], float)
    plant = H.PlantBatch(mem, np.zeros(B), np.zeros(B), x_noise=x_noise, seed=seed)
    plant.set_speed(V)
    plant.c0 = np.array([c for _, _, _, c in combos]) * plant.Fs
    import fork_real as FK  # noqa: F401  (ForkPort needs the extract on sys.path)
    tg = H.route()["toggles"]
    fork = VecPort(B, tg, rows_cfg)
    NF = int(secs * 100)
    ang = np.zeros((B, NF))
    rate = np.zeros((B, NF))
    cmdr = np.zeros((B, NF))
    last_tq = np.zeros(B)
    qcmd = np.zeros((B, NF + 4))
    wire_eff = np.zeros(B)
    idx, sp, mm = lane.demand(wire_eff)
    zero = np.zeros(B)
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            aw = plant.wheel_angle()
            aq = np.round(aw / 0.1) * 0.1
            ang[:, k] = aq
            r = fork.step(np.ones(B, bool), V, aq, np.zeros(B, bool), zero, zero, zero, np.full(B, lat_delay),
                          np.full(B, laf_off), np.zeros(B, bool))
            lim, can = H.honda_limiter(r["torque"], last_tq)
            last_tq = lim
            qcmd[:, k] = can
            cmdr[:, k] = can
        if (n - pipe_ms) >= 0 and (n - pipe_ms) % 10 == 0:
            wire_eff = qcmd[:, (n - pipe_ms) // 10]
            idx, sp, mm = lane.demand(wire_eff)
        x = plant.sense()
        T, _ = lane.tick(-x, sp, idx, mm)
        plant.step(T.astype(float))
        if n % 10 == 9:
            rate[:, k] = x / 8.0
    out = {}
    h = NF // 2
    for j, (ci, m, v, c) in enumerate(combos):
        a = ang[j, h:]
        rr = rate[j, h:]
        f, P = signal.welch(rr - rr.mean(), fs=100.0, nperseg=min(1024, len(rr)))
        band = (f >= 0.1) & (f <= 8.0)
        fpk = float(f[band][np.argmax(P[band])])
        out[(pairs[ci][1].name, m, v, c)] = dict(pp=float(a.max() - a.min()), mean=float(a.mean()),
                                                  rate_rms=float(np.std(rr)), f_pk=fpk,
                                                  cmd_pp=float(cmdr[j, h:].max() - cmdr[j, h:].min()),
                                                  diverged=bool(np.abs(a).max() > 360))
    return out
