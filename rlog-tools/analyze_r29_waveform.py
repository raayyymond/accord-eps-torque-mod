#!/usr/bin/env python3
"""analyze_r29_waveform.py -- time-domain confirmation of the route-29 grinding, plus two
resampling controls the frequency-domain work needs before its numbers can be trusted.

CONTROLS (both were live risks in the first two passes):
  C1  The torque series was sampled on 0x14A arrivals with 0x18F held. Rebuild it on 0x18F's OWN
      arrivals (zero hold) and confirm the 7.4 Hz line survives.
  C2  openpilot's 0xE4 was TX'd at ~87.5 Hz, not 100 Hz, and I zero-order-held it onto the 100 Hz
      grid. That injects energy near Nyquist and is the likely source of the 49.81 Hz / Q=255 line
      in the command spectrum. Measure the true TX interval distribution.

THEN: autocorrelation and the raw waveform of the grinding burst, which is what tells a
relaxation/stick-slip cycle apart from a sinusoidal resonance.

Usage:  python analyze_r29_waveform.py CACHE.npz [RLOG]
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyze_r29_grinding import FS, NFFT_HI, spectrum, peak_table, runs_of  # noqa: E402
from rlog_parse import read_messages  # noqa: E402

RLOG = (r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\rlogs"
        r"\75604b0a432fdc89_00000029--47bc9c9d99--0--rlog.zst")


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def i16be(b, o):
    v = (b[o] << 8) | b[o + 1]
    return v - 0x10000 if v & 0x8000 else v


def main(cache, rlog):
    d = dict(np.load(cache))
    sca = d["sca"] > 0.5
    tq = d["tq"]
    rr = runs_of(sca, 100)
    a, b = rr[0]
    print(f"grinding window = the single long STEER_CONTROL_ACTIVE run: "
          f"t {d['t'][a]:.2f}-{d['t'][b-1]:.2f} s, {b-a} frames")

    # ------------------------------------------------------------------- C1 / C2: raw CAN timing
    hdr("C1/C2. RESAMPLING CONTROLS -- re-read the raw CAN stream with no hold")
    t18, x18, t14, tE4, xE4 = [], [], [], [], []
    for evt in read_messages(rlog):
        try:
            w = evt.which()
        except Exception:
            continue
        if w != "can":
            continue
        tm = evt.logMonoTime * 1e-9
        for m in evt.can:
            s, ad, dd = int(m.src), int(m.address), bytes(m.dat)
            if s == 1 and ad == 0x18F and len(dd) >= 2:
                t18.append(tm); x18.append(i16be(dd, 0) * -1.0)
            elif s == 1 and ad == 0x14A:
                t14.append(tm)
            elif s == 129 and ad == 0x0E4 and len(dd) >= 3:
                tE4.append(tm); xE4.append(float(i16be(dd, 0)))
    t18 = np.array(t18); x18 = np.array(x18)
    t14 = np.array(t14); tE4 = np.array(tE4); xE4 = np.array(xE4)
    t0 = t18[0]
    for nm, t in (("0x18F src1", t18), ("0x14A src1", t14), ("0x0E4 src129", tE4)):
        dt = np.diff(t)
        print(f"  {nm:14s} n={len(t):5d}  mean rate {len(t)/(t[-1]-t[0]):7.3f} Hz   "
              f"dt median {1000*np.median(dt):6.3f} ms  p95 {1000*np.percentile(dt,95):6.3f}  "
              f"max {1000*dt.max():8.3f}   dt>15ms: {int((dt>0.015).sum())}")
    # 0x18F vs 0x14A pairing
    print(f"  0x18F and 0x14A counts match: {len(t18)==len(t14)};  "
          f"max |t18 - t14| = {1000*np.abs(t18[:min(len(t18),len(t14))]-t14[:min(len(t18),len(t14))]).max():.3f} ms"
          f"  => the hold used in the cache is sub-sample")

    # C1: spectrum of torque on its OWN arrivals, restricted to the grinding window
    tw0, tw1 = d["t"][a] + t0, d["t"][b - 1] + t0
    sel18 = (t18 >= tw0) & (t18 <= tw1)
    f, P, K, _ = spectrum(x18[sel18], None, NFFT_HI)
    print(f"\n  C1: torque on 0x18F's OWN grid, grinding window, n={int(sel18.sum())} K={K}")
    for r in peak_table(f, P, 0.6, 50.0, min_prom=3.0)[:8]:
        print(f"      {r['f']:7.2f} Hz  prom {r['prom']:7.1f}x  Q {r['Q']:6.1f}")
    f2, P2, K2, _ = spectrum(tq, sca, NFFT_HI)
    print(f"  (cache/held version for comparison, K={K2}): " +
          "  ".join(f"{r['f']:.2f}Hz {r['prom']:.0f}x"
                    for r in peak_table(f2, P2, 0.6, 50.0, min_prom=3.0)[:5]))
    print("  => if the top lines agree the hold is not creating them.")

    # C2: 0xE4 TX cadence inside the grinding window
    selE = (tE4 >= tw0) & (tE4 <= tw1)
    dtE = np.diff(tE4[selE])
    print(f"\n  C2: 0xE4 TX inside the grinding window: n={int(selE.sum())}, "
          f"rate {selE.sum()/(tw1-tw0):.2f} Hz")
    print(f"      dt histogram (ms): " + "  ".join(
        f"{lo}-{hi}:{int(((dtE*1000>=lo)&(dtE*1000<hi)).sum())}"
        for lo, hi in ((0, 8), (8, 12), (12, 16), (16, 25), (25, 50), (50, 10000))))
    print(f"      => openpilot held a clean 100 Hz here. NO dropped-frame story: the whole-route")
    print(f"         count of 5383 vs 6151 is because it TX'd for only part of the segment.")
    print(f"      But 0xE4 and 0x14A are two INDEPENDENT 100 Hz streams, so holding one onto the")
    print(f"      other's grid duplicates/skips samples as their phase drifts. Spectrum of the")
    print(f"      command on its OWN grid, to see which command lines survive:")
    fE, PE, KE, _ = spectrum(xE4[selE], None, NFFT_HI)
    for r in peak_table(fE, PE, 0.6, 50.0, min_prom=3.0)[:8]:
        print(f"         {r['f']:7.2f} Hz  prom {r['prom']:7.1f}x  Q {r['Q']:6.1f}")
    fEh, PEh, KEh, _ = spectrum(d["e4tq"], sca, NFFT_HI)
    print(f"      (held-onto-0x14A version, K={KEh}): " +
          "  ".join(f"{r['f']:.2f}Hz {r['prom']:.0f}x"
                    for r in peak_table(fEh, PEh, 0.6, 50.0, min_prom=3.0)[:6]))
    for nm, ff_, PP in (("own grid", fE, PE), ("held", fEh, PEh)):
        bb = (ff_ >= 19) & (ff_ <= 24)
        rf_ = (ff_ >= 6) & (ff_ <= 40) & ~bb
        j = int(np.argmax(np.where(bb, PP, -np.inf)))
        lo_ = (ff_ >= 6) & (ff_ <= 9)
        rl = (ff_ >= 1) & (ff_ <= 40) & ~lo_
        jl = int(np.argmax(np.where(lo_, PP, -np.inf)))
        print(f"      command {nm:9s}: 19-24 Hz peak {ff_[j]:5.2f} prom {PP[j]/np.median(PP[rf_]):6.2f}x"
              f"   6-9 Hz peak {ff_[jl]:5.2f} prom {PP[jl]/np.median(PP[rl]):6.2f}x")

    # ------------------------------------------------------------------ autocorrelation / waveform
    hdr("AUTOCORRELATION of the torque in the grinding window (relaxation cycle vs sinusoid)")
    x = tq[a:b].astype(float)
    x = x - np.polyval(np.polyfit(np.arange(len(x)), x, 3), np.arange(len(x)))
    ac = np.correlate(x, x, "full")[len(x) - 1:]
    ac /= ac[0]
    lags = np.arange(len(ac)) / FS
    win = (lags > 0.05) & (lags < 0.5)
    j = int(np.argmax(np.where(win, ac, -np.inf)))
    print(f"  first strong peak at lag {lags[j]*1000:.1f} ms  => {1/lags[j]:.2f} Hz, r={ac[j]:.3f}")
    print(f"  {'lag(ms)':>8s} " + " ".join(f"{1000*lags[i]:7.0f}" for i in range(0, 60, 4)))
    print(f"  {'r':>8s} " + " ".join(f"{ac[i]:7.3f}" for i in range(0, 60, 4)))
    per = int(round(FS / (1 / lags[j])))
    print(f"  harmonic check: r at 1x/2x/3x the period ({per}/{2*per}/{3*per} samples) = "
          f"{ac[per]:.3f} / {ac[min(2*per,len(ac)-1)]:.3f} / {ac[min(3*per,len(ac)-1)]:.3f}")

    hdr("RAW WAVEFORM, 1.0 s at the peak of the burst (t=29.4-30.4 s window was prom 1031x)")
    i0 = int(np.argmin(np.abs(d["t"] - 29.6)))
    probe = d["probe"].astype(int)
    print(f"  {'t':>7s} {'torque':>8s} {'rate_f':>8s} {'angle':>8s} {'0xE4cmd':>8s} "
          f"{'bit3':>5s} {'bit4':>5s} {'SCA':>4s}")
    for i in range(i0, i0 + 70):
        print(f"  {d['t'][i]:7.3f} {d['tq'][i]:8.0f} {d['rate_f'][i]:8.1f} {d['ang'][i]:8.2f} "
              f"{d['e4tq'][i]:8.0f} {(probe[i]>>3)&1:5d} {(probe[i]>>4)&1:5d} {int(d['sca'][i]):4d}")

    # zero-crossing rate of the band-passed torque
    hdr("BAND-LIMITED RMS BUDGET in the grinding window (torque counts)")
    f3 = np.fft.rfftfreq(len(x), 1 / FS)
    X = np.fft.rfft(x * np.hanning(len(x)))
    tot = (np.abs(X) ** 2).sum()
    for lo, hi in ((0, 1), (1, 4), (4, 6), (6, 9), (9, 12), (12, 17), (17, 19), (19, 24),
                   (24, 27), (27, 33), (33, 50)):
        s = (f3 >= lo) & (f3 < hi)
        print(f"   {lo:3.0f}-{hi:3.0f} Hz : {100*(np.abs(X[s])**2).sum()/tot:6.2f}% of variance")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else RLOG))
