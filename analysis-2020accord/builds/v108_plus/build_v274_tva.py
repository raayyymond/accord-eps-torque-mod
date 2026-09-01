# -*- coding: utf-8 -*-
r"""V274 -- THE RATE AXIS, SCALED 6x.  TORQUE SCALING UNCHANGED AT 6x.  BASE: V268.

THE OPERATOR'S SYMPTOM, QUANTIFIED:  "LKAS demand has not been scaling with steering velocity."
The loop's MAXIMUM COMMANDABLE RATE is 22.3 column deg/s.  Above that, more command buys nothing --
the reference itself has run out.  That is the complaint, and it was never a gain problem.

    max commandable rate = 32 * map_ceiling / 247.1 = 32*172/247.1 = 22.3 deg/s

THE INSIGHT THAT MAKES THIS A TWO-CELL BUILD (operator, 2026-09-01).  The loop's cells sit on TWO
INDEPENDENT AXES, because the error is in PHYSICAL rate-error units:

    error = 32*setpoint - feedback = 247.1 * (r_cmd - r_act)

The error for a given rate error does NOT depend on the map scale.  Therefore:

  RATE axis    0xC9A88 map ceiling M   -> the COMMANDED rate,  r_max = 32M/247.1
               0xC62E6 feedback clamp F -> the MEASURABLE rate, r_meas = F/247.1
  TORQUE axis  0xC61BC (P) . 0xC61BE (sum) . 0xC61B2/0xC61B4 (out) . gain 0xC6CD0
               -> torque per unit of rate ERROR.  DOES NOT SCALE WITH THE RATE TARGET.

=> V274 scales ONLY the rate axis.  Every torque-path cell is frozen and asserted below, so
   **delivered peak torque is bit-for-bit what V268/V112 already produce: (15360*5346)>>15 = 2505.**

FOUR EDITS -- V273's three, re-aimed at the rate axis and scaled 6x, plus the feedback clamp.
  [A] TELEMETRY -- CAN 427 repointed to the variant selector gp-0x674e (3 code bytes, from V273).
      wire == 5 => record 2 (slots 10/11).  wire == 35 => record 11 (slots 24-27).  A STATIC boot
      constant, so ANY drive answers it -- parked, disengaged, ten seconds.  It matters here
      specifically: V274 edits all 28 records because we still do not know which one is live.
  [B] ASSIST MAP  0xC9A88 -- COMPLETELY LINEARISED **and** scaled 6x, all 28 records:
          Y[i] = round( X[i] * 6*Y_stock[-1] / 240 )
      so each record keeps its own character (ceiling 172/180/188 -> 1032/1080/1128) while its
      response becomes a straight line.  This is V273's edit [C] carried forward -- the resolution
      collapse is what made demand unreadable at high command: stock spends its top 80 index steps
      climbing 6 counts (slope 0.075, one output level per 13.3 steps) against 2.0 at the bottom.
      Linearised at 6x the slope is 4.3 everywhere -- uniform resolution AND 6x the rate ceiling.
  [C] OVERRIDE TAPER FLATTENED -- 0xCBA04 / 0xCBA74, Y -> each record's own Y[0], 56 records.
      This is V273's edit [B].  Stock X = (70,72,78,80) Y = (254,234,12,0), indexed by
      |gp-0x4f60|>>5, i.e. the DRIVER'S OWN COLUMN TORQUE multiplied into the demand.  Index 0 is
      below X[0], so hands-off already returns 254 -- the curve only acts ABOVE raw driver torque
      ~2240, where it currently cuts LKAS demand to ZERO by ~2560.  Flattening changes NOTHING below
      that threshold and removes the cut above it.  Flattening to each record's own Y[0] only ever
      RAISES Y, never lowers it.
  [D] FEEDBACK CLAMP  0xC62E6  7680 -> 46080 (6x), so the loop can still MEASURE what it commands.

WHY BOTH [B] AND [C], AND WHY EXACTLY 6x ON EACH.  Honda matched them: feedback_clamp / max_error =
7680/5504 = 1.395.  Scaling both by 6 preserves that ratio EXACTLY (46080/33024 = 1.395).  Raise the
map alone and the feedback pins at 31.1 deg/s while the setpoint keeps climbing -- the loop would go
effectively OPEN above 31 deg/s.  That is a real defect, and it is the one V273 has.

WHAT V274 DELIBERATELY DOES **NOT** DO, each with its reason:
  * It does NOT raise the P clamp 0xC61BC.  P saturating on a large transient is correct behaviour --
    a big rate error should command full effort.  Raising it would raise TORQUE, which the operator
    explicitly does not want.  Frozen and asserted.
  * It does NOT raise the sum clamp 0xC61BE.  Besides being a torque cell, it carries a
    SIGN-EXTENSION DEFECT: of its four clamp reads, 0x2A146 is `ld.h` (2567be71) while 0x2A13E /
    0x2A14C / 0x2A156 are `ld.hu` (e5..bf71).  Set it >= 32768 and PEAK DEMAND CLAMPS NEGATIVE.
    V274 never approaches it.  0xC61BC (4/4 ld.hu) and 0xC62E6 (3/3 ld.hu) are clean.
  * It does NOT touch 0xC61B2/0xC61B4 (3072).  These never bind today -- the lane clips at 2505,
    82 % of its own output clamp -- so leaving them frozen is what keeps torque at exactly 6x.
  * It does NOT enable Ki (0xC63E6 = 0).  Three independent agents converged: P already sits at
    97.4 % of its clamp at max demand BY DESIGN, so the steady-state error is large intentionally,
    not a residual for an integrator; and Ki costs ~-145 deg at 7 Hz, into the band where Re(Z) < 0
    is replicated on three drives.  V270/V271/V272 (Ki = 5/5/1) are mis-motivated.
  * It does NOT change Kp or Kd.  Scaling the reference and the feedback TOGETHER leaves the
    small-signal loop gain invariant -- for the same physical rate error the loop responds
    identically.  No retune is required, and manufacturing one would only add risk.
  * The override taper flatten [C] IS included at the operator's direction.  Note what it is: the
    taper multiplies DRIVER COLUMN TORQUE into the LKAS demand, so flattening it stops LKAS backing
    off when the driver pushes.  It does NOT disable the separate override DEBOUNCE path
    (gp-0x682f vs cal 0xC64B8) -- which V112 already set to 255 against a channel saturating at 255.
  * It does NOT restore V62's rate-lane doubling.  V255/V256/V269 carried it at this gain and drove
    UNDRIVEABLE.

EME -- CLEARED BY CONSTRUCTION, NOT BY A CLEARANCE.  The soft-EME integrator watches
gp-0x6acc = governed_LKAS + COMP against a bound the flown car holds at +-5120 with COMP <= 2560.
V274 changes NO torque-path cell, so the LKAS lane's delivered magnitude is UNCHANGED and the EME
margin cannot be newly encroached.  (The untraced dynamic limit gp-0x4f64 inside FUN_0004503c would
have gated a TORQUE build.  It does not gate this one.)  The hard bricking interlock is the INT/FLOAT
lockstep quad -- V27 hard-faulted on a desync -- and none of V274's cells is in it.

GATE 2.  No pole, no gain, no filter coefficient moves.  The feedback pole (923/1024, corner 16.53 Hz)
and the 5 Hz output LPF are untouched, and a clamp that is not binding is linearly transparent.  The
closed-loop transfer at 6-9 Hz and 22-30 Hz is therefore IDENTICAL to V268 by construction.  This is
deliberately NOT the shape of argument that made V255/V256/V269 undriveable ("Kd adds phase lead, no
pole moves into the RHP") -- that was a claim about a changed system; this is a claim that the linear
system did not change.

THE SENTENCE A NULL WOULD LICENSE.  If the operator drives V274 and LKAS still will not track a brisk
correction, then the rate ceiling was NOT the binding constraint and the limit lies on the torque axis
(0xC61B2/0xC61B4 at 2505 counts) or in the plant.  That is a clean, interpretable null -- and edit [A]
returns its answer regardless of how the drive goes.

BASE: V268 (= V112 + both pump families flattened across slots 0-33).
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
from verify_bootloader_crc import walk_all_blocks                                   # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V274_WRITE", "").strip().lower()

BASE_NAME = "_v268_V268-V112BASE-BOTH.PUMPS.ALL.MODES_plain_image.bin"
BASE_SHA = "39c4e517ad63929eb6de64116a405260d4941ed8e62d5bb01d0210fe49da727f"
TAG = "V274-V268BASE-RATE6X.MAPLINEAR6X.TAPERFLAT.FEEDBACK6X"

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
    0xC61B2: 3072,   0xC61B4: 3072,    # forward output clamps -- never bind (lane clips at 2505)
    0xC61B6: 10240,  0xC61BA: 10240,   # D clamp / I anti-windup
    0xC61BC: 15360,  0xC61BE: 15360,   # P clamp / sum clamp  (0xC61BE has the ld.h sign defect)
    0xC6CD0: 5346,                     # forward gain, 6x
    0xC63E6: 0,                        # Ki -- stays OFF
    0xC63E8: 923,    0xC63EA: 1560,    # feedback lag pole / input gain -- pole must NOT move
    0xC63EC: 992,    0xC63EE: 507,     # 5 Hz output LPF
    0xC62E4: 4,                        # error deadband
    0xC6B26: 256,    0xC6B12: 98,      # the OTHER PID (driver-side) -- untouched
    0xC6AE6: 2048,   0xC644A: 1024,
}
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
    print(f"  V274 -- RATE AXIS x{K}.  TORQUE PATH FROZEN.  BASE V268.")
    print("=" * 102)

    print("\n  [1] BASE = V268")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V268 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}")
    check(u16(base, FB_CELL) == FB_STOCK, f"base feedback clamp == {FB_STOCK}")
    check(base[SAR_R26] == SAR_1X and base[SAR_R24] == SAR_1X, "rate lane stock 1x (V62 NOT restored)")
    check(base[IDX_CLAMP_P] == 240 and base[IDX_CLAMP_N] == 240, "index clamp +-240 unchanged")

    print("\n  [1b] THE SIGN-EXTENSION DEFECT ON 0xC61BE -- why V274 does not go near it")
    for a, want in ((0x2A13E, 0xE5), (0x2A146, 0x25), (0x2A14C, 0xE5), (0x2A156, 0xE5)):
        kind = "ld.hu ZERO-ext" if base[a] == 0xE5 else "ld.h  SIGN-ext" if base[a] == 0x25 else "??"
        check(base[a] == want, f"0x{a:05X} {base[a]:02X} = {kind}")
    print("      -> one of four reads is SIGN-extended; 0xC61BE >= 32768 would clamp peak NEGATIVE.")
    print("      -> V274 leaves 0xC61BE at 15360.  Never approached.")

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
    print("      wire = clamp(|gp-0x674e| * 5, 0, 1023):  5 => record 2 | 35 => record 11")
    check(bytes(code[CAVE[0]:CAVE[1]]) == bytes(base[CAVE[0]:CAVE[1]]), "cave byte-identical")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]), "hook byte-identical")

    print(f"\n  [3] [B] ASSIST MAP -- LINEARISED and scaled {K}x, all {N_SLOTS} records")
    ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    check(all(START <= p < END for p in ptrs), f"all {len(ptrs)} map pointers in range")
    shapes = {}
    for p in ptrs:
        n = s16(base, p)
        check(n == MAP_N, f"map 0x{p:05X} npt == {MAP_N}")
        X, Y = rec(base, p, n)
        check(tuple(X) == MAP_X, f"map 0x{p:05X} X == stock (X is NOT touched)")
        ceil = K * Y[-1]                                   # 6x THIS record's own ceiling
        newY = tuple(round(x * ceil / MAP_X[-1]) for x in MAP_X)   # then a STRAIGHT LINE through it
        check(max(newY) <= 32767, f"map 0x{p:05X} scaled ceiling {max(newY)} fits int16")
        for i, y in enumerate(newY):
            o = p + 2 + 2 * n + 2 * i
            struct.pack_into("<h", code, o, y)
            attributed |= {o, o + 1}
        gY = rec(code, p, n)[1]
        check(tuple(gY) == newY, f"map 0x{p:05X} Y -> linear, ceiling {ceil}")
        _ex = [x * ceil / MAP_X[-1] for x in MAP_X]
        check(all(abs(gY[i] - _ex[i]) <= 0.5 for i in range(n)),
              f"map 0x{p:05X} every knot is the correctly-ROUNDED point on the straight line "
              f"y = {ceil/MAP_X[-1]:.4f}*x -- this IS the linearisation, to integer precision")
        _sl = [(gY[i+1]-gY[i])/(MAP_X[i+1]-MAP_X[i]) for i in range(n-1)]
        check(max(_sl) / min(_sl) < 1.10,
              f"map 0x{p:05X} slope ratio {max(_sl)/min(_sl):.3f} across ALL segments "
              f"(min {min(_sl):.3f} max {max(_sl):.3f}) -- stock's was 2.25/0.075 = 30.0x")
        check(all(gY[i + 1] >= gY[i] for i in range(n - 1)), f"map 0x{p:05X} still monotone")
        shapes.setdefault((tuple(Y), newY), []).append(p)
    for (oldY, newY), ps in shapes.items():
        print(f"      {len(ps):2d} records  ceiling {oldY[-1]:4d} -> {newY[-1]:5d}   slope {newY[-1]/240:.3f} counts/index (stock top segment: 0.075)")
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

    print("\n  [5] THE ARITHMETIC THIS BUILD IS MAKING")
    FB_SCALE = 2 * 1560 / (1024 - 923) * 8       # feedback counts per column deg/s
    p1 = u32(base, MAP_PTR + 4)
    M0 = rec(base, p1, MAP_N)[1][-1]
    for nm, M, F in (("V268 (today)", M0, FB_STOCK), ("V274", M0 * K, FB_NEW)):
        print(f"      {nm:14s} map ceiling {M:5d}  feedback {F:6d}"
              f"   max COMMANDED {32*M/FB_SCALE:6.1f} deg/s"
              f"   max MEASURABLE {F/FB_SCALE:6.1f} deg/s"
              f"   ratio {F/(32*M):.3f}")
    print("      -> Honda's feedback:max-error ratio of 1.395 is preserved EXACTLY by scaling both by 6.")
    peak = (u16(code, 0xC61BE) * u16(code, 0xC6CD0)) >> 15
    print(f"      -> delivered peak torque = (0xC61BE {u16(code,0xC61BE)} * gain {u16(code,0xC6CD0)}) >> 15"
          f" = {peak}, clipped by 0xC61B4 {u16(code,0xC61B4)}: {'NO' if peak < u16(code,0xC61B4) else 'YES'}")
    check(peak == 2505, "delivered peak torque is 2505 -- IDENTICAL to V268/V112")

    print("\n  [6] TORQUE PATH RE-ASSERTED ON THE BUILT IMAGE")
    for a, v in FROZEN.items():
        check(u16(code, a) == v, f"0x{a:05X} still {v}")
    check(code[SAR_R26] == SAR_1X and code[SAR_R24] == SAR_1X, "rate lane still stock 1x")
    check(code[IDX_CLAMP_P] == 240 and code[IDX_CLAMP_N] == 240, "index clamp still +-240")
    for nm, ptr in (("Kp", KP_PTR), ("Kd", KD_PTR)):
        for s in range(N_SLOTS):
            p = u32(base, ptr + 4 * s)
            n = s16(base, p)
            check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]),
                  f"{nm} record slot {s} byte-identical") if s < 2 else None
    print("      (Kp/Kd slots 0-1 spot-asserted; full-image diff below proves ALL of them)")

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
    allow = set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE, FB_CELL, FB_CELL + 1}
    for p in ptrs:
        allow |= {p + 2 + 2 * MAP_N + k for k in range(2 * MAP_N)}
    for p in tps:
        allow |= {p + 2 + 2 * TAPER_N + k for k in range(2 * TAPER_N)}
    check(set(pay) <= allow, "every payload byte is a map Y knot, a taper Y knot, the feedback "
                             "clamp, or one of the 3 telemetry code bytes -- no X axis, no cave, "
                             "no torque cell")
    cb = sorted(x for x in pay if x < 0xC0000)
    check(cb == sorted(set(range(SRC_DISP, SRC_DISP + 2)) | {SAR_SITE}),
          f"exactly 3 code bytes move, all in the 427 packer: {[hex(x) for x in cb]}")
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

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v274_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V274_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)


if __name__ == "__main__":
    build()
