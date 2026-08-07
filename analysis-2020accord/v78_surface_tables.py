#!/usr/bin/env python3
"""v78_surface_tables.py -- the byte-exact damper calibration surface, stock / V74 / V75.

PURE PYTHON BYTE WORK. No Ghidra. Every number below comes from an LE read at a stated offset.

Layout (from build_v74_tva.rec_any -- the record's OWN count word drives it, NOT a fixed span):
    [base+0x00] u16 n         [base+2 .. base+2+2n) X[0..n-1] s16 LE
    [base+2+2n .. +4n)        Y[0..n-1] s16 LE      (record length = 4 + 4n)
Pointer arrays are mode-indexed u32 LE absolute addresses (image address == file offset).

Scales, both from the kit's settled record (NOT invented here):
    speed:  64 counts / km-h        (memory/reference-accord-damper-two-deadzones-factorC-factorE,
                                     docs/HANDOFF-2026-07-24 sec 4b -- implemented as x41/64, 64.0625)
    rate :  4.7121 counts / column deg-s
            (.claude/agent-memory/.../reference_accord_gp6abe_column_degps_scale_settled)
"""
import hashlib
import os
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           r"C:\Users\dudei\Desktop\Projects\accord-firmwares")) / "analysis-2020accord"

IMGS = {
    "stock": ROOT / "stock_fw_dump" / "code.bin",
    "V74":   ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "V75":   ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",     # THE FLOWN V75
    "V75r":  ROOT / "_v75_CY0.566_magprobe_plain_image.bin",             # the post-fault re-cut
}

FACTOR_B_PTRS, FACTOR_C_PTRS = 0xC9CCC, 0xC9E9C
FACTOR_D_PTRS, FACTOR_E_PTRS = 0xC9DB4, 0xC9F84
CEILING_PTRS = 0xC77A0
PTR_STRIDE_BETWEEN_ARRAYS = 0xE8

VARIANT_KEY_TABLE, VARIANT_IDX_TABLE, VARIANT_STRIDE, VARIANT_ROWS = 0xCD000, 0xCD012, 0x24, 16
ENGAGED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
THIS_CAR_ROW, THIS_CAR_KEY, THIS_CAR_MODES = 11, "TVCA4", [24, 25, 26, 27]
MANUAL_MODE, LIVE_MODE = 24, 26

SPEED_CTS_PER_KMH = 64.0
RATE_CTS_PER_DEGS = 4.7121
Q10 = 1024
DAMP_WEIGHT_ADDR = 0xC63A0          # V72 LEVER C: tp+0x73A0, one reader @0x381AC, 1024 -> 2048


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec_any(b, base):
    n = u16(b, base)
    assert 1 <= n <= 16, f"record @0x{base:05X} declares count {n}"
    xs = list(struct.unpack_from(f"<{n}h", b, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n))
    return n, xs, ys


def rec_len(b, base):
    return 4 + 4 * u16(b, base)


def deref(b, arr, mode):
    return u32(b, arr + 4 * mode)


def lerp_int(x, xs, ys):
    """The integer LERP the firmware performs inline. CLAMPS to ys[0] below xs[0], ys[-1] above."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for j in range(len(xs) - 1):
        if xs[j] <= x <= xs[j + 1]:
            span = xs[j + 1] - xs[j]
            if span == 0:
                return ys[j]
            return ((ys[j + 1] - ys[j]) * (x - xs[j])) // span + ys[j]
    return ys[-1]


def load():
    out = {}
    for k, p in IMGS.items():
        if not p.exists():
            print(f"  !! MISSING {k}: {p}")
            continue
        raw = p.read_bytes()
        out[k] = raw
        print(f"  {k:6s} {p.name}\n         sha256={hashlib.sha256(raw).hexdigest()}  {len(raw)} B")
    return out


def hdr(t):
    print("\n" + "=" * 108)
    print(t)
    print("=" * 108)


# ---------------------------------------------------------------------------------------------------
def part0_provenance(B):
    hdr("PART 0 -- provenance, mode columns, and the FactorA question")
    st = B["stock"]
    rows = []
    for n in range(VARIANT_ROWS):
        key = bytes(st[VARIANT_KEY_TABLE + n * VARIANT_STRIDE:
                       VARIANT_KEY_TABLE + n * VARIANT_STRIDE + 5]).decode("ascii", "replace")
        m = list(st[VARIANT_IDX_TABLE + n * VARIANT_STRIDE:VARIANT_IDX_TABLE + n * VARIANT_STRIDE + 4])
        rows.append((n, key, m))
    r = rows[THIS_CAR_ROW]
    print(f"  config row {r[0]} key={r[1]!r} modes={r[2]}   (expected {THIS_CAR_KEY} {THIS_CAR_MODES})"
          f"   @0x{VARIANT_KEY_TABLE + THIS_CAR_ROW * VARIANT_STRIDE:X}")
    assert r[1] == THIS_CAR_KEY and r[2] == THIS_CAR_MODES

    print("\n  -- FactorA: is there a 5th mode-indexed pointer array? --")
    print("     known arrays are 0xE8 apart: B 0xC9CCC | D 0xC9DB4 | C 0xC9E9C | E 0xC9F84")
    for cand, label in ((FACTOR_B_PTRS - PTR_STRIDE_BETWEEN_ARRAYS, "one stride BELOW FactorB"),
                        (FACTOR_E_PTRS + PTR_STRIDE_BETWEEN_ARRAYS, "one stride ABOVE FactorE")):
        vals = [u32(st, cand + 4 * m) for m in range(6)]
        plaus = sum(1 for v in vals if 0xD0000 <= v <= 0xDFFFF)
        print(f"     0x{cand:X} ({label}): first6={[hex(v) for v in vals]}"
              f"  -> {plaus}/6 look like record pointers")
    print("     ⇒ see report: 'FactorA' is the SEED gp-0x698a, pinned 1024; NO table exists.")

    print("\n  -- V72 LEVER C, the scalar damper weight downstream of the (C*E)>>10 dose --")
    for k, b in B.items():
        print(f"     {k:6s} 0xC63A0 = {u16(b, DAMP_WEIGHT_ADDR):5d}  (tp+0x73A0; stock 1024)")


# ---------------------------------------------------------------------------------------------------
def part1_full_dump(B, modes):
    hdr("PART 1 -- FULL RECORD DUMP: every factor, every build, per mode. Byte addresses included.")
    factors = (("FactorB", FACTOR_B_PTRS), ("FactorC", FACTOR_C_PTRS),
               ("FactorD", FACTOR_D_PTRS), ("FactorE", FACTOR_E_PTRS),
               ("Ceiling", CEILING_PTRS))
    builds = [k for k in ("stock", "V74", "V75", "V75r") if k in B]
    for name, arr in factors:
        print(f"\n  ##### {name}   pointer array 0x{arr:X} #####")
        for mode in modes:
            ptr_addr = arr + 4 * mode
            base = deref(B["stock"], arr, mode)
            for k in builds:
                assert deref(B[k], arr, mode) == base, f"{k}: {name}[{mode}] pointer MOVED"
            n, _x, _y = rec_any(B["stock"], base)
            L = rec_len(B["stock"], base)
            tag = "ENGAGED" if mode in ENGAGED else ("manual " if mode in DISENGAGED else "  ?    ")
            print(f"\n   mode {mode:2d} [{tag}]  ptr cell 0x{ptr_addr:X} -> record 0x{base:05X}"
                  f"  n={n}  len={L} B  span 0x{base:05X}..0x{base + L - 1:05X}")
            xa = [base + 2 + 2 * i for i in range(n)]
            ya = [base + 2 + 2 * n + 2 * i for i in range(n)]
            print(f"      X byte addrs: {' '.join('0x%05X' % a for a in xa)}")
            print(f"      Y byte addrs: {' '.join('0x%05X' % a for a in ya)}")
            for k in builds:
                _n, xs, ys = rec_any(B[k], base)
                same = bytes(B[k][base:base + L]) == bytes(B["stock"][base:base + L])
                d = []
                if not same:
                    _n0, x0, y0 = rec_any(B["stock"], base)
                    d = [f"X[{i}] {x0[i]}->{xs[i]}" for i in range(n) if x0[i] != xs[i]] + \
                        [f"Y[{i}] {y0[i]}->{ys[i]}" for i in range(n) if y0[i] != ys[i]]
                print(f"      {k:5s} X={str(xs):<30s} Y={str(ys):<30s} "
                      f"{'byte-stock' if same else 'MOVED: ' + ', '.join(d)}")
                print(f"            raw {bytes(B[k][base:base + L]).hex()}")


# ---------------------------------------------------------------------------------------------------
def part1b_blast(B):
    hdr("PART 1b -- BLAST RADIUS: every mode whose FactorB/C/D/E/Ceiling record differs from stock")
    for name, arr in (("FactorB", FACTOR_B_PTRS), ("FactorC", FACTOR_C_PTRS),
                      ("FactorD", FACTOR_D_PTRS), ("FactorE", FACTOR_E_PTRS),
                      ("Ceiling", CEILING_PTRS)):
        for k in ("V74", "V75", "V75r"):
            if k not in B:
                continue
            moved = []
            for mode in range(34):
                base = deref(B["stock"], arr, mode)
                L = rec_len(B["stock"], base)
                if bytes(B[k][base:base + L]) != bytes(B["stock"][base:base + L]):
                    moved.append(mode)
            eng = [m for m in moved if m in ENGAGED]
            dis = [m for m in moved if m in DISENGAGED]
            oth = [m for m in moved if m not in ENGAGED and m not in DISENGAGED]
            print(f"  {name:8s} {k:5s}: {len(moved):2d} modes changed  engaged={eng}"
                  f"  DISENGAGED={dis}  other={oth}")


# ---------------------------------------------------------------------------------------------------
def sidebyside(B, mode):
    hdr(f"PART 1c -- SIDE BY SIDE, mode {mode} "
        f"({'ENGAGED / openpilot' if mode in ENGAGED else 'MANUAL'})")
    builds = [k for k in ("stock", "V74", "V75", "V75r") if k in B]
    for name, arr, xunit in (("FactorC", FACTOR_C_PTRS, "speed"),
                             ("FactorE", FACTOR_E_PTRS, "rate"),
                             ("FactorB", FACTOR_B_PTRS, "torque"),
                             ("FactorD", FACTOR_D_PTRS, "rate"),
                             ("Ceiling", CEILING_PTRS, "backdrive")):
        base = deref(B["stock"], arr, mode)
        n, _x, _y = rec_any(B["stock"], base)
        print(f"\n  {name} @0x{base:05X}  n={n}  X axis = {xunit}")
        cols = "".join(f"  X[{i}]      Y[{i}]   " for i in range(n))
        print(f"    {'build':6s}" + cols)
        for k in builds:
            _n, xs, ys = rec_any(B[k], base)
            cells = "".join(f"  {xs[i]:6d}    {ys[i]:6d}   " for i in range(n))
            print(f"    {k:6s}" + cells)
        if xunit == "speed":
            _n, xs, _y = rec_any(B["stock"], base)
            print("    km/h  " + "".join(f"  {x / SPEED_CTS_PER_KMH:6.1f}             " for x in xs))
        if xunit == "rate":
            for k in builds:
                _n, xs, _y = rec_any(B[k], base)
                print(f"    {k:5s} deg/s " + " ".join(f"{x / RATE_CTS_PER_DEGS:8.2f}" for x in xs))


# ---------------------------------------------------------------------------------------------------
def part2_shape(B, modes):
    hdr("PART 2 -- THE SHAPE PROBLEM: FactorC's dip, and FactorE's X[0]")
    print("\n  (a) FactorC monotonicity, per build, per mode.  A 'dip' = Y[i+1] < Y[i].")
    print(f"  {'mode':>4} {'build':6} {'Y':32} {'dips (idx: drop, at km/h)':50}")
    for mode in modes:
        base = deref(B["stock"], FACTOR_C_PTRS, mode)
        for k in ("stock", "V74", "V75"):
            if k not in B:
                continue
            _n, xs, ys = rec_any(B[k], base)
            dips = [(i + 1, ys[i] - ys[i + 1], xs[i + 1] / SPEED_CTS_PER_KMH)
                    for i in range(len(ys) - 1) if ys[i + 1] < ys[i]]
            s = ", ".join(f"idx{i}: -{d} ({v:.0f} km/h)" for i, d, v in dips) or "none - MONOTONE"
            print(f"  {mode:>4} {k:6} {str(ys):32} {s:50}")

    print("\n  (b) The live mode 26 FactorC curve, sampled on the speed axis (counts -> km/h)")
    base = deref(B["stock"], FACTOR_C_PTRS, LIVE_MODE)
    recs = {k: rec_any(B[k], base)[1:] for k in ("stock", "V74", "V75") if k in B}
    print(f"    {'km/h':>6} {'counts':>7} | " + " ".join(f"{k:>7}" for k in recs))
    for kmh in (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 100, 120, 140, 160):
        v = int(round(kmh * SPEED_CTS_PER_KMH))
        print(f"    {kmh:>6} {v:>7} | " + " ".join(f"{lerp_int(v, *recs[k]):>7}" for k in recs))

    print("\n  (c) FactorE X[0] -- what does 'extend to 0' do?  LERP clamps to Y[0] below X[0].")
    eb = deref(B["stock"], FACTOR_E_PTRS, LIVE_MODE)
    for k in ("stock", "V74", "V75"):
        _n, ex, ey = rec_any(B[k], eb)
        print(f"    {k:6s} X={ex} Y={ey}   X in deg/s = "
              f"{[round(x / RATE_CTS_PER_DEGS, 2) for x in ex]}")
    _n, ex75, ey75 = rec_any(B["V75"], eb)
    ex_ext = [0] + ex75[1:]
    print(f"\n    hypothetical V75 with X[0]:=0 -> X={ex_ext} Y={ey75}")
    print(f"    {'rate ct':>8} {'deg/s':>7} | {'V75 E':>7} {'X0=0 E':>7} {'delta':>7}")
    changed = 0
    for r in (0, 1, 2, 4, 6, 8, 11, 12, 13, 20, 30, 50, 75, 99, 127, 150, 188, 199, 200, 250, 400):
        a = lerp_int(r, ex75, ey75)
        b = lerp_int(r, ex_ext, ey75)
        print(f"    {r:>8} {r / RATE_CTS_PER_DEGS:>7.2f} | {a:>7} {b:>7} {b - a:>+7}")
    for r in range(0, 4001):
        if lerp_int(r, ex75, ey75) != lerp_int(r, ex_ext, ey75):
            changed += 1
    print(f"    ⇒ FactorE differs at {changed} of 4001 integer rate points in [0,4000]"
          f"  ⇒ extending X[0] to 0 is {'NOT a no-op' if changed else 'a NO-OP'}")
    a0, b0 = lerp_int(0, ex75, ey75), lerp_int(0, ex_ext, ey75)
    print(f"    at rate 0 exactly: V75 E={a0}, X0=0 E={b0}  (both {'equal' if a0 == b0 else 'DIFFER'}"
          " -- Y[0]=0 means no step at zero rate either way)")


# ---------------------------------------------------------------------------------------------------
def dose(B, k, mode, v_counts, rate):
    """(C*E)>>10 with B and D asserted flat 1024, then the +/- ceiling clamp. Mirrors FUN_00034350."""
    b = B[k]
    c = lerp_int(v_counts, *rec_any(b, deref(b, FACTOR_C_PTRS, mode))[1:])
    e = lerp_int(rate, *rec_any(b, deref(b, FACTOR_E_PTRS, mode))[1:])
    bb = lerp_int(v_counts, *rec_any(b, deref(b, FACTOR_B_PTRS, mode))[1:])
    dd = lerp_int(rate, *rec_any(b, deref(b, FACTOR_D_PTRS, mode))[1:])
    v = (Q10 * bb) >> 10
    v = (v * c) >> 10
    v = (v * dd) >> 10
    return (v * e) >> 10


def ceiling_floor(B, k, mode):
    b = B[k]
    n, xs, ys = rec_any(b, deref(b, CEILING_PTRS, mode))
    return n, xs, ys


def part3_surface(B, mode):
    hdr(f"PART 3 -- THE 2-D DOSE SURFACE, mode {mode}.  dose = (((1024*B)>>10 *C)>>10 *D)>>10 *E)>>10")
    builds = [k for k in ("stock", "V74", "V75", "V75r") if k in B]
    for k in builds:
        n, xs, ys = ceiling_floor(B, k, mode)
        print(f"   {k:6s} ceiling record: n={n} X={xs} Y={ys}  -> floor {ys[0]}")
    fl = ceiling_floor(B, "stock", mode)[2][0]

    print(f"\n   BEFORE the +/-{fl} clamp. Rows = column deg/s, cols = km/h. STOCK | V74 | V75")
    speeds_kmh = [0, 10, 20, 30, 35, 45, 60]
    rates_degs = [0, 2, 5, 10, 15, 21, 27, 40, 64, 85, 106, 200, 300, 424]
    for k in builds:
        print(f"\n   ---- {k} ----")
        print("   deg/s\\km/h " + " ".join(f"{s:>7}" for s in speeds_kmh))
        for rd in rates_degs:
            r = int(round(rd * RATE_CTS_PER_DEGS))
            row = [dose(B, k, mode, int(round(s * SPEED_CTS_PER_KMH)), r) for s in speeds_kmh]
            print(f"   {rd:>6}({r:>4})" + " ".join(f"{x:>7}" for x in row))

    print(f"\n   PEAK reachable at CREEP (speed 0) and where the {fl} floor binds:")
    for k in builds:
        pk = max(dose(B, k, mode, 0, r) for r in range(0, 4001))
        first = next((r for r in range(0, 4001) if dose(B, k, mode, 0, r) >= fl), None)
        gpk = max(dose(B, k, mode, v, r) for v in range(0, 14001, 64) for r in (0, 4000))
        print(f"     {k:6s} creep peak={pk:4d}  first rate reaching {fl}: "
              f"{first if first is not None else '-- never --'}"
              f"{'' if first is None else f' ct = {first / RATE_CTS_PER_DEGS:.1f} deg/s'}"
              f"   GLOBAL peak over all speeds = {gpk}")


def k_gain(B, k, mode):
    b = B[k]
    _n, cx, cy = rec_any(b, deref(b, FACTOR_C_PTRS, mode))
    _n, ex, ey = rec_any(b, deref(b, FACTOR_E_PTRS, mode))
    M = (cy[0] * ey[1]) >> 10
    M0 = (cy[0] * ey[0]) >> 10
    return cy[0], ex[0], ex[1], ey[0], ey[1], M, (M - M0) / (ex[1] - ex[0])


def part3b_k(B, mode):
    hdr(f"PART 3b -- RAMP-REGIME INCREMENTAL GAIN k, mode {mode}, recomputed FROM THE BYTES")
    print(f"   k = ((C_Y0*E_Y1)>>10 - (C_Y0*E_Y0)>>10) / (E_X1 - E_X0)   [counts of damper per "
          "count of rate]")
    print(f"   {'build':6} {'C_Y0':>6} {'E_X0':>6} {'E_X1':>6} {'E_Y0':>6} {'E_Y1':>6} "
          f"{'M':>6} {'k':>9} {'dB vs V74':>10}")
    kv74 = None
    for k in [x for x in ("stock", "V74", "V75", "V75r") if x in B]:
        cy0, ex0, ex1, ey0, ey1, M, kk = k_gain(B, k, mode)
        if k == "V74":
            kv74 = kk
        db = "--" if not kv74 or kk == 0 else f"{20 * __import__('math').log10(kk / kv74):+.2f}"
        print(f"   {k:6} {cy0:>6} {ex0:>6} {ex1:>6} {ey0:>6} {ey1:>6} {M:>6} {kk:>9.4f} {db:>10}")
    print("   (last session quoted stock 0.0000 / V74 0.5799 / V75 1.5798 -- compare above)")


# ---------------------------------------------------------------------------------------------------
def part5_cap(B, modes):
    hdr("PART 5 -- IS FactorC Y[0] PER-MODE CAPPED?  The constraint, and the REALIZED value per mode")
    print("   CONSTRAINT (build_v75_tva._no_clip_ok): over a 14001x4501-point grid (speed step 32,")
    print("   rate step 20 => 98,988 points), every point the edit RAISES must satisfy")
    print("   dose = (C*E)>>10 <= that mode's OWN ceiling_floor (= its ceiling record's Y[0]).")
    print("   The cap is the LARGEST C_Y0 passing that, found by binary search on [old, 4096].")
    print("   Closed form for the binding corner (speed 0 -> C = C_Y0 ; rate >= E_X[3] -> E = E_Y3):")
    print("       cap = max{c : (c*E_Y3)>>10 <= floor}\n")
    speeds = list(range(0, 14001, 32))
    rates = list(range(0, 4501, 20))
    print(f"   {'mode':>4} {'stockY0':>8} {'V74 Y0':>7} {'V75 Y0':>7} {'E_Y3':>6} {'floor':>6} "
          f"{'cap(closed)':>11} {'cap(search)':>11} {'reached 566?':>12}")
    caps = {}
    for mode in modes:
        cb = deref(B["stock"], FACTOR_C_PTRS, mode)
        eb = deref(B["stock"], FACTOR_E_PTRS, mode)
        y0s = {k: rec_any(B[k], cb)[2][0] for k in ("stock", "V74", "V75") if k in B}
        _n, _ex, ey75 = rec_any(B["V75"], eb)
        floor = ceiling_floor(B, "V75", mode)[2][0]
        closed = max(c for c in range(0, 4097) if (c * ey75[3]) >> 10 <= floor)
        # honest re-run of the binary search on the V75 image (which already carries EX1)
        base_c = [lerp_int(v, *rec_any(B["V74"], cb)[1:]) for v in speeds]
        base_e = [lerp_int(r, *rec_any(B["V74"], eb)[1:]) for r in rates]
        _n, cx, cy = rec_any(B["V75"], cb)
        _n, ex, ey = rec_any(B["V75"], eb)
        es = [lerp_int(r, ex, ey) for r in rates]

        def ok(c0):
            cs = [lerp_int(v, cx, [c0] + cy[1:]) for v in speeds]
            for ci, cbv in zip(cs, base_c):
                for ei, ebv in zip(es, base_e):
                    now = (ci * ei) >> 10
                    if now > ((cbv * ebv) >> 10) and now > floor:
                        return False
            return True

        lo, hi = y0s["V74"], 4096
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if ok(mid):
                lo = mid
            else:
                hi = mid - 1
        caps[mode] = lo
        print(f"   {mode:>4} {y0s['stock']:>8} {y0s['V74']:>7} {y0s['V75']:>7} {ey75[3]:>6} "
              f"{floor:>6} {closed:>11} {lo:>11} "
              f"{'YES' if y0s['V75'] == 566 else 'no (' + str(y0s['V75']) + ')':>12}")
    return caps


def main():
    hdr("v78 -- IMAGES READ (sha256 of every file used)")
    B = load()
    part0_provenance(B)
    part1_full_dump(B, (MANUAL_MODE, LIVE_MODE))
    part1b_blast(B)
    sidebyside(B, LIVE_MODE)
    sidebyside(B, MANUAL_MODE)
    part2_shape(B, (MANUAL_MODE, LIVE_MODE))
    part3_surface(B, LIVE_MODE)
    part3_surface(B, MANUAL_MODE)
    part3b_k(B, LIVE_MODE)
    part5_cap(B, ENGAGED)


if __name__ == "__main__":
    main()
