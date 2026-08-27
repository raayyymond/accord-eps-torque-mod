"""build_v15_tva.py — V15 LKAS 2x-torque build for the 2020 Accord (39990-TVA,A160).

LINEAGE: builds off V9 (the stock reconstruction, == code.bin window decoded by the
ECU) + THREE targeted calibration halfword edits.  V10-V13 are NOT used — every one of
them targeted a wrong model (driver-curve scale / ceiling-raise / setpoint-gain shl3 /
dual-path lockstep ceiling), all of which left the LKAS high end at stock because they
edited DOWNSTREAM of the real magnitude stage.  See project/project_accord_torque_mod_v0.md and
reference/firmware/reference_accord_lkas_window_ceiling.md / reference/tooling/reference_accord_databin_tp_base.md.

WHAT V15 EDITS — identical to V14 (arb gain x2 + clamps x2) with one change:
  All occurrences of the part-number string '39990-TVA-A160' are written as
  '39990-TVA,A160' (comma instead of hyphen between TVA and A160) in the RWD
  header.  Calibration patches and cipher are otherwise unchanged from V14.

  The EPS APPLICATION calibration base is tp = 0xBF000 (set @0x140ce in FUN_00014084),
  NOT 0xF8000 (that is only the bootloader's transient tp).  All `tp+offset` scalar cal
  therefore lives in the PROGRAMMED 0xBF000-0xC6FFF region, present in this dump and in
  the [0x13000,0x100000) window we flash.  There is no absent partition.

  In m_steer_torque_arbitration (FUN_00028ea6) the LKAS output is:
      out = clamp( (combined_torque * polarity[gp-0x6752] * GAIN[tp+0x746c]) >> 15,
                   ±CLAMP[tp+0x71b4] )                          -> gp-0x6b3c
  then m_steer_torque_limit_and_pack (FUN_0x2b422) re-clamps by CLAMP[tp+0x71b2].
  At full command the curve-pinned demand (~15360) * 891 >> 15 ~= ±418, already BELOW the
  ±512 clamps -> the GAIN (891) is what caps LKAS torque, not any downstream window/shaper
  clamp (which is why all the V11-V13 clamp/window edits were inert at the top).

  V15 = double the gain, and double the two output clamps so the doubled gain is not
  re-cut.  Three flashable cal halfword edits, NO code rewrite:
      0xC646C  GAIN tp+0x746c        891 (0x037B) -> 1782 (0x06F6)
      0xC61B4  arb clamp tp+0x71b4   512 (0x0200) -> 1024 (0x0400)
      0xC61B2  pack clamp tp+0x71b2  512 (0x0200) -> 1024 (0x0400)

  Gain x2 doubles torque at EVERY command level (incl. full 4096), so this is the
  gain lever ONLY — do NOT also stack the shl3 setpoint gain (that would be ~4x low/mid).

  All three sites fall inside ONE CRC block: #48 [0xC6000, 0xC6FFC), stored CRC @0xC6FFC.
  (The arb math is upstream; these scalars are read straight from ROM each call, no RAM
  governor mirror exists for them — contrast gp-0x4f64.)

OPEN / RESIDUAL (per feedback_rigorous_validation, no bench read available):
  * Downstream code clamps (mixer ±0x2800=10240, shaper ±0x2000=8192, FOC ±8192) are
    left STOCK.  Doubled LKAS output peaks ~836 counts (418*2) at the arb stage — far
    below those clamps — so headroom is expected; but CONFIRM via CAN 0x427 motor-torque
    telemetry that the LKAS channel is not amplified to motor-scale before those clamps.
  * Doubling plant gain without an openpilot lateral-PID/feedforward retune will oscillate
    (observed on the V12A gain build); openpilot must know it now drives ~2x torque.

MECHANICS identical to the proven V9b path: cipher v9b ((c^0xBF)^0x10)-0x9E, window
[0x13000,0x100000), raw &-key BF109E from the T2F template.  Self-validates by decoding
our own payload exactly as the ECU would, splicing into a 1 MB image, and replaying the
49-block bootloader CRC walk — require ECU-decode==patched AND 49/49 CRC PASS.

STUDY ARTIFACT.  No flash until the operator names the file + bus (kit iron rule).
"""
import os, sys, gzip, struct, zlib

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING, ANALYSIS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"   # V9 baseline (stock)
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"                       # comma/red-panda EPS target -> 0x18DA30F1

# v9b cipher ONLY (OPS: xor=0, sub=4) — the resident on-ECU decryptor (FUN_0xB35E)
V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- V15 calibration halfword edits (addr, current u16, new u16, note) -------------
# tp(app)=0xBF000, so tp+0x746c=0xC646C, tp+0x71b4=0xC61B4, tp+0x71b2=0xC61B2.
# Each current value is asserted before write (brick-safety); LE u16.
CAL_PATCHES = [
    (0xC646C, 891, 1782, "GAIN  tp+0x746c  arb Q15 output gain  891->1782 (x2)"),
    (0xC61B4, 512, 1024, "CLAMP tp+0x71b4  arb output clamp      512->1024 (x2)"),
    (0xC61B2, 512, 1024, "CLAMP tp+0x71b2  limit&pack clamp      512->1024 (x2)"),
]

# All three sites are in CRC block #48; recompute only that block.
TOUCHED_BLOCKS = [(0xC6000, 0xC6FFC)]


def patch_cal(code):
    for addr, cur, new, note in CAL_PATCHES:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} (0x{cur:04X}) "
                                 f"got {got} (0x{got:04X}) ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:5d} (0x{cur:04X}) -> {new:5d} (0x{new:04X})   {note}")


def make_tva_headers(template_info):
    new = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new.append((tag, [b"39990-TVA-A110", b"39990-TVA,A160"]))
        elif tag == b"!":
            new.append((tag, [vals[0], vals[0]]))
        elif tag == b"%":
            new.append((tag, [CAN_SIG_BYTE]))
        else:
            new.append((tag, list(vals)))
    return new


def full_image(plain_window):
    img = bytearray(b"\xff" * 0x100000)
    img[START:END] = plain_window
    return bytes(img)


def recompute_crc(code, start, crc_off):
    old = struct.unpack_from("<I", code, crc_off)[0]
    new = zlib.crc32(code[start:crc_off]) & 0xFFFFFFFF
    struct.pack_into("<I", code, crc_off, new)
    print(f"  CRC [0x{start:X},0x{crc_off:X}) @0x{crc_off:X}: 0x{old:08X} -> 0x{new:08X}")


def build(label, code_stock, headers, tag):
    print("=" * 74)
    print(f"{label}: LKAS 2x via arb gain+clamps (gain 891->1782, clamps 512->1024)"
          f"   cipher v9b")
    code = bytearray(code_stock)

    patch_cal(code)
    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    # self-validate exactly as the ECU would: decode our own payload, splice, CRC-walk
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    csum = struct.unpack("<I", rwd[-4:])[0]
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw)")
    print(f"  ECU-decode==patched code: {matches}   CRC blocks failing: {fails}")
    print(f"  rwd size 0x{len(rwd):X}  trailer csum 0x{csum:08X}")
    if not matches or fails:
        print(f"  *** {label} self-check FAILED — not writing ***\n")
        return None
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.relpath(out, REPO)}\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  %=30 -> 0x18DA30F1")
    print(f"baseline = V9 stock; edits = 3 cal halfwords (arb gain x2 + clamps x2)\n")
    build("V15A", code, headers, tag="LKAS-2x-arbgain-clamps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
