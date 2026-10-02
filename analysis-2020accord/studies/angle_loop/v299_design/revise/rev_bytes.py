# -*- coding: utf-8 -*-
r"""rev_bytes.py -- V299 rev 2: every byte, from the V298 image (sha 177abf04), patched BY ADDRESS, in memory.
ANALYSIS ONLY: writes NO image or .rwd to the firmware repo.  It writes one DISASM-ONLY scratch copy (named
NOT_AN_ARTIFACT) under _scratch/v299_REV2 for a Ghidra dry-run decode of the new bytes.

Byte sets (all inside the main CRC block [0x13000, 0xC4FFC)):
  rev1  = the synthesis' 21 cave bytes (hard freeze 512->1229; opposing clause -> asymmetric bound + 4 nop) + F181 A16B
  rev2  = rev1 with the span 0xC4C6A..0xC4CAB (66 B) RE-LAID OUT: the same asymmetric-bound semantics in 16 B (the 8 nop
          bytes are reclaimed) + a TWO-LEVEL A3 cap: v-word <= 1382 -> 4096 S (V298's), 1382 < v <= 2880 -> 6144 S,
          v > 2880 -> shl 6, no cap (V298's).  Every instruction form is one V298's cave already executes.
  alt4  = rev1 + the 4-byte edit the stability refuter proposed (0xC4C9C 1382 -> 2880, 0xC4CA4 4096 -> 6144): one cap
          value 6144 for EVERY v <= 2880 (REJECTED in the spec: it also lifts the <= 6 m/s cap; F4 trips at 3 m/s).
Then: CRC trailer recomputed, CRC chain walk_all_blocks (50/50) and bootloader replay walk (49/49), sha256s, full diff,
pattern census of every patched pattern (patch by address), and the revert/candidate .rwd '/' headers read back.
usage: python rev_bytes.py"""
import contextlib
import glob
import hashlib
import io
import json
import os
import struct
import sys
import time
import zlib
from pathlib import Path

T0 = time.time()
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[4]
for sub in ("lib", "verify", "builds", "builds/v50_v79", "builds/v108_plus"):
    sys.path.insert(0, str(KIT / "analysis-2020accord" / sub))
from verify_bootloader_crc import walk, walk_all_blocks  # noqa: E402

OUT = KIT / "_scratch" / "v299_REV2"
OUT.mkdir(parents=True, exist_ok=True)
FWR = Path(os.environ["ACCORD_FIRMWARE_ROOT"])
P = glob.glob(str(FWR / "analysis-2020accord" / "_v298_*_plain_image.bin"))
assert len(P) == 1, P
V298 = Path(P[0]).read_bytes()
assert hashlib.sha256(V298).hexdigest() == "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"
B0, B1 = 0x13000, 0xC4FFC

REV1 = [  # (addr, V298 bytes, new bytes, decoded V298 -> new)
    (0xC4C64, "0002", "cd04", "movea imm16 512 -> 1229 (hard freeze)"),
    (0xC4C6A, "206e2c01", "244f0096", "movea 0x12c,r0,r13 -> ld.h -0x6a00[gp],r9"),
    (0xC4C6E, "ed41", "0968", "cmp r13,r8 -> mov r9,r13"),
    (0xC4C70, "d305", "3069", "bnh 0xC4C7A -> xor r16,r13"),
    (0xC4C72, "244f", "ae05", "ld.h -0x4f60 (1st half) -> bge 0xC4C76"),
    (0xC4C74, "a0b0", "004a", "ld.h -0x4f60 (2nd half) -> mov 0,r9"),
    (0xC4C76, "3049d625244f0096", "0000000000000000", "xor r16,r9 ; blt FRZ ; ld.h -0x6a00 -> 4 x nop"),
]
SPAN0, SPAN1 = 0xC4C6A, 0xC4CAC
REV2_SPAN = [  # (addr, bytes, instruction, loop term)
    (0xC4C6A, "244f0096", "ld.h  -0x6a00[gp],r9", "theta (0.1 deg/count)"),
    (0xC4C6E, "e081", "cmp   r0,r16", "sign of E'"),
    (0xC4C70, "ae05", "bge   0xC4C74", ""),
    (0xC4C72, "8049", "subr  r0,r9", "r9 = theta * sgn(E')"),
    (0xC4C74, "e049", "cmp   r0,r9", ""),
    (0xC4C76, "ae05", "bge   0xC4C7A", ""),
    (0xC4C78, "004a", "mov   0,r9", "r9 = max(theta*sgn(E'), 0)  (= rev1's asym + abs, all cases)"),
    (0xC4C7A, "e447a395", "ld.hu -0x6a5e[gp],r8", "v-word (speed)"),
    (0xC4C7E, "206e400b", "movea 0xb40,r0,r13", "2880 = 12.5 m/s"),
    (0xC4C82, "ed41", "cmp   r13,r8", ""),
    (0xC4C84, "9b15", "bh    0xC4CA6", "v > 2880: shl 6, no cap"),
    (0xC4C86, "c44a", "shl   0x4,r9", ""),
    (0xC4C88, "094ee204", "addi  0x4e2,r9,r9", "+ B = 1250"),
    (0xC4C8C, "206e6605", "movea 0x566,r0,r13", "1382 = 6.0 m/s"),
    (0xC4C90, "ed41", "cmp   r13,r8", ""),
    (0xC4C92, "cb05", "bh    0xC4C9A", "v > 1382: the 6144 level"),
    (0xC4C94, "206e0010", "movea 0x1000,r0,r13", "cap 4096 (v <= 6.0 m/s, = V298)"),
    (0xC4C98, "b505", "br    0xC4C9E", ""),
    (0xC4C9A, "206e0018", "movea 0x1800,r0,r13", "cap 6144 (6.0 < v <= 12.5 m/s, NEW)"),
    (0xC4C9E, "ed49", "cmp   r13,r9", ""),
    (0xC4CA0, "ed4f364b", "cmovh r13,r9,r9", "bound = min_u(bound, cap)"),
    (0xC4CA4, "c505", "br    0xC4CAC", ""),
    (0xC4CA6, "c64a", "shl   0x6,r9", "v > 2880 path"),
    (0xC4CA8, "094ee204", "addi  0x4e2,r9,r9", "+ B = 1250 (no cap)"),
]
ALT4 = [(0xC4C9C, "6605", "400b", "movea 1382 -> 2880 (cap gate)"),
        (0xC4CA4, "0010", "0018", "movea 4096 -> 6144 (cap value)")]


def patch(img, edits, check_old=True):
    b = bytearray(img)
    for a, old, new, _ in edits:
        o, n = bytes.fromhex(old), bytes.fromhex(new)
        if check_old:
            assert bytes(b[a:a + len(o)]) == o, (hex(a), b[a:a + len(o)].hex(), old)
        b[a:a + len(n)] = n
    return b


def finish(b):
    assert b[0x1310D] == 0x41 and bytes(b[0x13100:0x1310E]) == b"39990-TVA,A16A"
    b[0x1310D] = 0x42
    old = struct.unpack_from("<I", b, B1)[0]
    new = zlib.crc32(bytes(b[B0:B1])) & 0xFFFFFFFF
    struct.pack_into("<I", b, B1, new)
    return b, old, new


def qwalk(fn, img):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(bytearray(img))


L = []


def say(s):
    L.append(s)
    print(s)


crc_ok = struct.unpack_from("<I", V298, B1)[0] == zlib.crc32(V298[B0:B1]) & 0xFFFFFFFF
say(f"V298 image sha256 177abf04 (asserted); V298 main trailer {V298[B1:B1 + 4].hex(' ')} = crc32 {'OK' if crc_ok else 'MISMATCH'}; "
    f"V298 chain bad={qwalk(walk_all_blocks, V298)} boot bad={qwalk(walk, V298)}")
r1 = patch(V298, REV1)
span = b"".join(bytes.fromhex(h) for _, h, _, _ in REV2_SPAN)
assert len(span) == SPAN1 - SPAN0 == 66, len(span)
a = SPAN0
for ad, h, _, _ in REV2_SPAN:
    assert ad == a, (hex(ad), hex(a))
    a += len(bytes.fromhex(h))
r2 = bytearray(r1)
r2[SPAN0:SPAN1] = span
alt = patch(r1, ALT4)
res = {}
for nm, b in (("rev1", r1), ("rev2", r2), ("alt4", alt)):
    b, old, new = finish(bytearray(b))
    d = [i for i in range(len(V298)) if b[i] != V298[i]]
    cave = bytes(b[0xC4C00:0xC4D04])
    res[nm] = dict(img=bytes(b), diff=d, trailer=bytes(b[B1:B1 + 4]).hex(" "), cave_sha=hashlib.sha256(cave).hexdigest(),
                   img_sha=hashlib.sha256(bytes(b)).hexdigest(), chain=qwalk(walk_all_blocks, b), boot=qwalk(walk, b))
    nc = sum(1 for i in d if 0xC4C00 <= i < 0xC4D04)
    stray = [hex(i) for i in d if not (0xC4C00 <= i < 0xC4D04 or i == 0x1310D or B1 <= i < B1 + 4)]
    say(f"[{nm}] bytes differing from V298: {len(d)} = cave {nc} + F181 {sum(1 for i in d if i == 0x1310D)} + trailer "
        f"{sum(1 for i in d if B1 <= i < B1 + 4)} (stray {stray})")
    say(f"      trailer {V298[B1:B1 + 4].hex(' ')} -> {res[nm]['trailer']}  | CRC chain walk_all_blocks bad={res[nm]['chain']} "
        f"(50/50 iff 0) | bootloader replay walk bad={res[nm]['boot']} (49/49 iff 0)")
    say(f"      cave sha256 {res[nm]['cave_sha']}  image sha256 {res[nm]['img_sha']}")
assert res["rev1"]["img_sha"].startswith("ac15b533"), "rev1 must reproduce the synthesis' predicted image"
assert res["rev1"]["cave_sha"].startswith("0ea16bde")
say("rev1 reproduces the synthesis' predicted image ac15b533... and cave 0ea16bde... (control)")
d21 = [i for i in range(SPAN0, SPAN1) if r2[i] != r1[i]]
d298 = [i for i in range(SPAN0, SPAN1) if r2[i] != V298[i]]
say(f"rev2 span 0xC4C6A..0xC4CAB: {len(d21)} of 66 bytes differ from rev1, {len(d298)} differ from V298; "
    f"cave bytes differing from V298 in total: {sum(1 for i in res['rev2']['diff'] if 0xC4C00 <= i < 0xC4D04)}")
say("addr      V298  rev1  rev2")
for i in range(0xC4C64, SPAN1, 2):
    say(f"{i:#08x}  {V298[i:i + 2].hex()}  {r1[i:i + 2].hex()}  {r2[i:i + 2].hex()}")
for nm, pat in (("movea 512 (V298 hard freeze)", "206e0002"), ("movea 1382", "206e6605"), ("movea 4096", "206e0010"),
                ("movea 2880", "206e400b"), ("movea 6144", "206e0018"), ("ld.hu -0x6a5e,r8", "e447a395"),
                ("cmovh r13,r9,r9", "ed4f364b")):
    hits = []
    p = bytes.fromhex(pat)
    i = V298.find(p)
    while i >= 0:
        hits.append(hex(i))
        i = V298.find(p, i + 1)
    say(f"census V298 {nm:28s} {pat}: {hits[:8]}{' ...' if len(hits) > 8 else ''} ({len(hits)})")
assert bytes(r2[0xC4C00:SPAN0]) == bytes(r1[0xC4C00:SPAN0]) and bytes(r2[SPAN1:0xC4D04]) == bytes(r1[SPAN1:0xC4D04])
assert bytes(r2[SPAN1:0xC4D04]) == bytes(V298[SPAN1:0xC4D04]) and bytes(r2[0xC4C00:0xC4C64]) == bytes(V298[0xC4C00:0xC4C64])
say("cave outside 0xC4C64..0xC4CAB == V298 byte for byte (table pointer, GB-P rows, FRZ/CAM/DONE tails, op-skip)")
dis = OUT / "V299R2_DISASM_ONLY_NOT_AN_ARTIFACT.bin"
dis.write_bytes(res["rev2"]["img"])
say(f"wrote {dis} (disasm-only scratch copy, sha {hashlib.sha256(res['rev2']['img']).hexdigest()[:16]})")
for nm in ("rev1", "rev2", "alt4"):
    (OUT / f"{nm}_cave.hex").write_text(res[nm]["img"][0xC4C00:0xC4D04].hex(" "), encoding="utf-8")
try:
    from encode_eps import parse_x31
    RW = FWR / "flashing-2020accord" / "rwd"
    for f in sorted(RW.glob("*.rwd")):
        if any(k in f.name for k in ("V298", "V295", "V294")):
            raw = f.read_bytes()
            pr = parse_x31(raw)
            hd = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in pr["headers"]}
            say(f"rwd {f.name[:78]}... sha {hashlib.sha256(raw).hexdigest()[:12]}  '/' = {hd.get('/')}")
except Exception as e:  # noqa: BLE001
    say(f"rwd header read failed: {e!r}")
json.dump({k: dict(trailer=v["trailer"], cave_sha=v["cave_sha"], img_sha=v["img_sha"], chain=v["chain"], boot=v["boot"],
                   ndiff=len(v["diff"])) for k, v in res.items()}, open(OUT / "rev_bytes.json", "w"), indent=1)
say(f"wall {time.time() - T0:.2f} s")
(OUT / "rev_bytes.txt").write_text("\n".join(L), encoding="utf-8")
