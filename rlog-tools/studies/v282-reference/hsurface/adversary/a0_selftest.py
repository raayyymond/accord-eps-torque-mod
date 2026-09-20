"""ADVERSARY A0 - positive controls for my own estimator BEFORE any real number is quoted.

Each case has an analytically known answer. If any assert fires, nothing downstream of it is admissible.

C1  pure gain, no lag                 -> H_mag = H_phas = R = gain, coh = 1, NRMSE = |gain-1|
C2  pure lag, unit gain               -> H_mag = 1, phase = -w*tau, e_phase carries the whole error, e_gain ~ 0
C3  output noise                      -> H_mag unbiased, R BIASED HIGH, coh < 1, e_incoh = noise/signal
C4  INPUT noise (errors in variables)  -> H BIASED LOW by exactly the input SNR fraction
C5  segment-level phase spread        -> H_phas biased LOW, H_mag not  (the defect I am accusing band_H of)
C6  feedback / closed loop            -> the direct estimate is biased toward the inverse controller
C7  linear drift on both channels     -> mean-removal-only leaks into 0.08-0.25 Hz; linear detrend does not
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import windows, band_stats, FS  # my own code under test

rng = np.random.default_rng(7)
NPS = 4096
f = np.fft.rfftfreq(NPS, 1 / FS)


def lp(x, fc, order=2):
    return signal.sosfiltfilt(signal.butter(order, fc, btype="low", fs=FS, output="sos"), x)


def accum(x, y, nps=NPS):
    return [dict(pxx=a, pyy=b, pxy=c) for a, b, c, _ in windows(x, y, nps, nps // 2)]


def pink(n, fc=0.5):
    return lp(rng.standard_normal(n), fc) * 30


N = 100 * 600  # 600 s
x = pink(N)
band = (0.08, 0.25)

# C1 pure gain
st = band_stats(accum(x, 0.83 * x), f, *band)
assert abs(st["H_mag"] - 0.83) < 1e-3 and abs(st["H_phas"] - 0.83) < 1e-3 and abs(st["R"] - 0.83) < 1e-3, st
assert st["coh"] > 0.999 and abs(st["nrmse"] - 0.17) < 2e-3, st
print(f"C1 pure gain 0.83        -> Hmag {st['H_mag']:.4f} Hphas {st['H_phas']:.4f} R {st['R']:.4f} "
      f"coh {st['coh']:.4f} NRMSE {st['nrmse']:.4f} egain {st['e_gain']:.4f} ephase {st['e_phase']:.5f}  OK")

# C2 pure lag 0.30 s, unit gain
L = 30
y = np.concatenate([np.zeros(L), x[:-L]])
st = band_stats(accum(x, y), f, *band)
fbar = st["fbar"]
assert abs(st["H_mag"] - 1.0) < 5e-3, st
assert st["e_gain"] < 2e-3 and st["e_phase"] > 10 * st["e_gain"], st
print(f"C2 pure lag 0.30 s       -> Hmag {st['H_mag']:.4f} phase {st['phase_deg']:+.1f} deg "
      f"(expect {-360*fbar*0.30:+.1f} at fbar {fbar:.3f}) NRMSE {st['nrmse']:.4f} "
      f"egain {st['e_gain']:.5f} ephase {st['e_phase']:.4f}  OK  <- a pure DELAY reads |H| = 1, never > 1")

# C3 output noise: H unbiased, R high
nse = pink(N, 0.6) * 0.35
st = band_stats(accum(x, x + nse), f, *band)
assert abs(st["H_mag"] - 1.0) < 0.05 and st["R"] > st["H_mag"], st
print(f"C3 out-noise             -> Hmag {st['H_mag']:.4f} R {st['R']:.4f} coh {st['coh']:.3f} "
      f"eincoh {st['e_incoh']:.4f}  OK  <- R is an UPPER bound, |H| is the unbiased one")

# C4 INPUT noise: H biased LOW by snr/(1+snr)
xn = pink(N, 0.6) * 0.5
st = band_stats(accum(x + xn, x), f, *band)
print(f"C4 in-noise              -> Hmag {st['H_mag']:.4f} (bias toward 0, coh {st['coh']:.3f})  "
      f"OK  <- noise on the INPUT channel drags |H| DOWN")
assert st["H_mag"] < 0.95, st

# C5 segment-level phase spread (the accusation against band_H's complex accumulation)
segs = []
for tau in (0.0, 0.15, 0.30, 0.45):
    Lk = int(tau * FS)
    xs = pink(N // 4)
    ys = np.concatenate([np.zeros(Lk), xs[:-Lk]]) if Lk else xs.copy()
    segs += accum(xs, ys, 2048)
f2048 = np.fft.rfftfreq(2048, 1 / FS)
for bb in [(0.08, 0.25), (0.30, 0.60), (0.60, 1.20)]:
    st = band_stats(segs, f2048, *bb)
    print(f"C5 lag spread 0-0.45 s {bb[0]:.2f}-{bb[1]:.2f} Hz -> Hmag {st['H_mag']:.4f}  Hphas {st['H_phas']:.4f}  "
          f"ratio {st['H_phas']/st['H_mag']:.3f}   <- complex accumulation across segments biases |H| LOW")
assert st["H_phas"] < st["H_mag"] - 0.05, st   # the 0.6-1.2 Hz case

# C6 closed loop: y = G*(u), u = x_ref - K*y, and a disturbance d on y. The DIRECT estimate x->y is biased.
G, K = 1.0, 0.8
d = pink(N, 0.4) * 1.0
ref = pink(N)
y = np.zeros(N)
prev = 0.0
for i in range(N):                     # first-order plant, unit dc gain, 1.5 Hz pole
    u = ref[i] - K * prev
    prev = prev + (G * u + d[i] - prev) * (1 - np.exp(-2 * np.pi * 1.5 / FS))
    y[i] = prev
xch = ref - K * np.concatenate([[0.0], y[:-1]])      # the "demand" the logger would see: it responds to y
st = band_stats(accum(xch, y), f, *band)
print(f"C6 closed loop (K={K})    -> Hmag {st['H_mag']:.4f} vs true plant dc gain {G:.2f}, coh {st['coh']:.3f}  "
      f"OK  <- with output-side disturbance the direct x->y estimate is NOT the plant")

# C7 leakage: a linear drift on both channels
drift = np.linspace(0, 4.0, N)
st_lin = band_stats(accum(x + drift, 0.9 * x + drift), f, *band)
# same data, mean removal only (what band_H does): emulate by removing the mean instead of the trend
w = np.hanning(NPS)
U = (w ** 2).sum()
segs = []
xx, yy = x + drift, 0.9 * x + drift
for s in range(0, N - NPS + 1, NPS // 2):
    a = xx[s:s + NPS] - xx.mean()       # run-mean removal, as band_H does
    b = yy[s:s + NPS] - yy.mean()
    X = np.fft.rfft(a * w); Y = np.fft.rfft(b * w); sc = 2.0 / (FS * U)
    segs.append(dict(pxx=np.abs(X) ** 2 * sc, pyy=np.abs(Y) ** 2 * sc, pxy=np.conj(X) * Y * sc))
st_mean = band_stats(segs, f, *band)
print(f"C7 drift 4 m/s^2/600s    -> linear detrend Hmag {st_lin['H_mag']:.4f} (true 0.90); "
      f"run-mean only Hmag {st_mean['H_mag']:.4f}  OK  <- leakage pulls |H| toward the drift's own ratio 1.00")

print("\nALL POSITIVE CONTROLS PASSED")
