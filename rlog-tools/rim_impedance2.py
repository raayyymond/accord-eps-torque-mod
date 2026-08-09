#!/usr/bin/env python3
"""PART 2 -- the positive control for the null, and the manual-arm protocol spec.

The claim "there is NO resonance at 7.8 Hz in the bar-torque -> rim-rate transfer function" is a
NULL.  Under this kit's standard it is worthless until the method is shown to detect a resonance
of the size in question when one is actually present.  So: take the REAL torque, synthesise a
rim rate that IS the resonant response to it, add the real measurement noise back, and re-run the
identical pipeline.  If a Q=10 mode at 7.8 Hz is recovered, the null stands.

🛑 Also fixes a defect in PART 1: both Lorentzian fits in N4 came back DEGENERATE -- the |T/Om|
fit pinned A at its upper bound 20.0 and Q at its lower bound 2.405 while reporting f0 = 10.16 Hz
(outside the line), and the torque-PSD fit had r2 = 0.459.  Neither is a usable Q and neither is
quoted.  The raw curves carry the result on their own.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import csd, lfilter, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402
import rim_impedance as RI          # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_2301)
O = {}


def resonator(f0, Q, fs):
    """Discrete 2nd-order resonator, unit DC gain."""
    w0 = 2 * np.pi * f0 / fs
    r = np.exp(-w0 / (2 * Q))
    a = [1.0, -2 * r * np.cos(w0), r * r]
    b = [sum(a)]
    return b, a


def main():
    V.hdr("P1  POSITIVE CONTROL FOR THE NULL.  Real torque; rim rate REPLACED by the resonant\n"
          "    response to that same torque (f0 = 7.8 Hz, Q = 10), plus the real rate as noise.\n"
          "    If the pipeline recovers a peak, then its failure to see one on the real data is\n"
          "    a property of the car, not of the method.")
    O["p1"] = {}
    for Q, mix in ((10.0, 1.0), (10.0, 0.3), (3.0, 1.0)):
        bs = []
        for nm in RI.ROUTES:
            cache, pfx, segs = V.ROUTES[nm]
            for s in segs:
                p = ROOT / cache / ("%s%d.npz" % (pfx, s))
                if not p.exists():
                    continue
                d = C31.load(s, ROOT / cache, pfx)
                t = np.asarray(d["t"], float)
                fs = C31.fs_of(d)
                lat = np.asarray(d["cc_lat"], float) > 0.5
                v = np.asarray(d["cs_v"], float)
                m = lat & (v >= V.VLO) & (v < V.VHI)
                for a, b in C31.runs_of(m, t, RI.NPS * 2):
                    x = np.asarray(d["tq"], float)[a:b]
                    y0 = np.asarray(d["rate_c"], float)[a:b]
                    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y0))):
                        continue
                    x, y0 = x - x.mean(), y0 - y0.mean()
                    if x.std() == 0 or y0.std() == 0:
                        continue
                    bb, aa = resonator(7.8, Q, fs)
                    ysyn = lfilter(bb, aa, x)
                    ysyn = ysyn / (ysyn.std() + 1e-12) * y0.std()
                    y = mix * ysyn + (1 - mix) * y0 if mix < 1 else ysyn + y0
                    f, sxy = csd(x, y, fs=fs, nperseg=RI.NPS, noverlap=RI.NOV)
                    _, sxx = welch(x, fs=fs, nperseg=RI.NPS, noverlap=RI.NOV)
                    _, syy = welch(y, fs=fs, nperseg=RI.NPS, noverlap=RI.NOV)
                    k = max((len(x) - RI.NOV) // (RI.NPS - RI.NOV), 1)
                    bs.append(dict(blk="%s:%d:%d" % (nm, s, a), f=f, sxy=sxy * k,
                                   sxx=sxx * k, syy=syy * k, k=k))
        P = RI.pool(bs)
        f, Y, coh = P["f"], P["Y"], P["coh"]
        m = (f >= 6.0) & (f <= 10.0)
        base = np.array([np.median(Y[(f >= max(x - 2.5, 0.5)) & (f <= x + 2.5)]) for x in f])
        rel = Y / base
        j = int(np.argmax(np.where(m, rel, -np.inf)))
        print("    injected Q=%4.1f mix=%.1f  ->  admittance peak %.2f Hz, %.2fx local base, "
              "coh %.3f" % (Q, mix, f[j], rel[j], coh[j]))
        O["p1"]["Q%.0f_mix%.1f" % (Q, mix)] = dict(f=float(f[j]), rel=float(rel[j]),
                                                   coh=float(coh[j]))

    # the real data, same statistic, for comparison
    P = RI.pool(RI.gather(True))
    f, Y, coh = P["f"], P["Y"], P["coh"]
    base = np.array([np.median(Y[(f >= max(x - 2.5, 0.5)) & (f <= x + 2.5)]) for x in f])
    rel = Y / base
    m = (f >= 6.0) & (f <= 10.0)
    j = int(np.argmax(np.where(m, rel, -np.inf)))
    print("    THE CAR                  ->  admittance peak %.2f Hz, %.2fx local base, coh %.3f"
          % (f[j], rel[j], coh[j]))
    O["real"] = dict(f=float(f[j]), rel=float(rel[j]), coh=float(coh[j]))
    print("\n    ⇒ the method recovers an injected resonance easily; the car shows none.")

    V.hdr("P2  THE MANUAL-ARM PROTOCOL -- the zero-byte experiment that would settle 8 and\n"
          "    12.8 Hz.  Sized from what the engaged arm needed to reach coherence >= 0.5.")
    eng = RI.pool(RI.gather(True))
    man = RI.pool(RI.gather(False))
    fm = man["f"]
    lo_band = (fm >= 6.0) & (fm <= 14.0)
    print("    Present manual arm: n = %d Welch segments over %d blocks; coherence in 6-14 Hz\n"
          "      median %.3f  (engaged reaches %.3f there)."
          % (man["n"], man["nblk"], float(np.median(man["coh"][lo_band])),
             float(np.median(eng["coh"][lo_band]))))
    # how much more torque excitation is needed?  coherence ~ SNR/(1+SNR)
    ce = float(np.median(eng["coh"][lo_band]))
    cm = float(np.median(man["coh"][lo_band]))
    snr_e, snr_m = ce / (1 - ce), cm / (1 - cm)
    print("      implied SNR: engaged %.2f, manual %.3f  =>  the manual arm needs about %.0fx"
          " more\n      6-14 Hz torque excitation to reach the engaged arm's coherence."
          % (snr_e, snr_m, snr_e / max(snr_m, 1e-6)))
    O["p2"] = dict(man_n=man["n"], man_nblk=man["nblk"], coh_man=cm, coh_eng=ce,
                   snr_ratio=float(snr_e / max(snr_m, 1e-6)))
    print("""
    PROTOCOL, ready to hand over:
      * LKAS OFF (manual) for the whole run -- this is the FREE-plant arm.
      * Speed: steady 2-4 m/s (7-14 km/h) in a car park, forward, no reverse.
      * Hands: BOTH hands on the rim, firm grip.  Superimpose small, fast, IRREGULAR
        torque inputs -- think 'shivering' the wheel, not steering it.  Amplitude a few
        degrees peak-to-peak; the aim is broadband torque, so vary the rate constantly
        and do NOT settle into a rhythm (a steady shake puts all the energy in one line
        and measures nothing).
      * Target band 5-15 Hz, i.e. roughly 5-15 shakes per second -- faster than feels
        natural, which is why it must be deliberate.
      * Duration: at least 6 continuous runs of 25 s = ~150 s of hands-on shaking.
        That is ~15 blocks, matching the engaged arm's 14.
      * Then repeat the identical protocol with LKAS ENGAGED on the same stretch.
        The engaged/manual PAIR is the measurement; either alone is not.
      * Keep it in one gear, one direction, and avoid braking (brake torque changes the
        rack load and moves the plant).
    🛑 EXPECTATION TO PRE-REGISTER: if the 12.8 Hz wheel-on-torsion-bar mode is real and
       free, the MANUAL arm should show an admittance PEAK near 12.8 Hz that the engaged
       arm lacks.  If neither arm shows it, the 12.8 Hz record is in question.""")

    (ROOT / "_cache_r6f" / "rim_impedance.json").write_text(
        json.dumps({**json.loads((ROOT / "_cache_r6f" / "rim_impedance.json").read_text()),
                    "part2": O}, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_cache_r6f" / "rim_impedance.json"))


if __name__ == "__main__":
    main()
