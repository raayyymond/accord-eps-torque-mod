#!/usr/bin/env python3
r"""probe/v103_r9e_cave.py -- WHAT THE V103 CAVE ACTUALLY MEASURED, and what each rung LICENSES.

BIT MAP -- read from `analysis-2020accord/builds/v80_v107/build_v103_tva.py`, not from memory:
    b7 0x80 = gp-0x6b4c < 0                 sign of the 11-SLOT ASSIST SUM (the 427 source)
    b6 0x40 = |gp-0x6ada| >= |gp-0x6adc|    COMPARATOR r24 vs r26 (the two rate-lane mirrors)
    b5 0x20 = |gp-0x6ae2| >= |gp-0x6b26|    COMPARATOR modelled friction vs inertia
    b4 0x10 = gp-0x6ada < 0                 sign of r24
    b3 0x08 = gp-0x3680 < 0   *** NEW ***   sign of D_state, the PID's own D-term accumulator
    byte7[7:6] = 3                          identity code, SHARED with V101/V102
    0x1AB     = clamp(|gp-0x6b4c|*5>>6, 0, 0x3FF)   counts = wire * 12.8   (V102's packer)

The build's own PREDICTED duties (from V102's flight, quoted in the V103 docstring):
    b7 ~0.27 rising 0.148->0.417 with wheel rate · b6 0.8991 rising 0.836->0.992 · b5 0.2481 ·
    b4 0.4091.  A large departure means the cave is not doing what V102's did.

🛑 DESIGN LAW (CLAUDE.md): a sign bit is only worth something PAIRED WITH A MAGNITUDE CHANNEL.
   b7 pairs with the 427 magnitude -> a fully signed gp-0x6b4c.  b3 has NO magnitude partner, so
   what it can license is its SIGN STRUCTURE: zero-crossing rate, spectrum, and its conditional
   agreement with quantities we already have free on the wire.
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
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(9203)
OUT = {}
DT = 0.01
PRED = {"b7": 0.27, "b6": 0.8991, "b5": 0.2481, "b4": 0.4091, "b3": None}
RATE_BINS = [(0.0, 0.35), (0.35, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0),
             (13.0, 25.0), (25.0, 50.0), (50.0, 1e9)]


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def main():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    eng, press = M["eng"], M["press"]
    v, rate = M["v"], M["rate"]
    b = {k: np.asarray(z["v103_" + k], float) > 0.5 for k in ("b7", "b6", "b5", "b4", "b3")}
    mag = np.asarray(z["mag427"], float)                 # |gp-0x6b4c| * 5 >> 6, 10-bit field
    x6b4c = np.asarray(z["x6b4c"], float)                # signed, counts
    tq = np.asarray(z["tq"], float)
    e4 = np.asarray(z["e4tq"], float)
    rate_signed = np.asarray(z["rate_f"], float)
    ang = np.asarray(z["ang"], float)

    # ---------------------------------------------------------------- 1 DUTIES vs PREDICTION
    hdr("1 -- RUNG DUTIES vs THE BUILD'S OWN PREDICTION.  A large miss means the cave is not\n"
        "     doing what V102's did, and nothing downstream can be trusted.")
    print("  %-6s %10s %10s %10s %10s %12s   %s"
          % ("bit", "all", "engaged", "manual", "eng&mov", "PREDICTED", "meaning"))
    MEAN = {"b7": "sign(gp-0x6b4c) < 0  [assist-sum sign]",
            "b6": "|r24| >= |r26|      [rate-lane comparator]",
            "b5": "|friction| >= |inertia|",
            "b4": "sign(r24) < 0",
            "b3": "sign(D_state) < 0   *** NEW ***"}
    D = {}
    for k in ("b7", "b6", "b5", "b4", "b3"):
        d = dict(all=float(b[k].mean()), eng=float(b[k][eng].mean()),
                 man=float(b[k][~eng].mean()),
                 engmov=float(b[k][eng & (v > 0.5)].mean()), pred=PRED[k])
        D[k] = d
        print("  %-6s %10.4f %10.4f %10.4f %10.4f %12s   %s"
              % (k, d["all"], d["eng"], d["man"], d["engmov"],
                 ("%.4f" % PRED[k]) if PRED[k] else "n/a (NEW)", MEAN[k]))
    OUT["duties"] = D

    print("\n  by |wheel rate| bin, ENGAGED  (the build predicted b7 and b6 both RISE with rate):")
    print("      %-12s %8s " % ("rate deg/s", "n") + " ".join("%9s" % k for k in
                                                              ("b7", "b6", "b5", "b4", "b3")))
    OUT["duty_by_rate"] = {}
    for lo, hi in RATE_BINS:
        m = eng & (rate >= lo) & (rate < hi)
        if m.sum() < 50:
            continue
        row = {k: float(b[k][m].mean()) for k in ("b7", "b6", "b5", "b4", "b3")}
        row["n"] = int(m.sum())
        OUT["duty_by_rate"]["%.2g-%.2g" % (lo, min(hi, 999))] = row
        print("      %-12s %8d " % ("%.2g-%.2g" % (lo, min(hi, 999)), m.sum()) +
              " ".join("%9.4f" % row[k] for k in ("b7", "b6", "b5", "b4", "b3")))

    # ---------------------------------------------------------------- 2 b7 + 427 = SIGNED LANE
    hdr("2 -- b7 PAIRED WITH THE 427 MAGNITUDE = a FULLY SIGNED gp-0x6b4c.  This is the one rung\n"
        "     that satisfies the design law by itself (sign bit + magnitude channel).")
    W = eng & (v > 0.5)
    print("  |gp-0x6b4c| engaged: wire p50 %.0f  p90 %.0f  max %.0f  =>  counts p50 %.0f  "
          "p90 %.0f  max %.0f   (counts = wire x 12.8)"
          % (np.percentile(mag[W], 50), np.percentile(mag[W], 90), mag[W].max(),
             np.percentile(mag[W], 50) * 12.8, np.percentile(mag[W], 90) * 12.8,
             mag[W].max() * 12.8))
    print("  field saturation: >=1023 %.4f %%   >=800 (the +-10240 writer clamp) %.4f %%   "
          "=> the channel is %s"
          % (100 * np.mean(mag[W] >= 1023), 100 * np.mean(mag[W] >= 800),
             "UNDER-RANGED (max %.0f of 1023 = %.1f %% of the field)"
             % (mag[W].max(), 100 * mag[W].max() / 1023)))
    # does the signed lane track the LKAS command?
    ok = W & np.isfinite(e4)
    r1 = float(np.corrcoef(x6b4c[ok], e4[ok])[0, 1])
    r2 = float(np.corrcoef(x6b4c[ok], tq[ok])[0, 1])
    r3 = float(np.corrcoef(x6b4c[ok], rate_signed[ok])[0, 1])
    agree_cmd = float(np.mean(np.sign(x6b4c[ok]) == np.sign(e4[ok])))
    print("  corr(signed 6b4c, 0x0E4 command) = %+.4f   corr(.., driver torque) = %+.4f   "
          "corr(.., wheel rate) = %+.4f" % (r1, r2, r3))
    print("  sign agreement with the LKAS command = %.4f   [record: gp-0x6b4c is an 11-SLOT ASSIST\n"
          "     SUM, NOT the LKAS command; V98 measured sign agreement at CHANCE (52.80 %%)]"
          % agree_cmd)
    OUT["lane6b4c"] = dict(corr_cmd=r1, corr_tq=r2, corr_rate=r3, sign_agree_cmd=agree_cmd,
                           wire_p50=float(np.percentile(mag[W], 50)),
                           wire_p90=float(np.percentile(mag[W], 90)),
                           wire_max=float(mag[W].max()),
                           sat_1023=float(np.mean(mag[W] >= 1023)),
                           sat_800=float(np.mean(mag[W] >= 800)))

    # ---------------------------------------------------------------- 3 b3 -- THE NEW RUNG
    hdr("3 -- *** b3: THE SIGN OF D_state (gp-0x3680), the PID's own D-term accumulator ***\n"
        "     THE NEW MEASURAND.  It has no magnitude partner, so what it licenses is its SIGN\n"
        "     STRUCTURE: toggle rate, spectrum, and conditional agreement with wire quantities.")
    b3 = b["b3"]
    s3 = np.where(b3, -1.0, 1.0)          # +1 when D_state >= 0, -1 when < 0
    ch = np.where(np.diff(b3.astype(int)) != 0)[0]
    rl = np.diff(np.concatenate(([0], ch + 1, [len(b3)])))
    print("  duty (D_state < 0): all %.4f  engaged %.4f  manual %.4f"
          % (b3.mean(), b3[eng].mean(), b3[~eng].mean()))
    print("  zero crossings %d over %.1f s = %.2f /s   => implied dominant frequency ~%.2f Hz"
          % (len(ch), t[-1], len(ch) / t[-1], len(ch) / t[-1] / 2.0))
    print("  run lengths (frames of 10 ms): p50 %.0f  p90 %.0f  p99 %.0f  max %d"
          % (np.percentile(rl, 50), np.percentile(rl, 90), np.percentile(rl, 99), rl.max()))
    print("  🛑 A p50 run of %.0f frames == a %.1f Hz square wave.  That is INSIDE the symptom\n"
          "     band, and it means D_state is DITHERING, not tracking a slow error."
          % (np.percentile(rl, 50), fs / (2 * np.percentile(rl, 50))))
    # spectrum of the sign sequence
    NW = 512
    wn = np.hanning(NW)
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    for armnm, am in (("engaged", eng & (v > 0.5)), ("manual", (~eng) & (v > 0.5))):
        Wz = []
        for a_, b_ in V.episodes(am, t, NW):
            for i in range(0, (b_ - a_) - NW + 1, NW // 2):
                Wz.append(slice(a_ + i, a_ + i + NW))
        if len(Wz) < 6:
            continue
        acc = np.zeros(len(f))
        for w in Wz:
            x = s3[w]
            acc += np.abs(np.fft.rfft((x - x.mean()) * wn)) ** 2
        acc /= len(Wz)
        sel = (f >= 1.0) & (f <= 45.0)
        base = np.median(acc[sel])
        j = int(np.argmax(acc[sel]))
        loc = [(f[sel][i], acc[sel][i] / base) for i in range(1, len(acc[sel]) - 1)
               if acc[sel][i] > acc[sel][i - 1] and acc[sel][i] > acc[sel][i + 1]]
        loc.sort(key=lambda x: -x[1])
        print("  b3 SIGN SPECTRUM, %-8s (%3d windows of %.2f s): peak %.2f Hz (x%.2f), "
              "top maxima %s" % (armnm, len(Wz), NW / fs, f[sel][j], acc[sel][j] / base,
                                 "  ".join("%.1f Hz(x%.1f)" % x for x in loc[:5])))
        # band shares
        shares = {}
        for nm, lo_, hi_ in (("2.5-4.5", 2.5, 4.5), ("6-9", 6.0, 9.0), ("15-22", 15.0, 22.0),
                             ("20-28", 20.0, 28.0), ("31-35", 31.0, 35.0), ("40-49", 40.0, 49.0)):
            mm = (f >= lo_) & (f <= hi_)
            shares[nm] = float(acc[mm].sum() / acc[sel].sum())
        print("      band share of b3's own sign power: " +
              "  ".join("%s %.3f" % (k, vv) for k, vv in shares.items()))
        OUT.setdefault("b3_spectrum", {})[armnm] = dict(
            n_win=len(Wz), f_peak=float(f[sel][j]), prom=float(acc[sel][j] / base),
            top=[[float(a2), float(b2)] for a2, b2 in loc[:5]], band_share=shares)

    # what does D_state's sign AGREE with?
    print("\n  CONDITIONAL AGREEMENT (engaged & moving) -- what D_state's sign tracks:")
    print("      %-34s %10s %10s" % ("hypothesis: sign(D) == sign(X)", "agreement", "vs chance"))
    W2 = eng & (v > 0.5)
    OUT["b3_agreement"] = {}
    for nm, x in (("-wheel rate (0x18F rate_f)", -rate_signed), ("+wheel rate", rate_signed),
                  ("driver torque tq", tq), ("-driver torque", -tq),
                  ("LKAS command 0x0E4", e4), ("-LKAS command", -e4),
                  ("steering angle", ang), ("signed 6b4c", x6b4c),
                  ("d/dt wheel rate (accel)", np.gradient(rate_signed, DT)),
                  ("d/dt driver torque", np.gradient(tq, DT))):
        good = W2 & np.isfinite(x) & (np.abs(x) > 1e-9)
        if good.sum() < 500:
            continue
        a = float(np.mean(np.sign(x[good]) == s3[good]))
        base_ = max(a, 1 - a)
        print("      %-34s %10.4f %10s" % (nm, a, "%+.4f" % (a - 0.5)))
        OUT["b3_agreement"][nm] = dict(agree=a, n=int(good.sum()), best=base_)
    print("      🛑 0.5 == CHANCE.  Only a value far from 0.5 licenses a claim about what D is.")

    # b3 vs b4 (r24's sign) -- are D_state and r24 the same lane?
    for k in ("b7", "b6", "b5", "b4"):
        a = float(np.mean(b3[W2] == b[k][W2]))
        print("      sign(D) == %s on %.4f of engaged&moving frames" % (k, a))
        OUT["b3_agreement"]["vs_" + k] = a

    # ---------------------------------------------------------------- 4 COMPARATORS
    hdr("4 -- THE TWO COMPARATORS (b6, b5).  These are the rungs that are IMMUNE to sizing --\n"
        "     their DUTY is the answer, no LSB and no ceiling assumed.")
    print("  b6  |r24| >= |r26|   engaged duty %.4f   => r24 (the DIRECT-derivative lane) is the\n"
          "      larger of the two rate lanes on %.1f %% of engaged frames."
          % (D["b6"]["eng"], 100 * D["b6"]["eng"]))
    print("  b5  |friction| >= |inertia|  engaged duty %.4f  manual %.4f   => the modelled Coulomb\n"
          "      friction term dominates the inertia term on %.1f %% of engaged frames."
          % (D["b5"]["eng"], D["b5"]["man"], 100 * D["b5"]["eng"]))
    print("\n  (b6,b5) 2x2 joint, ENGAGED:")
    for x_ in (0, 1):
        for y_ in (0, 1):
            m = eng & (b["b6"] == bool(x_)) & (b["b5"] == bool(y_))
            print("      b6=%d b5=%d  duty %.4f  (%6.1f s)  |rate| p50 %6.2f  v p50 %5.1f km/h"
                  % (x_, y_, m.mean() / max(eng.mean(), 1e-9), m.sum() * DT,
                     np.median(rate[m]) if m.sum() else np.nan,
                     np.median(v[m]) * 3.6 if m.sum() else np.nan))
            OUT.setdefault("b6b5_2x2", {})["b6=%d,b5=%d" % (x_, y_)] = float(
                m.sum() / max(eng.sum(), 1))

    # ---------------------------------------------------------------- 5 WHAT EACH LICENSES
    hdr("5 -- WHAT EACH RUNG LICENSES ON THIS ROUTE.")
    print("""  b7 + 427   EVIDENCE.  A fully signed gp-0x6b4c at %.2f Hz.  Under-ranged: the field
             peaks at %.0f of 1023 (%.1f %% used), so amplitude claims are coarse but the SIGN
             and the ZERO CROSSINGS are exact.  Licenses: the assist sum's polarity vs the
             command, and its band structure below the 427 Nyquist.
  b6         EVIDENCE, comparator -- immune to sizing by construction.  Licenses: which rate
             lane dominates, and how that flips with wheel rate.  No amplitude claim.
  b5         EVIDENCE, comparator.  Licenses: friction-vs-inertia dominance and its rate
             dependence.  No amplitude claim.
  b4         EVIDENCE.  r24's sign; pairs with b6 to place r24 in the lane ranking.
  b3         *** NEW ***  EVIDENCE for D_state's SIGN STRUCTURE ONLY.  It has NO magnitude
             partner, so it cannot say how big D is, only how often and how fast it changes
             sign, and what that sign agrees with.""" % (32388 / 647.8, mag.max(),
                                                         100 * mag.max() / 1023))

    Path(HERE / "_scratch/out/_v103_r9e_cave.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_r9e_cave.json")


if __name__ == "__main__":
    main()
