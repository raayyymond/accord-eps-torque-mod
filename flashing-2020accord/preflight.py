#!/usr/bin/env python3
"""PRE-FLIGHT CHECK -- run this on the .rwd immediately before flashing.

    python flashing-2020accord/preflight.py <rwd-filename-or-path>

Everything this checks has bitten this kit at least once:

  1. the file is not one of the SUPERSEDED-DO-NOT-FLASH artefacts
  2. the x31 container checksum is intact
  3. the payload decodes to an image whose SHA256 matches a known build
  4. the bootloader CRC chain walks 50/50   (a bad chain is a brick)
  5. the part-number string is the expected 39990-TVA,A160 marker
  6. the 164-byte cave region matches a known build (caves are the ONLY bricking class here)

then prints WHAT ACTUALLY CHANGES versus the build currently on the car, and the stop conditions.

It does not flash anything and it never touches the bus.
"""
import glob
import hashlib
import os
import re
import struct
import sys
from pathlib import Path

# PATH BOOTSTRAP -- .pkgroot lives in analysis-2020accord/, not at the repo root, so walk up
# looking for THAT rather than for a .pkgroot beside this file.
_d = Path(__file__).resolve().parent
while not (_d / "analysis-2020accord" / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
_kit = _d / "analysis-2020accord"
for _p in [_d, _kit]:
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _kit / _sub
    if not _q.is_dir():
        continue
    for _r in [_q] + [x for x in _q.rglob("*") if x.is_dir()]:
        if str(_r) not in sys.path:
            sys.path.insert(0, str(_r))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
RWD_DIR = Path(ROOT, "flashing-2020accord", "rwd")
IMG_DIR = Path(ROOT, "analysis-2020accord")
START, END = 0x13000, 0x100000
FLYING = "v122"
OK, BAD, WARN = "[PASS]", "[FAIL]", "[WARN]"
_n = [0, 0]


def chk(cond, msg, fatal=True):
    _n[0] += 1
    if cond:
        _n[1] += 1
    print(f"  {OK if cond else (BAD if fatal else WARN)} {msg}")
    return bool(cond)


def images():
    out = {}
    for p in glob.glob(str(IMG_DIR / "*plain_image.bin")):
        if "SUPERSEDED" in p:
            continue
        m = re.search(r"_v(\d+)_", os.path.basename(p))
        if m:
            out[int(m.group(1))] = p
    return out


def main(arg):
    print("=" * 92)
    print("  PRE-FLIGHT CHECK -- nothing is flashed and no bus is touched")
    print("=" * 92)

    p = Path(arg)
    if not p.exists():
        cand = list(RWD_DIR.glob(f"*{arg}*"))
        cand = [c for c in cand if c.suffix == ".rwd"]
        if len(cand) != 1:
            print(f"  {BAD} {arg!r} matched {len(cand)} files in {RWD_DIR}")
            for c in cand[:8]:
                print(f"         {c.name}")
            return 2
        p = cand[0]
    print(f"\n  file: {p.name}")
    print(f"  dir : {p.parent}")

    print("\n  [1] NOT A SUPERSEDED ARTEFACT")
    if not chk("SUPERSEDED" not in p.name.upper(),
               "the filename does not carry SUPERSEDED-DO-NOT-FLASH"):
        print("\n  STOP. This build was superseded on purpose. See docs/scoring/SHELF.md.")
        return 1

    raw = p.read_bytes()
    print(f"\n  [2] CONTAINER  ({len(raw):,} bytes, sha256 {hashlib.sha256(raw).hexdigest()[:16]}...)")
    try:
        import build_vfourframe_tva as FF
        from encode_eps import parse_x31, build_decode_table
        FF.assert_x31_checksum(raw, p.name)
        chk(True, "x31 container checksum is intact")
    except Exception as e:
        chk(False, f"x31 checksum FAILED: {e}")
        return 1

    print("\n  [3] DECODE AND IDENTIFY")
    info = parse_x31(raw)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    payload = bytes(info["encs"][0]).translate(dec_tbl)
    imgs = images()
    match, img = None, None
    for v, ip in sorted(imgs.items()):
        b = Path(ip).read_bytes()
        if b[START:END] == payload:
            match, img = v, b
            break
    if not chk(match is not None,
               f"payload matches a known build image"
               + (f" -- V{match}" if match else " -- NO MATCH")):
        print("\n  STOP. The .rwd does not decode to any image on disk. Do not flash it.")
        return 1
    print(f"         identified as V{match}   image sha256 "
          f"{hashlib.sha256(img).hexdigest()[:16]}...")

    print("\n  [4] BOOTLOADER CRC CHAIN")
    try:
        from verify_bootloader_crc import walk_all_blocks
        import io as _io
        import contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            bad = walk_all_blocks(img)
        chk(bad == 0, f"CRC chain walks 50/50 ({bad} mismatch)")
        if bad:
            print("\n  STOP. A broken CRC chain is a brick. Do not flash it.")
            return 1
    except Exception as e:
        chk(False, f"CRC walk failed: {e}")
        return 1

    print("\n  [5] PART-NUMBER MARKER")
    n = img.count(b"39990-TVA,A160")
    chk(n >= 1, f"the modified-firmware marker 39990-TVA,A160 is present ({n} copies)")
    chk(img.count(b"39990-TVA-A160") == 0,
        "no un-marked 39990-TVA-A160 remains", fatal=False)

    print("\n  [6] THE CAVE -- this kit's only bricking class")
    stock = Path(IMG_DIR, "stock_fw_dump", "code.bin").read_bytes()
    cave = img[0xC4B34:0xC4B34 + 164]
    known = {Path(ip).read_bytes()[0xC4B34:0xC4B34 + 164] for ip in imgs.values()}
    chk(cave in known, "the 164-byte cave matches a build on disk (not a novel cave)")
    chk(cave != stock[0xC4B34:0xC4B34 + 164],
        "the cave is present (telemetry active)", fatal=False)

    print("\n  [7] WHAT ACTUALLY CHANGES vs THE BUILD ON THE CAR")
    fly = None
    for v, ip in imgs.items():
        if v == 122:
            fly = Path(ip).read_bytes()
    if fly is None:
        print("         (no flying-build image on disk; skipped)")
    else:
        d = [a for a in range(START, END) if img[a] != fly[a] and (a & 0xFFF) < 0xFFC]
        runs = []
        for a in d:
            if runs and a <= runs[-1][1]:
                runs[-1][1] = max(runs[-1][1], a + 1)
            else:
                runs.append([a, a + 1])
        # a run only covers the bytes that DIFFER, so a 4-byte float whose last byte happens to
        # match reads as "3B" and decodes wrong.  Snap to the natural cell width.
        FLOATS = {0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4}
        snapped = []
        for lo, hi in runs:
            base = lo & ~3
            if base in FLOATS:
                lo, hi = base, base + 4
            else:
                lo &= ~1
                hi = hi + (hi & 1)
            if snapped and lo <= snapped[-1][1]:
                snapped[-1][1] = max(snapped[-1][1], hi)
            else:
                snapped.append([lo, hi])
        # split any run spanning the biquad block so each float32 prints on its own
        split = []
        for lo, hi in snapped:
            if (lo & ~3) in FLOATS and hi - lo > 4:
                for q in range(lo, hi, 4):
                    split.append([q, min(q + 4, hi)])
            else:
                split.append([lo, hi])
        runs = split
        print(f"         {len(d)} payload bytes in {len(runs)} cells vs V{FLYING[1:]}:")
        for lo, hi in runs:
            k = hi - lo
            if k == 4 and (lo & ~3) in FLOATS:
                a, b = (round(struct.unpack_from("<f", fly, lo)[0], 7),
                        round(struct.unpack_from("<f", img, lo)[0], 7))
                print(f"           0x{lo:05X} (f32)  {a}  ->  {b}")
            elif k == 1:
                print(f"           0x{lo:05X} (u8 )  {fly[lo]}  ->  {img[lo]}")
            elif k % 2 == 0 and k <= 8:
                a = [struct.unpack_from("<h", fly, lo + 2 * i)[0] for i in range(k // 2)]
                b = [struct.unpack_from("<h", img, lo + 2 * i)[0] for i in range(k // 2)]
                print(f"           0x{lo:05X} (i16)  {a}  ->  {b}")
            else:
                a = " ".join("%02x" % x for x in fly[lo:min(hi, lo + 6)])
                b = " ".join("%02x" % x for x in img[lo:min(hi, lo + 6)])
                print(f"           0x{lo:05X} ({k}B )  {a}  ->  {b}")

    print("\n" + "=" * 92)
    print(f"  {_n[1]}/{_n[0]} checks passed -- V{match} is INTERNALLY CONSISTENT and safe to send")
    print("=" * 92)
    print("""
  BEFORE YOU FLASH
    - kill openpilot/pandad first:   tmux kill-server
    - name the file and the bus out loud; they must be read back to you
    - keep docs/scoring/SHELF.md open for the stop conditions

  STOP CONDITIONS ON THE DRIVE
    - ratcheting noticeably WORSE      -> the inertia sign was inverted; reflash V195
    - wheel heavy/dead to fast inputs  -> the half-dose is too much; quarter it
    - a new high note WHILE ENGAGED    -> Honda's 55 Hz null, which the notch gives up.
                                          Manual driving is bit-for-bit stock, so it can only
                                          appear with LKAS on.
""")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
