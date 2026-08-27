#!/usr/bin/env python3
r"""
V111 -- THE RELAY PROBE.  V109 PLUS A THREE-BYTE TAP RE-POINT.  NO CAVE EDIT, NO DOSE.

WHAT THIS IS
------------
V111 = V109, with the CAN-427 magnitude tap re-aimed from `gp-0x6c2c` to `gp-0x6abc`, the
INPUT OF THE COULOMB RELAY, and its shift re-scaled to fit.  **Three payload bytes.**

    0x55DF2   d4 93 -> 44 95     tap source  gp-0x6c2c -> gp-0x6abc   (disp16 0x9544)
    0x55E10   a5    -> a3        sar 5 -> sar 3

🛑 **THIS IS A MEASUREMENT, NOT A FIX.  It changes NO dynamics cell.**  Every calibration that
affects how the car drives is byte-identical to V109.  The only thing that changes is which
number the firmware puts on a spare CAN field.

🛑 **FLY V109 FIRST.**  V109's tap still watches `gp-0x6c2c`, which V108 added specifically so the
next drive could solve the `gp-0x6b26` Y row -- a question open since V107.  Re-pointing the tap
COSTS that solve.  V111 is the build AFTER V109, not instead of it.

WHY `gp-0x6abc` -- THE RELAY IS LOCATED AND THIS IS ITS INPUT
-------------------------------------------------------------
`FUN_0003b8f6` @`0x3B8F6` (decompiled 2026-08-27) contains the command-proportional Coulomb relay
the kit has named since V80 without ever pointing at the instruction:

    iVar20   = POL * gp-0x6abc * 12                       # POL = *(char*)(gp-0x6752)
    fVar13   = clamp(iVar20 / cal(0xC40BC), -1.0, +1.0)   # <-- THE RELAY.  tp+0x50bc
    friction = EMA(|model| * cal(0xC40D2)/1024 * fVar13 + cal(0xC4080)/1024 * fVar13)
    gp-0x6ae2 = friction * 1024
    iVar20   = (model - friction - inertia) * gain        # subtracted from the model

Below the knee the term is LINEAR in rate (viscous).  Above it, a pure +-1 sign (Coulomb).
**Saturation point: `|gp-0x6abc| >= knee/12`.**

    knee 300 (STOCK)  ->  |gp-0x6abc| >= 25   =  5.3 deg/s
    knee 600 (V108)   ->  |gp-0x6abc| >= 50   = 10.6 deg/s      <- ON THE CAR
    knee 1200         ->  100                 = 21.2 deg/s
    knee 2400         ->  200                 = 42.4 deg/s

⭐ V108's relay corner is **10.6 deg/s -- the bottom edge of the 8-20 deg/s band in which the
ratchet was isolated** (see below).  Stock's was 5.3 deg/s, i.e. saturated essentially always.

THE MEASUREMENT THIS BUILD EXISTS TO MAKE
-----------------------------------------
`accord-ratchet-and-grind-are-command-gated-saturation`, with a 2-D control that separated command
from rate: at **matched** steering rate (rms 8-20 deg/s) the 6-9/1-3 band shape rises
**0.93 -> 1.13 -> 4.72 -> 44.71** across command bins -- a **48x fold at constant rate** -- while the
pure rate effect at matched command is only **2.8x**.  ⇒ the ratcheting is switched on by COMMAND,
and the relay is a product of a command-tracking magnitude and a rate-driven shape.

**What V111 buys:** the full distribution of `|gp-0x6abc|` on the wire, from which the relay's
saturation duty at ANY candidate knee is computed post-hoc -- not one threshold, the whole curve.

    (|gp-0x6abc| >= 50) and NOT (>= 200)  ==  EXACTLY the population a 600 -> 2400 knee raise
                                              would affect.

⭐ **If that duty is near zero in the symptomatic regime, the knee lever is dead and no assist was
ever spent.**  The null is interpretable, which is the whole point of spending a drive on it.

WHY A DOSE WOULD BE PREMATURE -- THE COST IS LARGE AND UNMEASURED
-----------------------------------------------------------------
`clamp(x/knee, +-1)` is monotonically DECREASING in the knee, and `accord-friction-polarity-more-
assist` is verified nine ways that **more modelled friction = MORE assist**.  So raising the knee
is a **direct assist reduction**, trading against the operator's 6x goal, in the same direction
that made V93/V94 undriveable (*"made the stuttering and grinding worse, by a lot"*).
Magnitude bound: friction is clamped to +-10.0 float ⇒ `gp-0x6ae2` spans **+-10,240 counts** against
a residual clamped at **+-20,000** ⇒ **the term can reach 51 % of the residual range.**
A 600 -> 2400 raise is a **4x cut at 10.6 deg/s**, tapering to nothing by 42.4 deg/s.
🛑 **A 4x cut in a term that large is not a small edit, and modelling it is not good enough.**

SIZING -- WHY sar 3
-------------------
The packer is `wire = clamp((min(|src|,65535) * 5) >> sar, 0, 0x3FF)` (`0x55E06` mul 0x5).
Peak `|gp-0x6abc|` on record, via its sibling `gp-0x6ac0` (SAME underlying quantity -- see the
GATE note below), is **1462 ct = 310 deg/s**.

    sar 2 : peak wire 1827 / 1023   SATURATES -- rejected
    sar 3 : peak wire  913 / 1023   ok, 89 % utilisation   1 ct = 1.60 raw = 0.340 deg/s   <- PICK
    sar 4 : peak wire  456 / 1023   ok but half the resolution
    sar 5 : peak wire  228 / 1023   V109's setting -- 4.5x under-ranged for this signal

At sar 3 the two knees of interest land at **31** and **125** wire counts: both far above the LSB,
both far below the ceiling.  **Sized against a distribution the kit HAS measured, not a guess** --
which is the rung-design law (`feedback-size-probe-rungs-against-lane-reachable-output`).

GATE NOTES
----------
✅ **The scale is DERIVED, not assumed.**  `FUN_00041464` writes `gp-0x6abc <- gp-0x4f50` (raw,
signed) and `gp-0x6ac0 <- |EMA(gp-0x4f50 * 1024)| >> 10`.  The `>>10` undoes the `x1024`, so the two
are the SAME quantity differing only in filtering and sign ⇒ `gp-0x6ac0`'s 4.7121 ct/(column deg/s)
scale transfers.  Cross-checked: peak 1462 ct = 310 deg/s against the 400-500 deg/s max steering
rates measured directly from `ang`.

✅ **NO CAVE EDIT.**  The 164-byte cave at `0xC4B34` is asserted byte-identical to V109, so every
carried rung (`b5` = `|gp-0x6ae2| >= |gp-0x6b26|` included) still means exactly what it meant on
routes `a5`/`a6`/`1e`.  **Code caves are this kit's only bricking class (V24, V27, V48B).  This
build does not touch one.**

✅ **The tap re-point is a PROVEN mechanism.**  V107 did exactly this edit at exactly these two
addresses (`0x55DF2` gp-0x6b86 -> gp-0x6c2c, `0x55E10` sar 4 -> sar 3) and flew fault-free as
routes `1b`/`1e`.  V108 then moved only the shift.  **This is the third use of the same lever.**

⚠ **WHAT IT COSTS:** the `gp-0x6c2c` channel goes dark.  That is the cell V108's E5 was added to
un-censor, and the `gp-0x6b26` Y-row solve depends on it.  **Hence: V109 first.**

Usage:
    python builds/v108_plus/build_v111_tva.py
    ACCORD_V111_WRITE=rwd python builds/v108_plus/build_v111_tva.py
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
WRITE_MODE = os.environ.get("ACCORD_V111_WRITE", "").strip().lower()

BASE_NAME = "_v109_V109-V108BASE-ALPHA2.C40DC.14_plain_image.bin"
BASE_SHA = "e9eb51fcad9ffc8768cd3e8eb601619d0f2acc0f702f01c4732243c70cc7f4d6"
STOCK_SHA = V106B.STOCK_SHA

u16, s16, rd, rdw = V106B.u16, V106B.s16, V106B.rd, V106B.rdw
rec_y, rec_x = V106B.rec_y, V106B.rec_x
MANUAL_MODES, ENGAGED_MODES = V106B.MANUAL_MODES, V106B.ENGAGED_MODES
Y_V108 = (-29490, -17202, -16000)
X_EXPECT = (0, 1280, 5760)

# ---- THE TWO EDITS ----------------------------------------------------------------------------
TAP_DISP_ADDR = 0x55DF2                 # the disp16 halfword of the tap's gp-relative load
TAP_OLD_DISP = (-0x6C2C) & 0xFFFF       # 0x93D4 -- V107/V108/V109 watch gp-0x6c2c
TAP_NEW_DISP = (-0x6ABC) & 0xFFFF       # 0x9544 -- the RELAY INPUT
SAR_ADDR = 0x55E10
SAR_OLD, SAR_NEW = 0xA5, 0xA3           # sar 5 -> sar 3
MUL_ADDR = 0x55E06                      # the `mul 0x5` the packer applies BEFORE the shift

# ---- cells that must NOT move ------------------------------------------------------------------
KNEE_CAL, KNEE_V108 = 0xC40BC, 600      # the relay knee -- THIS BUILD DOES NOT DOSE IT
K1_CAL, K1_VAL = 0xC40D2, 204           # the |model|-proportional friction gain (V89)
OFF_CAL = 0xC4080                       # the relay's constant offset term
ALPHA2_CAL, ALPHA2_V109 = 0xC40DC, 14   # V109's band-limit edit -- carried
GAIN_CAL, GAIN_6X = 0xC6CD0, 5346
BQ_ADDR, BQ_LEN = 0xC60A8, 16           # V108's Honda-restored notch
CAVE_BASE, CAVE_LEN = V106B.CAVE_BASE, V106B.CAVE_LEN
CAVE_FREE_END = V106B.CAVE_FREE_END
RATE_SCALE = 4.7121                     # ct per column deg/s, via gp-0x6ac0
PEAK_6AC0 = 1462                        # peak on record, the sibling cell

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

    print("\n  [1] BASE = V109, AND IT MUST BE V109")
    base_path = plain_image_path(BASE_NAME)
    base = bytearray(Path(base_path).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"  base image is V109 ({BASE_SHA[:16]}...)")
    stock = bytearray(Path(plain_image_path("stock_fw_dump/code.bin")).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA, "  stock reference sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "  base image CRC chain 50/50 before we touch it")
    code = bytearray(base)
    attributed = set()

    print("\n  [2] THE BASE IS THE ONE THE PROBE ASSUMES")
    check(u16(base, KNEE_CAL) == KNEE_V108,
          f"  0x{KNEE_CAL:05X} (relay knee) = {KNEE_V108} on the car -- the probe is sized to it")
    check(u16(base, ALPHA2_CAL) == ALPHA2_V109, f"  0x{ALPHA2_CAL:05X} = {ALPHA2_V109} (V109)")
    check(u16(base, GAIN_CAL) == GAIN_6X, f"  0x{GAIN_CAL:05X} = {GAIN_6X} (6x) -- carried")
    check(rd(base, BQ_ADDR, BQ_LEN) == rd(stock, BQ_ADDR, BQ_LEN),
          "  the biquad is Honda's (V108's revert) -- carried")
    check(u16(base, TAP_DISP_ADDR) == TAP_OLD_DISP,
          f"  0x{TAP_DISP_ADDR:05X} = 0x{TAP_OLD_DISP:04X} -- the tap watches gp-0x6c2c today")
    check(base[SAR_ADDR] == SAR_OLD, f"  0x{SAR_ADDR:05X} = 0x{SAR_OLD:02X} (sar {SAR_OLD & 0xF})")

    print("\n  [3] THE EDITS -- THREE PAYLOAD BYTES, BOTH ON THE TELEMETRY PATH ONLY")
    struct.pack_into("<H", code, TAP_DISP_ADDR, TAP_NEW_DISP)
    attributed |= {TAP_DISP_ADDR, TAP_DISP_ADDR + 1}
    code[SAR_ADDR] = SAR_NEW
    attributed.add(SAR_ADDR)
    print(f"      0x{TAP_DISP_ADDR:05X}  0x{TAP_OLD_DISP:04X} -> 0x{TAP_NEW_DISP:04X}   "
          f"tap source gp-0x6c2c -> gp-0x6abc  (THE RELAY INPUT)")
    print(f"      0x{SAR_ADDR:05X}  0x{SAR_OLD:02X} -> 0x{SAR_NEW:02X}         "
          f"sar {SAR_OLD & 0xF} -> sar {SAR_NEW & 0xF}")
    check(u16(code, TAP_DISP_ADDR) == TAP_NEW_DISP, "  tap disp16 reads back as gp-0x6abc")
    check(code[SAR_ADDR] == SAR_NEW, "  sar reads back as 3")

    print("\n  [4] SIZING -- AGAINST A DISTRIBUTION THE KIT HAS MEASURED, NOT A GUESS")
    print(f"      peak |gp-0x6abc| on record = {PEAK_6AC0} ct = "
          f"{PEAK_6AC0 / RATE_SCALE:.0f} deg/s (via the sibling gp-0x6ac0)")
    print(f"      {'sar':>5} {'peak wire':>10} {'1 ct =':>10} {'knee600':>9} {'knee2400':>9}")
    for s in (2, 3, 4, 5):
        pk = (PEAK_6AC0 * 5) >> s
        print(f"      {s:>5} {pk:>10} {(1 << s) / 5.0 / RATE_SCALE:>9.3f}/s "
              f"{wire(50, s):>9} {wire(200, s):>9}"
              f"{'   SATURATES' if pk > 0x3FF else ''}"
              f"{'   <- PICK' if s == (SAR_NEW & 0xF) else ''}")
    check((PEAK_6AC0 * 5) >> (SAR_NEW & 0xF) <= 0x3FF,
          f"  sar {SAR_NEW & 0xF}: the whole measured range fits the 10-bit field, no ceiling")
    check((PEAK_6AC0 * 5) >> ((SAR_NEW & 0xF) - 1) > 0x3FF,
          f"  sar {(SAR_NEW & 0xF) - 1} WOULD saturate -- sar {SAR_NEW & 0xF} is the tightest safe fit")
    k600, k2400 = wire(50, SAR_NEW & 0xF), wire(200, SAR_NEW & 0xF)
    check(k600 >= 8 and k2400 >= 8,
          f"  both knees resolve well above the LSB: knee600 -> {k600} ct, knee2400 -> {k2400} ct")
    check(k2400 <= 0x3FF, "  the knee-2400 threshold is inside the field")
    print(f"      => (wire >= {k600}) AND NOT (wire >= {k2400}) is EXACTLY the population a")
    print(f"         600 -> 2400 knee raise would affect.  Its duty sizes the dose.")

    print("\n  [5] NOTHING THAT AFFECTS HOW THE CAR DRIVES HAS MOVED")
    for a, name in ((KNEE_CAL, "0xC40BC relay knee"), (K1_CAL, "0xC40D2 K1"),
                    (OFF_CAL, "0xC4080 relay offset"), (ALPHA2_CAL, "0xC40DC alpha2"),
                    (GAIN_CAL, "0xC6CD0 6x gain")):
        check(u16(code, a) == u16(base, a), f"  {name} byte-identical to V109")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical to V109")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == rec_y(base, m) and rec_x(code, m) == rec_x(base, m),
              f"  mode {m} gp-0x6b26 row byte-identical to V109")
    for m in MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} (MANUAL) byte-identical to V109")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  🛑 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL TO V109 -- no cave edit, and every "
          f"carried rung still means what routes a5/a6/1e measured")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF -- nothing was appended")
    # 🛑 V106B.assert_frozen is NOT used here: its expected values are V106's, and V107 (tap),
    # V108 (knee, sar) and V109 (alpha2) have legitimately moved four of them since.  Asserting a
    # stale table would either fail on correct edits or, worse, be silenced.  The V109-RELATIVE
    # form is both correct and stronger: every cell the kit freezes must equal THE BASE, except
    # the two this build deliberately edits.
    exempt = {TAP_DISP_ADDR, TAP_DISP_ADDR + 1, SAR_ADDR}
    moved = [a for a, (w, _v, _d) in sorted(V106B.FROZEN.items())
             if a not in exempt and rd(code, a, w) != rd(base, a, w)]
    check(not moved,
          f"  all {len(V106B.FROZEN)} kit-frozen cells equal the V109 BASE "
          f"(2 exempted: the tap disp16 and the sar)")

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

    print("\n  [7] FULL BYTE DIFF vs V109 -- ZERO UNATTRIBUTED")
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
    check(payload == 3, f"exactly 3 payload bytes ({payload} found)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V111 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V111-V109BASE-TAP.6ABC.SAR3"
    img_out = plain_image_path(f"_v111_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V111_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
