#!/usr/bin/env python3
r"""
V117 -- V112 + DISARM THE BIQUAD.  0xC649B 1 -> 0.  ONE BYTE, FULLY REVERSIBLE.

WHAT THIS IS
------------
V117 = V112 with a single byte cleared.  alpha2, the relay knee, K1, the gain, the cave and every
biquad COEFFICIENT are all held at V112's values, so this is single-variable against the build on
the car and is undone by writing the byte back.

WHAT THE BIQUAD IS -- read from the assembly at 0x35A28-0x35A50, not guessed
---------------------------------------------------------------------------
    y[n] = 0.81731*x[n] + 1.53720*y[n-1] - 0.63462*y[n-2]        (all-pole, 2nd order)
    cal 0xC60B4 = 0.81731 (b0) · 0xC60A8 = -1.53720 (a1) · 0xC60AC = 0.63462 (a2)
    pole radius 0.79663, pole angle 0.26565 rad, DC GAIN 8.39

    at 1 kHz  -> pole at 42.3 Hz  => a FLAT ~8.4x gain across 7-12 Hz
    at 100 Hz -> pole at 4.23 Hz  => a Q-2.46 RESONATOR sitting on the problem band

The task's rate could not be pinned (FUN_000352b4 is entered from an RTOS TCB at 0xBB928, not a
periodic rate table), but the conclusion does not depend on it: **either way, arming this filter
puts a large gain into the aggregator path**, and stock leaves it OFF.

🛑 STOCK DOES NOT RUN THIS FILTER.  Arming needs THREE edits, all verified from the images:
    0xC649B  0 -> 1     the arm cal
    0x35A08  e798 -> fb97   repoints the gate input from gp-0x671a to gp-0x6806
    0x35A12  ec -> e0      cmp r12,r9 -> cmp r0,r9  (compare against 0 instead of cal 0xC64FA = 5)
V88 and everything before it carry 0xC649B = 0 and stock code there.  V103 onward carry all three.
**V117 clears only the CAL byte** -- the two code edits stay, so the change is one byte and the
revert is one byte.

WHY THIS IS THE BEST AVAILABLE SHOT
-----------------------------------
The 7-9 Hz anti-damped excess is definitely OURS: stock measures -13.1 and every one of 16 modified
routes measures -31.9 to -74.8.  Seven candidate mechanisms have been tested and eliminated, each
with its own control: the command rail (0.76x [0.22,1.49]), driver grip (0.79x [0.67,1.01]),
command magnitude (present at |cmd| < 512), Coulomb relay switching (0.14x [0.11,0.19], inverted by
a scale-free ratio), a linear gain law (within-gain spread 41.2 vs between-gain step 19.1), and
amplitude dependence (real, but Honda's, and the gap persists 2.2x at matched amplitude).

The biquad's own natural experiment is the strongest surviving signal:
    7-9 Hz Re(Z)   biquad OFF (9 routes) median -37.7
                   biquad ON  (8 routes) median -55.4     point estimate 1.47x
    P(ON more anti-damped than OFF) = 0.722, chance 0.5
🛑 **That is NOT statistically separable at n = 9/8 with overlapping ranges, and the excess is
already present at V90, which has no biquad.  So the biquad is NOT the origin.**  What it may be is
an ADDITIVE contributor, and 1.47x is far larger than anything else on the table -- V115's alpha2
lever supplies only ~1.05x of the deficit by comparison.

**This build IS the experiment.**  It converts an unseparable observational comparison into a
single-variable on-car test, at the cost of one byte.

WHAT TO EXPECT, STATED HONESTLY
-------------------------------
  * If the peak-turn oscillation weakens noticeably -> the biquad is a real contributor and the
    next step is to reshape its coefficients rather than merely disarm it.
  * If nothing changes -> the biquad is eliminated as a contributor too, and the search moves to
    the remaining common edits (the V57 gain repoint, V42's fix, the cave, the ceiling raise).
  * If something gets WORSE -> arming it was doing useful work; revert the one byte.

⚠ Arming the biquad was a deliberate V103 decision and V103-V107 fed the arc that produced V108's
improvements, so disarming may give something up.  It is one byte and fully reversible.
⊕ V88 -- a build the operator reported as "grinding FIXED" -- ran with this filter OFF, so
biquad-off is a state this car has already driven well in.

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
WRITE_MODE = os.environ.get("ACCORD_V117_WRITE", "").strip().lower()

BASE_NAME = "_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin"
BASE_SHA = "f032878c4e0b8e90d782ddac6ba2d644e09956cc1b267a60ef4fb1c44ee1f96f"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
Y_V108 = (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)

# ---- THE TWO EDITS -- scaled TOGETHER so the small-signal gain is held EXACTLY -------------
SCALE = 3
KNEE_CAL, KNEE_OLD, KNEE_NEW = 0xC40BC, 1800, 1800            # V112 value, HELD
K1_CAL, K1_OLD, K1_NEW = 0xC40D2, 612, 612                    # V112 value, HELD

# ---- cells that must NOT move ------------------------------------------------------------------
OFF_CAL, OFF_VAL = 0xC4080, 0           # the relay's constant offset -- ZERO, so no Coulomb floor
POLE_CAL, POLE_VAL = 0xC40D0, 408       # the friction EMA pole -- adds phase; MUST NOT MOVE
ALPHA2_CAL, ALPHA2_V111, ALPHA2_NEW = 0xC40DC, 14, 14  # HELD
ARM_CAL, ARM_OLD, ARM_NEW = 0xC649B, 1, 0              # THE EDIT -- disarm the biquad
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
    print("  V117 -- V112 + DISARM THE BIQUAD.  0xC649B 1 -> 0.  ONE BYTE, FULLY REVERSIBLE.")
    print("=" * 102)

    print("\n  [1] BASE = V112, AND IT MUST BE V112")
    base_path = plain_image_path(BASE_NAME)
    base = bytearray(Path(base_path).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V112 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE IS V112 -- THE BUILD ON THE CAR -- AND EVERY ASSUMPTION IS CHECKED")
    check(u16(base, KNEE_CAL) == KNEE_OLD,
          f"  0x{KNEE_CAL:05X} (relay knee) = {KNEE_OLD} -- V112's RAISED knee, HELD")
    check(u16(base, K1_CAL) == K1_OLD, f"  0x{K1_CAL:05X} (K1) = {K1_OLD} (V112)")
    check(u16(base, OFF_CAL) == OFF_VAL,
          f"  0x{OFF_CAL:05X} (relay offset) = 0 -- NO Coulomb floor; the term dies with the command")
    check(u16(base, RESID_CAL) == RESID_VAL,
          f"  0x{RESID_CAL:05X} = {RESID_VAL} -- bounds |model| <= 20000/{RESID_VAL} = "
          f"{20000/RESID_VAL:.4f}, which is what makes the +-10.0 clamp unreachable")
    check(u16(base, ALPHA2_CAL) == ALPHA2_V111, f"  0x{ALPHA2_CAL:05X} = {ALPHA2_V111} (V111 alpha2)")
    check(u16(base, GAIN_CAL) == GAIN_6X, f"  0x{GAIN_CAL:05X} = {GAIN_6X} (6x) -- carried")
    check(u16(base, TAP_DISP_ADDR) == TAP_DISP and base[SAR_ADDR] == SAR_VAL,
          "  V112's gp-0x6abc tap at sar 3 is present and will be carried unchanged")

    print("\n  [3] THE EDIT -- ONE PAYLOAD BYTE.  THE BIQUAD ARM ONLY.")
    code[ARM_CAL] = ARM_NEW
    attributed |= {ARM_CAL}
    # K1 is deliberately NOT written -- V113 rests on it staying at 204
    print(f"      0x{ARM_CAL:05X}  {ARM_OLD} -> {ARM_NEW}   biquad ARM byte")
    print(f"      0x{KNEE_CAL:05X}  {KNEE_OLD} -> {KNEE_OLD}   knee   (HELD)\n"
          f"      0x{K1_CAL:05X}  {K1_OLD} -> {K1_OLD}   K1     (HELD)")

    print("\n  [4] EVERYTHING ELSE IS UNTOUCHED -- knee, K1 and alpha2 all held")
    g_old = (K1_OLD / 1024.0) * (12.0 / KNEE_OLD)
    g_new = (K1_NEW / 1024.0) * (12.0 / KNEE_NEW)

    print("")
    print("  [3b] WHAT THE BIQUAD IS -- read from the assembly, not guessed")
    print("      y[n] = 0.81731*x + 1.53720*y[n-1] - 0.63462*y[n-2]   (all-pole, 2nd order)")
    print("      pole radius 0.79663, angle 0.26565 rad, DC GAIN 8.39")
    print("      -> at 1 kHz the pole is 42.3 Hz, so it is a FLAT 8.4x gain through 7-12 Hz")
    print("      -> at 100 Hz the pole is 4.23 Hz, a Q-2.46 resonator on the problem band")
    print("      Either way, arming it puts a LARGE gain into the aggregator path.")
    for a_, nm_ in ((0xC60A8, "a1 -1.53720"), (0xC60AC, "a2  0.63462"),
                    (0xC60B4, "b0  0.81731")):
        check(rd(code, a_, 4) == rd(base, a_, 4),
              f"  biquad coefficient 0x{a_:05X} ({nm_}) byte-identical -- shape UNTOUCHED")
    print("")
    print("  [3c] THE EVIDENCE FOR DISARMING -- a natural experiment already in the corpus")
    print("      7-9 Hz Re(Z), biquad OFF (9 routes) median -37.7")
    print("                    biquad ON  (8 routes) median -55.4")
    print("      point estimate: a 1.47x reduction.  P(ON worse) = 0.722, chance 0.5.")
    print("      NOT statistically separable at n=9/8 -- this build IS the experiment.")

    check(KNEE_OLD in MEASURED_DUTY,
          f"  the relay ladder below is context only -- V117 does not touch the relay")
    print(f"      MEASURED relay saturation duty, 5-10 mph engaged hands-off cmd>=2048:")
    for k in sorted(MEASURED_DUTY):
        mark = "  <- V111 (CI [0.669,0.815])" if k == KNEE_OLD else (
               "  <- THIS BUILD" if k == KNEE_NEW else "")
        print(f"         knee {k:5d}   duty {MEASURED_DUTY[k]:.4f}{mark}")
    check(KNEE_NEW == KNEE_OLD,
          f"  the relay knee is HELD at V112's {KNEE_OLD} -- V117 does not touch the relay lane")

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
    for a, nm in ((ALPHA2_CAL, "0xC40DC alpha2 HELD at 14"),
                  (KNEE_CAL, "0xC40BC relay knee HELD at 1800 (V112)"),
                  (K1_CAL, "0xC40D2 K1 HELD AT 612 (V112)"),
                  (GAIN_CAL, "0xC6CD0 6x gain"), (RESID_CAL, "0xC7468 residual scale"),
                  (TAP_DISP_ADDR, "0x55DF2 V111 tap")):
        check(u16(code, a) == u16(base, a), f"  {nm} byte-identical to V112")
    check(code[SAR_ADDR] == base[SAR_ADDR], "  0x55E10 sar byte-identical to V112")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- no cave edit, outside the "
          f"bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {ARM_CAL}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved, f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V112 BASE (2 exempted)")

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

    print("\n  [7] FULL BYTE DIFF vs V112 -- ZERO UNATTRIBUTED")
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
    check(payload == 1, f"exactly 1 payload byte ({payload} found)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V117 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V117-V112BASE-BIQUAD.DISARM.C649B"
    img_out = plain_image_path(f"_v117_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V117_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
