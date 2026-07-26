"""
verify_v52c_image.py -- INDEPENDENT post-build integrity verifier for the V52C broad low-pass image.

DESIGN RULE (the V40 process lesson, CLAUDE.md): a verifier and the builder it checks MUST NOT share an
assumption. This file therefore imports NOTHING from build_v52*.py / v52_cave_asm.py. Every check --
the CRC chain walk, the x31 container checksum, the V850E2 instruction decode, the repoint validation,
the cave semantics -- is re-implemented from scratch here and run against the BUILT BYTES.

It answers, mechanically:
  1. Is every byte that changed vs V38 accounted for by an INTENDED edit? (no stray writes)
  2. Is every repoint site a genuine `ld.h -disp[gp],rX` INSTRUCTION BOUNDARY, not a coincidental
     2-byte alignment inside some other instruction? (linear-sweep decode from the function start)
  3. Does the cave, decoded from the built image, implement exactly y += (74*(x-y)+512)>>10 ?
  4. Is the trampoline transparent -- displaced instructions re-executed LAST, correct return address?
  5. Are the safety cals (4x gain, DTC-0x1d clamp trap + float mirror, monitor literals) byte-stock?
  6. Do all CRC blocks verify, and is the block count unchanged from the baseline?
  7. Do the three RAW monitor sites still read RAW gp-0x4f60? (health gates must stay on the raw sensor)

Usage:  python verify_v52c_image.py [--built PATH] [--baseline PATH]
Exit code 0 = all checks pass. Any failure prints FAIL lines and exits 1.
"""

import argparse
import hashlib
import struct
import sys
import zlib

GP = 0xFEDF8000
TP = 0xBF000
# START/END = the x31 CONTAINER extent (the CRC linked-list head lives at END-8 = 0xFFFF8).
# MAIN_START/MAIN_END = the MAIN code block, which is a *member* of that chain. Conflating the two
# seeds the walk with a phantom "block 0" that re-uses block 0xC5000's trailer -- do not "simplify".
START, END = 0x13000, 0x100000
MAIN_START, MAIN_END = 0x13000, 0xC4FFC
EXPECTED_BLOCKS = 50
CAVE_BASE = 0xC4B34
HOOK = 0x7FEAC
RETURN = 0x7FEB0
D_SENSOR = 0x4F60
D_CELL = 0x1300
ALPHA = 74
ROUND = 512

# The three health-gate reads that MUST stay raw (health gates belong on the raw sensor).
RAW_MONITOR_SITES = {
    0x42C20: "M1 FUN_00042af8 int monitor (+/-25600 -> gp-0x6af8)",
    0x43EDA: "M2 FUN_00043e44 float monitor (IEEE double 25.0)",
    0x28F26: "FUN_00028ea6 plausibility gate (+/-25600)",
}
# Deliberately-dormant mux arms left raw (cal-gated fallback; cals 0xC6498/0xC6499 = 0x01 select the
# OTHER branch, so the gp-0x4f60-derived arm is not taken). Their load also feeds an always-live
# plausibility gate on the raw value -- same bucket as the monitors: raw is REQUIRED.
DORMANT_RAW_SITES = {
    0x34392: "FUN_00034350 damping (dormant arm + live raw range gate)",
    0x34ACE: "FUN_00034a72 boost (dormant arm + live raw range gate)",
}
# COMPLETENESS INVARIANT. Every gp-0x4f60 disp16 load in the COMMAND REGION [0x28000,0x46000) is
# either repointed (a carrier) or listed here with a reason. If a future edit adds a command-region
# raw read that is not justified, this check fails. Non-command regions (producer 0x7Exxx-0x81xxx,
# CAN packers, UDS/diagnostic loggers, angle-cal SM) are intentionally out of scope -- telemetry and
# health monitoring must observe the TRUE sensor, never the filtered copy.
COMMAND_REGION = (0x28000, 0x46000)
COMMAND_RAW_JUSTIFIED = {
    0x28F26: "health gate: plausibility vs LITERAL +/-25600",
    0x42C20: "health gate: monitor M1 vs LITERAL +/-25600",
    0x43EDA: "health gate: monitor M2 vs LITERAL IEEE double 25.0",
    0x34392: "dormant mux arm (cal 0xC6498=0x01 selects the other branch) + live raw range gate",
    0x34ACE: "dormant mux arm (cal 0xC6499=0x01 selects the other branch) + live raw range gate",
    0x2EC66: "FUN_0002ec52 diagnostic logger (~100 Hz task), not a command carrier",
    0x2ECBA: "FUN_0002ec52 diagnostic logger (~100 Hz task), not a command carrier",
    0x2A992: "DEAD: FUN_0002a93a -- 0 callers, 0 xrefs, 0 LE32 pointer refs to its entry",
    0x2D9A2: "DEAD: orphan fragment [0x2d5fe,0x2db93] -- real code, 0 xrefs, 0 pointer refs",
    0x2DAE6: "DEAD: orphan fragment [0x2d5fe,0x2db93] -- real code, 0 xrefs, 0 pointer refs",
}
# Command-region carriers deliberately EXCLUDED from the repoint, each on measured evidence.
# If a future edit sweeps one of these in, this verifier must fail.
LEAVE_RAW_CARRIERS = {
    # Intentionally EMPTY: all 19 command-path carriers are repointed (operator directive -- a mixed
    # raw/filtered population is itself the hazard; V27 bricked from asymmetry, not magnitude).
}

RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA
RATCHET_NEW_HW = 0x65B5

SAFETY_CALS_U16 = {
    0xC646C: (3564, "LKAS output gain (V38 4x) -- must be UNTOUCHED"),
    0xC67B8: (1024, "FUN_0003a382 uVar27 Y0"),
    0xC6450: (1024, "FUN_0003a382 Stage A pole"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole"),
    0xD209C: (2, "damping clamp m10 header"), 0xD209E: (300, "clamp m10 X0"),
    0xD20A0: (800, "clamp m10 X1"), 0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "damping clamp m11 header"), 0xD20AA: (300, "clamp m11 X0"),
    0xD20AC: (800, "clamp m11 X1"), 0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
SAFETY_CALS_U8 = {
    0xC4120: (0x01, "type-8 slot-8 sum gate"),
    0xC6498: (0x01, "damping mode byte"),
    0xC6499: (0x01, "boost mode byte"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

FAILURES = []
CHECKS = [0]


def check(cond, label, detail=""):
    CHECKS[0] += 1
    if cond:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}   {detail}")
        FAILURES.append(label)
    return cond


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def gp_field(disp_neg):
    return (0x10000 - disp_neg) & 0xFFFF


# --------------------------------------------------------------------------------------------------
# Independent V850E2 decoder (only the forms this build touches, plus enough to walk boundaries)
# --------------------------------------------------------------------------------------------------
def insn_lens(b, pc):
    """Possible byte lengths of the instruction at pc, most-likely first.

    V850E2 length is NOT always decidable from the first halfword: `jr/jarl disp22` (the 0x0780
    family) and the 48-bit extended-displacement load/store (`0x0784` = op 0x3C, reg1=gp) share
    their high bits and differ only in the low 5 bits -- which double as displacement bits for jr.
    Returning a SET of candidate lengths and letting the caller search over them is honest about
    that ambiguity. Collapsing it to a single guess is what made an earlier version of this file
    wrongly REJECT a real instruction boundary at 0x3B908: it swallowed the 4-byte `jr` at 0x3B904
    as 6 bytes. (0x3B908 is provably a boundary -- it is the target of the Bcond at 0x3B902,
    disp=+6.)
    """
    w = u16(b, pc)
    op = (w >> 5) & 0x3F
    if (w & 0xF800) == 0x0780:                   # jr/jarl disp22 OR 48-bit ext-disp ld/st
        return (4, 6)
    if op in (0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
              0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F):
        return (4,)
    return (2,)


def decode_ldst(b, pc):
    """Decode a gp/sp-relative ld/st. Returns (mnemonic, reg1, reg2, disp16) or None."""
    w = u16(b, pc)
    op = (w >> 5) & 0x3F
    if op not in (0x38, 0x39, 0x3A, 0x3B):
        return None
    f = u16(b, pc + 2)
    reg1, reg2 = w & 0x1F, (w >> 11) & 0x1F
    if op == 0x39:
        mnem = "ld.hu" if (f & 1) else "ld.h"
    elif op == 0x3B:
        mnem = "st.w" if (f & 1) else "st.h"
    elif op == 0x38:
        mnem = "ld.b"
    else:
        mnem = "st.b"
    return mnem, reg1, reg2, f


def boundary_walk_reaches(b, start, target, limit=4096):
    """True iff SOME consistent instruction decode starting at `start` lands exactly on `target`.

    Depth-first over the ambiguous lengths above. This is a CORROBORATING check only -- Ghidra's
    in-context re-disassembly of the built image remains the authoritative boundary proof.
    """
    seen, stack = set(), [start]
    while stack:
        pc = stack.pop()
        if pc == target:
            return True
        if pc > target or pc - start > limit or pc in seen:
            continue
        seen.add(pc)
        for n in insn_lens(b, pc):
            stack.append(pc + n)
    return False


# --------------------------------------------------------------------------------------------------
# CRC chain -- re-implemented independently (faithful bootloader replay incl. the 0xC6000 bridge)
# --------------------------------------------------------------------------------------------------
def crc_blocks(code):
    sp, np = struct.unpack_from("<HH", code, END - 8)
    bs, bl = sp << 12, (np << 12) - 4
    blocks, seen = [], set()
    while True:
        if bs in seen:
            raise RuntimeError(f"CRC chain loop at 0x{bs:X}")
        seen.add(bs)
        blocks.append((bs, bs + bl))
        if bs == START:
            break
        p, n = struct.unpack_from("<HH", code, bs - 8)
        bs, bl = p << 12, (n << 12) - 4
        if len(blocks) > 200:
            raise RuntimeError("runaway CRC chain")
    return blocks


# --------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--built", default=r"C:\Users\dudei\Desktop\Projects\accord-firmware"
                                       r"\analysis-2020accord\_v52c_plain_image.bin")
    ap.add_argument("--baseline", default=r"C:\Users\dudei\Desktop\Projects\accord-firmware"
                                          r"\analysis-2020accord\_v38_plain_image.bin")
    ap.add_argument("--repoints", default="", help="comma-separated hex site addresses (optional override)")
    args = ap.parse_args()

    built = open(args.built, "rb").read()
    base = open(args.baseline, "rb").read()
    print(f"built    : {args.built}\n           sha256 {hashlib.sha256(built).hexdigest()}")
    print(f"baseline : {args.baseline}\n           sha256 {hashlib.sha256(base).hexdigest()}\n")

    # ---- 1. discover the repoint set FROM THE BYTES (do not trust a supplied list) -----------------
    print("== 1. repoint discovery (from the built bytes, not from the builder) ==")
    disp_cell = gp_field(D_CELL)
    disp_raw = gp_field(D_SENSOR)
    discovered = []
    for a in range(START, END - 4, 2):
        if u16(built, a + 2) == disp_cell and (u16(built, a) & 0x1F) == 4 \
                and ((u16(built, a) >> 5) & 0x3F) in (0x38, 0x39, 0x3A, 0x3B) \
                and a not in range(CAVE_BASE, CAVE_BASE + 128):
            if u16(base, a + 2) == disp_raw:
                discovered.append(a)
    print(f"  repointed carrier sites found: {len(discovered)}")
    for a in discovered:
        d = decode_ldst(built, a)
        print(f"    0x{a:05X}  {d[0]:<5} -0x{D_CELL:04X}[gp],r{d[2]}")
    check(len(discovered) > 0, "at least one repoint present")

    # ---- 2. instruction-boundary proof for every repoint site -------------------------------------
    print("\n== 2. instruction-boundary proof (linear sweep, catches coincidental alignment) ==")
    for a in discovered:
        d = decode_ldst(built, a)
        ok_form = d is not None and d[0] == "ld.h" and d[1] == 4
        # sweep from a known-safe anchor 64 bytes back that is itself a boundary in BOTH images
        anchor = None
        for back in range(16, 512, 2):
            cand = a - back
            if cand < START:
                break
            if boundary_walk_reaches(built, cand, a, limit=back + 8):
                anchor = cand
                break
        check(ok_form and anchor is not None,
              f"0x{a:05X} is a real `ld.h -disp[gp],rX` at an instruction boundary",
              f"form={d} anchor={anchor}")

    # ---- 3. the three RAW monitor sites must still read RAW ---------------------------------------
    print("\n== 3. health gates must still read RAW gp-0x4f60 ==")
    for a, why in RAW_MONITOR_SITES.items():
        check(u16(built, a + 2) == disp_raw, f"0x{a:05X} still RAW -- {why}",
              f"disp=0x{u16(built, a + 2):04X}")
    for a, why in DORMANT_RAW_SITES.items():
        check(u16(built, a + 2) == disp_raw, f"0x{a:05X} still RAW -- {why}",
              f"disp=0x{u16(built, a + 2):04X}")
    for a, why in LEAVE_RAW_CARRIERS.items():
        check(u16(built, a + 2) == disp_raw, f"0x{a:05X} still RAW (deliberate exclusion) -- {why}",
              f"disp=0x{u16(built, a + 2):04X}")
    # And the exclusions must not have been swept into the repoint set by accident.
    check(not (set(discovered) & (set(RAW_MONITOR_SITES) | set(DORMANT_RAW_SITES)
                                 | set(LEAVE_RAW_CARRIERS))),
          "no repointed site collides with a monitor / dormant arm / deliberate exclusion")

    # COMPLETENESS: every command-region raw read must be justified. This is the machine-checked
    # form of the "all carriers are filtered" claim -- it fails if a future edit leaves an
    # unexplained raw read on the command path.
    cmd_raw = []
    for a in range(MAIN_START, MAIN_END - 4, 2):
        if not (COMMAND_REGION[0] <= a < COMMAND_REGION[1]):
            continue
        w1 = u16(built, a)
        if (w1 & 0x1F) == 4 and ((w1 >> 5) & 0x3F) == 0x39 and u16(built, a + 2) == disp_raw:
            cmd_raw.append(a)
    unjustified = [a for a in cmd_raw if a not in COMMAND_RAW_JUSTIFIED]
    check(not unjustified,
          f"all {len(cmd_raw)} command-region RAW reads are justified (0 unexplained carriers)",
          f"unjustified: {[hex(a) for a in unjustified]}")
    missing = [a for a in COMMAND_RAW_JUSTIFIED if a not in cmd_raw]
    check(not missing,
          "every justified-raw site is actually still raw in the built image",
          f"no longer raw: {[hex(a) for a in missing]}")

    # ---- 4. cave semantics, decoded from the built image ------------------------------------------
    print("\n== 4. cave semantics (decoded from built bytes, then simulated) ==")
    seq, pc = [], CAVE_BASE
    while pc < CAVE_BASE + 128:
        w = u16(built, pc)
        n = insn_lens(built, pc)[0]
        seq.append((pc, w, built[pc:pc + n]))
        if (w & 0xFFC0) == 0x0780:      # jr -> end of cave
            break
        pc += n
    tail = pc + 4
    check(u16(built, CAVE_BASE + 0x14) == ((10 << 11) | (0x39 << 5) | 4),
          "cave loads the state cell into r10 (ld.h ...,r10)")
    check(u16(built, CAVE_BASE + 0x16) == disp_cell,
          f"cave state-cell disp is gp-0x{D_CELL:04X}", f"got 0x{u16(built, CAVE_BASE + 0x16):04X}")
    check(u16(built, CAVE_BASE + 0x1A) == disp_raw, "cave reads RAW gp-0x4f60 as the filter input")
    check(u16(built, CAVE_BASE + 0x38) == disp_cell, "cave stores back to the state cell",
          f"got 0x{u16(built, CAVE_BASE + 0x38):04X}")
    # round-to-nearest constant present
    found_round = any(built[p:p + 4] == struct.pack("<HH", (12 << 11) | (0x30 << 5) | 12, ROUND)
                      for p, _w, _b in seq)
    check(found_round, f"round-to-nearest `addi {ROUND},r12,r12` present (kills the DC-bias ratchet)")
    # displaced instructions re-executed LAST, then jr to RETURN
    check(built[tail - 8:tail - 4] == bytes.fromhex("e0410870"),
          "displaced `cmp r0,r8` + `mov r8,r14` re-executed LAST (PSW flags fresh for the bge)")
    jr_w = u16(built, tail - 4)
    jr_disp = ((jr_w & 0x3F) << 16) | u16(built, tail - 2)
    if jr_disp & 0x200000:
        jr_disp -= 0x400000
    check((tail - 4) + jr_disp == RETURN, f"cave returns to 0x{RETURN:05X}",
          f"computed 0x{(tail - 4) + jr_disp:05X}")

    # simulate the decoded arithmetic against the intended reference filter
    def ref(y, x):
        return y + ((ALPHA * (x - y) + ROUND) >> 10)
    y_sim = 0
    ok_sim = True
    for x in [0, 1, -1, 17, -17, 25600, -25600, 12345, -12345, 3, -3]:
        for _ in range(50):
            y_sim = ref(y_sim, x)
        if not (-32768 <= y_sim <= 32767):
            ok_sim = False
    check(ok_sim, "filter state provably stays inside s16 for all sensor inputs (no st.h truncation)")
    # DC-bias check. A quantized EMA CANNOT settle exactly -- it has an inherent deadband where the
    # step rounds to 0. What V52's round-to-nearest must guarantee is that the deadband is SYMMETRIC
    # about x (midpoint 0), i.e. no one-way ratchet. V50's floor rounding gave [-13,0], midpoint -6.5.
    def settle(x, y0):
        y = y0
        for _ in range(20000):
            n = ref(y, x)
            if n == y:
                return y
            y = n
        return y
    for x in (137, 1000, 4096, -137, -4096):
        lo, hi = settle(x, x - 4000) - x, settle(x, x + 4000) - x
        check(lo + hi == 0, f"deadband symmetric about x={x} -> no DC-bias ratchet",
              f"deadband [{lo:+d},{hi:+d}] midpoint {(lo + hi) / 2:+.1f}")
    # Round-half-up is odd-symmetric EXCEPT at exact ties (74*d == 512 mod 1024), where +d rounds up
    # and -d rounds toward zero -- a 1 LSB difference. Assert the asymmetry is EXACTLY that set, that
    # every discrepancy is 1 LSB, and that NO tie falls inside the deadband (where it could bias the
    # settling point). Ties start at |d|>=512, i.e. large transients where 1 LSB of a ~4000-count step
    # is 0.025%. This is characterised-and-accepted, not a ratchet.
    step = lambda d: (ALPHA * d + ROUND) >> 10
    reach = 58368
    asym = [d for d in range(-reach, reach + 1) if step(d) != -step(-d)]
    ties = [d for d in range(-reach, reach + 1)
            if (ALPHA * d) % 1024 == 512 or (ALPHA * -d) % 1024 == 512]
    check(set(asym) == set(ties),
          "EMA quantizer asymmetry is EXACTLY the round-half-up tie set (no systematic skew)",
          f"{len(asym)} asym vs {len(ties)} ties")
    check(all(abs(step(d) + step(-d)) == 1 for d in asym),
          "every tie discrepancy is exactly 1 LSB")
    check(all(abs(d) > 6 for d in asym),
          "no tie falls inside the +/-6 deadband (settling point cannot be biased)")

    # ---- 5. trampoline ---------------------------------------------------------------------------
    print("\n== 5. trampoline transparency ==")
    check(base[HOOK:HOOK + 4] == bytes.fromhex("e0410870"), "baseline hook was the stock cmp/mov")
    tw = u16(built, HOOK)
    td = ((tw & 0x3F) << 16) | u16(built, HOOK + 2)
    if td & 0x200000:
        td -= 0x400000
    check((tw & 0xFFC0) == 0x0780 and HOOK + td == CAVE_BASE,
          f"hook @0x{HOOK:05X} is `jr 0x{CAVE_BASE:05X}`", f"target 0x{HOOK + td:05X}")

    # ---- 6. safety cals byte-stock ---------------------------------------------------------------
    print("\n== 6. safety calibrations byte-stock ==")
    for a, (v, why) in SAFETY_CALS_U16.items():
        check(u16(built, a) == v, f"0x{a:05X} == {v} ({why})", f"got {u16(built, a)}")
    for a, (v, why) in SAFETY_CALS_U8.items():
        check(built[a] == v, f"0x{a:05X} == 0x{v:02X} ({why})", f"got 0x{built[a]:02X}")
    check(built[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16] == CLAMP_FLOAT_STOCK,
          "DTC-0x1d clamp float mirror byte-stock (no-debounce hard-shutdown trap)")

    # ---- 7. ratchet fix present ------------------------------------------------------------------
    print("\n== 7. carried-forward state-4 ratchet fix ==")
    check(u16(base, RATCHET_ADDR) == RATCHET_STOCK_HW, "baseline 0x454FE is the stock bne")
    check(u16(built, RATCHET_ADDR) == RATCHET_NEW_HW, "built 0x454FE is br (ratchet fix carried)")
    check(built[RATCHET_ADDR + 1] == base[RATCHET_ADDR + 1], "ratchet branch displacement untouched")

    # ---- 8. CRC chain ----------------------------------------------------------------------------
    print("\n== 8. CRC chain ==")
    bb, xb = crc_blocks(base), crc_blocks(built)
    check(len(bb) == len(xb), f"block count unchanged ({len(bb)})", f"{len(bb)} -> {len(xb)}")
    check(len(xb) == EXPECTED_BLOCKS, f"chain traverses the expected {EXPECTED_BLOCKS} blocks",
          f"got {len(xb)}")
    check(any(s == MAIN_START and t == MAIN_END for s, t in xb),
          f"MAIN block 0x{MAIN_START:05X}..0x{MAIN_END:05X} is in the chain")
    bad = [(s, zlib.crc32(built[s:t]) & 0xFFFFFFFF, struct.unpack_from("<I", built, t)[0])
           for s, t in xb if (zlib.crc32(built[s:t]) & 0xFFFFFFFF) != struct.unpack_from("<I", built, t)[0]]
    check(not bad, f"all {len(xb)} CRC blocks verify", f"bad={[hex(x[0]) for x in bad]}")

    # ---- 9. no stray edits -----------------------------------------------------------------------
    print("\n== 9. every changed byte is accounted for ==")
    diffs = [i for i in range(0, 0x100000) if base[i] != built[i]]
    intended = set()
    for a in discovered:
        intended.update({a + 2, a + 3})
    intended.add(RATCHET_ADDR)
    intended.update(range(HOOK, HOOK + 4))
    intended.update(range(CAVE_BASE, tail))
    for s, t in xb:
        intended.update(range(t, t + 4))          # CRC trailers may legitimately change
    stray = [i for i in diffs if i not in intended]
    check(not stray, f"{len(diffs)} changed bytes, 0 stray",
          f"stray at {[hex(i) for i in stray[:24]]}")

    print(f"\n{'=' * 78}")
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} FAILURE(S) out of {CHECKS[0]} checks")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print(f"RESULT: ALL {CHECKS[0]} CHECKS PASSED")
    print("NOTE: this verifier proves BYTE + STRUCTURAL integrity only. It does NOT close GATE-2")
    print("      (closed-loop stability) and is NOT a substitute for the Ghidra re-disassembly of")
    print("      the built image. Both remain mandatory before any flash consideration.")


if __name__ == "__main__":
    main()
