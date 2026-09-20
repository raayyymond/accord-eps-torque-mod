# -*- coding: utf-8 -*-
r"""V294 design -- the orchestrator's own crux check, written BEFORE the build script.

THE IDEA (operator, 2026-09-20): the fork's 100 Hz loop cannot damp the wheel through a ~60 ms round trip,
so put a loop back in the EPS at 1 kHz -- but on ACCELERATION, not rate, and lean on the torque-map
feedforward.  V293's forward path stays BYTE-EXACT; the only new thing is an acceleration TRIM through the
existing P gain.

HOW, with the stock PID and no cave (every number below is checked against the image's own bytes):

    V293 today:   r26 = clamp(s_old + s_new, +-0)  = 0          E = 32*sp - 0        P = (E*120)>>8 = 15*sp
    V294:         r26 = clamp(s_new - s_old, +-C)               E =  4*sp - r26      P = (E*960)>>8 = 15*sp - (960/256)*r26

  * 0x28FA4  `add r9,r26`  -> `subr r9,r26`   (r26 := r9 - r26 = s_new - s_old).  ONE opcode nibble.
    s is the fb lag's state (pole a/1024); s_new - s_old = (b/1024) * (x - lag(x)) = a WASHOUT of the wheel
    rate x = the wheel ACCELERATION through a first-order low-pass at the lag pole, scaled by b/1024.
  * 0x29D76  `shl 0x5,r16` -> `shl 0x2,r16`   (E = 4*sp - r26).  ONE immediate field.  With Kp 120 -> 960
    the feedforward product is 3840*sp in BOTH images, so P_ff is BIT-IDENTICAL to V293 at every sp, and the
    trim gain on r26 rises x8 (the only way to size the trim without moving the feedforward).
  * 0xC62E6  fb clamp 0 -> C: bounds |r26| and therefore the trim to (960/256)*C sum counts = 25 % of the
    rail at C = 1024.  "Rely on the feedforward as much as possible" is a HARD bound here, not a tuning.
  * 0xC63EA  b (the lag's input gain) sets the trim gain; 0xC63E8 a sets the acceleration bandwidth.
  * Kd = 0 and the D clamp = 0 stay (V293): NO jerk term.  Ki = 0 stays: NO rate term.

WHY ACCELERATION AND NOT RATE, in one line: with T = -K*H(s)*alpha and H a LAG, the equation of motion
gives J_eff = J + K*Re H and b_eff = b - K*w*Im H; a lag has Im H < 0, so every degree of loop lag turns the
trim into DAMPING.  Delayed RATE feedback does the opposite (b_eff = b + K*cos(phi), negative past 90 deg),
which is the 20 Hz crossover resonance V282 ground on.  The trim anti-damps only where the total lag passes
180 deg, ~40 Hz, where the output lag has already cut it x0.05.

EVIDENCE / BELIEF: opcode decode, the integer mirror and the sum-count ratios are EVIDENCE (bytes).  The
physical scale (8 x-counts per deg/s) is BELIEF inherited from the record; every deg/s^2 figure carries it.
J = 8e-5, b, k(v) are the fork's identified plant (latcontrol_vehicle_tunes.py @ Dom 84766cdc5), BELIEF.
"""
import json
import math
import sys
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

import numpy as np                                                                 # noqa: E402
import build_v293_tva as V293                                                       # noqa: E402
from firmware_paths import plain_image_path                                          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

V293_NAME = ("_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048"
             "-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V293_SHA = "f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17"

# ---- the fork's identified plant, Dom 84766cdc5 latcontrol_vehicle_tunes.py (BELIEF) ------------------
J_TQ = 8e-5                                                    # torque per deg/s^2
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
LEVEL_BP, LEVEL_V = [12.5, 17.5], [1.15, 1.45]
EPS_G_BP, EPS_G_V = [5.0, 12.5, 18.5, 28.5], [550.0, 271.0, 246.0, 167.0]   # deg/s per unit torque = 1/b
B_LIGHT = 0.0006                                               # the "light damping" world, rev 4/5 fits
COUNTS_PER_TQ = 2605.0          # lane counts per unit fork torque: T(idx) = 10.25/idx, idx 240 = 0.9448 u
X_PER_DEGS = 8.0                # x counts per deg/s  [BELIEF]
TS = 1e-3
KP_NEW, E_SHIFT_NEW, KP_OLD, E_SHIFT_OLD = 960, 2, 120, 5
GAIN_FWD = (254 / 256) * (5346 / 32768)   # taper x forward gain; the output lag is modelled explicitly
OUT_A, OUT_B = 992, 507


def k_of_v(v):
    return float(np.interp(v, HOLD_V_BP, HOLD_K_V)) * float(np.interp(v, LEVEL_BP, LEVEL_V))


def b_ident(v):
    return 1.0 / float(np.interp(v, EPS_G_BP, EPS_G_V))


# ---- A. the two opcode edits, decoded with V293's independent decoder -------------------------------------
def decode_pair(img, site, new_bytes):
    old = V293.decode_one(bytes(img), site)
    patched = bytearray(img)
    patched[site:site + 2] = new_bytes
    new = V293.decode_one(bytes(patched), site)
    return old, new


# ---- B. the integer mirror of the fb lag with the DIFFERENCE operand -------------------------------------
def fb_tick(a, b, s, x, op):
    s_new = ((a * s) >> 10) + ((b * x) >> 10)
    r26 = (s_new - s) if op == "diff" else (s + s_new)
    return s_new, r26


def fb_orbit(a, b, x, op, clamp):
    s, seen, hist = 0, {}, []
    for _ in range(200000):
        if s in seen:
            cyc = hist[seen[s]:]
            return cyc
        seen[s] = len(hist)
        s, r26 = fb_tick(a, b, s, x, op)
        hist.append(max(-clamp, min(clamp, r26)))
    return hist[-1:]


def fb_sine_response(a, b, f, amp, op, clamp=10 ** 9, n_settle=4000, n_fit=8000):
    """Drive the integer filter with x = amp*sin(2 pi f t) at 1 kHz; least-squares the output onto
    sin/cos after settling.  Returns (gain, phase_deg) of r26 relative to x."""
    s = 0
    t = np.arange(n_settle + n_fit) * TS
    x = np.round(amp * np.sin(2 * math.pi * f * t)).astype(int)
    y = np.zeros(len(t))
    for i in range(len(t)):
        s, r26 = fb_tick(a, b, s, int(x[i]), op)
        y[i] = max(-clamp, min(clamp, r26))
    tt, yy = t[n_settle:], y[n_settle:]
    A = np.column_stack([np.sin(2 * math.pi * f * tt), np.cos(2 * math.pi * f * tt), np.ones_like(tt)])
    c, *_ = np.linalg.lstsq(A, yy, rcond=None)
    g = math.hypot(c[0], c[1]) / amp
    ph = math.degrees(math.atan2(c[1], c[0]))
    return g, ph


def H_fb(z, a, b, op):
    """Exact z-domain transfer of the fb lag stage, x -> r26 (unclamped)."""
    S = (b / 1024) / (z - a / 1024)
    return S * ((z - 1) if op == "diff" else (z + 1))


def H_out(z):
    return (1 + z) * (OUT_B / 1024) / (32 * (z - OUT_A / 1024))


def tau_p(a):
    return -TS / math.log(a / 1024)


def f_pole(a):
    return 1 / (2 * math.pi * tau_p(a))


# ---- D. the trim as a torque acting on the wheel ----------------------------------------------------------
def G_trim(f, a, b, tau_d):
    """Torque (lane counts) per degree of wheel angle, T_trim = -G_trim * theta.  Chain: x = 8*rate,
    r26 = H_fb x, P = -(KP_NEW/256) r26, S = taper*P, y = H_out S, T = gain*y, plus a pure delay."""
    w = 2 * math.pi * f
    z = np.exp(1j * w * TS)
    per_x = (KP_NEW / 256) * H_fb(z, a, b, "diff") * H_out(z) * GAIN_FWD * np.exp(-1j * w * tau_d)
    per_rate = per_x * X_PER_DEGS               # counts per deg/s
    return per_rate * (1j * w)                  # counts per deg  (rate = jw * theta)


def plant_D(f, v, b_world):
    """k - J w^2 + j b w, in lane counts per degree."""
    w = 2 * math.pi * f
    J = J_TQ * COUNTS_PER_TQ
    bb = (B_LIGHT if b_world == "light" else b_ident(v)) * COUNTS_PER_TQ
    k = k_of_v(v) * COUNTS_PER_TQ
    return k - J * w ** 2 + 1j * bb * w


def mode_analysis(v, a, b, tau_d, b_world):
    """Quasi-static effective inertia/damping at the wheel mode, and the mode's zeta before/after."""
    J = J_TQ * COUNTS_PER_TQ
    bb = (B_LIGHT if b_world == "light" else b_ident(v)) * COUNTS_PER_TQ
    k = k_of_v(v) * COUNTS_PER_TQ
    f0 = math.sqrt(k / J) / (2 * math.pi)
    z0 = bb / (2 * math.sqrt(k * J))
    f = f0
    for _ in range(30):                          # iterate the resonance with the added inertia
        g = G_trim(f, a, b, tau_d)
        w = 2 * math.pi * f
        J_add = -g.real / w ** 2
        f = math.sqrt(k / (J + J_add)) / (2 * math.pi)
    g = G_trim(f, a, b, tau_d)
    w = 2 * math.pi * f
    J_add, b_add = -g.real / w ** 2, g.imag / w
    zeta = (bb + b_add) / (2 * math.sqrt(k * (J + J_add)))
    return dict(f0=f0, zeta0=z0, f1=f, zeta1=zeta, J_add_ratio=J_add / J, b_add_ratio=b_add / bb,
                b_add_tq=b_add / COUNTS_PER_TQ)


def loop_gain(f, v, a, b, tau_d, b_world):
    return G_trim(f, a, b, tau_d) / plant_D(f, v, b_world)


def v282_hf_gain(f):
    """V282's rate-loop feedback at f, in P-domain counts per x count: P term on the SUM operand plus the
    D term on the tick difference of the sum.  Kp 248, Kd 128, a 923, b 1560.  Magnitudes only."""
    z = np.exp(2j * math.pi * f * TS)
    Hs = H_fb(z, 923, 1560, "sum")
    P = (248 / 256) * Hs
    D = 16 * (1 - 1 / z) * Hs
    return abs(P), abs(D), abs(P + D)


def v294_hf_gain(f, a, b):
    z = np.exp(2j * math.pi * f * TS)
    return abs((KP_NEW / 256) * H_fb(z, a, b, "diff"))


def k_alpha(a, b):
    """The trim's acceleration gain at f -> 0, in lane counts per deg/s^2, and as a fraction of J."""
    ka = (KP_NEW / 256) * (b / 1024) * tau_p(a) * X_PER_DEGS * GAIN_FWD * (2 * OUT_B / ((1024 - OUT_A) * 32))
    return ka, ka / (J_TQ * COUNTS_PER_TQ)


def b_for_kalpha(a, ratio):
    ka1, r1 = k_alpha(a, 1024)
    return int(round(1024 * ratio / r1))


def overflow(a, b, x_max=12000):
    s_max = b * x_max / (1024 - a)
    return a * s_max, (2 ** 31) / (a * s_max)


def main():
    img = Path(plain_image_path(V293_NAME)).read_bytes()
    import hashlib
    assert hashlib.sha256(img).hexdigest() == V293_SHA, "V293 image sha mismatch"
    print("=" * 110)
    print("  V294 DESIGN -- crux checks against the V293 image", V293_SHA[:16])
    print("=" * 110)

    print("\n[A] THE TWO OPCODE EDITS, decoded by build_v293_tva.decode_one (independent V850 decoder)")
    for site, new, want in ((0x28FA4, bytes.fromhex("89d1"), "subr r9, r26"),
                            (0x29D76, bytes.fromhex("c282"), "shl 0x2, r16")):
        (n0, m0, o0, f0), (n1, m1, o1, f1) = decode_pair(img, site, new)
        print(f"    0x{site:05X}: {img[site:site+2].hex()} `{m0} {o0}`  ->  {new.hex()} `{m1} {o1}`   "
              f"(len {n0}->{n1}) {'OK' if ''.join(f'{m1} {o1}'.split()) == ''.join(want.split()) and n0 == n1 == 2 else 'MISMATCH'}")

    print("\n[B] THE FEEDFORWARD PRODUCT IS BIT-IDENTICAL: (32*sp*120)>>8 == (4*sp*960)>>8 for every sp")
    bad = [sp for sp in range(-1200, 1201) if ((32 * sp * KP_OLD) >> 8) != ((4 * sp * KP_NEW) >> 8)]
    print(f"    sp in [-1200, 1200]: {len(bad)} mismatches  -> {'IDENTICAL' if not bad else bad[:5]}")

    print("\n[C] THE DIFFERENCE OPERAND, integer mirror vs the z-domain transfer (a=923, b=1560 stock pole)")
    print("    steady state at constant x (orbit of the clamped r26): x = 0 / 80 / 800 / 12000")
    for x in (0, 80, 800, 12000):
        cyc = fb_orbit(923, 1560, x, "diff", 10 ** 9)
        print(f"      x={x:6d}: orbit len {len(cyc)}, values {sorted(set(cyc))}  (the SUM operand at x=80 sits at 2434)")
    print("    sinusoidal x, amp 800 (= 100 deg/s at the BELIEF scale): integer gain/phase vs linear H(z)")
    for f in (0.5, 1.0, 2.5, 5.0, 7.0, 10.0, 20.0, 30.0):
        g, ph = fb_sine_response(923, 1560, f, 800, "diff")
        z = np.exp(2j * math.pi * f * TS)
        Hl = H_fb(z, 923, 1560, "diff")
        print(f"      f={f:5.1f} Hz  integer |H| {g:8.4f} ph {ph:7.1f} deg   linear |H| {abs(Hl):8.4f} ph {math.degrees(np.angle(Hl)):7.1f} deg"
              f"   (acceleration-equivalent phase {math.degrees(np.angle(Hl)) - 90:7.1f} deg vs alpha)")

    print("\n[D] CANDIDATES: pole a, input gain b sized for K_alpha/J in {0.5, 1.0, 2.0}  [J, scale: BELIEF]")
    print("    a    f_pole   K/J   b      |a*s|max/2^31   trim@20Hz vs V282 P+D@20Hz   clampbind alpha(C=1024)   trim cap")
    cands = []
    for a in (923, 974, 992):
        for ratio in (0.5, 1.0, 2.0):
            b = b_for_kalpha(a, ratio)
            ka, r = k_alpha(a, b)
            ov, margin = overflow(a, b)
            p282, d282, pd282 = v282_hf_gain(20.0)
            ours20 = v294_hf_gain(20.0, a, b)
            ds_per_alpha = (b / 1024) * tau_p(a) * X_PER_DEGS
            alpha_clamp = 1024 / ds_per_alpha
            cap = (KP_NEW / 256) * 1024 * GAIN_FWD * 0.990 / 2461
            cands.append(dict(a=a, b=b, ratio=r, f_pole=f_pole(a), ov_frac=1 / margin, ours20=ours20,
                              v282_20=pd282, alpha_clamp=alpha_clamp))
            print(f"    {a:4d}  {f_pole(a):5.1f}   {r:4.2f}  {b:5d}   {1/margin:6.3f}          "
                  f"{ours20:6.2f} / {pd282:6.2f} = {ours20/pd282:5.3f} ({20*math.log10(ours20/pd282):6.1f} dB)"
                  f"   {alpha_clamp:7.0f} deg/s^2            {100*cap:4.1f} % of rail")
    print(f"    (V282 at 20 Hz: P {p282:.2f} + D {d282:.2f} P-counts per x count; V282's loop was MARGINAL there)")

    print("\n[E0] POLE SWEEP -- zeta ratio at the wheel mode (light world) per speed, the 20 Hz margin vs V282, 7 Hz sign")
    print("    a     f_pole  K/J   b     zeta x @5   @8   @12.5 @19  @26    f1/f0@19   20Hz vs V282   7Hz b_add/b@19")
    sweep = []
    for a in (923, 974, 992, 1005, 1011, 1015):
        for ratio in (1.0, 2.0):
            b = b_for_kalpha(a, ratio)
            zs = [mode_analysis(v, a, b, 1.5e-3, "light") for v in (5.0, 8.0, 12.5, 19.0, 26.0)]
            g7 = G_trim(7.0, a, b, 1.5e-3)
            b7 = g7.imag / (2 * math.pi * 7.0) / (B_LIGHT * COUNTS_PER_TQ)
            r20 = v294_hf_gain(20.0, a, b) / v282_hf_gain(20.0)[2]
            ov = overflow(a, b)[0] / 2 ** 31
            sweep.append(dict(a=a, b=b, ratio=ratio, f_pole=f_pole(a), zeta_ratio=[m["zeta1"] / m["zeta0"] for m in zs],
                              f_ratio_19=zs[3]["f1"] / zs[3]["f0"], r20=r20, r20_db=20 * math.log10(r20), b7=b7, ov=ov))
            print(f"    {a:4d}  {f_pole(a):5.1f}   {ratio:3.1f}  {b:5d}   " +
                  " ".join(f"{m['zeta1']/m['zeta0']:4.2f}" for m in zs) +
                  f"     {zs[3]['f1']/zs[3]['f0']:4.2f}      {r20:5.3f} ({20*math.log10(r20):5.1f} dB)   {b7:+5.2f}   ovf {ov:.3f}")

    print("\n[E] THE WHEEL MODE, before/after, per speed and per damping world (tau_d = 1.5 ms nominal)")
    tbl = {}
    for a, ratio in ((923, 1.0), (974, 1.0), (1005, 1.0), (1011, 1.0), (1011, 2.0)):
        b = b_for_kalpha(a, ratio)
        print(f"    --- a={a} (f_pole {f_pole(a):.1f} Hz), b={b}, K/J={ratio}")
        print("      v     world   f0    zeta0 -> f1    zeta1   x   J_add/J  b_add/b  b_add(tq)")
        for world in ("light", "ident"):
            for v in (5.0, 8.0, 12.5, 19.0, 26.0):
                m = mode_analysis(v, a, b, 1.5e-3, world)
                tbl[f"{a}_{b}_{world}_{v}"] = m
                print(f"      {v:4.1f}  {world:5s}  {m['f0']:5.2f} {m['zeta0']:5.3f} -> {m['f1']:5.2f} {m['zeta1']:5.3f}  "
                      f"x{m['zeta1']/m['zeta0']:4.2f}   {m['J_add_ratio']:5.2f}    {m['b_add_ratio']:5.2f}    {m['b_add_tq']:.5f}")

    print("\n[F] LOOP GAIN OF THE TRIM AROUND THE RIGID-BODY PLANT (light world, v=19): |L| and phase; -180 crossings")
    curves = {}
    for a, ratio in ((923, 1.0), (974, 1.0), (992, 1.0)):
        b = b_for_kalpha(a, ratio)
        fs = np.logspace(math.log10(0.3), math.log10(200), 400)
        for tau_d in (1.5e-3, 3.0e-3):
            L = np.array([loop_gain(f, 19.0, a, b, tau_d, "light") for f in fs])
            mag, ph = np.abs(L), np.degrees(np.unwrap(np.angle(L)))
            # the -180 crossing (phase of L relative to -1: L is the return ratio of NEGATIVE feedback: 1 + L = 0)
            cross = [fs[i] for i in range(1, len(fs)) if (ph[i - 1] > -180 >= ph[i]) or (ph[i - 1] < -180 <= ph[i])]
            gm = [mag[np.argmin(abs(fs - c))] for c in cross]
            hf = mag[fs > 10].max()
            print(f"    a={a} b={b} tau_d={tau_d*1e3:.1f} ms: max|L| {mag.max():.3f} at {fs[mag.argmax()]:.1f} Hz; "
                  f"max|L| above 10 Hz {hf:.3f}; -180 crossings {[f'{c:.0f}Hz |L|={g:.3f}' for c, g in zip(cross, gm)]}")
            if tau_d == 1.5e-3:
                curves[f"{a}_{b}"] = dict(f=fs.tolist(), mag=mag.tolist(), ph=ph.tolist())

    print("\n[G] THE TRIM'S FREQUENCY RESPONSE as an acceleration feedback: |T/alpha| / K_alpha, phase vs -alpha")
    resp = {}
    for a, ratio in ((923, 1.0), (974, 1.0), (992, 1.0)):
        b = b_for_kalpha(a, ratio)
        ka, _ = k_alpha(a, b)
        fs = np.logspace(math.log10(0.2), math.log10(100), 300)
        rows = []
        for f in fs:
            g = G_trim(f, a, b, 1.5e-3)
            w = 2 * math.pi * f
            over_alpha = g / (-(w ** 2))                     # T per unit alpha (alpha = -w^2 theta)
            rows.append((f, abs(over_alpha) / ka, math.degrees(np.angle(-over_alpha))))
        resp[f"{a}_{b}"] = rows
        pick = [r for r in rows if any(abs(r[0] - q) / q < 0.02 for q in (1, 2.5, 7, 20, 40))]
        print(f"    a={a} b={b}: " + "  ".join(f"{f:.1f}Hz |H|{m:.2f} ph{p:+.0f}" for f, m, p in pick[::max(1, len(pick)//5)]))

    json.dump(dict(cands=cands, modes=tbl, loops=curves, resp=resp), open(OUT / "v294_design.json", "w"), indent=1)
    print(f"\n  wrote {OUT / 'v294_design.json'}")


if __name__ == "__main__":
    main()
