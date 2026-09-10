# -*- coding: utf-8 -*-
"""studies/grind/adv_v290_wire_phase.py -- MODEL-FREE sign check for V290: the phase of the 427 torque tap (T) relative to
the wheel rate in the 18-22 Hz band during grinding windows, on V282 (r39), V288 (r5e_v288) and V289 (r62/r63), plus the
V289 cave's own b4.5 = sign(n) against the rate.   Agent advphys, 2026-09-09.  Analysis only.

What this measures: T = -R * wire  (R = the loop's return ratio, T per raw count of x = -wire); rate_x = -wire/CPD, so the
transfer rate_x -> T has EXACTLY the angle of R.  The byte-derived prediction (adv_v290_physics.py): V282/V288 R(20.3) =
1.74 at -72.6 deg; V289 R swings through the notch (+25 deg at 20.3, but steep across 18-22).  The 0x1AB tap reads ~3.9 ms
after the 0x18F snapshot it responds to (creep20 sec. 1.0), so the corrected angle = raw + 360 f tau.
Windows: the census recipe (2 s / 0.5 s step / engaged lateral / bar 15-26 Hz prominence >= 8 AND bar 18-22 >= 40 raw),
tap on its native 50 Hz instants (creep20.native_tap_segment), pooled cross-spectra nperseg 64 (0.78 Hz).
Run: python adv_v290_wire_phase.py    (writes _scratch/adv_v290_wire_phase.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import v280_map_profiles as V                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST, W, STEP = 100.0, 50.0, 200, 50
TAU = 0.0039
ROUTES = (("r39", "V282"), ("r5e_v288", "V288r2"), ("r62_v289", "V289"), ("r63_v289", "V289"))
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def present_windows(g):
    """census windows (start frame) where the 18-22 Hz bar line is present, engaged lateral only."""
    starts = []
    for aa, bb in C20.runs(g["eng"], W):
        for s in range(aa, bb - W + 1, STEP):
            f0, prom, _, _ = GI.line_of(g["bar"][s:s + W], FS)
            if np.isfinite(f0) and prom >= 8 and GI.band(g["bar"][s:s + W], 18, 22) >= 40:
                starts.append((s, f0))
    return starts


def pooled_phase(g, starts, label):
    P = C20.Pool(FST, 64); secs = 0
    for s, f0 in starts:
        seg = C20.native_tap_segment(g, s, s + W)
        if seg is None or len(seg["T"]) < 64:
            continue
        P.add({k: v - v.mean() for k, v in seg.items()}); secs += W / FS
    if P.n == 0:
        pr("  %s: no windows" % label); return None
    f = P.f
    H = P.tf("r", "T"); coh = P.coh("r", "T")
    pr("  %s: %d windows (%.0f s, overlapping), tap->rate pooled at the tap's 50 Hz instants" % (label, len(starts), secs))
    pr("   f Hz | angle(rate_x -> T) raw | corrected (+360 f tau) | |H| T per deg/s | coh")
    rows = {}
    for f0 in (16, 17, 18, 19, 19.5, 20, 20.3, 21, 22, 23, 24):
        i = int(np.argmin(np.abs(f - f0)))
        raw = np.degrees(np.angle(H[i])); corr = raw + 360 * f[i] * TAU
        rows[f0] = (corr, abs(H[i]), coh[i])
        pr("   %4.1f | %+6.0f | %+6.0f | %6.1f | %.2f" % (f[i], raw, ((corr + 180) % 360) - 180, abs(H[i]), coh[i]))
    return rows


def b5_phase(tag, g, starts):
    """V289 b4.5 = sign(n) (1 when n < 0) at the 0x14A instants vs the band-passed wire rate."""
    p = os.path.join(C20.CACHE, tag + "_b4.npz")
    if not os.path.exists(p):
        pr("  no _b4 cache for %s" % tag); return
    B = np.load(p); t14, b4 = B["t14b"], B["b4"].astype(int)
    b5 = (b4 >> 5) & 1
    # constant 0x14A-vs-0x18F frame offset: median of (t14 - nearest t18) over the route
    D = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
    t18 = D["t18"]
    j = np.clip(np.searchsorted(t18, t14), 1, len(t18) - 1)
    dt = np.minimum(np.abs(t18[j] - t14), np.abs(t18[j - 1] - t14))
    off = t14 - np.where(np.abs(t18[j] - t14) < np.abs(t18[j - 1] - t14), t18[j], t18[j - 1])
    pr("  %s b4.5: engaged duty %.3f ; 0x14A minus nearest 0x18F timestamp: median %+.1f ms, IQR %.1f ms" % (
        tag, np.mean(b5[np.interp(t14, g["t"], g["eng"].astype(float)) > 0.5]), 1e3 * np.median(off), 1e3 * (np.percentile(off, 75) - np.percentile(off, 25))))
    bp = C20.bandpass(g["wire"], 17.0, 23.0, FS)   # wire rate, band-passed on the frame axis
    an = signal.hilbert(bp)
    num = 0j; den = 0.0; n = 0
    for s, f0 in starts:
        t0, t1 = g["t"][s], g["t"][s + W - 1]
        m = (t14 >= t0) & (t14 <= t1)
        if m.sum() < 50:
            continue
        sgn = 2.0 * b5[m] - 1.0                        # +1 when n < 0
        a = np.interp(t14[m], g["t"], an.real) + 1j * np.interp(t14[m], g["t"], an.imag)
        num += np.sum(sgn * np.conj(a)); den += np.sum(np.abs(a)) ; n += m.sum()
    if n == 0:
        pr("  no b5 samples in present windows"); return
    ph = np.degrees(np.angle(num))
    pr("  %s: phase of (n<0 indicator) relative to the WIRE rate 17-23 Hz: %+.0f deg (|corr| %.2f, n=%d);" % (tag, ph, abs(num) / den, n))
    pr("      n < 0 leads/lags wire>0: prediction n = (1-N) S = -(1-N) fade C F x = +(1-N) fade C F wire -> n IN PHASE with wire (+%.0f deg incl. FCfade) => (n<0) indicator ~180 deg from wire" % 22.6)
    pr("      => predicted indicator angle ~ %+.0f deg (before the 0x14A/0x18F frame offset, which at 20 Hz is %.0f deg per ms)" % (180 + 22.6, 360 * 20.3 / 1000))


def main():
    for tag, build in ROUTES:
        try:
            g = C20.load(tag)
        except Exception as e:  # noqa: BLE001
            pr("FAILED %s: %r" % (tag, e)); continue
        g["rate_x"] = -g["wire"] / V.CPD
        starts = present_windows(g)
        pr("\n" + "=" * 120)
        pr("%s (%s): %.0f s, %.0f s engaged, %d present census windows" % (tag, build, g["t"][-1] - g["t"][0], g["eng"].sum() / FS, len(starts)))
        pr("=" * 120)
        pooled_phase(g, starts, "grinding windows")
        # control stratum: engaged v<8 hands-off runs (the mode_nature sec. 4 stratum)
        msk = g["eng"] & (g["vego"] < 8.0) & (np.abs(g["bar"]) < 400)
        ctl = [(a, np.nan) for a, b in C20.runs(msk, 128) for a in range(a, b - W + 1, W)]
        pooled_phase(g, ctl, "control: engaged v<8 hands-off, all")
        if build == "V289":
            b5_phase(tag, g, starts)
    with open(os.path.join(SCR, "adv_v290_wire_phase.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/adv_v290_wire_phase.txt")


if __name__ == "__main__":
    main()
