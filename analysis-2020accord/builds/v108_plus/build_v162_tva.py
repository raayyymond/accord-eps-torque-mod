#!/usr/bin/env python3
r"""
V162 -- GIVE THE RESONANCE PID ITS AUTHORITY BACK IN THE RATCHET'S OWN BAND.
        0xC67C4 : 1280 -> 512.  Base = V122BASE.  ONE HALFWORD.  A VIRGIN CELL.

THE LEVER, AND WHY IT IS THE GOLDEN MODEL'S OWN RECOMMENDATION
--------------------------------------------------------------
The model's elimination is explicit:

    "for 52-70% of the return the LKAS lane is a DC CONSTANT, yet the 6-9 Hz |tq| envelope is
     unchanged ... A constant cannot carry 7.8 Hz => THE RINGING ENTERS THROUGH A SENSOR-FED LANE,
     NOT THE COMMAND LANE.  Excludes every command-side lever and leaves {r24/r26, gp-0x6ad4,
     gp-0x6b26, gp-0x6bbe, the V89 plant-model path}."

and of those survivors it singles this one out:

    "LIVE gp-0x6ad4 resonance PID -- the most reachable authority of any gated lane HERE: its
     ceiling LERP 0xC67C2 (X=[128,1280,3200] Y=[0,1024,1024] on voted speed) reads p50 395-558 /
     p90 ~830, i.e. 2-3x the 164-341 quoted elsewhere, because 6-20 km/h is FASTER than the
     4.9-8.0 km/h ratchet episodes that number came from.  V56's mute of this lane was scored at
     ~21 Hz -- the lane has NEVER been scored at 6-9 Hz, so it is OPEN, not eliminated."

That last sentence overturns the accord-v57/v56 memory which recorded gp-0x6ad4 as eliminated.  An
elimination scored at 21 Hz does not eliminate a 6-9 Hz role, and the ratchet is 6-9 Hz.

WHAT THE TABLE DOES, AND THE ARITHMETIC
----------------------------------------
0xC67BE is a (0, 3) knot-count header; X at 0xC67C2, Y at 0xC67C8; axis = voted speed gp-0x6a5e at
64 counts/km/h.  Stock X = [128, 1280, 3200] = [2, 20, 50] km/h, Y = [0, 1024, 1024].

        speed      stock ceiling      as % of full authority
         2 km/h            0                0.0 %
         3 km/h           56                5.5 %
         5 km/h          170               16.6 %      <- the ratchet's own band
         8 km/h          341               33.3 %
        20 km/h         1024              100.0 %

=> THE LANE WHOSE JOB IS TO DAMP RESONANCE IS THROTTLED TO ABOUT ONE SIXTH OF ITS AUTHORITY
   EXACTLY WHERE THE RATCHET LIVES.  The model's own 164-341 figure for the 4.9-8.0 km/h ratchet
   episodes reproduces from these bytes exactly.

Moving X[1] from 1280 to 512 puts full authority at 8 km/h instead of 20 km/h:

        speed      stock -> new        ratio
         2 km/h        0 ->    0        unchanged (parking protection intact)
         3 km/h       56 ->  170        x3.00
         5 km/h      170 ->  512        x3.00
         8 km/h      341 -> 1024        x3.00
        12 km/h      568 -> 1024        x1.80
        20 km/h     1024 -> 1024        unchanged
        40 km/h     1024 -> 1024        unchanged

WHY THIS DIRECTION IS THE SAFE ONE
-----------------------------------
[EVIDENCE] It RELEASES authority and never removes any: the ceiling is >= stock at every speed.
[EVIDENCE] X[0] = 128 is UNTOUCHED, so at and below 2 km/h the ceiling stays EXACTLY 0 and Honda's
standstill/parking protection is byte-for-byte intact.
[EVIDENCE] At 20 km/h and above nothing changes at all -- the edit is confined to the creep band.
[EVIDENCE] Y is UNTOUCHED.  The ceiling's VALUE stays Honda's own 1024; only the SPEED at which it
is reached moves.  Honda already runs this lane at FULL authority above 20 km/h and the car does not
ratchet there, so this moves the creep band TOWARD a configuration that is already known-good on
this car rather than into unexplored territory.
[EVIDENCE] The axis is VEHICLE SPEED, which varies over seconds.  It cannot modulate at 6-9 Hz, so
the parametric-pump failure mode that governs every rate-axis edit does not apply here.
[EVIDENCE] 0xC67C4 is VIRGIN: (128, 1280, 0) on all 161 build images -- no build has ever touched
this table, so there is no interaction with any historical edit.
[EVIDENCE] X stays strictly ascending with no collapsed knot; a zero-width LERP segment divides by
zero and the shape gate asserts against it.
=> cal-only, one halfword, outside the cave/bricking class.

WHAT IS NOT ESTABLISHED
-----------------------
[BELIEF] that gp-0x6ad4's PHASE is favourable at 6-9 Hz.  It is a resonance controller, but its
design target may be the ~21 Hz mode; a controller phased for 21 Hz can have the wrong phase at
7.8 Hz, in which case MORE authority makes the ratchet WORSE, not better.  This is the single real
risk of this build and it cannot be settled statically -- the lane has never been scored at 6-9 Hz,
which is precisely why the model calls it OPEN.  Mitigation: the change is confined to 2-20 km/h and
reverts to stock above that, so any adverse effect is bounded to the creep band and the operator can
feel it immediately at low speed rather than discovering it at highway speed.
[NOTE] If the drive is worse, the diagnosis is unambiguous and the fix is to revert this one
halfword; X[1] can also be moved to 768 (12 km/h) for a 2x rather than 3x release.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
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

import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V162_WRITE", "").strip().lower()

BASE_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
BASE_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd = V106B.u16, V106B.s16, V106B.rd
rec_y = V106B.rec_y
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES

# ---- THE EDIT -------------------------------------------------------------------------------
ALPHA2_CAL, ALPHA2_HELD = 0xC40DC, 8
PID_HDR = 0xC67BE                              # (0, N) knot-count header, N = 3
PID_X   = 0xC67C2                              # resonance-PID ceiling LERP, X knots
PID_Y   = 0xC67C8                              #   ... Y knots
PID_X1  = 0xC67C4                              # X[1] -- THE EDIT
X1_OLD, X1_NEW = 1280, 512                     # 20.0 km/h -> 8.0 km/h on voted speed
LB_CAL, LB_HELD = 0xC6446, 5244                # Lever B -- HELD here (that is V160/V161)
LB_POST, LB_STOCK = 0xC6442, 512               # count>0 multiplier; stock Lever B
CNT_HI, CNT_LO, DTC_LIM = 0xC61FA, 0xC61F8, 0xC6500
ALPHA2_STOCK = 22
ALPHA2_STEPS = ((22, 14, "V91  -> V111"), (14, 8, "V112 -> V122"))   # flown, fault-free

# ---- THE FIVE CELLS V133 MOVED THAT THIS BUILD DELIBERATELY LEAVES AT V122 -------------------
REVERTED = {
    0xC407E: (2, 511, "b26 clamp = APPARENT MASS ceiling.  V133 doubled it to 1023 and the car"
                      " got VIOLENTLY worse, persisting after disengage because it is NOT"
                      " mode-gated."),
    0x3AB76: (1, 0xAA, "Lever A r26 arm -- left STOCK.  Its partner caused grind #2."),
    0x3AC20: (1, 0xAA, "Lever A r24 arm -- left STOCK.  RECORDED as having CAUSED grind #2,"
                       " which the operator reported on V133 while DISENGAGED."),
    0xC6CD0: (2, 5346, "LKAS gain HELD at 6x.  V133's 8x adds 33 % excitation into a zeta"
                       " 0.017-0.036 resonance, against an explicit operator instruction."),
    0xC640A: (2, -8192, "oscillation branch Y left at Honda's value -- V133's -1966 flew inside"
                        " a six-variable build and is NOT independently cleared."),
}
CEIL_F, CEIL_F_VAL = 0xC4004, 0.5           # the clamp's float twin, matched to 511
KNEE_CAL, KNEE_VAL = 0xC40BC, 3000                  # the relay knee -- HELD (V151 owns it)
K1_CAL, K1_VAL = 0xC40D2, 1020
OFF_CAL, OFF_VAL = 0xC4080, 0
POLE_CAL, POLE_VAL = 0xC40D0, 408
RESID_CAL, RESID_VAL = 0xC7468, 41232
ARM_CAL, ARM_VAL = 0xC620A, 12800
BQ_ADDR, BQ_LEN = 0xC60A8, 16
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END

FS, ALPHA0 = 1000.0, 37 / 128.0
SIG_BAND = (18.0, 22.0)
OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ASSERTION FAILED: {msg}")


def band_mag(a2, n=41):
    import math
    lo, hi = SIG_BAND
    tot = 0.0
    for i in range(n):
        f = lo + (hi - lo) * i / (n - 1)
        w = 2 * math.pi * f / FS
        z = complex(math.cos(w), math.sin(w))
        a = a2 / 64.0
        tot += abs(64 * (ALPHA0 / (1 - (1 - ALPHA0) / z)) * (1 - 1 / z) * (a / (1 - (1 - a) / z)))
    return tot / n


def build():
    print("=" * 102)
    print("  V162 -- resonance-PID ceiling X[1] 1280 -> 512.  ONE halfword.  V122BASE")
    print("=" * 102)

    print("\n  [1] BASE = V122, THE LAST FLOWN KNOWN-GOOD BUILD")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V122 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE CARRIES V122's VALUES, INCLUDING EVERY CELL V133 MOVED")
    check(u16(base, ALPHA2_CAL) == ALPHA2_HELD,
          f"  0x{ALPHA2_CAL:05X} alpha2 = {ALPHA2_HELD} -- HELD; Lever-B-only build")
    check(u16(base, KNEE_CAL) == KNEE_VAL and u16(base, K1_CAL) == K1_VAL,
          f"  relay knee {KNEE_VAL} / K1 {K1_VAL} -- V122's tuned pair")
    check(u16(base, OFF_CAL) == OFF_VAL and u16(base, POLE_CAL) == POLE_VAL,
          "  relay offset 0 and friction EMA pole 408, both V122")
    check(u16(base, RESID_CAL) == RESID_VAL, f"  0x{RESID_CAL:05X} residual scale = {RESID_VAL}")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(base, a) if want < 0 else (base[a] if w == 1 else u16(base, a))
        check(got == want, f"  0x{a:05X} = {want} in the base -- {why.split('.')[0]}")
    _fb = struct.unpack_from("<f", base, CEIL_F)[0]
    check(abs(_fb - CEIL_F_VAL) < 1e-9 and abs(_fb * 1024 - (511 + 1)) < 1e-6,
          f"  0x{CEIL_F:05X} float twin = {CEIL_F_VAL} and float*1024 == int+1 ({_fb*1024:.0f})")

    print("\n  [3] THE EDIT -- ONE HALFWORD")
    _hdr = (u16(base, PID_HDR), u16(base, PID_HDR + 2))
    check(_hdr == (0, 3),
          f"  header at 0x{PID_HDR:05X} = {_hdr} -- the (0, N) KNOT-COUNT invariant, N = 3")
    _X = [u16(base, PID_X + 2*i) for i in range(3)]
    _Y = [u16(base, PID_Y + 2*i) for i in range(3)]
    check(_X == [128, 1280, 3200] and _X == sorted(_X),
          f"  X = {_X} counts = {[round(x/64.,1) for x in _X]} km/h on voted speed, STRICTLY ASCENDING")
    check(_Y == [0, 1024, 1024], f"  Y = {_Y}")
    check(u16(base, PID_X1) == X1_OLD, f"  0x{PID_X1:05X} X[1] = {X1_OLD} in the base")
    struct.pack_into("<H", code, PID_X1, X1_NEW)
    attributed |= {PID_X1, PID_X1 + 1}
    print(f"      0x{PID_X1:05X}  resonance-PID ceiling X[1]  {X1_OLD} -> {X1_NEW}")
    check(u16(code, PID_X1) == X1_NEW, f"  reads back {X1_NEW}")

    print("\n  [4] THE RESONANCE PID GETS ITS AUTHORITY BACK IN THE RATCHET'S OWN BAND")
    def _ceil(img, v):
        X = [u16(img, PID_X + 2*i) for i in range(3)]
        Y = [u16(img, PID_Y + 2*i) for i in range(3)]
        if v <= X[0]:
            return Y[0]
        if v >= X[-1]:
            return Y[-1]
        j = 0
        while X[j+1] <= v:
            j += 1
        return (Y[j+1] - Y[j]) * (v - X[j]) // (X[j+1] - X[j]) + Y[j]
    rows = []
    for kmh in (2, 3, 5, 8, 12, 20, 40):
        v = int(kmh * 64)
        rows.append((kmh, _ceil(base, v), _ceil(code, v)))
    print("        km/h    stock ceiling    new ceiling     ratio")
    for kmh, o, n in rows:
        print(f"        {kmh:4d}    {o:8d}         {n:8d}      {'x%.2f' % (n/o) if o else '--'}")
    check(all(n >= o for _, o, n in rows),
          "  \U0001f6d1 THE MONOTONE-IN-DOSE GATE: the ceiling is >= stock at EVERY speed -- this"
          " RELEASES authority, it never removes any.")
    check(rows[0][2] == 0,
          f"  \U0001f6d1 THE PARKING GATE: at 2 km/h the ceiling stays EXACTLY 0.  X[0] = {_X[0]} is"
          f" UNTOUCHED, so Honda's standstill/parking protection is byte-for-byte intact.")
    check(rows[-1][1] == rows[-1][2] and rows[-2][1] == rows[-2][2],
          f"  \U0001f6d1 THE CONVERGENCE GATE: at 20 km/h and above the ceiling is UNCHANGED at"
          f" {rows[-1][2]}.  The edit is confined to the creep band; highway behaviour is identical.")
    _Xn = [u16(code, PID_X + 2*i) for i in range(3)]
    check(_Xn == sorted(_Xn) and len(set(_Xn)) == 3,
          f"  \U0001f6d1 THE SHAPE GATE: X = {_Xn} is still STRICTLY ASCENDING with no collapsed knot"
          f" -- a LERP with a zero-width segment divides by zero.")
    check(_Y == [u16(code, PID_Y + 2*i) for i in range(3)],
          f"  Y = {_Y} is UNTOUCHED -- the ceiling's VALUE is Honda's; only the SPEED at which it is"
          f" reached moves.  Honda already runs this lane at FULL 1024 above 20 km/h and the car does"
          f" not ratchet there, so this moves creep TOWARD a configuration that is known-good.")
    check(u16(code, LB_CAL) == LB_HELD,
          f"  0x{LB_CAL:05X} Lever B HELD at {LB_HELD} -- raising it is V160/V161, separate builds")

    print("\n  [5] \U0001f6d1 EVERY CELL IMPLICATED IN V133's REGRESSION IS AT ITS V122 VALUE")
    for a, (w, want, why) in sorted(REVERTED.items()):
        got = s16(code, a) if want < 0 else (code[a] if w == 1 else u16(code, a))
        check(got == want and rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} = {want}  -- {why}")
    check(struct.unpack_from("<f", code, CEIL_F)[0] == CEIL_F_VAL,
          f"  0x{CEIL_F:05X} float twin stays {CEIL_F_VAL}, matched to the 511 int")
    check(u16(code, 0xC6CD0) == 5346,
          "  \U0001f6d1 THE GAIN GATE: LKAS gain stays 6x.  The operator's instruction was"
          " conditional -- 8x only if we do NOT get more oscillation and grinding.  We did.")

    print("\n  [6] NOTHING ELSE MOVED")
    for a, w, nm in ((ALPHA2_CAL, 2, "alpha2 -- HELD, Lever-B-only build"),
                     (0xC61F6, 2, "pump deadband -- HELD at Honda 3"),
                     (K1_CAL, 2, "K1 -- HELD, knee-only step"), (OFF_CAL, 2, "relay offset"),
                     (POLE_CAL, 2, "friction EMA pole"), (RESID_CAL, 2, "residual scale"),
                     (ARM_CAL, 2, "detector arm threshold"), (0xC40DA, 2, "the >>7 EMA twin")):
        check(rd(code, a, w) == rd(base, a, w), f"  0x{a:05X} {nm} byte-identical to V122")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- cal-only, OUTSIDE the"
          f" bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {PID_X1, PID_X1 + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V122 base (the PID ceiling X[1] exempted)")

    print("\n  [7] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old:08X} -> 0x{new:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [8] FULL BYTE DIFF vs V122 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    _tr = [b[1] for b in blocks]
    for lo, hi in runs:
        tag = "CRC" if any(lo < t + 4 and t < hi for t in _tr) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo < t + 4 and t < hi for t in _tr))
    check(1 <= payload <= 2, f"{payload} payload byte(s) -- the PID ceiling X[1] u16 (1280=0x0500 -> 512=0x0200 moves only the HIGH byte)")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V151 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V162-V122BASE-RESPID.CEILING.X1.1280.TO.512"
    img_out = plain_image_path(f"_v162_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V162_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
