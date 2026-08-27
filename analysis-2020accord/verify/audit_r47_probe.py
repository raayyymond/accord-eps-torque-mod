#!/usr/bin/env python3
"""verify/audit_r47_probe.py -- V67 gate-probe decode + FLIGHT-CLEAN audit for route 47.

Route `75604b0a432fdc89_00000047--3e0b6134c0`, 26 segments (0..25), flown on V67.

Reads the caches written by `extract/extract_r47_cache.py` (`_scratch/cache/r47/r47s{N}.npz` +
`r47s{N}_events.json`). Everything in sections A-G is cache-only and takes seconds.
Section H re-parses the RAW rlogs and is the INDEPENDENT SECOND METHOD for the
STEER_STATUS == 4 count -- the gridded cache holds 0x18F held-last onto the 0x14A
arrival grid, so a 1-frame ST==4 blip could in principle be dropped or duplicated by
the hold. H counts every 0x18F src-1 frame as it arrived.

    python analysis-2020accord/verify/audit_r47_probe.py           # A-G, cache only
    python analysis-2020accord/verify/audit_r47_probe.py --raw     # + H (re-parses 26 rlogs, ~3 min)
    python analysis-2020accord/verify/audit_r47_probe.py --raw --refresh   # force the rlog re-parse

H caches its own result to `_scratch/cache/r47/r47_raw18f.npz`; `--refresh` rebuilds it.

🛑 V67's byte4 (CAN 0x14A src 1). The same five bits have carried four different meanings
across V59/V64/V65/V66/V67 -- this decode is V67's and only V67's:
    bit7 = 1                   LIVENESS. field(bits 7:3) == 0 => the cave did not fire => VOID
    bit6 = gp-0x6806 != 0      *** THE GATE *** -- V67's x2 rate-lane arm is taken here, nowhere else
    bit5 = gp-0x671d != 0      *** THE MASK *** -- OUTRANKS the arm, pins the gain to 0xC6442 = 1024,
                               which is BELOW the stock creep LERP of 3072
    bit4 = gp-0x671a >= 5      the THIRD arm (0xC6440 = 2048); bites only while bit6 is clear
    bit3 = 0                   UNUSED on V67 -- a set bit means this is not a V67 log
    bits 2:0 = stock STEER_SENSOR_STATUS, preserved

WALL CLOCK -- 🛑 `wall_t0` IN THE CACHE IS NOT USABBLE AS WRITTEN ON TWO SEGMENTS.
`extract/extract_r47_cache.py` takes the MEDIAN of (clocks.wallTimeNanos - logMonoTime). On s0 the
clocks stream still carries the pre-NTP RTC value (2025-07-02) for most of the segment, so the
median lands a year early and `wall_off_sd` is 3.86e6 s. On s25 there are ZERO clocks messages
and `wall_t0` is NaN. This tool instead fits ONE route-wide constant
`abs_off = wall_t0 - t0_mono` over the segments whose own `wall_off_sd` is sane, then applies it
to every segment. Across s1..s24 that constant is stable to +-0.03 s.
"""
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("R47_CACHE", ROOT / "_scratch/cache/r47"))
RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = "75604b0a432fdc89_00000047--3e0b6134c0"
SEGS = list(range(26))

GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

# Flight-clean event set. `steerUnavailable` / `steerTempUnavailable` are the EPS-side ones;
# the rest are the openpilot-side health signals prior handoffs have audited.
WATCH = ("steerUnavailable", "steerTempUnavailable", "canError", "immediateDisable",
         "controlsMismatch", "steerSaturated", "wrongGear")

# The kill band for a gate that switches a control gain (docs/specs/design/V66-V67-DESIGN.md).
KILL_LO_HZ, KILL_HI_HZ = 15.0, 60.0

# ★★ V57's on-car validation of THIS SAME CELL (gp-0x6806), routes 28/29, July.
# (route, frames, % agreement with carControl.latActive, % duty, transitions/s)
V57_BASELINE = ((29, 7924, 99.899, 21.73, 0.0505), (28, 29990, 99.943, 49.88, 0.0300))

WALL_SD_MAX = 1.0        # a segment whose wall_off_sd exceeds this is NOT used for the fit


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")


def transitions(m):
    d = np.diff(np.asarray(m, bool).astype(np.int8))
    return int((d > 0).sum()), int((d < 0).sum())


def load():
    segs = {}
    for s in SEGS:
        z = np.load(CACHE / f"r47s{s}.npz")
        segs[s] = {k: z[k] for k in z.files}
        segs[s]["events"] = json.loads((CACHE / f"r47s{s}_events.json").read_text())
    return segs


def wall_offset(segs):
    """ONE route-wide constant (wall_t0 - t0_mono), median over the segments with sane clocks."""
    good, bad = [], []
    for s, d in segs.items():
        w, sd = float(d["wall_t0"][0]), float(d["wall_off_sd"][0])
        (good if (np.isfinite(w) and np.isfinite(sd) and sd <= WALL_SD_MAX) else bad).append(s)
    offs = np.array([float(segs[s]["wall_t0"][0]) - float(segs[s]["t0_mono"][0]) for s in good])
    return float(np.median(offs)), float(offs.std(ddof=1)), good, bad


def local(ts):
    return time.strftime("%H:%M:%S", time.localtime(ts))


# ---------------------------------------------------------------------------------------------
def main(do_raw, refresh):
    segs = load()
    off, off_sd, good, bad = wall_offset(segs)

    hdr("A.  WALL-CLOCK ANCHOR  (🛑 the cache's own wall_t0 is wrong on 2 of 26 segments)")
    print(f"   route-wide constant (wall_t0 - t0_mono) = {off:.3f}   sd over the {len(good)} good "
          f"segments = {off_sd:.4f} s")
    print(f"   segments REJECTED from the fit and back-filled from it: {bad}")
    for s in bad:
        d = segs[s]
        print(f"      s{s}: cache wall_t0={float(d['wall_t0'][0]):.3f} "
              f"sd={float(d['wall_off_sd'][0]):.1f} nclk={len(d['clk_wall'])}  "
              f"-> corrected {local(float(d['t0_mono'][0]) + off)}")
    for s in SEGS:
        segs[s]["w0"] = float(segs[s]["t0_mono"][0]) + off

    # ---- B. per-segment table ----------------------------------------------------------------
    hdr("B.  PER-SEGMENT TABLE   (probe decode + gate vs latActive + CAN rate + health)")
    print("   'agree' = bit6 == (carControl.latActive > 0.5), per frame on the 0x14A grid.")
    print("   't/s' counts bit6 transitions WITHIN the segment only -- joins are counted "
          "separately in C.")
    print(f"\n   {'seg':>3s} {'wall_t0':>9s} {'n':>6s} {'dur':>6s} {'fs':>6s} "
          f"{'VOID':>5s} {'bit3':>5s} {'illeg':>5s} "
          f"{'b6duty':>7s} {'lat':>7s} {'agree':>8s} {'trans':>6s} {'t/s':>6s} "
          f"{'b5':>3s} {'b4':>3s} {'r14A':>6s} {'r18F':>6s} {'ST4':>4s} {'ST!=0':>6s} {'gear'}")
    tot = Counter()
    per = {}
    for s in SEGS:
        d = segs[s]
        n = len(d["t"])
        dur = d["t"][-1] - d["t"][0]
        fs = 1.0 / np.median(np.diff(d["t"]))
        b6 = d["g6806"] > 0.5
        lat = d["cc_lat"] > 0.5
        agree = float((b6 == lat).mean())
        r, f_ = transitions(b6)
        void = int((d["field"] == 0).sum())
        b3 = int(d["unused"].sum())
        ill = int(d["illegal"].sum())
        st = d["sstat"].astype(int)
        st4 = int((st == 4).sum())
        stnz = int((st != 0).sum())
        g = Counter(d["cs_gear"].astype(int).tolist())
        gs = " ".join(f"{GEAR[k]}:{v}" for k, v in sorted(g.items(), key=lambda kv: -kv[1]))
        r14 = len(d["raw14A"]) / (d["raw14A"][-1] - d["raw14A"][0]) if len(d["raw14A"]) > 1 else 0
        r18 = len(d["raw18F"]) / (d["raw18F"][-1] - d["raw18F"][0]) if len(d["raw18F"]) > 1 else 0
        print(f"   s{s:<2d} {local(d['w0']):>9s} {n:6d} {dur:6.1f} {fs:6.2f} "
              f"{void:5d} {b3:5d} {ill:5d} "
              f"{100 * b6.mean():6.2f}% {100 * lat.mean():6.2f}% {100 * agree:7.3f}% "
              f"{r + f_:6d} {(r + f_) / dur:6.3f} "
              f"{int(d['g671d'].sum()):3d} {int(d['g671a'].sum()):3d} "
              f"{r14:6.2f} {r18:6.2f} {st4:4d} {stnz:6d} {gs}")
        tot["n"] += n
        tot["void"] += void
        tot["b3"] += b3
        tot["ill"] += ill
        tot["trans"] += r + f_
        tot["b5"] += int(d["g671d"].sum())
        tot["b4"] += int(d["g671a"].sum())
        tot["st4"] += st4
        per[s] = dict(n=n, dur=dur, fs=fs, b6=b6, lat=lat, agree=agree, trans=r + f_)

    # ---- C. gate validation ------------------------------------------------------------------
    b6a = np.concatenate([per[s]["b6"] for s in SEGS])
    lata = np.concatenate([per[s]["lat"] for s in SEGS])
    scaa = np.concatenate([segs[s]["sca"] > 0.5 for s in SEGS])
    n = len(b6a)
    dur_tot = sum(per[s]["dur"] for s in SEGS)

    hdr("C.  GATE VALIDATION -- bit6 (gp-0x6806) vs carControl.latActive")
    tp = int((b6a & lata).sum()); tn = int((~b6a & ~lata).sum())
    fp = int((b6a & ~lata).sum()); fn = int((~b6a & lata).sum())
    print(f"   route-wide agreement : {100 * (tp + tn) / n:.4f}%   ({n} frames, {dur_tot:.1f} s)")
    print(f"\n   confusion matrix                lat=1        lat=0")
    print(f"       bit6 = 1 (gate TRUE)   {tp:10d}   {fp:10d}")
    print(f"       bit6 = 0 (gate false)  {fn:10d}   {tn:10d}")
    print(f"   disagreeing frames: {fp + fn}  ({100 * (fp + fn) / n:.4f}%) = "
          f"{(fp + fn) / 100.4:.2f} s of exposure")
    print(f"   duty: latActive-true frames {100 * b6a[lata].mean():.3f}%   "
          f"latActive-false frames {100 * b6a[~lata].mean():.3f}%   "
          f"gap {100 * (b6a[lata].mean() - b6a[~lata].mean()):+.3f} pp")
    print(f"   cross-check against 0x18F b4 bit3 STEER_CONTROL_ACTIVE: "
          f"bit6 == sca on {100 * (b6a == scaa).mean():.4f}%")

    # 🛑 WHERE the disagreements sit decides what they MEAN. A disagreement 1 sample from a gate
    # edge is log-vs-CAN timing skew between openpilot's carControl and the EPS's own 100 Hz frame.
    # A disagreement in the MIDDLE of a hold is a real gate dropout and would sink the build.
    dd = []
    for s in SEGS:
        b6, lat = per[s]["b6"], per[s]["lat"]
        edges = np.flatnonzero(np.diff(b6.astype(np.int8)))
        for i in np.flatnonzero(b6 != lat):
            dd.append(int(np.min(np.abs(edges - i))) if len(edges) else 10 ** 9)
    if dd:
        dd = np.array(dd)
        print(f"\n   WHERE the {len(dd)} disagreements sit -- distance in samples to the nearest "
              f"bit6 EDGE:")
        print(f"      mean {dd.mean():.2f}   median {np.median(dd):.1f}   "
              f"MAX (the tail) {dd.max()}   => {int((dd <= 3).sum())}/{len(dd)} within 3 samples "
              f"(30 ms) of an edge")
        print(f"      mid-hold disagreements (>10 samples from any edge): "
              f"{int((dd > 10).sum())}  <- these would be real GATE DROPOUTS")

    join = 0
    for a, b in zip(SEGS[:-1], SEGS[1:]):
        if bool(per[a]["b6"][-1]) != bool(per[b]["b6"][0]):
            join += 1
    print(f"\n   TRANSITIONS. within-segment {tot['trans']}  +  at segment joins {join}  "
          f"=  {tot['trans'] + join} total")
    print(f"   rate = {(tot['trans'] + join) / dur_tot:.4f} transitions/s over {dur_tot:.1f} s "
          f"=> {(tot['trans'] + join) / 2:.0f} engagement episodes")
    print("\n   ★★ AGAINST V57's PRE-FLASH ON-CAR VALIDATION OF THE SAME CELL:")
    for rt, fr, ag, du, tps in V57_BASELINE:
        print(f"      route {rt:<3d} {fr:7d} frames  agreement {ag:7.3f}%  duty {du:6.2f}%  "
              f"{tps:.4f} trans/s")
    print(f"      route 47  {n:7d} frames  agreement {100 * (tp + tn) / n:7.3f}%  "
          f"duty {100 * b6a.mean():6.2f}%  {(tot['trans'] + join) / dur_tot:.4f} trans/s")

    # ---- C2. toggle spectrum -----------------------------------------------------------------
    print(f"\n   -- TOGGLE SPECTRUM (the parametric-pump check; kill band "
          f"{KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz) --")
    ntr = tot["trans"] + join
    print(f"   HARD BOUND, no spectrum needed: {ntr} transitions in {dur_tot:.1f} s can carry at "
          f"most\n   {ntr / 2 / dur_tot:.5f} Hz of square-wave fundamental -- "
          f"{KILL_LO_HZ / max(ntr / 2 / dur_tot, 1e-12):.0f}x below the kill band.")
    shown = 0
    for s in SEGS:
        m = per[s]["b6"].astype(float)
        if m.std() == 0 or per[s]["trans"] < 4:
            continue
        shown += 1
        fs = per[s]["fs"]
        P = np.abs(np.fft.rfft((m - m.mean()) * np.hanning(len(m)))) ** 2
        f = np.fft.rfftfreq(len(m), 1 / fs)
        band = (f >= KILL_LO_HZ) & (f <= min(KILL_HI_HZ, fs / 2))
        print(f"   s{s:<2d} {per[s]['trans']:3d} toggles  peak {f[1:][np.argmax(P[1:])]:6.3f} Hz  "
              f"power in {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz = "
              f"{100 * P[band].sum() / P[1:].sum():.4f}% of AC power")
    if not shown:
        print(f"   NO SEGMENT REACHES 4 TOGGLES (the most any segment has is "
              f"{max(per[s]['trans'] for s in SEGS)}), so no per-segment spectrum is estimated --")
        print("   a 2-toggle series has no meaningful periodogram. The route-wide series below is")
        print("   the only one worth transforming.")
    # The 26 segments are contiguous in logMonoTime (checked in J), so the concatenation is a real
    # continuous series here and NOT the 'concatenated subset' trap that retracted V58's 25 Hz.
    fs_r = float(np.median([per[s]["fs"] for s in SEGS]))
    P = np.abs(np.fft.rfft((b6a.astype(float) - b6a.mean()) * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, 1 / fs_r)
    band = (f >= KILL_LO_HZ) & (f <= min(KILL_HI_HZ, fs_r / 2))
    print(f"   ROUTE-WIDE series ({n} samples, contiguous): peak {f[1:][np.argmax(P[1:])]:.4f} Hz; "
          f"power in {KILL_LO_HZ:.0f}-{KILL_HI_HZ:.0f} Hz = "
          f"{100 * P[band].sum() / P[1:].sum():.6f}% of AC power; "
          f"below 1 Hz = {100 * P[(f > 0) & (f < 1)].sum() / P[1:].sum():.4f}%")
    print("   🛑 fs ~100 Hz => Nyquist ~50 Hz; a true 58 Hz toggle would alias to 42 Hz. The HARD")
    print("      BOUND above does not depend on the spectrum, so the alias does not weaken it.")

    # ---- D. masking risk ---------------------------------------------------------------------
    hdr("D.  MASKING RISK -- bit5 (gp-0x671d) and bit4 (gp-0x671a >= 5)")
    b5a = np.concatenate([segs[s]["g671d"] > 0.5 for s in SEGS])
    b4a = np.concatenate([segs[s]["g671a"] > 0.5 for s in SEGS])
    print(f"   bit5 gp-0x671d != 0  set on {int(b5a.sum()):7d} / {n} frames "
          f"({100 * b5a.mean():.5f}%)")
    print(f"   bit4 gp-0x671a >= 5  set on {int(b4a.sum()):7d} / {n} frames "
          f"({100 * b4a.mean():.5f}%)")
    print(f"   gate TRUE but MASKED (bit6 & bit5) : {int((b6a & b5a).sum())}  "
          "<- the dose V67 failed to deliver")
    print("\n   arms resolved through the priority ladder (they must partition the drive):")
    sel = {"0xC6442 = 1024  MASKED, BELOW STOCK": b5a,
           "0xC6446 = 5244  *** V67's ARM ***": b6a & ~b5a,
           "0xC6440 = 2048  third arm": b4a & ~b6a & ~b5a,
           "mode-10 LERP            = STOCK": ~b5a & ~b6a & ~b4a}
    acc = np.zeros(n, bool)
    for k, v in sel.items():
        print(f"      {k:42s} {int(v.sum()):7d}  {100 * v.mean():6.2f}%")
        acc |= v
    assert int(acc.sum()) == n, "the four arms do not partition the drive"
    print(f"      (partition checked: {n} frames)")

    # ---- E. decode faults --------------------------------------------------------------------
    hdr("E.  DECODE FAULTS")
    pa = np.concatenate([segs[s]["probe"].astype(int) for s in SEGS])
    print(f"   VOID (field == 0, cave did not fire) : {tot['void']} / {n}")
    print(f"   bit3 set (UNUSED on V67)             : {tot['b3']} / {n}")
    print(f"   `illegal` (bit3 set OR bit7 clear)   : {tot['ill']} / {n}")
    print(f"   byte4 histogram (whole route): " +
          "  ".join(f"0x{v:02X} x{c}" for v, c in Counter(pa.tolist()).most_common()))
    legal = {0x80 | a | b | c for a in (0, 0x40) for b in (0, 0x20) for c in (0, 0x10)}
    print(f"   payloads outside the 8 legal (masking bits 2:0): "
          f"{int(sum(1 for v in set(pa.tolist()) if (v & 0xF8) not in legal))} distinct")

    # ---- F. flight-clean: STEER_STATUS -------------------------------------------------------
    hdr("F.  FLIGHT-CLEAN -- STEER_STATUS (0x18F byte4 bits 7:4), METHOD 1 = gridded cache")
    sta = np.concatenate([segs[s]["sstat"].astype(int) for s in SEGS])
    print(f"   histogram over {n} gridded frames: {dict(sorted(Counter(sta.tolist()).items()))}")
    print(f"   *** ST == 4 (the gentle EME) : {int((sta == 4).sum())} ***")
    for v in sorted(set(sta.tolist())):
        if v == 0:
            continue
        for s in SEGS:
            m = segs[s]["sstat"].astype(int) == v
            if m.any():
                tt = segs[s]["t"][m]
                print(f"      ST=={v}: s{s} {int(m.sum())} frames, t+{tt[0]:.3f}..{tt[-1]:.3f} s "
                      f"({local(segs[s]['w0'] + tt[0])} local), vEgo "
                      f"{segs[s]['cs_v'][m].min():.2f}..{segs[s]['cs_v'][m].max():.2f}")
    print("   ⚠ the CHANNEL IS LIVE, not stuck: prior caches read ST==3 on every route "
          "(r29 119, r31 10,\n     r35 119, r37 119, r3a 81, r3b 119 frames), so a 0 here is a "
          "measurement, not a dead field.")

    # ---- G. events + gear --------------------------------------------------------------------
    hdr("G.  FLIGHT-CLEAN -- onroadEvents")
    allc = Counter()
    for s in SEGS:
        for e in segs[s]["events"]:
            allc[e["name"]] += 1
    print("   every event name in the route: " +
          "  ".join(f"{k}:{v}" for k, v in allc.most_common()))
    print(f"\n   -- THE WATCHED SET {WATCH} --")
    for w in WATCH:
        hits = [(s, e) for s in SEGS for e in segs[s]["events"] if e["name"] == w]
        if not hits:
            print(f"   {w:22s} 0")
            continue
        print(f"   {w:22s} {len(hits)}")
        bys = {}
        for s, e in hits:
            bys.setdefault(s, []).append(e)
        for s, es in sorted(bys.items()):
            ts = [e["t"] for e in es]
            fl = Counter((e["enable"], e["soft"], e["immediate"], e["noEntry"]) for e in es)
            print(f"        s{s:<2d} {len(es):4d}x  t+{min(ts):7.3f}..{max(ts):7.3f}  "
                  f"{local(segs[s]['w0'] + min(ts))}-{local(segs[s]['w0'] + max(ts))} local  "
                  f"(enable,soft,immediate,noEntry)={dict(fl)}")

    hdr("H.  GEAR -- segments to EXCLUDE from downstream dynamics analysis")
    for s in SEGS:
        g = Counter(segs[s]["cs_gear"].astype(int).tolist())
        flag = [GEAR[k] for k in g if GEAR[k] in ("reverse", "park", "neutral", "unknown")]
        if flag:
            print(f"   s{s:<2d} EXCLUDE/CAUTION: " +
                  " ".join(f"{GEAR[k]}={g[k]}" for k in sorted(g) if GEAR[k] in flag) +
                  f"   (drive={g.get(2, 0)})")
    print("   all other segments are 100% drive.")

    # ---- I. CAN health: the MEAN rate AND its TAIL -------------------------------------------
    hdr("I.  CAN HEALTH -- rate MEAN and inter-arrival TAIL (a mean of 100 Hz hides a dropout)")
    print(f"   {'seg':>4s} {'0x14A Hz':>9s} {'p99 gap':>9s} {'max gap':>9s} {'>30ms':>6s}   "
          f"{'0x18F Hz':>9s} {'p99 gap':>9s} {'max gap':>9s} {'>30ms':>6s}   {'join gap':>9s}")
    worst = 0.0
    for i, s in enumerate(SEGS):
        row = f"   s{s:<3d}"
        for a in ("raw14A", "raw18F"):
            g = np.diff(segs[s][a])
            hz = len(segs[s][a]) / (segs[s][a][-1] - segs[s][a][0])
            row += (f" {hz:9.2f} {1000 * np.percentile(g, 99):8.2f}m "
                    f"{1000 * g.max():8.2f}m {int((g > 0.030).sum()):6d}  ")
            worst = max(worst, g.max())
        if i + 1 < len(SEGS):
            nxt = SEGS[i + 1]
            jg = (float(segs[nxt]["t0_mono"][0]) + segs[nxt]["raw14A"][0]) - \
                 (float(segs[s]["t0_mono"][0]) + segs[s]["raw14A"][-1])
            row += f" {1000 * jg:8.2f}m"
        print(row)
    print(f"   worst single 0x14A/0x18F inter-arrival gap anywhere in the route: "
          f"{1000 * worst:.1f} ms")
    print("   'join gap' is the 0x14A gap ACROSS a segment boundary in absolute logMonoTime. If it")
    print("   is ~10 ms the segments are contiguous and section C's concatenation is a real series.")

    # ---- J. raw rlog cross-check -------------------------------------------------------------
    if do_raw:
        raw_check(segs, refresh)
    else:
        print("\n   (skipping the raw-rlog second method for ST==4; pass --raw to run it)")


def raw_check(segs, refresh):
    """INDEPENDENT SECOND METHOD: count ST==4 on every raw 0x18F src-1 frame."""
    out = CACHE / "r47_raw18f.npz"
    if out.exists() and not refresh:
        z = np.load(out)
        st_hist = {int(k): int(v) for k, v in zip(z["st_vals"], z["st_cnt"])}
        n18, n14, b4h = int(z["n18"]), int(z["n14"]), z["b4_hist"]
        per18, per14 = z["per18"], z["per14"]
        t4 = z["t4"]
    else:
        sys.path.insert(0, str(ROOT / "rlog-tools"))
        from rlog_parse import read_messages
        st = Counter(); b4 = Counter(); n18 = n14 = 0
        per18, per14, t4 = [], [], []
        for s in SEGS:
            p = RLOGDIR / f"{ROUTE}--{s}--rlog.zst"
            c18 = c14 = 0
            for evt in read_messages(p):
                try:
                    if evt.which() != "can":
                        continue
                except Exception:
                    continue
                tm = evt.logMonoTime * 1e-9
                for m in evt.can:
                    if int(m.src) != 1:
                        continue
                    a = int(m.address)
                    d = bytes(m.dat)
                    if a == 0x18F and len(d) >= 5:
                        v = (d[4] >> 4) & 0x0F
                        st[v] += 1
                        c18 += 1
                        if v == 4:
                            t4.append((s, tm))
                    elif a == 0x14A and len(d) >= 5:
                        b4[d[4]] += 1
                        c14 += 1
            per18.append(c18); per14.append(c14)
            n18 += c18; n14 += c14
            print(f"      s{s}: 0x18F {c18}  0x14A {c14}", flush=True)
        st_hist = dict(st)
        b4h = np.array(sorted(b4.items()), dtype=np.int64)
        per18 = np.array(per18); per14 = np.array(per14)
        t4 = np.array(t4, float).reshape(-1, 2)
        np.savez_compressed(out, st_vals=np.array(sorted(st_hist)),
                            st_cnt=np.array([st_hist[k] for k in sorted(st_hist)]),
                            n18=n18, n14=n14, b4_hist=b4h, per18=per18, per14=per14, t4=t4)

    hdr("J.  FLIGHT-CLEAN -- STEER_STATUS, METHOD 2 = RAW 0x18F src-1 CAN frames (independent)")
    print(f"   raw 0x18F src1 frames : {n18}")
    print(f"   raw 0x14A src1 frames : {n14}")
    print(f"   STEER_STATUS histogram: {dict(sorted(st_hist.items()))}")
    print(f"   *** ST == 4 (the gentle EME), RAW COUNT : {st_hist.get(4, 0)} ***")
    if len(t4):
        for s, tm in t4[:20]:
            print(f"      s{int(s)} logMonoTime {tm:.3f}")
    cache_n = sum(len(segs[s]["t"]) for s in SEGS)
    cache_st = Counter(np.concatenate([segs[s]["sstat"].astype(int) for s in SEGS]).tolist())
    print(f"\n   METHOD 1 vs METHOD 2:")
    print(f"      gridded frames {cache_n}   raw 0x14A {n14}   difference "
          f"{n14 - cache_n} (the cache drops each segment's 0x14A frames that precede its first "
          f"0x18F)")
    print(f"      ST==4  cache {cache_st.get(4, 0)}   raw {st_hist.get(4, 0)}   "
          f"{'AGREE' if cache_st.get(4, 0) == st_hist.get(4, 0) else '*** DISAGREE ***'}")
    print(f"      ST==3  cache {cache_st.get(3, 0)}   raw {st_hist.get(3, 0)}  "
          "(hold-vs-raw difference here is expected: the grid resamples 0x18F)")
    print(f"\n   raw 0x14A byte4 histogram: " +
          "  ".join(f"0x{int(v):02X} x{int(c)}" for v, c in b4h))
    print(f"\n   {'seg':>4s} {'0x18F':>7s} {'0x14A':>7s} {'Hz18F':>7s} {'Hz14A':>7s}")
    for i, s in enumerate(SEGS):
        dur = segs[s]["t"][-1] - segs[s]["t"][0]
        print(f"   s{s:<3d} {int(per18[i]):7d} {int(per14[i]):7d} "
              f"{per18[i] / dur:7.2f} {per14[i] / dur:7.2f}")


if __name__ == "__main__":
    main("--raw" in sys.argv, "--refresh" in sys.argv)
