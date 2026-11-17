"""Find and characterise the ~15 Hz buzz on the A340 user route. Reads the npz cache only (seconds)."""
import sys, os, glob
import numpy as np
from scipy import signal

C = sys.argv[1]
FS = 100.0


def s16(d, i):
    return ((d[:, i].astype(np.int32) << 8) | d[:, i + 1]).astype(np.int16).astype(float)


def load(seg):
    z = np.load(os.path.join(C, "seg%02d.npz" % seg))
    t0 = float(z["t0"])
    t = z["t_14a"] - t0
    n = len(t)
    ang = -0.1 * s16(z["d_14a"], 0)
    rate = -1.0 * s16(z["d_14a"], 2)
    tq = -1.0 * s16(z["d_18f"], 0)[:n]           # driver torque sensor
    cmd = s16(z["d_e4"], 0)                       # 0xE4 STEER_TORQUE
    req = (z["d_e4"][:, 2] >> 7) & 1
    te4 = z["t_e4"] - t0
    cmd = np.interp(t, te4, cmd); req = np.interp(t, te4, req) > 0.5
    mt = z["d_1ab"]
    mtq = (((mt[:, 0].astype(np.int32) & 0x03) << 8) | mt[:, 1])  # MOTOR_TORQUE raw 10b (unverified layout)
    cs = z["cs"]
    v = np.interp(t, cs[:, 0] - t0, cs[:, 1])
    return dict(t=t, ang=ang, rate=rate, tq=tq, cmd=cmd, req=req, v=v, raw14a=z["d_14a"], raw18f=z["d_18f"])


def band_env(x, lo, hi, win=0.5):
    b, a = signal.butter(4, [lo / (FS / 2), hi / (FS / 2)], "band")
    y = signal.filtfilt(b, a, x)
    k = int(win * FS)
    return np.sqrt(np.convolve(y * y, np.ones(k) / k, "same")), y


def peakf(x, t, tc, half=0.6):
    m = (t > tc - half) & (t < tc + half)
    xx = signal.detrend(x[m])
    f, p = signal.periodogram(xx * np.hanning(len(xx)), FS, nfft=1024)
    k = (f > 5) & (f < 45)
    return f[k][np.argmax(p[k])]


segs = sorted(int(os.path.basename(p)[3:5]) for p in glob.glob(os.path.join(C, "seg*.npz")))
allrows = []
for sg in segs:
    d = load(sg)
    t = d["t"]
    env_tq, _ = band_env(d["tq"], 11, 20)
    env_rt, _ = band_env(d["rate"], 11, 20)
    # whole-seg PSD of driver torque
    f, p = signal.welch(signal.detrend(d["tq"]), FS, nperseg=256)
    k = (f > 5) & (f < 45)
    print("seg %2d  dur %.0fs  tq PSD peak 5-45Hz at %.1f Hz | env_tq p50 %.2f p99 %.2f max %.2f | env_rate p99 %.2f max %.2f"
          % (sg, t[-1], f[k][np.argmax(p[k])], np.median(env_tq), np.percentile(env_tq, 99), env_tq.max(),
             np.percentile(env_rt, 99), env_rt.max()))
    thr = max(6 * np.median(env_tq), 3.0)
    on = env_tq > thr
    edges = np.flatnonzero(np.diff(on.astype(int)))
    if on[0]: edges = np.r_[0, edges]
    if on[-1]: edges = np.r_[edges, len(on) - 1]
    for a, b in zip(edges[::2], edges[1::2]):
        if (b - a) < 20: continue
        i = a + np.argmax(env_tq[a:b])
        towards = np.sign(d["ang"][i]) * np.sign(np.mean(d["rate"][max(0, i - 10):i + 10])) < 0
        row = (sg, t[a], t[b], t[i], env_tq[i], env_rt[i], peakf(d["tq"], t, t[i]), peakf(d["rate"], t, t[i]),
               d["ang"][i], np.mean(d["rate"][max(0, i - 10):i + 10]), d["v"][i], d["cmd"][i], int(d["req"][i]), int(towards),
               np.mean(d["tq"][max(0, i - 25):i + 25]))
        allrows.append(row)
print()
print("seg  t_on  t_off  t_pk  envTq envRate fTq  fRate   ang   rate    v   cmd req toC meanTq")
for r in allrows:
    print("%3d %5.1f %5.1f %5.1f  %5.1f %5.1f  %4.1f %4.1f  %6.1f %6.1f %5.1f %6.0f  %d   %d  %6.0f" % r)
a = np.array(allrows)
if len(a):
    print("\nbursts %d | toward-centre %.0f%% | engaged(req) %.0f%% | f median %.1f Hz (IQR %.1f-%.1f) | |ang| median %.0f deg (p10 %.0f p90 %.0f) | v median %.1f m/s"
          % (len(a), 100 * a[:, 13].mean(), 100 * a[:, 12].mean(), np.median(a[:, 6]), *np.percentile(a[:, 6], [25, 75]),
             np.median(abs(a[:, 8])), *np.percentile(abs(a[:, 8]), [10, 90]), np.median(a[:, 10])))
    np.save(os.path.join(C, "bursts.npy"), a)
