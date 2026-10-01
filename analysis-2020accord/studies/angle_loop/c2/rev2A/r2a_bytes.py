# -*- coding: utf-8 -*-
r"""r2a_bytes.py -- every byte of every C2 rev 2 (reviser A) implementation, and the byte-level checks the C2
bytes-and-fail-safe refuter listed as unrun.  ANALYSIS ONLY: nothing is written to any image file, no .rwd, and the
integrity trailers are NOT computed here -- the builder's H8 step owns that; this script only NAMES the regions an edit
dirties.

 1  ASSEMBLE  each cave with the D designer's two-pass assembler (ds_asm.assemble) and compare P1 / F1 byte for byte
    with the panel's ds_cave_D2a.hex / ds_cave_B0r.hex; P2 / F2 differ from them only in the table rows.
 2  BRANCH FIELDS  the hook (jarl), the freeze return (jr), every Bcond: the displacement re-extracted from the BYTES and
    its target checked (inside the cave, 0x29D7A, or 0x29D7E), independent of the assembler's label arithmetic.
 3  CENSUS    from the listing semantics: registers the cave writes (must be a subset of r6 r8 r9 r13 r16 r26; never r25
    or r14), memory the cave writes (must be none), memory it reads (gp cells and the table only), the walk's
    terminating 0xFFFF row.
 4  H1        the assembled bytes EXECUTED by ds_asm.run_bytes against the lane's cave arithmetic (ds_asm.cave_ref), 60 000
    random inputs per implementation incl. the 0x7FFF sentinel, validity edges, table knots +-1, a random register file
    (every non-scratch register incl. r25 and r14 checked unchanged).
 5  DIFF      every edit applied in memory to V295 by ds_bytes.build (each old byte asserted first); the full diff over
    [0x13000, 0x100000) must contain exactly the listed bytes.
 6  OVERFLOW  the int32 budget of every multiply the cave adds, evaluated on the implementation's own table extremes.
 7  FORMS     every distinct multi-byte cave instruction searched in the V295 image: where the same bytes already exist
    at an even code address, that address is listed for a Ghidra dry-run decode (done by hand, recorded on the page).
usage: python r2a_bytes.py      (writes r2a_bytes_out.txt and c2_cave_<impl>.hex)"""
from __future__ import annotations

import hashlib
import struct

import numpy as np

import r2a_common as R

import ds_asm as A  # noqa: E402
import ds_bytes as DB  # noqa: E402

V = open(A.IMG, "rb").read()
assert hashlib.sha256(V).hexdigest().startswith("5c044d65"), "not the V295 image"
ALLOWED_W = {6, 8, 9, 13, 16, 26}


def writes_of(ins):
    """registers an assembler instruction tuple writes (ds_asm.listing semantics)."""
    op = ins[0]
    if op in ("shl_i", "sar_i", "mov_i5", "add_i5"):
        return {ins[2]}
    if op in ("mov", "subr", "sub", "add"):
        return {ins[2]}
    if op == "cmp" or op in ("nop", "half", "jmp", "jr") or op in A.COND:
        return set()
    if op == "mov_i32":
        return {ins[2]}
    if op in ("movea", "addi", "andi"):
        return {ins[3]}
    if op in ("ld_hu", "ld_h", "ld_w"):
        return {ins[3]}
    if op == "st_w":
        return set()
    if op == "mul":
        return {ins[2]} | ({ins[3]} if ins[3] else set())
    if op in A.CMOV:
        return {ins[3]}
    if op == "jarl":
        return {ins[2]}
    raise KeyError(op)


def reads_mem(ins):
    if ins[0] in ("ld_hu", "ld_h", "ld_w"):
        return (ins[2], ins[1])
    return None


def branch_from_bytes(code, base, pc):
    """re-extract a branch target from the BYTES (Format III Bcond / Format V jr-jarl / jmp [reg])."""
    h1 = code[pc - base] | (code[pc - base + 1] << 8)
    op6 = (h1 >> 5) & 0x3F
    if (op6 >> 2) == 0b1011:
        d = ((h1 >> 11) << 4) | (((h1 >> 4) & 7) << 1)
        d = d - 512 if d & 0x100 else d
        return ("bcond", pc + d)
    if op6 in (0x3C, 0x3D):
        h2 = code[pc - base + 2] | (code[pc - base + 3] << 8)
        if h2 & 1 == 0:
            d = ((h1 & 0x3F) << 16) | h2
            d = d - (1 << 22) if d & (1 << 21) else d
            return ("jr" if (h1 >> 11) == 0 else "jarl", pc + d)
    if h1 & 0xFFE0 == 0x0060:
        return ("jmp", h1 & 0x1F)
    return None


def main():
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)

    tabs = R.tables()
    P(f"base V295 {A.IMG.split(chr(92))[-1]}  sha256 {hashlib.sha256(V).hexdigest()}")
    hook = bytes(V[0x29D76:0x29D7A])
    P(f"hook site 0x29D76 in V295: {hook.hex(' ')} (shl 2,r16 ; sub r26,r16 -- displaced verbatim into the cave)")
    P(f"free span 0xC4BD8..0xC4FEF all 0xFF in V295: {all(x == 0xFF for x in V[0xC4BD8:0xC4FF0])}")
    summary = {}
    for impl in R.IMPLS:
        tbl = tabs[impl]
        lst = R.IMPLS[impl]["listing"]
        cid = "D2a" if lst == "D2a" else "B0r"
        code, labels, asm_lines = A.assemble(lst, tbl)
        ncode = labels["TBL"] - A.CAVE
        P("=" * 118)
        P(f"{impl}: {R.IMPLS[impl]['note']}")
        P(f"  cave {A.CAVE:#x}..{A.CAVE + len(code):#x}: {len(code)} bytes = {ncode} code + {len(code) - ncode} table; "
          f"sha256 {hashlib.sha256(code).hexdigest()[:16]}")
        ref = {"P1": "ds_cave_D2a.hex", "F1": "ds_cave_B0r.hex"}.get(impl)
        if ref:
            panel = bytes.fromhex((R.AL / "panel" / "D-structure" / ref).read_text().replace(" ", "").strip())
            P(f"  [1] == panel {ref}: {panel == code}")
        else:
            base_impl = "P1" if lst == "D2a" else "F1"
            c0, l0, _ = A.assemble(lst, tabs[base_impl])
            P(f"  [1] code bytes == {base_impl}'s code bytes: {code[:ncode] == c0[:l0['TBL'] - A.CAVE]}; table differs "
              f"only: {code[ncode:] != c0[l0['TBL'] - A.CAVE:]}")
        # [2] branch fields from the bytes
        bad_br = []
        for pc, lab, ins, bs, com in asm_lines:
            if ins[0] in A.COND or ins[0] in ("jr", "jmp"):
                b = branch_from_bytes(code, A.CAVE, pc)
                tgt = labels[ins[1]] if ins[0] in A.COND and isinstance(ins[1], str) else (
                    ins[1] if ins[0] == "jr" else None)
                if ins[0] == "jmp":
                    ok = b == ("jmp", 6)
                elif ins[0] == "jr":
                    ok = b == ("jr", A.FRZ_RET)
                else:
                    ok = b[0] == "bcond" and b[1] == tgt and A.CAVE <= b[1] < A.CAVE + ncode
                if not ok:
                    bad_br.append((hex(pc), ins, b))
        hk = A.enc(("jarl", A.CAVE, 6), A.HOOK, {})
        hkb = b"".join(struct.pack("<H", x) for x in hk)
        hb = branch_from_bytes(hkb, A.HOOK, A.HOOK)
        P(f"  [2] hook 0x29D76 -> {hkb.hex(' ')} decodes from the bytes as {hb[0]} {hb[1]:#x} (want jarl 0xc4c00, r6: "
          f"reg2 field {(hk[0] >> 11)}); every cave branch target re-extracted from the bytes: "
          f"{'OK' if not bad_br else bad_br}")
        # [3] census
        w = set()
        rd = []
        stores = []
        for pc, lab, ins, bs, com in asm_lines:
            if ins[0] == "half":
                continue
            w |= writes_of(ins)
            m = reads_mem(ins)
            if m:
                rd.append(m)
            if ins[0] == "st_w":
                stores.append((hex(pc), ins))
        gp_reads = sorted({f"gp{d:+#x}" for b, d in rd if b == 4})
        tbl_reads = sorted({f"[r9{d:+d}]" for b, d in rd if b == 9})
        P(f"  [3] registers written {sorted(w)}  (allowed {sorted(ALLOWED_W)}; r25/r14 written: "
          f"{bool({25, 14} & w)}) -> {'OK' if w <= ALLOWED_W and not ({25, 14} & w) else 'FAIL'}")
        P(f"      memory written: {stores or 'none'};  gp cells read: {gp_reads};  table reads: {tbl_reads};  "
          f"last table row {tbl[-1]} (0xFFFF terminator: {tbl[-1][0] == 0xFFFF})")
        # [4] H1
        nb = A.h1_test(lst, tbl, code, N=60000)
        P(f"  [4] H1: the assembled bytes executed vs the lane's cave arithmetic, 60000 random inputs: {nb} mismatches")
        # [5] diff
        img, listing, cave, labels2 = DB.build(cid, tbl)
        assert cave == code
        diff = [a for a in range(0x13000, 0x100000) if img[a] != V[a]]
        listed = set()
        for kind, a, old, new, dec, term in listing:
            n = len(bytes.fromhex(old.replace(" ", "")))
            listed |= {a + i for i in range(n) if img[a + i] != V[a + i]}
        cave_set = {a for a in range(A.CAVE, A.CAVE + len(cave)) if img[a] != V[a]}
        unlisted = [hex(a) for a in diff if a not in listed and a not in cave_set]
        n_code = sum(1 for a in listed if a < 0xC0000)
        n_cal = sum(1 for a in listed if a >= 0xC0000)
        P(f"  [5] edits (each old byte asserted against V295 before replacing):")
        for kind, a, old, new, dec, term in listing:
            P(f"      {kind:4s} {a:#08x}  {old:12s} -> {new:12s}  {dec:52s} {term}")
        P(f"      FULL DIFF [0x13000, 0x100000): {len(diff)} bytes differ; written: in-place code {n_code} + cal {n_cal} "
          f"+ cave {len(cave)} = {n_code + n_cal + len(cave)}; UNLISTED: {unlisted or 'none'}")
        regions = sorted({("main code block, trailer 0xC4FFC" if a < 0xC5000 else
                           ("cal page 0xC6000-0xC6FFC" if 0xC6000 <= a < 0xC7000 else f"block holding {a & ~0xFFF:#x}"))
                          for a in diff})
        P(f"      integrity regions dirtied (the builder recomputes and verifies them, H8): {regions}")
        # [6] overflow on this table
        Gmax = max(R.G_at(v, tbl) for v in np.arange(0, 60.0, 0.05))
        Emax = 4 * 32767 + 65535
        dvS = max(abs((tbl[i + 1][0] - tbl[i][0]) * tbl[i][2]) for i in range(len(tbl) - 1) if tbl[i + 1][0] != 0xFFFF)
        P(f"  [6] |E| <= 4*32767 + 65535 = {Emax}; max G over 0..60 m/s {Gmax}; |E*G| <= {Emax * Gmax:.3e} "
          f"(< 2^31 = 2.147e9: {Emax * Gmax < 2 ** 31}); max |dv*S| in a segment {dvS} (< 2^31: {dvS < 2 ** 31}); "
          f"|E'*112| <= {(Emax * Gmax >> 8) * 112:.3e}; D: |34 * 13000| = {34 * 13000} -> DCL clamp")
        summary[impl] = dict(cave=len(code), code=ncode, table=len(code) - ncode, in_place=n_code, cal=n_cal,
                             total=n_code + n_cal + len(code), h1=nb, unlisted=unlisted, regs=sorted(w))
        (R.HERE / f"c2_cave_{impl}.hex").write_text(code.hex(" ") + "\n")
    # [7] forms present elsewhere in the image (for Ghidra dry-run decodes)
    P("=" * 118)
    P("[7] distinct cave instructions (P and F listings) whose exact bytes already occur at an even code address in V295 "
      "(Ghidra dry-run decode targets):")
    seen = {}
    for lst, base_impl in (("D2a", "P2"), ("B0", "F2")):
        code, labels, asm_lines = A.assemble(lst, tabs[base_impl])
        for pc, lab, ins, bs, com in asm_lines:
            if ins[0] == "half":
                continue
            b = bytes.fromhex(bs.replace(" ", ""))
            if len(b) < 4 or b in seen:
                continue
            hits = []
            start = 0x13000
            while len(hits) < 2:
                i = V.find(b, start, 0xC0000)
                if i < 0:
                    break
                if i % 2 == 0:
                    hits.append(i)
                start = i + 1
            seen[b] = (lst, pc, ins, hits)
    for b, (lst, pc, ins, hits) in seen.items():
        P(f"  {lst:4s} {pc:#07x} {b.hex(' '):20s} {str(ins):38s} found at {[hex(x) for x in hits] or 'nowhere'}")
    (R.HERE / "r2a_bytes_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    import json
    (R.OUT / "bytes_summary.json").write_text(json.dumps(summary))


if __name__ == "__main__":
    main()
