"""build_v12_tva.py — V12A LKAS-torque build for the 2020 Accord (39990-TVA-A160).

WHY V12 EXISTS
--------------
V11A (build_v11_tva.py) raised every clamp DOWNSTREAM of the steering setpoint to the
±0x3FFF window ceiling. Road test 2026-05-25: imperceptible. Root cause — V11A is a pure
*ceiling-raise*: it left the setpoint GAIN untouched. In `s_lkas_process_steer_cmd`
(@0x52676): `setpoint = clamp( -(comma_cmd << 2), ±0x4000 ) -> 0xFEDF1652`. The downstream
clamps only bind at FULL-scale comma command (4096*4 = 16384 = 0x4000); in normal
lane-keeping openpilot commands far below that, so the setpoint never reaches even the
*stock* clamps and the raised ceilings never engage. A ceiling-raise is invisible unless
the command saturates.

V12A = V11A's clamps + the SETPOINT GAIN: `shl 0x2,r6 -> shl 0x3,r6` @0x526d2 (single byte
0xC2 -> 0xC3). x4 -> x8 doubles the internal command at EVERY level (saturating at ±0x4000
at half comma input), so the effect is felt across the normal operating range. V11A's
raised clamps are what stop the doubled value being re-cut by the arb/distributor/mixer/
shaper staircase. The gain byte (0x32C2: reg2=r6, imm5=2 -> imm5=3) is Ghidra-verified.

The clamp recipe is imported from build_v11_tva (single source of truth, no drift); this
script adds only the gain byte. Self-validates identically: decode our own payload as the
ECU would, splice, replay the 49-block bootloader CRC walk; require 49/49 PASS + full
byte-diff = V11A's sites + the one gain byte. Output -> the configured RWD directory.

CAVEATS (road-test guidance, NOT auto-flashed by this script):
  * Doubling plant gain without an openpilot lateral-PID retune can oscillate. Low-speed
    test first; watch for weave / over-correction. (See TORQUE_MOD_V0.md §1.4, §6.)
  * The shaper's runtime symmetric limit *(gp-0x4f64)=0xFEDF309C may still cap the top end;
    the low-mid range will still feel the gain. (See reference_accord_lkas_window_ceiling.)
STUDY ARTIFACT. No flash until the operator names the file + bus.
"""
import os, sys, gzip, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DIR = os.path.dirname(HERE)
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_v11_tva as v11   # verified clamp recipe + cipher/CRC/header machinery
from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31

# Setpoint GAIN — the multiplier V11A lacked. shl 0x2,r6 (x4) -> shl 0x3,r6 (x8 = 2x slope).
# Byte 0x32C2 LE @0x526d2: reg2=r6, imm5=2; imm5 2->3 flips only the low byte 0xC2->0xC3.
# Lives in the main CRC block [0x13000,0xC4FFC) -> covered by V11's main-block recompute.
GAIN_ADDR, GAIN_OLD, GAIN_NEW = 0x526d2, 0xC2, 0xC3


def patch_gain(code):
    got = code[GAIN_ADDR]
    if got != GAIN_OLD:
        raise AssertionError(f"gain 0x{GAIN_ADDR:05X}: expected 0x{GAIN_OLD:02X} got 0x{got:02X}")
    code[GAIN_ADDR] = GAIN_NEW
    print(f"  0x{GAIN_ADDR:05X}: {GAIN_OLD:02X} -> {GAIN_NEW:02X}   "
          f"setpoint gain shl 0x2 -> shl 0x3 (x4 -> x8 = 2x slope at every command level)")


def build(label, code_stock, headers, tag):
    print("=" * 74)
    print(f"{label}: V11A clamps (window ±0x{v11.W:04X}, clamp ±0x{v11.CLAMP:04X}, "
          f"arb 0x{v11.ARB_NEW:04X}) + setpoint gain shl3   cipher v9b")
    code = bytearray(code_stock)

    v11.patch_code(code)          # distributor / mixer / gate / shaper-in / shaper-final
    v11.patch_arb(code)           # arb setpoint-limit table 15360 -> 16384
    patch_gain(code)              # the multiplier
    for start, crc_off in v11.TOUCHED_BLOCKS:
        v11.recompute_crc(code, start, crc_off)

    dec = build_decode_table(v11.V9B["keys"], v11.V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[v11.START:v11.END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": v11.START, "length": v11.END - v11.START}], [payload])

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = v11.walk(v11.full_image(ecu_plain), label=f"{label}")
    csum = struct.unpack("<I", rwd[-4:])[0]
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw)")
    print(f"  ECU-decode==patched code: {matches}   CRC blocks failing: {fails}")
    print(f"  rwd size 0x{len(rwd):X}  trailer csum 0x{csum:08X}")
    if not matches or fails:
        print(f"  *** {label} self-check FAILED — not writing ***\n")
        return None
    os.makedirs(v11.OUT_DIR, exist_ok=True)
    out = os.path.join(v11.OUT_DIR,
                       f"39990-TVA-A160-{label}-{tag}-0x{v11.START:X}-0x{v11.END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.relpath(out, v11.REPO)}\n")
    return out


def main():
    code = open(v11.CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(v11.TEMPLATE_T2F, "rb").read()))
    headers = v11.make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{v11.START:X},0x{v11.END:X})  "
          f"%=30 -> 0x18DA30F1\n")
    build("V12A", code, headers, tag="LKAS-gain2x-shl3+clamps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
