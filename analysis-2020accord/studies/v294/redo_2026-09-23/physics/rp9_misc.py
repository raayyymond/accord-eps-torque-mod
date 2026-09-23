import math, numpy as np
from rp3_wheel_mode import loop, closed_poles, mode, s_of, crossings, k_of
print("INVERTED sign (gain -1), light b: unstable poles (s-plane, Hz) ")
for v in (5, 8, 19, 26):
    for g in (-1.0, -0.5):
        P = closed_poles(*loop(8e-5, 6e-4, k_of(v), gain=g))
        S = s_of(P[np.abs(P) >= 1.0])
        print(f"  v {v} gain {g}: max|z| {abs(P).max():.4f}; unstable: " + ", ".join(f"{s.real:+.1f}{s.imag/2/math.pi:+.2f}Hz" for s in S if s.imag >= 0))
print("\nloop gain with the design's LEVELLED k (x1.15 <=12.5 -> x1.45 >=17.5), light b, d=1 m=3")
for v in (12.5, 19, 26):
    kk = k_of(v) * float(np.interp(v, [12.5, 17.5], [1.15, 1.45]))
    Ln, Ld = loop(8e-5, 6e-4, kk)
    f, L, cr = crossings(Ln, Ld)
    i = np.argmin(abs(f - 2.4)); im = np.argmax(abs(L))
    print(f"  v {v}: |L|(2.4 Hz) {abs(L[i]):.2f}; max |L| {abs(L[im]):.2f} at {f[im]:.2f} Hz phase {np.degrees(np.angle(L[im])):+.0f}; min Re L {L.real.min():+.3f}; -180: " +
          "; ".join(f"{c[0]:.1f} Hz |L| {c[1]:.3f}" for c in cr))
