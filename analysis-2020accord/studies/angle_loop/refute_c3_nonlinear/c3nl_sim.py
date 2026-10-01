# -*- coding: utf-8 -*-
r"""c3nl_sim.py -- C3 round-1 NONLINEAR refuter (2026-10-01): an INDEPENDENT 1 kHz closed-loop simulation of design C3
(C3-P primary, C3-F fallback) plus the references P2 (rev2-A) and E2-A3.  ANALYSIS ONLY: builds no image, flashes
nothing, sends nothing, touches no design or fork file.

Independence (what is and is not re-used):
  * THE LANE is written here from two sources that are NOT the common scorer's CandLane:
      - Honda's downstream arithmetic (I, P, D, sum, fade, sum clamp, output lag, sign-hold gate, x ramp, x pol x fwd,
        lane clamp) from lane_mirror_v295.py (the tracer's byte-exact mirror, every line an address);
      - the cave from the C3 design's own listing (DESIGN-ANGLE-LOOP-C3 sec 1.2 / sec 2) read against the cave HEX:
        the G(v) table rows are parsed here from the hex bytes (struct, LE), the policy constants (512, 2880 shl 4/6,
        1250, 1382, 4096) are the listed immediates, cross-checked against the hex bytes in check_hex_immediates().
    The cal is read LE from the V295 image here (and compared with lane_mirror_v295.load_cal in the control).
  * THE PLANT is my own Karnopp integrator (same equation as the brief: J th'' + b th' + k sat tanh(th/sat) + friction);
    the member PARAMETERS come from the r71b family via nl_sim.params (a parameter table, the credible-set definition).
  * SENSORS / FORK: written here from the TRACE facts (gp-0x6a00 = floor(10 th + 0.5) refreshed by slot 4 at
    tick % 10 == 4 after the lane; gp-0x6abe = 1 kHz integer EMA alpha 37/128 of gp-0x4f50 = s16(round(-4.712 * motor
    deg/s + N(0, 2.8))); gp-0x6a56 = slot-4 hold of clamp(-((abe*48*1159)>>15), +-12000); 0xE4 on tick % 10 == 0,
    raw = -round(10 th_sp), gp-0x69ae = clamp(-4 raw, +-16384)); the 'vgr' frame (motor rate = omega / kappa(theta))
    from the correction LERP 0xC6892/0xC68A2 read by angle_signal_mirror.Cal.
  * NEW HERE (not in the common scorer): per-tick SPEED traces (plant params, the G(v) walk, the ARB slope knee and the
    low-speed cap all follow v(t)), aged sensor delivery, consistent-sensor hands, outward / partial hands.
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parent
KIT = AL.parents[2]
for _q in (AL / "refute_c2r2_nonlinear", AL, KIT / "analysis-2020accord" / "studies" / "v295" / "plant"):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))
import angle_signal_mirror as AM  # noqa: E402  (the correction LERP cal, read from the image)
import nl_sim as NSP              # noqa: E402  (ONLY nl_sim.params: the member parameter table)

V295 = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
            "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
            "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
OUT = KIT / "_scratch" / "angle_loop" / "refute-c3-nonlinear"
OUT.mkdir(parents=True, exist_ok=True)
SENT = 0x7FFF
SENT32 = 0x7FFFFFFF
ABE_PER = -8.0 / (48.0 * 1159.0 / 32768.0)         # gp-0x6abe counts per motor deg/s
TP = 0xBF000
SEL = 7


def s32(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def s16(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 15)) & 0xFFFF) - (1 << 15)


# ------------------------------------------------------------------------------------------------------------------
# calibration (V295 image, LE) -- addresses per lane_mirror_v295.load_cal
# ------------------------------------------------------------------------------------------------------------------
def _cal():
    img = V295.read_bytes()
    u16 = lambda a: struct.unpack_from("<H", img, a)[0]  # noqa: E731
    i16 = lambda a: struct.unpack_from("<h", img, a)[0]  # noqa: E731
    u32 = lambda a: struct.unpack_from("<I", img, a)[0]  # noqa: E731

    def rec(bank, n):
        p = u32(bank + 4 * SEL)
        assert u16(p) == n
        return (np.array([u16(p + 2 + 2 * i) for i in range(n)], np.int64),
                np.array([u16(p + 2 + 2 * n + 2 * i) for i in range(n)], np.int64))
    return dict(PCL=u16(TP + 0x71BC), SCL=u16(TP + 0x71BE), OCL=u16(TP + 0x71B4), oa=i16(TP + 0x73EC),
                ob=u16(TP + 0x73EE), g74a3=img[TP + 0x74A3], dz=i16(TP + 0x71B8), fwd=i16(TP + 0x7CD0),
                fadeA=rec(0xCBC34, 6), fadeB=rec(0xCBBC4, 6),
                # V295 values of the cells C3 changes (asserted in the control against the design's sec 1.3)
                v295_ICL=u16(TP + 0x71BA), v295_Ki=u16(TP + 0x73E6), v295_DCL=u16(TP + 0x71B6),
                v295_DB=u16(TP + 0x72E4), v295_a=i16(TP + 0x73E8), v295_b=u16(TP + 0x73EA), v295_C=u16(TP + 0x72E6))


CAL = _cal()


def lerp_vec(X, Y, u):
    """Honda's integer LERP (divq truncates toward zero), vectorised."""
    u = np.asarray(u, np.int64)
    n = len(X)
    k = np.clip(np.searchsorted(X, u, side="right"), 1, n - 1)
    x0, x1, y0, y1 = X[k - 1], X[k], Y[k - 1], Y[k]
    num = (y1 - y0) * (u - x0)
    den = x1 - x0
    q = np.abs(num) // np.abs(den)
    mid = y0 + np.where((num < 0) != (den < 0), -q, q)
    return np.where(u <= X[0], Y[0], np.where(u >= X[-1], Y[-1], mid))


FA0 = int(lerp_vec(*CAL["fadeA"], np.array([0]))[0])          # gp-0x6830 = 0 (no grab rate in the sim)


# ------------------------------------------------------------------------------------------------------------------
# the caves: table rows parsed from the HEX bytes; policy immediates cross-checked against the bytes
# ------------------------------------------------------------------------------------------------------------------
def hexbytes(p):
    return bytes.fromhex(Path(p).read_text().replace("\n", " "))


def parse_rows(b):
    i = b.find(bytes.fromhex("2906"))                       # mov imm32,r9 (6-byte form) -> the table address
    taddr = struct.unpack_from("<I", b, i + 2)[0]
    off = taddr - 0xC4C00
    rows = [struct.unpack_from("<HHh", b, off + 6 * k) for k in range((len(b) - off) // 6)]
    assert rows[-1][0] == 0xFFFF
    return tuple(rows), off


def walk_G(rows, v):
    """the cave's walk, scalar: X0 test (bh), segment search (bnh on X(i+1)), G(i) + ((v - X(i)) * S(i)) >> 12."""
    v &= 0xFFFF
    if not v > rows[0][0]:
        return rows[0][1]
    i = 0
    while not v <= rows[i + 1][0]:
        i += 1
    X, G, S = rows[i]
    prod = (v - X) * S
    prod = ((prod + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)
    return G + (prod >> 12)


def check_hex_immediates(b):
    """the listed policy immediates, found at their listed encodings in the bytes (movea imm16,r0,r13 = 20 6e lo hi)."""
    need = {"512": "206e0002", "2880": "206e400b", "1250 (addi r9)": "094ee204", "1382": "206e6605",
            "4096": "206e0010", "shl 4,r9": "c44a", "shl 6,r9": "c64a", "ld.h -0x6a00,r9": "244f0096",
            "ld.w -0x6dd0,r13": "246f3192", "sar 10,r13": "aa6a", "andi 0x8000,r14,r13": "ce6e0080",
            "ld.hu -0x4f68,r8": "e44799b0"}
    return {k: (bytes.fromhex(h) in b) for k, h in need.items()}


C3D = AL / "c3"
IMPL = {}


def _impl(name, hexp, dop, kd, icl, arb):
    b = hexbytes(hexp)
    rows, _ = parse_rows(b)
    IMPL[name] = dict(rows=rows, dop=dop, kd=kd, icl=icl, arb=arb, hex=b,
                      glut=np.array([walk_G(rows, v) for v in range(0, 65536)], np.int64))


A3 = (4, 6, 2880, 1250, 1382, 4096)          # (sh_lo, sh_hi, vth, B, vcap, cap) -- the listed immediates
A2 = (4, 6, 2880, 1250, -1, 0)
_impl("C3-P", C3D / "c3_cave_C3-P.hex", "fresh", 48, 8192, A3)
_impl("C3-F", C3D / "c3_cave_C3-F.hex", "held", 24, 8192, A3)
_impl("C3-PA2", C3D / "c3_cave_C3-PA2.hex", "fresh", 48, 8192, A2)
_impl("P2", AL / "c2" / "rev2A" / "c2_cave_P2.hex", "fresh", 34, 4096, None)
_impl("E2-A3", AL / "panel2" / "E2-integral-most-margin" / "e2_cave_A3.hex", "fresh", 34, 8192, A3)
KP, KI, DCL, DB = 112, 56, 10240, 0


class Lane:
    """C3-class lane, vectorised over columns; every line = an instruction (address in the comment)."""

    def __init__(self, impls):
        self.B = B = len(impls)
        self.gl = np.stack([IMPL[i]["glut"] for i in impls])        # (B, 65536)
        self.fresh = np.array([IMPL[i]["dop"] == "fresh" for i in impls])
        self.kd = np.array([IMPL[i]["kd"] for i in impls], np.int64)
        self.icl = np.array([((IMPL[i]["icl"] & 0xFFFF) << 10) >> 3 for i in impls], np.int64)   # 0x29DA0..AE
        arb = [IMPL[i]["arb"] for i in impls]
        self.arb_on = np.array([a is not None for a in arb])
        aa = [a if a is not None else (0, 0, 0, 0, -1, 0) for a in arb]
        self.sh_lo, self.sh_hi, self.vth, self.Bb, self.vcap, self.cap = (np.array([a[j] for a in aa], np.int64)
                                                                         for j in range(6))
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.olag, self.Tprev = z(), z(), z(), z(), z()
        self.wraps = 0
        self.ar = np.arange(B)
        self.log = {}

    def tick(self, a6a00, abe, x6a56, sp69ae, tq, ramp, act, req, vw, pol=-1):
        c = CAL
        B = self.B
        bc = lambda a: np.broadcast_to(np.asarray(a, np.int64), (B,))  # noqa: E731
        ramp, act, req, tq, vw = bc(ramp), bc(act), bc(req), bc(tq), bc(vw) & 0xFFFF
        # ---- fb filter 0x28F4C..0x28FBC: E1 x := gp-0x6a00 ; a 0, b 8192 ; E2 add ; C 65535
        x = s16(a6a00)                                            # 0x28F4C ld.h -0x6a00[gp],r7  (E1)
        valid = (x >= -12000) & (x <= 12000)                      # 0x28F50..0x28F58 bail test
        s_old = np.where(self.lane_ok == 1, self.s, 0)            # 0x28F66..0x28F84
        s_new = s32((s32(0 * s_old) >> 10) + (s32(x * 8192) >> 10))   # 0x28F86..0x28FA2 (a = 0, b = 8192)
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)          # 0x28FA4 add (E2) ; clamp C 65535
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                    # A2 + B2 (bVar2 taken as true)
        sp = s16(sp69ae)                                          # E4 0x29D6A ld.h -0x69ae[gp],r16
        # ---- THE CAVE (sec 1.2 listing) ----
        E = s32(s32(sp << 2) - r26)                               # 0xC4C00 shl 2,r16 ; 0xC4C02 sub r26,r16
        ab = s16(abe)                                             # 0xC4C04 ld.h -0x6abe[gp],r26
        op = np.where(((ab + 13000) & 0xFFFFFFFF) <= 26000, ab, 0)   # 0xC4C08..0xC4C12 addi/movea/cmp/cmovh
        G = self.gl[self.ar, vw]                                  # 0xC4C16..0xC4C50 the walk
        prod = E * G
        self.wraps += int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8                                       # 0xC4C52 mul ; 0xC4C56 sar 8
        atq = np.minimum(np.abs(tq), 0xFFFF)                      # gp-0x4f68 (|gp-0x4f60| saturated)
        f_hard = atq > 512                                        # 0xC4C58..0xC4C62 bh FRZ
        th = s16(a6a00)                                           # 0xC4C64 ld.h -0x6a00[gp],r9
        ath = np.abs(th)                                          # 0xC4C68..6C cmp/bge/subr
        sh = np.where(vw > self.vth, self.sh_hi, self.sh_lo)      # 0xC4C6E..0xC4C7E (bh = unsigned >)
        bound = s32((ath << sh) + self.Bb)                        # shl ; 0xC4C80 addi 1250
        capon = (self.vcap >= 0) & ~(vw > self.vcap)              # 0xC4C84..0xC4C8A bh skips the cap
        bound = np.where(capon & (bound > self.cap), self.cap, bound)   # 0xC4C8C..0xC4C92 cmovh -> min
        Is = self.I8 >> 10                                        # 0xC4C96 ld.w ; 0xC4C9A sar 10
        t = np.where(Ep >= 0, Is, -Is)                            # 0xC4C9C..0xC4CA0 cmp r0,r16 ; bge ; subr
        f_arb = self.arb_on & (t >= bound)                        # 0xC4CA2 cmp r9,r13 ; bge FRZ
        f_ramp = (ramp & 0x8000) == 0                             # 0xC4CA6 andi ; 0xC4CAA bne DONE
        frz = f_hard | (~f_hard & (f_arb | f_ramp))
        # ---- Honda's I 0x29D7A..0x29DC2 (normal: e5 = E' >> 5 ; FRZ exit 0x29D7E with r6 = 0) ; DB 0
        e5 = np.where(frz, 0, Ep >> 5)
        inc = s32(e5 * KI) >> 3                                   # 0x29DA8 mul ; 0x29DB2 sar 3
        acc = (self.I8 >> 3) + inc                                # 0x29DA4 ld.w ; 0x29DB0 sar 3 ; 0x29DB4 add
        self.wraps += int(np.count_nonzero(s32(acc) != acc))
        I = np.clip(s32(acc), -self.icl, self.icl)
        I8n = s32(I << 3)                                         # 0x29DE4 shl 3
        # ---- P 0x29E34..0x29E5C (Kp flat 112)
        P = np.clip(s32(Ep * KP) >> 8, -c["PCL"], c["PCL"])
        # ---- D: C3-P OPH (zxh Kd ; mov r26,r8 = op) | C3-F E5 (subr r0,r7 = -Kd ; ld.h -0x6a56,r8)
        Dp = s32(self.kd * op) >> 3
        Dh = s32(-self.kd * s16(x6a56)) >> 3
        D = np.clip(np.where(self.fresh, Dp, Dh), -DCL, DCL)
        # ---- sum, fade, sum clamp 0x29F18..0x2A162
        S = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fB = lerp_vec(*c["fadeB"], i682f)
        f = ((FA0 * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)                           # 0x2A190 (0 on skip ticks)
        # ---- output lag 0x2A174..0x2A1B0
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        # ---- sign-hold gate 0x2A198..0x2A1E4 (only while STEER_CONTROL_ACTIVE == 0)
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & blk, 0, yr)
        k = pol * c["fwd"]
        r11 = s32(yr * k) >> 15
        T = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), P=np.where(run, P, 0), D=np.where(run, D, 0),
                        frz=frz & run, farb=f_arb & ~f_hard & run, bound=bound, Ep=Ep, run=run)
        return s16(T)


# ------------------------------------------------------------------------------------------------------------------
# the frame (correction LERP) and the plant
# ------------------------------------------------------------------------------------------------------------------
class Frame:
    def __init__(self):
        c = AM.Cal("v295")
        k = c.k713a * c.k7432 / (8 * 256 * 16384)
        lin = np.array([x * 512 / 45 * k / 10.0 for x in c.X])
        cor = np.array(c.Y, float) / 10.0
        self.phi = np.linspace(0.0, 450.0, 90001)
        self.th = self.phi + np.interp(self.phi, lin, cor)
        self.kap = 1.0 + np.gradient(np.interp(self.phi, lin, cor), self.phi)
        assert np.all(np.diff(self.th) > 0)

    def kappa(self, th):
        return np.interp(np.abs(np.asarray(th, float)), self.th, self.kap)


FRAME = Frame()
_VG = np.round(np.arange(0.0, 40.0001, 0.05), 2)
_PLUT = {}


def plut(member):
    if member not in _PLUT:
        _PLUT[member] = np.array([NSP.params(member, v) for v in _VG], float)    # (nv, 7)
    return _PLUT[member]


def pparams(members, v):
    """per-column params at per-column speed v (linear interpolation on a 0.05 m/s grid; exact at the grid)."""
    v = np.asarray(v, float)
    out = np.zeros((len(members), 7))
    for m in set(members):
        idx = np.array([i for i, mm in enumerate(members) if mm == m])
        L = plut(m)
        for j in range(6):
            out[idx, j] = np.interp(v[idx], _VG, L[:, j])
        out[idx, 6] = L[0, 6]
    return out


class Plant:
    """Karnopp stick-slip rigid plant, 10 kHz sub-steps: J th'' + b th' + k sat tanh(th/sat) + friction = u + hand."""

    def __init__(self, members, v0):
        self.members = list(members)
        P = pparams(self.members, v0)
        self.set(P)
        B = len(members)
        self.th = np.zeros(B)
        self.om = np.zeros(B)
        self.tau = P[:, 6].astype(int)
        self.buf = np.zeros((int(self.tau.max()) + 1, B))
        self.n = 0

    def set(self, P):
        self.J, self.b, self.k, self.sat, self.Fc, self.Fs = (P[:, i] for i in range(6))

    def delay(self, T):
        L = self.buf.shape[0]
        self.buf[self.n % L] = T
        out = self.buf[(self.n - self.tau) % L, np.arange(len(T))]
        self.n += 1
        return out

    def step(self, u, hk=None, hb=None, hth=None, dt=1e-3, nsub=10):
        h = dt / nsub
        for _ in range(nsub):
            th, om = self.th, self.om
            net = u - self.k * self.sat * np.tanh(th / self.sat) - self.b * om
            if hk is not None:
                net = net + hk * (hth - th) - hb * om
            stuck = (om == 0.0) & (np.abs(net) <= self.Fs)
            fdir = np.where(om != 0.0, np.sign(om), np.sign(net))
            om_new = om + np.where(stuck, 0.0, (net - self.Fc * fdir) / self.J) * h
            om_new = np.where(stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om))), 0.0, om_new)
            self.om = om_new
            self.th = th + om_new * h


# ------------------------------------------------------------------------------------------------------------------
# scenario + runner
# ------------------------------------------------------------------------------------------------------------------
@dataclass
class Scn:
    dur: float
    ref: object                      # f(t) -> (B,) planned angle, deg (gp-0x6a00 frame)
    tq: object = None                # f(t, th, om, hand_force) -> (B,) SIGNED word gp-0x4f60
    hand: object = None              # f(t) -> None | (Kh, Bh, th_h) arrays
    uext: object = None              # f(t) -> (B,) external torque, T counts
    vel: object = None               # f(t) -> (B,) speed m/s (None = the column's constant v)
    events: tuple = ()
    mode0: str = "engaged"
    th0: object = None
    sp_meas_until: float = None
    sp_hold_from: float = None
    rec: bool = True


def run(cols, scn: Scn, seed=11, noise=2.8, frame="vgr"):
    """cols: list of dict(impl, member, v, age(0|10)).  Returns 1 kHz th/om/T/I/frz/farb, plan (100 Hz), wire."""
    B = len(cols)
    impls = [c["impl"] for c in cols]
    members = [c["member"] for c in cols]
    v0 = np.array([c["v"] for c in cols], float)
    aged = np.array([c.get("age", 0) == 10 for c in cols])
    lane = Lane(impls)
    pl = Plant(members, v0 if scn.vel is None else np.asarray(scn.vel(0.0), float) * np.ones(B))
    if scn.th0 is not None:
        pl.th = np.asarray(scn.th0, float) * np.ones(B)
    rng = np.random.default_rng(seed)
    nT = int(round(scn.dur * 1000))
    R = {k: np.zeros((nT, B), np.float32) for k in ("th", "om", "T", "I", "hf", "v")}
    R["frz"] = np.zeros((nT, B), bool)
    R["farb"] = np.zeros((nT, B), bool)
    plan_r = np.zeros((nT // 10 + 1, B), np.float32)
    wire = []
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    fifo = []
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    mode = scn.mode0
    ramp = np.full(B, 0x8000 if mode == "engaged" else 0, np.int64)
    act = req = 1 if mode == "engaged" else 0
    ev = sorted(scn.events)
    ei = 0
    sen = stopped = False
    plan_now = pl.th.copy()
    hforce = np.zeros(B)
    vnow = v0.copy()
    for n in range(nT):
        t = n * 1e-3
        if scn.vel is not None:
            vnow = np.asarray(scn.vel(t), float) * np.ones(B)
            if n % 10 == 0:
                pl.set(pparams(members, vnow))
        vw = np.round(vnow * 3.6 * 64).astype(np.int64)
        while ei < len(ev) and t >= ev[ei][0] - 1e-9:
            kind = ev[ei][1]
            if kind == "fault":
                sen, mode = True, "fault"
            elif kind == "stop":
                stopped = True
            elif kind == "dis":
                mode = "dis"
            elif kind in ("relatch", "engage"):
                mode = "relatch"
            ei += 1
        if mode == "engaged":
            ramp[:] = 0x8000
            act, req = 1, 1
        elif mode in ("fault", "dis"):
            ramp = np.maximum(0, ramp - 16)
            act, req = 0, (0xFF if mode == "fault" else 0)
        elif mode == "relatch":
            ramp = np.minimum(0x8000, ramp + 33)
            act, req = 1, 1
        elif mode == "off":
            ramp = np.maximum(0, ramp - 16)
            act, req = 0, 0
        if n % 10 == 0 and not sen and not stopped:
            k6 = max(len(wire) - 6, 0)
            th_meas = wire[k6] / 10.0 if wire else pl.th.copy()
            if mode in ("dis", "off") or (scn.sp_meas_until is not None and t < scn.sp_meas_until):
                plan_now = th_meas * np.ones(B)
                cmd = np.clip(-(s16(-np.floor(10.0 * th_meas + 0.5).astype(np.int64)) << 2), -0x4000, 0x4000)
            elif scn.sp_hold_from is not None and t >= scn.sp_hold_from:
                pass
            else:
                plan_now = np.asarray(scn.ref(t), float) * np.ones(B)
                raw = s16(-np.floor(10.0 * plan_now + 0.5).astype(np.int64))
                cmd = np.clip(s32(-(raw << 2)), -0x4000, 0x4000)
        cmd_in = np.full(B, SENT, np.int64) if sen else cmd
        tqv = np.zeros(B, np.int64) if scn.tq is None else np.round(
            np.asarray(scn.tq(t, pl.th, pl.om, hforce), float) * np.ones(B)).astype(np.int64)
        om_m = pl.om / FRAME.kappa(pl.th) if frame == "vgr" else pl.om
        g4f50 = s16(np.round(ABE_PER * om_m + rng.normal(0.0, noise, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = s16(st >> 10)
        T = lane.tick(held_th, abe, held_x, cmd_in, tqv, ramp, act, req, vw)
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
        u = -Tapp
        if scn.uext is not None:
            u = u + np.asarray(scn.uext(t), float)
        hh = scn.hand(t) if scn.hand is not None else None
        if hh is None:
            hforce = np.zeros(B)
            pl.step(u)
        else:
            hk, hb, hth = (np.asarray(a, float) * np.ones(B) for a in hh)
            hforce = hk * (hth - pl.th) - hb * pl.om                      # the hand's force before this step
            pl.step(u, hk, hb, hth)
        R["th"][n], R["om"][n], R["T"][n] = pl.th, pl.om, T
        R["I"][n], R["frz"][n], R["farb"][n] = lane.log["I"], lane.log["frz"], lane.log["farb"]
        R["hf"][n], R["v"][n] = hforce, vnow
        if n % 10 == 0:
            plan_r[n // 10] = plan_now
    R.update(plan=plan_r, wire=np.array(wire), wraps=lane.wraps)
    return R


# ------------------------------------------------------------------------------------------------------------------
# metric helpers (my own)
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


def dwell_jump(om_f, th_f, ref_f):
    """the record-style detector (same definition as the round-2 lens): dwell = 0.1 s moving mean |rate| < 0.25 deg/s
    for >= 10 frames while the reference moved >= 0.1 deg; event if the wheel then jumps >= max(2x the reference's
    change, 0.2 deg) before the next dwell (<= 0.5 s).  Returns events, max jump, and the event list (frame, jump)."""
    B = om_f.shape[1]
    ker = np.ones(10) / 10.0
    ev = np.zeros(B, int)
    jm = np.zeros(B)
    lst = [[] for _ in range(B)]
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
                lst[j].append((b, float(jump), float(rf[e] - rf[b])))
    return ev, jm, lst


def A_turn(v):
    AT = {3.0: 90.0, 5.0: 50.0, 8.0: 30.0, 12.5: 12.0, 19.0: 5.0, 26.0: 3.0, 30.0: 2.5}
    K = sorted(AT)
    return float(np.exp(np.interp(v, K, [np.log(AT[k]) for k in K])))


def tgt_alat(v, a, L=2.83, SR=16.0):
    return float(np.degrees(a * L * SR / v ** 2))
