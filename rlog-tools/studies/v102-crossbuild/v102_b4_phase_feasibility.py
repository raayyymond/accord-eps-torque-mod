#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_b4_phase_feasibility.py -- CAN a 1-BIT SIGN SEQUENCE give r24's phase at 22-26 Hz?

FEASIBILITY FIRST.  The number is only computed if the controls pass.

WHY IT MIGHT WORK (the theory the request rests on)
    Bussgang's theorem: for jointly Gaussian x, y,  E[sgn(x)*y] = c * E[x*y]  with c a REAL
    POSITIVE scalar.  A real positive scale factor does not touch the ARGUMENT, so the
    cross-spectral PHASE survives hard limiting exactly.  Hard limiting costs amplitude
    information, not phase.  So far so good.

WHY IT MIGHT NOT -- THREE HAZARDS, none of which Bussgang covers
  H1  NOT GAUSSIAN, AND BROADBAND.  Bussgang needs joint Gaussianity.  More seriously, sgn(x) of a
      signal dominated by content OUTSIDE 22-26 Hz is essentially a square wave at the DOMINANT
      frequency, and its 22-26 Hz content is that wave's harmonic structure -- NOT x's actual
      22-26 Hz content.  The phase you recover would then be the wrong signal's.
  H2  🛑 UNFILTERED 10:1 DECIMATION.  The cave runs at 100 Hz but `gp-0x6ada` updates in the 1 kHz
      control task, so the bit is a 100 Hz SAMPLE of a 1 kHz-updated sign, with NO anti-alias
      filter.  Everything from 0-500 Hz folds into 0-50 Hz.
  H3  3rd-HARMONIC ALIASING LANDS IN-BAND.  A square wave's 3rd harmonic of a 24.7-26 Hz
      fundamental sits at 74-78 Hz, which aliases to 22-26 Hz -- **directly into the band of
      interest**, at 1/3 amplitude and phase-locked to the fundamental.  This one is specific to
      this band at this sample rate and it is the reason this cannot be waved through on theory.

⚠ A CALIBRATION HANDLE THAT IS NOT REASSURING ON ITS OWN.  `b4` flips 39.2 /s engaged.
    * a clean 19.6 Hz oscillation gives 2 flips/cycle = 39.2 /s   <- looks great
    * an i.i.d. coin flip at 100 Hz gives 50 /s                   <- 39.2 is 78 % of that
  **The two hypotheses are nearly degenerate on flip rate**, so flip rate PROVES NOTHING.  Only the
  spectrum and a phase-recovery control can separate them.

THE PLAN, in order.  Stop at the first failure.
  CONTROL A  Synthetic phase recovery.  Build a 1 kHz signal with a KNOWN 22-26 Hz phase relative
             to a reference, hard-limit it, decimate 10:1 unfiltered, and see whether the recovered
             phase tracks truth.  Sweep true phase over 0-315 deg.  Tune the broadband/line ratio
             so the synthetic reproduces the MEASURED 39.2 flips/s -- otherwise the control is not
             representative of the real operating point.
  CONTROL B  Does `b4` actually have 22-26 Hz structure, or is it white?  Spectrum of the real bit
             sequence against a white-noise null of the same flip rate.
  CONTROL C  Shuffled-pair null -- phase between `b4` and a time-reversed / rotated reference.
  THEN       The number, vs `rate_c` (NOT `rate_f`: it carries ~83 deg of unmodelled filter phase
             at 21.5 Hz -- measured in this session).

🛑 PAIRING: uses `v102_b4`, decoded from `probe`, which lives on the `t` row grid.  (t, probe) is a
   SAFE pair.  `raw14_b4` is NEVER touched here.  A 10 ms error is ~90 deg at 24 Hz.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for _r in ("96",):
    if _r not in L.ROUTES:
        L.ROUTES[_r] = L._mk(_r, "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")

NF = 256
WIN = np.hanning(NF)
FG = np.fft.rfftfreq(NF, 1.0 / 100.0)
BAND = (FG >= 22.0) & (FG <= 26.0)


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def taper(x):
    r = np.arange(len(x), dtype=float)
    c = np.polyfit(r, x, 1)
    return (x - (c[0] * r + c[1])) * WIN


def xphase(a, b):
    """arg(csd(a,b)) band-summed over 22-26 Hz, plus mean coherence.  Complex sum BEFORE angle."""
    S = Pa = Pb = 0.0
    n = 0
    for i in range(0, len(a) - NF + 1, NF // 2):
        A = np.fft.rfft(taper(a[i:i + NF]))
        B = np.fft.rfft(taper(b[i:i + NF]))
        S = S + A * np.conj(B)
        Pa = Pa + np.abs(A) ** 2
        Pb = Pb + np.abs(B) ** 2
        n += 1
    if n < 4:
        return np.nan, np.nan, 0
    coh = float(np.mean((np.abs(S) ** 2) / np.maximum(Pa * Pb, 1e-30)))
    return float(np.degrees(np.angle(S[BAND].sum()))), coh, n


def flips_per_s(bits, fs=100.0):
    return float(np.sum(np.diff(bits.astype(int)) != 0)) / (len(bits) / fs)


# =====================================================================================================
if __name__ == "__main__":
    hdr("CONTROL A -- SYNTHETIC PHASE RECOVERY through sign() + unfiltered 10:1 decimation.\n"
        "  1 kHz source, a 24 Hz line at a KNOWN phase on broadband noise, hard-limited, then\n"
        "  every 10th sample kept.  Broadband/line ratio tuned to reproduce the MEASURED 39.2 /s.")
    rng = np.random.default_rng(11)
    FS_HI, DEC, T = 1000.0, 10, 600.0
    th = np.arange(int(T * FS_HI)) / FS_HI
    # tune the line-to-noise ratio so the decimated sign sequence flips at ~39.2 /s
    print("\n  tuning broadband:line so the decimated sign flips at the measured 39.2 /s")
    best = None
    for snr in (0.15, 0.25, 0.4, 0.6, 0.9, 1.4, 2.2, 3.5):
        nz = rng.standard_normal(len(th))
        nz = np.convolve(nz, np.ones(7) / 7.0, mode="same")     # mild low-pass => realistic lane
        x = nz + snr * np.sin(2 * np.pi * 24.0 * th)
        s = (np.sign(x)[::DEC] > 0).astype(float)
        f = flips_per_s(s)
        print("      line/noise %.2f  ->  %.1f flips/s" % (snr, f))
        if best is None or abs(f - 39.2) < abs(best[1] - 39.2):
            best = (snr, f)
    SNR = best[0]
    print("  => using line/noise = %.2f (gives %.1f flips/s vs measured 39.2)" % (SNR, best[1]))

    print("\n  %-14s %14s %14s %10s   %s" % ("true phase", "recovered", "error", "coh2", "verdict"))
    errs = []
    for true_deg in range(0, 360, 45):
        nz = rng.standard_normal(len(th))
        nz = np.convolve(nz, np.ones(7) / 7.0, mode="same")
        ref_hi = np.sin(2 * np.pi * 24.0 * th)
        x = nz + SNR * np.sin(2 * np.pi * 24.0 * th + np.radians(true_deg))
        s = np.sign(x)[::DEC]
        ref = ref_hi[::DEC] + 0.3 * rng.standard_normal(len(th) // DEC)
        got, coh, n = xphase(s, ref)
        err = (got - true_deg + 180) % 360 - 180
        errs.append(err)
        print("  %-14d %14.1f %14.1f %10.3f   %s"
              % (true_deg, got, err, coh, "ok" if abs(err) < 20 else "🛑 BIASED"))
    errs = np.array(errs)
    bias, scat = float(np.mean(errs)), float(np.std(errs))
    print("\n  MEAN BIAS %+.1f deg   SCATTER %.1f deg" % (bias, scat))
    SOUND = abs(bias) < 15 and scat < 25
    print("  => %s" % ("✅ SOUND -- hard limiting + unfiltered decimation preserve phase here."
                       if SOUND else
                       "🛑 NOT SOUND -- the estimator does not recover a known phase. STOP."))

    # ------------------------------------------------------------------ CONTROL B
    hdr("CONTROL B -- does the REAL `b4` have 22-26 Hz structure, or is it a coin flip?")
    acc = {}
    for seg in L.ROUTES["96"]["segs"]:
        d = L.load_seg("96", seg)
        for k in ("t", "cc_lat", "v_rear", "rate_c", "cs_tq", "v102_b4", "v102_b6", "tq"):
            if k in d:
                acc.setdefault(k, []).append(d[k])
    D = {k: np.concatenate(v) for k, v in acc.items()}
    if "v102_b4" not in D:
        print("  🛑 v102_b4 column absent from the per-segment cache -- cannot proceed.")
        sys.exit(2)
    blocks = L.all_blocks("96")
    print("  engaged frames: %d   b4 flip rate engaged: %.1f /s"
          % (int((D["cc_lat"] > 0.5).sum()),
             flips_per_s(D["v102_b4"][D["cc_lat"] > 0.5] > 0.5)))
    P, Pn, n = 0.0, 0.0, 0
    for b in blocks:
        if "v102_b4" not in b:
            continue
        m = (b["cc_lat"] > 0.5) & (b["v_rear"] * 3.6 >= 30) & (b["v_rear"] * 3.6 < 85)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                x = (b["v102_b4"][i:i + NF] > 0.5).astype(float) * 2 - 1
                P = P + np.abs(np.fft.rfft(taper(x))) ** 2
                w = rng.permutation(x)
                Pn = Pn + np.abs(np.fft.rfft(taper(w))) ** 2
                n += 1
            i += NF // 2
    if n < 8:
        print("  🛑 only %d windows -- too thin." % n)
        sys.exit(2)
    P, Pn = P / n, Pn / n
    ratio = P[BAND].sum() / Pn[BAND].sum()
    print("  %d windows.  22-26 Hz power / SHUFFLED-same-bits power = %.3f" % (n, ratio))
    print("  (shuffling destroys time order but keeps the duty, so this is a pure white-bit null)")
    for lo, hi in ((2, 6), (6, 9), (12, 18), (18, 22), (22, 26), (26, 31), (35, 45)):
        bb = (FG >= lo) & (FG <= hi)
        print("      %5.1f-%4.1f Hz   power/white = %.3f" % (lo, hi, P[bb].sum() / Pn[bb].sum()))
    STRUCT = ratio > 1.15
    print("  => %s" % ("✅ b4 carries real 22-26 Hz structure above a white-bit null."
                       if STRUCT else
                       "🛑 b4 is INDISTINGUISHABLE FROM A COIN FLIP in this band."))

    # ------------------------------------------------------------------ CONTROL C + number
    hdr("CONTROL C + THE NUMBER -- vs `rate_c` (NOT rate_f: ~83 deg unmodelled filter phase).")
    if not (SOUND and STRUCT):
        print("  🛑 CONTROLS FAILED -- the number is NOT computed and must NOT be inferred.")
        sys.exit(1)
    S = Pa = Pb = 0.0
    Sn = 0.0
    n = 0
    ep = []
    for e, b in enumerate(blocks):
        if "v102_b4" not in b:
            continue
        vv = b["v_rear"] * 3.6
        m = (b["cc_lat"] > 0.5) & (vv >= 30) & (vv < 85) & (np.abs(b["cs_tq"]) < 400)
        i = 0
        while i + NF <= len(m):
            if m[i:i + NF].mean() >= 0.98:
                x = (b["v102_b4"][i:i + NF] > 0.5).astype(float) * 2 - 1
                y = b["rate_c"][i:i + NF]
                A, B = np.fft.rfft(taper(x)), np.fft.rfft(taper(y))
                S = S + A * np.conj(B)
                Pa = Pa + np.abs(A) ** 2
                Pb = Pb + np.abs(B) ** 2
                Sn = Sn + A * np.conj(np.fft.rfft(taper(y[::-1])))   # time-reversed null
                n += 1
                ep.append(e)
            i += NF // 2
    if n < 10:
        print("  🛑 only %d hands-off windows in 30-85 km/h -- too thin to quote." % n)
        sys.exit(1)
    coh = float(np.mean((np.abs(S) ** 2) / np.maximum(Pa * Pb, 1e-30)))
    ang = float(np.degrees(np.angle(S[BAND].sum())))
    angn = float(np.degrees(np.angle(Sn[BAND].sum())))
    print("  %d windows / %d blocks" % (n, len(set(ep))))
    print("  arg(csd(b4, rate_c)) at 22-26 Hz = %+.1f deg   coh2 %.4f" % (ang, coh))
    print("  TIME-REVERSED NULL              = %+.1f deg   (should be incoherent/arbitrary)" % angn)
    print("\n  🛑 INTERPRETATION IS NOT MINE TO MAKE ALONE -- the sign convention (LKAS and driver")
    print("     torque are in OPPOSITE frames) must be applied once, deliberately, by whoever")
    print("     converts this into a pump-or-damp verdict.")
