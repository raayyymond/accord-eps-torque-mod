"""Integer-exact mirror of the torque-sensor assist lane: ROM record -> gp-0x6b82.

Every line is annotated with the V850 instruction address it mirrors.  Constants are
read little-endian from the stock image.  gp = 0xFEDF8000, tp = 0xBF000.

Chain:  FUN_000382d8 (ROM record, speed-interp)
     -> FUN_000389ec (speed-cap remap + slot fill)
     -> FUN_000352b4 (map build, breakpoint search, LERP, slew selector)
"""
import struct, os

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', 'C:/Users/dudei/Desktop/Projects/accord-firmwares')
IMG = os.path.join(FW, 'analysis-2020accord', 'stock_fw_dump', 'code.bin')
_B = open(IMG, 'rb').read()
u16 = lambda a: struct.unpack_from('<H', _B, a)[0]
s16 = lambda a: struct.unpack_from('<h', _B, a)[0]
u32 = lambda a: struct.unpack_from('<I', _B, a)[0]

TP = 0xBF000

# ---- cals (all little-endian reads from the stock image) -------------------
CAL_7178 = s16(TP + 0x7178)   # 0xC6178 = 5274   slot ceiling
CAL_713A = u16(TP + 0x713A)   # 0xC613A = 1159
CAL_713C = u16(TP + 0x713C)   # 0xC613C = 14490  X-ish[9] default
CAL_7200 = u16(TP + 0x7200)   # 0xC6200 = 8192   Y-ish[9] default AND the +/-8192 torque clamp
CAL_7468 = u16(TP + 0x7468)   # 0xC6468 = 2639
CAL_7384 = u16(TP + 0x7384)   # 0xC6384 = 2048   max map slope, Q10 (=2.000)

SPD_CAP_X = [u16(TP + 0x769A + 2 * i) for i in range(7)]   # speed counts
SPD_CAP_Y = [u16(TP + 0x76A8 + 2 * i) for i in range(7)]   # torque-axis cap
BOOST_X = [u16(TP + 0x7B66 + 2 * i) for i in range(13)]    # |angle| * 0.1 deg
BOOST_Y = [u16(TP + 0x7B80 + 2 * i) for i in range(13)]

REC_PTR_BASES = [0xC7B40, 0xC7C28, 0xC7D10, 0xC7DF8, 0xC7EE0, 0xC7FC8, 0xC80B0]
SPD_BKPT_BASE = 0xCC9FC

# ---- biquad (FUN_000352b4 @ 0x35a28), stock float32 coefficients ----------
BQ_A1 = struct.unpack_from('<f', _B, TP + 0x70A8)[0]   # 0xC60A8 = -1.5372
BQ_A2 = struct.unpack_from('<f', _B, TP + 0x70AC)[0]   # 0xC60AC =  0.63462
BQ_B1 = struct.unpack_from('<f', _B, TP + 0x70B0)[0]   # 0xC60B0 = -1.8808
BQ_C4 = struct.unpack_from('<f', _B, TP + 0x70B4)[0]   # 0xC60B4 =  0.81731


def _sxh(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def rom_records(mode):
    """The 7 speed-indexed ROM records for `mode`.  rec[0]=N, rec[1..9]=A, rec[10..18]=B."""
    out = []
    for base in REC_PTR_BASES:
        p = u32(base + mode * 4)
        out.append(([s16(p + 2 * k) for k in range(1, 10)],      # A  -> gp-0x6350
                    [s16(p + 2 * k) for k in range(10, 19)]))    # B  -> gp-0x630c
    return out


def speed_breakpoints(mode):
    p = u32(SPD_BKPT_BASE + mode * 4)
    return [s16(p + 2 * k) for k in range(7)]


# ---------------------------------------------------------------------------
# FUN_000382d8 : interpolate the ROM record across the speed breakpoints.
# ---------------------------------------------------------------------------
def stage_382d8(mode, speed_cnt):
    """-> (A[0..8] @ gp-0x6350, B[0..8] @ gp-0x630c)"""
    bk = speed_breakpoints(mode)
    recs = rom_records(mode)
    i = 0                                          # 0x000382f6  while bk[i] <= speed
    while i <= 6 and bk[i] <= speed_cnt:
        i += 1
    if i == 0:
        A, B = list(recs[0][0]), list(recs[0][1])  # 0x0003830c  record 0 verbatim
    elif i == 7:
        A, B = list(recs[6][0]), list(recs[6][1])  # 0x0003843a  record 6 verbatim
    else:                                          # 0x00038520  LERP between i-1 and i
        A0, B0 = recs[i - 1]
        A1, B1 = recs[i]
        num = speed_cnt - bk[i - 1]
        den = bk[i] - bk[i - 1]
        A = [A0[k] + (((A1[k] - A0[k]) * num) // den) for k in range(9)]
        B = [B0[k] + (((B1[k] - B0[k]) * num) // den) for k in range(9)]
    for k in range(1, 9):                          # 0x00038740  8 monotone rungs on B
        if B[k] < B[k - 1]:
            B[k] = B[k - 1]
    return A, B


def _lerp_u16(x, X, Y):
    """The firmware's own u16 table walk (0x389f4 / 0x35844 shape)."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    k = 1
    while X[k] <= x:
        k += 1
    return ((Y[k] - Y[k - 1]) * (x - X[k - 1])) // (X[k] - X[k - 1]) + Y[k - 1]


# ---------------------------------------------------------------------------
# FUN_000389ec : speed-cap remap, then the slot fill that writes Xsrc/Ysrc.
# ---------------------------------------------------------------------------
def stage_389ec(A, B, speed_cnt, angle_10deg, k1=1024, k2=1024):
    """-> (Xsrc[0..9] @ gp-0x6430.., Ysrc[0..9] @ gp-0x6444..)  both 10 entries, [0]=0."""
    cap = _lerp_u16(speed_cnt, SPD_CAP_X, SPD_CAP_Y)                # 0x000389f4
    boost = 1024 if angle_10deg >= 0x2711 else _lerp_u16(angle_10deg, BOOST_X, BOOST_Y)
    a = [(A[j] << 10) // k1 for j in range(9)]                      # 0x00038b8x
    bb = [(B[j] * k2) >> 10 for j in range(9)]
    Xi = [0] * 10                                                   # gp-0x373c[]  A-ish, torque axis
    Yi = [0] * 10                                                   # gp-0x3714[]  B-ish, assist axis
    j = 1
    while j < 9:                                                    # 0x00038c40
        if a[j] < cap:
            Xi[j] = a[j]
            y = bb[j]
            if j == 8:
                Xi[8] = cap
            y = max(y, Yi[j - 1])
            y = min(y, CAL_7200)
            Yi[j] = y
            j += 1
        else:                                                       # 0x00038d1c
            Xi[j] = cap
            num = ((bb[j] - bb[j - 1]) * 0x10000) >> 6
            den = (a[j] - a[j - 1]) or 1
            t = ((num // den) * (cap - a[j - 1]) * 0x40) >> 16
            y = (t if t > -1 else 0) + bb[j - 1]
            y = min(max(y, Yi[j - 1]), CAL_7200)
            Yi[j] = y
            for m in range(j + 1, 9):                               # 0x00038e10 replicate forward
                Xi[m] = Xi[j]
                Yi[m] = Yi[j]
            break
    Xi[9] = max(CAL_713C, Xi[8])                                    # 0x00038f10
    Yi[9] = CAL_7200
    SCALE = (((CAL_7468 * CAL_713A) >> 7) << 10) // boost            # 0x00038fd8
    INV = 0x1000000 // CAL_7468                                      # 0x00038fe6
    Xsrc = [0] * 10
    Ysrc = [0] * 10
    for j in range(1, 10):                                           # 0x00039054
        Xsrc[j] = Yi[j]                                              # 0x00039028
        t = (Yi[j] * SCALE) >> 18                                    # 0x39054 mulu ; 0x39064 shr 0x12
        d = _sxh(Xi[j] - t)                                          # 0x39066 sub ; 0x39068 sxh
        d = _sxh((d * INV) >> 14)                                    # 0x3906a mul ; 0x3906e sar 0xe
        if d < 0:
            d = 0                                                    # 0x39074 bge -> st.h r0
        elif d > CAL_7178:
            d = CAL_7178                                             # 0x3908e ble -> else 5274
        Ysrc[j] = d
    return Xsrc, Ysrc


# ---------------------------------------------------------------------------
# FUN_000352b4 : build the 10-point map, then search + LERP + slew-select.
# ---------------------------------------------------------------------------
def build_map(Xsrc, Ysrc, gp69a0=1024):
    """-> X[0..9] @ gp-0x37fc, Y[0..9] @ gp-0x37e8, Z[0..9] @ gp-0x3810, S[1..9] @ gp-0x37d6+2j"""
    X = [0] * 10
    Y = [0] * 10
    Z = [0] * 10
    S = [0] * 10
    slope = 0.0
    for j in range(1, 10):
        seed = Xsrc[j]                                               # 0x0003535c FUN_000352a0
        X[j] = X[j - 1] + 1 if seed <= X[j - 1] else seed
        dy = Ysrc[j] / 1024.0 - Y[j - 1] / 1024.0                    # 0x00035368..0x00035390
        dx = X[j] / 1024.0 - X[j - 1] / 1024.0
        slope = dy / dx if dx else 0.0
        ynew = Ysrc[j] if slope >= 0.0 else Y[j - 1]                 # 0x00035394 cmovh
        if slope < 0.0:
            slope = 0.0
        if slope >= CAL_7384 / 1024.0:                               # 0x000353ac
            slope = CAL_7384 / 1024.0
            X[j] = int((X[j - 1] / 1024.0 + dy / slope) * 1024.0) & 0xFFFF
            if X[j] > CAL_7200:                                      # 0x000353e8
                X[j] = X[j - 1] + 1 if CAL_7200 <= X[j - 1] else CAL_7200
                ynew = int(((X[j] / 1024.0 - X[j - 1] / 1024.0) * slope
                            + Y[j - 1] / 1024.0) * 1024.0) & 0xFFFF
        Y[j] = ynew                                                  # 0x00035432
        zr = ((((X[j] - X[j - 1]) * gp69a0 * 4) >> 12) + Z[j - 1]) & 0xFFFF   # 0x0003544a
        if zr < Y[j]:                                                # 0x00035466 bnh
            Z[j] = zr
            slope = gp69a0 / 1024.0
        else:
            Z[j] = Y[j]
            if Y[j - 1] != Z[j - 1]:                                 # 0x0003547a be
                d = X[j] / 1024.0 - X[j - 1] / 1024.0
                if d:
                    slope = (Y[j] / 1024.0 - Z[j - 1] / 1024.0) / d
        S[j] = int(slope * 1024.0) & 0xFFFF                          # 0x000354a6 / 0x354c6
    return X, Y, Z, S


def lane(Tsens, X, Y, Z, S, comp_6b4a=0, pol=-1):
    """Tsens = gp-0x4f60 (int16).  Mirrors 0x000354ce .. 0x000358fa."""
    t = max(-CAL_7200, min(CAL_7200, Tsens))                         # 0x000354ce
    v = comp_6b4a if -0x6400 <= comp_6b4a <= 0x6400 else 0           # 0x000354f6
    Tc = max(-0x6400, min(0x6400, t + v))                            # 0x0003550a
    aTc = abs(Tc)                                                    # 0x00035520
    i = 0                                                            # 0x00035528
    if X[0] <= aTc:
        i = 1
        while i <= 9 and X[i] <= aTc:
            i += 1
    if i == 10:
        a_q10 = S[9]                                                 # 0x00035554
        m = Y[9]
    else:
        a_q10 = S[i]                                                 # 0x00035568  -> gp-0x69a4
        m = ((Y[i] - Y[i - 1]) * (aTc - X[i - 1])) // (X[i] - X[i - 1]) + Y[i - 1]
    if not (-0x6400 <= Tsens <= 0x6400):                             # 0x000355b0
        a_q10 = 0
    sgn = 1 if Tc >= 0 else -1                                       # 0x000355e4
    m_cl = 0x3000 if m > 0x2FFF else m                               # 0x000355d4
    b7a = _sxh(m_cl * sgn * pol)                                     # 0x000355f8  -> gp-0x6b7a
    ext = (((aTc - X[9]) & 0xFFFF) * a_q10) >> 10                    # 0x35774 mulu ; 0x35786 shr
    if ext >= 0x3000:
        ext = 0x3000                                                 # 0x00035788
    zl = _lerp_u16(aTc, X, Z)                                        # 0x00035844
    ab7a = abs(b7a)
    step_on = zl < ab7a                                              # 0x00035892 setfc
    add = ext if (aTc > X[9] and step_on) else 0                     # 0x00035896
    s = _sxh(zl + add)                                               # 0x000358a4
    if (s & 0xFFFF) > 0x3000:
        s = 0x3000                                                   # 0x000358ac
    if s >= ab7a:
        s = ab7a                                                     # 0x000358ba cmovge
    s = _sxh(s * sgn * pol)                                          # 0x000358c2
    b82 = _sxh(s if step_on else b7a)                                # 0x000358d0 -> gp-0x6b82
    resid = _sxh(b7a - s)                                            # 0x000358d4
    resid = max(-0x3000, min(0x3000, resid))
    b84 = resid if step_on else 0                                    # 0x000358fa -> gp-0x6b84
    return dict(Tc=Tc, aTc=aTc, m=m, a_q10=a_q10, b7a=b7a, b82=b82, b84=b84,
                zl=zl, step_on=step_on, idx=i)


def biquad_response(f_hz, fs_hz, c4=None):
    """|H| and phase of  c4*(1 + b1 z^-1 + z^-2) / (1 + a1 z^-1 + a2 z^-2)."""
    import cmath
    c4 = BQ_C4 if c4 is None else c4
    z = cmath.exp(-2j * cmath.pi * f_hz / fs_hz)
    num = c4 * (1 + BQ_B1 * z + z * z)
    den = 1 + BQ_A1 * z + BQ_A2 * z * z
    return num / den
