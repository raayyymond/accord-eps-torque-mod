"""
c6_trim_response.py -- what each fb-former / Kp / output-lag knob PHYSICALLY does to the V294 acceleration trim,
from the exact LINEAR 1 kHz discrete transfer functions of the byte-exact recurrences (floors ignored -- they add
<= 1-count dither, see c3).  T is the delivered lane torque (T counts, the 427 tap's unit); omega is the
steering-wheel rate in deg/s (x = 8 counts per deg/s, EVIDENCE per the V294 redo).

  fb former (0x28F86..0x28FA8, V294 'diff'):  r26 = (b/1024)(1 - z^-1)/(1 - (a/1024) z^-1) * 8*omega
  P (0x29E36/0x29E3E):                          P = -(Kp/256) r26            (the trim part of E = 4 sp - r26)
  taper (0x2A0B4..0x2A0C2):                     x 254/256 at rest
  output lag (0x2A174..0x2A1B0):                y = (1 + z^-1)/32 * (bo/1024)/(1 - (ao/1024) z^-1) * S
  delivery (0x2A1FE/0x2A202):                   T = y * gain/32768 (gain 5346, pol cancels)
Decomposition:  T/omega = -(K_B + j w K_J)  ->  K_B = -Re(H) [T per deg/s, damping], K_J = -Im(H)/w [T per deg/s^2, inertia]
No plant, no loop: this is the CONTROLLER's own response.  The closed-loop consequence needs the plant (BELIEF).

Run:  python c6_trim_response.py
"""
import cmath
import math

TS = 1e-3


def H(f, a=1011, b=567, kp=960, ao=992, bo=507, gain=5346, taper=254):
    w = 2 * math.pi * f
    z1 = cmath.exp(-1j * w * TS)
    fb = (b / 1024) * (1 - z1) / (1 - (a / 1024) * z1) * 8          # r26 per deg/s
    out = (1 + z1) / 32 * (bo / 1024) / (1 - (ao / 1024) * z1)      # y per S
    return -(kp / 256) * fb * (taper / 256) * out * gain / 32768     # T per deg/s


def row(label, **kw):
    fs = (0.3, 1.0, 2.0, 2.5, 3.0, 5.0, 10.0, 20.0)
    cells = []
    for f in fs:
        h = H(f, **kw)
        w = 2 * math.pi * f
        KB = -h.real
        KJ = -h.imag / w
        ph = math.degrees(cmath.phase(-h))          # 0 deg = pure rate damping, +90 = pure inertia (acceleration)
        cells.append(f"{f:>4}Hz |{abs(h):5.2f}| {ph:+4.0f}deg")
    print(f"{label:34s} " + "  ".join(cells))


def main():
    print("|T/omega| in T counts per deg/s, and phase of the opposing torque: 0 = pure damping, +90 = pure inertia\n")
    row("V294 as built (1011, 567, Kp 960)")
    print("\n-- the pole a (b held) : moves the inertia->damping crossover --")
    for a in (1017, 1005, 993, 975, 923):
        row(f"a {a} b 567", a=a)
    print("\n-- the pole a with b scaled to hold the BELOW-pole inertia gain b/(1024-a) --")
    for a in (1017, 1005, 993, 975):
        row(f"a {a} b {round(567 * (1024 - a) / 13)}", a=a, b=round(567 * (1024 - a) / 13))
    print("\n-- b (or equivalently Kp, which also scales the FEEDFORWARD) : pure gain --")
    for b in (284, 1134, 2268):
        row(f"a 1011 b {b}", b=b)
    print("\n-- the output lag (0xC63EC/0xC63EE, DC held ~0.99) : adds phase to the trim AND the feedforward --")
    for ao in (960, 976, 1000):
        bo = round(0.990234375 * 16 * (1024 - ao))
        row(f"out-lag a {ao} b {bo}", ao=ao, bo=bo)
    # the inertia (K_J, T per deg/s^2) at 0.3 Hz and the damping (K_B, T per deg/s) at 2.5 Hz, as built
    h03, h25 = H(0.3), H(2.5)
    print(f"\nAS BUILT: K_J(0.3 Hz) = {-h03.imag / (2 * math.pi * 0.3):.4f} T per deg/s^2 ; "
          f"K_B(2.5 Hz) = {-h25.real:.3f} T per deg/s, K_J(2.5 Hz) = {-h25.imag / (2 * math.pi * 2.5):.4f} T per deg/s^2")


if __name__ == "__main__":
    main()
