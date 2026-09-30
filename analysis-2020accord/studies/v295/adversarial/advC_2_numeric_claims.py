# -*- coding: utf-8 -*-
"""ADV-C part 2 -- every numeric claim of the V295 docstring/report, re-derived from the BUILT IMAGE with my OWN
integer mirror of FUN_00028ea6 (written from the Ghidra decompile of the V294 program, whose code bytes are identical to
V295's).  No kit module imported (numpy only).  Every cell is read from the image by address; addresses are resolved
through the instructions that read them where it matters (0x28F86 b, 0x28F8A a, 0x2A1F0 the forward gain).

Mirror (decompile line refs are to scratchpad/dec_28ea6.c):
  s_new = (a*s_old >> 10) + ((x*b) >> 10)                  l.85-87   a = s16 tp+0x73E8, b = u16 tp+0x73EA
  r26   = clamp(s_new - s_old, -C, +C)                      l.88-96   C = u16 tp+0x72E6
  s_old := 0 when the sentinel gp-0x3d2c != 1               l.75-82   (cold boot, and the tick after a bail)
  sp    = sign * LERP(map[slot], idx)                       l.951-977
  E     = sp*4 - r26                                        l.980     (V294 shl 0x2)
  I     = 0   because Ki = u16 tp+0x73E6 = 0 and the state starts 0      l.996-1012
  P     = clamp((E*Kp) >> 8, +-u16 tp+0x71BC)               l.1039-1057, Kp = LERP(Kp[slot], |idx|)
  D     = clamp((dE*Kd) >> 3, +-u16 tp+0x71B6) = 0          l.1081-1097 (D clamp 0)
  S     = clamp((FADE * (I>>7 + P + D)) >> 8, +-u16 tp+0x71BE),  FADE = ((A*B) & 0xFFFF) >> 8    l.1188-1210
  Ln    = (LA*L >> 10) + ((S*LB) >> 10);  y = (L + Ln) >> 5   l.1220-1233  LA = s16 tp+0x73EC, LB = u16 tp+0x73EE
  yr    = (short)((y * RAMP) >> 15), RAMP = 0x8000 engaged  l.1249
  T     = clamp(((0 + yr) * dir * G) >> 15, +-u16 tp+0x71B4) l.1251-1270, G = s16 tp+0x7CD0 (via ld.h @0x2A1F0), dir = +1
ASSUMPTIONS carried (same as the build's golden-model mirror, stated not proved here): gp-0x6b2c hold term = 0,
gp-0x6752 dir = +1, ramp = 0x8000, fade indices at rest (0), variant slot 7.
Bail tick (l.161-170, 1212-1219): sentinel := 2, S := 0 into the output lag; the next tick reads s_old = 0.
"""
import cmath
import math
import struct
import sys

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
import glob                                                                              # noqa: E402
def ld(pat):
    g = [p for p in glob.glob(FW + pat) if "SUPERSEDED" not in p]
    assert len(g) == 1, g
    return open(g[0], "rb").read()


IMG = dict(stock=open(FW + "stock_fw_dump/code.bin", "rb").read(), v282=ld("_v282_*_plain_image.bin"),
           v293=ld("_v293_*_plain_image.bin"), v294=ld("_v294_*_plain_image.bin"), v295=ld("_v295_*_plain_image.bin"))
import hashlib                                                                           # noqa: E402
assert hashlib.sha256(IMG["v295"]).hexdigest() == "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
assert hashlib.sha256(IMG["v294"]).hexdigest() == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
TP, SLOT = 0xBF000, 7
FAILS, DEFECTS = [], []


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def s16(b, o): return struct.unpack_from("<h", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


def chk(cond, msg, defect=False):
    tag = "[ok]    " if cond else ("[DEFECT]" if defect else "[FAIL]  ")
    print("  " + tag + " " + msg)
    if not cond:
        (DEFECTS if defect else FAILS).append(msg)


def rec(b, p):
    n = u16(b, p)
    return [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def lerp(X, Y, x):
    """firmware LERP: x <= X0 -> Y0; x >= Xn -> Yn; else Y[k-1] + trunc((Y[k]-Y[k-1])*(x-X[k-1]) / (X[k]-X[k-1]))"""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    k = 1
    while X[k] <= x:
        k += 1
    num = (Y[k] - Y[k - 1]) * (x - X[k - 1])
    den = X[k] - X[k - 1]
    q = abs(num) // den
    return Y[k - 1] + (q if num >= 0 else -q)


def tp_load(b, site, signed):
    hw1, hw2 = u16(b, site), u16(b, site + 2)
    r1 = hw1 & 0x1F
    assert r1 == 5, f"0x{site:X} not tp-based"
    d = hw2 & 0xFFFE
    d = d - 0x10000 if d & 0x8000 else d
    a = TP + d
    return a, (s16(b, a) if signed else u16(b, a))


def cells(b):
    ab, bv = tp_load(b, 0x28F86, False)
    aa, av = tp_load(b, 0x28F8A, True)
    ag, G = tp_load(b, 0x2A1EE, True)
    mX, mY = rec(b, u32(b, 0xC9A88 + 4 * SLOT))
    kX, kY = rec(b, u32(b, 0xCB994 + 4 * SLOT))
    dX, dY = rec(b, u32(b, 0xCB7D4 + 4 * SLOT))
    fade = {}
    for na, ta in (("cbb54", 0xCBB54), ("cbc34", 0xCBC34)):
        for nb, tb in (("cbae4", 0xCBAE4), ("cbbc4", 0xCBBC4)):
            A = lerp(*rec(b, u32(b, ta + 4 * SLOT)), 0)
            B = lerp(*rec(b, u32(b, tb + 4 * SLOT)), 0)
            fade[(na, nb)] = ((A * B) & 0xFFFF) >> 8
    return dict(b=bv, b_addr=ab, a=av, a_addr=aa, G=G, G_addr=ag, C=u16(b, 0xC62E6), Ki=u16(b, 0xC63E6),
                PC=u16(b, 0xC61BC), DC=u16(b, 0xC61B6), SC=u16(b, 0xC61BE), OC=u16(b, 0xC61B4),
                LA=s16(b, 0xC63EC), LB=u16(b, 0xC63EE), mX=mX, mY=mY, kX=kX, kY=kY, dX=dX, dY=dY, fade=fade,
                subr=(u16(b, 0x28FA4) >> 5) & 0x3F == 0x0C, shl=u16(b, 0x29D76) & 0x1F)


c5, c4 = cells(IMG["v295"]), cells(IMG["v294"])
print("=" * 110)
for nm, c in (("V294", c4), ("V295", c5)):
    print(f" {nm}: b@0x{c['b_addr']:X}={c['b']} a@0x{c['a_addr']:X}={c['a']} C={c['C']} Ki={c['Ki']} PC={c['PC']} DC={c['DC']} "
          f"SC={c['SC']} OC={c['OC']} LA={c['LA']} LB={c['LB']} G@0x{c['G_addr']:X}={c['G']} subr={c['subr']} shl={c['shl']}")
    print(f"       map Y {c['mY']}  X {c['mX']};  Kp Y {c['kY']};  Kd Y {c['dY']};  fade {c['fade']}")
fades = set(c5["fade"].values())
chk(fades == {254}, f"FADE at rest is 254 for every (A,B) table pairing: {c5['fade']}")
FADE = 254
assert c5["Ki"] == 0 and c5["DC"] == 0 and c5["subr"] and c5["shl"] == 2 and len(set(c5["kY"])) == 1
KP = c5["kY"][0]


def sp_of(c, idx, sign):
    return sign * lerp(c["mX"], c["mY"], idx)


# ---------------------------------------------------------------- the vectorised lane (my code)
def march(c, x, sp, n, bail_at=None, keep=None):
    x = np.asarray(x, np.int64); sp = np.asarray(sp, np.int64)
    a, b, C = c["a"], c["b"], c["C"]
    s = np.zeros_like(x); L = np.zeros_like(x); sent = 0
    keep = set(range(n) if keep is None else keep)
    Tk, Rk = [], []
    mx = 0
    for t in range(n):
        if t == bail_at:
            sent = 2
            S = np.zeros_like(x); r26 = np.zeros_like(x)
        else:
            so = s if sent == 1 else np.zeros_like(x)
            p1, p2 = a * so, x * b
            mx = max(mx, int(np.abs(p1).max()), int(np.abs(p2).max()))
            sn = (p1 >> 10) + (p2 >> 10)
            r26 = np.clip(sn - so, -C, C)
            s = sn; sent = 1
            E = sp * 4 - r26
            pe = E * KP
            mx = max(mx, int(np.abs(pe).max()))
            P = np.clip(pe >> 8, -c["PC"], c["PC"])
            S = np.clip((FADE * P) >> 8, -c["SC"], c["SC"])
        q1, q2 = c["LA"] * L, S * c["LB"]
        mx = max(mx, int(np.abs(q1).max()), int(np.abs(q2).max()))
        Ln = (q1 >> 10) + (q2 >> 10)
        y = (L + Ln) >> 5
        L = Ln
        yr = (y * 0x8000) >> 15
        yr = ((yr + 0x8000) & 0xFFFF) - 0x8000
        T = np.clip((yr * c["G"]) >> 15, -c["OC"], c["OC"])
        if t in keep:
            Tk.append(T); Rk.append(r26)
    return np.array(Tk), np.array(Rk), mx


def surface(c, fb_const=0, n=4000):
    """T settled at constant sp with a CONSTANT r26 = fb_const (the golden-surface definition), idx 0..240, both signs."""
    idx = np.array([i for s in (1, -1) for i in range(241)]); sg = np.array([s for s in (1, -1) for _ in range(241)])
    sp = np.array([sp_of(c, int(i), int(s)) for i, s in zip(idx, sg)], np.int64)
    L = np.zeros_like(sp); Ts = []
    E = sp * 4 - fb_const
    P = np.clip((E * KP) >> 8, -c["PC"], c["PC"])
    S = np.clip((FADE * P) >> 8, -c["SC"], c["SC"])
    for t in range(n):
        Ln = ((c["LA"] * L) >> 10) + ((S * c["LB"]) >> 10)
        y = (L + Ln) >> 5
        L = Ln
        T = np.clip((y * c["G"]) >> 15, -c["OC"], c["OC"])
        if t >= n - 50:
            Ts.append(T)
    Ts = np.array(Ts)
    return idx, sg, Ts


print("\n [1] STATIC SURFACE at r26 = 0 (docstring: rail +2461/-2463, V295 == V294)")
i5, g5, T5 = surface(c5); _, _, T4 = surface(c4)
steady = bool(np.all(T5[-1] == T5[-2]) and np.all(T5.min(0) == T5.max(0)))
print(f"   settled (constant over the last 50 ticks on every lane): {steady}; lanes with a 1-count limit cycle: "
      f"{int(np.sum(T5.min(0) != T5.max(0)))}")
Tp = {int(i): int(t) for i, s, t in zip(i5, g5, T5[-1]) if s == 1}
Tn = {int(i): int(t) for i, s, t in zip(i5, g5, T5[-1]) if s == -1}
print("   idx   T(+)   T(-):", [(i, Tp[i], Tn[i]) for i in (0, 12, 32, 60, 120, 180, 238, 240)])
chk(Tp[240] == 2461 and Tn[240] == -2463, f"rail +{Tp[240]} / {Tn[240]}")
chk(np.array_equal(T5, T4), "V295 surface == V294 surface at r26 = 0 on all 482 lanes")
build_tbl = {0: (0, 0), 12: (124, -126), 32: (331, -332), 60: (617, -619), 120: (1237, -1239), 180: (1860, -1862),
             238: (2459, -2460), 240: (2461, -2463)}
chk(all((Tp[i], Tn[i]) == v for i, v in build_tbl.items()), "the build's printed T(+)/T(-) table reproduced at all 8 idx")
xs = np.array([i * 16.125736 for i in range(1, 239)])
slope = float(np.polyfit(xs, [Tp[i] for i in range(1, 239)], 1)[0])
print(f"   sub-rail slope (OLS, idx 1..238, x = idx*16.125736): {slope:.5f} T per wire count")
chk(round(slope, 4) == 0.6410, f"sub-rail slope {slope:.4f} (report 0.6410; the orchestrator's brief says 0.6409)")
if round(slope, 4) != 0.6409:
    DEFECTS.append(f"brief/decision text quotes the sub-rail slope as 0.6409; the image gives {slope:.5f} (rounds to 0.6410)")
_, _, Tc5p = surface(c5, fb_const=+c5["C"]); _, _, Tc5n = surface(c5, fb_const=-c5["C"])
_, _, Tc4p = surface(c4, fb_const=+c4["C"])
cap_p, cap_n = int(Tc5p[-1][0]), int(Tc5n[-1][0])
print(f"   zero-command trim cap at r26 = +C / -C: {cap_p} / {cap_n};  V294 at +C {int(Tc4p[-1][0])}")
chk(cap_p == -616 and cap_n == 615, "trim cap -616 / +615 (the docstring's '616 T trim cap')")

print("\n [2] CLOSED-FORM TRIM NUMBERS (docstring 0b / report sec.3)")
fwd = (FADE / 256) * (c5["LB"] / (1024 - c5["LA"]) / 16) * (c5["G"] / 32768)
print(f"   T per P-count = FADE/256 * LB/(1024-LA)/16 * G/32768 = {fwd:.5f}   (docstring: 0.1600)")
chk(abs(fwd - 0.1600) < 0.005, f"forward factor {fwd:.4f} ~ 0.1600", defect=True)
if abs(fwd - 0.1600) >= 0.0005:
    DEFECTS.append(f"docstring 0b rounds the forward factor to 0.1600; the image gives {fwd:.5f} (cosmetic; K_alpha is computed "
                   f"with the exact value in [12])")
for nm, c in (("V294", c4), ("V295", c5)):
    beta, alpha = c["b"] / 1024, c["a"] / 1024
    ka = (KP / 256) * c["b"] / (1024 - c["a"]) * 1e-3 * 8 * fwd
    def px(f):
        z = cmath.exp(1j * 2 * math.pi * f * 1e-3)
        return (KP / 256) * abs(beta * (z - 1) / (z - alpha))
    pole = -math.log(alpha) / (2 * math.pi * 1e-3)
    c["ka"], c["px20"], c["px24"] = ka, px(20), px(2.4)
    print(f"   {nm}: pole {pole:.3f} Hz; K_alpha {ka:.4f} T/(deg/s^2); |P/x| 20 Hz {px(20):.4f}; 2.4 Hz {px(2.4):.4f}; "
          f"HF limit {(KP / 256) * beta * 2 / (1 + alpha):.4f}")
chk(round(c4["ka"], 3) == 0.210 and round(c5["ka"], 3) == 0.388, "K_alpha 0.210 -> 0.388")
chk(round(c4["px20"], 3) == 2.079 and round(c5["px20"], 3) == 3.850, "|P/x| 20 Hz 2.079 -> 3.850")
chk(round(c4["px24"], 3) == 1.594 and round(c5["px24"], 3) == 2.953, "|P/x| 2.4 Hz 1.594 -> 2.953")
chk(c5["px20"] / c4["px20"] < 3.0, f"HF ratio {c5['px20'] / c4['px20']:.4f} < x3 (H-HF-1)")
# V282's 44.90, from the V282 image: fb = s_old + s_new (add), E = 32*sp - fb, P = E*Kp>>8, D = (dE*Kd)>>3
c2 = cells(IMG["v282"])
z = cmath.exp(1j * 2 * math.pi * 20 * 1e-3)
fbx = (c2["b"] / 1024) * (z + 1) / (z - c2["a"] / 1024)
kp2, kd2 = c2["kY"][0], c2["dY"][0]
pdx = abs((kp2 / 256 + (kd2 / 8) * (1 - 1 / z)) * fbx)
print(f"   V282 (image: a {c2['a']} b {c2['b']} Kp {kp2} Kd {kd2} add={not c2['subr']} shl {c2['shl']}): |(P+D)/x| 20 Hz = {pdx:.2f}")
chk(abs(pdx - 44.90) < 0.05, f"V282's 44.90 reproduced from the V282 image ({pdx:.2f}); V295 is {20 * math.log10(c5['px20'] / pdx):.1f} dB below")
# where the trim reaches C
b5, a5 = c5["b"], c5["a"]
acc_C = c5["C"] / (b5 / (1024 - a5) * 8e-3)
print(f"   trim reaches C: below the pole at {acc_C:.0f} deg/s^2 (docstring '~1500'); HF limit at "
      f"{c5['C'] / (b5 / 1024 * 2 / (1 + a5 / 1024)) / 8:.0f} deg/s; at 2 Hz {c5['C'] / abs((b5 / 1024) * (cmath.exp(2j * math.pi * 2e-3) - 1) / (cmath.exp(2j * math.pi * 2e-3) - a5 / 1024)) / 8:.0f} deg/s, "
      f"3 Hz {c5['C'] / abs((b5 / 1024) * (cmath.exp(6j * math.pi * 1e-3) - 1) / (cmath.exp(6j * math.pi * 1e-3) - a5 / 1024)) / 8:.0f} deg/s "
      f"(docstring '~118 deg/s of 2 Hz-band rate')")

print("\n [3] int32 at the |x| = 12000 bail edge (docstring (c'): 4.058 -> 2.191, b_max 1150)")
def fixed(a, b, x):
    s, peak = 0, 0
    while True:
        s2 = ((a * s) >> 10) + ((b * x) >> 10)
        peak = max(peak, abs(a * s))
        if s2 == s:
            return s, peak
        s = s2
for nm, c in (("V294", c4), ("V295", c5)):
    sp_, pp = fixed(c["a"], c["b"], 12000); sn_, pn = fixed(c["a"], c["b"], -12000)
    c["marg"] = 2 ** 31 / max(pp, pn)
    print(f"   {nm}: s* {sn_:,} / {sp_:,}; max|a*s| {max(pp, pn):,}; margin {c['marg']:.4f}")
bmax = max(bb for bb in range(900, 1400) if 2 ** 31 / max(fixed(c5["a"], bb, 12000)[1], fixed(c5["a"], bb, -12000)[1]) >= 2.0)
print(f"   largest b with margin >= 2.0 at a = {c5['a']}: {bmax}")
chk(round(c4["marg"], 3) == 4.058 and round(c5["marg"], 3) == 2.191 and bmax == 1150, "int32 margins and b_max reproduced")
# guard edge from the code bytes: 0x2EE0 + x < 0x5DC1 (unsigned) -> x in [-12000, 12000]
print("   guard (decompile l.70): (0x2ee0 + x) < 0x5dc1  ->  x in [-12000, +12000]; |x| = 12000 is INSIDE the guard")

print("\n [4] FULL LANE, constant x from cold boot (report: 2892 lanes, r26 -> 0, settled T == V294)")
lanes = [(i, s, xv) for xv in (80, -80, 800, -800, 12000, -12000) for s in (1, -1) for i in range(241)]
spl = [sp_of(c5, i, s) for i, s, _ in lanes]; xl = [xv for _, _, xv in lanes]
T5f, R5f, mx5 = march(c5, xl, spl, 6000, keep=range(5000, 6000))
T4f, R4f, mx4 = march(c4, xl, spl, 6000, keep=range(5000, 6000))
chk(not np.any(R5f[-500:]) and np.all(T5f[-1] == T5f[-500]), f"r26 == 0 and T constant over the last 500 ticks on all {len(lanes)} lanes")
chk(np.array_equal(T5f[-1], T4f[-1]), "settled T == V294's on every lane")
chk(mx5 < 2 ** 31, f"int32 audit over the march: max |product| {mx5:,} (report 979,917,816)")
chk(mx5 == 979917816, "max product equals the report's 979,917,816 exactly", defect=True)

print("\n [5] RESTART PULSE after one bail tick, x = +-800 (100 deg/s at 8 counts per deg/s), 964 lanes")
rl = [(i, s, r) for i in range(241) for s in (1, -1) for r in (1, -1)]
spr = [sp_of(c5, i, s) for i, s, _ in rl]; xr = [r * 800 for _, _, r in rl]
PRE, POST = 3000, 1500
res = {}
for nm, c in (("V295", c5), ("V294", c4)):
    TT, RR, _ = march(c, xr, spr, PRE + 1 + POST, bail_at=PRE, keep=range(PRE - 500, PRE + 1 + POST))
    settled = (not np.any(RR[:500])) and bool(np.all(TT[498] == TT[499]))
    dev = np.abs(TT[500:] - TT[499])
    res[nm] = (dev.max(0), dev[1:].max(0), settled, dev)
v5, v4 = res["V295"][0], res["V294"][0]
k = int(np.argmax(v5))
z5 = [int(v5[j]) for j, l in enumerate(rl) if l[0] == 0]; z4 = [int(v4[j]) for j, l in enumerate(rl) if l[0] == 0]
ratio = v5 / np.maximum(v4, 1)
print(f"   settled before the bail: V295 {res['V295'][2]}  V294 {res['V294'][2]}")
print(f"   V295 worst {int(v5.max())} at idx {rl[k][0]} demand {rl[k][1]:+d} rate {rl[k][2]:+d} (all argmax lanes: "
      f"{[rl[j] for j in np.flatnonzero(v5 == v5.max())]}); excluding the bail tick {int(res['V295'][1].max())}")
print(f"   V294 worst {int(v4.max())};  zero command V295 {sorted(set(z5))} V294 {sorted(set(z4))};  worst per-point ratio "
      f"{ratio.max():.3f} at idx {rl[int(np.argmax(ratio))][0]};  lanes over 288: {int(np.sum(v5 > 288))};  lanes at 287: {int(np.sum(v5 == 287))}")
for i in (0, 60, 120, 180, 238, 240):
    js = [j for j, l in enumerate(rl) if l[0] == i]
    print(f"     idx {i:3d}: V295 {int(max(v5[j] for j in js)):4d}  V294 {int(max(v4[j] for j in js)):4d}")
chk(int(v5.max()) == 287 and int(v4.max()) == 165 and max(z5) == 269 and max(z4) == 145,
    "restart pulse 165 -> 287 worst, 145 -> 269 at zero command")
chk(int(v5.max()) <= 288, "restart pulse <= 288 (H-SAFE-3)")
chk(round(float(ratio.max()), 3) == 1.932, f"worst per-point ratio 1.932 ({ratio.max():.4f})")
# where in time the peak sits, and its sign relative to the settled T
dev5 = res["V295"][3]
tpk = int(np.argmax(dev5[:, k]))
print(f"   peak at tick +{tpk} after the bail tick on the worst lane")
# sensitivity: the pulse vs b around the decision (the 1-count margin)
print("   sensitivity of the worst pulse to b (a, C, Kp fixed):")
for bb in (1040, 1045, 1049, 1050, 1051, 1055, 1060):
    cc = dict(c5); cc["b"] = bb
    TT, _, _ = march(cc, xr, spr, PRE + 1 + POST, bail_at=PRE, keep=range(PRE - 1, PRE + 1 + POST))
    print(f"     b {bb}: worst {int(np.abs(TT[1:] - TT[0]).max())}")
# sensitivity to the assumed 8.00 counts per deg/s: the measured range 7.1-7.8 means 100 deg/s is 710-780 counts,
# and the flip side: if the true scale were higher than 8 the cap is exceeded at 100 deg/s
print("   sensitivity of the worst pulse to the x-per-deg/s scale at 100 deg/s:")
for xc in (760, 800, 808, 816, 840):
    xr2 = [r * xc for _, _, r in rl]
    TT, _, _ = march(c5, xr2, spr, PRE + 1 + POST, bail_at=PRE, keep=range(PRE - 1, PRE + 1 + POST))
    print(f"     x = {xc} ({xc / 8:.1f} deg/s at 8.00): worst {int(np.abs(TT[1:] - TT[0]).max())}")

print("\n [6] THE CUMULATIVE NON-STOCK DELTA -- docstring sec.1 + [15], read from the stock dump and the V295 image")
S_, V = IMG["stock"], IMG["v295"]
rows = [("fb clamp C", 0xC62E6, "u", 7680, 1024), ("pole a", 0xC63E8, "s", 923, 1011), ("gain b", 0xC63EA, "u", 1560, 1050),
        ("D clamp", 0xC61B6, "u", 10240, 0), ("r24 engaged arm", 0xC6446, "u", 512, 2048), ("Ki", 0xC63E6, "u", 0, 0),
        ("fwd clamp", 0xC61B2, "u", 512, 3072), ("OUT cap", 0xC61B4, "u", 512, 3072), ("lockout", 0xC62EA, "u", 320, 0),
        ("biquad enable", 0xC649B, "b", 0, 1), ("DTC-0x49 gate", 0xC64B8, "u", 112, 255), ("sq-wave hold", 0xC64DE, "b", 17, 27),
        ("P clamp", 0xC61BC, "u", 15360, 15360), ("SUM clamp", 0xC61BE, "u", 15360, 15360),
        ("out-lag a", 0xC63EC, "s", 992, 992), ("out-lag b", 0xC63EE, "u", 507, 507), ("shared scale", 0xC646C, "u", 891, 891)]
for nm, a, t, st, v in rows:
    rs = S_[a] if t == "b" else (s16(S_, a) if t == "s" else u16(S_, a))
    rv = V[a] if t == "b" else (s16(V, a) if t == "s" else u16(V, a))
    chk(rs == st and rv == v, f"{nm:16s} 0x{a:05X}: stock {rs:6d} (claimed {st})  V295 {rv:6d} (claimed {v})")
# the forward gain: resolve the load at 0x2A1F0 in EACH image (the stock-dump trap at 0xC6CD0)
ag_s, g_s = tp_load(S_, 0x2A1EE, True); ag_v, g_v = tp_load(V, 0x2A1EE, True)
print(f"   ld.h @0x2A1EE in STOCK loads 0x{ag_s:X} = {g_s};  in V295 loads 0x{ag_v:X} = {g_v};  stock dump raw 0xC6CD0 = "
      f"0x{u16(S_, 0xC6CD0):04X} ({s16(S_, 0xC6CD0)} signed)")
chk(ag_s == 0xC646C and g_s == 891 and ag_v == 0xC6CD0 and g_v == 5346 and u16(S_, 0xC6CD0) == 0xFFFF,
    "forward gain: stock 891 via 0xC646C (0xC6CD0 is blank 0xFFFF in stock -- the trap), V295 5346 via 0xC6CD0")
chk(u16(V, 0xC646C) == 891, "the shared scale 0xC646C is still stock 891 on V295")
# code sites
def op(b, o): return (u16(b, o) >> 5) & 0x3F
chk(op(S_, 0x28FA4) == 0x0E and op(V, 0x28FA4) == 0x0C and u16(S_, 0x28FA4) >> 11 == 26 and u16(V, 0x28FA4) & 0x1F == 9,
    f"0x28FA4 stock add r9,r26 ({u16(S_, 0x28FA4):04x}) -> V295 subr r9,r26 ({u16(V, 0x28FA4):04x})")
chk(u16(S_, 0x29D76) == 0x82C5 and u16(V, 0x29D76) == 0x82C2, f"0x29D76 stock shl 0x5,r16 ({u16(S_, 0x29D76):04x}) -> V295 shl 0x2,r16 ({u16(V, 0x29D76):04x})")
# banks, all 28 records
def bank(b, tbl):
    return [rec(b, u32(b, tbl + 4 * s))[1] for s in range(28)]
kpS, kpV, kdS, kdV = bank(S_, 0xCB994), bank(V, 0xCB994), bank(S_, 0xCB7D4), bank(V, 0xCB7D4)
chk(kpS[SLOT] == [248, 512, 645, 696, 696] and all(r == [960] * len(r) for r in kpV), f"Kp: stock slot 7 {kpS[SLOT]} -> V295 all 28 records flat 960")
chk(kdS[SLOT] == [128] * 4 and all(r == [0] * len(r) for r in kdV), f"Kd: stock slot 7 {kdS[SLOT]} -> V295 all 28 records 0")
mS = rec(S_, u32(S_, 0xC9A88 + 4 * SLOT)); mV = rec(V, u32(V, 0xC9A88 + 4 * SLOT))
chk(mV[1] == [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032] and mS[1] == [0, 24, 42, 50, 62, 100, 126, 154, 166, 172] and mS[0] == mV[0],
    f"map slot 7: stock Y {mS[1]} -> V295 Y {mV[1]} (X {mV[0]} unchanged)")
# V282 rows claimed unchanged, spot-read on V295 vs V282
v282 = IMG["v282"]
spots = [(0x13109, 1), (0x14120, 1), (0x2A1F0, 2), (0x35A08, 2), (0x35A12, 1), (0x35A18, 1), (0x3AA96, 1), (0x454FE, 1),
         (0x55C0E, 4), (0x55DF2, 32), (0xC4B34, 0xA4), (0xC6CD0, 2), (0xC61B2, 4), (0xC674E, 4), (0xC675A, 4), (0xC6768, 6),
         (0xC6598, 8), (0xC65AC, 8), (0xC65C4, 12), (0xC40BC, 2), (0xC40D2, 2), (0xC40DC, 2), (0xC61C0, 6), (0xC64B4, 6),
         (0xC649B, 1), (0xC62EA, 2), (0xC64DE, 2)]
bad = [hex(a) for a, n in spots if V[a:a + n] != v282[a:a + n]]
chk(not bad, f"{len(spots)} V282-row cells/windows byte-identical V282 -> V295 (docstring: 'unchanged by V293/V294/V295'): bad {bad}")
print(f"   0x14A cave [0xC4B34,0xC4BD8) sha256[:8] on V295: {hashlib.sha256(V[0xC4B34:0xC4BD8]).hexdigest()[:8]};  hook 0x55C0E "
      f"{V[0x55C0E:0x55C12].hex()};  427 tap window {V[0x55DF0:0x55E12].hex()}")
# the setpoint ceiling bank 0xCB844: stock 15360 x9 -> 16384
ceil_S = rec(S_, u32(S_, 0xCB844 + 4 * SLOT))[1]; ceil_V = rec(V, u32(V, 0xCB844 + 4 * SLOT))[1]
print(f"   setpoint ceiling slot 7: stock {ceil_S} -> V295 {ceil_V}")
# V293 / V294 per-build deltas as the docstring states them
v293, v294 = IMG["v293"], IMG["v294"]
chk(u16(v282, 0xC62E6) == 46080 and u16(v293, 0xC62E6) == 0, "V293: fb clamp 46080 -> 0")
chk(u16(v282, 0xC61B6) == 10240 and u16(v293, 0xC61B6) == 0, "V293: D clamp 10240 -> 0")
chk(u16(v282, 0xC6446) == 5244 and u16(v293, 0xC6446) == 2048, "V293: r24 arm 5244 -> 2048")
chk(all(r == [120] * len(r) for r in bank(v293, 0xCB994)) and all(r == [0] * len(r) for r in bank(v293, 0xCB7D4)),
    "V293: Kp all 28 -> 120 flat, Kd all 28 -> 0")
chk(u16(v293, 0xC62E6) == 0 and u16(v294, 0xC62E6) == 1024 and s16(v293, 0xC63E8) == 923 and s16(v294, 0xC63E8) == 1011
    and u16(v293, 0xC63EA) == 1560 and u16(v294, 0xC63EA) == 567 and all(r == [960] * len(r) for r in bank(v294, 0xCB994)),
    "V294: C 0 -> 1024, a 923 -> 1011, b 1560 -> 567, Kp 120 -> 960 all 28")
chk(op(v293, 0x28FA4) == 0x0E and op(v294, 0x28FA4) == 0x0C and u16(v293, 0x29D76) == 0x82C5 and u16(v294, 0x29D76) == 0x82C2,
    "V294: 0x28FA4 add -> subr, 0x29D76 shl 5 -> 2")

print("\n" + "=" * 110)
print(f" RESULT: {len(FAILS)} FAIL(s), {len(DEFECTS)} DEFECT(s)")
for f in FAILS:
    print("   FAIL  ", f)
for d in DEFECTS:
    print("   DEFECT", d)
