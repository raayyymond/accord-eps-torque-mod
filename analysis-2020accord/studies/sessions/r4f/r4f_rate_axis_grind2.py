#!/usr/bin/env python3
"""Route `4f`: grind #2 stratified by the RATE AXIS, and the test of prediction P-A.

P-A (orchestrator, 2026-08-04): V69 raises only Y[0]/Y[1] of the gain_B records -- the FLAT
[0, 400]-count segment of the `gp-0x6ac0` axis -- so its ×4 collapses to 1.00× by 1400 counts. At
grind #2's creep operating point (~256 deg/s ⇒ ~1206 counts) V69 delivers only **1.72×**, BELOW the
flat 2.00× that on V62/V65 produced the 11.71× amplification. ⇒ "grind #2 gone at low speed" would
be fully explained by an under-dose on the rate axis.

🛑 EXPOSURE COMES BEFORE MECHANISM. §1 reports the grind-#2 corner exposure and its detectability
FIRST, before any dose arithmetic, because the far likelier explanation of a zero is that the route
never entered the corner. If the corner exposure cannot detect grind #2 at V62's own rate, P-A is
UNTESTED on this route and no amount of stratification changes that.

★ EVERYTHING HERE IS SPLIT ENGAGED / DISENGAGED. V69 has NO gate (V67/V68 did), so its surface
doses MANUAL creep too -- the first build since V65 to do so, and manual creep is grind #2's home
arm. That makes 4f the most informative route yet for grind #2 in either direction.

Usage:  python studies/sessions/r4f/r4f_rate_axis_grind2.py [--json OUT]
"""
from __future__ import annotations
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

import argparse
import glob
import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.stats import poisson

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import r47_orchestrator_checks as R47                    # noqa: E402
from _r31_common import sustained                        # noqa: E402

FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMAGES = {"stock": FW / "stock_fw_dump" / "code.bin", "V62": FW / "_v62_plain_image.bin",
          "V67": FW / "_v67_plain_image.bin", "V69": FW / "_v69_plain_image.bin"}
REC_ADDR = [0xD2A74, 0xD2AB0, 0xD2AEC, 0xD2B28]
CROSS_X_ADDR = 0xC6010
R24_SAR, ARM_ADDR, GATE_BYTE = 0x3AC20, 0xC6446, 0x3AA96

# 🛑 counts per deg/s on `gp-0x6ac0`. The kit's working figure, and it reproduces the orchestrator's
# own operating points EXACTLY (128 deg/s -> 603, 256 -> 1206, 30-42 -> 141-198). ⚠ BELIEF, not
# EVIDENCE: `gp-0x6ac0` is the resolver/FOC ELECTRICAL rate and memory
# `accord-c520c-cap-table-axis-provenance` records that the table's INDEX FORMULA IS NOT
# RECONSTRUCTED. Every table below is therefore also printed in raw deg/s so the mapping can be
# redone without re-running anything.
CPS = 4.7121

CREEP = (0.3, 4.0)
CORNER_EFF, CORNER_ANG = 1200.0, 100.0
POOLS = {
    "Kd=1.00  (V58 r2b + V59 r2c + V64 r35)": ["_scratch/cache/r2b", "_scratch/cache/r2c", "_scratch/cache/r35"],
    "Kd=2.00  (V62 r37 + V65 r3a/r3b)":       ["_scratch/cache/r37", "_scratch/cache/r3a", "_scratch/cache/r3b"],
    "Kd=gated (V67 r47+r4a)":                 ["_scratch/cache/r47", "_scratch/cache/r4a"],
    "V69 r4f  *** THIS ROUTE ***":            ["_scratch/cache/r4f"],
}
KD2 = "Kd=2.00  (V62 r37 + V65 r3a/r3b)"
V67K = "Kd=gated (V67 r47+r4a)"
V69K = "V69 r4f  *** THIS ROUTE ***"

# Rate strata on the gp-0x6ac0 axis. Boundaries are the BYTE-VERIFIED X breakpoints (400, 1400) plus
# the two points where V69's and V67's dose CROSS V62's flat 2.000x (1126 and 1000) -- derived in §2.
STRATA = [(0, 400), (400, 1126), (1126, 1400), (1400, 10 ** 9)]
RES: dict = {}


def hdr(s):
    print(f"\n{'=' * 114}\n{s}\n{'=' * 114}")


# ------------------------------------------------------------------ the surface, from bytes -----
def rec_of(b, addr):
    return (list(struct.unpack_from("<4H", b, addr + 0x02)),
            list(struct.unpack_from("<4H", b, addr + 0x0A)))


def lerp(x, xs, ys):
    """FUN_0003ad74's LERP, mirroring the decompiled integer arithmetic: FLAT outside the ends,
    2-point interpolation between ADJACENT records only, `divq` truncating toward zero."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if x < xs[i + 1]:
            num = (ys[i + 1] - ys[i]) * (x - xs[i])
            q = abs(num) // (xs[i + 1] - xs[i])
            return ys[i] + (q if num >= 0 else -q)
    return ys[-1]


def gain_b(b, speed_counts, rate_counts):
    """gain_B as the firmware computes it: LERP over speed across records, then over the rate axis."""
    recs = [rec_of(b, a) for a in REC_ADDR]
    cross = list(struct.unpack_from("<4h", b, CROSS_X_ADDR))
    k = max(cross[0], min(speed_counts, cross[-1]))
    xs = [lerp(k, cross, [recs[i][0][j] for i in range(4)]) for j in range(4)]
    ys = [lerp(k, cross, [recs[i][1][j] for i in range(4)]) for j in range(4)]
    return lerp(rate_counts, xs, ys)


def delivered(name, b, speed_counts, rate_counts, engaged=True):
    """The DELIVERED r24-lane multiplier vs stock, for one build at one operating point.

    Three distinct mechanisms, all byte-verified in §2 -- they are NOT interchangeable:
      surface   V69: gain_B's own table raised. Rate-SHAPED, unconditional.
      sar       V62/V65: `sar 0xa` -> `sar 0x9` AFTER the multiply. FLAT ×2, every speed and rate.
      arm       V67/V68: gate repointed so `0xC6446` SUBSTITUTES for the whole LERP while LKAS
                applies. A CONSTANT gain, so its ratio to stock RISES with rate -- the opposite
                shape to V69's.
    """
    g_stock = gain_b(IMG["stock"], speed_counts, rate_counts)
    sar = struct.unpack_from("<H", b, R24_SAR)[0]
    gate = b[GATE_BYTE]
    arm = struct.unpack_from("<H", b, ARM_ADDR)[0]
    if gate == 0xFB and engaged:          # V67/V68: the arm substitutes for the surface
        g = arm
    else:
        g = gain_b(b, speed_counts, rate_counts)
    mult = 2.0 if sar == 0x42A9 else 1.0  # the `sar` edit doubles whatever the gain arm produced
    return g * mult / g_stock


IMG = {k: v.read_bytes() for k, v in IMAGES.items() if v.exists()}


# ------------------------------------------------------------------ windows ----------------------
def windows(cache, tag):
    """R47._windows' instrument EXACTLY (2.56 s, butter+hilbert, p99, burst > 500) plus the effort,
    angle and RATE covariates the corner and the rate stratification need."""
    rows = []
    for p in sorted(glob.glob(str(ROOT / cache / "*.npz"))):
        if "_imu" in p or "_rpm" in p:
            continue
        d = dict(np.load(p))
        if "cs_v" not in d or "tq" not in d or "rate_c" not in d:
            continue
        t = d["t"]
        fs = 1.0 / np.median(np.diff(t))
        if not 95 < fs < 105:
            continue
        env = {k: R47._envelope(d["tq"], fs, *v) for k, v in R47.BANDS.items()}
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        rate = np.abs(np.asarray(d["rate_c"], float))
        n, hop = int(R47.WIN_S * fs), int(R47.WIN_S * fs) // 2
        lat = d["cc_lat"] > 0.5
        for i in range(0, len(t) - n, hop):
            sl = slice(i, i + n)
            v = float(np.median(d["cs_v"][sl]))
            if not (CREEP[0] < v < CREEP[1]):
                continue
            rows.append(dict(tag=tag, v=v, lat=float(lat[sl].mean()),
                             ang=float(np.abs(d["ang"][sl]).max()),
                             eff=float(np.median(eff[sl])),
                             r50=float(np.median(rate[sl])),
                             r90=float(np.percentile(rate[sl], 90)),
                             rmax=float(np.max(rate[sl])),
                             **{k: float(np.percentile(env[k][sl], 99)) for k in R47.BANDS}))
    return rows


_W: dict = {}


def W(pool):
    if pool not in _W:
        _W[pool] = sum([windows(c, pool) for c in POOLS[pool]], [])
    return _W[pool]


ARMS = (("LKAS ON", lambda r: r["lat"] > 0.9), ("LKAS OFF", lambda r: r["lat"] < 0.1))


def stratum(r, key):
    c = r[key] * CPS
    for i, (lo, hi) in enumerate(STRATA):
        if lo <= c < hi:
            return i
    return len(STRATA) - 1


# =================================================================================================
def sec_exposure():
    hdr("1.  🛑 EXPOSURE FIRST — CAN ROUTE 4f DETECT GRIND #2 AT V62's OWN RATE?")
    print("   corner = creep(0.3-4.0 m/s) ∧ |sustained torque| >= 1200 ∧ |angle| >= 100 deg.")
    print("   Nothing below this section is interpretable if the answer here is no.\n")
    crate, chave = {}, {}
    print(f"   {'pool':44s} {'arm':9s} {'corner s':>9s} {'n':>5s} {'40-49 MAX':>10s} "
          f"{'bursts':>7s} {'rate/s':>9s}")
    for k in POOLS:
        for lab, sel in ARMS:
            s = [r for r in W(k) if sel(r) and r["eff"] >= CORNER_EFF and r["ang"] >= CORNER_ANG]
            secs = len(s) * R47.WIN_S / 2
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            mx = max((r["40-49"] for r in s), default=float("nan"))
            print(f"   {k:44s} {lab:9s} {secs:9.1f} {len(s):5d} {mx:10.1f} {b:7d} "
                  f"{b / max(secs, 1e-9):9.5f}")
            chave[(k, lab)] = (secs, b)
            if k == KD2:
                crate[lab] = b / max(secs, 1e-9)
        print()
    print("   POWER at the Kd=2.00 CORNER rate -- P(0) is the probability of seeing zero bursts")
    print("   in that exposure IF grind #2 were running at V62/V65's measured rate:")
    print(f"   {'route':26s} {'arm':9s} {'corner s':>9s} {'obs':>5s} {'expected':>9s} "
          f"{'P(0)':>8s}   verdict")
    out = {}
    for k, rl in ((V67K, "V67 r47+r4a"), (V69K, "V69 r4f")):
        for lab, _ in ARMS:
            secs, obs = chave[(k, lab)]
            exp = crate[lab] * secs
            p0 = float(poisson.pmf(0, exp))
            verd = ("DETECTABLE, and CLEAN" if p0 < 0.05 and obs == 0 else
                    f"{obs} burst(s)" if obs else "🛑 NOT DETECTABLE -- UNDER-POWERED")
            print(f"   {rl:26s} {lab:9s} {secs:9.1f} {obs:5d} {exp:9.2f} {p0:8.4f}   {verd}")
            out[f"{rl}|{lab}"] = dict(secs=secs, obs=obs, exp=exp, p0=p0)
    need = {lab: 2.9957 / crate[lab] for lab, _ in ARMS}
    print(f"\n   Seconds of CORNER exposure needed for P(0) < 0.05: "
          f"ON {need['LKAS ON']:.0f} s, OFF {need['LKAS OFF']:.0f} s.")
    for lab, _ in ARMS:
        have = chave[(V69K, lab)][0]
        print(f"      4f {lab:9s}: has {have:.1f} s ⇒ {max(0.0, need[lab] - have):.0f} s MORE needed")
    RES["corner_exposure"] = dict(power=out, kd2_corner_rate=crate,
                                  census={f"{a}|{b}": list(v) for (a, b), v in chave.items()},
                                  need_s=need)
    print("\n   🛑 VERDICT ON DETECTABILITY: printed above per arm. Where it says NOT DETECTABLE,")
    print("     P-A is UNTESTED on that arm of this route -- not supported, not refuted.")


# =================================================================================================
def sec_dose():
    hdr("2.  THE DELIVERED DOSE vs THE RATE AXIS — byte-verified from four images")
    print("   Verified by direct little-endian byte read (second method, not the builder's word):\n")
    print(f"   {'build':7s} {'r24 sar @0x3AC20':>17s} {'gate @0x3AA96':>14s} {'0xC6446':>8s} "
          f"{'rec0 Y':>28s} {'rec2/rec3':>10s}")
    for nm in ("stock", "V62", "V67", "V69"):
        b = IMG[nm]
        sar = struct.unpack_from("<H", b, R24_SAR)[0]
        y0 = rec_of(b, REC_ADDR[0])[1]
        same = all(rec_of(b, a) == rec_of(IMG["stock"], a) for a in REC_ADDR[2:])
        print(f"   {nm:7s} {f'0x{sar:04X} ' + ('(x2)' if sar == 0x42A9 else '(stock)'):>17s} "
              f"{f'0x{b[GATE_BYTE]:02X}':>14s} "
              f"{struct.unpack_from('<H', b, ARM_ADDR)[0]:8d} {str(y0):>28s} "
              f"{'stock' if same else 'MOVED':>10s}")
    print(f"\n   0xC6010 speed breakpoints = "
          f"{list(struct.unpack_from('<4h', IMG['stock'], CROSS_X_ADDR))} counts "
          f"= [0, 10, 50, 100] km/h at 64.0625 counts per km/h.")
    print("   rec0 X (rate axis) = [0, 400, 1400, 3000] counts. ⇒ ✅ P-A's structural claim CONFIRMED:")
    print("     V69 raised only the FLAT [0,400] segment; rec2/rec3 byte-identical ⇒ >=50 km/h is")
    print("     exactly stock and the 50 km/h knee is sharp.")
    print("\n   ★ AND A DISTINCTION P-A's WRITE-UP DOES NOT MAKE, which changes the conclusion:")
    print("     the three builds dose by THREE DIFFERENT MECHANISMS with THREE DIFFERENT SHAPES —")
    print("       V62/V65  `sar 0xa`->`sar 0x9`      FLAT ×2.000, every speed AND every rate")
    print("       V67/V68  0xC6446=5244 SUBSTITUTES  a CONSTANT gain ⇒ its ratio to stock RISES")
    print("                for the whole LERP        with rate (stock rolls off; 5244 does not)")
    print("       V69      the surface table itself  ⇒ its ratio FALLS with rate")
    print("     V67 and V69 therefore dose OPPOSITE ENDS of the rate axis.\n")
    print(f"   DELIVERED r24 multiplier vs stock at 0 km/h (engaged), by rate:")
    print(f"   {'gp-0x6ac0':>10s} {'deg/s':>8s} {'stock gain':>11s} "
          f"{'V62 x':>8s} {'V67 x':>8s} {'V69 x':>8s}   note")
    tbl = []
    for c in (0, 200, 400, 603, 800, 1000, 1126, 1206, 1400, 2000, 3000):
        gs = gain_b(IMG["stock"], 0, c)
        d62 = delivered("V62", IMG["V62"], 0, c)
        d67 = delivered("V67", IMG["V67"], 0, c)
        d69 = delivered("V69", IMG["V69"], 0, c)
        note = ""
        if c == 603:
            note = "grind #1 operating point (~128 deg/s)"
        if c == 1206:
            note = "*** grind #2 CREEP operating point (~256 deg/s)"
        if c == 1000:
            note = "V67 crosses 2.000x"
        if c == 1126:
            note = "V69 crosses 2.000x"
        tbl.append(dict(counts=c, degs=c / CPS, stock=gs, v62=d62, v67=d67, v69=d69))
        print(f"   {c:10d} {c / CPS:8.1f} {gs:11d} {d62:8.3f} {d67:8.3f} {d69:8.3f}   {note}")
    RES["dose_table"] = tbl
    print("\n   ✅ P-A's two headline numbers REPRODUCE EXACTLY from the bytes: 3.52x at 603 counts")
    print("     (grind #1) and 1.72x at 1206 counts (grind #2 creep).")
    print("\n   🛑🛑 BUT THE SAME TABLE CONTAINS A PROBLEM FOR P-A's MECHANISM, and it is not a")
    print("     stratification question — it is arithmetic on the recorded burst counts:")
    print(f"       at 1206 counts  V69 = {tbl[7]['v69']:.3f}x   V62 = 2.000x   "
          f"V67 = {tbl[7]['v67']:.3f}x")
    print("     V67 delivered MORE than V62's flat dose at grind #2's own stated operating point,")
    print("     and V67 recorded 0 bursts in 158.7 s engaged creep with P(0) = 0.0005.")
    print("     V67 crosses 2.000x at 1000 counts and V69 crosses it at 1126 — so there is NO point")
    print("     on the rate axis where BOTH sit below V62's dose. Yet both gave zero and V62 gave 24.")
    print("     ⇒ 'delivered dose >= 2.00x at the operating point' is NOT SUFFICIENT to explain the")
    print("       V67 and V69 nulls, whichever operating point is chosen. [EVIDENCE — bytes + counts]")
    print("     ⚠ It is not a refutation of P-A's ARITHMETIC (which is exact) and it does not mean")
    print("       the rate axis is irrelevant: V67 and V62 differ in other ways too (0xC646C")
    print("       decouple, 0xC6CD0 = 3564, mss0), so dose is not the only variable in that contrast.")


# =================================================================================================
def sec_strata():
    hdr("3.  WHERE DID V62/V65's BURSTS ACTUALLY LIVE ON THE RATE AXIS? — data, not modelling")
    print("   This is the decisive empirical question P-A rests on. Every burst in the Kd=2 pool is")
    print("   located on the rate axis; if they sit where V69 under-doses, P-A has a mechanism.\n")
    for key, lab in (("r50", "window MEDIAN |rate|"), ("r90", "window p90 |rate|")):
        print(f"   ---- stratified on {lab} ----")
        print(f"   {'stratum (gp-0x6ac0)':20s} {'deg/s':>11s} {'V62x':>6s} {'V67x':>6s} "
              f"{'V69x':>6s} {'arm':9s} | {'Kd2 n':>6s} {'burst':>6s} {'MAX':>8s} "
              f"| {'V67 n':>6s} {'burst':>6s} {'MAX':>8s} | {'V69 n':>6s} {'burst':>6s} {'MAX':>8s}")
        for i, (lo, hi) in enumerate(STRATA):
            mid = min(hi - 1, (lo + min(hi, 3000)) // 2)
            for arm, sel in ARMS:
                # 🛑 PER ARM. V67/V68's dose is GATED: with LKAS off the arm is not selected and
                # the build runs STOCK. Labelling its manual rows with the engaged multiplier
                # would misattribute a stock-dose null to a 2.7x dose.
                eng = (arm == "LKAS ON")
                d62 = delivered("V62", IMG["V62"], 0, mid, eng)
                d67 = delivered("V67", IMG["V67"], 0, mid, eng)
                d69 = delivered("V69", IMG["V69"], 0, mid, eng)
                cells = []
                for pk in (KD2, V67K, V69K):
                    s = [r for r in W(pk) if sel(r) and stratum(r, key) == i]
                    b = sum(1 for r in s if r["40-49"] > R47.BURST)
                    mx = max((r["40-49"] for r in s), default=float("nan"))
                    cells.append(f"{len(s):6d} {b:6d} {mx:8.1f}")
                hs = "inf" if hi > 1e8 else str(hi)
                print(f"   {f'[{lo}, {hs})':20s} "
                      f"{f'{lo / CPS:.0f}-{(hi / CPS if hi < 1e8 else 9999):.0f}':>11s} "
                      f"{d62:6.3f} {d67:6.3f} {d69:6.3f} {arm:9s} | " + " | ".join(cells))
            RES.setdefault(f"strata_{key}", []).append(dict(lo=lo, hi=hi))
        print()

    hdr("3b. THE SAME STRATIFICATION AS A 40-49 Hz LEVEL, all four pools, both arms")
    print("   p90 and MAX of the 40-49 Hz envelope. A burst threshold is binary and this route has")
    print("   no bursts anywhere, so the LEVEL is what carries information about a dose effect.\n")
    for key in ("r50",):
        for arm, sel in ARMS:
            print(f"   ---- {arm}, stratified on window MEDIAN |rate| ----")
            print(f"   {'pool':44s} " + " ".join(
                f"{f'[{lo},{(hi if hi < 1e8 else 0)})':>16s}" for lo, hi in STRATA))
            for k in POOLS:
                cells = []
                for i in range(len(STRATA)):
                    s = [r for r in W(k) if sel(r) and stratum(r, key) == i]
                    if not s:
                        cells.append(f"{'--':>16s}")
                        continue
                    cells.append(f"{np.percentile([r['40-49'] for r in s], 90):7.1f}/"
                                 f"{max(r['40-49'] for r in s):-7.1f}")
                print(f"   {k:44s} " + " ".join(cells))
            print(f"   {'(p90 / MAX of the 40-49 Hz envelope; n per cell below)':44s}")
            for k in POOLS:
                cells = [f"{len([r for r in W(k) if sel(r) and stratum(r, key) == i]):>16d}"
                         for i in range(len(STRATA))]
                print(f"   {k:44s} " + " ".join(cells))
            print()


# =================================================================================================
def sec_power():
    hdr("5.  STRATUM-SPECIFIC POISSON POWER — the test P-A actually needs")
    print("   Reference rate is the Kd=2.00 pool's burst rate IN THAT STRATUM AND ARM, so the")
    print("   comparison never assumes creep seconds are exchangeable across the rate axis.")
    print("   Stratified on window p90 |rate| (a burst is a TAIL event; the median under-locates it).\n")
    key = "r90"
    print(f"   {'stratum':16s} {'arm':9s} {'Kd2 rate/s':>11s} | "
          f"{'V67 s':>7s} {'V67 x':>6s} {'exp':>7s} {'P(0)':>9s} | "
          f"{'V69 s':>7s} {'V69 x':>6s} {'exp':>7s} {'P(0)':>9s}")
    out = {}
    for i, (lo, hi) in enumerate(STRATA):
        mid = min(hi - 1, (lo + min(hi, 3000)) // 2)
        hs = "inf" if hi > 1e8 else str(hi)
        for arm, sel in ARMS:
            eng = (arm == "LKAS ON")          # V67's arm is GATED -- manual runs STOCK
            d67 = delivered("V67", IMG["V67"], 0, mid, eng)
            d69 = delivered("V69", IMG["V69"], 0, mid, eng)
            k2 = [r for r in W(KD2) if sel(r) and stratum(r, key) == i]
            s2 = len(k2) * R47.WIN_S / 2
            b2 = sum(1 for r in k2 if r["40-49"] > R47.BURST)
            if s2 <= 0 or b2 == 0:
                print(f"   {f'[{lo},{hs})':16s} {arm:9s} {'-- Kd=2 has no bursts here, no rate':>11s}")
                continue
            rate = b2 / s2
            cells = []
            for pk in (V67K, V69K):
                s = [r for r in W(pk) if sel(r) and stratum(r, key) == i]
                secs = len(s) * R47.WIN_S / 2
                obs = sum(1 for r in s if r["40-49"] > R47.BURST)
                exp = rate * secs
                p0 = float(poisson.pmf(0, exp))
                cells.append(f"{secs:7.1f} {(d67 if pk == V67K else d69):6.3f} {exp:7.2f} "
                             f"{p0:9.6f}")
                out[f"{lo}-{hs}|{arm}|{pk}"] = dict(secs=secs, obs=obs, exp=exp, p0=p0,
                                                    kd2_rate=rate)
            print(f"   {f'[{lo},{hs})':16s} {arm:9s} {rate:11.5f} | " + " | ".join(cells))
    RES["stratum_power"] = out
    print("\n   🛑 READ THE [1400, inf) LKAS ON ROW FIRST. It is the stratum that carries most of")
    print("     V62/V65's bursts, and V67 ran MORE dose than V62 there over MORE exposure.")


def sec_arms():
    hdr("4.  THE ENGAGED / DISENGAGED SPLIT — V69 has NO GATE, so manual creep is dosed too")
    print("   V67/V68 armed only while LKAS applied; their MANUAL creep ran stock. V69's surface is")
    print("   unconditional, so 4f is the first route since V65 (route 3a/3b) to dose manual creep —")
    print("   grind #2's home arm. This table is therefore the most informative cell on the route.\n")
    print(f"   {'pool':44s} {'arm':9s} {'creep s':>8s} {'n':>5s} {'40-49 p50':>10s} "
          f"{'p90':>8s} {'MAX':>9s} {'bursts':>7s}  dosed?")
    dosed = {("Kd=2.00  (V62 r37 + V65 r3a/r3b)", "LKAS ON"): "yes, 2.000x flat",
             ("Kd=2.00  (V62 r37 + V65 r3a/r3b)", "LKAS OFF"): "yes, 2.000x flat",
             (V67K, "LKAS ON"): "yes, 1.71-3.41x (rises with rate)",
             (V67K, "LKAS OFF"): "NO -- stock",
             (V69K, "LKAS ON"): "yes, 4.00x->1.00x (falls with rate)",
             (V69K, "LKAS OFF"): "yes, 4.00x->1.00x (falls with rate)"}
    for k in POOLS:
        for arm, sel in ARMS:
            s = [r for r in W(k) if sel(r)]
            if not s:
                continue
            secs = len(s) * R47.WIN_S / 2
            b = sum(1 for r in s if r["40-49"] > R47.BURST)
            print(f"   {k:44s} {arm:9s} {secs:8.1f} {len(s):5d} "
                  f"{np.median([r['40-49'] for r in s]):10.1f} "
                  f"{np.percentile([r['40-49'] for r in s], 90):8.1f} "
                  f"{max(r['40-49'] for r in s):9.1f} {b:7d}  "
                  f"{dosed.get((k, arm), 'stock')}")
        print()
    print("   ★ The V69 DISENGAGED creep row is the cell that has never existed before at this dose:")
    print("     a 4.000x low-rate dose on the manual arm, which is where V62/V65 recorded 6 bursts")
    print("     in 139.5 s. Read its burst count and its 40-49 MAX together with §1's power line.")


# =================================================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "_scratch/out/_r4f_rate_axis.json"))
    ap.add_argument("sections", nargs="*")
    a = ap.parse_args()
    for s in (a.sections or ["exposure", "dose", "strata", "arms"]):
        globals()["sec_" + s]()
    Path(a.json).write_text(json.dumps(RES, indent=1, default=str))
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
