"""advp_lane.py -- the adversary's OWN byte-exact V294-class LKAS lane, written from the decompile + listing of
FUN_00028ea6 on the V294 image (Ghidra /advC program), NOT from the harness or the golden model.

Per 1 ms tick (V294: fb_op diff, e_shift 2, Ki = 0, Kd = 0, D clamp 0):
  s_new = ((a*s) >> 10) + ((b*x) >> 10) ; r26 = clamp(s_new - s, +-C) ; s = s_new        (0x28F86..0x28FBE)
  E     = (sp << 2) - r26                                                                (0x29D76 shl 2 ; 0x29D78 sub)
  kp    = kp_lerp(rec, idx)                                                              (0x29DC6..0x29E32, below)
  P     = clamp((E*kp) >> 8, +-Pcl)                                                       (0x29E36 mul ; 0x29E3E sar 8)
  S     = clamp((m*P) >> 8, +-Scl)                   (I>>7 = 0 and D = 0 on V294)        (0x2A0BE mul ; sar 8 ; clamp)
  L'    = ((la*L) >> 10) + ((S*lb) >> 10) ; y = (L + L') >> 5 ; L = L'                   (decompile: iVar23/iVar31/iVar34)
  T     = clamp(((y*ramp)>>15 sxh) * gain >> 15, +-Tcl)   ramp = 0x8000 engaged, pol cancels (applied as sign sg)
"""
import struct

A_FB, B_FB, C_FB = 1011, 567, 1024
PCL, SCL, TCL = 15360, 15360, 3072
LA, LB, GAIN = 992, 507, 5346
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)
MAP_Y = (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032)


def kp_lerp(X, Y, idx):
    """0x29DC6..0x29E32, instruction for instruction:
       cmp X0,idx ; bh  (idx > X0 unsigned) else Y0          0x29DEA/0x29DEC/0x29DEE
       cmp X4,idx ; bnc (idx >= X4)          -> Y4           0x29DF6/0x29DF8/0x29E04
       walk: k = first knot with X[k] > idx                 0x29DFA..0x29E12 (bnc loops while idx >= X[k])
       r9 = Y[k]-Y[k-1] (32-bit sub of two zero-extended halfwords) ; r7 = idx - X[k-1] ; mul (low 32)
       r6 = X[k]-X[k-1] ; divq r6,r9 (SIGNED, truncates toward zero) ; add Y[k-1] ; zxh"""
    if not idx > X[0]:
        return Y[0] & 0xFFFF
    if idx >= X[4]:
        return Y[4] & 0xFFFF
    k = 1
    while idx >= X[k]:
        k += 1
    num = (Y[k] - Y[k - 1]) * (idx - X[k - 1])
    num = ((num + 2 ** 31) % 2 ** 32) - 2 ** 31            # 32-bit
    den = X[k] - X[k - 1]
    q = abs(num) // den
    q = -q if num < 0 else q                               # signed divide, toward zero (den > 0 here)
    return (Y[k - 1] + q) & 0xFFFF


def map_lerp(idx, X=MAP_X, Y=MAP_Y):
    """0x29CFE.. 10-knot walk, same structure (decompile lines: X0 at rec+2, X9 at rec+0x14, Y at rec+0x16).
    Rising map -> trunc == floor."""
    if not idx > X[0]:
        return Y[0]
    if idx >= X[-1]:
        return Y[-1]
    k = 1
    while idx >= X[k]:
        k += 1
    num = (Y[k] - Y[k - 1]) * (idx - X[k - 1])
    den = X[k] - X[k - 1]
    q = abs(num) // den
    q = -q if num < 0 else q
    return Y[k - 1] + q


def kp_table(X, Y):
    return [kp_lerp(X, Y, i) for i in range(256)]


MAP_T = [map_lerp(i) for i in range(241)]


def march(sgn, idx, m, kpt, x1k=None, trim=True, C=C_FB, a=A_FB, b=B_FB, e_shift=2):
    """frames at 100 Hz (ZOH over 10 ticks); x1k the 1 kHz fb operand (counts, already clipped to +-12000).
    Returns T per tick (python list of ints)."""
    n = len(idx) * 10
    T = [0] * n
    s = 0
    L = 0
    sp_k = [int(sg) * MAP_T[int(i)] for sg, i in zip(sgn, idx)]
    kp_k = [kpt[int(i)] for i in idx]
    m_k = [int(v) for v in m]
    xs = x1k if (trim and x1k is not None) else None
    for i in range(n):
        k = i // 10
        r26 = 0
        if xs is not None:
            sn = ((a * s) >> 10) + ((b * xs[i]) >> 10)
            r26 = sn - s
            r26 = C if r26 > C else (-C if r26 < -C else r26)
            s = sn
        E = (sp_k[k] << e_shift) - r26
        P = (E * kp_k[k]) >> 8
        P = PCL if P > PCL else (-PCL if P < -PCL else P)
        S = (m_k[k] * P) >> 8
        S = SCL if S > SCL else (-SCL if S < -SCL else S)
        L2 = ((LA * L) >> 10) + ((S * LB) >> 10)
        y = (L + L2) >> 5
        L = L2
        v = (y * GAIN) >> 15
        T[i] = TCL if v > TCL else (-TCL if v < -TCL else v)
    return T


def surface(kpt, idx, r26=0, m=254, ticks=3000):
    """steady T at constant idx and constant r26, from L = 0 (cold boot); returns (T_last, L)."""
    sp = MAP_T[idx]
    E = (sp << 2) - r26
    P = max(-PCL, min(PCL, (E * kpt[idx]) >> 8))
    S = max(-SCL, min(SCL, (m * P) >> 8))
    L = 0
    seen = set()
    T = 0
    for _ in range(ticks):
        if L in seen:
            break
        seen.add(L)
        L2 = ((LA * L) >> 10) + ((S * LB) >> 10)
        y = (L + L2) >> 5
        L = L2
        T = max(-TCL, min(TCL, (y * GAIN) >> 15))
    return T, P, S


def quant(v):
    """427 tap: sign-magnitude, 8 counts per LSB (truncation toward zero)."""
    import numpy as np
    v = np.asarray(v, float)
    return np.sign(v) * (np.abs(v).astype(np.int64) >> 3) * 8.0
