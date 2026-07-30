#!/usr/bin/env python3
"""analyze_r29_comb.py -- follow-ups to analyze_r29_grinding.py on route 29 seg 0 (V57).

Four questions the first pass raised:

  1. HARMONIC COMB. The whole-route torque spectrum shows lines at 7.38 / 14.79 / 22.11 / 29.28 /
     36.74 / 44.10 Hz -- spacings 7.41 / 7.32 / 7.17 / 7.46 / 7.36. If that is one comb, the
     "20-25 Hz mode" this kit has chased for ~50 builds is the THIRD HARMONIC of a ~7.4 Hz
     fundamental, and a ~7.4 Hz relaxation/stick-slip cycle is exactly what "grinding" sounds like.
     Tested per-window: does f(18-25 Hz peak) / f(5-10 Hz peak) sit at 3.00?

  2. THE SIGN CHANNEL. V57's bit4 (gate output == 0) is IDENTICALLY 0 across all 1581
     STEER_CONTROL_ACTIVE frames, so its spectrum carries no information there. bit3
     (gp-0x6b30 < 0) is the live one: 250 transitions. A 1-bit sign channel preserves
     zero-crossing timing exactly, so its spectrum locates the fundamental of the LKAS forward-path
     signal without any amplitude calibration.

  3. SMALL SUBSETS. SCA=1 + hands-off is 449 frames with no contiguous 256-run. Redone at nfft=128
     (1.28 s, 0.78 Hz bins) so the like-for-like baseline comparison is possible at all.

  4. IS 22 Hz IN openpilot's COMMAND? The TX'd 0xE4 STEER_TORQUE (src 129, the steering bus) is
     logged at 100 Hz. This is a DIRECT measurement of the question V55's 1.5-bit probe could only
     bound.

⚠ fs = 100.01 Hz throughout: f and (fs - f) are indistinguishable. Quoted as sub-Nyquist.

Usage:  python analyze_r29_comb.py CACHE.npz
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyze_r29_grinding import (FS, NFFT, NFFT_HI, BAND, spectrum, bandpower,  # noqa: E402
                                  peak_table, runs_of)


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def main(cache):
    d = dict(np.load(cache))
    n = len(d["t"])
    sca = d["sca"] > 0.5
    hands = np.abs(d["tq"]) > 200
    tq, rf, ang, v = d["tq"], d["rate_f"], d["ang"], d["cs_v"]
    probe = d["probe"].astype(int)
    neg = (probe & 0x08) != 0          # bit3: gate output < 0
    zero = (probe & 0x10) != 0         # bit4: gate output == 0
    e4 = d["e4tq"]

    rr = runs_of(sca, 1)
    print(f"STEER_CONTROL_ACTIVE runs: " +
          "; ".join(f"[{d['t'][a]:.2f}-{d['t'][b-1]:.2f}s, {b-a} fr]" for a, b in rr))

    # ------------------------------------------------------------------------------ 1. HARMONIC COMB
    hdr("1. IS IT ONE HARMONIC COMB? (torque, SCA=1 run only, nfft=512)")
    f, P, K, nr = spectrum(tq, sca, NFFT_HI)
    print(f"   K={K} independent 5.12 s segments in {nr} run(s)")
    pk = [r for r in peak_table(f, P, 0.6, 50.0, min_prom=2.0)]
    pk_by_f = sorted(pk, key=lambda r: r["f"])
    print(f"   {'f (Hz)':>8s} {'power':>12s} {'prom':>7s} {'Q':>7s}  {'f/f1':>6s} {'spacing':>8s}")
    f1 = None
    for i, r in enumerate(pk_by_f):
        if f1 is None and r["f"] > 5:
            f1 = r["f"]
        sp = f"{r['f']-pk_by_f[i-1]['f']:8.2f}" if i else f"{'--':>8s}"
        ratio = f"{r['f']/f1:6.3f}" if f1 else f"{'--':>6s}"
        print(f"   {r['f']:8.2f} {r['P']:12.4g} {r['prom']:6.1f}x {r['Q']:7.1f}  {ratio} {sp}")

    # harmonic product spectrum: fundamental that best explains the comb
    print(f"\n   -- harmonic product spectrum (fundamental search, harmonics 1..5) --")
    Pn = P / P.max()
    best = []
    for j, f0 in enumerate(f):
        if not (3.0 <= f0 <= 12.0):
            continue
        s = 0.0
        for h in range(1, 6):
            fh = f0 * h
            if fh > f[-1]:
                break
            k = int(round(fh / (f[1] - f[0])))
            s += np.log(Pn[max(k - 1, 0):k + 2].max() + 1e-300)
        best.append((s, f0))
    best.sort(reverse=True)
    print("      top fundamentals: " + "  ".join(f"{f0:.2f} Hz" for _, f0 in best[:6]))
    f0 = best[0][1]
    print(f"      => best-fit fundamental {f0:.2f} Hz; predicted harmonics: " +
          " ".join(f"{f0*h:.2f}" for h in range(1, 7)))

    # per-window lock test
    print(f"\n   -- PER-WINDOW LOCK TEST (nfft=256, hop 64; is f_high / f_low == 3.00?) --")
    nf, hop = NFFT, 64
    ff = np.fft.rfftfreq(nf, 1 / FS)
    lo_b = (ff >= 5.0) & (ff <= 10.0)
    hi_b = (ff >= 18.0) & (ff <= 26.0)
    m2_b = (ff >= 12.0) & (ff <= 17.0)
    rows = []
    for a, b in rr:
        for i in range(a, b - nf + 1, hop):
            seg = tq[i:i + nf]
            c = np.polyfit(np.arange(nf), seg, 1)
            Pw = np.abs(np.fft.rfft((seg - np.polyval(c, np.arange(nf))) * np.hanning(nf))) ** 2
            fl = ff[int(np.argmax(np.where(lo_b, Pw, -np.inf)))]
            f2 = ff[int(np.argmax(np.where(m2_b, Pw, -np.inf)))]
            fh = ff[int(np.argmax(np.where(hi_b, Pw, -np.inf)))]
            rows.append((d["t"][i], fl, f2, fh, fh / fl, f2 / fl,
                         Pw[lo_b].max(), Pw[hi_b].max(), v[i:i + nf].mean(),
                         np.abs(ang[i:i + nf]).mean()))
    R = np.array(rows)
    print(f"   {'t0':>6s} {'f_lo':>6s} {'f_h2':>6s} {'f_hi':>6s} {'hi/lo':>6s} {'h2/lo':>6s} "
          f"{'P_lo':>10s} {'P_hi':>10s} {'v':>5s} {'|ang|':>6s}")
    for r in R[::2]:
        print(f"   {r[0]:6.2f} {r[1]:6.2f} {r[2]:6.2f} {r[3]:6.2f} {r[4]:6.3f} {r[5]:6.3f} "
              f"{r[6]:10.4g} {r[7]:10.4g} {r[8]:5.2f} {r[9]:6.1f}")
    print(f"\n   hi/lo ratio: mean {R[:,4].mean():.3f}  median {np.median(R[:,4]):.3f}  "
          f"sd {R[:,4].std():.3f}   within 3.00+-0.15 in "
          f"{100*np.mean(np.abs(R[:,4]-3)<0.15):.0f}% of {len(R)} windows")
    print(f"   h2/lo ratio: mean {R[:,5].mean():.3f}  median {np.median(R[:,5]):.3f}  "
          f"sd {R[:,5].std():.3f}   within 2.00+-0.15 in "
          f"{100*np.mean(np.abs(R[:,5]-2)<0.15):.0f}%")
    print(f"   corr(f_lo, f_hi) = {np.corrcoef(R[:,1], R[:,3])[0,1]:+.3f}   "
          f"(a locked comb drifts together; independent modes do not)")
    print(f"   f_lo range {R[:,1].min():.2f}-{R[:,1].max():.2f} Hz, "
          f"f_hi range {R[:,3].min():.2f}-{R[:,3].max():.2f} Hz")

    # is the low line present when NOT steering?
    print(f"\n   -- is the ~7.4 Hz line present with SCA=0? --")
    for nm, sel in (("SCA=1", sca), ("SCA=0", ~sca), ("SCA=0 + hands-on", ~sca & hands)):
        f2_, P2, K2, nr2 = spectrum(tq, sel, NFFT_HI)
        if P2 is None:
            print(f"      {nm:18s} no complete segment")
            continue
        b = (f2_ >= 5) & (f2_ <= 10)
        ref = (f2_ >= 1) & (f2_ <= 40) & ~b
        j = int(np.argmax(np.where(b, P2, -np.inf)))
        print(f"      {nm:18s} K={K2:2d}  5-10 Hz peak {f2_[j]:5.2f} Hz  "
              f"prom {P2[j]/np.median(P2[ref]):7.2f}x   P(5-10)={P2[b].mean():.4g}")

    # ------------------------------------------------------------------------ 2. THE SIGN CHANNEL
    hdr("2. V57 SIGN CHANNEL -- spectrum of bit3 (gp-0x6b30 < 0), SCA=1 only")
    tr = int((np.diff(neg[sca].astype(int)) != 0).sum())
    dursca = (rr[0][1] - rr[0][0]) / FS if rr else np.nan
    print(f"   bit4 (out==0) within SCA=1: {int(zero[sca].sum())}/{int(sca.sum())} -> "
          f"IDENTICALLY ZERO, spectrum carries NO information (this is why bit3 is used)")
    print(f"   bit3 transitions within SCA=1: {tr} over {dursca:.2f} s "
          f"=> {tr/dursca:.2f} sign flips/s => implied fundamental {tr/dursca/2:.2f} Hz")
    f3, P3, K3, nr3 = spectrum(neg[sca].astype(float), None, NFFT_HI, detrend=False)
    print(f"   spectrum of the sign bit, K={K3} segments:")
    for r in peak_table(f3, P3, 0.6, 50.0, min_prom=2.0)[:10]:
        print(f"      {r['f']:7.2f} Hz  power {r['P']:11.4g}  prom {r['prom']:6.1f}x  Q {r['Q']:6.1f}")
    b = (f3 >= 5) & (f3 <= 10)
    ref = (f3 >= 1) & (f3 <= 40) & ~b
    j = int(np.argmax(np.where(b, P3, -np.inf)))
    print(f"   5-10 Hz peak {f3[j]:.2f} Hz, prom {P3[j]/np.median(P3[ref]):.2f}x")
    b = (f3 >= BAND[0]) & (f3 <= BAND[1])
    ref = (f3 >= 6) & (f3 <= 40) & ~b
    j = int(np.argmax(np.where(b, P3, -np.inf)))
    print(f"   15-27 Hz peak {f3[j]:.2f} Hz, prom {P3[j]/np.median(P3[ref]):.2f}x, "
          f"P(15-27)={P3[b].mean():.4g}")
    # coherence-free cross-check: correlate the sign bit against sign(torque)
    st = (tq[sca] < 0).astype(float)
    print(f"   corr(bit3, sign(driver torque<0)) = {np.corrcoef(neg[sca].astype(float), st)[0,1]:+.3f}"
          f"   corr(bit3, sign(rate<0)) = "
          f"{np.corrcoef(neg[sca].astype(float), (rf[sca]<0).astype(float))[0,1]:+.3f}")

    # ------------------------------------------------------------- 3. SMALL SUBSETS AT nfft=128
    hdr("3. SMALL SUBSETS AT nfft=128 (1.28 s, 0.7814 Hz bins)  -- 15-27 Hz band power, TORQUE")
    print(f"   ⚠ nfft=128 power is NOT comparable to nfft=256 power. Use only within this table.")
    print(f"   {'subset':36s} {'n':>6s} {'K':>4s} {'runs':>5s} {'P15-27':>12s} {'peak':>7s} {'prom':>7s}")
    subs = [("SCA=1 + hands-off", sca & ~hands), ("SCA=1 + hands-on", sca & hands),
            ("SCA=0 + hands-off", ~sca & ~hands), ("SCA=0 + hands-on", ~sca & hands),
            ("SCA=1, |ang| 0-2", sca & (np.abs(ang) < 2)),
            ("SCA=1, |ang| 2-5", sca & (np.abs(ang) >= 2) & (np.abs(ang) < 5)),
            ("SCA=1, |ang| 5-10", sca & (np.abs(ang) >= 5) & (np.abs(ang) < 10)),
            ("SCA=1, |ang| 10-20", sca & (np.abs(ang) >= 10) & (np.abs(ang) < 20)),
            ("SCA=1, |ang| >=20", sca & (np.abs(ang) >= 20)),
            ("SCA=1, v 0.5-1.0", sca & (v >= 0.5) & (v < 1.0)),
            ("SCA=1, v 1.0-1.5", sca & (v >= 1.0) & (v < 1.5)),
            ("SCA=1, v >=1.5", sca & (v >= 1.5))]
    for nm, sel in subs:
        if sel.sum() < 50:
            print(f"   {nm:36s} {int(sel.sum()):6d}   -- n<50, REFUSED --")
            continue
        f4, P4, K4, nr4 = spectrum(tq, sel, 128)
        if P4 is None:
            print(f"   {nm:36s} {int(sel.sum()):6d} {0:4d} {0:5d}   "
                  f"-- no contiguous 128-run, REFUSED --")
            continue
        b = (f4 >= BAND[0]) & (f4 <= BAND[1])
        ref = (f4 >= 6) & (f4 <= 40) & ~b
        j = int(np.argmax(np.where(b, P4, -np.inf)))
        print(f"   {nm:36s} {int(sel.sum()):6d} {K4:4d} {nr4:5d} {P4[b].mean():12.4g} "
              f"{f4[j]:7.2f} {P4[j]/np.median(P4[ref]):6.2f}x")

    # ---------------------------------------------------- 4. IS 22 Hz IN openpilot's 0xE4 COMMAND?
    hdr("4. IS THE MODE IN openpilot's TX'd 0xE4 STEER_TORQUE? (direct, not a probe)")
    rail = np.abs(e4[sca]) >= 4096
    print(f"   SCA=1: n={int(sca.sum())}  |cmd| mean {np.abs(e4[sca]).mean():.0f}  "
          f"AT THE +-4096 RAIL in {100*rail.mean():.1f}% of frames  "
          f"(sign +{int((e4[sca]>0).sum())}/-{int((e4[sca]<0).sum())})")
    fe, Pe, Ke, _ = spectrum(e4, sca, NFFT_HI)
    ft, Pt, Kt, _ = spectrum(tq, sca, NFFT_HI)
    for nm, ff_, PP, KK in (("0xE4 COMMAND", fe, Pe, Ke), ("0x18F SENSOR", ft, Pt, Kt)):
        b = (ff_ >= BAND[0]) & (ff_ <= BAND[1])
        ref = (ff_ >= 6) & (ff_ <= 40) & ~b
        lo = (ff_ >= 5) & (ff_ <= 10)
        j = int(np.argmax(np.where(b, PP, -np.inf)))
        jl = int(np.argmax(np.where(lo, PP, -np.inf)))
        print(f"   {nm:14s} K={KK:2d}  P(15-27)={PP[b].mean():11.4g}  peak {ff_[j]:5.2f} Hz "
              f"prom {PP[j]/np.median(PP[ref]):7.2f}x   |   5-10 Hz peak {ff_[jl]:5.2f} Hz "
              f"P(5-10)={PP[lo].mean():11.4g}")
    print(f"\n   command/sensor 15-27 Hz power ratio = "
          f"{Pe[(fe>=BAND[0])&(fe<=BAND[1])].mean()/Pt[(ft>=BAND[0])&(ft<=BAND[1])].mean():.4f} "
          f"(units differ: command counts vs sensor counts -- read the PROMINENCES, not this)")
    print(f"   command lines:")
    for r in peak_table(fe, Pe, 0.6, 50.0, min_prom=2.0)[:8]:
        print(f"      {r['f']:7.2f} Hz  prom {r['prom']:6.1f}x  Q {r['Q']:6.1f}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1])))
