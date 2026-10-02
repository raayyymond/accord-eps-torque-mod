"""rev_h1_regs.py -- exit-register equivalence, rev 2 vs rev 1 bytes on the SAME cases (interpreter): r8 (= v-word on the
CAC paths), r13, r16, r26, r6 and the exit pc must be identical on every case; r9 (the A3 bound) may differ only where the
two caps differ (1382 < v <= 2880 and the bound above 4096).  Random + targeted cases.  ANALYSIS ONLY."""
import sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_h1 as H
T0 = time.time()
r1 = bytes.fromhex((H.OUT / "rev1_cave.hex").read_text().replace(" ", ""))
r2 = bytes.fromhex((H.OUT / "rev2_cave.hex").read_text().replace(" ", ""))
C = H.cases(1500, 41, H.DT.GBP) + H.cases_targeted(1500, 42)


def regs(code):
    rng = np.random.default_rng(99)
    out = []
    for (sp, r26, v, tq, ramp, th, I8, abe, r25) in C:
        vals = dict(abe=abe, v=v, a4f68=min(abs(tq), 0xFFFF), tq=tq, th=th, I8=I8, Ep6=H.ST.SENT32, C6=0, W6=0, x=0)
        key = {"6abe": "abe", "6a5e": "v", "4f68": "a4f68", "4f60": "tq", "6a00": "th", "6dd0": "I8", "6cf8": "Ep6",
               "6c44": "C6", "6c40": "W6", "6a56": "x"}
        mem = {0xC4C00 + j: b for j, b in enumerate(code)}
        for nm, (off, w) in H.ST.CELLS.items():
            val = vals[key[nm]] & ((1 << (8 * w)) - 1)
            for q in range(w):
                mem[(H.GP + off + q) & H.NC.M32] = (val >> (8 * q)) & 0xFF
        cpu = H.ST.Cpu2(mem)
        init = {16: sp, 26: r26, 14: ramp, 25: r25}
        init.update({q: int(rng.integers(0, 2 ** 32)) for q in range(1, 32) if q not in (4, 6, 14, 16, 25, 26)})
        for q, v_ in init.items():
            cpu.r[q] = v_ & H.NC.M32
        cpu.r[4] = H.GP
        cpu.r[6] = H.NC.HOOK_RET
        pc = 0xC4C00
        for _ in range(600):
            if not (0xC4C00 <= pc < 0xC4C00 + len(code)):
                break
            pc = cpu.step(pc)
        out.append((pc, cpu.r[8], cpu.r[9], cpu.r[13], cpu.r[16], cpu.r[26], cpu.r[6]))
    return out


a, b = regs(r1), regs(r2)
same = [i for i in range(len(C)) if a[i][0] == b[i][0] and a[i][1] == b[i][1] and a[i][3:] == b[i][3:]]
r9d = [i for i in range(len(C)) if a[i][2] != b[i][2]]
in_band = [i for i in r9d if 1382 < (C[i][2] & 0xFFFF) <= 2880]
print(f"cases {len(C)}: pc/r8/r13/r16/r26/r6 identical on {len(same)}; r9 differs on {len(r9d)}, of which in 1382<v<=2880: "
      f"{len(in_band)}; r9 rev1 >= 4096 there: {all(int(a[i][2]) > 4096 or int(b[i][2]) != int(a[i][2]) for i in in_band)}")
print(f"exit-pc differs on {sum(a[i][0] != b[i][0] for i in range(len(C)))} cases (the cap changes the freeze decision)")
print(f"wall {time.time() - T0:.1f} s")
