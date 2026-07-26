"""build_v13_tva.py — V13A LKAS-torque build for the 2020 Accord (39990-TVA-A160).

GOAL: ~2x LKAS torque across the FULL comma command range [0,4096), including the
high end where V12A still delivered stock (~8192).

WHY V11A/V12A LEFT THE TOP AT STOCK — the real reason (Ghidra, full decompile of
FUN_00042af8 + FUN_00043e44, 2026-05-26):
  The LKAS torque demand is computed TWICE and cross-checked in LOCKSTEP:
    * INTEGER path  : shaper FUN_00042af8 -> demand gp-0x6b98 (0xFEDF1468)
    * FLOATING path : FUN_00043e44       -> shadow gp-0x6dbc
  A redundancy monitor (present in BOTH functions) requires |shadow*1024 - demand|
  <= ~5 counts; outside that band it sets fault bit 0x20, summed with 6 sibling bits
  into an accumulator that trips FUN_0004613e(0x38c7,..)/FUN_000462e6(0x3f1b,..) past
  0x80/128.0.  The ~8192 ceiling lives IDENTICALLY in both pipelines:
    INT  : clamp(cmd, +/-*(gp-0x4f64))            then clamp(+/-0x2000)
    FLOAT: clamp(accum, +/-(gp-0x4f64)/1024<=10)  then clamp(+/-8.0)   (8.0*1024=8192)
  They were co-designed to agree at 8192.  V11A/V12A raised only the INT *(gp-0x2000)
  static clamp -> the int gp-0x4f64 clamp still bound at ~8192 AND the float shadow
  still capped at 8.0, so the locked-together pair never moved.  (This is NOT a motor
  thermal limit -- the motor sources far more current for driver assist.  See
  reference_accord_lkas_window_ceiling.md, which retracts the earlier thermal claim.)

WHAT V13 DOES — raise the ceiling in BOTH pipelines in lockstep so the monitor still
sees agreement at the new ~2x ceiling (0x3FFF int  <->  ~15.999*1024 = 16383 float):

  Inherited unchanged:
    * V11A clamp recipe  (build_v11_tva.patch_code + patch_arb): input window-check
      +/-0x3FFF, distributor/mixer/gate, shaper static clamp +/-0x4000, arb table 0x4000.
    * V12A setpoint gain (build_v12_tva.patch_gain): shl 0x2 -> shl 0x3 @0x526d2 (2x slope).

  NEW in V13 — the lockstep ceiling edits (2 int + 4 float), all imm/opcode-level,
  each asserts its current 4 bytes first (brick-safety):
    INT path (FUN_00042af8):
      0x43ae4  ld.hu -0x4f64,gp,r10   -> movea 0x3FFF,r0,r10   force limit value = 0x3FFF
      0x43af6  addi  -0x2801,r10,r0   -> addi  -0x4000,r10,r0   widen its window-check so 0x3FFF passes
    FLOAT path (FUN_00043e44) — mirror the same ceiling so the shadow tracks:
      0x4486e  ld.hu -0x4f64,gp,r12   -> movea 0x3FFF,r0,r12   force float limit = 0x3FFF (/1024=15.999)
      0x4487e  movhi 0x4120,r0,r9     -> movhi 0x4180,r0,r9     raise the <=10.0 cap to <=16.0
      0x448c2  movhi 0x4100,r0,r14    -> movhi 0x4180,r0,r14    +8.0  final clamp -> +16.0
      0x448ce  movhi -0x3f00,r0,r11   -> movhi -0x3e80,r0,r11   -8.0  final clamp -> -16.0

  Result: INT demand max = 0x3FFF (16383); FLOAT shadow max = 15.999*1024 = 16383.
  |16383 - 16383| = 0  -> the 0x20 redundancy bit stays clear at the new ceiling.
  The other 6 monitor bits compare pre-final-clamp intermediates these edits do not
  touch, so they are unaffected.  We force the LOADS (not the gp-0x4f64 cell), so the
  governor's value and the 3 other readers (FUN_0004503c/0006e09a/0006e140) still see
  the real limit and behave stock.

RESIDUAL RISK (cannot be closed without bench/emulation; no bench read available):
  * The int and float paths must also agree within +/-5 counts in the 8192->16383
    region that was previously MASKED by the 8192 saturation.  float-vs-int rounding
    there is unverified.  If they diverge >5 counts, the monitor faults at high command
    (LKAS would cut out / log a DTC).  Road-testable, recoverable.
  * FUN_0006e09a/0006e140 can also write gp-0x6b98 (limit*cal) under non-nominal
    conditions; those use the real gp-0x4f64 (~8192) and would disagree with the shadow.
    Believed gated to fault/init modes, not steady-state LKAS. Unverified.
  * Doubling plant gain (V12A) oscillates without an openpilot lateral-PID retune
    (operator already observed/accepted this at low end).

All other mechanics are identical to V11A/V12A: cipher v9b ((c^0xBF)^0x10)-0x9E, window
[0x13000,0x100000), raw &-key BF109E, self-validate by decoding our own payload as the
ECU would, splicing, replaying the 49-block bootloader CRC walk; require 49/49 PASS +
full byte-diff = V11A sites + V12A gain byte + these 6 lockstep bytes.  All 6 new sites
are in the main CRC block [0x13000,0xC4FFC), covered by v11.TOUCHED_BLOCKS.

STUDY ARTIFACT.  No flash until the operator names the file + bus (kit iron rule).
"""
import os, sys, gzip, struct

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DIR = os.path.dirname(HERE)
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_v11_tva as v11   # verified clamp recipe + cipher/CRC/header machinery
import build_v12_tva as v12   # verified setpoint-gain (shl 0x2 -> shl 0x3)
from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31

# --- V13 lockstep ceiling edits: (addr, current 4 bytes hex, new 4 bytes hex, note) ---
# Each is a full 4-byte replace; current bytes asserted before write (brick-safety).
# movea encodings verified against the in-image movea at 0x43b12/0x43b1c.
# movhi edits change only the imm16 (high half of the float constant); opcode/regs kept.
LOCKSTEP_PATCHES = [
    # INTEGER path — shaper FUN_00042af8 gp-0x4f64 clamp
    (0x43ae4, "e4579db0", "2056ff3f",
     "INT  ld.hu -0x4f64,gp,r10 -> movea 0x3FFF,r0,r10  (force int limit value = 0x3FFF)"),
    (0x43af6, "0a06ffd7", "0a0600c0",
     "INT  addi -0x2801,r10,r0  -> addi -0x4000,r10,r0   (widen limit window-check, pass 0x3FFF)"),
    # FLOAT path — shadow recompute FUN_00043e44, mirror the same ceiling
    (0x4486e, "e4679db0", "2066ff3f",
     "FLT  ld.hu -0x4f64,gp,r12 -> movea 0x3FFF,r0,r12  (force float limit = 0x3FFF -> /1024=15.999)"),
    (0x4487e, "404e2041", "404e8041",
     "FLT  movhi 0x4120,r0,r9   -> movhi 0x4180,r0,r9    (raise limit cap 10.0 -> 16.0)"),
    (0x448c2, "40760041", "40768041",
     "FLT  movhi 0x4100,r0,r14  -> movhi 0x4180,r0,r14   (+8.0 final clamp -> +16.0)"),
    (0x448ce, "405e00c1", "405e80c1",
     "FLT  movhi -0x3f00,r0,r11 -> movhi -0x3e80,r0,r11  (-8.0 final clamp -> -16.0)"),
]


def patch_lockstep(code):
    for addr, cur_hex, new_hex, note in LOCKSTEP_PATCHES:
        cur = bytes.fromhex(cur_hex)
        new = bytes.fromhex(new_hex)
        got = bytes(code[addr:addr + 4])
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur.hex().upper()} "
                                 f"got {got.hex().upper()} ({note})")
        code[addr:addr + 4] = new
        print(f"  0x{addr:05X}: {cur_hex.upper()} -> {new_hex.upper()}   {note}")


def build(label, code_stock, headers, tag):
    print("=" * 74)
    print(f"{label}: V11A clamps + V12A gain (shl3) + LOCKSTEP ceiling raise "
          f"(int 0x3FFF <-> float 16383)   cipher v9b")
    code = bytearray(code_stock)

    v11.patch_code(code)          # distributor / mixer / gate / shaper-in / shaper-final
    v11.patch_arb(code)           # arb setpoint-limit table 15360 -> 16384
    v12.patch_gain(code)          # setpoint gain shl 0x2 -> shl 0x3 (2x slope)
    patch_lockstep(code)          # NEW: raise the gp-0x4f64 clamp in BOTH int + float paths
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
    build("V13A", code, headers, tag="LKAS-gain2x-lockstep-ceiling16383")
    return 0


if __name__ == "__main__":
    sys.exit(main())
