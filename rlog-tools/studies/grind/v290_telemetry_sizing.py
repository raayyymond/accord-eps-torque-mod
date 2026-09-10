# -*- coding: utf-8 -*-
"""studies/grind/v290_telemetry_sizing.py -- SIZE THE V290 CAVE TELEMETRY BITS AGAINST MEASURED DATA.

Agent `instr290` (SUBAGENT, orchestrator `main`), 2026-09-09.  Analysis only: builds nothing, flashes
nothing, sends nothing.

The V290 element under design is a Q14 TDF-II RBJ NOTCH at 21.5 Hz, Q 1.5, fs 1 kHz, applied to the
RATE OPERAND x = gp-0x6a56 at hook 0x28F4C (cave 0xC4C90), plus the feedback lag pole 16.5 -> 40/50 Hz.
The kit's probe design law forbids spending a telemetry rung on a bare threshold against a quantity
whose distribution has never been measured.  This script MEASURES the distributions, on the wire, for
every candidate rung, so the bit table in
`docs/specs/design/DESIGN-V290-TELEMETRY-2026-09-09.md` is sized rather than guessed.

x on the wire: CAN 0x18F[2:3] carries -(gp-0x6a56) DIRECTLY (kit memory
`accord-gp6a56-is-motor-rate-not-an-angle-sensor.md`, re-cited by
`docs/traces/TRACE-2026-09-09-v290-postlag-hook-rate-operand-ram.md` Q1(ii)), so x = -rate in RAW
COUNTS, LSB 1, and the cache's `rate` column is exactly that stream.  The cave runs at 1 kHz and the
wire samples it at 100 Hz, so the wire's x is a 10x-decimated view: every duty below is computed BOTH
on a zero-order-hold upsample to 1 kHz (the correct model if gp-0x6a56 is refreshed at 100 Hz) AND on
a linear interpolation (the optimistic model if it is refreshed faster), and the spread between the
two is reported as the honest uncertainty.  Content above 50 Hz is INVISIBLE to this method -- that is
stated, not hidden, and is precisely why bit b3 exists.

Routes: r39 (V282 -- V290's BASE), r62_v289 / r63_v289 (V289 -- they carry the 15-17 Hz line V290 has
to handle).  Caches `analysis-2020accord/_scratch/cache/v280/<key>.npz`, never rewritten.

Run:  python v290_telemetry_sizing.py    ->  _scratch/v290_telemetry_sizing.txt
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
SCR = os.path.join(KIT, "analysis-2020accord", "_scratch")
OUT = os.path.join(SCR, "v290_telemetry_sizing.txt")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS_WIRE = 100.0
FS_CAVE = 1000.0
UP = 10
QSH = 14
GUARD = 12000                      # Honda's |x| <= 12000 implausibility BAIL at 0x28F50


def rbj_notch_q14(f0, q, fs=FS_CAVE, qsh=QSH):
    """RBJ notch, normalised to a0 = 1<<qsh, rounded to integers exactly as build_v289_tva.py does."""
    w0 = 2.0 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2.0 * q)
    a0 = 1.0 + alpha
    scale = float(1 << qsh)
    b0 = int(round(scale * 1.0 / a0))
    b1 = int(round(scale * (-2.0 * np.cos(w0)) / a0))
    a2 = int(round(scale * (1.0 - alpha) / a0))
    a1 = b1
    return b0, b1, b0, (1 << qsh), a1, a2


def notch_response(b0, b1, b2, a0, a1, a2, f, fs=FS_CAVE):
    w, h = signal.freqz([b0, b1, b2], [a0, a1, a2], worN=2.0 * np.pi * np.asarray(f) / fs)
    return np.abs(h)


def run_cave(x, b0, b1, a2, qsh=QSH):
    """Byte-exact mirror of the V289/V290 cave recursion (integer, floor-shift, 14-bit residual `e`).

        acc = b0*x + s1 + e ; y = acc >> qsh ; e' = acc & mask
        s2' = b0*x - a2*y   ; n = x - y ; s1' = b1*n + s2_old
    """
    mask = (1 << qsh) - 1
    s1 = s2 = e = 0
    n_out = np.empty(len(x), dtype=np.int64)
    y_out = np.empty(len(x), dtype=np.int64)
    for i, xi in enumerate(x):
        xi = int(xi)
        bx = b0 * xi
        acc = bx + s1 + e
        y = acc >> qsh
        e = acc & mask
        s2n = bx - a2 * y
        n = xi - y
        s1 = b1 * n + s2
        s2 = s2n
        n_out[i] = n
        y_out[i] = y
    return y_out, n_out


def load(key):
    d = np.load(os.path.join(CACHE, key + ".npz"))
    t18 = d["t18"].astype(float)
    rate = d["rate"].astype(float)
    sca = d["sca"].astype(int)
    # lateral engaged = SCA on 0x18F AND STEER_REQUEST on 0xE4, per the session's standing definition
    req = np.interp(t18, d["te4"].astype(float), d["req"].astype(float)) > 0.5
    eng = (sca == 1) & req
    return t18, -rate, eng, d


def upsample(x, mode):
    if mode == "zoh":
        return np.repeat(x, UP)
    n = len(x)
    return np.interp(np.arange(n * UP) / float(UP), np.arange(n), x)


def duty(mask, sel):
    sel = np.asarray(sel, dtype=bool)
    if sel.sum() == 0:
        return float("nan")
    return float(np.asarray(mask, dtype=bool)[sel].mean())


def band_env(x, f_lo, f_hi, fs=FS_WIRE):
    b, a = signal.butter(2, [f_lo / (fs / 2), f_hi / (fs / 2)], btype="band")
    return np.abs(signal.hilbert(signal.filtfilt(b, a, x)))


def main():
    lines = []

    def P(s=""):
        print(s)
        lines.append(s)

    F0, Q = 21.5, 1.5
    b0, b1, b2, a0, a1, a2 = rbj_notch_q14(F0, Q)
    P("=" * 100)
    P("V290 TELEMETRY SIZING -- measured duties for every candidate rung")
    P("=" * 100)
    P(f"notch: RBJ f0={F0} Hz Q={Q} fs=1000 -> Q14  b0={b0} b1={b1} b2={b2} | a0={a0} a1={a1} a2={a2}")
    ff = np.array([0.0, 5, 7.5, 10, 12, 14, 15, 16, 16.5, 17, 18, 20, 21.5, 23, 25, 27, 30, 40, 60, 100, 200, 499.9])
    mag = notch_response(b0, b1, b2, a0, a1, a2, ff)
    P("  |H(f)| of the quantised notch (and |1-H| = the removed component's gain):")
    P("    f Hz : " + " ".join(f"{v:7.1f}" for v in ff))
    P("    |H|  : " + " ".join(f"{v:7.3f}" for v in mag))
    # gain of the "removed" path n = x - y  (as a transfer, 1 - H(z), evaluated by the same freqz)
    w, hN = signal.freqz([b0, b1, b2], [a0, a1, a2], worN=2 * np.pi * ff / FS_CAVE)
    P("    |1-H|: " + " ".join(f"{abs(1 - v):7.3f}" for v in hN))
    P()
    P("The notch is 3 dB down (|1-H| >= 0.707) over the band where the REMOVED component dominates:")
    fgrid = np.linspace(0.1, 100, 20000)
    _, hg = signal.freqz([b0, b1, b2], [a0, a1, a2], worN=2 * np.pi * fgrid / FS_CAVE)
    inband = fgrid[np.abs(1 - hg) >= 0.5]
    P(f"    |1-H| >= 0.50 over {inband.min():.2f}-{inband.max():.2f} Hz "
      f"(the notch's own -6 dB rejection band; V289's Q3 at 20.05 Hz was much narrower)")
    P()

    results = {}
    for key, label in (("r39", "V282  (V290's BASE)"),
                       ("r62_v289", "V289 route 62"),
                       ("r63_v289", "V289 route 63")):
        t18, x, eng, d = load(key)
        P("=" * 100)
        P(f"{key}   {label}    n={len(x)} frames, engaged {eng.sum()} ({eng.mean() * 100:.1f} %)")
        P("=" * 100)
        P(f"  |x| raw counts: max {np.abs(x).max():.0f}   p99 {np.percentile(np.abs(x), 99):.0f}   "
          f"p50 {np.percentile(np.abs(x), 50):.0f}   (Honda's BAIL guard is |x| > {GUARD})")

        # --- the 15-22 Hz grinding envelope on the wire, used to define "symptomatic" frames --------
        env = band_env(x, 13.0, 22.5)
        thr = np.percentile(env[eng], 90) if eng.sum() else np.inf
        grind = eng & (env >= thr)
        P(f"  13-22.5 Hz envelope: engaged p50 {np.percentile(env[eng], 50):.0f}  p90 {thr:.0f}  "
          f"max {env[eng].max():.0f} raw   -> 'symptomatic' = engaged & env>=p90 ({grind.sum()} frames)")

        for mode in ("zoh", "lin"):
            xu = np.round(upsample(x, mode)).astype(np.int64)
            engu = np.repeat(eng, UP)
            grindu = np.repeat(grind, UP)
            y, n = run_cave(xu, b0, b1, a2)
            ax, an, ay = np.abs(xu), np.abs(n), np.abs(y)
            dif = np.abs(np.diff(np.concatenate([[xu[0]], xu])))   # |x - x_prev|, the 1 kHz differencer

            P(f"  --- upsample = {mode} -----------------------------------------------------------")
            P(f"      |y| max {ay.max()}  ({ay.max() / max(1, np.abs(xu).max()):.3f} x |x|max)  "
              f"-> the +-{GUARD} guard {'BINDS' if ay.max() > GUARD else 'NEVER binds'} "
              f"(headroom x{GUARD / max(1, ay.max()):.1f})")
            P(f"      b5  sign(n)<0                duty  eng {duty(n < 0, engu):.4f}   "
              f"diseng {duty(n < 0, ~engu):.4f}   symptomatic {duty(n < 0, grindu):.4f}")
            row = {"b5_eng": duty(n < 0, engu)}
            P("      b7  |n| >= |x|>>S            S:   " + "  ".join(f"{s:>6d}" for s in range(0, 7)))
            for name, sel in (("eng", engu), ("symptomatic", grindu), ("diseng", ~engu)):
                vals = [duty(an >= (ax >> s), sel) for s in range(0, 7)]
                P(f"          {name:<14s}                 " + "  ".join(f"{v:6.3f}" for v in vals))
                row["b7_" + name] = vals
            # separation between symptomatic and quiet frames -- the figure of merit for choosing S
            quiet = engu & ~grindu
            sep = [duty(an >= (ax >> s), grindu) - duty(an >= (ax >> s), quiet) for s in range(0, 7)]
            P("          SEPARATION (sympt-quiet)         " + "  ".join(f"{v:6.3f}" for v in sep))
            best = int(np.nanargmax(sep))
            P(f"          -> best separation at S={best} ({sep[best]:+.3f})")
            row["b7_sep"] = sep
            row["b7_best_S"] = best
            P(f"      b3  |x-x_prev| >= |n|        duty  eng {duty(dif >= an, engu):.4f}   "
              f"diseng {duty(dif >= an, ~engu):.4f}   symptomatic {duty(dif >= an, grindu):.4f}")
            bs = best
            b7m = an >= (ax >> bs)
            P(f"          P(b3 | b7=1, S={bs})  {duty(dif >= an, engu & b7m):.4f}      "
              f"P(b3 | b7=0)  {duty(dif >= an, engu & ~b7m):.4f}   <- the dither control")
            row["b3_eng"] = duty(dif >= an, engu)
            row["b3_given_b7"] = duty(dif >= an, engu & b7m)
            row["b3_given_nb7"] = duty(dif >= an, engu & ~b7m)
            # sanity: how often would a bare |n| >= |y| (V289's b7 form) fire here?
            P(f"      (V289's form |n| >= |y| on THIS operand would read "
              f"{duty(an >= ay, engu):.4f} engaged -- shown to justify NOT reusing it)")
            row["v289form_eng"] = duty(an >= ay, engu)
            results[f"{key}:{mode}"] = row

    P()
    P("=" * 100)
    P("NOTE ON WHAT THIS CANNOT SEE: every duty above is computed from the 100 Hz wire copy of x.")
    P("Content above 50 Hz in the real 1 kHz operand is invisible to it.  b7 is a NOTCH-BAND")
    P("comparator (the notch passes >50 Hz, so n ~ 0 there) and is therefore honestly predicted;")
    P("b3 is deliberately the bit that measures what this method cannot -- its EXCESS over the")
    P("duty printed here IS the measurement of the unmodelled high-frequency content.")
    P("=" * 100)

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(OUT.replace(".txt", ".json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
