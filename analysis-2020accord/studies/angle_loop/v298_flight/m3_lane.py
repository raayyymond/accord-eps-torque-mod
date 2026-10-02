# -*- coding: utf-8 -*-
r"""m3_lane.py -- the V298 lane on route 79's wire inputs, for M3 (integrator, freeze, driver-torque sensor).

ANALYSIS ONLY.  Reads the kit's v280 wire cache and the V298 image's cells; writes nothing; sends nothing.

WHAT IS EXACT AND WHAT IS NOT
  * Every memoryless stage (fb sum r26, E, E' = (E G) >> 8, the hard / opposing-hand / ramp freezes, the A3 bound, P, D,
    the fade f) is drive_read_fastlane.cand_lane's int64 numpy arithmetic, same order, same wraps (that function is
    proven bit-exact against score_time.CandLane, which is H1-validated against the cave by a V850E2 interpreter).
  * THE I RECURSION (the only state-dependent freeze: A3's angle-referenced bound, plus the ICL clamp) is solved here
    WITHOUT a per-tick Python loop: it is a cumsum between EVENTS (the first tick where the A3 stop or the ICL clamp
    bites); a stop holds I constant, so the next free tick is found by one vectorised search.  Integer-exact; validated
    word-for-word against the instrument's own cached replay (I at slot 4 of every frame) in m3_integrator_freeze.py.
  * The output path (fade, SCL clamp, the 0xC63EC/EE lag, x ramp, x -5346/32768, OCL) is run in FLOAT with
    scipy.signal.lfilter per marched block; the integer floors of the lag are dropped (<= ~0.3 T of bias; checked
    against the cached integer T).
  * The engage ramp: ramp(arm) picks the image's direction-0 cells (+33 / -16 per tick, what the instrument replays)
    or the direction-2 cells (+328 / -66 per tick, 0xC63FC / 0xC63FA, what V298 runs when the fork sends byte-2
    bits 3:2 = 2 -- TRACE-2026-09-30-dominance-preemption-timeout-version-and-6803 section 5).

UNITS / SIGNS (inherited from angle_loop_drive_read.wire_inputs, each re-checked in m3_integrator_freeze.py section 1):
  th  = gp-0x6a00 = round(10 * ang) (0.1 deg, carState sign, + = left)
  cmd = gp-0x69ae = clamp(-4 * raw) ; theta_sp = -raw/10 deg
  tq  = gp-0x4f60 = round(-bar), bar = 0x18F raw * 1.024 ; the 0x18F raw = -carState steeringTorque (route 79: equal
        on 99.3 % of frames at the 1-frame lag) => gp-0x4f60 = +carState torque * 1.024, + = the hand pushes left
  gp-0x4f68 = clamp(|gp-0x4f60|, 0, 65535) (GENTLE-EME gating map, Segment D: BELIEF inherited)
"""
from __future__ import annotations

import contextlib
import glob
import io
import os
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then the kit root and every code subfolder
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
HERE = Path(__file__).resolve().parent                      # .../analysis-2020accord/studies/angle_loop/v298_flight
KIT = HERE.parents[3]
AL = KIT / "analysis-2020accord" / "studies" / "angle_loop"
for _q in (KIT / "rlog-tools" / "studies" / "grind", KIT / "analysis-2020accord" / "studies" / "v280",
           KIT / "analysis-2020accord" / "lib", KIT / "rlog-tools" / "studies" / "angle_loop"):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))



class FL:
    """drive_read_fastlane's helpers, copied VERBATIM in effect (s16/s32/lerp_vec/_frame_ticks/ticked_frames) so this
    module does not depend on a file other sessions edit; the arithmetic is unchanged (validated word-for-word against
    the instrument's cached replay in m3_integrator_freeze.py)."""

    @staticmethod
    def s32(a):
        a = np.asarray(a, np.int64)
        return ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)

    @staticmethod
    def s16(a):
        a = np.asarray(a, np.int64)
        return ((a + (1 << 15)) & 0xFFFF) - (1 << 15)

    @staticmethod
    def lerp_vec(X, Y, u):
        X = np.asarray(X, np.int64)
        Y = np.asarray(Y, np.int64)
        u = np.asarray(u, np.int64)
        k = np.clip(np.searchsorted(X, u, side="right"), 1, len(X) - 1)
        x0, x1, y0, y1 = X[k - 1], X[k], Y[k - 1], Y[k]
        num = (y1 - y0) * (u - x0)
        den = x1 - x0
        q = np.abs(num) // np.abs(den)
        mid = y0 + np.where((num < 0) != (den < 0), -q, q)
        return np.where(u <= X[0], Y[0], np.where(u >= X[-1], Y[-1], mid))

    @staticmethod
    def ticked_frames(eng, r0, gap):
        e = np.asarray(eng, bool)
        k = np.arange(len(e), dtype=np.int64)
        last = np.maximum.accumulate(np.where(e, k, -10 ** 9))
        return ~((~e) & (r0 == 0) & (k - last > gap))

    @staticmethod
    def _frame_ticks(F, n, a, split):
        kp = np.maximum(F - 1, 0)
        out = np.empty((len(F), 10), np.int64)
        out[:, :split + 1] = a[kp][:, None]
        out[:, split + 1:] = a[F][:, None]
        return out

CACHE = KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280"
IMG_GLOB = os.path.join(os.environ["ACCORD_FIRMWARE_ROOT"], "analysis-2020accord", "_v298_*_plain_image.bin")
FS = 100.0
SENT32 = 0x7FFFFFFF


# =====================================================================================================================
# THE IMAGE (V298, read here, every load-bearing cell asserted)
# =====================================================================================================================
def image_cells():
    p = sorted(glob.glob(IMG_GLOB))
    assert len(p) == 1, p
    img = Path(p[0]).read_bytes()
    u16 = lambda a: struct.unpack_from("<H", img, a)[0]  # noqa: E731
    i16 = lambda a: struct.unpack_from("<h", img, a)[0]  # noqa: E731
    u32 = lambda a: struct.unpack_from("<I", img, a)[0]  # noqa: E731

    def rec(bank, n=6):                                      # selector 7 (nl_sim._cal's form)
        q = u32(bank + 4 * 7)
        return (np.array([u16(q + 2 + 2 * i) for i in range(n)], np.int64),
                np.array([u16(q + 2 + 2 * n + 2 * i) for i in range(n)], np.int64))
    c = dict(path=p[0], ki=u16(0xC63E6), icl=u16(0xC61BA), dcl=u16(0xC61B6), a=i16(0xC63E8), b=u16(0xC63EA),
             C=u16(0xC62E6), DB=u16(0xC62E4), PCL=u16(0xC61BC), SCL=u16(0xC61BE), OCL=u16(0xC61B4), oa=i16(0xC63EC),
             ob=u16(0xC63EE), dz=i16(0xC61B8), fwd=i16(0xC6CD0), kp=u16(0xE5384), kd=u16(0xE5126), g74a3=img[0xC64A3],
             ramp_in0=u16(0xC63F8), ramp_out0=u16(0xC63F6), ramp_in2=u16(0xC63FC), ramp_out2=u16(0xC63FA),
             fadeA=rec(0xCBC34), fadeB=rec(0xCBBC4), fadeB2=rec(0xCBAE4),
             rows=[(u16(0xC4CDA + 6 * k), u16(0xC4CDA + 6 * k + 2), i16(0xC4CDA + 6 * k + 4)) for k in range(7)],
             version=img[0x13100:0x1310E].decode("latin-1"))
    # the design's cells (build_v298_tva docstring section 0; DESIGN-ANGLE-LOOP-C3-rev2 1.3) -- asserted, not assumed
    assert (c["ki"], c["icl"], c["dcl"], c["kp"], c["kd"], c["a"], c["b"], c["C"], c["DB"]) == \
        (40, 8192, 10240, 112, 48, 0, 8192, 65535, 0), c
    assert (c["PCL"], c["SCL"], c["OCL"], c["oa"], c["ob"], c["fwd"]) == (15360, 15360, 3072, 992, 507, 5346), c
    assert c["rows"] == [(714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570),
                         (4032, 1068, 2118), (6198, 2188, 0), (65535, 2188, 0)], c["rows"]
    assert np.array_equal(c["fadeB"][0], c["fadeB2"][0]) and np.array_equal(c["fadeB"][1], c["fadeB2"][1])
    assert c["version"].endswith("A16A"), c["version"]
    return c


def glut(rows, vmax=12000):
    """nl_cave.walk_G for every speed word 0..vmax, vectorised: G + (s32((v - X_i) S_i) >> 12)."""
    X = np.array([r[0] for r in rows], np.int64)
    G = np.array([r[1] for r in rows], np.int64)
    S = np.array([r[2] for r in rows], np.int64)
    v = np.arange(vmax + 1, dtype=np.int64)
    i = np.searchsorted(X[1:], v, side="left")              # 'while v > X[i+1]: i += 1'
    i = np.minimum(i, len(X) - 2)
    out = FL.s32(G[i] + (FL.s32((v - X[i]) * S[i]) >> 12))
    return np.where(v <= X[0], G[0], out)


# =====================================================================================================================
# THE WIRE (the instrument's own grid: creep20_loop_id.load, = angle_loop_drive_read.load_route's frame axis)
# =====================================================================================================================
def load_wire(tag="r79_a1f5d2_al"):
    with contextlib.redirect_stdout(io.StringIO()):
        import creep20_loop_id as C20
    g = C20.load(tag)
    D = np.load(CACHE / (tag + ".npz"))
    W = dict(t=g["t"], ang=g["ang"], raw=np.round(g["cmd"]), req=g["req"] > 0.5, sca=g["sca"] > 0.5, bar=g["bar"],
             wire=g["wire"], vego=g["vego"], T_t=g["T_t"], T=g["T"], have=g["have18"])
    W["eng"] = W["req"] & W["sca"] & W["have"]
    j = np.clip(np.searchsorted(D["tcs"], W["t"], side="right") - 1, 0, len(D["tcs"]) - 1)
    W["pressed"] = D["cs_press"][j] > 0
    W["cs_tq"] = D["cs_tq"][j]
    W["theta"] = W["ang"]
    W["theta_sp"] = -W["raw"] / 10.0
    W["err"] = W["theta_sp"] - W["theta"]                   # deg, + = setpoint left of the wheel
    W["w18"] = -W["wire"] / 8.0                             # deg/s, sign of d(theta)/dt
    # time since the engage rising edge (vectorised; = angle_loop_drive_read.derive's tse)
    e = W["eng"]
    k = np.arange(len(e))
    start = np.maximum.accumulate(np.where(e & ~np.r_[False, e[:-1]], k, 0))
    W["tse"] = np.where(e, W["t"] - W["t"][start], -1.0)
    W["eid"] = np.where(e, np.cumsum(e & ~np.r_[False, e[:-1]]), 0)
    return W


def wire_inputs(W):
    """angle_loop_drive_read.wire_inputs, verbatim in effect."""
    th = np.round(10.0 * np.nan_to_num(W["ang"])).astype(np.int64)
    cmd = np.clip(-4 * np.round(np.nan_to_num(W["raw"])).astype(np.int64), -0x4000, 0x4000)
    tq = np.round(-np.nan_to_num(W["bar"])).astype(np.int64)
    x = np.round(-np.nan_to_num(W["wire"])).astype(np.int64)
    abe = np.round(-x * 32768.0 / (48 * 1159)).astype(np.int64)
    vws = np.clip(np.round(np.nan_to_num(W["vego"]) * 230.4), 0, 12000).astype(np.int64)
    return th, cmd, tq, x, abe, vws


# =====================================================================================================================
# THE ENGAGE RAMP -- per frame, vectorised over engaged / disengaged RUNS (no per-sample loop)
# =====================================================================================================================
def ramp_ticks(eng, up=33, dn=16):
    """-> (r0 (n,), R (n,10)): ramp at each frame start and after each of its 10 ticks (FL.ramp_ticks with the
    per-tick step a parameter).  dir-0 = (33, 16) [the instrument]; dir-2 = (328, 66) [V298 with arm 2]."""
    e = np.asarray(eng, bool)
    n = len(e)
    d = np.flatnonzero(np.diff(np.r_[-1, e.astype(int)]) != 0)          # run starts
    ends = np.r_[d[1:], n]
    r0 = np.zeros(n, np.int64)
    r = 0
    for a, b in zip(d, ends):                               # loop over RUNS (tens), not samples
        j = np.arange(b - a, dtype=np.int64)
        if e[a]:
            r0[a:b] = np.minimum(0x8000, r + 10 * up * j)
            r = int(min(0x8000, r + 10 * up * (b - a)))
        else:
            r0[a:b] = np.maximum(0, r - 10 * dn * j)
            r = int(max(0, r - 10 * dn * (b - a)))
    s1 = np.arange(1, 11, dtype=np.int64)
    R = np.where(e[:, None], np.minimum(0x8000, r0[:, None] + up * s1[None, :]),
                 np.maximum(0, r0[:, None] - dn * s1[None, :]))
    return r0, R


# =====================================================================================================================
# THE LANE'S MEMORYLESS TERMS (FL.cand_lane's numpy section, with the freeze terms kept separate)
# =====================================================================================================================
def shift_ticks(a, s):
    """a per-frame array held at 1 kHz (10 ticks per frame) and shifted by s ticks: s > 0 = tick j sees the value the
    100 Hz array holds at tick j + s (the firmware's word LEADS the wire sample)."""
    q = np.repeat(np.asarray(a), 10)
    if s > 0:
        q = np.r_[q[s:], np.repeat(q[-1:], s)]
    elif s < 0:
        q = np.r_[np.repeat(q[:1], -s), q[:s]]
    return q


def lane_terms(C, th, cmd, tq, x, abe, vws, eng, R, r0, gl, sgn_flip=False, q_shift=0):
    """q_shift: the torque word's timing vs the 0x18F frame, in 1 kHz ticks (0 = the instrument's convention: every
    tick of frame k sees frame k's 0x18F word)."""
    n = len(th)
    eng = np.asarray(eng, bool)
    tk = FL.ticked_frames(eng, r0, 100)
    F = np.flatnonzero(tk)
    m = len(F)
    kn = np.minimum(F + 1, n - 1)
    a6 = FL._frame_ticks(F, n, th, 4)
    ab = np.empty((m, 10), np.int64)
    ab[:, :9] = abe[F][:, None]
    ab[:, 9] = abe[kn]
    cm = np.broadcast_to(cmd[F][:, None], (m, 10))
    q = shift_ticks(tq, q_shift).reshape(n, 10)[F] if q_shift else np.broadcast_to(tq[F][:, None], (m, 10))
    vw = np.broadcast_to(np.clip(vws[F], 0, 12000)[:, None], (m, 10))
    ee = np.broadcast_to(eng[F][:, None], (m, 10))
    rr = R[F]
    a6, ab, cm, q, vw, ee, rr = (np.ascontiguousarray(v).ravel() for v in (a6, ab, cm, q, vw, ee, rr))
    xv = FL.s16(a6)
    valid = (xv >= -12000) & (xv <= 12000)
    s_new = FL.s32(FL.s32(xv * 8192) >> 10)
    s_old = np.zeros(len(xv), np.int64)
    s_old[1:] = np.where(valid[:-1], s_new[:-1], 0)
    r26 = np.where(valid, np.clip(FL.s32(s_old + s_new), -65535, 65535), 0)
    run = valid & (rr != 0) & ee
    E = FL.s32((FL.s16(cm) << 2) - r26)
    G = gl[vw]
    Ep = FL.s32(E * G) >> 8
    atq = np.minimum(np.abs(q), 0xFFFF)                     # gp-0x4f68
    hs = FL.s16(-q if sgn_flip else q)                      # gp-0x4f60 (sign-flipped only for the counterfactual)
    c1 = atq > 512                                          # hard freeze (cave 0xC4C5E..)
    c2 = (np.abs(hs) > 300) & ((hs ^ Ep) < 0) & ~c1         # opposing-hand freeze (only reached if not c1)
    c4 = ((rr & 0x8000) == 0)                               # ramp not full
    th6 = FL.s16(a6)
    vwm = vw & 0xFFFF
    sh = np.where(vwm <= 2880, 4, 6)
    bound = FL.s32((np.abs(th6) << sh) + 1250)
    bound = np.where((vwm <= 1382) & (bound > 4096), 4096, bound)
    e5 = Ep >> 5
    inc = FL.s32(e5 * C["ki"]) >> 3
    inc_exact = Ep * C["ki"] / 256.0                        # the same increment with no sar-5 / sar-3 floor
    P = np.clip(FL.s32(Ep * C["kp"]) >> 8, -C["PCL"], C["PCL"])
    ab16 = FL.s16(ab)
    abv = ((ab16 + 13000) & 0xFFFFFFFF) <= 26000
    D = np.clip(FL.s32(C["kd"] * np.where(abv, ab16, 0)) >> 3, -C["dcl"], C["dcl"])
    i682f = np.minimum(np.abs(q >> 5), 255)
    fA1 = int(FL.lerp_vec(*C["fadeA"], np.zeros(1, np.int64))[0])
    f = ((fA1 * FL.lerp_vec(*C["fadeB"], i682f)) & 0xFFFF) >> 8
    rs = np.zeros((m, 10), bool)
    rs[1:, 0] = np.diff(F) > 1
    rs[0, 0] = True
    return dict(F=F, m=m, run=run, E=E, Ep=Ep, G=G, c1=c1, c2=c2, c4=c4, bound=bound, inc=inc, inc_exact=inc_exact,
                P=P, D=D, f=f, rr=rr, ee=ee, rs=rs.ravel(), atq=atq, hs=hs, th6=th6, cm=cm, r26=r26)


# =====================================================================================================================
# THE I RECURSION -- integer-exact, event-driven, vectorised
# =====================================================================================================================
def i_recursion(L, freeze, a3=True, icl_s=None, window=8192):
    """I after every marched tick (int64).  freeze: the static freeze mask (bool per tick).
    Per tick (FL.cand_lane): if freeze or (a3 and dir(I >> 7) >= bound): I unchanged else I = clamp(I + inc, +-icl);
    I := 0 on every tick the PID does not run and at every frame-skip reset.
    Returns (I_after, a3_stop (A3 bound held a non-zero step), clamp (ICL bit), n_events)."""
    C_icl = ((icl_s & 0xFFFF) << 10) >> 3
    run, rs = L["run"], L["rs"]
    steps_all = np.where(freeze, 0, L["inc"])
    sg_all = L["Ep"] >= 0
    bnd_all = L["bound"]
    N = len(run)
    Iout = np.zeros(N, np.int64)
    a3s = np.zeros(N, bool)
    clp = np.zeros(N, bool)
    # segments: maximal blocks of run ticks with no reset inside
    st = run & (rs | ~np.r_[False, run[:-1]])
    starts = np.flatnonzero(st)
    ends = np.empty_like(starts)
    nr = np.flatnonzero(~run)
    for i, s in enumerate(starts):
        j = np.searchsorted(nr, s)
        e_ = nr[j] if j < len(nr) else N
        if i + 1 < len(starts):
            e_ = min(e_, starts[i + 1])
        ends[i] = e_
    nev = 0

    def stopmask(Ib, sl):
        qv = Ib >> 7
        return np.where(sg_all[sl], qv >= bnd_all[sl], -qv >= bnd_all[sl]) if a3 else np.zeros(len(Ib), bool)

    for s, e_ in zip(starts, ends):
        I = 0
        t = s
        while t < e_:
            w = min(e_, t + window)
            sl = slice(t, w)
            stp = steps_all[sl]
            cs = np.cumsum(stp)
            Ib = I + np.r_[0, cs[:-1]]
            stop = stopmask(Ib, sl) & (stp != 0)
            Ia = Ib + stp
            cl = (Ia > C_icl) | (Ia < -C_icl)
            ev = stop | cl
            if not ev.any():
                Iout[sl] = Ia
                I = int(Ia[-1])
                t = w
                continue
            k = int(np.argmax(ev))
            nev += 1
            Iout[t:t + k] = Ia[:k]
            if stop[k]:
                Ik = int(Ib[k])
                h0 = t + k
                w2 = min(e_, h0 + window)
                sl2 = slice(h0, w2)
                stp2 = steps_all[sl2]
                s2 = stopmask(np.full(w2 - h0, Ik, np.int64), sl2) & (stp2 != 0)
                free = (~s2) & (stp2 != 0)
                j = int(np.argmax(free)) if free.any() else (w2 - h0)
                Iout[h0:h0 + j] = Ik
                a3s[h0:h0 + j] = s2[:j]
                I = Ik
                t = h0 + j
            else:
                Ic = C_icl if Ia[k] > C_icl else -C_icl
                Iout[t + k] = Ic
                clp[t + k] = True
                # ride the clamp: I stays at +-icl until a step of the opposite sign
                h0 = t + k + 1
                w2 = min(e_, h0 + window)
                stp2 = steps_all[h0:w2]
                rel = (stp2 * np.sign(Ic)) < 0
                j = int(np.argmax(rel)) if rel.any() else (w2 - h0)
                Iout[h0:h0 + j] = Ic
                clp[h0:h0 + j] = (stp2[:j] != 0)
                I = Ic
                t = h0 + j
    return Iout, a3s, clp, nev


# =====================================================================================================================
# THE OUTPUT PATH (float lag per marched block) -> T at slot 4 per frame
# =====================================================================================================================
def output_T(C, L, I_after, n, comp=None):
    """T (n,) float at slot 4 of each frame.  comp=None: the full S; comp='P'|'D'|'I': that component alone carried
    through the same (linear) fade / lag / ramp chain, the SCL clamp dropped (components() convention)."""
    run, f, rr, F, m = L["run"], L["f"], L["rr"], L["F"], L["m"]
    Ish = I_after >> 7
    if comp is None:
        S = np.where(run, np.clip((((Ish + L["P"] + L["D"]) * f) >> 8), -C["SCL"], C["SCL"]), 0).astype(float)
    else:
        z = dict(P=L["P"], D=L["D"], I=Ish)[comp].astype(float)
        S = np.where(run, z * f / 256.0, 0.0)
    out = np.zeros(m * 10)
    blk = np.flatnonzero(L["rs"])
    blk_e = np.r_[blk[1:], m * 10]
    for a, b in zip(blk, blk_e):                            # blocks = contiguous marched frames (a few dozen)
        o = lfilter([C["ob"] / 1024.0], [1.0, -C["oa"] / 1024.0], S[a:b])
        out[a:b] = (np.r_[0.0, o[:-1]] + o) / 32.0
    yr = out * rr / 32768.0
    T = -yr * C["fwd"] / 32768.0
    if comp is None:
        T = np.clip(T, -C["OCL"], C["OCL"])
    Tn = np.zeros(n)
    Tn[F] = T.reshape(m, 10)[:, 4]
    return Tn


def slot4(L, a, n, fill=0):
    out = np.full(n, fill, dtype=np.asarray(a).dtype)
    out[L["F"]] = np.asarray(a).reshape(L["m"], 10)[:, 4]
    return out


def per_frame_frac(L, mask, n):
    """fraction of the 10 ticks of each frame where mask holds (0 on unmarched frames)."""
    out = np.zeros(n)
    out[L["F"]] = np.asarray(mask, float).reshape(L["m"], 10).mean(1)
    return out
