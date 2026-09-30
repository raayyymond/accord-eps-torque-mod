# -*- coding: utf-8 -*-
"""a4_nl.py -- (c)/(d) MY nonlinear closed loop: MY byte-exact integer lane (IntLane, == golden model, a0) + MY plant
integrator (Karnopp stick-slip, 4 sub-steps per ms, rigid or collocated two-mass, transport delay, 3 ms rate former,
x noise, 0.1 deg angle quantisation) + MY simplified r1 fork law at 100 Hz (Kp 0.9 + low-speed factor, Ki 0.3 with the
safety-limit freeze, FF = setpoint / LAF, the SteerFriction relay on the lsf error + JERK_GAIN * jerk with the centre
jerk dead zone, Honda limiter 0.03/frame, 22 ms pipe) + the firmware demand chain (bar 0).  Scenarios:
  hold : on-centre, setpoint 0 + small planner wander, road torque noise -> hunting / limit cycles / dwell-jump
  turn : hard turn, lat accel 0 -> A in 1 s, hold 3 s, back in 1 s, twice (left, right) -> 1.6-3 Hz, overshoot, clamps
  creep: 3 m/s slow setpoint ramp (friction-dominated) -> stick-slip jump count and size
V294 and b964 on the same seeds.  Output: a4_nl_out.txt, a4_nl.json"""
import json
import os
import sys
from dataclasses import replace

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import adv_lib as A  # noqa: E402
import v294_plant as VP  # noqa: E402

out = open(os.path.join(HERE, "a4_nl_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")
    out.flush()


V294 = A.read_cells("V294")
B964 = A.with_b(V294, 964)
fam = VP.family()
nom = fam["nominal"]
MEM = {"nominal": nom, "light_b": fam["light_b"], "F_hi": fam["F_hi"], "F_lo": fam["F_lo"], "J_hi2": fam["J_hi2"],
       "b_lo": fam["b_lo"], "tau9": replace(nom, name="tau9", tau_ms=9),
       "mode20_lo": replace(nom.with_mode20(20.0, 0.02, 0.5), name="mode20_lo"),
       "lb_mode20_lo": replace(fam["light_b"].with_mode20(20.0, 0.02, 0.5), name="lb_mode20_lo")}
VM = dict(sf=-0.0006999872680281922, chi=0.0, l=2.8299999237060547)
SR, KP, KI, LAF, FRIC, THR = 16.84, 0.9, 0.3, 14.0, 0.011, 0.30


def kla(v):
    cf = (1. - VM["chi"]) / (1. - VM["sf"] * v ** 2) / VM["l"]
    return cf / SR * v ** 2 * np.pi / 180.0


def demand(lane, wire):
    """firmware demand chain at bar = 0 (G = 255, F1 = 255, F2 = 255 -> m 254).  Returns idx, sp (march convention)."""
    wire = np.asarray(wire, np.int64)
    S = np.clip(-4 * wire, -0x4000, 0x4000)
    prod = (((255 * 255) & 0xFFFF) * S) >> 16
    v = np.clip(prod >> 6, -240, 240)
    idx = np.abs(v)
    sgn = np.where(v < 0, -1, 1)
    sp = -sgn * lane.map_tab[lane.rows, idx]
    return idx, sp


class Plant:
    """batch plant, left-positive angle th (deg), om (deg/s); u = -T(t - tau) + d.  Karnopp stick-slip; 4 sub-steps."""

    def __init__(self, members, v, th0, x_noise=1.93, seed=0):
        self.m = members
        B = len(members)
        self.B = B
        self.th = np.array(th0, float)
        self.om = np.zeros(B)
        self.thw = self.th.copy()
        self.omw = np.zeros(B)
        self.two = np.array([mm.f2 > 0 for mm in members])
        self.tau = np.array([int(mm.tau_ms) for mm in members])
        self.w = 3
        self.hist = np.repeat(self.th[:, None], self.w, 1)
        self.hp = 0
        self.Tb = np.zeros((B, 32))
        self.tp = 0
        self.rng = np.random.default_rng(seed)
        self.xn = x_noise
        self.set_speed(v)

    def set_speed(self, v):
        v = np.broadcast_to(np.asarray(v, float), (self.B,))
        par = [mm.arrays_at(np.array([vv])) for mm, vv in zip(self.m, v)]
        g = lambda k: np.array([p_[k][0] for p_ in par])  # noqa: E731
        self.J, self.b, self.k, self.Fc, self.Fs, self.sat = g("J"), g("b"), g("k"), g("Fc"), g("Fs"), g("sat")
        r2 = np.array([mm.r2 for mm in self.m])
        f2 = np.array([mm.f2 for mm in self.m])
        z2 = np.array([mm.zeta2 for mm in self.m])
        self.Jw = np.where(self.two, self.J * r2, 1.0)
        self.Jm = np.where(self.two, self.J - self.Jw, self.J)
        mu = np.where(self.two, self.Jm * self.Jw / self.J, 1.0)
        self.K = np.where(self.two, (2 * np.pi * f2) ** 2 * mu, 0.0)
        self.c = np.where(self.two, 2 * z2 * np.sqrt(self.K * mu), 0.0)

    def sense(self):
        x = 8.0 * (self.th - self.hist[:, self.hp]) / (self.w * 1e-3)
        x = x + self.rng.normal(0, self.xn, self.B)
        return np.clip(np.round(x), -12000, 12000).astype(np.int64)

    def step(self, T, d):
        self.Tb[:, self.tp] = T
        u = -self.Tb[np.arange(self.B), (self.tp - self.tau) % 32] + d
        self.tp = (self.tp + 1) % 32
        self.hist[:, self.hp] = self.th
        self.hp = (self.hp + 1) % self.w
        h = 0.25e-3
        for _ in range(4):
            spring = self.k * self.sat * np.tanh(self.th / self.sat)
            fl = u - spring - self.b * self.om - self.K * (self.th - self.thw) - self.c * (self.om - self.omw)
            stuck = (self.om == 0.0) & (np.abs(fl) <= self.Fs)
            fdir = np.where(self.om != 0.0, np.sign(self.om), np.sign(fl))
            om_new = self.om + np.where(stuck, 0.0, (fl - self.Fc * fdir) / self.Jm) * h
            om_new[stuck | ((self.om != 0.0) & (np.sign(om_new) != np.sign(self.om)))] = 0.0
            omw_new = self.omw + (self.K * (self.th - self.thw) + self.c * (self.om - self.omw)) / self.Jw * h
            self.omw = np.where(self.two, omw_new, 0.0)
            self.thw = np.where(self.two, self.thw + self.omw * h, self.th)
            self.om = om_new
            self.th = self.th + self.om * h


def run(cells_list, members, v, setpoint, jerk, dist, secs, seed=0, pipe=22):
    """one batch.  setpoint/jerk: (B, n_frames) lat accel (m/s^2, left +) and its jerk; dist: (B, n_ticks) road torque."""
    B = len(cells_list)
    lane = A.IntLane(cells_list)
    NF = int(secs * 100)
    pl = Plant(members, v, np.zeros(B), seed=seed)
    I = np.zeros(B)
    last = np.zeros(B)
    lim_flag = np.zeros(B, bool)
    q = np.zeros((B, NF + 10), np.int64)
    wire = np.zeros(B, np.int64)
    idx, sp = demand(lane, wire)
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
    dzv = np.interp(v, [0.0, 5.0, 12.0, 25.0], [0.08, 0.12, 0.18, 0.18])
    rec = {k: np.zeros((B, NF)) for k in ("th", "om", "la", "plan", "wire", "T", "slew", "cb", "pb")}
    T1k = np.zeros((B, NF * 10), np.float32)
    om1k = np.zeros((B, NF * 10), np.float32)
    cb = np.zeros(B)
    pb = np.zeros(B)
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            thq = np.round(pl.thw / 0.1) * 0.1 if np.any(pl.two) else np.round(pl.th / 0.1) * 0.1
            meas = kla(v) * thq
            spt = setpoint[:, k]
            e = spt - meas
            el = e * (1 + lsf / KP)
            el32 = el.astype(np.float32).astype(float)
            cw = np.interp(np.abs(spt), [0.0, 0.18, 0.35], [1.0, 1.0, 0.0])
            fj = np.sign(jerk[:, k]) * np.maximum(np.abs(jerk[:, k]) - dzv * cw, 0.0)
            fr = np.interp(el + 0.22 * fj, [-THR, THR], [-FRIC * LAF, FRIC * LAF])
            if not lim_flag.all():
                pass
            Inew = I + KI * 0.01 * el32
            I = np.where(lim_flag, I, Inew)
            outp = np.clip(KP * el32 + I + spt + fr, -LAF, LAF)
            tq = outp / LAF
            lim = np.clip(tq, last - 0.03, last + 0.03)
            lim_flag = np.abs(tq - lim) > 1e-2
            last = lim
            q[:, k] = np.trunc(np.clip(-lim * 4096.0, -4096, 4096)).astype(np.int64)
            rec["th"][:, k] = pl.th
            rec["om"][:, k] = pl.om
            rec["la"][:, k] = meas
            rec["plan"][:, k] = spt
            rec["slew"][:, k] = lim_flag
        if n - pipe >= 0 and (n - pipe) % 10 == 0:
            wire = q[:, (n - pipe) // 10]
            idx, sp = demand(lane, wire)
        x = pl.sense()
        T = lane.tick(-x, sp, idx, 254)
        cb += lane.cbind
        pb += lane.pbind
        pl.step(T.astype(float), dist[:, n])
        T1k[:, n] = T
        om1k[:, n] = pl.om
        if n % 10 == 9:
            rec["wire"][:, k] = wire
            rec["T"][:, k] = T
    rec["cbind"] = cb / (NF * 10)
    rec["pbind"] = pb / (NF * 10)
    rec["T1k"] = T1k
    rec["om1k"] = om1k
    rec["maxabs"] = dict(lane.maxabs)
    return rec


def bp(x, lo, hi, fs=100.0):
    b, a = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return signal.filtfilt(b, a, x, axis=-1)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x) ** 2)))


def dwell_jumps(om, fs=100.0):
    """dwell-then-jump events: >= 0.2 s with |om| < 0.25 deg/s followed within 0.1 s by |om| > 3 deg/s."""
    n = 0
    sizes = []
    for j in range(om.shape[0]):
        still = np.abs(om[j]) < 0.25
        i = 0
        L = len(still)
        while i < L:
            if still[i]:
                a = i
                while i < L and still[i]:
                    i += 1
                if i - a >= 20 and i < L - 10:
                    pk = np.max(np.abs(om[j, i:i + 30]))
                    if pk > 3.0:
                        n += 1
                        sizes.append(pk)
            else:
                i += 1
    return n, (float(np.median(sizes)) if sizes else 0.0)


def lc_peak(om, lo=1.0, hi=5.0, fs=100.0):
    f, p = signal.welch(om - om.mean(axis=-1, keepdims=True), fs=fs, nperseg=1024, axis=-1)
    p = p.mean(axis=0)
    m = (f >= lo) & (f <= hi)
    k = np.flatnonzero(m)[int(np.argmax(p[m]))]
    sh = ((f >= lo * 0.5) & (f < lo)) | ((f > hi) & (f <= hi * 1.6))
    cf = np.polyfit(np.log(f[sh]), np.log(p[sh] + 1e-30), 1)
    return float(f[k]), float(10 * np.log10(p[k] / np.exp(np.polyval(cf, np.log(f[k])))))


def road(B, n, rms_T, seed, lo=0.3, hi=8.0):
    rng = np.random.default_rng(seed)
    b, a = signal.butter(2, [lo / 500.0, hi / 500.0], btype="band")
    d = signal.lfilter(b, a, rng.normal(size=(1, n)), axis=-1)
    d = d / d.std() * rms_T
    return np.repeat(d, B, 0)


RES = {}
names = list(MEM)
# ---------------------------------------------------------------- HOLD (on-centre) at five speeds
P("=== HOLD on-centre, 60 s, planner wander 0.05 m/s^2 rms (0.05-0.5 Hz), road torque 15 T rms (0.3-8 Hz)")
for v in (3.1, 8.0, 12.0, 17.0, 26.9):
    secs = 60.0
    cl = [V294] * len(names) + [B964] * len(names)
    mm = [MEM[k] for k in names] * 2
    B = len(cl)
    rng = np.random.default_rng(3)
    bb, aa = signal.butter(2, [0.05 / 50, 0.5 / 50], btype="band")
    wander = signal.lfilter(bb, aa, rng.normal(size=int(secs * 100)))
    wander = wander / wander.std() * 0.05
    sp_ = np.repeat(wander[None], B, 0)
    jk = np.gradient(sp_, axis=1) * 100
    r = run(cl, mm, v, sp_, jk, road(B, int(secs * 1000), 15.0, 5), secs, seed=11)
    nn = len(names)
    for j, nm in enumerate(names):
        rr = []
        for off in (0, nn):
            om = r["om"][j + off:j + off + 1, 500:]
            dj = dwell_jumps(om)
            lc = lc_peak(om)
            rr.append(dict(r_lo=rms(bp(om, 0.3, 1.0)), r_mid=rms(bp(om, 1.0, 3.0)), r_hi=rms(bp(om, 3.0, 8.0)),
                           th_rms=rms(r["th"][j + off, 500:]), lc_f=lc[0], lc_dB=lc[1], dj=dj[0], dj_size=dj[1],
                           cb=float(r["cbind"][j + off]), slew=float(r["slew"][j + off].mean()),
                           err=rms(r["plan"][j + off, 500:] - r["la"][j + off, 500:])))
        RES[("hold", v, nm)] = rr
        a, b = rr
        P("  v %4.1f %-12s r_lo %.2f->%.2f  r_mid %.2f->%.2f  r_hi %.2f->%.2f  th_rms %.2f->%.2f  err %.3f->%.3f  "
          "LC %.2fHz %+.1fdB -> %.2fHz %+.1fdB  dwell-jumps %d (%.1f) -> %d (%.1f)  Cbind %.4f  slew %.3f->%.3f" % (
              v, nm, a["r_lo"], b["r_lo"], a["r_mid"], b["r_mid"], a["r_hi"], b["r_hi"], a["th_rms"], b["th_rms"], a["err"], b["err"],
              a["lc_f"], a["lc_dB"], b["lc_f"], b["lc_dB"], a["dj"], a["dj_size"], b["dj"], b["dj_size"], b["cb"], a["slew"], b["slew"]))

# ---------------------------------------------------------------- TURN (hard) at 8 / 12 / 17 / 20 m/s
P()
P("=== HARD TURNS: lat accel 0 -> A (1 s ramp), hold 3 s, back (1 s), then -A; road torque 15 T rms")
for v, Aacc in ((8.0, 2.0), (12.0, 2.5), (17.0, 2.5), (20.0, 3.0)):
    secs = 16.0
    t = np.arange(int(secs * 100)) / 100.0

    def prof(t, A_):
        y = np.zeros_like(t)
        for t0, sgn in ((1.0, 1), (8.0, -1)):
            y += sgn * A_ * np.clip((t - t0) / 1.0, 0, 1) * (1 - np.clip((t - t0 - 4.0) / 1.0, 0, 1))
        return y
    spt = prof(t, Aacc)
    cl = [V294] * len(names) + [B964] * len(names)
    mm = [MEM[k] for k in names] * 2
    B = len(cl)
    sp_ = np.repeat(spt[None], B, 0)
    jk = np.gradient(sp_, axis=1) * 100
    r = run(cl, mm, v, sp_, jk, road(B, int(secs * 1000), 15.0, 7), secs, seed=13)
    nn = len(names)
    hard = np.abs(spt) >= 1.5
    for j, nm in enumerate(names):
        rr = []
        for off in (0, nn):
            om = r["om"][j + off]
            h16 = bp(om[None], 1.6, 3.0)[0]
            la, pl_ = r["la"][j + off], r["plan"][j + off]
            hold = (np.abs(pl_) > 0.95 * Aacc)
            T1 = r["T1k"][j + off].astype(float)
            hf = [rms(bp(T1[None], lo, hi, fs=1000.0)[0][500:-500]) for lo, hi in ((5, 9), (9, 13), (13, 17), (17, 23), (23, 30))]
            rr.append(dict(h16=rms(h16[hard]), r_mid=rms(bp(om[None], 1.0, 3.0)[0][100:-100]),
                           hold=float(np.median(la[hold] / pl_[hold])), ovs=float(np.max(np.abs(la)) / Aacc),
                           Tmax=float(np.max(np.abs(r["T1k"][j + off]))), cb=float(r["cbind"][j + off]), pb=float(r["pbind"][j + off]),
                           slew=float(r["slew"][j + off].mean()), hf=hf, lc=lc_peak(om[None, 100:])))
        RES[("turn", v, nm)] = rr
        a, b = rr
        P("  v %4.1f A %.1f %-12s hard 1.6-3 Hz %.2f->%.2f (x%.2f)  r_mid %.2f->%.2f  hold %.3f->%.3f  peak|la|/A %.3f->%.3f  "
          "Tmax %.0f->%.0f  Cbind %.4f->%.4f Pbind %.4f  slew %.3f->%.3f  HF T x %s  LC %.2fHz %+.1f -> %.2fHz %+.1f" % (
              v, Aacc, nm, a["h16"], b["h16"], b["h16"] / max(a["h16"], 1e-9), a["r_mid"], b["r_mid"], a["hold"], b["hold"],
              a["ovs"], b["ovs"], a["Tmax"], b["Tmax"], a["cb"], b["cb"], b["pb"], a["slew"], b["slew"],
              "/".join("%.2f" % (y / max(x_, 1e-9)) for x_, y in zip(a["hf"], b["hf"])), a["lc"][0], a["lc"][1], b["lc"][0], b["lc"][1]))

# ---------------------------------------------------------------- CREEP stick-slip at 3.1 m/s
P()
P("=== CREEP 3.1 m/s: slow setpoint triangle 0 -> 0.25 m/s^2 over 20 s and back (friction-dominated), no road noise")
secs = 40.0
t = np.arange(int(secs * 100)) / 100.0
spt = 0.25 * (1 - np.abs(t - 20.0) / 20.0)
cl = [V294] * len(names) + [B964] * len(names)
mm = [MEM[k] for k in names] * 2
B = len(cl)
sp_ = np.repeat(spt[None], B, 0)
jk = np.gradient(sp_, axis=1) * 100
r = run(cl, mm, 3.1, sp_, jk, np.zeros((B, int(secs * 1000))), secs, seed=17)
nn = len(names)
for j, nm in enumerate(names):
    rr = []
    for off in (0, nn):
        om = r["om"][j + off:j + off + 1, 200:]
        dj = dwell_jumps(om)
        th = r["th"][j + off, 200:]
        rr.append(dict(dj=dj[0], size=dj[1], pk_om=float(np.max(np.abs(om))), err=rms(r["plan"][j + off, 200:] - r["la"][j + off, 200:]),
                       stuck=float(np.mean(np.abs(om) < 0.25))))
    RES[("creep", 3.1, nm)] = rr
    a, b = rr
    P("  %-12s dwell-jumps %d (median peak %.1f deg/s) -> %d (%.1f)   peak |om| %.1f -> %.1f  stuck share %.2f -> %.2f  "
      "err %.4f -> %.4f" % (nm, a["dj"], a["size"], b["dj"], b["size"], a["pk_om"], b["pk_om"], a["stuck"], b["stuck"], a["err"], b["err"]))
P()
P("int32 max |a*s| / |E*Kp| seen in these runs (b964 lanes included):", r["maxabs"])
json.dump({"|".join(str(x) for x in k): v for k, v in RES.items()}, open(os.path.join(HERE, "a4_nl.json"), "w"), default=float)
out.close()
