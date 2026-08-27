"""builds/telemetry/build_uds_telem_tva.py - UDS-over-CAN RAM telemetry for the gentle-EME (39990-TVA-A160).

*** SUPERSEDED 2026-07-10 -- DO NOT USE. This build has an off-by-one-ENTRY bug: it patches DID 0x4800's
    handler_ptr (0xB780C) instead of DID 0x4801's (0xB7820), and assumes table base 0xB7800 instead of the
    true 0xB77FC -> the cave is wired to the WRONG DID and 0x4801 reads return stale bytes (empirically dead).
    Use builds/telemetry/build_v31u_uds_telem_tva.py (correct handler_ptr @0xB7820, WORKING/FLASHED). See
    docs/handoffs/2026-07/HANDOFF-2026-07-10-v31u-uds-telemetry-working.md. ***


WHAT THIS IS (2026-07-08)
=========================================================================================================
A comma-visible RAM read of the 4 gentle-EME signals via the EPS's APPLICATION UDS stack (SID 0x22
ReadDataByIdentifier), which responds natively on CAN (req 0x18DA80F1 / resp 0x18DAF180) and crosses the
car gateway -- unlike broadcast frames (0x660 etc.), which are gateway-filtered (proven: TIER1's 0x660
rearm was invisible on-car, 2026-07-08 scan). Full design + evidence: docs/guides/SPEC-uds-can-ram-telemetry-a160.md.

STOCK BASE (minimal): this build applies ONLY the UDS telemetry patch -- no V31 cal. It isolates/validates
the new channel and reproduces the gentle-EME (gates armed at stock 320). Rebase on V31 later if you want
V31 drivability during the capture drive.

THE PATCH (2 field edits in one RDBI DID descriptor + one cave handler)
=========================================================================================================
RDBI DID descriptor table @0xB7800 (stride 0x14): index 0 = DID 0x4801, stock handler 0x0004D5C2, len 56.
We REPURPOSE it (a Honda-proprietary 0x48xx DID -- openpilot never reads UDS DIDs; only a dealer tool
would, acceptable for a study flash):
  * handler ptr  @0xB780C  0x0004D5C2 -> 0x000C4E00 (the cave)
  * declared len @0xB7812  0x0038(56) -> 0x000A(10 = 8 data + 2 DID echo, mirroring stock 0xF181=16=14+2)
  * DID @0xB7810 stays 0x4801 (unchanged) -> read `22 48 01`, get `62 48 01 <8 bytes>`.

Cave handler @0xC4E00 (492 free 0xFF bytes; app-region, inside the [0x13000,0xC4FFC) CRC block). It mirrors
the stock 0xF181 handler FUN_0004f6d6 exactly (prologue/length-store/211ba/2073a/epilogue reused verbatim),
expanding its single append into four 2-byte RAM reads:
  set *(u16*)(ctx+0xc)=0x0A; FUN_000211ba();
  FUN_0002114e(0xFEDF159E,2)  voter-MAX  (gp-0x6a62)   -> 0xC6312 (V33) decider gate signal
  FUN_0002114e(0xFEDF15A2,2)  voter-AVG  (gp-0x6a5e)   -> 0xC62FE (V35) deliver-commit gate signal
  FUN_0002114e(0xFEDF3098,2)  |col torq| (gp-0x4f68)   -> Gate-5 (0xC61EA=4096) signal
  FUN_0002114e(0xFEDF133C,2)  angle      (gp-0x6cc4)   -> angle-#1 suspect
  FUN_0002073a();
Response payload (8 bytes, little-endian u16 each): [0:2]=MAX [2:4]=AVG [4:6]=|col torq| [6:8]=angle.

HANDLER ENCODING: static instrs (prepare/movea/st.h/mov-imm32/mov-imm5/dispose) are verbatim/immediate-swap
copies of FUN_0004f6d6 (Ghidra-read this session). The 6 PC-relative jarl displacements are recomputed for
the 0xC4E00 placement using the V850E2 Format-V encoding derived + cross-checked on 3 real jarls:
  jarl disp22,lp: hw1 = 0xFF80 | (disp>>16 & 0x3F);  hw2 = disp & 0xFFFF;  disp = target - instr_addr.
The emitted image is disassembled in Ghidra to confirm (see verify step / build report).

SAFETY: STUDY ARTIFACT. Read-only DID, no SecurityAccess, default session; touches only the diagnostic
read surface (no command/torque/motor/soft-EME/engage-SM/fault code). No flash until the operator names
file + bus (kit iron rule).
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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
import os, sys, gzip, struct, zlib

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR
BIN_OUT      = plain_image_path("_uds_telem_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"
V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# ---- the RDBI-DID cave handler (V850E2, 72 bytes) ----
HANDLER = bytes.fromhex(
    "80072100"      # prepare {lp},0                (verbatim from FUN_0004f6d6)
    "207e0a00"      # movea 0x0A,r0,r15             (imm 0x10->0x0A)
    "667f0c00"      # st.h  r15,0xc[r6]             (verbatim: *(u16*)(ctx+0xc)=10)
    "b5ffaec3"      # jarl  0x000211ba,lp           (recomputed disp @0xC4E0C)
    "26069e15dffe"  # mov   0xFEDF159E,r6           (voter-MAX)
    "023a"          # mov   2,r7
    "b5ff36c3"      # jarl  0x0002114e,lp           (@0xC4E18)
    "2606a215dffe"  # mov   0xFEDF15A2,r6           (voter-AVG)
    "023a"          # mov   2,r7
    "b5ff2ac3"      # jarl  0x0002114e,lp           (@0xC4E24)
    "26069830dffe"  # mov   0xFEDF3098,r6           (|column torque|)
    "023a"          # mov   2,r7
    "b5ff1ec3"      # jarl  0x0002114e,lp           (@0xC4E30)
    "26063c13dffe"  # mov   0xFEDF133C,r6           (angle)
    "023a"          # mov   2,r7
    "b5ff12c3"      # jarl  0x0002114e,lp           (@0xC4E3C)
    "b5fffab8"      # jarl  0x0002073a,lp           (@0xC4E40)
    "40063f00"      # dispose 0x0,{lp},[lp]         (verbatim: restore lp + jmp[lp])
)
assert len(HANDLER) == 72, len(HANDLER)
CAVE = 0x0C4E00

# ---- edits ----
CODE_PATCHES = [
    (0xB780C, bytes.fromhex("c2d50400"), struct.pack("<I", CAVE),
     "DID 0x4801 (idx0) handler ptr 0x0004D5C2 -> 0x000C4E00 (cave)"),
    (0xB7812, bytes.fromhex("3800"),     struct.pack("<H", 0x000A),
     "DID 0x4801 declared length 56 -> 10 (=8 data + 2 DID echo)"),
    (CAVE,    b"\xff" * 72,              HANDLER,
     "telemetry DID handler (reads 4 RAM signals, appends 8 bytes)"),
]
# stock-identity guards (prove we hit the right entry)
DID_ENTRY_STOCK = (0xB7800, bytes.fromhex("df0000000f00000000000000c2d5040001483800"),
                   "RDBI DID entry 0 (0x4801) stock")
DID_GUARD = [
    (0xB7810, bytes.fromhex("0148"), "DID id 0x4801 stays unchanged"),
]


def patch_code(code, table):
    for addr, old, new, note in table:
        assert len(old) == len(new), f"len mismatch @0x{addr:05X}"
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(f"CODE 0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}: {old.hex()} -> {new.hex()}   {note}")


def guard_bytes(code, table):
    for addr, expect, note in table:
        got = bytes(code[addr:addr + len(expect)])
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect.hex()} got {got.hex()} ({note})")


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


# both edits (0xB7800 table + 0xC4E00 cave) live in this one CRC block:
TOUCHED_BLOCKS = [(0x13000, 0xC4FFC)]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: STOCK base + UDS-over-CAN RAM telemetry (repurpose DID 0x4801)")
    code = bytearray(code_stock)

    # pre-patch guards
    guard_bytes(code, [DID_ENTRY_STOCK])
    assert bytes(code[CAVE:CAVE + 72]) == b"\xff" * 72, "cave not empty (expected 72x 0xFF)"

    print("  --- UDS telemetry patch ---")
    patch_code(code, CODE_PATCHES)

    # post-patch guards
    guard_bytes(code, DID_GUARD)
    assert bytes(code[CAVE + 72:CAVE + 96]) == b"\xff" * 24, "cave tail must stay 0xFF"

    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

    # readback asserts (decode the emitted .rwd from scratch)
    assert bytes(ecu_plain[0xB780C - START:0xB7810 - START]) == struct.pack("<I", CAVE), "handler ptr lost"
    assert struct.unpack_from("<H", ecu_plain, 0xB7812 - START)[0] == 0x000A, "declared len lost"
    assert bytes(ecu_plain[0xB7810 - START:0xB7812 - START]) == bytes.fromhex("0148"), "DID id changed"
    assert bytes(ecu_plain[CAVE - START:CAVE - START + 72]) == HANDLER, "cave handler lost"
    assert bytes(ecu_plain[CAVE - START + 72:CAVE - START + 96]) == b"\xff" * 24, "cave tail not 0xFF"

    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, b in runs:
        print(f"     0x{a:05X}-0x{b:05X} ({b - a + 1}B)")

    if not matches or fails:
        print(f"  *** {label} self-check FAILED -- not writing ***\n")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    with open(BIN_OUT, "wb") as f:
        f.write(full_image(ecu_plain))
    print(f"  WROTE {os.path.relpath(out, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)} (1MB plain image for Ghidra verify)\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock)")
    print("UDS = STOCK + repurpose RDBI DID 0x4801 -> cave handler reading 4 gentle-EME RAM signals")
    print("      read `22 48 01` on 0x18DA80F1 -> `62 48 01 <MAX AVG |torq| angle>` (LE u16 each)\n")
    build("UDStelem", code, headers, tag="DID4801-RAMread")
    return 0


if __name__ == "__main__":
    sys.exit(main())
