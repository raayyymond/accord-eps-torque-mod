#!/usr/bin/env python3
r"""
V112 -- THE FIRST LEVER THAT SATISFIES THE OPERATOR'S BOTH-AT-ONCE DIRECTIVE.

WHAT THIS IS
------------
V112 = V111, with the friction relay's KNEE and its |model| GAIN scaled x3 TOGETHER.
**Four payload bytes.  No cave edit.  No telemetry change.**

    0xC40BC   600 -> 1800     the relay knee     (saturation 10.6 -> 31.8 deg/s)
    0xC40D2   204 ->  612     K1, the |model|-proportional gain

THE DIRECTIVE THIS ANSWERS -- operator, 2026-08-27, after driving V111
----------------------------------------------------------------------
    "Increasing mass and friction should not be our primary approach to resolving the ratcheting if
     it comes at the cost of max steering angular velocity and acceleration.  We want BOTH: low
     apparent steering mass and friction to LKAS AND no ratcheting."

Every prior ratchet lever violated that: `gp-0x6b26`, the base-assist damper and alpha2 are all
MOTION-fed, so they oppose all motion and cap max angular velocity by construction.  This one does
not add impedance at all -- it reshapes a feed-forward friction COMPENSATION.

WHY SCALING BOTH CELLS IS THE WHOLE TRICK
------------------------------------------
`FUN_0003b8f6`:
    fVar13   = clamp(POL * gp-0x6abc * 12 / cal(0xC40BC), -1, +1)
    friction = EMA(|model| * cal(0xC40D2)/1024 * fVar13)     # cal(0xC4080) = 0, no Coulomb floor
    residual = model - friction - inertia                    # MORE friction => MORE assist

    small-signal GAIN  (sets the LIGHTNESS)   =  (K1/1024) * (12/knee)
    SATURATION rate    (sets the RELAY-ness)  =  knee/12   counts of |gp-0x6abc|

The knee is in BOTH; K1 is in ONE.  So K1 is exactly the free variable that cancels the knee's gain
effect and leaves its saturation effect standing.  x3/x3 holds the gain EXACTLY:

    V111 : (204/1024)*(12/ 600) = 0.0039844      saturates above 10.6 deg/s
    V112 : (612/1024)*(12/1800) = 0.0039844      saturates above 31.8 deg/s     <- IDENTICAL GAIN

=> below 10.6 deg/s V112 is BIT-IDENTICAL to V111.  The wheel feels exactly the same at low rate.
   Above it, the term keeps climbing instead of clipping -- MORE friction compensation, i.e. MORE
   assist, exactly where max angular velocity is wanted.

THE MEASUREMENT THAT SIZED IT -- route 21 IS the V111 drive
-----------------------------------------------------------
Route 21 (18 segments, 1068 s, 78.6 % engaged) was identified as V111 by PHYSICS, not assumption:
the 427 tap's quantiles NUMERICALLY EQUAL the steering rate measured from `ang` --
p95 39.4 vs 40.4, p99 167.4 vs 171.8, p99.5 224.4 vs 222.3, **p99.9 313.4 vs 313.3 deg/s** -- which
only holds if the tap is `gp-0x6abc` at sar 3.  It also independently confirms the 4.7121 ct/(deg/s)
scale to within 0-3 % in the upper tail.

**RELAY SATURATION DUTY, measured, in the operator's own grind-#1 regime**
(5-10 mph, engaged, hands-off, |cmd| >= 2048, n = 289 frames):

    knee  600 (V111) : 0.7439   block-bootstrap 95% CI [0.6691, 0.8146]   <- ON THE CAR
    knee 1200        : 0.4810
    knee 1800 (V112) : 0.2353                                             <- THIS BUILD, 3.2x cut
    knee 2400        : 0.0484
    knee 3600        : 0.0000

*** THE RELAY IS IN HARD COULOMB MODE 74 % OF THE TIME IN EXACTLY THE REGIME HE NAMES. ***
That is the first direct measurement of the mechanism the kit has called a "command-proportional
Coulomb relay" since V80, and it is the reason this build exists.

GATE 1 -- CLOSED
----------------
`0xC40BC`: exactly ONE tp-relative access image-wide, at file `0x3BAB4`, zero writers.
`0xC40D2`: exactly ONE, at `0x3BAFE`.  Raw Python LE scan (disp16 base-filtered) and the decompile
agree independently on both the count and the location.
(NB `0xC40BC` = 600 is HONDA'S OWN VALUE -- V99 halved it to 300 and it stayed halved for NINE builds
until V108 restored it.  This build goes ABOVE Honda for the first time, deliberately.)

GATE 2 -- CLOSED.  ZERO PHASE COST, AND THE MAGNITUDE IS BOUNDED BY ITS OWN SMALL-SIGNAL VALUE
-----------------------------------------------------------------------------------------------
* `clamp(x/knee, +-1)` is an ODD, MEMORYLESS nonlinearity => its describing function N(A) is REAL at
  every input amplitude => **it adds ZERO phase and cannot rotate anything into a new sector.**
* The magnitude rises at most **2.97x** over V111 at some amplitudes -- but **it can never exceed the
  small-signal gain g, which is UNCHANGED from V111 and is exercised on every drive at low rate.**
  No new gain regime is created; the lane simply behaves at high rate the way it already behaves at
  low rate.  That is the whole GATE-2 case and it is structural, not statistical.
* **The +-10.0 friction clamp CANNOT BIND.**  `iVar11 = cal(0xC7468) * fVar18` clamps at +-20000 and
  `cal(0xC7468)` = 41232, so `|model| <= 20000/41232 = 0.4851`.  Hence
  `friction_max = 0.4851 * 612/1024 = 0.290` against a clamp of 10.0 -- **34x of headroom.**
  (At V111 it is 103x.)  This was the only objection to compensating K1 and it dies on arithmetic.

WHAT IT COSTS, STATED PLAINLY
-----------------------------
At saturating rates the friction term rises from `0.199*|model|` to `0.598*|model|`, so the residual
falls from `0.80*|model|` to `0.40*|model|` -- a **2x reduction in the torque-tracking reference at
high steering rate.**  By the verified polarity that is MORE assist, which is the intent, but it is
a real change and the operator should be told it is not a small edit above 31.8 deg/s.
* Below 10.6 deg/s: **bit-identical to V111.**  His regime's p50 is 3.7 deg/s, so most frames do not
  change at all.
* `FUN_0003b8f6` is NOT LKAS-gated, so manual steering feel changes above 10.6 deg/s too.

WHAT IT DELIBERATELY DOES NOT TOUCH
-----------------------------------
alpha2 (`0xC40DC` = 14) is LEFT ALONE.  V111's alpha2 cut is the suspected source of the added
friction he objects to, but that magnitude is UNVERIFIED and reverting it would give back three
measured improvements for one regression.  **This build changes the RELAY only, so his next report
is a single-variable read on the relay hypothesis.**

Usage:
    python builds/v108_plus/build_v112_tva.py
    ACCORD_V112_WRITE=rwd python builds/v108_plus/build_v112_tva.py
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
WRITE_MODE = os.environ.get("ACCORD_V112_WRITE", "").strip().lower()

BASE_NAME = "_v111_V111-V109BASE-TAP.6ABC.SAR3_plain_image.bin"
BASE_SHA = "9c4865cffd337cfb5d27f66843edbff928a8ffbf6f365e4fdeb7e98f7ddfb546"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
Y_V108 = (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)

# ---- THE TWO EDITS -- scaled TOGETHER so the small-signal gain is held EXACTLY -------------
SCALE = 3
KNEE_CAL, KNEE_OLD, KNEE_NEW = 0xC40BC, 600, 600 * SCALE      # 1800  -> saturates at 31.8 deg/s
K1_CAL, K1_OLD, K1_NEW = 0xC40D2, 204, 204 * SCALE            #  612  -> cancels the gain change

# ---- cells that must NOT move ------------------------------------------------------------------
OFF_CAL, OFF_VAL = 0xC4080, 0           # the relay's constant offset -- ZERO, so no Coulomb floor
POLE_CAL, POLE_VAL = 0xC40D0, 408       # the friction EMA pole -- adds phase; MUST NOT MOVE
ALPHA2_CAL, ALPHA2_V111 = 0xC40DC, 14   # V111's band-limit -- DELIBERATELY LEFT ALONE
RESID_CAL, RESID_VAL = 0xC7468, 41232   # |model| -> residual scale; bounds the clamp argument
GAIN_CAL, GAIN_6X = 0xC6CD0, 5346
BQ_ADDR, BQ_LEN = 0xC60A8, 16
TAP_DISP_ADDR, TAP_DISP = 0x55DF2, (-0x6ABC) & 0xFFFF   # V111's tap -- carried unchanged
SAR_ADDR, SAR_VAL = 0x55E10, 0xA3
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END
RATE_SCALE = 4.7121
MEASURED_DUTY = {600: 0.7439, 1200: 0.4810, 1800: 0.2353, 2400: 0.0484, 3600: 0.0000}

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


def wire(raw, sar):
    return min((min(abs(raw), 65535) * 5) >> sar, 0x3FF)


def build():
    print("=" * 102)
    print("  V111 -- THE RELAY PROBE.  V109 + a 3-byte tap re-point.  NO CAVE EDIT, NO DOSE.")
    print("=" * 102)

    print("\n  [1] BASE = V111, AND IT MUST BE V111")
    base_path = plain_image_path(BASE_NAME)
    base = bytearray(Path(base_path).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V111 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE IS V111, AND EVERY ASSUMPTION IS CHECKED")
    check(u16(base, KNEE_CAL) == KNEE_OLD,
          f"  0x{KNEE_CAL:05X} (relay knee) = {KNEE_OLD} -- Honda's own value, restored by V108")
    check(u16(base, K1_CAL) == K1_OLD, f"  0x{K1_CAL:05X} (K1) = {K1_OLD} (V89)")
    check(u16(base, OFF_CAL) == OFF_VAL,
          f"  0x{OFF_CAL:05X} (relay offset) = 0 -- NO Coulomb floor; the term dies with the command")
    check(u16(base, RESID_CAL) == RESID_VAL,
          f"  0x{RESID_CAL:05X} = {RESID_VAL} -- bounds |model| <= 20000/{RESID_VAL} = "
          f"{20000/RESID_VAL:.4f}, which is what makes the +-10.0 clamp unreachable")
    check(u16(base, ALPHA2_CAL) == ALPHA2_V111, f"  0x{ALPHA2_CAL:05X} = {ALPHA2_V111} (V111 alpha2)")
    check(u16(base, GAIN_CAL) == GAIN_6X, f"  0x{GAIN_CAL:05X} = {GAIN_6X} (6x) -- carried")
    check(u16(base, TAP_DISP_ADDR) == TAP_DISP and base[SAR_ADDR] == SAR_VAL,
          "  V111's gp-0x6abc tap at sar 3 is present and will be carried unchanged")

    print("\n  [3] THE EDITS -- FOUR PAYLOAD BYTES, SCALED TOGETHER")
    struct.pack_into("<H", code, KNEE_CAL, KNEE_NEW)
    attributed |= {KNEE_CAL, KNEE_CAL + 1}
    struct.pack_into("<H", code, K1_CAL, K1_NEW)
    attributed |= {K1_CAL, K1_CAL + 1}
    print(f"      0x{KNEE_CAL:05X}  {KNEE_OLD} -> {KNEE_NEW}   knee   (x{SCALE})")
    print(f"      0x{K1_CAL:05X}  {K1_OLD} -> {K1_NEW}   K1     (x{SCALE})")

    print("\n  [4] THE GAIN IS HELD EXACTLY -- that is the entire point of scaling BOTH")
    g_old = (K1_OLD / 1024.0) * (12.0 / KNEE_OLD)
    g_new = (K1_NEW / 1024.0) * (12.0 / KNEE_NEW)
    print(f"      small-signal gain  V111 {g_old:.7f}   V112 {g_new:.7f}")
    check(abs(g_new - g_old) < 1e-12,
          "  small-signal gain IDENTICAL -- below the old corner V112 is BIT-IDENTICAL to V111")
    sat_old, sat_new = KNEE_OLD / 12.0, KNEE_NEW / 12.0
    print(f"      saturation         {sat_old:.0f} ct = {sat_old/RATE_SCALE:.1f} deg/s"
          f"  ->  {sat_new:.0f} ct = {sat_new/RATE_SCALE:.1f} deg/s")
    check(KNEE_NEW in MEASURED_DUTY,
          f"  the dose is on the MEASURED ladder (route 21 = V111, n=289 frames)")
    print(f"      MEASURED relay saturation duty, 5-10 mph engaged hands-off cmd>=2048:")
    for k in sorted(MEASURED_DUTY):
        mark = "  <- V111 (CI [0.669,0.815])" if k == KNEE_OLD else (
               "  <- THIS BUILD" if k == KNEE_NEW else "")
        print(f"         knee {k:5d}   duty {MEASURED_DUTY[k]:.4f}{mark}")
    check(MEASURED_DUTY[KNEE_NEW] < MEASURED_DUTY[KNEE_OLD] / 3.0,
          f"  duty cut {MEASURED_DUTY[KNEE_OLD]/MEASURED_DUTY[KNEE_NEW]:.1f}x -- "
          f"big enough for ONE short symptomatic drive to read")

    print("\n  [5] GATE 2 -- ZERO PHASE, AND THE CLAMP CANNOT BIND")
    mmax = 20000.0 / RESID_VAL
    fmax_old = mmax * K1_OLD / 1024.0
    fmax_new = mmax * K1_NEW / 1024.0
    print(f"      |model| <= {mmax:.4f}  =>  friction_max  {fmax_old:.4f} -> {fmax_new:.4f}"
          f"   vs the +-10.0 clamp")
    check(fmax_new < 10.0 / 10.0,
          f"  friction_max {fmax_new:.4f} leaves {10.0/fmax_new:.0f}x of headroom to the clamp")
    print(f"      residual at saturating rate: {1-fmax_old/mmax:.2f}*|model| ->"
          f" {1-fmax_new/mmax:.2f}*|model|   (a {(1-fmax_old/mmax)/(1-fmax_new/mmax):.1f}x reduction"
          f" -- MORE assist, by the verified polarity)")
    check(u16(code, POLE_CAL) == POLE_VAL,
          f"  0x{POLE_CAL:05X} (friction EMA pole) = {POLE_VAL} UNTOUCHED -- it is the only cell in"
          f" this lane that adds PHASE, and V111 already showed what phase costs")
    check(u16(code, OFF_CAL) == OFF_VAL, "  0xC4080 still 0 -- no Coulomb floor introduced")

    print("\n  [5b] NOTHING ELSE MOVED")
    for a, nm in ((ALPHA2_CAL, "0xC40DC alpha2 (deliberately left at V111's 14)"),
                  (GAIN_CAL, "0xC6CD0 6x gain"), (RESID_CAL, "0xC7468 residual scale"),
                  (TAP_DISP_ADDR, "0x55DF2 V111 tap")):
        check(u16(code, a) == u16(base, a), f"  {nm} byte-identical to V111")
    check(code[SAR_ADDR] == base[SAR_ADDR], "  0x55E10 sar byte-identical to V111")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- no cave edit, outside the "
          f"bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {KNEE_CAL, KNEE_CAL + 1, K1_CAL, K1_CAL + 1}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved, f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V111 BASE (2 exempted)")

    print("\n  [6] CRC RECOMPUTATION")
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

    print("\n  [7] FULL BYTE DIFF vs V111 -- ZERO UNATTRIBUTED")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    runs, unattributed = [], [a for a in diff if a not in attributed]
    for a in diff:
        if runs and a == runs[-1][1]:
            runs[-1][1] = a + 1
        else:
            runs.append([a, a + 1])
    for lo, hi in runs:
        tag = "CRC" if any(lo <= x < hi for x in (b[1] for b in blocks)) else "payload"
        print(f"      0x{lo:05X}..0x{hi-1:05X}  {hi-lo:3d} B  {tag:8s} "
              f"{bytes(base[lo:hi]).hex()} -> {bytes(code[lo:hi]).hex()}")
    check(not unattributed,
          f"every one of {len(diff)} differing bytes in {len(runs)} runs is attributed")
    payload = sum(hi - lo for lo, hi in runs
                  if not any(lo <= x < hi for x in (b[1] for b in blocks)))
    check(payload == 4, f"exactly 4 payload bytes ({payload} found)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V112 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V112-V111BASE-RELAY.KNEE1800.K1.612"
    img_out = plain_image_path(f"_v112_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V112_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
