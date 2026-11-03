"""STOCK-A340 .rwd -- the operator's stock 39990-TVA-A340 dump, re-packed UNCHANGED into the flashable container.

Purpose: a REVERT file for the A340 car.  The payload is the stock image's [0x13000, 0x100000) byte for byte (nothing
edited, not even the part-number strings), so flashing it returns the ECU to the dump it came from.  The '/' header lists
every string the A340 ECU can report so the flasher's part-number gate accepts it from stock, from the 2x build
(39990-TVA,A340) and from the 6x build (39990-TVA,A34C).

Base: ../accord-firmwares/analysis-2020accord/other bins/39990-TVA-A340.bin  (sha256 01a53539..., the operator's dump).
Container: the V38 .rwd (parsed, cipher validated non-circularly against the known V38 plain image).

Run:  python build_stock_a340.py           (writes the .rwd; < 10 s)
      python build_stock_a340.py --dry-run (everything but the write)
"""
import contextlib
import hashlib
import io
import os
import sys
from pathlib import Path

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import build_vfourframe_tva as FF                                                     # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table         # noqa: E402
from firmware_paths import RWD_DIR                                                    # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                               # noqa: E402

START, END = 0x13000, 0x100000
FW_ROOT = Path(os.environ["ACCORD_FIRMWARE_ROOT"])
A340_PATH = FW_ROOT / "analysis-2020accord" / "other bins" / "39990-TVA-A340.bin"
A340_SHA = "01a53539e19bb0b54fb339a08644ca6981b844fad41276a1f8c305f13aa6f071"

LABEL = "STOCK-A340"
RWD_NAME = f"39990-TVA-A340-{LABEL}-UNMODIFIED.DUMP.01a53539-REVERT-0x{START:X}-0x{END:X}.rwd"
VSTR = [b"39990-TVA-A310", b"39990-TVA-A340", b"39990-TVA,A340", b"39990-TVA,A34C"]   # == the V300-A340 list
HW_STR = b"001100121020"
OK, BAD = "[PASS]", "[FAIL]"


class Run:
    def __init__(self):
        self.n = self.ok = 0
        self.failures = []

    def check(self, cond, msg):
        self.n += 1
        cond = bool(cond)
        self.ok += cond
        print(f"      {OK if cond else BAD} {msg}")
        if not cond:
            self.failures.append(msg)
        return cond


def walk_counts(img):
    out = []
    for fn in (walk, walk_all_blocks):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fails = fn(bytes(img))
        line = [ln for ln in buf.getvalue().splitlines() if "result:" in ln][-1]
        out.append((int(line.split("result:")[1].split("block")[0]), fails))
    return out


def build(dry_run=False):
    R = Run()
    ck = R.check
    print("=" * 110)
    print(f"  {LABEL}: the stock 39990-TVA-A340 dump re-packed UNCHANGED as a flashable .rwd (revert file)")
    print("=" * 110)

    stock = Path(A340_PATH).read_bytes()
    print("\n  [0] BASE")
    ck(len(stock) == 0x100000 and hashlib.sha256(stock).hexdigest() == A340_SHA, f"A340 dump sha256 {A340_SHA[:16]}... (1 MB)")
    ck(stock[0x13100:0x1310E] == b"39990-TVA-A340" and stock[0x14117:0x14125] == b"39990-TVA-A340",
       "both part-number strings (0x13100, 0x14117) read 39990-TVA-A340: this is the stock A340 image, unmodified")
    wc = walk_counts(stock)
    ck(wc == [(49, 0), (50, 0)], f"stock image CRC chain: bootloader replay {wc[0][0]}/{wc[0][1]} fails, full chain {wc[1][0]}/{wc[1][1]} fails")

    print("\n  [1] CONTAINER (V38 .rwd template, cipher validated against the known V38 plain image)")
    src = Path(FF.V38_RWD).read_bytes()
    ck(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    v38 = bytearray(b"\xff" * 0x100000)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    ck(bytes(v38[START:END]) == Path(FF.V38_PLAIN).read_bytes()[START:END], "V38 rwd decodes to the known V38 plain image (non-circular)")
    ck(len(info["blocks"]) == 1 and info["blocks"][0]["start"] == START and info["blocks"][0]["length"] == END - START,
       "template has one block [0x13000, +0xED000)")

    print("\n  [2] ENCODE + READBACK")
    headers = []
    for tag, vals in info["headers"]:
        if tag == b"/":
            vals = list(VSTR)
        elif tag == b"!":
            vals = [HW_STR] * len(VSTR)
        headers.append((tag, list(vals)))
    rwd = encode_x31(headers, info["blocks"], [bytes(stock[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, f"{LABEL} output")
    back = bytearray(b"\xff" * 0x100000)
    back[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    ck(bytes(back[START:END]) == bytes(stock[START:END]), ".rwd payload decodes back BYTE-IDENTICAL to the stock dump over [0x13000, 0x100000)")
    ck(bytes(back[START:END]) != bytes(v38[START:END]), "payload is NOT the V38 template's payload (negative control)")
    got = {t.decode("latin1"): [v.decode("latin1") for v in vv] for t, vv in parse_x31(rwd)["headers"]}
    print(f"      headers: {got}")
    ck(got.get("/") == [s.decode() for s in VSTR] and got.get("!") == [HW_STR.decode()] * len(VSTR) and got.get("&") == ["BF109E"],
       "'/' lists stock A340, the 2x string (TVA,A340) and the 6x string (TVA,A34C); '!' x4; '&' BF109E unchanged")
    # the flasher's own gate (prefix match either way) must accept every string this ECU can report
    # eps-update-tva.py cannot be imported (dash in the name); the rule below is its app_id_matches_part verbatim
    norm = lambda b: b.rstrip(b"\x00").strip()                                                  # noqa: E731
    gate = lambda a: any(norm(a) == norm(p) or norm(a).startswith(norm(p)) or norm(p).startswith(norm(a)) for p in VSTR)   # noqa: E731
    ck(all(gate(s) for s in (b"39990-TVA-A340\x00\x00", b"39990-TVA,A340\x00\x00", b"39990-TVA,A34C\x00\x00")) and not gate(b"39990-TVA-A160\x00\x00"),
       "flasher part gate (eps-update-tva.app_id_matches_part rule): accepts A340 stock / 2x / 6x F181 strings, rejects an A160 ECU")

    out_r = Path(RWD_DIR, RWD_NAME)
    ck(len(str(out_r)) <= 259, f"output path fits 259 chars ({len(str(out_r))})")
    others = [p for p in Path(RWD_DIR).glob("*STOCK-A340*") if p.name != RWD_NAME]
    ck(not others, f"no other STOCK-A340 rwd on disk {[p.name for p in others]}")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("\n" + "=" * 110)
    print(f"  payload = stock dump sha256 {A340_SHA}")
    print(f"  rwd     sha256 {rwd_sha}   ({RWD_NAME})")
    print(f"  {R.ok}/{R.n} checks passed" + ("" if not R.failures else f"  FAILURES: {R.failures}"))
    print("=" * 110)
    if R.failures:
        raise SystemExit("FAILED -- nothing written")
    if dry_run:
        print("  dry run: nothing written")
        return
    out_r.write_bytes(rwd)
    print(f"  wrote {out_r}")


if __name__ == "__main__":
    build(dry_run="--dry-run" in sys.argv)
