"""Scan V850 code clusters for movhi-pair address loads that resolve into the
calibration/torque-table region (0xC4000-0xFD0B9). Each such site is code that
reads a calibration table -> candidate LKAS/assist torque-command code path.

Uses radare2 (v850) linear sweep + movhi/(movea|ld|st) pair resolution.
Standalone (does not import disasm_v850, which expects rizin field names).
"""
import json, re, subprocess, sys
from pathlib import Path

R2 = r"C:\Users\dudei\Desktop\Projects\radare2-6.1.4-w64\bin\radare2.exe"
ANALYSIS_DIR = Path(__file__).resolve().parents[1]
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))
from firmware_paths import STOCK_FW_DUMP

FW = STOCK_FW_DUMP / "code.bin"

# Calibration / torque-table region (ACCORD_TVA_ARCHITECTURE_MAP.md §1, §4)
CAL_LO, CAL_HI = 0xC4000, 0xFD0B9
# Code clusters to sweep (skip 0xEF72-0x14810: strings + 0x14000 data table)
SCAN_RANGES = [(0x0024, 0xEF72), (0x14810, 0x86242)]
CHUNK = 0x10000

# Named candidate tables from the architecture map §4.4 for hit-attribution
CANDIDATES = {
    0xC52CA: "C5000 paired-curve block (8 curves)",
    0xCE0B2: "CE000 assist-curve family",
    0xCF0B2: "CF000 assist-curve family (mirror)",
}

_MOVHI = re.compile(r"^movhi\s+(-?\d+|0x[0-9a-fA-F]+),\s*r0,\s*(\w+)$")
_MOVEA = re.compile(r"^movea\s+(-?\d+|0x[0-9a-fA-F]+),\s*(\w+),\s*(\w+)$")
_MEM   = re.compile(r"^(ld|st)\.(?:b|h|w|hu|bu)\s+"
                    r"(?:\w+,\s*)?(-?\d+|0x[0-9a-fA-F]+)\[(\w+)\]")

def pint(s):
    s = s.strip()
    return int(s, 16) if s.lower().startswith(("0x", "-0x")) else int(s, 10)

def sx16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v

def r2_pDj(start, nbytes):
    out = subprocess.run(
        [R2, "-a", "v850", "-b", "32", "-m", "0x0", "-N", "-qc",
         f"pDj {nbytes} @ 0x{start:x}", str(FW)],
        capture_output=True, text=True, check=False).stdout
    out = out.strip()
    if not out:
        return []
    # radare2 occasionally prefixes a stray line; grab the JSON array
    i = out.find("[")
    return json.loads(out[i:]) if i >= 0 else []

def resolve(insns):
    """Yield (movhi_addr, partner_addr, resolved_addr, movhi_op, partner_op)."""
    WIN = 12
    hits = []
    for i, ins in enumerate(insns):
        op = ins.get("opcode", "").strip()
        m = _MOVHI.match(op)
        if not m:
            continue
        hi = pint(m.group(1)) & 0xFFFF
        dst = m.group(2)
        for j in range(i + 1, min(len(insns), i + 1 + WIN)):
            fop = insns[j].get("opcode", "").strip()
            # clobber check (skip the canonical movea dst,dst self-use)
            if re.match(rf"^(movhi|mov|movea)\s+.*,\s*{dst}$", fop) \
               and not re.match(rf"^movea\s+\S+,\s*{dst},\s*{dst}$", fop) \
               and j != i + 1:
                break
            mm = _MOVEA.match(fop)
            if mm and mm.group(2) == dst:
                addr = ((hi << 16) + sx16(pint(mm.group(1)))) & 0xFFFFFFFF
                hits.append((ins["addr"], insns[j]["addr"], addr, op, fop)); break
            mm = _MEM.match(fop)
            if mm and mm.group(3) == dst:
                addr = ((hi << 16) + sx16(pint(mm.group(2)))) & 0xFFFFFFFF
                hits.append((ins["addr"], insns[j]["addr"], addr, op, fop)); break
    return hits

def main():
    all_hits = []
    for lo, hi in SCAN_RANGES:
        off = lo
        while off < hi:
            n = min(CHUNK, hi - off)
            insns = r2_pDj(off, n)
            for h in resolve(insns):
                if CAL_LO <= h[2] <= CAL_HI:
                    all_hits.append(h)
            off += n
            print(f"  swept 0x{off:06X}/0x{hi:06X}  (cal-hits so far: {len(all_hits)})",
                  file=sys.stderr)

    # dedupe by (movhi_addr, resolved_addr)
    seen, uniq = set(), []
    for h in all_hits:
        k = (h[0], h[2])
        if k not in seen:
            seen.add(k); uniq.append(h)
    uniq.sort(key=lambda h: h[2])

    print(f"\n=== {len(uniq)} unique code sites loading calibration-region addresses ===\n")
    for mh, pa, addr, mop, pop in uniq:
        tag = ""
        for cb, name in CANDIDATES.items():
            if abs(addr - cb) <= 0x200:
                tag = f"  <== near {name} (0x{cb:05X})"
        print(f"code 0x{mh:06X}/0x{pa:06X} -> table 0x{addr:06X}{tag}")
        print(f"      {mop}  |  {pop}")

    # histogram of which 4KB cal pages are referenced
    from collections import Counter
    pages = Counter((h[2] >> 12) << 12 for h in uniq)
    print("\n=== referenced calibration pages (4KB granularity) ===")
    for pg in sorted(pages):
        print(f"  0x{pg:06X}: {pages[pg]} ref(s)")

if __name__ == "__main__":
    main()
