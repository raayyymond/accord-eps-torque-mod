"""advb_lane.py -- ADV-B's OWN integer mirror of the LKAS lane of FUN_00028ea6 (V294/V295 code, byte-identical),
written from this agent's Ghidra decompile (`_ghidra_v294_FUN_00028ea6.c`, saved beside this file) with every cell
read LITTLE-ENDIAN FROM THE IMAGE FILE by advb_lib (never from a build script).  Addresses cite the decompile / listing.

Per 1 ms tick:
  demand   cmd  = clamp(-4*wire, +-0x4000)                                  FUN_00052676 (decompiled this session)
           bar5 = |bar>>5| (255 if > 254)                                   gp-0x682f, decompile l.135-139
           G    = LERP(opp-sign 0xCB8B4 | same-sign 0xCB924 bank, bar5)      l.807-906 (override arm off: 0xE4 b2 field = 0)
           act  = LERP(tp+0x7976 table, gp-0x6830)                          l.908-929
           prod = (((G*act) & 0xFFFF) * cmd) >> 16 ; v = prod >> 6         l.930-933
           idx  = |clamp(v, -[0xC64F1], +[0xC64F0])| ; sgn = -1 if v < 0   l.934-954
           sp   = sgn * LERP(map 0xC9A88 rec, idx)                          l.955-979
  fb       s_new = ((a*s)>>10) + ((x*b)>>10) ; r26 = clamp(s_new - s, +-C) l.85-96 (subr @0x28FA4)
  bar filt sb_new = ((sb*[0x73e2])>>5) + ((bar*[0x73e4])>>5) ; d = clamp((sb_new-sb)>>4, +-0x3200) ; g6830 = |d|>>6
  PID      E = (sp << sh) - r26 ; P = clamp((E*Kp)>>8, +-Pcl) ; I = D = 0 (Ki = 0, Kd = 0, D clamp 0 read)
           S = clamp(((((F1*F2)&0xFFFF)>>8) * P) >> 8, +-Scl)               l.1188-1210 ; F1 = LERP(0xCBC34, g6830), F2 = LERP(0xCBBC4, bar5)
  out lag  L' = ((la*L)>>10) + ((S*lb)>>10) ; y = (L + L')>>5 ; L = L'      l.1229-1233
  deliver  yr = (short)((y*ramp)>>15) ; T = clamp(((0 + yr)*pol*gain)>>15, +-Tcl)   l.1249-1270
  PID runs iff (ramp != 0 or req) and no filter bail; when skipped S = 0 (l.1212-1219).
"""
from advb_lib import lerp_rec, load, rec, s16, u16, u8


def lerp_walk(X, Y, x):
    """the firmware walk (decompile l.956-976): Y[0] if x <= X[0]; Y[-1] if x >= X[-1]; else trunc-toward-zero interp."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    j = 1
    while X[j] <= x:
        j += 1
    num = (Y[j] - Y[j - 1]) * (x - X[j - 1])
    den = X[j] - X[j - 1]
    q = abs(num) // abs(den)
    q = -q if (num < 0) != (den < 0) else q
    return Y[j - 1] + q


def cells_from_image(name_or_path, sha=None, sel=7):
    b, h = load(name_or_path, sha)
    c = dict(sha=h)
    c["a"] = s16(b, 0xC63E8); c["b"] = u16(b, 0xC63EA); c["C"] = u16(b, 0xC62E6)
    c["ki"] = u16(b, 0xC63E6); c["pcl"] = u16(b, 0xC61BC); c["scl"] = u16(b, 0xC61BE); c["dcl"] = u16(b, 0xC61B6)
    c["tcl"] = u16(b, 0xC61B4); c["la"] = s16(b, 0xC63EC); c["lb"] = u16(b, 0xC63EE); c["gain"] = s16(b, 0xC6CD0)
    c["idx_pos"] = u8(b, 0xC64F0); c["idx_neg"] = u8(b, 0xC64F1); c["cut"] = u8(b, 0xC64B8)
    c["bf9"] = u16(b, 0xC63E2); c["bf8"] = u16(b, 0xC63E4)
    hw = u16(b, 0x29D76); assert (hw >> 5) & 0x3F == 0x16; c["sh"] = hw & 31
    hw = u16(b, 0x28FA4); c["op"] = {0x0E: "sum", 0x0C: "diff"}[(hw >> 5) & 0x3F]
    # the forward-gain displacement at 0x2A1EE must point at tp+0x7cd0 (V57 lever) for c["gain"] to be the read cell
    c["gain_disp"] = u16(b, 0x2A1F0)
    _, c["map_X"], c["map_Y"] = lerp_rec(b, 0xC9A88, 10, sel)
    _, c["kp_X"], c["kp_Y"] = lerp_rec(b, 0xCB994, 5, sel)
    _, c["kd_X"], c["kd_Y"] = lerp_rec(b, 0xCB7D4, 4, sel)
    _, c["gopp_X"], c["gopp_Y"] = lerp_rec(b, 0xCB8B4, 4, sel)
    _, c["gsame_X"], c["gsame_Y"] = lerp_rec(b, 0xCB924, 4, sel)
    _, c["tB_X"], c["tB_Y"] = lerp_rec(b, 0xCBC34, 6, sel)
    _, c["tD_X"], c["tD_Y"] = lerp_rec(b, 0xCBBC4, 6, sel)
    # activity table at tp+0x7976 (count @0x7976? decompile: X[0] @0x7976, X[last] @0x797c, Y @0x797e..0x7984)
    c["act_X"] = [u16(b, 0xC6976 + 2 * i) for i in range(4)]
    c["act_Y"] = [u16(b, 0xC697E + 2 * i) for i in range(4)]
    c["lim_rec"] = rec(b, 0xCB844, sel)
    return c


class Lane:
    """one lane, pure Python ints.  tick() consumes wire (0xE4 counts), x (counts, |x| <= 12000), bar (firmware
    counts), req (0/1) and returns T.  Options: trim=False forces r26 = 0 (the NULL / FF-only march);
    inv=True negates r26 (the sign-leg control); b_override replaces b."""

    def __init__(self, c, pol=-1, trim=True, inv=False, b_override=None, bar_sign=+1):
        self.c = c
        self.pol = pol
        self.trim = trim
        self.inv = inv
        self.b = c["b"] if b_override is None else b_override
        self.bar_sign = bar_sign
        self.s = 0; self.sent = 0; self.sb = 0; self.L = 0; self.ramp = 0
        n = 256
        self.map_t = [lerp_walk(c["map_X"], c["map_Y"], i) for i in range(n)]
        self.kp_t = [lerp_walk(c["kp_X"], c["kp_Y"], i) for i in range(n)]
        self.gopp_t = [lerp_walk(c["gopp_X"], c["gopp_Y"], i) for i in range(n)]
        self.gsame_t = [lerp_walk(c["gsame_X"], c["gsame_Y"], i) for i in range(n)]
        self.tB_t = [lerp_walk(c["tB_X"], c["tB_Y"], i) for i in range(n)]
        self.tD_t = [lerp_walk(c["tD_X"], c["tD_Y"], i) for i in range(n)]
        self.act_t = [lerp_walk(c["act_X"], c["act_Y"], i) for i in range(n)]
        assert c["ki"] == 0 and all(y == 0 for y in c["kd_Y"]), "this mirror carries no I/D path"
        assert c["cut"] == 255

    def tick(self, wire, x, bar, req, want=False):
        c = self.c
        # ---- feedback former + bar filter (runs every tick; bails never occur on this route: asserted) ----
        assert -12000 <= x <= 12000 and -25600 <= bar <= 25600
        s_old = self.s if self.sent == 1 else 0
        sb_old = self.sb if self.sent == 1 else 0
        s_new = ((c["a"] * s_old) >> 10) + ((x * self.b) >> 10)
        r26 = s_new - s_old
        C = c["C"]
        r26 = C if r26 > C else (-C if r26 < -C else r26)
        self.s = s_new
        sb_new = ((sb_old * c["bf9"]) >> 5) + ((bar * c["bf8"]) >> 5)
        d = (sb_new - sb_old) >> 4
        d = 0x3200 if d > 0x3200 else (-0x3200 if d < -0x3200 else d)
        self.sb = sb_new
        self.sent = 1
        g6830 = min(abs(d) >> 6, 255)
        u = bar >> 5
        u = -u if u < 0 else u
        bar5 = u if u <= 254 else 255
        if not self.trim:
            r26 = 0
        elif self.inv:
            r26 = -r26
        # ---- ramp (gp-0x69b0): +33/tick while requested, to 0x8000; request off -> the lane is not scored ----
        if req:
            self.ramp = min(0x8000, self.ramp + 33)
        else:
            self.ramp = 0
        runs = (self.ramp != 0) or req
        if runs:
            cmd = -4 * wire
            cmd = 0x4000 if cmd > 0x4000 else (-0x4000 if cmd < -0x4000 else cmd)
            bs = self.bar_sign * bar
            same = (cmd < 0 and bs < 0) or (cmd >= 0 and bs >= 0)
            G = self.gsame_t[bar5] if same else self.gopp_t[bar5]
            act = self.act_t[g6830]
            prod = (((G * act) & 0xFFFF) * cmd) >> 16
            v = prod >> 6
            neg = v < 0
            if v > c["idx_pos"]:
                v = c["idx_pos"]
            elif v < -c["idx_neg"]:
                v = -c["idx_neg"]
            idx = (-v if v < 0 else v) & 0xFF
            sp = (-1 if neg else 1) * self.map_t[idx]
            E = (sp << c["sh"]) - r26
            kp = self.kp_t[idx]
            P = (E * kp) >> 8
            pcl = c["pcl"]
            P = pcl if P > pcl else (-pcl if P < -pcl else P)
            tf = ((self.tB_t[g6830] * self.tD_t[bar5]) & 0xFFFF) >> 8
            S = (tf * P) >> 8
            scl = c["scl"]
            S = scl if S > scl else (-scl if S < -scl else S)
        else:
            S = 0; sp = 0; P = 0; idx = 0; tf = 0
        L2 = ((c["la"] * self.L) >> 10) + ((S * c["lb"]) >> 10)
        y = (self.L + L2) >> 5
        self.L = L2
        yr = (y * self.ramp) >> 15
        yr = ((yr + 0x8000) & 0xFFFF) - 0x8000          # (short)
        T = (yr * self.pol * c["gain"]) >> 15
        tcl = c["tcl"]
        T = tcl if T > tcl else (-tcl if T < -tcl else T)
        if want:
            return T, r26, sp, P, S, idx, tf
        return T
