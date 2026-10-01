# -*- coding: utf-8 -*-
r"""g_cave.py -- the caves of designer G's implementations as listings -> bytes, and the design-time H1 (the assembled
bytes EXECUTED by the D designer's V850E2 interpreter ds_asm.run_bytes against the integer lane's cave arithmetic).
ANALYSIS ONLY: nothing is written to any image; BELIEF until a built image is decoded by Ghidra (H5).

  (i)  fresh-rate D   = ds_asm.listing('D2a', tbl)   -- rev2-A P2's code byte for byte; only the table rows differ
  (ii) held-rate D    = ds_asm.listing('B0', tbl)    -- C1 rev 2 / rev2-A F2's code byte for byte; only the table differs
  (iii) angle-own D   = listing_box10(tbl, sh)       -- new: the held angle's difference across one refresh, held 10 ticks
Every encoding form of (iii) is one of ds_asm's controlled forms (ds_asm.CONTROLS: ld.w/ld.h/st.w disp[gp], mov imm32,
cmp, cmov z (cond 2), andi, add imm5 (0x29E8E add 0xa,r8), shl/sar imm5, sub, mov, be/bne/br).
usage:  python g_cave.py           (prints listings + H1; writes g_cave_<id>.hex and g_cave_out.txt)"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402,F401  (paths)
import ds_asm as A  # noqa: E402
import c1_lib as C  # noqa: E402

s32 = A.s32
RAM_A, RAM_B = A.RAM_A, A.RAM_B           # gp-0x6c44, gp-0x6c40 (V289-flown words; GATE 1 in the page)


def listing_box10(tbl, sh=6, thr=512):
    L = []

    def Ad(lab, ins, com=""):
        L.append((lab, ins, com))
    Ad("C", ("shl_i", 2, 16), "displaced 0x29D76: 4 sp")
    Ad(None, ("sub", 26, 16), "displaced 0x29D78: E = 4 sp - r26")
    # ---------------- the angle-own D operand (box10), left in r26 for 0x29EE0 (mov r26,r8) ----------------
    Ad(None, ("ld_w", -0x6CF8, 4, 9), "Honda's E_prev gp-0x6cf8 (0x7FFFFFFF after any skip tick)  [ENGAGE INIT]")
    Ad(None, ("mov_i32", A.SENT, 13), "")
    Ad(None, ("cmp", 13, 9), "Z := first PID tick")
    Ad(None, ("ld_h", -0x6A00, 4, 8), "th_h = gp-0x6a00 (0.1 deg, the 100 Hz-held angle)   [D OPERAND]")
    Ad(None, ("ld_w", RAM_A, 4, 13), "C = last seen th_h (cave RAM gp-0x6c44)")
    Ad(None, ("ld_w", RAM_B, 4, 26), "W = (-Delta << 8) + countdown (cave RAM gp-0x6c40)")
    Ad(None, ("cmovz", 8, 13, 13), "first tick: C := th_h")
    Ad(None, ("cmovz", 0, 26, 26), "first tick: W := 0")
    Ad(None, ("sub", 8, 13), "r13 = C - th_h = -Delta (the refresh's change)")
    Ad(None, ("bne", "CHG"), "a refresh changed th_h")
    Ad(None, ("andi", 0xFF, 26, 9), "countdown")
    Ad(None, ("be", "HOLD"), "0: idle, W stays 0")
    Ad(None, ("add_i5", -1, 26), "countdown - 1")
    Ad(None, ("andi", 0xFF, 26, 9), "")
    Ad(None, ("cmovz", 0, 26, 26), "expired (a zero-change refresh): W := 0")
    Ad(None, ("br", "HOLD"), "")
    Ad("CHG", ("shl_i", 8, 13), "-Delta << 8")
    Ad(None, ("add_i5", 10, 13), "+ 10 ticks")
    Ad(None, ("mov", 13, 26), "W := (-Delta << 8) + 10")
    Ad("HOLD", ("st_w", 8, RAM_A, 4), "C := th_h")
    Ad(None, ("st_w", 26, RAM_B, 4), "W")
    Ad(None, ("sar_i", 8, 26), "op = -(th_h[n] - th_h[n-10])")
    Ad(None, ("shl_i", sh, 26), f"op << {sh}  (Honda's (Kd op) >> 3 at 0x29EE4 follows)")
    A._walk(Ad)
    Ad("APPLY", ("mul", 8, 16, 0), "E * G (low word)                                 [THE SPEED GAIN]")
    Ad(None, ("sar_i", 8, 16), "E' = (E G) >> 8")
    A._freeze_branchy(Ad, thr)
    rows = []
    for (Xv, G, S) in tbl:
        rows += [("half", Xv), ("half", G), ("half", S & 0xFFFF)]
    L.append(("TBL", rows[0], "table: X u16, G u16, S s16 Q12 per row"))
    for r in rows[1:]:
        L.append((None, r, ""))
    return L


def assemble_listing(L, base=A.CAVE):
    labels = {}
    pc = base
    for lab, ins, _ in L:
        if lab:
            labels[lab] = pc
        pc += A.size(ins)
    out = bytearray()
    lines = []
    pc = base
    for lab, ins, com in L:
        hw = A.enc(ins, pc, labels)
        bs = b"".join(struct.pack("<H", h) for h in hw)
        assert len(bs) == A.size(ins)
        out += bs
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        pc += len(bs)
    return bytes(out), labels, lines


def box10_ref(tbl, sh, thr, sp, r26, v, tq, ramp, cells):
    c = dict(cells)
    G = C.cave_G(v & 0xFFFF, tbl)
    frz = (tq & 0xFFFF) > thr or (ramp & 0x8000) == 0
    first = c["6cf8"] == A.SENT
    th = c["6a00"]
    Cc = th if first else c["6c44"]
    W = 0 if first else c["6c40"]
    if s32(Cc - th) != 0:
        W = s32(s32(s32(Cc - th) << 8) + 10)
    elif W & 0xFF:
        W = s32(W - 1)
        if (W & 0xFF) == 0:
            W = 0
    c["6c44"] = th
    c["6c40"] = W
    op = s32((W >> 8) << sh)
    E = s32((sp << 2) - r26)
    Ep = s32(E * G) >> 8
    return Ep, (A.FRZ_RET if frz else A.RET), (0 if frz else None), op, c


def h1_box10(tbl, sh, code, thr=512, N=60000, seed=11):
    rng = np.random.default_rng(seed)
    bad = 0
    scratch = (6, 8, 9, 13, 16, 26)
    edges = [0, 32000, 65535] + [x + d for x, _, _ in tbl if x < 0xFFFF for d in (-1, 0, 1)]
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 50 else 32767
        r26 = int(rng.integers(-65535, 65536))
        v = int(rng.integers(0, 32001)) if k % 7 else int(rng.choice(edges))
        tq = int(rng.integers(0, 3000)) if k % 3 else int(rng.choice([0, thr - 1, thr, thr + 1, 65535]))
        ramp = int(rng.choice([0x8000, 0x8000, 0x8000, int(rng.integers(1, 0x8000))]))
        th = int(rng.choice([int(rng.integers(-4000, 4000)), 12000, -12000, int(rng.integers(-30, 30))]))
        mode = k % 5
        if mode == 0:
            Cc = th                                                  # unchanged
        elif mode == 1:
            Cc = th + int(rng.integers(-120, 121))                   # a refresh change
        else:
            Cc = int(rng.integers(-12000, 12001))
        cnt = int(rng.choice([0, 1, 2, 9, 10]))
        dl = int(rng.integers(-120, 121))
        W = 0 if (k % 7 == 0) else s32((dl << 8) + cnt)
        cells = {"6a5e": v, "4f68": tq, "6cf8": int(rng.choice([A.SENT, int(rng.integers(-800000, 800000))])),
                 "6abe": 0, "6cc4": 0, "6c44": Cc, "6c40": W, "3d30": 0, "6a00": th}
        mem = {}
        for nm, off in A.CELLS.items():
            a = (A.GP + off) & 0xFFFFFFFF
            val = cells[nm] & ((1 << (8 * A.WIDTH[nm])) - 1)
            for i in range(A.WIDTH[nm]):
                mem[a + i] = (val >> (8 * i)) & 0xFF
        for i, b in enumerate(code):
            mem[A.CAVE + i] = b
        regs = {i: int(rng.integers(-2 ** 31, 2 ** 31)) for i in range(32)}
        regs.update({0: 0, 16: sp, 26: r26, 14: ramp, 4: s32(A.GP), 6: A.RET})
        pc_exit, rr, mem2 = A.run_bytes(code, A.CAVE, regs, mem, A.CAVE)
        r16, ex, r6, op, c2 = box10_ref(tbl, sh, thr, sp, r26, v, tq, ramp, cells)
        ok = rr[16] == r16 and pc_exit == ex and (r6 is None or rr[6] == r6) and rr[26] == op
        ok = ok and all(rr[i] == regs[i] for i in range(32) if i not in scratch)
        for nm in ("6c44", "6c40"):
            a = (A.GP + A.CELLS[nm]) & 0xFFFFFFFF
            got = s32(sum(mem2[a + i] << (8 * i) for i in range(4)))
            ok = ok and got == c2[nm]
        for nm, off in A.CELLS.items():
            if nm in ("6c44", "6c40"):
                continue
            a = (A.GP + off) & 0xFFFFFFFF
            ok = ok and all(mem2[a + i] == ((cells[nm] & ((1 << (8 * A.WIDTH[nm])) - 1)) >> (8 * i)) & 0xFF
                            for i in range(A.WIDTH[nm]))
        if not ok:
            bad += 1
            if bad <= 3:
                print("   MISMATCH box10", dict(sp=sp, r26=r26, v=v, tq=tq, ramp=ramp), cells, "got", rr[16], rr[26],
                      hex(pc_exit), "want", r16, op, hex(ex))
    return bad


def build_cave(impl):
    """impl: dict(dkind, rows, sh) -> (code bytes, labels, lines)."""
    if impl["dkind"] == "fresh":
        return A.assemble("D2a", impl["rows"])
    if impl["dkind"] == "held":
        return A.assemble("B0", impl["rows"])
    return assemble_listing(listing_box10(impl["rows"], impl.get("sh", 6)))


def h1(impl, code, N=60000):
    if impl["dkind"] == "fresh":
        return A.h1_test("D2a", impl["rows"], code, N=N)
    if impl["dkind"] == "held":
        return A.h1_test("B0", impl["rows"], code, N=N)
    return h1_box10(impl["rows"], impl.get("sh", 6), code, N=N)


def main(impls=None, N=60000):
    impls = impls or json.loads((X.OUT / "g_impls.json").read_text())
    lines_out = []

    def P(s=""):
        print(s, flush=True)
        lines_out.append(s)
    res = {}
    for iid, im in impls.items():
        im = dict(im, rows=[tuple(r) for r in im["rows"]])
        code, labels, lines = build_cave(im)
        ncode = labels["TBL"] - A.CAVE
        P("=" * 118)
        P(f"{iid}: {im['note']}")
        P(f"  cave {A.CAVE:#x}..{A.CAVE + len(code):#x}: {len(code)} bytes = {ncode} code "
          f"({sum(1 for l in lines if l[2][0] != 'half')} instructions) + {len(code) - ncode} table; sha256 "
          f"{hashlib.sha256(code).hexdigest()[:16]}")
        for pc, lab, ins, bs, com in lines:
            if ins[0] == "half" and lab != "TBL":
                continue
            P(f"  {pc:#07x} {lab:6s} {bs:18s} {str(ins):40s} {com}")
        P("  table rows: " + " ".join(f"({x}, {g}, {s})" for x, g, s in im["rows"]))
        nb = h1(im, code, N=N)
        P(f"  H1: assembled bytes executed (ds_asm.run_bytes) vs the lane's cave arithmetic, {N} random inputs: "
          f"{nb} mismatches")
        (HERE / f"g_cave_{iid}.hex").write_text(code.hex(" "))
        res[iid] = dict(cave=len(code), code=ncode, table=len(code) - ncode, h1_bad=nb,
                        sha=hashlib.sha256(code).hexdigest())
    (HERE / "g_cave_out.txt").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    (X.OUT / "g_cave.json").write_text(json.dumps(res))
    return res


if __name__ == "__main__":
    main()
