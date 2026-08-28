import numpy as np
FS=1000.0
def H(f,alpha,shift=1024.0):
    a=alpha/shift; w=2*np.pi*f/FS
    return a/(1-(1-a)*np.exp(-1j*w))
print("CAN THE FRICTION EMA POLE (0xC40D0) SEPARATE 'FEEL' FROM 'OSCILLATION'?")
print("  friction = EMA_alpha(|model| * K1/1024 * sat(rate)).  DC gain is 1 for any alpha,")
print("  so lowering alpha keeps the DC (steering-feel) term and attenuates 7.42 Hz.\n")
print("  alpha |  |H| @0.5Hz  |H| @7.42Hz  phase@7.42  | ANTI-DAMP (|H|cos) | INERTIA (|H|sin)")
for al in (408,200,100,56,28,14,7):
    h05=H(0.5,al); h=H(7.42,al); ph=-np.angle(h)
    ad=abs(h)*np.cos(ph); inr=abs(h)*np.sin(ph)
    print("  %4d  |   %6.4f      %6.4f     %6.2f deg |      %6.4f        |    %6.4f"
          %(al,abs(h05),abs(h),np.degrees(ph),ad,inr))
print("\n  vs V112 baseline (alpha 408): anti-damping 1.000, inertia 0.070")
b=H(7.42,408); bp=-np.angle(b); bad=abs(b)*np.cos(bp); bin_=abs(b)*np.sin(bp)
print("  alpha |  anti-damping vs V112  |  inertia vs V112  |  DC feel kept")
for al in (408,200,100,56,28,14):
    h=H(7.42,al); ph=-np.angle(h)
    print("  %4d  |        %6.3f          |      %6.2fx      |     %6.4f"
          %(al,abs(h)*np.cos(ph)/bad,(abs(h)*np.sin(ph))/bin_,abs(H(0.5,al))))
print("\n  COMPARE: V113's K1 cut gives anti-damping 0.333 at EVERY frequency,")
print("  with NO added inertia and NO added phase.")
