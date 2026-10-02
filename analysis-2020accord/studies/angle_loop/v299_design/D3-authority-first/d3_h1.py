# -*- coding: utf-8 -*-
r"""d3_h1.py -- D3 (a) firmware bytes: the V298 FLIGHT cave (0xC4C00..0xC4D03, 260 B, read from the V298 image) with
D3's in-place edits applied, EXECUTED by the kit's independent V850E2 interpreter (refute_c2r2_nonlinear/nl_cave.Cpu +
panel2/score_time.Cpu2) and compared with the time scorer's integer mirror CandLane.cave_stage.  ANALYSIS ONLY.

D3 (a) edits inside the cave (no instruction added, removed or moved; no relink; same 260 B):
  0xC4C64  movea imm16  0x0200 (512)  -> 0x04CD (1229)   hard hand freeze  |gp-0x4f68| > 1229 (= 1200 raw x 1.024)
  0xC4C6C  movea imm16  0x012C (300)  -> 0x0320 (800)    opposing-hand freeze |tq| > 800 and sign(tq) != sign(E')
  0xC4CDA  row 0 G 1178 -> 1414, S 1041 -> 185 ; row 1 (X 1843) unchanged (G 1465, S -6264)   G x1.2 @3.1 -> x1.0 @8.0
Per case the interpreter's exit and registers are checked against the mirror:
  valid rate, armed (r25 != 0): r16 = E', exit 0x29D7A (run) / 0x29D7E (freeze), r6 = 0 at the freeze exit, r26 = op,
                                 no RAM written, every non-scratch register unchanged;
  invalid rate (|gp-0x6abe| > 13000 or 0x7FFF): exit 0x2A164 (Honda's skip epilogue), no RAM written;
  camera frame (r25 == 0): exit 0x29D7E with r16 = 0, r26 = 0, r6 = -(I8 >> 6).
Controls: V298 bytes vs V298 cells (must be 0), and both cross pairings (must be > 0 -- the check can fail).
usage: python d3_h1.py  -> _scratch/angle_loop/v299-D3/h1.txt
"""
import contextlib
import hashlib
import io
import struct
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AL / "panel2"))
import d3_common as D  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import score_time as ST  # noqa: E402
NC = ST.NC
GP = ST.GP
SKIP = 0x2A164


def d3_cave(img):
    cave = bytearray(img[0xC4C00:0xC4C00 + 260])
    assert hashlib.sha256(bytes(cave)).hexdigest().startswith("ef1861e10421"), "not the V298 flight cave"
    assert cave[0x64:0x66] == struct.pack("<H", 512) and cave[0x6C:0x6E] == struct.pack("<H", 300)
    cave[0x64:0x66] = struct.pack("<H", 1229)
    cave[0x6C:0x6E] = struct.pack("<H", 800)
    rows = D.scaled_rows(1.2, mult_8=1.0)
    t = 0xC4CDA - 0xC4C00
    for i, (X, G, S_) in enumerate(rows):
        cave[t + 6 * i:t + 6 * i + 6] = struct.pack("<HHh", X, G, S_)
    return bytes(cave), rows


def run_h1(code, cand, N, seed, thr_edges):
    rng = np.random.default_rng(seed)
    knots = [r[0] for r in cand.rows if r[0] < 0xFFFF]
    cases = []
    for k in range(N):
        sp = int(rng.integers(-16384, 16385)) if k % 40 else 32767
        r26 = int(rng.integers(-65535, 65536))
        v = int(rng.integers(0, 12001)) if k % 5 else int(np.clip(rng.choice(knots + [1382, 2880]) + rng.integers(-1, 2),
                                                                      0, 12000))
        tq = int(rng.choice([int(rng.integers(-3000, 3001)), int(rng.choice(thr_edges))]))
        ramp = int(rng.choice([0x8000, 0x8000, int(rng.integers(0, 0x8000)), 0xFFFF]))
        th = int(rng.choice([int(rng.integers(-4000, 4001)), int(rng.integers(-40, 41))]))
        I8 = int(rng.choice([int(rng.integers(-12288 * 1024, 12288 * 1024)), int(rng.integers(-2 ** 20, 2 ** 20)), 0]))
        abe = int(rng.choice([int(rng.integers(-13000, 13001)), int(rng.integers(-500, 501)), 13000, -13000,
                              13001, -13001, 0x7FFF, int(rng.integers(-32768, 32768))]))
        r25 = 0 if k % 9 == 0 else 1
        cases.append((sp, r26, v, tq, ramp, th, I8, abe, r25))
    a = np.array(cases, np.int64)
    lane = ST.CandLane([cand] * N, a[:, 2])
    cv = lane.cave_stage(ST.s16(a[:, 0]), a[:, 1], a[:, 4], a[:, 5], a[:, 7], ST.s16(a[:, 3]), a[:, 6],
                         np.full(N, ST.SENT32, np.int64), np.zeros(N, np.int64), np.zeros(N, np.int64))
    bad = {"valid": 0, "skip": 0, "cam": 0}
    nn = {"valid": 0, "skip": 0, "cam": 0}
    first = None
    for i, (sp, r26, v, tq, ramp, th, I8, abe, r25) in enumerate(cases):
        vals = dict(abe=abe, v=v, a4f68=min(abs(tq), 0xFFFF), tq=tq, th=th, I8=I8, Ep6=ST.SENT32, C6=0, W6=0, x=0)
        key = {"6abe": "abe", "6a5e": "v", "4f68": "a4f68", "4f60": "tq", "6a00": "th", "6dd0": "I8", "6cf8": "Ep6",
               "6c44": "C6", "6c40": "W6", "6a56": "x"}
        ram = {(GP + off) & NC.M32: (vals[key[nm]] & ((1 << (8 * w)) - 1), w) for nm, (off, w) in ST.CELLS.items()}
        regs = {16: sp, 26: r26, 14: ramp, 25: r25}
        junk = {q: int(rng.integers(0, 2 ** 32)) for q in range(1, 32) if q not in (4, 6, 14, 16, 25, 26)}
        regs.update(junk)
        mem = {0xC4C00 + j: b for j, b in enumerate(code)}
        for ad, (val, w) in ram.items():
            for q in range(w):
                mem[(ad + q) & NC.M32] = (val >> (8 * q)) & 0xFF
        mem0 = dict(mem)
        cpu = ST.Cpu2(mem)
        for q, v_ in regs.items():
            cpu.r[q] = v_ & NC.M32
        cpu.r[4] = GP
        cpu.r[6] = NC.HOOK_RET
        pc = 0xC4C00
        for _ in range(600):
            if not (0xC4C00 <= pc < 0xC4C00 + len(code)):
                break
            pc = cpu.step(pc)
        ab16 = ((abe + 0x8000) & 0xFFFF) - 0x8000
        valid = abs(ab16) <= 13000
        ram_same = all(cpu.mem.get(ad, None) == mem0.get(ad, None) for ad in mem0)
        regs_ok = all(cpu.r[q] == (regs[q] & NC.M32) for q in regs if q not in ST.SCRATCH) and cpu.r[4] == GP
        if not valid:
            cls = "skip"
            ok = pc == SKIP and ram_same and regs_ok
        elif r25 == 0:
            cls = "cam"
            ok = (pc == NC.FRZ_RET and NC.s32(cpu.r[16]) == 0 and NC.s32(cpu.r[26]) == 0
                  and NC.s32(cpu.r[6]) == NC.s32(-(I8 >> 6)) and ram_same and regs_ok)
        else:
            cls = "valid"
            frz = bool(cv["frz"][i] | cv["leak"][i])
            ok = (NC.s32(cpu.r[16]) == int(cv["Ep"][i]) and pc == (NC.FRZ_RET if frz else NC.HOOK_RET)
                  and (not frz or NC.s32(cpu.r[6]) == int(cv["r6"][i])) and NC.s32(cpu.r[26]) == int(cv["op"][i])
                  and ram_same and regs_ok)
        nn[cls] += 1
        if not ok:
            bad[cls] += 1
            if first is None:
                first = dict(cls=cls, case=cases[i], pc=hex(pc), r16=NC.s32(cpu.r[16]))
    return bad, nn, first


def main():
    t0 = time.time()
    img = D.v298_image()
    D.assert_v298(img)
    code298 = img[0xC4C00:0xC4C00 + 260]
    code_d3, rows = d3_cave(img)
    diff = [(0xC4C00 + i, code298[i], code_d3[i]) for i in range(260) if code298[i] != code_d3[i]]
    A3 = (6, 4, 2880, 1250, 1382, 4096)
    c298 = ST.Cand("V298", "E2", D.GB_P, "fresh", kd=48, kp=112, ki=40, icl=8192, thr=512, sgn_thr=300, arb=A3)
    cd3 = replace(c298, id="D3a", rows=rows, thr=1229, sgn_thr=800)
    edges = [-1230, -1229, -801, -800, -513, -512, -301, -300, 0, 300, 301, 512, 513, 800, 801, 1229, 1230, -32768, 32767]
    L = ["D3 H1: V298 FLIGHT cave bytes (+ D3 (a) in-place edits) executed by nl_cave.Cpu/Cpu2 vs CandLane.cave_stage",
         f"V298 cave sha256 {hashlib.sha256(code298).hexdigest()[:16]}  D3a cave sha256 "
         f"{hashlib.sha256(code_d3).hexdigest()[:16]}  bytes changed {len(diff)}: "
         + ", ".join(f"0x{a:05X} {o:02x}->{n:02x}" for a, o, n in diff)]
    for nm, code, cand, N in (("V298 bytes vs V298 mirror (control)", code298, c298, 1500),
                              ("D3a bytes vs D3a mirror (THE CHECK)", code_d3, cd3, 12000),
                              ("V298 bytes vs D3a mirror (negative control)", code298, cd3, 1500),
                              ("D3a bytes vs V298 mirror (negative control)", code_d3, c298, 1500)):
        bad, nn, first = run_h1(code, cand, N, 7, edges)
        L.append(f"  {nm:45s}: mismatches valid {bad['valid']}/{nn['valid']}, op-skip {bad['skip']}/{nn['skip']},"
                 f" camera {bad['cam']}/{nn['cam']}" + (f"   first {first}" if first and "THE CHECK" in nm else ""))
        print(L[-1], flush=True)
    L.append(f"wall time {time.time() - t0:.1f} s")
    print(L[-1])
    (D.OUT / "h1.txt").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
