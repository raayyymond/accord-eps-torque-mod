"""
REDO-PHYSICS claim 1: the V294 feedback operand, from the integer arithmetic.

Independent integer mirror (NOT the golden model's lkas_fb_lag; that is used only as a cross-check at the end):
    0x28F8E/0x28F9A  t1 = (b*x) >> 10          (sar floors toward -inf; Python >> floors too)
    0x28F92/0x28FA0  t2 = (a*s) >> 10
    0x28FA2          s_new = t1 + t2
    0x28FA4 (V294)   r26 = s_new - s           subr r9,r26
    0x28FA8          s := s_new
    clamp r26 to +-C (C = 1024)
a = 1011 (ld.h signed), b = 567 (ld.hu), Ts = 1 ms.
"""
import math, random, sys
import numpy as np

A, B, C = 1011, 567, 1024
TS = 1e-3


def tick(x, s, a=A, b=B, c=C):
    s_new = ((a * s) >> 10) + ((b * x) >> 10)
    r = s_new - s
    r = max(-c, min(c, r))
    return r, s_new


# ---- 1a. the z-domain transfer function -------------------------------------------------------------
# linear:  s[n] = p s[n-1] + g x[n],  p = a/1024, g = b/1024
#          r[n] = s[n] - s[n-1]  =>  R(z)/X(z) = g (1 - z^-1) / (1 - p z^-1)
# with x = 8 * omega (omega in deg/s, x-scale 8 EVIDENCE) and alpha = d omega/dt:
#   (1 - z^-1) = j 2 sin(wT/2) e^{-j wT/2}  ->  R/alpha = g * T * sinc-ish * e^{-j wT/2} / (1 - p z^-1) * 8
p, g = A / 1024, B / 1024
pole_hz = -math.log(p) / (2 * math.pi * TS)
dc_s = g / (1 - p)                               # DC gain x -> s
dc_alpha = g * TS / (1 - p)                      # DC gain alpha(x-counts/s) -> r26
print("=== 1a. transfer function ===")
print(f"p = a/1024 = {p:.6f}; pole = -ln(p)/(2 pi Ts) = {pole_hz:.4f} Hz  (continuous-matched s-pole {-math.log(p)/TS:.3f} rad/s)")
print(f"g = b/1024 = {g:.6f};  DC(x->s) = g/(1-p) = {dc_s:.4f};  high-f |r26/x| -> g = {g:.4f} (Nyquist 2g/(1+p) = {2*g/(1+p):.4f})")
print(f"DC(alpha -> r26) = g*Ts/(1-p) = {dc_alpha:.6f} r26 per (x-count/s) = {8*dc_alpha:.5f} r26 per deg/s^2")
for a_ in (923, 1011, 1015, 1018):
    print(f"   a={a_}: pole {-math.log(a_/1024)/(2*math.pi*TS):.3f} Hz")


def Hx(f, a=A, b=B):
    z1 = np.exp(-2j * np.pi * f * TS)
    return (b / 1024) * (1 - z1) / (1 - (a / 1024) * z1)


def Halpha_cont_equiv(f, a=A, b=B):
    """r26 per (x-count/s) of alpha, exact discrete, divided by j w (alpha = j w * rate)."""
    w = 2 * np.pi * f
    return Hx(f, a, b) / (1j * w)


print("\n f(Hz)   |r26/x|   ph(deg)   |r26/alpha|/DC   ph_alpha(deg)   1st-order LP@pole: mag, ph")
for f in (0.1, 0.5, 1, 2, 2.03, 3, 5, 10, 16, 20, 26, 30, 50):
    h = Hx(f); ha = Halpha_cont_equiv(f)
    lp = 1 / (1 + 1j * f / pole_hz)
    print(f"{f:6.2f}  {abs(h):8.4f}  {np.degrees(np.angle(h)):8.2f}   {abs(ha)/dc_alpha:10.4f}   {np.degrees(np.angle(ha)):10.2f}"
          f"    {abs(lp):.4f}, {np.degrees(np.angle(lp)):7.2f}")

# numeric check of the formula by simulating the LINEAR recursion with a sinusoid (float, no floors)
print("\n  simulated linear recursion vs formula (float):")
for f in (1.0, 2.0, 20.0):
    n = np.arange(20000); x = 1000 * np.sin(2 * np.pi * f * n * TS)
    s = 0.0; r = np.zeros_like(x)
    for i, xi in enumerate(x):
        s_new = p * s + g * xi; r[i] = s_new - s; s = s_new
    seg = slice(10000, 20000)
    ref = np.exp(2j * np.pi * f * n[seg] * TS)
    est = 2 * np.mean(r[seg] * np.conj(ref)) / 1000 * 1j  # sin -> (e - e*)/2j
    # fit amplitude/phase directly
    Xm = np.vstack([np.sin(2*np.pi*f*n[seg]*TS), np.cos(2*np.pi*f*n[seg]*TS)]).T
    cs, cc = np.linalg.lstsq(Xm, r[seg], rcond=None)[0]
    amp = math.hypot(cs, cc) / 1000; ph = math.degrees(math.atan2(cc, cs))
    h = Hx(f)
    print(f"   f={f:5.1f}: sim |H| {amp:.5f} ph {ph:7.2f}  | formula {abs(h):.5f} {np.degrees(np.angle(h)):7.2f}")

# ---- 1b. does the INTEGER operand settle to EXACTLY 0 at every constant x? ------------------------------
print("\n=== 1b. settle to exactly 0 at constant x (integer) ===")
# Monotonicity argument: F(s) = floor(a s/1024) + c is non-decreasing in s (a > 0), so the orbit of any
# integer s is monotone and bounded => reaches a fixed point in finite time => r26 = s_new - s = 0 exactly.
# Brute force: every x in [-12000, 12000], from s = 0 (cold boot), s = +-2^20 and a random state.
worst_ticks, bad = 0, []
rng = random.Random(1)
for x in range(-12000, 12001):
    for s0 in (0, 1 << 20, -(1 << 20), rng.randint(-600000, 600000)):
        s, n = s0, 0
        while True:
            r, s2 = tick(x, s)
            n += 1
            if s2 == s:
                break
            s = s2
            if n > 5000:
                bad.append((x, s0)); break
        worst_ticks = max(worst_ticks, n)
        assert r == 0
print(f"all 24001 x values x 4 start states reach r26 == 0 exactly; worst ticks to settle {worst_ticks}; failures {len(bad)}")
# the fixed-point INTERVAL width (hysteresis of the state, not of the operand)
def fixed_interval(x):
    c = (B * x) >> 10
    s_star = c / (1 - p)
    return [s for s in range(int(s_star) - 400, int(s_star) + 400) if ((A * s) >> 10) + c == s]
for x in (0, 1, 80, 800, 12000, -800):
    fi = fixed_interval(x)
    print(f"   x={x:6d}: fixed-point interval of s = [{fi[0]}, {fi[-1]}] width {len(fi)}  (1/(1-p) = {1/(1-p):.1f})")

# ---- 1c. worst-case dither from the two floors, under a VARYING x -------------------------------------
print("\n=== 1c. dither: integer r26 minus the linear (float) r26 ===")
# analytic bound: s_int[n] = p s_int[n-1] + g x[n] + e[n], e in (-2, 0]; r_int - r_lin = (1-z^-1)/(1-pz^-1) e
#   = e[n] - (1-p) sum_k p^k e[n-1-k]  ->  strictly inside (-2, +2); r26 is an integer => |dither| <= 1
def run(xs):
    s_i, s_f = 0, 0.0
    di = []
    for x in xs:
        r_i, s_i = tick(int(x), s_i, c=10**9)
        sf_new = p * s_f + g * x; r_f = sf_new - s_f; s_f = sf_new
        di.append(r_i - r_f)
    return np.array(di)
tests = {
    "white x +-12000": [rng.randint(-12000, 12000) for _ in range(200000)],
    "slow ramp 0.02 cnt/tick": [int(0.02 * k) for k in range(200000)],
    "2 Hz sine amp 400": [int(round(400 * math.sin(2 * math.pi * 2 * k * TS))) for k in range(200000)],
    "20 Hz sine amp 40": [int(round(40 * math.sin(2 * math.pi * 20 * k * TS))) for k in range(200000)],
    "random walk": np.clip(np.cumsum([rng.choice((-3, -1, 0, 1, 3)) for _ in range(200000)]), -12000, 12000).astype(int),
}
for name, xs in tests.items():
    d = run(xs)[2000:]
    print(f"   {name:26s}: dither min {d.min():+.3f} max {d.max():+.3f} mean {d.mean():+.4f} rms {d.std():.3f}")
# worst-case search: adversarial x sequences (greedy) to push the dither
best = 0
for trial in range(300):
    xs = [rng.randint(-12000, 12000) if rng.random() < 0.5 else rng.randint(-3, 3) for _ in range(3000)]
    d = run(xs)
    best = max(best, np.abs(d).max())
print(f"   adversarial random search (300 x 3000 ticks): max |dither| {best:.4f}  (bound < 2)")

# ---- 1d. slow acceleration: is there a DEAD ZONE (operand stuck at 0 under a small constant accel)? -----
print("\n=== 1d. constant acceleration (x ramp): the operand's mean equals the linear value; it is PWM-quantised ===")
for beta in (0.001, 0.005, 0.01, 0.023, 0.05, 0.2, 1.0):     # x counts per tick
    xs = [math.floor(beta * k) for k in range(400000)]
    s = 0; rs = []
    for x in xs:
        r, s = tick(x, s); rs.append(r)
    rs = np.array(rs[100000:])
    lin = g * beta / (1 - p)
    print(f"   beta {beta:6.3f} cnt/ms = {beta*1000/8:7.3f} deg/s^2: mean r26 {rs.mean():8.4f} vs linear {lin:8.4f}; values {sorted(set(rs.tolist()))[:6]}")

# ---- cross-check against the golden model's mirror ---------------------------------------------------
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
import eps_lkas_chain_model as M
from dataclasses import replace
v294 = replace(M.Calibration(), fb_clamp=1024, fb_lag_a=1011, fb_lag_b=567, fb_op="diff", e_shift=2)
st = M.EpsState(); s = 0; mism = 0
for k in range(100000):
    x = tests["white x +-12000"][k] if k % 3 else int(300 * math.sin(k / 50))
    r_g = M.lkas_fb_lag(x, st, v294)
    r_m, s = tick(x, s)
    mism += (r_g != r_m)
print(f"\ncross-check vs golden-model lkas_fb_lag (fb_op diff): mismatches {mism}/100000")
