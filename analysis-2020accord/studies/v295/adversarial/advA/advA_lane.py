# -*- coding: utf-8 -*-
"""advA_lane.py -- ADV-A's OWN integer mirror of the LKAS lane, FUN_00028ea6, written from the Ghidra listing
(V294 program /advC/_v294_..., dry-run disassembly this session; code bytes proven identical to the V295 FILE at 64
sites by a1_bytes.py and by the 0-byte code-region diff).  It does NOT import the golden model, the harness or the
build script.  Every cell is passed in from a1_cells.json (read from the image bytes).

Registers are 32-bit; every add/sub/mul keeps the LOW word (w32), every `sar` floors (Python >> floors).
"""
M32 = 0xFFFFFFFF


def w32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


def sxh(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def lerp(X, Y, x):
    """0x29D3x.. / 0x29DC6.. / 0x29E76..: flat below X[0] (`if x <= X[0]` -> Y[0]), flat at/above X[-1];
    else walk while X[i] <= x, then Y[i-1] + (Y[i]-Y[i-1])*(x-X[i-1]) divq (X[i]-X[i-1]) (divq TRUNCATES)."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    i = 1
    while X[i] <= x:
        i += 1
    num = (Y[i] - Y[i - 1]) * (x - X[i - 1])
    den = X[i] - X[i - 1]
    q = abs(num) // abs(den)
    q = -q if (num < 0) != (den < 0) else q
    return Y[i - 1] + q


class Lane:
    def __init__(self, c):
        self.c = c
        self.a = c["fb_a"]; self.b = c["fb_b"] & 0xFFFF; self.C = c["fb_clamp"] & 0xFFFF
        self.esh = c["e_shift"]; self.diff = c["fb_op"] == "diff"
        self.db = c["deadband"]; self.ki = c["ki"]; self.icl = w32((c["i_clamp"] << 10) >> 3)
        self.pcl = c["p_clamp"]; self.dcl = c["d_clamp"]
        self.scl_u = c["sum_clamp_u"]; self.scl_s = c["sum_clamp_s"]
        self.la = c["lag_a"]; self.lb = c["lag_b"] & 0xFFFF
        self.gate_arm = c["gate_arm"]; self.thr_s = c["gate_thr"]; self.thr_u = c["gate_thr"] & 0xFFFF
        self.gain = c["gain"]; self.tcl_u = c["t_clamp_u"]; self.tcl_s = c["t_clamp_s"]
        self.kp_x, self.kp_y = c["kp_x"], c["kp_y"]; self.kd_x, self.kd_y = c["kd_x"], c["kd_y"]
        self.map_x, self.map_y = c["map_x"], c["map_y"]
        self.reset()

    def reset(self):
        # cold boot: .data copy (golden model cites 0x89380/0x89384 zero sources); E_prev boots as whatever .data
        # holds -- modelled as the out-of-window sentinel, which is what every skip stores
        self.s = 0; self.sent = 0; self.I8 = 0; self.Eprev = 0x7FFFFFFF; self.o = 0; self.yr_prev = 0
        self.last = {}

    def sp_of(self, idx, sign):
        """0x29D6C `mulh r13,r16`: sp = (s16)sign * (s16)LERP(map, idx)"""
        return sxh(sign) * sxh(lerp(self.map_x, self.map_y, idx))

    def tick(self, x, sp, idx, m=254, pol=1, ramp=0x8000, gate_live=False, valid=True, addend=0):
        """one 1 kHz tick.  valid=False = any OTHER guard failing (bar range, polarity) -> same bail path.
        gate_live = (gp-0x6806 == 0).  Returns T; self.last holds every intermediate."""
        L = {}
        bail = (not valid) or not (-12000 <= x <= 12000) or pol == 0
        if bail:
            # 0x28F5A / 0x28F48 / 0x28F62 -> 0x290B0 : sentinel := 2 (decompile line 162-172), r26 := 0, PID skipped
            self.sent = 2
            r26 = 0
            L["r26_raw"] = None
        else:
            s_old = self.s if self.sent == 1 else 0                   # 0x28F66..0x28F84
            r7 = w32(sxh(x) * self.b)                                 # 0x28F86 ld.hu b ; 0x28F8E mul r16,r7,r0
            r9 = w32(sxh(self.a) * s_old)                             # 0x28F8A ld.h a  ; 0x28F92 mul r26,r9,r0
            L["bx"], L["as"] = r7, r9
            r7 >>= 10                                                 # 0x28F9A sar 0xa
            r9 >>= 10                                                 # 0x28FA0 sar 0xa
            s_new = w32(r9 + r7)                                      # 0x28FA2 add r7,r9
            r26 = w32(s_new - s_old) if self.diff else w32(s_new + s_old)  # 0x28FA4 subr r9,r26
            L["r26_raw"] = r26
            self.s = s_new                                            # 0x28FA8 st.w r9 (before the clamp resolves)
            if r26 > self.C:                                          # 0x28FA6 cmp r13,r26 ; ble
                r26 = self.C
            elif r26 < -self.C:                                       # 0x28FB2 subr ; cmp ; bge
                r26 = w32(-self.C)
            self.sent = 1
        L["r26"] = r26
        run = (not bail) and ramp != 0                                # line 766: (ramp != 0 || flag==1) && bVar3
        if run:
            E = w32(w32(sp << self.esh) - r26)                        # 0x29D76 shl ; 0x29D78 sub r26,r16
            e5 = E >> 5                                               # 0x29D7C
            exc = e5 - self.db if e5 > self.db else (e5 + self.db if e5 < -self.db else 0)
            I = w32((self.I8 >> 3) + (w32(exc * self.ki) >> 3))       # 0x29DA4..0x29DB4
            I = self.icl if I > self.icl else (w32(-self.icl) if I <= -self.icl else I)
            I8 = w32(I << 3)
            kp = lerp(self.kp_x, self.kp_y, idx) & 0xFFFF             # zxh r9
            pp = w32(E * kp)                                          # 0x29E36 mul r9,r8,r0
            P = pp >> 8                                               # 0x29E3E sar 0x8
            P = self.pcl if P > self.pcl else (w32(-self.pcl) if P < -self.pcl else P)
            kd = lerp(self.kd_x, self.kd_y, idx) & 0xFFFF
            r27 = self.Eprev if (-768000 <= self.Eprev <= 768000) else E   # 0x29E5E..: 0x177000 < prev+0xbb800 -> E
            D = w32(w32(E - r27) * kd) >> 3
            D = self.dcl if D > self.dcl else (w32(-self.dcl) if D < -self.dcl else D)
            Ssum = w32((I >> 7) + P + D)                              # 0x29F18 sar 7 ; adds
            S = w32(m * Ssum) >> 8                                    # 0x2A0BE mul r2,r12,r0 ; 0x2A0C2 sar 8
            if S > self.scl_u:                                        # 0x2A142 cmp (ld.hu) ; ble
                S = self.scl_s                                        # 0x2A146 ld.h
            elif S < -self.scl_u:                                     # 0x2A150..0x2A154
                S = sxh(-self.scl_u)                                  # 0x2A156..0x2A15C subr ; sxh
            else:
                S = sxh(S)                                            # 0x2A160 sxh r12
            self.Eprev = E; self.I8 = I8
            L.update(E=E, I=I, P=P, D=D, kp=kp, pp=pp, Ssum=Ssum, mS=w32(m * Ssum))
        else:
            S = 0; self.I8 = 0; self.Eprev = 0x7FFFFFFF               # 0x2A164..0x2A172
        L["S"] = S
        # ---- output lag 0x2A174..0x2A1B0
        p12 = w32(S * self.lb)                                        # 0x2A180 mul r7,r12,r0
        p7 = w32(sxh(self.la) * self.o)                               # 0x2A194 mul r9,r7,r0
        L["S_lb"], L["la_o"] = p12, p7
        o_new = w32((p12 >> 10) + (p7 >> 10))                         # 0x2A1A0/A6 sar 0xa ; 0x2A1A8 add
        y = w32(self.o + o_new) >> 5                                  # 0x2A1AA add ; 0x2A1AC sar 5
        self.o = o_new                                                # 0x2A1B0 st.w
        L["y"] = y
        # ---- output gate 0x2A198/0x2A1AE..0x2A1E4 (armed by cal 0xC64A3 == 1 AND gp-0x6806 == 0)
        zero = False
        if self.gate_arm == 1 and gate_live:
            if sxh(y) > self.thr_s:                                   # 0x2A1C6 cmp r6,r8 ; bgt 0x2A1D4
                zero = not (w32(y * self.yr_prev) > 0)                # 0x2A1D4..0x2A1E0
            elif y >= -self.thr_u:                                    # 0x2A1D0 cmp r8,r9 ; bge 0x2A1E2
                zero = True
            else:
                zero = not (w32(y * self.yr_prev) > 0)
        if zero:
            yr = 0
        else:
            L["y_ramp"] = w32(y * ramp)
            yr = sxh(w32(y * ramp) >> 15)                             # 0x2A1E6 mul r14,r9 ; sar 0xf ; sxh
        self.yr_prev = yr                                             # 0x2A206 st.h r9,-0x6b30
        k = w32(sxh(pol) * sxh(self.gain))                            # 0x2A1F6 mulh r7,r13
        t = w32(w32(addend + yr) * k) >> 15                           # 0x2A1FC add ; 0x2A1FE mul ; 0x2A202 sar 0xf
        L["y_gain"] = w32(w32(addend + yr) * k)
        if t > self.tcl_u:                                            # 0x2A204 cmp r16(ld.hu),r11 ; ble
            t = self.tcl_s                                            # 0x2A20C ld.h
        elif t < -self.tcl_u:
            t = w32(-self.tcl_u)
        L["T"] = t; L["yr"] = yr
        self.last = L
        return t
