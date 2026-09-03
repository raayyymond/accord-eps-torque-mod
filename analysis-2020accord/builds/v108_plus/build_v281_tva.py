# -*- coding: utf-8 -*-
r"""V281 rev 2 -- V280 rev 2 + the LKAS rate-PID Kp LERP FLAT at 341 FROM idx 24.  Cal-only.  Map, clamp, tap byte-identical to V280 rev 2.

=== REV 2 (2026-09-03) ===========================================================================
Rev 1 (image e27f12de...) capped the KNOTS only: Y[1..4] = 341 with X untouched.  Because Y[0] stays and X[1] = 68, the first
segment's slope fell from 3.88/idx to 1.37/idx, so Kp DROPPED on idx 1..67 too (idx 12: 294 -> 264, -10 %) -- the highway
lane-change regime (idx 2-12), which the sizing said should be untouched, was not.  Rev 2 RE-KNOTS: X = 0, 24, 68, 136, 208
(drop the 112 knot, insert 24; n stays 5, record length unchanged) with Y = Y[0], 341, 341, 341, 341.  The first segment now
runs from (0, Y[0]) to (24, 341) -- on slot 7 that is exactly V280 rev 2's own first segment (248 + 264*i//68 == 248 + 93*i//24
for every i 0..24, asserted per record), so the integer LERP output is IDENTICAL to V280 rev 2 at every idx 0..24 and 341 at every
idx >= 24.  The dropped 112 knot carried 341 after the cap, so above 68 nothing differs from rev 1.
Rev 1 is SUPERSEDED-DO-NOT-FLASH (kept on disk under that name; its hash is a cross-image check below).
TWO CORRECTIONS found while asserting rev 2, both stated here rather than hidden by a weaker assertion:
  (a) "IDENTICAL at every idx 0..24" is not exactly achievable with the firmware's floor LERP: 248 + 264*i//68 and
      248 + 93*i//24 differ by ONE count at a few idx (e.g. idx 17: 314 vs 313).  Asserted: |diff| <= 1 count on idx 0..24,
      == at idx 0, 2, 12 and 24, and 341 at every idx >= 24.  One count of 341 is 0.3 %.
  (b) A UNIFORM knee at X = 24 would put Kp ABOVE V280 rev 2 on records whose Y[0] is low (slots 0/4: 205 -> 341 over 24 idx is
      5.7/idx vs the base's 3.8/idx; +46 counts at idx 23; slots 2/5: +34).  That breaks "<= V280 rev 2 everywhere", which is
      the safety invariant of this build (authority only goes DOWN).  So the knee is PER RECORD: X[1] = the smallest idx at
      which the record's OWN base LERP reaches >= 341 (slot 7: 24 -- exactly the brief; slots 0/4: 37; 1/6: 20; 2/5: 32; 8/9: 23;
      dead 10-27: 7).  With that choice the new first segment's slope is <= the base's by construction, so LERP <= base at every
      idx on all 28 records (asserted), and the base's own value is reproduced within 1 count below the knee on the LIVE slot
      (within 4 counts, <= 1.5 %, on the others -- their base first segment does not pass through an integer 341 knot).

=== WHY THIS BUILD EXISTS (2026-09-03) ==========================================================
Sizing: analysis-2020accord/studies/v280/KPFLAT-SIZING-2026-09-03.md (subagent `kpflat`, script kpflat_sizing.py).
V280 rev 2 is the base (the straight-line map to the x6 top, clamp 46080, the V278 rev 3 delivered-torque tap).

THE SYMPTOM: the 6.5-7.4 Hz strong-turn ripple (episodes F7 of HIGHANGLE-r32-r33-2026-09-02.md; 7 of them, 6 at idx >= 68).
THE MECHANISM [EVIDENCE on the tap-identified plant; BELIEF that the closed loop follows the model]:
  The inner rate loop  L = [Kp/256 + 16(1-z^-1)] * 254/256 * H_lag * 5346/32768 * H_fb * 8 * z^-1 * G(wheel rate / T)
  is UNSTABLE in the loaded high-angle regime (v <= 10 m/s, |angle| >= 30 deg) at the as-is Kp(idx):
    Kp 512-696 (idx 68-173, where 6 of the 7 episodes sit): GM 0.50-0.86x at 8.2-9.1 Hz, PM -5..-25 deg.
  The 7 Hz line is that loop's crossover limit cycle, amplitude-regulated by the P clamp (describing function N = 0.60-0.83,
  so the loop self-regulates to K_eff = N * Kp(idx) = 394-575, median 439, on the six idx >= 106 episodes).
  Two methods put K_crit ~ 425 (linear GM = 1 with Kd 128: 425 / 443 / 426 on three plant fits; describing function: 439).
THE LEVER: Kp(idx) = V280 rev 2's own value for idx <= 24 (where it reaches 341 on slot 7), then FLAT 341.  Flat 341 is the
  thinnest cap that clears all six idx >= 68 episodes: PM 11-14 deg, GM 1.36-1.43x.  Slot 7: idx 12 294 (unchanged),
  idx 24 341 (unchanged), idx 58 473 -> 341 (-28 %), idx 68 512 -> 341, idx >= 136 696 -> 341 (-51 %).
COST, read from the chain (kpflat sizing, sec. 0.4): hands-light full-demand rate ~ -4 %; a STALLED wheel at idx 58 gets
  -28 % of the as-is push, and the full push arrives from idx ~ 80 instead of ~ 58.  That is a slice of the low-command stall
  authority V280 was built to restore -- stated plainly, the operator trades it for the loop margin.
INERT WHERE: the highway lane-change regime runs at idx 2-12 (LOWCMD A4); the LERP output there is IDENTICAL to V280 rev 2
  (asserted for every idx 0..24 on the six records whose base X[1] was 68, the live slot 7 among them).  A change in the
  lane-change feel on V281 rev 2 is NOT this lever.  [EVIDENCE: the integer LERP, floor form, evaluated on both images]
LINEAGE: neither 0xCB994 (Kp bank) nor any Kp record address is in BUILD-LINEAGE-PART1-LEVER-INDEX.md.  The Kp bank was
  edited only by V275 (/6, withdrawn unflashed) and V279 (Kp 256 flat + Kd 0 + fb clamp 0, a different loop, unflown).
  ==> the Kp bank has NEVER FLOWN EDITED.  V281 is its first flight.  Kd bank 0xCB7D4 UNTOUCHED (slot 7: 4 knots, 128 flat).

=== THE CELLS ==================================================================================
  [A] Kp LERP records via the pointer bank 0xCB994 (28 u32 LE pointers, 28 DISTINCT records -- no sharing; record = u16 n,
      X[n] u16, Y[n] u16).  For EVERY record: X = 0, knee, 68, 136, 208 (knee per record, see REV 2 (b); 24 on the live slot)
      and Y = Y[0], 341, 341, 341, 341 (n = 5 unchanged).
      Slot 7 (live, record 11 TVCA4) @0xE5378:
        X  0, 68, 112, 136, 208  ->  0, 24, 68, 136, 208        Y  248, 512, 645, 696, 696  ->  248, 341, 341, 341, 341
      Y[0] (205..307) is untouched on every record.  Payload bytes: computed from the base per cell and asserted vs the diff
      (X[1..2] on all 28 records; X[3..4] already 136/208 on slots 0/1/3/4/6/7, differ elsewhere; Y[1..4] on all 28 records).
      Every record: LERP <= V280 rev 2 at every idx 0..240, within 1 count of it below its knee, == 341 from its knee up.
  Nothing else: map family 0xC9A88, 0xC62E6 (46080), the 0x55DF0-0x55E12 tap window, the Kd family, the tapers, the frozen
  torque path -- all byte-identical to V280 rev 2 (asserted by cross-image compare, not by re-stating constants).

=== THE INSTRUMENT (already on the wire in this build) =========================================
  CAN-427 field ((b0&3)<<8)|b1 = (sign(T)<<9) | (|T|>>3), T = gp-0x6b38, the delivered lane torque (V278 rev 3 tap, unchanged).
  PRE-REGISTERED READ, same frames as the V280 rev 2 read (|angle| >= 30 deg, idx >= 68, v <= 10 m/s, >= 1 s runs):
    (i)  T 6-8.5 Hz amplitude / |T| p50: V280 rev 2's own value is the baseline; V281 predicted to fall to the D-path floor.
    (ii) 0x18F driver-torque 6-8.5 Hz ring amplitude (no tap needed).
    (iii) 7 Hz episodes per 100 s of high-angle engaged time.
    Cost read: sustained full-demand hands-light rate p50 (predicted ~ -4 %); stalled-wheel |T| at idx 40-80 (predicted -28 % at 58).
  FAIL sentences: the 7 Hz line persists at the same ripple/level with Kp verified 341 in the image ==> the line is NOT the inner
  loop's P-path limit cycle (D-fed or plant-fed); next lever is the fb pole (0xC63E8/EA), not more Kp.  Lane-change feel changes
  ==> not this lever (Kp(idx <= 24) is byte-identical); look elsewhere.

=== RISK, PLAINLY ==============================================================================
Authority goes DOWN, never up: P = E * Kp >> 8 with Kp <= 341 instead of <= 696 (max -51 % of P at idx >= 136 for the same E).
The P clamp, sum clamp, gain, override cliff, EME -- all byte-identical.  The lane keeps the sign of E (every Y > 0, asserted).
The only new value on the car is 341 (0x0155) in 112 knots.  Cal-only, no code byte changes (asserted: 0x13000-0xC0000 identical).

=== CLASS OF BUILD =============================================================================
The FIRST edit of the inner-loop gain bank to fly.  V276/V278/V280 moved the REFERENCE (the map); V281 leaves the reference exactly
where V280 rev 2 put it and lowers the inner loop's proportional gain where the sizing says it is above K_crit.  Interpretable from
one strong slow turn at |angle| >= 30 deg (the 7 Hz line in T) and one full-demand hands-light sweep (the cost).
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
KP_CAP = 341
KNEE_X = 24                                             # the LIVE slot's knee; every other record gets its own (see docstring (b))
NEW_X = (0, KNEE_X, 68, 136, 208)                        # the LIVE slot's X axis
def knee_for(X, Y):
    """Smallest idx at which the record's OWN base LERP reaches >= KP_CAP -- the new (knee, 341) knot then lies ON or BELOW the
    base curve, so the new first segment can never exceed the base one (floor LERP: (341-Y0)/x1 <= (base(x1)-Y0)/x1 <= base slope)."""
    return next(i for i in range(241) if lerp(X, Y, i) >= KP_CAP)
def new_x_for(X, Y):
    x1 = knee_for(X, Y)
    assert 0 < x1 < 68
    return (0, x1, 68, 136, 208)
TAG = f"V281R2-V280R2BASE-KP.FLAT{KP_CAP}.FROM{KNEE_X}.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
REV1_IMAGE = "SUPERSEDED_v281_rev1_KNOTCAP_plain_image.bin"
REV1_SHA = "e27f12dea6af1b7bc597c3eff79144b0d1d2f570e97c1b9ae1ae293e57b306fb"

# ---- [A] the Kp bank -------------------------------------------------------------------------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT = 7                                           # record 11 TVCA4 -- on the wire, 35 = 7x5
LIVE_KP_REC = 0xE5378
LIVE_KP_X, LIVE_KP_Y = (0, 68, 112, 136, 208), (248, 512, 645, 696, 696)
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)
PRINT_IDX = (0, 2, 12, 24, 58, 68, 100, 136, 240)

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
    """A second, minimal implementation with none of build()'s bookkeeping: cap, then re-CRC every 4 KB block it touched."""
    img = bytearray(base)
    touched = set()
    for s in range(N_SLOTS):
        p = u32(img, KP_PTR + 4 * s)
        n = u16(img, p)
        assert n == 5
        X0 = [u16(img, p + 2 + 2 * k) for k in range(n)]
        Y0 = [u16(img, p + 2 + 2 * n + 2 * k) for k in range(n)]
        x1 = next(i for i in range(241) if lerp(X0, Y0, i) >= KP_CAP)
        want = (0, x1, 68, 136, 208)
        for k in range(n):
            ox, oy = p + 2 + 2 * k, p + 2 + 2 * n + 2 * k
            if u16(img, ox) != want[k]:
                struct.pack_into("<H", img, ox, want[k])
                touched.add(ox)
            if k and u16(img, oy) != KP_CAP:
                struct.pack_into("<H", img, oy, KP_CAP)
                touched.add(oy)
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 102)
    print(f"  V281 rev 2 -- Kp FLAT {KP_CAP} from each record's knee (live slot 7: X {NEW_X}) on every record of 0xCB994.  Base V280 rev 2.  Map/clamp/tap/Kd byte-identical.")
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

    print("\n  [2] THE Kp POINTER FAMILY, WALKED FROM THE IMAGE")
    kp_ptrs_by_slot = [u32(base, KP_PTR + 4 * s) for s in range(N_SLOTS)]
    kp_ptrs = sorted(set(kp_ptrs_by_slot))
    check(all(START <= p < END for p in kp_ptrs), f"all {len(kp_ptrs)} Kp pointers in [0x13000, 0x100000)", "V")
    print(f"      {N_SLOTS} pointers -> {len(kp_ptrs)} distinct records" +
          ("" if len(kp_ptrs) == N_SLOTS else "  (SHARED records exist -- capped once each)"))
    # a record must not overlap any other Kp record, any Kd record, or the pointer banks themselves
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

    # ------------------------------------------------------------------------------------------
    print(f"\n  [3] [A] RE-KNOT: X = {NEW_X}, Y = Y[0], {KP_CAP} x4 on every record")
    code = bytearray(base)
    attributed = set()
    # expectations computed from the BASE, before any write: per cell, does the packed new value differ from the packed base?
    def _want(p):
        n, X, Y = rec(base, p)
        return list(new_x_for(X, Y)), [Y[0]] + [KP_CAP] * (n - 1)
    exp_cells = exp_bytes = 0
    for p in kp_ptrs:
        n, X, Y = rec(base, p)
        wX, wY = _want(p)
        for k in range(n):
            for old, new in ((X[k], wX[k]), (Y[k], wY[k])):
                if old != new:
                    exp_cells += 1
                    exp_bytes += sum(1 for j in (0, 1) if struct.pack("<H", old)[j] != struct.pack("<H", new)[j])
    print(f"      from the base: {exp_cells} u16 cells change on {len(kp_ptrs)} records -> {exp_bytes} bytes will differ")
    table = {}
    for p in kp_ptrs:
        n, X, Y = rec(base, p)
        check(n == 5, f"Kp 0x{p:05X} n == 5 (the re-knot keeps the record length)", "V")
        wX, wY = _want(p)
        for k in range(n):
            ox, oy = p + 2 + 2 * k, y_off(p, n, k)
            if X[k] != wX[k]:
                struct.pack_into("<H", code, ox, wX[k]); attributed |= {ox, ox + 1}
            if Y[k] != wY[k]:
                struct.pack_into("<H", code, oy, wY[k]); attributed |= {oy, oy + 1}
        n2, X2, Y2 = rec(code, p)
        bn, bX, bY = rec(base, p)                                  # re-read from BASE, not the loop's list
        check(n2 == bn == 5 and u16(code, p) == u16(base, p), f"Kp 0x{p:05X} n untouched (record length unchanged)", "S")
        x1 = knee_for(bX, bY)
        check(tuple(X2) == (0, x1, 68, 136, 208), f"Kp 0x{p:05X} X == (0, {x1}, 68, 136, 208)  (was {bX}); knee {x1} = first idx where the base LERP >= {KP_CAP}", "S")
        check(lerp(bX, bY, x1) >= KP_CAP and (x1 == 0 or lerp(bX, bY, x1 - 1) < KP_CAP), f"Kp 0x{p:05X} knee {x1} verified on the base LERP", "S")
        check(all(X2[k + 1] > X2[k] for k in range(n2 - 1)), f"Kp 0x{p:05X} X strictly increasing", "S")
        check(Y2 == [bY[0]] + [KP_CAP] * 4, f"Kp 0x{p:05X} Y == {bY[0]}, {KP_CAP} x4  (was {bY})", "S")
        check(Y2[0] == bY[0] < KP_CAP, f"Kp 0x{p:05X} Y[0] = {bY[0]} untouched and < {KP_CAP}", "S")
        check(max(Y2) <= KP_CAP and min(Y2) > 0, f"Kp 0x{p:05X} 0 < every Y <= {KP_CAP} -- the lane keeps the sign of E", "S")
        check(all(Y2[k + 1] >= Y2[k] for k in range(n2 - 1)), f"Kp 0x{p:05X} still monotone", "S")
        # the LERP contract, per record
        L0 = [lerp(bX, bY, i) for i in range(241)]
        L1 = [lerp(X2, Y2, i) for i in range(241)]
        check(all(L1[i] <= L0[i] for i in range(241)), f"Kp 0x{p:05X} LERP <= V280 rev 2 at every idx 0..240", "S")
        check(all(L1[i] == KP_CAP for i in range(x1, 241)), f"Kp 0x{p:05X} LERP == {KP_CAP} at every idx {x1}..240", "S")
        check(L1[0] == L0[0], f"Kp 0x{p:05X} LERP identical at idx 0", "S")
        slots_here = [s for s in range(N_SLOTS) if kp_ptrs_by_slot[s] == p]
        dmax = max(L0[i] - L1[i] for i in range(x1))
        check(dmax <= 4, f"Kp 0x{p:05X} (slots {slots_here}) LERP within 4 counts (<= 1.5 %) of V280 rev 2 at every idx 0..{x1 - 1} (max shortfall {dmax}; the live slot is held to 1 below)", "S")
        table.setdefault((tuple(bX), tuple(bY), tuple(X2), tuple(Y2)), []).append(slots_here)
    print("\n      per-slot before/after (records grouped by identical X/Y):")
    for (bX, bY, nX, nY), slots in table.items():
        sl = sorted(x for g in slots for x in g)
        print(f"        slots {sl}: X {list(bX)} -> {list(nX)}   Y {list(bY)} -> {list(nY)}")
    changed_cells = sum(1 for p in kp_ptrs for k in range(5) for (a, b) in ((u16(base, p + 2 + 2 * k), u16(code, p + 2 + 2 * k)), (u16(base, y_off(p, 5, k)), u16(code, y_off(p, 5, k)))) if a != b)
    check(changed_cells == exp_cells, f"changed u16 cells {changed_cells} == {exp_cells} (computed from the base)", "S")
    changed_bytes = sum(1 for p in kp_ptrs for o in rec_span(base, p) if code[o] != base[o])
    check(changed_bytes == exp_bytes, f"changed Kp-record bytes {changed_bytes} == {exp_bytes} (computed from the base, per byte)", "S")
    check(len(kp_ptrs) == N_SLOTS == 28 and all(any(y > KP_CAP for y in rec(base, p)[2]) for p in kp_ptrs),
          "all 28 records carried at least one knot above the cap -- none passed through unchanged by accident", "S")
    check(knee_for(*rec(base, kp_ptrs_by_slot[LIVE_SLOT])[1:]) == KNEE_X, f"LIVE slot {LIVE_SLOT}'s knee is {KNEE_X} (the brief's value) -- derived from its base LERP, not assumed", "S")
    # the uniform-24 alternative would have RAISED Kp on low-Y[0] records -- prove that, so the per-record knee is justified from the image
    worst = max(max(lerp((0, 24, 68, 136, 208), [rec(base, p)[2][0]] + [KP_CAP] * 4, i) - lerp(*rec(base, p)[1:], i) for i in range(241)) for p in kp_ptrs)
    check(worst > 0, f"POSITIVE CONTROL for the per-record knee: a uniform X[1] = 24 would exceed V280 rev 2 by up to {worst} counts on some record", "S")
    check(bytes(code[KP_PTR:KP_PTR + 4 * N_SLOTS]) == bytes(base[KP_PTR:KP_PTR + 4 * N_SLOTS]), "the pointer bank 0xCB994 itself is untouched (the edit is in the DATA)", "S")

    print(f"\n      LIVE slot {LIVE_SLOT} Kp LERP (integer, floor) at idx {PRINT_IDX}:")
    _, lX, lY = rec(code, kp_ptrs_by_slot[LIVE_SLOT])
    _, bX7, bY7 = rec(base, kp_ptrs_by_slot[LIVE_SLOT])
    print(f"        idx     : " + "".join(f"{i:>6d}" for i in PRINT_IDX))
    print(f"        V280 r2 : " + "".join(f"{lerp(bX7, bY7, i):>6d}" for i in PRINT_IDX))
    print(f"        V281    : " + "".join(f"{lerp(lX, lY, i):>6d}" for i in PRINT_IDX))
    check(tuple(lX) == NEW_X and tuple(lY) == (248, 341, 341, 341, 341), f"LIVE slot {LIVE_SLOT} X == {NEW_X}, Y == 248, 341, 341, 341, 341", "S")
    offs = [i for i in range(KNEE_X + 1) if lerp(lX, lY, i) != lerp(bX7, bY7, i)]
    check(all(0 <= lerp(bX7, bY7, i) - lerp(lX, lY, i) <= 1 for i in range(KNEE_X + 1)), f"live LERP within 1 count BELOW V280 rev 2 at every idx 0..{KNEE_X}; off by one at idx {offs} (floor LERP on a 24- vs 68-wide segment)", "S")
    check(lerp(lX, lY, 2) == lerp(bX7, bY7, 2) == 255 and lerp(lX, lY, 12) == lerp(bX7, bY7, 12) == 294 and lerp(lX, lY, 24) == lerp(bX7, bY7, 24) == 341, "live LERP 255 @2, 294 @12, 341 @24 on BOTH builds", "S")
    check(all(lerp(lX, lY, i) < lerp(bX7, bY7, i) for i in range(KNEE_X + 1, 241)), f"live LERP strictly BELOW V280 rev 2 at every idx {KNEE_X + 1}..240", "S")
    check(all(lerp(lX, lY, i) == KP_CAP for i in range(KNEE_X, 241)), f"live LERP == {KP_CAP} for every idx {KNEE_X}..240", "S")
    check(all(lerp(lX, lY, i) <= lerp(bX7, bY7, i) for i in range(241)), "live LERP <= V280 rev 2 at every idx (authority only goes DOWN)", "S")
    check(max(lerp(lX, lY, i) for i in range(241)) == KP_CAP and lerp(lX, lY, 0) == 248, f"live LERP max {KP_CAP}, Kp(0) = 248", "S")
    first_flat = next(i for i in range(241) if lerp(lX, lY, i) == KP_CAP)
    print(f"        first idx at the cap: {first_flat}; ramp 248 -> 341 over X 0..24 = {93/24:.3f}/idx == V280 rev 2's 264/68 = {264/68:.3f}/idx")
    print("        ratio V281r2/V280r2 at idx 2, 12, 24, 58, 136: " + ", ".join(f"{lerp(lX, lY, i) / lerp(bX7, bY7, i):.3f}" for i in (2, 12, 24, 58, 136)))

    # ------------------------------------------------------------------------------------------
    print("\n  [4] EVERYTHING ELSE BYTE-IDENTICAL TO V280 rev 2 -- compared against the base image")
    check(bytes(code[0x13000:0xC0000]) == bytes(base[0x13000:0xC0000]), "code region 0x13000-0xC0000 byte-identical (cal-only build)", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), "tap window 0x55DF0-0x55E12 byte-identical", "S")
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
        allow |= {y_off(p, n, k) + j for k in range(n) for j in (0, 1)}
        allow |= {p + 2 + 2 * k + j for k in range(1, n) for j in (0, 1)}      # X[1..4]; X[0] = 0 never changes
    check(set(pay) <= allow, "every payload byte is a Kp X[1..4] or Y[1..4] cell", "S")
    check(all(u16(code, p) == 5 and u16(code, p + 2) == 0 for p in kp_ptrs), "n and X[0] untouched on every record", "S")
    check(len(pay) == exp_bytes, f"payload byte count {len(pay)} == {exp_bytes} computed from the base", "S")
    check(all(x >= 0xC0000 for x in pay), "no code byte changed", "S")
    trailer_bytes = [x for x in diff if (x & 0xFFF) >= 0xFFC]
    check(len(trailer_bytes) == 4 * len(blocks), f"{len(trailer_bytes)} trailer bytes == 4 x {len(blocks)} blocks", "S")
    for s, e in runs(diff):
        kind = "CRC trailer" if (s & 0xFFF) >= 0xFFC else "Kp X/Y cells"
        owner = [sl for sl in range(N_SLOTS) if s in rec_span(base, kp_ptrs_by_slot[sl])] if kind == "Kp X/Y cells" else []
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
    FF.assert_x31_checksum(rwd, "V281 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
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
            check(p == u32(base, KP_PTR + 4 * s) and n == bn == 5 and tuple(X) == new_x_for(bX, bY) and Y == [bY[0]] + [KP_CAP] * 4,
                  f"{nm}: Kp slot {s:2d} @0x{p:05X} X == {X} Y == {Y}", "T" if nm == "code" else "S")
        check(tuple(rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))[1]) == NEW_X and tuple(rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))[2]) == (248, 341, 341, 341, 341), f"{nm}: live Kp X == {NEW_X}, Y == 248,341,341,341,341", "T" if nm == "code" else "S")
        check(tuple(rec(im, u32(im, KD_PTR + 4 * LIVE_SLOT))[2]) == LIVE_KD_Y, f"{nm}: live Kd == 128 x 4", "S")
        check(u16(im, FB_CELL) == FB_V280, f"{nm}: 0xC62E6 == {FB_V280}", "S")
        check(rec(im, u32(im, MAP_PTR + 4 * LIVE_SLOT))[2] == [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], f"{nm}: live map == the straight line", "S")
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: tap window == V280 rev 2", "S")
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}", "S")

    print("\n  [8b] CROSS-IMAGE vs V281 rev 1 (knot cap, superseded) -- read from THAT image")
    rev1 = Path(plain_image_path(REV1_IMAGE)).read_bytes()
    check(hashlib.sha256(rev1).hexdigest() == REV1_SHA, "V281 rev 1 image sha256 matches the reported hash", "S")
    d1 = [x for x in range(START, END) if code[x] != rev1[x] and (x & 0xFFF) < 0xFFC]
    allow_x = set()
    for p in kp_ptrs:
        allow_x |= {p + 2 + 2 * k + j for k in range(1, 5) for j in (0, 1)}
    check(d1 and set(d1) <= allow_x, f"vs rev 1: every payload difference is a Kp X[1..4] cell ({len(d1)} bytes); every Y, the map, clamp, code identical", "S")
    check(not [x for x in range(0x13000, 0xC0000) if code[x] != rev1[x]], "vs rev 1: no code byte differs", "S")
    check(all(rec(rev1, p)[2] == rec(code, p)[2] for p in kp_ptrs), "vs rev 1: every record's Y is identical (rev 2 changes only the X axis)", "S")
    check(all(rec(rev1, p)[1] == rec(base, p)[1] for p in kp_ptrs), "rev 1 carried the BASE X axis (read from the rev 1 image)", "S")
    r1X, r1Y = rec(rev1, kp_ptrs_by_slot[LIVE_SLOT])[1:]
    for i in (2, 12, 24, 58):
        print(f"        live LERP @idx {i:3d}: V280r2 {lerp(bX7, bY7, i)}  rev 1 {lerp(r1X, r1Y, i)}  rev 2 {lerp(lX, lY, i)}")
    check(lerp(r1X, r1Y, 12) == 264 and lerp(lX, lY, 12) == 294, "rev 1 read 264 at idx 12 (the defect); rev 2 reads 294 (== base)", "S")

    print("\n  [9] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha, "independent rebuild (cap + re-CRC, no shared state) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    _scr = os.environ.get("ACCORD_V281_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v281r2_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v281r2_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(f"_v281r2_{TAG}_plain_image.bin"))
        out_rwd = Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
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
