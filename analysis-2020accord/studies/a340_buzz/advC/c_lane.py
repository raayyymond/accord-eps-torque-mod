# own derivation: lane local loop L(z)=g*LP1(37/128)*LP2(a2/64)*z^-d on a ZOH inertia (rate integrates torque; d(rate) cancels integrator)
import numpy as np
from scipy.optimize import brentq
fs=1000.
def L(f,a2,d,a1=37/128):
    z=np.exp(1j*2*np.pi*f/fs); return a1/(1-(1-a1)/z)*a2/(1-(1-a2)/z)*z**(-d)
fr=np.linspace(1,499,9980)
gc={}
for a2n in (22,14):
  for d in (1,2,3,4):
    ph=np.unwrap(np.angle(L(fr,a2n/64,d))); 
    if ph.min()>-np.pi: print(a2n,d,'no crossing'); continue
    i=np.argmax(ph<=-np.pi); f=np.interp(-np.pi,[ph[i],ph[i-1]],[fr[i],fr[i-1]]) if False else fr[i]
    g=1/abs(L(f,a2n/64,d)); gc[(a2n,d)]=(g,f)
    print(f'a2={a2n} d={d}: g_crit={g:.2f} f_-180={f:.0f} Hz alias100={abs(((f+50)%100)-50):.1f} Hz')
print('ratio gcrit22/gcrit14 (dB):',[round(20*np.log10(gc[(22,d)][0]/gc[(14,d)][0]),2) for d in (2,3) if (22,d) in gc and (14,d) in gc])
print('stock-to-REV3 gain ratio: x3 (<=5.6 m/s) -> %.2f dB ; x4.45(16m/s) %.2f dB; x8.14 %.2f dB'%(20*np.log10(3),20*np.log10(4.46),20*np.log10(8.14)))
# DF: saturation (+-c): N(A)=2/pi(asin(c/A)+c/A sqrt(1-(c/A)^2)); limit cycle at g*N=g_crit
def N(r): # r=c/A<=1
    return 2/np.pi*(np.arcsin(r)+r*np.sqrt(1-r*r))
print('DF amplitude (A/c = clamp-normalised lane-input amplitude) vs overdrive g/g_crit:')
for od in (1.05,1.2,1.5,2,3,5):
    r=brentq(lambda r:N(r)-1/od,1e-6,1.0); print(f'  g/gcrit={od}: A/c={1/r:.2f}  (output sits at the clamp for A/c>1)')
print('=> at g/gcrit>=1.5 the lane output is >85% clamp-limited; the oscillation AMPLITUDE in rate is set by the clamp/plant: A_rate ~ c/(g*Ldc) -- scale-dependent (needs J_m)')
