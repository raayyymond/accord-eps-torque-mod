import numpy as np
FS=1000.0
def parts(f,a2,a_lp=37):
    w=2*np.pi*f/FS; z=np.exp(1j*w); a=a_lp/128.0; b=a2/64.0
    H=64*(a/(1-(1-a)/z))*(1-1/z)*(b/(1-(1-b)/z))
    Hr=H/(1j*w); phi=-np.angle(Hr); m=np.abs(Hr)*w
    return m*np.sin(phi), m*np.cos(phi)      # damping, mass
def band(a2,lo,hi,which=0):
    fs=np.arange(lo,hi+0.001,0.5)
    return np.mean([parts(f,a2)[which] for f in fs])
print("DOSE CHOICE -- damping by BAND, relative to V111 (a2=14)")
print("  the Re(Z) profile: 6-16 Hz is DEEPLY anti-damped (-33..-67);")
print("  20-24 Hz is nearly neutral (-3..-5); above f0~23.3 Hz it is already DAMPED.\n")
print("  a2 | 6-16Hz dmp | 20-30Hz dmp | 6-16Hz mass | peak Hz | bb rms")
ff=np.linspace(0.5,499,4000)
def bb(a2,a_lp=37):
    w=2*np.pi*ff/FS; z=np.exp(1j*w); a=a_lp/128.0; b=a2/64.0
    return np.sqrt(np.mean(np.abs(64*(a/(1-(1-a)/z))*(1-1/z)*(b/(1-(1-b)/z)))**2))
for a2 in (22,14,10,8,7,6,5,4,3):
    d1=band(a2,6,16)/band(14,6,16); d2=band(a2,20,30)/band(14,20,30)
    m1=band(a2,6,16,1)/band(14,6,16,1)
    w=2*np.pi*ff/FS; z=np.exp(1j*w); a=37/128.0; b=a2/64.0
    mag=np.abs(64*(a/(1-(1-a)/z))*(1-1/z)*(b/(1-(1-b)/z)))
    tag = "  <- V111" if a2==14 else ("  <- V108" if a2==22 else "")
    print("  %2d |   %6.3f   |   %6.3f    |   %6.3f    | %6.1f  | %6.3f%s"
          %(a2,d1,d2,m1,ff[np.argmax(mag)],bb(a2)/bb(14),tag))
print("\n  READ: damping in the DEEP band peaks at a2=4, but a2=4 gives back 27% of the")
print("  20-30 Hz damping that V106's win was measured in.  a2=6 keeps 97% of the 6-16 Hz")
print("  gain while giving back only ~7% at 20-30 Hz.  That is the balanced dose.")
