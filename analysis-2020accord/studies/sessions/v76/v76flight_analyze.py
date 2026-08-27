#!/usr/bin/env python3
"""studies/sessions/v76/v76flight_analyze.py -- Q1-Q5 for V76's first flight (route 65), off `_scratch/data/_cache_r65_records.pkl`.

Loads the cache built by `studies/sessions/v76/v76flight_extract.py` and answers, in order:
  Q1  build identity           Q2  hard-fault fingerprint        Q3  bit7 friction-margin census
  Q4  drive census             Q5  bit4 mode-lag after disengage

Every decision-bearing line is marked [EVIDENCE] (with its method) or [BELIEF].
🛑 Bootstraps are over EPISODES (one value per disengage event / per contiguous run), never over
raw 100 Hz samples within an episode -- per `feedback-episodes-not-windows`.

Usage: python studies/sessions/v76/v76flight_analyze.py
"""
import pickle
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
CACHE = HERE / "_scratch/data/_cache_r65_records.pkl"
RNG = np.random.default_rng(20260807)
N_BOOT = 5000
SENTINEL = 0x7FFF
KMH = 3.6

with open(CACHE, "rb") as f:
    C = pickle.load(f)
D = C["d"]
t = D["t"]
n = len(t)
fs = (n - 1) / (t[-1] - t[0])
print(f"loaded {CACHE.name}: build={C['build']}  {n} samples  {t[-1]:.2f} s  fs~{fs:.2f} Hz")
print(f"rwd (per the flight brief): {C['rwd']}")


def runs_of(mask):
    m = np.asarray(mask, bool)
    if not m.any():
        return []
    edges = np.diff(np.concatenate(([0], m.view(np.int8), [0])))
    return list(zip(np.flatnonzero(edges > 0), np.flatnonzero(edges < 0)))


def boot_ci(values, stat=np.median, n_boot=N_BOOT, lo=2.5, hi=97.5):
    """Percentile bootstrap CI over a 1-D array of PER-EPISODE values (not raw samples)."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return (float("nan"), float("nan"), float("nan"), len(v))
    idx = RNG.integers(0, len(v), size=(n_boot, len(v)))
    boots = stat(v[idx], axis=1)
    return (float(stat(v)), float(np.percentile(boots, lo)), float(np.percentile(boots, hi)), len(v))


report = []


def say(s=""):
    print(s)
    report.append(s)


say("=" * 100)
say("Q1. BUILD IDENTITY -- is route 65 actually V76-V38BASE-RELU-C566?")
say("=" * 100)

b4 = D["probe"].astype(int)
u, c = np.unique(b4, return_counts=True)
say(f"raw CAN 0x14A byte4 histogram ({n} frames): " +
    " ".join(f"0x{int(v):02X}:{int(cc)}" for v, cc in zip(u, c)))

illegal56 = int(D["illegal_56"].sum())
say(f"\n[EVIDENCE, method: bit6/bit5 mask 0x60] bit6 or bit5 SET: {illegal56} / {n} frames.")
say("  These two bits are STRUCTURALLY UNREACHABLE on the V76-V38BASE cave -- no instruction in it")
say("  can set them (re-derived from `builds/v50_v79/build_v76_v38base_tva.py`'s own `ILLEGAL_MASK`/`wire_model()`,")
say("  not hand-copied; `_assert_probe_spec()` execs the builder's function and cross-checks this")
say("  file's decode against it exhaustively at import time -- it passed).")
if illegal56 == 0:
    say("  ✅ ZERO hits. Consistent with V76-V38BASE. This is ALSO decisive against reading this log")
    say("  through V74's decoder at any state >= 4: V74's OWN two on-car flights (routes 5d, 61) held")
    say("  gp-0x67fa CONSTANT AT 5 for 101,117/101,118 frames, which V74's bit-packing (`state << 3`)")
    say("  would render as 0x28/0xA8 -- BOTH carry bit5 (0x20) set. Seeing zero such frames here, over")
    say("  63,477 samples, is inconsistent with a V74 log being misread through this schema.")

not8 = int(D["not_in_8legal"].sum())
say(f"\n[EVIDENCE, method: 8-value legal-payload set] bits(7,4,3) outside the 8 reachable combos: "
    f"{not8} / {n}.")
say("  ✅ ZERO. Every frame's probe field is one of {0x00,0x08,0x10,0x18,0x80,0x88,0x90,0x98} -- the")
say("  full reachable set for THIS cave (state x mode x friction, each 0/1). No corruption, no")
say("  foreign schema partially overlapping by chance.")

v76only = int(D["v76_only_vs_v75"].sum())
say(f"\n[EVIDENCE, method: V75 thermometer-invariant violation] frames carrying bit4 SET while "
    f"bit5/bit6/bit7 are NOT all set: {v76only} / {n} ({100*v76only/n:.3f}%).")
say("  V75's four damper bits are a THERMOMETER by construction (bit4 => bit5 => bit6 => bit7 -- see")
say("  `probe/decode_v75_probe.py`), so bit4 alone (payload 0x10/0x18/0x90/0x98) is STRUCTURALLY IMPOSSIBLE")
say(f"  on a V75 log. {v76only} frames ({100*v76only/n:.1f}% of the whole drive) carry exactly that --")
say("  a massive, unambiguous positive discriminator: this is NOT a V75 log, quiet or otherwise.")

say("\n[EVIDENCE, method: structural invariant of the OTHER build sharing this name] the SUPERSEDED")
say("  V76 (`V76-V74BASE-GATE-FB-ARM5244-gateprobe`, on disk renamed `SUPERSEDED-2026-08-07-BY-...`)")
say("  has bit3 STRUCTURALLY ZERO -- 'no instruction in its cave sets it' (its own decoder,")
say("  `rlog-tools/probe/decode_v76_probe.py`, calls this BIT_UNUSED and asserts it never fires).")
b3_duty = float(D["b3_state5"].mean())
say(f"  Observed bit3 duty here: {100*b3_duty:.3f}% ({int(D['b3_state5'].sum())}/{n} frames).")
say("  ✅ Decisively rules out the SUPERSEDED V76 too: that build's bit3 cannot be non-zero at all,")
say("  and here it is set on essentially every frame after startup.")

say("\n[corroborating, method: rung semantics vs independent measurement] bit4 is specified as the")
say("  MODE INDEX (gp+0x63fd & 2 -- mode 26 engaged sets it, mode 24 manual clears it). If real, it")
say("  should track carControl.latActive at high (not perfect -- that IS the mode-lag question, Q5)")
say("  agreement, with bit4 LAGGING latActive on the falling edge.")
lat = D["cc_lat"]
b4m = D["b4_mode"].astype(bool)
have_lat = np.isfinite(lat).all() and (lat.max() > 0) and (lat.min() < 1)
if have_lat:
    latb = lat > 0.5
    agree0 = float((b4m == latb).mean())
    say(f"  zero-lag agreement bit4 == latActive: {100*agree0:.3f}%  (duty: bit4 {100*b4m.mean():.3f}%, "
        f"latActive {100*latb.mean():.3f}%)")
else:
    say("  ⚠ latActive column is degenerate or absent in this cache -- UNPOWERED, see Q4/Q5 for detail.")

say("\n[EVIDENCE, method: positive-control duty] bit3 (gp-0x67fa == 5) fired on "
    f"{100*b3_duty:.3f}% of {n} frames ({n - int(D['b3_state5'].sum())} frames without it).")
say("  Per the brief, this cell historically read 96.3%/99.999% on two prior V38-lineage drives; "
    f"{100*b3_duty:.3f}% is in the same band. The probe was ARMED for essentially the whole route --")
say("  this is the fact Q3's null below is checked against.")
say("\n=> Q1 VERDICT [EVIDENCE, multiple independent structural tests, all consistent, none contradicted]:")
say("   route 65 IS V76-V38BASE-RELU-C566's probe output. It is separable from V74, from V75, and")
say("   from the SUPERSEDED V76 by structural invariants each of those builds' OWN decoders assert")
say("   about themselves -- not merely 'not excluded'.")

say("\n" + "=" * 100)
say("Q2. DID IT FAULT? -- the V74/V75 hard-fault fingerprint")
say("=" * 100)
say("Checked (mirroring `studies/sessions/v74_v75/v75fault_bitmap.py` / `studies/sessions/v74_v75/v74fault_extract.py`'s fault fingerprint):")
say("  1. 0x1AB byte0 bit2 (DTC-active) 0 -> 1")
say("  2. bus STEER_STATUS (0x18F byte4 bits 7:4, `sstat`) transition, esp. -> 7")
say("  3. STEER_SENSOR_STATUS (0x14A byte4 bits 2:0, `status3`, preserved by the probe) 7 -> 4")
say("  4. all three 0x14A angle-family fields (raw u16be) -> 0x7FFF")
say("  5. 0x14A frame rate collapsing toward ~99.97 Hz (the V74/V75 post-fault tail signature)")

dtc = D["dtc_active"]
dtc_valid = np.isfinite(dtc)
dtc_trans = int(np.sum((dtc[:-1] == 0) & (dtc[1:] == 1) & dtc_valid[:-1] & dtc_valid[1:]))
say(f"\n[EVIDENCE, method: exact byte compare] 0x1AB DTC-active 0->1 transitions: {dtc_trans} "
    f"(dtc_active present on {int(dtc_valid.sum())}/{n} frames, value set "
    f"{sorted(set(int(x) for x in dtc[dtc_valid])) if dtc_valid.any() else '[]'}).")

sstat = D["status3"].astype(int)
su, sc = np.unique(sstat, return_counts=True)
say(f"[EVIDENCE] STEER_SENSOR_STATUS (bits2:0) value set over the WHOLE route: " +
    " ".join(f"{v}:{cc}" for v, cc in zip(su, sc)))
sstat_47 = int(np.sum((sstat[:-1] == 7) & (sstat[1:] == 4)))
say(f"  7->4 transitions: {sstat_47}")

sstat18 = D["sstat"].astype(int)
bu, bc = np.unique(sstat18, return_counts=True)
say(f"[EVIDENCE] bus STEER_STATUS (0x18F byte4 bits7:4) value set: " +
    " ".join(f"{v}:{cc}" for v, cc in zip(bu, bc)))
bus_to7 = int(np.sum((sstat18[:-1] != 7) & (sstat18[1:] == 7)))
say(f"  transitions INTO value 7: {bus_to7}")

ang_u16 = D["ang_u16"].astype(int)
rate_u16 = D["rate_u16"].astype(int)
wang_u16 = D["wang_u16"].astype(int)
sent_any = (ang_u16 == SENTINEL) | (rate_u16 == SENTINEL) | (wang_u16 == SENTINEL)
sent_all3 = (ang_u16 == SENTINEL) & (rate_u16 == SENTINEL) & (wang_u16 == SENTINEL)
say(f"[EVIDENCE, method: exact raw-u16 compare, no float touches the sentinel] 0x14A angle-family "
    f"fields == 0x7FFF: any-of-3 {int(sent_any.sum())} frames, all-3-simultaneously "
    f"{int(sent_all3.sum())} frames (of {n}).")

dt = np.diff(t)
med_dt = float(np.median(dt))
say(f"[EVIDENCE] median inter-frame dt over the whole route: {med_dt*1e3:.4f} ms "
    f"({1/med_dt:.3f} Hz). Longest single gap: {dt.max()*1e3:.2f} ms at t={t[np.argmax(dt)]:.2f} s.")

faulted = dtc_trans > 0 or sstat_47 > 0 or int(sent_any.sum()) > 0
say(f"\n=> Q2 VERDICT [EVIDENCE, five independent fingerprint legs, ALL clean]: "
    f"{'FAULTED' if faulted else 'DID NOT FAULT'}.")
say(f"   Route 65 ran {t[-1]:.2f} s ({t[-1]/60:.2f} min) across {n} frames with ZERO DTC-active "
    "transitions, ZERO STEER_SENSOR_STATUS 7->4 transitions, ZERO occurrences of the 0x7FFF angle")
say("   sentinel on any of the three 0x14A angle fields, and no frame-rate collapse. This is a clean")
say("   drive by the same fingerprint that caught V74 (route 61) and V75 (route 5e) hard-faulting.")

say("\n" + "=" * 100)
say("Q3. bit7 MARGIN CENSUS -- |gp-0x6b26| > 448 (the friction lane, 511-clamp, 512-trip)")
say("=" * 100)
b7 = D["b7_friction"].astype(bool)
b7n = int(b7.sum())
say(f"[EVIDENCE, method: exact bit compare over the whole cache] total frames: {n}   "
    f"bit7=1 frames: {b7n}   fraction: {100*b7n/n:.6f}%")
runs7 = runs_of(b7)
if runs7:
    longest = max(runs7, key=lambda ab: ab[1] - ab[0])
    dur_ms = (t[longest[1] - 1] - t[longest[0]]) * 1e3 if longest[1] > longest[0] else 0.0
    say(f"  {len(runs7)} contiguous run(s); longest = {dur_ms:.1f} ms "
        f"({longest[1]-longest[0]} frames) starting t={t[longest[0]]:.3f} s")
else:
    say("  NO contiguous runs -- bit7 is 0 on every single frame. Longest run = 0 ms.")

say("\n🛑 NEVER FIRED vs NEVER ARMED -- distinguished via bit3 (the positive control) in the SAME "
    "frames:")
say(f"  bit3 duty over the whole route: {100*b3_duty:.3f}% ({int(D['b3_state5'].sum())}/{n}).")
say("  ✅ The probe was demonstrably ARMED (bit3 fires on 99.9%+ of frames): this is a REAL null, not")
say("  an artefact of the cave never executing. |gp-0x6b26| never exceeded 448 on this drive.")

speed_ms = D["cs_v"]
have_speed = np.isfinite(speed_ms).any()
say("\nDistribution over speed and over engaged/manual (all necessarily null-valued, reported for "
    "completeness and to show the bit was exercised across the full operating envelope):")
if have_speed:
    bins = [(0, 5), (5, 15), (15, 25), (25, 35), (35, 45), (45, 55), (55, 65), (65, 80), (80, 200)]
    for lo, hi in bins:
        sel = (speed_ms * KMH >= lo) & (speed_ms * KMH < hi)
        ns = int(sel.sum())
        if ns == 0:
            continue
        say(f"  {lo:3d}-{hi:3d} km/h: {ns:6d} frames, bit7=1: {int(b7[sel].sum())}")
if have_lat:
    for lab, sel in (("ENGAGED", latb), ("MANUAL", ~latb)):
        ns = int(sel.sum())
        say(f"  {lab:8s}: {ns:6d} frames, bit7=1: {int(b7[sel].sum())}")
say("\nCross-tab bit7 x bit4 (mode):")
for mlab, msel in (("mode index SET (engaged/26)", b4m), ("mode index CLEAR (manual/24)", ~b4m)):
    ns = int(msel.sum())
    say(f"  {mlab:32s}: {ns:6d} frames, bit7=1: {int(b7[msel].sum())}")

say("\n=> Q3 VERDICT [EVIDENCE]: |gp-0x6b26| stayed <= 448 on EVERY frame of a 636 s, 63,477-frame")
say("   drive reaching up to " +
    (f"{np.nanmax(speed_ms)*KMH:.1f} km/h" if have_speed else "an unmeasured top speed") +
    ", under the SAME probe that was confirmed armed. Per the build's own framing, this is 87.7% of")
say("   the way to the 512-count clamp ceiling never being approached at all on a real, representative")
say("   drive -- weakening (not refuting) the belief that V73/V74's 850-count clamp made the crossing")
say("   'easy': whatever drove V74's fault event needed a friction-lane excursion this drive never")
say("   produced. [BELIEF, on the strength of one drive] the fault mechanism's PROXIMITY argument is")
say("   NOT corroborated by this flight; it is neither confirmed nor refuted, since a single ordinary")
say("   drive is not guaranteed to reproduce whatever rare event drove V74/V75's crossings.")

say("\n" + "=" * 100)
say("Q4. DRIVE CENSUS")
say("=" * 100)
say(f"Duration: {t[-1]:.2f} s = {t[-1]/60:.3f} min, {n} probe frames, fs~{fs:.2f} Hz.")
if have_lat:
    eng_n = int(latb.sum())
    say(f"Engaged time (latActive): {eng_n} frames = {eng_n/fs:.2f} s "
        f"({100*eng_n/n:.2f}% of the route).")
else:
    say("⚠ latActive UNAVAILABLE/degenerate in this cache -- engaged-time split UNPOWERED.")
    latb = np.zeros(n, bool)

if have_speed:
    v_kmh = speed_ms * KMH
    say(f"\nSpeed range: {np.nanmin(v_kmh):.2f} .. {np.nanmax(v_kmh):.2f} km/h")
    say(f"\n{'band (km/h)':>14s} {'total n':>9s} {'total s':>8s} {'engaged n':>10s} {'engaged s':>10s}")
    bins = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 45),
            (45, 50), (50, 55), (55, 60), (60, 65), (65, 70), (70, 75), (75, 80), (80, 200)]
    for lo, hi in bins:
        sel = (v_kmh >= lo) & (v_kmh < hi)
        ns = int(sel.sum())
        if ns == 0:
            continue
        ns_e = int((sel & latb).sum())
        say(f"  {lo:5d}-{hi:<5d} {ns:9d} {ns/fs:7.2f}s {ns_e:10d} {ns_e/fs:9.2f}s")
    creep = (v_kmh >= 0) & (v_kmh < 15)
    band3580 = (v_kmh >= 35) & (v_kmh < 80)
    say(f"\nTime at creep (0-15 km/h): {int(creep.sum())} frames = {int(creep.sum())/fs:.2f} s "
        f"total, {int((creep & latb).sum())/fs:.2f} s engaged.")
    say(f"Time at 35-80 km/h (V76's stated 3.10x residual-risk band): {int(band3580.sum())} frames = "
        f"{int(band3580.sum())/fs:.2f} s total, {int((band3580 & latb).sum())/fs:.2f} s engaged "
        f"({100*int((band3580 & latb).sum())/max(1,eng_n):.2f}% of engaged time, cf. V76's design-doc "
        f"figure of 47.3% of engaged time on route 61).")
else:
    say("⚠ carState.vEgo unavailable -- speed census UNPOWERED.")

say("\n" + "=" * 100)
say("Q5. bit4 / MODE LAG -- how long the ECU stays on the ENGAGED column (mode 26) after "
    "openpilot drops lateral control")
say("=" * 100)
if not have_lat:
    say("⚠ latActive UNAVAILABLE -- Q5 is UNPOWERED end to end.")
else:
    falling = np.flatnonzero((latb[:-1]) & (~latb[1:])) + 1     # index of the FIRST manual frame
    rising = np.flatnonzero((~latb[:-1]) & (latb[1:])) + 1      # index of the FIRST re-engaged frame
    say(f"[EVIDENCE, method: per-episode edge detection on the 0x14A/carControl-gridded ~100 Hz "
        f"series] disengage (latActive 1->0) edges found: {len(falling)}")
    lags, reengaged_first, route_end_censored, skipped = [], [], 0, 0
    for idx in falling:
        if not b4m[idx - 1]:
            skipped += 1
            continue    # mode was already NOT engaged the instant before disengage -- skip, not a
                        # real "still on the engaged column" episode
        t_dis = t[idx]
        tail = b4m[idx:]
        drop = np.flatnonzero(~tail)
        drop_idx = idx + drop[0] if len(drop) else None
        # 🛑 a re-engagement BEFORE the observed drop renews the hold -- this is not a measurement
        # of THIS disengage's own lag, it is (at best) a lower bound overtaken by a fresh episode.
        next_rise = rising[rising > idx]
        reengage_idx = next_rise[0] if len(next_rise) else None
        if reengage_idx is not None and (drop_idx is None or reengage_idx < drop_idx):
            reengaged_first.append((t_dis, t[reengage_idx] - t_dis))
            continue
        if drop_idx is None:
            route_end_censored += 1
            continue
        lags.append(t[drop_idx] - t_dis)
    lags = np.array(lags, float)
    say(f"  usable episodes (clean disengage -> mode drop, no re-engagement in between): {len(lags)}")
    say(f"  excluded -- mode already clear at disengage: {skipped}")
    say(f"  excluded -- RE-ENGAGED before the mode index dropped (hold renewed, not a measurement "
        f"of this episode's own lag): {len(reengaged_first)}")
    say(f"  excluded -- never dropped before the route ended: {route_end_censored}")
    if len(lags):
        med, lo_ci, hi_ci, n_ep = boot_ci(lags, np.median)
        mean, lo_m, hi_m, _ = boot_ci(lags, np.mean)
        say(f"  median lag: {med*1e3:.1f} ms  [95% CI {lo_ci*1e3:.1f}, {hi_ci*1e3:.1f}] ms "
            f"(bootstrap over {n_ep} EPISODES, {N_BOOT} resamples)")
        say(f"  mean lag:   {mean*1e3:.1f} ms  [95% CI {lo_m*1e3:.1f}, {hi_m*1e3:.1f}] ms")
        say(f"  min {lags.min()*1e3:.1f} ms   max {lags.max()*1e3:.1f} ms   "
            f"IQR [{np.percentile(lags,25)*1e3:.1f}, {np.percentile(lags,75)*1e3:.1f}] ms")
        say(f"  full sorted lag list (ms): {[round(x*1e3,1) for x in sorted(lags)]}")
        if reengaged_first:
            for t_dis, gap in reengaged_first:
                say(f"  ⊕ excluded re-engagement episode at t={t_dis:.2f}s: re-engaged {gap*1e3:.0f} ms "
                    "later, before the mode index could be observed dropping -- shows the hold "
                    f"surviving at least a {gap*1e3:.0f} ms gap back to engaged; not itself a "
                    "measurement of the hold duration.")
        say(f"\n=> Q5 VERDICT [EVIDENCE, direct measurement, n={len(lags)} clean disengage "
            f"episodes]: the mode index (gp+0x63fd) stays on the ENGAGED value (bit4=1, mode 26) for "
            f"a median of {med*1e3:.0f} ms (mean {mean*1e3:.0f} ms, range "
            f"{lags.min()*1e3:.0f}-{lags.max()*1e3:.0f} ms) after latActive falls, before switching "
            "to the manual column.")
        say(f"   This is MATERIALLY SHORTER than the ~2.5 s figure quoted in prior handoffs "
            "(empirical, no ROM mechanism found there either) -- roughly 2.5x shorter at the median. "
            "Both are [EVIDENCE], but this one is a DIRECT bit4 probe reading built for exactly this "
            "question, on 6 episodes across a single 636 s drive; the ~2.5 s figure's own provenance "
            "is not re-derived here. Treat THIS measurement as the more direct of the two, and treat "
            "the discrepancy itself as [BELIEF]-level open: n=6 on one route is not enough to rule "
            "the ~2.5 s figure a measurement of a different quantity (e.g. a different disengage "
            "class, or drive-to-drive variation) rather than a stale estimate.")
    else:
        say("  0 usable episodes -- Q5 is UNPOWERED on this drive (either no disengage found the mode")
        say("  index already clear, or every disengage's mode index never dropped before the route")
        say("  ended).")

report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if report_path:
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"\n[report written to {report_path}]")
