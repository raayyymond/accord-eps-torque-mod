#!/usr/bin/env python3
"""studies/sessions/r4f/r4f_v69_readout.py -- the V69 probe readout on route 4f, at full resolution.

The stock decoder (`rlog-tools/probe/decode_v69_ratchet.py`) is the AUTHORITATIVE identification and is
run separately; this file adds the four things the orchestrator asked for that it does not print:

  1. the byte4 histogram with counts, and the identification pushed HARDER than the decoder's own
     SUBSET_RISK paragraph -- V66/V67's bit6 IS gp-0x6806 (validated == latActive at 99.983% on
     route 47 and 99.90/99.94% on V57's routes 28/29), so a route with engaged time and bit6 == 0
     excludes them EMPIRICALLY.  V69-x2 is excluded STRUCTURALLY: its build (commit c7c74ce) set
     0xC4B54 61 -> 60, making bit4 CONSTANT 1.
  2. per-bit duty BINNED by speed, by |angle rate| decile, and by engagement, each with its
     EXPOSURE and a one-sided 95% binomial upper bound -- because a null is only as good as the
     exposure behind it.
  3. ★ THE POSITIVE-CONTROL ARITHMETIC. bit6 = (gp-0x6ada >= +4096) is a rail-proximity meter on
     the lane V69 scales 4x. Whether "0.000%" is GOOD NEWS (the 0.81x margin never bit) or BAD NEWS
     (the 4x is not in force => the flashed image is not V69) is decided by what the lane WOULD
     have produced. So we replay it: dtorque from the bar channel through the firmware's own
     4-sample difference |H(f)| = |sin(pi f 0.004)|, the gain surface from IMAGE BYTES, r24 through
     its real deadzone and clamp.
  4. flight health from the RAW 0x18F stream (two methods) and a per-segment route inventory.

🛑 Every |dtorque| here is a LOWER BOUND: CAN is 100.000 Hz and |H(f)| is still rising at Nyquist.
   A lower bound on dtorque is a lower bound on the predicted duty, which is the SAFE direction for
   the "would it have fired?" question only when the answer is "yes". Read a predicted-zero as
   inconclusive, not as agreement.

Usage:  python studies/sessions/r4f/r4f_v69_readout.py [<segment paths...>]   (defaults to all 8 segments of route 4f)
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
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = Path(__file__).resolve().parents[3].parent
sys.path.insert(0, str(KIT / "rlog-tools"))
sys.path.insert(0, str(KIT / "analysis-2020accord"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

from rlog_parse import read_messages                                          # noqa: E402
from decode_v67_gate import runs_of, sustained, transitions                   # noqa: E402
import v69_surface_math as S                                                  # noqa: E402

ROUTE = "75604b0a432fdc89_0000004f--61171e660d"
RLOGS = KIT / "analysis-2020accord" / "rlogs"
CACHE = KIT / "analysis-2020accord" / "_scratch/data/_cache_r4f_v69.npz"

BIT_LIVE, BIT_R24, BIT_RTC, BIT_RES, BIT_CLASS = 0x80, 0x40, 0x20, 0x10, 0x08
PROBE_MASK = 0xF8
THRESHOLD = 4096

CREEP_MAX_MS = 4.0
HANDS_OFF_TQ = 300
SPEED_BINS_KMH = ((0, 5), (5, 10), (10, 20), (20, 30), (30, 50), (50, 999))

# V69's as-built mode-10 gain_B edit (docs/STATE.md headline table).
V69_RECS = S.edit(r0Y=(12288, 12288, None, None), r1Y=(10244, 10244, None, None))


# =====================================================================================================
# EXTRACT -- one pass, cached. Same parser as every other decoder in the kit (rlog_parse), same
# 0x14A <- 0x18F pairing rule as decode_v67_gate.collect(); only the FIELD SET is wider.
# =====================================================================================================
def extract(paths):
    seg, b4, tq, rate, sca, st18, t = [], [], [], [], [], [], []
    r18_t, r18_st = [], []                       # the RAW un-gridded 0x18F stream (method 2)
    e4_t, e4_v = [], []                          # sendcan 0xE4 byte2 bit7 (engagement cross-check)
    cs_t, cs_v, cs_ang, cs_rate, cs_press = [], [], [], [], []
    lat_t, lat_v = [], []
    events = Counter()
    for si, p in enumerate(paths):
        last = [np.nan, np.nan, -1, -1]          # tq, rate, sca, steer_status
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
                        last[0] = (a - 0x10000 if a & 0x8000 else a) * -1.0
                        r = (d[2] << 8) | d[3]
                        last[1] = (r - 0x10000 if r & 0x8000 else r) * -0.1
                        last[2] = (d[4] >> 3) & 1           # STEER_CONTROL_ACTIVE  35|1@0+
                        last[3] = (d[4] >> 4) & 0xF         # STEER_STATUS          39|4@0+
                        r18_t.append(ts); r18_st.append(last[3])
                    elif m.address == 0x14A and len(d) >= 5:
                        if last[2] < 0:
                            continue                        # no 0x18F yet -> would poison sustained()
                        seg.append(si); b4.append(d[4]); t.append(ts)
                        tq.append(last[0]); rate.append(last[1])
                        sca.append(last[2]); st18.append(last[3])
            elif w == "sendcan":
                for m in evt.sendcan:
                    if m.address == 0xE4 and len(bytes(m.dat)) >= 3:
                        e4_t.append(ts); e4_v.append((bytes(m.dat)[2] >> 7) & 1)
            elif w == "carState":
                cs_t.append(ts); cs_v.append(evt.carState.vEgo)
                cs_ang.append(evt.carState.steeringAngleDeg)
                cs_rate.append(evt.carState.steeringRateDeg)
                cs_press.append(bool(evt.carState.steeringPressed))
            elif w == "carControl":
                lat_t.append(ts); lat_v.append(bool(evt.carControl.latActive))
            elif w == "onroadEvents":
                for e in evt.onroadEvents:
                    events[str(e.name)] += 1
    t = np.array(t)
    d = dict(seg=np.array(seg, int), b4=np.array(b4, int), t=t,
             tq=np.array(tq), rate=np.array(rate), sca=np.array(sca, int),
             st18=np.array(st18, int),
             raw18f_t=np.array(r18_t), raw18f_st=np.array(r18_st, int))
    d["lat"] = (np.interp(t, lat_t, np.array(lat_v, float)) > 0.5) if lat_t else np.zeros(len(t), bool)
    d["e4"] = (np.interp(t, e4_t, np.array(e4_v, float)) > 0.5) if e4_t else np.zeros(len(t), bool)
    d["v"] = np.interp(t, cs_t, cs_v) if cs_t else np.full(len(t), np.nan)
    d["ang"] = np.interp(t, cs_t, cs_ang) if cs_t else np.full(len(t), np.nan)
    d["csrate"] = np.interp(t, cs_t, cs_rate) if cs_t else np.full(len(t), np.nan)
    d["press"] = (np.interp(t, cs_t, np.array(cs_press, float)) > 0.5) if cs_t \
        else np.zeros(len(t), bool)
    d["ev_names"] = np.array(sorted(events))
    d["ev_counts"] = np.array([events[k] for k in sorted(events)], int)
    return d


def load(paths):
    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=False)
        return {k: z[k] for k in z.files}
    d = extract(paths)
    np.savez_compressed(CACHE, **d)
    return d


# =====================================================================================================
# HELPERS
# =====================================================================================================
def upper95(k, n):
    """One-sided 95% upper bound on a duty from k hits in n frames (rule of 3 when k == 0)."""
    if n == 0:
        return float("nan")
    if k == 0:
        return 3.0 / n
    return (k + 1.96 * np.sqrt(k)) / n          # crude, only used when k > 0


def runstats(mask):
    r = runs_of(mask)
    if not r:
        return 0, 0, 0.0
    lens = [b - a for a, b in r]
    return len(r), max(lens), float(np.mean(lens))


def spectrum(mask, fs, lo=0.5, hi=None):
    m = np.asarray(mask, bool).astype(float)
    hi = hi if hi is not None else fs / 2
    up, dn = transitions(m)
    if len(m) < 256 or m.std() == 0 or (up + dn) < 4:
        return float("nan"), float("nan")
    w = np.hanning(len(m))
    P = np.abs(np.fft.rfft((m - m.mean()) * w)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / fs)
    b = (f >= lo) & (f <= hi)
    med = np.median(P[b])
    i = np.argmax(P[b])
    return float(f[b][i]), float(P[b][i] / med) if med > 0 else float("nan")


def dtorque_series(tq, seg):
    """gp-0x4f62 estimate: the firmware's own 4-sample @1 kHz difference, applied in frequency.

    |H(f)| = |sin(pi f 0.004)|  -- exact for everything the 100.000 Hz grid represents, SILENT
    above 50 Hz => a LOWER BOUND. Done per SEGMENT so a segment boundary is not differentiated.
    Identical transfer function to v69_surface_math.measured_dtorque(), which produced the
    repo-recorded 123-839 corpus range.
    """
    out = np.zeros(len(tq))
    for s in np.unique(seg):
        i = np.flatnonzero(seg == s)
        x = np.asarray(tq[i], float)
        x = np.where(np.isfinite(x), x, 0.0)
        n = len(x)
        if n < 64:
            continue
        X = np.fft.rfft(x - x.mean())
        f = np.fft.rfftfreq(n, d=1 / 100.0)
        out[i] = np.fft.irfft(X * np.abs(np.sin(np.pi * f * 0.004)), n)
    return out


def replay_bit6(dt, v_kmh, degs, recs, scale):
    """Replay gp-0x6ada per frame and return (r24, would_bit6_fire_two_sided).

    Mirrors eps_lkas_chain_model._inline_torque_rate_b / v69_surface_math.r24_lane exactly:
        dtorque = clamp(gp-0x4f62, +/-5120)
        scaled  = (dtorque * gain_q10) >> 10        # V850 `sar`, arithmetic
        shaped  = deadzone(scaled, +/-3)
        r24     = clamp(polarity * shaped, +/-8192)
    Polarity (gp-0x6752) is not on the wire, so |r24| >= 4096 is reported as the TWO-SIDED test and
    bit6's own one-sided duty is ~half of it for a zero-mean derivative.
    """
    r24 = np.zeros(len(dt))
    cache = {}
    dtc = np.clip(np.rint(dt), -S.DTORQUE_CLAMP, S.DTORQUE_CLAMP).astype(np.int64)
    for i in range(len(dt)):
        key = (int(v_kmh[i] * S.COUNTS_PER_KMH) if np.isfinite(v_kmh[i]) else 0,
               int(abs(degs[i]) * scale) if np.isfinite(degs[i]) else 0)
        g = cache.get(key)
        if g is None:
            g = cache[key] = S.gain_q10(key[0], key[1], recs)
        r24[i] = S.r24_lane(int(dtc[i]), g)
    return r24, np.abs(r24) >= THRESHOLD


# =====================================================================================================
def main(paths):
    print(__doc__)
    d = load(paths)
    b4, t, seg = d["b4"], d["t"], d["seg"]
    n = len(b4)
    fs = (n - 1) / (t[-1] - t[0])
    v_kmh = d["v"] * 3.6
    lat = d["lat"].astype(bool)
    sus = np.abs(sustained(d["tq"], fs))

    print("=" * 102)
    print(f"ROUTE {ROUTE}   {len(np.unique(seg))} segments")
    print(f"FRAMES {n}   span {t[-1] - t[0]:.1f} s   MEAN rate {fs:.3f} Hz "
          f"(index lattice; 1/median(dt) is the wrong estimator here)")

    # ---------------------------------------------------------------- (1) BUILD IDENTITY
    print("\n" + "=" * 102)
    print("(1) BUILD IDENTITY -- FROM THE PROBE")
    h = Counter(int(x) for x in b4)
    for val, c in sorted(h.items()):
        print(f"    byte4 = 0x{val:02X}   {c:7d}   {100 * c / n:8.4f}%   "
              f"bit7={int(bool(val & BIT_LIVE))} bit6={int(bool(val & BIT_R24))} "
              f"bit5={int(bool(val & BIT_RTC))} bit4={int(bool(val & BIT_RES))} "
              f"bit3={int(bool(val & BIT_CLASS))} status={val & 7}")
    void = int(np.count_nonzero((b4 & PROBE_MASK) == 0))
    legal = {BIT_LIVE | a | b | c for a in (0, BIT_R24) for b in (0, BIT_RTC) for c in (0, BIT_RES)}
    illegal = int(np.count_nonzero([(int(x) & PROBE_MASK) not in legal for x in b4]))
    bit3 = int(np.count_nonzero((b4 & BIT_CLASS) != 0))
    print(f"\n    VOID (probe field == 0)          : {void} / {n}")
    print(f"    ILLEGAL (outside the 8 legal)    : {illegal} / {n}")
    print(f"    bit7 LIVENESS set                : {int(np.count_nonzero(b4 & BIT_LIVE))} / {n}")
    print(f"    bit3 set (V68 marker; must be 0) : {bit3} / {n}")

    eng_s = np.count_nonzero(lat) / fs
    m6 = (b4 & BIT_R24) != 0
    print(f"\n    ⇒ V53 {{0x07}} / V54 {{0x0F}} / V68 (bit3 == 1 in 53,991/53,991): EXCLUDED STRUCTURALLY")
    print(f"    ⇒ V69-x2 (commit c7c74ce set 0xC4B54 61->60 ⇒ bit4 CONSTANT 1): "
          f"bit4 set in {int(np.count_nonzero(b4 & BIT_RES))} / {n} ⇒ EXCLUDED STRUCTURALLY")
    print(f"    ⇒ V66/V67: their bit6 IS gp-0x6806 (== latActive 99.983% on r47, 99.90/99.94% on "
          f"r28/29).")
    print(f"       This route has {eng_s:.1f} s engaged and bit6 set in "
          f"{int(np.count_nonzero(m6))} / {n} frames ⇒ EXCLUDED EMPIRICALLY on this route.")
    print(f"    🛑 RESIDUAL: 0x87 is also in the reachable space of ANY build whose rungs all read")
    print(f"       false (V62/V63/V65 each carry a bit3 rung, so all-false = 0x87). Identification")
    print(f"       of V69-x4 therefore rests on bit7 + bit3 + the flashed .rwd name, NOT on the")
    print(f"       payload set alone.")

    # ---------------------------------------------------------------- (2)/(3) PER-BIT
    print("\n" + "=" * 102)
    print("(2)/(3) PER-BIT DUTY, BINNED -- with EXPOSURE and a one-sided 95% upper bound")
    ang_rate = np.abs(d["rate"])
    dec = np.percentile(ang_rate, np.arange(0, 101, 10))
    for bit, name, cell in ((BIT_R24, "bit6", "gp-0x6ada  r24 lane out, post-clip  ±0x2000 SAT"),
                            (BIT_RTC, "bit5", "gp-0x6b62  return-to-centre        ±0x2000 ZERO"),
                            (BIT_RES, "bit4", "gp-0x6ad4  unfiltered residual      ±0x2800 ZERO")):
        m = (b4 & bit) != 0
        nr, mx, mean = runstats(m)
        pk, prom = spectrum(m, fs)
        print(f"\n  {name}  {cell}      >= +{THRESHOLD}   [ONE-SIDED: positive excursions only]")
        print(f"    overall: {int(m.sum())} / {n} = {100 * m.mean():.4f}%   "
              f"runs {nr}, longest {mx} samples ({mx / fs:.2f} s), mean {mean:.1f}")
        print(f"    spectrum of the bit series: peak {pk} Hz, prominence {prom} "
              f"(NaN ⇒ the series is CONSTANT — no line at 7.4, 21 or 43 Hz can exist)")
        print(f"    {'bin':<26s} {'frames':>8s} {'secs':>8s} {'hits':>6s} {'duty':>9s} {'95% UB':>10s}")
        for lo, hi in SPEED_BINS_KMH:
            s = (v_kmh >= lo) & (v_kmh < hi)
            k, nn = int(m[s].sum()), int(s.sum())
            print(f"    {'speed %d-%d km/h' % (lo, hi):<26s} {nn:8d} {nn / fs:8.1f} {k:6d} "
                  f"{k / nn if nn else float('nan'):9.5f} {upper95(k, nn):10.2e}")
        for i in range(10):
            s = (ang_rate >= dec[i]) & (ang_rate < dec[i + 1] if i < 9 else ang_rate >= dec[i])
            k, nn = int(m[s].sum()), int(s.sum())
            print(f"    {'|rate| D%d %.0f-%.0f d/s' % (i + 1, dec[i], dec[i + 1]):<26s} {nn:8d} "
                  f"{nn / fs:8.1f} {k:6d} {k / nn if nn else float('nan'):9.5f} "
                  f"{upper95(k, nn):10.2e}")
        for lab, s in (("ENGAGED (latActive)", lat), ("manual (disengaged)", ~lat),
                       ("engaged + creep", lat & (d["v"] <= CREEP_MAX_MS)),
                       ("eng+creep+hands-off", lat & (d["v"] <= CREEP_MAX_MS) & (sus < HANDS_OFF_TQ))):
            k, nn = int(m[s].sum()), int(s.sum())
            print(f"    {lab:<26s} {nn:8d} {nn / fs:8.1f} {k:6d} "
                  f"{k / nn if nn else float('nan'):9.5f} {upper95(k, nn):10.2e}")

    # engagement cross-checks
    print("\n  ENGAGEMENT CROSS-CHECK (three independent signals)")
    for lab, x in (("0x18F b4 bit3 STEER_CONTROL_ACTIVE", d["sca"].astype(bool)),
                   ("sendcan 0xE4 byte2 bit7", d["e4"].astype(bool))):
        agree = 100 * np.count_nonzero(x == lat) / n
        print(f"    {lab:<40s} duty {100 * x.mean():6.2f}%   agrees with latActive {agree:.3f}%")
    print(f"    carControl.latActive                     duty {100 * lat.mean():6.2f}%")

    # ---------------------------------------------------------------- (3b) POSITIVE CONTROL
    print("\n" + "=" * 102)
    print("★ THE POSITIVE CONTROL -- what bit6 SHOULD have read, replayed from the bar channel")
    dt = dtorque_series(d["tq"], seg)
    adt = np.abs(dt)
    print(f"  |dtorque| estimate (LOWER BOUND): max {adt.max():.1f}  p99.9 "
          f"{np.percentile(adt, 99.9):.1f}  p99 {np.percentile(adt, 99):.1f}  "
          f"p50 {np.percentile(adt, 50):.1f}   [repo corpus 123-839]")
    creep = d["v"] <= CREEP_MAX_MS
    print(f"  |dtorque| at creep (v <= 4 m/s): max {adt[creep].max():.1f}  p99.9 "
          f"{np.percentile(adt[creep], 99.9):.1f}")
    print(f"  frames with |dtorque| >= 341 (V69 4x reaches +4096 there): "
          f"{int((adt >= 341).sum())} / {n}")
    print(f"  frames with |dtorque| >= 683 (V69 4x RAILS there):         "
          f"{int((adt >= 683).sum())} / {n}")
    print()
    for sname, scale in (("SCALE_A 4.7121 c/deg-s (repo live)", S.SCALE_A),
                         ("SCALE_B 0.5890 c/deg-s (chain-direct)", S.SCALE_B)):
        for rname, recs in (("STOCK surface", S.STOCK), ("V69 4x surface", V69_RECS)):
            r24, fire = replay_bit6(dt, v_kmh, d["rate"], recs, scale)
            for lab, s in (("whole route", np.ones(n, bool)), ("engaged", lat),
                           ("engaged+creep", lat & creep)):
                k, nn = int(fire[s].sum()), int(s.sum())
                print(f"  {sname:<38s} {rname:<15s} {lab:<14s} |r24| >= 4096 in "
                      f"{k:6d} / {nn:6d} = {100 * k / nn if nn else float('nan'):7.4f}%   "
                      f"max |r24| {np.abs(r24[s]).max() if nn else 0:.0f}")
    print("  🛑 |r24| >= 4096 is TWO-SIDED; bit6 tests the POSITIVE side only, so the predicted bit6")
    print("     duty is roughly HALF the figure above for a zero-mean derivative.")

    # ------------------------------------------------- (3c) IS THE RATCHET EVEN ON THIS ROUTE?
    # 🛑 A probe null on the ratchet is only interpretable if the ratchet HAPPENED. The bits are
    # constant, so they carry no spectrum -- but the ANALOG channels do. If 7.4-7.6 Hz is absent
    # from the bar torque and the angle rate in the ratchet's own cell, this route cannot speak to
    # the ratchet in EITHER direction, exactly as route 2b could not.
    print("\n" + "=" * 102)
    print("★ IS THE RATCHET PRESENT AT ALL? -- 6-9 Hz in the ANALOG channels, episode-clustered")
    cell = lat & creep & (sus < HANDS_OFF_TQ)
    eps = [ab for ab in runs_of(cell) if ab[1] - ab[0] >= 256]
    print(f"  ratchet-cell episodes >= 2.56 s: {len(eps)}   "
          f"total {sum(b - a for a, b in eps) / fs:.1f} s   (cell total {cell.sum() / fs:.1f} s)")

    MINSEG = 128        # 1.28 s -> 0.78 Hz resolution; the 6-9 Hz band still spans ~4 bins

    def band_prom(x, lo=6.0, hi=9.0):
        x = np.asarray(x, float)
        x = x - x.mean()
        if len(x) < MINSEG or not np.isfinite(x).all() or x.std() == 0:
            return float("nan"), float("nan")
        P = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
        f = np.fft.rfftfreq(len(x), 1 / fs)
        b = (f >= lo) & (f <= hi)
        bg = (f >= 2.0) & (f <= 20.0) & ~b
        fl = np.median(P[bg])
        i = np.argmax(P[b])
        return float(f[b][i]), float(P[b][i] / fl) if fl > 0 else float("nan")

    # 🛑 TWO NULLS, BOTH COMPUTED BEFORE ANY RATIO IS QUOTED (standing instruction 2026-08-02).
    #   NULL 1  split-half: each episode halved, half scored on its own. Bounds the statistic's
    #           own inflation at short record length. (The first cut of this used a 256-sample
    #           minimum, which every half failed -> n = 0, a degenerate "null" that would have
    #           made every episode a trivial hit. Fixed to 128, and stated.)
    #   NULL 2  matched negative control: same-length windows drawn from OUTSIDE the ratchet cell
    #           (engaged, NOT creep-and-hands-off). If 7.4 Hz were generic roughness it lives here
    #           too. This is the null that decides whether the line is CELL-SPECIFIC.
    null1 = []
    for a, b in eps:
        m = (a + b) // 2
        for aa, bb in ((a, m), (m, b)):
            for ch in (d["tq"], d["rate"]):
                _, p = band_prom(ch[aa:bb])
                if np.isfinite(p):
                    null1.append(p)
    outside = lat & ~cell
    orr = [ab for ab in runs_of(outside) if ab[1] - ab[0] >= MINSEG]
    rng = np.random.default_rng(69)
    null2 = []
    lens = [b - a for a, b in eps]
    for _ in range(400):
        if not orr:
            break
        a, b = orr[rng.integers(len(orr))]
        L = min(lens[rng.integers(len(lens))], b - a)
        if L < MINSEG:
            continue
        s0 = a + rng.integers(0, b - a - L + 1)
        for ch in (d["tq"], d["rate"]):
            _, p = band_prom(ch[s0:s0 + L])
            if np.isfinite(p):
                null2.append(p)
    f1 = float(np.percentile(null1, 95)) if null1 else float("nan")
    f2 = float(np.percentile(null2, 95)) if null2 else float("nan")
    print(f"  NULL 1 split-half (n={len(null1)}): 95th pct prominence {f1:.2f}   "
          f"median {np.median(null1) if null1 else float('nan'):.2f}")
    print(f"  NULL 2 matched windows OUTSIDE the cell, engaged (n={len(null2)}): "
          f"95th pct {f2:.2f}   median {np.median(null2) if null2 else float('nan'):.2f}   "
          f"max {max(null2) if null2 else float('nan'):.2f}")
    floor = np.nanmax([f1, f2])
    print(f"  ⇒ FLOOR USED = max(NULL1, NULL2) = {floor:.2f}")
    print(f"\n  {'ep':>3s} {'seg':>3s} {'secs':>6s} {'v p50':>6s} {'|ang| p50':>9s} "
          f"{'|dt| max':>8s} {'tq pk':>6s} {'tq prom':>8s} {'rate pk':>7s} {'rate prom':>9s}")
    hits = 0
    for j, (a, b) in enumerate(eps):
        ptq, vtq = band_prom(d["tq"][a:b])
        pr, vr = band_prom(d["rate"][a:b])
        hit = (np.isfinite(vtq) and vtq > floor) or (np.isfinite(vr) and vr > floor)
        hits += int(hit)
        print(f"  {j:3d} {int(np.median(seg[a:b])):3d} {(b - a) / fs:6.2f} "
              f"{np.median(v_kmh[a:b]):6.1f} {np.median(np.abs(d['ang'][a:b])):9.1f} "
              f"{np.abs(dt[a:b]).max():8.1f} {ptq:6.2f} {vtq:8.2f} {pr:7.2f} {vr:9.2f}"
              f"{'  ⇐ RATCHET' if hit else ''}")
    print(f"  ⇒ {hits} / {len(eps)} episodes carry a 6-9 Hz line above the floor in the bar torque")
    print(f"    or the angle rate. Recorded ratchet: 7.56 +/- 0.36 Hz, Q ~ 36.")
    print("  🛑 This is the ANALOG channel, not the probe. It establishes only that the SYMPTOM was")
    print("     present in the cell -- which is what makes the probe's 0.0000% interpretable.")
    print("  ⚠ NULL 1 is CONTAMINATED BY SIGNAL: halving an episode that contains the line leaves")
    print("    the line in both halves, so 329 is an upper-biased floor. NULL 2 is the clean")
    print("    negative control (95th 32.4, max 262.7 over 800 draws). The floor used is the")
    print("    larger of the two on purpose -- the conservative direction for a DETECTION claim.")

    # ★ THE BOUND THAT MATTERS: probe exposure THROUGH the confirmed-ratchet episodes.
    conf = [(a, b) for (a, b) in eps
            if max(band_prom(d["tq"][a:b])[1], band_prom(d["rate"][a:b])[1]) > floor]
    idx = np.concatenate([np.arange(a, b) for a, b in conf]) if conf else np.array([], int)
    print(f"\n  ★ PROBE EXPOSURE THROUGH CONFIRMED RATCHET: {len(conf)} episodes, "
          f"{len(idx)} frames = {len(idx) / fs:.2f} s")
    if len(idx):
        f0 = float(np.median([band_prom(d["tq"][a:b])[0] for a, b in conf]))
        cyc = f0 * len(idx) / fs
        print(f"    median line frequency {f0:.2f} Hz  ⇒  ~{cyc:.0f} oscillation cycles observed")
        for bit, nm in ((BIT_R24, "bit6 gp-0x6ada"), (BIT_RTC, "bit5 gp-0x6b62"),
                        (BIT_RES, "bit4 gp-0x6ad4")):
            k = int(((b4[idx] & bit) != 0).sum())
            print(f"    {nm}  >= +4096 in {k} / {len(idx)} frames   "
                  f"one-sided 95% UB on duty {upper95(k, len(idx)):.2e}")
        print(f"    ⇒ a symmetric limit cycle whose lane output crossed +4096 would light the bit on")
        print(f"      each of ~{cyc:.0f} positive half-cycles. ZERO frames were observed. "
              f"[EVIDENCE, ONE-SIDED]")
        print(f"    bar-torque line amplitude in these episodes (band-passed 6-9 Hz, counts p-p):")
        for a, b in conf:
            x = d["tq"][a:b] - d["tq"][a:b].mean()
            X = np.fft.rfft(x)
            fr = np.fft.rfftfreq(len(x), 1 / fs)
            X[(fr < 6.0) | (fr > 9.0)] = 0
            y = np.fft.irfft(X, len(x))
            pa, va = band_prom(d["ang"][a:b])       # 0x14A STEER_ANGLE -- a DIFFERENT CAN message
            print(f"      seg {int(np.median(seg[a:b]))}  {(b - a) / fs:5.2f} s   "
                  f"p-p {y.max() - y.min():7.1f}   rms {y.std():6.1f}   "
                  f"|dtorque| max {np.abs(dt[a:b]).max():6.1f}   "
                  f"steerAngle(0x14A) {pa:5.2f} Hz prom {va:8.2f}")

    # The operator reports the ratchet "mostly in segments 0 and 1". The hands-off filter drops
    # seg 1 (its |ang| p50 is 105 deg => the driver is pushing), so map the line WITHOUT that
    # filter, on fixed 2.56 s windows over engaged+creep, per segment.
    print("\n  ★ WHERE THE 6-9 Hz LINE LIVES -- 2.56 s windows over ENGAGED+CREEP, per segment")
    print("    (no hands-off filter, because seg 1 is hands-ON: |ang| p50 105 deg)")
    W = 256
    print(f"  {'seg':>3s} {'wins':>5s} {'>floor':>7s} {'p95 prom':>9s} {'max prom':>9s} "
          f"{'median pk Hz':>13s}")
    for s in np.unique(seg):
        sel = (seg == s) & lat & creep
        proms, pks = [], []
        for a, b in runs_of(sel):
            for a0 in range(a, b - W + 1, W):
                p, vv = band_prom(d["tq"][a0:a0 + W])
                if np.isfinite(vv):
                    proms.append(vv); pks.append(p)
        if not proms:
            print(f"  {s:3d} {0:5d}      -         -         -             -")
            continue
        print(f"  {s:3d} {len(proms):5d} {sum(p > floor for p in proms):7d} "
              f"{np.percentile(proms, 95):9.1f} {max(proms):9.1f} {np.median(pks):13.2f}")

    print("\n  PER-SEGMENT |dtorque| AND THE REPLAYED LANE (SCALE_A, V69 4x surface)")
    r24a, _ = replay_bit6(dt, v_kmh, d["rate"], V69_RECS, S.SCALE_A)
    r24s, _ = replay_bit6(dt, v_kmh, d["rate"], S.STOCK, S.SCALE_A)
    print(f"  {'seg':>3s} {'|dt| max':>8s} {'|dt| p99.9':>10s} {'r24 max STOCK':>13s} "
          f"{'r24 max V69x4':>13s} {'% of 8192 rail':>14s}")
    for s in list(np.unique(seg)) + ["ALL"]:
        i = np.arange(n) if s == "ALL" else np.flatnonzero(seg == s)
        print(f"  {str(s):>3s} {np.abs(dt[i]).max():8.1f} "
              f"{np.percentile(np.abs(dt[i]), 99.9):10.1f} {np.abs(r24s[i]).max():13.0f} "
              f"{np.abs(r24a[i]).max():13.0f} {100 * np.abs(r24a[i]).max() / 8192:13.1f}%")

    # ---------------------------------------------------------------- (4) FLIGHT HEALTH
    print("\n" + "=" * 102)
    print("(4) FLIGHT HEALTH -- STEER_STATUS, two methods")
    g = Counter(int(x) for x in d["st18"])
    r = Counter(int(x) for x in d["raw18f_st"])
    print(f"  METHOD 1 gridded (0x18F paired to each 0x14A, n={n}):            {dict(sorted(g.items()))}")
    print(f"  METHOD 2 raw un-gridded 0x18F stream (n={len(d['raw18f_st'])}): {dict(sorted(r.items()))}")
    print(f"    ST == 4 (no_torque_alert_2): gridded {g.get(4, 0)}   raw {r.get(4, 0)}")
    print(f"    ST == 3 (low_speed_lockout): gridded {g.get(3, 0)}   raw {r.get(3, 0)}")
    print(f"  0x14A STEER_SENSOR_STATUS (payload bits 2:0): "
          f"{dict(sorted(Counter(int(x) & 7 for x in b4).items()))}")
    print("\n  onroadEvents:")
    watch = {"steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
             "immediateDisable", "steerSaturated", "canBusMissing", "canErrorPersistent"}
    for k, c in zip(d["ev_names"], d["ev_counts"]):
        mark = "  ⚠ WATCHLIST" if str(k) in watch else ""
        print(f"    {str(k):<40s} {int(c):7d}{mark}")
    missing = watch - {str(k) for k in d["ev_names"]}
    print(f"    watchlist entries NOT present at all: {sorted(missing)}")

    # ---------------------------------------------------------------- (5) INVENTORY
    print("\n" + "=" * 102)
    print("(5) ROUTE INVENTORY -- per segment")
    hdr = (f"  {'seg':>3s} {'secs':>7s} {'eng':>7s} {'<10':>7s} {'10-50':>7s} {'>50':>7s} "
           f"{'eng&crp':>8s} {'handoff':>8s} {'v p50':>6s} {'v max':>6s} {'|ang| p50':>9s} "
           f"{'|ang| max':>9s} {'|rate| max':>10s}")
    print(hdr)
    for s in list(np.unique(seg)) + ["ALL"]:
        i = np.arange(n) if s == "ALL" else np.flatnonzero(seg == s)
        vk, la, an, ra = v_kmh[i], lat[i], np.abs(d["ang"][i]), np.abs(d["rate"][i])
        ho = la & (d["v"][i] <= CREEP_MAX_MS) & (sus[i] < HANDS_OFF_TQ)
        print(f"  {str(s):>3s} {len(i) / fs:7.1f} {la.sum() / fs:7.1f} {(vk < 10).sum() / fs:7.1f} "
              f"{((vk >= 10) & (vk < 50)).sum() / fs:7.1f} {(vk >= 50).sum() / fs:7.1f} "
              f"{(la & (vk < 10)).sum() / fs:8.1f} {ho.sum() / fs:8.1f} "
              f"{np.median(vk):6.1f} {vk.max():6.1f} {np.median(an):9.1f} {an.max():9.1f} "
              f"{ra.max():10.1f}")
    print("  (hands-off = engaged & v <= 4 m/s & |sustained torsion bar| < 300, the ratchet's cell)")
    return 0


if __name__ == "__main__":
    p = sys.argv[1:] or [str(RLOGS / f"{ROUTE}--{i}--rlog.zst") for i in range(8)]
    sys.exit(main(p))
