# -*- coding: utf-8 -*-
"""fvlc_camera_lock.py -- IS THE RING PHASE-LOCKED TO THE CAMERA CLOCK?
Subagent cyclekind, 2026-09-10.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

This is an INDEPENDENT re-derivation of the crux in `modeld_phase_lock.py` (subagent `modelrate`), on
MY episode definitions, MY per-build bands and all 11 routes, because it is decision-bearing and the
kit's rule is to verify the crux rather than relay it.

THE STATISTIC.  A staircase's 20 Hz component flips sign with the plan's slope, so a locked line is
locked MODULO PI and the plain circular mean cancels.  The square-law detector is

    R2 = | SUM z(t)^2 exp(-2i*2*pi*f*t) | / SUM |z(t)|^2 ,   z = analytic signal of the band

and R2 is EXACTLY the fraction of in-band energy lying on one phase axis relative to that clock.
R2 = 1 is a pure forced line; R2 = 0 is a free oscillation.

TWO THINGS I DO DIFFERENTLY, both to make the result robust to something I cannot verify:
  1  |R2| is INVARIANT to the clock's phase intercept (the intercept multiplies the sum by a unit
     complex constant), so I do NOT need modelV2 in my cache at all -- only the RATE.  f_model =
     19.99974 Hz, which `modelrate` measured to +-0.0006 Hz across six routes.
  2  I evaluate R2 in BLOCKS of 20 s and average, rather than over a whole stratum.  A whole-route
     evaluation assumes my CAN-derived time axis and the camera crystal agree to better than
     0.0003 Hz, which I cannot check; over 20 s a 0.005 Hz disagreement costs only 0.2 cycles.
     Blocking raises the finite-sample floor, which is why the floor is MEASURED, not assumed:
     the identical statistic against clocks detuned by 0.10-0.80 Hz.

THE POSITIVE CONTROL IS MANDATORY.  If my implementation cannot see the lock on the 0xE4 command --
which `modelrate` reports at R2 - floor = +0.42 in grinding -- then a null on the torque channel is
my bug, not a physical result.  The command row is printed first for exactly that reason.

Run: python fvlc_camera_lock.py     (writes _scratch/fvlc_camera_lock.txt)
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fvlc_lib as F            # noqa: E402
import fvlc_analysis as A       # noqa: E402
import creep20_loop_id as C20   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F_MODEL = 19.99974              # modeld / camera frame rate, measured by `modelrate` to +-0.0006 Hz
DET = np.r_[np.arange(-0.80, -0.099, 0.05), np.arange(0.10, 0.801, 0.05)]
BLK = 2000                      # 20 s at 100 Hz
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def analytic(x, fs, lo, hi, ntap=257):
    b = signal.firwin(ntap, [lo, hi], fs=fs, pass_zero=False)
    return signal.hilbert(signal.filtfilt(b, [1.0], np.asarray(x, float) - np.mean(x)))


def blocks_of(mask, n=BLK, minn=200):
    """Windows of n samples of ROUTE TIME, each keeping only the samples inside `mask`.

    NOT contiguous runs: grinding episodes are 1-5 s, so requiring 20 s of unbroken hot frames
    returns nothing.  R2's phase term uses ABSOLUTE t, so gaps inside a window are harmless; what
    the window length bounds is CLOCK DRIFT between my CAN time axis and the camera crystal.
    A window is kept only if it holds >= minn masked samples, so the finite-sample floor -- which is
    measured with detuned clocks on the SAME index sets -- is comparable across strata."""
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    out = []
    for a in range(0, len(mask), n):
        k = idx[(idx >= a) & (idx < a + n)]
        if len(k) >= minn:
            out.append(k)
    return out


def r2_blocks(z, t, f, blks):
    """mean R2 over blocks, and the per-block values (for a CI)."""
    v = []
    for k in blks:
        zz = z[k]
        den = float((np.abs(zz) ** 2).sum())
        if den <= 0:
            continue
        ph = np.exp(-2j * 2 * np.pi * f * t[k])
        v.append(float(np.abs((zz ** 2 * ph).sum()) / den))
    return (float(np.mean(v)) if v else np.nan), np.array(v)


def energy_blocks(z, blks):
    return np.array([float(np.mean(np.abs(z[k]) ** 2)) for k in blks])


def boot(v, n=4000, seed=3):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 3:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    b = np.array([v[rng.integers(0, len(v), len(v))].mean() for _ in range(n)])
    return float(v.mean()), float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def main():
    tags = [t for t in F.ROUTES if os.path.exists(os.path.join(F.SCR, "fvlc_%s.pkl" % t))]
    pr("IS THE RING PHASE-LOCKED TO THE CAMERA CLOCK?   cyclekind, 2026-09-10")
    pr("f_model = %.5f Hz, blocks of %.0f s, floor = max R2 over %d clocks detuned 0.10-0.80 Hz"
       % (F_MODEL, BLK / 100.0, len(DET)))
    pr("R2 is the fraction of in-band energy locked (mod pi) to the clock.  R2 - floor is the readable number.")
    pr("")
    pr("BAND 18-22 Hz on every route -- the band that CONTAINS the camera rate.  (V289's own line sits at")
    pr("16.2 Hz, 3.8 Hz away from the clock, so for V289 this band is the comb's band, not its ring's.)")
    pr("")
    pr("%-11s %-8s %-22s %-9s %5s | %-24s %8s %9s" %
       ("route", "build", "channel", "stratum", "nblk", "mean R2 [95% CI]", "floor", "R2-floor"))
    rows = {}
    for tag in tags:
        g = A.R(tag)
        eps, hot = A.EPS(tag)
        t = g["t"]
        quiet = g["eng"] & ~hot
        grind = g["eng"] & hot
        d2 = np.r_[0.0, 0.0, np.diff(g["cmd"], 2)]
        chans = [("0xE4 cmd 2nd diff", d2), ("0xE4 command", g["cmd"]),
                 ("bar driver torque", g["bar"]), ("wheel rate 0x18F", g["wire"].astype(float))]
        for name, x in chans:
            z = analytic(x, 100.0, 18.0, 22.0)
            for slab, m in (("quiet", quiet), ("grinding", grind)):
                blks = blocks_of(m)
                if len(blks) < 4:
                    continue
                r0, v0 = r2_blocks(z, t, F_MODEL, blks)
                fl = max(r2_blocks(z, t, F_MODEL + d, blks)[0] for d in DET)
                mu, lo, hi = boot(v0)
                pr("%-11s %-8s %-22s %-9s %5d | %.4f [%.4f-%.4f]%s %8.4f %+9.4f" %
                   (tag, g["build"], name, slab, len(blks), mu, lo, hi, "  ", fl, r0 - fl))
                rows[(tag, name, slab)] = dict(r2=r0, floor=fl, v=v0, blks=blks,
                                               e=energy_blocks(z, blks), build=g["build"])
        pr("")
    pr("=" * 122)
    pr("POSITIVE CONTROL CHECK -- if the 0xE4 rows are NOT above their floor, every null below is my bug.")
    pr("=" * 122)
    for nm in ("0xE4 cmd 2nd diff", "0xE4 command"):
        for slab in ("quiet", "grinding"):
            v = [rows[k]["r2"] - rows[k]["floor"] for k in rows if k[1] == nm and k[2] == slab]
            if v:
                pr("  %-20s %-9s : R2-floor over %d routes  median %+.4f   min %+.4f   max %+.4f"
                   % (nm, slab, len(v), np.median(v), min(v), max(v)))
    pr("")
    pr("=" * 122)
    pr("THE ANSWER -- the same contrast on the RING channel")
    pr("=" * 122)
    for nm in ("bar driver torque", "wheel rate 0x18F"):
        for slab in ("quiet", "grinding"):
            v = [rows[k]["r2"] - rows[k]["floor"] for k in rows if k[1] == nm and k[2] == slab]
            if v:
                pr("  %-20s %-9s : R2-floor over %d routes  median %+.4f   min %+.4f   max %+.4f"
                   % (nm, slab, len(v), np.median(v), min(v), max(v)))
    pr("")
    pr("=" * 122)
    pr("THE DECOMPOSITION THAT ANSWERS THE QUESTION")
    pr("=" * 122)
    pr("If the grinding line IS the forced response to the camera comb, the grinding EXCESS energy in the")
    pr("torque band must be LOCKED energy: dE_lock / dE_total -> 1.  If it is a free mode being rung, the")
    pr("excess is FREE: dE_lock / dE_total -> 0.  Locked energy uses the FLOOR-CORRECTED fraction")
    pr("max(R2 - floor, 0), so a finite-sample lock cannot be counted as physical.")
    pr("\u26a0 V289 rows are shown but are NOT informative: its ring sits at 16.2 Hz, outside this 18-22 band.")
    pr("")
    pr("%-11s %-8s | %10s %10s %10s | %10s %10s %9s" %
       ("route", "build", "E quiet", "E grind", "dE", "dE_lock", "dE_free", "lock frac"))
    for tag in tags:
        kq, kg = (tag, "bar driver torque", "quiet"), (tag, "bar driver torque", "grinding")
        if kq not in rows or kg not in rows:
            continue
        q, gg = rows[kq], rows[kg]
        eq, eg = float(np.mean(q["e"])), float(np.mean(gg["e"]))
        lq = max(q["r2"] - q["floor"], 0.0) * eq
        lg = max(gg["r2"] - gg["floor"], 0.0) * eg
        dE, dL = eg - eq, lg - lq
        pr("%-11s %-8s | %10.4g %10.4g %10.4g | %10.4g %10.4g %9.3f" %
           (tag, gg["build"], eq, eg, dE, dL, dE - dL, (dL / dE) if dE > 0 else np.nan))
    pr("")
    pr("=" * 122)
    pr("DOES THE RING TRACK THE **LOCKED** PART OF THE COMMAND, OR ONLY ITS FREE PART?")
    pr("=" * 122)
    pr("Per 20 s block: split the command's in-band energy into E_lock = R2_block * E and E_free =")
    pr("(1-R2_block) * E, then regress log(ring energy in bar) on each.  An ECHO of the ring lives in the")
    pr("FREE part (it is locked to the ring, not to the camera); a DRIVE lives in the LOCKED part.")
    pr("This is the clean way past the echo confound.")
    pr("\u26a0 UNDERPOWERED BY CONSTRUCTION: E_lock and E_free are both proportional to E and therefore")
    pr("nearly collinear, so the two slopes cannot be separated. Read the DIRECT R2 on the ring instead;")
    pr("this table is reported only so the attempt is on the record.")
    pr("")
    pr("%-11s %-8s %5s | %-26s %-26s" % ("route", "build", "nblk", "slope on log E_lock", "slope on log E_free"))
    from scipy import stats as st
    for tag in tags:
        k1 = (tag, "0xE4 command", "grinding")
        k2 = (tag, "bar driver torque", "grinding")
        if k1 not in rows or k2 not in rows:
            continue
        c, r = rows[k1], rows[k2]
        if len(c["v"]) < 6:
            continue
        el = np.maximum(c["v"] * c["e"], 1e-9)
        ef = np.maximum((1 - c["v"]) * c["e"], 1e-9)
        y = np.log(np.maximum(r["e"], 1e-9))
        s1 = st.linregress(np.log(el), y)
        s2 = st.linregress(np.log(ef), y)
        pr("%-11s %-8s %5d | %+.3f (p=%.3g)%s %+.3f (p=%.3g)" %
           (tag, r["build"], len(y), s1.slope, s1.pvalue, "        ", s2.slope, s2.pvalue))
    with open(os.path.join(F.SCR, "fvlc_camera_lock.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/fvlc_camera_lock.txt")


if __name__ == "__main__":
    main()
