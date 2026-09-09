# -*- coding: utf-8 -*-
"""ADVERSARY C -- V289 rev 1 -- does the INIT_ON_SENTINEL=True path (a) assemble, (b) behave, (c) pass the
script's own gates?  The docstring says the prologue is "encoded and unit-tested but NOT emitted".

Imports the builder as a module (no write mode is ever set) and uses ITS emulator on the init=True bytes,
because the question is about the builder's own switch, not about the flashed image.
"""
import os
import sys
from pathlib import Path

os.environ.pop("ACCORD_V289_WRITE", None)
here = Path(__file__).resolve()
sys.path.insert(0, str(here.parents[1] / "builds" / "v108_plus"))
import build_v289_tva as B   # noqa: E402

base = bytearray(Path(B.plain_image_path(B.BASE_NAME)).read_bytes())
notch = B.notch_cave(init=True)
nb = b"".join(by for _, by, _, _ in notch)
plain = b"".join(by for _, by, _, _ in B.notch_cave(init=False))
print(f"init=True cave: {len(nb)} B / {len(notch)} instr ; init=False: {len(plain)} B")
print("prologue bytes:", nb[:26].hex())
for a, by, mn, cm in notch[:8]:
    print(f"  0x{a:05X} {by.hex():<12} {mn}")
assert nb[26:-4] == plain[:-4] and nb[-4:] != plain[-4:], "body after the prologue == shipped body except the pc-relative final jr"
# bne target: prologue = ld.w(4) mov32(6) cmp(2) bne(2) st.w x3 (12) -> bne at +12 must land at +26
bne_at = B.NOTCH + 12
n_, txt = B.decode_one(nb + b"\0" * 8, 12)
print("bne decodes (pc-relative from offset 12):", txt, "-> target offset", int(txt.split()[1], 16))
assert int(txt.split()[1], 16) == 26, "bne must skip exactly the three st.w"

sim = bytearray(base)
sim[B.HOOK:B.HOOK + 4] = B.jr(B.HOOK, B.NOTCH)
sim[B.NOTCH:B.NOTCH + len(nb)] = nb
simb = bytes(sim)


def tick(mem, x):
    r12, regs, mem, steps, e = B.emu_tick(simb, x, mem)
    return r12, mem, steps


# (b) behaviour: seed a non-zero state; with the sentinel absent the state must persist, with it present it zeroes
for sentinel in (0, 0x7FFFFFFF, 0x7FFFFFFE, -1 & 0xFFFFFFFF):
    mem = {}
    B.set_state(mem, 123456, -654321, 4095, 0xA0)
    for i in range(4):
        mem[B.GP_BASE + B.EINIT_CELL_DISP + i] = (sentinel >> (8 * i)) & 0xFF
    st_before = B.mem_state(mem)
    r12, mem, steps = tick(mem, 0)
    s1, s2, e, fl = B.mem_state(mem)
    # after one tick with x = 0 from zeroed state the mirror gives y = 0 and state stays 0
    mirror = [0, 0, 0] if sentinel == 0x7FFFFFFF else [123456, -654321, 4095]
    yo, y, n, flag = B.notch_tick(0, mirror)
    ok = (r12 == yo and (s1, s2, e, fl) == (mirror[0], mirror[1], mirror[2], flag))
    print(f"sentinel 0x{sentinel:08X}: state before {st_before} -> after {(s1, s2, e, fl)}, r12 {r12}, {steps} instr ; "
          f"{'zeroed' if sentinel == 0x7FFFFFFF else 'kept'} as designed: {ok}")
    assert ok

# live registers untouched, r7 == 507 on both arms
for sentinel in (0, 0x7FFFFFFF):
    mem = {}
    B.set_state(mem, 1, 2, 3)
    for i in range(4):
        mem[B.GP_BASE + B.EINIT_CELL_DISP + i] = (sentinel >> (8 * i)) & 0xFF
    r12, regs, mem, steps, e = B.emu_tick(simb, 777, mem)
    assert all(regs[r] == (0x51A7E000 + r * 0x01010101) & 0xFFFFFFFF for r in B.LIVE_ACROSS_HOOK)
    assert B._s32(regs[B.R7]) == 507
print("live registers preserved and r7 == 507 on both prologue arms")

# (c) the script's own gates with the switch on: [4](x) and [4d] as written
n_bytes = len(nb)
# With the switch True, `notch_bytes` in build() comes from notch_cave() whose DEFAULT init is the switch itself, so
# both operands of [4](x) are the 166-byte cave: `len(pro) == len(notch) + 26` is 166 == 192 -> FAIL.  (Confirmed
# empirically on a scratch copy with the constant flipped: the run stops at [4](x) with exit 1.)
x_gate = (len(nb) == len(nb) + 26)
print(f"[4](x) as written would pass with INIT_ON_SENTINEL=True: {x_gate}  <- both operands are notch_cave(init=True)")
doc = B.__doc__
print(f"[4d] docstring guard would pass ('140 bytes, 52 instructions' vs {len(nb)} bytes, {len(notch)} instructions): "
      f"{f'{len(nb)} bytes, {len(notch)} instructions' in doc}")
print("VERDICT: the prologue ASSEMBLES and BEHAVES (zeroes on the sentinel only, live regs intact), but the script's own"
      " [4](x) and [4d] gates FAIL when the switch is flipped -> the switch cannot produce a build without editing two assertions"
      " and the docstring; 'unit-tested' in the docstring means a LENGTH check only -- no behavioural test exists in the script.")
