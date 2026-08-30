# -*- coding: utf-8 -*-
r"""V229 -- V228 WITH HONDA'S 55 Hz NOTCH PUT BACK. ONE LEVER, SIXTEEN BYTES.

WHY THIS BUILD EXISTS.

There is exactly ONE biquad in this ECU (`0xC60A8/AC/B0/B4`), and Honda uses it as a **55 Hz notch**:

    car / Honda   zeros 55.23 Hz, poles 42.35 Hz (r 0.797)   deepest cut 55 Hz, |H| = 0.0063  (159x)
    V208-V228     zeros 20.50 Hz, poles 15.50 Hz (r 0.958)   deepest cut 21 Hz, |H| = 0.0433  (23x)

Every build since V172 has RELOCATED that cell down to ~20 Hz to put a cut where the 15-22 Hz grinding
band is. **The kit has been moving one filter, not adding one** -- and relocating it VACATES Honda's
55 Hz cut. Nothing in the record priced that, because CAN's Nyquist is 50.5 Hz: 55 Hz folds down and
masquerades as 30-49 Hz content, so no CAN-based instrument could ever see the bill.

                  |H| 18.5 Hz   |H| 55 Hz   |H| 65 Hz
    car / Honda      0.8978      0.0063      0.2472
    V228             0.2045      0.6285      0.6457     <- 100x louder at 55 Hz (+40 dB)

THE MEASUREMENT THAT DECIDES IT. On the alias-free audio (0-100 Hz), engaged vs not-engaged, matched
on BOTH speed and gear (gear pins engine order -- 60-72 Hz is 1800-2160 rpm of 4-cyl 2nd order, a real
confound), route-level bootstrap:

    band (Hz)   direct acoustic        AM of broadband carrier
    15-22        1.45x [1.03, 3.70]     1.21x [1.05, 1.39]      <- where the notch program aims
    50-60        2.13x [1.13, 3.82]     1.58x [1.10, 2.70]      <- where Honda's notch cuts
    60-72        2.22x [1.27, 5.04]     1.34x [1.06, 2.05]

    ** BOTH bands carry licensed LKAS-caused noise. **

WHAT IS **NOT** CLAIMED. 50-72 Hz is NOT established as worse than 15-22 Hz. The band CIs overlap
heavily, so the honest test is paired within route, and it is NOT licensed on either channel:
direct 1.73x [0.48, 2.55] (4/6 routes), AM 1.23x [0.87, 1.86] (4/7). **The notch program is not aimed
at the wrong band.** It is aimed at one licensed band out of several.

THE ARGUMENT, WHICH DOES NOT DEPEND ON THE ORDERING. Both bands are licensed problems of comparable
size. V228 therefore **gives up a 159x cut in a 2.2x problem to buy a 4.9x cut in a 1.45x problem** --
the cut depths differ by 32x. When two bands are comparably affected, the deeper cut is worth more, and
that is true whichever band is marginally worse.

AND IT SATISFIES A STANDING CONSTRAINT V228 VIOLATES. `docs/BUILD-LINEAGE.md` on the `0xC40DC` lever:
*"It must ship WITH the notch revert or not at all -- across 54-74.5 Hz V105's coefficients leave the
base-assist lane a geometric-mean 5.15x (+14.2 dB) louder than Honda's."* V228 ships `0xC40DC` = 22
(Honda's, which passes MORE HF: corner 21.3 -> 67.0 Hz) together with a notch that no longer cuts
54-74 Hz. **Both cells push HF the same way -- exactly the combination the record forbids.** V229 is
that notch revert.

IT ALSO REMOVES AN UNFLOWN PHASE PERTURBATION. V228 carries -25.4 deg at 7.79 Hz and -39.3 deg at
10.5 Hz against the car's -10.6 / -14.4, and NO route in the corpus has ever flown past -21.3 deg --
the whole V172->V228 notch arc is unflown. 9-12 Hz is the band the kit's own Re(Z) instrument ranks
most anti-damped (P = 1.000), and whether lag there helps or hurts is UNRESOLVED. V229 returns that
band to the only geometry ever actually driven.

WHAT V229 KEEPS FROM V228 -- every lever except the notch:
  * Lever B `0xC6446` = 13107 (the kit's only measured on-car win, V88)
  * `0xC40DC` = 22, Honda's alpha2                * `0xC63AE` = 512
  * `0xC407E` = 511 hard-fault interlock          * the friction lane restored to the car
  * the 427 telemetry tap (`0x55DF2` / `0x55E10`) * the 164-byte cave, BYTE-IDENTICAL

CLASS. This is a REVERT, and the first build since V172 to decline the relocated notch. It is not a new
lever and does not pretend to be one. Every notch build for ~56 builds has bought 15-22 Hz by selling
54-74 Hz; V229 is the first to ask whether that trade was ever worth making.

HOW THE COEFFICIENTS ARE SPECIFIED. **By copying the 16 bytes out of the flown V122 image**, not by
re-deriving them from decimals. A 6-dp decimal does not round-trip a float32
(`feedback-float-spec-must-be-the-formula`); copying bytes cannot go wrong at all.

RISK, PLAINLY. V229 gives up V228's 4.9x cut at 18.5 Hz. If the operator's grinding really does live at
15-22 Hz, **V229 will be worse there than V228** -- that is the honest cost, and it is the mirror of
V228's own. The two builds are a clean 16-byte single-variable pair, and driving both settles which
side of the trade his symptom sits on. That question has been open since V172.
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

import build_vfourframe_tva as FF                                                 # noqa: E402
import build_v53_tva as V53                                                       # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table     # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V229_WRITE", "").strip().lower()

BASE_NAME = "_v228_V228-V222BASE-GAIN.STAYS.6X.AS.CAR_plain_image.bin"
BASE_SHA = "6cf12db9fc49aee29e46c169c05fc18415f2a970b477cdae1372d57805748b3c"
DONOR_NAME = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"
DONOR_SHA = "b1f65f0aaaf9e6fabeb3a20605efcf7cb1f1ad6c75cb89573f0b02970d79b5e0"

BIQ, BIQ_LEN = 0xC60A8, 16
V228_BIQ = bytes.fromhex("5ff5f3bfd0b36a3f1be1fdbf9f1f283f")
HONDA_BIQ = bytes.fromhex("f8c2c4bf7576223f0ebef0bf3a3b513f")

# carried levers -- asserted, never re-set
LEVER_B, LEVER_B_VAL = 0xC6446, 13107
ALPHA2, ALPHA2_VAL = 0xC40DC, 22
RESID_SCALE, RESID_VAL = 0xC63AE, 512
FAULT_INTERLOCK, FAULT_VAL = 0xC407E, 511
ARM_SITES = {0x35A06: "844ffb97", 0x35A12: "e049", 0x35A18: "ea370000"}
ARM_CAL = 0xC649B
TAG = "V229-V228BASE-HONDA.55HZ.NOTCH.RESTORED"

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


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def resp(b, fr, fs=1000.0):
    """|H| and phase from the ENCODED float32 in the image."""
    import cmath
    import math
    z = cmath.exp(2j * math.pi * fr / fs)
    h = (f32(b, BIQ + 12) * (z * z + f32(b, BIQ + 8) * z + 1.0)
         / (z * z + f32(b, BIQ) * z + f32(b, BIQ + 4)))
    return abs(h), math.degrees(cmath.phase(h))


def build():
    print("=" * 102)
    print("  V229 -- V228 WITH HONDA'S 55 Hz NOTCH RESTORED.  ONE LEVER, 16 BYTES.")
    print("=" * 102)

    print("\n  [1] BASE = V228")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V228 base sha256 matches")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")

    print("\n  [2] DONOR = the FLOWN V122 image -- coefficients COPIED, never re-derived")
    donor = Path(plain_image_path(DONOR_NAME)).read_bytes()
    check(hashlib.sha256(donor).hexdigest() == DONOR_SHA, "V122 donor sha256 matches")
    check(donor[BIQ:BIQ + BIQ_LEN] == HONDA_BIQ, "donor biquad bytes are Honda's")
    check(base[BIQ:BIQ + BIQ_LEN] == V228_BIQ, "base biquad bytes are V208/V228's")

    code = bytearray(base)
    attributed = set()

    print("\n  [3] THE ONE EDIT")
    code[BIQ:BIQ + BIQ_LEN] = HONDA_BIQ
    attributed |= set(range(BIQ, BIQ + BIQ_LEN))
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == HONDA_BIQ, "biquad restored to Honda's 16 bytes")
    check(bytes(code[BIQ:BIQ + BIQ_LEN]) == donor[BIQ:BIQ + BIQ_LEN],
          "and byte-identical to the FLOWN V122 image")

    print("\n  [4] THE RESPONSE, READ BACK OUT OF THE BUILT IMAGE")
    for fr in (7.79, 10.5, 18.5, 55.0, 65.0):
        m_o, p_o = resp(base, fr)
        m_n, p_n = resp(code, fr)
        print(f"      {fr:6.2f} Hz   V228 {m_o:.4f}/{p_o:+7.1f}deg   ->   "
              f"V229 {m_n:.4f}/{p_n:+7.1f}deg")
    check(resp(code, 55.0)[0] < 0.01, "55 Hz cut restored (|H| < 0.01)")
    check(resp(code, 18.5)[0] > 0.80, "18.5 Hz cut GIVEN UP -- this is the cost, asserted openly")
    check(abs(resp(code, 10.5)[1] - (-14.4)) < 1.0,
          "9-12 Hz phase back on the only geometry ever driven (-14.4 deg)")

    print("\n  [5] EVERY OTHER LEVER IS UNTOUCHED")
    check(u16(code, LEVER_B) == LEVER_B_VAL, f"Lever B 0x{LEVER_B:05X} = {LEVER_B_VAL} (V88's win)")
    check(code[ALPHA2] == ALPHA2_VAL, f"0x{ALPHA2:05X} alpha2 = {ALPHA2_VAL} (Honda)")
    check(u16(code, RESID_SCALE) == RESID_VAL, f"0x{RESID_SCALE:05X} = {RESID_VAL}")
    check(u16(code, FAULT_INTERLOCK) == FAULT_VAL,
          f"0x{FAULT_INTERLOCK:05X} hard-fault interlock FROZEN at {FAULT_VAL}")
    check(bytes(code[0xC4B34:0xC4B34 + 164]) == bytes(base[0xC4B34:0xC4B34 + 164]),
          "the 164-byte cave is BYTE-IDENTICAL -- no cave change, not the bricking class")

    print("\n  [6] THE V103 ARMING IS STILL INTACT -- a reverted notch must still RUN")
    for a, want in sorted(ARM_SITES.items()):
        got = bytes(code[a:a + len(bytes.fromhex(want))]).hex()
        check(got == want, f"0x{a:05X} = {want} (arm source -> LKAS flag gp-0x6806)")
    check(code[ARM_CAL] == 1, f"0x{ARM_CAL:05X} = 1 (biquad enabled)")

    print("\n  [7] CRC RECOMPUTATION")
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in sorted(attributed)})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in attributed),
              f"no edit on trailer 0x{blk[1]:06X}")
        oldc = u32(code, blk[1])
        newc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], newc)
        attributed |= set(range(blk[1], blk[1] + 4))
        print(f"      [0x{blk[0]:06X},0x{blk[1]:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block byte-identical to base")

    print("\n  [8] FULL BYTE DIFF vs V228")
    diff = [a for a in range(START, END) if code[a] != base[a]]
    check(not [a for a in diff if a not in attributed],
          f"all {len(diff)} differing bytes attributed")
    pay = [a for a in diff if (a & 0xFFF) < 0xFFC]
    _exp = sum(1 for i in range(BIQ_LEN) if V228_BIQ[i] != HONDA_BIQ[i])
    check(len(pay) == _exp, f"{len(pay)} payload byte(s), derived expectation {_exp}")
    check(all(BIQ <= a < BIQ + BIQ_LEN for a in pay),
          "every payload byte lies inside the biquad -- nothing else moved")

    print("\n  [9] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V229 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")

    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    if WRITE_MODE == "rwd":
        Path(plain_image_path(f"_v229_{TAG}_plain_image.bin")).write_bytes(bytes(code))
        Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd").write_bytes(rwd)
        print("\n      WROTE image + rwd")
    else:
        print("\n  [10] NOT WRITTEN -- set ACCORD_V229_WRITE=rwd to emit the files")

    print("\n" + "=" * 102)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed")
    print("  ** V229 = V228 with Honda's 55 Hz notch put back. SIXTEEN BYTES apart.            **")
    print("  ** There is ONE biquad. Every build since V172 RELOCATED it to ~20 Hz, which      **")
    print("  ** VACATES Honda's 159x cut at 55 Hz. No CAN instrument could see that: Nyquist   **")
    print("  ** is 50.5 Hz, so 55 Hz folds down and masquerades as 30-49 Hz content.           **")
    print("  ** Audio, speed AND gear matched, route-clustered: LKAS raises 15-22 Hz by 1.45x  **")
    print("  ** and 50-72 Hz by 2.1-2.2x -- BOTH licensed. So V228 gives up a 159x cut in a    **")
    print("  ** 2.2x problem to buy a 4.9x cut in a 1.45x problem: 32x different depths.       **")
    print("  ** NOT CLAIMED: that 50-72 is WORSE than 15-22. Paired within-route is NOT        **")
    print("  ** licensed on either channel (1.73x [0.48,2.55] direct, 1.23x [0.87,1.86] AM).   **")
    print("  ** The argument is the DEPTH asymmetry, which holds either way.                   **")
    print("  ** It also satisfies the lineage constraint V228 violates: 0xC40DC=22 'must ship  **")
    print("  ** WITH the notch revert or not at all'. V228 ships it without.                   **")
    print("  ** COST, PLAINLY: V229 gives up V228's 4.9x cut at 18.5 Hz. If the grinding is    **")
    print("  ** really at 15-22 Hz, V229 is WORSE there. The pair is single-variable, so       **")
    print("  ** driving both settles a question open since V172.                               **")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
