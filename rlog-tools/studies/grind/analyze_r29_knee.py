#!/usr/bin/env python3
"""studies/grind/analyze_r29_knee.py -- does driver torque kill the grinding? Route 29, BOTH segments.

THE OPERATOR'S CLAIM: "significant driver torque in a direction kills the grinding."
THE FIRMWARE MECHANISM: the driver-override curve in FUN_00028ea6 @0x29a74,
X=[70,72,78,80] Y=[254,234,12,0]. X is |driver torque| >> 5, so the knee spans
2240 -> 2560 counts and LKAS authority collapses 254 -> 0 across it.

WHY A WELCH SPLIT CANNOT ANSWER THIS. Inside the 15.4 s LKAS episode the driver crosses the knee
repeatedly; no torque bin has a contiguous 256-sample run, and most have none at 128 either. So this
script measures the mode with a ZERO-PHASE ANALYTIC-SIGNAL ENVELOPE instead: band-limit the episode
in the FFT domain, invert to the analytic signal, take |.|. That gives a per-SAMPLE amplitude, so
every sample in a torque bin contributes and n is thousands rather than zero.

  envelope time resolution ~ 1/bandwidth: [18,25] Hz -> ~0.14 s, [6,9] Hz -> ~0.33 s. Torque bin
  boundaries are therefore smeared by that much; bins are wide enough (>=240 counts) that this
  costs contrast rather than creating it.

TWO CONTROLS, both needed because the conditioning variable IS the measured channel:
  - a FLOOR band [32,45] Hz envelope from the same signal. Broadband steering activity lifts every
    band together; a real mode lifts its own band relative to the floor. Ratios are quoted.
  - the RATE channel (0x14A, x-1.0) as an independent sensor whose low-frequency content is angle
    rate, not driver torque, so binning by driver torque is not binning by its own DC.

DIRECTION. "In a direction" is tested as OPPOSING vs ASSISTING: sign(driver torque) against
sign(the 0xE4 LKAS command), with the relative sign convention established from the data.

⚠ fs = 100.01 Hz. 7.4 Hz could be 92.6, 21.1 could be 78.9. Unbreakable from CAN alone.

Usage:  python studies/grind/analyze_r29_knee.py CACHE.npz
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

sys.path.insert(0, str(Path(__file__).parents[2]))
from analyze_r29_grinding import FS, NFFT, BAND, spectrum, bandpower, peak_table, runs_of  # noqa

KNEE_LO, KNEE_HI = 2240.0, 2560.0
B_MODE = (18.0, 25.0)      # the 20-22 Hz mode
B_LOW = (6.0, 9.0)         # the 7.4 Hz limit cycle
B_FLOOR = (32.0, 45.0)     # broadband reference
B_DRV = 3.0                # low-pass corner for "sustained driver effort"


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def analytic_env(x, lo, hi):
    """|analytic signal| of x band-limited to [lo,hi]. Zero-phase, exact, no filter design."""
    n = len(x)
    w = np.ones(n)
    k = max(int(0.05 * n), 8)                      # Tukey taper to kill edge ringing
    w[:k] = 0.5 * (1 - np.cos(np.pi * np.arange(k) / k))
    w[-k:] = w[:k][::-1]
    X = np.fft.rfft((x - x.mean()) * w)
    f = np.fft.rfftfreq(n, 1 / FS)
    X[(f < lo) | (f > hi)] = 0
    Z = np.zeros(n, complex)
    Z[:len(X)] = 2 * X
    Z[0] /= 2
    return np.abs(np.fft.ifft(Z)), w


def lowpass(x, fc):
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / FS)
    X[f > fc] = 0
    return np.fft.irfft(X, n)


def main(cache):
    d = dict(np.load(cache))
    n = len(d["t"])
    sca = d["sca"] > 0.5
    tq, rc, ang, v, e4 = d["tq"], d["rate_c"], d["ang"], d["cs_v"], d["e4tq"]
    lat = d["cc_lat"] > 0.5
    e4r = d["e4req"] > 0.5
    eng = d["cs_eng"] > 0.5

    rr = runs_of(sca, 50)
    hdr(f"ROUTE 29, BOTH SEGMENTS   n={n}  {d['t'][-1]:.2f} s  fs={FS:.4f} Hz")
    print(f"  LATERAL engagement (the correct proxy):")
    for nm, x in (("carControl.latActive", lat), ("0x18F STEER_CONTROL_ACTIVE", sca),
                  ("0xE4 STEER_TORQUE_REQUEST", e4r)):
        print(f"    {nm:34s} {int(x.sum()):5d}/{n} ({100*x.mean():6.2f}%)")
    print(f"    pairwise agreement: latAct~SCA {100*(lat==sca).mean():.2f}%   "
          f"latAct~E4req {100*(lat==e4r).mean():.2f}%   SCA~E4req {100*(sca==e4r).mean():.2f}%")
    print(f"  LEGACY proxy cruiseState.enabled (long+lat, NOT lateral): "
          f"{int(eng.sum())}/{n} ({100*eng.mean():.2f}%)  -- reported for comparability only")
    print(f"  LKAS episodes: " +
          "; ".join(f"[{d['t'][a]:.2f}-{d['t'][b-1]:.2f}s n={b-a}]" for a, b in rr))

    # ============================================================ A. spectra over BOTH segments
    hdr("A. SPECTRA, BOTH SEGMENTS, LKAS-APPLYING vs NOT (nfft=256, contiguous runs, K = true dof)")
    for cname, ch in (("TORQUE 0x18F (counts)", tq), ("RATE 0x14A x-1.0 (deg/s)", rc)):
        for lbl, sel in (("SCA=1 (both episodes)", sca), ("SCA=0", ~sca)):
            f, P, K, nr = spectrum(ch, sel, NFFT)
            if P is None:
                print(f"\n  {cname} | {lbl}: no complete segment")
                continue
            print(f"\n  {cname} | {lbl}   n={int(sel.sum())} K={K} runs={nr}   "
                  f"P(15-27)={bandpower(P, f):.4g}  P(6-9)={P[(f>=6)&(f<=9)].mean():.4g}")
            print(f"     {'f (Hz)':>8s} {'prom':>8s} {'Q':>7s} {'BW':>7s}")
            for r in peak_table(f, P, 0.6, 50.0, min_prom=3.0)[:9]:
                print(f"     {r['f']:8.2f} {r['prom']:7.1f}x {r['Q']:7.1f} {r['bw']:7.3f}")

    # ------------------------------------------- is 7.4 Hz a wheel order? (tyre-line falsification)
    hdr("A2. IS THE ~7.4 Hz LINE A WHEEL ORDER? (the kit's 8.69 Hz trap: order 1 = v / 2.076 m)")
    a, b = rr[0]
    nf, hop = 128, 16
    ff = np.fft.rfftfreq(nf, 1 / FS)
    lo_b, hi_b = (ff >= 5) & (ff <= 11), (ff >= 18) & (ff <= 25)
    rows = []
    for i in range(a, b - nf + 1, hop):
        seg = tq[i:i + nf]
        c = np.polyfit(np.arange(nf), seg, 1)
        Pw = np.abs(np.fft.rfft((seg - np.polyval(c, np.arange(nf))) * np.hanning(nf))) ** 2
        rows.append((v[i:i + nf].mean(), ff[int(np.argmax(np.where(lo_b, Pw, -np.inf)))],
                     ff[int(np.argmax(np.where(hi_b, Pw, -np.inf)))]))
    R = np.array(rows)
    print(f"  {len(R)} windows (nfft=128, hop 16) inside the main episode; "
          f"vEgo {R[:,0].min():.2f}-{R[:,0].max():.2f} m/s (a {R[:,0].max()/max(R[:,0].min(),1e-9):.1f}x span)")
    print(f"  observed 5-11 Hz peak: {R[:,1].min():.2f}-{R[:,1].max():.2f} Hz "
          f"(mean {R[:,1].mean():.2f}, sd {R[:,1].std():.2f})")
    print(f"  wheel order 1 predicted over that speed span: "
          f"{R[:,0].min()/2.076:.3f}-{R[:,0].max()/2.076:.3f} Hz  -- MEASURED LINE IS "
          f"{R[:,1].mean()/(R[:,0].mean()/2.076):.0f}x HIGHER")
    print(f"  corr(vEgo, f_low) = {np.corrcoef(R[:,0], R[:,1])[0,1]:+.3f}   "
          f"corr(vEgo, f_high) = {np.corrcoef(R[:,0], R[:,2])[0,1]:+.3f}   "
          f"(an order tracks speed with corr ~ +1)")

    # ================================================= THE KNEE TEST
    hdr("B. THE DRIVER-TORQUE KNEE TEST -- does driver effort kill the grinding?")
    a, b = rr[0]
    seg = slice(a, b)
    x_tq, x_rc = tq[seg], rc[seg]
    drv = np.abs(lowpass(x_tq, B_DRV))          # sustained driver effort
    drv_raw = np.abs(x_tq)
    keep = np.ones(b - a, bool)
    k = max(int(0.05 * (b - a)), 8)
    keep[:2 * k] = keep[-2 * k:] = False         # drop taper regions from all statistics

    envs = {}
    for cn, ch in (("TQ", x_tq), ("RATE", x_rc)):
        for bn, (lo, hi) in (("mode", B_MODE), ("low", B_LOW), ("floor", B_FLOOR)):
            envs[f"{cn}_{bn}"], _ = analytic_env(ch, lo, hi)

    print(f"  main episode t={d['t'][a]:.2f}-{d['t'][b-1]:.2f}s, {b-a} samples, "
          f"{int(keep.sum())} after edge-taper exclusion")
    print(f"  driver effort |lowpass(torque,{B_DRV:.0f}Hz)|: med {np.median(drv[keep]):.0f}  "
          f"p10 {np.percentile(drv[keep],10):.0f}  p90 {np.percentile(drv[keep],90):.0f}  "
          f"max {drv[keep].max():.0f}")
    print(f"  samples above the 2240 knee: {int((drv[keep]>=KNEE_LO).sum())}  "
          f"above 2560 (authority == 0): {int((drv[keep]>=KNEE_HI).sum())}")

    edges = [0, 500, 1000, 1500, 2000, KNEE_LO, KNEE_HI, 3200, 1e9]
    print(f"\n  {'|driver effort|':>18s} {'n':>5s} | {'TQ 18-25':>10s} {'TQ 6-9':>10s} "
          f"{'TQ floor':>9s} {'18-25/fl':>9s} {'6-9/fl':>8s} | {'RATE 18-25':>11s} {'RATE/fl':>8s}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = keep & (drv >= lo) & (drv < hi)
        lbl = f"{lo:.0f}-{hi:.0f}" if hi < 1e8 else f">={lo:.0f}"
        if m.sum() < 50:
            print(f"  {lbl:>18s} {int(m.sum()):5d}   -- n<50, REFUSED --")
            continue
        md = lambda k_: np.median(envs[k_][m])
        star = "  <== KNEE" if lo == KNEE_LO else ("  <== authority 0" if lo == KNEE_HI else "")
        print(f"  {lbl:>18s} {int(m.sum()):5d} | {md('TQ_mode'):10.1f} {md('TQ_low'):10.1f} "
              f"{md('TQ_floor'):9.1f} {md('TQ_mode')/md('TQ_floor'):9.2f} "
              f"{md('TQ_low')/md('TQ_floor'):8.2f} | {md('RATE_mode'):11.3f} "
              f"{md('RATE_mode')/md('RATE_floor'):8.2f}{star}")

    print(f"\n  Spearman rank corr with driver effort, inside the episode (n={int(keep.sum())}):")
    rank = lambda z: np.argsort(np.argsort(z)).astype(float)
    for k_ in ("TQ_mode", "TQ_low", "TQ_floor", "RATE_mode", "RATE_floor"):
        r = np.corrcoef(rank(drv[keep]), rank(envs[k_][keep]))[0, 1]
        print(f"    {k_:12s} rho = {r:+.3f}")
    for k_ in ("TQ_mode", "TQ_low", "RATE_mode"):
        rat = envs[k_][keep] / envs[k_.split('_')[0] + "_floor"][keep]
        print(f"    {k_+'/floor':18s} rho = "
              f"{np.corrcoef(rank(drv[keep]), rank(rat))[0,1]:+.3f}   "
              f"<-- activity-invariant form")

    # ------------------------------------------------------- direction: opposing vs assisting
    hdr("C. DIRECTION -- is it OPPOSING torque that kills it, or any torque?")
    cmd = e4[seg]
    same = np.sign(x_tq) == np.sign(cmd)
    print(f"  sign convention check: corr(driver torque, 0xE4 command) over the episode = "
          f"{np.corrcoef(x_tq, cmd)[0,1]:+.3f}")
    print(f"  corr(lowpass(driver tq,3Hz), 0xE4 command) = "
          f"{np.corrcoef(lowpass(x_tq, B_DRV), cmd)[0,1]:+.3f}")
    print(f"  frames with sign(driver)==sign(command): {int(same.sum())}/{len(same)} "
          f"({100*same.mean():.1f}%)")
    print(f"\n  {'condition':34s} {'n':>5s} {'TQ 18-25':>10s} {'18-25/fl':>9s} {'TQ 6-9':>9s} "
          f"{'6-9/fl':>8s}")
    for lbl, m in (("same sign, effort < 2240", keep & same & (drv < KNEE_LO)),
                   ("same sign, effort >= 2240", keep & same & (drv >= KNEE_LO)),
                   ("opposite sign, effort < 2240", keep & ~same & (drv < KNEE_LO)),
                   ("opposite sign, effort >= 2240", keep & ~same & (drv >= KNEE_LO))):
        if m.sum() < 50:
            print(f"  {lbl:34s} {int(m.sum()):5d}   -- n<50, REFUSED --")
            continue
        md = lambda k_: np.median(envs[k_][m])
        print(f"  {lbl:34s} {int(m.sum()):5d} {md('TQ_mode'):10.1f} "
              f"{md('TQ_mode')/md('TQ_floor'):9.2f} {md('TQ_low'):9.1f} "
              f"{md('TQ_low')/md('TQ_floor'):8.2f}")

    # ---------------------------------------------------- Welch cross-check where n allows it
    hdr("D. WELCH CROSS-CHECK of the knee (nfft=128, contiguous runs inside torque bins)")
    print(f"  {'|driver effort|':>18s} {'n':>5s} {'K':>3s} {'runs':>5s} {'P(15-27)':>11s} "
          f"{'P(6-9)':>11s} {'peak':>7s} {'prom':>7s}")
    full_drv = np.zeros(n)
    full_drv[seg] = drv
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = sca.copy()
        m[:] = False
        m[seg] = keep & (drv >= lo) & (drv < hi)
        lbl = f"{lo:.0f}-{hi:.0f}" if hi < 1e8 else f">={lo:.0f}"
        if m.sum() < 50:
            print(f"  {lbl:>18s} {int(m.sum()):5d}   -- n<50, REFUSED --")
            continue
        f, P, K, nr = spectrum(tq, m, 128)
        if P is None:
            print(f"  {lbl:>18s} {int(m.sum()):5d} {0:3d} {0:5d}   "
                  f"-- no contiguous 128-run, REFUSED --")
            continue
        bb = (f >= BAND[0]) & (f <= BAND[1])
        b69 = (f >= 6) & (f <= 9)
        ref = (f >= 6) & (f <= 40) & ~bb
        j = int(np.argmax(np.where(bb, P, -np.inf)))
        print(f"  {lbl:>18s} {int(m.sum()):5d} {K:3d} {nr:5d} {P[bb].mean():11.4g} "
              f"{P[b69].mean():11.4g} {f[j]:7.2f} {P[j]/np.median(P[ref]):6.2f}x")

    # --------------------------------------------------- angle conditioning inside the episode
    hdr("E. |ANGLE| CONDITIONING INSIDE THE LKAS EPISODE (envelope method; the kit's 2 Hz confound)")
    aa = np.abs(ang[seg])
    print(f"  angle inside the episode: {ang[seg].min():.1f} .. {ang[seg].max():.1f} deg")
    print(f"  {'|angle| bin':>14s} {'n':>5s} {'TQ 18-25':>10s} {'18-25/fl':>9s} {'TQ 6-9':>9s} "
          f"{'6-9/fl':>8s} {'v mean':>7s} {'effort':>7s} {'f_mode':>7s}")
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 20), (20, 50), (50, 1e9)):
        m = keep & (aa >= lo) & (aa < hi)
        if m.sum() < 50:
            print(f"  {f'{lo}-{hi:g}':>14s} {int(m.sum()):5d}   -- n<50, REFUSED --")
            continue
        md = lambda k_: np.median(envs[k_][m])
        # dominant frequency in-band, from the samples in this bin, via a weighted centroid
        idx = np.flatnonzero(m)
        fr = np.fft.rfftfreq(len(x_tq), 1 / FS)
        X = np.fft.rfft((x_tq - x_tq.mean()) * np.hanning(len(x_tq)))
        bsel = (fr >= B_MODE[0]) & (fr <= B_MODE[1])
        fpk = fr[bsel][int(np.argmax(np.abs(X[bsel])))]
        print(f"  {f'{lo}-{hi:g}':>14s} {int(m.sum()):5d} {md('TQ_mode'):10.1f} "
              f"{md('TQ_mode')/md('TQ_floor'):9.2f} {md('TQ_low'):9.1f} "
              f"{md('TQ_low')/md('TQ_floor'):8.2f} {v[seg][m].mean():7.2f} "
              f"{drv[m].mean():7.0f} {fpk:7.2f}")
    print("  ⚠ f_mode here is the EPISODE-WIDE peak, not per-bin: no angle bin has a contiguous")
    print("    run long enough for its own 0.4 Hz-resolution spectrum. Per-bin frequency shifts")
    print("    CANNOT be measured on this route -- REFUSED.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1])))
