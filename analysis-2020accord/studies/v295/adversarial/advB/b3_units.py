"""b3_units.py -- ADV-B step 3: the unit/scale chain from the BUILT IMAGE, on this agent's own lane.

 [0] my lane == the golden model (lkas_fb_lag + lkas_rate_pid_tick), tick for tick, V294 and V295 cells from the images
 [1] static surface: T per sp count, per idx, per 0xE4 wire count (sub-rail slope), the rail; T per openpilot torque unit
 [2] K_alpha by constant-acceleration march (numeric) and closed form, T per deg/s^2 of x/8 and of steering-wheel accel
 [3] controller T/omega at 0.5..20 Hz (closed form, exact 1 kHz z-domain incl. the output lag), damping and inertia parts;
     numeric lock-in check at 2.5 Hz and 20 Hz on my lane
 [4] |P/x| and |PID/x| at 20 Hz for V282 (from its OWN image, sum operand, shl 5, Kd), V294, V295
Run: python b3_units.py > b3_units_out.txt
"""
import cmath
import math
import random
import sys
from dataclasses import replace

sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
import eps_lkas_chain_model as M  # noqa: E402

from advb_lane import Lane, cells_from_image, lerp_walk  # noqa: E402
from advb_lib import find_v282  # noqa: E402

c5 = cells_from_image("V295")
c4 = cells_from_image("V294")
v282_path = find_v282()[0]
c2 = cells_from_image(v282_path, "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe")
print("images: V295 %s | V294 %s | V282 %s" % (c5["sha"][:16], c4["sha"][:16], c2["sha"][:16]))
for nm, c in (("V282", c2), ("V294", c4), ("V295", c5)):
    print("  %s a %d b %d C %d sh %d op %s Kp %s Kd %s Dcl %d P/S/T clamps %d/%d/%d lag %d/%d gain %d (disp 0x%04X) map %s"
          % (nm, c["a"], c["b"], c["C"], c["sh"], c["op"], c["kp_Y"], c["kd_Y"], c["dcl"], c["pcl"], c["scl"], c["tcl"],
             c["la"], c["lb"], c["gain"], c["gain_disp"], c["map_Y"]))
    print("       G opp X%s Y%s same X%s Y%s | act X%s Y%s | taperB X%s Y%s | taperD X%s Y%s | barfilt %d/%d"
          % (c["gopp_X"], c["gopp_Y"], c["gsame_X"], c["gsame_Y"], c["act_X"], c["act_Y"], c["tB_X"], c["tB_Y"],
             c["tD_X"], c["tD_Y"], c["bf9"], c["bf8"]))


def golden_cal(c):
    return replace(M.Calibration(), fb_lag_a=c["a"], fb_lag_b=c["b"], fb_clamp=c["C"], fb_op=c["op"], e_shift=c["sh"],
                   kp_x=tuple(c["kp_X"]), kp_y=tuple(c["kp_Y"]), kd_x=tuple(c["kd_X"]), kd_y=tuple(c["kd_Y"]),
                   pid_d_clamp=c["dcl"], pid_ki=c["ki"], pid_p_clamp=c["pcl"], sum_clamp=c["scl"], out_lag_a=c["la"],
                   out_lag_b=c["lb"], lkas_forward_gain=c["gain"], out_clamp=c["tcl"], assist_map_x=tuple(c["map_X"]),
                   assist_map_y=tuple(c["map_Y"]))


# ---------------------------------------------------------------------------------------------------------------
print("\n[0] my lane vs the golden model, tick for tick (random wire / x sequences, bar 0, request on, ramp full)")
for nm, c in (("V294", c4), ("V295", c5)):
    cal = golden_cal(c)
    rng = random.Random(7)
    bad = 0
    ntot = 0
    for trial in range(20):
        L = Lane(c, pol=-1)
        st = M.EpsState()
        st.pid_ramp = 0x8000
        L.ramp = 0x8000
        wire = 0
        x = 0
        for k in range(3000):
            if k % 10 == 0:
                wire = max(-4096, min(4096, wire + rng.randint(-300, 300)))
            x = max(-12000, min(12000, x + rng.randint(-400, 400)))
            T, r26, sp, P, S, idx, tf = L.tick(wire, x, 0, 1, want=True)
            fb = M.lkas_fb_lag(x, st, cal, lane_live=(k > 0))
            g = M.lkas_rate_pid_tick(sp, fb, idx, st, cal, pol=-1, taper=254)
            ntot += 1
            if g["T"] != T or fb != r26 or g["S"] != S:
                bad += 1
    print("   %s: %d ticks, %d mismatches (T, r26, S)" % (nm, ntot, bad))
    assert bad == 0


# ---------------------------------------------------------------------------------------------------------------
def settle(c, wire, x=0, ticks=6000, trim=True):
    L = Lane(c, pol=-1, trim=trim)
    L.ramp = 0x8000
    T = None
    for _ in range(ticks):
        T = L.tick(wire, x, 0, 1)
    return T


print("\n[1] static surface (settled T at constant wire, x = 0), pol -1 so + wire -> + T as on the tap")
for nm, c in (("V294", c4), ("V295", c5)):
    pts = [(w, settle(c, w)) for w in (-3870, -2000, -1000, -500, 500, 1000, 2000, 3000, 3870, 4096)]
    print("   %s: %s" % (nm, " ".join("%d:%d" % p for p in pts)))
ws = list(range(0, 3700, 97))
T5 = [settle(c5, w) for w in ws]
T4 = [settle(c4, w) for w in ws]
n = len(ws)
mx = sum(ws) / n; my = sum(T5) / n
slope = sum((w - mx) * (t - my) for w, t in zip(ws, T5)) / sum((w - mx) ** 2 for w in ws)
print("   V295 sub-rail slope (wire 0..3686, LS): %.4f T per wire count ; V294 identical: %s" % (slope, T4 == T5))
Tsp = (c5["kp_Y"][0] / 256.0) * (1 << c5["sh"]) * (254 / 256.0) * (2.0 * c5["lb"] / ((1024 - c5["la"]) * 32)) * c5["gain"] / 32768.0
print("   closed form T per sp count = (Kp/256)*2^sh*(254/256)*DC_lag*gain/32768 = %.4f ; map slope 4.30 sp/idx ->"
      " %.3f T/idx ; / 16.125736 wire per idx -> %.4f T/wire" % (Tsp, Tsp * 4.30, Tsp * 4.30 / 16.125736))
print("   rail: +%d / %d (wire +-4096)" % (settle(c5, 4096), settle(c5, -4096)))
for wpu in (4094.1, 4091.0, 4096.0):
    print("   T per openpilot torque unit at %.1f wire/unit (b2 [4]) = %.1f" % (wpu, slope * wpu))

# ---------------------------------------------------------------------------------------------------------------
print("\n[2] K_alpha: constant x acceleration (alpha deg/s^2 of x/8), sp = 0, settled trim T")


def kalpha_numeric(c, alpha_dps2=100.0, ticks=8000):
    L = Lane(c, pol=-1)
    L.ramp = 0x8000
    out = []
    for k in range(ticks):
        x = int(round(8.0 * alpha_dps2 * (k * 1e-3) - 6000))       # x from -6000 up, stays inside +-12000
        T, r26, *_ = L.tick(0, x, 0, 1, want=True)
        out.append((T, r26))
    tail = out[-2000:]
    return sum(t for t, _ in tail) / len(tail), sum(r for _, r in tail) / len(tail)


for nm, c in (("V294", c4), ("V295", c5)):
    T, r = kalpha_numeric(c)
    r_cf = 8 * c["b"] * 1e-3 / (1024 - c["a"])
    T_per_r26 = (c["kp_Y"][0] / 256.0) * (254 / 256.0) * (2.0 * c["lb"] / ((1024 - c["la"]) * 32)) * c["gain"] / 32768.0
    print("   %s: numeric at 100 deg/s^2: r26 %.2f (closed %.3f/deg/s^2 -> %.2f), T %.2f -> K_alpha %.4f T per deg/s^2 of x/8"
          " (closed %.4f) ; per deg/s^2 of STEERING WHEEL on centre (kappa 1.16): %.4f ; beyond 160 deg (0.965): %.4f"
          % (nm, r, r_cf, 100 * r_cf, T, abs(T) / 100.0, r_cf * T_per_r26, abs(T) / 100.0 / 1.16, abs(T) / 100.0 / 0.965))
    print("        T per r26 count = %.5f ; r26 counts per deg/s^2 = %.5f" % (T_per_r26, r_cf))

# ---------------------------------------------------------------------------------------------------------------
print("\n[3] controller T / omega (omega = x/8 in deg/s), exact 1 kHz z-domain, pol applied so a POSITIVE damping"
      " number means the torque OPPOSES the rate")


def H_T_per_x(c, f, kd_path=False):
    """T per x count (complex), trim path only, as built.  diff operand: r26 = (1 - z^-1) s ; sum: r26 = (1 + z^-1) s,
    s = (b/1024) x / (1 - (a/1024) z^-1).  E = -r26 ; P = Kp/256 E ; (+ D = Kd/8 (1 - z^-1) E if kd_path) ;
    S = 254/256 (P + D) ; L = (lb/1024) S / (1 - la/1024 z^-1) ; y = (1 + z^-1) L / 32 ; T = y pol gain / 32768."""
    z1 = cmath.exp(-2j * math.pi * f * 1e-3)
    s = (c["b"] / 1024.0) / (1 - (c["a"] / 1024.0) * z1)
    r26 = (1 - z1) * s if c["op"] == "diff" else (1 + z1) * s
    E = -r26
    P = (c["kp_Y"][0] / 256.0) * E
    D = (c["kd_Y"][0] / 8.0) * (1 - z1) * E if kd_path else 0.0
    S = (254 / 256.0) * (P + D)
    Lg = (c["lb"] / 1024.0) * S / (1 - (c["la"] / 1024.0) * z1)
    y = (1 + z1) * Lg / 32.0
    return y * (-1) * c["gain"] / 32768.0, P, P + D


def omega_resp(c, f):
    Tx, _, _ = H_T_per_x(c, f)
    # x = 8 omega ; omega = Re(W e^{jwt}) ; T = Re(Tx*8 W e^{jwt}).  In the TAP's sign convention (+T = +wire = RIGHT)
    # and x = +8*rate(LEFT +): a torque OPPOSING a leftward rate is a RIGHTward torque = +T.  So opposing part = +Re.
    G = Tx * 8.0
    w = 2 * math.pi * f
    return abs(G), math.degrees(cmath.phase(G)), G.real, G.imag / w     # |T/omega|, phase, damping, inertia (T per deg/s^2)


print("   f Hz  | V294 |T/w| ph  damp  inert | V295 |T/w| ph  damp  inert | ratio")
for f in (0.3, 0.5, 1.0, 2.0, 2.5, 3.0, 5.0, 10.0, 20.0):
    a4 = omega_resp(c4, f); a5 = omega_resp(c5, f)
    print("   %5.1f | %6.3f %+6.1f %6.3f %+7.4f | %6.3f %+6.1f %6.3f %+7.4f | %.4f" % (f, *a4, *a5, a5[0] / a4[0]))


def lockin(c, f, amp=500, ticks=20000):
    L = Lane(c, pol=-1)
    L.ramp = 0x8000
    T = []
    for k in range(ticks):
        x = int(round(amp * math.sin(2 * math.pi * f * k * 1e-3)))
        T.append(L.tick(0, x, 0, 1))
    k0 = ticks // 2
    ci = sum(T[k] * math.sin(2 * math.pi * f * k * 1e-3) for k in range(k0, ticks)) * 2 / (ticks - k0)
    cq = sum(T[k] * math.cos(2 * math.pi * f * k * 1e-3) for k in range(k0, ticks)) * 2 / (ticks - k0)
    G = complex(ci, cq) / amp            # T per x count, phase re x
    return G


print("   numeric lock-in on my lane (x = 500 sin; 2000 put V295 into the C clamp at 2.5 Hz -- see report), T per x count, vs closed form:")
for f in (2.5, 20.0):
    for nm, c in (("V294", c4), ("V295", c5)):
        G = lockin(c, f)
        Hc, _, _ = H_T_per_x(c, f)
        print("     %s %4.1f Hz: numeric |%.5f| %+.1f deg ; closed |%.5f| %+.1f deg" % (
            nm, f, abs(G), math.degrees(cmath.phase(G)), abs(Hc), math.degrees(cmath.phase(Hc))))

print("   per deg/s of STEERING WHEEL on centre, divide the damping by kappa 1.16:"
      " V294 %.3f -> V295 %.3f at 2.5 Hz" % (omega_resp(c4, 2.5)[2] / 1.16, omega_resp(c5, 2.5)[2] / 1.16))

# ---------------------------------------------------------------------------------------------------------------
print("\n[4] |P/x| and |PID/x| at 20 Hz (P or P+D counts per x count), each from its own image")
for nm, c in (("V282", c2), ("V294", c4), ("V295", c5)):
    _, P, PD = H_T_per_x(c, 20.0, kd_path=True)
    print("   %s: |P/x| %.3f  |(P+D)/x| %.3f   (Kp %d, Kd %d, op %s, a %d, b %d)" % (nm, abs(P), abs(PD), c["kp_Y"][0],
                                                                                   c["kd_Y"][0], c["op"], c["a"], c["b"]))
_, P4, _ = H_T_per_x(c4, 20.0); _, P5, _ = H_T_per_x(c5, 20.0); _, _, PD2 = H_T_per_x(c2, 20.0, kd_path=True)
print("   V295/V294 = %.4f ; V295 vs V282 %.2f dB ; V282 |PID/x| %.2f" % (abs(P5) / abs(P4), 20 * math.log10(abs(P5) / abs(PD2)), abs(PD2)))
