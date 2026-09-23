"""Compare the design's quasi-static zeta (v294_design.mode_analysis) with EXACT closed-loop poles on IDENTICAL inputs."""
import os, sys, math
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v294")
import v294_design as D
import numpy as np
from rp3_wheel_mode import loop, closed_poles, mode
print("design constants: COUNTS_PER_TQ", D.COUNTS_PER_TQ, " k_alpha(1011,567) =", D.k_alpha(1011, 567))
print(" v    k(design, levelled)  | design quasi-static: zeta0 -> zeta1 (x)  f1 | EXACT poles, same k/J/b, d=1 m=1: zeta0 -> zeta1 (x) f_n | EXACT, map k (unlevelled)")
for v in (5.0, 8.0, 12.5, 19.0, 26.0):
    m = D.mode_analysis(v, 1011, 567, 1.5e-3, "light")
    k = D.k_of_v(v)
    Ln0, Ld0 = loop(8e-5, 6e-4, k, d=1, m=1, gain=0.0); z0 = mode(closed_poles(Ln0, Ld0), 0.1, 8)
    Ln, Ld = loop(8e-5, 6e-4, k, d=1, m=1); z1 = mode(closed_poles(Ln, Ld), 0.1, 8)
    km = float(np.interp(v, D.HOLD_V_BP, D.HOLD_K_V))
    Ln0, Ld0 = loop(8e-5, 6e-4, km, d=1, m=1, gain=0.0); y0 = mode(closed_poles(Ln0, Ld0), 0.1, 8)
    Ln, Ld = loop(8e-5, 6e-4, km, d=1, m=1); y1 = mode(closed_poles(Ln, Ld), 0.1, 8)
    print(f"{v:5.1f}  {k:.5f}             | {m['zeta0']:.3f} -> {m['zeta1']:.3f} (x{m['zeta1']/m['zeta0']:.2f}) {m['f1']:.2f} Hz"
          f"  | {z0[0]:.3f} -> {z1[0]:.3f} (x{z1[0]/z0[0]:.2f}) {z1[1]:.2f} Hz | x{y1[0]/y0[0]:.2f}")
