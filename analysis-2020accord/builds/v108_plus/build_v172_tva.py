#!/usr/bin/env python3
r"""
V172 -- RETUNE THE ASSIST MAP'S SECOND-ORDER SECTION.  Base = V158.  4 float32 cells.
        An ALTERNATIVE to V168's slope cap, with a DIFFERENT feel cost -- not a replacement.

WHAT THIS IS
------------
`FUN_000352b4` carries a genuine second-order section in the DOMINANT torque-fed lane
(gp-0x6b86, 5.8-7.8x the entire PID), states gp-0x3814 / gp-0x3818, coefficients at
0xC60A8 / 0xC60AC / 0xC60B0 / 0xC60B4 (float32), enable 0xC649B, running at 1 kHz:

    w = -C_AC*s1 - C_A8*s2 + C_B4*x
    y = (1-C_AC)*s1 + (C_B0-C_A8)*s2 + C_B4*x        clamped to +/-12.0
    s1 <- s2 ;  s2 <- w

  This RETRACTS two recorded claims -- "this firmware has NO frequency-selective lever" and
  "no notch filter exists anywhere".  It has one, and it is already ENABLED on the flying
  build (stock ships 0xC649B = 0; the kit turned it on at V104).

  The FLYING tuning passes the ratchet almost untouched: gain 0.9790 at 8.64 Hz.

THE DESIGN, AND THE MISTAKE THAT NEARLY DISCARDED IT
-----------------------------------------------------
An optimiser targeting depth at 8.64 Hz reaches -96 dB with unity DC, but that solution has
COMPLEX poles at r ~ 0.988, i.e. a Q ~ 40 resonance at 3.3 Hz -- in the driver's own band --
with 333 ms settling and 65 oscillation cycles on a step.  Not flyable.

A frontier sweep then appeared to kill the whole lever, because it printed a "ring Q" for
every pole radius.  That figure is MEANINGLESS FOR REAL POLES, and the rows that mattered
had real ones.  Constraining the search to REAL poles at r <= 0.97 gives:

    poles [0.97, 0.47509]  -- both REAL, so no ringing at all
    step response: 0.0 % overshoot, 130 ms settle
    pulse response: ZERO oscillation cycles

  It is an overdamped low-pass, not a resonator.  I nearly discarded a viable design by
  reading Q off real poles; recorded so it is not repeated.

WHAT IT DOES
------------
    freq      FLYING     V172       ratio
    0.5 Hz    1.0000     1.0067     1.007     <- DC unchanged: no steady-state feel cost
    3   Hz    0.9975     0.8501     0.852     <- driver band, 15 % down
    5   Hz    0.9931     0.6802     0.685     <- driver band, 32 % down
    8.64 Hz   0.9790     0.4441     0.454     <- THE RATCHET, 2.2x attenuated
    21  Hz    0.8659     0.0902     0.104     <- THE GRIND, 9.6x attenuated
    40  Hz    0.4522     0.1348     0.298

  Loop effect on the same anchoring used for the slope cap (P.L real-positive, measured
  Q_eff/Q_passive = 14.3):
      effective map s at 8.64 Hz: 1.958 -> 0.888
      |L| 1.713  ->  P.L 0.5640  ->  |1-P.L| 0.4360  ->  Q ratio 2.29
      = 6.2x MORE DAMPED than stock, versus 5.7x for the largest slope-cap dose (V171).

HOW ITS COST DIFFERS FROM V168's -- THIS IS THE POINT
------------------------------------------------------
    V168 slope cap    reduces assist per unit torque at EVERY input speed INCLUDING DC
                      => heavier steering NEAR CENTRE, all the time.
    V172 this build   leaves DC alone (gain 1.007) and reduces assist for FAST inputs
                      => steering weight unchanged at rest; assist arrives ~130 ms slower
                         on quick inputs, and 3-5 Hz driver content loses 15-32 %.

  Neither is free.  They are different trades and the operator should pick on feel:
  V168 costs static weight, V172 costs response speed.
  ** V172 also attenuates the GRIND 9.6x, which V168 does not. **

WHAT A NULL WILL LICENSE  (written BEFORE the cut)
---------------------------------------------------
Scored from ONE continuous 15 s engaged creep pass with score_band_excess.py:
  * ratchet 5-12 Hz below its slope-matched null  => confirmed, and the loop-gain account
    holds for a frequency-selective cut as well as a broadband one.
  * ratchet unchanged  => 6.2x predicted damping produced nothing, which falsifies the
    real-positive P.L assumption for BOTH this build and V168 -- the two levers share it,
    so a null here is informative about V168 too.
  * grind 15-25 Hz should ALSO fall, by more than the ratchet (9.6x vs 2.2x filter
    attenuation).  If the ratchet moves and the grind does not, the shared-loop account is
    wrong somewhere and the difference names where.

RISK
----
4 float32 cells the kit has already changed on-car without fault (V106/V107 moved exactly
these four).  Enable already 1 on the base.  No cave, no code edit.  Poles real and inside
the unit circle with margin.  The one genuine unknown is whether 130 ms of added lag in the
dominant assist lane feels like a "catch" -- that is a FEEL question the drive answers.

BASE = V158, so this build also carries V158's damper shape.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

# --- PATH BOOTSTRAP -------------------------------------------------------------------------
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

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
import build_v106_tva as V106B                                                    # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V172_WRITE", "").strip().lower()

BASE_NAME = "_v158_V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE_plain_image.bin"
BASE_SHA = "42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf"

u16 = V106B.u16

# ---- THE EDIT -------------------------------------------------------------------------------
# Specified by RAW LITTLE-ENDIAN WORD, never by a decimal: a 6-dp decimal does not round-trip
# a float32, and three agents once produced three different byte strings for one coefficient
# because each wrote a decimal.  The float value is ASSERTED against the raw word below.
COEFFS = {
    0xC60A8: (0xBFB8F890, "C_A8  -1.44508553   feedback, z^1"),
    0xC60AC: (0x3EEBF24E, "C_AC  +0.460833013  feedback, z^0"),
    0xC60B0: (0xBFFC4794, "C_B0  -1.97093439   output, s2"),
    0xC60B4: (0x3F0C6945, "C_B4  +0.548481286  input"),
}
ENABLE, ENABLE_VAL = 0xC649B, 1        # already ON on the base; asserted, NOT written
GATE, GATE_VAL = 0xC64FA, 5
CAP_CAL, CAP_VAL = 0xC6384, 2048       # slope cap left at STOCK -- this build is the ALTERNATIVE
FS = 1000.0

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def f32_at(buf, off):
    return struct.unpack_from("<f", buf, off)[0]


def resp(c, f):
    """Analytic transfer function, validated against the decompiled recursion."""
    import cmath
    z = cmath.exp(2j * 3.141592653589793 * f / FS)
    num = c["C_B4"] * ((1 - c["C_AC"]) + (c["C_B0"] - c["C_A8"]) * z)
    den = z * z + c["C_A8"] * z + c["C_AC"]
    return abs(num / den + c["C_B4"])


def coeffs_of(buf):
    return {"C_A8": f32_at(buf, 0xC60A8), "C_AC": f32_at(buf, 0xC60AC),
            "C_B0": f32_at(buf, 0xC60B0), "C_B4": f32_at(buf, 0xC60B4)}


def poles_of(c):
    a, b = c["C_A8"], c["C_AC"]
    disc = a * a - 4 * b
    if disc >= 0:
        r = disc ** 0.5
        return [(-a + r) / 2, (-a - r) / 2], True
    r = (-disc) ** 0.5
    return [complex(-a / 2, r / 2), complex(-a / 2, -r / 2)], False


def build():
    print("=" * 102)
    print("  V172 -- ASSIST-MAP SECOND-ORDER SECTION RETUNED   (base V158)")
    print("=" * 102)

    print("\n  [1] BASE")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base image sha256 matches V158 ({BASE_SHA[:16]}...)")
    code = bytearray(base)

    print("\n  [2] THE SECTION IS ENABLED ON THE BASE, AND THE SLOPE CAP IS LEFT ALONE")
    check(base[ENABLE] == ENABLE_VAL,
          f"0x{ENABLE:05X} enable = {ENABLE_VAL} (Honda ships 0; the kit enabled it at V104)")
    check(base[GATE] == GATE_VAL, f"0x{GATE:05X} gate = {GATE_VAL}")
    check(u16(base, CAP_CAL) == CAP_VAL,
          f"0x{CAP_CAL:05X} slope cap = {CAP_VAL} (STOCK) -- V172 is the ALTERNATIVE to V168")

    print("\n  [3] THE FLYING TUNING PASSES THE RATCHET -- verified, not assumed")
    old = coeffs_of(base)
    g_old = resp(old, 8.64)
    check(g_old > 0.90,
          f"flying section gain at 8.64 Hz = {g_old:.4f} -- it does NOT attenuate the ratchet")

    print("\n  [4] THE EDIT -- four float32 cells, specified by RAW WORD")
    attributed = set()
    for off, (word, why) in sorted(COEFFS.items()):
        struct.pack_into("<I", code, off, word)
        attributed |= set(range(off, off + 4))
        print(f"      0x{off:05X}  {f32_at(base, off):+.9g} -> {f32_at(code, off):+.9g}   {why}")
    for off, (word, _) in COEFFS.items():
        check(struct.unpack_from("<I", code, off)[0] == word,
              f"0x{off:05X} raw word is exactly {word:08X} (asserted against the LOSSY decimal)")

    print("\n  [5] THE RESULT -- computed from the BUILT IMAGE's own bytes")
    new = coeffs_of(code)
    p, real = poles_of(new)
    check(real, f"poles are REAL {[round(float(x), 5) for x in p]} -- overdamped, cannot ring")
    check(max(abs(x) for x in p) < 0.99,
          f"pole radius {max(abs(float(x)) for x in p):.5f} < 0.99 (stable with margin)")
    for f, lim, tag in ((0.5, None, "DC -- no steady-state feel cost"),
                        (3.0, None, "driver band"), (5.0, None, "driver band"),
                        (8.64, 0.60, "THE RATCHET"), (21.0, 0.20, "THE GRIND")):
        g0, g1 = resp(old, f), resp(new, f)
        print(f"      {f:6.2f} Hz   {g0:.4f} -> {g1:.4f}   ({g1/g0:.3f}x)   {tag}")
        if lim is not None:
            check(g1 < lim, f"{f:.2f} Hz attenuated below {lim}")
    check(abs(resp(new, 0.5) - 1.0) < 0.02,
          f"DC gain {resp(new, 0.5):.4f} within 2 % of unity -- the point of this lever")

    print("\n  [6] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = struct.unpack_from("<I", code, blk[1])[0]
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    print("\n  [7] FULL BYTE DIFF vs V158 -- ZERO UNATTRIBUTED")
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
    check(payload <= 16, f"{payload} payload bytes (<= 16: four float32 coefficients)")
    check(u16(code, CAP_CAL) == CAP_VAL, "slope cap still STOCK -- V172 does not stack with V168")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V172 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V172-V158BASE-ASSIST.SECTION.RETUNE.REALPOLE"
    img_out = plain_image_path(f"_v172_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V172_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
