"""ADV-bytes 11: my own closed form of the trim's opposing torque per wheel rate (no rate-former window), a check on the
design's d1/d6 'damping part' numbers.  T_opp/omega = 8 * H_fb * (960/256) * (254/256) * H_lag * (5346/32768)."""
import numpy as np, math
def tf(a, f, b=567, la=992, lb=507, w=0):
    z1 = np.exp(-2j*np.pi*f*1e-3)
    Hfb = (b/1024)*(1-z1)/(1-a/1024*z1)
    Hlag = (1+z1)/32*(lb/1024)/(1-la/1024*z1)
    Hw = 1.0 if not w else (1-z1**w)/(w*(1-z1))          # optional w-ms rate-former window
    return 8*Hfb*Hw*3.75*(254/256)*Hlag*(5346/32768)
for w in (0, 3):
    print("rate-former window %d ms" % w)
    for f in (1.0, 2.0, 2.5, 3.0, 5.0, 20.0):
        r = [tf(a, f, w=w) for a in (1011, 1017)]
        print("  %5.1f Hz: V294 |T/w| %.2f angle %+5.1f damping %.2f | A1017 |T/w| %.2f angle %+5.1f damping %.2f" % (
            f, abs(r[0]), math.degrees(np.angle(r[0])), r[0].real, abs(r[1]), math.degrees(np.angle(r[1])), r[1].real))
    # damping peak
    fg = np.linspace(0.5, 8, 3000)
    for a in (1011, 1017):
        dp = np.array([tf(a, f, w=w).real for f in fg]); print("  a=%d damping peak %.2f T/(deg/s) at %.2f Hz" % (a, dp.max(), fg[dp.argmax()]))
    # K_alpha below the pole: T_opp / alpha at 0.05 Hz
    for a in (1011, 1017):
        f = 0.02; print("  a=%d K_alpha (T per deg/s^2 at %.2f Hz) %.4f" % (a, f, abs(tf(a, f, w=w))/(2*np.pi*f)))
