#!/usr/bin/env python3
r"""
V174 -- THE PRE-REGISTERED NEXT POINT ON THE V173 FRONTIER.  Base = V158.  3 cells.
        Same lever, same shape, same notch.  ONE knob moved: the slow pole 0.970 -> 0.980.

WHY THIS EXISTS BEFORE THE V173 DRIVE
--------------------------------------
V173 is the fly-first build.  This is the build to fly *if* the operator's verdict on V173 is
"better, but the ratcheting is still there".  It is cut now so that verdict costs no build delay.
** It is NOT an alternative to V173 and must not be flown first. **  V173 is the cheaper point on
the same curve; flying the expensive point first throws away the ability to tell which one the
car needed.

THE FRONTIER, AND WHY IT IS A STRAIGHT LINE
--------------------------------------------
The section's slow REAL pole sets both the attenuation and the added lag through one time
constant, so they cannot be separated -- one real pole, one tau.  Measured off the built images:

    p_slow   corner    ratchet @8.17   grind 15-25   added lag @1 Hz
    0.7966   36.19 Hz     -0.26 dB       -1.39 dB        +2.1 ms     (stock)
    0.9700    4.85 Hz     -5.89 dB      -12.61 dB       +29.1 ms     V173
    0.9800    3.22 Hz     -8.77 dB      -16.03 dB       +42.8 ms  <- V174, THIS BUILD
    0.9850    2.41 Hz    -11.03 dB      -18.49 dB       +54.1 ms
    0.9900    1.60 Hz    -14.38 dB      -22.00 dB       +69.2 ms

=> a strikingly linear ~4.8 ms of 1 Hz lag per dB of ratchet attenuation.  V174 buys 2.9 dB more
ratchet and 3.4 dB more grind for 13.7 ms more lag at 1 Hz.
** Do not cut a build past p_slow = 0.985 without an operator lag verdict in hand ** -- beyond
there the added lag exceeds anything this kit has ever shipped, and the operator's standing
instruction is that apparent mass and friction must NOT be the price of fixing the ratcheting.

WHY BROADBAND, AND NOT A NOTCH ON THE RATCHET
----------------------------------------------
Settled twice over, and re-derived from the image bytes on 2026-08-29:
  * the mode WANDERS.  A synthetic FIXED 8.3333 Hz line reproduces through the same estimator to
    sd 0.005 Hz; the corpus gives sd 0.79 Hz between routes, of which 0.71 Hz survives a
    within-route split-half control.  The frequency genuinely moves ~+-9 % drive to drive.
  * a re-centred notch fails GATE 2 MAGNITUDE by 47x.  C_B4 = (1+C_A8+C_AC)/(2+C_B0) and
    2+C_B0 = 2-2cos(theta) -> 0 as the notch approaches DC, so at 8.17 Hz C_B4 = 36.98 and
    max|H| = 46.91 -- it AMPLIFIES the grind band 6.5x (+16.3 dB) and destroys Honda's 55 Hz
    null by 10^5.  This is the reason V173's docstring already gave (C_B4 ~ 1/f^2).
  * and the lineage rule stands: "THE NOTCH LEVER IS SPENT -- do not re-propose a re-centred
    0xC60A8 biquad without new evidence."  V105 flew a 25.5 Hz notch and failed.
=> the poles, not the notch, are the lever in the ratchet band.  C_B0 stays byte-identical.

RISK
----
Identical class to V173: three float32 calibration cells the kit has already moved on-car without
fault (V106/V107/V173 all touch this group).  No cave, no code edit, no RAM claim.  Poles REAL at
[0.980, 0.475] => overdamped, cannot ring.  C_B0 untouched => Honda's 55.23 Hz notch bit-for-bit.
GATE 2 magnitude: max |H| = 0.988 over 0.5-499 Hz => the section can only REMOVE loop gain.
GATE 1 as V173: gp-0x6b86 has exactly ONE consumer outside its producer (the aggregator at
0x3AC7C) and no monitor watches it.
** The honest cost, stated plainly: +42.8 ms of group delay at 1 Hz (-15.9 deg).  That is lag the
operator will feel as steering weight.  It is the mechanism, not a side effect. **
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
WRITE_MODE = os.environ.get("ACCORD_V174_WRITE", "").strip().lower()

BASE_NAME = "_v158_V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE_plain_image.bin"
BASE_SHA = "42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf"

u16 = V106B.u16

# ---- THE EDIT -------------------------------------------------------------------------------
# Specified by RAW LITTLE-ENDIAN WORD.  A 6-dp decimal does not round-trip a float32 -- three
# agents once produced three different byte strings for one coefficient because each wrote a
# decimal.  Each word is re-derived from the FORMULA below and asserted against it, so the
# rule cannot be silently forgotten.
P_SLOW, P_FAST = 0.980, 0.475
COEFFS = {
    0xC60A8: (0xBFBA3D71, "C_A8  -1.45500004    pole sum      -> poles 0.980 / 0.475, both REAL"),
    0xC60AC: (0x3EEE5604, "C_AC  +0.465499997   pole product"),
    0xC60B4: (0x3DB466E4, "C_B4  +0.0880868733  input gain, solved for unity DC"),
}
# C_B0 (0xC60B0) is DELIBERATELY NOT in the edit set -- it alone sets the notch frequency and
# Honda's 55.23 Hz placement is kept bit-for-bit.  Asserted unchanged below.
NOTCH_CAL, NOTCH_WORD = 0xC60B0, 0xBFF0BE0E
ENABLE, ENABLE_VAL = 0xC649B, 1        # already ON on the base; asserted, NOT written
GATE, GATE_VAL = 0xC64FA, 5
CAP_CAL, CAP_VAL = 0xC6384, 2048       # slope cap left at STOCK -- does not stack with V168
FS = 1000.0

# V173's measured response at the two endpoint frequencies -- V174 must beat both, strictly.
V173_AT_RATCHET, V173_AT_GRIND = 0.476076, 0.189446

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
    """Analytic transfer function, in the same collapsed form V173 validated against the
    decompiled recursion.  Algebraically C_B4*(z^2 + C_B0*z + 1)/(z^2 + C_A8*z + C_AC)."""
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


def group_delay_ms(c, f):
    import cmath
    h = 1e-3
    ph = []
    for x in (f - h, f, f + h):
        z = cmath.exp(2j * 3.141592653589793 * x / FS)
        ph.append(cmath.phase(c["C_B4"] * (z * z + c["C_B0"] * z + 1.0)
                              / (z * z + c["C_A8"] * z + c["C_AC"])))
    for i in (1, 2):                                    # unwrap
        while ph[i] - ph[i - 1] > 3.141592653589793:
            ph[i] -= 2 * 3.141592653589793
        while ph[i] - ph[i - 1] < -3.141592653589793:
            ph[i] += 2 * 3.141592653589793
    return -(ph[2] - ph[0]) / (2 * 2 * 3.141592653589793 * h) * 1000.0


def build():
    print("=" * 102)
    print("  V174 -- ASSIST SECTION SLOW POLE 0.970 -> 0.980, HONDA NOTCH KEPT   (base V158)")
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
          f"0x{CAP_CAL:05X} slope cap = {CAP_VAL} (STOCK) -- does not stack with V168")

    print("\n  [3] THE COEFFICIENTS ARE RE-DERIVED FROM THE FORMULA, NOT TYPED")
    b0 = f32_at(base, NOTCH_CAL)
    a8 = struct.unpack("<f", struct.pack("<f", -(P_SLOW + P_FAST)))[0]
    ac = struct.unpack("<f", struct.pack("<f", P_SLOW * P_FAST))[0]
    b4 = struct.unpack("<f", struct.pack("<f", (1.0 + a8 + ac) / (2.0 + b0)))[0]
    for off, want in ((0xC60A8, a8), (0xC60AC, ac), (0xC60B4, b4)):
        word = struct.unpack("<I", struct.pack("<f", want))[0]
        check(word == COEFFS[off][0],
              f"0x{off:05X} formula gives raw word {word:08X}, matching the pinned constant")

    print("\n  [4] THE FLYING TUNING PASSES THE RATCHET -- verified, not assumed")
    old = coeffs_of(base)
    check(resp(old, 8.64) > 0.90,
          f"flying section gain at 8.64 Hz = {resp(old, 8.64):.4f} -- does NOT attenuate it")

    print("\n  [5] THE EDIT -- three float32 cells, specified by RAW WORD")
    attributed = set()
    for off, (word, why) in sorted(COEFFS.items()):
        struct.pack_into("<I", code, off, word)
        attributed |= set(range(off, off + 4))
        print(f"      0x{off:05X}  {f32_at(base, off):+.9g} -> {f32_at(code, off):+.9g}   {why}")

    print("\n  [6] THE RESULT -- computed from the BUILT IMAGE's own bytes")
    new = coeffs_of(code)
    p, real = poles_of(new)
    check(real, f"poles are REAL {[round(float(x), 5) for x in p]} -- overdamped, cannot ring")
    check(abs(max(abs(x) for x in p) - P_SLOW) < 1e-5,
          f"slow pole is {max(abs(float(x)) for x in p):.6f}, the intended {P_SLOW}")
    check(max(abs(x) for x in p) < 0.99,
          f"pole radius {max(abs(float(x)) for x in p):.5f} < 0.99 (stable with margin)")
    for f, tag in ((0.5, "DC -- no steady-state feel cost"), (3.0, "driver band"),
                   (8.64, "THE RATCHET"), (21.0, "THE GRIND")):
        g0, g1 = resp(old, f), resp(new, f)
        print(f"      {f:6.2f} Hz   {g0:.4f} -> {g1:.4f}   ({g1/g0:.3f}x)   {tag}")
    check(resp(new, 8.64) < V173_AT_RATCHET,
          f"ratchet {resp(new, 8.64):.6f} is STRICTLY better than V173's {V173_AT_RATCHET}")
    check(resp(new, 21.0) < V173_AT_GRIND,
          f"grind   {resp(new, 21.0):.6f} is STRICTLY better than V173's {V173_AT_GRIND}")
    check(abs(resp(new, 0.5) - 1.0) < 0.02,
          f"DC gain {resp(new, 0.5):.4f} within 2 % of unity -- the point of this lever")
    check(struct.unpack_from("<I", code, NOTCH_CAL)[0] == NOTCH_WORD,
          f"0x{NOTCH_CAL:05X} C_B0 UNCHANGED at {NOTCH_WORD:08X} -- Honda's 55.23 Hz notch kept")
    check(resp(new, 55.23) < 0.001,
          f"55.23 Hz still notched: {resp(new, 55.23):.6f} (flying {resp(old, 55.23):.6f})")
    import numpy as _np
    _g = max(resp(new, float(x)) for x in _np.arange(0.5, 499.5, 0.5))
    check(_g <= 1.001, f"GATE 2 magnitude: max |H| to Nyquist is {_g:.4f} -- never amplifies")
    lag = group_delay_ms(new, 1.0) - group_delay_ms(old, 1.0)
    print(f"      added group delay at 1 Hz: {lag:+.1f} ms   "
          f"** THE HONEST COST -- the operator feels this as steering weight **")
    check(lag < 50.0, f"added lag at 1 Hz is {lag:.1f} ms (< 50 ms ceiling for this frontier point)")

    print("\n  [7] CRC RECOMPUTATION")
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

    print("\n  [8] FULL BYTE DIFF vs V158 -- ZERO UNATTRIBUTED")
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
    check(u16(code, CAP_CAL) == CAP_VAL, "slope cap still STOCK")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V174 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    tag = "V174-V158BASE-ASSIST.SECTION.POLE.0.980.NOTCH.KEPT"
    img_out = plain_image_path(f"_v174_{tag}_plain_image.bin")
    rwd_out = Path(RWD_DIR, f"39990-TVA,A160-{tag}-0x{START:X}-0x{END:X}.rwd")

    if WRITE_MODE == "rwd":
        Path(img_out).write_bytes(bytes(code))
        Path(rwd_out).write_bytes(rwd)
        print(f"\n      WROTE {img_out}")
        print(f"      WROTE {rwd_out}")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V174_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}   "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V173 IS THE FLY-FIRST BUILD.  V174 is for the verdict "
          "'better, but still there'. **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
