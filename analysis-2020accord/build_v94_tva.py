#!/usr/bin/env python3
r"""build_v94_tva.py -- V94 = V93's lever + the INSTRUMENT RESCALED so it can still see it.

🛑 WHY V94 EXISTS.  V93 is CORRECT but its instrument is not sized for its own edit.  427 packs
`wire = (|gp-0x6b26| * 5) >> 3`, and V93 divides `|gp-0x6b26|` by 4 -- so on route 78's measured
distribution, **87.5 % of engaged frames would land on wire <= 1**.  The primary endpoint would be
measured at 1-2 LSB.  `sar 3 -> sar 1` is exactly x4 and CANCELS the x0.25: the V94 wire
distribution reproduces route 78's as-flown one almost exactly (p75/p90/p95/p99/max
5/10/17/37/137 vs 5/10/17/38/138), making the ratio test QUANTISATION-IDENTICAL.
⊕ And because `gp-0x6b26 = -K * gp-0x6c2c` with K KNOWN (we set it), a full-resolution 427 makes
the EPS-motor ACCELERATION itself recoverable -- the lever's INPUT, never telemetered on any
build -- with NO cave change and therefore none of the cave risk class.

V93 (image 779180f8..., rwd 9c93dca6...) is NOT superseded and NOT dead: it is a valid, verified
artefact that simply measures itself poorly.  V94 is a NEW BUILD NUMBER precisely so V93's
published hashes stay meaningful -- see feedback-name-superseded-hashes-dead-not-merely-omitted.

    base   _v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin
           sha256 28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db

    0xD6A6C  mode 24 MANUAL  Y row  (-9830,-5734,-1966) -> (-4915,-2867,-983)   x0.50  EXACT
    0xD7A5C  mode 26 ENGAGED Y row  (-9830,-5734,-1966) -> (-2458,-1434,-492)   x0.25
    0xD7A6C  mode 27         Y row  (-9830,-5734,-1966) -> (-2458,-1434,-492)   x0.25
        ⊕ x0.25 does NOT divide exactly: Python `//` FLOORS toward -inf, so -9830//4 = -2458 (not
          -2457). For a NEGATIVE row that rounds AWAY from zero, i.e. very slightly LESS reduction
          than a true x0.25 -- the conservative direction. Values are asserted exactly, not derived
          twice, so the built image is the authority here.
    0xC640A  FALLBACK-2 flat gain          -8192 -> -6144                       x0.75
    0xC640C  FALLBACK-1 flat gain          -3277 -> -2458                       x0.75
    0x55E10  CAN 427 packer  `sar 0x3,r6` -> `sar 0x1,r6`   a3 -> a1   (x4 resolution)

Six edits: 22 calibration bytes + ONE code byte + 16 CRC bytes. NO cave change. The V90 cave
(4-rung cave + CAN 427 = gp-0x6b26) is carried byte-for-byte, which is the whole point: 427 measures
this build's own dose directly.

===================================================================================================
🛑🛑 WHY THE DIRECTION IS REVERSED -- READ THIS FIRST
===================================================================================================
`FUN_00041464` was traced to the instruction on 2026-08-11 and `gp-0x6c2c` is a FIRST DIFFERENCE of
the filtered motor rate:

    415e8: add  r28, r24     ; r24 = NEW filtered rate
    415fc: ble  0x41600      ; the NORMAL path skips the reset below
    415fe: mov  r24, r7      ; RESET path only (invalid state / first tick) => difference forced 0
    41602: sub  r7, r9       ; 🛑 r9 = NEW - OLD  ==  THE FIRST DIFFERENCE
    41612: shl  0x5, r9      ; x32, clamped +-0xfa0000 -> r22
    4162e: mov  r22, r26     ; the EMA input IS that clamped difference
    41644: st.w r26, -0x35a0, gp   ; -> >>9 -> gp-0x6c2c

⇒ **`gp-0x6c2c` is angular ACCELERATION**, so `gp-0x6b26 = -K * accel` and the aggregator's
unweighted `add` puts `-K*alpha` into the motor command:

    J*alpha = T_driver + T_motor,  T_motor ∋ -K*alpha   ⇒   (J + K)*alpha = T_driver

**`0xCBE74` ADDS APPARENT INERTIA. It is 90 deg out of phase with velocity: it stores energy and
dissipates NONE.** It cannot add damping and could never have fixed an anti-damping problem.

🛑 `build_v91_tva.py` says of this same term: *"The Y row is NEGATIVE, so gp-0x6b26 carries the
OPPOSITE sign to gp-0x6c2c => the term is genuinely DISSIPATIVE (it opposes motor rate)."*
**THAT IS WRONG. It opposes ACCELERATION.** Every document calling `0xCBE74`
"friction/**damping**-comp" inherits the error. Raising K makes the wheel heavier and pulls the
resonance DOWN, further into the 6-9 Hz band the driver's own input excites -- the opposite of the
operator's *"turning angle rate still limited by this."*

===================================================================================================
LINEAGE -- 13 builds have touched this LERP family and EVERY ONE raised it or restored stock
===================================================================================================
V73, V74, V75, V76, V76_v38base, V77, V81, V83a, V84, V86, V90, V91, V92.
    V74/V75  x1.5 on 14 records          -> BOTH HARD-FAULTED (latched loss of assist)
    V81      friction row -> STOCK        -> fault-free (route 67)
    V91/V92  x1.5 on modes 26/27          -> fault-free, and MEASURED INERT (see below)
**LOWERING IT HAS NEVER BEEN TRIED.** That is what makes V93 a new lever and not a re-run.

===================================================================================================
🛑 WHY V91/V92 WERE INERT, AND HOW V93 RESOLVES IT IN ONE FLIGHT
===================================================================================================
Routes 78/79 measured the V91/V92 x1.5 dose as INERT at `gp-0x6b26`: engaged cell-stratified ratio
**0.99 [0.91, 1.26]** against a pre-registered 1.50, with the MANUAL negative control holding at
**1.009 [0.982, 1.047]**, and a three-way duty of **0.167 / 0.161 / 0.165** against a needed 0.204.
V92's identity is proven single-frame, and its image carries the dosed row -- so the dose was ON THE
CAR and did nothing.

`FUN_00036c12` has THREE gain sources, and only one of them is the mode record:

    if (gp-0x671a >= 0xFF || gp-0x67f4 != 1)      gain = cal(0xC640C) = -3277     [FALLBACK-1]
    else if (gp-0x671a >= cal(0xC64FD) = 5)       gain = cal(0xC640A) = -8192     [FALLBACK-2]
    else                                          gain = LERP(0xCBE74[mode])      [the records]

V91/V92 wrote ONLY the records. **V93 writes all three, at THREE DIFFERENT FACTORS**, so the engaged
`|gp-0x6b26|` ratio against route 78 names the live branch on the first drive:

    ratio 0.25  ⇒ mode 26 IS the engaged record (the kit's standing assumption)
    ratio 0.50  ⇒ the car reads MODE 24 IN BOTH STATES -- the suspected cause of the V91/V92 null
    ratio 0.75  ⇒ a FALLBACK constant is live; the mode records are dead and 0xC640A/C is the lever
    ratio 1.00  ⇒ something upstream is wrong; STOP, do not dose further

**Every branch delivers a reduction**, so this is a fix attempt, not a probe.
⚠ **THE MANUAL NEGATIVE CONTROL IS DELIBERATELY SPENT.** Mode 24 is written at x0.50, so manual is
no longer a null control -- it becomes the second point of a two-point calibration. That is the
price of the discriminator, and it is paid knowingly.
⚠ At v = 0 the mode-26 Y[0] (-2457) and FALLBACK-1 (-2458) are within one count. They separate on
the SPEED SHAPE (the record LERPs to -491 at 90 km/h; the fallback is flat), so score the
per-speed-bin arm, not just the pooled median.

===================================================================================================
SIZING -- LOWERING IS STRICTLY SAFE ON BOTH BINDING BOUNDS
===================================================================================================
Both bounds that capped V91 at ~1.60 are bounds on the MAGNITUDE of the product, so a REDUCTION
moves strictly away from both:
    CLIP:     |gp-0x6b26| shrinks  ⇒ the +-511 rail (0xC407E) cannot be approached.
              🛑 A railed lane is sign(gp-0x6c2c) x 511 -- a Coulomb RELAY, the V80 mechanism.
    OVERFLOW: the `mul r13,r6,r0` (x0x111, high half discarded) product shrinks ⇒ wraparound
              moves further away.
Both are asserted numerically below rather than argued.

GATE 1 (RAM ownership): NOT ENGAGED -- cal-only, no cave, no new RAM.
GATE 2 (closed-loop stability): a scalar on an existing term adds ZERO phase at any frequency and
strictly REDUCES that lane's loop gain. The effect is bounded: `gp-0x6b26` is 2-18 % of the ~208 ct
engaged command median, so removing three quarters of it moves `omega_n = sqrt(k/(J+K))` by at most
**~1.10x**. A ~10 % shift, not a band jump.

⚠ **THE HONEST RISK:** apparent inertia is part of what makes the wheel feel planted. Removing most
of it may read as nervous or darty on-centre, and raising `omega_n` moves it TOWARD the 18-22 Hz
band the operator currently calls sufficient. If he reports either, that is a real cost, not noise.

⚠ **THIS DOES NOT ADDRESS THE ANTI-DAMPING.** `Re(Z) < 0` from 2 to ~24 Hz replicated on all three
of routes 77/78/79 and is strongest in the micro regime. No firmware lever is justified against it
until the MANUAL HANDS-OFF COAST separates plant from loop; routes 78/79 held 1.8 s and 0.0 s of it.

Usage:
    python build_v93_tva.py                    # DRY RUN, writes nothing
    ACCORD_V94_WRITE=bin python build_v93_tva.py
    ACCORD_V94_WRITE=rwd python build_v93_tva.py
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V94_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path(
    "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin"))
BASE_SHA = "28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))

# ---------------------------------------------------------------------------------------------
# THE LEVER
# ---------------------------------------------------------------------------------------------
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_N_MODES = 34
REC_N_OFF, REC_X_OFF, REC_Y_OFF, REC_LEN = 0x00, 0x02, 0x08, 0x10
FRICTION_NPT = 3
FRICTION_X = (0, 1280, 5760)               # counts of voted speed; 64 ct/km/h => [0, 20, 90] km/h
FRICTION_Y_STOCK = (-9830, -5734, -1966)

# mode -> (numerator, denominator).  THREE DISTINCT FACTORS = the branch discriminator.
MODE_FACTORS = {24: (1, 2), 26: (1, 4), 27: (1, 4)}
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)

TP = 0xBF000                               # 🛑 tp+0x740A = 0xC640A, NOT 0xC740A
FALLBACK_NUM, FALLBACK_DEN = 3, 4          # x0.75
FALLBACKS = {TP + 0x740A: -8192,           # 0xC640A  gp-0x671a >= cal(0xC64FD)
             TP + 0x740C: -3277}           # 0xC640C  outer gate fails
GATE_BYTE_ADDR, GATE_BYTE_VALUE = 0xC64FD, 5        # read-only here; asserted UNCHANGED

PACKER_ADDR = 0x55E10                      # `sar 0x3,r6` in the CAN 427 packer
PACKER_STOCK, PACKER_NEW = 0xA3, 0xA1      # byte0 = 0xA0 | imm5  =>  sar 3 -> sar 1
PACKER_HW_TAIL = 0x32                      # byte1 = (r6 << 3) | 0x02, MUST NOT MOVE
CLAMP_ADDR, CLAMP_VALUE = 0xC407E, 511
MUL_IMM = 0x111
INT32_MAX = 2 ** 31 - 1
PRODUCER_CEILING = 32000                   # gp-0x6c2c's own hard bound
ROUTE77_ENGAGED_MAX = 319.1                # measured |gp-0x6b26| at the STOCK Y row

# ---------------------------------------------------------------------------------------------
FROZEN = {
    0xC407E: (2, 511, "🛑 HARD-FAULT INTERLOCK CLAMP -- Honda's 511, one under its own 512 trip"),
    0xC40D2: (2, 204, "K1 modelled Coulomb friction -- V89's lever, CARRIED unchanged"),
    0xC4080: (2, 0, "K0 pure-Coulomb arm -- the recorded NEVER-RAISE relay hazard, stays 0"),
    0xC40BC: (2, 600, "friction relay gate -- 600. 6000 measured 2.3x WORSE"),
    0xC40D0: (2, 408, "friction EMA alpha (16.7 Hz)"),
    0xC40D4: (2, 573, "command-branch EMA -- V86's FALSIFIED lever"),
    0xC40D8: (2, 3686, "friction-family constant"),
    0xC646E: (2, 1428, "INERTIA gain -- do NOT propose, raising it makes the wheel lighter"),
    0xC63A6: (2, 1024, "observer weight on gp-0x6b26 (Path 2) -- FROZEN"),
    0xC6200: (2, 8192, "residual clamp"),
    0xC6446: (2, 5244, "Lever B arm -- V88's 5244"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC6CD0: (2, 3564, "private forward LKAS gain = 4.000x, NEVER lower"),
    0xC616C: (2, 0, "🛑 NEVER-RAISE driver-torque Coulomb relay -- stays 0"),
    0xC64FD: (1, 5, "🛑 the FALLBACK-2 gate on gp-0x671a -- V94 does NOT move it"),
    0x3AA96: (1, 0xFB, "Lever B gate -- V88's"),
    0x454FE: (1, 0xB5, "V42's ratchet fix -- restored at V80"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
}

CAVE_BASE, CAVE_END = 0xC4B34, 0xC4B80
V90_CAVE = bytes.fromhex(
    "003a2437da946032ae05483a24370a946032ae058031a9326032a305443a24371e956032"
    "a305423a243700946032ae05413ac43a483a8437edeac636070007314437ecea2436e8ea7f00ffff")
HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")
R427_ADDR, R427_DISP = 0x55DF2, 0x6B26

VARIANT_TOKEN = "V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75-427.SAR1"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v94_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V94-{TAG}-0x{START:X}-0x{END:X}.rwd")

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"🛑 ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def rd(b, a, n):
    return bytes(b[a:a + n])


def rec_addr(buf, mode):
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_fields(buf, mode):
    r = rec_addr(buf, mode)
    n = s16(buf, r + REC_N_OFF)
    X = tuple(s16(buf, r + REC_X_OFF + 2 * i) for i in range(FRICTION_NPT))
    Y = tuple(s16(buf, r + REC_Y_OFF + 2 * i) for i in range(FRICTION_NPT))
    return r, n, X, Y


def scaled(num, den):
    return tuple(y * num // den for y in FRICTION_Y_STOCK)


def assert_frozen(buf, where):
    for a, (n, v, why) in sorted(FROZEN.items()):
        got = buf[a] if n == 1 else u16(buf, a)
        check(got == v, f"{where}: 0x{a:05X} = {got} (== {v}) -- {why}")


# =============================================================================================
def main():
    print("=" * 102)
    print(f"  V94  [{VARIANT_TOKEN}]")
    print("  🛑 THE FIRST BUILD EVER TO **LOWER** THE 0xCBE74 TERM.")
    print("     gp-0x6c2c is a FIRST DIFFERENCE of filtered motor rate = ACCELERATION, so")
    print("     gp-0x6b26 = -K*accel ADDS APPARENT INERTIA. It dissipates nothing.")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    print(f"    {BASE_BIN}\n    sha256 {base_sha}  ({len(base)} bytes)")
    check(len(base) == 0x100000, "base image is 1 MiB")
    check(base_sha == BASE_SHA, f"base sha256 == the flown V90's {BASE_SHA}")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain verifies 50/50")
    assert_frozen(base, "base")

    # ------------------------------------------------------------------------------------
    print("\n  [2] POINTER IDENTITY -- every record DEREFERENCED from 0xCBE74 + mode*4")
    print("      🛑 The mode number is printed beside every address. This is the discipline that")
    print("         caught 0xD6A5C being mode 23, not 24.")
    before = {}
    for m in range(FRICTION_N_MODES):
        before[m] = rec_fields(base, m)
    for m in sorted(set(list(MODE_FACTORS) + list(MANUAL_MODES) + list(ENGAGED_MODES) + [23, 25])):
        r, n, X, Y = before[m]
        tgt = " <-- V93 WRITES" if m in MODE_FACTORS else ""
        print(f"      mode {m:2d}  ptr 0x{FRICTION_PTR_ARRAY + m * 4:05X} -> rec 0x{r:05X}  "
              f"n={n}  X={X}  Y={Y}{tgt}")
    for m in MODE_FACTORS:
        r, n, X, Y = before[m]
        check(n == FRICTION_NPT, f"mode {m}: n == {FRICTION_NPT}")
        check(X == FRICTION_X, f"mode {m}: X == {FRICTION_X}")
        check(Y == FRICTION_Y_STOCK, f"mode {m}: Y == STOCK {FRICTION_Y_STOCK}")

    tgt_recs = {m: before[m][0] for m in MODE_FACTORS}
    check(len(set(tgt_recs.values())) == len(tgt_recs),
          f"the three target records are DISTINCT addresses "
          f"{ {m: hex(a) for m, a in tgt_recs.items()} } -- WITHOUT THIS THE DISCRIMINATOR IS VOID")

    # ------------------------------------------------------------------------------------
    print("\n  [3] 🛑 RECORD-ALIASING SWEEP -- the cal-only equivalent of GATE 1")
    print("      FUN_00034a72 (base assist) indexes EIGHT other pointer arrays by the SAME mode")
    print("      byte. If any of them pointed into a record V93 writes, this edit would silently")
    print("      change BASE ASSIST. Whole-image LE scan for each target record address:")
    for m, ra in sorted(tgt_recs.items()):
        needle = struct.pack("<I", ra)
        hits, i = [], 0
        while True:
            i = bytes(base).find(needle, i)
            if i < 0:
                break
            hits.append(i)
            i += 1
        aligned = [h for h in hits if h % 4 == 0]
        in_array = [h for h in aligned
                    if FRICTION_PTR_ARRAY <= h < FRICTION_PTR_ARRAY + FRICTION_N_MODES * 4]
        outside = [h for h in aligned if h not in in_array]
        print(f"      mode {m:2d} rec 0x{ra:05X}: {len(hits)} raw, {len(aligned)} word-aligned, "
              f"{len(in_array)} inside 0xCBE74[], {len(outside)} OUTSIDE "
              f"{[hex(h) for h in outside[:6]]}")
        check(not outside,
              f"mode {m} record 0x{ra:05X} is pointed to ONLY from the 0xCBE74 array "
              f"=> no other subsystem reads it")
        check(len(in_array) == 1 and in_array[0] == FRICTION_PTR_ARRAY + m * 4,
              f"mode {m} record has exactly ONE pointer, at 0xCBE74+{m}*4")

    # ------------------------------------------------------------------------------------
    print("\n  [4] THE EDITS")
    code = bytearray(base)
    attributed, by_addr = set(), {}

    def poke16(addr, val, why):
        struct.pack_into("<h", code, addr, val)
        for k in range(2):
            attributed.add(addr + k)
            by_addr[addr + k] = why

    for m, (num, den) in sorted(MODE_FACTORS.items()):
        r = before[m][0]
        new = scaled(num, den)
        ya = r + REC_Y_OFF
        for i, v in enumerate(new):
            poke16(ya + 2 * i, v, f"mode {m} friction Y[{i}] x{num}/{den}")
        print(f"      mode {m:2d} rec 0x{r:05X} Y@0x{ya:05X}: {FRICTION_Y_STOCK} -> {new}"
              f"   (x{num}/{den})")
        check(all(abs(v) < abs(s) for v, s in zip(new, FRICTION_Y_STOCK)),
              f"mode {m}: every Y knot is strictly SMALLER in magnitude than stock "
              f"(this build only ever REDUCES)")
        check(all(v < 0 for v in new), f"mode {m}: every Y knot stays NEGATIVE -- no sign flip")

    for a, stock_v in sorted(FALLBACKS.items()):
        check(s16(base, a) == stock_v, f"0x{a:05X} reads stock {stock_v} on the base")
        nv = stock_v * FALLBACK_NUM // FALLBACK_DEN
        poke16(a, nv, f"fallback gain 0x{a:05X} x{FALLBACK_NUM}/{FALLBACK_DEN}")
        print(f"      0x{a:05X} fallback gain: {stock_v} -> {nv}   "
              f"(x{FALLBACK_NUM}/{FALLBACK_DEN})")
        check(abs(nv) < abs(stock_v) and nv < 0,
              f"0x{a:05X}: smaller magnitude, still negative")

    check(len(attributed) == 22, f"exactly 22 calibration bytes written (got {len(attributed)})")

    # ---- the SIXTH edit: one CODE byte, the 427 packer.  Same class as V92's a332->a432.
    print("\n      --- the 427 packer, so the instrument can still see this lever ---")
    check(code[PACKER_ADDR] == PACKER_STOCK,
          f"0x{PACKER_ADDR:05X} reads 0x{PACKER_STOCK:02X} (`sar 0x3,r6`) on the base")
    check(code[PACKER_ADDR + 1] == PACKER_HW_TAIL,
          f"0x{PACKER_ADDR+1:05X} == 0x{PACKER_HW_TAIL:02X} -- the register field is r6, unmoved")
    code[PACKER_ADDR] = PACKER_NEW
    attributed.add(PACKER_ADDR)
    by_addr[PACKER_ADDR] = "CAN 427 packer sar 3 -> sar 1"
    check(code[PACKER_ADDR + 1] == PACKER_HW_TAIL,
          f"after the write 0x{PACKER_ADDR+1:05X} is STILL 0x{PACKER_HW_TAIL:02X} -- only the "
          f"immediate moved, not the register")
    print(f"      0x{PACKER_ADDR:05X}: sar 0x3,r6 -> sar 0x1,r6   (0x{PACKER_STOCK:02X} -> "
          f"0x{PACKER_NEW:02X})   wire = |gp-0x6b26| * 5 >> 1")
    railed = (511 * 5) >> 1
    print(f"      resolution 1.60 -> 0.40 counts/LSB;  a RAILED lane packs to {railed}, which is "
          f"> 1023 ->\n      it CLIPS at |gp-0x6b26| >= 409 = 80 % of the rail. That is an EARLIER "
          f"alarm, not a lost one.")
    check(len(attributed) == 23, f"22 cal bytes + 1 code byte = 23 (got {len(attributed)})")
    check(u16(code, GATE_BYTE_ADDR - 1) == u16(base, GATE_BYTE_ADDR - 1),
          f"0x{GATE_BYTE_ADDR:05X} (the FALLBACK-2 gate = {GATE_BYTE_VALUE}) is UNTOUCHED")

    # ------------------------------------------------------------------------------------
    print("\n  [5] THE DISCRIMINATOR -- predicted engaged |gp-0x6b26| ratio vs route 78")
    print("      ratio 0.25  => mode 26 IS the engaged record")
    print("      ratio 0.50  => the car reads MODE 24 IN BOTH STATES (the suspected V91/V92 cause)")
    print("      ratio 0.75  => a FALLBACK is live; the mode records are dead")
    print("      ratio 1.00  => something upstream is wrong -- STOP")
    m26 = scaled(*MODE_FACTORS[26])
    fb1 = FALLBACKS[TP + 0x740C] * FALLBACK_NUM // FALLBACK_DEN
    print(f"      ⚠ at v=0 mode-26 Y[0] = {m26[0]} and FALLBACK-1 = {fb1} differ by "
          f"{abs(m26[0] - fb1)} count(s)")
    print(f"        => they separate on SPEED SHAPE (record LERPs to {m26[2]} at 90 km/h; the")
    print(f"           fallback is FLAT). Score the PER-SPEED-BIN arm, not just the pooled median.")

    # ------------------------------------------------------------------------------------
    print("\n  [6] SIZING -- a REDUCTION moves strictly AWAY from both binding bounds")
    y_max_new = max(abs(v) for m in MODE_FACTORS for v in scaled(*MODE_FACTORS[m]))
    y_max_all = max(y_max_new, max(abs(v) for v in FALLBACKS.values()) * FALLBACK_NUM
                    // FALLBACK_DEN)
    y_max_stock = max(abs(v) for v in FRICTION_Y_STOCK)
    wrap_stock = INT32_MAX / MUL_IMM * 64 / y_max_stock
    wrap_new = INT32_MAX / MUL_IMM * 64 / y_max_all
    print(f"      largest |Y| stock {y_max_stock}  ->  V93 {y_max_all}")
    print(f"      int32 wrap reachable at |gp-0x6c2c| = {wrap_stock:,.0f} (stock) -> "
          f"{wrap_new:,.0f} (V93), against the producer ceiling {PRODUCER_CEILING:,}")
    check(y_max_all < y_max_stock, "the largest gain magnitude STRICTLY DECREASES")
    check(wrap_new > PRODUCER_CEILING,
          f"int32 wraparound is UNREACHABLE: needs |gp-0x6c2c| = {wrap_new:,.0f} > "
          f"{PRODUCER_CEILING:,}")
    worst = ROUTE77_ENGAGED_MAX * y_max_all / y_max_stock
    print(f"      worst-case |gp-0x6b26| scaling route 77's engaged max {ROUTE77_ENGAGED_MAX}: "
          f"{worst:.1f} vs the +-{CLAMP_VALUE} rail ({100 * worst / CLAMP_VALUE:.1f} %)")
    check(worst < CLAMP_VALUE,
          f"the +-{CLAMP_VALUE} clamp is UNREACHABLE => the lane cannot become a Coulomb relay")

    # ------------------------------------------------------------------------------------
    print("\n  [7] THE V90 INSTRUMENT -- carried byte-for-byte (427 measures this build's own dose)")
    check(rd(code, CAVE_BASE, CAVE_END - CAVE_BASE) == V90_CAVE, "the V90 cave is byte-identical")
    check(rd(code, HOOK_ADDR, 4) == HOOK_BYTES, "the 0x14A cave hook is byte-identical")
    check(rd(code, R427_ADDR, 2) == struct.pack("<h", -R427_DISP),
          "CAN 427 still reads gp-0x6b26 (`ld.h -0x6b26[gp],r6`) -- SOURCE unchanged")
    check(code[PACKER_ADDR] == PACKER_NEW and code[PACKER_ADDR + 1] == PACKER_HW_TAIL,
          "CAN 427 packer is `sar 0x1,r6` -- the ONLY code byte this build moves")
    assert_frozen(code, "built")

    # ------------------------------------------------------------------------------------
    print("\n  [8] CRC -- trailer set DERIVED from the image's own block map")
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit landed on the trailer at 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}"
              f"   owns {len(owners)} of {len(touched)} touched byte(s)")
    derived = {b[1] for b in blocks}
    check(derived == {0xC4FFC, 0xC6FFC, 0xD6FFC, 0xD7FFC},
          f"DERIVED trailer set {sorted(hex(t) for t in derived)} == "
          f"{{0xc4ffc, 0xc6ffc, 0xd6ffc, 0xd7ffc}} -- the packer byte pulls in block 50 "
          f"[0x013000,0x0C4FFC). Derived, then asserted; never hard-coded")
    crc_only = {b[1] + k for b in blocks for k in range(4)}
    check(walk_all_blocks(bytes(code)) == 0,
          "built image CRC chain 50/50 (NECESSARY, NOT SUFFICIENT -- see [9])")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "the CRC-SKIPPED block [0xC5000,0xC5FFC) is byte-identical to the base (V40's brick)")
    check(bytes(code[:START]) == bytes(base[:START]), f"nothing below 0x{START:X} changed")

    # ------------------------------------------------------------------------------------
    print("\n  [9] ZERO-UNATTRIBUTED FULL BYTE DIFF")
    runs, i = [], START
    while i < END:
        if code[i] != base[i]:
            j = i
            while j < END and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1
    unattributed = []
    for lo, hi in runs:
        for a in range(lo, hi + 1):
            if a not in by_addr and a not in crc_only:
                unattributed.append(a)
    total = sum(hi - lo + 1 for lo, hi in runs)
    print(f"      {len(runs)} run(s), {total} byte(s) differ from the V90 base:")
    for lo, hi in runs:
        why = by_addr.get(lo, "CRC trailer" if lo in crc_only else "🛑 UNATTRIBUTED")
        print(f"        0x{lo:06X}-0x{hi:06X}  ({hi - lo + 1:3d} B)  {why}")
    # 🛑 DERIVE the expected total; never hard-code it. A written byte whose new value happens to
    #    equal the base's does NOT appear in the diff -- here -8192 (0xE000) -> -6144 (0xE800)
    #    share their low byte, so 22 bytes are WRITTEN but only 21 DIFFER. Asserting a constant 34
    #    would have failed a correct build, which is exactly the wrong kind of check.
    coincide = sorted(a for a in attributed if code[a] == base[a])
    expected = (len(attributed) - len(coincide)) + len(crc_only)
    check(not unattributed,
          f"ZERO unattributed bytes ({total} differ = {len(attributed)} cal written "
          f"- {len(coincide)} coinciding + {len(crc_only)} CRC)")
    for a in coincide:
        print(f"        ⊕ 0x{a:06X} was WRITTEN but equals the base byte ({by_addr[a]})")
    check(total == expected,
          f"the diff total {total} == the DERIVED expectation {expected}")
    check(len(crc_only) == 16, f"exactly 4 CRC trailers = 16 bytes (got {len(crc_only)})")

    # ------------------------------------------------------------------------------------
    print("\n  [10] LINEAGE -- is this really the first REDUCTION?")
    stock_p = Path(STOCK_BIN)
    if stock_p.exists():
        stock = stock_p.read_bytes()
        same = [m for m in range(FRICTION_N_MODES)
                if rec_fields(stock, m)[3] == before[m][3]]
        check(len(same) == FRICTION_N_MODES,
              f"the V90 base is BYTE-STOCK on all {FRICTION_N_MODES} friction records")
        for a, v in sorted(FALLBACKS.items()):
            check(s16(stock, a) == v, f"stock 0x{a:05X} == {v} => V94 is its FIRST movement ever")

    # ------------------------------------------------------------------------------------
    print("\n  [11] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V94 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "the decoded .rwd payload is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC chain 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V94_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            print("\n  [12] 🛑 FROM-DISK -- the SHIPPED .rwd re-read, re-hashed, decoded, re-asserted")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha,
                  f"shipped .rwd re-read from disk, sha256 {rwd_sha}")
            FF.assert_x31_checksum(shipped, "V94 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "the SHIPPED .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain 50/50")
            assert_frozen(sd, "shipped .rwd from disk")
            for m, (num, den) in sorted(MODE_FACTORS.items()):
                check(rec_fields(sd, m)[3] == scaled(num, den),
                      f"shipped .rwd: mode {m} Y = {scaled(num, den)}")
                check(rec_fields(sd, m)[2] == FRICTION_X,
                      f"shipped .rwd: mode {m} X = {FRICTION_X} UNCHANGED")
            check(rec_fields(sd, 25)[3] == FRICTION_Y_STOCK,
                  "shipped .rwd: mode 25 Y is BYTE-STOCK (only 24/26/27 were written)")
            for a, v in sorted(FALLBACKS.items()):
                want = v * FALLBACK_NUM // FALLBACK_DEN
                check(s16(sd, a) == want, f"shipped .rwd: 0x{a:05X} = {want}")
            check(sd[GATE_BYTE_ADDR] == GATE_BYTE_VALUE,
                  f"shipped .rwd: 0x{GATE_BYTE_ADDR:05X} = {GATE_BYTE_VALUE} UNTOUCHED")
            check(rd(sd, CAVE_BASE, CAVE_END - CAVE_BASE) == V90_CAVE,
                  "shipped .rwd: the V90 cave is byte-identical")
            check(rd(sd, R427_ADDR, 2) == struct.pack("<h", -R427_DISP),
                  "shipped .rwd: CAN 427 still reads gp-0x6b26")
            check(sd[PACKER_ADDR] == PACKER_NEW and sd[PACKER_ADDR + 1] == PACKER_HW_TAIL,
                  f"shipped .rwd: 0x{PACKER_ADDR:05X} = 0x{PACKER_NEW:02X} 0x{PACKER_HW_TAIL:02X} "
                  f"(`sar 0x1,r6`)")
            on_disk = Path(BIN_OUT).read_bytes()
            check(hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code),
                  f"the plain image re-read from disk hashes to {img_sha}")

    print("\n" + "=" * 102)
    print(f"  V94 [{VARIANT_TOKEN}]     {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 22 cal bytes + ONE code byte. The FIRST build ever to LOWER this term. Mode 24")
    print("     x0.50, modes 26/27 x0.25, both fallbacks x0.75 -- three factors so the flight names")
    print("     the live branch. 427 packer sar 3 -> sar 1 so the instrument can still SEE the")
    print("     lever it is dosing: 87.5 % of engaged frames would otherwise land on wire <= 1.")
    print("  ⚠ The MANUAL negative control is deliberately SPENT (mode 24 is written).")
    print("  ⚠ This does NOT address the 2-26 Hz anti-damping. The hands-off coast is still owed.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    main()
