import numpy as np
fs=1000.0
def L(f,a2,d,a1=37/128):
    z=np.exp(1j*2*np.pi*f/fs)
    lp1=a1/(1-(1-a1)/z); lp2=a2/(1-(1-a2)/z)
    return lp1*lp2*z**(-d)
fr=np.linspace(1,499,4990)
for a2n in (22,14):
  a2=a2n/64
  for d in (1,2,3):
    ph=np.unwrap(np.angle(L(fr,a2,d)))
    i=np.argmax(ph<=-np.pi)
    if ph.min()>-np.pi: print(a2n,d,'no -180 crossing below Nyquist');continue
    f=fr[i]; m=abs(L(f,a2,d))
    print(f"alpha2={a2n} d={d}: -180deg at {f:.0f} Hz, |L| per unit g={m:.3f} -> g_crit={1/m:.2f}; alias at 100Hz={abs(((f+50)%100)-50):.1f}Hz")
# plant: wheel speed from torque: rate = tau/(J s): L = g*LP1*LP2*z^-d with g=K'T/J (discretised derivative cancels integrator)
