"""
REDO-PHYSICS claim 2: trim gain through the whole chain, two methods.
  (L) linear z-domain product of the stages, written here from the instruction list;
  (G) the golden model's integer lkas_fb_lag + lkas_rate_pid_tick marched on integer sinusoids of x.
x = 8 counts per deg/s (EVIDENCE: 0x55B48 writes the 0x14A field as -x>>3; wire 7.1-7.8).
"""
import math, sys
import numpy as np
from dataclasses import replace
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
import eps_lkas_chain_model as M

TS = 1e-3
XS = 8.0
V293 = replace(M.Calibration(), fb_clamp=0, kd_y=(0, 0, 0, 0), pid_d_clamp=0, kp_y=(120,) * 5)
V294 = replace(V293, fb_clamp=1024, fb_lag_a=1011, fb_lag_b=567, kp_y=(960,) * 5, fb_op="diff", e_shift=2)


def z1(f):
    return np.exp(-2j * np.pi * f * TS)


def H_fb(f, a=1011, b=567):          # x -> r26
    return (b / 1024) * (1 - z1(f)) / (1 - (a / 1024) * z1(f))


def H_out(f, a=992, b=507):          # S -> y : s' = a s/1024 + b S/1024 ; y = (s + s')/32
    return (b / 1024) * (1 + z1(f)) / (1 - (a / 1024) * z1(f)) / 32


K_P = 960 / 256                       # P per E ; E = 4 sp - r26
TAPER = 254 / 256
FWD = 5346 / 32768


def T_per_x(f):                       # delivered T counts per x count (the trim), sign: negative feedback
    return -K_P * TAPER * H_fb(f) * H_out(f) * FWD


print("=== constants ===")
print(f"T per r26 at DC = -3.75 * 254/256 * {abs(H_out(1e-6)):.6f} * 5346/32768 = {-K_P*TAPER*abs(H_out(1e-6))*FWD:.5f}")
Kalpha = K_P * TAPER * abs(H_out(1e-6)) * FWD * (567 / 1024) * TS / (1 - 1011 / 1024) * XS
print(f"K_alpha (below the pole) = {Kalpha:.5f} T counts per deg/s^2")
print(f"r26 clamp 1024 -> P {1024*K_P:.0f} -> after taper {1024*K_P*TAPER:.0f} -> T {1024*K_P*TAPER*abs(H_out(1e-6))*FWD:.1f} counts "
      f"= {1024*K_P*TAPER*abs(H_out(1e-6))*FWD/2461:.3f} of the 2461 rail")
print(f"clamp binds: below the pole at alpha = {1024/((567/1024)*TS/(1-1011/1024)*XS):.0f} deg/s^2; "
      f"at high f at rate amplitude {1024/(0.5537*XS):.0f} deg/s (sinusoid)")

print("\n=== (L) linear: T per deg/s of wheel rate, and per deg/s^2 ===")
print(" f(Hz)  |T/rate| (T per deg/s)  phase vs rate   |T/alpha| (T per deg/s^2)  rate amp at which |r26|=1024")
for f in (0.25, 0.5, 1, 1.5, 2, 2.4, 3, 5, 10, 20):
    t = T_per_x(f) * XS
    ta = t / (1j * 2 * np.pi * f)
    bind = 1024 / (abs(H_fb(f)) * XS)
    print(f"{f:5.2f}   {abs(t):8.3f}               {np.degrees(np.angle(t)):7.1f}         {abs(ta):8.4f}               {bind:7.0f} deg/s")

# ---- (G) golden-model integer march -------------------------------------------------------------------
def march(freq, amp_dps, idx=0, cal=V294, n=None, pol=1):
    """Hold the command at idx, drive x = round(8*amp*sin), return fitted T amplitude/phase re x (trim part)."""
    sp = M.lkas_rate_lerp(cal.assist_map_x, cal.assist_map_y, idx)
    st = M.EpsState()
    n = n or int(max(6 / freq, 3.0) / TS) + 3000
    xs = np.round(XS * amp_dps * np.sin(2 * np.pi * freq * np.arange(n) * TS)).astype(int)
    Ts_, r26s = [], []
    for x in xs:
        fb = M.lkas_fb_lag(int(x), st, cal)
        d = M.lkas_rate_pid_tick(sp, fb, idx, st, cal, pol=pol)
        Ts_.append(d["T"]); r26s.append(fb)
    Ts_ = np.array(Ts_, float); seg = slice(n // 2, n)
    tt = np.arange(n)[seg] * TS
    Xm = np.vstack([np.sin(2 * np.pi * freq * tt), np.cos(2 * np.pi * freq * tt), np.ones_like(tt)]).T
    cs, cc, c0 = np.linalg.lstsq(Xm, Ts_[seg], rcond=None)[0]
    amp = math.hypot(cs, cc); ph = math.degrees(math.atan2(cc, cs))
    return amp / amp_dps, ph, c0, Ts_[seg].min(), Ts_[seg].max(), max(abs(np.array(r26s)[seg]))


print("\n=== (G) golden-model integer march at idx 0 (sp = 0): T per deg/s, phase re the rate ===")
for f, a in ((0.5, 20), (1, 20), (2, 10), (2, 40), (2, 88), (3, 20), (10, 5), (20, 5), (2, 400)):
    g, ph, c0, lo, hi, rmax = march(f, a)
    lin = T_per_x(f) * XS
    print(f"  f {f:5.2f} Hz amp {a:4d} deg/s: T/rate {g:7.3f} ph {ph:7.1f} | linear {abs(lin):7.3f} ph {np.degrees(np.angle(lin)):7.1f}"
          f" | mean {c0:+6.2f} T range [{lo:.0f},{hi:.0f}] max|r26| {rmax}")

print("\n=== the FEEDFORWARD scale: T per demand index and per fork unit torque (STEER_MAX 4096, 16.125736 wire/idx) ===")
T = [M.lkas_rate_pid_surface(i, V294)["T"] for i in range(0, 241)]
T3 = [M.lkas_rate_pid_surface(i, V293)["T"] for i in range(0, 241)]
assert T == T3
sl = np.polyfit(np.arange(0, 230), np.array(T[:230]), 1)
print(f"T(idx) linear fit idx 0..229: slope {sl[0]:.4f} T/idx, intercept {sl[1]:.2f}; T(120) = {T[120]}, T(240) = {T[240]}")
T_per_u = sl[0] * 4096 / 16.125736
print(f"T per fork unit torque u = slope * 4096/16.125736 = {T_per_u:.1f} T counts (u >= {3870/4096:.3f} is the rail)")
J = 8e-5
print(f"fork plant J 8e-5 u/(deg/s^2) -> J_T = {J*T_per_u:.4f} T/(deg/s^2); K_alpha/J = {Kalpha/(J*T_per_u):.3f}")
print(f"trim in fork units: K_alpha_u = {Kalpha/T_per_u:.3e} u per deg/s^2; at 2 Hz {abs(T_per_x(2)*XS)/T_per_u:.2e} u per deg/s "
      f"(light b 6e-4, identified 1/G 1.8e-3..6e-3)")

print("\n=== the P-clamp interaction near the rail (the trim is one-sided when 15*sp is near 15360) ===")
for idx in (0, 120, 200, 230, 236, 238, 239, 240):
    g, ph, c0, lo, hi, rmax = march(2.0, 40, idx=idx)
    print(f"  idx {idx:3d} (sp {M.lkas_rate_lerp(V294.assist_map_x, V294.assist_map_y, idx):4d}, FF T {T[idx]:4d}): 2 Hz 40 deg/s: "
          f"T/rate {g:6.3f} ph {ph:6.1f} mean {c0:7.1f} (FF {T[idx]}) range [{lo:.0f},{hi:.0f}]")
