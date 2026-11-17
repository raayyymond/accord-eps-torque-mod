"""Onset anatomy + waveform + alias test for chosen episodes. usage: <cache dir> <seg:t_route[:label]> ...
t_route = the route-relative time printed by a340_buzz_episodes.py (segment time ~= t - 60*seg)."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, s16

C = sys.argv[1]
cache = {}
for spec in sys.argv[2:]:
    parts = spec.split(":")
    seg, tt = int(parts[0]), float(parts[1])
    if seg not in cache:
        cache[seg] = load(os.path.join(C, "seg%02d.npz" % seg))
    d = cache[seg]
    i0 = int(np.searchsorted(d["t"], tt))
    print("\n================ seg %d  t %.2f (seg-time ~%.1f s)  %s" % (seg, tt, tt - 60 * seg, parts[2] if len(parts) > 2 else ""))
    print(" k     dt_ms   ang     rate  rate8    tq    hrate   m1ab(50Hz)  req  cmd    v")
    t1 = d["t1ab"]
    for k in range(i0 - 30, i0 + 36):
        if k < 1 or k >= len(d["t"]):
            continue
        j = int(np.searchsorted(t1, d["t"][k]))
        j = min(max(j, 0), len(t1) - 1)
        print("%4d %6.1f %7.1f %6.0f %7.2f %6.0f %7.1f   %5.0f      %d %6.0f %5.1f" % (
            k - i0, 1000 * (d["t"][k] - d["t"][k - 1]), d["ang"][k], d["rate"][k], d["rate8"][k], d["tq"][k],
            d["hr"][k], d["m1ab"][j], d["req"][k], d["cmd"][k] if d["has_e4"] else np.nan, d["v"][k]))
    # steady-state block: the 3 s after onset (or until BZ drops)
    sl = slice(i0 + 30, i0 + 330)
    hr = d["hr"][sl]
    ang = d["ang"][sl] - np.convolve(d["ang"][sl], np.ones(15) / 15, "same")
    # complex amplitudes at the as-sampled line (search 10-30 Hz on a 300-sample block)
    n = len(hr)
    tt_ = np.arange(n) / 100.0
    fr = np.linspace(10, 30, 401)
    E = np.exp(-2j * np.pi * fr[:, None] * tt_[None, :])
    R = E @ (hr * np.hanning(n))
    fpk = fr[np.argmax(np.abs(R))]
    e = np.exp(-2j * np.pi * fpk * tt_) * np.hanning(n)
    cr, ca = (e @ hr), (e @ (ang[: n] * 1.0))
    ratio = ca / cr if abs(cr) > 0 else np.nan
    print(" as-sampled line %.2f Hz | angle/rate complex ratio |%.4f| s, phase %+.0f deg" % (fpk, abs(ratio), np.degrees(np.angle(ratio))))
    for ftrue in (fpk, 100 - fpk, 100 + fpk, 200 - fpk):
        print("     if true f = %6.2f Hz: angle/rate should be |%.4f| s (phase -90 if f>0 alias-preserving else +90)" % (ftrue, 1 / (2 * np.pi * ftrue)))
    # waveform folding at the dominant integer period
    zc = np.flatnonzero(np.diff(np.sign(hr)) != 0)
    P = int(round(2 * np.median(np.diff(zc)))) if len(zc) > 3 else 6
    raw = d["rate"][sl] - np.convolve(d["rate"][sl], np.ones(P) / P, "same")
    m = (len(raw) // P) * P
    cyc = raw[:m].reshape(-1, P)
    # align each cycle to its max
    al = np.array([np.roll(c, -np.argmax(c)) for c in cyc])
    print(" fold period %d samples: mean cycle %s | per-cycle pk-pk p10/p50/p90 %s" % (
        P, np.round(al.mean(0), 1), np.round(np.percentile(cyc.max(1) - cyc.min(1), [10, 50, 90]), 1)))
    pk = d["rate"][sl]
    print(" raw rate values histogram (deg/s, top 8):", sorted(zip(*np.unique(pk.astype(int), return_counts=True)), key=lambda x: -x[1])[:8])
