"""EXP B: long constant-setpoint holds (30 s) under road disturbances -- does C0 HUNT (a self-sustained stick-slip /
quantiser limit cycle) or ratchet against a slowly varying load?  The harness's holds are 2-3 s with no disturbance.
Disturbance d is a torque on the wheel in T counts (+ left): 0, a constant 1.5 Fs (crown), a 0.05 Hz sinusoid of
amplitude 2 Fs (crown / crosswind drift), and 0-1 Hz band-limited noise of rms Fs (gusts / road)."""
import sys, json, time
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
SPEEDS = tuple(float(s) for s in sys.argv[2].split(",")) if len(sys.argv) > 2 else (3.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.5, 19.0, 26.0)
member = sys.argv[1] if len(sys.argv) > 1 else "nominal"
fam = F.VP.family()
DUR = 30.0
rng = np.random.default_rng(7)
nb = int(DUR * 1000) + 10
from scipy import signal
sos = signal.butter(2, 1.0, "low", fs=1000.0, output="sos")
base_noise = signal.sosfilt(sos, rng.normal(0, 1, nb))
base_noise /= base_noise[5000:].std()
cols = []
for v in SPEEDS:
    Fs = fam[member].at(v).Fs
    for kind in ("d0", "crown", "drift", "gust"):
        if kind == "d0":
            d = 0.0
        elif kind == "crown":
            d = (lambda t, a=1.5 * Fs: a if t > 1.0 else a * t)
        elif kind == "drift":
            d = (lambda t, a=2 * Fs: a * np.sin(2 * np.pi * 0.05 * t))
        else:
            d = (lambda t, a=Fs: a * base_noise[int(t * 1000)])
        # a 0.3 deg step at t = 1 s to start from a non-equilibrium point, then a constant setpoint
        cols.append(dict(member=member, v=v, kind=kind, Fs=Fs, d=d, ref=lambda t: 0.3 if t >= 1.0 else 0.0))
t0 = time.time()
rec = F.run(cols, DUR, rec_I=True)
tt = np.arange(rec["th"].shape[0]) * 1e-3
w = tt >= 5.0
res = []
print("member %s  [%.0f s]" % (member, time.time() - t0))
print("  v    kind    Fs   | slips/25s  maxjump  | err p2p deg  err rms | T 0.3-5Hz rms  T 5-30Hz rms | th dominant f (Hz)")
from scipy import signal as S
for j, c in enumerate(cols):
    th = rec["th"][:, j].astype(float); om = rec["om"][:, j].astype(float); T = rec["T"][:, j].astype(float)
    sp = rec["sp"][:, j].astype(float)
    # jumps after stuck intervals
    stuck = om == 0.0
    runs = F.HT._runs(stuck[w], 100)
    thw = th[w]
    jumps = [abs(thw[min(b + 500, len(thw) - 1)] - thw[b - 1]) for a, b in runs if b < len(thw) - 1]
    nsl = sum(1 for x in jumps if x >= 0.1)
    mj = max(jumps) if jumps else 0.0
    e = (sp - th)[w]
    Tl = HT_bp = S.sosfiltfilt(S.butter(2, [0.3, 5.0], "bandpass", fs=1000, output="sos"), T)[w]
    Th = S.sosfiltfilt(S.butter(2, [5.0, 30.0], "bandpass", fs=1000, output="sos"), T)[w]
    f, P = S.welch(th[w] - th[w].mean(), fs=1000, nperseg=8192)
    fd = f[1:][np.argmax(P[1:])]
    res.append(dict(v=c["v"], kind=c["kind"], slips=nsl, maxjump=mj, e_p2p=float(e.max() - e.min()), e_rms=float(e.std()), Tl=float(Tl.std()), Th=float(Th.std()), fdom=float(fd)))
    print("%5.1f  %-6s %5.1f | %4d   %6.2f  | %6.2f  %6.3f | %7.1f  %7.2f | %5.2f" % (c["v"], c["kind"], c["Fs"], nsl, mj, e.max() - e.min(), e.std(), Tl.std(), Th.std(), fd))
(OUT / ("expB_%s.json" % member)).write_text(json.dumps(res))
np.savez_compressed(OUT / ("expB_%s.npz" % member), th=rec["th"][::5], T=rec["T"][::5], I=rec["I"][::5], sp=rec["sp"][::5])
