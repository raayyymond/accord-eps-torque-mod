# -*- coding: utf-8 -*-
"""PROSPECTIVE PREDICTION for V121: how much should the harmonic ratio fall?

The relay is  fVar13 = clamp(POL * gp-0x6abc * 12 / knee, +-1),  gp-0x6abc = 4.7121 ct/(deg/s).
It is a memoryless nonlinearity, so I can feed the MEASURED rate signal from the V112 drives
through it at knee 1800 (what flew) and knee 3000 (V121) and compare the harmonic content of
the two outputs directly. No new drive needed to make the prediction; the drive tests it.

This mirrors the saturation-duty model that made a correct prospective call for V112
(predicted 0.2353, measured 0.3102 / 0.1071).

Measured on the wire, V112 routes r22+r23: harmonic ratio 0.970 and 1.455, median 1.213.
The prediction below is a RATIO of ratios -- how far knee 3000 moves it relative to knee 1800 --
so it does not depend on the absolute calibration of the statistic.

FALSIFIER: if V121 flies and the harmonic ratio does NOT fall by roughly the predicted factor,
the relay is not the excitation path for the 7-9 Hz mode.
"""
import numpy as np, os
from scipy import signal

FS, NW, CT = 100.0, 512, 4.7121
f = signal.welch(np.zeros(NW), FS, nperseg=NW)[1] * 0 + signal.welch(np.zeros(NW), FS, nperseg=NW)[0]
b69 = (f >= 6) & (f <= 9)


def prom(P, ft, hw=1.0, gap=0.4):
    pk = (f >= ft - gap) & (f <= ft + gap)
    sh = (((f >= ft - hw - gap) & (f < ft - gap)) | ((f > ft + gap) & (f <= ft + hw + gap)))
    if pk.sum() == 0 or sh.sum() == 0:
        return np.nan
    return P[pk].max() / max(np.median(P[sh]), 1e-30)


def harmonic_ratio_of(sigs):
    h, c = [], []
    for x in sigs:
        _, P = signal.welch(x - np.mean(x), FS, nperseg=NW, noverlap=NW // 2)
        f0 = f[b69][np.argmax(P[b69])]
        for m in (2.0, 3.0):
            if f0 * m < f[-1] - 2:
                h.append(prom(P, f0 * m))
        for m in (2.37, 2.63):
            if f0 * m < f[-1] - 2:
                c.append(prom(P, f0 * m))
    h = np.array([v for v in h if np.isfinite(v)])
    c = np.array([v for v in c if np.isfinite(v)])
    return np.median(h) / np.median(c)


raw = []
for r in ('22', '23'):
    z = np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r), allow_pickle=True)
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        raw.append(rate[sl])
E = np.array([signal.welch(x - x.mean(), FS, nperseg=NW)[1][b69].sum() for x in raw])
sel = [raw[i] for i in np.argsort(E)[-max(int(0.05 * len(E)), 8):]]
print("V112 routes r22+r23: %d engaged windows, taking the top %d by 6-9 Hz content.\n" % (len(raw), len(sel)))


def relay(x, knee):
    return np.clip(x * CT * 12.0 / knee, -1.0, 1.0)


print("  knee   sat rate   harmonic ratio of the RELAY OUTPUT   vs knee 1800")
base = None
for knee in (600, 1800, 2400, 3000, 4000, 8000):
    hr = harmonic_ratio_of([relay(x, knee) for x in sel])
    if knee == 1800:
        base = hr
    print("  %5d   %6.1f      %8.4f                        %s"
          % (knee, knee / (12 * CT), hr, '--' if base is None or knee == 1800 else '%.3fx' % (hr / base)))

hr1800 = harmonic_ratio_of([relay(x, 1800) for x in sel])
hr3000 = harmonic_ratio_of([relay(x, 3000) for x in sel])
pred = hr3000 / hr1800
print("\n  ==> PREDICTION: V121 (knee 3000) should move the relay's harmonic ratio to")
print("      %.3fx of V112's (knee 1800).")
print("      %.3fx" % pred)
print("      V112 MEASURED on the wire: r22 0.970, r23 1.455, median 1.213")
print("      => V121 predicted wire harmonic ratio ~ %.3f  (1.213 x %.3f)" % (1.213 * pred, pred))

rng = np.random.default_rng(0)
bs = []
for _ in range(200):
    s = [sel[i] for i in rng.integers(0, len(sel), len(sel))]
    try:
        bs.append(harmonic_ratio_of([relay(x, 3000) for x in s]) /
                  harmonic_ratio_of([relay(x, 1800) for x in s]))
    except Exception:
        pass
print("      window-bootstrap 95%% CI on the predicted factor: [%.3f, %.3f]"
      % (np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
print("\n  FALSIFIER: fly V121; if the measured harmonic ratio does not fall toward that value,")
print("  the relay is NOT the excitation path for the 7-9 Hz mode.")
