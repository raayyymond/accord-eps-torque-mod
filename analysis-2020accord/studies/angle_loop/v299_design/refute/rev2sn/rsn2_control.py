# -*- coding: utf-8 -*-
"""rsn2_control.py -- C1: the rev-2 CAVE BYTES (read from the reviser's disasm-only scratch image, sha 30ff05fa asserted),
executed by the kit's V850E2 interpreter (score_time.Cpu2 via rev_h1.run_bytes), vs MY engine's Lane with the R2
variant (freeze decision + E') -- my lane, not the spec's mirror.  C2: my Lane R2 vs the S2 lane at REV2_S2 bit for
bit on random sequences (T and I).  Negatives: bytes vs my Lane at rev-1 caps; my R2 vs S2 at rev-1.  ANALYSIS ONLY."""
import contextlib, hashlib, io, sys, time
from pathlib import Path
import numpy as np
T0 = time.perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R
E = R.E
with contextlib.redirect_stdout(io.StringIO()):
    import rev_h1 as H
img = (R.KIT / "_scratch" / "v299_REV2" / "V299R2_DISASM_ONLY_NOT_AN_ARTIFACT.bin").read_bytes()
assert hashlib.sha256(img).hexdigest().startswith("30ff05fa")
code = img[0xC4C00:0xC4D04]
rng = np.random.default_rng(2026)
N = 4000
cases = []
for k in range(N):
    if k % 2:
        v = int(rng.choice([int(rng.integers(1383, 2881)), 1381, 1382, 1383, 2879, 2880, 2881]))
        th = int(rng.integers(100, 1500)) * int(rng.choice([-1, 1]))
        I8 = int(rng.integers(2000, 9000)) * 1024 * int(rng.choice([-1, 1])) + int(rng.integers(0, 1024))
    else:
        v = int(rng.integers(0, 12001))
        th = int(rng.integers(-4000, 4001))
        I8 = int(rng.integers(-8192 * 1024, 8192 * 1024))
    sp = int(rng.integers(-16000, 16001)); r26 = int(rng.integers(-60000, 60001))
    tq = int(rng.choice([int(rng.integers(-1500, 1501)), int(rng.choice([-1230, -1229, 1229, 1230, 0]))]))
    abe = int(rng.integers(-3000, 3001))
    cases.append((sp, r26, v, tq, 0x8000, th, I8, abe, 1))
a = np.array(cases, np.int64)
got = H.run_bytes(code, cases, None)
pc = np.array([g[0] for g in got]); r16 = np.array([g[1] for g in got])
okmem = all(g[4] and g[5] for g in got)


def mylane(variant_fn):
    vws = a[:, 2]
    lane = E.Lane(["V299"] * N, vws, [variant_fn(int(x)) for x in vws])
    th = a[:, 5]
    lane.s = a[:, 1] - 8 * th; lane.ok = np.ones(N, np.int64); lane.I8 = a[:, 6].copy()
    lane.tick(th, a[:, 7], a[:, 0], a[:, 3], 0x8000)
    return lane.log["frz"].astype(bool), lane.log["Ep"]


cap2w = lambda vw: dict(capv=2880, capval=4096 if vw <= 1382 else 6144)  # noqa
frz, Ep = mylane(cap2w)
fb = pc == H.NC.FRZ_RET
print(f"C1 rev-2 bytes vs MY lane (R2): freeze-decision mismatches {int((frz != fb).sum())}/{N}, E' mismatches "
      f"{int((Ep != r16).sum())}/{N}; RAM/regs clean {okmem}; FRZ {int(fb.sum())} HOOK {int((pc == H.NC.HOOK_RET).sum())}")
frz1, _ = mylane(lambda vw: {})
print(f"N1 rev-2 bytes vs MY lane at rev-1 caps: mismatches {int((frz1 != fb).sum())}/{N} (must be > 0)")
# C2: my lane R2 vs S2's lane at REV2_S2 on random sequences
S2 = R.load_s2()
speeds = [3.0, 5.0, 5.99, 6.01, 7.0, 8.0, 10.0, 12.0, 12.49, 12.51, 15.0]
cl = [v for v in speeds for _ in range(8)]
B = len(cl)
vw = np.round(np.array(cl) * 230.4).astype(np.int64)


def c2(s2cid, myvar):
    mine = E.Lane(["V299"] * B, vw, [myvar(int(x)) for x in vw])
    ref = S2.S2Lane([S2.mk_cand(s2cid)] * B, vw)
    rg = np.random.default_rng(3); th = rg.normal(0, 600, B).astype(np.int64); mm = 0; held = th; imax = 0
    for n in range(9000):
        th = np.clip(th + rg.integers(-6, 7, B), -6000, 6000)
        held = th if n % 10 == 4 or n == 0 else held
        bias = (300 if (n // 3000) % 2 == 0 else -300) * (1 if n % 2 else 1)
        sp = np.clip(held + bias + rg.integers(-100, 100, B), -6000, 6000) * 4
        abe = rg.integers(-1000, 1000, B); w = rg.normal(0, 400, B).astype(np.int64)
        ramp = 0x8000 if (n // 700) % 9 else int(rg.integers(0, 0x8000))
        x = mine.tick(held, abe, sp, w, ramp); y = ref.tick(held, held, held, abe, sp, w, ramp, 1, 1)
        mm += int(np.count_nonzero(x != y)) + int(np.count_nonzero(mine.log["I"] != ref.log["I"]))
        imax = max(imax, int(np.abs(mine.log['I']).max()))
    print('   max |I>>7| reached', imax)
    return mm


print("C2 my R2 lane vs S2 lane 'R2' (rev2 two-level):", c2("R2", cap2w))
print("N2 my R2 lane vs S2 lane 'R1N' (rev-1 caps):", c2("R1N", cap2w), "(must be > 0)")
print(f"wall {time.perf_counter() - T0:.1f} s")
