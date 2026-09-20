"""ADJUDICATION, part A -- pure control arithmetic at the measured D_loop bracket.

No data. Answers, for D_loop in {54.3 (e4 floor @2.5Hz), 55, 60 (the fork's assumption), 65, 72 (e3 <8 m/s),
75, 92 (e3 CI upper)}:
  1. the phase a rate-feedback term sees, phi(f) = w*D_loop + atan(w*RC), and the b_eq multiplier
     m(f) = cos(phi)/sqrt(1+(w*RC)^2) -- the fraction of AccordRateLoopGain that arrives as real damping.
  2. the damping/pumping boundary (phi = 90 deg).
  3. the rate loop's own Nyquist: L(jw) = G * F_rc(jw) * e^{-jw D} * P_rate(jw), with the identified plant
     P_rate = w-domain rate/torque = s/(J s^2 + b s + k(v)), J = 8e-5, b = 6e-4, k = HONDA_ACCORD_HOLD_K_V(v).
     Where does arg L cross -180, and what is |L| there at G = 0.0006 and 0.0012?
  4. RC sensitivity: can ANY first-order rate filter keep 2.5 Hz damping while not pumping 4-6 Hz at this delay?
  5. the AccordRefFilter (two cascaded first-order) transfer, 0.06 (as flown) vs candidates.
All angles in degrees, frequencies in Hz, torque in the fork's [-1,1] output units, angles in deg.
"""
import numpy as np

RC = 0.01                       # HONDA_ACCORD_RATE_LOOP_RC
J = 8e-5                        # HONDA_ACCORD_EPS_INERTIA, torque/(deg/s^2)
B_PLANT = 6e-4                  # fork's light b, torque/(deg/s)
K_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
DLOOPS = [54.3, 55.0, 60.0, 65.0, 72.0, 75.0, 92.0]
FREQS = [1.8, 2.0, 2.5, 2.7, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0]


def k_of_v(v):
    return float(np.interp(v, K_BP, K_V))


def phi_deg(f, D, rc=RC):
    w = 2 * np.pi * f
    return np.degrees(w * D) + np.degrees(np.arctan(w * rc))


def mult(f, D, rc=RC):
    """b_eq / G : the fraction of the rate-loop gain that arrives as real (rate-opposing) damping."""
    w = 2 * np.pi * f
    return np.cos(np.radians(phi_deg(f, D, rc))) / np.sqrt(1 + (w * rc) ** 2)


def boundary(D, rc=RC, target=90.0):
    f = np.arange(0.5, 15.0, 0.0005)
    p = phi_deg(f, D, rc)
    i = np.argmax(p >= target)
    return float(f[i]) if p[-1] >= target else float("nan")


print("=" * 108)
print("1/2.  RATE-FEEDBACK PHASE AND DAMPING MULTIPLIER   m = cos(phi)/|F_rc|,  RC = %.3f s" % RC)
print("      m > 0 damps, m < 0 PUMPS.  m is the fraction of AccordRateLoopGain that arrives as damping.")
print("=" * 108)
hdr = "  ".join(f"{f:>6.1f}" for f in FREQS)
print(f"{'D_loop':>8s} {'f90':>6s} {'f180':>6s} | phi(deg) / m  at f = {hdr}")
for D in DLOOPS:
    d = D / 1000.0
    ph = "  ".join(f"{phi_deg(f, d):6.1f}" for f in FREQS)
    mm = "  ".join(f"{mult(f, d):+6.3f}" for f in FREQS)
    print(f"{D:8.1f} {boundary(d):6.2f} {boundary(d, target=180.0):6.2f} | phi {ph}")
    print(f"{'':8s} {'':6s} {'':6s} |  m  {mm}")

print()
print("=" * 108)
print("3.  RATE-LOOP NYQUIST with the identified plant  P_rate(s) = s/(J s^2 + b s + k(v))")
print("    L(jw) = G * F_rc * e^{-jwD} * P_rate.  Reported: f where arg L = -180, |L| there at G = 0.0006 / 0.0012.")
print("    (taper min(1, 12/v) = 1 at every speed below 12 m/s, so low speed runs the full gain.)")
print("=" * 108)
print(f"{'v m/s':>6s} {'k':>8s} {'f_mode':>7s} | {'D_loop':>7s} {'f(-180)':>8s} {'|P| there':>10s} "
      f"{'|L|@6e-4':>9s} {'|L|@1.2e-3':>11s}")
f = np.arange(0.2, 20.0, 0.002)
w = 2 * np.pi * f
for v in (3.0, 6.0, 8.0, 12.0):
    k = k_of_v(v)
    fmode = np.sqrt(k / J) / (2 * np.pi)
    P = (1j * w) / (J * (1j * w) ** 2 + B_PLANT * (1j * w) + k)          # deg/s per torque
    for D in (55.0, 65.0, 75.0):
        L = (1.0 / (1 + 1j * w * RC)) * np.exp(-1j * w * D / 1000.0) * P
        ang = np.unwrap(np.angle(L))
        i = np.argmax(ang <= -np.pi)
        if ang[-1] > -np.pi:
            print(f"{v:6.1f} {k:8.4f} {fmode:7.2f} |  {D:6.1f}   (never reaches -180 in band)")
            continue
        print(f"{v:6.1f} {k:8.4f} {fmode:7.2f} | {D:7.1f} {f[i]:8.2f} {abs(P[i]):10.1f} "
              f"{0.0006*abs(L[i]):9.3f} {0.0012*abs(L[i]):11.3f}")

print()
print("=" * 108)
print("4.  CAN ANY FIRST-ORDER RATE FILTER SEPARATE 'damp 2.5 Hz' FROM 'do not pump 4-6 Hz'?")
print("    m(2.5) should be large and positive; m(4..6) should be near zero, not large and negative.")
print("=" * 108)
print(f"{'D_loop':>7s} {'RC s':>6s} | {'m(2.5)':>8s} {'m(3.5)':>8s} {'m(4)':>8s} {'m(5)':>8s} {'m(6)':>8s} "
      f"{'harm/help':>10s}   (harm = -min(m(4..6)), help = m(2.5))")
for D in (55.0, 65.0, 75.0):
    for rc in (0.0, 0.005, 0.01, 0.02, 0.04, 0.08):
        d = D / 1000.0
        h = mult(2.5, d, rc)
        harm = -min(mult(4.0, d, rc), mult(5.0, d, rc), mult(6.0, d, rc))
        print(f"{D:7.1f} {rc:6.3f} | {h:8.3f} {mult(3.5,d,rc):8.3f} {mult(4.0,d,rc):8.3f} "
              f"{mult(5.0,d,rc):8.3f} {mult(6.0,d,rc):8.3f} {harm/max(h,1e-9):10.2f}")

print()
print("=" * 108)
print("5.  AccordRefFilter -- TWO cascaded first-order lags of RC each (latcontrol_torque.py:319-326).")
print("    |H| = 1/(1+(w RC)^2) ; group delay = 2 RC/(1+(w RC)^2) ; the whole demand path (hold FF, MOVE FF,")
print("    rate-loop desired side, P/I error) is downstream of it, so the demand-coherent part of the wheel")
print("    rate scales by |H_new/H_old| exactly, with no dependence on D_loop.")
print("=" * 108)
print(f"{'RC s':>6s} | {'|H|@0.25':>9s} {'grp@0.25 s':>11s} {'|H|@0.6':>8s} {'grp@0.6':>8s} | "
      f"{'|H|@1.8':>8s} {'|H|@2.5':>8s} {'|H|@3.5':>8s} | {'ratio vs 0.06 at 1.8/2.5/3.5':>30s}")


def H2(f, rc):
    w = 2 * np.pi * f
    return 1.0 / (1 + (w * rc) ** 2)


def grp(f, rc):
    w = 2 * np.pi * f
    return 2 * rc / (1 + (w * rc) ** 2)


for rc in (0.0, 0.06, 0.09, 0.12, 0.16, 0.20):
    r = "  ".join(f"{(H2(f,rc)/H2(f,0.06)):5.3f}" for f in (1.8, 2.5, 3.5)) if rc > 0 else "  ".join(
        f"{(1.0/H2(f,0.06)):5.3f}" for f in (1.8, 2.5, 3.5))
    print(f"{rc:6.3f} | {H2(0.25,rc):9.4f} {grp(0.25,rc):11.4f} {H2(0.6,rc):8.4f} {grp(0.6,rc):8.4f} | "
          f"{H2(1.8,rc):8.4f} {H2(2.5,rc):8.4f} {H2(3.5,rc):8.4f} | {r:>30s}")

print()
print("=" * 108)
print("6.  WHY THE SETPOINT IS THE STRONGER LEVER AT THE SHAKE: the MOVE term differentiates it.")
print("    MOVE torque per deg of angle_des = rate_gain/G(v) * w * |1/(1+jw*0.10)| ;  HOLD torque per deg = k(v).")
print("=" * 108)
G_BP = [5.0, 12.5, 18.5, 28.5]
G_V = [550.0, 271.0, 246.0, 167.0]
print(f"{'v':>5s} {'G':>7s} {'k':>8s} | {'f':>5s} {'MOVE/deg':>10s} {'HOLD/deg':>10s} {'MOVE/HOLD':>10s}")
for v in (3.0, 6.0, 8.0):
    G = float(np.interp(v, G_BP, G_V))
    k = k_of_v(v)
    for fq in (1.8, 2.5, 3.5):
        wq = 2 * np.pi * fq
        move = 0.5 / G * wq / np.sqrt(1 + (wq * 0.10) ** 2)
        print(f"{v:5.1f} {G:7.1f} {k:8.4f} | {fq:5.1f} {move:10.5f} {k:10.5f} {move/k:10.2f}")
