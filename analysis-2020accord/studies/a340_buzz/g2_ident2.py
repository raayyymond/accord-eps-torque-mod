# -*- coding: utf-8 -*-
"""g2_ident2.py -- second pass on the plant comparison A340 vs A160 (same controller, same x3 lane engaged):
 (1) loss term split  Im(1/P) = c + b*w  (c = amplitude-dependent Coulomb/hand term), k from Re(1/P) at <= 0.7 Hz, with
     bootstrap CIs and the A340/A160 RATIO per speed band;
 (2) hands check: torsion-bar torque per deg of wheel angle, |T_tb/theta| at 0.2-3 Hz, engaged not-pressed chunks
     (a free rim gives ~Jw*w^2 = small; a resting hand gives a stiffness/damping floor);
 (3) how much engaged hands-off data exists at creep on the A340 route (5.12 s chunks);
 (4) the STOCK A340 route: stock LKAS torque command -> wheel rate, coherence only (no A160 counterpart cached);
 (5) baseline for the proposed readout: rms of the 8-20 Hz band of the 0x14A rate, 1 s windows, engaged & not pressed.
ANALYSIS ONLY.  Seconds."""
import os
import sys
import time
import json
import numpy as np
from scipy import signal

t00 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g2_ident as I   # noqa: E402

FC, FB, FREQ = I.FC, I.FB, I.FREQ
zA = dict(np.load(os.path.join(HERE, "g2_cache_a340_mod.npz")))
zS = dict(np.load(os.path.join(HERE, "g2_cache_a340_stock.npz")))
zB = dict(np.load(os.path.join(HERE, "g2_cache_a160_v300.npz")))
out = {}


def est(cb, vm):
    H, coh, nd = I.binned(cb)
    Cf, Cr = I.ctl_resp(vm, FC)
    y = Cr / H - Cf
    om = 2 * np.pi * FC
    lo = (FC <= 0.75) & (coh > 0.5)
    k = float(np.sum(coh[lo] * y.real[lo]) / np.sum(coh[lo])) if lo.sum() >= 2 else np.nan
    s = (FC <= 1.5) & (coh > 0.4)
    if s.sum() >= 3:
        A = np.c_[np.ones(s.sum()), om[s]] * np.sqrt(coh[s])[:, None]
        (c, b), *_ = np.linalg.lstsq(A, y.imag[s] * np.sqrt(coh[s]), rcond=None)
    else:
        c = b = np.nan
    loss05 = float(np.interp(0.5, FC, y.imag))             # Im(1/P) at 0.5 Hz (T per deg)
    ph03 = float(np.degrees(np.angle(H[1])))               # tracking phase at 0.30 Hz
    bw = float(np.interp(0.707, np.abs(H[:7])[::-1], FC[:7][::-1])) if np.abs(H[6]) < 0.707 else np.nan
    return np.array([k, c, b, loss05, ph03, bw])


def run(z, key, name, tq_lim=400):
    ch = I.chunks(z, key, tq_lim)
    rng = np.random.default_rng(3)
    res = {}
    for lo, hi in I.BANDS:
        cb = [c for c in ch if lo <= c["v"] < hi]
        if len(cb) < 6:
            continue
        vm = float(np.mean([c["v"] for c in cb]))
        e0 = est(cb, vm)
        bs = np.array([est([cb[i] for i in rng.integers(0, len(cb), len(cb))], vm) for _ in range(200)])
        res[(lo, hi)] = dict(v=vm, n=len(cb), e=e0, lo=np.nanpercentile(bs, 5, axis=0), hi=np.nanpercentile(bs, 95, axis=0), bs=bs,
                             sp=float(np.median([c["sp_rms"] for c in cb])))
    return res


print("(1) plant seen by the angle loop (x3 lane inside), engaged, not pressed, mean|tq| < 400.  [5 %, 95 %] bootstrap over chunks")
RA, RB = run(zA, "sp_e4", "a340"), run(zB, "sp_cc", "a160")
lab = ("k T/deg", "c T/deg (Im 1/P at w->0)", "b T/(deg/s)", "Im(1/P) @0.5 Hz", "track phase @0.3 Hz deg", "f(|T|=0.707) Hz")
for band in I.BANDS:
    if band not in RA or band not in RB:
        print("  band %s: A340 n %s, A160 n %s -- skipped" % (band, RA.get(band, {}).get("n"), RB.get(band, {}).get("n")))
        continue
    a, b = RA[band], RB[band]
    print("  band %2d-%2d m/s: A340 v %.1f n %d (sp rms %.2f deg) | A160 v %.1f n %d (sp rms %.2f deg)" % (band[0], band[1], a["v"], a["n"], a["sp"], b["v"], b["n"], b["sp"]))
    for j, l in enumerate(lab):
        ratio = a["bs"][:, j][:, None] / b["bs"][:, j][None, :]
        print("     %-26s A340 %7.2f [%7.2f, %7.2f]   A160 %7.2f [%7.2f, %7.2f]   ratio %.2f [%.2f, %.2f]" % (
            l, a["e"][j], a["lo"][j], a["hi"][j], b["e"][j], b["lo"][j], b["hi"][j], a["e"][j] / b["e"][j],
            np.nanpercentile(ratio, 5), np.nanpercentile(ratio, 95)))
    out["%d-%d" % band] = dict(a340=a["e"].tolist(), a160=b["e"].tolist())

# sensitivity of (1) to the hand gate
print("\n(1b) same, hand gate mean|tq| < 150 (A340 only where n >= 6):")
RA2 = run(zA, "sp_e4", "a340", tq_lim=150)
for band, a in RA2.items():
    print("  band %s n %d: k %.1f c %.1f b %.2f Im@0.5 %.1f" % (band, a["n"], *a["e"][:4]))
RB2 = run(zB, "sp_cc", "a160", tq_lim=150)
for band, a in RB2.items():
    print("  A160 band %s n %d: k %.1f c %.1f b %.2f Im@0.5 %.1f" % (band, a["n"], *a["e"][:4]))


# ------------------------------------------------------------------ (2) hands check
def htb(z, key):
    ch = []
    ok = (z["req"] > 0.5) & (z["pressed"] < 0.5) & (z["v"] > 8)
    N, HOP = I.N, I.HOP
    cs = np.concatenate([[0], np.cumsum(ok)])
    for i in range(0, len(ok) - N, HOP):
        if cs[i + N] - cs[i] != N:
            continue
        x = signal.detrend(z["ang"][i:i + N]); y = signal.detrend(z["tq"][i:i + N])
        X = np.fft.rfft(x * I.WIN); Y = np.fft.rfft(y * I.WIN)
        ch.append(dict(Pxx=np.abs(X) ** 2, Pyy=np.abs(Y) ** 2, Pxy=np.conj(X) * Y, v=0, mt=float(np.mean(np.abs(z["tq"][i:i + N])))))
    return ch


print("\n(2) hands check, engaged not pressed v > 8: |T_tb/theta| (0x18F units per deg) and coherence by log bin")
print("     f      : " + " ".join("%6.2f" % x for x in FC))
for name, z in (("A340 mod", zA), ("A160 V300", zB)):
    ch = htb(z, None)
    H, coh, _ = I.binned(ch)
    print("     %-9s |H| " % name + " ".join("%6.1f" % abs(x) for x in H) + "   (n %d, median mean|tq| %.0f)" % (len(ch), np.median([c["mt"] for c in ch])))
    print("     %-9s coh " % name + " ".join("%6.2f" % x for x in coh))
    out["htb_" + name] = dict(H=np.abs(H).tolist(), coh=coh.tolist())

# ------------------------------------------------------------------ (3) creep exposure on the A340 route
for name, z in (("A340 mod", zA), ("A340 stock", zS), ("A160 V300", zB)):
    eng = (z["req"] > 0.5)
    for lo, hi in ((1, 3), (3, 6), (6, 10)):
        m = eng & (z["v"] >= lo) & (z["v"] < hi)
        print("(3) %s engaged %d-%d m/s: %.0f s total, %.0f s not pressed" % (name, lo, hi, m.sum() / 100, (m & (z["pressed"] < 0.5)).sum() / 100))

# ------------------------------------------------------------------ (4) stock route: LKAS torque cmd -> rate
ok = (zS["req"] > 0.5) & (zS["pressed"] < 0.5) & (zS["v"] > 2)
idx = np.flatnonzero(ok)
if len(idx) > 2000:
    brk = np.flatnonzero(np.diff(idx) > 1)
    runs = np.split(idx, brk + 1)
    Pxx = Pyy = Pxy = 0; n = 0
    for r in runs:
        if len(r) < 512:
            continue
        x = signal.detrend(zS["cmd"][r]); y = signal.detrend(zS["rate"][r])
        f, pxx = signal.welch(x, 100, nperseg=256); _, pyy = signal.welch(y, 100, nperseg=256); _, pxy = signal.csd(x, y, 100, nperseg=256)
        Pxx = Pxx + pxx * len(r); Pyy = Pyy + pyy * len(r); Pxy = Pxy + pxy * len(r); n += len(r)
    coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    Hs = Pxy / Pxx
    print("\n(4) STOCK A340 engaged not pressed: %.0f s in runs >= 5.12 s.  stock LKAS cmd -> wheel rate (deg/s per cmd count):" % (n / 100))
    for fq in (0.39, 0.78, 1.17, 1.95, 3.1, 5.1, 8.2):
        j = int(np.argmin(abs(f - fq)))
        print("      %.2f Hz: |H| %.4f  phase %4.0f deg  coh %.2f" % (f[j], abs(Hs[j]), np.degrees(np.angle(Hs[j])), coh[j]))

# ------------------------------------------------------------------ (5) readout baseline: 8-20 Hz band of the 0x14A rate
bb, ba = signal.butter(4, [8 / 50, 20 / 50], "band")
print("\n(5) rms of the 8-20 Hz band of the 0x14A rate over 1 s windows, engaged & not pressed, by speed (p50 / p90 / p99 deg/s, n s)")
for name, z in (("A340 REV3 (mod)", zA), ("A340 stock fw", zS), ("A160 V300", zB)):
    y = signal.filtfilt(bb, ba, z["rate"])
    r = np.sqrt(np.convolve(y * y, np.ones(100) / 100, "same"))
    ok = (z["req"] > 0.5) & (z["pressed"] < 0.5)
    row = []
    for lo, hi in ((1, 6), (6, 10), (10, 20), (20, 32)):
        m = ok & (z["v"] >= lo) & (z["v"] < hi)
        row.append("%d-%d m/s: %.2f / %.2f / %.2f (%.0f s)" % (lo, hi, *np.percentile(r[m], [50, 90, 99]), m.sum() / 100) if m.sum() > 200 else "%d-%d m/s: n<2 s" % (lo, hi))
    print("     %-16s " % name + " | ".join(row))
    out["bp_" + name] = row
json.dump(out, open(os.path.join(HERE, "g2_ident2.json"), "w"), indent=1, default=float)
print("\nwall %.1f s" % (time.time() - t00))
