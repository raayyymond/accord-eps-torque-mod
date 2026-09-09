# -*- coding: utf-8 -*-
"""ADVERSARY C -- V289 rev 1 -- ASSERTION CENSUS of build_v289_tva.py's dry-run log.

Usage:  python adv_v289_c_census.py <path to a captured --full dry-run log>

Re-classifies EVERY `[PASS] [k]` line with my own rules and prints every check whose class I move,
plus the totals.  Buckets:
  S   substantive about the BUILT BYTES or the toolchain (could fail on a bad image / bad encoder)
  D   substantive about DESIGN CONSTANTS only (arithmetic on module constants; catches a typo in a
      constant but never looks at the image)
  E   entailed by a sibling assertion in the same run
  V   entailed by the base sha256 (re-verifies a recorded constant of the base)
  T   tautological: readback of a write just made, a constant compared with itself, or a
      set-theoretic identity that holds for ANY inputs
"""
import re
import sys

log = open(sys.argv[1], encoding="utf-8", errors="replace").read().split("\n")
sec = None
rows = []
for line in log:
    m = re.match(r"\s+\[(\d+[a-z]?)\]", line)
    if m:
        sec = m.group(1)
    m = re.search(r"\[(PASS|FAIL)\] \[([SVTE])\] (.*)", line)
    if m:
        rows.append((sec, m.group(2), m.group(3).strip()))

# ordered rules: (section or None, regex on message, my class, reason)
RULES = [
    # [1] base
    ("1", r"^V282 base sha256", "S", "input identity"),
    # [1c]/[1d]/[1e] toolchain positive controls
    ("1c", r".", "S", "encoder vs flown bytes"),
    ("1d", r"byte-identically|stock owns|bits 5 and 7 are the CAVE", "S", "encoder / bit ownership"),
    ("1e", r".", "S", "decoder vs Ghidra"),
    # [2] GATE 1 census (first-time derivations from the base image; a hit kills the build)
    ("2", r".", "S", "RAM census"),
    ("2a", r".", "S", "RAM census"),
    ("2b", r".", "S", "RAM census"),
    ("2c", r".", "S", "branch census"),
    # [3] fb pole: constants-only arithmetic
    ("3", r"tp\+0x73e8/ea == 0xC63E8/EA", "T", "constant == constant (TP_BASE + 0x73E8)"),
    ("3", r"fits the signed load", "D", "range check on constants"),
    ("3", r"DC gain 2b/\(1024-a\)", "D", "constants"),
    ("3", r"^pole .* Hz -> ", "D", "constants"),
    ("3", r"fb filter headroom", "D", "constants"),
    ("3", r"fb-pole phase change", "D", "constants"),
    # [4] notch analytics on the constants
    ("4", r"DC gain EXACTLY 1|Nyquist gain EXACTLY 1|b0 == b2|poles complex|realised centre|realised Q|^\|H\(|^phase .* deg at 3.9|LINEAR WORST CASE|linear worst case = |every product is inside int32",
     "D", "coefficient arithmetic, never reads the image"),
    ("4a", r"bytes == mirror", "S", "emulator on the emitted bytes"),
    ("4a", r"executes <= 60 instructions", "S", "emulator"),
    ("4a", r"impulse 15360|^DC X=|CONTROL: plain TDF-II|zero input from state|^step 0->|l1 worst-case input|20 Hz rail square|chirp: no wrap|random full-scale|integer mirror: \|H",
     "D", "MIRROR-only (a Python function of the constants); reaches the bytes only through [4a]"),
    ("4a", r"FLAG halfword only ever|boundary \|n\| == \|y\||x = -3 from rest|^tail: FLAG", "S", "emulator on the emitted bytes"),
    ("4a", r"INIT_ON_SENTINEL=True would prepend", "D", "length-only check of an unshipped path; NOT a behavioural unit test"),
    ("4a", r"INIT_ON_SENTINEL is FALSE", "T", "a source constant compared with a literal (script says V)"),
    ("4c", r".", "S", "source-vs-layout drift guard"),
    ("4d", r".", "S", "docstring guard (text, can fail)"),
    # [5]
    ("5", r"is inside the free run and all-0xFF", "S", "layout vs base"),
    ("5", r"do not overlap|bytes still free", "D", "constants/lengths"),
    ("5", r"^jr @", "S", "decoder on the emitted jr"),
    # [6]
    ("6", r"same-length hook swap", "T", "len(4-byte constant) == 4"),
    ("6", r"every existing 0x14A rung byte-identical", "E", "region disjoint from all writes -> entailed by [7] stray == 0"),
    ("6", r"relocated epilogue is byte-identical|penultimate instruction IS the displaced", "S", "emitted bytes vs Honda's"),
    # [7]
    ("7", r"^no byte outside the written regions", "S", "the one real check"),
    # [8]
    ("8", r"exactly TWO CRC blocks|no edit lands ON the trailer", "S", "block ownership"),
    ("8", r"CRC moved 0x", "S", "weak but falsifiable"),
    ("8", r"built image CRC chain 50/50|built image BOOTLOADER CRC replay 49/49", "E",
     "entailed by base 50/50 [V] + stray == 0 + the two recomputed trailers [T]; nothing else changed"),
    # [9]
    ("9", r"every one of the .* differing bytes lies in the eight expected regions", "E", "entailed by [7] stray == 0 (allowed == attributed)"),
    ("9", r"^diff run .* attributable", "E", "entailed by the previous line"),
    # [9b]
    ("9b", r"V281 rev 3 image sha256 matches", "S", "input identity"),
    ("9b", r"V289 vs V281 rev 3", "T", "set-theoretic identity true for ANY three byte strings"),
    # [10]
    ("10", r"V38 source .rwd sha256", "S", "input identity"),
    ("10", r"decoded .rwd is byte-identical", "S", "library round trip (bijection + chunker)"),
    ("10", r"readback CRC 50/50", "E", "entailed by dec == code and [8]"),
    ("10", r"cipher table validated NON-circularly", "S", "cipher vs known plain"),
    # [11] dec arm entailed by [10] dec == code
    ("11", r"^dec :", "E", "entailed by [10] `dec == code`"),
    ("11", r"^code:.*(0xC63E8 = 875|== \d+$|live Kp record)", "T", "readback"),
    ("11", r"^code:", "S", "decoder / emulator on the FINAL image"),
    # [12]
    ("12", r".", "S", "second encoder (shares constants + FF.crc_block_map)"),
]


def classify(sec, kind, msg):
    for s, rx, cls, why in RULES:
        if (s is None or s == sec) and re.search(rx, msg):
            return cls, why
    # defaults: trust the script's own V/T/E labels; anything else S
    if kind in ("V", "T", "E"):
        return kind, "script's label kept"
    return "S", "script's label kept (no rule)"


tot_script = {}
tot_mine = {}
moves = []
for sec, kind, msg in rows:
    cls, why = classify(sec, kind, msg)
    tot_script[kind] = tot_script.get(kind, 0) + 1
    tot_mine[cls] = tot_mine.get(cls, 0) + 1
    if cls != kind:
        moves.append((sec, kind, cls, why, msg))

print(f"{len(rows)} assertions in the log")
print("script's buckets :", dict(sorted(tot_script.items())))
print("my buckets       :", dict(sorted(tot_mine.items())))
print()
print("MOVES (script label -> mine):")
by = {}
for sec, k, c, why, msg in moves:
    by.setdefault((sec, k, c, why), []).append(msg)
for (sec, k, c, why), msgs in by.items():
    print(f"  [{sec}] {k} -> {c}  x{len(msgs):<3} {why}")
    for m in msgs[:3]:
        print(f"        . {m[:130]}")
    if len(msgs) > 3:
        print(f"        . ... {len(msgs) - 3} more")
sm = sum(1 for _, k, _ in rows if k == "S")
print()
print(f"script says {sm} substantive; I count {tot_mine.get('S', 0)} S (image/toolchain) + {tot_mine.get('D', 0)} D (design constants)"
      f" = {tot_mine.get('S', 0) + tot_mine.get('D', 0)}; moved OUT of S entirely: "
      f"{sum(1 for _, k, c, _, _ in moves if k == 'S' and c in ('E', 'T', 'V'))}")
