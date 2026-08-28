import numpy as np
FS=1000.0
# EXACT chain from FUN_00041464 decompile:
#   y[n]  = y[n-1] + ((x[n]<<10 - y[n-1]) * 37) >> 7          alpha_lp = cal 0xC643C
#   d[n]  = y[n] - y[n-1]                                      first difference
#   acc   = clamp(d*32, +-0xfa0000)
#   s[n]  = s[n-1] + ((acc - s[n-1]) * a2) >> 6                a2 = cal 0xC40DC
#   gp-0x6c2c = s >> 9
# then FUN_00036c12:  gp-0x6b26 = clamp(-K * gp-0x6c2c, +-511)
def H_chain(f, a2, a_lp=37, shift_lp=7, shift_2=6):
    w = 2*np.pi*f/FS; z = np.exp(1j*w)
    a = a_lp/(1<<shift_lp)
    Hlp = a/(1-(1-a)/z)                    # one-pole LP on rate
    Hd  = (1-1/z)                          # first difference
    b   = a2/(1<<shift_2)
    He  = b/(1-(1-b)/z)                    # EMA A
    return Hlp*Hd*He                       # (x1024 and x32 are constant scales)

F = np.array([2,4,6,8,10,12,14,16,20,24,30,40,61,80])
print("gp-0x6b26 lane -- DAMPING vs MASS decomposition, by alpha2 (cal 0xC40DC)")
print("  gp-0x6b26 = -K*gp-0x6c2c ;  vs the VELOCITY phasor the term splits into")
print("     DAMPING  ~ |H|*sin(phi)   (opposes velocity -- what 6-16 Hz needs)")
print("     MASS     ~ |H|*cos(phi)   (apparent inertia -- what the operator does NOT want)\n")
A2 = [22, 14, 8, 6, 4, 3]
print("  f Hz |" + "".join("  a2=%-2d dmp  mass" % a for a in A2))
for f in F:
    row = ""
    for a2 in A2:
        H = H_chain(f, a2)
        # split the chain: the differencer already supplies the +90 deg; measure the
        # residual phase of the LP*EMA part relative to a pure differentiator
        Hres = H / (1j*2*np.pi*f/FS)
        phi = -np.angle(Hres); m = np.abs(Hres)*(2*np.pi*f/FS)
        row += "   %6.4f %6.4f" % (m*np.sin(phi), m*np.cos(phi))
    print("  %4.0f |%s" % (f, row))

print("\n  RATIOS vs V111 (a2=14), in the anti-damped band 6-16 Hz:")
print("   a2   DAMPING x   MASS x     (want: damping UP, mass DOWN)")
for a2 in A2:
    d=[];m=[]
    for f in (6,8,10,12,14,16):
        H=H_chain(f,a2)/(1j*2*np.pi*f/FS); phi=-np.angle(H); mag=np.abs(H)*(2*np.pi*f/FS)
        H0=H_chain(f,14)/(1j*2*np.pi*f/FS); p0=-np.angle(H0); m0=np.abs(H0)*(2*np.pi*f/FS)
        d.append(mag*np.sin(phi)/(m0*np.sin(p0))); m.append(mag*np.cos(phi)/(m0*np.cos(p0)))
    print("   %2d    %6.3f     %6.3f" % (a2, np.mean(d), np.mean(m)))

print("\n  WHERE THE LANE PEAKS (|H| max) -- the 'bandpass centre':")
ff=np.linspace(1,200,4000)
for a2 in A2:
    mag=np.abs(H_chain(ff,a2))
    print("   a2=%-2d  peak at %5.1f Hz   |H| at 10 Hz / peak = %.3f" %
          (a2, ff[np.argmax(mag)], np.abs(H_chain(10.,a2))/mag.max()))
