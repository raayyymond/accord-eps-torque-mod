"""
c3_pid_mirror.py -- V295 census, step 3: the V294 LKAS PID (FUN_00028ea6) as simple integer Python that
mirrors the listing EXACTLY, every line annotated with the instruction address that executes it. Every cal
value is READ FROM THE IMAGE BYTES (little-endian), never typed in. Then the design-space tables.

Method (EVIDENCE): Ghidra decompile of FUN_00028ea6 on the V294 program (/advC/_v294_..., bytes spot-checked
against the file at 0x28FA0, 0x29D70, 0xC63E0), then disassemble_bytes(dry_run) of 0x28F4C-0x28FE0,
0x29080-0x290E0, 0x29A40-0x29AB0, 0x29C40-0x29F40, 0x29F40-0x2A0C6, 0x2A13E-0x2A2F0 to pin every
instruction below. Inherited (not re-derived here): the 0x0E4 handler writes gp-0x69ae = clamp(-4*wire,
+-0x4000) (memory reference_accord_0e4_handler_x4); x = 8.00 counts per deg/s (V294 redo, 0x55B48).

Run:  python c3_pid_mirror.py  -> prints the tables; out/c3_tables.json
"""
import json
import random
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from c1_images_and_cells import load, u16, s16, u32

HERE = Path(__file__).resolve().parent
SEL = 7
TS = 1e-3                 # tick, 1 ms (EVIDENCE-by-consistency, two pole-label agreements; not a timer read)
X_PER_DEGS = 8.0          # x counts per deg/s of steering-wheel rate (EVIDENCE per the V294 redo)


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def clamp(v, lo, hi):
    return hi if v > hi else (lo if v < lo else v)


def fw_lerp(X, Y, x):
    """the firmware walk: flat below X[0] / at-or-above X[-1]; divq TRUNCATES toward zero."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    i = 1
    while X[i] <= x:           # 'while (X[i] <= x) i++' -- stops at the first X > x, so X[i]-X[i-1] > 0
        i += 1
    num = (Y[i] - Y[i - 1]) * (x - X[i - 1])
    den = X[i] - X[i - 1]
    q = abs(num) // abs(den)
    return Y[i - 1] + (q if (num >= 0) == (den > 0) else -q)


@dataclass
class Cal:
    # every field is filled from the image by read_cal(); names carry the address
    a_C63E8: int = 0; b_C63EA: int = 0; C_C62E6: int = 0          # fb former
    db_C62E4: int = 0; ki_C63E6: int = 0; icl_C61BA: int = 0       # I
    pcl_C61BC: int = 0; dcl_C61B6: int = 0; scl_C61BE: int = 0     # clamps
    oa_C63EC: int = 0; ob_C63EE: int = 0                           # output lag
    garm_C64A3: int = 0; gthr_C61B8: int = 0                       # output gate
    gain_C6CD0: int = 0; ocl_C61B4: int = 0; fcl_C61B2: int = 0    # delivery
    idxp_C64F0: int = 0; idxn_C64F1: int = 0; cut_C64B8: int = 0   # demand
    e_shift_29D76: int = 0                                         # the shl immediate (CODE)
    fb_op_28FA4: str = ""                                          # 'sum' (add) or 'diff' (subr)  (CODE)
    kp_x: tuple = (); kp_y: tuple = (); kd_x: tuple = (); kd_y: tuple = ()
    map_x: tuple = (); map_y: tuple = (); lim_x: tuple = (); lim_y: tuple = ()
    g_eq: tuple = (); g_ne: tuple = (); g_ov_eq: tuple = (); g_ov_ne: tuple = ()
    tA: tuple = (); tB: tuple = (); tC: tuple = (); tD: tuple = ()
    act: tuple = ()


def _rec(b, bank, n):
    p = u32(b, bank + 4 * SEL)
    return (tuple(u16(b, p + 2 + 2 * i) for i in range(n)), tuple(u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)))


def read_cal(b):
    c = Cal()
    c.a_C63E8 = s16(b, 0xC63E8); c.b_C63EA = u16(b, 0xC63EA); c.C_C62E6 = u16(b, 0xC62E6)
    c.db_C62E4 = u16(b, 0xC62E4); c.ki_C63E6 = u16(b, 0xC63E6); c.icl_C61BA = u16(b, 0xC61BA)
    c.pcl_C61BC = u16(b, 0xC61BC); c.dcl_C61B6 = u16(b, 0xC61B6); c.scl_C61BE = u16(b, 0xC61BE)
    c.oa_C63EC = s16(b, 0xC63EC); c.ob_C63EE = u16(b, 0xC63EE)
    c.garm_C64A3 = b[0xC64A3]; c.gthr_C61B8 = s16(b, 0xC61B8)
    # forward gain: V57+ images repoint 0x2A1F0's displacement 0x746C -> 0x7CD0; read the displacement
    disp = u16(b, 0x2A1F0)
    c.gain_C6CD0 = s16(b, 0xBF000 + disp)
    c.ocl_C61B4 = u16(b, 0xC61B4); c.fcl_C61B2 = u16(b, 0xC61B2)
    c.idxp_C64F0 = b[0xC64F0]; c.idxn_C64F1 = b[0xC64F1]; c.cut_C64B8 = b[0xC64B8]
    hw = u16(b, 0x29D76)                     # shl imm5,r16 : 0x82C0 | imm  (c5 82 = shl 5 ; c2 82 = shl 2)
    assert hw & 0xFFE0 == 0x82C0, hex(hw)
    c.e_shift_29D76 = hw & 0x1F
    hw = u16(b, 0x28FA4)                     # add r9,r26 = d1c9 ; subr r9,r26 = d189
    c.fb_op_28FA4 = {0xD1C9: "sum", 0xD189: "diff"}[hw]
    c.kp_x, c.kp_y = _rec(b, 0xCB994, 5)
    c.kd_x, c.kd_y = _rec(b, 0xCB7D4, 4)
    c.map_x, c.map_y = _rec(b, 0xC9A88, 10)
    c.lim_x, c.lim_y = _rec(b, 0xCB844, 9)
    c.g_eq = _rec(b, 0xCB924, 4); c.g_ne = _rec(b, 0xCB8B4, 4)
    c.g_ov_eq = _rec(b, 0xCBA74, 4); c.g_ov_ne = _rec(b, 0xCBA04, 4)
    c.tA = _rec(b, 0xCBB54, 6); c.tB = _rec(b, 0xCBC34, 6); c.tC = _rec(b, 0xCBAE4, 6); c.tD = _rec(b, 0xCBBC4, 6)
    c.act = (tuple(u16(b, 0xC6976 + 2 * i) for i in range(4)), tuple(u16(b, 0xC697E + 2 * i) for i in range(4)))
    return c


@dataclass
class St:
    s: int = 0            # gp-0x3d30  fb-lag state (int32), boots 0 (.data src 0x89380 = 00000000)
    sentinel: int = 0     # gp-0x3d2c  1 = filter ran last tick, 2 = bailed; boots 0
    I8: int = 0           # gp-0x6dd0  holds 8*I (int32), boots 0
    Eprev: int = 0x7FFFFFFF  # gp-0x6cf8 E_prev; disengage writes the 0x7FFFFFFF sentinel
    L: int = 0            # gp-0x3d3c  output-lag state (int32)
    yr_prev: int = 0      # gp-0x6b30  last ramped output


# ------------------------------------------------------------------------------------------------------
# 1. DEMAND: 0x0E4 wire -> cmd -> idx -> sp
# ------------------------------------------------------------------------------------------------------
def demand(wire, cal, bar=0, dbar6=0, e4_field=0, speed=0):
    """returns (idx 0..240, sign r8, sp).  bar = gp-0x4f60 torsion bar raw; dbar6 = gp-0x6830; e4_field = gp-0x6803"""
    cmd = clamp(-4 * wire, -0x4000, 0x4000)                 # 0x0E4 handler -> gp-0x69ae   [INHERITED]
    lim = fw_lerp(cal.lim_x, cal.lim_y, speed)              # 0x28FCC.. LERP 0xCB844 on speed gp-0x6a5e
    cmd = clamp(cmd, -lim, lim)                             # decompile lines 122-132 (clamp to +-LIM)
    bar5 = abs(bar >> 5)                                    # 0x29068 st.b gp-0x682f = |bar>>5|, 0xFF above 254
    bar5 = bar5 if bar5 <= 254 else 255
    ov = (e4_field == 2)                                    # 0x29A74 ld.bu gp-0x6803 ; 0x29A82 setfe r25 (==2)
    if cal.cut_C64B8 < bar5:                                # 0x29A78 ld.bu 0x74b8 ; 0x29A86 cmp ; 0x29A88 bnh
        prod = 0                                            # 0x29CC4.. r7 := 0 : the demand is CUT
    else:
        same = (cmd < 0) == (bar < 0)                       # 0x29A8E..0x29A9E sign(cmd) vs sign(bar)
        if same:
            G = fw_lerp(*(cal.g_ov_eq if ov else cal.g_eq), bar5)   # 0xCBA74 / 0xCB924
        else:
            G = fw_lerp(*(cal.g_ov_ne if ov else cal.g_ne), bar5)   # 0xCBA04 / 0xCB8B4
        act = fw_lerp(*cal.act, dbar6)                      # 0x29C5A.. activity LERP 0xC6976 on gp-0x6830
        g = (G * act) & 0xFFFF                              # 0x29CB4 mulu r6,r10 ; 0x29CB8 andi 0xffff
        prod = s32(g * cmd) >> 16                           # 0x29CBC mul r22,r7 ; 0x29CC0 sar 0x10
    v = prod >> 6                                           # 0x29CD6 sar 0x6
    sgn = -1 if v < 0 else 1                                # 0x29CD4 mov 1,r8 ; 0x29CD8 cmovn -1
    v = min(v, cal.idxp_C64F0)                              # 0x29CD0/0x29CDC.. clamp +[0xC64F0]
    v = max(v, -cal.idxn_C64F1)                             # 0x29CE6.. clamp -[0xC64F1]
    idx = abs(v) & 0xFF                                     # 0x29CF6..0x29CFA abs ; 0x29D12 zxb ; st.b gp-0x674b
    m = fw_lerp(cal.map_x, cal.map_y, idx)                  # 0x29CFC mov 0xc9a88 .. 0x29D68 LERP
    sp = s32(((m & 0xFFFF) ^ 0x8000) - 0x8000) * sgn        # 0x29D6C mulh r13,r16  (16x16 signed)
    return idx, sgn, sp                                     # 0x29D72 st.h sp -> gp-0x6a32


# ------------------------------------------------------------------------------------------------------
# 2. FEEDBACK FORMER (0x28F4C..0x28FBE), runs EVERY tick, engaged or not
# ------------------------------------------------------------------------------------------------------
def fb_former(x, st, cal, bail=False):
    """returns (r26, ok).  ok False = one of the four bails (0x28F3C/48/5A/62): r26 := 0 and the PID is skipped"""
    if bail or not (-12000 <= x <= 12000):                  # 0x28F50..0x28F5A (the other 3 bails: bar/pol)
        st.sentinel = 2                                     # 0x290B0 mov 2,r1 ; 0x290D4 st.b gp-0x3d2c
        return 0, False                                     # 0x290B6 mov 0,r26 ; 0x290C0 mov 0,r25 (-> skip)
    s_old = st.s if st.sentinel == 1 else 0                 # 0x28F66 ld.bu sentinel ; 0x28F7C ld.w / 0x28F84 mov 0
    b = cal.b_C63EA & 0xFFFF                                # 0x28F86 ld.hu 0x73ea
    a = cal.a_C63E8                                         # 0x28F8A ld.h  0x73e8 (SIGNED)
    tb = s32(x * b) >> 10                                   # 0x28F8E mul ; 0x28F9A sar 0xa
    ta = s32(a * s_old) >> 10                               # 0x28F92 mul ; 0x28FA0 sar 0xa
    s_new = s32(ta + tb)                                    # 0x28FA2 add r7,r9
    if cal.fb_op_28FA4 == "diff":
        r26 = s32(s_new - s_old)                            # 0x28FA4 subr r9,r26   (V294)
    else:
        r26 = s32(s_old + s_new)                            # 0x28FA4 add  r9,r26   (stock..V293)
    st.s = s_new                                            # 0x28FA8 st.w gp-0x3d30
    C = cal.C_C62E6 & 0xFFFF                                # 0x28F96/0x28F9C ld.hu 0x72e6
    r26 = C if r26 > C else (-C if r26 < -C else r26)       # 0x28FA6..0x28FBC
    st.sentinel = 1                                         # 0x28F74 mov 1,r1 ; 0x290D4 st.b
    return r26, True


# ------------------------------------------------------------------------------------------------------
# 3. THE PID (0x29D72..0x2A162) and the delivery (0x2A164..0x2A23C)
# ------------------------------------------------------------------------------------------------------
def pid_tick(sp, idx, r26, st, cal, run=True, bar5=0, dbar6=0, e4_field=0, ramp=0x8000, ramping_up=True, pol=1):
    """one tick. run=False is the 0x29A5C/0x29A64 skip to the 0x2A164 epilogue (disengaged or filter bail)."""
    o = {}
    if run:
        E = s32((sp << cal.e_shift_29D76) - r26)            # 0x29D76 shl imm,r16 ; 0x29D78 sub r26,r16
        e5 = E >> 5                                         # 0x29D7A mov ; 0x29D7C sar 0x5,r6
        db = cal.db_C62E4                                   # 0x29D6E ld.hu 0x72e4
        if e5 > db:                                         # 0x29D7E cmp ; 0x29D82 ble
            exc = e5 - db                                   # 0x29D84 ld.hu ; 0x29D88 subr r6,r9
        elif e5 < -db:                                      # 0x29D8C..0x29D94
            exc = e5 + db                                   # 0x29D96 ld.hu ; 0x29D9A add r6,r9
        else:
            exc = 0                                         # 0x29D80 mov 0,r9
        icl = s32((cal.icl_C61BA & 0xFFFF) << 10) >> 3      # 0x29DA0 ld.hu 0x71ba ; 0x29DAC shl 0xa ; 0x29DAE sar 3
        Iraw = s32((st.I8 >> 3) + (s32(exc * cal.ki_C63E6) >> 3))   # 0x29DA4 ld.w gp-0x6dd0 ; 0x29DA8 mul ; sar3 x2 ; add
        I = icl if Iraw > icl else (-icl if Iraw <= -icl else Iraw)  # 0x29DB6 cmovgt ; 0x29DC2 cmovle
        I8_new = s32(I << 3)                                # 0x29DE0 mov r2,r24 ; 0x29DE4 shl 0x3,r24
        kp = fw_lerp(cal.kp_x, cal.kp_y, idx) & 0xFFFF      # 0x29DC6.. LERP 0xCB994 on idx ; 0x29E32 zxh
        P = s32(E * kp) >> 8                                # 0x29E36 mul r9,r8 ; 0x29E3E sar 0x8
        P = clamp(P, -cal.pcl_C61BC, cal.pcl_C61BC)         # 0x29E3A..0x29E5C (ld.hu 0x71bc)
        win = (st.Eprev + 768000) & 0xFFFFFFFF              # 0x29E5E ld.w gp-0x6cf8 ; 0x29E68 ; 0x29E72 sub
        Eref = E if win >= 1536001 else st.Eprev            # 0x29E74 cmp 0x177001 ; 0x29E7E cmovnc r16,r8,r27
        kd = fw_lerp(cal.kd_x, cal.kd_y, idx) & 0xFFFF      # 0x29E76.. LERP 0xCB7D4 on idx ; 0x29EDE zxh
        D = s32(s32(E - Eref) * kd) >> 3                    # 0x29EE2 sub r27,r8 ; 0x29EE4 mul ; 0x29EEC sar 3
        D = clamp(D, -cal.dcl_C61B6, cal.dcl_C61B6)         # 0x29EE8..0x29F06 (ld.hu 0x71b6)
        raw = s32((I >> 7) + P + D)                         # 0x29F18 sar 0x7,r2 ; 0x29F1E add r9,r2 ; 0x29F24 add r8,r2
        ov = (e4_field == 2)                                # r25 = (gp-0x6803 == 2), set at 0x29A82
        fa = fw_lerp(*(cal.tA if ov else cal.tB), dbar6)    # 0x29F08 / 0x29F78 banks 0xCBB54 / 0xCBC34 on gp-0x6830 (r21)
        fc = fw_lerp(*(cal.tC if ov else cal.tD), bar5)     # 0x29FE2 / 0x2A04A banks 0xCBAE4 / 0xCBBC4 on gp-0x682f (r1)
        f = ((fa * fc) & 0xFFFF) >> 8                       # 0x2A0B4 mulu ; 0x2A0B8 andi 0xffff ; 0x2A0BC sar 8
        S = s32(raw * f) >> 8                               # 0x2A0BE mul r2,r12 ; 0x2A0C2 sar 8
        sc = cal.scl_C61BE & 0xFFFF                         # 0x2A13E ld.hu 0x71be (compare) ; 0x2A146 ld.h (assign)
        S = sc if S > sc else (-sc if S < -sc else S)
        o.update(E=E, e5=e5, exc=exc, I=I, kp=kp, P=P, kd=kd, D=D, raw=raw, taper=f, S=S)
        st.I8 = I8_new                                      # 0x2A190 st.w r24,gp-0x6dd0
        st.Eprev = E                                        # 0x2A18C st.w r16,gp-0x6cf8
    else:
        S = 0                                               # 0x2A164..0x2A172: r24=r29=r27=r22=0, r12=0
        st.I8 = 0                                           # 0x2A190 st.w r24(=0)  -> I RESET
        st.Eprev = 0x7FFFFFFF                               # 0x2A16C mov 0x7fffffff,r16 ; 0x2A18C st.w
        o.update(E=0, I=0, P=0, D=0, raw=0, taper=0, S=0)
    # ---- output lag (runs on BOTH paths) ----
    ob = cal.ob_C63EE & 0xFFFF                              # 0x2A174 ld.hu 0x73ee
    Lold = st.L                                             # 0x2A178 ld.w gp-0x3d3c
    t1 = s32(S * ob) >> 10                                  # 0x2A180 mul r7,r12 ; 0x2A1A0 sar 0xa
    t2 = s32(cal.oa_C63EC * Lold) >> 10                     # 0x2A184 ld.h 0x73ec ; 0x2A194 mul ; 0x2A1A6 sar 0xa
    Lnew = s32(t1 + t2)                                     # 0x2A1A8 add r12,r7
    y = s32(Lold + Lnew) >> 5                               # 0x2A1AA add r7,r9 ; 0x2A1AC sar 0x5
    st.L = Lnew                                             # 0x2A1B0 st.w gp-0x3d3c
    # ---- gate (armed only while ramping DOWN: gp-0x6806 == 0) and the ramp ----
    gated = False
    if cal.garm_C64A3 == 1 and not ramping_up:              # 0x2A198 ld.bu 0x74a3 ; 0x2A1B6 ld.bu gp-0x6806
        ys = ((y & 0xFFFF) ^ 0x8000) - 0x8000               # 0x2A1C4 sxh
        if (-cal.gthr_C61B8 <= ys <= cal.gthr_C61B8) or s32(y * st.yr_prev) <= 0:   # 0x2A1C6..0x2A1E0
            gated = True
    yr = 0 if gated else ((((s32(y * ramp) >> 15) & 0xFFFF) ^ 0x8000) - 0x8000)    # 0x2A1E6 mul ; sar 0xf ; sxh
    st.yr_prev = yr                                         # 0x2A206 st.h gp-0x6b30
    addend = 0                                              # r11 = gp-0x6b2c dither: its LERP Y (0xC673E..) is 0,0,0,0
    t = s32((addend + yr) * s32(pol * cal.gain_C6CD0)) >> 15   # 0x2A1F6 mulh ; 0x2A1FC add ; 0x2A1FE mul ; 0x2A202 sar 0xf
    T = clamp(t, -cal.ocl_C61B4, cal.ocl_C61B4)             # 0x2A204..0x2A220 (ld.hu compare, ld.h +assign)
    o.update(y=y, yr=yr, T=T)                               # 0x2A23C st.h gp-0x6b38 (the 427 tap source)
    return o


def full_tick(wire, x, st, cal, engaged=True, **kw):
    r26, ok = fb_former(x, st, cal)
    idx, sgn, sp = demand(wire, cal)
    o = pid_tick(sp, idx, r26, st, cal, run=(engaged and ok), **kw)
    o.update(r26=r26, idx=idx, sp=sp)
    return o


# ------------------------------------------------------------------------------------------------------
# cross-check against the golden model (an implementation written from the traces, not from this listing)
# ------------------------------------------------------------------------------------------------------
def golden_crosscheck(cal, n=20000, seed=1, ki=0, kd_y=None, dcl=None):
    sys.path.insert(0, str(HERE.parents[2] / "model"))
    import eps_lkas_chain_model as M
    gcal = replace(M.Calibration(), fb_clamp=cal.C_C62E6, fb_lag_a=cal.a_C63E8, fb_lag_b=cal.b_C63EA,
                   kp_y=cal.kp_y, kd_y=cal.kd_y if kd_y is None else kd_y, pid_d_clamp=cal.dcl_C61B6 if dcl is None else dcl,
                   fb_op=cal.fb_op_28FA4, e_shift=cal.e_shift_29D76, pid_ki=ki, assist_map_y=cal.map_y)
    mycal = replace(cal, ki_C63E6=ki, kd_y=cal.kd_y if kd_y is None else kd_y, dcl_C61B6=cal.dcl_C61B6 if dcl is None else dcl)
    rng = random.Random(seed)
    gst, st = M.EpsState(), St()
    st.sentinel = 1; gst_live = True
    x, idx = 0, 0
    mism = 0
    for k in range(n):
        x = clamp(x + rng.randint(-40, 40), -3000, 3000)
        if k % 10 == 0:
            idx = clamp(idx + rng.randint(-8, 8), 0, 240)
        sgn = 1 if (k // 3000) % 2 == 0 else -1
        sp = sgn * fw_lerp(cal.map_x, cal.map_y, idx)
        r26, _ = fb_former(x, st, mycal)
        g26 = M.lkas_fb_lag(x, gst, gcal, lane_live=gst_live)
        gst_live = True
        o = pid_tick(sp, idx, r26, st, mycal)
        g = M.lkas_rate_pid_tick(sp, g26, idx, gst, gcal, taper=254)
        keys = [("E", "E"), ("I", "I"), ("P", "P"), ("D", "D"), ("S", "S"), ("y", "y"), ("T", "T")]
        if r26 != g26 or any(o[a] != g[b] for a, b in keys):
            mism += 1
    return mism


def main():
    imgs = load()
    cals = {k: read_cal(v[0]) for k, v in imgs.items()}
    c = cals["v294"]
    out = {}
    print("V294 cal read from the image:", {k: v for k, v in c.__dict__.items() if not isinstance(v, tuple)})

    # ---- 0. cross-check vs the golden model: V294 as built, and with Ki / Kd made live ----
    for label, kw in (("V294 as built", {}), ("V294 + Ki 64", {"ki": 64}), ("V294 + Kd 128, Dclamp 10240", {"kd_y": (128,) * 4, "dcl": 10240}),
                      ("V294 + Ki 8 + Kd 64", {"ki": 8, "kd_y": (64,) * 4, "dcl": 10240})):
        m = golden_crosscheck(c, **kw)
        print(f"golden-model cross-check, {label}: {m} mismatching ticks of 20000")
        out[f"crosscheck:{label}"] = m

    # ---- 1. demand scale ----
    rows = []
    for w in (0, 16, 17, 100, 150, 161, 500, 1000, 2000, 3000, 3870, 4000):
        ip, _, spp = demand(w, c)
        im, _, spm = demand(-w, c)
        rows.append((w, ip, spp, im, spm))
    print("\nDEMAND: wire -> (idx, sp) for +wire and -wire (sign of sp = -sign(wire) by the x(-4) handler):")
    for r in rows:
        print(f"   wire {r[0]:+6d}: idx {r[1]:3d} sp {r[2]:+6d}   | wire {-r[0]:+6d}: idx {r[3]:3d} sp {r[4]:+6d}")
    asym = sum(1 for w in range(1, 3900) if demand(w, c)[0] != demand(-w, c)[0])
    print(f"   L/R asymmetry: idx(+w) != idx(-w) for {asym} of 3899 wire values (the double floor on negative products)")
    out["demand_rows"] = rows; out["demand_asym"] = asym

    # ---- 2. the steady surface and physical constants ----
    tap = 254
    T_per_S = tap / 256 * (2 * c.ob_C63EE / ((1024 - c.oa_C63EC) * 32)) * c.gain_C6CD0 / 32768
    DCs = c.b_C63EA / (1024 - c.a_C63E8)
    r26_per_alpha = DCs * X_PER_DEGS * TS                       # counts of r26 per deg/s^2 (below the pole)
    kp = c.kp_y[0]
    K_alpha_T = kp / 256 * r26_per_alpha * T_per_S              # T counts per deg/s^2
    ff_T_per_sp = kp / 256 * (1 << c.e_shift_29D76) * T_per_S
    alpha_ref_per_sp = (1 << c.e_shift_29D76) / r26_per_alpha
    print(f"\nCONSTANTS (V294, at rest taper {tap}):  T per S-count {T_per_S:.5f} | DC of s {DCs:.4f} per x-count"
          f" | r26 per deg/s^2 {r26_per_alpha:.5f} | 1 r26 count = {1 / r26_per_alpha:.3f} deg/s^2")
    print(f"   K_alpha = {K_alpha_T:.4f} T-counts per deg/s^2 (below the {(-__import__('math').log(c.a_C63E8 / 1024) / (2 * 3.14159265 * TS)):.2f} Hz pole)")
    print(f"   FF = {ff_T_per_sp:.4f} T per sp count = {ff_T_per_sp * 4.3:.3f} T per idx ; alpha_ref (E = 0) = {alpha_ref_per_sp:.3f} deg/s^2 per sp count")
    out["consts"] = dict(T_per_S=T_per_S, DCs=DCs, r26_per_alpha=r26_per_alpha, K_alpha_T=K_alpha_T,
                         ff_T_per_sp=ff_T_per_sp, alpha_ref_per_sp=alpha_ref_per_sp)

    # ---- 3. THE I TERM: what a non-zero Ki does on V294, marched on the exact tick ----
    print("\nI TERM on V294 (Ki != 0), wheel held still (x = 0), command held at idx, EPS alone (no outer loop):")
    print("   deadband 0xC62E4 = %d on E>>5  ->  exc = 0 while -%d <= E>>5 <= %d, i.e. E in [%d, %d]"
          % (c.db_C62E4, c.db_C62E4, c.db_C62E4, -c.db_C62E4 * 32, (c.db_C62E4 + 1) * 32 - 1))
    #   (E >> 5 floors toward -inf, so the dead band is ASYMMETRIC: e5 >= -4 <=> E >= -128 ; e5 <= 4 <=> E <= 159)
    irows = []
    for ki in (8, 32, 64, 256):
        cc = replace(c, ki_C63E6=ki)
        for idx_hold in (10, 23, 58, 120):
            st = St(); st.sentinel = 1
            sp = fw_lerp(c.map_x, c.map_y, idx_hold)
            t_rail, T0, T1, T5 = None, None, None, None
            for k in range(1, 20001):
                o = pid_tick(sp, idx_hold, 0, st, cc)
                if k == 1:
                    T0 = o["T"]
                if k == 1000:
                    T1 = o["T"]
                if k == 5000:
                    T5 = o["T"]
                if t_rail is None and abs(o["I"]) >= (((cc.icl_C61BA << 10) >> 3)):
                    t_rail = k / 1000
            ffT = pid_surface_T(sp, idx_hold, c)
            irows.append((ki, idx_hold, sp, ffT, T1, T5, o["T"], t_rail))
            print(f"   Ki {ki:4d} idx {idx_hold:3d} sp {sp:5d}: FF-only T {ffT:5d} | T @1 s {T1:5d} @5 s {T5:5d} @20 s {o['T']:5d}"
                  f" | I clamp reached at {t_rail if t_rail else '>20'} s")
    out["I_rows"] = irows
    # the rate component of I: telescoping sum of r26 = s_N - s_0
    print("   rate part of I (above the deadband): S_I,rate = -(Ki/8)(1/32)(1/128) * (s - s_reset) = -%.6f*Ki per deg/s of lagged rate"
          % (DCs * X_PER_DEGS / (8 * 32 * 128)))
    # floor asymmetry of the I input: symmetric +-E around the deadband
    for ki in (1, 4, 8, 12):
        cc = replace(c, ki_C63E6=ki)
        acc = {}
        for sgn in (1, -1):
            st = St(); st.sentinel = 1
            for k in range(1000):
                # E = sgn*200 exactly: sp chosen with shl 2 -> sp = 50, r26 = 0
                pid_tick(sgn * 50, 11, 0, st, cc)
            acc[sgn] = st.I8 >> 3
        print(f"   floor asymmetry, Ki {ki:2d}: I after 1 s at E=+200: {acc[1]:+7d} ; at E=-200: {acc[-1]:+7d}  (sum {acc[1] + acc[-1]:+d})")

    # ---- 4. THE D TERM: setpoint kick and jerk feedback ----
    print("\nD TERM on V294 (Kd != 0, D clamp != 0):")
    for kd in (32, 128, 512):
        cc = replace(c, kd_y=(kd,) * 4, dcl_C61B6=10240)
        st = St(); st.sentinel = 1
        # command staircase: +7 idx per 10 ms frame (the 123-count slew cap), wheel still
        Ts, Ds = [], []
        idx = 10
        for k in range(300):
            if k % 10 == 0 and k > 0:
                idx = min(idx + 7, 240)
            sp = fw_lerp(c.map_x, c.map_y, idx)
            o = pid_tick(sp, idx, 0, st, cc)
            Ts.append(o["T"]); Ds.append(o["D"])
        st0 = St(); st0.sentinel = 1
        T0s = []
        idx = 10
        for k in range(300):
            if k % 10 == 0 and k > 0:
                idx = min(idx + 7, 240)
            sp = fw_lerp(c.map_x, c.map_y, idx)
            T0s.append(pid_tick(sp, idx, 0, st0, c)["T"])
        dT = [a - b for a, b in zip(Ts, T0s)]
        print(f"   Kd {kd:4d}: D kick per 7-idx step max {max(Ds):6d} S (clamp {cc.dcl_C61B6}) ; delivered T minus Kd-0 T: "
              f"mean {sum(dT[100:]) / 200:+.1f}, max {max(dT):+d} T-counts ; jerk-feedback gain {kd / 8 * r26_per_alpha * TS:.2e} S per deg/s^3")

    # ---- 5. feedback former (a, b) grid ----
    import math
    print("\nFB FORMER grid: pole a (0xC63E8, ld.h, <= 1023), gain b (0xC63EA, ld.hu):")
    print("   a     b     pole Hz  DC_s    r26/(deg/s^2)  1 r26 count=deg/s^2  K_alpha T/(deg/s^2) @Kp960  a*s_max margin vs 2^31")
    grid = []
    for a in (923, 975, 993, 1005, 1011, 1017):
        for b in (567, 1134, 2268):
            dcs = b / (1024 - a)
            smax = b * 12000 / (1024 - a)
            margin = 2 ** 31 / (a * smax)
            ra = dcs * X_PER_DEGS * TS
            ka = 960 / 256 * ra * T_per_S
            grid.append((a, b, -math.log(a / 1024) / (2 * math.pi * TS), dcs, ra, 1 / ra, ka, margin))
            print(f"   {a:4d} {b:5d}  {grid[-1][2]:6.2f}  {dcs:7.2f}  {ra:10.4f}  {1 / ra:12.3f}  {ka:12.4f}  {margin:10.2f}{'  OVERFLOW' if margin < 1 else ''}")
    out["fb_grid"] = grid

    # ---- 6. output lag grid ----
    print("\nOUTPUT LAG (0xC63EC a, ld.h ; 0xC63EE b, ld.hu): DC = 2b/((1024-a)*32); one-pole phase/|H| at f:")
    for a in (960, 976, 992, 1000, 1008):
        b = round(0.990234375 * 16 * (1024 - a))
        p = -math.log(a / 1024) / (2 * math.pi * TS)
        ph = {f: -math.degrees(math.atan(f / p)) for f in (1, 2, 3, 5, 10, 20)}
        print(f"   a {a:4d} b {b:4d}: pole {p:5.2f} Hz, DC {2 * b / ((1024 - a) * 32):.5f}, phase " +
              " ".join(f"{f}Hz {v:+.0f}" for f, v in ph.items()))

    # ---- 7. overflow bounds for each multiply ----
    Emax = (1032 << c.e_shift_29D76) + 0xFFFF
    print(f"\nOVERFLOW: |E| <= 1032<<{c.e_shift_29D76} + C(<=65535) = {Emax}:  P: |E|*Kp(<=65535) = {Emax * 65535:.3e} "
          f"{'< 2^31 OK' if Emax * 65535 < 2 ** 31 else '>= 2^31 -> OVERFLOW possible'} ; at C=1024: {((1032 << 2) + 1024) * 65535:.3e}")
    print(f"   I: |E>>5|*Ki <= {(Emax >> 5) * 65535:.3e} ; I<<3 <= {((65535 << 10) >> 3) << 3} (< 2^31) ; "
          f"D: |dE|*Kd <= {2 * Emax * 65535:.3e}")
    (HERE / "_scratch" / "out").mkdir(exist_ok=True)
    (HERE / "_scratch" / "out" / "c3_tables.json").write_text(json.dumps(out, indent=1, default=str))


def pid_surface_T(sp, idx, cal, ticks=3000):
    st = St(); st.sentinel = 1
    o = None
    for _ in range(ticks):
        o = pid_tick(sp, idx, 0, st, cal)
    return o["T"]


if __name__ == "__main__":
    main()
