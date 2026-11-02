# -*- coding: utf-8 -*-
# KIT COPY (2026-11-01, T6) of scratchpad t4/h1_a340.py (agent cave-asm-2, T4c); changed only the import path / the A340 bytes source
# (re-assembled from the listing instead of read from cave_a340.hex).  Called by build_v300_a340.py.
"""h1_a340.py -- H1: the assembled cave bytes EXECUTED by e2_asm.run_bytes (V850E2 subset interpreter, read-only import)
vs an independent scalar re-statement of the V299/V300 rev-2 policy (cave_ref below).
CONTROL: the same reference in A160 mode vs V300's FLOWN-CLASS image cave bytes (A160 regs/offsets/full G, sar 6).
TEST:    A340 mode vs cave_a340.hex (halved G, sar 7, A340 regs/offsets, exits 0x2A344/0x2A348/0x2A596, link r7).
Checks per input: exit pc, E' reg, r26, freeze-out reg (on FRZ exits), every non-scratch register unchanged, memory unchanged.
usage: python h1_a340.py [N]"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a340_cave_listing as CL  # noqa: E402
EA = CL.EA
GP = 0xFEDF8000
s32 = EA.s32
QUIET = [False]


def gval(v, tbl):
    if v <= tbl[0][0]:
        return tbl[0][1]
    i = 0
    while not v <= tbl[i + 1][0]:
        i += 1
    X, G, S = tbl[i]
    return G + (s32((v - X) * S) >> 12)


def cave_ref(m, sp, r26, c, r25, ramp):
    """returns (exit, E_out, r26_out, fo_or_None)"""
    E = s32((sp << 2) - r26)
    op = c["rate"]
    if ((op + 13000) & 0xFFFFFFFF) > 26000:
        return m["SKIP"], E, op, None
    v = c["spd"]
    Ep = s32(E * gval(v, m["TBL"])) >> 8
    if r25 == 0:
        return m["FRZ"], 0, 0, s32(-(c["I"] >> m["CAMSAR"]))
    if c["hand"] > 1229:
        return m["FRZ"], Ep, op, 0
    th = c["ang"]
    if Ep < 0:
        th = -th
    if th < 0:
        th = 0
    if v > 2880:
        bound = (th << 6) + 1250
    else:
        bound = (th << 4) + 1250
        cap = 4096 if v <= 1382 else 6144
        if bound > cap:
            bound = cap
    t = c["I"] >> 10
    if Ep < 0:
        t = -t
    if t >= bound:
        return m["FRZ"], Ep, op, 0
    if (ramp & 0x8000) == 0:
        return m["FRZ"], Ep, op, 0
    return m["RET"], Ep, op, None


def run(mode, code, N, seed):
    m = CL.MODES[mode]
    off = {"rate": (m["RATE"], 2), "spd": (m["SPD"], 2), "hand": (m["HAND"], 2), "ang": (m["ANG"], 2),
           "I": (m["ISTATE"], 4)}
    scratch = {m["E"], m["P"], m["V"], m["K"], 26, m["FO"]}
    knots = [x + d for x, _, _ in m["TBL"] if x < 0xFFFF for d in (-1, 0, 1)] + [1381, 1382, 1383, 2879, 2880, 2881, 0, 65535]
    rng = np.random.default_rng(seed)
    bad, hist = 0, {}
    for k in range(N):
        sp = int(rng.integers(-32768, 32768)) if k % 9 else int(rng.choice([16384, -16384, 32767, -32768, 0]))
        r26 = int(rng.integers(-70000, 70000)) if k % 11 else int(rng.integers(-2 ** 31, 2 ** 31))
        v = int(rng.integers(0, 12001)) if k % 3 else int(rng.choice(knots))
        hand = int(rng.integers(0, 3000)) if k % 4 else int(rng.choice([0, 1228, 1229, 1230, 65535]))
        ang = int(rng.integers(-12000, 12001)) if k % 5 else int(rng.choice([0, 1, -1, 32767, -32768]))
        I = int(rng.integers(-(1 << 24), 1 << 24)) if k % 6 else int(rng.integers(-2 ** 31, 2 ** 31))
        if k % 2:                         # put t right at the bound often
            th = abs(ang)
            b = ((th << 6) if v > 2880 else min((th << 4) + 1250, 4096 if v <= 1382 else 6144) - 1250) + 1250
            I = int(rng.choice([b, b - 1, b + 1, -b, -b - 1, -b + 1])) * 1024 + int(rng.integers(0, 1024))
            I = max(-2 ** 31, min(2 ** 31 - 1, I))
        rate = int(rng.integers(-13000, 13001)) if k % 8 else int(rng.choice([-13001, -13000, 13000, 13001, 32767, -32768]))
        c = dict(rate=rate, spd=v, hand=hand, ang=ang, I=I)
        mem = {}
        for nm, (o, w) in off.items():
            a, val = (GP + o) & 0xFFFFFFFF, c[nm] & ((1 << (8 * w)) - 1)
            for i in range(w):
                mem[a + i] = (val >> (8 * i)) & 0xFF
        for i, b_ in enumerate(code):
            mem[CL.CAVE + i] = b_
        regs = {i: int(rng.integers(-2 ** 31, 2 ** 31)) for i in range(32)}
        ramp = int(rng.choice([0x8000, 0x8000, int(rng.integers(0, 0x8000)), int(rng.integers(-2 ** 31, 2 ** 31))]))
        r25 = int(rng.choice([0, 1, int(rng.integers(-2 ** 31, 2 ** 31))]))
        regs.update({0: 0, m["E"]: sp, 26: r26, 14: ramp, 25: r25, 4: s32(GP), m["LINK"]: m["RET"]})
        pc, rr, mem2 = EA.run_bytes(code, CL.CAVE, regs, dict(mem), CL.CAVE, stop_at=(m["RET"], m["FRZ"], m["SKIP"]))
        ex, Eo, r26o, fo = cave_ref(m, sp, r26, c, r25, ramp)
        ok = pc == ex and rr[m["E"]] == Eo and rr[26] == r26o and (fo is None or rr[m["FO"]] == fo)
        ok = ok and all(rr[i] == regs[i] for i in range(32) if i not in scratch) and mem2 == mem
        hist[hex(pc)] = hist.get(hex(pc), 0) + 1
        if not ok:
            bad += 1
            if bad <= 3:
                if not QUIET[0]: print("  MISMATCH", mode, dict(sp=sp, r26=r26, r25=r25, ramp=ramp), c, "got", hex(pc), rr[m["E"]],
                      rr[26], rr[m["FO"]], "want", hex(ex), Eo, r26o, fo)
    return bad, hist


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    a160, _, _ = CL.assemble(CL.MODES["A160"])
    assert CL.sha(a160) == CL.EXP_A160_SHA
    b, h = run("A160", a160, N, 7)
    print(f"CONTROL (reference vs V300 flown-class cave bytes, A160 mode): {b} mismatches / {N}; exits {h}")
    code = bytes.fromhex(CL.assemble(CL.MODES["A340"])[0].hex())
    b2, h2 = run("A340", code, N, 11)
    print(f"H1 (A340 bytes vs A340 reference): {b2} mismatches / {N}; exits {h2}")
    QUIET[0] = True
    # NEGATIVE CONTROLS: the harness must FAIL on a wrong reference (CAM sar 6; un-halved G; A160 link)
    for nm, patch in (("CAMSAR=6", dict(CAMSAR=6)), ("G not halved", dict(TBL=CL.V300_TBL)), ("FRZ thr via r6 link", dict(LINK=6))):
        saved = dict(CL.MODES["A340"])
        CL.MODES["A340"].update(patch)
        try:
            bn, _ = run("A340", code, 2000, 5)
        except Exception as e:
            bn = f"harness raised {type(e).__name__}"
        CL.MODES["A340"].clear(); CL.MODES["A340"].update(saved)
        print(f"  NEGATIVE CONTROL [{nm}]: {bn} mismatches / 2000 (must be > 0)")
    # G' vs G/2 deviation over every v
    t160, t340 = CL.MODES["A160"]["TBL"], CL.MODES["A340"]["TBL"]
    dev = [(gval(v, t340) - gval(v, t160) / 2, v) for v in range(65536)]
    mx = max(dev, key=lambda d: abs(d[0]))
    rel = max((abs(gval(v, t340) - gval(v, t160) / 2) / (gval(v, t160) / 2), v) for v in range(65536))
    print(f"G'(v) - G(v)/2 over v in [0,65535]: max |dev| {abs(mx[0]):.1f} counts at v={mx[1]} "
          f"(G'={gval(mx[1], t340)}, G/2={gval(mx[1], t160) / 2}); max relative {rel[0] * 100:.3f}% at v={rel[1]}")


if __name__ == "__main__":
    main()
