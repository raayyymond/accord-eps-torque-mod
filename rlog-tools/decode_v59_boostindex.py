#!/usr/bin/env python3
"""decode_v59_boostindex.py -- read V59's boost-index DEPTH probe out of an rlog.

V59 packs FIVE bits into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                          LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = (gp-0x6ba6 <  0)           the 0xFFFF FAULT SENTINEL from FUN_0003b66a
    bit 5 = ((gp-0x6ba6 >>  9) == 0)   index < 512    <- BELOW X1: nothing modulates
    bit 4 = ((gp-0x6ba6 >> 10) == 0)   index < 1024
    bit 3 = ((gp-0x6ba6 >> 11) == 0)   index < 2048
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

*** field = (byte4 >> 3) & 0x1F.  field == 0 means THE CAVE DID NOT FIRE -- a VOID reading, not
"everything false". Bit 7 is hard-wired 1 precisely so this tool can say that.

*** A THERMOMETER, not four flags. The thresholds nest, so bit5 => bit4 => bit3 in every valid frame.
A frame violating that is a DECODE ERROR (wrong build on the car, or a corrupt frame) and is counted
separately -- never averaged in as if it were a reading.

THE QUESTION THIS ANSWERS
-------------------------------------------------------------------------------------------------------
`gp-0x6ba6 == |gp-0x6b9a|` (byte-verified: FUN_0003b66a writes both from the same r28 at 0x3b892 /
0x3b8b0, with `subr r0,r13` @0x3b87a taking the magnitude). It indexes BOTH boost amplitude LERPs:
0xD28DC via pointer table 0xca4f4 (Y = 16384..8187) and 0xD2888 via 0xca23c (Y = 16384..8176).

V58 measured the SIGNED sibling crossing zero at 20.93 Hz -- per-run coherence 0.649/0.970/0.769/0.881
against the bus angle rate, and 13.69 toggles/s ENGAGED vs 0.61 DISENGAGED at matched creep speed. So
this index is that signal RECTIFIED: it has a minimum at every zero crossing and sweeps the boost
amplitude curve at ~2x the mode frequency, on the main assist path.

DEPTH IS THE WHOLE QUESTION. A sign bit carries no amplitude:
  * bit5 set essentially always  => the index never clears X1 = 512, the coefficient stays pinned at
    16384, and the mechanism is INERT. Do NOT flatten 0xD28DC -- it would be a lever for nothing.
  * bit5 clearing during the bursts => read how far the thermometer falls to bracket the swept Y range.
    0xD28DC / 0xD2888 become live levers, and so does the upstream EMA alpha tp+0x73ba (0xC63BA = 512).

🛑 CONVENTIONS THIS TOOL ENFORCES -- all three established the hard way on the V57/V58 drives:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes while
     lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. Bursty limit cycle => report ENVELOPE p99/max, never mean Welch power. The "V57 halved the 21 Hz"
     artifact lived entirely in a median dominated by quiet time between bursts.

⚠ Route 2b showed the grinding is CREEP-ONLY on V58 (prominence median 141x/138x/518x at 1-4 m/s vs
7-11x above 6 m/s), so condition on v <= 5 m/s or you will average the mode away.
⚠ 100 Hz sampling of a ~21 Hz phenomenon: every frequency quoted is indistinguishable from its alias
(21 Hz vs 79 Hz). Same limitation every probe in this kit has had.

Usage:  python decode_v59_boostindex.py RLOG [RLOG ...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from rlog_parse import read_messages  # noqa: E402

BIT_LIVE, BIT_FAULT, BIT_LT512, BIT_LT1024, BIT_LT2048 = 0x80, 0x40, 0x20, 0x10, 0x08
NFFT = 256

# LERP1 @0xD28DC, the curve the index walks. Used to turn a thermometer bracket into a Y range.
LERP1_X = np.array([0, 512, 1490, 2529, 3645, 5120], float)
LERP1_Y = np.array([16384, 14657, 11672, 9365, 8244, 8187], float)


def collect(paths):
    """Pair each 0x14A probe frame with the most recent 0x18F frame (both ~100 Hz on src 1)."""
    b4, rate, tq, sca, t = [], [], [], [], []
    last_rate, last_tq, last_sca = np.nan, np.nan, -1
    lat_t, lat_v, v_t, v_v = [], [], [], []
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
                        # 🛑 Drop 0x14A frames arriving BEFORE the first 0x18F -- otherwise last_tq is
                        # NaN, and a SINGLE NaN propagates through the FFT to make every sample NaN,
                        # which reads as "0 hands-off frames": a plausible null rather than an error.
                        if last_sca < 0:
                            continue
                        b4.append(d[4]); rate.append(last_rate); tq.append(last_tq)
                        sca.append(last_sca); t.append(ts)
            elif w == "carControl":
                lat_t.append(ts); lat_v.append(bool(evt.carControl.latActive))
            elif w == "carState":
                v_t.append(ts); v_v.append(evt.carState.vEgo)
    d = dict(b4=np.array(b4, int), rate=np.array(rate), tq=np.array(tq),
             sca=np.array(sca, int), t=np.array(t))
    d["lat"] = (np.interp(d["t"], lat_t, np.array(lat_v, float)) > 0.5) if lat_t \
        else np.zeros_like(d["t"], bool)
    d["v"] = np.interp(d["t"], v_t, v_v) if v_t else np.full_like(d["t"], np.nan)
    return d


def sustained(x, fs, fc=3.0):
    """Zero-phase lowpass -> the DRIVER's actual push, with the oscillation removed.

    ⚠ Compute over the SUBSET you intend to analyse, not the whole route, and guard the input: it is
    NaN-fragile by construction (one NaN in, all NaN out).
    """
    x = np.asarray(x, float)
    bad = ~np.isfinite(x)
    if bad.all():
        return np.full_like(x, np.inf)
    if bad.any():
        good = ~bad
        x = x.copy()
        x[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(good), x[good])
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    out = np.abs(np.fft.irfft(X, n=len(x)) + x.mean())
    assert np.isfinite(out).all(), "sustained() produced non-finite output"
    return out


def band_envelope(x, fs, lo, hi):
    """Analytic-signal magnitude restricted to [lo,hi] Hz -- the burst envelope, not mean power."""
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(x)))


def csd(x, y, fs, nfft=NFFT):
    """Non-overlapping Hann segments so the returned K is the TRUE dof."""
    win = np.hanning(nfft)
    f = np.fft.rfftfreq(nfft, 1 / fs)
    Pxy = np.zeros(len(f), complex); Pxx = np.zeros(len(f)); Pyy = np.zeros(len(f)); K = 0
    for i in range(0, len(x) - nfft + 1, nfft):
        X = np.fft.rfft((x[i:i + nfft] - x[i:i + nfft].mean()) * win)
        Y = np.fft.rfft((y[i:i + nfft] - y[i:i + nfft].mean()) * win)
        Pxy += X * np.conj(Y); Pxx += np.abs(X) ** 2; Pyy += np.abs(Y) ** 2; K += 1
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
    return f, coh, np.degrees(np.angle(Pxy)), K


def runs_of(mask, t, min_n):
    idx = np.where(mask)[0]
    if not len(idx):
        return
    s = prev = idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                yield s, prev + 1
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        yield s, prev + 1


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    fs = 1.0 / np.median(np.diff(d["t"]))
    field = (d["b4"] >> 3) & 0x1F
    print(f"\n{'=' * 92}\n{tag}   {n} frames  {d['t'][-1] - d['t'][0]:.1f}s  fs={fs:.2f} Hz")

    void = field == 0
    print("\n-- LIVENESS --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {void.sum()} / {n}  ({100 * void.mean():.2f}%)")
    print(f"   bit7 set                       : {(d['b4'] & BIT_LIVE != 0).sum()} / {n}")
    if void.all():
        print("\n   *** THE CAVE NEVER FIRED. Every reading below is VOID. Stop here.")
        return
    print("   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"]).most_common(8)))

    fault = (d["b4"] & BIT_FAULT) != 0
    lt512 = (d["b4"] & BIT_LT512) != 0
    lt1024 = (d["b4"] & BIT_LT1024) != 0
    lt2048 = (d["b4"] & BIT_LT2048) != 0

    bad = (lt512 & ~lt1024) | (lt1024 & ~lt2048)
    print("\n-- THERMOMETER INTEGRITY (bit5 => bit4 => bit3) --")
    print(f"   non-monotonic frames: {bad.sum()} / {n}  ({100 * bad.mean():.3f}%)")
    ok = ~bad
    # 🛑 HARD STOP, not a filter. A few stray frames are noise; a large fraction means these are not
    # V59 readings at all (V58's byte4, say), and the surviving subset will still decode into
    # plausible-looking numbers. Reporting a verdict on it is exactly the failure mode this kit keeps
    # hitting -- a confident wrong answer beats no answer only until someone flashes on it.
    if bad.mean() > 0.01:
        print("   *** STOP. Above 1% non-monotonic, these frames are NOT V59 readings -- almost")
        print("       certainly a different build on the car (V58's byte4 decodes this way).")
        print("       No verdict is computed: the surviving subset would still look plausible.")
        print(f"       byte4 values seen: {sorted(set(d['b4'].tolist()))}")
        return
    if bad.any():
        print("   (excluded from everything below rather than averaged in)")

    print("\n-- THE FAULT SENTINEL (gp-0x6ba6 == 0xFFFF, FUN_0003b66a input gate failed) --")
    print(f"   bit6 set: {fault[ok].sum()} / {ok.sum()}  ({100 * fault[ok].mean():.3f}%)")
    if fault[ok].mean() < 0.001:
        print("   => the sentinel path is NOT active. gp-0x6ba6 is a real magnitude throughout.")
    else:
        print("   !! the sentinel fires. r21 zeroes the amplitude blend whenever it does -- that is a")
        print("     100%-depth modulation and would be the mechanism outright. Check its rate vs 21 Hz.")

    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    creep = d["v"] <= 5.0
    print("\n-- ENGAGEMENT / SUBSET (cruiseState is long+lat: NOT used) --")
    print(f"   latActive               : {d['lat'].sum():6d} ({100 * d['lat'].mean():5.2f}%)")
    print(f"   STEER_CONTROL_ACTIVE==1 : {(d['sca'] == 1).sum():6d} "
          f"({100 * (d['sca'] == 1).mean():5.2f}%)  <- the analysis subset")
    print(f"   hands-off by SUSTAINED effort: {hands_off.sum()} "
          f"| by raw |tq|<=200: {(np.abs(d['tq']) <= 200).sum()}  <- raw discards the oscillation")
    print(f"   creep (v <= 5 m/s)      : {creep.sum()}  <- the grinding is CREEP-ONLY on V58")

    conds = [("ALL frames", ok),
             ("LKAS applying (SCA==1)", ok & (d["sca"] == 1)),
             ("LKAS applying + creep", ok & (d["sca"] == 1) & creep),
             ("LKAS applying + creep + hands-off", ok & (d["sca"] == 1) & creep & hands_off),
             ("LKAS off + creep", ok & (d["sca"] != 1) & creep)]
    print("\n-- THE DEPTH DISTRIBUTION -- where does the LERP index sit? --")
    print(f"   {'condition':36s} {'n':>6s} {'<512':>8s} {'512-1k':>8s} {'1k-2k':>8s} {'>=2048':>8s}")
    for name, sel in conds:
        if sel.sum() == 0:
            print(f"   {name:36s} {0:6d}   (none)")
            continue
        a = lt512[sel].mean()
        b = (lt1024 & ~lt512)[sel].mean()
        c = (lt2048 & ~lt1024)[sel].mean()
        e = (~lt2048)[sel].mean()
        print(f"   {name:36s} {sel.sum():6d} {100 * a:7.2f}% {100 * b:7.2f}% "
              f"{100 * c:7.2f}% {100 * e:7.2f}%")

    sel = ok & (d["sca"] == 1) & creep
    print("\n-- THE VERDICT: is the boost-amplitude modulation REAL or INERT? --")
    if sel.sum() == 0:
        print("   no LKAS-applying creep frames. Cannot call it.")
    else:
        below = lt512[sel].mean()
        print(f"   index < 512 (X1) on {100 * below:.2f}% of LKAS-applying creep frames")
        if below > 0.99:
            print("   => WEAK. The index stays inside the first LERP segment, so the coefficient is")
            print("      bounded to 16384..14657 -- a swing of at most 1.12x.")
            print("      *** NOT 'inert': the curve interpolates from X = 0, so it is only pinned at")
            print("      exactly 0. A 12% gain modulation at ~2x the mode frequency is still a")
            print("      parametric drive, just a modest one. Weigh that against GATE 2 (both curves")
            print("      sit on the BASE ASSIST path) before deciding 0xD28DC/0xD2888 are worth moving.")
        else:
            # bracket the swept Y range from the observed thermometer extremes
            lo_idx = 0.0 if below > 0 else (512.0 if (lt1024 & ~lt512)[sel].any() else 1024.0)
            hi_idx = 2048.0 if (~lt2048)[sel].any() else (1024.0 if (lt2048 & ~lt1024)[sel].any()
                                                          else 512.0)
            y_hi = np.interp(lo_idx, LERP1_X, LERP1_Y)
            y_lo = np.interp(hi_idx, LERP1_X, LERP1_Y)
            print(f"   => LIVE. The index sweeps roughly [{lo_idx:.0f}, {hi_idx:.0f}] counts, i.e. the")
            print(f"      0xD28DC coefficient swings about {y_hi:.0f} -> {y_lo:.0f} "
                  f"({y_hi / max(y_lo, 1):.2f}x) at ~2x the mode frequency.")
            print("      0xD28DC / 0xD2888 Y rows and the upstream EMA alpha 0xC63BA are live levers.")
            print("      *** Both still need GATE 2 -- they sit on the BASE ASSIST path, so they")
            print("         change manual feel, not just the LKAS lane.")

    print("\n-- IS THE SWEEP AT THE MODE FREQUENCY? bit5 toggle spectrum vs the bus angle rate --")
    segs = list(runs_of(sel, d["t"], NFFT))
    if not segs:
        print(f"   no contiguous run >= {NFFT} samples ({sel.sum()} frames). Cannot spectrum it.")
    else:
        x = np.concatenate([lt512[a:b].astype(float) for a, b in segs])
        y = np.concatenate([d["rate"][a:b] for a, b in segs])
        if x.std() == 0:
            print("   bit5 is CONSTANT over the selected runs -- no sweep at any frequency.")
            print("   (Consistent with INERT above; it is the same fact seen two ways.)")
        else:
            f, coh, ph, K = csd(x, y, fs)
            print(f"   {len(segs)} run(s), {len(x)} samples, K={K} (non-overlapping, nfft={NFFT})")
            for lo, hi in ((6, 9), (18, 26), (38, 46)):
                m = (f >= lo) & (f <= hi)
                j = int(np.argmax(np.where(m, coh, -np.inf)))
                print(f"      {f'{lo}-{hi}Hz':>9s} peak {f[j]:6.2f} Hz  coherence {coh[j]:.3f}  "
                      f"phase {ph[j]:+7.1f}d")
            print("   !! the RECTIFIED index should show at ~2x the mode (38-46 Hz band), with the")
            print("     18-26 Hz band carrying any asymmetry. 42 Hz is close to the 50 Hz Nyquist --")
            print("     treat its amplitude as indicative, its PRESENCE as the result.")

    print("\n-- CROSS-CHECK: does the index track the grinding envelope? --")
    if segs:
        env = np.concatenate([band_envelope(d["tq"][a:b], fs, 18, 26) for a, b in segs])
        lvl = np.concatenate([(3 - lt512[a:b].astype(int) - lt1024[a:b].astype(int)
                               - lt2048[a:b].astype(int)).astype(float) for a, b in segs])
        if lvl.std() == 0 or env.std() == 0:
            print("   one channel is constant -- no correlation available.")
        else:
            print(f"   corr(18-26 Hz envelope, thermometer level) = "
                  f"{np.corrcoef(env, lvl)[0, 1]:+.3f}  over {len(env)} frames")
            print("   (positive => the index climbs the curve exactly when the grinding is loud)")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
