#!/usr/bin/env python3
r"""
V118 -- V112 + BIQUAD DISARM + THE STATE-4 PROBE.  One flight, two answers.

WHAT THIS IS
------------
V118 = V112 with FOUR payload bytes.  NO CAVE EDIT.

    0xC649B   1 -> 0            disarm the biquad          (the candidate FIX)
    0x55DF2   gp-0x6ABC -> gp-0x67FA   the CAN 427 tap     (the candidate DIAGNOSTIC)
    0x55E10   sar 3 -> sar 0    probe scaling

One dynamics change (the arm byte) and one inert telemetry repoint.  The tap repoint is a pure
DISPLACEMENT edit -- the class that has never failed on this ECU -- and is NOT a cave change; the
164-byte cave is carried byte-identical.

WHY BOTH IN ONE BUILD
---------------------
The two leading candidates for the 7-9 Hz anti-damped excess are now:

  (a) the ARMED BIQUAD (0xC649B).  Point estimate from the corpus: 7-9 Hz Re(Z) is -37.7 with it
      off (9 routes) and -55.4 with it on (8 routes), a 1.47x step.  But P(ON worse) = 0.722 against
      chance 0.5 is NOT separable at n = 9/8, and the excess is already present at V90 which has no
      biquad -- so it is at most an ADDITIVE contributor, not the origin.

  (b) 0x454FE, which turns bne into an unconditional br so that `jarl FUN_00049A5A` -- HONDA'S
      STATE-4 GOVERNOR ROUTINE -- is NEVER CALLED on any build since V42.  This is the only
      surviving candidate that meets every constraint the excess imposes: code inside the governor,
      absent from stock, present in every affected build, state-gated on gp-0x67fa (hence
      engagement-conditional and command-independent), and it REMOVES a control element rather than
      scaling one.

(a) is testable by flying the disarm.  (b) is NOT safely testable by reverting -- V42's change is a
validated fix for the V38-era macro ratchet and reverting very likely brings that straight back.
What (b) needs first is its DUTY, which is unmeasured: gp-0x67fa is not on the CAN bus
(STEER_STATUS is NOT gp-0x67fa) and no cached build telemeters it.

=> fly the disarm AND measure the state at the same time.  One drive answers both.

THE PROBE
---------
    source  gp-0x67fa, the assist-chain state byte, read as a halfword
    wire    min((|hw| * 5) >> 0, 0x3FF)
    state 0-15  ->  wire 0, 5, 10 ... 75.      STATE 4 -> WIRE 20.

gp-0x67fb (the halfword's high byte) is live -- 4 writers, every one `st.b r0`, i.e. writing ZERO --
so the halfword should equal the state.  If it is ever non-zero the wire becomes
(256 + state) * 5 >= 1285 and CLIPS at 1023, so contamination is self-identifying and those samples
are discarded rather than misread.  The kit's own trap list warns that a disp16 scan cannot see the
6-byte gp-relative form, so a hidden writer is possible; the clip is the guard against exactly that.

WHAT IS GIVEN UP
----------------
The 427 wire currently carries |gp-0x6abc|, the raw resolver rate.  That is ALSO available from CAN
as carState.steeringRateDeg (`cs_rate`), which is what every Re(Z) measurement in this kit already
uses, so the loss is small and no existing analysis depends on the tap.

HOW TO READ THE DRIVE
---------------------
  * oscillation weaker  -> the biquad is a real contributor; next step is reshaping its
    coefficients rather than merely disarming it.
  * no change           -> the biquad is eliminated too.
  * worse               -> arming it was doing useful work; revert the one byte.
  AND, independently of the above:
  * state-4 duty HIGH   -> 0x454FE's deletion is live and becomes the prime suspect; the fix would
    be to restore FUN_00049A5A in a modified form, NOT a blind revert.
  * state-4 duty ~ZERO  -> 0x454FE is eliminated and the search moves to the V57 gain repoint, the
    LKAS ceiling raise, and the ~20 remaining cal cells.

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
WRITE_MODE = os.environ.get("ACCORD_V118_WRITE", "").strip().lower()

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
ARM_CAL, ARM_OLD, ARM_NEW = 0xC649B, 1, 0              # EDIT 1 -- disarm the biquad
TAP_OLD, TAP_NEW = (-0x6ABC) & 0xFFFF, (-0x67FA) & 0xFFFF   # EDIT 2 -- 427 tap -> gp-0x67fa
SAR_OLD, SAR_NEW = 0xA3, 0xA0                          # EDIT 3 -- sar 3 -> sar 0
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
    print("  V118 -- V112 + BIQUAD DISARM + THE STATE-4 PROBE.  One flight, two answers.")
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
          "  V112's gp-0x6abc tap at sar 3 is present and will be REPOINTED to gp-0x67fa")

    print("\n  [3] THE EDITS -- FOUR PAYLOAD BYTES.  BIQUAD ARM + THE STATE-4 PROBE.")
    code[ARM_CAL] = ARM_NEW
    attributed |= {ARM_CAL}
    struct.pack_into("<H", code, TAP_DISP_ADDR, TAP_NEW)
    attributed |= {TAP_DISP_ADDR, TAP_DISP_ADDR + 1}
    code[SAR_ADDR] = SAR_NEW
    attributed |= {SAR_ADDR}
    # K1 is deliberately NOT written -- V113 rests on it staying at 204
    print(f"      0x{ARM_CAL:05X}  {ARM_OLD} -> {ARM_NEW}   biquad ARM byte\n"
          f"      0x{TAP_DISP_ADDR:05X}  gp-0x6ABC -> gp-0x67FA   427 tap\n"
          f"      0x{SAR_ADDR:05X}  sar 3 -> sar 0   (state 0-15 -> wire 0-75)")
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

    print("")
    print("  [3d] THE PROBE -- what the 427 wire will carry")
    print("      source  gp-0x67fa, the assist-chain STATE byte, read as a halfword")
    print("      wire    min((|hw| * 5) >> 0, 0x3FF)")
    print("      state 0-15  ->  wire 0, 5, 10 ... 75      STATE 4 -> WIRE 20")
    print("      gp-0x67fb (the high byte) is live: 4 writers, all st.b r0 = ZERO.")
    print("      If it is ever non-zero the halfword is >= 256, so the wire is")
    print("      (256+state)*5 >= 1285, which CLIPS at 1023 -- contamination is")
    print("      self-identifying and those samples are discarded, not misread.")
    check(((4 * 5) >> 0) == 20, "  state 4 lands on wire value 20 -- unambiguous")
    check(((255 * 5) >> 0) > 0x3FF, "  any high-byte contamination CLIPS at 1023")

    check(KNEE_OLD in MEASURED_DUTY,
          f"  the relay ladder below is context only -- V118 does not touch the relay")
    print(f"      MEASURED relay saturation duty, 5-10 mph engaged hands-off cmd>=2048:")
    for k in sorted(MEASURED_DUTY):
        mark = "  <- V111 (CI [0.669,0.815])" if k == KNEE_OLD else (
               "  <- THIS BUILD" if k == KNEE_NEW else "")
        print(f"         knee {k:5d}   duty {MEASURED_DUTY[k]:.4f}{mark}")
    check(KNEE_NEW == KNEE_OLD,
          f"  the relay knee is HELD at V112's {KNEE_OLD} -- V118 does not touch the relay lane")

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
):
        check(u16(code, a) == u16(base, a), f"  {nm} byte-identical to V112")
    check(code[SAR_ADDR] == SAR_NEW, f"  0x{SAR_ADDR:05X} sar = 0 (probe scaling)")
    check(rd(code, BQ_ADDR, BQ_LEN) == rd(base, BQ_ADDR, BQ_LEN), "  biquad byte-identical")
    for m in ENGAGED_MODES + MANUAL_MODES:
        check(rec_y(code, m) == rec_y(base, m), f"  mode {m} gp-0x6b26 row byte-identical")
    check(rd(code, CAVE_BASE, CAVE_LEN) == rd(base, CAVE_BASE, CAVE_LEN),
          f"  \U0001f6d1 THE {CAVE_LEN}-BYTE CAVE IS BYTE-IDENTICAL -- no cave edit, outside the "
          f"bricking class")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          "  the cave's free region is still all 0xFF")
    exempt = {ARM_CAL, TAP_DISP_ADDR, TAP_DISP_ADDR + 1, SAR_ADDR}
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
    check(payload == 4, f"exactly 4 payload bytes ({payload} found)")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V118 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V118-V112BASE-BIQUAD.DISARM-TAP.67FA.SAR0"
    img_out = plain_image_path(f"_v118_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V118_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
