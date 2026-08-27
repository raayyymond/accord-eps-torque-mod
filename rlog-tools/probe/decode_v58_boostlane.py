#!/usr/bin/env python3
"""probe/decode_v58_boostlane.py -- read V58's angle-rate/boost-lane probe out of an rlog.

V58 packs FIVE bits into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                        LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = (gp-0x6bbe <  0)         SIGN of the angle-rate/boost lane  <- THE DAMPING PHASE
    bit 5 = (gp-0x6bbe == +512)      lane PINNED at its ceiling (0xD20C0, flat 512)
    bit 4 = (gp-0x6b9a <  0)         SIGN of the FIR chain output = boost's AMPLITUDE GATE
    bit 3 = (gp-0x6b9a == 0)         that gate dead/zero
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

*** field = (byte4 >> 3) & 0x1F.  field == 0 means THE CAVE DID NOT FIRE -- a VOID reading, not
"everything false". Bit 7 is hard-wired 1 precisely so this tool can say that.

THE QUESTION THIS ANSWERS
-------------------------------------------------------------------------------------------------------
Is gp-0x6bbe's angle-rate tributary viscous DAMPING at 20-25 Hz, or not? Static analysis has flipped
three times: "net damping" -> "sign unresolved, baseline isn't slow" -> "damping, baseline carries no
angle rate" -> "unresolved again, because gp-0x6a56 is NOT independently sensed (it is
clamp(polarity*((gp-0x6abe*48*cal)>>15), +-12000) = MOTOR resolver rate scaled) and baseline's Branch A
is ALSO gp-0x6abe-derived, so the two may partially cancel."

STEER_ANGLE_RATE is already on the bus (0x18F[2:4], BE signed x -0.1). So the CROSS-SPECTRUM PHASE of
bit6 against it at 20-25 Hz measures the sign directly. Pure viscous damping => the lane opposes
velocity => bit6 (lane<0) leads/lags the rate by ~180 deg. A phase near 0 deg means it REINFORCES.

Method validated before the build, on V57's bit3 (also a 1-bit sign channel): coherence 0.958 at
21.31 Hz against STEER_ANGLE_RATE on route 29's grinding burst. A comparator preserves zero-crossing
timing, which is exactly what phase estimation needs.

bit5 catches the failure mode that would make the whole lever moot: the ceiling is a SATURATING clamp,
so if the lane pins at +-512 the damping derivative goes to ZERO exactly at the peaks of the grinding.
Only the POSITIVE rail is exactly testable (x>>9 == 1 iff x == 512; x>>9 == -1 for ALL x in [-512,-1]),
so read the negative rail from bit6 + bit5 jointly.

bit4/bit3 test the mechanism found 2026-07-30: gp-0x6b9a is the FIR chain output indexing boost's
NON-flat table (0xD28DC, Y = 16384..8187), landing as `blendedMagnitude` in
`term3 = (term2 * blendedMagnitude) >> 14` @0x34ffa. If that gate oscillates at 20-25 Hz it
amplitude-modulates the strongest identified carrier.

🛑 CONVENTIONS THIS TOOL ENFORCES -- all three were established the hard way on the V57 drive:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes while
     lateral is really applying 21%. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200. The oscillation
     is +-1400 counts on the same channel, so the raw test trips on the phenomenon itself and discards
     the frames carrying 8.79x the oscillation amplitude.
  3. Spectra use NON-OVERLAPPING Hann segments so the printed K is the TRUE dof.

⚠ 100 Hz sampling of a ~22 Hz phenomenon: every frequency quoted is indistinguishable from its alias
(22 Hz vs 78 Hz). Same limitation every probe in this kit has had.

Usage:  python probe/decode_v58_boostlane.py RLOG [RLOG ...]
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
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

BIT_LIVE, BIT_SIGN, BIT_RAIL, BIT_GSIGN, BIT_GZERO = 0x80, 0x40, 0x20, 0x10, 0x08
NFFT = 256


def collect(paths):
    """Pair each 0x14A probe frame with the most recent 0x18F frame (both ~100 Hz on src 1)."""
    b4, rate, tq, sca, t = [], [], [], [], []
    last_rate, last_tq, last_sca = np.nan, np.nan, -1
    lat_t, lat_v, cs_t, cs_v, v_t, v_v = [], [], [], [], [], []
    for p in paths:
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            ts = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    if m.src != 1:
                        continue
                    d = bytes(m.dat)
                    if m.address == 0x18F and len(d) >= 5:
                        a = (d[0] << 8) | d[1]
                        last_tq = (a - 0x10000 if a & 0x8000 else a) * -1.0
                        r = (d[2] << 8) | d[3]
                        last_rate = (r - 0x10000 if r & 0x8000 else r) * -0.1
                        last_sca = (d[4] >> 3) & 1
                    elif m.address == 0x14A and len(d) >= 5:
                        # 🛑 Drop 0x14A frames that arrive BEFORE the first 0x18F. Otherwise last_tq
                        # is still NaN, and a SINGLE NaN propagates through the FFT in sustained()
                        # to make EVERY sample NaN -- which silently reads as "0 hands-off frames",
                        # a plausible-looking null rather than an error. (Cost one debugging round.)
                        if last_sca < 0:
                            continue
                        b4.append(d[4]); rate.append(last_rate); tq.append(last_tq)
                        sca.append(last_sca); t.append(ts)
            elif w == "carControl":
                lat_t.append(ts); lat_v.append(bool(evt.carControl.latActive))
            elif w == "carState":
                cs_t.append(ts); cs_v.append(bool(evt.carState.cruiseState.enabled))
                v_t.append(ts); v_v.append(evt.carState.vEgo)
    d = dict(b4=np.array(b4, int), rate=np.array(rate), tq=np.array(tq),
             sca=np.array(sca, int), t=np.array(t))
    d["lat"] = (np.interp(d["t"], lat_t, np.array(lat_v, float)) > 0.5) if lat_t \
        else np.zeros_like(d["t"], bool)
    d["cru"] = (np.interp(d["t"], cs_t, np.array(cs_v, float)) > 0.5) if cs_t \
        else np.zeros_like(d["t"], bool)
    d["v"] = np.interp(d["t"], v_t, v_v) if v_t else np.full_like(d["t"], np.nan)
    return d


def sustained(x, fs, fc=3.0):
    """Zero-phase lowpass -> the DRIVER's actual push, with the oscillation removed.

    ⚠ Compute this over the SUBSET you intend to analyse, not the whole route: the filter is global,
    so a route-wide call folds parking manoeuvres into the burst's baseline. And it is NaN-fragile by
    construction (one NaN in, all NaN out), so guard the input explicitly rather than trusting it.
    """
    x = np.asarray(x, float)
    bad = ~np.isfinite(x)
    if bad.all():
        return np.full_like(x, np.inf)
    if bad.any():
        # interpolate over gaps rather than propagating NaN through the FFT
        good = ~bad
        x = x.copy()
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(good), x[good])
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    out = np.abs(np.fft.irfft(X, n=len(x)) + x.mean())
    assert np.isfinite(out).all(), "sustained() produced non-finite output"
    return out


def runs_of(mask, t, min_n):
    idx = np.where(mask)[0]
    if not len(idx):
        return
    s, prev = idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                yield s, prev + 1
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        yield s, prev + 1


def csd(x, y, fs, nfft=NFFT):
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    Pxy = np.zeros(len(f), complex); Pxx = np.zeros(len(f)); Pyy = np.zeros(len(f)); K = 0
    for i in range(0, len(x) - nfft + 1, nfft):
        X = np.fft.rfft((x[i:i + nfft] - x[i:i + nfft].mean()) * win)
        Y = np.fft.rfft((y[i:i + nfft] - y[i:i + nfft].mean()) * win)
        Pxy += X * np.conj(Y); Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; K += 1
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
    return f, coh, np.degrees(np.angle(Pxy)), K


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    fs = 1.0 / np.median(np.diff(d["t"]))
    field = (d["b4"] >> 3) & 0x1F
    print(f"\n{'=' * 90}\n{tag}   {n} frames  {d['t'][-1] - d['t'][0]:.1f}s  fs={fs:.2f} Hz")

    void = field == 0
    print(f"\n-- LIVENESS --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {void.sum()} / {n}  ({100 * void.mean():.2f}%)")
    print(f"   bit7 set                       : {(d['b4'] & BIT_LIVE != 0).sum()} / {n}")
    if void.all():
        print("\n   *** THE CAVE NEVER FIRED. Every reading below is VOID. Stop here.")
        return
    print("   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"]).most_common(8)))

    neg = (d["b4"] & BIT_SIGN) != 0
    rail = (d["b4"] & BIT_RAIL) != 0
    gneg = (d["b4"] & BIT_GSIGN) != 0
    gzero = (d["b4"] & BIT_GZERO) != 0

    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    print(f"\n-- LATERAL PROXY AGREEMENT (cruiseState is long+lat: do NOT use it) --")
    print(f"   latActive               : {d['lat'].sum():6d} ({100 * d['lat'].mean():5.2f}%)")
    print(f"   STEER_CONTROL_ACTIVE==1 : {(d['sca'] == 1).sum():6d} "
          f"({100 * (d['sca'] == 1).mean():5.2f}%)  <- the analysis subset")
    print(f"   [legacy] cruiseState    : {d['cru'].sum():6d} ({100 * d['cru'].mean():5.2f}%)  <- WRONG")
    print(f"   hands-off by SUSTAINED effort: {hands_off.sum()} "
          f"| by raw |tq|<=200: {(np.abs(d['tq']) <= 200).sum()}  <- raw discards the oscillation")

    conds = [("ALL frames", np.ones(n, bool)),
             ("LKAS applying (SCA==1)", d["sca"] == 1),
             ("LKAS applying + hands-off", (d["sca"] == 1) & hands_off),
             ("LKAS off", d["sca"] != 1)]
    print(f"\n-- THE FIVE BITS, by condition --")
    print(f"   {'condition':30s} {'n':>6s} {'lane<0':>8s} {'lane@+512':>10s} "
          f"{'gate<0':>8s} {'gate==0':>8s}")
    for name, sel in conds:
        if sel.sum() == 0:
            print(f"   {name:30s} {0:6d}   (none)"); continue
        print(f"   {name:30s} {sel.sum():6d} {100 * neg[sel].mean():7.2f}% "
              f"{100 * rail[sel].mean():9.2f}% {100 * gneg[sel].mean():7.2f}% "
              f"{100 * gzero[sel].mean():7.2f}%")

    sel = (d["sca"] == 1) & hands_off
    print(f"\n-- THE DECISIVE NUMBER: bit6 phase vs STEER_ANGLE_RATE, LKAS-applying + hands-off --")
    segs = list(runs_of(sel, d["t"], NFFT))
    if not segs:
        print(f"   no contiguous run >= {NFFT} samples ({sel.sum()} frames selected). Cannot phase.")
    else:
        x = np.concatenate([neg[a:b].astype(float) for a, b in segs])
        y = np.concatenate([d["rate"][a:b] for a, b in segs])
        if x.std() == 0:
            print("   bit6 is CONSTANT -- the lane never changed sign. No phase available.")
        else:
            f, coh, ph, K = csd(x, y, fs)
            print(f"   {len(segs)} run(s), {len(x)} samples, K={K} (non-overlapping, nfft={NFFT})")
            print(f"      {'band':>9s} {'f(Hz)':>7s} {'coher':>7s} {'phase':>9s}")
            for lo, hi in ((6, 9), (18, 21), (21, 24), (24, 27)):
                m = (f >= lo) & (f <= hi)
                j = int(np.argmax(np.where(m, coh, -np.inf)))
                print(f"      {f'{lo}-{hi}Hz':>9s} {f[j]:7.2f} {coh[j]:7.3f} {ph[j]:8.1f}d")
            m = (f >= 20) & (f <= 25)
            j = int(np.argmax(np.where(m, coh, -np.inf)))
            p, c = ph[j], coh[j]
            print(f"\n   => at {f[j]:.2f} Hz: phase {p:+.1f} deg, coherence {c:.3f}")
            if c < 0.3:
                print("      COHERENCE TOO LOW to call the sign. Need more LKAS-applying data.")
            elif abs(abs(p) - 180) < 60:
                print("      ~ANTI-PHASE with the rate => the lane OPPOSES velocity => VISCOUS DAMPING.")
                print("      Raising K1 (0xD200C=43) would ADD damping. GATE 2 answered, on-car.")
            elif abs(p) < 60:
                print("      ~IN-PHASE with the rate => the lane REINFORCES velocity => ANTI-DAMPING.")
                print("      🛑 Raising K1 would make the grinding WORSE. Cutting is the direction.")
            else:
                print("      QUADRATURE-dominated => neither clean damping nor clean anti-damping;")
                print("      the lane acts as stiffness/inertia at this frequency. K1 is not a lever.")

    print(f"\n-- HEADROOM: does the lane pin at its +-512 ceiling? --")
    if sel.sum():
        print(f"   at +512 (bit5), LKAS-applying + hands-off: {100 * rail[sel].mean():.2f}% "
              f"({rail[sel].sum()}/{sel.sum()})")
        print(f"   negative-side rail is NOT directly observable (x>>9 == -1 for all x in [-512,-1]);")
        print(f"   read it from bit6+bit5 jointly. lane<0 in {100 * neg[sel].mean():.2f}%.")
        if rail[sel].mean() > 0.05:
            print("   => THE LANE PINS. Its damping derivative is ZERO there, so K1 cannot help at the")
            print("      peaks -- the CEILING (0xD20C0 Y row, flat 512) becomes the lever, not K1.")
        else:
            print("   => the lane has headroom; K1 is a live lever if the phase above says damping.")

    print(f"\n-- THE AMPLITUDE GATE (gp-0x6b9a): does it oscillate at 20-25 Hz? --")
    if segs:
        g = np.concatenate([gneg[a:b].astype(float) for a, b in segs])
        if g.std() == 0:
            print("   bit4 CONSTANT -- the gate never changes sign. No amplitude modulation.")
        else:
            f, coh, ph, K = csd(g, np.concatenate([d["rate"][a:b] for a, b in segs]), fs)
            m = (f >= 20) & (f <= 25)
            j = int(np.argmax(np.where(m, coh, -np.inf)))
            print(f"   K={K}: peak coherence in 20-25 Hz at {f[j]:.2f} Hz = {coh[j]:.3f}, "
                  f"phase {ph[j]:+.1f} deg")
            print("   (high coherence => the FIR chain modulates boost amplitude at the mode frequency,")
            print("    i.e. blendedMagnitude is a live participant, not a slow gain)")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
