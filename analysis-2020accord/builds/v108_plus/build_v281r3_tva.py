# -*- coding: utf-8 -*-
r"""V281 rev 3 -- V280 rev 2 + the LKAS rate-PID Kp LERP COMPLETELY FLAT at Y[0] (demand index 0's value).  Cal-only.
Map, clamp, tap, Kd byte-identical to V280 rev 2.

=== OPERATOR DECISION (2026-09-03, verbatim) ====================================================
  "I want Kp on the LKAS PID completely flat, flattened to demand index 0's value."

=== REV 3 ======================================================================================
Rev 1 (image e27f12de...) capped the KNOTS at 341 with X untouched (defect: Kp fell on idx 1..67 too).  Rev 2 (image 4c437e3b...)
re-knotted per record and flattened at 341 from each record's own knee.  Both are SUPERSEDED-DO-NOT-FLASH, kept on disk under
those names; their hashes are cross-image checks below.
REV 3 IS THE SIMPLEST POSSIBLE EDIT: on every one of the 28 records reachable from the Kp pointer bank 0xCB994,
  Y[1] = Y[2] = Y[3] = Y[4] = Y[0].   X, n, the leading 0 knot, the trailing pad: UNTOUCHED.
With every Y equal, the firmware's integer LERP  Y[k] + (Y[k+1]-Y[k])*(i-X[k])//(X[k+1]-X[k])  is Y[0] at every idx 0..240 on
every record, exactly -- no knee, no floor-rounding residue, no per-record special case (asserted for all 241 idx x 28 records).
Diff from the base: 4 u16 per record x 28 = 112 cells spanning 224 bytes, of which 198 BYTES actually differ (26 cells share their low
byte with Y[0], e.g. slots 0/4: 461 = 0x01CD -> 205 = 0x00CD); asserted per byte from the base, plus CRC trailers.

=== THE RECORD LAYOUT, CONFIRMED FROM THE BYTES (not from a brief) =============================
Slot 7 @0xE5378 on V280 rev 2, 12 LE u16 words, 24-byte stride between consecutive records:
    05 00 | 00 00  44 00  70 00  88 00  d0 00 | f8 00  00 02  85 02  b8 02  b8 02 | 00 00
    n = 5 | knots X = 0, 68, 112, 136, 208     | Y = 248, 512, 645, 696, 696       | pad
The Y words are at p+12 .. p+20 whether one names word[1] "lo_th" and word[5] "hi_th" (adversary A's walker reading) or X[0..4]
(this kit's mirror): the SAME five words, and this build touches only words 7..10 (Y[1..4]).  NOTE for the record: there is NO
separate duplicated-208 word in the bytes -- 24 bytes = n + 5 knot words + 5 Y words + 1 pad word.

=== WHY (sizing) ================================================================================
Sizing: analysis-2020accord/studies/v280/KPFLAT-SIZING-2026-09-03.md (subagent `kpflat`).  The doc's own flat-248 = Kp(0) row:
  margins (plant fit 1; fits 2-3 within a few deg):  |L| @4/6/7/8/10 Hz 2.38 1.39 1.12 0.92 0.66 ; phase @7 Hz -149 deg ;
    PM 27 deg @ 7.6 Hz ; GM 2.00x @ 12.0 Hz ; Ms 2.9.   Headline 0.3 quotes it as "PM 27-30 deg, GM 2.0-2.2x" across the fits,
    and notes flat 248 is the FIRST value that also clears the idx-26 episode class (K_eff 225 -- 248 is above it, but the linear
    margin there is PM 27 deg vs the as-is 10 deg).  K_crit ~ 425 (two methods); 248 sits at 0.58 x K_crit.
  authority cost, the doc's own rows (line map, clamp 46080, P-only steady state, 247 counts of E per deg/s):
    P-rail error            22.9 -> 64.2 deg/s   (= 15360*256/248 / 247; recomputed below from the chain arithmetic)
    full push only below   110.8 -> 69.5 deg/s
    full-demand rate under load 600/1000/1500/2472 counts:  128.1/124.3/119.7/110.8  ->  118.0/107.6/94.5/69.5  (-8 / -13 / -21 / -37 %)
    hands-light full-demand rate (measured p50 125 at ~690-count load): predicted ~ -8 %   [BELIEF: the chain's DC arithmetic]
    STALLED wheel (rate 0), delivered T by idx, as-is -> flat 248:
       idx 26: 781 -> 555 (-29 %) ; 40: 1392 -> 856 (-39 %) ; 58: 2364 -> 1239 (-48 %) ; 68: 2462 -> 1452 (-41 %) ;
       80: 2462 -> 1709 (-31 %) ; 100: 2462 -> 2137 (-13 %) ; >= 120: 2462 (rail) unchanged.
    Full stalled push arrives from idx ~ 120 instead of ~ 58.  The doc's summary: "-25...-48 % stall authority" at idx 26-80.
  THE HIGHWAY BAND IS NO LONGER INERT (unlike rev 2): the lane-change regime runs at idx 2-12 (LOWCMD A4) where V280 rev 2's Kp
    is 255 (idx 2) .. 294 (idx 12); rev 3 reads 248 there: -3 % at idx 2, -16 % at idx 12.  Inner loop only -- the reference
    (the map) is untouched.  [EVIDENCE: the integer LERP evaluated on both images, printed below]

=== THE CELLS ==================================================================================
  [A] Kp LERP records via the pointer bank 0xCB994 (28 u32 LE pointers, 28 DISTINCT records).  Y[1..4] := Y[0] on every record.
      Slot 7 (live, record 11 TVCA4) @0xE5378:  Y 248, 512, 645, 696, 696  ->  248, 248, 248, 248, 248 ; X 0, 68, 112, 136, 208 kept.
      Per-slot Y[0]: slots 0/4: 205 ; 1/6: 266 ; 2/5: 205 ; 3/7: 248 ; 8/9: 248 ; dead 10-27: 307.
  Nothing else: map family 0xC9A88, 0xC62E6 (46080), the 0x55DF0-0x55E11 tap window, the Kd family 0xCB7D4, the tapers, the frozen
  torque path, the whole code region 0x13000-0xC0000 -- all byte-identical to V280 rev 2 (asserted by cross-image compare).

=== THE INSTRUMENT (already on the wire in this build) =========================================
  CAN-427 field ((b0&3)<<8)|b1 = (sign(T)<<9) | (|T|>>3), T = gp-0x6b38, the delivered lane torque (V278 rev 3 tap, unchanged).
  PRE-REGISTERED READ, same frames as the V280 rev 2 read (|angle| >= 30 deg, idx >= 68, v <= 10 m/s, >= 1 s runs):
    (i)  T 6-8.5 Hz amplitude / |T| p50 (V280 rev 2 reads 0.42-0.99 in-episode; PASS <= 0.25 median, FAIL >= 0.4).
    (ii) 0x18F driver-torque 6-8.5 Hz ring amplitude.   (iii) 7 Hz episodes per 100 s of high-angle engaged time (V280: 5.3; PASS <= 2, FAIL >= 4).
    Cost read: sustained full-demand hands-light rate p50 (predicted ~ -8 %; FAIL if < 105 deg/s); stalled-wheel |T| at idx 40-80
    (predicted -31...-48 %); and the highway band's lane-change feel (idx 2-12 now -3...-16 % of Kp).
  FAIL sentences: the 7 Hz line persists at the same ripple/level with Kp verified 248 in the image ==> the line is NOT the inner
  loop's P-path limit cycle; next lever is the fb pole (0xC63E8/EA), not more Kp.  The r31-class stall stutter returning at idx
  40-80 ==> the stall-authority cost is the binding constraint (the doc's fb-pole companion is the next sizing).

=== RISK, PLAINLY ==============================================================================
Authority goes DOWN, never up: P = E * Kp >> 8 with Kp = Y[0] (248 live) instead of up to 696 (-64 % of P at idx >= 136 for the same E).
Kp(idx) <= V280 rev 2 at every idx on every record (asserted).  The lane keeps the sign of E (every Y > 0, asserted).  The P clamp,
sum clamp, gain, override cliff, EME -- byte-identical.  Cal-only; no code byte changes (asserted: 0x13000-0xC0000 identical).

=== CLASS OF BUILD =============================================================================
The FIRST edit of the inner-loop gain bank to fly (the Kp bank has NEVER flown edited: V275 /6 withdrawn, V279 unflown, V281 rev 1/2
superseded unflown).  V276/V278/V280 moved the REFERENCE (the map); V281 rev 3 leaves the reference where V280 rev 2 put it and
makes the inner loop's proportional gain demand-independent at its lowest tabled value.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V281_WRITE", "").strip().lower()

BASE_NAME = "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
BASE_SHA = "b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa"
TAG = "V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
REV1_IMAGE = "SUPERSEDED_v281_rev1_KNOTCAP_plain_image.bin"
REV1_SHA = "e27f12dea6af1b7bc597c3eff79144b0d1d2f570e97c1b9ae1ae293e57b306fb"
REV2_IMAGE = "SUPERSEDED_v281_rev2_FLAT341_plain_image.bin"
REV2_SHA = "4c437e3be49ccdd416f8d32c6621c640d8386c7200c6ab7c642a0136cb250a37"
REV2_CAP, REV2_LIVE_X = 341, (0, 24, 68, 136, 208)

# ---- [A] the Kp bank -------------------------------------------------------------------------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
REC_STRIDE = 24
LIVE_SLOT = 7                                           # record 11 TVCA4 -- on the wire, 35 = 7x5
LIVE_KP_REC = 0xE5378
LIVE_KP_X, LIVE_KP_Y = (0, 68, 112, 136, 208), (248, 512, 645, 696, 696)
LIVE_KP_WORDS = (5, 0, 68, 112, 136, 208, 248, 512, 645, 696, 696, 0)
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)
PRINT_IDX = (0, 2, 12, 24, 58, 68, 100, 136, 240)

# ---- the chain arithmetic behind the cost numbers (from the kpflat sizing; recomputed, not quoted) --------
P_CLAMP = 15360                      # 0xC61BC/BE
E_PER_DEGS = 247.0                   # counts of E per deg/s (kpflat sizing sec. 3)

# ---- everything that must NOT move, compared against the BASE IMAGE (not restated) -----------
MAP_PTR, MAP_N = 0xC9A88, 10
FB_CELL, FB_V280 = 0xC62E6, 46080
PACK_LO, PACK_HI = 0x55DF0, 0x55E12
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,
    0xC61B6: 10240,  0xC61BA: 10240,
    0xC61BC: 15360,  0xC61BE: 15360,
    0xC63E6: 0,
    0xC63E8: 923,    0xC63EA: 1560,
    0xC63EC: 992,    0xC63EE: 507,
    0xC62E4: 4,
    0xC6B26: 256,    0xC6B12: 98,
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
}
CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E

OK, BAD = "[PASS]", "[FAIL]"
# assertion census: S = substantive (could fail on a wrong edit), V = vacuous (entailed by the base sha256),
# T = tautological (readback of a value just written by this script)
_census = {"S": 0, "V": 0, "T": 0}
_checks = [0, 0]


def check(cond, msg, kind="S"):
    assert kind in _census
    _checks[0] += 1
    _census[kind] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} [{kind}] {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def words(b, p, k=12):
    return tuple(u16(b, p + 2 * i) for i in range(k))


def rec_span(b, p):
    n = u16(b, p)
    return set(range(p, p + 2 + 4 * n))


def y_off(p, n, k):
    return p + 2 + 2 * n + 2 * k


def lerp(X, Y, i):
    """The firmware's integer LERP as mirrored in the V280 script (floor division)."""
    if i <= X[0]:
        return Y[0]
    if i >= X[-1]:
        return Y[-1]
    for k in range(len(X) - 1):
        if X[k] <= i < X[k + 1]:
            return Y[k] + (Y[k + 1] - Y[k]) * (i - X[k]) // (X[k + 1] - X[k])


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def independent_rebuild(base):
    """A second, minimal implementation with none of build()'s bookkeeping: Y[1..4] = Y[0], then re-CRC every 4 KB block touched."""
    img = bytearray(base)
    touched = set()
    for s in range(N_SLOTS):
        p = u32(img, KP_PTR + 4 * s)
        n = u16(img, p)
        assert n == 5
        y0 = u16(img, p + 2 + 2 * n)
        for k in range(1, n):
            oy = p + 2 + 2 * n + 2 * k
            if u16(img, oy) != y0:
                struct.pack_into("<H", img, oy, y0)
                touched.add(oy)
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 102)
    print("  V281 rev 3 -- Kp COMPLETELY FLAT at Y[0] (Y[1..4] := Y[0], X untouched) on every record of 0xCB994.  Base V280 rev 2.")
    print("  Map/clamp/tap/Kd byte-identical.  Operator: 'I want Kp on the LKAS PID completely flat, flattened to demand index 0's value.'")
    print("=" * 102)

    print("\n  [1] BASE = V280 rev 2")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V280 rev 2 base sha256 matches", "S")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    check(u16(base, FB_CELL) == FB_V280, f"base 0xC62E6 == {FB_V280} (V280 rev 2's clamp)", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and n7 == 5 and tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y,
          f"base live Kp slot {LIVE_SLOT} @0x{LIVE_KP_REC:05X}: X {LIVE_KP_X} Y {LIVE_KP_Y}", "V")
    nd, Xd, Yd = rec(base, u32(base, KD_PTR + 4 * LIVE_SLOT))
    check(u32(base, KD_PTR + 4 * LIVE_SLOT) == LIVE_KD_REC and nd == 4 and tuple(Yd) == LIVE_KD_Y,
          f"base live Kd slot {LIVE_SLOT} @0x{LIVE_KD_REC:05X}: 4 knots, Y {LIVE_KD_Y}", "V")

    print("\n  [1b] THE RECORD LAYOUT, READ FROM THE BYTES of slot 7 @0xE5378 (24-byte stride)")
    w7 = words(base, LIVE_KP_REC)
    print(f"      words: {w7}")
    print(f"      bytes: {bytes(base[LIVE_KP_REC:LIVE_KP_REC + 24]).hex(' ')}")
    check(w7 == LIVE_KP_WORDS, "slot 7 = n 5 | knots 0 68 112 136 208 | Y 248 512 645 696 696 | pad 0  (12 words, 24 bytes)", "V")
    check(w7[5] == 208 and w7[6] == 248 and w7[11] == 0, "word[5] is the last knot 208, word[6] is Y[0] = 248, word[11] is the pad: NO duplicated-208 word exists", "V")
    check(u32(base, KP_PTR + 4 * 8) - LIVE_KP_REC == REC_STRIDE and LIVE_KP_REC - u32(base, KP_PTR + 4 * 6) == REC_STRIDE, "slots 6/7/8 are 24 bytes apart (the record stride)", "V")
    check(y_off(LIVE_KP_REC, 5, 0) == LIVE_KP_REC + 12, "Y[0] offset p+12 -- the same word under either naming of the knot words", "V")

    print("\n  [2] THE Kp POINTER FAMILY, WALKED FROM THE IMAGE")
    kp_ptrs_by_slot = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    kp_ptrs = sorted(set(kp_ptrs_by_slot))
    check(all(START <= p < END for p in kp_ptrs), f"all {len(kp_ptrs)} Kp pointers in [0x13000, 0x100000)", "V")
    print(f"      {N_SLOTS} pointers -> {len(kp_ptrs)} distinct records" +
          ("" if len(kp_ptrs) == N_SLOTS else "  (SHARED records exist -- flattened once each)"))
    spans = {}
    for p in kp_ptrs:
        n = u16(base, p)
        check(1 <= n <= 16, f"Kp 0x{p:05X} n = {n} is a sane knot count", "V")
        spans[p] = rec_span(base, p)
    kd_ptrs = sorted({u32(base, KD_PTR + 4 * s) for s in range(N_SLOTS)})
    kd_span = set()
    for p in kd_ptrs:
        kd_span |= rec_span(base, p)
    all_kp = set()
    for p in kp_ptrs:
        check(not (spans[p] & all_kp), f"Kp 0x{p:05X} does not overlap another Kp record", "V")
        all_kp |= spans[p]
    check(not (all_kp & kd_span), "no Kp record overlaps a Kd record", "V")
    check(not (all_kp & set(range(KP_PTR, KP_PTR + 4 * N_SLOTS))) and not (all_kp & set(range(KD_PTR, KD_PTR + 4 * N_SLOTS))),
          "no Kp record overlaps either pointer bank", "V")
    for p in kp_ptrs:
        n, X, Y = rec(base, p)
        check(all(X[i + 1] > X[i] for i in range(n - 1)), f"Kp 0x{p:05X} X strictly increasing (a LERP record, not something else)", "V")
        check(all(0 < y < 4096 for y in Y), f"Kp 0x{p:05X} every Y in (0, 4096) -- gain-sized, all positive", "V")
        check(Y[0] == min(Y), f"Kp 0x{p:05X} Y[0] = {Y[0]} is the record's MINIMUM (flattening to it never raises Kp anywhere)", "V")

    # ------------------------------------------------------------------------------------------
    print("\n  [3] [A] FLATTEN: Y[1..4] := Y[0] on every record; X, n, pad untouched")
    code = bytearray(base)
    attributed = set()
    exp_cells = exp_bytes = 0
    for p in kp_ptrs:
        n, X, Y = rec(base, p)
        for k in range(1, n):
            if Y[k] != Y[0]:
                exp_cells += 1
                exp_bytes += sum(1 for j in (0, 1) if struct.pack("<H", Y[k])[j] != struct.pack("<H", Y[0])[j])
    print(f"      from the base: {exp_cells} u16 cells change on {len(kp_ptrs)} records -> {exp_bytes} bytes will differ")
    table = {}
    for p in kp_ptrs:
        bn, bX, bY = rec(base, p)
        check(bn == 5, f"Kp 0x{p:05X} n == 5", "V")
        for k in range(1, bn):
            if bY[k] != bY[0]:
                oy = y_off(p, bn, k)
                struct.pack_into("<H", code, oy, bY[0]); attributed |= {oy, oy + 1}
        n2, X2, Y2 = rec(code, p)
        check(n2 == bn == 5 and u16(code, p) == u16(base, p), f"Kp 0x{p:05X} n untouched", "S")
        check(X2 == bX, f"Kp 0x{p:05X} X == {bX} UNTOUCHED (the knot axis is not this build's business)", "S")
        check(u16(code, p + 22) == u16(base, p + 22), f"Kp 0x{p:05X} pad word untouched", "S")
        check(Y2 == [bY[0]] * 5, f"Kp 0x{p:05X} Y == {bY[0]} x5  (was {bY})", "S")
        check(0 < Y2[0] == bY[0], f"Kp 0x{p:05X} Y[0] = {bY[0]} untouched and > 0 -- the lane keeps the sign of E", "S")
        L0 = [lerp(bX, bY, i) for i in range(241)]
        L1 = [lerp(X2, Y2, i) for i in range(241)]
        check(all(L1[i] == bY[0] for i in range(241)), f"Kp 0x{p:05X} LERP (floor form) == {bY[0]} at EVERY idx 0..240", "S")
        check(all(L1[i] <= L0[i] for i in range(241)), f"Kp 0x{p:05X} LERP <= V280 rev 2 at every idx 0..240", "S")
        check(L1[0] == L0[0], f"Kp 0x{p:05X} LERP identical at idx 0", "S")
        check(all(L1[i] < L0[i] for i in range(1, 241)), f"Kp 0x{p:05X} LERP strictly BELOW V280 rev 2 at every idx 1..240", "S")
        slots_here = [s for s in range(N_SLOTS) if kp_ptrs_by_slot[s] == p]
        table.setdefault((tuple(bX), tuple(bY), tuple(Y2)), []).append(slots_here)
    print("\n      per-slot before/after (records grouped by identical X/Y):")
    for (bX, bY, nY), slots in table.items():
        sl = sorted(x for g in slots for x in g)
        print(f"        slots {sl}: X {list(bX)} (kept)   Y {list(bY)} -> {list(nY)}")
    print("\n      per-slot Y table (all 28):")
    for s in range(N_SLOTS):
        p = kp_ptrs_by_slot[s]
        print(f"        slot {s:2d} @0x{p:05X}  Y {rec(base, p)[2]} -> {rec(code, p)[2]}" + ("   <-- LIVE" if s == LIVE_SLOT else "") + ("   (dead slot)" if s >= 10 else ""))
    changed_cells = sum(1 for p in kp_ptrs for k in range(5) for (a, b) in ((u16(base, p + 2 + 2 * k), u16(code, p + 2 + 2 * k)), (u16(base, y_off(p, 5, k)), u16(code, y_off(p, 5, k)))) if a != b)
    check(changed_cells == exp_cells == 4 * 28, f"changed u16 cells {changed_cells} == {exp_cells} == 4 x 28 (computed from the base)", "S")
    changed_bytes = sum(1 for p in kp_ptrs for o in rec_span(base, p) if code[o] != base[o])
    check(changed_bytes == exp_bytes, f"changed Kp-record bytes {changed_bytes} == {exp_bytes} (computed from the base, per byte)", "S")
    check(len(kp_ptrs) == N_SLOTS == 28 and all(all(y > rec(base, p)[2][0] for y in rec(base, p)[2][1:]) for p in kp_ptrs),
          "all 28 records carried every Y[1..4] above Y[0] -- none passed through unchanged", "S")
    check(bytes(code[KP_PTR:KP_PTR + 4 * N_SLOTS]) == bytes(base[KP_PTR:KP_PTR + 4 * N_SLOTS]), "the pointer bank 0xCB994 itself is untouched (the edit is in the DATA)", "S")

    print(f"\n      LIVE slot {LIVE_SLOT} Kp LERP (integer, floor) at idx {PRINT_IDX}:")
    _, lX, lY = rec(code, kp_ptrs_by_slot[LIVE_SLOT])
    _, bX7, bY7 = rec(base, kp_ptrs_by_slot[LIVE_SLOT])
    r2X, r2Y = REV2_LIVE_X, (248, 341, 341, 341, 341)          # re-read from the rev 2 image in [8b] below
    print(f"        idx     : " + "".join(f"{i:>6d}" for i in PRINT_IDX))
    print(f"        V280 r2 : " + "".join(f"{lerp(bX7, bY7, i):>6d}" for i in PRINT_IDX))
    print(f"        V281 r2 : " + "".join(f"{lerp(r2X, r2Y, i):>6d}" for i in PRINT_IDX))
    print(f"        V281 r3 : " + "".join(f"{lerp(lX, lY, i):>6d}" for i in PRINT_IDX))
    print(f"        r3/V280 : " + "".join(f"{lerp(lX, lY, i) / lerp(bX7, bY7, i):>6.3f}" for i in PRINT_IDX))
    check(tuple(lX) == LIVE_KP_X and tuple(lY) == (248,) * 5, f"LIVE slot {LIVE_SLOT} X == {LIVE_KP_X} (kept), Y == 248 x5", "S")
    check(all(lerp(lX, lY, i) == 248 for i in range(241)), "live LERP == 248 at every idx 0..240", "S")
    check(lerp(bX7, bY7, 2) == 255 and lerp(bX7, bY7, 12) == 294 and lerp(bX7, bY7, 24) == 341 and lerp(bX7, bY7, 58) == 473 and lerp(bX7, bY7, 136) == 696,
          "V280 rev 2 live LERP reads 255 @2, 294 @12, 341 @24, 473 @58, 696 @136 (the numbers this build is scored against)", "V")
    print(f"        highway band idx 2..12: V280 rev 2 {lerp(bX7, bY7, 2)}..{lerp(bX7, bY7, 12)}  ->  rev 3 248  ({100 * (248 / lerp(bX7, bY7, 2) - 1):+.1f} % .. {100 * (248 / lerp(bX7, bY7, 12) - 1):+.1f} %)")
    print(f"        idx 58 (stall class): {lerp(bX7, bY7, 58)} -> 248 ({100 * (248 / lerp(bX7, bY7, 58) - 1):+.1f} %);  idx >= 136: 696 -> 248 ({100 * (248 / 696 - 1):+.1f} %)")

    print("\n  [3b] THE FLAT-248 COST, from the chain arithmetic (kpflat sizing sec. 3; P = E*Kp>>8, clamp 15360, 247 counts of E per deg/s)")
    for kp, tag in ((696, "as-is top"), (341, "rev 2 flat"), (248, "rev 3 flat")):
        e_rail = P_CLAMP * 256 / kp
        print(f"        Kp {kp:3d} ({tag:10s}): P rails at |E| = {e_rail:7.1f} counts = {e_rail / E_PER_DEGS:5.1f} deg/s of rate error")
    e248 = P_CLAMP * 256 / 248 / E_PER_DEGS
    check(abs(e248 - 64.2) < 0.1, f"flat-248 P-rail error {e248:.1f} deg/s == the sizing doc's 64.2", "S")
    print("        sizing-doc rows for flat 248 (its own chain, line map, clamp 46080): full push only below 69.5 deg/s (as-is 110.8);")
    print("          full-demand rate under 600/1000/1500/2472-count load 118.0/107.6/94.5/69.5 (as-is 128.1/124.3/119.7/110.8; -8/-13/-21/-37 %);")
    print("          STALLED wheel T: idx 26 781->555, 40 1392->856, 58 2364->1239 (-48 %), 68 2462->1452, 80 2462->1709, 100 2462->2137, >=120 2462 (rail);")
    print("          margins: PM 27 deg @7.6 Hz, GM 2.00x @12.0 Hz, Ms 2.9 (fit 1; 'PM 27-30, GM 2.0-2.2x' over the three fits).")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] EVERYTHING ELSE BYTE-IDENTICAL TO V280 rev 2 -- compared against the base image")
    check(bytes(code[0x13000:0xC0000]) == bytes(base[0x13000:0xC0000]), "code region 0x13000-0xC0000 byte-identical (cal-only build)", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), "tap window 0x55DF0-0x55E11 byte-identical", "S")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]) and bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "V112 cave + hook byte-identical", "S")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]), "FUN_00028ea6 (the PID) byte-identical", "S")
    check(u16(code, FB_CELL) == u16(base, FB_CELL) == FB_V280, f"0xC62E6 == base == {FB_V280}", "S")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == u16(base, a_) == v, f"0x{a_:05X} == base == {v}", "S")
    map_ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    for p in map_ptrs:
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]), f"map 0x{p:05X} byte-identical", "S")
    check(bytes(code[MAP_PTR:MAP_PTR + 4 * N_SLOTS]) == bytes(base[MAP_PTR:MAP_PTR + 4 * N_SLOTS]), "map pointer bank byte-identical", "S")
    live_map = u32(base, MAP_PTR + 4 * LIVE_SLOT)
    check(rec(code, live_map)[2] == [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], "live map == V280 rev 2's straight line (read from the built image)", "S")
    for s in range(N_SLOTS):
        p = u32(base, KD_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kd slot {s} @0x{p:05X} byte-identical", "S")
    check(bytes(code[KD_PTR:KD_PTR + 4 * N_SLOTS]) == bytes(base[KD_PTR:KD_PTR + 4 * N_SLOTS]), "Kd pointer bank byte-identical", "S")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [5] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}", "S")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved (the block carries an edit)", "S")
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    print("\n  [6] FULL BYTE DIFF vs V280 rev 2 -- every changed run listed")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed", "S")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set()
    for p in kp_ptrs:
        n = u16(base, p)
        allow |= {y_off(p, n, k) + j for k in range(1, n) for j in (0, 1)}
    check(set(pay) <= allow, "every payload byte is a Kp Y[1..4] cell", "S")
    check(all(rec(code, p)[1] == rec(base, p)[1] and u16(code, p) == 5 for p in kp_ptrs), "n and every X untouched on every record", "S")
    check(len(pay) == exp_bytes, f"payload byte count {len(pay)} == {exp_bytes} computed from the base", "S")
    span = {y_off(p, 5, k) + j for p in kp_ptrs for k in range(1, 5) for j in (0, 1)}
    same = sorted(span - set(pay))
    check(len(span) == 224 and len(pay) + len(same) == 224,
          f"the 112 edited u16 cells span 224 bytes; {len(pay)} differ, {len(same)} are byte-equal to the base (a Y[k] sharing a byte with Y[0], e.g. 0x01CD -> 0x00CD)", "S")
    check(all(x >= 0xC0000 for x in pay), "no code byte changed", "S")
    trailer_bytes = [x for x in diff if (x & 0xFFF) >= 0xFFC]
    check(len(trailer_bytes) == 4 * len(blocks), f"{len(trailer_bytes)} trailer bytes == 4 x {len(blocks)} blocks", "S")
    for s, e in runs(diff):
        kind = "CRC trailer" if (s & 0xFFF) >= 0xFFC else "Kp Y[1..4]"
        owner = [sl for sl in range(N_SLOTS) if s in rec_span(base, kp_ptrs_by_slot[sl])] if kind == "Kp Y[1..4]" else []
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {kind}" + (f"  slot {owner}" if owner else "") +
              f"  {bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")
    print(f"      {len(pay)} payload bytes, 0 code, {len(blocks)} CRC trailers, {len(diff)} bytes total")

    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V281 rev 3 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN EXISTS -- the non-circular cipher test is REACHABLE", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    print("\n  [8] END STATE -- every edited record re-read from the FINAL image and from the DECODED .rwd")
    for nm, im in (("code", code), ("dec", dec)):
        for s in range(N_SLOTS):
            p = u32(im, KP_PTR + 4 * s)
            n, X, Y = rec(im, p)
            bn, bX, bY = rec(base, u32(base, KP_PTR + 4 * s))
            check(p == u32(base, KP_PTR + 4 * s) and n == bn == 5 and X == bX and Y == [bY[0]] * 5,
                  f"{nm}: Kp slot {s:2d} @0x{p:05X} X == {X} Y == {Y}", "T" if nm == "code" else "S")
        check(words(im, LIVE_KP_REC) == (5, 0, 68, 112, 136, 208, 248, 248, 248, 248, 248, 0), f"{nm}: live record words == 5 | 0 68 112 136 208 | 248 x5 | 0", "T" if nm == "code" else "S")
        check(tuple(rec(im, u32(im, KD_PTR + 4 * LIVE_SLOT))[2]) == LIVE_KD_Y, f"{nm}: live Kd == 128 x 4", "S")
        check(u16(im, FB_CELL) == FB_V280, f"{nm}: 0xC62E6 == {FB_V280}", "S")
        check(rec(im, u32(im, MAP_PTR + 4 * LIVE_SLOT))[2] == [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], f"{nm}: live map == the straight line", "S")
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: tap window == V280 rev 2", "S")
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}", "S")

    print("\n  [8b] CROSS-IMAGE vs V281 rev 1 (knot cap) and rev 2 (flat 341 from the knee) -- both SUPERSEDED, read from THOSE images")
    rev1 = Path(plain_image_path(REV1_IMAGE)).read_bytes()
    rev2 = Path(plain_image_path(REV2_IMAGE)).read_bytes()
    check(hashlib.sha256(rev1).hexdigest() == REV1_SHA, "V281 rev 1 image sha256 matches the reported hash", "S")
    check(hashlib.sha256(rev2).hexdigest() == REV2_SHA, "V281 rev 2 image sha256 matches the reported hash", "S")
    allow_y = {y_off(p, 5, k) + j for p in kp_ptrs for k in range(1, 5) for j in (0, 1)}
    allow_x = {p + 2 + 2 * k + j for p in kp_ptrs for k in range(1, 5) for j in (0, 1)}
    for nm, im, allow_set, what in (("rev 1", rev1, allow_y, "a Kp Y[1..4] cell"), ("rev 2", rev2, allow_y | allow_x, "a Kp X[1..4] or Y[1..4] cell")):
        d = [x for x in range(START, END) if code[x] != im[x] and (x & 0xFFF) < 0xFFC]
        check(d and set(d) <= allow_set, f"vs {nm}: every payload difference is {what} ({len(d)} bytes); map, clamp, tap, Kd, code identical", "S")
        check(not [x for x in range(0x13000, 0xC0000) if code[x] != im[x]], f"vs {nm}: no code byte differs", "S")
        check(all(rec(im, p)[2][0] == rec(code, p)[2][0] for p in kp_ptrs), f"vs {nm}: every record's Y[0] is identical", "S")
        check(all(max(rec(im, p)[2]) == REV2_CAP for p in kp_ptrs), f"{nm} carried the {REV2_CAP} cap on every record (read from its image); rev 3 carries none", "S")
    check(all(rec(rev1, p)[1] == rec(base, p)[1] == rec(code, p)[1] for p in kp_ptrs), "rev 1 and rev 3 both carry the BASE X axis; rev 2 re-knotted", "S")
    r1X, r1Y = rec(rev1, kp_ptrs_by_slot[LIVE_SLOT])[1:]
    r2X_, r2Y_ = rec(rev2, kp_ptrs_by_slot[LIVE_SLOT])[1:]
    check(tuple(r2X_) == r2X and tuple(r2Y_) == r2Y, f"rev 2 live record read from its image: X {r2X} Y {r2Y} (what the print above used)", "S")
    print(f"        live LERP: idx  " + "".join(f"{i:>6d}" for i in PRINT_IDX))
    for nm, (XX, YY) in (("V280r2", (bX7, bY7)), ("rev 1", (r1X, r1Y)), ("rev 2", (r2X_, r2Y_)), ("rev 3", (lX, lY))):
        print(f"        {nm:8s}       " + "".join(f"{lerp(XX, YY, i):>6d}" for i in PRINT_IDX))
    check(all(lerp(lX, lY, i) <= min(lerp(bX7, bY7, i), lerp(r1X, r1Y, i), lerp(r2X_, r2Y_, i)) for i in range(241)), "rev 3 live LERP <= V280 rev 2, rev 1 and rev 2 at every idx", "S")

    print("\n  [9] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha, "independent rebuild (flatten + re-CRC, no shared state) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    _scr = os.environ.get("ACCORD_V281_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v281r3_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v281r3_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(f"_v281r3_{TAG}_plain_image.bin"))
        out_rwd = Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        others = [f.name for f in Path(RWD_DIR).glob("*V281*.rwd") if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"exactly ONE flashable V281 rwd on disk (others: {others})", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V281_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- census: {_census['S']} substantive, {_census['V']} vacuous (entailed by the base sha256), {_census['T']} tautological (readback of a write)")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
