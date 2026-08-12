#!/usr/bin/env python3
"""V94 CELL LEDGER — cumulative non-stock cells, attributed to the build that introduced them.

Reads the PLAIN IMAGES ON DISK.  Never the build scripts.  V850E2 is LITTLE-ENDIAN and the plain
images are flat 1 MiB code images where file offset == firmware address (anchored below).

Four products:
  1) `diff`   — every byte where V94 differs from STOCK, run-grouped, with the FIRST build in the
                on-disk chain at which that address left stock.
  2) `matrix` — the load-bearing cells down every build that has an image, run-length compressed,
                with a freeze count (consecutive BUILDS at the current value, STOCK row excluded)
                and a `BACK TO STOCK` flag on every segment that returned to Honda's value.
  3) `grid`   — the same cells as a markdown table, milestone build columns only.
  4) `mask`   — the plain-image coverage mask (below), so it can be audited rather than trusted.

Coverage caveat, EVIDENCE: the plain images are reconstructed from the RWD and leave spans 0xFF
that are real data in the stock dump — 0x00000-0x05F31, 0x07000-0x0EF71 (both sparse) and
0x12FF0-0x12FFF.  50,284 bytes are 0xFF in ALL 85 images, so they are packaging, not levers, and
`diff` excludes them.  The 12 bytes that are 0xFF on V94 but NOT on every image — 0x55C0F,
0xC61C0-0xC61C5, 0xC64B4-0xC64B8 — are REAL edits and are kept in the diff.

Usage:
    python ledger_v94_cells.py diff                 # STOCK vs V94
    python ledger_v94_cells.py diff V92 V94         # any PAIR, by build tag
    python ledger_v94_cells.py diff V92 _v95_FOO_plain_image.bin    # or by filename / glob /
                                                    #   absolute path, for a build not yet in BUILDS
    python ledger_v94_cells.py matrix
    python ledger_v94_cells.py grid
    python ledger_v94_cells.py mask

A pair diff still prints the STOCK value and the first build that left stock at each address, so
"what does V95 revert" and "who put it there" are answered in one table.
`LEDGER_TARGET=<tag>` repoints `matrix` / `grid` (and the `diff` default) at another build.
"""
import hashlib
import struct
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
STOCK = ROOT / "stock_fw_dump" / "code.bin"

# Build order.  Pre-V38 entries are included so cells introduced in the V22-V37 era attribute to a
# real tag instead of collapsing onto "V38".  V22 is the earliest image on disk.
BUILDS = [
    ("STOCK", STOCK),
    ("V22", "_v22_plain_image.bin"),
    ("V23", "_v23_plain_image.bin"),
    ("V24", "_v24_plain_image.bin"),
    ("V25", "_v25_plain_image.bin"),
    ("V26", "_v26_plain_image.bin"),
    ("V27", "_v27_plain_image.bin"),
    ("V28", "_v28_plain_image.bin"),
    ("V29", "_v29_plain_image.bin"),
    ("V30", "_v30_plain_image.bin"),
    ("V31", "_v31_plain_image.bin"),
    ("V31p", "_v31p_plain_image.bin"),
    ("V31p2", "_v31p_v2_plain_image.bin"),
    ("V31t", "_v31t_plain_image.bin"),
    ("V31u", "_v31u_plain_image.bin"),
    ("V32", "_v32_plain_image.bin"),
    ("V33", "_v33_plain_image.bin"),
    ("V34", "_v34_plain_image.bin"),
    ("V35", "_v35_plain_image.bin"),
    ("V36", "_v36_plain_image.bin"),
    ("V37", "_v37_plain_image.bin"),
    ("V38", "_v38_plain_image.bin"),
    ("V39", "_v39_plain_image.bin"),
    ("V40", "_v40_plain_image.bin"),
    ("V41", "_v41_plain_image.bin"),
    ("V42", "_v42_plain_image.bin"),
    ("V43", "_v43_plain_image.bin"),
    ("V44", "_v44_plain_image.bin"),
    ("V45", "_v45_plain_image.bin"),
    ("V46", "_v46_plain_image.bin"),
    ("V47", "_v47_plain_image.bin"),
    ("V48a", "_v48a_plain_image.bin"),
    ("V48b", "_v48b_plain_image.bin"),
    ("V49", "_v49_plain_image.bin"),
    ("V49p", "_v49p_plain_image.bin"),
    ("V50", "_v50_plain_image.bin"),
    ("V50p", "_v50probe_plain_image.bin"),
    ("V51p", "_v51probe_plain_image.bin"),
    ("V52", "_v52_plain_image.bin"),
    ("V52c", "_v52c_plain_image.bin"),
    ("V53", "_v53_plain_image.bin"),
    ("V54", "_v54_plain_image.bin"),
    ("V55", "_v55_plain_image.bin"),
    ("V56", "_v56_plain_image.bin"),
    ("V57", "_v57_plain_image.bin"),
    ("V58", "_v58_plain_image.bin"),
    ("V59", "_v59_plain_image.bin"),
    ("V60", "_v60_plain_image.bin"),
    ("V61", "_v61_plain_image.bin"),
    ("V62", "_v62_plain_image.bin"),
    ("V63", "_v63_plain_image.bin"),
    ("V64", "_v64_plain_image.bin"),
    ("V65", "_v65_plain_image.bin"),
    ("V66", "_v66_plain_image.bin"),
    ("V67", "_v67_plain_image.bin"),
    ("V68", "_v68_plain_image.bin"),
    ("V69", "_v69_plain_image.bin"),
    ("V70", "_v70_plain_image.bin"),
    ("V71a", "_v71a_plain_image.bin"),
    ("V71b", "_v71b_plain_image.bin"),
    ("V71c", "_v71c_plain_image.bin"),
    ("V72", "_v72_plain_image.bin"),
    ("V73", "_v73_plain_image.bin"),
    ("V74", "_v74_engagedcols_x0_12_addonly_plain_image.bin"),
    ("V75", "_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
    ("V76", "_v76_v38base_relu_damper_plain_image.bin"),
    ("V76g", "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"),
    ("V77", "_v77_C63A0.1024_v74base_plain_image.bin"),
    ("V77b", "_v77b_C63A0.1024_v75base_plain_image.bin"),
    ("V78", "_v78_v76base_ey1_449_dose206_plain_image.bin"),
    ("V79", "_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin"),
    ("V80", "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin"),
    ("V81", "_v81_C407E.511-FRICTION.STOCK_plain_image.bin"),
    ("V83a", "_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin"),
    ("V84", "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin"),
    ("V85", "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin"),
    ("V86", "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V86b", "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V87", "_v87_V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98_plain_image.bin"),
    ("V88", "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256_plain_image.bin"),
    ("V89", "_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin"),
    ("V90", "_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin"),
    ("V91", "_v91_V90BASE-CBE74.M26.M27.X1.5_plain_image.bin"),
    ("V92", "_v92_V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4_plain_image.bin"),
    ("V93", "_v93_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75_plain_image.bin"),
    ("V94", "_v94_V90BASE-CBE74.M24x0.50.M26.M27x0.25-FALLBACKx0.75-427.SAR1_plain_image.bin"),
]

import os
# Override to point the diff/matrix at another build, e.g. LEDGER_TARGET=V92
TARGET = os.environ.get("LEDGER_TARGET", "V94")

# ---- cells for the cross-build matrix.  (addr, width, signed, label)
# width 1 = byte, 2 = halfword LE.  Friction knots are resolved through the pointer array instead.
MATRIX_SCALARS = [
    (0x3AA96, 1, False, "Lever B gate byte (C5 dead-0x683C / FB latActive-0x6806)"),
    (0x3AB76, 1, False, "V62 sar r26 (AA stock / A9 = x2)"),
    (0x3AC20, 1, False, "V62 sar r24 (AA stock / A9 = x2)"),
    (0x454FE, 1, False, "V42 macro-ratchet fix (BA stock bne / B5 br)"),
    (0x55E10, 1, False, "CAN-427 packer shift byte (sar N)"),
    (0x55C0E, 1, False, "CAN-427 packer source instr byte 0"),
    (0x55DF2, 2, False, "CAN-427 packer source disp (halfword)"),
    (0x2A1F0, 2, False, "V57 decouple displacement (7CD0 => 0xC6CD0)"),
    (0xC407C, 2, True, "friction-comp clamp neighbour"),
    (0xC407E, 2, True, "friction-comp clamp / DTC-0x1d interlock (+-511)"),
    (0xC40BC, 2, True, "Coulomb relay breakpoint (de-relay lever)"),
    (0xC40D2, 2, True, "K1 modelled Coulomb friction gain"),
    (0xC40D4, 2, True, "command EMA coeff"),
    (0xC61B2, 2, True, "ARBITRATION output clamp"),
    (0xC61B4, 2, True, "LKAS-GAIN output clamp"),
    (0xC61B8, 2, True, "pre-gain deadband"),
    (0xC62EA, 2, True, "low-speed steer lockout window"),
    (0xC63A0, 2, True, "FUN_00038148 lane weight [0]"),
    (0xC63A2, 2, True, "FUN_00038148 lane weight [1]"),
    (0xC63A4, 2, True, "FUN_00038148 lane weight [2]"),
    (0xC63A6, 2, True, "FUN_00038148 lane weight [3]"),
    (0xC63A8, 2, True, "FUN_00038148 lane weight [4]"),
    (0xC63AA, 2, True, "FUN_00038148 lane weight [5]"),
    (0xC63AC, 2, True, "Path-2 accumulator IIR coeff"),
    (0xC63F8, 2, True, "authority ramp-rate UP (0x8000/33 ~= 993 ms @1kHz)"),
    (0xC63FC, 2, True, "authority ramp-rate, the 10x-asymmetric twin"),
    (0xC640A, 2, True, "FUN_00036c12 FALLBACK-2 flat gain (gp-0x671a >= 5)"),
    (0xC640C, 2, True, "FUN_00036c12 FALLBACK-1 flat gain (outer gate fails)"),
    (0xC643E, 2, True, "gain_A arm"),
    (0xC6440, 2, True, "third arm gp-0x671a"),
    (0xC6442, 2, True, "gp-0x671d arm"),
    (0xC6444, 2, True, "r26 engaged arm"),
    (0xC6446, 2, True, "r24 engaged arm (Lever B)"),
    (0xC644A, 2, True, "V43 dirty-derivative pole"),
    (0xC646C, 2, True, "SHARED sensor scale (stock 891)"),
    (0xC64DE, 2, False, "legacy re-engage ramp (V18 'RAMPSTEP', label disputed)"),
    (0xC6CD0, 2, True, "V57 private forward LKAS gain"),
    # --- V38 authority foundation: the FLOAT twin of the corridor / boost walls
    (0xC6598, 4, "f", "corridor wall FLOAT +A"),
    (0xC659C, 4, "f", "corridor wall FLOAT +B"),
    (0xC65AC, 4, "f", "corridor wall FLOAT -A"),
    (0xC65B0, 4, "f", "corridor wall FLOAT -B"),
    (0xC65C4, 4, "f", "boost floor FLOAT [0]"),
    (0xC65C8, 4, "f", "boost floor FLOAT [1]"),
    (0xC65CC, 4, "f", "boost floor FLOAT [2]"),
    # --- and the INT twin, kept in lockstep or the dual-path monitor trips
    (0xC674E, 2, True, "corridor wall INT +A"),
    (0xC6750, 2, True, "corridor wall INT +B"),
    (0xC675A, 2, True, "corridor wall INT -A"),
    (0xC675C, 2, True, "corridor wall INT -B"),
    (0xC6768, 2, True, "boost floor INT [0]"),
    (0xC676A, 2, True, "boost floor INT [1]"),
    (0xC676C, 2, True, "boost floor INT [2]"),
    # --- gentle-EME debounce SM + DTC 0x49 counter gate
    (0xC61C0, 2, False, "gentle-EME debounce RATE threshold [0]"),
    (0xC61C2, 2, False, "gentle-EME debounce RATE threshold [1]"),
    (0xC61C4, 2, False, "gentle-EME debounce RATE threshold [2]"),
    (0xC64B4, 2, False, "gentle-EME debounce TORQUE threshold [0]"),
    (0xC64B6, 2, False, "gentle-EME debounce TORQUE threshold [1]"),
    (0xC64B8, 1, False, "DTC-0x49 fail-counter gate"),
    # --- ARB setpoint limit: one representative of the 8 selector-reachable records
    (0xE4194, 2, False, "ARB setpoint limit rec0 [0] (1 of 72 cells)"),
    (0xE520C, 2, False, "ARB setpoint limit rec7 [0] (1 of 72 cells)"),
    (0x13109, 1, False, "part-number string byte (cosmetic build marker)"),
]

FRICTION_PTR = 0xCBE74  # 34-entry u32 pointer array of 16-byte friction/inertia records
MATRIX_MODES = [24, 26, 27]


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    """[npt:u16][X x npt][Y x npt] — the friction/inertia record layout."""
    n = u16(b, base)
    if not (1 <= n <= 16) or base + 2 + 4 * n > len(b):
        return None
    xs = list(struct.unpack_from(f"<{n}h", b, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n))
    return n, xs, ys


def load_all():
    imgs, order = {}, []
    for name, f in BUILDS:
        p = f if isinstance(f, Path) else ROOT / f
        if not p.exists():
            print(f"### MISSING {name}: {p}", file=sys.stderr)
            continue
        imgs[name] = p.read_bytes()
        order.append(name)
    st = imgs["STOCK"]
    assert len(st) == 0x100000, len(st)
    assert s16(st, 0xC646C) == 891, s16(st, 0xC646C)      # tp-relative anchor, guards off-by-0x1000
    assert st[0x454FE] == 0xBA, hex(st[0x454FE])
    assert u32(st, FRICTION_PTR + 24 * 4) < 0x100000
    return imgs, order


def coverage_mask(imgs, order):
    """Addresses that are 0xFF in EVERY non-stock image but not in stock => packaging, not a lever."""
    st = imgs["STOCK"]
    tags = [n for n in order if n != "STOCK"]
    mask = set()
    cand = [i for i in range(len(st)) if st[i] != 0xFF and imgs[TARGET][i] == 0xFF]
    for i in cand:
        if all(imgs[t][i] == 0xFF for t in tags):
            mask.add(i)
    return mask, cand


def group(addrs):
    runs, cur = [], None
    for i in sorted(addrs):
        if cur and i == cur[1] + 1:
            cur[1] = i
        else:
            cur = [i, i]
            runs.append(cur)
    return runs


def first_nonstock(imgs, order, addr):
    """First tag in build order whose byte at `addr` differs from stock."""
    sv = imgs["STOCK"][addr]
    for n in order:
        if n == "STOCK":
            continue
        if imgs[n][addr] != sv:
            return n
    return None


def cmd_mask(imgs, order):
    mask, cand = coverage_mask(imgs, order)
    print(f"stock non-FF where V94 is FF : {len(cand)} bytes")
    print(f"of which FF in EVERY build   : {len(mask)}  => packaging mask")
    print("mask runs (gap-coalesced <0x100):")
    runs = group(mask)
    co = []
    for a, b in runs:
        if co and a - co[-1][1] < 0x100:
            co[-1][1] = b
        else:
            co.append([a, b])
    for a, b in co:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")
    late = sorted(set(cand) - mask)
    print(f"\nFF in V94 but NOT in every build ({len(late)}): {[hex(x) for x in late]}")
    for a in late:
        print(f"    0x{a:05X} first went FF at {first_nonstock(imgs, order, a)}")


def resolve(spec, imgs):
    """A build tag from BUILDS, or a path/filename/glob under ROOT — so an image that is not yet
    in BUILDS (a freshly cut build) can be diffed without editing this file."""
    if spec in imgs:
        return spec, imgs[spec], dict(BUILDS)[spec]
    p = Path(spec)
    if not p.is_absolute():
        hits = sorted(ROOT.glob(spec)) or sorted(ROOT.glob(f"*{spec}*plain_image.bin"))
        if not hits:
            raise SystemExit(f"cannot resolve '{spec}': not a build tag in BUILDS and no image "
                             f"matches it under {ROOT}")
        if len(hits) > 1:
            raise SystemExit(f"'{spec}' is ambiguous:\n  " + "\n  ".join(h.name for h in hits))
        p = hits[0]
    if not p.exists():
        raise SystemExit(f"no such image: {p}")
    label = p.stem.lstrip("_").split("_")[0].upper() or p.stem   # "_v95_FOO_plain_image" -> "V95"
    return label, p.read_bytes(), p.name


def cmd_diff(imgs, order, base_spec=None, target_spec=None):
    """Byte-diff any PAIR of images.  Defaults to STOCK vs TARGET.

    The `first` column is always the first build that left STOCK at that address — that is the
    attribution question worth asking regardless of which pair is on screen — so a pair diff also
    carries the stock value for context.
    """
    bname, bb, bfile = resolve(base_spec or "STOCK", imgs)
    tname, tb, tfile = resolve(target_spec or TARGET, imgs)
    if len(bb) != len(tb):
        raise SystemExit(f"size mismatch: {bname} {len(bb)} vs {tname} {len(tb)}")
    st = imgs["STOCK"]
    mask, _ = coverage_mask(imgs, order)
    for nm, blob, f in ((bname, bb, bfile), (tname, tb, tfile)):
        print(f"{nm:<6} {f}\n       sha256 {hashlib.sha256(blob).hexdigest()}")
    print()
    diffs = [i for i in range(len(bb)) if bb[i] != tb[i] and i not in mask]
    print(f"{bname} -> {tname}: {len(diffs)} non-mask differing bytes in {len(group(diffs))} runs\n")
    vs_stock = bname != "STOCK"
    hdr = f"{'run':<17} {'len':>3}  {'first':<6} "
    print(hdr + (f"{'STOCK':>24}  {bname:>24}  {tname:>24}" if vs_stock
                 else f"{bname} -> {tname}"))
    for a, b in group(diffs):
        firsts = sorted({first_nonstock(imgs, order, x) for x in range(a, b + 1)},
                        key=lambda n: order.index(n) if n else 999)
        f = "/".join(x or "?" for x in firsts)
        row = f"0x{a:05X}-0x{b:05X} {b - a + 1:>3}  {f:<6} "
        if vs_stock:
            print(row + f"{st[a:b + 1].hex():>24}  {bb[a:b + 1].hex():>24}  {tb[a:b + 1].hex():>24}")
        else:
            print(row + f"{bb[a:b + 1].hex()} -> {tb[a:b + 1].hex()}")


def _read(b, addr, w, signed):
    """signed: True = s16, False = u16/byte, "f" = LE float32."""
    if signed == "f":
        return f"{struct.unpack_from('<f', b, addr)[0]:g}f"
    if w == 1:
        return f"0x{b[addr]:02X}"
    return str(s16(b, addr) if signed else u16(b, addr))


def cmd_matrix(imgs, order):
    st = imgs["STOCK"]
    rows = []
    for addr, w, sg, label in MATRIX_SCALARS:
        vals = {n: _read(imgs[n], addr, w, sg) for n in order}
        rows.append((f"0x{addr:05X}", label, vals))
    for m in MATRIX_MODES:
        for k in range(3):
            vals = {}
            for n in order:
                b = imgs[n]
                base = u32(b, FRICTION_PTR + m * 4)
                r = rec(b, base) if base < 0x100000 else None
                vals[n] = str(r[2][k]) if r and len(r[2]) > k else "BAD"
            rows.append((f"0xCBE74[m{m}]", f"friction/inertia mode {m} Y[{k}]", vals))
        vals = {}
        for n in order:
            b = imgs[n]
            base = u32(b, FRICTION_PTR + m * 4)
            r = rec(b, base) if base < 0x100000 else None
            vals[n] = f"@0x{base:05X}" if r else "BAD"
        rows.append((f"0xCBE74[m{m}]", f"friction/inertia mode {m} record ptr", vals))

    print("=== CROSS-BUILD MATRIX (run-length along build order; STOCK first) ===\n")
    for addr, label, vals in rows:
        segs, prev, run = [], None, []
        for n in order:
            v = vals[n]
            if v != prev:
                if run:
                    segs.append((prev, run))
                run, prev = [n], v
            else:
                run.append(n)
        if run:
            segs.append((prev, run))
        sv = vals["STOCK"]
        cur = vals[TARGET]
        frozen = len([n for n in segs[-1][1] if n != "STOCK"])   # builds, not counting the STOCK row
        state = "STOCK" if cur == sv else "NON-STOCK"
        print(f"{addr:<15} {label}")
        print(f"    stock={sv}  V94={cur}  [{state}]  frozen {frozen} builds "
              f"(since {segs[-1][1][0]})")
        for v, r in segs:
            rng = f"{r[0]}..{r[-1]}" if len(r) > 1 else r[0]
            flag = ""
            if v == sv and r[0] != "STOCK":
                flag = "   <-- BACK TO STOCK"
            print(f"      {rng:<16} {v}{flag}")
        print()


# Milestone columns for the condensed grid: every build that moved one of the matrix cells,
# plus the flown ones.  `grid` prints these; `matrix` prints all 85 builds run-length compressed.
GRID_COLS = ["STOCK", "V22", "V25", "V29", "V31", "V36", "V37", "V38", "V42", "V43", "V53",
             "V57", "V62", "V63", "V67", "V71c", "V72", "V73", "V74", "V76", "V78", "V80",
             "V81", "V83a", "V84", "V85", "V86", "V87", "V88", "V89", "V90", "V91", "V92",
             "V93", "V94"]


def cmd_grid(imgs, order):
    cols = [c for c in GRID_COLS if c in order]
    rows = []
    for addr, w, sg, label in MATRIX_SCALARS:
        rows.append((f"0x{addr:05X}", label, {n: _read(imgs[n], addr, w, sg) for n in cols}))
    for m in MATRIX_MODES:
        for k in range(3):
            vals = {}
            for n in cols:
                b = imgs[n]
                r = rec(b, u32(b, FRICTION_PTR + m * 4))
                vals[n] = str(r[2][k]) if r else "BAD"
            rows.append((f"0xCBE74 m{m}", f"friction/inertia Y[{k}]", vals))
    wid = max(len(v) for _, _, vs in rows for v in vs.values())
    wid = max(wid, max(len(c) for c in cols))
    print("| cell | what | " + " | ".join(cols) + " |")
    print("|---|---|" + "---|" * len(cols))
    for addr, label, vals in rows:
        cells = []
        for c in cols:
            v = vals[c]
            cells.append(f"**{v}**" if v != vals["STOCK"] else v)
        print(f"| `{addr}` | {label} | " + " | ".join(cells) + " |")


def main():
    imgs, order = load_all()
    print(f"ANCHORS OK: stock 0xC646C=891, 0x454FE=0xBA, len=0x100000; "
          f"{len(order) - 1} builds on disk\n")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "diff"
    if cmd == "diff":
        cmd_diff(imgs, order, *sys.argv[2:4])
    else:
        {"matrix": cmd_matrix, "mask": cmd_mask, "grid": cmd_grid}[cmd](imgs, order)


if __name__ == "__main__":
    main()
