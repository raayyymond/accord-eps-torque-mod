"""v77 GATE 2 -- FULL byte diff V74 -> V75 (and V74 -> stock context).

The brief names the damper relay as the leading explanation for V75's hard fault. Before I accept
that, I need to know whether the relay is the ONLY thing that changed. Code caves are this kit's
only bricking class (V24/V27/V48B), so a cave delta is a competing hypothesis of equal standing.
Pure Python byte reads, LE.
"""
from pathlib import Path
import struct

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord")
V74 = (ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin").read_bytes()
V75 = (ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin").read_bytes()
V76 = (ROOT / "_v76_gate_fb_arm5244_gateprobe_plain_image.bin").read_bytes()
STK = (ROOT / "stock_fw_dump" / "code.bin").read_bytes()

CAVE_BASE, CAVE_EXTENT = 0xC4B34, 68


def runs(a, b, gap=8):
    """Contiguous differing byte runs, merged across gaps <= `gap`."""
    d = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    if not d:
        return []
    out, s, p = [], d[0], d[0]
    for i in d[1:]:
        if i - p <= gap:
            p = i
        else:
            out.append((s, p))
            s = p = i
    out.append((s, p))
    return out


def classify(lo, hi):
    if CAVE_BASE <= lo < CAVE_BASE + 256:
        return "CAVE (code)"
    if lo < 0x13000:
        return "below flash window"
    if 0xC0000 <= lo < 0xCE000:
        return "tp-relative cal block"
    if 0xD0000 <= lo < 0xD8000:
        return "mode-indexed RECORD block"
    if lo < 0xC0000:
        return "CODE"
    return "other"


for label, A, B in (("V74 -> V75", V74, V75), ("V74 -> V76", V74, V76)):
    r = runs(A, B)
    total = sum(h - l + 1 for l, h in r)
    print("=" * 100)
    print(f"{label}:  {len(r)} runs, {total} differing bytes")
    print("=" * 100)
    for lo, hi in r:
        n = hi - lo + 1
        tag = classify(lo, hi)
        old = A[lo:hi + 1].hex()
        new = B[lo:hi + 1].hex()
        if n <= 24:
            print(f"  0x{lo:06X}..0x{hi:06X} ({n:3d} B) [{tag}]  {old} -> {new}")
        else:
            print(f"  0x{lo:06X}..0x{hi:06X} ({n:3d} B) [{tag}]")
            print(f"       old {old}")
            print(f"       new {new}")
    print()

print("=" * 100)
print("CAVE region 0xC4B34 + 68, all four images")
print("=" * 100)
for nm, img in (("stock", STK), ("V74", V74), ("V75", V75), ("V76", V76)):
    print(f"  {nm:5s} {img[CAVE_BASE:CAVE_BASE + CAVE_EXTENT].hex()}")
print()
print("  V74 vs V75 cave identical:", V74[CAVE_BASE:CAVE_BASE + 96] == V75[CAVE_BASE:CAVE_BASE + 96])
print("  V74 vs V76 cave identical:", V74[CAVE_BASE:CAVE_BASE + 96] == V76[CAVE_BASE:CAVE_BASE + 96])

print()
print("=" * 100)
print("Hook site 0x55C0E (V68.HOOK_ADDR) +8, all four")
print("=" * 100)
for nm, img in (("stock", STK), ("V74", V74), ("V75", V75), ("V76", V76)):
    print(f"  {nm:5s} {img[0x55C0E:0x55C1E].hex()}")

print()
print("=" * 100)
print("Lockstep shadow cells' guards -- any CODE difference V74->V75 outside the cave?")
print("=" * 100)
code_runs = [(l, h) for l, h in runs(V74, V75) if l < 0xC0000]
print(f"  code-region runs (addr < 0xC0000): {len(code_runs)}")
for l, h in code_runs:
    print(f"    0x{l:06X}..0x{h:06X}  ({h-l+1} B)  {V74[l:h+1].hex()} -> {V75[l:h+1].hex()}")
