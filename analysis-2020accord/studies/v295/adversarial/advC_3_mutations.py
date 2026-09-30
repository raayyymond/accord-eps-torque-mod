# -*- coding: utf-8 -*-
"""ADV-C part 3 -- MY mutations against the V295 build script's own assertion set (imports the script under test).
M1  CRC-CONSISTENT stray edit in ANOTHER block: the live map knot (slot 7, knot 5) 275 -> 276, its address ADDED to
    `attributed` so the script itself re-CRCs that block.  The CRC walkers cannot see it; only the diff / owning-block
    checks can.
M2  .rwd PAYLOAD corruption with a VALID container checksum: the image handed to encode_x31 has 0xC63EA's low byte
    flipped.  The script's own mutation test never exercises the rwd path (do_rwd=False), so this is new coverage.
M3  a base image that is V294 with ONE filler byte flipped below 0x13000 (outside the flashed range).
M4  the dose one count high AND the file tag forged to match: b = 1051 with B_NEW monkeypatched to 1051 -- i.e. what
    happens if the DECISION CONSTANT itself is wrong.  Shows which assertions are anchored to physics vs to the constant.
ANALYSIS ONLY -- build() is called with the default do-not-write path; nothing is written."""
import os
import struct
import sys
from pathlib import Path

BUILDS = Path("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/builds/v108_plus")
sys.path.insert(0, str(BUILDS))
os.environ.pop("ACCORD_V295_WRITE", None)
os.environ["ACCORD_FIRMWARE_ROOT"] = "C:/Users/dudei/Desktop/Projects/accord-firmwares"
import build_v295_tva as B                                                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(B.plain_image_path(B.BASE_NAME)).read_bytes()


def run(name, **kw):
    R = B.Run(quiet=True, collect=True)
    try:
        r = B.build(base_bytes=kw.pop("base_bytes", base), run=R, **kw)
        fails = list(R.failures)
        sha = r["img_sha"]
    except SystemExit as e:
        fails, sha = list(R.failures) + [("S", str(e))], None
    except Exception as e:                                       # noqa: BLE001
        fails, sha = list(R.failures) + [("X", f"raised {type(e).__name__}: {e}")], None
    by = {k: sum(1 for kk, _ in fails if kk == k) for k in "SCVTX"}
    print(f"\n{'CAUGHT' if fails else 'MISSED'}  {name}: {len(fails)} fire  (S {by['S']} C {by['C']} V {by['V']} T {by['T']} X {by['X']})"
          f"  image sha {sha}")
    for k, m in fails:
        print(f"     [{k}] {m[:150]}")
    return fails


# ---- M1
def m1(code, att):
    p = B.u32(code, B.MAP_PTR + 4 * B.LIVE_SLOT)
    n = B.u16(code, p)
    a = p + 2 + 2 * n + 2 * 5
    assert B.u16(code, a) == 275, B.u16(code, a)
    struct.pack_into("<H", code, a, 276)
    att |= {a, a + 1}
    print(f"   M1: map Y knot 5 at 0x{a:X} 275 -> 276, attributed (script will re-CRC its block)")


f1 = run("M1 CRC-consistent stray map knot (another block, re-CRC'd by the script)", do_rwd=False, mutate_payload=m1)

# ---- M2
orig = B.encode_x31


def bad_encode(headers, blocks, encs):
    e = bytearray(encs[0])
    e[0xC63EA - B.START] ^= 0x01                              # one ENCODED byte of the payload, before the checksum is made
    return orig(headers, blocks, [bytes(e)])


B.encode_x31 = bad_encode
f2 = run("M2 rwd payload byte corrupted, container checksum valid", do_rwd=True)
B.encode_x31 = orig

# ---- M3
bb = bytearray(base)
bb[0x100] ^= 0x01
f3 = run("M3 base = V294 with one filler byte flipped below 0x13000", do_rwd=False, base_bytes=bytes(bb))

# ---- M4
saved = B.B_NEW
B.B_NEW = 1051
f4 = run("M4 decision constant itself wrong: B_NEW = 1051 (the build follows it)", do_rwd=False, b_new=1051)
B.B_NEW = saved

print("\nSUMMARY:", {"M1": len(f1), "M2": len(f2), "M3": len(f3), "M4": len(f4)})
