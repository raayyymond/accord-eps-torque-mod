"""V850 disassembly scaffolding for Accord EPS firmware analysis.

The V850 analog of `../analysis-c020-vs-c120/disasm_sh2a.py`. Since capstone in
this environment does NOT include V850 support, this wraps the `rizin` CLI
(`rizin 0.8.2 @ windows-x86-64` installed via scoop) and adds V850-specific
post-processing — most importantly, resolving the `movhi imm,r0,rX` +
`movea lo,rX,rY` immediate-pair idiom that builds 32-bit addresses, which
neither rizin nor Ghidra auto-resolves into xrefs (see CODE_BIN_FIRMWARE_MAP.md
§9 and §5c).

KNOWN UPSTREAM BUG (rizin 0.8.2 V850 plugin), not corrected by this script:
The plugin omits the ×2 halfword scaling for short-load instructions (`sld.hu`,
`sld.bu`, `sld.w`). The printed disp field is therefore half the true byte
displacement, and any cross-reference computed from rizin's disp output for a
short-load instruction will land at half the correct offset. The
`resolve_imm_pairs()` helper below only post-processes `movhi`-paired LONG
loads (`ld.X`, `st.X`, `movea`) and does NOT touch short loads — but if you
hand-interpret a `sld.hu disp[ep]` line from rizin output, decode the raw 2-byte
instruction against the V850E2M ISA (`rrrrr0000111dddd`: disp = `bits[3:0] × 2`)
rather than trusting the printed disp. See `V850_TOOLING.md` § "Known
disassembler quirks" and `V850_ALGORITHM_VERIFIED.md` for the full audit.

The firmware (`code.bin`) is the complete 1 MB code-flash image of a Renesas
µPD70F3508 (V850E2/Px4 core, **little-endian**), loaded flat at base `0x0`.
RAM lives at `0xFEDEC000–0xFEDFFFFF`; operands forming pointers in that range
are RAM, not flash.

Provides:
- `rz_disasm(off, n)` — disasm `n` instructions at file offset `off`, JSON
- `rz_disasm_range(start, end)` — disasm bytes in `[start, end)`, JSON list
- `disasm_function(entry)` — auto-extent disasm of a function (stops at first
  unconditional jump/return without a falling-through successor)
- `resolve_imm_pairs(insns)` — sweep a list and annotate every `movhi`/`movea`
  pair with the computed 32-bit address; also flags pointer loads
  (`ld.w lo[rX], rY`) that combine with a prior `movhi` to form a flash/RAM
  address.
- `classify_addr(addr)` — "flash" / "ram" / "data-flash" / "sfr" / "other"
- `format_lines(insns)` — pretty-printer mirroring `disasm_sh2a.format_lines`
- `KNOWN_OFFSETS` — addresses called out in CODE_BIN_FIRMWARE_MAP.md
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parents[4]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW_BIN = STOCK_FW_DUMP / "code.bin"
LOAD_BASE = 0x0
RIZIN = "rizin"  # on PATH via scoop

# Address-space ranges from CODE_BIN_FIRMWARE_MAP.md §1 (datasheet-backed).
FLASH_RANGE     = (0x00000000, 0x00100000)  # 1 MB code flash
DATA_FLASH      = (0x02000000, 0x02008000)  # 32 KB data flash
RAM_RANGE       = (0xFEDEC000, 0xFEE00000)  # 80 KB on-chip RAM
SFR_RANGE_LOW   = (0xFFFF0000, 0xFFFFFFFF)  # peripheral / SFR window (top of mem)
SFR_RANGE_HIGH  = (0xFF800000, 0xFF900000)  # secondary SFR window (DCRA at FF836020 etc.)

# Verified high-confidence addresses from CODE_BIN_FIRMWARE_MAP.md.
# Mirrors `KNOWN_TABLES` in disasm_sh2a.py — call out the landmarks.
KNOWN_OFFSETS = {
    0x000000: "reset vector table (firmware begin)",
    0x000024: "first decoded function (cluster-1 entry)",
    0x000080: "startup routine (__disable_irq, RAM init, calls 0x8000)",
    0x000238: "post-init handoff target (indirect call from 0x80)",
    0x005AF8: "string 'DV850T05xxxxxV104'",
    0x008000: "boot-invoked routine (NOP pad 0x8000-0x8007, code @ 0x8008)",
    0x009011: "string '39990-TVA-A110/A160' (Honda EPS part number)",
    0x00EF72: "end of code cluster 1",
    0x013090: "build timestamp string",
    0x014000: "vector/dispatch DATA table (NOT code; only ref is READ from 0x801c)",
    0x014810: "first function of code cluster 2 (exception handler, reads ECR)",
    0x06B8F4: "CRC engine (DCRA driver)",
    0x059616: "per-block CRC-32 trailer verifier helper",
    0x086242: "last decoded function",
    0x08B218: "end of programmed content (180 KB erased run begins)",
    0x0B7000: "diagnostic KFC_* string region",
    0x0C4000: "calibration region begins (per-block CRC-32 trailers)",
    0x0FD0B8: "last non-FF content byte (identical in A160 and A340)",
    0x0FFFF0: "top-of-flash trailer (offline flash-tool metadata)",
}

# ---------------------------------------------------------------------------
# Bytes cache + classification

_fw_bytes_cache: bytes | None = None


def fw_bytes() -> bytes:
    global _fw_bytes_cache
    if _fw_bytes_cache is None:
        _fw_bytes_cache = FW_BIN.read_bytes()
    return _fw_bytes_cache


def classify_addr(addr: int) -> str:
    if FLASH_RANGE[0] <= addr < FLASH_RANGE[1]:
        return "flash"
    if DATA_FLASH[0] <= addr < DATA_FLASH[1]:
        return "data-flash"
    if RAM_RANGE[0] <= addr < RAM_RANGE[1]:
        return "ram"
    if SFR_RANGE_LOW[0] <= addr <= SFR_RANGE_LOW[1]:
        return "sfr"
    if SFR_RANGE_HIGH[0] <= addr < SFR_RANGE_HIGH[1]:
        return "sfr"
    return "other"


# ---------------------------------------------------------------------------
# Rizin wrapper

def _rizin_cmd(cmd: str, fw: Path = FW_BIN) -> str:
    """Run a rizin command, return stdout as text. V850 LE flat-loaded at 0x0."""
    proc = subprocess.run(
        [RIZIN, "-a", "v850", "-b", "32", "-m", f"0x{LOAD_BASE:x}",
         "-N", "-qc", cmd, str(fw)],
        capture_output=True, text=True, check=False,
    )
    # rizin sometimes emits warnings on stderr; we want stdout only
    return proc.stdout


def rz_disasm(offset: int, n: int = 16, fw: Path = FW_BIN) -> list[dict]:
    """Disassemble `n` instructions starting at file offset (=load address).

    Returns rizin's `pdj` JSON list. Each entry is a dict with fields:
    offset, size, opcode (== disasm), bytes (hex), type, family, esil, jump.
    """
    out = _rizin_cmd(f"pdj {n} @ 0x{offset:x}", fw=fw)
    if not out.strip():
        return []
    return json.loads(out)


def rz_disasm_range(start: int, end: int, fw: Path = FW_BIN) -> list[dict]:
    """Disassemble all instructions in `[start, end)`. Uses `pDj <nbytes>`."""
    nbytes = end - start
    out = _rizin_cmd(f"pDj {nbytes} @ 0x{start:x}", fw=fw)
    if not out.strip():
        return []
    return json.loads(out)


# ---------------------------------------------------------------------------
# Function-extent auto-detection
#
# V850 has no fixed prologue, so we approximate: walk forward until the first
# unconditional terminator (jr / jmp / ret-like / reti / dispose+jmp) that is
# NOT followed by a known branch target within the recent window. This is
# heuristic — for high-confidence extents, anchor with Ghidra.

UNCOND_TERMINATORS = {"jr", "jmp", "reti", "ctret", "eiret", "feret"}
# `dispose` with implicit jmp in its operands (`dispose imm, list, [lp]`) is also a
# common function exit; we detect that via opcode prefix.


def disasm_function(entry: int, max_insns: int = 800, fw: Path = FW_BIN) -> list[dict]:
    """Walk forward from `entry`, stopping at the first plausible end.

    Returns list of pdj entries. Heuristic: stop after an unconditional jump or
    return-like instruction, *unless* a forward branch within the function
    body lands past it (i.e. the terminator is followed by reachable code).
    """
    # First, just bulk-disasm a generous window.
    insns = rz_disasm(entry, n=max_insns, fw=fw)
    if not insns:
        return []
    # Collect forward branch targets seen so far.
    branch_targets: set[int] = set()
    end_idx = len(insns)
    for i, ins in enumerate(insns):
        if "jump" in ins and ins["jump"] is not None:
            tgt = ins["jump"]
            if tgt > ins["offset"]:
                branch_targets.add(tgt)
        op = ins.get("opcode", "")
        mnem = op.split(" ", 1)[0] if op else ""
        is_uncond = (
            mnem in UNCOND_TERMINATORS
            or mnem == "dispose"  # often function exit with implicit jmp
        )
        if is_uncond:
            next_off = ins["offset"] + ins["size"]
            # If no recorded forward branch reaches past this terminator,
            # this is the function end.
            if not any(t > next_off for t in branch_targets):
                end_idx = i + 1
                break
    return insns[:end_idx]


# ---------------------------------------------------------------------------
# movhi/movea + movhi/ld pair resolution
#
# V850 idiom (CODE_BIN_FIRMWARE_MAP.md §9):
#   movhi imm,r0,rX    ; rX = imm << 16
#   movea lo,rX,rY     ; rY = rX + sign_ext_16(lo)        => full address
# or
#   movhi imm,r0,rX
#   ld.w/h/b lo[rX], rY ; load from (rX + sign_ext_16(lo))
# or
#   movhi imm,r0,rX
#   st.w/h/b rY, lo[rX] ; store to  (rX + sign_ext_16(lo))
#
# rizin prints the movhi as `movhi <unsigned imm>, r0, rX`. We need to:
# 1. Parse the imm, the dst register, and the displacement of the follower.
# 2. Compute (imm << 16) + sign_ext_16(disp).
# 3. Classify the result (flash/ram/sfr/other).

import re

_MOVHI_RE = re.compile(r"^movhi\s+(-?\d+|0x[0-9a-fA-F]+),\s*r0,\s*(\w+)$")
_MOVEA_RE = re.compile(r"^movea\s+(-?\d+|0x[0-9a-fA-F]+),\s*(\w+),\s*(\w+)$")
# ld/st with `disp[reg]` form. The size suffix doesn't matter for address calc.
_MEMACC_RE = re.compile(r"^(ld|st)\.(b|h|w|hu|bu)\s+"
                        r"(?:(\w+),\s*)?"          # st has src reg first
                        r"(-?\d+|0x[0-9a-fA-F]+)\[(\w+)\]"
                        r"(?:,\s*(\w+))?")          # ld has dst reg last


def _parse_int(s: str) -> int:
    s = s.strip()
    return int(s, 16) if s.lower().startswith(("0x", "-0x")) else int(s, 10)


def _sign_ext_16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def resolve_imm_pairs(insns: list[dict]) -> list[dict]:
    """Walk the instruction list, annotating movhi-pair address loads.

    Mutates each entry by adding (when applicable):
      - `resolved_addr`: int — the full 32-bit address the pair forms
      - `resolved_zone`: str — classify_addr(resolved_addr)
      - `resolved_partner`: int — offset of the partner instruction

    A `movhi` is paired with the *next* instruction touching its destination
    register that is a `movea`, `ld.*`, or `st.*` — but only within a short
    window (default 8 insns) and only if the register isn't clobbered in
    between by another write.
    """
    WINDOW = 12

    for i, ins in enumerate(insns):
        m = _MOVHI_RE.match(ins.get("opcode", "").strip())
        if not m:
            continue
        imm_hi = _parse_int(m.group(1)) & 0xFFFF
        dst_reg = m.group(2)

        # Look forward up to WINDOW for a follow-up that uses dst_reg as base.
        for j in range(i + 1, min(len(insns), i + 1 + WINDOW)):
            follow_op = insns[j].get("opcode", "").strip()

            # Check for clobber: another `movhi/mov/movea ... , dst_reg` overwriting it
            # (but NOT `movea ..., dst_reg, dst_reg` which uses-then-writes).
            mov_clobber = re.match(rf"^(movhi|mov|movea)\s+.*,\s*{dst_reg}$", follow_op)
            movea_self = re.match(rf"^movea\s+\S+,\s*{dst_reg},\s*{dst_reg}$", follow_op)
            if mov_clobber and not movea_self and j != i + 1:
                # Clobber before we find a partner: pair broken.
                # But still allow movea with dst==src on the same line (the canonical pair).
                break

            # movea lo, dst_reg, rY  (canonical address-build)
            mm = _MOVEA_RE.match(follow_op)
            if mm and mm.group(2) == dst_reg:
                lo = _sign_ext_16(_parse_int(mm.group(1)))
                addr = ((imm_hi << 16) + lo) & 0xFFFFFFFF
                ins["resolved_addr"] = addr
                ins["resolved_zone"] = classify_addr(addr)
                ins["resolved_partner"] = insns[j]["offset"]
                insns[j]["resolved_addr"] = addr
                insns[j]["resolved_zone"] = classify_addr(addr)
                insns[j]["resolved_partner"] = ins["offset"]
                break

            # ld.X disp[dst_reg], rY     OR     st.X rY, disp[dst_reg]
            mm = _MEMACC_RE.match(follow_op)
            if mm and mm.group(5) == dst_reg:
                lo = _sign_ext_16(_parse_int(mm.group(4)))
                addr = ((imm_hi << 16) + lo) & 0xFFFFFFFF
                ins["resolved_addr"] = addr
                ins["resolved_zone"] = classify_addr(addr)
                ins["resolved_partner"] = insns[j]["offset"]
                insns[j]["resolved_addr"] = addr
                insns[j]["resolved_zone"] = classify_addr(addr)
                insns[j]["resolved_partner"] = ins["offset"]
                break

    return insns


# ---------------------------------------------------------------------------
# Pretty-printing

def format_lines(insns: list[dict]) -> str:
    """Pretty-print disasm list. Mirrors disasm_sh2a.format_lines layout."""
    out = []
    for ins in insns:
        addr = ins.get("offset", 0)
        size = ins.get("size", 0)
        b = ins.get("bytes", "")[: size * 2]
        op = ins.get("opcode", ins.get("disasm", "")).strip()
        line = f"  0x{addr:06X}:  {b:<10s}  {op}"
        if "resolved_addr" in ins:
            ra = ins["resolved_addr"]
            zone = ins["resolved_zone"]
            line += f"    ; => 0x{ra:08X} [{zone}]"
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI

def _print_at(offset: int, n: int = 16, resolve: bool = True) -> None:
    insns = rz_disasm(offset, n=n)
    if resolve:
        resolve_imm_pairs(insns)
    label = KNOWN_OFFSETS.get(offset, "")
    header = f"=== 0x{offset:06X}  ({label})" if label else f"=== 0x{offset:06X}"
    print(header)
    print(format_lines(insns))
    print()


def _print_function(entry: int) -> None:
    insns = disasm_function(entry)
    resolve_imm_pairs(insns)
    label = KNOWN_OFFSETS.get(entry, "")
    header = f"=== function @ 0x{entry:06X}  ({label})" if label else f"=== function @ 0x{entry:06X}"
    print(header)
    print(f"  ({len(insns)} insns, ends at 0x{insns[-1]['offset']+insns[-1]['size']:06X})")
    print(format_lines(insns))
    print()


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        print("Usage:")
        print(f"  {sys.argv[0]} demo")
        print(f"  {sys.argv[0]} at <hex-offset> [n_insns]")
        print(f"  {sys.argv[0]} fn <hex-offset>")
        print(f"  {sys.argv[0]} range <hex-start> <hex-end>")
        return 0

    cmd = argv[1]
    if cmd == "demo":
        # Smoke test: disassemble at the four known landmark addresses
        # called out in the task brief.
        for off in (0x24, 0x80, 0x8000, 0x14810):
            _print_at(off, n=8)
        return 0
    if cmd == "at":
        off = int(argv[2], 16)
        n = int(argv[3]) if len(argv) > 3 else 16
        _print_at(off, n=n)
        return 0
    if cmd == "fn":
        off = int(argv[2], 16)
        _print_function(off)
        return 0
    if cmd == "range":
        start = int(argv[2], 16)
        end = int(argv[3], 16)
        insns = rz_disasm_range(start, end)
        resolve_imm_pairs(insns)
        print(format_lines(insns))
        return 0
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
