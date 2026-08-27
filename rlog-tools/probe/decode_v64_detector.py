#!/usr/bin/env python3
"""probe/decode_v64_detector.py -- read V64's reversal-detector probe out of an rlog.

V64 packs FIVE bits into CAN 330 (0x14A) byte4 at 100 Hz:

    bit 7 = 1                    LIVENESS (constant; 0 => the cave did not fire)
    bit 6 = gp-0x671a >= 5       *** V63'S ARM IS SELECTED. The decisive bit. ***
    bit 5 = gp-0x671a != 0       the latched reversal counter is nonzero
    bit 4 = gp-0x67df != 0       the FSM has LEFT NEUTRAL, i.e. |gp-0x6c2c| crossed +/-12800
    bit 3 = gp-0x671d != 0       r24's HIGHER-PRIORITY override is active (r24 takes 0xC6442)
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

*** field = (byte4 >> 3) & 0x1F.  field == 0 means THE CAVE DID NOT FIRE -- a VOID reading, not
"everything false". Bit 7 is hard-wired 1 precisely so this tool can say that.

THE QUESTION THIS ANSWERS
-------------------------------------------------------------------------------------------------------
V63 raises only the arms the firmware selects when `gp-0x671a >= CEIL`:
    0xC6440  2048 -> 4096   (r24)      0xC643E  1536 -> 3072   (r26)
A null V63 drive is uninterpretable on its own -- "the detector never tripped" and "the damping rise
was too small" look identical from the driver's seat. bit6 separates them, and bit4/bit3 say which knob
to turn next:

    bit6 ever set              -> the arm IS selected; a null means the rise was too small.
                                  Next: raise 0xC6440/0xC643E further, or fly V62 (unconditional).
    bit6 never set, bit4 set   -> the input crosses T but never latches to CEIL => lower CEIL 0xC64FA.
    bit6 never set, bit4 clear -> |gp-0x6c2c| never crosses T at all            => lower T   0xC620A.
    bit3 set                   -> r24 is on 0xC6442, so V63's 0xC6440 raise does nothing for r24;
                                  raise 0xC6442 too. (r26's chain is clean -- gate_683c is dead.)

🛑 gp-0x671a IS A ONE-WAY LATCH, NOT A PER-TICK FLAG -- READ THIS BEFORE READING ANY NUMBER BELOW
-------------------------------------------------------------------------------------------------------
From FUN_000428d4's output stage (0x429A0-0x42A12), byte-verified:
  * once the held value reaches CEIL, `cmp r8,r6 / bh` @0x429DE stops firing and the output is
    re-pinned to CEIL every tick;
  * the ONLY way down is the gp-0x6a88 timer draining tp+0x7270 = 5000 ticks = 5 s, which requires
    `gp-0x6a5e >= 640` AND revcount == 0 throughout;
  * at creep, `gp-0x6a5e < 640` takes the RELOAD path every tick, so *** THE LATCH NEVER CLEARS
    WITHIN A LOW-SPEED SEGMENT. ***

Consequences for reading this log, both of which this tool is built around:
  1. bit6 OCCUPANCY is nearly worthless once it first sets -- it will read ~100%. The informative
     numbers are TIME-TO-FIRST-SET and WHETHER IT EVER CLEARS. Those lead the report.
     Occupancy is still printed, because occupancy == 0 is the decisive NULL.
  2. bit6 => bit5 is STRUCTURAL (same register, same tick, CEIL = 5 > 0) -- a violation is a DECODE
     ERROR and this tool HARD-STOPS above 1%.  *** bit5 => bit4 IS NOT AN INVARIANT. *** The latch
     outlives the FSM's return to neutral (dwell > HYST = 50 ticks vs a 5 s hold), so bit5 & ~bit4 is
     the ordinary TAIL of every burst. It is reported as a measurement, never rejected.

🛑 START THE LOG BEFORE THE FIRST ENGAGEMENT. The latch fires exactly once per low-speed segment.

🛑 CONVENTIONS THIS TOOL ENFORCES -- all three established the hard way on the V57/V58 drives:
  1. ENGAGEMENT is LATERAL: carControl.latActive / 0x18F byte4 bit3 (STEER_CONTROL_ACTIVE).
     carState.cruiseState.enabled is LONGITUDINAL+LATERAL and reads 0.00% on parking-lot routes while
     lateral is really applying. Using it flipped V57's headline verdict.
  2. HANDS-OFF is SUSTAINED effort |lowpass(tq, 3 Hz)| <= 200, never raw |tq| <= 200.
  3. Bursty limit cycle => report ENVELOPE p99/max, never mean Welch power.

⚠ The grinding is CREEP-ONLY (prominence 141x/138x/518x at 1-4 m/s vs 7-11x above 6 m/s), so the
headline is conditioned on v <= 5 m/s. ⚠ 100 Hz sampling of a ~21 Hz phenomenon: every frequency is
indistinguishable from its alias. Same limitation every probe in this kit has had.

Usage:  python probe/decode_v64_detector.py RLOG [RLOG ...]
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1]))
from rlog_parse import read_messages  # noqa: E402

BIT_LIVE, BIT_ARMED, BIT_COUNTING, BIT_FSM, BIT_OVERRIDE = 0x80, 0x40, 0x20, 0x10, 0x08

CEIL = 5            # cal 0xC64FA, BYTE -- the threshold the cave hardcodes
T_THRESH = 12800    # cal 0xC620A -- the reversal threshold on gp-0x6c2c
HYST = 50           # cal 0xC64DD, BYTE, ticks at 1 kHz
HOLD = 5000         # cal 0xC6270 -- the latch hold, ticks at 1 kHz


def collect(paths):
    """Pair each 0x14A probe frame with the most recent 0x18F frame (both ~100 Hz on src 1)."""
    b4, rate, tq, sca, t = [], [], [], [], []
    last_rate, last_tq, last_sca = np.nan, np.nan, -1
    lat_t, lat_v, v_t, v_v, g_t, g_v = [], [], [], [], [], []
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
                try:
                    g_t.append(ts); g_v.append(str(evt.carState.gearShifter) == "reverse")
                except Exception:
                    pass
    d = dict(b4=np.array(b4, int), rate=np.array(rate), tq=np.array(tq),
             sca=np.array(sca, int), t=np.array(t))
    d["lat"] = (np.interp(d["t"], lat_t, np.array(lat_v, float)) > 0.5) if lat_t \
        else np.zeros_like(d["t"], bool)
    d["v"] = np.interp(d["t"], v_t, v_v) if v_t else np.full_like(d["t"], np.nan)
    d["rev"] = (np.interp(d["t"], g_t, np.array(g_v, float)) > 0.5) if g_t \
        else np.zeros_like(d["t"], bool)
    d["has_gear"] = bool(g_t)
    return d


def sustained(x, fs, fc=3.0):
    """Zero-phase lowpass -> the DRIVER's actual push, with the oscillation removed.

    ⚠ Compute over the SUBSET you intend to analyse, and guard the input: it is NaN-fragile by
    construction (one NaN in, all NaN out).
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


def transitions(mask):
    """(rising, falling) counts for a boolean series."""
    m = np.asarray(mask, bool).astype(int)
    if len(m) < 2:
        return 0, 0
    d = np.diff(m)
    return int((d > 0).sum()), int((d < 0).sum())


def longest_run(mask):
    """Longest contiguous True run, in samples."""
    m = np.asarray(mask, bool)
    best = cur = 0
    for v in m:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def report(tag, d):
    n = len(d["b4"])
    if n == 0:
        print(f"{tag}: no CAN 0x14A frames on src 1")
        return
    fs = 1.0 / np.median(np.diff(d["t"]))
    field = (d["b4"] >> 3) & 0x1F
    dur = d["t"][-1] - d["t"][0]
    print(f"\n{'=' * 92}\n{tag}   {n} frames  {dur:.1f}s  fs={fs:.2f} Hz")

    # ---- LIVENESS ---------------------------------------------------------------------------------
    void = field == 0
    print("\n-- LIVENESS --")
    print(f"   field == 0 (CAVE DID NOT FIRE) : {void.sum()} / {n}  ({100 * void.mean():.2f}%)")
    print(f"   bit7 set                       : {(d['b4'] & BIT_LIVE != 0).sum()} / {n}")
    if void.all():
        print("\n   *** THE CAVE NEVER FIRED. Every reading below is VOID. Stop here.")
        return
    print("   byte4 histogram: " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(d["b4"].tolist()).most_common(8)))

    armed = (d["b4"] & BIT_ARMED) != 0
    counting = (d["b4"] & BIT_COUNTING) != 0
    fsm = (d["b4"] & BIT_FSM) != 0
    override = (d["b4"] & BIT_OVERRIDE) != 0

    # ---- STRUCTURAL INTEGRITY ---------------------------------------------------------------------
    # ONLY bit6 => bit5. It is guaranteed by the cave itself: both bits read the SAME register in the
    # SAME tick and CEIL = 5 > 0. bit5 => bit4 is NOT an invariant (the latch tail) and is measured,
    # not enforced -- enforcing it would abort on perfectly good data.
    bad = armed & ~counting
    print("\n-- STRUCTURAL INTEGRITY (bit6 => bit5 only; bit5 => bit4 is NOT an invariant) --")
    print(f"   bit6 & ~bit5 (impossible)  : {bad.sum()} / {n}  ({100 * bad.mean():.3f}%)")
    # 🛑 HARD STOP, not a filter. A few stray frames are noise; a large fraction means these are not
    # V64 readings at all, and the surviving subset would still decode into plausible-looking numbers.
    # Reporting a verdict on it is exactly the failure mode this kit keeps hitting.
    if bad.mean() > 0.01:
        print("   *** STOP. Above 1% structurally impossible, these frames are NOT V64 readings.")
        print("       Almost certainly a different build is on the car. No verdict is computed:")
        print("       the surviving subset would still look plausible.")
        print(f"       byte4 values seen: {sorted(set(d['b4'].tolist()))}")
        return
    ok = ~bad
    if bad.any():
        print("   (excluded from everything below rather than averaged in)")
    # V59's byte4 is a THERMOMETER (bit5 => bit4 => bit3) and passes the check above, so it cannot be
    # ruled out by structure alone. Say so rather than silently assuming the right build is on the car.
    therm = ((~counting) | fsm) & ((~fsm) | override)
    print(f"   also consistent with V59's thermometer (bit5=>bit4=>bit3): "
          f"{100 * therm[ok].mean():.2f}% of frames")
    if therm[ok].mean() > 0.999:
        print("   !! 100% thermometer-consistent. V64 and V59 are INDISTINGUISHABLE on this log --")
        print("      under V64 the latch tail (bit5 & ~bit4) should be common. CONFIRM which .rwd is")
        print("      flashed before trusting the verdict.")

    # ---- SUBSETS ----------------------------------------------------------------------------------
    sus = sustained(d["tq"], fs)
    hands_off = sus <= 200
    creep = d["v"] <= 5.0
    eng = d["sca"] == 1
    print("\n-- ENGAGEMENT / SUBSET (cruiseState is long+lat: NOT used) --")
    print(f"   latActive               : {d['lat'].sum():6d} ({100 * d['lat'].mean():5.2f}%)")
    print(f"   STEER_CONTROL_ACTIVE==1 : {eng.sum():6d} ({100 * eng.mean():5.2f}%)  <- the subset")
    print(f"   agreement latActive vs SCA : {100 * (d['lat'] == eng).mean():.2f}%")
    print(f"   hands-off by SUSTAINED effort: {hands_off.sum()} "
          f"| by raw |tq|<=200: {(np.abs(d['tq']) <= 200).sum()}  <- raw discards the oscillation")
    print(f"   creep (v <= 5 m/s)      : {creep.sum()}")
    if d["has_gear"]:
        print(f"   REVERSE gear            : {d['rev'].sum()}")
    else:
        print("   REVERSE gear            : carState.gearShifter absent from this log -- the reverse")
        print("                             split below is EMPTY, not zero. Do not read it as a null.")

    # ---- THE LATCH: the numbers that actually carry information ------------------------------------
    print("\n-- THE LATCH (gp-0x671a is ONE-WAY at creep; these lead, not occupancy) --")
    idx = np.flatnonzero(armed & ok)
    if len(idx) == 0:
        print("   bit6 NEVER SET anywhere in this log.")
    else:
        first = idx[0]
        print(f"   first bit6 set at t+{d['t'][first] - d['t'][0]:.2f}s "
              f"(frame {first}/{n}), v={d['v'][first]:.2f} m/s, SCA={d['sca'][first]}")
        eng_idx = np.flatnonzero(eng)
        if len(eng_idx):
            lag = d["t"][first] - d["t"][eng_idx[0]]
            print(f"   first LATERAL engagement at t+{d['t'][eng_idx[0]] - d['t'][0]:.2f}s "
                  f"=> latency to arm = {lag:+.2f}s")
            if lag < 0:
                print("   !! bit6 was ALREADY SET before the first engagement in this log. The latch")
                print("      survives from an earlier segment -- time-to-first-set is NOT measured here.")
                print("      Re-drive with the log started before the first engagement.")
        rise, fall = transitions(armed[ok])
        print(f"   bit6 transitions: {rise} rising, {fall} falling   "
              f"longest continuous run {longest_run(armed[ok]) / fs:.1f}s")
        if fall == 0:
            print("   => bit6 NEVER CLEARS, exactly as the one-way latch predicts. V63's arm is")
            print("      selected CONTINUOUSLY from that moment on, including during manual steering.")
        else:
            print(f"   => bit6 clears {fall}x. That needs {HOLD} ticks ({HOLD / 1000:.0f}s) of")
            print("      gp-0x6a5e >= 640 with no reversals, i.e. sustained above-creep speed.")
    rise5, fall5 = transitions(counting[ok])
    rise4, fall4 = transitions(fsm[ok])
    print(f"   bit5 transitions: {rise5} rising / {fall5} falling   "
          f"bit4 transitions: {rise4} rising / {fall4} falling")
    tail = counting & ~fsm & ok
    print(f"   LATCH TAIL (bit5 & ~bit4): {tail.sum()} / {ok.sum()} ({100 * tail[ok].mean():.2f}%)")
    print("      -- counter still latched while the FSM has timed out back to NEUTRAL. A READING,")
    print(f"      not an error; HYST = {HYST} ticks vs a {HOLD / 1000:.0f}s hold makes it expected.")

    # ---- PER-ARM OCCUPANCY -------------------------------------------------------------------------
    conds = [("ALL frames", ok),
             ("ENGAGED (SCA==1)", ok & eng),
             ("ENGAGED + creep", ok & eng & creep),
             ("ENGAGED + creep + hands-off", ok & eng & creep & hands_off),
             ("MANUAL (SCA!=1)", ok & ~eng),
             ("MANUAL + creep", ok & ~eng & creep),
             ("REVERSE", ok & d["rev"]),
             ("REVERSE + manual", ok & d["rev"] & ~eng)]
    print("\n-- PER-BIT OCCUPANCY --")
    print(f"   {'condition':32s} {'n':>7s} {'bit6 arm':>9s} {'bit5 cnt':>9s} "
          f"{'bit4 fsm':>9s} {'bit3 ovr':>9s}")
    for name, sel in conds:
        if sel.sum() == 0:
            print(f"   {name:32s} {0:7d}   (none)")
            continue
        print(f"   {name:32s} {sel.sum():7d} {100 * armed[sel].mean():8.2f}% "
              f"{100 * counting[sel].mean():8.2f}% {100 * fsm[sel].mean():8.2f}% "
              f"{100 * override[sel].mean():8.2f}%")

    print("\n-- BY SPEED (engaged frames) --")
    print(f"   {'band':>14s} {'n':>7s} {'bit6 arm':>9s} {'bit5 cnt':>9s} {'bit4 fsm':>9s}")
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 15), (15, 99)):
        sel = ok & eng & (d["v"] >= lo) & (d["v"] < hi)
        if sel.sum() == 0:
            continue
        print(f"   {f'{lo}-{hi} m/s':>14s} {sel.sum():7d} {100 * armed[sel].mean():8.2f}% "
              f"{100 * counting[sel].mean():8.2f}% {100 * fsm[sel].mean():8.2f}%")

    # ---- THE HEADLINE ------------------------------------------------------------------------------
    sel = ok & eng & creep
    print(f"\n{'-' * 92}\n-- THE HEADLINE: what fraction of ENGAGED-CREEP frames have bit6 set? --")
    if sel.sum() == 0:
        print("   no engaged creep frames. Cannot call it. Re-drive the parking-lot route.")
        return
    frac = armed[sel].mean()
    print(f"   *** bit6 SET on {100 * frac:.2f}% of {sel.sum()} engaged-creep frames ***")
    print(f"   (bit4 on {100 * fsm[sel].mean():.2f}%, bit5 on {100 * counting[sel].mean():.2f}%, "
          f"bit3 on {100 * override[sel].mean():.2f}%)")

    print("\n-- THE VERDICT, AND THE NEXT LEVER --")
    if frac == 0:
        if fsm[sel].mean() > 0.001:
            print("   V63 IS INERT, and we now know WHY: the FSM leaves NEUTRAL "
                  f"({100 * fsm[sel].mean():.2f}% of frames), so |gp-0x6c2c| DOES cross T = {T_THRESH},")
            print(f"   but the counter never latches to CEIL = {CEIL}. The reversals are not")
            print(f"   sustained enough to beat the {HYST}-tick dwell timeout.")
            print("   => NEXT LEVER: lower CEIL at cal 0xC64FA (BYTE, currently 5). Note this arms the")
            print("      SAME two raised gains sooner -- it does not touch the smooth-steering LERPs.")
            print("   ⚠ 0xC64FA is a BYTE (ld.bu @0x429DA/0x429FC). Reading it as u16 gives 517.")
        else:
            print("   V63 IS INERT, and we now know WHY: the FSM never leaves NEUTRAL, so")
            print(f"   |gp-0x6c2c| NEVER CROSSES T = {T_THRESH}. The detector cannot trip at any CEIL.")
            print("   => NEXT LEVER: lower T at cal 0xC620A (HALFWORD, ld.h @0x428F6/0x42910).")
            print("      Lowering CEIL first would be wasted -- the counter never increments at all.")
        print("   In BOTH cases a null V63 drive is explained WITHOUT reflashing to find out, which is")
        print("   the whole point of V64.")
    elif frac < 0.02:
        print(f"   MARGINAL. The arm is selected, but only on {100 * frac:.2f}% of engaged-creep")
        print("   frames. Given the latch never clears at creep, that low a duty cycle means the")
        print("   detector tripped late or only in one part of the route -- check TIME-TO-FIRST-SET")
        print("   above and whether the log started before engagement.")
        print("   => If V63 drove null: the arm was barely ever active, so the null is about COVERAGE,")
        print("      not gain. Lower CEIL 0xC64FA before raising 0xC6440/0xC643E any further.")
    else:
        print(f"   *** V63'S ARM IS LIVE. *** Selected on {100 * frac:.2f}% of engaged-creep frames.")
        print("   A null V63 drive therefore means the DAMPING RISE WAS TOO SMALL, not that the")
        print("   detector missed. The detector cals (T 0xC620A, CEIL 0xC64FA) are NOT the problem.")
        print("   => NEXT LEVER: raise 0xC6440 / 0xC643E further (V63 took them 2x), or fly V62,")
        print("      which doubles the lane unconditionally and cannot miss -- at the manual-feel")
        print("      cost the operator objected to.")
        print("   ⚠ AND NOTE WHAT THE LATCH MEANS FOR FEEL: bit6 stays set for the rest of the")
        print("      low-speed segment, so V63's raised damping is ALSO active during manual steering")
        print("      after the first burst. If the operator reports heavier manual steering on V63,")
        print("      that is this latch, not a build error.")

    ovr = override[sel].mean()
    print("\n-- r24 COVERAGE (bit3): does V63's 0xC6440 raise reach r24 at all? --")
    print(f"   bit3 set on {100 * ovr:.2f}% of engaged-creep frames")
    if ovr > 0.5:
        print("   => r24 is MOSTLY on 0xC6442 (=1024), which has HIGHER priority than the state>=5 arm.")
        print("      V63's 0xC6440 raise does little or nothing for r24; r26 carries the whole build.")
        print("      => raise 0xC6442 too if r26 alone proves insufficient.")
    elif ovr > 0.01:
        print("   => r24 is INTERMITTENTLY on 0xC6442. Partial coverage; r26 still carries most of it.")
    else:
        print("   => the override is idle. r24 DOES take V63's 0xC6440, so both lanes are covered.")
    print()


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        sys.exit(1)
    report(Path(paths[0]).name.split("--")[0] + f"  [{len(paths)} seg]", collect(paths))
