# -*- coding: utf-8 -*-
r"""drive_read_fastlane.py -- the 1 kHz lane REPLAYS of angle_loop_drive_read.py, made fast and kept INTEGER-EXACT.

ANALYSIS ONLY (offline, on cached wire arrays).  Sends nothing, flashes nothing.

WHY: the drive read replayed six candidate images at 1 kHz over a whole route through score_time.CandLane.tick (a
numpy call per instruction, ~100 calls per tick, vectorised over only five columns) and lane_mirror_v295.lane_tick
(pure Python with LERP walks per tick).  On a 1224 s route that was ~10 minutes.

HOW (no arithmetic changes -- the same integer operations, the same order, the same timing convention):
  1. Every MEMORYLESS stage (the fb operand, E, E' = (E G) >> 8, the static freeze tests, P, D, the fade f, the
     setpoint chain, the A3 bound) is computed for ALL ticks at once in int64 numpy, with the same s16/s32 wraps as
     the source (score_time.CandLane.cave_stage/tick ; lane_mirror_v295.lane_tick / setpoint_chain).
  2. Only the RECURSIONS (the I integrator with its clamp and its state-dependent A3 freeze, the output-lag pole,
     the sign-hold gate's T_prev, and V295's fb pole) run in a scalar Python-int loop -- one loop per image, with
     no numpy call inside it.  Python ints are exact; every product in the loop is bounded below 2^31 by the
     image's own constants, ASSERTED at run time (_bounds), so the s32/s16 wraps the source applies are identities
     there.  If a cal ever moved outside those bounds the assertion fires; nothing silently changes.
  3. The tick schedule (which frames are marched, the ramp at each tick, the skip resets) is the source's own,
     computed once per frame.

PROOF OF EQUALITY (EVIDENCE, 2026-10-02, route 79 = r79_a1f5d2_al, 1224 s):
  * the pre-optimisation drive read's own _replay_cand (5 candidates, T and the I log), _replay_v295 and
    components() were run on the whole route and saved; this module's outputs differ in ZERO words / bits;
  * verify_against_source() re-runs that comparison on any W (a window from its first engagement) -- 0 on r79;
  * angle_loop_drive_read's drive_read.txt is byte-identical (bar the added RUNTIME line) and drive_read.json is
    byte-identical to the pre-optimisation reference output.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

SENT32 = 0x7FFFFFFF
VERSION = "fastlane-1"          # bump whenever the arithmetic here changes (it keys the per-route replay cache)


def s32(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def s16(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 15)) & 0xFFFF) - (1 << 15)


def lerp_vec(X, Y, u):
    """nl_sim.lerp_vec / lane_mirror_v295.lerp (Honda's integer LERP walk), vectorised."""
    X = np.asarray(X, np.int64)
    Y = np.asarray(Y, np.int64)
    u = np.asarray(u, np.int64)
    n = len(X)
    k = np.clip(np.searchsorted(X, u, side="right"), 1, n - 1)
    x0, x1, y0, y1 = X[k - 1], X[k], Y[k - 1], Y[k]
    num = (y1 - y0) * (u - x0)
    den = x1 - x0
    q = np.abs(num) // np.abs(den)
    mid = y0 + np.where((num < 0) != (den < 0), -q, q)
    return np.where(u <= X[0], Y[0], np.where(u >= X[-1], Y[-1], mid))


# =====================================================================================================================
# THE TICK SCHEDULE (angle_loop_drive_read._replay_cand / _replay_v295 / components, verbatim in effect)
# =====================================================================================================================
def ramp_ticks(eng, up=33, dn=16):
    """ramp after each of the 10 engage-SM updates of every frame: +up capped at 0x8000 while engaged, -dn floored at
    0 otherwise.  A frame the replay SKIPS has ramp 0 and is not engaged, so the march is identical whether or not it
    is skipped (the source's components() marches every tick; _replay_cand skips) -> one schedule serves both.
    (up, dn) = the per-tick steps: (33, 16) = the direction-0 cells 0xC63F8 / 0xC63F6 (the default; every replay before
    2026-10-02 used it); (328, 66) = the direction-2 cells 0xC63FC / 0xC63FA, what V298 runs while the fork sends 0xE4
    byte-2 bits 3:2 = 2 (M1-attribution-identity.md section 6.1, M3-integrator-freeze.md section 0).  The defaults keep
    the arithmetic, and so VERSION and every cached replay, unchanged."""
    e = np.asarray(eng, bool)
    n = len(e)
    r0 = np.zeros(n, np.int64)
    r = 0
    el = e.tolist()
    for k in range(n):                    # frame-level only (n = 100 Hz frames); the 10 ticks are closed-form below
        r0[k] = r
        r = min(0x8000, r + 10 * up) if el[k] else max(0, r - 10 * dn)
    s1 = np.arange(1, 11, dtype=np.int64)
    Ru = np.minimum(0x8000, r0[:, None] + up * s1[None, :])
    Rd = np.maximum(0, r0[:, None] - dn * s1[None, :])
    R = np.where(e[:, None], Ru, Rd)
    return r0, R


def ticked_frames(eng, r0, gap):
    """a frame is marched unless (not engaged) and ramp == 0 at its start and it is more than <gap> frames after the
    last engaged frame (100 for the candidate lanes, 300 for V295)."""
    e = np.asarray(eng, bool)
    k = np.arange(len(e), dtype=np.int64)
    last = np.maximum.accumulate(np.where(e, k, -10 ** 9))
    skip = (~e) & (r0 == 0) & (k - last > gap)
    return ~skip


def _frame_ticks(F, n, a, split):
    """(m, 10) per-tick view of a per-frame array: ticks 0..split see frame k-1 (clamped at 0), the rest frame k."""
    kp = np.maximum(F - 1, 0)
    out = np.empty((len(F), 10), np.int64)
    out[:, :split + 1] = a[kp][:, None]
    out[:, split + 1:] = a[F][:, None]
    return out


# =====================================================================================================================
# THE CANDIDATE LANE (score_time.CandLane with ONE column) -- the supported cave features only
# =====================================================================================================================
def cand_params(c):
    """the Cand fields the fast lane implements; anything else -> NotImplementedError (fall back to the source)."""
    unsupported = []
    if c.dop not in ("fresh", "held"):
        unsupported.append("dop=%s" % c.dop)
    if c.icl_rows:
        unsupported.append("icl_rows")
    if c.reset_firm is not None:
        unsupported.append("reset_firm")
    if c.eb_lo is not None:
        unsupported.append("eb_lo")
    if c.leak_s:
        unsupported.append("leak_s")
    if c.hb_sh:
        unsupported.append("hb_sh")
    if c.fb69:
        unsupported.append("fb69")
    if c.fade2:
        unsupported.append("fade2")
    if unsupported:
        raise NotImplementedError("fast lane: %s" % ",".join(unsupported))
    return dict(id=c.id, rows=[list(r) for r in c.rows], dop={"fresh": 0, "held": 1}[c.dop], kd=int(c.kd),
                kp=int(c.kp), ki=int(c.ki), icl=int(c.icl), thr=int(c.thr), ramp_frz=bool(c.ramp_frz),
                sgn=int(c.sgn_thr), arb=(list(c.arb) if c.arb is not None else None))


# ---- the cave's integral policy (the freeze tests and the A3 bound), shared by cand_lane and the V299 checks ----------
ARB_V299 = (6, 4, 2880, 1250, 2880, 6144, 1, 1382, 4096)
"""V299 rev 2/3 (DESIGN-V299-SYNTHESIS-rev3 section 1.3, cave_rev2; H1: the rev-2 BYTES == that mirror):
(sh, sh_lo, vth, B, vcap, cap, asym, vcap_lo, cap_lo) = bound S = (max(theta*sgn(E'), 0) << (4 if v <= 2880 else 6))
+ 1250, capped at 4096 when v-word <= 1382 and at 6144 when 1382 < v <= 2880 (no cap above 2880).  The 6-tuple forms
(ARB_A2, ARB_A3 = V298) keep |theta| and one cap, unchanged.  With thr 1229 and sgn 0 (no opposing clause)."""


def static_freeze(p, q, Ep, rr):
    """the cave's memoryless freezes: |gp-0x4f68| > thr (V298 512, V299 1229 = Honda steeringPressed), the opposing-
    hand clause |gp-0x4f60| > sgn with sign != sign(E') (V298 300, V299 none), and the ramp-in freeze."""
    q = np.asarray(q, np.int64)
    atq = np.minimum(np.abs(q), 0xFFFF)
    c1 = atq > p["thr"]
    hs = s16(q)
    c2 = (p["sgn"] > 0) & (np.abs(hs) > p["sgn"]) & ((hs ^ Ep) < 0)
    c4 = (p["ramp_frz"] & ((np.asarray(rr) & 0x8000) == 0)) if p["ramp_frz"] else np.zeros(len(q), bool)
    return c1 | c2 | c4


def arb_bound(arb, a6, vwm, Ep):
    """the A3 bound in S units (= I8 >> 10), integer-exact.  6-tuple: V298 (|theta|, one cap at v <= vcap).
    9-tuple: V299 (asym: max(theta*sgn(E'), 0); two-level cap: cap_lo at v <= vcap_lo, cap at vcap_lo < v <= vcap)."""
    sh, sh_lo, vth, Bb, vcap, cap = arb[:6]
    th6 = s16(a6)
    vwm = np.asarray(vwm, np.int64)
    shv = np.where((sh_lo >= 0) & (vwm <= vth), sh_lo, sh)
    if len(arb) == 6:
        base = np.abs(th6)
        capv = cap
    else:
        asym, vcap_lo, cap_lo = arb[6:9]
        base = np.maximum(np.where(np.asarray(Ep) < 0, -th6, th6), 0) if asym else np.abs(th6)
        capv = np.where(vwm <= vcap_lo, cap_lo, cap)
    bound = s32((base << shv) + Bb)
    capon = (vcap >= 0) & (vwm <= vcap)
    return np.where(capon & (bound > capv), capv, bound)


def v299_cand(ST, base):
    """V299 = V298's lane (base = the drive read's C3B-P: GB-P rows, fresh D, Kd 48, Ki 40, ICL 8192) with the V299
    integral policy: hard freeze 1229, no opposing clause, ARB_V299.  The source lane (score_time.CandLane) does not
    implement the 9-tuple, so this candidate exists only in the fast lane (cand_params never falls back for it)."""
    import dataclasses
    return dataclasses.replace(base, id="V299", thr=1229, sgn_thr=0, arb=ARB_V299, note="V299 rev 2/3 integral policy")


def _bounds(cal, kp=112, ki=56, kd=48, DCL=10240):
    """the loop's no-wrap guarantees, from the image's own constants (see the module docstring)."""
    SCL, ob, oa, fwd, OCL, PCL = cal["SCL"], cal["ob"], cal["oa"], cal["fwd"], cal["OCL"], cal["PCL"]
    assert 0 < SCL < 0x8000 and 0 < OCL < 0x8000 and 0 <= ob < 0x10000 and 0 < oa < 1024, cal
    t1max = (SCL * ob >> 10) + 1
    omax = t1max * 1024 // (1024 - oa) + 2 * 1024 // (1024 - oa) + 2      # the floor adds at most 1 per tick
    ymax = (2 * omax >> 5) + 1
    assert SCL * ob < 2 ** 31 and oa * omax < 2 ** 31, (SCL, ob, oa, omax)
    assert ymax * 0x8000 < 2 ** 31 and ymax < 0x8000 and ymax * ymax < 2 ** 31, ymax
    assert ymax * abs(fwd) < 2 ** 31 and abs(cal["dz"]) < 0x8000
    return dict(ymax=ymax, omax=omax)


def cand_lane(p, glut, cal, th, cmd, tq, x, abe, vws, eng, R, r0, rec_I=False):
    """-> T (n,) int64 at slot 4 of every frame (0 on skipped frames) [, I log (n,) = I >> 7 when the lane ran].
    Bit-exact against angle_loop_drive_read._replay_cand(ST, [cand], ...) (column 0)."""
    n = len(th)
    eng = np.asarray(eng, bool)
    tk = ticked_frames(eng, r0, 100)
    F = np.flatnonzero(tk)
    m = len(F)
    out_T = np.zeros(n, np.int64)
    out_I = np.zeros(n, np.int64) if rec_I else None
    if m == 0:
        return (out_T, out_I) if rec_I else out_T
    kn = np.minimum(F + 1, n - 1)
    # ---- per-tick inputs (the source's slot-4 timing convention)
    a6 = _frame_ticks(F, n, th, 4)                          # gp-0x6a00: ticks 0..4 see frame k-1
    xx = _frame_ticks(F, n, x, 4)                           # gp-0x6a56 (held rate), same
    ab = np.empty((m, 10), np.int64)
    ab[:, :9] = abe[F][:, None]                             # gp-0x6abe: ticks 0..8 frame k, tick 9 frame k+1
    ab[:, 9] = abe[kn]
    cm = np.broadcast_to(cmd[F][:, None], (m, 10))
    q = np.broadcast_to(tq[F][:, None], (m, 10))
    vw = np.broadcast_to(np.clip(vws[F], 0, 12000)[:, None], (m, 10))
    ee = np.broadcast_to(eng[F][:, None], (m, 10))
    rr = R[F]
    a6, xx, ab, cm, q, vw, ee, rr = (np.ascontiguousarray(v).ravel() for v in (a6, xx, ab, cm, q, vw, ee, rr))
    # ---- fb filter 0x28F4C..0x28FBE (E1 x := gp-0x6a00, E2 add, a 0 b 8192 C 65535): s_old is the previous MARCHED
    #      tick's s if that tick was valid (lane_ok == 1), else 0; the lane's s / lane_ok survive the skipped frames
    xv = s16(a6)
    valid = (xv >= -12000) & (xv <= 12000)
    s_new = s32((0 * 0 >> 10) + (s32(xv * 8192) >> 10))
    s_old = np.zeros(len(xv), np.int64)
    s_old[1:] = np.where(valid[:-1], s_new[:-1], 0)
    r26 = np.clip(s32(s_old + s_new), -65535, 65535)
    r26 = np.where(valid, r26, 0)
    run = valid & (rr != 0) & ee
    # ---- the cave (cave_stage) -- every memoryless term
    sp = s16(cm)
    E = s32((sp << 2) - r26)
    G = np.asarray(glut, np.int64)[vw]
    Ep = s32(E * G) >> 8
    fs = static_freeze(p, q, Ep, rr)
    arb_on = p["arb"] is not None
    if arb_on:
        bound = arb_bound(p["arb"], a6, vw & 0xFFFF, Ep)
    else:
        bound = np.zeros(len(rr), np.int64)
    e5 = Ep >> 5                                            # DB 0: exc = e5
    inc = s32(e5 * p["ki"]) >> 3
    P = np.clip(s32(Ep * p["kp"]) >> 8, -cal["PCL"], cal["PCL"])
    DCL = 10240
    if p["dop"] == 0:
        ab16 = s16(ab)
        abv = ((ab16 + 13000) & 0xFFFFFFFF) <= 26000
        op = np.where(abv, ab16, 0)
        D = np.clip(s32(p["kd"] * op) >> 3, -DCL, DCL)
    else:
        D = np.clip(s32(-p["kd"] * s16(xx)) >> 3, -DCL, DCL)
    i682f = np.minimum(np.abs(q >> 5), 255)
    fA1 = int(lerp_vec(*cal["fadeA"], np.zeros(1, np.int64))[0])
    fB = lerp_vec(*cal["fadeB"], i682f)
    f = ((fA1 * fB) & 0xFFFF) >> 8
    PD = P + D
    icl = ((p["icl"] & 0xFFFF) << 10) >> 3
    # no-wrap guarantees for the scalar loop (all wraps the source applies are identities inside these bounds)
    _bounds(cal)
    assert icl < 2 ** 24 and int(np.max(np.abs(inc), initial=0)) < 2 ** 28
    assert int(np.max(np.abs(PD), initial=0)) + (icl >> 7) < 2 ** 22 and int(np.max(f, initial=0)) < 256
    # ---- frame resets: a skipped frame sets I8 = 0, Eprev = sentinel, olag = 0, Tprev = 0
    rs = np.zeros((m, 10), bool)
    rs[1:, 0] = np.diff(F) > 1
    rs = rs.ravel()
    sgnp = Ep >= 0
    # ---- THE RECURSION (scalar, exact)
    SCL, ob, oa, OCL, dz = int(cal["SCL"]), int(cal["ob"]), int(cal["oa"]), int(cal["OCL"]), int(cal["dz"])
    kk = -int(cal["fwd"])                                   # pol -1
    gate = int(cal["g74a3"]) == 1
    T4 = [0] * m
    I4 = [0] * m
    I = olag = Tprev = 0
    L = zip(rs.tolist(), fs.tolist(), sgnp.tolist(), bound.tolist(), inc.tolist(), PD.tolist(), f.tolist(),
            run.tolist(), rr.tolist(), ee.tolist())
    j = 0
    s = 0
    for r_, fz, sg, bd, ic, pd, ff, rn, rp, ac in L:
        if r_:
            I = olag = Tprev = 0
        if fz or (arb_on and ((I >> 7) if sg else -(I >> 7)) >= bd):
            In = I
        else:
            In = I + ic
            if In > icl:
                In = icl
            elif In < -icl:
                In = -icl
        if rn:
            Sf = (((In >> 7) + pd) * ff) >> 8
            Sc = SCL if Sf > SCL else (-SCL if Sf < -SCL else Sf)
            I = In
        else:
            Sc = 0
            I = 0
        o_new = ((Sc * ob) >> 10) + ((oa * olag) >> 10)
        y = (olag + o_new) >> 5
        olag = o_new
        if gate and not ac and ((y <= dz and y >= -dz) or y * Tprev <= 0):
            yr = 0
        else:
            yr = (y * rp) >> 15
        T = (yr * kk) >> 15
        Tprev = yr
        if s == 4:
            T4[j] = OCL if T > OCL else (-OCL if T < -OCL else T)
            I4[j] = (I >> 7) if rn else 0
        s += 1
        if s == 10:
            s = 0
            j += 1
    out_T[F] = T4
    if rec_I:
        out_I[F] = I4
        return out_T, out_I
    return out_T


# =====================================================================================================================
# V295 (lane_mirror_v295.lane_tick with the default Edits, pol -1) -- the drive read's _replay_v295
# =====================================================================================================================
def setpoint_vec(cmd69ae, tq, speed, cal):
    """lane_mirror_v295.setpoint_chain (i6830 0, sel6803 0), vectorised -> (idx, sp)."""
    r13 = s16(cmd69ae)
    LIM = lerp_vec(*cal["lim"], speed) & 0xFFFF
    r22 = np.where(r13 < -LIM, -LIM, np.where(r13 > LIM, LIM, r13))
    tq = np.asarray(tq, np.int64)
    i682f = np.minimum(np.abs(tq >> 5), 255)
    same = (r22 < 0) == (tq < 0)
    taper = np.where(same, lerp_vec(*cal["tap_same"], i682f), lerp_vec(*cal["tap_opp"], i682f))
    spF = int(lerp_vec(*cal["spF"], np.zeros(1, np.int64))[0])
    Gs = (spF * taper) & 0xFFFF
    v = s32(Gs * r22) >> 16
    v = np.where(i682f > cal["cut"], 0, v)
    v = v >> 6
    sign = np.where(v < 0, -1, 1)
    v = np.clip(v, -cal["idx_lo"], cal["idx_hi"])
    idx = np.abs(v)
    Y = lerp_vec(*cal["map"], idx & 0xFF)
    sp = s32(s16(sign) * s16(Y))
    return idx, sp


def v295_lane(cal, th, cmd, tq, x, vws, eng, R, r0):
    """-> T (n,) int64 at slot 4 (0 on skipped frames).  Bit-exact against angle_loop_drive_read._replay_v295."""
    n = len(th)
    eng = np.asarray(eng, bool)
    tk = ticked_frames(eng, r0, 300)
    F = np.flatnonzero(tk)
    m = len(F)
    out_T = np.zeros(n, np.int64)
    if m == 0:
        return out_T
    # ---- per FRAME: the setpoint chain, kp, kd, the fade (each depends only on cmd / tq / speed)
    idx, sp = setpoint_vec(cmd[F], tq[F], vws[F], cal)
    kp = lerp_vec(*cal["kp"], idx & 0xFFFF) & 0xFFFF
    kd = lerp_vec(*cal["kd"], idx & 0xFF) & 0xFFFF
    i682f = np.minimum(np.abs(tq[F] >> 5), 255)
    A = int(lerp_vec(*cal["fadeA"], np.zeros(1, np.int64))[0])
    B = lerp_vec(*cal["fadeB"], i682f)
    f = ((A * B) & 0xFFFF) >> 8
    sp4 = sp << 2                                           # e_shift 2 (V294/V295)
    # ---- per TICK: the rate operand (ticks 0..4 see frame k-1), its validity and x*b >> 10
    xr = s16(_frame_ticks(F, n, x, 4).ravel())
    valid = (xr >= -12000) & (xr <= 12000)
    bxs = s32(xr * (cal["b"] & 0xFFFF)) >> 10
    rr = R[F].ravel()
    a = int(s16(cal["a"]))
    C = int(cal["C"] & 0xFFFF)
    DB = int(cal["DB"] & 0xFFFF)
    Ki = int(cal["Ki"] & 0xFFFF)
    icl = ((cal["ICL"] & 0xFFFF) << 10) >> 3
    PCL, DCL = int(cal["PCL"]), int(cal["DCL"])
    SCL = int(cal["SCL"] & 0xFFFF)
    ob, oa, OCL, dz = int(cal["ob"] & 0xFFFF), int(s16(cal["oa"])), int(cal["OCL"] & 0xFFFF), int(cal["dz"])
    kk = int(s32(-1 * int(s16(cal["fwd"]))))
    gate = int(cal["g74a3"]) == 1
    _bounds(dict(SCL=SCL, ob=ob, oa=oa, fwd=cal["fwd"], OCL=OCL, PCL=PCL, dz=dz))
    assert SCL == int(s16(SCL)) and OCL == int(s16(OCL)) and dz == (cal["dz"] & 0xFFFF)
    assert int(np.max(np.abs(sp4), initial=0)) + C < 2 ** 20 and int(np.max(kp, initial=0)) < 2 ** 16
    sp4l, kpl, kdl, fl, el = sp4.tolist(), kp.tolist(), kd.tolist(), f.tolist(), eng[F].tolist()
    vl, bl, rl = valid.tolist(), bxs.tolist(), rr.tolist()
    T4 = [0] * m
    s_ = lane_ok = I8 = olag = Tprev = 0
    Eprev = 0
    t = 0
    for j in range(m):
        spj, kpj, kdj, fj, e = sp4l[j], kpl[j], kdl[j], fl[j], el[j]
        for s in range(10):
            ok = vl[t]
            rp = rl[t]
            if ok:
                s_old = s_ if lane_ok == 1 else 0
                as_ = a * s_old
                as_ = ((as_ + 0x80000000) & 0xFFFFFFFF) - 0x80000000
                s_new = (as_ >> 10) + bl[t]
                s_new = ((s_new + 0x80000000) & 0xFFFFFFFF) - 0x80000000
                r26 = s_new - s_old
                r26 = ((r26 + 0x80000000) & 0xFFFFFFFF) - 0x80000000
                s_ = s_new
                r26 = -C if r26 < -C else (C if r26 > C else r26)
                lane_ok = 1
            else:
                r26 = 0
                lane_ok = 2
            if ok and (rp != 0 or e):
                E = spj - r26
                e5 = E >> 5
                exc = e5 - DB if e5 > DB else (e5 + DB if e5 < -DB else 0)
                Iv = (I8 >> 3) + ((exc * Ki) >> 3)
                Iv = -icl if Iv < -icl else (icl if Iv > icl else Iv)
                I8n = Iv << 3
                P = (E * kpj) >> 8
                P = -PCL if P < -PCL else (PCL if P > PCL else P)
                r27 = Eprev if -768000 <= Eprev <= 768000 else E
                D = (kdj * (E - r27)) >> 3
                D = -DCL if D < -DCL else (DCL if D > DCL else D)
                Sf = (((Iv >> 7) + P + D) * fj) >> 8
                Sc = SCL if Sf > SCL else (-SCL if Sf < -SCL else Sf)
                I8 = I8n
                Eprev = E
            else:
                Sc = 0
                I8 = 0
                Eprev = SENT32
            o_new = ((Sc * ob) >> 10) + ((oa * olag) >> 10)
            y = (olag + o_new) >> 5
            olag = o_new
            if gate and not e and ((y <= dz and y >= -dz) or y * Tprev <= 0):
                yr = 0
            else:
                yr = (y * rp) >> 15
            T = (yr * kk) >> 15
            Tprev = yr
            if s == 4:
                T4[j] = OCL if T > OCL else (-OCL if T < -OCL else T)
            t += 1
    out_T[F] = T4
    return out_T


# =====================================================================================================================
# THE EQUALITY CHECK AGAINST THE SOURCE LANES
# =====================================================================================================================
def verify_against_source(D, W, max_s=120.0, cands=("C3B-P", "C3-P56", "SKIP", "C3B-P-kd34", "C3B-F")):
    """march the SOURCE lanes (D._replay_cand_source = score_time.CandLane, D._replay_v295_source =
    lane_mirror_v295.lane_tick) on <max_s> seconds of W from just before its first engagement and compare every
    output word (T, and the I log) with this module's lanes.  D = the angle_loop_drive_read module.  -> n differing
    words (0 = equal)."""
    import lane_mirror_v295 as LM
    import nl_sim as NS
    ST = D.load_score_time()
    C = D.replay_cands(ST)
    eng = np.asarray(W["eng"], bool)
    k0 = max(0, int(np.flatnonzero(eng)[0]) - 50) if eng.any() else 0
    k1 = min(len(eng), k0 + int(max_s * 100))
    th, cmd, tq, x, abe, vws = (a[k0:k1] for a in D.wire_inputs(W))
    e = eng[k0:k1]
    r0, R = ramp_ticks(e)
    use = [C[c] for c in cands if c in C]
    T, I = D._replay_cand_source(ST, use, th, cmd, tq, x, abe, vws, e, rec_I=True)
    bad = 0
    for b, c in enumerate(use):
        Tf, If = cand_lane(cand_params(c), ST.glut(c.rows), NS.CAL, th, cmd, tq, x, abe, vws, e, R, r0, rec_I=True)
        bad += int(np.sum(Tf != T[:, b])) + int(np.sum(If != I[:, b]))
    T95 = D._replay_v295_source(th, cmd, tq, x, vws, e)
    bad += int(np.sum(v295_lane(LM.load_cal(), th, cmd, tq, x, vws, e, R, r0) != T95))
    return bad


# =====================================================================================================================
# DRIFT GUARD -- the fast lanes mirror these source functions AS THEY WERE when the equality was proved; if any of them
# changes, the drive read falls back to the source march (slow, correct) instead of silently diverging
# =====================================================================================================================
SOURCE_SHA = {
    "score_time.CandLane": "ef3d62843b0696a9", "score_time.Cand": "dc1f5cb0ede5861b",
    "nl_sim.lerp_vec": "f7ff97df1e7db571", "nl_sim.s32": "0a9a6bff03f18e8a", "nl_sim.s16": "3238fac9fb156f8d",
    "lane_mirror_v295.lane_tick": "cefaf5e1151750cb", "lane_mirror_v295.setpoint_chain": "9c32df4c7fd08c1e",
    "lane_mirror_v295.lerp": "d1dd67ce1e893b69",
    "drive_read._replay_cand_source": "d9023daa98d7623c", "drive_read._replay_v295_source": "a0c03e7ba9521bc1",
}


def src_sha(obj):
    import inspect
    return hashlib.sha256(inspect.getsource(obj).replace("\r\n", "\n").encode()).hexdigest()[:16]


def drift(objs):
    """names in {name: object} whose source no longer hashes to SOURCE_SHA[name] (or that cannot be read)."""
    bad = []
    for k, o in objs.items():
        try:
            if src_sha(o) != SOURCE_SHA[k]:
                bad.append(k)
        except (OSError, TypeError, KeyError):
            bad.append(k)
    return bad


# =====================================================================================================================
# CACHE KEY
# =====================================================================================================================
def key_of(*parts):
    """sha256 over the replay's every input: wire arrays (bytes), candidate params, cal, VERSION."""
    h = hashlib.sha256(VERSION.encode())
    for p in parts:
        if isinstance(p, np.ndarray):
            a = np.ascontiguousarray(p)
            h.update(str(a.dtype).encode() + str(a.shape).encode())
            h.update(a.tobytes())
        else:
            h.update(json.dumps(p, sort_keys=True, default=_jd).encode())
    return h.hexdigest()


def _jd(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (tuple, list)):
        return list(x)
    return str(x)
