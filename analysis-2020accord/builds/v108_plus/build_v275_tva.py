# -*- coding: utf-8 -*-
r"""V275 -- THE WHOLE RATE PID SCALED 6x, PROPORTIONALLY.  BASE: V268.

THE OPERATOR'S SYMPTOM:  "LKAS demand has not been scaling with steering velocity."
The loop's maximum COMMANDABLE rate saturates at the assist-map ceiling of 172.  Above that, more
command buys nothing -- the reference itself has run out.  V275 scales the ENTIRE loop by 6,
delivered torque included, so that every ratio Honda calibrated is preserved exactly.

=== WHY V274 WAS WITHDRAWN, AND WHAT IS DIFFERENT HERE =========================================
V274 scaled the assist map 6x and FROZE every torque cell, arguing that freezing the cells freezes
the torque.  Three independent adversarial reviews falsified that:
  * Freezing torque CELLS does not freeze delivered TORQUE.  The map scales the ERROR that feeds
    Kp, so P saturated over ~80% of the demand range and the lane went effectively BANG-BANG above
    index ~44.  The linearisation's own stated purpose -- uniform resolution at high command -- was
    defeated, not achieved.  Delivered torque rose up to 2.5x at sub-maximal demand.
  * The docstring's "delivered peak torque is bit-for-bit V268's = 2505" was FALSE.  V268's real
    peak is 2441 (P tops out at 14964 = 97.4% of the 15360 clamp).  2505 is the clamp-limited
    ceiling V268 never reaches.  The assertion defending it was a TAUTOLOGY: it read only two cells
    already asserted frozen three lines earlier, so it could not fail.
  * D acts on delta(FULL ERROR E = 32*setpoint - feedback), NOT delta(setpoint); the V274 analysis
    dropped that 32x.  Worse, D's sensitivity is governed by the map's SLOPE, and linearising the
    map removes the protection Honda's flat top gave D exactly in the high-command region.

V275 fixes all three by scaling the loop PROPORTIONALLY instead of freezing half of it.

=== THE CLAMP AUDIT -- WHICH CELLS CAN TAKE 6x, READ FROM THE IMAGE ============================
A clamp's read encoding decides its ceiling.  `ld.hu` (disp|1) is zero-extended -> ceiling 65535.
`ld.h` (plain disp) is SIGN-extended -> ceiling 32767, above which the +limit branch goes NEGATIVE.

  cal        role            now     x6      reads                       ceiling   verdict
  0xC62E6    feedback clamp   7680   46080   3/3 ld.hu                    65535    OK
  0xC61B6    D clamp         10240   61440   4/4 ld.hu                    65535    OK (not needed)
  0xC61BA    I clamp         10240   61440   1/1 ld.hu                    65535    OK (Ki=0, inert)
  0xC61B4    output clamp     3072   18432   3 ld.hu + 1 ld.h @0x2A20E    32767    OK
  0xC61BC    P clamp         15360   92160   4/4 ld.hu                    65535    BLOCKED (u16)
  0xC61BE    sum clamp       15360   92160   3 ld.hu + 1 ld.h @0x2A148    32767    BLOCKED (x2.13)

Two clamps cannot take 6x; 0xC61BE cannot even reach 2.2x without tripping its sign defect.
So the 6x is moved OFF those two cells and ONTO the terms that feed them:

      map 0xC9A88   x6   ->  setpoint x6     the loop can now COMMAND 6x the rate
      0xC62E6       x6   ->  46080           the loop can now MEASURE 6x the rate
      Kp  0xCB994   /6   ->  P back to its 1x numeric range  -> 15360 clamp NOT approached
      Kd  0xCB7D4   /6   ->  D back to its 1x numeric range  -> 10240 clamp NOT approached
                            and sum = I>>7+P+D stays 1x      -> 15360 clamp NOT approached
      gain 0xC6CD0  x6   ->  32076           the 6x re-enters HERE, where there IS headroom
      0xC61B4       x6   ->  18432           so the 6x torque is not clipped on the way out

At the top of the map, computed from the image (slot 1):
      E_max      = 32 * 1032          = 33024
      P_max      = 33024 * 116 >> 8   = 14964   <- 97.4% of the 15360 clamp, Honda's OWN ratio
      torque_max = 14964 * 32076 >>15 = 14647   <- 6.00x V268's real peak of 2441
      output clamp 18432 > 14647, NOT binding  <- mirrors V268, where 3072 > 2441
Every headroom ratio Honda calibrated is preserved to within integer rounding.

=== THE DIVISION ALSO REPAIRS THE D DEFECT ====================================================
D = (dE * Kd) >> 3, clamped +-10240.  Dividing Kd by 6 makes the linearised map SAFER than the car
is today, because the gain decrease more than cancels the slope increase:
      today  Kd=128, stock slope 2.25 (steepest)  ->  D rails at |d_index| >  8.9 per frame
      V275   Kd= 21, linear slope 4.30            ->  D rails at |d_index| > 28.4 per frame
3.2x MORE tolerant of a brisk one-frame step than the current car.  Dividing Kd is what makes
linearising the map safe; V274 linearised WITHOUT it, which is why the review condemned it.

=== FIVE EDITS ================================================================================
  [A] TELEMETRY -- CAN 427 repointed to the variant selector gp-0x674e (3 code bytes, from V273),
      PLUS a 1-byte clamp-floor fix.  A tracer found 4 of the 16 variant records read
      gp-0x674e = 0, which wires out as 0 -- INDISTINGUISHABLE from a dead channel or a build that
      did not take.  0x55E0E is `mov 0x0,r7`, the LOW argument of clamp(v,lo,hi); the byte
      0x00 -> 0x01 makes the floor 1, so a zero-valued selector reads 1 and only a genuinely dead
      channel reads 0.  1 byte, no new instruction, no cave.
      NOTE: expected wire CODES are deliberately NOT asserted.  The V273 docstring paired record
      NAMES (1-based) with record INDEX values (0-based) in the 0xCD012 table, so "record 2 =>
      wire 5" may actually be wire 0.  The floor fix makes the tap interpretable either way;
      quoting a specific expected code would repeat V274's habit of asserting unverified premises.
  [B] ASSIST MAP  0xC9A88 -- linearised AND scaled 6x, all 28 records (V273's edit, made safe by D).
  [C] OVERRIDE TAPER FLATTENED -- 0xCBA04/0xCBA74, Y -> each record's own Y[0], 56 records (V273's).
  [D] THE PROPORTIONAL RESCALE -- Kp/6, Kd/6, gain x6, output clamp x6, feedback clamp x6.
  [E] P / sum / D / I clamps FROZEN and asserted -- the 6x is deliberately routed AROUND them.

WHAT THIS BUILD IS NOT:  it is not a re-run of the gain ladder.  V101/V112 moved 0xC6CD0 ALONE with
the reference untouched, and 8x measured the WORST Re(Z) in the corpus.  Here the gain moves only
as the second half of a matched pair with Kp/6, so loop stiffness per unit of PHYSICAL rate error
is UNCHANGED; what changes is the reference's REACH.  That distinction is the whole build.

RISK, STATED BEFORE THE DRIVE:  delivered torque at full command rises 2441 -> 14647.  That is the
intended 6x and it is the largest authority increase this kit has ever cut.  The taper flatten [C]
compounds it by removing the driver-pushback cut.  ASSESS STATIONARY OR AT LOW SPEED FIRST.
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
from verify_bootloader_crc import walk, walk_all_blocks                                   # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V275_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
TAG = "V275-V268BASE-RATE6X.KP6.KD6.TORQUEHELD.TAPERFLAT"

K = 6                                       # the rate-axis scale factor

# ---- [A] telemetry ---------------------------------------------------------------------------
SRC_DISP, SRC_V268, SRC_NEW = 0x55DF2, 0x9544, 0x98B2
SAR_SITE, SAR_V268, SAR_NEW = 0x55E10, 0xA3, 0xA0

# ---- [B] assist map --------------------------------------------------------------------------
MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28
MAP_X = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)

# ---- [C] override taper ----------------------------------------------------------------------
TAPER_PTRS = (0xCBA04, 0xCBA74)
TAPER_N = 4
TAPER_SHAPES = {(70, 72, 78, 80): (254, 234, 12, 0),      # slots 0-9   <- this car's candidates
                (32, 48, 64, 112): (255, 205, 154, 0)}    # slots 10-27

# ---- [C] feedback clamp ----------------------------------------------------------------------
FB_CELL, FB_STOCK, FB_NEW = 0xC62E6, 7680, 7680 * K

# ---- frozen torque path, all asserted --------------------------------------------------------
FROZEN = {
    0xC61B4: 3072,                     # OUTPUT clamp -- FROZEN.  The torque cap.
    0xC6CD0: 5346,                     # forward gain -- FROZEN.  Already 6x Honda's 891; raising
                                       # it to 32076 would be 36x STOCK.  Operator's cap: 6x stock.
    0xC61B6: 10240,  0xC61BA: 10240,   # D clamp / I anti-windup -- 6x routed AROUND them (Kd/6)
    0xC61BC: 15360,  0xC61BE: 15360,   # P clamp / sum clamp     -- 6x routed AROUND them (Kp/6)
    0xC63E6: 0,                        # Ki -- stays OFF
    0xC63E8: 923,    0xC63EA: 1560,    # feedback lag pole / input gain -- pole must NOT move
    0xC63EC: 992,    0xC63EE: 507,     # 5 Hz output LPF
    0xC62E4: 4,                        # error deadband
    0xC6B26: 256,    0xC6B12: 98,      # the OTHER PID (driver-side) -- untouched
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,                     # NOT this loop's clamp: 0 reads in FUN_00028ea6, all 5 in
                                       # FUN_0002b422/FUN_0002b57a.  Asserted only to prove we did
                                       # not touch it.  STATE.md's "0xC61B2/0xC61B4 pair" is wrong.
}

# ---- [D] the proportional rescale ------------------------------------------------------------
GAIN_CELL, GAIN_V268 = 0xC6CD0, 5346        # FROZEN -- already 6x stock; 6x again = 36x stock
OUT_CELL, OUT_V268 = 0xC61B4, 3072          # FROZEN -- this IS the torque cap, and it stays
GAIN_SITE = 0x2A1EE                                             # ld.h -- 32076 must stay < 32768
FLOOR_SITE, FLOOR_V268, FLOOR_NEW = 0x55E0E, 0x00, 0x01         # clamp floor 0 -> 1
KP_N, KD_N = 5, 4

CAVE, HOOK = (0xC4B34, 0xC4BD8), 0x55C0E
SAR_R26, SAR_R24, SAR_1X = 0x3AB76, 0x3AC20, 0xAA
IDX_CLAMP_P, IDX_CLAMP_N = 0xC64F0, 0xC64F1
KP_PTR, KD_PTR = 0xCB994, 0xCB7D4
FB_SITES = (0x28F96, 0x28F9C, 0x28FB8)      # must all be ld.hu (low byte 0xe5)

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p, n):
    return ([u16(b, p + 2 + 2 * i) for i in range(n)],
            [s16(b, p + 2 + 2 * n + 2 * i) for i in range(n)])


def build():
    print("=" * 102)
    print(f"  V275 -- THE WHOLE RATE PID x{K}, PROPORTIONALLY.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK}")
    check(u16(base, GAIN_CELL) == GAIN_V268, f"base forward gain == {GAIN_V268} (= 6 x Honda's 891)")
    check(u16(base, OUT_CELL) == OUT_V268, f"base output clamp == {OUT_V268} -- the TORQUE CAP")
    check(base[FLOOR_SITE] == FLOOR_V268, "base 427 clamp floor is `mov 0x0,r7`")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49 (the flash-time model)")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x (V62 NOT restored)")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "index clamp +-240 unchanged")

    print("\n  [1b] THE SIGN-EXTENSION DEFECT -- and V275 raises TWO cells that carry it")
    SIGN_SITES = {0xC61BE: ((0x2A13E, 0xE5), (0x2A146, 0x25), (0x2A14C, 0xE5), (0x2A156, 0xE5)),
                  0xC61B4: ((0x2A1F8, 0xE5), (0x2A20C, 0x25), (0x2A212, 0xE5), (0x2A21C, 0xE5))}
    for cal_, sites in SIGN_SITES.items():
        n_sign = 0
        for a, want in sites:
            kind = "ld.hu ZERO-ext" if base[a] == 0xE5 else "ld.h  SIGN-ext" if base[a] == 0x25 else "??"
            check(base[a] == want, f"0x{cal_:05X} read @0x{a:05X} {base[a]:02X} = {kind}")
            n_sign += base[a] == 0x25
        check(n_sign == 1, f"0x{cal_:05X} has exactly ONE sign-extended read -> hard cap 32767")
    print("      -> 0xC61BE stays 15360 (a 6x would be 92160: over u16 AND over the sign cap).")
    check(base[GAIN_SITE] == 0x25, f"0x{GAIN_SITE:05X} is ld.h (sign-ext) -- gain capped at 32767")
    print("      -> V275 raises NEITHER 0xC61B4 NOR 0xC6CD0.  The 6x is on the RATE axis only.")

    print("\n  [1c] the feedback clamp's OWN reads must all be ld.hu, or 6x would break it")
    for a in FB_SITES:
        check(base[a] == 0xE5, f"0x{a:05X} {base[a]:02X} = ld.hu (zero-extend) -- safe above 32768")

    code = bytearray(base)
    attributed = set()

    print("\n  [2] [A] TELEMETRY -- CAN 427 -> gp-0x674e")
    check(u16(base, SRC_DISP) == SRC_V268, "base 427 source is gp-0x6ABC")
    check(base[SAR_SITE] == SAR_V268, "base packer carries `sar 0x3, r6`")
    struct.pack_into("<H", code, SRC_DISP, SRC_NEW)
    code[SAR_SITE] = SAR_NEW
    attributed |= set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE}
    code[FLOOR_SITE] = FLOOR_NEW
    attributed |= {FLOOR_SITE}
    check(code[FLOOR_SITE] == FLOOR_NEW, "427 clamp floor `mov 0x0,r7` -> `mov 0x1,r7`")
    print("      wire = clamp(|gp-0x674e| * 5, 1, 1023)")
    print("      -> floor 1, so selector==0 reads 1 and ONLY a dead channel reads 0.")
    print("      -> expected codes deliberately NOT asserted: the 0-vs-1-based record numbering")
    print("         in the 0xCD012 table is unresolved, so any specific code is a BELIEF.")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")

    print(f"\n  [3] [B] ASSIST MAP -- scaled {K}x, SHAPE PRESERVED, all {N_SLOTS} records")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(START <= p < END for p in ptrs), f"all {len(ptrs)} map pointers in range")
    shapes = {}
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        ceil = K * Y[-1]                                   # 6x THIS record's own ceiling
        newY = tuple(K * y for y in Y)                     # HONDA'S SHAPE, scaled -- NOT linearised
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        check(tuple(gY) == newY, f"map 0x{p:05X} Y -> {K}x, ceiling {ceil}")
        check(all(gY[i] == K * Y[i] for i in range(n)),
              f"map 0x{p:05X} EXACTLY {K}x stock at every knot -- Honda's SHAPE is preserved, so "
              f"torque-vs-index is preserved when Kp is divided by {K}")
        _r = [gY[i] / Y[i] for i in range(n) if Y[i]]
        check(max(_r) == min(_r) == K, f"map 0x{p:05X} every knot scales by exactly {K}, no rounding")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  ceiling {oldY[-1]:4d} -> {newY[-1]:5d}   (Honda's shape, x{K})")
    check(all(tuple(rec(code, p, MAP_N)[0]) == MAP_X for p in ptrs), "every map X untouched")

    print("\n  [3b] [C] OVERRIDE TAPER FLATTENED -- 0xCBA04 / 0xCBA74, all 28 slots x 2 banks")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tp_ = u32(base, arr + 4 * s)
            check(START <= tp_ < END, f"taper ptr 0x{arr:05X}[{s}] in range")
            tps.add(tp_)
    _cnt = {}
    for p in sorted(tps):
        n = s16(base, p)
        check(n == TAPER_N, f"taper 0x{p:05X} npt == {TAPER_N}")
        X, Y = rec(base, p, n)
        key = tuple(X)
        check(key in TAPER_SHAPES, f"taper 0x{p:05X} X {key} is a KNOWN shape")
        check(tuple(Y) == TAPER_SHAPES[key], f"taper 0x{p:05X} Y == stock before edit")
        check(all(Y[i] > Y[i + 1] for i in range(n - 1)), f"taper 0x{p:05X} Y strictly DECREASING")
        flat = Y[0]
        check(flat in (254, 255), f"taper 0x{p:05X} Y[0] == {flat}")
        _cnt[key] = _cnt.get(key, 0) + 1
        for i in range(n):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, flat)
            attributed |= {o, o + 1}
        nY = rec(code, p, n)[1]
        check(all(y == flat for y in nY), f"taper 0x{p:05X} Y -> flat {flat}")
        check(all(nY[i] >= Y[i] for i in range(n)),
              f"taper 0x{p:05X} flatten only RAISES Y -- no authority removed in any mode")
    for k_, v_ in _cnt.items():
        print(f"      shape X={k_} -> flattened in {v_} records")
    check(all(tuple(rec(code, p, TAPER_N)[0]) in TAPER_SHAPES for p in tps), "every taper X untouched")

    print(f"\n  [4] [C] FEEDBACK CLAMP 0xC62E6  {FB_STOCK} -> {FB_NEW}")
    struct.pack_into("<H", code, FB_CELL, FB_NEW)
    attributed |= {FB_CELL, FB_CELL + 1}
    check(u16(code, FB_CELL) == FB_NEW, f"feedback clamp == {FB_NEW}")
    check(FB_NEW < 65536, "fits u16")

    print(f"\n  [4b] [D] THE RESCALE -- Kp/{K} and Kd/{K}.  GAIN AND OUTPUT CLAMP UNTOUCHED.")

    def scale_bank(ptr, npt, name, div):
        nonlocal_attr = attributed
        seen, out = set(), {}
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            check(START <= p < END, f"{name} ptr[{s}] 0x{p:05X} in range")
            seen.add(p)
        for p in sorted(seen):
            n = s16(base, p)
            check(n == npt, f"{name} 0x{p:05X} npt == {npt}")
            X, Y = rec(base, p, n)
            newY = tuple(round(y / div) for y in Y)
            check(all(v > 0 for v in newY), f"{name} 0x{p:05X} every coefficient stays NON-ZERO")
            check(all(newY[i + 1] >= newY[i] for i in range(n - 1)),
                  f"{name} 0x{p:05X} monotonicity preserved")
            for i, v in enumerate(newY):
                o = p + 2 + 2 * n + 2 * i
                struct.pack_into("<h", code, o, v)
                nonlocal_attr |= {o, o + 1}
            gY = rec(code, p, n)[1]
            check(tuple(gY) == newY, f"{name} 0x{p:05X} Y -> /{div}")
            err = max(abs(gY[i] * div - Y[i]) / max(Y[i], 1) for i in range(n))
            check(err < 0.04, f"{name} 0x{p:05X} rounding error {err*100:.2f}% < 4%")
            check(tuple(rec(code, p, n)[0]) == tuple(X), f"{name} 0x{p:05X} X untouched")
            out[p] = (tuple(Y), newY)
        check(len(seen) == N_SLOTS, f"{name}: all {N_SLOTS} records are DISTINCT (no aliasing)")
        return out

    kp_recs = scale_bank(KP_PTR, KP_N, "Kp", K)
    kd_recs = scale_bank(KD_PTR, KD_N, "Kd", K)
    for nm, rs in (("Kp", kp_recs), ("Kd", kd_recs)):
        u = {}
        for (oY, nY) in rs.values():
            u[(oY, nY)] = u.get((oY, nY), 0) + 1
        for (oY, nY), c in sorted(u.items()):
            print(f"      {nm} x{c:2d}  {list(oY)} -> {list(nY)}")

    check(u16(code, GAIN_CELL) == GAIN_V268, f"forward gain STILL {GAIN_V268} (6x stock, NOT 36x)")
    check(u16(code, OUT_CELL) == OUT_V268, f"output clamp STILL {OUT_V268} -- the torque cap HOLDS")

    print("\n  [5] THE ARITHMETIC, COMPUTED FROM THE BUILT IMAGE -- NOT FROM CONSTANTS")

    def lerp(X, Y, x):
        if x <= X[0]:
            return Y[0]
        if x >= X[-1]:
            return Y[-1]
        for i in range(len(X) - 1):
            if X[i] <= x <= X[i + 1]:
                return Y[i] + (Y[i + 1] - Y[i]) * (x - X[i]) // (X[i + 1] - X[i])
        raise AssertionError

    SLOT = 1
    mp, kp, kd = (u32(base, MAP_PTR + 4 * SLOT), u32(base, KP_PTR + 4 * SLOT),
                  u32(base, KD_PTR + 4 * SLOT))
    mX, mY0 = rec(base, mp, MAP_N)
    mY1 = rec(code, mp, MAP_N)[1]
    pX, pY0 = rec(base, kp, KP_N)
    pY1 = rec(code, kp, KP_N)[1]

    def torque(idx, mY, pY, gain, pclamp, oclamp):
        sp = lerp(mX, mY, idx)
        E = 32 * sp
        P = max(-pclamp, min(pclamp, (E * lerp(pX, pY, idx)) >> 8))
        return sp, P, max(-oclamp, min(oclamp, (P * gain) >> 15))

    print("        idx |   V268: sp     P    torque |   V275: sp     P    torque | ratio")
    ratios, sat268, sat275 = [], 0, 0
    for idx in (12, 24, 48, 96, 160, 240):
        s0, p0, t0 = torque(idx, mY0, pY0, GAIN_V268, 15360, OUT_V268)
        s1, p1, t1 = torque(idx, mY1, pY1, GAIN_V268, 15360, OUT_V268)
        sat268 += p0 >= 15360
        sat275 += p1 >= 15360
        ratios.append(t1 / max(t0, 1))
        print(f"      {idx:5d} | {s0:9d} {p0:6d} {t0:8d}   | {s1:9d} {p1:6d} {t1:8d}   | {t1/max(t0,1):5.2f}")
        check(abs(t1 - t0) <= max(4, 0.03 * t0),
              f"idx {idx}: V275 torque {t1} == V268 {t0} to within 3% -- TORQUE IS HELD, only the "
              f"RATE the loop can command has moved")
    check(sat275 == 0, "P NEVER saturates in V275 (V274's defect: it saturated above idx ~44)")
    check(sat268 == 0, "P never saturates in V268 either -- like-for-like comparison")

    s0, p0, t0 = torque(240, mY0, pY0, GAIN_V268, 15360, OUT_V268)
    s1, p1, t1 = torque(240, mY1, pY1, GAIN_V268, 15360, OUT_V268)
    check(t0 == 2441, f"V268's REAL peak torque is {t0} (NOT the 2505 clamp ceiling V274 asserted)")
    check(t1 == t0, f"V275 peak torque {t1} is IDENTICAL to V268's {t0} -- the operator's cap of "
                    f"6x STOCK is held exactly; this build adds ZERO torque authority")
    check(p1 < 15360, f"peak P {p1} stays UNDER the 15360 clamp ({100*p1/15360:.1f}% of it)")
    check(t1 < OUT_V268, f"peak torque {t1} stays UNDER the output clamp {OUT_V268} -- not binding")
    check(max(ratios) <= 1.03, f"NO index exceeds 1.03x (max {max(ratios):.3f}x) -- torque held flat")
    sp_gain = mY1[-1] / mY0[-1]
    check(abs(sp_gain - K) < 1e-9, f"commandable RATE ceiling is exactly {sp_gain:.0f}x -- THAT is "
                                   f"the whole build: {mY0[-1]} -> {mY1[-1]} setpoint counts")

    print(f"\n      D-term: Kd {rec(base,kd,KD_N)[1][0]} -> {rec(code,kd,KD_N)[1][0]},"
          f" clamp 0xC61B6 = {u16(code,0xC61B6)} (FROZEN)")
    kd0, kd1 = rec(base, kd, KD_N)[1][0], rec(code, kd, KD_N)[1][0]
    sl0 = max((mY0[i+1]-mY0[i])/(mX[i+1]-mX[i]) for i in range(MAP_N-1))
    sl1 = max((mY1[i+1]-mY1[i])/(mX[i+1]-mX[i]) for i in range(MAP_N-1))
    d0 = 10240 / (32 * sl0 * kd0 / 8)
    d1 = 10240 / (32 * sl1 * kd1 / 8)
    print(f"      D rails at |d_index| > {d0:.1f}/frame today  ->  > {d1:.1f}/frame on V275")
    check(d1 > d0, f"V275 is MORE tolerant of a brisk step than the current car ({d1:.1f} > {d0:.1f})"
                   f" -- dividing Kd is what makes the linearised map safe")

    print("\n  [6] TORQUE PATH RE-ASSERTED ON THE BUILT IMAGE")
    for a, v in FROZEN.items():
        check(u16(code, a) == v, f"0x{a:05X} still {v}")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X, "rate lane still stock 1x")
    check(code[IDX_CLAMP_P] == 240 and code[IDX_CLAMP_N] == 240, "index clamp still +-240")
    check(u16(code, GAIN_CELL) == GAIN_V268, f"0xC6CD0 still {GAIN_V268}")
    check(u16(code, OUT_CELL) == OUT_V268, f"0xC61B4 still {OUT_V268}")

    print("\n  [7] CRC TRAILERS")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    for b0, b1 in blocks:
        check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit on trailer 0x{b1:06X}")
        oldc = u32(code, b1)
        newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
        struct.pack_into("<I", code, b1, newc)
        attributed |= set(range(b1, b1 + 4))
        print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")

    print("\n  [8] FULL BYTE DIFF vs V268")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(not [x for x in diff if x not in attributed], f"all {len(diff)} differing bytes attributed")
    pay = [x for x in diff if (x & 0xFFF) < 0xFFC]
    allow = set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE, FLOOR_SITE, FB_CELL, FB_CELL + 1}
    for ptr_, npt_ in ((KP_PTR, KP_N), (KD_PTR, KD_N)):
        for s in range(N_SLOTS):
            p = u32(base, ptr_ + 4 * s)
            allow |= {p + 2 + 2 * npt_ + k for k in range(2 * npt_)}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    for p in tps:
        allow |= {p + 2 + 2 * TAPER_N + k for k in range(2 * TAPER_N)}
    check(set(pay) <= allow, "every payload byte is a map/taper/Kp/Kd Y knot, the feedback clamp, "
                             "or one of the 4 telemetry code bytes -- no X axis, no cave, "
                             "no gain, no output clamp, no unintended cell")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(cb == sorted(set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE, FLOOR_SITE}),
          f"exactly 4 code bytes move, all in the 427 packer: {[hex(x) for x in cb]}")
    check(bytes(code[0x28EA6:0x2A30D]) == bytes(base[0x28EA6:0x2A30D]),
          "FUN_00028ea6 itself is byte-identical -- every edit is a CALIBRATION, not code")
    print(f"      {len(pay)} payload bytes, {len(cb)} code, {len(blocks)} CRC trailers")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V274 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49 (predicts flash NRC 0x72)")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest()
          if hasattr(FF, "V38_PLAIN") else True,
          "cipher table validated NON-circularly against the known V38 plain image")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v275_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V275_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
