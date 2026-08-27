#!/usr/bin/env python3
"""V87 ARC-MAP READER.  Extends studies/ledger/ledger_v38_to_v85_bytes.py to V86 / V86B and adds:
  (B) a FULL-BLOCK virginity scan of the plant-model cal block [0xC4000, 0xC4200) across every image
  (D) the silent-loss audit run against V86 *and* V86B (the ledger only scores one CURRENT)
  (E) a whole-image byte-diff-vs-stock census per build, so "what has actually moved" is read from
      the images and not from any curated SITES list.

Reads PLAIN IMAGES ON DISK.  V850 is little-endian; file offset == firmware address.
Env: ACCORD_FIRMWARE_ROOT (default C:/Users/dudei/Desktop/Projects/accord-firmwares)
"""
import importlib.util, os, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("led", HERE / "studies/ledger/ledger_v38_to_v85_bytes.py")
led = importlib.util.module_from_spec(spec)
sys.modules["led"] = led
spec.loader.exec_module(led)

BUILDS = list(led.BUILDS) + [
    ("V86",  "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V86B", "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
]
ROOT = led.ROOT
s16 = led.s16


def load_all():
    imgs = {}
    for name, f in BUILDS:
        p = f if isinstance(f, Path) else ROOT / f
        if not p.exists():
            print(f"### MISSING {name}: {p}", file=sys.stderr); continue
        imgs[name] = p.read_bytes()
    return imgs


def audit(imgs, cur):
    st = imgs["STOCK"]; b = imgs[cur]
    print("=" * 100)
    print(f"SILENT-LOSS AUDIT vs {cur}")
    print("=" * 100)
    for label, cells, carried, status in led.CONFIRMED_FIXES:
        rows = []
        for addr, w, want in cells:
            got = b[addr] if w == 1 else s16(b, addr)
            stv = st[addr] if w == 1 else s16(st, addr)
            rows.append((addr, w, want, got, stv, got == want))
        allok = all(r[5] for r in rows)
        allstock = all(r[3] == r[4] for r in rows)
        verdict = "PRESENT" if allok else ("BYTE-STOCK (ABSENT)" if allstock else "PARTIAL")
        print(f"\n[{verdict:>19}]  {label}")
        for addr, w, want, got, stv, good in rows:
            f = (lambda v: f"0x{v:02X}") if w == 1 else str
            print(f"      {'ok ' if good else '!! '}0x{addr:05X} w{w}  want={f(want):>8}  "
                  f"{cur}={f(got):>8}  stock={f(stv):>8}")


def plant_block(imgs, names, lo=0xC4000, hi=0xC4200):
    print("\n\n" + "=" * 100)
    print(f"PLANT-MODEL CAL BLOCK VIRGINITY  [0x{lo:05X}, 0x{hi:05X})  — every differing halfword, every build")
    print("=" * 100)
    st = imgs["STOCK"]
    any_diff = False
    for n in names:
        if n == "STOCK":
            continue
        b = imgs[n]
        diffs = [(a, s16(st, a), s16(b, a)) for a in range(lo, hi, 2) if b[a:a+2] != st[a:a+2]]
        if diffs:
            any_diff = True
            print(f"  {n:<10} {len(diffs)} halfword(s): " +
                  ", ".join(f"0x{a:05X} {o}->{v}" for a, o, v in diffs))
    if not any_diff:
        print("  (no build differs from stock anywhere in the block)")
    # per-address summary
    print("\n  --- per-address: which builds ever touched each cell in the block ---")
    for a in range(lo, hi, 2):
        touched = [n for n in names if n != "STOCK" and imgs[n][a:a+2] != st[a:a+2]]
        if touched:
            print(f"  0x{a:05X}  stock={s16(st,a):<7} touched by: {', '.join(touched)}")


def diff_census(imgs, names):
    print("\n\n" + "=" * 100)
    print("WHOLE-IMAGE BYTE-DIFF-VS-STOCK CENSUS (count of differing bytes, and region breakdown)")
    print("=" * 100)
    st = imgs["STOCK"]
    REGIONS = [("code   0x00000-0xC0000", 0x00000, 0xC0000),
               ("cal    0xC0000-0xD0000", 0xC0000, 0xD0000),
               ("tabl   0xD0000-0xE0000", 0xD0000, 0xE0000),
               ("tabl2  0xE0000-0x100000", 0xE0000, 0x100000)]
    print(f"  {'build':<10} {'total':>7}  " + "  ".join(f"{r[0].split()[0]:>7}" for r in REGIONS))
    for n in names:
        if n == "STOCK":
            continue
        b = imgs[n]
        tot = sum(1 for i in range(0x100000) if b[i] != st[i])
        parts = []
        for _, lo, hi in REGIONS:
            parts.append(sum(1 for i in range(lo, hi) if b[i] != st[i]))
        print(f"  {n:<10} {tot:>7}  " + "  ".join(f"{p:>7}" for p in parts))


def pairdiff(imgs, a, b):
    print("\n\n" + "=" * 100)
    print(f"BYTE DIFF  {a} -> {b}   (differing halfword-aligned regions)")
    print("=" * 100)
    A, B = imgs[a], imgs[b]
    runs = []
    i = 0
    while i < 0x100000:
        if A[i] != B[i]:
            j = i
            while j < 0x100000 and A[j] != B[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    for lo, hi in runs:
        print(f"  0x{lo:05X}..0x{hi-1:05X}  ({hi-lo}B)  {a}={A[lo:hi].hex()}  {b}={B[lo:hi].hex()}")
    print(f"  total {len(runs)} run(s), {sum(h-l for l,h in runs)} bytes")


if __name__ == "__main__":
    imgs = load_all()
    names = [n for n, _ in BUILDS if n in imgs]
    st = imgs["STOCK"]
    assert len(st) == 0x100000
    assert s16(st, 0xC407E) == 511 and s16(st, 0xC40BC) == 600
    print(f"BUILDS LOADED: {len(names)}  (last = {names[-1]})\n")
    for cur in ("V86", "V86B"):
        if cur in imgs:
            audit(imgs, cur)
    plant_block(imgs, names)
    if "V86" in imgs:
        pairdiff(imgs, "V85", "V86")
    if "V86B" in imgs:
        pairdiff(imgs, "V85", "V86B")
    diff_census(imgs, names)
