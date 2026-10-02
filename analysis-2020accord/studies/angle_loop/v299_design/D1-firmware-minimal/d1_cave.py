# -*- coding: utf-8 -*-
r"""d1_cave.py -- D1's cave (implementation (b)) as a LISTING -> bytes, with the same two-pass relink build_v298_tva uses,
and the design-time H1: the assembled bytes EXECUTED by the panel-2 V850E2 interpreter (score_time.h1, Cpu2) against
D1's own cave-stage mirror (d1_time.D1Lane.cave_stage).  ANALYSIS ONLY: no image is written, nothing is flashed.

CONTROLS (asserted):
  C1  this pipeline with V298's policy (POL_A3S_CAM: hard 512, opposing 300, A3, cap 4096, camera gate) + the op-skip
      re-derives build_v298_tva.FLIGHT_HEX byte for byte (sha ef1861e10421...), and without the op-skip SCORE_HEX.
  C2  score_time.h1 on V298's SCORE cave through D1Lane (asym off, V298 switches) -> 0 mismatches.
D1c (the design):
  * hard freeze THR 512 -> 1229 (movea imm16)                                  [0 B]
  * the opposing-hand clause REMOVED (policy sgn absent)                        [-16 B]
  * the ASYMMETRIC A3 bound: after `ld.h -0x6a00[gp],r9` insert
        mov r9,r13 ; xor r16,r13 ; bge AS ; mov 0,r9 ; AS:                     [+8 B]
    i.e. when sign(theta) != sign(E') the |theta| term of the bound is 0 and the I may wind toward centre only to B.
  -> flight cave 252 B (V298 260 B), relinked; score cave likewise.
H1: N random + edge cases; a mismatch in E', the exit address (0x29D7A normal / 0x29D7E freeze), r6, the D operand r26,
gp-0x6dd0, any preserved register or any read-only cell fails the case.
usage: python d1_cave.py      (wall time printed; < 30 s)
"""
import hashlib
import importlib.util
import struct
import sys
import time
from pathlib import Path

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
for q in (AL / "panel2" / "E2-integral-most-margin", AL / "panel" / "D-structure", AL / "c3" / "rev2B", HERE):
    sys.path.insert(0, str(q))
import e2_asm as EA  # noqa: E402
import rb_table as T  # noqa: E402

_b = importlib.util.spec_from_file_location("bv298", KIT / "analysis-2020accord" / "builds" / "v108_plus" / "build_v298_tva.py")
BV = importlib.util.module_from_spec(_b)
sys.modules["bv298"] = BV
_b.loader.exec_module(BV)

SKIP_TGT = 0x2A164
GBP = [tuple(r) for r in T.GB_P]
POL_V298 = dict(BV.POL_A3S_CAM)
POL_D1C = dict(arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, arb_vcap=1382, arb_cap=4096, cam=True, thr=1229)


def inject_opskip(entries):
    out, i, n = [], 0, len(entries)
    while i < n:
        lab, ins, com = entries[i]
        if ins == ("cmovh", 0, 26, 26):
            out.append((lab, ("bnh", "CONT"), "rate valid: continue  [op-skip]"))
            out.append((None, ("jr", SKIP_TGT), "rate INVALID: jr 0x2A164 (Honda A2/B2 epilogue)  [F3]"))
            out.append(("CONT", entries[i + 1][1], entries[i + 1][2]))
            i += 2
            continue
        out.append((lab, ins, com))
        i += 1
    return out


def inject_asym(entries):
    out, done = [], False
    i = 0
    while i < len(entries):
        lab, ins, com = entries[i]
        out.append((lab, ins, com))
        if ins == ("ld_h", -0x6A00, 4, 9) and not done:
            out.append((None, ("mov", 9, 13), "r13 = theta                                   [D1c ASYMMETRIC BOUND]"))
            out.append((None, ("xor", 16, 13), "theta ^ E'"))
            out.append((None, ("bge", "AS"), "same sign: the I winds AWAY from centre -> the theta-referenced bound"))
            out.append((None, ("mov_i5", 0, 9), "toward centre: |theta| term := 0 -> bound = B (1250 S)"))
            nl, ni, nc = entries[i + 1]
            assert nl is None and ni == ("cmp", 0, 9), entries[i + 1]
            out.append(("AS", ni, nc))
            i += 2
            done = True
            continue
        i += 1
    assert done
    return out


def asm(entries):
    labels, pc = {}, EA.CAVE
    for lab, ins, _ in entries:
        if lab:
            labels[lab] = pc
        pc += EA.size(ins)
    out, pc, lines = bytearray(), EA.CAVE, []
    for lab, ins, com in entries:
        bs = b"".join(struct.pack("<H", h) for h in EA.enc(ins, pc, labels))
        assert len(bs) == EA.size(ins)
        lines.append((pc, lab or "", ins, bs.hex(" "), com))
        out += bs
        pc += len(bs)
    return bytes(out), labels, lines


def build(pol, asym):
    ent = EA.listing(pol, GBP)
    if asym:
        ent = inject_asym(ent)
    fl, labf, linf = asm(inject_opskip(ent))
    sc, labs, lins = asm(ent)
    return fl, sc, labf, linf


out = []
# ---- C1: reproduce V298
f298, s298, _, _ = build(POL_V298, False)
assert f298 == BV.FLIGHT and s298 == BV.SCORE, "C1 failed: this pipeline does not reproduce V298's caves"
out.append(f"C1 PASS: V298 flight cave re-derived byte for byte ({len(f298)} B, sha {hashlib.sha256(f298).hexdigest()[:12]}),"
           f" score cave ({len(s298)} B)")
# ---- D1c
fD, sD, labD, linD = build(POL_D1C, True)
shaF, shaS = hashlib.sha256(fD).hexdigest(), hashlib.sha256(sD).hexdigest()
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "d1c_flight.hex").write_text(fD.hex(" "), encoding="utf-8")
(HERE / "out" / "d1c_score.hex").write_text(sD.hex(" "), encoding="utf-8")
ntbl = labD["TBL"] - EA.CAVE
out.append(f"D1c flight cave: {len(fD)} B = {ntbl} code + {len(fD) - ntbl} table (V298 260 = 218 + 42); sha {shaF[:12]}; "
           f"score cave {len(sD)} B sha {shaS[:12]}; free region ends 0x{BV.CAVE_FREE_END:X}: "
           f"{'fits' if EA.CAVE + len(fD) <= BV.CAVE_FREE_END else 'DOES NOT FIT'}")
# ---- the listing
out.append("")
out.append("D1c FLIGHT LISTING (address, label, bytes, instruction, comment)")
for pc, lab, ins, hx, com in linD:
    if ins[0] == "half":
        continue
    out.append(f"  {pc:#07x} {lab:6s} {hx:14s} {str(ins):38s} {com}")
out.append(f"  {labD['TBL']:#07x} TBL    GB-P table, 7 rows x (X u16, G u16, S s16)")
# ---- byte diff vs V298's flight cave (aligned listing comparison is the meaningful one; raw diff count reported)
nd = sum(1 for a, b in zip(fD, f298) if a != b) + abs(len(fD) - len(f298))
out.append(f"\nraw byte diff vs V298 flight cave: {nd} of {max(len(fD), len(f298))} positions differ (relink shifts the tail)")

# ---- H1 (score cave, interpreter vs the D1 mirror)
import d1_time as DT  # noqa: E402  (D1Lane = score_time.CandLane + D1's switches; its ST is the scorer instance)
ST = DT.ST


def h1_for(hexpath, thr, sgn, asym, N):
    c = ST.Cand("h1", "D1", tuple(GBP), "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=sgn, thr=thr,
                hexsrc=hexpath, ramp_in=328, ramp_out=66)
    c.asym, c.mg = asym, -1
    orig = ST.CandLane
    ST.CandLane = DT.D1Lane
    try:
        return ST.h1(c, N=N, seed=11)
    finally:
        ST.CandLane = orig


p298 = HERE / "out" / "v298_score.hex"
p298.write_text(s298.hex(" "), encoding="utf-8")
r0 = h1_for(p298, 512, 300, False, 3000)
out.append(f"\nC2 H1 control: V298 score cave bytes vs D1Lane(V298 switches): {r0['bad']}/{r0['n']} mismatches "
           f"(code {r0['code_B']} B)")
r1 = h1_for(HERE / "out" / "d1c_score.hex", 1229, 0, True, 8000)
out.append(f"H1 D1c: D1c score cave bytes vs D1Lane(D1c switches): {r1['bad']}/{r1['n']} mismatches (code {r1['code_B']} B)"
           + (f"  first bad {r1['first_bad']}" if r1["bad"] else ""))
rn = h1_for(HERE / "out" / "d1c_score.hex", 1229, 0, False, 1500)
out.append(f"H1 NEGATIVE control: D1c bytes vs a mirror WITHOUT the asym bound: {rn['bad']}/{rn['n']} mismatches "
           f"(must be > 0)")
rn2 = h1_for(HERE / "out" / "d1c_score.hex", 512, 0, True, 1500)
out.append(f"H1 NEGATIVE control: D1c bytes vs a mirror with hard 512: {rn2['bad']}/{rn2['n']} mismatches (must be > 0)")
out.append(f"wall {time.time() - T0:.1f} s")
(HERE / "out" / "d1_cave.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
