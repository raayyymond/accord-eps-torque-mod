#!/usr/bin/env python3
r"""v102_b4_phase_band.py -- run the b4 sign-phase measurement in ANY band.  Default: 6-9 Hz.

    python v102_b4_phase_band.py 6 9

Same chain as `v102_b4_phase_feasibility.py` + `v102_b4_phase_ci.py`, parameterised by band, so the
6-9 Hz answer is produced by the SAME estimator that produced the 22-26 Hz one -- no new instrument.

🛑 ONE PRIOR THAT DOES NOT HOLD, AND IT IS THE REASON TO CHECK RATHER THAN ASSUME.
   "6-9 Hz should be easier -- 11 samples/cycle, no 3rd-harmonic fold, and the ratchet is the
   strongest line in the spectrum."  The first two are true.  **The third is false FOR THIS BIT.**
   `b4`'s own spectrum against a shuffled-bit white null (measured, CONTROL B):

        2-6 Hz   0.650      <- BELOW white
        6-9 Hz   1.173      <- the WEAKEST of the structured bands
       12-18 Hz  1.726      <- b4's actual peak
       18-22 Hz  1.031
       22-26 Hz  1.382      <- where the 22-26 result was measured
       26-31 Hz  0.798
       35-45 Hz  0.595      <- BELOW white

   **`b4` is not dominated by the ratchet line.  6-9 Hz carries only a 17 % excess over a coin
   flip**, against 38 % at 22-26.  Sampling headroom is better and signal is worse; which wins is
   an empirical question.

WHAT ALIASES INTO 6-9 Hz: content at 100 +- (6-9) = 91-94 Hz, i.e. the 11th-15th odd harmonics of
the fundamental, at 1/11-1/15 amplitude.  Negligible -- the 3rd-harmonic hazard that made 22-26 Hz
worth worrying about has no analogue here.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if "96" not in L.ROUTES:
    L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")

NF = 256
WIN = np.hanning(NF)
FG = np.fft.rfftfreq(NF, 1.0 / 100.0)
LO, HI = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (6.0, 9.0)
BAND = (FG >= LO) & (FG <= HI)
FC = float(np.mean(FG[BAND]))


def taper(x):
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    return (x - (c[0] * r + c[1])) * WIN


def stat(A, B):
    S, Pa, Pb = (A * np.conj(B)).sum(0), (np.abs(A) ** 2).sum(0), (np.abs(B) ** 2).sum(0)
    coh = float(np.mean((np.abs(S) ** 2) / np.maximum(Pa * Pb, 1e-30)))
    return float(np.degrees(np.angle(S[BAND].sum()))), coh


def collect(ref="rate_c", vlo=30.0, vhi=85.0, hands_light=True):
    A, B, ep = [], [], []
    for e, b in enumerate(L.all_blocks("96")):
        if "v102_b4" not in b or ref not in b:
            continue
        vv = b["v_rear"] * 3.6
        m = (b["cc_lat"] > 0.5) & (vv >= vlo) & (vv < vhi)
        if hands_light:
            m = m & (np.abs(b["cs_tq"]) < 400)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                x = (b["v102_b4"][i:i + NF] > 0.5).astype(float) * 2 - 1
                A.append(np.fft.rfft(taper(x)))
                B.append(np.fft.rfft(taper(b[ref][i:i + NF])))
                ep.append(e)
            i += NF // 2
    return np.array(A), np.array(B), np.array(ep)


if __name__ == "__main__":
    print("=" * 100)
    print("BAND %.1f-%.1f Hz  (centre %.2f Hz, %d bins)" % (LO, HI, FC, BAND.sum()))
    print("=" * 100)

    # ---------------- CONTROL A: synthetic phase recovery through sign + 10:1 decimation
    print("\nCONTROL A -- synthetic phase recovery, line at %.1f Hz, sign() then unfiltered 10:1." % FC)
    rng = np.random.default_rng(11)
    FS_HI, DEC, T = 1000.0, 10, 600.0
    th = np.arange(int(T * FS_HI)) / FS_HI
    errs = []
    for true_deg in range(0, 360, 45):
        nz = np.convolve(rng.standard_normal(len(th)), np.ones(7) / 7.0, mode="same")
        ref_hi = np.sin(2 * np.pi * FC * th)
        x = nz + 1.4 * np.sin(2 * np.pi * FC * th + np.radians(true_deg))
        s = np.sign(x)[::DEC]
        ref = ref_hi[::DEC] + 0.3 * rng.standard_normal(len(th) // DEC)
        A = np.array([np.fft.rfft(taper(s[i:i + NF])) for i in range(0, len(s) - NF + 1, NF // 2)])
        B = np.array([np.fft.rfft(taper(ref[i:i + NF]))
                      for i in range(0, len(ref) - NF + 1, NF // 2)])
        got, _ = stat(A, B)
        errs.append((got - true_deg + 180) % 360 - 180)
    errs = np.array(errs)
    bias, scat = float(np.mean(errs)), float(np.std(errs))
    SOUND = abs(bias) < 15 and scat < 25
    print("   mean bias %+.1f deg   scatter %.1f deg   => %s"
          % (bias, scat, "✅ SOUND" if SOUND else "🛑 NOT SOUND -- STOP"))

    # ---------------- CONTROL B: structure vs a shuffled-bit white null, in THIS band
    print("\nCONTROL B -- does b4 carry structure in this band, vs shuffled-same-bits white?")
    P = Pn = 0.0
    n = 0
    for b in L.all_blocks("96"):
        if "v102_b4" not in b:
            continue
        m = (b["cc_lat"] > 0.5) & (b["v_rear"] * 3.6 >= 30) & (b["v_rear"] * 3.6 < 85)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                x = (b["v102_b4"][i:i + NF] > 0.5).astype(float) * 2 - 1
                P = P + np.abs(np.fft.rfft(taper(x))) ** 2
                Pn = Pn + np.abs(np.fft.rfft(taper(rng.permutation(x)))) ** 2
                n += 1
            i += NF // 2
    ratio = float(P[BAND].sum() / Pn[BAND].sum())
    STRUCT = ratio > 1.15
    print("   %d windows.  power / white = %.3f   => %s"
          % (n, ratio, "✅ structure present" if STRUCT else "🛑 INDISTINGUISHABLE FROM A COIN FLIP"))

    # ---------------- the number
    print("\nTHE NUMBER" + ("" if (SOUND and STRUCT) else "  -- 🛑 CONTROLS FAILED, NOT QUOTED"))
    if not (SOUND and STRUCT):
        sys.exit(1)
    out = {}
    for nm, kw in (("hands-LIGHT vs rate_c", dict()),
                   ("ALL hands  vs rate_c", dict(hands_light=False)),
                   ("hands-LIGHT vs cs_ang", dict(ref="cs_ang"))):
        A, B, ep = collect(**kw)
        if len(A) < 12:
            print("   %-24s only %d windows -- NOT QUOTED" % (nm, len(A)))
            continue
        ang, coh = stat(A, B)
        keys = np.unique(ep)
        bs = []
        for _ in range(3000):
            sel = np.concatenate([np.nonzero(ep == keys[j])[0]
                                  for j in rng.integers(0, len(keys), len(keys))])
            bs.append(stat(A[sel], B[sel])[0])
        d = (np.array(bs) - ang + 180) % 360 - 180
        lo, hi = np.percentile(d, [2.5, 97.5])
        eff = len(A) / 2.0
        out[nm] = ang
        print("   %-24s arg %+7.1f  CI [%+7.1f,%+7.1f] (w %3.0f)  coh2 %.4f  floor %.4f  %.1fx  "
              "%d win/%d blk" % (nm, ang, ang + lo, ang + hi, hi - lo, coh, 1.0 / eff,
                                 coh * eff, len(A), len(keys)))
        for nn, Bn in (("time-reversed",
                        np.array([np.fft.rfft(taper(np.real(np.fft.irfft(b))[::-1])) for b in B])),
                       ("rotated", np.roll(B, 37, axis=0)),
                       ("phase-rand", B * np.exp(1j * rng.uniform(0, 2 * np.pi, B.shape)))):
            a2, c2 = stat(A, Bn)
            print("        null %-14s arg %+7.1f  coh2 %.4f  %s"
                  % (nn, a2, c2, "ok" if c2 < coh * 0.6 else "🛑 NOT BELOW SIGNAL"))
    if "hands-LIGHT vs rate_c" in out and "hands-LIGHT vs cs_ang" in out:
        dd = (out["hands-LIGHT vs rate_c"] - out["hands-LIGHT vs cs_ang"] + 180) % 360 - 180
        print("\n   ⭐ DERIVATIVE CHECK: arg(vs rate) - arg(vs angle) = %+.1f deg, expected -90.0 "
              "=> %s by %.1f deg" % (dd, "AGREES" if abs(dd + 90) < 20 else "🛑 DISAGREES",
                                     abs(dd + 90)))
