"""Orchestrator cross-check: at what LATERAL ACCEL does the fitted hold map saturate,
and where does real tyre self-aligning torque actually saturate?
Everything here is first-principles vehicle dynamics; no fitted fork constant is trusted.
"""
import math
import numpy as np

# --- Accord 2020 parameters (published / standard) ---
M      = 1580.0     # kg, kerb + driver
L      = 2.83       # m, wheelbase
FRONT  = 0.60       # front weight fraction -> F_yf = FRONT * m * a_y in steady state
SR     = 16.88      # HONDA_ACCORD_STEER_RATIO_NOMINAL (steering wheel deg per road wheel deg)
K_US_DEG_PER_G = 3.0            # deg of extra steer per g  (typical FWD sedan 2-4)
K_US = K_US_DEG_PER_G / 9.81    # deg per (m/s^2)

# --- the fork's fitted hold map ---
SAT_A, SAT_B, SAT_C = (19.3, 546.0, 3.01)
def sat_deg(v): return SAT_A + SAT_B * math.exp(-v / SAT_C)

def steer_deg_for_ay(ay, v):
    """Steering-wheel angle (deg) needed for steady lateral accel ay at speed v."""
    kappa = ay / max(v*v, 1e-6)
    d_road = math.degrees(L * kappa) + K_US * ay     # Ackermann + understeer
    return d_road * SR

def ay_for_steer_deg(sw, v):
    """Invert the above."""
    d_road = sw / SR
    kappa_term = math.degrees(L / max(v*v, 1e-6))    # deg per (m/s^2) from Ackermann
    return d_road / (kappa_term + K_US)

print("=" * 78)
print("1. WHERE THE FITTED HOLD MAP SATURATES, IN LATERAL-ACCEL TERMS")
print("=" * 78)
print(f"{'v m/s':>6} {'sat deg':>8} {'a_y at sat':>11} {'a_y in g':>9} {'a_y at 2*sat':>13} {'sw for 0.3g':>12} {'sw for 0.8g':>12}")
for v in [12.5, 15.0, 17.5, 19.0, 22.0, 26.0, 30.0]:
    s = sat_deg(v)
    ay_s  = ay_for_steer_deg(s, v)
    ay_2s = ay_for_steer_deg(2*s, v)
    print(f"{v:6.1f} {s:8.2f} {ay_s:11.3f} {ay_s/9.81:9.3f} {ay_2s:13.3f} "
          f"{steer_deg_for_ay(0.3*9.81, v):12.1f} {steer_deg_for_ay(0.8*9.81, v):12.1f}")

print()
print("=" * 78)
print("2. WHERE REAL TYRE SELF-ALIGNING TORQUE ACTUALLY PEAKS")
print("=" * 78)
C_ALPHA_PER_TYRE = 1200.0 * 180.0 / math.pi   # N/rad  (1200 N/deg, typical 235/45R18)
MU = 0.9
for v in [19.0, 26.0]:
    print(f"\n  v = {v} m/s")
    print(f"  {'a_y (m/s2)':>11} {'a_y (g)':>8} {'slip_f (deg)':>13} {'sw angle (deg)':>15} {'F_yf/F_zf':>10}")
    F_zf = M * 9.81 * FRONT
    for ay in [0.5, 1.0, 1.59, 2.0, 3.0, 4.0, 6.0, 8.0]:
        F_yf = FRONT * M * ay
        slip = math.degrees(F_yf / (2.0 * C_ALPHA_PER_TYRE))
        print(f"  {ay:11.2f} {ay/9.81:8.3f} {slip:13.2f} {steer_deg_for_ay(ay, v):15.1f} {F_yf/(MU*F_zf):10.3f}")
    print(f"  [tyre saturates near F_yf/(mu*F_zf) = 1.0, i.e. a_y ~ {MU*9.81:.1f} m/s^2 = {MU:.2f} g]")
    print(f"  [pneumatic trail collapses -> Mz PEAKS around slip 3-5 deg, i.e. a_y ~ 5-9 m/s^2]")

print()
print("=" * 78)
print("3. THE DEFICIT: fitted tanh map vs a linear-in-angle spring of the same slope k")
print("=" * 78)
K_BP=[2.0,4.0,6.0,8.0,10.0,12.5,15.0,17.5,20.0,23.0,28.0]
K_V=[0.0021,0.0028,0.0044,0.0052,0.0074,0.0092,0.0095,0.0103,0.0116,0.0133,0.0160]
LVL_BP=[12.5,17.5]; LVL_V=[1.15,1.45]
for v in [19.0, 26.0]:
    k = float(np.interp(v,K_BP,K_V)) * float(np.interp(v,LVL_BP,LVL_V))
    s = sat_deg(v)
    print(f"\n  v = {v} m/s   k*level = {k:.5f} torque/deg   sat = {s:.1f} deg")
    print(f"  {'sw deg':>7} {'a_y m/s2':>9} {'tanh map':>9} {'linear':>8} {'ratio':>7} {'deficit':>8}")
    for sw in [10, 20, 30, 40, 60, 80, 120]:
        t_map = k * s * math.tanh(sw / s)
        t_lin = k * sw
        print(f"  {sw:7d} {ay_for_steer_deg(sw, v):9.2f} {t_map:9.4f} {t_lin:8.4f} "
              f"{t_map/t_lin:7.3f} {t_lin-t_map:8.4f}")

print()
print("=" * 78)
print("4. HOW LONG THE INTEGRATOR TAKES TO COVER THE DEFICIT")
print("=" * 78)
print("  I accumulates  ki * error_in_lat_accel * dt  per 10 ms frame.")
KI = 0.30
DT = 0.01
for v, sw in [(19.0, 40.0), (19.0, 80.0), (26.0, 40.0), (26.0, 80.0)]:
    k = float(np.interp(v,K_BP,K_V)) * float(np.interp(v,LVL_BP,LVL_V))
    s = sat_deg(v)
    deficit = k*sw - k*s*math.tanh(sw/s)
    ay = ay_for_steer_deg(sw, v)
    # steady-state lat-accel error that the I term needs to integrate to produce `deficit`
    # torque; at equilibrium I = ki * integral(err). Time to reach `deficit` if err is a
    # fraction f of the commanded a_y:
    for f in [0.10, 0.25]:
        err = f * ay
        t = deficit / max(KI * err, 1e-9)
        print(f"  v={v:4.1f} sw={sw:5.1f} (a_y={ay:4.2f})  deficit={deficit:.4f}  "
              f"if lat-accel err = {f*100:.0f}% of demand -> I covers it in {t:6.2f} s")
