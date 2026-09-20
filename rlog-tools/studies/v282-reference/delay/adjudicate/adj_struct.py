"""ADJUDICATION, part D -- the STRUCTURED loop model, and what the observer is worth against the rate loop.

A single lumped D_loop is right for phase arithmetic AT ONE FREQUENCY only.  e4 measured the actuation law as
4 ms + a 5 Hz POLE (two independent fits; matches the firmware output-lag cell), and a pole's phase delay FALLS
with frequency while a pure delay's does not.  Using the lumped 54.3 ms at 5-6 Hz therefore OVER-counts the
pumping.  This script rebuilds the loop from its measured parts:

    measured rate  --[ rate filter RC = 0.01 s ]--  gain  --[ pure transport ]--[ 5 Hz pole ]-->  delivered torque

    pure transport = D_ctl 11.02 + lambda' 2.36 + dd 3.8 + sample age 7.59 = 24.77 ms   (all e4, EVIDENCE)
    + X ms of UNMEASURED post-tap transport (EME shaper, FOC/PWM, motor current rise, mechanics, EPS sensing).
      X = 0 reproduces e4's floor (54.3 ms equivalent at 2.5 Hz); X = 18 reproduces e3's <8 m/s reading (72 ms).

Then: the observer's measured energy injection (adj_observer.py) expressed as the AccordRateLoopGain increase that
would be needed to cancel it -- the like-for-like comparison, since both terms sit at the same place in the loop.
"""
import numpy as np

D_FIX = 24.77e-3          # e4: D_ctl + lambda' + dd + sample age
FC_TAP = 5.0              # e4: the tap law's pole (= the firmware output-lag cell)
RC = 0.01
J, B_PLANT = 8e-5, 6e-4
K_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
FREQS = [1.8, 2.0, 2.5, 2.7, 3.0, 3.5, 4.0, 5.0, 6.0]
XS = [0.0, 6.0, 12.0, 18.0, 24.0]       # unmeasured post-tap transport, ms


def loop_fb(f, X_ms, rc=RC, pole=True):
    """measured rate -> delivered torque, per unit gain (complex)."""
    w = 2 * np.pi * np.asarray(f, float)
    H = np.exp(-1j * w * (D_FIX + X_ms / 1000.0)) / (1 + 1j * w * rc)
    if pole:
        H = H / (1 + 1j * np.asarray(f, float) / FC_TAP)
    return H


def eq_delay_ms(f, X_ms):
    """The lumped delay with the same PHASE at f, EXCLUDING the fork's own rate filter -- i.e. directly
    comparable with the reported D_loop (e4's 54.3 ms at 2.5 Hz is transport + the tap law, no RC)."""
    w = 2 * np.pi * f
    return -np.angle(loop_fb(f, X_ms, rc=0.0)) / w * 1000.0


def m_of(f, X_ms, rc=RC, pole=True):
    """b_eq / gain: the fraction of AccordRateLoopGain that arrives as real rate-opposing damping."""
    return np.real(loop_fb(f, X_ms, rc=rc, pole=pole))


print("=" * 104)
print("D.1  EQUIVALENT LUMPED D_loop, from the structured model, vs frequency")
print("     (this is why a single D_loop number must always be quoted WITH its frequency)")
print("=" * 104)
print(f"{'X ms':>5s} {'D_eq@1.8':>9s} {'D_eq@2.5':>9s} {'D_eq@3.5':>9s} {'D_eq@5':>8s} {'D_eq@6':>8s}")
for X in XS:
    print(f"{X:5.0f} " + " ".join(f"{eq_delay_ms(f, X):9.1f}" for f in (1.8, 2.5, 3.5)) +
          " " + " ".join(f"{eq_delay_ms(f, X):8.1f}" for f in (5.0, 6.0)))

print()
print("=" * 104)
print("D.2  DAMPING MULTIPLIER m(f) = Re{H(f)}, H = measured rate -> delivered torque per unit gain.")
print("     m > 0 damps, m < 0 PUMPS.  Compare the 'pole' rows with the 'lumped delay' rows: treating the tap")
print("     law as a pure delay over-states the 4-6 Hz pumping by ~2x.")
print("=" * 104)
hdr = "  ".join(f"{f:>6.1f}" for f in FREQS)
print(f"{'X ms':>5s} {'model':>12s} {'f90':>5s} | m at f = {hdr}")
ff = np.arange(0.5, 12.0, 0.001)
for X in XS:
    # "pure delay" = the SAME total phase at 2.5 Hz, but with the tap law read as 30 ms of transport
    # instead of a 5 Hz pole (e4 says the total lag is 28-31 ms either way but the split is weakly identified)
    for lab, pole, extra in (("5 Hz pole", True, 0.0), ("tap=30ms delay", False, 30.0)):
        m = m_of(FREQS, X + extra, pole=pole)
        mm = m_of(ff, X + extra, pole=pole)
        sgn = np.where(np.diff(np.sign(mm)) < 0)[0]
        f90 = ff[sgn[0]] if len(sgn) else float("nan")
        print(f"{X:5.0f} {lab:>12s} {f90:5.2f} |        " + "  ".join(f"{x:+6.3f}" for x in m))

print()
print("=" * 104)
print("D.3  RATE-LOOP NYQUIST with the structured model and the identified plant, low speed (taper = 1)")
print("     |L| at the -180 deg crossing, for AccordRateLoopGain 0.0006 (as flown) and 0.0012 (the fork's limit)")
print("=" * 104)
w = 2 * np.pi * ff
print(f"{'v':>4s} {'X ms':>5s} {'f(-180)':>8s} {'|P| there':>10s} {'GM@6e-4':>8s} {'|L|@6e-4':>9s} {'|L|@1.2e-3':>11s}")
for v in (3.0, 6.0, 8.0):
    k = float(np.interp(v, K_BP, K_V))
    P = (1j * w) / (J * (1j * w) ** 2 + B_PLANT * (1j * w) + k)
    for X in XS:
        L = loop_fb(ff, X) * P
        ang = np.unwrap(np.angle(L))
        i = np.argmax(ang <= -np.pi)
        if ang[-1] > -np.pi:
            print(f"{v:4.1f} {X:5.0f}   never reaches -180 in 0.5-12 Hz")
            continue
        l6 = 0.0006 * abs(L[i])
        print(f"{v:4.1f} {X:5.0f} {ff[i]:8.2f} {abs(P[i]):10.1f} {1.0/l6:8.2f} {l6:9.3f} {0.0012*abs(L[i]):11.3f}")

print()
print("=" * 104)
print("D.4  THE OBSERVER vs THE RATE LOOP -- like for like, both at the same point in the loop.")
print("     b_eq(rate loop, 2.5 Hz) = G * m(2.5).  b_eq(observer) is MEASURED (adj_observer.py, 1.5-3.5 Hz).")
print("     'equiv gain' = the AccordRateLoopGain that would have to be ADDED to cancel the observer's injection.")
print("=" * 104)
OBS = {  # route: {bin: b_eq x 1e4 at tau = 55 / 65 / 75 ms}, measured
    "6c <8": (-0.37, -0.34, -0.29), "6d <8": (-0.31, -0.29, -0.27),
    "6e <8": (-1.17, -1.06, -0.94), "76 <8": (-1.44, -1.33, -1.19),
    "6c 3-8": (-0.22, -0.17, -0.12), "6d 3-8": (-0.53, -0.50, -0.46),
    "6e 3-8": (-1.18, -1.08, -0.95), "76 3-8": (-1.49, -1.39, -1.25),
}
print(f"{'X ms':>5s} {'D_eq@2.5':>9s} {'m(2.5)':>7s} {'rate-loop b_eq@6e-4':>20s} | observer b_eq x1e4 and the equivalent"
      f" gain it cancels")
for X, taus in ((0.0, 55.0), (12.0, 65.0), (18.0, 72.0)):
    m25 = float(m_of(2.5, X))
    blr = 0.0006 * m25
    key = f"{taus:.0f}"
    idx = {55.0: 0, 65.0: 1, 72.0: 2}[taus]
    parts = []
    for k, v3 in OBS.items():
        if " 3-8" not in k:
            continue
        b = v3[idx] * 1e-4
        parts.append(f"{k}: {v3[idx]:+.2f} = {abs(b)/blr*100:.0f}% of it (equiv gain {abs(b)/m25*1e4:.1f}e-4)")
    print(f"{X:5.0f} {eq_delay_ms(2.5, X):9.1f} {m25:7.3f} {blr*1e4:20.2f}e-4")
    for p in parts:
        print(f"{'':44s} {p}")

print()
print("=" * 104)
print("D.5  WHY REMOVING THE OBSERVER IS CHEAPER THAN ADDING RATE GAIN: the observer's two 0.6 Hz poles mean")
print("     its own content is already tiny at 4-6 Hz, so removing it costs NOTHING in the pumping band, while")
print("     raising the rate-loop gain buys damping at 2.5 Hz and pumping at 4-6 Hz in a FIXED ratio.")
print("=" * 104)
print(f"{'f Hz':>5s} {'|2-pole 0.6 Hz|':>15s}   (the observer's own roll-off)")
for f in (0.6, 1.5, 2.5, 3.5, 5.0, 6.0):
    print(f"{f:5.1f} {1.0/(1+(f/0.6)**2):15.4f}")
