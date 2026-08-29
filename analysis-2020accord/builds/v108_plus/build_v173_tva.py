#!/usr/bin/env python3
r"""
V173 -- THE ASSIST SECTION RETUNED **WITHOUT GIVING UP HONDA'S NOTCH**.  Base = V158.  3 cells.
        SUPERSEDES V172 as fly-first.  Same poles, same lag, same ratchet effect, notch KEPT.

WHAT CHANGED SINCE V172, AND WHY
---------------------------------
Collapsing the decompiled form shows the section is a TEXTBOOK notch whose parameters SEPARATE:

    H(z) = C_B4 * ( z^2 + C_B0*z + 1 ) / ( z^2 + C_A8*z + C_AC )

  * the NUMERATOR's roots have product 1 => the zeros are ALWAYS exactly on the unit circle,
    so this is ALWAYS a true notch, at 2*cos(theta) = -C_B0.  ** C_B0 ALONE sets the notch. **
  * the poles are set by C_A8/C_AC ALONE.  Notch frequency and damping are INDEPENDENT.
  * DC gain = C_B4 * (2 + C_B0) / (1 + C_A8 + C_AC).

STOCK C_B0 = -1.8808 puts Honda's notch at 55.23 Hz, where it is -43.9 dB.  **V172 moved it to
27.17 Hz** as a side effect of letting an optimiser choose all four coefficients -- so V172 gives up
Honda's 55 Hz notch entirely (0.000128 -> 0.251316 there).  ** We do not know what that notch is FOR. **
Honda placed a deep null at a specific frequency in the dominant assist lane deliberately.

V173 keeps `C_B0` BYTE-IDENTICAL to stock and moves ONLY the poles:

    freq        FLYING      V172        V173
    0.5 Hz      0.999965    1.006656    0.994633     DC preserved
    3   Hz      0.997530    0.850073    0.847560     driver band, same as V172
    8.64 Hz     0.978950    0.444078    0.476076     THE RATCHET -- same as V172
    21  Hz      0.865930    0.090235    0.189446     the grind: 4.6x (V172 got 9.6x)
    40  Hz      0.452204    0.134765    0.054184     better than V172
    55.23 Hz    0.000128    0.251316    0.000013     ** HONDA'S NOTCH KEPT, and deeper **

  group delay added at 0.5 Hz: V172 +30.1 ms, V173 +30.1 ms -- IDENTICAL (same poles).
  loop effect: V173 5.8x more damped vs V172's 6.1x -- within a rounding of each other.
  max |H| over the full band to Nyquist: 0.9946 => V173 NEVER amplifies anything.

THE TRADE, STATED PLAINLY
-------------------------
V173 gives up half the GRIND attenuation (4.6x vs 9.6x) to keep a notch whose purpose is unknown.
That is the right side to err on: the ratchet is the UNSOLVED symptom and both builds are equal
there, while the grind ALREADY has V158's damper on this same base.  And V173 touches THREE cells
instead of four.

WHY NOT PUT THE NOTCH ON THE RATCHET
-------------------------------------
Tried, and it is structurally impossible: C_B4 = DC*(1+C_A8+C_AC)/(2+C_B0) and 2+C_B0 = 2-2cos(theta)
-> 0 as the notch approaches DC, so C_B4 scales as ~1/f^2.
    notch 8.64 Hz => C_B4 = 13.576 => amplifies out-of-band by 1503x
    notch 27   Hz => C_B4 =  1.393 => amplifies by 120x
    notch 55.2 Hz => C_B4 =  0.336 => amplifies by 1.0x  (Honda's placement -- the ONLY free one)
=> Honda put the notch at 55 Hz because that is where it costs nothing.  A notch at the ratchet
   would need 13.6x input gain and would amplify everything else.  ** The poles, not the notch, are
   the lever in the ratchet band. **  My earlier remark that the optimiser "did not understand the
   structure" was wrong and is withdrawn -- it found the right shape for the right reason.

RISK
----
THREE float32 cells the kit has already changed on-car without fault (V106/V107 moved these).
`C_B0` untouched, so Honda's notch is bit-for-bit preserved.  Enable already 1 on the base.  No cave,
no code edit.  Poles REAL at [0.97, 0.475] => no ringing; step overshoot 0.0 %.
GATE 1 cleared separately: `gp-0x6b86` has exactly ONE consumer outside its producer (the aggregator
at 0x3AC7C) and no monitor watches it, so heavy filtering cannot trip a fault path.

Everything else -- the drive, the pre-registered outcomes, the sub-band grind attribution -- is as
written for V172.  BASE = V158, so this build also carries V158's damper shape.
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
WRITE_MODE = os.environ.get("ACCORD_V173_WRITE", "").strip().lower()

BASE_NAME = "_v158_V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE_plain_image.bin"
BASE_SHA = "42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf"

u16 = V106B.u16

# ---- THE EDIT -------------------------------------------------------------------------------
# Specified by RAW LITTLE-ENDIAN WORD, never by a decimal: a 6-dp decimal does not round-trip
# a float32, and three agents once produced three different byte strings for one coefficient
# because each wrote a decimal.  The float value is ASSERTED against the raw word below.
COEFFS = {
    0xC60A8: (0xBFB8F5C3, "C_A8  -1.44500005   pole sum      -> poles 0.970 / 0.475, both REAL"),
    0xC60AC: (0x3EEBE76D, "C_AC  +0.460750014  pole product"),
    0xC60B4: (0x3E074D3C, "C_B4  +0.132130563  input gain, solved for unity DC"),
}
# C_B0 (0xC60B0) is DELIBERATELY NOT in the edit set: it alone sets the notch frequency, and
# Honda's 55.23 Hz placement is kept bit-for-bit.  Asserted unchanged below.
NOTCH_CAL, NOTCH_WORD = 0xC60B0, 0xBFF0BE0E
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
    print("  V173 -- ASSIST SECTION POLES RETUNED, HONDA NOTCH KEPT   (base V158)")
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
    check(struct.unpack_from("<I", code, NOTCH_CAL)[0] == NOTCH_WORD,
          f"0x{NOTCH_CAL:05X} C_B0 UNCHANGED at {NOTCH_WORD:08X} -- Honda's 55.23 Hz notch kept")
    check(resp(new, 55.23) < 0.001,
          f"55.23 Hz still notched: {resp(new, 55.23):.6f} (flying {resp(old, 55.23):.6f})")
    import numpy as _np
    _f = _np.arange(0.5, 499.5, 0.5)
    _g = max(resp(new, float(x)) for x in _f)
    check(_g <= 1.001, f"max |H| over the FULL band to Nyquist is {_g:.4f} -- never amplifies")

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
    check(payload <= 12, f"{payload} payload bytes (<= 12: THREE float32 coefficients)")
    check(u16(code, CAP_CAL) == CAP_VAL, "slope cap still STOCK -- V172 does not stack with V168")

    print("\n  [8] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V173 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V173-V158BASE-ASSIST.SECTION.POLES.NOTCH.KEPT"
    img_out = plain_image_path(f"_v173_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [9] NOT WRITTEN -- set ACCORD_V173_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
