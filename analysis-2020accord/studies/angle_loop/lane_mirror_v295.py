# -*- coding: utf-8 -*-
r"""BYTE-EXACT PYTHON MIRROR OF THE V295 LKAS LANE (FUN_00028ea6), x load -> lane torque, with the
ANGLE-LOOP candidate edits as switches.  Written 2026-09-30 by the firmware-codepath-tracer subagent
(tracer-hook).  Trace write-up: docs/traces/TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path.md.

IMAGE   _v295_V295-V294BASE-ACCELTRIM.B1050-...TORQUE.TAP_plain_image.bin
        sha256 5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed (asserted below)
        Code 0x28EA6..0x2A30E is byte-identical to V294 (Python compare); the Ghidra program used for the
        listing is the V294 import.  Every cal below is read LITTLE-ENDIAN from the V295 image at run time.

EVERY LINE carries the instruction address it mirrors.  `>>` is Python's floor shift = V850 `sar`.
The LERP divide is `divq` = truncation toward zero (lerp()).  Products are taken as the low 32 bits
(s32()) exactly where the V850 `mul` keeps only the low word.

SWITCHES (all default to the V295 image as built):
  x_src   'rate'  0x28F4C ld.h -0x6a56[gp],r7   (V295)          bytes 24 3f aa 95
          'angle' 0x28F4C ld.h -0x6a00[gp],r7   (candidate)     bytes 24 3f 00 96
  fb_op   'diff'  0x28FA4 subr r9,r26           (V294/V295)     bytes 89 d1
          'sum'   0x28FA4 add  r9,r26           (stock..V293)   bytes c9 d1
  sp_src  'map'   0x29D6A mov r8,r16 ; 0x29D6C mulh r13,r16   (V295)   bytes 08 80 ed 80
          '69ae'  0x29D6A ld.h -0x69ae[gp],r16                (candidate) bytes 24 87 52 96
  d_src   'E'     0x29EDE zxh r7 ; 0x29EE0 mov r16,r8 ; 0x29EE2 sub r27,r8   (V295) bytes c7 00 10 40 bb 41
          'rate'  0x29EDE subr r0,r7 ; 0x29EE0 ld.h -0x6a56[gp],r8       (candidate) bytes 80 39 24 47 aa 95
  i_reset_on_ramp0  False: 0x29A5A bne 0x29a60 (ba 05) ; True: bv 0x29a60 (b0 05, never taken after cmp r0,r8)
  cal overrides: any key of load_cal(), e.g. {'a':0,'b':8192,'C':65535}
"""
from __future__ import annotations

import hashlib
import os
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

FW_ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
V295 = FW_ROOT / "analysis-2020accord" / (
    "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
    "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V295_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
TP = 0xBF000
SEL = 7                      # gp-0x674e, the live variant selector (MEASURED 7 on the wire; kit memory)


def s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(X, Y, u: int) -> int:
    """Honda's integer LERP walk (0x29D18.. and siblings): flat at or below X[0], flat at or above X[-1],
    divq truncates toward zero."""
    if u <= X[0]:
        return Y[0]
    if u >= X[-1]:
        return Y[-1]
    k = 1
    while X[k] <= u:                       # the `while (X[k] <= u)` walk
        k += 1
    num, den = (Y[k] - Y[k - 1]) * (u - X[k - 1]), X[k] - X[k - 1]
    q = abs(num) // abs(den)
    return Y[k - 1] + (-q if (num < 0) != (den < 0) else q)


# ================================================================================================
# CALIBRATION, read LE from the image
# ================================================================================================
def load_cal(path: Path = V295, check_sha: bool = True) -> dict:
    img = path.read_bytes()
    if check_sha:
        h = hashlib.sha256(img).hexdigest()
        assert h == V295_SHA, f"not the V295 image: {h}"
    u16 = lambda a: struct.unpack_from("<H", img, a)[0]
    i16 = lambda a: struct.unpack_from("<h", img, a)[0]
    u32 = lambda a: struct.unpack_from("<I", img, a)[0]

    def rec(bank, n):
        p = u32(bank + 4 * SEL)
        assert u16(p) == n, (hex(bank), u16(p), n)
        return tuple(u16(p + 2 + 2 * i) for i in range(n)), tuple(u16(p + 2 + 2 * n + 2 * i) for i in range(n))

    c = dict(
        C=u16(TP + 0x72E6),      # 0xC62E6 fb clamp, ld.hu @0x28F96/0x28F9C/0x28FB8
        a=i16(TP + 0x73E8),      # 0xC63E8 fb pole, ld.h SIGNED @0x28F8A
        b=u16(TP + 0x73EA),      # 0xC63EA fb gain, ld.hu @0x28F86
        DB=u16(TP + 0x72E4),     # 0xC62E4 I deadband, ld.hu @0x29D6E/84/8C/96
        Ki=u16(TP + 0x73E6),     # 0xC63E6, ld.hu @0x29D9C
        ICL=u16(TP + 0x71BA),    # 0xC61BA, ld.hu @0x29DA0
        PCL=u16(TP + 0x71BC),    # 0xC61BC, ld.hu @0x29E3A..
        DCL=u16(TP + 0x71B6),    # 0xC61B6, ld.hu @0x29EE8..
        SCL=u16(TP + 0x71BE),    # 0xC61BE, ld.hu compare @0x2A13E, ld.h on the + rail @0x2A146
        oa=i16(TP + 0x73EC),     # 0xC63EC output-lag pole, ld.h @0x2A184
        ob=u16(TP + 0x73EE),     # 0xC63EE output-lag gain, ld.hu @0x2A174
        g74a3=img[TP + 0x74A3],  # 0xC64A3 sign-hold gate enable, ld.bu @0x2A198
        dz=i16(TP + 0x71B8),     # 0xC61B8 sign-hold dead zone, ld.h @0x2A1BE
        fwd=i16(TP + 0x7CD0),    # 0xC6CD0 forward gain 5346, ld.h @0x2A1EE (V280+ repointed displacement)
        OCL=u16(TP + 0x71B4),    # 0xC61B4 lane clamp, ld.hu @0x2A1F8, ld.h on the + rail @0x2A20C
        idx_hi=img[TP + 0x74F0], idx_lo=img[TP + 0x74F1],   # 0xC64F0/F1, ld.bu @0x29CD0/0x29CE6
        cut=img[TP + 0x74B8],    # 0xC64B8 override cutout, ld.bu @0x29A78 (255 = unsatisfiable)
        spF=(tuple(u16(TP + 0x7976 + 2 * i) for i in range(4)), tuple(u16(TP + 0x797E + 2 * i) for i in range(4))),
    )
    c["map"] = rec(0xC9A88, 10)
    c["kp"] = rec(0xCB994, 5)
    c["kd"] = rec(0xCB7D4, 4)
    c["lim"] = rec(0xCB844, 9)
    c["tap_same"] = rec(0xCB924, 4)     # sign(cmd) == sign(tq), gp-0x6803 != 2
    c["tap_opp"] = rec(0xCB8B4, 4)      # signs oppose,          gp-0x6803 != 2
    c["cliff_same"] = rec(0xCBA74, 4)   # gp-0x6803 == 2 only (openpilot sends 0 -> never)
    c["cliff_opp"] = rec(0xCBA04, 4)
    c["fadeA"] = rec(0xCBC34, 6)        # key gp-0x6830 (grab rate), gp-0x6803 != 2
    c["fadeA2"] = rec(0xCBB54, 6)       # gp-0x6803 == 2
    c["fadeB"] = rec(0xCBBC4, 6)        # key gp-0x682f = min(|tq|>>5,255), gp-0x6803 != 2
    c["fadeB2"] = rec(0xCBAE4, 6)       # gp-0x6803 == 2
    return c


# ================================================================================================
# THE 0xE4 HANDLER (FUN_00052676) AND THE SETPOINT CHAIN (0x29032 .. 0x29D72)
# ================================================================================================
SENTINEL = 0x7FFF


def e4_handler(raw: int | None) -> int:
    """gp-0x69ae. raw = the signed 16-bit STEER_TORQUE field (bytes 0-1 BE, FUN_00021724); None = an RX
    fault/timeout path (FUN_00052676 param != 0), which writes the 0x7FFF sentinel."""
    if raw is None:
        return SENTINEL                                  # 0x5268C/0x52726/0x527C6 movea 0x7fff ; st.h
    r6 = s16(raw)                                        # 0x526CC sxh r6
    r6 = s32(-(r6 << 2))                                 # 0x526D2 shl 0x2 ; 0x526D4 subr r0,r6
    return clamp(r6, -0x4000, 0x4000)                    # 0x526DA jarl FUN_00049a90 ; 0x526F2 st.h r10


def setpoint_chain(cmd69ae: int, cal: dict, tq: int = 0, i682f: int | None = None, i6830: int = 0,
                   speed: int = 0, sel6803: int = 0):
    """Returns (idx, sign, sp_map). cmd69ae = gp-0x69ae as stored (signed 16, or the sentinel)."""
    r13 = s16(cmd69ae)                                   # 0x29032 ld.h -0x69ae[gp],r13
    LIM = lerp(*cal["lim"], speed) & 0xFFFF              # 0x28FC8..0x29030 LERP(0xCB844[sel]) ; 0x29036 andi
    r22 = clamp(r13, -LIM, LIM)                          # 0x2903A..0x29044 cmp/bgt/subr/cmovle
    if i682f is None:
        i682f = min(abs(tq >> 5), 255)                   # 0x29048..0x29068 (gp-0x682f)
    if i682f > cal["cut"]:                               # 0x29A86 cmp r8,r1 ; 0x29A88 bnh ; 0x29A8A jr 0x29CC4
        v = 0                                            # 0x29CCC mov 0x0,r7
    else:
        same = (r22 < 0) == (tq < 0)                     # 0x29A8E..0x29A9E sign fork (cmd==0 counts as +)
        if sel6803 == 2:
            T = cal["cliff_same"] if same else cal["cliff_opp"]
        else:
            T = cal["tap_same"] if same else cal["tap_opp"]
        taper = lerp(*T, i682f)
        spF = lerp(*cal["spF"], i6830)                   # 0x29C5A..0x29CB2 (0xC6974 record, flat 255)
        G = (spF * taper) & 0xFFFF                       # 0x29CB4 mulu ; 0x29CB8 andi 0xffff
        v = s32(G * r22) >> 16                           # 0x29CBC mul r22,r7 ; 0x29CC0 sar 0x10
    v >>= 6                                              # 0x29CD6 sar 0x6
    sign = -1 if v < 0 else 1                            # 0x29CD4 mov 0x1,r8 ; 0x29CD8 cmovn -0x1,r8,r8
    v = clamp(v, -cal["idx_lo"], cal["idx_hi"])          # 0x29CDC..0x29CF4
    idx = abs(v)                                         # 0x29CF6..0x29CFA
    Y = lerp(*cal["map"], idx & 0xFF)                    # 0x29D10 mov r7,r22 ; zxb ; 0x29D18..0x29D68 LERP
    sp = s16(sign) * s16(Y)                              # 0x29D6A mov r8,r16 ; 0x29D6C mulh r13,r16
    return idx, sign, s32(sp)


# ================================================================================================
# STATE (all RAM cells this lane owns; cold boot = 0 per the .data copy loop, kit memory)
# ================================================================================================
@dataclass
class LaneState:
    s: int = 0                 # gp-0x3d30 fb filter state (32-bit)
    lane_ok: int = 0           # gp-0x3d2c  (1 = previous tick was valid)
    I8: int = 0                # gp-0x6dd0  (holds 8*I)
    Eprev: int = 0             # gp-0x6cf8  (0x7FFFFFFF = Honda's first-tick sentinel)
    olag: int = 0              # gp-0x3d3c output-lag state (32-bit)
    T_prev_lane: int = 0       # gp-0x6b30  (yr of the previous tick, for the sign-hold gate)
    log: dict = field(default_factory=dict)


@dataclass
class Edits:
    x_src: str = "rate"        # 'rate' | 'angle'
    fb_op: str = "diff"        # 'diff' | 'sum'
    sp_src: str = "map"        # 'map'  | '69ae'
    d_src: str = "E"           # 'E'    | 'rate'
    i_reset_on_ramp0: bool = False
    e_shift: int = 2           # imm5 of 0x29D76 shl (2 on V294/V295, 5 stock)


def lane_tick(st: LaneState, cal: dict, ed: Edits, *, rate: int, angle: int, cmd69ae: int,
              tq: int = 0, i6830: int = 0, speed: int = 0, ramp: int = 0x8000, act6806: int = 1,
              req6805: int = 1, pol: int = 1, others_valid: bool = True, sel6803: int = 0) -> int:
    """One 1 kHz tick. rate = gp-0x6a56 (8 counts per deg/s), angle = gp-0x6a00 (0.1 deg/count),
    cmd69ae = gp-0x69ae, tq = gp-0x4f60, ramp = gp-0x69b0 AFTER this tick's engage-SM update,
    act6806 = STEER_CONTROL_ACTIVE, req6805 = STEER_TORQUE_REQUEST, pol = gp-0x6752.
    others_valid = the driver-torque / pol gates at 0x28F26..0x28F48 and 0x28F5E (taken as given).
    Returns T = gp-0x6b38."""
    # ---------------- fb filter, 0x28F4C..0x28FBE (runs EVERY tick, above the engagement guard) -------
    x = s16(rate if ed.x_src == "rate" else angle)      # 0x28F4C ld.h -0x6a56|-0x6a00[gp],r7
    valid = others_valid and (-12000 <= x <= 12000)      # 0x28F50 addi 0x2ee0 ; 0x28F54 addi -0x5dc1 ; bnc
    if valid:
        s_old = st.s if st.lane_ok == 1 else 0           # 0x28F66..0x28F84 (gp-0x3d2c sentinel reset)
        bx = s32(x * (cal["b"] & 0xFFFF))                # 0x28F86 ld.hu b ; 0x28F8E mul r16,r7,r0
        as_ = s32(s16(cal["a"]) * s_old)                 # 0x28F8A ld.h a  ; 0x28F92 mul r26,r9,r0
        s_new = s32((as_ >> 10) + (bx >> 10))            # 0x28F9A/0x28FA0 sar 0xa ; 0x28FA2 add r7,r9
        r26 = s32(s_old + s_new) if ed.fb_op == "sum" else s32(s_new - s_old)   # 0x28FA4 add|subr r9,r26
        st.s = s_new                                     # 0x28FA8 st.w r9,-0x3d30[gp]
        C = cal["C"] & 0xFFFF
        r26 = clamp(r26, -C, C)                          # 0x28FA6..0x28FBC
        st.lane_ok = 1                                   # gp-0x3d2c := 1 (r1)
    else:
        r26 = 0                                          # 0x290B6 mov 0x0,r26  (bail; gp-0x3d2c := 2)
        st.lane_ok = 2
    st.log["r26"] = r26
    st.log["g6a34"] = (abs((r26 >> 5) << 5)) >> 5        # 0x28FBE..0x28FC6, 0x290C6 shr 5, 0x290CA st.h

    # ---------------- the guard 0x29A48..0x29A70 ------------------------------------------------------
    if ed.i_reset_on_ramp0:
        run = valid and ramp != 0                        # 0x29A5A bne -> bv (never taken): skip iff ramp==0
    else:
        run = valid and (ramp != 0 or req6805 == 1)      # stock: run iff (ramp!=0 or request) and inputs valid
    if run:
        # ------------ setpoint 0x29032 .. 0x29D72 ----------------------------------------------------
        idx, sign, sp_map = setpoint_chain(cmd69ae, cal, tq=tq, i6830=i6830, speed=speed, sel6803=sel6803)
        sp = sp_map if ed.sp_src == "map" else s16(cmd69ae)          # 0x29D6A (mov+mulh | ld.h -0x69ae)
        st.log.update(idx=idx, sp=sp)
        # ------------ error 0x29D76/0x29D78 -----------------------------------------------------------
        E = s32((sp << ed.e_shift) - r26)                # 0x29D76 shl imm5,r16 ; 0x29D78 sub r26,r16
        # ------------ I 0x29D7A..0x29DC2 --------------------------------------------------------------
        e5 = E >> 5                                      # 0x29D7C sar 0x5,r6
        DB = cal["DB"] & 0xFFFF
        exc = e5 - DB if e5 > DB else (e5 + DB if e5 < -DB else 0)   # 0x29D7E..0x29D9A
        icl = ((cal["ICL"] & 0xFFFF) << 10) >> 3         # 0x29DA0 ld.hu ; 0x29DAC shl 0xa ; 0x29DAE sar 0x3
        inc = s32(exc * (cal["Ki"] & 0xFFFF)) >> 3       # 0x29DA8 mul r6,r9,r0 ; 0x29DB2 sar 0x3
        I = clamp(s32((st.I8 >> 3) + inc), -icl, icl)    # 0x29DA4 ld.w ; 0x29DB0 sar 0x3 ; 0x29DB4 add ; clamp
        I8_new = s32(I << 3)                             # 0x29DE0 mov r2,r24 ; 0x29DE4 shl 0x3,r24
        # ------------ P 0x29DC6..0x29E5C --------------------------------------------------------------
        kp = lerp(*cal["kp"], idx & 0xFFFF) & 0xFFFF     # 0x29DC6..0x29E32 (key idx, zxh)
        P = clamp(s32(E * kp) >> 8, -cal["PCL"], cal["PCL"])   # 0x29E34 mov ; 0x29E36 mul ; 0x29E3E sar 0x8
        # ------------ D 0x29E5E..0x29F06 --------------------------------------------------------------
        kd = lerp(*cal["kd"], idx & 0xFF)                # 0x29E76..0x29EDC (key idx byte, r22)
        if ed.d_src == "E":
            kd &= 0xFFFF                                 # 0x29EDE zxh r7
            r27 = st.Eprev if -768000 <= st.Eprev <= 768000 else E   # 0x29E5E..0x29E7E cmovnc
            r8 = s32(E - r27)                            # 0x29EE0 mov r16,r8 ; 0x29EE2 sub r27,r8
        else:
            kd = s32(-(kd & 0xFFFF))                     # 0x29EDE subr r0,r7      (candidate)
            r8 = s16(rate)                               # 0x29EE0 ld.h -0x6a56[gp],r8 (candidate)
        D = clamp(s32(kd * r8) >> 3, -cal["DCL"], cal["DCL"])   # 0x29EE4 mul r7,r8,r0 ; 0x29EEC sar 0x3 ; clamp
        # ------------ sum and the post-PID fade 0x29F18..0x2A0C2 -------------------------------------
        S = s32((I >> 7) + P + D)                        # 0x29F18 sar 0x7,r2 ; 0x29F1E add r9,r2 ; 0x29F24 add r8,r2
        i682f = min(abs(tq >> 5), 255)
        A = lerp(*(cal["fadeA2"] if sel6803 == 2 else cal["fadeA"]), i6830)   # 0x29F08..0x29FE8
        B = lerp(*(cal["fadeB2"] if sel6803 == 2 else cal["fadeB"]), i682f)   # 0x29FE2..0x2A0B0
        f = ((A * B) & 0xFFFF) >> 8                      # 0x2A0B4 mulu ; 0x2A0B8 andi 0xffff ; 0x2A0BC sar 0x8
        Sf = s32(S * f) >> 8                             # 0x2A0BE mul r2,r12 ; 0x2A0C2 sar 0x8
        SCL = cal["SCL"] & 0xFFFF
        if Sf > SCL:
            Sc = s16(cal["SCL"])                         # 0x2A146 ld.h (SIGNED: latent defect if SCL > 32767)
        elif Sf < -SCL:
            Sc = s16(-SCL)                               # 0x2A156 ld.hu ; subr ; 0x2A15C sxh
        else:
            Sc = s16(Sf)                                 # 0x2A160 sxh
        Eprev_new = E                                    # r16 -> 0x2A18C
        st.log.update(E=E, I=I, P=P, D=D, kp=kp, kd=kd, S=S, f=f, Sc=Sc)
    else:
        Sc, I8_new, Eprev_new = 0, 0, 0x7FFFFFFF         # 0x2A164..0x2A172 (shared epilogue head)
        st.log.update(E=None, I=0, P=0, D=0, S=0, Sc=0)
    st.I8 = I8_new                                       # 0x2A190 st.w r24,-0x6dd0[gp]
    st.Eprev = Eprev_new                                 # 0x2A18C st.w r16,-0x6cf8[gp]
    # ---------------- output lag 0x2A174..0x2A1B0 (runs every tick) -----------------------------------
    t1 = s32(Sc * (cal["ob"] & 0xFFFF)) >> 10            # 0x2A174 ld.hu ; 0x2A180 mul ; 0x2A1A0 sar 0xa
    t2 = s32(s16(cal["oa"]) * st.olag) >> 10             # 0x2A184 ld.h ; 0x2A194 mul ; 0x2A1A6 sar 0xa
    o_new = s32(t2 + t1)                                 # 0x2A1A8 add r12,r7
    y = s32(st.olag + o_new) >> 5                        # 0x2A1AA add r7,r9 ; 0x2A1AC sar 0x5
    st.olag = o_new                                      # 0x2A1B0 st.w r7,-0x3d3c[gp]
    # ---------------- sign-hold gate 0x2A1AE..0x2A1E4 (only once STEER_CONTROL_ACTIVE == 0) ------------
    if cal["g74a3"] == 1 and act6806 == 0:
        if (s16(y) <= cal["dz"] and y >= -(cal["dz"] & 0xFFFF)) or s32(y * st.T_prev_lane) <= 0:
            yr = 0                                       # 0x2A1E2 mov 0x0,r9
        else:
            yr = s16(s32(y * ramp) >> 15)                # 0x2A1E6 mul r14,r9 ; sar 0xf ; sxh
    else:
        yr = s16(s32(y * ramp) >> 15)
    # ---------------- forward gain and lane clamp 0x2A1EE..0x2A23C -----------------------------------
    k = s32(s16(pol) * s16(cal["fwd"]))                  # 0x2A1EE ld.h 0x7cd0 ; 0x2A1F2 ld.b pol ; 0x2A1F6 mulh
    r11 = s32((0 + yr) * k) >> 15                        # 0x2A1FC add r9,r11 (gp-0x6b2c addend == 0) ; mul ; sar 0xf
    OCL = cal["OCL"] & 0xFFFF
    T = s16(cal["OCL"]) if r11 > OCL else (-OCL if r11 < -OCL else r11)   # 0x2A204..0x2A220
    st.T_prev_lane = yr                                  # 0x2A206 st.h r9,-0x6b30[gp]
    st.log.update(y=y, yr=yr, T=T)
    return s16(T)                                        # 0x2A23C st.h r1,-0x6b38[gp]


# ================================================================================================
# CROSS-CHECK AGAINST THE GOLDEN MODEL, AND THE CANDIDATE CLAIMS
# ================================================================================================
def _crosscheck_golden(cal: dict, n: int = 20000, seed: int = 7) -> str:
    """Tick-by-tick against eps_lkas_chain_model.lkas_fb_lag + lkas_rate_pid_tick on the V295 cal, engaged
    (ramp 0x8000, STEER_CONTROL_ACTIVE 1, hands off, taper 254). Returns a one-line verdict."""
    import random
    from dataclasses import replace
    import eps_lkas_chain_model as M
    gm = replace(M.Calibration(), fb_clamp=cal["C"], fb_lag_a=cal["a"], fb_lag_b=cal["b"], fb_op="diff",
                 e_shift=2, kp_y=cal["kp"][1], kp_x=cal["kp"][0], kd_y=cal["kd"][1], kd_x=cal["kd"][0],
                 pid_d_clamp=cal["DCL"], assist_map_x=cal["map"][0], assist_map_y=cal["map"][1])
    gs = M.EpsState()
    st, ed = LaneState(), Edits()
    rnd = random.Random(seed)
    x = 0
    for t in range(n):
        x = clamp(x + rnd.randint(-40, 40), -3000, 3000)
        raw = rnd.randint(-3840, 3840) if t % 500 == 0 else (raw if t else 0)
        cmd = e4_handler(raw)
        T = lane_tick(st, cal, ed, rate=x, angle=0, cmd69ae=cmd)
        fb = M.lkas_fb_lag(x, gs, gm)
        idx, sign, sp = setpoint_chain(cmd, cal)
        r = M.lkas_rate_pid_tick(sp, fb, idx, gs, gm, pol=1, taper=254)
        assert fb == st.log["r26"], (t, fb, st.log["r26"])
        assert (r["E"], r["P"], r["S"], r["T"]) == (st.log["E"], st.log["P"], st.log["Sc"], T), (t, r, st.log)
    return f"golden model agrees tick-for-tick over {n} engaged ticks (fb, E, P, S, T)"


def _claims(cal: dict):
    out = []
    # (1) the map path is an 8-bit index: count distinct |sp| over the whole wire range
    sps = {abs(setpoint_chain(e4_handler(r), cal)[2]) for r in range(-4096, 4097)}
    idxs = {setpoint_chain(e4_handler(r), cal)[0] for r in range(-4096, 4097)}
    out.append(f"map path: {len(idxs)} distinct idx, {len(sps)} distinct |sp| over raw -4096..4096")
    # floor asymmetry: raw +1 -> idx 1 ; raw -1 -> idx 0
    out.append(f"floor asymmetry: raw +1 -> idx {setpoint_chain(e4_handler(1), cal)[0]}, "
               f"raw -1 -> idx {setpoint_chain(e4_handler(-1), cal)[0]}")
    # (2) the sentinel: RX fault -> sp
    i, sg, sp = setpoint_chain(SENTINEL, cal)
    out.append(f"0xE4 fault sentinel: idx {i}, sp {sp} (map path) ; sp {s16(SENTINEL)} with sp_src='69ae'")
    st = LaneState()
    T = [lane_tick(st, cal, Edits(), rate=0, angle=0, cmd69ae=SENTINEL, ramp=max(0, 0x8000 - 16 * k),
                   act6806=0 if k else 1, req6805=0) for k in range(0, 2049, 1)]
    out.append(f"V295 fault, lane already pushing + (prev T>0 needed by the sign-hold gate): T at 0/100/500/1000/2000 ms "
               f"= {T[0]}/{T[100]}/{T[500]}/{T[1000]}/{T[2000]}")
    # (3) the angle loop: E == 16*(theta_sp - theta) exactly, theta_sp = -raw
    C = dict(cal, a=0, b=8192, C=65535)
    ed = Edits(x_src="angle", fb_op="sum", sp_src="69ae")
    import random
    rnd = random.Random(1)
    ok = 0
    for _ in range(20000):
        st = LaneState()
        th, raw = rnd.randint(-4000, 4000), rnd.randint(-4096, 4096)
        lane_tick(st, C, ed, rate=0, angle=th, cmd69ae=e4_handler(raw))       # primes s (theta[n-1])
        lane_tick(st, C, ed, rate=0, angle=th, cmd69ae=e4_handler(raw))
        assert st.log["r26"] == 16 * th and st.log["E"] == 16 * (-raw - th), (th, raw, st.log)
        ok += 1
    out.append(f"angle loop (x=angle, sum, a=0, b=8192, C=65535, sp=gp-0x69ae): r26 == 16*theta and "
               f"E == 16*(theta_sp - theta), theta_sp = -raw, on {ok} random (theta, raw)")
    # (4) the D swap: D == clamp((-Kd*x)>>3)
    C2 = dict(C, kd=(cal["kd"][0], (16, 16, 16, 16)), DCL=10240)
    st = LaneState()
    lane_tick(st, C2, Edits(x_src="angle", fb_op="sum", sp_src="69ae", d_src="rate"), rate=80, angle=0, cmd69ae=0)
    out.append(f"D swap: rate x=80 (10 deg/s), Kd 16 -> D = {st.log['D']} (expect (-16*80)>>3 = {(-16 * 80) >> 3})")
    return out


def _enc_ldh_gp(reg2: int, disp: int) -> bytes:
    """Format VII ld.h disp16[gp],reg2: hw1 = reg2<<11 | 0b111001<<5 | 4 ; hw2 = disp (even)."""
    assert disp % 2 == 0
    return struct.pack("<HH", (reg2 << 11) | (0x39 << 5) | 4, disp & 0xFFFF)


def _enc_fmt1(op6: int, reg1: int, reg2: int) -> bytes:
    """Format I reg-reg: hw = reg2<<11 | op6<<5 | reg1 (mov 0x00, subr 0x0C, sub 0x0D, add 0x0E)."""
    return struct.pack("<H", (reg2 << 11) | (op6 << 5) | reg1)


EDIT_SITES = {   # address: (V295 bytes, candidate bytes, what)
    0x28F4C: (bytes.fromhex("243faa95"), _enc_ldh_gp(7, -0x6a00), "x := gp-0x6a00"),
    0x28FA4: (bytes.fromhex("89d1"), _enc_fmt1(0x0E, 9, 26), "subr r9,r26 -> add r9,r26"),
    0x29D6A: (bytes.fromhex("0880ed80"), _enc_ldh_gp(16, -0x69ae), "mov r8,r16; mulh r13,r16 -> ld.h -0x69ae[gp],r16"),
    0x29EDE: (bytes.fromhex("c700"), _enc_fmt1(0x0C, 0, 7), "zxh r7 -> subr r0,r7"),
    0x29EE0: (bytes.fromhex("1040bb41"), _enc_ldh_gp(8, -0x6a56), "mov r16,r8; sub r27,r8 -> ld.h -0x6a56[gp],r8"),
    0x29A5A: (bytes.fromhex("ba05"), bytes.fromhex("b005"), "bne 0x29a60 -> bv 0x29a60 (never taken)"),
}


def _check_encodings():
    img = V295.read_bytes()
    out = []
    # encoder positive controls against instructions that already exist in this image
    assert img[0x29032:0x29036] == _enc_ldh_gp(13, -0x69ae)          # ld.h -0x69ae[gp],r13
    assert img[0x28F4C:0x28F50] == _enc_ldh_gp(7, -0x6a56)           # ld.h -0x6a56[gp],r7
    assert img[0x40B04:0x40B08] == _enc_ldh_gp(14, -0x6a00)          # ld.h -0x6a00[gp],r14
    assert img[0x40B4C:0x40B4E] == _enc_fmt1(0x0C, 0, 9)             # subr r0,r9
    assert img[0x29EE0:0x29EE2] == _enc_fmt1(0x00, 16, 8)            # mov r16,r8
    assert img[0x29EE2:0x29EE4] == _enc_fmt1(0x0D, 27, 8)            # sub r27,r8
    assert img[0x29D78:0x29D7A] == _enc_fmt1(0x0D, 26, 16)           # sub r26,r16
    for a, (old, new, what) in EDIT_SITES.items():
        assert img[a:a + len(old)] == old, (hex(a), img[a:a + len(old)].hex())
        assert len(new) == len(old)
        out.append(f"  {a:#07x}  {old.hex()} -> {new.hex()}   {what}")
    # bcond: cccc = low nibble; 0xA = bne, 0x0 = bv; disp bits unchanged
    assert struct.unpack("<H", EDIT_SITES[0x29A5A][1])[0] == (struct.unpack("<H", img[0x29A5A:0x29A5C])[0] & ~0xF)
    return out


if __name__ == "__main__":
    cal = load_cal()
    print("edit sites (V295 bytes asserted, encoder positive-controlled on existing instructions):")
    for line in _check_encodings():
        print(line)
    print("V295 cal:", {k: cal[k] for k in ("C", "a", "b", "DB", "Ki", "ICL", "PCL", "DCL", "SCL", "oa", "ob",
                                            "g74a3", "dz", "fwd", "OCL", "idx_hi", "idx_lo", "cut")})
    print("map Y:", cal["map"][1], " Kp Y:", cal["kp"][1], " Kd Y:", cal["kd"][1])
    print(_crosscheck_golden(cal))
    for line in _claims(cal):
        print(line)
