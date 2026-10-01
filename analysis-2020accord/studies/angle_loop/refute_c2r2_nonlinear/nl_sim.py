# -*- coding: utf-8 -*-
r"""nl_sim.py -- C2 rev 2 NONLINEAR refuter (2026-10-01): an INDEPENDENT 1 kHz closed-loop simulation of the four
candidate lanes (rev2-A P2 / F2, rev2-B D2a / B0r).  ANALYSIS ONLY: builds no image, sends nothing, flashes nothing.

Independence: the lane below is written from the instruction listing (my own Ghidra dry-run of 0x29D60..0x29F80 on
the V294 program + the decompile of FUN_00028ea6), the cave arithmetic is nl_cave.mirror (proved equal to my own
interpreter executing the cave BYTES, 0 mismatches), the cal is read from the V295 image bytes here, and the plant is
my own Karnopp integrator with the r71b family's parameters (v294_plant.family() is used ONLY as the parameter table).
Nothing imports ds_lane / ds_time / harness_time / c1_lib.

LANE (every line = an instruction of FUN_00028ea6 with the C2 edit set; addresses in the comments)
SENSORS: gp-0x6a00 = floor(10 th + 0.5) and gp-0x6a56 = clamp(-((abe*48*1159)>>15), +-12000), both refreshed by slot 4
  on tick % 10 == 4 AFTER the lane (age 1..10; '+h10' columns deliver the sample taken 10 ticks earlier = ages 11..20);
  gp-0x6abe = the 1 kHz integer EMA of gp-0x4f50 = s16(round(-4.712 om + N(0, 2.8))) (alpha 37/128), BEFORE the lane.
  (The EMA/hold forms and the 2.8-count noise are the D designer's decode / BELIEF; re-used as a model, not as code.)
FORK: 0xE4 on tick % 10 == 0, raw = -round(10 th_ref), gp-0x69ae = clamp(-4 raw, +-16384); a stop holds the last value.
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parent
KIT = AL.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(KIT / "analysis-2020accord" / "studies" / "v295" / "plant"))
import nl_cave as NC  # noqa: E402
import v294_plant as VP  # noqa: E402

V295 = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
            "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
            "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
SENT = 0x7FFF
ABE_PER = -8.0 / (48.0 * 1159.0 / 32768.0)      # gp-0x6abe counts per deg/s (-4.712)
N4F50 = 2.8
NSUB = 10


def _cal():
    img = V295.read_bytes()
    u16 = lambda a: struct.unpack_from("<H", img, a)[0]  # noqa: E731
    i16 = lambda a: struct.unpack_from("<h", img, a)[0]  # noqa: E731
    u32 = lambda a: struct.unpack_from("<I", img, a)[0]  # noqa: E731

    def rec(bank, n):
        p = u32(bank + 4 * 7)
        return (np.array([u16(p + 2 + 2 * i) for i in range(n)], np.int64),
                np.array([u16(p + 2 + 2 * n + 2 * i) for i in range(n)], np.int64))
    return dict(PCL=u16(0xC61BC), SCL=u16(0xC61BE), OCL=u16(0xC61B4), oa=i16(0xC63EC), ob=u16(0xC63EE),
                g74a3=img[0xC64A3], dz=i16(0xC61B8), fwd=i16(0xC6CD0), fadeA=rec(0xCBC34, 6), fadeB=rec(0xCBBC4, 6))


CAL = _cal()
# the C2 cal set (both revisions): a 0, b 8192, C 65535, DB 0, Ki 56, ICL 4096, DCL 10240, Kp flat 112, Kd 34 | 20
KP, KI, ICL, DCL, DB = 112, 56, 4096, 10240, 0
IMPL = {"P2": ("fresh", 34), "D2a": ("fresh", 34), "F2": ("held", 20), "B0r": ("held", 20)}
ROWS = {k: NC.parse_table(NC.load_hex(k))[1] for k in IMPL}
GLUT = {k: np.array([NC.walk_G(ROWS[k], v) for v in range(0, 12001)], np.int64) for k in IMPL}


def lerp_vec(X, Y, u):
    u = np.asarray(u, np.int64)
    n = len(X)
    k = np.clip(np.searchsorted(X, u, side="right"), 1, n - 1)
    x0, x1, y0, y1 = X[k - 1], X[k], Y[k - 1], Y[k]
    num = (y1 - y0) * (u - x0)
    den = x1 - x0
    q = np.abs(num) // np.abs(den)
    mid = y0 + np.where((num < 0) != (den < 0), -q, q)
    return np.where(u <= X[0], Y[0], np.where(u >= X[-1], Y[-1], mid))


def s32(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def s16(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 15)) & 0xFFFF) - (1 << 15)


class Lane:
    """the C2 lane, vectorised over columns (impl per column)."""

    def __init__(self, impls, speeds_word):
        B = len(impls)
        self.B = B
        self.fresh = np.array([IMPL[i][0] == "fresh" for i in impls])
        self.kd = np.array([IMPL[i][1] for i in impls], np.int64)
        sw = np.clip(np.asarray(speeds_word, np.int64), 0, 12000)
        self.G = np.array([GLUT[i][s] for i, s in zip(impls, sw)], np.int64)
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.olag, self.Tprev = z(), z(), z(), z(), z()
        self.wraps = 0
        self.log = {}

    def tick(self, angle, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        c = CAL
        # fb filter 0x28F4C..0x28FBE with E1 (x := gp-0x6a00), E2 (add), cals a 0, b 8192, C 65535
        x = s16(angle)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((0 * s_old >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        # guard A2 + B2: the PID runs iff ramp != 0 and request == 1 (and bVar2: mode-3 valid, assumed true here)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(cmd)                                          # E4: ld.h -0x69ae[gp],r16
        # ---- THE CAVE (nl_cave.mirror, = the bytes) ----
        E = s32((sp << 2) - r26)                               # displaced shl 2 ; sub r26,r16
        prod = E * self.G
        self.wraps += int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8                                    # mul r8,r16,r0 ; sar 8
        atq = np.minimum(np.abs(tq), 0xFFFF)                   # gp-0x4f68 = |gp-0x4f60| saturated
        frz = (atq > 512) | ((np.int64(ramp) & 0x8000) == 0)
        ab = s16(abe)
        op = np.where(((ab + 13000) & 0xFFFFFFFF) <= 26000, ab, 0)
        # ---- Honda's I 0x29D7A..0x29DC2 (freeze returns to 0x29D7E with r6 = 0); DB 0 ----
        e5 = np.where(frz, 0, Ep >> 5)
        exc = np.where(e5 > DB, e5 - DB, np.where(e5 < -DB, e5 + DB, 0))
        icl = (ICL << 10) >> 3
        I = np.clip(s32((self.I8 >> 3) + (s32(exc * KI) >> 3)), -icl, icl)
        I8n = s32(I << 3)
        # ---- P 0x29E34..0x29E5C ----
        P = np.clip(s32(Ep * KP) >> 8, -c["PCL"], c["PCL"])
        # ---- D 0x29EDE..0x29F06: fresh (OPH mov r26,r8 ; zxh r7 Kd>0) | held (E5 subr r0,r7 ; ld.h -0x6a56) ----
        Dfr = s32(self.kd * op) >> 3
        Dhe = s32(-self.kd * s16(xheld)) >> 3
        D = np.clip(np.where(self.fresh, Dfr, Dhe), -DCL, DCL)
        # ---- sum, fade, sum clamp 0x29F18..0x2A162 ----
        S = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(np.asarray(tq, np.int64) >> 5), 255)
        fA = lerp_vec(*c["fadeA"], np.zeros(self.B, np.int64))
        fB = lerp_vec(*c["fadeB"], i682f)
        f = ((fA * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        # ---- output lag 0x2A174..0x2A1B0 ----
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t1 + t2)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        # ---- sign-hold gate 0x2A198..0x2A1E4 ----
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1 and act == 0:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where(blk, 0, yr)
        k = pol * c["fwd"]
        r11 = s32(yr * k) >> 15
        T = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), P=np.where(run, P, 0), D=np.where(run, D, 0), E=np.where(run, E, 0),
                        frz=frz, f=f, run=run)
        return s16(T)


# ------------------------------------------------------------------------------------------------------------------
# members (built here from the family's parameter table)
# ------------------------------------------------------------------------------------------------------------------
_FAM = VP.family()


def params(member, v):
    """(J, b, k, sat, Fc, Fs, tau_ms) at speed v for the lens members."""
    def at(name):
        return _FAM[name].arrays_at(np.array([float(v)]))
    if member.endswith("_nf"):                 # the same member with friction removed (linear control for the lens)
        J, b, k, sat, Fc, Fs, tau = params(member[:-3], v)
        return J, b, k, sat, 0.0, 0.0, tau
    if member in ("nominal", "F_hi", "F_lo", "J_hi", "b_lo", "tau6"):
        a = at(member)
        tau = _FAM[member].tau_ms
    elif member == "bc":                       # b_lo's damping, Coulomb/static x2 at >= 10, x1.3 at 5..10 (centres, interp)
        a = at("b_lo")
        n = at("nominal")
        fx = np.interp(float(v), VP.V_CENTRES, np.where(VP.V_CENTRES >= 10, 2.0, np.where(VP.V_CENTRES >= 5, 1.3, 1.0)))
        a = dict(a, Fc=n["Fc"] * fx, Fs=n["Fs"] * fx)
        tau = 2
    elif member == "b_lo*J_hi":                # J_hi refit, damping x 1/1.8 at >= 10 m/s, x0.7 below (per-speed step)
        a = at("J_hi")
        a = dict(a, b=a["b"] * (1 / 1.8 if v >= 10.0 else 0.7))
        tau = 2
    else:
        raise KeyError(member)
    g = lambda q: float(np.asarray(a[q]).ravel()[0])  # noqa: E731
    return g("J"), g("b"), g("k"), g("sat"), g("Fc"), g("Fs"), int(tau)


class Plant:
    """Karnopp stick-slip rigid plant, per-column parameters, 10 kHz sub-steps:
       J th'' + b th' + k sat tanh(th/sat) + friction = u + hand;  stuck while th' == 0 and |net| <= Fs."""

    def __init__(self, cols):
        P = np.array([params(c["member"], c["v"]) for c in cols], float)
        self.J, self.b, self.k, self.sat, self.Fc, self.Fs = (P[:, i] for i in range(6))
        self.tau = P[:, 6].astype(int)
        B = len(cols)
        self.th = np.zeros(B)
        self.om = np.zeros(B)
        self.buf = np.zeros((int(self.tau.max()) + 1, B))
        self.n = 0

    def delay(self, T):
        L = self.buf.shape[0]
        self.buf[self.n % L] = T
        out = self.buf[(self.n - self.tau) % L, np.arange(len(T))]
        self.n += 1
        return out

    def step(self, u, hand_k=None, hand_b=None, hand_th=None, dt=1e-3):
        h = dt / NSUB
        for _ in range(NSUB):
            th, om = self.th, self.om
            net = u - self.k * self.sat * np.tanh(th / self.sat) - self.b * om
            if hand_k is not None:
                net = net + hand_k * (hand_th - th) - hand_b * om
            stuck = (om == 0.0) & (np.abs(net) <= self.Fs)
            fdir = np.where(om != 0.0, np.sign(om), np.sign(net))
            om_new = om + np.where(stuck, 0.0, (net - self.Fc * fdir) / self.J) * h
            om_new = np.where(stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om))), 0.0, om_new)
            self.om = om_new
            self.th = th + om_new * h


@dataclass
class Scn:
    dur: float
    ref: object                    # f(t) -> (B,) deg (the fork's planned angle)
    tq: object = None              # f(t, th, om) -> (B,) torque word (gp-0x4f60, signed)
    hand: object = None            # f(t) -> None | (Kh (B,), Bh (B,), th_h (B,))
    uext: object = None            # f(t) -> (B,) external wheel torque (T counts, + left)
    events: tuple = ()             # ((t, kind), ...) kind in fault | dis | latch | relatch | engage | stop
    mode0: str = "engaged"
    th0: object = None             # (B,) initial angle
    sp_hold_from: float | None = None      # fork sends the last command from here on (engage-under-load)
    sp_meas_until: float | None = None     # fork sends the measured angle until here


def run(cols, scn: Scn, seed=11, rec_every=1):
    B = len(cols)
    impls = [c["impl"] for c in cols]
    vw = np.array([int(round(c["v"] * 3.6 * 64)) for c in cols], np.int64)
    aged = np.array([c.get("age", 0) == 10 for c in cols])
    lane = Lane(impls, vw)
    pl = Plant(cols)
    if scn.th0 is not None:
        pl.th = np.asarray(scn.th0, float).copy()
    rng = np.random.default_rng(seed)
    nT = int(round(scn.dur * 1000))
    th_r = np.zeros((nT, B), np.float32)
    om_r = np.zeros((nT, B), np.float32)
    T_r = np.zeros((nT, B), np.int16)
    sp_r = np.zeros((nT, B), np.int32)
    I_r = np.zeros((nT, B), np.int32)
    fz_r = np.zeros((nT, B), bool)
    wire = []
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    fifo = []
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    mode = scn.mode0
    ramp = 0x8000 if mode == "engaged" else 0
    act = req = 1 if mode == "engaged" else 0
    ev = sorted(scn.events)
    ei = 0
    sen = False
    stopped = False
    for n in range(nT):
        t = n * 1e-3
        while ei < len(ev) and t >= ev[ei][0] - 1e-9:
            kind = ev[ei][1]
            if kind == "fault":
                sen, mode = True, "fault"
            elif kind == "stop":
                stopped = True
            elif kind == "dis":
                mode = "dis"
            elif kind == "latch":
                mode = "latch"
            elif kind in ("relatch", "engage"):
                mode = "relatch"
            ei += 1
        if mode == "engaged":
            ramp, act, req = 0x8000, 1, 1
        elif mode in ("fault", "dis"):
            ramp, act, req = max(0, ramp - 16), 0, (0xFF if mode == "fault" else 0)
        elif mode == "latch":
            ramp, act, req = max(0, ramp - 328), 0, 1
        elif mode == "relatch":
            ramp, act, req = min(0x8000, ramp + 33), 1, 1
        elif mode == "off":
            ramp, act, req = max(0, ramp - 16), 0, 0
        if n % 10 == 0 and not sen and not stopped:
            k6 = max(len(wire) - 6, 0)
            th_meas = wire[k6] / 10.0 if wire else pl.th.copy()
            if mode in ("dis", "off") or (scn.sp_meas_until is not None and t < scn.sp_meas_until):
                thc = th_meas
                cmd = np.clip(-(s16(-np.floor(10.0 * thc + 0.5).astype(np.int64)) << 2), -0x4000, 0x4000)
            elif scn.sp_hold_from is not None and t >= scn.sp_hold_from:
                pass
            else:
                thc = np.asarray(scn.ref(t), float) * np.ones(B)
                raw = s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))
                cmd = np.clip(s32(-(raw << 2)), -0x4000, 0x4000)
        cmd_in = np.full(B, SENT, np.int64) if sen else cmd
        tq = np.zeros(B, np.int64) if scn.tq is None else np.round(np.asarray(scn.tq(t, pl.th, pl.om), float) *
                                                                   np.ones(B)).astype(np.int64)
        g4f50 = s16(np.round(ABE_PER * pl.om + rng.normal(0.0, N4F50, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = s16(st >> 10)
        T = lane.tick(held_th, held_x, abe, cmd_in, tq, ramp, act, req)
        q_now = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
        x_now = np.clip(-((s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
        fifo.append((q_now, x_now))
        if len(fifo) > 11:
            fifo.pop(0)
        if n % 10 == 4:
            held_th = np.where(aged, fifo[0][0], q_now)
            held_x = np.where(aged, fifo[0][1], x_now)
            wire.append(q_now.copy())
        Tapp = pl.delay(T.astype(float))
        u = -Tapp + (np.asarray(scn.uext(t), float) if scn.uext is not None else 0.0)
        hh = scn.hand(t) if scn.hand is not None else None
        if hh is None:
            pl.step(u)
        else:
            pl.step(u, *hh)
        th_r[n], om_r[n], T_r[n], sp_r[n] = pl.th, pl.om, T, cmd_in
        I_r[n] = lane.log["I"]
        fz_r[n] = lane.log["frz"]
    return dict(th=th_r, om=om_r, T=T_r, sp=sp_r, I=I_r, frz=fz_r, wire=np.array(wire), wraps=lane.wraps)


# ------------------------------------------------------------------------------------------------------------------
# metric helpers (my own implementations)
# ------------------------------------------------------------------------------------------------------------------
def runs_of(mask, minlen):
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


def slips(th, om):
    """stick >= 100 ms (om exactly 0) followed by a >= 0.1 deg move within 0.5 s."""
    out = np.zeros(th.shape[1], int)
    for j in range(th.shape[1]):
        for a, b in runs_of(om[:, j] == 0.0, 100):
            if b < th.shape[0] - 1:
                e = min(b + 500, th.shape[0] - 1)
                if abs(th[e, j] - th[b - 1, j]) >= 0.1:
                    out[j] += 1
    return out


def dwell_jump(om_f, th_f, ref_f):
    """record-style DWELL-THEN-JUMP on 100 Hz frames: dwell = 0.1 s moving mean |rate| < 0.25 deg/s for >= 10 frames
    while the reference moved >= 0.1 deg; event if the wheel then jumps >= max(2x the reference's change, 0.2 deg)
    before the next dwell (<= 0.5 s)."""
    B = om_f.shape[1]
    ker = np.ones(10) / 10.0
    ev = np.zeros(B, int)
    jm = np.zeros(B)
    for j in range(B):
        rs = np.convolve(np.abs(om_f[:, j]), ker, "same")
        rr = runs_of(rs < 0.25, 10)
        th, rf = th_f[:, j], ref_f[:, j]
        for q, (a, b) in enumerate(rr):
            if b + 2 >= len(th) or abs(rf[b - 1] - rf[a]) < 0.1:
                continue
            e = rr[q + 1][0] if q + 1 < len(rr) else len(th) - 1
            e = min(e, b + 50, len(th) - 1)
            jump = abs(th[e] - th[b])
            if jump >= max(2.0 * abs(rf[e] - rf[b]), 0.2):
                ev[j] += 1
                jm[j] = max(jm[j], jump)
    return ev, jm


def bp(x, lo, hi, fs=1000.0):
    from scipy import signal
    sos = signal.butter(2, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def wire_gain(r, t0):
    """OLS slope of the 0x14A angle (100 Hz, slot-4 frames) on the received setpoint, from t0."""
    w = r["wire"].astype(float) / 10.0
    idx = np.arange(w.shape[0]) * 10 + 4
    sp = r["sp"][idx.clip(0, r["sp"].shape[0] - 1)].astype(float) / 40.0
    m = idx * 1e-3 >= t0
    X, Y = sp[m], w[m]
    xm = X - X.mean(0)
    return (xm * (Y - Y.mean(0))).sum(0) / np.maximum((xm ** 2).sum(0), 1e-12)
